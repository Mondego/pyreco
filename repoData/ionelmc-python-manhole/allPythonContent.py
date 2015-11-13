__FILENAME__ = confenvs
from itertools import product, chain
from jinja2 import FileSystemLoader
from jinja2 import Environment
jinja = Environment(loader=FileSystemLoader('.'), trim_blocks=True, lstrip_blocks=True)

pythons = ['2.7', '2.6', '3.2', '3.3', '3.4', 'pypy']
deps = ['python-signalfd', 'python-signalfd gevent', 'python-signalfd eventlet', 'eventlet', 'gevent', '']
covers = [True, False]
envs = ['PATCH_THREAD=yes', '']
skips = list(chain(
    # disable py3/pypy with eventlet/gevent
    product(['3.2', '3.3', '3.4', 'pypy'], [dep for dep in deps if 'eventlet' in dep or 'gevent' in dep], covers, envs),
    product(pythons, [dep for dep in deps if not ('eventlet' in dep or 'gevent' in dep)], covers, envs[:1]),
))
tox = {}
for python, dep, cover, env in product(pythons, deps, covers, envs):
    if (python, dep, cover, env) not in skips:
        tox['-'.join(filter(None, (
            python,
            '-'.join(dep.replace('python-', '').split()),
            '' if cover else 'nocover',
            env and env.lower().replace('_', '').rstrip('=yes'),
        )))] = {
            'python': 'python' + python if 'py' not in python else python,
            'deps': dep.split(),
            'cover': cover,
            'env': env,
        }

open('tox.ini', 'w').write(jinja.get_template('tox.tmpl.ini').render(envs=tox))
open('.travis.yml', 'w').write(jinja.get_template('.travis.tmpl.yml').render(envs=tox))

########NEW FILE########
__FILENAME__ = manhole
from __future__ import print_function
from logging import getLogger
logger = getLogger(__name__)

import traceback
import socket
import struct
import sys
import os
import atexit
import code
import signal
import errno
import platform

try:
    import signalfd
except ImportError:
    signalfd = None
try:
    string = basestring
except NameError:  # python 3
    string = str
try:
    InterruptedError = InterruptedError
except NameError:  # python <= 3.2
    InterruptedError = OSError
if hasattr(sys, 'setswitchinterval'):
    setinterval = sys.setswitchinterval
    getinterval = sys.getswitchinterval
else:
    setinterval = sys.setcheckinterval
    getinterval = sys.getcheckinterval


def _get_original(qual_name):
    mod, name = qual_name.split('.')
    original = getattr(__import__(mod), name)

    try:
        from gevent.monkey import get_original
        original = get_original(mod, name)
    except (ImportError, SyntaxError):
        pass

    try:
        from eventlet.patcher import original
        original = getattr(original(mod), name)
    except (ImportError, SyntaxError):
        pass

    return original
_ORIGINAL_SOCKET = _get_original('socket.socket')
_ORIGINAL_FDOPEN = _get_original('os.fdopen')
try:
    _ORIGINAL_ALLOCATE_LOCK = _get_original('thread.allocate_lock')
except ImportError:  # python 3
    _ORIGINAL_ALLOCATE_LOCK = _get_original('_thread.allocate_lock')
_ORIGINAL_THREAD = _get_original('threading.Thread')
_ORIGINAL_EVENT = _get_original('threading.Event')
_ORIGINAL__ACTIVE = _get_original('threading._active')

PY3 = sys.version_info[0] == 3
PY26 = sys.version_info[:2] == (2, 6)
VERBOSE = True
START_TIMEOUT = None

try:
    import ctypes
    import ctypes.util
    libpthread_path = ctypes.util.find_library("pthread")
    if not libpthread_path:
        raise ImportError
    libpthread = ctypes.CDLL(libpthread_path)
    if not hasattr(libpthread, "pthread_setname_np"):
        raise ImportError
    _pthread_setname_np = libpthread.pthread_setname_np
    _pthread_setname_np.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    _pthread_setname_np.restype = ctypes.c_int
    pthread_setname_np = lambda ident, name: _pthread_setname_np(ident, name[:15].encode('utf8'))
except ImportError:
    pthread_setname_np = lambda ident, name: None

# OS X getsockopt(2) defines (may work for BSD too?)
SOL_LOCAL = 0
LOCAL_PEERCRED = 1

SO_PEERCRED = 17


def cry(message):
    """
    Fail-ignorant logging function.
    """
    if VERBOSE:
        try:
            _STDERR.write("Manhole: %s\n" % message)
        except:  # pylint: disable=W0702
            pass


def get_peercred(sock):
    """Gets the (pid, uid, gid) for the client on the given *connected* socket."""

    if platform.system() == 'Darwin':
        return struct.unpack('3i', sock.getsockopt(
            SOL_LOCAL, LOCAL_PEERCRED, struct.calcsize('3i')
        ))
    else:
        return struct.unpack('3i', sock.getsockopt(
            socket.SOL_SOCKET, SO_PEERCRED, struct.calcsize('3i')
        ))


class SuspiciousClient(Exception):
    pass


class Manhole(_ORIGINAL_THREAD):
    """
    Thread that runs the infamous "Manhole".
    """

    def __init__(self, sigmask, start_timeout):
        super(Manhole, self).__init__()
        self.daemon = True
        self.name = "Manhole"
        self.sigmask = sigmask
        self.serious = _ORIGINAL_EVENT()
        self.start_timeout = start_timeout  # time to wait for the manhole to get serious (to have a complete start)
                                            # see: http://emptysqua.re/blog/dawn-of-the-thread/

    def start(self):
        super(Manhole, self).start()
        if not self.serious.wait(self.start_timeout) and not PY26:
            cry("WARNING: Waited %s seconds but Manhole thread didn't start yet :(" % self.start_timeout)

    @staticmethod
    def get_socket():
        sock = _ORIGINAL_SOCKET(socket.AF_UNIX, socket.SOCK_STREAM)
        pid = os.getpid()
        name = "/tmp/manhole-%s" % pid
        if os.path.exists(name):
            os.unlink(name)
        sock.bind(name)
        sock.listen(5)
        cry("Manhole UDS path: "+name)
        return sock, pid

    def run(self):
        self.serious.set()
        if signalfd and self.sigmask:
            signalfd.sigprocmask(signalfd.SIG_BLOCK, self.sigmask)
        pthread_setname_np(self.ident, self.name)

        sock, pid = self.get_socket()
        while True:
            cry("Waiting for new connection (in pid:%s) ..." % pid)
            try:
                client = ManholeConnection(sock.accept()[0], self.sigmask)
                client.start()
                client.join()
            except (InterruptedError, socket.error) as e:
                if e.errno != errno.EINTR:
                    raise
                continue
            finally:
                client = None


class ManholeConnection(_ORIGINAL_THREAD):
    def __init__(self, client, sigmask):
        super(ManholeConnection, self).__init__()
        self.daemon = False
        self.client = client
        self.name = "ManholeConnection"
        self.sigmask = sigmask

    def run(self):
        cry('Started ManholeConnection thread. Checking credentials ...')
        if signalfd and self.sigmask:
            signalfd.sigprocmask(signalfd.SIG_BLOCK, self.sigmask)
        pthread_setname_np(self.ident, "Manhole ----")

        pid, _, _ = self.check_credentials(self.client)
        pthread_setname_np(self.ident, "Manhole %s" % pid)
        self.handle(self.client)

    @staticmethod
    def check_credentials(client):
        pid, uid, gid = get_peercred(client)

        euid = os.geteuid()
        client_name = "PID:%s UID:%s GID:%s" % (pid, uid, gid)
        if uid not in (0, euid):
            raise SuspiciousClient("Can't accept client with %s. It doesn't match the current EUID:%s or ROOT." % (
                client_name, euid
            ))

        cry("Accepted connection %s from %s" % (client, client_name))
        return pid, uid, gid

    @staticmethod
    def handle(client):
        client.settimeout(None)

        # disable this till we have evidence that it's needed
        #client.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 0)
        # Note: setting SO_RCVBUF on UDS has no effect, see: http://man7.org/linux/man-pages/man7/unix.7.html

        backup = []
        old_interval = getinterval()
        try:
            try:
                client_fd = client.fileno()
                for mode, names in (
                    ('w', (
                        'stderr',
                        'stdout',
                        '__stderr__',
                        '__stdout__'
                    )),
                    ('r', (
                        'stdin',
                        '__stdin__'
                    ))
                ):
                    for name in names:
                        backup.append((name, getattr(sys, name)))
                        setattr(sys, name, _ORIGINAL_FDOPEN(client_fd, mode, 1 if PY3 else 0))
                run_repl()
                cry("DONE.")
            finally:
                try:
                    setinterval(2147483647)  # change the switch/check interval to something ridiculous
                                             # we don't want to have other thread try to write to the
                                             # redirected sys.__std*/sys.std* - it would fail horribly
                    client.close()  # close before it's too late. it may already be dead
                    junk = []  # keep the old file objects alive for a bit
                    for name, fh in backup:
                        junk.append(getattr(sys, name))
                        setattr(sys, name, fh)
                    del backup
                    for fh in junk:
                        try:
                            fh.close()
                        except IOError:
                            pass
                        del fh
                    del junk
                finally:
                    setinterval(old_interval)
                    cry("Cleaned up.")
        except Exception:
            cry("ManholeConnection thread failed:")
            cry(traceback.format_exc())


def run_repl():
    dump_stacktraces()
    code.InteractiveConsole({
        'dump_stacktraces': dump_stacktraces,
        'sys': sys,
        'os': os,
        'socket': socket,
        'traceback': traceback,
    }).interact()


def _handle_oneshot(_signum, _frame):
    try:
        sock, pid = Manhole.get_socket()
        cry("Waiting for new connection (in pid:%s) ..." % pid)
        client, _ = sock.accept()
        ManholeConnection.check_credentials(client)
        ManholeConnection.handle(client)
    except:  # pylint: disable=W0702
        # we don't want to let any exception out, it might make the application missbehave
        cry("Manhole oneshot connection failed:")
        cry(traceback.format_exc())
    finally:
        _remove_manhole_uds()


def _remove_manhole_uds():
    name = "/tmp/manhole-%s" % os.getpid()
    if os.path.exists(name):
        os.unlink(name)

_INST_LOCK = _ORIGINAL_ALLOCATE_LOCK()
_STDERR = _INST = _ORIGINAL_OS_FORK = _ORIGINAL_OS_FORKPTY = _SHOULD_RESTART = None


def _patched_fork():
    """Fork a child process."""
    pid = _ORIGINAL_OS_FORK()
    if not pid:
        cry('Fork detected. Reinstalling Manhole.')
        reinstall()
    return pid


def _patched_forkpty():
    """Fork a new process with a new pseudo-terminal as controlling tty."""
    pid, master_fd = _ORIGINAL_OS_FORKPTY()
    if not pid:
        cry('Fork detected. Reinstalling Manhole.')
        reinstall()
    return pid, master_fd


def _patch_os_fork_functions():
    global _ORIGINAL_OS_FORK, _ORIGINAL_OS_FORKPTY  # pylint: disable=W0603
    if not _ORIGINAL_OS_FORK:
        _ORIGINAL_OS_FORK, os.fork = os.fork, _patched_fork
    if not _ORIGINAL_OS_FORKPTY:
        _ORIGINAL_OS_FORKPTY, os.forkpty = os.forkpty, _patched_forkpty
    cry("Patched %s and %s." % (_ORIGINAL_OS_FORK, _ORIGINAL_OS_FORKPTY))


def _activate_on_signal(_signum, _frame):
    assert _INST, "Manhole wasn't installed !"
    _INST.start()

ALL_SIGNALS = [
    getattr(signal, sig) for sig in dir(signal)
    if sig.startswith('SIG') and '_' not in sig
]


def install(verbose=True, patch_fork=True, activate_on=None, sigmask=ALL_SIGNALS, oneshot_on=None, start_timeout=0.5):
    global _STDERR, _INST, _SHOULD_RESTART, VERBOSE, START_TIMEOUT  # pylint: disable=W0603
    with _INST_LOCK:
        VERBOSE = verbose
        START_TIMEOUT = start_timeout
        _STDERR = sys.__stderr__
        if not _INST:
            _INST = Manhole(sigmask, start_timeout)
            if oneshot_on is not None:
                oneshot_on = getattr(signal, 'SIG'+oneshot_on) if isinstance(oneshot_on, string) else oneshot_on
                signal.signal(oneshot_on, _handle_oneshot)

            if activate_on is None:
                if oneshot_on is None:
                    _INST.start()
                    _SHOULD_RESTART = True
            else:
                activate_on = getattr(signal, 'SIG'+activate_on) if isinstance(activate_on, string) else activate_on
                if activate_on == oneshot_on:
                    raise RuntimeError('You cannot do activation of the Manhole thread on the same signal that you want to do oneshot activation !')
                signal.signal(activate_on, _activate_on_signal)
        atexit.register(_remove_manhole_uds)
        if patch_fork:
            if activate_on is None and oneshot_on is None:
                _patch_os_fork_functions()
            else:
                if activate_on:
                    cry("Not patching os.fork and os.forkpty. Activation is done by signal %s" % activate_on)
                elif oneshot_on:
                    cry("Not patching os.fork and os.forkpty. Oneshot activation is done by signal %s" % oneshot_on)


def reinstall():
    global _INST  # pylint: disable=W0603
    assert _INST
    with _INST_LOCK:
        if not (_INST.is_alive() and _INST in _ORIGINAL__ACTIVE):
            _INST = Manhole(_INST.sigmask, START_TIMEOUT)
            if _SHOULD_RESTART:
                _INST.start()


def dump_stacktraces():
    lines = []
    for thread_id, stack in sys._current_frames().items():  # pylint: disable=W0212
        lines.append("\n######### ProcessID=%s, ThreadID=%s #########" % (
            os.getpid(), thread_id
        ))
        for filename, lineno, name, line in traceback.extract_stack(stack):
            lines.append('File: "%s", line %d, in %s' % (filename, lineno, name))
            if line:
                lines.append("  %s" % (line.strip()))
    lines.append("#############################################\n\n")

    print('\n'.join(lines), file=sys.stderr)

########NEW FILE########
__FILENAME__ = test_manhole
from __future__ import print_function

import atexit
import errno
import imp
import logging
import os
import re
import select
import signal
import socket
import sys
import time
import unittest
from contextlib import closing

from process_tests import dump_on_error
from process_tests import setup_coverage
from process_tests import TestProcess
from process_tests import TestSocket
from process_tests import wait_for_strings
from pytest import mark
from pytest import raises

TIMEOUT = int(os.getenv('MANHOLE_TEST_TIMEOUT', 10))


def is_module_available(mod):
    try:
        return imp.find_module(mod)
    except ImportError:
        return False


def assert_manhole_running(proc, uds_path, oneshot=False, extra=None):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    for i in range(TIMEOUT):
        try:
            sock.connect(uds_path)
            break
        except Exception as exc:
            print('Failed to connect to %s: %s' % (uds_path, exc))
            time.sleep(1)
            if i + 1 == TIMEOUT:
                raise
    try:
        with TestSocket(sock) as client:
            with dump_on_error(client.read):
                wait_for_strings(client.read, TIMEOUT, "ProcessID", "ThreadID", ">>>")
                sock.send(b"print('FOOBAR')\n")
                wait_for_strings(client.read, TIMEOUT, "FOOBAR")
                wait_for_strings(proc.read, TIMEOUT, 'UID:%s' % os.getuid())
                if extra:
                    extra(sock)
                sock.shutdown(socket.SHUT_RDWR)
    finally:
        sock.close()
    wait_for_strings(proc.read, TIMEOUT, 'Cleaned up.', *[] if oneshot else ['Waiting for new connection'])


@mark.parametrize("count", range(1, 21))
def test_simple(count):
    with TestProcess(sys.executable, __file__, 'daemon', 'test_simple') as proc:
        with dump_on_error(proc.read):
            wait_for_strings(proc.read, TIMEOUT, '/tmp/manhole-')
            uds_path = re.findall(r"(/tmp/manhole-\d+)", proc.read())[0]
            wait_for_strings(proc.read, TIMEOUT, 'Waiting for new connection')
            for _ in range(count):
                proc.reset()
                assert_manhole_running(proc, uds_path)


def test_exit_with_grace():
    with TestProcess(sys.executable, '-u', __file__, 'daemon', 'test_simple') as proc:
        with dump_on_error(proc.read):
            wait_for_strings(proc.read, TIMEOUT, '/tmp/manhole-')
            uds_path = re.findall(r"(/tmp/manhole-\d+)", proc.read())[0]
            wait_for_strings(proc.read, TIMEOUT, 'Waiting for new connection')

            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(0.05)
            sock.connect(uds_path)
            with TestSocket(sock) as client:
                with dump_on_error(client.read):
                    wait_for_strings(client.read, TIMEOUT, "ThreadID", "ProcessID", ">>>")
                    sock.send(b"print('FOOBAR')\n")
                    wait_for_strings(client.read, TIMEOUT, "FOOBAR")

                    wait_for_strings(proc.read, TIMEOUT, 'UID:%s' % os.getuid())
                    sock.shutdown(socket.SHUT_WR)
                    select.select([sock], [], [], 5)
                    sock.recv(1024)
                    try:
                        sock.shutdown(socket.SHUT_RD)
                    except Exception as exc:
                        print("Failed to SHUT_RD: %s" % exc)
                    try:
                        sock.close()
                    except Exception as exc:
                        print("Failed to close socket: %s" % exc)
            wait_for_strings(proc.read, TIMEOUT, 'DONE.', 'Cleaned up.', 'Waiting for new connection')


def test_with_fork():
    with TestProcess(sys.executable, '-u', __file__, 'daemon', 'test_with_fork') as proc:
        with dump_on_error(proc.read):
            wait_for_strings(proc.read, TIMEOUT, '/tmp/manhole-')
            uds_path = re.findall(r"(/tmp/manhole-\d+)", proc.read())[0]
            wait_for_strings(proc.read, TIMEOUT, 'Waiting for new connection')
            for _ in range(2):
                proc.reset()
                assert_manhole_running(proc, uds_path)

            proc.reset()
            wait_for_strings(proc.read, TIMEOUT, 'Fork detected')
            wait_for_strings(proc.read, TIMEOUT, '/tmp/manhole-')
            new_uds_path = re.findall(r"(/tmp/manhole-\d+)", proc.read())[0]
            assert uds_path != new_uds_path

            wait_for_strings(proc.read, TIMEOUT, 'Waiting for new connection')
            for _ in range(2):
                proc.reset()
                assert_manhole_running(proc, new_uds_path)


if not hasattr(sys, 'pypy_version_info'):
    def test_with_forkpty():
        with TestProcess(sys.executable, '-u', __file__, 'daemon', 'test_with_forkpty') as proc:
            with dump_on_error(proc.read):
                wait_for_strings(proc.read, TIMEOUT, '/tmp/manhole-')
                uds_path = re.findall(r"(/tmp/manhole-\d+)", proc.read())[0]
                wait_for_strings(proc.read, TIMEOUT, 'Waiting for new connection')
                for _ in range(2):
                    proc.reset()
                    assert_manhole_running(proc, uds_path)

                proc.reset()
                wait_for_strings(proc.read, TIMEOUT, 'Fork detected')
                wait_for_strings(proc.read, TIMEOUT, '/tmp/manhole-')
                new_uds_path = re.findall(r"(/tmp/manhole-\d+)", proc.read())[0]
                assert uds_path != new_uds_path

                wait_for_strings(proc.read, TIMEOUT, 'Waiting for new connection')
                for _ in range(2):
                    proc.reset()
                    assert_manhole_running(proc, new_uds_path)


def test_auth_fail():
    with TestProcess(sys.executable, '-u', __file__, 'daemon', 'test_auth_fail') as proc:
        with dump_on_error(proc.read):
            wait_for_strings(proc.read, TIMEOUT, '/tmp/manhole-')
            uds_path = re.findall(r"(/tmp/manhole-\d+)", proc.read())[0]
            wait_for_strings(proc.read, TIMEOUT, 'Waiting for new connection')
            with closing(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)) as sock:
                sock.settimeout(1)
                sock.connect(uds_path)
                try:
                    assert b"" == sock.recv(1024)
                except socket.timeout:
                    pass
                wait_for_strings(
                    proc.read, TIMEOUT,
                    "SuspiciousClient: Can't accept client with PID:-1 UID:-1 GID:-1. It doesn't match the current EUID:",
                    'Waiting for new connection'
                )
                proc.proc.send_signal(signal.SIGINT)

try:
    import signalfd
except ImportError:
    pass
else:
    def test_signalfd_weirdness():
        with TestProcess(sys.executable, '-u', __file__, 'daemon', 'test_signalfd_weirdness') as proc:
            with dump_on_error(proc.read):
                wait_for_strings(proc.read, TIMEOUT, '/tmp/manhole-')
                uds_path = re.findall(r"(/tmp/manhole-\d+)", proc.read())[0]
                wait_for_strings(proc.read, TIMEOUT, 'Waiting for new connection')
                wait_for_strings(proc.read, 25 * TIMEOUT, *[
                    '[%s] read from signalfd:' % j for j in range(200)
                ])
                assert_manhole_running(proc, uds_path)

    if not is_module_available('gevent') and not is_module_available('eventlet'):
        def test_signalfd_weirdness_negative():
            with TestProcess(sys.executable, '-u', __file__, 'daemon', 'test_signalfd_weirdness_negative') as proc:
                with dump_on_error(proc.read):
                    wait_for_strings(proc.read, TIMEOUT, '/tmp/manhole-')
                    uds_path = re.findall(r"(/tmp/manhole-\d+)", proc.read())[0]
                    wait_for_strings(proc.read, TIMEOUT, 'Waiting for new connection')
                    wait_for_strings(proc.read, TIMEOUT, 'reading from signalfd failed')
                    assert_manhole_running(proc, uds_path)


def test_activate_on_usr2():
    with TestProcess(sys.executable, '-u', __file__, 'daemon', 'test_activate_on_usr2') as proc:
        with dump_on_error(proc.read):
            wait_for_strings(proc.read, TIMEOUT, 'Not patching os.fork and os.forkpty. Activation is done by signal')
            raises(AssertionError, wait_for_strings, proc.read, TIMEOUT, '/tmp/manhole-')
            proc.signal(signal.SIGUSR2)
            wait_for_strings(proc.read, TIMEOUT, '/tmp/manhole-')
            uds_path = re.findall(r"(/tmp/manhole-\d+)", proc.read())[0]
            wait_for_strings(proc.read, TIMEOUT, 'Waiting for new connection')
            assert_manhole_running(proc, uds_path)


def test_activate_on_with_oneshot_on():
    with TestProcess(sys.executable, '-u', __file__, 'daemon', 'test_activate_on_with_oneshot_on') as proc:
        with dump_on_error(proc.read):
            wait_for_strings(proc.read, TIMEOUT, "RuntimeError('You cannot do activation of the Manhole thread on the same signal that you want to do oneshot activation !')")


def test_oneshot_on_usr2():
    with TestProcess(sys.executable, '-u', __file__, 'daemon', 'test_oneshot_on_usr2') as proc:
        with dump_on_error(proc.read):
            wait_for_strings(proc.read, TIMEOUT, 'Not patching os.fork and os.forkpty. Oneshot activation is done by signal')
            raises(AssertionError, wait_for_strings, proc.read, TIMEOUT, '/tmp/manhole-')
            proc.signal(signal.SIGUSR2)
            wait_for_strings(proc.read, TIMEOUT, '/tmp/manhole-')
            uds_path = re.findall(r"(/tmp/manhole-\d+)", proc.read())[0]
            wait_for_strings(proc.read, TIMEOUT, 'Waiting for new connection')
            assert_manhole_running(proc, uds_path, oneshot=True)


def test_fail_to_cry():
    import manhole
    verbose = manhole.VERBOSE
    out = manhole._STDERR
    try:
        manhole.VERBOSE = True
        fh = os.fdopen(os.dup(2), 'w')
        fh.close()
        manhole._STDERR = fh
        manhole.cry('stuff')
    finally:
        manhole.VERBOSE = verbose
        manhole._STDERR = out


def test_oneshot_on_usr2_error():
    with TestProcess(sys.executable, '-u', __file__, 'daemon', 'test_oneshot_on_usr2') as proc:
        with dump_on_error(proc.read):
            wait_for_strings(proc.read, TIMEOUT, 'Not patching os.fork and os.forkpty. Oneshot activation is done by signal')
            raises(AssertionError, wait_for_strings, proc.read, TIMEOUT, '/tmp/manhole-')
            proc.signal(signal.SIGUSR2)
            wait_for_strings(proc.read, TIMEOUT, '/tmp/manhole-')
            uds_path = re.findall(r"(/tmp/manhole-\d+)", proc.read())[0]
            wait_for_strings(proc.read, TIMEOUT, 'Waiting for new connection')
            assert_manhole_running(proc, uds_path, oneshot=True, extra=lambda sock: sock.send(b"raise SystemExit()\n"))

            proc.reset()
            proc.signal(signal.SIGUSR2)
            wait_for_strings(proc.read, TIMEOUT, '/tmp/manhole-')
            uds_path = re.findall(r"(/tmp/manhole-\d+)", proc.read())[0]
            wait_for_strings(proc.read, TIMEOUT, 'Waiting for new connection')
            assert_manhole_running(proc, uds_path, oneshot=True)


def test_interrupt_on_accept():
    with TestProcess(sys.executable, '-u', __file__, 'daemon', 'test_interrupt_on_accept') as proc:
        with dump_on_error(proc.read):
            wait_for_strings(proc.read, TIMEOUT, '/tmp/manhole-')
            uds_path = re.findall(r"(/tmp/manhole-\d+)", proc.read())[0]
            wait_for_strings(proc.read, TIMEOUT, 'Waiting for new connection', 'Sending signal to manhole thread', 'Waiting for new connection')
            assert_manhole_running(proc, uds_path)


def setup_greenthreads(patch_threads=False):
    try:
        from gevent import monkey
        monkey.patch_all(thread=False)
    except (ImportError, SyntaxError):
        pass

    try:
        import eventlet
        eventlet.monkey_patch(thread=False)
    except (ImportError, SyntaxError):
        pass


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'daemon':
        logging.basicConfig(
            level=logging.DEBUG,
            format='[pid=%(process)d - %(asctime)s]: %(name)s - %(levelname)s - %(message)s',
        )
        test_name = sys.argv[2]

        setup_coverage()

        if os.getenv('PATCH_THREAD', False):
            import manhole
            setup_greenthreads(True)
        else:
            setup_greenthreads(True)
            import manhole

        if test_name == 'test_activate_on_usr2':
            manhole.install(activate_on='USR2')
            for i in range(TIMEOUT * 100):
                time.sleep(0.1)
        elif test_name == 'test_activate_on_with_oneshot_on':
            manhole.install(activate_on='USR2', oneshot_on='USR2')
            for i in range(TIMEOUT * 100):
                time.sleep(0.1)
        elif test_name == 'test_interrupt_on_accept':
            def handle_usr2(_sig, _frame):
                print('Got USR2')
            signal.signal(signal.SIGUSR2, handle_usr2)

            import ctypes
            import ctypes.util
            libpthread_path = ctypes.util.find_library("pthread")
            if not libpthread_path:
                raise ImportError
            libpthread = ctypes.CDLL(libpthread_path)
            if not hasattr(libpthread, "pthread_setname_np"):
                raise ImportError
            pthread_kill = libpthread.pthread_kill
            pthread_kill.argtypes = [ctypes.c_void_p, ctypes.c_int]
            pthread_kill.restype = ctypes.c_int
            manhole.install(sigmask=None)
            for i in range(15):
                time.sleep(0.1)
            print("Sending signal to manhole thread ...")
            pthread_kill(manhole._INST.ident, signal.SIGUSR2)
            for i in range(TIMEOUT * 100):
                time.sleep(0.1)
        elif test_name == 'test_oneshot_on_usr2':
            manhole.install(oneshot_on='USR2')
            for i in range(TIMEOUT  * 100):
                time.sleep(0.1)
        elif test_name.startswith('test_signalfd_weirdness'):
            if 'negative' in test_name:
                manhole.install(sigmask=None)
            else:
                manhole.install(sigmask=[signal.SIGCHLD])
            time.sleep(0.3)  # give the manhole a bit enough time to start
            print('Starting ...')
            import signalfd
            signalfd.sigprocmask(signalfd.SIG_BLOCK, [signal.SIGCHLD])
            fd = signalfd.signalfd(0, [signal.SIGCHLD], signalfd.SFD_NONBLOCK|signalfd.SFD_CLOEXEC)
            for i in range(200):
                print('Forking %s:' % i)
                pid = os.fork()
                print(' - [%s/%s] forked' % (i, pid))
                if pid:
                    while 1:
                        print(' - [%s/%s] selecting on: %s' % (i, pid, [fd]))
                        read_ready, _, errors = select.select([fd], [], [fd], 1)
                        if read_ready:
                            try:
                                print(' - [%s/%s] reading from signalfd ...' % (i, pid))
                                print(' - [%s] read from signalfd: %r ' % (i, os.read(fd, 128)))
                                break
                            except OSError as exc:
                                print(' - [%s/%s] reading from signalfd failed with errno %s' % (i, pid, exc.errno))
                        else:
                            print(' - [%s/%s] reading from signalfd failed - not ready !' % (i, pid))
                            if 'negative' in test_name:
                                time.sleep(1)
                        if errors:
                            raise RuntimeError("fd has error")
                else:
                    print(' - [%s/%s] exiting' % (i, pid))
                    os._exit(0)
            time.sleep(TIMEOUT * 10)
        elif test_name == 'test_auth_fail':
            manhole.get_peercred = lambda _: (-1, -1, -1)
            manhole.install()
            time.sleep(TIMEOUT * 10)
        else:
            manhole.install()
            time.sleep(0.3)  # give the manhole a bit enough time to start
            if test_name == 'test_simple':
                time.sleep(TIMEOUT * 10)
            elif test_name == 'test_with_forkpty':
                time.sleep(1)
                pid, masterfd = os.forkpty()
                if pid:
                    @atexit.register
                    def cleanup():
                        try:
                            os.kill(pid, signal.SIGINT)
                            time.sleep(0.2)
                            os.kill(pid, signal.SIGTERM)
                        except OSError as e:
                            if e.errno != errno.ESRCH:
                                raise
                    while not os.waitpid(pid, os.WNOHANG)[0]:
                        try:
                            os.write(2, os.read(masterfd, 1024))
                        except OSError as e:
                            print("Error while reading from masterfd:", e)
                else:
                    time.sleep(TIMEOUT * 10)
            elif test_name == 'test_with_fork':
                time.sleep(1)
                pid = os.fork()
                if pid:
                    @atexit.register
                    def cleanup():
                        try:
                            os.kill(pid, signal.SIGINT)
                            time.sleep(0.2)
                            os.kill(pid, signal.SIGTERM)
                        except OSError as e:
                            if e.errno != errno.ESRCH:
                                raise
                    os.waitpid(pid, 0)
                else:
                    time.sleep(TIMEOUT * 10)
            else:
                raise RuntimeError('Invalid test spec.')
        print('DIED.')
    else:
        unittest.main()

########NEW FILE########
