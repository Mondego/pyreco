__FILENAME__ = console
from . import Event, get_timestamp
from ..shared import console_repr


class Console(Event):
    contains = ('line', 'time', 'user', 'source', 'kind', 'data', 'level')
    requires = ('line',)

    line  = Event.Arg(required=True)
    kind  = Event.Arg()
    time  = Event.Arg()
    user  = Event.Arg(default='')
    source = Event.Arg(default='mark2')
    data  = Event.Arg()
    level = Event.Arg()
    
    def setup(self):
        if not self.time:
            self.time = get_timestamp(self.time)
        if not self.data:
            self.data = self.line
        
    def value(self):
        return console_repr(self)

########NEW FILE########
__FILENAME__ = error
from . import Event


class Error(Event):
    pass


class FatalError(Event):
    exception = Event.Arg()
    reason    = Event.Arg()

########NEW FILE########
__FILENAME__ = hook
from . import Event


class Hook(Event):
    name       = Event.Arg()
    is_command = Event.Arg()
    args       = Event.Arg()
    line       = Event.Arg()
    
    def setup(self):
        if not self.name:
            if self.line:
                t = self.line.split(" ", 1)
                
                self.name = t[0][1:]
                self.is_command = True
                if len(t) == 2:
                    self.args = t[1]
    
    def prefilter(self, name, public=False, doc=None):
        if name != self.name:
            return False
        
        if self.is_command and not public:
            return False
        
        return True
    

########NEW FILE########
__FILENAME__ = player
from . import Event


class PlayerEvent(Event):
    def setup(s):
        s.username = s.username.encode('ascii')


#Raised in manager

class PlayerJoin(PlayerEvent):
    username = Event.Arg(required=True)
    ip       = Event.Arg(required=True)

class PlayerQuit(PlayerEvent):
    username = Event.Arg(required=True)
    reason   = Event.Arg(required=True)


class PlayerChat(PlayerEvent):
    username = Event.Arg(required=True)
    message  = Event.Arg(required=True)


class PlayerDeath(PlayerEvent):
    text     = Event.Arg()
    username = Event.Arg(required=True)
    cause    = Event.Arg(required=True)
    killer   = Event.Arg()
    weapon   = Event.Arg()
    format   = Event.Arg(default="{username} died")

    def get_text(self, **kw):
        d = dict(((k, getattr(self, k)) for k in ('username', 'killer', 'weapon')))
        d.update(kw)
        return self.format.format(**d)

    def setup(self):
        self.text = self.get_text()

########NEW FILE########
__FILENAME__ = server
import re

from . import Event, get_timestamp

# input/output
output_exp = re.compile(
        r'^(?:\d{4}-\d{2}-\d{2} |)\[?(\d{2}:\d{2}:\d{2})\]? \[?(?:[^\]]+?/|)([A-Z]+)\]:? (.*)')

class ServerInput(Event):
    """Send data to the server's stdin. In plugins, a shortcut
    is available: self.send("say hello")"""
    
    line         = Event.Arg(required=True)


class ServerOutput(Event):
    """Issued when the server gives us a line on stdout. Note
    that to handle this, you must specify both the 'level'
    (e.g. INFO or SEVERE) and a regex pattern to match"""
    
    line  = Event.Arg(required=True)
    time  = Event.Arg()
    level = Event.Arg()
    data  = Event.Arg()
    
    def setup(self):
        m = output_exp.match(self.line)
        if m:
            g = m.groups()
            self.time = g[0]
            self.level= g[1]
            self.data = g[2]
        else:
            self.level= "???"
            self.data = self.line.strip()
        
        self.time = get_timestamp(self.time)
    
    def prefilter(self, pattern, level=None):
        if level and level != self.level:
            return False
        
        m = re.match(pattern, self.data)
        if not m:
            return False
        
        self.match = m
        
        return True
    
# start


class ServerStart(Event):
    """Issue this event to start the server"""
    
    pass


class ServerStarting(Event):
    """Issued by the ServerStart handler to alert listening plugins
    that the server process has started"""
    
    pid = Event.Arg()


class ServerStarted(Event):
    """Issued when we see the "Done! (1.23s)" line from the server
    
    This event has a helper method in plugins - just overwrite
    the server_started method.
    """


class ServerStop(Event):
    """Issue this event to stop the server."""
    
    reason   = Event.Arg(required=True)
    respawn  = Event.Arg(required=True)
    kill     = Event.Arg(default=False)
    announce = Event.Arg(default=True)

    dispatch_once = True


class ServerStopping(Event):
    """Issued by the ServerStop handler to alert listening plugins
    that the server is going for a shutdown
    
    This event has a helper method in plugins - just overwrite
    the server_started method."""

    reason  = Event.Arg(required=True)
    respawn = Event.Arg(required=True)
    kill    = Event.Arg(default=False)


class ServerStopped(Event):
    """When the server process finally dies, this event is raised"""
    pass


class ServerEvent(Event):
    """Tell plugins about something happening to the server"""

    cause    = Event.Arg(required=True)
    friendly = Event.Arg()
    data     = Event.Arg(required=True)
    priority = Event.Arg(default=0)
    
    def setup(self):
        if not self.friendly:
            self.friendly = self.cause

########NEW FILE########
__FILENAME__ = stat
from . import Event


class StatEvent(Event):
    source = Event.Arg()


#provider: ping
class StatPlayerCount(StatEvent):
    players_current = Event.Arg(required=True)
    players_max     = Event.Arg(required=True)


#provider: console tracking
class StatPlayers(StatEvent):
    players = Event.Arg(required=True)


#provider: psutil
class StatProcess(StatEvent):
    cpu    = Event.Arg(required=True)
    memory = Event.Arg(required=True)

########NEW FILE########
__FILENAME__ = user
from . import Event

#All these are raised in user_server

class UserInput(Event):
    user = Event.Arg(required=True)
    line = Event.Arg(required=True)

class UserAttach(Event):
    user = Event.Arg(required=True)

class UserDetach(Event):
    user = Event.Arg(required=True)

########NEW FILE########
__FILENAME__ = launcher
import re
import os
import sys
import glob
import stat
import time
import errno

#start:
import subprocess
import getpass
import pwd
import tempfile
from . import manager

#config:
from .shared import find_config, open_resource

#attach:
from . import user_client

#send/stop/kill
import json
import socket

#jar-list/jar-get
from . import servers
from twisted.internet import reactor

usage_text = "usage: mark2 command [options] [...]"

help_text = """
mark2 is a minecraft server wrapper

{usage}

commands:
{commands}

examples:
  mark2 start /home/you/mcservers/pvp
  mark2 attach
  mark2 send say hello!
  mark2 stop
"""

help_sub_text = """
mark2 {subcommand}: {doc}

usage: mark2 {subcommand} {value_spec}
"""


class Mark2Error(Exception):
    def __init__(self, error):
        self.error = error

    def __str__(self):
        return "error: %s" % self.error


class Mark2ParseError(Mark2Error):
    def __str__(self):
        return "%s\nparse error: %s" % (usage_text, self.error)


class Command(object):
    name = ""
    value_spec = ""
    options_spec = tuple()
    def __init__(self):
        pass

    def do_start(self):
        pass

    def do_end(self):
        pass

    @classmethod
    def get_bases(cls):
        o = []
        while True:
            cls = cls.__bases__[0]
            if cls is object:
                break
            o.append(cls)
        return o

    @classmethod
    def get_options_spec(cls):
        return sum([list(b.options_spec) for b in [cls] + cls.get_bases()[::-1]], [])

    def parse_options(self, c_args):
        options = {}
        options_tys = {}
        #transform
        for opt in self.__class__.get_options_spec():
            for flag in opt[1]:
                options_tys[flag] = opt

        while len(c_args) > 0:
            head = c_args[0]

            if head[0] != '-':
                break
            elif head == '--':
                c_args.pop(0)
                break
            elif head in options_tys:
                opt = options_tys[c_args.pop(0)]
                try:
                    options[opt[0]] = c_args.pop(0) if opt[2] != '' else True
                except IndexError:
                    raise Mark2ParseError("option `%s` missing argument" % opt[0])
            else:
                raise Mark2Error("%s: unknown option %s" % (self.name, head))

        self.options = options
        self.value = ' '.join(c_args) if len(c_args) else None

    def start(self):
        bases = self.__class__.get_bases()
        for b in bases[::-1]:
            b.do_start(self)
        self.run()
        for b in bases:
            b.do_end(self)

    def run(self):
        raise NotImplementedError


class CommandTyStateful(Command):
    options_spec = (('base', ('-b', '--base'), 'PATH',  'the directory to put mark2-related temp files (default: /tmp/mark2)'),)

    def do_start(self):
        self.shared_path = self.options.get('base', '/tmp/mark2')
        self.make_writable(self.shared_path)

        #get servers
        o = []
        for path in glob.glob(self.shared('pid', '*')):
            with open(path) as fp:
                pid = int(fp.read())
                try:
                    os.kill(pid, 0)
                except OSError as err:
                    if err.errno == errno.ESRCH:
                        os.remove(path)
                        continue
            f = os.path.basename(path)
            f = os.path.splitext(f)[0]
            o.append(f)

        self.servers = sorted(o)

    def shared(self, ty, name=None):
        if name is None:
            name = self.server_name
        return os.path.join(self.shared_path, "%s.%s" % (name, ty))

    def make_writable(self, directory):
        need_modes = stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH | stat.S_IRWXG | stat.S_IRWXO
        good_modes = stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO | stat.S_ISVTX

        if not os.path.exists(directory):
            os.makedirs(directory, good_modes)

        st = os.stat(directory)
        if (st.st_mode & need_modes) == need_modes:
            return True

        try:
            os.chmod(directory, good_modes)
            return True
        except Exception:
            raise Mark2Error('%s does not have the necessary modes to run mark2 and I do not have permission to change them!' % directory)


class CommandTySelective(CommandTyStateful):
    options_spec = (('name', ('-n', '--name'), 'NAME',  'create or select a server with this name'),)

    name_should_exist = True
    server_name = None

    def do_start(self):
        name = self.options.get('name', None)
        if self.name_should_exist:
            if name is None:
                if len(self.servers) > 0:
                    name = self.servers[0]
                else:
                    raise Mark2Error("no servers running!")
            elif name not in self.servers:
                raise Mark2Error("server not running: %s" % name)
        else:
            if name is None:
                pass #CommandStart will fill it.
            elif name in self.servers:
                raise Mark2Error("server already running: %s" % name)

        self.server_name = name

    def do_send(self, data):
        d = {
            'type': 'input',
            'user': '@external',
            'line': data
        }
        d = json.dumps(d) + "\n"

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(self.shared('sock'))
        s.send(d)
        s.close()


class CommandTyTerminal(CommandTySelective):
    options_spec = (
        ('wait', ('-w', '--wait'), 'REGEX', 'wait for this line of output to appear on console before returning.'),
        ('only', ('-o', '--only'), '',      'print the matched line and no others'),
        ('immediate', ('-i', '--immediate'), '', 'don\'t wait for any output'))

    wait = None
    wait_from_start = False
    only = False
    def do_end(self):
        if 'wait' in self.options:
            self.wait = self.options['wait']
        if 'only' in self.options:
            self.only = True
        if 'immediate' in self.options:
            self.wait = None

        try:
            self.do_wait()
        except KeyboardInterrupt:
            pass

    def do_wait(self):
        if self.wait is None:
            return
        while not os.path.exists(self.shared('log')):
            time.sleep(0.1)
        with open(self.shared('log'), 'r') as f:
            if not self.wait_from_start:
                f.seek(0,2)
            while True:
                line = f.readline().rstrip()
                if not line:
                    time.sleep(0.1)
                    continue

                if line[0] in (" ", "\t"):
                    print line
                    continue

                line = line.split(" ", 3)
                if line[2] == '[mark2]':
                    line2 = line[3].split(" ", 2)
                    if re.search(self.wait, line2[2]):
                        print line[3]
                        return
                    elif not self.only:
                        print line[3]


class CommandHelp(Command):
    """display help and available options"""
    name = 'help'
    value_spec = "[COMMAND]"
    def run(self):
        if self.value is None:
            print help_text.format(
                usage=usage_text,
                commands=self.columns([(c.name, c.value_spec, c.__doc__) for c in commands]))
        elif self.value in commands_d:
            cls = commands_d[self.value]
            print help_sub_text.format(
                subcommand = self.value,
                doc = cls.__doc__,
                value_spec = cls.value_spec
            )
            opts = cls.get_options_spec()
            if len(opts) > 0:
                print "options:"
                print self.columns([(' '.join(o[1]), o[2], o[3]) for o in opts]) + "\n"
        else:
            raise Mark2Error("Unknown command: %s" % self.value)

    def columns(self, data):
        o = []
        for tokens in data:
            line = ""
            for i, token in enumerate(tokens):
                line += token
                line += " "*(((i+1)*12)-len(line))
            o.append(line)

        return "\n".join(("  "+l for l in o))


class CommandStart(CommandTyTerminal):
    """start a server"""
    name = 'start'
    value_spec='[PATH]'
    name_should_exist = False

    def get_server_path(self):
        self.jar_file = None
        self.server_path = os.path.realpath("" if self.value is None else self.value)

        if os.path.isdir(self.server_path):
            pass
        elif os.path.isfile(self.server_path):
            if self.server_path.endswith('.jar'):
                self.server_path, self.jar_file = os.path.split(self.server_path)
            else:
                raise Mark2Error("unknown file type: " + self.server_path)
        else:
            raise Mark2Error("path does not exist: " + self.server_path)

    def check_config(self):
        new_cfg = find_config('mark2.properties', ignore_errors=True)
        if os.path.exists(new_cfg):
            return
        if os.path.exists(os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'config'))):
            new_dir = os.path.dirname(new_cfg)
            raise Mark2Error("mark2's configuration location has changed! move your config files to {0}".format(new_dir))
        else:
            raise Mark2Error("mark2 is unconfigured! run `mark2 config`")

    def check_ownership(self):
        d_user = pwd.getpwuid(os.stat(self.server_path).st_uid).pw_name
        m_user = getpass.getuser()
        if d_user != m_user:
            e = "server directory is owned by '{d_user}', but mark2 is running as '{m_user}'. " + \
                "please start mark2 as `sudo -u {d_user} mark2 start ...`"
            raise Mark2Error(e.format(d_user=d_user,m_user=m_user))

    def daemonize(self):
        if os.fork() > 0:
            return 1

        os.chdir(".")
        os.setsid()
        os.umask(0)

        if os.fork() > 0:
            sys.exit(0)

        null = os.open('/dev/null', os.O_RDWR)
        for fileno in (1, 2, 3):
            try:
                os.dup2(null, fileno)
            except:
                pass

        return 0

    def run(self):
        # parse the server path
        self.get_server_path()

        # get server name
        if self.server_name is None:
            self.server_name = os.path.basename(self.server_path)
            if self.server_name in self.servers:
                raise Mark2Error("server already running: %s" % self.server_name)

        # check for mark2.properties
        self.check_config()

        # check we own the server dir
        self.check_ownership()

        # clear old stuff
        for x in ('log', 'sock', 'pid'):
            if os.path.exists(self.shared(x)):
                os.remove(self.shared(x))

        i = 1
        while True:
            p = self.shared("log.%d" % i)
            if not os.path.exists(p):
                break
            os.remove(p)
            i += 1

        if self.daemonize() == 0:
            with open(self.shared('pid'), 'w') as f:
                f.write("{0}\n".format(os.getpid()))

            mgr = manager.Manager(self.shared_path, self.server_name, self.server_path, self.jar_file)
            reactor.callWhenRunning(mgr.startup)
            reactor.run()

            sys.exit(0)

        self.wait = '# mark2 started|stopped\.'
        self.wait_from_start = True


class CommandConfig(Command):
    """configure mark2"""
    options_spec = (('ask', ('-a', '--ask'), '', 'Ask before starting an editor'),)
    name = 'config'

    def check_executable(self, cmd):
        return subprocess.call(
            ["command", "-v", cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        ) == 0

    def copy_config(self, src, dest, header=''):
        f0 = src
        f1 = dest
        l0 = ''

        while l0.strip() == '' or l0.startswith('### ###'):
            l0 = f0.readline()

        f1.write(header)

        while l0 != '':
            f1.write(l0)
            l0 = f0.readline()

        f0.close()
        f1.close()

    def diff_config(self, src, dest):
        diff = ""

        d0 = src.readlines()
        d1 = dest.readlines()

        import difflib
        ignore = " \t\f\r\n"
        s = difflib.SequenceMatcher(lambda x: x in ignore, d0, d1)
        for tag, i0, i1, j0, j1 in s.get_opcodes():
            if tag in ('replace', 'insert'):
                for l1 in d1[j0:j1]:
                    if l1.strip(ignore) != '':
                        diff += l1

        return diff

    def run(self):
        path_old = 'resources/mark2.default.properties'
        path_new = find_config('mark2.properties')

        def write_config(data=''):
            data = "# see resources/mark2.default.properties for details\n" + data
            with open(path_new, 'w') as file_new:
                file_new.write(data)

        if "MARK2_TEST" not in os.environ and self.options.get('ask', False):
            response = raw_input('would you like to configure mark2 now? [yes] ') or 'yes'
            if response != 'yes':
                return write_config() if not os.path.exists(path_new) else None

        editors = ["editor", "nano", "vim", "vi", "emacs"]
        if "EDITOR" in os.environ:
            editors.insert(0, os.environ["EDITOR"])
        for editor in editors:
            if self.check_executable(editor):
                break
        else:
            if not os.path.exists(path_new):
                write_config()
            raise Mark2Error("no editor found. please set the $EDITOR environment variable.")

        if os.path.exists(path_new):
            subprocess.call([editor, path_new])
        else:
            #launch our editor
            fd_tmp, path_tmp = tempfile.mkstemp(prefix='mark2.properties.', text=True)
            with open_resource(path_old) as src:
                with open(path_tmp, 'w') as dst:
                    self.copy_config(src, dst)
            subprocess.call([editor, path_tmp])

            #diff the files
            with open_resource(path_old) as src:
                with open(path_tmp, 'r') as dst:
                    write_config(self.diff_config(src, dst))
            os.remove(path_tmp)


class CommandList(CommandTyStateful):
    """list running servers"""
    name = 'list'
    def run(self):
        for s in self.servers:
            print s


class CommandAttach(CommandTySelective):
    """attach to a server"""
    name = 'attach'
    def run(self):
        f = user_client.UserClientFactory(self.server_name, self.shared_path)
        f.main()


class CommandStop(CommandTyTerminal):
    """stop mark2"""
    name = 'stop'
    def run(self):
        self.do_send('~stop')
        self.wait='# mark2 stopped\.'


class CommandKill(CommandTyTerminal):
    """kill mark2"""
    name = 'kill'
    def run(self):
        self.do_send('~kill')
        self.wait = '# mark2 stopped\.'


class CommandSend(CommandTyTerminal):
    """send a console command"""
    name = 'send'
    value_spec='INPUT...'
    def run(self):
        if self.value is None:
            raise Mark2ParseError("nothing to send!")
        self.do_send(self.value)


class CommandJarList(Command):
    """list server jars"""
    name = 'jar-list'

    def run(self):
        def err(what):
            if reactor.running: reactor.stop()
            print "error: %s" % what.value

        def handle(listing):
            if reactor.running: reactor.stop()
            if len(listing) == 0:
                print "error: no server jars found!"
            else:
                print "The following server jars/zips are available:"
            print listing

        def start():
            d = servers.jar_list()
            d.addCallbacks(handle, err)

        reactor.callWhenRunning(start)

        reactor.run()


class CommandJarGet(Command):
    """download a server jar"""
    name = 'jar-get'
    value_spec = 'NAME'

    def run(self):
        if self.value is None:
            raise Mark2ParseError("missing jar type!")

        def err(what):
            #reactor.stop()
            print "error: %s" % what.value

        def handle((filename, data)):
            reactor.stop()
            if os.path.exists(filename):
                print "error: %s already exists!" % filename
            else:
                f = open(filename, 'wb')
                f.write(data)
                f.close()
                print "success! saved as %s" % filename

        def start():
            d = servers.jar_get(self.value)
            d.addCallbacks(handle, err)

        reactor.callWhenRunning(start)

        reactor.run()


commands = (CommandHelp, CommandStart, CommandList, CommandAttach, CommandStop, CommandKill, CommandSend, CommandJarList, CommandJarGet, CommandConfig)
commands_d = dict([(c.name, c) for c in commands])


def main():
    try:
        c_args = sys.argv[1:]
        if len(c_args) == 0:
            command_name = 'help'
        else:
            command_name = c_args.pop(0)
        command_cls = commands_d.get(command_name, None)
        if command_cls is None:
            raise Mark2ParseError("unknown command: %s" % command_name)
        command = command_cls()

        command.parse_options(c_args)
        command.start()

        return 0
    except Mark2Error as e:
        print e

        return 1

########NEW FILE########
__FILENAME__ = manager
import os
import traceback
import signal

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.python import log, logfile

#mark2 things
from . import events, properties, plugins
from .events import EventPriority
from .services import process
from .shared import find_config, open_resource

"""

This is the 'main' class that handles most of the logic

"""


class Manager(object):
    name = "manager"
    started = False
    shutting_down = False
    
    def __init__(self, shared_path, server_name, server_path, jar_file=None):
        self.shared_path = shared_path
        self.server_name = server_name
        self.server_path = server_path
        self.jar_file = jar_file
        self.players = set()

    def startup(self):
        reactor.addSystemEventTrigger('before', 'shutdown', self.before_reactor_stop)

        try:
            self.really_start()
        except Exception:
            for l in traceback.format_exc().split("\n"):
                print l
                self.console(l, kind='error')
            self.shutdown()

    def before_reactor_stop(self):
        self.console("mark2 stopped.")

    def really_start(self):
        #start event dispatcher
        self.events = events.EventDispatcher(self.handle_dispatch_error)

        #add some handlers
        self.events.register(self.handle_server_output, events.ServerOutput,  priority=EventPriority.MONITOR, pattern="")
        self.events.register(self.handle_console,       events.Console,       priority=EventPriority.MONITOR)
        self.events.register(self.handle_fatal,         events.FatalError,    priority=EventPriority._HIGH)
        self.events.register(self.handle_server_started,events.ServerStarted, priority=EventPriority.MONITOR)
        self.events.register(self.handle_user_attach,   events.UserAttach,    priority=EventPriority.MONITOR)
        self.events.register(self.handle_user_detach,   events.UserDetach,    priority=EventPriority.MONITOR)
        self.events.register(self.handle_user_input,    events.UserInput,     priority=EventPriority.MONITOR)
        self.events.register(self.handle_player_join,   events.PlayerJoin,    priority=EventPriority.MONITOR)
        self.events.register(self.handle_player_quit,   events.PlayerQuit,    priority=EventPriority.MONITOR)
        self.events.register(self.handle_server_stopped,events.ServerStopped, priority=EventPriority.MONITOR)

        #change to server directory
        os.chdir(self.server_path)

        #load config
        self.load_config()

        #start logging
        self.start_logging()

        #chmod log and pid
        for ext in ('log', 'pid'):
            os.chmod(os.path.join(self.shared_path, "%s.%s" % (self.server_name, ext)), self.config.get_umask(ext))

        self.console("mark2 starting...")

        #find jar file
        if self.jar_file is None:
            self.jar_file = process.find_jar(
                self.config['mark2.jar_path'].split(';'),
                self.jar_file)
            if self.jar_file is None:
                return self.fatal_error("Couldn't find server jar!")

        #load server.properties
        self.properties = properties.load(properties.Mark2Properties, open_resource('resources/server.default.properties'), 'server.properties')
        if self.properties is None:
            return self.fatal_error(reason="couldn't find server.properties")

        self.socket = os.path.join(self.shared_path, "%s.sock" % self.server_name)
        
        self.services = plugins.PluginManager(self,
                                              search_path='services',
                                              name='service',
                                              get_config=self.get_service_config)
        for name in self.services.find():
            cfg = self.get_service_config(name)
            if not cfg.get('enabled', True):
                continue
            result = self.services.load(name)
            if not result:
                return self.fatal_error(reason="couldn't load service: '{0}'".format(name))

        #load plugins
        self.plugins = plugins.PluginManager(self,
                                             search_path='plugins',
                                             name='plugin',
                                             get_config=self.get_plugin_config,
                                             require_config=True)
        self.load_plugins()

        #start the server
        self.events.dispatch(events.ServerStart())

    def handle_dispatch_error(self, event, callback, failure):
        o  = "An event handler threw an exception: \n"
        o += "  Callback: %s\n" % callback
        o += "  Event: \n"
        o += "".join(("    %s: %s\n" % (k, v) for k, v in event.serialize().iteritems()))

        # log the message and a very verbose exception log to the log file
        log.msg(o)
        failure.printDetailedTraceback()

        # log a less verbose exception to the console
        o += "\n".join("  %s" % l for l in failure.getTraceback().split("\n"))
        self.console(o)

    #helpers
    def start_logging(self):
        log_rotate = self.config['mark2.log.rotate_mode']
        log_size   = self.config['mark2.log.rotate_size']
        log_limit  = self.config['mark2.log.rotate_limit']
        if log_rotate == 'daily':
            log_obj = logfile.DailyLogFile("%s.log" % self.server_name, self.shared_path)
        elif log_rotate in ('off', 'size'):
            log_obj = logfile.LogFile("%s.log" % self.server_name, self.shared_path,
                                      rotateLength=log_size if log_rotate == 'size' else None,
                                      maxRotatedFiles=log_limit if log_limit != "" else None)
        else:
            raise ValueError("mark2.log.rotate-mode is invalid.")

        log.startLogging(log_obj)

    def load_config(self):
        self.config = properties.load(properties.Mark2Properties,
                                      open_resource('resources/mark2.default.properties'),
                                      find_config('mark2.properties'),
                                      'mark2.properties')
        if self.config is None:
            return self.fatal_error(reason="couldn't find mark2.properties")

    def get_plugin_config(self, name):
        return dict(self.config.get_plugins()).get(name, {})

    def get_service_config(self, name):
        return dict(self.config.get_service(name))

    def load_plugins(self):
        for name, _ in self.config.get_plugins():
            self.plugins.load(name)
    
    def shutdown(self):
        if not self.shutting_down:
            self.shutting_down = True
            reactor.callInThread(lambda: os.kill(os.getpid(), signal.SIGINT))

    def console(self, line, **k):
        for l in unicode(line).split(u"\n"):
            k['line'] = l
            self.events.dispatch(events.Console(**k))
    
    def fatal_error(self, *a, **k):
        k.setdefault('reason', a[0] if a else None)
        self.events.dispatch(events.FatalError(**k))
    
    def send(self, line):
        self.events.dispatch(events.ServerInput(line=line))
            
    #handlers
    def handle_server_output(self, event):
        self.events.dispatch(events.Console(source='server',
                                            line=event.line,
                                            time=event.time,
                                            level=event.level,
                                            data=event.data))

    def handle_console(self, event):
        for line in event.value().encode('utf8').split("\n"):
            log.msg(line, system="mark2")
    
    def handle_fatal(self, event):
        s = "fatal error: %s" % event.reason
        self.console(s, kind="error")
        self.shutdown()

    def handle_server_started(self, event):
        properties_ = properties.load(properties.Mark2Properties, open_resource('resources/server.default.properties'), 'server.properties')
        if properties_:
            self.properties = properties_
        if not self.started:
            self.console("mark2 started.")
            self.started = True

    def handle_user_attach(self, event):
        self.console("%s attached" % event.user, kind="joinpart")
    
    def handle_user_detach(self, event):
        self.console("%s detached" % event.user, kind="joinpart")
    
    @inlineCallbacks
    def handle_user_input(self, event):
        self.console(event.line, user=event.user, source="user")
        if event.line.startswith("~"):
            handled = yield self.events.dispatch(events.Hook(line=event.line))
            if not handled:
                self.console("unknown command.")
        elif event.line.startswith('#'):
            pass
        else:
            self.events.dispatch(events.ServerInput(line=event.line))
    
    def handle_command(self, user, text):
        self.console(text, prompt=">", user=user)
        self.send(text)

    def handle_player_join(self, event):
        self.players.add(str(event.username))
        self.events.dispatch(events.StatPlayers(players=list(self.players)))

    def handle_player_quit(self, event):
        self.players.discard(str(event.username))
        self.events.dispatch(events.StatPlayers(players=list(self.players)))

    def handle_server_stopped(self, event):
        self.players.clear()
        self.events.dispatch(events.StatPlayers(players=[]))

########NEW FILE########
__FILENAME__ = alert
import os
import random

from mk2.plugins import Plugin
from mk2.events import Hook, StatPlayerCount


class Alert(Plugin):
    interval = Plugin.Property(default=200)
    command  = Plugin.Property(default="say {message}")
    path     = Plugin.Property(default="alerts.txt")
    min_pcount = Plugin.Property(default=0)
    
    messages = []
    requirements_met = True
    
    def setup(self):
        self.register(self.count_check, StatPlayerCount)
        if self.path and os.path.exists(self.path):
            f = open(self.path, 'r')
            for l in f:
                l = l.strip()
                if l:
                    self.messages.append(l)
            f.close()

    def count_check(self, event):
        if event.players_current >= self.min_pcount:
            self.requirements_met = True
        else:
            self.requirements_met = False

    def server_started(self, event):
        if self.messages:
            self.repeating_task(self.repeater, self.interval)

    def repeater(self, event):
        if self.requirements_met:
            self.send_format(self.command, message=random.choice(self.messages))


########NEW FILE########
__FILENAME__ = backup
import time
import glob
import os
from twisted.internet import protocol, reactor, defer

from mk2.plugins import Plugin
from mk2.events import Hook, ServerOutput, ServerStopped, EventPriority
import shlex


class Backup(Plugin):
    path = Plugin.Property(default="backups/{timestamp}.tar.gz")
    mode = Plugin.Property(default="include")
    spec = Plugin.Property(default="world*")
    tar_flags = Plugin.Property(default='-hpczf')
    flush_wait = Plugin.Property(default=5)

    backup_stage = 0
    autosave_enabled = True
    proto = None
    done_backup = None
    
    def setup(self):
        self.register(self.backup, Hook, public=True, name='backup', doc='backup the server to a .tar.gz')
        self.register(self.autosave_changed, ServerOutput, pattern="(?P<username>[A-Za-z0-9_]{1,16}): (?P<action>Enabled|Disabled) level saving\.\.")
        self.register(self.autosave_changed, ServerOutput, pattern="Turned (?P<action>on|off) world auto-saving")
        self.register(self.server_stopped, ServerStopped, priority=EventPriority.HIGHEST)

    def server_started(self, event):
        self.autosave_enabled = True

    @EventPriority.HIGH
    @defer.inlineCallbacks
    def server_stopping(self, event):
        if self.backup_stage > 0:
            self.console("backup: delaying server stop until backup operation completes.")
            yield self.done_backup
            self.stop_tasks()
        self.autosave_enabled = False

    def server_stopped(self, event):
        self.autosave_enabled = False

    def save_state(self):
        if self.proto:
            self.console("stopping in-progress backup!")
            self.proto.transport.signalProcess('KILL')
        if self.done_backup:
            self.done_backup.callback(None)

        return self.autosave_enabled

    def load_state(self, state):
        self.autosave_enabled = state

    def autosave_changed(self, event):
        self.autosave_enabled = event.match.groupdict()['action'].lower() in ('on', 'enabled')
        if self.backup_stage == 1 and not self.autosave_enabled:
            self.backup_stage = 2
            self.delayed_task(self.do_backup, self.flush_wait)
        elif self.backup_stage == 2:
            self.console("warning: autosave changed while backup was in progress!")

    def backup(self, event):
        if self.backup_stage > 0:
            self.console("backup already in progress!")
            return

        self.done_backup = defer.Deferred()

        self.console("map backup starting...")
        self.autosave_enabled_prev = self.autosave_enabled
        if self.autosave_enabled:
            self.backup_stage = 1
            self.send('save-off')
        else:
            self.backup_stage = 2
            self.do_backup()

        return self.done_backup

    def do_backup(self, *a):
        timestamp = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())
        path = self.path.format(timestamp=timestamp, name=self.parent.server_name)
        if not os.path.exists(os.path.dirname(path)):
            try:
                os.makedirs(os.path.dirname(path))
            except IOError:
                self.console("Warning: {0} does't exist and I can't create it".format(os.path.dirname(path)),
                             kind='error')
                return

        if self.mode == "include":
            add = set()
            for e in self.spec.split(";"):
                add |= set(glob.glob(e))
        elif self.mode == "exclude":
            add = set(glob.glob('*'))
            for e in self.spec.split(";"):
                add -= set(glob.glob(e))

        cmd = ['tar']
        cmd.extend(shlex.split(self.tar_flags))
        cmd.append(path)
        cmd.extend(add)

        def p_ended(path):
            self.console("map backup saved to %s" % path)
            if self.autosave_enabled_prev:
                self.send('save-on')
            self.backup_stage = 0
            self.proto = None
            if self.done_backup:
                d = self.done_backup
                self.done_backup = None
                d.callback(None)

        self.proto = protocol.ProcessProtocol()
        self.proto.processEnded = lambda reason: p_ended(path)
        self.proto.childDataReceived = lambda fd, d: self.console(d.strip())
        reactor.spawnProcess(self.proto, "/bin/tar", cmd)


########NEW FILE########
__FILENAME__ = irc
import re
import os.path as path

from twisted.words.protocols import irc
from twisted.internet import defer
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.internet.interfaces import ISSLTransport
from twisted.python.util import InsensitiveDict

from mk2.plugins import Plugin
from mk2.events import PlayerChat, PlayerJoin, PlayerQuit, PlayerDeath, ServerOutput, ServerStopping, ServerStarting, StatPlayers, Hook

try:
    from OpenSSL import SSL
    from twisted.internet import ssl

    have_ssl = True
    
    class Mark2ClientContextFactory(ssl.ClientContextFactory):
        def __init__(self, parent, fingerprint=None, cert=None):
            self.parent = parent
            self.fingerprint = fingerprint
            self.cert = path.expanduser(cert) if cert else None
        
        @staticmethod
        def stripfp(fp):
            return fp.replace(':', '').lower()
        
        def verify(self, conn, cert, errno, errdepth, rc):
            ok = self.stripfp(cert.digest("sha1")) == self.stripfp(self.fingerprint)
            if self.parent and self.parent.factory.reconnect and not ok:
                self.parent.console("irc: server certificate verification failed")
                self.parent.factory.reconnect = False
            return ok
            
        def getContext(self):
            ctx = ssl.ClientContextFactory.getContext(self)
            if self.fingerprint:
                ctx.set_verify(SSL.VERIFY_PEER, self.verify)
            if self.cert:
                ctx.use_certificate_file(self.cert)
                ctx.use_privatekey_file(self.cert)
            return ctx
except:
    have_ssl = False


class IRCUser(object):
    username = ""
    hostname = ""
    status = ""
    oper = False
    away = False
    
    def __init__(self, parent, nick):
        self.parent = parent
        self.nick = nick
    
    @property
    def priority(self):
        p = self.parent.priority
        if self.status:
            return min([p[s] for s in self.status])
        else:
            return None


class SASLExternal(object):
    name = "EXTERNAL"

    def __init__(self, username, password):
        pass

    def is_valid(self):
        return True

    def respond(self, data):
        return ""


class SASLPlain(object):
    name = "PLAIN"

    def __init__(self, username, password):
        self.response = "{0}\0{0}\0{1}".format(username, password)

    def is_valid(self):
        return self.response != "\0\0"

    def respond(self, data):
        if data:
            return False
        return self.response


SASL_MECHANISMS = (SASLExternal, SASLPlain)


class IRCBot(irc.IRCClient):
    sasl_buffer = ""
    sasl_result = None
    sasl_login = None

    def __init__(self, factory, plugin):
        self.factory     = factory
        self.nickname    = plugin.nickname.encode('ascii')
        self.realname    = plugin.realname.encode('ascii')
        self.username    = plugin.ident.encode('ascii')
        self.ns_username = plugin.username
        self.ns_password = plugin.password
        self.password    = plugin.server_password.encode('ascii')
        self.channel     = plugin.channel.encode('ascii')
        self.key         = plugin.key.encode('ascii')
        self.console     = plugin.console
        self.irc_message = plugin.irc_message
        self.irc_action  = plugin.irc_action
        self.irc_chat_status = plugin.irc_chat_status
        self.mangle_username = plugin.mangle_username

        self.users       = InsensitiveDict()
        self.cap_requests = set()

    def register(self, nickname, hostname="foo", servername="bar"):
        self.sendLine("CAP LS")
        return irc.IRCClient.register(self, nickname, hostname, servername)

    def sendLine(self, line):
        irc.IRCClient.sendLine(self, line.encode('ascii', 'replace'))

    def _parse_cap(self, cap):
        mod = ''
        while cap[0] in "-~=":
            mod, cap = mod + cap[0], cap[1:]
        if '/' in cap:
            vendor, cap = cap.split('/', 1)
        else:
            vendor = None
        return (cap, mod, vendor)

    def request_cap(self, *caps):
        self.cap_requests |= set(caps)
        self.sendLine("CAP REQ :{0}".format(' '.join(caps)))

    @defer.inlineCallbacks
    def end_cap(self):
        if self.sasl_result:
            yield self.sasl_result
        self.sendLine("CAP END")

    def irc_CAP(self, prefix, params):
        self.supports_cap = True
        identifier, subcommand, args = params
        args = args.split(' ')
        if subcommand == "LS":
            self.sasl_start(args)
            if not self.cap_requests:
                self.sendLine("CAP END")
        elif subcommand == "ACK":
            ack = []
            for cap in args:
                if not cap:
                    continue
                cap, mod, vendor = self._parse_cap(cap)
                if '-' in mod:
                    if cap in self.capabilities:
                        del self.capabilities[cap]
                    continue
                self.cap_requests.remove(cap)
                if cap == 'sasl':
                    self.sasl_next()
            if ack:
                self.sendLine("CAP ACK :{0}".format(' '.join(ack)))
            if not self.cap_requests:
                self.end_cap()
        elif subcommand == "NAK":
            # this implementation is probably not compliant but it will have to do for now
            for cap in args:
                self.cap_requests.remove(cap)
            if not self.cap_requests:
                self.end_cap()

    def signedOn(self):
        if ISSLTransport.providedBy(self.transport):
            cert = self.transport.getPeerCertificate()
            fp = cert.digest("sha1")
            verified = "verified" if self.factory.parent.server_fingerprint else "unverified"
            self.console("irc: connected securely. server fingerprint: {0} ({1})".format(fp, verified))
        else:
            self.console("irc: connected")
        
        if self.ns_username and self.ns_password and not self.sasl_login:
            self.msg('NickServ', 'IDENTIFY {0} {1}'.format(self.ns_username, self.ns_password))
        
        self.join(self.channel, self.key)

    def irc_JOIN(self, prefix, params):
        nick = prefix.split('!')[0]
        channel = params[-1]
        if nick == self.nickname:
            self.joined(channel)
        else:
            self.userJoined(prefix, channel)

    def joined(self, channel):
        self.console('irc: joined channel')
        self.factory.client = self
        def who(a):
            self.sendLine("WHO " + channel)
        self.factory.parent.repeating_task(who, 30, now=True)
    
    def isupport(self, args):
        self.compute_prefix_names()
        
    def compute_prefix_names(self):
        KNOWN_NAMES = {"o": "op", "h": "halfop", "v": "voice"}
        prefixdata = self.supported.getFeature("PREFIX", {"o": ("@", 0), "v": ("+", 1)}).items()
        op_priority = ([priority for mode, (prefix, priority) in prefixdata if mode == "o"] + [None])[0]
        self.prefixes, self.statuses, self.priority = {}, {}, {}

        for mode, (prefix, priority) in prefixdata:
            name = "?"
            if mode in KNOWN_NAMES:
                name = KNOWN_NAMES[mode]
            elif priority == 0:
                if op_priority == 2:
                    name = "owner"
                else:
                    name = "admin"
            else:
                name = "+" + mode
            self.prefixes[mode] = prefix
            self.statuses[prefix] = name
            self.priority[name] = priority
            self.priority[mode] = priority
            self.priority[prefix] = priority

    def parse_prefixes(self, user, nick, prefixes=''):
        status = []
        prefixdata = self.supported.getFeature("PREFIX", {"o": ("@", 0), "v": ("+", 1)}).items()
        for mode, (prefix, priority) in prefixdata:
            if prefix in prefixes + nick:
                nick = nick.replace(prefix, '')
                status.append((prefix, priority))
        if nick == self.nickname:
            return
        user.status = ''.join(t[0] for t in sorted(status, key=lambda t: t[1]))
    
    def irc_RPL_WHOREPLY(self, prefix, params):
        _, channel, username, host, server, nick, status, hg = params
        if nick == self.nickname:
            return
        hops, gecos = hg.split(' ', 1)
        user = IRCUser(self, nick)
        user.username = username
        user.hostname = host
        user.oper = '*' in status
        user.away = status[0] == 'G'
        self.users[nick] = user
        self.parse_prefixes(user, nick, status[1:].replace('*', ''))
    
    def modeChanged(self, user, channel, _set, modes, args):
        args = list(args)
        if channel.lower() != self.channel.lower():
            return
        for m, arg in zip(modes, args):
            if m in self.prefixes and arg != self.nickname:
                u = self.users.get(arg, None)
                if u:
                    u.status = u.status.replace(self.prefixes[m], '')
                    if _set:
                        u.status = ''.join(sorted(list(u.status + self.prefixes[m]),
                                                  key=lambda k: self.priority[k]))

    def has_status(self, nick, status):
        if status != 0 and not status:
            return True
        if status not in self.priority:
            return False
        priority = self.priority[status]
        u = self.users.get(nick, None)
        return u and (u.priority is not None) and u.priority <= priority
    
    def userJoined(self, user, channel):
        nick = user.split('!')[0]
        user = IRCUser(self, nick)
        self.users[nick] = user
    
    def userRenamed(self, oldname, newname):
        if oldname not in self.users:
            return
        u = self.users[oldname]
        u.nick = newname
        self.users[newname] = u
        del self.users[oldname]
    
    def userLeft(self, user, channel):
        if user not in self.users:
            return
        del self.users[user]
    
    def userKicked(self, kickee, channel, kicker, message):
        if kickee not in self.users:
            return
        del self.users[kickee]
    
    def userQuit(self, user, quitMessage):
        if user not in self.users:
            return
        del self.users[user]

    def privmsg(self, user, channel, msg):
        if channel != self.channel:
            return
        if '!' not in user:
            return
        nick = user.split('!')[0]
        p = self.factory.parent
        
        if not self.has_status(nick, self.irc_chat_status):
            return

        if p.irc_players_enabled and msg.lower() == p.irc_command_prefix + "players":
            self.say(self.channel, p.irc_players_format.format(
                players=', '.join(map(self.mangle_username, p.players))))

        elif p.irc_command_prefix and msg.startswith(p.irc_command_prefix) and p.irc_command_status and self.has_status(nick, p.irc_command_status):
            argv = msg[len(p.irc_command_prefix):].split(' ')
            command = argv[0]
            if command.startswith('~'):
                if p.irc_command_mark2 and (command.lower() in p.irc_command_allow.lower().split(',') or p.irc_command_allow == '*'):
                    p.dispatch(Hook(line=' '.join(argv)))
            else:
                if command.lower() in p.irc_command_allow.lower().split(',') or p.irc_command_allow == '*':
                    p.send(' '.join(argv))

        else:
            self.irc_message(nick, msg)

    def action(self, user, channel, msg):
        self.console("%s %s %s" % (user, channel, msg))
        if channel != self.channel:
            return
        if '!' not in user:
            return
        nick = user.split('!')[0]
        
        if self.has_status(nick, self.irc_chat_status):
            self.irc_action(nick, msg)

    def irc_AUTHENTICATE(self, prefix, params):
        self.sasl_continue(params[0])

    def sasl_send(self, data):
        while data and len(data) >= 400:
            en, data = data[:400].encode('base64').replace('\n', ''), data[400:]
            self.sendLine("AUTHENTICATE " + en)
        if data:
            self.sendLine("AUTHENTICATE " + data.encode('base64').replace('\n', ''))
        else:
            self.sendLine("AUTHENTICATE +")

    def sasl_start(self, cap_list):
        if 'sasl' not in cap_list:
            print cap_list
            return
        self.request_cap('sasl')
        self.sasl_result = defer.Deferred()
        self.sasl_mechanisms = list(SASL_MECHANISMS)

    def sasl_next(self):
        mech = None
        while not mech or not mech.is_valid():
            if not self.sasl_mechanisms:
                return False
            self.sasl_auth = mech = self.sasl_mechanisms.pop(0)(self.ns_username, self.ns_password)
        self.sendLine("AUTHENTICATE " + self.sasl_auth.name)
        return True

    def sasl_continue(self, data):
        if data == '+':
            data = ''
        else:
            data = data.decode('base64')
        if len(data) == 400:
            self.sasl_buffer += data
        else:
            response = self.sasl_auth.respond(self.sasl_buffer + data)
            if response is False:  # abort
                self.sendLine("AUTHENTICATE *")
            else:
                self.sasl_send(response)
            self.sasl_buffer = ""

    def sasl_finish(self):
        if self.sasl_result:
            self.sasl_result.callback(True)
            self.sasl_result = None

    def sasl_failed(self, whine=True):
        if self.sasl_login is False:
            return
        if self.sasl_next():
            return
        self.sasl_login = False
        self.sendLine("AUTHENTICATE *")
        self.sasl_finish()
        if whine:
            self.console("irc: failed to log in.")

    def irc_904(self, prefix, params):
        print params
        self.sasl_failed()

    def irc_905(self, prefix, params):
        print params
        self.sasl_failed()

    def irc_906(self, prefix, params):
        self.sasl_failed(False)

    def irc_907(self, prefix, params):
        self.sasl_failed(False)

    def irc_900(self, prefix, params):
        self.sasl_login = params[2]
        self.console("irc: logged in as '{0}' (using {1})".format(self.sasl_login, self.sasl_auth.name))

    def irc_903(self, prefix, params):
        self.sasl_finish()

    def alterCollidedNick(self, nickname):
        return nickname + '_'

    def irc_relay(self, message):
        self.say(self.channel, message.encode('utf8'))


class IRCBotFactory(protocol.ClientFactory):
    protocol = IRCBot
    client = None
    reconnect = True

    def __init__(self, parent):
        self.parent = parent

    def clientConnectionLost(self, connector, reason):
        if self.reconnect:
            self.parent.console("irc: lost connection with server: %s" % reason.getErrorMessage())
            self.parent.console("irc: reconnecting...")
            connector.connect()

    def clientConnectionFailed(self, connector, reason):
        self.parent.console("irc: connection attempt failed: %s" % reason.getErrorMessage())
    
    def buildProtocol(self, addr):
        p = IRCBot(self, self.parent)
        return p
    
    def irc_relay(self, message):
        if self.client:
            self.client.irc_relay(message)


class IRC(Plugin):
    #connection
    host               = Plugin.Property(required=True)
    port               = Plugin.Property(required=True)
    server_password    = Plugin.Property()
    channel            = Plugin.Property(required=True)
    key                = Plugin.Property()
    certificate        = Plugin.Property()
    ssl                = Plugin.Property(default=False)
    server_fingerprint = Plugin.Property()

    #user
    nickname = Plugin.Property(default="RelayBot")
    realname = Plugin.Property(default="mark2 IRC relay")
    ident    = Plugin.Property(default="RelayBot")
    username = Plugin.Property(default="")
    password = Plugin.Property(default="")

    #general
    cancel_highlight     = Plugin.Property(default=False, type_=False)
    cancel_highlight_str = Plugin.Property(default=u"_")

    #game -> irc settings
    game_columns = Plugin.Property(default=True)

    game_status_enabled = Plugin.Property(default=True)
    game_status_format  = Plugin.Property(default=u"!, | server {what}.")

    game_chat_enabled = Plugin.Property(default=True)
    game_chat_format  = Plugin.Property(default=u"{username}, | {message}")
    game_chat_private = Plugin.Property(default=None)

    game_join_enabled = Plugin.Property(default=True)
    game_join_format  = Plugin.Property(default=u"*, | --> {username}")

    game_quit_enabled = Plugin.Property(default=True)
    game_quit_format  = Plugin.Property(default=u"*, | <-- {username}")

    game_death_enabled = Plugin.Property(default=True)
    game_death_format  = Plugin.Property(default=u"*, | {text}")

    game_server_message_enabled = Plugin.Property(default=True)
    game_server_message_format  = Plugin.Property(default=u"#server, | {message}")

    #bukkit only
    game_me_enabled = Plugin.Property(default=True)
    game_me_format  = Plugin.Property(default=u"*, | {username} {message}")

    #irc -> game settings
    irc_chat_enabled    = Plugin.Property(default=True)
    irc_chat_command    = Plugin.Property(default=u"say [IRC] <{nickname}> {message}")
    irc_action_command  = Plugin.Property(default=u"say [IRC] * {nickname} {message}")
    irc_chat_status     = Plugin.Property(default=None)

    irc_command_prefix  = Plugin.Property(default="!")
    irc_command_status  = Plugin.Property(default=None)
    irc_command_allow   = Plugin.Property(default="")
    irc_command_mark2   = Plugin.Property(default=False)

    irc_players_enabled = Plugin.Property(default=True)
    irc_players_format  = Plugin.Property(default=u"*, | players currently in game: {players}")

    def setup(self):
        self.players = []
        self.factory = IRCBotFactory(self)
        if self.ssl:
            if have_ssl:
                cf = Mark2ClientContextFactory(self,
                                               cert=self.certificate,
                                               fingerprint=self.server_fingerprint)
                reactor.connectSSL(self.host, self.port, self.factory, cf)
            else:
                self.parent.console("Couldn't load SSL for IRC!")
                return
        else:
            reactor.connectTCP(self.host, self.port, self.factory)

        if self.game_status_enabled:
            self.register(self.handle_stopping, ServerStopping)
            self.register(self.handle_starting,  ServerStarting)
        
        self.column_width = 16
        if self.cancel_highlight == "insert":
            self.column_width += len(self.cancel_highlight_str)

        def register(event_type, format, filter_=None, *a, **k):
            def handler(event, format):
                d = event.match.groupdict() if hasattr(event, 'match') else event.serialize()
                if filter_ and 'message' in d:
                    if filter_.match(d['message']):
                        return
                if self.cancel_highlight and 'username' in d and d['username'] in self.factory.client.users:
                    d['username'] = self.mangle_username(d['username'])
                line = self.format(format, **d)
                self.factory.irc_relay(line)
            self.register(lambda e: handler(e, format), event_type, *a, **k)

        if self.game_chat_enabled:
            if self.game_chat_private:
                try:
                    filter_ = re.compile(self.game_chat_private)
                    register(PlayerChat, self.game_chat_format, filter_=filter_)
                except:
                    self.console("plugin.irc.game_chat_private must be a valid regex")
                    register(PlayerChat, self.game_chat_format)
            else:
                register(PlayerChat, self.game_chat_format)

        if self.game_join_enabled:
            register(PlayerJoin, self.game_join_format)

        if self.game_quit_enabled:
            register(PlayerQuit, self.game_quit_format)

        if self.game_death_enabled:
            def handler(event):
                d = event.serialize()
                for k in 'username', 'killer':
                    if k in d and d[k] and d[k] in self.factory.client.users:
                        d[k] = self.mangle_username(d[k])
                text = event.get_text(**d)
                line = self.format(self.game_death_format, text=text)
                self.factory.irc_relay(line)
            self.register(handler, PlayerDeath)

        if self.game_server_message_enabled and not (self.irc_chat_enabled and self.irc_chat_command.startswith('say ')):
            register(ServerOutput, self.game_server_message_format, pattern=r'\[(?:Server|SERVER)\] (?P<message>.+)')

        if self.game_me_enabled:
            register(ServerOutput, self.game_me_format, pattern=r'\* (?P<username>[A-Za-z0-9_]{1,16}) (?P<message>.+)')

        if self.irc_chat_enabled:
            self.register(self.handle_players, StatPlayers)

    def teardown(self):
        self.factory.reconnect = False
        if self.factory.client:
            self.factory.client.quit("Plugin unloading.")
        
    def mangle_username(self, username):
        if not self.cancel_highlight:
            return username
        elif self.cancel_highlight == "insert":
            return username[:-1] + self.cancel_highlight_str + username[-1:]
        else:
            return self.cancel_highlight_str + username[1:]

    def format(self, format, **data):
        if self.game_columns:
            f = unicode(format).split(',', 1)
            f[0] = f[0].format(**data)
            if len(f) == 2:
                f[0] = f[0].rjust(self.column_width)
                f[1] = f[1].format(**data)
            return ''.join(f)
        else:
            return format.format(**data)

    def handle_starting(self, event):
        self.factory.irc_relay(self.format(self.game_status_format, what="starting"))

    def handle_stopping(self, event):
        self.factory.irc_relay(self.format(self.game_status_format, what="stopping"))

    def handle_players(self, event):
        self.players = sorted(event.players)

    def irc_message(self, user, message):
        if self.irc_chat_enabled:
            self.send_format(self.irc_chat_command, nickname=user, message=message)

    def irc_action(self, user, message):
        if self.irc_chat_enabled:
            self.console("{} {}".format(user, message))
            self.send_format(self.irc_action_command, nickname=user, message=message)

########NEW FILE########
__FILENAME__ = log
import time
import gzip
import os
import re

from mk2.plugins import Plugin
from mk2.events import Console, ServerStopped, ServerStopping, ServerOutput


class Log(Plugin):
    gzip      = Plugin.Property(default=True)
    path      = Plugin.Property(default="logs/server-{timestamp}-{status}.log.gz")
    vanilla   = Plugin.Property(default=False)
    
    log = u""
    reason = "unknown"
    time_re = re.compile(r'(?:\d{2}:\d{2}:\d{2}) (.*)')

    restore = ('log',)
    
    def setup(self):
        if self.vanilla:
            self.register(self.vanilla_logger, ServerOutput, pattern='.*')
        else:
            self.register(self.logger, Console)
        self.register(self.shutdown, ServerStopped)
        self.register(self.pre_shutdown, ServerStopping)

    def vanilla_logger(self, event):
        m = self.time_re.match(event.line)
        if m:
            self.log += u"{0} {1}\n".format(event.time, m.group(1))
        else:
            self.log += u"{0}\n".format(event.line)
    
    def logger(self, event):
        self.log += u"{0}\n".format(event.value())
    
    def pre_shutdown(self, event):
        self.reason = event.reason
    
    def shutdown(self, event):
        reason = self.reason
        if reason == None:
            reason = "ok"
            
        timestamp = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())
        
        path = self.path.format(timestamp=timestamp, name=self.parent.name, status=reason)

        if not os.path.exists(os.path.dirname(path)):
            try:
                os.makedirs(os.path.dirname(path))
            except IOError:
                self.console("Warning: {0} does't exist and I can't create it".format(os.path.dirname(path)),
                             kind='error')
                return
        
        if self.gzip:
            f = gzip.open(path, 'wb')
        else:
            f = open(path, 'w')
        
        f.write(self.log.encode('utf8'))
        f.close()
        self.console("server.log written to %s" % os.path.realpath(path))
        self.log = ""

########NEW FILE########
__FILENAME__ = mcbouncer
from twisted.python import log
import urllib
import json

from twisted.web.client import HTTPClientFactory, getPage
HTTPClientFactory.noisy = False

from mk2.plugins import Plugin
from mk2.events import ServerOutput

class BouncerAPI:
    methods = ['addBan', 'removeBan', 'getBanReason', 'getIPBanReason', 'updateUser']
    def __init__(self, api_base, api_key, errback):
        self.api_key = api_key
        self.api_base = api_base
        self.errback = errback
    
    def __getattr__(self, method):
        if not method in self.methods:
            raise AttributeError
        
        def inner(*args, **kwargs):
            args = [urllib.quote(a.encode('utf8'), "") for a in args]
            callback = kwargs.get('callback', None)
            addr = '/'.join([self.api_base, method, self.api_key] + args)
            deferred = getPage(addr)
            if callback:
                deferred.addCallback(lambda d: callback(json.loads(str(d))))
                deferred.addErrback(self.errback)
        return inner

class MCBouncer(Plugin):
    api_base   = Plugin.Property(default='http://mcbouncer.com/api')
    api_key    = Plugin.Property(default=None)
    reason     = Plugin.Property(default="Banned by an operator")
    proxy_mode = Plugin.Property(default=False)
    
    def setup(self):
        self.bouncer = BouncerAPI(self.api_base, self.api_key, self.on_error)
        
        self.register(self.on_login,  ServerOutput, pattern='([A-Za-z0-9_]{1,16})\[/([0-9\.]+):\d+\] logged in with entity id .+')
        self.register(self.on_ban,    ServerOutput, pattern='\[([A-Za-z0-9_]{1,16}): Banned player ([A-Za-z0-9_]{1,16})\]')
        self.register(self.on_ban,    ServerOutput, pattern='Banned player ([A-Za-z0-9_]{1,16})')
        self.register(self.on_pardon, ServerOutput, pattern='\[[A-Za-z0-9_]{1,16}: Unbanned player ([A-Za-z0-9_]{1,16})\]')
        self.register(self.on_pardon, ServerOutput, pattern='Unbanned player ([A-Za-z0-9_]{1,16})')
    
    def on_error(self, error):
        self.console("Couldn't contact mcbouncer! %s" % error.getErrorMessage())
        
    def on_ban(self, event):
        g = event.match.groups()
        player = g[-1]
        issuer = g[0] if len(g) == 2 else 'console'
        o = self.bouncer.addBan(issuer, player, self.reason)
    
    def on_pardon(self, event):
        g = event.match.groups()
        self.bouncer.removeBan(g[0])
    
    def on_login(self, event):
        g = event.match.groups()
        self.bouncer.getBanReason(g[0], callback=lambda d: self.ban_reason(g[0], d))
        if not self.proxy_mode:
            self.bouncer.updateUser(g[0], g[1])
            self.bouncer.getIPBanReason(g[1], callback=lambda d: self.ip_ban_reason(g[0], d))
    
    def ban_reason(self, user, details):
        if details['is_banned']:
            self.send('kick %s Banned: %s' % (user, details['reason']))
    
    def ip_ban_reason(self, user, details):
        if details['is_banned']:
            self.send('kick %s Banned: %s' % (user, details['reason']))

########NEW FILE########
__FILENAME__ = monitor
from mk2.plugins import Plugin
from mk2.events import ServerOutput, StatPlayerCount, ServerStop, ServerEvent, Event


class Check(object):
    alive = True
    timeout = 0
    time = 0
    warn = 0

    def __init__(self, parent, **kw):
        self.dispatch = parent.dispatch
        self.console = parent.console
        for k, v in kw.items():
            setattr(self, k, v)

    def check(self):
        if self.alive:
            self.alive = False
            return True
        return False

    def step(self):
        if self.check():
            return

        self.time += 1
        if self.timeout and self.time == self.timeout:
            timeout = "{0} minutes".format(self.timeout)
            self.console("{0} -- restarting.".format(self.message.format(timeout=timeout)))
            self.dispatch(ServerEvent(cause="server/error/" + self.event[0],
                                      data="REBOOTING SERVER: " + self.event[1].format(timeout=timeout),
                                      priority=1))
            self.dispatch(ServerStop(reason=self.stop_reason, respawn=True))
        elif self.warn and self.time == self.warn:
            if self.timeout:
                self.console("{0} -- auto restart in {1} minutes".format(self.warning, self.timeout - self.time))
            else:
                self.console(self.warning)
            time = "{0} minutes".format(self.warn)
            self.dispatch(ServerEvent(cause="server/warning/" + self.event[0],
                                      data="WARNING: " + self.event[1].format(timeout=time),
                                      priority=1))
        else:
            if self.timeout:
                self.console("{0} -- auto restart in {1} minutes".format(self.warning, self.timeout - self.time))
            else:
                self.console(self.warning)

    def reset(self):
        self.alive = True
        self.time = 0


class Monitor(Plugin):
    crash_enabled  = Plugin.Property(default=True)
    crash_timeout  = Plugin.Property(default=3)
    crash_warn     = Plugin.Property(default=0)
    crash_unknown_cmd_message    = Plugin.Property(default="Unknown command.*")
    crash_check_command    = Plugin.Property(default="")

    oom_enabled    = Plugin.Property(default=True)

    ping_enabled   = Plugin.Property(default=True)
    ping_timeout   = Plugin.Property(default=3)
    ping_warn      = Plugin.Property(default=0)

    pcount_enabled = Plugin.Property(default=False)
    pcount_timeout = Plugin.Property(default=3)
    pcount_warn    = Plugin.Property(default=0)

    def setup(self):
        do_step = False
        self.checks = {}

        if self.oom_enabled:
            self.register(self.handle_oom, ServerOutput, level='SEVERE', pattern='java\.lang\.OutOfMemoryError.*')

        if self.crash_enabled:
            do_step = True
            self.checks['crash'] =  Check(self, name="crash",
                                          timeout=self.crash_timeout,
                                          warn=self.crash_warn,
                                          message="server has crashed",
                                          warning="server might have crashed",
                                          event=("hang", "server didn't respond for {timeout}"),
                                          stop_reason="crashed")

        if self.ping_enabled:
            self.register(self.handle_ping, StatPlayerCount)
            do_step = True
            self.checks['ping'] =   Check(self, name="ping",
                                          timeout=self.ping_timeout,
                                          warn=self.ping_warn,
                                          message="server is not accepting connections",
                                          warning="server might have stopped accepting connections",
                                          event=("ping", "server didn't respond for {timeout}"),
                                          stop_reason="not accepting connections")

        if self.pcount_enabled:
            self.register(self.handle_pcount, StatPlayerCount)
            do_step = True
            self.checks['pcount'] = Check(self, name="pcount",
                                          timeout=self.pcount_timeout,
                                          warn=self.pcount_warn,
                                          message="server has had 0 players for {timeout}, something is wrong",
                                          warning="server has 0 players, might be inaccessible",
                                          event=("player-count", "server had 0 players for {timeout}"),
                                          stop_reason="zero players")

        self.do_step = do_step

    def server_started(self, event):
        self.reset_counts()
        if self.do_step:
            self.repeating_task(self.step, 60)

    def load_state(self, state):
        self.server_started(None)

    def step(self, *a):
        for c in self.checks.values():
            c.step()

        if self.crash_enabled:
            self.register(self.handle_crash_ok, ServerOutput,
                          pattern=self.crash_unknown_cmd_message,
                          track=False)
            self.send(self.crash_check_command)  # Blank command to trigger 'Unknown command'
    
    def reset_counts(self):
        for c in self.checks.values():
            c.reset()

    ### handlers
    
    # crash
    def handle_crash_ok(self, event):
        self.checks["crash"].reset()
        return Event.EAT | Event.UNREGISTER
    
    # out of memory
    def handle_oom(self, event):
        self.console('server out of memory, restarting...')
        self.dispatch(ServerEvent(cause='server/error/oom',
                                  data="server ran out of memory",
                                  priority=1))
        self.dispatch(ServerStop(reason='out of memory', respawn=True))

    # ping
    def handle_ping(self, event):
        if event.source == 'ping':
            self.checks["ping"].reset()
    
    # pcount
    def handle_pcount(self, event):
        if event.players_current > 0:
            self.checks["pcount"].reset()
        else:
            self.checks["pcount"].alive = False

########NEW FILE########
__FILENAME__ = mumble
import re
import struct

from twisted.application.internet import UDPServer
from twisted.internet import reactor, defer
from twisted.internet.defer import TimeoutError
from twisted.internet.protocol import DatagramProtocol

from mk2.plugins import Plugin
from mk2.events import ServerOutput

class MumbleProtocol(DatagramProtocol):
    buff = ""
    def __init__(self, parent, host, port):
        self.parent = parent
        self.host = host
        self.port = port

    def ping(self, *a):
        self.transport.write('\x00'*12, addr=(self.host, self.port))

    def datagramReceived(self, data, (host, port)):
        self.buff += data
        if len(self.buff) < 24:
            return

        if not self.buff.startswith('\x00\x01\x02\x03' + '\x00' * 8):
            self.parent.console("the mumble server gave us crazy data!")
            self.buff = ""
            return

        d = dict(zip(('users_current', 'users_max', 'bandwidth'), struct.unpack('>III', self.buff[12:24])))

        self.buff = self.buff[24:]

        self.parent.got_response(d)


class Mumble(Plugin):
    host       = Plugin.Property(required=True)
    port       = Plugin.Property(default=64738)
    timeout    = Plugin.Property(default=10)
    trigger    = Plugin.Property(default="!mumble")
    command_up = Plugin.Property(default='''
msg {username} &2host: &a{host}
msg {username} &2port: &a{port}
msg {username} &2status: &aup! users: {users_current}/{users_max}
'''.strip())

    command_down = Plugin.Property(default='''
msg {username} &2host: &a{host}
msg {username} &2port: &a{port}
msg {username} &2status: &adown.
'''.strip())

    def setup(self):
        self.users = []
        self.protocol = MumbleProtocol(self, self.host, self.port)
        self.register(self.handle_trigger, ServerOutput, pattern="<([A-Za-z0-9_]{1,16})> "+re.escape(self.trigger))
        reactor.listenUDP(0, self.protocol)

    def teardown(self):
        self.protocol.transport.loseConnection()

    def handle_trigger(self, event):
        username = event.match.group(1).encode('utf8')
        d = defer.Deferred()
        d.addCallback(lambda d: self.send_response(self.command_up,   username=username, **d))
        d.addErrback (lambda d: self.send_response(self.command_down, username=username))
        #add a timeout
        self.delayed_task(self.got_timeout, self.timeout)
        self.users.append(d)
        self.protocol.ping()

    def got_response(self, d):
        for u in self.users:
            u.callback(d)
        self.users = []
        self.stop_tasks()

    def got_timeout(self, e):
        for u in self.users:
            u.errback(TimeoutError())
        self.users = []
        self.stop_tasks()

    def send_response(self, command, **d):
        self.send_format(command, host=self.host, port=self.port, **d)

########NEW FILE########
__FILENAME__ = push
from mk2.plugins import Plugin
from mk2.events import ServerEvent, EventPriority

from twisted.internet import reactor
from twisted.internet.defer import Deferred, DeferredList
from twisted.mail import smtp, relaymanager
from twisted.web.client import getPage

from cStringIO import StringIO
from email.mime.text import MIMEText
from urllib import urlencode
import re

_endpoint = {}
_plugin = None


def endpoint(s):
    def _wrapper(cls):
        _endpoint[s] = cls
        cls.scheme = s
        return cls
    return _wrapper


class Endpoint(object):
    causes = "*"
    priority = "*"
    
    def __init__(self, plugin, uri):
        pass
        
    def push(self, event):
        pass
    
    def filter(self, event):
        if self.priority != "*":
            if int(self.priority) > event.priority:
                return False
        if self.causes != "*":
            for cause in self.causes.split(","):
                if cause == event.cause:
                    return True
                if cause.endswith("/") and event.cause.startswith(cause):
                    return True
            return False
        return True
    
    def wait(self, defer):
        def done_waiting(a):
            _plugin.pending.remove(defer)
            return a
        _plugin.pending.add(defer)
        defer.addBoth(done_waiting)
    
    def __str__(self):
        return "<{0} {1} causes={2} priority={3}>".format(self.__class__.__name__,
                                                          self.url,
                                                          self.causes, self.priority)
    
    
class HTTPEndpoint(Endpoint):
    method = "POST"
    postdata = {}
    
    def push(self, event):
        self.setup(event)
        
        defer = getPage(self.endpoint,
                        method=self.method,
                        postdata=urlencode(self.postdata),
                        headers={"Content-type": "application/x-www-form-urlencoded"})
        
        self.wait(defer)


@endpoint("nma")
class NMAEndpoint(HTTPEndpoint):
    endpoint = "https://www.notifymyandroid.com/publicapi/notify"
    method = "POST"
    
    def __init__(self, plugin, url):
        self.postdata = {
            "apikey":      url,
            "application": "mark2: {0}".format(plugin.parent.server_name),
        }
    
    def setup(self, event):
        self.postdata.update(priority=event.priority,
                             event=event.friendly,
                             description=event.data)


@endpoint("prowl")
class ProwlEndpoint(HTTPEndpoint):
    endpoint = "https://api.prowlapp.com/publicapi/add"
    method = "POST"
    
    def __init__(self, plugin, url):
        self.postdata = {
            "apikey":      url,
            "application": "mark2: {0}".format(plugin.parent.server_name),
        }
    
    def setup(self, event):
        self.postdata.update(priority=event.priority,
                             event=event.friendly,
                             description=event.data)


@endpoint("pushover")
class PushoverEndpoint(HTTPEndpoint):
    endpoint = "https://api.pushover.net/1/messages.json"
    method = "POST"
    device = None
    
    def __init__(self, plugin, url):
        if not plugin.pushover_token:
            raise Exception("pushover token is not configured")
        self.postdata = {
            "user":  url,
            "token": plugin.pushover_token,
        }
    
    def setup(self, event):
        self.postdata.update(priority=max(-1, event.priority),
                             title=event.friendly,
                             message=event.data)
        if self.device:
            self.postdata["device"] = self.device


@endpoint("smtp")
class SMTPEndpoint(Endpoint):
    def __init__(self, plugin, url):
        self.smtp_host, self.smtp_user, self.smtp_password =\
            plugin.email_smtp_server, plugin.email_smtp_user, plugin.email_smtp_password
        self.smtp_security = plugin.email_smtp_security

        if ':' in self.smtp_host:
            host = self.smtp_host.split(':')
            self.smtp_host, self.smtp_port = host[0], int(host[1])
        else:
            self.smtp_port = 25

        self.from_addr = plugin.email_address
        self.from_name = "mark2: {0}".format(plugin.parent.server_name)
        self.to_addr = url
        
    def getMailExchange(self, host):
        mxc = relaymanager.MXCalculator()
        def cbMX(mxRecord):
            return str(mxRecord.name)
        return mxc.getMX(host).addCallback(cbMX)

    def sendEmail(self, from_, from_name, to, msg_, subject=""):
        def send(host, user=None, pw=None, require_security=False):
            msg = MIMEText(msg_)
            msg['From'] = "\"{0}\" <{1}>".format(from_name, from_)
            msg['To'] = to
            msg['Subject'] = subject
            msgfile = StringIO(msg.as_string())
            d = Deferred()
            factory = smtp.ESMTPSenderFactory(user, pw, from_, to, msgfile, d,
                                              requireAuthentication=(user is not None),
                                              requireTransportSecurity=require_security)
            reactor.connectTCP(host, self.smtp_port, factory)
            self.wait(d)
            return d
        if self.smtp_host:
            return send(self.smtp_host, self.smtp_user, self.smtp_password, self.smtp_security)
        else:
            return self.getMailExchange(to.split("@")[1]).addCallback(send)
    
    def push(self, event):
        defer = self.sendEmail(self.from_addr, self.from_name, self.to_addr, event.data, event.friendly)
        
        self.wait(defer)


class Push(Plugin):
    endpoints           = Plugin.Property(default="")

    email_address       = Plugin.Property(default="mark2@fantastic.minecraft.server")
    email_smtp_server   = Plugin.Property(default="")
    email_smtp_user     = Plugin.Property(default="")
    email_smtp_password = Plugin.Property(default="")
    email_smtp_security = Plugin.Property(default=False)

    pushover_token      = Plugin.Property(default="")
    
    def setup(self):
        global _plugin
        _plugin = self
        
        self.pending = set()
        
        self.configure_endpoints()
        
        self.register(self.send_alert, ServerEvent, priority=EventPriority.MONITOR)
        
        self.eventid = reactor.addSystemEventTrigger('before', 'shutdown', self.finish)
    
    def teardown(self):
        reactor.removeSystemEventTrigger(self.eventid)
    
    def finish(self):
        return DeferredList(list(self.pending))
    
    def configure_endpoints(self):
        eps = self.endpoints.split("\n")
        self._endpoints = []
        for ep in eps:
            if not ep.strip():
                continue
            try:
                bits = re.split("\s+", ep)
                url, md = bits[0], bits[1:]
                scheme, ee = re.split(":(?://)?", url)
                if scheme not in _endpoint:
                    self.console("undefined endpoint requested: {0}".format(url))
                    continue
                cls = _endpoint[scheme]
                inst = cls(self, ee)
                inst.url = url
                for k, v in [d.split("=") for d in md]:
                    setattr(inst, k, v)
                self._endpoints.append(inst)
            except Exception as e:
                self.console("push: ERROR ({0}) adding endpoint: {1}".format(e, ep))
    
    def send_alert(self, event):
        for ep in self._endpoints:
            if ep.filter(event):
                ep.push(event)

########NEW FILE########
__FILENAME__ = redis
import json

from twisted.internet import protocol
from twisted.internet import reactor

from mk2.plugins import Plugin
from mk2 import events


class RedisProtocol(protocol.Protocol):
    def __init__(self, parent):
        self.parent = parent

    def request(self, *args):
        self.transport.write(self.encode_request(args))

    def encode_request(self, args):
        lines = []
        lines.append('*' + str(len(args)))
        for a in args:
            if isinstance(a, unicode):
                a = a.encode('utf8')
            lines.append('$' + str(len(a)))
            lines.append(a)
        lines.append('')
        return '\r\n'.join(lines)


class RedisFactory(protocol.ReconnectingClientFactory):
    def __init__(self, parent, channel):
        self.parent = parent
        self.channel = channel

    def buildProtocol(self, addr):
        self.protocol = RedisProtocol(self.parent)
        return self.protocol

    def relay(self, data, channel=None):
        channel = channel or self.channel
        self.protocol.request("PUBLISH", channel, json.dumps(data))


class Redis(Plugin):
    host         = Plugin.Property(default="localhost")
    port         = Plugin.Property(default=6379)
    channel      = Plugin.Property(default="mark2-{server}")
    relay_events = Plugin.Property(default="StatPlayers,PlayerJoin,PlayerQuit,PlayerChat,PlayerDeath")

    def setup(self):
        channel = self.channel.format(server=self.parent.server_name)
        self.factory = RedisFactory(self, channel)
        reactor.connectTCP(self.host, self.port, self.factory)
        for ev in self.relay_events.split(','):
            ty = events.get_by_name(ev.strip())
            if ty:
                self.register(self.on_event, ty)
            else:
                self.console("redis: couldn't bind to event: {0}".format(ev))

    def on_event(self, event):
        self.factory.relay(event.serialize())

########NEW FILE########
__FILENAME__ = rss
import feedparser
import re
from twisted.web.client import getPage

from mk2.plugins import Plugin

reddit_link = re.compile('http://(?:www\.)?redd(?:\.it/|it\.com/(?:tb|(?:r/[\w\.]+/)?comments)/)(\w+)(/.+/)?(\w{7})?')


#Many thanks to Adam Wight for this
class FeedPoller(object):
    last_seen_id = None

    def parse(self, data):
        result = feedparser.parse(data)
        result.entries.reverse()
        skipping = True
        for entry in result.entries:
            if (self.last_seen_id == entry.id):
                skipping = False
            elif not skipping:
                yield entry

        if result.entries:
            self.last_seen_id = result.entries[-1].id


class RSS(Plugin):
    url = Plugin.Property(default="")
    check_interval = Plugin.Property(default=60)
    command = Plugin.Property(default="say {link} - {title}")
    
    def setup(self):
        self.poller = FeedPoller()
        
    def server_started(self, event):
        if self.url != "":
            self.repeating_task(self.check_feeds, self.check_interval)
    
    def check_feeds(self, event):
        d = getPage(self.url)
        d.addCallback(self.update_feeds)
    
    def update_feeds(self, data):
        for entry in self.poller.parse(data):
            m = reddit_link.match(entry['link'])
            if m:
                entry['link'] = "http://redd.it/" + m.group(1)
            self.send_format(self.command, **entry)

########NEW FILE########
__FILENAME__ = save
from mk2.plugins import Plugin
from mk2.events import Hook


class Save(Plugin):
    warn_message = Plugin.Property(default="WARNING: saving map in {delay}.")
    message      = Plugin.Property(default="MAP IS SAVING.")
    
    def setup(self):
        self.register(self.save, Hook, public=True, name='save', doc='save the map')
    
    def warn(self, delay):
        self.send_format("say %s" % self.warn_message, delay=delay)
    
    def save(self, event):
        action = self.save_real
        if event.args:
            warn_length, action = self.action_chain(event.args, self.warn, action)
        action()
        event.handled = True

    def save_real(self):
        if self.message:
            self.send('say %s' % self.message)
        self.send('save-all')
    

########NEW FILE########
__FILENAME__ = script
import re
import os.path
import pwd
from time import localtime
from collections import namedtuple

from twisted.internet import protocol, reactor, defer

from mk2.plugins import Plugin
from mk2 import events

time_bounds = [(0, 59), (0, 23), (1, 31), (1, 12), (1, 7)]


class ScriptEntry(object):
    event = None
    ranges = None
    
    def __init__(self, plugin, line):
        self.plugin = plugin
        
        line = line.strip()
        if line.startswith('@'):
            self.type = "event"
            event_name, command = re.match(r'^@([^\s]+)\s+(.+)$', line).groups()
            event = events.get_by_name(event_name)
            if not event:
                raise ValueError("unknown event: %s" % event_name)
            self.plugin.register(lambda e: self.execute(command), event)
        else:
            self.type = "time"
            bits = re.split(r'\s+', line, 5)
            time_spec, self.command = bits[:5], bits[5]
            self.ranges = self.parse_time(time_spec)
    
    def parse_time(self, time_spec):
        Range = namedtuple('Range', ('min', 'max', 'skip'))
        ranges = []
        for spec_i, bound_i in zip(time_spec, time_bounds):
            n, top, skip = re.match(r'^(\d{1,2}|\*)(?:-(\d{1,2}))?(?:/(\d{1,2}))?$', spec_i).groups()
            if n == '*':
                if top:
                    raise ValueError("can't use * in a range expression")
                ranges.append(Range(bound_i[0], bound_i[1], int(skip or 1)))
            else:
                ranges.append(Range(int(n), int(top or n), int(skip or 1)))
        return ranges
 
    def execute(self, cmd):
        execute = defer.succeed(None)

        def execute_next(fn, *a, **kw):
            execute.addCallback(lambda r: fn(*a, **kw))
            execute.addErrback(lambda f: True)

        if cmd.startswith('$'):
            cmd = cmd[1:]
            d = defer.Deferred()

            p = protocol.ProcessProtocol()
            p.outReceived = lambda d: [execute_next(self.execute_reduced, l, cmd) for l in d.split("\n")]
            p.processEnded = lambda r: d.callback(None)

            reactor.spawnProcess(p, self.plugin.shell, [self.plugin.shell, '-c', cmd])

            d.addCallback(lambda r: execute)
            return d
        else:
            return self.execute_reduced(cmd)
    
    @defer.inlineCallbacks
    def execute_reduced(self, cmd, source='script'):
        if cmd.startswith('~'):
            handled = yield self.plugin.dispatch(events.Hook(line=cmd))
            if not handled:
                self.plugin.console("unknown command in script: %s" % cmd)
        elif cmd.startswith('/'):
            self.plugin.send(cmd[1:])
        elif cmd.startswith('#'):
            self.plugin.console("#{0}".format(cmd[1:]), user=source, source="user")
        elif cmd:
            self.plugin.console("couldn't understand script input: %s" % cmd)

    def step(self):
        if self.type != 'time':
            return
        time = localtime()
        time = [time.tm_min, time.tm_hour, time.tm_mday, time.tm_mon, time.tm_wday + 1]
        
        for r, t in zip(self.ranges, time):
            if not t in range(r.min, r.max + 1, r.skip):
                return
        
        self.execute(self.command)


class Script(Plugin):
    path = Plugin.Property(default='scripts.txt')
    shell = Plugin.Property(default='/bin/sh')
    
    def setup(self):
        self.scripts = []
        if not os.path.isfile(self.path):
            return
        
        with open(self.path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or line == '':
                    continue
                try:
                    self.scripts.append(ScriptEntry(self, line))
                except Exception as e:
                    self.console('invalid script line: %s' % line, kind='error')
                    self.console(str(e))
        
        for script in self.scripts:
            if script.type == 'time':
                self.delayed_task(lambda a: self.repeating_task(self.step, 60, now=True),
                                  max(0, 60 - localtime().tm_sec) % 60 + 1)
                break

    def step(self, event):
        for script in self.scripts:
            script.step()

    def server_stopping(self, event):
        pass  # don't cancel tasks

########NEW FILE########
__FILENAME__ = shutdown
from mk2.plugins import Plugin
from mk2.events import Hook, ServerStop, StatPlayers, StatPlayerCount


class Shutdown(Plugin):
    restart_warn_message   = Plugin.Property(default="WARNING: planned restart in {delay}.")
    stop_warn_message      = Plugin.Property(default="WARNING: server going down for planned maintainence in {delay}.")
    restart_message        = Plugin.Property(default="Server restarting.")
    stop_message           = Plugin.Property(default="Server going down for maintainence.")
    restart_cancel_message = Plugin.Property(default="WARNING: planned restart cancelled.")
    restart_cancel_reason  = Plugin.Property(default="WARNING: planned restart cancelled ({reason}).")
    stop_cancel_message    = Plugin.Property(default="WARNING: planned maintenance cancelled.")
    stop_cancel_reason     = Plugin.Property(default="WARNING: planned maintenance cancelled ({reason}).")
    kick_command           = Plugin.Property(default="kick {player} {message}")
    kick_mode              = Plugin.Property(default="all")
    
    failsafe = None

    cancel_preempt = 0

    restart_on_empty = False

    restore = ('cancel_preempt', 'cancel', 'restart_on_empty')
    
    def setup(self):
        self.players = []
        self.cancel = []
        
        self.register(self.handle_players, StatPlayers)
        self.register(self.handle_player_count, StatPlayerCount)
        
        self.register(self.h_stop,          Hook, public=True, name="stop",         doc='cleanly stop the server. specify a delay like `~stop 2m`')
        self.register(self.h_restart,       Hook, public=True, name="restart",      doc='cleanly restart the server. specify a delay like `~restart 30s`')
        self.register(self.h_restart_empty, Hook, public=True, name="restart-empty",doc='restart the server next time it has 0 players')
        self.register(self.h_kill,          Hook, public=True, name="kill",         doc='kill the server')
        self.register(self.h_kill_restart,  Hook, public=True, name="kill-restart", doc='kill the server and bring it back up')
        self.register(self.h_cancel,        Hook, public=True, name="cancel",       doc='cancel an upcoming shutdown or restart')

    def server_started(self, event):
        self.restart_on_empty = False
        self.cancel_preempt = 0
    
    def warn_restart(self, delay):
        self.send_format("say %s" % self.restart_warn_message, delay=delay)
    
    def warn_stop(self, delay):
        self.send_format("say %s" % self.stop_warn_message, delay=delay)

    def warn_cancel(self, reason, thing):
        if reason:
            message = self.restart_cancel_reason if thing == "restart" else self.stop_cancel_reason
        else:
            message = self.restart_cancel_message if thing == "restart" else self.stop_cancel_message
        self.send_format("say %s" % message, reason=reason)

    def nice_stop(self, respawn, kill):
        if not kill:
            message = self.restart_message if respawn else self.stop_message
            if self.kick_mode == 'all':
                for player in self.players:
                    self.send_format(self.kick_command, player=player, message=message)
            elif self.kick_mode == 'once':
                self.send_format(self.kick_command, message=message)
        self.dispatch(ServerStop(reason='console', respawn=respawn, kill=kill))

    def handle_players(self, event):
        self.players = event.players

    def handle_player_count(self, event):
        if event.players_current == 0 and self.restart_on_empty:
            self.restart_on_empty = False
            self.nice_stop(True, False)

    def cancel_something(self, reason=None):
        thing, cancel = self.cancel.pop(0)
        cancel(reason, thing)

    def should_cancel(self):
        if self.cancel_preempt:
            self.cancel_preempt -= 1
            return True
        else:
            return False
    
    #Hook handlers:
    def h_stop(self, event=None):
        if self.should_cancel():
            self.console("I'm not stopping because this shutdown was cancelled with ~cancel")
            return
        action = lambda: self.nice_stop(False, False)
        if event and event.args:
            warn_length, action, cancel = self.action_chain_cancellable(event.args, self.warn_stop, action, self.warn_cancel)
            self.cancel.append(("stop", cancel))
        action()

    def h_restart(self, event=None):
        if self.should_cancel():
            self.console("I'm not restarting because this shutdown was cancelled with ~cancel")
            return
        action = lambda: self.nice_stop(True, False)
        if event and event.args:
            warn_length, action, cancel = self.action_chain_cancellable(event.args, self.warn_restart, action, self.warn_cancel)
            self.cancel.append(("restart", cancel))
        action()

    def h_restart_empty(self, event):
        if self.restart_on_empty:
            self.console("I was already going to do that")
        else:
            self.console("I will restart the next time the server empties")
        self.restart_on_empty = True
    
    def h_kill(self, event):
        self.nice_stop(False, True)
    
    def h_kill_restart(self, event):
        self.nice_stop(True, True)

    def h_cancel(self, event):
        if self.cancel:
            self.cancel_something(event.args or None)
        else:
            self.cancel_preempt += 1
            self.console("I will cancel the next thing")

########NEW FILE########
__FILENAME__ = su
from mk2.plugins import Plugin
from mk2.events import UserInput


class Su(Plugin):
    command = Plugin.Property(default="sudo -su {user} -- {command}")
    mode = Plugin.Property(default="include")
    proc = Plugin.Property(default="ban;unban")
    
    def setup(self):
        self.register(self.uinput, UserInput)
    
    def uinput(self, event):
        handled = False
        for p in self.proc.split(";"):
            if event.line.startswith(p):
                handled = True
                break
        
        if (self.mode == 'exclude') ^ handled:
            event.line = self.command.format(user=event.user, command=event.line)

########NEW FILE########
__FILENAME__ = trigger
import os
import re

from mk2.plugins import Plugin
from mk2.events import ServerOutput


class Trigger(Plugin):
    command = Plugin.Property(default="msg {user} {message}")
    path = Plugin.Property(default="triggers.txt")
    
    triggers = {}
    
    def setup(self):
        if self.path and os.path.exists(self.path):
            f = open(self.path, 'r')
            for l in f:
                m = re.match('^\!?([^,]+),(.+)$', l)
                if m:
                    a, b = m.groups()
                    c = self.triggers.get(a, [])
                    c.append(b)
                    self.triggers[a] = c
            f.close()
            
            if self.triggers:
                self.register(self.trigger, ServerOutput, pattern='<([A-Za-z0-9_]{1,16})> \!(\w+)')
    
    def trigger(self, event):
        user, trigger = event.match.groups()
        if trigger in self.triggers:
            for line in self.triggers[trigger]:
                self.send(self.command.format(user=user, message=line))

########NEW FILE########
__FILENAME__ = properties
import os
import re
import shlex
import zipfile


def load(cls, *files):
    o = None
    for f in files:
        if isinstance(f, basestring):
            if os.path.isfile(f):
                with open(f) as f:
                    o = cls(f, o)
        else:
            o = cls(f, 0)
    return o


def load_jar(jar, *path):
    path = list(path)
    while path:
        try:
            z = zipfile.ZipFile(jar, 'r')
            o = Lang(z.open(path.pop(0), 'r'))
            z.close()
            return o
        except KeyError:
            pass
    return None


class Properties(dict):
    def __init__(self, f, parent=None):
        dict.__init__(self)

        if parent:
            self.update(parent)
            self.types = dict(parent.types)
        else:
            self.types = {}

        decoder = {
            'int': int,
            'bool': lambda a: a == 'true',
            'string': lambda a: a
        }

        c_seperator  = (':', '=')
        c_whitespace = (' ', '\t', '\f')
        c_escapes    = ('t','n','r','f')
        c_comment    = ('#','!')

        r_unescaped  = '(?<!\\\\)(?:\\\\\\\\)*'
        r_whitespace = '[' + re.escape(''.join(c_whitespace)) + ']*'
        r_seperator  = r_unescaped + r_whitespace + r_unescaped + '[' + re.escape(''.join(c_seperator + c_whitespace)) + ']'

        #This handles backslash escapes in keys/values
        def parse(input):
            token = list(input)
            out = u""
            uni = False
            while len(token) > 0:
                c = token.pop(0)
                if c == '\\':
                    try:
                        c = token.pop(0)
                        if c in c_escapes:
                            out += ('\\'+c).decode('string-escape')
                        elif c == 'u':
                            b = ""
                            for i in range(4):
                                b += token.pop(0)
                            out += unichr(int(b, 16))
                            uni = True
                        else:
                            out += c
                    except IndexError:
                        raise ValueError("Invalid escape sequence in input: %s" % input)
                else:
                    out += c

            if not uni:
                out = out.encode('ascii')
            return out

        d = f.read()

        #Deal with Windows / Mac OS linebreaks
        d = d.replace('\r\n','\n')
        d = d.replace('\r', '\n')
        #Strip leading whitespace
        d = re.sub('(?m)\n\s*', '\n', d)
        #Split logical lines
        d = re.split('(?m)' + r_unescaped + '\n', d)

        for line in d:
            #Strip comments and empty lines
            if line == '' or line[0] in c_comment:
                continue

            #Strip escaped newlines
            line = re.sub('(?m)' + r_unescaped + '(\\\\\n)', '', line)
            assert not '\n' in line

            #Split into k,v
            x = re.split(r_seperator, line, maxsplit=1)

            #No seperator, parse as empty value.
            if len(x) == 1:
                k, v = x[0], ""
            else:
                k, v = x

            k = parse(k).replace('-', '_')
            v = parse(v)

            if re.match('^\-?\d+$', v):
                ty = 'int'
            elif v in ('true', 'false'):
                ty = 'bool'
            elif v != '':
                ty = 'string'
            elif k in self.types:
                ty = self.types[k]
            else:
                ty = 'string'

            self.types[k] = ty
            self[k] = decoder[ty](v)
        f.close()

    def get_by_prefix(self, prefix):
        for k, v in self.iteritems():
            if k.startswith(prefix):
                yield k[len(prefix):], v


class Mark2Properties(Properties):
    def get_plugins(self):
        plugins = {}
        enabled = []
        for k, v in self.iteritems():
            m = re.match('^plugin\.(.+)\.(.+)$', k)
            if m:
                plugin, k2 = m.groups()
                
                if plugin not in plugins:
                    plugins[plugin] = {}
                
                if k2 == 'enabled':
                    if v:
                        enabled.append(plugin)
                else:
                    plugins[plugin][k2] = v

        return [(n, plugins[n]) for n in sorted(enabled)]

    def get_service(self, service):
        return self.get_by_prefix('mark2.service.{0}.'.format(service))

    def get_jvm_options(self):
        options = []
        for k, v in self.iteritems():
            m = re.match('^java\.cli\.([^\.]+)\.(.+)$', k)
            if m:
                a, b = m.groups()
                if a == 'D':
                    options.append('-D%s=%s' % (b, v))
                elif a == 'X':
                    options.append('-X%s%s' % (b, v))
                elif a == 'XX':
                    if v in (True, False):
                        options.append('-XX:%s%s' % ('+' if v else '-', b))
                    else:
                        options.append('-XX:%s=%s' % (b, v))
                else:
                    print "Unknown JVM option type: %s" % a
        if self.get('java.cli_extra', '') != '':
            options.extend(shlex.split(self['java.cli_extra']))
        return options
    
    def get_format_options(self):
        options = {}
        for k, v in self.iteritems():
            m = re.match('^mark2\.format\.(.*)$', k)
            if m:
                options[m.group(1)] = v
        return options

    def get_umask(self, ext):
        return int(str(self['mark2.umask.' + ext]), 8)

class ClientProperties(Properties):
    def get_palette(self):
        palette = []
        for k, v in self.get_by_prefix('theme.%s.' % self['theme']):
            palette.append([k,] + [t.strip() for t in v.split(',')])
        return palette

    def get_player_actions(self):
        return self['player_actions'].split(',')

    def get_player_reasons(self):
        return self.get_by_prefix('player_actions.reasons.')

    def get_apps(self):
        return self.get_by_prefix('stats.app.')

    def get_interval(self, name):
        return self['task.%s' % name]

class Lang(Properties):
    def get_deaths(self):
        seen = []
        for k, v in self.get_by_prefix('death.'):
            if not v in seen:
                seen.append(v)
                regex = reduce(lambda a, r: a.replace(*r),
                               ((r"\%{0}\$s".format(i + 1),
                                 "(?P<{0}>[A-Za-z0-9]{{1,32}})".format(x))
                                for i, x in enumerate(("username", "killer", "weapon"))),
                               re.escape(v))
                format = reduce(lambda a, r: a.replace(*r),
                                (("%{0}$s".format(i + 1),
                                  "{{{0}}}".format(x))
                                 for i, x in enumerate(("username", "killer", "weapon"))),
                                v)
                yield k, ("^{0}$".format(regex), format)

########NEW FILE########
__FILENAME__ = bukkit
import json

from . import JarProvider


class Bukkit(JarProvider):
    def work(self):
        self.get('http://dl.bukkit.org/api/1.0/downloads/channels/?_accept=application/json', self.handle_channels)

    def handle_channels(self, data):
        data = json.loads(data)
        for channel in data['results']:
            name = channel['name']
            slug = channel['slug']
            self.add(('Bukkit', name), (None, slug), 'http://dl.bukkit.org/latest-%s/craftbukkit.jar' % slug)

        self.commit()

ref = Bukkit

########NEW FILE########
__FILENAME__ = feed_the_beast
import re
from hashlib import md5
from xml.dom import minidom

from . import JarProvider

class FeedTheBeast(JarProvider):
    base = 'http://www.creeperrepo.net/'
    def work(self):
        self.get(self.base+'getdate', self.handle_date)

    def handle_date(self, data):
        hash = md5()
        hash.update('mcepoch1' + data)
        self.token = hash.hexdigest()
        self.get(self.base+'static/FTB2/modpacks.xml', self.handle_packs)

    def handle_packs(self, data):
        attr = lambda n, name: n.attributes[name].value

        dom = minidom.parseString(data)

        for node in dom.getElementsByTagName('modpack'):
            filename = attr(node, 'serverPack')
            if filename == "":
                continue

            artifact = attr(node, 'name')
            artifact = re.sub(' Pack$',           '', artifact)
            artifact = re.sub('^Feed The Beast ', '', artifact)
            artifact = re.sub('^FTB ',            '', artifact)

            url = self.base + 'direct/FTB2/' + self.token + '/'
            url+= '^'.join((
                'modpacks',
                attr(node, 'dir'),
                attr(node, 'version').replace('.', '_'),
                filename))

            self.add(('Feed The Beast', artifact), ('ftb', None), url)

        self.commit()

ref = FeedTheBeast

########NEW FILE########
__FILENAME__ = forge
from . import JarProvider

class Forge(JarProvider):
    base = 'http://files.minecraftforge.net/minecraftforge/minecraftforge-universal-{0}.zip'
    def work(self):
        for k in 'latest', 'recommended':
            self.add(('Forge', k.title()), (None, None), self.base.format(k))
        self.commit()

ref = Forge

########NEW FILE########
__FILENAME__ = mcpcplus
from . import JenkinsJarProvider

class MCPCPlus(JenkinsJarProvider):
    name = 'MCPC-Plus'
    base = 'http://ci.md-5.net/'
    project = 'MCPC-Plus'

ref = MCPCPlus

########NEW FILE########
__FILENAME__ = spigot
from . import JenkinsJarProvider

class Spigot(JenkinsJarProvider):
    name = 'Spigot'
    base = 'http://ci.md-5.net/'
    project = 'Spigot'

ref = Spigot

########NEW FILE########
__FILENAME__ = technic
import json
from . import JarProvider

class Technic(JarProvider):
    api_base = 'http://solder.technicpack.net/api/modpack/?include=full'
    packs   = (
        ('bigdig',     'BigDigServer-v{0}.zip'),
        ('tekkit',     'Tekkit_Server_{0}.zip'),
        ('tekkitlite', 'Tekkit_Lite_Server_{0}.zip'),
        ('voltz',      'Voltz_Server_v{0}.zip'))
    builds = ('recommended', 'latest')

    def work(self):
        self.get(self.api_base, self.handle_data)

    def handle_data(self, data):
        data = json.loads(data)
        base = data['mirror_url']
        for name, server in self.packs:
            mod = data['modpacks'][name]
            title = mod['display_name']
            title = 'Tekkit Classic' if title == 'Tekkit' else title
            for build in self.builds:
                self.add(('Technic', title, build.title()), (None, None, None),
                          base + 'servers/' + name + '/' + server.format(mod[build]))
        self.commit()

ref = Technic

########NEW FILE########
__FILENAME__ = vanilla
import json

from . import JarProvider

class Vanilla(JarProvider):
    base = 'http://s3.amazonaws.com/Minecraft.Download/versions/'
    def work(self):
        self.get(self.base + 'versions.json', self.handle_data)

    def handle_data(self, data):
        for k, v in json.loads(data)['latest'].iteritems():
            self.add(('Vanilla', k.title()), (None, None), '{0}{1}/minecraft_server.{1}.jar'.format(self.base, v))
        self.commit()

ref = Vanilla

########NEW FILE########
__FILENAME__ = builtin
from mk2 import events, properties
from mk2.services import process
from mk2.shared import find_config, open_resource
from mk2.plugins import Plugin

import os


class Builtin(Plugin):
    def setup(self):
        self.register(self.handle_cmd_help,          events.Hook, public=True, name="help", doc="displays this message")
        self.register(self.handle_cmd_events,        events.Hook, public=True, name="events", doc="lists events")
        self.register(self.handle_cmd_plugins,       events.Hook, public=True, name="plugins", doc="lists running plugins")
        self.register(self.handle_cmd_reload_plugin, events.Hook, public=True, name="reload-plugin", doc="reload a plugin")
        self.register(self.handle_cmd_rehash,        events.Hook, public=True, name="rehash", doc="reload config and any plugins that changed")
        self.register(self.handle_cmd_reload,        events.Hook, public=True, name="reload", doc="reload config and all plugins")
        self.register(self.handle_cmd_jar,           events.Hook, public=True, name="jar", doc="wrap a different server jar")
    
    def table(self, v):
        m = 0
        for name, doc in v:
            m = max(m, len(name))
        
        for name, doc in sorted(v, key=lambda x: x[0]):
            self.console(" ~%s | %s" % (name.ljust(m), doc))

    def handle_cmd_help(self, event):
        o = []
        for _, callback, args in self.parent.events.get(events.Hook):
            if args.get('public', False):
                o.append((args['name'], args.get('doc', '')))
        
        self.console("The following commands are available:")
        self.table(o)
    
    def handle_cmd_events(self, event):
        self.console("The following events are available:")
        self.table([(n, c.doc) for n, c in events.get_all()])

    def handle_cmd_plugins(self, events):
        self.console("These plugins are running: " + ", ".join(sorted(self.parent.plugins.keys())))

    def handle_cmd_reload_plugin(self, event):
        if event.args in self.parent.plugins:
            self.parent.plugins.reload(event.args)
            self.console("%s reloaded." % event.args)
        else:
            self.console("unknown plugin.")

    def handle_cmd_rehash(self, event):
        # make a dict of old and new plugin list
        plugins_old = dict(self.parent.config.get_plugins())
        self.parent.load_config()
        plugins_new = dict(self.parent.config.get_plugins())
        # reload the union of old plugins and new plugins
        requires_reload = set(plugins_old.keys()) | set(plugins_new.keys())
        # (except plugins whose config is exactly the same)
        for k in list(requires_reload):
            if plugins_old.get(k, False) == plugins_new.get(k, False):
                requires_reload.remove(k)
        requires_reload = list(requires_reload)
        # actually reload
        for p in requires_reload:
            self.parent.plugins.reload(p)
        reloaded = filter(None, requires_reload)
        self.console("%d plugins reloaded: %s" % (len(reloaded), ", ".join(reloaded)))

    def handle_cmd_reload(self, event):
        self.parent.plugins.unload_all()
        self.parent.load_config()
        self.parent.load_plugins()
        self.console("config + plugins reloaded.")

    def handle_cmd_jar(self, event):
        new_jar = process.find_jar(
            self.parent.config['mark2.jar_path'].split(';'),
            event.args)
        if new_jar:
            self.console("I will switch to {0} at the next restart".format(new_jar))
            self.parent.jar_file = new_jar
        else:
            self.console("Can't find a matching jar file.")

########NEW FILE########
__FILENAME__ = console_tracking
from mk2 import properties
from mk2.events import PlayerChat, PlayerDeath, PlayerJoin, PlayerQuit, ServerOutput
from mk2.plugins import Plugin

import re


class ConsoleTracking(Plugin):
    deaths = tuple()
    chat_events = tuple()

    def setup(self):
        lang = properties.load_jar(self.parent.jar_file, 'assets/minecraft/lang/en_US.lang', 'lang/en_US.lang')
        if lang is not None:
            self.deaths = tuple(lang.get_deaths())
            self.register(self.death_handler, ServerOutput, pattern=".*")

        self.register_chat()

    def register_chat(self):
        ev = []
        for key, e_ty in (('join', PlayerJoin),
                          ('quit', PlayerQuit),
                          ('chat', PlayerChat)):
            pattern = self.parent.config['mark2.regex.' + key]
            try:
                re.compile(pattern)
            except:
                return self.fatal_error(reason="mark2.regex.{0} isn't a valid regex!".format(key))
            ev.append(self.register(lambda e, e_ty=e_ty: self.dispatch(e_ty(**e.match.groupdict())),
                                    ServerOutput,
                                    pattern=pattern))
        self.chat_events = tuple(ev)

    def death_handler(self, event):
        for name, (pattern, format) in self.deaths:
            m = re.match(pattern, event.data)
            if m:
                self.dispatch(PlayerDeath(cause=None,
                                          format=format,
                                          **m.groupdict()))
                break

########NEW FILE########
__FILENAME__ = ping
import struct

from twisted.internet import task, reactor
from twisted.internet.protocol import Protocol, ClientFactory

from mk2.events import Event, StatPlayerCount, ServerOutput
from mk2.plugins import Plugin


class PingProtocol(Protocol):
    def connectionMade(self):
        self.buff = ""
        self.transport.write('\xFE\x01')
    
    def dataReceived(self, data):
        self.buff += data
        if len(self.buff) >= 3:
            l = struct.unpack('>h', self.buff[1:3])[0]
            
            if len(self.buff) >= 3 + l * 2:
                data = self.buff[9:].decode('utf-16be').split('\x00')
                self.dispatch(StatPlayerCount(source='ping', players_current=int(data[3]), players_max=int(data[4])))
                self.transport.loseConnection()


class PingFactory(ClientFactory):
    noisy = False
    
    def __init__(self, dispatch):
        self.dispatch = dispatch
    
    def buildProtocol(self, addr):
        pr = PingProtocol()
        pr.dispatch = self.dispatch
        return pr


class Ping(Plugin):
    alive = False
    event_id = None

    interval = Plugin.Property(default=10)
    
    def setup(self):
        self.host = self.parent.properties['server_ip'] or '127.0.0.1'

        self.task = task.LoopingCall(self.loop)
        self.task.start(self.interval, now=False)

    def server_started(self, event):
        ping_pattern = r"\s*(?:/{0}:\d+ lost connection|Reached end of stream for /{0})"
        if self.event_id:
            self.parent.events.unregister(self.event_id)
        self.event_id = self.parent.events.register(lambda ev: Event.EAT, ServerOutput,
                                                    pattern=ping_pattern.format(self.host))

    def loop(self):
        host = self.parent.properties['server_ip'] or '127.0.0.1'
        port = self.parent.properties['server_port']

        factory = PingFactory(self.parent.events.dispatch)

        reactor.connectTCP(host, port, factory, bindAddress=(self.host, 0))

########NEW FILE########
__FILENAME__ = process
import locale
from twisted.internet import protocol, reactor, error, defer, task
import glob
import psutil
import shlex


from mk2 import events
from mk2.events import EventPriority
from mk2.plugins import Plugin


class ProcessProtocol(protocol.ProcessProtocol):
    obuff = u""
    alive = True

    def __init__(self, dispatch, locale):
        self.dispatch = dispatch
        self.locale = locale

    def output(self, line):
        self.dispatch(events.ServerOutput(line=line))

    def childDataReceived(self, fd, data):
        if data[0] == '\b':
            data = data.lstrip(' \b')
        data = data.decode(self.locale)
        data = data.split("\n")
        data[0] = self.obuff + data[0]
        self.obuff = data.pop()
        for l in data:
            self.output(l.strip('\r'))

    def makeConnection(self, transport):
        self.dispatch(events.ServerStarting(pid=transport.pid))

    def processEnded(self, reason):
        self.alive = False
        if isinstance(reason.value, error.ProcessTerminated) and reason.value.exitCode:
            self.dispatch(events.ServerEvent(cause='server/error/exit-failure',
                                             data="server exited abnormally: {0}".format(reason.getErrorMessage()),
                                             priority=1))
            self.dispatch(events.FatalError(reason=reason.getErrorMessage()))
        else:
            self.dispatch(events.ServerStopped())


class Process(Plugin):
    name = "process"
    protocol = None
    respawn = False
    service_stopping = None
    transport = None
    failsafe = None
    stat_process = None
    done_pattern = Plugin.Property(default='Done \\(([0-9\\.]+)s\\)\\!.*')
    stop_cmd = Plugin.Property(default='stop\n')
    java_path = Plugin.Property(default='java')
    server_args = Plugin.Property(default='')

    def setup(self):
        self.register(self.server_input,    events.ServerInput,    priority=EventPriority.MONITOR)
        self.register(self.server_start,    events.ServerStart,    priority=EventPriority.MONITOR)
        self.register(self.server_starting, events.ServerStarting)
        self.register(self._server_started, events.ServerOutput, pattern=self.done_pattern)
        self.register(self.server_stop,     events.ServerStop,     priority=EventPriority.MONITOR)
        self.register(self.server_stopping, events.ServerStopping, priority=EventPriority.MONITOR)
        self.register(self.server_stopped,  events.ServerStopped,  priority=EventPriority.MONITOR)

        reactor.addSystemEventTrigger('before', 'shutdown', self.before_reactor_stop)

    def build_command(self):
        cmd = []
        cmd.append(self.java_path)
        #cmd.append('-server')
        cmd.extend(self.parent.config.get_jvm_options())
        cmd.append('-jar')
        cmd.append(self.parent.jar_file)
        cmd.append('nogui')
        cmd.extend(shlex.split(self.server_args))
        return cmd

    def server_start(self, e=None):
        self.parent.console("starting minecraft server")
        self.locale = locale.getpreferredencoding()
        self.protocol = ProcessProtocol(self.parent.events.dispatch, self.locale)
        cmd = self.build_command()

        self.transport = reactor.spawnProcess(self.protocol, cmd[0], cmd, env=None)
        if e:
            e.handled = True

    def server_input(self, e):
        if self.protocol and self.protocol.alive:
            l = e.line
            if not l.endswith('\n'):
                l += '\n'
            self.transport.write(l.encode(self.locale, 'ignore'))
            e.handled = True

    def server_starting(self, e):
        self.stat_process = task.LoopingCall(self.update_stat, psutil.Process(e.pid))
        self.stat_process.start(self.parent.config['java.ps.interval'])

    def _server_started(self, e):
        self.parent.events.dispatch(events.ServerStarted())

    @defer.inlineCallbacks
    def server_stop(self, e):
        e.handled = True
        if self.protocol is None or not self.protocol.alive:
            return
        if e.announce:
            yield self.parent.events.dispatch(events.ServerStopping(respawn=e.respawn, reason=e.reason, kill=e.kill))
        if e.kill:
            self.failsafe = None
            self.parent.console("killing minecraft server")
            self.transport.signalProcess('KILL')
        else:
            self.parent.console("stopping minecraft server")
            self.transport.write(self.stop_cmd)
            self.failsafe = self.parent.events.dispatch_delayed(events.ServerStop(respawn=e.respawn, reason=e.reason, kill=True, announce=False), self.parent.config['mark2.shutdown_timeout'])

    def server_stopping(self, e):
        self.respawn = e.respawn

    def server_stopped(self, e):
        if self.stat_process and self.stat_process.running:
            self.stat_process.stop()
        if self.failsafe:
            self.failsafe.cancel()
            self.failsafe = None
        if self.respawn:
            self.parent.events.dispatch(events.ServerStart())
            self.respawn = False
        elif self.service_stopping:
            self.service_stopping.callback(0)
        else:
            print "I'm stopping the reactor now"
            reactor.stop()

    def update_stat(self, process):
        try:
            self.parent.events.dispatch(events.StatProcess(cpu=process.get_cpu_percent(interval=0), memory=process.get_memory_percent()))
        except psutil.error.NoSuchProcess:
            pass

    def before_reactor_stop(self):
        if self.protocol and self.protocol.alive:
            self.parent.events.dispatch(events.ServerStop(reason="SIGINT", respawn=False))
            self.service_stopping = defer.Deferred()
            return self.service_stopping


def find_jar(search_patterns, hint=None):
    if hint:
        search_patterns.insert(0, hint)
    for pattern in search_patterns:
        g = glob.glob(pattern)
        if g:
            return g[0]

########NEW FILE########
__FILENAME__ = user_server
from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver

import os
import json

from mk2 import events
from mk2.plugins import Plugin


class Scrollback:
    def __init__(self, length):
        self.length = length
        self.data = []

    def put(self, line):
        self.data.append(line)
        if len(self.data) > self.length:
            self.data.pop(0)

    def get(self, max_items=None):
        if max_items is None:
            return self.data[:]
        else:
            return self.data[-max_items:]


class UserServerProtocol(LineReceiver):
    MAX_LENGTH = 999999
    delimiter = '\n'
    
    tab_last = None
    tab_index = 0
    
    attached_user = None
    
    def connectionMade(self):
        self._handlers = []
        for callback, ty in (
            (self.console_helper, events.Console),
            (self.handle_attach,  events.UserAttach),
            (self.handle_detach,  events.UserDetach)):
            self._handlers.append(self.register(callback, ty))
    
    def connectionLost(self, reason):
        if self.attached_user:
            self.dispatch(events.UserDetach(user=self.attached_user))

        for i in self._handlers:
            self.unregister(i)
        self._handlers = []
    
    def lineReceived(self, line):
        msg = json.loads(str(line))
        ty = msg["type"]
        
        if ty == "attach":
            self.attached_user = msg['user']
            self.dispatch(events.UserAttach(user=msg['user']))

        elif ty == "input":
            self.dispatch(events.UserInput(user=msg['user'], line=msg['line']))
        
        elif ty == "get_scrollback":
            self.send_helper("regex", patterns=dict(self.factory.parent.config.get_by_prefix('mark2.regex.')))
            self.send_helper("scrollback", lines=[e.serialize() for e in self.factory.scrollback.get()])

        elif ty == "get_users":
            for u in self.factory.users:
                self.send_helper("user_status", user=u, online=True)

        elif ty == "get_stats":
            self.send_helper("stats", stats=self.factory.stats)

        elif ty == "get_players":
            self.send_helper("players", players=self.factory.players)
        
        else:
            self.factory.parent.console("unknown packet: %s" % str(msg))
        
    def send_helper(self, ty, **k):
        k["type"] = ty
        self.sendLine(json.dumps(k))
    
    def console_helper(self, event):
        self.send_helper("console", **event.serialize())
    
    def handle_attach(self, event):
        self.send_helper("user_status", user=event.user, online=True)
    
    def handle_detach(self, event):
        self.send_helper("user_status", user=event.user, online=False)


class UserServerFactory(Factory):
    players = []
    
    def __init__(self, parent):
        self.parent     = parent
        self.scrollback = Scrollback(200)
        self.users      = set()
        
        self.parent.events.register(self.handle_console, events.Console)
        self.parent.events.register(self.handle_attach,  events.UserAttach)
        self.parent.events.register(self.handle_detach,  events.UserDetach)
        
        self.parent.events.register(self.handle_player_count, events.StatPlayerCount)
        self.parent.events.register(self.handle_players,      events.StatPlayers)
        self.parent.events.register(self.handle_process,      events.StatProcess)
        
        self.stats = dict((k, '___') for k in ('memory', 'cpu', 'players_current', 'players_max'))
    
    def buildProtocol(self, addr):
        p = UserServerProtocol()
        p.register   = self.parent.events.register
        p.unregister = self.parent.events.unregister
        p.dispatch   = self.parent.events.dispatch
        p.factory    = self
        return p

    def handle_console(self, event):
        self.scrollback.put(event)
    
    def handle_attach(self, event):
        self.users.add(event.user)
    
    def handle_detach(self, event):
        self.users.discard(event.user)
    
    #stat handlers
    def handle_player_count(self, event):
        self.stats['players_current'] = event.players_current
        self.stats['players_max']     = event.players_max
        
    def handle_players(self, event):
        self.players = sorted(event.players, key=str.lower)
    
    def handle_process(self, event):
        for n in ('cpu', 'memory'):
            self.stats[n] = '{0:.2f}'.format(event[n])


class UserServer(Plugin):
    def setup(self):
        socket = self.parent.socket
        if os.path.exists(socket):
            os.remove(socket)
        self.factory = UserServerFactory(self.parent)
        reactor.listenUNIX(socket, self.factory, mode=self.parent.config.get_umask('sock'))

    def save_state(self):
        return self.factory.players

    def load_state(self, state):
        self.factory.players = state

########NEW FILE########
__FILENAME__ = shared
import os
import pkg_resources


def open_resource(name):
    return pkg_resources.resource_stream('mk2', name)


_config_found = False


if "MARK2_CONFIG_DIR" in os.environ:
    _config_base = os.environ["MARK2_CONFIG_DIR"]
elif "VIRTUAL_ENV" in os.environ:
    _config_base = os.path.join(os.environ["VIRTUAL_ENV"], ".config", "mark2")
elif __file__.startswith(os.path.realpath('/home/')):
    _config_base = os.path.join(os.path.expanduser("~"), ".config", "mark2")
else:
    _config_base = os.path.join(os.path.join("/etc/mark2"))


def find_config(name, create=True, ignore_errors=False):
    global _config_base, _config_found
    if not _config_found:
        if os.path.exists(_config_base):
            _config_found = True

    if create and not _config_found:
        try:
            os.makedirs(_config_base)
            _config_found = True
        except OSError:
            pass

    if not ignore_errors and not _config_found:
        raise ValueError

    return os.path.join(_config_base, name)


def console_repr(e):
    s = u"%s %s " % (e['time'], {'server': '|', 'mark2': '#', 'user': '>'}.get(e['source'], '?'))
    if e['source'] == 'server' and e['level'] != 'INFO':
        s += u"[%s] " % e['level']
    elif e['source'] == 'user':
        s += u"(%s) " % e['user']
    
    s += u"%s" % e['data']
    return s

########NEW FILE########
__FILENAME__ = test_events
from .. import events
from ..events import Event, EventPriority

from twisted.trial import unittest


class TestEvent(Event):
    name = Event.Arg()

    def prefilter(self, name=None):
        return self.name == name


class EventWithArgs(Event):
    required = Event.Arg(required=True)
    default = Event.Arg(default='foo')


class PrefilterTest_1(Event):
    def prefilter(self, require, optional=None):
        pass


class PrefilterTest_2(Event):
    def prefilter(self, require, optional=None, **excess):
        pass


class EventsTestCase(unittest.TestCase):
    def setUp(self):
        self.events = events.EventDispatcher(lambda *a: None)

    @staticmethod
    def eating_handler(event):
        return Event.EAT

    @staticmethod
    def unregistering_handler(event):
        return Event.UNREGISTER

    def test_dispatch(self):
        """
        Test basic event dispatching.
        """
        self.hit = False

        def handler(event):
            self.hit = True

        self.events.register(handler, TestEvent)
        
        self.events.dispatch(TestEvent())

        self.assertTrue(self.hit)

    def test_priority(self):
        """
        Test event priority ordering.
        """
        self.hit_1, self.hit_2 = False, False

        def handler_1(event):
            self.hit_1 = True

        def handler_2(event):
            self.hit_2 = self.hit_1

        self.events.register(handler_1, TestEvent, priority=EventPriority.HIGH)
        self.events.register(handler_2, TestEvent, priority=EventPriority.LOW)

        self.events.dispatch(TestEvent())

        self.assertTrue(self.hit_2)

    def test_priority_decorator(self):
        """
        Test event priority decorators (like @EventPriority.HIGH)
        """
        self.hit_1, self.hit_2 = False, False

        @EventPriority.HIGH
        def handler_1(event):
            self.hit_1 = True

        @EventPriority.LOW
        def handler_2(event):
            self.hit_2 = self.hit_1

        self.events.register(handler_1, TestEvent)
        self.events.register(handler_2, TestEvent)

        self.events.dispatch(TestEvent())

        self.assertTrue(self.hit_2)

    def test_eat(self):
        """
        Test Event.EAT
        """
        self.hit = False

        def handler(event):
            self.hit = True

        self.events.register(self.eating_handler, TestEvent, priority=EventPriority.HIGH)
        self.events.register(handler, TestEvent, priority=EventPriority.LOW)

        self.events.dispatch(TestEvent())

        self.assertFalse(self.hit)

    def test_unregister(self):
        """
        Test unregistering events.
        """
        id_ = self.events.register(lambda event: None, TestEvent)

        # it should be handled now
        handled = self.events.dispatch(TestEvent())
        self.assertTrue(self.successResultOf(handled))

        # but not once we unregister it
        self.events.unregister(id_)
        handled = self.events.dispatch(TestEvent())
        self.assertFalse(self.successResultOf(handled))

    def test_unregister_from_event(self):
        """
        Test Event.UNREGISTER
        """
        self.events.register(self.unregistering_handler, TestEvent)

        handled = self.events.dispatch(TestEvent())
        self.assertTrue(self.successResultOf(handled))

        handled = self.events.dispatch(TestEvent())
        self.assertFalse(self.successResultOf(handled))

    def test_event_args(self):
        """
        Test Event.Arg
        """
        self.assertRaises(Exception, EventWithArgs)
        ev = EventWithArgs(required=True)
        self.assertEqual(ev.default, 'foo')

    def test_prefilter_check(self):
        """
        Test Event.prefilter() arg checking
        """
        def handler(event):
            pass

        self.assertRaises(Exception, self.events.register, handler, PrefilterTest_1)
        self.assertRaises(Exception, self.events.register, handler, PrefilterTest_2)

        self.events.register(handler, PrefilterTest_1, require='foo')
        self.events.register(handler, PrefilterTest_2, require='foo')

        self.events.register(handler, PrefilterTest_1, require='foo', optional='bar')
        self.events.register(handler, PrefilterTest_2, require='foo', optional='bar')

        self.assertRaises(Exception, self.events.register, handler, PrefilterTest_1,
                          require='foo', optional='bar', fooarg='excess argument')
        self.events.register(handler, PrefilterTest_2,
                             require='foo', optional='bar', fooarg='excess argument')

########NEW FILE########
__FILENAME__ = test_plugins
from mk2 import events, plugins

import sys

from twisted.internet import task
from twisted.internet.task import Clock
from twisted.trial import unittest


class TestEventDispatcher(events.EventDispatcher):
    def __init__(self):
        events.EventDispatcher.__init__(self, lambda a: None)
        self.clock = Clock()
        self.advance = self.clock.advance

    def dispatch_delayed(self, event, delay):
        return self.clock.callLater(delay, self.dispatch, event)

    def dispatch_repeating(self, event, interval, now=False):
        t = task.LoopingCall(self.dispatch, event)
        t.clock = self.clock
        t.start(interval, now)
        return t


class TestPlugin(plugins.Plugin):
    foo = 'foo'
    bar = 'bar'

    def setup(self):
        return False

    def save_state(self):
        return self.foo

    def load_state(self, state):
        self.bar = state


class TestPluginLoader(plugins.PluginLoader):
    plugins = {'test': TestPlugin}

    def load_plugin(self, name):
        if name in self.plugins:
            return self.plugins[name], None
        else:
            return False

    def find_plugins(self):
        return list(self.plugins.keys())


class PluginTestBase:
    def setUp(self):
        self.config = self
        self.fatal_error = lambda *a: None
        self.events = TestEventDispatcher()
        self.plugins = plugins.PluginManager(self, loaders=(TestPluginLoader,))

    def console(self, *a, **kw):
        print a, kw

    def get_plugins(self):
        return {'test_plugins': {}}


class PluginLoading(PluginTestBase, unittest.TestCase):
    def test_load(self):
        self.assertTrue(self.plugins.load('test') is not None)

    def test_reload(self):
        self.plugins.reload('test')


class PluginTestCase(PluginTestBase, unittest.TestCase):
    def setUp(self):
        PluginTestBase.setUp(self)
        self.plugins.load('test')

    @property
    def plugin(self):
        return self.plugins['test']

    def test_load_save_state(self):
        self.assertEqual(self.plugin.foo, 'foo')
        self.assertEqual(self.plugin.bar, 'bar')
        self.plugins.reload('test')
        self.assertEqual(self.plugin.bar, 'foo')

    def test_parse_time(self):
        name, time = self.plugin.parse_time("37s")
        self.assertEqual(time, 37)

    def test_action_chain(self):
        warn = [0]
        action = [False]

        # evil
        sys.modules[plugins.Plugin.__module__].reactor = self.events.clock

        def callbackWarn(a):
            warn[0] += 1

        def callbackAction():
            action[0] = True

        act = self.plugin.action_chain("10h;10m;10s",
                                       callbackWarn,
                                       callbackAction)[1]
        act()

        for i, time in enumerate((36000, 590, 10)):
            self.assertEqual(warn[0], i + 1)
            self.events.advance(time)

        self.assertEqual(warn[0], 3)
        self.assertTrue(action[0])

    def test_action_cancel(self):
        action = [False]
        cancelled = [False]

        # evil
        sys.modules[plugins.Plugin.__module__].reactor = self.events.clock

        def callbackCancel():
            cancelled[0] = True

        def callbackAction():
            action[0] = True

        act, cancel = self.plugin.action_chain_cancellable("1s",
                                                           lambda a: None,
                                                           callbackAction,
                                                           callbackCancel)[-2:]
        act()

        self.assertFalse(action[0])
        self.assertFalse(cancelled[0])

        cancel()

        self.assertTrue(cancelled[0])

        self.events.advance(2)

        self.assertFalse(action[0])

    def test_delayed_task(self):
        calls = [0]

        def task(ev):
            calls[0] += 1

        self.plugin.delayed_task(task, 10)

        self.events.advance(9)

        self.assertEqual(calls[0], 0)

        self.events.advance(1)

        self.assertEqual(calls[0], 1)

        self.events.advance(100)

        self.assertEqual(calls[0], 1)

    def test_repeating_task(self):
        calls = [0]

        def task(ev):
            calls[0] += 1

        self.plugin.repeating_task(task, 10)

        for i in xrange(100):
            self.events.advance(10)

        self.assertEqual(calls[0], 100)

    def test_stop_tasks(self):
        calls = [0]

        def task(ev):
            calls[0] += 1

        self.plugin.repeating_task(task, 10)

        for i in xrange(100):
            self.events.advance(10)

        self.plugin.stop_tasks()

        for i in xrange(100):
            self.events.advance(10)

        self.assertEqual(calls[0], 100)

########NEW FILE########
__FILENAME__ = test_process
from mk2 import events
from mk2.services import process

import random

from twisted.internet import error
from twisted.python.failure import Failure

from twisted.trial import unittest


class ProcessProtocolTestCase(unittest.TestCase):
    def setUp(self):
        self.dispatched = []
        self.proto = process.ProcessProtocol(self.dispatch, 'utf8')

    def dispatch(self, event):
        self.dispatched.append(event)

    def test_output(self):
        random.seed()

        data = '''a line of output
and another line of output
this line is incomplete'''

        lines = data.split('\n')

        while data:
            index = random.randint(1, min(len(data), 18))
            bit, data = data[:index], data[index:]
            self.proto.childDataReceived(1, bit)

        self.assertTrue(self.dispatched)

        while self.dispatched:
            event = self.dispatched.pop(0)
            self.assertIsInstance(event, events.ServerOutput)
            self.assertEqual(event['data'], lines.pop(0))

        self.assertEqual(len(lines), 1)  # the data after the final \n

    def test_process_success(self):
        fail = Failure(error.ProcessDone(None))

        self.proto.processEnded(fail)

        self.assertFalse(self.proto.alive)

        self.assertEqual(len(self.dispatched), 1)
        self.assertIsInstance(self.dispatched[0], events.ServerStopped)

    def test_process_failure(self):
        fail = Failure(error.ProcessTerminated(exitCode=1))

        self.proto.processEnded(fail)

        self.assertFalse(self.proto.alive)

        self.assertTrue(any(isinstance(event, events.FatalError) for event in self.dispatched))

########NEW FILE########
__FILENAME__ = user_client
import getpass
import glob
import json
import os
from string import Template
from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory, ProcessProtocol
from twisted.internet.task import LoopingCall
from twisted.protocols.basic import LineReceiver
import properties
import psutil
import re
import sys
import urwid
from shared import console_repr, open_resource


class TabEvent:
    fail = None

    def __init__(self, line, players):
        pos = line.rfind(' ') + 1
        if pos == 0:
            self.left, right = "", line
        else:
            self.left, right = line[:pos], line[pos:]

        self.players = filter(lambda p: p.startswith(right), players)
        if len(self.players) == 0:
            self.fail = line
        self.index = 0

    def next(self):
        if self.fail:
            return self.fail
        i = self.index % len(self.players)
        self.index += 1
        return self.left + self.players[i]


class Prompt(urwid.Edit):
    def __init__(self, get_players, run_command, *a, **k):
        self.history = ['']
        self.history_pos = 0
        self.tab = None

        self.get_players = get_players
        self.run_command = run_command

        urwid.Edit.__init__(self, *a, **k)

    def get_prompt(self):
        return self.get_edit_text()

    def set_prompt(self, x):
        self.set_edit_text(x)
        self.set_edit_pos(len(x))

    def save_prompt(self):
        self.history[self.history_pos] = self.get_prompt()

    def load_prompt(self):
        self.set_prompt(self.history[self.history_pos])

    def keypress(self, size, key):
        if key != 'tab':
            self.tab = None

        if key == 'up':
            if self.history_pos > 0:
                self.save_prompt()
                self.history_pos -= 1
                self.load_prompt()
        elif key == 'down':
            if self.history_pos < len(self.history) - 1:
                self.save_prompt()
                self.history_pos += 1
                self.load_prompt()
        elif key == 'enter':
            text = self.get_prompt()
            self.run_command(text)
            self.history_pos = len(self.history) - 1
            if self.history[self.history_pos - 1] == text:
                self.set_prompt('')
                self.cursor = 0
                self.save_prompt()
            else:
                self.save_prompt()
                self.history.append('')
                self.history_pos += 1
                self.load_prompt()
        elif key == 'tab':
            text = self.get_prompt()
            if text == '':
                self.set_prompt('say ')
            else:
                if self.tab is None:
                    self.tab = TabEvent(text, self.get_players())
                self.set_prompt(self.tab.next())
        else:
            return urwid.Edit.keypress(self, size, key)


class PMenuButton(urwid.Button):
    def __init__(self, caption, *a):
        super(PMenuButton, self).__init__(caption, *a)
        self._w = urwid.SelectableIcon(caption, 0)


class PMenuWrap(urwid.WidgetPlaceholder):
    names = ('players', 'actions', 'reasons')

    def __init__(self, actions, reasons, dispatch, escape):
        self.dispatch = dispatch
        self.escape = escape
        self._pmenu_lists   = [ (n, urwid.SimpleListWalker([])) for n    in self.names        ]
        self._pmenu_widgets = [ (n, urwid.ListBox(l))           for n, l in self._pmenu_lists ]

        self.fill(1, zip(actions, actions))
        self.fill(2, reasons)

        self.first()

        super(PMenuWrap, self).__init__(self._pmenu_widgets[0][1])

    def fill(self, index, items):
        name, contents = self._pmenu_lists[index]
        del contents[0:len(contents)]
        for name, result in items:
            e = urwid.AttrMap(PMenuButton(name, self.next, result), 'menu_item', 'menu_item_focus')
            contents.append(e)

    def first(self):
        self._pmenu_acc = []
        self._pmenu_stage = 0
        self.original_widget = self._pmenu_widgets[0][1]

    def next(self, widget, result):
        acc = self._pmenu_acc
        acc.append(result)
        #run command?
        if (self._pmenu_stage == 1 and not (result in ('kick', 'ban') and len(self._pmenu_lists[2][1]) > 0)) or\
           (self._pmenu_stage == 2):
            self.dispatch(' '.join([acc[1]] + [acc[0]] + acc[2:]))
            self.first()
        #next menu
        else:
            self._pmenu_stage += 1
            self.original_widget = self._pmenu_widgets[self._pmenu_stage][1]

    def prev(self):
        self._pmenu_acc.pop()
        self._pmenu_stage -= 1
        self.original_widget = self._pmenu_widgets[self._pmenu_stage][1]

    def keypress(self, size, key):
        if key == 'esc':
            if self._pmenu_stage == 0:
                self.escape()
            else:
                self.first()
        elif key == 'backspace':
            if self._pmenu_stage == 0:
                self.escape()
            else:
                self.prev()
        else:
            return self.original_widget.keypress(size, key)

    def set_players(self, players):
        content = self._pmenu_lists[0][1]
        diff = lambda a, b: [[e for e in d if not e in c] for c, d in ((a, b), (b, a))]

        add, remove = diff([b.original_widget.label for b in list(content)], players)

        #first remove players who logged off
        for b in list(content):
            if b.original_widget.label in remove:
                content.remove(b)

        #now add new players
        i = 0
        while len(add) > 0:
            a = add.pop(0)
            while i < len(content) - 1 and content[i].original_widget.label.lower() < a.lower():
                i += 1
            content.insert(i, urwid.AttrMap(PMenuButton(a, self.next, a), 'menu_item', 'menu_item_focus'))
            i += 1


class UI:
    loop = None

    def __init__(self, palette, get_players, run_command, switch_server, connect_to_server, pmenu_actions, pmenu_reasons):
        self.palette = palette
        self.get_players = get_players
        self.run_command = run_command
        self.switch_server = switch_server
        self.connect_to_server = connect_to_server

        self.pmenu_actions = pmenu_actions
        self.pmenu_reasons = pmenu_reasons

        self.lines = []
        self.filters = {}
        self.filter = lambda *a: True

        self.g_output_list = urwid.SimpleListWalker([])

        self.build()

    def build(self):
        #header
        self.g_servers = urwid.Columns([])
        self.g_users   = urwid.Columns([])
        g_head         = urwid.AttrMap(urwid.Columns((self.g_servers, self.g_users)), 'head')

        #main
        self.g_output  = urwid.ListBox(self.g_output_list)
        self.g_stats   = urwid.Text("")

        #player menu
        def escape():
            self.g_frame.focus_position='footer'
        self.g_pmenu = PMenuWrap(self.pmenu_actions, self.pmenu_reasons, self.run_command, escape)

        g_sidebar = urwid.Pile((
            ('pack', urwid.AttrMap(urwid.LineBox(self.g_stats, title='stats'), 'stats')),
            urwid.AttrMap(urwid.LineBox(self.g_pmenu, title="players"), 'menu')))
        g_main    = urwid.Columns((
            urwid.WidgetDisable(urwid.AttrMap(urwid.LineBox(self.g_output, title='server'), 'console')),
            ('fixed', 31, g_sidebar)))

        #foot
        self.g_prompt = Prompt(self.get_players, self.run_command, ' > ')
        g_prompt = urwid.AttrMap(self.g_prompt, 'prompt', 'prompt_focus')

        self.g_frame = urwid.Frame(g_main, g_head, g_prompt, focus_part='footer')
        self.g_main = urwid.AttrMap(urwid.Padding(self.g_frame, left=1, right=1), 'frame')

        #log.addObserver(lambda m: self.append_output(str(m['message'])))

    def main(self):
        self.loop = urwid.MainLoop(
            self.g_main,
            self.palette,
            input_filter=self.filter_input,
            event_loop=urwid.TwistedEventLoop()
        )
        self.loop.run()

    def stop(self):
        def exit(*a):
            raise urwid.ExitMainLoop
        self.loop.set_alarm_in(0, exit)

    def filter_input(self, keys, raw):
        passthru = []
        for key in keys:
            if key in ('page up', 'page down'):
                self.g_output.keypress((0, 16), key)
            elif key == 'ctrl left':
                self.switch_server(-1)
            elif key == 'ctrl right':
                self.switch_server(1)
            elif key == 'ctrl p':
                self.g_frame.focus_position = 'body'
            elif key == 'f8':
                raise urwid.ExitMainLoop
            else:
                passthru.append(key)

        return passthru

    def redraw(self):
        if self.loop:
            self.loop.draw_screen()

    def set_servers(self, servers, current=None):
        new = []
        for s in sorted(servers):
            e = PMenuButton(" %s " % s, lambda button, _s=s: self.connect_to_server(_s))
            e = urwid.AttrMap(e, 'server_current' if s == current else 'server')
            new.append((e, self.g_servers.options('pack')))

        contents = self.g_servers.contents
        del contents[0:len(contents)]
        sep = u'\u21C9 ' if urwid.supports_unicode() else u':'
        contents.append((urwid.AttrMap(urwid.Text(u' mark2 %s' % sep), 'mark2'), self.g_servers.options('pack')))
        contents.extend(new)
        contents.append((urwid.Divider(), self.g_users.options()))

    def set_users(self, users):
        new = []
        for user, attached in users:
            e = urwid.Text(" %s " % user)
            e = urwid.AttrMap(e, 'user_attached' if attached else 'user')
            new.append((e, self.g_users.options('pack')))

        contents = self.g_users.contents
        del contents[0:len(contents)]
        contents.append((urwid.Divider(), self.g_users.options()))
        contents.extend(new)

    def safe_unicode(self, text):
        if urwid.supports_unicode():
            return text
        else:
            return text.encode('ascii', errors='replace')

    def append_output(self, line):
        scroll = False
        del self.lines[:-999]
        self.lines.append(line)

        if not self.filter(line):
            return

        try:
            p = self.g_output.focus_position
            try:
                self.g_output.body.next_position(p)
            except IndexError:  # scrolled to end
                scroll = True
        except IndexError:  # nothing in listbox
            pass

        self.g_output_list.append(urwid.Text(self.safe_unicode(console_repr(line))))
        if scroll:
            self.g_output.focus_position += 1

        self.redraw()

    def set_output(self, lines=None):
        contents = self.g_output_list
        del contents[0:len(contents)]

        lines = lines or self.lines
        lines = [l for l in lines if self.filter(l)]

        for line in lines:
            contents.append(urwid.Text(self.safe_unicode(console_repr(line))))

        try:
            self.g_output.focus_position = len(lines) - 1
        except IndexError:  # nothing in list
            pass
        self.redraw()

    def set_filter(self, filter_):
        if isinstance(filter_, basestring):
            return self.set_filter(self.filters[filter_])
        self.filter = filter_.apply
        self.set_output()

    def set_players(self, players):
        self.g_pmenu.set_players(players)
        self.redraw()

    def set_stats(self, stats):
        self.g_stats.set_text(stats)
        self.redraw()


class SystemUsers(set):
    def __init__(self):
        self.me = getpass.getuser()
        set.__init__(self)

    def update_users(self):
        self.clear()
        for u in psutil.get_users():
            self.add(u.name)


class App(object):
    def __init__(self, name, interval, update, shell, command):
        self.name = name
        self.interval = interval
        self.update = update
        self.cmd = [shell, '-c', command]
        self.stopping = False
        self.start()

    def start(self):
        p = ProcessProtocol()
        self.buff     = ""
        self.protocol = p

        p.outReceived   = self.got_out
        p.processEnded  = self.got_exit
        reactor.spawnProcess(p, self.cmd[0], self.cmd)

    def got_out(self, d):
        self.buff += d

    def got_exit(self, *a):
        self.update(self.name, self.buff.strip())
        if not self.stopping:
            reactor.callLater(self.interval, self.start)


class LineFilter:
    HIDE = 1
    SHOW = 2

    def __init__(self):
        self._actions = []
        self._default = self.SHOW

    def append(self, action, *predicates):
        self.setdefault(action)
        def action_(msg):
            if all(p(msg) for p in predicates):
                return action
            return None
        self._actions.append(action_)

    def setdefault(self, action):
        if len(self._actions) == 0:
            self._default = (self.HIDE if action != self.SHOW else self.SHOW)

    def apply(self, msg):
        current = self._default
        for action in self._actions:
            current = action(msg) or current
        return current == LineFilter.SHOW


class UserClientFactory(ClientFactory):
    def __init__(self, initial_name, shared_path='/tmp/mark2'):
        self.socket_to   = lambda n: os.path.join(shared_path, n + ".sock")
        self.socket_from = lambda p: os.path.splitext(os.path.basename(p))[0]

        self.client = None
        self.stats = {}
        self.system_users = SystemUsers()

        #read the config
        self.config = properties.load(properties.ClientProperties, open_resource('resources/mark2rc.default.properties'), os.path.expanduser('~/.mark2rc.properties'))
        assert not self.config is None
        self.stats_template = Template(self.config['stats'])

        #start apps
        self.apps = []

        #start ui
        self.ui = UI(self.config.get_palette(), self.get_players, self.run_command, self.switch_server, self.connect_to_server, self.config.get_player_actions(), self.config.get_player_reasons())
        for name, command in self.config.get_apps():
            app = App(name, self.config.get_interval('apps'), self.app_update, self.config['stats.app_shell'], command)
            self.apps.append(app)

        #tasks
        t = LoopingCall(self.update_servers)
        t.start(self.config.get_interval('servers'))

        t = LoopingCall(self.update_users)
        t.start(self.config.get_interval('users'))

        t = LoopingCall(self.update_players)
        t.start(self.config.get_interval('players'))

        t = LoopingCall(self.update_stats)
        t.start(self.config.get_interval('stats'))

        self.connect_to_server(initial_name)

    def log(self, w):
        self.ui.append_output(str(w))

    def main(self):
        self.ui.main()

    def buildProtocol(self, addr):
        self.client = UserClientProtocol(self.socket_from(addr.name), self.system_users.me, self)
        self.update_servers()
        return self.client

    def switch_server(self, delta=1):
        self.update_servers()
        if len(self.servers) == 0:  # no running servers
            return self.ui.stop()
        if len(self.servers) == 1:  # don't switch with only one server
            return

        index = self.servers.index(self.client.name)
        name = self.servers[(index + delta) % len(self.servers)]
        self.connect_to_server(name)

    def connect_to_server(self, name):
        if self.client:
            self.client.close()
        reactor.connectUNIX(self.socket_to(name), self)

    def update_servers(self):
        servers = []
        for f in glob.glob(self.socket_to('*')):
            servers.append(self.socket_from(f))

        self.servers = sorted(servers)
        self.ui.set_servers(self.servers, current=self.client.name if self.client else None)

    def update_users(self):
        self.system_users.update_users()
        if self.client:
            self.client.get_users()

    def update_players(self):
        if self.client:
            self.client.get_players()

    def update_stats(self):
        if self.client:
            self.client.get_stats()

    def app_update(self, name, data):
        self.stats[name] = data

    def get_players(self):
        if self.client:
            return self.client.players
        else:
            return []

    def run_command(self, command):
        if self.client:
            return self.client.run_command(command)

    def server_connected(self, client):
        pass

    def server_disconnected(self, client):
        self.switch_server()

    def server_output(self, line):
        self.ui.append_output(line)

    def server_scrollback(self, lines):
        self.ui.set_output(lines)

    def server_players(self, players):
        self.ui.set_players(players)

    def server_users(self, users_a):
        users_l = list(self.system_users)

        users = []
        for u in sorted(set(users_l + users_a), key=str.lower):
            users.append((u, u in users_a))

        self.ui.set_users(users)

    def server_stats(self, stats):
        self.stats.update(stats)
        self.ui.set_stats(self.stats_template.safe_substitute(self.stats))

    def server_regex(self, patterns):
        self.make_filters(patterns)

    def make_filters(self, server_patterns={}):
        cfg = {}
        cfg.update(server_patterns)
        cfg.update(self.config.get_by_prefix('pattern.'))

        # read patterns from config to get a dict of name: filter function
        def makefilter(p):
            ppp = p
            p = re.compile(p)
            def _filter(msg):
                m = p.match(msg['data'])
                return m and m.end() == len(msg['data'])
            return _filter
        patterns = dict((k, makefilter(p)) for k, p in cfg.iteritems())

        patterns['all'] = lambda a: True

        # read filters
        self.ui.filters = {}
        for name, spec in self.config.get_by_prefix('filter.'):
            filter_ = LineFilter()
            action = LineFilter.SHOW
            for pattern in spec.split(','):
                pattern = pattern.strip().replace('-', '_')
                if ':' in pattern:
                    a, pattern = pattern.split(':', 1)
                    action = {'show': LineFilter.SHOW, 'hide': LineFilter.HIDE}.get(a)
                    filter_.setdefault(action)
                if not pattern:
                    continue
                filter_.append(action, patterns[pattern])
            self.ui.filters[name] = filter_
        self.ui.set_filter(self.config['use_filter'])


class NullFactory(object):
    def __getattr__(self, name):
        return lambda *a, **k: None


class UserClientProtocol(LineReceiver):
    MAX_LENGTH = 999999
    delimiter = '\n'
    enabled = False

    def __init__(self, name, user, factory):
        self.name = name
        self.user = user
        self.users = set()
        self.players = list()
        self.factory = factory

    def close(self):
        self.transport.loseConnection()
        self.factory = NullFactory()

    def connectionMade(self):
        self.alive = 1
        self.send("attach", user=self.user)
        self.send("get_scrollback")
        self.factory.server_connected(self)

    def connectionLost(self, reason):
        self.alive = 0
        self.factory.server_disconnected(self)

    def lineReceived(self, line):
        #log.msg(line)
        msg = json.loads(line)
        ty = msg["type"]

        if ty == "console":
            self.factory.server_output(msg)

        elif ty == "scrollback":
            self.factory.server_scrollback(msg['lines'])

        elif ty == "user_status":
            user = str(msg["user"])
            if msg["online"]:
                self.users.add(user)
            else:
                self.users.discard(user)
            self.factory.server_users(list(self.users))

        elif ty == "players":
            self.players = msg['players']
            self.factory.server_players(self.players)

        elif ty == "stats":
            self.factory.server_stats(msg['stats'])

        elif ty == "regex":
            self.factory.server_regex(msg['patterns'])

        else:
            self.factory.log("wat")

    def send(self, ty, **d):
        d['type'] = ty
        if self.alive:
            self.sendLine(json.dumps(d))

    def run_command(self, command):
        self.send("input", line=command, user=self.user)

    def get_players(self):
        self.send("get_players")

    def get_stats(self):
        self.send("get_stats")

    def get_users(self):
        self.send("get_users")


if __name__ == '__main__':
    thing = UserClientFactory('testserver')
    thing.main()

########NEW FILE########
