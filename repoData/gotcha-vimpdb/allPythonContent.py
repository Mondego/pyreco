__FILENAME__ = manual_test
def output(arg):
    print "MANUAL: arg=", arg


def main():
    import vimpdb; vimpdb.set_trace()
    for abc in range(10):
        output(abc)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = bbbconfig
import os
import ConfigParser

from vimpdb import errors


def read_from_file_4_0(filename, klass):
    parser = ConfigParser.RawConfigParser()
    parser.read(filename)
    if not parser.has_section('vimpdb'):
        raise errors.BadRCFile('[vimpdb] section is missing in "%s"' %
            filename)
    error_msg = ("'%s' option is missing from section [vimpdb] in "
        + "'" + filename + "'.")
    if parser.has_option('vimpdb', 'script'):
        vim_client_script = parser.get('vimpdb', 'script')
    else:
        raise errors.BadRCFile(error_msg % "vim_client_script")
    if parser.has_option('vimpdb', 'server_name'):
        server_name = parser.get('vimpdb', 'server_name')
    else:
        raise errors.BadRCFile(error_msg % 'server_name')
    if parser.has_option('vimpdb', 'port'):
        port = parser.getint('vimpdb', 'port')
    else:
        raise errors.BadRCFile(error_msg % 'port')
    if parser.has_option('vimpdb', 'script'):
        vim_server_script = parser.get('vimpdb', 'script')
    else:
        raise errors.BadRCFile(error_msg % "vim_server_script")
    return klass(vim_client_script, vim_server_script, server_name, port)


ENVIRON_SCRIPT_KEY = "VIMPDB_VIMSCRIPT"
ENVIRON_SERVER_NAME_KEY = "VIMPDB_SERVERNAME"


def has_environ():
    return (ENVIRON_SERVER_NAME_KEY in os.environ) or (
        ENVIRON_SERVER_NAME_KEY in os.environ)


def read_from_environ(klass, default):
    script = os.environ.get(ENVIRON_SCRIPT_KEY, default.vim_client_script)
    server_name = os.environ.get(ENVIRON_SERVER_NAME_KEY, default.server_name)
    config = klass(script, script, server_name, default.port)
    return config

########NEW FILE########
__FILENAME__ = config
import sys
import os
import os.path
import logging
import time
import ConfigParser
import subprocess

from vimpdb import bbbconfig
from vimpdb import errors

RCNAME = os.path.expanduser('~/.vimpdbrc')

CLIENT = 'CLIENT'
SERVER = 'SERVER'


logger = logging.getLogger('vimpdb')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(name)s - %(levelname)s - \
%(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def get_package_path(instance):
    module = sys.modules[instance.__module__]
    return os.path.dirname(module.__file__)


class Config(object):

    def __init__(self, vim_client_script, vim_server_script, server_name,
        port, loglevel=logging.INFO):
        self.scripts = dict()
        self.vim_client_script = self.scripts[CLIENT] = vim_client_script
        self.vim_server_script = self.scripts[SERVER] = vim_server_script
        self.server_name = server_name
        self.port = port
        self.loglevel = loglevel

    def __repr__(self):
        return ("<vimpdb Config : Script %s; Server name %s, Port %s>" %
          (self.scripts[CLIENT], self.server_name, self.port))

    def __eq__(self, other):
        return (
            self.scripts[CLIENT] == other.scripts[CLIENT] and
            self.scripts[SERVER] == other.scripts[SERVER] and
            self.server_name == other.server_name and
            self.port == other.port)

if sys.platform == 'darwin':
    DEFAULT_CLIENT_SCRIPT = 'mvim'
    DEFAULT_SERVER_SCRIPT = DEFAULT_CLIENT_SCRIPT
    DEFAULT_SERVER_NAME = "VIM"
elif sys.platform == 'win32':
    DEFAULT_CLIENT_SCRIPT = 'vim.exe'
    DEFAULT_SERVER_SCRIPT = 'gvim.exe'
    DEFAULT_SERVER_NAME = "VIM"
else:
    DEFAULT_CLIENT_SCRIPT = 'vim'
    DEFAULT_SERVER_SCRIPT = 'gvim'
    DEFAULT_SERVER_NAME = "GVIM"

DEFAULT_PORT = 6666


defaultConfig = Config(DEFAULT_CLIENT_SCRIPT, DEFAULT_SERVER_SCRIPT,
            DEFAULT_SERVER_NAME, DEFAULT_PORT)
defaultConfig.vim_client_script = defaultConfig.scripts[CLIENT]


def get_configuration(filename=RCNAME):
    if not os.path.exists(filename):
        mustCheck = True
        mustWrite = True
        if bbbconfig.has_environ():
            config = bbbconfig.read_from_environ(Config, defaultConfig)
        else:
            config = defaultConfig
    else:
        mustCheck = False
        mustWrite = False
        try:
            config = read_from_file(filename, Config)
        except errors.BadRCFile, e:
            try:
                config_4_0 = bbbconfig.read_from_file_4_0(filename, Config)
            except errors.BadRCFile:
                raise e
            config = config_4_0
            mustCheck = True
    initial = config
    if mustCheck:
        config = Detector(config).checkConfiguration()
    if mustWrite or initial != config:
        write_to_file(filename, config)
    Detector(config).check_serverlist()
    logger.setLevel(config.loglevel)
    return config


def getRawConfiguration(filename=RCNAME):
    return read_from_file(filename, Config)


def read_from_file(filename, klass):
    parser = ConfigParser.RawConfigParser()
    parser.read(filename)
    if not parser.has_section('vimpdb'):
        raise errors.BadRCFile('[vimpdb] section is missing in "%s"' %
            filename)
    error_msg = ("'%s' option is missing from section [vimpdb] in "
        + "'" + filename + "'.")
    vim_client_script = read_option(parser, 'vim_client_script', error_msg)
    vim_server_script = read_option(parser, 'vim_server_script', error_msg)
    server_name = read_option(parser, 'server_name', error_msg)
    port = int(read_option(parser, 'port', error_msg))
    loglevel = logging.INFO
    if parser.has_option('vimpdb', 'loglevel'):
        loglevel = parser.get('vimpdb', 'loglevel')
        if loglevel == 'DEBUG':
            loglevel = logging.DEBUG
    return klass(vim_client_script, vim_server_script, server_name, port,
        loglevel)


def read_option(parser, name, error_msg):
    if parser.has_option('vimpdb', name):
        return parser.get('vimpdb', name)
    else:
        raise errors.BadRCFile(error_msg % name)


def write_to_file(filename, config):
    parser = ConfigParser.RawConfigParser()
    parser.add_section('vimpdb')
    parser.set('vimpdb', 'vim_client_script', config.scripts[CLIENT])
    parser.set('vimpdb', 'vim_server_script', config.scripts[SERVER])
    parser.set('vimpdb', 'server_name', config.server_name)
    parser.set('vimpdb', 'port', config.port)
    rcfile = open(filename, 'w')
    parser.write(rcfile)
    rcfile.close()


def getCommandOutputPosix(parts):
    try:
        p = subprocess.Popen(parts, stdout=subprocess.PIPE)
        return_code = p.wait()
    except OSError, e:
        message = 'When trying to run "%s" : %s' % (" ".join(parts), e.args[1])
        raise OSError(e.args[0], message)
    if return_code:
        raise errors.ReturnCodeError(return_code, " ".join(parts))
    child_stdout = p.stdout
    output = child_stdout.read()
    return output.strip()


NO_SERVER_SUPPORT = ("'%s' launches a VIM instance without "
    "clientserver support.")
NO_PYTHON_SUPPORT = "'%s' launches a VIM instance without python support."
NO_PYTHON_IN_VERSION = ("Calling --version returned no information "
    "about python support:\n %s")
NO_CLIENTSERVER_IN_VERSION = ("Calling --version returned no information "
    "about clientserver support:\n %s")
RETURN_CODE = "'%s' returned exit code '%d'."


class DetectorBase(object):

    MAX_TIMEOUT = 5

    def __init__(self, config, commandParser):
        self.scripts = dict()
        self.scripts[CLIENT] = config.scripts[CLIENT]
        self.scripts[SERVER] = config.scripts[SERVER]
        self.server_name = config.server_name
        self.port = config.port
        self.loglevel = config.loglevel
        self.commandParser = commandParser

    def checkConfiguration(self):
        while not self._checkConfiguration():
            pass
        return self

    def _checkConfiguration(self):
        try:
            self.check_clientserver_support(CLIENT)
        except ValueError, e:
            print e.args[0]
            self.query_script(CLIENT)
            return False
        try:
            self.check_python_support()
        #XXX catch WindowsError
        except OSError, e:
            print e.args[1]
            server_script = self.scripts[SERVER]
            if server_script == DEFAULT_SERVER_SCRIPT:
                print ("with the default VIM server script (%s)."
                    % server_script)
            else:
                print ("with the VIM server script from the configuration "
                    "(%s)." % server_script)
            self.query_script(SERVER)
            return False
        except ValueError, e:
            print e.args[0]
            self.query_script(SERVER)
            return False
        try:
            self.check_server_clientserver_support()
        except ValueError, e:
            print e.args[0]
            self.query_script(SERVER)
            return False
        try:
            self.check_serverlist()
        except ValueError, e:
            print e.args[0]
            self.query_servername()
            return False
        return True

    def launch_vim_server(self):
        raise NotImplemented

    def build_command(self, script_type, *args):
        script = self.scripts[script_type]
        command = script.split()
        command.extend(args)
        return command

    def get_serverlist(self):
        command = self.build_command(CLIENT, '--serverlist')
        try:
            return self.commandParser(command)
        except errors.ReturnCodeError, e:
            return_code = e.args[0]
            command = e.args[1]
            raise ValueError(RETURN_CODE % (command, return_code))
        except OSError, e:
            raise ValueError(str(e))

    def serverAvailable(self):
        serverlist = self.get_serverlist()
        servers = serverlist.lower().splitlines()
        server_name = self.server_name.lower()
        for server in servers:
            if server_name == server:
                return True
        return False

    def check_serverlist(self):
        if not self.serverAvailable():
            try:
                self.launch_vim_server()
            except errors.ReturnCodeError, e:
                return_code = e.args[0]
                command = e.args[1]
                raise ValueError(RETURN_CODE % (command, return_code))
            except OSError, e:
                raise ValueError(str(e))
        timeout = 0.0
        INCREMENT = 0.1
        while timeout < self.MAX_TIMEOUT:
            if self.serverAvailable():
                break
            time.sleep(INCREMENT)
            timeout += INCREMENT
        else:
            serverlist = self.get_serverlist()
            if not self.serverAvailable():
                msg = "'%s' server name not available in server list:\n%s"
                raise ValueError(msg % (self.server_name, serverlist))
        return True

    def get_vim_version(self, script_type):
        try:
            command = self.build_command(script_type, '--version')
            return self.commandParser(command)
        except errors.ReturnCodeError, e:
            return_code = e.args[0]
            command = e.args[1]
            raise ValueError(RETURN_CODE % (command, return_code))
        except OSError, e:
            raise ValueError(str(e))

    def check_clientserver_support(self, script_type):
        version = self.get_vim_version(script_type)
        if '+clientserver' in version:
            return True
        elif '-clientserver' in version:
            raise ValueError(NO_SERVER_SUPPORT % self.scripts[script_type])
        else:
            raise ValueError(NO_CLIENTSERVER_IN_VERSION % version)

    def check_server_clientserver_support(self):
        raise NotImplemented

    def check_python_support(self):
        raise NotImplemented

    def query_script(self, script_type):
        if script_type == CLIENT:
            type = 'client'
        else:
            type = 'server'
        question = ("Input another VIM %s script (leave empty to abort): "
            % type)
        answer = raw_input(question)
        if answer == '':
            raise errors.BrokenConfiguration
        else:
            self.scripts[script_type] = answer

    def query_servername(self):
        question = "Input another server name (leave empty to abort): "
        answer = raw_input(question)
        if answer == '':
            raise errors.BrokenConfiguration
        else:
            self.server_name = answer

if sys.platform == 'win32':

    def getCommandOutputWindows(parts):
        try:
            return getCommandOutputPosix(parts)
        except WindowsError:
            raise errors.ReturnCodeError(1, " ".join(parts))

    class Detector(DetectorBase):

        def __init__(self, config, commandParser=getCommandOutputWindows):
            return super(Detector, self).__init__(config, commandParser)

        def check_python_support(self):
            command = self.build_command(SERVER, 'dummy.txt',
                '+exe \'if has("python") | :q | else | :cq | endif\'')
            return_code = subprocess.call(command)
            if return_code:
                raise ValueError(NO_PYTHON_SUPPORT % self.scripts[SERVER])
            else:
                return True

        def check_server_clientserver_support(self):
            command = self.build_command(SERVER, 'dummy.txt',
                '+exe \'if has("clientserver") | :q | else | :cq | endif\'')
            return_code = subprocess.call(command)
            if return_code:
                raise ValueError(NO_SERVER_SUPPORT % self.scripts[SERVER])
            else:
                return True

        def launch_vim_server(self):
            command = self.build_command(SERVER, '--servername',
                self.server_name)
            subprocess.Popen(command)
            return True

else:

    class Detector(DetectorBase):

        def __init__(self, config, commandParser=getCommandOutputPosix):
            return super(Detector, self).__init__(config, commandParser)

        def check_python_support(self):
            version = self.get_vim_version(SERVER)
            if '+python' in version:
                return True
            elif '-python' in version:
                raise ValueError(NO_PYTHON_SUPPORT % self.scripts[SERVER])
            else:
                raise ValueError(NO_PYTHON_IN_VERSION % version)

        def check_server_clientserver_support(self):
            return self.check_clientserver_support(SERVER)

        def launch_vim_server(self):
            command = self.build_command(SERVER, '--servername',
                self.server_name)
            return_code = subprocess.call(command)
            if return_code:
                raise errors.ReturnCodeError(return_code, " ".join(command))
            return True

########NEW FILE########
__FILENAME__ = controller
import socket
import vim_bridge

from vimpdb import config

# after call of initialize function,
# pointer to vim module
# instead of importing vim module
vim = None

# after call of initialize function,
# holds a Controller instance
controller = None


def initialize(module):
    global vim
    global controller
    vim = module
    controller = Controller()


def buffer_create():
    source_buffer = vim.current.buffer.name
    vim.command('silent rightbelow 5new -vimpdb-')
    vim.command('set buftype=nofile')
    vim.command('set noswapfile')
    vim.command('set nonumber')
    vim.command('set nowrap')
    buffer = vim.current.buffer
    while True:
        vim.command('wincmd w')  # switch back window
        if source_buffer == vim.current.buffer.name:
            break
    return buffer


def buffer_find():
    for win in vim.windows:
        try:  # FIXME: Error while new a unnamed buffer
            if '-vimpdb-' in win.buffer.name:
                return win.buffer
        except:
            pass
    return None


@vim_bridge.bridged
def _PDB_buffer_write(message):
    pdb_buffer = buffer_find()
    if pdb_buffer is None:
        pdb_buffer = buffer_create()

    pdb_buffer[:] = None

    for line in message:
        pdb_buffer.append(line)
    del pdb_buffer[0]


@vim_bridge.bridged
def _PDB_buffer_close():
    vim.command('silent! bwipeout -vimpdb-')


def watch_create():
    source_buffer = vim.current.buffer.name
    vim.command('silent rightbelow 40vnew -watch-')
    vim.command('set buftype=nofile')
    vim.command('set noswapfile')
    vim.command('set nonumber')
    vim.command('set nowrap')
    buffer = vim.current.buffer
    while True:
        vim.command('wincmd w')   # switch back window
        if source_buffer == vim.current.buffer.name:
            break
    return buffer


def watch_find():
    for win in vim.windows:
        try:   # FIXME: Error while new a unnamed buffer
            if '-watch-' in win.buffer.name:
                return win.buffer
        except:
            pass
    return None


def watch_get():
    watch_buffer = watch_find()
    if watch_buffer is None:
        watch_buffer = watch_create()
    return watch_buffer


@vim_bridge.bridged
def _PDB_watch_reset():
    watch_buffer = watch_get()
    watch_buffer[:] = None


@vim_bridge.bridged
def _PDB_watch_write(message):
    watch_buffer = watch_get()

    for line in message:
        watch_buffer.append(line)
    if watch_buffer[0].strip() == '':
        del watch_buffer[0]


@vim_bridge.bridged
def _PDB_watch_close():
    vim.command('silent! bwipeout -watch-')


# socket management
class Controller(object):

    def __init__(self):
        configuration = config.getRawConfiguration()
        self.port = configuration.port
        self.host = '127.0.0.1'
        self.socket = None

    def init_socket(self):
        if self.socket is None:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
                socket.IPPROTO_UDP)

    def socket_send(self, message):
        self.init_socket()
        self.socket.sendto(message, (self.host, self.port))

    def socket_close(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None


@vim_bridge.bridged
def PDB_send_command(message):
    controller.socket_send(message)


@vim_bridge.bridged
def _PDB_socket_close():
    controller.socket_close()

########NEW FILE########
__FILENAME__ = debugger
import pdb
from pdb import Pdb
import sys
import StringIO
import pprint
from vimpdb import proxy
from vimpdb import config

PYTHON_25_OR_BIGGER = sys.version_info >= (2, 5)
PYTHON_26_OR_BIGGER = sys.version_info >= (2, 6)


def capture_sys_stdout(method):

    def decorated(self, line):
        self.capture_sys_stdout()
        result = method(self, line)
        self.stop_capture_sys_stdout()
        self.to_vim.showFeedback(self.pop_output())
        return result

    return decorated


def capture_self_stdout(method):

    def decorated(self, line):
        self.capture_self_stdout()
        result = method(self, line)
        self.stop_capture_self_stdout()
        self.to_vim.showFeedback(self.pop_output())
        return result

    return decorated


if PYTHON_25_OR_BIGGER:
    capture = capture_self_stdout
else:
    capture = capture_sys_stdout


def show_line(method):

    def decorated(self, line):
        result = method(self, line)
        self.showFileAtLine()
        return result

    return decorated


def close_socket(method):

    def decorated(self, line):
        self.from_vim.closeSocket()
        return method(self, line)

    return decorated


class Switcher:
    """
    Helper for switching from pdb to vimpdb
    and vice versa
    """

    def set_trace_without_step(self, frame):
        self.reset()
        while frame:
            frame.f_trace = self.trace_dispatch
            self.botframe = frame
            frame = frame.f_back
        sys.settrace(self.trace_dispatch)

    def update_state(self, other):
        self.stack = other.stack
        self.curindex = other.curindex
        self.curframe = other.curframe

    def has_gone_up(self):
        return self.curindex + 1 != len(self.stack)


class VimPdb(Pdb, Switcher):
    """
    debugger integrated with Vim
    """

    def __init__(self, to_vim, from_vim):
        Pdb.__init__(self)
        self.capturing = False
        self.to_vim = to_vim
        self.from_vim = from_vim
        self._textOutput = ''

    def trace_dispatch(self, frame, event, arg):
        """allow to switch to Pdb instance"""
        if hasattr(self, 'pdb'):
            return self.pdb.trace_dispatch(frame, event, arg)
        else:
            return Pdb.trace_dispatch(self, frame, event, arg)

    def execRcLines(self):
        pass

    def cmdloop(self):
        stop = None
        self.preloop()
        while not stop:
            line = self.from_vim.waitFor(self)
            line = self.precmd(line)
            stop = self.onecmd(line)
            stop = self.postcmd(stop, line)
        self.postloop()

    def preloop(self):
        self.showFileAtLine()

    def getFileAndLine(self):
        frame, lineno = self.stack[self.curindex]
        filename = self.canonic(frame.f_code.co_filename)
        return filename, lineno

    def showFileAtLine(self):
        filename, lineno = self.getFileAndLine()
        self.to_vim.showFileAtLine(filename, lineno)
        watches = self.formatLocals()
        self.to_vim.displayLocals(watches)

    def formatLocals(self):
        stream = StringIO.StringIO()
        locals = self.curframe.f_locals
        keys = locals.keys()
        keys.sort()
        for key in keys:
            stream.write('%s = \n' % key)
            formatted_value = pprint.pformat(locals[key], width=36)
            for line in formatted_value.splitlines():
                stream.write('    %s\n' % line)
        watches = stream.getvalue()
        stream.close()
        return watches

    # stdout captures to send back to Vim
    def capture_sys_stdout(self):
        self.stdout = sys.stdout
        sys.stdout = StringIO.StringIO()
        self.capturing = True

    def stop_capture_sys_stdout(self):
        if self.capturing:
            self.capturing = False
            self.push_output(sys.stdout.getvalue())
            sys.stdout = self.stdout

    # stdout captures to send back to Vim
    def capture_self_stdout(self):
        self.initial_stdout = self.stdout
        self.stdout = StringIO.StringIO()
        self.capturing = True

    def stop_capture_self_stdout(self):
        if self.capturing:
            self.capturing = False
            self.push_output(self.stdout.getvalue())
            self.stdout = self.initial_stdout

    def push_output(self, text):
        self._textOutput += text

    def pop_output(self):
        result = self._textOutput
        self._textOutput = ''
        return result

    def do_pdb(self, line):
        """
        'pdb' command:
        switches back to debugging with (almost) standard pdb.Pdb
        except for added 'vim' command.
        """
        self.from_vim.closeSocket()
        self.pdb = get_hooked_pdb()
        self.pdb.set_trace_without_step(self.botframe)
        if self.has_gone_up():
            self.pdb.update_state(self)
            self.pdb.print_current_stack_entry()
            self.pdb.cmdloop()
        else:
            self.pdb.interaction(self.curframe, None)
        return 1

    do_u = do_up = capture(show_line(Pdb.do_up))
    do_d = do_down = capture(show_line(Pdb.do_down))
    do_a = do_args = capture(Pdb.do_args)
    do_b = do_break = capture(Pdb.do_break)
    do_cl = do_clear = capture(Pdb.do_clear)
    do_c = do_continue = close_socket(Pdb.do_continue)

    @capture
    def print_stack_entry(self, frame_lineno, prompt_prefix=pdb.line_prefix):
        return Pdb.print_stack_entry(self, frame_lineno, prompt_prefix)

    def default(self, line):
        # first char should not be output (it is the '!' needed to escape)
        self.push_output(line[1:] + " = ")
        return Pdb.default(self, line)

if PYTHON_26_OR_BIGGER:
    VimPdb.default = capture_self_stdout(VimPdb.default)
else:
    VimPdb.default = capture_sys_stdout(VimPdb.default)


def make_instance():
    configuration = config.get_configuration()
    communicator = proxy.Communicator(configuration.vim_client_script,
        configuration.server_name)
    to_vim = proxy.ProxyToVim(communicator)
    from_vim = proxy.ProxyFromVim(configuration.port)
    return VimPdb(to_vim, from_vim)


def set_trace():
    """
    can be called like pdb.set_trace()
    """
    instance = make_instance()
    instance.set_trace(sys._getframe().f_back)


# hook vimpdb  #
################


def trace_dispatch(self, frame, event, arg):
    """allow to switch to Vimpdb instance"""
    if hasattr(self, 'vimpdb'):
        return self.vimpdb.trace_dispatch(frame, event, arg)
    else:
        return self._orig_trace_dispatch(frame, event, arg)


class SwitcherToVimpdb(Switcher):
    """
    with vim command
    """

    def do_vim(self, arg):
        """v(im)
    switch to debugging with vimpdb"""
        self.vimpdb = make_instance()
        self.vimpdb.set_trace_without_step(self.botframe)
        if self.has_gone_up():
            self.vimpdb.update_state(self)
            self.vimpdb.cmdloop()
        else:
            self.vimpdb.interaction(self.curframe, None)
        return 1

    do_v = do_vim

    def print_current_stack_entry(self):
        self.print_stack_entry(self.stack[self.curindex])


def setupMethod(klass, method):
    name = method.__name__
    orig = getattr(klass, name)
    orig_attr = '_orig_' + name
    if not hasattr(klass, orig_attr):
        setattr(klass, '_orig_' + name, orig)
        setattr(klass, name, method)


def hook(klass):
    """
    monkey-patch pdb.Pdb class

    adds a 'vim' (and 'v') command:
    it switches to debugging with vimpdb
    """

    if not hasattr(klass, 'do_vim'):
        setupMethod(klass, trace_dispatch)
        klass.__bases__ += (SwitcherToVimpdb, )


def get_hooked_pdb():
    hook(Pdb)
    debugger = Pdb()
    return debugger

########NEW FILE########
__FILENAME__ = errors
class BadRCFile(Exception):
    pass


class ReturnCodeError(Exception):
    pass


class BrokenConfiguration(Exception):
    pass


class RemoteUnavailable(Exception):
    pass

########NEW FILE########
__FILENAME__ = proxy
import os
import socket
import subprocess

from vimpdb import config
from vimpdb import errors


def get_eggs_paths():
    import vim_bridge
    vimpdb_path = config.get_package_path(errors.ReturnCodeError())
    vim_bridge_path = config.get_package_path(vim_bridge.bridged)
    return (
        os.path.dirname(vimpdb_path),
        os.path.dirname(vim_bridge_path),
        )


class Communicator(object):

    def __init__(self, script, server_name):
        self.script = script
        self.server_name = server_name

    def prepare_subprocess(self, *args):
        parts = self.script.split()
        parts.extend(args)
        return parts

    def _remote_expr(self, expr):
        parts = self.prepare_subprocess('--servername',
                   self.server_name, "--remote-expr", expr)
        p = subprocess.Popen(parts, stdout=subprocess.PIPE)
        return_code = p.wait()
        if return_code:
            raise errors.RemoteUnavailable()
        child_stdout = p.stdout
        output = child_stdout.read()
        return output.strip()

    def _send(self, command):
        # add ':<BS>' to hide last keys sent in VIM command-line
        command = ''.join((command, ':<BS>'))
        parts = self.prepare_subprocess('--servername',
                   self.server_name, "--remote-send", command)
        return_code = subprocess.call(parts)
        if return_code:
            raise errors.RemoteUnavailable()


class ProxyToVim(object):
    """
    use subprocess to launch Vim instance that use clientserver mode
    to communicate with Vim instance used for debugging.
    """

    def __init__(self, communicator):
        self.communicator = communicator

    def _send(self, command):
        self.communicator._send(command)
        config.logger.debug("sent: %s" % command)

    def _remote_expr(self, expr):
        return self.communicator._remote_expr(expr)

    def setupRemote(self):
        if not self.isRemoteSetup():
            # source vimpdb.vim
            proxy_package_path = config.get_package_path(self)
            filename = os.path.join(proxy_package_path, "vimpdb.vim")
            command = "<C-\><C-N>:source %s<CR>" % filename
            self._send(command)
            for egg_path in get_eggs_paths():
                self._send(':call PDB_setup_egg(%s)<CR>' % repr(egg_path))
            self._send(':call PDB_init_controller()')

    def isRemoteSetup(self):
        status = self._expr("exists('*PDB_setup_egg')")
        return status == '1'

    def showFeedback(self, feedback):
        if not feedback:
            return
        feedback_list = feedback.splitlines()
        self.setupRemote()
        self._send(':call PDB_show_feedback(%s)<CR>' % repr(feedback_list))

    def displayLocals(self, feedback):
        if not feedback:
            return
        feedback_list = feedback.splitlines()
        self.setupRemote()
        self._send(':call PDB_reset_watch()<CR>')
        for line in feedback_list:
            self._send(':call PDB_append_watch([%s])<CR>' % repr(line))

    def showFileAtLine(self, filename, lineno):
        if os.path.exists(filename):
            self._showFileAtLine(filename, lineno)

    def _showFileAtLine(self, filename, lineno):
        # Windows compatibility:
        # Windows command-line does not play well with backslash in filename.
        # So turn backslash to slash; Vim knows how to translate them back.
        filename = filename.replace('\\', '/')
        self.setupRemote()
        self._send(':call PDB_show_file_at_line("%s", "%d")<CR>'
            % (filename, lineno))

    def _expr(self, expr):
        config.logger.debug("expr: %s" % expr)
        result = self._remote_expr(expr)
        config.logger.debug("result: %s" % result)
        return result

    # code leftover from hacking
    # def getText(self, prompt):
    #     self.setupRemote()
    #     command = self._expr('PDB_get_command("%s")' % prompt)
    #     return command


class ProxyFromVim(object):

    BUFLEN = 512

    socket_factory = socket.socket

    def __init__(self, port):
        self.socket_inactive = True
        self.port = port

    def bindSocket(self):
        if self.socket_inactive:
            self.socket = self.socket_factory(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.socket.bind(('', self.port))
            self.socket_inactive = False

    def closeSocket(self):
        if not self.socket_inactive:
            self.socket.close()
            self.socket_inactive = True

    def waitFor(self, pdb):
        self.bindSocket()
        (message, address) = self.socket.recvfrom(self.BUFLEN)
        config.logger.debug("command: %s" % message)
        return message


# code leftover from hacking
# def eat_stdin(self):
#     sys.stdout.write('-- Type Ctrl-D to continue --\n')
#     sys.stdout.flush()
#     sys.stdin.readlines()

########NEW FILE########
__FILENAME__ = communicator
import optparse
import sys
parser = optparse.OptionParser()
parser.add_option('--servername', dest="server_name")
parser.add_option('--remote-expr', dest="expr")
parser.add_option('--remote-send', dest="command")


parser.parse_args(sys.argv)

if hasattr(parser.values, 'expr'):
    print parser.values.expr, parser.values.server_name
if hasattr(parser.values, 'command'):
    print parser.values.command, parser.values.server_name

########NEW FILE########
__FILENAME__ = compatiblevim
print "+clientserver +python"

########NEW FILE########
__FILENAME__ = emptyserverlist
print

########NEW FILE########
__FILENAME__ = incompatiblevim
print "-clientserver -python"

########NEW FILE########
__FILENAME__ = nopython
print "+clientserver -python"

########NEW FILE########
__FILENAME__ = noserver
print "-clientserver +python"

########NEW FILE########
__FILENAME__ = returncode
import sys
sys.exit(1)

########NEW FILE########
__FILENAME__ = rightserverlist
print "VIM"

########NEW FILE########
__FILENAME__ = wrongserverlist
print "WRONG"

########NEW FILE########
__FILENAME__ = test_config
import os
import sys
import py


def test_read_options():
    import tempfile
    from vimpdb.config import CLIENT
    from vimpdb.config import SERVER
    handle, name = tempfile.mkstemp()
    file = open(name, 'w')
    file.write("""
[vimpdb]
vim_client_script = vim_client_script
vim_server_script = vim_server_script
port = 1000
server_name = server_name
""")
    file.close()
    from vimpdb.config import read_from_file
    from vimpdb.config import Config
    configuration = read_from_file(name, Config)
    assert configuration.port == 1000
    assert configuration.scripts[CLIENT] == 'vim_client_script'
    assert configuration.scripts[SERVER] == 'vim_server_script'
    assert configuration.server_name == 'server_name'
    os.remove(name)


def test_read_options_legacy_script():
    import tempfile
    from vimpdb.config import CLIENT
    from vimpdb.config import SERVER
    handle, name = tempfile.mkstemp()
    file = open(name, 'w')
    file.write("""
[vimpdb]
script = vim_client_script
port = 1000
server_name = server_name
""")
    file.close()
    from vimpdb.bbbconfig import read_from_file_4_0
    from vimpdb.config import Config
    configuration = read_from_file_4_0(name, Config)
    assert configuration.port == 1000
    assert configuration.scripts[CLIENT] == 'vim_client_script'
    assert configuration.scripts[SERVER] == 'vim_client_script'
    assert configuration.server_name == 'server_name'
    os.remove(name)


def test_no_vimpdb_section():
    import tempfile
    handle, name = tempfile.mkstemp()
    file = open(name, 'w')
    file.write("""
[vimpdbx]
vim_client_script = vim_client_script
port = 1000
server_name = server_name
""")
    file.close()
    from vimpdb.errors import BadRCFile
    from vimpdb.config import read_from_file
    from vimpdb.config import Config
    py.test.raises(BadRCFile, read_from_file, name, Config)
    os.remove(name)


def test_missing_client_script_option():
    import tempfile
    handle, name = tempfile.mkstemp()
    file = open(name, 'w')
    file.write("""
[vimpdb]
vim_server_script = vim_server_script
port = 1000
server_name = server_name
""")
    file.close()
    from vimpdb.errors import BadRCFile
    from vimpdb.config import read_from_file
    from vimpdb.config import Config
    py.test.raises(BadRCFile, read_from_file, name, Config)
    os.remove(name)


def test_missing_server_script_option():
    import tempfile
    handle, name = tempfile.mkstemp()
    file = open(name, 'w')
    file.write("""
[vimpdb]
vim_client_script = vim_client_script
port = 1000
server_name = server_name
""")
    file.close()
    from vimpdb.errors import BadRCFile
    from vimpdb.config import read_from_file
    from vimpdb.config import Config
    py.test.raises(BadRCFile, read_from_file, name, Config)
    os.remove(name)


def test_missing_port_option():
    import tempfile
    handle, name = tempfile.mkstemp()
    file = open(name, 'w')
    file.write("""
[vimpdb]
vim_client_script = vim_client_script
portx = 1000
server_name = server_name
""")
    file.close()
    from vimpdb.errors import BadRCFile
    from vimpdb.config import read_from_file
    from vimpdb.config import Config
    py.test.raises(BadRCFile, read_from_file, name, Config)
    os.remove(name)


def test_missing_server_name_option():
    import tempfile
    handle, name = tempfile.mkstemp()
    file = open(name, 'w')
    file.write("""
[vimpdb]
vim_client_script = vim_client_script
port = 1000
server_namex = server_name
""")
    file.close()
    from vimpdb.errors import BadRCFile
    from vimpdb.config import read_from_file
    from vimpdb.config import Config
    py.test.raises(BadRCFile, read_from_file, name, Config)
    os.remove(name)


def test_default_config():
    from vimpdb.config import CLIENT
    from vimpdb.config import SERVER
    from vimpdb.config import defaultConfig
    from vimpdb.config import DEFAULT_PORT
    from vimpdb.config import DEFAULT_CLIENT_SCRIPT
    from vimpdb.config import DEFAULT_SERVER_SCRIPT
    from vimpdb.config import DEFAULT_SERVER_NAME
    configuration = defaultConfig
    assert configuration.port == DEFAULT_PORT
    assert configuration.scripts[CLIENT] == DEFAULT_CLIENT_SCRIPT
    assert configuration.scripts[SERVER] == DEFAULT_SERVER_SCRIPT
    assert configuration.server_name == DEFAULT_SERVER_NAME


def test_file_creation():
    import tempfile
    handle, name = tempfile.mkstemp()
    os.remove(name)
    from vimpdb.config import defaultConfig
    from vimpdb.config import DEFAULT_PORT
    from vimpdb.config import DEFAULT_CLIENT_SCRIPT
    from vimpdb.config import DEFAULT_SERVER_SCRIPT
    from vimpdb.config import DEFAULT_SERVER_NAME
    from vimpdb.config import write_to_file
    write_to_file(name, defaultConfig)
    assert os.path.exists(name)
    config_file = open(name)
    content = config_file.read()
    assert 'vim_client_script =' in content
    assert DEFAULT_CLIENT_SCRIPT in content
    assert 'vim_server_script =' in content
    assert DEFAULT_SERVER_SCRIPT in content
    assert 'port =' in content
    assert str(DEFAULT_PORT) in content
    assert 'server_name =' in content
    assert DEFAULT_SERVER_NAME in content
    config_file.close()
    os.remove(name)


def build_script(script):
    """make path to scripts used by tests
    """

    from vimpdb.config import get_package_path
    tests_path = get_package_path(build_script)
    script_path = sys.executable + " " + os.path.sep.join([tests_path,
        'scripts', script])
    return script_path


def test_detector_instantiation():
    from vimpdb.config import Detector
    from vimpdb.config import SERVER
    from vimpdb.config import CLIENT
    from vimpdb.config import Config
    configuration = Config('vim_client_script', 'vim_server_script',
        'server_name', 6666)
    detector = Detector(configuration)
    assert detector.port == configuration.port
    assert detector.scripts[CLIENT] == configuration.scripts[CLIENT]
    assert detector.scripts[SERVER] == configuration.scripts[SERVER]
    assert detector.server_name == configuration.server_name


def test_detector_build_command():
    from vimpdb.config import Detector
    from vimpdb.config import CLIENT
    from vimpdb.config import Config
    configuration = Config('vim_client_script', 'vim_server_script',
        'server_name', 6666)
    detector = Detector(configuration)
    result = detector.build_command(CLIENT, "test")
    assert result[-1] == "test"
    assert result[0:-1] == configuration.scripts[CLIENT].split()


def test_detect_compatible():
    from vimpdb import config

    vim_client_script = build_script("compatiblevim.py")
    vim_server_script = build_script("compatiblevim.py")
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    detector.check_clientserver_support(config.SERVER)
    detector.check_clientserver_support(config.CLIENT)
    detector.check_python_support()


def test_detect_incompatible():
    from vimpdb import config

    vim_client_script = "dummy"
    vim_server_script = build_script("incompatiblevim.py")
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    py.test.raises(ValueError, detector.check_clientserver_support,
        config.SERVER)
    py.test.raises(ValueError, detector.check_python_support)


def test_detect_rightserverlist():
    from vimpdb import config

    vim_client_script = build_script("rightserverlist.py")
    vim_server_script = "dummy"
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    assert 'VIM' in detector.get_serverlist()
    detector.check_serverlist()


def test_detect_wrongserverlist():
    from vimpdb import config

    vim_client_script = build_script("wrongserverlist.py")
    vim_server_script = "dummy"
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    assert 'WRONG' in detector.get_serverlist()
    py.test.raises(ValueError, detector.check_serverlist)


def test_detector_get_vim_version_bad_script():
    from vimpdb import config

    vim_client_script = build_script("returncode.py")
    vim_server_script = "dummy"
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    info = py.test.raises(ValueError, detector.get_vim_version, config.CLIENT)
    assert (info.value.args[0].endswith(
        "returncode.py --version' returned exit code '1'."))


def test_detector_get_vim_version_good_script():
    from vimpdb import config

    vim_client_script = build_script("compatiblevim.py")
    vim_server_script = "dummy"
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    version = detector.get_vim_version(config.CLIENT)
    assert version == '+clientserver +python'


def test_detector_check_python_support():
    from vimpdb import config

    vim_client_script = "dummy"
    vim_server_script = build_script("compatiblevim.py")
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    assert detector.check_python_support()


def test_detector_no_python_support():
    from vimpdb import config

    vim_client_script = "dummy"
    vim_server_script = build_script("nopython.py")
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    info = py.test.raises(ValueError, detector.check_python_support)
    assert info.value.args[0].endswith(
        "' launches a VIM instance without python support.")


def test_detector_no_python_in_version():
    from vimpdb import config

    vim_client_script = "dummy"
    vim_server_script = build_script("rightserverlist.py")
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    info = py.test.raises(ValueError, detector.check_python_support)
    assert (info.value.args[0] ==
      'Calling --version returned no information about python support:\n VIM')


def test_detector_check_clientserver_support():
    from vimpdb import config

    vim_client_script = build_script("compatiblevim.py")
    vim_server_script = "dummy"
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    assert detector.check_clientserver_support(config.CLIENT)


def test_detector_no_clientserver_support():
    from vimpdb import config

    vim_client_script = build_script("noserver.py")
    vim_server_script = "dummy"
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    info = py.test.raises(ValueError, detector.check_clientserver_support,
        config.CLIENT)
    assert info.value.args[0].endswith(
        "' launches a VIM instance without clientserver support.")


def test_detector_no_clientserver_in_version():
    from vimpdb import config

    vim_client_script = build_script("rightserverlist.py")
    vim_server_script = "dummy"
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    info = py.test.raises(ValueError, detector.check_clientserver_support,
        config.CLIENT)
    assert (info.value.args[0] ==
        ('Calling --version returned no information about clientserver '
        'support:\n VIM'))


def test_detector_get_serverlist():
    from vimpdb import config

    vim_client_script = build_script("rightserverlist.py")
    vim_server_script = "dummy"
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    serverlist = detector.get_serverlist()
    assert serverlist == "VIM"


def test_detector_get_serverlist_bad_script():
    from vimpdb import config

    vim_client_script = build_script("returncode.py")
    vim_server_script = "dummy"
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    info = py.test.raises(ValueError, detector.get_serverlist)
    assert (info.value.args[0].endswith(
        "returncode.py --serverlist' returned exit code '1'."))


def test_detector_check_serverlist():
    from vimpdb import config

    vim_client_script = build_script("rightserverlist.py")
    vim_server_script = "dummy"
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    assert detector.check_serverlist()


def test_detector_check_serverlist_bad_server_script():
    from vimpdb import config

    vim_client_script = build_script("emptyserverlist.py")
    vim_server_script = build_script("returncode.py")
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    info = py.test.raises(ValueError, detector.check_serverlist)
    assert (info.value.args[0].endswith(
        "returncode.py --servername VIM' returned exit code '1'."))


def test_detector_server_not_available():
    from vimpdb import config

    vim_client_script = build_script("rightserverlist.py")
    vim_server_script = build_script("rightserverlist.py")
    server_name = 'SERVERNAME'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    detector.MAX_TIMEOUT = 0.5
    info = py.test.raises(ValueError, detector.check_serverlist)
    assert (info.value.args[0] ==
        "'SERVERNAME' server name not available in server list:\nVIM")


def test_detector_launch_server():
    from vimpdb import config

    vim_client_script = "dummy"
    vim_server_script = build_script("compatiblevim.py")
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    assert detector.launch_vim_server()


def test_detector_launch_server_bad_script():
    from vimpdb import errors
    from vimpdb import config

    vim_client_script = build_script("compatiblevim.py")
    vim_server_script = build_script("returncode.py")
    server_name = 'VIM'
    port = 6666

    configuration = config.Config(vim_client_script, vim_server_script,
        server_name, port)

    detector = config.Detector(configuration)
    detector.MAX_TIMEOUT = 0.5
    info = py.test.raises(errors.ReturnCodeError, detector.launch_vim_server)
    assert info.value.args[0] == 1
    assert info.value.args[1].endswith('returncode.py --servername VIM')


if __name__ == '__main__':
    test_detector_get_vim_version_good_script()

########NEW FILE########
__FILENAME__ = test_debugger
from mock import Mock
from mock import patch


def test_klass_after_setup_method():
    from vimpdb.debugger import setupMethod

    mocked_method = Mock(name='orig')

    class Klass:

        method = mocked_method

    new_method = Mock(name='new')
    new_method.__name__ = 'method'

    setupMethod(Klass, new_method)

    assert hasattr(Klass, '_orig_method')
    assert Klass._orig_method == mocked_method
    assert hasattr(Klass, 'method')
    assert Klass.method == new_method


def test_instance_of_klass_after_setup_method():
    from vimpdb.debugger import setupMethod

    mocked_method = Mock(name='orig')

    class Klass:

        method = mocked_method

    new_method = Mock(name='new')
    new_method.__name__ = 'method'

    setupMethod(Klass, new_method)
    instance = Klass()
    instance.method()

    assert new_method.called

    instance._orig_method()
    assert mocked_method.called


@patch('vimpdb.debugger.trace_dispatch')
def test_hook(mocked_trace_dispatch):
    from vimpdb.debugger import hook
    from vimpdb.debugger import SwitcherToVimpdb

    class Klass:

        def trace_dispatch(self):
            pass

    orig_trace_dispatch = Klass.trace_dispatch
    mocked_trace_dispatch.__name__ = 'trace_dispatch'

    hook(Klass)

    assert Klass._orig_trace_dispatch == orig_trace_dispatch
    assert SwitcherToVimpdb in Klass.__bases__
    assert Klass.trace_dispatch == mocked_trace_dispatch


@patch('vimpdb.debugger.setupMethod')
def test_hook_do_nothing(mocked_setupMethod):
    from vimpdb.debugger import hook
    from vimpdb.debugger import SwitcherToVimpdb

    class Klass:

        def do_vim(self):
            pass


    hook(Klass)

    assert not mocked_setupMethod.called
    assert SwitcherToVimpdb not in Klass.__bases__


@patch('vimpdb.debugger.trace_dispatch')
def test_get_hooked_pdb(mocked_trace_dispatch):
    from pdb import Pdb
    from vimpdb.debugger import get_hooked_pdb
    from vimpdb.debugger import SwitcherToVimpdb

    mocked_trace_dispatch.__name__ = 'trace_dispatch'

    debugger = get_hooked_pdb()

    assert isinstance(debugger, Pdb)
    assert isinstance(debugger, SwitcherToVimpdb)
    assert hasattr(debugger, 'do_vim')
    assert debugger.trace_dispatch == mocked_trace_dispatch


@patch('vimpdb.config.get_configuration')
def test_make_instance(mocked_get_configuration):
    from vimpdb.config import Config
    from vimpdb.debugger import make_instance
    from vimpdb.debugger import VimPdb

    mocked_get_configuration.return_value = Config(
        'client', 'server', 'name', 6666)

    instance = make_instance()

    assert isinstance(instance, VimPdb)
    assert instance.from_vim.port == 6666
    assert instance.to_vim.communicator.script == 'client'
    assert instance.to_vim.communicator.server_name == 'name'

########NEW FILE########
__FILENAME__ = test_proxy
import os
import sys
import py
from mock import Mock


def build_script(script):
    """make path to scripts used by tests
    """

    from vimpdb.config import get_package_path
    tests_path = get_package_path(build_script)
    script_path = sys.executable + " " + os.path.sep.join([tests_path,
        'scripts', script])
    return script_path


def test_Communicator_instantiation():
    from vimpdb.proxy import Communicator

    communicator = Communicator('script', 'server_name')

    assert communicator.script == 'script'
    assert communicator.server_name == 'server_name'


def test_Communicator_remote_expr_ok():
    from vimpdb.proxy import Communicator
    script = build_script("communicator.py")

    communicator = Communicator(script, 'server_name')
    result = communicator._remote_expr('expr')

    assert 'expr' in result
    assert 'server_name' in result


def test_Communicator_remote_expr_return_code():
    from vimpdb.proxy import Communicator
    from vimpdb.errors import RemoteUnavailable
    script = build_script("returncode.py")

    communicator = Communicator(script, 'server_name')
    py.test.raises(RemoteUnavailable, communicator._remote_expr, 'expr')


def test_Communicator_send_ok():
    from vimpdb.proxy import Communicator
    script = build_script("communicator.py")

    communicator = Communicator(script, 'server_name')
    communicator._send('command')


def test_Communicator_send_return_code():
    from vimpdb.proxy import Communicator
    from vimpdb.errors import RemoteUnavailable
    script = build_script("returncode.py")

    communicator = Communicator(script, 'server_name')
    py.test.raises(RemoteUnavailable, communicator._send, 'command')


def test_ProxyToVim_instantiation():
    from vimpdb.proxy import ProxyToVim

    communicator = Mock()

    to_vim = ProxyToVim(communicator)
    assert isinstance(to_vim, ProxyToVim)
    assert to_vim.communicator == communicator


def test_ProxyToVim_setupRemote():
    from vimpdb.proxy import ProxyToVim
    from vimpdb.proxy import Communicator

    communicator = Mock(spec=Communicator)
    communicator._remote_expr.return_value = '0'

    to_vim = ProxyToVim(communicator)
    to_vim.setupRemote()

    communicator._remote_expr.assert_called_with("exists('*PDB_setup_egg')")
    assert communicator._send.call_count == 4
    call_args_list = communicator._send.call_args_list
    call_args, call_kwargs = call_args_list[0]
    assert call_args[0].endswith('vimpdb/vimpdb.vim<CR>')
    call_args, call_kwargs = call_args_list[1]
    assert call_args[0].startswith(':call PDB_setup_egg(')
    call_args, call_kwargs = call_args_list[2]
    assert call_args[0].startswith(':call PDB_setup_egg(')
    call_args, call_kwargs = call_args_list[3]
    assert call_args[0].startswith(':call PDB_init_controller(')


def test_ProxyToVim_setupRemote_does_nothing():
    from vimpdb.proxy import ProxyToVim
    from vimpdb.proxy import Communicator

    communicator = Mock(spec=Communicator)
    communicator._remote_expr.return_value = '1'

    to_vim = ProxyToVim(communicator)
    to_vim.setupRemote()

    assert communicator._remote_expr.call_count == 1, (
        "_remote_expr not called")
    communicator._remote_expr.assert_called_with("exists('*PDB_setup_egg')")


def test_ProxyToVim_isRemoteSetup():
    from vimpdb.proxy import ProxyToVim
    from vimpdb.proxy import Communicator

    communicator = Mock(spec=Communicator)

    to_vim = ProxyToVim(communicator)
    to_vim.isRemoteSetup()

    assert communicator._remote_expr.call_count == 1
    communicator._remote_expr.assert_called_with("exists('*PDB_setup_egg')")


def test_ProxyToVim_showFeedback_empty():
    from vimpdb.proxy import ProxyToVim
    from vimpdb.proxy import Communicator

    communicator = Mock(spec=Communicator)

    to_vim = ProxyToVim(communicator)
    to_vim.showFeedback('')

    assert not communicator.called


def test_ProxyToVim_showFeedback_content():
    from vimpdb.proxy import ProxyToVim
    from vimpdb.proxy import Communicator

    communicator = Mock(spec=Communicator)
    communicator._remote_expr.return_value = '1'

    to_vim = ProxyToVim(communicator)
    to_vim.showFeedback('first\nsecond')

    assert communicator._remote_expr.call_count == 1
    communicator._remote_expr.assert_called_with("exists('*PDB_setup_egg')")
    assert communicator._send.call_count == 1
    communicator._send.assert_called_with(
        ":call PDB_show_feedback(['first', 'second'])<CR>")


def test_ProxyToVim_showFileAtLine_wrong_file():
    from vimpdb.proxy import ProxyToVim
    from vimpdb.proxy import Communicator

    communicator = Mock(spec=Communicator)
    communicator._remote_expr.return_value = '1'

    to_vim = ProxyToVim(communicator)
    to_vim.showFileAtLine('bla.vim', 1)

    assert not communicator.called


def test_ProxyToVim_showFileAtLine_existing_file():
    from vimpdb.proxy import ProxyToVim
    from vimpdb.proxy import Communicator
    from vimpdb.config import get_package_path

    existingFile = get_package_path(
        test_ProxyToVim_showFileAtLine_existing_file)

    communicator = Mock(spec=Communicator)
    communicator._remote_expr.return_value = '1'

    to_vim = ProxyToVim(communicator)
    to_vim.showFileAtLine(existingFile, 1)

    communicator._remote_expr.assert_called_with("exists('*PDB_setup_egg')")
    assert communicator._send.call_count == 1
    call_args, call_kwargs = communicator._send.call_args
    assert call_args[0].startswith(':call PDB_show_file_at_line("')
    assert call_args[0].endswith(' "1")<CR>')
    assert not '\\' in call_args[0]


def test_ProxyToVim_showFileAtLine_existing_file_windows():
    from vimpdb.proxy import ProxyToVim
    from vimpdb.proxy import Communicator
    from vimpdb.config import get_package_path

    existingFile = get_package_path(
        test_ProxyToVim_showFileAtLine_existing_file)
    existingFile = existingFile.replace(os.sep, '\\')

    communicator = Mock(spec=Communicator)
    communicator._remote_expr.return_value = '1'

    to_vim = ProxyToVim(communicator)
    to_vim._showFileAtLine(existingFile, 1)

    communicator._remote_expr.assert_called_with("exists('*PDB_setup_egg')")
    assert communicator._send.call_count == 1
    call_args, call_kwargs = communicator._send.call_args
    assert call_args[0].startswith(':call PDB_show_file_at_line("')
    assert call_args[0].endswith(' "1")<CR>')
    assert not '\\' in call_args[0]


def test_ProxyFromVim_instantiation():
    from vimpdb.proxy import ProxyFromVim
    from_vim = ProxyFromVim(6666)
    assert isinstance(from_vim, ProxyFromVim)
    assert from_vim.port == 6666
    assert from_vim.socket_inactive


def test_ProxyFromVim_bindSocket():
    from vimpdb.proxy import ProxyFromVim
    from_vim = ProxyFromVim(6666)

    from_vim.socket_factory = Mock()

    from_vim.bindSocket()

    assert not from_vim.socket_inactive
    assert from_vim.socket.bind.call_count == 1
    from_vim.socket.bind.assert_called_with(('', 6666))


def test_ProxyFromVim_bindSocket_active():
    from vimpdb.proxy import ProxyFromVim
    from_vim = ProxyFromVim(6666)

    from_vim.socket_factory = Mock()
    from_vim.socket_inactive = False

    from_vim.bindSocket()

    assert not from_vim.socket_factory.called


def test_ProxyFromVim_closeSocket():
    from vimpdb.proxy import ProxyFromVim
    from_vim = ProxyFromVim(6666)

    from_vim.socket = Mock()
    from_vim.socket_inactive = False

    from_vim.closeSocket()

    assert from_vim.socket_inactive
    assert from_vim.socket.close.call_count == 1
    from_vim.socket.close.assert_called_with()


def test_ProxyFromVim_closeSocket_inactive():
    from vimpdb.proxy import ProxyFromVim
    from_vim = ProxyFromVim(6666)

    from_vim.socket = Mock()

    from_vim.closeSocket()

    assert from_vim.socket_inactive
    assert not from_vim.socket.called


def test_ProxyFromVim_waitFor():
    from vimpdb.proxy import ProxyFromVim
    from socket import socket

    from_vim = ProxyFromVim(6666)

    mocked_socket = Mock(socket)
    mocked_socket.recvfrom.return_value = ('message', None)
    mocked_factory = Mock(return_value=mocked_socket)
    from_vim.socket_factory = mocked_factory

    message = from_vim.waitFor(None)

    assert message == 'message'
    assert from_vim.socket.recvfrom.called

########NEW FILE########
