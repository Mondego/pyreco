__FILENAME__ = bot
#!/usr/bin/env python

import os
import Queue
import sys
import traceback
import time

sys.path += ['plugins']  # so 'import hook' works without duplication
sys.path += ['lib']
os.chdir(sys.path[0] or '.')  # do stuff relative to the install directory


class Bot(object):
    def __init__(self):
        self.conns = {}
        self.persist_dir = os.path.abspath('persist')
        if not os.path.exists(self.persist_dir):
            os.mkdir(self.persist_dir)

bot = Bot()

print 'Loading plugins'

# bootstrap the reloader
eval(compile(open(os.path.join('core', 'reload.py'), 'U').read(),
             os.path.join('core', 'reload.py'), 'exec'))
reload(init=True)

print 'Connecting to IRC'

try:
    config()
    if not hasattr(bot, 'config'):
        exit()
except Exception, e:
    print 'ERROR: malformed config file:', e
    traceback.print_exc()
    sys.exit()

print 'Running main loop'

while True:
    reload()  # these functions only do things
    config()  # if changes have occured

    for conn in bot.conns.itervalues():
        try:
            out = conn.out.get_nowait()
            main(conn, out)
        except Queue.Empty:
            pass
    while all(conn.out.empty() for conn in bot.conns.itervalues()):
        time.sleep(.1)

########NEW FILE########
__FILENAME__ = config
import inspect
import json
import os


def save(conf):
    json.dump(conf, open('config', 'w'), sort_keys=True, indent=2)

if not os.path.exists('config'):
    open('config', 'w').write(inspect.cleandoc(
        r'''
        {
          "connections":
          {
            "local irc":
            {
              "server": "localhost",
              "nick": "skybot",
              "channels": ["#test"]
            }
          },
          "prefix": ".",
          "disabled_plugins": [],
          "disabled_commands": [],
          "acls": {},
          "api_keys": {},
          "censored_strings":
          [
            "DCC SEND",
            "1nj3ct",
            "thewrestlinggame",
            "startkeylogger",
            "hybux",
            "\\0",
            "\\x01",
            "!coz",
            "!tell /x"
          ]
        }''') + '\n')


def config():
    # reload config from file if file has changed
    config_mtime = os.stat('config').st_mtime
    if bot._config_mtime != config_mtime:
        try:
            bot.config = json.load(open('config'))
            bot._config_mtime = config_mtime
            for name, conf in bot.config['connections'].iteritems():
                if name in bot.conns:
                    bot.conns[name].set_conf(conf)
                else:
                    if conf.get('ssl'):
                        bot.conns[name] = SSLIRC(conf)
                    else:
                        bot.conns[name] = IRC(conf)
        except ValueError, e:
            print 'ERROR: malformed config!', e


bot._config_mtime = 0

########NEW FILE########
__FILENAME__ = db
import os
import sqlite3


def get_db_connection(conn, name=''):
    "returns an sqlite3 connection to a persistent database"

    if not name:
        name = '%s.%s.db' % (conn.nick, conn.server)

    filename = os.path.join(bot.persist_dir, name)
    return sqlite3.connect(filename, timeout=10)

bot.get_db_connection = get_db_connection

########NEW FILE########
__FILENAME__ = irc
import re
import socket
import time
import thread
import Queue

from ssl import wrap_socket, CERT_NONE, CERT_REQUIRED, SSLError


def decode(txt):
    for codec in ('utf-8', 'iso-8859-1', 'shift_jis', 'cp1252'):
        try:
            return txt.decode(codec)
        except UnicodeDecodeError:
            continue
    return txt.decode('utf-8', 'ignore')


def censor(text):
    text = text.replace('\n', '').replace('\r', '')
    replacement = '[censored]'
    if 'censored_strings' in bot.config:
        words = map(re.escape, bot.config['censored_strings'])
        regex = re.compile('(%s)' % "|".join(words))
        text = regex.sub(replacement, text)
    return text


class crlf_tcp(object):

    "Handles tcp connections that consist of utf-8 lines ending with crlf"

    def __init__(self, host, port, timeout=300):
        self.ibuffer = ""
        self.obuffer = ""
        self.oqueue = Queue.Queue()  # lines to be sent out
        self.iqueue = Queue.Queue()  # lines that were received
        self.socket = self.create_socket()
        self.host = host
        self.port = port
        self.timeout = timeout

    def create_socket(self):
        return socket.socket(socket.AF_INET, socket.TCP_NODELAY)

    def run(self):
        self.socket.connect((self.host, self.port))
        thread.start_new_thread(self.recv_loop, ())
        thread.start_new_thread(self.send_loop, ())

    def recv_from_socket(self, nbytes):
        return self.socket.recv(nbytes)

    def get_timeout_exception_type(self):
        return socket.timeout

    def handle_receive_exception(self, error, last_timestamp):
        if time.time() - last_timestamp > self.timeout:
            self.iqueue.put(StopIteration)
            self.socket.close()
            return True
        return False

    def recv_loop(self):
        last_timestamp = time.time()
        while True:
            try:
                data = self.recv_from_socket(4096)
                self.ibuffer += data
                if data:
                    last_timestamp = time.time()
                else:
                    if time.time() - last_timestamp > self.timeout:
                        self.iqueue.put(StopIteration)
                        self.socket.close()
                        return
                    time.sleep(1)
            except (self.get_timeout_exception_type(), socket.error) as e:
                if self.handle_receive_exception(e, last_timestamp):
                    return
                continue

            while '\r\n' in self.ibuffer:
                line, self.ibuffer = self.ibuffer.split('\r\n', 1)
                self.iqueue.put(decode(line))

    def send_loop(self):
        while True:
            line = self.oqueue.get().splitlines()[0][:500]
            print ">>> %r" % line
            self.obuffer += line.encode('utf-8', 'replace') + '\r\n'
            while self.obuffer:
                sent = self.socket.send(self.obuffer)
                self.obuffer = self.obuffer[sent:]


class crlf_ssl_tcp(crlf_tcp):

    "Handles ssl tcp connetions that consist of utf-8 lines ending with crlf"

    def __init__(self, host, port, ignore_cert_errors, timeout=300):
        self.ignore_cert_errors = ignore_cert_errors
        crlf_tcp.__init__(self, host, port, timeout)

    def create_socket(self):
        return wrap_socket(crlf_tcp.create_socket(self), server_side=False,
                           cert_reqs=CERT_NONE if self.ignore_cert_errors else
                           CERT_REQUIRED)

    def recv_from_socket(self, nbytes):
        return self.socket.read(nbytes)

    def get_timeout_exception_type(self):
        return SSLError

    def handle_receive_exception(self, error, last_timestamp):
        # this is terrible
        if not "timed out" in error.args[0]:
            raise
        return crlf_tcp.handle_receive_exception(self, error, last_timestamp)

irc_prefix_rem = re.compile(r'(.*?) (.*?) (.*)').match
irc_noprefix_rem = re.compile(r'()(.*?) (.*)').match
irc_netmask_rem = re.compile(r':?([^!@]*)!?([^@]*)@?(.*)').match
irc_param_ref = re.compile(r'(?:^|(?<= ))(:.*|[^ ]+)').findall


class IRC(object):

    "handles the IRC protocol"
    # see the docs/ folder for more information on the protocol

    def __init__(self, conf):
        self.set_conf(conf)

        self.out = Queue.Queue()  # responses from the server are placed here
        # format: [rawline, prefix, command, params,
        # nick, user, host, paramlist, msg]
        self.connect()

        thread.start_new_thread(self.parse_loop, ())

    def set_conf(self, conf):
        self.conf = conf
        self.nick = self.conf['nick']
        self.server = self.conf['server']

    def create_connection(self):
        return crlf_tcp(self.server, self.conf.get('port', 6667))

    def connect(self):
        self.conn = self.create_connection()
        thread.start_new_thread(self.conn.run, ())
        self.cmd("NICK", [self.nick])
        self.cmd("USER",
                 [self.conf.get('user', 'skybot'), "3", "*", self.conf.get('realname',
                                                                 'Python bot - http://github.com/rmmh/skybot')])
        if 'server_password' in self.conf:
            self.cmd("PASS", [self.conf['server_password']])

    def parse_loop(self):
        while True:
            msg = self.conn.iqueue.get()

            if msg == StopIteration:
                self.connect()
                continue

            if msg.startswith(":"):  # has a prefix
                prefix, command, params = irc_prefix_rem(msg).groups()
            else:
                prefix, command, params = irc_noprefix_rem(msg).groups()
            nick, user, host = irc_netmask_rem(prefix).groups()
            paramlist = irc_param_ref(params)
            lastparam = ""
            if paramlist:
                if paramlist[-1].startswith(':'):
                    paramlist[-1] = paramlist[-1][1:]
                lastparam = paramlist[-1]
            self.out.put([msg, prefix, command, params, nick, user, host,
                          paramlist, lastparam])
            if command == "PING":
                self.cmd("PONG", paramlist)

    def join(self, channel):
        self.cmd("JOIN", channel.split(" "))  # [chan, password]

    def msg(self, target, text):
        self.cmd("PRIVMSG", [target, text])

    def cmd(self, command, params=None):
        if params:
            params[-1] = ':' + params[-1]
            self.send(command + ' ' + ' '.join(map(censor, params)))
        else:
            self.send(command)

    def send(self, str):
        self.conn.oqueue.put(str)


class FakeIRC(IRC):

    def __init__(self, conf):
        self.set_conf(conf)
        self.out = Queue.Queue()  # responses from the server are placed here

        self.f = open(fn, 'rb')

        thread.start_new_thread(self.parse_loop, ())

    def parse_loop(self):
        while True:
            msg = decode(self.f.readline()[9:])

            if msg == '':
                print "!!!!DONE READING FILE!!!!"
                return

            if msg.startswith(":"):  # has a prefix
                prefix, command, params = irc_prefix_rem(msg).groups()
            else:
                prefix, command, params = irc_noprefix_rem(msg).groups()
            nick, user, host = irc_netmask_rem(prefix).groups()
            paramlist = irc_param_ref(params)
            lastparam = ""
            if paramlist:
                if paramlist[-1].startswith(':'):
                    paramlist[-1] = paramlist[-1][1:]
                lastparam = paramlist[-1]
            self.out.put([msg, prefix, command, params, nick, user, host,
                          paramlist, lastparam])
            if command == "PING":
                self.cmd("PONG", [params])

    def cmd(self, command, params=None):
        pass


class SSLIRC(IRC):

    def create_connection(self):
        return crlf_ssl_tcp(self.server, self.conf.get('port', 6697), self.conf.get('ignore_cert', True))

########NEW FILE########
__FILENAME__ = main
import thread
import traceback


thread.stack_size(1024 * 512)  # reduce vm size


class Input(dict):

    def __init__(self, conn, raw, prefix, command, params,
                 nick, user, host, paraml, msg):

        chan = paraml[0].lower()
        if chan == conn.nick.lower():  # is a PM
            chan = nick

        def say(msg):
            conn.msg(chan, msg)

        def reply(msg):
            if chan == nick:  # PMs don't need prefixes
                self.say(msg)
            else:
                self.say(nick + ': ' + msg)

        def pm(msg, nick=nick):
            conn.msg(nick, msg)

        def set_nick(nick):
            conn.set_nick(nick)

        def me(msg):
            self.say("\x01%s %s\x01" % ("ACTION", msg))

        def notice(msg):
            conn.cmd('NOTICE', [nick, msg])

        def kick(target=None, reason=None):
            conn.cmd('KICK', [chan, target or nick, reason or ''])

        def ban(target=None):
            conn.cmd('MODE', [chan, '+b', target or host])

        def unban(target=None):
            conn.cmd('MODE', [chan, '-b', target or host])


        dict.__init__(self, conn=conn, raw=raw, prefix=prefix, command=command,
                      params=params, nick=nick, user=user, host=host,
                      paraml=paraml, msg=msg, server=conn.server, chan=chan,
                      notice=notice, say=say, reply=reply, pm=pm, bot=bot,
                      kick=kick, ban=ban, unban=unban, me=me,
                      set_nick=set_nick, lastparam=paraml[-1])

    # make dict keys accessible as attributes
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


def run(func, input):
    args = func._args

    if 'inp' not in input:
        input.inp = input.paraml

    if args:
        if 'db' in args and 'db' not in input:
            input.db = get_db_connection(input.conn)
        if 'input' in args:
            input.input = input
        if 0 in args:
            out = func(input.inp, **input)
        else:
            kw = dict((key, input[key]) for key in args if key in input)
            out = func(input.inp, **kw)
    else:
        out = func(input.inp)
    if out is not None:
        input.reply(unicode(out))


def do_sieve(sieve, bot, input, func, type, args):
    try:
        return sieve(bot, input, func, type, args)
    except Exception:
        print 'sieve error',
        traceback.print_exc()
        return None


class Handler(object):

    '''Runs plugins in their own threads (ensures order)'''

    def __init__(self, func):
        self.func = func
        self.input_queue = Queue.Queue()
        thread.start_new_thread(self.start, ())

    def start(self):
        uses_db = 'db' in self.func._args
        db_conns = {}
        while True:
            input = self.input_queue.get()

            if input == StopIteration:
                break

            if uses_db:
                db = db_conns.get(input.conn)
                if db is None:
                    db = bot.get_db_connection(input.conn)
                    db_conns[input.conn] = db
                input.db = db

            try:
                run(self.func, input)
            except:
                traceback.print_exc()

    def stop(self):
        self.input_queue.put(StopIteration)

    def put(self, value):
        self.input_queue.put(value)


def dispatch(input, kind, func, args, autohelp=False):
    for sieve, in bot.plugs['sieve']:
        input = do_sieve(sieve, bot, input, func, kind, args)
        if input == None:
            return

    if autohelp and args.get('autohelp', True) and not input.inp \
            and func.__doc__ is not None:
        input.reply(func.__doc__)
        return

    if hasattr(func, '_apikey'):
        key = bot.config.get('api_keys', {}).get(func._apikey, None)
        if key is None:
            input.reply('error: missing api key')
            return
        input.api_key = key

    if func._thread:
        bot.threads[func].put(input)
    else:
        thread.start_new_thread(run, (func, input))


def match_command(command):
    commands = list(bot.commands)

    # do some fuzzy matching
    prefix = filter(lambda x: x.startswith(command), commands)
    if len(prefix) == 1:
        return prefix[0]
    elif prefix and command not in prefix:
        return prefix

    return command


def main(conn, out):
    inp = Input(conn, *out)

    # EVENTS
    for func, args in bot.events[inp.command] + bot.events['*']:
        dispatch(Input(conn, *out), "event", func, args)

    if inp.command == 'PRIVMSG':
        # COMMANDS
        bot_prefix = re.escape(bot.config.get("prefix", "."))
        if inp.chan == inp.nick:  # private message, no command prefix
            prefix = r'^(?:['+bot_prefix+']?|'
        else:
            prefix = r'^(?:['+bot_prefix+']|'

        command_re = prefix + inp.conn.nick
        command_re += r'[:,]+\s+)(\w+)(?:$|\s+)(.*)'

        m = re.match(command_re, inp.lastparam)

        if m:
            trigger = m.group(1).lower()
            command = match_command(trigger)

            if isinstance(command, list):  # multiple potential matches
                input = Input(conn, *out)
                input.reply("did you mean %s or %s?" %
                            (', '.join(command[:-1]), command[-1]))
            elif command in bot.commands:
                input = Input(conn, *out)
                input.trigger = trigger
                input.inp_unstripped = m.group(2)
                input.inp = input.inp_unstripped.strip()

                func, args = bot.commands[command]
                dispatch(input, "command", func, args, autohelp=True)

        # REGEXES
        for func, args in bot.plugs['regex']:
            m = args['re'].search(inp.lastparam)
            if m:
                input = Input(conn, *out)
                input.inp = m

                dispatch(input, "regex", func, args)

########NEW FILE########
__FILENAME__ = reload
import collections
import glob
import os
import re
import sys
import traceback


if 'mtimes' not in globals():
    mtimes = {}

if 'lastfiles' not in globals():
    lastfiles = set()


def make_signature(f):
    return f.func_code.co_filename, f.func_name, f.func_code.co_firstlineno


def format_plug(plug, kind='', lpad=0, width=40):
    out = ' ' * lpad + '%s:%s:%s' % make_signature(plug[0])
    if kind == 'command':
        out += ' ' * (50 - len(out)) + plug[1]['name']

    if kind == 'event':
        out += ' ' * (50 - len(out)) + ', '.join(plug[1]['events'])

    if kind == 'regex':
        out += ' ' * (50 - len(out)) + plug[1]['regex']

    return out


def reload(init=False):
    changed = False

    if init:
        bot.plugs = collections.defaultdict(list)
        bot.threads = {}

    core_fileset = set(glob.glob(os.path.join("core", "*.py")))

    for filename in core_fileset:
        mtime = os.stat(filename).st_mtime
        if mtime != mtimes.get(filename):
            mtimes[filename] = mtime

            changed = True

            try:
                eval(compile(open(filename, 'U').read(), filename, 'exec'),
                     globals())
            except Exception:
                traceback.print_exc()
                if init:        # stop if there's an error (syntax?) in a core
                    sys.exit()  # script on startup
                continue

            if filename == os.path.join('core', 'reload.py'):
                reload(init=init)
                return

    fileset = set(glob.glob(os.path.join('plugins', '*.py')))

    # remove deleted/moved plugins
    for name, data in bot.plugs.iteritems():
        bot.plugs[name] = [x for x in data if x[0]._filename in fileset]

    for filename in list(mtimes):
        if filename not in fileset and filename not in core_fileset:
            mtimes.pop(filename)

    for func, handler in list(bot.threads.iteritems()):
        if func._filename not in fileset:
            handler.stop()
            del bot.threads[func]

    # compile new plugins
    for filename in fileset:
        mtime = os.stat(filename).st_mtime
        if mtime != mtimes.get(filename):
            mtimes[filename] = mtime

            changed = True

            try:
                code = compile(open(filename, 'U').read(), filename, 'exec')
                namespace = {}
                eval(code, namespace)
            except Exception:
                traceback.print_exc()
                continue

            # remove plugins already loaded from this filename
            for name, data in bot.plugs.iteritems():
                bot.plugs[name] = [x for x in data
                                   if x[0]._filename != filename]

            for func, handler in list(bot.threads.iteritems()):
                if func._filename == filename:
                    handler.stop()
                    del bot.threads[func]

            for obj in namespace.itervalues():
                if hasattr(obj, '_hook'):  # check for magic
                    if obj._thread:
                        bot.threads[obj] = Handler(obj)

                    for type, data in obj._hook:
                        bot.plugs[type] += [data]

                        if not init:
                            print '### new plugin (type: %s) loaded:' % \
                                type, format_plug(data)

    if changed:
        bot.commands = {}
        for plug in bot.plugs['command']:
            name = plug[1]['name'].lower()
            if not re.match(r'^\w+$', name):
                print '### ERROR: invalid command name "%s" (%s)' % (name,
                                                                     format_plug(plug))
                continue
            if name in bot.commands:
                print "### ERROR: command '%s' already registered (%s, %s)" % \
                    (name, format_plug(bot.commands[name]),
                     format_plug(plug))
                continue
            bot.commands[name] = plug

        bot.events = collections.defaultdict(list)
        for func, args in bot.plugs['event']:
            for event in args['events']:
                bot.events[event].append((func, args))

    if init:
        print '  plugin listing:'

        if bot.commands:
            # hack to make commands with multiple aliases
            # print nicely

            print '    command:'
            commands = collections.defaultdict(list)

            for name, (func, args) in bot.commands.iteritems():
                commands[make_signature(func)].append(name)

            for sig, names in sorted(commands.iteritems()):
                names.sort(key=lambda x: (-len(x), x))  # long names first
                out = ' ' * 6 + '%s:%s:%s' % sig
                out += ' ' * (50 - len(out)) + ', '.join(names)
                print out

        for kind, plugs in sorted(bot.plugs.iteritems()):
            if kind == 'command':
                continue
            print '    %s:' % kind
            for plug in plugs:
                print format_plug(plug, kind=kind, lpad=6)
        print

########NEW FILE########
__FILENAME__ = bf
'''brainfuck interpreter adapted from (public domain) code at
http://brainfuck.sourceforge.net/brain.py'''

import re
import random

from util import hook


BUFFER_SIZE = 5000
MAX_STEPS = 1000000


@hook.command
def bf(inp):
    ".bf <prog> -- executes brainfuck program <prog>"""

    program = re.sub('[^][<>+-.,]', '', inp)

    # create a dict of brackets pairs, for speed later on
    brackets = {}
    open_brackets = []
    for pos in range(len(program)):
        if program[pos] == '[':
            open_brackets.append(pos)
        elif program[pos] == ']':
            if len(open_brackets) > 0:
                brackets[pos] = open_brackets[-1]
                brackets[open_brackets[-1]] = pos
                open_brackets.pop()
            else:
                return 'unbalanced brackets'
    if len(open_brackets) != 0:
        return 'unbalanced brackets'

    # now we can start interpreting
    ip = 0        # instruction pointer
    mp = 0        # memory pointer
    steps = 0
    memory = [0] * BUFFER_SIZE  # initial memory area
    rightmost = 0
    output = ""   # we'll save the output here

    # the main program loop:
    while ip < len(program):
        c = program[ip]
        if c == '+':
            memory[mp] = (memory[mp] + 1) % 256
        elif c == '-':
            memory[mp] = (memory[mp] - 1) % 256
        elif c == '>':
            mp += 1
            if mp > rightmost:
                rightmost = mp
                if mp >= len(memory):
                    # no restriction on memory growth!
                    memory.extend([0] * BUFFER_SIZE)
        elif c == '<':
            mp = mp - 1 % len(memory)
        elif c == '.':
            output += chr(memory[mp])
            if len(output) > 500:
                break
        elif c == ',':
            memory[mp] = random.randint(1, 255)
        elif c == '[':
            if memory[mp] == 0:
                ip = brackets[ip]
        elif c == ']':
            if memory[mp] != 0:
                ip = brackets[ip]

        ip += 1
        steps += 1
        if steps > MAX_STEPS:
            if output == '':
                output = '(no output)'
            output += '[exceeded %d iterations]' % MAX_STEPS
            break

    stripped_output = re.sub(r'[\x00-\x1F]', '', output)

    if stripped_output == '':
        if output != '':
            return 'no printable output'
        return 'no output'

    return stripped_output[:430].decode('utf8', 'ignore')

########NEW FILE########
__FILENAME__ = bitcoin
from util import http, hook


@hook.command(autohelp=False)
def bitcoin(inp, say=None):
    ".bitcoin -- gets current exchange rate for bitcoins from BTC-e"
    data = http.get_json("https://btc-e.com/api/2/btc_usd/ticker")
    say("USD/BTC: \x0307{buy:.0f}\x0f - High: \x0307{high:.0f}\x0f"
            " - Low: \x0307{low:.0f}\x0f - Volume: {vol_cur:.0f}".format(**data['ticker']))

########NEW FILE########
__FILENAME__ = cdecl
from util import hook, http


@hook.command
def cdecl(inp):
	'''.cdecl <expr> -- translate between C declarations and English, using cdecl.org'''
	return http.get("http://cdecl.org/query.php", q=inp)

########NEW FILE########
__FILENAME__ = choose
import re
import random

from util import hook


@hook.command
def choose(inp):
    ".choose <choice1>, <choice2>, ... <choicen> -- makes a decision"

    c = re.findall(r'([^,]+)', inp)
    if len(c) == 1:
        c = re.findall(r'(\S+)', inp)
        if len(c) == 1:
            return 'the decision is up to you'

    return random.choice(c).strip()

########NEW FILE########
__FILENAME__ = crowdcontrol
# crowdcontrol.py by craisins in 2014
# Bot must have some sort of op or admin privileges to be useful

import re
import time
from util import hook

# Use "crowdcontrol" array in config
# syntax
# rule:
#   re: RegEx. regular expression to match
#   msg: String. message to display either with kick or as a warning
#   kick: Integer. 1 for True, 0 for False on if to kick user
#   ban_length: Integer. (optional) Length of time (seconds) to ban user. (-1 to never unban, 0 to not ban, > 1 for time)


@hook.regex(r'.*')
def crowdcontrol(inp, kick=None, ban=None, unban=None, reply=None, bot=None):
    inp = inp.group(0)
    for rule in bot.config.get('crowdcontrol', []):
        if re.search(rule['re'], inp) is not None:
            should_kick = rule.get('kick', 0)
            ban_length = rule.get('ban_length', 0)
            reason = rule.get('msg')
            if ban_length != 0:
                ban()
            if should_kick:
                kick(reason=reason)
            elif 'msg' in rule:
                reply(reason)
            if ban_length > 0:
                time.sleep(ban_length)
                unban()

########NEW FILE########
__FILENAME__ = dice
"""
dice.py: written by Scaevolus 2008, updated 2009
simulates dicerolls
"""
import re
import random

from util import hook


whitespace_re = re.compile(r'\s+')
valid_diceroll = r'^([+-]?(?:\d+|\d*d(?:\d+|F))(?:[+-](?:\d+|\d*d(?:\d+|F)))*)( .+)?$'
valid_diceroll_re = re.compile(valid_diceroll, re.I)
sign_re = re.compile(r'[+-]?(?:\d*d)?(?:\d+|F)', re.I)
split_re = re.compile(r'([\d+-]*)d?(F|\d*)', re.I)


def nrolls(count, n):
    "roll an n-sided die count times"
    if n == "F":
        return [random.randint(-1, 1) for x in xrange(min(count, 100))]
    if n < 2:  # it's a coin
        if count < 5000:
            return [random.randint(0, 1) for x in xrange(count)]
        else:  # fake it
            return [int(random.normalvariate(.5 * count, (.75 * count) ** .5))]
    else:
        if count < 5000:
            return [random.randint(1, n) for x in xrange(count)]
        else:  # fake it
            return [int(random.normalvariate(.5 * (1 + n) * count,
                                             (((n + 1) * (2 * n + 1) / 6. - (.5 * (1 + n)) ** 2) * count) ** .5))]


@hook.command('roll')
#@hook.regex(valid_diceroll, re.I)
@hook.command
def dice(inp):
    ".dice <diceroll> -- simulates dicerolls, e.g. .dice 2d20-d5+4 roll 2 " \
        "D20s, subtract 1D5, add 4"

    try:  # if inp is a re.match object...
        (inp, desc) = inp.groups()
    except AttributeError:
        (inp, desc) = valid_diceroll_re.match(inp).groups()

    if "d" not in inp:
        return

    spec = whitespace_re.sub('', inp)
    if not valid_diceroll_re.match(spec):
        return "Invalid diceroll"
    groups = sign_re.findall(spec)

    total = 0
    rolls = []

    for roll in groups:
        count, side = split_re.match(roll).groups()
        count = int(count) if count not in " +-" else 1
        if side.upper() == "F":  # fudge dice are basically 1d3-2
            for fudge in nrolls(count, "F"):
                if fudge == 1:
                    rolls.append("\x033+\x0F")
                elif fudge == -1:
                    rolls.append("\x034-\x0F")
                else:
                    rolls.append("0")
                total += fudge
        elif side == "":
            total += count
        else:
            side = int(side)
            try:
                if count > 0:
                    dice = nrolls(count, side)
                    rolls += map(str, dice)
                    total += sum(dice)
                else:
                    dice = nrolls(-count, side)
                    rolls += [str(-x) for x in dice]
                    total -= sum(dice)
            except OverflowError:
                return "Thanks for overflowing a float, jerk >:["

    if desc:
        return "%s: %d (%s=%s)" % (desc.strip(),  total, inp, ", ".join(rolls))
    else:
        return "%d (%s=%s)" % (total, inp, ", ".join(rolls))

########NEW FILE########
__FILENAME__ = dictionary
import re

from util import hook, http


@hook.command('u')
@hook.command
def urban(inp):
    '''.u/.urban <phrase> -- looks up <phrase> on urbandictionary.com'''

    url = 'http://www.urbandictionary.com/iphone/search/define'
    page = http.get_json(url, term=inp, headers={'Referer': 'http://m.urbandictionary.com'})
    defs = page['list']

    if page['result_type'] == 'no_results':
        return 'not found.'

    out = defs[0]['word'] + ': ' + defs[0]['definition'].replace('\r\n', ' ')

    if len(out) > 400:
        out = out[:out.rfind(' ', 0, 400)] + '...'

    return out


# define plugin by GhettoWizard & Scaevolus
@hook.command('dictionary')
@hook.command
def define(inp):
    ".define/.dictionary <word> -- fetches definition of <word>"

    url = 'http://ninjawords.com/'

    h = http.get_html(url + http.quote_plus(inp))

    definition = h.xpath('//dd[@class="article"] | '
                         '//div[@class="definition"] |'
                         '//div[@class="example"]')

    if not definition:
        return 'No results for ' + inp

    def format_output(show_examples):
        result = '%s: ' % h.xpath('//dt[@class="title-word"]/a/text()')[0]

        correction = h.xpath('//span[@class="correct-word"]/text()')
        if correction:
            result = 'definition for "%s": ' % correction[0]

        sections = []
        for section in definition:
            if section.attrib['class'] == 'article':
                sections += [[section.text_content() + ': ']]
            elif section.attrib['class'] == 'example':
                if show_examples:
                    sections[-1][-1] += ' ' + section.text_content()
            else:
                sections[-1] += [section.text_content()]

        for article in sections:
            result += article[0]
            if len(article) > 2:
                result += ' '.join('%d. %s' % (n + 1, section)
                                   for n, section in enumerate(article[1:]))
            else:
                result += article[1] + ' '

        synonyms = h.xpath('//dd[@class="synonyms"]')
        if synonyms:
            result += synonyms[0].text_content()

        result = re.sub(r'\s+', ' ', result)
        result = re.sub('\xb0', '', result)
        return result

    result = format_output(True)
    if len(result) > 450:
        result = format_output(False)

    if len(result) > 450:
        result = result[:result.rfind(' ', 0, 450)]
        result = re.sub(r'[^A-Za-z]+\.?$', '', result) + ' ...'

    return result


@hook.command('e')
@hook.command
def etymology(inp):
    ".e/.etymology <word> -- Retrieves the etymology of chosen word"

    url = 'http://www.etymonline.com/index.php'

    h = http.get_html(url, term=inp)

    etym = h.xpath('//dl')

    if not etym:
        return 'No etymology found for ' + inp

    etym = etym[0].text_content()

    etym = ' '.join(etym.split())

    if len(etym) > 400:
        etym = etym[:etym.rfind(' ', 0, 400)] + ' ...'

    return etym

########NEW FILE########
__FILENAME__ = dotnetpad
"dotnetpad.py: by sklnd, because gobiner wouldn't shut up"

import urllib
import httplib
import socket
import json

from util import hook


def dotnetpad(lang, code, timeout=30):
    "Posts a provided snippet of code in a provided langugage to dotnetpad.net"

    code = code.encode('utf8')
    params = urllib.urlencode({'language': lang, 'code': code})

    headers = {"Content-type": "application/x-www-form-urlencoded",
               "Accept": "text/plain"}

    try:
        conn = httplib.HTTPConnection("dotnetpad.net", 80, timeout=timeout)
        conn.request("POST", "/Skybot", params, headers)
        response = conn.getresponse()
    except httplib.HTTPException:
        conn.close()
        return 'error: dotnetpad is broken somehow'
    except socket.error:
        return 'error: unable to connect to dotnetpad'

    try:
        result = json.loads(response.read())
    except ValueError:
        conn.close()
        return 'error: dotnetpad is broken somehow'

    conn.close()

    if result['Errors']:
        return 'First error: %s' % (result['Errors'][0]['ErrorText'])
    elif result['Output']:
        return result['Output'].lstrip()
    else:
        return 'No output'


@hook.command
def fs(inp):
    ".fs -- post a F# code snippet to dotnetpad.net and print the results"

    return dotnetpad('fsharp', inp)


@hook.command
def cs(snippet):
    ".cs -- post a C# code snippet to dotnetpad.net and print the results"

    file_template = ('using System; '
                     'using System.Linq; '
                     'using System.Collections.Generic; '
                     'using System.Text; '
                     '%s')

    class_template = ('public class Default '
                      '{'
                      '    %s \n'
                      '}')

    main_template = ('public static void Main(String[] args) '
                     '{'
                     '    %s \n'
                     '}')

    # There are probably better ways to do the following, but I'm feeling lazy
    # if no main is found in the snippet, use the template with Main in it
    if 'public static void Main' not in snippet:
        code = main_template % snippet
        code = class_template % code
        code = file_template % code

    # if Main is found, check for class and see if we need to use the
    # classed template
    elif 'class' not in snippet:
        code = class_template % snippet
        code = file_template % code

        return 'Error using dotnetpad'
    # if we found class, then use the barebones template
    else:
        code = file_template % snippet

    return dotnetpad('csharp', code)

########NEW FILE########
__FILENAME__ = down
import urlparse

from util import hook, http


@hook.command
def down(inp):
    '''.down <url> -- checks to see if the site is down'''

    if 'http://' not in inp:
        inp = 'http://' + inp

    inp = 'http://' + urlparse.urlparse(inp).netloc

    # http://mail.python.org/pipermail/python-list/2006-December/589854.html
    try:
        http.get(inp, get_method='HEAD')
        return inp + ' seems to be up'
    except http.URLError:
        return inp + ' seems to be down'

########NEW FILE########
__FILENAME__ = drama
'''Searches Encyclopedia Dramatica and returns the first paragraph of the
article'''

from util import hook, http

api_url = "http://encyclopediadramatica.se/api.php?action=opensearch"
ed_url = "http://encyclopediadramatica.se/"


@hook.command('ed')
@hook.command
def drama(inp):
    '''.drama <phrase> -- gets first paragraph of Encyclopedia Dramatica ''' \
        '''article on <phrase>'''

    j = http.get_json(api_url, search=inp)
    if not j[1]:
        return 'no results found'
    article_name = j[1][0].replace(' ', '_').encode('utf8')

    url = ed_url + http.quote(article_name, '')
    page = http.get_html(url)

    for p in page.xpath('//div[@id="bodyContent"]/p'):
        if p.text_content():
            summary = ' '.join(p.text_content().splitlines())
            if len(summary) > 300:
                summary = summary[:summary.rfind(' ', 0, 300)] + "..."
            return '%s :: \x02%s\x02' % (summary, url)

    return "error"

########NEW FILE########
__FILENAME__ = gcalc
from util import hook, http


@hook.command
def calc(inp):
    '''.calc <term> -- returns Google Calculator result'''

    h = http.get_html('http://www.google.com/search', q=inp)

    m = h.xpath('//h2[@class="r"]/text()')

    if not m:
        return "could not calculate " + inp

    res = ' '.join(m[0].split())

    return res

########NEW FILE########
__FILENAME__ = gif
import random

from util import hook, http


@hook.api_key('giphy')
@hook.command('gif')
@hook.command
def giphy(inp, api_key=None):
    '''.gif/.giphy <query> -- returns first giphy search result'''
    url = 'http://api.giphy.com/v1/gifs/search'
    try:
        response = http.get_json(url, q=inp, limit=10, api_key=api_key)
    except http.HTTPError as e:
        return e.msg

    results = response.get('data')
    if results:
        return random.choice(results).get('bitly_gif_url')
    else:
        return 'no results found'

########NEW FILE########
__FILENAME__ = google
import random

from util import hook, http


def api_get(query, key, is_image=None, num=1):
    url = ('https://www.googleapis.com/customsearch/v1?cx=007629729846476161907:ud5nlxktgcw'
           '&fields=items(title,link,snippet)&safe=off' + ('&searchType=image' if is_image else ''))
    return http.get_json(url, key=key, q=query, num=num)


@hook.api_key('google')
@hook.command
def gis(inp, api_key=None):
    '''.gis <term> -- finds an image using google images (safesearch off)'''

    parsed = api_get(inp, api_key, is_image=True, num=10)
    if 'items' not in parsed:
        return 'no images found'
    return random.choice(parsed['items'])['link']


@hook.api_key('google')
@hook.command('g')
@hook.command
def google(inp, api_key=None):
    '''.g/.google <query> -- returns first google search result'''

    parsed = api_get(inp, api_key)
    if 'items' not in parsed:
        return 'no results found'

    out = u'{link} -- \x02{title}\x02: "{snippet}"'.format(**parsed['items'][0])
    out = ' '.join(out.split())

    if len(out) > 300:
        out = out[:out.rfind(' ')] + '..."'

    return out

########NEW FILE########
__FILENAME__ = hash
import hashlib

from util import hook


@hook.command
def md5(inp):
    return hashlib.md5(inp).hexdigest()


@hook.command
def sha1(inp):
    return hashlib.sha1(inp).hexdigest()


@hook.command
def hash(inp):
    ".hash <text> -- returns hashes of <text>"
    return ', '.join(x + ": " + getattr(hashlib, x)(inp).hexdigest()
                     for x in 'md5 sha1 sha256'.split())

########NEW FILE########
__FILENAME__ = help
import re

from util import hook


@hook.command(autohelp=False)
def help(inp, bot=None, pm=None):
    ".help [command] -- gives a list of commands/help for a command"

    funcs = {}
    disabled = bot.config.get('disabled_plugins', [])
    disabled_comm = bot.config.get('disabled_commands', [])
    for command, (func, args) in bot.commands.iteritems():
        fn = re.match(r'^plugins.(.+).py$', func._filename)
        if fn.group(1).lower() not in disabled:
            if command not in disabled_comm:
                if func.__doc__ is not None:
                    if func in funcs:
                        if len(funcs[func]) < len(command):
                            funcs[func] = command
                    else:
                        funcs[func] = command

    commands = dict((value, key) for key, value in funcs.iteritems())

    if not inp:
        pm('available commands: ' + ' '.join(sorted(commands)))
    else:
        if inp in commands:
            pm(commands[inp].__doc__)

########NEW FILE########
__FILENAME__ = imdb
# IMDb lookup plugin by Ghetto Wizard (2011).

from util import hook, http


@hook.command
def imdb(inp):
    '''.imdb <movie> -- gets information about <movie> from IMDb'''

    content = http.get_json("http://www.omdbapi.com/", t=inp)

    if content['Response'] == 'Movie Not Found':
        return 'movie not found'
    elif content['Response'] == 'True':
        content['URL'] = 'http://www.imdb.com/title/%(imdbID)s' % content

        out = '\x02%(Title)s\x02 (%(Year)s) (%(Genre)s): %(Plot)s'
        if content['Runtime'] != 'N/A':
            out += ' \x02%(Runtime)s\x02.'
        if content['imdbRating'] != 'N/A' and content['imdbVotes'] != 'N/A':
            out += ' \x02%(imdbRating)s/10\x02 with \x02%(imdbVotes)s\x02 votes.'
        out += ' %(URL)s'
        return out % content
    else:
        return 'unknown error'

########NEW FILE########
__FILENAME__ = lastfm
'''
The Last.fm API key is retrieved from the bot config file.
'''

from util import hook, http


api_url = "http://ws.audioscrobbler.com/2.0/?format=json"


@hook.api_key('lastfm')
@hook.command(autohelp=False)
def lastfm(inp, nick='', say=None, api_key=None):
    if inp:
        user = inp
    else:
        user = nick

    response = http.get_json(api_url, method="user.getrecenttracks",
                             api_key=api_key, user=user, limit=1)

    if 'error' in response:
        if inp:  # specified a user name
            return "error: %s" % response["message"]
        else:
            return "your nick is not a Last.fm account. try '.lastfm username'."

    if not "track" in response["recenttracks"] or len(response["recenttracks"]["track"]) == 0:
        return "no recent tracks for user \x02%s\x0F found" % user

    tracks = response["recenttracks"]["track"]

    if type(tracks) == list:
        # if the user is listening to something, the tracks entry is a list
        # the first item is the current track
        track = tracks[0]
        status = 'current track'
    elif type(tracks) == dict:
        # otherwise, they aren't listening to anything right now, and
        # the tracks entry is a dict representing the most recent track
        track = tracks
        status = 'last track'
    else:
        return "error parsing track listing"

    title = track["name"]
    album = track["album"]["#text"]
    artist = track["artist"]["#text"]

    ret = "\x02%s\x0F's %s - \x02%s\x0f" % (user, status, title)
    if artist:
        ret += " by \x02%s\x0f" % artist
    if album:
        ret += " on \x02%s\x0f" % album

    say(ret)

########NEW FILE########
__FILENAME__ = log
"""
log.py: written by Scaevolus 2009
"""

import os
import codecs
import time
import re

from util import hook


log_fds = {}  # '%(net)s %(chan)s' : (filename, fd)

timestamp_format = '%H:%M:%S'

formats = {'PRIVMSG': '<%(nick)s> %(msg)s',
           'PART': '-!- %(nick)s [%(user)s@%(host)s] has left %(chan)s',
           'JOIN': '-!- %(nick)s [%(user)s@%(host)s] has joined %(param0)s',
           'MODE': '-!- mode/%(chan)s [%(param_tail)s] by %(nick)s',
           'KICK': '-!- %(param1)s was kicked from %(chan)s by %(nick)s [%(msg)s]',
           'TOPIC': '-!- %(nick)s changed the topic of %(chan)s to: %(msg)s',
           'QUIT': '-!- %(nick)s has quit [%(msg)s]',
           'PING': '',
           'NOTICE': ''
           }

ctcp_formats = {'ACTION': '* %(nick)s %(ctcpmsg)s'}

irc_color_re = re.compile(r'(\x03(\d+,\d+|\d)|[\x0f\x02\x16\x1f])')


def get_log_filename(dir, server, chan):
    return os.path.join(dir, 'log', gmtime('%Y'), server,
                        (gmtime('%%s.%m-%d.log') % chan).lower())


def gmtime(format):
    return time.strftime(format, time.gmtime())


def beautify(input):
    format = formats.get(input.command, '%(raw)s')
    args = dict(input)

    leng = len(args['paraml'])
    for n, p in enumerate(args['paraml']):
        args['param' + str(n)] = p
        args['param_' + str(abs(n - leng))] = p

    args['param_tail'] = ' '.join(args['paraml'][1:])
    args['msg'] = irc_color_re.sub('', args['msg'])

    if input.command == 'PRIVMSG' and input.msg.count('\x01') >= 2:
        ctcp = input.msg.split('\x01', 2)[1].split(' ', 1)
        if len(ctcp) == 1:
            ctcp += ['']
        args['ctcpcmd'], args['ctcpmsg'] = ctcp
        format = ctcp_formats.get(args['ctcpcmd'],
                                  '%(nick)s [%(user)s@%(host)s] requested unknown CTCP '
                                  '%(ctcpcmd)s from %(chan)s: %(ctcpmsg)s')

    return format % args


def get_log_fd(dir, server, chan):
    fn = get_log_filename(dir, server, chan)
    cache_key = '%s %s' % (server, chan)
    filename, fd = log_fds.get(cache_key, ('', 0))

    if fn != filename:  # we need to open a file for writing
        if fd != 0:     # is a valid fd
            fd.flush()
            fd.close()
        dir = os.path.split(fn)[0]
        if not os.path.exists(dir):
            os.makedirs(dir)
        fd = codecs.open(fn, 'a', 'utf-8')
        log_fds[cache_key] = (fn, fd)

    return fd


@hook.singlethread
@hook.event('*')
def log(paraml, input=None, bot=None):
    timestamp = gmtime(timestamp_format)

    if input.command == 'QUIT':  # these are temporary fixes until proper
        input.chan = 'quit'      # presence tracking is implemented
    if input.command == 'NICK':
        input.chan = 'nick'

    beau = beautify(input)

    if beau == '':  # don't log this
        return

    if input.chan:
        fd = get_log_fd(bot.persist_dir, input.server, input.chan)
        fd.write(timestamp + ' ' + beau + '\n')

    print timestamp, input.chan, beau.encode('utf8', 'ignore')

########NEW FILE########
__FILENAME__ = mem
import os
import re

from util import hook


@hook.command(autohelp=False)
def mem(inp):
    ".mem -- returns bot's current memory usage -- linux/windows only"

    if os.name == 'posix':
        status_file = open("/proc/%d/status" % os.getpid()).read()
        line_pairs = re.findall(r"^(\w+):\s*(.*)\s*$", status_file, re.M)
        status = dict(line_pairs)
        keys = 'VmSize VmLib VmData VmExe VmRSS VmStk'.split()
        return ', '.join(key + ':' + status[key] for key in keys)

    elif os.name == 'nt':
        cmd = "tasklist /FI \"PID eq %s\" /FO CSV /NH" % os.getpid()
        out = os.popen(cmd).read()

        total = 0
        for amount in re.findall(r'([,0-9]+) K', out):
            total += int(amount.replace(',', ''))

        return 'memory usage: %d kB' % total

    return mem.__doc__

########NEW FILE########
__FILENAME__ = metacritic
# metacritic.com scraper

import re
from urllib2 import HTTPError

from util import hook, http


@hook.command('mc')
def metacritic(inp):
    '.mc [all|movie|tv|album|x360|ps3|pc|gba|ds|3ds|wii|vita|wiiu|xone|ps4] <title> -- gets rating for'\
    ' <title> from metacritic on the specified medium'

    # if the results suck, it's metacritic's fault

    args = inp.strip()

    game_platforms = ('x360', 'ps3', 'pc', 'gba', 'ds', '3ds', 'wii', 'vita', 'wiiu', 'xone', 'ps4')
    all_platforms = game_platforms + ('all', 'movie', 'tv', 'album')

    try:
        plat, title = args.split(' ', 1)
        if plat not in all_platforms:
            # raise the ValueError so that the except block catches it
            # in this case, or in the case of the .split above raising the
            # ValueError, we want the same thing to happen
            raise ValueError
    except ValueError:
        plat = 'all'
        title = args

    cat = 'game' if plat in game_platforms else plat

    title_safe = http.quote_plus(title)

    url = 'http://www.metacritic.com/search/%s/%s/results' % (cat, title_safe)

    try:
        doc = http.get_html(url)
    except HTTPError:
        return 'error fetching results'

    ''' result format:
    -- game result, with score
    -- subsequent results are the same structure, without first_result class
    <li class="result first_result">
        <div class="result_type">
            <strong>Game</strong>
            <span class="platform">WII</span>
        </div>
        <div class="result_wrap">
            <div class="basic_stats has_score">
                <div class="main_stats">
                    <h3 class="product_title basic_stat">...</h3>
                    <div class="std_score">
                      <div class="score_wrap">
                        <span class="label">Metascore: </span>
                        <span class="data metascore score_favorable">87</span>
                      </div>
                    </div>
                </div>
                <div class="more_stats extended_stats">...</div>
            </div>
        </div>
    </li>

    -- other platforms are the same basic layout
    -- if it doesn't have a score, there is no div.basic_score
    -- the <div class="result_type"> changes content for non-games:
    <div class="result_type"><strong>Movie</strong></div>
    '''

    # get the proper result element we want to pull data from

    result = None

    if not doc.find_class('query_results'):
        return 'no results found'

    # if they specified an invalid search term, the input box will be empty
    if doc.get_element_by_id('search_term').value == '':
        return 'invalid search term'

    if plat not in game_platforms:
        # for [all] results, or non-game platforms, get the first result
        result = doc.find_class('result first_result')[0]

        # find the platform, if it exists
        result_type = result.find_class('result_type')
        if result_type:

            # if the result_type div has a platform div, get that one
            platform_div = result_type[0].find_class('platform')
            if platform_div:
                plat = platform_div[0].text_content().strip()
            else:
                # otherwise, use the result_type text_content
                plat = result_type[0].text_content().strip()

    else:
        # for games, we want to pull the first result with the correct
        # platform
        results = doc.find_class('result')
        for res in results:
            result_plat = res.find_class('platform')[0].text_content().strip()
            if result_plat == plat.upper():
                result = res
                break

    if not result:
        return 'no results found'

    # get the name, release date, and score from the result
    product_title = result.find_class('product_title')[0]
    name = product_title.text_content()
    link = 'http://metacritic.com' + product_title.find('a').attrib['href']

    try:
        release = result.find_class('release_date')[0].\
            find_class('data')[0].text_content()

        # strip extra spaces out of the release date
        release = re.sub(r'\s{2,}', ' ', release)
    except IndexError:
        release = None

    try:
        score = result.find_class('metascore_w')[0].text_content()
    except IndexError:
        score = None

    return '[%s] %s - %s, %s -- %s' % (plat.upper(), name,
                                       score or 'no score',
                                       'release: %s' % release if release else 'unreleased',
                                       link)

########NEW FILE########
__FILENAME__ = misc
import socket
import subprocess
import time

from util import hook, http

socket.setdefaulttimeout(10)  # global setting


def get_version():
    p = subprocess.Popen(['git', 'log', '--oneline'], stdout=subprocess.PIPE)
    stdout, _ = p.communicate()
    p.wait()

    revnumber = len(stdout.splitlines())

    shorthash = stdout.split(None, 1)[0]

    http.ua_skybot = 'Skybot/r%d %s (http://github.com/rmmh/skybot)' \
        % (revnumber, shorthash)

    return shorthash, revnumber


# autorejoin channels
@hook.event('KICK')
def rejoin(paraml, conn=None):
    if paraml[1] == conn.nick:
        if paraml[0].lower() in conn.conf.get("channels", []):
            conn.join(paraml[0])


# join channels when invited
@hook.event('INVITE')
def invite(paraml, conn=None):
    conn.join(paraml[-1])


@hook.event('004')
def onjoin(paraml, conn=None):
    # identify to services
    nickserv_password = conn.conf.get('nickserv_password', '')
    nickserv_name = conn.conf.get('nickserv_name', 'nickserv')
    nickserv_command = conn.conf.get('nickserv_command', 'IDENTIFY %s')
    if nickserv_password:
        conn.msg(nickserv_name, nickserv_command % nickserv_password)
        time.sleep(1)

    # set mode on self
    mode = conn.conf.get('mode')
    if mode:
        conn.cmd('MODE', [conn.nick, mode])

    # join channels
    for channel in conn.conf.get("channels", []):
        conn.join(channel)
        time.sleep(1)  # don't flood JOINs

    # set user-agent
    ident, rev = get_version()


@hook.regex(r'^\x01VERSION\x01$')
def version(inp, notice=None):
    ident, rev = get_version()
    notice('\x01VERSION skybot %s r%d - http://github.com/rmmh/'
           'skybot/\x01' % (ident, rev))

########NEW FILE########
__FILENAME__ = mtg
import re

from util import hook, http


@hook.command
def mtg(inp):
    ".mtg <name> -- gets information about Magic the Gathering card <name>"

    url = 'http://magiccards.info/query?v=card&s=cname'
    h = http.get_html(url, q=inp)

    name = h.find('body/table/tr/td/span/a')
    if name is None:
        return "no cards found"
    card = name.getparent().getparent().getparent()

    type = card.find('td/p').text.replace('\n', '')

    # this is ugly
    text = http.html.tostring(card.xpath("//p[@class='ctext']/b")[0])
    text = text.replace('<br>', '$')
    text = http.html.fromstring(text).text_content()
    text = re.sub(r'(\w+\s*)\$+(\s*\w+)', r'\1. \2', text)
    text = text.replace('$', ' ')
    text = re.sub(r'\(.*?\)', '', text)  # strip parenthetical explanations
    text = re.sub(r'\.(\S)', r'. \1', text)  # fix spacing

    printings = card.find('td/small').text_content()
    printings = re.search(r'Editions:(.*)Languages:', printings).group(1)
    printings = re.findall(r'\s*(.+?(?: \([^)]+\))*) \((.*?)\)',
                           ' '.join(printings.split()))

    printing_out = ', '.join('%s (%s)' % (set_abbrevs.get(x[0], x[0]),
                                          rarity_abbrevs.get(x[1], x[1]))
                             for x in printings)

    name.make_links_absolute(base_url=url)
    link = name.attrib['href']
    name = name.text_content().strip()
    type = type.strip()
    text = ' '.join(text.split())

    return ' | '.join((name, type, text, printing_out, link))


set_abbrevs = {
    '15th Anniversary': '15ANN',
    'APAC Junior Series': 'AJS',
    'Alara Reborn': 'ARB',
    'Alliances': 'AI',
    'Anthologies': 'AT',
    'Antiquities': 'AQ',
    'Apocalypse': 'AP',
    'Arabian Nights': 'AN',
    'Arena League': 'ARENA',
    'Asia Pacific Land Program': 'APAC',
    'Battle Royale': 'BR',
    'Battle Royale Box Set': 'BRB',
    'Beatdown': 'BTD',
    'Beatdown Box Set': 'BTD',
    'Betrayers of Kamigawa': 'BOK',
    'Celebration Cards': 'UQC',
    'Champions of Kamigawa': 'CHK',
    'Champs': 'CP',
    'Chronicles': 'CH',
    'Classic Sixth Edition': '6E',
    'Coldsnap': 'CS',
    'Coldsnap Theme Decks': 'CSTD',
    'Conflux': 'CFX',
    'Core Set - Eighth Edition': '8E',
    'Core Set - Ninth Edition': '9E',
    'Darksteel': 'DS',
    'Deckmasters': 'DM',
    'Dissension': 'DI',
    'Dragon Con': 'DRC',
    'Duel Decks: Divine vs. Demonic': 'DVD',
    'Duel Decks: Elves vs. Goblins': 'EVG',
    'Duel Decks: Garruk vs. Liliana': 'GVL',
    'Duel Decks: Jace vs. Chandra': 'JVC',
    'Eighth Edition': '8ED',
    'Eighth Edition Box Set': '8EB',
    'European Land Program': 'EURO',
    'Eventide': 'EVE',
    'Exodus': 'EX',
    'Fallen Empires': 'FE',
    'Fifth Dawn': '5DN',
    'Fifth Edition': '5E',
    'Fourth Edition': '4E',
    'Friday Night Magic': 'FNMP',
    'From the Vault: Dragons': 'FVD',
    'From the Vault: Exiled': 'FVE',
    'Future Sight': 'FUT',
    'Gateway': 'GRC',
    'Grand Prix': 'GPX',
    'Guildpact': 'GP',
    'Guru': 'GURU',
    'Happy Holidays': 'HHO',
    'Homelands': 'HL',
    'Ice Age': 'IA',
    'Introductory Two-Player Set': 'ITP',
    'Invasion': 'IN',
    'Judge Gift Program': 'JR',
    'Judgment': 'JU',
    'Junior Series': 'JSR',
    'Legend Membership': 'DCILM',
    'Legends': 'LG',
    'Legions': 'LE',
    'Limited Edition (Alpha)': 'LEA',
    'Limited Edition (Beta)': 'LEB',
    'Limited Edition Alpha': 'LEA',
    'Limited Edition Beta': 'LEB',
    'Lorwyn': 'LW',
    'MTGO Masters Edition': 'MED',
    'MTGO Masters Edition II': 'ME2',
    'MTGO Masters Edition III': 'ME3',
    'Magic 2010': 'M10',
    'Magic Game Day Cards': 'MGDC',
    'Magic Player Rewards': 'MPRP',
    'Magic Scholarship Series': 'MSS',
    'Magic: The Gathering Launch Parties': 'MLP',
    'Media Inserts': 'MBP',
    'Mercadian Masques': 'MM',
    'Mirage': 'MR',
    'Mirrodin': 'MI',
    'Morningtide': 'MT',
    'Multiverse Gift Box Cards': 'MGBC',
    'Nemesis': 'NE',
    'Ninth Edition Box Set': '9EB',
    'Odyssey': 'OD',
    'Onslaught': 'ON',
    'Planar Chaos': 'PC',
    'Planechase': 'PCH',
    'Planeshift': 'PS',
    'Portal': 'PO',
    'Portal Demogame': 'POT',
    'Portal Second Age': 'PO2',
    'Portal Three Kingdoms': 'P3K',
    'Premium Deck Series: Slivers': 'PDS',
    'Prerelease Events': 'PTC',
    'Pro Tour': 'PRO',
    'Prophecy': 'PR',
    'Ravnica: City of Guilds': 'RAV',
    'Release Events': 'REP',
    'Revised Edition': 'RV',
    'Saviors of Kamigawa': 'SOK',
    'Scourge': 'SC',
    'Seventh Edition': '7E',
    'Shadowmoor': 'SHM',
    'Shards of Alara': 'ALA',
    'Starter': 'ST',
    'Starter 1999': 'S99',
    'Starter 2000 Box Set': 'ST2K',
    'Stronghold': 'SH',
    'Summer of Magic': 'SOM',
    'Super Series': 'SUS',
    'Tempest': 'TP',
    'Tenth Edition': '10E',
    'The Dark': 'DK',
    'Time Spiral': 'TS',
    'Time Spiral Timeshifted': 'TSTS',
    'Torment': 'TR',
    'Two-Headed Giant Tournament': 'THGT',
    'Unglued': 'UG',
    'Unhinged': 'UH',
    'Unhinged Alternate Foils': 'UHAA',
    'Unlimited Edition': 'UN',
    "Urza's Destiny": 'UD',
    "Urza's Legacy": 'UL',
    "Urza's Saga": 'US',
    'Visions': 'VI',
    'Weatherlight': 'WL',
    'Worlds': 'WRL',
    'WotC Online Store': 'WOTC',
    'Zendikar': 'ZEN'}

rarity_abbrevs = {
    'Land': 'L',
    'Common': 'C',
    'Uncommon': 'UC',
    'Rare': 'R',
    'Special': 'S',
    'Mythic Rare': 'MR'}

########NEW FILE########
__FILENAME__ = oblique
import time

from util import hook, http


commands_modtime = 0
commands = {}


def update_commands(force=False):
    global commands_modtime, commands

    if force or time.time() - commands_modtime > 60 * 60:  # update hourly
        h = http.get_html('http://wiki.github.com/nslater/oblique/')

        lines = h.xpath('//li/text()')
        commands = {}
        for line in lines:
            if not line.strip():
                continue

            if line.strip().find(" ") == -1:
                continue

            name, url = line.strip().split(None, 1)
            commands[name] = url

        commands_modtime = time.time()


@hook.command('o')
@hook.command
def oblique(inp, nick='', chan=''):
    '.o/.oblique <command> <args> -- runs <command> using oblique web'
    ' services. see http://wiki.github.com/nslater/oblique/'

    update_commands()

    if ' ' in inp:
        command, args = inp.split(None, 1)
    else:
        command = inp
        args = ''

    command = command.lower()

    if command == 'refresh':
        update_commands(True)
        return '%d commands loaded.' % len(commands)
    if command in commands:
        url = commands[command]
        url = url.replace('${nick}', nick)
        url = url.replace('${sender}', chan)
        url = url.replace('${args}', http.quote(args.encode('utf8')))
        try:
            return http.get(url)
        except http.HTTPError, e:
            return "http error %d" % e.code
    else:
        return 'no such service'

########NEW FILE########
__FILENAME__ = pre
# searches scene releases using orlydb

from util import hook, http


@hook.command
def predb(inp):
    '.predb <query> -- searches scene releases using orlydb.com'

    try:
        h = http.get_html("http://orlydb.com/", q=inp)
    except HTTPError:
        return 'orlydb seems to be down'

    results = h.xpath("//div[@id='releases']/div/span[@class='release']/..")

    if not results:
        return "zero results"

    result = results[0]

    date, time = result.xpath("span[@class='timestamp']/text()")[0].split()
    section, = result.xpath("span[@class='section']//text()")
    name, = result.xpath("span[@class='release']/text()")

    size = result.xpath("span[@class='inforight']//text()")
    if size:
        size = ' :: ' + size[0].split()[0]
    else:
        size = ''

    return '%s - %s - %s%s' % (date, section, name, size)

########NEW FILE########
__FILENAME__ = profile
# for crusty old rotor

from util import hook


@hook.command
def profile(inp):
    ".profile <username> -- links to <username>'s profile on SA"

    return 'http://forums.somethingawful.com/member.php?action=getinfo' + \
        '&username=' + '+'.join(inp.split())

########NEW FILE########
__FILENAME__ = pyexec
import re

from util import hook, http


re_lineends = re.compile(r'[\r\n]*')


@hook.command
def python(inp):
    ".python <prog> -- executes python code <prog>"

    res = http.get("http://eval.appspot.com/eval", statement=inp).splitlines()

    if len(res) == 0:
        return
    res[0] = re_lineends.split(res[0])[0]
    if not res[0] == 'Traceback (most recent call last):':
        return res[0].decode('utf8', 'ignore')
    else:
        return res[-1].decode('utf8', 'ignore')

########NEW FILE########
__FILENAME__ = quote
import random
import re
import time

from util import hook


def add_quote(db, chan, nick, add_nick, msg):
    db.execute('''insert or fail into quote (chan, nick, add_nick,
                    msg, time) values(?,?,?,?,?)''',
               (chan, nick, add_nick, msg, time.time()))
    db.commit()


def del_quote(db, chan, nick, msg):
    updated = db.execute('''update quote set deleted = 1 where
                  chan=? and lower(nick)=lower(?) and msg=?''',
                  (chan, nick, msg))
    db.commit()

    if updated.rowcount == 0:
        return False
    else:
        return True


def get_quotes_by_nick(db, chan, nick):
    return db.execute("select time, nick, msg from quote where deleted!=1 "
                      "and chan=? and lower(nick)=lower(?) order by time",
                      (chan, nick)).fetchall()


def get_quotes_by_chan(db, chan):
    return db.execute("select time, nick, msg from quote where deleted!=1 "
                      "and chan=? order by time", (chan,)).fetchall()


def format_quote(q, num, n_quotes):
    ctime, nick, msg = q
    return "[%d/%d] %s <%s> %s" % (num, n_quotes,
                                   time.strftime("%Y-%m-%d", time.gmtime(ctime)), nick, msg)


@hook.command('q')
@hook.command
def quote(inp, nick='', chan='', db=None, admin=False):
    ".q/.quote [#chan] [nick] [#n]/.quote add|delete <nick> <msg> -- gets " \
        "random or [#n]th quote by <nick> or from <#chan>/adds or deletes " \
        "quote"

    db.execute("create table if not exists quote"
               "(chan, nick, add_nick, msg, time real, deleted default 0, "
               "primary key (chan, nick, msg))")
    db.commit()

    add = re.match(r"add[^\w@]+(\S+?)>?\s+(.*)", inp, re.I)
    delete = re.match(r"delete[^\w@]+(\S+?)>?\s+(.*)", inp, re.I)
    retrieve = re.match(r"(\S+)(?:\s+#?(-?\d+))?$", inp)
    retrieve_chan = re.match(r"(#\S+)\s+(\S+)(?:\s+#?(-?\d+))?$", inp)

    if add:
        quoted_nick, msg = add.groups()
        try:
            add_quote(db, chan, quoted_nick, nick, msg)
            db.commit()
        except db.IntegrityError:
            return "message already stored, doing nothing."
        return "quote added."
    if delete:
        if not admin:
            return 'only admins can delete quotes'
        quoted_nick, msg = delete.groups()
        if del_quote(db, chan, quoted_nick, msg):
            return "deleted quote '%s'" % msg
        else:
            return "found no matching quotes to delete"
    elif retrieve:
        select, num = retrieve.groups()

        if select.startswith('#'):
            quotes = get_quotes_by_chan(db, select)
        else:
            quotes = get_quotes_by_nick(db, chan, select)
    elif retrieve_chan:
        chan, nick, num = retrieve_chan.groups()

        quotes = get_quotes_by_nick(db, chan, nick)
    else:
        return quote.__doc__

    n_quotes = len(quotes)

    if not n_quotes:
        return "no quotes found"

    if num:
        num = int(num)

    if num:
        if num > n_quotes or (num < 0 and num < -n_quotes):
            return "I only have %d quote%s for %s" % (n_quotes,
                                                      ('s', '')[n_quotes == 1], select)
        elif num < 0:
            selected_quote = quotes[num]
            num = n_quotes + num + 1
        else:
            selected_quote = quotes[num - 1]
    else:
        num = random.randint(1, n_quotes)
        selected_quote = quotes[num - 1]

    return format_quote(selected_quote, num, n_quotes)

########NEW FILE########
__FILENAME__ = religion
from util import hook, http


@hook.command('god')
@hook.command
def bible(inp):
    ".bible <passage> -- gets <passage> from the Bible (ESV)"

    base_url = ('http://www.esvapi.org/v2/rest/passageQuery?key=IP&'
                'output-format=plain-text&include-heading-horizontal-lines&'
                'include-headings=false&include-passage-horizontal-lines=false&'
                'include-passage-references=false&include-short-copyright=false&'
                'include-footnotes=false&line-length=0&'
                'include-heading-horizontal-lines=false')

    text = http.get(base_url, passage=inp)

    text = ' '.join(text.split())

    if len(text) > 400:
        text = text[:text.rfind(' ', 0, 400)] + '...'

    return text


@hook.command('allah')
@hook.command
def koran(inp):  # Koran look-up plugin by Ghetto Wizard
    ".koran <chapter.verse> -- gets <chapter.verse> from the Koran"

    url = 'http://quod.lib.umich.edu/cgi/k/koran/koran-idx?type=simple'

    results = http.get_html(url, q1=inp).xpath('//li')

    if not results:
        return 'No results for ' + inp

    return results[0].text_content()

########NEW FILE########
__FILENAME__ = remember
"""
remember.py: written by Scaevolus 2010
"""

import string
import re

from util import hook


def db_init(db):
    db.execute("create table if not exists memory(chan, word, data, nick,"
               " primary key(chan, word))")
    db.commit()


def get_memory(db, chan, word):
    row = db.execute("select data from memory where chan=? and word=lower(?)",
                     (chan, word)).fetchone()
    if row:
        return row[0]
    else:
        return None


@hook.command
@hook.command("r")
def remember(inp, nick='', chan='', db=None):
    ".remember <word> [+]<data> s/<before>/<after> -- maps word to data in the memory, or "
    " does a string replacement (not regex)"
    db_init(db)

    append = False
    replacement = False

    try:
        head, tail = inp.split(None, 1)
    except ValueError:
        return remember.__doc__

    data = get_memory(db, chan, head)
    if data is not None:
        _head, _tail = data.split(None, 1)
    else:
        _head, _tail = head, ''

    if tail[0] == '+':
        append = True
        # ignore + symbol
        new = tail[1:]
        # data is stored with the input so ignore it when re-adding it
        if len(tail) > 1 and tail[1] in (string.punctuation + ' '):
            tail = _tail + new
        else:
            tail = _tail + ' ' + new

    if len(tail) > 2 and tail[0] == 's' and tail[1] in string.punctuation:
        args = tail.split(tail[1])
        if len(args) == 4 and args[3] == '':
            args = args[:-1]
        if len(args) == 3:
            replacement = True
            _, src, dst = args
            new_data = _tail.replace(src, dst, 1)
            if new_data == _tail:
                return 'replacement left data unchanged'
            tail = new_data
        else:
            return 'invalid replacement syntax -- try s$foo$bar instead?'

    db.execute("replace into memory(chan, word, data, nick) values"
               " (?,lower(?),?,?)", (chan, head, head + ' ' + tail, nick))
    db.commit()

    if data:
        if append:
            return "appending %s to %s" % (new, data.replace('"', "''"))
        elif replacement:
            return "replacing '%s' with '%s' in %s" % (src, dst, _tail)
        else:
            return 'forgetting "%s", remembering this instead.' % \
                data.replace('"', "''")
    else:
        return 'done.'


@hook.command
@hook.command("f")
def forget(inp, chan='', db=None):
    ".forget <word> -- forgets the mapping that word had"

    db_init(db)
    data = get_memory(db, chan, inp)

    if not chan.startswith('#'):
        return "I won't forget anything in private."

    if data:
        db.execute("delete from memory where chan=? and word=lower(?)",
                   (chan, inp))
        db.commit()
        return 'forgot `%s`' % data.replace('`', "'")
    else:
        return "I don't know about that."


@hook.regex(r'^\? ?(.+)')
def question(inp, chan='', say=None, db=None):
    "?<word> -- shows what data is associated with word"
    db_init(db)

    data = get_memory(db, chan, inp.group(1).strip())
    if data:
        say(data)

########NEW FILE########
__FILENAME__ = rottentomatoes
from util import http, hook

api_root = 'http://api.rottentomatoes.com/api/public/v1.0/'
movie_search_url = api_root + 'movies.json'
movie_reviews_url = api_root + 'movies/%s/reviews.json'


@hook.api_key('rottentomatoes')
@hook.command('rt')
@hook.command
def rottentomatoes(inp, api_key=None):
    '.rt <title> -- gets ratings for <title> from Rotten Tomatoes'

    results = http.get_json(movie_search_url, q=inp, apikey=api_key)
    if results['total'] == 0:
        return 'no results'

    movie = results['movies'][0]
    title = movie['title']
    id = movie['id']
    critics_score = movie['ratings']['critics_score']
    audience_score = movie['ratings']['audience_score']
    url = movie['links']['alternate']

    if critics_score == -1:
        return

    reviews = http.get_json(movie_reviews_url %
                            id, apikey=api_key, review_type='all')
    review_count = reviews['total']

    fresh = critics_score * review_count / 100
    rotten = review_count - fresh

    return u"%s - critics: \x02%d%%\x02 (%d\u2191%d\u2193)" \
        " audience: \x02%d%%\x02 - %s" % (title, critics_score,
                                          fresh, rotten, audience_score, url)

########NEW FILE########
__FILENAME__ = seen
" seen.py: written by sklnd in about two beers July 2009"

import time

from util import hook, timesince


def db_init(db):
    "check to see that our db has the the seen table and return a connection."
    db.execute("create table if not exists seen(name, time, quote, chan, "
               "primary key(name, chan))")
    db.commit()


@hook.singlethread
@hook.event('PRIVMSG', ignorebots=False)
def seeninput(paraml, input=None, db=None, bot=None):
    db_init(db)
    db.execute("insert or replace into seen(name, time, quote, chan)"
               "values(?,?,?,?)", (input.nick.lower(), time.time(), input.msg,
                                   input.chan))
    db.commit()


@hook.command
def seen(inp, nick='', chan='', db=None, input=None):
    ".seen <nick> -- Tell when a nickname was last in active in irc"

    inp = inp.lower()

    if input.conn.nick.lower() == inp:
        # user is looking for us, being a smartass
        return "You need to get your eyes checked."

    if inp == nick.lower():
        return "Have you looked in a mirror lately?"

    db_init(db)

    last_seen = db.execute("select name, time, quote from seen where"
                           " name = ? and chan = ?", (inp, chan)).fetchone()

    if last_seen:
        reltime = timesince.timesince(last_seen[1])
        if last_seen[0] != inp.lower():  # for glob matching
            inp = last_seen[0]
        if last_seen[2][0:1] == "\x01":
            return '%s was last seen %s ago: *%s %s*' % \
                (inp, reltime, inp, last_seen[2][8:-1])
        else:
            return '%s was last seen %s ago saying: %s' % \
                (inp, reltime, last_seen[2])
    else:
        return "I've never seen %s" % inp

########NEW FILE########
__FILENAME__ = sieve
import re

from util import hook


@hook.sieve
def sieve_suite(bot, input, func, kind, args):
    if input.command == 'PRIVMSG' and \
       input.nick.lower()[-3:] == 'bot' and args.get('ignorebots', True):
            return None

    if kind == "command":
        if input.trigger in bot.config.get('disabled_commands', []):
            return None

        ignored = bot.config.get('ignored', [])
        if input.host in ignored or input.nick in ignored:
            return None

    fn = re.match(r'^plugins.(.+).py$', func._filename)
    disabled = bot.config.get('disabled_plugins', [])
    if fn and fn.group(1).lower() in disabled:
        return None

    acls = bot.config.get('acls', {})
    for acl in [acls.get(func.__name__), acls.get(input.chan), acls.get(input.conn.server)]:
        if acl is None:
            continue
        if 'deny-except' in acl:
            allowed_channels = map(unicode.lower, acl['deny-except'])
            if input.chan.lower() not in allowed_channels:
                return None
        if 'allow-except' in acl:
            denied_channels = map(unicode.lower, acl['allow-except'])
            if input.chan.lower() in denied_channels:
                return None
        if 'whitelist' in acl:
            if func.__name__ not in acl['whitelist']:
                return None
        if 'blacklist' in acl:
            if func.__name__ in acl['whitelist']:
                return None
        if 'blacklist-nicks' in acl:
            if input.nick.lower() in acl['blacklist-nicks']:
                return None

    admins = input.conn.conf.get('admins', [])
    input.admin = input.host in admins or input.nick in admins

    if args.get('adminonly', False):
        if not input.admin:
            return None

    return input

########NEW FILE########
__FILENAME__ = snopes
import re

from util import hook, http


search_url = "http://search.atomz.com/search/?sp_a=00062d45-sp00000000"


@hook.command
def snopes(inp):
    ".snopes <topic> -- searches snopes for an urban legend about <topic>"

    search_page = http.get_html(search_url, sp_q=inp, sp_c="1")
    result_urls = search_page.xpath("//a[@target='_self']/@href")

    if not result_urls:
        return "no matching pages found"

    snopes_page = http.get_html(result_urls[0])
    snopes_text = snopes_page.text_content()

    claim = re.search(r"Claim: .*", snopes_text).group(0).strip()
    status = re.search(r"Status: .*", snopes_text)

    if status is not None:
        status = status.group(0).strip()
    else:  # new-style statuses
        status = "Status: %s." % re.search(r"FALSE|TRUE|MIXTURE|UNDETERMINED",
                                           snopes_text).group(0).title()

    claim = re.sub(r"[\s\xa0]+", " ", claim)   # compress whitespace
    status = re.sub(r"[\s\xa0]+", " ", status)

    return "%s %s %s" % (claim, status, result_urls[0])

########NEW FILE########
__FILENAME__ = somethingawful
from util import hook, http


thread_re = r"(?i)forums\.somethingawful\.com/\S+threadid=(\d+)"
showthread = "http://forums.somethingawful.com/showthread.php?noseen=1"


def login(user, password):
    http.jar.clear_expired_cookies()
    if any(cookie.domain == 'forums.somethingawful.com' and
           cookie.name == 'bbuserid' for cookie in http.jar):
        if any(cookie.domain == 'forums.somethingawful.com' and
               cookie.name == 'bbpassword' for cookie in http.jar):
            return
        assert("malformed cookie jar")
    user = http.quote(user)
    password = http.quote(password)
    http.get("http://forums.somethingawful.com/account.php", cookies=True,
             post_data="action=login&username=%s&password=%s" % (user, password))


@hook.api_key('somethingawful')
@hook.regex(thread_re)
def forum_link(inp, api_key=None):
    if api_key is None or 'user' not in api_key or 'password' not in api_key:
        return

    login(api_key['user'], api_key['password'])

    thread = http.get_html(showthread, threadid=inp.group(1), perpage='1',
                           cookies=True)

    breadcrumbs = thread.xpath('//div[@class="breadcrumbs"]//a/text()')

    if not breadcrumbs:
        return

    thread_title = breadcrumbs[-1]
    forum_title = forum_abbrevs.get(breadcrumbs[-2], breadcrumbs[-2])

    poster = thread.xpath('//dt[contains(@class, author)]//text()')[0]

    # 1 post per page => n_pages = n_posts
    num_posts = thread.xpath('//a[@title="Last page"]/@href')

    if not num_posts:
        num_posts = 1
    else:
        num_posts = int(num_posts[0].rsplit('=', 1)[1])

    return '\x02%s\x02 > \x02%s\x02 by \x02%s\x02, %s post%s' % (
        forum_title, thread_title, poster, num_posts,
        's' if num_posts > 1 else '')


forum_abbrevs = {
    'Serious Hardware / Software Crap': 'SHSC',
    'The Cavern of COBOL': 'CoC',
    'General Bullshit': 'GBS',
    'Haus of Tech Support': 'HoTS'
}

########NEW FILE########
__FILENAME__ = stock
from util import hook, http


@hook.command
def stock(inp):
    '''.stock <symbol> -- gets stock information'''

    url = ('http://query.yahooapis.com/v1/public/yql?format=json&'
           'env=store%3A%2F%2Fdatatables.org%2Falltableswithkeys')

    parsed = http.get_json(url, q='select * from yahoo.finance.quote '
                           'where symbol in ("%s")' % inp)  # heh, SQLI

    quote = parsed['query']['results']['quote']

    # if we dont get a company name back, the symbol doesn't match a company
    if quote['Change'] is None:
        return "unknown ticker symbol %s" % inp

    change = float(quote['Change'])
    price = float(quote['LastTradePriceOnly'])

    if change < 0:
        quote['color'] = "5"
    else:
        quote['color'] = "3"

    quote['PercentChange'] = 100 * change / (price - change)

    ret = "%(Name)s - %(LastTradePriceOnly)s "                   \
          "\x03%(color)s%(Change)s (%(PercentChange).2f%%)\x03 "        \
          "Day Range: %(DaysRange)s " \
          "MCAP: %(MarketCapitalization)s" % quote

    return ret

########NEW FILE########
__FILENAME__ = suggest
import random
import re

from util import hook, http


@hook.command
def suggest(inp, inp_unstripped=None):
    ".suggest [#n] <phrase> -- gets a random/the nth suggested google search"

    if inp_unstripped is not None:
        inp = inp_unstripped
    m = re.match('^#(\d+) (.+)$', inp)
    num = 0
    if m:
        num, inp = m.groups()
        num = int(num)

    json = http.get_json('http://suggestqueries.google.com/complete/search', client='firefox', q=inp)
    suggestions = json[1]
    if not suggestions:
        return 'no suggestions found'

    if not num:
        num = random.randint(1, len(suggestions))
    if len(suggestions) + 1 <= num:
        return 'only got %d suggestions' % len(suggestions)
    out = suggestions[num - 1]
    return '#%d: %s' % (num, out)

########NEW FILE########
__FILENAME__ = tag
# -*- coding: utf-8 -*-

import math
import random
import re
import threading

from util import hook


def sanitize(s):
    return re.sub(r'[\x00-\x1f]', '', s)


@hook.command
def munge(inp, munge_count=0):
    reps = 0
    for n in xrange(len(inp)):
        rep = character_replacements.get(inp[n])
        if rep:
            inp = inp[:n] + rep.decode('utf8') + inp[n + 1:]
            reps += 1
            if reps == munge_count:
                break
    return inp


class PaginatingWinnower(object):

    def __init__(self):
        self.lock = threading.Lock()
        self.last_input = []
        self.recent = set()

    def winnow(self, inputs, limit=400, ordered=False):
        "remove random elements from the list until it's short enough"
        with self.lock:
            # try to remove elements that were *not* removed recently
            inputs_sorted = sorted(inputs)
            if inputs_sorted == self.last_input:
                same_input = True
            else:
                same_input = False
                self.last_input = inputs_sorted
                self.recent.clear()

            combiner = lambda l: u', '.join(l)
            suffix = ''

            while len(combiner(inputs)) >= limit:
                if same_input and any(inp in self.recent for inp in inputs):
                    if ordered:
                        for inp in self.recent:
                            if inp in inputs:
                                inputs.remove(inp)
                    else:
                        inputs.remove(
                            random.choice([inp for inp in inputs if inp in self.recent]))
                else:
                    if ordered:
                        inputs.pop()
                    else:
                        inputs.pop(random.randint(0, len(inputs) - 1))
                suffix = ' ...'

            self.recent.update(inputs)
            return combiner(inputs) + suffix

winnow = PaginatingWinnower().winnow


def add_tag(db, chan, nick, subject):
    match = db.execute('select * from tag where lower(nick)=lower(?) and'
                       ' chan=? and lower(subject)=lower(?)',
                       (nick, chan, subject)).fetchall()
    if match:
        return 'already tagged'

    db.execute('replace into tag(chan, subject, nick) values(?,?,?)',
               (chan, subject, nick))
    db.commit()

    return 'tag added'


def delete_tag(db, chan, nick, del_tag):
    count = db.execute('delete from tag where lower(nick)=lower(?) and'
                       ' chan=? and lower(subject)=lower(?)',
                       (nick, chan, del_tag)).rowcount
    db.commit()

    if count:
        return 'deleted'
    else:
        return 'tag not found'


def get_tag_counts_by_chan(db, chan):
    tags = db.execute("select subject, count(*) from tag where chan=?"
                      " group by lower(subject)"
                      " order by lower(subject)", (chan,)).fetchall()

    tags.sort(key=lambda x: x[1], reverse=True)
    if not tags:
        return 'no tags in %s' % chan
    return winnow(['%s (%d)' % row for row in tags], ordered=True)


def get_tags_by_nick(db, chan, nick):
    tags = db.execute("select subject from tag where lower(nick)=lower(?)"
                      " and chan=?"
                      " order by lower(subject)", (nick, chan)).fetchall()
    if tags:
        return 'tags for "%s": ' % munge(nick, 1) + winnow([
            tag[0] for tag in tags])
    else:
        return ''


def get_nicks_by_tagset(db, chan, tagset):
    nicks = None
    for tag in tagset.split('&'):
        tag = tag.strip()

        current_nicks = db.execute("select nick from tag where " +
                                   "lower(subject)=lower(?)"
                                   " and chan=?", (tag, chan)).fetchall()

        if not current_nicks:
            return "tag '%s' not found" % tag

        if nicks is None:
            nicks = set(current_nicks)
        else:
            nicks.intersection_update(current_nicks)

    nicks = [munge(x[0], 1) for x in sorted(nicks)]
    if not nicks:
        return 'no nicks found with tags "%s"' % tagset
    return 'nicks tagged "%s": ' % tagset + winnow(nicks)


@hook.command
def tag(inp, chan='', db=None):
    '.tag <nick> <tag> -- marks <nick> as <tag> {related: .untag, .tags, .tagged, .is}'

    db.execute('create table if not exists tag(chan, subject, nick)')

    add = re.match(r'(\S+) (.+)', inp)

    if add:
        nick, subject = add.groups()
        if nick.lower() == 'list':
            return 'tag syntax has changed. try .tags or .tagged instead'
        elif nick.lower() == 'del':
            return 'tag syntax has changed. try ".untag %s" instead' % subject
        return add_tag(db, chan, sanitize(nick), sanitize(subject))
    else:
        tags = get_tags_by_nick(db, chan, inp)
        if tags:
            return tags
        else:
            return tag.__doc__


@hook.command
def untag(inp, chan='', db=None):
    '.untag <nick> <tag> -- unmarks <nick> as <tag> {related: .tag, .tags, .tagged, .is}'

    delete = re.match(r'(\S+) (.+)$', inp)

    if delete:
        nick, del_tag = delete.groups()
        return delete_tag(db, chan, nick, del_tag)
    else:
        return untag.__doc__


@hook.command
def tags(inp, chan='', db=None):
    '.tags <nick>/list -- get list of tags for <nick>, or a list of tags {related: .tag, .untag, .tagged, .is}'
    if inp == 'list':
        return get_tag_counts_by_chan(db, chan)

    tags = get_tags_by_nick(db, chan, inp)
    if tags:
        return tags
    else:
        return get_nicks_by_tagset(db, chan, inp)


@hook.command
def tagged(inp, chan='', db=None):
    '.tagged <tag> [& tag...] -- get nicks marked as <tag> (separate multiple tags with &) {related: .tag, .untag, .tags, .is}'

    return get_nicks_by_tagset(db, chan, inp)

@hook.command('is')
def is_tagged(inp, chan='', db=None):
    '.is <nick> <tag> -- checks if <nick> has been marked as <tag> {related: .tag, .untag, .tags, .tagged}'

    args = re.match(r'(\S+) (.+)$', inp)

    if args:
        nick, tag = args.groups()
        found = db.execute("select 1 from tag"
                           " where lower(nick)=lower(?)"
                           "   and lower(subject)=lower(?)"
                           "   and chan=?", (nick, tag, chan)).fetchone()
        if found:
            return 'yes'
        else:
            return 'no'
    else:
        return is_tagged.__doc__

def distance(lat1, lon1, lat2, lon2):
    deg_to_rad = math.pi / 180
    lat1 *= deg_to_rad
    lat2 *= deg_to_rad
    lon1 *= deg_to_rad
    lon2 *= deg_to_rad

    R = 6371  # km
    d = math.acos(math.sin(lat1) * math.sin(lat2) +
                  math.cos(lat1) * math.cos(lat2) *
                  math.cos(lon2 - lon1)) * R
    return d


@hook.command(autohelp=False)
def near(inp, nick='', chan='', db=None):
    try:
        loc = db.execute("select lat, lon from location where chan=? and nick=lower(?)",
                (chan, nick)).fetchone()
    except db.OperationError:
        loc = None

    if loc is None:
        return 'use .weather <loc> first to set your location'

    lat, lon = loc

    db.create_function('distance', 4, distance)
    nearby = db.execute("select nick, distance(lat, lon, ?, ?) as dist from location where chan=?"
                        " and nick != lower(?) order by dist limit 20", (lat, lon, chan, nick)).fetchall()

    in_miles = 'mi' in inp.lower()

    out = '(km) '
    factor = 1.0
    if in_miles:
        out = '(mi) '
        factor = 0.621

    while nearby and len(out) < 200:
        nick, dist = nearby.pop(0)
        out += '%s:%.0f ' % (munge(nick, 1), dist * factor)

    return out


character_replacements = {
    'a': 'ä',
#    'b': 'Б',
    'c': 'ċ',
    'd': 'đ',
    'e': 'ë',
    'f': 'ƒ',
    'g': 'ġ',
    'h': 'ħ',
    'i': 'í',
    'j': 'ĵ',
    'k': 'ķ',
    'l': 'ĺ',
#    'm': 'ṁ',
    'n': 'ñ',
    'o': 'ö',
    'p': 'ρ',
#    'q': 'ʠ',
    'r': 'ŗ',
    's': 'š',
    't': 'ţ',
    'u': 'ü',
#    'v': '',
    'w': 'ω',
    'x': 'χ',
    'y': 'ÿ',
    'z': 'ź',
    'A': 'Å',
    'B': 'Β',
    'C': 'Ç',
    'D': 'Ď',
    'E': 'Ē',
#    'F': 'Ḟ',
    'G': 'Ġ',
    'H': 'Ħ',
    'I': 'Í',
    'J': 'Ĵ',
    'K': 'Ķ',
    'L': 'Ĺ',
    'M': 'Μ',
    'N': 'Ν',
    'O': 'Ö',
    'P': 'Р',
#    'Q': 'Ｑ',
    'R': 'Ŗ',
    'S': 'Š',
    'T': 'Ţ',
    'U': 'Ů',
#    'V': 'Ṿ',
    'W': 'Ŵ',
    'X': 'Χ',
    'Y': 'Ỳ',
    'Z': 'Ż'}

########NEW FILE########
__FILENAME__ = tell
" tell.py: written by sklnd in July 2009"
"       2010.01.25 - modified by Scaevolus"

import time

from util import hook, timesince


def db_init(db):
    "check to see that our db has the tell table and return a dbection."
    db.execute("create table if not exists tell"
               "(user_to, user_from, message, chan, time,"
               "primary key(user_to, message))")
    db.commit()

    return db


def get_tells(db, user_to):
    return db.execute("select user_from, message, time, chan from tell where"
                      " user_to=lower(?) order by time",
                      (user_to.lower(),)).fetchall()


@hook.singlethread
@hook.event('PRIVMSG')
def tellinput(paraml, input=None, db=None):
    if 'showtells' in input.msg.lower():
        return

    db_init(db)

    tells = get_tells(db, input.nick)

    if tells:
        user_from, message, time, chan = tells[0]
        reltime = timesince.timesince(time)

        reply = "%s said %s ago in %s: %s" % (user_from, reltime, chan,
                                              message)
        if len(tells) > 1:
            reply += " (+%d more, .showtells to view)" % (len(tells) - 1)

        db.execute("delete from tell where user_to=lower(?) and message=?",
                   (input.nick, message))
        db.commit()
        input.pm(reply)


@hook.command(autohelp=False)
def showtells(inp, nick='', chan='', notice=None, db=None):
    ".showtells -- view all pending tell messages (sent in PM)."

    db_init(db)

    tells = get_tells(db, nick)

    if not tells:
        notice("You have no pending tells.")
        return

    for tell in tells:
        user_from, message, time, chan = tell
        past = timesince.timesince(time)
        notice("%s said %s ago in %s: %s" % (user_from, past, chan, message))

    db.execute("delete from tell where user_to=lower(?)",
               (nick,))
    db.commit()


@hook.command
def tell(inp, nick='', chan='', db=None):
    ".tell <nick> <message> -- relay <message> to <nick> when <nick> is around"

    query = inp.split(' ', 1)

    if len(query) != 2:
        return tell.__doc__

    user_to = query[0].lower()
    message = query[1].strip()
    user_from = nick

    if chan.lower() == user_from.lower():
        chan = 'a pm'

    if user_to == user_from.lower():
        return "No."

    db_init(db)

    if db.execute("select count() from tell where user_to=?",
                  (user_to,)).fetchone()[0] >= 5:
        return "That person has too many things queued."

    try:
        db.execute("insert into tell(user_to, user_from, message, chan,"
                   "time) values(?,?,?,?,?)", (user_to, user_from, message,
                                               chan, time.time()))
        db.commit()
    except db.IntegrityError:
        return "Message has already been queued."

    return "I'll pass that along."

########NEW FILE########
__FILENAME__ = tf
# tf.py: written by ipsum
#
# This skybot plugin retreives the number of items
# a given user has waiting from idling in Team Fortress 2.

from util import hook, http


@hook.command('hats')
@hook.command
def tf(inp):
    """.tf/.hats <SteamID> -- Shows items waiting to be received in TF2."""

    if inp.isdigit():
        link = 'profiles'
    else:
        link = 'id'

    url = 'http://steamcommunity.com/%s/%s/tfitems?json=1' % \
        (link, http.quote(inp.encode('utf8'), safe=''))

    try:
        inv = http.get_json(url)
    except ValueError:
        return '%s is not a valid profile' % inp

    dropped, dhats, hats = 0, 0, 0
    for item, data in inv.iteritems():
        ind = int(data['defindex'])
        if data['inventory'] == 0:
            if 47 <= ind <= 55 or 94 <= ind <= 126 or 134 <= ind <= 152:
                dhats += 1
            else:
                dropped += 1
        else:
            if 47 <= ind <= 55 or 94 <= ind <= 126 or 134 <= ind <= 152:
                hats += 1

    return '%s has had %s items and %s hats drop (%s total hats)' %  \
        (inp, dropped, dhats, dhats + hats)

########NEW FILE########
__FILENAME__ = tinyurl
from util import hook, http


@hook.regex(r'(?i)http://(?:www\.)?tinyurl.com/([A-Za-z0-9\-]+)')
def tinyurl(match):
    try:
        return http.open(match.group()).url.strip()
    except http.URLError, e:
        pass

########NEW FILE########
__FILENAME__ = translate
'''
A Google API key is required and retrieved from the bot config file.
Since December 1, 2011, the Google Translate API is a paid service only.
'''

import htmlentitydefs
import re

from util import hook, http

api_key = ""

########### from http://effbot.org/zone/re-sub.htm#unescape-html #############


def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is

    return re.sub("&#?\w+;", fixup, text)

##############################################################################


def goog_trans(text, slang, tlang):
    url = 'https://www.googleapis.com/language/translate/v2'
    parsed = http.get_json(
        url, key=api_key, q=text, source=slang, target=tlang)
    if not 200 <= parsed['responseStatus'] < 300:
        raise IOError('error with the translation server: %d: %s' % (
            parsed['responseStatus'], parsed['responseDetails']))
    if not slang:
        return unescape('(%(detectedSourceLanguage)s) %(translatedText)s' %
                        (parsed['responseData']['data']['translations'][0]))
    return unescape('%(translatedText)s' % parsed['responseData']['data']['translations'][0])


def match_language(fragment):
    fragment = fragment.lower()
    for short, _ in lang_pairs:
        if fragment in short.lower().split():
            return short.split()[0]

    for short, full in lang_pairs:
        if fragment in full.lower():
            return short.split()[0]

    return None


@hook.command
def translate(inp, bot=None):
    '.translate [source language [target language]] <sentence> -- translates' \
        ' <sentence> from source language (default autodetect) to target' \
        ' language (default English) using Google Translate'

    if not hasapikey(bot):
        return None

    args = inp.split(' ', 2)

    try:
        if len(args) >= 2:
            sl = match_language(args[0])
            if not sl:
                return goog_trans(inp, '', 'en')
            if len(args) == 2:
                return goog_trans(args[1], sl, 'en')
            if len(args) >= 3:
                tl = match_language(args[1])
                if not tl:
                    if sl == 'en':
                        return 'unable to determine desired target language'
                    return goog_trans(args[1] + ' ' + args[2], sl, 'en')
                return goog_trans(args[2], sl, tl)
        return goog_trans(inp, '', 'en')
    except IOError, e:
        return e


languages = 'ja fr de ko ru zh'.split()
language_pairs = zip(languages[:-1], languages[1:])


def babel_gen(inp):
    for language in languages:
        inp = inp.encode('utf8')
        trans = goog_trans(inp, 'en', language).encode('utf8')
        inp = goog_trans(trans, language, 'en')
        yield language, trans, inp


@hook.command
def babel(inp, bot=None):
    ".babel <sentence> -- translates <sentence> through multiple languages"

    if not hasapikey(bot):
        return None

    try:
        return list(babel_gen(inp))[-1][2]
    except IOError, e:
        return e


@hook.command
def babelext(inp, bot=None):
    ".babelext <sentence> -- like .babel, but with more detailed output"

    if not hasapikey(bot):
        return None

    try:
        babels = list(babel_gen(inp))
    except IOError, e:
        return e

    out = u''
    for lang, trans, text in babels:
        out += '%s:"%s", ' % (lang, text.decode('utf8'))

    out += 'en:"' + babels[-1][2].decode('utf8') + '"'

    if len(out) > 300:
        out = out[:150] + ' ... ' + out[-150:]

    return out


def hasapikey(bot):
    api_key = bot.config.get("api_keys", {}).get("googletranslate", None)
    return api_key

lang_pairs = [
    ("no", "Norwegian"),
    ("it", "Italian"),
    ("ht", "Haitian Creole"),
    ("af", "Afrikaans"),
    ("sq", "Albanian"),
    ("ar", "Arabic"),
    ("hy", "Armenian"),
    ("az", "Azerbaijani"),
    ("eu", "Basque"),
    ("be", "Belarusian"),
    ("bg", "Bulgarian"),
    ("ca", "Catalan"),
    ("zh-CN zh", "Chinese"),
    ("hr", "Croatian"),
    ("cs", "Czech"),
    ("da", "Danish"),
    ("nl", "Dutch"),
    ("en", "English"),
    ("et", "Estonian"),
    ("tl", "Filipino"),
    ("fi", "Finnish"),
    ("fr", "French"),
    ("gl", "Galician"),
    ("ka", "Georgian"),
    ("de", "German"),
    ("el", "Greek"),
    ("ht", "Haitian Creole"),
    ("iw", "Hebrew"),
    ("hi", "Hindi"),
    ("hu", "Hungarian"),
    ("is", "Icelandic"),
    ("id", "Indonesian"),
    ("ga", "Irish"),
    ("it", "Italian"),
    ("ja jp jpn", "Japanese"),
    ("ko", "Korean"),
    ("lv", "Latvian"),
    ("lt", "Lithuanian"),
    ("mk", "Macedonian"),
    ("ms", "Malay"),
    ("mt", "Maltese"),
    ("no", "Norwegian"),
    ("fa", "Persian"),
    ("pl", "Polish"),
    ("pt", "Portuguese"),
    ("ro", "Romanian"),
    ("ru", "Russian"),
    ("sr", "Serbian"),
    ("sk", "Slovak"),
    ("sl", "Slovenian"),
    ("es", "Spanish"),
    ("sw", "Swahili"),
    ("sv", "Swedish"),
    ("th", "Thai"),
    ("tr", "Turkish"),
    ("uk", "Ukrainian"),
    ("ur", "Urdu"),
    ("vi", "Vietnamese"),
    ("cy", "Welsh"),
    ("yi", "Yiddish")
]

########NEW FILE########
__FILENAME__ = tvdb
"""
TV information, written by Lurchington 2010
modified by rmmh 2010, 2013
"""

import datetime

from util import hook, http, timesince


base_url = "http://thetvdb.com/api/"
api_key = "469B73127CA0C411"


def get_episodes_for_series(seriesname):
    res = {"error": None, "ended": False, "episodes": None, "name": None}
    # http://thetvdb.com/wiki/index.php/API:GetSeries
    try:
        query = http.get_xml(base_url + 'GetSeries.php', seriesname=seriesname)
    except http.URLError:
        res["error"] = "error contacting thetvdb.com"
        return res

    series_id = query.xpath('//seriesid/text()')

    if not series_id:
        res["error"] = "unknown tv series (using www.thetvdb.com)"
        return res

    series_id = series_id[0]

    try:
        series = http.get_xml(base_url + '%s/series/%s/all/en.xml' %
                              (api_key, series_id))
    except http.URLError:
        res["error"] = "error contacting thetvdb.com"
        return res

    series_name = series.xpath('//SeriesName/text()')[0]

    if series.xpath('//Status/text()')[0] == 'Ended':
        res["ended"] = True

    res["episodes"] = series.xpath('//Episode')
    res["name"] = series_name
    return res


def get_episode_info(episode):
    episode_air_date = episode.findtext("FirstAired")

    try:
        airdate = datetime.date(*map(int, episode_air_date.split('-')))
    except (ValueError, TypeError):
        return None

    episode_num = "S%02dE%02d" % (int(episode.findtext("SeasonNumber")),
                                  int(episode.findtext("EpisodeNumber")))

    episode_name = episode.findtext("EpisodeName")
    # in the event of an unannounced episode title, users either leave the
    # field out (None) or fill it with TBA
    if episode_name == "TBA":
        episode_name = None

    episode_desc = '%s' % episode_num
    if episode_name:
        episode_desc += ' - %s' % episode_name
    return (episode_air_date, airdate, episode_desc)


@hook.command
@hook.command('tv')
def tv_next(inp):
    ".tv_next <series> -- get the next episode of <series>"
    episodes = get_episodes_for_series(inp)

    if episodes["error"]:
        return episodes["error"]

    series_name = episodes["name"]
    ended = episodes["ended"]
    episodes = episodes["episodes"]

    if ended:
        return "%s has ended." % series_name

    next_eps = []
    today = datetime.date.today()

    for episode in reversed(episodes):
        ep_info = get_episode_info(episode)

        if ep_info is None:
            continue

        (episode_air_date, airdate, episode_desc) = ep_info

        if airdate > today:
            next_eps = ['%s (%s) (%s)' % (episode_air_date, timesince.timeuntil(
                datetime.datetime.strptime(episode_air_date, "%Y-%m-%d")), episode_desc)]
        elif airdate == today:
            next_eps = ['Today (%s)' % episode_desc] + next_eps
        else:
            # we're iterating in reverse order with newest episodes last
            # so, as soon as we're past today, break out of loop
            break

    if not next_eps:
        return "there are no new episodes scheduled for %s" % series_name

    if len(next_eps) == 1:
        return "the next episode of %s airs %s" % (series_name, next_eps[0])
    else:
        next_eps = ', '.join(next_eps)
        return "the next episodes of %s: %s" % (series_name, next_eps)


@hook.command
@hook.command('tv_prev')
def tv_last(inp):
    ".tv_last <series> -- gets the most recently aired episode of <series>"
    episodes = get_episodes_for_series(inp)

    if episodes["error"]:
        return episodes["error"]

    series_name = episodes["name"]
    ended = episodes["ended"]
    episodes = episodes["episodes"]

    prev_ep = None
    today = datetime.date.today()

    for episode in reversed(episodes):
        ep_info = get_episode_info(episode)

        if ep_info is None:
            continue

        (episode_air_date, airdate, episode_desc) = ep_info

        if airdate < today:
            # iterating in reverse order, so the first episode encountered
            # before today was the most recently aired
            prev_ep = '%s (%s)' % (episode_air_date, episode_desc)
            break

    if not prev_ep:
        return "there are no previously aired episodes for %s" % series_name
    if ended:
        return '%s ended. The last episode aired %s' % (series_name, prev_ep)
    return "the last episode of %s aired %s" % (series_name, prev_ep)

########NEW FILE########
__FILENAME__ = twitter
import random
import re
from time import strptime, strftime
from urllib import quote

from util import hook, http


@hook.api_key('twitter')
@hook.command
def twitter(inp, api_key=None):
    ".twitter <user>/<user> <n>/<id>/#<search>/#<search> <n> -- " \
        "get <user>'s last/<n>th tweet/get tweet <id>/do <search>/get <n>th <search> result"

    if not isinstance(api_key, dict) or any(key not in api_key for key in
                                            ('consumer', 'consumer_secret', 'access', 'access_secret')):
        return "error: api keys not set"

    getting_id = False
    doing_search = False
    index_specified = False

    if re.match(r'^\d+$', inp):
        getting_id = True
        request_url = "https://api.twitter.com/1.1/statuses/show.json?id=%s" % inp
    else:
        try:
            inp, index = re.split('\s+', inp, 1)
            index = int(index)
            index_specified = True
        except ValueError:
            index = 0
        if index < 0:
            index = 0
        if index >= 20:
            return 'error: only supports up to the 20th tweet'

        if re.match(r'^#', inp):
            doing_search = True
            request_url = "https://api.twitter.com/1.1/search/tweets.json?q=%s" % quote(inp)
        else:
            request_url = "https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name=%s" % inp

    try:
        tweet = http.get_json(request_url, oauth=True, oauth_keys=api_key)
    except http.HTTPError, e:
        errors = {400: 'bad request (ratelimited?)',
                  401: 'unauthorized',
                  403: 'forbidden',
                  404: 'invalid user/id',
                  500: 'twitter is broken',
                  502: 'twitter is down ("getting upgraded")',
                  503: 'twitter is overloaded (lol, RoR)',
                  410: 'twitter shut off api v1.'}
        if e.code == 404:
            return 'error: invalid ' + ['username', 'tweet id'][getting_id]
        if e.code in errors:
            return 'error: ' + errors[e.code]
        return 'error: unknown %s' % e.code

    if doing_search:
        try:
            tweet = tweet["statuses"]
            if not index_specified:
                index = random.randint(0, len(tweet) - 1)
        except KeyError:
            return 'error: no results'

    if not getting_id:
        try:
            tweet = tweet[index]
        except IndexError:
            return 'error: not that many tweets found'

    text = http.unescape(tweet["text"]).replace('\n', ' ')
    screen_name = tweet["user"]["screen_name"]
    time = tweet["created_at"]

    time = strftime('%Y-%m-%d %H:%M:%S',
                    strptime(time, '%a %b %d %H:%M:%S +0000 %Y'))

    return "%s \x02%s\x02: %s" % (time, screen_name, text)


@hook.api_key('twitter')
@hook.regex(r'https?://twitter.com/(#!/)?([_0-9a-zA-Z]+)/status/(\d+)')
def show_tweet(match, api_key=None):
    return twitter(match.group(3), api_key)

########NEW FILE########
__FILENAME__ = urlhistory
import math
import time

from util import hook, urlnorm, timesince


expiration_period = 60 * 60 * 24  # 1 day

ignored_urls = [urlnorm.normalize("http://google.com")]


def db_init(db):
    db.execute("create table if not exists urlhistory"
               "(chan, url, nick, time)")
    db.commit()


def insert_history(db, chan, url, nick):
    db.execute("insert into urlhistory(chan, url, nick, time) "
               "values(?,?,?,?)", (chan, url, nick, time.time()))
    db.commit()


def get_history(db, chan, url):
    db.execute("delete from urlhistory where time < ?",
               (time.time() - expiration_period,))
    return db.execute("select nick, time from urlhistory where "
                      "chan=? and url=? order by time desc", (chan, url)).fetchall()


def nicklist(nicks):
    nicks = sorted(dict(nicks), key=unicode.lower)
    if len(nicks) <= 2:
        return ' and '.join(nicks)
    else:
        return ', and '.join((', '.join(nicks[:-1]), nicks[-1]))


def format_reply(history):
    if not history:
        return

    last_nick, recent_time = history[0]
    last_time = timesince.timesince(recent_time)

    if len(history) == 1:
        return "%s linked that %s ago." % (last_nick, last_time)

    hour_span = math.ceil((time.time() - history[-1][1]) / 3600)
    hour_span = '%.0f hours' % hour_span if hour_span > 1 else 'hour'

    hlen = len(history)
    ordinal = ["once", "twice", "%d times" % hlen][min(hlen, 3) - 1]

    if len(dict(history)) == 1:
        last = "last linked %s ago" % last_time
    else:
        last = "last linked by %s %s ago" % (last_nick, last_time)

    return "that url has been posted %s in the past %s by %s (%s)." % (ordinal,
                                                                       hour_span, nicklist(history), last)


@hook.regex(r'([a-zA-Z]+://|www\.)[^ ]+')
def urlinput(match, nick='', chan='', db=None, bot=None):
    db_init(db)
    url = urlnorm.normalize(match.group().encode('utf-8'))
    if url not in ignored_urls:
        url = url.decode('utf-8')
        history = get_history(db, chan, url)
        insert_history(db, chan, url, nick)

        inp = match.string.lower()

        for name in dict(history):
            if name.lower() in inp:  # person was probably quoting a line
                return               # that had a link. don't remind them.

        if nick not in dict(history):
            return format_reply(history)

########NEW FILE########
__FILENAME__ = hook
import inspect
import re


def _hook_add(func, add, name=''):
    if not hasattr(func, '_hook'):
        func._hook = []
    func._hook.append(add)

    if not hasattr(func, '_filename'):
        func._filename = func.func_code.co_filename

    if not hasattr(func, '_args'):
        argspec = inspect.getargspec(func)
        if name:
            n_args = len(argspec.args)
            if argspec.defaults:
                n_args -= len(argspec.defaults)
            if argspec.keywords:
                n_args -= 1
            if argspec.varargs:
                n_args -= 1
            if n_args != 1:
                err = '%ss must take 1 non-keyword argument (%s)' % (name,
                                                                     func.__name__)
                raise ValueError(err)

        args = []
        if argspec.defaults:
            end = bool(argspec.keywords) + bool(argspec.varargs)
            args.extend(argspec.args[-len(argspec.defaults):
                        end if end else None])
        if argspec.keywords:
            args.append(0)  # means kwargs present
        func._args = args

    if not hasattr(func, '_thread'):  # does function run in its own thread?
        func._thread = False


def sieve(func):
    if func.func_code.co_argcount != 5:
        raise ValueError(
            'sieves must take 5 arguments: (bot, input, func, type, args)')
    _hook_add(func, ['sieve', (func,)])
    return func


def command(arg=None, **kwargs):
    args = {}

    def command_wrapper(func):
        args.setdefault('name', func.func_name)
        _hook_add(func, ['command', (func, args)], 'command')
        return func

    if kwargs or not inspect.isfunction(arg):
        if arg is not None:
            args['name'] = arg
        args.update(kwargs)
        return command_wrapper
    else:
        return command_wrapper(arg)


def event(arg=None, **kwargs):
    args = kwargs

    def event_wrapper(func):
        args['name'] = func.func_name
        args.setdefault('events', ['*'])
        _hook_add(func, ['event', (func, args)], 'event')
        return func

    if inspect.isfunction(arg):
        return event_wrapper(arg, kwargs)
    else:
        if arg is not None:
            args['events'] = arg.split()
        return event_wrapper


def singlethread(func):
    func._thread = True
    return func


def api_key(key):
    def annotate(func):
        func._apikey = key
        return func
    return annotate


def regex(regex, flags=0, **kwargs):
    args = kwargs

    def regex_wrapper(func):
        args['name'] = func.func_name
        args['regex'] = regex
        args['re'] = re.compile(regex, flags)
        _hook_add(func, ['regex', (func, args)], 'regex')
        return func

    if inspect.isfunction(regex):
        raise ValueError("regex decorators require a regex to match against")
    else:
        return regex_wrapper

########NEW FILE########
__FILENAME__ = http
# convenience wrapper for urllib2 & friends
import binascii
import cookielib
import hmac
import json
import random
import string
import time
import urllib
import urllib2
import urlparse

from hashlib import sha1
from urllib import quote, unquote, quote_plus as _quote_plus
from urllib2 import HTTPError, URLError

from lxml import etree, html


ua_skybot = 'Skybot/1.0 http://github.com/rmmh/skybot'

ua_firefox = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.6) ' \
             'Gecko/20070725 Firefox/2.0.0.6'
ua_internetexplorer = 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'

jar = cookielib.CookieJar()


def get(*args, **kwargs):
    return open(*args, **kwargs).read()


def get_html(*args, **kwargs):
    return html.fromstring(get(*args, **kwargs))


def get_xml(*args, **kwargs):
    return etree.fromstring(get(*args, **kwargs))


def get_json(*args, **kwargs):
    return json.loads(get(*args, **kwargs))


def open(url, query_params=None, post_data=None,
         get_method=None, cookies=False, oauth=False, oauth_keys=None, headers=None, **kwargs):
    if query_params is None:
        query_params = {}

    query_params.update(kwargs)

    url = prepare_url(url, query_params)

    request = urllib2.Request(url, post_data)

    if get_method is not None:
        request.get_method = lambda: get_method

    if headers is not None:
        for header_key, header_value in headers.iteritems():
            request.add_header(header_key, header_value)

    if 'User-Agent' not in request.headers:
        request.add_header('User-Agent', ua_skybot)

    if oauth:
        nonce = oauth_nonce()
        timestamp = oauth_timestamp()
        api_url, req_data = string.split(url, "?")
        unsigned_request = oauth_unsigned_request(
            nonce, timestamp, req_data, oauth_keys['consumer'], oauth_keys['access'])

        signature = oauth_sign_request("GET", api_url, req_data, unsigned_request, oauth_keys[
            'consumer_secret'], oauth_keys['access_secret'])

        header = oauth_build_header(
            nonce, signature, timestamp, oauth_keys['consumer'], oauth_keys['access'])
        request.add_header('Authorization', header)

    if cookies:
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(jar))
    else:
        opener = urllib2.build_opener()
    return opener.open(request)


def prepare_url(url, queries):
    if queries:
        scheme, netloc, path, query, fragment = urlparse.urlsplit(url)

        query = dict(urlparse.parse_qsl(query))
        query.update(queries)
        query = urllib.urlencode(dict((to_utf8(key), to_utf8(value))
                                      for key, value in query.iteritems()))

        url = urlparse.urlunsplit((scheme, netloc, path, query, fragment))

    return url


def to_utf8(s):
    if isinstance(s, unicode):
        return s.encode('utf8', 'ignore')
    else:
        return str(s)


def quote_plus(s):
    return _quote_plus(to_utf8(s))


def oauth_nonce():
    return ''.join([str(random.randint(0, 9)) for i in range(8)])


def oauth_timestamp():
    return str(int(time.time()))


def oauth_unsigned_request(nonce, timestamp, req, consumer, token):
    d = {'oauth_consumer_key': consumer,
         'oauth_nonce': nonce,
         'oauth_signature_method': 'HMAC-SHA1',
         'oauth_timestamp': timestamp,
         'oauth_token': token,
         'oauth_version': '1.0'}

    k, v = string.split(req, "=")
    d[k] = v

    unsigned_req = ''

    for x in sorted(d, key=lambda key: key):
        unsigned_req += x + "=" + d[x] + "&"

    unsigned_req = quote(unsigned_req[:-1])

    return unsigned_req


def oauth_build_header(nonce, signature, timestamp, consumer, token):
    d = {'oauth_consumer_key': consumer,
         'oauth_nonce': nonce,
         'oauth_signature': signature,
         'oauth_signature_method': 'HMAC-SHA1',
         'oauth_timestamp': timestamp,
         'oauth_token': token,
         'oauth_version': '1.0'}

    header = 'OAuth '

    for x in sorted(d, key=lambda key: key):
        header += x + '="' + d[x] + '", '

    return header[:-1]


def oauth_sign_request(method, url, params, unsigned_request, consumer_secret, token_secret):
    key = consumer_secret + "&" + token_secret

    base = method + "&" + quote(url, '') + "&" + unsigned_request

    hash = hmac.new(key, base, sha1)

    signature = quote(binascii.b2a_base64(hash.digest())[:-1])

    return signature


def unescape(s):
    if not s.strip():
        return s
    return html.fromstring(s).text_content()

########NEW FILE########
__FILENAME__ = timesince
# Copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  1. Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
#  3. Neither the name of Django nor the names of its contributors may be used
#     to endorse or promote products derived from this software without
#     specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"AND
#ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED.IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
#ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import datetime


def timesince(d, now=None):
    """
    Takes two datetime objects and returns the time between d and now
    as a nicely formatted string, e.g. "10 minutes".  If d occurs after now,
    then "0 minutes" is returned.

    Units used are years, months, weeks, days, hours, and minutes.
    Seconds and microseconds are ignored.  Up to two adjacent units will be
    displayed.  For example, "2 weeks, 3 days" and "1 year, 3 months" are
    possible outputs, but "2 weeks, 3 hours" and "1 year, 5 days" are not.

    Adapted from http://blog.natbat.co.uk/archive/2003/Jun/14/time_since
    """
    chunks = (
      (60 * 60 * 24 * 365, ('year', 'years')),
      (60 * 60 * 24 * 30, ('month', 'months')),
      (60 * 60 * 24 * 7, ('week', 'weeks')),
      (60 * 60 * 24, ('day', 'days')),
      (60 * 60, ('hour', 'hours')),
      (60, ('minute', 'minutes'))
    )

    # Convert int or float (unix epoch) to datetime.datetime for comparison
    if isinstance(d, int) or isinstance(d, float):
        d = datetime.datetime.fromtimestamp(d)

    # Convert datetime.date to datetime.datetime for comparison.
    if not isinstance(d, datetime.datetime):
        d = datetime.datetime(d.year, d.month, d.day)
    if now and not isinstance(now, datetime.datetime):
        now = datetime.datetime(now.year, now.month, now.day)

    if not now:
        now = datetime.datetime.now()

    # ignore microsecond part of 'd' since we removed it from 'now'
    delta = now - (d - datetime.timedelta(0, 0, d.microsecond))
    since = delta.days * 24 * 60 * 60 + delta.seconds
    if since <= 0:
        # d is in the future compared to now, stop processing.
        return u'0 ' + 'minutes'
    for i, (seconds, name) in enumerate(chunks):
        count = since // seconds
        if count != 0:
            break

    if count == 1:
        s = '%(number)d %(type)s' % {'number': count, 'type': name[0]}
    else:
        s = '%(number)d %(type)s' % {'number': count, 'type': name[1]}

    if i + 1 < len(chunks):
        # Now get the second item
        seconds2, name2 = chunks[i + 1]
        count2 = (since - (seconds * count)) // seconds2
        if count2 != 0:
            if count2 == 1:
                s += ', %d %s' % (count2, name2[0])
            else:
                s += ', %d %s' % (count2, name2[1])
    return s


def timeuntil(d, now=None):
    """
    Like timesince, but returns a string measuring the time until
    the given time.
    """
    if not now:
        now = datetime.datetime.now()
    return timesince(now, d)

########NEW FILE########
__FILENAME__ = urlnorm
"""
URI Normalization function:
 * Always provide the URI scheme in lowercase characters.
 * Always provide the host, if any, in lowercase characters.
 * Only perform percent-encoding where it is essential.
 * Always use uppercase A-through-F characters when percent-encoding.
 * Prevent dot-segments appearing in non-relative URI paths.
 * For schemes that define a default authority, use an empty authority if the
   default is desired.
 * For schemes that define an empty path to be equivalent to a path of "/",
   use "/".
 * For schemes that define a port, use an empty port if the default is desired
 * All portions of the URI must be utf-8 encoded NFC from Unicode strings

implements:
  http://gbiv.com/protocols/uri/rev-2002/rfc2396bis.html#canonical-form
  http://www.intertwingly.net/wiki/pie/PaceCanonicalIds

inspired by:
  Tony J. Ibbs,    http://starship.python.net/crew/tibs/python/tji_url.py
  Mark Nottingham, http://www.mnot.net/python/urlnorm.py
"""

__license__ = "Python"

import re
import unicodedata
import urlparse
from urllib import quote, unquote

default_port = {
    'http': 80,
}


class Normalizer(object):
    def __init__(self, regex, normalize_func):
        self.regex = regex
        self.normalize = normalize_func

normalizers = ( Normalizer( re.compile(r'(?:https?://)?(?:[a-zA-Z0-9\-]+\.)?(?:amazon|amzn){1}\.(?P<tld>[a-zA-Z\.]{2,})\/(gp/(?:product|offer-listing|customer-media/product-gallery)/|exec/obidos/tg/detail/-/|o/ASIN/|dp/|(?:[A-Za-z0-9\-]+)/dp/)?(?P<ASIN>[0-9A-Za-z]{10})'),
                            lambda m: r'http://amazon.%s/dp/%s' % (m.group('tld'), m.group('ASIN'))),
                Normalizer( re.compile(r'.*waffleimages\.com.*/([0-9a-fA-F]{40})'),
                            lambda m: r'http://img.waffleimages.com/%s' % m.group(1) ),
                Normalizer( re.compile(r'(?:youtube.*?(?:v=|/v/)|youtu\.be/|yooouuutuuube.*?id=)([-_a-z0-9]+)'),
                            lambda m: r'http://youtube.com/watch?v=%s' % m.group(1) ),
    )


def normalize(url):
    """Normalize a URL."""

    scheme, auth, path, query, fragment = urlparse.urlsplit(url.strip())
    userinfo, host, port = re.search('([^@]*@)?([^:]*):?(.*)', auth).groups()

    # Always provide the URI scheme in lowercase characters.
    scheme = scheme.lower()

    # Always provide the host, if any, in lowercase characters.
    host = host.lower()
    if host and host[-1] == '.':
        host = host[:-1]
    if host and host.startswith("www."):
        if not scheme:
            scheme = "http"
        host = host[4:]
    elif path and path.startswith("www."):
        if not scheme:
            scheme = "http"
        path = path[4:]

    # Only perform percent-encoding where it is essential.
    # Always use uppercase A-through-F characters when percent-encoding.
    # All portions of the URI must be utf-8 encoded NFC from Unicode strings
    def clean(string):
        string = unicode(unquote(string), 'utf-8', 'replace')
        return unicodedata.normalize('NFC', string).encode('utf-8')
    path = quote(clean(path), "~:/?#[]@!$&'()*+,;=")
    fragment = quote(clean(fragment), "~")

    # note care must be taken to only encode & and = characters as values
    query = "&".join(["=".join([quote(clean(t), "~:/?#[]@!$'()*+,;=")
        for t in q.split("=", 1)]) for q in query.split("&")])

    # Prevent dot-segments appearing in non-relative URI paths.
    if scheme in ["", "http", "https", "ftp", "file"]:
        output = []
        for input in path.split('/'):
            if input == "":
                if not output:
                    output.append(input)
            elif input == ".":
                pass
            elif input == "..":
                if len(output) > 1:
                    output.pop()
            else:
                output.append(input)
        if input in ["", ".", ".."]:
            output.append("")
        path = '/'.join(output)

    # For schemes that define a default authority, use an empty authority if
    # the default is desired.
    if userinfo in ["@", ":@"]:
        userinfo = ""

    # For schemes that define an empty path to be equivalent to a path of "/",
    # use "/".
    if path == "" and scheme in ["http", "https", "ftp", "file"]:
        path = "/"

    # For schemes that define a port, use an empty port if the default is
    # desired
    if port and scheme in default_port.keys():
        if port.isdigit():
            port = str(int(port))
            if int(port) == default_port[scheme]:
                port = ''

    # Put it all back together again
    auth = (userinfo or "") + host
    if port:
        auth += ":" + port
    if url.endswith("#") and query == "" and fragment == "":
        path += "#"
    normal_url = urlparse.urlunsplit((scheme, auth, path, query,
        fragment)).replace("http:///", "http://")
    for norm in normalizers:
        m = norm.regex.match(normal_url)
        if m:
            return norm.normalize(m)
    return normal_url

########NEW FILE########
__FILENAME__ = validate
'''
Runs a given url through the w3c validator

by Vladi
'''

from util import hook, http


@hook.command
def validate(inp):
    ".validate <url> -- runs url through w3c markup validator"

    if not inp.startswith('http://'):
        inp = 'http://' + inp

    url = 'http://validator.w3.org/check?uri=' + http.quote_plus(inp)
    info = dict(http.open(url).info())

    status = info['x-w3c-validator-status'].lower()
    if status in ("valid", "invalid"):
        errorcount = info['x-w3c-validator-errors']
        warningcount = info['x-w3c-validator-warnings']
        return "%s was found to be %s with %s errors and %s warnings." \
            " see: %s" % (inp, status, errorcount, warningcount, url)

########NEW FILE########
__FILENAME__ = vimeo
from util import hook, http


@hook.regex(r'vimeo.com/([0-9]+)')
def vimeo_url(match):
    info = http.get_json('http://vimeo.com/api/v2/video/%s.json'
                         % match.group(1))

    if info:
        return ("\x02%(title)s\x02 - length \x02%(duration)ss\x02 - "
                "\x02%(stats_number_of_likes)s\x02 likes - "
                "\x02%(stats_number_of_plays)s\x02 plays - "
                "\x02%(user_name)s\x02 on \x02%(upload_date)s\x02"
                % info[0])

########NEW FILE########
__FILENAME__ = weather
"weather, thanks to wunderground"

from util import hook, http


@hook.api_key('wunderground')
@hook.command(autohelp=False)
def weather(inp, chan='', nick='', reply=None, db=None, api_key=None):
    ".weather <location> [dontsave] | @<nick> -- gets weather data from Wunderground "\
            "http://wunderground.com/weather/api"

    if not api_key:
        return None

    # this database is used by other plugins interested in user's locations,
    # like .near in tag.py
    db.execute(
        "create table if not exists location(chan, nick, loc, lat, lon, primary key(chan, nick))")

    if inp[0:1] == '@':
        nick = inp[1:].strip()
        loc = None
        dontsave = True
    else:
        loc = inp

        dontsave = loc.endswith(" dontsave")
        if dontsave:
            loc = loc[:-9].strip().lower()

    if not loc:  # blank line
        loc = db.execute(
            "select loc from location where chan=? and nick=lower(?)",
            (chan, nick)).fetchone()
        if not loc:
            try:
                # grab from old-style weather database
                loc = db.execute("select loc from weather where nick=lower(?)",
                                 (nick,)).fetchone()
            except db.OperationalError:
                pass    # no such table
            if not loc:
                return weather.__doc__
        loc = loc[0]

    loc, _, state = loc.partition(', ')

    # Check to see if a lat, long pair is being passed. This could be done more
    # completely with regex, and converting from DMS to decimal degrees. This
    # is nice and simple, however.
    try:
        float(loc)
        float(state)

        loc = loc + ',' + state
        state = ''
    except ValueError:
        if state:
            state = http.quote_plus(state)
            state += '/'

        loc = http.quote_plus(loc)

    url = 'http://api.wunderground.com/api/'
    query = '{key}/geolookup/conditions/forecast/q/{state}{loc}.json' \
            .format(key=api_key, state=state, loc=loc)
    url += query

    try:
        parsed_json = http.get_json(url)
    except IOError:
        return 'Could not get data from Wunderground'

    info = {}
    if 'current_observation' not in parsed_json:
        resp = 'Could not find weather for {inp}. '.format(inp=inp)

        # In the case of no observation, but results, print some possible
        # location matches
        if 'results' in parsed_json['response']:
            resp += 'Possible matches include: '
            results = parsed_json['response']['results']

            for place in results[:6]:
                resp += '{city}, '.format(**place)

                if place['state']:
                    resp += '{state}, '.format(**place)

                if place['country_name']:
                    resp += '{country_name}; '.format(**place)

            resp = resp[:-2]

        reply(resp)
        return

    obs = parsed_json['current_observation']
    sf = parsed_json['forecast']['simpleforecast']['forecastday'][0]
    info['city'] = obs['display_location']['full']
    info['t_f'] = obs['temp_f']
    info['t_c'] = obs['temp_c']
    info['weather'] = obs['weather']
    info['h_f'] = sf['high']['fahrenheit']
    info['h_c'] = sf['high']['celsius']
    info['l_f'] = sf['low']['fahrenheit']
    info['l_c'] = sf['low']['celsius']
    info['humid'] = obs['relative_humidity']
    info['wind'] = 'Wind: {mph}mph/{kph}kph' \
        .format(mph=obs['wind_mph'], kph=obs['wind_kph'])
    reply('{city}: {weather}, {t_f}F/{t_c}C'
          '(H:{h_f}F/{h_c}C L:{l_f}F/{l_c}C)'
          ', Humidity: {humid}, {wind}'.format(**info))

    lat = float(obs['display_location']['latitude'])
    lon = float(obs['display_location']['longitude'])

    if inp and not dontsave:
        db.execute("insert or replace into location(chan, nick, loc, lat, lon) "
                   "values (?, ?, ?, ?,?)",        (chan, nick.lower(), inp, lat, lon))
        db.commit()

########NEW FILE########
__FILENAME__ = wikipedia
'''Searches wikipedia and returns first sentence of article
Scaevolus 2009'''

import re

from util import hook, http


api_prefix = "http://en.wikipedia.org/w/api.php"
search_url = api_prefix + "?action=opensearch&format=xml"

paren_re = re.compile('\s*\(.*\)$')


@hook.command('w')
@hook.command
def wiki(inp):
    '''.w/.wiki <phrase> -- gets first sentence of wikipedia ''' \
        '''article on <phrase>'''

    x = http.get_xml(search_url, search=inp)

    ns = '{http://opensearch.org/searchsuggest2}'
    items = x.findall(ns + 'Section/' + ns + 'Item')

    if items == []:
        if x.find('error') is not None:
            return 'error: %(code)s: %(info)s' % x.find('error').attrib
        else:
            return 'no results found'

    def extract(item):
        return [item.find(ns + x).text for x in
                ('Text', 'Description', 'Url')]

    title, desc, url = extract(items[0])

    if 'may refer to' in desc:
        title, desc, url = extract(items[1])

    title = paren_re.sub('', title)

    if title.lower() not in desc.lower():
        desc = title + desc

    desc = re.sub('\s+', ' ', desc).strip()  # remove excess spaces

    if len(desc) > 300:
        desc = desc[:300] + '...'

    return '%s -- %s' % (desc, http.quote(http.unquote(url), ':/'))

########NEW FILE########
__FILENAME__ = wolframalpha
import re

from util import hook, http


@hook.api_key('wolframalpha')
@hook.command('wa')
@hook.command
def wolframalpha(inp, api_key=None):
    ".wa/.wolframalpha <query> -- computes <query> using Wolfram Alpha"

    url = 'http://api.wolframalpha.com/v2/query?format=plaintext'

    result = http.get_xml(url, input=inp, appid=api_key)

    pod_texts = []
    for pod in result.xpath("//pod"):
        title = pod.attrib['title']
        if pod.attrib['id'] == 'Input':
            continue

        results = []
        for subpod in pod.xpath('subpod/plaintext/text()'):
            subpod = subpod.strip().replace('\\n', '; ')
            subpod = re.sub(r'\s+', ' ', subpod)
            if subpod:
                results.append(subpod)
        if results:
            pod_texts.append(title + ': ' + '|'.join(results))

    ret = '. '.join(pod_texts)

    if not pod_texts:
        return 'no results'

    ret = re.sub(r'\\(.)', r'\1', ret)

    def unicode_sub(match):
        return unichr(int(match.group(1), 16))

    ret = re.sub(r'\\:([0-9a-z]{4})', unicode_sub, ret)

    if len(ret) > 430:
        ret = ret[:ret.rfind(' ', 0, 430)]
        ret = re.sub(r'\W+$', '', ret) + '...'

    if not ret:
        return 'no results'

    return ret

########NEW FILE########
__FILENAME__ = yahooanswers
from util import hook, http
from random import choice


@hook.api_key('yahoo')
@hook.command
def answer(inp, api_key=None):
    ".answer <query> -- find the answer to a question on Yahoo! Answers"

    url = "http://answers.yahooapis.com/AnswersService/V1/questionSearch"

    result = http.get_json(url,
                           query=inp,
                           search_in="question",
                           output="json",
                           appid=api_key)

    questions = result.get("all", {}).get("questions", [])
    answered = filter(lambda x: x.get("ChosenAnswer", ""), questions)

    if not answered:
        return "no results"

    chosen = choice(answered)
    answer, link = chosen["ChosenAnswer"], chosen["Link"]
    response = "%s -- %s" % (answer, link)

    return " ".join(response.split())

########NEW FILE########
__FILENAME__ = youtube
import re
import time

from util import hook, http


youtube_re = (r'(?:youtube.*?(?:v=|/v/)|youtu\.be/|yooouuutuuube.*?id=)'
              '([-_a-z0-9]+)', re.I)

base_url = 'http://gdata.youtube.com/feeds/api/'
url = base_url + 'videos/%s?v=2&alt=jsonc'
search_api_url = base_url + 'videos?v=2&alt=jsonc&max-results=1'
video_url = 'http://youtube.com/watch?v=%s'


def get_video_description(vid_id):
    j = http.get_json(url % vid_id)

    if j.get('error'):
        return

    j = j['data']

    out = '\x02%s\x02' % j['title']

    if not j.get('duration'):
        return out

    out += ' - length \x02'
    length = j['duration']
    if length / 3600:  # > 1 hour
        out += '%dh ' % (length / 3600)
    if length / 60:
        out += '%dm ' % (length / 60 % 60)
    out += "%ds\x02" % (length % 60)

    if 'rating' in j:
        out += ' - rated \x02%.2f/5.0\x02 (%d)' % (j['rating'],
                                                   j['ratingCount'])

    if 'viewCount' in j:
        out += ' - \x02%s\x02 views' % group_int_digits(j['viewCount'])

    upload_time = time.strptime(j['uploaded'], "%Y-%m-%dT%H:%M:%S.000Z")
    out += ' - \x02%s\x02 on \x02%s\x02' % (
                        j['uploader'], time.strftime("%Y.%m.%d", upload_time))

    if 'contentRating' in j:
        out += ' - \x034NSFW\x02'

    return out

def group_int_digits(number, delimiter=' ', grouping=3):
    base = str(number).strip()
    builder = []
    while base:
        builder.append(base[-grouping:])
        base = base[:-grouping]
    builder.reverse()
    return delimiter.join(builder)

@hook.regex(*youtube_re)
def youtube_url(match):
    return get_video_description(match.group(1))


@hook.command('yt')
@hook.command('y')
@hook.command
def youtube(inp):
    '.youtube <query> -- returns the first YouTube search result for <query>'

    j = http.get_json(search_api_url, q=inp)

    if 'error' in j:
        return 'error while performing the search'

    if j['data']['totalItems'] == 0:
        return 'no results found'

    vid_id = j['data']['items'][0]['id']

    return get_video_description(vid_id) + " - " + video_url % vid_id

########NEW FILE########
