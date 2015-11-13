__FILENAME__ = assembler
import sys, zlib

z = zlib.decompressobj()
mainmod = sys.modules[__name__]
while 1:
    name = sys.stdin.readline().strip()
    if name:
        nbytes = int(sys.stdin.readline())
        if verbosity >= 2:
            sys.stderr.write('server: assembling %r (%d bytes)\n'
                             % (name, nbytes))
        content = z.decompress(sys.stdin.read(nbytes))
        exec compile(content, name, "exec")

        # FIXME: this crushes everything into a single module namespace,
        # then makes each of the module names point at this one. Gross.
        assert(name.endswith('.py'))
        modname = name[:-3]
        mainmod.__dict__[modname] = mainmod
    else:
        break

verbose = verbosity
sys.stderr.flush()
sys.stdout.flush()
main()

########NEW FILE########
__FILENAME__ = client
import struct, socket, select, errno, re, signal, time
import compat.ssubprocess as ssubprocess
import helpers, ssnet, ssh, ssyslog
from ssnet import SockWrapper, Handler, Proxy, Mux, MuxWrapper
from helpers import *

_extra_fd = os.open('/dev/null', os.O_RDONLY)

def got_signal(signum, frame):
    log('exiting on signal %d\n' % signum)
    sys.exit(1)


_pidname = None
def check_daemon(pidfile):
    global _pidname
    _pidname = os.path.abspath(pidfile)
    try:
        oldpid = open(_pidname).read(1024)
    except IOError, e:
        if e.errno == errno.ENOENT:
            return  # no pidfile, ok
        else:
            raise Fatal("can't read %s: %s" % (_pidname, e))
    if not oldpid:
        os.unlink(_pidname)
        return  # invalid pidfile, ok
    oldpid = int(oldpid.strip() or 0)
    if oldpid <= 0:
        os.unlink(_pidname)
        return  # invalid pidfile, ok
    try:
        os.kill(oldpid, 0)
    except OSError, e:
        if e.errno == errno.ESRCH:
            os.unlink(_pidname)
            return  # outdated pidfile, ok
        elif e.errno == errno.EPERM:
            pass
        else:
            raise
    raise Fatal("%s: sshuttle is already running (pid=%d)"
                % (_pidname, oldpid))


def daemonize():
    if os.fork():
        os._exit(0)
    os.setsid()
    if os.fork():
        os._exit(0)

    outfd = os.open(_pidname, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0666)
    try:
        os.write(outfd, '%d\n' % os.getpid())
    finally:
        os.close(outfd)
    os.chdir("/")

    # Normal exit when killed, or try/finally won't work and the pidfile won't
    # be deleted.
    signal.signal(signal.SIGTERM, got_signal)
    
    si = open('/dev/null', 'r+')
    os.dup2(si.fileno(), 0)
    os.dup2(si.fileno(), 1)
    si.close()

    ssyslog.stderr_to_syslog()


def daemon_cleanup():
    try:
        os.unlink(_pidname)
    except OSError, e:
        if e.errno == errno.ENOENT:
            pass
        else:
            raise


def original_dst(sock):
    try:
        SO_ORIGINAL_DST = 80
        SOCKADDR_MIN = 16
        sockaddr_in = sock.getsockopt(socket.SOL_IP,
                                      SO_ORIGINAL_DST, SOCKADDR_MIN)
        (proto, port, a,b,c,d) = struct.unpack('!HHBBBB', sockaddr_in[:8])
        assert(socket.htons(proto) == socket.AF_INET)
        ip = '%d.%d.%d.%d' % (a,b,c,d)
        return (ip,port)
    except socket.error, e:
        if e.args[0] == errno.ENOPROTOOPT:
            return sock.getsockname()
        raise


class FirewallClient:
    def __init__(self, port, subnets_include, subnets_exclude, dnsport):
        self.port = port
        self.auto_nets = []
        self.subnets_include = subnets_include
        self.subnets_exclude = subnets_exclude
        self.dnsport = dnsport
        argvbase = ([sys.argv[1], sys.argv[0], sys.argv[1]] +
                    ['-v'] * (helpers.verbose or 0) +
                    ['--firewall', str(port), str(dnsport)])
        if ssyslog._p:
            argvbase += ['--syslog']
        argv_tries = [
            ['sudo', '-p', '[local sudo] Password: '] + argvbase,
            ['su', '-c', ' '.join(argvbase)],
            argvbase
        ]

        # we can't use stdin/stdout=subprocess.PIPE here, as we normally would,
        # because stupid Linux 'su' requires that stdin be attached to a tty.
        # Instead, attach a *bidirectional* socket to its stdout, and use
        # that for talking in both directions.
        (s1,s2) = socket.socketpair()
        def setup():
            # run in the child process
            s2.close()
        e = None
        if os.getuid() == 0:
            argv_tries = argv_tries[-1:]  # last entry only
        for argv in argv_tries:
            try:
                if argv[0] == 'su':
                    sys.stderr.write('[local su] ')
                self.p = ssubprocess.Popen(argv, stdout=s1, preexec_fn=setup)
                e = None
                break
            except OSError, e:
                pass
        self.argv = argv
        s1.close()
        self.pfile = s2.makefile('wb+')
        if e:
            log('Spawning firewall manager: %r\n' % self.argv)
            raise Fatal(e)
        line = self.pfile.readline()
        self.check()
        if line != 'READY\n':
            raise Fatal('%r expected READY, got %r' % (self.argv, line))

    def check(self):
        rv = self.p.poll()
        if rv:
            raise Fatal('%r returned %d' % (self.argv, rv))

    def start(self):
        self.pfile.write('ROUTES\n')
        for (ip,width) in self.subnets_include+self.auto_nets:
            self.pfile.write('%d,0,%s\n' % (width, ip))
        for (ip,width) in self.subnets_exclude:
            self.pfile.write('%d,1,%s\n' % (width, ip))
        self.pfile.write('GO\n')
        self.pfile.flush()
        line = self.pfile.readline()
        self.check()
        if line != 'STARTED\n':
            raise Fatal('%r expected STARTED, got %r' % (self.argv, line))

    def sethostip(self, hostname, ip):
        assert(not re.search(r'[^-\w\.]', hostname))
        assert(not re.search(r'[^0-9.]', ip))
        self.pfile.write('HOST %s,%s\n' % (hostname, ip))
        self.pfile.flush()

    def done(self):
        self.pfile.close()
        rv = self.p.wait()
        if rv == EXITCODE_NEEDS_REBOOT:
            raise FatalNeedsReboot()
        elif rv:
            raise Fatal('cleanup: %r returned %d' % (self.argv, rv))


def onaccept(listener, mux, handlers):
    global _extra_fd
    try:
        sock,srcip = listener.accept()
    except socket.error, e:
        if e.args[0] in [errno.EMFILE, errno.ENFILE]:
            debug1('Rejected incoming connection: too many open files!\n')
            # free up an fd so we can eat the connection
            os.close(_extra_fd)
            try:
                sock,srcip = listener.accept()
                sock.close()
            finally:
                _extra_fd = os.open('/dev/null', os.O_RDONLY)
            return
        else:
            raise
    dstip = original_dst(sock)
    debug1('Accept: %s:%r -> %s:%r.\n' % (srcip[0],srcip[1],
                                          dstip[0],dstip[1]))
    if dstip[1] == listener.getsockname()[1] and islocal(dstip[0]):
        debug1("-- ignored: that's my address!\n")
        sock.close()
        return
    chan = mux.next_channel()
    if not chan:
        log('warning: too many open channels.  Discarded connection.\n')
        sock.close()
        return
    mux.send(chan, ssnet.CMD_CONNECT, '%s,%s' % dstip)
    outwrap = MuxWrapper(mux, chan)
    handlers.append(Proxy(SockWrapper(sock, sock), outwrap))


dnsreqs = {}
def dns_done(chan, data):
    peer,sock,timeout = dnsreqs.get(chan) or (None,None,None)
    debug3('dns_done: channel=%r peer=%r\n' % (chan, peer))
    if peer:
        del dnsreqs[chan]
        debug3('doing sendto %r\n' % (peer,))
        sock.sendto(data, peer)


def ondns(listener, mux, handlers):
    pkt,peer = listener.recvfrom(4096)
    now = time.time()
    if pkt:
        debug1('DNS request from %r: %d bytes\n' % (peer, len(pkt)))
        chan = mux.next_channel()
        dnsreqs[chan] = peer,listener,now+30
        mux.send(chan, ssnet.CMD_DNS_REQ, pkt)
        mux.channels[chan] = lambda cmd,data: dns_done(chan,data)
    for chan,(peer,sock,timeout) in dnsreqs.items():
        if timeout < now:
            del dnsreqs[chan]
    debug3('Remaining DNS requests: %d\n' % len(dnsreqs))


def _main(listener, fw, ssh_cmd, remotename, python, latency_control,
          dnslistener, seed_hosts, auto_nets,
          syslog, daemon):
    handlers = []
    if helpers.verbose >= 1:
        helpers.logprefix = 'c : '
    else:
        helpers.logprefix = 'client: '
    debug1('connecting to server...\n')

    try:
        (serverproc, serversock) = ssh.connect(ssh_cmd, remotename, python,
                        stderr=ssyslog._p and ssyslog._p.stdin,
                        options=dict(latency_control=latency_control))
    except socket.error, e:
        if e.args[0] == errno.EPIPE:
            raise Fatal("failed to establish ssh session (1)")
        else:
            raise
    mux = Mux(serversock, serversock)
    handlers.append(mux)

    expected = 'SSHUTTLE0001'
    
    try:
        v = 'x'
        while v and v != '\0':
            v = serversock.recv(1)
        v = 'x'
        while v and v != '\0':
            v = serversock.recv(1)
        initstring = serversock.recv(len(expected))
    except socket.error, e:
        if e.args[0] == errno.ECONNRESET:
            raise Fatal("failed to establish ssh session (2)")
        else:
            raise
    
    rv = serverproc.poll()
    if rv:
        raise Fatal('server died with error code %d' % rv)
        
    if initstring != expected:
        raise Fatal('expected server init string %r; got %r'
                        % (expected, initstring))
    debug1('connected.\n')
    print 'Connected.'
    sys.stdout.flush()
    if daemon:
        daemonize()
        log('daemonizing (%s).\n' % _pidname)
    elif syslog:
        debug1('switching to syslog.\n')
        ssyslog.stderr_to_syslog()

    def onroutes(routestr):
        if auto_nets:
            for line in routestr.strip().split('\n'):
                (ip,width) = line.split(',', 1)
                fw.auto_nets.append((ip,int(width)))

        # we definitely want to do this *after* starting ssh, or we might end
        # up intercepting the ssh connection!
        #
        # Moreover, now that we have the --auto-nets option, we have to wait
        # for the server to send us that message anyway.  Even if we haven't
        # set --auto-nets, we might as well wait for the message first, then
        # ignore its contents.
        mux.got_routes = None
        fw.start()
    mux.got_routes = onroutes

    def onhostlist(hostlist):
        debug2('got host list: %r\n' % hostlist)
        for line in hostlist.strip().split():
            if line:
                name,ip = line.split(',', 1)
                fw.sethostip(name, ip)
    mux.got_host_list = onhostlist

    handlers.append(Handler([listener], lambda: onaccept(listener, mux, handlers)))

    if dnslistener:
        handlers.append(Handler([dnslistener], lambda: ondns(dnslistener, mux, handlers)))

    if seed_hosts != None:
        debug1('seed_hosts: %r\n' % seed_hosts)
        mux.send(0, ssnet.CMD_HOST_REQ, '\n'.join(seed_hosts))
    
    while 1:
        rv = serverproc.poll()
        if rv:
            raise Fatal('server died with error code %d' % rv)
        
        ssnet.runonce(handlers, mux)
        if latency_control:
            mux.check_fullness()
        mux.callback()


def main(listenip, ssh_cmd, remotename, python, latency_control, dns,
         seed_hosts, auto_nets,
         subnets_include, subnets_exclude, syslog, daemon, pidfile):
    if syslog:
        ssyslog.start_syslog()
    if daemon:
        try:
            check_daemon(pidfile)
        except Fatal, e:
            log("%s\n" % e)
            return 5
    debug1('Starting sshuttle proxy.\n')
    
    if listenip[1]:
        ports = [listenip[1]]
    else:
        ports = xrange(12300,9000,-1)
    last_e = None
    bound = False
    debug2('Binding:')
    for port in ports:
        debug2(' %d' % port)
        listener = socket.socket()
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        dnslistener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        dnslistener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind((listenip[0], port))
            dnslistener.bind((listenip[0], port))
            bound = True
            break
        except socket.error, e:
            last_e = e
    debug2('\n')
    if not bound:
        assert(last_e)
        raise last_e
    listener.listen(10)
    listenip = listener.getsockname()
    debug1('Listening on %r.\n' % (listenip,))

    if dns:
        dnsip = dnslistener.getsockname()
        debug1('DNS listening on %r.\n' % (dnsip,))
        dnsport = dnsip[1]
    else:
        dnsport = 0
        dnslistener = None

    fw = FirewallClient(listenip[1], subnets_include, subnets_exclude, dnsport)
    
    try:
        return _main(listener, fw, ssh_cmd, remotename,
                     python, latency_control, dnslistener,
                     seed_hosts, auto_nets, syslog, daemon)
    finally:
        try:
            if daemon:
                # it's not our child anymore; can't waitpid
                fw.p.returncode = 0
            fw.done()
        finally:
            if daemon:
                daemon_cleanup()

########NEW FILE########
__FILENAME__ = ssubprocess
# subprocess - Subprocesses with accessible I/O streams
#
# For more information about this module, see PEP 324.
#
# This module should remain compatible with Python 2.2, see PEP 291.
#
# Copyright (c) 2003-2005 by Peter Astrand <astrand@lysator.liu.se>
#
# Licensed to PSF under a Contributor Agreement.
# See http://www.python.org/2.4/license for licensing details.

r"""subprocess - Subprocesses with accessible I/O streams

This module allows you to spawn processes, connect to their
input/output/error pipes, and obtain their return codes.  This module
intends to replace several other, older modules and functions, like:

os.system
os.spawn*
os.popen*
popen2.*
commands.*

Information about how the subprocess module can be used to replace these
modules and functions can be found below.



Using the subprocess module
===========================
This module defines one class called Popen:

class Popen(args, bufsize=0, executable=None,
            stdin=None, stdout=None, stderr=None,
            preexec_fn=None, close_fds=False, shell=False,
            cwd=None, env=None, universal_newlines=False,
            startupinfo=None, creationflags=0):


Arguments are:

args should be a string, or a sequence of program arguments.  The
program to execute is normally the first item in the args sequence or
string, but can be explicitly set by using the executable argument.

On UNIX, with shell=False (default): In this case, the Popen class
uses os.execvp() to execute the child program.  args should normally
be a sequence.  A string will be treated as a sequence with the string
as the only item (the program to execute).

On UNIX, with shell=True: If args is a string, it specifies the
command string to execute through the shell.  If args is a sequence,
the first item specifies the command string, and any additional items
will be treated as additional shell arguments.

On Windows: the Popen class uses CreateProcess() to execute the child
program, which operates on strings.  If args is a sequence, it will be
converted to a string using the list2cmdline method.  Please note that
not all MS Windows applications interpret the command line the same
way: The list2cmdline is designed for applications using the same
rules as the MS C runtime.

bufsize, if given, has the same meaning as the corresponding argument
to the built-in open() function: 0 means unbuffered, 1 means line
buffered, any other positive value means use a buffer of
(approximately) that size.  A negative bufsize means to use the system
default, which usually means fully buffered.  The default value for
bufsize is 0 (unbuffered).

stdin, stdout and stderr specify the executed programs' standard
input, standard output and standard error file handles, respectively.
Valid values are PIPE, an existing file descriptor (a positive
integer), an existing file object, and None.  PIPE indicates that a
new pipe to the child should be created.  With None, no redirection
will occur; the child's file handles will be inherited from the
parent.  Additionally, stderr can be STDOUT, which indicates that the
stderr data from the applications should be captured into the same
file handle as for stdout.

If preexec_fn is set to a callable object, this object will be called
in the child process just before the child is executed.

If close_fds is true, all file descriptors except 0, 1 and 2 will be
closed before the child process is executed.

if shell is true, the specified command will be executed through the
shell.

If cwd is not None, the current directory will be changed to cwd
before the child is executed.

If env is not None, it defines the environment variables for the new
process.

If universal_newlines is true, the file objects stdout and stderr are
opened as a text files, but lines may be terminated by any of '\n',
the Unix end-of-line convention, '\r', the Macintosh convention or
'\r\n', the Windows convention.  All of these external representations
are seen as '\n' by the Python program.  Note: This feature is only
available if Python is built with universal newline support (the
default).  Also, the newlines attribute of the file objects stdout,
stdin and stderr are not updated by the communicate() method.

The startupinfo and creationflags, if given, will be passed to the
underlying CreateProcess() function.  They can specify things such as
appearance of the main window and priority for the new process.
(Windows only)


This module also defines two shortcut functions:

call(*popenargs, **kwargs):
    Run command with arguments.  Wait for command to complete, then
    return the returncode attribute.

    The arguments are the same as for the Popen constructor.  Example:

    retcode = call(["ls", "-l"])

check_call(*popenargs, **kwargs):
    Run command with arguments.  Wait for command to complete.  If the
    exit code was zero then return, otherwise raise
    CalledProcessError.  The CalledProcessError object will have the
    return code in the returncode attribute.

    The arguments are the same as for the Popen constructor.  Example:

    check_call(["ls", "-l"])

Exceptions
----------
Exceptions raised in the child process, before the new program has
started to execute, will be re-raised in the parent.  Additionally,
the exception object will have one extra attribute called
'child_traceback', which is a string containing traceback information
from the childs point of view.

The most common exception raised is OSError.  This occurs, for
example, when trying to execute a non-existent file.  Applications
should prepare for OSErrors.

A ValueError will be raised if Popen is called with invalid arguments.

check_call() will raise CalledProcessError, if the called process
returns a non-zero return code.


Security
--------
Unlike some other popen functions, this implementation will never call
/bin/sh implicitly.  This means that all characters, including shell
metacharacters, can safely be passed to child processes.


Popen objects
=============
Instances of the Popen class have the following methods:

poll()
    Check if child process has terminated.  Returns returncode
    attribute.

wait()
    Wait for child process to terminate.  Returns returncode attribute.

communicate(input=None)
    Interact with process: Send data to stdin.  Read data from stdout
    and stderr, until end-of-file is reached.  Wait for process to
    terminate.  The optional input argument should be a string to be
    sent to the child process, or None, if no data should be sent to
    the child.

    communicate() returns a tuple (stdout, stderr).

    Note: The data read is buffered in memory, so do not use this
    method if the data size is large or unlimited.

The following attributes are also available:

stdin
    If the stdin argument is PIPE, this attribute is a file object
    that provides input to the child process.  Otherwise, it is None.

stdout
    If the stdout argument is PIPE, this attribute is a file object
    that provides output from the child process.  Otherwise, it is
    None.

stderr
    If the stderr argument is PIPE, this attribute is file object that
    provides error output from the child process.  Otherwise, it is
    None.

pid
    The process ID of the child process.

returncode
    The child return code.  A None value indicates that the process
    hasn't terminated yet.  A negative value -N indicates that the
    child was terminated by signal N (UNIX only).


Replacing older functions with the subprocess module
====================================================
In this section, "a ==> b" means that b can be used as a replacement
for a.

Note: All functions in this section fail (more or less) silently if
the executed program cannot be found; this module raises an OSError
exception.

In the following examples, we assume that the subprocess module is
imported with "from subprocess import *".


Replacing /bin/sh shell backquote
---------------------------------
output=`mycmd myarg`
==>
output = Popen(["mycmd", "myarg"], stdout=PIPE).communicate()[0]


Replacing shell pipe line
-------------------------
output=`dmesg | grep hda`
==>
p1 = Popen(["dmesg"], stdout=PIPE)
p2 = Popen(["grep", "hda"], stdin=p1.stdout, stdout=PIPE)
output = p2.communicate()[0]


Replacing os.system()
---------------------
sts = os.system("mycmd" + " myarg")
==>
p = Popen("mycmd" + " myarg", shell=True)
pid, sts = os.waitpid(p.pid, 0)

Note:

* Calling the program through the shell is usually not required.

* It's easier to look at the returncode attribute than the
  exitstatus.

A more real-world example would look like this:

try:
    retcode = call("mycmd" + " myarg", shell=True)
    if retcode < 0:
        print >>sys.stderr, "Child was terminated by signal", -retcode
    else:
        print >>sys.stderr, "Child returned", retcode
except OSError, e:
    print >>sys.stderr, "Execution failed:", e


Replacing os.spawn*
-------------------
P_NOWAIT example:

pid = os.spawnlp(os.P_NOWAIT, "/bin/mycmd", "mycmd", "myarg")
==>
pid = Popen(["/bin/mycmd", "myarg"]).pid


P_WAIT example:

retcode = os.spawnlp(os.P_WAIT, "/bin/mycmd", "mycmd", "myarg")
==>
retcode = call(["/bin/mycmd", "myarg"])


Vector example:

os.spawnvp(os.P_NOWAIT, path, args)
==>
Popen([path] + args[1:])


Environment example:

os.spawnlpe(os.P_NOWAIT, "/bin/mycmd", "mycmd", "myarg", env)
==>
Popen(["/bin/mycmd", "myarg"], env={"PATH": "/usr/bin"})


Replacing os.popen*
-------------------
pipe = os.popen(cmd, mode='r', bufsize)
==>
pipe = Popen(cmd, shell=True, bufsize=bufsize, stdout=PIPE).stdout

pipe = os.popen(cmd, mode='w', bufsize)
==>
pipe = Popen(cmd, shell=True, bufsize=bufsize, stdin=PIPE).stdin


(child_stdin, child_stdout) = os.popen2(cmd, mode, bufsize)
==>
p = Popen(cmd, shell=True, bufsize=bufsize,
          stdin=PIPE, stdout=PIPE, close_fds=True)
(child_stdin, child_stdout) = (p.stdin, p.stdout)


(child_stdin,
 child_stdout,
 child_stderr) = os.popen3(cmd, mode, bufsize)
==>
p = Popen(cmd, shell=True, bufsize=bufsize,
          stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
(child_stdin,
 child_stdout,
 child_stderr) = (p.stdin, p.stdout, p.stderr)


(child_stdin, child_stdout_and_stderr) = os.popen4(cmd, mode, bufsize)
==>
p = Popen(cmd, shell=True, bufsize=bufsize,
          stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
(child_stdin, child_stdout_and_stderr) = (p.stdin, p.stdout)


Replacing popen2.*
------------------
Note: If the cmd argument to popen2 functions is a string, the command
is executed through /bin/sh.  If it is a list, the command is directly
executed.

(child_stdout, child_stdin) = popen2.popen2("somestring", bufsize, mode)
==>
p = Popen(["somestring"], shell=True, bufsize=bufsize
          stdin=PIPE, stdout=PIPE, close_fds=True)
(child_stdout, child_stdin) = (p.stdout, p.stdin)


(child_stdout, child_stdin) = popen2.popen2(["mycmd", "myarg"], bufsize, mode)
==>
p = Popen(["mycmd", "myarg"], bufsize=bufsize,
          stdin=PIPE, stdout=PIPE, close_fds=True)
(child_stdout, child_stdin) = (p.stdout, p.stdin)

The popen2.Popen3 and popen2.Popen4 basically works as subprocess.Popen,
except that:

* subprocess.Popen raises an exception if the execution fails
* the capturestderr argument is replaced with the stderr argument.
* stdin=PIPE and stdout=PIPE must be specified.
* popen2 closes all filedescriptors by default, but you have to specify
  close_fds=True with subprocess.Popen.
"""

import sys
mswindows = (sys.platform == "win32")

import os
import types
import traceback
import gc
import signal

# Exception classes used by this module.
class CalledProcessError(Exception):
    """This exception is raised when a process run by check_call() returns
    a non-zero exit status.  The exit status will be stored in the
    returncode attribute."""
    def __init__(self, returncode, cmd):
        self.returncode = returncode
        self.cmd = cmd
    def __str__(self):
        return "Command '%s' returned non-zero exit status %d" % (self.cmd, self.returncode)


if mswindows:
    import threading
    import msvcrt
    if 0: # <-- change this to use pywin32 instead of the _subprocess driver
        import pywintypes
        from win32api import GetStdHandle, STD_INPUT_HANDLE, \
                             STD_OUTPUT_HANDLE, STD_ERROR_HANDLE
        from win32api import GetCurrentProcess, DuplicateHandle, \
                             GetModuleFileName, GetVersion
        from win32con import DUPLICATE_SAME_ACCESS, SW_HIDE
        from win32pipe import CreatePipe
        from win32process import CreateProcess, STARTUPINFO, \
                                 GetExitCodeProcess, STARTF_USESTDHANDLES, \
                                 STARTF_USESHOWWINDOW, CREATE_NEW_CONSOLE
        from win32process import TerminateProcess
        from win32event import WaitForSingleObject, INFINITE, WAIT_OBJECT_0
    else:
        from _subprocess import *
        class STARTUPINFO:
            dwFlags = 0
            hStdInput = None
            hStdOutput = None
            hStdError = None
            wShowWindow = 0
        class pywintypes:
            error = IOError
else:
    import select
    import errno
    import fcntl
    import pickle

__all__ = ["Popen", "PIPE", "STDOUT", "call", "check_call", "CalledProcessError"]

try:
    MAXFD = os.sysconf("SC_OPEN_MAX")
except:
    MAXFD = 256

# True/False does not exist on 2.2.0
#try:
#    False
#except NameError:
#    False = 0
#    True = 1

_active = []

def _cleanup():
    for inst in _active[:]:
        if inst._internal_poll(_deadstate=sys.maxint) >= 0:
            try:
                _active.remove(inst)
            except ValueError:
                # This can happen if two threads create a new Popen instance.
                # It's harmless that it was already removed, so ignore.
                pass

PIPE = -1
STDOUT = -2


def call(*popenargs, **kwargs):
    """Run command with arguments.  Wait for command to complete, then
    return the returncode attribute.

    The arguments are the same as for the Popen constructor.  Example:

    retcode = call(["ls", "-l"])
    """
    return Popen(*popenargs, **kwargs).wait()


def check_call(*popenargs, **kwargs):
    """Run command with arguments.  Wait for command to complete.  If
    the exit code was zero then return, otherwise raise
    CalledProcessError.  The CalledProcessError object will have the
    return code in the returncode attribute.

    The arguments are the same as for the Popen constructor.  Example:

    check_call(["ls", "-l"])
    """
    retcode = call(*popenargs, **kwargs)
    cmd = kwargs.get("args")
    if cmd is None:
        cmd = popenargs[0]
    if retcode:
        raise CalledProcessError(retcode, cmd)
    return retcode


def list2cmdline(seq):
    """
    Translate a sequence of arguments into a command line
    string, using the same rules as the MS C runtime:

    1) Arguments are delimited by white space, which is either a
       space or a tab.

    2) A string surrounded by double quotation marks is
       interpreted as a single argument, regardless of white space
       or pipe characters contained within.  A quoted string can be
       embedded in an argument.

    3) A double quotation mark preceded by a backslash is
       interpreted as a literal double quotation mark.

    4) Backslashes are interpreted literally, unless they
       immediately precede a double quotation mark.

    5) If backslashes immediately precede a double quotation mark,
       every pair of backslashes is interpreted as a literal
       backslash.  If the number of backslashes is odd, the last
       backslash escapes the next double quotation mark as
       described in rule 3.
    """

    # See
    # http://msdn.microsoft.com/library/en-us/vccelng/htm/progs_12.asp
    result = []
    needquote = False
    for arg in seq:
        bs_buf = []

        # Add a space to separate this argument from the others
        if result:
            result.append(' ')

        needquote = (" " in arg) or ("\t" in arg) or ("|" in arg) or not arg
        if needquote:
            result.append('"')

        for c in arg:
            if c == '\\':
                # Don't know if we need to double yet.
                bs_buf.append(c)
            elif c == '"':
                # Double backslashes.
                result.append('\\' * len(bs_buf)*2)
                bs_buf = []
                result.append('\\"')
            else:
                # Normal char
                if bs_buf:
                    result.extend(bs_buf)
                    bs_buf = []
                result.append(c)

        # Add remaining backslashes, if any.
        if bs_buf:
            result.extend(bs_buf)

        if needquote:
            result.extend(bs_buf)
            result.append('"')

    return ''.join(result)


def _closerange(start, max):
    try:
        os.closerange(start, max)
    except AttributeError:
        for i in xrange(start, max):
            try:
                os.close(i)
            except:
                pass


class Popen(object):
    def __init__(self, args, bufsize=0, executable=None,
                 stdin=None, stdout=None, stderr=None,
                 preexec_fn=None, close_fds=False, shell=False,
                 cwd=None, env=None, universal_newlines=False,
                 startupinfo=None, creationflags=0):
        """Create new Popen instance."""
        _cleanup()

        self._child_created = False
        if not isinstance(bufsize, (int, long)):
            raise TypeError("bufsize must be an integer")

        if mswindows:
            if preexec_fn is not None:
                raise ValueError("preexec_fn is not supported on Windows "
                                 "platforms")
            if close_fds and (stdin is not None or stdout is not None or
                              stderr is not None):
                raise ValueError("close_fds is not supported on Windows "
                                 "platforms if you redirect stdin/stdout/stderr")
        else:
            # POSIX
            if startupinfo is not None:
                raise ValueError("startupinfo is only supported on Windows "
                                 "platforms")
            if creationflags != 0:
                raise ValueError("creationflags is only supported on Windows "
                                 "platforms")

        self.stdin = None
        self.stdout = None
        self.stderr = None
        self.pid = None
        self.returncode = None
        self.universal_newlines = universal_newlines

        # Input and output objects. The general principle is like
        # this:
        #
        # Parent                   Child
        # ------                   -----
        # p2cwrite   ---stdin--->  p2cread
        # c2pread    <--stdout---  c2pwrite
        # errread    <--stderr---  errwrite
        #
        # On POSIX, the child objects are file descriptors.  On
        # Windows, these are Windows file handles.  The parent objects
        # are file descriptors on both platforms.  The parent objects
        # are None when not using PIPEs. The child objects are None
        # when not redirecting.

        (p2cread, p2cwrite,
         c2pread, c2pwrite,
         errread, errwrite) = self._get_handles(stdin, stdout, stderr)

        self._execute_child(args, executable, preexec_fn, close_fds,
                            cwd, env, universal_newlines,
                            startupinfo, creationflags, shell,
                            p2cread, p2cwrite,
                            c2pread, c2pwrite,
                            errread, errwrite)

        # On Windows, you cannot just redirect one or two handles: You
        # either have to redirect all three or none. If the subprocess
        # user has only redirected one or two handles, we are
        # automatically creating PIPEs for the rest. We should close
        # these after the process is started. See bug #1124861.
        if mswindows:
            if stdin is None and p2cwrite is not None:
                os.close(p2cwrite)
                p2cwrite = None
            if stdout is None and c2pread is not None:
                os.close(c2pread)
                c2pread = None
            if stderr is None and errread is not None:
                os.close(errread)
                errread = None

        if p2cwrite is not None:
            self.stdin = os.fdopen(p2cwrite, 'wb', bufsize)
        if c2pread is not None:
            if universal_newlines:
                self.stdout = os.fdopen(c2pread, 'rU', bufsize)
            else:
                self.stdout = os.fdopen(c2pread, 'rb', bufsize)
        if errread is not None:
            if universal_newlines:
                self.stderr = os.fdopen(errread, 'rU', bufsize)
            else:
                self.stderr = os.fdopen(errread, 'rb', bufsize)


    def _translate_newlines(self, data):
        data = data.replace("\r\n", "\n")
        data = data.replace("\r", "\n")
        return data


    def __del__(self, sys=sys):
        if not self._child_created:
            # We didn't get to successfully create a child process.
            return
        # In case the child hasn't been waited on, check if it's done.
        self._internal_poll(_deadstate=sys.maxint)
        if self.returncode is None and _active is not None:
            # Child is still running, keep us alive until we can wait on it.
            _active.append(self)


    def communicate(self, input=None):
        """Interact with process: Send data to stdin.  Read data from
        stdout and stderr, until end-of-file is reached.  Wait for
        process to terminate.  The optional input argument should be a
        string to be sent to the child process, or None, if no data
        should be sent to the child.

        communicate() returns a tuple (stdout, stderr)."""

        # Optimization: If we are only using one pipe, or no pipe at
        # all, using select() or threads is unnecessary.
        if [self.stdin, self.stdout, self.stderr].count(None) >= 2:
            stdout = None
            stderr = None
            if self.stdin:
                if input:
                    self.stdin.write(input)
                self.stdin.close()
            elif self.stdout:
                stdout = self.stdout.read()
                self.stdout.close()
            elif self.stderr:
                stderr = self.stderr.read()
                self.stderr.close()
            self.wait()
            return (stdout, stderr)

        return self._communicate(input)


    def poll(self):
        return self._internal_poll()


    if mswindows:
        #
        # Windows methods
        #
        def _get_handles(self, stdin, stdout, stderr):
            """Construct and return tupel with IO objects:
            p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite
            """
            if stdin is None and stdout is None and stderr is None:
                return (None, None, None, None, None, None)

            p2cread, p2cwrite = None, None
            c2pread, c2pwrite = None, None
            errread, errwrite = None, None

            if stdin is None:
                p2cread = GetStdHandle(STD_INPUT_HANDLE)
            if p2cread is not None:
                pass
            elif stdin is None or stdin == PIPE:
                p2cread, p2cwrite = CreatePipe(None, 0)
                # Detach and turn into fd
                p2cwrite = p2cwrite.Detach()
                p2cwrite = msvcrt.open_osfhandle(p2cwrite, 0)
            elif isinstance(stdin, int):
                p2cread = msvcrt.get_osfhandle(stdin)
            else:
                # Assuming file-like object
                p2cread = msvcrt.get_osfhandle(stdin.fileno())
            p2cread = self._make_inheritable(p2cread)

            if stdout is None:
                c2pwrite = GetStdHandle(STD_OUTPUT_HANDLE)
            if c2pwrite is not None:
                pass
            elif stdout is None or stdout == PIPE:
                c2pread, c2pwrite = CreatePipe(None, 0)
                # Detach and turn into fd
                c2pread = c2pread.Detach()
                c2pread = msvcrt.open_osfhandle(c2pread, 0)
            elif isinstance(stdout, int):
                c2pwrite = msvcrt.get_osfhandle(stdout)
            else:
                # Assuming file-like object
                c2pwrite = msvcrt.get_osfhandle(stdout.fileno())
            c2pwrite = self._make_inheritable(c2pwrite)

            if stderr is None:
                errwrite = GetStdHandle(STD_ERROR_HANDLE)
            if errwrite is not None:
                pass
            elif stderr is None or stderr == PIPE:
                errread, errwrite = CreatePipe(None, 0)
                # Detach and turn into fd
                errread = errread.Detach()
                errread = msvcrt.open_osfhandle(errread, 0)
            elif stderr == STDOUT:
                errwrite = c2pwrite
            elif isinstance(stderr, int):
                errwrite = msvcrt.get_osfhandle(stderr)
            else:
                # Assuming file-like object
                errwrite = msvcrt.get_osfhandle(stderr.fileno())
            errwrite = self._make_inheritable(errwrite)

            return (p2cread, p2cwrite,
                    c2pread, c2pwrite,
                    errread, errwrite)


        def _make_inheritable(self, handle):
            """Return a duplicate of handle, which is inheritable"""
            return DuplicateHandle(GetCurrentProcess(), handle,
                                   GetCurrentProcess(), 0, 1,
                                   DUPLICATE_SAME_ACCESS)


        def _find_w9xpopen(self):
            """Find and return absolut path to w9xpopen.exe"""
            w9xpopen = os.path.join(os.path.dirname(GetModuleFileName(0)),
                                    "w9xpopen.exe")
            if not os.path.exists(w9xpopen):
                # Eeek - file-not-found - possibly an embedding
                # situation - see if we can locate it in sys.exec_prefix
                w9xpopen = os.path.join(os.path.dirname(sys.exec_prefix),
                                        "w9xpopen.exe")
                if not os.path.exists(w9xpopen):
                    raise RuntimeError("Cannot locate w9xpopen.exe, which is "
                                       "needed for Popen to work with your "
                                       "shell or platform.")
            return w9xpopen


        def _execute_child(self, args, executable, preexec_fn, close_fds,
                           cwd, env, universal_newlines,
                           startupinfo, creationflags, shell,
                           p2cread, p2cwrite,
                           c2pread, c2pwrite,
                           errread, errwrite):
            """Execute program (MS Windows version)"""

            if not isinstance(args, types.StringTypes):
                args = list2cmdline(args)

            # Process startup details
            if startupinfo is None:
                startupinfo = STARTUPINFO()
            if None not in (p2cread, c2pwrite, errwrite):
                startupinfo.dwFlags |= STARTF_USESTDHANDLES
                startupinfo.hStdInput = p2cread
                startupinfo.hStdOutput = c2pwrite
                startupinfo.hStdError = errwrite

            if shell:
                startupinfo.dwFlags |= STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = SW_HIDE
                comspec = os.environ.get("COMSPEC", "cmd.exe")
                args = comspec + " /c " + args
                if (GetVersion() >= 0x80000000L or
                        os.path.basename(comspec).lower() == "command.com"):
                    # Win9x, or using command.com on NT. We need to
                    # use the w9xpopen intermediate program. For more
                    # information, see KB Q150956
                    # (http://web.archive.org/web/20011105084002/http://support.microsoft.com/support/kb/articles/Q150/9/56.asp)
                    w9xpopen = self._find_w9xpopen()
                    args = '"%s" %s' % (w9xpopen, args)
                    # Not passing CREATE_NEW_CONSOLE has been known to
                    # cause random failures on win9x.  Specifically a
                    # dialog: "Your program accessed mem currently in
                    # use at xxx" and a hopeful warning about the
                    # stability of your system.  Cost is Ctrl+C wont
                    # kill children.
                    creationflags |= CREATE_NEW_CONSOLE

            # Start the process
            try:
                hp, ht, pid, tid = CreateProcess(executable, args,
                                         # no special security
                                         None, None,
                                         int(not close_fds),
                                         creationflags,
                                         env,
                                         cwd,
                                         startupinfo)
            except pywintypes.error, e:
                # Translate pywintypes.error to WindowsError, which is
                # a subclass of OSError.  FIXME: We should really
                # translate errno using _sys_errlist (or simliar), but
                # how can this be done from Python?
                raise WindowsError(*e.args)

            # Retain the process handle, but close the thread handle
            self._child_created = True
            self._handle = hp
            self.pid = pid
            ht.Close()

            # Child is launched. Close the parent's copy of those pipe
            # handles that only the child should have open.  You need
            # to make sure that no handles to the write end of the
            # output pipe are maintained in this process or else the
            # pipe will not close when the child process exits and the
            # ReadFile will hang.
            if p2cread is not None:
                p2cread.Close()
            if c2pwrite is not None:
                c2pwrite.Close()
            if errwrite is not None:
                errwrite.Close()


        def _internal_poll(self, _deadstate=None):
            """Check if child process has terminated.  Returns returncode
            attribute."""
            if self.returncode is None:
                if WaitForSingleObject(self._handle, 0) == WAIT_OBJECT_0:
                    self.returncode = GetExitCodeProcess(self._handle)
            return self.returncode


        def wait(self):
            """Wait for child process to terminate.  Returns returncode
            attribute."""
            if self.returncode is None:
                obj = WaitForSingleObject(self._handle, INFINITE)
                self.returncode = GetExitCodeProcess(self._handle)
            return self.returncode


        def _readerthread(self, fh, buffer):
            buffer.append(fh.read())


        def _communicate(self, input):
            stdout = None # Return
            stderr = None # Return

            if self.stdout:
                stdout = []
                stdout_thread = threading.Thread(target=self._readerthread,
                                                 args=(self.stdout, stdout))
                stdout_thread.setDaemon(True)
                stdout_thread.start()
            if self.stderr:
                stderr = []
                stderr_thread = threading.Thread(target=self._readerthread,
                                                 args=(self.stderr, stderr))
                stderr_thread.setDaemon(True)
                stderr_thread.start()

            if self.stdin:
                if input is not None:
                    self.stdin.write(input)
                self.stdin.close()

            if self.stdout:
                stdout_thread.join()
            if self.stderr:
                stderr_thread.join()

            # All data exchanged.  Translate lists into strings.
            if stdout is not None:
                stdout = stdout[0]
            if stderr is not None:
                stderr = stderr[0]

            # Translate newlines, if requested.  We cannot let the file
            # object do the translation: It is based on stdio, which is
            # impossible to combine with select (unless forcing no
            # buffering).
            if self.universal_newlines and hasattr(file, 'newlines'):
                if stdout:
                    stdout = self._translate_newlines(stdout)
                if stderr:
                    stderr = self._translate_newlines(stderr)

            self.wait()
            return (stdout, stderr)

        def send_signal(self, sig):
            """Send a signal to the process
            """
            if sig == signal.SIGTERM:
                self.terminate()
            else:
                raise ValueError("Only SIGTERM is supported on Windows")

        def terminate(self):
            """Terminates the process
            """
            TerminateProcess(self._handle, 1)

        kill = terminate

    else:
        #
        # POSIX methods
        #
        def _get_handles(self, stdin, stdout, stderr):
            """Construct and return tupel with IO objects:
            p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite
            """
            p2cread, p2cwrite = None, None
            c2pread, c2pwrite = None, None
            errread, errwrite = None, None

            if stdin is None:
                pass
            elif stdin == PIPE:
                p2cread, p2cwrite = os.pipe()
            elif isinstance(stdin, int):
                p2cread = stdin
            else:
                # Assuming file-like object
                p2cread = stdin.fileno()

            if stdout is None:
                pass
            elif stdout == PIPE:
                c2pread, c2pwrite = os.pipe()
            elif isinstance(stdout, int):
                c2pwrite = stdout
            else:
                # Assuming file-like object
                c2pwrite = stdout.fileno()

            if stderr is None:
                pass
            elif stderr == PIPE:
                errread, errwrite = os.pipe()
            elif stderr == STDOUT:
                errwrite = c2pwrite
            elif isinstance(stderr, int):
                errwrite = stderr
            else:
                # Assuming file-like object
                errwrite = stderr.fileno()

            return (p2cread, p2cwrite,
                    c2pread, c2pwrite,
                    errread, errwrite)


        def _set_cloexec_flag(self, fd):
            try:
                cloexec_flag = fcntl.FD_CLOEXEC
            except AttributeError:
                cloexec_flag = 1

            old = fcntl.fcntl(fd, fcntl.F_GETFD)
            fcntl.fcntl(fd, fcntl.F_SETFD, old | cloexec_flag)


        def _close_fds(self, but):
            _closerange(3, but)
            _closerange(but + 1, MAXFD)


        def _execute_child(self, args, executable, preexec_fn, close_fds,
                           cwd, env, universal_newlines,
                           startupinfo, creationflags, shell,
                           p2cread, p2cwrite,
                           c2pread, c2pwrite,
                           errread, errwrite):
            """Execute program (POSIX version)"""

            if isinstance(args, types.StringTypes):
                args = [args]
            else:
                args = list(args)

            if shell:
                args = ["/bin/sh", "-c"] + args

            if executable is None:
                executable = args[0]

            # For transferring possible exec failure from child to parent
            # The first char specifies the exception type: 0 means
            # OSError, 1 means some other error.
            errpipe_read, errpipe_write = os.pipe()
            self._set_cloexec_flag(errpipe_write)

            gc_was_enabled = gc.isenabled()
            # Disable gc to avoid bug where gc -> file_dealloc ->
            # write to stderr -> hang.  http://bugs.python.org/issue1336
            gc.disable()
            try:
                self.pid = os.fork()
            except:
                if gc_was_enabled:
                    gc.enable()
                raise
            self._child_created = True
            if self.pid == 0:
                # Child
                try:
                    # Close parent's pipe ends
                    if p2cwrite is not None:
                        os.close(p2cwrite)
                    if c2pread is not None:
                        os.close(c2pread)
                    if errread is not None:
                        os.close(errread)
                    os.close(errpipe_read)

                    # Dup fds for child
                    if p2cread is not None:
                        os.dup2(p2cread, 0)
                    if c2pwrite is not None:
                        os.dup2(c2pwrite, 1)
                    if errwrite is not None:
                        os.dup2(errwrite, 2)

                    # Close pipe fds.  Make sure we don't close the same
                    # fd more than once, or standard fds.
                    if p2cread is not None and p2cread not in (0,):
                        os.close(p2cread)
                    if c2pwrite is not None and c2pwrite not in (p2cread, 1):
                        os.close(c2pwrite)
                    if errwrite is not None and errwrite not in (p2cread, c2pwrite, 2):
                        os.close(errwrite)

                    # Close all other fds, if asked for
                    if close_fds:
                        self._close_fds(but=errpipe_write)

                    if cwd is not None:
                        os.chdir(cwd)

                    if preexec_fn:
                        preexec_fn()

                    if env is None:
                        os.execvp(executable, args)
                    else:
                        os.execvpe(executable, args, env)

                except:
                    exc_type, exc_value, tb = sys.exc_info()
                    # Save the traceback and attach it to the exception object
                    exc_lines = traceback.format_exception(exc_type,
                                                           exc_value,
                                                           tb)
                    exc_value.child_traceback = ''.join(exc_lines)
                    os.write(errpipe_write, pickle.dumps(exc_value))

                # This exitcode won't be reported to applications, so it
                # really doesn't matter what we return.
                os._exit(255)

            # Parent
            if gc_was_enabled:
                gc.enable()
            os.close(errpipe_write)
            if p2cread is not None and p2cwrite is not None:
                os.close(p2cread)
            if c2pwrite is not None and c2pread is not None:
                os.close(c2pwrite)
            if errwrite is not None and errread is not None:
                os.close(errwrite)

            # Wait for exec to fail or succeed; possibly raising exception
            data = os.read(errpipe_read, 1048576) # Exceptions limited to 1 MB
            os.close(errpipe_read)
            if data != "":
                os.waitpid(self.pid, 0)
                child_exception = pickle.loads(data)
                raise child_exception


        def _handle_exitstatus(self, sts):
            if os.WIFSIGNALED(sts):
                self.returncode = -os.WTERMSIG(sts)
            elif os.WIFEXITED(sts):
                self.returncode = os.WEXITSTATUS(sts)
            else:
                # Should never happen
                raise RuntimeError("Unknown child exit status!")


        def _internal_poll(self, _deadstate=None):
            """Check if child process has terminated.  Returns returncode
            attribute."""
            if self.returncode is None:
                try:
                    pid, sts = os.waitpid(self.pid, os.WNOHANG)
                    if pid == self.pid:
                        self._handle_exitstatus(sts)
                except os.error:
                    if _deadstate is not None:
                        self.returncode = _deadstate
            return self.returncode


        def wait(self):
            """Wait for child process to terminate.  Returns returncode
            attribute."""
            if self.returncode is None:
                pid, sts = os.waitpid(self.pid, 0)
                self._handle_exitstatus(sts)
            return self.returncode


        def _communicate(self, input):
            read_set = []
            write_set = []
            stdout = None # Return
            stderr = None # Return

            if self.stdin:
                # Flush stdio buffer.  This might block, if the user has
                # been writing to .stdin in an uncontrolled fashion.
                self.stdin.flush()
                if input:
                    write_set.append(self.stdin)
                else:
                    self.stdin.close()
            if self.stdout:
                read_set.append(self.stdout)
                stdout = []
            if self.stderr:
                read_set.append(self.stderr)
                stderr = []

            input_offset = 0
            while read_set or write_set:
                try:
                    rlist, wlist, xlist = select.select(read_set, write_set, [])
                except select.error, e:
                    if e.args[0] == errno.EINTR:
                        continue
                    raise

                if self.stdin in wlist:
                    # When select has indicated that the file is writable,
                    # we can write up to PIPE_BUF bytes without risk
                    # blocking.  POSIX defines PIPE_BUF >= 512
                    chunk = input[input_offset : input_offset + 512]
                    bytes_written = os.write(self.stdin.fileno(), chunk)
                    input_offset += bytes_written
                    if input_offset >= len(input):
                        self.stdin.close()
                        write_set.remove(self.stdin)

                if self.stdout in rlist:
                    data = os.read(self.stdout.fileno(), 1024)
                    if data == "":
                        self.stdout.close()
                        read_set.remove(self.stdout)
                    stdout.append(data)

                if self.stderr in rlist:
                    data = os.read(self.stderr.fileno(), 1024)
                    if data == "":
                        self.stderr.close()
                        read_set.remove(self.stderr)
                    stderr.append(data)

            # All data exchanged.  Translate lists into strings.
            if stdout is not None:
                stdout = ''.join(stdout)
            if stderr is not None:
                stderr = ''.join(stderr)

            # Translate newlines, if requested.  We cannot let the file
            # object do the translation: It is based on stdio, which is
            # impossible to combine with select (unless forcing no
            # buffering).
            if self.universal_newlines and hasattr(file, 'newlines'):
                if stdout:
                    stdout = self._translate_newlines(stdout)
                if stderr:
                    stderr = self._translate_newlines(stderr)

            self.wait()
            return (stdout, stderr)

        def send_signal(self, sig):
            """Send a signal to the process
            """
            os.kill(self.pid, sig)

        def terminate(self):
            """Terminate the process with SIGTERM
            """
            self.send_signal(signal.SIGTERM)

        def kill(self):
            """Kill the process with SIGKILL
            """
            self.send_signal(signal.SIGKILL)


def _demo_posix():
    #
    # Example 1: Simple redirection: Get process list
    #
    plist = Popen(["ps"], stdout=PIPE).communicate()[0]
    print "Process list:"
    print plist

    #
    # Example 2: Change uid before executing child
    #
    if os.getuid() == 0:
        p = Popen(["id"], preexec_fn=lambda: os.setuid(100))
        p.wait()

    #
    # Example 3: Connecting several subprocesses
    #
    print "Looking for 'hda'..."
    p1 = Popen(["dmesg"], stdout=PIPE)
    p2 = Popen(["grep", "hda"], stdin=p1.stdout, stdout=PIPE)
    print repr(p2.communicate()[0])

    #
    # Example 4: Catch execution error
    #
    print
    print "Trying a weird file..."
    try:
        print Popen(["/this/path/does/not/exist"]).communicate()
    except OSError, e:
        if e.errno == errno.ENOENT:
            print "The file didn't exist.  I thought so..."
            print "Child traceback:"
            print e.child_traceback
        else:
            print "Error", e.errno
    else:
        print >>sys.stderr, "Gosh.  No error."


def _demo_windows():
    #
    # Example 1: Connecting several subprocesses
    #
    print "Looking for 'PROMPT' in set output..."
    p1 = Popen("set", stdout=PIPE, shell=True)
    p2 = Popen('find "PROMPT"', stdin=p1.stdout, stdout=PIPE)
    print repr(p2.communicate()[0])

    #
    # Example 2: Simple execution of program
    #
    print "Executing calc..."
    p = Popen("calc")
    p.wait()


if 0 and __name__ == "__main__":
    if mswindows:
        _demo_windows()
    else:
        _demo_posix()

########NEW FILE########
__FILENAME__ = md2man
#!/usr/bin/env python
import sys, os, markdown, re
from BeautifulSoup import BeautifulSoup

def _split_lines(s):
    return re.findall(r'([^\n]*\n?)', s)
    

class Writer:
    def __init__(self):
        self.started = False
        self.indent = 0
        self.last_wrote = '\n'

    def _write(self, s):
        if s:
            self.last_wrote = s
            sys.stdout.write(s)

    def writeln(self, s):
        if s:
            self.linebreak()
            self._write('%s\n' % s)

    def write(self, s):
        if s:
            self.para()
            for line in _split_lines(s):
                if line.startswith('.'):
                    self._write('\\&' + line)
                else:
                    self._write(line)

    def linebreak(self):
        if not self.last_wrote.endswith('\n'):
            self._write('\n')

    def para(self, bullet=None):
        if not self.started:
            if not bullet:
                bullet = ' '
            if not self.indent:
                self.writeln(_macro('.PP'))
            else:
                assert(self.indent >= 2)
                prefix = ' '*(self.indent-2) + bullet + ' '
                self.writeln('.IP "%s" %d' % (prefix, self.indent))
            self.started = True

    def end_para(self):
        self.linebreak()
        self.started = False

    def start_bullet(self):
        self.indent += 3
        self.para(bullet='\\[bu]')

    def end_bullet(self):
        self.indent -= 3
        self.end_para()

w = Writer()


def _macro(name, *args):
    if not name.startswith('.'):
        raise ValueError('macro names must start with "."')
    fixargs = []
    for i in args:
        i = str(i)
        i = i.replace('\\', '')
        i = i.replace('"', "'")
        if (' ' in i) or not i:
            i = '"%s"' % i
        fixargs.append(i)
    return ' '.join([name] + list(fixargs))


def macro(name, *args):
    w.writeln(_macro(name, *args))


def _force_string(owner, tag):
    if tag.string:
        return tag.string
    else:
        out = ''
        for i in tag:
            if not (i.string or i.name in ['a', 'br']):
                raise ValueError('"%s" tags must contain only strings: '
                                 'got %r: %r' % (owner.name, tag.name, tag))
            out += _force_string(owner, i)
        return out


def _clean(s):
    s = s.replace('\\', '\\\\')
    return s


def _bitlist(tag):
    if getattr(tag, 'contents', None) == None:
        for i in _split_lines(str(tag)):
            yield None,_clean(i)
    else:
        for e in tag:
            name = getattr(e, 'name', None)
            if name in ['a', 'br']:
                name = None  # just treat as simple text
            s = _force_string(tag, e)
            if name:
                yield name,_clean(s)
            else:
                for i in _split_lines(s):
                    yield None,_clean(i)


def _bitlist_simple(tag):
    for typ,text in _bitlist(tag):
        if typ and not typ in ['em', 'strong', 'code']:
            raise ValueError('unexpected tag %r inside %r' % (typ, tag.name))
        yield text


def _text(bitlist):
    out = ''
    for typ,text in bitlist:
        if not typ:
            out += text
        elif typ == 'em':
            out += '\\fI%s\\fR' % text
        elif typ in ['strong', 'code']:
            out += '\\fB%s\\fR' % text
        else:
            raise ValueError('unexpected tag %r inside %r' % (typ, tag.name))
    out = out.strip()
    out = re.sub(re.compile(r'^\s+', re.M), '', out)
    return out


def text(tag):
    w.write(_text(_bitlist(tag)))


# This is needed because .BI (and .BR, .RB, etc) are weird little state
# machines that alternate between two fonts.  So if someone says something
# like foo<b>chicken</b><b>wicken</b>dicken we have to convert that to
#   .BI foo chickenwicken dicken
def _boldline(l):
    out = ['']
    last_bold = False
    for typ,text in l:
        nonzero = not not typ
        if nonzero != last_bold:
            last_bold = not last_bold
            out.append('')
        out[-1] += re.sub(r'\s+', ' ', text)
    macro('.BI', *out)


def do_definition(tag):
    w.end_para()
    macro('.TP')
    w.started = True
    split = 0
    pre = []
    post = []
    for typ,text in _bitlist(tag):
        if split:
            post.append((typ,text))
        elif text.lstrip().startswith(': '):
            split = 1
            post.append((typ,text.lstrip()[2:].lstrip()))
        else:
            pre.append((typ,text))
    _boldline(pre)
    w.write(_text(post))


def do_list(tag):
    for i in tag:
        name = getattr(i, 'name', '').lower()
        if not name and not str(i).strip():
            pass
        elif name != 'li':
            raise ValueError('only <li> is allowed inside <ul>: got %r' % i)
        else:
            w.start_bullet()
            for xi in i:
                do(xi)
                w.end_para()
            w.end_bullet()


def do(tag):
    name = getattr(tag, 'name', '').lower()
    if not name:
        text(tag)
    elif name == 'h1':
        macro('.SH', _force_string(tag, tag).upper())
        w.started = True
    elif name == 'h2':
        macro('.SS', _force_string(tag, tag))
        w.started = True
    elif name.startswith('h') and len(name)==2:
        raise ValueError('%r invalid - man page headers must be h1 or h2'
                         % name)
    elif name == 'pre':
        t = _force_string(tag.code, tag.code)
        if t.strip():
            macro('.RS', '+4n')
            macro('.nf')
            w.write(_clean(t).rstrip())
            macro('.fi')
            macro('.RE')
            w.end_para()
    elif name == 'p' or name == 'br':
        g = re.match(re.compile(r'([^\n]*)\n +: +(.*)', re.S), str(tag))
        if g:
            # it's a definition list (which some versions of python-markdown
            # don't support, including the one in Debian-lenny, so we can't
            # enable that markdown extension).  Fake it up.
            do_definition(tag)
        else:
            text(tag)
            w.end_para()
    elif name == 'ul':
        do_list(tag)
    else:
        raise ValueError('non-man-compatible html tag %r' % name)
        
    
PROD='Untitled'
VENDOR='Vendor Name'
SECTION='9'
GROUPNAME='User Commands'
DATE=''
AUTHOR=''

lines = []
if len(sys.argv) > 1:
    for n in sys.argv[1:]:
        lines += open(n).read().decode('utf8').split('\n')
else:
    lines += sys.stdin.read().decode('utf8').split('\n')

# parse pandoc-style document headers (not part of markdown)
g = re.match(r'^%\s+(.*?)\((.*?)\)\s+(.*)$', lines[0])
if g:
    PROD = g.group(1)
    SECTION = g.group(2)
    VENDOR = g.group(3)
    lines.pop(0)
g = re.match(r'^%\s+(.*?)$', lines[0])
if g:
    AUTHOR = g.group(1)
    lines.pop(0)
g = re.match(r'^%\s+(.*?)$', lines[0])
if g:
    DATE = g.group(1)
    lines.pop(0)
g = re.match(r'^%\s+(.*?)$', lines[0])
if g:
    GROUPNAME = g.group(1)
    lines.pop(0)

inp = '\n'.join(lines)
if AUTHOR:
    inp += ('\n# AUTHOR\n\n%s\n' % AUTHOR).replace('<', '\\<')

html = markdown.markdown(inp)
soup = BeautifulSoup(html, convertEntities=BeautifulSoup.HTML_ENTITIES)

macro('.TH', PROD.upper(), SECTION, DATE, VENDOR, GROUPNAME)
macro('.ad', 'l')  # left justified
macro('.nh')  # disable hyphenation
for e in soup:
    do(e)

########NEW FILE########
__FILENAME__ = firewall
import re, errno, socket, select, signal, struct
import compat.ssubprocess as ssubprocess
import helpers, ssyslog
from helpers import *

# python doesn't have a definition for this
IPPROTO_DIVERT = 254

# return values from sysctl_set
SUCCESS = 0
SAME = 1
FAILED = -1
NONEXIST = -2


def nonfatal(func, *args):
    try:
        func(*args)
    except Fatal, e:
        log('error: %s\n' % e)


def _call(argv):
    debug1('>> %s\n' % ' '.join(argv))
    rv = ssubprocess.call(argv)
    if rv:
        raise Fatal('%r returned %d' % (argv, rv))
    return rv


def ipt_chain_exists(name):
    argv = ['iptables', '-t', 'nat', '-nL']
    p = ssubprocess.Popen(argv, stdout = ssubprocess.PIPE)
    for line in p.stdout:
        if line.startswith('Chain %s ' % name):
            return True
    rv = p.wait()
    if rv:
        raise Fatal('%r returned %d' % (argv, rv))


def ipt(*args):
    argv = ['iptables', '-t', 'nat'] + list(args)
    _call(argv)


_no_ttl_module = False
def ipt_ttl(*args):
    global _no_ttl_module
    if not _no_ttl_module:
        # we avoid infinite loops by generating server-side connections
        # with ttl 42.  This makes the client side not recapture those
        # connections, in case client == server.
        try:
            argsplus = list(args) + ['-m', 'ttl', '!', '--ttl', '42']
            ipt(*argsplus)
        except Fatal:
            ipt(*args)
            # we only get here if the non-ttl attempt succeeds
            log('sshuttle: warning: your iptables is missing '
                'the ttl module.\n')
            _no_ttl_module = True
    else:
        ipt(*args)



# We name the chain based on the transproxy port number so that it's possible
# to run multiple copies of sshuttle at the same time.  Of course, the
# multiple copies shouldn't have overlapping subnets, or only the most-
# recently-started one will win (because we use "-I OUTPUT 1" instead of
# "-A OUTPUT").
def do_iptables(port, dnsport, subnets):
    chain = 'sshuttle-%s' % port

    # basic cleanup/setup of chains
    if ipt_chain_exists(chain):
        nonfatal(ipt, '-D', 'OUTPUT', '-j', chain)
        nonfatal(ipt, '-D', 'PREROUTING', '-j', chain)
        nonfatal(ipt, '-F', chain)
        ipt('-X', chain)

    if subnets or dnsport:
        ipt('-N', chain)
        ipt('-F', chain)
        ipt('-I', 'OUTPUT', '1', '-j', chain)
        ipt('-I', 'PREROUTING', '1', '-j', chain)

    if subnets:
        # create new subnet entries.  Note that we're sorting in a very
        # particular order: we need to go from most-specific (largest swidth)
        # to least-specific, and at any given level of specificity, we want
        # excludes to come first.  That's why the columns are in such a non-
        # intuitive order.
        for swidth,sexclude,snet in sorted(subnets, reverse=True):
            if sexclude:
                ipt('-A', chain, '-j', 'RETURN',
                    '--dest', '%s/%s' % (snet,swidth),
                    '-p', 'tcp')
            else:
                ipt_ttl('-A', chain, '-j', 'REDIRECT',
                        '--dest', '%s/%s' % (snet,swidth),
                        '-p', 'tcp',
                        '--to-ports', str(port))
                
    if dnsport:
        nslist = resolvconf_nameservers()
        for ip in nslist:
            ipt_ttl('-A', chain, '-j', 'REDIRECT',
                    '--dest', '%s/32' % ip,
                    '-p', 'udp',
                    '--dport', '53',
                    '--to-ports', str(dnsport))


def ipfw_rule_exists(n):
    argv = ['ipfw', 'list']
    p = ssubprocess.Popen(argv, stdout = ssubprocess.PIPE)
    found = False
    for line in p.stdout:
        if line.startswith('%05d ' % n):
            if not ('ipttl 42' in line
                    or ('skipto %d' % (n+1)) in line
                    or 'check-state' in line):
                log('non-sshuttle ipfw rule: %r\n' % line.strip())
                raise Fatal('non-sshuttle ipfw rule #%d already exists!' % n)
            found = True
    rv = p.wait()
    if rv:
        raise Fatal('%r returned %d' % (argv, rv))
    return found


_oldctls = {}
def _fill_oldctls(prefix):
    argv = ['sysctl', prefix]
    p = ssubprocess.Popen(argv, stdout = ssubprocess.PIPE)
    for line in p.stdout:
        assert(line[-1] == '\n')
        (k,v) = line[:-1].split(': ', 1)
        _oldctls[k] = v
    rv = p.wait()
    if rv:
        raise Fatal('%r returned %d' % (argv, rv))
    if not line:
        raise Fatal('%r returned no data' % (argv,))


KERNEL_FLAGS_PATH = '/Library/Preferences/SystemConfiguration/com.apple.Boot'
KERNEL_FLAGS_NAME = 'Kernel Flags'
def _defaults_read_kernel_flags():
    argv = ['defaults', 'read', KERNEL_FLAGS_PATH, KERNEL_FLAGS_NAME]
    debug1('>> %s\n' % ' '.join(argv))
    p = ssubprocess.Popen(argv, stdout = ssubprocess.PIPE)
    flagstr = p.stdout.read().strip()
    rv = p.wait()
    if rv:
        raise Fatal('%r returned %d' % (argv, rv))
    flags = flagstr and flagstr.split(' ') or []
    return flags


def _defaults_write_kernel_flags(flags):
    flagstr = ' '.join(flags)
    argv = ['defaults', 'write', KERNEL_FLAGS_PATH, KERNEL_FLAGS_NAME,
            flagstr]
    _call(argv)
    argv = ['plutil', '-convert', 'xml1', KERNEL_FLAGS_PATH + '.plist']
    _call(argv)
    


def defaults_write_kernel_flag(name, val):
    flags = _defaults_read_kernel_flags()
    found = 0
    for i in range(len(flags)):
        if flags[i].startswith('%s=' % name):
            found += 1
            flags[i] = '%s=%s' % (name, val)
    if not found:
        flags.insert(0, '%s=%s' % (name, val))
    _defaults_write_kernel_flags(flags)


def _sysctl_set(name, val):
    argv = ['sysctl', '-w', '%s=%s' % (name, val)]
    debug1('>> %s\n' % ' '.join(argv))
    return ssubprocess.call(argv, stdout = open('/dev/null', 'w'))


_changedctls = []
def sysctl_set(name, val, permanent=False):
    PREFIX = 'net.inet.ip'
    assert(name.startswith(PREFIX + '.'))
    val = str(val)
    if not _oldctls:
        _fill_oldctls(PREFIX)
    if not (name in _oldctls):
        debug1('>> No such sysctl: %r\n' % name)
        return NONEXIST
    oldval = _oldctls[name]
    if val == oldval:
        return SAME

    rv = _sysctl_set(name, val)
    if rv != 0:
        return FAILED
    if permanent:
        debug1('>>   ...saving permanently in /etc/sysctl.conf\n')
        f = open('/etc/sysctl.conf', 'a')
        f.write('\n'
                '# Added by sshuttle\n'
                '%s=%s\n' % (name, val))
        f.close()
    else:
        _changedctls.append(name)
    return SUCCESS


def _udp_unpack(p):
    src = (socket.inet_ntoa(p[12:16]), struct.unpack('!H', p[20:22])[0])
    dst = (socket.inet_ntoa(p[16:20]), struct.unpack('!H', p[22:24])[0])
    return src, dst


def _udp_repack(p, src, dst):
    addrs = socket.inet_aton(src[0]) + socket.inet_aton(dst[0])
    ports = struct.pack('!HH', src[1], dst[1])
    return p[:12] + addrs + ports + p[24:]


_real_dns_server = [None]
def _handle_diversion(divertsock, dnsport):
    p,tag = divertsock.recvfrom(4096)
    src,dst = _udp_unpack(p)
    debug3('got diverted packet from %r to %r\n' % (src, dst))
    if dst[1] == 53:
        # outgoing DNS
        debug3('...packet is a DNS request.\n')
        _real_dns_server[0] = dst
        dst = ('127.0.0.1', dnsport)
    elif src[1] == dnsport:
        if islocal(src[0]):
            debug3('...packet is a DNS response.\n')
            src = _real_dns_server[0]
    else:
        log('weird?! unexpected divert from %r to %r\n' % (src, dst))
        assert(0)
    newp = _udp_repack(p, src, dst)
    divertsock.sendto(newp, tag)
    

def ipfw(*args):
    argv = ['ipfw', '-q'] + list(args)
    _call(argv)


def do_ipfw(port, dnsport, subnets):
    sport = str(port)
    xsport = str(port+1)

    # cleanup any existing rules
    if ipfw_rule_exists(port):
        ipfw('delete', sport)

    while _changedctls:
        name = _changedctls.pop()
        oldval = _oldctls[name]
        _sysctl_set(name, oldval)

    if subnets or dnsport:
        sysctl_set('net.inet.ip.fw.enable', 1)

        # This seems to be needed on MacOS 10.6 and 10.7.  For more
        # information, see:
        #   http://groups.google.com/group/sshuttle/browse_thread/thread/bc32562e17987b25/6d3aa2bb30a1edab
        # and
        #   http://serverfault.com/questions/138622/transparent-proxying-leaves-sockets-with-syn-rcvd-in-macos-x-10-6-snow-leopard
        changeflag = sysctl_set('net.inet.ip.scopedroute', 0, permanent=True)
        if changeflag == SUCCESS:
            log("\n"
                "        WARNING: ONE-TIME NETWORK DISRUPTION:\n"
                "        =====================================\n"
                "sshuttle has changed a MacOS kernel setting to work around\n"
                "a bug in MacOS 10.6.  This will cause your network to drop\n"
                "within 5-10 minutes unless you restart your network\n"
                "interface (change wireless networks or unplug/plug the\n"
                "ethernet port) NOW, then restart sshuttle.  The fix is\n"
                "permanent; you only have to do this once.\n\n")
            sys.exit(1)
        elif changeflag == FAILED:
            # On MacOS 10.7, the scopedroute sysctl became read-only, so
            # we have to fix it using a kernel boot parameter instead,
            # which requires rebooting.  For more, see:
            #   http://groups.google.com/group/sshuttle/browse_thread/thread/a42505ca33e1de80/e5e8f3e5a92d25f7
            log('Updating kernel boot flags.\n')
            defaults_write_kernel_flag('net.inet.ip.scopedroute', 0)
            log("\n"
                "        YOU MUST REBOOT TO USE SSHUTTLE\n"
                "        ===============================\n"
                "sshuttle has changed a MacOS kernel boot-time setting\n"
                "to work around a bug in MacOS 10.7 Lion.  You will need\n"
                "to reboot before it takes effect.  You only have to\n"
                "do this once.\n\n")
            sys.exit(EXITCODE_NEEDS_REBOOT)

        ipfw('add', sport, 'check-state', 'ip',
             'from', 'any', 'to', 'any')

    if subnets:
        # create new subnet entries
        for swidth,sexclude,snet in sorted(subnets, reverse=True):
            if sexclude:
                ipfw('add', sport, 'skipto', xsport,
                     'tcp',
                     'from', 'any', 'to', '%s/%s' % (snet,swidth))
            else:
                ipfw('add', sport, 'fwd', '127.0.0.1,%d' % port,
                     'tcp',
                     'from', 'any', 'to', '%s/%s' % (snet,swidth),
                     'not', 'ipttl', '42', 'keep-state', 'setup')

    # This part is much crazier than it is on Linux, because MacOS (at least
    # 10.6, and probably other versions, and maybe FreeBSD too) doesn't
    # correctly fixup the dstip/dstport for UDP packets when it puts them
    # through a 'fwd' rule.  It also doesn't fixup the srcip/srcport in the
    # response packet.  In Linux iptables, all that happens magically for us,
    # so we just redirect the packets and relax.
    #
    # On MacOS, we have to fix the ports ourselves.  For that, we use a
    # 'divert' socket, which receives raw packets and lets us mangle them.
    #
    # Here's how it works.  Let's say the local DNS server is 1.1.1.1:53,
    # and the remote DNS server is 2.2.2.2:53, and the local transproxy port
    # is 10.0.0.1:12300, and a client machine is making a request from
    # 10.0.0.5:9999. We see a packet like this:
    #    10.0.0.5:9999 -> 1.1.1.1:53
    # Since the destip:port matches one of our local nameservers, it will
    # match a 'fwd' rule, thus grabbing it on the local machine.  However,
    # the local kernel will then see a packet addressed to *:53 and
    # not know what to do with it; there's nobody listening on port 53.  Thus,
    # we divert it, rewriting it into this:
    #    10.0.0.5:9999 -> 10.0.0.1:12300
    # This gets proxied out to the server, which sends it to 2.2.2.2:53,
    # and the answer comes back, and the proxy sends it back out like this:
    #    10.0.0.1:12300 -> 10.0.0.5:9999
    # But that's wrong!  The original machine expected an answer from
    # 1.1.1.1:53, so we have to divert the *answer* and rewrite it:
    #    1.1.1.1:53 -> 10.0.0.5:9999
    #
    # See?  Easy stuff.
    if dnsport:
        divertsock = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                                   IPPROTO_DIVERT)
        divertsock.bind(('0.0.0.0', port)) # IP field is ignored

        nslist = resolvconf_nameservers()
        for ip in nslist:
            # relabel and then catch outgoing DNS requests
            ipfw('add', sport, 'divert', sport,
                 'udp',
                 'from', 'any', 'to', '%s/32' % ip, '53',
                 'not', 'ipttl', '42')
        # relabel DNS responses
        ipfw('add', sport, 'divert', sport,
             'udp',
             'from', 'any', str(dnsport), 'to', 'any',
             'not', 'ipttl', '42')

        def do_wait():
            while 1:
                r,w,x = select.select([sys.stdin, divertsock], [], [])
                if divertsock in r:
                    _handle_diversion(divertsock, dnsport)
                if sys.stdin in r:
                    return
    else:
        do_wait = None
        
    return do_wait


def program_exists(name):
    paths = (os.getenv('PATH') or os.defpath).split(os.pathsep)
    for p in paths:
        fn = '%s/%s' % (p, name)
        if os.path.exists(fn):
            return not os.path.isdir(fn) and os.access(fn, os.X_OK)


hostmap = {}
def rewrite_etc_hosts(port):
    HOSTSFILE='/etc/hosts'
    BAKFILE='%s.sbak' % HOSTSFILE
    APPEND='# sshuttle-firewall-%d AUTOCREATED' % port
    old_content = ''
    st = None
    try:
        old_content = open(HOSTSFILE).read()
        st = os.stat(HOSTSFILE)
    except IOError, e:
        if e.errno == errno.ENOENT:
            pass
        else:
            raise
    if old_content.strip() and not os.path.exists(BAKFILE):
        os.link(HOSTSFILE, BAKFILE)
    tmpname = "%s.%d.tmp" % (HOSTSFILE, port)
    f = open(tmpname, 'w')
    for line in old_content.rstrip().split('\n'):
        if line.find(APPEND) >= 0:
            continue
        f.write('%s\n' % line)
    for (name,ip) in sorted(hostmap.items()):
        f.write('%-30s %s\n' % ('%s %s' % (ip,name), APPEND))
    f.close()

    if st:
        os.chown(tmpname, st.st_uid, st.st_gid)
        os.chmod(tmpname, st.st_mode)
    else:
        os.chown(tmpname, 0, 0)
        os.chmod(tmpname, 0644)
    os.rename(tmpname, HOSTSFILE)


def restore_etc_hosts(port):
    global hostmap
    hostmap = {}
    rewrite_etc_hosts(port)


def _mask(ip, width):
    nip = struct.unpack('!I', socket.inet_aton(ip))[0]
    masked = nip & shl(shl(1, width) - 1, 32-width)
    return socket.inet_ntoa(struct.pack('!I', masked))


def ip_in_subnets(ip, subnets):
    for swidth,sexclude,snet in sorted(subnets, reverse=True):
        if _mask(snet, swidth) == _mask(ip, swidth):
            return not sexclude
    return False


# This is some voodoo for setting up the kernel's transparent
# proxying stuff.  If subnets is empty, we just delete our sshuttle rules;
# otherwise we delete it, then make them from scratch.
#
# This code is supposed to clean up after itself by deleting its rules on
# exit.  In case that fails, it's not the end of the world; future runs will
# supercede it in the transproxy list, at least, so the leftover rules
# are hopefully harmless.
def main(port, dnsport, syslog):
    assert(port > 0)
    assert(port <= 65535)
    assert(dnsport >= 0)
    assert(dnsport <= 65535)

    if os.getuid() != 0:
        raise Fatal('you must be root (or enable su/sudo) to set the firewall')

    if program_exists('ipfw'):
        do_it = do_ipfw
    elif program_exists('iptables'):
        do_it = do_iptables
    else:
        raise Fatal("can't find either ipfw or iptables; check your PATH")

    # because of limitations of the 'su' command, the *real* stdin/stdout
    # are both attached to stdout initially.  Clone stdout into stdin so we
    # can read from it.
    os.dup2(1, 0)

    if syslog:
        ssyslog.start_syslog()
        ssyslog.stderr_to_syslog()

    debug1('firewall manager ready.\n')
    sys.stdout.write('READY\n')
    sys.stdout.flush()

    # don't disappear if our controlling terminal or stdout/stderr
    # disappears; we still have to clean up.
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    # ctrl-c shouldn't be passed along to me.  When the main sshuttle dies,
    # I'll die automatically.
    os.setsid()

    # we wait until we get some input before creating the rules.  That way,
    # sshuttle can launch us as early as possible (and get sudo password
    # authentication as early in the startup process as possible).
    line = sys.stdin.readline(128)
    if not line:
        return  # parent died; nothing to do

    subnets = []
    if line != 'ROUTES\n':
        raise Fatal('firewall: expected ROUTES but got %r' % line)
    while 1:
        line = sys.stdin.readline(128)
        if not line:
            raise Fatal('firewall: expected route but got %r' % line)
        elif line == 'GO\n':
            break
        try:
            (width,exclude,ip) = line.strip().split(',', 2)
        except:
            raise Fatal('firewall: expected route or GO but got %r' % line)
        subnets.append((int(width), bool(int(exclude)), ip))
        
    try:
        if line:
            debug1('firewall manager: starting transproxy.\n')
            do_wait = do_it(port, dnsport, subnets)
            sys.stdout.write('STARTED\n')
        
        try:
            sys.stdout.flush()
        except IOError:
            # the parent process died for some reason; he's surely been loud
            # enough, so no reason to report another error
            return

        # Now we wait until EOF or any other kind of exception.  We need
        # to stay running so that we don't need a *second* password
        # authentication at shutdown time - that cleanup is important!
        while 1:
            if do_wait: do_wait()
            line = sys.stdin.readline(128)
            if line.startswith('HOST '):
                (name,ip) = line[5:].strip().split(',', 1)
                if ip_in_subnets(ip, subnets):
                    hostmap[name] = ip
                    rewrite_etc_hosts(port)
            elif line:
                raise Fatal('expected EOF, got %r' % line)
            else:
                break
    finally:
        try:
            debug1('firewall manager: undoing changes.\n')
        except:
            pass
        do_it(port, 0, [])
        restore_etc_hosts(port)

########NEW FILE########
__FILENAME__ = helpers
import sys, os, socket, errno

logprefix = ''
verbose = 0

def log(s):
    try:
        sys.stdout.flush()
        sys.stderr.write(logprefix + s)
        sys.stderr.flush()
    except IOError:
        # this could happen if stderr gets forcibly disconnected, eg. because
        # our tty closes.  That sucks, but it's no reason to abort the program.
        pass

def debug1(s):
    if verbose >= 1:
        log(s)

def debug2(s):
    if verbose >= 2:
        log(s)

def debug3(s):
    if verbose >= 3:
        log(s)


class Fatal(Exception):
    pass


EXITCODE_NEEDS_REBOOT = 111
class FatalNeedsReboot(Fatal):
    pass


def list_contains_any(l, sub):
    for i in sub:
        if i in l:
            return True
    return False


def resolvconf_nameservers():
    l = []
    for line in open('/etc/resolv.conf'):
        words = line.lower().split()
        if len(words) >= 2 and words[0] == 'nameserver':
            l.append(words[1])
    return l


def resolvconf_random_nameserver():
    l = resolvconf_nameservers()
    if l:
        if len(l) > 1:
            # don't import this unless we really need it
            import random
            random.shuffle(l)
        return l[0]
    else:
        return '127.0.0.1'
    

def islocal(ip):
    sock = socket.socket()
    try:
        try:
            sock.bind((ip, 0))
        except socket.error, e:
            if e.args[0] == errno.EADDRNOTAVAIL:
                return False  # not a local IP
            else:
                raise
    finally:
        sock.close()
    return True  # it's a local IP, or there would have been an error


def shl(n, bits):
    # we use our own implementation of left-shift because
    # results may be different between older and newer versions
    # of python for numbers like 1<<32.  We use long() because
    # int(2**32) doesn't work in older python, which has limited
    # int sizes.
    return n * long(2**bits)

########NEW FILE########
__FILENAME__ = hostwatch
import time, socket, re, select, errno
if not globals().get('skip_imports'):
    import compat.ssubprocess as ssubprocess
    import helpers
    from helpers import *

POLL_TIME = 60*15
NETSTAT_POLL_TIME = 30
CACHEFILE=os.path.expanduser('~/.sshuttle.hosts')


_nmb_ok = True
_smb_ok = True
hostnames = {}
queue = {}
try:
    null = open('/dev/null', 'wb')
except IOError, e:
    log('warning: %s\n' % e)
    null = os.popen("sh -c 'while read x; do :; done'", 'wb', 4096)


def _is_ip(s):
    return re.match(r'\d+\.\d+\.\d+\.\d+$', s)


def write_host_cache():
    tmpname = '%s.%d.tmp' % (CACHEFILE, os.getpid())
    try:
        f = open(tmpname, 'wb')
        for name,ip in sorted(hostnames.items()):
            f.write('%s,%s\n' % (name, ip))
        f.close()
        os.rename(tmpname, CACHEFILE)
    finally:
        try:
            os.unlink(tmpname)
        except:
            pass


def read_host_cache():
    try:
        f = open(CACHEFILE)
    except IOError, e:
        if e.errno == errno.ENOENT:
            return
        else:
            raise
    for line in f:
        words = line.strip().split(',')
        if len(words) == 2:
            (name,ip) = words
            name = re.sub(r'[^-\w\.]', '-', name).strip()
            ip = re.sub(r'[^0-9.]', '', ip).strip()
            if name and ip:
                found_host(name, ip)


def found_host(full_hostname, ip):
    full_hostname = re.sub(r'[^-\w\.]', '_', full_hostname)
    hostname = re.sub(r'\..*', '', full_hostname)
    _insert_host(full_hostname, ip)
    _insert_host(hostname, ip)


def _insert_host(hostname, ip):
    if (ip.startswith('127.') or ip.startswith('255.') 
        or hostname == 'localhost'):
        return
    oldip = hostnames.get(hostname)
    if oldip != ip:
        hostnames[hostname] = ip
        debug1('Found: %s: %s\n' % (hostname, ip))
        sys.stdout.write('%s,%s\n' % (hostname, ip))
        write_host_cache()


def _check_etc_hosts():
    debug2(' > hosts\n')
    for line in open('/etc/hosts'):
        line = re.sub(r'#.*', '', line)
        words = line.strip().split()
        if not words:
            continue
        ip = words[0]
        names = words[1:]
        if _is_ip(ip):
            debug3('<    %s %r\n' % (ip, names))
            for n in names:
                check_host(n)
                found_host(n, ip)


def _check_revdns(ip):
    debug2(' > rev: %s\n' % ip)
    try:
        r = socket.gethostbyaddr(ip)
        debug3('<    %s\n' % r[0])
        check_host(r[0])
        found_host(r[0], ip)
    except socket.herror, e:
        pass


def _check_dns(hostname):
    debug2(' > dns: %s\n' % hostname)
    try:
        ip = socket.gethostbyname(hostname)
        debug3('<    %s\n' % ip)
        check_host(ip)
        found_host(hostname, ip)
    except socket.gaierror, e:
        pass


def _check_netstat():
    debug2(' > netstat\n')
    argv = ['netstat', '-n']
    try:
        p = ssubprocess.Popen(argv, stdout=ssubprocess.PIPE, stderr=null)
        content = p.stdout.read()
        p.wait()
    except OSError, e:
        log('%r failed: %r\n' % (argv, e))
        return

    for ip in re.findall(r'\d+\.\d+\.\d+\.\d+', content):
        debug3('<    %s\n' % ip)
        check_host(ip)
        

def _check_smb(hostname):
    return
    global _smb_ok
    if not _smb_ok:
        return
    argv = ['smbclient', '-U', '%', '-L', hostname]
    debug2(' > smb: %s\n' % hostname)
    try:
        p = ssubprocess.Popen(argv, stdout=ssubprocess.PIPE, stderr=null)
        lines = p.stdout.readlines()
        p.wait()
    except OSError, e:
        log('%r failed: %r\n' % (argv, e))
        _smb_ok = False
        return

    lines.reverse()

    # junk at top
    while lines:
        line = lines.pop().strip()
        if re.match(r'Server\s+', line):
            break

    # server list section:
    #    Server   Comment
    #    ------   -------
    while lines:
        line = lines.pop().strip()
        if not line or re.match(r'-+\s+-+', line):
            continue
        if re.match(r'Workgroup\s+Master', line):
            break
        words = line.split()
        hostname = words[0].lower()
        debug3('<    %s\n' % hostname)
        check_host(hostname)

    # workgroup list section:
    #   Workgroup  Master
    #   ---------  ------
    while lines:
        line = lines.pop().strip()
        if re.match(r'-+\s+', line):
            continue
        if not line:
            break
        words = line.split()
        (workgroup, hostname) = (words[0].lower(), words[1].lower())
        debug3('<    group(%s) -> %s\n' % (workgroup, hostname))
        check_host(hostname)
        check_workgroup(workgroup)

    if lines:
        assert(0)


def _check_nmb(hostname, is_workgroup, is_master):
    return
    global _nmb_ok
    if not _nmb_ok:
        return
    argv = ['nmblookup'] + ['-M']*is_master + ['--', hostname]
    debug2(' > n%d%d: %s\n' % (is_workgroup, is_master, hostname))
    try:
        p = ssubprocess.Popen(argv, stdout=ssubprocess.PIPE, stderr=null)
        lines = p.stdout.readlines()
        rv = p.wait()
    except OSError, e:
        log('%r failed: %r\n' % (argv, e))
        _nmb_ok = False
        return
    if rv:
        log('%r returned %d\n' % (argv, rv))
        return
    for line in lines:
        m = re.match(r'(\d+\.\d+\.\d+\.\d+) (\w+)<\w\w>\n', line)
        if m:
            g = m.groups()
            (ip, name) = (g[0], g[1].lower())
            debug3('<    %s -> %s\n' % (name, ip))
            if is_workgroup:
                _enqueue(_check_smb, ip)
            else:
                found_host(name, ip)
                check_host(name)


def check_host(hostname):
    if _is_ip(hostname):
        _enqueue(_check_revdns, hostname)
    else:
        _enqueue(_check_dns, hostname)
    _enqueue(_check_smb, hostname)
    _enqueue(_check_nmb, hostname, False, False)


def check_workgroup(hostname):
    _enqueue(_check_nmb, hostname, True, False)
    _enqueue(_check_nmb, hostname, True, True)


def _enqueue(op, *args):
    t = (op,args)
    if queue.get(t) == None:
        queue[t] = 0


def _stdin_still_ok(timeout):
    r,w,x = select.select([sys.stdin.fileno()], [], [], timeout)
    if r:
        b = os.read(sys.stdin.fileno(), 4096)
        if not b:
            return False
    return True


def hw_main(seed_hosts):
    if helpers.verbose >= 2:
        helpers.logprefix = 'HH: '
    else:
        helpers.logprefix = 'hostwatch: '

    read_host_cache()
        
    _enqueue(_check_etc_hosts)
    _enqueue(_check_netstat)
    check_host('localhost')
    check_host(socket.gethostname())
    check_workgroup('workgroup')
    check_workgroup('-')
    for h in seed_hosts:
        check_host(h)

    while 1:
        now = time.time()
        for t,last_polled in queue.items():
            (op,args) = t
            if not _stdin_still_ok(0):
                break
            maxtime = POLL_TIME
            if op == _check_netstat:
                maxtime = NETSTAT_POLL_TIME
            if now - last_polled > maxtime:
                queue[t] = time.time()
                op(*args)
            try:
                sys.stdout.flush()
            except IOError:
                break
                
        # FIXME: use a smarter timeout based on oldest last_polled
        if not _stdin_still_ok(1):
            break

########NEW FILE########
__FILENAME__ = main
import sys, os, re
import helpers, options, client, server, firewall, hostwatch
import compat.ssubprocess as ssubprocess
from helpers import *


# list of:
# 1.2.3.4/5 or just 1.2.3.4
def parse_subnets(subnets_str):
    subnets = []
    for s in subnets_str:
        m = re.match(r'(\d+)(?:\.(\d+)\.(\d+)\.(\d+))?(?:/(\d+))?$', s)
        if not m:
            raise Fatal('%r is not a valid IP subnet format' % s)
        (a,b,c,d,width) = m.groups()
        (a,b,c,d) = (int(a or 0), int(b or 0), int(c or 0), int(d or 0))
        if width == None:
            width = 32
        else:
            width = int(width)
        if a > 255 or b > 255 or c > 255 or d > 255:
            raise Fatal('%d.%d.%d.%d has numbers > 255' % (a,b,c,d))
        if width > 32:
            raise Fatal('*/%d is greater than the maximum of 32' % width)
        subnets.append(('%d.%d.%d.%d' % (a,b,c,d), width))
    return subnets


# 1.2.3.4:567 or just 1.2.3.4 or just 567
def parse_ipport(s):
    s = str(s)
    m = re.match(r'(?:(\d+)\.(\d+)\.(\d+)\.(\d+))?(?::)?(?:(\d+))?$', s)
    if not m:
        raise Fatal('%r is not a valid IP:port format' % s)
    (a,b,c,d,port) = m.groups()
    (a,b,c,d,port) = (int(a or 0), int(b or 0), int(c or 0), int(d or 0),
                      int(port or 0))
    if a > 255 or b > 255 or c > 255 or d > 255:
        raise Fatal('%d.%d.%d.%d has numbers > 255' % (a,b,c,d))
    if port > 65535:
        raise Fatal('*:%d is greater than the maximum of 65535' % port)
    if a == None:
        a = b = c = d = 0
    return ('%d.%d.%d.%d' % (a,b,c,d), port)


optspec = """
sshuttle [-l [ip:]port] [-r [username@]sshserver[:port]] <subnets...>
sshuttle --server
sshuttle --firewall <port> <subnets...>
sshuttle --hostwatch
--
l,listen=  transproxy to this ip address and port number [127.0.0.1:0]
H,auto-hosts scan for remote hostnames and update local /etc/hosts
N,auto-nets  automatically determine subnets to route
dns        capture local DNS requests and forward to the remote DNS server
python=    path to python interpreter on the remote server
r,remote=  ssh hostname (and optional username) of remote sshuttle server
x,exclude= exclude this subnet (can be used more than once)
exclude-from=  exclude the subnets in a file (whitespace separated)
v,verbose  increase debug message verbosity
e,ssh-cmd= the command to use to connect to the remote [ssh]
seed-hosts= with -H, use these hostnames for initial scan (comma-separated)
no-latency-control  sacrifice latency to improve bandwidth benchmarks
wrap=      restart counting channel numbers after this number (for testing)
D,daemon   run in the background as a daemon
V,version  print sshuttle's version number
syslog     send log messages to syslog (default if you use --daemon)
pidfile=   pidfile name (only if using --daemon) [./sshuttle.pid]
server     (internal use only)
firewall   (internal use only)
hostwatch  (internal use only)
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[2:])

if opt.version:
    import version
    print version.TAG
    sys.exit(0)
if opt.daemon:
    opt.syslog = 1
if opt.wrap:
    import ssnet
    ssnet.MAX_CHANNEL = int(opt.wrap)
helpers.verbose = opt.verbose

try:
    if opt.server:
        if len(extra) != 0:
            o.fatal('no arguments expected')
        server.latency_control = opt.latency_control
        sys.exit(server.main())
    elif opt.firewall:
        if len(extra) != 2:
            o.fatal('exactly two arguments expected')
        sys.exit(firewall.main(int(extra[0]), int(extra[1]), opt.syslog))
    elif opt.hostwatch:
        sys.exit(hostwatch.hw_main(extra))
    else:
        if len(extra) < 1 and not opt.auto_nets:
            o.fatal('at least one subnet (or -N) expected')
        includes = extra
        excludes = ['127.0.0.0/8']
        for k,v in flags:
            if k in ('-x','--exclude'):
                excludes.append(v)
            if k in ('-X', '--exclude-from'):
                excludes += open(v).read().split()
        remotename = opt.remote
        if remotename == '' or remotename == '-':
            remotename = None
        if opt.seed_hosts and not opt.auto_hosts:
            o.fatal('--seed-hosts only works if you also use -H')
        if opt.seed_hosts:
            sh = re.split(r'[\s,]+', (opt.seed_hosts or "").strip())
        elif opt.auto_hosts:
            sh = []
        else:
            sh = None
        sys.exit(client.main(parse_ipport(opt.listen or '0.0.0.0:0'),
                             opt.ssh_cmd,
                             remotename,
                             opt.python,
                             opt.latency_control,
                             opt.dns,
                             sh,
                             opt.auto_nets,
                             parse_subnets(includes),
                             parse_subnets(excludes),
                             opt.syslog, opt.daemon, opt.pidfile))
except FatalNeedsReboot, e:
    log('You must reboot before using sshuttle.\n')
    sys.exit(EXITCODE_NEEDS_REBOOT)
except Fatal, e:
    log('fatal: %s\n' % e)
    sys.exit(99)
except KeyboardInterrupt:
    log('\n')
    log('Keyboard interrupt: exiting.\n')
    sys.exit(1)

########NEW FILE########
__FILENAME__ = options
"""Command-line options parser.
With the help of an options spec string, easily parse command-line options.
"""
import sys, os, textwrap, getopt, re, struct

class OptDict:
    def __init__(self):
        self._opts = {}

    def __setitem__(self, k, v):
        if k.startswith('no-') or k.startswith('no_'):
            k = k[3:]
            v = not v
        self._opts[k] = v

    def __getitem__(self, k):
        if k.startswith('no-') or k.startswith('no_'):
            return not self._opts[k[3:]]
        return self._opts[k]

    def __getattr__(self, k):
        return self[k]


def _default_onabort(msg):
    sys.exit(97)


def _intify(v):
    try:
        vv = int(v or '')
        if str(vv) == v:
            return vv
    except ValueError:
        pass
    return v


def _atoi(v):
    try:
        return int(v or 0)
    except ValueError:
        return 0


def _remove_negative_kv(k, v):
    if k.startswith('no-') or k.startswith('no_'):
        return k[3:], not v
    return k,v

def _remove_negative_k(k):
    return _remove_negative_kv(k, None)[0]


def _tty_width():
    s = struct.pack("HHHH", 0, 0, 0, 0)
    try:
        import fcntl, termios
        s = fcntl.ioctl(sys.stderr.fileno(), termios.TIOCGWINSZ, s)
    except (IOError, ImportError):
        return _atoi(os.environ.get('WIDTH')) or 70
    (ysize,xsize,ypix,xpix) = struct.unpack('HHHH', s)
    return xsize or 70


class Options:
    """Option parser.
    When constructed, two strings are mandatory. The first one is the command
    name showed before error messages. The second one is a string called an
    optspec that specifies the synopsis and option flags and their description.
    For more information about optspecs, consult the bup-options(1) man page.

    Two optional arguments specify an alternative parsing function and an
    alternative behaviour on abort (after having output the usage string).

    By default, the parser function is getopt.gnu_getopt, and the abort
    behaviour is to exit the program.
    """
    def __init__(self, optspec, optfunc=getopt.gnu_getopt,
                 onabort=_default_onabort):
        self.optspec = optspec
        self._onabort = onabort
        self.optfunc = optfunc
        self._aliases = {}
        self._shortopts = 'h?'
        self._longopts = ['help']
        self._hasparms = {}
        self._defaults = {}
        self._usagestr = self._gen_usage()

    def _gen_usage(self):
        out = []
        lines = self.optspec.strip().split('\n')
        lines.reverse()
        first_syn = True
        while lines:
            l = lines.pop()
            if l == '--': break
            out.append('%s: %s\n' % (first_syn and 'usage' or '   or', l))
            first_syn = False
        out.append('\n')
        last_was_option = False
        while lines:
            l = lines.pop()
            if l.startswith(' '):
                out.append('%s%s\n' % (last_was_option and '\n' or '',
                                       l.lstrip()))
                last_was_option = False
            elif l:
                (flags, extra) = l.split(' ', 1)
                extra = extra.strip()
                if flags.endswith('='):
                    flags = flags[:-1]
                    has_parm = 1
                else:
                    has_parm = 0
                g = re.search(r'\[([^\]]*)\]$', extra)
                if g:
                    defval = g.group(1)
                else:
                    defval = None
                flagl = flags.split(',')
                flagl_nice = []
                for _f in flagl:
                    f,dvi = _remove_negative_kv(_f, _intify(defval))
                    self._aliases[f] = _remove_negative_k(flagl[0])
                    self._hasparms[f] = has_parm
                    self._defaults[f] = dvi
                    if len(f) == 1:
                        self._shortopts += f + (has_parm and ':' or '')
                        flagl_nice.append('-' + f)
                    else:
                        f_nice = re.sub(r'\W', '_', f)
                        self._aliases[f_nice] = _remove_negative_k(flagl[0])
                        self._longopts.append(f + (has_parm and '=' or ''))
                        self._longopts.append('no-' + f)
                        flagl_nice.append('--' + _f)
                flags_nice = ', '.join(flagl_nice)
                if has_parm:
                    flags_nice += ' ...'
                prefix = '    %-20s  ' % flags_nice
                argtext = '\n'.join(textwrap.wrap(extra, width=_tty_width(),
                                                initial_indent=prefix,
                                                subsequent_indent=' '*28))
                out.append(argtext + '\n')
                last_was_option = True
            else:
                out.append('\n')
                last_was_option = False
        return ''.join(out).rstrip() + '\n'

    def usage(self, msg=""):
        """Print usage string to stderr and abort."""
        sys.stderr.write(self._usagestr)
        e = self._onabort and self._onabort(msg) or None
        if e:
            raise e

    def fatal(self, s):
        """Print an error message to stderr and abort with usage string."""
        msg = 'error: %s\n' % s
        sys.stderr.write(msg)
        return self.usage(msg)

    def parse(self, args):
        """Parse a list of arguments and return (options, flags, extra).

        In the returned tuple, "options" is an OptDict with known options,
        "flags" is a list of option flags that were used on the command-line,
        and "extra" is a list of positional arguments.
        """
        try:
            (flags,extra) = self.optfunc(args, self._shortopts, self._longopts)
        except getopt.GetoptError, e:
            self.fatal(e)

        opt = OptDict()

        for k,v in self._defaults.iteritems():
            k = self._aliases[k]
            opt[k] = v

        for (k,v) in flags:
            k = k.lstrip('-')
            if k in ('h', '?', 'help'):
                self.usage()
            if k.startswith('no-'):
                k = self._aliases[k[3:]]
                v = 0
            else:
                k = self._aliases[k]
                if not self._hasparms[k]:
                    assert(v == '')
                    v = (opt._opts.get(k) or 0) + 1
                else:
                    v = _intify(v)
            opt[k] = v
        for (f1,f2) in self._aliases.iteritems():
            opt[f1] = opt._opts.get(f2)
        return (opt,flags,extra)

########NEW FILE########
__FILENAME__ = server
import re, struct, socket, select, traceback, time
if not globals().get('skip_imports'):
    import ssnet, helpers, hostwatch
    import compat.ssubprocess as ssubprocess
    from ssnet import SockWrapper, Handler, Proxy, Mux, MuxWrapper
    from helpers import *


def _ipmatch(ipstr):
    if ipstr == 'default':
        ipstr = '0.0.0.0/0'
    m = re.match(r'^(\d+(\.\d+(\.\d+(\.\d+)?)?)?)(?:/(\d+))?$', ipstr)
    if m:
        g = m.groups()
        ips = g[0]
        width = int(g[4] or 32)
        if g[1] == None:
            ips += '.0.0.0'
            width = min(width, 8)
        elif g[2] == None:
            ips += '.0.0'
            width = min(width, 16)
        elif g[3] == None:
            ips += '.0'
            width = min(width, 24)
        return (struct.unpack('!I', socket.inet_aton(ips))[0], width)


def _ipstr(ip, width):
    if width >= 32:
        return ip
    else:
        return "%s/%d" % (ip, width)


def _maskbits(netmask):
    if not netmask:
        return 32
    for i in range(32):
        if netmask[0] & shl(1, i):
            return 32-i
    return 0
    
    
def _list_routes():
    argv = ['netstat', '-rn']
    p = ssubprocess.Popen(argv, stdout=ssubprocess.PIPE)
    routes = []
    for line in p.stdout:
        cols = re.split(r'\s+', line)
        ipw = _ipmatch(cols[0])
        if not ipw:
            continue  # some lines won't be parseable; never mind
        maskw = _ipmatch(cols[2])  # linux only
        mask = _maskbits(maskw)   # returns 32 if maskw is null
        width = min(ipw[1], mask)
        ip = ipw[0] & shl(shl(1, width) - 1, 32-width)
        routes.append((socket.inet_ntoa(struct.pack('!I', ip)), width))
    rv = p.wait()
    if rv != 0:
        log('WARNING: %r returned %d\n' % (argv, rv))
        log('WARNING: That prevents --auto-nets from working.\n')
    return routes


def list_routes():
    l = []
    for (ip,width) in _list_routes():
        if not ip.startswith('0.') and not ip.startswith('127.'):
            l.append((ip,width))
    return l


def _exc_dump():
    exc_info = sys.exc_info()
    return ''.join(traceback.format_exception(*exc_info))


def start_hostwatch(seed_hosts):
    s1,s2 = socket.socketpair()
    pid = os.fork()
    if not pid:
        # child
        rv = 99
        try:
            try:
                s2.close()
                os.dup2(s1.fileno(), 1)
                os.dup2(s1.fileno(), 0)
                s1.close()
                rv = hostwatch.hw_main(seed_hosts) or 0
            except Exception, e:
                log('%s\n' % _exc_dump())
                rv = 98
        finally:
            os._exit(rv)
    s1.close()
    return pid,s2


class Hostwatch:
    def __init__(self):
        self.pid = 0
        self.sock = None


class DnsProxy(Handler):
    def __init__(self, mux, chan, request):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        Handler.__init__(self, [sock])
        self.timeout = time.time()+30
        self.mux = mux
        self.chan = chan
        self.tries = 0
        self.peer = None
        self.request = request
        self.sock = sock
        self.sock.setsockopt(socket.SOL_IP, socket.IP_TTL, 42)
        self.try_send()

    def try_send(self):
        if self.tries >= 3:
            return
        self.tries += 1
        self.peer = resolvconf_random_nameserver()
        self.sock.connect((self.peer, 53))
        debug2('DNS: sending to %r\n' % self.peer)
        try:
            self.sock.send(self.request)
        except socket.error, e:
            if e.args[0] in ssnet.NET_ERRS:
                # might have been spurious; try again.
                # Note: these errors sometimes are reported by recv(),
                # and sometimes by send().  We have to catch both.
                debug2('DNS send to %r: %s\n' % (self.peer, e))
                self.try_send()
                return
            else:
                log('DNS send to %r: %s\n' % (self.peer, e))
                return

    def callback(self):
        try:
            data = self.sock.recv(4096)
        except socket.error, e:
            if e.args[0] in ssnet.NET_ERRS:
                # might have been spurious; try again.
                # Note: these errors sometimes are reported by recv(),
                # and sometimes by send().  We have to catch both.
                debug2('DNS recv from %r: %s\n' % (self.peer, e))
                self.try_send()
                return
            else:
                log('DNS recv from %r: %s\n' % (self.peer, e))
                return
        debug2('DNS response: %d bytes\n' % len(data))
        self.mux.send(self.chan, ssnet.CMD_DNS_RESPONSE, data)
        self.ok = False


def main():
    if helpers.verbose >= 1:
        helpers.logprefix = ' s: '
    else:
        helpers.logprefix = 'server: '
    debug1('latency control setting = %r\n' % latency_control)

    routes = list(list_routes())
    debug1('available routes:\n')
    for r in routes:
        debug1('  %s/%d\n' % r)
        
    # synchronization header
    sys.stdout.write('\0\0SSHUTTLE0001')
    sys.stdout.flush()

    handlers = []
    mux = Mux(socket.fromfd(sys.stdin.fileno(),
                            socket.AF_INET, socket.SOCK_STREAM),
              socket.fromfd(sys.stdout.fileno(),
                            socket.AF_INET, socket.SOCK_STREAM))
    handlers.append(mux)
    routepkt = ''
    for r in routes:
        routepkt += '%s,%d\n' % r
    mux.send(0, ssnet.CMD_ROUTES, routepkt)

    hw = Hostwatch()
    hw.leftover = ''
        
    def hostwatch_ready():
        assert(hw.pid)
        content = hw.sock.recv(4096)
        if content:
            lines = (hw.leftover + content).split('\n')
            if lines[-1]:
                # no terminating newline: entry isn't complete yet!
                hw.leftover = lines.pop()
                lines.append('')
            else:
                hw.leftover = ''
            mux.send(0, ssnet.CMD_HOST_LIST, '\n'.join(lines))
        else:
            raise Fatal('hostwatch process died')

    def got_host_req(data):
        if not hw.pid:
            (hw.pid,hw.sock) = start_hostwatch(data.strip().split())
            handlers.append(Handler(socks = [hw.sock],
                                    callback = hostwatch_ready))
    mux.got_host_req = got_host_req

    def new_channel(channel, data):
        (dstip,dstport) = data.split(',', 1)
        dstport = int(dstport)
        outwrap = ssnet.connect_dst(dstip,dstport)
        handlers.append(Proxy(MuxWrapper(mux, channel), outwrap))
    mux.new_channel = new_channel

    dnshandlers = {}
    def dns_req(channel, data):
        debug2('Incoming DNS request.\n')
        h = DnsProxy(mux, channel, data)
        handlers.append(h)
        dnshandlers[channel] = h
    mux.got_dns_req = dns_req

    while mux.ok:
        if hw.pid:
            assert(hw.pid > 0)
            (rpid, rv) = os.waitpid(hw.pid, os.WNOHANG)
            if rpid:
                raise Fatal('hostwatch exited unexpectedly: code 0x%04x\n' % rv)
        
        ssnet.runonce(handlers, mux)
        if latency_control:
            mux.check_fullness()
        mux.callback()

        if dnshandlers:
            now = time.time()
            for channel,h in dnshandlers.items():
                if h.timeout < now or not h.ok:
                    del dnshandlers[channel]
                    h.ok = False

########NEW FILE########
__FILENAME__ = ssh
import sys, os, re, socket, zlib
import compat.ssubprocess as ssubprocess
import helpers
from helpers import *


def readfile(name):
    basedir = os.path.dirname(os.path.abspath(sys.argv[0]))
    path = [basedir] + sys.path
    for d in path:
        fullname = os.path.join(d, name)
        if os.path.exists(fullname):
            return open(fullname, 'rb').read()
    raise Exception("can't find file %r in any of %r" % (name, path))


def empackage(z, filename, data=None):
    (path,basename) = os.path.split(filename)
    if not data:
        data = readfile(filename)
    content = z.compress(data)
    content += z.flush(zlib.Z_SYNC_FLUSH)
    return '%s\n%d\n%s' % (basename, len(content), content)


def connect(ssh_cmd, rhostport, python, stderr, options):
    main_exe = sys.argv[0]
    portl = []

    rhostIsIPv6 = False
    if (rhostport or '').count(':') > 1:
        rhostIsIPv6 = True
        if rhostport.count(']') or rhostport.count('['):
            result = rhostport.split(']')
            rhost = result[0].strip('[')
            if len(result) > 1:
                result[1] = result[1].strip(':')
                if result[1] is not '':
                    portl = ['-p', str(int(result[1]))]
        else: # can't disambiguate IPv6 colons and a port number. pass the hostname through.
            rhost = rhostport
    else: # IPv4
        l = (rhostport or '').split(':', 1)
        rhost = l[0]
        if len(l) > 1:
            portl = ['-p', str(int(l[1]))]

    if rhost == '-':
        rhost = None

    ipv6flag = []
    if rhostIsIPv6:
        ipv6flag = ['-6']

    z = zlib.compressobj(1)
    content = readfile('assembler.py')
    optdata = ''.join("%s=%r\n" % (k,v) for (k,v) in options.items())
    content2 = (empackage(z, 'cmdline_options.py', optdata) +
                empackage(z, 'helpers.py') +
                empackage(z, 'compat/ssubprocess.py') +
                empackage(z, 'ssnet.py') +
                empackage(z, 'hostwatch.py') +
                empackage(z, 'server.py') +
                "\n")
    
    pyscript = r"""
                import sys;
                skip_imports=1;
                verbosity=%d;
                exec compile(sys.stdin.read(%d), "assembler.py", "exec")
                """ % (helpers.verbose or 0, len(content))
    pyscript = re.sub(r'\s+', ' ', pyscript.strip())

        
    if not rhost:
        # ignore the --python argument when running locally; we already know
        # which python version works.
        argv = [sys.argv[1], '-c', pyscript]
    else:
        if ssh_cmd:
            sshl = ssh_cmd.split(' ')
        else:
            sshl = ['ssh']
        if python:
            pycmd = "'%s' -c '%s'" % (python, pyscript)
        else:
            pycmd = ("P=python2; $P -V 2>/dev/null || P=python; "
                     "exec \"$P\" -c '%s'") % pyscript
        argv = (sshl + 
                portl + 
                ipv6flag + 
                [rhost, '--', pycmd])
    (s1,s2) = socket.socketpair()
    def setup():
        # runs in the child process
        s2.close()
    s1a,s1b = os.dup(s1.fileno()), os.dup(s1.fileno())
    s1.close()
    debug2('executing: %r\n' % argv)
    p = ssubprocess.Popen(argv, stdin=s1a, stdout=s1b, preexec_fn=setup,
                          close_fds=True, stderr=stderr)
    os.close(s1a)
    os.close(s1b)
    s2.sendall(content)
    s2.sendall(content2)
    return p, s2

########NEW FILE########
__FILENAME__ = ssnet
import struct, socket, errno, select
if not globals().get('skip_imports'):
    from helpers import *

MAX_CHANNEL = 65535
    
# these don't exist in the socket module in python 2.3!
SHUT_RD = 0
SHUT_WR = 1
SHUT_RDWR = 2


HDR_LEN = 8


CMD_EXIT = 0x4200
CMD_PING = 0x4201
CMD_PONG = 0x4202
CMD_CONNECT = 0x4203
CMD_STOP_SENDING = 0x4204
CMD_EOF = 0x4205
CMD_DATA = 0x4206
CMD_ROUTES = 0x4207
CMD_HOST_REQ = 0x4208
CMD_HOST_LIST = 0x4209
CMD_DNS_REQ = 0x420a
CMD_DNS_RESPONSE = 0x420b

cmd_to_name = {
    CMD_EXIT: 'EXIT',
    CMD_PING: 'PING',
    CMD_PONG: 'PONG',
    CMD_CONNECT: 'CONNECT',
    CMD_STOP_SENDING: 'STOP_SENDING',
    CMD_EOF: 'EOF',
    CMD_DATA: 'DATA',
    CMD_ROUTES: 'ROUTES',
    CMD_HOST_REQ: 'HOST_REQ',
    CMD_HOST_LIST: 'HOST_LIST',
    CMD_DNS_REQ: 'DNS_REQ',
    CMD_DNS_RESPONSE: 'DNS_RESPONSE',
}


NET_ERRS = [errno.ECONNREFUSED, errno.ETIMEDOUT,
            errno.EHOSTUNREACH, errno.ENETUNREACH,
            errno.EHOSTDOWN, errno.ENETDOWN]


def _add(l, elem):
    if not elem in l:
        l.append(elem)


def _fds(l):
    out = []
    for i in l:
        try:
            out.append(i.fileno())
        except AttributeError:
            out.append(i)
    out.sort()
    return out


def _nb_clean(func, *args):
    try:
        return func(*args)
    except OSError, e:
        if e.errno not in (errno.EWOULDBLOCK, errno.EAGAIN):
            raise
        else:
            debug3('%s: err was: %s\n' % (func.__name__, e))
            return None


def _try_peername(sock):
    try:
        pn = sock.getpeername()
        if pn:
            return '%s:%s' % (pn[0], pn[1])
    except socket.error, e:
        if e.args[0] not in (errno.ENOTCONN, errno.ENOTSOCK):
            raise
    return 'unknown'


_swcount = 0
class SockWrapper:
    def __init__(self, rsock, wsock, connect_to=None, peername=None):
        global _swcount
        _swcount += 1
        debug3('creating new SockWrapper (%d now exist)\n' % _swcount)
        self.exc = None
        self.rsock = rsock
        self.wsock = wsock
        self.shut_read = self.shut_write = False
        self.buf = []
        self.connect_to = connect_to
        self.peername = peername or _try_peername(self.rsock)
        self.try_connect()

    def __del__(self):
        global _swcount
        _swcount -= 1
        debug1('%r: deleting (%d remain)\n' % (self, _swcount))
        if self.exc:
            debug1('%r: error was: %s\n' % (self, self.exc))

    def __repr__(self):
        if self.rsock == self.wsock:
            fds = '#%d' % self.rsock.fileno()
        else:
            fds = '#%d,%d' % (self.rsock.fileno(), self.wsock.fileno())
        return 'SW%s:%s' % (fds, self.peername)

    def seterr(self, e):
        if not self.exc:
            self.exc = e
        self.nowrite()
        self.noread()

    def try_connect(self):
        if self.connect_to and self.shut_write:
            self.noread()
            self.connect_to = None
        if not self.connect_to:
            return  # already connected
        self.rsock.setblocking(False)
        debug3('%r: trying connect to %r\n' % (self, self.connect_to))
        if socket.inet_aton(self.connect_to[0])[0] == '\0':
            self.seterr(Exception("Can't connect to %r: "
                                  "IP address starts with zero\n"
                                  % (self.connect_to,)))
            self.connect_to = None
            return
        try:
            self.rsock.connect(self.connect_to)
            # connected successfully (Linux)
            self.connect_to = None
        except socket.error, e:
            debug3('%r: connect result: %s\n' % (self, e))
            if e.args[0] == errno.EINVAL:
                # this is what happens when you call connect() on a socket
                # that is now connected but returned EINPROGRESS last time,
                # on BSD, on python pre-2.5.1.  We need to use getsockopt()
                # to get the "real" error.  Later pythons do this
                # automatically, so this code won't run.
                realerr = self.rsock.getsockopt(socket.SOL_SOCKET,
                                                socket.SO_ERROR)
                e = socket.error(realerr, os.strerror(realerr))
                debug3('%r: fixed connect result: %s\n' % (self, e))
            if e.args[0] in [errno.EINPROGRESS, errno.EALREADY]:
                pass  # not connected yet
            elif e.args[0] == 0:
                # connected successfully (weird Linux bug?)
                # Sometimes Linux seems to return EINVAL when it isn't
                # invalid.  This *may* be caused by a race condition
                # between connect() and getsockopt(SO_ERROR) (ie. it
                # finishes connecting in between the two, so there is no
                # longer an error).  However, I'm not sure of that.
                #
                # I did get at least one report that the problem went away
                # when we added this, however.
                self.connect_to = None
            elif e.args[0] == errno.EISCONN:
                # connected successfully (BSD)
                self.connect_to = None
            elif e.args[0] in NET_ERRS + [errno.EACCES, errno.EPERM]:
                # a "normal" kind of error
                self.connect_to = None
                self.seterr(e)
            else:
                raise  # error we've never heard of?!  barf completely.

    def noread(self):
        if not self.shut_read:
            debug2('%r: done reading\n' % self)
            self.shut_read = True
            #self.rsock.shutdown(SHUT_RD)  # doesn't do anything anyway
        
    def nowrite(self):
        if not self.shut_write:
            debug2('%r: done writing\n' % self)
            self.shut_write = True
            try:
                self.wsock.shutdown(SHUT_WR)
            except socket.error, e:
                self.seterr('nowrite: %s' % e)

    def too_full(self):
        return False  # fullness is determined by the socket's select() state

    def uwrite(self, buf):
        if self.connect_to:
            return 0  # still connecting
        self.wsock.setblocking(False)
        try:
            return _nb_clean(os.write, self.wsock.fileno(), buf)
        except OSError, e:
            if e.errno == errno.EPIPE:
                debug1('%r: uwrite: got EPIPE\n' % self)
                self.nowrite()
                return 0
            else:
                # unexpected error... stream is dead
                self.seterr('uwrite: %s' % e)
                return 0
        
    def write(self, buf):
        assert(buf)
        return self.uwrite(buf)

    def uread(self):
        if self.connect_to:
            return None  # still connecting
        if self.shut_read:
            return
        self.rsock.setblocking(False)
        try:
            return _nb_clean(os.read, self.rsock.fileno(), 65536)
        except OSError, e:
            self.seterr('uread: %s' % e)
            return '' # unexpected error... we'll call it EOF

    def fill(self):
        if self.buf:
            return
        rb = self.uread()
        if rb:
            self.buf.append(rb)
        if rb == '':  # empty string means EOF; None means temporarily empty
            self.noread()

    def copy_to(self, outwrap):
        if self.buf and self.buf[0]:
            wrote = outwrap.write(self.buf[0])
            self.buf[0] = self.buf[0][wrote:]
        while self.buf and not self.buf[0]:
            self.buf.pop(0)
        if not self.buf and self.shut_read:
            outwrap.nowrite()


class Handler:
    def __init__(self, socks = None, callback = None):
        self.ok = True
        self.socks = socks or []
        if callback:
            self.callback = callback

    def pre_select(self, r, w, x):
        for i in self.socks:
            _add(r, i)

    def callback(self):
        log('--no callback defined-- %r\n' % self)
        (r,w,x) = select.select(self.socks, [], [], 0)
        for s in r:
            v = s.recv(4096)
            if not v:
                log('--closed-- %r\n' % self)
                self.socks = []
                self.ok = False


class Proxy(Handler):
    def __init__(self, wrap1, wrap2):
        Handler.__init__(self, [wrap1.rsock, wrap1.wsock,
                                wrap2.rsock, wrap2.wsock])
        self.wrap1 = wrap1
        self.wrap2 = wrap2

    def pre_select(self, r, w, x):
        if self.wrap1.shut_write: self.wrap2.noread()
        if self.wrap2.shut_write: self.wrap1.noread()
        
        if self.wrap1.connect_to:
            _add(w, self.wrap1.rsock)
        elif self.wrap1.buf:
            if not self.wrap2.too_full():
                _add(w, self.wrap2.wsock)
        elif not self.wrap1.shut_read:
            _add(r, self.wrap1.rsock)

        if self.wrap2.connect_to:
            _add(w, self.wrap2.rsock)
        elif self.wrap2.buf:
            if not self.wrap1.too_full():
                _add(w, self.wrap1.wsock)
        elif not self.wrap2.shut_read:
            _add(r, self.wrap2.rsock)

    def callback(self):
        self.wrap1.try_connect()
        self.wrap2.try_connect()
        self.wrap1.fill()
        self.wrap2.fill()
        self.wrap1.copy_to(self.wrap2)
        self.wrap2.copy_to(self.wrap1)
        if self.wrap1.buf and self.wrap2.shut_write:
            self.wrap1.buf = []
            self.wrap1.noread()
        if self.wrap2.buf and self.wrap1.shut_write:
            self.wrap2.buf = []
            self.wrap2.noread()
        if (self.wrap1.shut_read and self.wrap2.shut_read and
            not self.wrap1.buf and not self.wrap2.buf):
            self.ok = False
            self.wrap1.nowrite()
            self.wrap2.nowrite()


class Mux(Handler):
    def __init__(self, rsock, wsock):
        Handler.__init__(self, [rsock, wsock])
        self.rsock = rsock
        self.wsock = wsock
        self.new_channel = self.got_dns_req = self.got_routes = None
        self.got_host_req = self.got_host_list = None
        self.channels = {}
        self.chani = 0
        self.want = 0
        self.inbuf = ''
        self.outbuf = []
        self.fullness = 0
        self.too_full = False
        self.send(0, CMD_PING, 'chicken')

    def next_channel(self):
        # channel 0 is special, so we never allocate it
        for timeout in xrange(1024):
            self.chani += 1
            if self.chani > MAX_CHANNEL:
                self.chani = 1
            if not self.channels.get(self.chani):
                return self.chani

    def amount_queued(self):
        total = 0
        for b in self.outbuf:
            total += len(b)
        return total
            
    def check_fullness(self):
        if self.fullness > 32768:
            if not self.too_full:
                self.send(0, CMD_PING, 'rttest')
            self.too_full = True
        #ob = []
        #for b in self.outbuf:
        #    (s1,s2,c) = struct.unpack('!ccH', b[:4])
        #    ob.append(c)
        #log('outbuf: %d %r\n' % (self.amount_queued(), ob))
        
    def send(self, channel, cmd, data):
        data = str(data)
        assert(len(data) <= 65535)
        p = struct.pack('!ccHHH', 'S', 'S', channel, cmd, len(data)) + data
        self.outbuf.append(p)
        debug2(' > channel=%d cmd=%s len=%d (fullness=%d)\n'
               % (channel, cmd_to_name.get(cmd,hex(cmd)),
                  len(data), self.fullness))
        self.fullness += len(data)

    def got_packet(self, channel, cmd, data):
        debug2('<  channel=%d cmd=%s len=%d\n' 
               % (channel, cmd_to_name.get(cmd,hex(cmd)), len(data)))
        if cmd == CMD_PING:
            self.send(0, CMD_PONG, data)
        elif cmd == CMD_PONG:
            debug2('received PING response\n')
            self.too_full = False
            self.fullness = 0
        elif cmd == CMD_EXIT:
            self.ok = False
        elif cmd == CMD_CONNECT:
            assert(not self.channels.get(channel))
            if self.new_channel:
                self.new_channel(channel, data)
        elif cmd == CMD_DNS_REQ:
            assert(not self.channels.get(channel))
            if self.got_dns_req:
                self.got_dns_req(channel, data)
        elif cmd == CMD_ROUTES:
            if self.got_routes:
                self.got_routes(data)
            else:
                raise Exception('got CMD_ROUTES without got_routes?')
        elif cmd == CMD_HOST_REQ:
            if self.got_host_req:
                self.got_host_req(data)
            else:
                raise Exception('got CMD_HOST_REQ without got_host_req?')
        elif cmd == CMD_HOST_LIST:
            if self.got_host_list:
                self.got_host_list(data)
            else:
                raise Exception('got CMD_HOST_LIST without got_host_list?')
        else:
            callback = self.channels.get(channel)
            if not callback:
                log('warning: closed channel %d got cmd=%s len=%d\n' 
                       % (channel, cmd_to_name.get(cmd,hex(cmd)), len(data)))
            else:
                callback(cmd, data)

    def flush(self):
        self.wsock.setblocking(False)
        if self.outbuf and self.outbuf[0]:
            wrote = _nb_clean(os.write, self.wsock.fileno(), self.outbuf[0])
            debug2('mux wrote: %r/%d\n' % (wrote, len(self.outbuf[0])))
            if wrote:
                self.outbuf[0] = self.outbuf[0][wrote:]
        while self.outbuf and not self.outbuf[0]:
            self.outbuf[0:1] = []

    def fill(self):
        self.rsock.setblocking(False)
        try:
            b = _nb_clean(os.read, self.rsock.fileno(), 32768)
        except OSError, e:
            raise Fatal('other end: %r' % e)
        #log('<<< %r\n' % b)
        if b == '': # EOF
            self.ok = False
        if b:
            self.inbuf += b

    def handle(self):
        self.fill()
        #log('inbuf is: (%d,%d) %r\n'
        #     % (self.want, len(self.inbuf), self.inbuf))
        while 1:
            if len(self.inbuf) >= (self.want or HDR_LEN):
                (s1,s2,channel,cmd,datalen) = \
                    struct.unpack('!ccHHH', self.inbuf[:HDR_LEN])
                assert(s1 == 'S')
                assert(s2 == 'S')
                self.want = datalen + HDR_LEN
            if self.want and len(self.inbuf) >= self.want:
                data = self.inbuf[HDR_LEN:self.want]
                self.inbuf = self.inbuf[self.want:]
                self.want = 0
                self.got_packet(channel, cmd, data)
            else:
                break

    def pre_select(self, r, w, x):
        _add(r, self.rsock)
        if self.outbuf:
            _add(w, self.wsock)

    def callback(self):
        (r,w,x) = select.select([self.rsock], [self.wsock], [], 0)
        if self.rsock in r:
            self.handle()
        if self.outbuf and self.wsock in w:
            self.flush()


class MuxWrapper(SockWrapper):
    def __init__(self, mux, channel):
        SockWrapper.__init__(self, mux.rsock, mux.wsock)
        self.mux = mux
        self.channel = channel
        self.mux.channels[channel] = self.got_packet
        self.socks = []
        debug2('new channel: %d\n' % channel)

    def __del__(self):
        self.nowrite()
        SockWrapper.__del__(self)

    def __repr__(self):
        return 'SW%r:Mux#%d' % (self.peername,self.channel)

    def noread(self):
        if not self.shut_read:
            self.shut_read = True
            self.mux.send(self.channel, CMD_STOP_SENDING, '')
            self.maybe_close()

    def nowrite(self):
        if not self.shut_write:
            self.shut_write = True
            self.mux.send(self.channel, CMD_EOF, '')
            self.maybe_close()

    def maybe_close(self):
        if self.shut_read and self.shut_write:
            # remove the mux's reference to us.  The python garbage collector
            # will then be able to reap our object.
            self.mux.channels[self.channel] = None

    def too_full(self):
        return self.mux.too_full

    def uwrite(self, buf):
        if self.mux.too_full:
            return 0  # too much already enqueued
        if len(buf) > 2048:
            buf = buf[:2048]
        self.mux.send(self.channel, CMD_DATA, buf)
        return len(buf)

    def uread(self):
        if self.shut_read:
            return '' # EOF
        else:
            return None  # no data available right now

    def got_packet(self, cmd, data):
        if cmd == CMD_EOF:
            self.noread()
        elif cmd == CMD_STOP_SENDING:
            self.nowrite()
        elif cmd == CMD_DATA:
            self.buf.append(data)
        else:
            raise Exception('unknown command %d (%d bytes)' 
                            % (cmd, len(data)))


def connect_dst(ip, port):
    debug2('Connecting to %s:%d\n' % (ip, port))
    outsock = socket.socket()
    outsock.setsockopt(socket.SOL_IP, socket.IP_TTL, 42)
    return SockWrapper(outsock, outsock,
                       connect_to = (ip,port),
                       peername = '%s:%d' % (ip,port))


def runonce(handlers, mux):
    r = []
    w = []
    x = []
    to_remove = filter(lambda s: not s.ok, handlers)
    for h in to_remove:
        handlers.remove(h)

    for s in handlers:
        s.pre_select(r,w,x)
    debug2('Waiting: %d r=%r w=%r x=%r (fullness=%d/%d)\n' 
            % (len(handlers), _fds(r), _fds(w), _fds(x),
               mux.fullness, mux.too_full))
    (r,w,x) = select.select(r,w,x)
    debug2('  Ready: %d r=%r w=%r x=%r\n' 
        % (len(handlers), _fds(r), _fds(w), _fds(x)))
    ready = r+w+x
    did = {}
    for h in handlers:
        for s in h.socks:
            if s in ready:
                h.callback()
                did[s] = 1
    for s in ready:
        if not s in did:
            raise Fatal('socket %r was not used by any handler' % s)

########NEW FILE########
__FILENAME__ = ssyslog
import sys, os
from compat import ssubprocess


_p = None
def start_syslog():
    global _p
    _p = ssubprocess.Popen(['logger',
                            '-p', 'daemon.notice',
                            '-t', 'sshuttle'], stdin=ssubprocess.PIPE)


def stderr_to_syslog():
    sys.stdout.flush()
    sys.stderr.flush()
    os.dup2(_p.stdin.fileno(), 2)

########NEW FILE########
__FILENAME__ = stresstest
#!/usr/bin/env python
import sys, os, socket, select, struct, time

listener = socket.socket()
listener.bind(('127.0.0.1', 0))
listener.listen(500)

servers = []
clients = []
remain = {}

NUMCLIENTS = 50
count = 0


while 1:
    if len(clients) < NUMCLIENTS:
        c = socket.socket()
        c.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        c.bind(('0.0.0.0', 0))
        c.connect(listener.getsockname())
        count += 1
        if count >= 16384:
            count = 1
        print 'cli CREATING %d' % count
        b = struct.pack('I', count) + 'x'*count
        remain[c] = count
        print 'cli  >> %r' % len(b)
        c.send(b)
        c.shutdown(socket.SHUT_WR)
        clients.append(c)
        r = [listener]
        time.sleep(0.1)
    else:
        r = [listener]+servers+clients
    print 'select(%d)' % len(r)
    r,w,x = select.select(r, [], [], 5)
    assert(r)
    for i in r:
        if i == listener:
            s,addr = listener.accept()
            servers.append(s)
        elif i in servers:
            b = i.recv(4096)
            print 'srv <<  %r' % len(b)
            if not i in remain:
                assert(len(b) >= 4)
                want = struct.unpack('I', b[:4])[0]
                b = b[4:]
                #i.send('y'*want)
            else:
                want = remain[i]
            if want < len(b):
                print 'weird wanted %d bytes, got %d: %r' % (want, len(b), b)
                assert(want >= len(b))
            want -= len(b)
            remain[i] = want
            if not b:  # EOF
                if want:
                    print 'weird: eof but wanted %d more' % want
                    assert(want == 0)
                i.close()
                servers.remove(i)
                del remain[i]
            else:
                print 'srv  >> %r' % len(b)
                i.send('y'*len(b))
                if not want:
                    i.shutdown(socket.SHUT_WR)
        elif i in clients:
            b = i.recv(4096)
            print 'cli <<  %r' % len(b)
            want = remain[i]
            if want < len(b):
                print 'weird wanted %d bytes, got %d: %r' % (want, len(b), b)
                assert(want >= len(b))
            want -= len(b)
            remain[i] = want
            if not b:  # EOF
                if want:
                    print 'weird: eof but wanted %d more' % want
                    assert(want == 0)
                i.close()
                clients.remove(i)
                del remain[i]
listener.accept()

########NEW FILE########
__FILENAME__ = askpass
import sys, os, re, subprocess

def askpass(prompt):
    prompt = prompt.replace('"', "'")

    if 'yes/no' in prompt:
        return "yes"

    script="""
        tell application "Finder"
            activate
            display dialog "%s" \
              with title "Sshuttle SSH Connection" \
              default answer "" \
              with icon caution \
              with hidden answer
        end tell
    """ % prompt

    p = subprocess.Popen(['osascript', '-e', script], stdout=subprocess.PIPE)
    out = p.stdout.read()
    rv = p.wait()
    if rv:
        return None
    g = re.match("text returned:(.*), button returned:.*", out)
    if not g:
        return None
    return g.group(1)

########NEW FILE########
__FILENAME__ = main
import sys, os, pty
from AppKit import *
import my, models, askpass

def sshuttle_args(host, auto_nets, auto_hosts, dns, nets, debug,
                  no_latency_control):
    argv = [my.bundle_path('sshuttle/sshuttle', ''), '-r', host]
    assert(argv[0])
    if debug:
        argv.append('-v')
    if auto_nets:
        argv.append('--auto-nets')
    if auto_hosts:
        argv.append('--auto-hosts')
    if dns:
        argv.append('--dns')
    if no_latency_control:
        argv.append('--no-latency-control')
    argv += nets
    return argv


class _Callback(NSObject):
    def initWithFunc_(self, func):
        self = super(_Callback, self).init()
        self.func = func
        return self
    def func_(self, obj):
        return self.func(obj)


class Callback:
    def __init__(self, func):
        self.obj = _Callback.alloc().initWithFunc_(func)
        self.sel = self.obj.func_


class Runner:
    def __init__(self, argv, logfunc, promptfunc, serverobj):
        print 'in __init__'
        self.id = argv
        self.rv = None
        self.pid = None
        self.fd = None
        self.logfunc = logfunc
        self.promptfunc = promptfunc
        self.serverobj = serverobj
        self.buf = ''
        self.logfunc('\nConnecting to %s.\n' % self.serverobj.host())
        print 'will run: %r' % argv
        self.serverobj.setConnected_(False)
        pid,fd = pty.fork()
        if pid == 0:
            # child
            try:
                os.execvp(argv[0], argv)
            except Exception, e:
                sys.stderr.write('failed to start: %r\n' % e)
                raise
            finally:
                os._exit(42)
        # parent
        self.pid = pid
        self.file = NSFileHandle.alloc()\
               .initWithFileDescriptor_closeOnDealloc_(fd, True)
        self.cb = Callback(self.gotdata)
        NSNotificationCenter.defaultCenter()\
            .addObserver_selector_name_object_(self.cb.obj, self.cb.sel,
                        NSFileHandleDataAvailableNotification, self.file)
        self.file.waitForDataInBackgroundAndNotify()

    def __del__(self):
        self.wait()

    def _try_wait(self, options):
        if self.rv == None and self.pid > 0:
            pid,code = os.waitpid(self.pid, options)
            if pid == self.pid:
                if os.WIFEXITED(code):
                    self.rv = os.WEXITSTATUS(code)
                    if self.rv == 111:
                        NSRunAlertPanel('Sshuttle',
                            'Please restart your computer to finish '
                            'installing Sshuttle.',
                            'Restart Later', None, None)
                else:
                    self.rv = -os.WSTOPSIG(code)
                self.serverobj.setConnected_(False)
                self.serverobj.setError_('VPN process died')
                self.logfunc('Disconnected.\n')
        print 'wait_result: %r' % self.rv
        return self.rv

    def wait(self):
        rv = None
        while rv is None:
            self.gotdata(None)
            rv = self._try_wait(os.WNOHANG)
        
    def poll(self):
        return self._try_wait(os.WNOHANG)

    def kill(self):
        assert(self.pid > 0)
        print 'killing: pid=%r rv=%r' % (self.pid, self.rv)
        if self.rv == None:
            self.logfunc('Disconnecting from %s.\n' % self.serverobj.host())
            os.kill(self.pid, 15)
            self.wait()

    def gotdata(self, notification):
        print 'gotdata!'
        d = str(self.file.availableData())
        if d:
            self.logfunc(d)
            self.buf = self.buf + d
            if 'Connected.\r\n' in self.buf:
                self.serverobj.setConnected_(True)
            self.buf = self.buf[-4096:]
            if self.buf.strip().endswith(':'):
                lastline = self.buf.rstrip().split('\n')[-1]
                resp = self.promptfunc(lastline)
                add = ' (response)\n'
                self.buf += add
                self.logfunc(add)
                self.file.writeData_(my.Data(resp + '\n'))
            self.file.waitForDataInBackgroundAndNotify()
        self.poll()
        #print 'gotdata done!'


class SshuttleApp(NSObject):
    def initialize(self):
        d = my.PList('UserDefaults') 
        my.Defaults().registerDefaults_(d)


class SshuttleController(NSObject):
    # Interface builder outlets
    startAtLoginField = objc.IBOutlet()
    autoReconnectField = objc.IBOutlet()
    debugField = objc.IBOutlet()
    routingField = objc.IBOutlet()
    prefsWindow = objc.IBOutlet()
    serversController = objc.IBOutlet()
    logField = objc.IBOutlet()
    latencyControlField = objc.IBOutlet()
    
    servers = []
    conns = {}

    def _connect(self, server):
        host = server.host()
        print 'connecting %r' % host
        self.fill_menu()
        def logfunc(msg):
            print 'log! (%d bytes)' % len(msg)
            self.logField.textStorage()\
                .appendAttributedString_(NSAttributedString.alloc()\
                                         .initWithString_(msg))
            self.logField.didChangeText()
        def promptfunc(prompt):
            print 'prompt! %r' % prompt
            return askpass.askpass(prompt)
        nets_mode = server.autoNets()
        if nets_mode == models.NET_MANUAL:
            manual_nets = ["%s/%d" % (i.subnet(), i.width())
                           for i in server.nets()]
        elif nets_mode == models.NET_ALL:
            manual_nets = ['0/0']
        else:
            manual_nets = []
        noLatencyControl = (server.latencyControl() != models.LAT_INTERACTIVE)
        conn = Runner(sshuttle_args(host,
                                    auto_nets = nets_mode == models.NET_AUTO,
                                    auto_hosts = server.autoHosts(),
                                    dns = server.useDns(),
                                    nets = manual_nets,
                                    debug = self.debugField.state(),
                                    no_latency_control = noLatencyControl),
                      logfunc=logfunc, promptfunc=promptfunc,
                      serverobj=server)
        self.conns[host] = conn

    def _disconnect(self, server):
        host = server.host()
        print 'disconnecting %r' % host
        conn = self.conns.get(host)
        if conn:
            conn.kill()
        self.fill_menu()
        self.logField.textStorage().setAttributedString_(
                        NSAttributedString.alloc().initWithString_(''))
    
    @objc.IBAction
    def cmd_connect(self, sender):
        server = sender.representedObject()
        server.setWantConnect_(True)

    @objc.IBAction
    def cmd_disconnect(self, sender):
        server = sender.representedObject()
        server.setWantConnect_(False)

    @objc.IBAction
    def cmd_show(self, sender):
        self.prefsWindow.makeKeyAndOrderFront_(self)
        NSApp.activateIgnoringOtherApps_(True)

    @objc.IBAction
    def cmd_quit(self, sender):
        NSApp.performSelector_withObject_afterDelay_(NSApp.terminate_,
                                                     None, 0.0)

    def fill_menu(self):
        menu = self.menu
        menu.removeAllItems()

        def additem(name, func, obj):
            it = menu.addItemWithTitle_action_keyEquivalent_(name, None, "")
            it.setRepresentedObject_(obj)
            it.setTarget_(self)
            it.setAction_(func)
        def addnote(name):
            additem(name, None, None)

        any_inprogress = None
        any_conn = None
        any_err = None
        if len(self.servers):
            for i in self.servers:
                host = i.host()
                title = i.title()
                want = i.wantConnect()
                connected = i.connected()
                numnets = len(list(i.nets()))
                if not host:
                    additem('Connect Untitled', None, i)
                elif i.autoNets() == models.NET_MANUAL and not numnets:
                    additem('Connect %s (no routes)' % host, None, i)
                elif want:
                    any_conn = i
                    additem('Disconnect %s' % title, self.cmd_disconnect, i)
                else:
                    additem('Connect %s' % title, self.cmd_connect, i)
                if not want:
                    msg = 'Off'
                elif i.error():
                    msg = 'ERROR - try reconnecting'
                    any_err = i
                elif connected:
                    msg = 'Connected'
                else:
                    msg = 'Connecting...'
                    any_inprogress = i
                addnote('   State: %s' % msg)
        else:
            addnote('No servers defined yet')

        menu.addItem_(NSMenuItem.separatorItem())
        additem('Preferences...', self.cmd_show, None)
        additem('Quit Sshuttle VPN', self.cmd_quit, None)

        if any_err:
            self.statusitem.setImage_(self.img_err)
            self.statusitem.setTitle_('Error!')
        elif any_conn:
            self.statusitem.setImage_(self.img_running)
            if any_inprogress:
                self.statusitem.setTitle_('Connecting...')
            else:
                self.statusitem.setTitle_('')
        else:
            self.statusitem.setImage_(self.img_idle)
            self.statusitem.setTitle_('')

    def load_servers(self):
        l = my.Defaults().arrayForKey_('servers') or []
        sl = []
        for s in l:
            host = s.get('host', None)
            if not host: continue
            
            nets = s.get('nets', [])
            nl = []
            for n in nets:
                subnet = n[0]
                width = n[1]
                net = models.SshuttleNet.alloc().init()
                net.setSubnet_(subnet)
                net.setWidth_(width)
                nl.append(net)
            
            autoNets = s.get('autoNets', models.NET_AUTO)
            autoHosts = s.get('autoHosts', True)
            useDns = s.get('useDns', autoNets == models.NET_ALL)
            latencyControl = s.get('latencyControl', models.LAT_INTERACTIVE)
            srv = models.SshuttleServer.alloc().init()
            srv.setHost_(host)
            srv.setAutoNets_(autoNets)
            srv.setAutoHosts_(autoHosts)
            srv.setNets_(nl)
            srv.setUseDns_(useDns)
            srv.setLatencyControl_(latencyControl)
            sl.append(srv)
        self.serversController.addObjects_(sl)
        self.serversController.setSelectionIndex_(0)

    def save_servers(self):
        l = []
        for s in self.servers:
            host = s.host()
            if not host: continue
            nets = []
            for n in s.nets():
                subnet = n.subnet()
                if not subnet: continue
                nets.append((subnet, n.width()))
            d = dict(host=s.host(),
                     nets=nets,
                     autoNets=s.autoNets(),
                     autoHosts=s.autoHosts(),
                     useDns=s.useDns(),
                     latencyControl=s.latencyControl())
            l.append(d)
        my.Defaults().setObject_forKey_(l, 'servers')
        self.fill_menu()

    def awakeFromNib(self):
        self.routingField.removeAllItems()
        tf = self.routingField.addItemWithTitle_
        tf('Send all traffic through this server')
        tf('Determine automatically')
        tf('Custom...')

        self.latencyControlField.removeAllItems()
        tf = self.latencyControlField.addItemWithTitle_
        tf('Fast transfer')
        tf('Low latency')

        # Hmm, even when I mark this as !enabled in the .nib, it still comes
        # through as enabled.  So let's just disable it here (since we don't
        # support this feature yet).
        self.startAtLoginField.setEnabled_(False)
        self.startAtLoginField.setState_(False)
        self.autoReconnectField.setEnabled_(False)
        self.autoReconnectField.setState_(False)

        self.load_servers()

        # Initialize our menu item
        self.menu = NSMenu.alloc().initWithTitle_('Sshuttle')
        bar = NSStatusBar.systemStatusBar()
        statusitem = bar.statusItemWithLength_(NSVariableStatusItemLength)
        self.statusitem = statusitem
        self.img_idle = my.Image('chicken-tiny-bw', 'png')
        self.img_running = my.Image('chicken-tiny', 'png')
        self.img_err = my.Image('chicken-tiny-err', 'png')
        statusitem.setImage_(self.img_idle)
        statusitem.setHighlightMode_(True)
        statusitem.setMenu_(self.menu)
        self.fill_menu()
        
        models.configchange_callback = my.DelayedCallback(self.save_servers)
        
        def sc(server):
            if server.wantConnect():
                self._connect(server)
            else:
                self._disconnect(server)
        models.setconnect_callback = sc


# Note: NSApplicationMain calls sys.exit(), so this never returns.
NSApplicationMain(sys.argv)

########NEW FILE########
__FILENAME__ = models
from AppKit import *
import my


configchange_callback = setconnect_callback = None
objc_validator = objc.signature('@@:N^@o^@')


def config_changed():
    if configchange_callback:
        configchange_callback()


def _validate_ip(v):
    parts = v.split('.')[:4]
    if len(parts) < 4:
        parts += ['0'] * (4 - len(parts))
    for i in range(4):
        n = my.atoi(parts[i])
        if n < 0:
            n = 0
        elif n > 255:
            n = 255
        parts[i] = str(n)
    return '.'.join(parts)


def _validate_width(v):
    n = my.atoi(v)
    if n < 0:
        n = 0
    elif n > 32:
        n = 32
    return n


class SshuttleNet(NSObject):
    def subnet(self):
        return getattr(self, '_k_subnet', None)
    def setSubnet_(self, v):
        self._k_subnet = v
        config_changed()
    @objc_validator
    def validateSubnet_error_(self, value, error):
        #print 'validateSubnet!'
        return True, _validate_ip(value), error

    def width(self):
        return getattr(self, '_k_width', 24)
    def setWidth_(self, v):
        self._k_width = v
        config_changed()
    @objc_validator
    def validateWidth_error_(self, value, error):
        #print 'validateWidth!'
        return True, _validate_width(value), error

NET_ALL = 0
NET_AUTO = 1
NET_MANUAL = 2

LAT_BANDWIDTH = 0
LAT_INTERACTIVE = 1

class SshuttleServer(NSObject):
    def init(self):
        self = super(SshuttleServer, self).init()
        config_changed()
        return self
    
    def wantConnect(self):
        return getattr(self, '_k_wantconnect', False)
    def setWantConnect_(self, v):
        self._k_wantconnect = v
        self.setError_(None)
        config_changed()
        if setconnect_callback: setconnect_callback(self)

    def connected(self):
        return getattr(self, '_k_connected', False)
    def setConnected_(self, v):
        print 'setConnected of %r to %r' % (self, v)
        self._k_connected = v
        if v: self.setError_(None)  # connected ok, so no error
        config_changed()

    def error(self):
        return getattr(self, '_k_error', None)
    def setError_(self, v):
        self._k_error = v
        config_changed()

    def isValid(self):
        if not self.host():
            return False
        if self.autoNets() == NET_MANUAL and not len(list(self.nets())):
            return False
        return True

    def title(self):
        host = self.host()
        if not host:
            return host
        an = self.autoNets()
        suffix = ""
        if an == NET_ALL:
            suffix = " (all traffic)"
        elif an == NET_MANUAL:
            n = self.nets()
            suffix = ' (%d subnet%s)' % (len(n), len(n)!=1 and 's' or '')
        return self.host() + suffix
    def setTitle_(self, v):
        # title is always auto-generated
        config_changed()
    
    def host(self):
        return getattr(self, '_k_host', None)
    def setHost_(self, v):
        self._k_host = v
        self.setTitle_(None)
        config_changed()
    @objc_validator
    def validateHost_error_(self, value, error):
        #print 'validatehost! %r %r %r' % (self, value, error)
        while value.startswith('-'):
            value = value[1:]
        return True, value, error

    def nets(self):
        return getattr(self, '_k_nets', [])
    def setNets_(self, v):
        self._k_nets = v
        self.setTitle_(None)
        config_changed()
    def netsHidden(self):
        #print 'checking netsHidden'
        return self.autoNets() != NET_MANUAL
    def setNetsHidden_(self, v):
        config_changed()
        #print 'setting netsHidden to %r' % v
        
    def autoNets(self):
        return getattr(self, '_k_autoNets', NET_AUTO)
    def setAutoNets_(self, v):
        self._k_autoNets = v
        self.setNetsHidden_(-1)
        self.setUseDns_(v == NET_ALL)
        self.setTitle_(None)
        config_changed()

    def autoHosts(self):
        return getattr(self, '_k_autoHosts', True)
    def setAutoHosts_(self, v):
        self._k_autoHosts = v
        config_changed()

    def useDns(self):
        return getattr(self, '_k_useDns', False)
    def setUseDns_(self, v):
        self._k_useDns = v
        config_changed()

    def latencyControl(self):
        return getattr(self, '_k_latencyControl', LAT_INTERACTIVE)
    def setLatencyControl_(self, v):
        self._k_latencyControl = v
        config_changed()

########NEW FILE########
__FILENAME__ = my
import sys, os
from AppKit import *
import PyObjCTools.AppHelper


def bundle_path(name, typ):
    if typ:
        return NSBundle.mainBundle().pathForResource_ofType_(name, typ)
    else:
        return os.path.join(NSBundle.mainBundle().resourcePath(), name)


# Load an NSData using a python string
def Data(s):
    return NSData.alloc().initWithBytes_length_(s, len(s))


# Load a property list from a file in the application bundle.
def PList(name):
    path = bundle_path(name, 'plist')
    return NSDictionary.dictionaryWithContentsOfFile_(path)


# Load an NSImage from a file in the application bundle.
def Image(name, ext):
    bytes = open(bundle_path(name, ext)).read()
    img = NSImage.alloc().initWithData_(Data(bytes))
    return img


# Return the NSUserDefaults shared object.
def Defaults():
    return NSUserDefaults.standardUserDefaults()


# Usage:
#   f = DelayedCallback(func, args...)
# later:
#   f()
#
# When you call f(), it will schedule a call to func() next time the
# ObjC event loop iterates.  Multiple calls to f() in a single iteration
# will only result in one call to func().
#
def DelayedCallback(func, *args, **kwargs):
    flag = [0]
    def _go():
        if flag[0]:
            print 'running %r (flag=%r)' % (func, flag)
            flag[0] = 0
            func(*args, **kwargs)
    def call():
        flag[0] += 1
        PyObjCTools.AppHelper.callAfter(_go)
    return call


def atoi(s):
    try:
        return int(s)
    except ValueError:
        return 0

########NEW FILE########
