__FILENAME__ = echo-coro
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import socket
import sys
import os
import signal

from gogreen import coro
from gogreen import start

ECHO_PORT = 5580

class EchoClient(coro.Thread):
    def __init__(self, *args, **kwargs):
        super(EchoClient, self).__init__(*args, **kwargs)

        self.sock = kwargs['sock']
        self.addr = kwargs['addr']
        self.exit = False

    def run(self):
        self.info('Accepted connection: %r', (self.addr,))

        while not self.exit:
            try:
                buf = self.sock.recv(1024)
            except coro.CoroutineSocketWake:
                continue
            except socket.error:
                buf = ''

            if not buf:
                break

            try:
                self.sock.send(buf)
            except coro.CoroutineSocketWake:
                continue
            except socket.error:
                break

        self.sock.close()
        self.info('Connection closed: %r', (self.addr,))

    def shutdown(self):
        self.exit = True
        self.sock.wake()

class EchoServer(coro.Thread):
    def __init__(self, *args, **kwargs):
        super(EchoServer, self).__init__(*args, **kwargs)

        self.addr = kwargs['addr']
        self.sock = None
        self.exit = False

    def run(self):
        self.sock = coro.make_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.addr)
        self.sock.listen(128)

        self.info('Listening to address: %r' % (self.addr,))

        while not self.exit:
            try:
                conn, addr = self.sock.accept()
            except coro.CoroutineSocketWake:
                continue
            except Exception, e:
                self.error('Exception from accept: %r', e)
                break

            eclnt = EchoClient(addr = addr, sock = conn)
            eclnt.start()

        self.sock.close()

        for child in self.child_list():
            child.shutdown()

        self.child_wait(30)
        self.info('Server exit.')

    def shutdown(self):
        self.exit = True
        self.sock.wake()

def run(here, log, loglevel, logdir, **kwargs):
    eserv = EchoServer(addr = ('', ECHO_PORT))
    eserv.start()

    def shutdown_handler(signum, frame):
        eserv.shutdown()

    signal.signal(signal.SIGUSR2, shutdown_handler)

    try:
        coro.event_loop()
    except KeyboardInterrupt:
        pass

    return None

if __name__ == '__main__':
	conf = {
		0 : {'lockport' : 5581, 'echo_port' : 5580}, 
	}
    value = start.main(
		conf,
		run,
		name = 'echoserver',
		)
	sys.exit(value) 

########NEW FILE########
__FILENAME__ = heartbeat
#!/usr/bin/python
#
'''heartbeat

a common pattern is to do some work every N seconds. this example demestrates
how to do that with gogreen.
'''
import signal
import sys

from gogreen import coro
from gogreen import emulate
from gogreen import start
from gogreen import backdoor

# do monkeypatching of various things like sockets, etc.
#
emulate.init()

class Heartbeat(coro.Thread):

    def __init__(self, period, *args, **kwargs):
        super(Heartbeat, self).__init__(*args, **kwargs)
        self._period = period
        self._cond   = coro.coroutine_cond()
        self._exit   = False

    def run(self):
        self.info('Heartbeat: start')
        while not self._exit:
            self.info('bah-bump')
            self._cond.wait(self._period)
        self.info('Heartbeat: end')

    def shutdown(self):
        self._exit = True
        self._cond.wake_all()
        
def run(here, log, loglevel, logdir, **kwargs):
    heart = Heartbeat(
        1.2, # every 1.2 seconds
        log = log,
        )
    heart.set_log_level(loglevel)
    heart.start()

    if 'backport' in here:
        back = backdoor.BackDoorServer(
            args = (here['backport'],),
            log  = log, 
            )
        back.set_log_level(loglevel)
        back.start()

    def shutdown_handler(signum, frame):
        heart.shutdown()
        back.shutdown()

    signal.signal(signal.SIGUSR2, shutdown_handler)

    try:
        coro.event_loop()
    except KeyboardInterrupt:
        pass

    return None

if __name__ == '__main__':
    conf = {
        0 : {'lockport' : 6581, 'backport' : 5500, }, 
    }
    value = start.main(
        conf,
        run,
        name = 'heartbeat',
        )
    sys.exit(value) 

########NEW FILE########
__FILENAME__ = basebot
import socket

from gogreen import coro


class Bot(coro.Thread):
    def __init__(self,
            server_address,
            nick,
            username=None,
            realname=None,
            password=None,
            nickserv=None,
            rooms=None):
        super(Bot, self).__init__()
        self.server_address = server_address
        self.nick = nick
        self.username = username or nick
        self.realname = realname or nick
        self.password = password
        self.nickserv = nickserv
        self.rooms = rooms or []
        self.in_rooms = set()
        self.connected = self.registered = False

    def cmd(self, cmd, *args):
        args = map(str, args)
        if args and " " in args[-1] and not args[-1].startswith(":"):
            args[-1] = ":" + args[-1]

        # lock this so separate outgoing commands can't overlap
        self.write_lock.lock()
        try:
            self.sock.sendall(" ".join([cmd.upper()] + args) + "\n")
        finally:
            self.write_lock.unlock()

    def connect(self):
        raw_sock = socket.socket()
        self.sock = coro.coroutine_socket(raw_sock)
        self.sock.connect(self.server_address)
        self.write_lock = coro.coroutine_lock()
        self.connected = True

    def register(self):
        self.cmd("nick", self.nick)
        self.cmd("user", self.username, 0, 0, self.realname)
        if self.password:
            if self.nickserv:
                self.message(self.nickserv, "identify %s" % self.password)
            else:
                self.cmd("pass", self.password)
        self.registered = True

    def change_nick(self, nick):
        self.nick = nick
        self.cmd("nick", nick)

    def join_rooms(self):
        for room in self.rooms:
            if room in self.in_rooms:
                continue
            if not hasattr(room, "__iter__"):
                room = (room,)
            self.join_room(*room)

    def join_room(self, room, password=None):
        if password is None:
            self.cmd("join", room)
        else:
            self.cmd("join", room, password)
        self.in_rooms.add(room)

    def message(self, target, message):
        self.cmd("privmsg", target, message)

    def quit(self, message=None):
        self.child_wait()
        if message is None:
            self.cmd("quit")
        else:
            self.cmd("quit", message)

    def run(self):
        self.running = True

        if not self.connected:
            self.connect()
        if not self.registered:
            self.register()
        self.join_rooms()

        sockfile = self.sock.makefile()

        while self.running:
            line = sockfile.readline()

            if not line:
                break

            worker = BotWorker(self, args=(line,))
            worker.start()

    def on_ping(self, cmd, args, prefix):
        self.cmd("pong", args[0])

    def default_handler(self, cmd, args, prefix):
        pass

    def default_on_reply(self, code, args, prefix):
        pass

    def post_register(self):
        pass


class BotWorker(coro.Thread):
    def __init__(self, bot, *args, **kwargs):
        super(BotWorker, self).__init__(*args, **kwargs)
        self.bot = bot

    def _parse_line(self, line):
        prefix = None
        if line.startswith(":"):
            prefix, line = line.split(" ", 1)
            prefix = prefix[1:]

        cmd, line = line.split(" ", 1)

        if line.startswith(":"):
            args = [line[1:]]
        elif " :" in line:
            args, final_arg = line.split(" :", 1)
            args = args.split(" ")
            args.append(final_arg)
        else:
            args = line.split(" ")

        return cmd, args, prefix

    def run(self, line):
        cmd, args, prefix = self._parse_line(line.rstrip('\r\n'))
        if cmd.isdigit():
            cmd = int(cmd)
            if _code_is_error(cmd):
                raise IRCServerError(cmd, REPLY_CODES[cmd], *args)
            handler = getattr(
                    self.bot, "on_reply_%d" % cmd, self.bot.default_on_reply)
        else:
            handler = getattr(
                    self.bot, "on_%s" % cmd.lower(), self.bot.default_handler)

        handler(cmd, args, prefix)


class IRCError(Exception):
    pass


class IRCServerError(IRCError):
    pass


def _code_is_error(code):
    return code >= 400

# http://irchelp.org/irchelp/rfc/chapter6.html
REPLY_CODES = {
    200: "RPL_TRACELINK",
    201: "RPL_TRACECONNECTING",
    202: "RPL_TRACEHANDSHAKE",
    203: "RPL_TRACEUNKNOWN",
    204: "RPL_TRACEOPERATOR",
    205: "RPL_TRACEUSER",
    206: "RPL_TRACESERVER",
    208: "RPL_TRACENEWTYPE",
    211: "RPL_STATSLINKINFO",
    212: "RPL_STATSCOMMANDS",
    213: "RPL_STATSCLINE",
    214: "RPL_STATSNLINE",
    215: "RPL_STATSILINE",
    216: "RPL_STATSKLINE",
    218: "RPL_STATSYLINE",
    219: "RPL_ENDOFSTATS",
    221: "RPL_UMODEIS",
    241: "RPL_STATSLLINE",
    242: "RPL_STATSUPTIME",
    243: "RPL_STATSOLINE",
    244: "RPL_STATSHLINE",
    251: "RPL_LUSERCLIENT",
    252: "RPL_LUSEROP",
    253: "RPL_LUSERUNKNOWN",
    254: "RPL_LUSERCHANNELS",
    255: "RPL_LUSERME",
    256: "RPL_ADMINME",
    257: "RPL_ADMINLOC1",
    258: "RPL_ADMINLOC2",
    259: "RPL_ADMINEMAIL",
    261: "RPL_TRACELOG",
    300: "RPL_NONE",
    301: "RPL_AWAY",
    302: "RPL_USERHOST",
    303: "RPL_ISON",
    305: "RPL_UNAWAY",
    306: "RPL_NOAWAY",
    311: "RPL_WHOISUSER",
    312: "RPL_WHOISSERVER",
    313: "RPL_WHOISOPERATOR",
    314: "RPL_WHOWASUSER",
    315: "RPL_ENDOFWHO",
    317: "RPL_WHOISIDLE",
    318: "RPL_ENDOFWHOIS",
    319: "RPL_WHOISCHANNELS",
    321: "RPL_LISTSTART",
    322: "RPL_LIST",
    323: "RPL_LISTEND",
    324: "RPL_CHANNELMODEIS",
    331: "RPL_NOTOPIC",
    332: "RPL_TOPIC",
    341: "RPL_INVITING",
    342: "RPL_SUMMONING",
    351: "RPL_VERSION",
    352: "RPL_WHOREPLY",
    353: "RPL_NAMREPLY",
    364: "RPL_LINKS",
    365: "RPL_ENDOFLINKS",
    366: "RPL_ENDOFNAMES",
    367: "RPL_BANLIST",
    368: "RPL_ENDOFBANLIST",
    369: "RPL_ENDOFWHOWAS",
    371: "RPL_INFO",
    372: "RPL_MOTD",
    374: "RPL_ENDOFINFO",
    375: "RPL_MOTDSTART",
    376: "RPL_ENDOFMOTD",
    381: "RPL_YOUREOPER",
    382: "RPL_REHASHING",
    391: "RPL_TIME",
    392: "RPL_USERSSTART",
    393: "RPL_USERS",
    394: "RPL_ENDOFUSERS",
    395: "RPL_NOUSERS",

    401: "ERR_NOSUCHNICK",
    402: "ERR_NOSUCHSERVER",
    403: "ERR_NOSUCHCHANNEL",
    404: "ERR_CANNOTSENDTOCHAN",
    405: "ERR_TOOMANYCHANNELS",
    406: "ERR_WASNOSUCHNICK",
    407: "ERR_TOOMANYTARGETS",
    409: "ERR_NOORIGIN",
    411: "ERR_NORECIPIENT",
    412: "ERR_NOTEXTTOSEND",
    413: "ERR_NOTOPLEVEL",
    414: "ERR_WILDTOPLEVEL",
    421: "ERR_UNKNOWNCOMMAND",
    422: "ERR_NOMOTD",
    423: "ERR_NOADMININFO",
    424: "ERR_FILEERROR",
    431: "ERR_NONICKNAMEGIVEN",
    432: "ERR_ERRONEUSENICKNAME",
    433: "ERR_NICKNAMEINUSE",
    436: "ERR_NICKCOLLISION",
    441: "ERR_USERNOTINCHANNEL",
    442: "ERR_NOTONCHANNEL",
    443: "ERR_USERONCHANNEL",
    444: "ERR_NOLOGIN",
    445: "ERR_SUMMONDISABLED",
    446: "ERR_USERSDISABLED",
    451: "ERR_NOTREGISTERED",
    461: "ERR_NEEDMOREPARAMS",
    462: "ERR_ALREADYREGISTERED",
    463: "ERR_NOPERFORMHOST",
    464: "ERR_PASSWDMISMATCH",
    465: "ERR_YOUREBANNEDCREEP",
    467: "ERR_KEYSET",
    471: "ERR_CHANNELISFULL",
    472: "ERR_UNKNOWNMODE",
    473: "ERR_INVITEONLYCHAN",
    474: "ERR_BANNEDFROMCHAN",
    475: "ERR_BADCHANNELKEY",
    481: "ERR_NOPRIVILEGES",
    482: "ERR_CHANOPRIVSNEEDED",
    483: "ERR_CANTKILLSERVER",
    491: "ERR_NOOPERHOST",
    501: "ERR_UMODEUNKNOWNFLAG",
    502: "ERR_USERSDONTMATCH",
}

########NEW FILE########
__FILENAME__ = cmdbot
import basebot


class CmdBot(basebot.Bot):
    class commander(object):
        def __init__(self, bot):
            self.bot = bot

        def ping(self, rest):
            return 'pong'

    def __init__(self, *args, **kwargs):
        super(CmdBot, self).__init__(*args, **kwargs)
        self.cmds = self.commander(self)

    def on_privmsg(self, cmd, args, prefix):
        parent = super(CmdBot, self)
        if hasattr(parent, "on_privmsg"):
            parent.on_privmsg(cmd, args, prefix)

        sender = prefix.split("!", 1)[0]
        to, msg = args

        if to in self.in_rooms:
            if not msg.startswith(self.nick):
                return
            rest = msg[len(self.nick):].lstrip(": ")
        else:
            rest = msg

        if " " in rest:
            cmd_name, rest = rest.split(" ", 1)
        else:
            cmd_name, rest = rest, ""

        handler = getattr(self.cmds, cmd_name, None)
        result = None
        if handler:
            result = handler(rest)

        if result:
            if to in self.in_rooms:
                self.message(to, "%s: %s" % (sender, result))
            elif to == self.nick:
                self.message(sender, result)
            else:
                raise basebot.IRCError("unknown target: %s" % to)

########NEW FILE########
__FILENAME__ = logbot
import logging.handlers

import basebot


class LogBot(basebot.Bot):
    filename_format = "%s.log"
    message_format = "[%(asctime)s] %(message)s"

    def __init__(self, *args, **kwargs):
        super(LogBot, self).__init__(*args, **kwargs)
        self.logs = {}

    def join_room(self, room, password=None):
        super(LogBot, self).join_room(room, password)

        handler = logging.handlers.RotatingFileHandler(
                self.filename_format % room, 'a', 6291456, 5)
        handler.setFormatter(logging.Formatter(self.message_format))
        logger = logging.Logger(room)
        logger.addHandler(handler)
        self.logs[room] = logger

        self.message(room, "(this conversation is being recorded)")

    def on_privmsg(self, cmd, args, prefix):
        parent = super(LogBot, self)
        if hasattr(parent, "on_privmsg"):
            parent.on_privmsg(cmd, args, prefix)

        sender = prefix.split("!", 1)[0]
        to, msg = args
        if to in self.logs:
            self.logs[to].info("<%s> %s" % (sender, msg))

    def on_join(self, cmd, args, prefix):
        parent = super(LogBot, self)
        if hasattr(parent, "on_join"):
            parent.on_join(cmd, args, prefix)

        sender = prefix.split("!", 1)[0]
        room = args[0]

        if room in self.logs:
            self.logs[room].info("<%s> joined %s" % (sender, room))

    def on_part(self, cmd, args, prefix):
        parent = super(LogBot, self)
        if hasattr(parent, "on_part"):
            parent.on_part(cmd, args, prefix)

        sender = prefix.split("!", 1)[0]
        room = args[0]

        if room in self.logs:
            self.logs[room].info("<%s> left %s" % (sender, room))

    def cmd(self, cmd, *args):
        super(LogBot, self).cmd(cmd, *args)

        if cmd.lower() == "privmsg":
            target, message = args
            if target in self.logs:
                self.logs[target].info("<%s> %s" % (self.nick, message))

########NEW FILE########
__FILENAME__ = opbot
import basebot


class OpsHolderBot(basebot.Bot):
    '''A most inactive bot, it will just sit in a room and hold any chanops you
    give it, doling out chanops upon request (when you provide the password)

    to get it to op you, /msg it with the password, a space, and the room name

    to start it up, do something like this:
    >>> bot = OpsHolderBot(
    >>>         ("example.irc.server.com", 6667),
    >>>         "bot_nick",
    >>>         password=irc_password_for_nick,
    >>>         ops_password=password_for_giving_chanops,
    >>>         rooms=["#list", "#of", "#channels", "#to", "#serve"])
    >>> bot.start()
    >>> coro.event_loop()
    '''
    def __init__(self, *args, **kwargs):
        self._ops_password = kwargs.pop("ops_password")
        super(OpsHolderBot, self).__init__(*args, **kwargs)
        self._chanops = {}

    def join_room(self, room, passwd=None):
        super(OpsHolderBot, self).join_room(room, passwd)
        self._chanops[room] = False

    def on_mode(self, cmd, args, prefix):
        parent = super(OpsHolderBot, self)
        if hasattr(parent, "on_mode"):
            parent.on_mode(cmd, args, prefix)

        # MODE is how another user would give us ops -- test for that case
        context, mode_change = args[:2]
        if context.startswith("#") and \
                mode_change.startswith("+") and \
                "o" in mode_change and\
                len(args) > 2 and args[2] == self.nick:
            self._chanops[context] = True

    def on_privmsg(self, cmd, args, prefix):
        parent = super(OpsHolderBot, self)
        if hasattr(parent, "on_privmsg"):
            parent.on_privmsg(cmd, args, prefix)

        # ignore channels
        if args[0] != self.nick:
            return

        sender = prefix.split("!", 1)[0]

        if " " not in args[1]:
            return
        passwd, roomname = args[1].rsplit(" ", 1)

        if passwd == self._ops_password:
            if self._chanops.get(roomname):
                # grant chanops
                self.cmd("mode", roomname, "+o", sender)
            else:
                self.message(sender, "I don't have ops to give in that room")
        else:
            self.message(sender, "sorry, wrong password")

    def on_reply_353(self, code, args, prefix):
        parent = super(OpsHolderBot, self)
        if hasattr(parent, "on_reply_353"):
            parent.on_reply_353(cmd, args, prefix)

        # 353 is sent when joining a room -- this tests to see if we are given
        # chanops upon entrance (we are the first here, creating the room)
        names = args[-1]
        if "@" + self.nick in names.split(" "):
            self._chanops[args[-2]] = True

########NEW FILE########
__FILENAME__ = backdoor
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 1999, 2000 by eGroups, Inc.
# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import coro
import socket
import string
import StringIO
import sys
import traceback

# Originally, this object implemented the file-output api, and set
# sys.stdout and sys.stderr to 'self'.  However, if any other
# coroutine ran, it would see the captured definition of sys.stdout,
# and would send its output here, instead of the expected place.  Now
# the code captures all output using StringIO.  A little less
# flexible, a little less efficient, but much less surprising!
# [Note: this is exactly the same problem addressed by Scheme
#  dynamic-wind facility]

class BackDoorClient(coro.Thread):
    def init(self):
        self.address = None
        self.socket  = None
        self.buffer  = ''
        self.lines   = []
        self.exit    = False
        self.multilines = []
        self.line_separator = '\r\n'
        #
        # allow the user to change the prompts:
        #
        if not sys.__dict__.has_key('ps1'):
            sys.ps1 = '>>> '
        if not sys.__dict__.has_key('ps2'):
            sys.ps2 = '... '

    def send (self, data):
        olb = lb = len(data)
        while lb:
            ns = self.socket.send (data)
            lb = lb - ns
        return olb

    def prompt (self):
        if self.multilines:
            self.send (sys.ps2)
        else:
            self.send (sys.ps1)

    def read_line (self):
        if self.lines:
            l = self.lines[0]
            self.lines = self.lines[1:]
            return l
        else:
            while not self.lines:
                block = self.socket.recv (8192)
                if not block:
                    return None
                elif block == '\004':
                    self.socket.close()
                    return None
                else:
                    self.buffer = self.buffer + block
                    lines = string.split (self.buffer, self.line_separator)
                    for l in lines[:-1]:
                        self.lines.append (l)
                    self.buffer = lines[-1]
            return self.read_line()

    def run(self, conn, addr):
        self.socket  = conn
        self.address = addr

        # a call to socket.setdefaulttimeout will mean that this backdoor
        # has a timeout associated with it. to counteract this set the
        # socket timeout to None here.
        self.socket.settimeout(None)

        self.info('Incoming backdoor connection from %r' % (self.address,))
        #
        # print header for user
        #
        self.send ('Python ' + sys.version + self.line_separator)
        self.send (sys.copyright + self.line_separator)
        #
        # this does the equivalent of 'from __main__ import *'
        #
        env = sys.modules['__main__'].__dict__.copy()
        #
        # wait for imput and process
        #
        while not self.exit:
            self.prompt()
            try:
                line = self.read_line()
            except coro.CoroutineSocketWake:
                continue

            if line is None:
                break
            elif self.multilines:
                self.multilines.append(line)
                if line == '':
                    code = string.join(self.multilines, '\n')
                    self.parse(code, env)
                    # we do this after the parsing so parse() knows not to do
                    # a second round of multiline input if it really is an
                    # unexpected EOF
                    self.multilines = []
            else:
                self.parse(line, env)

        self.info('Backdoor connection closing')

        self.socket.close()
        self.socket = None
        return None

    def parse(self, line, env):
        save = sys.stdout, sys.stderr
        output = StringIO.StringIO()
        try:
            try:
                sys.stdout = sys.stderr = output
                co = compile (line, repr(self), 'eval')
                result = eval (co, env)
                if result is not None:
                    print repr(result)
                    env['_'] = result
            except SyntaxError:
                try:
                    co = compile (line, repr(self), 'exec')
                    exec co in env
                except SyntaxError, msg:
                    # this is a hack, but it is a righteous hack:
                    if not self.multilines and str(msg) == 'unexpected EOF while parsing':
                        self.multilines.append(line)
                    else:
                        traceback.print_exc()
                except:
                    traceback.print_exc()
            except:
                traceback.print_exc()
        finally:
            sys.stdout, sys.stderr = save
            self.send (output.getvalue())
            del output

    def shutdown(self):
        if not self.exit:
            self.exit = True
            self.socket.wake()


class BackDoorServer(coro.Thread):
    def init(self):
        self._exit = False
        self._s    = None

    def run(self, port=8023, ip=''):
        self._s = coro.make_socket(socket.AF_INET, socket.SOCK_STREAM)
        self._s.set_reuse_addr()
        self._s.bind((ip, port))
        self._s.listen(1024)

        port = self._s.getsockname()[1]
        self.info('Backdoor listening on port %d' % (port,))

        while not self._exit:
            try:
                conn, addr = self._s.accept()
            except coro.CoroutineSocketWake:
                continue

            client = BackDoorClient(args = (conn, addr))
            client.start()

        self.info('Backdoor exiting (children: %d)' % self.child_count())

        self._s.close()
        self._s = None

        for child in self.child_list():
            child.shutdown()

        self.child_wait()
        return None

    def shutdown(self):
        if self._exit:
            return None

        self._exit = True

        if self._s is not None:
            self._s.wake()
#
# extremely minimal test server
#
if __name__ == '__main__':
    server = BackDoorServer()
    server.start()
    coro.event_loop (30.0)
#
# end...

########NEW FILE########
__FILENAME__ = btree
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import bisect
import itertools
import operator


class BTreeNode(object):
    def shrink(self, path):
        parent = None
        if path:
            parent, parent_index = path.pop()

            # first, try to pass a value left
            if parent_index:
                left = parent.children[parent_index - 1]
                if len(left.values) < left.order:
                    parent.neighbor_pass_left(self, parent_index)
                    return

            # second, try to pass one right
            if parent_index + 1 < len(parent.children):
                right = parent.children[parent_index + 1]
                if len(right.values) < right.order:
                    parent.neighbor_pass_right(self, parent_index)
                    return

        # finally, split the current node, then shrink the parent if we must
        center = len(self.values) // 2
        median = self.values[center]

        # create a sibling node with the second half of our data
        args = [self.tree, self.values[center + 1:]]
        if self.BRANCH:
            args.append(self.children[center + 1:])
        sibling = type(self)(*args)

        # cut our data down to the first half
        self.values = self.values[:center]
        if self.BRANCH:
            self.children = self.children[:center + 1]

        if not parent:
            parent = self.tree.BRANCH_NODE(self.tree, [], [self])
            parent_index = 0
            self.tree._root = parent

        # pass the median element up to the parent
        parent.values.insert(parent_index, median)
        parent.children.insert(parent_index + 1, sibling)
        if len(parent.values) > parent.order:
            parent.shrink(path)

    def grow(self, path, count=1):
        parent, parent_index = path.pop()
        minimum = self.order // 2
        left, right = None, None

        # first try to borrow from the right sibling
        if parent_index + 1 < len(parent.children):
            right = parent.children[parent_index + 1]
            if len(right.values) - count >= minimum:
                parent.neighbor_pass_left(right, parent_index + 1, count)
                return

        # then try borrowing from the left sibling
        if parent_index:
            left = parent.children[parent_index - 1]
            if len(left.values) - count >= minimum:
                parent.neighbor_pass_right(left, parent_index - 1, count)
                return

        # see if we can borrow a few from both
        if count > 1 and left and right:
            lspares = len(left.values) - minimum
            rspares = len(right.values) - minimum
            if lspares + rspares >= count:
                # distribute the pulling evenly between the two neighbors
                even_remaining = lspares + rspares - count
                from_right = rspares - (even_remaining // 2)
                parent.neighbor_pass_right(left, parent_index - 1, from_left)
                parent.neighbor_pass_left(right, parent_index + 1, from_right)
                return

        # consolidate with a sibling -- try left first
        if left:
            left.values.append(parent.values.pop(parent_index - 1))
            left.values.extend(self.values)
            if self.BRANCH:
                left.children.extend(self.children)
            parent.children.pop(parent_index)
        else:
            self.values.append(parent.values.pop(parent_index))
            self.values.extend(right.values)
            if self.BRANCH:
                self.children.extend(right.children)
            parent.children.pop(parent_index + 1)

        if len(parent.values) < minimum:
            if path:
                # parent is not the root
                parent.grow(path)
            elif not parent.values:
                # parent is root and is now empty
                self.tree._root = left or self

    def __repr__(self):
        name = self.BRANCH and "BRANCH" or "LEAF"
        return "<%s %s>" % (name, ", ".join(map(str, self.values)))


class BTreeBranchNode(BTreeNode):
    BRANCH = True
    __slots__ = ["tree", "order", "values", "children"]

    def __init__(self, tree, values, children):
        self.tree = tree
        self.order = tree.order
        self.values = values
        self.children = children

    def neighbor_pass_right(self, child, child_index, count=1):
        separator_index = child_index
        target = self.children[child_index + 1]
        index = len(child.values) - count

        target.values[0:0] = (child.values[index + 1:] +
                [self.values[separator_index]])
        self.values[separator_index] = child.values[index]
        child.values[index:] = []

        if child.BRANCH:
            target.children[0:0] = child.children[-count:]
            child.children[-count:] = []

    def neighbor_pass_left(self, child, child_index, count=1):
        separator_index = child_index - 1
        target = self.children[child_index - 1]

        target.values.extend([self.values[separator_index]] +
                child.values[:count - 1])
        self.values[separator_index] = child.values[count - 1]
        child.values[:count] = []

        if child.BRANCH:
            index = len(child.values) + 1
            target.children.extend(child.children[:count])
            child.children[:count] = []

    def remove(self, index, path):
        minimum = self.order // 2

        # try replacing the to-be removed item from the right subtree first
        to_leaf = [(self, index + 1)]
        descendent = self.children[index + 1]
        while descendent.BRANCH:
            to_leaf.append((descendent, 0))
            descendent = descendent.children[0]
        if len(descendent.values) > minimum:
            path.extend(to_leaf)
            self.values[index] = descendent.values[0]
            descendent.remove(0, path)
            return

        # fall back to promoting from the left subtree
        to_leaf = [(self, index)]
        descendent = self.children[index]
        while descendent.BRANCH:
            to_leaf.append((descendent, len(descendent.children) - 1))
            descendent = descendent.children[-1]
        path.extend(to_leaf)
        self.values[index] = descendent.values[-1]
        descendent.remove(len(descendent.values) - 1, path)

    def split(self, value):
        index = bisect.bisect_right(self.values, value)
        child = self.children[index]

        left = type(self)(self.tree, self.values[:index], self.children[:index])

        self.values = self.values[index:]
        self.children = self.children[index + 1:]

        # right here both left and self has the same number of children as
        # values -- but the relevant child hasn't been split yet, so we'll add
        # the two resultant children to the respective child list

        left_child, right_child = child.split(value)
        left.children.append(left_child)
        self.children.insert(0, right_child)

        return left, self


class BTreeLeafNode(BTreeNode):
    BRANCH = False
    __slots__ = ["tree", "order", "values"]

    def __init__(self, tree, values):
        self.tree = tree
        self.order = tree.order
        self.values = values

    def remove(self, index, path):
        self.values.pop(index)
        if path and len(self.values) < self.order // 2:
            self.grow(path)

    def split(self, value):
        index = bisect.bisect_right(self.values, value)

        left = type(self)(self.tree, self.values[:index])

        self.values = self.values[index:]

        self.tree._first = self

        return left, self


class BTree(object):
    BRANCH_NODE = BTreeBranchNode
    LEAF_NODE = BTreeLeafNode

    def __init__(self, order):
        self.order = order
        self._root = self._first = self.LEAF_NODE(self, [])

    def __nonzero__(self):
        return bool(self._root.values)

    @property
    def first(self):
        if not self:
            return None
        return self._first.values[0]

    def insert(self, value, after=False):
        path = self.find_path_to_leaf(value, after)
        node, index = path.pop()

        node.values.insert(index, value)

        if len(node.values) > self.order:
            node.shrink(path)

    def remove(self, value, last=True):
        test = last and self._test_right or self._test_left
        path = self.find_path(value, last)
        node, index = path.pop()

        if test(node.values, index, value):
            if last:
                index -= 1
            node.remove(index, path)
        else:
            raise ValueError("%r not in %s" % (value, self.__class__.__name__))

    def __repr__(self):
        def recurse(node, accum, depth):
            accum.append(("  " * depth) + repr(node))
            if node.BRANCH:
                for child in node.children:
                    recurse(child, accum, depth + 1)

        accum = []
        recurse(self._root, accum, 0)
        return "\n".join(accum)

    def _test_right(self, values, index, value):
        return index and values[index - 1] == value

    def _test_left(self, values, index, value):
        return index < len(values) and values[index] == value

    def find_path(self, value, after=False):
        cut = after and bisect.bisect_right or bisect.bisect_left
        test = after and self._test_right or self._test_left

        path, node = [], self._root
        index = cut(node.values, value)
        path.append((node, index))

        while node.BRANCH and not test(node.values, index, value):
            node = node.children[index]
            index = cut(node.values, value)
            path.append((node, index))

        return path

    def find_path_to_leaf(self, value, after=False):
        cut = after and bisect.bisect_right or bisect.bisect_left

        path = self.find_path(value, after)
        node, index = path[-1]

        while node.BRANCH:
            node = node.children[index]
            index = cut(node.values, value)
            path.append((node, index))

        return path

    def _iter_recurse(self, node):
        if node.BRANCH:
            for child, value in itertools.izip(node.children, node.values):
                for ancestor_value in self._iter_recurse(child):
                    yield ancestor_value

                yield value

            for value in self._iter_recurse(node.children[-1]):
                yield value
        else:
            for value in node.values:
                yield value

    def __iter__(self):
        return self._iter_recurse(self._root)

    def pull_prefix(self, value):
        '''
        get and remove the prefix section of the btree up to and
        including all values for `value`, and return it as a list

        http://www.chiark.greenend.org.uk/~sgtatham/tweak/btree.html#S6.2
        '''
        left, right = self._root.split(value)

        # first eliminate redundant roots
        while self._root.BRANCH and not self._root.values:
            self._root = self._root.children[0]

        # next traverse down, rebalancing as we go
        if self._root.BRANCH:
            path = [(self._root, 0)]
            node = self._root.children[0]

            while node.BRANCH:
                short_by = (node.order // 2) - len(node.values)
                if short_by > 0:
                    node.grow(path[:], short_by + 1)
                path.append((node, 0))
                node = node.children[0]

            short_by = (node.order // 2) - len(node.values)
            if short_by > 0:
                node.grow(path[:], short_by + 1)

        throwaway = object.__new__(type(self))
        throwaway._root = left # just using you for your __iter__
        return iter(throwaway)

    @classmethod
    def bulkload(cls, values, order):
        tree = object.__new__(cls)
        tree.order = order

        minimum = order // 2
        valuegroups, separators = [[]], []

        for value in values:
            if len(valuegroups[-1]) < order:
                valuegroups[-1].append(value)
            else:
                separators.append(value)
                valuegroups.append([])

        if len(valuegroups[-1]) < minimum and separators:
            sep_value = separators.pop()
            last_two_values = valuegroups[-2] + [sep_value] + valuegroups[-1]
            valuegroups[-2] = last_two_values[:minimum]
            valuegroups[-1] = last_two_values[minimum + 1:]
            separators.append(last_two_values[minimum])

        last_generation = []
        for values in valuegroups:
            last_generation.append(cls.LEAF_NODE(tree, values))

        tree._first = last_generation[0]

        if not separators:
            tree._root = last_generation[0]
            return tree

        while len(separators) > order + 1:
            pairs, separators = separators, []
            last_values, values = values, [[]]

            for value in pairs:
                if len(values[-1]) < order:
                    values[-1].append(value)
                else:
                    separators.append(value)
                    values.append([])

            if len(values[-1]) < minimum and separators:
                sep_value = separators.pop()
                last_two_values = values[-2] + [sep_value] + values[-1]
                values[-2] = last_two_values[:minimum]
                values[-1] = last_two_values[minimum + 1:]
                separators.append(last_two_values[minimum])

            offset = 0
            for i, value_group in enumerate(values):
                children = last_generation[offset:offset + len(value_group) + 1]
                values[i] = cls.BRANCH_NODE(tree, value_group, children)
                offset += len(value_group) + 1

            last_generation = values

        root = cls.BRANCH_NODE(tree, separators, last_generation)

        tree._root = root
        return tree

########NEW FILE########
__FILENAME__ = cache
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''cache

various simple caches
'''

from gogreen import dqueue

DEFAULT_CACHE_SIZE = 1024

class CacheObject(dqueue.QueueObject):
    __slots__ = ['id', 'value']

    def __init__(self, *args, **kwargs):
        super(CacheObject, self).__init__(*args, **kwargs)

        self.id    = args[0]
        self.value = kwargs.get('value', None)

    def __repr__(self):
        return '<CacheObject %r: %r>' % (self.id, self.value)


class LRU(object):
    def __init__(self, *args, **kwargs):
        self._size = kwargs.get('size', DEFAULT_CACHE_SIZE)
        self._ordr = dqueue.ObjectQueue()
        self._objs = {}

    def __len__(self):
        return len(self._objs)

    def _balance(self):
        if len(self._objs) > self._size:
            obj = self._ordr.get_tail()
            del(self._objs[obj.id])

    def _lookup(self, id):
        obj = self._objs.get(id, None)
        if obj is not None:
            self._ordr.remove(obj)
            self._ordr.put_head(obj)

        return obj

    def _insert(self, obj):
        self._objs[obj.id] = obj
        self._ordr.put_head(obj)

        self._balance()

    def lookup(self, id):
        obj = self._lookup(id)
        if obj is None:
            return None
        else:
            return obj.value

    def insert(self, id, value):
        obj = self._lookup(id)
        if obj is None:
            obj = CacheObject(id)
            self._insert(obj)

        obj.value = value

    def reset(self, size = None):
        if size is not None:
            self._size = size

        self._ordr.clear()
        self._objs = {}

    def head(self):
        return self._ordr.look_head()

    def tail(self):
        return self._ordr.look_tail()
#
# end...


########NEW FILE########
__FILENAME__ = coro
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 1999, 2000 by eGroups, Inc.
# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import traceback
import os
import select
import string
import signal
import sys
import time
import logging
import errno
import weakref

import _socket
import socket
#
# The creation of the ssl object passed into coroutine_ssl relies on
# a _ssl module which correctly handles non-blocking connect. (as of
# python 2.4.1 the shipping _ssl.so does not correctly support this
# so a patched version is in this source tree.)
#
try:
    import green_ssl as __real_ssl__
except:
    __real_ssl__ = None

try:
    import _epoll
except:
    _epoll = None

try:
    signal.setitimer
    signal.ITIMER_PROF
    itimer = signal
except NameError:
    try:
        import itimer
    except:
        itimer = None

# sentinel value used by wait_for_read() and wait_for_write()
USE_DEFAULT_TIMEOUT = -1

# node size for the event_list btree
TIMED_BRANCHING_ORDER = 50

#
# poll masks.
DEFAULT_MASK = select.POLLIN|select.POLLOUT|select.POLLPRI
ERROR_MASK = select.POLLERR|select.POLLHUP|select.POLLNVAL

from errno import EALREADY, EINPROGRESS, EWOULDBLOCK, ECONNRESET, ENOTCONN
import exceptions
#
# import underlying coroutine module: greenlet.
#
try:
    from greenlet import greenlet
except ImportError:
    from py.magic import greenlet

import btree

#
# save real socket incase we emulate.
#
__real_socket__ = _socket.socket

class CoroutineSocketError (exceptions.Exception):
    pass

class CoroutineCondError (exceptions.Exception):
    pass

class CoroutineThreadError (exceptions.Exception):
    pass

class TimeoutError (exceptions.Exception):
    pass

class CoroutineSocketWake (exceptions.Exception):
    pass

class CoroutineCondWake (exceptions.Exception):
    pass

class ConnectionError(Exception):
    pass

class LockTimeout(exceptions.Exception):
    pass

# ===========================================================================
#                          Coroutine Socket
# ===========================================================================

class coroutine_socket(object):
    '''coroutine_socket

    socket that automatically suspends/resumes instead of blocking.
    '''
    def __init__ (self, *args, **kwargs):
        """Timeout semantics for __init__():
           If you do not pass in a keyword arg for timeout (or
           pass in a value of None), then the socket is blocking.
        """

        self.socket = kwargs.get('sock', args and args[0] or None)
        if self.socket:
            self.socket.setblocking(0)
            self.set_fileno()

        self.family = kwargs.get('family', socket.AF_UNSPEC)

        me = current_thread()
        if me is not None:
            default = me.get_socket_timeout()
        else:
            default = None

        if default is None:
            default = getdefaulttimeout()

        self._timeout         = kwargs.get('timeout', default)
        self._connect_timeout = kwargs.get('connect_timeout', default)

        self._wake   = []
        self._closed = 0
        #
        # coro poll threads waiting for sig.
        self._waits  = {None: 0}

    def set_fileno (self):
        self._fileno = self.socket.fileno()

    def fileno (self):
        return self._fileno

    def create_socket (self, family, type, proto = 0):
        if self.family != family:
            self.family = family
        self.socket = __real_socket__(family, type, proto)
        self.socket.setblocking(0)
        self.set_fileno()

    def _wait_add(self, mask):
        self._waits[current_thread()] = mask
        return reduce(lambda x, y: x|y, self._waits.values())

    def _wait_del(self):
        del(self._waits[current_thread()])
        return reduce(lambda x, y: x|y, self._waits.values())

    def _waiting(self):
        return filter(lambda y: y[0] is not None, self._waits.items())

    def wake(self, mask = 0xffff):
        for thrd, mask in filter(lambda y: y[1] & mask, self._waiting()):
            if thrd is current_thread():
                raise CoroutineThreadError, 'cannot wakeup current thread'

            schedule(thrd)

    def _wait_for_event(self, eventmask, timeout):
        """Timeout semantics:
           No timeout keyword arg given means that the default
           given to __init__() is used. A timeout of None means
           that we will act as a blocking socket."""

        if timeout == USE_DEFAULT_TIMEOUT:
            timeout = self._timeout

        me = current_thread()
        if me is None:
            raise CoroutineSocketError, "coroutine sockets in 'main'"

        the_event_poll.register(self, eventmask)
        result = me.Yield(timeout, 0)
        the_event_poll.unregister(self)

        if result is None:
            raise CoroutineSocketWake, 'socket has been awakened'

        if result == 0:
            raise TimeoutError, "request timed out in recv (%s secs)" % timeout

        if 0 < (result & eventmask):
            return None

        if 0 < (result & ERROR_MASK):
            raise socket.error(socket.EBADF, 'Bad file descriptor')
        #
        # all cases should have been handled by this point
        return None

    def wait_for_read (self, timeout = USE_DEFAULT_TIMEOUT):
        return self._wait_for_event(select.POLLIN, timeout)

    def wait_for_write (self, timeout = USE_DEFAULT_TIMEOUT):
        return self._wait_for_event(select.POLLOUT, timeout)

    def connect (self, address):
        try:
            if socket.AF_INET == self.family:
                host, port = address
                #
                # Perform DNS resolution here so it will use our,
                # coroified resolver instead of the DNS code
                # baked into Python, which uses native sockets.
                #
                host = socket.gethostbyname(host)
                address = (host, port)

            return self.socket.connect(address)
        except socket.error, why:
            if why[0] in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                pass
            elif why[0] == errno.EALREADY:
                return
            else:
                raise socket.error, why
        #
        # When connect gets a EINPROGRESS/EWOULDBLOCK exception, we wait
        # until the socket has completed the connection (ready for write)
        # Coroutine yields are done outside of the exception handler, to
        # avoid tracebacks leaking into other coroutines.
        #
        self.wait_for_write(timeout = self._connect_timeout)
        ret = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if ret != 0:
            raise socket.error, (ret, os.strerror(ret))

    def recv (self, buffer_size):
        self.wait_for_read()
        return self.socket.recv(buffer_size)

    def recvfrom (self, buffer_size):
        self.wait_for_read()
        return self.socket.recvfrom (buffer_size)

    def recv_into (self, buffer, buffer_size):
        self.wait_for_read()
        return self.socket.recv_into (buffer, buffer_size)

    def recvfrom_into (self, buffer, buffer_size):
        self.wait_for_read()
        return self.socket.recvfrom_into (buffer, buffer_size)

    # Things we try to avoid:
    #   1) continually slicing a huge string into slightly smaller pieces
    #     [e.g., 1MB, 1MB-8KB, 1MB-16KB, ...]
    #   2) forcing the kernel to copy huge strings for the syscall
    #
    # So, we try to send reasonably-sized slices of a large string.
    # If we were really smart we might try to adapt the amount we try to send
    # based on how much got through the last time.

    _max_send_block = 64 * 1024

    def send (self, data):
        self.wait_for_write()
        return self.socket.send(data)

    def sendall(self, data):
        t = 0
        while data:
            self.wait_for_write()
            n = self.socket.send(data[:min(len(data), self._max_send_block)])
            data = data[n:]
            t = t + n
        return t

    def sendto (self, data, where):
        self.wait_for_write()
        return self.socket.sendto (data, where)

    def bind (self, address):
        return self.socket.bind (address)

    def listen (self, queue_length):
        return self.socket.listen (queue_length)

    def accept (self):
        while 1:
            try:
                self.wait_for_read()
            except TimeoutError, e:
                raise socket.timeout, 'timed out'

            try:
                conn, addr = self.socket.accept()
                return self.__class__ (conn), addr
            except socket.error, e:
                if e[0] not in (errno.EAGAIN, errno.EWOULDBLOCK):
                    raise

    def close (self):
        if not self._closed:
            self._closed = 1
            if self.socket:
                return self.socket.close()
            else:
                return None

    def shutdown(self, *args):
        return self.socket.shutdown(*args)

    def __del__ (self):
        self.close()

    def set_reuse_addr (self):
        # try to re-use a server port if possible
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except:
            pass

    def settimeout(self, o):
        self._connect_timeout = o
        self._timeout         = o

    def gettimeout(self):
        return self._timeout

    def makefile(self, mode='r', bufsize=-1):
        return socket._fileobject(self, mode, bufsize)

    def setsockopt(self, level, option, value):
        return self.socket.setsockopt(level, option, value)

    def getsockopt(self, level, option):
        return self.socket.getsockopt(level, option)

    def getsockname(self):
        return self.socket.getsockname()

    def setblocking(self, val):
        # the socket is always in non-blocking mode, though it will block a
        # coroutine. lie here, since most code out there that does
        # setblocking(0) doesn't need it as it uses select/poll/epoll regardless
        return None



SSL_WAIT_ERRORS = set([
    socket._ssl.SSL_ERROR_WANT_READ,
    socket._ssl.SSL_ERROR_WANT_WRITE,
    socket._ssl.SSL_ERROR_WANT_CONNECT,
])

class coroutine_ssl(object):
    def __init__(self, socket, ssl):
        self._socket = socket
        self._ssl = ssl

    def read(self, size):
        data = ''
        error = 0
        while size:
            #
            # Yield on initial entry (no error set) to prevent non-yielding
            # read loops using small increments to fetch large amounts of
            # data. Error set to want write or connect is a wait for file
            # descriptor write ready.
            #
            if not error:
                current_thread().Yield(0.0)
            elif error == socket._ssl.SSL_ERROR_WANT_READ:
                self._socket._sock.wait_for_read()
            else:
                self._socket._sock.wait_for_write()

            try:
                partial = self._ssl.read(size)
            except (socket.error, socket.sslerror), exception:
                error = exception[0]

                if error in SSL_WAIT_ERRORS:
                    continue
                elif data:
                    break
                else:
                    raise

            if not partial:
                break

            error = 0
            size -= len(partial)
            data += partial

        return data

    def write(self, data):
        error = 0
        sent = 0
        while data:
            #
            # see read
            #
            if not error:
                current_thread().Yield(0.0)
            elif error == socket._ssl.SSL_ERROR_WANT_READ:
                self._socket._sock.wait_for_read()
            else:
                self._socket._sock.wait_for_write()

            try:
                size = self._ssl.write(data)
                sent += size
            except (socket.error, socket.sslerror), exception:
                error = exception[0]

                if error in SSL_WAIT_ERRORS:
                    continue
                elif sent:
                    break
                else:
                    raise

            error = 0
            data  = data[size:]

        return sent

    def issuer(self):
        return self._ssl.issuer()

    def server(self):
        return self._ssl.server()

# ===========================================================================
#                         Condition Variable
# ===========================================================================

class coroutine_cond(object):
    __slots__ = ['_waiting', '_ordered', '_counter']

    def __init__ (self):
        self._waiting = {}
        self._ordered = []
        self._counter = 0

    def __len__(self):
        return self._counter

    def wait (self, timeout = None):
        thrd = current_thread()
        tid  = thrd.thread_id()

        self._counter += 1
        self._waiting[tid] = thrd
        self._ordered.append(tid)

        result = thrd.Yield(timeout)
        #
        # If we have passed to here, we are not waiting any more.
        # depending how we were awoken, we may need to remove the
        # thread reference
        #
        if self._waiting.has_key(tid):
            del self._waiting[tid]
            self._ordered.remove(tid)

        self._counter -= 1
        return result

    def wake (self, id, *args):
        thrd = self._waiting.pop(id, None)
        if thrd is None:
            raise CoroutineCondError, 'unknown thread <%d>' % (id)

        self._ordered.remove(id)
        schedule (thrd, args)

    def wake_one (self, *args):
        if not len(self._waiting):
            return None

        thid = self._ordered.pop(0)
        thrd = self._waiting.pop(thid)

        schedule(thrd, args)

    def wake_all (self, *args):
        for thrd in self._waiting.values():
            schedule (thrd, args)

        self._waiting = {}
        self._ordered = []

class stats_cond(coroutine_cond):
    def __init__ (self, timeout = None):
        super(self.__class__, self).__init__()
        self.waiting     = {}
        self.total_waits = 0
        self.total_time  = 0.0
        self.timeouts    = 0
        self.timeout     = timeout

    def wait (self, timeout = None):
        tid = current_thread().thread_id()
        self.waiting[tid] = time.time()

        if timeout is None:
                timeout = self.timeout

        result = super(self.__class__, self).wait(timeout)
        if result is None:
            self.timeouts += 1

        self.total_waits += 1
        self.total_time  += time.time() - self.waiting[tid]

        del self.waiting[tid]
        return result

    def stats(self):
        result = {
            'waiting': self.waiting.values(),
            'timeouts': self.timeouts,
            'total': self.total_time,
            'waits': self.total_waits }

        result['waiting'].sort()

        if self.total_time:
            result.update({'average': self.total_time/self.total_waits })
        else:
            result.update({'average': 0})

        return result;

class coroutine_lock(object):
    __slots__ = ['_cond', '_lock']

    def __init__(self):
        self._cond = coroutine_cond()
        self._lock = 0

    def __len__(self):
        return len(self._cond)

    def lock(self, timeout = None):
        while self._lock:
            result = self._cond.wait(timeout)
            if result is None:
                raise LockTimeout('lock timeout', timeout)

        self._lock = 1

    def tset(self):
        locked, self._lock = bool(self._lock), 1
        return not locked

    def unlock(self):
        self._lock = 0
        self._cond.wake_one()

    def locked(self):
        return bool(self._lock)

    def mucked(self):
        return bool(self._lock or len(self._cond))


class coroutine_fifo(object):
    def __init__(self, timeout = None):
        self._cond = coroutine_cond()
        self._timeout = timeout
        self._fifo = []

    def __len__(self):
        return len(self._fifo)

    def waiters(self):
        return len(self._cond)

    def push(self, o):
        self._fifo.append(o)
        self._cond.wake_one(None)

    def pop(self, **kwargs):
        timeout = kwargs.get('timeout', self._timeout)

        while not len(self._fifo):
            result = self._cond.wait(timeout = timeout)
            if result is None:
                raise TimeoutError
            elif not result:
                raise CoroutineCondWake

        return self._fifo.pop(0)

    def wake(self):
        self._cond.wake_all()

# ===========================================================================
#                Coro-aware Logging and Standard IO replacements
# ===========================================================================
class coroutine_logger(logging.Logger):
    def makeRecord(self, *args):
        args = args[:7]
        rv = logging.LogRecord(*args)
        rv.__dict__.update({'coro':current_id()})
        return rv

class coroutine_stdio(object):
    def __init__(self):
        self._partial = {}

    def write(self, str):
        value = string.split(str, '\n')
        id    = current_id()

        self._partial[id] = self._partial.get(id, '') + value[0]
        value = value[1:]

        if not value:
            return

        self._output(self._prefix + self._partial[id])
        for line in value[:-1]:
            self._output(self._prefix + line)

        self._partial[id] = value[-1]
        return

    def flush(self):
        pass

class coroutine_stdout(coroutine_stdio):
    def __init__(self, log):
        super(self.__class__,self).__init__()
        self._output = log.info
        self._prefix = '>> '

class coroutine_stderr(coroutine_stdio):
    def __init__(self, log):
        super(self.__class__,self).__init__()
        self._output = log.error
        self._prefix = '!> '


# ===========================================================================
#                     Thread Abstraction
# ===========================================================================

def get_callstack(depth = 2):
    data  = []

    while depth is not None:
        try:
            f = sys._getframe(depth)
        except:
            depth = None
        else:
            data.append((
                '/'.join(f.f_code.co_filename.split('/')[-2:]),
                f.f_code.co_name,
                f.f_lineno))
            depth += 1

    return data

def preemptive_locked():
    '''preemptive_locked

    Decorator for functions which need to execute w/ preemption disabled.
    '''
    def function(method):
        def disabled(obj, *args, **kwargs):
            obj.preemptable_disable()
            try:
                return method(obj, *args, **kwargs)
            finally:
                obj.preemptable_enable()

        return disabled
    return function


_current_threads = {}
_current_threads_by_id = {}

def _register_thread(thread):
    _current_threads[thread._co] = thread
    _current_threads_by_id[thread.thread_id()] = thread

def _unregister_thread(thread):
    _current_threads.pop(thread._co)
    _current_threads_by_id.pop(thread.thread_id())


class Thread(object):
    _thread_count = 0

    def __init__(self, *args, **kwargs):
        self._thread_id = Thread._thread_count = Thread._thread_count + 1

        if not kwargs.has_key('name'):
            self._name = 'thread_%d' % self._thread_id
        else:
            self._name = kwargs['name']

        self._target = kwargs.get('target', None)
        self._args   = kwargs.get('args', ())
        self._kwargs = kwargs.get('kwargs', {})
        #
        # statistics when profiling
        #
        self._resume_count = 0
        self._total_time   = 0
        self._long_time    = 0

        self._alive = 0
        self._started = 0
        self._profile = 0
        self._daemonic = 0
        self._deadman = None
        self._joinees = None
        self._locald  = {}
        #
        # preemptive scheduler info
        #
        self._preempted   = 0
        self._preemptable = [1, 0]
        #
        # debug info
        #
        self._trace = 0
        self._where = None
        #
        # child management
        #
        self._children = {}
        self._cwaiter  = coroutine_cond()
        ## dp 8/16/05
        ## self._co = coroutine.new (self._run, 65536)
        self._co = greenlet(self._run)

        self._status = 'initialized'
        #
        # inherit some properties from a parent thread
        #
        parent = current_thread()
        if parent:
            self._log      = kwargs.get('log', parent._log)
            self._loglevel = parent._loglevel
            self._profile  = parent._profile

            def dropped(ref):
                self._parent = None

            self._parent = weakref.ref(parent)
        else:
            self._log      = kwargs.get('log', None)
            self._loglevel = logging.DEBUG
            self._parent   = None
        #
        # call user specified initialization function
        #
        self.init()

    def __del__ (self):
        if self._alive:
            self.kill()

    def __repr__ (self):
        if self._profile:
            p = ' resume_count: %d execute_time: %s' % (
                self._resume_count,
                self._total_time)
        else:
            p = ''
        if self._alive:
            a = 'running'
        else:
            a = 'suspended'

        return '<%s.%s id:%d %s %s%s at %x>' % (
            __name__,
            self.__class__.__name__,
            self._thread_id,
            self._status,
            a,
            p,
            id(self))
    #
    # subclass overrides
    #
    def init(self):
        'user defined initialization call'
        pass

    def complete(self):
        'user defined cleanup call on completion'
        pass

    def run (self):
        sys.stderr.write('Unregistered run method!\n')
    #
    # intra-thread management
    #
    def child_join(self, child):
        '''child_join

        children register with their parent at initialization time
        '''
        tid = child.thread_id()
        self._children[tid] = tid

    def child_drop(self, child):
        '''child_drop

        children unregister from their parent when they are destroyed
        '''
        o = self._children.pop(child.thread_id(), None)
        if o is not None:
            self._cwaiter.wake_all()

    def child_list(self):
        return map(lambda t: _get_thread(t), self._children.keys())

    def child_wait(self, timeout = None, exclude = set(), children = None):
        if children is None:
            children = set(self._children.keys()) - exclude
        else:
            children = set(map(lambda i: i.thread_id(), children)) - exclude
            
        error = children - set(self._children.keys())
        if error:
            raise ValueError('Cannot wait for strangers', error)

        while children:
            start  = time.time()
            result = self._cwaiter.wait(timeout)
            if result is None:
                break

            if timeout is not None:
                timeout -= time.time() - start

            children.intersection_update(set(self._children.keys()))

        return len(children)

    def child_count(self):
        return len(self._children)

    def parent(self):
        if self._parent is not None:
            return self._parent()
        else:
            return None

    def abandon(self):
        for tid in self._children.values():
            child = _get_thread(tid)
            if child is not None:
                child._parent = None

        self._children = {}
        self._cwaiter.wake_all()

    def start (self):
        if not self._started:
            self._started = 1
            schedule(self)

    def resume (self, args):
        if not hasattr(self, '_co'):
            return

        self._co.parent = MAIN_EVENT_LOOP
        #
        # clear preemption data on resume not on completion.
        #
        self._preempted = 0

        if self._profile:
            self._resume_count = self._resume_count + 1
            start_time = time.time()
        else:
            start_time = 0

        try:
            if self._alive:
                # This first one will create a self-referenced tuple,
                # which causes a core dump. The second does not.
                # Extremely weird.
                # result = coroutine.resume (self._co, (args,))
                # dp 8/16/05
                # newargs = (args,)
                # coroutine.resume (self._co, newargs)
                result = self._co.switch(args)
            else:
                result = self._co.switch()
        except greenlet.GreenletExit:
            self.kill()

        if self._profile and start_time:
            exec_time = time.time() - start_time

            self._total_time += exec_time
            self._long_time   = max(self._long_time, exec_time)

        return result

    def _run (self):
        try:
            self._alive   = 1
            self._status  = 'alive'
            self._joinees = []
            _register_thread(self)

            parent = self.parent()
            if parent is not None:
                parent.child_join(self)

            if self._target is None:
                result = apply (self.run, self._args, self._kwargs)
            else:
                result = apply (self._target, self._args, self._kwargs)
        except greenlet.GreenletExit:
            pass
        except:
            self.traceback()

        self.kill()

    def kill (self):
        if not self._alive:
            return

        self.complete()
        self.abandon()

        parent = self.parent()
        if parent is not None:
            parent.child_drop(self)

        if self._joinees is not None:
            for waiter in self._joinees:
                waiter.wake_all()

            self._joinees = None

        _unregister_thread(self)

        self._alive  = 0
        self._status = 'dead'
        self._locald.clear()
        del(self._co)
    #
    # logging.
    #
    def set_log_level(self, level):
        self._loglevel = level
    def get_log_level(self):
        return self._loglevel
    def log(self, level, msg, *args):
        if not level < self._loglevel:
            if self._log:
                self._log.log(level, args and msg % args or msg)
            else:
                sys.stderr.write(
                    'LOGLEVEL %02d: %s\n' % (level, args and msg % args or msg))
    def debug(self, msg, *args):
        self.log(logging.DEBUG, msg, *args)
    def info(self, msg, *args):
        self.log(logging.INFO, msg, *args)
    def warn(self, msg, *args):
        self.log(logging.WARN, msg, *args)
    def error(self, msg, *args):
        self.log(logging.ERROR, msg, *args)
    def critical(self, msg, *args):
        self.log(logging.CRITICAL, msg, *args)
    def traceback(self, level = logging.ERROR):
        t,v,tb = sys.exc_info()
        self.log(level, 'Traceback: [%s|%s]' % (str(t),str(v)))
        while tb:
            self.log(level, '  %s (%s:%s)' % (
                tb.tb_frame.f_code.co_filename,
                tb.tb_frame.f_code.co_name,
                str(tb.tb_lineno)))
            tb = tb.tb_next
        del(tb)
    #
    # thread local storage
    #
    def get_local(self, key, default = None):
        return self._locald.get(key, default)

    def pop_local(self, key, default = None):
        return self._locald.pop(key, default)

    def set_local(self, key, value):
        self._locald[key] = value

    def has_local(self, key):
        return self._locald.has_key(key)

    def set_locals(self, **kwargs):
        self._locald.update(kwargs)

    #
    #
    #
    @preemptive_locked()
    def Yield(self, timeout = None, arg = None):
        #
        # add self to timeout event list
        #
        if timeout is not None:
            triple = the_event_list.insert_event(self, timeout, arg)
        #
        # in debug mode record stack
        #
        if self._trace:
            self._where = get_callstack()
        #
        # release control
        #
        result = MAIN_EVENT_LOOP.switch()  ##coroutine.main(())
        #
        # remove self from timeout event list.
        #
        if timeout is not None:
            the_event_list.remove_event(triple)

        return result

    @preemptive_locked()
    def preempt(self, limit = 0, level = 1):
        if not self._preempted > max(limit, 1):
            return None

        self.Yield(0.0)

        if not level:
            return None
        #
        # debug output.
        #
        frame = sys._getframe(3)

        level -= 1
        if not level:
            self.info('Preempted:   %s  (%s:%d)' % (
                '/'.join(frame.f_code.co_filename.split('/')[-2:]),
                frame.f_code.co_name,
                frame.f_lineno))
            return None

        level -= 1
        if not level:
            self.info('Preempted:   %s' % (
                '|'.join(map(
                    lambda i: '%s:%s()' % (i[0],i[1]),
                    get_callstack(3)[:-2]))))
            return None

        self.info('Preempted:', pre)
        for data in get_callstack(3):
            thrd.info('    %s  (%s:%d)' % data)

        return None

    def join(self, timeout = None):
        '''join

        Wait, no longer then timeout, until this thread exits.

        results:
          True  - successfully joined
          False - join failed due to timeout
          None  - join failed because coroutine is not joinable.
        '''
        waiter = coroutine_cond()
        if self._joinees is not None:
            self._joinees.append(waiter)
            result = waiter.wait(timeout)
            result = ((result is None and [False]) or [True])[0]
        else:
            result = None

        return result
    #
    # basic thread info
    #
    def profile(self, status, children = False):
        '''profile

        Enable/Disable the collection of the context switch counter and
        the execution time counter. Optionally cascade to child threads
        '''
        self._profile = status

        if not children:
            return None

        for child in self.child_list():
            child.profile(status, children = children)

    def profile_clear(self, children = False):
        '''profile_clear

        Reset the threads context switch counter and the execution time
        counters.
        '''
        self._resume_count = 0
        self._total_time   = 0
        self._long_time    = 0

        if not children:
            return None

        for child in self.child_list():
            child.clear(children = children)

    def clear(self):
        return self.profile_clear() # backwards code compat.

    def resume_count(self):
        '''resume_count

        Return the value of the context switch counter
        '''
        return self._profile and self._resume_count or None

    def total_time(self):
        '''total_time

        Return the value of the execution time counter values.
        '''
        return self._profile and self._total_time or None

    def long_time(self):
        '''long_time

        Return the time value of the longest executing section.
        '''
        return self._profile and self._long_time or None

    def trace(self, status):
        '''trace

        Enable/Disable the recording of the threads execution stack during
        the most recent context switch.
        '''
        #
        # to allow orthogonal components to enable/disable trace, the
        # variable is implemented as a counter.
        #
        self._trace += (-1,1)[int(bool(status))]
        self._trace  = max(self._trace, 0)

    def where(self):
        '''where

        Return the execution stack of the thread at the time of the thread's
        last context switch.
        '''
        return self._where

    def thread_id (self):
        return self._thread_id

    def getName (self):
        return self._name

    def setName (self, name):
        self._name = name

    def isAlive (self):
        return self._alive

    def isDaemon (self):
        return self._daemonic

    def setDaemon (self, daemonic):
        self._daemonic = daemonic

    def status (self):
        print 'Thread status:'
        print ' id:          ', self._thread_id
        print ' alive:       ', self._alive
        if self._profile:
            print ' resume count:', self._resume_count
            print ' execute time:', self._total_time

    def set_socket_timeout(self, value):
        '''set_socket_timeout

        set a timer that no socket wait will exceed. This ensures that
        emulated sockets which use no timeout will not sleep indefinetly.
        '''
        self._deadman = value

    def get_socket_timeout(self):
        return self._deadman
    #
    # preemption support
    #
    def preemptable_disable(self):
        '''preemptable_disable

        Disable any preemption of this thread, regardless of other
        preemption settings. Primary usage is critical sections of
        lock code where atomicity needs to be guaranteed.

        See Also: preemptable_enable(), preemptable()
        '''
        self._preemptable[0] -= 1

    def preemptable_enable(self):
        '''preemptable_enable

        Disable any preemption of this thread, regardless of other
        preemption settings. Primary usage is critical sections of
        lock code where atomicity needs to be guaranteed.

        See Also: preemptable_disable(), preemptable()
        '''
        self._preemptable[0] += 1

    def preemptable_set(self, status):
        '''preemptable_set

        Set the thread level preemption enable/disable advisory. Multiple
        calls to enable (or disable) are cumulative. (i.e. the same
        number of disable (or enable) calls need to be made to reverse
        the action.)

        For example; Two enable calls followed by a single disable call
        will leave the thread in a state where the system is advised
        that preemption is allowed.

        See Also: preemptable_get(), preemptable()
        '''
        self._preemptable[1] += [-1, 1][int(bool(status))]

    def preemptable_get(self):
        '''preemptable_get

        Get the thread level  preemption enable/disable advisory.

        See Also: preemptable_set(), preemptable()
        '''
        return self._preemptable[1] > 0

    def preemptable(self):
        '''preemptable

        Return the preemptability state of the thread. Takes into account
        the advisory as well as the hard setting.

        NOTE: System level preemption needs to be enabled for this to
              have any meaningful effect.

        See Also: coro.preemptive_enable(), coro.preemptive_disable()
                  preemptable_enable(), preemptable_disable(),
                  preemptable_set(), preemptable_get()
        '''
        return bool(self._preemptable[1] > 0 and self._preemptable[0])
#
# end class Thread
#
def traceback_info():
    t,v,tb = sys.exc_info()
    tbinfo = []

    while tb:
        tbinfo.append((
            tb.tb_frame.f_code.co_filename,
            tb.tb_frame.f_code.co_name,
            str(tb.tb_lineno)
            ))
        tb = tb.tb_next
    del tb
    return (str(t), str(v), tbinfo)

def compact_traceback ():
    t,v,tb = traceback_info()

    if tb:
        file, function, line = tb[-1]
        info  = '['
        info += string.join(map(lambda x: string.join (x, '|'), tb), '] [')
        info += ']'
    else:
        file, function, line = ('','','')
        info = 'no traceback!'

    return (file, function, line), t, v, info
#
# ===========================================================================
#                   global state and threadish API
# ===========================================================================

default_timeout = None
# coroutines that are ready to run
pending = {}

def setdefaulttimeout(timeout):
    global default_timeout
    default_timeout = timeout

def getdefaulttimeout():
    global default_timeout
    return default_timeout

def make_socket (family, type, **kwargs):
    s = apply(coroutine_socket, (), kwargs)
    s.create_socket(family, type)
    return s

def new (function, *args, **kwargs):
    return Thread (target=function, args=args, kwargs=kwargs)

def new_socket(family, type, proto = 0):
    return coroutine_socket(sock = __real_socket__(family, type, proto))

def new_ssl(sock, keyfile=None, certfile=None):
    if not __real_ssl__:
        raise RuntimeError("the green_ssl extension is required")
    return coroutine_ssl(
        sock, __real_ssl__.ssl(sock._sock.socket, keyfile, certfile))

_emulate_list = [
    ('socket', '_realsocket'),
    ('socket', 'setdefaulttimeout'),
    ('socket', 'getdefaulttimeout'),
    ('socket', 'ssl'),
    ('socket', 'sslerror'),
]
_original_emulate = {}
def socket_emulate():

    # save _emulate_list
    for module, attr in _emulate_list:
        _original_emulate.setdefault(
            (module, attr),
            getattr(sys.modules[module], attr, None))

    socket._realsocket = new_socket
    socket.setdefaulttimeout = setdefaulttimeout
    socket.getdefaulttimeout = getdefaulttimeout
    socket.ssl = new_ssl
    if __real_ssl__:
        socket.sslerror = __real_ssl__.sslerror

def socket_reverse():
    for module, attr in _emulate_list:
        if _original_emulate.get((module, attr)):
            setattr(sys.modules[module], attr, _original_emulate[(module, attr)])

def real_socket(family, type, proto = 0):
    # return the real python socket, can be useful when in emulation mode.
    return __real_socket__(family, type, proto)

def spawn (function, *args, **kwargs):
    t = Thread (target=function, args=args, kwargs=kwargs)
    t.start()
    return t

def schedule (coroutine, args=None):
    "schedule a coroutine to run"
    pending[coroutine] = args

def Yield(timeout = None):
    return current_thread().Yield(timeout)

def sleep(timeout):
    return current_thread().Yield(timeout)

def thread_list():
    return _current_threads.values()

def _get_thread(id):
    return _current_threads_by_id.get(id, None)

def gt(tid = 1):
    return _get_thread(tid)

def current_thread(default = None):
    co = greenlet.getcurrent()
    return _current_threads.get (co, default)

def current_id():
    co = greenlet.getcurrent()
    thrd = _current_threads.get (co, None)
    if thrd is None:
            return -1
    else:
            return thrd.thread_id()

current = current_thread

def insert_thread(thrd):
    thrd.start()

def profile_start():
    return len([thrd.profile(True) for thrd in thread_list()])

def profile_stop():
    return len([thrd.profile(False) for thrd in thread_list()])

def profile_clear():
    return len([thrd.clear() for thrd in thread_list()])

def trace_start():
    return len([thrd.trace(True) for thrd in thread_list()])

def trace_stop():
    return len([thrd.trace(False) for thrd in thread_list()])

def trace_dump():
    return [(thrd.thread_id(), thrd._where) for thrd in thread_list()]
#
# thread local storage
#
class DefaultLocalStorage(object):
    def __init__(self):
        self._locald = {}

    def get_local(self, key, default = None):
        return self._locald.get(key, default)

    def pop_local(self, key, default = None):
        return self._locald.pop(key, default)

    def set_local(self, key, value):
        self._locald[key] = value

    def set_locals(self, **kwargs):
        self._locald.update(kwargs)

    def has_local(self, key):
        return self._locald.has_key(key)

default_local_storage = DefaultLocalStorage()

def get_local(key, default = None):
    return current_thread(default_local_storage).get_local(key, default)

def pop_local(key, default = None):
    return current_thread(default_local_storage).pop_local(key, default)

def set_local(key, value):
    return current_thread(default_local_storage).set_local(key, value)

def has_local(key):
    return current_thread(default_local_storage).has_local(key)

def set_locals(**kwargs):
    return current_thread(default_local_storage).set_locals(**kwargs)

def preemptable_disable():
    if not current_thread():
        return
    return current_thread().preemptable_disable()

def preemptable_enable():
    if not current_thread():
        return
    return current_thread().preemptable_enable()
#
# execute current pending coroutines. (run loop)
#
def run_pending():
    "run all pending coroutines"
    while len(pending):
        try:
            # some of these will kick off others, thus the loop
            c,v = pending.popitem()
            c.resume(v)
        except:
            # XXX can we throw the exception to the coroutine?
            traceback.print_exc()

class LoggingProxy(object):
    def log(self, level, msg, *args):
        if not current_thread():
            return sys.stderr.write(
                'LOGLEVEL %02d: %s\n' % (level, args and msg % args or msg))
        return current_thread().log(level, msg, *args)
    def debug(self, msg, *args):
        return self.log(logging.DEBUG, msg, *args)
    def info(self, msg, *args):
        return self.log(logging.INFO, msg, *args)
    def warn(self, msg, *args):
        return self.log(logging.WARN, msg, *args)
    def error(self, msg, *args):
        return self.log(logging.ERROR, msg, *args)
    def critical(self, msg, *args):
        return self.log(logging.CRITICAL, msg, *args)
    def traceback(self, level = logging.ERROR):
        if not current_thread():
            t,v,tb = sys.exc_info()
            self.log(level, 'Traceback: [%s|%s]' % (str(t),str(v)))
            while tb:
                self.log(level, '  %s (%s:%s)' % (
                    tb.tb_frame.f_code.co_filename,
                    tb.tb_frame.f_code.co_name,
                    str(tb.tb_lineno)))
                tb = tb.tb_next
            del(tb)
            return
        return current_thread().traceback()

log = LoggingProxy()
#
#
# optional preemptive handler
#
the_preemptive_rate    = None
the_preemptive_count   = 2
the_preemptive_info    = 1

def preemptive_signal_handler(signum, frame):
    try:
        global the_preemptive_rate
        if the_preemptive_rate is None:
            return None

        thrd = current_thread()
        if thrd is None:
            return None

        thrd._preempted += 1

        if not thrd.preemptable():
            return None

        global the_preemptive_info
        global the_preemptive_count

        thrd.preempt(limit = the_preemptive_count, level = the_preemptive_info)
    except Exception, e:
        log.traceback()

def preemptive_enable(frequency = 50):
    global the_preemptive_rate

    if not itimer:
        raise RuntimeError("the 'itimer' extension is required for preempting")

    if the_preemptive_rate is None:
        signal.signal(signal.SIGPROF, preemptive_signal_handler)

    the_preemptive_rate = 1.0/frequency

    itimer.setitimer(
        itimer.ITIMER_PROF,
        the_preemptive_rate,
        the_preemptive_rate)

def preemptive_disable():
    global the_preemptive_rate

    if not itimer:
        return

    the_preemptive_rate = None

    itimer.setitimer(itimer.ITIMER_PROF, 0, 0)
    signal.signal(signal.SIGPROF, signal.SIG_IGN)


_MAX = type('max', (), {'__cmp__': lambda self, x: 1})()


class event_list(object):
    def __init__(self):
        self.timed = btree.BTree(TIMED_BRANCHING_ORDER)
        self.zero_timeout = set()

    def __nonzero__(self):
        return bool(self.zero_timeout or self.timed)

    def insert_event(self, co, timeout, args):
        now = time.time()
        if isinstance(timeout, (int, long)):
            now = int(now)
        triple = (timeout + now, co, args)
        if timeout:
            self.timed.insert(triple)
        else:
            self.zero_timeout.add((co, args))
        return triple

    def remove_event(self, triple):
        if triple[0]:
            try:
                self.timed.remove(triple)
            except ValueError:
                pass
        else:
            self.zero_timeout.discard((triple[1], triple[2]))

    def run_scheduled(self):
        now = time.time()
        for triple in self.timed.pull_prefix((now, _MAX)):
            schedule(triple[1], triple[2])

        for thread, args in self.zero_timeout:
            schedule(thread, args)
        self.zero_timeout.clear()

    def next_event(self, max_timeout=30.0):
        if self.zero_timeout:
            return 0
        if not self.timed:
            return max_timeout
        return self.timed.first[0] - time.time()

class _event_poll(object):
    def __init__(self):
        self._info = {}

    def __nonzero__ (self):
        return len(self._info)

    def __len__(self):
        return len(self._info)

    def register(self, s, eventmask = DEFAULT_MASK):

        eventmask = s._wait_add(eventmask)
        self._info[s.fileno()] = (s, eventmask)

        self.ctl_add(s, eventmask)

    def unregister(self, s):

        eventmask = s._wait_del()
        if eventmask:
            self.ctl_mod(s, eventmask)
            self._info[s.fileno()] = (s, eventmask)
        else:
            self.ctl_del(s)
            del(self._info[s.fileno()])

    def poll(self, timeout = None):
        try:
            presult = self.wait(timeout)
        except (select.error, IOError), e:
            presult = []
            if e.args[0] != errno.EINTR: # Interrupted system call
                raise select.error, e

        cresult = []
        for fd, out_event in presult:
            s, tmp_event = self._info[fd]
            for thrd, in_event in s._waiting():
                if out_event & in_event or out_event & ERROR_MASK:
                    cresult.append((s, thrd, in_event, out_event))

        return cresult

class event_poll(_event_poll):
    def __init__(self):
        super(event_poll, self).__init__()
        self._poll = select.poll()

    def ctl_add(self, fd, mask):
        self._poll.register(fd, mask)

    def ctl_mod(self, fd, mask):
        self._poll.register(fd, mask)

    def ctl_del(self, fd):
        self._poll.unregister(fd)

    def wait(self, timeout):
        timeout = timeout is None and -1 or float(timeout)
        return self._poll.poll(timeout)

if hasattr(select, "epoll"):
    class event_epoll(_event_poll):
        def __init__(self, size=-1):
            sef._size = size
            self._epoll = select.epoll()

        def ctl_add(self, fd, mask):
            self._epoll.register(fd, mask)

        def ctl_mod(self, fd, mask):
            self._epoll.modify(fd, mask)

        def ctl_del(self, fd):
            self._epoll.unregister(fd)

        def wait(self, timeout=None):
            timeout = timeout is None and -1 or float(timeout)
            return self._epoll.poll(timeout, self._size)

else:
    class event_epoll(_event_poll):
        def __init__(self, size = 32*1024):
            super(event_epoll, self).__init__()
            self._size  = size
            self._epoll = _epoll.epoll(self._size)

        def ctl_add(self, fd, mask):
            self._epoll._control(_epoll.CTL_ADD, fd.fileno(), mask)

        def ctl_mod(self, fd, mask):
            self._epoll._control(_epoll.CTL_MOD, fd.fileno(), mask)

        def ctl_del(self, fd):
            self._epoll._control(_epoll.CTL_DEL, fd.fileno(), 0)

        def wait(self, timeout):
            timeout = timeout is None and -1 or int(timeout)
            return self._epoll.wait(self._size, timeout)
#
# primary scheduling/event loop
#
the_event_list = event_list()
the_event_poll = event_poll()
the_loop_count = 0

stop = 0

def use_epoll(size = 32*1024):
    if hasattr(select, "epoll") or _epoll is not None:
        global the_event_poll
        the_event_poll = event_epoll(size)
        return True
    else:
        return False

def shutdown(countdown = 0):
    global stop
    stop = time.time() + countdown

def exit_handler(signum, frame):
    print 'Caught signal <%d> exiting.' % (signum)
    shutdown()

def reset_event_loop():
    #
    # dump all events/threads, I'm using this to shut down, so
    # if the event_loop exits, I want to startup another eventloop
    # thread set to perform shutdown functions.
    #
    global the_event_list
    global the_event_poll
    global the_loop_count
    global pending

    the_event_list = event_list()
    the_event_poll = event_poll()
    the_loop_count = 0

    pending = {}

    return None

def _exit_event_loop():

    if stop and not (stop > time.time()):
        return True
    else:
        return not the_event_list and not the_event_poll and not pending


def _real_event_loop(max_timeout):
    global the_loop_count

    while True:
        #
        # count number of times through the loop
        #
        the_loop_count += 1
        #
        # run scheduled coroutines
        #
        run_pending()
        #
        # check for exit ahead of potential sleep
        #
        if _exit_event_loop():
            break
        #
        # calculate max timeout to wait before resuming anything
        #
        delta = the_event_list.next_event(max_timeout)
        delta = delta * 1000 ## seconds to milliseconds
        #
        # wait on readiness events using calculated timeout
        #
        results = the_event_poll.poll(delta)
        #
        # once the wait/poll has completed, schedule timer events ahead
        # of readiness events. There can only be one resume per waiting
        # coro each iteration. The last schedule() in the iteration will
        # be the resumed event. The event_list must handle having a
        # sechedule() disappear.
        #
        the_event_list.run_scheduled()

        for sock, thrd, in_event, out_event in results:
            schedule(thrd, out_event)
    #
    # exit...
    return None

def event_loop(max_timeout = 30.0):
    signal.signal(signal.SIGUSR1, exit_handler)
    global MAIN_EVENT_LOOP
    try:
        MAIN_EVENT_LOOP = greenlet(_real_event_loop)
        MAIN_EVENT_LOOP.switch(max_timeout)
    finally:
        preemptive_disable()
#
# end..

########NEW FILE########
__FILENAME__ = corocurl
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""corocurl

Emulation of PycURL objects which can be used inside the coro framework.

Written by Libor Michalek.
"""
import os
import getopt
import logging

import sys
import exceptions
import pycurl
import coro
import time
import select

__real_curl__ = pycurl.Curl
__real_mult__ = pycurl.CurlMulti

DEFAULT_YIELD_TIMEOUT = 2

class CoroutineCurlError (exceptions.Exception):
    pass

class coroutine_curl(object):
    '''coroutine_curl

    Emulation replacement for the standard pycurl.Curl() object. The
    object uses the non-blocking pycurl.CurlMulti interface to execute
    requests.
    '''

    def __init__(self):
        self._curl = __real_curl__()
        self._mult = __real_mult__()

        self._waits = {None: 0}
        self._fdno  = None

    def __getattr__(self, name):
        return getattr(pycurl, name)
    #
    # poll() registration API interface functions
    #
    def fileno(self):
        if self._fdno is None:
            raise CoroutineCurlError, 'coroutine curl no fd yet'

        return self._fdno

    def _wait_add(self, mask):
        self._waits[coro.current_thread()] = mask
        return reduce(lambda x, y: x|y, self._waits.values())

    def _wait_del(self):
        del(self._waits[coro.current_thread()])
        return reduce(lambda x, y: x|y, self._waits.values())

    def _waiting(self):
        return filter(lambda y: y[0] is not None, self._waits.items())
    #
    # internal
    #
    def _perform(self):
        current = coro.current_thread()
        if current is None:
            raise CoroutineCurlError, "coroutine curl in 'main'"

        while 1:
            ret = pycurl.E_CALL_MULTI_PERFORM

            while ret == pycurl.E_CALL_MULTI_PERFORM:
                ret, num = self._mult.perform()

            if not num:
                break
            #
            # build fdset and eventmask
            #
            read_set, send_set, excp_set = self._mult.fdset()
            if not read_set and not send_set:
                raise CoroutineCurlError, 'coroutine curl empty fdset'

            if read_set and send_set and read_set != send_set:
                raise CoroutineCurlError, 'coroutine curl bad fdset'

            self._fdno = (read_set + send_set)[0]
            eventmask  = 0

            if read_set:
                eventmask |= select.POLLIN

            if send_set:
                eventmask |= select.POLLOUT
            #
            # get timeout
            #
            # starting with pycurl version 7.16.0 the multi object
            # supplies the max yield timeout, otherwise we just use
            # a reasonable floor value.
            #
            if hasattr(self._mult, 'timeout'):
                timeout = self._mult.timeout()
            else:
                timeout = DEFAULT_YIELD_TIMEOUT
            #
            # wait
            #
            coro.the_event_poll.register(self, eventmask)
            result = current.Yield(timeout, 0)
            coro.the_event_poll.unregister(self)
            #
            # process results (result of 0 is a timeout)
            #
            self._fdno = None

            if result is None:
                raise CoroutineSocketWake, 'socket has been awakened'

            if 0 < (result & coro.ERROR_MASK):
                raise pycurl.error, (socket.EBADF, 'Bad file descriptor')

        queued, success, failed = self._mult.info_read()
        if failed:
            raise pycurl.error, (failed[0][1], failed[0][2])
    #
    # emulated API
    #
    def perform(self):
        self._mult.add_handle(self._curl)
        try:
            self._perform()
        finally:
            self._mult.remove_handle(self._curl)

    def close(self):
        self._mult.close()
        self._curl.close()

    def errstr(self):
        return self._curl.errstr()

    def getinfo(self, option):
        return self._curl.getinfo(option)

    def setopt(self, option, value):
        return self._curl.setopt(option, value)

    def unsetopt(self, option):
        return self._curl.setopt(option)

class coroutine_multi(object):
    '''coroutine_multi

    coroutine replacement for the standard pycurl.CurlMulti() object.
    Since one should not need to deal with CurlMulti interface while
    using the coroutine framework, this remains unimplemented.
    '''

    def __init__(self):
        raise CoroutineCurlError, 'Are you sure you know what you are doing?'

def emulate():
    "replace some pycurl objects with coroutine aware objects"
    pycurl.Curl      = coroutine_curl
    pycurl.CurlMulti = coroutine_multi
    # sys.modules['pycurl'] = sys.modules[__name__]
#
# Standalone testing interface
#
TEST_CONNECT_TIMEOUT = 15
TEST_DATA_TIMEOUT    = 15

class CurlEater:
    def __init__(self):
        self.contents = ''

    def body_callback(self, buf):
        self.contents = self.contents + buf

class CurlFetch(coro.Thread):
    def run(self, url):
        self.info('starting fetch <%s>' % (url,))
        ce = CurlEater()

        c = pycurl.Curl()
        c.setopt(pycurl.URL, url)
        c.setopt(pycurl.CONNECTTIMEOUT, TEST_CONNECT_TIMEOUT)
        c.setopt(pycurl.TIMEOUT, TEST_DATA_TIMEOUT)
        c.setopt(pycurl.WRITEFUNCTION, ce.body_callback)

        try:
            c.perform()
        except:
            self.traceback()

        self.info('fetched %d bytes' % (len(ce.contents),))
        return None

def run(url, log, loglevel):
    #
    # turn on curl emulation
    emulate()
    #
    # webserver and handler
    fetch = CurlFetch(log = log, args = (url,))
    fetch.set_log_level(loglevel)
    fetch.start()
    #
    # primary event loop.
    coro.event_loop()
    #
    # never reached...
    return None

LOG_FRMT = '[%(name)s|%(coro)s|%(asctime)s|%(levelname)s] %(message)s'
LOGLEVELS = dict(
    CRITICAL=logging.CRITICAL, DEBUG=logging.DEBUG, ERROR=logging.ERROR,
    FATAL=logging.FATAL, INFO=logging.INFO, WARN=logging.WARN,
    WARNING=logging.WARNING)

COMMAND_LINE_ARGS = ['help', 'logfile=', 'loglevel=', 'url=']

def usage(name, error = None):
    if error:
        print 'Error:', error
    print "  usage: %s [options]" % name

def main(argv, environ):
    progname = sys.argv[0]

    url      = None
    logfile  = None
    loglevel = 'INFO'

    dirname  = os.path.dirname(os.path.abspath(progname))
    os.chdir(dirname)

    try:
        list, args = getopt.getopt(argv[1:], [], COMMAND_LINE_ARGS)
    except getopt.error, why:
        usage(progname, why)
        return None

    for (field, val) in list:
        if field == '--help':
            usage(progname)
            return None
        elif field == '--url':
            url = val
        elif field == '--logfile':
            logfile = val
        elif field == '--loglevel':
            loglevel = val
    #
    # setup logging
    #
    hndlr = logging.StreamHandler(sys.stdout)
    log = coro.coroutine_logger('corocurl')
    fmt = logging.Formatter(LOG_FRMT)

    log.setLevel(logging.DEBUG)

    sys.stdout = coro.coroutine_stdout(log)
    sys.stderr = coro.coroutine_stderr(log)

    hndlr.setFormatter(fmt)
    log.addHandler(hndlr)
    loglevel = LOGLEVELS.get(loglevel, None)
    if loglevel is None:
        log.warn('Unknown logging level, using INFO: %r' % (loglevel, ))
        loglevel = logging.INFO
    #
    # check param and execute
    #
    if url is not None:
        result = run(url, log, loglevel)
    else:
        log.error('no url provided!')
        result = None

    return result

if __name__ == '__main__':
    main(sys.argv, os.environ)


#
# end...

########NEW FILE########
__FILENAME__ = corofile
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""corofile

Emulation of file objects with nonblocking semantics. Useful
for handling standard io.

Written by Donovan Preston.
"""

import coro

import os
import sys
import fcntl
import errno
import select

ERROR_MASK = select.POLLERR|select.POLLHUP|select.POLLNVAL
BUFFER_CHUNK_SIZE = 32*1024

class NonblockingFile(object):
    def __init__(self, fp):
        self._fp = fp

        F = fcntl.fcntl(self._fp.fileno(), fcntl.F_GETFL)
        F = F | os.O_NONBLOCK
        fcntl.fcntl(self._fp.fileno(), fcntl.F_SETFL, F)

        self._chunk = BUFFER_CHUNK_SIZE
        self._data  = ''
        self._waits = {None: 0}

    def fileno(self):
        return self._fp.fileno()

    def _wait_add(self, mask):
        self._waits[coro.current_thread()] = mask
        return reduce(lambda x, y: x|y, self._waits.values())

    def _wait_del(self):
        del(self._waits[coro.current_thread()])
        return reduce(lambda x, y: x|y, self._waits.values())

    def _waiting(self):
        return filter(lambda y: y[0] is not None, self._waits.items())

    def _wait_for_event(self, eventmask):
        me = coro.current_thread()
        if me is None:
            raise coro.CoroutineThreadError, "coroutine sockets in 'main'"

        coro.the_event_poll.register(self, eventmask)
        result = me.Yield()
        coro.the_event_poll.unregister(self)

        if result is None:
            raise coro.CoroutineSocketWake, 'file descriptor has been awakened'

        if result & eventmask:
            return None

        if result & ERROR_MASK:
            raise IOError(errno.EPIPE, 'Broken pipe')
        #
        # all cases should have been handled by this point
        return None

    def read(self, numbytes = -1):
        while numbytes < 0 or numbytes > len(self._data):
            self._wait_for_event(select.POLLIN|select.POLLHUP)

            read = os.read(self.fileno(), self._chunk)
            if not read:
                break

            self._data += read

        if numbytes < 0:
            result, self._data = self._data, ''
        else:
            result, self._data = self._data[:numbytes], self._data[numbytes:]

        return result

    def write(self, data):
        pos = 0

        while pos < len(data):
            self._wait_for_event(select.POLLOUT)

            size = os.write(self.fileno(), data[pos:pos + self._chunk])
            pos += size

    def flush(self):
        if hasattr(self._fp, 'flush'):
            self._wait_for_event(select.POLLOUT)
            self._fp.flush()

    def close(self):
        self._fp.close()


__old_popen2__ = os.popen2

def popen2(*args, **kw):
    stdin, stdout = __old_popen2__(*args, **kw)
    return NonblockingFile(stdin), NonblockingFile(stdout)


def emulate_popen2():
    if os.popen2 is not popen2:
        os.popen2 = popen2

__old_popen3__ = os.popen3

def popen3(*args, **kwargs):
    stdin, stdout, stderr = __old_popen3__(*args, **kwargs)
    return NonblockingFile(stdin), NonblockingFile(stdout), NonblockingFile(stderr)

def install_stdio():
    sys.stdin = NonblockingFile(sys.stdin)
    sys.stdout = NonblockingFile(sys.stdout)
    return sys.stdin, sys.stdout

def echostdin():
    sin, sout = install_stdio()

    sout.write("HELLO WORLD!\n")
    echo = ''
    while True:
        char = sin.read(1)
        if not char:
            return
        if char == '\n':
            sout.write('%s\n' % (echo, ))
            echo = ''
        else:
            echo += char


def readToEOF():
    sin, sout = install_stdio()

    read = sin.read()
    sout.write(read)


if __name__ == '__main__':
    coro.spawn(echostdin)
#	coro.spawn(readToEOF)
    coro.event_loop()



########NEW FILE########
__FILENAME__ = corohttpd
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 1999 eGroups, Inc.
# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
corohttpd
    This is an infrastructure for having a http server using coroutines
    There are three major classes defined here:
    HttpProtocol
        This is a descendent of coro.Thread. It handles the connection
        to the client, spawned by HttpServer. Its run method goes through
        the stages of reading the request, filling out a HttpRequest and
        finding the right handler, etc. It is separate from the HttpRequest
        object because each HttpProtocol, which represents one socket,
        can spawn multiple request with socket keepalives.
    HttpRequest
        This object collects all of the data for a request. It is initialized
        from the HttpClient thread with the http request data, and is then
        passed to the handler to receive data. It attempts to enforce a valid
        http protocol on the response
    HttpServer
        This is a thread which just sits accepting on a socket, and spawning
        HttpProtocols to handle incoming requests

    Additionally, the server expects http handler classes which respond
    to match and handle_request. There is an example class,
    HttpFileHandler, which is a basic handler to respond to GET requests
    to a document root. It will return any file which exists.

    To use, implement your own handler class which responds to match and
    handle_request. Then, create a server, add handlers to the server,
    and start it. You then need to call the event_loop yourself.
    Something like:

        server = HttpServer(args = (('0.0.0.0', 7001), 'access.log'))
        file_handler = HttpFileHandler('/home/htdocs/')
        server.push_handler(file_handler)
        server.start()
        coro.event_loop(30.0)
"""

import os
import coro
import socket
import string
import sys
import time
import re
import bisect
import errno
import logging
import logging.handlers
import getopt
import exceptions
import tempfile
import cStringIO
import urllib
import cgi
import BaseHTTPServer
import inspect
import Cookie
import zlib
import struct

import backdoor
import statistics

coro.socket_emulate()

SAVE_REQUEST_DEPTH  = 100
REQUEST_COUNT_DEPTH = 900
REQUEST_STATS_PERIOD = [15, 60, 300, 600]
ACCESS_LOG_SIZE_MAX  = 64*1024*1024
ACCESS_LOG_COUNT_MAX = 128

READ_CHUNK_SIZE = 32*1024
POST_READ_CHUNK_SIZE = 64*1024

SEND_BUF_SIZE = 128*1024
RECV_BUF_SIZE = 128*1024

HEADER_CLIENT_IPS = ['True-Client-IP', 'NS-Client-IP']

FUTURAMA = 'Mon, 28-Sep-2026 21:46:59 GMT'

try:
    # If we can get the hostname, obfuscate and add a header
    hostre = re.compile('^([A-Za-z\-_]+)(\d+|)(\.\w+|)')
    hostre = hostre.search(socket.getfqdn())
    hostgp = hostre and hostre.groups() or ('unknown','X','unknown')
    HOST_HEADER = (
        'X-Host',
        hostgp[0][0] + hostgp[0][-1] + hostgp[1] + hostgp[2])
except:
    HOST_HEADER = ('X-Host', 'FAIL')

def save_n(queue, value, data, depth):
    if value > queue[0][0]:
        bisect.insort(queue, (value, data))
        while len(queue) > depth:
            del(queue[0])

def header_blackcheck(rules, headers):
    for header, rule in rules:
        header = headers.get(header, [])
        header = (isinstance(header, str) and [[header]] or [header])[0]

        if not header:
            return True

        for element in header:
            if rule(element):
                return True

    return False

def gzip_stream(s):
    header = struct.pack(
        '<BBBBIBB',
        0x1f,
        0x8b,
        0x08,
        0x00,
        int(time.time()),
        0x00,
        0x03)

    size = len(s)
    crc  = zlib.crc32(s)

    return header + zlib.compress(s)[2:-4] + struct.pack('<II', crc, size)

def deflate_stream(s):
    return zlib.compress(s)

SUPPORTED_ENCODINGS = [('gzip', gzip_stream), ('deflate', deflate_stream)]

class ConnectionClosed(Exception):
    def __repr__(self):
        return "ConnectionClosed(%r)" % (self.args[0], )

NO_REQUEST_YET = "<no request yet>"
NO_COMMAND_YET = "<no command yet>"
BETWEEN_REQUESTS = "<between requests>"

class HttpAllow(object):
    '''HttpAllow

    Access check based on IP address. Initialized with a list of IP
    addresses, using an optional netmask, that are allowed to access
    the resource. An IP is checked against the list uring the match
    method.
    '''
    def __init__(self, allow):
        self._allow = []

        for address in allow:
            address = address.split('/')

            if 1 < len(address):
                mask = int(address[-1])
            else:
                mask = 32

            address = reduce(
                lambda x, y: (x<<8) | y,
                map(lambda i: int(i), address[0].split('.')))

            mask = (1 << (32 - mask)) - 1

            self._allow.append({'addr': address, 'mask': mask})

    def match(self, address):
        address = reduce(
            lambda x, y: (x<<8)|y,
            map(lambda i: int(i), address.split('.')))

        for allow in self._allow:
            if allow['addr']|allow['mask'] == address|allow['mask']:
                return True

        return False


class HttpProtocol(coro.Thread, BaseHTTPServer.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'corohttpd/0.2'
    request_version = 'HTTP/0.9'

    connection = None
    client_address = ('<no address yet>', 0)
    close_connection = 0
    server = None
    request = None
    handlers = []
    buffer = ''
    _index = -1
    closed = False
    _chunked = False
    requestline = NO_REQUEST_YET
    command = NO_COMMAND_YET
    _reply_code = 200
    _request_count = 0

    def __init__(self, *args, **kwargs):
        super(HttpProtocol, self).__init__(*args, **kwargs)
        #
        # DO NOT call the BaseHTTPRequestHandler __init__. It kicks
        # off the request handling immediately. We need it to happen
        # in run instead. Since the base class for BaseHTTPRequestHandler
        # (SocketServer.BaseRequestHandler) is not a subclass of object,
        # the super call will not invoke the __init__ handler for it,
        # only for coro.Thread.
        #
        self._tbrec = kwargs.get('tbrec', None)
        self._debug_read = kwargs.get('debug_read', False)

        self._rsize = 0
        self._wsize = 0

        self._debug_read_buffers = []

        self._default_headers = []
        self._reply_headers = {}
        self._encblack = None

        self.accumulator = None
        self.headers = {}

        self.raw_requestline = ''
        self._push_time = 0
        self._req_time = 0
        self._sent_headers = False
        self._encode_write = False
        self._encode_wrote = False
        self._old_loglevel = None

    def run(self, conn, client_address, server, handlers):
        ## TODO get rid of _conn and use request instead
        ## same with these other two
        self.connection = conn
        self.client_address = client_address
        self.server = server
        self.handlers = handlers

        self.rfile = self

        self.handle()

        return None

    def complete(self):
        self.server.record_counts(self._request_count)
        self.server = None

        try:
            self.connection.shutdown(2)
        except socket.error:
            pass
        self.connection = None

        self.closed = True
        self.client_address = ('<no address>', 0)
        self.handlers = []
        self.buffer = ''
        self._index = -1
        self.requestline = NO_REQUEST_YET
        self.headers = None
        self.rfile = None

    def handle_one_request(self):
        self.raw_requestline = ''
        self._push_time = 0
        self._req_time = 0
        self._rsize = 0
        self._wsize = 0
        self._sent_headers = False
        self._encode_write = False
        self._encode_wrote = False
        self._reply_headers = {}
        self._reply_code = 200

        try:
            self.really_handle()

            if self._chunked:
                self.write('0\r\n\r\n')

            if not self.close_connection:
                self.requestline = BETWEEN_REQUESTS

            return None
        except ConnectionClosed, e:
            self.warn('connection terminated: %r' % (e,))
        except socket.error, e:
            if e[0] in [errno.EBADF, errno.ECONNRESET, errno.EPIPE]:
                self.debug('socket error: %r' % (e.args,))
            else:
                self.warn('socket error: %r' % (e.args,))
        except coro.TimeoutError, e:
            if self.raw_requestline:
                self.warn('Timeout: %r for %r' % (
                    e.args[0], self.client_address))
        except coro.CoroutineSocketWake:
            pass
        except:
            self.traceback()
        #
        # exception cases fall through.
        #
        self.close_connection = 1

    def really_handle(self):
        #
        # get request line and start timer
        #
        self.raw_requestline = self.readline()
        self._req_time = time.time()
        self.clear()

        if not self.raw_requestline:
            self.close_connection = 1
            return

        if not self.parse_request():
            self.close_connection = 1
            return

        keep_alive = self.headers.get('Keep-Alive', None)
        if keep_alive is not None:
            try:
                self.connection.settimeout(int(keep_alive))
            except ValueError:
                ## not an int; do nothing
                pass

        self.debug('from: %r request: %r' % (
            self.client_address, self.requestline,))

        for key, value in self._default_headers:
            self.set_header(key, value)

        self.request = HttpRequest(
            self, self.requestline, self.command, self.path, self.headers)
        self.server.request_started(self.request, self._req_time)

        try:
            try:
                for handler in self.handlers:
                    if handler.match(self.request):
                        self.debug('Calling handler: %r' % (handler,))

                        handler.handle_request(self.request)
                        self.push('')
                        break
                else:
                    self.debug('handler not found: %r' % (self.request))
                    self.send_error(404)
            except (
                ConnectionClosed,
                coro.TimeoutError,
                coro.CoroutineSocketWake,
                socket.error):
                #
                # can not send the error, since it is an IO problem,
                # but set the response code anyway to something denoting
                # the issue
                #
                self.traceback(logging.DEBUG)
                self.response(506)
                raise
            except:
                self.traceback()
                self.send_error(500)
        finally:
            self.server.request_ended(
                self.request,
                self._reply_code,
                self._req_time,
                self._push_time,
                self._rsize,
                self._wsize)

            if self._debug_read:
                self.log_reads()
                self._debug_read = False
                self._debug_read_buffers = []

            if self._old_loglevel is not None:
                self.set_log_level(self._old_loglevel)
                self._old_loglevel = None

            self._request_count += 1
            self.raw_requestline = ''
            self.request = None
            self.accumulator = None

        return None

    def send_error(self, code, message=None):
        self.response(code)
        self.set_header('content-type', 'text/html')
        self.set_header('connection', 'close')

        if (
            self.command != 'HEAD' and code >= 200
            and code not in (204, 304)):
            if message is None:
                message = self.responses[code][0]
            message = message.replace(
                "&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            explain = self.responses[code][1]
            content = self.error_message_format % dict(
                code=code, message=message, explain=explain)
            self.set_header('Content-Length', len(content))
            self.push(content)
        else:
            self.push('')

    def log_request(self, code='-', size='-'):
        """log_request

        Called by BaseHTTPServer.HTTPServer to log the request completion.

        There is not enough information here to properly log the request;
        so we just ignore this and write to the access log ourselves.
        """
        pass

   	def log_error(self, format, *args):
        """log_error

        Called by BaseHTTPServer.HTTPServer to log an error.
        """
        formatted = format % args
        self.error(formatted)
        self.info('Request: %s' % (self.requestline, ))
        if '404' not in formatted:
            for key, value in self.headers.items():
                self.info('Header: %s: %s' % (key, value ))

    def log_message(self, format, *args):
        """log_message

        Called by BaseHTTPServer.HTTPServer to log a message.
        """
        self.info(format % args)

    def log_reads(self):
        """log_reads

        Write the contents of _debug_read_buffers out to the log.
        """
        self.debug('----------BEGIN DEBUG REPORT----------')
        for data in self._debug_read_buffers:
            if isinstance(data, (str, unicode)):
                self.debug(data)
            else:
                self.debug(repr(data))
        self.debug('---------- END DEBUG REPORT ----------')

    def set_debug_read(self, flag=True):
        """set_debug_read

        Call to set (or unset) the _debug_read flag.  If this flag is
        set, data received in calls to read and readlines will be
        logged.
        """
        self._debug_read = flag

    def add_debug_read_data(self, s):
        self._debug_read_buffers.append(s)

    def req_log_level(self, level):
        '''req_log_level

        Set the coroutine log level for one request.
        '''
        self._old_loglevel = self.get_log_level()
        self.set_log_level(level)

    def set_encode_blacklist(self, data):
        '''set_encode_blacklist

        Set the response encoding blacklist. (added by server which
        maintains master list)

        NOTE: the default is no blacklist, which means that no encoding
              will be performed. To encode all responses, push an empty
              blacklist.
        '''
        self._encblack = data

    def address_string(self):
        """address_string

        Called by BaseHTTPServer.HTTPServer to get the address of the
        remote client host to put in the access log.
        """
        if self.request:
            for header_name in HEADER_CLIENT_IPS:
                ip = self.request.get_header(header_name)
                if ip: break
        else:
            ip = None

        if ip is None:
            return str(self.client_address[0])
        else:
            return ip

    # This is for handlers that process PUT/POST themselves.
    # This whole thing needs to be redone with a file-like
    # interface to 'stdin' for requests, and we need to think
    # about HTTP/1.1 and pipelining, etc...

    def read(self, size):
        while len(self.buffer) < size:
            buffer = self.connection.recv(READ_CHUNK_SIZE)
            if not buffer:
                raise ConnectionClosed("Remote host closed connection in read")
            self.buffer += buffer
            self._rsize += len(buffer)

            if self.accumulator:
                self.accumulator.recv_bytes(len(buffer))

        result = self.buffer[:size]
        self.buffer = self.buffer[size:]

        if self._debug_read: self._debug_read_buffers.append(result)
        return result

    def readline(self, size=None):
        while 0 > self._index:
            buffer = self.connection.recv(READ_CHUNK_SIZE)
            if not buffer:
                return buffer

            self.buffer += buffer
            self._rsize += len(buffer)
            self._index = string.find(self.buffer, '\n')

            if self.accumulator:
                self.accumulator.recv_bytes(len(buffer))

        result = self.buffer[:self._index+1]

        self.buffer = self.buffer[self._index + 1:]
        self._index = string.find(self.buffer, '\n')

        if self._debug_read: self._debug_read_buffers.append(result)
        return result

    def write(self, data):
        olb = lb = len(data)
        while lb:
            ns = self.connection.send(data[olb-lb:])
            if self.accumulator:
                self.accumulator.sent_bytes(ns)
            lb = lb - ns
        self._wsize = self._wsize + olb
        return olb

    def set_default_headers(self, data):
        self._default_headers = data

    def set_header(self, key, value, overwrite = True):
        value = str(value)
        if key.lower() == 'connection' and value.lower() == 'close':
            self.close_connection = 1

        if overwrite:
            self._reply_headers[key.lower()] = [value]
        else:
            self._reply_headers.setdefault(key.lower(), []).append(value)

    def get_outgoing_header(self, key, default = None):
        return self._reply_headers.get(key.lower(), default)

    def has_outgoing_header(self, key):
        return self._reply_headers.has_key(key.lower())

    def pop_outgoing_header(self, key):
        return self._reply_headers.pop(key.lower(), None)

    def response(self, code=200):
        self._reply_code = code

    def encode(self, s):
        #
        # check if encoding is allowed locally.
        #
        if not s:
            return s
        #
        # code path encode selection.
        if not self._encode_write:
            return s
        #
        # encoding capability configuration
        if self._encblack is None:
            return s

        ingress, egress = self._encblack
        #
        # egress/content blacklist
        if header_blackcheck(egress, self._reply_headers):
            return s
        #
        # generate Vary header before checking the encode header or the
        # ingress blacklist, since that will not effect that this content
        # MAY be encoded. From this point on an encode is possible and
        # will depend on what the client has sent.
        #
        vary = map(lambda i: i[0], ingress)
        vary.append('accept-encoding')
        vary = map(lambda i: '-'.join(map(str.title, i.split('-'))), vary)

        self.set_header('Vary', ','.join(vary))
        #
        # decode accept-encoding header
        #
        header = self.headers.get('accept-encoding', None)
        if not header:
            return s

        encodings = []
        for node in map(lambda i: i.split(';'), header.split(',')):
            if len(node) < 2:
                encodings.append((node[0], 1))
                continue

            node, quality = node[:2]
            try:
                quality = float(quality.split('=')[1])
            except (ValueError, IndexError), e:
                continue

            encodings.append((node, quality))

        encodings = filter(lambda i: i[1], encodings)
        encodings.sort(key = lambda i: i[1], reverse = True)
        encodings = set(map(lambda i: i[0].strip(), encodings))

        if not encodings:
            return s
        #
        # check the headers against supported types.
        #
        for ename, efunc in SUPPORTED_ENCODINGS:
            if ename in encodings:
               break
        else:
            ename, efunc = None, None

        if ename is None:
            return s
        #
        # ingress header check
        if header_blackcheck(ingress, self.headers):
            return s

        #
        # compress
        #
        s = efunc(s)
        #
        # generate encoding specific headers.
        #
        self.set_header('Content-Encoding', ename)
        self.set_header('Content-Length', len(s))

        self._encode_wrote = True
        return s

    def push(self, s, encode = False):
        self._push_time = time.time()
        #
        # toggle encode, once a push is encoded it needs to stay
        #
        self._encode_write |= encode

        if self._encode_wrote and self._sent_headers and s:
            raise RuntimeError('Cannot encode after headers have been sent')

        if self.request_version == 'HTTP/0.9' or self._sent_headers:
            return self.write(s)

        if self.close_connection:
            self.set_header('connection', 'close', overwrite = True)
        if not self.has_outgoing_header('server'):
            self.set_header('server', self.version_string())
        if not self.has_outgoing_header('date'):
            self.set_header('date', self.date_time_string())
        if not self.has_outgoing_header('connection'):
            self.set_header('connection', self.headers.get(
                'connection', 'close').strip())

        transfer = self.get_outgoing_header('transfer-encoding', [])
        if transfer:
            self._chunked = transfer[-1] == 'chunked'
        else:
            self._chunked = False

        if self._encode_write and self._chunked:
            raise RuntimeError('HTTP encode with chunk unsupported')

        s = self.encode(s)

        if not self._chunked and not self.has_outgoing_header('content-length'):
            self.set_header('content-length', len(s))

        keep_alive = self.get_outgoing_header(
            'connection', ['close'])[-1].lower()

        if keep_alive == 'keep-alive':
            self.close_connection = 0
        else:
            self.close_connection = 1

        headers = []
        for key, values in self._reply_headers.items():
            for value in values:
                headers.append(
                    '%s: %s' % (
                    '-'.join(map(str.title, key.split('-'))), value))

        headers.extend(('', ''))
        self._sent_headers = True

        return self.write(
            "%(version)s %(code)s %(message)s\r\n"
            "%(headers)s%(body)s" % dict(
                version=self.protocol_version,
                code=self._reply_code,
                message=self.responses[self._reply_code][0],
                headers='\r\n'.join(headers),
                body=s))

    def push_chunked(self, stuff):
        chunked = '%X\r\n%s\r\n' % (len(stuff), stuff)
        if self._sent_headers:
            self.write(chunked)
        else:
            self.set_header('transfer-encoding', 'chunked')
            self.push(chunked)

    def shutdown(self, nice = False):
        self.close_connection = 1

        if not self.connection:
            return None

        if nice and self.raw_requestline:
            return None

        if hasattr(self.connection, 'wake'):
            self.connection.wake()

    def get_name(self):
        if self.request is None:
            return '%s.%s' % (
                self.__class__.__module__,
                self.__class__.__name__)
        else:
            return self.request.get_name()

    def traceback(self, level = logging.ERROR):
        super(HttpProtocol, self).traceback(level)

        if level < logging.INFO:
            return None

        if self._tbrec is None:
            return None

        self._tbrec.record(name = self.get_name())

    def sent_headers(self):
        return self._sent_headers


class HttpRequest(object):
    request_count = 0
    # <path>;<params>?<query>#<fragment>
    path_re = re.compile('([^;?#]*)(;[^?#]*)?(\?[^#]*)?(#.*)?')
    cookies = {}

    def __init__(self, connection, requestline, command, path, headers):
        HttpRequest.request_count = HttpRequest.request_count + 1
        self._request_number = HttpRequest.request_count
        self.requestline = requestline
        self._request_headers = headers
        self._connection = connection
        #
        # request is named by handler for stats collection
        #
        self._name = 'none'

        ## By the time we get here, BaseHTTPServer has already
        ## verified that the request line is correct.
        self._method = command.lower()
        self._uri = path

        m = HttpRequest.path_re.match(self._uri)
        self._path, self._params, self._query, self._frag = m.groups()

        if self._query and self._query[0] == '?':
            self._query = self._query[1:]
        #
        # unquote the path, other portions of the uri are unquoted
        # where they are handled
        #
        self._path = urllib.unquote_plus(self._path)
        self.cookie_domain = None
    #
    # statistics/information related functions.
    # name should be set by request handler and used for statistics gathering
    #
    def set_name(self, o):
        if inspect.isclass(type(o)):
            o = type(o)
        if inspect.isclass(o):
            o = '%s.%s' % (o.__module__, o.__name__)
        if type(o) == type(''):
            self._name = o

    def get_name(self):
        return self._name
    #
    # some pass through functions to the connection
    #
    def log_level(self, level):
        '''log_level

        Set the coroutine log level for this request.
        '''
        self._connection.req_log_level(level)

    def push(self, s, encode = False):
        '''push

        Given a string push the value to the request client. The first
        push for a request will generate and flush headers as well.
        An optional encode parameter, when set to True, will attempt
        a content encoding on the string.

        NOTE: When encode is True the entire body of the response MUST
              be pushed, since the encode cannot be partial. IF a
              susequent push is performed on the same request after an
              encode has occured, an exception will be raised.
        '''
        return self._connection.push(s, encode = encode)

    def set_header(self, key, value, **kwargs):
        return self._connection.set_header(key, value, **kwargs)

    def get_outgoing_header(self, key, default = None):
        return self._connection.get_outgoing_header(key, default)

    def has_outgoing_header(self, key):
        return self._connection.has_outgoing_header(key)

    def pop_outgoing_header(self, key):
        return self._connection.pop_outgoing_header(key)

    def has_key(self, key):
        return self.has_outgoing_header(key)

    def push_chunked(self, s):
        return self._connection.push_chunked(s)

    def response(self, code = 200):
        return self._connection.response(code)

    def send_error(self, code, message = None):
        return self._connection.send_error(code, message)

    def server(self):
        return self._connection.server

    def proto(self):
        return float(self._connection.request_version.split('/')[1])

    # Method access
    def method(self):
        return self._method

    # URI access
    def uri(self):
        return self._uri

    def address_string(self):
        for name in HEADER_CLIENT_IPS:
            ip = self.get_header(name)
            if ip: return ip

        return str(self._connection.client_address[0])

    # Incoming header access
    def get_header(self, header_name, default=None):
        """Get a header with the given name. If none is present,
        return default. Default is None unless provided.
        """
        return self.get_headers().get(header_name.lower(), default)

    def get_headers(self):
        return self._request_headers

    def get_query_pairs(self):
        """get_query_pairs

        Return a tuple of two-ples, (arg, value), for
        all of the query parameters passed in this request.
        """
        if hasattr(self, '_split_query'):
            return self._split_query

        self._split_query = []

        if self._query is None:
            return self._split_query

        for value in self._query.split('&'):
            value = value.split('=')
            key   = value[0]
            value = '='.join(value[1:])

            if key and value:
                self._split_query.append(
                    (urllib.unquote_plus(key), urllib.unquote_plus(value)))

        return self._split_query

    # Query access
    def get_query(self, name):
        """Generate all query parameters matching the given name.
        """
        for key, value in self.get_query_pairs():
            if key == name or not name:
                yield value

    # Post argument access
    def get_arg_list(self, name):
        return self.get_field_storage().getlist(name)

    def get_arg(self, name, default=None):
        return self.get_field_storage().getfirst(name, default)

    def get_field_storage(self):
        if not hasattr(self, '_field_storage'):
            if self.method() == 'get':
                data = ''
                if self._query:
                    data = self._query

                fl = cStringIO.StringIO(data)
            else:
                fl = self._connection.rfile
            ## Allow our resource to provide the FieldStorage instance for
            ## customization purposes.
            headers = self.get_headers()
            environ = dict(
                REQUEST_METHOD = 'POST',
                QUERY_STRING   = self._query or '')

            if (hasattr(self, 'resource') and
                hasattr(self.resource, 'getFieldStorage')):

                self._field_storage = self.resource.getFieldStorage(
                    fl, headers, environ)
            else:
                self._field_storage = cgi.FieldStorage(
                    fl, headers, environ = environ)

        return self._field_storage

    def get_cookie(self, name = None, default = None, morsel = False):
        '''get_cookie

        Return a Cookie.SimpleCookie() object containing the request
        cookie.

        Optional parameters:

          name    - Return a specific cookie value.
          morsel  - If True then the name/value will be wrapped in a
                    Cookie.Morsel() object, (default: False) instead
                    of the actual value string.
          default - If the name parameter is specified and the specified
                    name is not found in the cookie then the provided
                    default will be returned instead of None.
        '''
        if not hasattr(self, '_simple_cookie'):
            cookie = self.get_header('Cookie', default='')
            self._simple_cookie = Cookie.SimpleCookie()
            self._simple_cookie.load(cookie)

        if name is None:
            return self._simple_cookie

        data = self._simple_cookie.get(name)
        if data is None:
            return default

        if morsel:
            return data
        else:
            return data.value

    def set_cookie(
        self, name, value,
        domain = None, path = '/', expires = FUTURAMA, strict = False):
        '''set_cookie

        Given a name and value, add a set-cookie header to this request
        objects response.

        Optional parameters:

        domain  - Set the cookie domain. If a cookie domain is not provided
                  then the objects cookie_domain member will be used as the
                  domain. If the cookie_domain member has not been set then
                  the requests Host header will be used to determine the
                  domain. Specifically the N-1 segments of the host or the
                  top 2 levels of the domain which ever is GREATER.
        strict  - If set to True then raise an error if neither the domain
                  parameter or cookie_domain member is set. In other words
                  do NOT derive the domain from the Host header.
                  (default: False)
        expires - Set the cookie expiration time. (default: far future)
                  Use empty string expires value for session cookies.
                  (i.e. cookies that expire when the browser is closed.)
        path    - Set the cookie path. (default: /)
        '''
        if domain is None:
            if self.cookie_domain is None:
                if strict:
                    raise LookupError('no domain set w/ strict enforcement')

                host = self.get_header('host')
                if host is None:
                    raise ValueError('no host header for cookie inheritance')

                host = host.split('.')
                chop = max(len(host) - 1, min(len(host), 2))
                host = host[-chop:]

                if len(host) < 2:
                    raise ValueError(
                        'bad host header for cookie inheritance',
                        self.get_header('host'))

                domain = '.'.join(host)
            else:
                domain = self.cookie_domain

        domain = domain.split(':')[0]

        morsel = Cookie.Morsel()
        morsel.set(name, value, value)

        morsel['domain']  = '.%s' % domain
        morsel['path']    = path
        morsel['expires'] = expires

        self.set_header('Set-Cookie', morsel.OutputString(), overwrite = False)

    def write(self, stuff):
        #
        # this is where the templating stuff is
        # Hook for converting from random objects into html
        #
        if hasattr(self, 'convert'):
            converted = self.convert(self, stuff)
        else:
            converted = stuff

        self.connection().set_header('Content-Length', len(converted))
        #
        # since write is a one shot process, no follow-up push/writes
        # are expected or encouraged, we are safe to attempt an encoding.
        # check to see if headers have been sent, since some error/exotic
        # paths may send ahead of the framework write.
        #
        encode = not self.connection().sent_headers()
        self.push(converted, encode = encode)

    def connection(self):
        return self._connection

    def traceback(self, level = logging.ERROR):
        return self._connection.traceback(level = level)

    def __setitem__(self, key, value):
        self._connection.set_header(key, value)

    request = property(lambda self: self)

class HttpFileHandler(object):
    def __init__(self, doc_root):
        self.doc_root = doc_root

    def match(self, request):
        path = request._path
        filename = os.path.join(self.doc_root, path[1:])
        if os.path.exists(filename):
            return True
        return False

    def handle_request(self, request):
        request.set_name(self)

        path = request._path
        filename = os.path.join(self.doc_root, path[1:])

        if os.path.isdir(filename):
            filename = os.path.join(filename, 'index.html')

        if not os.path.isfile(filename):
            request.send_error(404)
        else:
            f = file(filename, 'rb')
            finfo = os.stat(filename)
            request.set_header('Content-Type', 'text/html')
            request.set_header('Content-Length', str(finfo.st_size))
            bc = 0

            block = f.read(8192)
            if not block:
                request.send_error(204) # no content
            else:
                while 1:
                    bc = bc + request.push(block)
                    block = f.read(8192)
                    if not block:
                        break

class HttpStatisticsHandler(object):
    def __init__(self, allow = [], name = 'statistics'):
        self._name  = name
        self._allow = HttpAllow(allow)

    def match(self, request):
        if request.proto() < 1.0:
            return False

        if self._name != request._path.strip('/'):
            return False
        else:
            return self._allow.match(request.connection().address_string())

    def handle_request(self, request):
        request.set_name(self)

        server = request.server()
        data = 'total:'

        results = server.request_averages()
        data += ' %d %d %d %d'   % tuple(map(lambda x: x['count'], results))
        data += ' %d %d %d %d\n' % tuple(map(lambda x: x['elapse'], results))

        results = server.request_details()
        results = results.items()
        results.sort()

        for name, values in results:
            data += '%s:' % (name,)

            for value in values:
                data += ' %d' % (value['count']/value['seconds'])

            for value in values:
                if value['count']:
                    result = value['elapse']/value['count']
                else:
                    result = 0

                data += ' %d' % result

            data += '\n'

        request.set_header('Content-Type', 'text/plain')
        request.response(200)
        request.push(data)

class HttpServer(coro.Thread):
    def __init__(self, *args, **kwargs):
        super(HttpServer, self).__init__(*args, **kwargs)

        self._handlers = []
        self._max_requests = 0
        self._outstanding_requests = {}
        self._exit = False
        self._headers = [HOST_HEADER]
        self._encblack = None
        self._graceperiod = 0
        self._send_size = SEND_BUF_SIZE
        self._recv_size = RECV_BUF_SIZE
        self._connects = 0
        self._requests = 0
        self._response = 0
        self._recorder = statistics.Recorder()
        self._stoptime = 30

        self._wall_time = statistics.TopRecorder(threshold = 0.0)
        self._exec_time = statistics.TopRecorder(threshold = 0.0)
        self._nyld_time = statistics.TopRecorder(threshold = 0.0)
        self._resu_time = statistics.TopRecorder(threshold = 0)
        #
        # mark whether socket was provided to ensure creator is always
        # the destructor as well.
        #
        self.socket = kwargs.get('socket', None)
        self.passed = bool(self.socket is not None)
        self._tbrec = kwargs.get('tbrec', None)
        self._debug = False
        #
        # post request callbacks.
        #
        preq = kwargs.get('postreq', [])
        preq = (isinstance(preq, (list, tuple)) and [preq] or [[preq]])[0]

        self._postreqs = preq

    def statistics(self, allow):
        '''statistics

        Enable IP addresses in the 'allow' list to access server
        statistics through a 'GET /statistics' request.
        '''
        self.push_handler(HttpStatisticsHandler(allow))

    def push_default_headers(self, data, merge = True):
        if not merge:
            self._headers.extend(data)

        headers = set(map(lambda i: i[0], self._headers))
        for header, value in data:
            if header in headers:
                self._headers = filter(lambda i: i[0] != header, self._headers)

            self._headers.append((header, value))

    def push_handler(self, handler):
        self._handlers.append(handler)

    def replace_handler(self, old_handler, new_handler):
        """replace_handler replaces old_handler with new_handler in
        this http servers handlers list.

        Returns old_handler on success, raises ValueError if
        old_handler is not in the handlers list.
        """
        for i in xrange(len(self._handlers)):
            if self._handlers[i] == old_handler:
                self._handlers[i] = new_handler
                return old_handler

        raise exceptions.ValueError('%s not in handlers' % str(old_handlers))

    def drop_handlers(self):
        self._handlers = []

    def push_encode_blacklist(self, data):
        '''push_encode_blacklist

        Add a response encoding blacklist.

        NOTE: the default is no blacklist, which means that no encoding
              will be performed. To encode all responses, push an empty
              blacklist.
        '''
        self._encblack = data

    def socket_init(self, addr):
        '''socket_init

        create listen socket if it does not already exist.
        '''
        if self.socket is not None:
            return None

        self.socket = coro.make_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.passed = False

        self.socket.set_reuse_addr()
        self.socket.bind(addr)
        self.socket.listen(1024)

    def socket_term(self):
        '''socket_term

        close and delete the listen socket if the server created it.
        '''
        if self.passed:
            return None

        if self.socket is None:
            return None

        self.socket.close()
        self.socket = None

    def set_debug_read(self, flag=True):
        """set_debug_read

        Call to set (or unset) the _debug_read flag.  If this flag is
        set, data received in calls to read and readlines will be
        logged.
        """
        self._debug = flag
        for child in self.child_list():
            child.set_debug_read(self._debug)

    def run(self, addr = None, logfile = '', timeout = None, idle = None):
        self._daily = []
        self._hourly = []

        self._idletime = idle
        self._timeout  = timeout

        hndlr = logging.handlers.RotatingFileHandler(
            logfile or 'log', 'a', ACCESS_LOG_SIZE_MAX, ACCESS_LOG_COUNT_MAX)
        hndlr.setFormatter(logging.Formatter('%(message)s'))

        self.access = logging.Logger('access')
        self.access.addHandler(hndlr)

        self.socket_init(addr)

        address, port = self.socket.getsockname()
        self.port = port

        self.info('HttpServer listening on %s:%d' % (address, port))
        while not self._exit:
            try:
                sock, address = self.socket.accept()
                sock.settimeout(self._timeout)
                sock.setsockopt(
                    socket.SOL_SOCKET, socket.SO_SNDBUF, self._send_size)
                sock.setsockopt(
                    socket.SOL_SOCKET, socket.SO_RCVBUF, self._recv_size)

                protocol = HttpProtocol(
                    tbrec = self._tbrec,
                    postreq = self._postreqs,
                    debug_read = self._debug,
                    args = (sock, address, self, self._handlers))
                ## This is for any sockets that may happen to get opened
                ## during the processing of these http requests; additional
                ## outgoing requests made by the server in order to get
                ## data to fulfill an incoming web request, etc.
                protocol.set_socket_timeout(self._idletime)
                protocol.set_default_headers(self._headers)
                protocol.set_encode_blacklist(self._encblack)
                protocol.start()
            except coro.CoroutineSocketWake:
                continue
            except coro.TimeoutError, e:
                self.warn('Http Server: socket timeout: %r' % (e,))
                continue
            except socket.error, e:
                self.warn('Http Server: socket error: %s' % str(e))
                continue
            except exceptions.Exception, e:
                self.error('Http Server: exception: %r' % (e,))
                self.traceback()
                break

        self.info('HttpServer exiting (children: %d)' % self.child_count())
        #
        # stop listening for new connections
        #
        self.socket_term()
        #
        # yield to allow any pending protocol threads to startup.
        # (so we can shut them down :)
        #
        self.Yield(timeout = 0)
        #
        # mark all child connections as in close
        #
        for client in self.child_list():
            client.close_connection = 1
        #
        # wait for a grace period before force closing any open
        # connections which are waiting for requests
        #
        if self.child_list():
            self.Yield(self._graceperiod)

        for client in self.child_list():
            client.shutdown(nice = True)
        #
        # wait for all children to exit
        #
        zombies = self.child_wait(self._stoptime)
        if not zombies:
            return None

        self.info('httpd server timeout on %d zombies' % (zombies))
        for zombie in self.child_list():
            self.info(
                '  httpd zombie: %r <%s>' % (
                    zombie.client_address,
                    zombie.requestline))

        return None

    def complete(self):
        self._handlers = []
        self._max_requests = 0
        self._outstanding_requests = {}

    def record_counts(self, requests):
        self._connects += 1
        if requests:
            self._requests += requests
            self._response += 1

    def request_started(self, request, current = None):
        """request_started

        Called back from HttpProtocol when an individual request is
        starting. Can be either a single socket with non-persistent
        connections, or a single request of many on a socket with
        persistent connections.
        """
        #
        # save request for duration
        #
        self._outstanding_requests[request] = request
        #
        # count max outstanding requests
        #
        self._max_requests = max(
            len(self._outstanding_requests), self._max_requests)

    def request_ended(self, req, code, start_time, push_time, rsize, wsize):
        """request_ended

        Called back from HttpProtocol when an individual request is
        finished, erronious or not. Must be paired with request_started.
        """

        if self._exit:
            return None
        #
        # get a single fix on the time
        #
        current = time.time()
        #
        # fixup times
        #
        total_time = max(current - start_time, 0)
        local_time = max(push_time - start_time, 0)
        #
        # record local_time by request handler
        #
        self._recorder.request(
            local_time,
            name = req.get_name(),
            current = current)
        #
        # clear outstanding request
        #
        if req in self._outstanding_requests:
            del(self._outstanding_requests[req])
        #
        # save N most expensive requests
        #
        data = (
            req._uri,
            local_time,
            coro.current_thread().total_time(),
            coro.current_thread().resume_count(),
            coro.current_thread().long_time())

        self._wall_time.save(data[1], data)
        self._exec_time.save(data[2], data)
        self._nyld_time.save(data[3], data)
        self._resu_time.save(data[4], data)
        #
        # log file
        #
        self.access.info(
            '0 - - [%s] "%s" %s %s %s %d %d %s %d' % (
            req.connection().log_date_time_string(),
            req.requestline,
            code, total_time, local_time, rsize, wsize,
            req.connection().address_string(),
            coro.current_id()))
        #
        # Call any request completion callbacks
        #
        for call in self._postreqs:
            if not callable(call):
                continue

            try:
                call(
                    req,
                    code = code,
                    start_time = start_time,
                    push_time = push_time,
                    current_time = current,
                    read_size = rsize,
                    write_size = wsize)
            except:
                self.error('TB in %r' % call)
                self.traceback()

        return None

    def outstanding_requests(self):
        """outstanding_requests

        Call me to find out which requests are outstanding.
        """
        return self._outstanding_requests.values()

    def max_requests(self):
        """max_requests

        Call me to find out what the max concurrent requests high-water
        mark was.
        """
        return self._max_requests

    def num_requests(self):
        """num_requests

        Call me to find out how many requests I am currently handling.
        """
        return len(self._outstanding_requests)

    def request_rate(self):
        return self._recorder.rate()

    def request_details(self):
        return self._recorder.details()

    def request_averages(self):
        return self._recorder.averages()

    def shutdown(self, grace = 0, stop = 30):
        """shutdown

        Call me to stop serving new requests and shutdown as soon
        as possible.
        """
        if self._exit:
            return None

        self._graceperiod = grace
        self._stoptime    = stop
        self._exit        = True

        if hasattr(self.socket, 'wake'):
            return self.socket.wake()

    def get_name(self):
        return '%s.%s' % (
            self.__class__.__module__,
            self.__class__.__name__)

    def traceback(self):
        super(HttpServer, self).traceback()

        if self._tbrec is None:
            return None

        self._tbrec.record(name = self.get_name())
#
# standalone test interface
#
def run(port, log, loglevel, access, root, backport):
    #
    # webserver and handler
    server = HttpServer(
        log = log, args=(('0.0.0.0', port),), kwargs={'logfile': access})
    handler = HttpFileHandler(root)
    server.push_handler(handler)
    server.set_log_level(loglevel)
    server.start()
    #
    # backdoor
    bdserv = backdoor.BackDoorServer(kwargs = {'port': backport})
    bdserv.start()
    #
    # primary event loop.
    coro.event_loop()
    #
    # never reached...
    return None

LOG_FRMT = '[%(name)s|%(coro)s|%(asctime)s|%(levelname)s] %(message)s'
LOGLEVELS = dict(
    CRITICAL=logging.CRITICAL, DEBUG=logging.DEBUG, ERROR=logging.ERROR,
    FATAL=logging.FATAL, INFO=logging.INFO, WARN=logging.WARN,
    WARNING=logging.WARNING)

COMMAND_LINE_ARGS = [
    'help', 'fork', 'port=', 'accesslog=', 'backdoor=', 'logfile=',
    'loglevel=', 'root=']

def usage(name, error = None):
    if error:
        print 'Error:', error
    print "  usage: %s [options]" % name

def main(argv, environ):
    progname = sys.argv[0]

    backport = 9876
    mainport = 7221
    accesslog = None
    logfile = None
    loglevel = 'INFO'
    dofork = False
    forklist = [progname]
    smap = []
    docroot = '/Library/WebServer/Documents'

    dirname  = os.path.dirname(os.path.abspath(progname))
    os.chdir(dirname)

    try:
        list, args = getopt.getopt(argv[1:], [], COMMAND_LINE_ARGS)
    except getopt.error, why:
        usage(progname, why)
        return None

    for (field, val) in list:
        if field == '--help':
            usage(progname)
            return None
        elif field == '--backdoor':
            backport = int(val)
        elif field == '--port':
            mainport = int(val)
        elif field == '--accesslog':
            accesslog = val
        elif field == '--logfile':
            logfile = val
        elif field == '--loglevel':
            loglevel = val
        elif field == '--root':
            docroot = val
        elif field == '--fork':
            dofork = True
            continue

        forklist.append(field)
        if val:
            forklist.append(val)

    if dofork:
        pid = os.fork()
        if pid:
            return
        else:
            os.execvpe(progname, forklist, environ)

    if logfile:
        hndlr = logging.FileHandler(logfile)

        os.close(sys.stdin.fileno())
        os.close(sys.stdout.fileno())
        os.close(sys.stderr.fileno())
    else:
        hndlr = logging.StreamHandler(sys.stdout)

    log = coro.coroutine_logger('corohttpd')
    fmt = logging.Formatter(LOG_FRMT)

    log.setLevel(logging.DEBUG)

    sys.stdout = coro.coroutine_stdout(log)
    sys.stderr = coro.coroutine_stderr(log)

    hndlr.setFormatter(fmt)
    log.addHandler(hndlr)
    loglevel = LOGLEVELS.get(loglevel, None)
    if loglevel is None:
        log.warn('Unknown logging level, using INFO: %r' % (loglevel, ))
        loglevel = logging.INFO

    run(mainport, log, loglevel, accesslog, docroot, backport)
    return None

if __name__ == '__main__':
    main(sys.argv, os.environ)


########NEW FILE########
__FILENAME__ = coromysql
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 1999 eGroups, Inc.
# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Note: this should be split into two modules, one which is unaware of
# the distinction between blocking and coroutine sockets.

# Strategies:
#   1) Simple; schedule at the socket level.
#      Just like the mysql client library, when a coroutine accesses
#        the mysql client object, it will automatically detach when
#        the socket gets EWOULDBLOCK.
#   2) Smart; schedule at the request level.
#      Use a separate coroutine to manage the mysql connection.
#      A client coroutine will resume when a response is available.
#   3) Sophisticated; schedule at the row level.
#      Allow a client coroutine to peel off rows one at a time.
#
#
# Currently I am trying to emulate MySQLmodule.c as closely as possible
# so it can be used as a drop-in replacement, from Mysqldb.py and up., If
# all the commands are not there, they are being added on an as needed
# basis.
#
# The one place where the stradegy takes a different route than the module
# is auto reconnects. The module does not perform auto reconnect, so it is
# left to higher layers like Mysqldb.py, which uses sleep. Unfortunatly
# regular sleep will block an entire process. (bad) So we are adding
# auto-reconnect to this module. -Libor 10/10/99
#

## dp 8/17/05
## Fool the mysql module by matching its version info.
version_info = (1, 2, 0, "final", 1)
#
# Use the original mysql c module for some things
#
import _mysql as origmysqlc

version_info = origmysqlc.version_info

import types
import exceptions
import operator
import math
import socket
import string
import struct
import sys
import sha
import array
import time
import select

import coro

from coromysqlerr import *
#
# performance improvements used by the fast connection
#
try:
    import mysqlfuncs
except:
    mysqlfuncs = None

def log(msg):
    sys.stderr.write(msg + '\n')

MAX_RECONNECT_RETRY   = 1
RECONNECT_RETRY_GRAIN = 0.1
DEFAULT_RECV_SIZE     = 256 *1024
MYSQL_HEADER_SIZE     = 0x4

SEND_BUF_SIZE  = 256*1024
RECV_BUF_SIZE  = 256*1024

CHECK_MASK = select.POLLIN|select.POLLERR|select.POLLHUP|select.POLLNVAL

class MySQLError(exceptions.StandardError):
    pass
class Warning(exceptions.Warning, MySQLError):
    pass
class Error(MySQLError):
    pass
class InterfaceError(Error):
    pass
class DatabaseError(Error):
    pass
class DataError(DatabaseError):
    pass
class OperationalError(DatabaseError):
    pass
class IntegrityError(DatabaseError):
    pass
class InternalError(DatabaseError):
    pass
class ProgrammingError(DatabaseError):
    pass
class NotSupportedError(DatabaseError):
    pass

class error(MySQLError):
    pass
class NetworkError(MySQLError):
    pass

def error_to_except(merr):
    if not merr:
        return InterfaceError

    if merr > CR_MAX_ERROR:
        return InterfaceError

    if merr in [
        CR_COMMANDS_OUT_OF_SYNC,
        ER_DB_CREATE_EXISTS,
        ER_SYNTAX_ERROR,
        ER_PARSE_ERROR,
        ER_NO_SUCH_TABLE,
        ER_WRONG_DB_NAME,
        ER_WRONG_TABLE_NAME,
        ER_FIELD_SPECIFIED_TWICE,
        ER_INVALID_GROUP_FUNC_USE,
        ER_UNSUPPORTED_EXTENSION,
        ER_TABLE_MUST_HAVE_COLUMNS,
        ER_CANT_DO_THIS_DURING_AN_TRANSACTION]:
        return ProgrammingError

    if merr in [
        ER_DUP_ENTRY,
        ER_DUP_UNIQUE,
        ER_PRIMARY_CANT_HAVE_NULL]:
        return IntegrityError

    if merr in [ER_WARNING_NOT_COMPLETE_ROLLBACK]:
        return NotSupportedError

    if merr < 1000:
        return InternalError
    else:
        return OperationalError

# ===========================================================================
#                           Authentication
# ===========================================================================
#
# switching to 4.1 password/handshake.
#
# mysql-4.1.13a/libmysql/password.c
#
#  SERVER:  public_seed=create_random_string()
#           send(public_seed)
#
#  CLIENT:  recv(public_seed)
#           hash_stage1=sha1("password")
#           hash_stage2=sha1(hash_stage1)
#           reply=xor(hash_stage1, sha1(public_seed,hash_stage2)
#           send(reply)
#
#  SERVER:  recv(reply)
#           hash_stage1=xor(reply, sha1(public_seed,hash_stage2))
#           candidate_hash2=sha1(hash_stage1)
#           check(candidate_hash2==hash_stage2)

def scramble (message, password):
    hash_stage1 = sha.new(password).digest()
    hash_stage2 = sha.new(hash_stage1).digest()
    hash_stage2 = sha.new(message + hash_stage2).digest()

    reply = ''
    while hash_stage1 and hash_stage2:
        reply = reply + chr(ord(hash_stage1[0]) ^ ord(hash_stage2[0]))
        hash_stage1 = hash_stage1[1:]
        hash_stage2 = hash_stage2[1:]

    return reply
# ===========================================================================
#                           Packet Protocol
# ===========================================================================

def unpacket (p):
    # 3-byte length, one-byte packet number, followed by packet data
    a,b,c,s = map (ord, p[:4])
    l = a | (b << 8) | (c << 16)
    # s is a sequence number

    return l, s

def packet(data, s = 0):
    return struct.pack('<i', len(data) | s << 24) + data

def n_byte_num (data, n, pos=0):
    result = 0
    for i in range(n):
        result = result | (ord(data[pos+i])<<(8*i))

    return result

def decode_length (data):
    n = ord(data[0])

    if n < 251:
        return n, 1
    elif n == 251:
        return 0, 1
    elif n == 252:
        return n_byte_num (data, 2, 1), 3
    elif n == 253:
        # documentation says 32 bits, but wire decode shows 24 bits.
        # (there is enough padding on the wire for 32, but lets stick
        #  to 24...) Rollover to 254 happens at 24 bit boundry.
        return n_byte_num (data, 3, 1), 4
    elif n == 254:
        return n_byte_num (data, 8, 1), 9
    else:
        raise DataError, ('unexpected field length', n)

# used to generate the dumps below
def dump_hex (s):
    r1 = []
    r2 = []

    for ch in s:
        r1.append (' %02x' % ord(ch))
        if (ch in string.letters) or (ch in string.digits):
            r2.append ('  %c' % ch)
        else:
            r2.append ('   ')

    return string.join (r1, ''), string.join (r2, '')
# ===========================================================================
# generic utils
# ===========================================================================
def is_disconnect(reason):
    lower = string.lower(repr(reason.args))
    if string.find(lower, "lost connection") != -1:
        return 1

    if string.find(lower, "no connection") != -1:
        return 1

    if string.find(lower, "server has gone away") != -1:
        return 1

    return 0

def handle_error_sanely(cursor, errclass, errargs):
    raise

class connection(object):
    server_capabilities = 0

    def __init__ (self, **kwargs):
        self.username = kwargs.get('user',   '')
        self.password = kwargs.get('passwd', '')

        self.addresses = [(
            socket.AF_INET,
            (kwargs.get('host', '127.0.0.1'), kwargs.get('port', 3306)))]

        if kwargs.get('host') == 'localhost':
            self.addresses.append((socket.AF_UNIX, '/tmp/mysql.sock'))

        self._database = kwargs.get('db', '')
        self._init_cmd = kwargs.get('init_command', None)

        self._debug = kwargs.get('debug', 0) or (coro.current_id() < 0)

        self._connect_timeout = kwargs.get('connect_timeout', None)
        self._timeout         = kwargs.get('timeout', None)

        self._connected   = 0
        self._server_info = ''
        self._recv_buffer = ''

        self._rbuf = ''
        self._rlen = 0
        self._roff = 0
        self._rpac = []

        self._latest_fields = []
        self._latest_rows   = []
        self._nfields       = 0
        self._affected      = 0
        self._insert_id     = 0
        self._warning_count = 0
        self._message       = None

        self.socket = None
        self._lock  = 0

        self._reconnect_cmds = 0
        self._reconnect_exec = 0
        self._reconnect_maxr = MAX_RECONNECT_RETRY

        if not self._debug:
            self._timer_cond = coro.coroutine_cond()
            self._lock_cond  = coro.coroutine_cond()

        self.converter = {}
        self.errorhandler = handle_error_sanely

        from MySQLdb import converters
        from weakref import proxy

        self.charset = self.character_set_name().split('_')[0]

        self.converter = converters.conversions.copy()
        self.converter[types.StringType]  = self.string_literal
        self.converter[types.UnicodeType] = self.unicode_literal
        #
        # preconverter set by upper layer, blech, use it for string types.
        #
        self._preconv = kwargs.get('conv', None)
        #
        # check switch for C implementation.
        #
        if kwargs.get('fast', False) and mysqlfuncs:
            self.read_packet = self._fast_read_packet
            self.cmd_query   = self._fast_cmd_query

        return None

    def __del__(self):
        self._close()

    def handle_error_sanely(self, self2, errclass, errargs):
        raise

    def sleep(self, *args, **kwargs):
        if self._debug:
            return apply(time.sleep, args, kwargs)
        else:
            return apply(self._timer_cond.wait, args, kwargs)

    def make_socket(self, *args, **kwargs):
        if self._debug:
            return apply(socket.socket, args, kwargs)
        else:
            return apply(coro.make_socket, args, kwargs)

    def lock_wait(self, *args, **kwargs):
        if not self._debug:
            return apply(self._lock_cond.wait, args, kwargs)

    def lock_wake(self, *args, **kwargs):
        if not self._debug:
            return apply(self._lock_cond.wake_one, args, kwargs)

    def lock_waiting(self):
        if not self._debug:
            return len(self._lock_cond)
        else:
            return 0

    def _lock_connection(self):

        while self._lock:
            self.lock_wait()

        self._lock = 1
        return None

    def _unlock_connection(self):
        waiting = self.lock_waiting()

        self._lock = 0
        self.lock_wake()
        #
        # yield to give someone else a chance
        #
        if waiting:
            self.sleep(0.0)

    def _close(self):
        if self.socket is not None:
            self.socket.close()

        self._server_info = ''
        self._connected   = 0

        self._rbuf = ''
        self._rlen = 0
        self._roff = 0
        self._rpac = []

        self.address = None
        self.socket  = None

    def close(self):
        if self._connected:
            self.cmd_quit()

        self._close()

    def _connect(self):
        self.socket  = None
        self.address = None

        sock = None

        for family, addr in self.addresses:
            try:
                sock = self.make_socket(family, socket.SOCK_STREAM)
                sock.settimeout(self._connect_timeout)

                sock.connect(addr)
            except (socket.error, coro.TimeoutError):
                sock = None
            else:
                break

        if sock is None:
            raise NetworkError(
                CR_CONNECTION_ERROR,
                'Can not connect to MySQL server')

        self.address = addr
        self.socket  = sock
        self.socket.settimeout(self._timeout)
        self.socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        self.socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_SNDBUF,
            SEND_BUF_SIZE)
        self.socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_RCVBUF,
            RECV_BUF_SIZE)

        self._rbuf = ''
        self._rlen = 0
        self._roff = 0
        self._rpac = []

        return None

    def ping(self):
        pass

    def commit(self):
        self.cmd_query('COMMIT')

    def rollback(self):
        self.cmd_query('ROLLBACK')

    def _check(self):
        #
        # Perform a non-blocking poll on the socket to determine if there
        # is an error/read readiness event waiting. If there is, then
        # attempt to read into the internal connection buffer and handle
        # the error occordingly.
        #
        # In normal operation we only expect readiness in the uncommon
        # error case, normally there should be nothing (e.g. FIN) there.
        #
        p = select.poll()
        p.register(self.socket, CHECK_MASK)

        if not p.poll(0.0):
            return None

        try:
            self.recv()
        except NetworkError:
            raise NetworkError(
                    CR_SERVER_GONE_ERROR,
                    'MySQL server has gone away')

    def recv(self):
        try:
            data = self.socket.recv(DEFAULT_RECV_SIZE)
        except (socket.error, coro.TimeoutError):
            data = ''

        if not data:
            raise NetworkError(
                CR_SERVER_LOST,
                'Lost connection to MySQL server during query')

        if self._rbuf:
            self._rbuf += data
        else:
            self._rbuf  = data

    def write (self, data):
        while data:
            try:
                n = self.socket.send(data)
            except (socket.error, coro.TimeoutError):
                n = 0

            if not n:
                raise NetworkError(
                    CR_SERVER_GONE_ERROR,
                    'MySQL server has gone away')

            data = data[n:]

    def send_packet(self, data, sequence=0):
        self.write(packet(data, sequence))

    def read_packet(self):
        while not self._rpac:
            self.recv()
            self.rrip()

        return self._rpac.pop(0)

    def rrip(self):
        off = 0

        while len(self._rbuf) > off:
            #
            # header
            #
            if (len(self._rbuf) - off) < MYSQL_HEADER_SIZE:
                break
            #
            # 3-byte length, one-byte packet number, followed by packet data
            #
            val = struct.unpack('<i', self._rbuf[off:off + 4])[0]
            size, seq = (val & 0xFFFFFF, val >> 24)
            off += MYSQL_HEADER_SIZE
            #
            # body
            #
            if (len(self._rbuf) - off) < size:
                off -= MYSQL_HEADER_SIZE
                break
            #
            # now we have at least one packet
            #
            self._rpac.append(self._rbuf[off:off + size])
            off += size

        self._rbuf  = self._rbuf[off:]

    def _login (self):
        data = self.read_packet()
        #
        # unpack the greeting
        protocol_version = ord(data[:1])
        data = data[1:]

        eos = string.find (data, '\00')
        mysql_version = data[:eos]
        data = data[eos + 1:]

        thread_id = n_byte_num(data, 4)
        data = data[4:]

        challenge = data[:8]
        data = data[8:]
        data = data[1:] # filler

        capability = data[:2]
        data = data[2:]

        server_language = data[:1]
        data = data[1:]

        server_status = data[:2]
        data = data[2:]
        data = data[13:] # filler

        challenge = challenge + data[:12]
        data = data[12:]

        if self.password:
            auth = scramble(challenge, self.password)
        else:
            auth = ''
        # 2 bytes of client_capability
        # 3 bytes of max_allowed_packet
        # no idea what they are

        lp = (
            '\x0d\x86\x03\x00' +  # Client Flags
            '\x00\x00\x00\x01' +      # Max Packet Size
            server_language +         # Charset Number
            ('\00' * 23) +            # Filler
            self.username + '\00' +   # username
            chr(len(auth)) + auth +   # scramble buffer
            self._database + '\00')   # database name

        # seems to require a sequence number of one
        self.send_packet (lp, 1)
        #
        # read the response, which will check for errors
        #
        response_tuple = self.read_reply_header()
        if response_tuple != (0, 0, 0, 0):
            raise InternalError, 'unknow header response: <%s>' % \
                (repr(response_tuple))

        self._server_info = mysql_version

        #
        # mark that we are now connected
        #
        return None

    def check_connection(self):
        if self._connected:
            return None

        self._connect()
        self._login()

        if self._database is not None:
            self.cmd_use(self._database)

        if self._init_cmd is not None:
            self.cmd_query(self._init_cmd)

        self._connected = 1

    def command(self, command_type, command):
        q = chr(decode_db_cmds[command_type]) + command
        self.send_packet (q, 0)

    def unpack_len (self, d):
        if ord(d[0]) > 250:
            fl, sc = decode_length (d)
        else:
            fl, sc = (ord(d[0]), 1)

        return fl, sc

    def unpack_data (self, d):
        r = []
        while len(d):
            fl, sc = self.unpack_len(d)

            r.append (d[sc:sc+fl])
            d = d[sc+fl:]

        return r

    def unpack_field (self, d):
        r = []

        for name, size in decode_pos_field:
            if not len(d):
                raise InternalError, 'No data before all fields processed.'

            if size == -1:
                fl, sc = self.unpack_len(d)

                r.append(d[sc:sc+fl])
                d = d[sc+fl:]
            else:
                r.append(d[:size])
                d = d[size:]

        # 4.1 has an optional default field
        if len(d):
            fl, sc = self.unpack_len(d)

            r.append(d[sc:sc+fl])
            d = d[sc+fl:]

        if len(d):
            raise InternalError, 'Still have data, but finished parsing.'

        return r

    def unpack_int(self, data_str):

        if len(data_str) > 4:
            raise TypeError, 'data too long for an int32: <%d>' % len(data_str)

        value = 0

        while len(data_str):

            i = ord(data_str[len(data_str)-1])
            data_str = data_str[:len(data_str)-1]

            value = value + (i << (8 * len(data_str)))

        return value

    def read_field_packet(self):
        #
        # handle the generic portion for all types of result packets
        #
        data = self.read_packet()
        if data[0] < '\xfe':
            return data

        if data[0] == '\xfe':
            # more data in 4.1:
            # 2 bytes - warning_count
            # 2 bytes - server_status
            return None
        #
        # data[0] == 0xFF
        #
        error_num = ord(data[1]) + (ord(data[2]) << 8)
        error_msg = data[3:]

        raise error_to_except(error_num), (error_num, error_msg)

    def read_reply_header(self):
        #
        # read in the reply header and return the results.
        #
        data = self.read_field_packet()
        if data is None:
            raise InternalError, 'unexpected EOF in header'

        rows_in_set = 0
        affected_rows = 0
        insert_id = 0
        warning_count = 0
        server_status = None

        rows_in_set, move = decode_length(data)
        data = data[move:]

        if len(data):

            affected_rows, move = decode_length(data)
            data = data[move:]
            insert_id, move     = decode_length(data)
            data = data[move:]

            server_status, warning_count = struct.unpack('<2sh', data[:4])
            data = data[4:]
        #
        # save the remainder as the message
        #
        self._message = data

        return rows_in_set, affected_rows, insert_id, warning_count
    #
    # Internal mysql client requests to get raw data from db (cmd_*)
    #
    def cmd_use(self, database):
        self.command('init_db', database)

        rows, affected, insert_id, warning_count = self.read_reply_header()

        if rows != 0 or affected != 0 or insert_id != 0:
            msg = 'unexpected header: <%d:%d:%d>' % (rows, affected, insert_id)
            raise InternalError, msg

        self._database = database
        return None

    def cmd_query(self, query):
        #print 'coro mysql query: "%s"' % (repr(query))
        self.command('query', query)
        #
        # read in the header
        #
        (self._nfields,
         self._affected,
         self._insert_id,
         self._warning_count) = self.read_reply_header()

        self._latest_fields = []
        self._latest_rows   = []

        if not self._nfields:
            return 0 #statement([], [], affected, insert_id)

        decoders = range(self._nfields)
        fields = []
        i = 0

        # read column data.
        while 1:
            data = self.read_field_packet()
            if data is None:
                break

            field = self.unpack_field (data)
            type  = ord(field[decode_field_pos['type']])
            flags = struct.unpack('H', field[decode_field_pos['flags']])[0]

            field[decode_field_pos['type']]  = type
            field[decode_field_pos['flags']] = flags

            decoders[i] = (
                decode_type_map[type],
                flags,
                self._preconv.get(type, None))

            fields.append(field)

            i = i + 1

        if len(fields) != self._nfields:
            raise InternalError, "number of fields did not match"

        # read rows
        rows = []
        field_range = range(self._nfields)

        while 1:
            data = self.read_field_packet()
            if data is None:
                break

            row = self.unpack_data (data)
            #
            # cycle through all fields in the row appling decoders
            #
            for i in field_range:
                decode, flags, preconv = decoders[i]
                #
                # find preconverter if it exists and is a sequence. This
                # is field dependent
                #
                if operator.isSequenceType(preconv):
                    func = None

                    for mask, p in preconv:
                        if mask is None or mask & flags:
                            func = p
                            break
                else:
                    func = preconv
                #
                # call decoder
                #
                row[i] = decode(row[i], flags, func)
            #
            # save entire decoded row
            #

            rows.append(row)

        self._latest_fields = fields
        self._latest_rows = rows
        return len(rows) # statement(fields, rows)

    def cmd_quit(self):
        self.command('quit', '')
        #
        # no reply!
        #
        return None

    def cmd_shutdown(self):
        self.command('shutdown', '')

        data = self.read_field_packet()
        print "shutdown: data: <%s>" % (repr(data))

        return None

    def cmd_drop(self, db_name):
        self.command('drop_db', db_name)

        (self._nfields,
         self._affected,
         self._insert_id,
         self._warning_count) = self.read_reply_header()
        return None

    def cmd_listfields(self, cmd):
        self.command('field_list', cmd)

        rows = []
        #
        # read data line until we get 255 which is error or 254 which is
        # end of data ( I think :-)
        #
        while 1:

            data = self.read_field_packet()
            if data is None:
                return rows

            row = self.unpack_data(data)

            table_name = row[0]
            field_name = row[1]
            field_size = self.unpack_int(row[2])
            field_type = decode_type_names[ord(row[3])]
            field_flag = self.unpack_int(row[4])
            field_val  = row[5]

            flag = ''

            if field_flag & decode_flag_value['pri_key']:
                flag = flag + decode_flag_name['pri_key']
            if field_flag & decode_flag_value['not_null']:
                flag = flag + ' ' + decode_flag_name['not_null']
            if field_flag & decode_flag_value['unique_key']:
                flag = flag + ' ' + decode_flag_name['unique_key']
            if field_flag & decode_flag_value['multiple_key']:
                flag = flag + ' ' + decode_flag_name['multiple_key']
            if field_flag & decode_flag_value['auto']:
                flag = flag + ' ' + decode_flag_name['auto']
            #
            # for some reason we do not pass back the default value (row[5])
            #
            rows.append([field_name, table_name, field_type,
                         field_size, flag])

        return None

    def cmd_create(self, name):
        self.command('create_db', name)
        #
        # response
        #
        (self._nfields,
         self._affected,
         self._insert_id,
         self._warning_count) = self.read_reply_header()
        return None

    def reconnect_cmds(self, value):
        '''reconnect_cmds

        Assign the number of DB commands which will have reconnect retry
        enabled and reset the counter of commands executed towards this
        counter back to 0. To set the actual number of retries use
        reconnect_retry_set()

        The value is the number of commands for which retry will be
        enabled. (default: 0) The value None indicates no limit.

        NOTE: The reason for the existence of this method is that once
              a transaction has begun auto-reconnect can lead to results
              that are inconsistent. If auto-reconnect is desired with a
              connection then it should only be enabled for the first
              command.
        '''
        self._reconnect_cmds = value
        self._reconnect_exec = 0

    def reconnect_retry_set(self, value = MAX_RECONNECT_RETRY):
        '''reconnect_retry_set

        Set the max reconnect retry count. Once a transaction has begun
        this must be set to 0 to ensure correctness.
        '''
        self._reconnect_maxr = value

    def _reconnect_retry(self):
        if self._reconnect_cmds is None:
            return self._reconnect_maxr

        if self._reconnect_cmds > self._reconnect_exec:
            return self._reconnect_maxr

        return 0

    def _reconnect_check(self, retry_count):
        #
        # for now only check when reconnect is enabled, but
        # check might make sense in all cases, and reraise
        # when reconnect has run out...
        #
        if not retry_count < self._reconnect_retry():
            return False

        try:
            self._check()
        except NetworkError, e:
            self._close()
            #
            # we only attempt reconnect on write errors to the
            # server. (basically stale/dead connection) read
            # errors need to be propagated to the consumer.
            #
            if e[0] != CR_SERVER_GONE_ERROR:
                raise e
        else:
            return False
        #
        # network error. close, sleep and retry
        #
        self._close()

        sleep_time = retry_count * RECONNECT_RETRY_GRAIN

        coro.log.info('<%r> lost connection, sleeping <%0.1f>' % (
            self.address, sleep_time))

        self.sleep(sleep_time)
        return True

    def _execute_with_retry(self, method_name, args = ()):
        retry_count = 0
        #
        # lock down the connection while we are performing a query.
        #
        self._lock_connection()

        try:
            while True:
                try:
                    self.check_connection()
                except NetworkError, e:
                    self._close()
                    raise e

                if self._reconnect_check(retry_count):
                    retry_count += 1
                    continue

                try:
                    return apply(getattr(self, method_name), args)
                except IntegrityError, e:
                    raise e
                except ProgrammingError, e:
                    raise e
                except exceptions.Exception, e:
                    self._close()
                    raise e
        finally:
            #
            # unlock the connection 
            self._unlock_connection()
            #
            # Increment the number of commands executed.
            self._reconnect_exec += 1
    #
    # MySQL module compatibility, properly wraps raw client requests,
    # to format the return types.
    #
    # use_result option is currently not implemented, if anyone has the
    # time, please add support for it. Libor 4/2/00
    #
    def selectdb(self, database, use_result = 0):
        return self._execute_with_retry('cmd_use', (database,))

    def query (self, q, use_result = 0):
        return self._execute_with_retry('cmd_query', (q,))

    def listtables (self, wildcard = None):
        if wildcard is None:
            cmd = "show tables"
        else:
            cmd = "show tables like '%s'" % (wildcard)

        o = self._execute_with_retry('cmd_query', (cmd,))
        return o.fetchrows()

    def listfields (self, table_name, wildcard = None):
        if wildcard is None:
            cmd = "%s\000\000" % (table_name)
        else:
            cmd = "%s\000%s\000" % (table_name, wildcard)

        return self._execute_with_retry('cmd_listfields', (cmd,))

    def drop(self, database, use_result = 0):
        return self._execute_with_retry('cmd_drop', (database,))

    def create(self, db_name, use_result = 0):
        return self._execute_with_retry('cmd_create', (db_name,))

    def character_set_name(self):
        return 'utf8'

    def next_result(self):
        return -1

    def store_result(self):
        value = statement(
            self,
            self._latest_fields,
            self._latest_rows,
            self._affected,
            self._insert_id)
        return value

    def affected_rows(self):
        return len(self._latest_rows) or self._affected

    def insert_id(self):
        return self._insert_id

    def info(self):
        return self._message

    def warning_count(self):
        # return self._warning_count
        return 0

    def escape(self, o, converter):
        return origmysqlc.escape(o, self.converter)

    def string_literal(self, obj, dummy=None):
        return origmysqlc.string_literal(obj)

    def unicode_literal(self, obj, dummy=None):
        return self.string_literal(obj.encode(self.charset))

    def get_server_info(self):
        try:
            self.check_connection()
        except NetworkError, e:
            raise error_to_except(e[0]), e.args
        return self._server_info
    #
    # Fast Option
    #
    def _fast_read_packet(self):
        while not self._rpac:
            self.recv()
            self._rpac = mysqlfuncs.rip_packets(self._rbuf)

        return self._rpac.pop(0)

    def _fast_cmd_query(self, query):
        self.command('query', query)
        #
        # read in the header
        #
        (self._nfields,
         self._affected,
         self._insert_id,
         self._warning_count) = self.read_reply_header()

        self._latest_fields = []
        self._latest_rows   = []

        if not self._nfields:
            return 0 # statement([], [], affected, insert_id)

        fields = []
        rows   = []
        #
        # read column data.
        #
        while 1:
            data = self.read_field_packet()
            if data is None:
                break

            fields.append(mysqlfuncs.unpack_field(data))

        if len(fields) != self._nfields:
            raise InternalError, "number of fields did not match"
        #
        # read rows
        #
        while 1:
            data = self.read_field_packet()
            if data is None:
                break

            rows.append(mysqlfuncs.unpack_data(data, fields))
            #
            # cycle through all fields in the row appling decoders
            #
            # for i in xrange(self._nfields):
            #    field   = fields[i]
            #    decode  = decode_type_map[field[9]]
            #    flags   = field[10]
            #    preconv = self._preconv.get(field[9])
            #    #
            #    # find preconverter if it exists and is a sequence. This
            #    # is field dependent
            #    #
            #    if operator.isSequenceType(preconv):
            #        func = None

            #        for mask, p in preconv:
            #            if mask is None or mask & flags:
            #                func = p
            #                break
            #    else:
            #        func = preconv
            #    #
            #    # call decoder
            #    #
            #    row[i] = decode(row[i], flags, func)

        self._latest_fields = fields
        self._latest_rows = rows
        return len(rows) # statement(fields, rows)


class statement(object):
    def __init__ (self, db, fields, rows, affected_rows = -1, insert_id = 0):
        self._fields = fields
        self._flags = []
        self._rows = rows

        if affected_rows > 0:
            self._affected_rows = affected_rows
        else:
            self._affected_rows = len(rows)

        self._index = 0
        self._insert_id = insert_id

    # =======================================================================
    # internal methods
    # =======================================================================
    def _fetchone (self):
        if self._index <  len(self._rows):
            result = self._rows[self._index]
            self._index = self._index + 1
        else:
            result = []

        return result

    def _fetchmany (self, size):
        result = self._rows[self._index:self._index + size]
        self._index = self._index + len(result)

        return result

    def _fetchall (self):
        result = self._rows[self._index:]
        self._index = self._index + len(result)

        return result
    # =======================================================================
    # external methods
    # =======================================================================
    def affectedrows (self):
        return self._affected_rows

    def numrows (self):
        return len(self._rows)

    def numfields(self):
        return len(self._fields)

    def fields (self):
        # raw format:
        # table, fieldname, ??? (flags?), datatype
        # ['groupmap', 'gid', '\013\000\000', '\003', '\013B\000']
        # MySQL returns
        # ['gid', 'groupmap', 'long', 11, 'pri notnull auto_inc mkey']

        result = []
        for field in self._fields:
            flag_list = []
            flag_value = struct.unpack(
                'H', field[decode_field_pos['flags']])[0]

            for value, name in decode_flag.items():
                if 0 < value & flag_value:
                    flag_list.append(name)

            self._flags = flag_list

            type = field[decode_field_pos['type']]

            result.append(
                [field[decode_field_pos['table']],
                 field[decode_field_pos['name']],
                 decode_type_names[ord(type)],
                 string.join(flag_list)])

        return result

    def fetch_row(self, size, fetch_type):
        #The rows are formatted according to how:
        #  0 -- tuples (default)
        #  1 -- dictionaries, key=column or table.column if duplicated
        #  2 -- dictionaries, key=table.column
        if fetch_type:
            raise InternalError, 'unsupported row result type: %d' % fetch_type

        if size:
            value = self._fetchmany(size)
        else:
            value = self._fetchall()

        return tuple(map(lambda x: tuple(x), value))

    def fetchrows(self, size = 0):
        if size:
            return self._fetchmany(size)
        else:
            return self._fetchall()

    # [{'groupmap.podid': 2,
    #   'groupmap.listname': 'medusa',
    #   'groupmap.active': 'y',
    #   'groupmap.gid': 116225,
    #   'groupmap.locked': 'n'}]
    def fetchdict (self, size = 0):
        result = []
        keys = []

        for field in self._fields:
            keys.append('%s.%s' % (field[decode_field_pos['table']],
                                   field[decode_field_pos['name']]))

        range_len_keys = range(len(keys))
        for row in self.fetchrows(size):

            d = {}
            for j in range_len_keys:
                d[keys[j]] = row[j]

            result.append(d)

        return result

    def insert_id (self):
        # i have no idea what this is
        return self._insert_id

    def describe(self):
        # http://www.python.org/peps/pep-0249.html
        # (name, type_code, display_size, internal_size, precision, scale,
        #  null_ok). The first two items (name and type_code) are mandatory.
        return tuple(map(
            lambda x: (x[4], x[9], None, None, None, None, None),
            self._fields))

    def field_flags(self):
        return self._flags

# ======================================================================
# decoding MySQL data types
# ======================================================================

def _is_flag_notnull(f):
    return 0 < (f & decode_flag_value['not_null'])

_is_flag_notnull = lambda f: bool(f & decode_flag_value['not_null'])
_is_flag_notnull = lambda f: bool(f & 1)

# decode string as int, unless string is empty.
def _null_int(s, f, p = None):
    if len(s):
        return int(s)
    else:
        return None

def _null_float(s, f, p = None):
    if len(s):
        return float(s)
    else:
        return None

# decode string as long, unless string is empty.
def _null_long(s, f, p = None):
    if len(s):
        return long(s)
    else:
        return None

def _array_str(s, f, p = None):
    return array.array('c', s)

def _null_str(s, f, p = None):
    if s:
        if p:
            return p(s)
        else:
            return s

    if _is_flag_notnull(f):
        return ''
    else:
        return None

# by default leave as a string
decode_type_map = [_null_str] * 256
decode_type_names = ['unknown'] * 256

# Many of these are not correct!  Note especially
# the time/date types... If you want to write a real decoder
# for any of these, just replace 'str' with your function.

for code, cast, name in (
    (0x00,    _null_int,    'decimal'),
    (0x01,    _null_int,    'tiny'),
    (0x02,    _null_int,    'short'),
    (0x03,    _null_long,   'long'),
    (0x04,    _null_float,  'float'),
    (0x05,    _null_float,  'double'),
    (0x06,    _null_str,    'null'),
    (0x07,    _null_str,    'timestamp'),
    (0x08,    _null_long,   'longlong'),
    (0x09,    _null_int,    'int24'),
    (0x0A,    _null_str,    'date'),       # unsure handling...
    (0x0B,    _null_str,    'time'),       # unsure handling...
    (0x0C,    _null_str,    'datetime'),   # unsure handling...
    (0x0D,    _null_str,    'year'),       # unsure handling...
    (0x0E,    _null_str,    'newdate'),    # unsure handling...
    (0x0F,    _null_str,    'varchar'),    # unsure handling... MySQL 5.0
    (0x10,    _null_str,    'bit'),        # unsure handling... MySQL 5.0
    (0xF6,    _null_str,    'newdecimal'), # unsure handling... MySQL 5.0
    (0xF7,    _null_str,    'enum'),       # unsure handling...
    (0xF8,    _null_str,    'set'),        # unsure handling...
    (0xF9,    _null_str,    'tiny_blob'),
    (0xFA,    _null_str,    'medium_blob'),
    (0xFB,    _null_str,    'long_blob'),
    (0xFC,    _null_str,    'blob'),
    (0xFD,    _null_str,    'var_string'), # in the C code it is VAR_STRING
    (0xFE,    _null_str,    'string'),
    (0xFF,    _null_str,    'geometry')    # unsure handling...
    ):
    decode_type_map[code] = cast
    decode_type_names[code] = name
#
# we need flag mappings also
#
decode_flag_value = {}
decode_flag_name  = {}
decode_flag       = {}

for value, flag, name in (
    (1,     'not_null',      'notnull'),  # Field can not be NULL
    (2,     'pri_key',       'pri'),      # Field is part of a primary key
    (4,     'unique_key',    'ukey'),     # Field is part of a unique key
    (8,     'multiple_key',  'mkey'),     # Field is part of a key
    (16,    'blob',          'unused'),   # Field is a blob
    (32,    'unsigned',      'unused'),   # Field is unsigned
    (64,    'zerofill',      'unused'),   # Field is zerofill
    (128,   'binary',        'unused'),
    (256,   'enum',          'unused'),   # field is an enum
    (512,   'auto',          'auto_inc'), # field is a autoincrement field
    (1024,  'timestamp',     'unused'),   # Field is a timestamp
    (2048,  'set',           'unused'),   # field is a set
    (16384, 'part_key',      'unused'),   # Intern; Part of some key
    (32768, 'group',         'unused'),   # Intern: Group field
    (65536, 'unique',        'unused')    # Intern: Used by sql_yacc
    ):
    decode_flag_value[flag] = value
    decode_flag_name[flag]  = name
    decode_flag[value] = name
#
# database commands
#
decode_db_cmds = {}

for value, name in (
    (0,  'sleep'),
    (1,  'quit'),
    (2,  'init_db'),
    (3,  'query'),
    (4,  'field_list'),
    (5,  'create_db'),
    (6,  'drop_db'),
    (7,  'refresh'),
    (8,  'shutdown'),
    (9,  'statistics'),
    (10, 'process_info'),
    (11, 'connect'),
    (12, 'process_kill'),
    (13, 'debug')
    ):
    decode_db_cmds[name] = value
#
# database commands
#
decode_db_cmds = {}

for value, name in (
    (0,  'sleep'),
    (1,  'quit'),
    (2,  'init_db'),
    (3,  'query'),
    (4,  'field_list'),
    (5,  'create_db'),
    (6,  'drop_db'),
    (7,  'refresh'),
    (8,  'shutdown'),
    (9,  'statistics'),
    (10, 'process_info'),
    (11, 'connect'),
    (12, 'process_kill'),
    (13, 'debug')
    ):
    decode_db_cmds[name] = value
#
# Mysql 4.1 fields
#
decode_field_pos = {}
decode_pos_field = []

for pos, size, name in (
    (0,  -1, 'catalog'),
    (1,  -1, 'db'),
    (2,  -1, 'table'),
    (3,  -1, 'org_table'),
    (4,  -1, 'name'),
    (5,  -1, 'org_name'),
    (6,   1, '(filler 1)'),
    (7,   2, 'charset'),
    (8,   4, 'length'),
    (9,   1, 'type'),
    (10,  2, 'flags'),
    (11,  1, 'decimals'),
    (12,  1, '(filler 2)')
    ):
    decode_pos_field.append((name, size))
    decode_field_pos[name] = pos
## ======================================================================
##
## SMR - borrowed from daGADFLY.py, moved dict 'constant' out of
##       function definition.
##
quote_for_escape = {'\0': '\\0', "'": "\\'", '"': '\\"', '\\': '\\\\'}

import types

def escape(s):
    quote = quote_for_escape
    if type(s) == types.IntType:
        return str(s)
    if s == None:
        return ""
    if type(s) == types.StringType:
        r = range(len(s))
        r.reverse() # iterate backwards, so as not to destroy indexing

        for i in r:
            if quote.has_key(s[i]):
                s = s[:i] + quote[s[i]] + s[i+1:]
        return s

    log(s)
    log (type(s))
    raise MySQLError
#
# MySQL module compatibility
#
def connect (host, user, passwd, db="", timeout=None, connect_timeout=None):
    conn = connection(
        user, passwd, (host, 3306), debug=0, timeout=timeout,
        connect_timeout=connect_timeout)

    # I found that this is the best way to maximize the number of ultimately
    # successful requests if many threads (>50) are running. - martinb 99/11/03
    try:
        conn.check_connection()
    except InternalError, msg:
        pass
    return conn
#
# emulate standard MySQL calls and errors.
#
_emulate_list = [
    ('MySQL',    None),
    ('_mysql',   None),
    ('MySQLdb', 'MySQLError'),
    ('MySQLdb', 'Warning'),
    ('MySQLdb', 'Error'),
    ('MySQLdb', 'InterfaceError'),
    ('MySQLdb', 'DatabaseError'),
    ('MySQLdb', 'DataError'),
    ('MySQLdb', 'OperationalError'),
    ('MySQLdb', 'IntegrityError'),
    ('MySQLdb', 'InternalError'),
    ('MySQLdb', 'ProgrammingError'),
    ('MySQLdb', 'NotSupportedError'),
]
_original_emulate = {}
def emulate():
    "have this module pretend to be the real MySQL module"
    import MySQLdb

    # save _emulate_list
    for module, attr in _emulate_list:
        if not attr:
            _original_emulate.setdefault((module, attr), sys.modules.get(module))
            continue
        _original_emulate.setdefault(
            (module, attr),
            getattr(sys.modules[module], attr, None))

    sys.modules['MySQL'] = sys.modules[__name__]
    sys.modules['_mysql'] = sys.modules[__name__]

    sys.modules['MySQLdb'].MySQLError        = MySQLError
    sys.modules['MySQLdb'].Warning           = Warning
    sys.modules['MySQLdb'].Error             = Error
    sys.modules['MySQLdb'].InterfaceError    = InterfaceError
    sys.modules['MySQLdb'].DatabaseError     = DatabaseError
    sys.modules['MySQLdb'].DataError         = DataError
    sys.modules['MySQLdb'].OperationalError  = OperationalError
    sys.modules['MySQLdb'].IntegrityError    = IntegrityError
    sys.modules['MySQLdb'].InternalError     = InternalError
    sys.modules['MySQLdb'].ProgrammingError  = ProgrammingError
    sys.modules['MySQLdb'].NotSupportedError = NotSupportedError

def reverse():
    for module, attr in _emulate_list:
        if not attr:
            if _original_emulate.get((module, attr)):
                sys.modules[module] = _original_emulate[(module, attr)]
            continue
        if _original_emulate.get((module, attr)):
            setattr(sys.modules[module], attr, _original_emulate[(module, attr)])

def test ():
    c = connection ('rushing', 'fnord', ('127.0.0.1', 3306))
    print 'connecting...'
    c.connect()
    print 'logging in...'
    c.login()
    print c
    c.cmd_use ('mysql')
    print c.cmd_query ('select * from host')
    c.cmd_quit()

if __name__ == '__main__':
    for i in range(10):
        coro.spawn (test)
    coro.event_loop (30.0)
#
# - connection is analogous to DBH in MySQLmodule.c, and statment is
#   analogous to STH in MySQLmodule.c
# - DBH is the database handler, and STH is the statment handler,
# - Here are the methods that the MySQLmodule.c implements, and if they
#   are at least attempted here in coromysql
#
# DBH:
#
#    "selectdb"       - yes
#    "do"             - no
#    "query"          - yes
#    "listdbs"        - no
#    "listtables"     - yes
#    "listfields"     - yes
#    "listprocesses"  - no
#    "create"         - yes
#    "stat"           - no
#    "clientinfo"     - no
#    "hostinfo"       - no
#    "serverinfo"     - no
#    "protoinfo"      - no
#    "drop"           - yes
#    "reload"         - no
#    "insert_id"      - no
#    "close"          - yes
#    "shutdown"       - no
#
# STH:
#
#    "fields"         - yes
#    "fetchrows"      - yes
#    "fetchdict"      - yes
#    "seek"           - no
#    "numrows"        - yes
#    "numfields"      - yes
#    "eof"            - no
#    "affectedrows"   - yes
#    "insert_id"      - yes


## dp new stuff

string_literal = origmysqlc.string_literal
escape_sequence = origmysqlc.escape_sequence
escape_dict = origmysqlc.escape_dict
NULL = origmysqlc.NULL
get_client_info = lambda: '5.0.67-kb8'
#
# end...


########NEW FILE########
__FILENAME__ = coromysqlerr
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 1999 eGroups, Inc.
# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# ===========================================================================
#                                   Errors
# ===========================================================================
ER_HASHCHK = 1000
ER_NISAMCHK = 1001
ER_NO = 1002
ER_YES = 1003
ER_CANT_CREATE_FILE = 1004
ER_CANT_CREATE_TABLE = 1005
ER_CANT_CREATE_DB = 1006
ER_DB_CREATE_EXISTS = 1007
ER_DB_DROP_EXISTS = 1008
ER_DB_DROP_DELETE = 1009
ER_DB_DROP_RMDIR = 1010
ER_CANT_DELETE_FILE = 1011
ER_CANT_FIND_SYSTEM_REC = 1012
ER_CANT_GET_STAT = 1013
ER_CANT_GET_WD = 1014
ER_CANT_LOCK = 1015
ER_CANT_OPEN_FILE = 1016
ER_FILE_NOT_FOUND = 1017
ER_CANT_READ_DIR = 1018
ER_CANT_SET_WD = 1019
ER_CHECKREAD = 1020
ER_DISK_FULL = 1021
ER_DUP_KEY = 1022
ER_ERROR_ON_CLOSE = 1023
ER_ERROR_ON_READ = 1024
ER_ERROR_ON_RENAME = 1025
ER_ERROR_ON_WRITE = 1026
ER_FILE_USED = 1027
ER_FILSORT_ABORT = 1028
ER_FORM_NOT_FOUND = 1029
ER_GET_ERRNO = 1030
ER_ILLEGAL_HA = 1031
ER_KEY_NOT_FOUND = 1032
ER_NOT_FORM_FILE = 1033
ER_NOT_KEYFILE = 1034
ER_OLD_KEYFILE = 1035
ER_OPEN_AS_READONLY = 1036
ER_OUTOFMEMORY = 1037
ER_OUT_OF_SORTMEMORY = 1038
ER_UNEXPECTED_EOF = 1039
ER_CON_COUNT_ERROR = 1040
ER_OUT_OF_RESOURCES = 1041
ER_BAD_HOST_ERROR = 1042
ER_HANDSHAKE_ERROR = 1043
ER_DBACCESS_DENIED_ERROR = 1044
ER_ACCESS_DENIED_ERROR = 1045
ER_NO_DB_ERROR = 1046
ER_UNKNOWN_COM_ERROR = 1047
ER_BAD_NULL_ERROR = 1048
ER_BAD_DB_ERROR = 1049
ER_TABLE_EXISTS_ERROR = 1050
ER_BAD_TABLE_ERROR = 1051
ER_NON_UNIQ_ERROR = 1052
ER_SERVER_SHUTDOWN = 1053
ER_BAD_FIELD_ERROR = 1054
ER_WRONG_FIELD_WITH_GROUP = 1055
ER_WRONG_GROUP_FIELD = 1056
ER_WRONG_SUM_SELECT = 1057
ER_WRONG_VALUE_COUNT = 1058
ER_TOO_LONG_IDENT = 1059
ER_DUP_FIELDNAME = 1060
ER_DUP_KEYNAME = 1061
ER_DUP_ENTRY = 1062
ER_WRONG_FIELD_SPEC = 1063
ER_PARSE_ERROR = 1064
ER_EMPTY_QUERY = 1065
ER_NONUNIQ_TABLE = 1066
ER_INVALID_DEFAULT = 1067
ER_MULTIPLE_PRI_KEY = 1068
ER_TOO_MANY_KEYS = 1069
ER_TOO_MANY_KEY_PARTS = 1070
ER_TOO_LONG_KEY = 1071
ER_KEY_COLUMN_DOES_NOT_EXITS = 1072
ER_BLOB_USED_AS_KEY = 1073
ER_TOO_BIG_FIELDLENGTH = 1074
ER_WRONG_AUTO_KEY = 1075
ER_READY = 1076
ER_NORMAL_SHUTDOWN = 1077
ER_GOT_SIGNAL = 1078
ER_SHUTDOWN_COMPLETE = 1079
ER_FORCING_CLOSE = 1080
ER_IPSOCK_ERROR = 1081
ER_NO_SUCH_INDEX = 1082
ER_WRONG_FIELD_TERMINATORS = 1083
ER_BLOBS_AND_NO_TERMINATED = 1084
ER_TEXTFILE_NOT_READABLE = 1085
ER_FILE_EXISTS_ERROR = 1086
ER_LOAD_INFO = 1087
ER_ALTER_INFO = 1088
ER_WRONG_SUB_KEY = 1089
ER_CANT_REMOVE_ALL_FIELDS = 1090
ER_CANT_DROP_FIELD_OR_KEY = 1091
ER_INSERT_INFO = 1092
ER_UPDATE_TABLE_USED = 1093
ER_NO_SUCH_THREAD = 1094
ER_KILL_DENIED_ERROR = 1095
ER_NO_TABLES_USED = 1096
ER_TOO_BIG_SET = 1097
ER_NO_UNIQUE_LOGFILE = 1098
ER_TABLE_NOT_LOCKED_FOR_WRITE = 1099
ER_TABLE_NOT_LOCKED = 1100
ER_BLOB_CANT_HAVE_DEFAULT = 1101
ER_WRONG_DB_NAME = 1102
ER_WRONG_TABLE_NAME = 1103
ER_TOO_BIG_SELECT = 1104
ER_UNKNOWN_ERROR = 1105
ER_UNKNOWN_PROCEDURE = 1106
ER_WRONG_PARAMCOUNT_TO_PROCEDURE = 1107
ER_WRONG_PARAMETERS_TO_PROCEDURE = 1108
ER_UNKNOWN_TABLE = 1109
ER_FIELD_SPECIFIED_TWICE = 1110
ER_INVALID_GROUP_FUNC_USE = 1111
ER_UNSUPPORTED_EXTENSION = 1112
ER_TABLE_MUST_HAVE_COLUMNS = 1113
ER_RECORD_FILE_FULL = 1114
ER_UNKNOWN_CHARACTER_SET = 1115
ER_TOO_MANY_TABLES = 1116
ER_TOO_MANY_FIELDS = 1117
ER_TOO_BIG_ROWSIZE = 1118
ER_STACK_OVERRUN = 1119
ER_WRONG_OUTER_JOIN = 1120
ER_NULL_COLUMN_IN_INDEX = 1121
ER_CANT_FIND_UDF = 1122
ER_CANT_INITIALIZE_UDF = 1123
ER_UDF_NO_PATHS = 1124
ER_UDF_EXISTS = 1125
ER_CANT_OPEN_LIBRARY = 1126
ER_CANT_FIND_DL_ENTRY = 1127
ER_FUNCTION_NOT_DEFINED = 1128
ER_HOST_IS_BLOCKED = 1129
ER_HOST_NOT_PRIVILEGED = 1130
ER_PASSWORD_ANONYMOUS_USER = 1131
ER_PASSWORD_NOT_ALLOWED = 1132
ER_PASSWORD_NO_MATCH = 1133
ER_UPDATE_INFO = 1134
ER_CANT_CREATE_THREAD = 1135
ER_WRONG_VALUE_COUNT_ON_ROW = 1136
ER_CANT_REOPEN_TABLE = 1137
ER_INVALID_USE_OF_NULL = 1138
ER_REGEXP_ERROR = 1139
ER_MIX_OF_GROUP_FUNC_AND_FIELDS = 1140
ER_NONEXISTING_GRANT = 1141
ER_TABLEACCESS_DENIED_ERROR = 1142
ER_COLUMNACCESS_DENIED_ERROR = 1143
ER_ILLEGAL_GRANT_FOR_TABLE = 1144
ER_GRANT_WRONG_HOST_OR_USER = 1145
ER_NO_SUCH_TABLE = 1146
ER_NONEXISTING_TABLE_GRANT = 1147
ER_NOT_ALLOWED_COMMAND = 1148
ER_SYNTAX_ERROR = 1149
ER_DELAYED_CANT_CHANGE_LOCK = 1150
ER_TOO_MANY_DELAYED_THREADS = 1151
ER_ABORTING_CONNECTION = 1152
ER_NET_PACKET_TOO_LARGE = 1153
ER_NET_READ_ERROR_FROM_PIPE = 1154
ER_NET_FCNTL_ERROR = 1155
ER_NET_PACKETS_OUT_OF_ORDER = 1156
ER_NET_UNCOMPRESS_ERROR = 1157
ER_NET_READ_ERROR = 1158
ER_NET_READ_INTERRUPTED = 1159
ER_NET_ERROR_ON_WRITE = 1160
ER_NET_WRITE_INTERRUPTED = 1161
ER_TOO_LONG_STRING = 1162
ER_TABLE_CANT_HANDLE_BLOB = 1163
ER_TABLE_CANT_HANDLE_AUTO_INCREMENT = 1164
ER_DELAYED_INSERT_TABLE_LOCKED = 1165
ER_WRONG_COLUMN_NAME = 1166
ER_WRONG_KEY_COLUMN = 1167
ER_WRONG_MRG_TABLE = 1168
ER_DUP_UNIQUE = 1169
ER_BLOB_KEY_WITHOUT_LENGTH = 1170
ER_PRIMARY_CANT_HAVE_NULL = 1171
ER_TOO_MANY_ROWS = 1172
ER_REQUIRES_PRIMARY_KEY = 1173
ER_NO_RAID_COMPILED = 1174
ER_UPDATE_WITHOUT_KEY_IN_SAFE_MODE = 1175
ER_KEY_DOES_NOT_EXITS = 1176
ER_CHECK_NO_SUCH_TABLE = 1177
ER_CHECK_NOT_IMPLEMENTED = 1178
ER_CANT_DO_THIS_DURING_AN_TRANSACTION = 1179
ER_ERROR_DURING_COMMIT = 1180
ER_ERROR_DURING_ROLLBACK = 1181
ER_ERROR_DURING_FLUSH_LOGS = 1182
ER_ERROR_DURING_CHECKPOINT = 1183
ER_NEW_ABORTING_CONNECTION = 1184
ER_DUMP_NOT_IMPLEMENTED    = 1185
ER_FLUSH_MASTER_BINLOG_CLOSED = 1186
ER_INDEX_REBUILD  = 1187
ER_MASTER = 1188
ER_MASTER_NET_READ = 1189
ER_MASTER_NET_WRITE = 1190
ER_FT_MATCHING_KEY_NOT_FOUND = 1191
ER_LOCK_OR_ACTIVE_TRANSACTION = 1192
ER_UNKNOWN_SYSTEM_VARIABLE = 1193
ER_CRASHED_ON_USAGE = 1194
ER_CRASHED_ON_REPAIR = 1195
ER_WARNING_NOT_COMPLETE_ROLLBACK = 1196
ER_TRANS_CACHE_FULL = 1197
ER_SLAVE_MUST_STOP = 1198
ER_SLAVE_NOT_RUNNING = 1199
ER_BAD_SLAVE = 1200
ER_MASTER_INFO = 1201
ER_SLAVE_THREAD = 1202
ER_TOO_MANY_USER_CONNECTIONS = 1203
ER_SET_CONSTANTS_ONLY = 1204
ER_LOCK_WAIT_TIMEOUT = 1205
ER_LOCK_TABLE_FULL = 1206
ER_READ_ONLY_TRANSACTION = 1207
ER_DROP_DB_WITH_READ_LOCK = 1208
ER_CREATE_DB_WITH_READ_LOCK = 1209
ER_WRONG_ARGUMENTS = 1210
ER_NO_PERMISSION_TO_CREATE_USER = 1211
ER_UNION_TABLES_IN_DIFFERENT_DIR = 1212
ER_LOCK_DEADLOCK = 1213
ER_TABLE_CANT_HANDLE_FT = 1214
ER_CANNOT_ADD_FOREIGN = 1215
ER_NO_REFERENCED_ROW = 1216
ER_ROW_IS_REFERENCED = 1217
ER_CONNECT_TO_MASTER = 1218
ER_QUERY_ON_MASTER = 1219
ER_ERROR_WHEN_EXECUTING_COMMAND = 1220
ER_WRONG_USAGE = 1221
ER_WRONG_NUMBER_OF_COLUMNS_IN_SELECT = 1222
ER_CANT_UPDATE_WITH_READLOCK = 1223
ER_MIXING_NOT_ALLOWED = 1224
ER_DUP_ARGUMENT = 1225
ER_USER_LIMIT_REACHED = 1226
ER_SPECIFIC_ACCESS_DENIED_ERROR = 1227
ER_LOCAL_VARIABLE = 1228
ER_GLOBAL_VARIABLE = 1229
ER_NO_DEFAULT = 1230
ER_WRONG_VALUE_FOR_VAR = 1231
ER_WRONG_TYPE_FOR_VAR = 1232
ER_VAR_CANT_BE_READ = 1233
ER_CANT_USE_OPTION_HERE = 1234
ER_NOT_SUPPORTED_YET    = 1235
ER_MASTER_FATAL_ERROR_READING_BINLOG = 1236
ER_SLAVE_IGNORED_TABLE = 1237
ER_INCORRECT_GLOBAL_LOCAL_VAR = 1238
ER_WRONG_FK_DEF = 1239
ER_KEY_REF_DO_NOT_MATCH_TABLE_REF = 1240
ER_OPERAND_COLUMNS = 1241
ER_SUBQUERY_NO_1_ROW = 1242
ER_UNKNOWN_STMT_HANDLER = 1243
ER_CORRUPT_HELP_DB = 1244
ER_CYCLIC_REFERENCE = 1245
ER_AUTO_CONVERT = 1246
ER_ILLEGAL_REFERENCE = 1247
ER_DERIVED_MUST_HAVE_ALIAS = 1248
ER_SELECT_REDUCED = 1249
ER_TABLENAME_NOT_ALLOWED_HERE = 1250
ER_NOT_SUPPORTED_AUTH_MODE = 1251
ER_SPATIAL_CANT_HAVE_NULL = 1252
ER_COLLATION_CHARSET_MISMATCH = 1253
ER_SLAVE_WAS_RUNNING = 1254
ER_SLAVE_WAS_NOT_RUNNING = 1255
ER_TOO_BIG_FOR_UNCOMPRESS = 1256
ER_ZLIB_Z_MEM_ERROR = 1257
ER_ZLIB_Z_BUF_ERROR = 1258
ER_ZLIB_Z_DATA_ERROR = 1259
ER_CUT_VALUE_GROUP_CONCAT = 1260
ER_WARN_TOO_FEW_RECORDS = 1261
ER_WARN_TOO_MANY_RECORDS = 1262
ER_WARN_NULL_TO_NOTNULL = 1263
ER_WARN_DATA_OUT_OF_RANGE = 1264
ER_WARN_DATA_TRUNCATED = 1265
ER_WARN_USING_OTHER_HANDLER = 1266
ER_CANT_AGGREGATE_2COLLATIONS = 1267
ER_DROP_USER = 1268
ER_REVOKE_GRANTS = 1269
ER_CANT_AGGREGATE_3COLLATIONS = 1270
ER_CANT_AGGREGATE_NCOLLATIONS = 1271
ER_VARIABLE_IS_NOT_STRUCT = 1272
ER_UNKNOWN_COLLATION = 1273
ER_SLAVE_IGNORED_SSL_PARAMS = 1274
ER_SERVER_IS_IN_SECURE_AUTH_MODE = 1275
ER_WARN_FIELD_RESOLVED = 1276
ER_BAD_SLAVE_UNTIL_COND = 1277
ER_MISSING_SKIP_SLAVE = 1278
ER_UNTIL_COND_IGNORED = 1279
ER_WRONG_NAME_FOR_INDEX = 1280
ER_WRONG_NAME_FOR_CATALOG = 1281
ER_WARN_QC_RESIZE = 1282
ER_BAD_FT_COLUMN = 1283
ER_UNKNOWN_KEY_CACHE = 1284
ER_WARN_HOSTNAME_WONT_WORK = 1285
ER_UNKNOWN_STORAGE_ENGINE = 1286
ER_WARN_DEPRECATED_SYNTAX = 1287
ER_NON_UPDATABLE_TABLE = 1288
ER_FEATURE_DISABLED = 1289
ER_OPTION_PREVENTS_STATEMENT = 1290
ER_DUPLICATED_VALUE_IN_TYPE = 1291
ER_TRUNCATED_WRONG_VALUE = 1292
ER_TOO_MUCH_AUTO_TIMESTAMP_COLS = 1293
ER_INVALID_ON_UPDATE = 1294
ER_UNSUPPORTED_PS = 1295
ER_GET_ERRMSG = 1296
ER_GET_TEMPORARY_ERRMSG = 1297
ER_UNKNOWN_TIME_ZONE = 1298
ER_WARN_INVALID_TIMESTAMP = 1299
ER_INVALID_CHARACTER_STRING = 1300
ER_WARN_ALLOWED_PACKET_OVERFLOWED = 1301
ER_CONFLICTING_DECLARATI_ERROR_MESSAGES = 303

CR_MIN_ERROR               = 2000
CR_MAX_ERROR               = 2999

CR_UNKNOWN_ERROR           = 2000
CR_SOCKET_CREATE_ERROR     = 2001
CR_CONNECTION_ERROR        = 2002
CR_CONN_HOST_ERROR         = 2003
CR_IPSOCK_ERROR            = 2004
CR_UNKNOWN_HOST            = 2005
CR_SERVER_GONE_ERROR       = 2006
CR_VERSION_ERROR           = 2007
CR_OUT_OF_MEMORY           = 2008
CR_WRONG_HOST_INFO         = 2009
CR_LOCALHOST_CONNECTION    = 2010
CR_TCP_CONNECTION          = 2011
CR_SERVER_HANDSHAKE_ERR    = 2012
CR_SERVER_LOST             = 2013
CR_COMMANDS_OUT_OF_SYNC    = 2014
CR_NAMEDPIPE_CONNECTION    = 2015
CR_NAMEDPIPEWAIT_ERROR     = 2016
CR_NAMEDPIPEOPEN_ERROR     = 2017
CR_NAMEDPIPESETSTATE_ERROR = 2018
CR_CANT_READ_CHARSET       = 2019
CR_NET_PACKET_TOO_LARGE    = 2020
CR_EMBEDDED_CONNECTION     = 2021
CR_PROBE_SLAVE_STATUS      = 2022
CR_PROBE_SLAVE_HOSTS       = 2023
CR_PROBE_SLAVE_CONNECT     = 2024
CR_PROBE_MASTER_CONNECT    = 2025
CR_SSL_CONNECTION_ERROR    = 2026
CR_MALFORMED_PACKET        = 2027
CR_WRONG_LICENSE           = 2028
CR_NULL_POINTER            = 2029
CR_NO_PREPARE_STMT         = 2030
CR_PARAMS_NOT_BOUND        = 2031
CR_DATA_TRUNCATED          = 2032
CR_NO_PARAMETERS_EXISTS    = 2033
CR_INVALID_PARAMETER_NO    = 2034
CR_INVALID_BUFFER_USE      = 2035
CR_UNSUPPORTED_PARAM_TYPE  = 2036

CR_SHARED_MEMORY_CONNECTION              = 2037
CR_SHARED_MEMORY_CONNECT_REQUEST_ERROR   = 2038
CR_SHARED_MEMORY_CONNECT_ANSWER_ERROR    = 2039
CR_SHARED_MEMORY_CONNECT_FILE_MAP_ERROR  = 2040
CR_SHARED_MEMORY_CONNECT_MAP_ERROR       = 2041
CR_SHARED_MEMORY_FILE_MAP_ERROR          = 2042
CR_SHARED_MEMORY_MAP_ERROR               = 2043
CR_SHARED_MEMORY_EVENT_ERROR             = 2044
CR_SHARED_MEMORY_CONNECT_ABANDONED_ERROR = 2045
CR_SHARED_MEMORY_CONNECT_SET_ERROR       = 2046
CR_CONN_UNKNOW_PROTOCOL                  = 2047
CR_INVALID_CONN_HANDLE                   = 2048
CR_SECURE_AUTH                           = 2049
CR_FETCH_CANCELED                        = 2050
CR_NO_DATA                               = 2051
CR_NO_STMT_METADATA                      = 2052

########NEW FILE########
__FILENAME__ = coroqueue
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""coroqueue

A corosafe Queue implementation.

Written by Libor Michalek.
"""

import weakref
import coro
import time
import bisect
import exceptions
import operator
import copy
import smtplib
import socket

import pyinfo

DEFAULT_PRIORITY = 0x01


def merge(dst, src):
    if dst is None:
        return copy.deepcopy(src)

    if not isinstance(dst, type(src)):
        raise TypeError(
            'Cannot merge two different types %r:%r' % (type(dst), type(src)))

    if isinstance(dst, type(0)):
        return dst + src

    if isinstance(dst, type(())):
        return tuple(map(operator.add, dst, src))

    if isinstance(dst, type({})):
        return filter(
            lambda i: dst.update({i[0]: merge(dst.get(i[0]), i[1])}),
            src.items()) or dst

    raise TypeError('Unhandled destination type: %r' % (type(dst),))


class Timeout(object):
    def __init__(self, timeout):
        if timeout is None:
            self.expire = None
        else:
            self.expire = time.time() + timeout

    def __repr__(self):
        if self.expire is None:
            return repr(None)
        else:
            return repr(self.expire - time.time())

    def __nonzero__(self):
        if self.expire is None:
            return True
        else:
            return bool(self.expire > time.time())

    def __call__(self):
        if self.expire is None:
            return None
        else:
            return self.expire - time.time()


class ElementContainer(object):
    def __init__(self, *args, **kwargs):
        self._item_list = []
        self._item_set  = set()

    def __len__(self):
        return len(self._item_list)

    def __nonzero__(self):
        return bool(self._item_list)

    def __contains__(self, obj):
        return obj in self._item_set

    def add(self, obj):
        self._item_list.append((time.time(), obj))
        self._item_set.add(obj)

    def pop(self):
        timestamp, obj = self._item_list.pop()
        self._item_set.remove(obj)
        return obj

    def rip(self, timestamp = None):
        if timestamp is None:
            index = len(self._item_list)
        else:
            index = bisect.bisect(self._item_list, (timestamp, None))

        if not index:
            return []

        data = map(lambda i: i[1], self._item_list[:index])
        del(self._item_list[:index])
        self._item_set.difference_update(data)

        return data

class TimeoutError(exceptions.Exception):
    pass

class QueueError(exceptions.Exception):
    pass

class QueueDeadlock(exceptions.Exception):
    pass

class Queue(object):
    '''
    Simple generic queue.
    '''
    def __init__(self, object_allocator, args, kwargs, **kw):
        #
        #
        #
        self._timeout   = kw.get('timeout', None)
        self._patient   = kw.get('patient', False)
        self._active    = True
        self._item_out  = 0
        self._item_list = ElementContainer()

        self._item_refs = {}
        self._item_save = {}
        self._item_time = {}

        self._out_total = 0L
        self._out_time  = 0
        self._out_max   = 0

        self._item_args   = args
        self._item_kwargs = kwargs
        self._item_alloc  = object_allocator
        #
        # priority list is presented lowest to highest
        #
        self._item_max    = {}
        self._item_queues = {}
        self._item_prios  = []

        size  = kw.get('size', 0)
        prios = kw.get('prios', [DEFAULT_PRIORITY])

        for index in range(len(prios)):
            if isinstance(prios[index], type(tuple())):
                size += prios[index][1]
                prio  = prios[index][0]
            else:
                prio  = prios[index]

            self._item_queues[prio] = coro.stats_cond(timeout = self._timeout)
            self._item_max[prio]    = size

            self._item_prios.insert(0, prio)

    def __repr__(self):
        state = self.state()

        entries = '(use: %d, max: %r, waiting: %r)' % \
            (state['out'], state['max'], state['wait'])
        return 'Queue: status <%s> entries %s' % (
            ((self._active and 'on') or 'off'), entries,)

    def __alloc(self):
        o = self._item_alloc(
            *self._item_args, **self._item_kwargs)

        def dropped(ref):
            self._stop_info(self._item_save.pop(self._item_refs[ref], {}))

            self._item_out = self._item_out - 1
            del(self._item_refs[ref])
            self.wake_one()

        r = weakref.ref(o, dropped)
        self._item_refs[r] = id(o)

        return o

    def __dealloc(self, o):
        for r in weakref.getweakrefs(o):
            self._item_refs.pop(r, None)

    def _stop_info(self, data):
        '''_stop_info

        When an object is being returned to the queue, stop recording
        trace information in the thread that removed the object from
        the queue.
        '''
        thrd = coro._get_thread(data.get('thread', 0))
        if thrd is not None:
            thrd.trace(False)

        return data

    def _save_info(self, o):
        '''_save_info

        When an item is fetched from the queue, save information about
        the item request and the requester.
        '''
        data    = {'caller': pyinfo.rawstack(depth = 2), 'time':   time.time()}
        current = coro.current_thread()

        if current is not None:
            data.update({'thread': current.thread_id()})
            current.trace(True)

        self._item_save[id(o)] = data
        return o

    def _drop_info(self, o):
        '''_drop_info

        When an item is returned to the queue, release information about
        the original item request and the requester.
        '''
        return self._stop_info(self._item_save.pop(id(o), {}))

    def _dealloc(self, o):
        self.__dealloc(o)

    def _drop_all(self):
        '''_drop_all

        All currently allocated and queued (e.g. not checked out) are
        released and deallocated.
        '''
        while self._item_list:
            self._dealloc(self._item_list.pop())

    def timeout(self, *args):
        if not args:
            return self._timeout

        self._timeout = args[0]

        for cond in self._item_queues.values():
            cond.timeout = self._timeout

    def empty(self, prio):
        prio = (prio is None and self._item_prios[-1]) or prio
        return (not (self._item_out < self._item_max[prio]))

    def wake_all(self):
        for prio in self._item_prios:
            self._item_queues[prio].wake_all()

    def wake_one(self):
        for prio in self._item_prios:
            if len(self._item_queues[prio]):
                self._item_queues[prio].wake_one()
                break

    def wait_one(self, prio = None, timeout = None):
        prio = (prio is None and self._item_prios[-1]) or prio

        result = self._item_queues[prio].wait(timeout)
        if result is None:
            return (False, prio)     # wait timed out
        elif result:
            return (True, result[0]) # wait had a priority adjustment
        else:
            return (True, prio)      # wait completed successfully

    def bump(self, id, prio):
        for cond in self._item_queues.values():
            try:
                cond.wake(id, prio)
            except coro.CoroutineCondError:
                pass
            else:
                break

    def get(self, prio = None, poll = False):
        '''get

        Return an object from the queue, wait/yield if one is not available
        until it becomes available.

        Note: when the queue has a timeout defined, the return value
              will be None when the timeout expires and no object has
              become available.
        '''
        wait = not poll

        while wait and \
                  ((self.empty(prio) and self._active) or \
                   (self._patient and not self._active)):
            wait, prio = self.wait_one(prio)

        if self.empty(prio) or not self._active:
            return None

        if not self._item_list:
            self._item_list.add(self.__alloc())

        self._item_out  += 1
        self._out_total += 1

        return self._save_info(self._item_list.pop())

    def put(self, o):
        if o in self._item_list:
            raise QueueError('cannnot put object already in queue', o)

        timestamp = self._drop_info(o).get('time', None)
        if timestamp is not None:
            out_time = time.time() - timestamp

            self._out_time += out_time
            self._out_max   = max(out_time, self._out_max)

        self._item_out = self._item_out - 1

        if self._active:
            self._item_list.add(o)
        else:
            self._dealloc(o)

        self.wake_one()
        return None

    def active(self):
        return self._active

    def patient(self, v):
        self._patient = v

    def on(self, *args, **kwargs):
        self._active = True
        self.wake_all()

    def off(self, **kwargs):
        timeout = Timeout(kwargs.get('timeout', None))
        wait    = True
        #
        # It is possible to use the regular wait queue to wait for all
        # outstanding objects, since wake_all() clears out the entire
        # wait list synchronously and _active set to false prevents
        # anyone else from entering.
        #
        self._active = False
        self.wake_all()

        while wait and self._item_out and not self._active:
            wait, prio = self.wait_one(timeout = timeout())

        if not self._active:
            self._drop_all()

        return wait

    def trim(self, age):
        '''trim

        Any item in the queue which is older then age seconds gets reaped.
        '''
        count = 0

        for o in self._item_list.rip(time.time() - age):
            self._dealloc(o)
            count += 1

        return count

    def resize(self, size, prio = None):
        prio = (prio is None and self._item_prios[-1]) or prio
        self._item_max[prio] = size

    def size(self, prio = None):
        prio = (prio is None and self._item_prios[-1]) or prio
        return self._item_max[prio]

    def stats(self):
        qstats = {}
        for stat in map(lambda x: x.stats(), self._item_queues.values()):
            qstats['waiting'] = qstats.get('waiting', []) + stat['waiting']
            qstats['timeouts'] = qstats.get('timeouts', 0) + stat['timeouts']
            qstats['total'] = qstats.get('total', 0) + stat['total']
            qstats['waits'] = qstats.get('waits', 0) + stat['waits']

        if qstats['total']:
            qstats['average'] = qstats['total']/qstats['waits']
        else:
            qstats['average'] = 0

        qstats.update({
            'item_max': self._item_max.values(),
            'item_out': self._item_out,
            'requests': self._out_total,
            'out_max' : self._out_max,
            'pending' : self._item_save})
        qstats['pending'].sort()
        qstats['waiting'].sort()

        if  self._out_time:
            average = self._out_time/(self._out_total-self._item_out)
        else:
            average = 0

        qstats.update({'avg_pend': average})
        return qstats

    def state(self):
        item_max  = []
        item_wait = []
        item_left = []

        for index in range(len(self._item_prios)-1, -1, -1):
            prio = self._item_prios[index]

            item_max.append(self._item_max[prio])
            item_left.append(self._item_max[prio] - self._item_out)
            item_wait.append(len(self._item_queues[prio]))

        return {
            'out': self._item_out,
            'max': item_max,
            'in':  item_left,
            'wait': item_wait}

    def find(self):
        '''find

        Return information about each object that is currently checked out
        and therefore not in the queue.

          caller - execution stack trace at the time the object was
                   removed from the queue
          thread - coroutine ID of the thread executing at the time the
                   object was removed from the queue
          trace  - current execution stack trace of the coroutine which
                   removed the object from the queue
          time   - unix timestamp when the object was removed from the
                   queue.
        '''
        saved = self._item_save.copy()
        for oid, data in saved.items():
            thread = coro._get_thread(data['thread'])
            if thread is None:
                data.update({'trace': None})
            else:
                data.update({'trace': thread.where()})

        return saved


class SortedQueue(object):
    def __init__(
        self, object_allocator, args, kwargs, size = 0, timeout = None):

        self._timeout     = timeout
        self._item_args   = args
        self._item_kwargs = kwargs
        self._item_alloc  = object_allocator
        self._item_max    = size
        self._item_out    = 0

        self._out_total   = 0L
        self._out_time    = 0
        self._out_max     = 0

        self._item_list = []
        self._item_refs = {}
        self._item_time = {}
        self._item_cond = coro.stats_cond(timeout = self._timeout)

    def __repr__(self):
        state = self.state()
        entries = '(use: %d, max: %r, waiting: %r)' % \
                  (state['out'], state['max'], state['wait'])

        return 'SortedQueue: entries %s' % entries

    def __alloc(self):
        o = self._item_alloc(
            *self._item_args, **self._item_kwargs)

        def dropped(ref):
            self._item_out = self._item_out - 1
            del(self._item_refs[ref])
            self.wake_one()

        r = weakref.ref(o, dropped)
        self._item_refs[r] = id(o)

        return o

    def empty(self):
        return not (self._item_out < self._item_max)


    def wake_all(self):
        self._item_cond.wake_all()

    def wake_one(self):
        self._item_cond.wake_one()

    def wait_one(self):
        result = self._item_cond.wait()
        return not (result is None)

    def head(self, poll = False):
        return self._get(poll)

    def tail(self, poll = False):
        return self._get(poll, True)

    def _get(self, poll = False, tail = False):

        wait = not poll

        # wait for something to come in if we're not polling
        while wait and self.empty():
            wait = self.wait_one()

        if self.empty():
            return None

        if not self._item_list:
            if tail:
                return None
            self._item_list.append(self.__alloc())

        self._item_time[coro.current_id()] = time.time()
        self._item_out  += 1
        self._out_total += 1

        if tail:
            o = self._item_list[0]
            del(self._item_list[0])
        else:
            o = self._item_list.pop()

        return o

    def put(self, o):
        id = coro.current_id()
        if id in self._item_time:
            out_time = time.time() - self._item_time[id]
            self._out_time += out_time
            self._out_max = max(self._out_max, out_time)
            del(self._item_time[id])

        self._item_out -= 1
        bisect.insort(self._item_list, o)

        self.wake_one()
        return None

    def resize(self, size):
        self._item_max = size

    def size(self):
        return self._item_max

    def stats(self):
        qstats = {}
        qstats.update(self._item_cond.stats())

        qstats.update({
            'item_max' : self._item_max,
            'item_out' : self._item_out,
            'requests' : self._out_total,
            'out_max'  : self._out_max,
            'pending'  : self._item_time.values() })
        qstats['pending'].sort()
        qstats['waiting'].sort()

        if self._out_time:
            average = self._out_time/(self._out_total-self._item_out)
        else:
            average = 0

        qstats.update({'avg_pend' : average })
        return qstats

    def state(self):
        return { 'out'  : self._item_out,
                 'max'  : self._item_max,
                 'in'   : self._item_max - self._item_out,
                 'wait' : len(self._item_cond) }

class SafeQueue(Queue):
    '''SafeQueue

    Queue with protection against a single coro.thread requesting multiple
    objects and potentially deadlocking in the process.
    '''
    def __init__(self, *args, **kwargs):
        super(SafeQueue, self).__init__(*args, **kwargs)

        self._item_thrd = {}

    def _stop_info(self, data):
        data = super(SafeQueue, self)._stop_info(data)
        self._item_thrd.pop(data.get('thread', -1), None)

        return data

    def _save_info(self, o):
        o = super(SafeQueue, self)._save_info(o)
        t = self._item_save[id(o)].get('thread', -1)

        self._item_thrd[t] = id(o)
        return o

    def get(self, *args, **kwargs):
        '''get

        Return an object from the queue, wait/yield if one is not available
        until it becomes available.

        Note: when the queue has a timeout defined, the return value
              will be None when the timeout expires and no object has
              become available.

        QueueDeadlock raised if an attempt is made to get an object and
        the current thread already has fetched an object from the queue
        which has yet to be returned.
        '''
        if coro.current_id() in self._item_thrd:
            obj = self._item_thrd[coro.current_id()]
            raise QueueDeadlock(obj, self._item_save[obj])

        return super(SafeQueue, self).get(*args, **kwargs)

class ThreadQueue(Queue):
    def __init__(self, thread, args, size = 0,priorities = [DEFAULT_PRIORITY]):
        super(ThreadQueue, self).__init__(
            thread, (), {'args': args},	size = size, prios = priorities)

    def get(self, prio = None, poll = False):
        thrd = super(type(self), self).get(prio, poll)
        if thrd is not None:
            thrd.start()
        return thrd

class SimpleObject(object):
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return '<SimpleObject: %r>' % (self.name,)

class SimpleQueue(Queue):
    def __init__(self, name, size = 0, priorities = [DEFAULT_PRIORITY]):
        super(SimpleQueue, self).__init__(
            SimpleObject, (name, ), {}, size = size, prios = priorities)

class SMTPQueue(SafeQueue):

    def __init__(self, host_primary, host_secondary=None, priorities=None,
            size=0, optional={}, timeout=None, trace=False, **kw):
        priorities = priorities or [DEFAULT_PRIORITY]
        self.host_primary = host_primary
        self.host_secondary = host_secondary
        super(SMTPQueue, self).__init__(
            smtplib.SMTP, (), optional, size = size,
            prios = priorities, timeout = timeout, **kw)

    def get(self, *args, **kwargs):
        smtp = super(SMTPQueue, self).get(*args, **kwargs)
        if not getattr(smtp, 'sock', None):
            try:
                smtp.connect(self.host_primary)
            except socket.gaierror, gaie:
                if self.host_secondary:
                    smtp.connect(self.host_secondary)
                raise
        return smtp

    def _dealloc(self, o):
        super(SMTPQueue, self)._dealloc(o)
        o.close()

#
#
# end


########NEW FILE########
__FILENAME__ = corowork
#!/usr/local/bin/python
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""corowork

Queue with worker threads to service entries.
"""

import coro
import coroqueue
import statistics

import exceptions
import time
import sys
import os

# same as btserv/cacches.py but not importable because of Logic circular import
DB_USAGE_MARKER = 'cache-db-usage'

class QueueError (exceptions.Exception):
    pass

class Worker(coro.Thread):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__(*args, **kwargs)

        self._requests = kwargs['requests']
        self._filter   = kwargs['filter']
        self._prio     = kwargs.get('prio', 0)

        self._exit  = False
        self._drain = False

    def execute(self, *args, **kwargs):
        self.info('REQUEST args: %r kwargs: %r' % (args, kwargs))

    def run(self):
        self.info('Starting QueueWorker [%s]: %s' % (self._prio, self.__class__.__name__))

        while not self._exit:
            if self._drain:
                timeout = 0
            else:
                timeout = None

            try:
                args, kwargs, start = self._requests.pop(timeout = timeout)
            except coro.CoroutineCondWake:
                continue
            except coro.TimeoutError:
                break

            self.profile_clear()
            #
            # execution
            #
            self.execute(*args, **kwargs)
            #
            # record statistics
            #
            stamp = time.time()
            delta = stamp - start
            label = self._filter(args, kwargs)

            self.parent().record(stamp, delta, label)
        #
        # shutdown
        #
        self.info('Exiting QueueWorker')

    def shutdown(self):
        self._exit = True

    def drain(self):
        self._drain = True

    def requeue(self, *args, **kwargs):
        self._requests.push((args, kwargs, time.time()))

class CommandWorker(Worker):
    '''A worker thread that that expects command from a
    notify/rpc_call call to be part of the execute args. Attempts to
    lookup the method on this thread object and execute it.
    '''

    def execute(self, object, id, cmd, args, server = None, seq = None):
        handler = getattr(self, cmd, None)
        result = None
        if handler is not None and getattr(handler, 'command', 0):
            try:
                result = handler(args)
            except exceptions.Exception, e:
                self.traceback()
        if server is not None:
            server.rpc_response(seq, result)


class Server(coro.Thread):
    name = 'WorkQueueServer'

    def __init__(self, *args, **kwargs):
        super(Server, self).__init__(*args, **kwargs)

        self.work   = kwargs.get('worker', Worker)
        self.filter = kwargs.get('filter', lambda i,j: None)
        self.sizes  = kwargs.get('sizes') or [kwargs['size']]
        self.kwargs = kwargs
        self.stop   = False
        self.drain  = False

        self.rpcs    = {}
        self.cmdq    = []
        self.klist   = []
        self.workers = []

        self.identity = kwargs.get('identity', {})
        self.waiter   = coro.coroutine_cond()
        self.requests = []

        for size in self.sizes:
            self.requests.append(coro.coroutine_fifo())
            self.workers.append([])

        self.stats  = statistics.Recorder()
        self.wqsize = statistics.WQSizeRecorder()
        self.dbuse  = statistics.Recorder()

        self.wlimit = statistics.TopRecorder(threshold = 0.0)
        self.elimit = statistics.TopRecorder(threshold = 0.0)
        self.tlimit = statistics.TopRecorder(threshold = 0.0)
        self.rlimit = statistics.TopRecorder(threshold = 0)

        self.kwargs.update({
            'filter':   self.filter})

    def run(self):
        self.info('Starting %s.' % (self.name,))

        while not self.stop:
            #
            # spawn workers
            #
            while self.klist:
                work_klass, prio = self.klist.pop(0)
                work_kwargs = self.kwargs.copy()
                work_kwargs.update(
                    {'requests' : self.requests[prio],
                     'prio'     : prio, })
                worker = work_klass(**work_kwargs)
                worker.start()
                self.workers[prio].append(worker)
            #
            # execute management commands
            #
            while self.cmdq:
                try:
                    self.command_dispatch(*self.cmdq.pop(0))
                except:
                    self.traceback()
            #
            # wait for something to do
            self.waiter.wait()

        self.info(
            'Stopping %s. (children: %d)' % (
                self.name,
                self.child_count()))

        self.command_clear()

        for child in self.child_list():
            child.drain()

        for r in self.requests:
            r.wake()
        self.child_wait()

    def shutdown(self, timeout = None):
        if not self.stop:
            self.stop = True
            self.waiter.wake_all()

        return self.join(timeout)

    def resize(self, size, prio = 0):
        if not size:
            return None

        if size == self.sizes[prio]:
            return None

        kill = max(0, len(self.workers[prio]) - size)
        while kill:
            kill -= 1
            work  = self.workers[prio].pop()
            work.drain()

        self.requests[prio].wake()
        self.sizes[prio] = size

    def spawn(self, prio = 0):

        if self.requests[prio].waiters():
            return None

        size = self.sizes[prio]
        if size > self._wcount(prio):
            self.klist.append((self.work, prio))
            self.waiter.wake_all()

    def request(self, *args, **kwargs):
        '''make a request for this work server. this method can take a prio
        kwarg:  when it is present, it specifies the maximum priority slot
        this request is made in. defaults to the first slot, 0.

        requests are put into the lowest possible slot until that slot is
        "full," here full meaning # of worker threads < size for priority slot.
        '''
        if self.stop:
            raise QueueError('Sevrer has been shutdown.')

        # find the priority to queue this request in to
        max_prio = min(kwargs.get('prio', 0), len(self.sizes))
        for prio in xrange(max_prio+1):
            if self.requests[prio].waiters():
                break
            self.workers[prio] = filter(
                lambda w: w.isAlive(), self.workers[prio])

            # if we got here it means nothing is waiting for something
            # to do at this prio. check to see if we can spawn.
            room = max(self.sizes[prio] - len(self.workers[prio]), 0)
            if not room:
                continue
            room -= len(filter(lambda i: i[1] == prio, self.klist))
            if room > 0:
                self.klist.append((self.work, prio))
                self.waiter.wake_all()
                break

        self.requests[prio].push((args, kwargs, time.time()))

    def record(self, current, elapse, label):
        self.stats.request(elapse, name = label, current = current)
        if coro.get_local(DB_USAGE_MARKER, False):
            self.dbuse.request(elapse, name = label, current = current)
        self.wqsize.request(sum(map(len, self.requests)))

        data = (
            label, current, elapse,
            coro.current_thread().total_time(),
            coro.current_thread().long_time(),
            coro.current_thread().resume_count())

        self.wlimit.save(data[2], data) # longest wall clock + queue wait times
        self.elimit.save(data[3], data) # longest execution times
        self.tlimit.save(data[4], data) # longest non-yield times
        self.rlimit.save(data[5], data) # most request yields

    def least_prio(self):
        '''return the smallest request priority that is not full. a full
        request priority is one that has created all of its worker threads
        '''
        for prio in xrange(len(self.sizes)):
            if self._wcount(prio) < self.sizes[prio]:
                break
        return prio

    def _wcount(self, prio):
        return len(filter(lambda t: t.isAlive(), self.workers[prio])) + \
               len(filter(lambda k: k[1] == prio, self.klist))
    #
    # dispatch management/stats commands
    #
    def command_list(self):
        result = []

        for name in dir(self):
            handler = getattr(self, name, None)
            if not callable(handler):
                continue
            if getattr(handler, 'command', None) is None:
                continue
            name = name.split('_')
            if name[0] != 'object':
                continue
            name = '_'.join(name[1:])
            if not name:
                continue

            result.append(name)

        return result

    def command_clear(self):
        for seq in self.rpcs.keys():
            self.command_response(seq)

    def command_push(self, obj, id, cmd, args, seq, server):
        self.rpcs[seq] = server
        self.cmdq.append((obj, cmd, args, seq))

        self.waiter.wake_all()

    def command_response(self, seq, response = None):
        server = self.rpcs.pop(seq, None)
        if server is not None: server.rpc_response(seq, response)

    def command_dispatch(self, obj, cmd, args, seq):
        name = 'object_%s' % (cmd,)
        handler = getattr(self, name, None)
        response = self.identity.copy()

        if getattr(handler, 'command', None) is None:
            response.update({'rc': 1, 'msg': 'no handler: <%s>' % name})
            self.command_response(seq, response)
            return None

        try:
            result = handler(args)
        except exceptions.Exception, e:
            self.traceback()
            t,v,tb = coro.traceback_info()

            response.update({
                'rc': 1,
                'msg': 'Exception: [%s|%s]' % (t,v),
                'tb': tb})
        else:
            response.update({'rc': 0, 'result': result})

        self.command_response(seq, response)
        return None
#
# end..

########NEW FILE########
__FILENAME__ = coutil
#!/usr/bin/env python

# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""coutil

Various coroutine-safe utilities.

Written by Libor Michalek.
"""

import os
import sys
import string
import types
import random as whrandom

import coro

class object_queue:

  def __init__ (self):
    # object queue
    self._queue = []
    self._c = coro.coroutine_cond()

  def __len__ (self):
    return len(self._queue)

  def push (self, q):
    # place data in the queue, and wake up a consumer
    self._queue.append(q)
    self._c.wake_one()

  def pop (self):
    # if there is nothing in the queue, wait to be awoken
    while not len(self._queue):
      self._c.wait()

    item = self._queue[0]
    del self._queue[0]

    return item

class critical_section:

  def __init__(self):

    self._lock  = 0
    self._error = 0
    self._c     = coro.coroutine_cond()

    return None

  def get_lock(self):

    while self._lock and not self._error:
      self._c.wait()

    if not self._error:
      self._lock = 1

    return self._error

  def release_lock(self):

    self._lock = 0
    self._c.wake_one()

    return None

  def error(self):

    self._lock  = 0
    self._error = 1
    self._c.wake_all()

    return None

class conditional_id:

  def __init__(self):

    self.__wait_map = {}
    self.__map_cond = coro.coroutine_cond()

  def wait(self, id):

    self.__wait_map[id] = coro.current_thread().thread_id()
    self.__map_cond.wait()

    return None

  def wake(self, id):

    if self.__wait_map.has_key(id):
      self.__map_cond.wake(self.__wait_map[id])
      del self.__wait_map[id]

    return None

  def wake_one(self):

    if len(self.__wait_map):
      id = whrandom.choice(self.__wait_map.keys())
      self.wake(id)

    return None

  def wake_all(self):

    self.__wait_map = {}
    self.__map_cond.wake_all()

    return None

########NEW FILE########
__FILENAME__ = dqueue
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''dqueue

Object and Queue class for implementing a doubly linked list queue.
'''

import exceptions
import operator

class ObjectQueueError(exceptions.Exception):
    pass

class QueueObject(object):
    __slots__ = ['__item_next__', '__item_prev__']

    def __init__(self, *args, **kwargs):
        self.__item_next__ = None
        self.__item_prev__ = None

    def __queued__(self):
        return not (self.__item_next__ is None or self.__item_prev__ is None)

    def __clip__(self):
        '''__clip__

        void queue connectivity, used when object has been cloned/copied
        and the references are no longer meaningful, since the queue
        neighbors correctly reference the original object.
        '''
        self.__item_next__ = None
        self.__item_prev__ = None

class QueueIterator(object):
    def __init__(self, queue, *args, **kwargs):
        self._queue  = queue
        self._object = self._queue.look_head()

    def __iter__(self):
        return self

    def next(self):
        if self._object is None:
            raise StopIteration

        value, self._object = self._object, self._queue.next(self._object)
        if self._object is self._queue.look_head():
            self._object = None

        return value

class ObjectQueue(object):
    def __init__(self, *args, **kwargs):
        self._head = None
        self._size = 0

    def __len__(self):
        return self._size

    def __del__(self):
        return self.clear()

    def __nonzero__(self):
        return self._head is not None

    def __iter__(self):
        return QueueIterator(self)

    def _validate(self, obj):
        if not hasattr(obj, '__item_next__'):
            raise ObjectQueueError, 'not a queueable object'
        if not hasattr(obj, '__item_prev__'):
            raise ObjectQueueError, 'not a queueable object'

    def put(self, obj, fifo = False):
        self._validate(obj)

        if self._in_queue(obj):
            raise ObjectQueueError, 'object already queued'

        if self._head is None:
            obj.__item_next__ = obj
            obj.__item_prev__ = obj
            self._head        = obj
        else:
            obj.__item_next__ = self._head
            obj.__item_prev__ = self._head.__item_prev__

            obj.__item_next__.__item_prev__ = obj
            obj.__item_prev__.__item_next__ = obj

            if fifo:
                self._head = obj

        self._size += 1

    def get(self, fifo = False):
        if self._head is None:
            return None

        if fifo:
            obj = self._head
        else:
            obj = self._head.__item_prev__

        if obj.__item_next__ is obj and obj.__item_prev__ is obj:
            self._head = None
        else:
            obj.__item_next__.__item_prev__ = obj.__item_prev__
            obj.__item_prev__.__item_next__ = obj.__item_next__

            self._head = obj.__item_next__

        obj.__item_next__ = None
        obj.__item_prev__ = None

        self._size -= 1
        return obj

    def look(self, fifo = False):
        if self._head is None:
            return None

        if fifo:
            return self._head
        else:
            return self._head.__item_prev__

    def remove(self, obj):
        self._validate(obj)

        if not self._in_queue(obj):
            raise ObjectQueueError, 'object not queued'

        if obj.__item_next__ is obj and obj.__item_prev__ is obj:
            self._head = None
        else:
            next = obj.__item_next__
            prev = obj.__item_prev__
            next.__item_prev__ = prev
            prev.__item_next__ = next

            if self._head == obj:
                self._head = next

        obj.__item_next__ = None
        obj.__item_prev__ = None

        self._size -= 1

    def next(self, obj):
        if self._head == obj.__item_next__:
            return None
        else:
            return obj.__item_next__

    def prev(self, obj):
        if self._head.__item_prev__ == obj.__item_prev__:
            return None
        else:
            return obj.__item_prev__

    def put_head(self, obj):
        return self.put(obj, fifo = True)

    def put_tail(self, obj):
        return self.put(obj, fifo = False)

    def get_head(self):
        return self.get(fifo = True)

    def get_tail(self):
        return self.get(fifo = False)

    def look_head(self):
        return self.look(fifo = True)

    def look_tail(self):
        return self.look(fifo = False)

    def clear(self):
        while self:
            self.get()

    def _in_queue(self, obj):
        return obj.__item_next__ is not None and obj.__item_prev__ is not None

def iterqueue(queue, forward = True):
    '''emits elements out of the queue in a given order/direction.'''
    if forward:
        start = queue.look_head
        move  = queue.next
    else:
        start = queue.look_tail
        move  = queue.prev
    item = start()
    while item:
        yield item
        item = move(item)

#
# end...

########NEW FILE########
__FILENAME__ = emulate
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''emulate

Various emulation/monkey-patch functions for functionality which we want
behaving differently in the coro environment. Generally that behaviour
is a coroutine yield and reschedule on code which would have otherwise
blocked the entire process.

In the past each module maintained individual emulation code, this becomes
unwieldy as the scope continues to expand and encourages functionality
creep.
'''
import time

import coro
import corocurl
import coromysql
import corofile
#
# save needed implementations.
#
original = {
    'sleep': time.sleep,
    }

def sleep(value):
    thrd = coro.current_thread()
    if thrd is None:
        original['sleep'](value)
    else:
        thrd.Yield(timeout = value)

def emulate_sleep():
    time.sleep = sleep


def init():
    '''all

    Enable emulation for all modules/code which can be emulated.

    NOTE: only code which works correctly in coro AND main can/should
          be automatically initialized, the below emulations do not
          fall into that category, they only work in a coroutine, which
          is why the are here.
    '''
    coro.socket_emulate()
    corocurl.emulate()
    coromysql.emulate()
    corofile.emulate_popen2()
    #
    # auto-emulations
    #
    emulate_sleep()
#
# end..

########NEW FILE########
__FILENAME__ = fileobject
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''fileobject

emulate a fileobject using a seperate process to handle IO for coroutine
concurrency

Written by Libor Michalek. 2006
'''

import coro
import corofile
import coroqueue

# corofile.emulate_popen2()

import os
import sys
import struct
import exceptions
import pickle
import signal
import weakref
import signal

STAUS_OPENED = 1
STAUS_CLOSED = 0

COMMAND_SIZE   = 8 # cmd is 8 bytes, four for identifier and four for length
COMMAND_OPEN   = 0
COMMAND_CLOSE  = 1
COMMAND_READ   = 2
COMMAND_WRITE  = 3
COMMAND_FLUSH  = 4
COMMAND_SEEK   = 5

COMMAND_STAT   = 6
COMMAND_MKDIRS = 7
COMMAND_CHMOD  = 8
COMMAND_UNLINK = 9
COMMAND_UTIME  = 10
COMMAND_TELL   = 11
COMMAND_READLN = 12

COMMAND_MAP = {
    COMMAND_OPEN:   'open',
    COMMAND_CLOSE:  'close',
    COMMAND_READ:   'read',
    COMMAND_WRITE:  'write',
    COMMAND_FLUSH:  'flush',
    COMMAND_SEEK:   'seek',
    COMMAND_STAT:   'stat',
    COMMAND_MKDIRS: 'makedirs',
    COMMAND_CHMOD:  'chmod',
    COMMAND_UNLINK: 'unlink',
    COMMAND_UTIME:  'utime',
    COMMAND_TELL:   'tell',
    COMMAND_READLN: 'readline',
    }

RESPONSE_SUCCESS = 100
RESPONSE_ERROR   = 101

BUFFER_READ_SIZE  =      32*1024
BUFFER_WRITE_SIZE = 16*1024*1024

DEFAULT_QUEUE_SIZE = 16

NOWAIT = False

class CoroFileObjectError (exceptions.Exception):
    pass

class CoroFileObject(object):
    def __init__(self):
        self._stdi, self._stdo = os.popen2([
            os.path.realpath(__file__.replace('.pyc', '.py'))])

        self._data = ''
        self._status = STAUS_CLOSED
        self.name = None

    def __del__(self):
        if self._status == STAUS_OPENED:
            self.close(return_to_queue = False)

        if self._stdi: self._stdi.close()
        if self._stdo: self._stdo.close()
        if not NOWAIT: os.wait()

    def _cmd_(self, cmd, data = ''):
        self._stdi.write(struct.pack('!ii', cmd, len(data)))
        self._stdi.write(data)
        self._stdi.flush()

        data = self._stdo.read(COMMAND_SIZE)
        if not data:
            raise CoroFileObjectError('No command from child')

        response, size = struct.unpack('!ii', data)
        if size:
            data = self._stdo.read(size)
        else:
            data = None

        if response == RESPONSE_ERROR:
            raise pickle.loads(data)
        else:
            return data

    def open(self, name, mode = 'r'):
        if self._status == STAUS_OPENED:
            self.close()

        result = self._cmd_(COMMAND_OPEN, '%s\n%s' % (name, mode))
        self._status = STAUS_OPENED
        self.name = name
        return result

    def read(self, bytes = -1):
        while bytes < 0 or bytes > len(self._data):
            result = self._cmd_(COMMAND_READ)
            if result is None:
                break

            self._data += result
        #
        # either have all the data we want or file EOF
        #
        if bytes < 0:
            # Return all remaining data
            data = self._data
            self._data = ''
        else:
            data       = self._data[:bytes]
            self._data = self._data[bytes:]

        return data

    def readline(self, bytes = -1):
        while bytes < 0 or bytes > len(self._data):
            result = self._cmd_(COMMAND_READLN)
            if result is None:
                break
            self._data += result
            if result[-1] == '\n':
                break

        #
        # either have all the data we want or file EOF
        #
        if bytes < 0:
            # Return all remaining data
            data = self._data
            self._data = ''
        else:
            data       = self._data[:bytes]
            self._data = self._data[bytes:]

        return data


    def write(self, data):
        while data:
            self._cmd_(COMMAND_WRITE, data[:BUFFER_WRITE_SIZE])
            data = data[BUFFER_WRITE_SIZE:]

    def seek(self, offset):
        self._data = ''
        return self._cmd_(COMMAND_SEEK, struct.pack('!i', offset))

    def tell(self):
        return int(self._cmd_(COMMAND_TELL))

    def flush(self):
        return self._cmd_(COMMAND_FLUSH)

    def close(self, return_to_queue = True):
        """close closes this fileobject
        NB: The return_to_queue parameter is ignored.  It is required
        for interface compatability with the AutoCleanFileOjbect subclass.
        """
        self._data = ''
        self._status = STAUS_CLOSED
        return self._cmd_(COMMAND_CLOSE)
    #
    # non-standard extensions
    #
    def stat(self, path):
        args = eval(self._cmd_(COMMAND_STAT, path))
        return os._make_stat_result(*args)

    def makedirs(self, path):
        return eval(self._cmd_(COMMAND_MKDIRS, path))

    def chmod(self, path, mode):
        return eval(self._cmd_(COMMAND_CHMOD, '%s\n%d' % (path, mode)))

    def unlink(self, path):
        return eval(self._cmd_(COMMAND_UNLINK, path))

    def utime(self, path, value = None):
        return eval(self._cmd_(COMMAND_UTIME, '%s\n%s' % (path, str(value))))


class AutoCleanFileObject(CoroFileObject):
    """AutoCleanFileOjbect overrides close to optionally return itself
    to the filequeue after closing.
    """
    def close(self, return_to_queue = True):
        """close closes this fileobject

        return_to_queue: return this object back to the filequeue if
            True, the default.
        """
        res = super(AutoCleanFileObject, self).close()
        if return_to_queue:
            filequeue.put(self)
        return res

class FileObjectHandler(object):
    def __init__(self, stdin, stdout):
        self._stdi = stdin
        self._stdo = stdout
        self._fd   = None

    def open(self, data):
        name, mode = data.split('\n')

        self._fd = file(name, mode, BUFFER_READ_SIZE)

    def close(self, data):
        self._fd.close()

    def read(self, data):
        return self._fd.read(BUFFER_READ_SIZE)

    def readline(self, data):
        r = self._fd.readline(BUFFER_READ_SIZE)
        return r

    def write(self, data):
        return self._fd.write(data)

    def flush(self, data):
        return self._fd.flush()

    def seek(self, data):
        (offset,) = struct.unpack('!i', data)
        return self._fd.seek(offset)

    def tell(self, data):
        return str(self._fd.tell())
    #
    # non-standard extensions
    #
    def stat(self, data):
        return str(os.stat(data).__reduce__()[1])

    def makedirs(self, data):
        return str(os.makedirs(data))

    def chmod(self, data):
        path, mode = data.split('\n')
        return str(os.chmod(path, int(mode)))

    def unlink(self, data):
        return str(os.unlink(data))

    def utime(self, data):
        path, value = data.split('\n')
        return str(os.utime(path, eval(value)))

    def run(self):
        result = 0

        while True:
            try:
                data = self._stdi.read(COMMAND_SIZE)
            except KeyboardInterrupt:
                data = None

            if not data:
                result = 1
                break

            cmd, size = struct.unpack('!ii', data)
            if size:
                data = self._stdi.read(size)
            else:
                data = ''

            if size != len(data):
                result = 2
                break

            handler = getattr(self, COMMAND_MAP.get(cmd, 'none'), None)
            if handler is None:
                result = 3
                break

            try:
                result = handler(data)
            except exceptions.Exception, e:
                result   = pickle.dumps(e)
                response = RESPONSE_ERROR
            else:
                response = RESPONSE_SUCCESS

            if result is None:
                result = ''

            try:
                self._stdo.write(struct.pack('!ii', response, len(result)))
                self._stdo.write(result)
                self._stdo.flush()
            except IOError:
                result = 4
                break

        return result

class CoroFileQueue(coroqueue.Queue):
    def __init__(self, size, timeout = None):
        super(CoroFileQueue, self).__init__(
            AutoCleanFileObject, (), {}, size = size, timeout = timeout)

        self._fd_save = {}
        self._fd_refs  = {}

    def _save_info(self, o):
        def dropped(ref):
            self._fd_save.pop(self._fd_refs.pop(id(ref), None), None)

        p = weakref.proxy(o, dropped)
        self._fd_save[id(o)] = p
        self._fd_refs[id(p)] = id(o)

        return super(CoroFileQueue, self)._save_info(o)

    def _drop_info(self, o):
        self._fd_refs.pop(id(self._fd_save.pop(id(o), None)), None)

        return super(CoroFileQueue, self)._drop_info(o)

    def outstanding(self):
        return map(lambda i: getattr(i, 'name', None), self._fd_save.values())


filequeue = CoroFileQueue(DEFAULT_QUEUE_SIZE)

def resize(size):
    return filequeue.resize(size)

def size():
    return filequeue.size()

def _fo_open(name, mode = 'r'):
    fd = filequeue.get()
    if fd is None:
        return None

    try:
        fd.open(name, mode)
    except:
        filequeue.put(fd)
        raise
    return fd

#
# TODO: Remove close method once all references to it have been purged.
#
def _fo_close(fd):
    fd.close(return_to_queue=False)
    return filequeue.put(fd)

def __command__(name, *args, **kwargs):
    fd = filequeue.get()
    if fd is None:
        return None

    try:
        return getattr(fd, name)(*args, **kwargs)
    finally:
        filequeue.put(fd)

def _fo_stat(path):
    return __command__('stat', path)

def _fo_makedirs(path):
    return __command__('makedirs', path)

def _fo_chmod(path, mode):
    return __command__('chmod', path, mode)

def _fo_unlink(path):
    return __command__('unlink', path)

def _fo_utime(path, value = None):
    return __command__('utime', path, value = value)

#
# os.* calls
#
stat = os.stat
makedirs = os.makedirs
chmod = os.chmod
unlink = os.unlink
utime = os.utime

#
# file/open call
#
open = file
#
# close call
#
def dummy_close(fd):
    return fd.close()

close = dummy_close

# a generator function for doing readlines in a fileobject friendly manner
def iterlines(fd):
    while True:
        ln = fd.readline()
        if not ln:
            break
        yield ln

def iterfiles(filenames):
    for fn in filenames:
        fd = open(fn)
        for ln in iterlines(fd):
            yield ln
        fd.close()

def emulate():
    fileobject = sys.modules['gogreen.fileobject']
    #
    # os.* calls
    #
    fileobject.stat = _fo_stat
    fileobject.makedirs = _fo_makedirs
    fileobject.chmod = _fo_chmod
    fileobject.unlink = _fo_unlink
    fileobject.utime = _fo_utime

    #
    # file/open call
    #
    fileobject.open  = _fo_open
    fileobject.close = _fo_close

def nowait():
    '''nowait

    NOTE: GLOBAL SIGNAL CHANGE!

    Do not wait for the terminated/exiting fileobject, since this can
    block. To prevent the processes from becoming unreaped zombies we
    disable the SIGCHILD signal. (see man wait(2))
    '''
    global NOWAIT
    NOWAIT = True

    signal.signal(signal.SIGCHLD, signal.SIG_IGN)


if __name__ == '__main__':
    import prctl

    prctl.prctl(prctl.PDEATHSIG, signal.SIGTERM)

    handler = FileObjectHandler(sys.stdin, sys.stdout)
    value   = handler.run()
    sys.exit(value)
#
# end..

########NEW FILE########
__FILENAME__ = purepydns
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""purepydns.py

Pure Python DNS resolution routines, and a wrapper method that swaps
them with the baked-in DNS routines.

Requires the dnspython library available at:
http://www.dnspython.org/

Not to be confused with PyDNS, which is an entirely different Python
module for performing DNS lookups.
"""
import os
import sys
import socket
import time

import dns.exception
import dns.inet
import dns.message
import dns.name
import dns.rdata
import dns.rdataset
import dns.rdatatype
import dns.resolver
import dns.reversename

import coro
import cache

DNS_QUERY_TIMEOUT = 10.0
DNS_CACHE_MAXSIZE = 512

#
# Resolver instance used to perfrom DNS lookups.
#
class FakeAnswer(list):
    expiration = 0
class FakeRecord(object):
    pass

class ResolverProxy(object):
    def __init__(self, *args, **kwargs):
        self._resolver = None
        self._filename = kwargs.get('filename', '/etc/resolv.conf')
        self._hosts = {}
        if kwargs.pop('etc_hosts', True):
            self._load_etc_hosts()

    def _load_etc_hosts(self):
        try:
            fd = open('/etc/hosts', 'r')
            contents = fd.read()
            fd.close()
        except EnvironmentError:
            return

        contents = [line for line in contents.split('\n') if line and not line[0] == '#']

        for line in contents:
            line = line.replace('\t', ' ')
            parts = line.split(' ')
            parts = [p for p in parts if p]
            if not len(parts):
                continue
            ip = parts[0]
            for part in parts[1:]:
                self._hosts[part] = ip

    def clear(self):
        self._resolver = None

    def query(self, *args, **kwargs):
        if self._resolver is None:
            self._resolver = dns.resolver.Resolver(filename = self._filename)

        query = args[0]
        if query is None:
            args = list(args)
            query = args[0] = '0.0.0.0'
        if self._hosts and self._hosts.get(query):
            answer = FakeAnswer()
            record = FakeRecord()
            setattr(record, 'address', self._hosts[query])
            answer.append(record)
            return answer

        return self._resolver.query(*args, **kwargs)
#
# cache
#
resolver  = ResolverProxy()
responses = cache.LRU(size = DNS_CACHE_MAXSIZE)

def resolve(name):
    error = None
    rrset = responses.lookup(name)

    if rrset is None or time.time() > rrset.expiration:
        try:
            rrset = resolver.query(name)
        except dns.exception.Timeout, e:
            error = (socket.EAI_AGAIN, 'Lookup timed out')
        except dns.exception.DNSException, e:
            error = (socket.EAI_NODATA, 'No address associated with hostname')
        else:
            responses.insert(name, rrset)

    if error:
        if rrset is None:
            raise socket.gaierror(error)
        else:
            sys.stderr.write('DNS error: %r %r\n' % (name, error))

    return rrset
#
# methods
#
def getaliases(host):
    """Checks for aliases of the given hostname (cname records)
    returns a list of alias targets
    will return an empty list if no aliases
    """
    cnames = []
    error = None

    try:
        answers = dns.resolver.query(host, 'cname')
    except dns.exception.Timeout, e:
        error = (socket.EAI_AGAIN, 'Lookup timed out')
    except dns.exception.DNSException, e:
        error = (socket.EAI_NODATA, 'No address associated with hostname')
    else:
        for record in answers:
            cnames.append(str(answers[0].target))

    if error:
        sys.stderr.write('DNS error: %r %r\n' % (host, error))

    return cnames


def getaddrinfo(host, port, family=0, socktype=0, proto=0, flags=0):
    """Replacement for Python's socket.getaddrinfo.

    Currently only supports IPv4.  At present, flags are not
    implemented.
    """
    socktype = socktype or socket.SOCK_STREAM

    if is_ipv4_addr(host):
        return [(socket.AF_INET, socktype, proto, '', (host, port))]

    rrset = resolve(host)
    value = []

    for rr in rrset:
        value.append((socket.AF_INET, socktype, proto, '', (rr.address, port)))

    return value

def gethostbyname(hostname):
    """Replacement for Python's socket.gethostbyname.

    Currently only supports IPv4.
    """
    if is_ipv4_addr(hostname):
        return hostname

    rrset = resolve(hostname)
    return rrset[0].address

def gethostbyname_ex(hostname):
    """Replacement for Python's socket.gethostbyname_ex.

    Currently only supports IPv4.
    """

    if is_ipv4_addr(hostname):
        return (hostname, [], [hostname])

    rrset = resolve(hostname)
    addrs = []

    for rr in rrset:
        addrs.append(rr.address)

    return (hostname, [], addrs)

def getnameinfo(sockaddr, flags):
    """Replacement for Python's socket.getnameinfo.

    Currently only supports IPv4.
    """
    try:
        host, port = sockaddr
    except (ValueError, TypeError):
        if not isinstance(sockaddr, tuple):
            # there's a stdlib test that's hyper-careful about refcounts
            del sockaddr
            raise TypeError('getnameinfo() argument 1 must be a tuple')
        else:
            # must be an ipv6 sockaddr, pretend we don't know how to resolve it
            raise socket.gaierror(
                    socket.EAI_NONAME, 'Name or service not known')

    if (flags & socket.NI_NAMEREQD) and (flags & socket.NI_NUMERICHOST):
        # Conflicting flags.  Punt.
        raise socket.gaierror(
            (socket.EAI_NONAME, 'Name or service not known'))

    if is_ipv4_addr(host):
        try:
            rrset =	resolver.query(
                dns.reversename.from_address(host), dns.rdatatype.PTR)
            if len(rrset) > 1:
                raise socket.error('sockaddr resolved to multiple addresses')
            host = rrset[0].target.to_text(omit_final_dot=True)
        except dns.exception.Timeout, e:
            if flags & socket.NI_NAMEREQD:
                raise socket.gaierror((socket.EAI_AGAIN, 'Lookup timed out'))
        except dns.exception.DNSException, e:
            if flags & socket.NI_NAMEREQD:
                raise socket.gaierror(
                    (socket.EAI_NONAME, 'Name or service not known'))
    else:
        try:
            rrset = resolver.query(host)
            if len(rrset) > 1:
                raise socket.error('sockaddr resolved to multiple addresses')
            if flags & socket.NI_NUMERICHOST:
                host = rrset[0].address
        except dns.exception.Timeout, e:
            raise socket.gaierror((socket.EAI_AGAIN, 'Lookup timed out'))
        except dns.exception.DNSException, e:
            raise socket.gaierror(
                (socket.EAI_NODATA, 'No address associated with hostname'))

    if not (flags & socket.NI_NUMERICSERV):
        proto = (flags & socket.NI_DGRAM) and 'udp' or 'tcp'
        port = socket.getservbyport(port, proto)

    return (host, port)

def is_ipv4_addr(host):
    """is_ipv4_addr returns true if host is a valid IPv4 address in
    dotted quad notation.
    """
    try:
        d1, d2, d3, d4 = map(int, host.split('.'))
    except (ValueError, AttributeError):
        return False

    if 0 <= d1 <= 255 and 0 <= d2 <= 255 and 0 <= d3 <= 255 and 0 <= d4 <= 255:
        return True

    return False

def _net_read(sock, count, expiration):
    """coro friendly replacement for dns.query._net_write
    Read the specified number of bytes from sock.  Keep trying until we
    either get the desired amount, or we hit EOF.
    A Timeout exception will be raised if the operation is not completed
    by the expiration time.
    """
    s = ''
    while count > 0:
        try:
            n = sock.recv(count)
        except coro.TimeoutError:
            ## Q: Do we also need to catch coro.CoroutineSocketWake and pass?
            if expiration - time.time() <= 0.0:
                raise dns.exception.Timeout
        if n == '':
            raise EOFError
        count = count - len(n)
        s = s + n
    return s

def _net_write(sock, data, expiration):
    """coro friendly replacement for dns.query._net_write
    Write the specified data to the socket.
    A Timeout exception will be raised if the operation is not completed
    by the expiration time.
    """
    current = 0
    l = len(data)
    while current < l:
        try:
            current += sock.send(data[current:])
        except coro.TimeoutError:
            ## Q: Do we also need to catch coro.CoroutineSocketWake and pass?
            if expiration - time.time() <= 0.0:
                raise dns.exception.Timeout

def udp(
    q, where, timeout=DNS_QUERY_TIMEOUT, port=53, af=None, source=None,
    source_port=0, ignore_unexpected=False):
    """coro friendly replacement for dns.query.udp
    Return the response obtained after sending a query via UDP.

    @param q: the query
    @type q: dns.message.Message
    @param where: where to send the message
    @type where: string containing an IPv4 or IPv6 address
    @param timeout: The number of seconds to wait before the query times out.
    If None, the default, wait forever.
    @type timeout: float
    @param port: The port to which to send the message.  The default is 53.
    @type port: int
    @param af: the address family to use.  The default is None, which
    causes the address family to use to be inferred from the form of of where.
    If the inference attempt fails, AF_INET is used.
    @type af: int
    @rtype: dns.message.Message object
    @param source: source address.  The default is the IPv4 wildcard address.
    @type source: string
    @param source_port: The port from which to send the message.
    The default is 0.
    @type source_port: int
    @param ignore_unexpected: If True, ignore responses from unexpected
    sources.  The default is False.
    @type ignore_unexpected: bool"""

    wire = q.to_wire()
    if af is None:
        try:
            af = dns.inet.af_for_address(where)
        except:
            af = dns.inet.AF_INET
    if af == dns.inet.AF_INET:
        destination = (where, port)
        if source is not None:
            source = (source, source_port)
    elif af == dns.inet.AF_INET6:
        destination = (where, port, 0, 0)
        if source is not None:
            source = (source, source_port, 0, 0)

    s = socket.socket(af, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        expiration = dns.query._compute_expiration(timeout)
        if source is not None:
            s.bind(source)
        try:
            s.sendto(wire, destination)
        except coro.TimeoutError:
            ## Q: Do we also need to catch coro.CoroutineSocketWake and pass?
            if expiration - time.time() <= 0.0:
                raise dns.exception.Timeout
        while 1:
            try:
                (wire, from_address) = s.recvfrom(65535)
            except coro.TimeoutError:
                ## Q: Do we also need to catch coro.CoroutineSocketWake and pass?
                if expiration - time.time() <= 0.0:
                    raise dns.exception.Timeout
            if from_address == destination:
                break
            if not ignore_unexpected:
                raise dns.query.UnexpectedSource(
                    'got a response from %s instead of %s'
                    % (from_address, destination))
    finally:
        s.close()
    r = dns.message.from_wire(wire, keyring=q.keyring, request_mac=q.mac)
    if not q.is_response(r):
        raise dns.query.BadResponse()
    return r

def tcp(q, where, timeout=DNS_QUERY_TIMEOUT, port=53,
    af=None, source=None, source_port=0):
    """coro friendly replacement for dns.query.tcp
    Return the response obtained after sending a query via TCP.

    @param q: the query
    @type q: dns.message.Message object
    @param where: where to send the message
    @type where: string containing an IPv4 or IPv6 address
    @param timeout: The number of seconds to wait before the query times out.
    If None, the default, wait forever.
    @type timeout: float
    @param port: The port to which to send the message.  The default is 53.
    @type port: int
    @param af: the address family to use.  The default is None, which
    causes the address family to use to be inferred from the form of of where.
    If the inference attempt fails, AF_INET is used.
    @type af: int
    @rtype: dns.message.Message object
    @param source: source address.  The default is the IPv4 wildcard address.
    @type source: string
    @param source_port: The port from which to send the message.
    The default is 0.
    @type source_port: int"""

    wire = q.to_wire()
    if af is None:
        try:
            af = dns.inet.af_for_address(where)
        except:
            af = dns.inet.AF_INET
    if af == dns.inet.AF_INET:
        destination = (where, port)
        if source is not None:
            source = (source, source_port)
    elif af == dns.inet.AF_INET6:
        destination = (where, port, 0, 0)
        if source is not None:
            source = (source, source_port, 0, 0)
    s = socket.socket(af, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        expiration = dns.query._compute_expiration(timeout)
        if source is not None:
            s.bind(source)
        try:
            s.connect(destination)
        except coro.TimeoutError:
            ## Q: Do we also need to catch coro.CoroutineSocketWake and pass?
            if expiration - time.time() <= 0.0:
                raise dns.exception.Timeout

        l = len(wire)
        # copying the wire into tcpmsg is inefficient, but lets us
        # avoid writev() or doing a short write that would get pushed
        # onto the net
        tcpmsg = struct.pack("!H", l) + wire
        _net_write(s, tcpmsg, expiration)
        ldata = _net_read(s, 2, expiration)
        (l,) = struct.unpack("!H", ldata)
        wire = _net_read(s, l, expiration)
    finally:
        s.close()
    r = dns.message.from_wire(wire, keyring=q.keyring, request_mac=q.mac)
    if not q.is_response(r):
        raise dns.query.BadResponse()
    return r

def emulate():
    """Resolve DNS with this module instead of the DNS resolution
    functionality that's baked into Python's socket module.
    """
    socket.getaddrinfo = getaddrinfo
    socket.gethostbyname = gethostbyname
    socket.gethostbyname_ex = gethostbyname_ex
    socket.getnameinfo = getnameinfo

    # Install our coro-friendly replacements for the tcp and udp
    # query methods.
    dns.query.tcp = tcp
    dns.query.udp = udp

def reset():
    resolver.clear()
    responses.reset(size = DNS_CACHE_MAXSIZE)

def main(argv=None):
    if argv is None: argv = sys.argv

    print "getaddrinfo('www.google.com', 80) returns: %s" % (
        getaddrinfo('www.google.com', 80), )
    print "getaddrinfo('www.slide.com', 80) returns: %s" % (
        getaddrinfo('www.slide.com', 80), )
    print "getaddrinfo('208.76.68.33', 80) returns: %s" % (
        getaddrinfo('208.76.68.33', 80), )
    try:
        getaddrinfo('bogus.ghosthacked.net', 80)
    except socket.gaierror:
        print "getaddrinfo('bogus.ghosthacked.net', 80) failed as expected."
    print

    print "gethostbyname('www.google.com') returns: %s" % (
        gethostbyname('www.google.com'), )
    print "gethostbyname('www.slide.com') returns: %s" % (
        gethostbyname('www.slide.com'), )
    print "gethostbyname('208.76.68.33') returns: %s" % (
        gethostbyname('208.76.68.33'), )
    try:
        gethostbyname('bogus.ghosthacked.net')
    except socket.gaierror:
        print "gethostbyname('bogus.ghosthacked.net') failed as expected."
    print

    print "gethostbyname_ex('www.google.com') returns: %s" % (
        gethostbyname_ex('www.google.com'), )
    print "gethostbyname_ex('www.slide.com') returns: %s" % (
        gethostbyname_ex('www.slide.com'), )
    print "gethostbyname_ex('208.76.68.33') returns: %s" % (
        gethostbyname_ex('208.76.68.33'), )
    try:
        gethostbyname_ex('bogus.ghosthacked.net')
    except socket.gaierror:
        print "gethostbyname_ex('bogus.ghosthacked.net') failed as expected."
    print

    try:
        getnameinfo(('www.google.com', 80), 0)
    except socket.error:
        print "getnameinfo(('www.google.com'), 80, 0) failed as expected."
    print "getnameinfo(('www.slide.com', 80), 0) returns: %s" % (
        getnameinfo(('www.slide.com', 80), 0), )
    print "getnameinfo(('208.76.68.33', 80), 0) returns: %s" % (
        getnameinfo(('208.76.68.33', 80), 0), )
    try:
        getnameinfo(('bogus.ghosthacked.net', 80), 0)
    except socket.gaierror:
        print "getnameinfo('bogus.ghosthacked.net') failed as expected."

    return 0

if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = pyinfo
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''pyinfo

Functions for gathering and presenting information about the running
python program.
'''

import sys

def rawstack(depth = 1):
    data = []

    while depth is not None:
        try:
            f = sys._getframe(depth)
        except ValueError:
            depth = None
        else:
            data.append((
                '/'.join(f.f_code.co_filename.split('/')[-2:]),
                f.f_code.co_name,
                f.f_lineno))
            depth += 1

    return data

def callstack(outfunc = sys.stdout.write, depth = 1, compact = False):
    data = rawstack(depth)
    data = map(lambda i: '%s:%s:%d' % i, data)

    if compact:
        return outfunc('|'.join(data))

    for value in data:
        outfunc(value)

    return None
#
# end...

########NEW FILE########
__FILENAME__ = sendfd
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''sendfd.py

Wrapper functions for sending/receiving a socket between two
unix socket domain endpoints in a coro environment
'''

import os
import struct
import socket

import coro
import sendmsg


def sendsocket(control, identifier, sock):
    payload = struct.pack('i', sock.fileno())

    control.wait_for_write()
    sendmsg.sendmsg(
        control.fileno(),
        identifier,
        0,
        (socket.SOL_SOCKET, sendmsg.SCM_RIGHTS, payload))


def recvsocket(control):
    control.wait_for_read()
    result = sendmsg.recvmsg(control.fileno())

    identifier, flags, [(level, type, data)] = result

    fd = struct.unpack('i', data)[0]
    try:
        sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
        sock = coro.coroutine_socket(sock)
    finally:
        os.close(fd)

    return sock




########NEW FILE########
__FILENAME__ = start
from gogreen import coro
from gogreen import emulate
from gogreen import purepydns

import prctl

import logging
import sys
import os
import getopt
import resource
import curses
import errno
import stat
import getpass
import socket

import logging
import logging.handlers

emulate.init()
purepydns.emulate()

LOG_SIZE_MAX  = 16*1024*1024
LOG_COUNT_MAX = 50

SERVER_MAX_FD = 32768

SRV_LOG_FRMT = '[%(name)s|%(coro)s|%(asctime)s|%(levelname)s] %(message)s'
LOGLEVELS = dict(
    CRITICAL=logging.CRITICAL, DEBUG=logging.DEBUG, ERROR=logging.ERROR,
    FATAL=logging.FATAL, INFO=logging.INFO, WARN=logging.WARN,
    WARNING=logging.WARNING,INSANE=5)

class GreenFormatter(object):
    def __init__(self, fmt = SRV_LOG_FRMT, width = 0):
        self.fmt = logging.Formatter(fmt)
        self.width = width
    def set_width(self, width):
        self.width = width
    def formatTime(self, record, datefmt=None):
        return self.fmt.formatTime(record, datefmt)
    def formatException(self, ei):
        return self.fmt.formatException(ei)
    def format(self, record):
        msg = self.fmt.format(record)
        if self.width:
            return msg[:self.width]
        else:
            return msg

def get_local_servers(config_map, user = None):
    """get_local_servers returns a dictionary keyed by server ids of
    all configuration blocks from config_map for servers that run as
    the current user on the local machine.  The dictionary is keyed 
    list of configuration blocks all server configurations in
    config_map.
    """
    local_srvs = {}
    user = user or getpass.getuser()
    name = socket.gethostname()
    for id, server in config_map.items():
        if server.get('host', 'localhost') in [name, 'localhost'] and \
            user == server.get('user', user):
            local_srvs[id] = server

    return local_srvs


def _lock(server):
    """_lock attempt to bind and listen to server's lockport.
    Returns the listening socket object on success.
    Raises socket.error if the port is already locked.
    """
    s = coro.make_socket(socket.AF_INET, socket.SOCK_STREAM)
    s.set_reuse_addr()
    s.bind((server.get('bind_ip', ''), server['lockport']))
    s.listen(1024)

    return s

def lock_node(config_map, id=None):
    if id is None:
        for id, server in get_local_servers(config_map).items():
            try:
                s = _lock(server)
            except socket.error:
                pass
            else:
                server['lock']  = s
                server['total'] = len(config_map)
                server['id']    = id
                return server
    else:
        server = get_local_servers(config_map)[id]
        try:
            s = _lock(server)
        except socket.error:
            pass
        else:
            server['lock']  = s
            server['total'] = len(config_map)
            server['id']    = id
            return server

    return None # unused value


BASE_COMMAND_LINE_ARGS = [
    'help', 'fork', 'nowrap', 'logfile=', 'loglevel=', 'pidfile=',
    ]

def usage(name, error = None):
    if error:
        print 'Error:', error
    print "  usage: %s [options]" % name

def main(
    serv_dict, exec_func,
    name = 'none', base_dir = '.', arg_list = [], defaults = {},
    prefork = None):

    log = coro.coroutine_logger(name)
    fmt = GreenFormatter()

    log.setLevel(logging.DEBUG)
    #
    # check for argument collisions
    #
    extra = set(map(lambda i: i.strip('='), arg_list))
    base  = set(map(lambda i: i.strip('='), BASE_COMMAND_LINE_ARGS))
    both  = tuple(extra & base)

    if both:
        raise AttributeError(
            'Collision between standard and extended command line arguments',
            both)

    progname = sys.argv[0]
    #
    # internal parameter defaults
    #
    max_fd   = defaults.get('max_fd', SERVER_MAX_FD)
    loglevel = 'INFO'
    logdir   = None
    logfile  = None
    pidfile  = None
    dofork   = False
    linewrap = True
    #
    # setup defaults for true/false parameters
    #
    parameters = {}

    for key in filter(lambda i: not i.endswith('='), arg_list):
        parameters[key] = False

    dirname  = os.path.dirname(os.path.abspath(progname))
    os.chdir(dirname)

    try:
        list, args = getopt.getopt(
            sys.argv[1:],
            [],
            BASE_COMMAND_LINE_ARGS + arg_list)
    except getopt.error, why:
        usage(progname, why)
        return None

    for (field, val) in list:
        field = field.strip('-')

        if field == 'help':
            usage(progname)
            return None
        elif field == 'nowrap':
            linewrap = False
        elif field == 'logfile':
            logfile = val
        elif field == 'loglevel':
            loglevel = val
        elif field == 'pidfile':
            pidfile = val
        elif field == 'fork':
            dofork = True
        elif field in extra:
            if field in arg_list:
                parameters[field] = True
            else:
                try:
                    parameters[field] = int(val)
                except (TypeError, ValueError):
                    parameters[field] = val

    # init
    here = lock_node(serv_dict)
    if here is None:
        return 128

    if 'logdir' in here:
        logdir = os.path.join(base_dir, here['logdir'])
        try:
            value = os.stat(logdir)
        except OSError, e:
            if errno.ENOENT == e[0]:
                os.makedirs(logdir)
                os.chmod(logdir, stat.S_IRWXU|stat.S_IRWXG|stat.S_IRWXO)
            else:
                print 'logdir lookup error: %r' % (e,)
                return 127

    if prefork is not None:
        parameters['prefork'] = prefork()

    if dofork:
        pid = os.fork()
        if pid:
            return 0

    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (max_fd, max_fd))
    except ValueError, e:
        if not os.getuid():
            print 'MAX FD error: %s, %d' % (e.args[0], max_fd)
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (-1, -1))
    except ValueError, e:
        print 'CORE size error:', e

    if not os.getuid():
        os.setgid(1)
        os.setuid(1)

    try:
        prctl.prctl(prctl.DUMPABLE, 1)
    except (AttributeError, ValueError, prctl.PrctlError), e:
        print 'PRCTL DUMPABLE error:', e

    if logdir and pidfile:
        pidfile = logdir + '/' + pidfile
        try:
            fd = open(pidfile, 'w')
        except IOError, e:
            print 'IO error: %s' % (e.args[1])
            return None
        else:
            fd.write('%d' % os.getpid())
            fd.close()

    if logdir and logfile:
        logfile = logdir + '/' + logfile
        hndlr = logging.handlers.RotatingFileHandler(
            logfile, 'a', LOG_SIZE_MAX, LOG_COUNT_MAX)
        
        os.close(sys.stdin.fileno())
        os.close(sys.stdout.fileno())
        os.close(sys.stderr.fileno())
    else:
        if not linewrap:
            win = curses.initscr()
            height, width = win.getmaxyx()
            win = None
            curses.reset_shell_mode()
            curses.endwin()

            fmt.set_width(width)
            
        hndlr = logging.StreamHandler(sys.stdout)

    sys.stdout = coro.coroutine_stdout(log)
    sys.stderr = coro.coroutine_stderr(log)

    hndlr.setFormatter(fmt)
    log.addHandler(hndlr)
    loglevel = LOGLEVELS.get(loglevel, None)
    if loglevel is None:
        log.warn('Unknown logging level, using INFO: %r' % (loglevel, ))
        loglevel = logging.INFO

    max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
    log.info('uid: %d, gid: %d, max fd: %d' % (os.getuid(),os.getgid(),max_fd))

    result = exec_func(here, log, loglevel, logdir, **parameters)
    
    if result is not None:
        log.critical('Server exiting: %r' % (result,))
    else:
        log.critical('Server exit')

    return 0

########NEW FILE########
__FILENAME__ = statistics
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''statistics

Maintain second resolution statistics which can then be consolidated into
statistics for multiple time periods.
'''

import time
import bisect

QUEUE_PERIOD = [15, 60, 300, 600]
QUEUE_DEPTH  = QUEUE_PERIOD[-1]
HEAP_LIMIT   = 128

class Recorder(object):
    def __init__(self, depth = QUEUE_DEPTH, period = QUEUE_PERIOD):
        self._global = [{'timestamp': 0, 'elapse': 0, 'count': 0}]
        self._local  = {}
        self._depth  = depth
        self._period = period

    def _local_request(self, elapse, name, current):
        #
        # track average request time per second for a given period
        #
        record = self._local.setdefault(name, [])

        if not record or record[-1]['timestamp'] != current:
            record.append({'timestamp': current, 'elapse': 0, 'count': 0})

        record[-1]['count']  += 1
        record[-1]['elapse'] += int(elapse * 1000000)
        #
        # clear old entries
        #
        while len(record) > self._depth:
            del(record[0])

    def _global_request(self, elapse, current):
        #
        # track average request time per second for a given period
        #
        if self._global[-1]['timestamp'] != current:
            self._global.append({'timestamp': current,'elapse': 0,'count': 0})

        self._global[-1]['count']  += 1
        self._global[-1]['elapse'] += int(elapse * 1000000)
        #
        # clear old entries
        #
        while len(self._global) > self._depth:
            del(self._global[0])
    #
    # info API
    #
    def last(self):
        return self._global[-1]['timestamp']
    #
    # logging API
    #
    def request(self, elapse, name = 'none', current = None):
        if current is None:
            current = int(time.time())
        else:
            current = int(current)

        self._local_request(elapse, name, current)
        self._global_request(elapse, current)
    #
    # query API
    #
    def rate(self, current = None):
        current = current or int(time.time())
        results = []
        index   = 0

        timestamps, counts  = zip(*map(
            lambda x: (x['timestamp'], x['count']),
            self._global))

        for period in self._period[::-1]:
            index = bisect.bisect(timestamps, (current - period), index)
            results.append(sum(counts[index:])/period)

        return results[::-1]

    def details(self, current = None):
        current = current or int(time.time())
        results = {}

        for name, record in self._local.items():
            results[name] = []
            index = 0

            timestamps, counts, elapse = zip(*map(
                lambda x: (x['timestamp'], x['count'], x['elapse']),
                record))

            for period in self._period[::-1]:
                index = bisect.bisect(timestamps, (current - period), index)
                results[name].append({
                    'count':   sum(counts[index:]),
                    'elapse':  sum(elapse[index:]),
                    'seconds': period})

            results[name].reverse()
        return results

    def averages(self, current = None):
        current = current or int(time.time())
        results = []
        index   = 0

        timestamps, counts, elapse  = zip(*map(
            lambda x: (x['timestamp'], x['count'], x['elapse']),
            self._global))

        for period in self._period[::-1]:
            index = bisect.bisect(timestamps, (current - period), index)
            reqs  = sum(counts[index:])

            results.append({
                'count':   reqs/period,
                'elapse':  (reqs and sum(elapse[index:])/reqs) or 0,
                'seconds': period})

        return results[::-1]


class RecorderHitRate(object):
    def __init__(self, depth = QUEUE_DEPTH, period = QUEUE_PERIOD):
        self._global = [(0, 0, 0)]
        self._depth  = depth
        self._period = period
    #
    # logging API
    #
    def request(self, hit = True, current = None):
        if current is None:
            current = int(time.time())
        else:
            current = int(current)

        pos = int(hit)
        neg = int(not hit)

        if self._global[-1][0] != current:
            self._global.append((current, pos, neg))
        else:
            current, oldpos, oldneg = self._global[-1]
            self._global[-1] = (current, oldpos + pos, oldneg + neg)

        while len(self._global) > self._depth:
            del(self._global[0])
    #
    # query API
    #
    def data(self):
        current = int(time.time())
        results = []
        index   = 0

        timelist, poslist, neglist = zip(*self._global)

        for period in self._period[::-1]:
            index = bisect.bisect(timelist, (current - period), index)

            pos = sum(poslist[index:])
            neg = sum(neglist[index:])

            results.append((pos, neg))

        return results[::-1]

    def rate(self):
        return map(
            lambda i: sum(i) and float(i[0])/sum(i) or None,
            self.data())

class WQSizeRecorder(object):

    def __init__(self, depth = QUEUE_DEPTH, period = QUEUE_PERIOD):
        self._global = [(0, 0, 0)]
        self._depth  = depth
        self._period = period

    # logging API
    def request(self, size, current = None):
        if current is None:
            current = int(time.time())
        else:
            current = int(current)

        size = int(size)

        if self._global[-1][0] != current:
            self._global.append((current, size, 1))
        else:
            current, oldsize, oldcnt = self._global[-1]
            self._global[-1] = (current, oldsize + size, oldcnt + 1)

        while len(self._global) > self._depth:
            del(self._global[0])

    # query api
    def sizes(self):
        current = int(time.time())
        results = []
        index   = 0

        timelist, sizelist, cntlist = zip(*self._global)

        for period in self._period[::-1]:
            index = bisect.bisect(timelist, (current - period), index)

            sizes = sizelist[index:]
            cnts  = cntlist[index:]
            results.append((sum(sizes), len(sizes)+sum(cnts)))

        return results[::-1]

class TopRecorder(object):
    def __init__(self, depth = HEAP_LIMIT, threshold = None):
        self._heap  = [(0, None)]
        self._depth = depth
        self._hold  = threshold

    def fetch(self, limit = None):
        if limit:
            return self._heap[-limit:]
        else:
            return self._heap

    def save(self, value, data):
        if not value > self._hold:
            return None

        if value < self._heap[0][0]:
            return None

        bisect.insort(self._heap, (value, data))

        while len(self._heap) > self._depth:
            del(self._heap[0])
#
# end..

########NEW FILE########
__FILENAME__ = ultramini
# -*- Mode: Python; tab-width: 4 -*-

# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Ultra mini lightweight framework
"""

import os, re, types, urllib, cgi, cStringIO, sys, tempfile, Cookie
import exceptions

try:
    import amf
except:
    amf = None
try:
    import amfast
except:
    amfast = None

class LocationDeprecationWarning(DeprecationWarning):
    pass


class xml(object):
    """An object which contains only xml bytes.
    """
    def __init__(self, string):
        self.string = string


####################
####################
## Argument Converters
####################
####################


def arguments(*args):
    """A Decorator which you wrap around a function or a method to indicate
    which magical objects you want passed to your functions which are
    embedded in a Resource's template.

    The magical values you can pass are:
        LOCATION
        REQUEST
        SITE
        RESOURCE
        METHOD
        URI

    For example, to pass a function the SiteMap instance, do this:

        @arguments(SITE)
        def foo(site):
            print "The site!"

    The values which you pass a string argument to get variables out of the
    request environment (which also take a default) are:

        QUERY
        QUERIES
        ARG
        ARGS
        COOKIE
        HEADER

    For example, to pass a query parameter to a function, with a default
    if the parameter is not present, do this:

        @arguments(QUERY('foo', 'default'))
        def foo(foo):
            print foo

    All the magic objects which take string values have a __getattr__
    implementation for syntatic convenience when you do not need to
    pass a default value (None will be used as the default value):

        @arguments(QUERY.foo)
        def foo(foo):
            print foo
    """
    def decorate(func):
        func.arguments = args
        return func
    return decorate


class LOCATION(object):
    """The Location object representing the URL currently being rendered.
    """


class REQUEST(object):
    """The Request object representing the current web request.
    """


class SITE(object):
    """The SiteMap object in which the resource which is currently being
    rendered resides.
    """


class RESOURCE(object):
    """The currently-being-rendered resource.
    """


class METHOD(object):
    """The method of the current request.
    """


class URI(object):
    """The URI of the current request.
    """


class Thing(object):
    """A lazy thing. Lazy things have a name and a default
    value, and are looked up lazily from the request environment.
    """
    def __init__(self, name, default=None):
        self.name = name
        self.default = default

    def __getattr__(self, name):
        return type(self)(name)

    def __call__(self, name, default=None):
        return type(self)(name, default)


class QUERY(Thing):
    """A query argument (url parameter)
    """


class QUERIES(Thing):
    """Produce a generator of all query arguments with the given name
    """


class ARG(Thing):
    """A form post variable.
    """


class ARGS(Thing):
    """All form post variables with the given name.
    """


class COOKIE(Thing):
    """A cookie with the given name.
    """


class HEADER(Thing):
    """A header with the given name.
    """


def getQueries(request, arg):
    queries = tuple(request.get_query(arg.name))
    if not queries:
        return arg.default
    return queries


def getQuery(request, arg):
    queries = getQueries(request, arg)
    if queries == arg.default:
        return arg.default
    return queries[0]


def getArgs(request, arg):
    val = request.get_arg_list(arg.name)
    if not val:
        return arg.default
    return val


def getCookie(request, arg):
    """get a cookie woot.
    """
    if not hasattr(request, '_simple_cookie'):
        cookie = request.get_header('Cookie')
        if not cookie:
            return arg.default
        c = Cookie.SimpleCookie()
        c.load(cookie)
        request._simple_cookie = c
    cook_value = request._simple_cookie.get(arg.name)
    if cook_value and cook_value.value:
        return cook_value.value
    return arg.default


def getLocation(request, arg):
    import warnings
    if True:
        warnings.warn(
            "The location is deprecated. Use the request instead.",
            LocationDeprecationWarning, 2)
    return request


## Argument converters are passed to the "arguments" decorator.
## Immediately before the decorated function is called, they are invoked.
## They are passed information about the current request
## and they should return the lazy value they represent.
argumentConverters = {
    LOCATION: getLocation,
    REQUEST: lambda request, arg: request,
    SITE: lambda request, arg: request.site,
    RESOURCE: lambda request, arg: request.resource,
    METHOD: lambda request, arg: request.method(),
    URI: lambda request, arg: request.uri(),
    QUERY: getQuery,
    QUERIES: getQueries,
    ARG: lambda request, arg: request.get_arg(arg.name, arg.default),
    ARGS: getArgs,
    COOKIE: getCookie,
    HEADER: lambda request, arg: request.get_header(arg.name, arg.default),
}


## These things are all prototype objects; they have __getattr__
## and __call__ factories which are used for generating clones
## of them. The lines below make the names that people use
## into instances instead of classes.
LOCATION = LOCATION()
REQUEST = REQUEST()
SITE = SITE()
RESOURCE = RESOURCE()
METHOD = METHOD()
URI = URI()
QUERY = QUERY('')
QUERIES = QUERIES('')
ARG = ARG('')
ARGS = ARGS('')
COOKIE = COOKIE('')
HEADER = HEADER('')


####################
####################
## End Argument Converters
####################
####################


####################
####################
## Rendering Converters
####################
####################


## Rendering converters
## When objects are placed into a DOM which is rendered to be
## sent to the client as HTML, they are run through a series
## of rendering converters until nothing but a single "xml"
## instance is left.

def convertFunction(request, function):
    args = []
    for arg in getattr(function, 'arguments', ()):
        converter = argumentConverters.get(type(arg))
        if converter is None:
            args.append(arg)
        else:
            args.append(converter(request, arg))

    return function(*args)


convertSequence = lambda request, sequence: xml(
    ''.join([request.convert(request, x) for x in sequence]))


convertNumber = lambda request, number: xml(str(number))


class show(object):
    """A marker which will lazily look up a show_* method
    from the currently-being-rendered resource when encountered
    in a template.
    """
    def __init__(self, name, args=()):
        self.name = name
        self.args = args

    def __getattr__(self, name):
        return type(self)(name)

    def __call__(self, *args):
        return type(self)(self.name, self.args + args)

    def __iter__(self):
        return iter(())


def convertShow(request, theDirective):
    @arguments(RESOURCE, *theDirective.args)
    def convert(resource, *args):
        return getattr(resource, "show_%s" % (theDirective.name, ))(*args)
    return convert


class stan(object):
    def __init__(
        self, tag, attributes, children, pattern=None, show=None, clone=False):
        (self.tag, self.attributes, self.children, self.pattern, self.show,
         self.clone) = (
            tag, attributes, children, pattern, show, clone)

    def __getitem__(self, args):
        """Add child nodes to this tag.
        """
        if not isinstance(args, (tuple, list)):
            args = (args, )
        if not isinstance(args, list):
            args = list(args)
        if self.clone:
            return type(self)(
                self.tag, self.attributes.copy(), [
                    x for x in self.children] + args,
                self.pattern, self.show, False)
        self.children.extend(args)
        return self

    def __call__(self, **kw):
        """Set attributes of this tag. There are two special names
        which are reserved:

            pattern
                Make it possible to find this node later using the
                findPattern function

            show
                When this node is rendered, instead render the
                value passed as the "show" value.
        """
        if kw.has_key('pattern'):
            pattern = kw.pop('pattern')
        else:
            pattern = self.pattern

        if kw.has_key('show'):
            show = kw.pop('show')
        else:
            show = self.show

        if self.clone:
            newattrs = self.attributes.copy()
            newattrs.update(kw)
            return type(self)(
                self.tag, newattrs, self.children[:], pattern, show, False)
        self.attributes.update(kw)
        self.pattern = pattern
        self.show = show
        return self

    def cloneNode(self):
        return type(self)(
            self.tag, self.attributes.copy(), self.children[:], None,
            self.show, False)


def tagFactory(tagName):
    return stan(tagName, {}, [], None, None, True)


def findPattern(someStan, targetPattern):
    """Find a node marked with the given pattern, "targetPattern",
    in a DOM object, "someStan"
    """
    pat = getattr(someStan, 'pattern', None)
    if pat == targetPattern:
        return someStan.cloneNode()
    for child in getattr(someStan, 'children', []):
        result = findPattern(child, targetPattern)
        if result is not None:
            return result.cloneNode()


## TODO: Inline elements shouldn't have any whitespace after them or before
## the closing tag.


def convertStan(request, theStan):
    ## XXX this probably isn't necessary
    request.tag = theStan
    if theStan.show is not None:
        return theStan.show
    if theStan.pattern is not None:
        return xml('')

    attrs = ''
    if theStan.attributes:
        for key, value in theStan.attributes.items():
            attrs += ' %s="%s"' % (
                key, request.convert(request, value).replace('"', '&quot;'))
    #"
    depth = getattr(request, 'depth', 0)
    indent = '  ' * depth
    request.depth = depth + 1
    if theStan.tag in inline_elements:
        template = """<%(tag)s%(attrs)s>%(children)s</%(tag)s>"""
    else:
        template = """
%(indent)s<%(tag)s%(attrs)s>
%(indent)s  %(children)s
%(indent)s</%(tag)s>
"""
    result = template % dict(
        indent=indent, tag=theStan.tag, attrs=attrs,
        children=request.convert(request, theStan.children).strip())

    request.depth -= 1
    return xml(result)


inline_elements = [
    'a', 'abbr', 'acronym', 'b', 'basefont', 'bdo', 'big', 'br', 'cite',
    'code', 'dfn', 'em', 'font', 'i', 'img', 'input', 'kbd', 'label',
    'q', 's', 'samp', 'select', 'small', 'span', 'strike', 'strong',
    'sub', 'sup', 'textarea', 'tt', 'u', 'var']
inline_elements = dict((x, True) for x in inline_elements)


tags_to_create = [
'a','abbr','acronym','address','applet','area','b','base','basefont','bdo',
'big','blockquote','body','br','button','caption','center','cite','code',
'col','colgroup','dd','dfn','div','dl','dt','em','fieldset','font','form',
'frame','frameset','h1','h2','h3','h4','h5','h6','head','hr','html','i',
'iframe','img','input','ins','isindex','kbd','label','legend','li','link',
'menu','meta','noframes','noscript','ol','optgroup','option','p','param',
'pre','q','s','samp','script','select','small','span','strike','strong',
'style','sub','sup','table','tbody','td','textarea','tfoot','th','thead',
'title','tr','tt','u','ul','var'
]


class tags(object):
    """A namespace for tags, so one can say "from ultramini import tags"
    and have access to all tags as tags.html, tags.foo, etc
    """
    pass


for tag in tags_to_create:
    T = tagFactory(tag)
    globals()[tag] = T
    setattr(tags, tag, T)
del tag
del T
del tags_to_create


converters = {
    unicode: lambda request, uni: uni.encode('utf8'),
    list: convertSequence,
    tuple: convertSequence,
    types.GeneratorType: convertSequence,
    types.FunctionType: convertFunction,
    types.MethodType: convertFunction,
    types.UnboundMethodType: convertFunction,
    int: convertNumber,
    float: convertNumber,
    long: convertNumber,
    show: convertShow,
    stan: convertStan,
    str: lambda request, string: xml(
        string.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
}
converters.update(argumentConverters)


show = show('')


def registerConverter(convertType, converter):
    """Call this to register a converter for one of your custom types.
    """
    converters[convertType] = converter


def convert(request, stuff):
    """Recursively apply stuff converters until we get an xml instance.
    """
    while not isinstance(stuff, xml):
        convert = converters.get(type(stuff))
        if convert is None:
            raise RuntimeError, "Converter for type %r (%r) not found." % (
                type(stuff), stuff)
        stuff = convert(request, stuff)
    return stuff.string


####################
####################
## End Rendering Converters
####################
####################



####################
####################
## Incoming Type Converters
####################
####################


## When arguments come in (as GET url parameters or POST arguments)
## they can be converted from strings to Python types using incoming
## type converters. To use them, wrap a get_* or post_* method
## using the annotate decorator. When a get_ or post_ method
## is called (by having a corresponding ?get= parameter or action
## argument) the arguments named in the decorator will be converted
## before they are passed to the method.


def annotate(*args, **kwargs):
    '''annotate

      A decorator which annotates a handler function (GET and/or POST
    method) with pre and/or post request filter functions as well as
    mapping functions for each argument the action method will receive.

    First argument: return converter(s)

        The return value converter, if present, can be either a single
      callable or a list of callables. The return value of the annotated
      function is passed as the only argument to the callable and the
      callable returns a string which is sent as the body of the HTTP
      response. When the return converter is a list of callables the call
      argument and return value of each are chained together. Only the
      last callable needs to return a string for the body of the HTTP
      response. If the first argument is not present then the return
      value of the annotated function must be a string which will be the
      body of the HTTP response.


    Second argument: input converter(s)

        The second argument, if present, is the input converter, and can
      be either a single callable or a list of callables. Each is called
      with three arguments; 1) the handler instance to which the annotated
      method belongs, 2) the request object, 3) the request field storage,
      in the case of a POST, or the request query parameters, in the case
      of a GET, represented as a dictionary. The return value can either be
      None, or a new dictionary representation of the third argument which
      will be chained into the next input converter callable and/or used
      for the annotated mapping functions described in the next section.

    Keyword arguments: action mapping functions

        Each keyword argument is either a callable or one of the well
      known constants below. In both cases each keyword represents the
      method parameter of the same name.

        In the case that the keyword argument is set to one of the well
      known constants the object/data represented by the constants, as
      described below, will be passed into the method as the parameter
      of the same name as the keyword argument.

        In the case that the keyword argument is a callable AND there is
      a query parameter, in the case of a GET, or a field argument, in
      the case of a POST, of the same name, then the value of the request
      parameter/argument is passed into the callable. The result of the
      callable is then passed into the method as the parameter
      of the same name as the keyword argument.

    Keyword argument constants:

      (used as annotation types for retrieving specific information about
       the request)

      REQUEST - request (corohttpd.HttpRequest)
      COOKIE  - cookies (Cookie.SimpleCookie)    request.get_cookie()
      HEADER  - HTTP header  (mimetools.Message) request.get_headers()
      METHOD  - HTTP method (str)                request.method()
      URI     - HTTP uri (str)                   request.uri()
      QUERIES - query parameters (list)          request.get_query_pairs()
      ARGS    - arguments (cgi.FieldStorage)     request.get_field_storage()


    Examples:

    To expose a method to be called by placing ?action=foo
    in the query string with a single parameter bar of type int:
    (e.g. /handler?action=foo&bar=2)

    @method()
    @annotate(bar = int)
    def action_foo(self, bar):
        print bar

    To express lists of things:

    @method()
    @annotate(bar=[int])
    def action_foo(self, bar):
        for someInt in bar:
            print someInt

    Include converters; return converter to ensure a string response, a
    input converter to decode the crypto on bar:


    def fini(value):
        return str(value)

    def init(rec, req, param):
        if param.has_key('bar'):
            param['bar'] = decode(param['bar'])
        return param

    @annotate(fini, init, bar = int)
    def get_default(self, bar = 0):
        print bar
        return 2 * bar

    Include request object to set response header:

    @annotate(fini, init, req = REQUEST, bar = int)
    def get_default(self, req, bar = 0):
        print bar
        req.set_header('X-Bar', bar)
        return 2 * bar
    '''
    TODO = '''

    Dicts of things should be expressed by presenting
    arguments with a common prefix separated by a dot. For
    example:

    ?get=foo&someDict.bar=1&someDict.baz=foo

    Would call:

    @annotate(someDict={bar: int, baz: str})
    def get_foo(self, someDict):
        print someDict['bar']
        print someDict['baz']

    This is still TODO. (Perhaps colon instead of dot?)
    '''

    returnConverter = args and args[0]
    inputConverter = None
    if len(args) == 2:
        inputConverter = args[1]
    def decorate(method):
        method.returnConverter = returnConverter
        method.inputConverter = inputConverter
        method.types = kwargs
        return method
    return decorate


def convertList(request, theList):
    request.target = request.target[0]
    if not isinstance(theList, list):
        theList = [theList]
    return [convertTypes(request, item) for item in theList]


def convertTuple(request, theTuple):
    stuff = []
    for i, subtype in enumerate(request.target):
        request.target = subtype
        stuff.append(convertTypes(request, theTuple[i]))
    return tuple(stuff)


def convertDict(request, nothing):
    theDict = {}
    for field in request.get_field_storage().list:
        if field.name.startswith(request.target_name + '.'):
            theDict[field.name.split('.', 1)[-1]] = field.value
    target = request.target
    result = {}
    for (key, value) in target.items():
        request.target = value
        result[key] = convertTypes(request, theDict[key])
    return result


typeConverters = converters.copy()
typeConverters.update({
    int: lambda target, value: int(value),
    float: lambda target, value: float(value),
    list: convertList,
    tuple: convertTuple,
    dict: convertDict,
    str: lambda target, value: value,
    unicode: lambda target, value: value.decode('utf8'),
    types.FunctionType: lambda request, value: request.target(request, value),
    object: lambda target, value: value,
    bool: lambda target, value: bool(value),

    type(REQUEST): lambda request, value: request,
    type(SITE): lambda request, value: request.site,
    type(RESOURCE): lambda request, value: request.resource,
    type(METHOD): lambda request, value: request.method(),
    type(URI): lambda request, value: request.uri(),
    type(QUERIES): lambda request, value: request.get_query_pairs(),
    type(ARGS): lambda request, value: request.get_field_storage(),
    type(COOKIE): lambda request, value: request.get_cookie(),
    type(HEADER): lambda request, value: request.get_headers(),
})


def registerTypeConverter(convertType, converter):
    typeConverters[convertType] = converter


def convertTypes(request, value):
    target = request.target
    converter = typeConverters.get(type(target))
    if converter is None:
        converter = typeConverters.get(target)
    if converter is None:
        raise ValueError, "No converter for type %s (%s)" % (target, value)
    return converter(request, value)


def storage_to_dict(fs):
    rc = {}
    for k, v in dict(fs).iteritems():
        if isinstance(v, list):
            rc[k] = [isinstance(e, cgi.MiniFieldStorage) and e.value or e for e in v]
        elif isinstance(v, basestring):
            rc[k] = v
        elif not hasattr(v, 'value'):
            rc[k] = v
        else:
            rc[k] = v.value
    return rc

def applyWithTypeConversion(callable_method, request, **kwargs):
    '''
        Currently useful kwargs:
            `resource` => instance of the resource executing
    '''
    types = getattr(callable_method, 'types', {})
    returnConverter = getattr(callable_method, 'returnConverter', None)
    inputConverter = getattr(callable_method, 'inputConverter', None)

    fs = request.get_field_storage()
    parameters = storage_to_dict(fs)

    if inputConverter:
        if not isinstance(inputConverter, (list, tuple)):
            inputConverter = (inputConverter, )

        for conv in inputConverter:
            rc = conv(kwargs.get('resource'), request, parameters)
            parameters = rc or parameters

    try:
        converted = {}
        for (key, value) in types.items():
            request.target_name = key
            request.target = value
            if parameters.has_key(key):
                val = parameters[key]
            else:
                val = getattr(value, 'default', None)

            try:
                val = convertTypes(request, val)
            except (TypeError, ValueError):
                val = None

            if val is not None:
                converted[key] = val

        result = callable_method(**converted)
    except TypeError:
        raise
    if result is None:
        result = ''
    if not returnConverter:
        return False, result

    if not isinstance(returnConverter, (list, tuple)):
        returnConverter = (returnConverter, )

    for conv in returnConverter:
        result = conv(result)

    return True, result


##AMF Converter Support
class AMFDecodeException(exceptions.Exception):
    pass

class AMFFieldStorage(cgi.FieldStorage):
    def __init__(self, *args, **kwargs):
        self.classmapper = kwargs.pop('class_mapper', None)
        cgi.FieldStorage.__init__(self, *args, **kwargs)

    def read_single(self):
        qs = self.fp.read(self.length)
        if qs.strip() == '':
            raise AMFDecodeException('empty AMF data on decode')
        ct = amfast.context.DecoderContext(qs, amf3=True,
                class_def_mapper=self.classmapper)
        data = amfast.decoder.decode(ct)
        ct = None

        self.list = [cgi.MiniFieldStorage(k,v) for k,v in data.amf_payload.iteritems()]
        self.skip_lines()

####################
####################
## End Incoming Converters
####################
####################



####################
####################
## URL Traversal
####################
####################


## SiteMap has a root Resource and traverses the URL using the Resource
## interface.


class SiteMap(object):
    """An object which is capable of matching Resource objects to URLs and
    delegating rendering responsibility to the matched object.

    This class implements the corohttpd handler interface: match
    and handle_request. It adapts this interface to something more similar
    to the Nevow URL traversal interface: findChild and handle (like
    locateChild and renderHTTP in Nevow).
    """
    def __init__(self, root, **parameters):
        self.root   = root
        root.child_ = root

        self.__dict__.update(parameters)

    def __del__(self):
        self.root._clear_child_()

    def match(self, request):
        request.site = self

        remaining = tuple(request._path.split('/')[1:])
        if request._path.find('://') < 0:
            # Provided our path doesn't contain another URL, trim redundant slashes
            parts = request._path.split('/')[1:]
            remaining = tuple((s for i, s in enumerate(parts) if s or i == (len(parts) - 1)))

        child     = self.root
        handled   = ()

        while child is not None and remaining:
            child, handled, remaining = child.findChild(request, remaining)

        if child is None:
            return False
        #
        # Allow resources to delegate to someone else,
        # even if they have been selected as the target of rendering
        #
        newChild = child.willHandle(request)
        if newChild is None:
            return False

        if newChild is not child:
            child = newChild

        request.segments = handled
        request.resource = child

        return True

    def handle_request(self, request):
        request.convert = convert
        resource = request.resource
        request.set_name(resource)
        resource.handle(request)

        request.resource = None
#
# Resource specific decorator(s).
#
def method_post(*args, **kwargs):
    def decorate(m):
        m.ultramini_method = ['post']
        m.ultramini_inheritable = kwargs.get('inherit')
        return m
    if args:
        return decorate(args[0])
    return decorate

def method_get(*args, **kwargs):
    def decorate(m):
        m.ultramini_method = ['get']
        m.ultramini_inheritable = kwargs.get('inherit')
        return m
    if args:
        return decorate(args[0])
    return decorate

def method(*args, **kwargs):
    def decorate(m):
        m.ultramini_method = ['get', 'post']
        m.ultramini_inheritable = kwargs.get('inherit')
        return m
    if args:
        return decorate(args[0])
    return decorate


class Resource(object):
    contentType = 'text/html'
    template = "Resources must provide a template attribute."
    _amf_class_mapper = None

    global_public_methods = {}

    def __init__(self, *args, **kwargs):
        self.__init_global__()

        self._public_methods = self.global_public_methods[hash(self.__class__)]
        return super(Resource, self).__init__(*args, **kwargs)

    def __init_global__(self):
        if self.global_public_methods.has_key(hash(self.__class__)):
            return None

        data = {}
        for name in dir(self):
            element = getattr(self, name)
            for label in getattr(element, 'ultramini_method', []):
                if self.__class__.__dict__.get(name):
                    data.setdefault(label, []).extend([name])
                elif getattr(element, 'ultramini_inheritable', False):
                    data.setdefault(label, []).extend([name])

        self.global_public_methods[hash(self.__class__)] = data

    def __call__(self, request, name):
        return self

    _child_re = re.compile(r'^child_')
    def _clear_child_(self):
        """_clear_child_ deletes this object's 'child_' attribute,
        then loops through all this object's attributes, and
        recursively calls the _clear_child method of any child_*
        attributes

        Arguments:
        self: mandatory python self arg
        """
        try:
            del self.child_
        except AttributeError, e:
            pass

        for attr in filter(self._child_re.match, dir(self)):
            try:
                getattr(self, attr)._clear_child_()
            except AttributeError:
                pass

    def willHandle(self, request):
        """This Resource is about to handle a request.
        If it wants to delegate to another Resource, it can return it here.
        """
        return self

    def findChild(self, request, segments):
        """External URL segment traversal API. This method MUST always
        return a tuple of:

            (child, handled, remaining)

        child may be None to indicate a 404. Handled should be a tuple
        of URL segments which were handled by this call to findChild;
        remaining should be a tuple of URL segments which were not
        handled by this call to findChild.

        findChild can be overriden to implement fancy URL traversal
        mechanisms such as handling multiple segments in one call,
        doing an internal server-side redirect to another resource and
        passing it segments to handle, or delegating this segment
        to another resource entirely. However, for most common use
        cases, you will not override findChild.

        Any methods or attributes named child_* will be mapped to
        URL segments. For example, if an instance of Root is set
        as the root object, the urls "/foo" and "/bar" will be valid:

        class Root(Resource):
            child_foo = Resource()

            def child_bar(self, request, bar):
                return Resource()

        Finally, if a childFactory method is defined it will be called
        with a single URL segment:

        class Root(Resource):
            def childFactory(self, request, childName):
                ## For URL "/foo" childName will be "foo"
                return Resource()
        """
        current, remaining = segments[0], segments[1:]

        childFactory = getattr(
            self,
            'child_%s' % (current, ),
            self.childFactory)

        return childFactory(request, current), (current, ), remaining

    def childFactory(self, request, childName):
        """Override this to produce instances of Resource to represent the next
        url segment below self. The next segment is provided in childName.
        """
        return None

    def handle(self, request):
        request.set_header('Content-Type', self.contentType)
        handler = getattr(
            self, "handle_%s" % (request.method(), ), self.handle_default)
        handler(request)

    def handle_default(self, request):
        request.push(
            "<html><body>No handler for method %r present.</body></html>" %
            (request.method(), ))

    def handle_get(self, request):
        get_method = self.getAction('get', request)

        if get_method is None:
            request.write(self.template)
        else:
            converted, result = applyWithTypeConversion(get_method, request,
                resource=self)
            request.write(result)

    ################
    ## AMF Specific
    ################

    @classmethod
    def mapped_classes(cls):
        return [
            amf.AMFRequest,
        ]

    def amf_class_mapper(self):
        '''
            Return an amfast ClassDefMapper object to properly deserialize objects
            in this request.

            Note: this function may be called multiple times
        '''
        if not self._amf_class_mapper:
            self._amf_class_mapper = amfast.class_def.ClassDefMapper()
            # Standard required mappings
            amf.registerClassToMapper(amf.AMFRequest, self._amf_class_mapper)
            amf.registerClassToMapper(amf.AMFResponse, self._amf_class_mapper)
            amf.registerClassToMapper(amf.GenericAMFException, self._amf_class_mapper)
            amf.registerClassToMapper(amf.AMFError, self._amf_class_mapper)

            # Map classes for subclasses
            for cls in self.mapped_classes():
                amf.registerClassToMapper(cls, self._amf_class_mapper)
        return self._amf_class_mapper

    ################
    ## END AMF Specific
    ################

    def getFieldStorage(self, data, headers, environ):
        '''getFieldStorage

        Result is an instance of cgi.FieldStorage or subclass. This is
        provided as a hook for subclasses to override if they want to
        parse the incoming POST data differently than a basic FieldStorage.
        For example, imgsrv/server overrides this to trick FieldStorage
        into saving binary parts directly into the image file directory,
        to avoid having to copy the file from a temporary file into the
        final location.

        data    - readable file-stream
        headers - request header dicttionary
        environ - request environment dictionary
        '''
        if headers.getheader('Content-Type') == 'application/x-amf' \
                and amf and amfast:
            return AMFFieldStorage(data, headers, environ=environ,
                class_mapper=self.amf_class_mapper())
        return cgi.FieldStorage(
            data,
            headers,
            environ = environ,
            keep_blank_values = 1)

    def getAction(self, key, request):
        fs = request.get_field_storage()
        actions = []
        methods = getattr(self, '_public_methods', {})

        for name in methods.get(key, []):
            parts = name.split('_')
            data = '_'.join(parts[1:])

            for value in fs.getlist(parts[0]):
                if value != data:
                    continue

                method = getattr(self, name, None)
                if method is None:
                    continue

                actions.append(method)

        if not actions:
            return getattr(
                self,
                '%s_%s' % (key, fs.getfirst(key, 'default')),
                None)

        method = actions.pop()
        if actions:
            raise RuntimeError('multiple methods requested', method, actions)

        return method

    def handle_post(self, request):
        fs = request.get_field_storage()
        post_method = self.getAction('post', request)

        if post_method is None:
            result = self.post(request, fs)
            converted = False
        else:
            converted, result = applyWithTypeConversion(post_method, request,
                resource=self)

        if not result:
            request.write(self.template)
            return None

        if converted:
            request.write(result)
            return None

        request.set_header('Location', request.convert(request, result))
        request.response(303)
        request.write('')


    def post(self, request, form):
        """post

        Override this to handle a form post.
        Return a URL to be redirected to.

        request: An HttpRequest instance representing the place the form
                  was posted to.
        form: A cgi.FieldStorage instance representing the posted form.
        """
        return request.uri()


class MovedPermanently(Resource):
    def __init__(self, location):
        self.location = location

    @annotate(req=REQUEST)
    def get_default(self, req):
        req.set_header(
            'Location',
            self.location)
        req.response(301) # Moved Permanently
        return self.location


class MovedTemporarily(Resource):
    def __init__(self, location):
        self.location = location

    @annotate(req=REQUEST)
    def get_default(self, req):
        req.set_header(
            'Location',
            self.location)
        req.response(302) # Moved Temporarily
        return self.location


class SeeOther(Resource):
    def __init__(self, location):
        self.location = location

    @annotate(req=REQUEST)
    def get_default(self, req):
        req.set_header(
            'Location',
            self.location)
        req.response(303) # See Other
        return self.location


class DebugLoggingResource(Resource):
    def enable_debug_logging(self, req, **kwargs):
        if kwargs.has_key('loglevel'):
            req.log_level(kwargs['loglevel'])

        if kwargs.get('httpread', False):
            req.connection().set_debug_read()
            req.connection().add_debug_read_data(req.requestline)
            req.connection().add_debug_read_data('')

            for header in req.get_headers().items():
                req.connection().add_debug_read_data('%s: %s' % header)

        return None

    def findChild(self, req, segments):
        debug = {}

        for value in req.get_query('ultradebug'):
            try:
                val = value.split('_')
                key = '_'.join(val[:-1])
                val = val[-1]

                key, val = key and (key, val) or (val, True)

                try:
                    debug[key] = int(val)
                except (TypeError, ValueError):
                    debug[key] = val
            except:
                print 'Cannot parse debug identifier <%s>' % value

        self.enable_debug_logging(req, **debug)
        return super(DebugLoggingResource, self).findChild(req, segments)

########NEW FILE########
__FILENAME__ = wsgi
'''
untested, exploratory module serving a WSGI app on the corohttpd framework
'''

import coro
import corohttpd
import logging
import sys


class _WSGIInput(object):
    def __init__(self, request):
        self._request = request
        self._length = int(request.get_header('Content-Length', '0'))

    def read(self, size=-1):
        conn = self._request._connection
        gathered = len(conn.buffer)

        # reading Content-Length bytes should behave like EOF
        if size >= 0:
            size = min(size, self._length)

        if not size:
            return ''

        while 1:
            data = conn.connection.recv(corohttpd.READ_CHUNK_SIZE)
            gathered += len(data)
            conn.buffer += data
            if not data:
                data, conn.buffer = conn.buffer, ''
                self._length -= len(data)
                return data
            if size >= 0 and gathered >= size:
                break

        data, conn.buffer = conn.buffer[:size], conn.buffer[size:]
        self._length -= len(data)
        return data

    def readline(self):
        conn = self._request._connection
        while 1:
            index = conn.buffer.find("\r\n")
            if index >= 0 or len(conn.buffer) >= self._length:
                if index < 0:
                    index = len(conn.buffer)
                result, conn.buffer = conn.buffer[:index], conn.buffer[index:]
                result = result[:self._length]
                self._length -= len(result)
                return result

            data = conn.connection.recv(corohttpd.READ_CHUNK_SIZE)
            if not data:
                break
            conn.buffer += data

        result, conn.buffer = conn.buffer, ''
        self._length -= len(result)
        return result

    def readlines(self, hint=None):
        return list(self._readlines())

    def _readlines(self):
        line = self.readline()
        while line:
            yield line
            line = self.readline()


class _WSGIErrors(object):
    def __init__(self, logger):
        self._log = logger

    def flush(self):
        pass

    def write(self, msg):
        self._log.log(logging.ERROR, msg)

    def writelines(self, lines):
        map(self.write, lines)


class WSGIAppHandler(object):
    def __init__(self, app):
        self.app = app

    def match(self, request):
        return True

    def handle_request(self, request):
        address = request.server().socket.getsockname()
        if request._connection._log:
            errors = _WSGIErrors(request._connection._log)
        else:
            errors = sys.stderr

        environ = {
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'http',
            'wsgi.input': _WSGIInput(request),
            'wsgi.errors': errors,
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
            'SCRIPT_NAME': '',
            'PATH_INFO': request._path,
            'SERVER_NAME': address[0],
            'SERVER_PORT': address[1],
            'REQUEST_METHOD': request.method().upper(),
            'SERVER_PROTOCOL': request._connection.protocol_version,
        }

        if request._query:
            environ['QUERY_STRING'] = request._query

        clheader = request.get_header('Content-Length')
        if clheader:
            environ['CONTENT_LENGTH'] = clheader

        ctheader = request.get_header('Content-Type')
        if ctheader:
            environ['CONTENT_TYPE'] = ctheader

        for name, value in request.get_headers().items():
            environ['HTTP_%s' % name.replace('-', '_').upper()] = value

        headers_sent = [False]

        def start_response(status, headers, exc_info=None):
            if exc_info and collector[1]:
                raise exc_info[0], exc_info[1], exc_info[2]
            else:
                exc_info = None

            # this is goofy -- get the largest status prefix that is an integer
            for index, character in enumerate(status):
                if index and not status[:index].isdigit():
                    break

            code = int(status[:index - 1])
            request.response(code)

            for name, value in headers:
                request.set_header(name, value)

            headers_sent[0] = True

            return request.push

        body_iterable = self.app(environ, start_response)
        for chunk in body_iterable:
            request.push(chunk)


def serve(address, wsgiapp, access_log='', error_log=None):
    kwargs = {}
    if error_log:
        handler = logging.handlers.RotatingFileHandler(
                filename or 'log',
                'a',
                corohttpd.ACCESS_LOG_SIZE_MAX,
                corohttpd.ACCESS_LOG_COUNT_MAX)
        handler.setFormatter(logging.Formatter('%(message)s'))
        kwargs['log'] = logging.Logger('error')
        kwargs['log'].addHandler(handler)

    server = corohttpd.HttpServer(args=(address, access_log), **kwargs)
    server.push_handler(WSGIAppHandler(wsgiapp))
    server.start()
    coro.event_loop()


def main():
    def hello_wsgi_world(environ, start_response):
        start_response('200 OK', [
            ('Content-Type', 'text/plain'),
            ('Content-Length', '13')])
        return ["Hello, World!"]

    serve(("", 8000), hello_wsgi_world, access_log='access.log')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = pavement
import errno
import os
from setuptools import Extension

from paver.easy import *
from paver.path import path
from paver.setuputils import setup


setup(
    name="gogreen",
    description="Coroutine utilities for non-blocking I/O with greenlet",
    version="1.0.1",
    license="bsd",
    author="Libor Michalek",
    author_email="libor@pobox.com",
    packages=["gogreen"],
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Topic :: System :: Networking",
    ]
)

MANIFEST = (
    "LICENSE",
    "setup.py",
    "paver-minilib.zip",
)

@task
def manifest():
    path('MANIFEST.in').write_lines('include %s' % x for x in MANIFEST)

@task
@needs('generate_setup', 'minilib', 'manifest', 'setuptools.command.sdist')
def sdist():
    pass

@task
def clean():
    for p in map(path, ('gogreen.egg-info', 'dist', 'build', 'MANIFEST.in')):
        if p.exists():
            if p.isdir():
                p.rmtree()
            else:
                p.remove()
    for p in path(__file__).abspath().parent.walkfiles():
        if p.endswith(".pyc") or p.endswith(".pyo"):
            try:
                p.remove()
            except OSError, exc:
                if exc.args[0] == errno.EACCES:
                    continue
                raise

########NEW FILE########
__FILENAME__ = test_ultramini
"""test_ultramini

Tests for the ultramini web framework.
"""

import cgi
import cStringIO
import logging
import sys
import types
import unittest
import warnings

from gogreen import coro
from gogreen import ultramini
from gogreen import corohttpd



warnings.filterwarnings(
	'ignore', category=ultramini.LocationDeprecationWarning)


########################################################################
## Testcase helpers
########################################################################


class CoroTestCase(unittest.TestCase):
	def setUp(self):
		super(CoroTestCase, self).setUp()
		coro.socket_emulate()
	
	def tearDown(self):
		super(CoroTestCase, self).tearDown()
		coro.socket_reverse()


DEFAULT = object()
FAILURE = Exception("Test failed.")
PASSED = object()

class FakeServer(object):
	def __init__(self, condition):
		self.access = self
		self.condition = condition

	def request_started(self, req, cur=None):
		pass

	def info(self, bytes):
		coro.current_thread().info(bytes)

	def request_ended(self, req, code, start_time, push_time, rsize, wsize):
		self.condition.wake_all()

	def record_counts(self, *args):
		pass


class FakeSocket(object):
	def __init__(self, bytes):
		self.bytes = bytes
		self.pushed = ''

	def recv(self, num):
		if num > len(self.bytes):
			num = len(self.bytes)
		torecv = self.bytes[:num]
		self.bytes = self.bytes[num:]
		if not torecv:
			raise corohttpd.ConnectionClosed()
		return torecv

	read = recv

	def send(self, bytes):
		self.pushed += bytes
		return len(bytes)

	def close(self):
		pass

	def getsockname(self):
		return "<fake>"
	
	def shutdown(self, *args, **kwargs):
		pass


def sendreq(site, bytes):
	result = []
	def actually_send():
		socket = FakeSocket(bytes)
		waiter = coro.coroutine_cond()
		server = FakeServer(waiter)
		log = coro.coroutine_logger('tests')
		output = cStringIO.StringIO()
		log.addHandler(logging.StreamHandler(output))
		http = corohttpd.HttpProtocol(
			args=(socket, ('<fake>', 0), server, [site]), log=log)
		http.start()
		waiter.wait(0.01)
		if socket.pushed.startswith('HTTP/1.1 500'):
			output.seek(0)
			print output.read()
		result.append(socket.pushed)

	coro.spawn(actually_send)
	coro.event_loop()
	rv = result[0].split('\r\n\r\n', 1)
	if len(rv) != 2:
		rv = ('', '')
	return rv


class FakeRequest(corohttpd.HttpRequest):
	def __init__(self, query, site, method,  uri, headers, path, body, resource):
		self.site = site

		# These should be private but they aren't
		self._query = query
		self._path = path

		# These are private
		self._headers_ = headers
		self._method_ = method
		self._body_ = body
		self._uri_ = uri

		self.pushed = ''
		self._response_ = 200

		self._outgoing_headers_ = {}

		if resource is None:
			resource = ultramini.Resource()
		self.resource = resource

		self.convert = ultramini.convert

	def method(self):
		return self._method_

	def uri(self):
		return self._uri_

	def get_headers(self):
		return self._headers_

	def get_header(self, name, default=None):
		return self._headers_.get(name, default)

	def push(self, stuff):
		self.pushed += stuff

	def set_header(self, key, value):
		self._outgoing_headers_[key] = value

	def connection(self):
		return FakeSocket(self._body_)

	def response(self, code):
		self._response_ = code

	def result(self):
		return self._response_, self.pushed, self._outgoing_headers_

	def get_field_storage(self):
		if self._method_ == 'get':
			environ = dict(
				QUERY_STRING=self._query,
				REQUEST_METHOD='get')
			fp = None
		else:
			environ = dict(
				CONTENT_TYPE='application/x-www-form-urlencoded',
				REQUEST_METHOD='post')
			fp = cStringIO.StringIO(self._body_)
		
		fs = cgi.FieldStorage(
			fp, self.get_headers(),
			environ=environ)
		return fs

	def write(self, stuff):
		self.push(ultramini.convert(self, stuff))


def loc(
	query='', site=None, method='get', resource=None, 
	uri='http://fakeuri', body='', path='/',
	headers=None):
	if headers is None:
		headers = {
			'content-type': 'application/x-www-form-urlencoded'}
	if method == 'post':
		headers['content-length'] = str(len(body))
	return FakeRequest(
		query, site, method, uri, headers, path, body, resource)


def write(stuff, resource=None):
	l = loc(resource=resource)
	l.write(stuff)
	return l.pushed




########################################################################
## post_* and get_* argument converter tests
########################################################################

class TestThing(CoroTestCase):
	def runTest(self):
		mything = ultramini.Thing('')
		otherthing = mything.foo
		assert otherthing.name == 'foo'
		thirdthing = mything('bar', 'baz')
		assert thirdthing.name == 'bar'
		assert thirdthing.default == 'baz'

class TestLocation(CoroTestCase):
	def runTest(self):
		l = loc()

		@ultramini.arguments(ultramini.LOCATION)
		def some_function(foo):
			assert foo == l

		ultramini.convertFunction(l, some_function)

class TestRequest(CoroTestCase):
	def runTest(self):
		req = loc()

		@ultramini.arguments(ultramini.REQUEST)
		def some_function(foo):
			assert foo == req

		ultramini.convertFunction(req, some_function)


class TestSite(CoroTestCase):
	def runTest(self):
		@ultramini.arguments(ultramini.SITE)
		def some_function(foo):
			assert foo == PASSED

		ultramini.convertFunction(
			loc(site=PASSED), some_function)

class TestResource(CoroTestCase):
	def runTest(self):
		@ultramini.arguments(ultramini.RESOURCE)
		def some_function(foo):
			assert foo == PASSED

		ultramini.convertFunction(
			loc(resource=PASSED), some_function)

class TestMethod(CoroTestCase):
	def runTest(self):
		@ultramini.arguments(ultramini.METHOD)
		def some_function(foo):
			assert foo == "GLORP"

		ultramini.convertFunction(
			loc(method="GLORP"), some_function)

class TestURL(CoroTestCase):
	def runTest(self):
		@ultramini.arguments(ultramini.URI)
		def some_function(foo):
			assert foo == "/foo.gif"

		ultramini.convertFunction(
			loc(uri="/foo.gif"), some_function)

class TestQuery(CoroTestCase):
	def runTest(self):
		l = loc("foo=bar")
		@ultramini.arguments(ultramini.QUERY.foo)
		def some_function(foo):
			assert foo == 'bar'

		ultramini.convertFunction(l, some_function)

class TestMissingQuery(CoroTestCase):
	def runTest(self):
		l = loc("foo=bar")

		@ultramini.arguments(ultramini.QUERY('bar', DEFAULT))
		def another(bar):
			assert bar == DEFAULT

		ultramini.convertFunction(l, another)
			  
class TestQueries(CoroTestCase):
	def runTest(self):
		l = loc("foo=bar&foo=baz")

		@ultramini.arguments(ultramini.QUERIES.foo)
		def some_function(foo):
			foo = tuple(foo)
			assert foo == ('bar', 'baz')

		ultramini.convertFunction(l, some_function)

class TestMissingQueries(CoroTestCase):
	def runTest(self):
		l = loc("foo=bar&foo=baz")

		@ultramini.arguments(ultramini.QUERIES('bar', DEFAULT))
		def another(foo):
			assert foo == DEFAULT

		ultramini.convertFunction(l, another)

class TestArg(CoroTestCase):
	def runTest(self):
		l = loc(body='foo=bar', method='post')

		@ultramini.arguments(ultramini.ARG.foo)
		def some_function(foo):
			assert foo == 'bar'

		ultramini.convertFunction(l, some_function)

class TestMissingArg(CoroTestCase):
	def runTest(self):
		l = loc(body='foo=bar', method='post')

		@ultramini.arguments(ultramini.ARG('bar', DEFAULT))
		def another(foo):
			assert foo == DEFAULT

		ultramini.convertFunction(l, another)


class TestArgs(CoroTestCase):
	def runTest(self):
		l = loc(body='foo=bar&foo=baz', method='post')

		@ultramini.arguments(ultramini.ARGS.foo)
		def some_function(foo):
			assert foo == ['bar', 'baz']

		ultramini.convertFunction(l, some_function)

class TestMissingArgs(CoroTestCase):
	def runTest(self):
		l = loc(body='foo=bar&foo=baz', method='post')

		@ultramini.arguments(ultramini.ARGS('bar', DEFAULT))
		def another(foo):
			assert foo == DEFAULT

		ultramini.convertFunction(l, another)

class TestCookie(CoroTestCase):
	def runTest(self):
		l = loc(headers=dict(Cookie="foo=bar"))

		@ultramini.arguments(ultramini.COOKIE.foo)
		def some_function(foo):
			assert foo == "bar"

		ultramini.convertFunction(l, some_function)

class TestMissingCookie(CoroTestCase):
	def runTest(self):
		l = loc(headers=dict(Cookie="foo=bar"))

		@ultramini.arguments(ultramini.COOKIE('bar', DEFAULT))
		def another(foo):
			assert foo == DEFAULT

		ultramini.convertFunction(l, another)


class TestNoCookies(CoroTestCase):
	def runTest(self):
		@ultramini.arguments(ultramini.COOKIE('missing', DEFAULT))
		def another(foo):
			assert foo == DEFAULT

		ultramini.convertFunction(loc(), another)

class TestHeader(CoroTestCase):
	def runTest(self):
		l = loc(headers=dict(foo='bar'))

		@ultramini.arguments(ultramini.HEADER.foo)
		def some_function(foo):
			assert foo == 'bar'

		ultramini.convertFunction(l, some_function)

class TestQuotedQuery(CoroTestCase):
	def runTest(self):
		l = loc(query="channel=462280&amp;ver=3&amp;p=run")

		@ultramini.arguments(ultramini.QUERY.channel)
		def some_function(channel):
			assert channel == "462280"

		ultramini.convertFunction(l, some_function)

class TestLiteralArgument(CoroTestCase):
	def runTest(self):
		@ultramini.arguments(1234)
		def some_function(channel):
			assert channel == 1234

		ultramini.convertFunction(loc(), some_function)


########################################################################
## rendering converter tests: things which are contained within a
## resource's template attribute
########################################################################


class ConverterTests(CoroTestCase):
	def test_unicode(self):
		the_string = u'\u00bfHabla espa\u00f1ol?'
		assert  write(the_string) == the_string.encode('utf8')


	def test_list(self):
		assert write(['abc', 1, 2, 3]) == 'abc123'


	def test_tuple(self):
		assert write(('abc', 1, 2, 3)) == 'abc123'


	def test_generator(self):
		def the_generator():
			yield 'abc'
			yield 1
			yield 2
			yield 3

		assert write(the_generator) == 'abc123'


	def test_function(self):
		def the_function():
			return "abc123"

		assert write(the_function) == 'abc123'


	def test_method(self):
		class Foo(object):
			def __init__(self):
				self.bar = 'abc123'

			def baz(self):
				return self.bar

		f = Foo()
		assert write(f.baz) == f.bar


	def test_unbound_method(self):
		class Foo(object):
			@ultramini.arguments(ultramini.RESOURCE)
			def method(self):
				return 'asdf'

		assert write(Foo.method, Foo()) == 'asdf'


	def test_int(self):
		the_number = 12345
		assert write(the_number) == str(the_number)


	def test_float(self):
		the_number = 3.1415
		assert write(the_number) == str(the_number)


	def test_long(self):
		the_number = 100000L * 100000L
		assert write(the_number) == str(the_number)


	def test_show(self):
		class Foo(object):
			def show_bar(self):
				return 'hello'

		assert write(ultramini.show.bar, Foo()) == 'hello'


	def test_show_arguments(self):
		class Foo(object):
			def show_bar(self, foo):
				return foo

		assert write(ultramini.show.bar('foo'), Foo()) == 'foo'


	def test_iter_show(self):
		assert list(iter(ultramini.show.bar)) == []

	def test_string_quoting(self):
		assert write("<&>") == "&lt;&amp;&gt;"

	def test_pattern_omitted(self):
		assert write(
			ultramini.img[ultramini.span(pattern='foo')]) == '<img></img>'


	def test_stan_show_special(self):
		class Foo(object):
			template = ultramini.img[ultramini.span(show=ultramini.show.bar)]

			def show_bar(self):
				return "baz"

		written = write(Foo.template, Foo())
		assert written == '<img>baz</img>'


	def test_mutate_stan(self):
		foo = ultramini.img()
		foo(src='bar')

		assert write(foo) == '<img src="bar"></img>'

	def test_register_converter(self):
		class Blarg(object):
			pass

		def convert_blarg(request, blarg):
			return 'blarg.'

		ultramini.registerConverter(Blarg, convert_blarg)

		written = write(Blarg())
		assert written == 'blarg.'


	def test_no_converter(self):
		class Wrong(object):
			pass

		self.failUnlessRaises(RuntimeError, write, Wrong())


########################################################################
## Cast converter tests
########################################################################

class TypeConversionTests(CoroTestCase):
	def test_quoted_query_converter(self):
		l = loc(query="channel=462280&amp;ver=3&amp;p=run")

		@ultramini.annotate(channel=int)
		def some_function(channel):
			assert channel == 462280

		ultramini.applyWithTypeConversion(some_function, l)


	def test_int_converter(self):
		l = loc(query="channel=462280")

		@ultramini.annotate(channel=int)
		def some_function(channel):
			assert channel == 462280

		ultramini.applyWithTypeConversion(some_function, l)


	def test_failing_int_converter(self):
		l = loc(query="channel=asdf")

		@ultramini.annotate(channel=int)
		def somefunc(channel):
			raise FAILURE

		self.failUnlessRaises(
			TypeError, ultramini.applyWithTypeConversion, somefunc, l)


	def test_float_converter(self):
		l = loc(query="pi=3.14")

		@ultramini.annotate(pi=float)
		def somefunc(pi):
			assert pi == 3.14
			
		ultramini.applyWithTypeConversion(somefunc, l)


	def test_failing_float_converter(self):
		l = loc(query='pi=asdf')

		@ultramini.annotate(pi=float)
		def somefunc(pi):
			raise FAILURE

		self.failUnlessRaises(
			TypeError, ultramini.applyWithTypeConversion, somefunc, l)


	def test_list_converter(self):
		l = loc(query="foo=bar&foo=baz")

		@ultramini.annotate(foo=[str])
		def somefunc(foo):
			assert foo == ['bar', 'baz']

		ultramini.applyWithTypeConversion(somefunc, l)


	def test_list_single(self):
		l = loc(query="foo=bar")

		@ultramini.annotate(foo=[str])
		def somefunc(foo):
			assert foo == ['bar']

		ultramini.applyWithTypeConversion(somefunc, l)


	def test_list_fail(self):
		l = loc(query="foo=bar")

		@ultramini.annotate(foo=[int])
		def somefunc(foo):
			raise FAILURE

		self.failUnlessRaises(
			TypeError, ultramini.applyWithTypeConversion, somefunc, l)


	def test_tuple_converter(self):
		l = loc(query="foo=1&foo=hello&foo=3.1415")

		@ultramini.annotate(foo=(int, str, float))
		def somefunc(foo):
			(fi, fs, ff) = foo
			assert fi == 1
			assert fs == 'hello'
			assert ff == 3.1415

		ultramini.applyWithTypeConversion(somefunc, l)


	def test_dict_converter(self):
		l = loc(query="foo.bar=1&foo.baz=asdf")

		@ultramini.annotate(foo=dict(bar=int, baz=str))
		def somefunc(foo):
			assert isinstance(foo, dict)
			assert foo['bar'] == 1
			assert foo['baz'] == 'asdf'

		ultramini.applyWithTypeConversion(somefunc, l)


	def test_str_converter(self):
		l = loc(query='foo=foo')

		@ultramini.annotate(foo=str)
		def somefunc(foo):
			assert foo == 'foo'

		ultramini.applyWithTypeConversion(somefunc, l)


	def test_unicode_converter(self):
		l = loc(query=u'foo=\u00bfHabla%20espa\u00f1ol?'.encode('utf8'))

		@ultramini.annotate(foo=unicode)
		def somefunc(foo):
			assert foo == u'\u00bfHabla espa\u00f1ol?'

		ultramini.applyWithTypeConversion(somefunc, l)


	def test_function_converter(self):
		l = loc(query='foo=something')

		def converter_function(request, value):
			return "else"

		@ultramini.annotate(foo=converter_function)
		def somefunc(foo):
			assert foo == 'else'

		ultramini.applyWithTypeConversion(somefunc, l)


	def test_annotate_return_converter(self):
		def converter_function(something):
			assert something == 'wrong'
			return "right"

		@ultramini.annotate(converter_function)
		def somefunc():
			return 'wrong'

		success, result = ultramini.applyWithTypeConversion(somefunc, loc())
		# applyWithTypeConversion should return (hasConverted, result)
		# so we want (True, 'right')
		assert success, ('Failed to properly convert')
		assert result == 'right', (result, 'Incorrect return')


	def test_no__incoming_converter(self):
		class Wrong(object):
			pass

		@ultramini.annotate(foo=Wrong)
		def somefunc(foo):
			raise FAILED

		self.failUnlessRaises(
			TypeError, ultramini.applyWithTypeConversion, somefunc, loc(
				query='foo=bar'))

	def test_input_and_output_converter(self):
		def caps_in(resource, request, parameters):
			for k, v in parameters.iteritems():
				parameters[k] = unicode(v).upper()
			return parameters

		def lower_out(result):
			return unicode(result).lower()

		@ultramini.annotate(lower_out, caps_in, foo=str)
		def somefunc(foo):
			if not foo == 'WORLD':
				return 'World was supposed to be caps :('
			return 'HeLLo %s' % foo

		l = loc(query='foo=world')
		success, result = ultramini.applyWithTypeConversion(somefunc, l)
		assert success
		assert result == 'hello world', (success, result)

	def test_chained_input_converters(self):
		def intify(resource, request, params):
			for k in params.iterkeys():
				params[k] = int(params[k])
			return params

		def subtract_five(resource, request, params):
			for k in params.iterkeys():
				params[k] = params[k] - 5
			return params

		@ultramini.annotate(unicode, (intify, subtract_five), foo=int)
		def somefunc(foo):
			return foo

		l = loc(query='foo=10')
		success, result = ultramini.applyWithTypeConversion(somefunc, l)
		assert success
		assert result == u'5', (success, result)

	def test_custom_converter(self):
		old = ultramini.converters[str]
		try:
			ultramini.registerConverter(str, lambda r, s: ultramini.xml(s))
			@ultramini.annotate(str)
			def handler():
				return '<strong/>'

			l = loc()
			success, result = ultramini.applyWithTypeConversion(handler, l)
			result = ultramini.convert(l, result)
			assert success
			assert result == '<strong/>', (success, result)
		finally:
			ultramini.registerConverter(str, old)



########################################################################
## Test url traversal
########################################################################


class URLTraversalTests(CoroTestCase):
	def find_resource(self, path, root):
		req = loc(path=path)
		ultramini.SiteMap(root).match(req)
		return req.resource


	def test_root(self):
		root = ultramini.Resource()
		result = self.find_resource('/', root)
		assert result == root


	def test_child(self):
		root = ultramini.Resource()
		child = root.child_foo = ultramini.Resource()
		result = self.find_resource('/foo', root)
		assert result == child


	def test_findChild(self):
		child = ultramini.Resource()
		class Foo(ultramini.Resource):
			def findChild(self, req, segments):
				return child, segments, ()

		root = Foo()

		assert self.find_resource('/foobar', root) == child
		assert self.find_resource('/', root) == child
		assert self.find_resource('/asdfasdf/asdfasdf/asdfasdf', root) == child


	def test_childFactory(self):
		class Child(ultramini.Resource):
			def __init__(self, name):
				self.name = name

		class Root(ultramini.Resource):
			def childFactory(self, req, name):
				return Child(name)

		root = Root()

		assert self.find_resource('/foo', root).name == 'foo'
		assert self.find_resource('/bar', root).name == 'bar'
		assert self.find_resource('/baz', root).name == 'baz'


	def test_willHandle(self):
		child = ultramini.Resource()

		class Root(ultramini.Resource):
			def willHandle(self, req):
				return child

			def childFactory(self, req, segments):
				return self, segments, ()

		assert self.find_resource('/', Root()) == child


########################################################################
## Test handling
########################################################################


class HandlingTests(CoroTestCase):
	def handle_resource(self, req, root):
		ultramini.SiteMap(root).match(req)
		req.resource.handle(req)
		return req.result()


	def test_handle_get(self):
		simple = ultramini.Resource()
		simple.template = 'hello'

		code, result, headers = self.handle_resource(loc(), simple)
		assert code == 200
		assert result == 'hello'


	def test_handle_post(self):
		simple = ultramini.Resource()
		simple.template = 'hello'

		## Assert that we redirect
		code, result, headers = self.handle_resource(
			loc(method='post', headers={'content-length': '0'}), simple)
		assert code == 303, (code, headers, result)
		assert result == ''
		assert headers['Location'] == loc().uri()


	def test_handle_get_method(self):
		class Simple(ultramini.Resource):
			def get_default(self):
				return 'hello'

		code, result, headers = self.handle_resource(loc(), Simple())
		assert code == 200
		assert result == 'hello'


	def test_handle_get_custom(self):
		class Simple(ultramini.Resource):
			def get_default(self):
				return 'fail'

			def get_foo(self):
				return 'pass'

		code, result, headers = self.handle_resource(loc(query='get=foo'), Simple())
		assert code == 200
		assert result == 'pass'


	def test_handle_post_method(self):
		class Simple(ultramini.Resource):
			def post_default(self):
				return '/foo'

		code, result, headers = self.handle_resource(
			loc(method='post'), Simple())
		assert code == 303
		assert result == ''
		assert headers['Location'] == '/foo'


	def test_handle_post_custom(self):
		class Simple(ultramini.Resource):
			def post_default(self):
				return '/wrong'

			def post_foo(self):
				return '/foo'

		code, result, headers = self.handle_resource(
			loc(method='post', body='post=foo'), Simple())
		assert code == 303
		assert result == ''
		assert headers['Location'] == '/foo'


	def test_missing_methods(self):
		expected = (
			"<html><body>No handler for method 'GURFLE' present.</body></html>")

		code, result, headers = self.handle_resource(
			loc(method='GURFLE'), ultramini.Resource())

		assert code == 200
		assert result == expected


########################################################################
## Test that we interact with corohttpd properly
########################################################################


GET_TEMPLATE = """GET %s HTTP/1.1\r
Host: localhost\r
\r
"""


POST_TEMPLATE = """POST %s HTTP/1.1\r
Host: localhost\r
Content-length: %s\r
\r
%s"""


class CorohttpdTests(CoroTestCase):
	system = True # Marking these system-tests since they mostly suck
	def test_simple_http(self):
		root = ultramini.Resource()
		root.template = 'hello'
		site = ultramini.SiteMap(root)
		headers, result = sendreq(site, GET_TEMPLATE % ('/', ))

		assert result == 'hello', (site, result, headers)


	def test_simple_not_found(self):
		root = ultramini.Resource()
		site = ultramini.SiteMap(root)
		headers, result = sendreq(
			site, GET_TEMPLATE % ('/asdfkjasdfhakshdfkhaqe/asdfhas/a.dhf', ))
		assert headers.startswith("HTTP/1.1 404"), ('Fail', headers, result)


	def test_query_parameter(self):
		class Simple(ultramini.Resource):
			@ultramini.annotate(foo=str)
			def get_default(self, foo):
				assert foo == 'bar'

		root = Simple()
		headers, result = sendreq(
			ultramini.SiteMap(root), GET_TEMPLATE % ('/?foo=bar', ))

		assert headers.startswith("HTTP/1.1 200")

		
	def test_header(self):
		class Simple(ultramini.Resource):
			@ultramini.arguments(ultramini.HEADER.host)
			def host(self, foo):
				assert foo == 'localhost'
				return "ok"

			template = host

		headers, result = sendreq(
			ultramini.SiteMap(Simple()), GET_TEMPLATE % ('/', ))

		assert result == 'ok'


	def test_continuation_header(self):
		class Simple(ultramini.Resource):
			@ultramini.arguments(ultramini.HEADER.continuation)
			def continuation(self, foo):
				assert foo == "foo bar baz\n foo bar baz"
				return "ok"

			template = continuation

		headers, result = sendreq(
			ultramini.SiteMap(Simple()), """GET / HTTP/1.1\r
Host: localhost\r
Continuation: foo bar baz\r
 foo bar baz\r
Another-Header: 1234-asdf\r
\r
	""")
		self.assertEqual(result, 'ok')


	def test_outgoing_header(self):
		class Simple(ultramini.Resource):
			@ultramini.annotate(req=ultramini.REQUEST)
			def get_default(self, req):
				req.set_header('Some-header', 'Some-value')
				assert req.has_key('Some-header')
				assert req.get_outgoing_header('Some-header') == ['Some-value']
				return "ok"

		headers, result = sendreq(
			ultramini.SiteMap(Simple()), GET_TEMPLATE % ('/', ))

		self.assertEqual(result, 'ok')
		assert 'Some-header: Some-value'.lower() in headers.lower()


	def test_post_request(self):
		class Simple(ultramini.Resource):
			def post(self, req, form):
				return '/'

		headers, result = sendreq(
			ultramini.SiteMap(Simple()), POST_TEMPLATE % ('/', 0, ''))

		assert headers.startswith('HTTP/1.1 303')


	def test_cached_resource(self):
		class Simple(ultramini.Resource):
			template = 0
			def willHandle(self, request):
				self.template = self.template + 1
				return self

		sitemap = ultramini.SiteMap(Simple())

		headers, result = sendreq(sitemap, GET_TEMPLATE % ('/', ))
		assert result == '1', ('Fail', result)

		headers, result = sendreq(sitemap, GET_TEMPLATE % ('/', ))
		assert result == '2', ('Fail', result)


	def test_uncached_resource(self):
		class Simple(ultramini.Resource):
			cache = False
			template = 0
			def willHandle(self, request):
				self.template = self.template + 1
				return self

		sitemap = ultramini.SiteMap(Simple())

		headers, result = sendreq(sitemap, GET_TEMPLATE % ('/', ))
		assert result == '1', (result, headers)

		headers, result = sendreq(sitemap, GET_TEMPLATE % ('/', ))
		assert result == '2', (result, headers)


## TODO Write cache tests
	
if __name__ == '__main__':
	unittest.main()

########NEW FILE########
