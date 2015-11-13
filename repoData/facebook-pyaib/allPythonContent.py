__FILENAME__ = botbot
#!/usr/bin/env python
#
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from pyaib.ircbot import IrcBot
import sys

argv = sys.argv[1:]

#Load 'botbot.conf' from the par
bot = IrcBot(argv[0] if argv else 'botbot.conf')

print("Config Dump: %s" % bot.config)

#Bot Take over
bot.run()

########NEW FILE########
__FILENAME__ = debug
""" Debug Plugin (botbot plugins.debug) """
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import time

from pyaib.plugins import observe, keyword, plugin_class, every


#Let pyaib know this is a plugin class and to
# Store the address of the class instance at
# 'debug' in the irc_context obj
@plugin_class('debug')
class Debug(object):

    #Get a copy of the irc_context, and a copy of your config
    # So for us it would be 'plugin.debug' in the bot config
    def __init__(self, irc_context, config):
        print("Debug Plugin Loaded!")

    @observe('IRC_RAW_MSG', 'IRC_RAW_SEND')
    def debug(self, irc_c, msg):
        print("[%s] %r" % (time.strftime('%H:%M:%S'), msg))

    @observe('IRC_MSG_PRIVMSG')
    def auto_reply(self, irc_c, msg):
        if msg.channel is None:
            msg.reply(msg.message)

    @keyword('die')
    def die(self, irc_c, msg, trigger, args, kargs):
        msg.reply('Ok :(')
        irc_c.client.die()

    @keyword('raw')
    def raw(self, irc_c, msg, trigger, args, kargs):
        irc_c.RAW(args)

    @keyword('test')
    def argtest(self, irc_c, msg, trigger, args, kargs):
        msg.reply('Trigger: %r' % trigger)
        msg.reply('ARGS: %r' % args)
        msg.reply('KEYWORDS: %r' % kargs)

    @keyword('join')
    def join(self, irc_c, msg, trigger, args, kargs):
        if len(args) > 0:
            irc_c.JOIN(args)

    @keyword('part')
    def part(self, irc_c, msg, trigger, args, kargs):
        if len(args) > 0:
            irc_c.PART(args, message='%s asked me to leave.' % msg.nick)

    @keyword('invite')
    def invite(self, irc_c, msg, trigger, args, kargs):
        if len(args) > 0 and args[0].startswith('#'):
            irc_c.RAW('INVITE %s :%s' % (msg.nick, args[0]))

    @observe('IRC_MSG_INVITE')
    def follow_invites(self, irc_c, msg):
        if msg.target == irc_c.botnick:  # Sanity
            irc_c.JOIN(msg.message)
            irc_c.PRIVMSG(msg.message, '%s: I have arrived' % msg.nick)

########NEW FILE########
__FILENAME__ = example
""" Example Plugin (dice roller) (botbot plugins.example) """
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import re

from pyaib.plugins import keyword
from random import SystemRandom


def statsCheck(stats):
    total = sum([(s - 10) / 2 for s in stats])
    avg = total / 6
    return  avg > 0 and max(stats) > 13


def statsGen():
    rand = SystemRandom()
    while True:
        stats = []
        for s in range(0, 6):  # Six Stats
            rolls = []
            for d in range(0, 4):  # Four Dice
                roll = rand.randint(1, 6)
                if roll == 1:  # Reroll 1's once
                    roll = rand.randint(1, 6)
                rolls.append(roll)
            rolls.sort()
            rolls.reverse()
            stats.append(rolls[0] + rolls[1] + rolls[2])
        if statsCheck(stats):
            return stats
    return None


@keyword('stats')
def stats(irc_c, msg, trigger, args, kargs):
    msg.reply("%s: Set 1: %r" % (msg.nick, statsGen()))
    msg.reply("%s: Set 2: %r" % (msg.nick, statsGen()))


rollRE = re.compile(r'((\d+)?d((?:\d+|%))([+-]\d+)?)', re.IGNORECASE)
modRE = re.compile(r'([+-]\d+)')

def roll(count, sides):
    results = []
    rand = SystemRandom()
    for x in range(count):
        if sides == 100 or sides == 1000:
            #Special Case for 100 sized dice
            results.append(rand.randint(1, 10))
            results.append(rand.randrange(0, 100, 10))
            if sides == 1000:
                results.append(rand.randrange(0, 1000, 100))
        else:
            results.append(rand.randint(1, sides))
    return results


@keyword('roll')
def diceroll(irc_c, msg, trigger, args, kargs):

    def help():
        txt = ("Dice expected in form [<count>]d<sides|'%'>[+-<modifer>] or "
               "+-<modifier> for d20 roll. No argument rolls d20.")
        msg.reply(txt)

    if 'help' in kargs or 'h' in kargs:
        help()
        return
    rolls = []
    if not args:
        rolls.append(['d20', 1, 20, 0])
    else:
        for dice in args:
            m = rollRE.match(dice) or modRE.match(dice)
            if m:
                group = m.groups()
                if len(group) == 1:
                    dice = ['d20%s' % group[0], 1, 20, int(group[0])]
                    rolls.append(dice)
                else:
                    dice = [group[0], int(group[1] or 1),
                            100 if group[2] == '%' else int(group[2]),
                            int(group[3] or 0)]
                    rolls.append(dice)
                    if dice[1] > 100 or (dice[2] > 100 and dice[2] != 1000):
                        msg.reply("%s: I don't play with crazy power gamers!"
                                  % msg.nick)
                        return
            else:
                help()
                return

    for dice in rolls:
        results = roll(dice[1], dice[2])
        total = sum(results) + int(dice[3])
        if len(results) > 10:
            srolls = '+'.join([str(x) for x in results[:10]])
            srolls += '...'
        else:
            srolls = '+'.join([str(x) for x in results])
        msg.reply("%s: (%s)[%s] = %d" % (
            msg.nick, dice[0], srolls, total))


print("Example Plugin Done")

########NEW FILE########
__FILENAME__ = jokes
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import random

from pyaib.plugins import keyword, plugin_class


@plugin_class
class Jokes(object):
    def __init__(self, irc_context, config):
        self.r = Roulette()
        self.ballresp = config.ballresp
        print("Jokes Plugin Loaded!")

    @keyword('roulette')
    @keyword.nosubs
    @keyword.autohelp_noargs
    def roulette_root(self, irc_c, msg, trigger, args, kargs):
        """[spin|reload|stats|clearstats] :: Play russian roulette.
 One round in a six chambered gun.
 Take turns to spin the cylinder until somebody dies."""
        pass

    @keyword('roulette')
    @keyword.sub('spin')
    @keyword.autohelp
    def roulette_spin(self, irc_c, msg, trigger, args, kargs):
        ''':: spins the cylinder'''
        if self.r.fire(msg.nick):
            msg.reply("BANG! %s %s" % (msg.nick, Roulette.unluckyMsg()))
        else:
            msg.reply("%s %s" % (msg.nick, Roulette.luckyMsg()))

    @keyword('roulette')
    @keyword.sub('reload')
    @keyword.autohelp
    def roulette_reload(self, irc_c, msg, trigger, args, kargs):
        ''':: force the gun to reload'''
        self.r.reload()

    @keyword('roulette')
    @keyword.sub('stats')
    @keyword.autohelp
    def roulette_stats(self, irc_c, msg, trigger, args, kargs):
        '''[player] :: show stats from all games'''
        if len(args) == 0:
            stats = self.r.getGlobalStats()
            msg.reply("In all games there were %d misses and %d kills"
                      % (stats['misses'], stats['hits']))
        else:
            stats = self.r.getStats(args[0])
            if stats:
                msg.reply("%s dodged %d times, died %d times"
                          % (args[0], stats['misses'], stats['hits']))

    @keyword('roulette')
    @keyword.sub('clearstats')
    @keyword.autohelp
    def roulette_clearstats(self, irc_c, msg, trigger, args, kargs):
        ''':: clear stats'''
        self.r.clear()

    @keyword('8ball')
    @keyword.autohelp_noargs
    def magic_8ball(self, irc_c, msg, trigger, args, kargs):
        """[question]? :: Ask the magic 8 ball a question."""
        if not msg.message.endswith('?'):
            msg.reply("%s: that does not look like a question to me" %
                      msg.nick)
            return
        msg.reply("%s: %s" % (msg.nick, random.choice(self.ballresp)))


class Roulette(object):

    luckyQuotes = [
        "got lucky!",
        "is safe... for now.",
        "lived to see another day!"
    ]
    unluckyQuotes = [
        "swallowed a bullet!",
        "snuffed it!",
        "kicked the bucket!",
        "just died!"
    ]

    def __init__(self):
        self.loaded = False
        self.fired = False
        self.chamber = None
        self.position = 0
        self.stats = {}

    @staticmethod
    def luckyMsg():
        return random.choice(Roulette.luckyQuotes)

    @staticmethod
    def unluckyMsg():
        return random.choice(Roulette.unluckyQuotes)

    def clear(self):
        self.stats = {}

    def reload(self):
        self.chamber = random.choice([0, 1, 2, 3, 4, 5])
        self.position = 0
        self.loaded = True

    def getStats(self, nick):
        if nick in self.stats:
            return self.stats[nick]

    def getGlobalStats(self):
        stats = {'hits': 0, 'misses': 0}
        for name in self.stats.keys():
            stats['hits'] += self.stats[name]['hits']
            stats['misses'] += self.stats[name]['misses']
        return stats

    def fire(self, nick):
        if not self.loaded:
            self.reload()

        if nick not in self.stats:
            self.stats[nick] = {'hits': 0, 'misses': 0}

        if(self.position == self.chamber):
            self.loaded = False
            self.fired = True
            self.stats[nick]['hits'] += 1
            return True
        else:
            self.position += 1
            self.stats[nick]['misses'] += 1
            return False

########NEW FILE########
__FILENAME__ = channels
#!/usr/bin/env python
#
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import re
from .components import component_class, observes, msg_parser


@component_class('channels')
class Channels(object):
    """ track channels and stuff """
    def __init__(self, irc_c, config):
        self.channels = set()
        self.config = config
        self.db = None
        print("Channel Management Loaded")

    #Provide a little bit of magic
    def __contains__(self, channel):
        return channel.lower() in self.channels

    @observes('IRC_ONCONNECT')
    def _autojoin(self, irc_c):
        self.channels.clear()
        if self.config.autojoin:
            if isinstance(self.config.autojoin, basestring):
                self.config.autojoin = self.config.autojoin.split(',')
            if self.config.db and irc_c.db:
                print("Loading Channels from DB")
                self.db = irc_c.db.get('channels', 'autojoin')
                if self.db.value:
                    merge = list(set(self.db.value + self.config.autojoin))
                    self.config.autojoin = merge
                else:
                    self.db.value = []
                self.db.value = sorted(self.config.autojoin)
                self.db.commit()
            print("Channels Auto Joining: %r" % self.config.autojoin)
            irc_c.JOIN(self.config.autojoin)

    @msg_parser('JOIN')
    def _join_parser(self, msg, irc_c):
        msg.raw_channel = re.sub(r'^:', '', msg.args.strip())
        msg.channel = msg.raw_channel.lower()

    @msg_parser('PART')
    def _part_parser(self, msg, irc_c):
        msg.raw_channel, _, message = msg.args.strip().partition(' ')
        msg.channel = msg.raw_channel.lower()
        msg.message = re.sub(r'^:', '', message)

    @msg_parser('KICK')
    def _kick_parser(self, msg, irc_c):
        msg.raw_channel, msg.victim, message = msg.args.split(' ', 2)
        msg.channel = msg.raw_channel.lower()
        msg.message = re.sub(r'^:', '', message)

    @observes('IRC_MSG_JOIN')
    def _join(self, irc_c, msg):
        #Only Our Joins
        if msg.nick.lower() == irc_c.botnick.lower():
            self.channels.add(msg.channel)
            if self.db and msg.channel not in self.db.value:
                self.db.value.append(msg.channel)
                self.db.value.sort()
                self.db.commit()

    @observes('IRC_MSG_PART')
    def _part(self, irc_c, msg):
        #Only Our Parts
        if msg.nick.lower() == irc_c.botnick.lower():
            self.channels.remove(msg.channel)
            if self.db and msg.channel in self.db.value:
                self.db.value.remove(msg.channel)
                self.db.value.sort()
                self.db.commit()

    @observes('IRC_MSG_KICK')
    def _kick(self, irc_c, msg):
        if irc_c.botnick.lower() == msg.victim.lower():
            self.channels.remove(msg.channel)

########NEW FILE########
__FILENAME__ = components
#!/usr/bin/env python
#
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import inspect
import collections
from importlib import import_module

from gevent.event import AsyncResult
import gevent

from .util.decorator import EasyDecorator
from .irc import Message

__all__ = ['component_class',
           'msg_parser',
           'watches', 'observe', 'observes', 'handle', 'handles',
           'every',
           'triggers_on', 'keyword', 'keywords', 'trigger', 'triggers',
           'ComponentManager']

#Used to mark classes for later inspection
CLASS_MARKER = '_PYAIB_COMPONENT'


def component_class(cls):
    """
        Let the component loader know to load this class
        If they pass a string argument to the decorator use it as a context
        name for the instance
    """
    if isinstance(cls, basestring):
        context = cls

        def wrapper(cls):
            setattr(cls, CLASS_MARKER, context)
            return cls
        return wrapper

    elif inspect.isclass(cls):
        setattr(cls, CLASS_MARKER, True)
        return cls


def _requires(*names):
    def wrapper(cls):
        cls.__requires__ = names
        return cls
    return wrapper

component_class.requires = _requires


def _get_plugs(method, kind):
    """ Setup a place to put plugin hooks, allowing only one type per func """
    if not hasattr(method, '__plugs__'):
        method.__plugs__ = (kind, [])
    elif method.__plugs__[0] != kind:
        raise RuntimeError('Multiple Hook Types on a single method (%s)' %
                           method.__name__)
    return method.__plugs__[1]


def msg_parser(*kinds, **kwargs):
    """
    Defines that this method is a message type parser
    @param kinds: List of IRC message types/numerics
    @param kwargs: Accepts chain keyword, True or 'after' executes this after
        the existing parser. 'before' execute before existing parsers.
        default is to replace the existing parser
    """
    chain = kwargs.pop('chain', False)
    def wrapper(func):
        parsers = _get_plugs(func, 'parsers')
        parsers.extend([(kind, chain) for kind in kinds])
        return func
    return wrapper


def watches(*events):
    """ Define a series of events to later be subscribed to """
    def wrapper(func):
        eplugs = _get_plugs(func, 'events')
        eplugs.extend([event for event in events if event not in eplugs])
        return func
    return wrapper
observes = watches
observe = watches
handle = watches
handles = watches


class _Ignore(EasyDecorator):
    """Only pass if triggers is from user not ignored"""
    def wrapper(dec, irc_c, msg, *args):
        if dec.args and dec.kwargs.get('runtime'):
            for attr in dec.args:
                if hasattr(dec._instance, attr):
                    ignore_nicks = getattr(dec._instance, attr)
                    if isinstance(ignore_nicks, basestring)\
                            and msg.sender.nick == ignore_nicks:
                        return
                    elif isinstance(ignore_nicks, collections.Container)\
                            and msg.sender.nick in ignore_nicks:
                        return
        elif dec.args and msg.sender.nick in dec.args:
            return
        return dec.call(irc_c, msg, *args)
watches.ignore = _Ignore


class _Channel(EasyDecorator):
    """Ignore triggers not in channels, or optionally a list of channels"""
    def wrapper(dec, irc_c, msg, *args):
        if msg.channel:
            #Did they want to restrict which channels
            #Should we lookup allowed channels at run time
            if dec.args and dec.kwargs.get('runtime'):
                for attr in dec.args:
                    ok = False
                    if hasattr(dec._instance, attr):
                        channel = getattr(dec._instance, attr)
                        if isinstance(channel, basestring)\
                                and msg.channel == channel:
                            ok = True
                        elif isinstance(channel, collections.Container)\
                                and msg.channel in channel:
                            ok = True
                if not ok:
                    return
            elif dec.args and msg.channel not in dec.args:
                return
            return dec.call(irc_c, msg, *args)
watches.channel = _Channel


def every(seconds, name=None):
    """ Define a timer to execute every interval """
    def wrapper(func):
        timers = _get_plugs(func, 'timers')
        timer = (name if name else func.__name__, seconds)
        if timer not in timers:
            timers.append(timer)
        return func
    return wrapper


class triggers_on(object):
    """Define a series of trigger words this method responds too"""
    def __init__(self, *words):
        self.words = words

    def __call__(self, func):
        triggers = _get_plugs(func, 'triggers')
        triggers.extend(set([word for word in self.words
                             if word not in triggers]))
        return func

    class channel(EasyDecorator):
        """Ignore triggers not in channels, or optionally a list of channels"""
        def wrapper(dec, irc_c, msg, trigger, args, kargs):
            if msg.channel:
                #Did they want to restrict which channels
                #Should we lookup allowed channels at run time
                if dec.args and dec.kwargs.get('runtime'):
                    ok = False
                    for attr in dec.args:
                        if hasattr(dec._instance, attr):
                            channel = getattr(dec._instance, attr)
                            if isinstance(channel, basestring)\
                                    and msg.channel.lower() == channel:
                                ok = True
                            elif isinstance(channel, collections.Container)\
                                    and msg.channel.lower() in channel:
                                ok = True
                    if not ok:
                        return
                elif dec.args and msg.channel not in dec.args:
                    return
            elif not dec.kwargs.get('private'):
                return
            return dec.call(irc_c, msg, trigger, args, kargs)

    class private_or_channel(channel):
        """Allow either private or specified channel"""
        def __init__(dec, *args, **kwargs):
            kwargs['private'] = True
            super(private_or_channel, dec).__init__(*args, **kwargs)

    class private(EasyDecorator):
        """Only pass if triggers is from message not in a channel"""
        def wrapper(dec, irc_c, msg, trigger, args, kargs):
            if not msg.channel:
                return dec.call(irc_c, msg, trigger, args, kargs)

    class helponly(EasyDecorator):
        """Only provide help"""
        def wrapper(dec, irc_c, msg, trigger, args, kargs):
            msg.reply('%s %s' % (trigger,
                                 irc_c.triggers._clean_doc(dec.__doc__)))

    class autohelp(EasyDecorator):
        """Make --help trigger help"""
        def wrapper(dec, irc_c, msg, trigger, args, kargs):
            if 'help' in kargs or (args and args[0] == 'help'):
                msg.reply('%s %s' % (trigger,
                                     irc_c.triggers._clean_doc(dec.__doc__)))
            else:
                dec.call(irc_c, msg, trigger, args, kargs)

    class autohelp_noargs(EasyDecorator):
        """Empty args / kargs trigger help"""
        #It was impossible to call autohelp to decorate this method
        def wrapper(dec, irc_c, msg, trigger, args, kargs):
            if (not args and not kargs) or 'help' in kargs or (
                    args and args[0] == 'help'):
                msg.reply('%s %s' % (trigger,
                                     irc_c.triggers._clean_doc(dec.__doc__)))
            else:
                return dec.call(irc_c, msg, trigger, args, kargs)

    class sub(EasyDecorator):
        """Handle only sub(words) for a given trigger"""
        def __init__(dec, *words):
            dec._subs = words
            for word in words:
                if not isinstance(word, basestring):
                    raise TypeError("sub word must be a string")

        def wrapper(dec, irc_c, msg, trigger, args, kargs):
            if args and args[0].lower() in dec._subs:
                return dec.call(irc_c, msg, '%s %s' % (trigger,
                                                       args[0].lower()),
                                args[1:], kargs)

    subs = sub

    class nosub(EasyDecorator):
        """Prevent call if argument is present"""
        def wrapper(dec, irc_c, msg, trigger, args, kargs):
            if (not dec.args and args) or (dec.args and args
                                           and args[0].lower() in dec.args):
                return
            else:
                return dec.call(irc_c, msg, trigger, args, kargs)

    nosubs = nosub

keyword = keywords = trigger = triggers = triggers_on
triggers.ignore = _Ignore
triggers.channel = _Channel


class ComponentManager(object):
    """ Manage and Load all pyaib Components """
    _loaded_components = collections.defaultdict(AsyncResult)

    def __init__(self, context, config):
        """ Needs a irc context and its config """
        self.context = context
        self.config = config

    def load(self, name):
        """ Load a python module as a component """
        if self.is_loaded(name):
            return
        #Load top level config item matching component name
        basename = name.split('.').pop()
        config = self.context.config.setdefault(basename, {})
        print("Loading Component %s..." % name)
        ns = self._process_component(name, 'pyaib', CLASS_MARKER,
                                     self.context, config)
        self._loaded_components[basename].set(ns)

    def _require(self, name):
        self._loaded_components[name].wait()

    def load_configured(self, autoload=None):
        """
            Load all configured components autoload is a list of components
            to always load
        """
        components = []
        if isinstance(autoload, (list, tuple, set)):
            components.extend(autoload)

        #Don't do duplicate loads
        if self.config.load:
            if not isinstance(self.config.load, list):
                self.config.load = self.config.load.split(' ')
            [components.append(comp) for comp in self.config.load
             if comp not in components]
        gevent.joinall([gevent.spawn(self.load, component)
                        for component in components])

    def is_loaded(self, name):
        """ Determine by name if a component is loaded """
        return self._loaded_components[name].ready()

    def _install_hooks(self, context, hooked_methods):
        #Add All the hooks to the right place
        for method in hooked_methods:
            kind, args = method.__plugs__
            if kind == 'events':
                for event in args:
                    context.events(event).observe(method)
            elif kind == 'triggers':
                for word in args:
                    context.triggers(word).observe(method)
            elif kind == 'timers':
                for name, seconds in args:
                    context.timers.set(name, method, every=seconds)
            elif kind == 'parsers':
                for name, chain in args:
                    self._add_parsers(method, name, chain)

    def _add_parsers(self, method, name, chain):
        """ Handle Message parser adding and chaining """
        if chain:
            existing = Message.get_parser(name)

            def _chain_after(msg, irc_c):
                existing(msg, irc_c)
                method(msg, irc_c)

            def _chain_before(msg, irc_c):
                method(msg, irc_c)
                existing(msg, irc_c)

            if existing and chain == 'before':
                Message.add_parser(name, _chain_before)
            elif existing:
                Message.add_parser(name, _chain_after)
            else:
                Message.add_parser(name, method)
        else:
            Message.add_parser(name, method)

    def _find_annotated_callables(self, class_marker, component_ns, config,
                                  context):
        annotated_callables = []
        for name, member in inspect.getmembers(component_ns):
            #Find Classes marked for loading
            if inspect.isclass(member) and hasattr(member, class_marker):
                #Handle Requirements
                if hasattr(member, '__requires__'):
                    for req in member.__requires__:
                        self._require(req)
                obj = member(context, config)
                #Save the context for this obj if the class_marker is a str
                context_name = getattr(obj, class_marker)
                if isinstance(context_name, basestring):
                    context[context_name] = obj
                    #Search for hooked instance methods
                for name, thing in inspect.getmembers(obj):
                    if (isinstance(thing, collections.Callable)
                            and hasattr(thing, '__plugs__')):
                        annotated_callables.append(thing)
            #Find Functions with Hooks
            if (isinstance(member, collections.Callable)
                    and hasattr(member, '__plugs__')):
                annotated_callables.append(member)
        return annotated_callables

    def _process_component(self, name, path, class_marker, context, config):
        if name.startswith('/'):
            importname = name[1:]
            path = None
        else:
            importname = '.'.join([path, name])

        try:
            component_ns = import_module(importname)
        except ImportError as e:
            raise ImportError('pyaib failed to load (%s): %r'
                              % (importname, e))

        annotated_calls = self._find_annotated_callables(class_marker,
                                                         component_ns, config,
                                                         context)
        self._install_hooks(context, annotated_calls)
        return component_ns

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
#
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import sys
import os
import yaml

from .util import data


class Config(object):
    def __init__(self, configFile=None, configPath=None):
        print("Config Module Loaded.")
        if configFile is None:
            raise RuntimeError("YOU MUST PASS 'configFile' DURING BOT INIT")
        (config, searchpaths) = self.__load(configFile, configPath)
        if config is None:
            msg = ("You need a valid main config (searchpaths: %s)" %
                   searchpaths)
            raise RuntimeError(msg)
        #Wrap the config dict
        self.config = data.CaseInsensitiveObject(config)

        #Files can be loaded from the 'CONFIG' section
        #Load the load statement if any
        for section, file in self.config.setdefault('config.load', {}).items():
            config = self.__load(file,
                                 [configPath, self.config.get('config.path')])
            #Badly syntax configs will be empty
            if config is None:
                config = {}
            self.config.set(section, config)

    #Attempt to load a config file name print exceptions
    def __load(self, configFile, path=None):
        data = None
        (filepath, searchpaths) = self.__findfile(configFile, path)
        if filepath:  # If the file is found lets try to load it
            try:
                data = yaml.safe_load(file(filepath, 'r'))
                print("Loaded Config from %s." % configFile)
            except yaml.YAMLError, exc:
                print("Error in configuration file (%s): %s" % (filepath, exc))
                if hasattr(exc, 'problem_mark'):
                    mark = exc.problem_mark
                    print("Error position: (%s:%s)" % (mark.line + 1,
                                                       mark.column + 1))
        return (data, searchpaths)

    #Find the requested file in the path (for PARs)
    #If configFile is a list then do lookup for each
    #First Found is returned
    def __findfile(self, configFile, path=None):
        searchpaths = []
        if isinstance(path, list):
            searchpaths.extend(path)  # Optional Config path
        elif path:
            searchpaths.append(path)
        searchpaths.extend(sys.path)
        for path in searchpaths:
            if not os.path.isdir(path):
                path = os.path.dirname(path)
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    if configFile in files:
                        return (os.path.join(root, configFile), searchpaths)
        return (None, searchpaths)

########NEW FILE########
__FILENAME__ = db
#!/usr/bin/env python
#
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""
Generic DB Component

Provide a simple key value store.

The Backend data store can be changed out via a driver intermediate.
Must support the following methods, object is a dict or list or mixture

[key(plain text), payload] should be the return value for operations that
return objects

Driver Methods:

getObject(key=, bucket=)
setObject(object, key=, bucket=)
updateObject(object, key=, bucket=)
updateObjectKey(bucket=, oldkey=, newkey=)
updateObjectBucket(key=, oldbucket=, newbucket=)
getAllObjects(bucket=)  (iter)
deleteObject(key=, bucket=) #One at a time for safety
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import hashlib
import json
import inspect
from importlib import import_module

from .components import component_class

CLASS_MARKER = '_PYAIB_DB_DRIVER'


def sha256(msg):
    """ return the hex digest for a givent msg """
    return hashlib.sha256(msg).hexdigest()

hash = sha256


def jsonify(thing):
    return json.dumps(thing, sort_keys=True, separators=(',', ':'))


def dejsonify(jsonstr):
    return json.loads(jsonstr)


def db_driver(cls):
    """Mark a class def as a db driver"""
    setattr(cls, CLASS_MARKER, True)
    return cls


@component_class('db')
class ObjectStore(object):
    """ Generic Key Value Store """

    # Database Driver is not loaded
    _driver = None

    def __init__(self, irc_c, config):
        self.config = config
        self._load_driver()
        # Small Sanity Test
        if not self._driver:
            raise RuntimeError('Can not load DB component driver not loaded')

    def _load_driver(self):
        """ Loads the configured driver config.db.backend """
        name = self.config.backend
        if not name:
            #Raise some exception, bail out we are done.
            raise RuntimeError('config item db.backend not set')
        if '.' in name:
            importname = name
        else:
            importname = 'pyaib.dbd.%s' % name
        basename = name.split('.').pop()
        driver_ns = import_module(importname)
        for name, cls in inspect.getmembers(driver_ns, inspect.isclass):
            if hasattr(cls, CLASS_MARKER):
                #Load up the driver
                self._driver = cls(self.config.driver.setdefault(basename, {}))
                break
        else:
            raise RuntimeError('Unable to instance db driver %r' % name)

    #Define easy data access methods
    def get(self, bucket, key=None):
        """Get a Bucket or if key is provided get a Item from the db"""
        if key is None:
            return Bucket(self, bucket)
        key, payload = self._driver.getObject(key, bucket)
        return Item(self._driver, bucket, key, payload)

    def getAll(self, bucket):
        """Get all items in the bucket ITERATOR"""
        for key, payload in self._driver.getAllObjects(bucket):
            yield Item(self._driver, bucket, key, payload)

    def set(self, bucket, key, obj):
        """Store an object in the db by bucket and key, return an Item"""
        self._driver.setObject(obj, key, bucket)
        return Item(self._driver, bucket, key, obj)

    def delete(self, bucket, key):
        """Delete an object in the store"""
        self._driver.deleteObject(key, bucket)


class Item(object):
    """ Represents a item stored in the key value store, with easy methods """
    def __init__(self, driver, bucket, key, payload):
        self._driver = driver
        #Store some meta to determine changes for commit
        self._meta = {'bucket': bucket, 'key': key,
                      'objectHash': hash(jsonify(payload))}
        self.bucket = bucket
        self.key = key
        self.value = payload

    def reload(self):
        self.key, self.value = self._driver.getObject(self._meta['key'],
                                                      self._meta['bucket'])
        self.bucket = self._meta['bucket']

    def delete(self):
        self._driver.deleteObject(self.key, self.bucket)

    def commit(self):
        if hash(jsonify(self.value)) != self._meta['objectHash']:
            if not self.value:
                self.delete()
            else:
                self._driver.updateObject(self.value, self._meta['key'],
                                          self._meta['bucket'])
        elif self._meta['bucket'] != self.bucket:
            if not self.bucket:
                self.delete()
            else:
                self._driver.updateObjectBucket(self._meta['key'],
                                                self._meta['bucket'],
                                                self.bucket)
        elif self._meta['key'] != self.key:
            if not self.key:
                self.delete()
            else:
                self._driver.updateObjectKey(self._meta['bucket'],
                                             self._meta['key'], self.key)
        #Nothing left to commit


class Bucket(object):
    """ An class tied to a bucket """
    def __init__(self, db, bucket):
        self._db = db
        self._bucket = bucket

    def __repr__(self):
        return 'Bucket(%r)' % self._bucket

    def get(self, key):
        return self._db.get(self._bucket, key)

    def getAll(self):
        return self._db.getAll(self._bucket)

    def set(self, key, obj):
        return self._db.set(self._bucket, key, obj)

    def delete(self, key):
        return self._db.delete(self._bucket, key)

########NEW FILE########
__FILENAME__ = sqlite
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sqlite3
from zlib import compress, decompress

from pyaib.db import db_driver, hash

try:
    #Try to make use of ujson if we have it
    import ujson as json
    import pyaib.db
    pyaib.db.json = json
    pyaib.db.jsonify = json.dumps
except ImportError:
    pass

from pyaib.db import jsonify, dejsonify


@db_driver
class SqliteDriver(object):
    """ A Sqlite3 Pyaib DB Driver """

    def __init__(self, config):
        path = config.path
        if not path:
            raise RuntimeError('Missing "path" config for sqlite driver')
        try:
            self.conn = sqlite3.connect(path)
        except sqlite3.OperationalError as e:
            #Can't open DB
            raise
        print("Sqlite DB Driver Loaded!")

    def _bucket_exists(self, bucket):
        c = self.conn.execute("SELECT name from sqlite_master "
                              "WHERE type='table' and name=?",
                              (hash(bucket),))
        if c.fetchone():
            return True
        else:
            return False

    def _has_keys(self, bucket):
        c = self.conn.execute("SELECT count(*) from `{}`".format(hash(bucket)))
        row = c.fetchone()
        if row[0]:
            return True
        else:
            return False

    def _create_bucket(self, bucket):
        self.conn.execute("CREATE TABLE `{}` (key blob UNIQUE, value blob)"
                          .format(hash(bucket)))

    def getObject(self, key, bucket):
        if not self._bucket_exists(bucket):
            return key, None
        c = self.conn.execute("SELECT key, value from `{}` WHERE key=?"
                              .format(hash(bucket)), (key,))
        row = c.fetchone()
        if row:
            k, v = row
            return (k, dejsonify(decompress(v)))
        else:
            return key, None

    def setObject(self, obj, key, bucket):
        if not self._bucket_exists(bucket):
            self._create_bucket(bucket)
        self.conn.execute("REPLACE INTO `{}` (key, value) VALUES (?, ?)"
                          .format(hash(bucket)),
                          (key, buffer(compress(jsonify(obj)))))
        self.conn.commit()

    def updateObject(self, obj, key, bucket):
        self.setObject(obj, key, bucket)

    def updateObjectKey(self, bucket, oldkey, newkey):
        self.conn.execute("UPDATE `{}` set key = ? where key=?"
                          .format(hash(bucket)), (newkey, oldkey))
        self.conn.commit()

    def updateObjectBucket(self, key, oldbucket, newbucket):
        _, v = self.getObject(key, oldbucket)
        self.deleteObject(key, oldbucket, commit=False)
        self.setObject(v, key, newbucket)

    def getAllObjects(self, bucket):
        if not self._bucket_exists(bucket):
            return
        for k, v in self.conn.execute("SELECT key, value from `{}`"
                                      .format(hash(bucket))):
            yield (k, dejsonify(decompress(v)))

    def deleteObject(self, key, bucket, commit=True):
        if self._bucket_exists(bucket):
            self.conn.execute("DELETE from `{}` where key = ?"
                              .format(hash(bucket)), (key,))
            if not self._has_keys(bucket):
                self.conn.execute("DROP TABLE IF EXISTS `{}`"
                                  .format(hash(bucket)))
            if commit:
                self.conn.commit()

########NEW FILE########
__FILENAME__ = events
#!/usr/bin/env python
#
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import collections
import gevent
import gevent.pool

from . import irc


class Event(object):
    """ An Event Handler """
    def __init__(self):
        self.__observers = []

    def observe(self, observer):
        if isinstance(observer, collections.Callable):
            self.__observers.append(observer)
        else:
            print("Event Error: %s not callable" % repr(observer))
        return self

    def unobserve(self, observer):
        self.__observers.remove(observer)
        return self

    def fire(self, *args, **keywargs):
        #Pull the irc_c from the args
        irc_c = args[0]
        if not isinstance(irc_c, irc.Context):
            print("Error first argument should be the irc context")
            #Maybe DIE here
            return

        for observer in self.__observers:
            if isinstance(observer, collections.Callable):
                irc_c.bot_greenlets.spawn(observer, *args, **keywargs)
            else:
                print("Event Error: %s not callable" % repr(observer))

    def clearObjectObservers(self, inObject):
        for observer in self.__observers:
            if observer.__self__ == inObject:
                self.unobserve(observer)

    def getObserverCount(self):
        return len(self.__observers)

    def observers(self):
        return self.__observers

    def __bool__(self):
        return self.getObserverCount() > 0

    __nonzero__ = __bool__  # 2.x compat
    __iadd__ = observe
    __isub__ = unobserve
    __call__ = fire
    __len__ = getObserverCount


class Events(object):
    """ Manage events allow observers before events are defined"""
    def __init__(self, irc_c):
        self.__events = {}
        self.__nullEvent = NullEvent()
        #A place to track all the running events
        #Events load first so this seems logical
        irc_c.bot_greenlets = gevent.pool.Group()

    def list(self):
        return self.__events.keys()

    def isEvent(self, name):
        return name.lower() in self.__events

    def getOrMake(self, name):
        if not self.isEvent(name):
            #Make Event if it does not exist
            self.__events[name.lower()] = Event()
        return self.get(name)

    #Do not create the event on a simple get
    #Return the null event on non existent events
    def get(self, name):
        event = self.__events.get(name.lower())
        if event is None:  # Only on undefined events
            return self.__nullEvent
        return event

    __contains__ = isEvent
    __call__ = getOrMake
    __getitem__ = get


class NullEvent(object):
    """ Null Object Pattern: Don't Do Anything Silently"""
    def fire(self, *args, **keywargs):
        pass

    def clearObjectObservers(self, obj):
        pass

    def getObserverCount(self):
        return 0

    def __bool__(self):
        return False

    __nonzero__ = __bool__  # Diff between 3.x and 2.x

    def observe(self, observer):
        raise TypeError('Null Events can not have Observers!')

    def unobserve(self, observer):
        raise TypeError('Null Events do not have Observers!')

    __iadd__ = observe
    __isub__ = unobserve
    __call__ = fire
    __len__ = getObserverCount

########NEW FILE########
__FILENAME__ = irc
#!/usr/bin/env python
#
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import re
import sys
from textwrap import wrap
import traceback
import time

import gevent

from .linesocket import LineSocket
from .util import data
from .util.decorator import raise_exceptions
from . import __version__ as pyaib_version

MAX_LENGTH = 510

#Class for storing irc related information
class Context(data.Object):
    """Dummy Object to hold irc data and send messages"""
    # IRC COMMANDS are all CAPS for sanity with irc information
    # TODO: MOVE irc commands into component and under irc_c.cmd

    # Raw IRC Message
    def RAW(self, message):
        try:
            #Join up the message parts
            if isinstance(message, (list, tuple)):
                message = ' '.join(message)
            #Raw Send but don't allow empty spam
            if message is not None:
                #Clean up messages
                message = re.sub(r'[\r\n]', '', message).expandtabs(4).rstrip()
                if len(message):
                    self.client.socket.writeline(message)
                    #Fire raw send event for debug if exists [] instead of ()
                    self.events['IRC_RAW_SEND'](self, message)
        except TypeError:
            #Somebody tried to raw a None or something just print exception
            print("Bad RAW message: %r" % repr(message))
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_tb(exc_traceback)

    # Set our nick
    def NICK(self, nick):
        self.RAW('NICK %s' % nick)
        if not self.registered:
            #Assume we get the nick we want during registration
            self.botnick = nick

    #privmsg with max line handling
    def PRIVMSG(self, target, msg):
        if isinstance(msg, (list, tuple, set)):
            msg = ' '.join(msg)
        privmsg = 'PRIVMSG %s :%s'
        # length of self.botsender.raw is 0 when not set :P
        # + 2 because of leading : and space after nickmask
        prefix_length = len(self.botsender.raw) + 2 + len(privmsg %
                                                          (target, ''))
        for line in wrap(msg, MAX_LENGTH - prefix_length):
            self.RAW(privmsg % (target, line))

    def JOIN(self, channels):
        if isinstance(channels, (list, set, tuple)):
            channels = list(channels)
        else:
            channels = [channels]

        join = 'JOIN '
        msg = join

        #Build up join messages (wrap won't work)
        while channels:
            channel = channels.pop() + ','
            if len(msg + channel) > MAX_LENGTH:
                self.RAW(msg.rstrip(','))
                msg = join
            msg += channel

        self.RAW(msg.rstrip(','))

    def PART(self, channels, message=None):
        if isinstance(channels, list):
            channels = ','.join(channels)
        if message:
            self.RAW('PART %s :%s' % (channels, message))
        else:
            self.RAW('PART %s' % channels)


class Client(object):
    """IRC Client contains irc logic"""
    def __init__(self, irc_c):
        self.config = irc_c.config.irc
        self.servers = self.config.servers
        self.irc_c = irc_c
        irc_c.client = self
        self.reconnect = True
        self.__register_client_hooks(self.config)

    #The IRC client Event Loop
    #Call events for every irc message
    def _try_connect(self):
        for server in self.servers:
            host, port, ssl = self.__parseserver(server)
            sock = LineSocket(host, port, SSL=ssl)
            if sock.connect():
                self.socket = sock
                return sock
        return None

    def _fire_msg_events(self, sock, irc_c):
        while True:  # Event still running
            raw = sock.readline()  # Yield
            if raw:
                #Fire RAW MSG if it has observers
                irc_c.events['IRC_RAW_MSG'](irc_c, raw)
                #Parse the RAW message
                msg = Message(irc_c, raw)
                if msg:  # This is a valid message
                    #So we can do length calculations for PRIVMSG WRAPS
                    if (msg.nick == irc_c.botnick
                            and irc_c.botsender != msg.sender):
                        irc_c.botsender = msg.sender
                    #Event for kind of message [if exists]
                    eventKey = 'IRC_MSG_%s' % msg.kind
                    irc_c.events[eventKey](irc_c, msg)
                    #Event for parsed messages [if exists]
                    irc_c.events['IRC_MSG'](irc_c, msg)

    def run(self):
        irc_c = self.irc_c

        #Function to Fire Timers
        def _timers(irc_c):
            print("Starting Timers Loop")
            while True:
                gevent.sleep(1)
                irc_c.timers(irc_c)

        #If servers is not a list make it one
        if not isinstance(self.servers, list):
            self.servers = self.servers.split(',')
        while self.reconnect:
            # Keep trying to reconnect going through the server list
            sock = self._try_connect()
            if sock is None:
                gevent.sleep(10)  # Wait 10 Seconds between retries
                print("Retrying Server List...")
                continue
            #Catch when the socket has an exception
            try:
                #Have the line socket autofill its buffers
                #Maybe this should be in socket.connect
                gevent.spawn(raise_exceptions(self.socket.run))
                gevent.sleep(0)  # Yield
                #Fire Socket Connect Event (Always)
                irc_c.events('IRC_SOCKET_CONNECT')(irc_c)
                irc_c.bot_greenlets.spawn(_timers, irc_c)
                #Enter the irc event loop
                self._fire_msg_events(sock, irc_c)
            except LineSocket.SocketError:
                try:
                    self.socket.close()
                    print("Giving Greenlets Time(1s) to die..")
                    irc_c.bot_greenlets.join(timeout=1)
                except gevent.Timeout:
                    # We got a timeout kill the others
                    print("Killing Remaining Greenlets...")
                    irc_c.bot_greenlets.kill()
        else:
            print("Bot Dying.")

    def die(self, message="Dying"):
        self.irc_c.RAW("QUIT :%s" % message)
        self.reconnect = False

    def cycle(self):
        self.irc_c.RAW("QUIT :Reconnecting")

    def signal_handler(self, signum, frame):
        """ Handle Ctrl+C """
        self.irc_c.RAW("QUIT :Received a ctrl+c exiting")
        self.reconnect = False

    #Register our own hooks for basic protocol handling
    def __register_client_hooks(self, options):
        events = self.irc_c.events
        timers = self.irc_c.timers

        #AUTO_PING TIMER
        def AUTO_PING(irc_c, msg):
            irc_c.RAW('PING :%s' % irc_c.server)
        #if auto_ping unless set to 0
        if options.auto_ping != 0:
            timers.set('AUTO_PING', AUTO_PING,
                       every=options.auto_ping or 600)

        #Handle PINGs
        def PONG(irc_c, msg):
            irc_c.RAW('PONG :%s' % msg.args)
            #On a ping from the server reset our timer for auto-ping
            timers.reset('AUTO_PING', AUTO_PING)
        events('IRC_MSG_PING').observe(PONG)

        #On the socket connecting we should attempt to register
        def REGISTER(irc_c):
            irc_c.registered = False
            if options.password:  # Use a password if one is issued
                #TODO allow password to be associated with server url
                irc_c.RAW('PASS %s' % options.password)
            irc_c.RAW('USER %s 8 * :%s'
                      % (options.user,
                         options.realname.format(version=pyaib_version)))
            irc_c.NICK(options.nick)
        events('IRC_SOCKET_CONNECT').observe(REGISTER)

        #Trigger an IRC_ONCONNECT event on 001 msg's
        def ONCONNECT(irc_c, msg):
            irc_c.server = msg.sender
            irc_c.registered = True
            irc_c.events('IRC_ONCONNECT')(irc_c)
        events('IRC_MSG_001').observe(ONCONNECT)

        def NICK_INUSE(irc_c, msg):
            if not irc_c.registered:
                irc_c.NICK('%s_' % irc_c.botnick)
            _, nick, _ = msg.args.split(' ', 2)
            #Fire event for other modules [if its watched]
            irc_c.events['IRC_NICK_INUSE'](irc_c, nick)
        events('IRC_MSG_433').observe(NICK_INUSE)

        #When we change nicks handle botnick updates
        def NICK(irc_c, msg):
            if msg.nick.lower() == irc_c.botnick.lower():
                irc_c.botnick = msg.args
            irc_c.events['IRC_NICK_CHANGE'](irc_c, msg.nick, msg.args)
        events('IRC_MSG_NICK').observe(NICK)

    #Parse Server Records
    # (ssl:)?host(:port)? // after ssl: is optional
    # TODO allow password@ in server strings
    def __parseserver(self, server):
        match = re.search(r'^(ssl:(?://)?)?([^:]+)(?::(\d+))?$',
                          server.lower())
        if match is None:
            print('BAD Server String: %s' % server)
            sys.exit(1)
        #Pull out the pieces of the server line
        ssl = match.group(1) is not None
        host = match.group(2)
        port = int(match.group(3)) or 6667
        return [host, port, ssl]


class Message (object):
    """Parse raw irc text into easy to use class"""

    MSG_REGEX = re.compile(r'^(?::([^ ]+) )?([^ ]+) (.+)$')
    DIRECT_REGEX = re.compile(r'^([^ ]+) :?(.+)$')

    #Some Message prefixes for channel prefixes
    PREFIX_OP = 1
    PREFIX_HALFOP = 2
    PREFIX_VOICE = 3

    # Place to store parsers for complex message types
    _parsers = {}

    @classmethod
    def add_parser(cls, kind, handler):
        cls._parsers[kind] = handler

    @classmethod
    def get_parser(cls, kind):
        return cls._parsers.get(kind)

    def __init__(self, irc_c, raw):
        self.raw = raw
        match = Message.MSG_REGEX.search(raw)
        if match is None:
            self._error_out('IRC Message')

        #If the prefix is blank its the server
        self.sender = Sender(match.group(1) or irc_c.server)
        self.kind = match.group(2)
        self.args = match.group(3)
        self.nick = self.sender.nick

        #Time Stamp every message (Floating Point is Fine)
        self.timestamp = time.time()

        #Handle more message types
        if self.kind in Message._parsers:
            Message._parsers[self.kind](self, irc_c)

        #Be nice strip off the leading : on args
        self.args = re.sub(r'^:', '', self.args)

    def _error_out(self, text):
        print('BAD %s: %s' % (text, self.raw))
        self.kind = None

    def __bool__(self):
        return self.kind is not None

    __nonzero__ = __bool__

    def __str__(self):
        return self.raw

    #Friendly get that doesnt blow up on non-existent entries
    def __getattr__(self, key):
        return None

    @staticmethod
    def _directed_message(msg, irc_c):
        match = Message.DIRECT_REGEX.search(msg.args)
        if match is None:
            return msg._error_out('PRIVMSG')
        msg.target = match.group(1).lower()
        msg.message = match.group(2)

        #If the target is not the bot its a channel message
        if msg.target != irc_c.botnick:
            msg.reply_target = msg.target
            #Strip off any message prefixes
            msg.raw_channel = msg.target.lstrip('@%+')
            msg.channel = msg.raw_channel.lower()  # Normalized to lowercase
            #Record the perfix
            if msg.target.startswith('@'):
                msg.channel_prefix = msg.PREFIX_OP
            elif msg.target.startswith('%'):
                msg.channel_prefix = msg.PREFIX_HALFOP
            elif msg.target.startswith('+'):
                msg.channel_prefix = msg.PREFIX_VOICE
        else:
            msg.reply_target = msg.nick

        #Setup a reply method
        def __reply(text):
            irc_c.PRIVMSG(msg.reply_target, text)
        msg.reply = __reply


#Install some common parsers
Message.add_parser('PRIVMSG', Message._directed_message)
Message.add_parser('NOTICE', Message._directed_message)
Message.add_parser('INVITE', Message._directed_message)


class Sender(unicode):
    """all the logic one would need for understanding sender part of irc msg"""
    def __new__(cls, sender):
        #Pull out each of the pieces at instance time
        if '!' in sender:
            nick, _, usermask = sender.partition('!')
            inst = unicode.__new__(cls, nick)
            inst._user, _, inst._hostname = usermask.partition('@')
            return inst
        else:
            return unicode.__new__(cls, sender)

    @property
    def raw(self):
        """ get the raw sender string """
        if self.nick:
            return '%s!%s@%s' % (self, self._user, self._hostname)
        else:
            return self

    @property
    def nick(self):
        """ get the nick """
        if hasattr(self, '_hostname'):
            return self

    @property
    def user(self):
        """ get the user name """
        if self.nick:
            return self._user.lstrip('~')

    @property
    def hostname(self):
        """ get the hostname """
        if self.nick:
            return self._hostname
        else:
            return self

    @property
    def usermask(self):
        """ get the usermask user@hostname """
        if self.nick:
            return '%s@%s' % (self._user, self._hostname)

########NEW FILE########
__FILENAME__ = ircbot
#!/usr/bin/env python
#
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

#WE want the ares resolver, screw thread-pool
import os
os.environ['GEVENT_RESOLVER'] = 'ares'
import gevent.monkey
gevent.monkey.patch_all()

#Screw you python, lets try this for unicode support
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import signal
import gevent

from .config import Config
from .events import Events
from .timers import Timers
from .components import ComponentManager
from . import irc


class IrcBot(object):
    """ A easy framework to make useful bots """
    def __init__(self, *args, **kargs):
        #Shortcut
        install = self._install

        #Irc Context the all purpose data structure
        install('irc_c', irc.Context(), False)

        #Load the Config
        install('config', Config(*args, **kargs).config)

        #Install most basic fundamental functionality
        install('events', self._loadComponent(Events, False))
        install('timers', self._loadComponent(Timers, False))

        #Load the ComponentManager and load components
        autoload = ['triggers', 'channels', 'plugins']  # Force these to load
        install('components', self._loadComponent(ComponentManager))\
            .load_configured(autoload)

    def run(self):
        """ Starts the Event loop for the bot """
        client = irc.Client(self.irc_c)

        #Tell the client to run inside a greenlit
        signal.signal(signal.SIGINT, client.signal_handler)
        gevent.spawn(client.run).join()

    # Assign things to self and Context
    def _install(self, name, thing, inContext=True):
        setattr(self, name, thing)
        if inContext:
            self.irc_c[name] = thing
        return thing

    def _loadComponent(self, cname, passConfig=True):
        """ Load a Component passing it the context and its config """
        #I am using != instead of is not because of space limits :P
        config = cname.__name__ if cname != ComponentManager else "Components"
        if passConfig:
            return cname(self.irc_c, self.config.setdefault(config, {}))
        else:
            return cname(self.irc_c)

########NEW FILE########
__FILENAME__ = linesocket
#!/usr/bin/env python
#
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""
Line based socket using gevent
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import errno

import gevent
from gevent import socket
from gevent import queue, select
from OpenSSL import SSL

from .util.decorator import utf8Encode, utf8Decode, raise_exceptions


class LineSocketBuffers(object):
    def __init__(self):
        self.readbuffer = bytearray()
        self.writebuffer = bytearray()

    def clear(self):
        del self.readbuffer[0:]
        del self.writebuffer[0:]

    def readbuffer_mv(self):
        return memoryview(self.readbuffer)

    def writebuffer_mv(self):
        return memoryview(self.writebuffer)

#We use this to end lines we send to the server its in the RFC
#Buffers don't support unicode just yet so 'encode'
LINEENDING = b'\r\n'


class LineSocket(object):
    """Line based socket impl takes a host and port"""
    def __init__(self, host, port, SSL):
        self.host, self.port, self.SSL = (host, port, SSL)
        self._socket = None
        self._buffer = LineSocketBuffers()
        #Thread Safe Queues for
        self._IN = queue.Queue()
        self._OUT = queue.Queue()

    #Exceptions for LineSockets
    class SocketError(Exception):
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return repr(self.value)

    # Connect to remote host
    def connect(self):
        host, port = (self.host, self.port)

        #Clean out the buffers
        self._buffer.clear()

        #If the existing socket is not None close it
        if self._socket is not None:
            self.close()

        # Resolve the hostname and connect (ipv6 ready)
        sock = None
        try:
            for info in socket.getaddrinfo(host, port, socket.AF_UNSPEC,
                                           socket.SOCK_STREAM):
                family, socktype, proto, canonname, sockaddr = info

                #Validate the socket will make
                try:
                    sock = socket.socket(family, socktype, proto)

                    #Set Keepalives
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                except socket.error, msg:
                    print('Socket Error: %s' % msg)
                    sock = None
                    continue

                #Wrap in ssl if asked
                if self.SSL:
                    print('Starting SSL')
                    try:
                        ctx = SSL.Context(SSL.SSLv23_METHOD)
                        sock = SSL.Connection(ctx, sock)
                    except SSL.Error, err:
                        print('Could not Initiate SSL: %s' % err)
                        sock = None
                        continue

                #Try to establish the connection
                try:
                    print('Trying Connect(%s)' % repr(sockaddr))
                    sock.settimeout(10)
                    sock.connect(sockaddr)
                except socket.error, msg:
                    print('Socket Error: %s' % msg)
                    if self.SSL:
                        sock.shutdown()
                    sock.close()
                    sock = None
                    continue
                break
        except Exception as e:
            print('Some unknown exception: %s' % e)

        #After all the connection attempts and sock is still none lets bomb out
        if sock is None:
            print('Could not open connection')
            return False

        #Set the socket to non_blocking
        sock.setblocking(0)

        print("Connection Open.")
        self._socket = sock
        return True

    #Start up the read and write threads
    def run(self):
        #Fire off some greenlits to handing reading and writing
        try:
            print("Starting Read/Write Loops")
            tasks = [gevent.spawn(raise_exceptions(self._read)),
                     gevent.spawn(raise_exceptions(self._write))]
            #Wait for a socket exception and raise the flag
            select.select([], [], [self._socket])  # Yield
            raise self.SocketError('Socket Exception')
        finally:  # Make sure we kill the tasks
            print("Killing read and write loops")
            gevent.killall(tasks)

    def close(self):
        if self.SSL:
            try:
                self._socket.shutdown()
            except:
                pass
        self._socket.close()
        self._socket = None

    #Read from the socket, split out lines into a queue for readline
    def _read(self):
        eof = False
        while True:
            try:
                #Wait for when the socket is ready for read
                select.select([self._socket], [], [])  # Yield
                data = self._socket.recv(4096)
                if not data:  # Disconnected Remote
                    eof = True
                self._buffer.readbuffer.extend(data)
            except SSL.WantReadError:
                pass  # Nonblocking ssl yo
            except (SSL.ZeroReturnError, SSL.SysCallError):
                eof = True
            except socket.error as e:
                if e.errno == errno.EAGAIN:
                    pass  # Don't Care
                else:
                    raise

            #If there are lines to proccess do so
            while LINEENDING in self._buffer.readbuffer:
                #Find the buffer offset
                size = self._buffer.readbuffer.find(LINEENDING)
                #Get the string from the buffer
                line = self._buffer.readbuffer_mv()[0:size].tobytes()
                #Place the string the the queue for safe handling
                #Also convert it to unicode
                self._IN.put(line)
                #Delete the line from the buffer + 2 for line endings
                del self._buffer.readbuffer[0:size + 2]

            # Make sure we parse our readbuffer before we return
            if eof:  # You would think reading from a disconnected socket would
                     # raise an excaption
                raise self.SocketError('EOF')

    #Read Operation (Block)
    @utf8Decode.returnValue
    def readline(self):
        return self._IN.get()

    #Write Operation
    def _write(self):
        while True:
            line = self._OUT.get()  # Yield Operation
            self._buffer.writebuffer.extend(line + LINEENDING)

            #If we have buffers to write lets write them all
            while self._buffer.writebuffer:
                try:
                    gevent.sleep(0)  # This gets tight sometimes
                    #Try to dump 4096 bytes to the socket
                    count = self._socket.send(
                        self._buffer.writebuffer_mv()[0:4096])
                    #Remove sent len from buffer
                    del self._buffer.writebuffer[0:count]
                except SSL.WantReadError:
                    gevent.sleep(0)  # Yield so this is not tight
                except socket.error as e:
                    if e.errno == errno.EPIPE:
                        raise self.SocketError('Broken Pipe')
                    else:
                        raise self.SocketError('Err Socket Code: ' + e.errno)
                except SSL.SysCallError as (errnum, errstr):
                    if errnum == errno.EPIPE:
                        raise self.SocketError(errstr)
                    else:
                        raise self.SocketError('SSL Syscall (%d) Error: %s'
                                               % (errnum, errstr))

    #writeline Operation [Blocking]
    @utf8Encode
    def writeline(self, data):
        self._OUT.put(data)

########NEW FILE########
__FILENAME__ = nickserv
#!/usr/bin/env python
#
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from .components import component_class, observes


@component_class('nickserv')
class Nickserv(object):
    """ track channels and stuff """
    def __init__(self, irc_c, config):
        self.config = config
        self.password = config.password

    @observes('IRC_ONCONNECT')
    def AUTO_IDENTIFY(self, irc_c):
        if irc_c.config.debug:
            return
        self.identify(irc_c)

        #Spawn off a watcher that makes sure we have the nick we want
        irc_c.timers.clear('nickserv', self.watcher)
        irc_c.timers.set('nickserv', self.watcher, every=90)

    def watcher(self, irc_c, timertext):
        if irc_c.botnick != irc_c.config.irc.nick:
            self.identify(irc_c)

    def identify(self, irc_c):
        if irc_c.botnick != irc_c.config.irc.nick:
            print("TRYING TO GET MY NICK BACK")
            irc_c.PRIVMSG('nickserv', 'GHOST %s %s' % (irc_c.config.irc.nick,
                                                       self.password))
            irc_c.NICK(irc_c.config.irc.nick)

        #Identify
        print("Identifying with nickserv")
        irc_c.PRIVMSG('nickserv', 'IDENTIFY %s' % self.password)

########NEW FILE########
__FILENAME__ = plugins
#!/usr/bin/env python
#
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import inspect

from .components import *

#Use this as an indicator of a class to inspect later
CLASS_MARKER = '_PYAIB_PLUGIN'


def plugin_class(cls):
    """
        Let the component loader know to load this class
        If they pass a string argument to the decorator use it as a context
        name for the instance
    """
    if isinstance(cls, basestring):
        context = cls

        def wrapper(cls):
            setattr(cls, CLASS_MARKER, context)
            return cls
        return wrapper

    elif inspect.isclass(cls):
        setattr(cls, CLASS_MARKER, True)
        return cls

plugin_class.requires = component_class.requires


@component_class('plugins')
@component_class.requires('triggers')
class PluginManager(ComponentManager):
    def __init__(self, context, config):
        ComponentManager.__init__(self, context, config)

        #Load all configured plugins
        self.load_configured()

    def load(self, name):
        #Pull from the global config
        basename = name.split('.').pop()
        config = self.context.config.setdefault("plugin.%s" % basename, {})
        print("Loading Plugin %s..." % name)
        ns = self._process_component(name, self.config.base, CLASS_MARKER,
                                     self.context, config)
        self._loaded_components["plugin.%s" % basename].set(ns)

########NEW FILE########
__FILENAME__ = timers
#!/usr/bin/env python
#
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
import time

#TODO Look into replacing timers with some kind of gevent construct


class Timers(object):
    """ A Timers Handler """
    def __init__(self, context):
        self.__timers = []

    def __call__(self, irc_c):
        for timer in self.__timers:
            timer(time.time(), irc_c)
            if not timer:
                self.__timers.remove(timer)

    #Returns the timer
    def set(self, *args, **keywargs):
        timer = Timer(*args, **keywargs)
        if timer:
            self.__timers.append(timer)
        return bool(timer)

    def reset(self, message, callable):
        for timer in self.__timers:
            if timer.message == message and timer.callable == callable:
                if timer.every:
                    timer.at = time.time() + timer.every
                else:
                    self.__timers.remove(timer)

    def clear(self, message, callable):
        for timer in self.__timers:
            if timer.message == message and timer.callable == callable:
                self.__timers.remove(timer)

    def __len__(self):
        return len(self.__timers)


class Timer(object):
    """A Single Timer"""
    # message = Message That gets passed to the callable
    # at = Time when trigger will ring
    # every = How long to push the 'at' time after timer rings
    # count = Number of times the timer will fire before clearing
    # callable = a callable object
    def __init__(self, message, callable, at=None, every=None, count=None):
        self.expired = False
        self.message = message
        if at is None:
            self.at = time.time()
            if every:
                self.at += every
        else:
            self.at = at
        self.count = count
        self.every = every
        if isinstance(callable, collections.Callable):
            self.callable = callable
        else:
            print('Timer Error: %s not callable' % repr(callable))
            self.expired = True

    def __bool__(self):
        return self.expired is False

    __nonzero__ = __bool__

    #Ring Check
    def __call__(self, timestamp, irc_c):
        if not isinstance(self.callable, collections.Callable):
            print('Timer Error: (%r:%r) not callable'
                  % (self.message, callable))
            return

        if not self:  # Sanity test for expired alarms
            return

        if timestamp >= self.at:
            #Throw it into a greenlit
            irc_c.bot_greenlets.spawn(self.callable, irc_c, self.message)

            #Reset the timer
            if self.every:
                self.at = time.time() + self.every
                if self.count:
                    if self.count <= 1:
                        self.expired = True
                    else:
                        self.count -= 1
            else:
                self.expired = True

########NEW FILE########
__FILENAME__ = triggers
#!/usr/bin/env python
#
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import re
from .events import Events
from .components import component_class, observes, keyword


@component_class
class Triggers(Events):
    """ Handle Trigger Words """
    def __init__(self, irc_c, config):
        Events.__init__(self, irc_c)

        self.prefix = config.prefix or '!'

        #Install self in context
        irc_c['triggers'] = self

        #How to parse trigger arguments
        self._keywordRE = re.compile(r'^--?([a-z]\w*)(?:\s*(=))?\s*(.*)$',
                                     re.I)
        self._argRE = re.compile(r"""^(?:(['"])((?:\\\1|.)*?)\1"""
                                 r"""|(\S+))\s*(.*)$""")
        print("Triggers Loaded")

    def _generate_command_words(self, commands, msg):
        """
            Generate an array of arrays, of command words
            Length of each array, is max irc messages length
        """
        def _size(alist):
            size = 0
            for words in alist:
                for word in words:
                    size += len(word) + 2  # Room for formating
            return size

            #Smarter Line Wrap
        messages = [['Command List:']]  # List of commands to send
        prefix_len = len('PRVMSG %s :' % msg.nick)
        for word in sorted(commands):
            show = False
            event_handler = self.get(word)
            if event_handler:
                for observer in event_handler.observers():
                    if observer.__doc__:
                        show = True
                        break
            if show:  # Hidden Commands Stay Hidden
                if _size(messages[-1]) + len(word) + prefix_len <= 510:
                    messages[-1].append(word)
                else:
                    messages.append([word])
        return messages

    def _clean_doc(self, doc):
        """ Cleanup Multi-line Doc Strings """
        return ' '.join([s.strip() for s in doc.strip().split('\n')])

    def _generate_long_help(self, commands, msg):
        for k in sorted(commands):
            event_handler = self.get(k)
            if event_handler:
                for observer in event_handler.observers():
                    if observer.__doc__:
                        doc = self._clean_doc(observer.__doc__)
                        if hasattr(observer, '_subs'):
                            for sub in observer._subs:
                                msg.reply("%s %s %s"
                                          % (k, sub, doc))
                        else:
                            msg.reply("%s %s" % (k, doc))

    @keyword('help')
    @keyword.autohelp
    def autohelp(self, irc_c, msg, trigger, args, kargs):
        """[<command>]+ [--list|--full] :: get docs"""
        if args:
            commands = args
        else:
            commands = self.list()

        if msg.channel and not args:  # Was this issued in channel without args
            #Force short mode
            if 'full' in kargs:  # If you ask for full we send your the list
                msg.reply_target = msg.nick
            else:
                kargs['list'] = True

        if 'list' in kargs and 'full' not in kargs:
            messages = self._generate_command_words(commands, msg)
            for words in messages:
                msg.reply('%s' % ' '.join(words))
        else:
            self._generate_long_help(commands, msg)

    def parse(self, next):
        """ Take a string of arguments and parse them into args and kwargs """
        args = []
        kwargs = {}
        while next:
            getnext = None
            keymatch = self._keywordRE.search(next)
            if keymatch:
                name, getnext, next = keymatch.groups()
                kwargs[name] = True
                if not getnext:  # So keywords don't get lost
                    continue

            argmatch = self._argRE.search(next)
            if argmatch:
                quotetype, quoted, naked, next = argmatch.groups()
                #Could be a empty string
                arg = quoted if quoted is not None else naked
                #Get rid of any escaped strings
                arg = re.sub(r"""\\(['"])""", r'\1', arg)
                if getnext:
                    kwargs[name] = arg
                else:
                    args.append(arg)
        return [args, kwargs]

    #Just privmsg, rfc forbids automatic responces to notice
    @observes('IRC_MSG_PRIVMSG')
    def _handler(self, irc_c, msg):
        #Addressed Keywords like '<botnick>: keyword'
        address = '%s:' % irc_c.botnick

        #Cleanup the message for parsing
        message = msg.message.strip()
        if (message.startswith(self.prefix)
                or message.lower().startswith(address)
                or msg.channel is None):
            #Lets strip directed addressed messages
            if message.lower().startswith(address):
                message = message[len(address):].strip()

            #Get the trigger and everything else
            parts = message.split(None, 1)
            if parts:
                word = parts.pop(0).lstrip(self.prefix)
            else:
                #WTF empty screw it
                return

            #Try to get the args
            if parts:
                allargs = parts.pop(0)
            else:
                allargs = ''  # Empty NO ARGS provided

            #Get the trigger if it exists
            trigger = self.get(word)

            if trigger:
                args, keywords = self.parse(allargs)
                #Call the trigger with parsed args
                msg.unparsed = allargs
                trigger(irc_c, msg, word, args, keywords)

########NEW FILE########
__FILENAME__ = data
#!/usr/bin/env python
#
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import weakref


class Raw(object):
    """Wrapper to tell Object not to rewrap but just store the value"""
    def __init__(self, value):
        self.value = value

#A Sentinel value because None is a valid value
sentinel = object()


class Object(dict):
    """
        Pretty DataStructure Objects with lots of magic
        All Collections added to this object will be converted to
        data.Collection if they are not already and instance of that type

        All Dicts added to this class will be converted to data.Object's if
        they are not currently instances of data.Object

        To prevent any conversions from taking place in a value place in a
        data.Object use data.Raw(myobject) to tell data.Object to store it
        as is.

    """
    #dir(self) causes these to be getattr'ed
    #Its a weird python artifact
    __members__ = None
    __methods__ = None

    def __init__(self, *args, **kwargs):
        #Look to see if this object should be somebodies child once not empty
        if kwargs.get('__PARENT__'):
            self.__dict__['__PARENT__'] = kwargs.pop('__PARENT__')
        super(Object, self).__init__(*args, **kwargs)
        #A place to store future children before they are actually children
        self.__dict__['__CACHE__'] = weakref.WeakValueDictionary()
        #Read Only Keys
        self.__dict__['__PROTECTED__'] = set()
        #Make sure all children are Object not dict
        #Also handle 'a.b.c' style keys
        for k in self.keys():
            self[k] = self.pop(k)

    def __wrap(self, value):
        if isinstance(value, (tuple, set, frozenset)):
            return type(value)([self.__wrap(v) for v in value])
        elif isinstance(value, list) and not isinstance(value, Collection):
            return Collection(value, self.__class__)
        elif isinstance(value, Object):
            return value  # Don't Rewrap if already this class.
        elif isinstance(value, Raw):
            return value.value
        elif isinstance(value, dict):
            if isinstance(self, CaseInsensitiveObject):
                return CaseInsensitiveObject(value)
            else:
                return Object(value)
        else:
            return value

    def __protect__(self, key, value=sentinel):
        """Protected keys add its parents, not sure if useful"""
        if not isinstance(key, list):
            key = key.split('.') if isinstance(key, basestring) else [key]
        key, path = key.pop(0), key
        if len(path) > 0:
            self.get(key).protect(path, value)
        elif value is not sentinel:
            self[key] = value
        if key not in self:
            raise KeyError('key %s has no value to protect' % key)
        self.__PROTECTED__.add(key)

    #Object.key sets
    def __setattr__(self, name, value):
        bad_ids = dir(self)
        #Add some just for causion
        bad_ids.append('__call__')
        bad_ids.append('__dir__')

        if name in self.__PROTECTED__:
            raise KeyError('key %r is read only' % name)

        if name not in bad_ids:
            if self.__dict__.get('__PARENT__'):
                #Do all the black magic with making sure my parents exist
                parent, pname = self.__dict__.pop('__PARENT__')
                parent[pname] = self

            #Get rid of cached future children that match name
            if name in self.__CACHE__:
                del self.__CACHE__[name]

            dict.__setitem__(self, name, self.__wrap(value))
        else:
            print("%s is an invalid identifier" % name)
            print("identifiers can not be %r" % bad_ids)
            raise KeyError('bad identifier')

    #Object.key gets
    def __getattr__(self, key):
        return self.get(key)

    #Dict like functionality and xpath like access
    def __getitem__(self, key, default=sentinel):
        if not isinstance(key, list):
            key = key.split('.') if isinstance(key, basestring) else [key]
        key, path = key.pop(0), key
        if len(path) > 0:
            return self.get(key).__getitem__(path, default)
        elif key not in self:
            if default is sentinel:
                #Return a parentless object (this might be evil)
                #CACHE it
                return self.__CACHE__.setdefault(
                    key, self.__class__(__PARENT__=(self, key)))
            else:
                return default
        else:
            return dict.get(self, key)

    get = __getitem__

    def __contains__(self, key):
        """ contains method with key paths support """
        if not isinstance(key, list):
            key = key.split('.') if isinstance(key, basestring) else [key]
        this, next = key.pop(0), key
        if this in self.iterkeys():
            if len(next) > 0:
                return next in self.get(this)
            else:
                return True
        else:
            return False

    has_key = __contains__

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self.get(key)

    #Allow address keys 'key.key.key'
    def __setitem__(self, key, value):
        if not isinstance(key, list):
            key = key.split('.') if isinstance(key, basestring) else [key]
        key, path = key.pop(0), key
        if len(path) > 0:
            self.setdefault(key, {}).__setitem__(path, value)
        else:
            self.__setattr__(key, value)

    set = __setitem__

    #Allow del by 'key.key.key'
    def __delitem__(self, key):
        if not isinstance(key, list):
            key = key.split('.') if isinstance(key, basestring) else [key]
        key, path = key.pop(0), key
        if len(path) > 0:
            self.get(key).__delitem__(path)  # Pass the delete down
        else:
            if key not in self:
                pass  # This should handle itself
            else:
                dict.__delitem__(self, key)

    __delattr__ = __delitem__


class CaseInsensitiveObject(Object):
    """A Case Insensitive Version of data.Object"""
    def __protect__(self, key, value=sentinel):
        Object.__protect__(self, key.lower(), value)

    def __getitem__(self, key, default=sentinel):
        if isinstance(key, list):
            key = [x.lower() if isinstance(x, basestring) else x for x in key]
        elif isinstance(key, basestring):
            key = key.lower()
        return Object.__getitem__(self, key, default)
    get = __getitem__

    def __setattr__(self, key, value):
        if isinstance(key, basestring):
            key = key.lower()
        return Object.__setattr__(self, key, value)

    def __contains__(self, key):
        if not isinstance(key, list):
            key = key.split('.') if isinstance(key, basestring) else [key]
        if isinstance(key[0], basestring):
            key[0] = key[0].lower()
        return Object.__contains__(self, key)

    has_key = __contains__

    def __getattr__(self, key):
        if key in self:
            return self.get(key)
        else:
            return Object.__getattr__(self, key)

    def __delattr__(self, key):
        if isinstance(key, basestring):
            key = key.lower()
        return Object.__delattr__(self, key)

    __delitem__ = __delattr__


class Collection(list):
    """Special Lists so [dicts,[dict,dict]] within get converted"""
    def __init__(self, alist=None, default=Object):
        if alist is None:
            alist = ()
        super(Collection, self).__init__(alist)
        self.__default = default
        #Makes sure all the conversions happen
        for i in xrange(0, len(self)):
            self[i] = self[i]

    def __wrap(self, value):
        if isinstance(value, dict):
            return self.__default(value)
        elif isinstance(value, self.__class__):
            return value  # Do Not Re-wrap
        elif isinstance(value, list):
            return self.__class__(value, self.__default)
        else:
            return value

    def __setitem__(self, key, value):
        super(Collection, self).__setitem__(key, self.__wrap(value))

    def __getslice__(self, s, e):
        return self.__class__(super(Collection, self).__getslice__(s, e),
                              self.__default)

    def append(self, value):
        list.append(self, self.__wrap(value))

    def extend(self, alist):
        for i in alist:
            self.append(i)

    def insert(self, key, value):
        list.insert(self, key, self.__wrap(value))

    def shift(self):
        return self.pop(0)

    def unshift(self, value):
        self.insert(0, value)

    push = append

########NEW FILE########
__FILENAME__ = decorator
#!/usr/bin/env python
#
# Copyright 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import collections
import inspect
import gevent
import functools
import copy


class EasyDecorator(object):
    """An attempt to make Decorating stuff easier"""
    _instance = None
    _thing = _othing = None

    def __init__(self, *args, **kwargs):
        """Figure how we are being called for decoration"""
        #Default to empty
        self.args = []
        self.kwargs = {}

        if len(args) == 1 and not kwargs \
           and (inspect.isclass(args[0]) or isinstance(args[0],
                                                       collections.Callable)):
            self._thing = args[0]
            self._mimic()
        else:
            # Save args so wrappers could use them
            self.args = args
            self.kwargs = kwargs

    def _mimic(self):
        """Mimic the base object so we have the same props"""
        for n in set(dir(self._thing)) - set(dir(self)):
            setattr(self, n, getattr(self._thing, n))
        #These have to happen
        self.__name__ = self._thing.__name__
        self.__doc__ = self._thing.__doc__

    def wrapper(self, *args, **kwargs):
        """Empty Wrapper: Overwride me"""
        return self.call(*args, **kwargs)

    def call(self, *args, **kwargs):
        """Call the decorated object"""
        return self._thing(*args, **kwargs)

    #Instance Methods
    def __get__(self, instance, klass):
        self._instance = instance

        #Before we bind the method lets capture the original
        if self._othing is None:
            self._othing = self._thing

        #Get a bound method from the original
        self._thing = self._othing.__get__(instance, klass)

        #Return a copy of self, for instance safety
        return copy.copy(self)

    #Functions / With args this gets the thing
    def __call__(self, *args, **kwargs):
        if self._thing:
            return self.wrapper(*args, **kwargs)
        else:
            self._thing = args[0]
            self._mimic()
            return self


def filterintree(adict, block, stype=str, history=None):
    """Execute block filter for all strings in a dict/list recusive"""
    if not adict:  # Don't go through the proccess for empty containers
        return adict
    if history is None:
        history = set()
    if id(adict) in history:
        return
    else:
        history.add(id(adict))

    if isinstance(adict, list):
        for i in xrange(len(adict)):
            if isinstance(adict[i], stype):
                adict[i] = block(adict[i])
            elif isinstance(adict[i], (set, tuple)):
                adict[i] = filterintree(adict[i], block, stype, history)
            elif isinstance(adict[i], (list, dict)):
                filterintree(adict[i], block, stype, history)
    elif isinstance(adict, (set, tuple)):
        c = list(adict)
        filterintree(c, block, stype, history)
        return type(adict)(c)
    elif isinstance(adict, dict):
        for k, v in adict.iteritems():
            if isinstance(v, stype):
                adict[k] = block(v)
            elif isinstance(v, (dict, list)):
                filterintree(v, block, stype, history)
            elif isinstance(v, (set, tuple)):
                adict[k] = filterintree(v, block, stype, history)


class utf8Decode(EasyDecorator):
    """decode all arguments to unicode strings"""
    def wrapper(self, *args, **kwargs):
        def decode(s):
            return s.decode('utf-8', 'ignore')

        args = filterintree(args, decode)
        filterintree(kwargs, decode)
        #Call Method with converted args
        return self.call(*args, **kwargs)

    class returnValue(EasyDecorator):
        """decode the return value only"""
        def wrapper(self, *args, **kwargs):
            def decode(s):
                return s.decode('utf-8', 'ignore')

            value = [self.call(*args, **kwargs)]
            filterintree(value, decode)
            return value[0]


class utf8Encode(EasyDecorator):
    """encode all unicode arguments to byte strings"""
    def wrapper(self, *args, **kwargs):
        def encode(s):
            return s.encode('utf-8', 'backslashreplace')

        args = filterintree(args, encode, stype=unicode)
        filterintree(kwargs, encode, stype=unicode)
        #Call Method with converted args
        return self.call(*args, **kwargs)

    class returnValue(EasyDecorator):
        """encode the return value"""
        def wrapper(self, *args, **kwargs):
            def encode(s):
                return s.encode('utf-8', 'backslashreplace')

            value = [self.call(*args, **kwargs)]
            filterintree(value, encode, stype=unicode)
            return value[0]


def raise_exceptions(func):
    """Wrap around for spawn to raise exceptions in current context"""
    caller = gevent.getcurrent()

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as ex:
            caller.throw(ex)

    return wrapper

########NEW FILE########
