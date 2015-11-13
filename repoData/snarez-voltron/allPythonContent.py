__FILENAME__ = dbgentry
import voltron
import voltron.cmd
import voltron.common
try:
    import voltron.lldbcmd
    in_lldb = True
except:
    in_lldb = False
try:
    import voltron.gdbcmd
    in_gdb = True
except:
    in_gdb = False

log = voltron.common.configure_logging()

if in_lldb:
    # Called when the module is loaded into lldb and initialised
    def __lldb_init_module(debugger, dict):
        log.debug("Initialising LLDB command")
        voltron.lldbcmd.inst = voltron.lldbcmd.VoltronLLDBCommand(debugger, dict)
        voltron.cmd.inst = voltron.lldbcmd.inst

    # Called when the command is invoked by lldb
    def lldb_invoke(debugger, command, result, dict):
        voltron.lldbcmd.inst.invoke(debugger, command, result, dict)

if in_gdb:
    # Called when the module is loaded by gdb
    if __name__ == "__main__":
        log.debug('Initialising GDB command')
        inst = voltron.gdbcmd.VoltronGDBCommand()
        voltron.cmd.inst = inst
        print("Voltron loaded.")

if not in_lldb and not in_gdb:
    print("Something wicked this way comes")

########NEW FILE########
__FILENAME__ = cmd
from __future__ import print_function

import logging
import logging.config
from collections import defaultdict

from .comms import *

DISASM_MAX = 32
STACK_MAX = 64

log = configure_logging()

class VoltronCommand (object):
    running = False

    # Methods for handling commands from the debugger
    def handle_command(self, command):
        global log
        if "start" in command:
            self.start()
        elif "stop" in command:
            self.stop()
        elif "status" in command:
            self.status()
        elif "update" in command:
            self.update()
        elif 'debug' in command:
            if 'enable' in command:
                log.setLevel(logging.DEBUG)
                print("Debug logging enabled")
            elif 'disable' in command:
                log.setLevel(logging.INFO)
                print("Debug logging disabled")
            else:
                print("Debug logging is currently " + ("enabled" if log.getEffectiveLevel() == logging.DEBUG else "disabled"))
        else:
            print("Usage: voltron <start|stop|update|status|debug>")

    def start(self):
        if not self.running:
            print("Starting voltron")
            self.running = True
            self.register_hooks()
        else:
            print("Already running")

    def stop(self):
        if self.running:
            print("Stopping voltron")
            self.unregister_hooks()
            self.stop_server()
            self.running = False
        else:
            print("Not running")

    def start_server(self):
        if self.server == None:
            self.server = Server()
            self.server.base_helper = self.base_helper
            self.server.start()
        else:
            log.debug("Server thread is already running")

    def stop_server(self):
        if self.server != None:
            self.server.stop()
            self.server = None
        else:
            log.debug("Server thread is not running")

    def status(self):
        if self.server != None:
            summs = self.server.client_summary()
            print("There are {} clients attached:".format(len(summs)))
            for summary in summs:
                print(summary)
        else:
            print("Server is not running (no inferior)")

    def update(self):
        log.debug("Updating clients")
        self.server.update_clients()

    # These methods are overridden by the debugger-specific classes
    def register_hooks(self):
        pass

    def unregister_hooks(self):
        pass



class DebuggerHelper (object):
    # General methods for retrieving common types of registers
    def get_pc_name(self):
        return self.pc

    def get_pc(self):
        return self.get_register(self.pc)

    def get_sp_name(self):
        return self.sp

    def get_sp(self):
        return self.get_register(self.sp)



########NEW FILE########
__FILENAME__ = colour
ESCAPES = {
    # reset
    'reset':        0,

    # colours
    'grey':         30,
    'red':          31,
    'green':        32,
    'yellow':       33,
    'blue':         34,
    'magenta':      35,
    'cyan':         36,
    'white':        37,

    # background
    'b_grey':       40,
    'b_red':        41,
    'b_green':      42,
    'b_yellow':     43,
    'b_blue':       44,
    'b_magenta':    45,
    'b_cyan':       46,
    'b_white':      47,

    # attributes
    'a_bold':       1,
    'a_dark':       2,
    'a_underline':  4,
    'a_blink':      5,
    'a_reverse':    7,
    'a_concealed':  8
}
ESC_TEMPLATE = '\033[{}m'

def escapes():
    return ESCAPES

def get_esc(name):
    return ESCAPES[name]

def fmt_esc(name):
    return ESC_TEMPLATE.format(escapes()[name])

FMT_ESCAPES = dict((k, fmt_esc(k)) for k in ESCAPES)

########NEW FILE########
__FILENAME__ = common
import os
import logging
import logging.config

LOG_CONFIG = {
    'version': 1,
    'formatters': {
        'standard': {'format': 'voltron: [%(levelname)s] %(message)s'}
    },
    'filters': {
        'debug_only': {
            '()': 'voltron.common.DebugOnlyFilter'
        },
        'debug_max': {
            '()': 'voltron.common.DebugMaxFilter'
        }
    },
    'handlers': {
        'default': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'filters': ['debug_max']
        },
        'debug_file': {
            'class': 'logging.FileHandler',
            'formatter': 'standard',
            'filename': 'voltron.debug.' + str(os.getpid()),
            'delay': True
        }
    },
    'loggers': {
        'voltron': {
            'handlers': ['default', 'debug_file'],
            'level': 'INFO',
            'propogate': True,
        }
    }
}

class DebugOnlyFilter(logging.Filter):
    def filter(self, record):
        return record.levelno == logging.DEBUG

class DebugMaxFilter(logging.Filter):
    def filter(self, record):
        return record.levelno > logging.DEBUG

def configure_logging():
    logging.config.dictConfig(LOG_CONFIG)
    log = logging.getLogger('voltron')
    return log

def merge(d1, d2):
    for k1,v1 in d1.items():
        if isinstance(v1, dict) and k1 in d2.keys() and isinstance(d2[k1], dict):
            merge(v1, d2[k1])
        else:
            d2[k1] = v1
    return d2

# Python 3 shims
if not hasattr(__builtins__, "xrange"):
    xrange = range

########NEW FILE########
__FILENAME__ = comms
import os
import logging
import socket
import select
try:
    import Queue
except:
    import queue as Queue
import time
import pickle
import threading
import logging
import logging.config

from .common import *
from .env import *
import voltron.cmd

READ_MAX = 0xFFFF

queue = Queue.Queue()

log = configure_logging()

#
# Classes shared between client and server
#

# Base socket class
class BaseSocket(object):
    def fileno(self):
        return self.sock.fileno()

    def close(self):
        self.sock.close()

    def send(self, buf):
        self.sock.send(buf)


class SocketDisconnected(Exception): pass


#
# Client-side classes
#

# Socket to register with the server and receive messages, calls view's render() method when a message comes in
class Client(BaseSocket):
    def __init__(self, view=None, config={}):
        self.view = view
        self.config = config
        self.reg_info = None
        self.sock = None
        self.do_connect()

    def do_connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        success = False
        while not success:
            try:
                self.sock.connect(ENV['sock'])
                success = True
                self.register()
            except Exception as e:
                if self.view:
                    self.view.render(error="Failed connecting to server:" + str(e))
                    time.sleep(1)
                else:
                    raise e

    def register(self):
        log.debug('Client {} registering with config: {}'.format(self, str(self.config)))
        msg = {'msg_type': 'register', 'config': self.config}
        log.debug('Sending: ' + str(msg))
        self.send(pickle.dumps(msg))

    def recv(self):
        return self.sock.recv(READ_MAX)

    def read(self):
        data = self.recv()
        if len(data) > 0:
            msg = None
            try:
                msg = pickle.loads(data)
                log.debug('Received message: ' + str(msg))
            except Exception as e:
                log.error('Exception parsing message: ' + str(e))
                log.error('Invalid message: ' + data)

            if msg and self.view:
                self.view.render(msg)
        else:
            log.debug('Empty read')
            raise SocketDisconnected("socket closed")


# Used by calculon
class InteractiveClient(Client):

    def __init__(self, *args, **kwargs):
        super(InteractiveClient, self).__init__(*args, **kwargs)
        self.pending = Queue.Queue()
        self.callback_thread = None

    def query(self, msg):
        self.send(pickle.dumps(msg))
        resp = self.recv()
        if len(resp) > 0:
            return pickle.loads(resp)

    def recv(self):
        if self.callback_thread:
            return self.pending.get()
        else:
            return self._recv()

    def _recv(self):
        return super(InteractiveClient, self).recv()

    def start_callback_thread(self, lock, callback):
        def _():
            while True:
                self.recv_block(lock, callback)
        self.callback_thread = threading.Thread(target=_)
        self.callback_thread.daemon = True
        self.callback_thread.start()

    def recv_block(self, lock, callback):
        msg = self._recv()
        if 'value' in msg:
            # Interactive message
            self.pending.put(msg)
        elif 'data' in msg:
            # Event happened in the debugger
            try:
                lock.acquire()
                callback(msg)
            finally:
                lock.release()

#
# Server-side classes
#

# Wrapper for a ServerThread to run in the context of a debugger host. Responsible for:
# - Collecting clients (populated by ServerThread)
# - Providing summaries of connected clients to the host DebuggerCommand or Console
# - Collecting data from a DebuggerHelper and sending out updates
# - Responding to requests from interactive clients
# - Handling push updates from proxy clients
class Server (object):
    def __init__(self):
        self._clients = []
        self.exit_out, self.exit_in = os.pipe()
        self.base_helper = None
        self.helper = None

    def start(self):
        log.debug("Starting server thread")
        self.thread = ServerThread(self, self._clients, self.exit_out)
        self.thread.start()

    def stop(self):
        log.debug("Stopping server thread")
        os.write(self.exit_in, chr(0))
        self.thread.join(10)

    @property
    def clients(self):
        return self._clients

    def client_summary(self):
        return [str(c) + ': ' + c.registration['config']['type'] for c in self._clients]

    def refresh_helper(self):
        # if we don't have a helper, or the one we have is for the wrong architecture, get a new one
        if self.helper == None or self.helper != None and self.helper.get_arch() not in self.helper.archs:
            self.helper = self.base_helper.helper()

    def update_clients(self):
        log.debug("Updating clients")

        # Make sure we have a target
        if not self.base_helper.has_target():
            return

        # Make sure we have a helper
        self.refresh_helper()

        # Process updates for registered clients
        log.debug("Processing updates")
        for client in filter(lambda c: c.registration['config']['update_on'] == 'stop', self._clients):
            event = {'msg_type': 'update', 'arch': self.helper.arch_group}
            if client.registration['config']['type'] == 'cmd':
                event['data'] = self.helper.get_cmd_output(client.registration['config']['cmd'])
            elif client.registration['config']['type'] == 'register':
                event['data'] = {'regs': self.helper.get_registers(), 'inst': self.helper.get_next_instruction()}
            elif client.registration['config']['type'] == 'disasm':
                event['data'] = self.helper.get_disasm()
            elif client.registration['config']['type'] == 'stack':
                event['data'] = {'data': self.helper.get_stack(), 'sp': self.helper.get_sp()}
            elif client.registration['config']['type'] == 'bt':
                event['data'] = self.helper.get_backtrace()
            elif client.registration['config']['type'] == 'interactive':
                # TODO Work is if there's some plausible state that should be sent
                event['data'] = None

            try:
                client.send_event(event)
            except socket.error:
                self.server.purge_client(client)

    def handle_push_update(self, client, msg):
        log.debug('Got a push update from client {} of type {} with data: {}'.format(self, msg['update_type'], str(msg['data'])))
        event = {'msg_type': 'update', 'data': msg['data']}
        for c in self._clients:
            if c.registration != None and c.registration['config']['type'] == msg['update_type']:
                c.send_event(event)
        client.send_event(pickle.dumps({'msg_type': 'ack'}))

    def handle_interactive_query(self, client, msg):
        log.debug('Got an interactive query from client {} of type {}'.format(self, msg['query']))
        resp = {'value': None}

        # Make sure we have a helper
        self.refresh_helper()

        if msg['query'] == 'get_register':
            reg = msg['register']
            registers = self.helper.get_registers()
            if reg in registers:
                resp['value'] = registers[reg]
        elif msg['query'] == 'get_memory':
            try:
                start = int(msg['start'])
                end = int(msg['end'])
                length = end - start
                assert(length > 0)
                resp['value'] = self.helper.get_memory(start, length)
            except:
                pass
        client.send_event(resp)


# Wrapper for a ServerThread to run in standalone mode for debuggers without python support
class StandaloneServer(Server):
    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('server', help='standalone server for debuggers without python support')
        sp.set_defaults(func=StandaloneServer)

    def __init__(self, args={}, loaded_config={}):
        self.args = args

    def run(self):
        log.debug("Running standalone server")
        self.start()
        while True:
            time.sleep(1)


# Thread spun off when the server is started to listen for incoming client connections
class ServerThread(threading.Thread):
    def __init__(self, server, clients, exit_pipe):
        self.server = server
        self.clients = clients
        self.exit_pipe = exit_pipe
        threading.Thread.__init__(self)

    def run(self):
        # Make sure there's no left over socket
        try:
            os.remove(ENV['sock'])
        except:
            pass

        # Create a server socket instance
        serv = ServerSocket(ENV['sock'])
        self.lock = threading.Lock()

        # Main event loop
        running = True
        while running:
            _rfds = [serv, self.exit_pipe] + self.clients
            rfds, _, _ = select.select(_rfds, [], [])
            for i in rfds:
                if i == serv:
                    client = i.accept()
                    client.server = self.server
                    self.clients.append(client)
                elif i == self.exit_pipe:
                    # Flush the pipe
                    os.read(self.exit_pipe, 1)
                    running = False
                    break
                else:
                    try:
                        i.read()
                    except socket.error:
                        self.purge_client(i)
                    except SocketDisconnected:
                        self.purge_client(i)
        # Clean up
        for client in self.clients:
            client.close()
        os.close(self.exit_pipe)
        serv.close()
        try:
            os.remove(ENV['sock'])
        except:
            pass

    def purge_client(self, client):
        client.close()
        self.clients.remove(client)


# Socket for talking to an individual client, collected by Server/ServerThread
class ClientHandler(BaseSocket):
    def __init__(self, sock):
        self.sock = sock
        self.registration = None

    def read(self):
        data = self.sock.recv(READ_MAX)
        if len(data.strip()):
            # receive message
            try:
                msg = pickle.loads(data)
                log.debug('Received msg: ' + str(msg))
            except Exception as e:
                log.error('Exception: ' + str(e))
                log.error('Invalid message data: ' + str(data))
                return

            # store registration or dispatch message to server
            if msg['msg_type'] == 'register':
                log.debug('Registering client {} with config: {}'.format(self, str(msg['config'])))
                self.registration = msg
            elif msg['msg_type'] == 'push_update':
                self.server.handle_push_update(self, msg)
            elif msg['msg_type'] == 'interactive':
                self.server.handle_interactive_query(self, msg)
            else:
                log.error('Invalid message type: ' + msg['msg_type'])
        else:
            raise SocketDisconnected("socket closed")

    def send_event(self, event):
        log.debug('Sending event to client {}: {}'.format(self, event))
        self.send(pickle.dumps(event))


# Main server socket for accept()s
class ServerSocket(BaseSocket):
    def __init__(self, sockfile):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(sockfile)
        self.sock.listen(1)

    def accept(self):
        pair = self.sock.accept()
        if pair is not None:
            sock, addr = pair
            try:
                # TODO read some bytes, parse a header and dispatch to a
                # different client type
                return ClientHandler(sock)
            except Exception as e:
                log.error("Exception handling accept: " + str(e))

########NEW FILE########
__FILENAME__ = console
from __future__ import print_function

import sys
import os
import sys
import lldb
import rl
from rl import completer, generator, completion

from .comms import *
from .common import *
from .colour import *
from .lldbcmd import *

VERSION = 'voltron-0.1'
BANNER = "{version} (based on {lldb_version})"

log = configure_logging()

class Console(object):
    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('console', help='voltron debugger console')
        sp.set_defaults(func=Console)

    def __init__(self, args={}, loaded_config={}):
        self.args = args
        self.config = loaded_config['console']
        if not args.debug:
            log.setLevel(logging.WARNING)

        # set up line editor
        completer.completer = self.complete
        completer.parse_and_bind('TAB: complete')
        rl.history.read_file(ENV['history'])
        self.lastbuf = None

        # set up debugger
        self.dbg = lldb.SBDebugger.Create()
        self.dbg.SetAsync(False)
        lldb.debugger = self.dbg

        # set up lldb command interpreter
        self.ci = self.dbg.GetCommandInterpreter()

        # set up voltron server
        self.server = Server()
        self.server.base_helper = LLDBHelper
        self.server.start()

        # set up voltron console command
        self.cmd = VoltronLLDBConsoleCommand()
        self.cmd.server = self.server
        voltron.lldbcmd.inst = self.cmd

        # set prompt
        self.update_prompt()

    def run(self):
        # print banner
        self.print_banner()

        # main event loop
        while 1:
            try:
                self.pre_prompt()
                line = raw_input(self.prompt.encode(sys.stdout.encoding))
            except EOFError:
                break
            self.handle_command(line)
            rl.readline.write_history_file(ENV['history'])

    def print_banner(self):
        d = {'version': VERSION, 'lldb_version': self.dbg.GetVersionString()}
        print(BANNER.format(**d))

    def update_prompt(self):
        self.prompt = self.process_prompt(self.config['prompt'])

    def process_prompt(self, prompt):
        d = FMT_ESCAPES
        if self.server.helper:
            d['pc'] = self.server.helper.get_pc()
            d['thread'] = self.server.helper.get_current_thread()
        else:
            d['pc'] = 0
            d['thread'] = '-'
        return self.escape_prompt(prompt['format'].format(**d))

    def escape_prompt(self, prompt, start = "\x01", end = "\x02"):
        escaped = False
        result = ""
        for c in prompt:
            if c == "\x1b" and not escaped:
                result += start + c
                escaped = True
            elif c.isalpha() and escaped:
                result += c + end
                escaped = False
            else:
                result += c
        return result

    def pre_prompt(self):
        log.debug("updating views")
        self.update_prompt()
        self.cmd.update()

    def handle_command(self, cmd):
        if cmd.startswith('voltron'):
            # execute voltron command
            self.cmd.handle_command(cmd)
        else:
            # execute lldb command
            res = lldb.SBCommandReturnObject()
            self.ci.HandleCommand(cmd, res)

            # print output
            if res.Succeeded():
                print(res.GetOutput().strip())
            else:
                print(res.GetError().strip())

    def complete(self, prefix, state):
        completion.suppress_append = True   # lldb appends its own spaces
        buf = rl.readline.get_line_buffer()

        if self.lastbuf != buf:
            # new buffer, redo completion
            self.res = []
            matches = lldb.SBStringList()
            r = self.ci.HandleCompletion(buf, completion.rl_point, completion.rl_point, -1, matches)
            log.debug("completion: got matches: " + str([matches.GetStringAtIndex(i) for i in range(matches.GetSize())]))
            
            # if there's a single fragment
            if len(matches.GetStringAtIndex(0).strip()) > 0:
                # add it
                match = prefix + matches.GetStringAtIndex(0)
                log.debug("completion: partial: " + match)
                self.res.append(match)
            else:
                # otherwise, add the other possible matches
                for i in range(1, matches.GetSize()):
                    match = matches.GetStringAtIndex(i)[len(buf.split()[-1]):]
                    self.res.append(match)

            # store buffer
            self.lastbuf = buf

        log.debug("completion: returning: " + self.res[state])
        return self.res[state]

    def cleanup(self):
        self.server.stop()


########NEW FILE########
__FILENAME__ = env
from scruffy import Environment

from .common import *

log = configure_logging()


ENV = Environment({
    'dir':  {
        'path': '~/.voltron',
        'create': True,
        'mode': 448 # 0700
    },
    'files': {
        'config': {
            'type':     'config',
            'default':  {
                'path':     'config/default.cfg',
                'rel_to':   'pkg',
                'pkg':      'voltron'
            },
            'read':     True
        },
        'sock': {
            'name':     '{basename}.sock',
            'type':     'raw',
            'var':      'VOLTRON_SOCKET'
        },
        'history': {
            'type':     'raw',
            'var':      'VOLTRON_HISTORY'
        }
    },
    'basename': 'voltron'
})

CONFIG = ENV['config']

########NEW FILE########
__FILENAME__ = gdbcmd
from __future__ import print_function

import os
import sys
import gdb
import logging
import re

from .cmd import *
from .common import *

log = configure_logging()


class VoltronGDBCommand (VoltronCommand, gdb.Command):
    def __init__(self):
        super(VoltronCommand, self).__init__("voltron", gdb.COMMAND_NONE, gdb.COMPLETE_NONE)
        self.running = False
        self.server = None
        self.helper = None
        self.base_helper = GDBHelper

    def invoke(self, arg, from_tty):
        self.handle_command(arg)

    def register_hooks(self):
        gdb.events.stop.connect(self.stop_handler)
        gdb.events.exited.connect(self.exit_handler)
        gdb.events.cont.connect(self.cont_handler)

    def unregister_hooks(self):
        gdb.events.stop.disconnect(self.stop_handler)
        gdb.events.exited.disconnect(self.exit_handler)
        gdb.events.cont.disconnect(self.cont_handler)

    def stop_handler(self, event):
        log.debug('Inferior stopped')
        self.update()

    def exit_handler(self, event):
        log.debug('Inferior exited')
        self.stop_server()
        self.helper = None

    def cont_handler(self, event):
        log.debug('Inferior continued')
        if self.server == None:
            self.start_server()


class GDBHelper (DebuggerHelper):
    @staticmethod
    def has_target():
        return len(gdb.inferiors()) > 0

    @staticmethod
    def get_arch():
        try:
            return gdb.selected_frame().architecture().name()
        except:
            return re.search('\(currently (.*)\)', gdb.execute('show architecture', to_string=True)).group(1)

    @staticmethod
    def helper():
        arch = GDBHelper.get_arch()
        for cls in GDBHelper.__subclasses__():
            if hasattr(cls, 'archs') and arch in cls.archs:
                return cls()
        raise LookupError('No helper found for arch {}'.format(arch))

    def get_next_instruction(self):
        return self.get_disasm().split('\n')[0].split(':')[1].strip()

    def get_disasm(self):
        log.debug('Getting disasm')
        res = gdb.execute('x/{}i ${}'.format(DISASM_MAX, self.get_pc_name()), to_string=True)
        return res

    def get_stack(self):
        log.debug('Getting stack')
        res = str(gdb.selected_inferior().read_memory(self.get_sp(), STACK_MAX*16))
        return res

    def get_memory(self, start, length):
        log.debug('Getting %x + %d' % (start, length))
        res = str(gdb.selected_inferior().read_memory(start, length))
        return res

    def get_backtrace(self):
        log.debug('Getting backtrace')
        res = gdb.execute('bt', to_string=True)
        return res

    def get_cmd_output(self, cmd=''):
        log.debug('Getting command output: ' + cmd)
        res = gdb.execute(cmd, to_string=True)
        return res


class GDBHelperX86 (GDBHelper):
    archs = ['i386', 'i386:intel', 'i386:x64-32', 'i386:x64-32:intel', 'i8086']
    arch_group = 'x86'
    pc = 'eip'
    sp = 'esp'

    def get_registers(self):
        log.debug('Getting registers')

        # Get regular registers
        regs = ['eax','ebx','ecx','edx','ebp','esp','edi','esi','eip','cs','ds','es','fs','gs','ss']
        vals = {}
        for reg in regs:
            try:
                vals[reg] = int(gdb.parse_and_eval('(long)$'+reg)) & 0xFFFFFFFF
            except:
                log.debug('Failed getting reg: ' + reg)
                vals[reg] = 'N/A'

        # Get flags
        try:
            vals['eflags'] = int(gdb.execute('info reg $eflags', to_string=True).split()[1], 16)
        except:
            log.debug('Failed getting reg: eflags')
            vals['eflags'] = 'N/A'

        # Get SSE registers
        sse = self.get_registers_sse(8)
        vals = dict(list(vals.items()) + list(sse.items()))

        # Get FPU registers
        fpu = self.get_registers_fpu()
        vals = dict(list(vals.items()) + list(fpu.items()))

        log.debug('Got registers: ' + str(vals))
        return vals

    def get_registers_sse(self, num=8):
        # the old way of doing this randomly crashed gdb or threw a python exception
        regs = {}
        for line in gdb.execute('info all-registers', to_string=True).split('\n'):
            m = re.match('^(xmm\d+)\s.*uint128 = (0x[0-9a-f]+)\}', line)
            if m:
                regs[m.group(1)] = int(m.group(2), 16)
        return regs

    def get_registers_fpu(self):
        regs = {}
        for i in range(8):
            reg = 'st'+str(i)
            try:
                regs[reg] = int(gdb.execute('info reg '+reg, to_string=True).split()[-1][2:-1], 16)
            except:
                log.debug('Failed getting reg: ' + reg)
                regs[reg] = 'N/A'
        return regs

    def get_register(self, reg):
        log.debug('Getting register: ' + reg)
        return int(gdb.parse_and_eval('(long)$'+reg)) & 0xFFFFFFFF


class GDBHelperX64 (GDBHelperX86, GDBHelper):
    archs = ['i386:x86-64', 'i386:x86-64:intel']
    arch_group = 'x64'
    pc = 'rip'
    sp = 'rsp'

    def get_registers(self):
        log.debug('Getting registers')

        # Get regular registers
        regs = ['rax','rbx','rcx','rdx','rbp','rsp','rdi','rsi','rip','r8','r9','r10','r11','r12','r13','r14','r15',
                'cs','ds','es','fs','gs','ss']
        vals = {}
        for reg in regs:
            try:
                vals[reg] = int(gdb.parse_and_eval('(long long)$'+reg)) & 0xFFFFFFFFFFFFFFFF
            except:
                log.debug('Failed getting reg: ' + reg)
                vals[reg] = 'N/A'

        # Get flags
        try:
            vals['rflags'] = int(gdb.execute('info reg $eflags', to_string=True).split()[1], 16)
        except:
            log.debug('Failed getting reg: eflags')
            vals['rflags'] = 'N/A'

        # Get SSE registers
        sse = self.get_registers_sse(16)
        vals = dict(list(vals.items()) + list(sse.items()))

        # Get FPU registers
        fpu = self.get_registers_fpu()
        vals = dict(list(vals.items()) + list(fpu.items()))

        log.debug('Got registers: ' + str(vals))
        return vals

    def get_register(self, reg):
        log.debug('Getting register: ' + reg)
        return int(gdb.parse_and_eval('(long long)$'+reg)) & 0xFFFFFFFFFFFFFFFF


class GDBHelperARM (GDBHelper):
    archs = ['arm', 'arm', 'armv2', 'armv2a', 'armv3', 'armv3m', 'armv4', 'armv4t', 'armv5', 'armv5t', 'armv5te']
    arch_group = 'arm'
    pc = 'pc'
    sp = 'sp'

    def get_registers(self):
        log.debug('Getting registers')
        regs = ['pc','sp','lr','cpsr','r0','r1','r2','r3','r4','r5','r6', 'r7','r8','r9','r10','r11','r12']
        vals = {}
        for reg in regs:
            try:
                vals[reg] = int(gdb.parse_and_eval('(long)$'+reg)) & 0xFFFFFFFF
            except:
                log.debug('Failed getting reg: ' + reg)
                vals[reg] = 'N/A'
        return vals

    def get_register(self, reg):
        log.debug('Getting register: ' + reg)
        return int(gdb.parse_and_eval('(long)$'+reg)) & 0xFFFFFFFF

########NEW FILE########
__FILENAME__ = gdbproxy
import logging
import socket
import struct
try:
    import cPickle as pickle
except ImportError:
    import pickle

from .comms import READ_MAX, BaseSocket
from .common import *
from .env import *

log = configure_logging()

# This class is called from the command line by GDBv6's stop-hook. The dumped registers and stack are collected,
# parsed and sent to the voltron standalone server, which then sends the updates out to any registered clients.
# I hate that this exists. Fuck GDBv6.
class GDB6Proxy(BaseSocket):
    REGISTERS = ['rax','rbx','rcx','rdx','rbp','rsp','rdi','rsi','rip','r8','r9','r10','r11','r12','r13','r14','r15','eflags','cs','ds','es','fs','gs','ss']

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('gdb6proxy', help='import a dump from GDBv6 and send it to the server')
        sp.add_argument('type', action='store', help='the type to proxy - reg or stack')
        sp.set_defaults(func=GDB6Proxy)

    def __init__(self, args={}, loaded_config={}):
        global log
        asyncore.dispatcher.__init__(self)
        self.args = args
        if not args.debug:
            log.setLevel(logging.WARNING)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(ENV['socket'])
        self.handle_connect()

    def run(self):
        while True:
            self.handle_read()

    def handle_connect(self):
        if self.args.type == "reg":
            event = self.read_registers()
        elif self.args.type == "stack":
            event = self.read_stack()
        else:
            log.error("Invalid proxy type")
        log.debug("Pushing update to server")
        log.debug(str(event))
        self.send(pickle.dumps(event))

    def handle_read(self):
        data = self.recv(READ_MAX)
        msg = pickle.loads(data)
        if msg['msg_type'] != 'ack':
            log.error("Did not get ack: " + str(msg))
        self.close()

    def read_registers(self):
        log.debug("Parsing register data")
        data = {}
        for reg in GDB6Proxy.REGISTERS:
            try:
                with open('/tmp/voltron.reg.'+reg, 'r+b') as f:
                    if reg in ['eflags','cs','ds','es','fs','gs','ss']:
                        (val,) = struct.unpack('<L', f.read())
                    else:
                        (val,) = struct.unpack('<Q', f.read())
                data[reg] = val
            except Exception as e:
                log.warning("Exception reading register {}: {}".format(reg, str(e)))
                data[reg] = '<fail>'
        data['rflags'] = data['eflags']
        event = {'msg_type': 'push_update', 'update_type': 'register', 'data': data}
        return event

    def read_stack(self):
        log.debug("Parsing stack data")
        with open('/tmp/voltron.stack', 'r+b') as f:
            data = f.read()
        with open('/tmp/voltron.reg.rsp', 'r+b') as f:
            (rsp,) = struct.unpack('<Q', f.read())
        event = {'msg_type': 'push_update', 'update_type': 'stack', 'data': {'sp': rsp, 'data': data}}
        return event

########NEW FILE########
__FILENAME__ = lldbcmd
from __future__ import print_function

import lldb
import logging
import logging.config

from .cmd import *
from .comms import *
from .common import *

log = configure_logging()
inst = None


class VoltronLLDBCommand (VoltronCommand):
    def __init__(self, debugger, dict):
        super(VoltronCommand, self).__init__()
        self.debugger = debugger
        lldb.debugger.HandleCommand('command script add -f dbgentry.lldb_invoke voltron')
        self.running = False
        self.server = None
        self.base_helper = LLDBHelper

    def invoke(self, debugger, command, result, dict):
        self.handle_command(command)

    def start(self):
        if self.server == None:
            self.start_server()
        super(VoltronLLDBCommand, self).start()

    def register_hooks(self):
        lldb.debugger.HandleCommand('target stop-hook add -o \'voltron update\'')

    def unregister_hooks(self):
        # XXX: Fix this so it only removes our stop-hook
        lldb.debugger.HandleCommand('target stop-hook delete')


class VoltronLLDBConsoleCommand (VoltronCommand):
    def __init__(self):
        # we just add a reference to a dummy script, and intercept calls to `voltron` in the console
        # this kinda sucks, but it'll do for now
        lldb.debugger.HandleCommand('command script add -f xxx voltron')
        self.running = False
        self.server = None


class LLDBHelper (DebuggerHelper):
    @staticmethod
    def has_target():
        registers = LLDBHelper.get_frame().GetRegisters()
        return len(registers) != 0

    @staticmethod
    def get_frame():
        return lldb.debugger.GetTargetAtIndex(0).process.selected_thread.GetFrameAtIndex(0)

    @staticmethod
    def get_arch():
        return lldb.debugger.GetTargetAtIndex(0).triple.split('-')[0]

    @staticmethod
    def helper():
        if LLDBHelper.has_target():
            arch = LLDBHelper.get_arch()
            for cls in LLDBHelper.__subclasses__():
                if hasattr(cls, 'archs') and arch in cls.archs:
                    inst = cls()
                    return inst
            raise LookupError('No helper found for arch {}'.format(arch))
        raise LookupError('No target')

    def get_next_instruction(self):
        target = lldb.debugger.GetTargetAtIndex(0)
        pc = lldb.SBAddress(self.get_pc(), target)
        inst = target.ReadInstructions(pc, 1)
        return str(inst).split(':')[1].strip()

    def get_registers(self):
        log.debug('Getting registers')

        regs = LLDBHelper.get_frame().GetRegisters()
        objs = []
        for i in xrange(len(regs)):
            objs += regs[i]

        regs = {}
        for reg in objs:
            val = 'n/a'
            if reg.value != None:
                try:
                    val = int(reg.value, 16)
                except:
                    try:
                        val = int(reg.value)
                    except Exception as e:
                        log.debug("Exception converting register value: " + str(e))
                        val = 0
            regs[reg.name] = val

        return regs

    def get_register(self, reg):
        log.debug('Getting register: ' + reg)
        return self.get_registers()[reg]

    def get_disasm(self):
        log.debug('Getting disasm')
        res = self.get_cmd_output('disassemble -c {}'.format(DISASM_MAX))
        return res

    def get_stack(self):
        log.debug('Getting stack')
        error = lldb.SBError()
        res = lldb.debugger.GetTargetAtIndex(0).process.ReadMemory(self.get_sp(), STACK_MAX*16, error)
        return res

    def get_memory(self, start, length):
        log.debug('Getting %x + %d' % (start, length))
        error = lldb.SBError()
        res = lldb.debugger.GetTargetAtIndex(0).process.ReadMemory(start, length, error)
        return res

    def get_backtrace(self):
        log.debug('Getting backtrace')
        res = self.get_cmd_output('bt')
        return res

    def get_cmd_output(self, cmd=None):
        if cmd:
            log.debug('Getting command output: ' + cmd)
            res = lldb.SBCommandReturnObject()
            lldb.debugger.GetCommandInterpreter().HandleCommand(cmd, res)
            res = res.GetOutput()
        else:
            res = "<No command>"
        return res

    def get_current_thread(self):
        return lldb.debugger.GetTargetAtIndex(0).process.GetSelectedThread().idx


class LLDBHelperX86 (LLDBHelper):
    archs = ['i386']
    arch_group = 'x86'
    pc = 'eip'
    sp = 'esp'

    def get_registers(self):
        regs = super(LLDBHelperX86, self).get_registers()
        for i in range(7):
            regs['st'+str(i)] = regs['stmm'+str(i)]
            return regs


class LLDBHelperX64 (LLDBHelperX86, LLDBHelper):
    archs = ['x86_64']
    arch_group = 'x64'
    pc = 'rip'
    sp = 'rsp'


class LLDBHelperARM (LLDBHelper):
    archs = ['armv6', 'armv7', 'armv7s']
    arch_group = 'arm'
    pc = 'pc'
    sp = 'sp'


class LLDBHelperARM64 (LLDBHelper):
    archs = ['arm64']
    arch_group = 'arm64'
    pc = 'pc'
    sp = 'sp'

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python

import os
import argparse
import logging
import logging.config
import struct
import traceback

from .view import *
from .comms import *
from .gdbproxy import *
from .common import *
from .env import *
try:
    from .console import *
    HAS_CONSOLE = True
except ImportError:
    HAS_CONSOLE = False

log = configure_logging()

def main(debugger=None, dict=None):
    global log, queue, inst

    # Load config
    # Set up command line arg parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', '-d', action='store_true', help='print debug logging')
    top_level_sp = parser.add_subparsers(title='subcommands', description='valid subcommands')
    view_parser = top_level_sp.add_parser('view', help='display a view')
    view_sp = view_parser.add_subparsers(title='views', description='valid view types', help='additional help')

    # Update the view base class
    base = CursesView if 'curses' in CONFIG.keys() and CONFIG['curses'] else TerminalView
    for cls in TerminalView.__subclasses__():
        cls.__bases__ = (base,)

    # Set up a subcommand for each view class
    for cls in base.__subclasses__():
        cls.configure_subparser(view_sp)

    # And subcommands for the loathsome red-headed stepchildren
    StandaloneServer.configure_subparser(top_level_sp)
    GDB6Proxy.configure_subparser(top_level_sp)
    if HAS_CONSOLE:
        Console.configure_subparser(top_level_sp)

    # Parse args
    args = parser.parse_args()
    if args.debug:
        log.setLevel(logging.DEBUG)

    # Instantiate and run the appropriate module
    inst = args.func(args, loaded_config=CONFIG)
    try:
        inst.run()
    except Exception as e:
        log.error("Exception running module {}: {}".format(inst.__class__.__name__, traceback.format_exc()))
    except KeyboardInterrupt:
        pass
    inst.cleanup()
    log.info('Exiting')


if __name__ == "__main__":
    main()



########NEW FILE########
__FILENAME__ = rdb
import pdb
import socket
import sys

# Trying to debug a quirk in some code that gets called async by {ll,g}db?
#
# from .rdb import Rdb
# Rdb().set_trace()
#
# Then: telnet localhost 4444


socks = {}
# Only bind the socket once
def _sock(port):
    if port in socks:
        return socks[port]

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", port))
    socks[port] = s
    return s

class Rdb(pdb.Pdb):
    def __init__(self, port=4444):
        self.old_stdout = sys.stdout
        self.old_stdin = sys.stdin
        self.skt = _sock(port)
        self.skt.listen(1)
        (clientsocket, address) = self.skt.accept()
        handle = clientsocket.makefile('rw')
        pdb.Pdb.__init__(self, completekey='tab', stdin=handle, stdout=handle)
        sys.stdout = sys.stdin = handle

########NEW FILE########
__FILENAME__ = view
from __future__ import print_function

import os
import sys
import logging
try:
    import cPickle as pickle
except ImportError:
    import pickle
import curses
import pprint
import re
import signal

try:
    import pygments
    import pygments.lexers
    import pygments.formatters
    have_pygments = True
except:
    have_pygments = False

from collections import defaultdict

from .comms import *
from .common import *
from .colour import *

log = configure_logging()

ADDR_FORMAT_128 = '0x{0:0=32X}'
ADDR_FORMAT_64 = '0x{0:0=16X}'
ADDR_FORMAT_32 = '0x{0:0=8X}'
ADDR_FORMAT_16 = '0x{0:0=4X}'
SHORT_ADDR_FORMAT_128 = '{0:0=32X}'
SHORT_ADDR_FORMAT_64 = '{0:0=16X}'
SHORT_ADDR_FORMAT_32 = '{0:0=8X}'
SHORT_ADDR_FORMAT_16 = '{0:0=4X}'

# Parent class for all views
class VoltronView (object):
    @classmethod
    def add_generic_arguments(cls, sp):
        sp.add_argument('--show-header', '-e', dest="header", action='store_true', help='show header', default=None)
        sp.add_argument('--hide-header', '-E', dest="header", action='store_false', help='hide header')
        sp.add_argument('--show-footer', '-f', dest="footer", action='store_true', help='show footer', default=None)
        sp.add_argument('--hide-footer', '-F', dest="footer", action='store_false', help='hide footer')
        sp.add_argument('--name', '-n', action='store', help='named configuration to use', default=None)

    def __init__(self, args={}, loaded_config={}):
        log.debug('Loading view: ' + self.__class__.__name__)
        self.client = None
        self.args = args
        self.loaded_config = loaded_config

        # Commonly set by render method for header and footer formatting
        self.title = ''
        self.info = ''

        # Build configuration
        self.build_config()

        log.debug("View config: " + pprint.pformat(self.config))
        log.debug("Args: " + str(self.args))

        # Let subclass do any setup it needs to do
        self.setup()

        # Override settings from command line args
        if self.args.header != None:
            self.config['header']['show'] = self.args.header
        if self.args.footer != None:
            self.config['footer']['show'] = self.args.footer

        # Initialise window
        self.init_window()

        # Setup a SIGWINCH handler so we do reasonable things on resize
        # signal.signal(signal.SIGWINCH, lambda sig, stack: self.render())

        # Connect to server
        self.connect()

    def build_config(self):
        # Start with all_views config
        self.config = self.loaded_config['view']['all_views']

        # Add view-specific config
        self.config['type'] = self.view_type
        name = self.view_type + '_view'
        if 'view' in self.loaded_config and name in self.loaded_config['view']:
            merge(self.loaded_config['view'][name], self.config)

        # Add named config
        if self.args.name != None:
            merge(self.loaded_config[self.args.name], self.config)

        # Apply view-specific command-line args
        self.apply_cli_config()

    def apply_cli_config(self):
        if self.args.header != None:
            self.config['header']['show'] = self.args.header
        if self.args.footer != None:
            self.config['footer']['show'] = self.args.footer

    def setup(self):
        log.debug('Base view class setup')

    def connect(self):
        try:
            self.client = Client(view=self, config=self.config)
        except Exception as e:
            log.error('Exception connecting: ' + str(e))
            raise e

    def run(self):
        self.client.do_connect()
        os.system('clear')
        self.render(error='Waiting for an update from the debugger')
        try:
            while True:
                self.client.read()
        except SocketDisconnected as e:
            if self.should_reconnect():
                log.debug("Restarting process: " + str(type(e)))
                log.debug("Restarting process")
                self.reexec()
            else:
                raise


    def render(self, msg=None):
        log.warning('Might wanna implement render() in this view eh')

    def hexdump(self, src, length=16, sep='.', offset=0):
        FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or sep for x in range(256)])
        lines = []
        for c in xrange(0, len(src), length):
            chars = src[c:c+length]
            hex = ' '.join(["%02X" % ord(x) for x in chars])
            if len(hex) > 24:
                hex = "%s %s" % (hex[:24], hex[24:])
            printable = ''.join(["%s" % ((ord(x) <= 127 and FILTER[ord(x)]) or sep) for x in chars])
            lines.append("%s:  %-*s  |%s|\n" % (ADDR_FORMAT_64.format(offset+c), length*3, hex, printable))
        return ''.join(lines).strip()

    def should_reconnect(self):
        try:
            return self.loaded_config['view']['reconnect']
        except:
            return True

    def reexec(self):
        # Instead of trying to reset internal state, just exec ourselves again
        os.execv(sys.argv[0], sys.argv)


class TerminalView (VoltronView):
    def init_window(self):
        # Hide cursor
        os.system('tput civis')

    def cleanup(self):
        log.debug('Cleaning up view')
        os.system('tput cnorm')

    def clear(self):
        os.system('clear')

    def render(self, msg=None):
        self.clear()
        if self.config['header']['show']:
            print(self.format_header())
        print(self.body, end='')
        if self.config['footer']['show']:
            print('\n' + self.format_footer(), end='')
        sys.stdout.flush()

    def window_size(self):
        height, width = os.popen('stty size').read().split()
        height = int(height)
        width = int(width)
        return (height, width)

    def body_height(self):
        height, width = self.window_size()
        if self.config['header']['show']:
            height -= 1
        if self.config['footer']['show']:
            height -= 1
        return height

    def colour(self, text='', colour=None, background=None, attrs=[]):
        s = ''
        if colour != None:
            s += fmt_esc(colour)
        if background != None:
            s += fmt_esc('b_'+background)
        if attrs != []:
            s += ''.join(map(lambda x: fmt_esc('a_'+x), attrs))
        s += text
        s += fmt_esc('reset')
        return s

    def format_header(self):
        height, width = self.window_size()

        # Get values for labels
        l = getattr(self, self.config['header']['label_left']['name']) if self.config['header']['label_left']['name'] != None else ''
        r = getattr(self, self.config['header']['label_right']['name']) if self.config['header']['label_right']['name'] != None else ''
        p = self.config['header']['pad']
        llen = len(l)
        rlen = len(r)

        # Add colour
        l = self.colour(l, self.config['header']['label_left']['colour'], self.config['header']['label_left']['bg_colour'], self.config['header']['label_left']['attrs'])
        r = self.colour(r, self.config['header']['label_right']['colour'], self.config['header']['label_right']['bg_colour'], self.config['header']['label_right']['attrs'])
        p = self.colour(p, self.config['header']['colour'], self.config['header']['bg_colour'], self.config['header']['attrs'])

        # Build header
        header = l + (width - llen - rlen)*p + r

        return header

    def format_footer(self):
        height, width = self.window_size()

        # Get values for labels
        l = getattr(self, self.config['footer']['label_left']['name']) if self.config['footer']['label_left']['name'] != None else ''
        r = getattr(self, self.config['footer']['label_right']['name']) if self.config['footer']['label_right']['name'] != None else ''
        p = self.config['footer']['pad']
        llen = len(l)
        rlen = len(r)

        # Add colour
        l = self.colour(l, self.config['footer']['label_left']['colour'], self.config['footer']['label_left']['bg_colour'], self.config['footer']['label_left']['attrs'])
        r = self.colour(r, self.config['footer']['label_right']['colour'], self.config['footer']['label_right']['bg_colour'], self.config['footer']['label_right']['attrs'])
        p = self.colour(p, self.config['footer']['colour'], self.config['footer']['bg_colour'], self.config['footer']['attrs'])

        # Build header and footer
        footer = l + (width - llen - rlen)*p + r

        return footer

    def pad_body(self):
        height, width = self.window_size()

        # Split body into lines
        lines = self.body.split('\n')

        # Subtract lines (including wrapped lines)
        pad = self.body_height()
        for line in lines:
            line = ''.join(re.split('\033\[\d+m', line))
            (n, rem) = divmod(len(line), width)
            if rem > 0: n += 1
            pad -= n

        # If we have too much data for the view, too bad
        if pad < 0:
            pad = 0

        self.body += int(pad)*'\n'


class CursesView (VoltronView):
    def init_window(self):
        self.screen = curses.initscr()
        self.screen.border(0)

    def cleanup(self):
        curses.endwin()

    def render(self, msg=None):
        self.screen.clear()
        y = 0
        if self.config['header']['show']:
            self.screen.addstr(0, 0, self.header)
            y = 1
        self.screen.addstr(0, y, self.body)
        self.screen.refresh()

    def clear(self):
        self.screen.clear()

    def window_size(self):
        height, width = os.popen('stty size').read().split()
        height = int(height)
        width = int(width)
        return (height, width)

    def body_height(self):
        height, width = self.window_size()
        if self.config['header']['show']:
            height -= 1
        if self.config['footer']['show']:
            height -= 1
        return height


# Class to actually render the view
class RegisterView (TerminalView):
    view_type = 'register'
    FORMAT_INFO = {
        'x64': [
            {
                'regs':             ['rax','rbx','rcx','rdx','rbp','rsp','rdi','rsi','rip',
                                     'r8','r9','r10','r11','r12','r13','r14','r15'],
                'label_format':     '{0:3s}:',
                'category':         'general',
            },
            {
                'regs':             ['cs','ds','es','fs','gs','ss'],
                'value_format':     SHORT_ADDR_FORMAT_16,
                'category':         'general',
            },
            {
                'regs':             ['rflags'],
                'value_format':     '{}',
                'value_func':       'self.format_flags',
                'value_colour_en':  False,
                'category':         'general',
            },
            {
                'regs':             ['rflags'],
                'value_format':     '{}',
                'value_func':       'self.format_jump',
                'value_colour_en':  False,
                'category':         'general',
                'format_name':      'jump'
            },
            {
                'regs':             ['xmm0','xmm1','xmm2','xmm3','xmm4','xmm5','xmm6','xmm7','xmm8',
                                     'xmm9','xmm10','xmm11','xmm12','xmm13','xmm14','xmm15'],
                'value_format':     SHORT_ADDR_FORMAT_128,
                'value_func':       'self.format_xmm',
                'category':         'sse',
            },
            {
                'regs':             ['st0','st1','st2','st3','st4','st5','st6','st7'],
                'value_format':     '{0:0=20X}',
                'value_func':       'self.format_fpu',
                'category':         'fpu',
            },
        ],
        'x86': [
            {
                'regs':             ['eax','ebx','ecx','edx','ebp','esp','edi','esi','eip'],
                'label_format':     '{0:3s}:',
                'value_format':     SHORT_ADDR_FORMAT_32,
                'category':         'general',
            },
            {
                'regs':             ['cs','ds','es','fs','gs','ss'],
                'value_format':     SHORT_ADDR_FORMAT_16,
                'category':         'general',
            },
            {
                'regs':             ['eflags'],
                'value_format':     '{}',
                'value_func':       'self.format_flags',
                'value_colour_en':  False,
                'category':         'general',
            },
            {
                'regs':             ['eflags'],
                'value_format':     '{}',
                'value_func':       'self.format_jump',
                'value_colour_en':  False,
                'category':         'general',
                'format_name':      'jump'
            },
            {
                'regs':             ['xmm0','xmm1','xmm2','xmm3','xmm4','xmm5','xmm6','xmm7'],
                'value_format':     SHORT_ADDR_FORMAT_128,
                'value_func':       'self.format_xmm',
                'category':         'sse',
            },
            {
                'regs':             ['st0','st1','st2','st3','st4','st5','st6','st7'],
                'value_format':     '{0:0=20X}',
                'value_func':       'self.format_fpu',
                'category':         'fpu',
            },
        ],
        'arm': [
            {
                'regs':             ['pc','sp','lr','cpsr','r0','r1','r2','r3','r4','r5','r6',
                                    'r7','r8','r9','r10','r11','r12'],
                'label_format':     '{0:>3s}:',
                'value_format':     SHORT_ADDR_FORMAT_32,
                'category':         'general',
            }
        ],
        'arm64': [
            {
                'regs':             ['pc', 'sp', 'x0', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'x8', 'x9', 'x10',
                                    'x11', 'x12', 'x13', 'x14', 'x15', 'x16', 'x17', 'x18', 'x19', 'x20',
                                    'x21', 'x22', 'x23', 'x24', 'x25', 'x26', 'x27', 'x28', 'x29', 'x30'],
                'label_format':     '{0:3s}:',
                'value_format':     SHORT_ADDR_FORMAT_64,
                'category':         'general',
            },
        ],
    }
    TEMPLATES = {
        'x64': {
            'horizontal': {
                'general': (
                    "{raxl} {rax}  {rbxl} {rbx}  {rbpl} {rbp}  {rspl} {rsp}  {rflags}\n"
                    "{rdil} {rdi}  {rsil} {rsi}  {rdxl} {rdx}  {rcxl} {rcx}  {ripl} {rip}\n"
                    "{r8l} {r8}  {r9l} {r9}  {r10l} {r10}  {r11l} {r11}  {r12l} {r12}\n"
                    "{r13l} {r13}  {r14l} {r14}  {r15l} {r15}\n"
                    "{csl} {cs}  {dsl} {ds}  {esl} {es}  {fsl} {fs}  {gsl} {gs}  {ssl} {ss} {jump}"
                ),
                'sse': (
                    "{xmm0l}  {xmm0} {xmm1l}  {xmm1} {xmm2l}  {xmm2}\n"
                    "{xmm3l}  {xmm3} {xmm4l}  {xmm4} {xmm5l}  {xmm5}\n"
                    "{xmm6l}  {xmm6} {xmm7l}  {xmm7} {xmm8l}  {xmm8}\n"
                    "{xmm9l}  {xmm9} {xmm10l} {xmm10} {xmm11l} {xmm11}\n"
                    "{xmm12l} {xmm12} {xmm13l} {xmm13} {xmm14l} {xmm14}\n"
                    "{xmm15l} {xmm15}\n"
                ),
                'fpu': (
                    "{st0l} {st0} {st1l} {st1} {st2l} {st2} {st3l} {st2}\n"
                    "{st4l} {st4} {st5l} {st5} {st6l} {st6} {st7l} {st7}\n"
                )
            },
            'vertical': {
                'general': (
                    "{rflags}\n{jump}\n"
                    "{ripl} {rip}\n"
                    "{raxl} {rax}\n{rbxl} {rbx}\n{rbpl} {rbp}\n{rspl} {rsp}\n"
                    "{rdil} {rdi}\n{rsil} {rsi}\n{rdxl} {rdx}\n{rcxl} {rcx}\n"
                    "{r8l} {r8}\n{r9l} {r9}\n{r10l} {r10}\n{r11l} {r11}\n{r12l} {r12}\n"
                    "{r13l} {r13}\n{r14l} {r14}\n{r15l} {r15}\n"
                    "{csl}  {cs}  {dsl}  {ds}\n{esl}  {es}  {fsl}  {fs}\n{gsl}  {gs}  {ssl}  {ss}"
                ),
                'sse': (
                    "{xmm0l}  {xmm0}\n{xmm1l}  {xmm1}\n{xmm2l}  {xmm2}\n{xmm3l}  {xmm3}\n"
                    "{xmm4l}  {xmm4}\n{xmm5l}  {xmm5}\n{xmm6l}  {xmm6}\n{xmm7l}  {xmm7}\n"
                    "{xmm8l}  {xmm8}\n{xmm9l}  {xmm9}\n{xmm10l} {xmm10}\n{xmm11l} {xmm11}\n"
                    "{xmm12l} {xmm12}\n{xmm13l} {xmm13}\n{xmm14l} {xmm14}\n{xmm15l} {xmm15}"
                ),
                'fpu': (
                    "{st0l} {st0}\n{st1l} {st1}\n{st2l} {st2}\n{st3l} {st2}\n"
                    "{st4l} {st4}\n{st5l} {st5}\n{st6l} {st6}\n{st7l} {st7}\n"
                )
            }
        },
        'x86': {
            'horizontal': {
                'general': (
                    "{eaxl} {eax}  {ebxl} {ebx}  {ebpl} {ebp}  {espl} {esp}  {eflags}\n"
                    "{edil} {edi}  {esil} {esi}  {edxl} {edx}  {ecxl} {ecx}  {eipl} {eip}\n"
                    "{csl} {cs}  {dsl} {ds}  {esl} {es}  {fsl} {fs}  {gsl} {gs}  {ssl} {ss} {jump}"
                ),
                'sse': (
                    "{xmm0l}  {xmm0} {xmm1l}  {xmm1} {xmm2l}  {xmm2}\n"
                    "{xmm3l}  {xmm3} {xmm4l}  {xmm4} {xmm5l}  {xmm5}\n"
                    "{xmm6l}  {xmm6} {xmm7l}"
                ),
                'fpu': (
                    "{st0l} {st0} {st1l} {st1} {st2l} {st2} {st3l} {st2}\n"
                    "{st4l} {st4} {st5l} {st5} {st6l} {st6} {st7l} {st7}\n"
                )
            },
            'vertical': {
                'general': (
                    "{eflags}\n{jump}\n"
                    "{eipl} {eip}\n"
                    "{eaxl} {eax}\n{ebxl} {ebx}\n{ebpl} {ebp}\n{espl} {esp}\n"
                    "{edil} {edi}\n{esil} {esi}\n{edxl} {edx}\n{ecxl} {ecx}\n"
                    "{csl}  {cs}\n{dsl}  {ds}\n{esl}  {es}\n{fsl}  {fs}\n{gsl}  {gs}\n{ssl}  {ss}"
                ),
                'sse': (
                    "{xmm0l}  {xmm0}\n{xmm1l}  {xmm1}\n{xmm2l}  {xmm2}\n{xmm3l}  {xmm3}\n"
                    "{xmm4l}  {xmm4}\n{xmm5l}  {xmm5}\n{xmm6l}  {xmm6}\n{xmm7l}  {xmm7}\n"
                ),
                'fpu': (
                    "{st0l} {st0}\n{st1l} {st1}\n{st2l} {st2}\n{st3l} {st2}\n"
                    "{st4l} {st4}\n{st5l} {st5}\n{st6l} {st6}\n{st7l} {st7}\n"
                )
            }
        },
        'arm': {
            'horizontal': {
                'general': (
                    "{pcl} {pc} {spl} {sp} {lrl} {lr} {cpsrl} {cpsr}\n"
                    "{r0l} {r0} {r1l} {r1} {r2l} {r2} {r3l} {r3} {r4l} {r4} {r5l} {r5} {r6l} {r6}\n"
                    "{r7l} {r7} {r8l} {r8} {r9l} {r9} {r10l} {r10} {r11l} {r11} {r12l} {r12}"
                ),
            },
            'vertical': {
                'general': (
                    "{pcl} {pc}\n{spl} {sp}\n{lrl} {lr}\n"
                    "{r0l} {r0}\n{r1l} {r1}\n{r2l} {r2}\n{r3l} {r3}\n{r4l} {r4}\n{r5l} {r5}\n{r6l} {r6}\n{r7l} {r7}\n"
                    "{r8l} {r8}\n{r9l} {r9}\n{r10l} {r10}\n{r11l} {r11}\n{r12l} {r12}\n{cpsrl}{cpsr}"
                ),
            }
        },
        'arm64': {
            'horizontal': {
                'general': (
                    "{pcl} {pc}\n{spl} {sp}\n"
                    "{x0l} {x0}\n{x1l} {x1}\n{x2l} {x2}\n{x3l} {x3}\n{x4l} {x4}\n{x5l} {x5}\n{x6l} {x6}\n{x7l} {x7}\n"
                    "{x8l} {x8}\n{x9l} {x9}\n{x10l} {x10}\n{x11l} {x11}\n{x12l} {x12}\n{x13l} {x13}\n{x14l} {x14}\n"
                    "{x15l} {x15}\n{x16l} {x16}\n{x17l} {x17}\n{x18l} {x18}\n{x19l} {x19}\n{x20l} {x20}\n{x21l} {x21}\n"
                    "{x22l} {x22}\n{x23l} {x23}\n{x24l} {x24}\n{x25l} {x25}\n{x26l} {x26}\n{x27l} {x27}\n{x28l} {x28}\n"
                    "{x29l} {x29}\n{x30l} {x30}\n"
                ),
            },
            'vertical': {
                'general': (
                    "{pcl} {pc}\n{spl} {sp}\n"
                    "{x0l} {x0}\n{x1l} {x1}\n{x2l} {x2}\n{x3l} {x3}\n{x4l} {x4}\n{x5l} {x5}\n{x6l} {x6}\n{x7l} {x7}\n"
                    "{x8l} {x8}\n{x9l} {x9}\n{x10l} {x10}\n{x11l} {x11}\n{x12l} {x12}\n{x13l} {x13}\n{x14l} {x14}\n"
                    "{x15l} {x15}\n{x16l} {x16}\n{x17l} {x17}\n{x18l} {x18}\n{x19l} {x19}\n{x20l} {x20}\n{x21l} {x21}\n"
                    "{x22l} {x22}\n{x23l} {x23}\n{x24l} {x24}\n{x25l} {x25}\n{x26l} {x26}\n{x27l} {x27}\n{x28l} {x28}\n"
                    "{x29l} {x29}\n{x30l} {x30}"
                ),
            }
        }
    }
    FLAG_BITS = {'c': 0, 'p': 2, 'a': 4, 'z': 6, 's': 7, 't': 8, 'i': 9, 'd': 10, 'o': 11}
    FLAG_TEMPLATE = "[ {o} {d} {i} {t} {s} {z} {a} {p} {c} ]"
    XMM_INDENT = 7
    last_regs = None
    last_flags = None

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('reg', help='register view')
        VoltronView.add_generic_arguments(sp)
        sp.set_defaults(func=RegisterView)
        g = sp.add_mutually_exclusive_group()
        g.add_argument('--horizontal', '-o',    dest="orientation", action='store_const',   const="horizontal", help='horizontal orientation')
        g.add_argument('--vertical', '-v',      dest="orientation", action='store_const',   const="vertical",   help='vertical orientation (default)')
        sp.add_argument('--general', '-g',      dest="sections",    action='append_const',  const="general",    help='show general registers')
        sp.add_argument('--no-general', '-G',   dest="sections",    action='append_const',  const="no_general", help='show general registers')
        sp.add_argument('--sse', '-s',          dest="sections",    action='append_const',  const="sse",        help='show sse registers')
        sp.add_argument('--no-sse', '-S',       dest="sections",    action='append_const',  const="no_sse",     help='show sse registers')
        sp.add_argument('--fpu', '-p',          dest="sections",    action='append_const',  const="fpu",        help='show fpu registers')
        sp.add_argument('--no-fpu', '-P',       dest="sections",    action='append_const',  const="no_fpu",     help='show fpu registers')

    def apply_cli_config(self):
        super(RegisterView, self).apply_cli_config()
        if self.args.orientation != None:
            self.config['orientation'] = self.args.orientation
        if self.args.sections != None:
            a = filter(lambda x: 'no_'+x not in self.args.sections and not x.startswith('no_'), self.config['sections'] + self.args.sections)
            self.config['sections'] = []
            for sec in a:
                if sec not in self.config['sections']:
                    self.config['sections'].append(sec)

    def render(self, msg=None, error=None):
        if msg != None:
            # Store current message
            self.curr_msg = msg

            # Build template
            template = '\n'.join(map(lambda x: self.TEMPLATES[msg['arch']][self.config['orientation']][x], self.config['sections']))

            # Process formatting settings
            data = defaultdict(lambda: 'n/a')
            data.update(msg['data']['regs'])
            inst = msg['data']['inst']
            formats = self.FORMAT_INFO[msg['arch']]
            formatted = {}
            for fmt in formats:
                # Apply defaults where they're missing
                fmt = dict(list(self.config['format_defaults'].items()) + list(fmt.items()))

                # Format the data for each register
                for reg in fmt['regs']:
                    # Format the label
                    label = fmt['label_format'].format(reg)
                    if fmt['label_func'] != None:
                        formatted[reg+'l'] = eval(fmt['label_func'])(str(label))
                    if fmt['label_colour_en']:
                        formatted[reg+'l'] =  self.colour(formatted[reg+'l'], fmt['label_colour'])

                    # Format the value
                    val = data[reg]
                    if type(val) == str:
                        temp = fmt['value_format'].format(0)
                        if len(val) < len(temp):
                            val += (len(temp) - len(val))*' '
                        formatted_reg = self.colour(val, fmt['value_colour'])
                    else:
                        colour = fmt['value_colour']
                        if self.last_regs == None or self.last_regs != None and val != self.last_regs[reg]:
                            colour = fmt['value_colour_mod']
                        formatted_reg = val
                        if fmt['value_format'] != None:
                            formatted_reg = fmt['value_format'].format(formatted_reg)
                        if fmt['value_func'] != None:
                            if type(fmt['value_func']) == str:
                                formatted_reg = eval(fmt['value_func'])(formatted_reg)
                            else:
                                formatted_reg = fmt['value_func'](formatted_reg)
                        if fmt['value_colour_en']:
                            formatted_reg = self.colour(formatted_reg, colour)
                    if fmt['format_name'] == None:
                        formatted[reg] = formatted_reg
                    else:
                        formatted[fmt['format_name']] = formatted_reg

            # Prepare output
            log.debug('Formatted: ' + str(formatted))
            self.body = template.format(**formatted)

            # Store the regs
            self.last_regs = data

        # Prepare headers and footers
        height, width = self.window_size()
        self.title = '[regs:{}]'.format('|'.join(self.config['sections']))
        if len(self.title) > width:
            self.title = '[regs]'

        # Set body to error message if appropriate
        if msg == None and error != None:
            self.body = self.colour(error, 'red')

        # Pad the body
        self.pad_body()

        # Call parent's render method
        super(RegisterView, self).render()

    def format_flags(self, val):
        values = {}

        # Get formatting info for flags
        if self.curr_msg['arch'] == 'x64':
            reg = 'rflags'
        elif self.curr_msg['arch'] == 'x86':
            reg = 'eflags'
        fmt = dict(list(self.config['format_defaults'].items()) + list(list(filter(lambda x: reg in x['regs'], self.FORMAT_INFO[self.curr_msg['arch']]))[0].items()))

        # Handle each flag bit
        val = int(val, 10)
        formatted = {}
        for flag in self.FLAG_BITS.keys():
            values[flag] = (val & (1 << self.FLAG_BITS[flag]) > 0)
            log.debug("Flag {} value {} (for flags 0x{})".format(flag, values[flag], val))
            formatted[flag] = str.upper(flag) if values[flag] else flag
            if self.last_flags != None and self.last_flags[flag] != values[flag]:
                colour = fmt['value_colour_mod']
            else:
                colour = fmt['value_colour']
            formatted[flag] = self.colour(formatted[flag], colour)

        # Store the flag values for comparison
        self.last_flags = values

        # Format with template
        flags = self.FLAG_TEMPLATE.format(**formatted)

        return flags

    def format_jump(self, val):
        # Grab flag bits
        val = int(val, 10)
        values = {}
        for flag in self.FLAG_BITS.keys():
            values[flag] = (val & (1 << self.FLAG_BITS[flag]) > 0)

        # If this is a jump instruction, see if it will be taken
        inst = self.curr_msg['data']['inst'].split()[0]
        j = None
        if inst in ['ja', 'jnbe']:
            if not values['c'] and not values['z']:
                j = (True, '!c && !z')
            else:
                j = (False, 'c || z')
        elif inst in ['jae', 'jnb', 'jnc']:
            if not values['c']:
                j = (True, '!c')
            else:
                j = (False, 'c')
        elif inst in ['jb', 'jc', 'jnae']:
            if values['c']:
                j = (True, 'c')
            else:
                j = (False, '!c')
        elif inst in ['jbe', 'jna']:
            if values['c'] or values['z']:
                j = (True, 'c || z')
            else:
                j = (False, '!c && !z')
        elif inst in ['jcxz', 'jecxz', 'jrcxz']:
            if self.get_arch() == 'x64':
                cx = regs['rcx']
            elif self.get_arch() == 'x86':
                cx = regs['ecx']
            if cx == 0:
                j = (True, cx+'==0')
            else:
                j = (False, cx+'!=0')
        elif inst in ['je', 'jz']:
            if values['z']:
                j = (True, 'z')
            else:
                j = (False, '!z')
        elif inst in ['jnle', 'jg']:
            if not values['z'] and values['s'] == values['o']:
                j = (True, '!z && s==o')
            else:
                j = (False, 'z || s!=o')
        elif inst in ['jge', 'jnl']:
            if values['s'] == values['o']:
                j = (True, 's==o')
            else:
                j = (False, 's!=o')
        elif inst in ['jl', 'jnge']:
            if values['s'] == values['o']:
                j = (False, 's==o')
            else:
                j = (True, 's!=o')
        elif inst in ['jle', 'jng']:
            if values['z'] or values['s'] == values['o']:
                j = (True, 'z || s==o')
            else:
                j = (False, '!z && s!=o')
        elif inst in ['jne', 'jnz']:
            if not values['z']:
                j = (True, '!z')
            else:
                j = (False, 'z')
        elif inst in ['jno']:
            if not values['o']:
                j = (True, '!o')
            else:
                j = (False, 'o')
        elif inst in ['jnp', 'jpo']:
            if not values['p']:
                j = (True, '!p')
            else:
                j = (False, 'p')
        elif inst in ['jns']:
            if not values['s']:
                j = (True, '!s')
            else:
                j = (False, 's')
        elif inst in ['jo']:
            if values['o']:
                j = (True, 'o')
            else:
                j = (False, '!o')
        elif inst in ['jp', 'jpe']:
            if values['p']:
                j = (True, 'p')
            else:
                j = (False, '!p')
        elif inst in ['js']:
            if values['s']:
                j = (True, 's')
            else:
                j = (False, '!s')

        # Construct message
        if j != None:
            taken, reason = j
            if taken:
                jump = 'Jump ({})'.format(reason)
            else:
                jump = '!Jump ({})'.format(reason)
        else:
            jump = ''

        # Pad out
        height, width = self.window_size()
        t = '{:^%d}' % (width - 2)
        jump = t.format(jump)

        # Colour
        if j != None:
            jump = self.colour(jump, self.config['format_defaults']['value_colour_mod'])
        else:
            jump = self.colour(jump, self.config['format_defaults']['value_colour'])

        return '[' + jump + ']'

    def format_xmm(self, val):
        if self.config['orientation'] == 'vertical':
            height, width = self.window_size()
            if width < len(SHORT_ADDR_FORMAT_128.format(0)) + self.XMM_INDENT:
                return val[:16] + '\n' + ' '*self.XMM_INDENT + val[16:]
            else:
                return val[:16] +  ':' + val[16:]
        else:
            return val

    def format_fpu(self, val):
        if self.config['orientation'] == 'vertical':
            return val
        else:
            return val

class DisasmView (TerminalView):
    view_type = 'disasm'

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('disasm', help='disassembly view')
        VoltronView.add_generic_arguments(sp)
        sp.set_defaults(func=DisasmView)

    def render(self, msg=None, error=None):
        height, width = self.window_size()

        # Set up header & error message if applicable
        self.title = '[code]'
        if error != None:
            self.body = self.colour(error, 'red')

        if msg != None:
            # Get the disasm
            disasm = msg['data']
            disasm = '\n'.join(disasm.split('\n')[:self.body_height()])

            # Pygmentize output
            if have_pygments:
                try:
                    lexer = pygments.lexers.get_lexer_by_name('gdb')
                    disasm = pygments.highlight(disasm, lexer, pygments.formatters.Terminal256Formatter())
                except Exception as e:
                    log.warning('Failed to highlight disasm: ' + str(e))

            # Build output
            self.body = disasm.rstrip()

        # Call parent's render method
        super(DisasmView, self).render()


class StackView (TerminalView):
    view_type = 'stack'

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('stack', help='stack view')
        VoltronView.add_generic_arguments(sp)
        sp.add_argument('--bytes', '-b', action='store', type=int, help='bytes per line (default 16)', default=16)
        sp.set_defaults(func=StackView)

    def render(self, msg=None, error=None):
        height, width = self.window_size()

        # Set up header and error message if applicable
        self.title = "[stack]"
        if error != None:
            self.body = self.colour(error, 'red')
            self.pad_body()

        if msg != None:
            # Get the stack data
            data = msg['data']
            stack_raw = data['data']
            sp = data['sp']
            stack_raw = stack_raw[:(self.body_height())*self.args.bytes]

            # Hexdump it
            lines = self.hexdump(stack_raw, offset=sp, length=self.args.bytes).split('\n')
            lines.reverse()
            stack = '\n'.join(lines)

            # Build output
            self.info = '[0x{0:0=4x}:'.format(len(stack_raw)) + ADDR_FORMAT_64.format(sp) + ']'
            self.body = stack.strip()

        # Call parent's render method
        super(StackView, self).render()


class BacktraceView (TerminalView):
    view_type = 'bt'

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('bt', help='backtrace view')
        VoltronView.add_generic_arguments(sp)
        sp.set_defaults(func=BacktraceView)

    def render(self, msg=None, error=None):
        height, width = self.window_size()

        # Set up header and error message if applicable
        self.title = '[backtrace]'
        if error != None:
            self.body = self.colour(error, 'red')

        if msg != None:
            # Get the back trace data
            data = msg['data']

            # Build output
            self.body = data.strip()

        # Pad body
        self.pad_body()

        # Call parent's render method
        super(BacktraceView, self).render()


class CommandView (TerminalView):
    view_type = 'cmd'

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('cmd', help='command view - specify a command to be run each time the debugger stops')
        VoltronView.add_generic_arguments(sp)
        sp.add_argument('command', action='store', help='command to run')
        sp.set_defaults(func=CommandView)

    def setup(self):
        self.config['cmd'] = self.args.command

    def render(self, msg=None, error=None):
        # Set up header and error message if applicable
        self.title = '[cmd:' + self.config['cmd'] + ']'
        if error != None:
            self.body = self.colour(error, 'red')

        if msg != None:
            # Get the command output
            data = msg['data']
            lines = data.split('\n')
            pad = self.body_height() - len(lines) + 1
            if pad < 0:
                pad = 0

            # Build output
            self.body = data.rstrip() + pad*'\n'

        # Call parent's render method
        super(CommandView, self).render()


########NEW FILE########
