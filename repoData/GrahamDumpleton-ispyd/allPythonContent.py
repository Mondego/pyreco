__FILENAME__ = client
import cmd
import ConfigParser
import glob
import os
import socket
import sys
import threading

class ClientShell(cmd.Cmd):

    prompt = '(ispyd) '

    def __init__(self, config_file, stdin=None, stdout=None):
        cmd.Cmd.__init__(self, stdin=stdin, stdout=stdout)

        self.__config_file = config_file
        self.__config_object = ConfigParser.RawConfigParser()

        if not self.__config_object.read([config_file]):
            raise RuntimeError('Unable to open configuration file %s.' %
                               config_file)

        server = self.__config_object.get('ispyd', 'listen') % {'pid': '*'}

        if os.path.isabs(server):
            self.__servers = [(socket.AF_UNIX, path) for path in
                             sorted(glob.glob(server))]
        else:
            host, port = server.split(':')
            port = int(port)

            self.__servers = [(socket.AF_INET, (host, port))]

    def emptyline(self):
        pass

    def help_help(self):
        print >> self.stdout, """help (command)
        Output list of commands or help details for named command."""

    def do_exit(self, line):
        """exit
        Exit the client shell."""

        return True

    def do_servers(self, line):
        """servers
        Display a list of the servers which can be connected to."""

        for i in range(len(self.__servers)):
            print >> self.stdout, '%s: %s' % (i+1, self.__servers[i])

    def do_connect(self, line):
        """connect [index]
        Connect to the server from the servers lift with given index. If
        there is only one server then the index position does not need to
        be supplied."""

        if len(self.__servers) == 0:
            print >> self.stdout, 'No servers to connect to.'
            return

        if not line:
            if len(self.__servers) != 1:
                print >> self.stdout, 'Multiple servers, which should be used?'
                return
            else:
                line = '1'

        try:
            selection = int(line)
        except:
            selection = None

        if selection is None:
            print >> self.stdout, 'Server selection not an integer.'
            return

        if selection <= 0 or selection > len(self.__servers):
            print >> self.stdout, 'Invalid server selected.'
            return

        server = self.__servers[selection-1]

        client = socket.socket(server[0], socket.SOCK_STREAM)
        client.connect(server[1])

        def write():
            while 1:
                try:
                    c = sys.stdin.read(1)
                    if not c:
                        client.shutdown(socket.SHUT_RD)
                        break
                    client.sendall(c)
                except:
                    break

        def read():
            while 1:
                try:
                    c = client.recv(1)
                    if not c:
                        break
                    sys.stdout.write(c)
                    sys.stdout.flush()
                except:
                    break

        thread1 = threading.Thread(target=write)
        thread1.setDaemon(True)

        thread2 = threading.Thread(target=read)
        thread2.setDaemon(True)

        thread1.start()
        thread2.start()

        thread2.join()

        return True

def main():
    shell = ClientShell(sys.argv[1])
    shell.cmdloop()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = console
import code
import os
import sys
import threading

import __builtin__

from ispyd.wrapper import ObjectWrapper

_consoles = threading.local()

def acquire_console(shell):
    _consoles.active = shell

def release_console():
    del _consoles.active

def setquit():
    """Define new built-ins 'quit' and 'exit'.
    These are simply strings that display a hint on how to exit.

    """
    if os.sep == ':':
        eof = 'Cmd-Q'
    elif os.sep == '\\':
        eof = 'Ctrl-Z plus Return'
    else:
        eof = 'Ctrl-D (i.e. EOF)'

    class Quitter(object):
        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return 'Use %s() or %s to exit' % (self.name, eof)

        def __call__(self, code=None):
            # If executed with our interactive console, only raise the
            # SystemExit exception but don't close sys.stdout as we are
            # not the owner of it.

            if hasattr(_consoles, 'active'):
                raise SystemExit(code)

            # Shells like IDLE catch the SystemExit, but listen when their
            # stdin wrapper is closed.

            try:
                sys.stdin.close()
            except:
                pass
            raise SystemExit(code)

    __builtin__.quit = Quitter('quit')
    __builtin__.exit = Quitter('exit')

setquit()

class OutputWrapper(ObjectWrapper):

    def flush(self):
        try:
            shell = _consoles.active
            return shell.stdout.flush()
        except:
            return self._ispyd_next_object.flush()

    def write(self, data):
        try:
            shell = _consoles.active
            return shell.stdout.write(data)
        except:
            return self._ispyd_next_object.write(data)

    def writelines(self, data):
        try:
            shell = _consoles.active
            return shell.stdout.writelines(data)
        except:
            return self._ispyd_next_object.writelines(data)

sys.stdout = OutputWrapper(sys.stdout)
sys.stderr = OutputWrapper(sys.stderr)

########NEW FILE########
__FILENAME__ = manager
import atexit
import cmd
import ConfigParser
import os
import socket
import threading
import traceback
import sys

from ispyd.shell import RootShell

class ShellManager(object):

    def __init__(self, config_file):
        self.__config_file = config_file
        self.__config_object = ConfigParser.RawConfigParser()

        if not self.__config_object.read([config_file]):
            raise RuntimeError('Unable to open configuration file %s.' %
                               config_file)

        self.__socket_server = self.__config_object.get('ispyd',
            'listen') % {'pid': os.getpid()}

        if not os.path.isabs(self.__socket_server):
            host, port = self.__socket_server.split(':')
            port = int(port)
            self.__socket_server = (host, port)

        self.__thread = threading.Thread(target=self.__thread_run,
            name='ISpyd-Shell-Manager')

        self.__thread.setDaemon(True)
        self.__thread.start()

    def __socket_cleanup(self, path):
        try:
            os.unlink(path)
        except:
            pass

    def __thread_run(self):
        if type(self.__socket_server) == type(()):
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(self.__socket_server)
        else:
            try:
                os.unlink(self.__socket_server)
            except:
                pass

            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            listener.bind(self.__socket_server)

            atexit.register(self.__socket_cleanup, self.__socket_server)
            os.chmod(self.__socket_server, 0600)

        listener.listen(5)

        while True:
            client, addr = listener.accept()

            shell = RootShell(self.__config_object)

            shell.stdin = client.makefile('r')
            shell.stdout = client.makefile('w')

            try:
                shell.cmdloop()
            except:
                print >> shell.stdout, 'Exception in shell "%s".' % shell.name
                traceback.print_exception(*sys.exc_info(), file=shell.stdout)

            shell.stdin = None
            shell.stdout = None

            del shell

            client.close()

########NEW FILE########
__FILENAME__ = debugger
import inspect
import pdb
import sys
import traceback

from ispyd.wrapper import ObjectWrapper
from ispyd.console import acquire_console, release_console

_probes = {}
_tracebacks = {}

class DebuggerWrapper(ObjectWrapper):

    def __init__(self, wrapped, name):
        super(DebuggerWrapper, self).__init__(wrapped)
        self._ispyd_name = name

    def _ispyd_new_object(self, wrapped):
        return self.__class__(wrapped, self._ispyd_name)

    def __call__(self, *args, **kwargs):
        try:
            return self._ispyd_next_object(*args, **kwargs)
        except:
            _tracebacks[self._ispyd_name] = sys.exc_info()[2]
            raise

def resolve_path(module, name):
    if not inspect.ismodule(module):
        __import__(module)
        module = sys.modules[module]

    parent = module

    path = name.split('.')
    attribute = path[0]

    original = getattr(parent, attribute)
    for attribute in path[1:]:
        parent = original
        original = getattr(original, attribute)

    return (parent, attribute, original)

def remove_probe(module, name):
    (parent, attribute, original) = resolve_path(module, name)
    wrapper = getattr(parent, attribute)
    original = wrapper._ispyd_next_object
    setattr(parent, attribute, original)

def insert_probe(module, name, factory, args=()):
    (parent, attribute, original) = resolve_path(module, name)
    wrapper = factory(original, *args)
    setattr(parent, attribute, wrapper)
    return wrapper

class DebuggerShell(object):

    name = 'debugger'

    def activate(self, config_object):
        self.__config_object = config_object

        enabled = False

        if self.__config_object.has_option('debugger', 'enabled'):
            value = self.__config_object.get('debugger', 'enabled')
            enabled = value.lower() in ('1', 'on', 'yes', 'true')

        if not enabled:
            print >> self.stdout, 'Sorry, the debugger plugin is disabled.'
            return True

    def do_insert(self, line):
        """insert (module:function|module:class.function)
	Insert a debugger probe around the nominated function to capture
	traceback for future exception raised in the context of that
	function."""

        if not line:
            print >> self.stdout, 'Invalid probe location.'
            return

        if line in _probes:
            print >> self.stdout, 'Probe already exists.'
            return

        try:
            module, name = line.split(':')
        except:
            print >> self.stdout, 'Invalid probe location.'
            return

        try:
            _probes[line] = insert_probe(module, name,
                                         DebuggerWrapper, (line,))
        except:
            print >> self.stdout, 'Failed to insert probe.'
            return

    def do_remove(self, line):
        """remove (module:function|module:class.function)
        Remove the debugger probe around the nominated function."""

        if not line:
            print >> self.stdout, 'Invalid probe location.'
            return

        if not line in _probes:
            print >> self.stdout, 'Probe does not exist.'
            return

        try:
            module, name = line.split(':')
        except:
            print >> self.stdout, 'Invalid probe location.'
            return

        try:
            remove_probe(module, name)
        except:
            print >> self.stdout, 'Failed to remove probe.'
            return
        else:
            del _probes[line]

    def do_list(self, line):
        """list
        Display the list of functions which debugger probes have currently
        been added around."""

        print >> self.stdout, sorted(_probes.keys())

    def do_reset(self, line):
        """reset
        Remove all debugger probes and clear out any tracebacks which have
        been captured from past exceptions."""

        global _tracebacks
        _tracebacks = []
        for name in _probes.keys():
            self.do_remove(name)

    def do_tracebacks(self, line):
        """traceback
        Display a list of the tracebacks that have been captured from past
        exceptions."""

        print >> self.stdout, _tracebacks

    def do_print(self, line):
        """print (module:function|module:class.function)
        Print the stack trace for the traceback captured for the nominated
        function."""

        if not line in _tracebacks:
            return
        traceback.print_tb(_tracebacks[line], file=self.stdout)

    def do_discard(self, line):
        """discard (module:function|module:class.function)
        Discards the current traceback currently held for the nominated
        function."""

        if line in _tracebacks:
            del _tracebacks[line]

    def do_debug(self, line):
        """debug (module:function|module:class.function)
        Run 'pdb' in post mortem mode for the traceback captured against
        the nominated function."""

        if not line in _tracebacks:
            return

        tb = _tracebacks[line]

        debugger = pdb.Pdb(stdin=self.stdin, stdout=self.stdout)
        debugger.reset()

        acquire_console(self)

        try:
            debugger.interaction(None, tb)
        except SystemExit:
            pass
        finally:
            release_console()

########NEW FILE########
__FILENAME__ = process
import fnmatch
import os
import sys

class ProcessShell(object):

    name = 'process'

    def do_pid(self, line):
        """pid
	Display the process ID of the current process."""

        print >> self.stdout, os.getpid()

    def do_uid(self, line):
        """uid
	Display the uid under which the process is executing."""

        print >> self.stdout, os.getuid()

    def do_euid(self, line):
        """uid
	Display the current effective uid under which the process is
	executing."""

        print >> self.stdout, os.geteuid()

    def do_gid(self, line):
        """gid
	Display the gid under which the process is executing."""

        print >> self.stdout, os.getgid()

    def do_egid(self, line):
        """egid
	Display the current effective gid under which the process is
	executing."""

        print >> self.stdout, os.getegid()

    def do_cwd(self, line):
        """cwd
	Display the current working directory the process is running in."""

        print >> self.stdout, os.getcwd()

########NEW FILE########
__FILENAME__ = profiler
import atexit
import Queue
import StringIO
import sys
import threading
import time
import traceback

_profiler = None

class Profiler(threading.Thread):

    def __init__(self, duration, interval, filename):
        super(Profiler, self).__init__()
        self._duration = duration
        self._interval = interval
        self._filename = filename
        self._queue = Queue.Queue()
        self._nodes = {}
        self._links = {}

    def run(self):
        start = time.time()

        while time.time() < start+self._duration:
            try:
                self._queue.get(timeout=self._interval)
                break
            except:
                pass

            stacks = sys._current_frames().values()

            for stack in stacks:
                self.process_stack(stack)

        print >> open(self._filename, 'w'), repr((self._nodes, self._links))

        #print >> open(self._filename, 'w'), repr(self._records)

        global _profiler

        _profiler = None

    def abort(self):
        self._queue.put(True)
        self.join()

    def process_stack(self, stack):
        output = StringIO.StringIO()

        parent = None

        for filename, lineno, name, line in traceback.extract_stack(stack): 
            node = (filename, name)

            node_record = self._nodes.get(node)

            if node_record is None:
                node_record = { 'count': 1 }
                self._nodes[node] = node_record
            else:
                node_record['count'] += 1

            if parent:
                link = (parent, node)

                link_record = self._links.get(link)

                if link_record is None:
                    link_record = { 'count': 1 }
                    self._links[link] = link_record
                else:
                    link_record['count'] += 1

            parent = node
                    

        """
        children = None

        for filename, lineno, name, line in traceback.extract_stack(stack): 
            #key = (filename, lineno, name)
            key = (filename, name)

            if children is None:
                record = self._records.get(key)

                if record is None:
                    record = { 'count': 1, 'children': {} }
                    self._records[key] = record
                else:
                    record['count'] += 1

                children = record['children']

            elif key in children:
                record = children[key]
                record['count'] += 1
                children = record['children']

            else:
                record = { 'count': 1, 'children': {} }
                children[key] = record
                children = record['children']
        """

def _abort():
    if _profiler:
        _profiler.abort()

atexit.register(_abort)

class ProfilerShell(object):

    name = 'profiler'

    def activate(self, config_object):
        self.__config_object = config_object

        enabled = False

        if self.__config_object.has_option('profiler', 'enabled'):
            value = self.__config_object.get('profiler', 'enabled')
            enabled = value.lower() in ('1', 'on', 'yes', 'true')

        if not enabled:
            print >> self.stdout, 'Sorry, the profiler plugin is disabled.'
            return True

    def do_start(self, line):
        global _profiler

        if _profiler is None:
            _profiler = Profiler(10.0*60.0, 0.105, '/tmp/profile.dat')
            #_profiler = Profiler(20.0, 1.0, '/tmp/profile.dat')
            _profiler.start()

    def do_abort(self, line):
        global _profiler

        if _profiler is None:
            _profiler.abort()

########NEW FILE########
__FILENAME__ = python
import code
import fnmatch
import os
import sys
import thread
import threading
import traceback

from ispyd.console import acquire_console, release_console

class EmbeddedConsole(code.InteractiveConsole):

    def write(self, data):
        self.stdout.write(data)
        self.stdout.flush()

    def raw_input(self, prompt):
        self.stdout.write(prompt)
        self.stdout.flush()
        line = self.stdin.readline()
        line = line.rstrip('\r\n')
        return line

class PythonShell(object):

    name = 'python'

    def activate(self, config_object):
        self.__config_object = config_object

    def do_platform(self, line):
        """platform
	Display the platform the process is running on. This is the value
        available from 'sys.platform'."""

        print >> self.stdout, sys.platform

    def do_version(self, line):
        """version
	Display the version of Python being used. This is the value
	available from 'sys.version'."""

        print >> self.stdout, sys.version

    def do_prefix(self, line):
        """prefix
	Display the location of the Python installation being used. This is
	the value available from 'sys.prefix'."""

        print >> self.stdout, sys.prefix

    def do_path(self, line):
        """path
	Display the Python module search path. This is the value available
	from 'sys.path'."""

        print >> self.stdout, sys.path

    def do_executable(self, line):
        """executable
	Display the executable run when this process was started. This is
	the value available from 'sys.executable'.
        
	Note that in an embedded system this may not refer to the Python
	executable, but the name of the application Python was being
	embedded in."""

        print >> self.stdout, sys.executable

    def do_argv(self, line):
        """argv
        Display the command line arguments supplied when the executable
        that started this process was run. This is the value available
        from 'sys.argv'.

        Note that in an embedded sytem this may not reflect the actual
        command line arguments used."""

        print >> self.stdout, sys.argv

    def do_defaultencoding(self, line):
        """defaultencoding
        Display the default encoding used when converting Unicode strings.
        This is the value available from 'sys.defaultencoding'."""

        print >> self.stdout, sys.getdefaultencoding()

    def do_filesystemencoding(self, line):
        """filesystemencoding
        Display the file system encoding. This is the value available from
        'sys.filesystemencoding'."""

        print >> self.stdout, sys.getfilesystemencoding()

    def do_maxint(self, line):
        """maxint
	Display the largest positive integer supported by Pythons regular
	integer type. This is the value available from 'sys.maxint'."""

        print >> self.stdout, sys.maxint

    def do_maxsize(self, line):
        """maxsize
	Display the largest positive integer supported by the platforms
	Py_ssize_t type, and thus the maximum size lists, strings, dicts,
	and many other containers can have. This is the value available
	from 'sys.maxsize'."""

        print >> self.stdout, sys.maxsize

    def do_maxunicode(self, line):
        """maxunicode
	Display an integer giving the largest supported code point for a
	Unicode character. The value of this depends on the configuration
	option that specifies whether Unicode characters are stored as
	UCS-2 or UCS-4. This is the value available from 'sys.maxunicode'."""

        print >> self.stdout, sys.maxunicode

    def do_environ(self, line):
        """environ
	Display the set of environment variables for the process. This is
        the set of environment variables available from 'os.environ'.

	Note that this is only those environment variables which were
	already set at the point the Python (sub)interpreter was started or
	which were later set from within the (sub)interpreter. It will not
	include any which are later set from C code, or set from within
	another Python (sub)interpreter within the same process."""

        print >> self.stdout, os.environ

    def do_modules(self, pattern):
        """modules
        Display the currently loaded Python modules. By default this will
        only display the root module for any packages. If you wish to see
        all modules, including sub modules of packages, use 'modules *'.
	The value '*' can be replaced with any glob pattern to be more
	selective. For example 'modules ispyd.*' will list just the sub
	modules for this package."""

        if pattern:
            result = []
            for name in sys.modules.keys():
                if fnmatch.fnmatch(name, pattern):
                    result.append(name)
            print >> self.stdout, sorted(result)
        else:
            result = []
            for name in sys.modules.keys():
                if not '.' in name:
                    result.append(name)
            print >> self.stdout, sorted(result)

    def do_threads(self, line): 
        """threads
	Display stack trace dumps for all threads currently executing
	within the Python interpreter.
        
        Note that if coroutines are being used, such as systems based
        on greenlets, then only the thread stack of the currently
        executing coroutine will be displayed."""

        all = [] 
        for threadId, stack in sys._current_frames().items():
            block = []
            block.append('# ThreadID: %s' % threadId) 
            thr = threading._active.get(threadId)
            if thr:
                block.append('# Name: %s' % thr.name) 
            for filename, lineno, name, line in traceback.extract_stack(
                stack): 
                block.append('File: \'%s\', line %d, in %s' % (filename,
                        lineno, name)) 
                if line:
                    block.append('  %s' % (line.strip()))
            all.append('\n'.join(block))

        print >> self.stdout, '\n\n'.join(all)

    def do_console(self, line):
        """console
        When enabled in the configuration file, will startup up an embedded
        interactive Python interpreter. Invoke 'exit()' or 'quit()' to
        escape the interpreter session."""

        enabled = False

        if self.__config_object.has_option('python:console', 'enabled'):
            value = self.__config_object.get('python:console', 'enabled')
            enabled = value.lower() in ('1', 'on', 'yes', 'true')

        if not enabled:
            print >> self.stdout, 'Sorry, the Python console is disabled.'
            return

        locals = {}

        locals['stdin'] = self.stdin
        locals['stdout'] = self.stdout

        console = EmbeddedConsole(locals)

        console.stdin = self.stdin
        console.stdout = self.stdout

        acquire_console(self)

        try:
            console.interact()
        except SystemExit:
            pass
        finally:
            release_console()

########NEW FILE########
__FILENAME__ = wsgi
import StringIO
import sys
import thread
import threading
import time
import traceback

from ispyd.wrapper import ObjectWrapper

_exceptions = []

class WSGITransaction(object):

    request_lock = threading.Lock()
    request_count = 0

    transactions = {}

    def __init__(self, environ):
        self.environ = environ

        self.thread_id = thread.get_ident()

        self.deleted = False
        self.running = False

        self.start = 0.0
        self.finish = 0.0

        with self.request_lock:
            WSGITransaction.request_count += 1
            self.request_id = WSGITransaction.request_count

    def __del__(self):
        self.deleted = True
        if self.running:
            self.__exit__(None, None, None)

    def __enter__(self):
        self.transactions[self.request_id] = self
        self.running = True
        self.start = time.time()
        return self

    def __exit__(self, exc, value, tb):
        _exceptions.append(tb)
        self.running = False
        self.finish = time.time()
        if not self.deleted:
            try:
                del self.transactions[self.request_id]
            except:
                pass

class WSGIApplicationIterable(object):

    def __init__(self, transaction, iterable):
        self.transaction = transaction
        self.iterable = iterable

    def __iter__(self):
        for item in self.iterable:
            yield item

    def close(self):
        try:
            if hasattr(self.iterable, 'close'):
                self.iterable.close()
        except:
            self.transaction.__exit__(*sys.exc_info())
            raise
        else:
            self.transaction.__exit__(None, None, None)

class WSGIApplicationWrapper(ObjectWrapper):

    def _ispyd_new_object(self, wrapped):
        return self.__class__(wrapped)

    def __call__(self, environ, start_response):
        transaction = WSGITransaction(environ)
        transaction.__enter__()

        try:
            iterable = self._ispyd_next_object(environ, start_response)
        except:
            transaction.__exit__(*sys.exc_info())
            raise

        return WSGIApplicationIterable(transaction, iterable)

def wsgi_application():
    def decorator(wrapped):
        return WSGIApplicationWrapper(wrapped)
    return decorator

class WSGIShell(object):

    name = 'wsgi'

    def format_traceback(self, stack):
        output = StringIO.StringIO()

        for filename, lineno, name, line in traceback.extract_stack(stack): 
            print >> output, 'File: "%s", line %d, in %s' % (
                    filename, lineno, name)
            if line: 
                print >> output, '  %s' % line.strip()

        return output.getvalue()

    def format_transaction(self, transaction, frames):
        output = StringIO.StringIO()

        start_time = time.ctime(transaction.start)
        duration = time.time() - transaction.start

        print >> output

        print >> output, '==== %d ====' % transaction.request_id

        print >> output

        print >> output, 'thread_id = %d' % transaction.thread_id
        print >> output, 'start_time = %s' % start_time
        print >> output, 'duration = %0.6f seconds' % duration

        print >> output

        for key in sorted(transaction.environ.keys()):
            value = repr(transaction.environ[key])
            print >> output, '%s = %s' % (key, value)

        print >> output

        text = None

        if transaction.thread_id in frames:
            text = self.format_traceback(frames[transaction.thread_id])

        if not text or transaction.finish != 0.0:
            return ''

        print >> output, text

        return output.getvalue()

    def do_requests(self, line):
        """requests
        Display details on any web requests currently being processed by
        the WSGI application."""

        output = StringIO.StringIO()

        frames = dict(sys._current_frames().items())
        transactions = dict(WSGITransaction.transactions)
        request_ids = sorted(transactions.keys())

        for i in range(len(request_ids)):
            request_id = request_ids[i]
            text = self.format_transaction(transactions[request_id], frames)
            if text:
                output.write(text)

        text = output.getvalue()
        if text:
            print >> self.stdout, text
        else:
            print >> self.stdout, 'No active transactions.'

########NEW FILE########
__FILENAME__ = shell
import cmd
import os
import sys
import traceback

_builtin_plugins = [
  'ispyd.plugins.debugger:DebuggerShell',
  'ispyd.plugins.process:ProcessShell',
  'ispyd.plugins.profiler:ProfilerShell',
  'ispyd.plugins.python:PythonShell',
  'ispyd.plugins.wsgi:WSGIShell',
]

class ProxyShell(cmd.Cmd):

    use_rawinput = 0

    def __init__(self, plugin, stdin, stdout):
        cmd.Cmd.__init__(self, stdin=stdin, stdout=stdout)

        self.__plugin = plugin

        plugin.stdin = stdin
        plugin.stdout = stdout

    def activate(self, config_object):
        if hasattr(self.__plugin, 'activate'):
            return self.__plugin.activate(config_object)

    def shutdown(self):
        if hasattr(self.__plugin, 'shutdown'):
            return self.__plugin.shutdown()

    def get_names(self):
        names1 = []
        classes = [self.__plugin.__class__]
        while classes:
            aclass = classes.pop(0)
            if aclass.__bases__:
                classes = classes + list(aclass.__bases__)
            names1 = names1 + dir(aclass)

        names2 = cmd.Cmd.get_names(self)

        names = set(names1 + names2)

        return list(names)

    def emptyline(self):
        pass

    def __getattr__(self, name):
        return getattr(self.__plugin, name)

    def do_prompt(self, flag):
        """prompt (on|off)
	Enable or disable the shell prompt."""

        if flag == 'on':
            self.prompt = '(%s:%d) ' % (self.__plugin.name, os.getpid())
        elif flag == 'off':
            self.prompt = ''

    def do_exit(self, line):
        """exit
        Exit the sub shell. Control will be returned to the root shell."""

        if hasattr(self.__plugin, 'do_exit'):
            self.__plugin.do_exit(line)
        return True

    def help_help(self):
        print >> self.stdout, """help (command)
        Output list of commands or help details for named command."""

class RootShell(cmd.Cmd):

    name = 'ispyd'

    use_rawinput = 0

    def __init__(self, config_object):
        cmd.Cmd.__init__(self)

        self.__config_object = config_object

        self.__plugins = {}

        if self.__config_object.has_option('ispyd', 'plugins'):
            names = self.__config_object.get('ispyd', 'plugins')
            names = names % {'builtins': ' '.join(_builtin_plugins)}
            names = names.split()
        else:
            names = _builtin_plugins

        for name in names:
            module, object = name.split(':')
            __import__(module)
            plugin = getattr(sys.modules[module], object)
            self.__plugins[plugin.name] = plugin

        self.do_prompt('on')

    def emptyline(self):
        pass

    def do_prompt(self, flag):
        """prompt (on|off)
	Enable or disable the shell prompt. When invoking a sub shell, the
	current setting will be inherited by the sub shell."""

        if flag == 'on':
            self.prompt = '(%s:%d) ' % (self.name, os.getpid())
        elif flag == 'off':
            self.prompt = ''

    def do_plugins(self, line):
        """plugins
        Outputs the names of the loaded plugins."""

        plugins = sorted(self.__plugins.keys())
        print >> self.stdout, plugins

    def do_shell(self, name):
        """enter name
        Invoke and enter into shell for the named plugin."""

        if name in self.__plugins:
            type = self.__plugins[name]

            plugin = type()

            shell = ProxyShell(plugin, self.stdin, self.stdout)

            shell.do_prompt(self.prompt and 'on' or 'off')

            if shell.activate(self.__config_object):
                return

            try:
                shell.cmdloop()
            except:
                print >> self.stdout, 'Exception in shell "%s".' % plugin.name
                traceback.print_exception(*sys.exc_info(), file=self.stdout)

            shell.shutdown()

    def do_exit(self, line):
        """exit
        Exit the root shell."""

        return True

    def help_help(self):
        print >> self.stdout, """help (command)
        Output list of commands or help details for named command."""

########NEW FILE########
__FILENAME__ = wrapper
import sys

# From Python 3.X. In older Python versions it fails if attributes do
# not exist and don't maintain a __wrapped__ attribute.

WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__doc__', '__annotations__')
WRAPPER_UPDATES = ('__dict__',)

def update_wrapper(wrapper,
                   wrapped,
                   assigned = WRAPPER_ASSIGNMENTS,
                   updated = WRAPPER_UPDATES):
    """Update a wrapper function to look like the wrapped function

       wrapper is the function to be updated
       wrapped is the original function
       assigned is a tuple naming the attributes assigned directly
       from the wrapped function to the wrapper function (defaults to
       functools.WRAPPER_ASSIGNMENTS)
       updated is a tuple naming the attributes of the wrapper that
       are updated with the corresponding attribute from the wrapped
       function (defaults to functools.WRAPPER_UPDATES)
    """
    wrapper.__wrapped__ = wrapped
    for attr in assigned:
        try:
            value = getattr(wrapped, attr)
        except AttributeError:
            pass
        else:
            setattr(wrapper, attr, value)
    for attr in updated:
        getattr(wrapper, attr).update(getattr(wrapped, attr, {}))
    # Return the wrapper so this can be used as a decorator via partial()
    return wrapper

# Generic object wrapper which tries to proxy everything through to
# the wrapped object and also preserve introspection abilties.

class ObjectWrapper(object):

    def __init__(self, wrapped):
        if type(wrapped) == type(()):
            (instance, wrapped) = wrapped
        else:
            instance = None

        self._ispyd_instance = instance
        self._ispyd_next_object = wrapped

        try:
            self._ispyd_last_object = wrapped._ispyd_last_object
        except:
            self._ispyd_last_object = wrapped

        for attr in WRAPPER_ASSIGNMENTS:
            try:
                value = getattr(wrapped, attr)
            except AttributeError:
                pass
            else:
                object.__setattr__(self, attr, value)

    def __setattr__(self, name, value):
        if not name.startswith('_ispyd_'):
            setattr(self._ispyd_next_object, name, value)
        else:
            self.__dict__[name] = value

    def __getattr__(self, name):
        return getattr(self._ispyd_next_object, name)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        descriptor = self._ispyd_next_object.__get__(instance, owner)
        return self._ispyd_new_object((instance, descriptor))

    def _ispyd_new_object(self, wrapped):
        return self.__class__(wrapped)

    def __dir__(self):
        return dir(self._ispyd_next_object)

    def __call__(self, *args, **kwargs):
        return self._ispyd_next_object(*args, **kwargs)

########NEW FILE########
__FILENAME__ = wsgi
import os
import flask
import time

from ispyd.manager import ShellManager
from ispyd.plugins.wsgi import WSGIApplicationWrapper

config_file = os.path.join(os.path.dirname(__file__), 'ispyd.ini')
shell_manager = ShellManager(config_file)

application = flask.Flask(__name__)
application.wsgi_app = WSGIApplicationWrapper(application.wsgi_app)

def function():
    raise RuntimeError('xxx')

@application.route("/")
def hello():
    time.sleep(0.05)
    function()
    return flask.render_template_string("Hello World!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    application.run(host='0.0.0.0', port=port)

########NEW FILE########
