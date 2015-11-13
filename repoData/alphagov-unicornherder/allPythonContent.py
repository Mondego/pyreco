__FILENAME__ = helpers
import contextlib

from nose.tools import *
from mock import *

@contextlib.contextmanager
def fake_timeout_fail(*args, **kwargs):
    from unicornherder.timeout import TimeoutError
    raise TimeoutError()

########NEW FILE########
__FILENAME__ = test_herder
import signal
import sys
from .helpers import *
from unicornherder.herder import Herder, HerderError

if sys.version_info > (3, 0):
    builtin_mod = 'builtins'
else:
    builtin_mod = '__builtin__'


class TestHerder(object):

    def test_init_defaults(self):
        h = Herder()
        assert_equal(h.unicorn, 'gunicorn')
        assert_equal(h.pidfile, 'gunicorn.pid')
        assert_equal(h.args, '')

    def test_init_unicorn(self):
        h = Herder(unicorn='unicorn')
        assert_equal(h.unicorn, 'unicorn')

    def test_init_gunicorn(self):
        h = Herder(unicorn='gunicorn')
        assert_equal(h.unicorn, 'gunicorn')

    def test_init_unicornbad(self):
        assert_raises(HerderError, Herder, unicorn='unicornbad')

    @patch('unicornherder.herder.subprocess.Popen')
    def test_spawn_returns_true(self, popen_mock):
        h = Herder()
        h._boot_loop = lambda: True
        assert_true(h.spawn())

    @patch('unicornherder.herder.subprocess.Popen')
    def test_spawn_gunicorn(self, popen_mock):
        h = Herder(unicorn='gunicorn')
        h._boot_loop = lambda: True
        h.spawn()
        assert_equal(popen_mock.call_count, 1)
        popen_mock.assert_called_once_with(['gunicorn', '-D', '-p', 'gunicorn.pid'])

    @patch('unicornherder.herder.subprocess.Popen')
    def test_spawn_unicorn(self, popen_mock):
        h = Herder(unicorn='unicorn')
        h._boot_loop = lambda: True
        h.spawn()
        assert_equal(popen_mock.call_count, 1)
        popen_mock.assert_called_once_with(['unicorn', '-D', '-P', 'unicorn.pid'])

    @patch('unicornherder.herder.subprocess.Popen')
    @patch('unicornherder.herder.timeout')
    def test_spawn_unicorn_timeout(self, timeout_mock, popen_mock):
        popen_mock.return_value.pid = -1
        timeout_mock.side_effect = fake_timeout_fail
        h = Herder()
        popen_mock.return_value.poll.return_value = None
        ret = h.spawn()
        assert_false(ret)
        popen_mock.return_value.terminate.assert_called_once_with()

    @patch('unicornherder.herder.subprocess.Popen')
    @patch('unicornherder.herder.timeout')
    def test_configurable_boot_timeout(self, timeout_mock, popen_mock):
        popen_mock.return_value.pid = -1
        timeout_mock.side_effect = fake_timeout_fail
        h = Herder(boot_timeout=45)
        popen_mock.return_value.poll.return_value = None
        ret = h.spawn()
        timeout_mock.assert_called_once_with(45)
        assert_false(ret)
        popen_mock.return_value.terminate.assert_called_once_with()

    @patch('unicornherder.herder.time.sleep')
    @patch('unicornherder.herder.psutil.Process')
    @patch('%s.open' % builtin_mod)
    def test_loop_valid_pid(self, open_mock, process_mock, sleep_mock):
        open_mock.return_value.read.return_value = '123\n'
        h = Herder()
        ret = h._loop_inner()
        assert_equal(ret, True)
        process_mock.assert_called_once_with(123)

    @patch('unicornherder.herder.time.sleep')
    @patch('%s.open' % builtin_mod)
    def test_loop_invalid_pid(self, open_mock, sleep_mock):
        open_mock.return_value.read.return_value = 'foobar'
        h = Herder()
        assert_raises(HerderError, h._loop_inner)

    @patch('unicornherder.herder.time.sleep')
    @patch('%s.open' % builtin_mod)
    def test_loop_nonexistent_pidfile(self, open_mock, sleep_mock):
        def _fail():
            raise IOError()
        open_mock.return_value.read.side_effect = _fail
        h = Herder()
        assert_raises(HerderError, h._loop_inner)

    @patch('unicornherder.herder.time.sleep')
    @patch('%s.open' % builtin_mod)
    def test_loop_nonexistent_pidfile_terminating(self, open_mock, sleep_mock):
        def _fail():
            raise IOError()
        open_mock.return_value.read.side_effect = _fail
        h = Herder()
        h.terminating = True
        assert_equal(h._loop_inner(), False)

    @patch('unicornherder.herder.time.sleep')
    @patch('unicornherder.herder.psutil.Process')
    @patch('%s.open' % builtin_mod)
    def test_loop_detects_pidchange(self, open_mock, process_mock, sleep_mock):
        proc1 = MagicMock()
        proc2 = MagicMock()
        proc1.pid = 123
        proc2.pid = 456

        h = Herder()

        open_mock.return_value.read.return_value = '123\n'
        process_mock.return_value = proc1
        ret = h._loop_inner()
        assert_equal(ret, True)

        open_mock.return_value.read.return_value = '456\n'
        process_mock.return_value = proc2
        ret = h._loop_inner()
        assert_equal(ret, True)

        expected_calls = []
        assert_equal(proc1.mock_calls, expected_calls)

    @patch('unicornherder.herder.time.sleep')
    @patch('unicornherder.herder.psutil.Process')
    @patch('%s.open' % builtin_mod)
    def test_loop_reload_pidchange_signals(self, open_mock, process_mock,
                                           sleep_mock):
        proc1 = MagicMock()
        proc2 = MagicMock()
        proc1.pid = 123
        proc2.pid = 456

        h = Herder()

        open_mock.return_value.read.return_value = '123\n'
        process_mock.return_value = proc1
        ret = h._loop_inner()
        assert_equal(ret, True)

        # Simulate SIGHUP
        h._handle_HUP(signal.SIGHUP, None)

        open_mock.return_value.read.return_value = '456\n'
        process_mock.return_value = proc2
        ret = h._loop_inner()
        assert_equal(ret, True)

        expected_calls = [call.send_signal(signal.SIGUSR2),
                          call.send_signal(signal.SIGWINCH),
                          call.send_signal(signal.SIGQUIT)]
        assert_equal(proc1.mock_calls, expected_calls)

    def test_forward_signal(self):
        h = Herder()
        h.master = MagicMock()

        h._handle_signal('INT')(signal.SIGINT, None)
        h.master.send_signal.assert_called_once_with(signal.SIGINT)

    def test_forward_signal_nomaster(self):
        h = Herder()
        h._handle_signal('INT')(signal.SIGINT, None)

    def test_handle_hup_nomaster(self):
        h = Herder()
        h._handle_HUP(signal.SIGHUP, None)

########NEW FILE########
__FILENAME__ = command
from __future__ import print_function

import argparse
import logging
import os
import sys

from . import __version__
from .herder import Herder


parser = argparse.ArgumentParser(description='Manage daemonized (g)unicorns.')

parser.add_argument('-u', '--unicorn', default='gunicorn', metavar='TYPE',
                    choices=['unicorn', 'unicorn_rails', 'gunicorn','gunicorn_django'],
                    help='The type of unicorn to manage (gunicorn, gunicorn_django, unicorn, unicorn_rails)')
parser.add_argument('-b', '--unicorn-bin', default=None, metavar='UNICORN_BIN',
                    type=str, dest='unicorn_bin',
                    help='path to a specific unicorn to manage')
parser.add_argument('-g', '--gunicorn-bin', default=None, metavar='GUNICORN_BIN',
                    type=str, dest='gunicorn_bin',
                    help='path to a specific gunicorn to manage')
parser.add_argument('-p', '--pidfile', metavar='PATH',
                    help='Path to the pidfile that unicorn will write')
parser.add_argument('-t', '--timeout', default=30, type=int, metavar='30', dest='boot_timeout',
                    help='Timeout in seconds to start workers')
parser.add_argument('-v', '--version', action='version', version=__version__)
parser.add_argument('args', nargs=argparse.REMAINDER,
                    help='Any additional arguments will be passed to unicorn/'
                         "gunicorn. Prefix with '--' if you are passing flags (e.g. "
                         'unicornherder -- -w 4 myapp:app)')


def configure_logger():
    format = '%(asctime)-15s  %(levelname)-8s  %(message)s'
    logging.basicConfig(format=format, level=logging.INFO)

    log = logging.getLogger('unicornherder')

    level = os.environ.get('UNICORNHERDER_LOGLEVEL', '').upper()
    valid_levels = ['CRITICAL', 'FATAL', 'ERROR', 'WARN',
                    'WARNING', 'INFO', 'DEBUG']

    if level in valid_levels:
        log.setLevel(getattr(logging, level))


def main():
    configure_logger()

    args = parser.parse_args()

    if len(args.args) > 0 and args.args[0] == '--':
        args.args.pop(0)

    args.args = ' '.join(args.args)

    if args.pidfile is None:
        args.pidfile = '%s.pid' % args.unicorn

    herder = Herder(**vars(args))
    if herder.spawn():
        return herder.loop()

if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = herder
import atexit
import logging
import psutil
import shlex
import signal
import subprocess
import time

from .timeout import timeout, TimeoutError

log = logging.getLogger(__name__)

COMMANDS = {
    'unicorn': 'unicorn -D -P "{pidfile}" {args}',
    'unicorn_rails': 'unicorn_rails -D -P "{pidfile}" {args}',
    'unicorn_bin': '{unicorn_bin} -D -P "{pidfile}" {args}',
    'gunicorn': 'gunicorn -D -p "{pidfile}" {args}',
    'gunicorn_django': 'gunicorn_django -D -p "{pidfile}" {args}',
    'gunicorn_bin': '{gunicorn_bin} -D -p "{pidfile}" {args}'
}

MANAGED_PIDS = set([])

WORKER_WAIT = 120


class HerderError(Exception):
    pass


class Herder(object):
    """

    The Herder class manages a single unicorn instance and its worker
    children. It has few configuration options: you simply instantiate a
    Herder, spawn unicorn with ``spawn()``, and then start a monitoring loop
    with the ``loop()`` method.

    The ``loop()`` method will exit with a status code, which by default will
    be used as the exit status of the ``unicornherder`` command line utility.

    Example::

        herder = Herder()
        if herder.spawn():
            sys.exit(herder.loop())

    """

    def __init__(self, unicorn='gunicorn', unicorn_bin=None, gunicorn_bin=None,
                 pidfile=None, boot_timeout=30, args=''):
        """

        Creates a new Herder instance.

        unicorn      - the type of unicorn to herd; either 'unicorn' or 'gunicorn'
                       (Default: gunicorn)
        unicorn_bin  - path of specific unicorn to run
                       (Default: None)
        gunicorn_bin - path of specific gunicorn to run
                       (Default: None)
        pidfile      - path of the pidfile to write
                       (Default: gunicorn.pid or unicorn.pid depending on the value of
                        the unicorn parameter)
        args         - any additional arguments to pass to the unicorn executable
                       (Default: '')

        """

        self.unicorn_bin = unicorn_bin
        self.gunicorn_bin = gunicorn_bin

        if unicorn_bin:
            self.unicorn = unicorn_bin
        elif gunicorn_bin:
            self.unicorn = gunicorn_bin
        else:
            self.unicorn = unicorn
        self.pidfile = '%s.pid' % self.unicorn if pidfile is None else pidfile
        self.args = args
        self.boot_timeout = boot_timeout

        try:
            if not unicorn_bin and not gunicorn_bin:
                COMMANDS[self.unicorn]
        except KeyError:
            raise HerderError('Unknown unicorn type: %s' % self.unicorn)

        self.master = None
        self.reloading = False
        self.terminating = False

    def spawn(self):
        """

        Spawn a new unicorn instance.

        Returns False if unicorn fails to daemonize, and True otherwise.

        """
        if self.unicorn in COMMANDS:
            cmd = COMMANDS[self.unicorn]
            cmd = cmd.format(pidfile=self.pidfile, args=self.args)
        elif self.unicorn_bin:
            cmd = COMMANDS['unicorn_bin']
            cmd = cmd.format(unicorn_bin=self.unicorn, pidfile=self.pidfile, args=self.args)
        elif self.gunicorn_bin:
            cmd = COMMANDS['gunicorn_bin']
            cmd = cmd.format(gunicorn_bin=self.unicorn, pidfile=self.pidfile, args=self.args)
        else:
            return False

        log.debug("Calling %s: %s", self.unicorn, cmd)

        cmd = shlex.split(cmd)
        try:
            process = subprocess.Popen(cmd)
        except OSError as e:
            if e.errno == 2:
                log.error("Command '%s' not found. Is it installed?", cmd[0])
                return False
            else:
                raise

        MANAGED_PIDS.add(process.pid)

        try:
            with timeout(self.boot_timeout):
                process.wait()
        except TimeoutError:
            log.error('%s failed to daemonize within %s seconds. Sending TERM '
                      'and exiting.', self.unicorn, self.boot_timeout)
            if process.poll() is None:
                process.terminate()
            return False

        # If we got this far, unicorn has daemonized, and we no longer need to
        # worry about the original process.
        MANAGED_PIDS.remove(process.pid)

        # The unicorn herder does a graceful unicorn restart on HUP
        signal.signal(signal.SIGHUP, self._handle_HUP)

        # Forward other useful signals to the currently tracked master
        # process.
        #
        # We do NOT forward SIGWINCH, because it is triggered by terminal
        # resize, leading to some *seriously* weird behaviour (resize
        # xterm, unicorn workers are killed).
        for sig in ['INT', 'QUIT', 'TERM', 'TTIN', 'TTOU', 'USR1', 'USR2']:
            signal.signal(getattr(signal, 'SIG%s' % sig),
                          self._handle_signal(sig))

        return True

    def loop(self):
        """Enter the monitoring loop"""
        while True:
            if not self._loop_inner():
                # The unicorn has died. So should we.
                log.error('%s died. Exiting.', self.unicorn.title())
                return 1
            time.sleep(2)

    def _loop_inner(self):
        old_master = self.master
        pid = self._read_pidfile()

        if pid is None:
            return False

        try:
            self.master = psutil.Process(pid)
        except psutil.NoSuchProcess:
            return False

        if old_master is None:
            log.info('%s booted (PID %s)', self.unicorn.title(), self.master.pid)

            MANAGED_PIDS.add(self.master.pid)

        # Unicorn has forked a new master
        if old_master is not None and self.master.pid != old_master.pid:
            log.info('%s changed PID (was %s, now %s)',
                     self.unicorn.title(),
                     old_master.pid,
                     self.master.pid)

            MANAGED_PIDS.add(self.master.pid)

            if self.reloading:
                _wait_for_workers(self.master)
                _kill_old_master(old_master)
                self.reloading = False

            MANAGED_PIDS.remove(old_master.pid)

        return True

    def _read_pidfile(self):
        for _ in range(5):
            try:
                content = open(self.pidfile).read()
            except IOError as e:
                try:
                    log.debug('pidfile missing, checking for %s.oldbin', self.pidfile)
                    content = open(self.pidfile + ".oldbin").read()
                except IOError as e:
                    # If we are expecting unicorn to die, then this is normal, and
                    # we can just return None, thus triggering a clean exit of the
                    # Herder.
                    if self.terminating:
                        return None
                    else:
                        log.debug('Got IOError while attempting to read pidfile: %s', e)
                        log.debug('This is usually not fatal. Retrying in a moment...')
                        time.sleep(1)
                        continue
            try:
                pid = int(content)
            except ValueError as e:
                log.debug('Got ValueError while reading pidfile. Is "%s" an integer? %s',
                          content, e)
                log.debug('This is usually not fatal. Retrying in a moment...')
                time.sleep(1)
                continue

            return pid

        raise HerderError('Failed to read pidfile %s after 5 attempts, aborting!' %
                          self.pidfile)

    def _handle_signal(self, name):
        def _handler(signum, frame):
            if self.master is None:
                log.warn("Caught %s but have no tracked process.", name)
                return

            if signum in [signal.SIGINT, signal.SIGQUIT, signal.SIGTERM]:
                log.debug("Caught %s: expecting termination.", name)
                self.terminating = True

            log.debug("Forwarding %s to PID %s", name, self.master.pid)
            self.master.send_signal(signum)

        return _handler

    def _handle_HUP(self, signum, frame):
        if self.master is None:
            log.warn("Caught HUP but have no tracked process.")
            return

        log.info("Caught HUP: gracefully restarting PID %s", self.master.pid)
        self.reloading = True
        self.master.send_signal(signal.SIGUSR2)


#
# If the unicorn herder exits abnormally, it is essential that unicorn
# dies as well. Register an atexit callback to kill off any surviving
# unicorns.
#
@atexit.register
def _emergency_slaughter():
    for pid in MANAGED_PIDS:
        try:
            proc = psutil.Process(pid)
            proc.kill()
        except:
            pass


def _wait_for_workers(process):
    # TODO: do something smarter here
    time.sleep(WORKER_WAIT)


def _kill_old_master(process):
    log.debug("Sending WINCH to old master (PID %s)", process.pid)
    process.send_signal(signal.SIGWINCH)
    time.sleep(1)
    log.debug("Sending QUIT to old master (PID %s)", process.pid)
    process.send_signal(signal.SIGQUIT)

########NEW FILE########
__FILENAME__ = timeout
import contextlib
import signal


class TimeoutError(Exception):
    pass


@contextlib.contextmanager
def timeout(time=30):
    def _fail(signal, frame):
        raise TimeoutError("%s second timeout expired" % time)

    signal.signal(signal.SIGALRM, _fail)
    signal.alarm(time)
    yield
    signal.alarm(0)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)

########NEW FILE########
