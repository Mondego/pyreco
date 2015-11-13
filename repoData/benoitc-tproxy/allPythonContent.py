__FILENAME__ = couchdbrouter
import re
re_host = re.compile("Host:\s*(.*)\r\n")

class CouchDBRouter(object):
    # look at the routing table and return a couchdb node to use
    def lookup(self, name):
        """ do something """
        return ("127.0.0.1",5984)
router = CouchDBRouter()

# Perform content-aware routing based on the stream data. Here, the
# Host header information from the HTTP protocol is parsed to find the 
# username and a lookup routine is run on the name to find the correct
# couchdb node. If no match can be made yet, do nothing with the
# connection. (make your own couchone server...)

def proxy(data):
    matches = re_host.findall(data)
    if matches:
        host = router.lookup(matches.pop()) 
        return {"remote": host}
    return None

########NEW FILE########
__FILENAME__ = httpproxy
# -*- coding: utf-8 -
#
# This file is part of tproxy released under the MIT license. 
# See the NOTICE for more information.


""" simple proxy that can be used behind a browser. 
This example require http_parser module:

    pip install http_parser

"""

import io
import urlparse
import socket

from http_parser.http import HttpStream, NoMoreData, ParserError
from http_parser.parser import HttpParser
from tproxy.util import parse_address

def get_host(addr, is_ssl=False):
    """ return a correct Host header """
    host = addr[0]
    if addr[1] != (is_ssl and 443 or 80):
        host = "%s:%s" % (host, addr[1])
    return host


def write_chunk(to, data):
    """ send a chunk encoded """
    chunk = "".join(("%X\r\n" % len(data), data, "\r\n"))
    to.writeall(chunk)

def write(to, data):
    to.writeall(data)

def send_body(to, body, chunked=False):
    if chunked:
        _write = write_chunk
    else:
        _write = write

    while True:
        data = body.read(io.DEFAULT_BUFFER_SIZE)
        if not data:
            break
        _write(to, data)

    if chunked:
        _write(to, "")

def rewrite_request(req):
    try:
        while True:
            parser = HttpStream(req)
            headers = parser.headers()

            parsed_url = urlparse.urlparse(parser.url())

            is_ssl = parsed_url.scheme == "https"

            host = get_host(parse_address(parsed_url.netloc, 80),
                is_ssl=is_ssl)
            headers['Host'] = host
            headers['Connection'] = 'close'

            if 'Proxy-Connection' in headers:
                del headers['Proxy-Connection']


            location = urlparse.urlunparse(('', '', parsed_url.path,
                parsed_url.params, parsed_url.query, parsed_url.fragment))

            httpver = "HTTP/%s" % ".".join(map(str, 
                        parser.version()))

            new_headers = ["%s %s %s\r\n" % (parser.method(), location, 
                httpver)]

            new_headers.extend(["%s: %s\r\n" % (hname, hvalue) \
                    for hname, hvalue in headers.items()])

            req.writeall(bytes("".join(new_headers) + "\r\n"))
            body = parser.body_file()
            send_body(req, body, parser.is_chunked())

    except (socket.error, NoMoreData, ParserError):
            pass
    
def proxy(data):
    recved = len(data)

    idx = data.find("\r\n")
    if idx <= 0:
        return

    line, rest = data[:idx], data[idx:]
    if line.startswith("CONNECT"):
        parts = line.split(None)
        netloc = parts[1]
        remote = parse_address(netloc, 80)

        reply_msg = "%s 200 OK\r\n\r\n" % parts[2]
        return {"remote": remote, 
                "reply": reply_msg,
                "data": ""}


    parser = HttpParser()
    parsed = parser.execute(data, recved)
    if parsed != recved:
        return  { 'close':'HTTP/1.0 502 Gateway Error\r\n\r\nError parsing request'}

    if not parser.get_url():
        return

    parsed_url = urlparse.urlparse(parser.get_url())

    is_ssl = parsed_url.scheme == "https"
    remote = parse_address(parsed_url.netloc, 80)

    return {"remote": remote, 
            "ssl": is_ssl}

########NEW FILE########
__FILENAME__ = httprewrite
import re
from http_parser.http import HttpStream, NoMoreData
from http_parser.reader import SocketReader
import socket

def rewrite_headers(parser, values=None):
    headers = parser.headers()
    if isinstance(values, dict):
        headers.update(values)

    httpver = "HTTP/%s" % ".".join(map(str, 
                parser.version()))

    new_headers = ["%s %s %s\r\n" % (parser.method(), parser.url(), 
        httpver)]

    new_headers.extend(["%s: %s\r\n" % (k, str(v)) for k, v in \
            headers.items()])

    return "".join(new_headers) + "\r\n"

def rewrite_request(req):
    try: 
        while True:
            parser = HttpStream(req)
                
            new_headers = rewrite_headers(parser, {'Host': 'gunicorn.org'})
            if new_headers is None:
                break
            req.send(new_headers)
            body = parser.body_file()
            while True:
                data = body.read(8192)
                if not data:
                    break
                req.writeall(data)
    except (socket.error, NoMoreData):
        pass

def rewrite_response(resp):
    try:
        while True:
            parser = HttpStream(resp)
            # we aren't doing anything here
            for data in parser:
                resp.writeall(data)
     
            if not parser.should_keep_alive():
                # close the connection.
                break
    except (socket.error, NoMoreData):
        pass

def proxy(data):
    return {'remote': ('gunicorn.org', 80)}

########NEW FILE########
__FILENAME__ = psock4
import socket
import struct

def proxy(data):
    if len(data) < 9:
        return

    command = ord(data[1])
    ip, port = socket.inet_ntoa(data[4:8]), struct.unpack(">H", data[2:4])[0]
    idx = data.index("\0")
    userid = data[8:idx]

    if command == 1: #connect
        return dict(remote="%s:%s" % (ip, port),
                reply="\0\x5a\0\0\0\0\0\0",
                data=data[idx:])
    else:
        return {"close": "\0\x5b\0\0\0\0\0\0"}

########NEW FILE########
__FILENAME__ = sendfile
import os

WELCOME_FILE = os.path.join(os.path.dirname(__file__), "welcome.txt")

def proxy(data):
    fno = os.open(WELCOME_FILE, os.O_RDONLY) 
    return {
            "file": fno,
            "reply": "HTTP/1.1 200 OK\r\n\r\n"
           }

########NEW FILE########
__FILENAME__ = ssl
def proxy(data):
    return {'remote': ('encrypted.google.com', 443), "ssl": True}

########NEW FILE########
__FILENAME__ = transparent
def proxy(data):
    return { "remote": "google.com:80" }

########NEW FILE########
__FILENAME__ = transparentrw
import io
import re

def rewrite_request(req):
    while True:
        data = req.read(io.DEFAULT_BUFFER_SIZE)
        if not data:
            break
        req.writeall(data) 

def rewrite_response(resp):
    while True:
        data = resp.read(io.DEFAULT_BUFFER_SIZE)
        if not data:
            break
        resp.writeall(data)

def proxy(data):
    return {'remote': ('google.com', 80)}

########NEW FILE########
__FILENAME__ = app
# -*- coding: utf-8 -
#
# This file is part of tproxy released under the MIT license. 
# See the NOTICE for more information.

import imp
import inspect
import logging
from logging.config import fileConfig
import os
import sys

from gevent import core
from gevent.hub import get_hub
from gevent import monkey
monkey.noisy = False
monkey.patch_all()

from . import util
from .arbiter import Arbiter
from .config import Config
from .tools import import_module

class Script(object):
    """ load a python file or module """

    def __init__(self, script_uri, cfg=None):
        self.script_uri = script_uri
        self.cfg = cfg

    def load(self):
        if os.path.exists(self.script_uri):
            script = imp.load_source('_route', self.script_uri)
        else:
            if ":" in self.script_uri:
                parts = self.script_uri.rsplit(":", 1)
                name, objname = parts[0], parts[1]
                mod = import_module(name)

                script_class = getattr(mod, objname)
                if inspect.getargspec(script_class.__init__) > 1:
                    script = script_class(self.cfg)
                else:
                    script=script_class()
            else:
                script = import_module(self.script_uri)

        script.__dict__['__tproxy_cfg__'] = self.cfg
        return script
                        
class Application(object):

    LOG_LEVELS = {
        "critical": logging.CRITICAL,
        "error": logging.ERROR,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG
    }

    def __init__(self):
        self.logger = None
        self.cfg = Config("%prog [OPTIONS] script_path")
        self.script = None

    def load_config(self):
         # parse console args
        parser = self.cfg.parser()
        opts, args = parser.parse_args()

        if len(args) != 1:
            parser.error("No script or module specified.")

        script_uri = args[0]
        self.cfg.default_name = args[0]

        # Load conf
        try:
            for k, v in opts.__dict__.items():
                if v is None:
                    continue
                self.cfg.set(k.lower(), v)
        except Exception, e:
            sys.stderr.write("config error: %s\n" % str(e))
            os._exit(1)

        # setup script
        self.script = Script(script_uri, cfg=self.cfg)
        sys.path.insert(0, os.getcwd())


    def configure_logging(self):
        """\
        Set the log level and choose the destination for log output.
        """
        self.logger = logging.getLogger('tproxy')

        fmt = r"%(asctime)s [%(process)d] [%(levelname)s] %(message)s"
        datefmt = r"%Y-%m-%d %H:%M:%S"
        if not self.cfg.logconfig:
            handlers = []
            if self.cfg.logfile != "-":
                handlers.append(logging.FileHandler(self.cfg.logfile))
            else:
                handlers.append(logging.StreamHandler())

            loglevel = self.LOG_LEVELS.get(self.cfg.loglevel.lower(), logging.INFO)
            self.logger.setLevel(loglevel)
            for h in handlers:
                h.setFormatter(logging.Formatter(fmt, datefmt))
                self.logger.addHandler(h)
        else:
            if os.path.exists(self.cfg.logconfig):
                fileConfig(self.cfg.logconfig)
            else:
                raise RuntimeError("Error: logfile '%s' not found." %
                        self.cfg.logconfig)

    def run(self):
        self.load_config()

        if self.cfg.daemon:
            util.daemonize()
        else:
            try:
                os.setpgrp()
            except OSError, e:
                if e[0] != errno.EPERM:
                    raise
      
        self.configure_logging()
        try:
            Arbiter(self.cfg, self.script).run()
        except RuntimeError, e:
            sys.stderr.write("\nError: %s\n\n" % e)
            sys.stderr.flush()
            os._exit(1)

def run():
    Application().run()

########NEW FILE########
__FILENAME__ = arbiter
# -*- coding: utf-8 -
#
# This file is part of tproxy released under the MIT license. 
# See the NOTICE for more information.

import errno
import logging
import os
import signal
import sys
import time
import traceback

import gevent
from gevent import select

from . import __version__
from . import util
from .pidfile import Pidfile
from .proxy import tcp_listener
from .worker import Worker



class HaltServer(Exception):
    def __init__(self, reason, exit_status=1):
        self.reason = reason
        self.exit_status = exit_status
    
    def __str__(self):
        return "<HaltServer %r %d>" % (self.reason, self.exit_status)

class Arbiter(object):

    WORKER_BOOT_ERROR = 3

    START_CTX = {}
    
    LISTENER = None
    WORKERS = {}    
    PIPE = []

    # I love dynamic languages
    SIG_QUEUE = []
    SIGNALS = map(
        lambda x: getattr(signal, "SIG%s" % x),
        "HUP QUIT INT TERM TTIN TTOU USR1 USR2 WINCH".split()
    )
    SIG_NAMES = dict(
        (getattr(signal, name), name[3:].lower()) for name in dir(signal)
        if name[:3] == "SIG" and name[3] != "_"
    )

    def __init__(self, cfg, script):
        self.cfg = cfg
        self.script = script
        self.num_workers = cfg.workers
        self.address = cfg.address
        self.timeout = cfg.timeout
        self.name = cfg.name

        self.pid = 0
        self.pidfile = None
        self.worker_age = 0
        self.reexec_pid = 0
        self.master_name = "master"
        self.log = logging.getLogger(__name__)

        # get current path, try to use PWD env first
        try:
            a = os.stat(os.environ['PWD'])
            b = os.stat(os.getcwd())
            if a.ino == b.ino and a.dev == b.dev:
                cwd = os.environ['PWD']
            else:
                cwd = os.getcwd()
        except:
            cwd = os.getcwd()
            
        args = sys.argv[:]
        args.insert(0, sys.executable)

        # init start context
        self.START_CTX = {
            "args": args,
            "cwd": cwd,
            0: sys.executable
        }

    def start(self):
        self.pid = os.getpid()
        self.init_signals()
        if not self.LISTENER:
            self.LISTENER = tcp_listener(self.address, self.cfg.backlog)

        if self.cfg.pidfile is not None:
            self.pidfile = Pidfile(self.cfg.pidfile)
            self.pidfile.create(self.pid)

        util._setproctitle("master [%s]" % self.name)
        self.log.info("tproxy %s started" % __version__)
        self.log.info("Listening on %s:%s" % self.address)

    def init_signals(self):
        """\
        Initialize master signal handling. Most of the signals
        are queued. Child signals only wake up the master.
        """
        if self.PIPE:
            map(os.close, self.PIPE)
        self.PIPE = pair = os.pipe()
        map(util.set_non_blocking, pair)
        map(util.close_on_exec, pair)
        map(lambda s: signal.signal(s, self.signal), self.SIGNALS)
        signal.signal(signal.SIGCHLD, self.handle_chld)

    def signal(self, sig, frame):
        if len(self.SIG_QUEUE) < 5:
            self.SIG_QUEUE.append(sig)
            self.wakeup()
        else:
            self.log.warn("Dropping signal: %s" % sig)

    def run(self):
        self.start()
        self.manage_workers()
        while True:
            try:
                self.reap_workers()
                sig = self.SIG_QUEUE.pop(0) if len(self.SIG_QUEUE) else None
                if sig is None:
                    self.sleep()
                    self.murder_workers()
                    self.manage_workers()
                    continue
                
                if sig not in self.SIG_NAMES:
                    self.log.info("Ignoring unknown signal: %s" % sig)
                    continue
                
                signame = self.SIG_NAMES.get(sig)
                handler = getattr(self, "handle_%s" % signame, None)
                if not handler:
                    self.log.error("Unhandled signal: %s" % signame)
                    continue
                self.log.info("Handling signal: %s" % signame)
                handler()  
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
                self.log.info("Unhandled exception in main loop:\n%s" %  
                            traceback.format_exc())
                self.stop(False)
                if self.pidfile is not None:
                    self.pidfile.unlink()
                sys.exit(-1)
    
    def handle_chld(self, *args):
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
        self.log.info("Hang up: %s" % self.master_name)
        self.reload()
        
    def handle_quit(self):
        "SIGQUIT handling"
        raise StopIteration
    
    def handle_int(self):
        "SIGINT handling"
        self.stop(False)
        raise StopIteration
    
    def handle_term(self):
        "SIGTERM handling"
        self.stop(False)
        raise StopIteration

    def handle_ttin(self):
        """\
        SIGTTIN handling.
        Increases the number of workers by one.
        """
        self.num_workers += 1
        self.manage_workers()
    
    def handle_ttou(self):
        """\
        SIGTTOU handling.
        Decreases the number of workers by one.
        """
        if self.num_workers <= 1:
            return
        self.num_workers -= 1
        self.manage_workers()

    def handle_usr1(self):
        """\
        SIGUSR1 handling.
        Kill all workers by sending them a SIGUSR1
        """
        self.kill_workers(signal.SIGUSR1)
    
    def handle_usr2(self):
        """\
        SIGUSR2 handling.
        Creates a new master/worker set as a slave of the current
        master without affecting old workers. Use this to do live
        deployment with the ability to backout a change.
        """
        self.reexec()
        
    def handle_winch(self):
        "SIGWINCH handling"
        if os.getppid() == 1 or os.getpgrp() != os.getpid():
            self.log.info("graceful stop of workers")
            self.num_workers = 0
            self.kill_workers(signal.SIGQUIT)
        else:
            self.log.info("SIGWINCH ignored. Not daemonized")
    
    def wakeup(self):
        """\
        Wake up the arbiter by writing to the PIPE
        """
        try:
            os.write(self.PIPE[1], '.')
        except IOError, e:
            if e.errno not in [errno.EAGAIN, errno.EINTR]:
                raise
                    
    def halt(self, reason=None, exit_status=0):
        """ halt arbiter """
        self.stop()
        self.log.info("Shutting down: %s" % self.master_name)
        if reason is not None:
            self.log.info("Reason: %s" % reason)
        if self.pidfile is not None:
            self.pidfile.unlink()
        sys.exit(exit_status)

    def sleep(self):
        """\
        Sleep until PIPE is readable or we timeout.
        A readable PIPE means a signal occurred.
        """
        try:
            ready = select.select([self.PIPE[0]], [], [], 1.0)
            if not ready[0]:
                return
            while os.read(self.PIPE[0], 1):
                pass
        except select.error, e:
            if e[0] not in [errno.EAGAIN, errno.EINTR]:
                raise
        except OSError, e:
            if e.errno not in [errno.EAGAIN, errno.EINTR]:
                raise
        except KeyboardInterrupt:
            sys.exit()
            
    
    def stop(self, graceful=True):
        """\
        Stop workers
        
        :attr graceful: boolean, If True (the default) workers will be
        killed gracefully  (ie. trying to wait for the current connection)
        """
        self.LISTENER = None
        sig = signal.SIGQUIT
        if not graceful:
            sig = signal.SIGTERM
        limit = time.time() + self.timeout
        while self.WORKERS and time.time() < limit:
            self.kill_workers(sig)
            gevent.sleep(0.1)
            self.reap_workers()
        self.kill_workers(signal.SIGKILL)

    def reexec(self):
        """\
        Relaunch the master and workers.
        """
        if self.pidfile is not None:
            self.pidfile.rename("%s.oldbin" % self.pidfile.fname)
        
        self.reexec_pid = os.fork()
        if self.reexec_pid != 0:
            self.master_name = "Old Master"
            return
            
        os.environ['TPROXY_FD'] = str(self.LISTENER.fileno())
        os.chdir(self.START_CTX['cwd'])
        self.cfg.pre_exec(self)
        os.execvpe(self.START_CTX[0], self.START_CTX['args'], os.environ)
        
    def reload(self):
        # spawn new workers with new app & conf
        for i in range(self.cfg.workers):
            self.spawn_worker()
        
        # unlink pidfile
        if self.pidfile is not None:
            self.pidfile.unlink()

        # create new pidfile
        if self.cfg.pidfile is not None:
            self.pidfile = Pidfile(self.cfg.pidfile)
            self.pidfile.create(self.pid)
        
        # manage workers
        self.manage_workers() 
        
    def murder_workers(self):
        """\
        Kill unused/idle workers
        """
        for (pid, worker) in self.WORKERS.items():
            try:
                diff = time.time() - os.fstat(worker.tmp.fileno()).st_ctime
                if diff <= self.timeout:
                    continue
            except ValueError:
                continue

            self.log.critical("WORKER TIMEOUT (pid:%s)" % pid)
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
                if self.reexec_pid == wpid:
                    self.reexec_pid = 0
                else:
                    # A worker said it cannot boot. We'll shutdown
                    # to avoid infinite start/stop cycles.
                    exitcode = status >> 8
                    if exitcode == self.WORKER_BOOT_ERROR:
                        reason = "Worker failed to boot."
                        raise HaltServer(reason, self.WORKER_BOOT_ERROR)
                    worker = self.WORKERS.pop(wpid, None)
                    if not worker:
                        continue
                    worker.tmp.close()
        except OSError, e:
            if e.errno == errno.ECHILD:
                pass
    
    def manage_workers(self):
        """\
        Maintain the number of workers by spawning or killing
        as required.
        """
        if len(self.WORKERS.keys()) < self.num_workers:
            self.spawn_workers()

        num_to_kill = len(self.WORKERS) - self.num_workers
        for i in range(num_to_kill, 0, -1):
            pid, age = 0, sys.maxint
            for (wpid, worker) in self.WORKERS.iteritems():
                if worker.age < age:
                    pid, age = wpid, worker.age
            self.kill_worker(pid, signal.SIGQUIT)
            
    def spawn_worker(self):
        self.worker_age += 1
        worker = Worker(self.worker_age, self.pid, self.LISTENER, self.cfg,
                self.script)
        pid = os.fork()
        if pid != 0:
            self.WORKERS[pid] = worker
            return

        # Process Child
        worker_pid = os.getpid()
        try:
            self.log.info("Booting worker with pid: %s" % worker_pid)
            worker.serve_forever()
            sys.exit(0)
        except SystemExit:
            raise
        except KeyboardInterrupt:
            sys.exit(0)
        except:
            self.log.exception("Exception in worker process:")
            if not worker.booted:
                sys.exit(self.WORKER_BOOT_ERROR)
            sys.exit(-1)
        finally:
            self.log.info("Worker exiting (pid: %s)" % worker_pid)
            try:
                worker.tmp.close()
            except:
                pass

    def spawn_workers(self):
        """\
        Spawn new workers as needed.
        
        This is where a worker process leaves the main loop
        of the master process.
        """
        
        for i in range(self.num_workers - len(self.WORKERS.keys())):
            self.spawn_worker()

    def kill_workers(self, sig):
        """\
        Lill all workers with the signal `sig`
        :attr sig: `signal.SIG*` value
        """
        for pid in self.WORKERS.keys():
            self.kill_worker(pid, sig)
                    
    def kill_worker(self, pid, sig):
        """\
        Kill a worker
        
        :attr pid: int, worker pid
        :attr sig: `signal.SIG*` value
         """
        try:
            os.kill(pid, sig)
        except OSError, e:
            if e.errno == errno.ESRCH:
                try:
                    worker = self.WORKERS.pop(pid)
                    worker.tmp.close()
                    return
                except (KeyError, OSError):
                    return
            raise

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -
#
# This file is part of tproxy released under the MIT license. 
# See the NOTICE for more information.

import logging
import os
import ssl

import gevent
from gevent import coros
from gevent import socket
import greenlet

from .server import ServerConnection, InactivityTimeout
from .util import parse_address, is_ipv6
from .sendfile import async_sendfile

log = logging.getLogger(__name__)

class ConnectionError(Exception):
    """ Exception raised when a connection is either rejected or a
    connection timeout occurs """

class ClientConnection(object):

    def __init__(self, sock, addr, worker):
        self.sock = sock
        self.addr = addr
        self.worker = worker

        self.route = self.worker.route
        self.buf = []
        self.remote = None
        self.connected = False
        self._lock = coros.Semaphore()

    def handle(self):
        with self._lock:
            self.worker.nb_connections +=1
            self.worker.refresh_name()

        try:
            while not self.connected:
                data = self.sock.recv(1024)
                if not data:
                    break
                self.buf.append(data)
                if self.remote is None:
                    try:
                        self.do_proxy()
                    except StopIteration:
                        break
        except ConnectionError, e:
            log.error("Error while connecting: [%s]" % str(e))
            self.handle_error(e)
        except InactivityTimeout, e:
            log.warn("inactivity timeout")
            self.handle_error(e)
        except socket.error, e:
            log.error("socket.error: [%s]" % str(e))
            self.handle_error(e)
        except greenlet.GreenletExit:
            pass
        except KeyboardInterrupt:
            pass
        except Exception, e:
            log.error("unknown error %s" % str(e))
        finally:
            if self.remote is not None:
                log.debug("Close connection to %s:%s" % self.remote)

            with self._lock:
                self.worker.nb_connections -=1
                self.worker.refresh_name()
            _closesocket(self.sock)

    def handle_error(self, e):
        if hasattr(self.route, 'proxy_error'):
            self.route.proxy_error(self, e)

    def do_proxy(self):
        commands = self.route.proxy("".join(self.buf))
        if commands is None: # do nothing
            return 

        
        if not isinstance(commands, dict):
            raise StopIteration
        
        if 'remote' in commands:
            remote = parse_address(commands['remote'])
            if 'data' in commands:
                self.buf = [commands['data']]
            if 'reply' in commands:
                self.send_data(self.sock, commands['reply'])
            
            is_ssl = commands.get('ssl', False)
            ssl_args = commands.get('ssl_args', {})
            extra = commands.get('extra')
            connect_timeout = commands.get('connect_timeout')
            inactivity_timeout = commands.get('inactivity_timeout')
            self.connect_to_resource(remote, is_ssl=is_ssl, connect_timeout=connect_timeout,
                    inactivity_timeout=inactivity_timeout, extra=extra,
                    **ssl_args)

        elif 'close' in commands:
            if isinstance(commands['close'], basestring): 
                self.send_data(self.sock, commands['close'])
            raise StopIteration()

        elif 'file' in commands:
            # command to send a file
            if isinstance(commands['file'], basestring):
                fdin = os.open(commands['file'], os.O_RDONLY)
            else:
                fdin = commands['file']

            offset = commands.get('offset', 0)
            nbytes = commands.get('nbytes', os.fstat(fdin).st_size)
        
            # send a reply if needed, useful in HTTP response.
            if 'reply' in commands:
                self.send_data(self.sock, commands['reply'])
            
            # use sendfile if possible to send the file content
            async_sendfile(self.sock.fileno(), fdin, offset, nbytes)
            raise StopIteration()
        else:
            raise StopIteration()

    def send_data(self, sock, data):
        if hasattr(data, 'read'):
            try:
                data.seek(0)
            except (ValueError, IOError):
                pass
            
            while True:
                chunk = data.readline()
                if not chunk:
                    break
                sock.sendall(chunk)    
        elif isinstance(data, basestring):
           sock.sendall(data)
        else:
            for chunk in data:
                sock.sendall(chunk)

    def connect_to_resource(self, addr, is_ssl=False, connect_timeout=None,
            inactivity_timeout=None, extra=None, **ssl_args):

        with gevent.Timeout(connect_timeout, ConnectionError):
            try:
                if is_ipv6(addr[0]):
                    sock = socket.socket(socket.AF_INET6, 
                            socket.SOCK_STREAM)
                else:
                    sock = socket.socket(socket.AF_INET, 
                            socket.SOCK_STREAM)

                if is_ssl:
                    sock = ssl.wrap_socket(sock, **ssl_args)
                sock.connect(addr)
            except socket.error, e:
                raise ConnectionError(
                        "socket error while connectinng: [%s]" % str(e))

        self.remote = addr
        self.connected = True
        log.debug("Successful connection to %s:%s" % addr)

        if self.buf and self.route.empty_buf:
            self.send_data(sock, self.buf)
            self.buf = []

        server = ServerConnection(sock, self, 
                timeout=inactivity_timeout, extra=extra, buf=self.buf)
        server.handle()

def _closesocket(sock):
    try:
        sock._sock.close()
        sock.close()
    except socket.error:
        pass

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -
#
# This file is part of tproxy released under the MIT license. 
# See the NOTICE for more information.

class ConfigError(Exception):
    """ Exception raised on config error """


# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license. 
# See the NOTICE for more information.

import copy
import grp
import inspect
import optparse
import os
import pwd
import textwrap
import types

from . import __version__
from . import util

KNOWN_SETTINGS = []

class ConfigError(Exception):
    """ Exception raised on config error """

def wrap_method(func):
    def _wrapped(instance, *args, **kwargs):
        return func(*args, **kwargs)
    return _wrapped

def make_settings(ignore=None):
    settings = {}
    ignore = ignore or ()
    for s in KNOWN_SETTINGS:
        setting = s()
        if setting.name in ignore:
            continue
        settings[setting.name] = setting.copy()
    return settings

class Config(object):
        
    def __init__(self, usage=None):
        self.settings = make_settings()
        self.usage = usage
        self.default_name = None
        
    def __getattr__(self, name):
        if name not in self.settings:
            raise AttributeError("No configuration setting for: %s" % name)
        return self.settings[name].get()
    
    def __setattr__(self, name, value):
        if name != "settings" and name in self.settings:
            raise AttributeError("Invalid access!")
        super(Config, self).__setattr__(name, value)
    
    def set(self, name, value):
        if name not in self.settings:
            raise AttributeError("No configuration setting for: %s" % name)
        self.settings[name].set(value)

    def parser(self):
        kwargs = {
            "usage": self.usage,
            "version": __version__
        }
        parser = optparse.OptionParser(**kwargs)

        keys = self.settings.keys()
        def sorter(k):
            return (self.settings[k].section, self.settings[k].order)
        keys.sort(key=sorter)
        for k in keys:
            self.settings[k].add_option(parser)
        return parser

    @property   
    def workers(self):
        return self.settings['workers'].get()

    @property
    def address(self):
        bind = self.settings['bind'].get()
        return util.parse_address(str(bind))
        
    @property
    def uid(self):
        return self.settings['user'].get()
      
    @property
    def gid(self):
        return self.settings['group'].get()
        
    @property
    def name(self):
        pn = self.settings['name'].get()
        if pn is not None:
            return pn
        else:
            return self.default_name or ""
            
class SettingMeta(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(SettingMeta, cls).__new__
        parents = [b for b in bases if isinstance(b, SettingMeta)]
        if not parents:
            return super_new(cls, name, bases, attrs)
    
        attrs["order"] = len(KNOWN_SETTINGS)
        attrs["validator"] = wrap_method(attrs["validator"])
        
        new_class = super_new(cls, name, bases, attrs)
        new_class.fmt_desc(attrs.get("desc", ""))
        KNOWN_SETTINGS.append(new_class)
        return new_class

    def fmt_desc(cls, desc):
        desc = textwrap.dedent(desc).strip()
        setattr(cls, "desc", desc)
        setattr(cls, "short", desc.splitlines()[0])

class Setting(object):
    __metaclass__ = SettingMeta
    
    name = None
    value = None
    section = None
    cli = None
    validator = None
    type = None
    meta = None
    action = None
    default = None
    short = None
    desc = None
    
    def __init__(self):
        if self.default is not None:
            self.set(self.default)    
        
    def add_option(self, parser):
        if not self.cli:
            return
        args = tuple(self.cli)
        kwargs = {
            "dest": self.name,
            "metavar": self.meta or None,
            "action": self.action or "store",
            "type": self.type or "string",
            "default": None,
            "help": "%s [%s]" % (self.short, self.default)
        }
        if kwargs["action"] != "store":
            kwargs.pop("type")
        parser.add_option(*args, **kwargs)
    
    def copy(self):
        return copy.copy(self)
    
    def get(self):
        return self.value
    
    def set(self, val):
        assert callable(self.validator), "Invalid validator: %s" % self.name
        self.value = self.validator(val)

def validate_bool(val):
    if isinstance(val, types.BooleanType):
        return val
    if not isinstance(val, basestring):
        raise TypeError("Invalid type for casting: %s" % val)
    if val.lower().strip() == "true":
        return True
    elif val.lower().strip() == "false":
        return False
    else:
        raise ValueError("Invalid boolean: %s" % val)

def validate_pos_int(val):
    if not isinstance(val, (types.IntType, types.LongType)):
        val = int(val, 0)
    else:
        # Booleans are ints!
        val = int(val)
    if val < 0:
        raise ValueError("Value must be positive: %s" % val)
    return val

def validate_string(val):
    if val is None:
        return None
    if not isinstance(val, basestring):
        raise TypeError("Not a string: %s" % val)
    return val.strip()

def validate_callable(arity):
    def _validate_callable(val):
        if not callable(val):
            raise TypeError("Value is not callable: %s" % val)
        if arity != len(inspect.getargspec(val)[0]):
            raise TypeError("Value must have an arity of: %s" % arity)
        return val
    return _validate_callable


def validate_user(val):
    if val is None:
        return os.geteuid()
    if isinstance(val, int):
        return val
    elif val.isdigit():
        return int(val)
    else:
        try:
            return pwd.getpwnam(val).pw_uid
        except KeyError:
            raise ConfigError("No such user: '%s'" % val)

def validate_group(val):
    if val is None:
        return os.getegid()

    if isinstance(val, int):
        return val
    elif val.isdigit():
        return int(val)
    else:
        try:
            return grp.getgrnam(val).gr_gid
        except KeyError:
            raise ConfigError("No such group: '%s'" % val)


class Bind(Setting):
    name = "bind"
    section = "Server Socket"
    cli = ["-b", "--bind"]
    meta = "ADDRESS"
    validator = validate_string
    default = "127.0.0.1:5000"
    desc = """\
        The socket to bind.
        
        A string of the form: 'HOST', 'HOST:PORT', 'unix:PATH'. An IP is a valid
        HOST.
        """
        
class Backlog(Setting):
    name = "backlog"
    section = "Server Socket"
    cli = ["--backlog"]
    meta = "INT"
    validator = validate_pos_int
    type = "int"
    default = 2048
    desc = """\
        The maximum number of pending connections.    
        
        This refers to the number of clients that can be waiting to be served.
        Exceeding this number results in the client getting an error when
        attempting to connect. It should only affect servers under significant
        load.
        
        Must be a positive integer. Generally set in the 64-2048 range.    
        """

class Workers(Setting):
    name = "workers"
    section = "Worker Processes"
    cli = ["-w", "--workers"]
    meta = "INT"
    validator = validate_pos_int
    type = "int"
    default = 1
    desc = """\
        The number of worker process for handling requests.
        
        A positive integer generally in the 2-4 x $(NUM_CORES) range. You'll
        want to vary this a bit to find the best for your particular
        application's work load.
        """
class WorkerConnections(Setting):
    name = "worker_connections"
    section = "Worker Processes"
    cli = ["--worker-connections"]
    meta = "INT"
    validator = validate_pos_int
    type = "int"
    default = 1000
    desc = """\
        The maximum number of simultaneous clients per worker.
        """

class Timeout(Setting):
    name = "timeout"
    section = "Worker Processes"
    cli = ["-t", "--timeout"]
    meta = "INT"
    validator = validate_pos_int
    type = "int"
    default = 30
    desc = """\
        Workers silent for more than this many seconds are killed and restarted.
        
        Generally set to thirty seconds. Only set this noticeably higher if
        you're sure of the repercussions for sync workers. For the non sync
        workers it just means that the worker process is still communicating and
        is not tied to the length of time required to handle a single request.
        """

class Daemon(Setting):
    name = "daemon"
    section = "Server Mechanics"
    cli = ["-D", "--daemon"]
    validator = validate_bool
    action = "store_true"
    default = False
    desc = """\
        Daemonize the tproxy process.
        
        Detaches the server from the controlling terminal and enters the
        background.
        """

class Pidfile(Setting):
    name = "pidfile"
    section = "Server Mechanics"
    cli = ["-p", "--pid"]
    meta = "FILE"
    validator = validate_string
    default = None
    desc = """\
        A filename to use for the PID file.
        
        If not set, no PID file will be written.
        """

class User(Setting):
    name = "user"
    section = "Server Mechanics"
    cli = ["-u", "--user"]
    meta = "USER"
    validator = validate_user
    default = os.geteuid()
    desc = """\
        Switch worker processes to run as this user.
        
        A valid user id (as an integer) or the name of a user that can be
        retrieved with a call to pwd.getpwnam(value) or None to not change
        the worker process user.
        """

class Group(Setting):
    name = "group"
    section = "Server Mechanics"
    cli = ["-g", "--group"]
    meta = "GROUP"
    validator = validate_group
    default = os.getegid()
    desc = """\
        Switch worker process to run as this group.
        
        A valid group id (as an integer) or the name of a user that can be
        retrieved with a call to pwd.getgrnam(value) or None to not change
        the worker processes group.
        """

class Umask(Setting):
    name = "umask"
    section = "Server Mechanics"
    cli = ["-m", "--umask"]
    meta = "INT"
    validator = validate_pos_int
    type = "int"
    default = 0
    desc = """\
        A bit mask for the file mode on files written by tproxy.
        
        Note that this affects unix socket permissions.
        
        A valid value for the os.umask(mode) call or a string compatible with
        int(value, 0) (0 means Python guesses the base, so values like "0",
        "0xFF", "0022" are valid for decimal, hex, and octal representations)
        """

class Logfile(Setting):
    name = "logfile"
    section = "Logging"
    cli = ["--log-file"]
    meta = "FILE"
    validator = validate_string
    default = "-"
    desc = """\
        The log file to write to.
        
        "-" means log to stdout.
        """

class Loglevel(Setting):
    name = "loglevel"
    section = "Logging"
    cli = ["--log-level"]
    meta = "LEVEL"
    validator = validate_string
    default = "info"
    desc = """\
        The granularity of log outputs.
        
        Valid level names are:
        
        * debug
        * info
        * warning
        * error
        * critical
        """

class LogConfig(Setting):
    name = "logconfig"
    section = "Logging"
    cli = ["--log-config"]
    meta = "FILE"
    validator = validate_string
    default = None 
    desc = """\
        The log config file to use.
        
        tproxy uses the standard Python logging module's Configuration
        file format.
        """

class Procname(Setting):
    name = "name"
    section = "Process Naming"
    cli = ["-n", "--name"]
    meta = "STRING"
    validator = validate_string
    default = None
    desc = """\
        A base to use with setproctitle for process naming.
        
        This affects things like ``ps`` and ``top``. If you're going to be
        running more than one instance of tproxy you'll probably want to set a
        name to tell them apart. This requires that you install the setproctitle
        module.
        
        It defaults to 'tproxy'.
        """

class SslKeyFile(Setting):
    name = "ssl_keyfile"
    section = "Ssl"
    cli = ["--ssl-keyfile"]
    validator = validate_string
    meta = "STRING"
    default = None
    desc = """\
        Ssl key file
        """

class SslCertFile(Setting):
    name = "ssl_certfile"
    section = "Ssl"
    cli = ["--ssl-certfile"]
    validator = validate_string
    meta = "STRING"
    default = None
    desc = """\
        Ssl cert file
        """

class SslCertFile(Setting):
    name = "ssl_certfile"
    section = "Ssl"
    cli = ["--ssl-certfile"]
    validator = validate_string
    meta = "STRING"
    default = None
    desc = """\
        Ssl ca certs file. contains concatenated "certification
        authority" certificates.
        """

class SslCACerts(Setting):
    name = "ssl_ca_certs"
    section = "Ssl"
    cli = ["--ssl-ca-certs"]
    validator = validate_string
    meta = "STRING"
    default = None
    desc = """\
        Ssl ca certs file. contains concatenated "certification
        authority" certificates.
        """

class SSLCertReq(Setting):
    name = "ssl_cert_reqs"
    section = "Ssl"
    cli = ["--ssl-cert-reqs"]
    validator = validate_pos_int
    meta = "INT"
    default = 0
    desc = """\
        Specifies whether a certificate is required from the other
        side of the connection, and whether it will be validated if
        provided. Values are: 0 (certificates ignored), 1 (not
        required, but validated if provided), 2 (required and
        validated).
        """


########NEW FILE########
__FILENAME__ = pidfile
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license. 
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
__FILENAME__ = proxy
# -*- coding: utf-8 -
#
# This file is part of tproxy released under the MIT license. 
# See the NOTICE for more information.

import errno
import logging
import os
import signal
import sys
import time

import gevent
from gevent.server import StreamServer
from gevent import socket

# we patch all
from gevent import monkey
monkey.noisy = False
monkey.patch_all()


from .client import ClientConnection
from .route import Route
from . import util

log = logging.getLogger(__name__)


class ProxyServer(StreamServer):

    def __init__(self, listener, script, backlog=None, 
            spawn='default', **sslargs):
        StreamServer.__init__(self, listener, backlog=backlog,
                spawn=spawn, **sslargs)
        
        self.script = script
        self.nb_connections = 0
        self.route = None
        self.rewrite_request = None
        self.rewrite_response = None

    def handle_quit(self, *args):
        """Graceful shutdown. Stop accepting connections immediately and
        wait as long as necessary for all connections to close.
        """
        gevent.spawn(self.stop)

    def handle_exit(self, *args):
        """ Fast shutdown.Stop accepting connection immediatly and wait
        up to 10 seconds for connections to close before forcing the
        termination
        """
        gevent.spawn(self.stop, 10.0)

    def handle_winch(self, *args):
        # Ignore SIGWINCH in worker. Fixes a crash on OpenBSD.
        return

    def pre_start(self):
        """ create socket if needed and bind SIGKILL, SIGINT & SIGTERM
        signals
        """
        # setup the socket
        if not hasattr(self, 'socket'):
            self.socket = tcp_listener(self.address, self.backlog)
            self.address = self.socket.getsockname()
        self._stopped_event.clear()

         # make SSL work:
        if self.ssl_enabled:
            self._handle = self.wrap_socket_and_handle
        else:
            self._handle = self.handle

        # handle signals
        signal.signal(signal.SIGQUIT, self.handle_quit)
        signal.signal(signal.SIGTERM, self.handle_exit)
        signal.signal(signal.SIGINT, self.handle_exit)
        signal.signal(signal.SIGWINCH, self.handle_winch)

    def init_route(self):
        if self.route is not None:
            return

        self.route = Route(self.script) 

    def start_accepting(self):
        self.init_route()
        super(ProxyServer, self).start_accepting()

    def handle(self, socket, address):
        """ handle the connection """
        conn = ClientConnection(socket, address, self)
        conn.handle()

    def wrap_socket_and_handle(self, client_socket, address):
        # used in case of ssl sockets
        ssl_socket = self.wrap_socket(client_socket, **self.ssl_args)
        return self.handle(ssl_socket, address)

def tcp_listener(address, backlog=None):
    backlog = backlog or 128

    if util.is_ipv6(address[0]):
        family = socket.AF_INET6
    else:
        family = socket.AF_INET

    bound = False
    if 'TPROXY_FD' in os.environ:
        fd = int(os.environ.pop('TPROXY_FD'))
        try:
            sock = socket.fromfd(fd, family, socket.SOCK_STREAM)
        except socket.error, e:
            if e[0] == errno.ENOTCONN:
                log.error("TPROXY_FD should refer to an open socket.")
            else:
                raise
        bound = True
    else:
        sock = socket.socket(family, socket.SOCK_STREAM)

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    for i in range(5):
        try:
            if not bound:
                sock.bind(address) 
            sock.setblocking(0)
            sock.listen(backlog)
            return sock
        except socket.error, e:
            if e[0] == errno.EADDRINUSE:
                log.error("Connection in use: %s" % str(address))
            if e[0] == errno.EADDRNOTAVAIL:
                log.error("Invalid address: %s" % str(address))
                sys.exit(1)
            if i < 5:
                log.error("Retrying in 1 second. %s" % str(e))
                time.sleep(1)

########NEW FILE########
__FILENAME__ = rewrite
# -*- coding: utf-8 -
#
# This file is part of tproxy released under the MIT license. 
# See the NOTICE for more information.

import sys

# backports socketio
import io
import inspect
import socket

try:
    import errno
except ImportError:
    errno = None
EBADF = getattr(errno, 'EBADF', 9)
EINTR = getattr(errno, 'EINTR', 4)
EAGAIN = getattr(errno, 'EAGAIN', 11)
EWOULDBLOCK = getattr(errno, 'EWOULDBLOCK', 11)

_blocking_errnos = ( EAGAIN, EWOULDBLOCK, EBADF)

if sys.version_info[:2] < (2, 7):
    # in python 2.6 socket.recv_into doesn't support bytesarray
    def _readinto(sock, b):
        while True:
            try:
                data = sock.recv(len(b))
                recved = len(data)
                b[0:recved] = data
                return recved
            except socket.error as e:
                n = e.args[0]
                
                if n == EINTR:
                    continue
                if n in _blocking_errnos:
                    return None
                raise
    _get_memory = buffer
else:
    _readinto = None
    def _get_memory(string, offset):
        return memoryview(string)[offset:]

class RewriteIO(io.RawIOBase):

    """Raw I/O implementation for stream sockets.

    It provides the raw I/O interface on top of a socket object.
    Backported from python 3.
    """


    def __init__(self, src, dest, buf=None):

        io.RawIOBase.__init__(self)
        self._src = src
        self._dest = dest

        if not buf:
            buf = []
        self._buf = buf
        
    def readinto(self, b):
        self._checkClosed()
        self._checkReadable()
        
        buf = bytes("".join(self._buf))

        if buf and buf is not None:
            l = len(b)
            if len(self._buf) > l:
                del b[l:]

                b[0:l], buf = buf[:l], buf[l:]
                self._buf = [buf]
                return len(b)
            else:
                length = len(buf)
                del b[length:]
                b[0:length] = buf
                self._buf = []
                return len(b) 

        if _readinto is not None:
            return _readinto(self._src, b)

        while True:
            try:
                return self._src.recv_into(b)
            except socket.error as e:
                n = e.args[0]
                if n == EINTR:
                    continue
                if n in _blocking_errnos:
                    return None
                raise

    def write(self, b):
        self._checkClosed()
        self._checkWritable()

        try:
            return self._dest.send(bytes(b))
        except socket.error as e:
            # XXX what about EINTR?
            if e.args[0] in _blocking_errnos:
                return None
            raise

    def writeall(self, b):
        sent = 0
        while sent < len(b):
            sent += self._dest.send(_get_memory(b, sent))

    def readable(self):
        """True if the SocketIO is open for reading.
        """
        return not self.closed

    def writable(self):
        """True if the SocketIO is open for writing.
        """
        return not self.closed
    
    def recv(self, n=None):
        return self.read(n)

    def send(self, b):
        return self.write(b)

    def sendall(self, b):
        return self.writeall(b)
        

class RewriteProxy(object):

    def __init__(self, src, dest, rewrite_fun, timeout=None,
            extra=None, buf=None):
        self.src = src
        self.dest = dest
        self.rewrite_fun = rewrite_fun
        self.timeout = timeout
        self.buf = buf
        self.extra = extra

    def run(self):
        pipe = RewriteIO(self.src, self.dest, self.buf) 
        spec = inspect.getargspec(self.rewrite_fun)
        try:
            if len(spec.args) > 1:
                self.rewrite_fun(pipe, self.extra)
            else:
                self.rewrite_fun(pipe)
        finally:
            pipe.close()



########NEW FILE########
__FILENAME__ = route
# -*- coding: utf-8 -
#
# This file is part of tproxy released under the MIT license. 
# See the NOTICE for more information.

import io
import logging

from .rewrite import RewriteProxy

class Route(object):
    """ toute object to handle real proxy """

    def __init__(self, script):
        if hasattr(script, "load"):
            self.script = script.load()
        else:
            self.script = script

        self.empty_buf = True
        if hasattr(self.script, 'rewrite_request'):
            self.proxy_input = self.rewrite_request
            self.empty_buf = False
        else:
            self.proxy_input = self.proxy_io

        if hasattr(self.script, 'rewrite_response'):
            self.proxy_connected = self.rewrite_response
        else:
            self.proxy_connected = self.proxy_io

        self.log = logging.getLogger(__name__)

    def proxy(self, data):
        return self.script.proxy(data)

    def proxy_io(self, src, dest, buf=None, extra=None):
        while True:
            data = src.recv(io.DEFAULT_BUFFER_SIZE)
            if not data: 
                break
            self.log.debug("got data from input")
            dest.sendall(data)

    def rewrite(self, src, dest, fun, buf=None, extra=None):
        rwproxy = RewriteProxy(src, dest, fun, extra=extra, buf=buf)
        rwproxy.run()

    def rewrite_request(self, src, dest, buf=None, extra=None):
        self.rewrite(src, dest, self.script.rewrite_request, buf=buf,
                extra=extra)
        
    def rewrite_response(self, src, dest, extra=None):
        self.rewrite(src, dest, self.script.rewrite_response, 
                extra=extra)

########NEW FILE########
__FILENAME__ = sendfile
# -*- coding: utf-8 -
#
# This file is part of tproxy released under the MIT license. 
# See the NOTICE for more information.

import errno
import io
import os
try:
    from os import sendfile
except ImportError:
    try:
        from _sendfile import sendfile
    except ImportError:
        def sendfile(fdout, fdin, offset, nbytes):
            fsize = os.fstat(fdin).st_size

            # max to send
            length = min(fsize-offset, nbytes)

            with os.fdopen(fdin) as fin:          
                fin.seek(offset)

                while length > 0:
                    l = min(length, io.DEFAULT_BUFFER_SIZE)
                    os.write(fdout, fin.read(l))
                    length = length - l

            return length

from gevent.socket import wait_write


def async_sendfile(fdout, fdin, offset, nbytes):
    total_sent = 0
    while total_sent < nbytes:
        try:
            sent = sendfile(fdout, fdin, offset + total_sent, 
                    nbytes - total_sent)
            total_sent += sent
        except OSError, e:
            if e.args[0] == errno.EAGAIN:
                wait_write(fdout)
            else:
                raise
    return total_sent

########NEW FILE########
__FILENAME__ = server
# -*- coding: utf-8 -
#
# This file is part of tproxy released under the MIT license. 
# See the NOTICE for more information.

import logging

import greenlet
import gevent
from gevent.event import Event
from gevent.pool import Group, Pool


class InactivityTimeout(Exception):
    """ Exception raised when the configured timeout elapses without
    receiving any data from a connected server """

class Peers(Group):
    """
    Peered greenlets. If one of greenlet is killed, all are killed. 
    """
    def discard(self, greenlet):
        super(Peers, self).discard(greenlet)
        if not hasattr(self, '_killing'):
            self._killing = True
            gevent.spawn(self.kill)

class ServerConnection(object):

    def __init__(self, sock, client, timeout=None, extra=None,
            buf=None):
        self.sock = sock
        self.timeout = timeout
        self.client = client
        self.extra = extra
        self.buf = buf

        self.route = client.route

        self.log = logging.getLogger(__name__)
        self._stopped_event = Event()
        
    def handle(self):
        """ start to relay the response
        """
        try:
            peers = Peers([
                gevent.spawn(self.route.proxy_input, self.client.sock,
                    self.sock, self.buf, self.extra),
                gevent.spawn(self.route.proxy_connected, self.sock, 
                    self.client.sock, self.extra)])
            gevent.joinall(peers.greenlets)
        finally:
            self.sock.close()

        
    def proxy_input(self, src, dest, buf, extra):
        """ proxy innput to the connected host
        """
        self.route.proxy_input(src, dest, buf=buf, extra=extra) 

    def proxy_connected(self, src, dest, extra):
        """ proxy the response from the connected host to the client
        """
        self.route.proxy_connected(src, dest, extra=extra) 

########NEW FILE########
__FILENAME__ = tools
# -*- coding: utf-8 -
#
# This file is part of tproxy released under the MIT license. 
# See the NOTICE for more information.


try:
    from importlibe import import_module
except ImportError:
    import sys
    
    def _resolve_name(name, package, level):
        """Return the absolute name of the module to be imported."""
        if not hasattr(package, 'rindex'):
            raise ValueError("'package' not set to a string")
        dot = len(package)
        for x in xrange(level, 1, -1):
            try:
                dot = package.rindex('.', 0, dot)
            except ValueError:
                raise ValueError("attempted relative import beyond top-level "
                                  "package")
        return "%s.%s" % (package[:dot], name)


    def import_module(name, package=None):
        """Import a module.

        The 'package' argument is required when performing a relative import. It
        specifies the package to use as the anchor point from which to resolve the
        relative import to an absolute import.

        """
        if name.startswith('.'):
            if not package:
                raise TypeError("relative imports require the 'package' argument")
            level = 0
            for character in name:
                if character != '.':
                    break
                level += 1
            name = _resolve_name(name[level:], package, level)
        __import__(name)
        return sys.modules[name]

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -
#
# This file is part of tproxy released under the MIT license. 
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
import random
import resource
import socket

# add support for gevent 1.0
from gevent import version_info
if version_info[0] >0:
    from gevent.os import fork
else:
    from gevent.hub import fork
    
try:
    from setproctitle import setproctitle
    def _setproctitle(title):
        setproctitle("tproxy: %s" % title) 
except ImportError:
    def _setproctitle(title):
        return

MAXFD = 1024
if (hasattr(os, "devnull")):
   REDIRECT_TO = os.devnull
else:
   REDIRECT_TO = "/dev/null"

def is_ipv6(addr):
    try:
        socket.inet_pton(socket.AF_INET6, addr)
    except socket.error: # not a valid address
        return False
    return True
        

def parse_address(netloc, default_port=5000):
    if isinstance(netloc, tuple):
        return netloc

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

def daemonize(close=False):
    """\
    Standard daemonization of a process.
    http://www.svbug.com/documentation/comp.unix.programmer-FAQ/faq_2.html#SEC16
    """
    if not 'TPROXY_FD' in os.environ:
        try:
            if fork():
                os._exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %s\n" % str(e))
            sys.exit(1)

        os.setsid()
        
        try:
            if fork():
                os._exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %s\n" % str(e))
            sys.exit(1)

        os.umask(0)
        
        if close:
            maxfd = get_maxfd()

            # Iterate through and close all file descriptors.
            for fd in range(0, maxfd):
                try:
                    os.close(fd)
                except OSError:	
                    # ERROR, fd wasn't open to begin with (ignored)
                    pass
        
        os.open(REDIRECT_TO, os.O_RDWR)
        os.dup2(0, 1)
        os.dup2(0, 2)

def seed():
    try:
        random.seed(os.urandom(64))
    except NotImplementedError:
        random.seed(random.random())

########NEW FILE########
__FILENAME__ = worker
# -*- coding: utf-8 -
#
# This file is part of tproxy released under the MIT license. 
# See the NOTICE for more information.

import os
import logging
import signal

import gevent
from gevent.pool import Pool
from gevent.ssl import wrap_socket


from . import util
from .proxy import ProxyServer
from .workertmp import WorkerTmp

class Worker(ProxyServer):

    SIGNALS = map(
        lambda x: getattr(signal, "SIG%s" % x),
        "HUP QUIT INT TERM USR1 USR2 WINCH CHLD".split()
    )

    PIPE = []

    def __init__(self, age, ppid, listener, cfg, script):
        ProxyServer.__init__(self, listener, script, 
                spawn=Pool(cfg.worker_connections))

        if cfg.ssl_keyfile and cfg.ssl_certfile:
            self.wrap_socket = wrap_socket
            self.ssl_args = dict(
                    keyfile = cfg.ssl_keyfile,
                    certfile = cfg.ssl_certfile,
                    server_side = True,
                    cert_reqs = cfg.ssl_cert_reqs,
                    ca_certs = cfg.ssl_ca_certs,
                    suppress_ragged_eofs=True,
                    do_handshake_on_connect=True)
            self.ssl_enabled = True

        self.name = cfg.name
        self.age = age
        self.ppid = ppid
        self.cfg = cfg
        self.tmp = WorkerTmp(cfg)
        self.booted = False
        self.log = logging.getLogger(__name__)

    def __str__(self):
        return "<Worker %s>" % self.pid

    @property
    def pid(self):
        return os.getpid()

    def init_process(self):
        #gevent doesn't reinitialize dns for us after forking
        #here's the workaround
        gevent.core.dns_shutdown(fail_requests=1)
        gevent.core.dns_init()

        util.set_owner_process(self.cfg.uid, self.cfg.gid)

        # Reseed the random number generator
        util.seed()

        # For waking ourselves up
        self.PIPE = os.pipe()
        map(util.set_non_blocking, self.PIPE)
        map(util.close_on_exec, self.PIPE)
        

        # Prevent fd inherientence
        util.close_on_exec(self.socket)
        util.close_on_exec(self.tmp.fileno())

        map(lambda s: signal.signal(s, signal.SIG_DFL), self.SIGNALS)
        self.booted = True

    def start_heartbeat(self):
        def notify():
            while self.started:
                gevent.sleep(self.cfg.timeout / 2.0)

                # If our parent changed then we shut down.
                if self.ppid != os.getppid():
                    self.log.info("Parent changed, shutting down: %s" % self)
                    return

                self.tmp.notify()

        return gevent.spawn(notify)

    def serve_forever(self):
        self.init_process()
        self.start_heartbeat()
        super(Worker, self).serve_forever()

    def refresh_name(self):
        title = "worker"
        if self.name is not None:
            title += " [%s]"
        title = "%s - handling %s connections" % (title, self.nb_connections)
        util._setproctitle(title)

    def stop_accepting(self):
        title = "worker"
        if self.name is not None:
            title += " [%s]"
        title = "%s - stop accepting" % title
        util._setproctitle(title)
        super(Worker, self).stop_accepting()

    def start_accepting(self):
        self.refresh_name() 
        super(Worker, self).start_accepting()

    def kill(self):
        """stop accepting."""
        self.started = False
        try:
            self.stop_accepting()
        finally:
            self.__dict__.pop('socket', None)
            self.__dict__.pop('handle', None)

########NEW FILE########
__FILENAME__ = workertmp
# -*- coding: utf-8 -
#
# This file is part of tproxy released under the MIT license. 
# See the NOTICE for more information.

import os
import tempfile

from . import util

class WorkerTmp(object):

    def __init__(self, cfg):
        old_umask = os.umask(cfg.umask)
        fd, name = tempfile.mkstemp(prefix="wtproxy-")
        
        # allows the process to write to the file
        util.chown(name, cfg.uid, cfg.gid)
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
__FILENAME__ = _sendfile
# -*- coding: utf-8 -
#
# This file is part of tproxy released under the MIT license. 
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
        'dragonfly'
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
            e = ctypess.get_errno()
            raise OSError(e, os.strerror(e))
        return sent

########NEW FILE########
