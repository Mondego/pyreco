__FILENAME__ = cloudbot
#!/usr/bin/env python

import os
import Queue
import sys
import time
import re

sys.path += ['plugins', 'lib']  # add stuff to the sys.path for easy imports
os.chdir(sys.path[0] or '.')  # do stuff relative to the install directory


class Bot(object):
    pass

print 'CloudBot DEV <http://git.io/cloudbotirc>'

# create new bot object
bot = Bot()
bot.vars = {}

# record start time for the uptime command
bot.start_time = time.time()

print 'Begin Plugin Loading.'

# bootstrap the reloader
eval(compile(open(os.path.join('core', 'reload.py'), 'U').read(),
             os.path.join('core', 'reload.py'), 'exec'))
reload(init=True)

config()
if not hasattr(bot, 'config'):
    exit()

print 'Connecting to IRC...'

bot.conns = {}

try:
    for name, conf in bot.config['connections'].iteritems():
        # strip all spaces and capitalization from the connection name
        name = name.replace(" ", "_")
        name = re.sub('[^A-Za-z0-9_]+', '', name)
        print 'Connecting to server: %s' % conf['server']
        if conf.get('ssl'):
            bot.conns[name] = SSLIRC(name, conf['server'], conf['nick'], conf=conf,
                                     port=conf.get('port', 6667), channels=conf['channels'],
                                     ignore_certificate_errors=conf.get('ignore_cert', True))
        else:
            bot.conns[name] = IRC(name, conf['server'], conf['nick'], conf=conf,
                                  port=conf.get('port', 6667), channels=conf['channels'])
except Exception as e:
    print 'ERROR: malformed config file', e
    sys.exit()

bot.persist_dir = os.path.abspath('persist')
if not os.path.exists(bot.persist_dir):
    os.mkdir(bot.persist_dir)

print 'Connection(s) made, starting main loop.'

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
    print "Please rename 'config.default' to 'config' to set up your bot!"
    print "For help, see http://git.io/cloudbotirc"
    print "Thank you for using CloudBot!"
    sys.exit()


def config():
    # reload config from file if file has changed
    config_mtime = os.stat('config').st_mtime
    if bot._config_mtime != config_mtime:
        try:
            bot.config = json.load(open('config'))
            bot._config_mtime = config_mtime
        except ValueError, e:
            print 'error: malformed config', e


bot._config_mtime = 0

########NEW FILE########
__FILENAME__ = db
import os
import sqlite3
import thread

threaddbs = {}


def get_db_connection(conn, name=''):
    """returns an sqlite3 connection to a persistent database"""

    if not name:
        name = '{}.db'.format(conn.name)

    threadid = thread.get_ident()
    if name in threaddbs and threadid in threaddbs[name]:
        return threaddbs[name][threadid]
    filename = os.path.join(bot.persist_dir, name)

    db = sqlite3.connect(filename, timeout=10)
    if name in threaddbs:
        threaddbs[name][threadid] = db
    else:
        threaddbs[name] = {threadid: db}
    return db

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
        if bot.config['censored_strings']:
            words = map(re.escape, bot.config['censored_strings'])
            regex = re.compile('({})'.format("|".join(words)))
            text = regex.sub(replacement, text)
    return text


class crlf_tcp(object):
    """Handles tcp connections that consist of utf-8 lines ending with crlf"""

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
    """Handles ssl tcp connetions that consist of utf-8 lines ending with crlf"""

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
    """handles the IRC protocol"""

    def __init__(self, name, server, nick, port=6667, channels=[], conf={}):
        self.name = name
        self.channels = channels
        self.conf = conf
        self.server = server
        self.port = port
        self.nick = nick
        self.history = {}
        self.vars = {}

        self.out = Queue.Queue()  # responses from the server are placed here
        # format: [rawline, prefix, command, params,
        # nick, user, host, paramlist, msg]
        self.connect()

        thread.start_new_thread(self.parse_loop, ())

    def create_connection(self):
        return crlf_tcp(self.server, self.port)

    def connect(self):
        self.conn = self.create_connection()
        thread.start_new_thread(self.conn.run, ())
        self.set_pass(self.conf.get('server_password'))
        self.set_nick(self.nick)
        self.cmd("USER",
                 [conf.get('user', 'cloudbot'), "3", "*", conf.get('realname',
                                                                   'CloudBot - http://git.io/cloudbot')])

    def parse_loop(self):
        while True:
            # get a message from the input queue
            msg = self.conn.iqueue.get()

            if msg == StopIteration:
                self.connect()
                continue

            # parse the message
            if msg.startswith(":"):  # has a prefix
                prefix, command, params = irc_prefix_rem(msg).groups()
            else:
                prefix, command, params = irc_noprefix_rem(msg).groups()
            nick, user, host = irc_netmask_rem(prefix).groups()
            mask = nick + "!" + user + "@" + host
            paramlist = irc_param_ref(params)
            lastparam = ""
            if paramlist:
                if paramlist[-1].startswith(':'):
                    paramlist[-1] = paramlist[-1][1:]
                lastparam = paramlist[-1]
            # put the parsed message in the response queue
            self.out.put([msg, prefix, command, params, nick, user, host,
                          mask, paramlist, lastparam])
            # if the server pings us, pong them back
            if command == "PING":
                self.cmd("PONG", paramlist)

    def set_pass(self, password):
        if password:
            self.cmd("PASS", [password])

    def set_nick(self, nick):
        self.cmd("NICK", [nick])

    def join(self, channel):
        """ makes the bot join a channel """
        self.send("JOIN {}".format(channel))
        if channel not in self.channels:
            self.channels.append(channel)

    def part(self, channel):
        """ makes the bot leave a channel """
        self.cmd("PART", [channel])
        if channel in self.channels:
            self.channels.remove(channel)

    def msg(self, target, text):
        """ makes the bot send a PRIVMSG to a target  """
        self.cmd("PRIVMSG", [target, text])

    def ctcp(self, target, ctcp_type, text):
        """ makes the bot send a PRIVMSG CTCP to a target """
        out = u"\x01{} {}\x01".format(ctcp_type, text)
        self.cmd("PRIVMSG", [target, out])

    def cmd(self, command, params=None):
        if params:
            params[-1] = u':' + params[-1]
            self.send(u"{} {}".format(command, ' '.join(params)))
        else:
            self.send(command)

    def send(self, str):
        self.conn.oqueue.put(str)


class SSLIRC(IRC):
    def __init__(self, name, server, nick, port=6667, channels=[], conf={},
                 ignore_certificate_errors=True):
        self.ignore_cert_errors = ignore_certificate_errors
        IRC.__init__(self, name, server, nick, port, channels, conf)

    def create_connection(self):
        return crlf_ssl_tcp(self.server, self.port, self.ignore_cert_errors)

########NEW FILE########
__FILENAME__ = main
import thread
import traceback


thread.stack_size(1024 * 512)  # reduce vm size


class Input(dict):
    def __init__(self, conn, raw, prefix, command, params,
                 nick, user, host, mask, paraml, msg):

        chan = paraml[0].lower()
        if chan == conn.nick.lower():  # is a PM
            chan = nick

        def message(message, target=chan):
            """sends a message to a specific or current channel/user"""
            conn.msg(target, message)

        def reply(message, target=chan):
            """sends a message to the current channel/user with a prefix"""
            if target == nick:
                conn.msg(target, message)
            else:
                conn.msg(target, u"({}) {}".format(nick, message))

        def action(message, target=chan):
            """sends an action to the current channel/user or a specific channel/user"""
            conn.ctcp(target, "ACTION", message)

        def ctcp(message, ctcp_type, target=chan):
            """sends an ctcp to the current channel/user or a specific channel/user"""
            conn.ctcp(target, ctcp_type, message)

        def notice(message, target=nick):
            """sends a notice to the current channel/user or a specific channel/user"""
            conn.cmd('NOTICE', [target, message])

        dict.__init__(self, conn=conn, raw=raw, prefix=prefix, command=command,
                      params=params, nick=nick, user=user, host=host, mask=mask,
                      paraml=paraml, msg=msg, server=conn.server, chan=chan,
                      notice=notice, message=message, reply=reply, bot=bot,
                      action=action, ctcp=ctcp, lastparam=paraml[-1])

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
    """Runs plugins in their own threads (ensures order)"""

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
                import traceback

                traceback.print_exc()

    def stop(self):
        self.input_queue.put(StopIteration)

    def put(self, value):
        self.input_queue.put(value)


def dispatch(input, kind, func, args, autohelp=False):
    for sieve, in bot.plugs['sieve']:
        input = do_sieve(sieve, bot, input, func, kind, args)
        if input is None:
            return

    if not (not autohelp or not args.get('autohelp', True) or input.inp or not (func.__doc__ is not None)):
        input.notice(input.conn.conf["command_prefix"] + func.__doc__)
        return

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
    command_prefix = conn.conf.get('command_prefix', '.')

    # EVENTS
    for func, args in bot.events[inp.command] + bot.events['*']:
        dispatch(Input(conn, *out), "event", func, args)

    if inp.command == 'PRIVMSG':
        # COMMANDS
        if inp.chan == inp.nick:  # private message, no command prefix
            prefix = '^(?:[{}]?|'.format(command_prefix)
        else:
            prefix = '^(?:[{}]|'.format(command_prefix)

        command_re = prefix + inp.conn.nick
        command_re += r'[,;:]+\s+)(\w+)(?:$|\s+)(.*)'

        m = re.match(command_re, inp.lastparam)

        if m:
            trigger = m.group(1).lower()
            command = match_command(trigger)

            if isinstance(command, list):  # multiple potential matches
                input = Input(conn, *out)
                input.notice("Did you mean {} or {}?".format
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


def format_plug(plug, kind='', lpad=0):
    out = ' ' * lpad + '{}:{}:{}'.format(*make_signature(plug[0]))
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
                print '### ERROR: invalid command name "{}" ({})'.format(name, format_plug(plug))
                continue
            if name in bot.commands:
                print "### ERROR: command '{}' already registered ({}, {})".format(name,
                                                                                   format_plug(bot.commands[name]),
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
            print '    {}:'.format(kind)
            for plug in plugs:
                print format_plug(plug, kind=kind, lpad=6)
        print

########NEW FILE########
__FILENAME__ = cleverbot
# from jessi bot
import urllib2
import hashlib
import re
import unicodedata
from util import hook

# these are just parts required
# TODO: Merge them.

arglist = ['', 'y', '', '', '', '', '', '', '', '', 'wsf', '',
           '', '', '', '', '', '', '', '0', 'Say', '1', 'false']

always_safe = ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
               'abcdefghijklmnopqrstuvwxyz'
               '0123456789' '_.-')

headers = {'X-Moz': 'prefetch', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
           'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:7.0.1)Gecko/20100101 Firefox/7.0',
           'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Referer': 'http://www.cleverbot.com',
           'Pragma': 'no-cache', 'Cache-Control': 'no-cache, no-cache', 'Accept-Language': 'en-us;q=0.8,en;q=0.5'}

keylist = ['stimulus', 'start', 'sessionid', 'vText8', 'vText7', 'vText6',
           'vText5', 'vText4', 'vText3', 'vText2', 'icognoid',
           'icognocheck', 'prevref', 'emotionaloutput', 'emotionalhistory',
           'asbotname', 'ttsvoice', 'typing', 'lineref', 'fno', 'sub',
           'islearning', 'cleanslate']

MsgList = list()


def quote(s, safe='/'):  # quote('abc def') -> 'abc%20def'
    s = s.encode('utf-8')
    s = s.decode('utf-8')
    print "s= " + s
    print "safe= " + safe
    safe += always_safe
    safe_map = dict()
    for i in range(256):
        c = chr(i)
        safe_map[c] = (c in safe) and c or ('%%%02X' % i)
    try:
        res = map(safe_map.__getitem__, s)
    except:
        print "blank"
        return ''
    print "res= " + ''.join(res)
    return ''.join(res)


def encode(keylist, arglist):
    text = str()
    for i in range(len(keylist)):
        k = keylist[i]
        v = quote(arglist[i])
        text += '&' + k + '=' + v
    text = text[1:]
    return text


def Send():
    data = encode(keylist, arglist)
    digest_txt = data[9:29]
    new_hash = hashlib.md5(digest_txt).hexdigest()
    arglist[keylist.index('icognocheck')] = new_hash
    data = encode(keylist, arglist)
    req = urllib2.Request('http://www.cleverbot.com/webservicemin',
                          data, headers)
    f = urllib2.urlopen(req)
    reply = f.read()
    return reply


def parseAnswers(text):
    d = dict()
    keys = ['text', 'sessionid', 'logurl', 'vText8', 'vText7', 'vText6',
            'vText5', 'vText4', 'vText3', 'vText2', 'prevref', 'foo',
            'emotionalhistory', 'ttsLocMP3', 'ttsLocTXT', 'ttsLocTXT3',
            'ttsText', 'lineRef', 'lineURL', 'linePOST', 'lineChoices',
            'lineChoicesAbbrev', 'typingData', 'divert']
    values = text.split('\r')
    i = 0
    for key in keys:
        d[key] = values[i]
        i += 1
    return d


def ask(inp):
    arglist[keylist.index('stimulus')] = inp
    if MsgList:
        arglist[keylist.index('lineref')] = '!0' + str(len(
            MsgList) / 2)
    asw = Send()
    MsgList.append(inp)
    answer = parseAnswers(asw)
    for k, v in answer.iteritems():
        try:
            arglist[keylist.index(k)] = v
        except ValueError:
            pass
    arglist[keylist.index('emotionaloutput')] = str()
    text = answer['ttsText']
    MsgList.append(text)
    return text


@hook.command("cb")
def cleverbot(inp, reply=None):
    reply(ask(inp))


''' # TODO: add in command to control extra verbose per channel
@hook.event('PRIVMSG')
def cbevent(inp, reply=None):
    reply(ask(inp))

@hook.command("cbver", permissions=['cleverbot'])
def cleverbotverbose(inp, notice=None):
    if on in input
'''

########NEW FILE########
__FILENAME__ = mtg
import re

from util import hook, http


@hook.command
def mtg(inp):
    ".mtg <name> -- Gets information about Magic the Gathering card <name>."

    url = 'http://magiccards.info/query?v=card&s=cname'
    h = http.get_html(url, q=inp)

    name = h.find('body/table/tr/td/span/a')
    if name is None:
        return "No cards found :("
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
__FILENAME__ = mygengo_translate
# BING translation plugin by Lukeroge and neersighted
from util import hook
from util import http
import re
import htmlentitydefs
import mygengo

gengo = mygengo.MyGengo(
    public_key='PlwtF1CZ2tu27IdX_SXNxTFmfN0j|_-pJ^Rf({O-oLl--r^QM4FygRdt^jusSSDE',
    private_key='wlXpL=SU[#JpPu[dQaf$v{S3@rg[=95$$TA(k$sb3_6~B_zDKkTbd4#hXxaorIae',
    sandbox=False,
)

def gengo_translate(text, source, target):
    try:
        translation = gengo.postTranslationJob(job={
            'type': 'text',
            'slug': 'Translating '+source+' to '+target+' with the myGengo API',
            'body_src': text, 
            'lc_src': source,
            'lc_tgt': target,
            'tier': 'machine',
        })
        translated = translation['response']['job']['body_tgt']
        return u"(%s > %s) %s" % (source, target, translated)
    except mygengo.MyGengoError:
        return "error: could not translate"

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
def translate(inp):
    ".translate <source language> <target language> <sentence> -- Translates <sentence> from <source language> to <target language> using MyGengo."
    args = inp.split(' ')
    sl = match_language(args[0])
    tl = match_language(args[1])
    txt = unicode(" ".join(args[2:]))
    if sl and tl:
        return unicode(gengo_translate(txt, sl, tl))
    else:
        return "error: translate could not reliably determine one or both languages"

languages = 'ja fr de ko ru zh'.split()
language_pairs = zip(languages[:-1], languages[1:])
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
    ("cs cz", "Czech"),
    ("da dk", "Danish"),
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
__FILENAME__ = religion
from util import hook, http


@hook.command('god')
@hook.command
def bible(inp):
    """.bible <passage> -- gets <passage> from the Bible (ESV)"""

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
    """.koran <chapter.verse> -- gets <chapter.verse> from the Koran"""

    url = 'http://quod.lib.umich.edu/cgi/k/koran/koran-idx?type=simple'

    results = http.get_html(url, q1=inp).xpath('//li')

    if not results:
        return 'No results for ' + inp

    return results[0].text_content()

########NEW FILE########
__FILENAME__ = repaste
from util import hook, http

import urllib
import random
import urllib2
import htmlentitydefs
import re

re_htmlent = re.compile("&(" + "|".join(htmlentitydefs.name2codepoint.keys()) + ");")
re_numeric = re.compile(r'&#(x?)([a-fA-F0-9]+);')


def db_init(db):
    db.execute("create table if not exists repaste(chan, manual, primary key(chan))")
    db.commit()


def decode_html(text):
    text = re.sub(re_htmlent,
                   lambda m: unichr(htmlentitydefs.name2codepoint[m.group(1)]),
                   text)

    text = re.sub(re_numeric,
                  lambda m: unichr(int(m.group(2), 16 if m.group(1) else 10)),
                  text)
    return text


def scrape_mibpaste(url):
    if not url.startswith("http"):
        url = "http://" + url
    pagesource = http.get(url)
    rawpaste = re.search(r'(?s)(?<=<body>\n).+(?=<hr>)', pagesource).group(0)
    filterbr = rawpaste.replace("<br />", "")
    unescaped = decode_html(filterbr)
    stripped = unescaped.strip()

    return stripped


def scrape_pastebin(url):
    id = re.search(r'(?:www\.)?pastebin.com/([a-zA-Z0-9]+)$', url).group(1)
    rawurl = "http://pastebin.com/raw.php?i=" + id
    text = http.get(rawurl)

    return text


autorepastes = {}


#@hook.regex('(pastebin\.com)(/[^ ]+)')
@hook.regex('(mibpaste\.com)(/[^ ]+)')
def autorepaste(inp, input=None, notice=None, db=None, chan=None, nick=None):
    db_init(db)
    manual = db.execute("select manual from repaste where chan=?", (chan, )).fetchone()
    if manual and len(manual) and manual[0]:
        return
    url = inp.group(1) + inp.group(2)
    urllib.unquote(url)
    if url in autorepastes:
        out = autorepastes[url]
        notice("In the future, please use a less awful pastebin (e.g. pastebin.com)")
    else:
        out = repaste("http://" + url, input, db, False)
        autorepastes[url] = out
        notice("In the future, please use a less awful pastebin (e.g. pastebin.com) instead of %s." % inp.group(1))
    input.say("%s (repasted for %s)" % (out, nick))


scrapers = {
    r'mibpaste\.com': scrape_mibpaste,
    r'pastebin\.com': scrape_pastebin
}


def scrape(url):
    for pat, scraper in scrapers.iteritems():
        print "matching " + repr(pat) + " " + url
        if re.search(pat, url):
            break
    else:
        return None

    return scraper(url)


def paste_sprunge(text, syntax=None, user=None):
    data = urllib.urlencode({"sprunge": text})
    url = urllib2.urlopen("http://sprunge.us/", data).read().strip()

    if syntax:
        url += "?" + syntax

    return url


def paste_ubuntu(text, user=None, syntax='text'):
    data = urllib.urlencode({"poster": user,
                             "syntax": syntax,
                             "content": text})

    return urllib2.urlopen("http://paste.ubuntu.com/", data).url


def paste_gist(text, user=None, syntax=None, description=None):
    data = {
        'file_contents[gistfile1]': text,
        'action_button': "private"
    }

    if description:
        data['description'] = description

    if syntax:
        data['file_ext[gistfile1]'] = "." + syntax

    req = urllib2.urlopen('https://gist.github.com/gists', urllib.urlencode(data).encode('utf8'))
    return req.url


def paste_strictfp(text, user=None, syntax="plain"):
    data = urllib.urlencode(dict(
        language=syntax,
        paste=text,
        private="private",
        submit="Paste"))
    req = urllib2.urlopen("http://paste.strictfp.com/", data)
    return req.url


pasters = dict(
    ubuntu=paste_ubuntu,
    sprunge=paste_sprunge,
    gist=paste_gist,
    strictfp=paste_strictfp
)


@hook.command
def repaste(inp, input=None, db=None, isManual=True):
    ".repaste mode|list|[provider] [syntax] <pastebinurl> -- Reuploads mibpaste to [provider]."

    parts = inp.split()
    db_init(db)
    if parts[0] == 'list':
        return " ".join(pasters.keys())

    paster = paste_gist
    args = {}

    if not parts[0].startswith("http"):
        p = parts[0].lower()

        if p in pasters:
            paster = pasters[p]
            parts = parts[1:]

    if not parts[0].startswith("http"):
        p = parts[0].lower()
        parts = parts[1:]

        args["syntax"] = p

    if len(parts) > 1:
        return "PEBKAC"

    args["user"] = input.user

    url = parts[0]

    scraped = scrape(url)

    if not scraped:
        return "No scraper for given url"

    args["text"] = scraped
    pasted = paster(**args)

    return pasted

########NEW FILE########
__FILENAME__ = urlhistory
import math
import re
import time

from util import hook, urlnorm, timesince


expiration_period = 60 * 60 * 24  # 1 day

ignored_urls = [urlnorm.normalize("http://google.com"),]


def db_init(db):
    db.execute("create table if not exists urlhistory"
                 "(chan, url, nick, time)")
    db.commit()


def insert_history(db, chan, url, nick):
    now = time.time()
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
        return #"%s linked that %s ago." % (last_nick, last_time)

    hour_span = math.ceil((time.time() - history[-1][1]) / 3600)
    hour_span = '%.0f hours' % hour_span if hour_span > 1 else 'hour'

    hlen = len(history)
    ordinal = ["once", "twice", "%d times" % hlen][min(hlen, 3) - 1]

    if len(dict(history)) == 1:
        last = "last linked %s ago" % last_time
    else:
        last = "last linked by %s %s ago" % (last_nick, last_time)

    return #"that url has been posted %s in the past %s by %s (%s)." % (ordinal,

@hook.command
def url(inp, nick='', chan='', db=None, bot=None):
    db_init(db)
    url = urlnorm.normalize(inp.group().encode('utf-8'))
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
__FILENAME__ = wordoftheday
import re
from util import hook, http, misc
from BeautifulSoup import BeautifulSoup


@hook.command(autohelp=False)
def word(inp, say=False, nick=False):
    "word -- Gets the word of the day."
    page = http.get('http://merriam-webster.com/word-of-the-day')

    soup = BeautifulSoup(page)

    word = soup.find('strong', {'class': 'main_entry_word'}).renderContents()
    function = soup.find('p', {'class': 'word_function'}).renderContents()

    #definitions = re.findall(r'<span class="ssens"><strong>:</strong>'
    #                        r' *([^<]+)</span>', content)

    say("(%s) The word of the day is:"\
        " \x02%s\x02 (%s)" % (nick, word, function))

########NEW FILE########
__FILENAME__ = _html5lib
__all__ = [
    'HTML5TreeBuilder',
    ]

import warnings
from bs4.builder import (
    PERMISSIVE,
    HTML,
    HTML_5,
    HTMLTreeBuilder,
    )
from bs4.element import NamespacedAttribute
import html5lib
from html5lib.constants import namespaces
from bs4.element import (
    Comment,
    Doctype,
    NavigableString,
    Tag,
    )

class HTML5TreeBuilder(HTMLTreeBuilder):
    """Use html5lib to build a tree."""

    features = ['html5lib', PERMISSIVE, HTML_5, HTML]

    def prepare_markup(self, markup, user_specified_encoding):
        # Store the user-specified encoding for use later on.
        self.user_specified_encoding = user_specified_encoding
        return markup, None, None, False

    # These methods are defined by Beautiful Soup.
    def feed(self, markup):
        if self.soup.parse_only is not None:
            warnings.warn("You provided a value for parse_only, but the html5lib tree builder doesn't support parse_only. The entire document will be parsed.")
        parser = html5lib.HTMLParser(tree=self.create_treebuilder)
        doc = parser.parse(markup, encoding=self.user_specified_encoding)

        # Set the character encoding detected by the tokenizer.
        if isinstance(markup, unicode):
            # We need to special-case this because html5lib sets
            # charEncoding to UTF-8 if it gets Unicode input.
            doc.original_encoding = None
        else:
            doc.original_encoding = parser.tokenizer.stream.charEncoding[0]

    def create_treebuilder(self, namespaceHTMLElements):
        self.underlying_builder = TreeBuilderForHtml5lib(
            self.soup, namespaceHTMLElements)
        return self.underlying_builder

    def test_fragment_to_document(self, fragment):
        """See `TreeBuilder`."""
        return u'<html><head></head><body>%s</body></html>' % fragment


class TreeBuilderForHtml5lib(html5lib.treebuilders._base.TreeBuilder):

    def __init__(self, soup, namespaceHTMLElements):
        self.soup = soup
        super(TreeBuilderForHtml5lib, self).__init__(namespaceHTMLElements)

    def documentClass(self):
        self.soup.reset()
        return Element(self.soup, self.soup, None)

    def insertDoctype(self, token):
        name = token["name"]
        publicId = token["publicId"]
        systemId = token["systemId"]

        doctype = Doctype.for_name_and_ids(name, publicId, systemId)
        self.soup.object_was_parsed(doctype)

    def elementClass(self, name, namespace):
        tag = self.soup.new_tag(name, namespace)
        return Element(tag, self.soup, namespace)

    def commentClass(self, data):
        return TextNode(Comment(data), self.soup)

    def fragmentClass(self):
        self.soup = BeautifulSoup("")
        self.soup.name = "[document_fragment]"
        return Element(self.soup, self.soup, None)

    def appendChild(self, node):
        # XXX This code is not covered by the BS4 tests.
        self.soup.append(node.element)

    def getDocument(self):
        return self.soup

    def getFragment(self):
        return html5lib.treebuilders._base.TreeBuilder.getFragment(self).element

class AttrList(object):
    def __init__(self, element):
        self.element = element
        self.attrs = dict(self.element.attrs)
    def __iter__(self):
        return list(self.attrs.items()).__iter__()
    def __setitem__(self, name, value):
        "set attr", name, value
        self.element[name] = value
    def items(self):
        return list(self.attrs.items())
    def keys(self):
        return list(self.attrs.keys())
    def __len__(self):
        return len(self.attrs)
    def __getitem__(self, name):
        return self.attrs[name]
    def __contains__(self, name):
        return name in list(self.attrs.keys())


class Element(html5lib.treebuilders._base.Node):
    def __init__(self, element, soup, namespace):
        html5lib.treebuilders._base.Node.__init__(self, element.name)
        self.element = element
        self.soup = soup
        self.namespace = namespace

    def appendChild(self, node):
        if (node.element.__class__ == NavigableString and self.element.contents
            and self.element.contents[-1].__class__ == NavigableString):
            # Concatenate new text onto old text node
            # XXX This has O(n^2) performance, for input like
            # "a</a>a</a>a</a>..."
            old_element = self.element.contents[-1]
            new_element = self.soup.new_string(old_element + node.element)
            old_element.replace_with(new_element)
            self.soup._most_recent_element = new_element
        else:
            self.soup.object_was_parsed(node.element, parent=self.element)

    def getAttributes(self):
        return AttrList(self.element)

    def setAttributes(self, attributes):
        if attributes is not None and len(attributes) > 0:

            converted_attributes = []
            for name, value in list(attributes.items()):
                if isinstance(name, tuple):
                    new_name = NamespacedAttribute(*name)
                    del attributes[name]
                    attributes[new_name] = value

            self.soup.builder._replace_cdata_list_attribute_values(
                self.name, attributes)
            for name, value in attributes.items():
                self.element[name] = value

            # The attributes may contain variables that need substitution.
            # Call set_up_substitutions manually.
            #
            # The Tag constructor called this method when the Tag was created,
            # but we just set/changed the attributes, so call it again.
            self.soup.builder.set_up_substitutions(self.element)
    attributes = property(getAttributes, setAttributes)

    def insertText(self, data, insertBefore=None):
        text = TextNode(self.soup.new_string(data), self.soup)
        if insertBefore:
            self.insertBefore(text, insertBefore)
        else:
            self.appendChild(text)

    def insertBefore(self, node, refNode):
        index = self.element.index(refNode.element)
        if (node.element.__class__ == NavigableString and self.element.contents
            and self.element.contents[index-1].__class__ == NavigableString):
            # (See comments in appendChild)
            old_node = self.element.contents[index-1]
            new_str = self.soup.new_string(old_node + node.element)
            old_node.replace_with(new_str)
        else:
            self.element.insert(index, node.element)
            node.parent = self

    def removeChild(self, node):
        node.element.extract()

    def reparentChildren(self, newParent):
        while self.element.contents:
            child = self.element.contents[0]
            child.extract()
            if isinstance(child, Tag):
                newParent.appendChild(
                    Element(child, self.soup, namespaces["html"]))
            else:
                newParent.appendChild(
                    TextNode(child, self.soup))

    def cloneNode(self):
        tag = self.soup.new_tag(self.element.name, self.namespace)
        node = Element(tag, self.soup, self.namespace)
        for key,value in self.attributes:
            node.attributes[key] = value
        return node

    def hasContent(self):
        return self.element.contents

    def getNameTuple(self):
        if self.namespace == None:
            return namespaces["html"], self.name
        else:
            return self.namespace, self.name

    nameTuple = property(getNameTuple)

class TextNode(Element):
    def __init__(self, element, soup):
        html5lib.treebuilders._base.Node.__init__(self, None)
        self.element = element
        self.soup = soup

    def cloneNode(self):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = _htmlparser
"""Use the HTMLParser library to parse HTML files that aren't too bad."""

__all__ = [
    'HTMLParserTreeBuilder',
    ]

from HTMLParser import (
    HTMLParser,
    HTMLParseError,
    )
import sys
import warnings

# Starting in Python 3.2, the HTMLParser constructor takes a 'strict'
# argument, which we'd like to set to False. Unfortunately,
# http://bugs.python.org/issue13273 makes strict=True a better bet
# before Python 3.2.3.
#
# At the end of this file, we monkeypatch HTMLParser so that
# strict=True works well on Python 3.2.2.
major, minor, release = sys.version_info[:3]
CONSTRUCTOR_TAKES_STRICT = (
    major > 3
    or (major == 3 and minor > 2)
    or (major == 3 and minor == 2 and release >= 3))

from bs4.element import (
    CData,
    Comment,
    Declaration,
    Doctype,
    ProcessingInstruction,
    )
from bs4.dammit import EntitySubstitution, UnicodeDammit

from bs4.builder import (
    HTML,
    HTMLTreeBuilder,
    STRICT,
    )


HTMLPARSER = 'html.parser'

class BeautifulSoupHTMLParser(HTMLParser):
    def handle_starttag(self, name, attrs):
        # XXX namespace
        self.soup.handle_starttag(name, None, None, dict(attrs))

    def handle_endtag(self, name):
        self.soup.handle_endtag(name)

    def handle_data(self, data):
        self.soup.handle_data(data)

    def handle_charref(self, name):
        # XXX workaround for a bug in HTMLParser. Remove this once
        # it's fixed.
        if name.startswith('x'):
            real_name = int(name.lstrip('x'), 16)
        elif name.startswith('X'):
            real_name = int(name.lstrip('X'), 16)
        else:
            real_name = int(name)

        try:
            data = unichr(real_name)
        except (ValueError, OverflowError), e:
            data = u"\N{REPLACEMENT CHARACTER}"

        self.handle_data(data)

    def handle_entityref(self, name):
        character = EntitySubstitution.HTML_ENTITY_TO_CHARACTER.get(name)
        if character is not None:
            data = character
        else:
            data = "&%s;" % name
        self.handle_data(data)

    def handle_comment(self, data):
        self.soup.endData()
        self.soup.handle_data(data)
        self.soup.endData(Comment)

    def handle_decl(self, data):
        self.soup.endData()
        if data.startswith("DOCTYPE "):
            data = data[len("DOCTYPE "):]
        elif data == 'DOCTYPE':
            # i.e. "<!DOCTYPE>"
            data = ''
        self.soup.handle_data(data)
        self.soup.endData(Doctype)

    def unknown_decl(self, data):
        if data.upper().startswith('CDATA['):
            cls = CData
            data = data[len('CDATA['):]
        else:
            cls = Declaration
        self.soup.endData()
        self.soup.handle_data(data)
        self.soup.endData(cls)

    def handle_pi(self, data):
        self.soup.endData()
        if data.endswith("?") and data.lower().startswith("xml"):
            # "An XHTML processing instruction using the trailing '?'
            # will cause the '?' to be included in data." - HTMLParser
            # docs.
            #
            # Strip the question mark so we don't end up with two
            # question marks.
            data = data[:-1]
        self.soup.handle_data(data)
        self.soup.endData(ProcessingInstruction)


class HTMLParserTreeBuilder(HTMLTreeBuilder):

    is_xml = False
    features = [HTML, STRICT, HTMLPARSER]

    def __init__(self, *args, **kwargs):
        if CONSTRUCTOR_TAKES_STRICT:
            kwargs['strict'] = False
        self.parser_args = (args, kwargs)

    def prepare_markup(self, markup, user_specified_encoding=None,
                       document_declared_encoding=None):
        """
        :return: A 4-tuple (markup, original encoding, encoding
        declared within markup, whether any characters had to be
        replaced with REPLACEMENT CHARACTER).
        """
        if isinstance(markup, unicode):
            return markup, None, None, False

        try_encodings = [user_specified_encoding, document_declared_encoding]
        dammit = UnicodeDammit(markup, try_encodings, is_html=True)
        return (dammit.markup, dammit.original_encoding,
                dammit.declared_html_encoding,
                dammit.contains_replacement_characters)

    def feed(self, markup):
        args, kwargs = self.parser_args
        parser = BeautifulSoupHTMLParser(*args, **kwargs)
        parser.soup = self.soup
        try:
            parser.feed(markup)
        except HTMLParseError, e:
            warnings.warn(RuntimeWarning(
                "Python's built-in HTMLParser cannot parse the given document. This is not a bug in Beautiful Soup. The best solution is to install an external parser (lxml or html5lib), and use Beautiful Soup with that parser. See http://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-a-parser for help."))
            raise e

# Patch 3.2 versions of HTMLParser earlier than 3.2.3 to use some
# 3.2.3 code. This ensures they don't treat markup like <p></p> as a
# string.
#
# XXX This code can be removed once most Python 3 users are on 3.2.3.
if major == 3 and minor == 2 and not CONSTRUCTOR_TAKES_STRICT:
    import re
    attrfind_tolerant = re.compile(
        r'\s*((?<=[\'"\s])[^\s/>][^\s/=>]*)(\s*=+\s*'
        r'(\'[^\']*\'|"[^"]*"|(?![\'"])[^>\s]*))?')
    HTMLParserTreeBuilder.attrfind_tolerant = attrfind_tolerant

    locatestarttagend = re.compile(r"""
  <[a-zA-Z][-.a-zA-Z0-9:_]*          # tag name
  (?:\s+                             # whitespace before attribute name
    (?:[a-zA-Z_][-.:a-zA-Z0-9_]*     # attribute name
      (?:\s*=\s*                     # value indicator
        (?:'[^']*'                   # LITA-enclosed value
          |\"[^\"]*\"                # LIT-enclosed value
          |[^'\">\s]+                # bare value
         )
       )?
     )
   )*
  \s*                                # trailing whitespace
""", re.VERBOSE)
    BeautifulSoupHTMLParser.locatestarttagend = locatestarttagend

    from html.parser import tagfind, attrfind

    def parse_starttag(self, i):
        self.__starttag_text = None
        endpos = self.check_for_whole_start_tag(i)
        if endpos < 0:
            return endpos
        rawdata = self.rawdata
        self.__starttag_text = rawdata[i:endpos]

        # Now parse the data between i+1 and j into a tag and attrs
        attrs = []
        match = tagfind.match(rawdata, i+1)
        assert match, 'unexpected call to parse_starttag()'
        k = match.end()
        self.lasttag = tag = rawdata[i+1:k].lower()
        while k < endpos:
            if self.strict:
                m = attrfind.match(rawdata, k)
            else:
                m = attrfind_tolerant.match(rawdata, k)
            if not m:
                break
            attrname, rest, attrvalue = m.group(1, 2, 3)
            if not rest:
                attrvalue = None
            elif attrvalue[:1] == '\'' == attrvalue[-1:] or \
                 attrvalue[:1] == '"' == attrvalue[-1:]:
                attrvalue = attrvalue[1:-1]
            if attrvalue:
                attrvalue = self.unescape(attrvalue)
            attrs.append((attrname.lower(), attrvalue))
            k = m.end()

        end = rawdata[k:endpos].strip()
        if end not in (">", "/>"):
            lineno, offset = self.getpos()
            if "\n" in self.__starttag_text:
                lineno = lineno + self.__starttag_text.count("\n")
                offset = len(self.__starttag_text) \
                         - self.__starttag_text.rfind("\n")
            else:
                offset = offset + len(self.__starttag_text)
            if self.strict:
                self.error("junk characters in start tag: %r"
                           % (rawdata[k:endpos][:20],))
            self.handle_data(rawdata[i:endpos])
            return endpos
        if end.endswith('/>'):
            # XHTML-style empty tag: <span attr="value" />
            self.handle_startendtag(tag, attrs)
        else:
            self.handle_starttag(tag, attrs)
            if tag in self.CDATA_CONTENT_ELEMENTS:
                self.set_cdata_mode(tag)
        return endpos

    def set_cdata_mode(self, elem):
        self.cdata_elem = elem.lower()
        self.interesting = re.compile(r'</\s*%s\s*>' % self.cdata_elem, re.I)

    BeautifulSoupHTMLParser.parse_starttag = parse_starttag
    BeautifulSoupHTMLParser.set_cdata_mode = set_cdata_mode

    CONSTRUCTOR_TAKES_STRICT = True

########NEW FILE########
__FILENAME__ = _lxml
__all__ = [
    'LXMLTreeBuilderForXML',
    'LXMLTreeBuilder',
    ]

from io import BytesIO
from StringIO import StringIO
import collections
from lxml import etree
from bs4.element import Comment, Doctype, NamespacedAttribute
from bs4.builder import (
    FAST,
    HTML,
    HTMLTreeBuilder,
    PERMISSIVE,
    TreeBuilder,
    XML)
from bs4.dammit import UnicodeDammit

LXML = 'lxml'

class LXMLTreeBuilderForXML(TreeBuilder):
    DEFAULT_PARSER_CLASS = etree.XMLParser

    is_xml = True

    # Well, it's permissive by XML parser standards.
    features = [LXML, XML, FAST, PERMISSIVE]

    CHUNK_SIZE = 512

    # This namespace mapping is specified in the XML Namespace
    # standard.
    DEFAULT_NSMAPS = {'http://www.w3.org/XML/1998/namespace' : "xml"}

    @property
    def default_parser(self):
        # This can either return a parser object or a class, which
        # will be instantiated with default arguments.
        return etree.XMLParser(target=self, strip_cdata=False, recover=True)

    def __init__(self, parser=None, empty_element_tags=None):
        if empty_element_tags is not None:
            self.empty_element_tags = set(empty_element_tags)
        if parser is None:
            # Use the default parser.
            parser = self.default_parser
        if isinstance(parser, collections.Callable):
            # Instantiate the parser with default arguments
            parser = parser(target=self, strip_cdata=False)
        self.parser = parser
        self.soup = None
        self.nsmaps = [self.DEFAULT_NSMAPS]

    def _getNsTag(self, tag):
        # Split the namespace URL out of a fully-qualified lxml tag
        # name. Copied from lxml's src/lxml/sax.py.
        if tag[0] == '{':
            return tuple(tag[1:].split('}', 1))
        else:
            return (None, tag)

    def prepare_markup(self, markup, user_specified_encoding=None,
                       document_declared_encoding=None):
        """
        :return: A 3-tuple (markup, original encoding, encoding
        declared within markup).
        """
        if isinstance(markup, unicode):
            return markup, None, None, False

        try_encodings = [user_specified_encoding, document_declared_encoding]
        dammit = UnicodeDammit(markup, try_encodings, is_html=True)
        return (dammit.markup, dammit.original_encoding,
                dammit.declared_html_encoding,
                dammit.contains_replacement_characters)

    def feed(self, markup):
        if isinstance(markup, bytes):
            markup = BytesIO(markup)
        elif isinstance(markup, unicode):
            markup = StringIO(markup)
        # Call feed() at least once, even if the markup is empty,
        # or the parser won't be initialized.
        data = markup.read(self.CHUNK_SIZE)
        self.parser.feed(data)
        while data != '':
            # Now call feed() on the rest of the data, chunk by chunk.
            data = markup.read(self.CHUNK_SIZE)
            if data != '':
                self.parser.feed(data)
        self.parser.close()

    def close(self):
        self.nsmaps = [self.DEFAULT_NSMAPS]

    def start(self, name, attrs, nsmap={}):
        # Make sure attrs is a mutable dict--lxml may send an immutable dictproxy.
        attrs = dict(attrs)
        nsprefix = None
        # Invert each namespace map as it comes in.
        if len(self.nsmaps) > 1:
            # There are no new namespaces for this tag, but
            # non-default namespaces are in play, so we need a
            # separate tag stack to know when they end.
            self.nsmaps.append(None)
        elif len(nsmap) > 0:
            # A new namespace mapping has come into play.
            inverted_nsmap = dict((value, key) for key, value in nsmap.items())
            self.nsmaps.append(inverted_nsmap)
            # Also treat the namespace mapping as a set of attributes on the
            # tag, so we can recreate it later.
            attrs = attrs.copy()
            for prefix, namespace in nsmap.items():
                attribute = NamespacedAttribute(
                    "xmlns", prefix, "http://www.w3.org/2000/xmlns/")
                attrs[attribute] = namespace

        # Namespaces are in play. Find any attributes that came in
        # from lxml with namespaces attached to their names, and
        # turn then into NamespacedAttribute objects.
        new_attrs = {}
        for attr, value in attrs.items():
            namespace, attr = self._getNsTag(attr)
            if namespace is None:
                new_attrs[attr] = value
            else:
                nsprefix = self._prefix_for_namespace(namespace)
                attr = NamespacedAttribute(nsprefix, attr, namespace)
                new_attrs[attr] = value
        attrs = new_attrs

        namespace, name = self._getNsTag(name)
        nsprefix = self._prefix_for_namespace(namespace)
        self.soup.handle_starttag(name, namespace, nsprefix, attrs)

    def _prefix_for_namespace(self, namespace):
        """Find the currently active prefix for the given namespace."""
        if namespace is None:
            return None
        for inverted_nsmap in reversed(self.nsmaps):
            if inverted_nsmap is not None and namespace in inverted_nsmap:
                return inverted_nsmap[namespace]
        return None

    def end(self, name):
        self.soup.endData()
        completed_tag = self.soup.tagStack[-1]
        namespace, name = self._getNsTag(name)
        nsprefix = None
        if namespace is not None:
            for inverted_nsmap in reversed(self.nsmaps):
                if inverted_nsmap is not None and namespace in inverted_nsmap:
                    nsprefix = inverted_nsmap[namespace]
                    break
        self.soup.handle_endtag(name, nsprefix)
        if len(self.nsmaps) > 1:
            # This tag, or one of its parents, introduced a namespace
            # mapping, so pop it off the stack.
            self.nsmaps.pop()

    def pi(self, target, data):
        pass

    def data(self, content):
        self.soup.handle_data(content)

    def doctype(self, name, pubid, system):
        self.soup.endData()
        doctype = Doctype.for_name_and_ids(name, pubid, system)
        self.soup.object_was_parsed(doctype)

    def comment(self, content):
        "Handle comments as Comment objects."
        self.soup.endData()
        self.soup.handle_data(content)
        self.soup.endData(Comment)

    def test_fragment_to_document(self, fragment):
        """See `TreeBuilder`."""
        return u'<?xml version="1.0" encoding="utf-8"?>\n%s' % fragment


class LXMLTreeBuilder(HTMLTreeBuilder, LXMLTreeBuilderForXML):

    features = [LXML, HTML, FAST, PERMISSIVE]
    is_xml = False

    @property
    def default_parser(self):
        return etree.HTMLParser

    def feed(self, markup):
        self.parser.feed(markup)
        self.parser.close()

    def test_fragment_to_document(self, fragment):
        """See `TreeBuilder`."""
        return u'<html><body>%s</body></html>' % fragment

########NEW FILE########
__FILENAME__ = dammit
# -*- coding: utf-8 -*-
"""Beautiful Soup bonus library: Unicode, Dammit

This class forces XML data into a standard format (usually to UTF-8 or
Unicode).  It is heavily based on code from Mark Pilgrim's Universal
Feed Parser. It does not rewrite the XML or HTML to reflect a new
encoding; that's the tree builder's job.
"""

import codecs
from htmlentitydefs import codepoint2name
import re
import logging

# Import a library to autodetect character encodings.
chardet_type = None
try:
    # First try the fast C implementation.
    #  PyPI package: cchardet
    import cchardet
    def chardet_dammit(s):
        return cchardet.detect(s)['encoding']
except ImportError:
    try:
        # Fall back to the pure Python implementation
        #  Debian package: python-chardet
        #  PyPI package: chardet
        import chardet
        def chardet_dammit(s):
            return chardet.detect(s)['encoding']
        #import chardet.constants
        #chardet.constants._debug = 1
    except ImportError:
        # No chardet available.
        def chardet_dammit(s):
            return None

# Available from http://cjkpython.i18n.org/.
try:
    import iconv_codec
except ImportError:
    pass

xml_encoding_re = re.compile(
    '^<\?.*encoding=[\'"](.*?)[\'"].*\?>'.encode(), re.I)
html_meta_re = re.compile(
    '<\s*meta[^>]+charset\s*=\s*["\']?([^>]*?)[ /;\'">]'.encode(), re.I)

class EntitySubstitution(object):

    """Substitute XML or HTML entities for the corresponding characters."""

    def _populate_class_variables():
        lookup = {}
        reverse_lookup = {}
        characters_for_re = []
        for codepoint, name in list(codepoint2name.items()):
            character = unichr(codepoint)
            if codepoint != 34:
                # There's no point in turning the quotation mark into
                # &quot;, unless it happens within an attribute value, which
                # is handled elsewhere.
                characters_for_re.append(character)
                lookup[character] = name
            # But we do want to turn &quot; into the quotation mark.
            reverse_lookup[name] = character
        re_definition = "[%s]" % "".join(characters_for_re)
        return lookup, reverse_lookup, re.compile(re_definition)
    (CHARACTER_TO_HTML_ENTITY, HTML_ENTITY_TO_CHARACTER,
     CHARACTER_TO_HTML_ENTITY_RE) = _populate_class_variables()

    CHARACTER_TO_XML_ENTITY = {
        "'": "apos",
        '"': "quot",
        "&": "amp",
        "<": "lt",
        ">": "gt",
        }

    BARE_AMPERSAND_OR_BRACKET = re.compile("([<>]|"
                                           "&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)"
                                           ")")

    AMPERSAND_OR_BRACKET = re.compile("([<>&])")

    @classmethod
    def _substitute_html_entity(cls, matchobj):
        entity = cls.CHARACTER_TO_HTML_ENTITY.get(matchobj.group(0))
        return "&%s;" % entity

    @classmethod
    def _substitute_xml_entity(cls, matchobj):
        """Used with a regular expression to substitute the
        appropriate XML entity for an XML special character."""
        entity = cls.CHARACTER_TO_XML_ENTITY[matchobj.group(0)]
        return "&%s;" % entity

    @classmethod
    def quoted_attribute_value(self, value):
        """Make a value into a quoted XML attribute, possibly escaping it.

         Most strings will be quoted using double quotes.

          Bob's Bar -> "Bob's Bar"

         If a string contains double quotes, it will be quoted using
         single quotes.

          Welcome to "my bar" -> 'Welcome to "my bar"'

         If a string contains both single and double quotes, the
         double quotes will be escaped, and the string will be quoted
         using double quotes.

          Welcome to "Bob's Bar" -> "Welcome to &quot;Bob's bar&quot;
        """
        quote_with = '"'
        if '"' in value:
            if "'" in value:
                # The string contains both single and double
                # quotes.  Turn the double quotes into
                # entities. We quote the double quotes rather than
                # the single quotes because the entity name is
                # "&quot;" whether this is HTML or XML.  If we
                # quoted the single quotes, we'd have to decide
                # between &apos; and &squot;.
                replace_with = "&quot;"
                value = value.replace('"', replace_with)
            else:
                # There are double quotes but no single quotes.
                # We can use single quotes to quote the attribute.
                quote_with = "'"
        return quote_with + value + quote_with

    @classmethod
    def substitute_xml(cls, value, make_quoted_attribute=False):
        """Substitute XML entities for special XML characters.

        :param value: A string to be substituted. The less-than sign
          will become &lt;, the greater-than sign will become &gt;,
          and any ampersands will become &amp;. If you want ampersands
          that appear to be part of an entity definition to be left
          alone, use substitute_xml_containing_entities() instead.

        :param make_quoted_attribute: If True, then the string will be
         quoted, as befits an attribute value.
        """
        # Escape angle brackets and ampersands.
        value = cls.AMPERSAND_OR_BRACKET.sub(
            cls._substitute_xml_entity, value)

        if make_quoted_attribute:
            value = cls.quoted_attribute_value(value)
        return value

    @classmethod
    def substitute_xml_containing_entities(
        cls, value, make_quoted_attribute=False):
        """Substitute XML entities for special XML characters.

        :param value: A string to be substituted. The less-than sign will
          become &lt;, the greater-than sign will become &gt;, and any
          ampersands that are not part of an entity defition will
          become &amp;.

        :param make_quoted_attribute: If True, then the string will be
         quoted, as befits an attribute value.
        """
        # Escape angle brackets, and ampersands that aren't part of
        # entities.
        value = cls.BARE_AMPERSAND_OR_BRACKET.sub(
            cls._substitute_xml_entity, value)

        if make_quoted_attribute:
            value = cls.quoted_attribute_value(value)
        return value


    @classmethod
    def substitute_html(cls, s):
        """Replace certain Unicode characters with named HTML entities.

        This differs from data.encode(encoding, 'xmlcharrefreplace')
        in that the goal is to make the result more readable (to those
        with ASCII displays) rather than to recover from
        errors. There's absolutely nothing wrong with a UTF-8 string
        containg a LATIN SMALL LETTER E WITH ACUTE, but replacing that
        character with "&eacute;" will make it more readable to some
        people.
        """
        return cls.CHARACTER_TO_HTML_ENTITY_RE.sub(
            cls._substitute_html_entity, s)


class UnicodeDammit:
    """A class for detecting the encoding of a *ML document and
    converting it to a Unicode string. If the source encoding is
    windows-1252, can replace MS smart quotes with their HTML or XML
    equivalents."""

    # This dictionary maps commonly seen values for "charset" in HTML
    # meta tags to the corresponding Python codec names. It only covers
    # values that aren't in Python's aliases and can't be determined
    # by the heuristics in find_codec.
    CHARSET_ALIASES = {"macintosh": "mac-roman",
                       "x-sjis": "shift-jis"}

    ENCODINGS_WITH_SMART_QUOTES = [
        "windows-1252",
        "iso-8859-1",
        "iso-8859-2",
        ]

    def __init__(self, markup, override_encodings=[],
                 smart_quotes_to=None, is_html=False):
        self.declared_html_encoding = None
        self.smart_quotes_to = smart_quotes_to
        self.tried_encodings = []
        self.contains_replacement_characters = False

        if markup == '' or isinstance(markup, unicode):
            self.markup = markup
            self.unicode_markup = unicode(markup)
            self.original_encoding = None
            return

        new_markup, document_encoding, sniffed_encoding = \
            self._detectEncoding(markup, is_html)
        self.markup = new_markup

        u = None
        if new_markup != markup:
            # _detectEncoding modified the markup, then converted it to
            # Unicode and then to UTF-8. So convert it from UTF-8.
            u = self._convert_from("utf8")
            self.original_encoding = sniffed_encoding

        if not u:
            for proposed_encoding in (
                override_encodings + [document_encoding, sniffed_encoding]):
                if proposed_encoding is not None:
                    u = self._convert_from(proposed_encoding)
                    if u:
                        break

        # If no luck and we have auto-detection library, try that:
        if not u and not isinstance(self.markup, unicode):
            u = self._convert_from(chardet_dammit(self.markup))

        # As a last resort, try utf-8 and windows-1252:
        if not u:
            for proposed_encoding in ("utf-8", "windows-1252"):
                u = self._convert_from(proposed_encoding)
                if u:
                    break

        # As an absolute last resort, try the encodings again with
        # character replacement.
        if not u:
            for proposed_encoding in (
                override_encodings + [
                    document_encoding, sniffed_encoding, "utf-8", "windows-1252"]):
                if proposed_encoding != "ascii":
                    u = self._convert_from(proposed_encoding, "replace")
                if u is not None:
                    logging.warning(
                            "Some characters could not be decoded, and were "
                            "replaced with REPLACEMENT CHARACTER.")
                    self.contains_replacement_characters = True
                    break

        # We could at this point force it to ASCII, but that would
        # destroy so much data that I think giving up is better
        self.unicode_markup = u
        if not u:
            self.original_encoding = None

    def _sub_ms_char(self, match):
        """Changes a MS smart quote character to an XML or HTML
        entity, or an ASCII character."""
        orig = match.group(1)
        if self.smart_quotes_to == 'ascii':
            sub = self.MS_CHARS_TO_ASCII.get(orig).encode()
        else:
            sub = self.MS_CHARS.get(orig)
            if type(sub) == tuple:
                if self.smart_quotes_to == 'xml':
                    sub = '&#x'.encode() + sub[1].encode() + ';'.encode()
                else:
                    sub = '&'.encode() + sub[0].encode() + ';'.encode()
            else:
                sub = sub.encode()
        return sub

    def _convert_from(self, proposed, errors="strict"):
        proposed = self.find_codec(proposed)
        if not proposed or (proposed, errors) in self.tried_encodings:
            return None
        self.tried_encodings.append((proposed, errors))
        markup = self.markup
        # Convert smart quotes to HTML if coming from an encoding
        # that might have them.
        if (self.smart_quotes_to is not None
            and proposed.lower() in self.ENCODINGS_WITH_SMART_QUOTES):
            smart_quotes_re = b"([\x80-\x9f])"
            smart_quotes_compiled = re.compile(smart_quotes_re)
            markup = smart_quotes_compiled.sub(self._sub_ms_char, markup)

        try:
            #print "Trying to convert document to %s (errors=%s)" % (
            #    proposed, errors)
            u = self._to_unicode(markup, proposed, errors)
            self.markup = u
            self.original_encoding = proposed
        except Exception as e:
            #print "That didn't work!"
            #print e
            return None
        #print "Correct encoding: %s" % proposed
        return self.markup

    def _to_unicode(self, data, encoding, errors="strict"):
        '''Given a string and its encoding, decodes the string into Unicode.
        %encoding is a string recognized by encodings.aliases'''

        # strip Byte Order Mark (if present)
        if (len(data) >= 4) and (data[:2] == '\xfe\xff') \
               and (data[2:4] != '\x00\x00'):
            encoding = 'utf-16be'
            data = data[2:]
        elif (len(data) >= 4) and (data[:2] == '\xff\xfe') \
                 and (data[2:4] != '\x00\x00'):
            encoding = 'utf-16le'
            data = data[2:]
        elif data[:3] == '\xef\xbb\xbf':
            encoding = 'utf-8'
            data = data[3:]
        elif data[:4] == '\x00\x00\xfe\xff':
            encoding = 'utf-32be'
            data = data[4:]
        elif data[:4] == '\xff\xfe\x00\x00':
            encoding = 'utf-32le'
            data = data[4:]
        newdata = unicode(data, encoding, errors)
        return newdata

    def _detectEncoding(self, xml_data, is_html=False):
        """Given a document, tries to detect its XML encoding."""
        xml_encoding = sniffed_xml_encoding = None
        try:
            if xml_data[:4] == b'\x4c\x6f\xa7\x94':
                # EBCDIC
                xml_data = self._ebcdic_to_ascii(xml_data)
            elif xml_data[:4] == b'\x00\x3c\x00\x3f':
                # UTF-16BE
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data, 'utf-16be').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == b'\xfe\xff') \
                     and (xml_data[2:4] != b'\x00\x00'):
                # UTF-16BE with BOM
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data[2:], 'utf-16be').encode('utf-8')
            elif xml_data[:4] == b'\x3c\x00\x3f\x00':
                # UTF-16LE
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data, 'utf-16le').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == b'\xff\xfe') and \
                     (xml_data[2:4] != b'\x00\x00'):
                # UTF-16LE with BOM
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data[2:], 'utf-16le').encode('utf-8')
            elif xml_data[:4] == b'\x00\x00\x00\x3c':
                # UTF-32BE
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data, 'utf-32be').encode('utf-8')
            elif xml_data[:4] == b'\x3c\x00\x00\x00':
                # UTF-32LE
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data, 'utf-32le').encode('utf-8')
            elif xml_data[:4] == b'\x00\x00\xfe\xff':
                # UTF-32BE with BOM
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data[4:], 'utf-32be').encode('utf-8')
            elif xml_data[:4] == b'\xff\xfe\x00\x00':
                # UTF-32LE with BOM
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data[4:], 'utf-32le').encode('utf-8')
            elif xml_data[:3] == b'\xef\xbb\xbf':
                # UTF-8 with BOM
                sniffed_xml_encoding = 'utf-8'
                xml_data = unicode(xml_data[3:], 'utf-8').encode('utf-8')
            else:
                sniffed_xml_encoding = 'ascii'
                pass
        except:
            xml_encoding_match = None
        xml_encoding_match = xml_encoding_re.match(xml_data)
        if not xml_encoding_match and is_html:
            xml_encoding_match = html_meta_re.search(xml_data)
        if xml_encoding_match is not None:
            xml_encoding = xml_encoding_match.groups()[0].decode(
                'ascii').lower()
            if is_html:
                self.declared_html_encoding = xml_encoding
            if sniffed_xml_encoding and \
               (xml_encoding in ('iso-10646-ucs-2', 'ucs-2', 'csunicode',
                                 'iso-10646-ucs-4', 'ucs-4', 'csucs4',
                                 'utf-16', 'utf-32', 'utf_16', 'utf_32',
                                 'utf16', 'u16')):
                xml_encoding = sniffed_xml_encoding
        return xml_data, xml_encoding, sniffed_xml_encoding

    def find_codec(self, charset):
        return self._codec(self.CHARSET_ALIASES.get(charset, charset)) \
               or (charset and self._codec(charset.replace("-", ""))) \
               or (charset and self._codec(charset.replace("-", "_"))) \
               or charset

    def _codec(self, charset):
        if not charset:
            return charset
        codec = None
        try:
            codecs.lookup(charset)
            codec = charset
        except (LookupError, ValueError):
            pass
        return codec

    EBCDIC_TO_ASCII_MAP = None

    def _ebcdic_to_ascii(self, s):
        c = self.__class__
        if not c.EBCDIC_TO_ASCII_MAP:
            emap = (0,1,2,3,156,9,134,127,151,141,142,11,12,13,14,15,
                    16,17,18,19,157,133,8,135,24,25,146,143,28,29,30,31,
                    128,129,130,131,132,10,23,27,136,137,138,139,140,5,6,7,
                    144,145,22,147,148,149,150,4,152,153,154,155,20,21,158,26,
                    32,160,161,162,163,164,165,166,167,168,91,46,60,40,43,33,
                    38,169,170,171,172,173,174,175,176,177,93,36,42,41,59,94,
                    45,47,178,179,180,181,182,183,184,185,124,44,37,95,62,63,
                    186,187,188,189,190,191,192,193,194,96,58,35,64,39,61,34,
                    195,97,98,99,100,101,102,103,104,105,196,197,198,199,200,
                    201,202,106,107,108,109,110,111,112,113,114,203,204,205,
                    206,207,208,209,126,115,116,117,118,119,120,121,122,210,
                    211,212,213,214,215,216,217,218,219,220,221,222,223,224,
                    225,226,227,228,229,230,231,123,65,66,67,68,69,70,71,72,
                    73,232,233,234,235,236,237,125,74,75,76,77,78,79,80,81,
                    82,238,239,240,241,242,243,92,159,83,84,85,86,87,88,89,
                    90,244,245,246,247,248,249,48,49,50,51,52,53,54,55,56,57,
                    250,251,252,253,254,255)
            import string
            c.EBCDIC_TO_ASCII_MAP = string.maketrans(
            ''.join(map(chr, list(range(256)))), ''.join(map(chr, emap)))
        return s.translate(c.EBCDIC_TO_ASCII_MAP)

    # A partial mapping of ISO-Latin-1 to HTML entities/XML numeric entities.
    MS_CHARS = {b'\x80': ('euro', '20AC'),
                b'\x81': ' ',
                b'\x82': ('sbquo', '201A'),
                b'\x83': ('fnof', '192'),
                b'\x84': ('bdquo', '201E'),
                b'\x85': ('hellip', '2026'),
                b'\x86': ('dagger', '2020'),
                b'\x87': ('Dagger', '2021'),
                b'\x88': ('circ', '2C6'),
                b'\x89': ('permil', '2030'),
                b'\x8A': ('Scaron', '160'),
                b'\x8B': ('lsaquo', '2039'),
                b'\x8C': ('OElig', '152'),
                b'\x8D': '?',
                b'\x8E': ('#x17D', '17D'),
                b'\x8F': '?',
                b'\x90': '?',
                b'\x91': ('lsquo', '2018'),
                b'\x92': ('rsquo', '2019'),
                b'\x93': ('ldquo', '201C'),
                b'\x94': ('rdquo', '201D'),
                b'\x95': ('bull', '2022'),
                b'\x96': ('ndash', '2013'),
                b'\x97': ('mdash', '2014'),
                b'\x98': ('tilde', '2DC'),
                b'\x99': ('trade', '2122'),
                b'\x9a': ('scaron', '161'),
                b'\x9b': ('rsaquo', '203A'),
                b'\x9c': ('oelig', '153'),
                b'\x9d': '?',
                b'\x9e': ('#x17E', '17E'),
                b'\x9f': ('Yuml', ''),}

    # A parochial partial mapping of ISO-Latin-1 to ASCII. Contains
    # horrors like stripping diacritical marks to turn á into a, but also
    # contains non-horrors like turning “ into ".
    MS_CHARS_TO_ASCII = {
        b'\x80' : 'EUR',
        b'\x81' : ' ',
        b'\x82' : ',',
        b'\x83' : 'f',
        b'\x84' : ',,',
        b'\x85' : '...',
        b'\x86' : '+',
        b'\x87' : '++',
        b'\x88' : '^',
        b'\x89' : '%',
        b'\x8a' : 'S',
        b'\x8b' : '<',
        b'\x8c' : 'OE',
        b'\x8d' : '?',
        b'\x8e' : 'Z',
        b'\x8f' : '?',
        b'\x90' : '?',
        b'\x91' : "'",
        b'\x92' : "'",
        b'\x93' : '"',
        b'\x94' : '"',
        b'\x95' : '*',
        b'\x96' : '-',
        b'\x97' : '--',
        b'\x98' : '~',
        b'\x99' : '(TM)',
        b'\x9a' : 's',
        b'\x9b' : '>',
        b'\x9c' : 'oe',
        b'\x9d' : '?',
        b'\x9e' : 'z',
        b'\x9f' : 'Y',
        b'\xa0' : ' ',
        b'\xa1' : '!',
        b'\xa2' : 'c',
        b'\xa3' : 'GBP',
        b'\xa4' : '$', #This approximation is especially parochial--this is the
                       #generic currency symbol.
        b'\xa5' : 'YEN',
        b'\xa6' : '|',
        b'\xa7' : 'S',
        b'\xa8' : '..',
        b'\xa9' : '',
        b'\xaa' : '(th)',
        b'\xab' : '<<',
        b'\xac' : '!',
        b'\xad' : ' ',
        b'\xae' : '(R)',
        b'\xaf' : '-',
        b'\xb0' : 'o',
        b'\xb1' : '+-',
        b'\xb2' : '2',
        b'\xb3' : '3',
        b'\xb4' : ("'", 'acute'),
        b'\xb5' : 'u',
        b'\xb6' : 'P',
        b'\xb7' : '*',
        b'\xb8' : ',',
        b'\xb9' : '1',
        b'\xba' : '(th)',
        b'\xbb' : '>>',
        b'\xbc' : '1/4',
        b'\xbd' : '1/2',
        b'\xbe' : '3/4',
        b'\xbf' : '?',
        b'\xc0' : 'A',
        b'\xc1' : 'A',
        b'\xc2' : 'A',
        b'\xc3' : 'A',
        b'\xc4' : 'A',
        b'\xc5' : 'A',
        b'\xc6' : 'AE',
        b'\xc7' : 'C',
        b'\xc8' : 'E',
        b'\xc9' : 'E',
        b'\xca' : 'E',
        b'\xcb' : 'E',
        b'\xcc' : 'I',
        b'\xcd' : 'I',
        b'\xce' : 'I',
        b'\xcf' : 'I',
        b'\xd0' : 'D',
        b'\xd1' : 'N',
        b'\xd2' : 'O',
        b'\xd3' : 'O',
        b'\xd4' : 'O',
        b'\xd5' : 'O',
        b'\xd6' : 'O',
        b'\xd7' : '*',
        b'\xd8' : 'O',
        b'\xd9' : 'U',
        b'\xda' : 'U',
        b'\xdb' : 'U',
        b'\xdc' : 'U',
        b'\xdd' : 'Y',
        b'\xde' : 'b',
        b'\xdf' : 'B',
        b'\xe0' : 'a',
        b'\xe1' : 'a',
        b'\xe2' : 'a',
        b'\xe3' : 'a',
        b'\xe4' : 'a',
        b'\xe5' : 'a',
        b'\xe6' : 'ae',
        b'\xe7' : 'c',
        b'\xe8' : 'e',
        b'\xe9' : 'e',
        b'\xea' : 'e',
        b'\xeb' : 'e',
        b'\xec' : 'i',
        b'\xed' : 'i',
        b'\xee' : 'i',
        b'\xef' : 'i',
        b'\xf0' : 'o',
        b'\xf1' : 'n',
        b'\xf2' : 'o',
        b'\xf3' : 'o',
        b'\xf4' : 'o',
        b'\xf5' : 'o',
        b'\xf6' : 'o',
        b'\xf7' : '/',
        b'\xf8' : 'o',
        b'\xf9' : 'u',
        b'\xfa' : 'u',
        b'\xfb' : 'u',
        b'\xfc' : 'u',
        b'\xfd' : 'y',
        b'\xfe' : 'b',
        b'\xff' : 'y',
        }

    # A map used when removing rogue Windows-1252/ISO-8859-1
    # characters in otherwise UTF-8 documents.
    #
    # Note that \x81, \x8d, \x8f, \x90, and \x9d are undefined in
    # Windows-1252.
    WINDOWS_1252_TO_UTF8 = {
        0x80 : b'\xe2\x82\xac', # €
        0x82 : b'\xe2\x80\x9a', # ‚
        0x83 : b'\xc6\x92',     # ƒ
        0x84 : b'\xe2\x80\x9e', # „
        0x85 : b'\xe2\x80\xa6', # …
        0x86 : b'\xe2\x80\xa0', # †
        0x87 : b'\xe2\x80\xa1', # ‡
        0x88 : b'\xcb\x86',     # ˆ
        0x89 : b'\xe2\x80\xb0', # ‰
        0x8a : b'\xc5\xa0',     # Š
        0x8b : b'\xe2\x80\xb9', # ‹
        0x8c : b'\xc5\x92',     # Œ
        0x8e : b'\xc5\xbd',     # Ž
        0x91 : b'\xe2\x80\x98', # ‘
        0x92 : b'\xe2\x80\x99', # ’
        0x93 : b'\xe2\x80\x9c', # “
        0x94 : b'\xe2\x80\x9d', # ”
        0x95 : b'\xe2\x80\xa2', # •
        0x96 : b'\xe2\x80\x93', # –
        0x97 : b'\xe2\x80\x94', # —
        0x98 : b'\xcb\x9c',     # ˜
        0x99 : b'\xe2\x84\xa2', # ™
        0x9a : b'\xc5\xa1',     # š
        0x9b : b'\xe2\x80\xba', # ›
        0x9c : b'\xc5\x93',     # œ
        0x9e : b'\xc5\xbe',     # ž
        0x9f : b'\xc5\xb8',     # Ÿ
        0xa0 : b'\xc2\xa0',     #  
        0xa1 : b'\xc2\xa1',     # ¡
        0xa2 : b'\xc2\xa2',     # ¢
        0xa3 : b'\xc2\xa3',     # £
        0xa4 : b'\xc2\xa4',     # ¤
        0xa5 : b'\xc2\xa5',     # ¥
        0xa6 : b'\xc2\xa6',     # ¦
        0xa7 : b'\xc2\xa7',     # §
        0xa8 : b'\xc2\xa8',     # ¨
        0xa9 : b'\xc2\xa9',     # ©
        0xaa : b'\xc2\xaa',     # ª
        0xab : b'\xc2\xab',     # «
        0xac : b'\xc2\xac',     # ¬
        0xad : b'\xc2\xad',     # ­
        0xae : b'\xc2\xae',     # ®
        0xaf : b'\xc2\xaf',     # ¯
        0xb0 : b'\xc2\xb0',     # °
        0xb1 : b'\xc2\xb1',     # ±
        0xb2 : b'\xc2\xb2',     # ²
        0xb3 : b'\xc2\xb3',     # ³
        0xb4 : b'\xc2\xb4',     # ´
        0xb5 : b'\xc2\xb5',     # µ
        0xb6 : b'\xc2\xb6',     # ¶
        0xb7 : b'\xc2\xb7',     # ·
        0xb8 : b'\xc2\xb8',     # ¸
        0xb9 : b'\xc2\xb9',     # ¹
        0xba : b'\xc2\xba',     # º
        0xbb : b'\xc2\xbb',     # »
        0xbc : b'\xc2\xbc',     # ¼
        0xbd : b'\xc2\xbd',     # ½
        0xbe : b'\xc2\xbe',     # ¾
        0xbf : b'\xc2\xbf',     # ¿
        0xc0 : b'\xc3\x80',     # À
        0xc1 : b'\xc3\x81',     # Á
        0xc2 : b'\xc3\x82',     # Â
        0xc3 : b'\xc3\x83',     # Ã
        0xc4 : b'\xc3\x84',     # Ä
        0xc5 : b'\xc3\x85',     # Å
        0xc6 : b'\xc3\x86',     # Æ
        0xc7 : b'\xc3\x87',     # Ç
        0xc8 : b'\xc3\x88',     # È
        0xc9 : b'\xc3\x89',     # É
        0xca : b'\xc3\x8a',     # Ê
        0xcb : b'\xc3\x8b',     # Ë
        0xcc : b'\xc3\x8c',     # Ì
        0xcd : b'\xc3\x8d',     # Í
        0xce : b'\xc3\x8e',     # Î
        0xcf : b'\xc3\x8f',     # Ï
        0xd0 : b'\xc3\x90',     # Ð
        0xd1 : b'\xc3\x91',     # Ñ
        0xd2 : b'\xc3\x92',     # Ò
        0xd3 : b'\xc3\x93',     # Ó
        0xd4 : b'\xc3\x94',     # Ô
        0xd5 : b'\xc3\x95',     # Õ
        0xd6 : b'\xc3\x96',     # Ö
        0xd7 : b'\xc3\x97',     # ×
        0xd8 : b'\xc3\x98',     # Ø
        0xd9 : b'\xc3\x99',     # Ù
        0xda : b'\xc3\x9a',     # Ú
        0xdb : b'\xc3\x9b',     # Û
        0xdc : b'\xc3\x9c',     # Ü
        0xdd : b'\xc3\x9d',     # Ý
        0xde : b'\xc3\x9e',     # Þ
        0xdf : b'\xc3\x9f',     # ß
        0xe0 : b'\xc3\xa0',     # à
        0xe1 : b'\xa1',     # á
        0xe2 : b'\xc3\xa2',     # â
        0xe3 : b'\xc3\xa3',     # ã
        0xe4 : b'\xc3\xa4',     # ä
        0xe5 : b'\xc3\xa5',     # å
        0xe6 : b'\xc3\xa6',     # æ
        0xe7 : b'\xc3\xa7',     # ç
        0xe8 : b'\xc3\xa8',     # è
        0xe9 : b'\xc3\xa9',     # é
        0xea : b'\xc3\xaa',     # ê
        0xeb : b'\xc3\xab',     # ë
        0xec : b'\xc3\xac',     # ì
        0xed : b'\xc3\xad',     # í
        0xee : b'\xc3\xae',     # î
        0xef : b'\xc3\xaf',     # ï
        0xf0 : b'\xc3\xb0',     # ð
        0xf1 : b'\xc3\xb1',     # ñ
        0xf2 : b'\xc3\xb2',     # ò
        0xf3 : b'\xc3\xb3',     # ó
        0xf4 : b'\xc3\xb4',     # ô
        0xf5 : b'\xc3\xb5',     # õ
        0xf6 : b'\xc3\xb6',     # ö
        0xf7 : b'\xc3\xb7',     # ÷
        0xf8 : b'\xc3\xb8',     # ø
        0xf9 : b'\xc3\xb9',     # ù
        0xfa : b'\xc3\xba',     # ú
        0xfb : b'\xc3\xbb',     # û
        0xfc : b'\xc3\xbc',     # ü
        0xfd : b'\xc3\xbd',     # ý
        0xfe : b'\xc3\xbe',     # þ
        }

    MULTIBYTE_MARKERS_AND_SIZES = [
        (0xc2, 0xdf, 2), # 2-byte characters start with a byte C2-DF
        (0xe0, 0xef, 3), # 3-byte characters start with E0-EF
        (0xf0, 0xf4, 4), # 4-byte characters start with F0-F4
        ]

    FIRST_MULTIBYTE_MARKER = MULTIBYTE_MARKERS_AND_SIZES[0][0]
    LAST_MULTIBYTE_MARKER = MULTIBYTE_MARKERS_AND_SIZES[-1][1]

    @classmethod
    def detwingle(cls, in_bytes, main_encoding="utf8",
                  embedded_encoding="windows-1252"):
        """Fix characters from one encoding embedded in some other encoding.

        Currently the only situation supported is Windows-1252 (or its
        subset ISO-8859-1), embedded in UTF-8.

        The input must be a bytestring. If you've already converted
        the document to Unicode, you're too late.

        The output is a bytestring in which `embedded_encoding`
        characters have been converted to their `main_encoding`
        equivalents.
        """
        if embedded_encoding.replace('_', '-').lower() not in (
            'windows-1252', 'windows_1252'):
            raise NotImplementedError(
                "Windows-1252 and ISO-8859-1 are the only currently supported "
                "embedded encodings.")

        if main_encoding.lower() not in ('utf8', 'utf-8'):
            raise NotImplementedError(
                "UTF-8 is the only currently supported main encoding.")

        byte_chunks = []

        chunk_start = 0
        pos = 0
        while pos < len(in_bytes):
            byte = in_bytes[pos]
            if not isinstance(byte, int):
                # Python 2.x
                byte = ord(byte)
            if (byte >= cls.FIRST_MULTIBYTE_MARKER
                and byte <= cls.LAST_MULTIBYTE_MARKER):
                # This is the start of a UTF-8 multibyte character. Skip
                # to the end.
                for start, end, size in cls.MULTIBYTE_MARKERS_AND_SIZES:
                    if byte >= start and byte <= end:
                        pos += size
                        break
            elif byte >= 0x80 and byte in cls.WINDOWS_1252_TO_UTF8:
                # We found a Windows-1252 character!
                # Save the string up to this point as a chunk.
                byte_chunks.append(in_bytes[chunk_start:pos])

                # Now translate the Windows-1252 character into UTF-8
                # and add it as another, one-byte chunk.
                byte_chunks.append(cls.WINDOWS_1252_TO_UTF8[byte])
                pos += 1
                chunk_start = pos
            else:
                # Go on to the next character.
                pos += 1
        if chunk_start == 0:
            # The string is unchanged.
            return in_bytes
        else:
            # Store the final chunk.
            byte_chunks.append(in_bytes[chunk_start:])
        return b''.join(byte_chunks)


########NEW FILE########
__FILENAME__ = diagnose
"""Diagnostic functions, mainly for use when doing tech support."""
from StringIO import StringIO
from HTMLParser import HTMLParser
from bs4 import BeautifulSoup, __version__
from bs4.builder import builder_registry
import os
import random
import time
import traceback
import sys
import cProfile

def diagnose(data):
    """Diagnostic suite for isolating common problems."""
    print "Diagnostic running on Beautiful Soup %s" % __version__
    print "Python version %s" % sys.version

    basic_parsers = ["html.parser", "html5lib", "lxml"]
    for name in basic_parsers:
        for builder in builder_registry.builders:
            if name in builder.features:
                break
        else:
            basic_parsers.remove(name)
            print (
                "I noticed that %s is not installed. Installing it may help." %
                name)

    if 'lxml' in basic_parsers:
        basic_parsers.append(["lxml", "xml"])
        from lxml import etree
        print "Found lxml version %s" % ".".join(map(str,etree.LXML_VERSION))

    if 'html5lib' in basic_parsers:
        import html5lib
        print "Found html5lib version %s" % html5lib.__version__

    if hasattr(data, 'read'):
        data = data.read()
    elif os.path.exists(data):
        print '"%s" looks like a filename. Reading data from the file.' % data
        data = open(data).read()
    elif data.startswith("http:") or data.startswith("https:"):
        print '"%s" looks like a URL. Beautiful Soup is not an HTTP client.' % data
        print "You need to use some other library to get the document behind the URL, and feed that document to Beautiful Soup."
        return
    print

    for parser in basic_parsers:
        print "Trying to parse your markup with %s" % parser
        success = False
        try:
            soup = BeautifulSoup(data, parser)
            success = True
        except Exception, e:
            print "%s could not parse the markup." % parser
            traceback.print_exc()
        if success:
            print "Here's what %s did with the markup:" % parser
            print soup.prettify()

        print "-" * 80

def lxml_trace(data, html=True):
    """Print out the lxml events that occur during parsing.

    This lets you see how lxml parses a document when no Beautiful
    Soup code is running.
    """
    from lxml import etree
    for event, element in etree.iterparse(StringIO(data), html=html):
        print("%s, %4s, %s" % (event, element.tag, element.text))

class AnnouncingParser(HTMLParser):
    """Announces HTMLParser parse events, without doing anything else."""

    def _p(self, s):
        print(s)

    def handle_starttag(self, name, attrs):
        self._p("%s START" % name)

    def handle_endtag(self, name):
        self._p("%s END" % name)

    def handle_data(self, data):
        self._p("%s DATA" % data)

    def handle_charref(self, name):
        self._p("%s CHARREF" % name)

    def handle_entityref(self, name):
        self._p("%s ENTITYREF" % name)

    def handle_comment(self, data):
        self._p("%s COMMENT" % data)

    def handle_decl(self, data):
        self._p("%s DECL" % data)

    def unknown_decl(self, data):
        self._p("%s UNKNOWN-DECL" % data)

    def handle_pi(self, data):
        self._p("%s PI" % data)

def htmlparser_trace(data):
    """Print out the HTMLParser events that occur during parsing.

    This lets you see how HTMLParser parses a document when no
    Beautiful Soup code is running.
    """
    parser = AnnouncingParser()
    parser.feed(data)

_vowels = "aeiou"
_consonants = "bcdfghjklmnpqrstvwxyz"

def rword(length=5):
    "Generate a random word-like string."
    s = ''
    for i in range(length):
        if i % 2 == 0:
            t = _consonants
        else:
            t = _vowels
        s += random.choice(t)
    return s

def rsentence(length=4):
    "Generate a random sentence-like string."
    return " ".join(rword(random.randint(4,9)) for i in range(length))
        
def rdoc(num_elements=1000):
    """Randomly generate an invalid HTML document."""
    tag_names = ['p', 'div', 'span', 'i', 'b', 'script', 'table']
    elements = []
    for i in range(num_elements):
        choice = random.randint(0,3)
        if choice == 0:
            # New tag.
            tag_name = random.choice(tag_names)
            elements.append("<%s>" % tag_name)
        elif choice == 1:
            elements.append(rsentence(random.randint(1,4)))
        elif choice == 2:
            # Close a tag.
            tag_name = random.choice(tag_names)
            elements.append("</%s>" % tag_name)
    return "<html>" + "\n".join(elements) + "</html>"

def benchmark_parsers(num_elements=100000):
    """Very basic head-to-head performance benchmark."""
    print "Comparative parser benchmark on Beautiful Soup %s" % __version__
    data = rdoc(num_elements)
    print "Generated a large invalid HTML document (%d bytes)." % len(data)
    
    for parser in ["lxml", ["lxml", "html"], "html5lib", "html.parser"]:
        success = False
        try:
            a = time.time()
            soup = BeautifulSoup(data, parser)
            b = time.time()
            success = True
        except Exception, e:
            print "%s could not parse the markup." % parser
            traceback.print_exc()
        if success:
            print "BS4+%s parsed the markup in %.2fs." % (parser, b-a)

    from lxml import etree
    a = time.time()
    etree.HTML(data)
    b = time.time()
    print "Raw lxml parsed the markup in %.2fs." % (b-a)

if __name__ == '__main__':
    diagnose(sys.stdin.read())

########NEW FILE########
__FILENAME__ = element
import collections
import re
import sys
import warnings
from bs4.dammit import EntitySubstitution

DEFAULT_OUTPUT_ENCODING = "utf-8"
PY3K = (sys.version_info[0] > 2)

whitespace_re = re.compile("\s+")

def _alias(attr):
    """Alias one attribute name to another for backward compatibility"""
    @property
    def alias(self):
        return getattr(self, attr)

    @alias.setter
    def alias(self):
        return setattr(self, attr)
    return alias


class NamespacedAttribute(unicode):

    def __new__(cls, prefix, name, namespace=None):
        if name is None:
            obj = unicode.__new__(cls, prefix)
        elif prefix is None:
            # Not really namespaced.
            obj = unicode.__new__(cls, name)
        else:
            obj = unicode.__new__(cls, prefix + ":" + name)
        obj.prefix = prefix
        obj.name = name
        obj.namespace = namespace
        return obj

class AttributeValueWithCharsetSubstitution(unicode):
    """A stand-in object for a character encoding specified in HTML."""

class CharsetMetaAttributeValue(AttributeValueWithCharsetSubstitution):
    """A generic stand-in for the value of a meta tag's 'charset' attribute.

    When Beautiful Soup parses the markup '<meta charset="utf8">', the
    value of the 'charset' attribute will be one of these objects.
    """

    def __new__(cls, original_value):
        obj = unicode.__new__(cls, original_value)
        obj.original_value = original_value
        return obj

    def encode(self, encoding):
        return encoding


class ContentMetaAttributeValue(AttributeValueWithCharsetSubstitution):
    """A generic stand-in for the value of a meta tag's 'content' attribute.

    When Beautiful Soup parses the markup:
     <meta http-equiv="content-type" content="text/html; charset=utf8">

    The value of the 'content' attribute will be one of these objects.
    """

    CHARSET_RE = re.compile("((^|;)\s*charset=)([^;]*)", re.M)

    def __new__(cls, original_value):
        match = cls.CHARSET_RE.search(original_value)
        if match is None:
            # No substitution necessary.
            return unicode.__new__(unicode, original_value)

        obj = unicode.__new__(cls, original_value)
        obj.original_value = original_value
        return obj

    def encode(self, encoding):
        def rewrite(match):
            return match.group(1) + encoding
        return self.CHARSET_RE.sub(rewrite, self.original_value)

class HTMLAwareEntitySubstitution(EntitySubstitution):

    """Entity substitution rules that are aware of some HTML quirks.

    Specifically, the contents of <script> and <style> tags should not
    undergo entity substitution.

    Incoming NavigableString objects are checked to see if they're the
    direct children of a <script> or <style> tag.
    """

    cdata_containing_tags = set(["script", "style"])

    preformatted_tags = set(["pre"])

    @classmethod
    def _substitute_if_appropriate(cls, ns, f):
        if (isinstance(ns, NavigableString)
            and ns.parent is not None
            and ns.parent.name in cls.cdata_containing_tags):
            # Do nothing.
            return ns
        # Substitute.
        return f(ns)

    @classmethod
    def substitute_html(cls, ns):
        return cls._substitute_if_appropriate(
            ns, EntitySubstitution.substitute_html)

    @classmethod
    def substitute_xml(cls, ns):
        return cls._substitute_if_appropriate(
            ns, EntitySubstitution.substitute_xml)

class PageElement(object):
    """Contains the navigational information for some part of the page
    (either a tag or a piece of text)"""

    # There are five possible values for the "formatter" argument passed in
    # to methods like encode() and prettify():
    #
    # "html" - All Unicode characters with corresponding HTML entities
    #   are converted to those entities on output.
    # "minimal" - Bare ampersands and angle brackets are converted to
    #   XML entities: &amp; &lt; &gt;
    # None - The null formatter. Unicode characters are never
    #   converted to entities.  This is not recommended, but it's
    #   faster than "minimal".
    # A function - This function will be called on every string that
    #  needs to undergo entity substitution.
    #

    # In an HTML document, the default "html" and "minimal" functions
    # will leave the contents of <script> and <style> tags alone. For
    # an XML document, all tags will be given the same treatment.

    HTML_FORMATTERS = {
        "html" : HTMLAwareEntitySubstitution.substitute_html,
        "minimal" : HTMLAwareEntitySubstitution.substitute_xml,
        None : None
        }

    XML_FORMATTERS = {
        "html" : EntitySubstitution.substitute_html,
        "minimal" : EntitySubstitution.substitute_xml,
        None : None
        }

    def format_string(self, s, formatter='minimal'):
        """Format the given string using the given formatter."""
        if not callable(formatter):
            formatter = self._formatter_for_name(formatter)
        if formatter is None:
            output = s
        else:
            output = formatter(s)
        return output

    @property
    def _is_xml(self):
        """Is this element part of an XML tree or an HTML tree?

        This is used when mapping a formatter name ("minimal") to an
        appropriate function (one that performs entity-substitution on
        the contents of <script> and <style> tags, or not). It's
        inefficient, but it should be called very rarely.
        """
        if self.parent is None:
            # This is the top-level object. It should have .is_xml set
            # from tree creation. If not, take a guess--BS is usually
            # used on HTML markup.
            return getattr(self, 'is_xml', False)
        return self.parent._is_xml

    def _formatter_for_name(self, name):
        "Look up a formatter function based on its name and the tree."
        if self._is_xml:
            return self.XML_FORMATTERS.get(
                name, EntitySubstitution.substitute_xml)
        else:
            return self.HTML_FORMATTERS.get(
                name, HTMLAwareEntitySubstitution.substitute_xml)

    def setup(self, parent=None, previous_element=None):
        """Sets up the initial relations between this element and
        other elements."""
        self.parent = parent
        self.previous_element = previous_element
        if previous_element is not None:
            self.previous_element.next_element = self
        self.next_element = None
        self.previous_sibling = None
        self.next_sibling = None
        if self.parent is not None and self.parent.contents:
            self.previous_sibling = self.parent.contents[-1]
            self.previous_sibling.next_sibling = self

    nextSibling = _alias("next_sibling")  # BS3
    previousSibling = _alias("previous_sibling")  # BS3

    def replace_with(self, replace_with):
        if replace_with is self:
            return
        if replace_with is self.parent:
            raise ValueError("Cannot replace a Tag with its parent.")
        old_parent = self.parent
        my_index = self.parent.index(self)
        self.extract()
        old_parent.insert(my_index, replace_with)
        return self
    replaceWith = replace_with  # BS3

    def unwrap(self):
        my_parent = self.parent
        my_index = self.parent.index(self)
        self.extract()
        for child in reversed(self.contents[:]):
            my_parent.insert(my_index, child)
        return self
    replace_with_children = unwrap
    replaceWithChildren = unwrap  # BS3

    def wrap(self, wrap_inside):
        me = self.replace_with(wrap_inside)
        wrap_inside.append(me)
        return wrap_inside

    def extract(self):
        """Destructively rips this element out of the tree."""
        if self.parent is not None:
            del self.parent.contents[self.parent.index(self)]

        #Find the two elements that would be next to each other if
        #this element (and any children) hadn't been parsed. Connect
        #the two.
        last_child = self._last_descendant()
        next_element = last_child.next_element

        if self.previous_element is not None:
            self.previous_element.next_element = next_element
        if next_element is not None:
            next_element.previous_element = self.previous_element
        self.previous_element = None
        last_child.next_element = None

        self.parent = None
        if self.previous_sibling is not None:
            self.previous_sibling.next_sibling = self.next_sibling
        if self.next_sibling is not None:
            self.next_sibling.previous_sibling = self.previous_sibling
        self.previous_sibling = self.next_sibling = None
        return self

    def _last_descendant(self):
        "Finds the last element beneath this object to be parsed."
        last_child = self
        while hasattr(last_child, 'contents') and last_child.contents:
            last_child = last_child.contents[-1]
        return last_child
    # BS3: Not part of the API!
    _lastRecursiveChild = _last_descendant

    def insert(self, position, new_child):
        if new_child is self:
            raise ValueError("Cannot insert a tag into itself.")
        if (isinstance(new_child, basestring)
            and not isinstance(new_child, NavigableString)):
            new_child = NavigableString(new_child)

        position = min(position, len(self.contents))
        if hasattr(new_child, 'parent') and new_child.parent is not None:
            # We're 'inserting' an element that's already one
            # of this object's children.
            if new_child.parent is self:
                current_index = self.index(new_child)
                if current_index < position:
                    # We're moving this element further down the list
                    # of this object's children. That means that when
                    # we extract this element, our target index will
                    # jump down one.
                    position -= 1
            new_child.extract()

        new_child.parent = self
        previous_child = None
        if position == 0:
            new_child.previous_sibling = None
            new_child.previous_element = self
        else:
            previous_child = self.contents[position - 1]
            new_child.previous_sibling = previous_child
            new_child.previous_sibling.next_sibling = new_child
            new_child.previous_element = previous_child._last_descendant()
        if new_child.previous_element is not None:
            new_child.previous_element.next_element = new_child

        new_childs_last_element = new_child._last_descendant()

        if position >= len(self.contents):
            new_child.next_sibling = None

            parent = self
            parents_next_sibling = None
            while parents_next_sibling is None and parent is not None:
                parents_next_sibling = parent.next_sibling
                parent = parent.parent
                if parents_next_sibling is not None:
                    # We found the element that comes next in the document.
                    break
            if parents_next_sibling is not None:
                new_childs_last_element.next_element = parents_next_sibling
            else:
                # The last element of this tag is the last element in
                # the document.
                new_childs_last_element.next_element = None
        else:
            next_child = self.contents[position]
            new_child.next_sibling = next_child
            if new_child.next_sibling is not None:
                new_child.next_sibling.previous_sibling = new_child
            new_childs_last_element.next_element = next_child

        if new_childs_last_element.next_element is not None:
            new_childs_last_element.next_element.previous_element = new_childs_last_element
        self.contents.insert(position, new_child)

    def append(self, tag):
        """Appends the given tag to the contents of this tag."""
        self.insert(len(self.contents), tag)

    def insert_before(self, predecessor):
        """Makes the given element the immediate predecessor of this one.

        The two elements will have the same parent, and the given element
        will be immediately before this one.
        """
        if self is predecessor:
            raise ValueError("Can't insert an element before itself.")
        parent = self.parent
        if parent is None:
            raise ValueError(
                "Element has no parent, so 'before' has no meaning.")
        # Extract first so that the index won't be screwed up if they
        # are siblings.
        if isinstance(predecessor, PageElement):
            predecessor.extract()
        index = parent.index(self)
        parent.insert(index, predecessor)

    def insert_after(self, successor):
        """Makes the given element the immediate successor of this one.

        The two elements will have the same parent, and the given element
        will be immediately after this one.
        """
        if self is successor:
            raise ValueError("Can't insert an element after itself.")
        parent = self.parent
        if parent is None:
            raise ValueError(
                "Element has no parent, so 'after' has no meaning.")
        # Extract first so that the index won't be screwed up if they
        # are siblings.
        if isinstance(successor, PageElement):
            successor.extract()
        index = parent.index(self)
        parent.insert(index+1, successor)

    def find_next(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears after this Tag in the document."""
        return self._find_one(self.find_all_next, name, attrs, text, **kwargs)
    findNext = find_next  # BS3

    def find_all_next(self, name=None, attrs={}, text=None, limit=None,
                    **kwargs):
        """Returns all items that match the given criteria and appear
        after this Tag in the document."""
        return self._find_all(name, attrs, text, limit, self.next_elements,
                             **kwargs)
    findAllNext = find_all_next  # BS3

    def find_next_sibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears after this Tag in the document."""
        return self._find_one(self.find_next_siblings, name, attrs, text,
                             **kwargs)
    findNextSibling = find_next_sibling  # BS3

    def find_next_siblings(self, name=None, attrs={}, text=None, limit=None,
                           **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear after this Tag in the document."""
        return self._find_all(name, attrs, text, limit,
                              self.next_siblings, **kwargs)
    findNextSiblings = find_next_siblings   # BS3
    fetchNextSiblings = find_next_siblings  # BS2

    def find_previous(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears before this Tag in the document."""
        return self._find_one(
            self.find_all_previous, name, attrs, text, **kwargs)
    findPrevious = find_previous  # BS3

    def find_all_previous(self, name=None, attrs={}, text=None, limit=None,
                        **kwargs):
        """Returns all items that match the given criteria and appear
        before this Tag in the document."""
        return self._find_all(name, attrs, text, limit, self.previous_elements,
                           **kwargs)
    findAllPrevious = find_all_previous  # BS3
    fetchPrevious = find_all_previous    # BS2

    def find_previous_sibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears before this Tag in the document."""
        return self._find_one(self.find_previous_siblings, name, attrs, text,
                             **kwargs)
    findPreviousSibling = find_previous_sibling  # BS3

    def find_previous_siblings(self, name=None, attrs={}, text=None,
                               limit=None, **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear before this Tag in the document."""
        return self._find_all(name, attrs, text, limit,
                              self.previous_siblings, **kwargs)
    findPreviousSiblings = find_previous_siblings   # BS3
    fetchPreviousSiblings = find_previous_siblings  # BS2

    def find_parent(self, name=None, attrs={}, **kwargs):
        """Returns the closest parent of this Tag that matches the given
        criteria."""
        # NOTE: We can't use _find_one because findParents takes a different
        # set of arguments.
        r = None
        l = self.find_parents(name, attrs, 1, **kwargs)
        if l:
            r = l[0]
        return r
    findParent = find_parent  # BS3

    def find_parents(self, name=None, attrs={}, limit=None, **kwargs):
        """Returns the parents of this Tag that match the given
        criteria."""

        return self._find_all(name, attrs, None, limit, self.parents,
                             **kwargs)
    findParents = find_parents   # BS3
    fetchParents = find_parents  # BS2

    @property
    def next(self):
        return self.next_element

    @property
    def previous(self):
        return self.previous_element

    #These methods do the real heavy lifting.

    def _find_one(self, method, name, attrs, text, **kwargs):
        r = None
        l = method(name, attrs, text, 1, **kwargs)
        if l:
            r = l[0]
        return r

    def _find_all(self, name, attrs, text, limit, generator, **kwargs):
        "Iterates over a generator looking for things that match."

        if isinstance(name, SoupStrainer):
            strainer = name
        elif text is None and not limit and not attrs and not kwargs:
            # Optimization to find all tags.
            if name is True or name is None:
                return [element for element in generator
                        if isinstance(element, Tag)]
            # Optimization to find all tags with a given name.
            elif isinstance(name, basestring):
                return [element for element in generator
                        if isinstance(element, Tag) and element.name == name]
            else:
                strainer = SoupStrainer(name, attrs, text, **kwargs)
        else:
            # Build a SoupStrainer
            strainer = SoupStrainer(name, attrs, text, **kwargs)
        results = ResultSet(strainer)
        while True:
            try:
                i = next(generator)
            except StopIteration:
                break
            if i:
                found = strainer.search(i)
                if found:
                    results.append(found)
                    if limit and len(results) >= limit:
                        break
        return results

    #These generators can be used to navigate starting from both
    #NavigableStrings and Tags.
    @property
    def next_elements(self):
        i = self.next_element
        while i is not None:
            yield i
            i = i.next_element

    @property
    def next_siblings(self):
        i = self.next_sibling
        while i is not None:
            yield i
            i = i.next_sibling

    @property
    def previous_elements(self):
        i = self.previous_element
        while i is not None:
            yield i
            i = i.previous_element

    @property
    def previous_siblings(self):
        i = self.previous_sibling
        while i is not None:
            yield i
            i = i.previous_sibling

    @property
    def parents(self):
        i = self.parent
        while i is not None:
            yield i
            i = i.parent

    # Methods for supporting CSS selectors.

    tag_name_re = re.compile('^[a-z0-9]+$')

    # /^(\w+)\[(\w+)([=~\|\^\$\*]?)=?"?([^\]"]*)"?\]$/
    #   \---/  \---/\-------------/    \-------/
    #     |      |         |               |
    #     |      |         |           The value
    #     |      |    ~,|,^,$,* or =
    #     |   Attribute
    #    Tag
    attribselect_re = re.compile(
        r'^(?P<tag>\w+)?\[(?P<attribute>\w+)(?P<operator>[=~\|\^\$\*]?)' +
        r'=?"?(?P<value>[^\]"]*)"?\]$'
        )

    def _attr_value_as_string(self, value, default=None):
        """Force an attribute value into a string representation.

        A multi-valued attribute will be converted into a
        space-separated stirng.
        """
        value = self.get(value, default)
        if isinstance(value, list) or isinstance(value, tuple):
            value =" ".join(value)
        return value

    def _tag_name_matches_and(self, function, tag_name):
        if not tag_name:
            return function
        else:
            def _match(tag):
                return tag.name == tag_name and function(tag)
            return _match

    def _attribute_checker(self, operator, attribute, value=''):
        """Create a function that performs a CSS selector operation.

        Takes an operator, attribute and optional value. Returns a
        function that will return True for elements that match that
        combination.
        """
        if operator == '=':
            # string representation of `attribute` is equal to `value`
            return lambda el: el._attr_value_as_string(attribute) == value
        elif operator == '~':
            # space-separated list representation of `attribute`
            # contains `value`
            def _includes_value(element):
                attribute_value = element.get(attribute, [])
                if not isinstance(attribute_value, list):
                    attribute_value = attribute_value.split()
                return value in attribute_value
            return _includes_value
        elif operator == '^':
            # string representation of `attribute` starts with `value`
            return lambda el: el._attr_value_as_string(
                attribute, '').startswith(value)
        elif operator == '$':
            # string represenation of `attribute` ends with `value`
            return lambda el: el._attr_value_as_string(
                attribute, '').endswith(value)
        elif operator == '*':
            # string representation of `attribute` contains `value`
            return lambda el: value in el._attr_value_as_string(attribute, '')
        elif operator == '|':
            # string representation of `attribute` is either exactly
            # `value` or starts with `value` and then a dash.
            def _is_or_starts_with_dash(element):
                attribute_value = element._attr_value_as_string(attribute, '')
                return (attribute_value == value or attribute_value.startswith(
                        value + '-'))
            return _is_or_starts_with_dash
        else:
            return lambda el: el.has_attr(attribute)

    # Old non-property versions of the generators, for backwards
    # compatibility with BS3.
    def nextGenerator(self):
        return self.next_elements

    def nextSiblingGenerator(self):
        return self.next_siblings

    def previousGenerator(self):
        return self.previous_elements

    def previousSiblingGenerator(self):
        return self.previous_siblings

    def parentGenerator(self):
        return self.parents


class NavigableString(unicode, PageElement):

    PREFIX = ''
    SUFFIX = ''

    def __new__(cls, value):
        """Create a new NavigableString.

        When unpickling a NavigableString, this method is called with
        the string in DEFAULT_OUTPUT_ENCODING. That encoding needs to be
        passed in to the superclass's __new__ or the superclass won't know
        how to handle non-ASCII characters.
        """
        if isinstance(value, unicode):
            return unicode.__new__(cls, value)
        return unicode.__new__(cls, value, DEFAULT_OUTPUT_ENCODING)

    def __copy__(self):
        return self

    def __getnewargs__(self):
        return (unicode(self),)

    def __getattr__(self, attr):
        """text.string gives you text. This is for backwards
        compatibility for Navigable*String, but for CData* it lets you
        get the string without the CData wrapper."""
        if attr == 'string':
            return self
        else:
            raise AttributeError(
                "'%s' object has no attribute '%s'" % (
                    self.__class__.__name__, attr))

    def output_ready(self, formatter="minimal"):
        output = self.format_string(self, formatter)
        return self.PREFIX + output + self.SUFFIX


class PreformattedString(NavigableString):
    """A NavigableString not subject to the normal formatting rules.

    The string will be passed into the formatter (to trigger side effects),
    but the return value will be ignored.
    """

    def output_ready(self, formatter="minimal"):
        """CData strings are passed into the formatter.
        But the return value is ignored."""
        self.format_string(self, formatter)
        return self.PREFIX + self + self.SUFFIX

class CData(PreformattedString):

    PREFIX = u'<![CDATA['
    SUFFIX = u']]>'

class ProcessingInstruction(PreformattedString):

    PREFIX = u'<?'
    SUFFIX = u'?>'

class Comment(PreformattedString):

    PREFIX = u'<!--'
    SUFFIX = u'-->'


class Declaration(PreformattedString):
    PREFIX = u'<!'
    SUFFIX = u'!>'


class Doctype(PreformattedString):

    @classmethod
    def for_name_and_ids(cls, name, pub_id, system_id):
        value = name or ''
        if pub_id is not None:
            value += ' PUBLIC "%s"' % pub_id
            if system_id is not None:
                value += ' "%s"' % system_id
        elif system_id is not None:
            value += ' SYSTEM "%s"' % system_id

        return Doctype(value)

    PREFIX = u'<!DOCTYPE '
    SUFFIX = u'>\n'


class Tag(PageElement):

    """Represents a found HTML tag with its attributes and contents."""

    def __init__(self, parser=None, builder=None, name=None, namespace=None,
                 prefix=None, attrs=None, parent=None, previous=None):
        "Basic constructor."

        if parser is None:
            self.parser_class = None
        else:
            # We don't actually store the parser object: that lets extracted
            # chunks be garbage-collected.
            self.parser_class = parser.__class__
        if name is None:
            raise ValueError("No value provided for new tag's name.")
        self.name = name
        self.namespace = namespace
        self.prefix = prefix
        if attrs is None:
            attrs = {}
        elif builder.cdata_list_attributes:
            attrs = builder._replace_cdata_list_attribute_values(
                self.name, attrs)
        else:
            attrs = dict(attrs)
        self.attrs = attrs
        self.contents = []
        self.setup(parent, previous)
        self.hidden = False

        # Set up any substitutions, such as the charset in a META tag.
        if builder is not None:
            builder.set_up_substitutions(self)
            self.can_be_empty_element = builder.can_be_empty_element(name)
        else:
            self.can_be_empty_element = False

    parserClass = _alias("parser_class")  # BS3

    @property
    def is_empty_element(self):
        """Is this tag an empty-element tag? (aka a self-closing tag)

        A tag that has contents is never an empty-element tag.

        A tag that has no contents may or may not be an empty-element
        tag. It depends on the builder used to create the tag. If the
        builder has a designated list of empty-element tags, then only
        a tag whose name shows up in that list is considered an
        empty-element tag.

        If the builder has no designated list of empty-element tags,
        then any tag with no contents is an empty-element tag.
        """
        return len(self.contents) == 0 and self.can_be_empty_element
    isSelfClosing = is_empty_element  # BS3

    @property
    def string(self):
        """Convenience property to get the single string within this tag.

        :Return: If this tag has a single string child, return value
         is that string. If this tag has no children, or more than one
         child, return value is None. If this tag has one child tag,
         return value is the 'string' attribute of the child tag,
         recursively.
        """
        if len(self.contents) != 1:
            return None
        child = self.contents[0]
        if isinstance(child, NavigableString):
            return child
        return child.string

    @string.setter
    def string(self, string):
        self.clear()
        self.append(string.__class__(string))

    def _all_strings(self, strip=False, types=(NavigableString, CData)):
        """Yield all strings of certain classes, possibly stripping them.

        By default, yields only NavigableString and CData objects. So
        no comments, processing instructions, etc.
        """
        for descendant in self.descendants:
            if (
                (types is None and not isinstance(descendant, NavigableString))
                or
                (types is not None and type(descendant) not in types)):
                continue
            if strip:
                descendant = descendant.strip()
                if len(descendant) == 0:
                    continue
            yield descendant

    strings = property(_all_strings)

    @property
    def stripped_strings(self):
        for string in self._all_strings(True):
            yield string

    def get_text(self, separator=u"", strip=False,
                 types=(NavigableString, CData)):
        """
        Get all child strings, concatenated using the given separator.
        """
        return separator.join([s for s in self._all_strings(
                    strip, types=types)])
    getText = get_text
    text = property(get_text)

    def decompose(self):
        """Recursively destroys the contents of this tree."""
        self.extract()
        i = self
        while i is not None:
            next = i.next_element
            i.__dict__.clear()
            i.contents = []
            i = next

    def clear(self, decompose=False):
        """
        Extract all children. If decompose is True, decompose instead.
        """
        if decompose:
            for element in self.contents[:]:
                if isinstance(element, Tag):
                    element.decompose()
                else:
                    element.extract()
        else:
            for element in self.contents[:]:
                element.extract()

    def index(self, element):
        """
        Find the index of a child by identity, not value. Avoids issues with
        tag.contents.index(element) getting the index of equal elements.
        """
        for i, child in enumerate(self.contents):
            if child is element:
                return i
        raise ValueError("Tag.index: element not in tag")

    def get(self, key, default=None):
        """Returns the value of the 'key' attribute for the tag, or
        the value given for 'default' if it doesn't have that
        attribute."""
        return self.attrs.get(key, default)

    def has_attr(self, key):
        return key in self.attrs

    def __hash__(self):
        return str(self).__hash__()

    def __getitem__(self, key):
        """tag[key] returns the value of the 'key' attribute for the tag,
        and throws an exception if it's not there."""
        return self.attrs[key]

    def __iter__(self):
        "Iterating over a tag iterates over its contents."
        return iter(self.contents)

    def __len__(self):
        "The length of a tag is the length of its list of contents."
        return len(self.contents)

    def __contains__(self, x):
        return x in self.contents

    def __nonzero__(self):
        "A tag is non-None even if it has no contents."
        return True

    def __setitem__(self, key, value):
        """Setting tag[key] sets the value of the 'key' attribute for the
        tag."""
        self.attrs[key] = value

    def __delitem__(self, key):
        "Deleting tag[key] deletes all 'key' attributes for the tag."
        self.attrs.pop(key, None)

    def __call__(self, *args, **kwargs):
        """Calling a tag like a function is the same as calling its
        find_all() method. Eg. tag('a') returns a list of all the A tags
        found within this tag."""
        return self.find_all(*args, **kwargs)

    def __getattr__(self, tag):
        #print "Getattr %s.%s" % (self.__class__, tag)
        if len(tag) > 3 and tag.endswith('Tag'):
            # BS3: soup.aTag -> "soup.find("a")
            tag_name = tag[:-3]
            warnings.warn(
                '.%sTag is deprecated, use .find("%s") instead.' % (
                    tag_name, tag_name))
            return self.find(tag_name)
        # We special case contents to avoid recursion.
        elif not tag.startswith("__") and not tag=="contents":
            return self.find(tag)
        raise AttributeError(
            "'%s' object has no attribute '%s'" % (self.__class__, tag))

    def __eq__(self, other):
        """Returns true iff this tag has the same name, the same attributes,
        and the same contents (recursively) as the given tag."""
        if self is other:
            return True
        if (not hasattr(other, 'name') or
            not hasattr(other, 'attrs') or
            not hasattr(other, 'contents') or
            self.name != other.name or
            self.attrs != other.attrs or
            len(self) != len(other)):
            return False
        for i, my_child in enumerate(self.contents):
            if my_child != other.contents[i]:
                return False
        return True

    def __ne__(self, other):
        """Returns true iff this tag is not identical to the other tag,
        as defined in __eq__."""
        return not self == other

    def __repr__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        """Renders this tag as a string."""
        return self.encode(encoding)

    def __unicode__(self):
        return self.decode()

    def __str__(self):
        return self.encode()

    if PY3K:
        __str__ = __repr__ = __unicode__

    def encode(self, encoding=DEFAULT_OUTPUT_ENCODING,
               indent_level=None, formatter="minimal",
               errors="xmlcharrefreplace"):
        # Turn the data structure into Unicode, then encode the
        # Unicode.
        u = self.decode(indent_level, encoding, formatter)
        return u.encode(encoding, errors)

    def _should_pretty_print(self, indent_level):
        """Should this tag be pretty-printed?"""
        return (
            indent_level is not None and
            (self.name not in HTMLAwareEntitySubstitution.preformatted_tags
             or self._is_xml))

    def decode(self, indent_level=None,
               eventual_encoding=DEFAULT_OUTPUT_ENCODING,
               formatter="minimal"):
        """Returns a Unicode representation of this tag and its contents.

        :param eventual_encoding: The tag is destined to be
           encoded into this encoding. This method is _not_
           responsible for performing that encoding. This information
           is passed in so that it can be substituted in if the
           document contains a <META> tag that mentions the document's
           encoding.
        """

        # First off, turn a string formatter into a function. This
        # will stop the lookup from happening over and over again.
        if not callable(formatter):
            formatter = self._formatter_for_name(formatter)

        attrs = []
        if self.attrs:
            for key, val in sorted(self.attrs.items()):
                if val is None:
                    decoded = key
                else:
                    if isinstance(val, list) or isinstance(val, tuple):
                        val = ' '.join(val)
                    elif not isinstance(val, basestring):
                        val = unicode(val)
                    elif (
                        isinstance(val, AttributeValueWithCharsetSubstitution)
                        and eventual_encoding is not None):
                        val = val.encode(eventual_encoding)

                    text = self.format_string(val, formatter)
                    decoded = (
                        unicode(key) + '='
                        + EntitySubstitution.quoted_attribute_value(text))
                attrs.append(decoded)
        close = ''
        closeTag = ''

        prefix = ''
        if self.prefix:
            prefix = self.prefix + ":"

        if self.is_empty_element:
            close = '/'
        else:
            closeTag = '</%s%s>' % (prefix, self.name)

        pretty_print = self._should_pretty_print(indent_level)
        space = ''
        indent_space = ''
        if indent_level is not None:
            indent_space = (' ' * (indent_level - 1))
        if pretty_print:
            space = indent_space
            indent_contents = indent_level + 1
        else:
            indent_contents = None
        contents = self.decode_contents(
            indent_contents, eventual_encoding, formatter)

        if self.hidden:
            # This is the 'document root' object.
            s = contents
        else:
            s = []
            attribute_string = ''
            if attrs:
                attribute_string = ' ' + ' '.join(attrs)
            if indent_level is not None:
                # Even if this particular tag is not pretty-printed,
                # we should indent up to the start of the tag.
                s.append(indent_space)
            s.append('<%s%s%s%s>' % (
                    prefix, self.name, attribute_string, close))
            if pretty_print:
                s.append("\n")
            s.append(contents)
            if pretty_print and contents and contents[-1] != "\n":
                s.append("\n")
            if pretty_print and closeTag:
                s.append(space)
            s.append(closeTag)
            if indent_level is not None and closeTag and self.next_sibling:
                # Even if this particular tag is not pretty-printed,
                # we're now done with the tag, and we should add a
                # newline if appropriate.
                s.append("\n")
            s = ''.join(s)
        return s

    def prettify(self, encoding=None, formatter="minimal"):
        if encoding is None:
            return self.decode(True, formatter=formatter)
        else:
            return self.encode(encoding, True, formatter=formatter)

    def decode_contents(self, indent_level=None,
                       eventual_encoding=DEFAULT_OUTPUT_ENCODING,
                       formatter="minimal"):
        """Renders the contents of this tag as a Unicode string.

        :param eventual_encoding: The tag is destined to be
           encoded into this encoding. This method is _not_
           responsible for performing that encoding. This information
           is passed in so that it can be substituted in if the
           document contains a <META> tag that mentions the document's
           encoding.
        """
        # First off, turn a string formatter into a function. This
        # will stop the lookup from happening over and over again.
        if not callable(formatter):
            formatter = self._formatter_for_name(formatter)

        pretty_print = (indent_level is not None)
        s = []
        for c in self:
            text = None
            if isinstance(c, NavigableString):
                text = c.output_ready(formatter)
            elif isinstance(c, Tag):
                s.append(c.decode(indent_level, eventual_encoding,
                                  formatter))
            if text and indent_level and not self.name == 'pre':
                text = text.strip()
            if text:
                if pretty_print and not self.name == 'pre':
                    s.append(" " * (indent_level - 1))
                s.append(text)
                if pretty_print and not self.name == 'pre':
                    s.append("\n")
        return ''.join(s)

    def encode_contents(
        self, indent_level=None, encoding=DEFAULT_OUTPUT_ENCODING,
        formatter="minimal"):
        """Renders the contents of this tag as a bytestring."""
        contents = self.decode_contents(indent_level, encoding, formatter)
        return contents.encode(encoding)

    # Old method for BS3 compatibility
    def renderContents(self, encoding=DEFAULT_OUTPUT_ENCODING,
                       prettyPrint=False, indentLevel=0):
        if not prettyPrint:
            indentLevel = None
        return self.encode_contents(
            indent_level=indentLevel, encoding=encoding)

    #Soup methods

    def find(self, name=None, attrs={}, recursive=True, text=None,
             **kwargs):
        """Return only the first child of this Tag matching the given
        criteria."""
        r = None
        l = self.find_all(name, attrs, recursive, text, 1, **kwargs)
        if l:
            r = l[0]
        return r
    findChild = find

    def find_all(self, name=None, attrs={}, recursive=True, text=None,
                 limit=None, **kwargs):
        """Extracts a list of Tag objects that match the given
        criteria.  You can specify the name of the Tag and any
        attributes you want the Tag to have.

        The value of a key-value pair in the 'attrs' map can be a
        string, a list of strings, a regular expression object, or a
        callable that takes a string and returns whether or not the
        string matches for some custom definition of 'matches'. The
        same is true of the tag name."""

        generator = self.descendants
        if not recursive:
            generator = self.children
        return self._find_all(name, attrs, text, limit, generator, **kwargs)
    findAll = find_all       # BS3
    findChildren = find_all  # BS2

    #Generator methods
    @property
    def children(self):
        # return iter() to make the purpose of the method clear
        return iter(self.contents)  # XXX This seems to be untested.

    @property
    def descendants(self):
        if not len(self.contents):
            return
        stopNode = self._last_descendant().next_element
        current = self.contents[0]
        while current is not stopNode:
            yield current
            current = current.next_element

    # CSS selector code

    _selector_combinators = ['>', '+', '~']
    _select_debug = False
    def select(self, selector, _candidate_generator=None):
        """Perform a CSS selection operation on the current element."""
        tokens = selector.split()
        current_context = [self]

        if tokens[-1] in self._selector_combinators:
            raise ValueError(
                'Final combinator "%s" is missing an argument.' % tokens[-1])
        if self._select_debug:
            print 'Running CSS selector "%s"' % selector
        for index, token in enumerate(tokens):
            if self._select_debug:
                print ' Considering token "%s"' % token
            recursive_candidate_generator = None
            tag_name = None
            if tokens[index-1] in self._selector_combinators:
                # This token was consumed by the previous combinator. Skip it.
                if self._select_debug:
                    print '  Token was consumed by the previous combinator.'
                continue
            # Each operation corresponds to a checker function, a rule
            # for determining whether a candidate matches the
            # selector. Candidates are generated by the active
            # iterator.
            checker = None

            m = self.attribselect_re.match(token)
            if m is not None:
                # Attribute selector
                tag_name, attribute, operator, value = m.groups()
                checker = self._attribute_checker(operator, attribute, value)

            elif '#' in token:
                # ID selector
                tag_name, tag_id = token.split('#', 1)
                def id_matches(tag):
                    return tag.get('id', None) == tag_id
                checker = id_matches

            elif '.' in token:
                # Class selector
                tag_name, klass = token.split('.', 1)
                classes = set(klass.split('.'))
                def classes_match(candidate):
                    return classes.issubset(candidate.get('class', []))
                checker = classes_match

            elif ':' in token:
                # Pseudo-class
                tag_name, pseudo = token.split(':', 1)
                if tag_name == '':
                    raise ValueError(
                        "A pseudo-class must be prefixed with a tag name.")
                pseudo_attributes = re.match('([a-zA-Z\d-]+)\(([a-zA-Z\d]+)\)', pseudo)
                found = []
                if pseudo_attributes is not None:
                    pseudo_type, pseudo_value = pseudo_attributes.groups()
                    if pseudo_type == 'nth-of-type':
                        try:
                            pseudo_value = int(pseudo_value)
                        except:
                            raise NotImplementedError(
                                'Only numeric values are currently supported for the nth-of-type pseudo-class.')
                        if pseudo_value < 1:
                            raise ValueError(
                                'nth-of-type pseudo-class value must be at least 1.')
                        class Counter(object):
                            def __init__(self, destination):
                                self.count = 0
                                self.destination = destination

                            def nth_child_of_type(self, tag):
                                self.count += 1
                                if self.count == self.destination:
                                    return True
                                if self.count > self.destination:
                                    # Stop the generator that's sending us
                                    # these things.
                                    raise StopIteration()
                                return False
                        checker = Counter(pseudo_value).nth_child_of_type
                    else:
                        raise NotImplementedError(
                            'Only the following pseudo-classes are implemented: nth-of-type.')

            elif token == '*':
                # Star selector -- matches everything
                pass
            elif token == '>':
                # Run the next token as a CSS selector against the
                # direct children of each tag in the current context.
                recursive_candidate_generator = lambda tag: tag.children
            elif token == '~':
                # Run the next token as a CSS selector against the
                # siblings of each tag in the current context.
                recursive_candidate_generator = lambda tag: tag.next_siblings
            elif token == '+':
                # For each tag in the current context, run the next
                # token as a CSS selector against the tag's next
                # sibling that's a tag.
                def next_tag_sibling(tag):
                    yield tag.find_next_sibling(True)
                recursive_candidate_generator = next_tag_sibling

            elif self.tag_name_re.match(token):
                # Just a tag name.
                tag_name = token
            else:
                raise ValueError(
                    'Unsupported or invalid CSS selector: "%s"' % token)

            if recursive_candidate_generator:
                # This happens when the selector looks like  "> foo".
                #
                # The generator calls select() recursively on every
                # member of the current context, passing in a different
                # candidate generator and a different selector.
                #
                # In the case of "> foo", the candidate generator is
                # one that yields a tag's direct children (">"), and
                # the selector is "foo".
                next_token = tokens[index+1]
                def recursive_select(tag):
                    if self._select_debug:
                        print '    Calling select("%s") recursively on %s %s' % (next_token, tag.name, tag.attrs)
                        print '-' * 40
                    for i in tag.select(next_token, recursive_candidate_generator):
                        if self._select_debug:
                            print '(Recursive select picked up candidate %s %s)' % (i.name, i.attrs)
                        yield i
                    if self._select_debug:
                        print '-' * 40
                _use_candidate_generator = recursive_select
            elif _candidate_generator is None:
                # By default, a tag's candidates are all of its
                # children. If tag_name is defined, only yield tags
                # with that name.
                if self._select_debug:
                    if tag_name:
                        check = "[any]"
                    else:
                        check = tag_name
                    print '   Default candidate generator, tag name="%s"' % check
                if self._select_debug:
                    # This is redundant with later code, but it stops
                    # a bunch of bogus tags from cluttering up the
                    # debug log.
                    def default_candidate_generator(tag):
                        for child in tag.descendants:
                            if not isinstance(child, Tag):
                                continue
                            if tag_name and not child.name == tag_name:
                                continue
                            yield child
                    _use_candidate_generator = default_candidate_generator
                else:
                    _use_candidate_generator = lambda tag: tag.descendants
            else:
                _use_candidate_generator = _candidate_generator

            new_context = []
            new_context_ids = set([])
            for tag in current_context:
                if self._select_debug:
                    print "    Running candidate generator on %s %s" % (
                        tag.name, repr(tag.attrs))
                for candidate in _use_candidate_generator(tag):
                    if not isinstance(candidate, Tag):
                        continue
                    if tag_name and candidate.name != tag_name:
                        continue
                    if checker is not None:
                        try:
                            result = checker(candidate)
                        except StopIteration:
                            # The checker has decided we should no longer
                            # run the generator.
                            break
                    if checker is None or result:
                        if self._select_debug:
                            print "     SUCCESS %s %s" % (candidate.name, repr(candidate.attrs))
                        if id(candidate) not in new_context_ids:
                            # If a tag matches a selector more than once,
                            # don't include it in the context more than once.
                            new_context.append(candidate)
                            new_context_ids.add(id(candidate))
                    elif self._select_debug:
                        print "     FAILURE %s %s" % (candidate.name, repr(candidate.attrs))

            current_context = new_context

        if self._select_debug:
            print "Final verdict:"
            for i in current_context:
                print " %s %s" % (i.name, i.attrs)
        return current_context

    # Old names for backwards compatibility
    def childGenerator(self):
        return self.children

    def recursiveChildGenerator(self):
        return self.descendants

    def has_key(self, key):
        """This was kind of misleading because has_key() (attributes)
        was different from __in__ (contents). has_key() is gone in
        Python 3, anyway."""
        warnings.warn('has_key is deprecated. Use has_attr("%s") instead.' % (
                key))
        return self.has_attr(key)

# Next, a couple classes to represent queries and their results.
class SoupStrainer(object):
    """Encapsulates a number of ways of matching a markup element (tag or
    text)."""

    def __init__(self, name=None, attrs={}, text=None, **kwargs):
        self.name = self._normalize_search_value(name)
        if not isinstance(attrs, dict):
            # Treat a non-dict value for attrs as a search for the 'class'
            # attribute.
            kwargs['class'] = attrs
            attrs = None

        if 'class_' in kwargs:
            # Treat class_="foo" as a search for the 'class'
            # attribute, overriding any non-dict value for attrs.
            kwargs['class'] = kwargs['class_']
            del kwargs['class_']

        if kwargs:
            if attrs:
                attrs = attrs.copy()
                attrs.update(kwargs)
            else:
                attrs = kwargs
        normalized_attrs = {}
        for key, value in attrs.items():
            normalized_attrs[key] = self._normalize_search_value(value)

        self.attrs = normalized_attrs
        self.text = self._normalize_search_value(text)

    def _normalize_search_value(self, value):
        # Leave it alone if it's a Unicode string, a callable, a
        # regular expression, a boolean, or None.
        if (isinstance(value, unicode) or callable(value) or hasattr(value, 'match')
            or isinstance(value, bool) or value is None):
            return value

        # If it's a bytestring, convert it to Unicode, treating it as UTF-8.
        if isinstance(value, bytes):
            return value.decode("utf8")

        # If it's listlike, convert it into a list of strings.
        if hasattr(value, '__iter__'):
            new_value = []
            for v in value:
                if (hasattr(v, '__iter__') and not isinstance(v, bytes)
                    and not isinstance(v, unicode)):
                    # This is almost certainly the user's mistake. In the
                    # interests of avoiding infinite loops, we'll let
                    # it through as-is rather than doing a recursive call.
                    new_value.append(v)
                else:
                    new_value.append(self._normalize_search_value(v))
            return new_value

        # Otherwise, convert it into a Unicode string.
        # The unicode(str()) thing is so this will do the same thing on Python 2
        # and Python 3.
        return unicode(str(value))

    def __str__(self):
        if self.text:
            return self.text
        else:
            return "%s|%s" % (self.name, self.attrs)

    def search_tag(self, markup_name=None, markup_attrs={}):
        found = None
        markup = None
        if isinstance(markup_name, Tag):
            markup = markup_name
            markup_attrs = markup
        call_function_with_tag_data = (
            isinstance(self.name, collections.Callable)
            and not isinstance(markup_name, Tag))

        if ((not self.name)
            or call_function_with_tag_data
            or (markup and self._matches(markup, self.name))
            or (not markup and self._matches(markup_name, self.name))):
            if call_function_with_tag_data:
                match = self.name(markup_name, markup_attrs)
            else:
                match = True
                markup_attr_map = None
                for attr, match_against in list(self.attrs.items()):
                    if not markup_attr_map:
                        if hasattr(markup_attrs, 'get'):
                            markup_attr_map = markup_attrs
                        else:
                            markup_attr_map = {}
                            for k, v in markup_attrs:
                                markup_attr_map[k] = v
                    attr_value = markup_attr_map.get(attr)
                    if not self._matches(attr_value, match_against):
                        match = False
                        break
            if match:
                if markup:
                    found = markup
                else:
                    found = markup_name
        if found and self.text and not self._matches(found.string, self.text):
            found = None
        return found
    searchTag = search_tag

    def search(self, markup):
        # print 'looking for %s in %s' % (self, markup)
        found = None
        # If given a list of items, scan it for a text element that
        # matches.
        if hasattr(markup, '__iter__') and not isinstance(markup, (Tag, basestring)):
            for element in markup:
                if isinstance(element, NavigableString) \
                       and self.search(element):
                    found = element
                    break
        # If it's a Tag, make sure its name or attributes match.
        # Don't bother with Tags if we're searching for text.
        elif isinstance(markup, Tag):
            if not self.text or self.name or self.attrs:
                found = self.search_tag(markup)
        # If it's text, make sure the text matches.
        elif isinstance(markup, NavigableString) or \
                 isinstance(markup, basestring):
            if not self.name and not self.attrs and self._matches(markup, self.text):
                found = markup
        else:
            raise Exception(
                "I don't know how to match against a %s" % markup.__class__)
        return found

    def _matches(self, markup, match_against):
        # print u"Matching %s against %s" % (markup, match_against)
        result = False
        if isinstance(markup, list) or isinstance(markup, tuple):
            # This should only happen when searching a multi-valued attribute
            # like 'class'.
            if (isinstance(match_against, unicode)
                and ' ' in match_against):
                # A bit of a special case. If they try to match "foo
                # bar" on a multivalue attribute's value, only accept
                # the literal value "foo bar"
                #
                # XXX This is going to be pretty slow because we keep
                # splitting match_against. But it shouldn't come up
                # too often.
                return (whitespace_re.split(match_against) == markup)
            else:
                for item in markup:
                    if self._matches(item, match_against):
                        return True
                return False

        if match_against is True:
            # True matches any non-None value.
            return markup is not None

        if isinstance(match_against, collections.Callable):
            return match_against(markup)

        # Custom callables take the tag as an argument, but all
        # other ways of matching match the tag name as a string.
        if isinstance(markup, Tag):
            markup = markup.name

        # Ensure that `markup` is either a Unicode string, or None.
        markup = self._normalize_search_value(markup)

        if markup is None:
            # None matches None, False, an empty string, an empty list, and so on.
            return not match_against

        if isinstance(match_against, unicode):
            # Exact string match
            return markup == match_against

        if hasattr(match_against, 'match'):
            # Regexp match
            return match_against.search(markup)

        if hasattr(match_against, '__iter__'):
            # The markup must be an exact match against something
            # in the iterable.
            return markup in match_against


class ResultSet(list):
    """A ResultSet is just a list that keeps track of the SoupStrainer
    that created it."""
    def __init__(self, source):
        list.__init__([])
        self.source = source

########NEW FILE########
__FILENAME__ = testing
"""Helper classes for tests."""

import copy
import functools
import unittest
from unittest import TestCase
from bs4 import BeautifulSoup
from bs4.element import (
    CharsetMetaAttributeValue,
    Comment,
    ContentMetaAttributeValue,
    Doctype,
    SoupStrainer,
)

from bs4.builder import HTMLParserTreeBuilder
default_builder = HTMLParserTreeBuilder


class SoupTest(unittest.TestCase):

    @property
    def default_builder(self):
        return default_builder()

    def soup(self, markup, **kwargs):
        """Build a Beautiful Soup object from markup."""
        builder = kwargs.pop('builder', self.default_builder)
        return BeautifulSoup(markup, builder=builder, **kwargs)

    def document_for(self, markup):
        """Turn an HTML fragment into a document.

        The details depend on the builder.
        """
        return self.default_builder.test_fragment_to_document(markup)

    def assertSoupEquals(self, to_parse, compare_parsed_to=None):
        builder = self.default_builder
        obj = BeautifulSoup(to_parse, builder=builder)
        if compare_parsed_to is None:
            compare_parsed_to = to_parse

        self.assertEqual(obj.decode(), self.document_for(compare_parsed_to))


class HTMLTreeBuilderSmokeTest(object):

    """A basic test of a treebuilder's competence.

    Any HTML treebuilder, present or future, should be able to pass
    these tests. With invalid markup, there's room for interpretation,
    and different parsers can handle it differently. But with the
    markup in these tests, there's not much room for interpretation.
    """

    def assertDoctypeHandled(self, doctype_fragment):
        """Assert that a given doctype string is handled correctly."""
        doctype_str, soup = self._document_with_doctype(doctype_fragment)

        # Make sure a Doctype object was created.
        doctype = soup.contents[0]
        self.assertEqual(doctype.__class__, Doctype)
        self.assertEqual(doctype, doctype_fragment)
        self.assertEqual(str(soup)[:len(doctype_str)], doctype_str)

        # Make sure that the doctype was correctly associated with the
        # parse tree and that the rest of the document parsed.
        self.assertEqual(soup.p.contents[0], 'foo')

    def _document_with_doctype(self, doctype_fragment):
        """Generate and parse a document with the given doctype."""
        doctype = '<!DOCTYPE %s>' % doctype_fragment
        markup = doctype + '\n<p>foo</p>'
        soup = self.soup(markup)
        return doctype, soup

    def test_normal_doctypes(self):
        """Make sure normal, everyday HTML doctypes are handled correctly."""
        self.assertDoctypeHandled("html")
        self.assertDoctypeHandled(
            'html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"')

    def test_empty_doctype(self):
        soup = self.soup("<!DOCTYPE>")
        doctype = soup.contents[0]
        self.assertEqual("", doctype.strip())

    def test_public_doctype_with_url(self):
        doctype = 'html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"'
        self.assertDoctypeHandled(doctype)

    def test_system_doctype(self):
        self.assertDoctypeHandled('foo SYSTEM "http://www.example.com/"')

    def test_namespaced_system_doctype(self):
        # We can handle a namespaced doctype with a system ID.
        self.assertDoctypeHandled('xsl:stylesheet SYSTEM "htmlent.dtd"')

    def test_namespaced_public_doctype(self):
        # Test a namespaced doctype with a public id.
        self.assertDoctypeHandled('xsl:stylesheet PUBLIC "htmlent.dtd"')

    def test_real_xhtml_document(self):
        """A real XHTML document should come out more or less the same as it went in."""
        markup = b"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Hello.</title></head>
<body>Goodbye.</body>
</html>"""
        soup = self.soup(markup)
        self.assertEqual(
            soup.encode("utf-8").replace(b"\n", b""),
            markup.replace(b"\n", b""))

    def test_deepcopy(self):
        """Make sure you can copy the tree builder.

        This is important because the builder is part of a
        BeautifulSoup object, and we want to be able to copy that.
        """
        copy.deepcopy(self.default_builder)

    def test_p_tag_is_never_empty_element(self):
        """A <p> tag is never designated as an empty-element tag.

        Even if the markup shows it as an empty-element tag, it
        shouldn't be presented that way.
        """
        soup = self.soup("<p/>")
        self.assertFalse(soup.p.is_empty_element)
        self.assertEqual(str(soup.p), "<p></p>")

    def test_unclosed_tags_get_closed(self):
        """A tag that's not closed by the end of the document should be closed.

        This applies to all tags except empty-element tags.
        """
        self.assertSoupEquals("<p>", "<p></p>")
        self.assertSoupEquals("<b>", "<b></b>")

        self.assertSoupEquals("<br>", "<br/>")

    def test_br_is_always_empty_element_tag(self):
        """A <br> tag is designated as an empty-element tag.

        Some parsers treat <br></br> as one <br/> tag, some parsers as
        two tags, but it should always be an empty-element tag.
        """
        soup = self.soup("<br></br>")
        self.assertTrue(soup.br.is_empty_element)
        self.assertEqual(str(soup.br), "<br/>")

    def test_nested_formatting_elements(self):
        self.assertSoupEquals("<em><em></em></em>")

    def test_comment(self):
        # Comments are represented as Comment objects.
        markup = "<p>foo<!--foobar-->baz</p>"
        self.assertSoupEquals(markup)

        soup = self.soup(markup)
        comment = soup.find(text="foobar")
        self.assertEqual(comment.__class__, Comment)

        # The comment is properly integrated into the tree.
        foo = soup.find(text="foo")
        self.assertEqual(comment, foo.next_element)
        baz = soup.find(text="baz")
        self.assertEqual(comment, baz.previous_element)

    def test_preserved_whitespace_in_pre_and_textarea(self):
        """Whitespace must be preserved in <pre> and <textarea> tags."""
        self.assertSoupEquals("<pre>   </pre>")
        self.assertSoupEquals("<textarea> woo  </textarea>")

    def test_nested_inline_elements(self):
        """Inline elements can be nested indefinitely."""
        b_tag = "<b>Inside a B tag</b>"
        self.assertSoupEquals(b_tag)

        nested_b_tag = "<p>A <i>nested <b>tag</b></i></p>"
        self.assertSoupEquals(nested_b_tag)

        double_nested_b_tag = "<p>A <a>doubly <i>nested <b>tag</b></i></a></p>"
        self.assertSoupEquals(nested_b_tag)

    def test_nested_block_level_elements(self):
        """Block elements can be nested."""
        soup = self.soup('<blockquote><p><b>Foo</b></p></blockquote>')
        blockquote = soup.blockquote
        self.assertEqual(blockquote.p.b.string, 'Foo')
        self.assertEqual(blockquote.b.string, 'Foo')

    def test_correctly_nested_tables(self):
        """One table can go inside another one."""
        markup = ('<table id="1">'
                  '<tr>'
                  "<td>Here's another table:"
                  '<table id="2">'
                  '<tr><td>foo</td></tr>'
                  '</table></td>')

        self.assertSoupEquals(
            markup,
            '<table id="1"><tr><td>Here\'s another table:'
            '<table id="2"><tr><td>foo</td></tr></table>'
            '</td></tr></table>')

        self.assertSoupEquals(
            "<table><thead><tr><td>Foo</td></tr></thead>"
            "<tbody><tr><td>Bar</td></tr></tbody>"
            "<tfoot><tr><td>Baz</td></tr></tfoot></table>")

    def test_deeply_nested_multivalued_attribute(self):
        # html5lib can set the attributes of the same tag many times
        # as it rearranges the tree. This has caused problems with
        # multivalued attributes.
        markup = '<table><div><div class="css"></div></div></table>'
        soup = self.soup(markup)
        self.assertEqual(["css"], soup.div.div['class'])

    def test_angle_brackets_in_attribute_values_are_escaped(self):
        self.assertSoupEquals('<a b="<a>"></a>', '<a b="&lt;a&gt;"></a>')

    def test_entities_in_attributes_converted_to_unicode(self):
        expect = u'<p id="pi\N{LATIN SMALL LETTER N WITH TILDE}ata"></p>'
        self.assertSoupEquals('<p id="pi&#241;ata"></p>', expect)
        self.assertSoupEquals('<p id="pi&#xf1;ata"></p>', expect)
        self.assertSoupEquals('<p id="pi&#Xf1;ata"></p>', expect)
        self.assertSoupEquals('<p id="pi&ntilde;ata"></p>', expect)

    def test_entities_in_text_converted_to_unicode(self):
        expect = u'<p>pi\N{LATIN SMALL LETTER N WITH TILDE}ata</p>'
        self.assertSoupEquals("<p>pi&#241;ata</p>", expect)
        self.assertSoupEquals("<p>pi&#xf1;ata</p>", expect)
        self.assertSoupEquals("<p>pi&#Xf1;ata</p>", expect)
        self.assertSoupEquals("<p>pi&ntilde;ata</p>", expect)

    def test_quot_entity_converted_to_quotation_mark(self):
        self.assertSoupEquals("<p>I said &quot;good day!&quot;</p>",
                              '<p>I said "good day!"</p>')

    def test_out_of_range_entity(self):
        expect = u"\N{REPLACEMENT CHARACTER}"
        self.assertSoupEquals("&#10000000000000;", expect)
        self.assertSoupEquals("&#x10000000000000;", expect)
        self.assertSoupEquals("&#1000000000;", expect)

    def test_multipart_strings(self):
        "Mostly to prevent a recurrence of a bug in the html5lib treebuilder."
        soup = self.soup("<html><h2>\nfoo</h2><p></p></html>")
        self.assertEqual("p", soup.h2.string.next_element.name)
        self.assertEqual("p", soup.p.name)

    def test_basic_namespaces(self):
        """Parsers don't need to *understand* namespaces, but at the
        very least they should not choke on namespaces or lose
        data."""

        markup = b'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:mathml="http://www.w3.org/1998/Math/MathML" xmlns:svg="http://www.w3.org/2000/svg"><head></head><body><mathml:msqrt>4</mathml:msqrt><b svg:fill="red"></b></body></html>'
        soup = self.soup(markup)
        self.assertEqual(markup, soup.encode())
        html = soup.html
        self.assertEqual('http://www.w3.org/1999/xhtml', soup.html['xmlns'])
        self.assertEqual(
            'http://www.w3.org/1998/Math/MathML', soup.html['xmlns:mathml'])
        self.assertEqual(
            'http://www.w3.org/2000/svg', soup.html['xmlns:svg'])

    def test_multivalued_attribute_value_becomes_list(self):
        markup = b'<a class="foo bar">'
        soup = self.soup(markup)
        self.assertEqual(['foo', 'bar'], soup.a['class'])

    #
    # Generally speaking, tests below this point are more tests of
    # Beautiful Soup than tests of the tree builders. But parsers are
    # weird, so we run these tests separately for every tree builder
    # to detect any differences between them.
    #

    def test_soupstrainer(self):
        """Parsers should be able to work with SoupStrainers."""
        strainer = SoupStrainer("b")
        soup = self.soup("A <b>bold</b> <meta/> <i>statement</i>",
                         parse_only=strainer)
        self.assertEqual(soup.decode(), "<b>bold</b>")

    def test_single_quote_attribute_values_become_double_quotes(self):
        self.assertSoupEquals("<foo attr='bar'></foo>",
                              '<foo attr="bar"></foo>')

    def test_attribute_values_with_nested_quotes_are_left_alone(self):
        text = """<foo attr='bar "brawls" happen'>a</foo>"""
        self.assertSoupEquals(text)

    def test_attribute_values_with_double_nested_quotes_get_quoted(self):
        text = """<foo attr='bar "brawls" happen'>a</foo>"""
        soup = self.soup(text)
        soup.foo['attr'] = 'Brawls happen at "Bob\'s Bar"'
        self.assertSoupEquals(
            soup.foo.decode(),
            """<foo attr="Brawls happen at &quot;Bob\'s Bar&quot;">a</foo>""")

    def test_ampersand_in_attribute_value_gets_escaped(self):
        self.assertSoupEquals('<this is="really messed up & stuff"></this>',
                              '<this is="really messed up &amp; stuff"></this>')

        self.assertSoupEquals(
            '<a href="http://example.org?a=1&b=2;3">foo</a>',
            '<a href="http://example.org?a=1&amp;b=2;3">foo</a>')

    def test_escaped_ampersand_in_attribute_value_is_left_alone(self):
        self.assertSoupEquals('<a href="http://example.org?a=1&amp;b=2;3"></a>')

    def test_entities_in_strings_converted_during_parsing(self):
        # Both XML and HTML entities are converted to Unicode characters
        # during parsing.
        text = "<p>&lt;&lt;sacr&eacute;&#32;bleu!&gt;&gt;</p>"
        expected = u"<p>&lt;&lt;sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</p>"
        self.assertSoupEquals(text, expected)

    def test_smart_quotes_converted_on_the_way_in(self):
        # Microsoft smart quotes are converted to Unicode characters during
        # parsing.
        quote = b"<p>\x91Foo\x92</p>"
        soup = self.soup(quote)
        self.assertEqual(
            soup.p.string,
            u"\N{LEFT SINGLE QUOTATION MARK}Foo\N{RIGHT SINGLE QUOTATION MARK}")

    def test_non_breaking_spaces_converted_on_the_way_in(self):
        soup = self.soup("<a>&nbsp;&nbsp;</a>")
        self.assertEqual(soup.a.string, u"\N{NO-BREAK SPACE}" * 2)

    def test_entities_converted_on_the_way_out(self):
        text = "<p>&lt;&lt;sacr&eacute;&#32;bleu!&gt;&gt;</p>"
        expected = u"<p>&lt;&lt;sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</p>".encode("utf-8")
        soup = self.soup(text)
        self.assertEqual(soup.p.encode("utf-8"), expected)

    def test_real_iso_latin_document(self):
        # Smoke test of interrelated functionality, using an
        # easy-to-understand document.

        # Here it is in Unicode. Note that it claims to be in ISO-Latin-1.
        unicode_html = u'<html><head><meta content="text/html; charset=ISO-Latin-1" http-equiv="Content-type"/></head><body><p>Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!</p></body></html>'

        # That's because we're going to encode it into ISO-Latin-1, and use
        # that to test.
        iso_latin_html = unicode_html.encode("iso-8859-1")

        # Parse the ISO-Latin-1 HTML.
        soup = self.soup(iso_latin_html)
        # Encode it to UTF-8.
        result = soup.encode("utf-8")

        # What do we expect the result to look like? Well, it would
        # look like unicode_html, except that the META tag would say
        # UTF-8 instead of ISO-Latin-1.
        expected = unicode_html.replace("ISO-Latin-1", "utf-8")

        # And, of course, it would be in UTF-8, not Unicode.
        expected = expected.encode("utf-8")

        # Ta-da!
        self.assertEqual(result, expected)

    def test_real_shift_jis_document(self):
        # Smoke test to make sure the parser can handle a document in
        # Shift-JIS encoding, without choking.
        shift_jis_html = (
            b'<html><head></head><body><pre>'
            b'\x82\xb1\x82\xea\x82\xcdShift-JIS\x82\xc5\x83R\x81[\x83f'
            b'\x83B\x83\x93\x83O\x82\xb3\x82\xea\x82\xbd\x93\xfa\x96{\x8c'
            b'\xea\x82\xcc\x83t\x83@\x83C\x83\x8b\x82\xc5\x82\xb7\x81B'
            b'</pre></body></html>')
        unicode_html = shift_jis_html.decode("shift-jis")
        soup = self.soup(unicode_html)

        # Make sure the parse tree is correctly encoded to various
        # encodings.
        self.assertEqual(soup.encode("utf-8"), unicode_html.encode("utf-8"))
        self.assertEqual(soup.encode("euc_jp"), unicode_html.encode("euc_jp"))

    def test_real_hebrew_document(self):
        # A real-world test to make sure we can convert ISO-8859-9 (a
        # Hebrew encoding) to UTF-8.
        hebrew_document = b'<html><head><title>Hebrew (ISO 8859-8) in Visual Directionality</title></head><body><h1>Hebrew (ISO 8859-8) in Visual Directionality</h1>\xed\xe5\xec\xf9</body></html>'
        soup = self.soup(
            hebrew_document, from_encoding="iso8859-8")
        self.assertEqual(soup.original_encoding, 'iso8859-8')
        self.assertEqual(
            soup.encode('utf-8'),
            hebrew_document.decode("iso8859-8").encode("utf-8"))

    def test_meta_tag_reflects_current_encoding(self):
        # Here's the <meta> tag saying that a document is
        # encoded in Shift-JIS.
        meta_tag = ('<meta content="text/html; charset=x-sjis" '
                    'http-equiv="Content-type"/>')

        # Here's a document incorporating that meta tag.
        shift_jis_html = (
            '<html><head>\n%s\n'
            '<meta http-equiv="Content-language" content="ja"/>'
            '</head><body>Shift-JIS markup goes here.') % meta_tag
        soup = self.soup(shift_jis_html)

        # Parse the document, and the charset is seemingly unaffected.
        parsed_meta = soup.find('meta', {'http-equiv': 'Content-type'})
        content = parsed_meta['content']
        self.assertEqual('text/html; charset=x-sjis', content)

        # But that value is actually a ContentMetaAttributeValue object.
        self.assertTrue(isinstance(content, ContentMetaAttributeValue))

        # And it will take on a value that reflects its current
        # encoding.
        self.assertEqual('text/html; charset=utf8', content.encode("utf8"))

        # For the rest of the story, see TestSubstitutions in
        # test_tree.py.

    def test_html5_style_meta_tag_reflects_current_encoding(self):
        # Here's the <meta> tag saying that a document is
        # encoded in Shift-JIS.
        meta_tag = ('<meta id="encoding" charset="x-sjis" />')

        # Here's a document incorporating that meta tag.
        shift_jis_html = (
            '<html><head>\n%s\n'
            '<meta http-equiv="Content-language" content="ja"/>'
            '</head><body>Shift-JIS markup goes here.') % meta_tag
        soup = self.soup(shift_jis_html)

        # Parse the document, and the charset is seemingly unaffected.
        parsed_meta = soup.find('meta', id="encoding")
        charset = parsed_meta['charset']
        self.assertEqual('x-sjis', charset)

        # But that value is actually a CharsetMetaAttributeValue object.
        self.assertTrue(isinstance(charset, CharsetMetaAttributeValue))

        # And it will take on a value that reflects its current
        # encoding.
        self.assertEqual('utf8', charset.encode("utf8"))

    def test_tag_with_no_attributes_can_have_attributes_added(self):
        data = self.soup("<a>text</a>")
        data.a['foo'] = 'bar'
        self.assertEqual('<a foo="bar">text</a>', data.a.decode())

class XMLTreeBuilderSmokeTest(object):

    def test_docstring_generated(self):
        soup = self.soup("<root/>")
        self.assertEqual(
            soup.encode(), b'<?xml version="1.0" encoding="utf-8"?>\n<root/>')

    def test_real_xhtml_document(self):
        """A real XHTML document should come out *exactly* the same as it went in."""
        markup = b"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Hello.</title></head>
<body>Goodbye.</body>
</html>"""
        soup = self.soup(markup)
        self.assertEqual(
            soup.encode("utf-8"), markup)

    def test_formatter_processes_script_tag_for_xml_documents(self):
        doc = """
  <script type="text/javascript">
  </script>
"""
        soup = BeautifulSoup(doc, "xml")
        # lxml would have stripped this while parsing, but we can add
        # it later.
        soup.script.string = 'console.log("< < hey > > ");'
        encoded = soup.encode()
        self.assertTrue(b"&lt; &lt; hey &gt; &gt;" in encoded)

    def test_popping_namespaced_tag(self):
        markup = '<rss xmlns:dc="foo"><dc:creator>b</dc:creator><dc:date>2012-07-02T20:33:42Z</dc:date><dc:rights>c</dc:rights><image>d</image></rss>'
        soup = self.soup(markup)
        self.assertEqual(
            unicode(soup.rss), markup)

    def test_docstring_includes_correct_encoding(self):
        soup = self.soup("<root/>")
        self.assertEqual(
            soup.encode("latin1"),
            b'<?xml version="1.0" encoding="latin1"?>\n<root/>')

    def test_large_xml_document(self):
        """A large XML document should come out the same as it went in."""
        markup = (b'<?xml version="1.0" encoding="utf-8"?>\n<root>'
                  + b'0' * (2**12)
                  + b'</root>')
        soup = self.soup(markup)
        self.assertEqual(soup.encode("utf-8"), markup)


    def test_tags_are_empty_element_if_and_only_if_they_are_empty(self):
        self.assertSoupEquals("<p>", "<p/>")
        self.assertSoupEquals("<p>foo</p>")

    def test_namespaces_are_preserved(self):
        markup = '<root xmlns:a="http://example.com/" xmlns:b="http://example.net/"><a:foo>This tag is in the a namespace</a:foo><b:foo>This tag is in the b namespace</b:foo></root>'
        soup = self.soup(markup)
        root = soup.root
        self.assertEqual("http://example.com/", root['xmlns:a'])
        self.assertEqual("http://example.net/", root['xmlns:b'])

    def test_closing_namespaced_tag(self):
        markup = '<p xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:date>20010504</dc:date></p>'
        soup = self.soup(markup)
        self.assertEqual(unicode(soup.p), markup)

    def test_namespaced_attributes(self):
        markup = '<foo xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><bar xsi:schemaLocation="http://www.example.com"/></foo>'
        soup = self.soup(markup)
        self.assertEqual(unicode(soup.foo), markup)

    def test_namespaced_attributes_xml_namespace(self):
        markup = '<foo xml:lang="fr">bar</foo>'
        soup = self.soup(markup)
        self.assertEqual(unicode(soup.foo), markup)

class HTML5TreeBuilderSmokeTest(HTMLTreeBuilderSmokeTest):
    """Smoke test for a tree builder that supports HTML5."""

    def test_real_xhtml_document(self):
        # Since XHTML is not HTML5, HTML5 parsers are not tested to handle
        # XHTML documents in any particular way.
        pass

    def test_html_tags_have_namespace(self):
        markup = "<a>"
        soup = self.soup(markup)
        self.assertEqual("http://www.w3.org/1999/xhtml", soup.a.namespace)

    def test_svg_tags_have_namespace(self):
        markup = '<svg><circle/></svg>'
        soup = self.soup(markup)
        namespace = "http://www.w3.org/2000/svg"
        self.assertEqual(namespace, soup.svg.namespace)
        self.assertEqual(namespace, soup.circle.namespace)


    def test_mathml_tags_have_namespace(self):
        markup = '<math><msqrt>5</msqrt></math>'
        soup = self.soup(markup)
        namespace = 'http://www.w3.org/1998/Math/MathML'
        self.assertEqual(namespace, soup.math.namespace)
        self.assertEqual(namespace, soup.msqrt.namespace)

    def test_xml_declaration_becomes_comment(self):
        markup = '<?xml version="1.0" encoding="utf-8"?><html></html>'
        soup = self.soup(markup)
        self.assertTrue(isinstance(soup.contents[0], Comment))
        self.assertEqual(soup.contents[0], '?xml version="1.0" encoding="utf-8"?')
        self.assertEqual("html", soup.contents[0].next_element.name)

def skipIf(condition, reason):
   def nothing(test, *args, **kwargs):
       return None

   def decorator(test_item):
       if condition:
           return nothing
       else:
           return test_item

   return decorator

########NEW FILE########
__FILENAME__ = test_builder_registry
"""Tests of the builder registry."""

import unittest

from bs4 import BeautifulSoup
from bs4.builder import (
    builder_registry as registry,
    HTMLParserTreeBuilder,
    TreeBuilderRegistry,
)

try:
    from bs4.builder import HTML5TreeBuilder
    HTML5LIB_PRESENT = True
except ImportError:
    HTML5LIB_PRESENT = False

try:
    from bs4.builder import (
        LXMLTreeBuilderForXML,
        LXMLTreeBuilder,
        )
    LXML_PRESENT = True
except ImportError:
    LXML_PRESENT = False


class BuiltInRegistryTest(unittest.TestCase):
    """Test the built-in registry with the default builders registered."""

    def test_combination(self):
        if LXML_PRESENT:
            self.assertEqual(registry.lookup('fast', 'html'),
                             LXMLTreeBuilder)

        if LXML_PRESENT:
            self.assertEqual(registry.lookup('permissive', 'xml'),
                             LXMLTreeBuilderForXML)
        self.assertEqual(registry.lookup('strict', 'html'),
                          HTMLParserTreeBuilder)
        if HTML5LIB_PRESENT:
            self.assertEqual(registry.lookup('html5lib', 'html'),
                              HTML5TreeBuilder)

    def test_lookup_by_markup_type(self):
        if LXML_PRESENT:
            self.assertEqual(registry.lookup('html'), LXMLTreeBuilder)
            self.assertEqual(registry.lookup('xml'), LXMLTreeBuilderForXML)
        else:
            self.assertEqual(registry.lookup('xml'), None)
            if HTML5LIB_PRESENT:
                self.assertEqual(registry.lookup('html'), HTML5TreeBuilder)
            else:
                self.assertEqual(registry.lookup('html'), HTMLParserTreeBuilder)

    def test_named_library(self):
        if LXML_PRESENT:
            self.assertEqual(registry.lookup('lxml', 'xml'),
                             LXMLTreeBuilderForXML)
            self.assertEqual(registry.lookup('lxml', 'html'),
                             LXMLTreeBuilder)
        if HTML5LIB_PRESENT:
            self.assertEqual(registry.lookup('html5lib'),
                              HTML5TreeBuilder)

        self.assertEqual(registry.lookup('html.parser'),
                          HTMLParserTreeBuilder)

    def test_beautifulsoup_constructor_does_lookup(self):
        # You can pass in a string.
        BeautifulSoup("", features="html")
        # Or a list of strings.
        BeautifulSoup("", features=["html", "fast"])

        # You'll get an exception if BS can't find an appropriate
        # builder.
        self.assertRaises(ValueError, BeautifulSoup,
                          "", features="no-such-feature")

class RegistryTest(unittest.TestCase):
    """Test the TreeBuilderRegistry class in general."""

    def setUp(self):
        self.registry = TreeBuilderRegistry()

    def builder_for_features(self, *feature_list):
        cls = type('Builder_' + '_'.join(feature_list),
                   (object,), {'features' : feature_list})

        self.registry.register(cls)
        return cls

    def test_register_with_no_features(self):
        builder = self.builder_for_features()

        # Since the builder advertises no features, you can't find it
        # by looking up features.
        self.assertEqual(self.registry.lookup('foo'), None)

        # But you can find it by doing a lookup with no features, if
        # this happens to be the only registered builder.
        self.assertEqual(self.registry.lookup(), builder)

    def test_register_with_features_makes_lookup_succeed(self):
        builder = self.builder_for_features('foo', 'bar')
        self.assertEqual(self.registry.lookup('foo'), builder)
        self.assertEqual(self.registry.lookup('bar'), builder)

    def test_lookup_fails_when_no_builder_implements_feature(self):
        builder = self.builder_for_features('foo', 'bar')
        self.assertEqual(self.registry.lookup('baz'), None)

    def test_lookup_gets_most_recent_registration_when_no_feature_specified(self):
        builder1 = self.builder_for_features('foo')
        builder2 = self.builder_for_features('bar')
        self.assertEqual(self.registry.lookup(), builder2)

    def test_lookup_fails_when_no_tree_builders_registered(self):
        self.assertEqual(self.registry.lookup(), None)

    def test_lookup_gets_most_recent_builder_supporting_all_features(self):
        has_one = self.builder_for_features('foo')
        has_the_other = self.builder_for_features('bar')
        has_both_early = self.builder_for_features('foo', 'bar', 'baz')
        has_both_late = self.builder_for_features('foo', 'bar', 'quux')
        lacks_one = self.builder_for_features('bar')
        has_the_other = self.builder_for_features('foo')

        # There are two builders featuring 'foo' and 'bar', but
        # the one that also features 'quux' was registered later.
        self.assertEqual(self.registry.lookup('foo', 'bar'),
                          has_both_late)

        # There is only one builder featuring 'foo', 'bar', and 'baz'.
        self.assertEqual(self.registry.lookup('foo', 'bar', 'baz'),
                          has_both_early)

    def test_lookup_fails_when_cannot_reconcile_requested_features(self):
        builder1 = self.builder_for_features('foo', 'bar')
        builder2 = self.builder_for_features('foo', 'baz')
        self.assertEqual(self.registry.lookup('bar', 'baz'), None)

########NEW FILE########
__FILENAME__ = test_docs
"Test harness for doctests."

# pylint: disable-msg=E0611,W0142

__metaclass__ = type
__all__ = [
    'additional_tests',
    ]

import atexit
import doctest
import os
#from pkg_resources import (
#    resource_filename, resource_exists, resource_listdir, cleanup_resources)
import unittest

DOCTEST_FLAGS = (
    doctest.ELLIPSIS |
    doctest.NORMALIZE_WHITESPACE |
    doctest.REPORT_NDIFF)


# def additional_tests():
#     "Run the doc tests (README.txt and docs/*, if any exist)"
#     doctest_files = [
#         os.path.abspath(resource_filename('bs4', 'README.txt'))]
#     if resource_exists('bs4', 'docs'):
#         for name in resource_listdir('bs4', 'docs'):
#             if name.endswith('.txt'):
#                 doctest_files.append(
#                     os.path.abspath(
#                         resource_filename('bs4', 'docs/%s' % name)))
#     kwargs = dict(module_relative=False, optionflags=DOCTEST_FLAGS)
#     atexit.register(cleanup_resources)
#     return unittest.TestSuite((
#         doctest.DocFileSuite(*doctest_files, **kwargs)))

########NEW FILE########
__FILENAME__ = test_html5lib
"""Tests to ensure that the html5lib tree builder generates good trees."""

import warnings

try:
    from bs4.builder import HTML5TreeBuilder
    HTML5LIB_PRESENT = True
except ImportError, e:
    HTML5LIB_PRESENT = False
from bs4.element import SoupStrainer
from bs4.testing import (
    HTML5TreeBuilderSmokeTest,
    SoupTest,
    skipIf,
)

@skipIf(
    not HTML5LIB_PRESENT,
    "html5lib seems not to be present, not testing its tree builder.")
class HTML5LibBuilderSmokeTest(SoupTest, HTML5TreeBuilderSmokeTest):
    """See ``HTML5TreeBuilderSmokeTest``."""

    @property
    def default_builder(self):
        return HTML5TreeBuilder()

    def test_soupstrainer(self):
        # The html5lib tree builder does not support SoupStrainers.
        strainer = SoupStrainer("b")
        markup = "<p>A <b>bold</b> statement.</p>"
        with warnings.catch_warnings(record=True) as w:
            soup = self.soup(markup, parse_only=strainer)
        self.assertEqual(
            soup.decode(), self.document_for(markup))

        self.assertTrue(
            "the html5lib tree builder doesn't support parse_only" in
            str(w[0].message))

    def test_correctly_nested_tables(self):
        """html5lib inserts <tbody> tags where other parsers don't."""
        markup = ('<table id="1">'
                  '<tr>'
                  "<td>Here's another table:"
                  '<table id="2">'
                  '<tr><td>foo</td></tr>'
                  '</table></td>')

        self.assertSoupEquals(
            markup,
            '<table id="1"><tbody><tr><td>Here\'s another table:'
            '<table id="2"><tbody><tr><td>foo</td></tr></tbody></table>'
            '</td></tr></tbody></table>')

        self.assertSoupEquals(
            "<table><thead><tr><td>Foo</td></tr></thead>"
            "<tbody><tr><td>Bar</td></tr></tbody>"
            "<tfoot><tr><td>Baz</td></tr></tfoot></table>")

    def test_xml_declaration_followed_by_doctype(self):
        markup = '''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html>
  <head>
  </head>
  <body>
   <p>foo</p>
  </body>
</html>'''
        soup = self.soup(markup)
        # Verify that we can reach the <p> tag; this means the tree is connected.
        self.assertEqual(b"<p>foo</p>", soup.p.encode())

########NEW FILE########
__FILENAME__ = test_htmlparser
"""Tests to ensure that the html.parser tree builder generates good
trees."""

from bs4.testing import SoupTest, HTMLTreeBuilderSmokeTest
from bs4.builder import HTMLParserTreeBuilder

class HTMLParserTreeBuilderSmokeTest(SoupTest, HTMLTreeBuilderSmokeTest):

    @property
    def default_builder(self):
        return HTMLParserTreeBuilder()

    def test_namespaced_system_doctype(self):
        # html.parser can't handle namespaced doctypes, so skip this one.
        pass

    def test_namespaced_public_doctype(self):
        # html.parser can't handle namespaced doctypes, so skip this one.
        pass

########NEW FILE########
__FILENAME__ = test_lxml
"""Tests to ensure that the lxml tree builder generates good trees."""

import re
import warnings

try:
    from bs4.builder import LXMLTreeBuilder, LXMLTreeBuilderForXML
    LXML_PRESENT = True
    import lxml.etree
    LXML_VERSION = lxml.etree.LXML_VERSION
except ImportError, e:
    LXML_PRESENT = False
    LXML_VERSION = (0,)

from bs4 import (
    BeautifulSoup,
    BeautifulStoneSoup,
    )
from bs4.element import Comment, Doctype, SoupStrainer
from bs4.testing import skipIf
from bs4.tests import test_htmlparser
from bs4.testing import (
    HTMLTreeBuilderSmokeTest,
    XMLTreeBuilderSmokeTest,
    SoupTest,
    skipIf,
)

@skipIf(
    not LXML_PRESENT,
    "lxml seems not to be present, not testing its tree builder.")
class LXMLTreeBuilderSmokeTest(SoupTest, HTMLTreeBuilderSmokeTest):
    """See ``HTMLTreeBuilderSmokeTest``."""

    @property
    def default_builder(self):
        return LXMLTreeBuilder()

    def test_out_of_range_entity(self):
        self.assertSoupEquals(
            "<p>foo&#10000000000000;bar</p>", "<p>foobar</p>")
        self.assertSoupEquals(
            "<p>foo&#x10000000000000;bar</p>", "<p>foobar</p>")
        self.assertSoupEquals(
            "<p>foo&#1000000000;bar</p>", "<p>foobar</p>")

    # In lxml < 2.3.5, an empty doctype causes a segfault. Skip this
    # test if an old version of lxml is installed.

    @skipIf(
        not LXML_PRESENT or LXML_VERSION < (2,3,5,0),
        "Skipping doctype test for old version of lxml to avoid segfault.")
    def test_empty_doctype(self):
        soup = self.soup("<!DOCTYPE>")
        doctype = soup.contents[0]
        self.assertEqual("", doctype.strip())

    def test_beautifulstonesoup_is_xml_parser(self):
        # Make sure that the deprecated BSS class uses an xml builder
        # if one is installed.
        with warnings.catch_warnings(record=False) as w:
            soup = BeautifulStoneSoup("<b />")
            self.assertEqual(u"<b/>", unicode(soup.b))

    def test_real_xhtml_document(self):
        """lxml strips the XML definition from an XHTML doc, which is fine."""
        markup = b"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Hello.</title></head>
<body>Goodbye.</body>
</html>"""
        soup = self.soup(markup)
        self.assertEqual(
            soup.encode("utf-8").replace(b"\n", b''),
            markup.replace(b'\n', b'').replace(
                b'<?xml version="1.0" encoding="utf-8"?>', b''))


@skipIf(
    not LXML_PRESENT,
    "lxml seems not to be present, not testing its XML tree builder.")
class LXMLXMLTreeBuilderSmokeTest(SoupTest, XMLTreeBuilderSmokeTest):
    """See ``HTMLTreeBuilderSmokeTest``."""

    @property
    def default_builder(self):
        return LXMLTreeBuilderForXML()

########NEW FILE########
__FILENAME__ = test_soup
# -*- coding: utf-8 -*-
"""Tests of Beautiful Soup as a whole."""

import logging
import unittest
import sys
from bs4 import (
    BeautifulSoup,
    BeautifulStoneSoup,
)
from bs4.element import (
    CharsetMetaAttributeValue,
    ContentMetaAttributeValue,
    SoupStrainer,
    NamespacedAttribute,
    )
import bs4.dammit
from bs4.dammit import EntitySubstitution, UnicodeDammit
from bs4.testing import (
    SoupTest,
    skipIf,
)
import warnings

try:
    from bs4.builder import LXMLTreeBuilder, LXMLTreeBuilderForXML
    LXML_PRESENT = True
except ImportError, e:
    LXML_PRESENT = False

PYTHON_2_PRE_2_7 = (sys.version_info < (2,7))
PYTHON_3_PRE_3_2 = (sys.version_info[0] == 3 and sys.version_info < (3,2))

class TestDeprecatedConstructorArguments(SoupTest):

    def test_parseOnlyThese_renamed_to_parse_only(self):
        with warnings.catch_warnings(record=True) as w:
            soup = self.soup("<a><b></b></a>", parseOnlyThese=SoupStrainer("b"))
        msg = str(w[0].message)
        self.assertTrue("parseOnlyThese" in msg)
        self.assertTrue("parse_only" in msg)
        self.assertEqual(b"<b></b>", soup.encode())

    def test_fromEncoding_renamed_to_from_encoding(self):
        with warnings.catch_warnings(record=True) as w:
            utf8 = b"\xc3\xa9"
            soup = self.soup(utf8, fromEncoding="utf8")
        msg = str(w[0].message)
        self.assertTrue("fromEncoding" in msg)
        self.assertTrue("from_encoding" in msg)
        self.assertEqual("utf8", soup.original_encoding)

    def test_unrecognized_keyword_argument(self):
        self.assertRaises(
            TypeError, self.soup, "<a>", no_such_argument=True)

    @skipIf(
        not LXML_PRESENT,
        "lxml not present, not testing BeautifulStoneSoup.")
    def test_beautifulstonesoup(self):
        with warnings.catch_warnings(record=True) as w:
            soup = BeautifulStoneSoup("<markup>")
            self.assertTrue(isinstance(soup, BeautifulSoup))
            self.assertTrue("BeautifulStoneSoup class is deprecated")

class TestSelectiveParsing(SoupTest):

    def test_parse_with_soupstrainer(self):
        markup = "No<b>Yes</b><a>No<b>Yes <c>Yes</c></b>"
        strainer = SoupStrainer("b")
        soup = self.soup(markup, parse_only=strainer)
        self.assertEqual(soup.encode(), b"<b>Yes</b><b>Yes <c>Yes</c></b>")


class TestEntitySubstitution(unittest.TestCase):
    """Standalone tests of the EntitySubstitution class."""
    def setUp(self):
        self.sub = EntitySubstitution

    def test_simple_html_substitution(self):
        # Unicode characters corresponding to named HTML entites
        # are substituted, and no others.
        s = u"foo\u2200\N{SNOWMAN}\u00f5bar"
        self.assertEqual(self.sub.substitute_html(s),
                          u"foo&forall;\N{SNOWMAN}&otilde;bar")

    def test_smart_quote_substitution(self):
        # MS smart quotes are a common source of frustration, so we
        # give them a special test.
        quotes = b"\x91\x92foo\x93\x94"
        dammit = UnicodeDammit(quotes)
        self.assertEqual(self.sub.substitute_html(dammit.markup),
                          "&lsquo;&rsquo;foo&ldquo;&rdquo;")

    def test_xml_converstion_includes_no_quotes_if_make_quoted_attribute_is_false(self):
        s = 'Welcome to "my bar"'
        self.assertEqual(self.sub.substitute_xml(s, False), s)

    def test_xml_attribute_quoting_normally_uses_double_quotes(self):
        self.assertEqual(self.sub.substitute_xml("Welcome", True),
                          '"Welcome"')
        self.assertEqual(self.sub.substitute_xml("Bob's Bar", True),
                          '"Bob\'s Bar"')

    def test_xml_attribute_quoting_uses_single_quotes_when_value_contains_double_quotes(self):
        s = 'Welcome to "my bar"'
        self.assertEqual(self.sub.substitute_xml(s, True),
                          "'Welcome to \"my bar\"'")

    def test_xml_attribute_quoting_escapes_single_quotes_when_value_contains_both_single_and_double_quotes(self):
        s = 'Welcome to "Bob\'s Bar"'
        self.assertEqual(
            self.sub.substitute_xml(s, True),
            '"Welcome to &quot;Bob\'s Bar&quot;"')

    def test_xml_quotes_arent_escaped_when_value_is_not_being_quoted(self):
        quoted = 'Welcome to "Bob\'s Bar"'
        self.assertEqual(self.sub.substitute_xml(quoted), quoted)

    def test_xml_quoting_handles_angle_brackets(self):
        self.assertEqual(
            self.sub.substitute_xml("foo<bar>"),
            "foo&lt;bar&gt;")

    def test_xml_quoting_handles_ampersands(self):
        self.assertEqual(self.sub.substitute_xml("AT&T"), "AT&amp;T")

    def test_xml_quoting_including_ampersands_when_they_are_part_of_an_entity(self):
        self.assertEqual(
            self.sub.substitute_xml("&Aacute;T&T"),
            "&amp;Aacute;T&amp;T")

    def test_xml_quoting_ignoring_ampersands_when_they_are_part_of_an_entity(self):
        self.assertEqual(
            self.sub.substitute_xml_containing_entities("&Aacute;T&T"),
            "&Aacute;T&amp;T")

    def test_quotes_not_html_substituted(self):
        """There's no need to do this except inside attribute values."""
        text = 'Bob\'s "bar"'
        self.assertEqual(self.sub.substitute_html(text), text)


class TestEncodingConversion(SoupTest):
    # Test Beautiful Soup's ability to decode and encode from various
    # encodings.

    def setUp(self):
        super(TestEncodingConversion, self).setUp()
        self.unicode_data = u'<html><head><meta charset="utf-8"/></head><body><foo>Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!</foo></body></html>'
        self.utf8_data = self.unicode_data.encode("utf-8")
        # Just so you know what it looks like.
        self.assertEqual(
            self.utf8_data,
            b'<html><head><meta charset="utf-8"/></head><body><foo>Sacr\xc3\xa9 bleu!</foo></body></html>')

    def test_ascii_in_unicode_out(self):
        # ASCII input is converted to Unicode. The original_encoding
        # attribute is set.
        ascii = b"<foo>a</foo>"
        soup_from_ascii = self.soup(ascii)
        unicode_output = soup_from_ascii.decode()
        self.assertTrue(isinstance(unicode_output, unicode))
        self.assertEqual(unicode_output, self.document_for(ascii.decode()))
        self.assertEqual(soup_from_ascii.original_encoding.lower(), "ascii")

    def test_unicode_in_unicode_out(self):
        # Unicode input is left alone. The original_encoding attribute
        # is not set.
        soup_from_unicode = self.soup(self.unicode_data)
        self.assertEqual(soup_from_unicode.decode(), self.unicode_data)
        self.assertEqual(soup_from_unicode.foo.string, u'Sacr\xe9 bleu!')
        self.assertEqual(soup_from_unicode.original_encoding, None)

    def test_utf8_in_unicode_out(self):
        # UTF-8 input is converted to Unicode. The original_encoding
        # attribute is set.
        soup_from_utf8 = self.soup(self.utf8_data)
        self.assertEqual(soup_from_utf8.decode(), self.unicode_data)
        self.assertEqual(soup_from_utf8.foo.string, u'Sacr\xe9 bleu!')

    def test_utf8_out(self):
        # The internal data structures can be encoded as UTF-8.
        soup_from_unicode = self.soup(self.unicode_data)
        self.assertEqual(soup_from_unicode.encode('utf-8'), self.utf8_data)

    @skipIf(
        PYTHON_2_PRE_2_7 or PYTHON_3_PRE_3_2,
        "Bad HTMLParser detected; skipping test of non-ASCII characters in attribute name.")
    def test_attribute_name_containing_unicode_characters(self):
        markup = u'<div><a \N{SNOWMAN}="snowman"></a></div>'
        self.assertEqual(self.soup(markup).div.encode("utf8"), markup.encode("utf8"))

class TestUnicodeDammit(unittest.TestCase):
    """Standalone tests of Unicode, Dammit."""

    def test_smart_quotes_to_unicode(self):
        markup = b"<foo>\x91\x92\x93\x94</foo>"
        dammit = UnicodeDammit(markup)
        self.assertEqual(
            dammit.unicode_markup, u"<foo>\u2018\u2019\u201c\u201d</foo>")

    def test_smart_quotes_to_xml_entities(self):
        markup = b"<foo>\x91\x92\x93\x94</foo>"
        dammit = UnicodeDammit(markup, smart_quotes_to="xml")
        self.assertEqual(
            dammit.unicode_markup, "<foo>&#x2018;&#x2019;&#x201C;&#x201D;</foo>")

    def test_smart_quotes_to_html_entities(self):
        markup = b"<foo>\x91\x92\x93\x94</foo>"
        dammit = UnicodeDammit(markup, smart_quotes_to="html")
        self.assertEqual(
            dammit.unicode_markup, "<foo>&lsquo;&rsquo;&ldquo;&rdquo;</foo>")

    def test_smart_quotes_to_ascii(self):
        markup = b"<foo>\x91\x92\x93\x94</foo>"
        dammit = UnicodeDammit(markup, smart_quotes_to="ascii")
        self.assertEqual(
            dammit.unicode_markup, """<foo>''""</foo>""")

    def test_detect_utf8(self):
        utf8 = b"\xc3\xa9"
        dammit = UnicodeDammit(utf8)
        self.assertEqual(dammit.unicode_markup, u'\xe9')
        self.assertEqual(dammit.original_encoding.lower(), 'utf-8')

    def test_convert_hebrew(self):
        hebrew = b"\xed\xe5\xec\xf9"
        dammit = UnicodeDammit(hebrew, ["iso-8859-8"])
        self.assertEqual(dammit.original_encoding.lower(), 'iso-8859-8')
        self.assertEqual(dammit.unicode_markup, u'\u05dd\u05d5\u05dc\u05e9')

    def test_dont_see_smart_quotes_where_there_are_none(self):
        utf_8 = b"\343\202\261\343\203\274\343\202\277\343\202\244 Watch"
        dammit = UnicodeDammit(utf_8)
        self.assertEqual(dammit.original_encoding.lower(), 'utf-8')
        self.assertEqual(dammit.unicode_markup.encode("utf-8"), utf_8)

    def test_ignore_inappropriate_codecs(self):
        utf8_data = u"Räksmörgås".encode("utf-8")
        dammit = UnicodeDammit(utf8_data, ["iso-8859-8"])
        self.assertEqual(dammit.original_encoding.lower(), 'utf-8')

    def test_ignore_invalid_codecs(self):
        utf8_data = u"Räksmörgås".encode("utf-8")
        for bad_encoding in ['.utf8', '...', 'utF---16.!']:
            dammit = UnicodeDammit(utf8_data, [bad_encoding])
            self.assertEqual(dammit.original_encoding.lower(), 'utf-8')

    def test_detect_html5_style_meta_tag(self):

        for data in (
            b'<html><meta charset="euc-jp" /></html>',
            b"<html><meta charset='euc-jp' /></html>",
            b"<html><meta charset=euc-jp /></html>",
            b"<html><meta charset=euc-jp/></html>"):
            dammit = UnicodeDammit(data, is_html=True)
            self.assertEqual(
                "euc-jp", dammit.original_encoding)

    def test_last_ditch_entity_replacement(self):
        # This is a UTF-8 document that contains bytestrings
        # completely incompatible with UTF-8 (ie. encoded with some other
        # encoding).
        #
        # Since there is no consistent encoding for the document,
        # Unicode, Dammit will eventually encode the document as UTF-8
        # and encode the incompatible characters as REPLACEMENT
        # CHARACTER.
        #
        # If chardet is installed, it will detect that the document
        # can be converted into ISO-8859-1 without errors. This happens
        # to be the wrong encoding, but it is a consistent encoding, so the
        # code we're testing here won't run.
        #
        # So we temporarily disable chardet if it's present.
        doc = b"""\357\273\277<?xml version="1.0" encoding="UTF-8"?>
<html><b>\330\250\330\252\330\261</b>
<i>\310\322\321\220\312\321\355\344</i></html>"""
        chardet = bs4.dammit.chardet_dammit
        logging.disable(logging.WARNING)
        try:
            def noop(str):
                return None
            bs4.dammit.chardet_dammit = noop
            dammit = UnicodeDammit(doc)
            self.assertEqual(True, dammit.contains_replacement_characters)
            self.assertTrue(u"\ufffd" in dammit.unicode_markup)

            soup = BeautifulSoup(doc, "html.parser")
            self.assertTrue(soup.contains_replacement_characters)
        finally:
            logging.disable(logging.NOTSET)
            bs4.dammit.chardet_dammit = chardet

    def test_sniffed_xml_encoding(self):
        # A document written in UTF-16LE will be converted by a different
        # code path that sniffs the byte order markers.
        data = b'\xff\xfe<\x00a\x00>\x00\xe1\x00\xe9\x00<\x00/\x00a\x00>\x00'
        dammit = UnicodeDammit(data)
        self.assertEqual(u"<a>áé</a>", dammit.unicode_markup)
        self.assertEqual("utf-16le", dammit.original_encoding)

    def test_detwingle(self):
        # Here's a UTF8 document.
        utf8 = (u"\N{SNOWMAN}" * 3).encode("utf8")

        # Here's a Windows-1252 document.
        windows_1252 = (
            u"\N{LEFT DOUBLE QUOTATION MARK}Hi, I like Windows!"
            u"\N{RIGHT DOUBLE QUOTATION MARK}").encode("windows_1252")

        # Through some unholy alchemy, they've been stuck together.
        doc = utf8 + windows_1252 + utf8

        # The document can't be turned into UTF-8:
        self.assertRaises(UnicodeDecodeError, doc.decode, "utf8")

        # Unicode, Dammit thinks the whole document is Windows-1252,
        # and decodes it into "â˜ƒâ˜ƒâ˜ƒ“Hi, I like Windows!”â˜ƒâ˜ƒâ˜ƒ"

        # But if we run it through fix_embedded_windows_1252, it's fixed:

        fixed = UnicodeDammit.detwingle(doc)
        self.assertEqual(
            u"☃☃☃“Hi, I like Windows!”☃☃☃", fixed.decode("utf8"))

    def test_detwingle_ignores_multibyte_characters(self):
        # Each of these characters has a UTF-8 representation ending
        # in \x93. \x93 is a smart quote if interpreted as
        # Windows-1252. But our code knows to skip over multibyte
        # UTF-8 characters, so they'll survive the process unscathed.
        for tricky_unicode_char in (
            u"\N{LATIN SMALL LIGATURE OE}", # 2-byte char '\xc5\x93'
            u"\N{LATIN SUBSCRIPT SMALL LETTER X}", # 3-byte char '\xe2\x82\x93'
            u"\xf0\x90\x90\x93", # This is a CJK character, not sure which one.
            ):
            input = tricky_unicode_char.encode("utf8")
            self.assertTrue(input.endswith(b'\x93'))
            output = UnicodeDammit.detwingle(input)
            self.assertEqual(output, input)

class TestNamedspacedAttribute(SoupTest):

    def test_name_may_be_none(self):
        a = NamespacedAttribute("xmlns", None)
        self.assertEqual(a, "xmlns")

    def test_attribute_is_equivalent_to_colon_separated_string(self):
        a = NamespacedAttribute("a", "b")
        self.assertEqual("a:b", a)

    def test_attributes_are_equivalent_if_prefix_and_name_identical(self):
        a = NamespacedAttribute("a", "b", "c")
        b = NamespacedAttribute("a", "b", "c")
        self.assertEqual(a, b)

        # The actual namespace is not considered.
        c = NamespacedAttribute("a", "b", None)
        self.assertEqual(a, c)

        # But name and prefix are important.
        d = NamespacedAttribute("a", "z", "c")
        self.assertNotEqual(a, d)

        e = NamespacedAttribute("z", "b", "c")
        self.assertNotEqual(a, e)


class TestAttributeValueWithCharsetSubstitution(unittest.TestCase):

    def test_content_meta_attribute_value(self):
        value = CharsetMetaAttributeValue("euc-jp")
        self.assertEqual("euc-jp", value)
        self.assertEqual("euc-jp", value.original_value)
        self.assertEqual("utf8", value.encode("utf8"))


    def test_content_meta_attribute_value(self):
        value = ContentMetaAttributeValue("text/html; charset=euc-jp")
        self.assertEqual("text/html; charset=euc-jp", value)
        self.assertEqual("text/html; charset=euc-jp", value.original_value)
        self.assertEqual("text/html; charset=utf8", value.encode("utf8"))

########NEW FILE########
__FILENAME__ = test_tree
# -*- coding: utf-8 -*-
"""Tests for Beautiful Soup's tree traversal methods.

The tree traversal methods are the main advantage of using Beautiful
Soup over just using a parser.

Different parsers will build different Beautiful Soup trees given the
same markup, but all Beautiful Soup trees can be traversed with the
methods tested here.
"""

import copy
import pickle
import re
import warnings
from bs4 import BeautifulSoup
from bs4.builder import (
    builder_registry,
    HTMLParserTreeBuilder,
)
from bs4.element import (
    CData,
    Comment,
    Doctype,
    NavigableString,
    SoupStrainer,
    Tag,
)
from bs4.testing import (
    SoupTest,
    skipIf,
)

XML_BUILDER_PRESENT = (builder_registry.lookup("xml") is not None)
LXML_PRESENT = (builder_registry.lookup("lxml") is not None)

class TreeTest(SoupTest):

    def assertSelects(self, tags, should_match):
        """Make sure that the given tags have the correct text.

        This is used in tests that define a bunch of tags, each
        containing a single string, and then select certain strings by
        some mechanism.
        """
        self.assertEqual([tag.string for tag in tags], should_match)

    def assertSelectsIDs(self, tags, should_match):
        """Make sure that the given tags have the correct IDs.

        This is used in tests that define a bunch of tags, each
        containing a single string, and then select certain strings by
        some mechanism.
        """
        self.assertEqual([tag['id'] for tag in tags], should_match)


class TestFind(TreeTest):
    """Basic tests of the find() method.

    find() just calls find_all() with limit=1, so it's not tested all
    that thouroughly here.
    """

    def test_find_tag(self):
        soup = self.soup("<a>1</a><b>2</b><a>3</a><b>4</b>")
        self.assertEqual(soup.find("b").string, "2")

    def test_unicode_text_find(self):
        soup = self.soup(u'<h1>Räksmörgås</h1>')
        self.assertEqual(soup.find(text=u'Räksmörgås'), u'Räksmörgås')

class TestFindAll(TreeTest):
    """Basic tests of the find_all() method."""

    def test_find_all_text_nodes(self):
        """You can search the tree for text nodes."""
        soup = self.soup("<html>Foo<b>bar</b>\xbb</html>")
        # Exact match.
        self.assertEqual(soup.find_all(text="bar"), [u"bar"])
        # Match any of a number of strings.
        self.assertEqual(
            soup.find_all(text=["Foo", "bar"]), [u"Foo", u"bar"])
        # Match a regular expression.
        self.assertEqual(soup.find_all(text=re.compile('.*')),
                         [u"Foo", u"bar", u'\xbb'])
        # Match anything.
        self.assertEqual(soup.find_all(text=True),
                         [u"Foo", u"bar", u'\xbb'])

    def test_find_all_limit(self):
        """You can limit the number of items returned by find_all."""
        soup = self.soup("<a>1</a><a>2</a><a>3</a><a>4</a><a>5</a>")
        self.assertSelects(soup.find_all('a', limit=3), ["1", "2", "3"])
        self.assertSelects(soup.find_all('a', limit=1), ["1"])
        self.assertSelects(
            soup.find_all('a', limit=10), ["1", "2", "3", "4", "5"])

        # A limit of 0 means no limit.
        self.assertSelects(
            soup.find_all('a', limit=0), ["1", "2", "3", "4", "5"])

    def test_calling_a_tag_is_calling_findall(self):
        soup = self.soup("<a>1</a><b>2<a id='foo'>3</a></b>")
        self.assertSelects(soup('a', limit=1), ["1"])
        self.assertSelects(soup.b(id="foo"), ["3"])

    def test_find_all_with_self_referential_data_structure_does_not_cause_infinite_recursion(self):
        soup = self.soup("<a></a>")
        # Create a self-referential list.
        l = []
        l.append(l)

        # Without special code in _normalize_search_value, this would cause infinite
        # recursion.
        self.assertEqual([], soup.find_all(l))

class TestFindAllBasicNamespaces(TreeTest):

    def test_find_by_namespaced_name(self):
        soup = self.soup('<mathml:msqrt>4</mathml:msqrt><a svg:fill="red">')
        self.assertEqual("4", soup.find("mathml:msqrt").string)
        self.assertEqual("a", soup.find(attrs= { "svg:fill" : "red" }).name)


class TestFindAllByName(TreeTest):
    """Test ways of finding tags by tag name."""

    def setUp(self):
        super(TreeTest, self).setUp()
        self.tree =  self.soup("""<a>First tag.</a>
                                  <b>Second tag.</b>
                                  <c>Third <a>Nested tag.</a> tag.</c>""")

    def test_find_all_by_tag_name(self):
        # Find all the <a> tags.
        self.assertSelects(
            self.tree.find_all('a'), ['First tag.', 'Nested tag.'])

    def test_find_all_by_name_and_text(self):
        self.assertSelects(
            self.tree.find_all('a', text='First tag.'), ['First tag.'])

        self.assertSelects(
            self.tree.find_all('a', text=True), ['First tag.', 'Nested tag.'])

        self.assertSelects(
            self.tree.find_all('a', text=re.compile("tag")),
            ['First tag.', 'Nested tag.'])


    def test_find_all_on_non_root_element(self):
        # You can call find_all on any node, not just the root.
        self.assertSelects(self.tree.c.find_all('a'), ['Nested tag.'])

    def test_calling_element_invokes_find_all(self):
        self.assertSelects(self.tree('a'), ['First tag.', 'Nested tag.'])

    def test_find_all_by_tag_strainer(self):
        self.assertSelects(
            self.tree.find_all(SoupStrainer('a')),
            ['First tag.', 'Nested tag.'])

    def test_find_all_by_tag_names(self):
        self.assertSelects(
            self.tree.find_all(['a', 'b']),
            ['First tag.', 'Second tag.', 'Nested tag.'])

    def test_find_all_by_tag_dict(self):
        self.assertSelects(
            self.tree.find_all({'a' : True, 'b' : True}),
            ['First tag.', 'Second tag.', 'Nested tag.'])

    def test_find_all_by_tag_re(self):
        self.assertSelects(
            self.tree.find_all(re.compile('^[ab]$')),
            ['First tag.', 'Second tag.', 'Nested tag.'])

    def test_find_all_with_tags_matching_method(self):
        # You can define an oracle method that determines whether
        # a tag matches the search.
        def id_matches_name(tag):
            return tag.name == tag.get('id')

        tree = self.soup("""<a id="a">Match 1.</a>
                            <a id="1">Does not match.</a>
                            <b id="b">Match 2.</a>""")

        self.assertSelects(
            tree.find_all(id_matches_name), ["Match 1.", "Match 2."])


class TestFindAllByAttribute(TreeTest):

    def test_find_all_by_attribute_name(self):
        # You can pass in keyword arguments to find_all to search by
        # attribute.
        tree = self.soup("""
                         <a id="first">Matching a.</a>
                         <a id="second">
                          Non-matching <b id="first">Matching b.</b>a.
                         </a>""")
        self.assertSelects(tree.find_all(id='first'),
                           ["Matching a.", "Matching b."])

    def test_find_all_by_utf8_attribute_value(self):
        peace = u"םולש".encode("utf8")
        data = u'<a title="םולש"></a>'.encode("utf8")
        soup = self.soup(data)
        self.assertEqual([soup.a], soup.find_all(title=peace))
        self.assertEqual([soup.a], soup.find_all(title=peace.decode("utf8")))
        self.assertEqual([soup.a], soup.find_all(title=[peace, "something else"]))

    def test_find_all_by_attribute_dict(self):
        # You can pass in a dictionary as the argument 'attrs'. This
        # lets you search for attributes like 'name' (a fixed argument
        # to find_all) and 'class' (a reserved word in Python.)
        tree = self.soup("""
                         <a name="name1" class="class1">Name match.</a>
                         <a name="name2" class="class2">Class match.</a>
                         <a name="name3" class="class3">Non-match.</a>
                         <name1>A tag called 'name1'.</name1>
                         """)

        # This doesn't do what you want.
        self.assertSelects(tree.find_all(name='name1'),
                           ["A tag called 'name1'."])
        # This does what you want.
        self.assertSelects(tree.find_all(attrs={'name' : 'name1'}),
                           ["Name match."])

        self.assertSelects(tree.find_all(attrs={'class' : 'class2'}),
                           ["Class match."])

    def test_find_all_by_class(self):
        tree = self.soup("""
                         <a class="1">Class 1.</a>
                         <a class="2">Class 2.</a>
                         <b class="1">Class 1.</b>
                         <c class="3 4">Class 3 and 4.</c>
                         """)

        # Passing in the class_ keyword argument will search against
        # the 'class' attribute.
        self.assertSelects(tree.find_all('a', class_='1'), ['Class 1.'])
        self.assertSelects(tree.find_all('c', class_='3'), ['Class 3 and 4.'])
        self.assertSelects(tree.find_all('c', class_='4'), ['Class 3 and 4.'])

        # Passing in a string to 'attrs' will also search the CSS class.
        self.assertSelects(tree.find_all('a', '1'), ['Class 1.'])
        self.assertSelects(tree.find_all(attrs='1'), ['Class 1.', 'Class 1.'])
        self.assertSelects(tree.find_all('c', '3'), ['Class 3 and 4.'])
        self.assertSelects(tree.find_all('c', '4'), ['Class 3 and 4.'])

    def test_find_by_class_when_multiple_classes_present(self):
        tree = self.soup("<gar class='foo bar'>Found it</gar>")

        f = tree.find_all("gar", class_=re.compile("o"))
        self.assertSelects(f, ["Found it"])

        f = tree.find_all("gar", class_=re.compile("a"))
        self.assertSelects(f, ["Found it"])

        # Since the class is not the string "foo bar", but the two
        # strings "foo" and "bar", this will not find anything.
        f = tree.find_all("gar", class_=re.compile("o b"))
        self.assertSelects(f, [])

    def test_find_all_with_non_dictionary_for_attrs_finds_by_class(self):
        soup = self.soup("<a class='bar'>Found it</a>")

        self.assertSelects(soup.find_all("a", re.compile("ba")), ["Found it"])

        def big_attribute_value(value):
            return len(value) > 3

        self.assertSelects(soup.find_all("a", big_attribute_value), [])

        def small_attribute_value(value):
            return len(value) <= 3

        self.assertSelects(
            soup.find_all("a", small_attribute_value), ["Found it"])

    def test_find_all_with_string_for_attrs_finds_multiple_classes(self):
        soup = self.soup('<a class="foo bar"></a><a class="foo"></a>')
        a, a2 = soup.find_all("a")
        self.assertEqual([a, a2], soup.find_all("a", "foo"))
        self.assertEqual([a], soup.find_all("a", "bar"))

        # If you specify the class as a string that contains a
        # space, only that specific value will be found.
        self.assertEqual([a], soup.find_all("a", class_="foo bar"))
        self.assertEqual([a], soup.find_all("a", "foo bar"))
        self.assertEqual([], soup.find_all("a", "bar foo"))

    def test_find_all_by_attribute_soupstrainer(self):
        tree = self.soup("""
                         <a id="first">Match.</a>
                         <a id="second">Non-match.</a>""")

        strainer = SoupStrainer(attrs={'id' : 'first'})
        self.assertSelects(tree.find_all(strainer), ['Match.'])

    def test_find_all_with_missing_atribute(self):
        # You can pass in None as the value of an attribute to find_all.
        # This will match tags that do not have that attribute set.
        tree = self.soup("""<a id="1">ID present.</a>
                            <a>No ID present.</a>
                            <a id="">ID is empty.</a>""")
        self.assertSelects(tree.find_all('a', id=None), ["No ID present."])

    def test_find_all_with_defined_attribute(self):
        # You can pass in None as the value of an attribute to find_all.
        # This will match tags that have that attribute set to any value.
        tree = self.soup("""<a id="1">ID present.</a>
                            <a>No ID present.</a>
                            <a id="">ID is empty.</a>""")
        self.assertSelects(
            tree.find_all(id=True), ["ID present.", "ID is empty."])

    def test_find_all_with_numeric_attribute(self):
        # If you search for a number, it's treated as a string.
        tree = self.soup("""<a id=1>Unquoted attribute.</a>
                            <a id="1">Quoted attribute.</a>""")

        expected = ["Unquoted attribute.", "Quoted attribute."]
        self.assertSelects(tree.find_all(id=1), expected)
        self.assertSelects(tree.find_all(id="1"), expected)

    def test_find_all_with_list_attribute_values(self):
        # You can pass a list of attribute values instead of just one,
        # and you'll get tags that match any of the values.
        tree = self.soup("""<a id="1">1</a>
                            <a id="2">2</a>
                            <a id="3">3</a>
                            <a>No ID.</a>""")
        self.assertSelects(tree.find_all(id=["1", "3", "4"]),
                           ["1", "3"])

    def test_find_all_with_regular_expression_attribute_value(self):
        # You can pass a regular expression as an attribute value, and
        # you'll get tags whose values for that attribute match the
        # regular expression.
        tree = self.soup("""<a id="a">One a.</a>
                            <a id="aa">Two as.</a>
                            <a id="ab">Mixed as and bs.</a>
                            <a id="b">One b.</a>
                            <a>No ID.</a>""")

        self.assertSelects(tree.find_all(id=re.compile("^a+$")),
                           ["One a.", "Two as."])

    def test_find_by_name_and_containing_string(self):
        soup = self.soup("<b>foo</b><b>bar</b><a>foo</a>")
        a = soup.a

        self.assertEqual([a], soup.find_all("a", text="foo"))
        self.assertEqual([], soup.find_all("a", text="bar"))
        self.assertEqual([], soup.find_all("a", text="bar"))

    def test_find_by_name_and_containing_string_when_string_is_buried(self):
        soup = self.soup("<a>foo</a><a><b><c>foo</c></b></a>")
        self.assertEqual(soup.find_all("a"), soup.find_all("a", text="foo"))

    def test_find_by_attribute_and_containing_string(self):
        soup = self.soup('<b id="1">foo</b><a id="2">foo</a>')
        a = soup.a

        self.assertEqual([a], soup.find_all(id=2, text="foo"))
        self.assertEqual([], soup.find_all(id=1, text="bar"))




class TestIndex(TreeTest):
    """Test Tag.index"""
    def test_index(self):
        tree = self.soup("""<div>
                            <a>Identical</a>
                            <b>Not identical</b>
                            <a>Identical</a>

                            <c><d>Identical with child</d></c>
                            <b>Also not identical</b>
                            <c><d>Identical with child</d></c>
                            </div>""")
        div = tree.div
        for i, element in enumerate(div.contents):
            self.assertEqual(i, div.index(element))
        self.assertRaises(ValueError, tree.index, 1)


class TestParentOperations(TreeTest):
    """Test navigation and searching through an element's parents."""

    def setUp(self):
        super(TestParentOperations, self).setUp()
        self.tree = self.soup('''<ul id="empty"></ul>
                                 <ul id="top">
                                  <ul id="middle">
                                   <ul id="bottom">
                                    <b>Start here</b>
                                   </ul>
                                  </ul>''')
        self.start = self.tree.b


    def test_parent(self):
        self.assertEqual(self.start.parent['id'], 'bottom')
        self.assertEqual(self.start.parent.parent['id'], 'middle')
        self.assertEqual(self.start.parent.parent.parent['id'], 'top')

    def test_parent_of_top_tag_is_soup_object(self):
        top_tag = self.tree.contents[0]
        self.assertEqual(top_tag.parent, self.tree)

    def test_soup_object_has_no_parent(self):
        self.assertEqual(None, self.tree.parent)

    def test_find_parents(self):
        self.assertSelectsIDs(
            self.start.find_parents('ul'), ['bottom', 'middle', 'top'])
        self.assertSelectsIDs(
            self.start.find_parents('ul', id="middle"), ['middle'])

    def test_find_parent(self):
        self.assertEqual(self.start.find_parent('ul')['id'], 'bottom')
        self.assertEqual(self.start.find_parent('ul', id='top')['id'], 'top')

    def test_parent_of_text_element(self):
        text = self.tree.find(text="Start here")
        self.assertEqual(text.parent.name, 'b')

    def test_text_element_find_parent(self):
        text = self.tree.find(text="Start here")
        self.assertEqual(text.find_parent('ul')['id'], 'bottom')

    def test_parent_generator(self):
        parents = [parent['id'] for parent in self.start.parents
                   if parent is not None and 'id' in parent.attrs]
        self.assertEqual(parents, ['bottom', 'middle', 'top'])


class ProximityTest(TreeTest):

    def setUp(self):
        super(TreeTest, self).setUp()
        self.tree = self.soup(
            '<html id="start"><head></head><body><b id="1">One</b><b id="2">Two</b><b id="3">Three</b></body></html>')


class TestNextOperations(ProximityTest):

    def setUp(self):
        super(TestNextOperations, self).setUp()
        self.start = self.tree.b

    def test_next(self):
        self.assertEqual(self.start.next_element, "One")
        self.assertEqual(self.start.next_element.next_element['id'], "2")

    def test_next_of_last_item_is_none(self):
        last = self.tree.find(text="Three")
        self.assertEqual(last.next_element, None)

    def test_next_of_root_is_none(self):
        # The document root is outside the next/previous chain.
        self.assertEqual(self.tree.next_element, None)

    def test_find_all_next(self):
        self.assertSelects(self.start.find_all_next('b'), ["Two", "Three"])
        self.start.find_all_next(id=3)
        self.assertSelects(self.start.find_all_next(id=3), ["Three"])

    def test_find_next(self):
        self.assertEqual(self.start.find_next('b')['id'], '2')
        self.assertEqual(self.start.find_next(text="Three"), "Three")

    def test_find_next_for_text_element(self):
        text = self.tree.find(text="One")
        self.assertEqual(text.find_next("b").string, "Two")
        self.assertSelects(text.find_all_next("b"), ["Two", "Three"])

    def test_next_generator(self):
        start = self.tree.find(text="Two")
        successors = [node for node in start.next_elements]
        # There are two successors: the final <b> tag and its text contents.
        tag, contents = successors
        self.assertEqual(tag['id'], '3')
        self.assertEqual(contents, "Three")

class TestPreviousOperations(ProximityTest):

    def setUp(self):
        super(TestPreviousOperations, self).setUp()
        self.end = self.tree.find(text="Three")

    def test_previous(self):
        self.assertEqual(self.end.previous_element['id'], "3")
        self.assertEqual(self.end.previous_element.previous_element, "Two")

    def test_previous_of_first_item_is_none(self):
        first = self.tree.find('html')
        self.assertEqual(first.previous_element, None)

    def test_previous_of_root_is_none(self):
        # The document root is outside the next/previous chain.
        # XXX This is broken!
        #self.assertEqual(self.tree.previous_element, None)
        pass

    def test_find_all_previous(self):
        # The <b> tag containing the "Three" node is the predecessor
        # of the "Three" node itself, which is why "Three" shows up
        # here.
        self.assertSelects(
            self.end.find_all_previous('b'), ["Three", "Two", "One"])
        self.assertSelects(self.end.find_all_previous(id=1), ["One"])

    def test_find_previous(self):
        self.assertEqual(self.end.find_previous('b')['id'], '3')
        self.assertEqual(self.end.find_previous(text="One"), "One")

    def test_find_previous_for_text_element(self):
        text = self.tree.find(text="Three")
        self.assertEqual(text.find_previous("b").string, "Three")
        self.assertSelects(
            text.find_all_previous("b"), ["Three", "Two", "One"])

    def test_previous_generator(self):
        start = self.tree.find(text="One")
        predecessors = [node for node in start.previous_elements]

        # There are four predecessors: the <b> tag containing "One"
        # the <body> tag, the <head> tag, and the <html> tag.
        b, body, head, html = predecessors
        self.assertEqual(b['id'], '1')
        self.assertEqual(body.name, "body")
        self.assertEqual(head.name, "head")
        self.assertEqual(html.name, "html")


class SiblingTest(TreeTest):

    def setUp(self):
        super(SiblingTest, self).setUp()
        markup = '''<html>
                    <span id="1">
                     <span id="1.1"></span>
                    </span>
                    <span id="2">
                     <span id="2.1"></span>
                    </span>
                    <span id="3">
                     <span id="3.1"></span>
                    </span>
                    <span id="4"></span>
                    </html>'''
        # All that whitespace looks good but makes the tests more
        # difficult. Get rid of it.
        markup = re.compile("\n\s*").sub("", markup)
        self.tree = self.soup(markup)


class TestNextSibling(SiblingTest):

    def setUp(self):
        super(TestNextSibling, self).setUp()
        self.start = self.tree.find(id="1")

    def test_next_sibling_of_root_is_none(self):
        self.assertEqual(self.tree.next_sibling, None)

    def test_next_sibling(self):
        self.assertEqual(self.start.next_sibling['id'], '2')
        self.assertEqual(self.start.next_sibling.next_sibling['id'], '3')

        # Note the difference between next_sibling and next_element.
        self.assertEqual(self.start.next_element['id'], '1.1')

    def test_next_sibling_may_not_exist(self):
        self.assertEqual(self.tree.html.next_sibling, None)

        nested_span = self.tree.find(id="1.1")
        self.assertEqual(nested_span.next_sibling, None)

        last_span = self.tree.find(id="4")
        self.assertEqual(last_span.next_sibling, None)

    def test_find_next_sibling(self):
        self.assertEqual(self.start.find_next_sibling('span')['id'], '2')

    def test_next_siblings(self):
        self.assertSelectsIDs(self.start.find_next_siblings("span"),
                              ['2', '3', '4'])

        self.assertSelectsIDs(self.start.find_next_siblings(id='3'), ['3'])

    def test_next_sibling_for_text_element(self):
        soup = self.soup("Foo<b>bar</b>baz")
        start = soup.find(text="Foo")
        self.assertEqual(start.next_sibling.name, 'b')
        self.assertEqual(start.next_sibling.next_sibling, 'baz')

        self.assertSelects(start.find_next_siblings('b'), ['bar'])
        self.assertEqual(start.find_next_sibling(text="baz"), "baz")
        self.assertEqual(start.find_next_sibling(text="nonesuch"), None)


class TestPreviousSibling(SiblingTest):

    def setUp(self):
        super(TestPreviousSibling, self).setUp()
        self.end = self.tree.find(id="4")

    def test_previous_sibling_of_root_is_none(self):
        self.assertEqual(self.tree.previous_sibling, None)

    def test_previous_sibling(self):
        self.assertEqual(self.end.previous_sibling['id'], '3')
        self.assertEqual(self.end.previous_sibling.previous_sibling['id'], '2')

        # Note the difference between previous_sibling and previous_element.
        self.assertEqual(self.end.previous_element['id'], '3.1')

    def test_previous_sibling_may_not_exist(self):
        self.assertEqual(self.tree.html.previous_sibling, None)

        nested_span = self.tree.find(id="1.1")
        self.assertEqual(nested_span.previous_sibling, None)

        first_span = self.tree.find(id="1")
        self.assertEqual(first_span.previous_sibling, None)

    def test_find_previous_sibling(self):
        self.assertEqual(self.end.find_previous_sibling('span')['id'], '3')

    def test_previous_siblings(self):
        self.assertSelectsIDs(self.end.find_previous_siblings("span"),
                              ['3', '2', '1'])

        self.assertSelectsIDs(self.end.find_previous_siblings(id='1'), ['1'])

    def test_previous_sibling_for_text_element(self):
        soup = self.soup("Foo<b>bar</b>baz")
        start = soup.find(text="baz")
        self.assertEqual(start.previous_sibling.name, 'b')
        self.assertEqual(start.previous_sibling.previous_sibling, 'Foo')

        self.assertSelects(start.find_previous_siblings('b'), ['bar'])
        self.assertEqual(start.find_previous_sibling(text="Foo"), "Foo")
        self.assertEqual(start.find_previous_sibling(text="nonesuch"), None)


class TestTagCreation(SoupTest):
    """Test the ability to create new tags."""
    def test_new_tag(self):
        soup = self.soup("")
        new_tag = soup.new_tag("foo", bar="baz")
        self.assertTrue(isinstance(new_tag, Tag))
        self.assertEqual("foo", new_tag.name)
        self.assertEqual(dict(bar="baz"), new_tag.attrs)
        self.assertEqual(None, new_tag.parent)

    def test_tag_inherits_self_closing_rules_from_builder(self):
        if XML_BUILDER_PRESENT:
            xml_soup = BeautifulSoup("", "xml")
            xml_br = xml_soup.new_tag("br")
            xml_p = xml_soup.new_tag("p")

            # Both the <br> and <p> tag are empty-element, just because
            # they have no contents.
            self.assertEqual(b"<br/>", xml_br.encode())
            self.assertEqual(b"<p/>", xml_p.encode())

        html_soup = BeautifulSoup("", "html")
        html_br = html_soup.new_tag("br")
        html_p = html_soup.new_tag("p")

        # The HTML builder users HTML's rules about which tags are
        # empty-element tags, and the new tags reflect these rules.
        self.assertEqual(b"<br/>", html_br.encode())
        self.assertEqual(b"<p></p>", html_p.encode())

    def test_new_string_creates_navigablestring(self):
        soup = self.soup("")
        s = soup.new_string("foo")
        self.assertEqual("foo", s)
        self.assertTrue(isinstance(s, NavigableString))

    def test_new_string_can_create_navigablestring_subclass(self):
        soup = self.soup("")
        s = soup.new_string("foo", Comment)
        self.assertEqual("foo", s)
        self.assertTrue(isinstance(s, Comment))

class TestTreeModification(SoupTest):

    def test_attribute_modification(self):
        soup = self.soup('<a id="1"></a>')
        soup.a['id'] = 2
        self.assertEqual(soup.decode(), self.document_for('<a id="2"></a>'))
        del(soup.a['id'])
        self.assertEqual(soup.decode(), self.document_for('<a></a>'))
        soup.a['id2'] = 'foo'
        self.assertEqual(soup.decode(), self.document_for('<a id2="foo"></a>'))

    def test_new_tag_creation(self):
        builder = builder_registry.lookup('html')()
        soup = self.soup("<body></body>", builder=builder)
        a = Tag(soup, builder, 'a')
        ol = Tag(soup, builder, 'ol')
        a['href'] = 'http://foo.com/'
        soup.body.insert(0, a)
        soup.body.insert(1, ol)
        self.assertEqual(
            soup.body.encode(),
            b'<body><a href="http://foo.com/"></a><ol></ol></body>')

    def test_append_to_contents_moves_tag(self):
        doc = """<p id="1">Don't leave me <b>here</b>.</p>
                <p id="2">Don\'t leave!</p>"""
        soup = self.soup(doc)
        second_para = soup.find(id='2')
        bold = soup.b

        # Move the <b> tag to the end of the second paragraph.
        soup.find(id='2').append(soup.b)

        # The <b> tag is now a child of the second paragraph.
        self.assertEqual(bold.parent, second_para)

        self.assertEqual(
            soup.decode(), self.document_for(
                '<p id="1">Don\'t leave me .</p>\n'
                '<p id="2">Don\'t leave!<b>here</b></p>'))

    def test_replace_with_returns_thing_that_was_replaced(self):
        text = "<a></a><b><c></c></b>"
        soup = self.soup(text)
        a = soup.a
        new_a = a.replace_with(soup.c)
        self.assertEqual(a, new_a)

    def test_unwrap_returns_thing_that_was_replaced(self):
        text = "<a><b></b><c></c></a>"
        soup = self.soup(text)
        a = soup.a
        new_a = a.unwrap()
        self.assertEqual(a, new_a)

    def test_replace_tag_with_itself(self):
        text = "<a><b></b><c>Foo<d></d></c></a><a><e></e></a>"
        soup = self.soup(text)
        c = soup.c
        soup.c.replace_with(c)
        self.assertEqual(soup.decode(), self.document_for(text))

    def test_replace_tag_with_its_parent_raises_exception(self):
        text = "<a><b></b></a>"
        soup = self.soup(text)
        self.assertRaises(ValueError, soup.b.replace_with, soup.a)

    def test_insert_tag_into_itself_raises_exception(self):
        text = "<a><b></b></a>"
        soup = self.soup(text)
        self.assertRaises(ValueError, soup.a.insert, 0, soup.a)

    def test_replace_with_maintains_next_element_throughout(self):
        soup = self.soup('<p><a>one</a><b>three</b></p>')
        a = soup.a
        b = a.contents[0]
        # Make it so the <a> tag has two text children.
        a.insert(1, "two")

        # Now replace each one with the empty string.
        left, right = a.contents
        left.replaceWith('')
        right.replaceWith('')

        # The <b> tag is still connected to the tree.
        self.assertEqual("three", soup.b.string)

    def test_replace_final_node(self):
        soup = self.soup("<b>Argh!</b>")
        soup.find(text="Argh!").replace_with("Hooray!")
        new_text = soup.find(text="Hooray!")
        b = soup.b
        self.assertEqual(new_text.previous_element, b)
        self.assertEqual(new_text.parent, b)
        self.assertEqual(new_text.previous_element.next_element, new_text)
        self.assertEqual(new_text.next_element, None)

    def test_consecutive_text_nodes(self):
        # A builder should never create two consecutive text nodes,
        # but if you insert one next to another, Beautiful Soup will
        # handle it correctly.
        soup = self.soup("<a><b>Argh!</b><c></c></a>")
        soup.b.insert(1, "Hooray!")

        self.assertEqual(
            soup.decode(), self.document_for(
                "<a><b>Argh!Hooray!</b><c></c></a>"))

        new_text = soup.find(text="Hooray!")
        self.assertEqual(new_text.previous_element, "Argh!")
        self.assertEqual(new_text.previous_element.next_element, new_text)

        self.assertEqual(new_text.previous_sibling, "Argh!")
        self.assertEqual(new_text.previous_sibling.next_sibling, new_text)

        self.assertEqual(new_text.next_sibling, None)
        self.assertEqual(new_text.next_element, soup.c)

    def test_insert_string(self):
        soup = self.soup("<a></a>")
        soup.a.insert(0, "bar")
        soup.a.insert(0, "foo")
        # The string were added to the tag.
        self.assertEqual(["foo", "bar"], soup.a.contents)
        # And they were converted to NavigableStrings.
        self.assertEqual(soup.a.contents[0].next_element, "bar")

    def test_insert_tag(self):
        builder = self.default_builder
        soup = self.soup(
            "<a><b>Find</b><c>lady!</c><d></d></a>", builder=builder)
        magic_tag = Tag(soup, builder, 'magictag')
        magic_tag.insert(0, "the")
        soup.a.insert(1, magic_tag)

        self.assertEqual(
            soup.decode(), self.document_for(
                "<a><b>Find</b><magictag>the</magictag><c>lady!</c><d></d></a>"))

        # Make sure all the relationships are hooked up correctly.
        b_tag = soup.b
        self.assertEqual(b_tag.next_sibling, magic_tag)
        self.assertEqual(magic_tag.previous_sibling, b_tag)

        find = b_tag.find(text="Find")
        self.assertEqual(find.next_element, magic_tag)
        self.assertEqual(magic_tag.previous_element, find)

        c_tag = soup.c
        self.assertEqual(magic_tag.next_sibling, c_tag)
        self.assertEqual(c_tag.previous_sibling, magic_tag)

        the = magic_tag.find(text="the")
        self.assertEqual(the.parent, magic_tag)
        self.assertEqual(the.next_element, c_tag)
        self.assertEqual(c_tag.previous_element, the)

    def test_append_child_thats_already_at_the_end(self):
        data = "<a><b></b></a>"
        soup = self.soup(data)
        soup.a.append(soup.b)
        self.assertEqual(data, soup.decode())

    def test_move_tag_to_beginning_of_parent(self):
        data = "<a><b></b><c></c><d></d></a>"
        soup = self.soup(data)
        soup.a.insert(0, soup.d)
        self.assertEqual("<a><d></d><b></b><c></c></a>", soup.decode())

    def test_insert_works_on_empty_element_tag(self):
        # This is a little strange, since most HTML parsers don't allow
        # markup like this to come through. But in general, we don't
        # know what the parser would or wouldn't have allowed, so
        # I'm letting this succeed for now.
        soup = self.soup("<br/>")
        soup.br.insert(1, "Contents")
        self.assertEqual(str(soup.br), "<br>Contents</br>")

    def test_insert_before(self):
        soup = self.soup("<a>foo</a><b>bar</b>")
        soup.b.insert_before("BAZ")
        soup.a.insert_before("QUUX")
        self.assertEqual(
            soup.decode(), self.document_for("QUUX<a>foo</a>BAZ<b>bar</b>"))

        soup.a.insert_before(soup.b)
        self.assertEqual(
            soup.decode(), self.document_for("QUUX<b>bar</b><a>foo</a>BAZ"))

    def test_insert_after(self):
        soup = self.soup("<a>foo</a><b>bar</b>")
        soup.b.insert_after("BAZ")
        soup.a.insert_after("QUUX")
        self.assertEqual(
            soup.decode(), self.document_for("<a>foo</a>QUUX<b>bar</b>BAZ"))
        soup.b.insert_after(soup.a)
        self.assertEqual(
            soup.decode(), self.document_for("QUUX<b>bar</b><a>foo</a>BAZ"))

    def test_insert_after_raises_exception_if_after_has_no_meaning(self):
        soup = self.soup("")
        tag = soup.new_tag("a")
        string = soup.new_string("")
        self.assertRaises(ValueError, string.insert_after, tag)
        self.assertRaises(NotImplementedError, soup.insert_after, tag)
        self.assertRaises(ValueError, tag.insert_after, tag)

    def test_insert_before_raises_notimplementederror_if_before_has_no_meaning(self):
        soup = self.soup("")
        tag = soup.new_tag("a")
        string = soup.new_string("")
        self.assertRaises(ValueError, string.insert_before, tag)
        self.assertRaises(NotImplementedError, soup.insert_before, tag)
        self.assertRaises(ValueError, tag.insert_before, tag)

    def test_replace_with(self):
        soup = self.soup(
                "<p>There's <b>no</b> business like <b>show</b> business</p>")
        no, show = soup.find_all('b')
        show.replace_with(no)
        self.assertEqual(
            soup.decode(),
            self.document_for(
                "<p>There's  business like <b>no</b> business</p>"))

        self.assertEqual(show.parent, None)
        self.assertEqual(no.parent, soup.p)
        self.assertEqual(no.next_element, "no")
        self.assertEqual(no.next_sibling, " business")

    def test_replace_first_child(self):
        data = "<a><b></b><c></c></a>"
        soup = self.soup(data)
        soup.b.replace_with(soup.c)
        self.assertEqual("<a><c></c></a>", soup.decode())

    def test_replace_last_child(self):
        data = "<a><b></b><c></c></a>"
        soup = self.soup(data)
        soup.c.replace_with(soup.b)
        self.assertEqual("<a><b></b></a>", soup.decode())

    def test_nested_tag_replace_with(self):
        soup = self.soup(
            """<a>We<b>reserve<c>the</c><d>right</d></b></a><e>to<f>refuse</f><g>service</g></e>""")

        # Replace the entire <b> tag and its contents ("reserve the
        # right") with the <f> tag ("refuse").
        remove_tag = soup.b
        move_tag = soup.f
        remove_tag.replace_with(move_tag)

        self.assertEqual(
            soup.decode(), self.document_for(
                "<a>We<f>refuse</f></a><e>to<g>service</g></e>"))

        # The <b> tag is now an orphan.
        self.assertEqual(remove_tag.parent, None)
        self.assertEqual(remove_tag.find(text="right").next_element, None)
        self.assertEqual(remove_tag.previous_element, None)
        self.assertEqual(remove_tag.next_sibling, None)
        self.assertEqual(remove_tag.previous_sibling, None)

        # The <f> tag is now connected to the <a> tag.
        self.assertEqual(move_tag.parent, soup.a)
        self.assertEqual(move_tag.previous_element, "We")
        self.assertEqual(move_tag.next_element.next_element, soup.e)
        self.assertEqual(move_tag.next_sibling, None)

        # The gap where the <f> tag used to be has been mended, and
        # the word "to" is now connected to the <g> tag.
        to_text = soup.find(text="to")
        g_tag = soup.g
        self.assertEqual(to_text.next_element, g_tag)
        self.assertEqual(to_text.next_sibling, g_tag)
        self.assertEqual(g_tag.previous_element, to_text)
        self.assertEqual(g_tag.previous_sibling, to_text)

    def test_unwrap(self):
        tree = self.soup("""
            <p>Unneeded <em>formatting</em> is unneeded</p>
            """)
        tree.em.unwrap()
        self.assertEqual(tree.em, None)
        self.assertEqual(tree.p.text, "Unneeded formatting is unneeded")

    def test_wrap(self):
        soup = self.soup("I wish I was bold.")
        value = soup.string.wrap(soup.new_tag("b"))
        self.assertEqual(value.decode(), "<b>I wish I was bold.</b>")
        self.assertEqual(
            soup.decode(), self.document_for("<b>I wish I was bold.</b>"))

    def test_wrap_extracts_tag_from_elsewhere(self):
        soup = self.soup("<b></b>I wish I was bold.")
        soup.b.next_sibling.wrap(soup.b)
        self.assertEqual(
            soup.decode(), self.document_for("<b>I wish I was bold.</b>"))

    def test_wrap_puts_new_contents_at_the_end(self):
        soup = self.soup("<b>I like being bold.</b>I wish I was bold.")
        soup.b.next_sibling.wrap(soup.b)
        self.assertEqual(2, len(soup.b.contents))
        self.assertEqual(
            soup.decode(), self.document_for(
                "<b>I like being bold.I wish I was bold.</b>"))

    def test_extract(self):
        soup = self.soup(
            '<html><body>Some content. <div id="nav">Nav crap</div> More content.</body></html>')

        self.assertEqual(len(soup.body.contents), 3)
        extracted = soup.find(id="nav").extract()

        self.assertEqual(
            soup.decode(), "<html><body>Some content.  More content.</body></html>")
        self.assertEqual(extracted.decode(), '<div id="nav">Nav crap</div>')

        # The extracted tag is now an orphan.
        self.assertEqual(len(soup.body.contents), 2)
        self.assertEqual(extracted.parent, None)
        self.assertEqual(extracted.previous_element, None)
        self.assertEqual(extracted.next_element.next_element, None)

        # The gap where the extracted tag used to be has been mended.
        content_1 = soup.find(text="Some content. ")
        content_2 = soup.find(text=" More content.")
        self.assertEqual(content_1.next_element, content_2)
        self.assertEqual(content_1.next_sibling, content_2)
        self.assertEqual(content_2.previous_element, content_1)
        self.assertEqual(content_2.previous_sibling, content_1)

    def test_extract_distinguishes_between_identical_strings(self):
        soup = self.soup("<a>foo</a><b>bar</b>")
        foo_1 = soup.a.string
        bar_1 = soup.b.string
        foo_2 = soup.new_string("foo")
        bar_2 = soup.new_string("bar")
        soup.a.append(foo_2)
        soup.b.append(bar_2)

        # Now there are two identical strings in the <a> tag, and two
        # in the <b> tag. Let's remove the first "foo" and the second
        # "bar".
        foo_1.extract()
        bar_2.extract()
        self.assertEqual(foo_2, soup.a.string)
        self.assertEqual(bar_2, soup.b.string)

    def test_clear(self):
        """Tag.clear()"""
        soup = self.soup("<p><a>String <em>Italicized</em></a> and another</p>")
        # clear using extract()
        a = soup.a
        soup.p.clear()
        self.assertEqual(len(soup.p.contents), 0)
        self.assertTrue(hasattr(a, "contents"))

        # clear using decompose()
        em = a.em
        a.clear(decompose=True)
        self.assertEqual(0, len(em.contents))

    def test_string_set(self):
        """Tag.string = 'string'"""
        soup = self.soup("<a></a> <b><c></c></b>")
        soup.a.string = "foo"
        self.assertEqual(soup.a.contents, ["foo"])
        soup.b.string = "bar"
        self.assertEqual(soup.b.contents, ["bar"])

    def test_string_set_does_not_affect_original_string(self):
        soup = self.soup("<a><b>foo</b><c>bar</c>")
        soup.b.string = soup.c.string
        self.assertEqual(soup.a.encode(), b"<a><b>bar</b><c>bar</c></a>")

    def test_set_string_preserves_class_of_string(self):
        soup = self.soup("<a></a>")
        cdata = CData("foo")
        soup.a.string = cdata
        self.assertTrue(isinstance(soup.a.string, CData))

class TestElementObjects(SoupTest):
    """Test various features of element objects."""

    def test_len(self):
        """The length of an element is its number of children."""
        soup = self.soup("<top>1<b>2</b>3</top>")

        # The BeautifulSoup object itself contains one element: the
        # <top> tag.
        self.assertEqual(len(soup.contents), 1)
        self.assertEqual(len(soup), 1)

        # The <top> tag contains three elements: the text node "1", the
        # <b> tag, and the text node "3".
        self.assertEqual(len(soup.top), 3)
        self.assertEqual(len(soup.top.contents), 3)

    def test_member_access_invokes_find(self):
        """Accessing a Python member .foo invokes find('foo')"""
        soup = self.soup('<b><i></i></b>')
        self.assertEqual(soup.b, soup.find('b'))
        self.assertEqual(soup.b.i, soup.find('b').find('i'))
        self.assertEqual(soup.a, None)

    def test_deprecated_member_access(self):
        soup = self.soup('<b><i></i></b>')
        with warnings.catch_warnings(record=True) as w:
            tag = soup.bTag
        self.assertEqual(soup.b, tag)
        self.assertEqual(
            '.bTag is deprecated, use .find("b") instead.',
            str(w[0].message))

    def test_has_attr(self):
        """has_attr() checks for the presence of an attribute.

        Please note note: has_attr() is different from
        __in__. has_attr() checks the tag's attributes and __in__
        checks the tag's chidlren.
        """
        soup = self.soup("<foo attr='bar'>")
        self.assertTrue(soup.foo.has_attr('attr'))
        self.assertFalse(soup.foo.has_attr('attr2'))


    def test_attributes_come_out_in_alphabetical_order(self):
        markup = '<b a="1" z="5" m="3" f="2" y="4"></b>'
        self.assertSoupEquals(markup, '<b a="1" f="2" m="3" y="4" z="5"></b>')

    def test_string(self):
        # A tag that contains only a text node makes that node
        # available as .string.
        soup = self.soup("<b>foo</b>")
        self.assertEqual(soup.b.string, 'foo')

    def test_empty_tag_has_no_string(self):
        # A tag with no children has no .stirng.
        soup = self.soup("<b></b>")
        self.assertEqual(soup.b.string, None)

    def test_tag_with_multiple_children_has_no_string(self):
        # A tag with no children has no .string.
        soup = self.soup("<a>foo<b></b><b></b></b>")
        self.assertEqual(soup.b.string, None)

        soup = self.soup("<a>foo<b></b>bar</b>")
        self.assertEqual(soup.b.string, None)

        # Even if all the children are strings, due to trickery,
        # it won't work--but this would be a good optimization.
        soup = self.soup("<a>foo</b>")
        soup.a.insert(1, "bar")
        self.assertEqual(soup.a.string, None)

    def test_tag_with_recursive_string_has_string(self):
        # A tag with a single child which has a .string inherits that
        # .string.
        soup = self.soup("<a><b>foo</b></a>")
        self.assertEqual(soup.a.string, "foo")
        self.assertEqual(soup.string, "foo")

    def test_lack_of_string(self):
        """Only a tag containing a single text node has a .string."""
        soup = self.soup("<b>f<i>e</i>o</b>")
        self.assertFalse(soup.b.string)

        soup = self.soup("<b></b>")
        self.assertFalse(soup.b.string)

    def test_all_text(self):
        """Tag.text and Tag.get_text(sep=u"") -> all child text, concatenated"""
        soup = self.soup("<a>a<b>r</b>   <r> t </r></a>")
        self.assertEqual(soup.a.text, "ar  t ")
        self.assertEqual(soup.a.get_text(strip=True), "art")
        self.assertEqual(soup.a.get_text(","), "a,r, , t ")
        self.assertEqual(soup.a.get_text(",", strip=True), "a,r,t")

    def test_get_text_ignores_comments(self):
        soup = self.soup("foo<!--IGNORE-->bar")
        self.assertEqual(soup.get_text(), "foobar")

        self.assertEqual(
            soup.get_text(types=(NavigableString, Comment)), "fooIGNOREbar")
        self.assertEqual(
            soup.get_text(types=None), "fooIGNOREbar")

    def test_all_strings_ignores_comments(self):
        soup = self.soup("foo<!--IGNORE-->bar")
        self.assertEqual(['foo', 'bar'], list(soup.strings))

class TestCDAtaListAttributes(SoupTest):

    """Testing cdata-list attributes like 'class'.
    """
    def test_single_value_becomes_list(self):
        soup = self.soup("<a class='foo'>")
        self.assertEqual(["foo"],soup.a['class'])

    def test_multiple_values_becomes_list(self):
        soup = self.soup("<a class='foo bar'>")
        self.assertEqual(["foo", "bar"], soup.a['class'])

    def test_multiple_values_separated_by_weird_whitespace(self):
        soup = self.soup("<a class='foo\tbar\nbaz'>")
        self.assertEqual(["foo", "bar", "baz"],soup.a['class'])

    def test_attributes_joined_into_string_on_output(self):
        soup = self.soup("<a class='foo\tbar'>")
        self.assertEqual(b'<a class="foo bar"></a>', soup.a.encode())

    def test_accept_charset(self):
        soup = self.soup('<form accept-charset="ISO-8859-1 UTF-8">')
        self.assertEqual(['ISO-8859-1', 'UTF-8'], soup.form['accept-charset'])

    def test_cdata_attribute_applying_only_to_one_tag(self):
        data = '<a accept-charset="ISO-8859-1 UTF-8"></a>'
        soup = self.soup(data)
        # We saw in another test that accept-charset is a cdata-list
        # attribute for the <form> tag. But it's not a cdata-list
        # attribute for any other tag.
        self.assertEqual('ISO-8859-1 UTF-8', soup.a['accept-charset'])


class TestPersistence(SoupTest):
    "Testing features like pickle and deepcopy."

    def setUp(self):
        super(TestPersistence, self).setUp()
        self.page = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN"
"http://www.w3.org/TR/REC-html40/transitional.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<title>Beautiful Soup: We called him Tortoise because he taught us.</title>
<link rev="made" href="mailto:leonardr@segfault.org">
<meta name="Description" content="Beautiful Soup: an HTML parser optimized for screen-scraping.">
<meta name="generator" content="Markov Approximation 1.4 (module: leonardr)">
<meta name="author" content="Leonard Richardson">
</head>
<body>
<a href="foo">foo</a>
<a href="foo"><b>bar</b></a>
</body>
</html>"""
        self.tree = self.soup(self.page)

    def test_pickle_and_unpickle_identity(self):
        # Pickling a tree, then unpickling it, yields a tree identical
        # to the original.
        dumped = pickle.dumps(self.tree, 2)
        loaded = pickle.loads(dumped)
        self.assertEqual(loaded.__class__, BeautifulSoup)
        self.assertEqual(loaded.decode(), self.tree.decode())

    def test_deepcopy_identity(self):
        # Making a deepcopy of a tree yields an identical tree.
        copied = copy.deepcopy(self.tree)
        self.assertEqual(copied.decode(), self.tree.decode())

    def test_unicode_pickle(self):
        # A tree containing Unicode characters can be pickled.
        html = u"<b>\N{SNOWMAN}</b>"
        soup = self.soup(html)
        dumped = pickle.dumps(soup, pickle.HIGHEST_PROTOCOL)
        loaded = pickle.loads(dumped)
        self.assertEqual(loaded.decode(), soup.decode())


class TestSubstitutions(SoupTest):

    def test_default_formatter_is_minimal(self):
        markup = u"<b>&lt;&lt;Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</b>"
        soup = self.soup(markup)
        decoded = soup.decode(formatter="minimal")
        # The < is converted back into &lt; but the e-with-acute is left alone.
        self.assertEqual(
            decoded,
            self.document_for(
                u"<b>&lt;&lt;Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</b>"))

    def test_formatter_html(self):
        markup = u"<b>&lt;&lt;Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</b>"
        soup = self.soup(markup)
        decoded = soup.decode(formatter="html")
        self.assertEqual(
            decoded,
            self.document_for("<b>&lt;&lt;Sacr&eacute; bleu!&gt;&gt;</b>"))

    def test_formatter_minimal(self):
        markup = u"<b>&lt;&lt;Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</b>"
        soup = self.soup(markup)
        decoded = soup.decode(formatter="minimal")
        # The < is converted back into &lt; but the e-with-acute is left alone.
        self.assertEqual(
            decoded,
            self.document_for(
                u"<b>&lt;&lt;Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</b>"))

    def test_formatter_null(self):
        markup = u"<b>&lt;&lt;Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</b>"
        soup = self.soup(markup)
        decoded = soup.decode(formatter=None)
        # Neither the angle brackets nor the e-with-acute are converted.
        # This is not valid HTML, but it's what the user wanted.
        self.assertEqual(decoded,
                          self.document_for(u"<b><<Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!>></b>"))

    def test_formatter_custom(self):
        markup = u"<b>&lt;foo&gt;</b><b>bar</b>"
        soup = self.soup(markup)
        decoded = soup.decode(formatter = lambda x: x.upper())
        # Instead of normal entity conversion code, the custom
        # callable is called on every string.
        self.assertEqual(
            decoded,
            self.document_for(u"<b><FOO></b><b>BAR</b>"))

    def test_formatter_is_run_on_attribute_values(self):
        markup = u'<a href="http://a.com?a=b&c=é">e</a>'
        soup = self.soup(markup)
        a = soup.a

        expect_minimal = u'<a href="http://a.com?a=b&amp;c=é">e</a>'

        self.assertEqual(expect_minimal, a.decode())
        self.assertEqual(expect_minimal, a.decode(formatter="minimal"))

        expect_html = u'<a href="http://a.com?a=b&amp;c=&eacute;">e</a>'
        self.assertEqual(expect_html, a.decode(formatter="html"))

        self.assertEqual(markup, a.decode(formatter=None))
        expect_upper = u'<a href="HTTP://A.COM?A=B&C=É">E</a>'
        self.assertEqual(expect_upper, a.decode(formatter=lambda x: x.upper()))

    def test_formatter_skips_script_tag_for_html_documents(self):
        doc = """
  <script type="text/javascript">
   console.log("< < hey > > ");
  </script>
"""
        encoded = BeautifulSoup(doc).encode()
        self.assertTrue(b"< < hey > >" in encoded)

    def test_formatter_skips_style_tag_for_html_documents(self):
        doc = """
  <style type="text/css">
   console.log("< < hey > > ");
  </style>
"""
        encoded = BeautifulSoup(doc).encode()
        self.assertTrue(b"< < hey > >" in encoded)

    def test_prettify_leaves_preformatted_text_alone(self):
        soup = self.soup("<div>  foo  <pre>  \tbar\n  \n  </pre>  baz  ")
        # Everything outside the <pre> tag is reformatted, but everything
        # inside is left alone.
        self.assertEqual(
            u'<div>\n foo\n <pre>  \tbar\n  \n  </pre>\n baz\n</div>',
            soup.div.prettify())

    def test_prettify_accepts_formatter(self):
        soup = BeautifulSoup("<html><body>foo</body></html>")
        pretty = soup.prettify(formatter = lambda x: x.upper())
        self.assertTrue("FOO" in pretty)

    def test_prettify_outputs_unicode_by_default(self):
        soup = self.soup("<a></a>")
        self.assertEqual(unicode, type(soup.prettify()))

    def test_prettify_can_encode_data(self):
        soup = self.soup("<a></a>")
        self.assertEqual(bytes, type(soup.prettify("utf-8")))

    def test_html_entity_substitution_off_by_default(self):
        markup = u"<b>Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!</b>"
        soup = self.soup(markup)
        encoded = soup.b.encode("utf-8")
        self.assertEqual(encoded, markup.encode('utf-8'))

    def test_encoding_substitution(self):
        # Here's the <meta> tag saying that a document is
        # encoded in Shift-JIS.
        meta_tag = ('<meta content="text/html; charset=x-sjis" '
                    'http-equiv="Content-type"/>')
        soup = self.soup(meta_tag)

        # Parse the document, and the charset apprears unchanged.
        self.assertEqual(soup.meta['content'], 'text/html; charset=x-sjis')

        # Encode the document into some encoding, and the encoding is
        # substituted into the meta tag.
        utf_8 = soup.encode("utf-8")
        self.assertTrue(b"charset=utf-8" in utf_8)

        euc_jp = soup.encode("euc_jp")
        self.assertTrue(b"charset=euc_jp" in euc_jp)

        shift_jis = soup.encode("shift-jis")
        self.assertTrue(b"charset=shift-jis" in shift_jis)

        utf_16_u = soup.encode("utf-16").decode("utf-16")
        self.assertTrue("charset=utf-16" in utf_16_u)

    def test_encoding_substitution_doesnt_happen_if_tag_is_strained(self):
        markup = ('<head><meta content="text/html; charset=x-sjis" '
                    'http-equiv="Content-type"/></head><pre>foo</pre>')

        # Beautiful Soup used to try to rewrite the meta tag even if the
        # meta tag got filtered out by the strainer. This test makes
        # sure that doesn't happen.
        strainer = SoupStrainer('pre')
        soup = self.soup(markup, parse_only=strainer)
        self.assertEqual(soup.contents[0].name, 'pre')

class TestEncoding(SoupTest):
    """Test the ability to encode objects into strings."""

    def test_unicode_string_can_be_encoded(self):
        html = u"<b>\N{SNOWMAN}</b>"
        soup = self.soup(html)
        self.assertEqual(soup.b.string.encode("utf-8"),
                          u"\N{SNOWMAN}".encode("utf-8"))

    def test_tag_containing_unicode_string_can_be_encoded(self):
        html = u"<b>\N{SNOWMAN}</b>"
        soup = self.soup(html)
        self.assertEqual(
            soup.b.encode("utf-8"), html.encode("utf-8"))

    def test_encoding_substitutes_unrecognized_characters_by_default(self):
        html = u"<b>\N{SNOWMAN}</b>"
        soup = self.soup(html)
        self.assertEqual(soup.b.encode("ascii"), b"<b>&#9731;</b>")

    def test_encoding_can_be_made_strict(self):
        html = u"<b>\N{SNOWMAN}</b>"
        soup = self.soup(html)
        self.assertRaises(
            UnicodeEncodeError, soup.encode, "ascii", errors="strict")

    def test_decode_contents(self):
        html = u"<b>\N{SNOWMAN}</b>"
        soup = self.soup(html)
        self.assertEqual(u"\N{SNOWMAN}", soup.b.decode_contents())

    def test_encode_contents(self):
        html = u"<b>\N{SNOWMAN}</b>"
        soup = self.soup(html)
        self.assertEqual(
            u"\N{SNOWMAN}".encode("utf8"), soup.b.encode_contents(
                encoding="utf8"))

    def test_deprecated_renderContents(self):
        html = u"<b>\N{SNOWMAN}</b>"
        soup = self.soup(html)
        self.assertEqual(
            u"\N{SNOWMAN}".encode("utf8"), soup.b.renderContents())

class TestNavigableStringSubclasses(SoupTest):

    def test_cdata(self):
        # None of the current builders turn CDATA sections into CData
        # objects, but you can create them manually.
        soup = self.soup("")
        cdata = CData("foo")
        soup.insert(1, cdata)
        self.assertEqual(str(soup), "<![CDATA[foo]]>")
        self.assertEqual(soup.find(text="foo"), "foo")
        self.assertEqual(soup.contents[0], "foo")

    def test_cdata_is_never_formatted(self):
        """Text inside a CData object is passed into the formatter.

        But the return value is ignored.
        """

        self.count = 0
        def increment(*args):
            self.count += 1
            return "BITTER FAILURE"

        soup = self.soup("")
        cdata = CData("<><><>")
        soup.insert(1, cdata)
        self.assertEqual(
            b"<![CDATA[<><><>]]>", soup.encode(formatter=increment))
        self.assertEqual(1, self.count)

    def test_doctype_ends_in_newline(self):
        # Unlike other NavigableString subclasses, a DOCTYPE always ends
        # in a newline.
        doctype = Doctype("foo")
        soup = self.soup("")
        soup.insert(1, doctype)
        self.assertEqual(soup.encode(), b"<!DOCTYPE foo>\n")


class TestSoupSelector(TreeTest):

    HTML = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
"http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>The title</title>
<link rel="stylesheet" href="blah.css" type="text/css" id="l1">
</head>
<body>

<div id="main" class="fancy">
<div id="inner">
<h1 id="header1">An H1</h1>
<p>Some text</p>
<p class="onep" id="p1">Some more text</p>
<h2 id="header2">An H2</h2>
<p class="class1 class2 class3" id="pmulti">Another</p>
<a href="http://bob.example.org/" rel="friend met" id="bob">Bob</a>
<h2 id="header3">Another H2</h2>
<a id="me" href="http://simonwillison.net/" rel="me">me</a>
<span class="s1">
<a href="#" id="s1a1">span1a1</a>
<a href="#" id="s1a2">span1a2 <span id="s1a2s1">test</span></a>
<span class="span2">
<a href="#" id="s2a1">span2a1</a>
</span>
<span class="span3"></span>
</span>
</div>
<p lang="en" id="lang-en">English</p>
<p lang="en-gb" id="lang-en-gb">English UK</p>
<p lang="en-us" id="lang-en-us">English US</p>
<p lang="fr" id="lang-fr">French</p>
</div>

<div id="footer">
</div>
"""

    def setUp(self):
        self.soup = BeautifulSoup(self.HTML)

    def assertSelects(self, selector, expected_ids):
        el_ids = [el['id'] for el in self.soup.select(selector)]
        el_ids.sort()
        expected_ids.sort()
        self.assertEqual(expected_ids, el_ids,
            "Selector %s, expected [%s], got [%s]" % (
                selector, ', '.join(expected_ids), ', '.join(el_ids)
            )
        )

    assertSelect = assertSelects

    def assertSelectMultiple(self, *tests):
        for selector, expected_ids in tests:
            self.assertSelect(selector, expected_ids)

    def test_one_tag_one(self):
        els = self.soup.select('title')
        self.assertEqual(len(els), 1)
        self.assertEqual(els[0].name, 'title')
        self.assertEqual(els[0].contents, [u'The title'])

    def test_one_tag_many(self):
        els = self.soup.select('div')
        self.assertEqual(len(els), 3)
        for div in els:
            self.assertEqual(div.name, 'div')

    def test_tag_in_tag_one(self):
        els = self.soup.select('div div')
        self.assertSelects('div div', ['inner'])

    def test_tag_in_tag_many(self):
        for selector in ('html div', 'html body div', 'body div'):
            self.assertSelects(selector, ['main', 'inner', 'footer'])

    def test_tag_no_match(self):
        self.assertEqual(len(self.soup.select('del')), 0)

    def test_invalid_tag(self):
        self.assertRaises(ValueError, self.soup.select, 'tag%t')

    def test_header_tags(self):
        self.assertSelectMultiple(
            ('h1', ['header1']),
            ('h2', ['header2', 'header3']),
        )

    def test_class_one(self):
        for selector in ('.onep', 'p.onep', 'html p.onep'):
            els = self.soup.select(selector)
            self.assertEqual(len(els), 1)
            self.assertEqual(els[0].name, 'p')
            self.assertEqual(els[0]['class'], ['onep'])

    def test_class_mismatched_tag(self):
        els = self.soup.select('div.onep')
        self.assertEqual(len(els), 0)

    def test_one_id(self):
        for selector in ('div#inner', '#inner', 'div div#inner'):
            self.assertSelects(selector, ['inner'])

    def test_bad_id(self):
        els = self.soup.select('#doesnotexist')
        self.assertEqual(len(els), 0)

    def test_items_in_id(self):
        els = self.soup.select('div#inner p')
        self.assertEqual(len(els), 3)
        for el in els:
            self.assertEqual(el.name, 'p')
        self.assertEqual(els[1]['class'], ['onep'])
        self.assertFalse(els[0].has_attr('class'))

    def test_a_bunch_of_emptys(self):
        for selector in ('div#main del', 'div#main div.oops', 'div div#main'):
            self.assertEqual(len(self.soup.select(selector)), 0)

    def test_multi_class_support(self):
        for selector in ('.class1', 'p.class1', '.class2', 'p.class2',
            '.class3', 'p.class3', 'html p.class2', 'div#inner .class2'):
            self.assertSelects(selector, ['pmulti'])

    def test_multi_class_selection(self):
        for selector in ('.class1.class3', '.class3.class2',
                         '.class1.class2.class3'):
            self.assertSelects(selector, ['pmulti'])

    def test_child_selector(self):
        self.assertSelects('.s1 > a', ['s1a1', 's1a2'])
        self.assertSelects('.s1 > a span', ['s1a2s1'])

    def test_child_selector_id(self):
        self.assertSelects('.s1 > a#s1a2 span', ['s1a2s1'])

    def test_attribute_equals(self):
        self.assertSelectMultiple(
            ('p[class="onep"]', ['p1']),
            ('p[id="p1"]', ['p1']),
            ('[class="onep"]', ['p1']),
            ('[id="p1"]', ['p1']),
            ('link[rel="stylesheet"]', ['l1']),
            ('link[type="text/css"]', ['l1']),
            ('link[href="blah.css"]', ['l1']),
            ('link[href="no-blah.css"]', []),
            ('[rel="stylesheet"]', ['l1']),
            ('[type="text/css"]', ['l1']),
            ('[href="blah.css"]', ['l1']),
            ('[href="no-blah.css"]', []),
            ('p[href="no-blah.css"]', []),
            ('[href="no-blah.css"]', []),
        )

    def test_attribute_tilde(self):
        self.assertSelectMultiple(
            ('p[class~="class1"]', ['pmulti']),
            ('p[class~="class2"]', ['pmulti']),
            ('p[class~="class3"]', ['pmulti']),
            ('[class~="class1"]', ['pmulti']),
            ('[class~="class2"]', ['pmulti']),
            ('[class~="class3"]', ['pmulti']),
            ('a[rel~="friend"]', ['bob']),
            ('a[rel~="met"]', ['bob']),
            ('[rel~="friend"]', ['bob']),
            ('[rel~="met"]', ['bob']),
        )

    def test_attribute_startswith(self):
        self.assertSelectMultiple(
            ('[rel^="style"]', ['l1']),
            ('link[rel^="style"]', ['l1']),
            ('notlink[rel^="notstyle"]', []),
            ('[rel^="notstyle"]', []),
            ('link[rel^="notstyle"]', []),
            ('link[href^="bla"]', ['l1']),
            ('a[href^="http://"]', ['bob', 'me']),
            ('[href^="http://"]', ['bob', 'me']),
            ('[id^="p"]', ['pmulti', 'p1']),
            ('[id^="m"]', ['me', 'main']),
            ('div[id^="m"]', ['main']),
            ('a[id^="m"]', ['me']),
        )

    def test_attribute_endswith(self):
        self.assertSelectMultiple(
            ('[href$=".css"]', ['l1']),
            ('link[href$=".css"]', ['l1']),
            ('link[id$="1"]', ['l1']),
            ('[id$="1"]', ['l1', 'p1', 'header1', 's1a1', 's2a1', 's1a2s1']),
            ('div[id$="1"]', []),
            ('[id$="noending"]', []),
        )

    def test_attribute_contains(self):
        self.assertSelectMultiple(
            # From test_attribute_startswith
            ('[rel*="style"]', ['l1']),
            ('link[rel*="style"]', ['l1']),
            ('notlink[rel*="notstyle"]', []),
            ('[rel*="notstyle"]', []),
            ('link[rel*="notstyle"]', []),
            ('link[href*="bla"]', ['l1']),
            ('a[href*="http://"]', ['bob', 'me']),
            ('[href*="http://"]', ['bob', 'me']),
            ('[id*="p"]', ['pmulti', 'p1']),
            ('div[id*="m"]', ['main']),
            ('a[id*="m"]', ['me']),
            # From test_attribute_endswith
            ('[href*=".css"]', ['l1']),
            ('link[href*=".css"]', ['l1']),
            ('link[id*="1"]', ['l1']),
            ('[id*="1"]', ['l1', 'p1', 'header1', 's1a1', 's1a2', 's2a1', 's1a2s1']),
            ('div[id*="1"]', []),
            ('[id*="noending"]', []),
            # New for this test
            ('[href*="."]', ['bob', 'me', 'l1']),
            ('a[href*="."]', ['bob', 'me']),
            ('link[href*="."]', ['l1']),
            ('div[id*="n"]', ['main', 'inner']),
            ('div[id*="nn"]', ['inner']),
        )

    def test_attribute_exact_or_hypen(self):
        self.assertSelectMultiple(
            ('p[lang|="en"]', ['lang-en', 'lang-en-gb', 'lang-en-us']),
            ('[lang|="en"]', ['lang-en', 'lang-en-gb', 'lang-en-us']),
            ('p[lang|="fr"]', ['lang-fr']),
            ('p[lang|="gb"]', []),
        )

    def test_attribute_exists(self):
        self.assertSelectMultiple(
            ('[rel]', ['l1', 'bob', 'me']),
            ('link[rel]', ['l1']),
            ('a[rel]', ['bob', 'me']),
            ('[lang]', ['lang-en', 'lang-en-gb', 'lang-en-us', 'lang-fr']),
            ('p[class]', ['p1', 'pmulti']),
            ('[blah]', []),
            ('p[blah]', []),
        )

    def test_nth_of_type(self):
        # Try to select first paragraph
        els = self.soup.select('div#inner p:nth-of-type(1)')
        self.assertEqual(len(els), 1)
        self.assertEqual(els[0].string, u'Some text')

        # Try to select third paragraph
        els = self.soup.select('div#inner p:nth-of-type(3)')
        self.assertEqual(len(els), 1)
        self.assertEqual(els[0].string, u'Another')

        # Try to select (non-existent!) fourth paragraph
        els = self.soup.select('div#inner p:nth-of-type(4)')
        self.assertEqual(len(els), 0)

        # Pass in an invalid value.
        self.assertRaises(
            ValueError, self.soup.select, 'div p:nth-of-type(0)')

    def test_nth_of_type_direct_descendant(self):
        els = self.soup.select('div#inner > p:nth-of-type(1)')
        self.assertEqual(len(els), 1)
        self.assertEqual(els[0].string, u'Some text')

    def test_id_child_selector_nth_of_type(self):
        self.assertSelects('#inner > p:nth-of-type(2)', ['p1'])

    def test_select_on_element(self):
        # Other tests operate on the tree; this operates on an element
        # within the tree.
        inner = self.soup.find("div", id="main")
        selected = inner.select("div")
        # The <div id="inner"> tag was selected. The <div id="footer">
        # tag was not.
        self.assertSelectsIDs(selected, ['inner'])

    def test_overspecified_child_id(self):
        self.assertSelects(".fancy #inner", ['inner'])
        self.assertSelects(".normal #inner", [])

    def test_adjacent_sibling_selector(self):
        self.assertSelects('#p1 + h2', ['header2'])
        self.assertSelects('#p1 + h2 + p', ['pmulti'])
        self.assertSelects('#p1 + #header2 + .class1', ['pmulti'])
        self.assertEqual([], self.soup.select('#p1 + p'))

    def test_general_sibling_selector(self):
        self.assertSelects('#p1 ~ h2', ['header2', 'header3'])
        self.assertSelects('#p1 ~ #header2', ['header2'])
        self.assertSelects('#p1 ~ h2 + a', ['me'])
        self.assertSelects('#p1 ~ h2 + [rel="me"]', ['me'])
        self.assertEqual([], self.soup.select('#inner ~ h2'))

    def test_dangling_combinator(self):
        self.assertRaises(ValueError, self.soup.select, 'h1 >')

    def test_sibling_combinator_wont_select_same_tag_twice(self):
        self.assertSelects('p[lang] ~ p', ['lang-en-gb', 'lang-en-us', 'lang-fr'])

########NEW FILE########
__FILENAME__ = iri2uri
"""
iri2uri

Converts an IRI to a URI.

"""
__author__ = "Joe Gregorio (joe@bitworking.org)"
__copyright__ = "Copyright 2006, Joe Gregorio"
__contributors__ = []
__version__ = "1.0.0"
__license__ = "MIT"
__history__ = """
"""

import urlparse


# Convert an IRI to a URI following the rules in RFC 3987
# 
# The characters we need to enocde and escape are defined in the spec:
#
# iprivate =  %xE000-F8FF / %xF0000-FFFFD / %x100000-10FFFD
# ucschar = %xA0-D7FF / %xF900-FDCF / %xFDF0-FFEF
#         / %x10000-1FFFD / %x20000-2FFFD / %x30000-3FFFD
#         / %x40000-4FFFD / %x50000-5FFFD / %x60000-6FFFD
#         / %x70000-7FFFD / %x80000-8FFFD / %x90000-9FFFD
#         / %xA0000-AFFFD / %xB0000-BFFFD / %xC0000-CFFFD
#         / %xD0000-DFFFD / %xE1000-EFFFD

escape_range = [
   (0xA0, 0xD7FF ),
   (0xE000, 0xF8FF ),
   (0xF900, 0xFDCF ),
   (0xFDF0, 0xFFEF),
   (0x10000, 0x1FFFD ),
   (0x20000, 0x2FFFD ),
   (0x30000, 0x3FFFD),
   (0x40000, 0x4FFFD ),
   (0x50000, 0x5FFFD ),
   (0x60000, 0x6FFFD),
   (0x70000, 0x7FFFD ),
   (0x80000, 0x8FFFD ),
   (0x90000, 0x9FFFD),
   (0xA0000, 0xAFFFD ),
   (0xB0000, 0xBFFFD ),
   (0xC0000, 0xCFFFD),
   (0xD0000, 0xDFFFD ),
   (0xE1000, 0xEFFFD),
   (0xF0000, 0xFFFFD ),
   (0x100000, 0x10FFFD)
]
 
def encode(c):
    retval = c
    i = ord(c)
    for low, high in escape_range:
        if i < low:
            break
        if i >= low and i <= high:
            retval = "".join(["%%%2X" % ord(o) for o in c.encode('utf-8')])
            break
    return retval


def iri2uri(uri):
    """Convert an IRI to a URI. Note that IRIs must be 
    passed in a unicode strings. That is, do not utf-8 encode
    the IRI before passing it into the function.""" 
    if isinstance(uri ,unicode):
        (scheme, authority, path, query, fragment) = urlparse.urlsplit(uri)
        authority = authority.encode('idna')
        # For each character in 'ucschar' or 'iprivate'
        #  1. encode as utf-8
        #  2. then %-encode each octet of that utf-8 
        uri = urlparse.urlunsplit((scheme, authority, path, query, fragment))
        uri = "".join([encode(c) for c in uri])
    return uri
        
if __name__ == "__main__":
    import unittest

    class Test(unittest.TestCase):

        def test_uris(self):
            """Test that URIs are invariant under the transformation."""
            invariant = [ 
                u"ftp://ftp.is.co.za/rfc/rfc1808.txt",
                u"http://www.ietf.org/rfc/rfc2396.txt",
                u"ldap://[2001:db8::7]/c=GB?objectClass?one",
                u"mailto:John.Doe@example.com",
                u"news:comp.infosystems.www.servers.unix",
                u"tel:+1-816-555-1212",
                u"telnet://192.0.2.16:80/",
                u"urn:oasis:names:specification:docbook:dtd:xml:4.1.2" ]
            for uri in invariant:
                self.assertEqual(uri, iri2uri(uri))
            
        def test_iri(self):
            """ Test that the right type of escaping is done for each part of the URI."""
            self.assertEqual("http://xn--o3h.com/%E2%98%84", iri2uri(u"http://\N{COMET}.com/\N{COMET}"))
            self.assertEqual("http://bitworking.org/?fred=%E2%98%84", iri2uri(u"http://bitworking.org/?fred=\N{COMET}"))
            self.assertEqual("http://bitworking.org/#%E2%98%84", iri2uri(u"http://bitworking.org/#\N{COMET}"))
            self.assertEqual("#%E2%98%84", iri2uri(u"#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}")))
            self.assertNotEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}".encode('utf-8')))

    unittest.main()

    

########NEW FILE########
__FILENAME__ = socks
"""SocksiPy - Python SOCKS module.
Version 1.00

Copyright 2006 Dan-Haim. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of Dan Haim nor the names of his contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.

THIS SOFTWARE IS PROVIDED BY DAN HAIM "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL DAN HAIM OR HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMANGE.


This module provides a standard socket-like interface for Python
for tunneling connections through SOCKS proxies.

"""

"""

Minor modifications made by Christopher Gilbert (http://motomastyle.com/)
for use in PyLoris (http://pyloris.sourceforge.net/)

Minor modifications made by Mario Vilas (http://breakingcode.wordpress.com/)
mainly to merge bug fixes found in Sourceforge

"""

import base64
import socket
import struct
import sys

if getattr(socket, 'socket', None) is None:
    raise ImportError('socket.socket missing, proxy support unusable')

PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2
PROXY_TYPE_HTTP = 3
PROXY_TYPE_HTTP_NO_TUNNEL = 4

_defaultproxy = None
_orgsocket = socket.socket

class ProxyError(Exception): pass
class GeneralProxyError(ProxyError): pass
class Socks5AuthError(ProxyError): pass
class Socks5Error(ProxyError): pass
class Socks4Error(ProxyError): pass
class HTTPError(ProxyError): pass

_generalerrors = ("success",
    "invalid data",
    "not connected",
    "not available",
    "bad proxy type",
    "bad input")

_socks5errors = ("succeeded",
    "general SOCKS server failure",
    "connection not allowed by ruleset",
    "Network unreachable",
    "Host unreachable",
    "Connection refused",
    "TTL expired",
    "Command not supported",
    "Address type not supported",
    "Unknown error")

_socks5autherrors = ("succeeded",
    "authentication is required",
    "all offered authentication methods were rejected",
    "unknown username or invalid password",
    "unknown error")

_socks4errors = ("request granted",
    "request rejected or failed",
    "request rejected because SOCKS server cannot connect to identd on the client",
    "request rejected because the client program and identd report different user-ids",
    "unknown error")

def setdefaultproxy(proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
    """setdefaultproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
    Sets a default proxy which all further socksocket objects will use,
    unless explicitly changed.
    """
    global _defaultproxy
    _defaultproxy = (proxytype, addr, port, rdns, username, password)

def wrapmodule(module):
    """wrapmodule(module)
    Attempts to replace a module's socket library with a SOCKS socket. Must set
    a default proxy using setdefaultproxy(...) first.
    This will only work on modules that import socket directly into the namespace;
    most of the Python Standard Library falls into this category.
    """
    if _defaultproxy != None:
        module.socket.socket = socksocket
    else:
        raise GeneralProxyError((4, "no proxy specified"))

class socksocket(socket.socket):
    """socksocket([family[, type[, proto]]]) -> socket object
    Open a SOCKS enabled socket. The parameters are the same as
    those of the standard socket init. In order for SOCKS to work,
    you must specify family=AF_INET, type=SOCK_STREAM and proto=0.
    """

    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, _sock=None):
        _orgsocket.__init__(self, family, type, proto, _sock)
        if _defaultproxy != None:
            self.__proxy = _defaultproxy
        else:
            self.__proxy = (None, None, None, None, None, None)
        self.__proxysockname = None
        self.__proxypeername = None
        self.__httptunnel = True

    def __recvall(self, count):
        """__recvall(count) -> data
        Receive EXACTLY the number of bytes requested from the socket.
        Blocks until the required number of bytes have been received.
        """
        data = self.recv(count)
        while len(data) < count:
            d = self.recv(count-len(data))
            if not d: raise GeneralProxyError((0, "connection closed unexpectedly"))
            data = data + d
        return data

    def sendall(self, content, *args):
        """ override socket.socket.sendall method to rewrite the header
        for non-tunneling proxies if needed
        """
        if not self.__httptunnel:
            content = self.__rewriteproxy(content)
        return super(socksocket, self).sendall(content, *args)

    def __rewriteproxy(self, header):
        """ rewrite HTTP request headers to support non-tunneling proxies
        (i.e. those which do not support the CONNECT method).
        This only works for HTTP (not HTTPS) since HTTPS requires tunneling.
        """
        host, endpt = None, None
        hdrs = header.split("\r\n")
        for hdr in hdrs:
            if hdr.lower().startswith("host:"):
                host = hdr
            elif hdr.lower().startswith("get") or hdr.lower().startswith("post"):
                endpt = hdr
        if host and endpt:
            hdrs.remove(host)
            hdrs.remove(endpt)
            host = host.split(" ")[1]
            endpt = endpt.split(" ")
            if (self.__proxy[4] != None and self.__proxy[5] != None):
                hdrs.insert(0, self.__getauthheader())
            hdrs.insert(0, "Host: %s" % host)
            hdrs.insert(0, "%s http://%s%s %s" % (endpt[0], host, endpt[1], endpt[2]))
        return "\r\n".join(hdrs)

    def __getauthheader(self):
        auth = self.__proxy[4] + ":" + self.__proxy[5]
        return "Proxy-Authorization: Basic " + base64.b64encode(auth)

    def setproxy(self, proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
        """setproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
        Sets the proxy to be used.
        proxytype -    The type of the proxy to be used. Three types
                are supported: PROXY_TYPE_SOCKS4 (including socks4a),
                PROXY_TYPE_SOCKS5 and PROXY_TYPE_HTTP
        addr -        The address of the server (IP or DNS).
        port -        The port of the server. Defaults to 1080 for SOCKS
                servers and 8080 for HTTP proxy servers.
        rdns -        Should DNS queries be preformed on the remote side
                (rather than the local side). The default is True.
                Note: This has no effect with SOCKS4 servers.
        username -    Username to authenticate with to the server.
                The default is no authentication.
        password -    Password to authenticate with to the server.
                Only relevant when username is also provided.
        """
        self.__proxy = (proxytype, addr, port, rdns, username, password)

    def __negotiatesocks5(self, destaddr, destport):
        """__negotiatesocks5(self,destaddr,destport)
        Negotiates a connection through a SOCKS5 server.
        """
        # First we'll send the authentication packages we support.
        if (self.__proxy[4]!=None) and (self.__proxy[5]!=None):
            # The username/password details were supplied to the
            # setproxy method so we support the USERNAME/PASSWORD
            # authentication (in addition to the standard none).
            self.sendall(struct.pack('BBBB', 0x05, 0x02, 0x00, 0x02))
        else:
            # No username/password were entered, therefore we
            # only support connections with no authentication.
            self.sendall(struct.pack('BBB', 0x05, 0x01, 0x00))
        # We'll receive the server's response to determine which
        # method was selected
        chosenauth = self.__recvall(2)
        if chosenauth[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        # Check the chosen authentication method
        if chosenauth[1:2] == chr(0x00).encode():
            # No authentication is required
            pass
        elif chosenauth[1:2] == chr(0x02).encode():
            # Okay, we need to perform a basic username/password
            # authentication.
            self.sendall(chr(0x01).encode() + chr(len(self.__proxy[4])) + self.__proxy[4] + chr(len(self.__proxy[5])) + self.__proxy[5])
            authstat = self.__recvall(2)
            if authstat[0:1] != chr(0x01).encode():
                # Bad response
                self.close()
                raise GeneralProxyError((1, _generalerrors[1]))
            if authstat[1:2] != chr(0x00).encode():
                # Authentication failed
                self.close()
                raise Socks5AuthError((3, _socks5autherrors[3]))
            # Authentication succeeded
        else:
            # Reaching here is always bad
            self.close()
            if chosenauth[1] == chr(0xFF).encode():
                raise Socks5AuthError((2, _socks5autherrors[2]))
            else:
                raise GeneralProxyError((1, _generalerrors[1]))
        # Now we can request the actual connection
        req = struct.pack('BBB', 0x05, 0x01, 0x00)
        # If the given destination address is an IP address, we'll
        # use the IPv4 address request even if remote resolving was specified.
        try:
            ipaddr = socket.inet_aton(destaddr)
            req = req + chr(0x01).encode() + ipaddr
        except socket.error:
            # Well it's not an IP number,  so it's probably a DNS name.
            if self.__proxy[3]:
                # Resolve remotely
                ipaddr = None
                req = req + chr(0x03).encode() + chr(len(destaddr)).encode() + destaddr
            else:
                # Resolve locally
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
                req = req + chr(0x01).encode() + ipaddr
        req = req + struct.pack(">H", destport)
        self.sendall(req)
        # Get the response
        resp = self.__recvall(4)
        if resp[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        elif resp[1:2] != chr(0x00).encode():
            # Connection failed
            self.close()
            if ord(resp[1:2])<=8:
                raise Socks5Error((ord(resp[1:2]), _socks5errors[ord(resp[1:2])]))
            else:
                raise Socks5Error((9, _socks5errors[9]))
        # Get the bound address/port
        elif resp[3:4] == chr(0x01).encode():
            boundaddr = self.__recvall(4)
        elif resp[3:4] == chr(0x03).encode():
            resp = resp + self.recv(1)
            boundaddr = self.__recvall(ord(resp[4:5]))
        else:
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        boundport = struct.unpack(">H", self.__recvall(2))[0]
        self.__proxysockname = (boundaddr, boundport)
        if ipaddr != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def getproxysockname(self):
        """getsockname() -> address info
        Returns the bound IP address and port number at the proxy.
        """
        return self.__proxysockname

    def getproxypeername(self):
        """getproxypeername() -> address info
        Returns the IP and port number of the proxy.
        """
        return _orgsocket.getpeername(self)

    def getpeername(self):
        """getpeername() -> address info
        Returns the IP address and port number of the destination
        machine (note: getproxypeername returns the proxy)
        """
        return self.__proxypeername

    def __negotiatesocks4(self,destaddr,destport):
        """__negotiatesocks4(self,destaddr,destport)
        Negotiates a connection through a SOCKS4 server.
        """
        # Check if the destination address provided is an IP address
        rmtrslv = False
        try:
            ipaddr = socket.inet_aton(destaddr)
        except socket.error:
            # It's a DNS name. Check where it should be resolved.
            if self.__proxy[3]:
                ipaddr = struct.pack("BBBB", 0x00, 0x00, 0x00, 0x01)
                rmtrslv = True
            else:
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
        # Construct the request packet
        req = struct.pack(">BBH", 0x04, 0x01, destport) + ipaddr
        # The username parameter is considered userid for SOCKS4
        if self.__proxy[4] != None:
            req = req + self.__proxy[4]
        req = req + chr(0x00).encode()
        # DNS name if remote resolving is required
        # NOTE: This is actually an extension to the SOCKS4 protocol
        # called SOCKS4A and may not be supported in all cases.
        if rmtrslv:
            req = req + destaddr + chr(0x00).encode()
        self.sendall(req)
        # Get the response from the server
        resp = self.__recvall(8)
        if resp[0:1] != chr(0x00).encode():
            # Bad data
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        if resp[1:2] != chr(0x5A).encode():
            # Server returned an error
            self.close()
            if ord(resp[1:2]) in (91, 92, 93):
                self.close()
                raise Socks4Error((ord(resp[1:2]), _socks4errors[ord(resp[1:2]) - 90]))
            else:
                raise Socks4Error((94, _socks4errors[4]))
        # Get the bound address/port
        self.__proxysockname = (socket.inet_ntoa(resp[4:]), struct.unpack(">H", resp[2:4])[0])
        if rmtrslv != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def __negotiatehttp(self, destaddr, destport):
        """__negotiatehttp(self,destaddr,destport)
        Negotiates a connection through an HTTP server.
        """
        # If we need to resolve locally, we do this now
        if not self.__proxy[3]:
            addr = socket.gethostbyname(destaddr)
        else:
            addr = destaddr
        headers =  ["CONNECT ", addr, ":", str(destport), " HTTP/1.1\r\n"]
        headers += ["Host: ", destaddr, "\r\n"]
        if (self.__proxy[4] != None and self.__proxy[5] != None):
                headers += [self.__getauthheader(), "\r\n"]
        headers.append("\r\n")
        self.sendall("".join(headers).encode())
        # We read the response until we get the string "\r\n\r\n"
        resp = self.recv(1)
        while resp.find("\r\n\r\n".encode()) == -1:
            resp = resp + self.recv(1)
        # We just need the first line to check if the connection
        # was successful
        statusline = resp.splitlines()[0].split(" ".encode(), 2)
        if statusline[0] not in ("HTTP/1.0".encode(), "HTTP/1.1".encode()):
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        try:
            statuscode = int(statusline[1])
        except ValueError:
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        if statuscode != 200:
            self.close()
            raise HTTPError((statuscode, statusline[2]))
        self.__proxysockname = ("0.0.0.0", 0)
        self.__proxypeername = (addr, destport)

    def connect(self, destpair):
        """connect(self, despair)
        Connects to the specified destination through a proxy.
        destpar - A tuple of the IP/DNS address and the port number.
        (identical to socket's connect).
        To select the proxy server use setproxy().
        """
        # Do a minimal input check first
        if (not type(destpair) in (list,tuple)) or (len(destpair) < 2) or (not isinstance(destpair[0], basestring)) or (type(destpair[1]) != int):
            raise GeneralProxyError((5, _generalerrors[5]))
        if self.__proxy[0] == PROXY_TYPE_SOCKS5:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self, (self.__proxy[1], portnum))
            self.__negotiatesocks5(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_SOCKS4:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatesocks4(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatehttp(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP_NO_TUNNEL:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1],portnum))
            if destpair[1] == 443:
                self.__negotiatehttp(destpair[0],destpair[1])
            else:
                self.__httptunnel = False
        elif self.__proxy[0] == None:
            _orgsocket.connect(self, (destpair[0], destpair[1]))
        else:
            raise GeneralProxyError((4, _generalerrors[4]))

########NEW FILE########
__FILENAME__ = imap
"""
The MIT License

Copyright (c) 2007-2010 Leah Culver, Joe Stump, Mark Paschal, Vic Fryzel

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import oauth2
import imaplib


class IMAP4_SSL(imaplib.IMAP4_SSL):
    """IMAP wrapper for imaplib.IMAP4_SSL that implements XOAUTH."""

    def authenticate(self, url, consumer, token):
        if consumer is not None and not isinstance(consumer, oauth2.Consumer):
            raise ValueError("Invalid consumer.")

        if token is not None and not isinstance(token, oauth2.Token):
            raise ValueError("Invalid token.")

        imaplib.IMAP4_SSL.authenticate(self, 'XOAUTH',
            lambda x: oauth2.build_xoauth_string(url, consumer, token))

########NEW FILE########
__FILENAME__ = smtp
"""
The MIT License

Copyright (c) 2007-2010 Leah Culver, Joe Stump, Mark Paschal, Vic Fryzel

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import oauth2
import smtplib
import base64


class SMTP(smtplib.SMTP):
    """SMTP wrapper for smtplib.SMTP that implements XOAUTH."""

    def authenticate(self, url, consumer, token):
        if consumer is not None and not isinstance(consumer, oauth2.Consumer):
            raise ValueError("Invalid consumer.")

        if token is not None and not isinstance(token, oauth2.Token):
            raise ValueError("Invalid token.")

        self.docmd('AUTH', 'XOAUTH %s' % \
            base64.b64encode(oauth2.build_xoauth_string(url, consumer, token)))

########NEW FILE########
__FILENAME__ = _version
# This is the version of this source code.

manual_verstr = "1.5"



auto_build_num = "211"



verstr = manual_verstr + "." + auto_build_num
try:
    from pyutil.version_class import Version as pyutil_Version
    __version__ = pyutil_Version(verstr)
except (ImportError, ValueError):
    # Maybe there is no pyutil installed.
    from distutils.version import LooseVersion as distutils_Version
    __version__ = distutils_Version(verstr)

########NEW FILE########
__FILENAME__ = const
# -*- coding: utf-8 -*-
"""
Constants needed for the binary parser. Part of the pygeoip package.

@author: Jennifer Ennis <zaylea@gmail.com>

@license: Copyright(C) 2004 MaxMind LLC

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/lgpl.txt>.
"""

from platform import python_version_tuple

PY2 = python_version_tuple()[0] == '2'
PY3 = python_version_tuple()[0] == '3'

GEOIP_STANDARD = 0
GEOIP_MEMORY_CACHE = 1

DMA_MAP = {
    500: 'Portland-Auburn, ME',
    501: 'New York, NY',
    502: 'Binghamton, NY',
    503: 'Macon, GA',
    504: 'Philadelphia, PA',
    505: 'Detroit, MI',
    506: 'Boston, MA',
    507: 'Savannah, GA',
    508: 'Pittsburgh, PA',
    509: 'Ft Wayne, IN',
    510: 'Cleveland, OH',
    511: 'Washington, DC',
    512: 'Baltimore, MD',
    513: 'Flint, MI',
    514: 'Buffalo, NY',
    515: 'Cincinnati, OH',
    516: 'Erie, PA',
    517: 'Charlotte, NC',
    518: 'Greensboro, NC',
    519: 'Charleston, SC',
    520: 'Augusta, GA',
    521: 'Providence, RI',
    522: 'Columbus, GA',
    523: 'Burlington, VT',
    524: 'Atlanta, GA',
    525: 'Albany, GA',
    526: 'Utica-Rome, NY',
    527: 'Indianapolis, IN',
    528: 'Miami, FL',
    529: 'Louisville, KY',
    530: 'Tallahassee, FL',
    531: 'Tri-Cities, TN',
    532: 'Albany-Schenectady-Troy, NY',
    533: 'Hartford, CT',
    534: 'Orlando, FL',
    535: 'Columbus, OH',
    536: 'Youngstown-Warren, OH',
    537: 'Bangor, ME',
    538: 'Rochester, NY',
    539: 'Tampa, FL',
    540: 'Traverse City-Cadillac, MI',
    541: 'Lexington, KY',
    542: 'Dayton, OH',
    543: 'Springfield-Holyoke, MA',
    544: 'Norfolk-Portsmouth, VA',
    545: 'Greenville-New Bern-Washington, NC',
    546: 'Columbia, SC',
    547: 'Toledo, OH',
    548: 'West Palm Beach, FL',
    549: 'Watertown, NY',
    550: 'Wilmington, NC',
    551: 'Lansing, MI',
    552: 'Presque Isle, ME',
    553: 'Marquette, MI',
    554: 'Wheeling, WV',
    555: 'Syracuse, NY',
    556: 'Richmond-Petersburg, VA',
    557: 'Knoxville, TN',
    558: 'Lima, OH',
    559: 'Bluefield-Beckley-Oak Hill, WV',
    560: 'Raleigh-Durham, NC',
    561: 'Jacksonville, FL',
    563: 'Grand Rapids, MI',
    564: 'Charleston-Huntington, WV',
    565: 'Elmira, NY',
    566: 'Harrisburg-Lancaster-Lebanon-York, PA',
    567: 'Greenville-Spartenburg, SC',
    569: 'Harrisonburg, VA',
    570: 'Florence-Myrtle Beach, SC',
    571: 'Ft Myers, FL',
    573: 'Roanoke-Lynchburg, VA',
    574: 'Johnstown-Altoona, PA',
    575: 'Chattanooga, TN',
    576: 'Salisbury, MD',
    577: 'Wilkes Barre-Scranton, PA',
    581: 'Terre Haute, IN',
    582: 'Lafayette, IN',
    583: 'Alpena, MI',
    584: 'Charlottesville, VA',
    588: 'South Bend, IN',
    592: 'Gainesville, FL',
    596: 'Zanesville, OH',
    597: 'Parkersburg, WV',
    598: 'Clarksburg-Weston, WV',
    600: 'Corpus Christi, TX',
    602: 'Chicago, IL',
    603: 'Joplin-Pittsburg, MO',
    604: 'Columbia-Jefferson City, MO',
    605: 'Topeka, KS',
    606: 'Dothan, AL',
    609: 'St Louis, MO',
    610: 'Rockford, IL',
    611: 'Rochester-Mason City-Austin, MN',
    612: 'Shreveport, LA',
    613: 'Minneapolis-St Paul, MN',
    616: 'Kansas City, MO',
    617: 'Milwaukee, WI',
    618: 'Houston, TX',
    619: 'Springfield, MO',
    620: 'Tuscaloosa, AL',
    622: 'New Orleans, LA',
    623: 'Dallas-Fort Worth, TX',
    624: 'Sioux City, IA',
    625: 'Waco-Temple-Bryan, TX',
    626: 'Victoria, TX',
    627: 'Wichita Falls, TX',
    628: 'Monroe, LA',
    630: 'Birmingham, AL',
    631: 'Ottumwa-Kirksville, IA',
    632: 'Paducah, KY',
    633: 'Odessa-Midland, TX',
    634: 'Amarillo, TX',
    635: 'Austin, TX',
    636: 'Harlingen, TX',
    637: 'Cedar Rapids-Waterloo, IA',
    638: 'St Joseph, MO',
    639: 'Jackson, TN',
    640: 'Memphis, TN',
    641: 'San Antonio, TX',
    642: 'Lafayette, LA',
    643: 'Lake Charles, LA',
    644: 'Alexandria, LA',
    646: 'Anniston, AL',
    647: 'Greenwood-Greenville, MS',
    648: 'Champaign-Springfield-Decatur, IL',
    649: 'Evansville, IN',
    650: 'Oklahoma City, OK',
    651: 'Lubbock, TX',
    652: 'Omaha, NE',
    656: 'Panama City, FL',
    657: 'Sherman, TX',
    658: 'Green Bay-Appleton, WI',
    659: 'Nashville, TN',
    661: 'San Angelo, TX',
    662: 'Abilene-Sweetwater, TX',
    669: 'Madison, WI',
    670: 'Ft Smith-Fay-Springfield, AR',
    671: 'Tulsa, OK',
    673: 'Columbus-Tupelo-West Point, MS',
    675: 'Peoria-Bloomington, IL',
    676: 'Duluth, MN',
    678: 'Wichita, KS',
    679: 'Des Moines, IA',
    682: 'Davenport-Rock Island-Moline, IL',
    686: 'Mobile, AL',
    687: 'Minot-Bismarck-Dickinson, ND',
    691: 'Huntsville, AL',
    692: 'Beaumont-Port Author, TX',
    693: 'Little Rock-Pine Bluff, AR',
    698: 'Montgomery, AL',
    702: 'La Crosse-Eau Claire, WI',
    705: 'Wausau-Rhinelander, WI',
    709: 'Tyler-Longview, TX',
    710: 'Hattiesburg-Laurel, MS',
    711: 'Meridian, MS',
    716: 'Baton Rouge, LA',
    717: 'Quincy, IL',
    718: 'Jackson, MS',
    722: 'Lincoln-Hastings, NE',
    724: 'Fargo-Valley City, ND',
    725: 'Sioux Falls, SD',
    734: 'Jonesboro, AR',
    736: 'Bowling Green, KY',
    737: 'Mankato, MN',
    740: 'North Platte, NE',
    743: 'Anchorage, AK',
    744: 'Honolulu, HI',
    745: 'Fairbanks, AK',
    746: 'Biloxi-Gulfport, MS',
    747: 'Juneau, AK',
    749: 'Laredo, TX',
    751: 'Denver, CO',
    752: 'Colorado Springs, CO',
    753: 'Phoenix, AZ',
    754: 'Butte-Bozeman, MT',
    755: 'Great Falls, MT',
    756: 'Billings, MT',
    757: 'Boise, ID',
    758: 'Idaho Falls-Pocatello, ID',
    759: 'Cheyenne, WY',
    760: 'Twin Falls, ID',
    762: 'Missoula, MT',
    764: 'Rapid City, SD',
    765: 'El Paso, TX',
    766: 'Helena, MT',
    767: 'Casper-Riverton, WY',
    770: 'Salt Lake City, UT',
    771: 'Yuma, AZ',
    773: 'Grand Junction, CO',
    789: 'Tucson, AZ',
    790: 'Albuquerque, NM',
    798: 'Glendive, MT',
    800: 'Bakersfield, CA',
    801: 'Eugene, OR',
    802: 'Eureka, CA',
    803: 'Los Angeles, CA',
    804: 'Palm Springs, CA',
    807: 'San Francisco, CA',
    810: 'Yakima-Pasco, WA',
    811: 'Reno, NV',
    813: 'Medford-Klamath Falls, OR',
    819: 'Seattle-Tacoma, WA',
    820: 'Portland, OR',
    821: 'Bend, OR',
    825: 'San Diego, CA',
    828: 'Monterey-Salinas, CA',
    839: 'Las Vegas, NV',
    855: 'Santa Barbara, CA',
    862: 'Sacramento, CA',
    866: 'Fresno, CA',
    868: 'Chico-Redding, CA',
    881: 'Spokane, WA'
}

COUNTRY_CODES = (
    '',
    'AP', 'EU', 'AD', 'AE', 'AF', 'AG', 'AI', 'AL', 'AM', 'AN', 'AO', 'AQ',
    'AR', 'AS', 'AT', 'AU', 'AW', 'AZ', 'BA', 'BB', 'BD', 'BE', 'BF', 'BG',
    'BH', 'BI', 'BJ', 'BM', 'BN', 'BO', 'BR', 'BS', 'BT', 'BV', 'BW', 'BY',
    'BZ', 'CA', 'CC', 'CD', 'CF', 'CG', 'CH', 'CI', 'CK', 'CL', 'CM', 'CN',
    'CO', 'CR', 'CU', 'CV', 'CX', 'CY', 'CZ', 'DE', 'DJ', 'DK', 'DM', 'DO',
    'DZ', 'EC', 'EE', 'EG', 'EH', 'ER', 'ES', 'ET', 'FI', 'FJ', 'FK', 'FM',
    'FO', 'FR', 'FX', 'GA', 'GB', 'GD', 'GE', 'GF', 'GH', 'GI', 'GL', 'GM',
    'GN', 'GP', 'GQ', 'GR', 'GS', 'GT', 'GU', 'GW', 'GY', 'HK', 'HM', 'HN',
    'HR', 'HT', 'HU', 'ID', 'IE', 'IL', 'IN', 'IO', 'IQ', 'IR', 'IS', 'IT',
    'JM', 'JO', 'JP', 'KE', 'KG', 'KH', 'KI', 'KM', 'KN', 'KP', 'KR', 'KW',
    'KY', 'KZ', 'LA', 'LB', 'LC', 'LI', 'LK', 'LR', 'LS', 'LT', 'LU', 'LV',
    'LY', 'MA', 'MC', 'MD', 'MG', 'MH', 'MK', 'ML', 'MM', 'MN', 'MO', 'MP',
    'MQ', 'MR', 'MS', 'MT', 'MU', 'MV', 'MW', 'MX', 'MY', 'MZ', 'NA', 'NC',
    'NE', 'NF', 'NG', 'NI', 'NL', 'NO', 'NP', 'NR', 'NU', 'NZ', 'OM', 'PA',
    'PE', 'PF', 'PG', 'PH', 'PK', 'PL', 'PM', 'PN', 'PR', 'PS', 'PT', 'PW',
    'PY', 'QA', 'RE', 'RO', 'RU', 'RW', 'SA', 'SB', 'SC', 'SD', 'SE', 'SG',
    'SH', 'SI', 'SJ', 'SK', 'SL', 'SM', 'SN', 'SO', 'SR', 'ST', 'SV', 'SY',
    'SZ', 'TC', 'TD', 'TF', 'TG', 'TH', 'TJ', 'TK', 'TM', 'TN', 'TO', 'TL',
    'TR', 'TT', 'TV', 'TW', 'TZ', 'UA', 'UG', 'UM', 'US', 'UY', 'UZ', 'VA',
    'VC', 'VE', 'VG', 'VI', 'VN', 'VU', 'WF', 'WS', 'YE', 'YT', 'RS', 'ZA',
    'ZM', 'ME', 'ZW', 'A1', 'A2', 'O1', 'AX', 'GG', 'IM', 'JE', 'BL', 'MF',
    'BQ', 'SS'
)

COUNTRY_CODES3 = (
    '', 'AP', 'EU', 'AND', 'ARE', 'AFG', 'ATG', 'AIA', 'ALB', 'ARM', 'ANT',
    'AGO', 'AQ', 'ARG', 'ASM', 'AUT', 'AUS', 'ABW', 'AZE', 'BIH', 'BRB', 'BGD',
    'BEL', 'BFA', 'BGR', 'BHR', 'BDI', 'BEN', 'BMU', 'BRN', 'BOL', 'BRA',
    'BHS', 'BTN', 'BV', 'BWA', 'BLR', 'BLZ', 'CAN', 'CC', 'COD', 'CAF', 'COG',
    'CHE', 'CIV', 'COK', 'CHL', 'CMR', 'CHN', 'COL', 'CRI', 'CUB', 'CPV', 'CX',
    'CYP', 'CZE', 'DEU', 'DJI', 'DNK', 'DMA', 'DOM', 'DZA', 'ECU', 'EST',
    'EGY', 'ESH', 'ERI', 'ESP', 'ETH', 'FIN', 'FJI', 'FLK', 'FSM', 'FRO',
    'FRA', 'FX', 'GAB', 'GBR', 'GRD', 'GEO', 'GUF', 'GHA', 'GIB', 'GRL', 'GMB',
    'GIN', 'GLP', 'GNQ', 'GRC', 'GS', 'GTM', 'GUM', 'GNB', 'GUY', 'HKG', 'HM',
    'HND', 'HRV', 'HTI', 'HUN', 'IDN', 'IRL', 'ISR', 'IND', 'IO', 'IRQ', 'IRN',
    'ISL', 'ITA', 'JAM', 'JOR', 'JPN', 'KEN', 'KGZ', 'KHM', 'KIR', 'COM',
    'KNA', 'PRK', 'KOR', 'KWT', 'CYM', 'KAZ', 'LAO', 'LBN', 'LCA', 'LIE',
    'LKA', 'LBR', 'LSO', 'LTU', 'LUX', 'LVA', 'LBY', 'MAR', 'MCO', 'MDA',
    'MDG', 'MHL', 'MKD', 'MLI', 'MMR', 'MNG', 'MAC', 'MNP', 'MTQ', 'MRT',
    'MSR', 'MLT', 'MUS', 'MDV', 'MWI', 'MEX', 'MYS', 'MOZ', 'NAM', 'NCL',
    'NER', 'NFK', 'NGA', 'NIC', 'NLD', 'NOR', 'NPL', 'NRU', 'NIU', 'NZL',
    'OMN', 'PAN', 'PER', 'PYF', 'PNG', 'PHL', 'PAK', 'POL', 'SPM', 'PCN',
    'PRI', 'PSE', 'PRT', 'PLW', 'PRY', 'QAT', 'REU', 'ROU', 'RUS', 'RWA',
    'SAU', 'SLB', 'SYC', 'SDN', 'SWE', 'SGP', 'SHN', 'SVN', 'SJM', 'SVK',
    'SLE', 'SMR', 'SEN', 'SOM', 'SUR', 'STP', 'SLV', 'SYR', 'SWZ', 'TCA',
    'TCD', 'TF', 'TGO', 'THA', 'TJK', 'TKL', 'TLS', 'TKM', 'TUN', 'TON', 'TUR',
    'TTO', 'TUV', 'TWN', 'TZA', 'UKR', 'UGA', 'UM', 'USA', 'URY', 'UZB', 'VAT',
    'VCT', 'VEN', 'VGB', 'VIR', 'VNM', 'VUT', 'WLF', 'WSM', 'YEM', 'YT', 'SRB',
    'ZAF', 'ZMB', 'MNE', 'ZWE', 'A1', 'A2', 'O1', 'ALA', 'GGY', 'IMN', 'JEY',
    'BLM', 'MAF', 'BES', 'SSD'
)

COUNTRY_NAMES = (
    '', 'Asia/Pacific Region', 'Europe', 'Andorra', 'United Arab Emirates',
    'Afghanistan', 'Antigua and Barbuda', 'Anguilla', 'Albania', 'Armenia',
    'Netherlands Antilles', 'Angola', 'Antarctica', 'Argentina',
    'American Samoa', 'Austria', 'Australia', 'Aruba', 'Azerbaijan',
    'Bosnia and Herzegovina', 'Barbados', 'Bangladesh', 'Belgium',
    'Burkina Faso', 'Bulgaria', 'Bahrain', 'Burundi', 'Benin', 'Bermuda',
    'Brunei Darussalam', 'Bolivia', 'Brazil', 'Bahamas', 'Bhutan',
    'Bouvet Island', 'Botswana', 'Belarus', 'Belize', 'Canada',
    'Cocos (Keeling) Islands', 'Congo, The Democratic Republic of the',
    'Central African Republic', 'Congo', 'Switzerland', 'Cote D\'Ivoire',
    'Cook Islands', 'Chile', 'Cameroon', 'China', 'Colombia', 'Costa Rica',
    'Cuba', 'Cape Verde', 'Christmas Island', 'Cyprus', 'Czech Republic',
    'Germany', 'Djibouti', 'Denmark', 'Dominica', 'Dominican Republic',
    'Algeria', 'Ecuador', 'Estonia', 'Egypt', 'Western Sahara', 'Eritrea',
    'Spain', 'Ethiopia', 'Finland', 'Fiji', 'Falkland Islands (Malvinas)',
    'Micronesia, Federated States of', 'Faroe Islands', 'France',
    'France, Metropolitan', 'Gabon', 'United Kingdom', 'Grenada', 'Georgia',
    'French Guiana', 'Ghana', 'Gibraltar', 'Greenland', 'Gambia', 'Guinea',
    'Guadeloupe', 'Equatorial Guinea', 'Greece',
    'South Georgia and the South Sandwich Islands', 'Guatemala', 'Guam',
    'Guinea-Bissau', 'Guyana', 'Hong Kong',
    'Heard Island and McDonald Islands', 'Honduras', 'Croatia', 'Haiti',
    'Hungary', 'Indonesia', 'Ireland', 'Israel', 'India',
    'British Indian Ocean Territory', 'Iraq', 'Iran, Islamic Republic of',
    'Iceland', 'Italy', 'Jamaica', 'Jordan', 'Japan', 'Kenya', 'Kyrgyzstan',
    'Cambodia', 'Kiribati', 'Comoros', 'Saint Kitts and Nevis',
    'Korea, Democratic People\'s Republic of', 'Korea, Republic of', 'Kuwait',
    'Cayman Islands', 'Kazakhstan', 'Lao People\'s Democratic Republic',
    'Lebanon', 'Saint Lucia', 'Liechtenstein', 'Sri Lanka', 'Liberia',
    'Lesotho', 'Lithuania', 'Luxembourg', 'Latvia', 'Libya', 'Morocco',
    'Monaco', 'Moldova, Republic of', 'Madagascar', 'Marshall Islands',
    'Macedonia', 'Mali', 'Myanmar', 'Mongolia', 'Macau',
    'Northern Mariana Islands', 'Martinique', 'Mauritania', 'Montserrat',
    'Malta', 'Mauritius', 'Maldives', 'Malawi', 'Mexico', 'Malaysia',
    'Mozambique', 'Namibia', 'New Caledonia', 'Niger', 'Norfolk Island',
    'Nigeria', 'Nicaragua', 'Netherlands', 'Norway', 'Nepal', 'Nauru', 'Niue',
    'New Zealand', 'Oman', 'Panama', 'Peru', 'French Polynesia',
    'Papua New Guinea', 'Philippines', 'Pakistan', 'Poland',
    'Saint Pierre and Miquelon', 'Pitcairn Islands', 'Puerto Rico',
    'Palestinian Territory', 'Portugal', 'Palau', 'Paraguay', 'Qatar',
    'Reunion', 'Romania', 'Russian Federation', 'Rwanda', 'Saudi Arabia',
    'Solomon Islands', 'Seychelles', 'Sudan', 'Sweden', 'Singapore',
    'Saint Helena', 'Slovenia', 'Svalbard and Jan Mayen', 'Slovakia',
    'Sierra Leone', 'San Marino', 'Senegal', 'Somalia', 'Suriname',
    'Sao Tome and Principe', 'El Salvador', 'Syrian Arab Republic',
    'Swaziland', 'Turks and Caicos Islands', 'Chad',
    'French Southern Territories', 'Togo', 'Thailand', 'Tajikistan', 'Tokelau',
    'Turkmenistan', 'Tunisia', 'Tonga', 'Timor-Leste', 'Turkey',
    'Trinidad and Tobago', 'Tuvalu', 'Taiwan', 'Tanzania, United Republic of',
    'Ukraine', 'Uganda', 'United States Minor Outlying Islands',
    'United States', 'Uruguay', 'Uzbekistan', 'Holy See (Vatican City State)',
    'Saint Vincent and the Grenadines', 'Venezuela', 'Virgin Islands, British',
    'Virgin Islands, U.S.', 'Vietnam', 'Vanuatu', 'Wallis and Futuna', 'Samoa',
    'Yemen', 'Mayotte', 'Serbia', 'South Africa', 'Zambia', 'Montenegro',
    'Zimbabwe', 'Anonymous Proxy', 'Satellite Provider', 'Other',
    'Aland Islands', 'Guernsey', 'Isle of Man', 'Jersey', 'Saint Barthelemy',
    'Saint Martin', 'Bonaire, Sint Eustatius and Saba', 'South Sudan'
)

CONTINENT_NAMES = (
    '--', 'AS', 'EU', 'EU', 'AS', 'AS', 'NA', 'NA', 'EU', 'AS', 'NA', 'AF',
    'AN', 'SA', 'OC', 'EU', 'OC', 'NA', 'AS', 'EU', 'NA', 'AS', 'EU', 'AF',
    'EU', 'AS', 'AF', 'AF', 'NA', 'AS', 'SA', 'SA', 'NA', 'AS', 'AN', 'AF',
    'EU', 'NA', 'NA', 'AS', 'AF', 'AF', 'AF', 'EU', 'AF', 'OC', 'SA', 'AF',
    'AS', 'SA', 'NA', 'NA', 'AF', 'AS', 'AS', 'EU', 'EU', 'AF', 'EU', 'NA',
    'NA', 'AF', 'SA', 'EU', 'AF', 'AF', 'AF', 'EU', 'AF', 'EU', 'OC', 'SA',
    'OC', 'EU', 'EU', 'NA', 'AF', 'EU', 'NA', 'AS', 'SA', 'AF', 'EU', 'NA',
    'AF', 'AF', 'NA', 'AF', 'EU', 'AN', 'NA', 'OC', 'AF', 'SA', 'AS', 'AN',
    'NA', 'EU', 'NA', 'EU', 'AS', 'EU', 'AS', 'AS', 'AS', 'AS', 'AS', 'EU',
    'EU', 'NA', 'AS', 'AS', 'AF', 'AS', 'AS', 'OC', 'AF', 'NA', 'AS', 'AS',
    'AS', 'NA', 'AS', 'AS', 'AS', 'NA', 'EU', 'AS', 'AF', 'AF', 'EU', 'EU',
    'EU', 'AF', 'AF', 'EU', 'EU', 'AF', 'OC', 'EU', 'AF', 'AS', 'AS', 'AS',
    'OC', 'NA', 'AF', 'NA', 'EU', 'AF', 'AS', 'AF', 'NA', 'AS', 'AF', 'AF',
    'OC', 'AF', 'OC', 'AF', 'NA', 'EU', 'EU', 'AS', 'OC', 'OC', 'OC', 'AS',
    'NA', 'SA', 'OC', 'OC', 'AS', 'AS', 'EU', 'NA', 'OC', 'NA', 'AS', 'EU',
    'OC', 'SA', 'AS', 'AF', 'EU', 'EU', 'AF', 'AS', 'OC', 'AF', 'AF', 'EU',
    'AS', 'AF', 'EU', 'EU', 'EU', 'AF', 'EU', 'AF', 'AF', 'SA', 'AF', 'NA',
    'AS', 'AF', 'NA', 'AF', 'AN', 'AF', 'AS', 'AS', 'OC', 'AS', 'AF', 'OC',
    'AS', 'EU', 'NA', 'OC', 'AS', 'AF', 'EU', 'AF', 'OC', 'NA', 'SA', 'AS',
    'EU', 'NA', 'SA', 'NA', 'NA', 'AS', 'OC', 'OC', 'OC', 'AS', 'AF', 'EU',
    'AF', 'AF', 'EU', 'AF', '--', '--', '--', 'EU', 'EU', 'EU', 'EU', 'NA',
    'NA', 'NA', 'AF'
)

# storage / caching flags
STANDARD = 0
MEMORY_CACHE = 1
MMAP_CACHE = 8

# Database structure constants
COUNTRY_BEGIN = 16776960
STATE_BEGIN_REV0 = 16700000
STATE_BEGIN_REV1 = 16000000

STRUCTURE_INFO_MAX_SIZE = 20
DATABASE_INFO_MAX_SIZE = 100

# Database editions
COUNTRY_EDITION = 1
COUNTRY_EDITION_V6 = 12
REGION_EDITION_REV0 = 7
REGION_EDITION_REV1 = 3
CITY_EDITION_REV0 = 6
CITY_EDITION_REV1 = 2
CITY_EDITION_REV1_V6 = 30
ORG_EDITION = 5
ISP_EDITION = 4
ASNUM_EDITION = 9
ASNUM_EDITION_V6 = 21
# Not yet supported databases
PROXY_EDITION = 8
NETSPEED_EDITION = 11

# Collection of databases
IPV6_EDITIONS = (COUNTRY_EDITION_V6, ASNUM_EDITION_V6, CITY_EDITION_REV1_V6)
CITY_EDITIONS = (CITY_EDITION_REV0, CITY_EDITION_REV1, CITY_EDITION_REV1_V6)
REGION_EDITIONS = (REGION_EDITION_REV0, REGION_EDITION_REV1)
REGION_CITY_EDITIONS = REGION_EDITIONS + CITY_EDITIONS

SEGMENT_RECORD_LENGTH = 3
STANDARD_RECORD_LENGTH = 3
ORG_RECORD_LENGTH = 4
MAX_RECORD_LENGTH = 4
MAX_ORG_RECORD_LENGTH = 300
FULL_RECORD_LENGTH = 50

US_OFFSET = 1
CANADA_OFFSET = 677
WORLD_OFFSET = 1353
FIPS_RANGE = 360
ENCODING = 'iso-8859-1'

########NEW FILE########
__FILENAME__ = timezone
# -*- coding: utf-8 -*-
"""
Time zone functions. Part of the pygeoip package.

@author: Jennifer Ennis <zaylea@gmail.com>

@license: Copyright(C) 2004 MaxMind LLC

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/lgpl.txt>.
"""

__all__ = ['time_zone_by_country_and_region']

_country = {
    'AD': 'Europe/Andorra',
    'AE': 'Asia/Dubai',
    'AF': 'Asia/Kabul',
    'AG': 'America/Antigua',
    'AI': 'America/Anguilla',
    'AL': 'Europe/Tirane',
    'AM': 'Asia/Yerevan',
    'AN': 'America/Curacao',
    'AO': 'Africa/Luanda',
    'AR': {
        '01': 'America/Argentina/Buenos_Aires',
        '02': 'America/Argentina/Catamarca',
        '03': 'America/Argentina/Tucuman',
        '04': 'America/Argentina/Rio_Gallegos',
        '05': 'America/Argentina/Cordoba',
        '06': 'America/Argentina/Tucuman',
        '07': 'America/Argentina/Buenos_Aires',
        '08': 'America/Argentina/Buenos_Aires',
        '09': 'America/Argentina/Tucuman',
        '10': 'America/Argentina/Jujuy',
        '11': 'America/Argentina/San_Luis',
        '12': 'America/Argentina/La_Rioja',
        '13': 'America/Argentina/Mendoza',
        '14': 'America/Argentina/Buenos_Aires',
        '15': 'America/Argentina/San_Luis',
        '16': 'America/Argentina/Buenos_Aires',
        '17': 'America/Argentina/Salta',
        '18': 'America/Argentina/San_Juan',
        '19': 'America/Argentina/San_Luis',
        '20': 'America/Argentina/Rio_Gallegos',
        '21': 'America/Argentina/Buenos_Aires',
        '22': 'America/Argentina/Catamarca',
        '23': 'America/Argentina/Ushuaia',
        '24': 'America/Argentina/Tucuman'
    },
    'AS': 'US/Samoa',
    'AT': 'Europe/Vienna',
    'AU': {
        '01': 'Australia/Canberra',
        '02': 'Australia/NSW',
        '03': 'Australia/North',
        '04': 'Australia/Queensland',
        '05': 'Australia/South',
        '06': 'Australia/Tasmania',
        '07': 'Australia/Victoria',
        '08': 'Australia/West'
    },
    'AW': 'America/Aruba',
    'AX': 'Europe/Mariehamn',
    'AZ': 'Asia/Baku',
    'BA': 'Europe/Sarajevo',
    'BB': 'America/Barbados',
    'BD': 'Asia/Dhaka',
    'BE': 'Europe/Brussels',
    'BF': 'Africa/Ouagadougou',
    'BG': 'Europe/Sofia',
    'BH': 'Asia/Bahrain',
    'BI': 'Africa/Bujumbura',
    'BJ': 'Africa/Porto-Novo',
    'BL': 'America/St_Barthelemy',
    'BM': 'Atlantic/Bermuda',
    'BN': 'Asia/Brunei',
    'BO': 'America/La_Paz',
    'BQ': 'America/Curacao',
    'BR': {
        '01': 'America/Rio_Branco',
        '02': 'America/Maceio',
        '03': 'America/Sao_Paulo',
        '04': 'America/Manaus',
        '05': 'America/Bahia',
        '06': 'America/Fortaleza',
        '07': 'America/Sao_Paulo',
        '08': 'America/Sao_Paulo',
        '11': 'America/Campo_Grande',
        '13': 'America/Belem',
        '14': 'America/Cuiaba',
        '15': 'America/Sao_Paulo',
        '16': 'America/Belem',
        '17': 'America/Recife',
        '18': 'America/Sao_Paulo',
        '20': 'America/Fortaleza',
        '21': 'America/Sao_Paulo',
        '22': 'America/Recife',
        '23': 'America/Sao_Paulo',
        '24': 'America/Porto_Velho',
        '25': 'America/Boa_Vista',
        '26': 'America/Sao_Paulo',
        '27': 'America/Sao_Paulo',
        '28': 'America/Maceio',
        '29': 'America/Sao_Paulo',
        '30': 'America/Recife',
        '31': 'America/Araguaina'
    },
    'BS': 'America/Nassau',
    'BT': 'Asia/Thimphu',
    'BW': 'Africa/Gaborone',
    'BY': 'Europe/Minsk',
    'BZ': 'America/Belize',
    'CA': {
        'AB': 'America/Edmonton',
        'BC': 'America/Vancouver',
        'MB': 'America/Winnipeg',
        'NB': 'America/Halifax',
        'NL': 'America/St_Johns',
        'NS': 'America/Halifax',
        'NT': 'America/Yellowknife',
        'NU': 'America/Rankin_Inlet',
        'ON': 'America/Toronto',
        'PE': 'America/Halifax',
        'QC': 'America/Montreal',
        'SK': 'America/Regina',
        'YT': 'America/Whitehorse'
    },
    'CC': 'Indian/Cocos',
    'CD': {
        '02': 'Africa/Kinshasa',
        '05': 'Africa/Lubumbashi',
        '06': 'Africa/Kinshasa',
        '08': 'Africa/Kinshasa',
        '10': 'Africa/Lubumbashi',
        '11': 'Africa/Lubumbashi',
        '12': 'Africa/Lubumbashi'
    },
    'CF': 'Africa/Bangui',
    'CG': 'Africa/Brazzaville',
    'CH': 'Europe/Zurich',
    'CI': 'Africa/Abidjan',
    'CK': 'Pacific/Rarotonga',
    'CL': 'Chile/Continental',
    'CM': 'Africa/Lagos',
    'CN': {
        '01': 'Asia/Shanghai',
        '02': 'Asia/Shanghai',
        '03': 'Asia/Shanghai',
        '04': 'Asia/Shanghai',
        '05': 'Asia/Harbin',
        '06': 'Asia/Chongqing',
        '07': 'Asia/Shanghai',
        '08': 'Asia/Harbin',
        '09': 'Asia/Shanghai',
        '10': 'Asia/Shanghai',
        '11': 'Asia/Chongqing',
        '12': 'Asia/Shanghai',
        '13': 'Asia/Urumqi',
        '14': 'Asia/Chongqing',
        '15': 'Asia/Chongqing',
        '16': 'Asia/Chongqing',
        '18': 'Asia/Chongqing',
        '19': 'Asia/Harbin',
        '20': 'Asia/Harbin',
        '21': 'Asia/Chongqing',
        '22': 'Asia/Harbin',
        '23': 'Asia/Shanghai',
        '24': 'Asia/Chongqing',
        '25': 'Asia/Shanghai',
        '26': 'Asia/Chongqing',
        '28': 'Asia/Shanghai',
        '29': 'Asia/Chongqing',
        '30': 'Asia/Chongqing',
        '31': 'Asia/Chongqing',
        '32': 'Asia/Chongqing',
        '33': 'Asia/Chongqing'
    },
    'CO': 'America/Bogota',
    'CR': 'America/Costa_Rica',
    'CU': 'America/Havana',
    'CV': 'Atlantic/Cape_Verde',
    'CW': 'America/Curacao',
    'CX': 'Indian/Christmas',
    'CY': 'Asia/Nicosia',
    'CZ': 'Europe/Prague',
    'DE': 'Europe/Berlin',
    'DJ': 'Africa/Djibouti',
    'DK': 'Europe/Copenhagen',
    'DM': 'America/Dominica',
    'DO': 'America/Santo_Domingo',
    'DZ': 'Africa/Algiers',
    'EC': {
        '01': 'Pacific/Galapagos',
        '02': 'America/Guayaquil',
        '03': 'America/Guayaquil',
        '04': 'America/Guayaquil',
        '05': 'America/Guayaquil',
        '06': 'America/Guayaquil',
        '07': 'America/Guayaquil',
        '08': 'America/Guayaquil',
        '09': 'America/Guayaquil',
        '10': 'America/Guayaquil',
        '11': 'America/Guayaquil',
        '12': 'America/Guayaquil',
        '13': 'America/Guayaquil',
        '14': 'America/Guayaquil',
        '15': 'America/Guayaquil',
        '17': 'America/Guayaquil',
        '18': 'America/Guayaquil',
        '19': 'America/Guayaquil',
        '20': 'America/Guayaquil',
        '22': 'America/Guayaquil'
    },
    'EE': 'Europe/Tallinn',
    'EG': 'Africa/Cairo',
    'EH': 'Africa/El_Aaiun',
    'ER': 'Africa/Asmera',
    'ES': {
        '07': 'Europe/Madrid',
        '27': 'Europe/Madrid',
        '29': 'Europe/Madrid',
        '31': 'Europe/Madrid',
        '32': 'Europe/Madrid',
        '34': 'Europe/Madrid',
        '39': 'Europe/Madrid',
        '51': 'Africa/Ceuta',
        '52': 'Europe/Madrid',
        '53': 'Atlantic/Canary',
        '54': 'Europe/Madrid',
        '55': 'Europe/Madrid',
        '56': 'Europe/Madrid',
        '57': 'Europe/Madrid',
        '58': 'Europe/Madrid',
        '59': 'Europe/Madrid',
        '60': 'Europe/Madrid'
    },
    'ET': 'Africa/Addis_Ababa',
    'FI': 'Europe/Helsinki',
    'FJ': 'Pacific/Fiji',
    'FK': 'Atlantic/Stanley',
    'FO': 'Atlantic/Faeroe',
    'FR': 'Europe/Paris',
    'FX': 'Europe/Paris',
    'GA': 'Africa/Libreville',
    'GB': 'Europe/London',
    'GD': 'America/Grenada',
    'GE': 'Asia/Tbilisi',
    'GF': 'America/Cayenne',
    'GG': 'Europe/Guernsey',
    'GH': 'Africa/Accra',
    'GI': 'Europe/Gibraltar',
    'GL': {
        '01': 'America/Thule',
        '02': 'America/Godthab',
        '03': 'America/Godthab'
    },
    'GM': 'Africa/Banjul',
    'GN': 'Africa/Conakry',
    'GP': 'America/Guadeloupe',
    'GQ': 'Africa/Malabo',
    'GR': 'Europe/Athens',
    'GS': 'Atlantic/South_Georgia',
    'GT': 'America/Guatemala',
    'GU': 'Pacific/Guam',
    'GW': 'Africa/Bissau',
    'GY': 'America/Guyana',
    'HK': 'Asia/Hong_Kong',
    'HN': 'America/Tegucigalpa',
    'HR': 'Europe/Zagreb',
    'HT': 'America/Port-au-Prince',
    'HU': 'Europe/Budapest',
    'ID': {
        '01': 'Asia/Pontianak',
        '02': 'Asia/Makassar',
        '03': 'Asia/Jakarta',
        '04': 'Asia/Jakarta',
        '05': 'Asia/Jakarta',
        '06': 'Asia/Jakarta',
        '07': 'Asia/Jakarta',
        '08': 'Asia/Jakarta',
        '09': 'Asia/Jayapura',
        '10': 'Asia/Jakarta',
        '11': 'Asia/Pontianak',
        '12': 'Asia/Makassar',
        '13': 'Asia/Makassar',
        '14': 'Asia/Makassar',
        '15': 'Asia/Jakarta',
        '16': 'Asia/Makassar',
        '17': 'Asia/Makassar',
        '18': 'Asia/Makassar',
        '19': 'Asia/Pontianak',
        '20': 'Asia/Makassar',
        '21': 'Asia/Makassar',
        '22': 'Asia/Makassar',
        '23': 'Asia/Makassar',
        '24': 'Asia/Jakarta',
        '25': 'Asia/Pontianak',
        '26': 'Asia/Pontianak',
        '30': 'Asia/Jakarta',
        '31': 'Asia/Makassar',
        '33': 'Asia/Jakarta'
    },
    'IE': 'Europe/Dublin',
    'IL': 'Asia/Jerusalem',
    'IM': 'Europe/Isle_of_Man',
    'IN': 'Asia/Calcutta',
    'IO': 'Indian/Chagos',
    'IQ': 'Asia/Baghdad',
    'IR': 'Asia/Tehran',
    'IS': 'Atlantic/Reykjavik',
    'IT': 'Europe/Rome',
    'JE': 'Europe/Jersey',
    'JM': 'America/Jamaica',
    'JO': 'Asia/Amman',
    'JP': 'Asia/Tokyo',
    'KE': 'Africa/Nairobi',
    'KG': 'Asia/Bishkek',
    'KH': 'Asia/Phnom_Penh',
    'KI': 'Pacific/Tarawa',
    'KM': 'Indian/Comoro',
    'KN': 'America/St_Kitts',
    'KP': 'Asia/Pyongyang',
    'KR': 'Asia/Seoul',
    'KW': 'Asia/Kuwait',
    'KY': 'America/Cayman',
    'KZ': {
        '01': 'Asia/Almaty',
        '02': 'Asia/Almaty',
        '03': 'Asia/Qyzylorda',
        '04': 'Asia/Aqtobe',
        '05': 'Asia/Qyzylorda',
        '06': 'Asia/Aqtau',
        '07': 'Asia/Oral',
        '08': 'Asia/Qyzylorda',
        '09': 'Asia/Aqtau',
        '10': 'Asia/Qyzylorda',
        '11': 'Asia/Almaty',
        '12': 'Asia/Qyzylorda',
        '13': 'Asia/Aqtobe',
        '14': 'Asia/Qyzylorda',
        '15': 'Asia/Almaty',
        '16': 'Asia/Aqtobe',
        '17': 'Asia/Almaty'
    },
    'LA': 'Asia/Vientiane',
    'LB': 'Asia/Beirut',
    'LC': 'America/St_Lucia',
    'LI': 'Europe/Vaduz',
    'LK': 'Asia/Colombo',
    'LR': 'Africa/Monrovia',
    'LS': 'Africa/Maseru',
    'LT': 'Europe/Vilnius',
    'LU': 'Europe/Luxembourg',
    'LV': 'Europe/Riga',
    'LY': 'Africa/Tripoli',
    'MA': 'Africa/Casablanca',
    'MC': 'Europe/Monaco',
    'MD': 'Europe/Chisinau',
    'ME': 'Europe/Podgorica',
    'MF': 'America/Marigot',
    'MG': 'Indian/Antananarivo',
    'MK': 'Europe/Skopje',
    'ML': 'Africa/Bamako',
    'MM': 'Asia/Rangoon',
    'MN': 'Asia/Choibalsan',
    'MO': 'Asia/Macao',
    'MP': 'Pacific/Saipan',
    'MQ': 'America/Martinique',
    'MR': 'Africa/Nouakchott',
    'MS': 'America/Montserrat',
    'MT': 'Europe/Malta',
    'MU': 'Indian/Mauritius',
    'MV': 'Indian/Maldives',
    'MW': 'Africa/Blantyre',
    'MX': {
        '01': 'America/Mexico_City',
        '02': 'America/Tijuana',
        '03': 'America/Hermosillo',
        '04': 'America/Merida',
        '05': 'America/Mexico_City',
        '06': 'America/Chihuahua',
        '07': 'America/Monterrey',
        '08': 'America/Mexico_City',
        '09': 'America/Mexico_City',
        '10': 'America/Mazatlan',
        '11': 'America/Mexico_City',
        '12': 'America/Mexico_City',
        '13': 'America/Mexico_City',
        '14': 'America/Mazatlan',
        '15': 'America/Chihuahua',
        '16': 'America/Mexico_City',
        '17': 'America/Mexico_City',
        '18': 'America/Mazatlan',
        '19': 'America/Monterrey',
        '20': 'America/Mexico_City',
        '21': 'America/Mexico_City',
        '22': 'America/Mexico_City',
        '23': 'America/Cancun',
        '24': 'America/Mexico_City',
        '25': 'America/Mazatlan',
        '26': 'America/Hermosillo',
        '27': 'America/Merida',
        '28': 'America/Monterrey',
        '29': 'America/Mexico_City',
        '30': 'America/Mexico_City',
        '31': 'America/Merida',
        '32': 'America/Monterrey'
    },
    'MY': {
        '01': 'Asia/Kuala_Lumpur',
        '02': 'Asia/Kuala_Lumpur',
        '03': 'Asia/Kuala_Lumpur',
        '04': 'Asia/Kuala_Lumpur',
        '05': 'Asia/Kuala_Lumpur',
        '06': 'Asia/Kuala_Lumpur',
        '07': 'Asia/Kuala_Lumpur',
        '08': 'Asia/Kuala_Lumpur',
        '09': 'Asia/Kuala_Lumpur',
        '11': 'Asia/Kuching',
        '12': 'Asia/Kuala_Lumpur',
        '13': 'Asia/Kuala_Lumpur',
        '14': 'Asia/Kuala_Lumpur',
        '15': 'Asia/Kuching',
        '16': 'Asia/Kuching'
    },
    'MZ': 'Africa/Maputo',
    'NA': 'Africa/Windhoek',
    'NC': 'Pacific/Noumea',
    'NE': 'Africa/Niamey',
    'NF': 'Pacific/Norfolk',
    'NG': 'Africa/Lagos',
    'NI': 'America/Managua',
    'NL': 'Europe/Amsterdam',
    'NO': 'Europe/Oslo',
    'NP': 'Asia/Katmandu',
    'NR': 'Pacific/Nauru',
    'NU': 'Pacific/Niue',
    'NZ': {
        '85': 'Pacific/Auckland',
        'E7': 'Pacific/Auckland',
        'E8': 'Pacific/Auckland',
        'E9': 'Pacific/Auckland',
        'F1': 'Pacific/Auckland',
        'F2': 'Pacific/Auckland',
        'F3': 'Pacific/Auckland',
        'F4': 'Pacific/Auckland',
        'F5': 'Pacific/Auckland',
        'F7': 'Pacific/Chatham',
        'F8': 'Pacific/Auckland',
        'F9': 'Pacific/Auckland',
        'G1': 'Pacific/Auckland',
        'G2': 'Pacific/Auckland',
        'G3': 'Pacific/Auckland'
    },
    'OM': 'Asia/Muscat',
    'PA': 'America/Panama',
    'PE': 'America/Lima',
    'PF': 'Pacific/Marquesas',
    'PG': 'Pacific/Port_Moresby',
    'PH': 'Asia/Manila',
    'PK': 'Asia/Karachi',
    'PL': 'Europe/Warsaw',
    'PM': 'America/Miquelon',
    'PN': 'Pacific/Pitcairn',
    'PR': 'America/Puerto_Rico',
    'PS': 'Asia/Gaza',
    'PT': {
        '02': 'Europe/Lisbon',
        '03': 'Europe/Lisbon',
        '04': 'Europe/Lisbon',
        '05': 'Europe/Lisbon',
        '06': 'Europe/Lisbon',
        '07': 'Europe/Lisbon',
        '08': 'Europe/Lisbon',
        '09': 'Europe/Lisbon',
        '10': 'Atlantic/Madeira',
        '11': 'Europe/Lisbon',
        '13': 'Europe/Lisbon',
        '14': 'Europe/Lisbon',
        '16': 'Europe/Lisbon',
        '17': 'Europe/Lisbon',
        '18': 'Europe/Lisbon',
        '19': 'Europe/Lisbon',
        '20': 'Europe/Lisbon',
        '21': 'Europe/Lisbon',
        '22': 'Europe/Lisbon'
    },
    'PW': 'Pacific/Palau',
    'PY': 'America/Asuncion',
    'QA': 'Asia/Qatar',
    'RE': 'Indian/Reunion',
    'RO': 'Europe/Bucharest',
    'RS': 'Europe/Belgrade',
    'RU': {
        '01': 'Europe/Volgograd',
        '02': 'Asia/Irkutsk',
        '03': 'Asia/Novokuznetsk',
        '04': 'Asia/Novosibirsk',
        '05': 'Asia/Vladivostok',
        '06': 'Europe/Moscow',
        '07': 'Europe/Volgograd',
        '08': 'Europe/Samara',
        '09': 'Europe/Moscow',
        '10': 'Europe/Moscow',
        '11': 'Asia/Irkutsk',
        '13': 'Asia/Yekaterinburg',
        '14': 'Asia/Irkutsk',
        '15': 'Asia/Anadyr',
        '16': 'Europe/Samara',
        '17': 'Europe/Volgograd',
        '18': 'Asia/Krasnoyarsk',
        '20': 'Asia/Irkutsk',
        '21': 'Europe/Moscow',
        '22': 'Europe/Volgograd',
        '23': 'Europe/Kaliningrad',
        '24': 'Europe/Volgograd',
        '25': 'Europe/Moscow',
        '26': 'Asia/Kamchatka',
        '27': 'Europe/Volgograd',
        '28': 'Europe/Moscow',
        '29': 'Asia/Novokuznetsk',
        '30': 'Asia/Vladivostok',
        '31': 'Asia/Krasnoyarsk',
        '32': 'Asia/Omsk',
        '33': 'Asia/Yekaterinburg',
        '34': 'Asia/Yekaterinburg',
        '35': 'Asia/Yekaterinburg',
        '36': 'Asia/Anadyr',
        '37': 'Europe/Moscow',
        '38': 'Europe/Volgograd',
        '39': 'Asia/Krasnoyarsk',
        '40': 'Asia/Yekaterinburg',
        '41': 'Europe/Moscow',
        '42': 'Europe/Moscow',
        '43': 'Europe/Moscow',
        '44': 'Asia/Magadan',
        '45': 'Europe/Samara',
        '46': 'Europe/Samara',
        '47': 'Europe/Moscow',
        '48': 'Europe/Moscow',
        '49': 'Europe/Moscow',
        '50': 'Asia/Yekaterinburg',
        '51': 'Europe/Moscow',
        '52': 'Europe/Moscow',
        '53': 'Asia/Novosibirsk',
        '54': 'Asia/Omsk',
        '55': 'Europe/Samara',
        '56': 'Europe/Moscow',
        '57': 'Europe/Samara',
        '58': 'Asia/Yekaterinburg',
        '59': 'Asia/Vladivostok',
        '60': 'Europe/Kaliningrad',
        '61': 'Europe/Volgograd',
        '62': 'Europe/Moscow',
        '63': 'Asia/Yakutsk',
        '64': 'Asia/Sakhalin',
        '65': 'Europe/Samara',
        '66': 'Europe/Moscow',
        '67': 'Europe/Samara',
        '68': 'Europe/Volgograd',
        '69': 'Europe/Moscow',
        '70': 'Europe/Volgograd',
        '71': 'Asia/Yekaterinburg',
        '72': 'Europe/Moscow',
        '73': 'Europe/Samara',
        '74': 'Asia/Krasnoyarsk',
        '75': 'Asia/Novosibirsk',
        '76': 'Europe/Moscow',
        '77': 'Europe/Moscow',
        '78': 'Asia/Yekaterinburg',
        '79': 'Asia/Irkutsk',
        '80': 'Asia/Yekaterinburg',
        '81': 'Europe/Samara',
        '82': 'Asia/Irkutsk',
        '83': 'Europe/Moscow',
        '84': 'Europe/Volgograd',
        '85': 'Europe/Moscow',
        '86': 'Europe/Moscow',
        '87': 'Asia/Novosibirsk',
        '88': 'Europe/Moscow',
        '89': 'Asia/Vladivostok'
    },
    'RW': 'Africa/Kigali',
    'SA': 'Asia/Riyadh',
    'SB': 'Pacific/Guadalcanal',
    'SC': 'Indian/Mahe',
    'SD': 'Africa/Khartoum',
    'SE': 'Europe/Stockholm',
    'SG': 'Asia/Singapore',
    'SH': 'Atlantic/St_Helena',
    'SI': 'Europe/Ljubljana',
    'SJ': 'Arctic/Longyearbyen',
    'SK': 'Europe/Bratislava',
    'SL': 'Africa/Freetown',
    'SM': 'Europe/San_Marino',
    'SN': 'Africa/Dakar',
    'SO': 'Africa/Mogadishu',
    'SR': 'America/Paramaribo',
    'SS': 'Africa/Juba',
    'ST': 'Africa/Sao_Tome',
    'SV': 'America/El_Salvador',
    'SX': 'America/Curacao',
    'SY': 'Asia/Damascus',
    'SZ': 'Africa/Mbabane',
    'TC': 'America/Grand_Turk',
    'TD': 'Africa/Ndjamena',
    'TF': 'Indian/Kerguelen',
    'TG': 'Africa/Lome',
    'TH': 'Asia/Bangkok',
    'TJ': 'Asia/Dushanbe',
    'TK': 'Pacific/Fakaofo',
    'TL': 'Asia/Dili',
    'TM': 'Asia/Ashgabat',
    'TN': 'Africa/Tunis',
    'TO': 'Pacific/Tongatapu',
    'TR': 'Asia/Istanbul',
    'TT': 'America/Port_of_Spain',
    'TV': 'Pacific/Funafuti',
    'TW': 'Asia/Taipei',
    'TZ': 'Africa/Dar_es_Salaam',
    'UA': {
        '01': 'Europe/Kiev',
        '02': 'Europe/Kiev',
        '03': 'Europe/Uzhgorod',
        '04': 'Europe/Zaporozhye',
        '05': 'Europe/Zaporozhye',
        '06': 'Europe/Uzhgorod',
        '07': 'Europe/Zaporozhye',
        '08': 'Europe/Simferopol',
        '09': 'Europe/Kiev',
        '10': 'Europe/Zaporozhye',
        '11': 'Europe/Simferopol',
        '13': 'Europe/Kiev',
        '14': 'Europe/Zaporozhye',
        '15': 'Europe/Uzhgorod',
        '16': 'Europe/Zaporozhye',
        '17': 'Europe/Simferopol',
        '18': 'Europe/Zaporozhye',
        '19': 'Europe/Kiev',
        '20': 'Europe/Simferopol',
        '21': 'Europe/Kiev',
        '22': 'Europe/Uzhgorod',
        '23': 'Europe/Kiev',
        '24': 'Europe/Uzhgorod',
        '25': 'Europe/Uzhgorod',
        '26': 'Europe/Zaporozhye',
        '27': 'Europe/Kiev'
    },
    'UG': 'Africa/Kampala',
    'US': {
        'AK': 'America/Anchorage',
        'AL': 'America/Chicago',
        'AR': 'America/Chicago',
        'AZ': 'America/Phoenix',
        'CA': 'America/Los_Angeles',
        'CO': 'America/Denver',
        'CT': 'America/New_York',
        'DC': 'America/New_York',
        'DE': 'America/New_York',
        'FL': 'America/New_York',
        'GA': 'America/New_York',
        'HI': 'Pacific/Honolulu',
        'IA': 'America/Chicago',
        'ID': 'America/Denver',
        'IL': 'America/Chicago',
        'IN': 'America/Indianapolis',
        'KS': 'America/Chicago',
        'KY': 'America/New_York',
        'LA': 'America/Chicago',
        'MA': 'America/New_York',
        'MD': 'America/New_York',
        'ME': 'America/New_York',
        'MI': 'America/New_York',
        'MN': 'America/Chicago',
        'MO': 'America/Chicago',
        'MS': 'America/Chicago',
        'MT': 'America/Denver',
        'NC': 'America/New_York',
        'ND': 'America/Chicago',
        'NE': 'America/Chicago',
        'NH': 'America/New_York',
        'NJ': 'America/New_York',
        'NM': 'America/Denver',
        'NV': 'America/Los_Angeles',
        'NY': 'America/New_York',
        'OH': 'America/New_York',
        'OK': 'America/Chicago',
        'OR': 'America/Los_Angeles',
        'PA': 'America/New_York',
        'RI': 'America/New_York',
        'SC': 'America/New_York',
        'SD': 'America/Chicago',
        'TN': 'America/Chicago',
        'TX': 'America/Chicago',
        'UT': 'America/Denver',
        'VA': 'America/New_York',
        'VT': 'America/New_York',
        'WA': 'America/Los_Angeles',
        'WI': 'America/Chicago',
        'WV': 'America/New_York',
        'WY': 'America/Denver'
    },
    'UY': 'America/Montevideo',
    'UZ': {
        '01': 'Asia/Tashkent',
        '02': 'Asia/Samarkand',
        '03': 'Asia/Tashkent',
        '06': 'Asia/Tashkent',
        '07': 'Asia/Samarkand',
        '08': 'Asia/Samarkand',
        '09': 'Asia/Samarkand',
        '10': 'Asia/Samarkand',
        '12': 'Asia/Samarkand',
        '13': 'Asia/Tashkent',
        '14': 'Asia/Tashkent'
    },
    'VA': 'Europe/Vatican',
    'VC': 'America/St_Vincent',
    'VE': 'America/Caracas',
    'VG': 'America/Tortola',
    'VI': 'America/St_Thomas',
    'VN': 'Asia/Phnom_Penh',
    'VU': 'Pacific/Efate',
    'WF': 'Pacific/Wallis',
    'WS': 'Pacific/Samoa',
    'YE': 'Asia/Aden',
    'YT': 'Indian/Mayotte',
    'YU': 'Europe/Belgrade',
    'ZA': 'Africa/Johannesburg',
    'ZM': 'Africa/Lusaka',
    'ZW': 'Africa/Harare'
 }


def time_zone_by_country_and_region(country_code, region_name=None):
    if country_code not in _country:
        return ''

    if not region_name or region_name == '00':
        region_name = None

    timezones = _country[country_code]
    if isinstance(timezones, str):
        return timezones

    if not region_name:
        return ''

    return timezones.get(region_name)

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
"""
Utility functions. Part of the pygeoip package.

@author: Jennifer Ennis <zaylea@gmail.com>

@license: Copyright(C) 2004 MaxMind LLC

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/lgpl.txt>.
"""

import socket
import binascii


def ip2long(ip):
    """
    Wrapper function for IPv4 and IPv6 converters
    @param ip: IPv4 or IPv6 address
    @type ip: str
    """
    try:
        return int(binascii.hexlify(socket.inet_aton(ip)), 16)
    except socket.error:
        return int(binascii.hexlify(socket.inet_pton(socket.AF_INET6, ip)), 16)

########NEW FILE########
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.2.0"


# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform == "java":
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
            del X


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        result = self._resolve()
        setattr(obj, self.name, result)
        # This is a bit ugly, but it avoids running this again.
        delattr(tp, self.name)
        return result


class MovedModule(_LazyDescr):

    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)


class MovedAttribute(_LazyDescr):

    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)



class _MovedItems(types.ModuleType):
    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
del attr

moves = sys.modules["six.moves"] = _MovedItems("moves")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_code = "__code__"
    _func_defaults = "__defaults__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_code = "func_code"
    _func_defaults = "func_defaults"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator


if PY3:
    def get_unbound_function(unbound):
        return unbound

    Iterator = object

    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)
else:
    def get_unbound_function(unbound):
        return unbound.im_func

    class Iterator(object):

        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)


def iterkeys(d):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)())

def itervalues(d):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)())

def iteritems(d):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)())


if PY3:
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    def u(s):
        return unicode(s, "unicode_escape")
    int2byte = chr
    import StringIO
    StringIO = BytesIO = StringIO.StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


if PY3:
    import builtins
    exec_ = getattr(builtins, "exec")


    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value


    print_ = getattr(builtins, "print")
    del builtins

else:
    def exec_(code, globs=None, locs=None):
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe(1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec("""exec code in globs, locs""")


    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")


    def print_(*args, **kwargs):
        """The new-style print function."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return
        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, base=object):
    """Create a base class with a metaclass."""
    return meta("NewBase", (base,), {})

########NEW FILE########
__FILENAME__ = api
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import os
import mimetypes

from tweepy.binder import bind_api
from tweepy.error import TweepError
from tweepy.parsers import ModelParser
from tweepy.utils import list_to_csv


class API(object):
    """Twitter API"""

    def __init__(self, auth_handler=None,
            host='api.twitter.com', search_host='search.twitter.com',
             cache=None, secure=True, api_root='/1.1', search_root='',
            retry_count=0, retry_delay=0, retry_errors=None, timeout=60,
            parser=None, compression=False):
        self.auth = auth_handler
        self.host = host
        self.search_host = search_host
        self.api_root = api_root
        self.search_root = search_root
        self.cache = cache
        self.secure = secure
        self.compression = compression
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.retry_errors = retry_errors
        self.timeout = timeout
        self.parser = parser or ModelParser()

    """ statuses/home_timeline """
    home_timeline = bind_api(
        path = '/statuses/home_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count'],
        require_auth = True
    )

    """ statuses/user_timeline """
    user_timeline = bind_api(
        path = '/statuses/user_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'since_id',
                          'max_id', 'count', 'include_rts']
    )

    """ statuses/mentions """
    mentions_timeline = bind_api(
        path = '/statuses/mentions_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count'],
        require_auth = True
    )

    """/statuses/:id/retweeted_by.format"""
    retweeted_by = bind_api(
        path = '/statuses/{id}/retweeted_by.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'count', 'page'],
        require_auth = True
    )

    """/related_results/show/:id.format"""
    related_results = bind_api(
        path = '/related_results/show/{id}.json',
        payload_type = 'relation', payload_list = True,
        allowed_param = ['id'],
        require_auth = False
    )

    """/statuses/:id/retweeted_by/ids.format"""
    retweeted_by_ids = bind_api(
        path = '/statuses/{id}/retweeted_by/ids.json',
        payload_type = 'ids',
        allowed_param = ['id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/retweets_of_me """
    retweets_of_me = bind_api(
        path = '/statuses/retweets_of_me.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count'],
        require_auth = True
    )

    """ statuses/show """
    get_status = bind_api(
        path = '/statuses/show.json',
        payload_type = 'status',
        allowed_param = ['id']
    )

    """ statuses/update """
    update_status = bind_api(
        path = '/statuses/update.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['status', 'in_reply_to_status_id', 'lat', 'long', 'source', 'place_id'],
        require_auth = True
    )

    """ statuses/destroy """
    destroy_status = bind_api(
        path = '/statuses/destroy/{id}.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ statuses/retweet """
    retweet = bind_api(
        path = '/statuses/retweet/{id}.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ statuses/retweets """
    retweets = bind_api(
        path = '/statuses/retweets/{id}.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'count'],
        require_auth = True
    )

    """ users/show """
    get_user = bind_api(
        path = '/users/show.json',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name']
    )

    ''' statuses/oembed '''
    get_oembed = bind_api(
        path = '/statuses/oembed.json',
        payload_type = 'json',
        allowed_param = ['id', 'url', 'maxwidth', 'hide_media', 'omit_script', 'align', 'related', 'lang']
    )

    """ Perform bulk look up of users from user ID or screenname """
    def lookup_users(self, user_ids=None, screen_names=None):
        return self._lookup_users(list_to_csv(user_ids), list_to_csv(screen_names))

    _lookup_users = bind_api(
        path = '/users/lookup.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['user_id', 'screen_name'],
    )

    """ Get the authenticated user """
    def me(self):
        return self.get_user(screen_name=self.auth.get_username())

    """ users/search """
    search_users = bind_api(
        path = '/users/search.json',
        payload_type = 'user', payload_list = True,
        require_auth = True,
        allowed_param = ['q', 'per_page', 'page']
    )

    """ users/suggestions/:slug """
    suggested_users = bind_api(
        path = '/users/suggestions/{slug}.json',
        payload_type = 'user', payload_list = True,
        require_auth = True,
        allowed_param = ['slug', 'lang']
    )

    """ users/suggestions """
    suggested_categories = bind_api(
        path = '/users/suggestions.json',
        payload_type = 'category', payload_list = True,
        allowed_param = ['lang'],
        require_auth = True
    )

    """ users/suggestions/:slug/members """
    suggested_users_tweets = bind_api(
        path = '/users/suggestions/{slug}/members.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['slug'],
        require_auth = True
    )

    """ direct_messages """
    direct_messages = bind_api(
        path = '/direct_messages.json',
        payload_type = 'direct_message', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count'],
        require_auth = True
    )

    """ direct_messages/show """
    get_direct_message = bind_api(
        path = '/direct_messages/show/{id}.json',
        payload_type = 'direct_message',
        allowed_param = ['id'],
        require_auth = True
    )

    """ direct_messages/sent """
    sent_direct_messages = bind_api(
        path = '/direct_messages/sent.json',
        payload_type = 'direct_message', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ direct_messages/new """
    send_direct_message = bind_api(
        path = '/direct_messages/new.json',
        method = 'POST',
        payload_type = 'direct_message',
        allowed_param = ['user', 'screen_name', 'user_id', 'text'],
        require_auth = True
    )

    """ direct_messages/destroy """
    destroy_direct_message = bind_api(
        path = '/direct_messages/destroy.json',
        method = 'DELETE',
        payload_type = 'direct_message',
        allowed_param = ['id'],
        require_auth = True
    )

    """ friendships/create """
    create_friendship = bind_api(
        path = '/friendships/create.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name', 'follow'],
        require_auth = True
    )

    """ friendships/destroy """
    destroy_friendship = bind_api(
        path = '/friendships/destroy.json',
        method = 'DELETE',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ friendships/show """
    show_friendship = bind_api(
        path = '/friendships/show.json',
        payload_type = 'friendship',
        allowed_param = ['source_id', 'source_screen_name',
                          'target_id', 'target_screen_name']
    )

    """ Perform bulk look up of friendships from user ID or screenname """
    def lookup_friendships(self, user_ids=None, screen_names=None):
        return self._lookup_friendships(list_to_csv(user_ids), list_to_csv(screen_names))

    _lookup_friendships = bind_api(
        path = '/friendships/lookup.json',
        payload_type = 'relationship', payload_list = True,
        allowed_param = ['user_id', 'screen_name'],
        require_auth = True
    )


    """ friends/ids """
    friends_ids = bind_api(
        path = '/friends/ids.json',
        payload_type = 'ids',
        allowed_param = ['id', 'user_id', 'screen_name', 'cursor']
    )

    """ friends/list """
    friends = bind_api(
        path = '/friends/list.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'cursor']
    )

    """ friendships/incoming """
    friendships_incoming = bind_api(
        path = '/friendships/incoming.json',
        payload_type = 'ids',
        allowed_param = ['cursor']
    )

    """ friendships/outgoing"""
    friendships_outgoing = bind_api(
        path = '/friendships/outgoing.json',
        payload_type = 'ids',
        allowed_param = ['cursor']
    )

    """ followers/ids """
    followers_ids = bind_api(
        path = '/followers/ids.json',
        payload_type = 'ids',
        allowed_param = ['id', 'user_id', 'screen_name', 'cursor']
    )

    """ followers/list """
    followers = bind_api(
        path = '/followers/list.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'cursor']
    )

    """ account/verify_credentials """
    def verify_credentials(self, **kargs):
        try:
            return bind_api(
                path = '/account/verify_credentials.json',
                payload_type = 'user',
                require_auth = True,
                allowed_param = ['include_entities', 'skip_status'],
            )(self, **kargs)
        except TweepError, e:
            if e.response and e.response.status == 401:
                return False
            raise

    """ account/rate_limit_status """
    rate_limit_status = bind_api(
        path = '/application/rate_limit_status.json',
        payload_type = 'json',
        allowed_param = ['resources'],
        use_cache = False
    )

    """ account/update_delivery_device """
    set_delivery_device = bind_api(
        path = '/account/update_delivery_device.json',
        method = 'POST',
        allowed_param = ['device'],
        payload_type = 'user',
        require_auth = True
    )

    """ account/update_profile_colors """
    update_profile_colors = bind_api(
        path = '/account/update_profile_colors.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['profile_background_color', 'profile_text_color',
                          'profile_link_color', 'profile_sidebar_fill_color',
                          'profile_sidebar_border_color'],
        require_auth = True
    )

    """ account/update_profile_image """
    def update_profile_image(self, filename):
        headers, post_data = API._pack_image(filename, 700)
        return bind_api(
            path = '/account/update_profile_image.json',
            method = 'POST',
            payload_type = 'user',
            require_auth = True
        )(self, post_data=post_data, headers=headers)

    """ account/update_profile_background_image """
    def update_profile_background_image(self, filename, *args, **kargs):
        headers, post_data = API._pack_image(filename, 800)
        bind_api(
            path = '/account/update_profile_background_image.json',
            method = 'POST',
            payload_type = 'user',
            allowed_param = ['tile'],
            require_auth = True
        )(self, post_data=post_data, headers=headers)

    """ account/update_profile """
    update_profile = bind_api(
        path = '/account/update_profile.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['name', 'url', 'location', 'description'],
        require_auth = True
    )

    """ favorites """
    favorites = bind_api(
        path = '/favorites/list.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['screen_name', 'user_id', 'max_id', 'count', 'since_id', 'max_id']
    )

    """ favorites/create """
    create_favorite = bind_api(
        path = '/favorites/create.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ favorites/destroy """
    destroy_favorite = bind_api(
        path = '/favorites/destroy.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ blocks/create """
    create_block = bind_api(
        path = '/blocks/create.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ blocks/destroy """
    destroy_block = bind_api(
        path = '/blocks/destroy.json',
        method = 'DELETE',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ blocks/blocking """
    blocks = bind_api(
        path = '/blocks/list.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['cursor'],
        require_auth = True
    )

    """ blocks/blocking/ids """
    blocks_ids = bind_api(
        path = '/blocks/ids.json',
        payload_type = 'json',
        require_auth = True
    )

    """ report_spam """
    report_spam = bind_api(
        path = '/users/report_spam.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['user_id', 'screen_name'],
        require_auth = True
    )

    """ saved_searches """
    saved_searches = bind_api(
        path = '/saved_searches/list.json',
        payload_type = 'saved_search', payload_list = True,
        require_auth = True
    )

    """ saved_searches/show """
    get_saved_search = bind_api(
        path = '/saved_searches/show/{id}.json',
        payload_type = 'saved_search',
        allowed_param = ['id'],
        require_auth = True
    )

    """ saved_searches/create """
    create_saved_search = bind_api(
        path = '/saved_searches/create.json',
        method = 'POST',
        payload_type = 'saved_search',
        allowed_param = ['query'],
        require_auth = True
    )

    """ saved_searches/destroy """
    destroy_saved_search = bind_api(
        path = '/saved_searches/destroy/{id}.json',
        method = 'POST',
        payload_type = 'saved_search',
        allowed_param = ['id'],
        require_auth = True
    )

    """ help/test """
    def test(self):
        try:
            bind_api(
                path = '/help/test.json',
            )(self)
        except TweepError:
            return False
        return True

    create_list = bind_api(
        path = '/lists/create.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['name', 'mode', 'description'],
        require_auth = True
    )

    destroy_list = bind_api(
        path = '/lists/destroy.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['owner_screen_name', 'owner_id', 'list_id', 'slug'],
        require_auth = True
    )

    update_list = bind_api(
        path = '/lists/update.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['list_id', 'slug', 'name', 'mode', 'description', 'owner_screen_name', 'owner_id'],
        require_auth = True
    )

    lists_all = bind_api(
        path = '/lists/list.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['screen_name', 'user_id'],
        require_auth = True
    )

    lists_memberships = bind_api(
        path = '/lists/memberships.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['screen_name', 'user_id', 'filter_to_owned_lists', 'cursor'],
        require_auth = True
    )

    lists_subscriptions = bind_api(
        path = '/lists/subscriptions.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['screen_name', 'user_id', 'cursor'],
        require_auth = True
    )

    list_timeline = bind_api(
        path = '/lists/statuses.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['owner_screen_name', 'slug', 'owner_id', 'list_id', 'since_id', 'max_id', 'count']
    )

    get_list = bind_api(
        path = '/lists/show.json',
        payload_type = 'list',
        allowed_param = ['owner_screen_name', 'owner_id', 'slug', 'list_id']
    )

    add_list_member = bind_api(
        path = '/lists/members/create.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['screen_name', 'user_id', 'owner_screen_name', 'owner_id', 'slug', 'list_id'],
        require_auth = True
    )

    remove_list_member = bind_api(
        path = '/lists/members/destroy.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['screen_name', 'user_id', 'owner_screen_name', 'owner_id', 'slug', 'list_id'],
        require_auth = True
    )

    list_members = bind_api(
        path = '/lists/members.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['owner_screen_name', 'slug', 'list_id', 'owner_id', 'cursor']
    )

    show_list_member = bind_api(
        path = '/lists/members/show.json',
        payload_type = 'user',
        allowed_param = ['list_id', 'slug', 'user_id', 'screen_name', 'owner_screen_name', 'owner_id']
    )

    subscribe_list = bind_api(
        path = '/lists/subscribers/create.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['owner_screen_name', 'slug', 'owner_id', 'list_id'],
        require_auth = True
    )

    unsubscribe_list = bind_api(
        path = '/lists/subscribers/destroy.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['owner_screen_name', 'slug', 'owner_id', 'list_id'],
        require_auth = True
    )

    list_subscribers = bind_api(
        path = '/lists/subscribers.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['owner_screen_name', 'slug', 'owner_id', 'list_id', 'cursor']
    )

    show_list_subscriber = bind_api(
        path = '/lists/subscribers/show.json',
        payload_type = 'user',
        allowed_param = ['owner_screen_name', 'slug', 'screen_name', 'owner_id', 'list_id', 'user_id']
    )

    """ trends/available """
    trends_available = bind_api(
        path = '/trends/available.json',
        payload_type = 'json'
    )

    trends_place = bind_api(
        path = '/trends/place.json',
        payload_type = 'json',
        allowed_param = ['id', 'exclude']
    )

    trends_closest = bind_api(
        path = '/trends/closest.json',
        payload_type = 'json',
        allowed_param = ['lat', 'long']
    )

    """ search """
    search = bind_api(
        path = '/search/tweets.json',
        payload_type = 'search_results',
        allowed_param = ['q', 'lang', 'locale', 'since_id', 'geocode', 'show_user', 'max_id', 'since', 'until', 'result_type']
    )

    """ trends/daily """
    trends_daily = bind_api(
        path = '/trends/daily.json',
        payload_type = 'json',
        allowed_param = ['date', 'exclude']
    )

    """ trends/weekly """
    trends_weekly = bind_api(
        path = '/trends/weekly.json',
        payload_type = 'json',
        allowed_param = ['date', 'exclude']
    )

    """ geo/reverse_geocode """
    reverse_geocode = bind_api(
        path = '/geo/reverse_geocode.json',
        payload_type = 'place', payload_list = True,
        allowed_param = ['lat', 'long', 'accuracy', 'granularity', 'max_results']
    )

    """ geo/id """
    geo_id = bind_api(
        path = '/geo/id/{id}.json',
        payload_type = 'place',
        allowed_param = ['id']
    )

    """ geo/search """
    geo_search = bind_api(
        path = '/geo/search.json',
        payload_type = 'place', payload_list = True,
        allowed_param = ['lat', 'long', 'query', 'ip', 'granularity', 'accuracy', 'max_results', 'contained_within']
    )

    """ geo/similar_places """
    geo_similar_places = bind_api(
        path = '/geo/similar_places.json',
        payload_type = 'place', payload_list = True,
        allowed_param = ['lat', 'long', 'name', 'contained_within']
    )

    """ Internal use only """
    @staticmethod
    def _pack_image(filename, max_size):
        """Pack image from file into multipart-formdata post body"""
        # image must be less than 700kb in size
        try:
            if os.path.getsize(filename) > (max_size * 1024):
                raise TweepError('File is too big, must be less than 700kb.')
        except os.error:
            raise TweepError('Unable to access file')

        # image must be gif, jpeg, or png
        file_type = mimetypes.guess_type(filename)
        if file_type is None:
            raise TweepError('Could not determine file type')
        file_type = file_type[0]
        if file_type not in ['image/gif', 'image/jpeg', 'image/png']:
            raise TweepError('Invalid file type for image: %s' % file_type)

        # build the mulitpart-formdata body
        fp = open(filename, 'rb')
        BOUNDARY = 'Tw3ePy'
        body = []
        body.append('--' + BOUNDARY)
        body.append('Content-Disposition: form-data; name="image"; filename="%s"' % filename)
        body.append('Content-Type: %s' % file_type)
        body.append('')
        body.append(fp.read())
        body.append('--' + BOUNDARY + '--')
        body.append('')
        fp.close()
        body = '\r\n'.join(body)

        # build headers
        headers = {
            'Content-Type': 'multipart/form-data; boundary=Tw3ePy',
            'Content-Length': str(len(body))
        }

        return headers, body


########NEW FILE########
__FILENAME__ = auth
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from urllib2 import Request, urlopen
import base64

from tweepy import oauth
from tweepy.error import TweepError
from tweepy.api import API


class AuthHandler(object):

    def apply_auth(self, url, method, headers, parameters):
        """Apply authentication headers to request"""
        raise NotImplementedError

    def get_username(self):
        """Return the username of the authenticated user"""
        raise NotImplementedError


class BasicAuthHandler(AuthHandler):

    def __init__(self, username, password):
        self.username = username
        self._b64up = base64.b64encode('%s:%s' % (username, password))

    def apply_auth(self, url, method, headers, parameters):
        headers['Authorization'] = 'Basic %s' % self._b64up

    def get_username(self):
        return self.username


class OAuthHandler(AuthHandler):
    """OAuth authentication handler"""

    OAUTH_HOST = 'api.twitter.com'
    OAUTH_ROOT = '/oauth/'

    def __init__(self, consumer_key, consumer_secret, callback=None, secure=False):
        self._consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        self._sigmethod = oauth.OAuthSignatureMethod_HMAC_SHA1()
        self.request_token = None
        self.access_token = None
        self.callback = callback
        self.username = None
        self.secure = secure

    def _get_oauth_url(self, endpoint, secure=False):
        if self.secure or secure:
            prefix = 'https://'
        else:
            prefix = 'http://'

        return prefix + self.OAUTH_HOST + self.OAUTH_ROOT + endpoint

    def apply_auth(self, url, method, headers, parameters):
        request = oauth.OAuthRequest.from_consumer_and_token(
            self._consumer, http_url=url, http_method=method,
            token=self.access_token, parameters=parameters
        )
        request.sign_request(self._sigmethod, self._consumer, self.access_token)
        headers.update(request.to_header())

    def _get_request_token(self):
        try:
            url = self._get_oauth_url('request_token')
            request = oauth.OAuthRequest.from_consumer_and_token(
                self._consumer, http_url=url, callback=self.callback
            )
            request.sign_request(self._sigmethod, self._consumer, None)
            resp = urlopen(Request(url, headers=request.to_header()))
            return oauth.OAuthToken.from_string(resp.read())
        except Exception, e:
            raise TweepError(e)

    def set_request_token(self, key, secret):
        self.request_token = oauth.OAuthToken(key, secret)

    def set_access_token(self, key, secret):
        self.access_token = oauth.OAuthToken(key, secret)

    def get_authorization_url(self, signin_with_twitter=False):
        """Get the authorization URL to redirect the user"""
        try:
            # get the request token
            self.request_token = self._get_request_token()

            # build auth request and return as url
            if signin_with_twitter:
                url = self._get_oauth_url('authenticate')
            else:
                url = self._get_oauth_url('authorize')
            request = oauth.OAuthRequest.from_token_and_callback(
                token=self.request_token, http_url=url
            )

            return request.to_url()
        except Exception, e:
            raise TweepError(e)

    def get_access_token(self, verifier=None):
        """
        After user has authorized the request token, get access token
        with user supplied verifier.
        """
        try:
            url = self._get_oauth_url('access_token')

            # build request
            request = oauth.OAuthRequest.from_consumer_and_token(
                self._consumer,
                token=self.request_token, http_url=url,
                verifier=str(verifier)
            )
            request.sign_request(self._sigmethod, self._consumer, self.request_token)

            # send request
            resp = urlopen(Request(url, headers=request.to_header()))
            self.access_token = oauth.OAuthToken.from_string(resp.read())
            return self.access_token
        except Exception, e:
            raise TweepError(e)

    def get_xauth_access_token(self, username, password):
        """
        Get an access token from an username and password combination.
        In order to get this working you need to create an app at
        http://twitter.com/apps, after that send a mail to api@twitter.com
        and request activation of xAuth for it.
        """
        try:
            url = self._get_oauth_url('access_token', secure=True) # must use HTTPS
            request = oauth.OAuthRequest.from_consumer_and_token(
                oauth_consumer=self._consumer,
                http_method='POST', http_url=url,
                parameters = {
                    'x_auth_mode': 'client_auth',
                    'x_auth_username': username,
                    'x_auth_password': password
                }
            )
            request.sign_request(self._sigmethod, self._consumer, None)

            resp = urlopen(Request(url, data=request.to_postdata()))
            self.access_token = oauth.OAuthToken.from_string(resp.read())
            return self.access_token
        except Exception, e:
            raise TweepError(e)

    def get_username(self):
        if self.username is None:
            api = API(self)
            user = api.verify_credentials()
            if user:
                self.username = user.screen_name
            else:
                raise TweepError("Unable to get username, invalid oauth token!")
        return self.username


########NEW FILE########
__FILENAME__ = binder
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import httplib
import urllib
import time
import re
from StringIO import StringIO
import gzip

from tweepy.error import TweepError
from tweepy.utils import convert_to_utf8_str
from tweepy.models import Model

re_path_template = re.compile('{\w+}')


def bind_api(**config):

    class APIMethod(object):

        path = config['path']
        payload_type = config.get('payload_type', None)
        payload_list = config.get('payload_list', False)
        allowed_param = config.get('allowed_param', [])
        method = config.get('method', 'GET')
        require_auth = config.get('require_auth', False)
        search_api = config.get('search_api', False)
        use_cache = config.get('use_cache', True)

        def __init__(self, api, args, kargs):
            # If authentication is required and no credentials
            # are provided, throw an error.
            if self.require_auth and not api.auth:
                raise TweepError('Authentication required!')

            self.api = api
            self.post_data = kargs.pop('post_data', None)
            self.retry_count = kargs.pop('retry_count', api.retry_count)
            self.retry_delay = kargs.pop('retry_delay', api.retry_delay)
            self.retry_errors = kargs.pop('retry_errors', api.retry_errors)
            self.headers = kargs.pop('headers', {})
            self.build_parameters(args, kargs)

            # Pick correct URL root to use
            if self.search_api:
                self.api_root = api.search_root
            else:
                self.api_root = api.api_root

            # Perform any path variable substitution
            self.build_path()

            if api.secure:
                self.scheme = 'https://'
            else:
                self.scheme = 'http://'

            if self.search_api:
                self.host = api.search_host
            else:
                self.host = api.host

            # Manually set Host header to fix an issue in python 2.5
            # or older where Host is set including the 443 port.
            # This causes Twitter to issue 301 redirect.
            # See Issue https://github.com/tweepy/tweepy/issues/12
            self.headers['Host'] = self.host

        def build_parameters(self, args, kargs):
            self.parameters = {}
            for idx, arg in enumerate(args):
                if arg is None:
                    continue

                try:
                    self.parameters[self.allowed_param[idx]] = convert_to_utf8_str(arg)
                except IndexError:
                    raise TweepError('Too many parameters supplied!')

            for k, arg in kargs.items():
                if arg is None:
                    continue
                if k in self.parameters:
                    raise TweepError('Multiple values for parameter %s supplied!' % k)

                self.parameters[k] = convert_to_utf8_str(arg)

        def build_path(self):
            for variable in re_path_template.findall(self.path):
                name = variable.strip('{}')

                if name == 'user' and 'user' not in self.parameters and self.api.auth:
                    # No 'user' parameter provided, fetch it from Auth instead.
                    value = self.api.auth.get_username()
                else:
                    try:
                        value = urllib.quote(self.parameters[name])
                    except KeyError:
                        raise TweepError('No parameter value found for path variable: %s' % name)
                    del self.parameters[name]

                self.path = self.path.replace(variable, value)

        def execute(self):
            # Build the request URL
            url = self.api_root + self.path
            if len(self.parameters):
                url = '%s?%s' % (url, urllib.urlencode(self.parameters))

            # Query the cache if one is available
            # and this request uses a GET method.
            if self.use_cache and self.api.cache and self.method == 'GET':
                cache_result = self.api.cache.get(url)
                # if cache result found and not expired, return it
                if cache_result:
                    # must restore api reference
                    if isinstance(cache_result, list):
                        for result in cache_result:
                            if isinstance(result, Model):
                                result._api = self.api
                    else:
                        if isinstance(cache_result, Model):
                            cache_result._api = self.api
                    return cache_result

            # Continue attempting request until successful
            # or maximum number of retries is reached.
            retries_performed = 0
            while retries_performed < self.retry_count + 1:
                # Open connection
                if self.api.secure:
                    conn = httplib.HTTPSConnection(self.host, timeout=self.api.timeout)
                else:
                    conn = httplib.HTTPConnection(self.host, timeout=self.api.timeout)

                # Apply authentication
                if self.api.auth:
                    self.api.auth.apply_auth(
                            self.scheme + self.host + url,
                            self.method, self.headers, self.parameters
                    )

                # Request compression if configured
                if self.api.compression:
                    self.headers['Accept-encoding'] = 'gzip'

                # Execute request
                try:
                    conn.request(self.method, url, headers=self.headers, body=self.post_data)
                    resp = conn.getresponse()
                except Exception, e:
                    raise TweepError('Failed to send request: %s' % e)

                # Exit request loop if non-retry error code
                if self.retry_errors:
                    if resp.status not in self.retry_errors: break
                else:
                    if resp.status == 200: break

                # Sleep before retrying request again
                time.sleep(self.retry_delay)
                retries_performed += 1

            # If an error was returned, throw an exception
            self.api.last_response = resp
            if resp.status != 200:
                try:
                    error_msg = self.api.parser.parse_error(resp.read())
                except Exception:
                    error_msg = "Twitter error response: status code = %s" % resp.status
                raise TweepError(error_msg, resp)

            # Parse the response payload
            body = resp.read()
            if resp.getheader('Content-Encoding', '') == 'gzip':
                try:
                    zipper = gzip.GzipFile(fileobj=StringIO(body))
                    body = zipper.read()
                except Exception, e:
                    raise TweepError('Failed to decompress data: %s' % e)
            result = self.api.parser.parse(self, body)

            conn.close()

            # Store result into cache if one is available.
            if self.use_cache and self.api.cache and self.method == 'GET' and result:
                self.api.cache.store(url, result)

            return result


    def _call(api, *args, **kargs):

        method = APIMethod(api, args, kargs)
        return method.execute()


    # Set pagination mode
    if 'cursor' in APIMethod.allowed_param:
        _call.pagination_mode = 'cursor'
    elif 'max_id' in APIMethod.allowed_param and \
         'since_id' in APIMethod.allowed_param:
        _call.pagination_mode = 'id'
    elif 'page' in APIMethod.allowed_param:
        _call.pagination_mode = 'page'

    return _call


########NEW FILE########
__FILENAME__ = cache
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import time
import datetime
import threading
import os

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import hashlib
except ImportError:
    # python 2.4
    import md5 as hashlib

try:
    import fcntl
except ImportError:
    # Probably on a windows system
    # TODO: use win32file
    pass


class Cache(object):
    """Cache interface"""

    def __init__(self, timeout=60):
        """Initialize the cache
            timeout: number of seconds to keep a cached entry
        """
        self.timeout = timeout

    def store(self, key, value):
        """Add new record to cache
            key: entry key
            value: data of entry
        """
        raise NotImplementedError

    def get(self, key, timeout=None):
        """Get cached entry if exists and not expired
            key: which entry to get
            timeout: override timeout with this value [optional]
        """
        raise NotImplementedError

    def count(self):
        """Get count of entries currently stored in cache"""
        raise NotImplementedError

    def cleanup(self):
        """Delete any expired entries in cache."""
        raise NotImplementedError

    def flush(self):
        """Delete all cached entries"""
        raise NotImplementedError


class MemoryCache(Cache):
    """In-memory cache"""

    def __init__(self, timeout=60):
        Cache.__init__(self, timeout)
        self._entries = {}
        self.lock = threading.Lock()

    def __getstate__(self):
        # pickle
        return {'entries': self._entries, 'timeout': self.timeout}

    def __setstate__(self, state):
        # unpickle
        self.lock = threading.Lock()
        self._entries = state['entries']
        self.timeout = state['timeout']

    def _is_expired(self, entry, timeout):
        return timeout > 0 and (time.time() - entry[0]) >= timeout

    def store(self, key, value):
        self.lock.acquire()
        self._entries[key] = (time.time(), value)
        self.lock.release()

    def get(self, key, timeout=None):
        self.lock.acquire()
        try:
            # check to see if we have this key
            entry = self._entries.get(key)
            if not entry:
                # no hit, return nothing
                return None

            # use provided timeout in arguments if provided
            # otherwise use the one provided during init.
            if timeout is None:
                timeout = self.timeout

            # make sure entry is not expired
            if self._is_expired(entry, timeout):
                # entry expired, delete and return nothing
                del self._entries[key]
                return None

            # entry found and not expired, return it
            return entry[1]
        finally:
            self.lock.release()

    def count(self):
        return len(self._entries)

    def cleanup(self):
        self.lock.acquire()
        try:
            for k, v in self._entries.items():
                if self._is_expired(v, self.timeout):
                    del self._entries[k]
        finally:
            self.lock.release()

    def flush(self):
        self.lock.acquire()
        self._entries.clear()
        self.lock.release()


class FileCache(Cache):
    """File-based cache"""

    # locks used to make cache thread-safe
    cache_locks = {}

    def __init__(self, cache_dir, timeout=60):
        Cache.__init__(self, timeout)
        if os.path.exists(cache_dir) is False:
            os.mkdir(cache_dir)
        self.cache_dir = cache_dir
        if cache_dir in FileCache.cache_locks:
            self.lock = FileCache.cache_locks[cache_dir]
        else:
            self.lock = threading.Lock()
            FileCache.cache_locks[cache_dir] = self.lock

        if os.name == 'posix':
            self._lock_file = self._lock_file_posix
            self._unlock_file = self._unlock_file_posix
        elif os.name == 'nt':
            self._lock_file = self._lock_file_win32
            self._unlock_file = self._unlock_file_win32
        else:
            print 'Warning! FileCache locking not supported on this system!'
            self._lock_file = self._lock_file_dummy
            self._unlock_file = self._unlock_file_dummy

    def _get_path(self, key):
        md5 = hashlib.md5()
        md5.update(key)
        return os.path.join(self.cache_dir, md5.hexdigest())

    def _lock_file_dummy(self, path, exclusive=True):
        return None

    def _unlock_file_dummy(self, lock):
        return

    def _lock_file_posix(self, path, exclusive=True):
        lock_path = path + '.lock'
        if exclusive is True:
            f_lock = open(lock_path, 'w')
            fcntl.lockf(f_lock, fcntl.LOCK_EX)
        else:
            f_lock = open(lock_path, 'r')
            fcntl.lockf(f_lock, fcntl.LOCK_SH)
        if os.path.exists(lock_path) is False:
            f_lock.close()
            return None
        return f_lock

    def _unlock_file_posix(self, lock):
        lock.close()

    def _lock_file_win32(self, path, exclusive=True):
        # TODO: implement
        return None

    def _unlock_file_win32(self, lock):
        # TODO: implement
        return

    def _delete_file(self, path):
        os.remove(path)
        if os.path.exists(path + '.lock'):
            os.remove(path + '.lock')

    def store(self, key, value):
        path = self._get_path(key)
        self.lock.acquire()
        try:
            # acquire lock and open file
            f_lock = self._lock_file(path)
            datafile = open(path, 'wb')

            # write data
            pickle.dump((time.time(), value), datafile)

            # close and unlock file
            datafile.close()
            self._unlock_file(f_lock)
        finally:
            self.lock.release()

    def get(self, key, timeout=None):
        return self._get(self._get_path(key), timeout)

    def _get(self, path, timeout):
        if os.path.exists(path) is False:
            # no record
            return None
        self.lock.acquire()
        try:
            # acquire lock and open
            f_lock = self._lock_file(path, False)
            datafile = open(path, 'rb')

            # read pickled object
            created_time, value = pickle.load(datafile)
            datafile.close()

            # check if value is expired
            if timeout is None:
                timeout = self.timeout
            if timeout > 0 and (time.time() - created_time) >= timeout:
                # expired! delete from cache
                value = None
                self._delete_file(path)

            # unlock and return result
            self._unlock_file(f_lock)
            return value
        finally:
            self.lock.release()

    def count(self):
        c = 0
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            c += 1
        return c

    def cleanup(self):
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            self._get(os.path.join(self.cache_dir, entry), None)

    def flush(self):
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            self._delete_file(os.path.join(self.cache_dir, entry))

class MemCacheCache(Cache):
    """Cache interface"""

    def __init__(self, client, timeout=60):
        """Initialize the cache
            client: The memcache client
            timeout: number of seconds to keep a cached entry
        """
        self.client = client
        self.timeout = timeout

    def store(self, key, value):
        """Add new record to cache
            key: entry key
            value: data of entry
        """
        self.client.set(key, value, time=self.timeout)

    def get(self, key, timeout=None):
        """Get cached entry if exists and not expired
            key: which entry to get
            timeout: override timeout with this value [optional]. DOES NOT WORK HERE
        """
        return self.client.get(key)

    def count(self):
        """Get count of entries currently stored in cache. RETURN 0"""
        raise NotImplementedError

    def cleanup(self):
        """Delete any expired entries in cache. NO-OP"""
        raise NotImplementedError

    def flush(self):
        """Delete all cached entries. NO-OP"""
        raise NotImplementedError

class RedisCache(Cache):
    '''Cache running in a redis server'''

    def __init__(self, client, timeout=60, keys_container = 'tweepy:keys', pre_identifier = 'tweepy:'):
        Cache.__init__(self, timeout)
        self.client = client
        self.keys_container = keys_container
        self.pre_identifier = pre_identifier

    def _is_expired(self, entry, timeout):
        # Returns true if the entry has expired
        return timeout > 0 and (time.time() - entry[0]) >= timeout

    def store(self, key, value):
        '''Store the key, value pair in our redis server'''
        # Prepend tweepy to our key, this makes it easier to identify tweepy keys in our redis server
        key = self.pre_identifier + key
        # Get a pipe (to execute several redis commands in one step)
        pipe = self.client.pipeline()
        # Set our values in a redis hash (similar to python dict)
        pipe.set(key, pickle.dumps((time.time(), value)))
        # Set the expiration
        pipe.expire(key, self.timeout)
        # Add the key to a set containing all the keys
        pipe.sadd(self.keys_container, key)
        # Execute the instructions in the redis server
        pipe.execute()

    def get(self, key, timeout=None):
        '''Given a key, returns an element from the redis table'''
        key = self.pre_identifier + key
        # Check to see if we have this key
        unpickled_entry = self.client.get(key)
        if not unpickled_entry:
            # No hit, return nothing
            return None

        entry = pickle.loads(unpickled_entry)
        # Use provided timeout in arguments if provided
        # otherwise use the one provided during init.
        if timeout is None:
            timeout = self.timeout

        # Make sure entry is not expired
        if self._is_expired(entry, timeout):
            # entry expired, delete and return nothing
            self.delete_entry(key)
            return None
        # entry found and not expired, return it
        return entry[1]

    def count(self):
        '''Note: This is not very efficient, since it retreives all the keys from the redis
        server to know how many keys we have'''
        return len(self.client.smembers(self.keys_container))

    def delete_entry(self, key):
        '''Delete an object from the redis table'''
        pipe = self.client.pipeline()
        pipe.srem(self.keys_container, key)
        pipe.delete(key)
        pipe.execute()

    def cleanup(self):
        '''Cleanup all the expired keys'''
        keys = self.client.smembers(self.keys_container)
        for key in keys:
            entry = self.client.get(key)
            if entry:
                entry = pickle.loads(entry)
                if self._is_expired(entry, self.timeout):
                    self.delete_entry(key)

    def flush(self):
        '''Delete all entries from the cache'''
        keys = self.client.smembers(self.keys_container)
        for key in keys:
            self.delete_entry(key)


class MongodbCache(Cache):
    """A simple pickle-based MongoDB cache sytem."""

    def __init__(self, db, timeout=3600, collection='tweepy_cache'):
        """Should receive a "database" cursor from pymongo."""
        Cache.__init__(self, timeout)
        self.timeout = timeout
        self.col = db[collection]
        self.col.create_index('created', expireAfterSeconds=timeout)

    def store(self, key, value):
        from bson.binary import Binary

        now = datetime.datetime.utcnow()
        blob = Binary(pickle.dumps(value))

        self.col.insert({'created': now, '_id': key, 'value': blob})

    def get(self, key, timeout=None):
        if timeout:
            raise NotImplementedError
        obj = self.col.find_one({'_id': key})
        if obj:
            return pickle.loads(obj['value'])

    def count(self):
        return self.col.find({}).count()

    def delete_entry(self, key):
        return self.col.remove({'_id': key})

    def cleanup(self):
        """MongoDB will automatically clear expired keys."""
        pass

    def flush(self):
        self.col.drop()
        self.col.create_index('created', expireAfterSeconds=self.timeout)

########NEW FILE########
__FILENAME__ = cursor
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from tweepy.error import TweepError

class Cursor(object):
    """Pagination helper class"""

    def __init__(self, method, *args, **kargs):
        if hasattr(method, 'pagination_mode'):
            if method.pagination_mode == 'cursor':
                self.iterator = CursorIterator(method, args, kargs)
            elif method.pagination_mode == 'id':
                self.iterator = IdIterator(method, args, kargs)
            elif method.pagination_mode == 'page':
                self.iterator = PageIterator(method, args, kargs)
            else:
                raise TweepError('Invalid pagination mode.')
        else:
            raise TweepError('This method does not perform pagination')

    def pages(self, limit=0):
        """Return iterator for pages"""
        if limit > 0:
            self.iterator.limit = limit
        return self.iterator

    def items(self, limit=0):
        """Return iterator for items in each page"""
        i = ItemIterator(self.iterator)
        i.limit = limit
        return i

class BaseIterator(object):

    def __init__(self, method, args, kargs):
        self.method = method
        self.args = args
        self.kargs = kargs
        self.limit = 0

    def next(self):
        raise NotImplementedError

    def prev(self):
        raise NotImplementedError

    def __iter__(self):
        return self

class CursorIterator(BaseIterator):

    def __init__(self, method, args, kargs):
        BaseIterator.__init__(self, method, args, kargs)
        self.next_cursor = -1
        self.prev_cursor = 0
        self.count = 0

    def next(self):
        if self.next_cursor == 0 or (self.limit and self.count == self.limit):
            raise StopIteration
        data, cursors = self.method(
                cursor=self.next_cursor, *self.args, **self.kargs
        )
        self.prev_cursor, self.next_cursor = cursors
        if len(data) == 0:
            raise StopIteration
        self.count += 1
        return data

    def prev(self):
        if self.prev_cursor == 0:
            raise TweepError('Can not page back more, at first page')
        data, self.next_cursor, self.prev_cursor = self.method(
                cursor=self.prev_cursor, *self.args, **self.kargs
        )
        self.count -= 1
        return data

class IdIterator(BaseIterator):

    def __init__(self, method, args, kargs):
        BaseIterator.__init__(self, method, args, kargs)
        self.max_id = kargs.get('max_id')
        self.since_id = kargs.get('since_id')
        self.count = 0

    def next(self):
        """Fetch a set of items with IDs less than current set."""
        if self.limit and self.limit == self.count:
            raise StopIteration

        # max_id is inclusive so decrement by one
        # to avoid requesting duplicate items.
        max_id = self.since_id - 1 if self.max_id else None
        data = self.method(max_id = max_id, *self.args, **self.kargs)
        if len(data) == 0:
            raise StopIteration
        self.max_id = data.max_id
        self.since_id = data.since_id
        self.count += 1
        return data

    def prev(self):
        """Fetch a set of items with IDs greater than current set."""
        if self.limit and self.limit == self.count:
            raise StopIteration

        since_id = self.max_id
        data = self.method(since_id = since_id, *self.args, **self.kargs)
        if len(data) == 0:
            raise StopIteration
        self.max_id = data.max_id
        self.since_id = data.since_id
        self.count += 1
        return data

class PageIterator(BaseIterator):

    def __init__(self, method, args, kargs):
        BaseIterator.__init__(self, method, args, kargs)
        self.current_page = 0

    def next(self):
        self.current_page += 1
        items = self.method(page=self.current_page, *self.args, **self.kargs)
        if len(items) == 0 or (self.limit > 0 and self.current_page > self.limit):
            raise StopIteration
        return items

    def prev(self):
        if (self.current_page == 1):
            raise TweepError('Can not page back more, at first page')
        self.current_page -= 1
        return self.method(page=self.current_page, *self.args, **self.kargs)

class ItemIterator(BaseIterator):

    def __init__(self, page_iterator):
        self.page_iterator = page_iterator
        self.limit = 0
        self.current_page = None
        self.page_index = -1
        self.count = 0

    def next(self):
        if self.limit > 0 and self.count == self.limit:
            raise StopIteration
        if self.current_page is None or self.page_index == len(self.current_page) - 1:
            # Reached end of current page, get the next page...
            self.current_page = self.page_iterator.next()
            self.page_index = -1
        self.page_index += 1
        self.count += 1
        return self.current_page[self.page_index]

    def prev(self):
        if self.current_page is None:
            raise TweepError('Can not go back more, at first page')
        if self.page_index == 0:
            # At the beginning of the current page, move to next...
            self.current_page = self.page_iterator.prev()
            self.page_index = len(self.current_page)
            if self.page_index == 0:
                raise TweepError('No more items')
        self.page_index -= 1
        self.count -= 1
        return self.current_page[self.page_index]


########NEW FILE########
__FILENAME__ = error
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

class TweepError(Exception):
    """Tweepy exception"""

    def __init__(self, reason, response=None):
        self.reason = unicode(reason)
        self.response = response
        Exception.__init__(self, reason)

    def __str__(self):
        return self.reason


########NEW FILE########
__FILENAME__ = models
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from tweepy.error import TweepError
from tweepy.utils import parse_datetime, parse_html_value, parse_a_href, \
        parse_search_datetime, unescape_html


class ResultSet(list):
    """A list like object that holds results from a Twitter API query."""
    def __init__(self, max_id=None, since_id=None):
        super(ResultSet, self).__init__()
        self._max_id = max_id
        self._since_id = since_id

    @property
    def max_id(self):
        if self._max_id:
            return self._max_id
        ids = self.ids()
        return max(ids) if ids else None

    @property
    def since_id(self):
        if self._since_id:
            return self._since_id
        ids = self.ids()
        return min(ids) if ids else None

    def ids(self):
        return [item.id for item in self if hasattr(item, 'id')]

class Model(object):

    def __init__(self, api=None):
        self._api = api

    def __getstate__(self):
        # pickle
        pickle = dict(self.__dict__)
        try:
            del pickle['_api']  # do not pickle the API reference
        except KeyError:
            pass
        return pickle

    @classmethod
    def parse(cls, api, json):
        """Parse a JSON object into a model instance."""
        raise NotImplementedError

    @classmethod
    def parse_list(cls, api, json_list):
        """Parse a list of JSON objects into a result set of model instances."""
        results = ResultSet()
        for obj in json_list:
            if obj:
                results.append(cls.parse(api, obj))
        return results


class Status(Model):

    @classmethod
    def parse(cls, api, json):
        status = cls(api)
        for k, v in json.items():
            if k == 'user':
                user_model = getattr(api.parser.model_factory, 'user')
                user = user_model.parse(api, v)
                setattr(status, 'author', user)
                setattr(status, 'user', user)  # DEPRECIATED
            elif k == 'created_at':
                setattr(status, k, parse_datetime(v))
            elif k == 'source':
                if '<' in v:
                    setattr(status, k, parse_html_value(v))
                    setattr(status, 'source_url', parse_a_href(v))
                else:
                    setattr(status, k, v)
                    setattr(status, 'source_url', None)
            elif k == 'retweeted_status':
                setattr(status, k, Status.parse(api, v))
            elif k == 'place':
                if v is not None:
                    setattr(status, k, Place.parse(api, v))
                else:
                    setattr(status, k, None)
            else:
                setattr(status, k, v)
        return status

    def destroy(self):
        return self._api.destroy_status(self.id)

    def retweet(self):
        return self._api.retweet(self.id)

    def retweets(self):
        return self._api.retweets(self.id)

    def favorite(self):
        return self._api.create_favorite(self.id)


class User(Model):

    @classmethod
    def parse(cls, api, json):
        user = cls(api)
        for k, v in json.items():
            if k == 'created_at':
                setattr(user, k, parse_datetime(v))
            elif k == 'status':
                setattr(user, k, Status.parse(api, v))
            elif k == 'following':
                # twitter sets this to null if it is false
                if v is True:
                    setattr(user, k, True)
                else:
                    setattr(user, k, False)
            else:
                setattr(user, k, v)
        return user

    @classmethod
    def parse_list(cls, api, json_list):
        if isinstance(json_list, list):
            item_list = json_list
        else:
            item_list = json_list['users']

        results = ResultSet()
        for obj in item_list:
            results.append(cls.parse(api, obj))
        return results

    def timeline(self, **kargs):
        return self._api.user_timeline(user_id=self.id, **kargs)

    def friends(self, **kargs):
        return self._api.friends(user_id=self.id, **kargs)

    def followers(self, **kargs):
        return self._api.followers(user_id=self.id, **kargs)

    def follow(self):
        self._api.create_friendship(user_id=self.id)
        self.following = True

    def unfollow(self):
        self._api.destroy_friendship(user_id=self.id)
        self.following = False

    def lists_memberships(self, *args, **kargs):
        return self._api.lists_memberships(user=self.screen_name, *args, **kargs)

    def lists_subscriptions(self, *args, **kargs):
        return self._api.lists_subscriptions(user=self.screen_name, *args, **kargs)

    def lists(self, *args, **kargs):
        return self._api.lists(user=self.screen_name, *args, **kargs)

    def followers_ids(self, *args, **kargs):
        return self._api.followers_ids(user_id=self.id, *args, **kargs)


class DirectMessage(Model):

    @classmethod
    def parse(cls, api, json):
        dm = cls(api)
        for k, v in json.items():
            if k == 'sender' or k == 'recipient':
                setattr(dm, k, User.parse(api, v))
            elif k == 'created_at':
                setattr(dm, k, parse_datetime(v))
            else:
                setattr(dm, k, v)
        return dm

    def destroy(self):
        return self._api.destroy_direct_message(self.id)


class Friendship(Model):

    @classmethod
    def parse(cls, api, json):
        relationship = json['relationship']

        # parse source
        source = cls(api)
        for k, v in relationship['source'].items():
            setattr(source, k, v)

        # parse target
        target = cls(api)
        for k, v in relationship['target'].items():
            setattr(target, k, v)

        return source, target


class Category(Model):

    @classmethod
    def parse(cls, api, json):
        category = cls(api)
        for k, v in json.items():
            setattr(category, k, v)
        return category


class SavedSearch(Model):

    @classmethod
    def parse(cls, api, json):
        ss = cls(api)
        for k, v in json.items():
            if k == 'created_at':
                setattr(ss, k, parse_datetime(v))
            else:
                setattr(ss, k, v)
        return ss

    def destroy(self):
        return self._api.destroy_saved_search(self.id)


class SearchResults(ResultSet):

    @classmethod
    def parse(cls, api, json):
        metadata = json['search_metadata']
        results = SearchResults(metadata.get('max_id'), metadata.get('since_id'))
        results.refresh_url = metadata.get('refresh_url')
        results.completed_in = metadata.get('completed_in')
        results.query = metadata.get('query')

        for status in json['statuses']:
            results.append(Status.parse(api, status))
        return results


class List(Model):

    @classmethod
    def parse(cls, api, json):
        lst = List(api)
        for k,v in json.items():
            if k == 'user':
                setattr(lst, k, User.parse(api, v))
            elif k == 'created_at':
                setattr(lst, k, parse_datetime(v))
            else:
                setattr(lst, k, v)
        return lst

    @classmethod
    def parse_list(cls, api, json_list, result_set=None):
        results = ResultSet()
        if isinstance(json_list, dict):
            json_list = json_list['lists']
        for obj in json_list:
            results.append(cls.parse(api, obj))
        return results

    def update(self, **kargs):
        return self._api.update_list(self.slug, **kargs)

    def destroy(self):
        return self._api.destroy_list(self.slug)

    def timeline(self, **kargs):
        return self._api.list_timeline(self.user.screen_name, self.slug, **kargs)

    def add_member(self, id):
        return self._api.add_list_member(self.slug, id)

    def remove_member(self, id):
        return self._api.remove_list_member(self.slug, id)

    def members(self, **kargs):
        return self._api.list_members(self.user.screen_name, self.slug, **kargs)

    def is_member(self, id):
        return self._api.is_list_member(self.user.screen_name, self.slug, id)

    def subscribe(self):
        return self._api.subscribe_list(self.user.screen_name, self.slug)

    def unsubscribe(self):
        return self._api.unsubscribe_list(self.user.screen_name, self.slug)

    def subscribers(self, **kargs):
        return self._api.list_subscribers(self.user.screen_name, self.slug, **kargs)

    def is_subscribed(self, id):
        return self._api.is_subscribed_list(self.user.screen_name, self.slug, id)

class Relation(Model):
    @classmethod
    def parse(cls, api, json):
        result = cls(api)
        for k,v in json.items():
            if k == 'value' and json['kind'] in ['Tweet', 'LookedupStatus']:
                setattr(result, k, Status.parse(api, v))
            elif k == 'results':
                setattr(result, k, Relation.parse_list(api, v))
            else:
                setattr(result, k, v)
        return result

class Relationship(Model):
    @classmethod
    def parse(cls, api, json):
        result = cls(api)
        for k,v in json.items():
            if k == 'connections':
                setattr(result, 'is_following', 'following' in v)
                setattr(result, 'is_followed_by', 'followed_by' in v)
            else:
                setattr(result, k, v)
        return result

class JSONModel(Model):

    @classmethod
    def parse(cls, api, json):
        return json


class IDModel(Model):

    @classmethod
    def parse(cls, api, json):
        if isinstance(json, list):
            return json
        else:
            return json['ids']


class BoundingBox(Model):

    @classmethod
    def parse(cls, api, json):
        result = cls(api)
        if json is not None:
            for k, v in json.items():
                setattr(result, k, v)
        return result

    def origin(self):
        """
        Return longitude, latitude of southwest (bottom, left) corner of
        bounding box, as a tuple.

        This assumes that bounding box is always a rectangle, which
        appears to be the case at present.
        """
        return tuple(self.coordinates[0][0])

    def corner(self):
        """
        Return longitude, latitude of northeast (top, right) corner of
        bounding box, as a tuple.

        This assumes that bounding box is always a rectangle, which
        appears to be the case at present.
        """
        return tuple(self.coordinates[0][2])


class Place(Model):

    @classmethod
    def parse(cls, api, json):
        place = cls(api)
        for k, v in json.items():
            if k == 'bounding_box':
                # bounding_box value may be null (None.)
                # Example: "United States" (id=96683cc9126741d1)
                if v is not None:
                    t = BoundingBox.parse(api, v)
                else:
                    t = v
                setattr(place, k, t)
            elif k == 'contained_within':
                # contained_within is a list of Places.
                setattr(place, k, Place.parse_list(api, v))
            else:
                setattr(place, k, v)
        return place

    @classmethod
    def parse_list(cls, api, json_list):
        if isinstance(json_list, list):
            item_list = json_list
        else:
            item_list = json_list['result']['places']

        results = ResultSet()
        for obj in item_list:
            results.append(cls.parse(api, obj))
        return results

class ModelFactory(object):
    """
    Used by parsers for creating instances
    of models. You may subclass this factory
    to add your own extended models.
    """

    status = Status
    user = User
    direct_message = DirectMessage
    friendship = Friendship
    saved_search = SavedSearch
    search_results = SearchResults
    category = Category
    list = List
    relation = Relation
    relationship = Relationship

    json = JSONModel
    ids = IDModel
    place = Place
    bounding_box = BoundingBox


########NEW FILE########
__FILENAME__ = oauth
"""
The MIT License

Copyright (c) 2007 Leah Culver

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import cgi
import urllib
import time
import random
import urlparse
import hmac
import binascii


VERSION = '1.0' # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class OAuthError(RuntimeError):
    """Generic exception class."""
    def __init__(self, message='OAuth error occured.'):
        self.message = message

def build_authenticate_header(realm=''):
    """Optional WWW-Authenticate header (401 error)"""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

def escape(s):
    """Escape a URL including any /."""
    return urllib.quote(s, safe='~')

def _utf8_str(s):
    """Convert unicode to utf-8."""
    if isinstance(s, unicode):
        return s.encode("utf-8")
    else:
        return str(s)

def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())

def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])

def generate_verifier(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class OAuthConsumer(object):
    """Consumer of OAuth authentication.

    OAuthConsumer is a data type that represents the identity of the Consumer
    via its shared secret with the Service Provider.

    """
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret


class OAuthToken(object):
    """OAuthToken is a data type that represents an End User via either an access
    or request token.
    
    key -- the token
    secret -- the token secret

    """
    key = None
    secret = None
    callback = None
    callback_confirmed = None
    verifier = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

    def set_callback(self, callback):
        self.callback = callback
        self.callback_confirmed = 'true'

    def set_verifier(self, verifier=None):
        if verifier is not None:
            self.verifier = verifier
        else:
            self.verifier = generate_verifier()

    def get_callback_url(self):
        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback

    def to_string(self):
        data = {
            'oauth_token': self.key,
            'oauth_token_secret': self.secret,
        }
        if self.callback_confirmed is not None:
            data['oauth_callback_confirmed'] = self.callback_confirmed
        return urllib.urlencode(data)
 
    def from_string(s):
        """ Returns a token from something like:
        oauth_token_secret=xxx&oauth_token=xxx
        """
        params = cgi.parse_qs(s, keep_blank_values=False)
        key = params['oauth_token'][0]
        secret = params['oauth_token_secret'][0]
        token = OAuthToken(key, secret)
        try:
            token.callback_confirmed = params['oauth_callback_confirmed'][0]
        except KeyError:
            pass # 1.0, no callback confirmed.
        return token
    from_string = staticmethod(from_string)

    def __str__(self):
        return self.to_string()


class OAuthRequest(object):
    """OAuthRequest represents the request and can be serialized.

    OAuth parameters:
        - oauth_consumer_key 
        - oauth_token
        - oauth_signature_method
        - oauth_signature 
        - oauth_timestamp 
        - oauth_nonce
        - oauth_version
        - oauth_verifier
        ... any additional parameters, as defined by the Service Provider.
    """
    parameters = None # OAuth parameters.
    http_method = HTTP_METHOD
    http_url = None
    version = VERSION

    def __init__(self, http_method=HTTP_METHOD, http_url=None, parameters=None):
        self.http_method = http_method
        self.http_url = http_url
        self.parameters = parameters or {}

    def set_parameter(self, parameter, value):
        self.parameters[parameter] = value

    def get_parameter(self, parameter):
        try:
            return self.parameters[parameter]
        except:
            raise OAuthError('Parameter not found: %s' % parameter)

    def _get_timestamp_nonce(self):
        return self.get_parameter('oauth_timestamp'), self.get_parameter(
            'oauth_nonce')

    def get_nonoauth_parameters(self):
        """Get any non-OAuth parameters."""
        parameters = {}
        for k, v in self.parameters.iteritems():
            # Ignore oauth parameters.
            if k.find('oauth_') < 0:
                parameters[k] = v
        return parameters

    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        auth_header = 'OAuth realm="%s"' % realm
        # Add the oauth parameters.
        if self.parameters:
            for k, v in self.parameters.iteritems():
                if k[:6] == 'oauth_':
                    auth_header += ', %s="%s"' % (k, escape(str(v)))
        return {'Authorization': auth_header}

    def to_postdata(self):
        """Serialize as post data for a POST request."""
        return '&'.join(['%s=%s' % (escape(str(k)), escape(str(v))) \
            for k, v in self.parameters.iteritems()])

    def to_url(self):
        """Serialize as a URL for a GET request."""
        return '%s?%s' % (self.get_normalized_http_url(), self.to_postdata())

    def get_normalized_parameters(self):
        """Return a string that contains the parameters that must be signed."""
        params = self.parameters
        try:
            # Exclude the signature if it exists.
            del params['oauth_signature']
        except:
            pass
        # Escape key values before sorting.
        key_values = [(escape(_utf8_str(k)), escape(_utf8_str(v))) \
            for k,v in params.items()]
        # Sort lexicographically, first after key, then after value.
        key_values.sort()
        # Combine key value pairs into a string.
        return '&'.join(['%s=%s' % (k, v) for k, v in key_values])

    def get_normalized_http_method(self):
        """Uppercases the http method."""
        return self.http_method.upper()

    def get_normalized_http_url(self):
        """Parses the URL and rebuilds it to be scheme://host/path."""
        parts = urlparse.urlparse(self.http_url)
        scheme, netloc, path = parts[:3]
        # Exclude default port numbers.
        if scheme == 'http' and netloc[-3:] == ':80':
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc[-4:] == ':443':
            netloc = netloc[:-4]
        return '%s://%s%s' % (scheme, netloc, path)

    def sign_request(self, signature_method, consumer, token):
        """Set the signature parameter to the result of build_signature."""
        # Set the signature method.
        self.set_parameter('oauth_signature_method',
            signature_method.get_name())
        # Set the signature.
        self.set_parameter('oauth_signature',
            self.build_signature(signature_method, consumer, token))

    def build_signature(self, signature_method, consumer, token):
        """Calls the build signature method within the signature method."""
        return signature_method.build_signature(self, consumer, token)

    def from_request(http_method, http_url, headers=None, parameters=None,
            query_string=None):
        """Combines multiple parameter sources."""
        if parameters is None:
            parameters = {}

        # Headers
        if headers and 'Authorization' in headers:
            auth_header = headers['Authorization']
            # Check that the authorization header is OAuth.
            if auth_header[:6] == 'OAuth ':
                auth_header = auth_header[6:]
                try:
                    # Get the parameters from the header.
                    header_params = OAuthRequest._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise OAuthError('Unable to parse OAuth parameters from '
                        'Authorization header.')

        # GET or POST query string.
        if query_string:
            query_params = OAuthRequest._split_url_string(query_string)
            parameters.update(query_params)

        # URL parameters.
        param_str = urlparse.urlparse(http_url)[4] # query
        url_params = OAuthRequest._split_url_string(param_str)
        parameters.update(url_params)

        if parameters:
            return OAuthRequest(http_method, http_url, parameters)

        return None
    from_request = staticmethod(from_request)

    def from_consumer_and_token(oauth_consumer, token=None,
            callback=None, verifier=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        defaults = {
            'oauth_consumer_key': oauth_consumer.key,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
            'oauth_version': OAuthRequest.version,
        }

        defaults.update(parameters)
        parameters = defaults

        if token:
            parameters['oauth_token'] = token.key
            if token.callback:
                parameters['oauth_callback'] = token.callback
            # 1.0a support for verifier.
            if verifier:
                parameters['oauth_verifier'] = verifier
        elif callback:
            # 1.0a support for callback in the request token request.
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_consumer_and_token = staticmethod(from_consumer_and_token)

    def from_token_and_callback(token, callback=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_token_and_callback = staticmethod(from_token_and_callback)

    def _split_header(header):
        """Turn Authorization: header into parameters."""
        params = {}
        parts = header.split(',')
        for param in parts:
            # Ignore realm parameter.
            if param.find('realm') > -1:
                continue
            # Remove whitespace.
            param = param.strip()
            # Split key-value.
            param_parts = param.split('=', 1)
            # Remove quotes and unescape the value.
            params[param_parts[0]] = urllib.unquote(param_parts[1].strip('\"'))
        return params
    _split_header = staticmethod(_split_header)

    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = cgi.parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters
    _split_url_string = staticmethod(_split_url_string)

class OAuthServer(object):
    """A worker to check the validity of a request against a data store."""
    timestamp_threshold = 300 # In seconds, five minutes.
    version = VERSION
    signature_methods = None
    data_store = None

    def __init__(self, data_store=None, signature_methods=None):
        self.data_store = data_store
        self.signature_methods = signature_methods or {}

    def set_data_store(self, data_store):
        self.data_store = data_store

    def get_data_store(self):
        return self.data_store

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.get_name()] = signature_method
        return self.signature_methods

    def fetch_request_token(self, oauth_request):
        """Processes a request_token request and returns the
        request token on success.
        """
        try:
            # Get the request token for authorization.
            token = self._get_token(oauth_request, 'request')
        except OAuthError:
            # No token required for the initial token request.
            version = self._get_version(oauth_request)
            consumer = self._get_consumer(oauth_request)
            try:
                callback = self.get_callback(oauth_request)
            except OAuthError:
                callback = None # 1.0, no callback specified.
            self._check_signature(oauth_request, consumer, None)
            # Fetch a new token.
            token = self.data_store.fetch_request_token(consumer, callback)
        return token

    def fetch_access_token(self, oauth_request):
        """Processes an access_token request and returns the
        access token on success.
        """
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        try:
            verifier = self._get_verifier(oauth_request)
        except OAuthError:
            verifier = None
        # Get the request token.
        token = self._get_token(oauth_request, 'request')
        self._check_signature(oauth_request, consumer, token)
        new_token = self.data_store.fetch_access_token(consumer, token, verifier)
        return new_token

    def verify_request(self, oauth_request):
        """Verifies an api call and checks all the parameters."""
        # -> consumer and token
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        # Get the access token.
        token = self._get_token(oauth_request, 'access')
        self._check_signature(oauth_request, consumer, token)
        parameters = oauth_request.get_nonoauth_parameters()
        return consumer, token, parameters

    def authorize_token(self, token, user):
        """Authorize a request token."""
        return self.data_store.authorize_request_token(token, user)

    def get_callback(self, oauth_request):
        """Get the callback URL."""
        return oauth_request.get_parameter('oauth_callback')
 
    def build_authenticate_header(self, realm=''):
        """Optional support for the authenticate header."""
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    def _get_version(self, oauth_request):
        """Verify the correct version request for this server."""
        try:
            version = oauth_request.get_parameter('oauth_version')
        except:
            version = VERSION
        if version and version != self.version:
            raise OAuthError('OAuth version %s not supported.' % str(version))
        return version

    def _get_signature_method(self, oauth_request):
        """Figure out the signature with some defaults."""
        try:
            signature_method = oauth_request.get_parameter(
                'oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD
        try:
            # Get the signature method object.
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise OAuthError('Signature method %s not supported try one of the '
                'following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_consumer(self, oauth_request):
        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        consumer = self.data_store.lookup_consumer(consumer_key)
        if not consumer:
            raise OAuthError('Invalid consumer.')
        return consumer

    def _get_token(self, oauth_request, token_type='access'):
        """Try to find the token for the provided request token key."""
        token_field = oauth_request.get_parameter('oauth_token')
        token = self.data_store.lookup_token(token_type, token_field)
        if not token:
            raise OAuthError('Invalid %s token: %s' % (token_type, token_field))
        return token
    
    def _get_verifier(self, oauth_request):
        return oauth_request.get_parameter('oauth_verifier')

    def _check_signature(self, oauth_request, consumer, token):
        timestamp, nonce = oauth_request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        self._check_nonce(consumer, token, nonce)
        signature_method = self._get_signature_method(oauth_request)
        try:
            signature = oauth_request.get_parameter('oauth_signature')
        except:
            raise OAuthError('Missing signature.')
        # Validate the signature.
        valid_sig = signature_method.check_signature(oauth_request, consumer,
            token, signature)
        if not valid_sig:
            key, base = signature_method.build_signature_base_string(
                oauth_request, consumer, token)
            raise OAuthError('Invalid signature. Expected signature base '
                'string: %s' % base)
        built = signature_method.build_signature(oauth_request, consumer, token)

    def _check_timestamp(self, timestamp):
        """Verify that timestamp is recentish."""
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = abs(now - timestamp)
        if lapsed > self.timestamp_threshold:
            raise OAuthError('Expired timestamp: given %d and now %s has a '
                'greater difference than threshold %d' %
                (timestamp, now, self.timestamp_threshold))

    def _check_nonce(self, consumer, token, nonce):
        """Verify that the nonce is uniqueish."""
        nonce = self.data_store.lookup_nonce(consumer, token, nonce)
        if nonce:
            raise OAuthError('Nonce already used: %s' % str(nonce))


class OAuthClient(object):
    """OAuthClient is a worker to attempt to execute a request."""
    consumer = None
    token = None

    def __init__(self, oauth_consumer, oauth_token):
        self.consumer = oauth_consumer
        self.token = oauth_token

    def get_consumer(self):
        return self.consumer

    def get_token(self):
        return self.token

    def fetch_request_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def access_resource(self, oauth_request):
        """-> Some protected resource."""
        raise NotImplementedError


class OAuthDataStore(object):
    """A database abstraction used to lookup consumers and tokens."""

    def lookup_consumer(self, key):
        """-> OAuthConsumer."""
        raise NotImplementedError

    def lookup_token(self, oauth_consumer, token_type, token_token):
        """-> OAuthToken."""
        raise NotImplementedError

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_request_token(self, oauth_consumer, oauth_callback):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_consumer, oauth_token, oauth_verifier):
        """-> OAuthToken."""
        raise NotImplementedError

    def authorize_request_token(self, oauth_token, user):
        """-> OAuthToken."""
        raise NotImplementedError


class OAuthSignatureMethod(object):
    """A strategy class that implements a signature method."""
    def get_name(self):
        """-> str."""
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, oauth_consumer, oauth_token):
        """-> str key, str raw."""
        raise NotImplementedError

    def build_signature(self, oauth_request, oauth_consumer, oauth_token):
        """-> str."""
        raise NotImplementedError

    def check_signature(self, oauth_request, consumer, token, signature):
        built = self.build_signature(oauth_request, consumer, token)
        return built == signature


class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):

    def get_name(self):
        return 'HMAC-SHA1'
        
    def build_signature_base_string(self, oauth_request, consumer, token):
        sig = (
            escape(oauth_request.get_normalized_http_method()),
            escape(oauth_request.get_normalized_http_url()),
            escape(oauth_request.get_normalized_parameters()),
        )

        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def build_signature(self, oauth_request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)

        # HMAC object.
        try:
            import hashlib # 2.5
            hashed = hmac.new(key, raw, hashlib.sha1)
        except:
            import sha # Deprecated
            hashed = hmac.new(key, raw, sha)

        # Calculate the digest base 64.
        return binascii.b2a_base64(hashed.digest())[:-1]


class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):

    def get_name(self):
        return 'PLAINTEXT'

    def build_signature_base_string(self, oauth_request, consumer, token):
        """Concatenates the consumer key and secret."""
        sig = '%s&' % escape(consumer.secret)
        if token:
            sig = sig + escape(token.secret)
        return sig, sig

    def build_signature(self, oauth_request, consumer, token):
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)
        return key
########NEW FILE########
__FILENAME__ = parsers
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from tweepy.models import ModelFactory
from tweepy.utils import import_simplejson
from tweepy.error import TweepError


class Parser(object):

    def parse(self, method, payload):
        """
        Parse the response payload and return the result.
        Returns a tuple that contains the result data and the cursors
        (or None if not present).
        """
        raise NotImplementedError

    def parse_error(self, payload):
        """
        Parse the error message from payload.
        If unable to parse the message, throw an exception
        and default error message will be used.
        """
        raise NotImplementedError


class RawParser(Parser):

    def __init__(self):
        pass

    def parse(self, method, payload):
        return payload

    def parse_error(self, payload):
        return payload


class JSONParser(Parser):

    payload_format = 'json'

    def __init__(self):
        self.json_lib = import_simplejson()

    def parse(self, method, payload):
        try:
            json = self.json_lib.loads(payload)
        except Exception, e:
            raise TweepError('Failed to parse JSON payload: %s' % e)

        needsCursors = method.parameters.has_key('cursor')
        if needsCursors and isinstance(json, dict) and 'previous_cursor' in json and 'next_cursor' in json:
            cursors = json['previous_cursor'], json['next_cursor']
            return json, cursors
        else:
            return json

    def parse_error(self, payload):
        error = self.json_lib.loads(payload)
        if error.has_key('error'):
            return error['error']
        else:
            return error['errors']


class ModelParser(JSONParser):

    def __init__(self, model_factory=None):
        JSONParser.__init__(self)
        self.model_factory = model_factory or ModelFactory

    def parse(self, method, payload):
        try:
            if method.payload_type is None: return
            model = getattr(self.model_factory, method.payload_type)
        except AttributeError:
            raise TweepError('No model for this payload type: %s' % method.payload_type)

        json = JSONParser.parse(self, method, payload)
        if isinstance(json, tuple):
            json, cursors = json
        else:
            cursors = None

        if method.payload_list:
            result = model.parse_list(method.api, json)
        else:
            result = model.parse(method.api, json)

        if cursors:
            return result, cursors
        else:
            return result


########NEW FILE########
__FILENAME__ = streaming
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import httplib
from socket import timeout
from threading import Thread
from time import sleep

from tweepy.models import Status
from tweepy.api import API
from tweepy.error import TweepError

from tweepy.utils import import_simplejson, urlencode_noplus
json = import_simplejson()

STREAM_VERSION = '1.1'


class StreamListener(object):

    def __init__(self, api=None):
        self.api = api or API()

    def on_connect(self):
        """Called once connected to streaming server.

        This will be invoked once a successful response
        is received from the server. Allows the listener
        to perform some work prior to entering the read loop.
        """
        pass

    def on_data(self, data):
        """Called when raw data is received from connection.

        Override this method if you wish to manually handle
        the stream data. Return False to stop stream and close connection.
        """

        if 'in_reply_to_status_id' in data:
            status = Status.parse(self.api, json.loads(data))
            if self.on_status(status) is False:
                return False
        elif 'delete' in data:
            delete = json.loads(data)['delete']['status']
            if self.on_delete(delete['id'], delete['user_id']) is False:
                return False
        elif 'limit' in data:
            if self.on_limit(json.loads(data)['limit']['track']) is False:
                return False

    def on_status(self, status):
        """Called when a new status arrives"""
        return

    def on_delete(self, status_id, user_id):
        """Called when a delete notice arrives for a status"""
        return

    def on_limit(self, track):
        """Called when a limitation notice arrvies"""
        return

    def on_error(self, status_code):
        """Called when a non-200 status code is returned"""
        return False

    def on_timeout(self):
        """Called when stream connection times out"""
        return


class Stream(object):

    host = 'stream.twitter.com'

    def __init__(self, auth, listener, **options):
        self.auth = auth
        self.listener = listener
        self.running = False
        self.timeout = options.get("timeout", 300.0)
        self.retry_count = options.get("retry_count")
        self.retry_time = options.get("retry_time", 10.0)
        self.snooze_time = options.get("snooze_time",  5.0)
        self.buffer_size = options.get("buffer_size",  1500)
        if options.get("secure", True):
            self.scheme = "https"
        else:
            self.scheme = "http"

        self.api = API()
        self.headers = options.get("headers") or {}
        self.parameters = None
        self.body = None

    def _run(self):
        # Authenticate
        url = "%s://%s%s" % (self.scheme, self.host, self.url)

        # Connect and process the stream
        error_counter = 0
        conn = None
        exception = None
        while self.running:
            if self.retry_count is not None and error_counter > self.retry_count:
                # quit if error count greater than retry count
                break
            try:
                if self.scheme == "http":
                    conn = httplib.HTTPConnection(self.host)
                else:
                    conn = httplib.HTTPSConnection(self.host)
                self.auth.apply_auth(url, 'POST', self.headers, self.parameters)
                conn.connect()
                conn.sock.settimeout(self.timeout)
                conn.request('POST', self.url, self.body, headers=self.headers)
                resp = conn.getresponse()
                if resp.status != 200:
                    if self.listener.on_error(resp.status) is False:
                        break
                    error_counter += 1
                    sleep(self.retry_time)
                else:
                    error_counter = 0
                    self.listener.on_connect()
                    self._read_loop(resp)
            except timeout:
                if self.listener.on_timeout() == False:
                    break
                if self.running is False:
                    break
                conn.close()
                sleep(self.snooze_time)
            except Exception, exception:
                # any other exception is fatal, so kill loop
                break

        # cleanup
        self.running = False
        if conn:
            conn.close()

        if exception:
            raise

    def _data(self, data):
        if self.listener.on_data(data) is False:
            self.running = False

    def _read_loop(self, resp):

        while self.running and not resp.isclosed():

            # Note: keep-alive newlines might be inserted before each length value.
            # read until we get a digit...
            c = '\n'
            while c == '\n' and self.running and not resp.isclosed():
                c = resp.read(1)
            delimited_string = c

            # read rest of delimiter length..
            d = ''
            while d != '\n' and self.running and not resp.isclosed():
                d = resp.read(1)
                delimited_string += d

            # read the next twitter status object
            if delimited_string.strip().isdigit():
                next_status_obj = resp.read( int(delimited_string) )
                self._data(next_status_obj)

        if resp.isclosed():
            self.on_closed(resp)

    def _start(self, async):
        self.running = True
        if async:
            Thread(target=self._run).start()
        else:
            self._run()

    def on_closed(self, resp):
        """ Called when the response has been closed by Twitter """
        pass

    def userstream(self, count=None, async=False, secure=True):
        self.parameters = {'delimited': 'length'}
        if self.running:
            raise TweepError('Stream object already connected!')
        self.url = '/2/user.json?delimited=length'
        self.host='userstream.twitter.com'
        self._start(async)

    def firehose(self, count=None, async=False):
        self.parameters = {'delimited': 'length'}
        if self.running:
            raise TweepError('Stream object already connected!')
        self.url = '/%s/statuses/firehose.json?delimited=length' % STREAM_VERSION
        if count:
            self.url += '&count=%s' % count
        self._start(async)

    def retweet(self, async=False):
        self.parameters = {'delimited': 'length'}
        if self.running:
            raise TweepError('Stream object already connected!')
        self.url = '/%s/statuses/retweet.json?delimited=length' % STREAM_VERSION
        self._start(async)

    def sample(self, count=None, async=False):
        self.parameters = {'delimited': 'length'}
        if self.running:
            raise TweepError('Stream object already connected!')
        self.url = '/%s/statuses/sample.json?delimited=length' % STREAM_VERSION
        if count:
            self.url += '&count=%s' % count
        self._start(async)

    def filter(self, follow=None, track=None, async=False, locations=None, 
        count = None, stall_warnings=False, languages=None):
        self.parameters = {}
        self.headers['Content-type'] = "application/x-www-form-urlencoded"
        if self.running:
            raise TweepError('Stream object already connected!')
        self.url = '/%s/statuses/filter.json?delimited=length' % STREAM_VERSION
        if follow:
            self.parameters['follow'] = ','.join(map(str, follow))
        if track:
            self.parameters['track'] = ','.join(map(str, track))
        if locations and len(locations) > 0:
            assert len(locations) % 4 == 0
            self.parameters['locations'] = ','.join(['%.2f' % l for l in locations])
        if count:
            self.parameters['count'] = count
        if stall_warnings:
            self.parameters['stall_warnings'] = stall_warnings
        if languages:
            self.parameters['language'] = ','.join(map(str, languages))
        self.body = urlencode_noplus(self.parameters)
        self.parameters['delimited'] = 'length'
        self._start(async)

    def disconnect(self):
        if self.running is False:
            return
        self.running = False


########NEW FILE########
__FILENAME__ = utils
# Tweepy
# Copyright 2010 Joshua Roesslein
# See LICENSE for details.

from datetime import datetime
import time
import htmlentitydefs
import re
import locale
from urllib import quote


def parse_datetime(string):
    # Set locale for date parsing
    locale.setlocale(locale.LC_TIME, 'C')

    # We must parse datetime this way to work in python 2.4
    date = datetime(*(time.strptime(string, '%a %b %d %H:%M:%S +0000 %Y')[0:6]))

    # Reset locale back to the default setting
    locale.setlocale(locale.LC_TIME, '')
    return date


def parse_html_value(html):

    return html[html.find('>')+1:html.rfind('<')]


def parse_a_href(atag):

    start = atag.find('"') + 1
    end = atag.find('"', start)
    return atag[start:end]


def parse_search_datetime(string):
    # Set locale for date parsing
    locale.setlocale(locale.LC_TIME, 'C')

    # We must parse datetime this way to work in python 2.4
    date = datetime(*(time.strptime(string, '%a, %d %b %Y %H:%M:%S +0000')[0:6]))

    # Reset locale back to the default setting
    locale.setlocale(locale.LC_TIME, '')
    return date


def unescape_html(text):
    """Created by Fredrik Lundh (http://effbot.org/zone/re-sub.htm#unescape-html)"""
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
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)


def convert_to_utf8_str(arg):
    # written by Michael Norton (http://docondev.blogspot.com/)
    if isinstance(arg, unicode):
        arg = arg.encode('utf-8')
    elif not isinstance(arg, str):
        arg = str(arg)
    return arg



def import_simplejson():
    try:
        import simplejson as json
    except ImportError:
        try:
            import json  # Python 2.6+
        except ImportError:
            try:
                from django.utils import simplejson as json  # Google App Engine
            except ImportError:
                raise ImportError, "Can't load a json library"

    return json

def list_to_csv(item_list):
    if item_list:
        return ','.join([str(i) for i in item_list])

def urlencode_noplus(query):
    return '&'.join(['%s=%s' % (quote(str(k)), quote(str(v))) \
        for k, v in query.iteritems()])


########NEW FILE########
__FILENAME__ = logger
"""Logging for Python YQL."""

import os
import logging
import logging.handlers


LOG_DIRECTORY_DEFAULT = os.path.join(os.path.dirname(__file__), "../logs")
LOG_DIRECTORY = os.environ.get("YQL_LOG_DIR", LOG_DIRECTORY_DEFAULT)
LOG_LEVELS = {'debug': logging.DEBUG,
              'info': logging.INFO,
              'warning': logging.WARNING,
              'error': logging.ERROR,
              'critical': logging.CRITICAL}

LOG_LEVEL = os.environ.get("YQL_LOGGING_LEVEL", 'debug')
LOG_FILENAME = os.path.join(LOG_DIRECTORY, "python-yql.log")
MAX_BYTES = 1024 * 1024

log_level = LOG_LEVELS.get(LOG_LEVEL)
yql_logger = logging.getLogger("python-yql")
yql_logger.setLevel(LOG_LEVELS.get(LOG_LEVEL))


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


def get_logger():
    """Set-upt the logger if enabled or fallback to NullHandler."""
    if os.environ.get("YQL_LOGGING", False):
        if not os.path.exists(LOG_DIRECTORY):
            os.mkdir(LOG_DIRECTORY)
        log_handler = logging.handlers.RotatingFileHandler(
                                LOG_FILENAME, maxBytes=MAX_BYTES,
                                backupCount=5)
        formatter = logging.Formatter(
                        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        log_handler.setFormatter(formatter)
    else:
        log_handler = NullHandler()
    yql_logger.addHandler(log_handler)
    return yql_logger

########NEW FILE########
__FILENAME__ = storage
import os
from hashlib import md5

from yql import YahooToken

SECRET = "FDHSJLUREIRPpieruweruwoeirhfsdjf"


class TokenStoreError(Exception):
    """Generic token storage"""
    pass


class BaseTokenStore(object):
    """Base class for storage"""

    def set(self, name, token):
        raise NotImplementedError

    def get(self, name):
        raise NotImplementedError


class FileTokenStore(BaseTokenStore):
    """A simple filesystem based token store

    Note: this is more intended as an example rather than
    something for heavy duty production usage.

    """

    def __init__(self, dir_path, secret=None):
        """Initialize token storage"""

        if not os.path.exists(dir_path):
            raise TokenStoreError("Path is not valid")

        self.base_dir = dir_path
        self.secret = secret or SECRET

    def get_filepath(self, name):
        """Build filepath"""

        filename = md5("%s%s" % (name, self.secret)).hexdigest()
        filepath = os.path.join(self.base_dir, filename)

        return filepath

    def set(self, name, token):
        """Write a token to file"""

        if hasattr(token, 'key'):
            token = YahooToken.to_string(token)

        if token:
            filepath = self.get_filepath(name)
            f_handle = open(filepath, 'w')
            f_handle.write(token)
            f_handle.close()

    def get(self, name):
        """Get a token from the filesystem"""

        filepath = self.get_filepath(name)

        if os.path.exists(filepath):
            f_handle = open(filepath, 'r')
            token = f_handle.read()
            f_handle.close()

            token = YahooToken.from_string(token)
            return token

########NEW FILE########
__FILENAME__ = test_errors
import json
from unittest import TestCase

from yql import NotOneError, YQLError


class YQLErrorTest(TestCase):
    def test_error_passed_error_string(self):
        error = YQLError(resp='some response', content='some content')
        self.assertEqual("some content", str(error))

    def test_error_passed_object(self):
        error = YQLError(resp='some response', content={"foo": 1})
        self.assertEqual(repr({"foo": 1}), str(error))

    def test_error_passed_json(self):
        content = {
            'error': {
                'description': 'some description',
            }
        }
        error = YQLError(resp='some response', content=json.dumps(content))
        self.assertEqual("some description", str(error))


class NotOneErrorTest(TestCase):
    def test_is_represented_by_message_as_json(self):
        error = NotOneError('some message')
        self.assertEqual("some message", str(error))

########NEW FILE########
__FILENAME__ = test_live_services
"""Tests against live services.

*** SKIPPED BY DEFAULT ***

These tests won't normally be run, as part of the main test suite but are run by
our hudson instance to tell us should Yahoo's API change in some way that will
break python-yql.

Note to end-users: These tests are dependent on defining a secrets file with API
keys and other secrets which are required to carry out these tests.

If the secrets file isn't present the tests are skipped

"""
import os
import sys
from time import time
from unittest import TestCase

from nose.plugins.skip import SkipTest

import yql
from yql.storage import FileTokenStore


SECRETS_DIR = os.path.join(os.path.dirname(__file__), "../../../secrets")
CACHE_DIR = os.path.abspath(os.path.join(SECRETS_DIR, "cache"))

try:
    if SECRETS_DIR not in sys.path:
        sys.path.append(SECRETS_DIR)

    from secrets import *
except ImportError:
    raise SkipTest("Unable to find secrets directory")


class LiveTestCase(TestCase):
    """A test case containing live tests"""

    def test_write_bitly_url(self):
        """Test writing bit.ly url"""

        query = """USE 'http://www.datatables.org/bitly/bit.ly.shorten.xml';
           SELECT * from bit.ly.shorten where login='%s' and apiKey='%s' and
           longUrl='http://yahoo.com'""" % (BITLY_USER, BITLY_API_KEY)

        y = yql.TwoLegged(YQL_API_KEY, YQL_SHARED_SECRET)
        res = y.execute(query)
        assert res.one()["data"]["url"] == "http://yhoo.it/9PPTOr"

    def test_public_request(self):
        """Test public two-legged request to flickr"""
        query = """select * from flickr.photos.search where
                   text="panda" and api_key='%s' LIMIT 3""" % FLICKR_API_KEY
        y = yql.TwoLegged(YQL_API_KEY, YQL_SHARED_SECRET)
        res = y.execute(query)
        assert len(res.rows) == 3

    def test_two_legged_weather_select(self):
        """Tests the weather tables using two-legged"""
        query = """select * from weather.forecast where location in
                (select id from xml where
                url='http://xoap.weather.com/search/search?where=london'
                and itemPath='search.loc')"""
        y = yql.TwoLegged(YQL_API_KEY, YQL_SHARED_SECRET)
        res = y.execute(query)
        assert len(res.rows) > 1

    def test_update_social_status(self):
        """Updates status"""
        y = yql.ThreeLegged(YQL_API_KEY, YQL_SHARED_SECRET)

        timestamp = time()
        query = """UPDATE social.profile.status
                   SET status='Using YQL. %s Update'
                   WHERE guid=me"""  % timestamp

        token_store = FileTokenStore(CACHE_DIR, secret='gsfdsfdsfdsfs')
        stored_token = token_store.get('foo')

        if not stored_token:
            # Do the dance
            request_token, auth_url = y.get_token_and_auth_url()
            print "Visit url %s and get a verifier string" % auth_url
            verifier = raw_input("Enter the code: ")
            token = y.get_access_token(request_token, verifier)
            token_store.set('foo', token)
        else:
            # Check access_token is within 1hour-old and if not refresh it
            # and stash it
            token = y.check_token(stored_token)
            if token != stored_token:
                token_store.set('foo', token)

        res = y.execute(query, token=token)
        assert res.rows[0] == "ok"
        new_query = """select message from social.profile.status where guid=me"""
        res = y.execute(new_query, token=token)
        assert res.rows[0].get("message") == "Using YQL. %s Update" % timestamp

    def test_update_meme_status(self):
        """Updates status"""
        y = yql.ThreeLegged(YQL_API_KEY, YQL_SHARED_SECRET)
        query = 'INSERT INTO meme.user.posts (type, content) VALUES("text", "test with pythonyql")'
        token_store = FileTokenStore(CACHE_DIR, secret='fjdsfjllds')

        store_name = "meme"
        stored_token = token_store.get(store_name)
        if not stored_token:
            # Do the dance
            request_token, auth_url = y.get_token_and_auth_url()
            print "Visit url %s and get a verifier string" % auth_url
            verifier = raw_input("Enter the code: ")
            token = y.get_access_token(request_token, verifier)
            token_store.set(store_name, token)
        else:
            # Check access_token is within 1hour-old and if not refresh it
            # and stash it
            token = y.check_token(stored_token)
            if token != stored_token:
                token_store.set(store_name, token)

        # post a meme
        res = y.execute(query, token=token)
        assert y.uri == "http://query.yahooapis.com/v1/yql"
        assert res.rows[0].get("message") == "ok"

        pubid = None
        if res.rows[0].get("post") and res.rows[0]["post"].get("pubid"):
            pubid = res.rows[0]["post"]["pubid"]

        # Delete the post we've just created
        query = 'DELETE FROM meme.user.posts WHERE pubid=@pubid'
        res2 = y.execute(query, token=token, params={"pubid": pubid})
        assert res2.rows[0].get("message") == "ok"

    def test_check_env_var(self):
        """Testing env variable"""
        y = yql.Public()
        env = "http://datatables.org/alltables.env"
        query = "SHOW tables;"
        res = y.execute(query, env=env)
        assert res.count >= 800

    def test_xpath_works(self):
        y = yql.Public()
        query = """SELECT * FROM html
                   WHERE url='http://google.co.uk'
                   AND xpath="//input[contains(@name, 'q')]"
                   LIMIT 10"""
        res = y.execute(query)
        assert res.rows[0].get("title") == "Search"



########NEW FILE########
__FILENAME__ = test_logger
import os
import shutil
from unittest import TestCase

import yql.logger


class LoggerTest(TestCase):
    def setUp(self):
        self._logging = os.environ.get('YQL_LOGGING', '')

    def tearDown(self):
        os.environ['YQL_LOGGING'] = self._logging

    def test_is_instantiated_even_if_log_dir_doesnt_exist(self):
        os.environ['YQL_LOGGING'] = '1'
        if os.path.exists(yql.logger.LOG_DIRECTORY):
            shutil.rmtree(yql.logger.LOG_DIRECTORY)
        yql.logger.get_logger()

    def test_logs_message_to_file(self):
        os.environ['YQL_LOGGING'] = '1'
        yql.logger.get_logger()

########NEW FILE########
__FILENAME__ = test_query_placeholders
"""Set of tests for the placeholder checking"""

from unittest import TestCase

from nose.tools import raises

import yql


class PublicTest(TestCase):
    @raises(ValueError)
    def test_empty_args_raises_valueerror(self):
        y = yql.Public()
        query = "SELECT * from foo where dog=@dog"
        params = {}
        y.execute(query, params)

    @raises(ValueError)
    def test_incorrect_args_raises_valueerror(self):
        y = yql.Public()
        query = "SELECT * from foo where dog=@dog"
        params = {'test': 'fail'}
        y.execute(query, params)

    @raises(ValueError)
    def test_params_raises_when_not_dict(self):
        y = yql.Public()
        query = "SELECT * from foo where dog=@dog"
        params = ['test']
        y.execute(query, params)

    @raises(ValueError)
    def test_unecessary_args_raises_valueerror(self):
        y = yql.Public()
        query = "SELECT * from foo where dog='test'"
        params = {'test': 'fail'}
        y.execute(query, params)

    @raises(ValueError)
    def test_incorrect_type_raises_valueerror(self):
        y = yql.Public()
        query = "SELECT * from foo where dog=@test"
        params = ('fail')
        y.execute(query, params)

    def test_placeholder_regex_one(self):
        y = yql.Public()
        query = "SELECT * from foo where email='foo@foo.com'"
        placeholders = y.get_placeholder_keys(query)
        self.assertEqual(placeholders, [])

    def test_placeholder_regex_two(self):
        y = yql.Public()
        query = "SELECT * from foo where email=@foo'"
        placeholders = y.get_placeholder_keys(query)
        self.assertEqual(placeholders, ['foo'])

    def test_placeholder_regex_three(self):
        y = yql.Public()
        query = "SELECT * from foo where email=@foo and test=@bar'"
        placeholders = y.get_placeholder_keys(query)
        self.assertEqual(placeholders, ['foo', 'bar'])

    def test_placeholder_regex_four(self):
        y = yql.Public()
        query = "SELECT * from foo where foo='bar' LIMIT @foo"
        placeholders = y.get_placeholder_keys(query)
        self.assertEqual(placeholders, ['foo'])

    def test_placeholder_regex_five(self):
        y = yql.Public()
        query = """SELECT * from foo
                    where foo='bar' LIMIT
                    @foo"""
        placeholders = y.get_placeholder_keys(query)
        self.assertEqual(placeholders, ['foo'])


########NEW FILE########
__FILENAME__ = test_requests_responses
from email import message_from_file
import os
from unittest import TestCase
import urlparse
from urllib import urlencode
try:
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl

from nose.tools import raises
from nose import with_setup
import oauth2 as oauth
import httplib2

import yql


HTTP_SRC_DIR = os.path.join(os.path.dirname(__file__), "http_src/")


class FileDataHttpReplacement(object):
    """Build a stand-in for httplib2.Http that takes its
    response headers and bodies from files on disk

    http://bitworking.org/news/172/Test-stubbing-httplib2

    """

    def __init__(self, cache=None, timeout=None):
        self.hit_counter = {}

    def request(self, uri, method="GET", body=None, headers=None, redirections=5):
        path = urlparse.urlparse(uri)[2]
        fname = os.path.join(HTTP_SRC_DIR, path[1:])

        if not os.path.exists(fname):
            index = self.hit_counter.get(fname, 1)

            if os.path.exists(fname + "." + str(index)):
                self.hit_counter[fname] = index + 1
                fname = fname + "." + str(index)

        if os.path.exists(fname):
            f = file(fname, "r")
            response = message_from_file(f)
            f.close()
            body = response.get_payload()
            response_headers = httplib2.Response(response)
            return (response_headers, body)
        else:
            return (httplib2.Response({"status": "404"}), "")

    def add_credentials(self, name, password):
        pass


class RequestDataHttpReplacement:
    """Create an httplib stub that returns request data"""

    def __init__(self):
        pass

    def request(self, uri, *args, **kwargs):
        """return the request data"""
        return uri, args, kwargs


class TestPublic(yql.Public):
    """Subclass of YQL to allow returning of the request data"""

    execute = yql.Public.get_uri


class TestTwoLegged(yql.TwoLegged):
    """Subclass of YQLTwoLegged to allow returning of the request data"""

    execute = yql.TwoLegged.get_uri


class TestThreeLegged(yql.ThreeLegged):
    """Subclass of YQLTwoLegged to allow returning of the request data"""

    execute = yql.ThreeLegged.get_uri


class StubbedHttpTestCase(TestCase):
    stub = None

    def setUp(self):
        self._http = httplib2.Http
        httplib2.Http = self.stub

    def tearDown(self):
        httplib2.Http = self._http


class PublicStubbedRequestTest(StubbedHttpTestCase):
    stub =  RequestDataHttpReplacement

    def test_urlencoding_for_public_yql(self):
        query = 'SELECT * from foo'
        y = TestPublic(httplib2_inst=httplib2.Http())
        uri = y.execute(query)
        self.assertEqual(uri, "http://query.yahooapis.com/v1/public/yql?q=SELECT+%2A+from+foo&format=json")

    def test_env_for_public_yql(self):
        query = 'SELECT * from foo'
        y = TestPublic(httplib2_inst=httplib2.Http())
        uri = y.execute(query, env="http://foo.com")
        self.assertTrue(uri.find(urlencode({"env":"http://foo.com"})) > -1)

    def test_name_param_inserted_for_public_yql(self):
        query = 'SELECT * from foo WHERE dog=@dog'
        y = TestPublic(httplib2_inst=httplib2.Http())
        uri = y.execute(query, {"dog": "fifi"})
        self.assertTrue(uri.find('dog=fifi') >-1)


class PublicStubbedFromFileTest(StubbedHttpTestCase):
    stub =  FileDataHttpReplacement

    def test_json_response_from_file(self):
        query = 'SELECT * from foo WHERE dog=@dog'
        y = yql.Public(httplib2_inst=httplib2.Http())
        content = y.execute(query, {"dog": "fifi"})
        self.assertEqual(content.count, 3)


class TwoLeggedTest(TestCase):
    @raises(TypeError)
    def test_yql_with_2leg_auth_raises_typerror(self):
        TestTwoLegged()

    def test_api_key_and_secret_attrs(self):
        y = yql.TwoLegged('test-api-key', 'test-secret')
        self.assertEqual(y.api_key, 'test-api-key')
        self.assertEqual(y.secret, 'test-secret')

    def test_get_two_legged_request_keys(self):
        y = yql.TwoLegged('test-api-key', 'test-secret')
        # Accessed this was because it's private
        request =  y._TwoLegged__two_legged_request('http://google.com')
        self.assertEqual(set(['oauth_nonce', 'oauth_version', 'oauth_timestamp',
            'oauth_consumer_key', 'oauth_signature_method', 'oauth_body_hash',
            'oauth_version', 'oauth_signature']), set(request.keys()))

    def test_get_two_legged_request_values(self):
        y = yql.TwoLegged('test-api-key', 'test-secret')
        # Accessed this was because it's private
        request =  y._TwoLegged__two_legged_request('http://google.com')
        self.assertEqual(request['oauth_consumer_key'], 'test-api-key')
        self.assertEqual(request['oauth_signature_method'], 'HMAC-SHA1')
        self.assertEqual(request['oauth_version'], '1.0')

    def test_get_two_legged_request_param(self):
        y = yql.TwoLegged('test-api-key', 'test-secret')
        # Accessed this way because it's private
        request =  y._TwoLegged__two_legged_request('http://google.com',
                                                            {"test-param": "test"})
        self.assertEqual(request.get('test-param'), 'test')


class TwoLeggedStubbedRequestTest(StubbedHttpTestCase):
    stub =  RequestDataHttpReplacement

    def test_request_for_two_legged(self):
        query = 'SELECT * from foo'
        y = TestTwoLegged('test-api-key', 'test-secret', httplib2_inst=httplib2.Http())
        signed_url = y.execute(query)
        qs  = dict(parse_qsl(signed_url.split('?')[1]))
        self.assertEqual(qs['q'], query)
        self.assertEqual(qs['format'], 'json')


class TwoLeggedStubbedFromFileTest(StubbedHttpTestCase):
    stub =  FileDataHttpReplacement

    def test_get_two_legged_from_file(self):
        query = 'SELECT * from foo'
        y = yql.TwoLegged('test-api-key', 'test-secret', httplib2_inst=httplib2.Http())
        # Accessed this was because it's private
        self.assertTrue(y.execute(query) is not None)


class ThreeLeggedTest(TestCase):
    @raises(TypeError)
    def test_yql_with_3leg_auth_raises_typerror(self):
        TestThreeLegged()

    def test_api_key_and_secret_attrs2(self):
        y = yql.ThreeLegged('test-api-key', 'test-secret')
        self.assertEqual(y.api_key, 'test-api-key')
        self.assertEqual(y.secret, 'test-secret')

    def test_get_base_params(self):
        y = yql.ThreeLegged('test-api-key', 'test-secret')
        result = y.get_base_params()
        self.assertEqual(set(['oauth_nonce', 'oauth_version', 'oauth_timestamp']),
                         set(result.keys()))

    @raises(ValueError)
    def test_raises_for_three_legged_with_no_token(self):
        query = 'SELECT * from foo'
        y = TestThreeLegged('test-api-key', 'test-secret', httplib2_inst=httplib2.Http())
        y.execute(query)


class ThreeLeggedStubbedRequestTest(StubbedHttpTestCase):
    stub =  RequestDataHttpReplacement

    def test_request_for_three_legged(self):
        query = 'SELECT * from foo'
        y = TestThreeLegged('test-api-key', 'test-secret',
                                            httplib2_inst=httplib2.Http())
        token = oauth.Token.from_string(
                            'oauth_token=foo&oauth_token_secret=bar')
        signed_url = y.execute(query, token=token)
        qs  = dict(parse_qsl(signed_url.split('?')[1]))
        self.assertEqual(qs['q'], query)
        self.assertEqual(qs['format'], 'json')


class ThreeLeggedStubbedFromFileTest(StubbedHttpTestCase):
    stub =  FileDataHttpReplacement

    def test_three_legged_execution(self):
        query = 'SELECT * from foo WHERE dog=@dog'
        y = yql.ThreeLegged('test','test2', httplib2_inst=httplib2.Http())
        token = yql.YahooToken('test', 'test2')
        content = y.execute(query, {"dog": "fifi"}, token=token)
        self.assertEqual(content.count, 3)

    @raises(ValueError)
    def test_three_legged_execution_raises_value_error_with_invalid_uri(self):
        y = yql.ThreeLegged('test','test2', httplib2_inst=httplib2.Http())
        y.uri = "fail"
        token = yql.YahooToken('tes1t', 'test2')
        y.execute("SELECT foo meh meh ", token=token)

    def test_get_access_token_request3(self):
        y = yql.ThreeLegged('test', 'test-does-not-exist',
                                    httplib2_inst=httplib2.Http())
        new_token = yql.YahooToken('test', 'test2')
        new_token.session_handle = 'sess_handle_test'
        token = y.refresh_token(token=new_token)
        self.assertTrue(hasattr(token, 'key'))
        self.assertTrue(hasattr(token, 'secret'))

########NEW FILE########
__FILENAME__ = test_services
from unittest import TestCase

from nose.tools import raises

import yql


class PublicTest(TestCase):
    @raises(ValueError)
    def test_cannot_use_unrecognizable_endpoint(self):
        y = yql.Public()
        y.endpoint = 'some-strange-endpoint'

########NEW FILE########
__FILENAME__ = test_storage
import os
import tempfile
from unittest import TestCase

from nose.tools import raises

from yql import YahooToken
from yql.storage import BaseTokenStore, FileTokenStore, TokenStoreError


class BaseTokenStoreTest(TestCase):
    @raises(NotImplementedError)
    def test_must_implement_set(self):
        class FooStore(BaseTokenStore):
            pass
        store = FooStore()
        store.set('some name', 'some token')

    @raises(NotImplementedError)
    def test_must_implement_get(self):
        class FooStore(BaseTokenStore):
            pass
        store = FooStore()
        store.get('some name')


class FileTokenStoreTest(TestCase):
    @raises(TokenStoreError)
    def test_must_be_instanced_with_an_existant_path(self):
        FileTokenStore('/some/inexistant/path')

    def test_saves_token_string_to_filesystem(self):
        directory = tempfile.mkdtemp()
        store = FileTokenStore(directory)
        store.set('foo', '?key=some-token')
        with open(store.get_filepath('foo')) as stored_file:
            self.assertTrue('some-token' in stored_file.read())

    def test_retrieves_token_from_filesystem(self):
        directory = tempfile.mkdtemp()
        store = FileTokenStore(directory)
        store.set('foo', '?key=%s&oauth_token=some-oauth-token&'\
                  'oauth_token_secret=some-token-secret' % 'some-token')
        token = store.get('foo')
        self.assertTrue('some-token' in token.to_string())

    def test_cannot_retrieve_token_if_path_doesnt_exist(self):
        directory = tempfile.mkdtemp()
        store = FileTokenStore(directory)
        store.set('foo', '?key=%s&oauth_token=some-oauth-token&'\
                  'oauth_token_secret=some-token-secret' % 'some-token')
        os.remove(store.get_filepath('foo'))
        self.assertTrue(store.get('foo') is None)

    def test_saves_token_to_filesystem(self):
        directory = tempfile.mkdtemp()
        store = FileTokenStore(directory)
        token = YahooToken('some-token', 'some-secret')
        store.set('foo', token)
        with open(store.get_filepath('foo')) as stored_file:
            self.assertTrue('some-token' in stored_file.read())

########NEW FILE########
__FILENAME__ = test_utilities
from unittest import TestCase

from yql.utils import get_http_method


class UtilitiesTest(TestCase):
    def test_finds_get_method_for_select_query(self):
        self.assertEqual(get_http_method("SELECT foo"), "GET")

    def test_finds_get_method_for_select_query_with_leading_space(self):
        self.assertEqual(get_http_method(" SELECT foo"), "GET")

    def test_finds_get_method_for_lowercase_select_query(self):
        self.assertEqual(get_http_method("select foo"), "GET")

    def test_finds_post_method_for_insert_query(self):
        self.assertEqual(get_http_method("INSERT into"), "POST")

    def test_finds_post_method_for_multiline_insert_query(self):
        query = """
        INSERT INTO yql.queries.query (name, query)
        VALUES ("weather", "SELECT * FROM weather.forecast
            WHERE location=90210")
            """
        self.assertEqual(get_http_method(query), "POST")

    def test_finds_put_method_for_update_query(self):
        self.assertEqual(get_http_method("update foo"), "PUT")

    def test_finds_post_method_for_delete_query(self):
        self.assertEqual(get_http_method("DELETE from"), "POST")

    def test_finds_post_method_for_lowercase_delete_query(self):
        self.assertEqual(get_http_method("delete from"), "POST")

    def test_finds_get_method_for_show_query(self):
        self.assertEqual(get_http_method("SHOW tables"), "GET")

    def test_finds_get_method_for_describe_query(self):
        self.assertEqual(get_http_method("DESC tablename"), "GET")

########NEW FILE########
__FILENAME__ = test_yahoo_token
from unittest import TestCase

from nose.tools import raises
try:
    from urlparse import parse_qs, parse_qsl
except ImportError:
    from cgi import parse_qs, parse_qsl

import yql


class YahooTokenTest(TestCase):
    def test_create_yahoo_token(self):
        token = yql.YahooToken('test-key', 'test-secret')
        self.assertEqual(token.key, 'test-key')
        self.assertEqual(token.secret, 'test-secret')

    def test_y_token_to_string(self):
        token = yql.YahooToken('test-key', 'test-secret')
        token_to_string = token.to_string()
        string_data = dict(parse_qsl(token_to_string))
        self.assertEqual(string_data.get('oauth_token'), 'test-key')
        self.assertEqual(string_data.get('oauth_token_secret'), 'test-secret')

    def test_y_token_to_string2(self):
        token = yql.YahooToken('test-key', 'test-secret')

        token.timestamp = '1111'
        token.session_handle = 'poop'
        token.callback_confirmed = 'basilfawlty'

        token_to_string = token.to_string()
        string_data = dict(parse_qsl(token_to_string))
        self.assertEqual(string_data.get('oauth_token'), 'test-key')
        self.assertEqual(string_data.get('oauth_token_secret'), 'test-secret')
        self.assertEqual(string_data.get('token_creation_timestamp'), '1111')
        self.assertEqual(string_data.get('oauth_callback_confirmed'), 'basilfawlty')
        self.assertEqual(string_data.get('oauth_session_handle'), 'poop')

    def test_y_token_from_string(self):
        token_string = "oauth_token=foo&oauth_token_secret=bar&"\
                       "oauth_session_handle=baz&token_creation_timestamp=1111"
        token_from_string = yql.YahooToken.from_string(token_string)
        self.assertEqual(token_from_string.key, 'foo')
        self.assertEqual(token_from_string.secret, 'bar')
        self.assertEqual(token_from_string.session_handle, 'baz')
        self.assertEqual(token_from_string.timestamp, '1111')

    @raises(ValueError)
    def test_y_token_raises_value_error(self):
        yql.YahooToken.from_string('')

    @raises(ValueError)
    def test_y_token_raises_value_error2(self):
        yql.YahooToken.from_string('foo')

    @raises(ValueError)
    def test_y_token_raises_value_error3(self):
        yql.YahooToken.from_string('oauth_token=bar')

    @raises(ValueError)
    def test_y_token_raises_value_error4(self):
        yql.YahooToken.from_string('oauth_token_secret=bar')

    @raises(AttributeError)
    def test_y_token_without_timestamp_raises(self):
        token = yql.YahooToken('test', 'test2')
        y = yql.ThreeLegged('test', 'test2')
        y.check_token(token)

    def test_y_token_without_timestamp_raises2(self):

        def refresh_token_replacement(token):
            return 'replaced'

        y = yql.ThreeLegged('test', 'test2')
        y.refresh_token = refresh_token_replacement

        token = yql.YahooToken('test', 'test2')
        token.timestamp = 11111
        self.assertEqual(y.check_token(token), 'replaced')

########NEW FILE########
__FILENAME__ = test_yql_object
"""Tests for the YQL object"""

import json
from unittest import TestCase

from nose.tools import raises

from yql import YQLObj, NotOneError


data_dict = json.loads("""{"query":{"count":"3","created":"2009-11-20T12:11:56Z","lang":"en-US","updated":"2009-11-20T12:11:56Z","uri":"http://query.yahooapis.com/v1/yql?q=select+*+from+flickr.photos.search+where+text%3D%22panda%22+limit+3","diagnostics":{"publiclyCallable":"true","url":{"execution-time":"742","content":"http://api.flickr.com/services/rest/?method=flickr.photos.search&text=panda&page=1&per_page=10"},"user-time":"745","service-time":"742","build-version":"3805"},"results":{"photo":[{"farm":"3","id":"4117944207","isfamily":"0","isfriend":"0","ispublic":"1","owner":"12346075@N00","secret":"ce1f6092de","server":"2510","title":"Pandas"},{"farm":"3","id":"4118710292","isfamily":"0","isfriend":"0","ispublic":"1","owner":"12346075@N00","secret":"649632a3e2","server":"2754","title":"Pandas"},{"farm":"3","id":"4118698318","isfamily":"0","isfriend":"0","ispublic":"1","owner":"28451051@N02","secret":"ec0b508684","server":"2586","title":"fuzzy flowers (Kalanchoe tomentosa)"}]}}}""")
data_dict2 = json.loads("""{"query":{"count":"1","created":"2009-11-20T12:11:56Z","lang":"en-US","updated":"2009-11-20T12:11:56Z","uri":"http://query.yahooapis.com/v1/yql?q=select+*+from+flickr.photos.search+where+text%3D%22panda%22+limit+3","diagnostics":{"publiclyCallable":"true","url":{"execution-time":"742","content":"http://api.flickr.com/services/rest/?method=flickr.photos.search&text=panda&page=1&per_page=10"},"user-time":"745","service-time":"742","build-version":"3805"},"results":{"photo":{"farm":"3","id":"4117944207","isfamily":"0","isfriend":"0","ispublic":"1","owner":"12346075@N00","secret":"ce1f6092de","server":"2510","title":"Pandas"}}}}""")


yqlobj = YQLObj(data_dict)
yqlobj2 = YQLObj({})
yqlobj3 = YQLObj(data_dict2)


class YQLObjTest(TestCase):
    @raises(AttributeError)
    def test_yql_object_one(self):
        """Test that invalid query raises AttributeError"""
        yqlobj.query = 1

    def test_yqlobj_uri(self):
        """Test that the query uri is as expected."""
        self.assertEqual(yqlobj.uri, u"http://query.yahooapis.com/v1/yql?q=select+*+"\
                       "from+flickr.photos.search+where+text%3D%22panda%22+limit+3")

    def test_yqlobj_query(self):
        """Test retrieval of the actual query"""
        self.assertEqual(yqlobj.query, u'select * from flickr.photos.search '\
                                'where text="panda" limit 3')

    def test_yqlobj_count(self):
        """Check we have 3 records"""
        self.assertEqual(yqlobj.count, 3)

    def test_yqlobj_lang(self):
        """Check the lang attr."""
        self.assertEqual(yqlobj.lang, u"en-US")

    def test_yqlobj_results(self):
        """Check the results."""
        expected_results = {u'photo': [
                                {u'isfamily': u'0',
                                 u'title': u'Pandas',
                                 u'farm': u'3',
                                 u'ispublic': u'1',
                                 u'server': u'2510',
                                 u'isfriend': u'0',
                                 u'secret': u'ce1f6092de',
                                 u'owner': u'12346075@N00',
                                 u'id': u'4117944207'},
                                {u'isfamily': u'0',
                                 u'title': u'Pandas',
                                 u'farm': u'3',
                                 u'ispublic': u'1',
                                 u'server': u'2754',
                                 u'isfriend': u'0',
                                 u'secret': u'649632a3e2',
                                 u'owner': u'12346075@N00',
                                 u'id': u'4118710292'},
                                {u'isfamily': u'0',
                                 u'title': u'fuzzy flowers (Kalanchoe tomentosa)',
                                 u'farm': u'3',
                                 u'ispublic': u'1',
                                 u'server': u'2586',
                                 u'isfriend': u'0',
                                 u'secret': u'ec0b508684',
                                 u'owner': u'28451051@N02',
                                 u'id': u'4118698318'}
                            ]}
        self.assertEqual(yqlobj.results, expected_results)

    def test_yqlobj_raw(self):
        """Check the raw attr."""
        self.assertEqual(yqlobj.raw, data_dict.get('query'))

    def test_yqlobj_diagnostics(self):
        """Check the diagnostics"""
        self.assertEqual(yqlobj.diagnostics, data_dict.get('query').get('diagnostics'))

    def test_query_is_none(self):
        """Check query is None with no data."""
        self.assertTrue(yqlobj2.query is None)

    def test_rows(self):
        """Test we can iterate over the rows."""
        stuff = []
        for row in yqlobj.rows:
            stuff.append(row.get('server'))

        self.assertEqual(stuff, [u'2510', u'2754', u'2586'])

    @raises(NotOneError)
    def test_one(self):
        """Test that accessing one result raises exception"""
        yqlobj.one()

    def test_one_with_one_result(self):
        """Test accessing data with one result."""
        res = yqlobj3.one()
        self.assertEqual(res.get("title"), "Pandas")

########NEW FILE########
__FILENAME__ = utils
""""Utility functions"""
import re


METHOD_MAP = (
    ("insert", "POST"),
    ("update", "PUT"),
    ("delete", "POST"),
)
MULTI_PLUS = re.compile(r"\+{2,}")
MULTI_SPACE = re.compile(r" {2,}")


def get_http_method(query):
    """Work out if this should be GET, POST, PUT or DELETE"""
    lower_query = query.strip().lower()

    http_method = "GET"
    for method in METHOD_MAP:
        if method[0] in lower_query:
            http_method = method[1]
            break

    return http_method


def clean_url(url):
    """Cleans up a uri/url"""
    url = url.replace("\n", "")
    url = MULTI_PLUS.sub("+", url)
    return url


def clean_query(query):
    """Cleans up a query"""
    query = query.replace("\n", "")
    query = MULTI_SPACE.sub(" ", query)
    return query

########NEW FILE########
__FILENAME__ = admin
import os
import sys
import re
import json
import time
import subprocess

from util import hook


@hook.command(autohelp=False, permissions=["permissions_users"])
def permissions(inp, bot=None, notice=None):
    """permissions [group] -- lists the users and their permission level who have permissions."""
    permissions = bot.config.get("permissions", [])
    groups = []
    if inp:
        for k in permissions:
            if inp == k:
                groups.append(k)
    else:
        for k in permissions:
            groups.append(k)
    if not groups:
        notice("{} is not a group with permissions".format(inp))
        return None

    for v in groups:
        members = ""
        for value in permissions[v]["users"]:
            members = members + value + ", "
        if members:
            notice("the members in the {} group are..".format(v))
            notice(members[:-2])
        else:
            notice("there are no members in the {} group".format(v))


@hook.command(permissions=["permissions_users"])
def deluser(inp, bot=None, notice=None):
    """deluser [user] [group] -- removes elevated permissions from [user].
    If [group] is specified, they will only be removed from [group]."""
    permissions = bot.config.get("permissions", [])
    inp = inp.split(" ")
    groups = []
    try:
        specgroup = inp[1]
    except IndexError:
        specgroup = None
        for k in permissions:
            groups.append(k)
    else:
        for k in permissions:
            if specgroup == k:
                groups.append(k)
    if not groups:
        notice("{} is not a group with permissions".format(inp[1]))
        return None

    removed = 0
    for v in groups:
        users = permissions[v]["users"]
        for value in users:
            if inp[0] == value:
                users.remove(inp[0])
                removed = 1
                notice("{} has been removed from the group {}".format(inp[0], v))
                json.dump(bot.config, open('config', 'w'), sort_keys=True, indent=2)
    if specgroup:
        if removed == 0:
            notice("{} is not in the group {}".format(inp[0], specgroup))
    else:
        if removed == 0:
            notice("{} is not in any groups".format(inp[0]))


@hook.command(permissions=["permissions_users"])
def adduser(inp, bot=None, notice=None):
    """adduser [user] [group] -- adds elevated permissions to [user].
    [group] must be specified."""
    permissions = bot.config.get("permissions", [])
    inp = inp.split(" ")
    try:
        user = inp[0]
        targetgroup = inp[1]
    except IndexError:
        notice("the group must be specified")
        return None
    if not re.search('.+!.+@.+', user):
        notice("the user must be in the form of \"nick!user@host\"")
        return None
    try:
        users = permissions[targetgroup]["users"]
    except KeyError:
        notice("no such group as {}".format(targetgroup))
        return None
    if user in users:
        notice("{} is already in {}".format(user, targetgroup))
        return None

    users.append(user)
    notice("{} has been added to the group {}".format(user, targetgroup))
    users.sort()
    json.dump(bot.config, open('config', 'w'), sort_keys=True, indent=2)


@hook.command("quit", autohelp=False, permissions=["botcontrol"])
@hook.command(autohelp=False, permissions=["botcontrol"])
def stop(inp, nick=None, conn=None):
    """stop [reason] -- Kills the bot with [reason] as its quit message."""
    if inp:
        conn.cmd("QUIT", ["Killed by {} ({})".format(nick, inp)])
    else:
        conn.cmd("QUIT", ["Killed by {}.".format(nick)])
    time.sleep(5)
    os.execl("./cloudbot", "cloudbot", "stop")


@hook.command(autohelp=False, permissions=["botcontrol"])
def restart(inp, nick=None, conn=None, bot=None):
    """restart [reason] -- Restarts the bot with [reason] as its quit message."""
    for botcon in bot.conns:
        if inp:
            bot.conns[botcon].cmd("QUIT", ["Restarted by {} ({})".format(nick, inp)])
        else:
            bot.conns[botcon].cmd("QUIT", ["Restarted by {}.".format(nick)])
    time.sleep(5)
    #os.execl("./cloudbot", "cloudbot", "restart")
    args = sys.argv[:]
    args.insert(0, sys.executable)
    os.execv(sys.executable, args)


@hook.command(autohelp=False, permissions=["botcontrol"])
def clearlogs(inp, input=None):
    """clearlogs -- Clears the bots log(s)."""
    subprocess.call(["./cloudbot", "clear"])


@hook.command(permissions=["botcontrol"])
def join(inp, conn=None, notice=None):
    """join <channel> -- Joins <channel>."""
    for target in inp.split(" "):
        if not target.startswith("#"):
            target = "#{}".format(target)
        notice("Attempting to join {}...".format(target))
        conn.join(target)


@hook.command(autohelp=False, permissions=["botcontrol"])
def part(inp, conn=None, chan=None, notice=None):
    """part <channel> -- Leaves <channel>.
    If [channel] is blank the bot will leave the
    channel the command was used in."""
    if inp:
        targets = inp
    else:
        targets = chan
    for target in targets.split(" "):
        if not target.startswith("#"):
            target = "#{}".format(target)
        notice("Attempting to leave {}...".format(target))
        conn.part(target)


@hook.command(autohelp=False, permissions=["botcontrol"])
def cycle(inp, conn=None, chan=None, notice=None):
    """cycle <channel> -- Cycles <channel>.
    If [channel] is blank the bot will cycle the
    channel the command was used in."""
    if inp:
        target = inp
    else:
        target = chan
    notice("Attempting to cycle {}...".format(target))
    conn.part(target)
    conn.join(target)


@hook.command(permissions=["botcontrol"])
def nick(inp, notice=None, conn=None):
    """nick <nick> -- Changes the bots nickname to <nick>."""
    if not re.match("^[A-Za-z0-9_|.-\]\[]*$", inp.lower()):
        notice("Invalid username!")
        return
    notice("Attempting to change nick to \"{}\"...".format(inp))
    conn.set_nick(inp)


@hook.command(permissions=["botcontrol"])
def raw(inp, conn=None, notice=None):
    """raw <command> -- Sends a RAW IRC command."""
    notice("Raw command sent.")
    conn.send(inp)


@hook.command(permissions=["botcontrol"])
def say(inp, conn=None, chan=None):
    """say [channel] <message> -- Makes the bot say <message> in [channel].
    If [channel] is blank the bot will say the <message> in the channel
    the command was used in."""
    inp = inp.split(" ")
    if inp[0][0] == "#":
        message = u" ".join(inp[1:])
        out = u"PRIVMSG {} :{}".format(inp[0], message)
    else:
        message = u" ".join(inp[0:])
        out = u"PRIVMSG {} :{}".format(chan, message)
    conn.send(out)


@hook.command("act", permissions=["botcontrol"])
@hook.command(permissions=["botcontrol"])
def me(inp, conn=None, chan=None):
    """me [channel] <action> -- Makes the bot act out <action> in [channel].
    If [channel] is blank the bot will act the <action> in the channel the
    command was used in."""
    inp = inp.split(" ")
    if inp[0][0] == "#":
        message = ""
        for x in inp[1:]:
            message = message + x + " "
        message = message[:-1]
        out = u"PRIVMSG {} :\x01ACTION {}\x01".format(inp[0], message)
    else:
        message = ""
        for x in inp[0:]:
            message = message + x + " "
        message = message[:-1]
        out = u"PRIVMSG {} :\x01ACTION {}\x01".format(chan, message)
    conn.send(out)

########NEW FILE########
__FILENAME__ = attacks
import random

from util import hook


with open("plugins/data/larts.txt") as f:
    larts = [line.strip() for line in f.readlines()
             if not line.startswith("//")]

with open("plugins/data/insults.txt") as f:
    insults = [line.strip() for line in f.readlines()
               if not line.startswith("//")]

with open("plugins/data/flirts.txt") as f:
    flirts = [line.strip() for line in f.readlines()
              if not line.startswith("//")]


@hook.command
def lart(inp, action=None, nick=None, conn=None, notice=None):
    """lart <user> -- LARTs <user>."""
    target = inp.strip()

    if " " in target:
        notice("Invalid username!")
        return

    # if the user is trying to make the bot slap itself, slap them
    if target.lower() == conn.nick.lower() or target.lower() == "itself":
        target = nick

    values = {"user": target}
    phrase = random.choice(larts)

    # act out the message
    action(phrase.format(**values))


@hook.command
def insult(inp, nick=None, action=None, conn=None, notice=None):
    """insult <user> -- Makes the bot insult <user>."""
    target = inp.strip()

    if " " in target:
        notice("Invalid username!")
        return

    if target == conn.nick.lower() or target == "itself":
        target = nick
    else:
        target = inp

    out = 'insults {}... "{}"'.format(target, random.choice(insults))
    action(out)


@hook.command
def flirt(inp, action=None, conn=None, notice=None):
    """flirt <user> -- Make the bot flirt with <user>."""
    target = inp.strip()

    if " " in target:
        notice("Invalid username!")
        return

    if target == conn.nick.lower() or target == "itself":
        target = 'itself'
    else:
        target = inp

    out = 'flirts with {}... "{}"'.format(target, random.choice(flirts))
    action(out)

########NEW FILE########
__FILENAME__ = brainfuck
"""brainfuck interpreter adapted from (public domain) code at
http://brainfuck.sourceforge.net/brain.py"""

import re
import random

from util import hook


BUFFER_SIZE = 5000
MAX_STEPS = 1000000


@hook.command('brainfuck')
@hook.command
def bf(inp):
    """bf <prog> -- Executes <prog> as Brainfuck code."""

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
            memory[mp] += 1 % 256
        elif c == '-':
            memory[mp] -= 1 % 256
        elif c == '>':
            mp += 1
            if mp > rightmost:
                rightmost = mp
                if mp >= len(memory):
                    # no restriction on memory growth!
                    memory.extend([0] * BUFFER_SIZE)
        elif c == '<':
            mp -= 1 % len(memory)
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
            output += '[exceeded {} iterations]'.format(MAX_STEPS)
            break

    stripped_output = re.sub(r'[\x00-\x1F]', '', output)

    if stripped_output == '':
        if output != '':
            return 'no printable output'
        return 'no output'

    return stripped_output[:430].decode('utf8', 'ignore')

########NEW FILE########
__FILENAME__ = cake
# coding=utf-8
import re
import random

from util import hook

cakes = ['Chocolate', 'Ice Cream', 'Angel', 'Boston Cream', 'Birthday', 'Bundt', 'Carrot', 'Coffee', 'Devils', 'Fruit', 'Gingerbread', 'Pound', 'Red Velvet', 'Stack', 'Welsh', 'Yokan']


@hook.command
def cake(inp, action=None):
    """cake <user> - Gives <user> an awesome cake."""
    inp = inp.strip()

    if not re.match("^[A-Za-z0-9_|.-\]\[]*$", inp.lower()):
        return "I can't give an awesome cake to that user!"

    cake_type = random.choice(cakes)
    size = random.choice(['small', 'little', 'mid-sized', 'medium-sized', 'large', 'gigantic'])
    flavor = random.choice(['tasty', 'delectable', 'delicious', 'yummy', 'toothsome', 'scrumptious', 'luscious'])
    method = random.choice(['makes', 'gives', 'gets', 'buys'])
    side_dish = random.choice(['glass of chocolate milk', 'bowl of ice cream', 'jar of cookies', 'bowl of chocolate sauce'])

    action("{} {} a {} {} {} cake and serves it with a small {}!".format(method, inp, flavor, size, cake_type, side_dish))

########NEW FILE########
__FILENAME__ = choose
import re
import random

from util import hook


@hook.command
def choose(inp):
    """choose <choice1>, [choice2], [choice3], [choice4], ... --
    Randomly picks one of the given choices."""

    c = re.findall(r'([^,]+)', inp)
    if len(c) == 1:
        c = re.findall(r'(\S+)', inp)
        if len(c) == 1:
            return 'The decision is up to you!'

    return random.choice(c).strip()

########NEW FILE########
__FILENAME__ = coin
import random

from util import hook


@hook.command(autohelp=False)
def coin(inp, action=None):
    """coin [amount] -- Flips [amount] of coins."""

    if inp:
        try:
            amount = int(inp)
        except (ValueError, TypeError):
            return "Invalid input!"
    else:
        amount = 1

    if amount == 1:
        action("flips a coin and gets {}.".format(random.choice(["heads", "tails"])))
    elif amount == 0:
        action("makes a coin flipping motion with its hands.")
    else:
        heads = int(random.normalvariate(.5 * amount, (.75 * amount) ** .5))
        tails = amount - heads
        action("flips {} coins and gets {} heads and {} tails.".format(amount, heads, tails))

########NEW FILE########
__FILENAME__ = cookie
"""
cookie.py: A plugin to serve cookies to users

(c) 2014 Techman <michael@techmansworld.com>

Plugin produced under guidance of the cake plugin. Thanks!
"""
# coding=utf-8
import re
import random

from util import hook

cookies = ['Chocolate Chip', 'Oatmeal', 'Sugar', 'Oatmeal Rasin', 'Macadamia Nut', 'Jam Thumbprint', 'Medican Wedding', 'Biscotti', 'Oatmeal Cranberry', 'Chocolate Fudge', 'Peanut Butter', 'Pumpkin', 'Lemon Bar', 'Chocolate Oatmeal Fudge', 'Toffee Peanut', 'Danish Sugar', 'Tripple Chocolate', 'Oreo']

@hook.command
def cookie(inp, action=None):
    """cookie <user> - Gives <user> a cookie"""
    inp = inp.strip()

    if not re.match("^[A-Za-z0-9_|.-\]\[]*$", inp.lower()):
        return "I can't give a cookie to that user!"

    cookie_type = random.choice(cookies)
    size = random.choice(['small', 'little', 'medium-sized', 'large', 'gigantic'])
    flavor = random.choice(['tasty', 'delectable', 'delicious', 'yummy', 'toothsome', 'scrumptious', 'luscious'])
    method = random.choice(['makes', 'gives', 'gets', 'buys'])
    side_dish = random.choice(['glass of milk', 'bowl of ice cream', 'bowl of chocolate sauce'])

    action("{} {} a {} {} {} cookie and serves it with a {}!".format(method, inp, flavor, size, cookie_type, side_dish))

########NEW FILE########
__FILENAME__ = core_ctcp
import time

from util import hook


# CTCP responses
@hook.regex(r'^\x01VERSION\x01$')
def ctcp_version(inp, notice=None):
    notice('\x01VERSION: CloudBot - http://git.io/cloudbotirc')


@hook.regex(r'^\x01PING\x01$')
def ctcp_ping(inp, notice=None):
    notice('\x01PING: PONG')


@hook.regex(r'^\x01TIME\x01$')
def ctcp_time(inp, notice=None):
    notice('\x01TIME: The time is: {}'.format(time.strftime("%r", time.localtime())))

########NEW FILE########
__FILENAME__ = core_misc
import socket
import time
import re

from util import hook


socket.setdefaulttimeout(10)

nick_re = re.compile(":(.+?)!")


# Auto-join on Invite (Configurable, defaults to True)
@hook.event('INVITE')
def invite(paraml, conn=None):
    invite_join = conn.conf.get('invite_join', True)
    if invite_join:
        conn.join(paraml[-1])


# Identify to NickServ (or other service)
@hook.event('004')
def onjoin(paraml, conn=None, bot=None):
    nickserv_password = conn.conf.get('nickserv_password', '')
    nickserv_name = conn.conf.get('nickserv_name', 'nickserv')
    nickserv_account_name = conn.conf.get('nickserv_user', '')
    nickserv_command = conn.conf.get('nickserv_command', 'IDENTIFY')
    if nickserv_password:
        if nickserv_password in bot.config['censored_strings']:
            bot.config['censored_strings'].remove(nickserv_password)
        if nickserv_account_name:
            conn.msg(nickserv_name, "{} {} {}".format(nickserv_command, nickserv_account_name, nickserv_password))
        else:
            conn.msg(nickserv_name, "{} {}".format(nickserv_command, nickserv_password))
        bot.config['censored_strings'].append(nickserv_password)
        time.sleep(1)

# Set bot modes
    mode = conn.conf.get('mode')
    if mode:
        conn.cmd('MODE', [conn.nick, mode])

# Join config-defined channels
    for channel in conn.channels:
        conn.join(channel)
        time.sleep(1)

    print "Bot ready."


@hook.event("KICK")
def onkick(paraml, conn=None, chan=None):
    # if the bot has been kicked, remove from the channel list
    if paraml[1] == conn.nick:
        conn.channels.remove(chan)
        auto_rejoin = conn.conf.get('auto_rejoin', False)
        if auto_rejoin:
            conn.join(paraml[0])


@hook.event("NICK")
def onnick(paraml, conn=None, raw=None):
    old_nick = nick_re.search(raw).group(1)
    new_nick = str(paraml[0])
    if old_nick == conn.nick:
        conn.nick = new_nick
        print "Bot nick changed from '{}' to '{}'.".format(old_nick, new_nick)


@hook.singlethread
@hook.event('004')
def keep_alive(paraml, conn=None):
    keepalive = conn.conf.get('keep_alive', False)
    if keepalive:
        while True:
            conn.cmd('PING', [conn.nick])
            time.sleep(60)

########NEW FILE########
__FILENAME__ = core_sieve
import re
from fnmatch import fnmatch

from util import hook


@hook.sieve
def sieve_suite(bot, input, func, kind, args):
    if input.command == 'PRIVMSG' and \
            input.nick.endswith('bot') and args.get('ignorebots', True):
        return None

    if kind == "command":
        if input.trigger in bot.config.get('disabled_commands', []):
            return None

    fn = re.match(r'^plugins.(.+).py$', func._filename)
    disabled = bot.config.get('disabled_plugins', [])
    if fn and fn.group(1).lower() in disabled:
        return None

    acl = bot.config.get('acls', {}).get(func.__name__)
    if acl:
        if 'deny-except' in acl:
            allowed_channels = map(unicode.lower, acl['deny-except'])
            if input.chan.lower() not in allowed_channels:
                return None
        if 'allow-except' in acl:
            denied_channels = map(unicode.lower, acl['allow-except'])
            if input.chan.lower() in denied_channels:
                return None

    # shim so plugins using the old "adminonly" permissions format still work
    if args.get('adminonly', False):
        args["permissions"] = ["adminonly"]

    if args.get('permissions', False):
        groups = bot.config.get("permissions", [])

        allowed_permissions = args.get('permissions', [])

        mask = input.mask.lower()

        # loop over every group
        for key, group in groups.iteritems():
            # loop over every permission the command allows
            for permission in allowed_permissions:
                # see if the group has that permission
                if permission in group["perms"]:
                    # if so, check it
                    group_users = [_mask.lower() for _mask in group["users"]]
                    for pattern in group_users:
                        if fnmatch(mask, pattern):
                            print "Allowed group {}.".format(group)
                            return input

        input.notice("Sorry, you are not allowed to use this command.")
        return None

    return input

########NEW FILE########
__FILENAME__ = correction
from util import hook

import re

CORRECTION_RE = r'^(s|S)/.*/.*/?\S*$'


@hook.regex(CORRECTION_RE)
def correction(match, input=None, conn=None, message=None):
    split = input.msg.split("/")

    if len(split) == 4:
        nick = split[3].lower()
    else:
        nick = None

    find = split[1]
    replace = split[2]

    for item in conn.history[input.chan].__reversed__():
        name, timestamp, msg = item
        if msg.startswith("s/"):
            # don't correct corrections, it gets really confusing
            continue
        if nick:
            if nick != name.lower():
                continue
        if find in msg:
            if "\x01ACTION" in msg:
                msg = msg.replace("\x01ACTION ", "/me ").replace("\x01", "")
            message(u"Correction, <{}> {}".format(name, msg.replace(find, "\x02" + replace + "\x02")))
            return
        else:
            continue

    return u"Did not find {} in any recent messages.".format(find)


########NEW FILE########
__FILENAME__ = cryptocoins
from util import http, hook

## CONSTANTS

exchanges = {
    "blockchain": {
        "api_url": "https://blockchain.info/ticker",
        "func": lambda data: u"Blockchain // Buy: \x0307${:,.2f}\x0f -"
                             u" Sell: \x0307${:,.2f}\x0f".format(data["USD"]["buy"], data["USD"]["sell"])
    },
    "coinbase": {
        "api_url": "https://coinbase.com/api/v1/prices/spot_rate",
        "func": lambda data: u"Coinbase // Current: \x0307${:,.2f}\x0f".format(float(data['amount']))
    },
    "bitpay": {
        "api_url": "https://bitpay.com/api/rates",
        "func": lambda data: u"Bitpay // Current: \x0307${:,.2f}\x0f".format(data[0]['rate'])
    },
    "bitstamp": {
        "api_url": "https://www.bitstamp.net/api/ticker/",
        "func": lambda data: u"BitStamp // Current: \x0307${:,.2f}\x0f - High: \x0307${:,.2f}\x0f -"
                             u" Low: \x0307${:,.2f}\x0f - Volume: {:,.2f} BTC".format(float(data['last']),
                                                                                      float(data['high']),
                                                                                      float(data['low']),
                                                                                      float(data['volume']))
    }
}


## HOOK FUNCTIONS

@hook.command("btc", autohelp=False)
@hook.command(autohelp=False)
def bitcoin(inp):
    """bitcoin <exchange> -- Gets current exchange rate for bitcoins from several exchanges, default is Blockchain.
    Supports MtGox, Bitpay, Coinbase and BitStamp."""
    inp = inp.lower()

    if inp:
        if inp in exchanges:
            exchange = exchanges[inp]
        else:
            return "Invalid Exchange"
    else:
        exchange = exchanges["blockchain"]

    data = http.get_json(exchange["api_url"])
    func = exchange["func"]
    return func(data)


@hook.command("ltc", autohelp=False)
@hook.command(autohelp=False)
def litecoin(inp, message=None):
    """litecoin -- gets current exchange rate for litecoins from BTC-E"""
    data = http.get_json("https://btc-e.com/api/2/ltc_usd/ticker")
    ticker = data['ticker']
    message("Current: \x0307${:,.2f}\x0f - High: \x0307${:,.2f}\x0f"
            " - Low: \x0307${:,.2f}\x0f - Volume: {:,.2f} LTC".format(ticker['buy'], ticker['high'], ticker['low'],
                                                                      ticker['vol_cur']))

########NEW FILE########
__FILENAME__ = cypher
import base64

from util import hook


def encode(key, clear):
    enc = []
    for i in range(len(clear)):
        key_c = key[i % len(key)]
        enc_c = chr((ord(clear[i]) + ord(key_c)) % 256)
        enc.append(enc_c)
    return base64.urlsafe_b64encode("".join(enc))


def decode(key, enc):
    dec = []
    enc = base64.urlsafe_b64decode(enc.encode('ascii', 'ignore'))
    for i in range(len(enc)):
        key_c = key[i % len(key)]
        dec_c = chr((256 + ord(enc[i]) - ord(key_c)) % 256)
        dec.append(dec_c)
    return "".join(dec)


@hook.command
def cypher(inp):
    """cypher <pass> <string> -- Cyphers <string> with <password>."""

    passwd = inp.split(" ")[0]
    inp = " ".join(inp.split(" ")[1:])
    return encode(passwd, inp)


@hook.command
def decypher(inp):
    """decypher <pass> <string> -- Decyphers <string> with <password>."""
    passwd = inp.split(" ")[0]
    inp = " ".join(inp.split(" ")[1:])
    return decode(passwd, inp)

########NEW FILE########
__FILENAME__ = dice
# Written by Scaevolus, updated by Lukeroge

import re
import random

from util import hook


whitespace_re = re.compile(r'\s+')
valid_diceroll = r'^([+-]?(?:\d+|\d*d(?:\d+|F))(?:[+-](?:\d+|\d*d(?:\d+|' \
                 'F)))*)( .+)?$'
valid_diceroll_re = re.compile(valid_diceroll, re.I)
sign_re = re.compile(r'[+-]?(?:\d*d)?(?:\d+|F)', re.I)
split_re = re.compile(r'([\d+-]*)d?(F|\d*)', re.I)


def n_rolls(count, n):
    """roll an n-sided die count times"""
    if n == "F":
        return [random.randint(-1, 1) for x in xrange(min(count, 100))]
    if n < 2:  # it's a coin
        if count < 100:
            return [random.randint(0, 1) for x in xrange(count)]
        else:  # fake it
            return [int(random.normalvariate(.5 * count, (.75 * count) ** .5))]
    else:
        if count < 100:
            return [random.randint(1, n) for x in xrange(count)]
        else:  # fake it
            return [int(random.normalvariate(.5 * (1 + n) * count,
                                             (((n + 1) * (2 * n + 1) / 6. -
                                               (.5 * (1 + n)) ** 2) * count) ** .5))]


@hook.command('roll')
#@hook.regex(valid_diceroll, re.I)
@hook.command
def dice(inp):
    """dice <dice roll> -- Simulates dice rolls. Example of <dice roll>:
    'dice 2d20-d5+4 roll 2'. D20s, subtract 1D5, add 4"""

    try:  # if inp is a re.match object...
        (inp, desc) = inp.groups()
    except AttributeError:
        (inp, desc) = valid_diceroll_re.match(inp).groups()

    if "d" not in inp:
        return

    spec = whitespace_re.sub('', inp)
    if not valid_diceroll_re.match(spec):
        return "Invalid dice roll"
    groups = sign_re.findall(spec)

    total = 0
    rolls = []

    for roll in groups:
        count, side = split_re.match(roll).groups()
        count = int(count) if count not in " +-" else 1
        if side.upper() == "F":  # fudge dice are basically 1d3-2
            for fudge in n_rolls(count, "F"):
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
                    d = n_rolls(count, side)
                    rolls += map(str, d)
                    total += sum(d)
                else:
                    d = n_rolls(-count, side)
                    rolls += [str(-x) for x in d]
                    total -= sum(d)
            except OverflowError:
                # I have never seen this happen. If you make this happen, you win a cookie
                return "Thanks for overflowing a float, jerk >:["

    if desc:
        return "{}: {} ({})".format(desc.strip(), total, ", ".join(rolls))
    else:
        return "{} ({})".format(total, ", ".join(rolls))

########NEW FILE########
__FILENAME__ = dictionary
# Plugin by GhettoWizard and Scaevolus
import re

from util import hook
from util import http


@hook.command('dictionary')
@hook.command
def define(inp):
    """define <word> -- Fetches definition of <word>."""

    url = 'http://ninjawords.com/'

    h = http.get_html(url + http.quote_plus(inp))

    definition = h.xpath('//dd[@class="article"] | '
                         '//div[@class="definition"] |'
                         '//div[@class="example"]')

    if not definition:
        return u'No results for {} :('.format(inp)

    def format_output(show_examples):
        result = u'{}: '.format(h.xpath('//dt[@class="title-word"]/a/text()')[0])

        correction = h.xpath('//span[@class="correct-word"]/text()')
        if correction:
            result = 'Definition for "{}": '.format(correction[0])

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
                result += u' '.join(u'{}. {}'.format(n + 1, section)
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
    """etymology <word> -- Retrieves the etymology of <word>."""

    url = 'http://www.etymonline.com/index.php'

    h = http.get_html(url, term=inp)

    etym = h.xpath('//dl')

    if not etym:
        return u'No etymology found for {} :('.format(inp)

    etym = etym[0].text_content()

    etym = ' '.join(etym.split())

    if len(etym) > 400:
        etym = etym[:etym.rfind(' ', 0, 400)] + ' ...'

    return etym

########NEW FILE########
__FILENAME__ = domainr
from util import hook, http


@hook.command
def domainr(inp):
    """domainr <domain> - Use domain.nr's API to search for a domain, and similar domains."""
    try:
        data = http.get_json('http://domai.nr/api/json/search?q=' + inp)
    except (http.URLError, http.HTTPError) as e:
        return "Unable to get data for some reason. Try again later."
    if data['query'] == "":
        return "An error occurred: {status} - {message}".format(**data['error'])
    domains = ""
    for domain in data['results']:
        domains += ("\x034" if domain['availability'] == "taken" else (
                    "\x033" if domain['availability'] == "available" else "\x031")) + domain['domain'] + "\x0f" + domain[
                    'path'] + ", "
    return "Domains: " + domains

########NEW FILE########
__FILENAME__ = down
import urlparse

from util import hook, http


@hook.command
def down(inp):
    """down <url> -- Checks if the site at <url> is up or down."""

    if 'http://' not in inp:
        inp = 'http://' + inp

    inp = 'http://' + urlparse.urlparse(inp).netloc

    # http://mail.python.org/pipermail/python-list/2006-December/589854.html
    try:
        http.get(inp, get_method='HEAD')
        return '{} seems to be up'.format(inp)
    except http.URLError:
        return '{} seems to be down'.format(inp)

########NEW FILE########
__FILENAME__ = drama
import re

from util import hook, http, text


api_url = "http://encyclopediadramatica.se/api.php?action=opensearch"
ed_url = "http://encyclopediadramatica.se/"


@hook.command
def drama(inp):
    """drama <phrase> -- Gets the first paragraph of
    the Encyclopedia Dramatica article on <phrase>."""

    j = http.get_json(api_url, search=inp)

    if not j[1]:
        return "No results found."
    article_name = j[1][0].replace(' ', '_').encode('utf8')

    url = ed_url + http.quote(article_name, '')
    page = http.get_html(url)

    for p in page.xpath('//div[@id="bodyContent"]/p'):
        if p.text_content():
            summary = " ".join(p.text_content().splitlines())
            summary = re.sub("\[\d+\]", "", summary)
            summary = text.truncate_str(summary, 220)
            return "{} :: {}".format(summary, url)

    return "Unknown Error."

########NEW FILE########
__FILENAME__ = eightball
import random

from util import hook, text


color_codes = {
    "<r>": "\x02\x0305",
    "<g>": "\x02\x0303",
    "<y>": "\x02"
}

with open("plugins/data/8ball_responses.txt") as f:
    responses = [line.strip() for line in
                 f.readlines() if not line.startswith("//")]


@hook.command('8ball')
def eightball(inp, action=None):
    """8ball <question> -- The all knowing magic eight ball,
    in electronic form. Ask and it shall be answered!"""

    magic = text.multiword_replace(random.choice(responses), color_codes)
    action("shakes the magic 8 ball... {}".format(magic))

########NEW FILE########
__FILENAME__ = encrypt
import os
import base64
import json
import hashlib

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2

from util import hook


# helper functions to pad and unpad a string to a specified block size
# <http://stackoverflow.com/questions/12524994/encrypt-decrypt-using-pycrypto-aes-256>
BS = AES.block_size
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s: s[0:-ord(s[-1])]

# helper functions to encrypt and encode a string with AES and base64
encode_aes = lambda c, s: base64.b64encode(c.encrypt(pad(s)))
decode_aes = lambda c, s: unpad(c.decrypt(base64.b64decode(s)))

db_ready = False


def db_init(db):
    """check to see that our db has the the encryption table."""
    global db_ready
    if not db_ready:
        db.execute("create table if not exists encryption(encrypted, iv, "
                   "primary key(encrypted))")
        db.commit()
        db_ready = True


def get_salt(bot):
    """generate an encryption salt if none exists, then returns the salt"""
    if not bot.config.get("random_salt", False):
        bot.config["random_salt"] = hashlib.md5(os.urandom(16)).hexdigest()
        json.dump(bot.config, open('config', 'w'), sort_keys=True, indent=2)
    return bot.config["random_salt"]


@hook.command
def encrypt(inp, bot=None, db=None, notice=None):
    """encrypt <pass> <string> -- Encrypts <string> with <pass>. (<string> can only be decrypted using this bot)"""
    db_init(db)

    split = inp.split(" ")

    # if there is only one argument, return the help message
    if len(split) == 1:
        notice(encrypt.__doc__)
        return

    # generate the key from the password and salt
    password = split[0]
    salt = get_salt(bot)
    key = PBKDF2(password, salt)

    # generate the IV and encode it to store in the database
    iv = Random.new().read(AES.block_size)
    iv_encoded = base64.b64encode(iv)

    # create the AES cipher and encrypt/encode the text with it
    text = " ".join(split[1:])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encoded = encode_aes(cipher, text)

    # store the encoded text and IV in the DB for decoding later
    db.execute("insert or replace into encryption(encrypted, iv)"
               "values(?,?)", (encoded, iv_encoded))
    db.commit()

    return encoded


@hook.command
def decrypt(inp, bot=None, db=None, notice=None):
    """decrypt <pass> <string> -- Decrypts <string> with <pass>. (can only decrypt strings encrypted on this bot)"""
    if not db_ready:
        db_init(db)

    split = inp.split(" ")

    # if there is only one argument, return the help message
    if len(split) == 1:
        notice(decrypt.__doc__)
        return

    # generate the key from the password and salt
    password = split[0]
    salt = get_salt(bot)
    key = PBKDF2(password, salt)

    text = " ".join(split[1:])

    # get the encoded IV from the database and decode it
    iv_encoded = db.execute("select iv from encryption where"
                            " encrypted=?", (text,)).fetchone()[0]
    iv = base64.b64decode(iv_encoded)

    # create AES cipher, decode text, decrypt text, and unpad it
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return decode_aes(cipher, text)

########NEW FILE########
__FILENAME__ = fact
from util import hook, http, web


@hook.command(autohelp=False)
def fact(inp):
    """fact -- Gets a random fact from OMGFACTS."""

    attempts = 0

    # all of this is because omgfacts is fail
    while True:
        try:
            soup = http.get_soup('http://www.omg-facts.com/random')
        except:
            if attempts > 2:
                return "Could not find a fact!"
            else:
                attempts += 1
                continue

        response = soup.find('a', {'class': 'surprise'})
        link = response['href']
        fact_data = ''.join(response.find(text=True))

        if fact_data:
            fact_data = fact_data.strip()
            break
        else:
            if attempts > 2:
                return "Could not find a fact!"
            else:
                attempts += 1
                continue

    url = web.try_isgd(link)

    return "{} - {}".format(fact_data, url)

########NEW FILE########
__FILENAME__ = factoids
# Written by Scaevolus 2010
import string
import re

from util import hook, http, text, pyexec


re_lineends = re.compile(r'[\r\n]*')

db_ready = []

# some simple "shortcodes" for formatting purposes
shortcodes = {
    '[b]': '\x02',
    '[/b]': '\x02',
    '[u]': '\x1F',
    '[/u]': '\x1F',
    '[i]': '\x16',
    '[/i]': '\x16'}


def db_init(db, conn):
    global db_ready
    if not conn.name in db_ready:
        db.execute("create table if not exists mem(word, data, nick,"
                   " primary key(word))")
        db.commit()
        db_ready.append(conn.name)


def get_memory(db, word):
    row = db.execute("select data from mem where word=lower(?)",
                     [word]).fetchone()
    if row:
        return row[0]
    else:
        return None


@hook.command("r", permissions=["addfactoid"])
@hook.command(permissions=["addfactoid"])
def remember(inp, nick='', db=None, notice=None, conn=None):
    """remember <word> [+]<data> -- Remembers <data> with <word>. Add +
    to <data> to append."""
    db_init(db, conn)

    append = False

    inp = string.replace(inp, "\\n", "\n")

    try:
        word, data = inp.split(None, 1)
    except ValueError:
        return remember.__doc__

    old_data = get_memory(db, word)

    if data.startswith('+') and old_data:
        append = True
        # remove + symbol
        new_data = data[1:]
        # append new_data to the old_data
        if len(new_data) > 1 and new_data[1] in (string.punctuation + ' '):
            data = old_data + new_data
        else:
            data = old_data + ' ' + new_data

    db.execute("replace into mem(word, data, nick) values"
               " (lower(?),?,?)", (word, data, nick))
    db.commit()

    if old_data:
        if append:
            notice(u"Appending \x02{}\x02 to \x02{}\x02. Type ?{} to see it.".format(new_data, old_data, word))
        else:
            notice(u'Remembering \x02{}\x02 for \x02{}\x02. Type ?{} to see it.'.format(data, word, word))
            notice(u'Previous data was \x02{}\x02'.format(old_data))
    else:
        notice(u'Remembering \x02{}\x02 for \x02{}\x02. Type ?{} to see it.'.format(data, word, word))


@hook.command("f", permissions=["delfactoid"])
@hook.command(permissions=["delfactoid"])
def forget(inp, db=None, notice=None, conn=None):
    """forget <word> -- Forgets a remembered <word>."""

    db_init(db, conn)
    data = get_memory(db, inp)

    if data:
        db.execute("delete from mem where word=lower(?)",
                   [inp])
        db.commit()
        notice(u'"%s" has been forgotten.' % data.replace('`', "'"))
        return
    else:
        notice("I don't know about that.")
        return


@hook.command
def info(inp, notice=None, db=None, conn=None):
    """info <factoid> -- Shows the source of a factoid."""

    db_init(db, conn)

    # attempt to get the factoid from the database
    data = get_memory(db, inp.strip())

    if data:
        notice(data)
    else:
        notice("Unknown Factoid.")


@hook.regex(r'^\? ?(.+)')
def factoid(inp, message=None, db=None, bot=None, action=None, conn=None, input=None):
    """?<word> -- Shows what data is associated with <word>."""
    try:
        prefix_on = bot.config["plugins"]["factoids"].get("prefix", False)
    except KeyError:
        prefix_on = False

    db_init(db, conn)

    # split up the input
    split = inp.group(1).strip().split(" ")
    factoid_id = split[0]

    if len(split) >= 1:
        arguments = " ".join(split[1:])
    else:
        arguments = ""

    data = get_memory(db, factoid_id)

    if data:
        # factoid preprocessors
        if data.startswith("<py>"):
            code = data[4:].strip()
            variables = u'input="""{}"""; nick="{}"; chan="{}"; bot_nick="{}";'.format(arguments.replace('"', '\\"'),
                                                                                      input.nick, input.chan,
                                                                                      input.conn.nick)
            result = pyexec.eval_py(variables + code)
        else:
            result = data

        # factoid postprocessors
        result = text.multiword_replace(result, shortcodes)

        if result.startswith("<act>"):
            result = result[5:].strip()
            action(result)
        elif result.startswith("<url>"):
            url = result[5:].strip()
            try:
                message(http.get(url))
            except http.HttpError:
                message("Could not fetch URL.")
        else:
            if prefix_on:
                message(u"\x02[{}]:\x02 {}".format(factoid_id, result))
            else:
                message(result)

@hook.command(autoHelp=False, permissions=["listfactoids"])
def listfactoids(inp, db=None, conn=None, reply=None):
    db_init(db, conn)
    text = False
    for word in db.execute("select word from mem").fetchall():
        if not text:
            text = word[0]
        else:
            text += u", {}".format(word[0])
        if len(text) > 400:
            reply(text.rsplit(u', ', 1)[0])
            text = word[0]
    return text

########NEW FILE########
__FILENAME__ = fishbans
from urllib import quote_plus

from util import hook, http


api_url = "http://api.fishbans.com/stats/{}/"


@hook.command("bans")
@hook.command
def fishbans(inp):
    """fishbans <user> -- Gets information on <user>s minecraft bans from fishbans"""
    user = inp.strip()

    try:
        request = http.get_json(api_url.format(quote_plus(user)))
    except (http.HTTPError, http.URLError) as e:
        return "Could not fetch ban data from the Fishbans API: {}".format(e)

    if not request["success"]:
        return "Could not fetch ban data for {}.".format(user)

    user_url = "http://fishbans.com/u/{}/".format(user)
    ban_count = request["stats"]["totalbans"]

    return "The user \x02{}\x02 has \x02{}\x02 ban(s). See detailed info " \
           "at {}".format(user, ban_count, user_url)


@hook.command
def bancount(inp):
    """bancount <user> -- Gets a count of <user>s minecraft bans from fishbans"""
    user = inp.strip()

    try:
        request = http.get_json(api_url.format(quote_plus(user)))
    except (http.HTTPError, http.URLError) as e:
        return "Could not fetch ban data from the Fishbans API: {}".format(e)

    if not request["success"]:
        return "Could not fetch ban data for {}.".format(user)

    user_url = "http://fishbans.com/u/{}/".format(user)
    services = request["stats"]["service"]

    out = []
    for service, ban_count in services.items():
        if ban_count != 0:
            out.append("{}: \x02{}\x02".format(service, ban_count))
        else:
            pass

    if not out:
        return "The user \x02{}\x02 has no bans.".format(user)
    else:
        return "Bans for \x02{}\x02: ".format(user) + ", ".join(out) + ". More info " \
               "at {}".format(user_url)

########NEW FILE########
__FILENAME__ = fmylife
from util import hook, http

fml_cache = []


def refresh_cache():
    """ gets a page of random FMLs and puts them into a dictionary """
    soup = http.get_soup('http://www.fmylife.com/random/')

    for e in soup.find_all('div', {'class': 'post article'}):
        fml_id = int(e['id'])
        text = ''.join(e.find('p').find_all(text=True))
        fml_cache.append((fml_id, text))

# do an initial refresh of the cache
refresh_cache()


@hook.command(autohelp=False)
def fml(inp, reply=None):
    """fml -- Gets a random quote from fmyfife.com."""

    # grab the last item in the fml cache and remove it
    fml_id, text = fml_cache.pop()
    # reply with the fml we grabbed
    reply('(#{}) {}'.format(fml_id, text))
    # refresh fml cache if its getting empty
    if len(fml_cache) < 3:
        refresh_cache()

########NEW FILE########
__FILENAME__ = fortune
import random

from util import hook


with open("plugins/data/fortunes.txt") as f:
    fortunes = [line.strip() for line in f.readlines()
                if not line.startswith("//")]


@hook.command(autohelp=False)
def fortune(inp):
    """fortune -- Fortune cookies on demand."""
    return random.choice(fortunes)

########NEW FILE########
__FILENAME__ = geoip
import os.path
import json
import gzip
from StringIO import StringIO

import pygeoip

from util import hook, http


# load region database
with open("./plugins/data/geoip_regions.json", "rb") as f:
    regions = json.loads(f.read())

if os.path.isfile(os.path.abspath("./plugins/data/GeoLiteCity.dat")):
    # initialise geolocation database
    geo = pygeoip.GeoIP(os.path.abspath("./plugins/data/GeoLiteCity.dat"))
else:
    download = http.get("http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz")
    string_io = StringIO(download)
    geoip_file = gzip.GzipFile(fileobj=string_io, mode='rb')

    output = open(os.path.abspath("./plugins/data/GeoLiteCity.dat"), 'wb')
    output.write(geoip_file.read())
    output.close()

    geo = pygeoip.GeoIP(os.path.abspath("./plugins/data/GeoLiteCity.dat"))


@hook.command
def geoip(inp):
    """geoip <host/ip> -- Gets the location of <host/ip>"""

    try:
        record = geo.record_by_name(inp)
    except:
        return "Sorry, I can't locate that in my database."

    data = {}

    if "region_name" in record:
        # we try catching an exception here because the region DB is missing a few areas
        # it's a lazy patch, but it should do the job
        try:
            data["region"] = ", " + regions[record["country_code"]][record["region_name"]]
        except:
            data["region"] = ""
    else:
        data["region"] = ""

    data["cc"] = record["country_code"] or "N/A"
    data["country"] = record["country_name"] or "Unknown"
    data["city"] = record["city"] or "Unknown"
    return u"\x02Country:\x02 {country} ({cc}), \x02City:\x02 {city}{region}".format(**data)

########NEW FILE########
__FILENAME__ = github
import json
import urllib2

from util import hook, http


shortcuts = {"cloudbot": "ClouDev/CloudBot"}


def truncate(msg):
    nmsg = msg.split()
    out = None
    x = 0
    for i in nmsg:
        if x <= 7:
            if out:
                out = out + " " + nmsg[x]
            else:
                out = nmsg[x]
        x += 1
    if x <= 7:
        return out
    else:
        return out + "..."


@hook.command
def ghissues(inp):
    """ghissues username/repo [number] - Get specified issue summary, or open issue count """
    args = inp.split(" ")
    try:
        if args[0] in shortcuts:
            repo = shortcuts[args[0]]
        else:
            repo = args[0]
        url = "https://api.github.com/repos/{}/issues".format(repo)
    except IndexError:
        return "Invalid syntax. .github issues username/repo [number]"
    try:
        url += "/%s" % args[1]
        number = True
    except IndexError:
        number = False
    try:
        data = json.loads(http.open(url).read())
        print url
        if not number:
            try:
                data = data[0]
            except IndexError:
                print data
                return "Repo has no open issues"
    except ValueError:
        return "Invalid data returned. Check arguments (.github issues username/repo [number]"
    fmt = "Issue: #%s (%s) by %s: %s | %s %s"  # (number, state, user.login, title, truncate(body), gitio.gitio(data.url))
    fmt1 = "Issue: #%s (%s) by %s: %s %s"  # (number, state, user.login, title, gitio.gitio(data.url))
    number = data["number"]
    if data["state"] == "open":
        state = u"\x033\x02OPEN\x02\x0f"
    else:
        state = u"\x034\x02CLOSED\x02\x0f by {}".format(data["closed_by"]["login"])
    user = data["user"]["login"]
    title = data["title"]
    summary = truncate(data["body"])
    gitiourl = gitio(data["html_url"])
    if "Failed to get URL" in gitiourl:
        gitiourl = gitio(data["html_url"] + " " + repo.split("/")[1] + number)
    if summary == "":
        return fmt1 % (number, state, user, title, gitiourl)
    else:
        return fmt % (number, state, user, title, summary, gitiourl)


@hook.command
def gitio(inp):
    """gitio <url> [code] -- Shorten Github URLs with git.io.  [code] is
    a optional custom short code."""
    split = inp.split(" ")
    url = split[0]

    try:
        code = split[1]
    except:
        code = None

    # if the first 8 chars of "url" are not "https://" then append
    # "https://" to the url, also convert "http://" to "https://"
    if url[:8] != "https://":
        if url[:7] != "http://":
            url = "https://" + url
        else:
            url = "https://" + url[7:]
    url = 'url=' + str(url)
    if code:
        url = url + '&code=' + str(code)
    req = urllib2.Request(url='http://git.io', data=url)

    # try getting url, catch http error
    try:
        f = urllib2.urlopen(req)
    except urllib2.HTTPError:
        return "Failed to get URL!"
    urlinfo = str(f.info())

    # loop over the rows in urlinfo and pick out location and
    # status (this is pretty odd code, but urllib2.Request is weird)
    for row in urlinfo.split("\n"):
        if row.find("Status") != -1:
            status = row
        if row.find("Location") != -1:
            location = row

    print status
    if not "201" in status:
        return "Failed to get URL!"

    # this wont work for some reason, so lets ignore it ^

    # return location, minus the first 10 chars
    return location[10:]

########NEW FILE########
__FILENAME__ = google
import random

from util import hook, http, text


def api_get(kind, query):
    """Use the RESTful Google Search API"""
    url = 'http://ajax.googleapis.com/ajax/services/search/%s?' \
          'v=1.0&safe=moderate'
    return http.get_json(url % kind, q=query)


@hook.command('image')
@hook.command('gis')
@hook.command
def googleimage(inp):
    """gis <query> -- Returns first Google Image result for <query>."""

    parsed = api_get('images', inp)
    if not 200 <= parsed['responseStatus'] < 300:
        raise IOError('error searching for images: {}: {}'.format(parsed['responseStatus'], ''))
    if not parsed['responseData']['results']:
        return 'no images found'
    return random.choice(parsed['responseData']['results'][:10])['unescapedUrl']


@hook.command('search')
@hook.command('g')
@hook.command
def google(inp):
    """google <query> -- Returns first google search result for <query>."""

    parsed = api_get('web', inp)
    if not 200 <= parsed['responseStatus'] < 300:
        raise IOError('error searching for pages: {}: {}'.format(parsed['responseStatus'], ''))
    if not parsed['responseData']['results']:
        return 'No results found.'

    result = parsed['responseData']['results'][0]

    title = http.unescape(result['titleNoFormatting'])
    title = text.truncate_str(title, 60)
    content = http.unescape(result['content'])

    if not content:
        content = "No description available."
    else:
        content = http.html.fromstring(content).text_content()
        content = text.truncate_str(content, 150)

    return u'{} -- \x02{}\x02: "{}"'.format(result['unescapedUrl'], title, content)

########NEW FILE########
__FILENAME__ = googleurlparse
from util import hook
from urllib import unquote

@hook.command(autohelp=False)
def googleurl(inp, db=None, nick=None):
    """googleurl [nickname] - Converts Google urls (google.com/url) to normal urls
       where possible, in the specified nickname's last message. If nickname isn't provided,
       action will be performed on user's last message"""
    if not inp:
        inp = nick
    last_message = db.execute("select name, quote from seen_user where name"
                              " like ? and chan = ?", (inp.lower(), input.chan.lower())).fetchone()
    if last_message:
        msg = last_message[1]
        out = ", ".join([(unquote(a[4:]) if a[:4] == "url=" else "") for a in msg.split("&")])\
              .replace(", ,", "").strip()
        return out if out else "No matches in your last message."
    else:
        if inp == nick:
            return "You haven't said anything in this channel yet!"
        else:
            return "That user hasn't said anything in this channel yet!"

########NEW FILE########
__FILENAME__ = google_translate
"""
A Google API key is required and retrieved from the bot config file.
Since December 1, 2011, the Google Translate API is a paid service only.
"""

import htmlentitydefs
import re

from util import hook, http


max_length = 100


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


def goog_trans(api_key, text, slang, tlang):
    url = 'https://www.googleapis.com/language/translate/v2'

    if len(text) > max_length:
        return "This command only supports input of less then 100 characters."

    if slang:
        parsed = http.get_json(url, key=api_key, q=text, source=slang, target=tlang, format="text")
    else:
        parsed = http.get_json(url, key=api_key, q=text, target=tlang, format="text")

        #if not 200 <= parsed['responseStatus'] < 300:
        #   raise IOError('error with the translation server: %d: %s' % (
        #           parsed['responseStatus'], parsed['responseDetails']))
    if not slang:
        return unescape('(%(detectedSourceLanguage)s) %(translatedText)s' %
                        (parsed['data']['translations'][0]))
    return unescape('%(translatedText)s' % parsed['data']['translations'][0])


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
    """translate [source language [target language]] <sentence> -- translates
    <sentence> from source language (default autodetect) to target
    language (default English) using Google Translate"""

    api_key = bot.config.get("api_keys", {}).get("googletranslate", None)
    if not api_key:
        return "This command requires a paid API key."

    args = inp.split(u' ', 2)

    try:
        if len(args) >= 2:
            sl = match_language(args[0])
            if not sl:
                return goog_trans(api_key, inp, '', 'en')
            if len(args) == 2:
                return goog_trans(api_key, args[1], sl, 'en')
            if len(args) >= 3:
                tl = match_language(args[1])
                if not tl:
                    if sl == 'en':
                        return 'unable to determine desired target language'
                    return goog_trans(api_key, args[1] + ' ' + args[2], sl, 'en')
                return goog_trans(api_key, args[2], sl, tl)
        return goog_trans(api_key, inp, '', 'en')
    except IOError, e:
        return e


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
__FILENAME__ = help
import re

from util import hook


@hook.command("help", autohelp=False)
def help_command(inp, notice=None, conn=None, bot=None):
    """help  -- Gives a list of commands/help for a command."""

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
        out = [""]
        well = []
        for x in commands:
            well.append(x)
        well.sort()
        count = 0
        for x in well:
            if len(out[count]) + len(str(x)) > 405:
                count += 1
                out.append(str(x))
            else:
                out[count] += " " + str(x)

        notice("Commands I recognise: " + out[0][1:])
        if len(out) > 1:
            for x in out[1:]:
                notice(x)
        notice("For detailed help, do '%shelp <example>' where <example> "
               "is the name of the command you want help for." % conn.conf["command_prefix"])

    else:
        if inp in commands:
            notice(conn.conf["command_prefix"] + commands[inp].__doc__)
        else:
            notice("Command {}{} not found".format(conn.conf["command_prefix"], inp))

########NEW FILE########
__FILENAME__ = history
from collections import deque
from util import hook, timesince
import time
import re

db_ready = []


def db_init(db, conn_name):
    """check to see that our db has the the seen table (connection name is for caching the result per connection)"""
    global db_ready
    if db_ready.count(conn_name) < 1:
        db.execute("create table if not exists seen_user(name, time, quote, chan, host, "
                   "primary key(name, chan))")
        db.commit()
        db_ready.append(conn_name)


def track_seen(input, message_time, db, conn):
    """ Tracks messages for the .seen command """
    db_init(db, conn)
    # keep private messages private
    if input.chan[:1] == "#" and not re.findall('^s/.*/.*/$', input.msg.lower()):
        db.execute("insert or replace into seen_user(name, time, quote, chan, host)"
                   "values(?,?,?,?,?)", (input.nick.lower(), message_time, input.msg,
                                         input.chan, input.mask))
        db.commit()


def track_history(input, message_time, conn):
    try:
        history = conn.history[input.chan]
    except KeyError:
        conn.history[input.chan] = deque(maxlen=100)
        history = conn.history[input.chan]

    data = (input.nick, message_time, input.msg)
    history.append(data)


@hook.singlethread
@hook.event('PRIVMSG', ignorebots=False)
def chat_tracker(paraml, input=None, db=None, conn=None):
    message_time = time.time()
    track_seen(input, message_time, db, conn)
    track_history(input, message_time, conn)


@hook.command(autohelp=False)
def resethistory(inp, input=None, conn=None):
    """resethistory - Resets chat history for the current channel"""
    try:
        conn.history[input.chan].clear()
        return "Reset chat history for current channel."
    except KeyError:
        # wat
        return "There is no history for this channel."

"""seen.py: written by sklnd in about two beers July 2009"""

@hook.command
def seen(inp, nick='', chan='', db=None, input=None, conn=None):
    """seen <nick> <channel> -- Tell when a nickname was last in active in one of this bot's channels."""

    if input.conn.nick.lower() == inp.lower():
        return "You need to get your eyes checked."

    if inp.lower() == nick.lower():
        return "Have you looked in a mirror lately?"

    if not re.match("^[A-Za-z0-9_|.\-\]\[]*$", inp.lower()):
        return "I can't look up that name, its impossible to use!"

    db_init(db, conn.name)

    last_seen = db.execute("select name, time, quote from seen_user where name"
                           " like ? and chan = ?", (inp, chan)).fetchone()

    if last_seen:
        reltime = timesince.timesince(last_seen[1])
        if last_seen[0] != inp.lower():  # for glob matching
            inp = last_seen[0]
        if last_seen[2][0:1] == "\x01":
            return '{} was last seen {} ago: * {} {}'.format(inp, reltime, inp,
                                                             last_seen[2][8:-1])
        else:
            return '{} was last seen {} ago saying: {}'.format(inp, reltime, last_seen[2])
    else:
        return "I've never seen {} talking in this channel.".format(inp)

########NEW FILE########
__FILENAME__ = horoscope
# Plugin by Infinity - <https://github.com/infinitylabs/UguuBot>

from util import hook, http, text

db_ready = False


def db_init(db):
    """check to see that our db has the horoscope table and return a connection."""
    global db_ready
    if not db_ready:
        db.execute("create table if not exists horoscope(nick primary key, sign)")
        db.commit()
        db_ready = True


@hook.command(autohelp=False)
def horoscope(inp, db=None, notice=None, nick=None):
    """horoscope <sign> -- Get your horoscope."""
    db_init(db)

    # check if the user asked us not to save his details
    dontsave = inp.endswith(" dontsave")
    if dontsave:
        sign = inp[:-9].strip().lower()
    else:
        sign = inp

    db.execute("create table if not exists horoscope(nick primary key, sign)")

    if not sign:
        sign = db.execute("select sign from horoscope where nick=lower(?)",
                          (nick,)).fetchone()
        if not sign:
            notice("horoscope <sign> -- Get your horoscope")
            return
        sign = sign[0]

    url = "http://my.horoscope.com/astrology/free-daily-horoscope-{}.html".format(sign)
    soup = http.get_soup(url)

    title = soup.find_all('h1', {'class': 'h1b'})[1]
    horoscope_text = soup.find('div', {'class': 'fontdef1'})
    result = u"\x02%s\x02 %s" % (title, horoscope_text)
    result = text.strip_html(result)
    #result = unicode(result, "utf8").replace('flight ','')

    if not title:
        return "Could not get the horoscope for {}.".format(inp)

    if inp and not dontsave:
        db.execute("insert or replace into horoscope(nick, sign) values (?,?)",
                    (nick.lower(), sign))
        db.commit()

    return result

########NEW FILE########
__FILENAME__ = hulu
from urllib import urlencode
import re

from util import hook, http, timeformat


hulu_re = (r'(.*://)(www.hulu.com|hulu.com)(.*)', re.I)


@hook.regex(*hulu_re)
def hulu_url(match):
    data = http.get_json("http://www.hulu.com/api/oembed.json?url=http://www.hulu.com" + match.group(3))
    showname = data['title'].split("(")[-1].split(")")[0]
    title = data['title'].split(" (")[0]
    return "{}: {} - {}".format(showname, title, timeformat.format_time(int(data['duration'])))


@hook.command('hulu')
def hulu_search(inp):
    """hulu <search> - Search Hulu"""
    result = http.get_soup(
        "http://m.hulu.com/search?dp_identifier=hulu&{}&items_per_page=1&page=1".format(urlencode({'query': inp})))
    data = result.find('results').find('videos').find('video')
    showname = data.find('show').find('name').text
    title = data.find('title').text
    duration = timeformat.format_time(int(float(data.find('duration').text)))
    description = data.find('description').text
    rating = data.find('content-rating').text
    return "{}: {} - {} - {} ({}) {}".format(showname, title, description, duration, rating,
                                             "http://www.hulu.com/watch/" + str(data.find('id').text))

########NEW FILE########
__FILENAME__ = ignore
import json
from fnmatch import fnmatch

from util import hook


@hook.sieve
def ignore_sieve(bot, input, func, type, args):
    """ blocks input from ignored channels/hosts """
    ignorelist = bot.config["plugins"]["ignore"]["ignored"]
    mask = input.mask.lower()

    # don't block input to event hooks
    if type == "event":
        return input

    if ignorelist:
        for pattern in ignorelist:
            if pattern.startswith("#") and pattern in ignorelist:
                if input.command == "PRIVMSG" and input.lastparam[1:] == "unignore":
                    return input
                else:
                    return None
            elif fnmatch(mask, pattern):
                if input.command == "PRIVMSG" and input.lastparam[1:] == "unignore":
                    return input
                else:
                    return None

    return input


@hook.command(autohelp=False)
def ignored(inp, notice=None, bot=None):
    """ignored -- Lists ignored channels/users."""
    ignorelist = bot.config["plugins"]["ignore"]["ignored"]
    if ignorelist:
        notice("Ignored channels/users are: {}".format(", ".join(ignorelist)))
    else:
        notice("No masks are currently ignored.")
    return


@hook.command(permissions=["ignore"])
def ignore(inp, notice=None, bot=None, config=None):
    """ignore <channel|nick|host> -- Makes the bot ignore <channel|user>."""
    target = inp.lower()
    ignorelist = bot.config["plugins"]["ignore"]["ignored"]
    if target in ignorelist:
        notice("{} is already ignored.".format(target))
    else:
        notice("{} has been ignored.".format(target))
        ignorelist.append(target)
        ignorelist.sort()
        json.dump(bot.config, open('config', 'w'), sort_keys=True, indent=2)
    return


@hook.command(permissions=["ignore"])
def unignore(inp, notice=None, bot=None, config=None):
    """unignore <channel|user> -- Makes the bot listen to
    <channel|user>."""
    target = inp.lower()
    ignorelist = bot.config["plugins"]["ignore"]["ignored"]
    if target in ignorelist:
        notice("{} has been unignored.".format(target))
        ignorelist.remove(target)
        ignorelist.sort()
        json.dump(bot.config, open('config', 'w'), sort_keys=True, indent=2)
    else:
        notice("{} is not ignored.".format(target))
    return

########NEW FILE########
__FILENAME__ = imdb
# IMDb lookup plugin by Ghetto Wizard (2011) and blha303 (2013)

import re

from util import hook, http, text


id_re = re.compile("tt\d+")
imdb_re = (r'(.*:)//(imdb.com|www.imdb.com)(:[0-9]+)?(.*)', re.I)


@hook.command
def imdb(inp):
    """imdb <movie> -- Gets information about <movie> from IMDb."""

    strip = inp.strip()

    if id_re.match(strip):
        content = http.get_json("http://www.omdbapi.com/", i=strip)
    else:
        content = http.get_json("http://www.omdbapi.com/", t=strip)

    if content.get('Error', None) == 'Movie not found!':
        return 'Movie not found!'
    elif content['Response'] == 'True':
        content['URL'] = 'http://www.imdb.com/title/{}'.format(content['imdbID'])

        out = '\x02%(Title)s\x02 (%(Year)s) (%(Genre)s): %(Plot)s'
        if content['Runtime'] != 'N/A':
            out += ' \x02%(Runtime)s\x02.'
        if content['imdbRating'] != 'N/A' and content['imdbVotes'] != 'N/A':
            out += ' \x02%(imdbRating)s/10\x02 with \x02%(imdbVotes)s\x02' \
                   ' votes.'
        out += ' %(URL)s'
        return out % content
    else:
        return 'Unknown error.'


@hook.regex(*imdb_re)
def imdb_url(match):
    imdb_id = match.group(4).split('/')[-1]
    if imdb_id == "":
        imdb_id = match.group(4).split('/')[-2]
    content = http.get_json("http://www.omdbapi.com/", i=imdb_id)
    if content.get('Error', None) == 'Movie not found!':
        return 'Movie not found!'
    elif content['Response'] == 'True':
        content['URL'] = 'http://www.imdb.com/title/%(imdbID)s' % content
        content['Plot'] = text.truncate_str(content['Plot'], 50)
        out = '\x02%(Title)s\x02 (%(Year)s) (%(Genre)s): %(Plot)s'
        if content['Runtime'] != 'N/A':
            out += ' \x02%(Runtime)s\x02.'
        if content['imdbRating'] != 'N/A' and content['imdbVotes'] != 'N/A':
            out += ' \x02%(imdbRating)s/10\x02 with \x02%(imdbVotes)s\x02' \
                   ' votes.'
        return out % content
    else:
        return 'Unknown error.'

########NEW FILE########
__FILENAME__ = imgur
import re
import random

from util import hook, http, web


base_url = "http://reddit.com/r/{}/.json"
imgur_re = re.compile(r'http://(?:i\.)?imgur\.com/(a/)?(\w+\b(?!/))\.?\w?')

album_api = "https://api.imgur.com/3/album/{}/images.json"


def is_valid(data):
    if data["domain"] in ["i.imgur.com", "imgur.com"]:
        return True
    else:
        return False


@hook.command(autohelp=False)
def imgur(inp):
    """imgur [subreddit] -- Gets the first page of imgur images from [subreddit] and returns a link to them.
     If [subreddit] is undefined, return any imgur images"""
    if inp:
        # see if the input ends with "nsfw"
        show_nsfw = inp.endswith(" nsfw")

        # remove "nsfw" from the input string after checking for it
        if show_nsfw:
            inp = inp[:-5].strip().lower()

        url = base_url.format(inp.strip())
    else:
        url = "http://www.reddit.com/domain/imgur.com/.json"
        show_nsfw = False

    try:
        data = http.get_json(url, user_agent=http.ua_chrome)
    except Exception as e:
        return "Error: " + str(e)

    data = data["data"]["children"]
    random.shuffle(data)

    # filter list to only have imgur links
    filtered_posts = [i["data"] for i in data if is_valid(i["data"])]

    if not filtered_posts:
        return "No images found."

    items = []

    headers = {
        "Authorization": "Client-ID b5d127e6941b07a"
    }

    # loop over the list of posts
    for post in filtered_posts:
        if post["over_18"] and not show_nsfw:
            continue

        match = imgur_re.search(post["url"])
        if match.group(1) == 'a/':
            # post is an album
            url = album_api.format(match.group(2))
            images = http.get_json(url, headers=headers)["data"]

            # loop over the images in the album and add to the list
            for image in images:
                items.append(image["id"])

        elif match.group(2) is not None:
            # post is an image
            items.append(match.group(2))

    if not items:
        return "No images found (use .imgur <subreddit> nsfw to show explicit content)"

    if show_nsfw:
        return "{} \x02NSFW\x02".format(web.isgd("http://imgur.com/" + ','.join(items)))
    else:
        return web.isgd("http://imgur.com/" + ','.join(items))

########NEW FILE########
__FILENAME__ = isup
import urlparse

from util import hook, http, urlnorm


@hook.command
def isup(inp):
    """isup -- uses isup.me to see if a site is up or not"""

    # slightly overcomplicated, esoteric URL parsing
    scheme, auth, path, query, fragment = urlparse.urlsplit(inp.strip())

    domain = auth.encode('utf-8') or path.encode('utf-8')
    url = urlnorm.normalize(domain, assume_scheme="http")

    try:
        soup = http.get_soup('http://isup.me/' + domain)
    except http.HTTPError, http.URLError:
        return "Could not get status."

    content = soup.find('div').text.strip()

    if "not just you" in content:
        return "It's not just you. {} looks \x02\x034down\x02\x0f from here!".format(url)
    elif "is up" in content:
        return "It's just you. {} is \x02\x033up\x02\x0f.".format(url)
    else:
        return "Huh? That doesn't look like a site on the interweb."

########NEW FILE########
__FILENAME__ = kernel
import re

from util import hook, http


@hook.command(autohelp=False)
def kernel(inp, reply=None):
    contents = http.get("https://www.kernel.org/finger_banner")
    contents = re.sub(r'The latest(\s*)', '', contents)
    contents = re.sub(r'version of the Linux kernel is:(\s*)', '- ', contents)
    lines = contents.split("\n")

    message = "Linux kernel versions: "
    message += ", ".join(line for line in lines[:-1])
    reply(message)

########NEW FILE########
__FILENAME__ = kill
import json

from util import hook, textgen


def get_generator(_json, variables):
    data = json.loads(_json)
    return textgen.TextGenerator(data["templates"],
                                 data["parts"], variables=variables)


@hook.command
def kill(inp, action=None, nick=None, conn=None, notice=None):
    """kill <user> -- Makes the bot kill <user>."""
    target = inp.strip()

    if " " in target:
        notice("Invalid username!")
        return

    # if the user is trying to make the bot kill itself, kill them
    if target.lower() == conn.nick.lower() or target.lower() == "itself":
        target = nick

    variables = {
        "user": target
    }

    with open("plugins/data/kills.json") as f:
        generator = get_generator(f.read(), variables)

    # act out the message
    action(generator.generate_string())

########NEW FILE########
__FILENAME__ = lastfm
from datetime import datetime

from util import hook, http, timesince


api_url = "http://ws.audioscrobbler.com/2.0/?format=json"


@hook.command('l', autohelp=False)
@hook.command(autohelp=False)
def lastfm(inp, nick='', db=None, bot=None, notice=None):
    """lastfm [user] [dontsave] -- Displays the now playing (or last played)
     track of LastFM user [user]."""
    api_key = bot.config.get("api_keys", {}).get("lastfm")
    if not api_key:
        return "error: no api key set"

    # check if the user asked us not to save his details
    dontsave = inp.endswith(" dontsave")
    if dontsave:
        user = inp[:-9].strip().lower()
    else:
        user = inp

    db.execute("create table if not exists lastfm(nick primary key, acc)")

    if not user:
        user = db.execute("select acc from lastfm where nick=lower(?)",
                          (nick,)).fetchone()
        if not user:
            notice(lastfm.__doc__)
            return
        user = user[0]

    response = http.get_json(api_url, method="user.getrecenttracks",
                             api_key=api_key, user=user, limit=1)

    if 'error' in response:
        return u"Error: {}.".format(response["message"])

    if not "track" in response["recenttracks"] or len(response["recenttracks"]["track"]) == 0:
        return u'No recent tracks for user "{}" found.'.format(user)

    tracks = response["recenttracks"]["track"]

    if type(tracks) == list:
        # if the user is listening to something, the tracks entry is a list
        # the first item is the current track
        track = tracks[0]
        status = 'is listening to'
        ending = '.'
    elif type(tracks) == dict:
        # otherwise, they aren't listening to anything right now, and
        # the tracks entry is a dict representing the most recent track
        track = tracks
        status = 'last listened to'
        # lets see how long ago they listened to it
        time_listened = datetime.fromtimestamp(int(track["date"]["uts"]))
        time_since = timesince.timesince(time_listened)
        ending = ' ({} ago)'.format(time_since)

    else:
        return "error: could not parse track listing"

    title = track["name"]
    album = track["album"]["#text"]
    artist = track["artist"]["#text"]

    out = u'{} {} "{}"'.format(user, status, title)
    if artist:
        out += u" by \x02{}\x0f".format(artist)
    if album:
        out += u" from the album \x02{}\x0f".format(album)

    # append ending based on what type it was
    out += ending

    if inp and not dontsave:
        db.execute("insert or replace into lastfm(nick, acc) values (?,?)",
                   (nick.lower(), user))
        db.commit()

    return out

########NEW FILE########
__FILENAME__ = lmgtfy
from util import hook, web, http


@hook.command('gfy')
@hook.command
def lmgtfy(inp):
    """lmgtfy [phrase] - Posts a google link for the specified phrase"""

    link = u"http://lmgtfy.com/?q={}".format(http.quote_plus(inp))

    try:
        return web.isgd(link)
    except (web.ShortenError, http.HTTPError):
        return link

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


log_fds = {}  # '%(net)s %(chan)s': (filename, fd)

timestamp_format = '%H:%M:%S'

formats = {
    'PRIVMSG': '<%(nick)s> %(msg)s',
    'PART': '-!- %(nick)s [%(user)s@%(host)s] has left %(chan)s',
    'JOIN': '-!- %(nick)s [%(user)s@%(host)s] has joined %(param0)s',
    'MODE': '-!- mode/%(chan)s [%(param_tail)s] by %(nick)s',
    'KICK': '-!- %(param1)s was kicked from %(chan)s by %(nick)s [%(msg)s]',
    'TOPIC': '-!- %(nick)s changed the topic of %(chan)s to: %(msg)s',
    'QUIT': '-!- %(nick)s has quit [%(msg)s]',
    'PING': '',
    'NOTICE': '-%(nick)s- %(msg)s'
}

ctcp_formats = {
    'ACTION': '* %(nick)s %(ctcpmsg)s',
    'VERSION': '%(nick)s has requested CTCP %(ctcpcmd)s from %(chan)s: %(ctcpmsg)s',
    'PING': '%(nick)s has requested CTCP %(ctcpcmd)s from %(chan)s: %(ctcpmsg)s',
    'TIME': '%(nick)s has requested CTCP %(ctcpcmd)s from %(chan)s: %(ctcpmsg)s',
    'FINGER': '%(nick)s has requested CTCP %(ctcpcmd)s from %(chan)s: %(ctcpmsg)s'
}

irc_color_re = re.compile(r'(\x03(\d+,\d+|\d)|[\x0f\x02\x16\x1f])')


def get_log_filename(dir, server, chan):
    return os.path.join(dir, 'log', gmtime('%Y'), server, chan,
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

    fd = get_log_fd(bot.persist_dir, input.server, 'raw')
    fd.write(timestamp + ' ' + input.raw + '\n')

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
__FILENAME__ = lyrics
from util import hook, http, web

url = "http://search.azlyrics.com/search.php?q="


@hook.command
def lyrics(inp):
    """lyrics <search> - Search AZLyrics.com for song lyrics"""
    if "pastelyrics" in inp:
        dopaste = True
        inp = inp.replace("pastelyrics", "").strip()
    else:
        dopaste = False
    soup = http.get_soup(url + inp.replace(" ", "+"))
    if "Try to compose less restrictive search query" in soup.find('div', {'id': 'inn'}).text:
        return "No results. Check spelling."
    div = None
    for i in soup.findAll('div', {'class': 'sen'}):
        if "/lyrics/" in i.find('a')['href']:
            div = i
            break
    if div:
        title = div.find('a').text
        link = div.find('a')['href']
        if dopaste:
            newsoup = http.get_soup(link)
            try:
                lyrics = newsoup.find('div', {'style': 'margin-left:10px;margin-right:10px;'}).text.strip()
                pasteurl = " " + web.haste(lyrics)
            except Exception as e:
                pasteurl = " (\x02Unable to paste lyrics\x02 [{}])".format(str(e))
        else:
            pasteurl = ""
        artist = div.find('b').text.title()
        lyricsum = div.find('div').text
        if "\r\n" in lyricsum.strip():
            lyricsum = " / ".join(lyricsum.strip().split("\r\n")[0:4])  # truncate, format
        else:
            lyricsum = " / ".join(lyricsum.strip().split("\n")[0:4])  # truncate, format
        return "\x02{}\x02 by \x02{}\x02 {}{} - {}".format(title, artist, web.try_isgd(link), pasteurl,
                                                           lyricsum[:-3])
    else:
        return "No song results. " + url + inp.replace(" ", "+")

########NEW FILE########
__FILENAME__ = metacritic
# metacritic.com scraper

import re
from urllib2 import HTTPError

from util import hook, http


@hook.command('mc')
@hook.command
def metacritic(inp):
    """mc [all|movie|tv|album|x360|ps3|pc|gba|ds|3ds|wii|vita|wiiu|xone|ps4] <title>
    Gets rating for <title> from metacritic on the specified medium."""

    args = inp.strip()

    game_platforms = ('x360', 'ps3', 'pc', 'gba', 'ds', '3ds', 'wii',
                      'vita', 'wiiu', 'xone', 'ps4')

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

    url = 'http://www.metacritic.com/search/{}/{}/results'.format(cat, title_safe)

    try:
        doc = http.get_html(url)
    except HTTPError:
        return 'error fetching results'

    # get the proper result element we want to pull data from
    result = None

    if not doc.find_class('query_results'):
        return 'No results found.'

    # if they specified an invalid search term, the input box will be empty
    if doc.get_element_by_id('search_term').value == '':
        return 'Invalid search term.'

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
        return 'No results found.'

    # get the name, release date, and score from the result
    product_title = result.find_class('product_title')[0]
    name = product_title.text_content()
    link = 'http://metacritic.com' + product_title.find('a').attrib['href']

    try:
        release = result.find_class('release_date')[0]. \
            find_class('data')[0].text_content()

        # strip extra spaces out of the release date
        release = re.sub(r'\s{2,}', ' ', release)
    except IndexError:
        release = None

    try:
        score = result.find_class('metascore_w')[0].text_content()
    except IndexError:
        score = None

    return '[{}] {} - \x02{}/100\x02, {} - {}'.format(plat.upper(), name, score or 'no score',
                                                      'release: \x02%s\x02' % release if release else 'unreleased',
                                                      link)

########NEW FILE########
__FILENAME__ = minecraft_bukget
import time
import random

from util import hook, http, web, text


## CONSTANTS

base_url = "http://api.bukget.org/3/"

search_url = base_url + "search/plugin_name/like/{}"
random_url = base_url + "plugins/bukkit/?start={}&size=1"
details_url = base_url + "plugins/bukkit/{}"

categories = http.get_json("http://api.bukget.org/3/categories")

count_total = sum([cat["count"] for cat in categories])
count_categories = {cat["name"].lower(): int(cat["count"]) for cat in categories}  # dict comps!


class BukgetError(Exception):
    def __init__(self, code, text):
        self.code = code
        self.text = text

    def __str__(self):
        return self.text


## DATA FUNCTIONS

def plugin_search(term):
    """ searches for a plugin with the bukget API and returns the slug """
    term = term.lower().strip()

    search_term = http.quote_plus(term)

    try:
        results = http.get_json(search_url.format(search_term))
    except (http.HTTPError, http.URLError) as e:
        raise BukgetError(500, "Error Fetching Search Page: {}".format(e))
    
    if not results:
        raise BukgetError(404, "No Results Found")

    for result in results:
        if result["slug"] == term:
            return result["slug"]

    return results[0]["slug"]


def plugin_random():
    """ gets a random plugin from the bukget API and returns the slug """
    results = None

    while not results:
        plugin_number = random.randint(1, count_total)
        print "trying {}".format(plugin_number)
        try:
            results = http.get_json(random_url.format(plugin_number))
        except (http.HTTPError, http.URLError) as e:
            raise BukgetError(500, "Error Fetching Search Page: {}".format(e))

    return results[0]["slug"]


def plugin_details(slug):
    """ takes a plugin slug and returns details from the bukget API """
    slug = slug.lower().strip()

    try:
        details = http.get_json(details_url.format(slug))
    except (http.HTTPError, http.URLError) as e:
        raise BukgetError(500, "Error Fetching Details: {}".format(e))
    return details


## OTHER FUNCTIONS

def format_output(data):
    """ takes plugin data and returns two strings representing information about that plugin """
    name = data["plugin_name"]
    description = text.truncate_str(data['description'], 30)
    url = data['website']
    authors = data['authors'][0]
    authors = authors[0] + u"\u200b" + authors[1:]
    stage = data['stage']

    current_version = data['versions'][0]

    last_update = time.strftime('%d %B %Y %H:%M',
                                time.gmtime(current_version['date']))
    version_number = data['versions'][0]['version']

    bukkit_versions = ", ".join(current_version['game_versions'])
    link = web.try_isgd(current_version['link'])

    if description:
        line_a = u"\x02{}\x02, by \x02{}\x02 - {} - ({}) \x02{}".format(name, authors, description, stage, url)
    else:
        line_a = u"\x02{}\x02, by \x02{}\x02 ({}) \x02{}".format(name, authors, stage, url)

    line_b = u"Last release: \x02v{}\x02 for \x02{}\x02 at {} \x02{}\x02".format(version_number, bukkit_versions,
                                                                                 last_update, link)

    return line_a, line_b


## HOOK FUNCTIONS

@hook.command('plugin')
@hook.command
def bukget(inp, reply=None, message=None):
    """bukget <slug/name> - Look up a plugin on dev.bukkit.org"""
    # get the plugin slug using search
    try:
        slug = plugin_search(inp)
    except BukgetError as e:
        return e

    # get the plugin info using the slug
    try:
        data = plugin_details(slug)
    except BukgetError as e:
        return e

    # format the final message and send it to IRC
    line_a, line_b = format_output(data)

    reply(line_a)
    message(line_b)


@hook.command(autohelp=None)
def randomplugin(inp, reply=None, message=None):
    """randomplugin - Gets a random plugin from dev.bukkit.org"""
    # get a random plugin slug
    try:
        slug = plugin_random()
    except BukgetError as e:
        return e

    # get the plugin info using the slug
    try:
        data = plugin_details(slug)
    except BukgetError as e:
        return e

    # format the final message and send it to IRC
    line_a, line_b = format_output(data)

    reply(line_a)
    message(line_b)
########NEW FILE########
__FILENAME__ = minecraft_items
""" plugin by _303 (?)
"""

import re

from util import hook


pattern = re.compile(r'^(?P<count>\d+)x (?P<name>.+?): (?P<ingredients>.*)$')

recipelist = []


class Recipe(object):
    __slots__ = 'output', 'count', 'ingredients', 'line'

    def __init__(self, output, count, ingredients, line):
        self.output = output
        self.count = count
        self.ingredients = ingredients
        self.line = line

    def __str__(self):
        return self.line


with open("plugins/data/recipes.txt") as f:
    for line in f.readlines():
        if line.startswith("//"):
            continue
        line = line.strip()
        match = pattern.match(line)
        if not match:
            continue
        recipelist.append(Recipe(line=line,
                                 output=match.group("name").lower(),
                                 ingredients=match.group("ingredients"),
                                 count=match.group("count")))

ids = []

with open("plugins/data/itemids.txt") as f:
    for line in f.readlines():
        if line.startswith("//"):
            continue
        parts = line.strip().split()
        itemid = parts[0]
        name = " ".join(parts[1:])
        ids.append((itemid, name))


@hook.command("mcid")
@hook.command
def mcitem(inp, reply=None):
    """mcitem <item/id> -- gets the id from an item or vice versa"""
    inp = inp.lower().strip()

    if inp == "":
        reply("error: no input.")
        return

    results = []

    for item_id, item_name in ids:
        if inp == item_id:
            results = ["\x02[{}]\x02 {}".format(item_id, item_name)]
            break
        elif inp in item_name.lower():
            results.append("\x02[{}]\x02 {}".format(item_id, item_name))

    if not results:
        return "No matches found."

    if len(results) > 12:
        reply("There are too many options, please narrow your search. ({})".format(str(len(results))))
        return

    out = ", ".join(results)

    return out


@hook.command("mccraft")
@hook.command
def mcrecipe(inp, reply=None):
    """mcrecipe <item> -- gets the crafting recipe for an item"""
    inp = inp.lower().strip()

    results = [recipe.line for recipe in recipelist
               if inp in recipe.output]

    if not results:
        return "No matches found."

    if len(results) > 3:
        reply("There are too many options, please narrow your search. ({})".format(len(results)))
        return

    for result in results:
        reply(result)

########NEW FILE########
__FILENAME__ = minecraft_ping
import socket
import struct
import json
import traceback

from util import hook


try:
    import DNS
    has_dns = True
except ImportError:
    has_dns = False


mc_colors = [(u'\xa7f', u'\x0300'), (u'\xa70', u'\x0301'), (u'\xa71', u'\x0302'), (u'\xa72', u'\x0303'),
             (u'\xa7c', u'\x0304'), (u'\xa74', u'\x0305'), (u'\xa75', u'\x0306'), (u'\xa76', u'\x0307'),
             (u'\xa7e', u'\x0308'), (u'\xa7a', u'\x0309'), (u'\xa73', u'\x0310'), (u'\xa7b', u'\x0311'),
             (u'\xa71', u'\x0312'), (u'\xa7d', u'\x0313'), (u'\xa78', u'\x0314'), (u'\xa77', u'\x0315'),
             (u'\xa7l', u'\x02'), (u'\xa79', u'\x0310'), (u'\xa7o', u'\t'), (u'\xa7m', u'\x13'),
             (u'\xa7r', u'\x0f'), (u'\xa7n', u'\x15')]


## EXCEPTIONS


class PingError(Exception):
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


class ParseError(Exception):
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


## MISC


def unpack_varint(s):
    d = 0
    i = 0
    while True:
        b = ord(s.recv(1))
        d |= (b & 0x7F) << 7 * i
        i += 1
        if not b & 0x80:
            return d

pack_data = lambda d: struct.pack('>b', len(d)) + d
pack_port = lambda i: struct.pack('>H', i)

## DATA FUNCTIONS


def mcping_modern(host, port):
    """ pings a server using the modern (1.7+) protocol and returns data """
    try:
        # connect to the server
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            s.connect((host, port))
        except socket.gaierror:
            raise PingError("Invalid hostname")
        except socket.timeout:
            raise PingError("Request timed out")

        # send handshake + status request
        s.send(pack_data("\x00\x00" + pack_data(host.encode('utf8')) + pack_port(port) + "\x01"))
        s.send(pack_data("\x00"))

        # read response
        unpack_varint(s)      # Packet length
        unpack_varint(s)      # Packet ID
        l = unpack_varint(s)  # String length

        if not l > 1:
            raise PingError("Invalid response")

        d = ""
        while len(d) < l:
            d += s.recv(1024)

        # Close our socket
        s.close()
    except socket.error:
        raise PingError("Socket Error")

    # Load json and return
    data = json.loads(d.decode('utf8'))
    try:
        version = data["version"]["name"]
        try:
            desc = u" ".join(data["description"]["text"].split())
        except TypeError:
            desc = u" ".join(data["description"].split())
        max_players = data["players"]["max"]
        online = data["players"]["online"]
    except Exception as e:
        # TODO: except Exception is bad
        traceback.print_exc(e)
        raise PingError("Unknown Error: {}".format(e))

    output = {
        "motd": format_colors(desc),
        "motd_raw": desc,
        "version": version,
        "players": online,
        "players_max": max_players
    }
    return output


def mcping_legacy(host, port):
    """ pings a server using the legacy (1.6 and older) protocol and returns data """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect((host, port))
        sock.send('\xfe\x01')
        response = sock.recv(1)
    except socket.gaierror:
        raise PingError("Invalid hostname")
    except socket.timeout:
        raise PingError("Request timed out")

    if response[0] != '\xff':
        raise PingError("Invalid response")

    length = struct.unpack('!h', sock.recv(2))[0]
    values = sock.recv(length * 2).decode('utf-16be')
    data = values.split(u'\x00')  # try to decode data using new format
    if len(data) == 1:
        # failed to decode data, server is using old format
        data = values.split(u'\xa7')
        output = {
            "motd": format_colors(" ".join(data[0].split())),
            "motd_raw": data[0],
            "version": None,
            "players": data[1],
            "players_max": data[2]
        }
    else:
        # decoded data, server is using new format
        output = {
            "motd": format_colors(" ".join(data[3].split())),
            "motd_raw": data[3],
            "version": data[2],
            "players": data[4],
            "players_max": data[5]
        }
    sock.close()
    return output


## FORMATTING/PARSING FUNCTIONS

def check_srv(domain):
    """ takes a domain and finds minecraft SRV records """
    DNS.DiscoverNameServers()
    srv_req = DNS.Request(qtype='srv')
    srv_result = srv_req.req('_minecraft._tcp.{}'.format(domain))

    for getsrv in srv_result.answers:
        if getsrv['typename'] == 'SRV':
            data = [getsrv['data'][2], getsrv['data'][3]]
            return data


def parse_input(inp):
    """ takes the input from the mcping command and returns the host and port """
    inp = inp.strip().split(" ")[0]
    if ":" in inp:
        # the port is defined in the input string
        host, port = inp.split(":", 1)
        try:
            port = int(port)
            if port > 65535 or port < 0:
                raise ParseError("The port '{}' is invalid.".format(port))
        except ValueError:
            raise ParseError("The port '{}' is invalid.".format(port))
        return host, port
    if has_dns:
        # the port is not in the input string, but we have PyDNS so look for a SRV record
        srv_data = check_srv(inp)
        if srv_data:
            return str(srv_data[1]), int(srv_data[0])
    # return default port
    return inp, 25565


def format_colors(motd):
    for original, replacement in mc_colors:
        motd = motd.replace(original, replacement)
    motd = motd.replace(u"\xa7k", "")
    return motd


def format_output(data):
    if data["version"]:
        return u"{motd}\x0f - {version}\x0f - {players}/{players_max}" \
               u" players.".format(**data).replace("\n", u"\x0f - ")
    else:
        return u"{motd}\x0f - {players}/{players_max}" \
               u" players.".format(**data).replace("\n", u"\x0f - ")


@hook.command
@hook.command("mcp")
def mcping(inp):
    """mcping <server>[:port] - Ping a Minecraft server to check status."""
    try:
        host, port = parse_input(inp)
    except ParseError as e:
        return "Could not parse input ({})".format(e)

    try:
        data = mcping_modern(host, port)
    except PingError:
        try:
            data = mcping_legacy(host, port)
        except PingError as e:
            return "Could not ping server, is it offline? ({})".format(e)

    return format_output(data)

########NEW FILE########
__FILENAME__ = minecraft_status
import json

from util import hook, http


@hook.command(autohelp=False)
def mcstatus(inp):
    """mcstatus -- Checks the status of various Mojang (the creators of Minecraft) servers."""

    try:
        request = http.get("http://status.mojang.com/check")
    except (http.URLError, http.HTTPError) as e:
        return "Unable to get Minecraft server status: {}".format(e)

    # lets just reformat this data to get in a nice format
    data = json.loads(request.replace("}", "").replace("{", "").replace("]", "}").replace("[", "{"))

    out = []

    # use a loop so we don't have to update it if they add more servers
    green = []
    yellow = []
    red = []
    for server, status in data.items():
        if status == "green":
            green.append(server)
        elif status == "yellow":
            yellow.append(server)
        else:
            red.append(server)

    if green:
        out = "\x033\x02Online\x02\x0f: " + ", ".join(green)
        if yellow:
            out += " "
    if yellow:
        out += "\x02Issues\x02: " + ", ".join(yellow)
        if red:
            out += " "
    if red:
        out += "\x034\x02Offline\x02\x0f: " + ", ".join(red)

    return "\x0f" + out.replace(".mojang.com", ".mj") \
                       .replace(".minecraft.net", ".mc")

########NEW FILE########
__FILENAME__ = minecraft_user
import json
from util import hook, http

NAME_URL = "https://account.minecraft.net/buy/frame/checkName/{}"
PAID_URL = "http://www.minecraft.net/haspaid.jsp"


class McuError(Exception):
    pass


def get_status(name):
    """ takes a name and returns status """
    try:
        name_encoded = http.quote_plus(name)
        response = http.get(NAME_URL.format(name_encoded))
    except (http.URLError, http.HTTPError) as e:
        raise McuError("Could not get name status: {}".format(e))

    if "OK" in response:
        return "free"
    elif "TAKEN" in response:
        return "taken"
    elif "invalid characters" in response:
        return "invalid"


def get_profile(name):
    profile = {}

    # form the profile request
    request = {
        "name": name,
        "agent": "minecraft"
    }

    # submit the profile request
    try:
        headers = {"Content-Type": "application/json"}
        r = http.get_json(
            'https://api.mojang.com/profiles/page/1',
            post_data=json.dumps(request),
            headers=headers
        )
    except (http.URLError, http.HTTPError) as e:
        raise McuError("Could not get profile status: {}".format(e))

    user = r["profiles"][0]
    profile["name"] = user["name"]
    profile["id"] = user["id"]

    profile["legacy"] = user.get("legacy", False)

    try:
        response = http.get(PAID_URL, user=name)
    except (http.URLError, http.HTTPError) as e:
        raise McuError("Could not get payment status: {}".format(e))

    if "true" in response:
        profile["paid"] = True
    else:
        profile["paid"] = False

    return profile


@hook.command("haspaid")
@hook.command("mcpaid")
@hook.command
def mcuser(inp):
    """mcpaid <username> -- Gets information about the Minecraft user <account>."""
    user = inp.strip()

    try:
        # get status of name (does it exist?)
        name_status = get_status(user)
    except McuError as e:
        return e

    if name_status == "taken":
        try:
            # get information about user
            profile = get_profile(user)
        except McuError as e:
            return "Error: {}".format(e)

        profile["lt"] = ", legacy" if profile["legacy"] else ""

        if profile["paid"]:
            return u"The account \x02{name}\x02 ({id}{lt}) exists. It is a \x02paid\x02" \
                   u" account.".format(**profile)
        else:
            return u"The account \x02{name}\x02 ({id}{lt}) exists. It \x034\x02is NOT\x02\x0f a paid" \
                   u" account.".format(**profile)
    elif name_status == "free":
        return u"The account \x02{}\x02 does not exist.".format(user)
    elif name_status == "invalid":
        return u"The name \x02{}\x02 contains invalid characters.".format(user)
    else:
        # if you see this, panic
        return "Unknown Error."
########NEW FILE########
__FILENAME__ = minecraft_wiki
import re

from util import hook, http, text


api_url = "http://minecraft.gamepedia.com/api.php?action=opensearch"
mc_url = "http://minecraft.gamepedia.com/"


@hook.command
def mcwiki(inp):
    """mcwiki <phrase> -- Gets the first paragraph of
    the Minecraft Wiki article on <phrase>."""

    try:
        j = http.get_json(api_url, search=inp)
    except (http.HTTPError, http.URLError) as e:
        return "Error fetching search results: {}".format(e)
    except ValueError as e:
        return "Error reading search results: {}".format(e)

    if not j[1]:
        return "No results found."

    # we remove items with a '/' in the name, because
    # gamepedia uses sub-pages for different languages
    # for some stupid reason
    items = [item for item in j[1] if not "/" in item]

    if items:
        article_name = items[0].replace(' ', '_').encode('utf8')
    else:
        # there are no items without /, just return a / one
        article_name = j[1][0].replace(' ', '_').encode('utf8')

    url = mc_url + http.quote(article_name, '')

    try:
        page = http.get_html(url)
    except (http.HTTPError, http.URLError) as e:
        return "Error fetching wiki page: {}".format(e)

    for p in page.xpath('//div[@class="mw-content-ltr"]/p'):
        if p.text_content():
            summary = " ".join(p.text_content().splitlines())
            summary = re.sub("\[\d+\]", "", summary)
            summary = text.truncate_str(summary, 200)
            return u"{} :: {}".format(summary, url)

    # this shouldn't happen
    return "Unknown Error."

########NEW FILE########
__FILENAME__ = mlia
# Plugin by Infinity - <https://github.com/infinitylabs/UguuBot>

import random

from util import hook, http


mlia_cache = []


def refresh_cache():
    """gets a page of random MLIAs and puts them into a dictionary """
    url = 'http://mylifeisaverage.com/{}'.format(random.randint(1, 11000))
    soup = http.get_soup(url)

    for story in soup.find_all('div', {'class': 'story '}):
        mlia_id = story.find('span', {'class': 'left'}).a.text
        mlia_text = story.find('div', {'class': 'sc'}).text.strip()
        mlia_cache.append((mlia_id, mlia_text))

# do an initial refresh of the cache
refresh_cache()


@hook.command(autohelp=False)
def mlia(inp, reply=None):
    """mlia -- Gets a random quote from MyLifeIsAverage.com."""
    # grab the last item in the mlia cache and remove it
    mlia_id, text = mlia_cache.pop()
    # reply with the mlia we grabbed
    reply('({}) {}'.format(mlia_id, text))
    # refresh mlia cache if its getting empty
    if len(mlia_cache) < 3:
        refresh_cache()

########NEW FILE########
__FILENAME__ = namegen
import json
import os

from util import hook, text, textgen


GEN_DIR = "./plugins/data/name_files/"


def get_generator(_json):
    data = json.loads(_json)
    return textgen.TextGenerator(data["templates"],
                                 data["parts"], default_templates=data["default_templates"])


@hook.command(autohelp=False)
def namegen(inp, notice=None):
    """namegen [generator] -- Generates some names using the chosen generator.
    'namegen list' will display a list of all generators."""

    # clean up the input
    inp = inp.strip().lower()

    # get a list of available name generators
    files = os.listdir(GEN_DIR)
    all_modules = []
    for i in files:
        if os.path.splitext(i)[1] == ".json":
            all_modules.append(os.path.splitext(i)[0])
    all_modules.sort()

    # command to return a list of all available generators
    if inp == "list":
        message = "Available generators: "
        message += text.get_text_list(all_modules, 'and')
        notice(message)
        return

    if inp:
        selected_module = inp.split()[0]
    else:
        # make some generic fantasy names
        selected_module = "fantasy"

    # check if the selected module is valid
    if not selected_module in all_modules:
        return "Invalid name generator :("

    # load the name generator
    with open(os.path.join(GEN_DIR, "{}.json".format(selected_module))) as f:
        try:
            generator = get_generator(f.read())
        except ValueError as error:
            return "Unable to read name file: {}".format(error)

    # time to generate some names
    name_list = generator.generate_strings(10)

    # and finally return the final message :D
    return "Some names to ponder: {}.".format(text.get_text_list(name_list, 'and'))

########NEW FILE########
__FILENAME__ = newegg
import json
import re

from util import hook, http, text, web


## CONSTANTS

ITEM_URL = "http://www.newegg.com/Product/Product.aspx?Item={}"

API_PRODUCT = "http://www.ows.newegg.com/Products.egg/{}/ProductDetails"
API_SEARCH = "http://www.ows.newegg.com/Search.egg/Advanced"

NEWEGG_RE = (r"(?:(?:www.newegg.com|newegg.com)/Product/Product\.aspx\?Item=)([-_a-zA-Z0-9]+)", re.I)


## OTHER FUNCTIONS

def format_item(item, show_url=True):
    """ takes a newegg API item object and returns a description """
    title = text.truncate_str(item["Title"], 50)

    # format the rating nicely if it exists
    if not item["ReviewSummary"]["TotalReviews"] == "[]":
        rating = "Rated {}/5 ({} ratings)".format(item["ReviewSummary"]["Rating"],
                                                  item["ReviewSummary"]["TotalReviews"][1:-1])
    else:
        rating = "No Ratings"

    if not item["FinalPrice"] == item["OriginalPrice"]:
        price = "{FinalPrice}, was {OriginalPrice}".format(**item)
    else:
        price = item["FinalPrice"]

    tags = []

    if item["Instock"]:
        tags.append("\x02Stock Available\x02")
    else:
        tags.append("\x02Out Of Stock\x02")

    if item["FreeShippingFlag"]:
        tags.append("\x02Free Shipping\x02")

    if item["IsFeaturedItem"]:
        tags.append("\x02Featured\x02")

    if item["IsShellShockerItem"]:
        tags.append(u"\x02SHELL SHOCKER\u00AE\x02")

    # join all the tags together in a comma separated string ("tag1, tag2, tag3")
    tag_text = u", ".join(tags)

    if show_url:
        # create the item URL and shorten it
        url = web.try_isgd(ITEM_URL.format(item["NeweggItemNumber"]))
        return u"\x02{}\x02 ({}) - {} - {} - {}".format(title, price, rating,
                                                        tag_text, url)
    else:
        return u"\x02{}\x02 ({}) - {} - {}".format(title, price, rating,
                                                   tag_text)


## HOOK FUNCTIONS

@hook.regex(*NEWEGG_RE)
def newegg_url(match):
    item_id = match.group(1)
    item = http.get_json(API_PRODUCT.format(item_id))
    return format_item(item, show_url=False)


@hook.command
def newegg(inp):
    """newegg <item name> -- Searches newegg.com for <item name>"""

    # form the search request
    request = {
        "Keyword": inp,
        "Sort": "FEATURED"
    }

    # submit the search request
    r = http.get_json(
        'http://www.ows.newegg.com/Search.egg/Advanced',
        post_data=json.dumps(request)
    )

    # get the first result
    if r["ProductListItems"]:
        return format_item(r["ProductListItems"][0])
    else:
        return "No results found."



########NEW FILE########
__FILENAME__ = newgrounds
import re

from util import hook, http


newgrounds_re = (r'(.*:)//(www.newgrounds.com|newgrounds.com)(:[0-9]+)?(.*)', re.I)
valid = set('0123456789')


def test(s):
    return set(s) <= valid


@hook.regex(*newgrounds_re)
def newgrounds_url(match):
    location = match.group(4).split("/")[-1]
    if not test(location):
        print "Not a valid Newgrounds portal ID. Example: http://www.newgrounds.com/portal/view/593993"
        return None
    soup = http.get_soup("http://www.newgrounds.com/portal/view/" + location)

    title = "\x02{}\x02".format(soup.find('title').text)

    # get author
    try:
        author_info = soup.find('ul', {'class': 'authorlinks'}).find('img')['alt']
        author = " - \x02{}\x02".format(author_info)
    except:
        author = ""

    # get rating
    try:
        rating_info = soup.find('dd', {'class': 'star-variable'})['title'].split("Stars &ndash;")[0].strip()
        rating = u" - rated \x02{}\x02/\x025.0\x02".format(rating_info)
    except:
        rating = ""

    # get amount of ratings
    try:
        ratings_info = soup.find('dd', {'class': 'star-variable'})['title'].split("Stars &ndash;")[1].replace("Votes",
                                                                                                              "").strip()
        numofratings = " ({})".format(ratings_info)
    except:
        numofratings = ""

    # get amount of views
    try:
        views_info = soup.find('dl', {'class': 'contentdata'}).findAll('dd')[1].find('strong').text
        views = " - \x02{}\x02 views".format(views_info)
    except:
        views = ""

    # get upload data
    try:
        date = "on \x02{}\x02".format(soup.find('dl', {'class': 'sidestats'}).find('dd').text)
    except:
        date = ""

    return title + rating + numofratings + views + author + date

########NEW FILE########
__FILENAME__ = notes
import re

from util import hook


db_ready = False


def clean_sql(sql):
    return re.sub(r'\s+', " ", sql).strip()


def db_init(db):
    global db_ready
    if db_ready:
        return

    exists = db.execute("""
      select exists (
        select * from sqlite_master where type = "table" and name = "todos"
      )
    """).fetchone()[0] == 1

    if not exists:
        db.execute(clean_sql("""
           create virtual table todos using fts4(
                user,
                text,
                added,
                tokenize=porter
           )"""))

    db.commit()

    db_ready = True


def db_getall(db, nick, limit=-1):
    return db.execute("""
        select added, text
            from todos
            where lower(user) = lower(?)
            order by added desc
            limit ?

        """, (nick, limit))


def db_get(db, nick, note_id):
    return db.execute("""
        select added, text from todos
        where lower(user) = lower(?)
        order by added desc
        limit 1
        offset ?
    """, (nick, note_id)).fetchone()


def db_del(db, nick, limit='all'):
    row = db.execute("""
        delete from todos
        where rowid in (
          select rowid from todos
          where lower(user) = lower(?)
          order by added desc
          limit ?
          offset ?)
     """, (nick,
           -1 if limit == 'all' else 1,
           0 if limit == 'all' else limit))
    db.commit()
    return row


def db_add(db, nick, text):
    db.execute("""
        insert into todos (user, text, added)
        values (?, ?, CURRENT_TIMESTAMP)
    """, (nick, text))
    db.commit()


def db_search(db, nick, query):
    return db.execute("""
        select added, text
        from todos
        where todos match ?
        and lower(user) = lower(?)
        order by added desc
    """, (query, nick))


@hook.command("notes")
@hook.command
def note(inp, nick='', chan='', db=None, notice=None, bot=None):
    """note(s) <add|del|list|search> args -- Manipulates your list of notes."""

    db_init(db)

    parts = inp.split()
    cmd = parts[0].lower()

    args = parts[1:]

    # code to allow users to access each others factoids and a copy of help
    # ".note (add|del|list|search) [@user] args -- Manipulates your list of todos."
    #if len(args) and args[0].startswith("@"):
    #    nick = args[0][1:]
    #    args = args[1:]

    if cmd == 'add':
        if not len(args):
            return "no text"

        text = " ".join(args)

        db_add(db, nick, text)

        notice("Note added!")
        return
    elif cmd == 'get':
        if len(args):
            try:
                index = int(args[0])
            except ValueError:
                notice("Invalid number format.")
                return
        else:
            index = 0

        row = db_get(db, nick, index)

        if not row:
            notice("No such entry.")
            return
        notice("[{}]: {}: {}".format(index, row[0], row[1]))
    elif cmd == 'del' or cmd == 'delete' or cmd == 'remove':
        if not len(args):
            return "error"

        if args[0] == 'all':
            index = 'all'
        else:
            try:
                index = int(args[0])
            except ValueError:
                notice("Invalid number.")
                return

        rows = db_del(db, nick, index)

        notice("Deleted {} entries".format(rows.rowcount))
    elif cmd == 'list':
        limit = -1

        if len(args):
            try:
                limit = int(args[0])
                limit = max(-1, limit)
            except ValueError:
                notice("Invalid number.")
                return

        rows = db_getall(db, nick, limit)

        found = False

        for (index, row) in enumerate(rows):
            notice("[{}]: {}: {}".format(index, row[0], row[1]))
            found = True

        if not found:
            notice("{} has no entries.".format(nick))
    elif cmd == 'search':
        if not len(args):
            notice("No search query given!")
            return
        query = " ".join(args)
        rows = db_search(db, nick, query)

        found = False

        for (index, row) in enumerate(rows):
            notice("[{}]: {}: {}".format(index, row[0], row[1]))
            found = True

        if not found:
            notice("{} has no matching entries for: {}".format(nick, query))

    else:
        notice("Unknown command: {}".format(cmd))

########NEW FILE########
__FILENAME__ = op
from util import hook


def mode_cmd(mode, text, inp, chan, conn, notice):
    """ generic mode setting function """
    split = inp.split(" ")
    if split[0].startswith("#"):
        channel = split[0]
        target = split[1]
        notice("Attempting to {} {} in {}...".format(text, target, channel))
        conn.send("MODE {} {} {}".format(channel, mode, target))
    else:
        channel = chan
        target = split[0]
        notice("Attempting to {} {} in {}...".format(text, target, channel))
        conn.send("MODE {} {} {}".format(channel, mode, target))


def mode_cmd_no_target(mode, text, inp, chan, conn, notice):
    """ generic mode setting function without a target"""
    split = inp.split(" ")
    if split[0].startswith("#"):
        channel = split[0]
        notice("Attempting to {} {}...".format(text, channel))
        conn.send("MODE {} {}".format(channel, mode))
    else:
        channel = chan
        notice("Attempting to {} {}...".format(text, channel))
        conn.send("MODE {} {}".format(channel, mode))


@hook.command(permissions=["op_ban", "op"])
def ban(inp, conn=None, chan=None, notice=None):
    """ban [channel] <user> -- Makes the bot ban <user> in [channel].
    If [channel] is blank the bot will ban <user> in
    the channel the command was used in."""
    mode_cmd("+b", "ban", inp, chan, conn, notice)


@hook.command(permissions=["op_ban", "op"])
def unban(inp, conn=None, chan=None, notice=None):
    """unban [channel] <user> -- Makes the bot unban <user> in [channel].
    If [channel] is blank the bot will unban <user> in
    the channel the command was used in."""
    mode_cmd("-b", "unban", inp, chan, conn, notice)


@hook.command(permissions=["op_quiet", "op"])
def quiet(inp, conn=None, chan=None, notice=None):
    """quiet [channel] <user> -- Makes the bot quiet <user> in [channel].
    If [channel] is blank the bot will quiet <user> in
    the channel the command was used in."""
    mode_cmd("+q", "quiet", inp, chan, conn, notice)


@hook.command(permissions=["op_quiet", "op"])
def unquiet(inp, conn=None, chan=None, notice=None):
    """unquiet [channel] <user> -- Makes the bot unquiet <user> in [channel].
    If [channel] is blank the bot will unquiet <user> in
    the channel the command was used in."""
    mode_cmd("-q", "unquiet", inp, chan, conn, notice)


@hook.command(permissions=["op_voice", "op"])
def voice(inp, conn=None, chan=None, notice=None):
    """voice [channel] <user> -- Makes the bot voice <user> in [channel].
    If [channel] is blank the bot will voice <user> in
    the channel the command was used in."""
    mode_cmd("+v", "voice", inp, chan, conn, notice)


@hook.command(permissions=["op_voice", "op"])
def devoice(inp, conn=None, chan=None, notice=None):
    """devoice [channel] <user> -- Makes the bot devoice <user> in [channel].
    If [channel] is blank the bot will devoice <user> in
    the channel the command was used in."""
    mode_cmd("-v", "devoice", inp, chan, conn, notice)


@hook.command(permissions=["op_op", "op"])
def op(inp, conn=None, chan=None, notice=None):
    """op [channel] <user> -- Makes the bot op <user> in [channel].
    If [channel] is blank the bot will op <user> in
    the channel the command was used in."""
    mode_cmd("+o", "op", inp, chan, conn, notice)


@hook.command(permissions=["op_op", "op"])
def deop(inp, conn=None, chan=None, notice=None):
    """deop [channel] <user> -- Makes the bot deop <user> in [channel].
    If [channel] is blank the bot will deop <user> in
    the channel the command was used in."""
    mode_cmd("-o", "deop", inp, chan, conn, notice)


@hook.command(permissions=["op_topic", "op"])
def topic(inp, conn=None, chan=None):
    """topic [channel] <topic> -- Change the topic of a channel."""
    split = inp.split(" ")
    if split[0].startswith("#"):
        message = " ".join(split[1:])
        chan = split[0]
    else:
        message = " ".join(split)
    conn.send("TOPIC {} :{}".format(chan, message))


@hook.command(permissions=["op_kick", "op"])
def kick(inp, chan=None, conn=None, notice=None):
    """kick [channel] <user> [reason] -- Makes the bot kick <user> in [channel]
    If [channel] is blank the bot will kick the <user> in
    the channel the command was used in."""
    split = inp.split(" ")

    if split[0].startswith("#"):
        channel = split[0]
        target = split[1]
        if len(split) > 2:
            reason = " ".join(split[2:])
            out = "KICK {} {}: {}".format(channel, target, reason)
        else:
            out = "KICK {} {}".format(channel, target)
    else:
        channel = chan
        target = split[0]
        if len(split) > 1:
            reason = " ".join(split[1:])
            out = "KICK {} {} :{}".format(channel, target, reason)
        else:
            out = "KICK {} {}".format(channel, target)

    notice("Attempting to kick {} from {}...".format(target, channel))
    conn.send(out)


@hook.command(permissions=["op_rem", "op"])
def remove(inp, chan=None, conn=None):
    """remove [channel] [user] -- Force a user to part from a channel."""
    split = inp.split(" ")
    if split[0].startswith("#"):
        message = " ".join(split[1:])
        chan = split[0]
        out = "REMOVE {} :{}".format(chan, message)
    else:
        message = " ".join(split)
        out = "REMOVE {} :{}".format(chan, message)
    conn.send(out)


@hook.command(permissions=["op_mute", "op"], autohelp=False)
def mute(inp, conn=None, chan=None, notice=None):
    """mute [channel] -- Makes the bot mute a channel..
    If [channel] is blank the bot will mute
    the channel the command was used in."""
    mode_cmd_no_target("+m", "mute", inp, chan, conn, notice)


@hook.command(permissions=["op_mute", "op"], autohelp=False)
def unmute(inp, conn=None, chan=None, notice=None):
    """mute [channel] -- Makes the bot mute a channel..
    If [channel] is blank the bot will mute
    the channel the command was used in."""
    mode_cmd_no_target("-m", "unmute", inp, chan, conn, notice)


@hook.command(permissions=["op_lock", "op"], autohelp=False)
def lock(inp, conn=None, chan=None, notice=None):
    """lock [channel] -- Makes the bot lock a channel.
    If [channel] is blank the bot will mute
    the channel the command was used in."""
    mode_cmd_no_target("+i", "lock", inp, chan, conn, notice)


@hook.command(permissions=["op_lock", "op"], autohelp=False)
def unlock(inp, conn=None, chan=None, notice=None):
    """unlock [channel] -- Makes the bot unlock a channel..
    If [channel] is blank the bot will mute
    the channel the command was used in."""
    mode_cmd_no_target("-i", "unlock", inp, chan, conn, notice)

########NEW FILE########
__FILENAME__ = osrc
from bs4 import BeautifulSoup

from util import hook, http, web


user_url = "http://osrc.dfm.io/{}"


@hook.command
def osrc(inp):
    """osrc <github user> -- Gets an Open Source Report Card for <github user>"""

    user_nick = inp.strip()
    url = user_url.format(user_nick)

    try:
        soup = http.get_soup(url)
    except (http.HTTPError, http.URLError):
        return "Couldn't find any stats for this user."

    report = soup.find("div", {"id": "description"}).find("p").get_text()

    # Split and join to remove all the excess whitespace, slice the
    # string to remove the trailing full stop.
    report = " ".join(report.split())[:-1]

    short_url = web.try_isgd(url)

    return "{} - {}".format(report, short_url)

########NEW FILE########
__FILENAME__ = password
# TODO: Add some kind of pronounceable password generation
# TODO: Improve randomness
import string
import random

from util import hook


@hook.command
def password(inp, notice=None):
    """password <length> [types] -- Generates a password of <length> (default 10).
    [types] can include 'alpha', 'no caps', 'numeric', 'symbols' or any combination of the inp, eg. 'numbers symbols'"""
    okay = []

    # find the length needed for the password
    numb = inp.split(" ")

    try:
        length = int(numb[0])
    except ValueError:
        length = 10

    # add alpha characters
    if "alpha" in inp or "letter" in inp:
        okay = okay + list(string.ascii_lowercase)
        #adds capital characters if not told not to
        if "no caps" not in inp:
            okay = okay + list(string.ascii_uppercase)

    # add numbers
    if "numeric" in inp or "number" in inp:
        okay = okay + [str(x) for x in xrange(0, 10)]

    # add symbols
    if "symbol" in inp:
        sym = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '-', '=', '_', '+', '[', ']', '{', '}', '\\', '|', ';',
               ':', "'", '.', '>', ',', '<', '/', '?', '`', '~', '"']
        okay += okay + sym

    # defaults to lowercase alpha password if the okay list is empty
    if not okay:
        okay = okay + list(string.ascii_lowercase)

    pw = ""

    # generates password
    for x in range(length):
        pw = pw + random.choice(okay)

    notice(pw)

########NEW FILE########
__FILENAME__ = ping
# ping plugin by neersighted
import subprocess
import re
import os

from util import hook


ping_regex = re.compile(r"(\d+.\d+)/(\d+.\d+)/(\d+.\d+)/(\d+.\d+)")


@hook.command
def ping(inp, reply=None):
    """ping <host> [count] -- Pings <host> [count] times."""

    if os.name == "nt":
        return "Sorry, this command is not supported on Windows systems."
        # TODO: Rewrite this entire command to work on Windows, somehow

    args = inp.split(' ')
    host = args[0]

    # check for a second argument and set the ping count
    if len(args) > 1:
        count = int(args[1])
        if count > 20:
            count = 20
    else:
        count = 5

    count = str(count)

    # I suck at regex, but this is causing issues, and I'm just going to remove it
    # I assume it's no longer needed with the way we run the process
    # host = re.sub(r'([^\s\w\.])+', '', host)

    reply("Attempting to ping {} {} times...".format(host, count))

    pingcmd = subprocess.check_output(["ping", "-c", count, host])
    if "request timed out" in pingcmd or "unknown host" in pingcmd:
        return "error: could not ping host"
    else:
        m = re.search(ping_regex, pingcmd)
        return "min: %sms, max: %sms, average: %sms, range: %sms, count: %s" \
               % (m.group(1), m.group(3), m.group(2), m.group(4), count)

########NEW FILE########
__FILENAME__ = plpaste
from util import hook, web


@hook.command(permissions=["adminonly"])
def plpaste(inp):
    if "/" in inp and inp.split("/")[0] != "util":
        return "Invalid input"
    try:
        with open("plugins/%s.py" % inp) as f:
            return web.haste(f.read(), ext='py')
    except IOError:
        return "Plugin not found (must be in plugins folder)"

########NEW FILE########
__FILENAME__ = potato
# coding=utf-8
import re
import random

from util import hook


potatoes = ['AC Belmont', 'AC Blue Pride', 'AC Brador', 'AC Chaleur', 'AC Domino', 'AC Dubuc', 'AC Glacier Chip',
            'AC Maple Gold', 'AC Novachip', 'AC Peregrine Red', 'AC Ptarmigan', 'AC Red Island', 'AC Saguenor',
            'AC Stampede Russet', 'AC Sunbury', 'Abeille', 'Abnaki', 'Acadia', 'Acadia Russet', 'Accent',
            'Adirondack Blue', 'Adirondack Red', 'Adora', 'Agria', 'All Blue', 'All Red', 'Alpha', 'Alta Russet',
            'Alturas Russet', 'Amandine', 'Amisk', 'Andover', 'Anoka', 'Anson', 'Aquilon', 'Arran Consul', 'Asterix',
            'Atlantic', 'Austrian Crescent', 'Avalanche', 'Banana', 'Bannock Russet', 'Batoche', 'BeRus',
            'Belle De Fonteney', 'Belleisle', 'Bintje', 'Blossom', 'Blue Christie', 'Blue Mac', 'Brigus',
            'Brise du Nord', 'Butte', 'Butterfinger', 'Caesar', 'CalWhite', 'CalRed', 'Caribe', 'Carlingford',
            'Carlton', 'Carola', 'Cascade', 'Castile', 'Centennial Russet', 'Century Russet', 'Charlotte', 'Cherie',
            'Cherokee', 'Cherry Red', 'Chieftain', 'Chipeta', 'Coastal Russet', 'Colorado Rose', 'Concurrent',
            'Conestoga', 'Cowhorn', 'Crestone Russet', 'Crispin', 'Cupids', 'Daisy Gold', 'Dakota Pearl', 'Defender',
            'Delikat', 'Denali', 'Desiree', 'Divina', 'Dundrod', 'Durango Red', 'Early Rose', 'Elba', 'Envol',
            'Epicure', 'Eramosa', 'Estima', 'Eva', 'Fabula', 'Fambo', 'Fremont Russet', 'French Fingerling',
            'Frontier Russet', 'Fundy', 'Garnet Chile', 'Gem Russet', 'GemStar Russet', 'Gemchip', 'German Butterball',
            'Gigant', 'Goldrush', 'Granola', 'Green Mountain', 'Haida', 'Hertha', 'Hilite Russet', 'Huckleberry',
            'Hunter', 'Huron', 'IdaRose', 'Innovator', 'Irish Cobbler', 'Island Sunshine', 'Ivory Crisp',
            'Jacqueline Lee', 'Jemseg', 'Kanona', 'Katahdin', 'Kennebec', "Kerr's Pink", 'Keswick', 'Keuka Gold',
            'Keystone Russet', 'King Edward VII', 'Kipfel', 'Klamath Russet', 'Krantz', 'LaRatte', 'Lady Rosetta',
            'Latona', 'Lemhi Russet', 'Liberator', 'Lili', 'MaineChip', 'Marfona', 'Maris Bard', 'Maris Piper',
            'Matilda', 'Mazama', 'McIntyre', 'Michigan Purple', 'Millenium Russet', 'Mirton Pearl', 'Modoc', 'Mondial',
            'Monona', 'Morene', 'Morning Gold', 'Mouraska', 'Navan', 'Nicola', 'Nipigon', 'Niska', 'Nooksack',
            'NorValley', 'Norchip', 'Nordonna', 'Norgold Russet', 'Norking Russet', 'Norland', 'Norwis', 'Obelix',
            'Ozette', 'Peanut', 'Penta', 'Peribonka', 'Peruvian Purple', 'Pike', 'Pink Pearl', 'Prospect', 'Pungo',
            'Purple Majesty', 'Purple Viking', 'Ranger Russet', 'Reba', 'Red Cloud', 'Red Gold', 'Red La Soda',
            'Red Pontiac', 'Red Ruby', 'Red Thumb', 'Redsen', 'Rocket', 'Rose Finn Apple', 'Rose Gold', 'Roselys',
            'Rote Erstling', 'Ruby Crescent', 'Russet Burbank', 'Russet Legend', 'Russet Norkotah', 'Russet Nugget',
            'Russian Banana', 'Saginaw Gold', 'Sangre', 'Sant�', 'Satina', 'Saxon', 'Sebago', 'Shepody', 'Sierra',
            'Silverton Russet', 'Simcoe', 'Snowden', 'Spunta', "St. John's", 'Summit Russet', 'Sunrise', 'Superior',
            'Symfonia', 'Tolaas', 'Trent', 'True Blue', 'Ulla', 'Umatilla Russet', 'Valisa', 'Van Gogh', 'Viking',
            'Wallowa Russet', 'Warba', 'Western Russet', 'White Rose', 'Willamette', 'Winema', 'Yellow Finn',
            'Yukon Gold']


@hook.command
def potato(inp, action=None):
    """potato <user> - Makes <user> a tasty little potato."""
    inp = inp.strip()

    if not re.match("^[A-Za-z0-9_|.-\]\[]*$", inp.lower()):
        return "I cant make a tasty potato for that user!"

    potato_type = random.choice(potatoes)
    size = random.choice(['small', 'little', 'mid-sized', 'medium-sized', 'large', 'gigantic'])
    flavor = random.choice(['tasty', 'delectable', 'delicious', 'yummy', 'toothsome', 'scrumptious', 'luscious'])
    method = random.choice(['bakes', 'fries', 'boils', 'roasts'])
    side_dish = random.choice(['side salad', 'dollop of sour cream', 'piece of chicken', 'bowl of shredded bacon'])

    action("{} a {} {} {} potato for {} and serves it with a small {}!".format(method, flavor, size, potato_type, inp,
                                                                               side_dish))

########NEW FILE########
__FILENAME__ = pre
import datetime

from util import hook, http, timesince


@hook.command("scene")
@hook.command
def pre(inp):
    """pre <query> -- searches scene releases using orlydb.com"""

    try:
        h = http.get_html("http://orlydb.com/", q=inp)
    except http.HTTPError as e:
        return 'Unable to fetch results: {}'.format(e)

    results = h.xpath("//div[@id='releases']/div/span[@class='release']/..")

    if not results:
        return "No results found."

    result = results[0]

    date = result.xpath("span[@class='timestamp']/text()")[0]
    section = result.xpath("span[@class='section']//text()")[0]
    name = result.xpath("span[@class='release']/text()")[0]

    # parse date/time
    date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    date_string = date.strftime("%d %b %Y")
    since = timesince.timesince(date)

    size = result.xpath("span[@class='inforight']//text()")
    if size:
        size = ' - ' + size[0].split()[0]
    else:
        size = ''

    return '{} - {}{} - {} ({} ago)'.format(section, name, size, date_string, since)

########NEW FILE########
__FILENAME__ = python
from util import hook
from util.pyexec import eval_py


@hook.command
def python(inp):
    """python <prog> -- Executes <prog> as Python code."""

    return eval_py(inp)

########NEW FILE########
__FILENAME__ = qrcode
# Plugin by https://github.com/Mu5tank05
from util import hook, web, http


@hook.command('qr')
@hook.command
def qrcode(inp):
    """qrcode [link] returns a link for a QR code."""

    args = {
        "cht": "qr",  # chart type (QR)
        "chs": "200x200",  # dimensions
        "chl": inp  # data
    }

    link = http.prepare_url("http://chart.googleapis.com/chart", args)

    return web.try_isgd(link)

########NEW FILE########
__FILENAME__ = quote
import random
import re
import time

from util import hook


def format_quote(q, num, n_quotes):
    """Returns a formatted string of a quote"""
    ctime, nick, msg = q
    return "[{}/{}] <{}> {}".format(num, n_quotes,
                                    nick, msg)


def create_table_if_not_exists(db):
    """Creates an empty quote table if one does not already exist"""
    db.execute("create table if not exists quote"
               "(chan, nick, add_nick, msg, time real, deleted default 0, "
               "primary key (chan, nick, msg))")
    db.commit()


def add_quote(db, chan, nick, add_nick, msg):
    """Adds a quote to a nick, returns message string"""
    try:
        db.execute('''INSERT OR FAIL INTO quote
                      (chan, nick, add_nick, msg, time)
                      VALUES(?,?,?,?,?)''',
                   (chan, nick, add_nick, msg, time.time()))
        db.commit()
    except db.IntegrityError:
        return "Message already stored, doing nothing."
    return "Quote added."


def del_quote(db, chan, nick, add_nick, msg):
    """Deletes a quote from a nick"""
    db.execute('''UPDATE quote SET deleted = 1 WHERE
                  chan=? AND lower(nick)=lower(?) AND msg=msg''')
    db.commit()


def get_quote_num(num, count, name):
    """Returns the quote number to fetch from the DB"""
    if num:  # Make sure num is a number if it isn't false
        num = int(num)
    if count == 0:  # Error on no quotes
        raise Exception("No quotes found for {}.".format(name))
    if num and num < 0:  # Count back if possible
        num = count + num + 1 if num + count > -1 else count + 1
    if num and num > count:  # If there are not enough quotes, raise an error
        raise Exception("I only have {} quote{} for {}.".format(count, ('s', '')[count == 1], name))
    if num and num == 0:  # If the number is zero, set it to one
        num = 1
    if not num:  # If a number is not given, select a random one
        num = random.randint(1, count)
    return num


def get_quote_by_nick(db, nick, num=False):
    """Returns a formatted quote from a nick, random or selected by number"""
    count = db.execute('''SELECT COUNT(*) FROM quote WHERE deleted != 1
                          AND lower(nick) = lower(?)''', [nick]).fetchall()[0][0]

    try:
        num = get_quote_num(num, count, nick)
    except Exception as error_message:
        return error_message

    quote = db.execute('''SELECT time, nick, msg
                          FROM quote
                          WHERE deleted != 1
                          AND lower(nick) = lower(?)
                          ORDER BY time
                          LIMIT ?, 1''', (nick, (num - 1))).fetchall()[0]
    return format_quote(quote, num, count)


def get_quote_by_nick_chan(db, chan, nick, num=False):
    """Returns a formatted quote from a nick in a channel, random or selected by number"""
    count = db.execute('''SELECT COUNT(*)
                          FROM quote
                          WHERE deleted != 1
                          AND chan = ?
                          AND lower(nick) = lower(?)''', (chan, nick)).fetchall()[0][0]

    try:
        num = get_quote_num(num, count, nick)
    except Exception as error_message:
        return error_message

    quote = db.execute('''SELECT time, nick, msg
                          FROM quote
                          WHERE deleted != 1
                          AND chan = ?
                          AND lower(nick) = lower(?)
                          ORDER BY time
                          LIMIT ?, 1''', (chan, nick, (num - 1))).fetchall()[0]
    return format_quote(quote, num, count)


def get_quote_by_chan(db, chan, num=False):
    """Returns a formatted quote from a channel, random or selected by number"""
    count = db.execute('''SELECT COUNT(*)
                          FROM quote
                          WHERE deleted != 1
                          AND chan = ?''', (chan,)).fetchall()[0][0]

    try:
        num = get_quote_num(num, count, chan)
    except Exception as error_message:
        return error_message

    quote = db.execute('''SELECT time, nick, msg
                          FROM quote
                          WHERE deleted != 1
                          AND chan = ?
                          ORDER BY time
                          LIMIT ?, 1''', (chan, (num - 1))).fetchall()[0]
    return format_quote(quote, num, count)


@hook.command('q')
@hook.command
def quote(inp, nick='', chan='', db=None, notice=None):
    """quote [#chan] [nick] [#n]/.quote add <nick> <msg>
    Gets random or [#n]th quote by <nick> or from <#chan>/adds quote."""
    create_table_if_not_exists(db)

    add = re.match(r"add[^\w@]+(\S+?)>?\s+(.*)", inp, re.I)
    retrieve = re.match(r"(\S+)(?:\s+#?(-?\d+))?$", inp)
    retrieve_chan = re.match(r"(#\S+)\s+(\S+)(?:\s+#?(-?\d+))?$", inp)

    if add:
        quoted_nick, msg = add.groups()
        notice(add_quote(db, chan, quoted_nick, nick, msg))
        return
    elif retrieve:
        select, num = retrieve.groups()
        by_chan = True if select.startswith('#') else False
        if by_chan:
            return get_quote_by_chan(db, select, num)
        else:
            return get_quote_by_nick(db, select, num)
    elif retrieve_chan:
        chan, nick, num = retrieve_chan.groups()
        return get_quote_by_nick_chan(db, chan, nick, num)

    notice(quote.__doc__)

########NEW FILE########
__FILENAME__ = rdio
import urllib
import json
import re

import oauth2 as oauth

from util import hook


def getdata(inp, types, api_key, api_secret):
    consumer = oauth.Consumer(api_key, api_secret)
    client = oauth.Client(consumer)
    response = client.request('http://api.rdio.com/1/', 'POST',
                              urllib.urlencode({'method': 'search', 'query': inp, 'types': types, 'count': '1'}))
    data = json.loads(response[1])
    return data


@hook.command
def rdio(inp, bot=None):
    """ rdio <search term> - alternatives: .rdiot (track), .rdioar (artist), .rdioal (album) """
    api_key = bot.config.get("api_keys", {}).get("rdio_key")
    api_secret = bot.config.get("api_keys", {}).get("rdio_secret")
    if not api_key:
        return "error: no api key set"
    data = getdata(inp, "Track,Album,Artist", api_key, api_secret)
    try:
        info = data['result']['results'][0]
    except IndexError:
        return "No results."
    if 'name' in info:
        if 'artist' in info and 'album' in info:  # Track
            name = info['name']
            artist = info['artist']
            album = info['album']
            url = info['shortUrl']
            return u"\x02{}\x02 by \x02{}\x02 - {} {}".format(name, artist, album, url)
        elif 'artist' in info and not 'album' in info:  # Album
            name = info['name']
            artist = info['artist']
            url = info['shortUrl']
            return u"\x02{}\x02 by \x02{}\x02 - {}".format(name, artist, url)
        else:  # Artist
            name = info['name']
            url = info['shortUrl']
            return u"\x02{}\x02 - {}".format(name, url)


@hook.command
def rdiot(inp, bot=None):
    """ rdiot <search term> - Search for tracks on rdio """
    api_key = bot.config.get("api_keys", {}).get("rdio_key")
    api_secret = bot.config.get("api_keys", {}).get("rdio_secret")
    if not api_key:
        return "error: no api key set"
    data = getdata(inp, "Track", api_key, api_secret)
    try:
        info = data['result']['results'][0]
    except IndexError:
        return "No results."
    name = info['name']
    artist = info['artist']
    album = info['album']
    url = info['shortUrl']
    return u"\x02{}\x02 by \x02{}\x02 - {} - {}".format(name, artist, album, url)


@hook.command
def rdioar(inp, bot=None):
    """ rdioar <search term> - Search for artists on rdio """
    api_key = bot.config.get("api_keys", {}).get("rdio_key")
    api_secret = bot.config.get("api_keys", {}).get("rdio_secret")
    if not api_key:
        return "error: no api key set"
    data = getdata(inp, "Artist", api_key, api_secret)
    try:
        info = data['result']['results'][0]
    except IndexError:
        return "No results."
    name = info['name']
    url = info['shortUrl']
    return u"\x02{}\x02 - {}".format(name, url)


@hook.command
def rdioal(inp, bot=None):
    """ rdioal <search term> - Search for albums on rdio """
    api_key = bot.config.get("api_keys", {}).get("rdio_key")
    api_secret = bot.config.get("api_keys", {}).get("rdio_secret")
    if not api_key:
        return "error: no api key set"
    data = getdata(inp, "Album", api_key, api_secret)
    try:
        info = data['result']['results'][0]
    except IndexError:
        return "No results."
    name = info['name']
    artist = info['artist']
    url = info['shortUrl']
    return u"\x02{}\x02 by \x02{}\x02 - {}".format(name, artist, url)


rdio_re = (r'(.*:)//(rd.io|www.rdio.com|rdio.com)(:[0-9]+)?(.*)', re.I)


@hook.regex(*rdio_re)
def rdio_url(match, bot=None):
    api_key = bot.config.get("api_keys", {}).get("rdio_key")
    api_secret = bot.config.get("api_keys", {}).get("rdio_secret")
    if not api_key:
        return None
    url = match.group(1) + "//" + match.group(2) + match.group(4)
    consumer = oauth.Consumer(api_key, api_secret)
    client = oauth.Client(consumer)
    response = client.request('http://api.rdio.com/1/', 'POST',
                              urllib.urlencode({'method': 'getObjectFromUrl', 'url': url}))
    data = json.loads(response[1])
    info = data['result']
    if 'name' in info:
        if 'artist' in info and 'album' in info:  # Track
            name = info['name']
            artist = info['artist']
            album = info['album']
            return u"Rdio track: \x02{}\x02 by \x02{}\x02 - {}".format(name, artist, album)
        elif 'artist' in info and not 'album' in info:  # Album
            name = info['name']
            artist = info['artist']
            return u"Rdio album: \x02{}\x02 by \x02{}\x02".format(name, artist)
        else:  # Artist
            name = info['name']
            return u"Rdio artist: \x02{}\x02".format(name)

########NEW FILE########
__FILENAME__ = recipe
import random

from util import hook, http, web

metadata_url = "http://omnidator.appspot.com/microdata/json/?url={}"

base_url = "http://www.cookstr.com"
search_url = base_url + "/searches"
random_url = search_url + "/surprise"

# set this to true to censor this plugin!
censor = True
phrases = [
    u"EAT SOME FUCKING \x02{}\x02",
    u"YOU WON'T NOT MAKE SOME FUCKING \x02{}\x02",
    u"HOW ABOUT SOME FUCKING \x02{}?\x02",
    u"WHY DON'T YOU EAT SOME FUCKING \x02{}?\x02",
    u"MAKE SOME FUCKING \x02{}\x02",
    u"INDUCE FOOD COMA WITH SOME FUCKING \x02{}\x02"
]

clean_key = lambda i: i.split("#")[1]


class ParseError(Exception):
    pass


def get_data(url):
    """ Uses the omnidator API to parse the metadata from the provided URL """
    try:
        omni = http.get_json(metadata_url.format(url))
    except (http.HTTPError, http.URLError) as e:
        raise ParseError(e)
    schemas = omni["@"]
    for d in schemas:
        if d["a"] == "<http://schema.org/Recipe>":
            data = {clean_key(key): value for (key, value) in d.iteritems()
                    if key.startswith("http://schema.org/Recipe")}
            return data
    raise ParseError("No recipe data found")


@hook.command(autohelp=False)
def recipe(inp):
    """recipe [term] - Gets a recipe for [term], or ets a random recipe if [term] is not provided"""
    if inp:
        # get the recipe URL by searching
        try:
            search = http.get_soup(search_url, query=inp.strip())
        except (http.HTTPError, http.URLError) as e:
            return "Could not get recipe: {}".format(e)

        # find the list of results
        result_list = search.find('div', {'class': 'found_results'})

        if result_list:
            results = result_list.find_all('div', {'class': 'recipe_result'})
        else:
            return "No results"

        # pick a random front page result
        result = random.choice(results)

        # extract the URL from the result
        url = base_url + result.find('div', {'class': 'image-wrapper'}).find('a')['href']

    else:
        # get a random recipe URL
        try:
            page = http.open(random_url)
        except (http.HTTPError, http.URLError) as e:
            return "Could not get recipe: {}".format(e)
        url = page.geturl()

    # use get_data() to get the recipe info from the URL
    try:
        data = get_data(url)
    except ParseError as e:
        return "Could not parse recipe: {}".format(e)

    name = data["name"].strip()
    return u"Try eating \x02{}!\x02 - {}".format(name, web.try_isgd(url))


@hook.command(autohelp=False)
def dinner(inp):
    """dinner - WTF IS FOR DINNER"""
    try:
        page = http.open(random_url)
    except (http.HTTPError, http.URLError) as e:
        return "Could not get recipe: {}".format(e)
    url = page.geturl()

    try:
        data = get_data(url)
    except ParseError as e:
        return "Could not parse recipe: {}".format(e)

    name = data["name"].strip().upper()
    text = random.choice(phrases).format(name)

    if censor:
        text = text.replace("FUCK", "F**K")

    return u"{} - {}".format(text, web.try_isgd(url))

########NEW FILE########
__FILENAME__ = reddit
from datetime import datetime
import re
import random

from util import hook, http, text, timesince


reddit_re = (r'.*(((www\.)?reddit\.com/r|redd\.it)[^ ]+)', re.I)

base_url = "http://reddit.com/r/{}/.json"
short_url = "http://redd.it/{}"


@hook.regex(*reddit_re)
def reddit_url(match):
    thread = http.get_html(match.group(0))

    title = thread.xpath('//title/text()')[0]
    upvotes = thread.xpath("//span[@class='upvotes']/span[@class='number']/text()")[0]
    downvotes = thread.xpath("//span[@class='downvotes']/span[@class='number']/text()")[0]
    author = thread.xpath("//div[@id='siteTable']//a[contains(@class,'author')]/text()")[0]
    timeago = thread.xpath("//div[@id='siteTable']//p[@class='tagline']/time/text()")[0]
    comments = thread.xpath("//div[@id='siteTable']//a[@class='comments']/text()")[0]

    return u'\x02{}\x02 - posted by \x02{}\x02 {} ago - {} upvotes, {} downvotes - {}'.format(
        title, author, timeago, upvotes, downvotes, comments)


@hook.command(autohelp=False)
def reddit(inp):
    """reddit <subreddit> [n] -- Gets a random post from <subreddit>, or gets the [n]th post in the subreddit."""
    id_num = None

    if inp:
        # clean and split the input
        parts = inp.lower().strip().split()

        # find the requested post number (if any)
        if len(parts) > 1:
            url = base_url.format(parts[0].strip())
            try:
                id_num = int(parts[1]) - 1
            except ValueError:
                return "Invalid post number."
        else:
            url = base_url.format(parts[0].strip())
    else:
        url = "http://reddit.com/.json"

    try:
        data = http.get_json(url, user_agent=http.ua_chrome)
    except Exception as e:
        return "Error: " + str(e)
    data = data["data"]["children"]

    # get the requested/random post
    if id_num is not None:
        try:
            item = data[id_num]["data"]
        except IndexError:
            length = len(data)
            return "Invalid post number. Number must be between 1 and {}.".format(length)
    else:
        item = random.choice(data)["data"]

    item["title"] = text.truncate_str(item["title"], 50)
    item["link"] = short_url.format(item["id"])

    raw_time = datetime.fromtimestamp(int(item["created_utc"]))
    item["timesince"] = timesince.timesince(raw_time)

    if item["over_18"]:
        item["warning"] = " \x02NSFW\x02"
    else:
        item["warning"] = ""

    return u"\x02{title} : {subreddit}\x02 - posted by \x02{author}\x02" \
           " {timesince} ago - {ups} upvotes, {downs} downvotes -" \
           " {link}{warning}".format(**item)

########NEW FILE########
__FILENAME__ = regex_chans
from util import hook


# Default value.
# If True, all channels without a setting will have regex enabled
# If False, all channels without a setting will have regex disabled
default_enabled = True

db_ready = False


def db_init(db):
    global db_ready
    if not db_ready:
        db.execute("CREATE TABLE IF NOT EXISTS regexchans(channel PRIMARY KEY, status)")
        db.commit()
        db_ready = True


def get_status(db, channel):
    row = db.execute("SELECT status FROM regexchans WHERE channel = ?", [channel]).fetchone()
    if row:
        return row[0]
    else:
        return None


def set_status(db, channel, status):
    row = db.execute("REPLACE INTO regexchans (channel, status) VALUES(?, ?)", [channel, status])
    db.commit()


def delete_status(db, channel):
    row = db.execute("DELETE FROM regexchans WHERE channel = ?", [channel])
    db.commit()


def list_status(db):
    row = db.execute("SELECT * FROM regexchans").fetchall()
    result = None
    for values in row:
        if result:
            result += u", {}: {}".format(values[0], values[1])
        else:
            result = u"{}: {}".format(values[0], values[1])
    return result


@hook.sieve
def sieve_regex(bot, inp, func, kind, args):
    db = bot.get_db_connection(inp.conn)
    db_init(db)
    if kind == 'regex' and inp.chan.startswith("#") and func.__name__ != 'factoid':
        chanstatus = get_status(db, inp.chan)
        if chanstatus != "ENABLED" and (chanstatus == "DISABLED" or not default_enabled):
            print u"Denying input.raw={}, kind={}, args={} from {}".format(inp.raw, kind, args, inp.chan)
            return None
        print u"Allowing input.raw={}, kind={}, args={} from {}".format(inp.raw, kind, args, inp.chan)

    return inp


@hook.command(permissions=["botcontrol"])
def enableregex(inp, db=None, message=None, notice=None, chan=None, nick=None):
    db_init(db)
    inp = inp.strip().lower()
    if not inp:
        channel = chan
    elif inp.startswith("#"):
        channel = inp
    else:
        channel = u"#{}".format(inp)

    message(u"Enabling regex matching (youtube, etc) (issued by {})".format(nick), target=channel)
    notice(u"Enabling regex matching (youtube, etc) in channel {}".format(channel))
    set_status(db, channel, "ENABLED")


@hook.command(permissions=["botcontrol"])
def disableregex(inp, db=None, message=None, notice=None, chan=None, nick=None):
    db_init(db)
    inp = inp.strip().lower()
    if not inp:
        channel = chan
    elif inp.startswith("#"):
        channel = inp
    else:
        channel = u"#{}".format(inp)

    message(u"Disabling regex matching (youtube, etc) (issued by {})".format(nick), target=channel)
    notice(u"Disabling regex matching (youtube, etc) in channel {}".format(channel))
    set_status(db, channel, "DISABLED")


@hook.command(permissions=["botcontrol"])
def resetregex(inp, db=None, message=None, notice=None, chan=None, nick=None):
    db_init(db)
    inp = inp.strip().lower()
    if not inp:
        channel = chan
    elif inp.startswith("#"):
        channel = inp
    else:
        channel = u"#{}".format(inp)

    message(u"Resetting regex matching setting (youtube, etc) (issued by {})".format(nick), target=channel)
    notice(u"Resetting regex matching setting (youtube, etc) in channel {}".format(channel))
    delete_status(db, channel)


@hook.command(permissions=["botcontrol"])
def regexstatus(inp, db=None, chan=None):
    db_init(db)
    inp = inp.strip().lower()
    if not inp:
        channel = chan
    elif inp.startswith("#"):
        channel = inp
    else:
        channel = u"#{}".format(inp)

    return u"Regex status for {}: {}".format(channel, get_status(db, channel))


@hook.command(permissions=["botcontrol"])
def listregex(inp, db=None):
    db_init(db)
    return list_status(db)

########NEW FILE########
__FILENAME__ = rottentomatoes
from util import http, hook

api_root = 'http://api.rottentomatoes.com/api/public/v1.0/'
movie_search_url = api_root + 'movies.json'
movie_reviews_url = api_root + 'movies/%s/reviews.json'


@hook.command('rt')
def rottentomatoes(inp, bot=None):
    """rt <title> -- gets ratings for <title> from Rotten Tomatoes"""

    api_key = bot.config.get("api_keys", {}).get("rottentomatoes", None)
    if not api_key:
        return "error: no api key set"

    title = inp.strip()

    results = http.get_json(movie_search_url, q=title, apikey=api_key)
    if results['total'] == 0:
        return 'No results.'

    movie = results['movies'][0]
    title = movie['title']
    movie_id = movie['id']
    critics_score = movie['ratings']['critics_score']
    audience_score = movie['ratings']['audience_score']
    url = movie['links']['alternate']

    if critics_score == -1:
        return

    reviews = http.get_json(movie_reviews_url % movie_id, apikey=api_key, review_type='all')
    review_count = reviews['total']

    fresh = critics_score * review_count / 100
    rotten = review_count - fresh

    return u"{} - Critics Rating: \x02{}%\x02 ({} liked, {} disliked) " \
           "Audience Rating: \x02{}%\x02 - {}".format(title, critics_score, fresh, rotten, audience_score, url)

########NEW FILE########
__FILENAME__ = rss
from util import hook, http, web, text


@hook.command("feed")
@hook.command
def rss(inp, message=None):
    """rss <feed> -- Gets the first three items from the RSS feed <feed>."""
    limit = 3

    # preset news feeds
    strip = inp.lower().strip()
    if strip == "bukkit":
        feed = "http://dl.bukkit.org/downloads/craftbukkit/feeds/latest-rb.rss"
        limit = 1
    elif strip == "xkcd":
        feed = "http://xkcd.com/rss.xml"
    elif strip == "ars":
        feed = "http://feeds.arstechnica.com/arstechnica/index"
    else:
        feed = inp

    query = "SELECT title, link FROM rss WHERE url=@feed LIMIT @limit"
    result = web.query(query, {"feed": feed, "limit": limit})

    if not result.rows:
        return "Could not find/read RSS feed."

    for row in result.rows:
        title = text.truncate_str(row["title"], 100)
        try:
            link = web.isgd(row["link"])
        except (web.ShortenError, http.HTTPError, http.URLError):
            link = row["link"]
        message(u"{} - {}".format(title, link))


@hook.command(autohelp=False)
def rb(inp, message=None):
    """rb -- Shows the latest Craftbukkit recommended build"""
    rss("bukkit", message)

########NEW FILE########
__FILENAME__ = shorten
from util import hook, http, web


@hook.command
def shorten(inp):
    """shorten <url> - Makes an is.gd shortlink to the url provided."""

    try:
        return web.isgd(inp)
    except (web.ShortenError, http.HTTPError) as error:
        return error

########NEW FILE########
__FILENAME__ = slap
import json

from util import hook, textgen


def get_generator(_json, variables):
    data = json.loads(_json)
    return textgen.TextGenerator(data["templates"],
                                 data["parts"], variables=variables)


@hook.command
def slap(inp, action=None, nick=None, conn=None, notice=None):
    """slap <user> -- Makes the bot slap <user>."""
    target = inp.strip()

    if " " in target:
        notice("Invalid username!")
        return

    # if the user is trying to make the bot slap itself, slap them
    if target.lower() == conn.nick.lower() or target.lower() == "itself":
        target = nick

    variables = {
        "user": target
    }

    with open("plugins/data/slaps.json") as f:
        generator = get_generator(f.read(), variables)

    # act out the message
    action(generator.generate_string())

########NEW FILE########
__FILENAME__ = slogan
import random

from util import hook, text


with open("plugins/data/slogans.txt") as f:
    slogans = [line.strip() for line in f.readlines()
               if not line.startswith("//")]


@hook.command
def slogan(inp):
    """slogan <word> -- Makes a slogan for <word>."""
    out = random.choice(slogans)
    if inp.lower() and out.startswith("<text>"):
        inp = text.capitalize_first(inp)

    return out.replace('<text>', inp)

########NEW FILE########
__FILENAME__ = snopes
import re

from util import hook, http


search_url = "http://search.atomz.com/search/?sp_a=00062d45-sp00000000"


@hook.command
def snopes(inp):
    """snopes <topic> -- Searches snopes for an urban legend about <topic>."""

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

    return "{} {} {}".format(claim, status, result_urls[0])

########NEW FILE########
__FILENAME__ = soundcloud
from urllib import urlencode
import re

from util import hook, http, web, text


sc_re = (r'(.*:)//(www.)?(soundcloud.com)(.*)', re.I)
api_url = "http://api.soundcloud.com"
sndsc_re = (r'(.*:)//(www.)?(snd.sc)(.*)', re.I)


def soundcloud(url, api_key):
    data = http.get_json(api_url + '/resolve.json?' + urlencode({'url': url, 'client_id': api_key}))

    if data['description']:
        desc = u": {} ".format(text.truncate_str(data['description'], 50))
    else:
        desc = ""
    if data['genre']:
        genre = u"- Genre: \x02{}\x02 ".format(data['genre'])
    else:
        genre = ""

    url = web.try_isgd(data['permalink_url'])

    return u"SoundCloud track: \x02{}\x02 by \x02{}\x02 {}{}- {} plays, {} downloads, {} comments - {}".format(
        data['title'], data['user']['username'], desc, genre, data['playback_count'], data['download_count'],
        data['comment_count'], url)


@hook.regex(*sc_re)
def soundcloud_url(match, bot=None):
    api_key = bot.config.get("api_keys", {}).get("soundcloud")
    if not api_key:
        print "Error: no api key set"
        return None
    url = match.group(1).split(' ')[-1] + "//" + (match.group(2) if match.group(2) else "") + match.group(3) + \
          match.group(4).split(' ')[0]
    return soundcloud(url, api_key)


@hook.regex(*sndsc_re)
def sndsc_url(match, bot=None):
    api_key = bot.config.get("api_keys", {}).get("soundcloud")
    if not api_key:
        print "Error: no api key set"
        return None
    url = match.group(1).split(' ')[-1] + "//" + (match.group(2) if match.group(2) else "") + match.group(3) + \
          match.group(4).split(' ')[0]
    return soundcloud(http.open(url).url, api_key)

########NEW FILE########
__FILENAME__ = spellcheck
from enchant.checker import SpellChecker
import enchant

from util import hook


locale = "en_US"


@hook.command
def spell(inp):
    """spell <word/sentence> -- Check spelling of a word or sentence."""

    if not enchant.dict_exists(locale):
        return "Could not find dictionary: {}".format(locale)

    if len(inp.split(" ")) > 1:
        # input is a sentence
        checker = SpellChecker(locale)
        checker.set_text(inp)

        offset = 0
        for err in checker:
            # find the location of the incorrect word
            start = err.wordpos + offset
            finish = start + len(err.word)
            # get some suggestions for it
            suggestions = err.suggest()
            s_string = '/'.join(suggestions[:3])
            s_string = "\x02{}\x02".format(s_string)
            # calculate the offset for the next word
            offset = (offset + len(s_string)) - len(err.word)
            # replace the word with the suggestions
            inp = inp[:start] + s_string + inp[finish:]
        return inp
    else:
        # input is a word
        dictionary = enchant.Dict(locale)
        is_correct = dictionary.check(inp)
        suggestions = dictionary.suggest(inp)
        s_string = ', '.join(suggestions[:10])
        if is_correct:
            return '"{}" appears to be \x02valid\x02! ' \
                   '(suggestions: {})'.format(inp, s_string)
        else:
            return '"{}" appears to be \x02invalid\x02! ' \
                   '(suggestions: {})'.format(inp, s_string)

########NEW FILE########
__FILENAME__ = spotify
import re
from urllib import urlencode

from util import hook, http, web

gateway = 'http://open.spotify.com/{}/{}'  # http spotify gw address
spuri = 'spotify:{}:{}'

spotify_re = (r'(spotify:(track|album|artist|user):([a-zA-Z0-9]+))', re.I)
http_re = (r'(open\.spotify\.com\/(track|album|artist|user)\/'
           '([a-zA-Z0-9]+))', re.I)


def sptfy(inp, sptfy=False):
    if sptfy:
        shortenurl = "http://sptfy.com/index.php"
        data = urlencode({'longUrl': inp, 'shortUrlDomain': 1, 'submitted': 1, "shortUrlFolder": 6, "customUrl": "",
                          "shortUrlPassword": "", "shortUrlExpiryDate": "", "shortUrlUses": 0, "shortUrlType": 0})
        try:
            soup = http.get_soup(shortenurl, post_data=data, cookies=True)
        except:
            return inp
        try:
            link = soup.find('div', {'class': 'resultLink'}).text.strip()
            return link
        except:
            message = "Unable to shorten URL: %s" % \
                      soup.find('div', {'class': 'messagebox_text'}).find('p').text.split("<br/>")[0]
            return message
    else:
        return web.try_isgd(inp)


@hook.command('sptrack')
@hook.command
def spotify(inp):
    """spotify <song> -- Search Spotify for <song>"""
    try:
        data = http.get_json("http://ws.spotify.com/search/1/track.json", q=inp.strip())
    except Exception as e:
        return "Could not get track information: {}".format(e)

    try:
        type, id = data["tracks"][0]["href"].split(":")[1:]
    except IndexError:
        return "Could not find track."
    url = sptfy(gateway.format(type, id))
    return u"\x02{}\x02 by \x02{}\x02 - {}".format(data["tracks"][0]["name"],
                                                           data["tracks"][0]["artists"][0]["name"], url)


@hook.command
def spalbum(inp):
    """spalbum <album> -- Search Spotify for <album>"""
    try:
        data = http.get_json("http://ws.spotify.com/search/1/album.json", q=inp.strip())
    except Exception as e:
        return "Could not get album information: {}".format(e)

    try:
        type, id = data["albums"][0]["href"].split(":")[1:]
    except IndexError:
        return "Could not find album."
    url = sptfy(gateway.format(type, id))
    return u"\x02{}\x02 by \x02{}\x02 - {}".format(data["albums"][0]["name"],
                                                           data["albums"][0]["artists"][0]["name"], url)


@hook.command
def spartist(inp):
    """spartist <artist> -- Search Spotify for <artist>"""
    try:
        data = http.get_json("http://ws.spotify.com/search/1/artist.json", q=inp.strip())
    except Exception as e:
        return "Could not get artist information: {}".format(e)

    try:
        type, id = data["artists"][0]["href"].split(":")[1:]
    except IndexError:
        return "Could not find artist."
    url = sptfy(gateway.format(type, id))
    return u"\x02{}\x02 - {}".format(data["artists"][0]["name"], url)


@hook.regex(*http_re)
@hook.regex(*spotify_re)
def spotify_url(match):
    type = match.group(2)
    spotify_id = match.group(3)
    url = spuri.format(type, spotify_id)
    # no error catching here, if the API is down fail silently
    data = http.get_json("http://ws.spotify.com/lookup/1/.json", uri=url)
    if type == "track":
        name = data["track"]["name"]
        artist = data["track"]["artists"][0]["name"]
        album = data["track"]["album"]["name"]
        return u"Spotify Track: \x02{}\x02 by \x02{}\x02 from the album \x02{}\x02 - {}".format(name, artist,
                                                                                                        album, sptfy(
                gateway.format(type, spotify_id)))
    elif type == "artist":
        return u"Spotify Artist: \x02{}\x02 - {}".format(data["artist"]["name"],
                                                                 sptfy(gateway.format(type, spotify_id)))
    elif type == "album":
        return u"Spotify Album: \x02{}\x02 - \x02{}\x02 - {}".format(data["album"]["artist"],
                                                                             data["album"]["name"],
                                                                             sptfy(gateway.format(type, spotify_id)))

########NEW FILE########
__FILENAME__ = steam
import re

from bs4 import BeautifulSoup, NavigableString, Tag

from util import hook, http, web
from util.text import truncate_str


steam_re = (r'(.*:)//(store.steampowered.com)(:[0-9]+)?(.*)', re.I)


def get_steam_info(url):
    page = http.get(url)
    soup = BeautifulSoup(page, 'lxml', from_encoding="utf-8")

    data = {}

    data["name"] = soup.find('div', {'class': 'apphub_AppName'}).text
    data["desc"] = truncate_str(soup.find('meta', {'name': 'description'})['content'].strip(), 80)

    # get the element details_block
    details = soup.find('div', {'class': 'details_block'})

    # loop over every <b></b> tag in details_block
    for b in details.findAll('b'):
        # get the contents of the <b></b> tag, which is our title
        title = b.text.lower().replace(":", "")
        if title == "languages":
            # we have all we need!
            break

        # find the next element directly after the <b></b> tag
        next_element = b.nextSibling
        if next_element:
            # if the element is some text
            if isinstance(next_element, NavigableString):
                text = next_element.string.strip()
                if text:
                    # we found valid text, save it and continue the loop
                    data[title] = text
                    continue
                else:
                    # the text is blank - sometimes this means there are
                    # useless spaces or tabs between the <b> and <a> tags.
                    # so we find the next <a> tag and carry on to the next
                    # bit of code below
                    next_element = next_element.find_next('a', href=True)

            # if the element is an <a></a> tag
            if isinstance(next_element, Tag) and next_element.name == 'a':
                text = next_element.string.strip()
                if text:
                    # we found valid text (in the <a></a> tag),
                    # save it and continue the loop
                    data[title] = text
                    continue

    data["price"] = soup.find('div', {'class': 'game_purchase_price price'}).text.strip()

    return u"\x02{name}\x02: {desc}, \x02Genre\x02: {genre}, \x02Release Date\x02: {release date}," \
           u" \x02Price\x02: {price}".format(**data)


@hook.regex(*steam_re)
def steam_url(match):
    return get_steam_info("http://store.steampowered.com" + match.group(4))


@hook.command
def steam(inp):
    """steam [search] - Search for specified game/trailer/DLC"""
    page = http.get("http://store.steampowered.com/search/?term=" + inp)
    soup = BeautifulSoup(page, 'lxml', from_encoding="utf-8")
    result = soup.find('a', {'class': 'search_result_row'})
    return get_steam_info(result['href']) + " - " + web.isgd(result['href'])

########NEW FILE########
__FILENAME__ = steam_calc
import csv
import StringIO

from util import hook, http, text


gauge_url = "http://www.mysteamgauge.com/search?username={}"

api_url = "http://mysteamgauge.com/user/{}.csv"
steam_api_url = "http://steamcommunity.com/id/{}/?xml=1"


def refresh_data(name):
    http.get(gauge_url.format(name), timeout=25, get_method='HEAD')


def get_data(name):
    return http.get(api_url.format(name))


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def unicode_dictreader(utf8_data, **kwargs):
    csv_reader = csv.DictReader(utf8_data, **kwargs)
    for row in csv_reader:
        yield dict([(key.lower(), unicode(value, 'utf-8')) for key, value in row.iteritems()])


@hook.command('sc')
@hook.command
def steamcalc(inp, reply=None):
    """steamcalc <username> [currency] - Gets value of steam account and
       total hours played. Uses steamcommunity.com/id/<nickname>. """

    # check if the user asked us to force reload
    force_reload = inp.endswith(" forcereload")
    if force_reload:
        name = inp[:-12].strip().lower()
    else:
        name = inp.strip()

    if force_reload:
        try:
            reply("Collecting data, this may take a while.")
            refresh_data(name)
            request = get_data(name)
            do_refresh = False
        except (http.HTTPError, http.URLError):
            return "Could not get data for this user."
    else:
        try:
            request = get_data(name)
            do_refresh = True
        except (http.HTTPError, http.URLError):
            try:
                reply("Collecting data, this may take a while.")
                refresh_data(name)
                request = get_data(name)
                do_refresh = False
            except (http.HTTPError, http.URLError):
                return "Could not get data for this user."

    csv_data = StringIO.StringIO(request)  # we use StringIO because CSV can't read a string
    reader = unicode_dictreader(csv_data)

    # put the games in a list
    games = []
    for row in reader:
        games.append(row)

    data = {}

    # basic information
    steam_profile = http.get_xml(steam_api_url.format(name))
    try:
        data["name"] = steam_profile.find('steamID').text
        online_state = steam_profile.find('stateMessage').text
    except AttributeError:
        return "Could not get data for this user."

    online_state = online_state.replace("<br/>", ": ")  # will make this pretty later
    data["state"] = text.strip_html(online_state)

    # work out the average metascore for all games
    ms = [float(game["metascore"]) for game in games if is_number(game["metascore"])]
    metascore = float(sum(ms)) / len(ms) if len(ms) > 0 else float('nan')
    data["average_metascore"] = "{0:.1f}".format(metascore)

    # work out the totals
    data["games"] = len(games)

    total_value = sum([float(game["value"]) for game in games if is_number(game["value"])])
    data["value"] = str(int(round(total_value)))

    # work out the total size
    total_size = 0.0

    for game in games:
        if not is_number(game["size"]):
            continue

        if game["unit"] == "GB":
            total_size += float(game["size"])
        else:
            total_size += float(game["size"]) / 1024

    data["size"] = "{0:.1f}".format(total_size)

    reply("{name} ({state}) has {games} games with a total value of ${value}"
          " and a total size of {size}GB! The average metascore for these"
          " games is {average_metascore}.".format(**data))

    if do_refresh:
        refresh_data(name)

########NEW FILE########
__FILENAME__ = stock
from util import hook, web


@hook.command
def stock(inp):
    """stock <symbol> -- gets stock information"""
    sym = inp.strip().lower()

    query = "SELECT * FROM yahoo.finance.quote WHERE symbol=@symbol LIMIT 1"
    quote = web.query(query, {"symbol": sym}).one()

    # if we don't get a company name back, the symbol doesn't match a company
    if quote['Change'] is None:
        return "Unknown ticker symbol: {}".format(sym)

    change = float(quote['Change'])
    price = float(quote['LastTradePriceOnly'])

    if change < 0:
        quote['color'] = "5"
    else:
        quote['color'] = "3"

    quote['PercentChange'] = 100 * change / (price - change)
    print quote

    return u"\x02{Name}\x02 (\x02{symbol}\x02) - {LastTradePriceOnly} " \
           "\x03{color}{Change} ({PercentChange:.2f}%)\x03 " \
           "Day Range: {DaysRange} " \
           "MCAP: {MarketCapitalization}".format(**quote)

########NEW FILE########
__FILENAME__ = suggest
from util import hook, http, text
from bs4 import BeautifulSoup


@hook.command
def suggest(inp):
    """suggest <phrase> -- Gets suggested phrases for a google search"""
    suggestions = http.get_json('http://suggestqueries.google.com/complete/search', client='firefox', q=inp)[1]

    if not suggestions:
        return 'no suggestions found'

    out = u", ".join(suggestions)

    # defuckify text (might not be needed now, but I'll keep it)
    soup = BeautifulSoup(out)
    out = soup.get_text()

    return text.truncate_str(out, 200)

########NEW FILE########
__FILENAME__ = system
import os
import re
import time
import platform
from datetime import timedelta

from util import hook


def convert_kilobytes(kilobytes):
    if kilobytes >= 1024:
        megabytes = kilobytes / 1024
        size = '%.2f MB' % megabytes
    else:
        size = '%.2f KB' % kilobytes
    return size


@hook.command(autohelp=False)
def system(inp):
    """system -- Retrieves information about the host system."""
    hostname = platform.node()
    os = platform.platform()
    python_imp = platform.python_implementation()
    python_ver = platform.python_version()
    architecture = '-'.join(platform.architecture())
    cpu = platform.machine()
    return "Hostname: \x02{}\x02, Operating System: \x02{}\x02, Python " \
           "Version: \x02{} {}\x02, Architecture: \x02{}\x02, CPU: \x02{}" \
           "\x02".format(hostname, os, python_imp, python_ver, architecture, cpu)


@hook.command(autohelp=False)
def memory(inp):
    """memory -- Displays the bot's current memory usage."""
    if os.name == "posix":
        # get process info
        status_file = open('/proc/self/status').read()
        s = dict(re.findall(r'^(\w+):\s*(.*)\s*$', status_file, re.M))
        # get the data we need and process it
        data = s['VmRSS'], s['VmSize'], s['VmPeak'], s['VmStk'], s['VmData']
        data = [float(i.replace(' kB', '')) for i in data]
        strings = [convert_kilobytes(i) for i in data]
        # prepare the output
        out = "Threads: \x02{}\x02, Real Memory: \x02{}\x02, Allocated Memory: \x02{}\x02, Peak " \
              "Allocated Memory: \x02{}\x02, Stack Size: \x02{}\x02, Heap " \
              "Size: \x02{}\x02".format(s['Threads'], strings[0], strings[1], strings[2],
              strings[3], strings[4])
        # return output
        return out

    elif os.name == "nt":
        cmd = 'tasklist /FI "PID eq %s" /FO CSV /NH' % os.getpid()
        out = os.popen(cmd).read()
        memory = 0
        for amount in re.findall(r'([,0-9]+) K', out):
            memory += float(amount.replace(',', ''))
        memory = convert_kilobytes(memory)
        return "Memory Usage: \x02{}\x02".format(memory)

    else:
        return "Sorry, this command is not supported on your OS."


@hook.command(autohelp=False)
def uptime(inp, bot=None):
    """uptime -- Shows the bot's uptime."""
    uptime_raw = round(time.time() - bot.start_time)
    uptime = timedelta(seconds=uptime_raw)
    return "Uptime: \x02{}\x02".format(uptime)


@hook.command(autohelp=False)
def pid(inp):
    """pid -- Prints the bot's PID."""
    return "PID: \x02{}\x02".format(os.getpid())

########NEW FILE########
__FILENAME__ = tell
""" tell.py: written by sklnd in July 2009
       2010.01.25 - modified by Scaevolus"""

import time
import re

from util import hook, timesince

db_ready = []


def db_init(db, conn):
    """Check that our db has the tell table, create it if not."""
    global db_ready
    if not conn.name in db_ready:
        db.execute("create table if not exists tell"
                   "(user_to, user_from, message, chan, time,"
                   "primary key(user_to, message))")
        db.commit()
        db_ready.append(conn.name)


def get_tells(db, user_to):
    return db.execute("select user_from, message, time, chan from tell where"
                      " user_to=lower(?) order by time",
                      (user_to.lower(),)).fetchall()


@hook.singlethread
@hook.event('PRIVMSG')
def tellinput(inp, input=None, notice=None, db=None, nick=None, conn=None):
    if 'showtells' in input.msg.lower():
        return

    db_init(db, conn)

    tells = get_tells(db, nick)

    if tells:
        user_from, message, time, chan = tells[0]
        reltime = timesince.timesince(time)

        reply = "{} sent you a message {} ago from {}: {}".format(user_from, reltime, chan,
                                                                  message)
        if len(tells) > 1:
            reply += " (+{} more, {}showtells to view)".format(len(tells) - 1, conn.conf["command_prefix"])

        db.execute("delete from tell where user_to=lower(?) and message=?",
                   (nick, message))
        db.commit()
        notice(reply)


@hook.command(autohelp=False)
def showtells(inp, nick='', chan='', notice=None, db=None, conn=None):
    """showtells -- View all pending tell messages (sent in a notice)."""

    db_init(db, conn)

    tells = get_tells(db, nick)

    if not tells:
        notice("You have no pending tells.")
        return

    for tell in tells:
        user_from, message, time, chan = tell
        past = timesince.timesince(time)
        notice("{} sent you a message {} ago from {}: {}".format(user_from, past, chan, message))

    db.execute("delete from tell where user_to=lower(?)",
               (nick,))
    db.commit()


@hook.command
def tell(inp, nick='', chan='', db=None, input=None, notice=None, conn=None):
    """tell <nick> <message> -- Relay <message> to <nick> when <nick> is around."""
    query = inp.split(' ', 1)

    if len(query) != 2:
        notice(tell.__doc__)
        return

    user_to = query[0].lower()
    message = query[1].strip()
    user_from = nick

    if chan.lower() == user_from.lower():
        chan = 'a pm'

    if user_to == user_from.lower():
        notice("Have you looked in a mirror lately?")
        return

    if user_to.lower() == input.conn.nick.lower():
        # user is looking for us, being a smart-ass
        notice("Thanks for the message, {}!".format(user_from))
        return

    if not re.match("^[a-z0-9_|.\-\]\[]*$", user_to.lower()):
        notice("I can't send a message to that user!")
        return

    db_init(db, conn)

    if db.execute("select count() from tell where user_to=?",
                  (user_to,)).fetchone()[0] >= 10:
        notice("That person has too many messages queued.")
        return

    try:
        db.execute("insert into tell(user_to, user_from, message, chan,"
                   "time) values(?,?,?,?,?)", (user_to, user_from, message,
                                               chan, time.time()))
        db.commit()
    except db.IntegrityError:
        notice("Message has already been queued.")
        return

    notice("Your message has been saved, and {} will be notified once they are active.".format(user_to))

########NEW FILE########
__FILENAME__ = time_plugin
import time

from util import hook, http
from util.text import capitalize_first


api_url = 'http://api.wolframalpha.com/v2/query?format=plaintext'


@hook.command("time")
def time_command(inp, bot=None):
    """time <area> -- Gets the time in <area>"""

    query = "current time in {}".format(inp)

    api_key = bot.config.get("api_keys", {}).get("wolframalpha", None)
    if not api_key:
        return "error: no wolfram alpha api key set"

    request = http.get_xml(api_url, input=query, appid=api_key)
    current_time = " ".join(request.xpath("//pod[@title='Result']/subpod/plaintext/text()"))
    current_time = current_time.replace("  |  ", ", ")

    if current_time:
        # nice place name for UNIX time
        if inp.lower() == "unix":
            place = "Unix Epoch"
        else:
            place = capitalize_first(" ".join(request.xpath("//pod[@"
                                                            "title='Input interpretation']/subpod/plaintext/text()"))[
                                     16:])
        return "{} - \x02{}\x02".format(current_time, place)
    else:
        return "Could not get the time for '{}'.".format(inp)


@hook.command(autohelp=False)
def beats(inp):
    """beats -- Gets the current time in .beats (Swatch Internet Time). """

    if inp.lower() == "wut":
        return "Instead of hours and minutes, the mean solar day is divided " \
               "up into 1000 parts called \".beats\". Each .beat lasts 1 minute and" \
               " 26.4 seconds. Times are notated as a 3-digit number out of 1000 af" \
               "ter midnight. So, @248 would indicate a time 248 .beats after midni" \
               "ght representing 248/1000 of a day, just over 5 hours and 57 minute" \
               "s. There are no timezones."
    elif inp.lower() == "guide":
        return "1 day = 1000 .beats, 1 hour = 41.666 .beats, 1 min = 0.6944 .beats, 1 second = 0.01157 .beats"

    t = time.gmtime()
    h, m, s = t.tm_hour, t.tm_min, t.tm_sec

    utc = 3600 * h + 60 * m + s
    bmt = utc + 3600  # Biel Mean Time (BMT)

    beat = bmt / 86.4

    if beat > 1000:
        beat -= 1000

    return "Swatch Internet Time: @%06.2f" % beat

########NEW FILE########
__FILENAME__ = title
from bs4 import BeautifulSoup

from util import hook, http, urlnorm


@hook.command
def title(inp):
    """title <url> -- gets the title of a web page"""
    url = urlnorm.normalize(inp.encode('utf-8'), assume_scheme="http")

    try:
        page = http.open(url)
        real_url = page.geturl()
        soup = BeautifulSoup(page.read())
    except (http.HTTPError, http.URLError):
        return "Could not fetch page."

    page_title = soup.find('title').contents[0]

    if not page_title:
        return "Could not find title."

    return u"{} [{}]".format(page_title, real_url)

########NEW FILE########
__FILENAME__ = tvdb
import datetime

from util import hook, http


base_url = "http://thetvdb.com/api/"
api_key = "469B73127CA0C411"


def get_episodes_for_series(series_name, api_key):
    res = {"error": None, "ended": False, "episodes": None, "name": None}
    # http://thetvdb.com/wiki/index.php/API:GetSeries
    try:
        query = http.get_xml(base_url + 'GetSeries.php', seriesname=series_name)
    except http.URLError:
        res["error"] = "error contacting thetvdb.com"
        return res

    series_id = query.xpath('//seriesid/text()')

    if not series_id:
        res["error"] = "Unknown TV series. (using www.thetvdb.com)"
        return res

    series_id = series_id[0]

    try:
        series = http.get_xml(base_url + '%s/series/%s/all/en.xml' % (api_key, series_id))
    except http.URLError:
        res["error"] = "Error contacting thetvdb.com."
        return res

    series_name = series.xpath('//SeriesName/text()')[0]

    if series.xpath('//Status/text()')[0] == 'Ended':
        res["ended"] = True

    res["episodes"] = series.xpath('//Episode')
    res["name"] = series_name
    return res


def get_episode_info(episode, api_key):
    first_aired = episode.findtext("FirstAired")

    try:
        air_date = datetime.date(*map(int, first_aired.split('-')))
    except (ValueError, TypeError):
        return None

    episode_num = "S%02dE%02d" % (int(episode.findtext("SeasonNumber")),
                                  int(episode.findtext("EpisodeNumber")))

    episode_name = episode.findtext("EpisodeName")
    # in the event of an unannounced episode title, users either leave the
    # field out (None) or fill it with TBA
    if episode_name == "TBA":
        episode_name = None

    episode_desc = '{}'.format(episode_num)
    if episode_name:
        episode_desc += ' - {}'.format(episode_name)
    return first_aired, air_date, episode_desc


@hook.command
@hook.command('tv')
def tv_next(inp, bot=None):
    """tv <series> -- Get the next episode of <series>."""

    api_key = bot.config.get("api_keys", {}).get("tvdb", None)
    if api_key is None:
        return "error: no api key set"
    episodes = get_episodes_for_series(inp, api_key)

    if episodes["error"]:
        return episodes["error"]

    series_name = episodes["name"]
    ended = episodes["ended"]
    episodes = episodes["episodes"]

    if ended:
        return "{} has ended.".format(series_name)

    next_eps = []
    today = datetime.date.today()

    for episode in reversed(episodes):
        ep_info = get_episode_info(episode, api_key)

        if ep_info is None:
            continue

        (first_aired, air_date, episode_desc) = ep_info

        if air_date > today:
            next_eps = ['{} ({})'.format(first_aired, episode_desc)]
        elif air_date == today:
            next_eps = ['Today ({})'.format(episode_desc)] + next_eps
        else:
            # we're iterating in reverse order with newest episodes last
            # so, as soon as we're past today, break out of loop
            break

    if not next_eps:
        return "There are no new episodes scheduled for {}.".format(series_name)

    if len(next_eps) == 1:
        return "The next episode of {} airs {}".format(series_name, next_eps[0])
    else:
        next_eps = ', '.join(next_eps)
        return "The next episodes of {}: {}".format(series_name, next_eps)


@hook.command
@hook.command('tv_prev')
def tv_last(inp, bot=None):
    """tv_last <series> -- Gets the most recently aired episode of <series>."""

    api_key = bot.config.get("api_keys", {}).get("tvdb", None)
    if api_key is None:
        return "error: no api key set"
    episodes = get_episodes_for_series(inp, api_key)

    if episodes["error"]:
        return episodes["error"]

    series_name = episodes["name"]
    ended = episodes["ended"]
    episodes = episodes["episodes"]

    prev_ep = None
    today = datetime.date.today()

    for episode in reversed(episodes):
        ep_info = get_episode_info(episode, api_key)

        if ep_info is None:
            continue

        (first_aired, air_date, episode_desc) = ep_info

        if air_date < today:
            #iterating in reverse order, so the first episode encountered
            #before today was the most recently aired
            prev_ep = '{} ({})'.format(first_aired, episode_desc)
            break

    if not prev_ep:
        return "There are no previously aired episodes for {}.".format(series_name)
    if ended:
        return '{} ended. The last episode aired {}.'.format(series_name, prev_ep)
    return "The last episode of {} aired {}.".format(series_name, prev_ep)

########NEW FILE########
__FILENAME__ = twitch
import re
from HTMLParser import HTMLParser

from util import hook, http


twitch_re = (r'(.*:)//(twitch.tv|www.twitch.tv)(:[0-9]+)?(.*)', re.I)
multitwitch_re = (r'(.*:)//(www.multitwitch.tv|multitwitch.tv)/(.*)', re.I)


def test(s):
    valid = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_/')
    return set(s) <= valid


def truncate(msg):
    nmsg = msg.split(" ")
    out = None
    x = 0
    for i in nmsg:
        if x <= 7:
            if out:
                out = out + " " + nmsg[x]
            else:
                out = nmsg[x]
        x += 1
    if x <= 7:
        return out
    else:
        return out + "..."


@hook.regex(*multitwitch_re)
def multitwitch_url(match):
    usernames = match.group(3).split("/")
    out = ""
    for i in usernames:
        if not test(i):
            print "Not a valid username"
            return None
        if out == "":
            out = twitch_lookup(i)
        else:
            out = out + " \x02|\x02 " + twitch_lookup(i)
    return out


@hook.regex(*twitch_re)
def twitch_url(match):
    bit = match.group(4).split("#")[0]
    location = "/".join(bit.split("/")[1:])
    if not test(location):
        print "Not a valid username"
        return None
    return twitch_lookup(location)


@hook.command('twitchviewers')
@hook.command
def twviewers(inp):
    inp = inp.split("/")[-1]
    if test(inp):
        location = inp
    else:
        return "Not a valid channel name."
    return twitch_lookup(location).split("(")[-1].split(")")[0].replace("Online now! ", "")


def twitch_lookup(location):
    locsplit = location.split("/")
    if len(locsplit) > 1 and len(locsplit) == 3:
        channel = locsplit[0]
        type = locsplit[1]  # should be b or c
        id = locsplit[2]
    else:
        channel = locsplit[0]
        type = None
        id = None
    h = HTMLParser()
    fmt = "{}: {} playing {} ({})"  # Title: nickname playing Game (x views)
    if type and id:
        if type == "b":  # I haven't found an API to retrieve broadcast info
            soup = http.get_soup("http://twitch.tv/" + location)
            title = soup.find('span', {'class': 'real_title js-title'}).text
            playing = soup.find('a', {'class': 'game js-game'}).text
            views = soup.find('span', {'id': 'views-count'}).text + " view"
            views = views + "s" if not views[0:2] == "1 " else views
            return h.unescape(fmt.format(title, channel, playing, views))
        elif type == "c":
            data = http.get_json("https://api.twitch.tv/kraken/videos/" + type + id)
            title = data['title']
            playing = data['game']
            views = str(data['views']) + " view"
            views = views + "s" if not views[0:2] == "1 " else views
            return h.unescape(fmt.format(title, channel, playing, views))
    else:
        data = http.get_json("http://api.justin.tv/api/stream/list.json?channel=" + channel)
        if data and len(data) >= 1:
            data = data[0]
            title = data['title']
            playing = data['meta_game']
            viewers = "\x033\x02Online now!\x02\x0f " + str(data["channel_count"]) + " viewer"
            print viewers
            viewers = viewers + "s" if not " 1 view" in viewers else viewers
            print viewers
            return h.unescape(fmt.format(title, channel, playing, viewers))
        else:
            try:
                data = http.get_json("https://api.twitch.tv/kraken/channels/" + channel)
            except:
                return
            title = data['status']
            playing = data['game']
            viewers = "\x034\x02Offline\x02\x0f"
            return h.unescape(fmt.format(title, channel, playing, viewers))

########NEW FILE########
__FILENAME__ = twitter
import re
import random
from datetime import datetime

import tweepy

from util import hook, timesince


TWITTER_RE = (r"(?:(?:www.twitter.com|twitter.com)/(?:[-_a-zA-Z0-9]+)/status/)([0-9]+)", re.I)


def get_api(bot):
    consumer_key = bot.config.get("api_keys", {}).get("twitter_consumer_key")
    consumer_secret = bot.config.get("api_keys", {}).get("twitter_consumer_secret")

    oauth_token = bot.config.get("api_keys", {}).get("twitter_access_token")
    oauth_secret = bot.config.get("api_keys", {}).get("twitter_access_secret")

    if not consumer_key:
        return False

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(oauth_token, oauth_secret)

    return tweepy.API(auth)


@hook.regex(*TWITTER_RE)
def twitter_url(match, bot=None):
    # Find the tweet ID from the URL
    tweet_id = match.group(1)

    # Get the tweet using the tweepy API
    api = get_api(bot)
    if not api:
        return
    try:
        tweet = api.get_status(tweet_id)
        user = tweet.user
    except tweepy.error.TweepError:
        return

    # Format the return the text of the tweet
    text = " ".join(tweet.text.split())

    if user.verified:
        prefix = u"\u2713"
    else:
        prefix = ""

    time = timesince.timesince(tweet.created_at, datetime.utcnow())

    return u"{}@\x02{}\x02 ({}): {} ({} ago)".format(prefix, user.screen_name, user.name, text, time)


@hook.command("tw")
@hook.command("twatter")
@hook.command
def twitter(inp, bot=None):
    """twitter <user> [n] -- Gets last/[n]th tweet from <user>"""

    api = get_api(bot)
    if not api:
        return "Error: No Twitter API details."

    if re.match(r'^\d+$', inp):
        # user is getting a tweet by id

        try:
            # get tweet by id
            tweet = api.get_status(inp)
        except tweepy.error.TweepError as e:
            if e[0][0]['code'] == 34:
                return "Could not find tweet."
            else:
                return u"Error {}: {}".format(e[0][0]['code'], e[0][0]['message'])

        user = tweet.user

    elif re.match(r'^\w{1,15}$', inp) or re.match(r'^\w{1,15}\s+\d+$', inp):
        # user is getting a tweet by name

        if inp.find(' ') == -1:
            username = inp
            tweet_number = 0
        else:
            username, tweet_number = inp.split()
            tweet_number = int(tweet_number) - 1

        if tweet_number > 300:
            return "This command can only find the last \x02300\x02 tweets."

        try:
            # try to get user by username
            user = api.get_user(username)
        except tweepy.error.TweepError as e:
            if e[0][0]['code'] == 34:
                return "Could not find user."
            else:
                return u"Error {}: {}".format(e[0][0]['code'], e[0][0]['message'])

        # get the users tweets
        user_timeline = api.user_timeline(id=user.id, count=tweet_number + 1)

        # if the timeline is empty, return an error
        if not user_timeline:
            return u"The user \x02{}\x02 has no tweets.".format(user.screen_name)

        # grab the newest tweet from the users timeline
        try:
            tweet = user_timeline[tweet_number]
        except IndexError:
            tweet_count = len(user_timeline)
            return u"The user \x02{}\x02 only has \x02{}\x02 tweets.".format(user.screen_name, tweet_count)

    elif re.match(r'^#\w+$', inp):
        # user is searching by hashtag
        search = api.search(inp)

        if not search:
            return "No tweets found."

        tweet = random.choice(search)
        user = tweet.user
    else:
        # ???
        return "Invalid Input"

    # Format the return the text of the tweet
    text = " ".join(tweet.text.split())

    if user.verified:
        prefix = u"\u2713"
    else:
        prefix = ""

    time = timesince.timesince(tweet.created_at, datetime.utcnow())

    return u"{}@\x02{}\x02 ({}): {} ({} ago)".format(prefix, user.screen_name, user.name, text, time)


@hook.command("twinfo")
@hook.command
def twuser(inp, bot=None):
    """twuser <user> -- Get info on the Twitter user <user>"""

    api = get_api(bot)
    if not api:
        return "Error: No Twitter API details."

    try:
        # try to get user by username
        user = api.get_user(inp)
    except tweepy.error.TweepError as e:
        if e[0][0]['code'] == 34:
            return "Could not find user."
        else:
            return "Unknown error"

    if user.verified:
        prefix = u"\u2713"
    else:
        prefix = ""

    if user.location:
        loc_str = u" is located in \x02{}\x02 and".format(user.location)
    else:
        loc_str = ""

    if user.description:
        desc_str = u" The users description is \"{}\"".format(user.description)
    else:
        desc_str = ""

    return u"{}@\x02{}\x02 ({}){} has \x02{:,}\x02 tweets and \x02{:,}\x02 followers.{}" \
           "".format(prefix, user.screen_name, user.name, loc_str, user.statuses_count, user.followers_count,
                     desc_str)

########NEW FILE########
__FILENAME__ = update
from git import Repo


from util import hook, web

@hook.command
def update(inp, bot=None):
    repo = Repo()
    git = repo.git
    try:
        pull = git.pull()
    except Exception as e:
        return e
    if "\n" in pull:
        return web.haste(pull)
    else:
        return pull


@hook.command
def version(inp, bot=None):
    repo = Repo()

    # get origin and fetch it
    origin = repo.remotes.origin
    info = origin.fetch()

    # get objects
    head = repo.head
    origin_head = info[0]
    current_commit = head.commit
    remote_commit = origin_head.commit

    if current_commit == remote_commit:
        in_sync = True
    else:
        in_sync = False

    # output
    return "Local \x02{}\x02 is at commit \x02{}\x02, remote \x02{}\x02 is at commit \x02{}\x02." \
           " You {} running the latest version.".format(head, current_commit.name_rev[:7],
                                                        origin_head, remote_commit.name_rev[:7],
                                                        "are" if in_sync else "are not")

########NEW FILE########
__FILENAME__ = urban
import re
import random

from util import hook, http, text


base_url = 'http://api.urbandictionary.com/v0'
define_url = base_url + "/define"
random_url = base_url + "/random"

@hook.command('u', autohelp=False)
@hook.command(autohelp=False)
def urban(inp):
    """urban <phrase> [id] -- Looks up <phrase> on urbandictionary.com."""

    if inp:
        # clean and split the input
        inp = inp.lower().strip()
        parts = inp.split()

        # if the last word is a number, set the ID to that number
        if parts[-1].isdigit():
            id_num = int(parts[-1])
            # remove the ID from the input string
            del parts[-1]
            inp = " ".join(parts)
        else:
            id_num = 1

        # fetch the definitions
        page = http.get_json(define_url, term=inp, referer="http://m.urbandictionary.com")

        if page['result_type'] == 'no_results':
            return 'Not found.'
    else:
        # get a random definition!
        page = http.get_json(random_url, referer="http://m.urbandictionary.com")
        id_num = None

    definitions = page['list']

    if id_num:
        # try getting the requested definition
        try:
            definition = definitions[id_num - 1]

            def_text = " ".join(definition['definition'].split())  # remove excess spaces
            def_text = text.truncate_str(def_text, 200)
        except IndexError:
            return 'Not found.'

        url = definition['permalink']
        output = u"[%i/%i] %s :: %s" % \
                 (id_num, len(definitions), def_text, url)

    else:
        definition = random.choice(definitions)

        def_text = " ".join(definition['definition'].split())  # remove excess spaces
        def_text = text.truncate_str(def_text, 200)

        name = definition['word']
        url = definition['permalink']
        output = u"\x02{}\x02: {} :: {}".format(name, def_text, url)

    return output

########NEW FILE########
__FILENAME__ = utility
import hashlib
import collections
import re

from util import hook, text


# variables

colors = collections.OrderedDict([
    ('red', '\x0304'),
    ('orange', '\x0307'),
    ('yellow', '\x0308'),
    ('green', '\x0309'),
    ('cyan', '\x0303'),
    ('ltblue', '\x0310'),
    ('rylblue', '\x0312'),
    ('blue', '\x0302'),
    ('magenta', '\x0306'),
    ('pink', '\x0313'),
    ('maroon', '\x0305')
])

# helper functions

strip_re = re.compile("(\x03|\x02|\x1f)(?:,?\d{1,2}(?:,\d{1,2})?)?", re.UNICODE)


def strip(string):
    return strip_re.sub('', string)


# basic text tools


## TODO: make this capitalize sentences correctly
@hook.command("capitalise")
@hook.command
def capitalize(inp):
    """capitalize <string> -- Capitalizes <string>."""
    return inp.capitalize()


@hook.command
def upper(inp):
    """upper <string> -- Convert string to uppercase."""
    return inp.upper()


@hook.command
def lower(inp):
    """lower <string> -- Convert string to lowercase."""
    return inp.lower()


@hook.command
def titlecase(inp):
    """title <string> -- Convert string to title case."""
    return inp.title()


@hook.command
def swapcase(inp):
    """swapcase <string> -- Swaps the capitalization of <string>."""
    return inp.swapcase()


# encoding


@hook.command
def rot13(inp):
    """rot13 <string> -- Encode <string> with rot13."""
    return inp.encode('rot13')


@hook.command
def base64(inp):
    """base64 <string> -- Encode <string> with base64."""
    return inp.encode('base64')


@hook.command
def unbase64(inp):
    """unbase64 <string> -- Decode <string> with base64."""
    return inp.decode('base64')


@hook.command
def checkbase64(inp):
    try:
        decoded = inp.decode('base64')
        recoded = decoded.encode('base64').strip()
        is_base64 = recoded == inp
    except:
        return '"{}" is not base64 encoded'.format(inp)

    if is_base64:
        return '"{}" is base64 encoded'.format(recoded)
    else:
        return '"{}" is not base64 encoded'.format(inp)


@hook.command
def unescape(inp):
    """unescape <string> -- Unescapes <string>."""
    try:
        return inp.decode('unicode-escape')
    except Exception as e:
        return "Error: {}".format(e)


@hook.command
def escape(inp):
    """escape <string> -- Escapes <string>."""
    try:
        return inp.encode('unicode-escape')
    except Exception as e:
        return "Error: {}".format(e)


# length


@hook.command
def length(inp):
    """length <string> -- gets the length of <string>"""
    return "The length of that string is {} characters.".format(len(inp))


# reverse


@hook.command
def reverse(inp):
    """reverse <string> -- reverses <string>."""
    return inp[::-1]


# hashing


@hook.command("hash")
def hash_command(inp):
    """hash <string> -- Returns hashes of <string>."""
    return ', '.join(x + ": " + getattr(hashlib, x)(inp).hexdigest()
                     for x in ['md5', 'sha1', 'sha256'])


# novelty


@hook.command
def munge(inp):
    """munge <text> -- Munges up <text>."""
    return text.munge(inp)


# colors - based on code by Reece Selwood - <https://github.com/hitzler/homero>


@hook.command
def rainbow(inp):
    inp = unicode(inp)
    inp = strip(inp)
    col = colors.items()
    out = ""
    l = len(colors)
    for i, t in enumerate(inp):
        if t == " ":
            out += t
        else:
            out += col[i % l][1] + t
    return out


@hook.command
def wrainbow(inp):
    inp = unicode(inp)
    col = colors.items()
    inp = strip(inp).split(' ')
    out = []
    l = len(colors)
    for i, t in enumerate(inp):
        out.append(col[i % l][1] + t)
    return ' '.join(out)


@hook.command
def usa(inp):
    inp = strip(inp)
    c = [colors['red'], '\x0300', colors['blue']]
    l = len(c)
    out = ''
    for i, t in enumerate(inp):
        out += c[i % l] + t
    return out

########NEW FILE########
__FILENAME__ = validate
"""
Runs a given url through the w3c validator

by Vladi
"""

from util import hook, http


@hook.command('w3c')
@hook.command
def validate(inp):
    """validate <url> -- Runs url through the w3c markup validator."""

    if not inp.startswith('http://'):
        inp = 'http://' + inp

    url = 'http://validator.w3.org/check?uri=' + http.quote_plus(inp)
    info = dict(http.open(url).info())

    status = info['x-w3c-validator-status'].lower()
    if status in ("valid", "invalid"):
        error_count = info['x-w3c-validator-errors']
        warning_count = info['x-w3c-validator-warnings']
        return "{} was found to be {} with {} errors and {} warnings." \
               " see: {}".format(inp, status, error_count, warning_count, url)

########NEW FILE########
__FILENAME__ = valvesounds
import json
import urllib2

from util import hook, http, web


def get_sound_info(game, search):
    search = search.replace(" ", "+")
    try:
        data = http.get_json("http://p2sounds.blha303.com.au/search/%s/%s?format=json" % (game, search))
    except urllib2.HTTPError as e:
        return "Error: " + json.loads(e.read())["error"]
    items = []
    for item in data["items"]:
        if "music" in game:
            textsplit = item["text"].split('"')
            text = ""
            for i in xrange(len(textsplit)):
                if i % 2 != 0 and i < 6:
                    if text:
                        text += " / " + textsplit[i]
                    else:
                        text = textsplit[i]
        else:
            text = item["text"]
        items.append("{} - {} {}".format(item["who"],
                                         text if len(text) < 325 else text[:325] + "...",
                                         item["listen"]))
    if len(items) == 1:
        return items[0]
    else:
        return "{} (and {} others: {})".format(items[0], len(items) - 1, web.haste("\n".join(items)))


@hook.command
def portal2(inp):
    """portal2 <quote> - Look up Portal 2 quote.
    Example: .portal2 demand to see life's manager"""
    return get_sound_info("portal2", inp)


@hook.command
def portal2dlc(inp):
    """portal2dlc <quote> - Look up Portal 2 DLC quote.
    Example: .portal2dlc1 these exhibits are interactive"""
    return get_sound_info("portal2dlc1", inp)


@hook.command("portal2pti")
@hook.command
def portal2dlc2(inp):
    """portal2dlc2 <quote> - Look up Portal 2 Perpetual Testing Inititive quote.
    Example: .portal2 Cave here."""
    return get_sound_info("portal2dlc2", inp)


@hook.command
def portal2music(inp):
    """portal2music <title> - Look up Portal 2 music.
    Example: .portal2music turret opera"""
    return get_sound_info("portal2music", inp)


@hook.command('portal1')
@hook.command
def portal(inp):
    """portal <quote> - Look up Portal quote.
    Example: .portal The last thing you want to do is hurt me"""
    return get_sound_info("portal1", inp)


@hook.command('portal1music')
@hook.command
def portalmusic(inp):
    """portalmusic <title> - Look up Portal music.
    Example: .portalmusic still alive"""
    return get_sound_info("portal1music", inp)


@hook.command('tf2sound')
@hook.command
def tf2(inp):
    """tf2 [who - ]<quote> - Look up TF2 quote.
    Example: .tf2 may i borrow your earpiece"""
    return get_sound_info("tf2", inp)


@hook.command
def tf2music(inp):
    """tf2music title - Look up TF2 music lyrics.
    Example: .tf2music rocket jump waltz"""
    return get_sound_info("tf2music", inp)

########NEW FILE########
__FILENAME__ = vimeo
from util import hook, http, timeformat


@hook.regex(r'vimeo.com/([0-9]+)')
def vimeo_url(match):
    """vimeo <url> -- returns information on the Vimeo video at <url>"""
    info = http.get_json('http://vimeo.com/api/v2/video/%s.json'
                         % match.group(1))

    if info:
        info[0]["duration"] = timeformat.format_time(info[0]["duration"])
        info[0]["stats_number_of_likes"] = format(
            info[0]["stats_number_of_likes"], ",d")
        info[0]["stats_number_of_plays"] = format(
            info[0]["stats_number_of_plays"], ",d")
        return ("\x02%(title)s\x02 - length \x02%(duration)s\x02 - "
                "\x02%(stats_number_of_likes)s\x02 likes - "
                "\x02%(stats_number_of_plays)s\x02 plays - "
                "\x02%(user_name)s\x02 on \x02%(upload_date)s\x02"
                % info[0])

########NEW FILE########
__FILENAME__ = weather
from util import hook, http, web

base_url = "http://api.wunderground.com/api/{}/{}/q/{}.json"


@hook.command(autohelp=None)
def weather(inp, reply=None, db=None, nick=None, bot=None, notice=None):
    """weather <location> [dontsave] -- Gets weather data
    for <location> from Wunderground."""

    api_key = bot.config.get("api_keys", {}).get("wunderground")

    if not api_key:
        return "Error: No wunderground API details."

    # initialise weather DB
    db.execute("create table if not exists weather(nick primary key, loc)")

    # if there is no input, try getting the users last location from the DB
    if not inp:
        location = db.execute("select loc from weather where nick=lower(?)",
                              [nick]).fetchone()
        if not location:
            # no location saved in the database, send the user help text
            notice(weather.__doc__)
            return
        loc = location[0]

        # no need to save a location, we already have it
        dontsave = True
    else:
        # see if the input ends with "dontsave"
        dontsave = inp.endswith(" dontsave")

        # remove "dontsave" from the input string after checking for it
        if dontsave:
            loc = inp[:-9].strip().lower()
        else:
            loc = inp

    location = http.quote_plus(loc)

    request_url = base_url.format(api_key, "geolookup/forecast/conditions", location)
    response = http.get_json(request_url)

    if 'location' not in response:
        try:
            location_id = response['response']['results'][0]['zmw']
        except KeyError:
            return "Could not get weather for that location."

        # get the weather again, using the closest match
        request_url = base_url.format(api_key, "geolookup/forecast/conditions", "zmw:" + location_id)
        response = http.get_json(request_url)

    if response['location']['state']:
        place_name = "\x02{}\x02, \x02{}\x02 (\x02{}\x02)".format(response['location']['city'],
                                                                  response['location']['state'],
                                                                  response['location']['country'])
    else:
        place_name = "\x02{}\x02 (\x02{}\x02)".format(response['location']['city'],
                                                      response['location']['country'])

    forecast_today = response["forecast"]["simpleforecast"]["forecastday"][0]
    forecast_tomorrow = response["forecast"]["simpleforecast"]["forecastday"][1]

    # put all the stuff we want to use in a dictionary for easy formatting of the output
    weather_data = {
        "place": place_name,
        "conditions": response['current_observation']['weather'],
        "temp_f": response['current_observation']['temp_f'],
        "temp_c": response['current_observation']['temp_c'],
        "humidity": response['current_observation']['relative_humidity'],
        "wind_kph": response['current_observation']['wind_kph'],
        "wind_mph": response['current_observation']['wind_mph'],
        "wind_direction": response['current_observation']['wind_dir'],
        "today_conditions": forecast_today['conditions'],
        "today_high_f": forecast_today['high']['fahrenheit'],
        "today_high_c": forecast_today['high']['celsius'],
        "today_low_f": forecast_today['low']['fahrenheit'],
        "today_low_c": forecast_today['low']['celsius'],
        "tomorrow_conditions": forecast_tomorrow['conditions'],
        "tomorrow_high_f": forecast_tomorrow['high']['fahrenheit'],
        "tomorrow_high_c": forecast_tomorrow['high']['celsius'],
        "tomorrow_low_f": forecast_tomorrow['low']['fahrenheit'],
        "tomorrow_low_c": forecast_tomorrow['low']['celsius'],
        "url": web.isgd(response["current_observation"]['forecast_url'] + "?apiref=e535207ff4757b18")
    }

    reply("{place} - \x02Current:\x02 {conditions}, {temp_f}F/{temp_c}C, {humidity}, "
          "Wind: {wind_kph}KPH/{wind_mph}MPH {wind_direction}, \x02Today:\x02 {today_conditions}, "
          "High: {today_high_f}F/{today_high_c}C, Low: {today_low_f}F/{today_low_c}C. "
          "\x02Tomorrow:\x02 {tomorrow_conditions}, High: {tomorrow_high_f}F/{tomorrow_high_c}C, "
          "Low: {tomorrow_low_f}F/{tomorrow_low_c}C - {url}".format(**weather_data))

    if location and not dontsave:
        db.execute("insert or replace into weather(nick, loc) values (?,?)",
                   (nick.lower(), location))
        db.commit()

########NEW FILE########
__FILENAME__ = wikipedia
"""Searches wikipedia and returns first sentence of article
Scaevolus 2009"""

import re

from util import hook, http, text


api_prefix = "http://en.wikipedia.org/w/api.php"
search_url = api_prefix + "?action=opensearch&format=xml"

paren_re = re.compile('\s*\(.*\)$')


@hook.command('w')
@hook.command
def wiki(inp):
    """wiki <phrase> -- Gets first sentence of Wikipedia article on <phrase>."""

    x = http.get_xml(search_url, search=inp)

    ns = '{http://opensearch.org/searchsuggest2}'
    items = x.findall(ns + 'Section/' + ns + 'Item')

    if not items:
        if x.find('error') is not None:
            return 'error: %(code)s: %(info)s' % x.find('error').attrib
        else:
            return 'No results found.'

    def extract(item):
        return [item.find(ns + x).text for x in
                ('Text', 'Description', 'Url')]

    title, desc, url = extract(items[0])

    if 'may refer to' in desc:
        title, desc, url = extract(items[1])

    title = paren_re.sub('', title)

    if title.lower() not in desc.lower():
        desc = title + desc

    desc = u' '.join(desc.split())  # remove excess spaces

    desc = text.truncate_str(desc, 200)

    return u'{} :: {}'.format(desc, http.quote(url, ':/'))

########NEW FILE########
__FILENAME__ = wolframalpha
import re

from util import hook, http, text, web


@hook.command('math')
@hook.command('calc')
@hook.command('wa')
@hook.command
def wolframalpha(inp, bot=None):
    """wa <query> -- Computes <query> using Wolfram Alpha."""
    api_key = bot.config.get("api_keys", {}).get("wolframalpha", None)

    if not api_key:
        return "error: missing api key"

    url = 'http://api.wolframalpha.com/v2/query?format=plaintext'

    result = http.get_xml(url, input=inp, appid=api_key)

    # get the URL for a user to view this query in a browser
    query_url = "http://www.wolframalpha.com/input/?i=" + \
                http.quote_plus(inp.encode('utf-8'))
    short_url = web.try_isgd(query_url)

    pod_texts = []
    for pod in result.xpath("//pod[@primary='true']"):
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
            pod_texts.append(title + u': ' + u', '.join(results))

    ret = u' - '.join(pod_texts)

    if not pod_texts:
        return 'No results.'

    ret = re.sub(r'\\(.)', r'\1', ret)

    def unicode_sub(match):
        return unichr(int(match.group(1), 16))

    ret = re.sub(r'\\:([0-9a-z]{4})', unicode_sub, ret)

    ret = text.truncate_str(ret, 250)

    if not ret:
        return 'No results.'

    return u"{} - {}".format(ret, short_url)

########NEW FILE########
__FILENAME__ = xkcd
import re

from util import hook, http


xkcd_re = (r'(.*:)//(www.xkcd.com|xkcd.com)(.*)', re.I)
months = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 7: 'July', 8: 'August',
          9: 'September', 10: 'October', 11: 'November', 12: 'December'}


def xkcd_info(xkcd_id, url=False):
    """ takes an XKCD entry ID and returns a formatted string """
    data = http.get_json("http://www.xkcd.com/" + xkcd_id + "/info.0.json")
    date = "%s %s %s" % (data['day'], months[int(data['month'])], data['year'])
    if url:
        url = " | http://xkcd.com/" + xkcd_id.replace("/", "")
    return "xkcd: \x02%s\x02 (%s)%s" % (data['title'], date, url if url else "")


def xkcd_search(term):
    search_term = http.quote_plus(term)
    soup = http.get_soup("http://www.ohnorobot.com/index.pl?s={}&Search=Search&"
                         "comic=56&e=0&n=0&b=0&m=0&d=0&t=0".format(search_term))
    result = soup.find('li')
    if result:
        url = result.find('div', {'class': 'tinylink'}).text
        xkcd_id = url[:-1].split("/")[-1]
        print xkcd_id
        return xkcd_info(xkcd_id, url=True)
    else:
        return "No results found!"


@hook.regex(*xkcd_re)
def xkcd_url(match):
    xkcd_id = match.group(3).split(" ")[0].split("/")[1]
    return xkcd_info(xkcd_id)


@hook.command
def xkcd(inp):
    """xkcd <search term> - Search for xkcd comic matching <search term>"""
    return xkcd_search(inp)

########NEW FILE########
__FILENAME__ = yahooanswers
from util import hook, web, text


@hook.command
def answer(inp):
    """answer <query> -- find the answer to a question on Yahoo! Answers"""

    query = "SELECT Subject, ChosenAnswer, Link FROM answers.search WHERE query=@query LIMIT 1"
    result = web.query(query, {"query": inp.strip()}).one()

    short_url = web.try_isgd(result["Link"])

    # we split the answer and .join() it to remove newlines/extra spaces
    answer_text = text.truncate_str(' '.join(result["ChosenAnswer"].split()), 80)

    return u'\x02{}\x02 "{}" - {}'.format(result["Subject"], answer_text, short_url)

########NEW FILE########
__FILENAME__ = youtube
import re
import time

from util import hook, http, timeformat


youtube_re = (r'(?:youtube.*?(?:v=|/v/)|youtu\.be/|yooouuutuuube.*?id=)'
              '([-_a-zA-Z0-9]+)', re.I)

base_url = 'http://gdata.youtube.com/feeds/api/'
api_url = base_url + 'videos/{}?v=2&alt=jsonc'
search_api_url = base_url + 'videos?v=2&alt=jsonc&max-results=1'
video_url = "http://youtu.be/%s"


def plural(num=0, text=''):
    return "{:,} {}{}".format(num, text, "s"[num == 1:])


def get_video_description(video_id):
    request = http.get_json(api_url.format(video_id))

    if request.get('error'):
        return

    data = request['data']

    out = u'\x02{}\x02'.format(data['title'])

    if not data.get('duration'):
        return out

    length = data['duration']
    out += u' - length \x02{}\x02'.format(timeformat.format_time(length, simple=True))

    if 'ratingCount' in data:
        likes = plural(int(data['likeCount']), "like")
        dislikes = plural(data['ratingCount'] - int(data['likeCount']), "dislike")

        percent = 100 * float(data['likeCount']) / float(data['ratingCount'])
        out += u' - {}, {} (\x02{:.1f}\x02%)'.format(likes,
                                                     dislikes, percent)

    if 'viewCount' in data:
        views = data['viewCount']
        out += u' - \x02{:,}\x02 view{}'.format(views, "s"[views == 1:])

    try:
        uploader = http.get_json(base_url + "users/{}?alt=json".format(data["uploader"]))["entry"]["author"][0]["name"][
            "$t"]
    except:
        uploader = data["uploader"]

    upload_time = time.strptime(data['uploaded'], "%Y-%m-%dT%H:%M:%S.000Z")
    out += u' - \x02{}\x02 on \x02{}\x02'.format(uploader,
                                                 time.strftime("%Y.%m.%d", upload_time))

    if 'contentRating' in data:
        out += u' - \x034NSFW\x02'

    return out


@hook.regex(*youtube_re)
def youtube_url(match):
    return get_video_description(match.group(1))


@hook.command('you')
@hook.command('yt')
@hook.command('y')
@hook.command
def youtube(inp):
    """youtube <query> -- Returns the first YouTube search result for <query>."""
    request = http.get_json(search_api_url, q=inp)

    if 'error' in request:
        return 'error performing search'

    if request['data']['totalItems'] == 0:
        return 'no results found'

    video_id = request['data']['items'][0]['id']

    return get_video_description(video_id) + u" - " + video_url % video_id


@hook.command('ytime')
@hook.command
def youtime(inp):
    """youtime <query> -- Gets the total run time of the first YouTube search result for <query>."""
    request = http.get_json(search_api_url, q=inp)

    if 'error' in request:
        return 'error performing search'

    if request['data']['totalItems'] == 0:
        return 'no results found'

    video_id = request['data']['items'][0]['id']
    request = http.get_json(api_url.format(video_id))

    if request.get('error'):
        return
    data = request['data']

    if not data.get('duration'):
        return

    length = data['duration']
    views = data['viewCount']
    total = int(length * views)

    length_text = timeformat.format_time(length, simple=True)
    total_text = timeformat.format_time(total, accuracy=8)

    return u'The video \x02{}\x02 has a length of {} and has been viewed {:,} times for ' \
           u'a total run time of {}!'.format(data['title'], length_text, views,
                                             total_text)


ytpl_re = (r'(.*:)//(www.youtube.com/playlist|youtube.com/playlist)(:[0-9]+)?(.*)', re.I)


@hook.regex(*ytpl_re)
def ytplaylist_url(match):
    location = match.group(4).split("=")[-1]
    try:
        soup = http.get_soup("https://www.youtube.com/playlist?list=" + location)
    except Exception:
        return "\x034\x02Invalid response."
    title = soup.find('title').text.split('-')[0].strip()
    author = soup.find('img', {'class': 'channel-header-profile-image'})['title']
    num_videos = soup.find('ul', {'class': 'header-stats'}).findAll('li')[0].text.split(' ')[0]
    views = soup.find('ul', {'class': 'header-stats'}).findAll('li')[1].text.split(' ')[0]
    return u"\x02%s\x02 - \x02%s\x02 views - \x02%s\x02 videos - \x02%s\x02" % (title, views, num_videos, author)

########NEW FILE########
__FILENAME__ = bucket
from time import time


class TokenBucket(object):
    """An implementation of the token bucket algorithm.
    
    >>> bucket = TokenBucket(80, 0.5)
    >>> print bucket.consume(10)
    True
    >>> print bucket.consume(90)
    False
    """
    def __init__(self, tokens, fill_rate):
        """tokens is the total tokens in the bucket. fill_rate is the
        rate in tokens/second that the bucket will be refilled."""
        self.capacity = float(tokens)
        self._tokens = float(tokens)
        self.fill_rate = float(fill_rate)
        self.timestamp = time()

    def consume(self, tokens):
        """Consume tokens from the bucket. Returns True if there were
        sufficient tokens otherwise False."""
        if tokens <= self.tokens:
            self._tokens -= tokens
        else:
            return False
        return True

    def refill(self):
        self._tokens = self.capacity

    def get_tokens(self):
        now = time()
        if self._tokens < self.capacity:
            delta = self.fill_rate * (now - self.timestamp)
            self._tokens = min(self.capacity, self._tokens + delta)
        self.timestamp = now
        return self._tokens
    tokens = property(get_tokens)
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

import cookielib
import json
import urllib
import urllib2
import urlparse

from urllib import quote, quote_plus as _quote_plus

from lxml import etree, html
from bs4 import BeautifulSoup

# used in plugins that import this
from urllib2 import URLError, HTTPError

ua_cloudbot = 'Cloudbot/DEV http://github.com/CloudDev/CloudBot'

ua_firefox = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:17.0) Gecko/17.0' \
             ' Firefox/17.0'
ua_old_firefox = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; ' \
                 'rv:1.8.1.6) Gecko/20070725 Firefox/2.0.0.6'
ua_internetexplorer = 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
ua_chrome = 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.4 (KHTML, ' \
            'like Gecko) Chrome/22.0.1229.79 Safari/537.4'

jar = cookielib.CookieJar()


def get(*args, **kwargs):
    return open(*args, **kwargs).read()


def get_url(*args, **kwargs):
    return open(*args, **kwargs).geturl()


def get_html(*args, **kwargs):
    return html.fromstring(get(*args, **kwargs))


def get_soup(*args, **kwargs):
    return BeautifulSoup(get(*args, **kwargs), 'lxml')


def get_xml(*args, **kwargs):
    return etree.fromstring(get(*args, **kwargs))


def get_json(*args, **kwargs):
    return json.loads(get(*args, **kwargs))


def open(url, query_params=None, user_agent=None, post_data=None,
         referer=None, get_method=None, cookies=False, timeout=None, headers=None, **kwargs):
    if query_params is None:
        query_params = {}

    if user_agent is None:
        user_agent = ua_cloudbot

    query_params.update(kwargs)

    url = prepare_url(url, query_params)

    request = urllib2.Request(url, post_data)

    if get_method is not None:
        request.get_method = lambda: get_method

    if headers is not None:
        for header_key, header_value in headers.iteritems():
            request.add_header(header_key, header_value)

    request.add_header('User-Agent', user_agent)

    if referer is not None:
        request.add_header('Referer', referer)

    if cookies:
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(jar))
    else:
        opener = urllib2.build_opener()

    if timeout:
        return opener.open(request, timeout=timeout)
    else:
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


def unescape(s):
    if not s.strip():
        return s
    return html.fromstring(s).text_content()

########NEW FILE########
__FILENAME__ = pyexec
import http
import web


def eval_py(code, paste_multiline=True):
    attempts = 0

    while True:
        try:
            output = http.get("http://eval.appspot.com/eval", statement=code).rstrip('\n')
            # sometimes the API returns a blank string on first attempt, lets try again
            # and make sure it is actually supposed to be a blank string. ._.
            if output == "":
                output = http.get("http://eval.appspot.com/eval", statement=code).rstrip('\n')
            break
        except http.HTTPError:
            if attempts > 2:
                return "Failed to execute code."
            else:
                attempts += 1
                continue

    if "Traceback (most recent call last):" in output:
        status = "Python error: "
    else:
        status = "Code executed sucessfully: "

    if "\n" in output and paste_multiline:
        return status + web.haste(output)
    else:
        return output

########NEW FILE########
__FILENAME__ = text
# -*- coding: utf-8 -*-
""" formatting.py - handy functions for formatting text
    this file contains code from the following URL:
    <http://code.djangoproject.com/svn/django/trunk/django/utils/text.py>
"""

import re

from HTMLParser import HTMLParser
import htmlentitydefs


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.result = []

    def handle_data(self, d):
        self.result.append(d)

    def handle_charref(self, number):
        codepoint = int(number[1:], 16) if number[0] in (u'x', u'X') else int(number)
        self.result.append(unichr(codepoint))

    def handle_entityref(self, name):
        codepoint = htmlentitydefs.name2codepoint[name]
        self.result.append(unichr(codepoint))

    def get_text(self):
        return u''.join(self.result)


def strip_html(html):
    s = HTMLTextExtractor()
    s.feed(html)
    return s.get_text()


def munge(text, munge_count=0):
    """munges up text."""
    reps = 0
    for n in xrange(len(text)):
        rep = character_replacements.get(text[n])
        if rep:
            text = text[:n] + rep.decode('utf8') + text[n + 1:]
            reps += 1
            if reps == munge_count:
                break
    return text


character_replacements = {
    'a': 'ä',
    'b': 'Б',
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
    'm': 'ṁ',
    'n': 'ñ',
    'o': 'ö',
    'p': 'ρ',
    'q': 'ʠ',
    'r': 'ŗ',
    's': 'š',
    't': 'ţ',
    'u': 'ü',
    'v': '',
    'w': 'ω',
    'x': 'χ',
    'y': 'ÿ',
    'z': 'ź',
    'A': 'Å',
    'B': 'Β',
    'C': 'Ç',
    'D': 'Ď',
    'E': 'Ē',
    'F': 'Ḟ',
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
    'Q': 'Ｑ',
    'R': 'Ŗ',
    'S': 'Š',
    'T': 'Ţ',
    'U': 'Ů',
    'V': 'Ṿ',
    'W': 'Ŵ',
    'X': 'Χ',
    'Y': 'Ỳ',
    'Z': 'Ż'}


def capitalize_first(line):
    """
    capitalises the first letter of words
    (keeps other letters intact)
    """
    return ' '.join([s[0].upper() + s[1:] for s in line.split(' ')])


def multiword_replace(text, wordDic):
    """
    take a text and replace words that match a key in a dictionary with
    the associated value, return the changed text
    """
    rc = re.compile('|'.join(map(re.escape, wordDic)))

    def translate(match):
        return wordDic[match.group(0)]
    return rc.sub(translate, text)


def truncate_words(content, length=10, suffix='...'):
    """Truncates a string after a certain number of words."""
    nmsg = content.split(" ")
    out = None
    x = 0
    for i in nmsg:
        if x <= length:
            if out:
                out = out + " " + nmsg[x]
            else:
                out = nmsg[x]
        x += 1
    if x <= length:
        return out
    else:
        return out + suffix


# from <http://stackoverflow.com/questions/250357/smart-truncate-in-python>
def truncate_str(content, length=100, suffix='...'):
    """Truncates a string after a certain number of chars.
    @rtype : str
    """
    if len(content) <= length:
        return content
    else:
        return content[:length].rsplit(' ', 1)[0] + suffix


# ALL CODE BELOW THIS LINE IS COVERED BY THE FOLLOWING AGREEMENT:

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

# Expression to match some_token and some_token="with spaces" (and similarly
# for single-quoted strings).

split_re = re.compile(r"""((?:[^\s'"]*(?:(?:"(?:[^"\\]|\\.)*" | '(?:["""
                      r"""^'\\]|\\.)*')[^\s'"]*)+) | \S+)""", re.VERBOSE)


def smart_split(text):
    r"""
    Generator that splits a string by spaces, leaving quoted phrases together.
    Supports both single and double quotes, and supports escaping quotes with
    backslashes. In the output, strings will keep their initial and trailing
    quote marks and escaped quotes will remain escaped (the results can then
    be further processed with unescape_string_literal()).

    >>> list(smart_split(r'This is "a person\'s" test.'))
    [u'This', u'is', u'"a person\\\'s"', u'test.']
    >>> list(smart_split(r"Another 'person\'s' test."))
    [u'Another', u"'person\\'s'", u'test.']
    >>> list(smart_split(r'A "\"funky\" style" test.'))
    [u'A', u'"\\"funky\\" style"', u'test.']
    """
    for bit in split_re.finditer(text):
        yield bit.group(0)


def get_text_list(list_, last_word='or'):
    """
    >>> get_text_list(['a', 'b', 'c', 'd'])
    u'a, b, c or d'
    >>> get_text_list(['a', 'b', 'c'], 'and')
    u'a, b and c'
    >>> get_text_list(['a', 'b'], 'and')
    u'a and b'
    >>> get_text_list(['a'])
    u'a'
    >>> get_text_list([])
    u''
    """
    if len(list_) == 0:
        return ''
    if len(list_) == 1:
        return list_[0]
    return '%s %s %s' % (
        # Translators: This string is used as a separator between list elements
        ', '.join([i for i in list_][:-1]),
        last_word, list_[-1])

########NEW FILE########
__FILENAME__ = textgen
import re
import random

TEMPLATE_RE = re.compile(r"\{(.+?)\}")


class TextGenerator(object):
    def __init__(self, templates, parts, default_templates=None, variables=None):
        self.templates = templates
        self.default_templates = default_templates
        self.parts = parts
        self.variables = variables

    def generate_string(self, template=None):
        """
        Generates one string using the specified templates.
        If no templates are specified, use a random template from the default_templates list.
        """
        # this is bad
        if self.default_templates:
            text = self.templates[template or random.choice(self.default_templates)]
        else:
            text = random.choice(self.templates)

        # replace static variables in the template with provided values
        if self.variables:
            for key, value in self.variables.items():
                text = text.replace("{%s}" % key, value)

        # get a list of all text parts we need
        required_parts = TEMPLATE_RE.findall(text)

        for required_part in required_parts:
            ppart = self.parts[required_part]
            # check if the part is a single string or a list
            if not isinstance(ppart, basestring):
                part = random.choice(self.parts[required_part])
            else:
                part = self.parts[required_part]
            text = text.replace("{%s}" % required_part, part)

        return text

    def generate_strings(self, amount, template=None):
        strings = []
        for i in xrange(amount):
            strings.append(self.generate_string())
        return strings

    def get_template(self, template):
        return self.templates[template]

########NEW FILE########
__FILENAME__ = timeformat
from util import text

def format_time(seconds, count=3, accuracy=6, simple=False):
    """
    Takes a length of time in seconds and returns a string describing that length of time.
    This function has a number of optional arguments that can be combined:

    SIMPLE: displays the time in a simple format
    >>> format_time(SECONDS)
    1 hour, 2 minutes and 34 seconds
    >>> format_time(SECONDS, simple=True)
    1h 2m 34s

    COUNT: how many periods should be shown (default 3)
    >>> format_time(SECONDS)
    147 years, 9 months and 8 weeks
    >>> format_time(SECONDS, count=6)
    147 years, 9 months, 7 weeks, 18 hours, 12 minutes and 34 seconds
    """

    if simple:
        periods = [
                ('c', 60 * 60 * 24 * 365 * 100),
                ('de', 60 * 60 * 24 * 365 * 10),
                ('y', 60 * 60 * 24 * 365),
                ('m', 60 * 60 * 24 * 30),
                ('d', 60 * 60 * 24),
                ('h', 60 * 60),
                ('m', 60),
                ('s', 1)
                ]
    else:
        periods = [
                (('century', 'centuries'), 60 * 60 * 24 * 365 * 100),
                (('decade', 'decades'), 60 * 60 * 24 * 365 * 10),
                (('year', 'years'), 60 * 60 * 24 * 365),
                (('month', 'months'), 60 * 60 * 24 * 30),
                (('day', 'days'), 60 * 60 * 24),
                (('hour', 'hours'), 60 * 60),
                (('minute', 'minutes'), 60),
                (('second', 'seconds'), 1)
                ]

    periods = periods[-accuracy:]

    strings = []
    i = 0
    for period_name, period_seconds in periods:
        if i < count:
            if seconds > period_seconds:
                    period_value, seconds = divmod(seconds, period_seconds)
                    i += 1
                    if simple:
                        strings.append("{}{}".format(period_value, period_name))
                    else:
                        if period_value == 1:
                            strings.append("{} {}".format(period_value, period_name[0]))
                        else:
                            strings.append("{} {}".format(period_value, period_name[1]))
        else:
            break

    if simple:
        return " ".join(strings)
    else:
        return text.get_text_list(strings, "and")
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

    if isinstance(now, int) or isinstance(now, float):
        now = datetime.datetime.fromtimestamp(now)

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


normalizers = (Normalizer(re.compile(
    r'(?:https?://)?(?:[a-zA-Z0-9\-]+\.)?(?:amazon|amzn){1}\.(?P<tld>[a-zA-Z\.]{2,})\/(gp/(?:product|offer-listing|customer-media/product-gallery)/|exec/obidos/tg/detail/-/|o/ASIN/|dp/|(?:[A-Za-z0-9\-]+)/dp/)?(?P<ASIN>[0-9A-Za-z]{10})'),
                          lambda m: r'http://amazon.%s/dp/%s' % (m.group('tld'), m.group('ASIN'))),
               Normalizer(re.compile(r'.*waffleimages\.com.*/([0-9a-fA-F]{40})'),
                          lambda m: r'http://img.waffleimages.com/%s' % m.group(1)),
               Normalizer(re.compile(r'(?:youtube.*?(?:v=|/v/)|youtu\.be/|yooouuutuuube.*?id=)([-_a-zA-Z0-9]+)'),
                          lambda m: r'http://youtube.com/watch?v=%s' % m.group(1)),
)


def normalize(url, assume_scheme=False):
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

    if assume_scheme and not scheme:
        scheme = assume_scheme.lower()

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
__FILENAME__ = web
""" web.py - handy functions for web services """

import http
import urlnorm
import json
import urllib
import yql

short_url = "http://is.gd/create.php"
paste_url = "http://hastebin.com"
yql_env = "http://datatables.org/alltables.env"

YQL = yql.Public()


class ShortenError(Exception):
    def __init__(self, code, text):
        self.code = code
        self.text = text

    def __str__(self):
        return self.text


def isgd(url):
    """ shortens a URL with the is.gd API """
    url = urlnorm.normalize(url.encode('utf-8'), assume_scheme='http')
    params = urllib.urlencode({'format': 'json', 'url': url})
    request = http.get_json("http://is.gd/create.php?%s" % params)

    if "errorcode" in request:
        raise ShortenError(request["errorcode"], request["errormessage"])
    else:
        return request["shorturl"]


def try_isgd(url):
    try:
        out = isgd(url)
    except (ShortenError, http.HTTPError):
        out = url
    return out


def haste(text, ext='txt'):
    """ pastes text to a hastebin server """
    page = http.get(paste_url + "/documents", post_data=text)
    data = json.loads(page)
    return ("%s/%s.%s" % (paste_url, data['key'], ext))


def query(query, params={}):
    """ runs a YQL query and returns the results """
    return YQL.execute(query, params, env=yql_env)

########NEW FILE########
