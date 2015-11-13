__FILENAME__ = app
# vim:ts=4:sw=4:expandtab
'''The main Application and Service classes
'''
import os
import gc
import cProfile
from OpenSSL import SSL
import socket
import traceback
import errno
from greenlet import greenlet

from diesel.hub import EventHub
from diesel import log, Connection, UDPSocket, Loop
from diesel.security import ssl_async_handshake
from diesel import runtime
from diesel.events import WaitPool


YES_PROFILE = ['1', 'on', 'true', 'yes']

class ApplicationEnd(Exception): pass

class Application(object):
    '''The Application represents diesel's main loop--
    the coordinating entity that runs all Services, Loops,
    Client protocol work, etc.
    '''
    def __init__(self, allow_app_replacement=False):
        assert (allow_app_replacement or runtime.current_app is None), "Only one Application instance per program allowed"
        runtime.current_app = self
        self.hub = EventHub()
        self.waits = WaitPool()
        self._run = False
        self._services = []
        self._loops = []

        self.running = set()

    def global_bail(self, msg):
        def bail():
            log.critical("ABORTING: {0}", msg)
            self.halt()
        return bail

    def run(self):
        '''Start up an Application--blocks until the program ends
        or .halt() is called.
        '''
        profile = os.environ.get('DIESEL_PROFILE', '').lower() in YES_PROFILE
        track_gc = os.environ.get('TRACK_GC', '').lower() in YES_PROFILE
        track_gc_leaks = os.environ.get('TRACK_GC_LEAKS', '').lower() in YES_PROFILE
        if track_gc:
            gc.set_debug(gc.DEBUG_STATS)
        if track_gc_leaks:
            gc.set_debug(gc.DEBUG_LEAK)

        self._run = True
        log.warning('Starting diesel <{0}>', self.hub.describe)

        for s in self._services:
            s.bind_and_listen()
            s.register(self)

        for l in self._loops:
            self.hub.schedule(l.wake)

        self.setup()

        def _main():
            while self._run:
                try:
                    self.hub.handle_events()
                except SystemExit:
                    log.warning("-- SystemExit raised.. exiting main loop --")
                    raise
                except KeyboardInterrupt:
                    log.warning("-- KeyboardInterrupt raised.. exiting main loop --")
                    break
                except ApplicationEnd:
                    log.warning("-- ApplicationEnd raised.. exiting main loop --")
                    break
                except Exception, e:
                    log.error("-- Unhandled Exception rose to main loop --")
                    log.error(traceback.format_exc())

            log.info('Ending diesel application')
            runtime.current_app = None

        def _profiled_main():
            log.warning("(Profiling with cProfile)")

            # NOTE: Scoping Issue:
            # Have to rebind _main to _real_main so it shows up in locals().
            _real_main = _main
            config = {'sort':1}
            statsfile = os.environ.get('DIESEL_PSTATS', None)
            if statsfile:
                config['filename'] = statsfile
            try:
                cProfile.runctx('_real_main()', globals(), locals(), **config)
            except TypeError, e:
                if "sort" in e.args[0]:
                    del config['sort']
                    cProfile.runctx('_real_main()', globals(), locals(), **config)
                else: raise e

        self.runhub = greenlet(_main if not profile else _profiled_main)
        self.runhub.switch()

    def add_service(self, service):
        '''Add a Service instance to this Application.

        The service will bind to the appropriate port and start
        handling connections when the Application is run().
        '''
        service.application = self
        if self._run:
            # TODO -- this path doesn't clean up binds yet
            service.bind_and_listen()
            service.register(self)
        else:
            self._services.append(service)

    def add_loop(self, loop, front=False, keep_alive=False, track=False):
        '''Add a Loop instance to this Application.

        The loop will be started when the Application is run().
        '''
        if track:
            loop.enable_tracking()

        if keep_alive:
            loop.keep_alive = True

        if self._run:
            self.hub.schedule(loop.wake)
        else:
            if front:
                self._loops.insert(0, loop)
            else:
                self._loops.append(loop)

    def halt(self):
        '''Stop this application from running--the initial run() call
        will return.
        '''
        for s in self._services:
            s.sock.close()
        raise ApplicationEnd()

    def setup(self):
        '''Do some initialization right before the main loop is entered.

        Called by run().
        '''
        pass

class Service(object):
    '''A TCP service listening on a certain port, with a protocol
    implemented by a passed connection handler.
    '''
    LQUEUE_SIZ = 500
    def __init__(self, connection_handler, port, iface='', ssl_ctx=None, track=False):
        '''Given a protocol-implementing callable `connection_handler`,
        handle connections on port `port`.

        Interface defaults to all interfaces, but overridable with `iface`.
        '''
        self.port = port
        self.iface = iface
        self.sock = None
        self.connection_handler = connection_handler
        self.application = None
        self.ssl_ctx = ssl_ctx
        self.track = track
        # Call this last so the connection_handler has a fully-instantiated
        # Service instance at its disposal.
        if hasattr(connection_handler, 'on_service_init'):
            if callable(connection_handler.on_service_init):
                connection_handler.on_service_init(self)

    def handle_cannot_bind(self, reason):
        log.critical("service at {0}:{1} cannot bind: {2}",
            self.iface or '*', self.port, reason)
        raise

    def register(self, app):
        app.hub.register(
            self.sock,
            self.accept_new_connection,
            None,
            app.global_bail("low-level socket error on bound service"),
        )

    def bind_and_listen(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(0)

        try:
            sock.bind((self.iface, self.port))
        except socket.error, e:
            self.handle_cannot_bind(str(e))

        sock.listen(self.LQUEUE_SIZ)
        self.sock = sock
        self.port = sock.getsockname()[1] # in case of 0 binds

    @property
    def listening(self):
        return self.sock is not None

    def accept_new_connection(self):
        try:
            sock, addr = self.sock.accept()
        except socket.error, e:
            code, s = e
            if code in (errno.EAGAIN, errno.EINTR):
                return
            raise
        sock.setblocking(0)
        def make_connection():
            c = Connection(sock, addr)
            l = Loop(self.connection_handler, addr)
            l.connection_stack.append(c)
            runtime.current_app.add_loop(l, track=self.track)
        if self.ssl_ctx:
            sock = SSL.Connection(self.ssl_ctx, sock)
            sock.set_accept_state()
            sock.setblocking(0)
            ssl_async_handshake(sock, self.application.hub, make_connection)
        else:
            make_connection()

class Thunk(object):
    def __init__(self, c):
        self.c = c
    def eval(self):
        return self.c()

class UDPService(Service):
    '''A UDP service listening on a certain port, with a protocol
    implemented by a passed connection handler.
    '''
    def __init__(self, connection_handler, port, iface=''):
        Service.__init__(self, connection_handler, port, iface)
        self.remote_addr = (None, None)

    def bind_and_listen(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # unsure if the following two lines are necessary for UDP
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(0)

        try:
            sock.bind((self.iface, self.port))
        except socket.error, e:
            self.handle_cannot_bind(str(e))

        self.sock = sock
        c = UDPSocket(self, sock)
        l = Loop(self.connection_handler)
        l.connection_stack.append(c)
        runtime.current_app.add_loop(l)

    def register(self, app):
        pass


def quickstart(*args, **kw):
    if '__app' in kw:
        app = kw.pop('__app')
    else:
        app = Application(**kw)
    args = list(args)
    for a in args:
        if isinstance(a, Thunk):
            a = a.eval()
        if isinstance(a, (list, tuple)):
            args.extend(a)
        elif isinstance(a, Service):
            app.add_service(a)
        elif isinstance(a, Loop):
            app.add_loop(a)
        elif callable(a):
            app.add_loop(Loop(a))
    app.run()

def quickstop():
    from runtime import current_app
    current_app.halt()

########NEW FILE########
__FILENAME__ = buffer
# vim:ts=4:sw=4:expandtab
class BufAny(object):
    pass

class Buffer(object):
    '''An input buffer.

    Allows socket data to be read immediately and buffered, but
    fine-grained byte-counting or sentinel-searching to be
    specified by consumers of incoming data.
    '''
    def __init__(self):
        self._atinbuf = []
        self._atterm = None
        self._atmark = 0
        
    def set_term(self, term):
        '''Set the current sentinel.

        `term` is either an int, for a byte count, or
        a string, for a sequence of characters that needs
        to occur in the byte stream.
        '''
        self._atterm = term

    def feed(self, data):
        '''Feed some data into the buffer.

        The buffer is appended, and the check() is run in case
        this append causes the sentinel to be satisfied.
        '''
        self._atinbuf.append(data)
        self._atmark += len(data)
        return self.check()

    def clear_term(self):
        self._atterm = None

    def check(self):
        '''Look for the next message in the data stream based on
        the current sentinel.
        '''
        ind = None
        all = None
        if self._atterm is BufAny:
            if self.has_data:
                return self.pop()
            return None
        if type(self._atterm) is int:
            if self._atmark >= self._atterm:
                ind = self._atterm
        elif self._atterm is None:
            return None
        else:
            all = ''.join(self._atinbuf)
            res = all.find(self._atterm)
            if res != -1:
                ind = res + len(self._atterm)
        if ind is None:
            return None
        self._atterm = None # this terminator was used
        if all is None:
            all = ''.join(self._atinbuf)
        use = all[:ind]
        new_all = all[ind:]
        self._atinbuf = [new_all]
        self._atmark = len(new_all)

        return use

    def pop(self):
        b = ''.join(self._atinbuf)
        self._atinbuf = []
        self._atmark = 0
        return b

    @property
    def has_data(self):
        return bool(self._atinbuf)

########NEW FILE########
__FILENAME__ = client
# vim:ts=4:sw=4:expandtab
import errno
import socket

class Client(object):
    '''An agent that connects to an external host and provides an API to
    return data based on a protocol across that host.
    '''
    def __init__(self, addr, port, ssl_ctx=None, timeout=None, source_ip=None): 
        self.ssl_ctx = ssl_ctx
        self.connected = False
        self.conn = None
        self.addr = addr
        self.port = port

        ip = self._resolve(self.addr)
        self._setup_socket(ip, timeout, source_ip)

    def _resolve(self, addr):
        from resolver import resolve_dns_name
        return resolve_dns_name(addr)

    def _setup_socket(self, ip, timeout, source_ip=None):
    
        from core import _private_connect
        remote_addr = (ip, self.port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(0)

        if source_ip:
            sock.bind((source_ip, 0))
    
        try:
            sock.connect(remote_addr)
        except socket.error, e:
            if e.args[0] == errno.EINPROGRESS:
                _private_connect(self, ip, sock, self.addr, self.port, timeout=timeout)
            else:
                raise

    def on_connect(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args, **kw):
        self.close()

    def close(self):
        '''Close the socket to the remote host.
        '''
        if not self.is_closed:
            self.conn.close()
            self.conn = None
            self.connected = True

    @property
    def is_closed(self):
        return not self.conn or self.conn.closed

class UDPClient(Client):
    def __init__(self, addr, port, source_ip=None):
        super(UDPClient, self).__init__(addr, port, source_ip = source_ip)

    def _setup_socket(self, ip, timeout, source_ip=None):
        from core import UDPSocket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(0)

        if source_ip:
            sock.bind((source_ip, 0))

        self.conn = UDPSocket(self, sock, ip, self.port)
        self.connected = True

    def _resolve(self, addr):
        return addr

    class remote_addr(object):
        def __get__(self, inst, other):
            return (inst.addr, inst.port)

        def __set__(self, inst, value):
            inst.addr, inst.port = value
    remote_addr = remote_addr()

########NEW FILE########
__FILENAME__ = console
"""A remote console into running diesel applications.

With the functions and classes in this module you can open remote Python
console sessions into your diesel applications. Technically, they aren't
remote because it is hardcoded to run over localhost. But they are remote
from a process point of view.

An application that wishes to provide a remote console only needs to import
and call the `install_console_signal_handler` function. That sets a handler
for the SIGTRAP signal that attempts to make a connection to a certain port
on localhost.

Running there should be this module's `main` function. It sends the SIGTRAP
to a specified PID and then waits for a connection.

This inversion of the typical client/server roles is to allow for easily
getting a console into one of many processes running on a host without having
to configure a persistent remote console port or service for each one.

The code also handles redirecting stdout for the console so that the results of
`print` statements and the like are sent to the connected console and not the
local stdout of the process. All other output to stdout will be directed to the
process's normal stdout.

"""
import code
import optparse
import os
import readline # for history feature side-effect
import signal
import struct
import sys

from cStringIO import StringIO


import diesel

from diesel.util import debugtools


port = 4299

def install_console_signal_handler():
    """Call this function to provide a remote console in your app."""
    def connect_to_user_console(sig, frame):
        diesel.fork_from_thread(application_console_endpoint)
    signal.signal(signal.SIGTRAP, connect_to_user_console)

class LocalConsole(code.InteractiveConsole):
    """A modified Python interpreter UI that talks to a remote console."""
    def runsource(self, source, filename=None):
        self.current_source = source.encode('utf-8')
        return code.InteractiveConsole.runsource(self, source, filename)

    def runcode(self, ignored_codeobj):
        if self.current_source:
            sz = len(self.current_source)
            header = struct.pack('>Q', sz)
            diesel.send("%s%s" % (header, self.current_source))
            self.current_source = None
            header = diesel.receive(8)
            (sz,) = struct.unpack('>Q', header)
            if sz:
                data = diesel.receive(sz)
                print data.rstrip()

def console_for(pid):
    """Sends a SIGTRAP to the pid and returns a console UI handler.

    The return value is meant to be passed to a diesel.Service.

    """
    os.kill(pid, signal.SIGTRAP)
    banner = "Remote console PID=%d" % pid
    def interactive(addr):
        remote_console = LocalConsole()
        remote_console.interact(banner)
        diesel.quickstop()
    return interactive


class RemoteConsoleService(diesel.Client):
    """Runs the backend console."""
    def __init__(self, *args, **kw):
        self.interpreter = BackendInterpreter({
            'diesel':diesel,
            'debugtools':debugtools,
        })
        super(RemoteConsoleService, self).__init__(*args, **kw)

    @diesel.call
    def handle_command(self):
        header = diesel.receive(8)
        (sz,) = struct.unpack('>Q', header)
        data = diesel.receive(sz)
        stdout_patch = StdoutDispatcher()
        with stdout_patch:
            self.interpreter.runsource(data)
        output = stdout_patch.contents
        outsz = len(output)
        outheader = struct.pack('>Q', outsz)
        diesel.send("%s%s" % (outheader, output))

class BackendInterpreter(code.InteractiveInterpreter):
    def write(self, data):
        sys.stdout.write(data)

def application_console_endpoint():
    """Connects to the console UI and runs until disconnected."""
    diesel.sleep(1)
    try:
        session = RemoteConsoleService('localhost', port)
    except diesel.ClientConnectionError:
        diesel.log.error('Failed to connect to local console')
    else:
        diesel.log.warning('Connected to local console')
        with session:
            while True:
                try:
                    session.handle_command()
                except diesel.ClientConnectionClosed:
                    diesel.log.warning('Disconnected from local console')
                    break

class StdoutDispatcher(object):
    """Dispatches calls to stdout to fake or real file-like objects.

    The creator of an instance will receive the fake file-like object and
    all others will receive the original stdout instance.

    """
    def __init__(self):
        self.owning_loop = diesel.core.current_loop.id
        self._orig_stdout = sys.stdout
        self._fake_stdout = StringIO()

    def __getattr__(self, name):
        if diesel.core.current_loop.id == self.owning_loop:
            return getattr(self._fake_stdout, name)
        else:
            return getattr(self._orig_stdout, name)

    def __enter__(self):
        sys.stdout = self
        return self

    def __exit__(self, *args):
        sys.stdout = self._orig_stdout

    @property
    def contents(self):
        return self._fake_stdout.getvalue()

def main():
    parser = optparse.OptionParser("Usage: %prog PID")
    parser.add_option(
        '-p', '--port', default=port, type="int",
        help="The port to listen on for console connections",
    )
    options, args = parser.parse_args()
    if not args:
        parser.print_usage()
        raise SystemExit(1)
    if args[0] == 'dummy':
        print "PID", os.getpid()
        def wait_for_signal():
            log = diesel.log.name('dummy')
            log.min_level = diesel.loglevels.INFO
            install_console_signal_handler()
            while True:
                log.info("sleeping")
                diesel.sleep(5)
        diesel.quickstart(wait_for_signal)
    else:
        pid = int(args[0])
        svc = diesel.Service(console_for(pid), options.port)
        diesel.quickstart(svc)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = client
from uuid import uuid4
from itertools import chain
from diesel import Client, fork, call, send, until_eol
from diesel.util.queue import Queue
import random

nodeid = str(uuid4())

class ConvoyGetRequest(object):
    def __init__(self, key):
        self.key = key

class ConvoySetRequest(object):
    def __init__(self, key, value, cap, timeout, lock):
        self.key = key
        self.value = value
        self.cap = cap
        self.timeout = timeout
        self.lock = lock

class ConvoyWaitRequest(object):
    def __init__(self, timeout, clocks):
        self.timeout = timeout
        self.clocks = clocks

class ConvoyAliveRequest(object):
    pass

class ConvoyNameService(object):
    def __init__(self, servers):
        self.servers = servers
        self.request_queue = Queue()
        self.pool_locks = {}

    def __call__(self):
        while True:
            server = random.choice(self.servers)
            with ConvoyConsensusClient(*server) as client:
                while True:
                    req, rq = self.request_queue.get()
                    if type(req) is ConvoyGetRequest:
                        resp = client.get(req.key)
                    elif type(req) is ConvoySetRequest:
                        resp = client.add_to_set(req.key, req.value, req.cap, req.timeout, req.lock)
                    elif type(req) is ConvoyWaitRequest:
                        resp = client.wait(req.timeout, req.clocks)
                    elif type(req) is ConvoyAliveRequest:
                        resp = client.keep_alive()
                    else:
                        assert 0
                    rq.put(resp)

    def lookup(self, key):
        rq = Queue()
        self.request_queue.put((ConvoyGetRequest(key), rq))
        return rq.get()

    def clear(self, key):
        rq = Queue()
        self.request_queue.put((ConvoySetRequest(key, None, 0, 5, 0), rq))
        return rq.get()

    def set(self, key, value):
        rq = Queue()
        self.request_queue.put((ConvoySetRequest(key, value, 0, 5, 0), rq))
        return rq.get()

    def add(self, key, value, cap, to=0):
        rq = Queue()
        self.request_queue.put((ConvoySetRequest(key, value, cap, to, 1), rq))
        return rq.get()

    def wait(self, timeout, clocks):
        rq = Queue()
        self.request_queue.put((ConvoyWaitRequest(timeout, clocks), rq))
        return rq.get()

    def alive(self):
        rq = Queue()
        self.request_queue.put((ConvoyAliveRequest(), rq))
        return rq.get()

class ConsensusSet(object):
    def __init__(self, l, clock=None):
        self.members = set(l)
        self.clock = clock

    def __repr__(self):
        return "consensus-set <%s @ %s>" % (
                ','.join(self.members), self.clock)

class ConvoySetFailed(object): 
    def __init__(self, set=None):
        self.set = set

class ConvoySetTimeout(ConvoySetFailed): 
    pass

class ConvoyWaitTimeout(object):
    pass

class ConvoyWaitDone(object):
    def __init__(self, key):
        self.key = key

class ConvoyConsensusClient(Client):
    '''low-level client; use the cluster abstraction'''
    @call
    def on_connect(self):
        send("CLIENT\r\n")
        send("HI %s\r\n" % nodeid)
        assert until_eol().strip().upper() == "HI-HOLA"

    @call
    def wait(self, timeout, clocks):
        parts = chain([timeout], 
                *clocks.iteritems())
        rest = ' '.join(map(str, parts))
        send("BLOCKON " + rest + "\r\n")

        response = until_eol().strip()
        parts = response.split()
        result, rest = parts[0].upper(), parts[1:]
        if result == "BLOCKON-DONE":
            return ConvoyWaitDone(rest[0])
        assert result == "BLOCKON-TIMEOUT"
        return ConvoyWaitTimeout()

    @call
    def get(self, key):
        send("GET %s\r\n" % key)
        response = until_eol().strip()
        parts = response.split()
        result, rest = parts[0].upper(), parts[1:]
        if result == "GET-MISSING":
            return ConsensusSet([])
        elif result == "GET-NULL":
            clock = rest[0]
            return ConsensusSet([], clock)
        else:
            assert result == "GET-VALUE"
            clock = rest[0]
            values = rest[1:]
            return ConsensusSet(values, clock)

    @call
    def add_to_set(self, key, value, cap, timeout, lock):
        send("SET %s %s %s %s %s\r\n" % (
            key, value or '_', cap, timeout, int(lock)))
        response = until_eol().strip()

        parts = response.split()
        result, rest = parts[0].upper(), parts[1:]

        if result == 'SET-TIMEOUT':
            if timeout == 0:
                cls = ConvoySetFailed
            else:
                cls = ConvoySetTimeout
            if rest:
                clock = rest[0]
                values = rest[1:]
                return cls(ConsensusSet(values, clock))
            else:
                return cls()
        else:
            assert result == "SET-OKAY"
            clock = rest[0]
            values = rest[1:]
            return ConsensusSet(values, clock)

    @call
    def keep_alive(self):
        send("KEEPALIVE\r\n")
        assert until_eol().strip().upper() == "KEEPALIVE-OKAY"

cargo = ConvoyNameService([('localhost', 1111), ('localhost', 1112), ('localhost', 1113)])

if __name__ == '__main__':
    def run():
        print cargo.clear("foo")
        print cargo.set("foo", "bar")
        print cargo.lookup("foo")
        quickstop()
    from diesel import quickstart, quickstop
    quickstart(cargo, run)


########NEW FILE########
__FILENAME__ = server
from collections import defaultdict
import sys
import random
import uuid
import time
import hashlib
from itertools import chain, izip

from diesel import (until_eol, send, log,
        quickstart, Service, first, fork, 
        Client, ClientConnectionError, call, sleep,
        Thunk)
from diesel.logmod import LOGLVL_DEBUG
from diesel.util.event import Event
from diesel.util.queue import Queue

instance = uuid.uuid4().hex
clog = None
proposal_id = 0

def update_id(inid):
    int_id = int(inid.split('.')[0])
    global proposal_id
    if inid > proposal_id:
        proposal_id = int_id + random.randint(0, 10)

def lamport_id():
    global proposal_id
    while True:
        proposal_id += 1
        yield '%030d.%s' % (proposal_id, instance)

idgen = lamport_id()

def init_group(hostconfig):
    global clog
    global group
    clog = log.sublog("consensus-server", LOGLVL_DEBUG)
    group = HostGroup(hostconfig)

class StoredValue(object):
    def __init__(self, v, proposal_id):
        assert proposal_id is not None
        self.v = v
        self.proposal_id = proposal_id
        self.transactions = set()

    def __cmp__(self, other):
        if other is None:
            return cmp(1, None)
        return cmp(self.proposal_id, other.proposal_id)

    def __repr__(self):
        return str((self.v, self.proposal_id, self.transactions))

    def __hash__(self):
        return hash((self.v, self.proposal_id))

    def to_peer_wire(self):
        return ' '.join(encode_nulls((self.v, self.proposal_id)))

    def to_sync_atoms(self):
        return [self.proposal_id, self.v or '_'] + list(chain(*self.transactions))

    @classmethod
    def from_peer_wire(cls, w):
        v, pid = make_nulls(w.split())
        return cls(v, pid)

class Storage(dict):
    def __init__(self):
        dict.__init__(self)
        self._watches = defaultdict(set)
        self._pfx_watches = defaultdict(set)

    def fire_triggers(self, key):
        if key in self._watches:
            trigs = self._watches.pop(key)
            for t in trigs:
                t.set()

        for k, trigs in self._pfx_watches.items():
            if key.startswith(k):
                for t in trigs:
                    t.set()
                del self._pfx_watches[k]

    def watch(self, key, trigger):
        self._watches[key].add(trigger)

    def watch_prefix(self, prefix, trigger):
        self._pfx_watches[prefix].add(trigger)

    def set(self, key, val):
        self[key] = val
        self.fire_triggers(key)

    def maybe_remove(self, key, rollback):
        if key in self and self[key].v is not None and rollback in self[key].v:
            return self[key].v.replace(rollback, '')
        return None

    def get_with_prefix(self, pfx):
        for k, v in self.iteritems():
            if k.startswith(pfx):
                yield k, v

store = Storage()
proposals = Storage()

class LockManager(object):
    TIMEOUT = 20 # XXX
    def __init__(self):
        self.clients = {}

    def touch_clients(self, cs):
        for c in cs:
            if c in self.clients:
                self.clients[c] = time.time(), self.clients[c][-1]

    def add_lock(self, clientid, key, rollback):
        if clientid not in self.clients:
            self.clients[clientid] = (None, [])
        (_, l) = self.clients[clientid]
        l.append((key, rollback))
        self.clients[clientid] = time.time(), l

    def scan(self):
        now = time.time()
        for cid, (t, ls) in self.clients.items():
            if now - t > self.TIMEOUT:
                nls = []
                for l, rollback in ls:
                    new = store.maybe_remove(l, rollback)
                    if new is not None:
                        fork(
                        group.network_set,
                        None, l, new, None,
                        )
                        nls.append((l, rollback))
                    if (cid, rollback) in store[l].transactions:
                        store[l].transactions.remove((cid, rollback))
                if nls:
                    self.clients[cid] = (t, nls)
                else:
                    del self.clients[cid]

    def __call__(self):
        while True:
            sleep(5)
            self.scan()

locker = LockManager()


class HostGroup(object):
    '''Abstraction of host group participating in consensus
    '''
    def __init__(self, hosts):
        self.hosts = hosts
        self.num_hosts = len(self.hosts)
        assert self.num_hosts % 2 == 1
        self.quorum_size = (self.num_hosts / 2) + 1
        clog.info("host group of size %s requiring quorum_size of %s" % (
            self.num_hosts, self.quorum_size))

        self.proposal_qs = []
        self.save_qs = []
        self.get_qs = []

    def __call__(self):
        for h, p in self.hosts:
            pq = Queue()
            sq = Queue()
            gq = Queue()
            fork(manage_peer_connection, h, p, pq, sq, gq)
            self.proposal_qs.append(pq)
            self.save_qs.append(sq)
            self.get_qs.append(gq)

    def network_set(self, client, key, value, new):
        proposal_id = idgen.next()
        resq = Queue()
        if new:
            rollback = '|' + new + ':' + proposal_id
            value += rollback
        else:
            rollback = None

        for q in self.proposal_qs:
            q.put((proposal_id, key, resq))

        success = 0
        while True: # XXX timeout etc
            v = resq.get()
            if v == PROPOSE_SUCCESS:
                success += 1
                if success == self.quorum_size:
                    break
            elif v == PROPOSE_FAIL:
                return None
            else:
                assert 0

        for q in self.save_qs:
            q.put((proposal_id, key, value, client, rollback, resq))

        success = 0
        while True: # XXX timeout etc
            v = resq.get()
            if v == PROPOSE_SUCCESS:
                pass # don't care
            elif v == PROPOSE_FAIL:
                pass # don't care
            elif v == SAVE_SUCCESS:
                success += 1
                if success == self.quorum_size:
                    return proposal_id
            else:
                assert 0

    def network_get(self, key):
        answers = defaultdict(int)
        resq = Queue()

        for gq in self.get_qs:
            gq.put((key, resq))

        ans = None

        # XXX - timeout
        for x in xrange(self.num_hosts):
            value = resq.get()
            answers[value] += 1
            if answers[value] == self.quorum_size:
                ans = value
                break

        if ans is not None and (key not in store or store[key].proposal_id < ans.proposal_id):
            clog.error("read-repair %s" % ans)
            store.set(key, ans)

        return ans



(
PROPOSE_SUCCESS,
PROPOSE_FAIL,
SAVE_SUCCESS,
) = range(3)


class Timer(object):
    def __init__(self, every, start=True):
        self.every = every
        self.last_fire = 0 if start else time.time()

    @property
    def till_due(self):
        return max(0, (self.last_fire + self.every) - time.time())

    @property
    def is_due(self):
        return self.till_due == 0

    def touch(self):
        self.last_fire = time.time()

def manage_peer_connection(host, port, proposals, saves, gets):
    import traceback
    sleep_time = 0.2
    client_alive_timer = Timer(5.0)
    while True:
        try:
            with PeerClient(host, port) as peer:
                peer.signon()
                peer.sync()
                sleep_time = 0.2
                while True:
                    if client_alive_timer.is_due:
                        peer.keep_clients_alive()
                        client_alive_timer.touch()
                    e, v = first(sleep=client_alive_timer.till_due, waits=[proposals, saves, gets])
                    if e == proposals:
                        id, key, resp = v
                        try:
                            resp.put(PROPOSE_SUCCESS
                                    if peer.propose(id, key)
                                    else PROPOSE_FAIL)
                        except:
                            proposals.put(v) # retry
                            raise
                    elif e == saves:
                        id, key, value, client, rollback, resp = v
                        try:
                            peer.save(id, key, value, client, rollback)
                            resp.put(SAVE_SUCCESS)
                        except:
                            saves.put(v) # retry
                            raise
                    elif e == gets:
                        key, resp = v
                        try:
                            v = peer.get(key)
                            resp.put(v)
                        except:
                            gets.put(v) # retry
                            raise

        except ClientConnectionError, e:
            clog.error("Connection problem to (%s, %s): %s" % (
                host, port, e))
            sleep(sleep_time)
            sleep_time *= 2
            sleep_time = min(sleep_time, 5.0)
        except:
            clog.error("Error in peer connection to (%s, %s):\n%s" % (
                host, port, traceback.format_exc()))
            sleep(sleep_time)
            sleep_time *= 2
            sleep_time = min(sleep_time, 5.0)

class PeerClient(Client):
    @call
    def signon(self):
        send("PEER\r\n")
        assert until_eol().strip().upper() == "PEER-HOLA"

    @call
    def sync(self):
        for k, v in store.iteritems():
            send("SYNC %s %s\r\n" % (
                (k, ' '.join(v.to_sync_atoms()))))

    @call
    def propose(self, id, key):
        send("PROPOSE %s %s\r\n" % (
        id, key))
        res = until_eol().strip().upper()
        return res == "ACCEPT"

    @call
    def save(self, id, key, value, client, rollback):
        send("SAVE %s %s %s %s %s\r\n" % (id, key, value or '_', client or '_', rollback or '_'))
        res = until_eol().strip().upper()
        assert res == "SAVED"

    @call
    def get(self, key):
        send("PEER-GET %s\r\n" % (key,))
        res = until_eol().strip()
        parts = res.split(None, 1)
        cmd = parts[0].upper()

        if cmd == 'PEER-GET-MISSING':
            return None
        else:
            assert cmd == 'PEER-GET-VALUE'
            rest = parts[1]
            value = StoredValue.from_peer_wire(rest)
            return value

    @call
    def keep_clients_alive(self):
        alive = []
        TIMEOUT = 15 # XXX
        now = time.time()
        for c, t in clients.items():
            if c is None or time.time() - t > TIMEOUT:
                del clients[c]

        send("PEER-KEEPALIVE %s\r\n" % (
            ' '.join(clients)))
        res = until_eol().strip().upper()
        assert res == "PEER-KEEPALIVE-OKAY"

cmd_registry = {}

clients = {}

def command(n):
    def cmd_deco(f):
        assert n not in cmd_registry
        cmd_registry[n] = f
        return f
    return cmd_deco

def make_nulls(l): 
    return [i if i != '_' else None for i in l]

def encode_nulls(l):
    return [str(i) if i is not None else '_' for i in l]


class CommonHandler(object):
    def send_header(self, cmd, *args):
        out = ' '.join([cmd.upper()] + map(str, args)) + '\r\n'
        send(out)

    def get_command_header(self):
        line = until_eol().strip("\r\n")
        atoms = line.split()
        cmd = atoms[0].upper()
        args = make_nulls(atoms[1:])

        return cmd, args

class PeerHandler(CommonHandler):
    @command("PROPOSE")
    def handle_propose(self, id, key):
        update_id(id)
        if key in proposals or (key in store and store[key].proposal_id >= id):
            self.send_header("REJECT")
        else:
            proposals[key] = id
            self.send_header("ACCEPT") # timeout proposals?

    @command("SAVE")
    def handle_save(self, id, key, value, owner, rollback):
        if key not in store or store[key].proposal_id < id:
            value = StoredValue(value, id)
            store.set(key, value)
            if owner:
                assert rollback
                locker.add_lock(owner, key, rollback)
                store[key].transactions.add((owner, rollback))
        if key in proposals:
            del proposals[key]
        self.send_header("SAVED")

    @command("SYNC")
    def handle_sync(self, key, id, value, *owners):
        update_id(id)
        if key not in store or id > store[key].proposal_id:
            ans = StoredValue(value, id)
            store.set(key, ans)
            for owner, rollback in izip(owners[::2], owners[1::2]):
                locker.add_lock(owner, key, rollback)
                store[key].transactions.add((owner, rollback))
            clog.error("sync-repair %s" % ans)

    @command("PEER-KEEPALIVE")
    def handle_peer_keepalive(self, *args):
        locker.touch_clients(args)
        self.send_header("PEER-KEEPALIVE-OKAY")

    @command("PEER-GET")
    def handle_peer_get(self, key):
        v = store.get(key)
        if v is None:
            self.send_header("PEER-GET-MISSING")
        else:
            self.send_header("PEER-GET-VALUE", v.to_peer_wire())

    def __call__(self, *args):
        self.send_header("PEER-HOLA")
        while True:
            cmd, args = self.get_command_header()
            cmd_registry[cmd](self, *args)

class ClientQuit(Exception): pass

class ClientHandler(CommonHandler):
    def __call__(self, *args):
        self.client_id = self.handle_hi()
        clients[self.client_id] = time.time()

        while True:
            cmd, args = self.get_command_header()
            try:
                cmd_registry[cmd](self, *args)
            except ClientQuit:
                break

    def handle_hi(self):
        line = until_eol().strip()
        atoms = line.split()
        cmd = atoms[0].upper()
        if cmd == "QUIT": return
        assert cmd == "HI"
        assert len(atoms) == 2
        client_id = atoms[1]

        self.send_header("HI-HOLA")

        return client_id

    def make_array(self, l):
        return tuple(i.split(':', 1)[0] for i in l.split('|')[1:])

    @command("GET")
    def handle_get(self, key):
        v = group.network_get(key)
        if v is None:
            self.send_header("GET-MISSING")
        elif v.v is None:
            self.send_header("GET-NULL", v.proposal_id)
        else:
            self.send_header("GET-VALUE", v.proposal_id, *self.make_array(v.v))

    @command("BLOCKON")
    def handle_blockon(self, timeout, *args):
        valmap = dict(izip(args[0::2], args[1::2]))
        timeout = float(timeout)
        blocktimer = Timer(timeout, start=False)
        blockevent = Event()
        while True:
            for v, pid in valmap.iteritems():
                if v in store and store[v].proposal_id != pid:
                    return self.send_header("BLOCKON-DONE", v)

            if blocktimer.is_due:
                self.send_header("BLOCKON-TIMEOUT")
                return

            for v in valmap:
                store.watch(v, blockevent)

            ev, _ = first(sleep=blocktimer.till_due, waits=[blockevent])

    def send_set_response(self, code, key):
        v = group.network_get(key)
        if v:
            self.send_header(code, v.proposal_id, *self.make_array(v.v))
        else:
            self.send_header(code)

    @command("SET")
    def handle_set(self, key, addition, members, timeout, lock):
        members = int(members)
        lock = int(lock)
        timeout = float(timeout)
        start = time.time()

        if addition is None:
            assert members == 0
            assert lock == 0
        else:
            assert '|' not in addition
            assert ':' not in addition

        while True:
            existing_value = group.network_get(key)
            if members and existing_value and existing_value.v is not None:
                pfx = existing_value.v
            else:
                pfx = ''

            blocked = False
            if members == 0 or pfx.count('|') < members:
                blocked = True
                pid = group.network_set(self.client_id if lock else None, key, pfx if addition else None, addition)
                if pid:
                    return self.send_set_response("SET-OKAY", key)

            left = (start + timeout) - time.time()
            if left <= 0:
                return self.send_set_response("SET-TIMEOUT", key)

            if blocked and key in store and store[key].proposal_id != existing_value.proposal_id:
                continue # value has changed already, let's try again

            trigger = Event()
            store.watch(key, trigger)
            ev, val = first(sleep=left, waits=[trigger])

            if ev != trigger:
                return self.send_set_response("SET-TIMEOUT", key)

    @command("KEEPALIVE")
    def handle_keepalive(self):
        clients[self.client_id] = time.time()
        self.send_header("KEEPALIVE-OKAY")

    @command("QUIT")
    def handle_quit(self):
        raise ClientQuit()

def handle_client(*args):
    type = until_eol().strip().upper()
    if type == "CLIENT":
        return ClientHandler()()
    elif type == "PEER":
        assert PeerHandler()()
    elif type == "QUIT":
        pass
    else:
        assert 0, "unknown connection type"

def run_server(me, cluster):
    init_group(cluster)
    port = int(me.split(':')[-1])
    return [locker, group, Service(handle_client, port)]

########NEW FILE########
__FILENAME__ = messagenet
import os
from struct import pack, unpack

from .convoy_env_palm import MessageResponse, MessageEnvelope
from diesel import Client, call, send, receive, Service
import traceback

MESSAGE_OUT = 1
MESSAGE_RES = 2

class ConvoyId(object):
    def __init__(self):
        id = None
me = ConvoyId()

def host_loop(host, q):
    h, p = host.split('/')
    p = int(p)
    client = None
    while True:
        env, typ, cb = q.get()
        try:
            if not client:
                client = MessageClient(h, p)
            client.send_message(env, typ)
        except:
            traceback.print_exc()
            client.close()
            client = None
            if cb:
                cb()

class MessageClient(Client):
    @call
    def send_message(self, env, typ):
        out = env.dumps()
        send(pack('=II', typ, len(out)))
        send(out)

def handle_conn(*args):
    from diesel.convoy import convoy
    while True:
        head = receive(8)
        typ, size = unpack('=II', head)
        body = receive(size)
        if typ == MESSAGE_OUT:
            env = MessageEnvelope(body)
            convoy.local_dispatch(env)
        else:
            resp = MessageResponse(body)
            convoy.local_response(resp)

class ConvoyService(Service):
    def __init__(self):
        Service.__init__(self, handle_conn, 0)

    def bind_and_listen(self):
        Service.bind_and_listen(self)

        me.id = '%s/%s' % (os.uname()[1], self.port)

########NEW FILE########
__FILENAME__ = core
# vim:ts=4:sw=4:expandtab
'''Core implementation/handling of coroutines, protocol primitives,
scheduling primitives, green-thread procedures.
'''
import os
import socket
import traceback
import errno
import sys
import itertools
from collections import deque
from OpenSSL import SSL
from greenlet import greenlet

from diesel import pipeline
from diesel import buffer
from diesel.security import ssl_async_handshake
from diesel import runtime
from diesel import log
from diesel.events import EarlyValue

class ConnectionClosed(socket.error):
    '''Raised if the client closes the connection.
    '''
    def __init__(self, msg, buffer=None):
        socket.error.__init__(self, msg)
        self.buffer = buffer

class ClientConnectionClosed(socket.error):
    '''Raised if the remote server (for a Client call)
    closes the connection.
    '''
    def __init__(self, msg, buffer=None, addr=None, port=None):
        socket.error.__init__(self, msg)
        self.buffer = buffer
        self.addr = addr
        self.port = port

    def __str__(self):
        s = socket.error.__str__(self)
        if self.addr and self.port:
            s += ' (addr=%s, port=%s)' % (self.addr, self.port)
        return s

class ClientConnectionError(socket.error):
    '''Raised if a client cannot connect.
    '''

class ClientConnectionTimeout(socket.error):
    '''Raised if the client connection timed out before succeeding.
    '''

class LoopKeepAlive(Exception):
    '''Raised when an exception occurs that causes a loop to terminate;
    allows the app to re-schedule keep_alive loops.
    '''

class ParentDiedException(Exception):
    '''Raised when the parent (assigned via fork_child) has died.
    '''

class TerminateLoop(Exception):
    '''Raised to terminate the current loop, closing the socket if there
    is one associated with the loop.
    '''

CRLF = '\r\n'
BUFSIZ = 2 ** 14

def until(*args, **kw):
    return current_loop.input_op(*args, **kw)

def until_eol():
    return until("\r\n")

class datagram(object):
    pass
datagram = datagram()
_datagram = datagram


def receive(*args, **kw):
    return current_loop.input_op(*args, **kw)

def send(*args, **kw):
    return current_loop.send(*args, **kw)

def wait(*args, **kw):
    return current_loop.wait(*args, **kw)

def fire(*args, **kw):
    return current_loop.fire(*args, **kw)

def sleep(*args, **kw):
    return current_loop.sleep(*args, **kw)

def thread(*args, **kw):
    return current_loop.thread(*args, **kw)

def _private_connect(*args, **kw):
    return current_loop.connect(*args, **kw)

def first(*args, **kw):
    return current_loop.first(*args, **kw)

def label(*args, **kw):
    return current_loop.label(*args, **kw)

def fork(*args, **kw):
    return current_loop.fork(False, *args, **kw)

def fork_child(*args, **kw):
    return current_loop.fork(True, *args, **kw)

def fork_from_thread(f, *args, **kw):
    l = Loop(f, *args, **kw)
    runtime.current_app.hub.schedule_loop_from_other_thread(l, ContinueNothing)

def signal(sig, callback=None):
    if not callback:
        return current_loop.signal(sig)
    else:
        return current_loop._signal(sig, callback)

class call(object):
    def __init__(self, f, inst=None):
        self.f = f
        self.client = inst

    def __get__(self, inst, cls):
        return call(self.f, inst)

    def __call__(self, *args, **kw):
        try:
            if not self.client.connected:
                raise ConnectionClosed(
                        "ClientNotConnected: client is not connected")
            if self.client.is_closed:
                raise ConnectionClosed(
                        "Client call failed: client connection was closed")
            current_loop.connection_stack.append(self.client.conn)
            try:
                r = self.f(self.client, *args, **kw)
            finally:
                current_loop.connection_stack.pop()
        except ConnectionClosed, e:
            raise ClientConnectionClosed(str(e), addr=self.client.addr, port=self.client.port)
        return r

current_loop = None

ContinueNothing = object()

def identity(cb): return cb

ids = itertools.count(1)

class Loop(object):
    def __init__(self, loop_callable, *args, **kw):
        self.loop_callable = loop_callable
        self.loop_label = str(self.loop_callable)
        self.args = args
        self.kw = kw
        self.keep_alive = False
        self.hub = runtime.current_app.hub
        self.app = runtime.current_app
        self.id = ids.next()
        self.children = set()
        self.parent = None
        self.deaths = 0
        self.reset()
        self._clock = 0.0
        self.clock = 0.0
        self.tracked = False
        self.dispatch = self._dispatch

    def reset(self):
        self.running = False
        self._wakeup_timer = None
        self.fire_handlers = {}
        self.fire_due = False
        self.connection_stack = []
        self.coroutine = None

    def enable_tracking(self):
        self.tracked = True
        self.dispatch = self._dispatch_track

    def run(self):
        from diesel.app import ApplicationEnd
        self.running = True
        self.app.running.add(self)
        parent_died = False
        try:
            self.loop_callable(*self.args, **self.kw)
        except TerminateLoop:
            pass
        except (SystemExit, KeyboardInterrupt, ApplicationEnd):
            raise
        except ParentDiedException:
            parent_died = True
        except:
            log.trace().error("-- Unhandled Exception in local loop <%s> --" % self.loop_label)
        finally:
            if self.connection_stack:
                assert len(self.connection_stack) == 1
                self.connection_stack.pop().close()
        self.deaths += 1
        self.running = False
        self.app.running.remove(self)
        # Keep-Alive Laws
        # ---------------
        # 1) Parent loop death always kills off children.
        # 2) Child loops with keep-alive resurrect if their parent didn't die.
        # 3) If a parent has died, a child always dies.
        self.notify_children()
        if self.keep_alive and not parent_died:
            log.warning("(Keep-Alive loop %s died; restarting)" % self)
            self.reset()
            self.hub.call_later(0.5, self.wake)
        elif self.parent and self in self.parent.children:
            self.parent.children.remove(self)
            self.parent = None

    def notify_children(self):
        for c in self.children:
            c.parent_died()

    def __hash__(self):
        return self.id

    def __str__(self):
        return '<Loop id=%s callable=%s>' % (self.id,
        str(self.loop_callable))

    def clear_pending_events(self):
        '''When a loop is rescheduled, cancel any other timers or waits.
        '''
        if self._wakeup_timer and self._wakeup_timer.pending:
            self._wakeup_timer.cancel()
        if self.connection_stack:
            conn = self.connection_stack[-1]
            conn.cleanup()
        self.fire_handlers = {}
        self.fire_due = False
        self.app.waits.clear(self)

    def thread(self, f, *args, **kw):
        self.hub.run_in_thread(self.wake, f, *args, **kw)
        return self.dispatch()

    def fork(self, make_child, f, *args, **kw):
        def wrap():
            return f(*args, **kw)
        l = Loop(wrap)
        if make_child:
            self.children.add(l)
            l.parent = self
        l.loop_label = str(f)
        self.app.add_loop(l, track=self.tracked)
        return l

    def parent_died(self):
        if self.running:
            self.hub.schedule(lambda: self.wake(ParentDiedException()))

    def label(self, label):
        self.loop_label = label

    def first(self, sleep=None, waits=None,
            receive_any=None, receive=None, until=None, until_eol=None, datagram=None):
        def marked_cb(kw):
            def deco(f):
                def mark(d):
                    if isinstance(d, Exception):
                        return f(d)
                    return f((kw, d))
                return mark
            return deco

        f_sent = filter(None, (receive_any, receive, until, until_eol, datagram))
        assert len(f_sent) <= 1,(
        "only 1 of (receive_any, receive, until, until_eol, datagram) may be provided")
        sentinel = None
        if receive_any:
            sentinel = buffer.BufAny
            tok = 'receive_any'
        elif receive:
            sentinel = receive
            tok = 'receive'
        elif until:
            sentinel = until
            tok = 'until'
        elif until_eol:
            sentinel = "\r\n"
            tok = 'until_eol'
        elif datagram:
            sentinel = _datagram
            tok = 'datagram'
        if sentinel:
            early_val = self._input_op(sentinel, marked_cb(tok))
            if early_val:
                return tok, early_val
            # othewise.. process others and dispatch

        if sleep is not None:
            self._sleep(sleep, marked_cb('sleep'))

        if waits:
            for w in waits:
                v = self._wait(w, marked_cb(w))
                if type(v) is EarlyValue:
                    self.clear_pending_events()
                    self.reschedule_with_this_value((w, v.val))
                    break
        return self.dispatch()

    def connect(self, client, ip, sock, host, port, timeout=None):
        def cancel_callback(sock):
            self.hub.unregister(sock)
            sock.close()
            self.hub.schedule(lambda: self.wake(
                ClientConnectionTimeout("connection timeout (%s:%s)" % (host, port))
                ))

        def connect_callback():
            if cancel_timer is not None:
                cancel_timer.cancel()
            self.hub.unregister(sock)

            try:
                sock.getpeername()
            except socket.error:
                return

            def finish(e=None):
                if e:
                    assert isinstance(e, Exception)
                    self.hub.schedule(
                    lambda: self.wake(e)
                    )
                else:
                    client.conn = Connection(fsock, ip)
                    client.connected = True
                    self.hub.schedule(
                    lambda: self.wake()
                    )

            if client.ssl_ctx:
                fsock = SSL.Connection(client.ssl_ctx, sock)
                fsock.setblocking(0)
                fsock.set_connect_state()
                ssl_async_handshake(fsock, self.hub, finish)
            else:
                fsock = sock
                finish()

        def error_callback():
            if cancel_timer is not None:
                cancel_timer.cancel()
            self.hub.unregister(sock)
            self.hub.schedule(
            lambda: self.wake(
                ClientConnectionError("odd error on connect() (%s:%s)" % (host, port))
                ))

        def read_callback():
            # DJB on handling socket connection failures, from
            # http://cr.yp.to/docs/connect.html

            # "Another possibility is getpeername(). If the socket is
            # connected, getpeername() will return 0. If the socket is not
            # connected, getpeername() will return ENOTCONN, and read(fd,&ch,1)
            # will produce the right errno through error slippage. This is a
            # combination of suggestions from Douglas C. Schmidt and Ken Keys."

            try:
                sock.getpeername()
            except socket.error:
                try:
                    d = sock.recv(1)
                except socket.error, e:
                    if e.errno == errno.ECONNREFUSED:
                        d = ''
                    else:
                        d = None

                if d != '':
                    log.error("internal error: expected empty read on disconnected socket")

                if cancel_timer is not None:
                    cancel_timer.cancel()
                self.hub.unregister(sock)
                self.hub.schedule(
                lambda: self.wake(
                    ClientConnectionError("Could not connect to remote host (%s:%s)" % (host, port))
                    ))
                return

        cancel_timer = None
        if timeout is not None:
            cancel_timer = self.hub.call_later(timeout, cancel_callback, sock)

        self.hub.register(sock, read_callback, connect_callback, error_callback)
        self.hub.enable_write(sock)
        try:
            self.dispatch()
        except ClientConnectionError:
            if cancel_timer is not None:
                cancel_timer.cancel()
            raise
        else:
            client.on_connect()

    def sleep(self, v=0):
        self._sleep(v)
        return self.dispatch()

    def _sleep(self, v, cb_maker=identity):
        cb = lambda: cb_maker(self.wake)(True)
        assert v >= 0

        if v > 0:
            self._wakeup_timer = self.hub.call_later(v, cb)
        else:
            self.hub.schedule(cb, True)

    def fire_in(self, what, value):
        if what in self.fire_handlers:
            handler = self.fire_handlers[what]
            self.fire_handlers = {}
            handler(value)
            self.fire_due = True

    def wait(self, event):
        v = self._wait(event)
        if type(v) is EarlyValue:
            self.reschedule_with_this_value(v.val)
        return self.dispatch()

    def _wait(self, event, cb_maker=identity):
        rcb = cb_maker(self.wake_fire)
        def cb(d):
            def call_in():
                rcb(d)
            self.hub.schedule(call_in)
        v = self.app.waits.wait(self, event)
        if type(v) is EarlyValue:
            return v
        self.fire_handlers[v] = cb

    def fire(self, event, value=None):
        self.app.waits.fire(event, value)

    def os_time(self):
        usage = os.times()
        return usage[0] + usage[1]

    def start_clock(self):
        self._clock = self.os_time()

    def update_clock(self):
        now = self.os_time()
        self.clock += (now - self._clock)
        self._clock = now

    def clocktime(self):
        self.update_clock()
        return self.clock

    def _dispatch(self):
        r = self.app.runhub.switch()
        return r

    def _dispatch_track(self):
        self.update_clock()
        return self._dispatch()

    def wake_fire(self, value=ContinueNothing):
        assert self.fire_due, "wake_fire called when fire wasn't due!"
        self.fire_due = False
        return self.wake(value)

    def wake(self, value=ContinueNothing):
        '''Wake up this loop.  Called by the main hub to resume a loop
        when it is rescheduled.
        '''
        if self.tracked:
            self.start_clock()

        global current_loop

        # if we have a fire pending,
        # don't run (triggered by sleep or bytes)
        if self.fire_due:
            return

        if self.coroutine is None:
            self.coroutine = greenlet(self.run)
            assert self.coroutine.parent == runtime.current_app.runhub
        self.clear_pending_events()
        current_loop = self
        if isinstance(value, Exception):
            self.coroutine.throw(value)
        elif value is not ContinueNothing:
            self.coroutine.switch(value)
        else:
            self.coroutine.switch()

    def input_op(self, sentinel_or_receive=buffer.BufAny):
        v = self._input_op(sentinel_or_receive)
        if v:
            return v
        else:
            return self.dispatch()

    def _input_op(self, sentinel, cb_maker=identity):
        conn = self.check_connection()
        cb = cb_maker(self.wake)
        res = conn.check_incoming(sentinel, cb)
        if callable(res):
            cb = res
        elif res:
            return res
        conn.waiting_callback = cb
        return None

    def check_connection(self):
        try:
            conn = self.connection_stack[-1]
        except IndexError:
            raise RuntimeError("Cannot complete TCP socket operation: no associated connection")
        if conn.closed:
            raise ConnectionClosed("Cannot complete TCP socket operation: associated connection is closed")
        return conn

    def send(self, o, priority=5):
        conn = self.check_connection()
        conn.queue_outgoing(o, priority)
        conn.set_writable(True)

    def reschedule_with_this_value(self, value):
        def delayed_call():
            self.wake(value)
        self.hub.schedule(delayed_call, True)

    def signal(self, sig):
        cb = lambda: self.wake(True)
        self._signal(sig, cb)
        return self.dispatch()

    def _signal(self, sig, cb):
        self.hub.add_signal_handler(sig, cb)

class Connection(object):
    def __init__(self, sock, addr):
        self.hub = runtime.current_app.hub
        self.pipeline = pipeline.Pipeline()
        self.buffer = buffer.Buffer()
        self.sock = sock
        self.addr = addr
        self.hub.register(sock, self.handle_read, self.handle_write, self.handle_error)
        self._writable = False
        self.closed = False
        self.waiting_callback = None

    def queue_outgoing(self, msg, priority=5):
        self.pipeline.add(msg, priority)

    def check_incoming(self, condition, callback):
        self.buffer.set_term(condition)
        return self.buffer.check()

    def set_writable(self, val):
        '''Set the associated socket writable.  Called when there is
        data on the outgoing pipeline ready to be delivered to the
        remote host.
        '''
        if self.closed:
            return
        if val and not self._writable:
            self.hub.enable_write(self.sock)
            self._writable = True
            return
        if not val and self._writable:
            self.hub.disable_write(self.sock)
            self._writable = False

    def cleanup(self):
        self.buffer.clear_term()
        self.waiting_callback = None

    def close(self):
        self.set_writable(True)
        self.pipeline.close_request()

    def shutdown(self, remote_closed=False):
        '''Clean up after a client disconnects or after
        the connection_handler ends (and we disconnect).
        '''
        self.hub.unregister(self.sock)
        self.closed = True
        self.sock.close()

        if remote_closed and self.waiting_callback:
            self.waiting_callback(
            ConnectionClosed('Connection closed by remote host',
            self.buffer.pop()))

    def handle_write(self):
        '''The low-level handler called by the event hub
        when the socket is ready for writing.
        '''
        if not self.pipeline.empty and not self.closed:
            try:
                data = self.pipeline.read(BUFSIZ)
            except pipeline.PipelineCloseRequest:
                self.shutdown()
            else:
                try:
                    bsent = self.sock.send(data)
                except socket.error, e:
                    code, s = e
                    if code in (errno.EAGAIN, errno.EINTR):
                        self.pipeline.backup(data)
                        return
                    self.shutdown(True)
                except (SSL.WantReadError, SSL.WantWriteError, SSL.WantX509LookupError):
                    self.pipeline.backup(data)
                    return
                except SSL.ZeroReturnError:
                    self.shutdown(True)
                except SSL.SysCallError:
                    self.shutdown(True)
                except:
                    sys.stderr.write("Unknown Error on send():\n%s"
                    % traceback.format_exc())
                    self.shutdown(True)

                else:
                    if bsent != len(data):
                        self.pipeline.backup(data[bsent:])

                    if not self.pipeline.empty:
                        return
                    else:
                        self.set_writable(False)

    def handle_read(self):
        '''The low-level handler called by the event hub
        when the socket is ready for reading.
        '''
        if self.closed:
            return
        try:
            data = self.sock.recv(BUFSIZ)
        except socket.error, e:
            code, s = e
            if code in (errno.EAGAIN, errno.EINTR):
                return
            data = ''
        except (SSL.WantReadError, SSL.WantWriteError, SSL.WantX509LookupError):
            return
        except SSL.ZeroReturnError:
            data = ''
        except SSL.SysCallError:
            data = ''
        except:
            sys.stderr.write("Unknown Error on recv():\n%s"
            % traceback.format_exc())
            data = ''

        if not data:
            self.shutdown(True)
        else:
            res = self.buffer.feed(data)
            # Require a result that satisfies current term
            if res:
                self.waiting_callback(res)

    def handle_error(self):
        self.shutdown(True)

class Datagram(str):
    def __new__(self, payload, addr):
        inst = str.__new__(self, payload)
        inst.addr = addr
        return inst

class UDPSocket(Connection):
    def __init__(self, parent, sock, ip=None, port=None):
        self.port = port
        self.parent = parent
        super(UDPSocket, self).__init__(sock, ip)
        del self.buffer
        del self.pipeline
        self.outgoing = deque([])
        self.incoming = deque([])

    def queue_outgoing(self, msg, priority=5):
        dgram = Datagram(msg, self.parent.remote_addr)
        self.outgoing.append(dgram)

    def check_incoming(self, condition, callback):
        assert condition is datagram, "UDP supports datagram sentinels only"
        if self.incoming:
            value = self.incoming.popleft()
            self.parent.remote_addr = value.addr
            return value
        def _wrap(value=ContinueNothing):
            if isinstance(value, Datagram):
                self.parent.remote_addr = value.addr
            return callback(value)
        return _wrap

    def handle_write(self):
        '''The low-level handler called by the event hub
        when the socket is ready for writing.
        '''
        while self.outgoing:
            dgram = self.outgoing.popleft()
            try:
                bsent = self.sock.sendto(dgram, dgram.addr)
            except socket.error, e:
                code, s = e
                if code in (errno.EAGAIN, errno.EINTR):
                    self.outgoing.appendleft(dgram)
                    return
                self.shutdown(True)
            except (SSL.WantReadError, SSL.WantWriteError, SSL.WantX509LookupError):
                self.outgoing.appendleft(dgram)
                return
            except SSL.ZeroReturnError:
                self.shutdown(True)
            except SSL.SysCallError:
                self.shutdown(True)
            except:
                sys.stderr.write("Unknown Error on send():\n%s"
                % traceback.format_exc())
                self.shutdown(True)
            else:
                assert bsent == len(dgram), "complete datagram not sent!"
        self.set_writable(False)

    def handle_read(self):
        '''The low-level handler called by the event hub
        when the socket is ready for reading.
        '''
        if self.closed:
            return
        try:
            data, addr = self.sock.recvfrom(BUFSIZ)
            dgram = Datagram(data, addr)
        except socket.error, e:
            code, s = e
            if code in (errno.EAGAIN, errno.EINTR):
                return
            dgram = Datagram('', (None, None))
        except (SSL.WantReadError, SSL.WantWriteError, SSL.WantX509LookupError):
            return
        except SSL.ZeroReturnError:
            dgram = Datagram('', (None, None))
        except SSL.SysCallError:
            dgram = Datagram('', (None, None))
        except:
            sys.stderr.write("Unknown Error on recv():\n%s"
            % traceback.format_exc())
            dgram = Datagram('', (None, None))

        if not dgram:
            self.shutdown(True)
        elif self.waiting_callback:
            self.waiting_callback(dgram)
        else:
            self.incoming.append(dgram)

    def cleanup(self):
        self.waiting_callback = None

    def close(self):
        self.set_writable(True)

    def shutdown(self, remote_closed=False):
        '''Clean up after the connection_handler ends.'''
        self.hub.unregister(self.sock)
        self.closed = True
        self.sock.close()

        if remote_closed and self.waiting_callback:
            self.waiting_callback(
                ConnectionClosed('Connection closed by remote host')
            )

########NEW FILE########
__FILENAME__ = dnosetests
#!/usr/bin/env python
"""Run nosetests in the diesel event loop.

You can pass the same command-line arguments that you can pass to the
`nosetests` command to this script and it will execute the tests in the
diesel event loop. This is a great way to test interactions between various
diesel green threads and network-based applications built with diesel.

"""
import diesel
import nose

from diesel.logmod import levels, set_log_level

def main():
    set_log_level(levels.CRITICAL)
    diesel.quickstart(nose.main)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = events
from collections import defaultdict

class StopWaitDispatch(Exception): pass
class StaticValue(object):
    def __init__(self, value):
        self.value = value

class EarlyValue(object):
    def __init__(self, val):
        self.val = val

class Waiter(object):
    @property
    def wait_id(self):
        return str(hash(self))

    def process_fire(self, given):
        return StaticValue(given)

    def ready_early(self):
        return False

class StringWaiter(str, Waiter):
    @property
    def wait_id(self):
        return str(self)


class WaitPool(object):
    '''A structure that manages all `wait`ers, makes sure fired events
    get to the right places.
    '''
    def __init__(self):
        self.waits = defaultdict(set)
        self.loop_refs = defaultdict(set)

    def wait(self, who, what):
        if isinstance(what, basestring):
            what = StringWaiter(what)

        if what.ready_early():
            return EarlyValue(what.process_fire(None))

        self.waits[what.wait_id].add(who)
        self.loop_refs[who].add(what)
        return what.wait_id

    def fire(self, what, value):
        if isinstance(what, basestring):
            what = StringWaiter(what)

        static = False
        for handler in self.waits[what.wait_id]:
            if handler.fire_due:
                continue
            if not static:
                try:
                    value = what.process_fire(value)
                except StopWaitDispatch:
                    break
                if type(value) == StaticValue:
                    static = True
                    value = value.value
            handler.fire_in(what.wait_id, value)

    def clear(self, who):
        for what in self.loop_refs[who]:
            self.waits[what.wait_id].remove(who)
        del self.loop_refs[who]

########NEW FILE########
__FILENAME__ = hub
# vim:ts=4:sw=4:expandtab
'''An event hub that supports sockets and timers, based
on Python 2.6's select & epoll support.
'''
try:
    import select26 as select
except ImportError:
    import select

try:
    import pyev
except:
    have_libev = False
else:
    have_libev = True

import errno
import fcntl
import os
import signal
import thread

from collections import deque, defaultdict
from operator import attrgetter
from time import time
from Queue import Queue, Empty

TRIGGER_COMPARE = attrgetter('trigger_time')

class ExistingSignalHandler(Exception):
    pass

class Timer(object):
    '''A timer is a promise to call some function at a future date.
    '''
    ALLOWANCE = 0.03 # If we're within 30ms, the timer is due
    def __init__(self, hub, interval, f, *args, **kw):
        self.hub = hub
        self.trigger_time = time() + interval
        self.f = f
        self.args = args
        self.kw = kw
        self.pending = True
        self.inq = False
        self.hub_data = None

    def cancel(self):
        self.pending = False
        if self.inq:
            self.inq = False
            self.hub.remove_timer(self)
            self.hub = None

    def callback(self):
        '''When the external entity checks this timer and determines
        it's due, this function is called, which calls the original
        callback.
        '''
        self.pending = False
        self.inq = False
        self.hub = None
        return self.f(*self.args, **self.kw)

    @property
    def due(self):
        '''Is it time to run this timer yet?

        The allowance provides some give-and-take so that if a
        sleep() delay comes back a little early, we still go.
        '''
        return (self.trigger_time - time()) < self.ALLOWANCE

class _PipeWrap(object):
    def __init__(self, p):
        self.p = p

    def fileno(self):
        return self.p

class IntWrap(_PipeWrap): pass

class AbstractEventHub(object):
    def __init__(self):
        self.timers = []
        self.new_timers = []
        self.run = True
        self.events = {}
        self.run_now = deque()
        self.fdmap = {}
        self.fd_ids = defaultdict(int)
        self._setup_threading()
        self.reschedule = deque()

    def _setup_threading(self):
        self._t_recv, self._t_wakeup = os.pipe()
        fcntl.fcntl(self._t_recv, fcntl.F_SETFL, os.O_NONBLOCK)
        fcntl.fcntl(self._t_wakeup, fcntl.F_SETFL, os.O_NONBLOCK)
        self.thread_comp_in = Queue()

        def handle_thread_done():
            try:
                os.read(self._t_recv, 65536)
            except IOError:
                pass
            while True:
                try:
                    c, v = self.thread_comp_in.get(False)
                except Empty:
                    break
                else:
                    c(v)
        self.register(_PipeWrap(self._t_recv), handle_thread_done, None, None)

    def remove_timer(self, t):
        try:
            self.timers.remove(t)
        except IndexError:
            pass

    def run_in_thread(self, reschedule, f, *args, **kw):
        def wrap():
            try:
                res = f(*args, **kw)
            except Exception, e:
                self.thread_comp_in.put((reschedule, e))
            else:
                self.thread_comp_in.put((reschedule, res))
            self.wake_from_other_thread()
        thread.start_new_thread(wrap, ())

    def wake_from_other_thread(self):
        try:
            os.write(self._t_wakeup, '\0')
        except IOError:
            pass

    def schedule_loop_from_other_thread(self, l, v=None):
        self.thread_comp_in.put((l.wake, v))
        self.wake_from_other_thread()

    def handle_events(self):
        '''Run one pass of event handling.
        '''
        raise NotImplementedError

    def call_later(self, interval, f, *args, **kw):
        '''Schedule a timer on the hub.
        '''
        t = Timer(self, interval, f, *args, **kw)
        self.new_timers.append(t)
        return t

    def schedule(self, c, reschedule=False):
        if reschedule:
            self.reschedule.append(c)
        else:
            self.run_now.append(c)

    def register(self, fd, read_callback, write_callback, error_callback):
        '''Register a socket fd with the hub, providing callbacks
        for read (data is ready to be recv'd) and write (buffers are
        ready for send()).

        By default, only the read behavior will be polled and the
        read callback used until enable_write is invoked.
        '''
        fn = fd.fileno()
        self.fdmap[fd] = fn
        self.fd_ids[fn] += 1
        assert fn not in self.events
        self.events[fn] = (read_callback, write_callback, error_callback)
        self._add_fd(fd)

    def add_signal_handler(self, sig, callback):
        '''Run the given callback when signal sig is triggered.'''
        raise NotImplementedError

    def _add_fd(self, fd):
        '''Add this socket to the list of sockets used in the
        poll call.
        '''
        raise NotImplementedError

    def enable_write(self, fd):
        '''Enable write polling and the write callback.
        '''
        raise NotImplementedError

    def disable_write(self, fd):
        '''Disable write polling and the write callback.
        '''
        raise NotImplementedError

    def unregister(self, fd):
        '''Remove this socket from the list of sockets the
        hub is polling on.
        '''
        if fd in self.fdmap:
            fn = self.fdmap.pop(fd)
            del self.events[fn]

            self._remove_fd(fd)

    def _remove_fd(self, fd):
        '''Remove this socket from the list of sockets the
        hub is polling on.
        '''
        raise NotImplementedError

    @property
    def describe(self):
        raise NotImplementedError()

class EPollEventHub(AbstractEventHub):
    '''A epoll-based hub.
    '''
    def __init__(self):
        self.epoll = select.epoll()
        self.signal_handlers = defaultdict(deque)
        super(EPollEventHub, self).__init__()

    @property
    def describe(self):
        return "hand-rolled select.epoll"

    def handle_events(self):
        '''Run one pass of event handling.

        epoll() is called, with a timeout equal to the next-scheduled
        timer.  When epoll returns, all fd-related events (if any) are
        handled, and timers are handled as well.
        '''
        while self.run_now and self.run:
            self.run_now.popleft()()

        if self.new_timers:
            for tr in self.new_timers:
                if tr.pending:
                    tr.inq = True
                    self.timers.append(tr)
            self.timers.sort(key=TRIGGER_COMPARE, reverse=True)
            self.new_timers = []

        tm = time()
        timeout = (self.timers[-1].trigger_time - tm) if self.timers else 1e6
        # epoll, etc, limit to 2^^31/1000 or OverflowError
        timeout = min(timeout, 1e6)
        if timeout < 0 or self.reschedule:
            timeout = 0

        # Run timers first, to try to nail their timings
        while self.timers and self.timers[-1].due:
            t = self.timers.pop()
            if t.pending:
                t.callback()
                while self.run_now and self.run:
                    self.run_now.popleft()()
                if not self.run:
                    return

        # Handle all socket I/O
        try:
            for (fd, evtype) in self.epoll.poll(timeout):
                fd_id = self.fd_ids[fd]
                if evtype & select.EPOLLIN or evtype & select.EPOLLPRI:
                    self.events[fd][0]()
                elif evtype & select.EPOLLERR or evtype & select.EPOLLHUP:
                    self.events[fd][2]()

                # The fd could have been reassigned to a new socket or removed
                # when running the callbacks immediately above. Only use it if
                # neither of those is the case.
                use_fd = fd_id == self.fd_ids[fd] and fd in self.events
                if evtype & select.EPOLLOUT and use_fd:
                    self.events[fd][1]()

                while self.run_now and self.run:
                    self.run_now.popleft()()

                if not self.run:
                    return
        except IOError, e:
            if e.errno == errno.EINTR:
                while self.run_now and self.run:
                    self.run_now.popleft()()
            else:
                raise

        self.run_now = self.reschedule
        self.reschedule = deque()

    def add_signal_handler(self, sig, callback):
        existing = signal.getsignal(sig)
        if not existing:
            signal.signal(sig, self._report_signal)
        elif existing != self._report_signal:
            raise ExistingSignalHandler(existing)
        self.signal_handlers[sig].append(callback)

    def _report_signal(self, sig, frame):
        for callback in self.signal_handlers[sig]:
            self.run_now.append(callback)
        self.signal_handlers[sig] = deque()
        signal.signal(sig, signal.SIG_DFL)

    def _add_fd(self, fd):
        '''Add this socket to the list of sockets used in the
        poll call.
        '''
        self.epoll.register(fd, select.EPOLLIN | select.EPOLLPRI)

    def enable_write(self, fd):
        '''Enable write polling and the write callback.
        '''
        self.epoll.modify(
                fd, select.EPOLLIN | select.EPOLLPRI | select.EPOLLOUT)

    def disable_write(self, fd):
        '''Disable write polling and the write callback.
        '''
        self.epoll.modify(fd, select.EPOLLIN | select.EPOLLPRI)

    def _remove_fd(self, fd):
        '''Remove this socket from the list of sockets the
        hub is polling on.
        '''
        self.epoll.unregister(fd)

class LibEvHub(AbstractEventHub):
    def __init__(self):
        self._ev_loop = pyev.default_loop()
        self._ev_watchers = {}
        self._ev_fdmap = {}
        AbstractEventHub.__init__(self)

    def add_signal_handler(self, sig, callback):
        existing = signal.getsignal(sig)
        if existing:
            raise ExistingSignalHandler(existing)
        watcher = self._ev_loop.signal(sig, self._signal_fired)
        self._ev_watchers[watcher] = callback
        watcher.start()

    @property
    def describe(self):
        return "pyev/libev (%s/%s) backend=%s" % (
                self._pyev_version() + ({
                    1  : "select()",
                    2  : "poll()",
                    4  : "epoll()",
                    8  : "kqueue()",
                    16 : "/dev/poll",
                    32 : "event ports",
                    }.get(self._ev_loop.backend, "UNKNOWN"),))

    def _pyev_version(self):
        if hasattr(pyev, 'version'):
            return pyev.version()
        else:
            pyev_ver = pyev.__version__
            libev_ver = ".".join(str(p) for p in pyev.abi_version())
            return (pyev_ver, libev_ver)

    def handle_events(self):
        '''Run one pass of event handling.
        '''
        while self.run_now and self.run:
            self.run_now.popleft()()

        if not self.run:
            self._ev_loop.stop()
            del self._ev_loop
            return

        if self.run_now or self.reschedule:
            self._ev_loop.start(pyev.EVRUN_NOWAIT)
        else:
            while not self.run_now:
                self._ev_loop.start(pyev.EVRUN_ONCE)

        while self.run_now and self.run:
            self.run_now.popleft()()

        self.run_now.extend(self.reschedule)
        self.reschedule = deque()

    def call_later(self, interval, f, *args, **kw):
        '''Schedule a timer on the hub.
        '''
        t = Timer(self, interval, f, *args, **kw)
        t.inq = True
        evt = self._ev_loop.timer(interval, 0, self._ev_timer_fired)
        t.hub_data = evt
        self._ev_watchers[evt] = t
        evt.start()
        return t

    def _ev_timer_fired(self, watcher, revents):
        t = self._ev_watchers.pop(watcher)
        if t.hub_data:
            t.hub_data = None
            self.run_now.append(t.callback)

    def remove_timer(self, t):
        evt = t.hub_data
        if evt in self._ev_watchers:
            del self._ev_watchers[evt]
            evt.stop()

    def schedule(self, c, reschedule=False):
        if reschedule:
            self.reschedule.append(c)
        else:
            self.run_now.append(c)

    def _signal_fired(self, watcher, revents):
        callback = self._ev_watchers.pop(watcher)
        watcher.stop()
        self.run_now.append(callback)

    def _ev_io_fired(self, watcher, revents):
        r, w, e = self.events[watcher.fd]
        if revents & pyev.EV_READ:
            self.run_now.append(r)
        if revents & pyev.EV_WRITE:
            self.run_now.append(w)
        if revents & pyev.EV_ERROR:
            self.run_now.append(e)

    def _add_fd(self, fd):
        '''Add this socket to the list of sockets used in the
        poll call.
        '''
        assert fd not in self._ev_fdmap
        rev = self._ev_loop.io(fd, pyev.EV_READ, self._ev_io_fired)
        wev = self._ev_loop.io(fd, pyev.EV_WRITE, self._ev_io_fired)
        self._ev_fdmap[fd] = rev, wev
        rev.start()

    def enable_write(self, fd):
        '''Enable write polling and the write callback.
        '''
        self._ev_fdmap[fd][1].start()

    def disable_write(self, fd):
        '''Disable write polling and the write callback.
        '''
        self._ev_fdmap[fd][1].stop()

    def _remove_fd(self, fd):
        '''Remove this socket from the list of sockets the
        hub is polling on.
        '''
        rev, wev = self._ev_fdmap.pop(fd)
        rev.stop()
        wev.stop()

# Expose a usable EventHub implementation
if (os.environ.get('DIESEL_LIBEV') or
    os.environ.get('DIESEL_NO_EPOLL') or
    not hasattr(select, 'epoll')):
    assert have_libev, "if you don't have select.epoll (not on linux?), please install pyev!"
    EventHub = LibEvHub
else:
    EventHub = EPollEventHub

########NEW FILE########
__FILENAME__ = interactive
"""An interactive interpreter inside of a diesel event loop.

It's useful for importing and interacting with code that expects to run
inside of a diesel event loop. It works especially well for interactive
sessions with diesel's various network protocol clients.

Supports both the standard Python interactive interpreter and IPython (if
installed).

"""
import code
import sys
sys.path.insert(0, '.')

import diesel
from diesel.util.streams import create_line_input_stream

try:
    from IPython.Shell import IPShell
    IPYTHON_AVAILABLE = True
except ImportError:
    try:
        # Support changes made in iPython 0.11
        from IPython.frontend.terminal.ipapp import TerminalInteractiveShell as IPShell
        IPYTHON_AVAILABLE = True
    except ImportError:
        IPYTHON_AVAILABLE = False


# Library Functions:
# ==================

def interact_python():
    """Runs an interactive interpreter; halts the diesel app when finished."""
    globals_ = globals()
    env = {
        '__builtins__':globals_['__builtins__'],
        '__doc__':globals_['__doc__'],
        '__name__':globals_['__name__'],
        'diesel':diesel,
    }
    inp = create_line_input_stream(sys.stdin)

    def diesel_input(prompt):
        sys.stdout.write(prompt)
        sys.stdout.flush()
        return inp.get().rstrip('\n')

    code.interact(None, diesel_input, env)
    diesel.quickstop()

def interact_ipython():
    """Starts an IPython instance; halts the diesel app when finished."""
    IPShell(user_ns={'diesel':diesel}).mainloop()
    diesel.quickstop()

# Interpreter entry points:
# =========================

def python():
    diesel.quickstart(interact_python)

def ipython():
    if not IPYTHON_AVAILABLE:
        print >> sys.stderr, "IPython not found."
        raise SystemExit(1)
    diesel.quickstart(interact_ipython)


########NEW FILE########
__FILENAME__ = logmod
# vim:ts=4:sw=4:expandtab
'''A simple logging module that supports various verbosity
levels and component-specific subloggers.
'''

import sys
import time
from twiggy import log as olog, levels, outputs, formats, emitters
try:
    from twiggy import add_emitters
except ImportError:
    from twiggy import addEmitters as add_emitters
from functools import partial

diesel_format = formats.line_format
diesel_format.traceback_prefix = '\n'
diesel_format.conversion = formats.ConversionTable()
diesel_format.conversion.add("time", partial(time.strftime, "%Y/%m/%d %H:%M:%S"), "[{1}]".format)
diesel_format.conversion.add("name", str, "{{{1}}}".format)
diesel_format.conversion.add("level", str, "{1}".format)
diesel_format.conversion.aggregate = " ".join
diesel_format.conversion.genericValue = str
diesel_format.conversion.genericItem = lambda _1, _2: "%s=%s" % (_1, _2)

diesel_output = outputs.StreamOutput(diesel_format)

def set_log_level(level=levels.INFO):
    emitters.clear()

    add_emitters(
        ('*', level, None, diesel_output)
    )

log = olog.name("diesel")

set_log_level()

########NEW FILE########
__FILENAME__ = pipeline
# vim:ts=4:sw=4:expandtab
'''An outgoing pipeline that can handle
strings or files.
'''
try:
    import cStringIO
except ImportError:
    raise ImportError, "cStringIO is required"

from bisect import bisect_right

_obj_SIO = cStringIO.StringIO
_type_SIO = cStringIO.OutputType
def make_SIO(d):
    t = _obj_SIO()
    t.write(d)
    t.seek(0)
    return t

def get_file_length(f):
    m = f.tell()
    f.seek(0, 2)
    r = f.tell()
    f.seek(m)
    return r

class PipelineCloseRequest(Exception): pass
class PipelineClosed(Exception): pass

class PipelineItem(object):
    def __init__(self, d):
        if type(d) is str:
            self.f = make_SIO(d)
            self.length = len(d)
            self.is_sio = True
            self.f.seek(0, 2)
        elif hasattr(d, 'seek'):
            self.f = d
            self.length = get_file_length(d)
            self.is_sio = False
        else:
            raise ValueError("argument to add() must be either a str or a file-like object")
        self.read = self.f.read

    def merge(self, s):
        self.f.write(s)
        self.length += len(s)

    def reset(self):
        if self.is_sio:
            self.is_sio = False
            self.f.seek(0, 0)

    @property
    def done(self):
        return self.f.tell() == self.length

    def __cmp__(self, other):
        if other is PipelineStandIn:
            return -1
        return cmp(self, other) 

class PipelineStandIn(object): pass

class Pipeline(object):
    '''A pipeline that supports appending strings or
    files and can read() transparently across object
    boundaries in the outgoing buffer.
    '''
    def __init__(self):
        self.line = []
        self.current = None
        self.want_close = False

    def add(self, d, priority=5):
        '''Add object `d` to the pipeline.
        '''
        if self.want_close:
            raise PipelineClosed

        priority *= -1

        dummy = (priority, PipelineStandIn)
        ind = bisect_right(self.line, dummy)
        if ind > 0 and type(d) is str and self.line[ind - 1][-1].is_sio:
            a_pri, adjacent = self.line[ind - 1]
            if adjacent.is_sio and a_pri == priority:
                adjacent.merge(d)
            else:
                self.line.insert(ind, (priority, PipelineItem(d)))
        else:
            self.line.insert(ind, (priority, PipelineItem(d)))

    def close_request(self):
        '''Add a close request to the outgoing pipeline.

        No more data will be allowed in the pipeline, and, when
        it is emptied, PipelineCloseRequest will be raised.
        '''
        self.want_close = True

    def read(self, amt):
        '''Read up to `amt` bytes off the pipeline.

        May raise PipelineCloseRequest if the pipeline is
        empty and the connected stream should be closed.
        '''
        if not self.current and not self.line:
            if self.want_close:
                raise PipelineCloseRequest()
            return ''

        if not self.current:
            _, self.current = self.line.pop(0)
            self.current.reset()

        out = ''
        while len(out) < amt:
            try:
                data = self.current.read(amt - len(out))
            except ValueError:
                data = ''
            if data == '':
                if not self.line:
                    self.current = None
                    break
                _, self.current = self.line.pop(0)
                self.current.reset()
            else:
                out += data

        # eagerly evict and EOF that's been read _just_ short of 
        # the EOF '' read() call.. so that we know we're empty,
        # and we don't bother with useless iterations
        if self.current and self.current.done:
            self.current = None

        return out
    
    def backup(self, d):
        '''Pop object d back onto the front the pipeline.

        Used in cases where not all data is sent() on the socket,
        for example--the remainder will be placed back in the pipeline.
        '''
        cur = self.current
        self.current = PipelineItem(d)
        self.current.reset()
        if cur:
            self.line.insert(0, (-1000000, cur))

    @property
    def empty(self):
        '''Is the pipeline empty?

        A close request is "data" that needs to be consumed,
        too.
        '''
        return self.want_close == False and not self.line and not self.current

########NEW FILE########
__FILENAME__ = DNS
from __future__ import absolute_import

import time
from collections import deque

from diesel import UDPClient, call, send, first, datagram

from dns.message import make_query, from_wire
from dns.rdatatype import A
from dns.resolver import Resolver as ResolvConf


class NotFound(Exception):
    pass

class Timeout(Exception):
    pass

_resolv_conf = ResolvConf()
_local_nameservers = _resolv_conf.nameservers
_search_domains = []
if _resolv_conf.domain:
    _search_domains.append(str(_resolv_conf.domain)[:-1])
_search_domains.extend(map(lambda n: str(n)[:-1], _resolv_conf.search))

del _resolv_conf

class DNSClient(UDPClient):
    """A DNS client.

    Uses nameservers from /etc/resolv.conf if none are supplied.

    """
    def __init__(self, servers=None, port=53):
        if servers is None:
            self.nameservers = servers = _local_nameservers
            self.primary = self.nameservers[0]
        super(DNSClient, self).__init__(servers[0], port)

    @call
    def resolve(self, name, orig_timeout=5):
        """Try to resolve name.

        Returns:
            A list of IP addresses for name.

        Raises:
            * Timeout if the request to all servers times out.
            * NotFound if we get a response from a server but the name
              was not resolved.

        """
        names = deque([name])
        for n in _search_domains:
            names.append(('%s.%s' % (name, n)))
        start = time.time()
        timeout = orig_timeout
        r = None
        while names:
            n = names.popleft()
            try:
                r = self._actually_resolve(n, timeout)
            except:
                timeout = orig_timeout - (time.time() - start)
                if timeout <= 0 or not names:
                    raise
            else:
                break
        assert r is not None
        return r

    def _actually_resolve(self, name, timeout):
        timeout = timeout / float(len(self.nameservers))
        try:
            for server in self.nameservers:
                # Try each nameserver in succession.
                self.addr = server
                query = make_query(name, A)
                send(query.to_wire())
                start = time.time()
                remaining = timeout
                while True:
                    # Handle the possibility of responses that are not to our
                    # original request - they are ignored and we wait for a
                    # response that matches our query.
                    item, data = first(datagram=True, sleep=remaining)
                    if item == 'datagram':
                        response = from_wire(data)
                        if query.is_response(response):
                            if response.answer:
                                a_records = [r for r in response.answer if r.rdtype == A]
                                return [item.address for item in a_records[0].items]
                            raise NotFound
                        else:
                            # Not a response to our query - continue waiting for
                            # one that is.
                            remaining = remaining - (time.time() - start)
                    elif item == 'sleep':
                        break
            else:
                raise Timeout(name)
        finally:
            self.addr = self.primary


########NEW FILE########
__FILENAME__ = dreadlock
from contextlib import contextmanager
from diesel import send, until_eol, Client, call
from diesel.util.pool import ConnectionPool

class DreadlockTimeout(Exception): pass
class DreadlockError(Exception): pass

class DreadlockService(object):
    def __init__(self, host, port, pool=10):
        self.pool = ConnectionPool(
        lambda: DreadlockClient(host, port),
        lambda c: c.close())

    @contextmanager
    def hold(self, key, timeout=10.0):
        with self.pool.connection as conn:
            conn.lock(key, timeout)
            try:
                yield None
            finally:
                conn.unlock(key)

class DreadlockClient(Client):
    @call
    def lock(self, key, timeout=10.0):
        ms_timeout = int(timeout * 1000)
        send("lock %s %d\r\n" % (key, ms_timeout))
        response = until_eol()
        if response[0] == 'l':
            return
        if response[0] == 't':
            raise DreadlockTimeout(key)
        if response[0] == 'e':
            raise DreadlockError(response[2:].strip())
        assert False, response

    @call
    def unlock(self, key):
        send("unlock %s\r\n" % (key,))
        response = until_eol()
        if response[0] == 'u':
            return
        if response[0] == 'e':
            raise DreadlockError(response[2:].strip())
        assert False, response

if __name__ == '__main__':
    locker = DreadlockService('localhost', 6001)
    import uuid
    from diesel import sleep, quickstart
    def f():
        with locker.hold("foo"):
            id = uuid.uuid4()
            print "start!", id
            sleep(5)
            print "end!", id

    quickstart(f, f)

########NEW FILE########
__FILENAME__ = core
# vim:ts=4:sw=4:expandtab
'''HTTP/1.1 implementation of client and server.
'''

import cStringIO
import os
import urllib
import time
from datetime import datetime
from urlparse import urlparse
from flask import Request, Response
from OpenSSL import SSL

utcnow = datetime.utcnow

try:
    from http_parser.parser import HttpParser
except ImportError:
    from http_parser.pyparser import HttpParser

from diesel import receive, ConnectionClosed, send, log, Client, call, first

SERVER_TAG = 'diesel-http-server'

hlog = log.name("http-error")

HOSTNAME = os.uname()[1] # win32?

def parse_request_line(line):
    '''Given a request line, split it into
    (method, url, protocol).
    '''
    items = line.split(' ')
    items[0] = items[0].upper()
    if len(items) == 2:
        return tuple(items) + ('0.9',)
    items[1] = urllib.unquote(items[1])
    items[2] = items[2].split('/')[-1].strip()
    return tuple(items)

class FileLikeErrorLogger(object):
    def __init__(self, logger):
        self.logger = logger

    def write(self, s):
        self.logger.error(s)

    def writelines(self, lns):
        self.logger.error('\n'.join(list(lns)))

    def flush(self):
        pass

class HttpServer(object):
    '''An HTTP/1.1 implementation of a server.
    '''
    def __init__(self, request_handler):
        '''Create an HTTP server that calls `request_handler` on requests.

        `request_handler` is a callable that takes a `Request` object and
        generates a `Response`.

        To support WebSockets, if the `Response` generated has a `status_code` of
        101 (Switching Protocols) and the `Response` has a `new_protocol` method,
        it will be called to handle the remainder of the client connection.

        '''
        self.request_handler = request_handler

    def on_service_init(self, service):
        '''Called when this connection handler is connected to a Service.'''
        self.port = service.port

    def __call__(self, addr):
        '''Since an instance of HttpServer is passed to the Service
        class (with appropriate request_handler established during
        initialization), this __call__ method is what's actually
        invoked by diesel.
        '''
        data = None
        while True:
            try:
                h = HttpParser()
                body = []
                while True:
                    if data:
                        used = h.execute(data, len(data))
                        if h.is_headers_complete():
                            body.append(h.recv_body())
                        if h.is_message_complete():
                            data = data[used:]
                            break
                    data = receive()

                env = h.get_wsgi_environ()
                if 'HTTP_CONTENT_LENGTH' in env:
                    env['CONTENT_LENGTH'] = env.pop("HTTP_CONTENT_LENGTH")
                if 'HTTP_CONTENT_TYPE' in env:
                    env['CONTENT_TYPE'] = env.pop("HTTP_CONTENT_TYPE")

                env.update({
                    'wsgi.version' : (1,0),
                    'wsgi.url_scheme' : 'http', # XXX incomplete
                    'wsgi.input' : cStringIO.StringIO(''.join(body)),
                    'wsgi.errors' : FileLikeErrorLogger(hlog),
                    'wsgi.multithread' : False,
                    'wsgi.multiprocess' : False,
                    'wsgi.run_once' : False,
                    'REMOTE_ADDR' : addr[0],
                    'SERVER_NAME' : HOSTNAME,
                    'SERVER_PORT': str(self.port),
                    })
                req = Request(env)
                if req.headers.get('Connection', '').lower() == 'upgrade':
                    req.data = data

                resp = self.request_handler(req)
                if 'Server' not in resp.headers:
                    resp.headers.add('Server', SERVER_TAG)
                if 'Date' not in resp.headers:
                    resp.headers.add('Date', utcnow().strftime("%a, %d %b %Y %H:%M:%S UTC"))

                assert resp, "HTTP request handler _must_ return a response"

                self.send_response(resp, version=h.get_version())

                if (not h.should_keep_alive()) or \
                    resp.headers.get('Connection', '').lower() == "close" or \
                    resp.headers.get('Content-Length') == None:
                    return

                # Switching Protocols
                if resp.status_code == 101 and hasattr(resp, 'new_protocol'):
                    resp.new_protocol(req)
                    break

            except ConnectionClosed:
                break

    def send_response(self, resp, version=(1,1)):
        if 'X-Sendfile' in resp.headers:
            sendfile = resp.headers.pop('X-Sendfile')
            size = os.stat(sendfile).st_size
            resp.headers.set('Content-Length', str(size))
        else:
            sendfile = None

        send("HTTP/%s %s %s\r\n" % (('%s.%s' % version), resp.status_code, resp.status))
        send(str(resp.headers))

        if sendfile:
            send(open(sendfile, 'rb')) # diesel can stream fds
        else:
            for i in resp.iter_encoded():
                send(i)

class HttpRequestTimeout(Exception): pass

class TimeoutHandler(object):
    def __init__(self, timeout):
        self._timeout = timeout
        self._start = time.time()

    def remaining(self, raise_on_timeout=True):
        remaining = self._timeout - (time.time() - self._start)
        if remaining < 0 and raise_on_timeout:
            self.timeout()
        return remaining

    def timeout(self):
        raise HttpRequestTimeout()

def cgi_name(n):
    if n.lower() in ('content-type', 'content-length'):
        # Certain headers are defined in CGI as not having an HTTP
        # prefix.
        return n.upper().replace('-', '_')
    else:
        return 'HTTP_' + n.upper().replace('-', '_')

class HttpClient(Client):
    '''An HttpClient instance that issues 1.1 requests,
    including keep-alive behavior.

    Does not support sending chunks, yet... body must
    be a string.
    '''
    url_scheme = "http"
    @call
    def request(self, method, url, headers=None, body=None, timeout=None):
        '''Issues a `method` request to `path` on the
        connected server.  Sends along `headers`, and
        body.

        Very low level--you must set "host" yourself,
        for example.  It will set Content-Length,
        however.
        '''
        headers = headers or {}
        url_info = urlparse(url)
        fake_wsgi = dict(
        (cgi_name(n), str(v).strip()) for n, v in headers.iteritems())

        if body and 'CONTENT_LENGTH' not in fake_wsgi:
            # If the caller hasn't set their own Content-Length but submitted
            # a body, we auto-set the Content-Length header here.
            fake_wsgi['CONTENT_LENGTH'] = str(len(body))

        fake_wsgi.update({
            'REQUEST_METHOD' : method,
            'SCRIPT_NAME' : '',
            'PATH_INFO' : url_info[2],
            'QUERY_STRING' : url_info[4],
            'wsgi.version' : (1,0),
            'wsgi.url_scheme' : 'http', # XXX incomplete
            'wsgi.input' : cStringIO.StringIO(body or ''),
            'wsgi.errors' : FileLikeErrorLogger(hlog),
            'wsgi.multithread' : False,
            'wsgi.multiprocess' : False,
            'wsgi.run_once' : False,
            })
        req = Request(fake_wsgi)

        timeout_handler = TimeoutHandler(timeout or 60)

        url = str(req.path)
        if req.query_string:
            url += '?' + str(req.query_string)

        send('%s %s HTTP/1.1\r\n%s' % (req.method, url, str(req.headers)))

        if body:
            send(body)

        h = HttpParser()
        body = []
        data = None
        while True:
            if data:
                used = h.execute(data, len(data))
                if h.is_headers_complete():
                    body.append(h.recv_body())
                if h.is_message_complete():
                    data = data[used:]
                    break
            ev, val = first(receive_any=True, sleep=timeout_handler.remaining())
            if ev == 'sleep': timeout_handler.timeout()
            data = val

        resp = Response(
            response=''.join(body),
            status=h.get_status_code(),
            headers=h.get_headers(),
            )

        return resp

class HttpsClient(HttpClient):
    url_scheme = "http"
    def __init__(self, *args, **kw):
        kw['ssl_ctx'] = SSL.Context(SSL.SSLv23_METHOD)
        HttpClient.__init__(self, *args, **kw)

########NEW FILE########
__FILENAME__ = pool
import urllib
import urlparse

import diesel
import diesel.protocols.http.core as http
import diesel.util.pool as pool


# XXX This dictionary can currently grow without bounds. A pool entry gets
# created for every (host, port) key. Don't use this for a web crawler.
_pools = {}

VERSION = '3.0'
USER_AGENT = 'diesel.protocols.http.pool v%s' % VERSION
POOL_SIZE = 10

class InvalidUrlScheme(Exception):
    pass

def request(url, method='GET', timeout=60, body=None, headers=None):
    if body and (not isinstance(body, basestring)):
        body_bytes = urllib.urlencode(body)
    else:
        body_bytes = body
    req_url = urlparse.urlparse(url)
    if not headers:
        headers = {}
    headers.update({
        'Connection': 'keep-alive',
    })
    if 'Host' not in headers:
        host = req_url.netloc.split(':')[0]
        headers['Host'] = host
    if 'User-Agent' not in headers:
        headers['User-Agent'] = USER_AGENT
    if req_url.query:
        req_path = '%s?%s' % (req_url.path, req_url.query)
    else:
        req_path = req_url.path
    encoded_path = req_path.encode('utf-8')
    # Loop to retry if the connection was closed.
    for i in xrange(POOL_SIZE):
        try:
            with http_pool_for_url(req_url).connection as conn:
                resp = conn.request(method, encoded_path, headers, timeout=timeout, body=body_bytes)
            break
        except diesel.ClientConnectionClosed, e:
            # try again with another pool connection
            continue
    else:
        raise e
    return resp

def http_pool_for_url(req_url):
    host, port = host_and_port_from_url(req_url)
    if (host, port) not in _pools:
        make_client = ClientFactory(req_url.scheme, host, port)
        close_client = lambda c: c.close()
        conn_pool = pool.ConnectionPool(make_client, close_client, POOL_SIZE)
        _pools[(host, port)] = conn_pool
    return _pools[(host, port)]

def host_and_port_from_url(req_url):
    if req_url.scheme == 'http':
        default_port = 80
    elif req_url.scheme == 'https':
        default_port = 443
    else:
        raise InvalidUrlScheme(req_url.scheme)
    if ':' not in req_url.netloc:
        host = req_url.netloc
        port = default_port
    else:
        host, port_ = req_url.netloc.split(':')
        port = int(port_)
    return host, port

class ClientFactory(object):
    def __init__(self, scheme, host, port):
        if scheme == 'http':
            self.ClientClass = http.HttpClient
        elif scheme == 'https':
            self.ClientClass = http.HttpsClient
        else:
            raise InvalidUrlScheme(scheme)
        self.host = host
        self.port = port

    def __call__(self):
        return self.ClientClass(self.host, self.port)


########NEW FILE########
__FILENAME__ = irc
'''Experimental support for Internet Relay Chat'''

from diesel import Client, call, sleep, send, until_eol, receive, first, Loop, Application, ConnectionClosed, quickstop
from OpenSSL import SSL
import os, pwd
from types import GeneratorType

LOCAL_HOST = os.uname()[1]
DEFAULT_REAL_NAME = "Diesel IRC"
DEFAULT_USER = pwd.getpwuid(os.getuid()).pw_name

class IrcError(Exception): pass

class IrcCommand(object):
    def __init__(self, prefix, command, raw_params):
        self.from_server = None
        self.from_nick = None
        self.from_host = None
        self.from_user = None
        if prefix:
            if '!' in prefix:
                self.from_nick, rest = prefix.split('!')
                self.from_host, self.from_user = rest.split('@')
            else:
                self.from_server = prefix

        self.prefix = prefix
        if command.isdigit():
            command = int(command)
        self.command = command
        self.params = []

        while raw_params:
            if raw_params.startswith(":"):
                self.params.append(raw_params[1:])
                break
            parts = raw_params.split(' ', 1)
            if len(parts) == 1:
                self.params.append(raw_params)
                break
            p, raw_params = parts
            self.params.append(p)

    def __str__(self):
        return "%s (%s) %r" % (self.command, self.from_nick, self.params)

class IrcClient(Client):
    def __init__(self, nick, host='localhost', port=6667,
        user=DEFAULT_USER, name=DEFAULT_REAL_NAME, password=None,
        **kw):
        self.nick = nick
        self.user = user
        self.name = name
        self.host = host
        self.logged_in = False
        self.password = password
        Client.__init__(self, host, port, **kw)

    @call
    def on_connect(self):
        self.do_login()
        self.on_logged_in()

    def on_logged_in(self):
        pass

    @call
    def do_login(self):
        if self.password:
            self.send_command("PASS", self.password)
        self.send_command("NICK", self.nick)
        self.send_command("USER",
            '%s@%s' % (self.user, LOCAL_HOST), 
            8, '*', self.name)
        self.logged_in = True

    @call
    def send_command(self, cmd, *args):
        if self.logged_in:
            send(":%s " % self.nick)
        acc = [cmd]
        for x, a in enumerate(args):
            ax = str(a)
            if ' ' in ax:
                assert (x == (len(args) - 1)), "no spaces except in final param"
                acc.append(':' + ax)
            else:
                acc.append(ax)
        send(' '.join(acc) + "\r\n")

    @call
    def recv_command(self):
        cmd = None
        while True:
            raw = until_eol().rstrip()
            if raw.startswith(':'):
                prefix, raw = raw[1:].split(' ', 1)
            else:
                prefix = None
            command, raw = raw.split(' ', 1)
            cmd = IrcCommand(prefix, command, raw)
            if cmd.command == 'PING':
                self.send_command('PONG', *cmd.params)
            elif cmd.command == 'ERROR':
                raise IrcError(cmd.params[0])
            elif type(cmd.command) is int and cmd.command == 433:
                self.nick += '_'
                self.do_login()
            else:
                break

        return cmd

class SSLIrcClient(IrcClient):
    def __init__(self, *args, **kw):
        kw['ssl_ctx'] = SSL.Context(SSL.SSLv23_METHOD)
        IrcClient.__init__(self, *args, **kw)


class IrcBot(IrcClient):
    def __init__(self, *args, **kw):
        if 'channels' in kw:
            self.chans = set(kw.pop('channels'))
        else:
            self.chans = set()

        IrcClient.__init__(self, *args, **kw)

    def on_logged_in(self):
        for c in self.chans:
            assert not c.startswith('#')
            c = '#' + c
            self.send_command(
            'JOIN', c)

    def on_message(self, channel, nick, content):
        pass

    def run(self):
        while True:
            cmd = self.recv_command()
            if cmd.command == "PRIVMSG":
                if cmd.from_nick and len(cmd.params) == 2:
                    mchan, content = cmd.params
                    if not content.startswith('\x01') and mchan.startswith('#') and mchan[1:] in self.chans:
                        content = content.decode('utf-8')
                        r = self.on_message(mchan, cmd.from_nick, content)
                        self._handle_return(r, mchan)

    def _handle_return(self, r, chan):
        if r is None:
            pass
        elif type(r) is str:
            if r.startswith("/me"):
                r = "\x01ACTION " + r[4:] + "\x01"
            assert '\r' not in r
            assert '\n' not in r
            assert '\0' not in r
            self.send_command('PRIVMSG', chan, r)
        elif type(r) is unicode:
            self._handle_return(r.encode('utf-8'), chan)
        elif type(r) is tuple:
            chan, r = r
            self._handle_return(r, chan)
        elif type(r) is GeneratorType:
            for i in r:
                self._handle_return(i, chan)
        else:
            print 'Hmm, unknown type returned from message handler:', type(r)

class SSLIrcBot(IrcBot):
    def __init__(self, *args, **kw):
        kw['ssl_ctx'] = SSL.Context(SSL.SSLv23_METHOD)
        IrcBot.__init__(self, *args, **kw)

########NEW FILE########
__FILENAME__ = mongodb
# vim:ts=4:sw=4:expandtab
"""A mongodb client library for Diesel"""

# needed to make diesel work with python 2.5
from __future__ import with_statement

import itertools
import struct
from collections import deque
from diesel import Client, call, sleep, send, receive, first, Loop, Application, ConnectionClosed
from bson import BSON, _make_c_string, decode_all
from bson.son import SON

_ZERO = "\x00\x00\x00\x00"
HEADER_SIZE = 16

class MongoOperationalError(Exception): pass

def _full_name(parent, child):
    return "%s.%s" % (parent, child)

class TraversesCollections(object):
    def __init__(self, name, client):
        self.name = name
        self.client = client

    def __getattr__(self, name):
        return self[name]

    def __getitem__(self, name):
        cls = self.client.collection_class or Collection
        return cls(_full_name(self.name, name), self.client)


class Db(TraversesCollections):
    pass

class Collection(TraversesCollections):
    def find(self, spec=None, fields=None, skip=0, limit=0):
        return MongoCursor(self.name, self.client, spec, fields, skip, limit)

    def update(self, spec, doc, upsert=False, multi=False, safe=True):
        return self.client.update(self.name, spec, doc, upsert, multi, safe)

    def insert(self, doc_or_docs, safe=True):
        return self.client.insert(self.name, doc_or_docs, safe)

    def delete(self, spec, safe=True):
        return self.client.delete(self.name, spec, safe)

class MongoClient(Client):
    collection_class = None

    def __init__(self, host='localhost', port=27017, **kw):
        Client.__init__(self, host, port, **kw)
        self._msg_id_counter = itertools.count(1)

    @property
    def _msg_id(self):
        return self._msg_id_counter.next()

    def _put_request_get_response(self, op, data):
        self._put_request(op, data)
        header = receive(HEADER_SIZE)
        length, id, to, code = struct.unpack('<4i', header)
        message = receive(length - HEADER_SIZE)
        cutoff = struct.calcsize('<iqii')
        flag, cid, start, numret = struct.unpack('<iqii', message[:cutoff])
        body = decode_all(message[cutoff:])
        return (cid, start, numret, body)

    def _put_request(self, op, data):
        req = struct.pack('<4i', HEADER_SIZE + len(data), self._msg_id, 0, op)
        send("%s%s" % (req, data))

    def _handle_response(self, cursor, resp):
        cid, start, numret, result = resp
        cursor.retrieved += numret
        cursor.id = cid
        if not cid or (cursor.retrieved == cursor.limit):
            cursor.finished = True
        return result

    @call
    def query(self, cursor):
        op = Ops.OP_QUERY
        c = cursor
        msg = Ops.query(c.col, c.spec, c.fields, c.skip, c.limit)
        resp = self._put_request_get_response(op, msg)
        return self._handle_response(cursor, resp)

    @call
    def get_more(self, cursor):
        limit = 0
        if cursor.limit:
            if cursor.limit > cursor.retrieved:
                limit = cursor.limit - cursor.retrieved
            else:
                cursor.finished = True
        if not cursor.finished:
            op = Ops.OP_GET_MORE
            msg = Ops.get_more(cursor.col, limit, cursor.id)
            resp = self._put_request_get_response(op, msg)
            return self._handle_response(cursor, resp)
        else:
            return []

    def _put_gle_command(self):
        msg = Ops.query('admin.$cmd', {'getlasterror' : 1}, 0, 0, -1)
        res = self._put_request_get_response(Ops.OP_QUERY, msg)
        _, _, _, r = res
        doc = r[0]
        if doc.get('err'):
            raise MongoOperationalError(doc['err'])
        return doc

    @call
    def update(self, col, spec, doc, upsert=False, multi=False, safe=True):
        data = Ops.update(col, spec, doc, upsert, multi)
        self._put_request(Ops.OP_UPDATE, data)
        if safe:
            return self._put_gle_command()

    @call
    def insert(self, col, doc_or_docs, safe=True):
        data = Ops.insert(col, doc_or_docs)
        self._put_request(Ops.OP_INSERT, data)
        if safe:
            return self._put_gle_command()

    @call
    def delete(self, col, spec, safe=True):
        data = Ops.delete(col, spec)
        self._put_request(Ops.OP_DELETE, data)
        if safe:
            return self._put_gle_command()

    @call
    def drop_database(self, name):
        return self._command(name, {'dropDatabase':1})

    @call
    def list_databases(self):
        result = self._command('admin', {'listDatabases':1})
        return [(d['name'], d['sizeOnDisk']) for d in result['databases']]

    @call
    def _command(self, dbname, command):
        msg = Ops.query('%s.$cmd' % dbname, command, None, 0, 1)
        resp = self._put_request_get_response(Ops.OP_QUERY, msg)
        cid, start, numret, result = resp
        if result:
            return result[0]
        else:
            return []

    def __getattr__(self, name):
        return Db(name, self)

class Ops(object):
    ASCENDING = 1
    DESCENDING = -1
    OP_UPDATE = 2001
    OP_INSERT = 2002
    OP_GET_BY_OID = 2003
    OP_QUERY = 2004
    OP_GET_MORE = 2005
    OP_DELETE = 2006
    OP_KILL_CURSORS = 2007

    @staticmethod
    def query(col, spec, fields, skip, limit):
        data = [
            _ZERO, 
            _make_c_string(col), 
            struct.pack('<ii', skip, limit),
            BSON.encode(spec or {}),
        ]
        if fields:
            if type(fields) == dict:
                data.append(BSON.encode(fields))
            else:
                data.append(BSON.encode(dict.fromkeys(fields, 1)))
        return "".join(data)

    @staticmethod
    def get_more(col, limit, id):
        data = _ZERO
        data += _make_c_string(col)
        data += struct.pack('<iq', limit, id)
        return data

    @staticmethod
    def update(col, spec, doc, upsert, multi):
        colname = _make_c_string(col)
        flags = 0
        if upsert:
            flags |= 1 << 0
        if multi:
            flags |= 1 << 1
        fmt = '<i%dsi' % len(colname)
        part = struct.pack(fmt, 0, colname, flags)
        return "%s%s%s" % (part, BSON.encode(spec), BSON.encode(doc))

    @staticmethod
    def insert(col, doc_or_docs):
        try:
            doc_or_docs.fromkeys
            doc_or_docs = [doc_or_docs]
        except AttributeError:
            pass
        doc_data = "".join(BSON.encode(doc) for doc in doc_or_docs)
        colname = _make_c_string(col)
        return "%s%s%s" % (_ZERO, colname, doc_data)

    @staticmethod
    def delete(col, spec):
        colname = _make_c_string(col)
        return "%s%s%s%s" % (_ZERO, colname, _ZERO, BSON.encode(spec))

class MongoIter(object):
    def __init__(self, cursor):
        self.cursor = cursor
        self.cache = deque()

    def next(self):
        try:
            return self.cache.popleft()
        except IndexError:
            more = self.cursor.more()
            if not more:
                raise StopIteration()
            else:
                self.cache.extend(more)
                return self.next()
        
class MongoCursor(object):
    def __init__(self, col, client, spec, fields, skip, limit):
        self.col = col
        self.client = client
        self.spec = spec
        self.fields = fields
        self.skip = skip
        self.limit = limit
        self.id = None
        self.retrieved = 0
        self.finished = False
        self._query_additions = []

    def more(self):
        if not self.retrieved:
            self._touch_query()
        if not self.id and not self.finished:
            return self.client.query(self)
        elif not self.finished:
            return self.client.get_more(self)

    def all(self):
        return list(self)

    def __iter__(self):
        return MongoIter(self)

    def one(self):
        all = self.all()
        la = len(all)
        if la == 1:
            res = all[0]
        elif la == 0:
            res = None
        else:
            raise ValueError("Cursor returned more than 1 record")
        return res

    def count(self):
        if self.retrieved:
            raise ValueError("can't count an already started cursor")
        db, col = self.col.split('.', 1)
        l = [('count', col), ('query', self.spec)]
        if self.skip:
            l.append(('skip', self.skip))
        if self.limit:
            l.append(('limit', self.limit))

        command = SON(l)
        result = self.client._command(db, command)
        return int(result.get('n', 0))

    def sort(self, name, direction):
        if self.retrieved:
            raise ValueError("can't sort an already started cursor")
        key = SON()
        key[name] = direction
        self._query_additions.append(('sort', key))
        return self

    def _touch_query(self):
        if self._query_additions:
            spec = SON({'$query': self.spec or {}})
            for k, v in self._query_additions:
                if k == 'sort':
                    ordering = spec.setdefault('$orderby', SON())
                    ordering.update(v)
            self.spec = spec
        
    def __enter__(self):
        return self

    def __exit__(self, *args, **params):
        if self.id and not self.finished:
            raise RuntimeError("need to cleanup cursor!")

class RawMongoClient(Client):
    "A mongodb client that does the bare minimum to push bits over the wire."

    @call
    def send(self, data, respond=False):
        """Send raw mongodb data and optionally yield the server's response."""
        send(data)
        if not respond:
            return ''
        else:
            header = receive(HEADER_SIZE)
            length, id, to, opcode = struct.unpack('<4i', header)
            body = receive(length - HEADER_SIZE)
            return header + body

class MongoProxy(object):
    ClientClass = RawMongoClient

    def __init__(self, backend_host, backend_port):
        self.backend_host = backend_host
        self.backend_port = backend_port

    def __call__(self, addr):
        """A persistent client<--proxy-->backend connection handler."""
        try:
            backend = None
            while True:
                header = receive(HEADER_SIZE)
                info = struct.unpack('<4i', header)
                length, id, to, opcode = info
                body = receive(length - HEADER_SIZE)
                resp, info, body = self.handle_request(info, body)
                if resp is not None:
                    # our proxy will respond without talking to the backend
                    send(resp)
                else:
                    # pass the (maybe modified) request on to the backend
                    length, id, to, opcode = info
                    is_query = opcode in [Ops.OP_QUERY, Ops.OP_GET_MORE]
                    payload = header + body
                    (backend, resp) = self.from_backend(payload, is_query, backend)
                    self.handle_response(resp)
        except ConnectionClosed:
            if backend:
                backend.close()

    def handle_request(self, info, body):
        length, id, to, opcode = info
        print "saw request with opcode", opcode
        return None, info, body

    def handle_response(self, response):
        send(response)

    def from_backend(self, data, respond, backend=None):
        if not backend:
            backend = self.ClientClass()
            backend.connect(self.backend_host, self.backend_port)
        resp = backend.send(data, respond)
        return (backend, resp)

########NEW FILE########
__FILENAME__ = nitro
import pynitro

import diesel
from functools import partial
from diesel import log, loglevels
from diesel.events import Waiter, StopWaitDispatch
from diesel.util.queue import Queue
from diesel.util.event import Event

class DieselNitroSocket(Waiter):
    def __init__(self, bind=None, connect=None, **kwargs):
        Waiter.__init__(self)
        self.destroyed = False
        kwargs['want_eventfd'] = 1
        self.socket = pynitro.NitroSocket(**kwargs)
        self._early_value = None
        from diesel.runtime import current_app
        from diesel.hub import IntWrap

        if bind:
            assert not connect
            self.socket.bind(bind)
        elif connect:
            assert not bind
            self.socket.connect(connect)

        self.hub = current_app.hub
        self.fd = IntWrap(self.socket.fileno())

        self.read_gate = Event()
        self.hub.register(self.fd, self.messages_exist, self.error, self.error)
        self.sent = 0
        self.received = 0

    def _send_op(self, op):
        while True:
            try:
                op()
            except pynitro.NitroFull:
                diesel.sleep(0.2)
            else:
                self.sent += 1
                return

    def recv(self):
        while True:
            try:
                m = self.socket.recv(self.socket.NOWAIT)
            except pynitro.NitroEmpty:
                self.read_gate.clear()
                self.read_gate.wait()
            else:
                self.received += 1
                return m

    def send(self, frame, flags=0):
        return self._send_op(
            partial(self.socket.send, frame, self.socket.NOWAIT | flags))

    def reply(self, orig, frame, flags=0):
        return self._send_op(
            partial(self.socket.reply, orig, frame, self.socket.NOWAIT | flags))

    def process_fire(self, dc):
        if not self._early_value:
            got = self.ready_early()
            if not got:
                raise StopWaitDispatch()

        assert self._early_value
        v = self._early_value
        self._early_value = None
        return v

    def ready_early(self):
        if self._early_value:
            return True
        try:
            m = self.socket.recv(self.socket.NOWAIT)
        except pynitro.NitroEmpty:
            self.read_gate.clear()
            return False
        else:
            self.received += 1
            self._early_value = m
            return True

    def messages_exist(self):
        '''Handle state change.
        '''
        self.read_gate.set()
        diesel.fire(self)

    def error(self):
        raise RuntimeError("OH NOES, some weird nitro FD callback")


    def destroy(self):
        if not self.destroyed:
            self.hub.unregister(self.fd)
            del self.socket
            self.destroyed = True

    def __enter__(self):
        return self

    def __del__(self):
        self.destroy()

    def __exit__(self, *args):
        self.destroy()

class DieselNitroService(object):
    """A Nitro service that can handle multiple clients.

    Clients must maintain a steady flow of messages in order to maintain
    state in the service. A heartbeat of some sort. Or the timeout can be
    set to a sufficiently large value understanding that it will cause more
    resource consumption.

    """
    name = ''
    default_log_level = loglevels.DEBUG
    timeout = 10

    def __init__(self, uri, logger=None, log_level=None):
        self.uri = uri
        self.nitro_socket = None
        self.log = logger or None
        self.selected_log_level = log_level
        self.clients = {}
        self.outgoing = Queue()
        self.incoming = Queue()
        self.name = self.name or self.__class__.__name__
        self._incoming_loop = None

        # Allow for custom `should_run` properties in subclasses.
        try:
            self.should_run = True
        except AttributeError:
            # A custom `should_run` property exists.
            pass

        if self.log and self.selected_log_level is not None:
            self.selected_log_level = None
            warnings.warn(
                "ignored `log_level` argument since `logger` was provided.",
                RuntimeWarning,
                stacklevel=2,
            )

    def _create_server_socket(self):
        self.nitro_socket = DieselNitroSocket(bind=self.uri)

    def _setup_the_logging_system(self):
        if not self.log:
            if self.selected_log_level is not None:
                log_level = self.selected_log_level
            else:
                log_level = self.default_log_level
            log_name = self.name or self.__class__.__name__
            self.log = log.name(log_name)
            self.log.min_level = log_level

    def _handle_client_requests_and_responses(self, remote_client):
        assert self.nitro_socket
        queues = [remote_client.incoming]
        try:
            while True:
                (evt, value) = diesel.first(waits=queues, sleep=self.timeout)
                if evt is remote_client.incoming:
                    assert isinstance(value, Message)
                    remote_client.async_frame = value.orig_frame
                    resp = self.handle_client_packet(value.data, remote_client.context)
                    if resp:
                        if isinstance(resp, basestring):
                            output = [resp]
                        else:
                            output = iter(resp)
                        for part in output:
                            msg = Message(
                                value.orig_frame,
                                remote_client.identity,
                                self.serialize_message(remote_client.identity, part),
                            )
                            self.outgoing.put(msg)
                elif evt == 'sleep':
                    break
        finally:
            self._cleanup_client(remote_client)

    def _cleanup_client(self, remote_client):
        del self.clients[remote_client.identity]
        self.cleanup_client(remote_client)
        self.log.debug("cleaned up client %r" % remote_client.identity)

    def _handle_all_inbound_and_outbound_traffic(self):
        assert self.nitro_socket
        queues = [self.nitro_socket, self.outgoing]
        socket = self.nitro_socket
        make_frame = pynitro.NitroFrame
        while self.should_run:
            (queue, msg) = diesel.first(waits=queues)

            if queue is self.outgoing:
                socket.reply(msg.orig_frame, make_frame(msg.data))
            else:
                id, obj = self.parse_message(msg.data)
                msg.clear_data()
                msg = Message(msg, id, obj)
                if msg.identity not in self.clients:
                    self._register_client(msg)
                self.clients[msg.identity].incoming.put(msg)


    def _register_client(self, msg):
        remote = RemoteClient.from_message(msg)
        self.clients[msg.identity] = remote
        self.register_client(remote, msg)
        diesel.fork_child(self._handle_client_requests_and_responses, remote)

    # Public API
    # ==========

    def __call__(self):
        return self.run()

    def run(self):
        self._create_server_socket()
        self._setup_the_logging_system()
        self._handle_all_inbound_and_outbound_traffic()

    def handle_client_packet(self, packet, context):
        """Called with a bytestring packet and dictionary context.

        Return an iterable of bytestrings.

        """
        raise NotImplementedError()

    def cleanup_client(self, remote_client):
        """Called with a RemoteClient instance. Do any cleanup you need to."""
        pass

    def register_client(self, remote_client, msg):
        """Called with a RemoteClient instance. Do any registration here."""
        pass

    def parse_message(self, raw_data):
        """Subclasses can override to alter the handling of inbound data.

        Transform an incoming bytestring into a structure (aka, json.loads)
        """
        return None, raw_data

    def serialize_message(self, identity, raw_data):
        """Subclasses can override to alter the handling of outbound data.

        Turn some structure into a bytestring (aka, json.dumps)
        """
        return raw_data

    def async_send(self, identity, msg):
        """Raises KeyError if client is no longer connected.
        """
        remote_client = self.clients[identity]
        out = self.serialize_message(msg)
        self.outgoing.put(
            Message(
                remote_client.async_frame,
                identity,
                out))

class RemoteClient(object):
    def __init__(self, identity):

        # The identity is some information sent along with packets from the
        # remote client that uniquely identifies it.

        self.identity = identity

        # The incoming queue is typically populated by the DieselNitroService
        # and represents a queue of messages send from the remote client.

        self.incoming = Queue()

        # The context in general is a place where you can put data that is
        # related specifically to the remote client and it will exist as long
        # the remote client doesn't timeout.

        self.context = {}

        # A skeleton frame to hang onto for async sending back
        self.async_frame = None

    @classmethod
    def from_message(cls, msg):
        return cls(msg.identity)


class Message(object):
    def __init__(self, frame, identity, data):
        self.orig_frame = frame
        self.identity = identity
        self.data = data

########NEW FILE########
__FILENAME__ = pg
# TODO -- more types

from contextlib import contextmanager
import itertools
from struct import pack, unpack

from diesel import Client, call, sleep, send, until, receive, first, Loop, Application, ConnectionClosed, quickstop

izip = itertools.izip

class Rollback(Exception): pass

class PgDataRow(list): pass
class PgStateChange(object): pass
class PgPortalSuspended(object): pass
class PgCommandComplete(str): pass
class PgParameterDescription(list): pass
class PgParseComplete(object): pass
class PgBindComplete(object): pass
class PgAuthOkay(object): pass
class PgAuthClear(object): pass
class PgAuthMD5(object):
    def __init__(self, salt):
        self.salt = salt

class PgRowDescriptor(object):
    def __init__(self, row_names, row_oids):
        self.row_names = row_names
        self.values = [NotImplementedError()] * len(row_names)
        self.lookup = dict((n, i) for i, n in enumerate(row_names))
        self.convs = [oid_to_conv(id) for id in row_oids]

    def __getattr__(self, n):
        return self.values[self.lookup[n]]

    def __getitem__(self, n):
        return self.values[self.lookup[n]]

    def load_row(self, ts):
        for x, (conv, v) in enumerate(izip(self.convs, ts)):
            self.values[x] = conv(v) if v is not None else None

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "PgRowDescriptor of %r" % [
            getattr(self, n) for n in self.row_names]

class PgServerError(Exception): pass

class PostgreSQLClient(Client):
    def __init__(self, host='localhost', port=5432, user='postgres', database='template1', **kw):
        self.in_query = False
        self.user = user
        self.database = database
        self.params = {}
        self.cancel_secret = None
        self.process_id = None
        self.state = None
        self.prepare_gen = itertools.count(0)
        self.prepared = {}
        Client.__init__(self, host, port, **kw)

    def on_connect(self):
        self.send_startup()
        auth = self.read_message()
        if not isinstance(auth, PgAuthOkay):
            self.do_authentication(auth)
        self.wait_for_queries()

    @call
    def send_startup(self):
        params='user\0{0}\0database\0{1}\0\0'.format(self.user, self.database)
        send(pack('!ii', 8 + len(params), 3 << 16 | 0))
        send(params)

    @call
    def wait_for_queries(self):
        while True:
            self.read_message()
            if self.state == 'I':
                break

    @call
    def wait_for_state(self):
        s = self.read_message()
        assert isinstance(s, PgStateChange)

    @call
    def read_message(self):
        b = receive(1)
        return self.msg_handlers[b](self)

    def handle_authentication(self):
        (size, stat) = unpack("!ii", receive(8))

        if stat == 0:
            return PgAuthOkay()
        elif stat == 5:
            return PgAuthClear()
        elif stat == 5:
            salt = receive(4)
            return PgAuthMD5(salt)
        else:
            raise NotImplementedError("Only MD5 authentication supported")

    def handle_error(self):
        (size,) = unpack("!i", receive(4))

        size -= 4
        d = {}
        while size:
            (key,) = unpack('!b', receive(1))
            if key == 0:
                break
            value = until('\0')
            size -= (1 + len(value))
            d[key] = value[:-1]

        raise PgServerError(d[ord('M')])

    def handle_param(self):
        (size,) = unpack("!i", receive(4))
        size -= 4
        key = until('\0')
        value = until('\0')
        assert len(key) + len(value) == size
        self.params[key[:-1]] = value[:-1]

    def handle_secret_key(self):
        (size,pid,key) = unpack("!iii", receive(12))
        self.process_id = pid
        self.cancel_secret = key

    def handle_ready(self):
        (size,s) = unpack("!ib", receive(5))
        self.state = chr(s)
        self.in_query = False
        return PgStateChange()

    def handle_command_complete(self):
        (size,) = unpack("!i", receive(4))
        tag = receive(size - 4)
        return PgCommandComplete(tag[:-1])

    def handle_parse_complete(self):
        (size,) = unpack("!i", receive(4))
        return PgParseComplete()

    def handle_bind_complete(self):
        (size,) = unpack("!i", receive(4))
        return PgBindComplete()

    def handle_nodata(self):
        (size,) = unpack("!i", receive(4))
        # effectively, ignore

    def handle_portal_suspended(self):
        (size,) = unpack("!i", receive(4))
        return PgPortalSuspended()

    def handle_parameter_description(self):
        oids = []
        (size, n) = unpack("!ih", receive(6))
        rest = unpack('!' + ('i' * n), receive(size - 6))
        return PgParameterDescription(rest)

    def handle_row_description(self):
        (size, n) = unpack("!ih", receive(6))

        names = []
        types = []
        for x in xrange(n):
            name = until('\0')[:-1]
            names.append(name)
            taboid, fattnum, typoid, sz, typmod, fmt = \
            unpack('!ihihih', receive(18))

            assert fmt == 0
            types.append(typoid)

        return PgRowDescriptor(names, types)

    @call
    def close(self):
        if not self.is_closed:
            send('X' + pack('!i', 4))
        Client.close(self)

    def handle_data(self):
        (size, n) = unpack("!ih", receive(6))
        values = PgDataRow()
        for x in xrange(n):
            (l,) = unpack('!i', receive(4))
            if l == -1:
                values.append(None)
            else:
                values.append(receive(l))

        return values

    @property
    @contextmanager
    def transact(self):
        assert self._query("BEGIN") == "BEGIN"
        self.wait_for_state()
        assert self.state == "T"

        try:
            yield self
        except Rollback:
            assert self.state == "T"
            assert self._query("ROLLBACK") == "ROLLBACK"
            self.wait_for_state()
            assert self.state == "I"
        else:
            assert not self.in_query, "Cannot commit with unconsumed query data"
            assert self.state == "T"
            assert self._query("COMMIT") == "COMMIT"
            self.wait_for_state()
            assert self.state == "I"

    def _simple_send(self, code, thing):
        send(code + pack("!i", len(thing) + 4))
        send(thing)

    @call
    def _query(self, q):
        assert self.state != "E"
        self._simple_send("Q", q + '\0')
        return self.read_message()

    @call
    def prepare(self, q, id):
        print 'PREP'
        q += '\0'
        sid = id + '\0'
        send('P' + pack('!i', 4 + len(q) + len(sid) + 2))
        send(sid)
        send(q)
        send(pack('!h', 0))

    @call
    def _execute(self, rows=0, describe=False):

        if describe:
            # request description
            send('D' + pack('!i', 4 + 1 + 1) + 'P' + '\0')

        send("E" + pack('!i', 4 + 1 + 4))
        send("\0" + pack('!i', rows))

    def _bind(self, id, args):
        acc = []
        acc.append("\0"         # portal name (default)
            "%s\0"              # prepared id
            "\0\0"              # no format codes (use text)
            % (id,)
            )

        # parameter data
        acc.append(pack("!h", len(args)))
        for t in args:
            s = py_to_pg(t)
            acc.append(pack('!i', len(s)))
            acc.append(s)

        acc.append('\0\0')      # no result-column types
        t = ''.join(acc)
        send('B' + pack('!i', len(t) + 4))
        send(t)

    @call
    def _sync(self):
        send('S' + pack('!i', 4))

    @call
    def _queue_query(self, q, args):
        prep = False
        if q in self.prepared:
            id = self.prepared[q]
        else:
            id = 'q%d' % self.prepare_gen.next()
            self.prepare(q, id)
            self.prepared[q] = id
            prep = True

        self._bind(id, args)
        return prep

    def handle_description(self):
        row_oids = self.read_message()
        assert isinstance(row_oids, PgParameterDescription)

    @call
    def execute(self, q, *args):
        prepared = self._queue_query(q, args)
        self._execute()
        self._sync()

        if prepared:
            assert isinstance(self.read_message(), PgParseComplete)

        assert isinstance(self.read_message(), PgBindComplete)

        m = self.read_message()
        assert isinstance(m, PgCommandComplete), "No results expected from execute() query"

        self.wait_for_state()

    @call
    def query_one(self, *args, **kw):
        i = self.query(*args, **kw)
        vs = list(i)

        if not vs:
            return None
        if len(vs) != 1:
            raise OperationalError("more than one result returned from query_one()")

        return vs[0]

    @call
    def query(self, q, *args, **kw):
        rows = kw.pop('buffer', 0)
        assert not kw, ("unknown keyword arguments: %r" % kw)

        prepared = self._queue_query(q, args)

        self._execute(rows, describe=True)
        self._sync()

        if prepared:
            assert isinstance(self.read_message(), PgParseComplete)

        assert isinstance(self.read_message(), PgBindComplete)

        row_desc = self.read_message()
        assert isinstance(row_desc, PgRowDescriptor)

        def yielder():
            while True:
                n = self.read_message()
                if isinstance(n, PgDataRow):
                    row_desc.load_row(n)
                    yield row_desc
                elif isinstance(n, PgPortalSuspended):
                    self._execute(rows)
                    self._sync()
                elif isinstance(n, PgCommandComplete):
                    break

            self.wait_for_state()

        self.in_query = True
        return yielder()

    msg_handlers = {
        'R' : handle_authentication,
        'S' : handle_param,
        'E' : handle_error,
        'K' : handle_secret_key,
        'Z' : handle_ready,
        'C' : handle_command_complete,
        '1' : handle_parse_complete,
        '2' : handle_bind_complete,
        't' : handle_parameter_description,
        'n' : handle_nodata,
        'T' : handle_row_description,
        'D' : handle_data,
        's' : handle_portal_suspended,
    }

#### TYPES

def py_to_pg(o):
    t = type(o)
    return {
        bool : lambda d: 't' if d else 'f',
        str : str,
        unicode : lambda a: a.encode('utf8'),
        int : str,
    }[t](o)

def oid_to_conv(id):
    return {
        16 : lambda d: d.startswith('t'),
        20 : int,
        21 : int,
        23 : int,
        26 : str,
        1042 : lambda s: unicode(s, 'utf-8'),
        1043 : lambda s: unicode(s, 'utf-8'),
    }[id]

if __name__ == '__main__':
    def f():
        with PostgreSQLClient(database="test", user="test") as client:
            with client.transact:
                client.execute("INSERT INTO companies (name) values ($1)"
                , "JamieCo3")
                client.execute("INSERT INTO typtest values ($1, $2, $3, $4, $5, $6)"
                , "string", "string", 14, 155, 23923, True)
                #for row in client.query("SELECT * FROM companies", buffer=500):
                #    print row.name
                #    print row.id
                for row in client.query("SELECT * FROM typtest", buffer=500):
                    print row

            client.execute("UPDATE companies set name = $1 where id < $2",
            "marky co", 5)

        print '\n\n~~~done!~~~'

    def g():
        with PostgreSQLClient(database="test", user="test") as client:
            for x in xrange(500):
                r = client.query_one(
                "select * from counters where id = $1 for update", 1)
        print 'done'


    from diesel import quickstart
    quickstart(f, g, g, g, g, g, g, g, g, g, g, g)

########NEW FILE########
__FILENAME__ = redis
from contextlib import contextmanager
from diesel import (Client, call, until_eol, receive,
                    fire, send, first, fork, sleep)
from diesel.util.queue import Queue, QueueTimeout
import time
import operator as op
import itertools
import uuid

def flatten_arg_pairs(l):
    o = []
    for i in l:
        o.extend(i)
    return o

REDIS_PORT = 6379

class RedisError(Exception): pass

class RedisClient(Client):
    def __init__(self, host='localhost', port=REDIS_PORT, password=None, **kw):
        self.password = password
        Client.__init__(self, host, port, **kw)

    ##################################################
    ### GENERAL OPERATIONS
    @call
    def auth(self):
        self._send('AUTH', self.password)
        resp = self._get_response()
        return bool(resp)
    @call
    def exists(self, k):
        self._send('EXISTS', k)
        resp = self._get_response()
        return bool(resp)

    @call
    def delete(self, k):
        self._send('DEL', k)
        resp = self._get_response()
        return bool(resp)

    @call
    def type(self, k):
        self._send('TYPE', k)
        resp = self._get_response()
        return resp

    @call
    def keys(self, pat):
        self._send('KEYS', pat)
        resp = self._get_response()
        return set(resp)

    @call
    def randomkey(self):
        self._send('RANDOMKEY')
        resp = self._get_response()
        return resp

    @call
    def rename(self, old, new):
        self._send('RENAME', old, new)
        resp = self._get_response()
        return resp

    @call
    def renamenx(self, old, new):
        self._send('RENAMENX', old, new)
        resp = self._get_response()
        return resp

    @call
    def dbsize(self):
        self._send('DBSIZE')
        resp = self._get_response()
        return resp

    @call
    def expire(self, key, seconds):
        self._send('EXPIRE', key, seconds)
        resp = self._get_response()
        return resp

    @call
    def expireat(self, key, when):
        unix_time = time.mktime(when.timetuple())
        self._send('EXPIREAT', key, unix_time)
        resp = self._get_response()
        return resp

    @call
    def ttl(self, key):
        self._send('TTL', key)
        resp = self._get_response()
        resp = None if resp == -1 else int(resp)
        return resp

    @call
    def select(self, idx):
        self._send('SELECT', idx)
        resp = self._get_response()
        return resp

    @call
    def move(self, key, idx):
        self._send('MOVE', key, idx)

    @call
    def flushdb(self):
        self._send('FLUSHDB')
        resp = self._get_response()
        return resp

    @call
    def flushall(self):
        self._send('FLUSHALL')
        resp = self._get_response()
        return resp

    ##################################################
    ### TRANSACTION OPERATIONS
    ### http://redis.io/topics/transactions
    @call
    def multi(self):
        """Starts a transaction."""
        self._send('MULTI')
        return self._get_response()

    @call
    def exec_(self):
        """Atomically executes queued commands in a transaction."""
        self._send('EXEC')
        return self._get_response()

    @call
    def discard(self):
        """Discards any queued commands and aborts a transaction."""
        self._send('DISCARD')
        return self._get_response()

    @call
    def watch(self, keys):
        """Sets up keys to be watched in preparation for a transaction."""
        self._send('WATCH', list=keys)
        return self._get_response()

    def transaction(self, watch=None):
        """Returns a RedisTransaction context manager.

        If watch is supplied, it should be a list of keys to be watched for
        changes. The transaction will be aborted if the value of any of the
        keys is changed outside of the transaction.

        A transaction can be invoked with Python's ``with`` statement for
        atomically executing a series of commands.

        >>> transaction = client.transaction(watch=['dependent_var_1'])
        >>> dv1 = client.get('dependent_var_1')
        >>> with transaction as t:
        ...     composite_val = compute(dv1)
        ...     t.set('dependent_var_2', composite_val)
        >>> print t.value

        """
        return RedisTransaction(self, watch or [])

    ##################################################
    ### STRING OPERATIONS
    @call
    def set(self, k, v):
        self._send('SET', k, v)
        resp = self._get_response()
        return resp

    @call
    def get(self, k):
        self._send('GET', k)
        resp = self._get_response()
        return resp

    @call
    def getset(self, k, v):
        self._send('GETSET', k, v)
        resp = self._get_response()
        return resp

    @call
    def mget(self, keylist):
        self._send('MGET', list=keylist)
        resp = self._get_response()
        return resp

    @call
    def setnx(self, k, v):
        self._send('SETNX', k, v)
        resp = self._get_response()
        return resp

    @call
    def setex(self, k, tm, v):
        self._send('SETEX', k, tm, v)
        resp = self._get_response()
        return resp

    @call
    def mset(self, d):
        self._send('MSET', list=flatten_arg_pairs(d.iteritems()))
        resp = self._get_response()
        return resp

    @call
    def msetnx(self, d):
        self._send('MSETNX', list=flatten_arg_pairs(d.iteritems()))
        resp = self._get_response()
        return resp

    @call
    def incr(self, k):
        self._send('INCR', k)
        resp = self._get_response()
        return resp

    @call
    def incrby(self, k, amt):
        self._send('INCRBY', k, amt)
        resp = self._get_response()
        return resp

    @call
    def decr(self, k):
        self._send('DECR', k)
        resp = self._get_response()
        return resp

    @call
    def decrby(self, k, amt):
        self._send('DECRBY', k, amt)
        resp = self._get_response()
        return resp

    @call
    def append(self, k, value):
        self._send('APPEND', k, value)
        resp = self._get_response()
        return resp

    @call
    def substr(self, k, start, end):
        self._send('SUBSTR', k, start, end)
        resp = self._get_response()
        return resp

    @call
    def getbit(self, k, offset):
        self._send('GETBIT', k, offset)
        resp = self._get_response()
        return int(resp)

    @call
    def setbit(self, k, offset, value):
        self._send('SETBIT', k, offset, value)
        resp = self._get_response()
        return resp

    @call
    def strlen(self, k):
        self._send('STRLEN', k)
        resp = self._get_response()
        return int(resp)


    ##################################################
    ### LIST OPERATIONS
    @call
    def rpush(self, k, v):
        self._send('RPUSH', k, v)
        resp = self._get_response()
        return resp

    @call
    def lpush(self, k, v):
        self._send('LPUSH', k, v)
        resp = self._get_response()
        return resp

    @call
    def llen(self, k):
        self._send('LLEN', k)
        resp = self._get_response()
        return resp

    @call
    def lrange(self, k, start, end):
        self._send('LRANGE', k, start, end)
        resp = self._get_response()
        return resp

    @call
    def ltrim(self, k, start, end):
        self._send('LTRIM', k, start, end)
        resp = self._get_response()
        return resp

    @call
    def lindex(self, k, idx):
        self._send('LINDEX', k, idx)
        resp = self._get_response()
        return resp

    @call
    def lset(self, k, idx, v):
        self._send('LSET', k, idx,  v)
        resp = self._get_response()
        return resp

    @call
    def lrem(self, k, v, count=0):
        self._send('LREM', k, count, v)
        resp = self._get_response()
        return resp

    @call
    def lpop(self, k):
        self._send('LPOP', k)
        resp = self._get_response()
        return resp

    @call
    def rpop(self, k):
        self._send('RPOP', k)
        resp = self._get_response()
        return resp

    @call
    def blpop(self, keylist, timeout=0):
        self._send('BLPOP', list=list(keylist) + [timeout])
        resp = self._get_response()
        if resp:
            assert len(resp) == 2
            resp = tuple(resp)
        else:
            resp = None
        return resp

    @call
    def brpop(self, keylist, timeout=0):
        self._send('BRPOP', list=list(keylist) + [timeout])
        resp = self._get_response()
        if resp:
            assert len(resp) == 2
            resp = tuple(resp)
        else:
            resp = None
        return resp

    @call
    def rpoplpush(self, src, dest):
        self._send('RPOPLPUSH', src, dest)
        resp = self._get_response()
        return resp

    ##################################################
    ### SET OPERATIONS
    @call
    def sadd(self, k, v):
        self._send('SADD', k, v)
        resp = self._get_response()
        return resp

    @call
    def srem(self, k, v):
        self._send('SREM', k, v)
        resp = self._get_response()
        return bool(resp)

    @call
    def spop(self, k):
        self._send('SPOP', k)
        resp = self._get_response()
        return resp

    @call
    def smove(self, src, dst, v):
        self._send('SMOVE', src, dst, v)
        resp = self._get_response()
        return resp

    @call
    def scard(self, k):
        self._send('SCARD', k)
        resp = self._get_response()
        return resp

    @call
    def sismember(self, k, v):
        self._send('SISMEMBER', k, v)
        resp = self._get_response()
        return bool(resp)

    @call
    def sinter(self, keylist):
        self._send('SINTER', list=keylist)
        resp = self._get_response()
        return set(resp)

    @call
    def sinterstore(self, dst, keylist):
        flist = [dst] + list(keylist)
        self._send('SINTERSTORE', list=flist)
        resp = self._get_response()
        return resp

    @call
    def sunion(self, keylist):
        self._send('SUNION', list=keylist)
        resp = self._get_response()
        return set(resp)

    @call
    def sunionstore(self, dst, keylist):
        flist = [dst] + list(keylist)
        self._send('SUNIONSTORE', list=flist)
        resp = self._get_response()
        return resp

    @call
    def sdiff(self, keylist):
        self._send('SDIFF', list=keylist)
        resp = self._get_response()
        return set(resp)

    @call
    def sdiffstore(self, dst, keylist):
        flist = [dst] + list(keylist)
        self._send('SDIFFSTORE', list=flist)
        resp = self._get_response()
        return resp

    @call
    def smembers(self, key):
        self._send('SMEMBERS', key)
        resp = self._get_response()
        return set(resp)

    @call
    def srandmember(self, key):
        self._send('SRANDMEMBER', key)
        resp = self._get_response()
        return resp

    ##################################################
    ### ZSET OPERATIONS

    def __pair_with_scores(self, resp):
        return [(resp[x], float(resp[x+1]))
                for x in xrange(0, len(resp), 2)]

    @call
    def zadd(self, key, score, member):
        self._send('ZADD', key, score, member)
        resp = self._get_response()
        return resp

    @call
    def zrem(self, key, member):
        self._send('ZREM', key, member)
        resp = self._get_response()
        return bool(resp)

    @call
    def zrange(self, key, start, end, with_scores=False):
        args = 'ZRANGE', key, start, end
        if with_scores:
            args += 'WITHSCORES',
        self._send(*args)
        resp = self._get_response()
        if with_scores:
            return self.__pair_with_scores(resp)
        return resp

    @call
    def zrevrange(self, key, start, end, with_scores=False):
        args = 'ZREVRANGE', key, start, end
        if with_scores:
            args += 'WITHSCORES',
        self._send(*args)
        resp = self._get_response()
        if with_scores:
            return self.__pair_with_scores(resp)
        return resp

    @call
    def zcard(self, key):
        self._send('ZCARD', key)
        resp = self._get_response()
        return int(resp)

    @call
    def zscore(self, key, member):
        self._send('ZSCORE', key, member)
        resp = self._get_response()
        return float(resp) if resp is not None else None

    @call
    def zincrby(self, key, increment, member):
        self._send('ZINCRBY', key, increment, member)
        resp = self._get_response()
        return float(resp)

    @call
    def zrank(self, key, member):
        self._send('ZRANK', key, member)
        resp = self._get_response()
        return resp

    @call
    def zrevrank(self, key, member):
        self._send('ZREVRANK', key, member)
        resp = self._get_response()
        return resp

    @call
    def zrangebyscore(self, key, min, max, offset=None, count=None, with_scores=False):
        args = 'ZRANGEBYSCORE', key, min, max
        if offset:
            assert count is not None, "if offset specified, count must be as well"
            args += 'LIMIT', offset, count
        if with_scores:
            args += 'WITHSCORES',

        self._send(*args)
        resp = self._get_response()

        if with_scores:
            return self.__pair_with_scores(resp)

        return resp

    @call
    def zcount(self, key, min, max):
        self._send('ZCOUNT', key, min, max)
        resp = self._get_response()
        return resp

    @call
    def zremrangebyrank(self, key, min, max):
        self._send('ZREMRANGEBYRANK', key, min, max)
        resp = self._get_response()
        return resp

    @call
    def zremrangebyscore(self, key, min, max):
        self._send('ZREMRANGEBYSCORE', key, min, max)
        resp = self._get_response()
        return resp

    ##################################################
    ### HASH OPERATIONS
    @call
    def hset(self, key, field, value):
        self._send('HSET', key, field, value)
        resp = self._get_response()
        return bool(resp)

    @call
    def hget(self, key, field):
        self._send('HGET', key, field)
        resp = self._get_response()
        return resp


    @call
    def hmset(self, key, d):
        if not d:
            return True
        args = [key] + flatten_arg_pairs(d.iteritems())

        self._send('HMSET', list=args)
        resp = self._get_response()
        return bool(resp)

    @call
    def hmget(self, key, l):
        if not l:
            return {}
        args = [key] + l
        self._send('HMGET', list=args)
        resp = self._get_response()
        return dict(zip(l, resp))

    @call
    def hincrby(self, key, field, amt):
        self._send('HINCRBY', key, field, amt)
        resp = self._get_response()
        return resp

    @call
    def hexists(self, key, field):
        self._send('HEXISTS', key, field)
        resp = self._get_response()
        return bool(resp)

    @call
    def hdel(self, key, field):
        self._send('HDEL', key, field)
        resp = self._get_response()
        return bool(resp)

    @call
    def hlen(self, key):
        self._send('HLEN', key)
        resp = self._get_response()
        return resp

    @call
    def hkeys(self, key):
        self._send('HKEYS', key)
        resp = self._get_response()
        return set(resp)

    @call
    def hvals(self, key):
        self._send('HVALS', key)
        resp = self._get_response()
        return resp

    @call
    def hgetall(self, key):
        self._send('HGETALL', key)
        resp = self._get_response()
        return dict(resp[x:x+2] for x in xrange(0, len(resp), 2))

    @call
    def hsetnx(self, key, field, value):
        self._send('HSETNX', key, field, value)
        resp = self._get_response()
        return bool(resp)

    ##################################################
    ### Sorting...
    @call
    def sort(self, key, pattern=None, limit=None,
    get=None, order='ASC', alpha=False, store=None):

        args = [key]
        if pattern:
            args += ['BY', pattern]

        if limit:
            args += ['LIMIT'] + list(limit)

        if get:
            args += ['GET', get]

        args += [order]

        if alpha:
            args += 'ALPHA'

        if store:
            args += ['STORE', store]

        self._send('SORT', *args)
        resp = self._get_response()
        return resp

    @call
    def subscribe(self, *channels):
        '''Subscribe to the given channels.

        Note: assumes subscriptions succeed
        '''
        self._send('SUBSCRIBE', *channels)
        return None

    @call
    def unsubscribe(self, *channels):
        '''Unsubscribe from the given channels, or all of them if none are given.

        Note: assumes subscriptions don't succeed
        '''
        self._send('UNSUBSCRIBE', *channels)
        return None

    @call
    def psubscribe(self, *channels):
        '''Subscribe to the given glob pattern-matched channels.

        Note: assumes subscriptions succeed
        '''
        self._send('PSUBSCRIBE', *channels)
        return None

    @call
    def punsubscribe(self, *channels):
        '''Unsubscribe from the given glob pattern-matched channels, or all of them if none are given.

        Note: assumes subscriptions don't succeed
        '''
        self._send('PUNSUBSCRIBE', *channels)
        return None

    @call
    def get_from_subscriptions(self, wake_sig=None):
        '''Wait for a published message on a subscribed channel.

        Returns a tuple consisting of:

            * The subscription pattern which matched
                (the same as the channel for non-glob subscriptions)
            * The channel the message was received from.
            * The message itself.

        -- OR -- None, if wake_sig was fired

        NOTE: The message will always be a string.  Handle this as you see fit.
        NOTE: subscribe/unsubscribe acks are ignored here
        '''
        while True:
            r = self._get_response(wake_sig)
            if r:
                if r[0] == 'message':
                    return [r[1]] + r[1:]
                elif r[0] == 'pmessage':
                    return r[1:]
            else:
                return None


    @call
    def publish(self, channel, message):
        '''Publish a message on the given channel.

        Returns the number of clients that received the message.
        '''
        self._send('PUBLISH', channel, message)
        resp = self._get_response()
        return resp

    @call
    def send_raw_command(self, arguments):
        cmd, rest = arguments[0], arguments[1:]
        self._send(cmd, list=rest)

        line_one = until_eol()
        if line_one[0] in ('+', '-', ':'):
            return line_one

        if line_one[0] == '$':
            amt = int(line_one[1:])
            if amt == -1:
                return line_one
            return line_one + receive(amt) + until_eol()
        if line_one[0] == '*':
            nargs = int(line_one[1:])
            if nargs == -1:
                return line_one
            out = line_one
            for x in xrange(nargs):
                head = until_eol()
                out += head
                out += receive(int(head[1:])) + until_eol()
            return out

    def _send(self, cmd, *args, **kwargs):
        if 'list' in kwargs:
            args = kwargs['list']
        all = (cmd,) + tuple(str(s) for s in args)
        send('*%s\r\n' % len(all))
        for i in all:
            send(('$%s\r\n' % len(i)) + i + '\r\n')

    def _get_response(self, wake_sig=None):
        if wake_sig:
            ev, val = first(until_eol=True, waits=[wake_sig])
            if ev != 'until_eol':
                return None
            fl = val.strip()
        else:
            fl = until_eol().strip()

        c = fl[0]
        if c == '+':
            return fl[1:]
        elif c == '$':
            l = int(fl[1:])
            if l == -1:
                resp = None
            else:
                resp = receive(l)
                until_eol() # noop
            return resp
        elif c == '*':
            count = int(fl[1:])
            resp = []
            if count == -1:
                return None
            for x in xrange(count):
                hl = until_eol()
                assert hl[0] in ['$', ':', '+']
                if hl[0] == '$':
                    l = int(hl[1:])
                    if l == -1:
                        resp.append(None)
                    else:
                        resp.append(receive(l))
                        until_eol() # noop
                elif hl[0] == ':':
                    resp.append(int(hl[1:]))
                elif hl[0] == '+':
                    resp.append(hl[1:].strip())
            return resp
        elif c == ':':
            return int(fl[1:])
        elif c == '-':
            e_message = fl[1:]
            raise RedisError(e_message)

class RedisTransaction(object):
    """A context manager for doing transactions with a RedisClient."""

    def __init__(self, client, watch_keys):
        """Returns a new RedisTransaction instance.

        The client argument should be a RedisClient instance and watch_keys
        should be a list of keys to watch.

        Handles calling the Redis WATCH, MULTI, EXEC and DISCARD commands to
        manage transactions. Calls WATCH to watch keys for changes, MULTI to
        start the transaction, EXEC to complete it or DISCARD to abort if there
        was an exception.

        Instances proxy method calls to the client instance. If the transaction
        is successful, the value attribute will contain the results.

        See http://redis.io/topics/transactions for more details.

        """
        self.client = client
        self.value = None
        self.watching = watch_keys
        self.aborted = False
        if watch_keys:
            self.client.watch(watch_keys)

    def __getattr__(self, name):
        return getattr(self.client, name)

    def __enter__(self):
        # Begin the transaction.
        self.client.multi()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if any([exc_type, exc_val, exc_tb]):
            # There was an error. Abort the transaction.
            self.client.discard()
            self.aborted = True
        else:
            # Try and execute the transaction.
            self.value = self.client.exec_()
            if self.value is None:
                self.aborted = True
                msg = 'A watched key changed before the transaction completed.'
                raise RedisTransactionError(msg)

        # Instruct Python not to swallow exceptions generated in the
        # transaction block.
        return False

class RedisTransactionError(Exception): pass


class LockNotAcquired(Exception):
    pass

class RedisLock(object):
    def __init__(self, client, key, timeout=30):
        assert timeout >= 2, 'Timeout must be greater than 2 to guarantee the transaction'
        self.client = client
        self.key = key
        self.timeout = timeout
        self.me = str(uuid.uuid4())

    def __enter__(self):
        trans = self.client.transaction(watch=[self.key])
        v = self.client.get(self.key)
        if v:
            raise LockNotAcquired()
        else:
            try:
                with trans as t:
                    t.setex(self.key, self.timeout, self.me)

                def touch():
                    with RedisClient(self.client.addr, self.client.port) as c:
                        while self.in_block:
                            c.expire(self.key, self.timeout)
                            sleep(self.timeout / 2)
                self.in_block = True
                fork(touch)
            except RedisTransactionError:
                raise LockNotAcquired()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.in_block = False
        val = self.client.get(self.key)
        assert val == self.me, 'Someone else took the lock, panic (val=%s, expected=%s, wha=%s)' % (val, self.me, self.client.get(self.key))
        self.client.delete(self.key)


#########################################
## Hub, an abstraction of sub behavior, etc
class RedisSubHub(object):
    def __init__(self, host='127.0.0.1', port=REDIS_PORT, password=None):
        self.host = host
        self.port = port
        self.password= password
        self.sub_wake_signal = uuid.uuid4().hex
        self.sub_adds = []
        self.sub_rms = []
        self.subs = {}

    def make_client(self):
        client = RedisClient(self.host, self.port, self.password)
        if self.password != None:
            client.auth()
        return  client

    def __isglob(self, glob):
        return '*' in glob or '?' in glob or ('[' in glob and ']' and glob)

    def __call__(self):
        with self.make_client() as conn:
            subs = self.subs
            for sub in subs:
                if self.__isglob(sub):
                    conn.psubscribe(sub)
                else:
                    conn.subscribe(sub)
            while True:
                new = rm = None
                if self.sub_adds:
                    sa = self.sub_adds[:]
                    self.sub_adds = []
                    new_subs, new_glob_subs = set(), set()
                    for k, q in sa:
                        new = new_glob_subs if self.__isglob(k) else new_subs

                        if k not in subs:
                            new.add(k)
                            subs[k] = set([q])
                        else:
                            subs[k].add(q)

                    if new_subs:
                        conn.subscribe(*new_subs)
                    if new_glob_subs:
                        conn.psubscribe(*new_glob_subs)

                if self.sub_rms:
                    sr = self.sub_rms[:]
                    self.sub_rms = []
                    rm_subs, rm_glob_subs = set(), set()
                    for k, q in sr:
                        rm = rm_glob_subs if self.__isglob(k) else rm_subs

                        subs[k].remove(q)
                        if not subs[k]:
                            del subs[k]
                            rm.add(k)

                    if rm_subs:
                        conn.unsubscribe(*rm_subs)
                    if rm_glob_subs:
                        conn.punsubscribe(*rm_glob_subs)

                if not self.sub_rms and not self.sub_adds:
                    r = conn.get_from_subscriptions(self.sub_wake_signal)
                    if r:
                        cls, key, msg = r
                        if cls in subs:
                            for q in subs[cls]:
                                q.put((key, msg))

    @contextmanager
    def subq(self, classes):
        if type(classes) not in (set, list, tuple):
            classes = [classes]

        q = Queue()

        for cls in classes:
            self.sub_adds.append((cls, q))

        fire(self.sub_wake_signal)

        try:
            yield q
        finally:
            for cls in classes:
                self.sub_rms.append((cls, q))


    @contextmanager
    def sub(self, classes):
        if type(classes) not in (set, list, tuple):
            classes = [classes]

        hb = self
        q = Queue()
        class Poller(object):
            def __init__(self):
                for cls in classes:
                    hb.sub_adds.append((cls, q))

                fire(hb.sub_wake_signal)

            def fetch(self, timeout=None):
                try:
                    qn, msg = q.get(timeout=timeout)
                except QueueTimeout:
                    return (None, None)
                else:
                    return (qn, msg)

            def close(self):
                for cls in classes:
                    hb.sub_rms.append((cls, q))

        pl = Poller()
        try:
            yield pl
        finally:
            pl.close()

########NEW FILE########
__FILENAME__ = riak
"""Riak protocol buffers client.

Provides a couple interfaces to working with a Riak database.

The first is a lower-level Client object. It has methods for interacting with
the server, buckets, keys and values. The methods are more verbose and return
dense dictionaries of data.

The other interface is via Buckets. These use a Client to allow you to work
with keys and values in the context of a Riak bucket. They offer a simpler API
and hooks for conflict resolution and custom loading/dumping of values.

"""
import struct

import diesel
from diesel.util.queue import Queue, QueueEmpty
from diesel.util.event import Event

try:
    import riak_palm
    from palm import palm
except ImportError:
    import sys
    sys.stderr.write("Warning: must use the palm (https://github.com/bumptech/palm/)\nprotocol buffers library to generate riak_palm.py\n")
    raise SystemExit(1)

from contextlib import contextmanager

# The commented-out message codes and types below are for requests and/or
# responses that don't have a body.

MESSAGE_CODES = [
(0, riak_palm.RpbErrorResp),
#(1, riak_palm.RpbPingReq),
#(2, riak_palm.RpbPingResp),
#(3, riak_palm.RpbGetClientIdReq),
(4, riak_palm.RpbGetClientIdResp),
(5, riak_palm.RpbSetClientIdReq),
#(6, riak_palm.RpbSetClientIdResp),
#(7, riak_palm.RpbGetServerInfoReq),
(8, riak_palm.RpbGetServerInfoResp),
(9, riak_palm.RpbGetReq ),
(10, riak_palm.RpbGetResp),
(11, riak_palm.RpbPutReq ),
(12, riak_palm.RpbPutResp),
(13, riak_palm.RpbDelReq ),
#(14, riak_palm.RpbDelResp),
#(15, riak_palm.RpbListBucketsReq),
(16, riak_palm.RpbListBucketsResp),
(17, riak_palm.RpbListKeysReq),
(18, riak_palm.RpbListKeysResp),
(19, riak_palm.RpbGetBucketReq),
(20, riak_palm.RpbGetBucketResp),
(21, riak_palm.RpbSetBucketReq),
#(22, riak_palm.RpbSetBucketResp),
(23, riak_palm.RpbMapRedReq),
(24, riak_palm.RpbMapRedResp),
(25, riak_palm.RpbIndexReq),
(26, riak_palm.RpbIndexResp),
]

resolutions_in_progress = {}

class ResolvedLookup(Event):
    def __init__(self, resolver):
        Event.__init__(self)
        self.error = None
        self.value = None
        self.resolver = resolver

@contextmanager
def in_resolution(bucket, key, entity):
    e = ResolvedLookup(entity)
    resolutions_in_progress[(bucket, key)] = e
    try:
        yield e
    except:
        a = resolutions_in_progress.pop((bucket, key))
        a.error = True
        a.set()
        raise
    else:
        del resolutions_in_progress[(bucket, key)]

PB_TO_MESSAGE_CODE = dict((cls, code) for code, cls in MESSAGE_CODES)
MESSAGE_CODE_TO_PB = dict(MESSAGE_CODES)

class BucketSubrequestException(Exception):
    def __init__(self, s, sub_exceptions):
        Exception.__init__(s)
        self.sub_exceptions = sub_exceptions

class Bucket(object):
    """A Bucket of keys/values in a Riak database.

    Buckets are intended to be cheap, non-shared objects for easily performing
    common key/value operations with Riak.

    Buckets should not be shared amongst concurrent consumers. Each consumer
    should have its own Bucket instance. This is due to the way vector clocks
    are tracked on the Bucket instances.

    """
    def __init__(self, name, client=None, make_client_context=None, resolver=None):
        """Return a new Bucket for the named bucket, using the given client.

        If your bucket allows sibling content (conflicts) you should supply a
        conflict resolver function or subclass and override ``resolve``. It
        should take four arguments and return a resolved value. Here is an
        example::

            def resolve_random(timestamp_1, value_1, timestamp_2, value_2):
                '''The worlds worst resolver function!'''
                return random.choice([value_1, value_2])

        """
        assert client is not None or make_client_context is not None,\
        "Must specify either client or make_client_context"
        assert not (client is not None and make_client_context is not None),\
        "Cannot specify both client and make_client_context"
        self.name = name
        if make_client_context:
            self.make_client_context = make_client_context
            self.used_client_context = True
        else:
            @contextmanager
            def noop_cm():
                yield client
            self.make_client_context = noop_cm
            self.used_client_context = False
        self._vclocks = {}
        if resolver:
            self.resolve = resolver
        self.client_id = None

    def for_client(self, client_id):
        self.client_id = client_id
        return self

    def get(self, key):
        """Get the value for key from the bucket.

        Records the vector clock for the value for future modification
        using ``put`` with this same Bucket instance.

        """
        with self.make_client_context() as client:
            if self.client_id:
                client.set_client_id(self.client_id)
            response = client.get(self.name, key)
        if response:
            return self._handle_response(key, response, resave=False)

    def _subrequest(self, inq, outq):
        while True:
            try:
                key = inq.get(waiting=False)
            except QueueEmpty:
                break
            else:
                try:
                    res = self.get(key)
                except Exception, e:
                    outq.put((key, False, e))
                else:
                    outq.put((key, True, res))

    def get_many(self, keys, concurrency_limit=100, no_failures=False):
        assert self.used_client_context,\
        "Cannot fetch in parallel without a pooled make_client_context!"
        inq = Queue()
        outq = Queue()
        for k in keys:
            inq.put(k)

        for x in xrange(min(len(keys), concurrency_limit)):
            diesel.fork(self._subrequest, inq, outq)

        failure = False
        okay, err = [], []
        for k in keys:
            (key, success, val) = outq.get()
            if success:
                okay.append((key, val))
            else:
                err.append((key, val))

        if no_failures:
            raise BucketSubrequestException(
            "Error in parallel subrequests", err)
        return okay, err

    def put(self, key, value, safe=True, **params):
        """Puts the given key/value into the bucket.

        If safe==True the response will be read back and conflict resolution
        might take place as well if the put triggers multiple sibling values
        for the key.

        Extra params are passed to the ``Client.put`` method.
        """
        if safe:
            params['return_body'] = True
            if 'vclock' not in params and key in self._vclocks:
                params['vclock'] = self._vclocks.pop(key)
        with self.make_client_context() as client:
            if self.client_id:
                client.set_client_id(self.client_id)
            response = client.put(self.name, key, self.dumps(value), **params)
        if response:
            return self._handle_response(key, response)

    def delete(self, key, vclock=None):
        """Deletes all values for the given key from the bucket."""
        with self.make_client_context() as client:
            if self.client_id:
                client.set_client_id(self.client_id)
            client.delete(self.name, key, vclock)

    def keys(self):
        """Get all the keys for a given bucket, is an iterator."""
        with self.make_client_context() as client:
            if self.client_id:
                client.set_client_id(self.client_id)
            return client.keys(self.name)

    def _handle_response(self, key, response, resave=True):
        # Returns responses for non-conflicting content. Resolves conflicts
        # if there are multiple values for a key.
        resave = resave and self.track_siblings(key, len(response['content']))
        if len(response['content']) == 1:
            self._vclocks[key] = response['vclock']
            return self.loads(response['content'][0]['value'])
        else:
            res = (self.name, key)
            if res in resolutions_in_progress:
                ev = resolutions_in_progress[res]
                if ev.resolver == self:
                    # recursing on put() with > 1 response
                    return self._resolve(key, response, resave=resave)
                ev.wait()
                if not ev.error:
                    return ev.value
                else:
                    return self._handle_response(key, response, resave=resave)
            with in_resolution(*(res + (self,))) as ev:
                result = self._resolve(key, response, resave=resave)
                ev.value = result
                ev.set()
            return result

    def _resolve(self, key, response, resave=True):
        # Performs conflict resolution for the given key and response. If all
        # goes well a new harmonized value for the key will be put up to the
        # bucket. If things go wrong, expect ... exceptions. :-|
        res = response['content'].pop(0)
        while response['content']:
            other = response['content'].pop(0)
            other['value'] = self.dumps(
                self.resolve(
                    res['last_mod'],
                    self.loads(res['value']),
                    other['last_mod'],
                    self.loads(other['value']),
                )
            )
            res = other
        resolved_value = self.loads(res['value'])
        params = dict(vclock=response['vclock'], return_body=True)
        if resave:
            return self.put(key, resolved_value, **params)
        else:
            return resolved_value

    def resolve(self, timestamp1, value1, timestamp2, value2):
        """Subclass to support custom conflict resolution."""
        msg = "Pass in a resolver or override this method."
        raise NotImplementedError(msg)

    def loads(self, raw_value):
        """Subclass to support loading rich values."""
        return raw_value

    def dumps(self, rich_value):
        """Subclass to support dumping rich values."""
        return rich_value

    def track_siblings(self, key, siblings):
        return True


class RiakErrorResp(Exception):
    def __init__(self, error_resp):
        Exception.__init__(self, error_resp.errmsg, error_resp.errcode)
        self.errmsg = error_resp.errmsg
        self.errcode = error_resp.errcode

    def __repr__(self):
        return "RiakErrorResp: %s" % (self.errmsg)

class RiakClient(diesel.Client):
    """A client for the Riak distributed key/value database.

    Instances can be used stand-alone or passed to a Bucket constructor
    (which has a simpler API).

    """
    def __init__(self, host='127.0.0.1', port=8087, **kw):
        """Creates a new Riak Client connection object."""
        diesel.Client.__init__(self, host, port, **kw)

    @diesel.call
    def get(self, bucket, key):
        """Get the value of key from named bucket.

        Returns a dictionary with a list of the content for the key
        and the vector clock (vclock) for the key.

        """
        request = riak_palm.RpbGetReq(bucket=bucket, key=key)
        self._send(request)
        response = self._receive()
        if response:
            return _to_dict(response)

    @diesel.call
    def put(self, bucket, key, value, indexes=None, **params):
        """Puts the value to the key in the named bucket.

        If an ``extra_content`` dictionary parameter is present, its content
        is merged into the RpbContent object.

        All other parameters are merged into the RpbPutReq object.

        """
        dict_content={'value':value}

        index_pairs = []
        if isinstance(indexes,list):
            for k,v in indexes:
                if not (k.endswith('_int') or k.endswith('_bin')):
                    msg = "Key must ends with _int or _bin"
                    raise NotImplementedError(msg)
                pair = riak_palm.RpbPair()
                pair.key = k
                pair.value = str(v)
                index_pairs.append(pair)

        if 'extra_content' in params:
            dict_content.update(params.pop('extra_content'))
        content = riak_palm.RpbContent(**dict_content)
        content.indexes.set(index_pairs)

        request = riak_palm.RpbPutReq(
            bucket=bucket,
            key=key,
            content=content,
        )
        for name, value in params.iteritems():
            setattr(request, name, value)
        self._send(request)
        response = self._receive()
        if response:
            return _to_dict(response)

    @diesel.call
    def index(self, bucket, idx, key, end=None):
        request = riak_palm.RpbIndexReq(
            bucket=bucket,
            index=idx,)

        if end:
            """range query"""
            request.qtype = 1
            request.range_min = key
            request.range_max = end
        else:
            """equal query"""
            request.qtype = 0
            request.key = key

        self._send(request)
        response = self._receive()
        if response:
            result = _to_dict(response)
            if result.has_key('keys'):
                return result['keys']
        return None

    @diesel.call
    def delete(self, bucket, key, vclock=None):
        """Deletes the given key from the named bucket, including all values."""
        request = riak_palm.RpbDelReq(bucket=bucket, key=key)
        self._send(request)
        return self._receive()

    @diesel.call
    def keys(self, bucket):
        """Gets the keys for the given bucket, is an iterator"""
        request = riak_palm.RpbListKeysReq(bucket=bucket)
        self._send(request)

        response = riak_palm.RpbListKeysResp(done=False) #Do/while?
        while not (response.done__exists and response.done):
            response = self._receive()
            for key in response.keys:
                yield key

    @diesel.call
    def info(self):
        # No protocol buffer object to build or send.
        message_code = 7
        total_size = 1
        fmt = "!iB"
        diesel.send(struct.pack(fmt, total_size, message_code))
        return self._receive()

    @diesel.call
    def set_bucket_props(self, bucket, props):
        """Sets some properties on the named bucket.

        ``props`` should be a dictionary of properties supported by the
        RpbBucketProps protocol buffer.

        """
        request = riak_palm.RpbSetBucketReq(bucket=bucket)
        bucket_props = riak_palm.RpbBucketProps()
        for name, value in props.iteritems():
            setattr(bucket_props, name, value)
        request.props = bucket_props
        self._send(request)
        return self._receive()

    @diesel.call
    def set_client_id(self, client_id):
        """Sets the remote client id for this connection.

        This is crazy-important to do if your bucket allows sibling documents
        and you are reusing connections. In general, client ids should map to
        actors within your system.

        """
        request = riak_palm.RpbSetClientIdReq(client_id=client_id)
        self._send(request)
        return self._receive()

    @diesel.call
    def _send(self, pb):
        # Send a protocol buffer on the wire as a request.
        message_code = PB_TO_MESSAGE_CODE[pb.__class__]
        message = pb.dumps()
        message_size = len(message)
        total_size = message_size + 1 # plus 1 mc byte
        fmt = "!iB%ds" % message_size
        diesel.send(struct.pack(fmt, total_size, message_code, message))

    @diesel.call
    def _receive(self):
        # Receive a protocol buffer from the wire as a response.
        response_size, = struct.unpack('!i', diesel.receive(4))
        raw_response = diesel.receive(response_size)
        message_code, = struct.unpack('B',raw_response[0])
        response = raw_response[1:]
        if response:
            pb_cls = MESSAGE_CODE_TO_PB[message_code]
            pb = pb_cls(response)
            if message_code == 0:
                # RpbErrorResp - raise an exception
                raise RiakErrorResp(pb)
            return pb

def _to_dict(pb):
    # Takes a protocol buffer (pb) and transforms it into a dict of more
    # common Python types.
    out = {}
    for name in pb.fields():
        if name not in pb:
            continue
        value = getattr(pb, name)
        def maybe_recurse(v):
            if isinstance(v, palm.ProtoBase):
                return _to_dict(v)
            return v
        if isinstance(value, palm.RepeatedSequence):
            value = [maybe_recurse(v) for v in iter(value)]
        else:
            value = maybe_recurse(value)
        out[name] = value
    return out


# Testing Code Below
# ==================
# XXX hack - can't define it in __main__ below
class Point(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

if __name__ == '__main__':
    import cPickle

    def test_client():
        c = RiakClient()
        c.set_client_id('testing-client')

        # Do some cleanup from a previous run.
        c.delete('testing', 'bar')
        c.delete('testing', 'foo')
        c.delete('testing', 'lala')
        c.delete('testing', 'baz')
        c.delete('testing', 'diff')
        c.delete('testing.pickles', 'here')
        c.delete('testing.pickles', 'there')
        diesel.sleep(3) # race condition for deleting PickleBucket keys?

        assert not c.get('testing', 'foo')
        assert c.put('testing', 'foo', '1', return_body=True)
        assert c.get('testing', 'foo')

        # Create a conflict for the 'bar' key in 'testing'.
        assert not c.set_bucket_props('testing', {'allow_mult':True})
        b1 = c.put('testing', 'bar', 'hi', return_body=True)
        b2 = c.put('testing', 'bar', 'bye', return_body=True)
        assert len(c.get('testing', 'bar')['content']) > 1

        def resolve_longest(t1, v1, t2, v2):
            if len(v1) > len(v2):
                return v1
            return v2

        # Test that the conflict is resolved, this time using the Bucket
        # interface.
        b = Bucket('testing', c, resolver=resolve_longest)
        resolved = b.get('bar')
        assert resolved == 'bye', resolved
        b.put('bar', resolved)
        assert len(c.get('testing', 'bar')['content']) == 1

        # put/get/delete with a Bucket
        assert b.put('lala', 'g'*1024)
        assert b.get('lala') == 'g'*1024
        b.delete('lala')
        assert not b.get('lala')

        # Multiple changes to a key using a Bucket should be a-ok.
        assert b.put('baz', 'zzzz')
        assert b.put('baz', 'ffff')
        assert b.put('baz', 'tttt')
        assert len(c.get('testing', 'baz')['content']) == 1
        assert b.get('baz') == 'tttt'

        # Custom Bucket.
        class PickleBucket(Bucket): # lol
            def loads(self, raw_value):
                return cPickle.loads(raw_value)

            def dumps(self, rich_value):
                return cPickle.dumps(rich_value)

            def resolve(self, t1, v1, t2, v2):
                # Returns the value with the smallest different between points.
                d1 = abs(v1.x - v1.y)
                d2 = abs(v2.x - v2.y)
                if d1 < d2:
                    return v1
                return v2

        assert not c.set_bucket_props('testing.pickles', {'allow_mult':True})
        p = PickleBucket('testing.pickles', c)
        assert p.put('here', Point(4,2))
        out = p.get('here')
        assert (4,2) == (out.x, out.y)
        assert isinstance(out, Point)

        # Resolve Point conflicts.
        p1 = PickleBucket('testing.pickles', c).for_client('c 1')
        p1.put('there', Point(4,12), safe=False)
        p2 = PickleBucket('testing.pickles', c).for_client('c 2')
        p2.put('there', Point(3,7), safe=False)
        p3 = PickleBucket('testing.pickles', c).for_client('c 3')
        p3.put('there', Point(90,99), safe=False)
        p4 = PickleBucket('testing.pickles', c).for_client('c 4')
        p4.put('there', Point(4,10), safe=False)
        p5 = PickleBucket('testing.pickles', c).for_client('c 5')
        p5.put('there', Point(1,9), safe=False)
        assert len(c.get('testing.pickles', 'there')['content']) == 5
        there = p5.get('there')
        assert (3,7) == (there.x, there.y), (there.x, there.y)
        assert isinstance(there, Point)

        # resolve on put
        p5.put('there', Point(1,9)) # should resolve b/c safe=True
        assert len(c.get('testing.pickles', 'there')['content']) == 1

        # Doing stuff with different client ids but the same vector clock.
        c.set_client_id('diff 1')
        assert b.put('diff', '---')
        c.set_client_id('diff 2')
        assert b.put('diff', '+++')
        assert b.get('diff') == '+++'

        # Provoking an error
        try:
            # Tell Riak to require 10000 nodes to write this before success.
            c.put('testing', 'error!', 'oh noes!', w=10000)
        except RiakErrorResp, e:
            assert e.errcode == 1, e.errcode
            assert e.errmsg == '{n_val_violation,3}', e.errmsg
            assert repr(e) == "RiakErrorResp: {n_val_violation,3}", repr(e)
        except Exception, e:
            assert 0, "UNEXPECTED EXCEPTION: %r" % e
        else:
            assert 0, "DID NOT RAISE"
        diesel.quickstop()
    diesel.quickstart(test_client)

del Point

########NEW FILE########
__FILENAME__ = websockets
"""A WebSocket protocol implementation for diesel.

Implements much of RFC 6455 (http://tools.ietf.org/html/rfc6455) and enough
of hybi-00 to support Safari 5.0.1+.

Not implemented:
    * PING/PONG.
    * Extension support.

"""
from .http import HttpServer, Response
from diesel.util.queue import Queue
from diesel import fork, until, receive, first, ConnectionClosed, send
from simplejson import dumps, loads, JSONDecodeError
import hashlib
from struct import pack, unpack
from base64 import b64encode
from array import array

class WebSocketDisconnect(object): pass
class WebSocketData(dict): pass

class WebSocketServer(HttpServer):
    '''Very simple Web Socket server.
    '''

    GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self, web_handler, web_socket_handler):
        """Creates a WebSocket server.

        The `web_handler` is used for non-WebSocket HTTP requests. It should
        be a callable that accepts a `Request` and returns a `Response`.

        The `web_socket_handler` will be called with three arguments: a
        `Request` instance, an input `Queue` and an output `Queue`. The input
        queue is where messages from the client will be received. Anything
        put in the output queue will be sent on to the client.

        All values passed to and from the queues MUST be dictionaries, or
        something that is JSON serializable. The one special case is the
        WebSocketDisconnect object that can arrive on the input queue if
        the client is closing the connection.

        """
        self.web_handler = web_handler
        self.web_socket_handler = web_socket_handler
        HttpServer.__init__(self, self.do_upgrade)

    def do_upgrade(self, req):
        """Handles the WebSocket handshake.

        Processes the `Request` instance `req` and returns a `Response`.

        Adds the WebSocket messaging protocol handler
        (`WebSocketServer.websocket_protocol`) to the `Response` object as
        `new_protocol`. That gets called by the underlying HttpServer when it
        sees a 101 Switching Protocols response.

        """
        if req.headers.get('Upgrade', '').lower() != 'websocket':
            return self.web_handler(req)

        headers = {}

        # do upgrade response
        org = req.headers.get('Origin')
        if 'Sec-WebSocket-Key' in req.headers:
            req.rfc_handshake = True
            assert req.headers.get('Sec-WebSocket-Version') in ['8', '13'], \
                   "We currently only support Websockets version 8 and 13 (ver=%s)" % \
                   req.headers.get('Sec-WebSocket-Version')

            protocol = req.headers.get('Sec-WebSocket-Protocol', None)
            key = req.headers.get('Sec-WebSocket-Key')
            accept = b64encode(hashlib.sha1(key + self.GUID).digest())
            headers = {
                'Upgrade' : 'websocket',
                'Connection' : 'Upgrade',
                'Sec-WebSocket-Accept' : accept,
                }
        elif 'Sec-WebSocket-Key1' in req.headers:
            req.rfc_handshake = False
            protocol = req.headers.get('Sec-WebSocket-Protocol', None)
            headers = {
                'Upgrade': 'WebSocket',
                'Connection': 'Upgrade',
                'Sec-WebSocket-Origin': org,
                'Sec-WebSocket-Location': req.url.replace('http', 'ws', 1),
            }
        else:
            assert 0, "Unsupported WebSocket handshake."

        if protocol:
            headers['Sec-WebSocket-Protocol'] = protocol

        resp = Response(
                response='',
                status=101,
                headers=headers,
                )
        resp.new_protocol = self.websocket_protocol

        return resp

    def websocket_protocol(self, req):
        """Runs the WebSocket protocol after the handshake is complete.

        Creates two `Queue` instances for incoming and outgoing messages and
        passes them to the `web_socket_handler` that was supplied to the
        `WebSocketServer` constructor.

        """
        inq = Queue()
        outq = Queue()

        if req.rfc_handshake:
            handle_frames = self.handle_rfc_6455_frames
        else:
            # Finish the non-RFC handshake
            key1 = req.headers.get('Sec-WebSocket-Key1')
            key2 = req.headers.get('Sec-WebSocket-Key2')

            # The final key can be in two places. The first is in the
            # `Request.data` attribute if diesel is *not* being proxied
            # to by a smart proxy that parsed HTTP requests. If it is being
            # proxied to, that data will not have been sent until after our
            # initial 101 Switching Protocols response, so we will need to
            # receive it here.

            if req.data:
                key3 = req.data
            else:
                evt, key3 = first(receive=8, sleep=5)
                assert evt == "receive", "timed out while finishing handshake"

            num1 = int(''.join(c for c in key1 if c in '0123456789'))
            num2 = int(''.join(c for c in key2 if c in '0123456789'))
            assert num1 % key1.count(' ') == 0
            assert num2 % key2.count(' ') == 0
            final = pack('!II8s', num1 / key1.count(' '), num2 / key2.count(' '), key3)
            handshake_finish = hashlib.md5(final).digest()
            send(handshake_finish)

            handle_frames = self.handle_non_rfc_frames

        def wrap(req, inq, outq):
            self.web_socket_handler(req, inq, outq)
            outq.put(WebSocketDisconnect())

        handler_loop = fork(wrap, req, inq, outq)

        try:
            handle_frames(inq, outq)
        except ConnectionClosed:
            if handler_loop.running:
                inq.put(WebSocketDisconnect())
            raise

    def handle_rfc_6455_frames(self, inq, outq):
        disconnecting = False
        while True:
            typ, val = first(receive=2, waits=[outq])
            if typ == 'receive':
                b1, b2 = unpack(">BB", val)

                opcode = b1 & 0x0f
                fin = (b1 & 0x80) >> 7
                has_mask = (b2 & 0x80) >> 7

                assert has_mask == 1, "Frames must be masked"

                if opcode == 8:
                    inq.put(WebSocketDisconnect())
                    if disconnecting:
                        break
                    disconnecting = True
                assert opcode in [1,8], "Currently only opcodes 1 & 8 are supported (opcode=%s)" % opcode
                length = b2 & 0x7f
                if length == 126:
                    length = unpack('>H', receive(2))[0]
                elif length == 127:
                    length = unpack('>L', receive(8))[0]

                mask = unpack('>BBBB', receive(4))
                if length:
                    payload = array('B', receive(length))
                    if disconnecting:
                        continue
                    for i in xrange(len(payload)):
                        payload[i] ^= mask[i % 4]

                    try:
                        data = loads(payload.tostring())
                        inq.put(data)
                    except JSONDecodeError:
                        pass
            elif typ == outq:
                if type(val) is WebSocketDisconnect:
                    b1 = 0x80 | (8 & 0x0f) # FIN + opcode
                    send(pack('>BB', b1, 0))
                    if disconnecting:
                        break
                    disconnecting = True
                else:
                    payload = dumps(val)

                    b1 = 0x80 | (1 & 0x0f) # FIN + opcode

                    payload_len = len(payload)
                    if payload_len <= 125:
                        header = pack('>BB', b1, payload_len)
                    elif payload_len > 125 and payload_len < 65536:
                        header = pack('>BBH', b1, 126, payload_len)
                    elif payload_len >= 65536:
                        header = pack('>BBQ', b1, 127, payload_len)

                    send(header + payload)

    def handle_non_rfc_frames(self, inq, outq):
        while True:
            typ, val = first(receive=1, waits=[outq])
            if typ == 'receive':
                assert val == '\x00'
                val = until('\xff')[:-1]
                if val == '':
                    inq.put(WebSocketDisconnect())
                    break
                else:
                    try:
                        data = loads(val)
                        inq.put(data)
                    except JSONDecodeError:
                        pass
            elif typ == outq:
                if type(val) is WebSocketDisconnect:
                    send('\x00\xff')
                    break
                else:
                    data = dumps(dict(val))
                    send('\x00%s\xff' % data)

########NEW FILE########
__FILENAME__ = wsgi
# vim:ts=4:sw=4:expandtab
"""A minimal WSGI implementation to hook into
diesel's HTTP module.

Note: not well-tested.  Contributions welcome.
"""
from diesel import Application, Service
from diesel.protocols.http import HttpServer, Response

import functools

class WSGIRequestHandler(object):
    '''The request_handler for the HttpServer that
    bootsraps the WSGI environment and hands it off to the
    WSGI callable.  This is the key coupling.
    '''
    def __init__(self, wsgi_callable, port=80):
        self.port = port
        self.wsgi_callable = wsgi_callable

    def _start_response(self, env, status, response_headers, exc_info=None):
        if exc_info:
            raise exc_info[0], exc_info[1], exc_info[2]
        else:
            r = env['diesel.response']
            r.status = status
            for k, v in response_headers:
                r.headers.add(k, v)
        return r.response.append

    def __call__(self, req):
        env = req.environ
        buf = []
        r = Response()
        env['diesel.response'] = r
        for output in self.wsgi_callable(env,
                functools.partial(self._start_response, env)):
            r.response.append(output)
        del env['diesel.response']
        return r

class WSGIApplication(Application):
    '''A WSGI application that takes over both `Service`
    setup, `request_handler` spec for the HTTPServer,
    and the app startup itself.


    Just pass it a wsgi_callable and port information, and
    it should do the rest.
    '''
    def __init__(self, wsgi_callable, port=80, iface=''):
        Application.__init__(self)
        self.port = port
        self.wsgi_callable = wsgi_callable
        http_service = Service(HttpServer(WSGIRequestHandler(wsgi_callable, port)), port, iface)
        self.add_service(http_service)

if __name__ == '__main__':
    def simple_app(environ, start_response):
        """Simplest possible application object"""
        status = '200 OK'
        response_headers = [('Content-type','text/plain')]
        start_response(status, response_headers)
        return ["Hello World!"]
    app = WSGIApplication(simple_app, port=7080)
    app.run()

########NEW FILE########
__FILENAME__ = zeromq
import warnings

from errno import EAGAIN

import zmq

import diesel
from diesel import log, loglevels
from diesel.events import Waiter, StopWaitDispatch
from diesel.util.queue import Queue
from diesel.util.event import Event


zctx = zmq.Context.instance()

class DieselZMQSocket(Waiter):
    '''Integrate zmq's super fast event loop with ours.
    '''
    def __init__(self, socket, bind=None, connect=None, context=None, linger_time=1000):
        self.zctx = context or zctx
        self.socket = socket
        self._early_value = None
        from diesel.runtime import current_app
        from diesel.hub import IntWrap

        if bind:
            assert not connect
            self.socket.bind(bind)
        elif connect:
            assert not bind
            self.socket.connect(connect)

        self.hub = current_app.hub
        self.fd = IntWrap(self.socket.getsockopt(zmq.FD))

        self.write_gate = Event()
        self.read_gate = Event()
        self.linger_time = linger_time
        self.hub.register(self.fd, self.handle_transition, self.error, self.error)
        self.handle_transition()
        self.destroyed = False
        self.sent = 0
        self.received = 0

    def send(self, message, flags=0):
        while True:
            try:
                self.socket.send(message, zmq.NOBLOCK | flags)
            except zmq.ZMQError, e:
                if e.errno == EAGAIN:
                    self.handle_transition(True) # force re-evaluation of EVENTS
                    self.write_gate.wait()
                else:
                    raise
            else:
                self.handle_transition(True)
                self.sent += 1
                break

    def recv(self, copy=True):
        while True:
            self.read_gate.wait()
            try:
                m = self.socket.recv(zmq.NOBLOCK, copy=copy)
            except zmq.ZMQError, e:
                if e.errno == EAGAIN:
                    self.handle_transition(True) # force re-evaluation of EVENTS
                    self.read_gate.wait()
                else:
                    raise
            else:
                self.handle_transition(True)
                self.received += 1
                return m

    def process_fire(self, dc):
        if not self._early_value:
            got = self.ready_early()
            if not got:
                raise StopWaitDispatch()

        assert self._early_value
        v = self._early_value
        self._early_value = None
        return v


    def ready_early(self):
        try:
            m = self.socket.recv(zmq.NOBLOCK, copy=False)
        except zmq.ZMQError, e:
            if e.errno == EAGAIN:
                return False
            else:
                raise
        else:
            self.handle_transition(True)
            self.received += 1
            self._early_value = m
            return True

    def handle_transition(self, manual=False):
        '''Handle state change.
        '''
        if not manual:
            diesel.fire(self)
        events = self.socket.getsockopt(zmq.EVENTS)
        if events & zmq.POLLIN:
            self.read_gate.set()
        else:
            self.read_gate.clear()

        if events & zmq.POLLOUT:
            self.write_gate.set()
        else:
            self.write_gate.clear()

    def error(self):
        raise RuntimeError("OH NOES, some weird zeromq FD error callback")

    def __del__(self):
        if not self.destroyed:
            self.hub.unregister(self.fd)
            self.socket.close(self.linger_time)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if not self.destroyed:
            self.hub.unregister(self.fd)
            self.socket.close(self.linger_time)

class DieselZMQService(object):
    """A ZeroMQ service that can handle multiple clients.

    Clients must maintain a steady flow of messages in order to maintain
    state in the service. A heartbeat of some sort. Or the timeout can be
    set to a sufficiently large value understanding that it will cause more
    resource consumption.

    """
    name = ''
    default_log_level = loglevels.DEBUG
    timeout = 10

    def __init__(self, uri, logger=None, log_level=None):
        self.uri = uri
        self.zmq_socket = None
        self.log = logger or None
        self.selected_log_level = log_level
        self.clients = {}
        self.outgoing = Queue()
        self.incoming = Queue()
        self.name = self.name or self.__class__.__name__
        self._incoming_loop = None

        # Allow for custom `should_run` properties in subclasses.
        try:
            self.should_run = True
        except AttributeError:
            # A custom `should_run` property exists.
            pass

        if self.log and self.selected_log_level is not None:
            self.selected_log_level = None
            warnings.warn(
                "ignored `log_level` argument since `logger` was provided.",
                RuntimeWarning,
                stacklevel=2,
            )

    def _create_zeromq_server_socket(self):
        # TODO support other ZeroMQ socket types
        low_level_sock = zctx.socket(zmq.ROUTER)
        self.zmq_socket = DieselZMQSocket(low_level_sock, bind=self.uri)

    def _setup_the_logging_system(self):
        if not self.log:
            if self.selected_log_level is not None:
                log_level = self.selected_log_level
            else:
                log_level = self.default_log_level
            log_name = self.name or self.__class__.__name__
            self.log = log.name(log_name)
            self.log.min_level = log_level

    def _handle_client_requests_and_responses(self, remote_client):
        assert self.zmq_socket
        queues = [remote_client.incoming, remote_client.outgoing]
        try:
            while True:
                (evt, value) = diesel.first(waits=queues, sleep=self.timeout)
                if evt is remote_client.incoming:
                    assert isinstance(value, Message)
                    # Update return path with latest (in case of reconnect)
                    remote_client.zmq_return = value.zmq_return
                    resp = self.handle_client_packet(value.data, remote_client.context)
                elif evt is remote_client.outgoing:
                    resp = value
                elif evt == 'sleep':
                    break
                if resp:
                    if isinstance(resp, basestring):
                        output = [resp]
                    else:
                        output = iter(resp)
                    for part in output:
                        msg = Message(
                            remote_client.identity,
                            part,
                        )
                        msg.zmq_return = remote_client.zmq_return
                        self.outgoing.put(msg)
        finally:
            self._cleanup_client(remote_client)

    def _cleanup_client(self, remote_client):
        del self.clients[remote_client.identity]
        self.cleanup_client(remote_client)
        self.log.debug("cleaned up client %r" % remote_client.identity)

    def _receive_incoming_messages(self):
        assert self.zmq_socket
        socket = self.zmq_socket
        while True:
            # TODO support receiving data from other socket types
            zmq_return_routing_data = socket.recv(copy=False)
            assert zmq_return_routing_data.more
            zmq_return_routing = zmq_return_routing_data.bytes
            packet_raw = socket.recv()
            msg = self.convert_raw_data_to_message(zmq_return_routing, packet_raw)
            msg.zmq_return = zmq_return_routing
            self.incoming.put(msg)

    def _handle_all_inbound_and_outbound_traffic(self):
        assert self.zmq_socket
        self._incoming_loop = diesel.fork_child(self._receive_incoming_messages)
        self._incoming_loop.keep_alive = True
        queues = [self.incoming, self.outgoing]
        while self.should_run:
            (queue, msg) = diesel.first(waits=queues)

            if queue is self.incoming:
                if msg.remote_identity not in self.clients:
                    self._register_client(msg)
                self.clients[msg.remote_identity].incoming.put(msg)

            elif queue is self.outgoing:
                self.zmq_socket.send(msg.zmq_return, zmq.SNDMORE)
                self.zmq_socket.send(msg.data)

    def _register_client(self, msg):
        remote = RemoteClient.from_message(msg)
        self.clients[msg.remote_identity] = remote
        self.register_client(remote, msg)
        diesel.fork_child(self._handle_client_requests_and_responses, remote)

    # Public API
    # ==========

    def __call__(self):
        return self.run()

    def run(self):
        self._create_zeromq_server_socket()
        self._setup_the_logging_system()
        self._handle_all_inbound_and_outbound_traffic()

    def handle_client_packet(self, packet, context):
        """Called with a bytestring packet and dictionary context.

        Return an iterable of bytestrings.

        """
        raise NotImplementedError()

    def cleanup_client(self, remote_client):
        """Called with a RemoteClient instance. Do any cleanup you need to."""
        pass

    def register_client(self, remote_client, msg):
        """Called with a RemoteClient instance. Do any registration here."""
        pass

    def convert_raw_data_to_message(self, zmq_return, raw_data):
        """Subclasses can override to alter the handling of inbound data.

        Importantly, they can route the message based on the raw_data and
        even convert the raw_data to something more application specific
        and pass it to the Message constructor.

        This default implementation uses the zmq_return identifier for the
        remote socket as the identifier and passes the raw_data to the
        Message constructor.

        """
        return Message(zmq_return, raw_data)


class RemoteClient(object):
    def __init__(self, identity, zmq_return):

        # The identity is some information sent along with packets from the
        # remote client that uniquely identifies it.

        self.identity = identity

        # The zmq_return is from the envelope and tells the ZeroMQ ROUTER
        # socket where to route outbound packets.

        self.zmq_return = zmq_return

        # The incoming queue is typically populated by the DieselZMQService
        # and represents a queue of messages send from the remote client.

        self.incoming = Queue()

        # The outgoing queue is where return values from the
        # DieselZMQService.handle_client_packet method are placed. Those values
        # are sent on to the remote client.
        #
        # Other diesel threads can stick values directly into outgoing queue
        # and the service will send them on as well. This allows for
        # asynchronous sending of messages to remote clients. That's why it's
        # called 'async' in the context.

        self.outgoing = Queue()

        # The context in general is a place where you can put data that is
        # related specifically to the remote client and it will exist as long
        # the remote client doesn't timeout.

        self.context = {'async':self.outgoing}

    @classmethod
    def from_message(cls, msg):
        return cls(msg.remote_identity, msg.zmq_return)


class Message(object):
    def __init__(self, remote_identity, data):
        self.remote_identity = remote_identity
        self.data = data

        # This is set by the DieselZMQService.
        self.zmq_return = None


########NEW FILE########
__FILENAME__ = resolver
'''Fetches the A record for a given name in a green thread, keeps
a cache.
'''

import os
import random
import time
import socket
from diesel.protocols.DNS import DNSClient, NotFound, Timeout
from diesel.util.pool import ConnectionPool
from diesel.util.lock import synchronized

DNS_CACHE_TIME = 60 * 5 # five minutes

cache = {}

class DNSResolutionError(Exception): pass

_pool = ConnectionPool(lambda: DNSClient(), lambda c: c.close())

hosts = {}

def load_hosts():
    if os.path.isfile("/etc/hosts"):
        for line in open("/etc/hosts"):
            parts = line.split()
            ip = None
            for p in parts:
                if p.startswith("#"):
                    break
                if not ip:
                    if ':' in p:
                        break
                    ip = p
                else:
                    hosts[p] = ip

load_hosts()

def resolve_dns_name(name):
    '''Uses a pool of DNSClients to resolve name to an IP address.

    Keep a cache.
    '''

    # Is name an IP address?
    try:
        socket.inet_pton(socket.AF_INET, name)
        return name
    except socket.error:
        # Not a valid IP address resolve it
        pass

    if name in hosts:
        return hosts[name]

    with synchronized('__diesel__.dns.' + name):
        try:
            ips, tm = cache[name]
            if time.time() - tm > DNS_CACHE_TIME:
                del cache[name]
                cache[name]
        except KeyError:
            try:
                with _pool.connection as conn:
                    ips = conn.resolve(name)
            except (NotFound, Timeout):
                raise DNSResolutionError("could not resolve A record for %s" % name)
            cache[name] = ips, time.time()
    return random.choice(ips)

########NEW FILE########
__FILENAME__ = runtime
current_app = None

def is_running():
    return current_app is not None

########NEW FILE########
__FILENAME__ = security
from OpenSSL import SSL
import traceback
import sys

def ssl_async_handshake(sock, hub, next):
    def shake():
        try:
            sock.do_handshake()
        except SSL.WantReadError:
            hub.disable_write(sock)
        except SSL.WantWriteError:
            hub.enable_write(sock)
        except SSL.WantX509LookupError:
            pass
        except Exception, e:
            hub.unregister(sock)
            next(e)
        else:
            hub.unregister(sock)
            next()
    hub.register(sock, shake, shake, shake)
    shake()

########NEW FILE########
__FILENAME__ = debugtools
import collections
import gc
import re
import traceback

from operator import itemgetter

import diesel


address_stripper = re.compile(r' at 0x[0-9a-f]+')

def print_greenlet_stacks():
    """Prints the stacks of greenlets from running loops.

    The number of greenlets at the same position in the stack is displayed
    on the line before the stack dump along with a simplified label for the
    loop callable.

    """
    stacks = collections.defaultdict(int)
    loops = {}
    for obj in gc.get_objects():
        if not isinstance(obj, diesel.Loop) or not obj.running:
            continue
        if obj.id == diesel.core.current_loop.id:
            continue
        fr = obj.coroutine.gr_frame
        stack = ''.join(traceback.format_stack(fr))
        stacks[stack] += 1
        loops[stack] = obj
    for stack, count in sorted(stacks.iteritems(), key=itemgetter(1)):
        loop = loops[stack]
        loop_id = address_stripper.sub('', str(loop.loop_callable))
        print '[%d] === %s ===' % (count, loop_id)
        print stack

########NEW FILE########
__FILENAME__ = event
from diesel import fire, first, signal
from diesel.events import Waiter, StopWaitDispatch

class EventTimeout(Exception): pass

class Event(Waiter):
    def __init__(self):
        self.is_set = False

    def set(self):
        if not self.is_set:
            self.is_set = True
            fire(self)

    def clear(self):
        self.is_set = False

    def ready_early(self):
        return self.is_set

    def process_fire(self, value):
        if not self.is_set:
            raise StopWaitDispatch()
        return value

    def wait(self, timeout=None):
        kw = dict(waits=[self])
        if timeout:
            kw['sleep'] = timeout
        mark, data = first(**kw)
        if mark != self:
            raise EventTimeout()

class Countdown(Event):
    def __init__(self, count):
        self.remaining = count
        Event.__init__(self)

    def tick(self):
        self.remaining -= 1
        if self.remaining <= 0:
            self.set()

class Signal(Event):
    """Used for waiting on an OS-level signal."""

    def __init__(self, signum):
        """Create a Signal instance waiting on signum.

        It will be triggered whenever the provided signum is sent to the
        process. A Loop can be off doing other tasks when the signal arrives
        and it will still trigger this event (the Loop won't know until the
        next time it waits on this event though).

        After the event has been triggered, it must be rearmed before it can
        be waited on again. Otherwise, like a base Event, it will remain in
        the triggered state and thus waiting on it will immediately return.

        """
        Event.__init__(self)
        self.signum = signum
        self.rearm()

    def rearm(self):
        """Prepares the Signal for use again.

        This must be called before waiting on a Signal again after it has
        been triggered.

        """
        self.clear()
        signal(self.signum, self.set)

########NEW FILE########
__FILENAME__ = lock
from uuid import uuid4
from diesel import wait, fire
from collections import defaultdict
from diesel.events import Waiter, StopWaitDispatch

class Lock(Waiter):
    def __init__(self, count=1):
        self.count = count

    def acquire(self):
        if self.count == 0:
            wait(self)
        else:
            self.count -= 1

    def release(self):
        self.count += 1
        fire(self)

    def __enter__(self):
        self.acquire()

    def __exit__(self, *args, **kw):
        self.release()

    @property
    def is_locked(self):
        return self.count == 0

    def ready_early(self):
        return not self.is_locked

    def process_fire(self, value):
        if self.count == 0:
            raise StopWaitDispatch()

        self.count -= 1
        return value

class SynchronizeDefault(object): pass

_sync_locks = defaultdict(Lock)

def synchronized(key=SynchronizeDefault):
    return _sync_locks[key]

########NEW FILE########
__FILENAME__ = requests_lib
"""Through the magic of monkeypatching, requests works with diesel.

It's a hack.

"""
import httplib

import diesel
from diesel.resolver import DNSResolutionError
from OpenSSL import SSL

try:
    from requests.packages.urllib3 import connectionpool
    import requests
except ImportError:
    connectionpool = None


class SocketLike(diesel.Client):
    """A socket-like diesel Client.

    At least enough to satisfy the requests test suite. Its primary job is
    to return a FileLike instance when `makefile` is called.

    """
    def __init__(self, host, port, **kw):
        super(SocketLike, self).__init__(host, port, **kw)
        self._timeout = None

    def makefile(self, mode, buffering):
        return FileLike(self, mode, buffering, self._timeout)

    def settimeout(self, n):
        self._timeout = n

    @diesel.call
    def sendall(self, data):
        diesel.send(data)

    def fileno(self):
        return id(self)

class FileLike(object):
    """Gives you a file-like interface from a diesel Client."""
    def __init__(self, client, mode, buffering, timeout):
        self._client = client
        self.mode = mode
        self.buffering = buffering
        self._extra = ""
        self._timeout = timeout

    # Properties To Stand In For diesel Client
    # ----------------------------------------

    @property
    def conn(self):
        return self._client.conn

    @property
    def connected(self):
        return self._client.connected

    @property
    def is_closed(self):
        return self._client.is_closed

    # File-Like API
    # -------------

    @diesel.call
    def read(self, size=None):
        assert size is not None, "Sorry, have to pass a size to read()"
        if size == 0:
            return ''
        evt, data = diesel.first(sleep=self._timeout, receive=size)
        if evt == 'sleep':
            self._timeout = None
            raise requests.exceptions.Timeout
        return data

    @diesel.call
    def readline(self, max_size=None):
        evt, line = diesel.first(sleep=self._timeout, until='\n')
        if evt == 'sleep':
            self._timeout = None
            raise requests.exceptions.Timeout
        if max_size:
            line = "".join([self._extra, line])
            nl = line.find('\n') + 1
            if nl > max_size:
                nl = max_size
            line, self._extra = line[:nl], line[nl:]
        return line

    @diesel.call
    def write(self, data):
        diesel.send(data)

    @diesel.call
    def next(self):
        data = self.readline()
        if not data:
            raise StopIteration()
        return data

    def __iter__(self):
        return self

    def close(self):
        self._client.close()

class HTTPConnection(httplib.HTTPConnection):
    def connect(self):
        try:
            self.sock = SocketLike(self.host, self.port)
        except DNSResolutionError:
            raise requests.ConnectionError

class HTTPSConnection(httplib.HTTPSConnection):
    def connect(self):
        try:
            kw = {'ssl_ctx': SSL.Context(SSL.SSLv23_METHOD)}
            self.sock = SocketLike(self.host, self.port, **kw)
        except DNSResolutionError:
            raise requests.ConnectionError

class RequestsLibNotFound(Exception):pass

def enable_requests():
    """This is monkeypatching."""
    if not connectionpool:
        msg = "You need to install requests (http://python-requests.org)"
        raise RequestsLibNotFound(msg)
    connectionpool.HTTPConnection = HTTPConnection
    connectionpool.HTTPSConnection = HTTPSConnection


########NEW FILE########
__FILENAME__ = pool
'''Simple connection pool for asynchronous code.
'''
from collections import deque
from diesel import *
from diesel.util.queue import Queue, QueueTimeout
from diesel.util.event import Event


class ConnectionPoolFull(Exception): pass

class InfiniteQueue(object):
    def get(self, timeout):
        pass

    def put(self):
        pass

class ConnectionPool(object):
    '''A connection pool that holds `pool_size` connected instances,
    calls init_callable() when it needs more, and passes
    to close_callable() connections that will not fit on the pool.
    '''

    def __init__(self, init_callable, close_callable, pool_size=5, pool_max=None, poll_max_timeout=5):
        self.init_callable = init_callable
        self.close_callable = close_callable
        self.pool_size = pool_size
        self.poll_max_timeout = poll_max_timeout
        if pool_max:
            self.remaining_conns = Queue()
            for _ in xrange(pool_max):
                self.remaining_conns.inp.append(None)
        else:
            self.remaining_conns = InfiniteQueue()
        self.connections = deque()

    def get(self):
        try:
            self.remaining_conns.get(timeout=self.poll_max_timeout)
        except QueueTimeout:
            raise ConnectionPoolFull()

        if not self.connections:
            self.connections.append(self.init_callable())
        conn = self.connections.pop()

        if not conn.is_closed:
            return conn
        else:
            self.remaining_conns.put()
            return self.get()

    def release(self, conn, error=False):
        self.remaining_conns.put()
        if not conn.is_closed:
            if not error and len(self.connections) < self.pool_size:
                self.connections.append(conn)
            else:
                self.close_callable(conn)

    @property
    def connection(self):
        return ConnContextWrapper(self, self.get())

class ConnContextWrapper(object):
    '''Context wrapper for try/finally behavior using the
    "with" statement.

    Ensures that connections return to the pool when the
    code block that requires them has ended.
    '''
    def __init__(self, pool, conn):
        self.pool = pool
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, type, value, tb):
        error = type is not None
        self.pool.release(self.conn, error)

class ThreadPoolDie(object): pass

class ThreadPool(object):
    def __init__(self, concurrency, handler, generator, finalizer=None):
        self.concurrency = concurrency
        self.handler = handler
        self.generator = generator
        self.finalizer = finalizer

    def handler_wrap(self):
        try:
            label("thread-pool-%s" % self.handler)
            while True:
                self.waiting += 1
                if self.waiting == 1:
                    self.trigger.set()
                i = self.q.get()
                self.waiting -= 1
                if i == ThreadPoolDie:
                    return
                self.handler(i)
        finally:
            self.running -=1
            if self.waiting == 0:
                self.trigger.set()
            if self.running == 0:
                self.finished.set()

    def __call__(self):
        self.q = Queue()
        self.trigger = Event()
        self.finished = Event()
        self.waiting = 0
        self.running = 0
        try:
            while True:
                for x in xrange(self.concurrency - self.running):
                    self.running += 1
                    fork(self.handler_wrap)

                if self.waiting == 0:
                    self.trigger.wait()
                    self.trigger.clear()

                try:
                    n = self.generator()
                except StopIteration:
                    break

                self.q.put(n)
                sleep()
        finally:
            for x in xrange(self.concurrency):
                self.q.put(ThreadPoolDie)
            if self.finalizer:
                self.finished.wait()
                fork(self.finalizer)

class TerminalThreadPool(ThreadPool):
    def __call__(self, *args, **kw):
        try:
            ThreadPool.__call__(self, *args, **kw)
        finally:
            while self.running:
                self.trigger.wait()
                self.trigger.clear()
            log.warning("TerminalThreadPool's producer exited; issuing quickstop()")
            fork(quickstop)

########NEW FILE########
__FILENAME__ = process
"""diesel's async I/O event hub meets multiprocessing.

Let's you run CPU intensive work in subprocesses and not block the event hub
while doing so.

"""
import multiprocessing as mp
import traceback

from diesel import runtime
from diesel import core
from diesel.util.queue import Queue


def spawn(func):
    """Spawn a new process that will run func.

    The returned Process instance can be called just like func.

    The spawned OS process lives until it is term()ed or otherwise dies. Each
    call to the returned Process instance results in another iteration of
    the remote loop. This way a single process can handle multiple calls to
    func.

    """
    return Process(func)


def term(proc):
    """Terminate the given proc.

    That is all.
    """
    proc.cleanup()
    proc.proc.terminate()


class ConflictingCall(Exception):
    pass

class Process(object):
    """A subprocess that cooperates with diesel's event hub.

    Communication with the spawned process happens over a pipe. Data that
    is to be sent to or received from the process is dispatched by the
    event hub. This makes it easy to run CPU intensive work in a non-blocking
    fashion and utilize multiple CPU cores.

    """
    def __init__(self, func):
        """Creates a new Process instance that will call func.

        The returned instance can be called as if it were func. The following
        code will run ``time.sleep`` in a subprocess and execution will resume
        when the remote call completes. Other green threads can run in the
        meantime.

        >>> time_sleep = Process(time.sleep)
        >>> time_sleep(4.2)
        >>> do_other_stuff()
        
        """
        self.func = func
        self.proc = None
        self.caller = None
        self.args = None
        self.params = None
        self.pipe = None
        self.in_call = False
        self.launch()

    def launch(self):
        """Starts a subprocess and connects it to diesel's plumbing.

        A pipe is created, registered with the event hub and used to
        communicate with the subprocess.

        """
        self.pipe, remote_pipe = mp.Pipe()
        runtime.current_app.hub.register(
            self.pipe,
            self.handle_return_value,
            self.send_arguments_to_process,
            runtime.current_app.global_bail('Process error!'),
        )
        def wrapper(pipe):
            while True:
                try:
                    args, params = pipe.recv()
                    pipe.send(self.func(*args, **params))
                except (SystemExit, KeyboardInterrupt):
                    pipe.close()
                    break
                except Exception, e:
                    e.original_traceback = traceback.format_exc()
                    pipe.send(e)

        self.proc = mp.Process(target=wrapper, args=(remote_pipe,))
        self.proc.daemon = True
        self.proc.start()

    def cleanup(self):
        runtime.current_app.hub.unregister(self.pipe)

    def handle_return_value(self):
        """Wakes up the caller with the return value of the subprocess func.

        Called by the event hub when data is ready.

        """
        try:
            result = self.pipe.recv()
        except EOFError:
            self.pipe.close()
            self.proc.terminate()
        else:
            self.in_call = False
            self.caller.wake(result)

    def send_arguments_to_process(self):
        """Sends the arguments to the function to the remote process.

        Called by the event hub after the instance has been called.

        """
        runtime.current_app.hub.disable_write(self.pipe)
        self.pipe.send((self.args, self.params))

    def __call__(self, *args, **params):
        """Trigger the execution of self.func in the subprocess.

        Switches control back to the event hub, letting other loops run until
        the subprocess finishes computation. Returns the result of the
        subprocess's call to self.func.

        """
        if self.in_call:
            msg = "Another loop (%r) is executing this process." % self.caller
            raise ConflictingCall(msg)
        runtime.current_app.hub.enable_write(self.pipe)
        self.args = args
        self.params = params
        self.caller = core.current_loop
        self.in_call = True
        return self.caller.dispatch()

class NoSubProcesses(Exception):
    pass

class ProcessPool(object):
    """A bounded pool of subprocesses.

    An instance is callable, just like a Process, and will return the result
    of executing the function in a subprocess. If all subprocesses are busy,
    the caller will wait in a queue.

    """
    def __init__(self, concurrency, handler):
        """Creates a new ProcessPool with subprocesses that run the handler.

        Args:
            concurrency (int): The number of subprocesses to spawn.
            handler (callable): A callable that the subprocesses will execute.

        """
        self.concurrency = concurrency
        self.handler = handler
        self.available_procs = Queue()
        self.all_procs = []

    def __call__(self, *args, **params):
        """Gets a process from the pool, executes it, and returns the results.

        This call will block until there is a process available to handle it.

        """
        if not self.all_procs:
            raise NoSubProcesses("Did you forget to start the pool?")
        try:
            p = self.available_procs.get()
            result = p(*args, **params)
            return result
        finally:
            self.available_procs.put(p)

    def pool(self):
        """A callable that starts the processes in the pool.

        This is useful as the callable to pass to a diesel.Loop when adding a
        ProcessPool to your application.

        """
        for i in xrange(self.concurrency):
            proc = spawn(self.handler)
            self.available_procs.put(proc)
            self.all_procs.append(proc)

if __name__ == '__main__':
    import diesel

    def sleep_and_return(secs):
        import time
        start = time.time()
        time.sleep(secs)
        return time.time() - start
    sleep_pool = ProcessPool(2, sleep_and_return)

    def main():
        def waiting(ident):
            print ident, "waiting ..."
            t = sleep_pool(4)
            print ident, "woken up after", t

        diesel.fork(waiting, 'a')
        diesel.fork(waiting, 'b')
        diesel.fork(waiting, 'c')
        for i in xrange(11):
            print "busy!"
            diesel.sleep(1)
        div = spawn(lambda x,y: x/y)
        try:
            div(1,0)
        except ZeroDivisionError, e:
            diesel.log.error(e.original_traceback)
        print '^^ That was an intentional exception.'
        term(div)
        psleep = spawn(sleep_and_return)
        diesel.fork(psleep, 0.5)
        diesel.fork(psleep, 0.5)
        diesel.sleep(1)
        print '^^ That was an intentional exception.'
        diesel.quickstop()
        
    diesel.quickstart(sleep_pool.pool, main)

########NEW FILE########
__FILENAME__ = queue
from uuid import uuid4
import random
from collections import deque
from contextlib import contextmanager

from diesel import fire, sleep, first
from diesel.events import Waiter, StopWaitDispatch

class QueueEmpty(Exception): pass
class QueueTimeout(Exception): pass

class Queue(Waiter):
    def __init__(self):
        self.inp = deque()

    def put(self, i=None):
        self.inp.append(i)
        fire(self)

    def get(self, waiting=True, timeout=None):
        if self.inp:
            val = self.inp.popleft()
            sleep()
            return val
        mark = None

        if waiting:
            kw = dict(waits=[self])
            if timeout:
                kw['sleep'] = timeout
            mark, val = first(**kw)
            if mark == self:
                return val
            else:
                raise QueueTimeout()

        raise QueueEmpty()

    def __iter__(self):
        return self

    def next(self):
        return self.get()

    @property
    def is_empty(self):
        return not bool(self.inp)

    def process_fire(self, value):
        if self.inp:
            return self.inp.popleft()
        else:
            raise StopWaitDispatch()

    def ready_early(self):
        return not self.is_empty

class Fanout(object):
    def __init__(self):
        self.subs = set()

    def pub(self, m):
        for s in self.subs:
            s.put(m)

    @contextmanager
    def sub(self):
        q = Queue()
        self.subs.add(q)
        try:
            yield q
        finally:
            self.subs.remove(q)

class Dispatcher(object):
    def __init__(self):
        self.subs = {}
        self.keys = []
        self.backlog = []

    def dispatch(self, m):
        if self.subs:
            k = random.choice(self.keys)
            self.subs[k].put(m)
        else:
            self.backlog.append(m)

    @contextmanager
    def accept(self):
        q = Queue()
        if self.backlog:
            for b in self.backlog:
                q.put(b)
            self.backlog = []
        id = uuid4()
        self.subs[id] = q
        self.keys = list(self.subs)
        try:
            yield q
        finally:
            del self.subs[id]
            self.keys = list(self.subs)
            while not q.is_empty:
                self.dispatch(q.get())

########NEW FILE########
__FILENAME__ = stats

from diesel import core

class CPUStats(object):
    def __init__(self):
        self.caller = core.current_loop
        self.cpu_seconds = 0.0

    def __enter__(self):
        self.start_clock = self.caller.clocktime()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not (exc_type and exc_val and exc_tb):
            end_clock = self.caller.clocktime()
            self.cpu_seconds = end_clock - self.start_clock


########NEW FILE########
__FILENAME__ = streams
import thread
from diesel.util.queue import Queue
from diesel import fork_from_thread

def put_stream_token(q, line):
    q.put(line)

def consume_stream(stream, q):
    while True:
        line = stream.readline()
        fork_from_thread(put_stream_token, q, line)
        if line == '':
            break

def create_line_input_stream(fileobj):
    q = Queue()
    thread.start_new_thread(consume_stream, (fileobj, q))
    return q

########NEW FILE########
__FILENAME__ = web
'''Slight wrapper around flask to fit the diesel

mold.
'''
import traceback

from flask import * # we're essentially republishing
from werkzeug.debug import tbtools
from diesel.protocols.websockets import WebSocketServer

from app import Application, Service, quickstart
from diesel import log, set_log_level, loglevels


class _FlaskTwiggyLogProxy(object):
    """Proxies to a Twiggy Logger.

    Nearly all attribute access is proxied to a twiggy Logger, with the
    exception of the `name` attribute. This one change brings it closer in
    line with the API of the Python standard library `logging` module which
    Flask expects.

    """
    def __init__(self, name):
        self.__dict__['_logger'] = log.name(name)
        self.__dict__['name'] = name

    def __getattr__(self, name):
        return getattr(self._logger, name)

    def __setattr__(self, name, value):
        return setattr(self._logger, name, value)

class DieselFlask(Flask):
    def __init__(self, name, *args, **kw):
        self.jobs = []
        self.diesel_app = self.make_application()
        Flask.__init__(self, name, *args, **kw)

    use_x_sendfile = True

    def request_class(self, environ):
        return environ # `id` -- environ IS the existing request.  no need to make another

    @classmethod
    def make_application(cls):
        return Application()

    def make_logger(self, level):
        # Flask expects a _logger attribute which we set here.
        self._logger = _FlaskTwiggyLogProxy(self.logger_name)
        self._logger.min_level = level

    def log_exception(self, exc_info):
        """A replacement for Flask's default.

        The default passed an exc_info parameter to logger.error(), which
        diesel doesn't support.

        """
        self._logger.trace().error('Exception on {0} [{1}]',
            request.path,
            request.method
        )

    def schedule(self, *args):
        self.jobs.append(args)

    def handle_request(self, req):
        with self.request_context(req):
            try:
                response = self.full_dispatch_request()
            except Exception, e:
                self.log_exception(e)
                try:
                    response = self.make_response(self.handle_exception(e))
                except:
                    tb = tbtools.get_current_traceback(skip=1)
                    response = Response(tb.render_summary(), headers={'Content-Type' : 'text/html'})

        return response

    def make_service(self, port=8080, iface='', verbosity=loglevels.DEBUG, debug=True):
        self.make_logger(verbosity)
        if debug:
            self.debug = True

        from diesel.protocols.http import HttpServer
        http_service = Service(HttpServer(self.handle_request), port, iface)

        return http_service

    def websocket(self, f):
        def no_web(req):
            assert 0, "Only `Upgrade` HTTP requests on a @websocket"
        ws = WebSocketServer(no_web, f)
        def ws_call(*args, **kw):
            assert not args and not kw, "No arguments allowed to websocket routes"
            return ws.do_upgrade(request)
        return ws_call

    def run(self, *args, **params):
        http_service = self.make_service(*args, **params)
        self.schedule(http_service)
        quickstart(*self.jobs, __app=self.diesel_app)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Diesel documentation build configuration file, created by
# sphinx-quickstart on Wed Mar 13 21:22:42 2013.
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
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Diesel'
copyright = u'2013, Jamie Turner'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '3.0'
# The full version, including alpha/beta/rc tags.
release = '3.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
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
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Dieseldoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Diesel.tex', u'Diesel Documentation',
   u'Jamie Turner', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'diesel', u'Diesel Documentation',
     [u'Jamie Turner'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Diesel', u'Diesel Documentation',
   u'Jamie Turner', 'Diesel', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = chat-redis
import time, cgi

from diesel import Service, Application, sleep, first, Loop

from diesel.web import DieselFlask
from diesel.protocols.websockets import WebSocketDisconnect

from diesel.util.queue import Fanout
from diesel.protocols.redis import RedisSubHub, RedisClient
from simplejson import dumps, loads, JSONDecodeError



content = '''
<html>
<head>
<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.7.1/jquery.min.js" type="text/javascript"></script>
<script>

var chatter = new WebSocket("ws://" + document.location.host + "/ws");

chatter.onopen = function (evt) {
}

chatter.onmessage = function (evt) {
    var res = JSON.parse(evt.data);
    var p = $('#the-chat');
    var add = $('<div class="chat-message"><span class="nick">&lt;' + res.nick +
    '&gt;</span> ' + res.message + '</div>');
    p.append(add);
    if (p.children().length > 15)
        p.children().first().remove();
}

function push () {
    chatter.send(JSON.stringify({
        message: $('#the-message').val(),
        nick: $('#the-nick').val()
    }));
    $('#the-message').val('');
    $('#the-message').focus();
}

$(function() {
    $('#the-button').click(push);
    $('#the-message').keyup(function (evt) { if (evt.keyCode == 13) push(); });
});

</script>

<style>

body {
    width: 800px;
    margin: 25px auto;
}

#the-chat {
    margin: 15px 8px;
}

.chat-message {
    margin: 4px 0;
}


.nick {
    font-weight: bold;
    color: #555;
}

</style>

</head>
<body>

<h2>Diesel WebSocket Chat</h2>

<div style="font-size: 13px; font-weight: bold; margin-bottom: 10px">
Nick: <input type="text" size="10" id="the-nick" />&nbsp;&nbsp;
Message: <input type="text" size="60" id="the-message" />&nbsp;&nbsp;
<input type="button" value="Send" id="the-button"/>
</div>

<div id="the-chat">
</div>

</body>
</html>
'''


#f = Fanout()

app = DieselFlask(__name__)

hub = RedisSubHub(host="localhost")

@app.route("/")
def web_handler():
    return content

@app.route("/ws")
@app.websocket
def pubsub_socket(req, inq, outq):
    c = hub.make_client()
    with hub.subq('foo') as group:
        while True:
            q, v = first(waits=[inq, group])
            if q == inq: # getting message from client
                print "(inq) %s" % v
                cmd = v.get("cmd", "")
                if cmd=="":
                    print "published message to %i subscribers" % c.publish("foo", dumps({
                    'nick' : cgi.escape(v['nick'].strip()),
                    'message' : cgi.escape(v['message'].strip()),
                    }))
                else:
                    outq.put(dict(message="test bot"))
            elif q == group: # getting message for broadcasting
                chan, msg_str = v
                try:
                    msg = loads(msg_str)
                    data = dict(message=msg['message'], nick=msg['nick'])
                    print "(outq) %s" % data
                    outq.put(data)
                except JSONDecodeError:
                    print "error decoding message %s" % msg_str
            elif isinstance(v, WebSocketDisconnect): # getting a disconnect signal
                return
            else:
                print "oops %s" % v

app.diesel_app.add_loop(Loop(hub))
app.run()


########NEW FILE########
__FILENAME__ = chat
import time, cgi

from diesel import Service, Application, sleep, first
from diesel.web import DieselFlask
from diesel.protocols.websockets import WebSocketDisconnect
from diesel.util.queue import Fanout

app = DieselFlask(__name__)

content = '''
<html>
<head>
<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.7.1/jquery.min.js" type="text/javascript"></script>
<script>

var chatter = new WebSocket("ws://" + document.location.host + "/ws");

chatter.onopen = function (evt) {
}

chatter.onmessage = function (evt) {
    var res = JSON.parse(evt.data);
    var p = $('#the-chat');
    var add = $('<div class="chat-message"><span class="nick">&lt;' + res.nick +
    '&gt;</span> ' + res.message + '</div>');
    p.append(add);
    if (p.children().length > 15)
        p.children().first().remove();
}

function push () {
    chatter.send(JSON.stringify({
        message: $('#the-message').val(),
        nick: $('#the-nick').val()
    }));
    $('#the-message').val('');
    $('#the-message').focus();
}

$(function() {
    $('#the-button').click(push);
    $('#the-message').keyup(function (evt) { if (evt.keyCode == 13) push(); });
});

</script>

<style>

body {
    width: 800px;
    margin: 25px auto;
}

#the-chat {
    margin: 15px 8px;
}

.chat-message {
    margin: 4px 0;
}


.nick {
    font-weight: bold;
    color: #555;
}

</style>

</head>
<body>

<h2>Diesel WebSocket Chat</h2>

<div style="font-size: 13px; font-weight: bold; margin-bottom: 10px">
Nick: <input type="text" size="10" id="the-nick" />&nbsp;&nbsp;
Message: <input type="text" size="60" id="the-message" />&nbsp;&nbsp;
<input type="button" value="Send" id="the-button"/>
</div>

<div id="the-chat">
</div>

</body>
</html>
'''


f = Fanout()

@app.route("/")
def web_handler():
    return content

@app.route("/ws")
@app.websocket
def socket_handler(req, inq, outq):
    with f.sub() as group:
        while True:
            q, v = first(waits=[inq, group])
            if q == group:
                outq.put(dict(message=v['message'], nick=v['nick']))
            elif isinstance(v, WebSocketDisconnect):
                return
            elif v.get('nick', '').strip() and v.get('message', '').strip():
                f.pub({
                    'nick' : cgi.escape(v['nick'].strip()),
                    'message' : cgi.escape(v['message'].strip()),
                    })

app.run()

########NEW FILE########
__FILENAME__ = child_test
from diesel import fork_child, sleep, ParentDiedException, quickstart, quickstop

def end_the_app_when_my_parent_dies():
    try:
        while True:
            print "child: weeee!"
            sleep(1)
    except ParentDiedException:
        print "child: ack, woe is me, I'm an orphan.  goodbye cruel world"
        quickstop()


def parent():
    print "parent: okay, parent here."
    sleep(1)
    print "parent: I'm so excited, about to become a parent"
    sleep(1)
    fork_child(end_the_app_when_my_parent_dies)
    sleep(1)
    print "parent: and, there he goes.  I'm so proud"
    sleep(4)
    print "parent: okay, I'm outta here"


if __name__ == '__main__':
    quickstart(parent)

########NEW FILE########
__FILENAME__ = clocker
import os
from diesel import Loop, fork, Application, sleep
from diesel.util.stats import CPUStats

def not_always_busy_worker():
    with CPUStats() as stats:
        for _ in xrange(12):
            for i in xrange(10000000): # do some work to forward cpu seconds
                pass
            sleep(0.1) # give up control

    print "cpu seconds ",  stats.cpu_seconds

def spawn_busy_workers():
    for _ in xrange(0,3):
        fork(not_always_busy_worker)

a = Application()
a.add_loop(Loop(spawn_busy_workers), track=True)
a.run()

########NEW FILE########
__FILENAME__ = combined
import time
from diesel import Service, Client, send, quickstart, quickstop
from diesel import until, call, log

def handle_echo(remote_addr):
    while True:
        message = until('\r\n')
        send("you said: %s" % message)

class EchoClient(Client):
    @call
    def echo(self, message):
        send(message + '\r\n')
        back = until("\r\n")
        return back

log = log.name('echo-system')

def do_echos():
    client = EchoClient('localhost', 8000)
    t = time.time()
    for x in xrange(5000):
        msg = "hello, world #%s!" % x
        echo_result = client.echo(msg)
        assert echo_result.strip() == "you said: %s" % msg
    log.info('5000 loops in {0:.2f}s', time.time() - t)
    quickstop()

quickstart(Service(handle_echo, port=8000), do_echos)

########NEW FILE########
__FILENAME__ = combined_tls
from OpenSSL import SSL
import time
from diesel import Service, Client, send, quickstart, quickstop
from diesel import until, call, log

server_ctx = SSL.Context(SSL.TLSv1_METHOD)
server_ctx.use_privatekey_file('snakeoil-key.pem')
server_ctx.use_certificate_file('snakeoil-cert.pem')

def handle_echo(remote_addr):
    while True:
        message = until('\r\n')
        send("you said: %s" % message)

class EchoClient(Client):
    @call
    def echo(self, message):
        send(message + '\r\n')
        back = until("\r\n")
        return back

log = log.name('echo-system')

def do_echos():
    with EchoClient('localhost', 8000, ssl_ctx=SSL.Context(SSL.TLSv1_METHOD)) as client:
        t = time.time()
        for x in xrange(5000):
            msg = "hello, world #%s!" % x
            echo_result = client.echo(msg)
            assert echo_result.strip() == "you said: %s" % msg
        log.info('5000 loops in {0:.2f}s', time.time() - t)
    quickstop()

quickstart(Service(handle_echo, port=8000, ssl_ctx=server_ctx), do_echos)

########NEW FILE########
__FILENAME__ = consolechat
# vim:ts=4:sw=4:expandtab
'''Simple chat server.

telnet, type your name, hit enter, then chat.  Invite
a friend to do the same.
'''
import sys
from diesel import (
    Application, Service, until_eol, fire, first, send, Client, call, thread,
    fork, Loop,
)
from diesel.util.queue import Queue

def chat_server(addr):
    my_nick = until_eol().strip()
    while True:
        evt, data = first(until_eol=True, waits=['chat_message'])
        if evt == 'until_eol':
           fire('chat_message', (my_nick, data.strip()))
        else:
            nick, message = data
            send("<%s> %s\r\n"  % (nick, message))

class ChatClient(Client):
    def __init__(self, *args, **kw):
        Client.__init__(self, *args, **kw)
        self.input = Queue()

    def read_chat_message(self, prompt):
        msg = raw_input(prompt)
        return msg

    def input_handler(self):
        nick = thread(self.read_chat_message, "nick: ").strip()
        self.nick = nick
        self.input.put(nick)
        while True:
            msg = thread(self.read_chat_message, "").strip()
            self.input.put(msg)

    @call
    def chat(self):
        fork(self.input_handler)
        nick = self.input.get()
        send("%s\r\n" % nick)
        while True:
            evt, data = first(until_eol=True, waits=[self.input])
            if evt == "until_eol":
                print data.strip()
            else:
                send("%s\r\n" % data)

def chat_client():
    with ChatClient('localhost', 8000) as c:
        c.chat()

app = Application()
if sys.argv[1] == "server":
    app.add_service(Service(chat_server, 8000))
elif sys.argv[1] == "client":
    app.add_loop(Loop(chat_client))
else:
    print "USAGE: python %s [server|client]" % sys.argv[0]
    raise SystemExit(1)
app.run()

########NEW FILE########
__FILENAME__ = convoy
from diesel.convoy import convoy, ConvoyRole
import kv_palm
convoy.register(kv_palm)

from kv_palm import ( GetRequest, GetOkay, GetMissing,
                      SetRequest, SetOkay )

class KvNode(ConvoyRole):
    limit = 1
    def __init__(self):
        self.values = {}
        ConvoyRole.__init__(self)

    def handle_GetRequest(self, sender, request):
        if request.key in self.values:
            sender.respond(GetOkay(value=self.values[request.key]))
        else:
            sender.respond(GetMissing())

    def handle_SetRequest(self, sender, request):
        self.values[request.key] = request.value
        sender.respond(SetOkay())

def run_sets():
    print "I am here!"
    convoy.send(SetRequest(key="foo", value="bar"))
    print "I am here 2!"
    convoy.send(SetRequest(key="foo", value="bar"))
    print "I am here 3!"
    print convoy.rpc(GetRequest(key="foo")).single
    print "I am here 4!"

    import time
    t = time.time()
    for x in xrange(5000):
        convoy.send(SetRequest(key="foo", value="bar"))
        r = convoy.rpc(GetRequest(key="foo")).single
    print 5000.0 / (time.time() - t), "/ s"
    print ''
    print r

if __name__ == '__main__':
    convoy.run_with_nameserver("localhost:11111", ["localhost:11111"], KvNode(), run_sets)
    #import cProfile
    #cProfile.run('convoy.run_with_nameserver("localhost:11111", ["localhost:11111"], KvNode(), run_sets)')

########NEW FILE########
__FILENAME__ = crawler
# vim:ts=4:sw=4:expandtab
'''A very simple, flawed web crawler--demonstrates
Clients + Loops
'''

import sys, time, re, os
from urlparse import urlparse, urljoin

url, folder = sys.argv[1:]

schema, host, path, _, _, _ = urlparse(url)
path = path or '/'
base_dir = path if path.endswith('/') else os.path.dirname(path)
if not base_dir.endswith('/'):
    base_dir += '/'

assert schema == 'http', 'http only'

from diesel import log as glog, quickstart, quickstop
from diesel.protocols.http import HttpClient
from diesel.util.pool import ThreadPool, ConnectionPool

CONCURRENCY = 10 # go easy on those apache instances!

url_exp = re.compile(r'(src|href)="([^"]+)', re.MULTILINE | re.IGNORECASE)

heads = {'Host' : host}

def get_links(s):
    for mo in url_exp.finditer(s):
        lpath = mo.group(2)
        if ':' not in lpath and '..' not in lpath:
            if lpath.startswith('/'):
                yield lpath
            else:
                yield urljoin(base_dir, lpath)

conn_pool = ConnectionPool(lambda: HttpClient(host, 80), lambda c: c.close(), pool_size=CONCURRENCY)

def ensure_dirs(lpath):
    def g(lpath):
        while len(lpath) > len(folder):
            lpath = os.path.dirname(lpath)
            yield lpath
    for d in reversed(list(g(lpath))):
        if not os.path.isdir(d):
            os.mkdir(d)

def write_file(lpath, body):
    bytes.append(len(body))
    lpath = (lpath if not lpath.endswith('/') else (lpath + 'index.html')).lstrip('/')
    lpath = os.path.join(folder, lpath)
    ensure_dirs(lpath)
    open(lpath, 'w').write(body)

def follow_loop(lpath):
    log.info(" -> %s" % lpath)
    with conn_pool.connection as client:
        resp = client.request('GET', lpath, heads)
        write_file(lpath, resp.data)

bytes = []
count = None
log = glog.name('http-crawler')

def req_loop():
    global count

    log.info(path)
    with conn_pool.connection as client:
        resp = client.request('GET', path, heads)
    body = resp.data
    write_file(path, body)
    links = set(get_links(body))
    for l in links:
        yield l
    count = len(links) + 1

def stop():
    log.info("Fetched %s files (%s bytes) in %.3fs with concurrency=%s" % (count, sum(bytes), time.time() - t, CONCURRENCY))
    quickstop()

t = time.time()

pool = ThreadPool(CONCURRENCY, follow_loop, req_loop().next, stop)

quickstart(pool)

########NEW FILE########
__FILENAME__ = dispatch
from diesel.util.queue import Dispatcher
from diesel import quickstart, quickstop, sleep, log
from functools import partial

d = Dispatcher()
WORKERS = 10

r = [0] * WORKERS
def worker(x):
    with d.accept() as q:
        while True:
            q.get()
            r[x] += 1

def maker():
    for x in xrange(500000):
        d.dispatch(x)
        if x % 10000 == 0:
            sleep()
            log.info("values: {0}", r)
    quickstop()

quickstart(maker, *(partial(worker, x) for x in xrange(WORKERS)))

########NEW FILE########
__FILENAME__ = dreadlocks
'''Test for client to dreadlock network lock service.
'''

import uuid
from diesel import sleep, quickstart
from diesel.protocols.dreadlock import DreadlockService

locker = DreadlockService('localhost', 6001)
def f():
    with locker.hold("foo", 30):
        id = uuid.uuid4()
        print "start!", id
        sleep(2)
        print "end!", id

quickstart(f, f, f, f, f)

########NEW FILE########
__FILENAME__ = echo
# vim:ts=4:sw=4:expandtab
'''Simple echo server.
'''
from diesel import Application, Service, until_eol, send

def hi_server(addr):
    while 1:
        inp = until_eol()
        if inp.strip() == "quit":
            break
        send("you said %s" % inp)

app = Application()
app.add_service(Service(hi_server, 8013))
app.run()

########NEW FILE########
__FILENAME__ = event
from diesel.util.event import Event
from diesel import quickstart, quickstop, sleep

pistol = Event()

def racer():
    pistol.wait()
    print "CHAAARGE!"

def starter():
    print "Ready..."
    sleep(1)
    print "Set..."
    sleep(1)
    print " ~~~~~~~~~ BANG ~~~~~~~~~ "
    pistol.set()
    sleep(1)
    print " ~~~~~~~~~ RACE OVER ~~~~~~~~~ "
    quickstop()

quickstart(starter, [racer for x in xrange(8)])

########NEW FILE########
__FILENAME__ = fanout
from diesel import quickstart, quickstop, sleep
from diesel.util.queue import Fanout
from diesel.util.event import Countdown

LISTENERS = 10
EVENTS = 5

cd = Countdown(LISTENERS * EVENTS)

f = Fanout()

def listener(x):
    with f.sub() as q:
        while True:
            v = q.get()
            print '%s <- %s' % (x, v)
            cd.tick()

def teller():
    for x in xrange(EVENTS):
        sleep(2)
        f.pub(x)

def killer():
    cd.wait()
    quickstop()

from functools import partial
quickstart(killer, teller,
        *[partial(listener, x) for x in xrange(LISTENERS)])

########NEW FILE########
__FILENAME__ = fire
# vim:ts=4:sw=4:expandtab
'''Example of event firing.
'''
import time
import random
from diesel import (quickstart, quickstop, sleep, 
                    fire, wait, log, loglevels,
                    set_log_level)

set_log_level(loglevels.DEBUG)

def gunner():
    x = 1
    while True:
        fire('bam', x)
        x += 1
        sleep()

def sieged():
    t = time.time()
    while True:
        n = wait('bam')
        if n % 10000 == 0:
            log.info(str(n))
            if n == 50000:
                delt = time.time() - t
                log.debug("50,000 messages in {0:.3f}s {1:.1f}/s)", delt, 50000 / delt)
                quickstop()

log = log.name('fire-system')
quickstart(gunner, sieged)

########NEW FILE########
__FILENAME__ = forker
from diesel import Loop, fork, Application, sleep

def sleep_and_print(num):
    sleep(1)
    print num
    sleep(1)
    a.halt()


def forker():
    for x in xrange(5):
        fork(sleep_and_print, x)

a = Application()
a.add_loop(Loop(forker))
a.run()

########NEW FILE########
__FILENAME__ = http
# vim:ts=4:sw=4:expandtab
'''The oh-so-canonical "Hello, World!" http server.
'''
from diesel import Application, Service
from diesel.protocols import http

def hello_http(req):
    return http.Response("Hello, World!")

app = Application()
app.add_service(Service(http.HttpServer(hello_http), 8088))
import cProfile
cProfile.run('app.run()')

########NEW FILE########
__FILENAME__ = http_client
# vim:ts=4:sw=4:expandtab
'''Simple http client example.

Check out crawler.py for more advanced behaviors involving
many concurrent clients.
'''

from diesel import Application, Loop, log, quickstart, quickstop
from diesel.protocols.http import HttpClient

def req_loop():
    for path in ['/Py-TOC', '/']:
        with HttpClient('www.jamwt.com', 80) as client:
            heads = {'Host' : 'www.jamwt.com'}
            log.info(str(client.request('GET', path, heads)))
    quickstop()

log = log.name('http-client')
quickstart(req_loop)

########NEW FILE########
__FILENAME__ = http_pool
import sys
from time import time

from diesel import quickstart, quickstop
from diesel.protocols.http.pool import request

def f():
    t1 = time()
    print request("http://example.iana.org/missing"), 'is missing?'
    t2 = time()
    print request("http://example.iana.org/missing"), 'is missing?'
    t3 = time()
    print request("http://example.iana.org/missing"), 'is missing?'
    t4 = time()
    print request("http://example.iana.org/"), 'is found?'
    t5 = time()

    print 'First request should (probably) have been longer (tcp handshake) than subsequent 3 requests:'
    reduce(lambda t1, t2: sys.stdout.write("%.4f\n" % (t2 - t1)) or t2, (t1, t2, t3, t4, t5))

    quickstop()

quickstart(f)

########NEW FILE########
__FILENAME__ = keep_alive
from diesel import Application, Loop, sleep
import time

def restart():
    print "I should restart"
    a = b

a = Application()
a.add_loop(Loop(restart), keep_alive=True)
a.run()

########NEW FILE########
__FILENAME__ = newwait
import random

from diesel import quickstart, first, sleep, fork
from diesel.util.queue import Queue

def fire_random(queues):
    while True:
        sleep(1)
        random.choice(queues).put(None)

def make_and_wait():
    q1 = Queue()
    q2 = Queue()
    both = [q1, q2]

    fork(fire_random, both)

    while True:
        q, v = first(waits=both)
        assert v is None
        if q == q1:
            print 'q1'
        elif q == q2:
            print 'q2'
        else:
            assert 0

quickstart(make_and_wait)

########NEW FILE########
__FILENAME__ = nitro
from pynitro import NitroFrame
from diesel.protocols.nitro import DieselNitroSocket
from diesel import quickstart, quickstop

#loc = "tcp://127.0.0.1:4444"
loc = "inproc://foobar"

def server():
    with DieselNitroSocket(bind=loc) as sock:
        while True:
            m = sock.recv()
            sock.send(NitroFrame("you said: " + m.data))

def client():
    with DieselNitroSocket(connect=loc) as sock:
        for x in xrange(100000):
            sock.send(NitroFrame("Hello, dude!"))
            m = sock.recv()
            assert m.data == "you said: Hello, dude!"

        quickstop()

quickstart(server, client)

########NEW FILE########
__FILENAME__ = nitro_echo_service
import diesel
from pynitro import NitroFrame
from diesel.protocols.nitro import (
    DieselNitroService, DieselNitroSocket,
)
import uuid

NUM_CLIENTS = 300
cids = range(NUM_CLIENTS)
dead = 0

def echo_client():
    global dead
    id = str(uuid.uuid4())
    s = DieselNitroSocket(connect='tcp://127.0.0.1:4321')
    for i in xrange(50):
        s.send(NitroFrame('%s|m%d' % (id, i)))
        r = s.recv()
        assert r.data == 'm%d:%d' % (i, i + 1)
    dead += 1
    print 'done!', dead

class EchoService(DieselNitroService):
    def handle_client_packet(self, packet, ctx):
        count = ctx.setdefault('count', 0) + 1
        ctx['count'] = count
        return '%s:%d' % (packet, count)

    def parse_message(self, raw):
        return raw.split('|')

    def cleanup_client(self, client):
        print 'client timed out', client.identity

echo_svc = EchoService('tcp://*:4321')
diesel.quickstart(echo_svc.run, *(echo_client for i in xrange(NUM_CLIENTS)))


########NEW FILE########
__FILENAME__ = queue
from diesel.util.queue import Queue, QueueTimeout
from diesel.util.event import Countdown
from diesel import log as glog, sleep, quickstart, quickstop

q = Queue()
cd = Countdown(4)

def putter():
    log = glog.name("putter")

    log.info("putting 100000 things on queue")
    for x in xrange(100000):
        q.put(x)
        sleep()

def getter():
    log = glog.name("getter")
    got = 0
    while got < 25000:
        try:
            s = q.get(timeout=3)
            sleep()
        except QueueTimeout:
            log.warning("timeout before getting a value, retrying...")
            continue
        got += 1

    log.info("SUCCESS!  got all 25,000")
    cd.tick()

def manage():
    cd.wait()
    quickstop()

quickstart(manage, putter, [getter for x in xrange(4)])

########NEW FILE########
__FILENAME__ = queue_fairness_and_speed
import time
import uuid

import diesel
import diesel.core
from diesel.util.queue import Queue

NUM_ITEMS = 100000
NUM_WORKERS = 10

shutdown = uuid.uuid4().hex
q = Queue()
dones = Queue()

def worker():
    num_processed = 0
    while True:
        val = diesel.wait(q)
        if val == shutdown:
            break
        num_processed += 1
    fmt_args = (diesel.core.current_loop, num_processed)
    print "%s, worker done (processed %d items)" % fmt_args
    dones.put('done')

def main():
    start = time.time()

    for i in xrange(NUM_ITEMS):
        q.put('item %d' % i)
    for i in xrange(NUM_WORKERS):
        q.put(shutdown)

    for i in xrange(NUM_WORKERS):
        diesel.fork_child(worker)
    for i in xrange(NUM_WORKERS):
        dones.get()

    print 'all workers done in %.2f secs' % (time.time() - start)
    diesel.quickstop()

if __name__ == '__main__':
    diesel.quickstart(main)

########NEW FILE########
__FILENAME__ = redispub
# vim:ts=4:sw=4:expandtab
'''Simple RedisSubHub client example.
'''

from diesel import Application, Loop, sleep
from diesel.protocols.redis import RedisSubHub, RedisClient
import time, sys

def send_loop():
    c = RedisClient()
    sleep(1)

    print 'SEND S', time.time()

    for x in xrange(500):
        c.publish("foo", "bar")

    print 'SEND E', time.time()

hub = RedisSubHub()

def recv_loop():
    print 'RECV S', time.time()
    with hub.sub('foo') as poll:
        for x in xrange(500):
            q, content = poll.fetch()
    print 'RECV E', time.time()

a = Application()
a.add_loop(Loop(hub)) # start up the sub loop
if 'send' in sys.argv:
    a.add_loop(Loop(send_loop))
if 'recv' in sys.argv:    
    a.add_loop(Loop(recv_loop))
    a.add_loop(Loop(recv_loop))
a.run()

########NEW FILE########
__FILENAME__ = redis_lock
import random

from diesel import fork, quickstop, quickstart, sleep
from diesel.protocols.redis import RedisClient, RedisTransactionError, RedisLock, LockNotAcquired


"""Implement the Redis INCR command using a lock. Obviously this is inefficient, but it's a good
example of how to use the RedisLock class"""

key = 'test-lock-key'
incr_key = 'test-incr-key'
counter = 0


"""If sleep_factor > lock_timeout you are exercising the timeout loop, otherwise, that loop should be a noop"""
lock_timeout = 3
sleep_factor = 1



def take_lock():
    global counter
    client = RedisClient('localhost', 6379)
    try:
        with RedisLock(client, key, timeout=lock_timeout) as lock:
            v = client.get(incr_key)
            sleep(random.random() * sleep_factor)
            client.set(incr_key, int(v) + 1)
        counter += 1
    except LockNotAcquired:
        pass

def main():
    client = RedisClient('localhost', 6379)
    client.delete(key)
    client.set(incr_key, 0)

    for _ in xrange(500):
        fork(take_lock)
        if random.random() > 0.1:
            sleep(random.random() / 10)
    sleep(2)
    assert counter == int(client.get(incr_key)), 'Incr failed!'
    quickstop()


quickstart(main)

########NEW FILE########
__FILENAME__ = resolve_names
from diesel import resolve_dns_name, DNSResolutionError
from diesel import Application, Loop, sleep

def resolve_the_google():
    print 'started resolution!'
    g_ip = resolve_dns_name("www.google.com")
    print "www.google.com's ip is %s" % g_ip
    try:
        bad_host = "www.g8asdf21oogle.com"
        print "now checking %s" % bad_host
        resolve_dns_name(bad_host)
    except DNSResolutionError:
        print "yep, it failed as expected"
    else:
        raise RuntimeError("The bad host resolved.  That's unexpected.")
    g_ip = resolve_dns_name("www.google.com")
    g_ip = resolve_dns_name("www.google.com")
    g_ip = resolve_dns_name("www.google.com")
    g_ip = resolve_dns_name("www.google.com")
    a.halt()

def stuff():
    while True:
        print "doing stuff!"
        sleep(0.01)

a = Application()
a.add_loop(Loop(stuff))
a.add_loop(Loop(resolve_the_google))
a.run()

########NEW FILE########
__FILENAME__ = santa
import random
from diesel import Application, Loop, fire, wait, sleep

deer_group = []
elf_group = []

def santa():
    while True:
        deer_ready, elves_ready = len(deer_group) == 9, len(elf_group) == 3
        if deer_ready:
            work_with_group('deer', deer_group, 'deliver toys')
        if elves_ready:
            work_with_group('elf', elf_group, 'meet in my study')
        sleep(random.random() * 1)

def actor(name, type, group, task, max_group, max_sleep):
    def actor_event_loop():
        while True:
            sleep(random.random() * max_sleep)
            if len(group) < max_group:
                group.append(name)
                wait('%s-group-started' % type)
                print "%s %s" % (name, task)
                wait('%s-group-done' % type)
    return actor_event_loop

def work_with_group(name, group, message):
    print "Ho! Ho! Ho! Let's", message
    fire('%s-group-started' % name)
    sleep(random.random() * 3)
    excuse_group(name, group)

def excuse_group(name, group):
    group[:] = []
    fire('%s-group-done' % name, True)

def main():
    app = Application()
    app.add_loop(Loop(santa))

    elf_do = "meets in study"
    for i in xrange(10):
        app.add_loop(Loop(actor("Elf %d" % i, 'elf', elf_group, elf_do, 3, 3)))

    deer_do = "delivers toys"
    for name in [
            'Dasher', 'Dancer', 'Prancer', 
            'Vixen', 'Comet', 'Cupid', 
            'Donner', 'Blitzen', 'Rudolph',
            ]:
        app.add_loop(Loop(actor(name, 'deer', deer_group, deer_do, 9, 9)))

    app.run()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = signals
import os

from signal import SIGUSR1

import diesel

from diesel.util.event import Signal


log = diesel.log.name('signal-example')

def main():
    usr1 = Signal(SIGUSR1)
    ticks = 0
    log.fields(pid=os.getpid()).info('started')
    while True:
        evt, _ = diesel.first(sleep=1, waits=[usr1])
        if evt == 'sleep':
            ticks += 1
        elif evt == usr1:
            log.fields(ticks=ticks).info('stats')
            # must rearm() to use again
            evt.rearm()

diesel.quickstart(main)

########NEW FILE########
__FILENAME__ = sleep_server
# vim:ts=4:sw=4:expandtab
'''Demonstrate sleep-type behavior server-side.
'''
from diesel import Application, Service, until_eol, sleep, send

def delay_echo_server(addr):
    inp = until_eol()

    for x in xrange(4):
        sleep(2)
        send(str(x) + '\r\n')
    send("you said %s" % inp)

app = Application()
app.add_service(Service(delay_echo_server, 8013))
app.run()

########NEW FILE########
__FILENAME__ = stdin
import sys

from diesel import quickstart, fork_from_thread
from diesel.util.queue import Queue
from thread import start_new_thread

q = Queue()

def consume():
    while True:
        v = q.get()
        print 'DIESEL GOT', v

def put(line):
    q.put(line)

def create():
    while True:
        line = sys.stdin.readline()
        print 'iter!', line
        fork_from_thread(put, line)

start_new_thread(create, ())
quickstart(consume)

########NEW FILE########
__FILENAME__ = stdin_stream
import sys

from diesel import quickstart
from diesel.util.streams import create_line_input_stream

def consume():
    q = create_line_input_stream(sys.stdin)
    while True:
        v = q.get()
        print 'DIESEL GOT', v

quickstart(consume)

########NEW FILE########
__FILENAME__ = synchronized
from diesel import Application, Loop, sleep
from diesel.util.lock import synchronized
import random
free = 0
sync = 0

def free_loop():
    global free
    free += 1
    sleep(random.random())
    free -= 1
    print 'FREE', free

def sync_loop():
    global sync
    with synchronized():
        sync += 1
        sleep(random.random())
        sync -= 1
        print 'SYNC', sync

def manage():
    sleep(10)
    a.halt()

a = Application()
for l in (free_loop, sync_loop):
    for x in xrange(10):
        a.add_loop(Loop(l))
a.add_loop(Loop(manage))
a.run()


########NEW FILE########
__FILENAME__ = test_dnosetest
"""Here is an example test module that can be run with `dnosetests`.

It is written like a standard nose test module but the test functions are
executed within the diesel event loop. That means they can fork other
green threads, do network I/O and other diesel-ish things. Very handy for
writing integration tests against diesel services.

"""
import time

import diesel


def test_sleeps_then_passes():
    diesel.sleep(1)
    assert True

def test_sleeps_then_fails():
    diesel.sleep(1)
    assert False, "OH NOES!"

########NEW FILE########
__FILENAME__ = thread
# vim:ts=4:sw=4:expandtab
'''Example of deferring blocking calls to threads
'''
from diesel import log, thread, quickstart
import time
from functools import partial

def blocker(taskid, sleep_time):
    while True:
        def f():
            time.sleep(sleep_time)
        thread(f)
        log.info('yo! {0} from {1} task', time.time(), taskid)

quickstart(partial(blocker, 'fast', 1), partial(blocker, 'slow', 5))

########NEW FILE########
__FILENAME__ = thread_pool
from diesel import quickstart, sleep, quickstop
from diesel.util.pool import ThreadPool
import random

def handle_it(i):
    print 'S', i
    sleep(random.random())
    print 'E', i

def c():
    for x in xrange(0, 20):
        yield x

make_it = c().next

def stop_it():
    quickstop()

threads = ThreadPool(10, handle_it, make_it, stop_it)

quickstart(threads)

########NEW FILE########
__FILENAME__ = timer
from diesel import Application, Loop, sleep
import time

def l():
    for x in xrange(2):
        print "hi"
        time.sleep(1)
        sleep(5)
    a.halt()

a = Application()
a.add_loop(Loop(l))
a.add_loop(Loop(l))
a.run()

########NEW FILE########
__FILENAME__ = timer_bench
"""A benchmark for diesel's internal timers.

Try something like:

    $ python examples/timer_bench.py 10
    $ python examples/timer_bench.py 100
    $ python examples/timer_bench.py 1000

The script will output the total time to run with the given number of
producer/consumer pairs and a sample of CPU time while the benchmark was
running.

"""
import os
import subprocess
import sys
import time

import diesel
from diesel.util.event import Countdown
from diesel.util.queue import Queue

OPERATIONS = 60
cpustats = []


def producer(q):
    for i in xrange(OPERATIONS):
        diesel.sleep(0.5)
        q.put(i)

def consumer(q, done):
    for i in xrange(OPERATIONS):
        evt, data = diesel.first(waits=[q], sleep=10000)
        if evt == "sleep":
            print "sleep was triggered!"
            break
    done.tick()

def pair(done):
    q = Queue()
    diesel.fork(producer, q)
    diesel.fork(consumer, q, done)

def track_cpu_stats():
    pid = os.getpid()
    def append_stats():
        rawstats = subprocess.Popen(['ps -p %d -f' % pid], shell=True, stdout=subprocess.PIPE).communicate()[0]
        header, data = rawstats.split('\n', 1)
        procstats = [d for d in data.split(' ') if d]
        cpustats.append(int(procstats[3]))
    while True:
        diesel.sleep(1)
        diesel.thread(append_stats)

def main():
    diesel.fork(track_cpu_stats)
    actor_pairs = int(sys.argv[1])
    done = Countdown(actor_pairs)
    for i in xrange(actor_pairs):
        pair(done)
    start = time.time()
    done.wait()
    print "done in %.2f secs" % (time.time() - start)
    diesel.sleep(1)
    diesel.quickstop()

if __name__ == '__main__':
    diesel.set_log_level(diesel.loglevels.ERROR)
    diesel.quickstart(main)
    print cpustats

########NEW FILE########
__FILENAME__ = udp_echo
# vim:ts=4:sw=4:expandtab
'''Simple udp echo server and client.
'''
import sys
from diesel import (
    UDPService, UDPClient, call, send, datagram, quickstart, receive,
)


class EchoClient(UDPClient):
    """A UDPClient example.

    Very much like a normal Client but it can only receive datagrams
    from the wire.

    """
    @call
    def say(self, msg):
        send(msg)
        return receive(datagram)

def echo_server():
    """The UDPService callback.

    Unlike a standard Service callback that represents a connection and takes
    the remote addr as the first function, a UDPService callback takes no
    arguments. It is responsible for receiving datagrams from the wire and
    acting upon them.

    """
    while True:
        data = receive(datagram)
        send("you said %s" % data)

def echo_client():
    client = EchoClient('localhost', 8013)
    while True:
        msg = raw_input("> ")
        print client.say(msg)

if len(sys.argv) == 2:
    if 'client' in sys.argv[1]:
        quickstart(echo_client)
        raise SystemExit
    elif 'server' in sys.argv[1]:
        quickstart(UDPService(echo_server, 8013))
        raise SystemExit
print 'usage: python %s (server|client)' % sys.argv[0]

########NEW FILE########
__FILENAME__ = web
from diesel.web import DieselFlask, request

app = DieselFlask(__name__)

@app.route("/")
def hello():
    name = request.args.get('name', 'world')
    return "hello, %s!" % name

@app.route("/err")
def err():
    a = b
    return "never happens.."

if __name__ == '__main__':
    import diesel
    def t():
        while True:
            diesel.sleep(1)
            print "also looping.."
    app.diesel_app.add_loop(diesel.Loop(t))
    app.run(debug=True)

########NEW FILE########
__FILENAME__ = zeromq_echo_service
import diesel
from diesel.protocols.zeromq import (
    DieselZMQService, zmq, zctx, DieselZMQSocket,
)


NUM_CLIENTS = 100
cids = range(NUM_CLIENTS)

def echo_client():
    sock = zctx.socket(zmq.DEALER)
    sock.identity = "client:%d" % cids.pop()
    s = DieselZMQSocket(sock, connect='tcp://127.0.0.1:4321')
    for i in xrange(10):
        s.send('msg:%d' % i)
        r = s.recv()
        assert r == 'msg:%d' % i
        print sock.identity, 'received', r

class EchoService(DieselZMQService):
    def handle_client_packet(self, packet, ctx):
        return packet

echo_svc = EchoService('tcp://*:4321')
diesel.quickstart(echo_svc.run, *(echo_client for i in xrange(NUM_CLIENTS)))


########NEW FILE########
__FILENAME__ = zeromq_first
from diesel import quickstart, quickstop, sleep, first
from diesel.protocols.zeromq import DieselZMQSocket, zctx, zmq
import time

def get_messages():
    outsock = DieselZMQSocket(zctx.socket(zmq.DEALER), bind="tcp://127.0.0.1:5000")

    for x in xrange(1000):
        t, m = first(sleep=1.0, waits=[outsock])

        if t == 'sleep':
            print "sleep timeout!"
        else:
            print "zmq:", m

    quickstop()

quickstart(get_messages)

########NEW FILE########
__FILENAME__ = zeromq_receiver
from diesel import quickstart, quickstop, sleep
from diesel.protocols.zeromq import DieselZMQSocket, zctx, zmq
import time

def get_messages():
    outsock = DieselZMQSocket(zctx.socket(zmq.DEALER), bind="tcp://127.0.0.1:5000")

    t = time.time()
    for x in xrange(500000):
        msg = outsock.recv()
        assert msg == "yo dawg %s" % x
        if x % 1000 == 0:
            sleep()

    delt = time.time() - t
    print "500000 messages in %ss (%.1f/s)" % (delt, 500000.0 / delt)
    quickstop()

def tick():
    while True:
        print "Other diesel stuff"
        sleep(1)

quickstart(get_messages, tick)

########NEW FILE########
__FILENAME__ = zeromq_sender
from diesel import quickstart, quickstop, sleep
from diesel.protocols.zeromq import DieselZMQSocket, zctx, zmq
import time

def send_message():
    outsock = DieselZMQSocket(zctx.socket(zmq.DEALER), connect="tcp://127.0.0.1:5000")

    for x in xrange(500000):
        outsock.send("yo dawg %s" % x)
        if x % 1000 == 0:
            sleep()

def tick():
    while True:
        print "Other diesel stuff"
        sleep(1)

quickstart(send_message, tick)

########NEW FILE########
__FILENAME__ = zeromq_test
from diesel import quickstart, quickstop, sleep
from diesel.protocols.zeromq import DieselZMQSocket, zctx, zmq
import time

def handle_messages():
    insock = DieselZMQSocket(zctx.socket(zmq.DEALER), bind="inproc://foo")

    for x in xrange(500000):
        msg = insock.recv()
        assert msg == "yo dawg %s" % x
    delt = time.time() - t
    print "500000 messages in %ss (%.1f/s)" % (delt, 500000.0 / delt)
    quickstop()

def send_message():
    global t
    outsock = DieselZMQSocket(zctx.socket(zmq.DEALER), connect="inproc://foo")
    t = time.time()

    for x in xrange(500000):
        outsock.send("yo dawg %s" % x)
        if x % 1000 == 0:
            sleep()

def tick():
    while True:
        print "Other diesel stuff"
        sleep(1)

quickstart(handle_messages, send_message, tick)

########NEW FILE########
__FILENAME__ = test_event_ordering
import diesel

from diesel import core
from diesel.util.queue import Queue


def test_pending_events_dont_break_ordering_when_handling_early_values():

    # This test confirms that "early values" returned from a Waiter do
    # not give other pending event sources the chance to switch their
    # values into the greenlet while it context switches to give other
    # greenlets a chance to run.

    # First we setup a fake connection. It mimics a connection that does
    # not have data waiting in the buffer, and has to wait for the system
    # to call it back when data is ready on the socket. The delay argument
    # specifies how long the test should wait before simulating that data
    # is ready.

    conn1 = FakeConnection(1, delay=[None, 0.1])

    # Next we setup a Queue instance and prime it with a value, so it will
    # be ready early and return an EarlyValue.

    q = Queue()
    q.put(1)

    # Force our fake connection into the connection stack for the current
    # loop so we can make network calls (like until_eol).

    loop = core.current_loop
    loop.connection_stack.append(conn1)

    try:

        # OK, this first() call does two things.
        # 1) It calls until_eol, finds that no data is ready, and sets up a
        #    callback to be triggered when data is ready (which our
        #    FakeConnection will simulate).
        # 2) Fetches from the 'q' which will result in an EarlyValue.

        source, value = diesel.first(until_eol=True, waits=[q])
        assert source == q, source

        # What must happen is that the callback registered to handle data
        # from the FakeConnection when it arrives MUST BE CANCELED/DISCARDED/
        # FORGOTTEN/NEVER CALLED. If it gets called, it will muck with
        # internal state, and possibly switch back into the running greenlet
        # with an unexpected value, which will throw off the ordering of
        # internal state and basically break everything.

        v = diesel.until_eol()
        assert v == 'expected value 1\r\n', 'actual value == %r !!!' % (v,)

    finally:
        loop.connection_stack = []


class FakeConnection(object):
    closed = False
    waiting_callback = None

    def __init__(self, conn_id, delay=None):
        self.conn_id = conn_id
        self.delay = delay

    def check_incoming(self, condition, callback):
        diesel.fork(self.delayed_value)
        return None

    def cleanup(self):
        self.waiting_callback = None

    def delayed_value(self):
        assert self.delay, \
            "This connection requires more items in its delay list for further requests."
        delay = self.delay.pop(0)
        if delay is not None:
            print diesel.sleep(delay)
        if self.waiting_callback:
            self.waiting_callback('expected value %s\r\n' % self.conn_id)



########NEW FILE########
__FILENAME__ = test_fanout
import uuid

import diesel

from diesel.util.queue import Fanout
from diesel.util.event import Countdown

class FanoutHarness(object):
    def setup(self):
        self.done = Countdown(10)
        self.fan = Fanout()
        self.subscriber_data = {}
        for x in xrange(10):
            diesel.fork(self.subscriber)
        diesel.sleep()
        for i in xrange(10):
            self.fan.pub(i)
        self.done.wait()

    def subscriber(self):
        self.subscriber_data[uuid.uuid4()] = data = []
        with self.fan.sub() as q:
            for i in xrange(10):
                data.append(q.get())
        self.done.tick()

class TestFanout(FanoutHarness):
    def test_all_subscribers_get_the_published_messages(self):
        assert len(self.subscriber_data) == 10
        for values in self.subscriber_data.itervalues():
            assert values == range(10), values

    def test_sub_is_removed_after_it_is_done(self):
        assert not self.fan.subs


########NEW FILE########
__FILENAME__ = test_fire
from diesel import fork, fire, wait, sleep, first
from diesel.util.event import Event

def test_basic_fire():
    done = Event()
    v = [0]
    def w():
        while True:
            wait("boom!")
            v[0] += 1

    def f():
        sleep(0.05)
        fire("boom!")
        sleep(0.05)
        fire("boom!")
        done.set()

    fork(f)
    fork(w)
    ev, _ = first(sleep=1, waits=[done])
    assert v[0] == 2

def test_fire_multiple():
    done = Event()
    v = [0]
    def w():
        while True:
            wait("boom!")
            v[0] += 1

    def f():
        sleep(0.05)
        fire("boom!")
        sleep(0.05)
        fire("boom!")
        done.set()

    fork(f)
    fork(w)
    fork(w)
    ev, _ = first(sleep=1, waits=[done])
    assert v[0] == 4


def test_fire_miss():
    done = Event()
    v = [0]
    def w():
        while True:
            wait("boom!")
            v[0] += 1

    def f():
        sleep(0.05)
        fire("fizz!")
        done.set()

    fork(f)
    fork(w)
    fork(w)

    ev, _ = first(sleep=1, waits=[done])
    assert v[0] == 0 # should not have woken up!


########NEW FILE########
__FILENAME__ = test_fork
from diesel import fork, sleep, first, Loop, fork_child, ParentDiedException
from diesel.util.event import Event
from diesel import runtime

def tottering_child(v):
    v[0] += 1
    sleep(10)

def test_basic_fork():
    v = [0]
    done = Event()
    def parent():
        fork(tottering_child, v)
        sleep(0.1)
        done.set()
    runtime.current_app.add_loop(Loop(parent))
    ev, _ = first(sleep=1, waits=[done])
    if ev == 'sleep':
        assert 0, "timed out"
    assert (v[0] == 1)

def test_fork_many():
    v = [0]
    COUNT = 10000
    def parent():
        for x in xrange(COUNT):
            fork(tottering_child, v)

    runtime.current_app.add_loop(Loop(parent))

    for i in xrange(16):
        if v[0] == COUNT:
            break
        sleep(0.5) # cumulative is long enough in core 2-era
    else:
        assert 0, "didn't reach expected COUNT soon enough"


def dependent_child(got_exception):
    try:
        sleep(50)
    except ParentDiedException:
        got_exception[0] = 1
    else:
        got_exception[0] = 0

def test_fork_child_normal_death():
    got_exception = [0]
    def parent():
        fork_child(dependent_child, got_exception)
        sleep(0.1)
        # implied, I end..

    l = Loop(parent)
    runtime.current_app.add_loop(l)
    sleep() # give the Loop a chance to start
    while l.running:
        sleep()
    assert got_exception[0], "child didn't die when parent died!"


def test_fork_child_exception():
    got_exception = [0]
    def parent():
        fork_child(dependent_child, got_exception)
        sleep(0.1)
        a = b # undef

    l = Loop(parent)
    runtime.current_app.add_loop(l)
    sleep() # give the Loop a chance to start
    while l.running:
        sleep()
    assert got_exception[0], "child didn't die when parent died!"

def test_loop_keep_alive_normal_death():
    v = [0]
    def l():
        v[0] += 1

    def p():
        sleep(0.7)

    runtime.current_app.add_loop(Loop(l), keep_alive=True)
    lp = Loop(p)
    runtime.current_app.add_loop(lp)
    sleep()
    while lp.running:
        sleep()
    assert (v[0] > 1)

def test_loop_keep_alive_exception():
    v = [0]
    def l():
        v[0] += 1
        a = b # exception!

    def p():
        sleep(0.7)

    runtime.current_app.add_loop(Loop(l), keep_alive=True)
    lp = Loop(p)
    runtime.current_app.add_loop(lp)
    sleep()
    while lp.running:
        sleep()
    assert (v[0] > 1)

def flapping_child():
    sleep(0.1)

def strong_child():
    sleep(20)

def protective_parent(child, children):
    child = fork_child(child)
    child.keep_alive = True
    children[0] = child
    sleep(2)

def test_child_keep_alive_retains_parent():
    children = [None]
    parent = Loop(protective_parent, flapping_child, children)
    runtime.current_app.add_loop(parent)
    sleep()
    while parent.running:
        # Deaths of the child are interspersed here.
        assert parent.children
        assert children[0].parent is parent
        sleep()
    # The child should have died a bunch of times during the parent's life.
    assert children[0].deaths > 1, children[0].deaths

def test_child_keep_alive_dies_with_parent():
    # Starts a child that attempts to run for a long time, with a parent
    # that has a short lifetime. The rule is that children are always
    # subordinate to their parents.
    children = [None]
    parent = Loop(protective_parent, strong_child, children)
    runtime.current_app.add_loop(parent)
    sleep()
    while parent.running:
        sleep()

    # Wait here because a child could respawn after 0.5 seconds if the
    # child-always-dies-with-parent rule is being violated.
    sleep(1)

    # Once the parent is dead, the child (even thought it is keep-alive)
    # should be dead as well.
    assert not children[0].running
    assert not parent.children


########NEW FILE########
__FILENAME__ = test_os_signals
import os
import signal
import time

import diesel

from diesel.util.event import Countdown, Event, Signal


state = {'triggered':False}

def waiter():
    diesel.signal(signal.SIGUSR1)
    state['triggered'] = True

def test_can_wait_on_os_signals():
    # Start our Loop that will wait on USR1
    diesel.fork(waiter)

    # Let execution switch to the newly spawned loop
    diesel.sleep()

    # We haven't sent the signal, so the state should not be triggered
    assert not state['triggered']

    # Send the USR1 signal
    os.kill(os.getpid(), signal.SIGUSR1)

    # Again, force a switch so the waiter can act on the signal
    diesel.sleep()

    # Now that we're back, the waiter should have triggered the state
    assert state['triggered']

def test_multiple_signal_waiters():
    N_WAITERS = 5
    c = Countdown(N_WAITERS)
    def mwaiter():
        diesel.signal(signal.SIGUSR1)
        c.tick()
    for i in xrange(N_WAITERS):
        diesel.fork(mwaiter)
    diesel.sleep()
    os.kill(os.getpid(), signal.SIGUSR1)
    evt, data = diesel.first(sleep=1, waits=[c])
    assert evt is c, "all waiters were not triggered!"

def test_overwriting_custom_signal_handler_fails():
    readings = []
    success = Event()
    failure = Event()

    def append_reading(sig, frame):
        readings.append(sig)
        signal.signal(signal.SIGUSR1, signal.SIG_DFL)
    signal.signal(signal.SIGUSR1, append_reading)

    def overwriter():
        try:
            diesel.signal(signal.SIGUSR1)
        except diesel.ExistingSignalHandler:
            success.set()
        else:
            failure.set()
    diesel.fork(overwriter)
    diesel.sleep()
    os.kill(os.getpid(), signal.SIGUSR1)
    evt, _ = diesel.first(waits=[success, failure])
    assert evt is success
    assert readings

def test_signals_are_handled_while_event_loop_is_blocked():
    done = Event()

    def handler():
        diesel.signal(signal.SIGUSR1)
        done.set()

    def killer():
        time.sleep(0.1)
        os.kill(os.getpid(), signal.SIGUSR1)

    diesel.fork(handler)
    diesel.thread(killer)
    diesel.sleep()
    evt, _ = diesel.first(sleep=1, waits=[done])
    assert evt is done

def test_signal_captured_by_Signal_instance():
    usr1 = Signal(signal.SIGUSR1)
    os.kill(os.getpid(), signal.SIGUSR1)
    evt, _ = diesel.first(sleep=0.1, waits=[usr1])
    assert evt is usr1, evt

def test_Signal_instances_trigger_multiple_times():
    usr1 = Signal(signal.SIGUSR1)
    for i in xrange(5):
        os.kill(os.getpid(), signal.SIGUSR1)
        evt, _ = diesel.first(sleep=0.1, waits=[usr1])
        assert evt is usr1, evt
        usr1.rearm()


########NEW FILE########
__FILENAME__ = test_queue
import random

from collections import defaultdict

import diesel

from diesel.util.queue import Queue, QueueTimeout
from diesel.util.event import Countdown, Event


N = 500
W = 50
TIMEOUT = 1.0

class QueueHarness(object):
    def setup(self):
        self.queue = Queue()
        self.done = Countdown(N)
        self.results = []
        self.handled = defaultdict(int)
        self.populate()
        self.consume()
        self.trigger()

    def consume(self):
        def worker(myid):
            while True:
                # Test both queue.get and wait() on queue (both are valid
                # APIs for getting items from the queue). The results should
                # be the same.
                if random.random() > 0.5:
                    v = self.queue.get()
                else:
                    v = diesel.wait(self.queue)
                self.results.append(v)
                self.handled[myid] += 1
                self.done.tick()
        for i in xrange(W):
            diesel.fork(worker, i)

    def trigger(self):
        ev, val = diesel.first(sleep=TIMEOUT, waits=[self.done])
        if ev == 'sleep':
            assert 0, "timed out"

    def test_results_are_ordered_as_expected(self):
        assert self.results == range(N), self.results

    def test_results_are_balanced(self):
        for wid, count in self.handled.iteritems():
            assert count == N/W, count

class TestConsumersOnFullQueue(QueueHarness):
    def populate(self):
        for i in xrange(N):
            self.queue.put(i)

class TestConsumersOnEmptyQueue(QueueHarness):
    def populate(self):
        def go():
            diesel.wait('ready')
            for i in xrange(N):
                self.queue.put(i)
        diesel.fork(go)

    def trigger(self):
        diesel.sleep()
        diesel.fire('ready')
        super(TestConsumersOnEmptyQueue, self).trigger()

class TestQueueTimeouts(object):
    def setup(self):
        self.result = Event()
        self.queue = Queue()
        self.timeouts = 0
        diesel.fork(self.consumer, 0.01)
        diesel.fork(self.producer, 0.05)
        diesel.fork(self.consumer, 0.10)
        ev, val = diesel.first(sleep=TIMEOUT, waits=[self.result])
        if ev == 'sleep':
            assert 0, 'timed out'

    def consumer(self, timeout):
        try:
            self.queue.get(timeout=timeout)
            self.result.set()
        except QueueTimeout:
            self.timeouts += 1

    def producer(self, delay):
        diesel.sleep(delay)
        self.queue.put('test')

    def test_a_consumer_timed_out(self):
        assert self.timeouts == 1

    def test_a_consumer_got_a_value(self):
        assert self.result.is_set

########NEW FILE########
__FILENAME__ = test_sleep
from time import time
from diesel import fork, fork_child, sleep, quickstart, quickstop, ParentDiedException
from diesel.hub import Timer

def test_basic_sleep():
    delt = [None]
    STIME = 0.3
    def l():
        t = time()
        sleep(STIME)
        delt[0] = time() - t
    l_ = fork(l)
    sleep()
    while l_.running:
        sleep()
    min_bound = (STIME - Timer.ALLOWANCE)
    max_bound = (STIME + Timer.ALLOWANCE)
    assert (delt[0] > min_bound and delt[0] < max_bound), delt[0]

def test_sleep_independence():
    v = [0]
    def i():
        v[0] += 1
        sleep(0.1)
        v[0] += 1

    fork(i)
    fork(i)
    sleep(0.05)
    assert (v[0] == 2)
    sleep(0.1)
    assert (v[0] == 4)

def test_sleep_zero():
    '''Sleep w/out argument allows other loops to run
    '''

    v = [0]
    def i():
        for i in xrange(10000):
            v[0] += 1
            sleep()

    fork(i)

    sleep(0.05)
    cur = v[0]
    sleep() # allow i to get scheduled
    now = v[0]
    assert (now == cur + 1)

########NEW FILE########
__FILENAME__ = test_mongodb
import uuid

import diesel
from diesel.protocols.mongodb import *

from diesel.util.queue import Fanout

class MongoDbHarness(object):
    def setup(self):
        self.client = MongoClient()
        self.client.drop_database('dieseltest')
        self.db = self.client.dieseltest

    def filt(self, d):
        del d['_id']
        return d

class TestMongoDB(MongoDbHarness):
    def test_empty(self):
        assert self.db.cempty.find().all() == []
        assert self.db.cempty.find().one() == None

    # INSERT
    def test_insert(self):
        d = {'one' : 'two'}
        assert self.db.ionly.insert({'one' : 'two'})['err'] == None

    def test_insert_many(self):
        d1 = {'one' : 'two'}
        d2 = {'three' : 'four'}
        inp = [d1, d2]
        inp.sort()
        assert self.db.imult.insert(inp)['err'] == None
        all = self.db.imult.find().all()
        map(self.filt, all)
        all.sort()
        assert all == inp

    # UPDATE
    def test_update_basic(self):
        d = {'one' : 'two', 'three' : 'four'}
        assert self.db.up1.insert(d)['err'] == None
        assert self.filt(self.db.up1.find().one()) == d
        assert self.db.up1.update({'one' : 'two'},
                {'three' : 'five'})['err'] == None
        new = self.filt(self.db.up1.find().one())
        assert 'one' not in new
        assert new['three'] == 'five'

    def test_update_set(self):
        d = {'one' : 'two', 'three' : 'four'}
        assert self.db.up2.insert(d)['err'] == None
        assert self.filt(self.db.up2.find().one()) == d
        assert self.db.up2.update({'one' : 'two'},
                {'$set' : {'three' : 'five'}})['err'] == None
        new = self.filt(self.db.up2.find().one())
        assert new['one'] == 'two'
        assert new['three'] == 'five'

    def test_update_not_multi(self):
        d = {'one' : 'two', 'three' : 'four'}
        assert self.db.up3.insert(d)['err'] == None
        assert self.db.up3.insert(d)['err'] == None
        assert self.db.up3.update({'one' : 'two'},
                {'$set' : {'three' : 'five'}})['err'] == None

        threes = set()
        for r in self.db.up3.find():
            threes.add(r['three'])
        assert threes == set(['four', 'five'])

    def test_update_multi(self):
        d = {'one' : 'two', 'three' : 'four'}
        assert self.db.up4.insert(d)['err'] == None
        assert self.db.up4.insert(d)['err'] == None
        assert self.db.up4.update({'one' : 'two'},
                {'$set' : {'three' : 'five'}},
                multi=True)['err'] == None

        threes = set()
        for r in self.db.up4.find():
            threes.add(r['three'])
        assert threes == set(['five'])

    def test_update_miss(self):
        d = {'one' : 'two', 'three' : 'four'}
        assert self.db.up5.insert(d)['err'] == None
        snap = self.db.up5.find().all()
        assert self.db.up5.update({'one' : 'nottwo'},
                {'$set' : {'three' : 'five'}},
                multi=True)['err'] == None

        assert snap == self.db.up5.find().all()

    def test_update_all(self):
        d = {'one' : 'two', 'three' : 'four'}
        assert self.db.up6.insert(d)['err'] == None
        assert self.db.up6.insert(d)['err'] == None
        assert self.db.up6.update({},
                {'$set' : {'three' : 'five'}},
                multi=True)['err'] == None

        for r in self.db.up6.find().all():
            assert r['three'] == 'five'

    def test_update_upsert(self):
        d = {'one' : 'two', 'three' : 'four'}
        assert self.db.up7.insert(d)['err'] == None
        assert self.db.up7.insert(d)['err'] == None
        assert len(self.db.up7.find().all()) == 2
        assert self.db.up7.update({'not' : 'there'},
                {'this is' : 'good'}, upsert=True)['err'] == None

        assert len(self.db.up7.find().all()) == 3

    # DELETE
    def test_delete_miss(self):
        d = {'one' : 'two'}
        assert self.db.del1.insert({'one' : 'two'})['err'] == None
        assert len(self.db.del1.find().all()) == 1
        assert self.db.del1.delete({'not' : 'me'})['err'] == None
        assert len(self.db.del1.find().all()) == 1

    def test_delete_target(self):
        d = {'one' : 'two'}
        assert self.db.del2.insert({'one' : 'two'})['err'] == None
        assert self.db.del2.insert({'three' : 'four'})['err'] == None
        assert len(self.db.del2.find().all()) == 2
        assert self.db.del2.delete({'one' : 'two'})['err'] == None
        assert len(self.db.del2.find().all()) == 1

    def test_delete_all(self):
        d = {'one' : 'two'}
        assert self.db.del3.insert({'one' : 'two'})['err'] == None
        assert self.db.del3.insert({'three' : 'four'})['err'] == None
        assert len(self.db.del3.find().all()) == 2
        assert self.db.del3.delete({})['err'] == None
        assert len(self.db.del3.find().all()) == 0

    # QUERY
    def test_query_basic(self):
        d = {'one' : 'two'}
        assert self.db.onerec.insert(d)['err'] == None
        assert map(self.filt, self.db.onerec.find().all()) == [d]
        assert self.filt(self.db.onerec.find().one()) == d

        x = 0
        for r in self.db.onerec.find():
            assert self.filt(r) == d
            x += 1
        assert x == 1

    def test_query_one(self):
        d1 = {'one' : 'two'}
        d2 = {'three' : 'four'}
        inp = [d1, d2]
        assert self.db.q0.insert(inp)['err'] == None
        assert len(self.db.q0.find().all()) == 2
        assert len(self.db.q0.find({'one' : 'two'}).all()) == 1

    def test_query_miss(self):
        d = {'one' : 'two'}
        assert self.db.q1.insert(d)['err'] == None
        assert self.db.q1.find({'one' : 'nope'}).all() == []

    def test_query_subfields(self):
        d = {'one' : 'two', 'three' : 'four'}
        assert self.db.q2.insert(d)['err'] == None
        assert map(self.filt,
                self.db.q2.find({'one' : 'two'}, ['three']).all()) \
                == [{'three' : 'four'}]

    def test_deterministic_order_when_static(self):
        for x in xrange(500):
            self.db.q3.insert({'x' : x})

        snap = self.db.q3.find().all()

        for x in xrange(100):
            assert snap == self.db.q3.find().all()

    def test_skip(self):
        for x in xrange(500):
            self.db.q4.insert({'x' : x})

        snap = self.db.q4.find().all()

        with_skip = self.db.q4.find(skip=250).all()

        assert snap[250:] == with_skip

    def test_limit(self):
        for x in xrange(500):
            self.db.q5.insert({'x' : x})

        snap = self.db.q5.find().all()

        with_skip = self.db.q5.find(limit=150).all()

        assert snap[:150] == with_skip

    def test_skip_limit(self):
        for x in xrange(500):
            self.db.q6.insert({'x' : x})

        snap = self.db.q6.find().all()

        with_skip = self.db.q6.find(skip=300, limit=150).all()

        assert snap[300:300+150] == with_skip

    # CURSOR PROPERTIES
    def test_cursor_count(self):
        for x in xrange(500):
            self.db.c1.insert({'x' : x})

        c = self.db.c1.find()
        assert c.count() == 500
        assert len(c.all()) == 500

        c = self.db.c1.find(skip=100, limit=150)
        assert c.count() == 150
        assert len(c.all()) == 150

    def test_cursor_sort(self):
        for x in xrange(500):
            self.db.c2.insert({'x' : x})

        snap = self.db.c2.find().sort('x', 1).all()

        print snap
        assert map(lambda d: d['x'], snap) == range(500)

        snap = self.db.c2.find().sort('x', -1).all()
        assert map(lambda d: d['x'], snap) == range(499, -1, -1)

########NEW FILE########
__FILENAME__ = test_redis
import diesel
from diesel.protocols.redis import *

class RedisHarness(object):
    def setup(self):
        self.client = RedisClient()
        self.client.select(11)
        self.client.flushdb()

class TestRedis(RedisHarness):
    def test_basic(self):
        r = self.client
        assert r.get('newdb') == None
        r.set('newdb', '1')

        r.set('foo3', 'bar')
        assert r.exists('foo3')
        r.delete('foo3')
        assert not r.exists('foo3')

        for x in xrange(5000):
            r.set('foo', 'bar')

        assert r.get('foo') == 'bar'
        assert r.get('foo2') == None

        assert r.exists('foo') == True
        assert r.exists('foo2') == False

        assert r.type('foo') == 'string'
        assert r.type('foo2') == 'none'
        assert r.keys('fo*') == set(['foo'])
        assert r.keys('bo*') == set()

        assert r.randomkey()

        r.rename('foo', 'bar')
        assert r.get('foo') == None
        assert r.get('bar') == 'bar'

        r.rename('bar', 'foo')
        assert r.get('foo') == 'bar'
        assert r.get('bar') == None
        assert r.dbsize()

        assert r.ttl('foo') == None

        r.setex("gonesoon", 3, "whatever")
        assert 0 < r.ttl("gonesoon") <= 3.0

        r.set("phrase", "to be or ")
        r.append("phrase", "not to be")
        assert r.get("phrase") == "to be or not to be"
        assert r.substr('phrase', 3, 11) == 'be or not'

        r.set("one", "two")
        assert r.mget(["one", "foo"]) == ['two', 'bar']
        r.mset({"one" : "three", "foo":  "four"})
        assert r.mget(["one", "foo"]) == ['three', 'four']

    def test_incr(self):
        r = self.client
        assert r.incr("counter") == 1
        assert r.get('counter') == '1'
        assert r.incr("counter") == 2
        assert r.get('counter') == '2'
        assert r.incrby("counter", 2) == 4
        assert r.get('counter') == '4'

    def test_decr(self):
        r = self.client
        r.set('counter', '4')
        assert r.decr("counter") == 3
        assert r.decr("counter") == 2
        assert r.decrby("counter", 2) == 0

    def test_lists(self):
        r = self.client
        r.rpush("ml", 5)
        r.lpush("ml", 1)
        assert r.lrange("ml", 0, 500) == ['1', '5']
        assert r.llen("ml") == 2

        r.ltrim("ml", 1, 3)

        assert r.lrange("ml", 0, 500) == ['5']

        r.lset("ml", 0, 'nifty!')
        assert r.lrange("ml", 0, 500) == ['nifty!']
        assert r.lindex("ml", 0) == 'nifty!'

        r.lrem("ml", 'nifty!')

        assert r.lrange("ml", 0, 500) == []

        r.rpush("ml", 'yes!')
        r.rpush("ml", 'no!')
        assert r.lrange("ml", 0, 500) == ["yes!", "no!"]

        assert r.lpop("ml") == 'yes!'
        assert r.rpop("ml") == 'no!'

        t = time.time()
        r.blpop(['ml'], 3)
        delt = time.time() - t
        assert 2.5 < delt < 10

        r.rpush("ml", 'yes!')
        r.rpush("ml", 'no!')
        assert r.blpop(['ml'], 3) == ('ml', 'yes!')
        assert r.blpop(['ml'], 3) == ('ml', 'no!')

        r.rpush("ml", 'yes!')
        r.rpush("ml", 'no!')
        r.rpush("ml2", 'one!')
        r.rpush("ml2", 'two!')

        r.rpoplpush("ml", "ml2")
        assert r.lrange("ml", 0, 500) == ['yes!']
        assert r.lrange("ml2", 0, 500) == ['no!', 'one!', 'two!']

    def test_sets(self):
        r = self.client
        r.sadd("s1", "one")
        r.sadd("s1", "two")
        r.sadd("s1", "three")

        assert r.smembers("s1") == set(["one", "two", "three"])

        r.srem("s1", "three")

        assert r.smembers("s1") == set(["one", "two"])

        r.smove("s1", "s2", "one")
        assert r.spop("s2") == 'one'
        assert r.scard("s1") == 1

        assert r.sismember("s1", "two") == True
        assert r.sismember("s1", "one") == False

        r.sadd("s1", "four")
        r.sadd("s2", "four")

        assert r.sinter(["s1", "s2"]) == set(['four'])
        r.sinterstore("s3", ["s1", "s2"])
        assert r.smembers('s3') == r.sinter(["s1", "s2"])
        assert r.sunion(["s1", "s2"]) == set(['two', 'four'])
        r.sunionstore("s3", ["s1", "s2"])
        assert r.smembers('s3') == r.sunion(["s1", "s2"])

        assert r.srandmember("s3") in r.smembers("s3")

    def test_zsets(self):
        r = self.client
        r.zadd("z1", 10, "ten")
        r.zadd("z1", 1, "one")
        r.zadd("z1", 2, "two")
        r.zadd("z1", 0, "zero")


        assert r.zrange("z1", 0, -1) == ['zero', 'one', 'two', 'ten']
        r.zrem("z1", "two")
        assert r.zrange("z1", 0, -1) == ['zero', 'one', 'ten']
        assert r.zrevrange("z1", 0, -1) == list(reversed(r.zrange("z1", 0, -1)))

        r.zrem("z1", (r.zrange("z1", 0, 0))[0]) # remove 'zero'?
        assert r.zrange("z1", 0, -1) == ['one', 'ten']
        assert r.zcard("z1") == 2

        assert r.zscore("z1", "one") == 1.0

        r.zincrby("z1", -2, "one")

        assert r.zscore("z1", "one") == -1.0

        r.zadd("z1", 2, "two")
        r.zadd("z1", 3, "three")
        assert r.zrangebyscore("z1", -5, 15) == ['one', 'two', 'three', 'ten']
        assert r.zrangebyscore("z1", 2, 15) == ['two', 'three', 'ten']
        assert r.zrangebyscore("z1", 2, 15, 1, 50) == ['three', 'ten']
        assert r.zrangebyscore("z1", 2, 15, 1, 1) == ['three']
        assert r.zrangebyscore("z1", 2, 15, 1, 50, with_scores=True) == [('three', 3.0), ('ten', 10.0)]

        assert r.zcount("z1", 2, 15) == 3

        assert r.zremrangebyrank('z1', 1, 1)
        assert r.zrangebyscore("z1", -5, 15) == ['one', 'three', 'ten']
        assert r.zremrangebyscore('z1', 2, 4)
        assert r.zrangebyscore("z1", -5, 15) == ['one', 'ten']

    def test_hashes(self):
        r = self.client
        r.hset("h1", "bahbah", "black sheep")
        assert r.hget("h1", "bahbah") == "black sheep"

        r.hmset("h1", {"foo" : "bar", "baz" : "bosh"})
        assert r.hmget("h1", ["foo", "bahbah", "baz"]) == {'foo' : 'bar', 'baz' : 'bosh', 'bahbah' : 'black sheep'}

        assert r.hincrby("h1", "count", 3) == 3
        assert r.hincrby("h1", "count", 4) == 7

        assert r.hmget("h1", ["foo", "count"]) == {'foo' : 'bar', 'count' : '7'}

        assert r.hexists("h1", "bahbah") == True
        assert r.hexists("h1", "nope") == False

        r.hdel("h1", "bahbah")
        assert r.hexists("h1", "bahbah") == False
        assert r.hlen("h1") == 3

        assert r.hkeys("h1") == set(['foo', 'baz', 'count'])
        assert set(r.hvals("h1")) == set(['bar', 'bosh', '7'])
        assert r.hgetall("h1") == {'foo' : 'bar', 'baz' : 'bosh', 'count' : '7'}

    def test_transactions(self):
        r = self.client
        r.set('t2', 1)
        # Try a successful transaction.
        with r.transaction() as t:
            t.incr('t1')
            t.incr('t2')
        assert r.get('t1') == '1'
        assert r.get('t2') == '2'

        # Try a failing transaction.
        try:
            with r.transaction() as t:
                t.incr('t1')
                t.icnr('t2') # typo!
        except AttributeError:
            # t1 should not get incremented since the transaction body
            # raised an exception.
            assert r.get('t1') == '1'
            assert t.aborted
        else:
            assert 0, "DID NOT RAISE"

        # Try watching keys in a transaction.
        r.set('w1', 'watch me')
        transaction = r.transaction(watch=['w1'])
        w1 = r.get('w1')
        with transaction:
            transaction.set('w2', w1 + ' if you can!')
        assert transaction.value == ['OK']
        assert r.get('w2') == 'watch me if you can!'

        # Try changing watched keys.
        r.set('w1', 'watch me')
        transaction = r.transaction(watch=['w1'])
        r.set('w1', 'changed!')
        w1 = r.get('w1')
        try:
            with transaction:
                transaction.set('w2', w1 + ' if you can!')
        except RedisTransactionError:
            assert transaction.aborted
        else:
            assert 0, "DID NOT RAISE"

########NEW FILE########
__FILENAME__ = test_zmq_service
import time

import diesel

from collections import namedtuple
from diesel.protocols.zeromq import DieselZMQService


# Test Cases
# ==========

def test_incoming_message_loop_is_kept_alive():
    def stop_after_10_sends(sock):
        if sock.send_calls == 10:
            raise StopIteration

    svc = MisbehavingService('something', max_ticks=10)
    loop = diesel.fork(svc.run)
    diesel.sleep()
    start = time.time()
    maxtime = 0.5
    while loop.running and time.time() - start < maxtime:
        diesel.sleep(0.1)
    if loop.running:
        loop.reschedule_with_this_value(diesel.TerminateLoop())
        diesel.sleep()
        assert not loop.running
    assert svc.zmq_socket.exceptions > 1, svc.zmq_socket.exceptions


# Stubs and Utilities For the Tests Above
# =======================================

envelope = namedtuple('envelope', ['more', 'bytes'])
body = namedtuple

class MisbehavingSocket(object):
    """Stub for DieselZMQSocket."""
    def __init__(self):
        self.recv_calls = 0
        self.send_calls = 0
        self.exceptions = 0

    def recv(self, copy=True):
        # raises an Exception every 5 calls
        self.recv_calls += 1
        if (self.recv_calls % 5) == 0:
            self.exceptions += 1
            raise Exception("aaaahhhhh")
        if not copy:
            return envelope(more=True, bytes="foobarbaz")
        return "this is the data you are looking for"

    def send(self, *args):
        self.send_calls += 1

class MisbehavingService(DieselZMQService):
    """A DieselZMQService with a MisbehavingSocket.

    It also stops running after a number of iterations (controlled via a
    `max_ticks` keyword argument).

    """
    def __init__(self, *args, **kw):
        self._test_ticks = 0
        self._max_ticks = kw.pop('max_ticks')
        super(MisbehavingService, self).__init__(*args, **kw)

    def _create_zeromq_server_socket(self):
        self.zmq_socket = MisbehavingSocket()

    @property
    def should_run(self):
        if self._test_ticks >= self._max_ticks:
            return False
        self._test_ticks += 1
        return True


########NEW FILE########
__FILENAME__ = test_buffer
from diesel.buffer import Buffer

def test_feed():
    b = Buffer()
    assert b.feed("rock") == None
    assert b.feed("rockandroll") == None

def test_read_bytes():
    b = Buffer()
    b.set_term(10)
    assert b.feed("rock") == None
    assert b.feed("rockandroll") == "rockrockan"
    # buffer left.. droll
    assert b.check() == None
    b.set_term(10)
    assert b.check() == None
    assert b.feed("r") == None
    assert b.feed("r") == None
    assert b.feed("r") == None
    assert b.feed("r") == None
    assert b.feed("r") == "drollrrrrr"
    assert b.feed("x" * 10000) == None # no term (re-)established

def test_read_sentinel():
    b = Buffer()
    assert b.feed("rock and") == None
    b.set_term("\r\n")
    assert b.feed(" roll\r") == None
    assert b.feed("\nrock ") == "rock and roll\r\n"
    assert b.feed("and roll 2\r\n") == None
    b.set_term("\r\n")
    assert b.check() == "rock and roll 2\r\n"

def test_read_hybrid():
    b = Buffer()
    assert b.feed("rock and") == None
    b.set_term("\r\n")
    assert b.feed(" roll\r") == None
    assert b.feed("\n012345678") == "rock and roll\r\n"
    b.set_term(16)
    assert b.check() == None
    assert b.feed("9abcdefgh") == "0123456789abcdef"


########NEW FILE########
__FILENAME__ = test_pipeline
#12345678
# That comment above matters (used in the test!)
from diesel.pipeline import Pipeline, PipelineClosed, PipelineCloseRequest
from cStringIO import StringIO

FILE = __file__
if FILE.endswith('.pyc') or FILE.endswith('.pyo'):
    FILE = FILE[:-1]

def test_add_string():
    p = Pipeline()
    assert (p.add("foo") == None)
    assert (not p.empty)

def test_add_file():
    p = Pipeline()
    assert (p.add(open(FILE)) == None)
    assert (not p.empty)

def test_add_filelike():
    p = Pipeline()
    sio = StringIO()
    assert (p.add(sio) == None)
    assert (not p.empty)

def test_add_badtypes():
    p = Pipeline()
    class Whatever(object): pass
    for item in [3, [], Whatever()]:
        try:
            p.add(item)
        except ValueError:
            pass
    assert (p.empty)


def test_read_empty():
    p = Pipeline()
    assert (p.read(500) == '')

def test_read_string():
    p = Pipeline()
    p.add("foo")
    assert (p.read(3) == "foo")
    assert (p.empty)

def test_read_file():
    p = Pipeline()
    p.add(open(FILE))
    assert (p.read(5) == "#1234")

def test_read_filelike():
    p = Pipeline()
    p.add(StringIO('abcdef'))
    assert (p.read(5) == 'abcde')

def test_read_twice():
    p = Pipeline()
    p.add("foo")
    assert (p.read(2) == "fo")
    assert (p.read(2) == "o")

def test_read_twice_empty():
    p = Pipeline()
    p.add("foo")
    assert (p.read(2) == "fo")
    assert (p.read(2) == "o")
    assert (p.read(2) == "")

def test_read_backup():
    p = Pipeline()
    p.add("foo")
    assert (p.read(2) == "fo")
    p.backup("fo")
    assert (p.read(2) == "fo")
    assert (p.read(2) == "o")

def test_read_backup_extra():
    p = Pipeline()
    p.add("foo")
    assert (p.read(2) == "fo")
    p.backup("foobar")
    assert (p.read(500) == "foobaro")

def test_read_hybrid_objects():
    p = Pipeline()
    p.add("foo,")
    p.add(StringIO("bar,"))
    p.add(open(FILE))

    assert (p.read(10) == "foo,bar,#1")
    assert (p.read(4) == "2345")
    p.backup("rock") # in the middle of the "file"
    assert (p.read(6) == "rock67")

def test_close():
    p = Pipeline()
    p.add("foo")
    p.add(StringIO("bar"))
    p.close_request()
    assert (p.read(1000) == "foobar")
    try:
        p.read(1000)
    except PipelineCloseRequest:
        pass

def test_long_1():
    p = Pipeline()
    p.add("foo")
    assert (p.read(2) == "fo")
    p.add("bar")
    assert (p.read(3) == "oba")
    p.backup("rocko")
    p.add(StringIO("soma"))
    assert (p.read(1000) == "rockorsoma")
    assert (p.read(1000) == "")
    assert (p.empty)
    p.add("X" * 10000)
    p.close_request()
    assert (p.read(5000) == 'X' * 5000)
    p.backup('XXX')
    try:
        p.add("newstuff")
    except PipelineClosed:
        pass
    assert (not p.empty)
    assert (p.read(100000) == 'X' * 5003)
    assert (not p.empty)
    try:
        p.read(1000)
    except PipelineCloseRequest:
        pass
    assert (not p.empty)
    try:
        p.read(1000)
    except PipelineCloseRequest:
        pass

def test_pri_clean():
    p = Pipeline()
    p.add("two")
    p.add("three")
    p.add("one")
    assert (p.read(18) == "twothreeone")

    p.add("two", 2)
    p.add("three", 3)
    p.add("six", 2)
    p.add("one", 1)
    assert (p.read(18) == "threetwosixone")

########NEW FILE########
__FILENAME__ = test_waiters
from diesel.events import (
    Waiter, WaitPool, EarlyValue, StringWaiter,
)


class EarlyReadyWaiter(Waiter):
    def ready_early(self):
        return True

    def process_fire(self, value):
        return "foo"

class Who(object):
    """Someone who is waiting ..."""
    pass

class TestStringWaiters(object):
    def test_string_waiters_for_the_same_string_have_the_same_wait_id(self):
        s1 = StringWaiter("asdf")
        s2 = StringWaiter("asdf")
        assert s1.wait_id == s2.wait_id

    def test_string_waiters_for_different_strings_have_different_wait_ids(self):
        s1 = StringWaiter("asdf")
        s2 = StringWaiter("jkl;")
        assert s1.wait_id != s2.wait_id

class TestWaitPoolWithEarlyReturn(object):
    def setup(self):
        self.pool = WaitPool()
        self.who = Who()
        self.waiter = EarlyReadyWaiter()
        self.result = self.pool.wait(self.who, self.waiter)

    def test_results_is_EarlyValue(self):
        assert isinstance(self.result, EarlyValue)
        assert self.result.val == "foo"

    def test_waiter_wait_id_not_added_to_wait_pool(self):
        assert self.waiter.wait_id not in self.pool.waits

    def test_who_not_added_to_wait_pool(self):
        assert self.who not in self.pool.loop_refs

class TestWaitPoolWithStringWaiter(object):
    def setup(self):
        self.pool = WaitPool()
        self.who = Who()
        self.wait_for = "a string"
        self.result = self.pool.wait(self.who, self.wait_for)

    def test_the_waiting_entity_is_added_to_wait_pool(self):
        assert self.pool.waits[self.wait_for]
        w = self.pool.waits[self.wait_for].pop()
        assert w is self.who

    def test_StringWaiter_added_to_wait_pool(self):
        v = self.pool.loop_refs[self.who].pop()
        assert isinstance(v, StringWaiter)

    def test_result_is_wait_id(self):
        assert self.result == self.wait_for

########NEW FILE########
