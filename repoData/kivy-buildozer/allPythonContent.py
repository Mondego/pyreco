__FILENAME__ = jsonstore
"""
Replacement for shelve, using json.
This is currently needed to correctly support db between Python 2 and 3.
"""

__all__ = ["JsonStore"]

import io
import sys
from json import load, dump, dumps
from os.path import exists

IS_PY3 = sys.version_info[0] >= 3

class JsonStore(object):

    def __init__(self, filename):
        super(JsonStore, self).__init__()
        self.filename = filename
        self.data = {}
        if exists(filename):
            try:
                with io.open(filename, encoding='utf-8') as fd:
                    self.data = load(fd)
            except ValueError:
                print("Unable to read the state.db, content will be replaced.")

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
        self.sync()

    def __delitem__(self, key):
        del self.data[key]
        self.sync()

    def __contains__(self, item):
        return item in self.data

    def get(self, item, default=None):
        return self.data.get(item, default)

    def keys(self):
        return self.data.keys()

    def sync(self):
        # http://stackoverflow.com/questions/12309269/write-json-data-to-file-in-python/14870531#14870531
        if IS_PY3:
            with open(self.filename, 'w') as fd:
                dump(self.data, fd, ensure_ascii=False)
        else:
            with io.open(self.filename, 'w', encoding='utf-8') as fd:
                fd.write(unicode(dumps(self.data, ensure_ascii=False)))


########NEW FILE########
__FILENAME__ = pexpect
"""Pexpect is a Python module for spawning child applications and controlling
them automatically. Pexpect can be used for automating interactive applications
such as ssh, ftp, passwd, telnet, etc. It can be used to a automate setup
scripts for duplicating software package installations on different servers. It
can be used for automated software testing. Pexpect is in the spirit of Don
Libes' Expect, but Pexpect is pure Python. Other Expect-like modules for Python
require TCL and Expect or require C extensions to be compiled. Pexpect does not
use C, Expect, or TCL extensions. It should work on any platform that supports
the standard Python pty module. The Pexpect interface focuses on ease of use so
that simple tasks are easy.

There are two main interfaces to Pexpect -- the function, run() and the class,
spawn. You can call the run() function to execute a command and return the
output. This is a handy replacement for os.system().

For example::

    pexpect.run('ls -la')

The more powerful interface is the spawn class. You can use this to spawn an
external child command and then interact with the child by sending lines and
expecting responses.

For example::

    child = pexpect.spawn('scp foo myname@host.example.com:.')
    child.expect ('Password:')
    child.sendline (mypassword)

This works even for commands that ask for passwords or other input outside of
the normal stdio streams.

Credits: Noah Spurrier, Richard Holden, Marco Molteni, Kimberley Burchett,
Robert Stone, Hartmut Goebel, Chad Schroeder, Erick Tryzelaar, Dave Kirby, Ids
vander Molen, George Todd, Noel Taylor, Nicolas D. Cesar, Alexander Gattin,
Geoffrey Marshall, Francisco Lourenco, Glen Mabey, Karthik Gurusamy, Fernando
Perez, Corey Minyard, Jon Cohen, Guillaume Chazarain, Andrew Ryan, Nick
Craig-Wood, Andrew Stone, Jorgen Grahn (Let me know if I forgot anyone.)

Free, open source, and all that good stuff.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Pexpect Copyright (c) 2008 Noah Spurrier
http://pexpect.sourceforge.net/

$Id: pexpect.py 507 2007-12-27 02:40:52Z noah $
"""

try:
    import os, sys, time
    import select
    import string
    import re
    import struct
    import resource
    import types
    import pty
    import tty
    import termios
    import fcntl
    import errno
    import traceback
    import signal
except ImportError, e:
    raise ImportError (str(e) + """

A critical module was not found. Probably this operating system does not
support it. Pexpect is intended for UNIX-like operating systems.""")

__version__ = '2.3'
__revision__ = '$Revision: 399 $'
__all__ = ['ExceptionPexpect', 'EOF', 'TIMEOUT', 'spawn', 'run', 'which',
    'split_command_line', '__version__', '__revision__']

# Exception classes used by this module.
class ExceptionPexpect(Exception):

    """Base class for all exceptions raised by this module.
    """

    def __init__(self, value):

        self.value = value

    def __str__(self):

        return str(self.value)

    def get_trace(self):

        """This returns an abbreviated stack trace with lines that only concern
        the caller. In other words, the stack trace inside the Pexpect module
        is not included. """

        tblist = traceback.extract_tb(sys.exc_info()[2])
        #tblist = filter(self.__filter_not_pexpect, tblist)
        tblist = [item for item in tblist if self.__filter_not_pexpect(item)]
        tblist = traceback.format_list(tblist)
        return ''.join(tblist)

    def __filter_not_pexpect(self, trace_list_item):

        """This returns True if list item 0 the string 'pexpect.py' in it. """

        if trace_list_item[0].find('pexpect.py') == -1:
            return True
        else:
            return False

class EOF(ExceptionPexpect):

    """Raised when EOF is read from a child. This usually means the child has exited."""

class TIMEOUT(ExceptionPexpect):

    """Raised when a read time exceeds the timeout. """

##class TIMEOUT_PATTERN(TIMEOUT):
##    """Raised when the pattern match time exceeds the timeout.
##    This is different than a read TIMEOUT because the child process may
##    give output, thus never give a TIMEOUT, but the output
##    may never match a pattern.
##    """
##class MAXBUFFER(ExceptionPexpect):
##    """Raised when a scan buffer fills before matching an expected pattern."""

def run (command, timeout=-1, withexitstatus=False, events=None, extra_args=None, logfile=None, cwd=None, env=None):

    """
    This function runs the given command; waits for it to finish; then
    returns all output as a string. STDERR is included in output. If the full
    path to the command is not given then the path is searched.

    Note that lines are terminated by CR/LF (\\r\\n) combination even on
    UNIX-like systems because this is the standard for pseudo ttys. If you set
    'withexitstatus' to true, then run will return a tuple of (command_output,
    exitstatus). If 'withexitstatus' is false then this returns just
    command_output.

    The run() function can often be used instead of creating a spawn instance.
    For example, the following code uses spawn::

        from pexpect import *
        child = spawn('scp foo myname@host.example.com:.')
        child.expect ('(?i)password')
        child.sendline (mypassword)

    The previous code can be replace with the following::

        from pexpect import *
        run ('scp foo myname@host.example.com:.', events={'(?i)password': mypassword})

    Examples
    ========

    Start the apache daemon on the local machine::

        from pexpect import *
        run ("/usr/local/apache/bin/apachectl start")

    Check in a file using SVN::

        from pexpect import *
        run ("svn ci -m 'automatic commit' my_file.py")

    Run a command and capture exit status::

        from pexpect import *
        (command_output, exitstatus) = run ('ls -l /bin', withexitstatus=1)

    Tricky Examples
    ===============

    The following will run SSH and execute 'ls -l' on the remote machine. The
    password 'secret' will be sent if the '(?i)password' pattern is ever seen::

        run ("ssh username@machine.example.com 'ls -l'", events={'(?i)password':'secret\\n'})

    This will start mencoder to rip a video from DVD. This will also display
    progress ticks every 5 seconds as it runs. For example::

        from pexpect import *
        def print_ticks(d):
            print d['event_count'],
        run ("mencoder dvd://1 -o video.avi -oac copy -ovc copy", events={TIMEOUT:print_ticks}, timeout=5)

    The 'events' argument should be a dictionary of patterns and responses.
    Whenever one of the patterns is seen in the command out run() will send the
    associated response string. Note that you should put newlines in your
    string if Enter is necessary. The responses may also contain callback
    functions. Any callback is function that takes a dictionary as an argument.
    The dictionary contains all the locals from the run() function, so you can
    access the child spawn object or any other variable defined in run()
    (event_count, child, and extra_args are the most useful). A callback may
    return True to stop the current run process otherwise run() continues until
    the next event. A callback may also return a string which will be sent to
    the child. 'extra_args' is not used by directly run(). It provides a way to
    pass data to a callback function through run() through the locals
    dictionary passed to a callback. """

    if timeout == -1:
        child = spawn(command, maxread=2000, logfile=logfile, cwd=cwd, env=env)
    else:
        child = spawn(command, timeout=timeout, maxread=2000, logfile=logfile, cwd=cwd, env=env)
    if events is not None:
        patterns = events.keys()
        responses = events.values()
    else:
        patterns=None # We assume that EOF or TIMEOUT will save us.
        responses=None
    child_result_list = []
    event_count = 0
    while 1:
        try:
            index = child.expect (patterns)
            if type(child.after) in types.StringTypes:
                child_result_list.append(child.before + child.after)
            else: # child.after may have been a TIMEOUT or EOF, so don't cat those.
                child_result_list.append(child.before)
            if type(responses[index]) in types.StringTypes:
                child.send(responses[index])
            elif type(responses[index]) is types.FunctionType:
                callback_result = responses[index](locals())
                sys.stdout.flush()
                if type(callback_result) in types.StringTypes:
                    child.send(callback_result)
                elif callback_result:
                    break
            else:
                raise TypeError ('The callback must be a string or function type.')
            event_count = event_count + 1
        except TIMEOUT, e:
            child_result_list.append(child.before)
            break
        except EOF, e:
            child_result_list.append(child.before)
            break
    child_result = ''.join(child_result_list)
    if withexitstatus:
        child.close()
        return (child_result, child.exitstatus)
    else:
        return child_result

class spawn (object):

    """This is the main class interface for Pexpect. Use this class to start
    and control child applications. """

    def __init__(self, command, args=[], timeout=30, maxread=2000, searchwindowsize=None, logfile=None, cwd=None, env=None):

        """This is the constructor. The command parameter may be a string that
        includes a command and any arguments to the command. For example::

            child = pexpect.spawn ('/usr/bin/ftp')
            child = pexpect.spawn ('/usr/bin/ssh user@example.com')
            child = pexpect.spawn ('ls -latr /tmp')

        You may also construct it with a list of arguments like so::

            child = pexpect.spawn ('/usr/bin/ftp', [])
            child = pexpect.spawn ('/usr/bin/ssh', ['user@example.com'])
            child = pexpect.spawn ('ls', ['-latr', '/tmp'])

        After this the child application will be created and will be ready to
        talk to. For normal use, see expect() and send() and sendline().

        Remember that Pexpect does NOT interpret shell meta characters such as
        redirect, pipe, or wild cards (>, |, or *). This is a common mistake.
        If you want to run a command and pipe it through another command then
        you must also start a shell. For example::

            child = pexpect.spawn('/bin/bash -c "ls -l | grep LOG > log_list.txt"')
            child.expect(pexpect.EOF)

        The second form of spawn (where you pass a list of arguments) is useful
        in situations where you wish to spawn a command and pass it its own
        argument list. This can make syntax more clear. For example, the
        following is equivalent to the previous example::

            shell_cmd = 'ls -l | grep LOG > log_list.txt'
            child = pexpect.spawn('/bin/bash', ['-c', shell_cmd])
            child.expect(pexpect.EOF)

        The maxread attribute sets the read buffer size. This is maximum number
        of bytes that Pexpect will try to read from a TTY at one time. Setting
        the maxread size to 1 will turn off buffering. Setting the maxread
        value higher may help performance in cases where large amounts of
        output are read back from the child. This feature is useful in
        conjunction with searchwindowsize.

        The searchwindowsize attribute sets the how far back in the incomming
        seach buffer Pexpect will search for pattern matches. Every time
        Pexpect reads some data from the child it will append the data to the
        incomming buffer. The default is to search from the beginning of the
        imcomming buffer each time new data is read from the child. But this is
        very inefficient if you are running a command that generates a large
        amount of data where you want to match The searchwindowsize does not
        effect the size of the incomming data buffer. You will still have
        access to the full buffer after expect() returns.

        The logfile member turns on or off logging. All input and output will
        be copied to the given file object. Set logfile to None to stop
        logging. This is the default. Set logfile to sys.stdout to echo
        everything to standard output. The logfile is flushed after each write.

        Example log input and output to a file::

            child = pexpect.spawn('some_command')
            fout = file('mylog.txt','w')
            child.logfile = fout

        Example log to stdout::

            child = pexpect.spawn('some_command')
            child.logfile = sys.stdout

        The logfile_read and logfile_send members can be used to separately log
        the input from the child and output sent to the child. Sometimes you
        don't want to see everything you write to the child. You only want to
        log what the child sends back. For example::
        
            child = pexpect.spawn('some_command')
            child.logfile_read = sys.stdout

        To separately log output sent to the child use logfile_send::
        
            self.logfile_send = fout

        The delaybeforesend helps overcome a weird behavior that many users
        were experiencing. The typical problem was that a user would expect() a
        "Password:" prompt and then immediately call sendline() to send the
        password. The user would then see that their password was echoed back
        to them. Passwords don't normally echo. The problem is caused by the
        fact that most applications print out the "Password" prompt and then
        turn off stdin echo, but if you send your password before the
        application turned off echo, then you get your password echoed.
        Normally this wouldn't be a problem when interacting with a human at a
        real keyboard. If you introduce a slight delay just before writing then
        this seems to clear up the problem. This was such a common problem for
        many users that I decided that the default pexpect behavior should be
        to sleep just before writing to the child application. 1/20th of a
        second (50 ms) seems to be enough to clear up the problem. You can set
        delaybeforesend to 0 to return to the old behavior. Most Linux machines
        don't like this to be below 0.03. I don't know why.

        Note that spawn is clever about finding commands on your path.
        It uses the same logic that "which" uses to find executables.

        If you wish to get the exit status of the child you must call the
        close() method. The exit or signal status of the child will be stored
        in self.exitstatus or self.signalstatus. If the child exited normally
        then exitstatus will store the exit return code and signalstatus will
        be None. If the child was terminated abnormally with a signal then
        signalstatus will store the signal value and exitstatus will be None.
        If you need more detail you can also read the self.status member which
        stores the status returned by os.waitpid. You can interpret this using
        os.WIFEXITED/os.WEXITSTATUS or os.WIFSIGNALED/os.TERMSIG. """

        self.STDIN_FILENO = pty.STDIN_FILENO
        self.STDOUT_FILENO = pty.STDOUT_FILENO
        self.STDERR_FILENO = pty.STDERR_FILENO
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr

        self.searcher = None
        self.ignorecase = False
        self.before = None
        self.after = None
        self.match = None
        self.match_index = None
        self.terminated = True
        self.exitstatus = None
        self.signalstatus = None
        self.status = None # status returned by os.waitpid
        self.flag_eof = False
        self.pid = None
        self.child_fd = -1 # initially closed
        self.timeout = timeout
        self.delimiter = EOF
        self.logfile = logfile
        self.logfile_read = None # input from child (read_nonblocking)
        self.logfile_send = None # output to send (send, sendline)
        self.maxread = maxread # max bytes to read at one time into buffer
        self.buffer = '' # This is the read buffer. See maxread.
        self.searchwindowsize = searchwindowsize # Anything before searchwindowsize point is preserved, but not searched.
        # Most Linux machines don't like delaybeforesend to be below 0.03 (30 ms).
        self.delaybeforesend = 0.05 # Sets sleep time used just before sending data to child. Time in seconds.
        self.delayafterclose = 0.1 # Sets delay in close() method to allow kernel time to update process status. Time in seconds.
        self.delayafterterminate = 0.1 # Sets delay in terminate() method to allow kernel time to update process status. Time in seconds.
        self.softspace = False # File-like object.
        self.name = '<' + repr(self) + '>' # File-like object.
        self.encoding = None # File-like object.
        self.closed = True # File-like object.
        self.cwd = cwd
        self.env = env
        self.__irix_hack = (sys.platform.lower().find('irix')>=0) # This flags if we are running on irix
        # Solaris uses internal __fork_pty(). All others use pty.fork().
        if (sys.platform.lower().find('solaris')>=0) or (sys.platform.lower().find('sunos5')>=0):
            self.use_native_pty_fork = False
        else:
            self.use_native_pty_fork = True


        # allow dummy instances for subclasses that may not use command or args.
        if command is None:
            self.command = None
            self.args = None
            self.name = '<pexpect factory incomplete>'
        else:
            self._spawn (command, args)

    def __del__(self):

        """This makes sure that no system resources are left open. Python only
        garbage collects Python objects. OS file descriptors are not Python
        objects, so they must be handled explicitly. If the child file
        descriptor was opened outside of this class (passed to the constructor)
        then this does not close it. """

        if not self.closed:
            # It is possible for __del__ methods to execute during the
            # teardown of the Python VM itself. Thus self.close() may
            # trigger an exception because os.close may be None.
            # -- Fernando Perez
            try:
                self.close()
            except AttributeError:
                pass

    def __str__(self):

        """This returns a human-readable string that represents the state of
        the object. """

        s = []
        s.append(repr(self))
        s.append('version: ' + __version__ + ' (' + __revision__ + ')')
        s.append('command: ' + str(self.command))
        s.append('args: ' + str(self.args))
        s.append('searcher: ' + str(self.searcher))
        s.append('buffer (last 100 chars): ' + str(self.buffer)[-100:])
        s.append('before (last 100 chars): ' + str(self.before)[-100:])
        s.append('after: ' + str(self.after))
        s.append('match: ' + str(self.match))
        s.append('match_index: ' + str(self.match_index))
        s.append('exitstatus: ' + str(self.exitstatus))
        s.append('flag_eof: ' + str(self.flag_eof))
        s.append('pid: ' + str(self.pid))
        s.append('child_fd: ' + str(self.child_fd))
        s.append('closed: ' + str(self.closed))
        s.append('timeout: ' + str(self.timeout))
        s.append('delimiter: ' + str(self.delimiter))
        s.append('logfile: ' + str(self.logfile))
        s.append('logfile_read: ' + str(self.logfile_read))
        s.append('logfile_send: ' + str(self.logfile_send))
        s.append('maxread: ' + str(self.maxread))
        s.append('ignorecase: ' + str(self.ignorecase))
        s.append('searchwindowsize: ' + str(self.searchwindowsize))
        s.append('delaybeforesend: ' + str(self.delaybeforesend))
        s.append('delayafterclose: ' + str(self.delayafterclose))
        s.append('delayafterterminate: ' + str(self.delayafterterminate))
        return '\n'.join(s)

    def _spawn(self,command,args=[]):

        """This starts the given command in a child process. This does all the
        fork/exec type of stuff for a pty. This is called by __init__. If args
        is empty then command will be parsed (split on spaces) and args will be
        set to parsed arguments. """

        # The pid and child_fd of this object get set by this method.
        # Note that it is difficult for this method to fail.
        # You cannot detect if the child process cannot start.
        # So the only way you can tell if the child process started
        # or not is to try to read from the file descriptor. If you get
        # EOF immediately then it means that the child is already dead.
        # That may not necessarily be bad because you may haved spawned a child
        # that performs some task; creates no stdout output; and then dies.

        # If command is an int type then it may represent a file descriptor.
        if type(command) == type(0):
            raise ExceptionPexpect ('Command is an int type. If this is a file descriptor then maybe you want to use fdpexpect.fdspawn which takes an existing file descriptor instead of a command string.')

        if type (args) != type([]):
            raise TypeError ('The argument, args, must be a list.')

        if args == []:
            self.args = split_command_line(command)
            self.command = self.args[0]
        else:
            self.args = args[:] # work with a copy
            self.args.insert (0, command)
            self.command = command

        command_with_path = which(self.command)
        if command_with_path is None:
            raise ExceptionPexpect ('The command was not found or was not executable: %s.' % self.command)
        self.command = command_with_path
        self.args[0] = self.command

        self.name = '<' + ' '.join (self.args) + '>'

        assert self.pid is None, 'The pid member should be None.'
        assert self.command is not None, 'The command member should not be None.'

        if self.use_native_pty_fork:
            try:
                self.pid, self.child_fd = pty.fork()
            except OSError, e:
                raise ExceptionPexpect('Error! pty.fork() failed: ' + str(e))
        else: # Use internal __fork_pty
            self.pid, self.child_fd = self.__fork_pty()

        if self.pid == 0: # Child
            try:
                self.child_fd = sys.stdout.fileno() # used by setwinsize()
                self.setwinsize(24, 80)
            except:
                # Some platforms do not like setwinsize (Cygwin).
                # This will cause problem when running applications that
                # are very picky about window size.
                # This is a serious limitation, but not a show stopper.
                pass
            # Do not allow child to inherit open file descriptors from parent.
            max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
            for i in range (3, max_fd):
                try:
                    os.close (i)
                except OSError:
                    pass

            # I don't know why this works, but ignoring SIGHUP fixes a
            # problem when trying to start a Java daemon with sudo
            # (specifically, Tomcat).
            signal.signal(signal.SIGHUP, signal.SIG_IGN)

            if self.cwd is not None:
                os.chdir(self.cwd)
            if self.env is None:
                os.execv(self.command, self.args)
            else:
                os.execvpe(self.command, self.args, self.env)

        # Parent
        self.terminated = False
        self.closed = False

    def __fork_pty(self):

        """This implements a substitute for the forkpty system call. This
        should be more portable than the pty.fork() function. Specifically,
        this should work on Solaris.

        Modified 10.06.05 by Geoff Marshall: Implemented __fork_pty() method to
        resolve the issue with Python's pty.fork() not supporting Solaris,
        particularly ssh. Based on patch to posixmodule.c authored by Noah
        Spurrier::

            http://mail.python.org/pipermail/python-dev/2003-May/035281.html

        """

        parent_fd, child_fd = os.openpty()
        if parent_fd < 0 or child_fd < 0:
            raise ExceptionPexpect, "Error! Could not open pty with os.openpty()."

        pid = os.fork()
        if pid < 0:
            raise ExceptionPexpect, "Error! Failed os.fork()."
        elif pid == 0:
            # Child.
            os.close(parent_fd)
            self.__pty_make_controlling_tty(child_fd)

            os.dup2(child_fd, 0)
            os.dup2(child_fd, 1)
            os.dup2(child_fd, 2)

            if child_fd > 2:
                os.close(child_fd)
        else:
            # Parent.
            os.close(child_fd)

        return pid, parent_fd

    def __pty_make_controlling_tty(self, tty_fd):

        """This makes the pseudo-terminal the controlling tty. This should be
        more portable than the pty.fork() function. Specifically, this should
        work on Solaris. """

        child_name = os.ttyname(tty_fd)

        # Disconnect from controlling tty if still connected.
        fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY);
        if fd >= 0:
            os.close(fd)

        os.setsid()

        # Verify we are disconnected from controlling tty
        try:
            fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY);
            if fd >= 0:
                os.close(fd)
                raise ExceptionPexpect, "Error! We are not disconnected from a controlling tty."
        except:
            # Good! We are disconnected from a controlling tty.
            pass

        # Verify we can open child pty.
        fd = os.open(child_name, os.O_RDWR);
        if fd < 0:
            raise ExceptionPexpect, "Error! Could not open child pty, " + child_name
        else:
            os.close(fd)

        # Verify we now have a controlling tty.
        fd = os.open("/dev/tty", os.O_WRONLY)
        if fd < 0:
            raise ExceptionPexpect, "Error! Could not open controlling tty, /dev/tty"
        else:
            os.close(fd)

    def fileno (self):   # File-like object.

        """This returns the file descriptor of the pty for the child.
        """

        return self.child_fd

    def close (self, force=True):   # File-like object.

        """This closes the connection with the child application. Note that
        calling close() more than once is valid. This emulates standard Python
        behavior with files. Set force to True if you want to make sure that
        the child is terminated (SIGKILL is sent if the child ignores SIGHUP
        and SIGINT). """

        if not self.closed:
            self.flush()
            os.close (self.child_fd)
            time.sleep(self.delayafterclose) # Give kernel time to update process status.
            if self.isalive():
                if not self.terminate(force):
                    raise ExceptionPexpect ('close() could not terminate the child using terminate()')
            self.child_fd = -1
            self.closed = True
            #self.pid = None

    def flush (self):   # File-like object.

        """This does nothing. It is here to support the interface for a
        File-like object. """

        pass

    def isatty (self):   # File-like object.

        """This returns True if the file descriptor is open and connected to a
        tty(-like) device, else False. """

        return os.isatty(self.child_fd)

    def waitnoecho (self, timeout=-1):

        """This waits until the terminal ECHO flag is set False. This returns
        True if the echo mode is off. This returns False if the ECHO flag was
        not set False before the timeout. This can be used to detect when the
        child is waiting for a password. Usually a child application will turn
        off echo mode when it is waiting for the user to enter a password. For
        example, instead of expecting the "password:" prompt you can wait for
        the child to set ECHO off::

            p = pexpect.spawn ('ssh user@example.com')
            p.waitnoecho()
            p.sendline(mypassword)

        If timeout is None then this method to block forever until ECHO flag is
        False.

        """

        if timeout == -1:
            timeout = self.timeout
        if timeout is not None:
            end_time = time.time() + timeout 
        while True:
            if not self.getecho():
                return True
            if timeout < 0 and timeout is not None:
                return False
            if timeout is not None:
                timeout = end_time - time.time()
            time.sleep(0.1)

    def getecho (self):

        """This returns the terminal echo mode. This returns True if echo is
        on or False if echo is off. Child applications that are expecting you
        to enter a password often set ECHO False. See waitnoecho(). """

        attr = termios.tcgetattr(self.child_fd)
        if attr[3] & termios.ECHO:
            return True
        return False

    def setecho (self, state):

        """This sets the terminal echo mode on or off. Note that anything the
        child sent before the echo will be lost, so you should be sure that
        your input buffer is empty before you call setecho(). For example, the
        following will work as expected::

            p = pexpect.spawn('cat')
            p.sendline ('1234') # We will see this twice (once from tty echo and again from cat).
            p.expect (['1234'])
            p.expect (['1234'])
            p.setecho(False) # Turn off tty echo
            p.sendline ('abcd') # We will set this only once (echoed by cat).
            p.sendline ('wxyz') # We will set this only once (echoed by cat)
            p.expect (['abcd'])
            p.expect (['wxyz'])

        The following WILL NOT WORK because the lines sent before the setecho
        will be lost::

            p = pexpect.spawn('cat')
            p.sendline ('1234') # We will see this twice (once from tty echo and again from cat).
            p.setecho(False) # Turn off tty echo
            p.sendline ('abcd') # We will set this only once (echoed by cat).
            p.sendline ('wxyz') # We will set this only once (echoed by cat)
            p.expect (['1234'])
            p.expect (['1234'])
            p.expect (['abcd'])
            p.expect (['wxyz'])
        """

        self.child_fd
        attr = termios.tcgetattr(self.child_fd)
        if state:
            attr[3] = attr[3] | termios.ECHO
        else:
            attr[3] = attr[3] & ~termios.ECHO
        # I tried TCSADRAIN and TCSAFLUSH, but these were inconsistent
        # and blocked on some platforms. TCSADRAIN is probably ideal if it worked.
        termios.tcsetattr(self.child_fd, termios.TCSANOW, attr)

    def read_nonblocking (self, size = 1, timeout = -1):

        """This reads at most size characters from the child application. It
        includes a timeout. If the read does not complete within the timeout
        period then a TIMEOUT exception is raised. If the end of file is read
        then an EOF exception will be raised. If a log file was set using
        setlog() then all data will also be written to the log file.

        If timeout is None then the read may block indefinitely. If timeout is -1
        then the self.timeout value is used. If timeout is 0 then the child is
        polled and if there was no data immediately ready then this will raise
        a TIMEOUT exception.

        The timeout refers only to the amount of time to read at least one
        character. This is not effected by the 'size' parameter, so if you call
        read_nonblocking(size=100, timeout=30) and only one character is
        available right away then one character will be returned immediately.
        It will not wait for 30 seconds for another 99 characters to come in.

        This is a wrapper around os.read(). It uses select.select() to
        implement the timeout. """

        if self.closed:
            raise ValueError ('I/O operation on closed file in read_nonblocking().')

        if timeout == -1:
            timeout = self.timeout

        # Note that some systems such as Solaris do not give an EOF when
        # the child dies. In fact, you can still try to read
        # from the child_fd -- it will block forever or until TIMEOUT.
        # For this case, I test isalive() before doing any reading.
        # If isalive() is false, then I pretend that this is the same as EOF.
        if not self.isalive():
            r,w,e = self.__select([self.child_fd], [], [], 0) # timeout of 0 means "poll"
            if not r:
                self.flag_eof = True
                raise EOF ('End Of File (EOF) in read_nonblocking(). Braindead platform.')
        elif self.__irix_hack:
            # This is a hack for Irix. It seems that Irix requires a long delay before checking isalive.
            # This adds a 2 second delay, but only when the child is terminated.
            r, w, e = self.__select([self.child_fd], [], [], 2)
            if not r and not self.isalive():
                self.flag_eof = True
                raise EOF ('End Of File (EOF) in read_nonblocking(). Pokey platform.')

        r,w,e = self.__select([self.child_fd], [], [], timeout)

        if not r:
            if not self.isalive():
                # Some platforms, such as Irix, will claim that their processes are alive;
                # then timeout on the select; and then finally admit that they are not alive.
                self.flag_eof = True
                raise EOF ('End of File (EOF) in read_nonblocking(). Very pokey platform.')
            else:
                raise TIMEOUT ('Timeout exceeded in read_nonblocking().')

        if self.child_fd in r:
            try:
                s = os.read(self.child_fd, size)
            except OSError, e: # Linux does this
                self.flag_eof = True
                raise EOF ('End Of File (EOF) in read_nonblocking(). Exception style platform.')
            if s == '': # BSD style
                self.flag_eof = True
                raise EOF ('End Of File (EOF) in read_nonblocking(). Empty string style platform.')

            if self.logfile is not None:
                self.logfile.write (s)
                self.logfile.flush()
            if self.logfile_read is not None:
                self.logfile_read.write (s)
                self.logfile_read.flush()

            return s

        raise ExceptionPexpect ('Reached an unexpected state in read_nonblocking().')

    def read (self, size = -1):   # File-like object.

        """This reads at most "size" bytes from the file (less if the read hits
        EOF before obtaining size bytes). If the size argument is negative or
        omitted, read all data until EOF is reached. The bytes are returned as
        a string object. An empty string is returned when EOF is encountered
        immediately. """

        if size == 0:
            return ''
        if size < 0:
            self.expect (self.delimiter) # delimiter default is EOF
            return self.before

        # I could have done this more directly by not using expect(), but
        # I deliberately decided to couple read() to expect() so that
        # I would catch any bugs early and ensure consistant behavior.
        # It's a little less efficient, but there is less for me to
        # worry about if I have to later modify read() or expect().
        # Note, it's OK if size==-1 in the regex. That just means it
        # will never match anything in which case we stop only on EOF.
        cre = re.compile('.{%d}' % size, re.DOTALL)
        index = self.expect ([cre, self.delimiter]) # delimiter default is EOF
        if index == 0:
            return self.after ### self.before should be ''. Should I assert this?
        return self.before

    def readline (self, size = -1):    # File-like object.

        """This reads and returns one entire line. A trailing newline is kept
        in the string, but may be absent when a file ends with an incomplete
        line. Note: This readline() looks for a \\r\\n pair even on UNIX
        because this is what the pseudo tty device returns. So contrary to what
        you may expect you will receive the newline as \\r\\n. An empty string
        is returned when EOF is hit immediately. Currently, the size argument is
        mostly ignored, so this behavior is not standard for a file-like
        object. If size is 0 then an empty string is returned. """

        if size == 0:
            return ''
        index = self.expect (['\r\n', self.delimiter]) # delimiter default is EOF
        if index == 0:
            return self.before + '\r\n'
        else:
            return self.before

    def __iter__ (self):    # File-like object.

        """This is to support iterators over a file-like object.
        """

        return self

    def next (self):    # File-like object.

        """This is to support iterators over a file-like object.
        """

        result = self.readline()
        if result == "":
            raise StopIteration
        return result

    def readlines (self, sizehint = -1):    # File-like object.

        """This reads until EOF using readline() and returns a list containing
        the lines thus read. The optional "sizehint" argument is ignored. """

        lines = []
        while True:
            line = self.readline()
            if not line:
                break
            lines.append(line)
        return lines

    def write(self, s):   # File-like object.

        """This is similar to send() except that there is no return value.
        """

        self.send (s)

    def writelines (self, sequence):   # File-like object.

        """This calls write() for each element in the sequence. The sequence
        can be any iterable object producing strings, typically a list of
        strings. This does not add line separators There is no return value.
        """

        for s in sequence:
            self.write (s)

    def send(self, s):

        """This sends a string to the child process. This returns the number of
        bytes written. If a log file was set then the data is also written to
        the log. """

        time.sleep(self.delaybeforesend)
        if self.logfile is not None:
            self.logfile.write (s)
            self.logfile.flush()
        if self.logfile_send is not None:
            self.logfile_send.write (s)
            self.logfile_send.flush()
        c = os.write(self.child_fd, s)
        return c

    def sendline(self, s=''):

        """This is like send(), but it adds a line feed (os.linesep). This
        returns the number of bytes written. """

        n = self.send(s)
        n = n + self.send (os.linesep)
        return n

    def sendcontrol(self, char):

        """This sends a control character to the child such as Ctrl-C or
        Ctrl-D. For example, to send a Ctrl-G (ASCII 7)::

            child.sendcontrol('g')

        See also, sendintr() and sendeof().
        """

        char = char.lower()
        a = ord(char)
        if a>=97 and a<=122:
            a = a - ord('a') + 1
            return self.send (chr(a))
        d = {'@':0, '`':0,
            '[':27, '{':27,
            '\\':28, '|':28,
            ']':29, '}': 29,
            '^':30, '~':30,
            '_':31,
            '?':127}
        if char not in d:
            return 0
        return self.send (chr(d[char]))

    def sendeof(self):

        """This sends an EOF to the child. This sends a character which causes
        the pending parent output buffer to be sent to the waiting child
        program without waiting for end-of-line. If it is the first character
        of the line, the read() in the user program returns 0, which signifies
        end-of-file. This means to work as expected a sendeof() has to be
        called at the beginning of a line. This method does not send a newline.
        It is the responsibility of the caller to ensure the eof is sent at the
        beginning of a line. """

        ### Hmmm... how do I send an EOF?
        ###C  if ((m = write(pty, *buf, p - *buf)) < 0)
        ###C      return (errno == EWOULDBLOCK) ? n : -1;
        #fd = sys.stdin.fileno()
        #old = termios.tcgetattr(fd) # remember current state
        #attr = termios.tcgetattr(fd)
        #attr[3] = attr[3] | termios.ICANON # ICANON must be set to recognize EOF
        #try: # use try/finally to ensure state gets restored
        #    termios.tcsetattr(fd, termios.TCSADRAIN, attr)
        #    if hasattr(termios, 'CEOF'):
        #        os.write (self.child_fd, '%c' % termios.CEOF)
        #    else:
        #        # Silly platform does not define CEOF so assume CTRL-D
        #        os.write (self.child_fd, '%c' % 4)
        #finally: # restore state
        #    termios.tcsetattr(fd, termios.TCSADRAIN, old)
        if hasattr(termios, 'VEOF'):
            char = termios.tcgetattr(self.child_fd)[6][termios.VEOF]
        else:
            # platform does not define VEOF so assume CTRL-D
            char = chr(4)
        self.send(char)

    def sendintr(self):

        """This sends a SIGINT to the child. It does not require
        the SIGINT to be the first character on a line. """

        if hasattr(termios, 'VINTR'):
            char = termios.tcgetattr(self.child_fd)[6][termios.VINTR]
        else:
            # platform does not define VINTR so assume CTRL-C
            char = chr(3)
        self.send (char)

    def eof (self):

        """This returns True if the EOF exception was ever raised.
        """

        return self.flag_eof

    def terminate(self, force=False):

        """This forces a child process to terminate. It starts nicely with
        SIGHUP and SIGINT. If "force" is True then moves onto SIGKILL. This
        returns True if the child was terminated. This returns False if the
        child could not be terminated. """

        if not self.isalive():
            return True
        try:
            self.kill(signal.SIGHUP)
            time.sleep(self.delayafterterminate)
            if not self.isalive():
                return True
            self.kill(signal.SIGCONT)
            time.sleep(self.delayafterterminate)
            if not self.isalive():
                return True
            self.kill(signal.SIGINT)
            time.sleep(self.delayafterterminate)
            if not self.isalive():
                return True
            if force:
                self.kill(signal.SIGKILL)
                time.sleep(self.delayafterterminate)
                if not self.isalive():
                    return True
                else:
                    return False
            return False
        except OSError, e:
            # I think there are kernel timing issues that sometimes cause
            # this to happen. I think isalive() reports True, but the
            # process is dead to the kernel.
            # Make one last attempt to see if the kernel is up to date.
            time.sleep(self.delayafterterminate)
            if not self.isalive():
                return True
            else:
                return False

    def wait(self):

        """This waits until the child exits. This is a blocking call. This will
        not read any data from the child, so this will block forever if the
        child has unread output and has terminated. In other words, the child
        may have printed output then called exit(); but, technically, the child
        is still alive until its output is read. """

        if self.isalive():
            pid, status = os.waitpid(self.pid, 0)
        else:
            raise ExceptionPexpect ('Cannot wait for dead child process.')
        self.exitstatus = os.WEXITSTATUS(status)
        if os.WIFEXITED (status):
            self.status = status
            self.exitstatus = os.WEXITSTATUS(status)
            self.signalstatus = None
            self.terminated = True
        elif os.WIFSIGNALED (status):
            self.status = status
            self.exitstatus = None
            self.signalstatus = os.WTERMSIG(status)
            self.terminated = True
        elif os.WIFSTOPPED (status):
            raise ExceptionPexpect ('Wait was called for a child process that is stopped. This is not supported. Is some other process attempting job control with our child pid?')
        return self.exitstatus

    def isalive(self):

        """This tests if the child process is running or not. This is
        non-blocking. If the child was terminated then this will read the
        exitstatus or signalstatus of the child. This returns True if the child
        process appears to be running or False if not. It can take literally
        SECONDS for Solaris to return the right status. """

        if self.terminated:
            return False

        if self.flag_eof:
            # This is for Linux, which requires the blocking form of waitpid to get
            # status of a defunct process. This is super-lame. The flag_eof would have
            # been set in read_nonblocking(), so this should be safe.
            waitpid_options = 0
        else:
            waitpid_options = os.WNOHANG

        try:
            pid, status = os.waitpid(self.pid, waitpid_options)
        except OSError, e: # No child processes
            if e[0] == errno.ECHILD:
                raise ExceptionPexpect ('isalive() encountered condition where "terminated" is 0, but there was no child process. Did someone else call waitpid() on our process?')
            else:
                raise e

        # I have to do this twice for Solaris. I can't even believe that I figured this out...
        # If waitpid() returns 0 it means that no child process wishes to
        # report, and the value of status is undefined.
        if pid == 0:
            try:
                pid, status = os.waitpid(self.pid, waitpid_options) ### os.WNOHANG) # Solaris!
            except OSError, e: # This should never happen...
                if e[0] == errno.ECHILD:
                    raise ExceptionPexpect ('isalive() encountered condition that should never happen. There was no child process. Did someone else call waitpid() on our process?')
                else:
                    raise e

            # If pid is still 0 after two calls to waitpid() then
            # the process really is alive. This seems to work on all platforms, except
            # for Irix which seems to require a blocking call on waitpid or select, so I let read_nonblocking
            # take care of this situation (unfortunately, this requires waiting through the timeout).
            if pid == 0:
                return True

        if pid == 0:
            return True

        if os.WIFEXITED (status):
            self.status = status
            self.exitstatus = os.WEXITSTATUS(status)
            self.signalstatus = None
            self.terminated = True
        elif os.WIFSIGNALED (status):
            self.status = status
            self.exitstatus = None
            self.signalstatus = os.WTERMSIG(status)
            self.terminated = True
        elif os.WIFSTOPPED (status):
            raise ExceptionPexpect ('isalive() encountered condition where child process is stopped. This is not supported. Is some other process attempting job control with our child pid?')
        return False

    def kill(self, sig):

        """This sends the given signal to the child application. In keeping
        with UNIX tradition it has a misleading name. It does not necessarily
        kill the child unless you send the right signal. """

        # Same as os.kill, but the pid is given for you.
        if self.isalive():
            os.kill(self.pid, sig)

    def compile_pattern_list(self, patterns):

        """This compiles a pattern-string or a list of pattern-strings.
        Patterns must be a StringType, EOF, TIMEOUT, SRE_Pattern, or a list of
        those. Patterns may also be None which results in an empty list (you
        might do this if waiting for an EOF or TIMEOUT condition without
        expecting any pattern).

        This is used by expect() when calling expect_list(). Thus expect() is
        nothing more than::

             cpl = self.compile_pattern_list(pl)
             return self.expect_list(cpl, timeout)

        If you are using expect() within a loop it may be more
        efficient to compile the patterns first and then call expect_list().
        This avoid calls in a loop to compile_pattern_list()::

             cpl = self.compile_pattern_list(my_pattern)
             while some_condition:
                ...
                i = self.expect_list(clp, timeout)
                ...
        """

        if patterns is None:
            return []
        if type(patterns) is not types.ListType:
            patterns = [patterns]

        compile_flags = re.DOTALL # Allow dot to match \n
        if self.ignorecase:
            compile_flags = compile_flags | re.IGNORECASE
        compiled_pattern_list = []
        for p in patterns:
            if type(p) in types.StringTypes:
                compiled_pattern_list.append(re.compile(p, compile_flags))
            elif p is EOF:
                compiled_pattern_list.append(EOF)
            elif p is TIMEOUT:
                compiled_pattern_list.append(TIMEOUT)
            elif type(p) is type(re.compile('')):
                compiled_pattern_list.append(p)
            else:
                raise TypeError ('Argument must be one of StringTypes, EOF, TIMEOUT, SRE_Pattern, or a list of those type. %s' % str(type(p)))

        return compiled_pattern_list

    def expect(self, pattern, timeout = -1, searchwindowsize=None):

        """This seeks through the stream until a pattern is matched. The
        pattern is overloaded and may take several types. The pattern can be a
        StringType, EOF, a compiled re, or a list of any of those types.
        Strings will be compiled to re types. This returns the index into the
        pattern list. If the pattern was not a list this returns index 0 on a
        successful match. This may raise exceptions for EOF or TIMEOUT. To
        avoid the EOF or TIMEOUT exceptions add EOF or TIMEOUT to the pattern
        list. That will cause expect to match an EOF or TIMEOUT condition
        instead of raising an exception.

        If you pass a list of patterns and more than one matches, the first match
        in the stream is chosen. If more than one pattern matches at that point,
        the leftmost in the pattern list is chosen. For example::

            # the input is 'foobar'
            index = p.expect (['bar', 'foo', 'foobar'])
            # returns 1 ('foo') even though 'foobar' is a "better" match

        Please note, however, that buffering can affect this behavior, since
        input arrives in unpredictable chunks. For example::

            # the input is 'foobar'
            index = p.expect (['foobar', 'foo'])
            # returns 0 ('foobar') if all input is available at once,
            # but returs 1 ('foo') if parts of the final 'bar' arrive late

        After a match is found the instance attributes 'before', 'after' and
        'match' will be set. You can see all the data read before the match in
        'before'. You can see the data that was matched in 'after'. The
        re.MatchObject used in the re match will be in 'match'. If an error
        occurred then 'before' will be set to all the data read so far and
        'after' and 'match' will be None.

        If timeout is -1 then timeout will be set to the self.timeout value.

        A list entry may be EOF or TIMEOUT instead of a string. This will
        catch these exceptions and return the index of the list entry instead
        of raising the exception. The attribute 'after' will be set to the
        exception type. The attribute 'match' will be None. This allows you to
        write code like this::

                index = p.expect (['good', 'bad', pexpect.EOF, pexpect.TIMEOUT])
                if index == 0:
                    do_something()
                elif index == 1:
                    do_something_else()
                elif index == 2:
                    do_some_other_thing()
                elif index == 3:
                    do_something_completely_different()

        instead of code like this::

                try:
                    index = p.expect (['good', 'bad'])
                    if index == 0:
                        do_something()
                    elif index == 1:
                        do_something_else()
                except EOF:
                    do_some_other_thing()
                except TIMEOUT:
                    do_something_completely_different()

        These two forms are equivalent. It all depends on what you want. You
        can also just expect the EOF if you are waiting for all output of a
        child to finish. For example::

                p = pexpect.spawn('/bin/ls')
                p.expect (pexpect.EOF)
                print p.before

        If you are trying to optimize for speed then see expect_list().
        """

        compiled_pattern_list = self.compile_pattern_list(pattern)
        return self.expect_list(compiled_pattern_list, timeout, searchwindowsize)

    def expect_list(self, pattern_list, timeout = -1, searchwindowsize = -1):

        """This takes a list of compiled regular expressions and returns the
        index into the pattern_list that matched the child output. The list may
        also contain EOF or TIMEOUT (which are not compiled regular
        expressions). This method is similar to the expect() method except that
        expect_list() does not recompile the pattern list on every call. This
        may help if you are trying to optimize for speed, otherwise just use
        the expect() method.  This is called by expect(). If timeout==-1 then
        the self.timeout value is used. If searchwindowsize==-1 then the
        self.searchwindowsize value is used. """

        return self.expect_loop(searcher_re(pattern_list), timeout, searchwindowsize)

    def expect_exact(self, pattern_list, timeout = -1, searchwindowsize = -1):

        """This is similar to expect(), but uses plain string matching instead
        of compiled regular expressions in 'pattern_list'. The 'pattern_list'
        may be a string; a list or other sequence of strings; or TIMEOUT and
        EOF.

        This call might be faster than expect() for two reasons: string
        searching is faster than RE matching and it is possible to limit the
        search to just the end of the input buffer.

        This method is also useful when you don't want to have to worry about
        escaping regular expression characters that you want to match."""

        if type(pattern_list) in types.StringTypes or pattern_list in (TIMEOUT, EOF):
            pattern_list = [pattern_list]
        return self.expect_loop(searcher_string(pattern_list), timeout, searchwindowsize)

    def expect_loop(self, searcher, timeout = -1, searchwindowsize = -1):

        """This is the common loop used inside expect. The 'searcher' should be
        an instance of searcher_re or searcher_string, which describes how and what
        to search for in the input.

        See expect() for other arguments, return value and exceptions. """

        self.searcher = searcher

        if timeout == -1:
            timeout = self.timeout
        if timeout is not None:
            end_time = time.time() + timeout 
        if searchwindowsize == -1:
            searchwindowsize = self.searchwindowsize

        try:
            incoming = self.buffer
            freshlen = len(incoming)
            while True: # Keep reading until exception or return.
                index = searcher.search(incoming, freshlen, searchwindowsize)
                if index >= 0:
                    self.buffer = incoming[searcher.end : ]
                    self.before = incoming[ : searcher.start]
                    self.after = incoming[searcher.start : searcher.end]
                    self.match = searcher.match
                    self.match_index = index
                    return self.match_index
                # No match at this point
                if timeout < 0 and timeout is not None:
                    raise TIMEOUT ('Timeout exceeded in expect_any().')
                # Still have time left, so read more data
                c = self.read_nonblocking (self.maxread, timeout)
                freshlen = len(c)
                time.sleep (0.0001)
                incoming = incoming + c
                if timeout is not None:
                    timeout = end_time - time.time()
        except EOF, e:
            self.buffer = ''
            self.before = incoming
            self.after = EOF
            index = searcher.eof_index
            if index >= 0:
                self.match = EOF
                self.match_index = index
                return self.match_index
            else:
                self.match = None
                self.match_index = None
                raise EOF (str(e) + '\n' + str(self))
        except TIMEOUT, e:
            self.buffer = incoming
            self.before = incoming
            self.after = TIMEOUT
            index = searcher.timeout_index
            if index >= 0:
                self.match = TIMEOUT
                self.match_index = index
                return self.match_index
            else:
                self.match = None
                self.match_index = None
                raise TIMEOUT (str(e) + '\n' + str(self))
        except:
            self.before = incoming
            self.after = None
            self.match = None
            self.match_index = None
            raise

    def getwinsize(self):

        """This returns the terminal window size of the child tty. The return
        value is a tuple of (rows, cols). """

        TIOCGWINSZ = getattr(termios, 'TIOCGWINSZ', 1074295912L)
        s = struct.pack('HHHH', 0, 0, 0, 0)
        x = fcntl.ioctl(self.fileno(), TIOCGWINSZ, s)
        return struct.unpack('HHHH', x)[0:2]

    def setwinsize(self, r, c):

        """This sets the terminal window size of the child tty. This will cause
        a SIGWINCH signal to be sent to the child. This does not change the
        physical window size. It changes the size reported to TTY-aware
        applications like vi or curses -- applications that respond to the
        SIGWINCH signal. """

        # Check for buggy platforms. Some Python versions on some platforms
        # (notably OSF1 Alpha and RedHat 7.1) truncate the value for
        # termios.TIOCSWINSZ. It is not clear why this happens.
        # These platforms don't seem to handle the signed int very well;
        # yet other platforms like OpenBSD have a large negative value for
        # TIOCSWINSZ and they don't have a truncate problem.
        # Newer versions of Linux have totally different values for TIOCSWINSZ.
        # Note that this fix is a hack.
        TIOCSWINSZ = getattr(termios, 'TIOCSWINSZ', -2146929561)
        if TIOCSWINSZ == 2148037735L: # L is not required in Python >= 2.2.
            TIOCSWINSZ = -2146929561 # Same bits, but with sign.
        # Note, assume ws_xpixel and ws_ypixel are zero.
        s = struct.pack('HHHH', r, c, 0, 0)
        fcntl.ioctl(self.fileno(), TIOCSWINSZ, s)

    def interact(self, escape_character = chr(29), input_filter = None, output_filter = None):

        """This gives control of the child process to the interactive user (the
        human at the keyboard). Keystrokes are sent to the child process, and
        the stdout and stderr output of the child process is printed. This
        simply echos the child stdout and child stderr to the real stdout and
        it echos the real stdin to the child stdin. When the user types the
        escape_character this method will stop. The default for
        escape_character is ^]. This should not be confused with ASCII 27 --
        the ESC character. ASCII 29 was chosen for historical merit because
        this is the character used by 'telnet' as the escape character. The
        escape_character will not be sent to the child process.

        You may pass in optional input and output filter functions. These
        functions should take a string and return a string. The output_filter
        will be passed all the output from the child process. The input_filter
        will be passed all the keyboard input from the user. The input_filter
        is run BEFORE the check for the escape_character.

        Note that if you change the window size of the parent the SIGWINCH
        signal will not be passed through to the child. If you want the child
        window size to change when the parent's window size changes then do
        something like the following example::

            import pexpect, struct, fcntl, termios, signal, sys
            def sigwinch_passthrough (sig, data):
                s = struct.pack("HHHH", 0, 0, 0, 0)
                a = struct.unpack('hhhh', fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ , s))
                global p
                p.setwinsize(a[0],a[1])
            p = pexpect.spawn('/bin/bash') # Note this is global and used in sigwinch_passthrough.
            signal.signal(signal.SIGWINCH, sigwinch_passthrough)
            p.interact()
        """

        # Flush the buffer.
        self.stdout.write (self.buffer)
        self.stdout.flush()
        self.buffer = ''
        mode = tty.tcgetattr(self.STDIN_FILENO)
        tty.setraw(self.STDIN_FILENO)
        try:
            self.__interact_copy(escape_character, input_filter, output_filter)
        finally:
            tty.tcsetattr(self.STDIN_FILENO, tty.TCSAFLUSH, mode)

    def __interact_writen(self, fd, data):

        """This is used by the interact() method.
        """

        while data != '' and self.isalive():
            n = os.write(fd, data)
            data = data[n:]

    def __interact_read(self, fd):

        """This is used by the interact() method.
        """

        return os.read(fd, 1000)

    def __interact_copy(self, escape_character = None, input_filter = None, output_filter = None):

        """This is used by the interact() method.
        """

        while self.isalive():
            r,w,e = self.__select([self.child_fd, self.STDIN_FILENO], [], [])
            if self.child_fd in r:
                data = self.__interact_read(self.child_fd)
                if output_filter: data = output_filter(data)
                if self.logfile is not None:
                    self.logfile.write (data)
                    self.logfile.flush()
                os.write(self.STDOUT_FILENO, data)
            if self.STDIN_FILENO in r:
                data = self.__interact_read(self.STDIN_FILENO)
                if input_filter: data = input_filter(data)
                i = data.rfind(escape_character)
                if i != -1:
                    data = data[:i]
                    self.__interact_writen(self.child_fd, data)
                    break
                self.__interact_writen(self.child_fd, data)

    def __select (self, iwtd, owtd, ewtd, timeout=None):

        """This is a wrapper around select.select() that ignores signals. If
        select.select raises a select.error exception and errno is an EINTR
        error then it is ignored. Mainly this is used to ignore sigwinch
        (terminal resize). """

        # if select() is interrupted by a signal (errno==EINTR) then
        # we loop back and enter the select() again.
        if timeout is not None:
            end_time = time.time() + timeout
        while True:
            try:
                return select.select (iwtd, owtd, ewtd, timeout)
            except select.error, e:
                if e[0] == errno.EINTR:
                    # if we loop back we have to subtract the amount of time we already waited.
                    if timeout is not None:
                        timeout = end_time - time.time()
                        if timeout < 0:
                            return ([],[],[])
                else: # something else caused the select.error, so this really is an exception
                    raise

##############################################################################
# The following methods are no longer supported or allowed.

    def setmaxread (self, maxread):

        """This method is no longer supported or allowed. I don't like getters
        and setters without a good reason. """

        raise ExceptionPexpect ('This method is no longer supported or allowed. Just assign a value to the maxread member variable.')

    def setlog (self, fileobject):

        """This method is no longer supported or allowed.
        """

        raise ExceptionPexpect ('This method is no longer supported or allowed. Just assign a value to the logfile member variable.')

##############################################################################
# End of spawn class
##############################################################################

class searcher_string (object):

    """This is a plain string search helper for the spawn.expect_any() method.

    Attributes:

        eof_index     - index of EOF, or -1
        timeout_index - index of TIMEOUT, or -1

    After a successful match by the search() method the following attributes
    are available:

        start - index into the buffer, first byte of match
        end   - index into the buffer, first byte after match
        match - the matching string itself
    """

    def __init__(self, strings):

        """This creates an instance of searcher_string. This argument 'strings'
        may be a list; a sequence of strings; or the EOF or TIMEOUT types. """

        self.eof_index = -1
        self.timeout_index = -1
        self._strings = []
        for n, s in zip(range(len(strings)), strings):
            if s is EOF:
                self.eof_index = n
                continue
            if s is TIMEOUT:
                self.timeout_index = n
                continue
            self._strings.append((n, s))

    def __str__(self):

        """This returns a human-readable string that represents the state of
        the object."""

        ss =  [ (ns[0],'    %d: "%s"' % ns) for ns in self._strings ]
        ss.append((-1,'searcher_string:'))
        if self.eof_index >= 0:
            ss.append ((self.eof_index,'    %d: EOF' % self.eof_index))
        if self.timeout_index >= 0:
            ss.append ((self.timeout_index,'    %d: TIMEOUT' % self.timeout_index))
        ss.sort()
        ss = zip(*ss)[1]
        return '\n'.join(ss)

    def search(self, buffer, freshlen, searchwindowsize=None):

        """This searches 'buffer' for the first occurence of one of the search
        strings.  'freshlen' must indicate the number of bytes at the end of
        'buffer' which have not been searched before. It helps to avoid
        searching the same, possibly big, buffer over and over again.

        See class spawn for the 'searchwindowsize' argument.

        If there is a match this returns the index of that string, and sets
        'start', 'end' and 'match'. Otherwise, this returns -1. """

        absurd_match = len(buffer)
        first_match = absurd_match

        # 'freshlen' helps a lot here. Further optimizations could
        # possibly include:
        #
        # using something like the Boyer-Moore Fast String Searching
        # Algorithm; pre-compiling the search through a list of
        # strings into something that can scan the input once to
        # search for all N strings; realize that if we search for
        # ['bar', 'baz'] and the input is '...foo' we need not bother
        # rescanning until we've read three more bytes.
        #
        # Sadly, I don't know enough about this interesting topic. /grahn
        
        for index, s in self._strings:
            if searchwindowsize is None:
                # the match, if any, can only be in the fresh data,
                # or at the very end of the old data
                offset = -(freshlen+len(s))
            else:
                # better obey searchwindowsize
                offset = -searchwindowsize
            n = buffer.find(s, offset)
            if n >= 0 and n < first_match:
                first_match = n
                best_index, best_match = index, s
        if first_match == absurd_match:
            return -1
        self.match = best_match
        self.start = first_match
        self.end = self.start + len(self.match)
        return best_index

class searcher_re (object):

    """This is regular expression string search helper for the
    spawn.expect_any() method.

    Attributes:

        eof_index     - index of EOF, or -1
        timeout_index - index of TIMEOUT, or -1

    After a successful match by the search() method the following attributes
    are available:

        start - index into the buffer, first byte of match
        end   - index into the buffer, first byte after match
        match - the re.match object returned by a succesful re.search

    """

    def __init__(self, patterns):

        """This creates an instance that searches for 'patterns' Where
        'patterns' may be a list or other sequence of compiled regular
        expressions, or the EOF or TIMEOUT types."""

        self.eof_index = -1
        self.timeout_index = -1
        self._searches = []
        for n, s in zip(range(len(patterns)), patterns):
            if s is EOF:
                self.eof_index = n
                continue
            if s is TIMEOUT:
                self.timeout_index = n
                continue
            self._searches.append((n, s))

    def __str__(self):

        """This returns a human-readable string that represents the state of
        the object."""

        ss =  [ (n,'    %d: re.compile("%s")' % (n,str(s.pattern))) for n,s in self._searches]
        ss.append((-1,'searcher_re:'))
        if self.eof_index >= 0:
            ss.append ((self.eof_index,'    %d: EOF' % self.eof_index))
        if self.timeout_index >= 0:
            ss.append ((self.timeout_index,'    %d: TIMEOUT' % self.timeout_index))
        ss.sort()
        ss = zip(*ss)[1]
        return '\n'.join(ss)

    def search(self, buffer, freshlen, searchwindowsize=None):

        """This searches 'buffer' for the first occurence of one of the regular
        expressions. 'freshlen' must indicate the number of bytes at the end of
        'buffer' which have not been searched before.

        See class spawn for the 'searchwindowsize' argument.
        
        If there is a match this returns the index of that string, and sets
        'start', 'end' and 'match'. Otherwise, returns -1."""

        absurd_match = len(buffer)
        first_match = absurd_match
        # 'freshlen' doesn't help here -- we cannot predict the
        # length of a match, and the re module provides no help.
        if searchwindowsize is None:
            searchstart = 0
        else:
            searchstart = max(0, len(buffer)-searchwindowsize)
        for index, s in self._searches:
            match = s.search(buffer, searchstart)
            if match is None:
                continue
            n = match.start()
            if n < first_match:
                first_match = n
                the_match = match
                best_index = index
        if first_match == absurd_match:
            return -1
        self.start = first_match
        self.match = the_match
        self.end = self.match.end()
        return best_index

def which (filename):

    """This takes a given filename; tries to find it in the environment path;
    then checks if it is executable. This returns the full path to the filename
    if found and executable. Otherwise this returns None."""

    # Special case where filename already contains a path.
    if os.path.dirname(filename) != '':
        if os.access (filename, os.X_OK):
            return filename

    if not os.environ.has_key('PATH') or os.environ['PATH'] == '':
        p = os.defpath
    else:
        p = os.environ['PATH']

    # Oddly enough this was the one line that made Pexpect
    # incompatible with Python 1.5.2.
    #pathlist = p.split (os.pathsep)
    pathlist = string.split (p, os.pathsep)

    for path in pathlist:
        f = os.path.join(path, filename)
        if os.access(f, os.X_OK):
            return f
    return None

def split_command_line(command_line):

    """This splits a command line into a list of arguments. It splits arguments
    on spaces, but handles embedded quotes, doublequotes, and escaped
    characters. It's impossible to do this with a regular expression, so I
    wrote a little state machine to parse the command line. """

    arg_list = []
    arg = ''

    # Constants to name the states we can be in.
    state_basic = 0
    state_esc = 1
    state_singlequote = 2
    state_doublequote = 3
    state_whitespace = 4 # The state of consuming whitespace between commands.
    state = state_basic

    for c in command_line:
        if state == state_basic or state == state_whitespace:
            if c == '\\': # Escape the next character
                state = state_esc
            elif c == r"'": # Handle single quote
                state = state_singlequote
            elif c == r'"': # Handle double quote
                state = state_doublequote
            elif c.isspace():
                # Add arg to arg_list if we aren't in the middle of whitespace.
                if state == state_whitespace:
                    None # Do nothing.
                else:
                    arg_list.append(arg)
                    arg = ''
                    state = state_whitespace
            else:
                arg = arg + c
                state = state_basic
        elif state == state_esc:
            arg = arg + c
            state = state_basic
        elif state == state_singlequote:
            if c == r"'":
                state = state_basic
            else:
                arg = arg + c
        elif state == state_doublequote:
            if c == r'"':
                state = state_basic
            else:
                arg = arg + c

    if arg != '':
        arg_list.append(arg)
    return arg_list

# vi:ts=4:sw=4:expandtab:ft=python:

########NEW FILE########
__FILENAME__ = client
'''
Main Buildozer client
=====================

'''

import sys
from buildozer import Buildozer, BuildozerCommandException, BuildozerException


def main():
    try:
        Buildozer().run_command(sys.argv[1:])
    except BuildozerCommandException:
        # don't show the exception in the command line. The log already show
        # the command failed.
        pass
    except BuildozerException as error:
        Buildozer().error('%s' % error)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = remote
'''
Buildozer remote
================

.. warning::

    This is an experimental tool and not widely used. It might not fit for you.

Pack and send the source code to a remote SSH server, bundle buildozer with it,
and start the build on the remote.
You need paramiko to make it work.
'''

__all__ = ["BuildozerRemote"]

import socket
import sys
from buildozer import (
    Buildozer, BuildozerCommandException, BuildozerException, __version__)
from sys import stdout, stdin, exit
from select import select
from os.path import join, expanduser, realpath, exists, splitext
from os import makedirs, walk, getcwd
try:
    from configparser import SafeConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser
try:
    import termios
    import tty
    has_termios = True
except ImportError:
    has_termios = False
try:
    import paramiko
except ImportError:
    print('Paramiko missing: pip install paramiko')


class BuildozerRemote(Buildozer):
    def run_command(self, args):
        while args:
            if not args[0].startswith('-'):
                break
            arg = args.pop(0)

            if arg in ('-v', '--verbose'):
                self.log_level = 2

            elif arg in ('-p', '--profile'):
                self.config_profile = args.pop(0)

            elif arg in ('-h', '--help'):
                self.usage()
                exit(0)

            elif arg == '--version':
                print('Buildozer (remote) {0}'.format(__version__))
                exit(0)

        self._merge_config_profile()

        if len(args) < 2:
            self.usage()
            return

        remote_name = args[0]
        remote_section = 'remote:{}'.format(remote_name)
        if not self.config.has_section(remote_section):
            self.error('Unknown remote "{}", must be configured first.'.format(
                remote_name))
            return

        self.remote_host = remote_host = self.config.get(
                remote_section, 'host', '')
        self.remote_port = self.config.get(
                remote_section, 'port', '22')
        self.remote_user = remote_user = self.config.get(
                remote_section, 'user', '')
        self.remote_build_dir = remote_build_dir = self.config.get(
                remote_section, 'build_directory', '')
        self.remote_identity = self.config.get(
                remote_section, 'identity', '')
        if not remote_host:
            self.error('Missing "host = " for {}'.format(remote_section))
            return
        if not remote_user:
            self.error('Missing "user = " for {}'.format(remote_section))
            return
        if not remote_build_dir:
            self.error('Missing "build_directory = " for {}'.format(remote_section))
            return

        # fake the target
        self.targetname = 'remote'
        self.check_build_layout()

        # prepare our source code
        self.info('Prepare source code to sync')
        self._copy_application_sources()
        self._ssh_connect()
        try:
            self._ensure_buildozer()
            self._sync_application_sources()
            self._do_remote_commands(args[1:])
            self._ssh_sync(getcwd(), mode='get')
        finally:
            self._ssh_close()

    def _ssh_connect(self):
        self.info('Connecting to {}'.format(self.remote_host))
        self._ssh_client = client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.load_system_host_keys()
        kwargs = {}
        if self.remote_identity:
            kwargs['key_filename'] = expanduser(self.remote_identity)
        client.connect(self.remote_host, username=self.remote_user,
                port=int(self.remote_port), **kwargs)
        self._sftp_client = client.open_sftp()

    def _ssh_close(self):
        self.debug('Closing remote connection')
        self._sftp_client.close()
        self._ssh_client.close()

    def _ensure_buildozer(self):
        s = self._sftp_client
        root_dir = s.normalize('.')
        self.remote_build_dir = join(root_dir, self.remote_build_dir,
                self.package_full_name)
        self.debug('Remote build directory: {}'.format(self.remote_build_dir))
        self._ssh_mkdir(self.remote_build_dir)
        self._ssh_sync(__path__[0])

    def _sync_application_sources(self):
        self.info('Synchronize application sources')
        self._ssh_sync(self.app_dir)

        # create custom buildozer.spec
        self.info('Create custom buildozer.spec')
        config = SafeConfigParser()
        config.read('buildozer.spec')
        config.set('app', 'source.dir', 'app')

        fn = join(self.remote_build_dir, 'buildozer.spec')
        fd = self._sftp_client.open(fn, 'wb')
        config.write(fd)
        fd.close()

    def _do_remote_commands(self, args):
        self.info('Execute remote buildozer')
        cmd = (
            'source ~/.profile;'
            'cd {0};'
            'env PYTHONPATH={0}:$PYTHONPATH '
            'python -c "import buildozer, sys;'
            'buildozer.Buildozer().run_command(sys.argv[1:])" {1} {2} 2>&1').format(
            self.remote_build_dir,
            '--verbose' if self.log_level == 2 else '',
            ' '.join(args),
            )
        self._ssh_command(cmd)

    def _ssh_mkdir(self, *args):
        directory = join(*args)
        self.debug('Create remote directory {}'.format(directory))
        try:
            self._sftp_client.mkdir(directory)
        except IOError:
            # already created?
            try:
                self._sftp_client.stat(directory)
            except IOError:
                self.error('Unable to create remote directory {}'.format(directory))
                raise

    def _ssh_sync(self, directory, mode='put'):
        self.debug('Syncing {} directory'.format(directory))
        directory = realpath(directory)
        base_strip = directory.rfind('/')
        if mode == 'get':
            local_dir = join(directory,'bin')
            remote_dir = join(self.remote_build_dir, 'bin')
            if not exists(local_dir):
                makedirs(local_dir)
            for _file in self._sftp_client.listdir(path=remote_dir):
                self._sftp_client.get(join(remote_dir, _file),
                                      join(local_dir, _file))
            return
        for root, dirs, files in walk(directory):
            self._ssh_mkdir(self.remote_build_dir, root[base_strip + 1:])
            for fn in files:
                if splitext(fn)[1] in ('.pyo', '.pyc', '.swp'):
                    continue
                local_file = join(root, fn)
                remote_file = join(self.remote_build_dir, root[base_strip + 1:], fn)
                self.debug('Sync {} -> {}'.format(local_file, remote_file))
                self._sftp_client.put(local_file, remote_file)

    def _ssh_command(self, command):
        self.debug('Execute remote command {}'.format(command))
        #shell = self._ssh_client.invoke_shell()
        #shell.sendall(command)
        #shell.sendall('\nexit\n')
        transport = self._ssh_client.get_transport()
        channel = transport.open_session()
        try:
            channel.exec_command(command)
            self._interactive_shell(channel)
        finally:
            channel.close()

    def _interactive_shell(self, chan):
        if has_termios:
            self._posix_shell(chan)
        else:
            self._windows_shell(chan)

    def _posix_shell(self, chan):
        oldtty = termios.tcgetattr(stdin)
        try:
            #tty.setraw(stdin.fileno())
            #tty.setcbreak(stdin.fileno())
            chan.settimeout(0.0)

            while True:
                r, w, e = select([chan, stdin], [], [])
                if chan in r:
                    try:
                        x = chan.recv(128)
                        if len(x) == 0:
                            print('\r\n*** EOF\r\n',)
                            break
                        stdout.write(x)
                        stdout.flush()
                        #print len(x), repr(x)
                    except socket.timeout:
                        pass
                if stdin in r:
                    x = stdin.read(1)
                    if len(x) == 0:
                        break
                    chan.sendall(x)
        finally:
            termios.tcsetattr(stdin, termios.TCSADRAIN, oldtty)

    # thanks to Mike Looijmans for this code
    def _windows_shell(self,chan):
        import threading

        stdout.write("Line-buffered terminal emulation. Press F6 or ^Z to send EOF.\r\n\r\n")

        def writeall(sock):
            while True:
                data = sock.recv(256)
                if not data:
                    stdout.write('\r\n*** EOF ***\r\n\r\n')
                    stdout.flush()
                    break
                stdout.write(data)
                stdout.flush()

        writer = threading.Thread(target=writeall, args=(chan,))
        writer.start()

        try:
            while True:
                d = stdin.read(1)
                if not d:
                    break
                chan.send(d)
        except EOFError:
            # user hit ^Z or F6
            pass

def main():
    try:
        BuildozerRemote().run_command(sys.argv[1:])
    except BuildozerCommandException:
        pass
    except BuildozerException as error:
        Buildozer().error('%s' % error)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = sitecustomize
from os.path import join, dirname
import sys
sys.path.append(join(dirname(__file__), '_applibs'))

########NEW FILE########
__FILENAME__ = target
from sys import exit

def no_config(f):
    f.__no_config = True
    return f

class Target(object):

    def __init__(self, buildozer):
        super(Target, self).__init__()
        self.buildozer = buildozer
        self.build_mode = 'debug'
        self.platform_update = False

    def check_requirements(self):
        pass

    def check_configuration_tokens(self, errors=None):
        if errors:
            self.buildozer.info('Check target configuration tokens')
            self.buildozer.error(
                '{0} error(s) found in the buildozer.spec'.format(
                len(errors)))
            for error in errors:
                print(error)
            exit(1)

    def compile_platform(self):
        pass

    def install_platform(self):
        pass

    def get_custom_commands(self):
        result = []
        for x in dir(self):
            if not x.startswith('cmd_'):
                continue
            if x[4:] in self.buildozer.standard_cmds:
                continue
            result.append((x[4:], getattr(self, x).__doc__))
        return result

    def get_available_packages(self):
        return ['kivy']

    def run_commands(self, args):
        if not args:
            self.buildozer.error('Missing target command')
            self.buildozer.usage()
            exit(1)

        result = []
        last_command = []
        for arg in args:
            if not arg.startswith('--'):
                if last_command:
                    result.append(last_command)
                    last_command = []
                last_command.append(arg)
            else:
                if not last_command:
                    self.buildozer.error('Argument passed without a command')
                    self.buildozer.usage()
                    exit(1)
                last_command.append(arg)
        if last_command:
            result.append(last_command)

        config_check = False

        for item in result:
            command, args = item[0], item[1:]
            if not hasattr(self, 'cmd_{0}'.format(command)):
                self.buildozer.error('Unknown command {0}'.format(command))
                exit(1)

            func = getattr(self, 'cmd_{0}'.format(command))

            need_config_check = not hasattr(func, '__no_config')
            if need_config_check and not config_check:
                config_check = True
                self.check_configuration_tokens()

            func(args)

    def cmd_clean(self, *args):
        self.buildozer.clean_platform()

    def cmd_update(self, *args):
        self.platform_update = True
        self.buildozer.prepare_for_build()

    def cmd_debug(self, *args):
        self.buildozer.prepare_for_build()
        self.build_mode = 'debug'
        self.buildozer.build()

    def cmd_release(self, *args):
        self.buildozer.prepare_for_build()
        self.build_mode = 'release'
        self.buildozer.build()

    def cmd_deploy(self, *args):
        self.buildozer.prepare_for_build()

    def cmd_run(self, *args):
        self.buildozer.prepare_for_build()

    def cmd_serve(self, *args):
        self.buildozer.cmd_serve()


########NEW FILE########
__FILENAME__ = android
'''
Android target, based on python-for-android project
'''
#
# Android target
# Thanks for Renpy (again) for its install_sdk.py and plat.py in the PGS4A
# project!
#

import sys
if sys.platform == 'win32':
    raise NotImplementedError('Windows platform not yet working for Android')

ANDROID_API = '14'
ANDROID_MINAPI = '8'
ANDROID_SDK_VERSION = '21'
ANDROID_NDK_VERSION = '9c'
APACHE_ANT_VERSION = '1.8.4'

import traceback
import os
import io
from pipes import quote
from sys import platform, executable
from buildozer import BuildozerException
from buildozer.target import Target
from os import environ
from os.path import exists, join, realpath, expanduser, basename, relpath
from shutil import copyfile
from glob import glob



class TargetAndroid(Target):

    @property
    def android_sdk_version(self):
        return self.buildozer.config.getdefault(
                'app', 'android.sdk', ANDROID_SDK_VERSION)

    @property
    def android_ndk_version(self):
        return self.buildozer.config.getdefault(
                'app', 'android.ndk', ANDROID_NDK_VERSION)

    @property
    def android_api(self):
        return self.buildozer.config.getdefault(
                'app', 'android.api', ANDROID_API)

    @property
    def android_minapi(self):
        return self.buildozer.config.getdefault(
                'app', 'android.minapi', ANDROID_MINAPI)

    @property
    def android_sdk_dir(self):
        directory = expanduser(self.buildozer.config.getdefault(
            'app', 'android.sdk_path', ''))
        if directory:
            return realpath(directory)
        version = self.buildozer.config.getdefault(
                'app', 'android.sdk', self.android_sdk_version)
        return join(self.buildozer.global_platform_dir,
                'android-sdk-{0}'.format(version))

    @property
    def android_ndk_dir(self):
        directory = expanduser(self.buildozer.config.getdefault(
            'app', 'android.ndk_path', ''))
        if directory:
            return realpath(directory)
        version = self.buildozer.config.getdefault(
                'app', 'android.ndk', self.android_ndk_version)
        return join(self.buildozer.global_platform_dir,
                'android-ndk-r{0}'.format(version))

    @property
    def apache_ant_dir(self):
        directory = expanduser(self.buildozer.config.getdefault(
            'app', 'android.ant_path', ''))
        if directory:
            return realpath(directory)
        version = self.buildozer.config.getdefault(
                'app', 'android.ant', APACHE_ANT_VERSION)
        return join(self.buildozer.global_platform_dir,
                'apache-ant-{0}'.format(version))

    def check_requirements(self):
        if platform in ('win32', 'cygwin'):
            try:
                self._set_win32_java_home()
            except:
                traceback.print_exc()
            self.android_cmd = join(self.android_sdk_dir, 'tools', 'android.bat')
            self.adb_cmd = join(self.android_sdk_dir, 'platform-tools', 'adb.exe')
            self.javac_cmd = self._locate_java('javac.exe')
            self.keytool_cmd = self._locate_java('keytool.exe')
        elif platform in ('darwin', ):
            self.android_cmd = join(self.android_sdk_dir, 'tools', 'android')
            self.adb_cmd = join(self.android_sdk_dir, 'platform-tools', 'adb')
            self.javac_cmd = self._locate_java('javac')
            self.keytool_cmd = self._locate_java('keytool')
        else:
            self.android_cmd = join(self.android_sdk_dir, 'tools', 'android')
            self.adb_cmd = join(self.android_sdk_dir, 'platform-tools', 'adb')
            self.javac_cmd = self._locate_java('javac')
            self.keytool_cmd = self._locate_java('keytool')

        # Check for C header <zlib.h>.
        _, _, returncode_dpkg = self.buildozer.cmd(
                'dpkg --version', break_on_error= False)
        is_debian_like = (returncode_dpkg == 0)
        if is_debian_like:
            if not self.buildozer.file_exists('/usr/include/zlib.h'):
                message = 'zlib headers must be installed, run: sudo apt-get install zlib1g-dev'
                raise BuildozerException(message)

        # Need to add internally installed ant to path for external tools
        # like adb to use
        path = [join(self.apache_ant_dir, 'bin')]
        if 'PATH' in self.buildozer.environ:
            path.append(self.buildozer.environ['PATH'])
        else:
            path.append(os.environ['PATH'])
        self.buildozer.environ['PATH'] = ':'.join(path)
        checkbin = self.buildozer.checkbin
        checkbin('Git (git)', 'git')
        checkbin('Cython (cython)', 'cython')
        checkbin('Java compiler (javac)', self.javac_cmd)
        checkbin('Java keytool (keytool)', self.keytool_cmd)

    def check_configuration_tokens(self):
        errors = []

        # check the permission
        available_permissions = self._get_available_permissions()
        if available_permissions:
            permissions = self.buildozer.config.getlist(
                'app', 'android.permissions', [])
            for permission in permissions:
                # no check on full named permission
                # like com.google.android.providers.gsf.permission.READ_GSERVICES
                if '.' in permission:
                    continue
                permission = permission.upper()
                if permission not in available_permissions:
                    errors.append(
                        '[app] "android.permission" contain an unknown'
                        ' permission {0}'.format(permission))

        super(TargetAndroid, self).check_configuration_tokens(errors)

    def _get_available_permissions(self):
        key = 'android:available_permissions'
        key_sdk = 'android:available_permissions_sdk'

        refresh_permissions = False
        sdk = self.buildozer.state.get(key_sdk, None)
        if not sdk or sdk != self.android_sdk_version:
            refresh_permissions = True
        if key not in self.buildozer.state:
            refresh_permissions = True
        if not refresh_permissions:
            return self.buildozer.state[key]

        try:
            self.buildozer.debug('Read available permissions from api-versions.xml')
            import xml.etree.ElementTree as ET
            fn = join(self.android_sdk_dir, 'platform-tools',
                    'api', 'api-versions.xml')
            with io.open(fn, encoding='utf-8') as fd:
                doc = ET.fromstring(fd.read())
            fields = doc.findall('.//class[@name="android/Manifest$permission"]/field[@name]')
            available_permissions = [x.attrib['name'] for x in fields]

            self.buildozer.state[key] = available_permissions
            self.buildozer.state[key_sdk] = self.android_sdk_version
            return available_permissions
        except:
            return None

    def _set_win32_java_home(self):
        if 'JAVA_HOME' in self.buildozer.environ:
            return
        import _winreg
        with _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft\Java Development Kit") as jdk: #@UndefinedVariable
            current_version, _type = _winreg.QueryValueEx(jdk, "CurrentVersion") #@UndefinedVariable
            with _winreg.OpenKey(jdk, current_version) as cv: #@UndefinedVariable
                java_home, _type = _winreg.QueryValueEx(cv, "JavaHome") #@UndefinedVariable
            self.buildozer.environ['JAVA_HOME'] = java_home

    def _locate_java(self, s):
        '''If JAVA_HOME is in the environ, return $JAVA_HOME/bin/s. Otherwise,
        return s.
        '''
        if 'JAVA_HOME' in self.buildozer.environ:
            return join(self.buildozer.environ['JAVA_HOME'], 'bin', s)
        else:
            return s

    def _install_apache_ant(self):
        ant_dir = self.apache_ant_dir
        if self.buildozer.file_exists(ant_dir):
            self.buildozer.info('Apache ANT found at {0}'.format(ant_dir))
            return ant_dir

        self.buildozer.info('Android ANT is missing, downloading')
        archive = 'apache-ant-{0}-bin.tar.gz'.format(APACHE_ANT_VERSION)
        url = 'http://archive.apache.org/dist/ant/binaries/'
        self.buildozer.download(url, archive,
                cwd=self.buildozer.global_platform_dir)
        self.buildozer.file_extract(archive,
                cwd=self.buildozer.global_platform_dir)
        self.buildozer.info('Apache ANT installation done.')
        return ant_dir

    def _install_android_sdk(self):
        sdk_dir = self.android_sdk_dir
        if self.buildozer.file_exists(sdk_dir):
            self.buildozer.info('Android SDK found at {0}'.format(sdk_dir))
            return sdk_dir

        self.buildozer.info('Android SDK is missing, downloading')
        if platform in ('win32', 'cygwin'):
            archive = 'android-sdk_r{0}-windows.zip'
            unpacked = 'android-sdk-windows'
        elif platform in ('darwin', ):
            archive = 'android-sdk_r{0}-macosx.zip'
            unpacked = 'android-sdk-macosx'
        elif platform in ('linux2', 'linux3'):
            archive = 'android-sdk_r{0}-linux.tgz'
            unpacked = 'android-sdk-linux'
        else:
            raise SystemError('Unsupported platform: {0}'.format(platform))

        archive = archive.format(self.android_sdk_version)
        url = 'http://dl.google.com/android/'
        self.buildozer.download(url, archive,
                cwd=self.buildozer.global_platform_dir)

        self.buildozer.info('Unpacking Android SDK')
        self.buildozer.file_extract(archive,
                cwd=self.buildozer.global_platform_dir)
        self.buildozer.file_rename(unpacked, sdk_dir,
                cwd=self.buildozer.global_platform_dir)
        self.buildozer.info('Android SDK installation done.')
        return sdk_dir

    def _install_android_ndk(self):
        ndk_dir = self.android_ndk_dir
        if self.buildozer.file_exists(ndk_dir):
            self.buildozer.info('Android NDK found at {0}'.format(ndk_dir))
            return ndk_dir

        self.buildozer.info('Android NDK is missing, downloading')
        if platform in ('win32', 'cygwin'):
            # Checking of 32/64 bits at Windows from: http://stackoverflow.com/a/1405971/798575
            import struct
            archive = 'android-ndk-r{0}-windows-{1}.zip'
            is_64 = (8*struct.calcsize("P") == 64)
        elif platform in ('darwin', ):
            archive = 'android-ndk-r{0}-darwin-{1}.tar.bz2'
            is_64 = (os.uname()[4] == 'x86_64')
        elif platform.startswith('linux'):
            archive = 'android-ndk-r{0}-linux-{1}.tar.bz2'
            is_64 = (os.uname()[4] == 'x86_64')
        else:
            raise SystemError('Unsupported platform: {0}'.format(platform))

        architecture = 'x86_64' if is_64 else 'x86'
        unpacked = 'android-ndk-r{0}'
        archive = archive.format(self.android_ndk_version, architecture)
        unpacked = unpacked.format(self.android_ndk_version)
        url = 'http://dl.google.com/android/ndk/'
        self.buildozer.download(url, archive,
                cwd=self.buildozer.global_platform_dir)

        self.buildozer.info('Unpacking Android NDK')
        self.buildozer.file_extract(archive,
                cwd=self.buildozer.global_platform_dir)
        self.buildozer.file_rename(unpacked, ndk_dir,
                cwd=self.buildozer.global_platform_dir)
        self.buildozer.info('Android NDK installation done.')
        return ndk_dir

    def _android_list_sdk(self):
        available_packages = self.buildozer.cmd(
                '{} list sdk -u -e'.format(self.android_cmd),
                cwd=self.buildozer.global_platform_dir,
                get_stdout=True)[0]

        # get only the line like -> id: 5 or "build-tools-19.0.1"
        # and extract the name part.
        print(available_packages)
        return [x.split('"')[1] for x in
                available_packages.splitlines() if x.startswith('id: ')]

    def _android_update_sdk(self, packages):
        from buildozer.libs.pexpect import EOF
        child = self.buildozer.cmd_expect('{} update sdk -u -a -t {}'.format(
            self.android_cmd, packages,
            cwd=self.buildozer.global_platform_dir),
            timeout=None)
        while True:
            index = child.expect([EOF, '[y/n]: '])
            if index == 0:
                break
            child.sendline('y')

    def _install_android_packages(self):
        # 3 pass installation.
        need_refresh = False

        self.buildozer.cmd('chmod ug+x {}'.format(self.android_cmd))

        # 1. update the tool and platform-tools if needed
        packages = self._android_list_sdk()
        if 'tools' in packages or 'platform-tools' in packages:
            self._android_update_sdk('tools,platform-tools')
            need_refresh = True

        # 2. install the latest build tool
        if need_refresh:
            packages = self._android_list_sdk()
        build_tools = [x for x in packages if x.startswith('build-tools-')]
        if build_tools:
            build_tools.sort()
            self._android_update_sdk(build_tools[-1])
            need_refresh = True

        # 3. finally, install the android for the current api
        android_platform = join(self.android_sdk_dir, 'platforms',
                'android-{0}'.format(self.android_api))
        if not self.buildozer.file_exists(android_platform):
            if need_refresh:
                packages = self._android_list_sdk()
            android_package = 'android-{}'.format(self.android_api)
            if android_package in packages:
                self._android_update_sdk(android_package)

        self.buildozer.info('Android packages installation done.')

    def install_platform(self):
        cmd = self.buildozer.cmd
        self.pa_dir = pa_dir = join(self.buildozer.platform_dir, 'python-for-android')
        if not self.buildozer.file_exists(pa_dir):
            system_p4a_dir = self.buildozer.config.getdefault('app', 'android.p4a_dir')
            if system_p4a_dir:
                cmd('ln -sf {} ./python-for-android'.format(system_p4a_dir),
                    cwd = self.buildozer.platform_dir)
            else:
                cmd('git clone git://github.com/kivy/python-for-android',
                    cwd=self.buildozer.platform_dir)
        elif self.platform_update:
            cmd('git clean -dxf', cwd=pa_dir)
            cmd('git pull origin master', cwd=pa_dir)

        source = self.buildozer.config.getdefault('app', 'android.branch')
        if source:
            cmd('git checkout  %s' % (source),
                cwd=pa_dir)

        self._install_apache_ant()
        self._install_android_sdk()
        self._install_android_ndk()
        self._install_android_packages()

        # ultimate configuration check.
        # some of our configuration cannot be check without platform.
        self.check_configuration_tokens()

        self.buildozer.environ.update({
            'PACKAGES_PATH': self.buildozer.global_packages_dir,
            'ANDROIDSDK': self.android_sdk_dir,
            'ANDROIDNDK': self.android_ndk_dir,
            'ANDROIDAPI': self.android_api,
            'ANDROIDNDKVER': 'r{}'.format(self.android_ndk_version)})

    def get_available_packages(self):
        available_modules = self.buildozer.cmd(
                './distribute.sh -l', cwd=self.pa_dir, get_stdout=True)[0]
        if not available_modules.startswith('Available modules:'):
            self.buildozer.error('Python-for-android invalid output for -l')
        return available_modules[19:].splitlines()[0].split()

    def compile_platform(self):
        # for android, the compilation depends really on the app requirements.
        # compile the distribution only if the requirements changed.
        last_requirements = self.buildozer.state.get('android.requirements', '')
        app_requirements = self.buildozer.config.getlist('app',
                'requirements', '')

        # we need to extract the requirements that python-for-android knows
        # about
        available_modules = self.get_available_packages()
        onlyname = lambda x: x.split('==')[0]
        android_requirements = [x for x in app_requirements if onlyname(x) in
                            available_modules]

        need_compile = 0
        if last_requirements != android_requirements:
            need_compile = 1

        dist_name = self.buildozer.config.get('app', 'package.name')
        dist_dir = join(self.pa_dir, 'dist', dist_name)
        if not exists(dist_dir):
            need_compile = 1

        # whitelist p4a
        p4a_whitelist = self.buildozer.config.getlist('app', 'android.p4a_whitelist')
        if p4a_whitelist:
            with open(join(self.pa_dir, 'src', 'whitelist.txt'), 'w') as fd:
                for wl in p4a_whitelist:
                    fd.write(wl + '\n')

        if not need_compile:
            self.buildozer.info('Distribution already compiled, pass.')
            return

        modules_str = ' '.join(android_requirements)
        cmd = self.buildozer.cmd
        self.buildozer.debug('Clean and build python-for-android')
        self.buildozer.rmdir(dist_dir)  # Delete existing distribution to stop
                                        # p4a complaining
        cmd('./distribute.sh -m "{0}" -d "{1}"'.format(modules_str, dist_name),
            cwd=self.pa_dir)
        self.buildozer.debug('Remove temporary build files')
        self.buildozer.rmdir(join(self.pa_dir, 'build'))
        self.buildozer.rmdir(join(self.pa_dir, '.packages'))
        self.buildozer.rmdir(join(self.pa_dir, 'src', 'jni', 'obj', 'local'))
        self.buildozer.info('Distribution compiled.')

        # ensure we will not compile again
        self.buildozer.state['android.requirements'] = android_requirements
        self.buildozer.state.sync()

    def _get_package(self):
        config = self.buildozer.config
        package_domain = config.getdefault('app', 'package.domain', '')
        package = config.get('app', 'package.name')
        if package_domain:
            package = package_domain + '.' + package
        return package.lower()

    def build_package(self):
        dist_name = self.buildozer.config.get('app', 'package.name')
        dist_dir = join(self.pa_dir, 'dist', dist_name)
        config = self.buildozer.config
        package = self._get_package()
        version = self.buildozer.get_version()

        # add extra libs/armeabi files in dist/default/libs/armeabi
        # (same for armeabi-v7a, x86, mips)
        for config_key, lib_dir in (
            ('android.add_libs_armeabi', 'armeabi'),
            ('android.add_libs_armeabi_v7a', 'armeabi-v7a'),
            ('android.add_libs_x86', 'x86'),
            ('android.add_libs_mips', 'mips')):

            patterns = config.getlist('app', config_key, [])
            if not patterns:
                continue

            self.buildozer.debug('Search and copy libs for {}'.format(lib_dir))
            for fn in self.buildozer.file_matches(patterns):
                self.buildozer.file_copy(
                    join(self.buildozer.root_dir, fn),
                    join(dist_dir, 'libs', lib_dir, basename(fn)))

        # update the project.properties libraries references
        self._update_libraries_references(dist_dir)

        # add src files
        self._add_java_src(dist_dir)

        # build the app
        build_cmd = (
            '{python} build.py --name {name}'
            ' --version {version}'
            ' --package {package}'
            ' --{storage_type} {appdir}'
            ' --sdk {androidsdk}'
            ' --minsdk {androidminsdk}').format(
            python=executable,
            name=quote(config.get('app', 'title')),
            version=version,
            package=package,
            storage_type='private' if config.getbooldefault(
                'app', 'android.private_storage', True) else 'dir',
            appdir=self.buildozer.app_dir,
            androidminsdk=config.getdefault(
                'app', 'android.minsdk', self.android_minapi),
            androidsdk=config.getdefault(
                'app', 'android.sdk', self.android_api))

        # add permissions
        permissions = config.getlist('app',
                'android.permissions', [])
        for permission in permissions:
            # force the latest component to be uppercase
            permission = permission.split('.')
            permission[-1] = permission[-1].upper()
            permission = '.'.join(permission)
            build_cmd += ' --permission {}'.format(permission)

        # meta-data
        meta_datas = config.getlistvalues('app', 'android.meta_data', [])
        for meta in meta_datas:
            key, value = meta.split('=', 1)
            meta = '{}={}'.format(key.strip(), value.strip())
            build_cmd += ' --meta-data "{}"'.format(meta)

        # add extra Java jar files
        add_jars = config.getlist('app', 'android.add_jars', [])
        for pattern in add_jars:
            pattern = join(self.buildozer.root_dir, pattern)
            matches = glob(expanduser(pattern.strip()))
            if matches:
                for jar in matches:
                    build_cmd += ' --add-jar "{}"'.format(jar)
            else:
                raise SystemError(
                    'Failed to find jar file: {}'.format(pattern))

        # add presplash
        presplash = config.getdefault('app', 'presplash.filename', '')
        if presplash:
            build_cmd += ' --presplash {}'.format(join(self.buildozer.root_dir,
                presplash))

        # add icon
        icon = config.getdefault('app', 'icon.filename', '')
        if icon:
            build_cmd += ' --icon {}'.format(join(self.buildozer.root_dir, icon))

        # OUYA Console support
        ouya_category = config.getdefault('app', 'android.ouya.category', '').upper()
        if ouya_category:
            if ouya_category not in ('GAME', 'APP'):
                raise SystemError('Invalid android.ouya.category: "{}" must be one of GAME or APP'.format(ouya_category))
            # add icon
            build_cmd += ' --ouya-category {}'.format(ouya_category)
            ouya_icon = config.getdefault('app', 'android.ouya.icon.filename', '')
            build_cmd += ' --ouya-icon {}'.format(join(self.buildozer.root_dir, ouya_icon))

        # add orientation
        orientation = config.getdefault('app', 'orientation', 'landscape')
        if orientation == 'all':
            orientation = 'sensor'
        build_cmd += ' --orientation {}'.format(orientation)

        # fullscreen ?
        fullscreen = config.getbooldefault('app', 'fullscreen', True)
        if not fullscreen:
            build_cmd += ' --window'

        # wakelock ?
        wakelock = config.getbooldefault('app', 'android.wakelock', False)
        if wakelock:
            build_cmd += ' --wakelock'

        # intent filters
        intent_filters = config.getdefault('app',
            'android.manifest.intent_filters', '')
        if intent_filters:
            build_cmd += ' --intent-filters {}'.format(
                    join(self.buildozer.root_dir, intent_filters))

        # build only in debug right now.
        if self.build_mode == 'debug':
            build_cmd += ' debug'
            mode = 'debug'
        else:
            build_cmd += ' release'
            mode = 'release-unsigned'
        self.buildozer.cmd(build_cmd, cwd=dist_dir)

        # XXX found how the apk name is really built from the title
        bl = '\'" ,'
        apktitle = ''.join([x for x in config.get('app', 'title') if x not in
            bl])
        apk = '{title}-{version}-{mode}.apk'.format(
            title=apktitle, version=version, mode=mode)

        # copy to our place
        copyfile(join(dist_dir, 'bin', apk),
                join(self.buildozer.bin_dir, apk))

        self.buildozer.info('Android packaging done!')
        self.buildozer.info('APK {0} available in the bin directory'.format(apk))
        self.buildozer.state['android:latestapk'] = apk
        self.buildozer.state['android:latestmode'] = self.build_mode

    def _update_libraries_references(self, dist_dir):
        # ensure the project.properties exist
        project_fn = join(dist_dir, 'project.properties')

        if not self.buildozer.file_exists(project_fn):
            content = ['target=android-{}\n'.format(self.android_api)]
        else:
            with io.open(project_fn, encoding='utf-8') as fd:
                content = fd.readlines()

        # extract library reference
        references = []
        for line in content[:]:
            if not line.startswith('android.library.reference.'):
                continue
            content.remove(line)

        # convert our references to relative path
        app_references = self.buildozer.config.getlist(
                'app', 'android.library_references', [])
        source_dir = realpath(self.buildozer.config.getdefault('app', 'source.dir', '.'))
        for cref in app_references:
            # get the full path of the current reference
            ref = realpath(join(source_dir, cref))
            if not self.buildozer.file_exists(ref):
                self.buildozer.error('Invalid library reference (path not found): {}'.format(cref))
                exit(1)
            # get a relative path from the project file
            ref = relpath(ref, dist_dir)
            # ensure the reference exists
            references.append(ref)

        # recreate the project.properties
        with io.open(project_fn, 'w', encoding='utf-8') as fd:
            for line in content:
                fd.write(line.decode('utf-8'))
            for index, ref in enumerate(references):
                fd.write(u'android.library.reference.{}={}\n'.format(
                    index + 1, ref))

        self.buildozer.debug('project.properties updated')

    def _add_java_src(self, dist_dir):
        java_src = self.buildozer.config.getlist('app', 'android.add_src', [])
        src_dir = join(dist_dir, 'src')
        for pattern in java_src:
            for fn in glob(expanduser(pattern.strip())):
                last_component = basename(fn)
                self.buildozer.file_copytree(fn, join(src_dir, last_component))

    @property
    def serials(self):
        if hasattr(self, '_serials'):
            return self._serials
        serial = environ.get('ANDROID_SERIAL')
        if serial:
            return serial.split(',')
        l = self.buildozer.cmd('{} devices'.format(self.adb_cmd),
                get_stdout=True)[0].splitlines()
        serials = []
        for serial in l:
            if not serial:
                continue
            if serial.startswith('*') or serial.startswith('List '):
                continue
            serials.append(serial.split()[0])
        self._serials = serials
        return serials

    def cmd_deploy(self, *args):
        super(TargetAndroid, self).cmd_deploy(*args)
        state = self.buildozer.state
        if 'android:latestapk' not in state:
            self.buildozer.error(
                'No APK built yet. Run "debug" first.')

        if state.get('android:latestmode', '') != 'debug':
            self.buildozer.error(
                'Only debug APK are supported for deploy')

        # search the APK in the bin dir
        apk = state['android:latestapk']
        full_apk = join(self.buildozer.bin_dir, apk)
        if not self.buildozer.file_exists(full_apk):
            self.buildozer.error(
                'Unable to found the latest APK. Please run "debug" again.')

        # push on the device
        for serial in self.serials:
            self.buildozer.environ['ANDROID_SERIAL'] = serial
            self.buildozer.info('Deploy on {}'.format(serial))
            self.buildozer.cmd('{0} install -r {1}'.format(
                self.adb_cmd, full_apk), cwd=self.buildozer.global_platform_dir)
        self.buildozer.environ.pop('ANDROID_SERIAL', None)

        self.buildozer.info('Application pushed.')

    def cmd_run(self, *args):
        super(TargetAndroid, self).cmd_run(*args)

        entrypoint = self.buildozer.config.getdefault(
            'app', 'android.entrypoint', 'org.renpy.android.PythonActivity')
        package = self._get_package()

        # push on the device
        for serial in self.serials:
            self.buildozer.environ['ANDROID_SERIAL'] = serial
            self.buildozer.info('Run on {}'.format(serial))
            self.buildozer.cmd(
                '{adb} shell am start -n {package}/{entry} -a {entry}'.format(
                adb=self.adb_cmd, package=package, entry=entrypoint),
                cwd=self.buildozer.global_platform_dir)
        self.buildozer.environ.pop('ANDROID_SERIAL', None)

        self.buildozer.info('Application started.')

    def cmd_logcat(self, *args):
        '''Show the log from the device
        '''
        self.check_requirements()
        serial = self.serials[0:]
        if not serial:
            return
        self.buildozer.environ['ANDROID_SERIAL'] = serial[0]
        self.buildozer.cmd('{adb} logcat'.format(adb=self.adb_cmd),
                cwd=self.buildozer.global_platform_dir,
                show_output=True)
        self.buildozer.environ.pop('ANDROID_SERIAL', None)



def get_target(buildozer):
    return TargetAndroid(buildozer)

########NEW FILE########
__FILENAME__ = ios
'''
iOS target, based on kivy-ios project. (not working yet.)
'''

import sys
if sys.platform != 'darwin':
    raise NotImplementedError('Windows platform not yet working for Android')

import plistlib
from buildozer import BuildozerCommandException
from buildozer.target import Target, no_config
from os.path import join, basename
from getpass import getpass

PHP_TEMPLATE = '''
<?php
// credits goes to http://jeffreysambells.com/2010/06/22/ios-wireless-app-distribution

$ipas = glob('*.ipa');
$provisioningProfiles = glob('*.mobileprovision');
$plists = glob('*.plist');

$sr = stristr( $_SERVER['SCRIPT_URI'], '.php' ) === false ? 
    $_SERVER['SCRIPT_URI'] : dirname($_SERVER['SCRIPT_URI']) . '/';
$provisioningProfile = $sr . $provisioningProfiles[0];
$ipa = $sr . $ipas[0];
$itmsUrl = urlencode( $sr . 'index.php?plist=' . str_replace( '.plist', '', $plists[0] ) );


if ($_GET['plist']) {
    $plist = file_get_contents( dirname(__FILE__) 
        . DIRECTORY_SEPARATOR 
        . preg_replace( '/![A-Za-z0-9-_]/i', '', $_GET['plist']) . '.plist' );
    $plist = str_replace('_URL_', $ipa, $plist);
    header('content-type: application/xml');
    echo $plist;
    die();
}


?><!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<title>Install {appname}</title>
<style type="text/css">
li { padding: 1em; }
</style>

</head>
<body>
<ul>
    <li><a href="<? echo $provisioningProfile; ?>">Install Team Provisioning File</a></li>
    <li><a href="itms-services://?action=download-manifest&url=<? echo $itmsUrl; ?>">
         Install Application</a></li>
</ul>
</body>
</html>
'''

class TargetIos(Target):

    def check_requirements(self):
        checkbin = self.buildozer.checkbin
        cmd = self.buildozer.cmd

        checkbin('Xcode xcodebuild', 'xcodebuild')
        checkbin('Xcode xcode-select', 'xcode-select')
        checkbin('Git git', 'git')
        checkbin('Cython', 'cython')
        checkbin('Mercurial', 'hg')
        checkbin('Cython cython', 'cython')
        checkbin('pkg-config', 'pkg-config')
        checkbin('autoconf', 'autoconf')
        checkbin('automake', 'automake')
        checkbin('libtool', 'libtool')

        self.buildozer.debug('Check availability of a iPhone SDK')
        sdk = cmd('xcodebuild -showsdks | fgrep "iphoneos" |'
                'tail -n 1 | awk \'{print $2}\'',
                get_stdout=True)[0]
        if not sdk:
            raise Exception(
                'No iPhone SDK found. Please install at least one iOS SDK.')
        else:
            self.buildozer.debug(' -> found %r' % sdk)

        self.buildozer.debug('Check Xcode path')
        xcode = cmd('xcode-select -print-path', get_stdout=True)[0]
        if not xcode:
            raise Exception('Unable to get xcode path')
        self.buildozer.debug(' -> found {0}'.format(xcode))

    def install_platform(self):
        cmd = self.buildozer.cmd
        self.ios_dir = ios_dir = join(self.buildozer.platform_dir, 'kivy-ios')
        if not self.buildozer.file_exists(ios_dir):
            cmd('git clone git://github.com/kivy/kivy-ios',
                    cwd=self.buildozer.platform_dir)
        elif self.platform_update:
            cmd('git clean -dxf', cwd=ios_dir)
            cmd('git pull origin master', cwd=ios_dir)

        self.fruitstrap_dir = fruitstrap_dir = join(self.buildozer.platform_dir,
                'fruitstrap')
        if not self.buildozer.file_exists(fruitstrap_dir):
            cmd('git clone git://github.com/mpurland/fruitstrap.git',
                    cwd=self.buildozer.platform_dir)

    def compile_platform(self):
        state = self.buildozer.state
        is_compiled = state.get('ios.platform.compiled', '')
        if not is_compiled:
            self.buildozer.cmd('tools/build-all.sh', cwd=self.ios_dir)
        state['ios.platform.compiled'] = '1'

        if not self.buildozer.file_exists(self.fruitstrap_dir, 'fruitstrap'):
            self.buildozer.cmd('make fruitstrap', cwd=self.fruitstrap_dir)

    def _get_package(self):
        config = self.buildozer.config
        package_domain = config.getdefault('app', 'package.domain', '')
        package = config.get('app', 'package.name')
        if package_domain:
            package = package_domain + '.' + package
        return package.lower()

    def build_package(self):
        self._unlock_keychain()

        # create the project
        app_name = self.buildozer.namify(self.buildozer.config.get('app',
            'package.name'))

        self.app_project_dir = join(self.ios_dir, 'app-{0}'.format(app_name.lower()))
        if not self.buildozer.file_exists(self.app_project_dir):
            self.buildozer.cmd('tools/create-xcode-project.sh {0} {1}'.format(
                app_name, self.buildozer.app_dir),
                cwd=self.ios_dir)
        else:
            self.buildozer.cmd('tools/populate-project.sh {0} {1}'.format(
                app_name, self.buildozer.app_dir),
                cwd=self.ios_dir)

        # fix the plist
        plist_fn = '{}-Info.plist'.format(app_name.lower())
        plist_rfn = join(self.app_project_dir, plist_fn)
        version = self.buildozer.get_version()
        self.buildozer.info('Update Plist {}'.format(plist_fn))
        plist = plistlib.readPlist(plist_rfn)
        plist['CFBundleIdentifier'] = self._get_package()
        plist['CFBundleShortVersionString'] = version
        plist['CFBundleVersion'] = '{}.{}'.format(version,
                self.buildozer.build_id)

        # add icon
        icon = self._get_icon()
        if icon:
            plist['CFBundleIconFiles'] = [icon]
            plist['CFBundleIcons'] = {'CFBundlePrimaryIcon': {
                'UIPrerenderedIcon': False, 'CFBundleIconFiles': [icon]}}

        # ok, write the modified plist.
        plistlib.writePlist(plist, plist_rfn)

        mode = 'Debug' if self.build_mode == 'debug' else 'Release'
        self.buildozer.cmd('xcodebuild -configuration {} clean build'.format(mode),
                cwd=self.app_project_dir)
        ios_app_dir = 'app-{app_lower}/build/{mode}-iphoneos/{app_lower}.app'.format(
                app_lower=app_name.lower(), mode=mode)
        self.buildozer.state['ios:latestappdir'] = ios_app_dir

        key = 'ios.codesign.{}'.format(self.build_mode)
        ioscodesign = self.buildozer.config.getdefault('app', key, '')
        if not ioscodesign:
            self.buildozer.error('Cannot create the IPA package without'
                ' signature. You must fill the "{}" token.'.format(key))
            return
        elif ioscodesign[0] not in ('"', "'"):
            ioscodesign = '"{}"'.format(ioscodesign)

        ipa = join(self.buildozer.bin_dir, '{}-{}.ipa'.format(
            app_name, version))
        self.buildozer.cmd((
            '/usr/bin/xcrun '
            '-sdk iphoneos PackageApplication {ios_app_dir} '
            '-o {ipa} --sign {ioscodesign} --embed '
            '{ios_app_dir}/embedded.mobileprovision').format(
                ioscodesign=ioscodesign, ios_app_dir=ios_app_dir,
                mode=mode, ipa=ipa),
                cwd=self.ios_dir)

        self.buildozer.info('iOS packaging done!')
        self.buildozer.info('IPA {0} available in the bin directory'.format(
            basename(ipa)))
        self.buildozer.state['ios:latestipa'] = ipa
        self.buildozer.state['ios:latestmode'] = self.build_mode

        self._create_index()

    def cmd_deploy(self, *args):
        super(TargetIos, self).cmd_deploy(*args)
        self._run_fruitstrap(gdb=False)

    def cmd_run(self, *args):
        super(TargetIos, self).cmd_run(*args)
        self._run_fruitstrap(gdb=True)

    def cmd_xcode(self, *args):
        '''Open the xcode project.
        '''
        app_name = self.buildozer.namify(self.buildozer.config.get('app',
            'package.name'))
        app_name = app_name.lower()

        ios_dir = ios_dir = join(self.buildozer.platform_dir, 'kivy-ios')
        self.buildozer.cmd('open {}.xcodeproj'.format(
            app_name), cwd=join(ios_dir, 'app-{}'.format(app_name)))

    def _run_fruitstrap(self, gdb=False):
        state = self.buildozer.state
        if 'ios:latestappdir' not in state:
            self.buildozer.error(
                'App not built yet. Run "debug" or "release" first.')
            return
        ios_app_dir = state.get('ios:latestappdir')

        if gdb:
            gdb_mode = '-d'
            self.buildozer.info('Deploy and start the application')
        else:
            gdb_mode = ''
            self.buildozer.info('Deploy the application')

        self.buildozer.cmd('{fruitstrap} {gdb} -b {app_dir}'.format(
            fruitstrap=join(self.fruitstrap_dir, 'fruitstrap'),
            gdb=gdb_mode, app_dir=ios_app_dir),
            cwd=self.ios_dir, show_output=True)

    def _get_icon(self):
        # check the icon size, must be 72x72 or 144x144
        icon = self.buildozer.config.getdefault('app', 'icon.filename', '')
        if not icon:
            return
        icon_fn = join(self.buildozer.app_dir, icon)
        if not self.buildozer.file_exists(icon_fn):
            self.buildozer.error('Icon {} does not exists'.format(icon_fn))
            return
        output = self.buildozer.cmd('file {}'.format(icon),
                cwd=self.buildozer.app_dir, get_stdout=True)[0]
        if not output:
            self.buildozer.error('Unable to read icon {}'.format(icon_fn))
            return
        # output is something like: 
        # "data/cancel.png: PNG image data, 50 x 50, 8-bit/color RGBA,
        # non-interlaced"
        info = output.splitlines()[0].split(',')
        fmt = info[0].split(':')[-1].strip()
        if fmt != 'PNG image data':
            self.buildozer.error('Only PNG icon are accepted, {} invalid'.format(icon_fn))
            return
        size = [int(x.strip()) for x in info[1].split('x')]
        if size != [72, 72] and size != [144, 144]:
            # icon cannot be used like that, it need a resize.
            self.buildozer.error('Invalid PNG size, must be 72x72 or 144x144. Resampling.')
            nearest_size = 144
            if size[0] < 144:
                nearest_size = 72

            icon_basename = 'icon-{}.png'.format(nearest_size)
            self.buildozer.file_copy(icon_fn, join(self.app_project_dir,
                icon_basename))
            self.buildozer.cmd('sips -z {0} {0} {1}'.format(nearest_size,
                icon_basename), cwd=self.app_project_dir)
        else:
            # icon ok, use it as it.
            icon_basename = 'icon-{}.png'.format(size[0])
            self.buildozer.file_copy(icon_fn, join(self.app_project_dir,
                icon_basename))

        icon_fn = join(self.app_project_dir, icon_basename)
        return icon_fn

    def _create_index(self):
        # TODO
        pass

    def check_configuration_tokens(self):
        errors = []
        config = self.buildozer.config
        identity_debug = config.getdefault('app', 'ios.codesign.debug', '')
        identity_release = config.getdefault('app', 'ios.codesign.release',
                identity_debug)
        available_identities = self._get_available_identities()

        if not identity_debug:
            errors.append('[app] "ios.codesign.debug" key missing, '
                    'you must give a certificate name to use.')
        elif identity_debug not in available_identities:
            errors.append('[app] identity {} not found. '
                    'Check with list_identities'.format(identity_debug))

        if not identity_release:
            errors.append('[app] "ios.codesign.release" key missing, '
                    'you must give a certificate name to use.')
        elif identity_release not in available_identities:
            errors.append('[app] identity "{}" not found. '
                    'Check with list_identities'.format(identity_release))

        super(TargetIos, self).check_configuration_tokens(errors)

    @no_config
    def cmd_list_identities(self, *args):
        '''List the available identities to use for signing.
        '''
        identities = self._get_available_identities()
        print('Available identities:')
        for x in identities:
            print('  - {}'.format(x))

    def _get_available_identities(self):
        output = self.buildozer.cmd('security find-identity -v -p codesigning',
                get_stdout=True)[0]

        lines = output.splitlines()[:-1]
        lines = ['"{}"'.format(x.split('"')[1]) for x in lines]
        return lines

    def _unlock_keychain(self):
        password_file = join(self.buildozer.buildozer_dir, '.ioscodesign')
        password = None
        if self.buildozer.file_exists(password_file):
            with open(password_file) as fd:
                password = fd.read()

        if not password:
            # no password available, try to unlock anyway...
            error = self.buildozer.cmd('security unlock-keychain -u',
                    break_on_error=False)[2]
            if not error:
                return
        else:
            # password available, try to unlock
            error = self.buildozer.cmd('security unlock-keychain -p {}'.format(
                password), break_on_error=False, sensible=True)[2]
            if not error:
                return

        # we need the password to unlock.
        correct = False
        attempt = 3
        while attempt:
            attempt -= 1
            password = getpass('Password to unlock the default keychain:')
            error = self.buildozer.cmd('security unlock-keychain -p "{}"'.format(
                password), break_on_error=False, sensible=True)[2]
            if not error:
                correct = True
                break
            self.error('Invalid keychain password')

        if not correct:
            self.error('Unable to unlock the keychain, exiting.')
            raise BuildozerCommandException()

        # maybe user want to save it for further reuse?
        print(
            'The keychain password can be saved in the build directory\n'
            'As soon as the build directory will be cleaned, '
            'the password will be erased.')

        save = None
        while save is None:
            q = raw_input('Do you want to save the password (Y/n): ')
            if q in ('', 'Y'):
                save = True
            elif q == 'n':
                save = False
            else:
                print('Invalid answer!')

        if save:
            with open(password_file, 'wb') as fd:
                fd.write(password)

def get_target(buildozer):
    return TargetIos(buildozer)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Buildozer documentation build configuration file, created by
# sphinx-quickstart on Sun Apr 20 16:56:31 2014.
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
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Buildozer'
copyright = u'2014, Kivy\'s Developers'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.11'
# The full version, including alpha/beta/rc tags.
release = '0.11'

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
exclude_patterns = []

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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


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
htmlhelp_basename = 'Buildozerdoc'


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
  ('index', 'Buildozer.tex', u'Buildozer Documentation',
   u'Kivy\'s Developers', 'manual'),
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
    ('index', 'buildozer', u'Buildozer Documentation',
     [u'Kivy\'s Developers'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Buildozer', u'Buildozer Documentation',
   u'Kivy\'s Developers', 'Buildozer', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
