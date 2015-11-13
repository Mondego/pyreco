__FILENAME__ = gevent_server
from lust import log, server
import os
import sys

def handle(socket, address):
    log.info("Blocking %r:%r" % address)
    socket.close()

class Service(server.Simple):

    name = 'geventserver'

    def before_jail(self, args):
        from gevent.server import StreamServer

        self.host = self.config.get('geventserver.host', '0.0.0.0')
        self.ports = (int(x) for x in self.config['geventserver.ports'].split())
        log.info("Listening ports %r" % self.ports)

        self.server = None # this gets the last one to do a forever on

        for port in self.ports:
            self.server = StreamServer((self.host, port), handle)
            self.server.start()

    def start(self, args):
        self.server.serve_forever()

    def shutdown(self, signal):
        log.info("Shutting down now signal: %d" % signal)

if __name__ == "__main__":

    log.setup('/tmp/geventserver.log')
    server = Service(config_file=os.getcwd() + '/examples/master.conf')
    server.run(sys.argv)


########NEW FILE########
__FILENAME__ = thread_server
import threading
import SocketServer
import sys
from lust import log, server


class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):
    allow_reuse_address = True

    def handle(self):
        log.info("Connection %r:%r" % self.client_address)
        self.request.sendall("HI!")
        self.request.close()


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

class ThreadDaemon(server.Simple):

    name = 'threadserver'

    def before_drop_privs(self, args):
        HOST = "0.0.0.0"
        if self.config:
            ports = list(int(x) for x in
                         self.config['threadserver.ports'].split())
        else:
            ports = list(int(x) for x in args)

        log.debug("Ports %r" % ports)

        if not ports:
            log.error("You need to list some ports.")
            sys.exit(1)

        self.server = None # this gets the last one to do a forever on

        for PORT in ports:
            server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
            ip, port = server.server_address
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()

        self.server = server

    def start(self, args):
        self.server.serve_forever()

    def shutdown(self, signal):
        log.info("Shutting down now signal: %d" % signal)


if __name__ == "__main__":
    # if you're on OSX then change this to whatever user nd group
    server = ThreadDaemon(uid='nobody', gid='nogroup')
    server.run(sys.argv)


########NEW FILE########
__FILENAME__ = config
from ConfigParser import SafeConfigParser


def load_ini_file(file_name, defaults={}):
    config = SafeConfigParser()
    config.readfp(open(file_name))
    results = {}

    for section in config.sections():
        for key, value in config.items(section):
            results[section + '.' + key] = value

    results.update(defaults)

    return results


########NEW FILE########
__FILENAME__ = log
import sys
import os
import time

DEBUG=False
SETUP=False

# need a simple thread lock on this, or just fuck it

def setup(log_path, force=False):
    global SETUP

    if force: SETUP=False

    if not SETUP:
        # test we can open for writing
        with open(log_path, 'a+') as f:
            f.write("[%s] INFO: Log opened.\n" % time.ctime())

        os.closerange(0, 1024)

        fd = os.open(log_path, os.O_RDWR | os.O_CREAT)

        os.dup2(0, 1)
        os.dup2(0, 2)

        sys.stdout = os.fdopen(fd, 'a+', 0)
        sys.stderr = sys.stdout
        SETUP=True

def warn(msg):
    print "[%s] WARN: %s" % (time.ctime(), msg)


def error(msg):
    print "[%s] ERROR: %s" % (time.ctime(), msg)


def info(msg):
    print "[%s] INFO: %s" % (time.ctime(), msg)


def debug(msg):
    if not DEBUG:
        print "[%s] DEBUG: %s" % (time.ctime(), msg)


def set_debug_level(on):
    global DEBUG
    DEBUG=on


########NEW FILE########
__FILENAME__ = server
from . import unix, log, config
import sys
import os

class Simple(object):

    name = None
    should_jail = True
    should_drop_priv = True

    def __init__(self, run_base="/var/run", log_dir="/var/log",
                 pid_file_path="/var/run",
                 uid="nobody", gid="nogroup", config_file=None):
        assert self.name, "You must set the service's name."

        config_file = config_file or os.path.join('/etc', self.name + ".conf")
        self.load_config(config_file)
        self.run_dir = self.get('run_dir') or os.path.join(run_base, self.name)
        self.pid_path = self.get('pid_path') or pid_file_path
        self.log_file = self.get('log_file') or os.path.join(log_dir, self.name + ".log")
        self.uid = self.get('uid') or uid
        self.gid = self.get('gid') or gid
        self.run_dir_mode = self.get('run_dir_mode') or '0700'
        self.run_dir_mode = int(self.run_dir_mode, 8)

        log.debug("UID and GID are %s:%s" % (self.uid, self.gid))

        self.unum, self.gnum = unix.get_user_info(self.uid, self.gid)
        log.debug("Numeric UID:GID are %d:%d" % (self.unum, self.gnum))


    def before_daemonize(self, args):
        pass


    def before_jail(self, args):
        pass


    def before_drop_privs(self, args):
        pass


    def start(self, args):
        pass


    def stop(self, args):
        log.info("Stopping server.")
        unix.kill_server(self.name, pid_file_path=self.pid_path)


    def status(self, args):
        print "Server running at pid %d" % unix.pid_read(self.name,
                                                         pid_file_path=self.pid_path)

    def shutdown(self, signal):
        pass


    def parse_cli(self, args):
        args.pop(0)

        if not args:
            log.error("Need a command like start, stop, status.")
            sys.exit(1)

        return args[0], args[1:]


    def daemonize(self, args):
        log.setup(self.log_file)
        log.info("Daemonizing.")

        self.before_daemonize(args)

        if unix.still_running(self.name, pid_file_path=self.pid_path):
            log.error("%s still running. Aborting." % self.name)
            sys.exit(1)
        else:
            unix.daemonize(self.name, pid_file_path=self.pid_path)

        def shutdown_handler(signal, frame):
            self.shutdown(signal)
            sys.exit(0)

        unix.register_shutdown(shutdown_handler)

        if not os.path.exists(self.run_dir):
            log.warn("Directory %s does not exist, attempting to create it." %
                     self.run_dir)
            os.mkdir(self.run_dir)

            log.info("Giving default permissions to %s, change them later if you need."
                     % self.run_dir)
            os.chown(self.run_dir, self.unum, self.gnum)
            os.chmod(self.run_dir, self.run_dir_mode)

        if self.should_jail:
            self.before_jail(args)
            log.info("Setting up the chroot jail to: %s" % self.run_dir)
            unix.chroot_jail(self.run_dir)
        else:
            log.warn("This daemon does not jail itself, chdir to %s instead" % self.run_dir)
            os.chdir(self.run_dir)

        if self.should_drop_priv:
            self.before_drop_privs(args)
            unix.drop_privileges(self.unum, self.gnum)
        else:
            log.warn("This daemon does not drop privileges.")

        log.info("Server %s running." % self.name)
        self.start(args)


    def run(self, args):
        command, args = self.parse_cli(args)

        if command == "start":
            self.daemonize(args)
        elif command == "stop":
            self.stop(args)
        elif command == "status":
            self.status(args)
        else:
            log.error("Invalid command: %s.  Commands are: start, stop, reload, status.")
            sys.exit(1)

    def get(self, name):
        """Simple convenience method that just uses the service's configured
        name to get a config value."""

        return self.config.get(self.name + '.' + name, None)

    def load_config(self, config_file):
        self.config_file = config_file
        log.debug("Config file at %s" % self.config_file)

        if os.path.exists(self.config_file):
            self.config = config.load_ini_file(self.config_file)
            log.debug("Loading config file %s contains %r" % (self.config_file,
                                                              self.config))
        else:
            log.warn("No config file at %s, using defaults." % self.config_file)
            self.config = {}


########NEW FILE########
__FILENAME__ = tail
import time
import os
import re
from . import log

def file_rotated(file_name, orig_stat):
    while True:
        try:
            new_stat = os.stat(file_name)

            if orig_stat == None:
                return True, new_stat
            elif orig_stat.st_ino != new_stat.st_ino:
                return True, new_stat
            else:
                return False, orig_stat
        except OSError:
            time.sleep(0.1)


def tail_lines(file_name):
    _, orig_stat = file_rotated(file_name, None)
    log_file = open(file_name)
    log_file.seek(0, os.SEEK_END)

    while True:
        line = log_file.readline()
        if line:
            yield line
        else:
            time.sleep(0.1)

            # check for rotation and reopen if it did
            rotated, orig_stat = file_rotated(file_name, orig_stat)
            if rotated:
                log.info("Log file %s rotated." % file_name)
                log_file.close()
                log_file = open(file_name)

def convert_patterns(patterns):
    results = {}

    for pattern, target in patterns.items():
        matcher = re.compile(pattern)
        results[matcher] = target

    return results

def scan_lines(file_name, patterns):
    patterns = convert_patterns(patterns)

    for line in tail_lines(file_name):
        for pattern, target in patterns.items():
            matches = pattern.match(line)
            if matches:
                yield target, line, matches.groupdict()


########NEW FILE########
__FILENAME__ = unix
import pwd
import grp
import signal
import os
from . import log

def make_pid_file_path(name, pid_file_path="/var/run"):
    return os.path.join(pid_file_path, name + ".pid")

def pid_store(name, pid_file_path="/var/run"):
    os.umask(077) # set umask for pid
    pid_path = make_pid_file_path(name, pid_file_path)

    with open(pid_path, "w") as f:
        f.write(str(os.getpid()))


def pid_read(name, pid_file_path="/var/run"):
    pid_path = make_pid_file_path(name, pid_file_path)
    log.debug("Checking pid path: %s" % pid_path)

    try:
        with open(pid_path, "r") as f:
            return int(f.read())
    except IOError:
        return -1

def still_running(name, pid_file_path="/var/run"):
    pid = pid_read(name, pid_file_path=pid_file_path)

    if pid == -1:
        log.debug("Returned pid not running at %s" % pid)
        return False
    else:
        # check if the process is still running with kill
        try:
            os.kill(pid, 0)
            log.debug("Process running at %d" % pid)
            return True
        except OSError:
            # this means the process is gone
            log.warn("Stale pid file %r has %d pid." % (
                make_pid_file_path(name, pid_file_path), pid))
            return False


def kill_server(name, pid_file_path="/var/run", sig=signal.SIGINT):
    if still_running(name, pid_file_path=pid_file_path):
        pid = pid_read(name, pid_file_path=pid_file_path)
        os.kill(pid, sig)


def reload_server(name, pid_file_path="/var/run"):
    kill_server(name, pid_file_path=pid_file_path, sig=signal.SIGHUP)


def pid_remove_dead(name, pid_file_path="/var/run"):
    if not still_running(name, pid_file_path=pid_file_path):
        pid_file = make_pid_file_path(name, pid_file_path)
        if os.path.exists(pid_file):
            os.remove(pid_file)


def daemonize(prog_name, pid_file_path="/var/run", dont_exit=False, main=None):
    """
    This will do the fork dance to daemonize the Python script.  You have a
    couple options in using this.
    
    1) Call it with just a prog_name and the current script forks like normal
    then continues running.

    2) Add dont_exit=True and it will both fork a new process *and* keep the
    parent.

    3) Set main to a function and that function will become the new main method
    of the process, and the process will exit when that function ends.
    """
    if os.fork() == 0:
        os.setsid()
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        pid = os.fork()

        if pid != 0:
            os._exit(0)
        else:
            pid_remove_dead(prog_name, pid_file_path=pid_file_path)
            pid_store(prog_name, pid_file_path=pid_file_path)

            if main: 
                main()
                os._exit(0)

    elif dont_exit:
        return True
    else:
        os._exit(0)


def chroot_jail(root="/tmp"):
    os.chroot(root)
    os.chdir("/")


def get_user_info(uid, gid):
    return (
        pwd.getpwnam(uid).pw_uid,
        grp.getgrnam(gid).gr_gid,
    )


def drop_privileges(running_uid, running_gid):
    if os.getuid() != 0:
        return

    log.info("Dropping pivs to UID %r GID %r" % (running_uid, running_gid))

    # Remove group privileges
    os.setgroups([])

    # Try setting the new uid/gid
    os.setgid(running_gid)
    os.setuid(running_uid)

    # Ensure a very conservative umask
    os.umask(077)


def register_signal(handler, signals):
    for sig in signals:
        signal.signal(sig, handler)


def register_shutdown(handler):
    register_signal(handler, signals=[signal.SIGINT, signal.SIGTERM])


########NEW FILE########
__FILENAME__ = config_tests
from nose.tools import *
from lust import config

def test_load_ini_file():
    settings = config.load_ini_file("tests/sample.ini")
    assert_equal(settings['threadserver.run_dir'], '/var/run/threadserver')

def test_load_ini_file_defaults():
    settings = config.load_ini_file("tests/sample.ini", defaults={'threadserver.run_dir':
                                                                  '/var/other'})
    assert_equal(settings['threadserver.run_dir'], '/var/other')


########NEW FILE########
__FILENAME__ = log_tests
from nose.tools import *
from lust import log
from mock import patch


@patch("sys.stdout")
@patch("sys.stderr")
@patch("os.dup2")
@patch("os.fdopen")
@patch("os.closerange")
def test_setup(*calls):
    log.setup("tests/test.log")
    # weird but 0 is os_close, and we want to force an exception
    calls[0].side_effect=OSError

    # confirm the last three in the @path list are called
    for i in calls[0:3]:
        assert_true(i.called, "Did not call %r" % i)


@patch('time.ctime')
def test_message_levels(time_ctime):
    log.warn("test warning")
    assert_true(time_ctime.called)
    time_ctime.reset

    log.error("test error")
    assert_true(time_ctime.called)
    time_ctime.reset

    log.info("test info")
    assert_true(time_ctime.called)
    time_ctime.reset


@patch('time.ctime')
def test_debug_level(time_ctime):
    log.set_debug_level(True)
    assert_true(log.DEBUG, "DEBUG should be true.")
    log.debug("Test")
    assert_false(time_ctime.called, "Should not get called.")
    log.set_debug_level(False)
    assert_false(log.DEBUG, "DEBUG should be true.")
    log.debug("Test")
    assert_true(time_ctime.called, "Should get called.")


########NEW FILE########
__FILENAME__ = server_tests
from nose.tools import *
from lust import unix
import os
from time import sleep

def setup():
    if unix.still_running("simpledaemon", pid_file_path="tests"):
        os.system('sudo python tests/simple_test_server.py stop')


def test_simple_server():
    if not os.path.exists("tests/simpledaemon"):
        os.mkdir("tests/simpledaemon")

    os.system('sudo python tests/simple_test_server.py start')
    sleep(1)

    EXPECT_PATHS=['tests/simpledaemon.pid',
                  'tests/simpledaemon.log',
                  'tests/simpledaemon/before_drop_priv.txt',
                  '/tmp/before_jail.txt',
                  '/tmp/before_daemonize.txt']

    for path in EXPECT_PATHS:
        assert_true(os.path.exists(path), "File %s not there." % path)

    os.system('sudo python tests/simple_test_server.py stop')
    sleep(1)

    assert_false(unix.still_running("simpledaemon", pid_file_path="tests"))

########NEW FILE########
__FILENAME__ = simple_test_server
import sys
import os
sys.path.append(os.getcwd())
from lust import log, server
import time


RUN_DIR=os.path.join(os.getcwd(), "tests")


class SimpleDaemon(server.Simple):

    name = "tests.simple_test_server"

    def before_daemonize(self, args):
        with open("/tmp/before_daemonize.txt", "w") as f:
            f.write("%r" % args)

    def before_jail(self, args):
        with open("/tmp/before_jail.txt", "w") as f:
            f.write("%r" % args)

    def before_drop_privs(self, args):
        assert os.getcwd() == "/", "CWD is not /, chroot failed."

        with open("before_drop_priv.txt", "w") as f:
            f.write("HI")

    def start(self, args):
        while True:
            time.sleep(1)

    def shutdown(self, signal):
        log.info("Shutting down now signal: %d" % signal)


if __name__ == "__main__":
    # if you're on OSX then change this to whatever user nd group
    server = SimpleDaemon(uid='nobody', gid='nogroup', 
                          pid_file_path=RUN_DIR, run_base=RUN_DIR, log_dir=RUN_DIR)
    server.run(sys.argv)


########NEW FILE########
__FILENAME__ = unix_tests
from nose.tools import *
from lust import unix, log
from mock import patch, Mock
import sys
import os
import time
import signal

# These tests use mocks to avoid system calls, with testing that the
# functionality works in the tests/server_tests.py using small server
# that are launched and confirmed work.

def test_make_pid_file_path():
    path = unix.make_pid_file_path("testing")
    assert_equal(path, "/var/run/testing.pid")
    path = unix.make_pid_file_path("testing", pid_file_path="/var/run/stuff")
    assert_equal(path, "/var/run/stuff/testing.pid")


def test_pid_store():
    unix.pid_store("testing", pid_file_path="/tmp")
    assert_equal(os.path.exists("/tmp/testing.pid"), True,
                           "Didn't make /tmp/testing.pid")
    os.unlink("/tmp/testing.pid")

def test_pid_read():
    unix.pid_store("test_pid_read", pid_file_path="/tmp")
    pid = unix.pid_read("test_pid_read", pid_file_path="/tmp")
    assert_equal(pid, os.getpid())
    os.unlink("/tmp/test_pid_read.pid")

def test_still_running():
    unix.pid_store("test_still_running", pid_file_path="/tmp")
    assert_true(unix.still_running("test_still_running", pid_file_path="/tmp"))
    os.unlink("/tmp/test_still_running.pid")

@patch("os.kill", new=Mock(side_effect=OSError))
def test_still_running_stale_process():
    unix.pid_store("test_still_running", pid_file_path="/tmp")
    assert_false(unix.still_running("test_still_running", pid_file_path="/tmp"))
    os.unlink("/tmp/test_still_running.pid")

@patch("lust.unix.still_running", new=Mock(return_value=False))
def test_pid_remove_dead():
    unix.pid_store("test_pid_remove_dead", pid_file_path="/tmp")
    unix.pid_remove_dead("test_pid_remove_dead", pid_file_path="/tmp")
    assert_false(os.path.exists("/tmp/test_pid_remove_dead.pid"))

@patch("lust.unix.still_running", new=Mock(return_value=True))
def test_pid_remove_dead_still_running():
    unix.pid_store("test_pid_remove_dead", pid_file_path="/tmp")
    unix.pid_remove_dead("test_pid_remove_dead", pid_file_path="/tmp")
    assert_true(os.path.exists("/tmp/test_pid_remove_dead.pid"))

@patch("os.kill")
def test_signal_server(os_kill):
    unix.pid_store("test_signal_server", pid_file_path="/tmp")
    unix.kill_server("test_signal_server", pid_file_path="/tmp")
    assert_true(os_kill.called)
    os_kill.reset

    unix.reload_server("test_signal_server", pid_file_path="/tmp")
    assert_true(os_kill.called)
    os_kill.reset

    os.unlink("/tmp/test_signal_server.pid")


@patch("lust.unix.still_running", new=Mock(return_value=False))
@patch("os.fork", new=Mock(return_value=0))
@patch("os.setsid")
@patch("signal.signal")
@patch("os._exit")
def test_daemonize(os__exit, *calls):
    unix.daemonize("test_daemonize", pid_file_path="/tmp")

    for i in calls:
        assert_true(i.called, "Failed to call %r" % i)

    # should not be calling exit
    assert_false(os__exit.called)

def test_daemonize_dont_exit():
    if os.path.exists('/tmp/test_daemonize_no_exit.log'): os.unlink('/tmp/test_daemonize_no_exit.log')
    if os.path.exists('/tmp/test_daemonize_no_exit.pid'): os.unlink('/tmp/test_daemonize_no_exit.pid')

    def main():
        """This will exit the daemon after 4 seconds."""
        log.setup('/tmp/test_daemonize_no_exit.log', force=True)
        for i in range(0, 4):
            log.info("I ran!")
            time.sleep(1)

    unix.daemonize('test_daemonize_no_exit', pid_file_path="/tmp",
                         dont_exit=True, main=main)

    while not unix.still_running('test_daemonize_no_exit', pid_file_path='/tmp'):
        time.sleep(1)

    assert_true(os.path.exists('/tmp/test_daemonize_no_exit.pid'))


@patch("os.chroot")
def test_chroot_jail(chroot_jail):
    unix.chroot_jail()
    assert_true(chroot_jail.called, "Failed to call the chroot jail.")


@patch("pwd.getpwnam")
@patch("grp.getgrnam")
@patch("os.getuid")
def test_get_user_info(os_getuid, *calls):
    # fakes out os.getuid to claim it's running as root
    os_getuid.return_value = 0

    unix.get_user_info('root', 'root')

    # now just confirm all the remaining system calls were called
    for i in calls:
        assert_true(i.called, "Failed to call %r" % i)


@patch("os.setgroups")
@patch("os.setgid")
@patch("os.setuid")
@patch("os.umask")
@patch("os.getuid")
def test_drop_privileges(os_getuid, *calls):
    # fakes out os.getuid to claim it's running as root
    os_getuid.return_value = 0

    unix.drop_privileges(501, 501)

    # now just confirm all the remaining system calls were called
    for i in calls:
        assert_true(i.called, "Failed to call %r" % i)


@patch("os.setuid")
@patch("os.getuid")
def test_drop_privileges_not_root(os_getuid, os_setuid):
    # fakes out os.getuid to claim it's running as root
    os_getuid.return_value = 1000
    unix.drop_privileges(501, 501)

    assert_true(os_getuid.called)
    assert_false(os_setuid.called)


@patch("signal.signal")
def test_register_shutdown(signal_signal):
    def dummy_handler(signal, frame):
        pass

    unix.register_shutdown(dummy_handler)

    assert_true(signal_signal.called)



########NEW FILE########
