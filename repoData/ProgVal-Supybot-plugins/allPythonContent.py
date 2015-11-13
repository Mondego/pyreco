__FILENAME__ = config
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import re
import supybot.conf as conf
import supybot.registry as registry

try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('AttackProtector')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('AttackProtector', True)

class XpY(registry.String):
    """Value must be in the format <number>p<seconds>."""
    _re = re.compile('(?P<number>[0-9]+)p(?P<seconds>[0-9]+)')
    def setValue(self, v):
        if self._re.match(v):
            registry.String.setValue(self, v)
        else:
            self.error()
try:
    XpY = internationalizeDocstring(XpY)
except TypeError:
    # Pypy
    pass

class Punishment(registry.String):
    """Value must be a valid punishment ('ban', 'kick', 'kban', 'mode+X',
    'mode-X', 'umode+X', 'umode-X', 'command XXX', ...)"""
    def set(self, s):
        if s not in ('ban', 'kick', 'kban') and not s.startswith('mode+') and \
                not s.startswith('mode-') and not s.startswith('umode-') and \
                not s.startswith('umode+') and \
                not s.startswith('mmode-') and not s.startswith('mmode-') and \
                not s.startswith('command ') and \
                not s.startswith('kban+') and not s.startswith('ban+') :
            self.error()
            return
        if s.startswith('kban+') or s.startswith('ban+'):
            try:
                int(s.split('+', 1)[1])
            except ValueError:
                self.error()
                return
        self.setValue(s)
try:
    Punishment = internationalizeDocstring(Punishment)
except TypeError:
    # Pypy
    pass

AttackProtector = conf.registerPlugin('AttackProtector')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(AttackProtector, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))

conf.registerChannelValue(AttackProtector, 'enable',
    registry.Boolean(True, _("""Determines whether or not AttackProtector
    is enabled on this channel.""")))
conf.registerGlobalValue(AttackProtector, 'exempt',
    registry.String('nopunish', _("""If a user has this capability, he won't be
        punished by AttackProtector""")))
conf.registerGlobalValue(AttackProtector, 'kickmessage',
    registry.String(_('$kind flood detected'), _("""The kick message used
    when a user abuses the channel. $kind will be replaced with the kind
    of attack.""")))
conf.registerGlobalValue(AttackProtector, 'delay',
    registry.Integer(10, _("""Determines how long (in seconds) the plugin will
    wait before being enabled. A too low value makes the bot believe that
    its incoming messages 'flood' on connection is an attack.""")))

kinds = {'join': ['5p10', 'ban', ''],
         'knock': ['5p20', 'mode+K', ''],
         'part': ['4p5', 'ban', ''],
         'nick': ['7p300', 'ban', ''],
         'message': ['10p20', 'kick', ''],
         'kicked': ['5p60', 'kban', _('user has been kicked multiple times')],
         'groupjoin': ['20p10', 'mode+i', ''],
         'groupknock': ['7p20', 'mode+K', ''],
         'grouppart': ['20p10', 'mode+i', ''],
         'groupnick': ['20p10', 'mode+N', ''],
         'groupmessage': ['20p20', 'mode+m', '']}
for kind, data in kinds.items():
    detection, punishment, help_ = data
    help_ = help_ or (_('a %s flood is detected') % kind)
    conf.registerGroup(AttackProtector, kind)
    conf.registerChannelValue(getattr(AttackProtector, kind), 'detection',
        XpY(detection, _("""In the format XpY, where X is the number of %s per
        Y seconds that triggers the punishment.""") % kind))
    conf.registerChannelValue(getattr(AttackProtector, kind), 'punishment',
        Punishment(punishment, _("""Determines the punishment applied when
        %s.""") % help_))
    conf.registerChannelValue(getattr(AttackProtector, kind), 'kickmessage',
        registry.String('', _("""The kick message used
        when a user abuses the channel with this kind of flood. If empty,
        defaults to supybot.plugins.AttackProtector.kickmessage.""")))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import re
import time
import functools

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.schedule as schedule
import supybot.registry as registry
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('AttackProtector')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

filterParser=re.compile('(?P<number>[0-9]+)p(?P<seconds>[0-9]+)')

class AttackProtectorDatabaseItem:
    def __init__(self, kind, prefix, channel, protector, irc, msg):
        self.kind = kind
        self.prefix = prefix
        self.channel = channel
        self.time = time.time()
        self.protector = protector
        value = protector.registryValue('%s.detection' % kind, channel)
        self.irc = irc
        self.msg = msg
        parsed = filterParser.match(value)
        self.expire = self.time + int(parsed.group('seconds'))

class AttackProtectorDatabase:
    def __init__(self):
        self._collections = {}

    def add(self, item):
        if item.kind not in self._collections:
            self._collections.update({item.kind: []})
        self._collections[item.kind].append(item)
        self.refresh()
        self.detectAttack(item)

    def refresh(self):
        currentTime = time.time() # Caching
        for kind in self._collections:
            collection = self._collections[kind]
            for item in collection:
                if item.expire < currentTime:
                    collection.remove(item)

    def detectAttack(self, lastItem):
        collection = self._collections[lastItem.kind]
        prefix = lastItem.prefix
        channel = lastItem.channel
        protector = lastItem.protector
        kind = lastItem.kind
        count = 0

        for item in collection:
            if item.prefix == prefix and item.channel == channel:
                count += 1
        detection = protector.registryValue(kind + '.detection', channel)
        if count >= int(filterParser.match(detection).group('number')):
            protector._slot(lastItem)
            for index, item in enumerate(collection):
                if item.prefix == prefix and item.channel == channel:
                    collection.pop(index)


class AttackProtector(callbacks.Plugin):
    """This plugin protects channels against spam and flood"""

    noIgnore = True

    def __init__(self, irc):
        self.__parent = super(AttackProtector, self)
        self.__parent.__init__(irc)
        self._enableOn = time.time() + self.registryValue('delay')
        self._database = AttackProtectorDatabase()

    def _eventCatcher(self, irc, msg, kind, **kwargs):
        if kind in ['part', 'join', 'message']:
            channels = [msg.args[0]]
            prefix = msg.prefix
        elif kind in ['knock']:
            channels = [msg.args[0]]
            prefix = msg.args[2]
        elif kind in ['nick']:
            newNick = msg.args[0]
            channels = []
            for (channel, c) in irc.state.channels.items():
                if newNick in c.users:
                    channels.append(channel)
            prefix = '*!' + msg.prefix.split('!')[1]
        elif kind in ['kicked']:
            assert 'kicked_prefix' in kwargs
            channel = msg.args[0]
            channels = [channel]
            prefix = kwargs['kicked_prefix']
        try:
            for channel in channels:
                item = None
                if not self.registryValue('%s.detection' % kind, channel) == \
                '0p0':
                    item = AttackProtectorDatabaseItem(kind, prefix, channel,
                                                       self, irc, msg)
                    self._database.add(item)

                try:
                    if not self.registryValue('group%s.detection' % kind,
                        channel) == '0p0':
                        item = AttackProtectorDatabaseItem('group%s' % kind,
                                                            '*!*@*', channel,
                                                            self, irc, msg)
                        self._database.add(item)
                except registry.NonExistentRegistryEntry:
                    pass
        except UnboundLocalError:
            pass

    def doJoin(self, irc, msg):
        self._eventCatcher(irc, msg, 'join')
    def do710(self, irc, msg):
        self._eventCatcher(irc, msg, 'knock')
    def doPart(self, irc, msg):
        self._eventCatcher(irc, msg, 'part')
    def doNick(self, irc, msg):
        self._eventCatcher(irc, msg, 'nick')
    def doPrivmsg(self, irc, msg):
        self._eventCatcher(irc, msg, 'message')
    def doNotice(self, irc, msg):
        self._eventCatcher(irc, msg, 'message')

    def _slot(self, lastItem):
        irc = lastItem.irc
        msg = lastItem.msg
        channel = lastItem.channel
        prefix = lastItem.prefix
        nick = prefix.split('!')[0]
        kind = lastItem.kind

        if not ircutils.isChannel(channel):
                return
        if not self.registryValue('enable', channel):
            return

        try:
            ircdb.users.getUser(msg.prefix) # May raise KeyError
            capability = self.registryValue('exempt')
            if capability:
                if ircdb.checkCapability(msg.prefix,
                        ','.join([channel, capability])):
                    self.log.info('Not punishing %s: they are immune.' %
                            prefix)
                    return
        except KeyError:
            pass
        punishment = self.registryValue('%s.punishment' % kind, channel)
        reason = self.registryValue('%s.kickmessage' % kind, channel)
        if not reason:
            reason = self.registryValue('kickmessage').replace('$kind', kind)

        if punishment == 'kick':
            self._eventCatcher(irc, msg, 'kicked', kicked_prefix=prefix)
        if kind == 'kicked':
            reason = _('You exceeded your kick quota.')

        banmaskstyle = conf.supybot.protocols.irc.banmask
        banmask = banmaskstyle.makeBanmask(prefix)
        if punishment == 'kick':
            msg = ircmsgs.kick(channel, nick, reason)
            irc.queueMsg(msg)
        elif punishment.startswith('ban'):
            msg = ircmsgs.ban(channel, banmask)
            irc.queueMsg(msg)

            if punishment.startswith('ban+'):
                delay = int(punishment[4:])
                unban = functools.partial(irc.queueMsg,
                        ircmsgs.unban(channel, banmask))
                schedule.addEvent(unban, delay + time.time())

        elif punishment.startswith('kban'):
            msg = ircmsgs.ban(channel, banmask)
            irc.queueMsg(msg)
            msg = ircmsgs.kick(channel, nick, reason)
            irc.queueMsg(msg)

            if punishment.startswith('kban+'):
                delay = int(punishment[5:])
                unban = functools.partial(irc.queueMsg,
                        ircmsgs.unban(channel, banmask))
                schedule.addEvent(unban, delay + time.time())

        elif punishment.startswith('mode'):
            msg = ircmsgs.mode(channel, punishment[len('mode'):])
            irc.queueMsg(msg)
        elif punishment.startswith('umode'):
            msg = ircmsgs.mode(channel, (punishment[len('umode'):], msg.nick))
            irc.queueMsg(msg)
        elif punishment.startswith('mmode'):
            msg = ircmsgs.mode(channel, (punishment[len('mmode'):], banmask))
            irc.queueMsg(msg)
        elif punishment.startswith('command '):
            tokens = callbacks.tokenize(punishment[len('command '):])
            self.Proxy(irc, msg, tokens)
AttackProtector = internationalizeDocstring(AttackProtector)


Class = AttackProtector


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import time
from supybot.test import *
import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.schedule as schedule

class AttackProtectorTestCase(ChannelPluginTestCase):
    plugins = ('AttackProtector', 'Config', 'Utilities', 'User')
    config = {'supybot.plugins.AttackProtector.join.detection': '5p2',
              'supybot.plugins.AttackProtector.part.punishment':
              'command echo hi !'}

    #################################
    # Utilities
    def _getIfAnswerIsEqual(self, msg):
        m = self.irc.takeMsg()
        while m is not None:
            if repr(m) == repr(msg):
                return True
            m = self.irc.takeMsg()
        return False
    def _getIfAnswerIsThisBan(self, banmask=None):
        if banmask is None:
            banmask = '*!' + (self.prefix.split('!')[1])
        return self._getIfAnswerIsEqual(ircmsgs.ban(self.channel, banmask))
    def _getIfAnswerIsThisKick(self, kind):
        reason = '%s flood detected' % kind
        return self._getIfAnswerIsEqual(ircmsgs.kick(self.channel, self.nick,
                                                 reason))
    def _getIfAnswerIsMode(self, mode):
        return self._getIfAnswerIsEqual(ircmsgs.IrcMsg(prefix="", command="MODE",
            args=(self.channel, mode)))

    #################################
    # Join tests
    def testPunishJoinFlood(self):
        for i in range(1, 5):
            msg = ircmsgs.join(self.channel, prefix=self.prefix)
            self.irc.feedMsg(msg)
        self.failIf(self._getIfAnswerIsThisBan() == False,
                    'No reaction to join flood.')
    def testPunishNotNoJoinFlood(self):
        for i in range(1, 4):
            msg = ircmsgs.join(self.channel, prefix=self.prefix)
            self.irc.feedMsg(msg)
        self.failIf(self._getIfAnswerIsThisBan(),
                    'Reaction to no join flood.')

    #################################
    # GroupJoin tests
    def testPunishGroupJoinFlood(self):
        for i in range(1, 20):
            prefix = self.prefix.split('@')
            prefix = '@'.join(['%s%i' % (prefix[0], i), prefix[1]])
            msg = ircmsgs.join(self.channel, prefix=prefix)
            self.irc.feedMsg(msg)
        self.failIf(self._getIfAnswerIsMode('+i') == False,
                    'No reaction to groupjoin flood.')
    def testPunishNotNoGroupJoinFlood(self):
        for i in range(1, 19):
            prefix = self.prefix.split('@')
            prefix = '@'.join(['%s%i' % (prefix[0], i), prefix[1]])
            msg = ircmsgs.join(self.channel, prefix=prefix)
            self.irc.feedMsg(msg)
        self.failIf(self._getIfAnswerIsMode('+i'),
                    'Reaction to no groupjoin flood.')

    #################################
    # Part tests
    def testPunishPartFlood(self):
        for i in range(1, 5):
            msg = ircmsgs.part(self.channel, prefix=self.prefix)
            self.irc.feedMsg(msg)
        msg = ircmsgs.privmsg(self.channel, 'hi !')
        self.failIf(self._getIfAnswerIsEqual(msg) == False,
                    'No reaction to part flood.')
    def testPunishNotNoPartFlood(self):
        for i in range(1, 4):
            msg = ircmsgs.part(self.channel, prefix=self.prefix)
            self.irc.feedMsg(msg)
        msg = ircmsgs.privmsg(self.channel, 'hi !')
        self.failIf(self._getIfAnswerIsEqual(msg),
                    'Reaction to no part flood.')

    #################################
    # Nick tests
    def testPunishNickFlood(self):
        for nick in 'ABCDEFG':
            msg = ircmsgs.nick(nick, prefix=self.prefix)
            self.irc.feedMsg(msg)
            self.prefix = nick + '!' + self.prefix.split('!')[1]
        banmask = '*!' + self.prefix.split('!')[1]
        self.failIf(self._getIfAnswerIsThisBan(banmask) == False,
                    'No reaction to nick flood.')
    def testPunishNotNoNickFlood(self):
        for nick in 'ABCDEF':
            msg = ircmsgs.nick(nick, prefix=self.prefix)
            self.irc.feedMsg(msg)
            self.prefix = nick + '!' + self.prefix.split('!')[1]
        banmask = '*!' + self.prefix.split('!')[1]
        self.failIf(self._getIfAnswerIsThisBan(banmask),
                    'Reaction to no nick flood.')

    #################################
    # Message tests
    def testPunishMessageFlood(self):
        for i in range(1, 11):
            msg = ircmsgs.privmsg(self.channel, 'Hi, this is a flood',
                                  prefix=self.prefix)
            self.irc.feedMsg(msg)
        self.failIf(self._getIfAnswerIsThisKick('message') == False,
                    'No reaction to privmsg flood.')
    def testPunishNoticeFlood(self):
        for i in range(1, 11):
            msg = ircmsgs.notice(self.channel, 'Hi, this is a flood',
                                  prefix=self.prefix)
            self.irc.feedMsg(msg)
        self.failIf(self._getIfAnswerIsThisKick('message') == False,
                    'No reaction to notice flood.')
    def testPunishNotNoMessageFlood(self):
        for i in range(1, 10):
            msg = ircmsgs.privmsg(self.channel, 'Hi, this is a flood',
                                  prefix=self.prefix)
            self.irc.feedMsg(msg)
        self.failIf(self._getIfAnswerIsThisKick('message'),
                   'Reaction to no privmsg flood.')
    def testPunishNotNoNoticeFlood(self):
        for i in range(1, 10):
            msg = ircmsgs.notice(self.channel, 'Hi, this is a flood',
                                  prefix=self.prefix)
            self.irc.feedMsg(msg)
        self.failIf(self._getIfAnswerIsThisKick('message'),
                   'Reaction to no notice flood.')
    def testPunishNoticeFlood(self):
        for i in range(1, 6):
            msg = ircmsgs.notice(self.channel, 'Hi, this is a flood',
                                  prefix=self.prefix)
            self.irc.feedMsg(msg)
            msg = ircmsgs.privmsg(self.channel, 'Hi, this is a flood',
                                  prefix=self.prefix)
            self.irc.feedMsg(msg)
        self.failIf(self._getIfAnswerIsThisKick('message') == False,
                    'No reaction to both notice and privmsg flood.')

    #################################
    # Test trusted users
    def testDoesNotPunishTrustedUsers(self):
        feedMsg = PluginTestCase.feedMsg
        feedMsg(self, 'register toto foobarbaz')
        feedMsg(self, 'identify toto foobarbaz')
        [self.irc.takeMsg() for x in 'xx']
        self.assertNotError('eval '
                '''"ircdb.users.getUser(1).capabilities.add('nopunish')"''')
        self.assertResponse('capabilities', '[nopunish]')

        try:
            for i in range(1, 5):
                msg = ircmsgs.join(self.channel, prefix=self.prefix)
                self.irc.feedMsg(msg)
            self.failIf(self._getIfAnswerIsThisBan(), 'Punishes trusted user')
        finally:
            feedMsg(self, 'hostmask remove toto %s' % self.prefix)
            feedMsg(self, 'unidentify') # Otherwise, other tests would fail
            [self.irc.takeMsg() for x in 'xx']
            self.assertNotRegexp('whoami', 'toto')
            self.assertError('capabilities')

    #################################
    # Test punishments

    def testDisable(self):
        for i in range(1, 11):
            msg = ircmsgs.privmsg(self.channel, 'Hi, this is a flood',
                                  prefix=self.prefix)
            self.irc.feedMsg(msg)
        self.assertNotError('config plugins.AttackProtector.message.punishment '
                'umode+b')
        return self._getIfAnswerIsEqual(ircmsgs.IrcMsg(prefix="", command="MODE",
            args=(self.channel, mode, self.nick)))

    def testKban(self):
        def run_schedule():
            while schedule.schedule.schedule:
                schedule.run()
        with conf.supybot.plugins.AttackProtector.message.punishment.context(
                'kban+2'):
            for i in range(1, 11):
                msg = ircmsgs.privmsg(self.channel, 'Hi, this is a flood',
                                      prefix=self.prefix)
                self.irc.feedMsg(msg)
            m = self.irc.takeMsg()
            self.assertEqual(m.command, 'MODE')
            m = self.irc.takeMsg()
            self.assertEqual(m.command, 'KICK')
            self.assertEqual(self.irc.takeMsg(), None)
            threading.Thread(target=run_schedule).start()
            self.assertEqual(self.irc.takeMsg(), None)
            time.sleep(1)
            self.assertEqual(self.irc.takeMsg(), None)
            time.sleep(2)
            m = self.irc.takeMsg()
            self.assertEqual(m.command, 'MODE')
        schedule.schedule.schedule = False

    #################################
    # 'Kicked' tests
    def testKbanAfterKicks(self):
        prefix = 'testing!Attack@Protector'
        self.assertNotError('config plugins.AttackProtector.groupmessage.detection 100p10')
        for i in range(1, 5):
            for i in range(1, 11):
                msg = ircmsgs.privmsg(self.channel, 'Hi, this is a flood',
                                      prefix=prefix)
                self.irc.feedMsg(msg)
            m = self.irc.takeMsg()
            self.assertEqual(m.command, 'KICK')
        for i in range(1, 11):
            msg = ircmsgs.privmsg(self.channel, 'Hi, this is a flood',
                                  prefix=prefix)
            self.irc.feedMsg(msg)
        self.assertEqual(self.irc.takeMsg().command, 'MODE')

    #################################
    # Global tests
    def testCleanCollection(self):
        for i in range(1, 4):
            self.irc.feedMsg(ircmsgs.join(self.channel, prefix=self.prefix))
        time.sleep(3)
        self.irc.feedMsg(ircmsgs.join(self.channel, prefix=self.prefix))
        self.failIf(self._getIfAnswerIsThisBan(),
                    'Doesn\'t clean the join collection.')

    def testDontCleanCollectionToEarly(self):
        for i in range(1, 4):
            self.irc.feedMsg(ircmsgs.join(self.channel, prefix=self.prefix))
        time.sleep(1)
        self.irc.feedMsg(ircmsgs.join(self.channel, prefix=self.prefix))
        self.failIf(self._getIfAnswerIsThisBan() == False,
                    'Cleans the collection before it should be cleaned')

    def testCleanCollectionAfterPunishment(self):
        for i in range(1, 6):
            self.irc.feedMsg(ircmsgs.join(self.channel, prefix=self.prefix))
        self._getIfAnswerIsThisBan()
        self.irc.feedMsg(ircmsgs.join(self.channel, prefix=self.prefix))
        self.failIf(self._getIfAnswerIsThisBan(),
                    'Doesn\'t clean the join collection after having banned.')

    def testDisable(self):
        for i in range(1, 11):
            msg = ircmsgs.privmsg(self.channel, 'Hi, this is a flood',
                                  prefix=self.prefix)
            self.irc.feedMsg(msg)
        self.assertNotError('config plugin.AttackProtector.enable False')
        self.failIf(self._getIfAnswerIsThisKick('message'),
                    'Punishment even if disabled')



# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('AutoTrans')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('AutoTrans', True)


AutoTrans = conf.registerPlugin('AutoTrans')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(AutoTrans, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))

conf.registerChannelValue(AutoTrans, 'queries',
    registry.SpaceSeparatedListOfStrings([], _("""A list of people who
    want to have a translated version of messages in a channel if the
    messages are not in their native language.
    Format: nick1:lang1 nick2:lang2.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import json
import operator
try:
    from urllib import quote
except:
    from urllib.request import quote

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('AutoTrans')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

class AutoTrans(callbacks.Plugin):
    """Add the help for "@plugin help AutoTrans" here
    This should describe *how* to use this plugin."""
    threaded = True

    def doPrivmsg(self, irc, msg):
        channel = msg.args[0]
        conf = list(map(lambda x:x.split(':'),
            self.registryValue('queries', channel)))

        headers = utils.web.defaultHeaders
        headers['User-Agent'] = ('Mozilla/5.0 (X11; U; Linux i686) '
                                 'Gecko/20071127 Firefox/2.0.0.11')

        origin_text = quote(msg.args[1])

        
        for lang in set(map(operator.itemgetter(1), conf)):
            result = utils.web.getUrlFd('http://translate.google.com/translate_a/t'
                                        '?client=t&hl=en&sl=auto&tl=%s&multires=1'
                                        '&otf=1&ssel=0&tsel=0&uptl=%s&sc=1&text='
                                        '%s' % (lang, lang, origin_text),
                                        headers).read().decode('utf8')

            while ',,' in result:
                result = result.replace(',,', ',null,')
            data = json.loads(result)

            try:
                language = data[2]
            except:
                language = 'unknown'

            text = ''.join(x[0] for x in data[0])
            text = '<%s@%s> %s' % (msg.nick, channel, text)
            for (nick, user_lang) in conf:
                if user_lang != language and user_lang == lang:
                    irc.reply(text, to=nick, private=True)


Class = AutoTrans


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *
import supybot.conf as conf

class AutoTransTestCase(ChannelPluginTestCase):
    plugins = ('AutoTrans',)

    if network:
        def testTranslate(self):
            def feedMsg(msg):
                return self._feedMsg(msg, usePrefixChar=False)
            self.assertNotError('config channel plugins.AutoTrans.queries '
                    'foo:en bar:de')
            while self.irc.takeMsg():
                pass
            m = feedMsg('This is a test')
            self.assertEqual(m.command, 'PRIVMSG', m)
            self.assertEqual(m.args[0], 'bar', m)
            self.assertEqual(m.args[1], '<test@#test> Dies ist ein Test', m)

            self.assertEqual(self.irc.takeMsg(), None)

            m = feedMsg('Dies ist ein Test')
            self.assertEqual(m.command, 'PRIVMSG', m)
            self.assertEqual(m.args[0], 'foo', m)
            self.assertEqual(m.args[1], '<test@#test> This is a test', m)

            self.assertEqual(self.irc.takeMsg(), None)

            msgs = set((feedMsg('Ceci est un test'), self.irc.takeMsg()))
            msgs_foo = list(filter(lambda m:m.args[0]=='foo', msgs))
            msgs_bar = list(filter(lambda m:m.args[0]=='bar', msgs))
            self.assertEqual(len(msgs_foo), 1)
            self.assertEqual(len(msgs_bar), 1)
            m = msgs_foo[0]
            self.assertEqual(m.command, 'PRIVMSG', m)
            self.assertEqual(m.args[0], 'foo', m)
            self.assertEqual(m.args[1], '<test@#test> This is a test', m)
            m = msgs_bar[0]
            self.assertEqual(m.command, 'PRIVMSG', m)
            self.assertEqual(m.args[0], 'bar', m)
            self.assertEqual(m.args[1], '<test@#test> Dies ist ein Test', m)

            self.assertEqual(self.irc.takeMsg(), None)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry

try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('Biography')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Biography', True)


Biography = conf.registerPlugin('Biography')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Biography, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))

conf.registerChannelValue(Biography, 'requireCapability',
    registry.String('admin', _("""Determines what capability (if any) is required to
    change fields of another user.""")))
conf.registerChannelValue(Biography, 'fields',
    registry.CommaSeparatedListOfStrings(['email', 'facebook', 'twitter'],
    _("""Comma-separated list of fields that can be stored.
    Order matters when displayed""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.world as world
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('Biography')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x


class BiographyDB(plugins.ChannelUserDB):
    def serialize(self, v):
        return [v]

    def deserialize(self, channel, id, L):
        if len(L) != 1:
            raise ValueError
        return L[0]

@internationalizeDocstring
class Biography(callbacks.Plugin):
    """Add the help for "@plugin help Biography" here
    This should describe *how* to use this plugin."""

    def __init__(self, irc):
        super(Biography, self).__init__(irc)

        filename = conf.supybot.directories.data.dirize('Biography.db')
        self.db = BiographyDB(filename)
        world.flushers.append(self.db.flush)

    def die(self):
        if self.db.flush in world.flushers:
            world.flushers.remove(self.db.flush)
        self.db.close()
        super(Biography, self).die()

    def _preCheck(self, irc, msg, user):
        # Stolen from Herald plugin
        capability = self.registryValue('requireCapability')
        if capability:
            try:
                u = ircdb.users.getUser(msg.prefix)
            except KeyError:
                irc.errorNotRegistered(Raise=True)
            else:
                if u != user:
                    if not ircdb.checkCapability(msg.prefix, capability):
                        irc.errorNoCapability(capability, Raise=True)

    @internationalizeDocstring
    def get(self, irc, msg, args, channel, user, key):
        """[<channel>] [<username>] [<field>]

        Gets an information for the <username>. If <field> is not given, all
        informations are returned."""
        fields = self.registryValue('fields', channel)
        if key and key not in fields:
            s = format(_('This is not a valid field. Valid fields are: %L'),
                    fields)
            irc.error(s, Raise=True)
        channeluser = (channel, user.id)
        if channeluser not in self.db:
            irc.error(_('No information on this user.'), Raise=True)
        info = self.db[channeluser]
        if key:
            if key not in info:
                irc.error(_('Information not available for this user.'),
                        Raise=True)
            irc.reply(_('%(key)s for %(user)s: %(value)s') % {
                'key': key, 'user': user.name,
                'value': info[key]})
        else:
            def part(key):
                return _('%(key)s: %(value)s') % {
                        'key': ircutils.bold(key),
                        'value': info[key],
                        }
            parts = map(lambda x:part(x) if x in info else '', fields)
            irc.reply(format('%L', parts))
    get = wrap(get, ['channel', first('otherUser', 'user'),
        optional('something')])

    @internationalizeDocstring
    def set(self, irc, msg, args, channel, user, key, value):
        """[<channel>] [<username>] <field> <value>

        Sets an information for the <username>."""
        self._preCheck(irc, msg, user)
        fields = self.registryValue('fields', channel)
        if key not in fields:
            s = format(_('This is not a valid field. Valid fields are: %L'),
                    fields)
            irc.error(s, Raise=True)
        channeluser = (channel, user.id)
        if channeluser not in self.db:
            self.db[channeluser] = {}
        self.db[channeluser].update({key: value})
        irc.replySuccess()
    set = wrap(set, ['channel', first('otherUser', 'user'),
        'something', 'text'])


Class = Biography


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *
import supybot.ircdb as ircdb

class BiographyTestCase(ChannelPluginTestCase):
    plugins = ('Biography', 'User')

    def setUp(self):
        super(BiographyTestCase, self).setUp()
        user = ircdb.users.newUser()
        user.name = 'ProgVal'
        ircdb.users.setUser(user)

        user = ircdb.users.newUser()
        user.name = 'someone'
        user.addHostmask(self.prefix)
        user.addCapability('admin')
        ircdb.users.setUser(user)

    def testBiography(self):
        self.assertRegexp('biography get ProgVal foo', 'not a valid field')
        self.assertRegexp('biography set ProgVal foo bar', 'not a valid field')
        self.assertRegexp('biography get ProgVal twitter', 'No information')
        self.assertRegexp('biography get ProgVal facebook', 'No information')
        self.assertRegexp('biography get ProgVal', 'No information')
        self.assertNotError('biography set ProgVal twitter @ProgVal')
        self.assertRegexp('biography get ProgVal twitter', '@ProgVal')
        self.assertRegexp('biography get ProgVal facebook', 'not available')
        self.assertRegexp('biography get ProgVal', '@ProgVal')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Brainfuck')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Brainfuck', True)


Brainfuck = conf.registerPlugin('Brainfuck')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Brainfuck, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import time

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Brainfuck')

class BrainfuckException(Exception):
    pass

class BrainfuckSyntaxError(BrainfuckException):
    pass

class BrainfuckTimeout(BrainfuckException):
    pass

class NotEnoughInput(BrainfuckException):
    pass

class SegmentationFault(BrainfuckException):
    pass

class InvalidCharacter(BrainfuckException):
    pass

class BrainfuckProcessor:
    def __init__(self, dummy=False):
        self._dummy = dummy
        if not dummy:
            self.memory = [0]
            self.memoryPointer = 0

    def checkSyntax(self, program):
        nesting = 0
        index = 0
        for char in program:
            index += 1
            if char == '[':
                nesting += 1
            elif char == ']':
                nesting -= 1
                if nesting < 0:
                    return _('Got `]` (at index %i), expected whatever you '
                            'want but not that.') % index
        if nesting != 0:
            return _('Got end of string, expected `]`.')
        return

    def execute(self, program, input_='', timeLimit=5, checkSyntax=True):
        if checkSyntax:
            syntaxError = self.checkSyntax(program)
            if syntaxError:
                raise BrainfuckSyntaxError(syntaxError)
        programPointer = 0
        output = ''
        programLength = len(program)
        input_ = [ord(x) for x in input_]
        loopStack = []
        timeout = time.time() + timeLimit
        while programPointer < programLength:
            char = program[programPointer]
            if char == '>':   # Increment pointer
                self.memoryPointer += 1
                if len(self.memory) <= self.memoryPointer:
                    self.memory.append(0)
            elif char == '<': # Decrement pointer
                self.memoryPointer -= 1
                if self.memoryPointer < 0:
                    raise SegmentationFault(_('Negative memory pointer.'))
            elif char == '+': # Increment data
                self.memory[self.memoryPointer] += 1
            elif char == '-': # Decrement data
                self.memory[self.memoryPointer] -= 1
            elif char == '.': # Output data
                try:
                    output += chr(self.memory[self.memoryPointer])
                except ValueError:
                    raise InvalidCharacter(str(self.memory[self.memoryPointer]))
            elif char == ',': # Input data
                try:
                    self.memory[self.memoryPointer] = input_.pop(0)
                except IndexError:
                    raise NotEnoughInput()
            elif char == '[': # Loop start
                if not self.memory[self.memoryPointer]:
                    nesting = 0
                    while programPointer < programLength:
                        if program[programPointer] == '[':
                            nesting += 1
                        elif program[programPointer] == ']':
                            nesting -= 1
                            if nesting == 0:
                                break
                        programPointer += 1
                else:
                    loopStack.append(programPointer)
            elif char == ']': # Loop end
                programPointer = loopStack.pop() - 1
            programPointer += 1
            if timeout < time.time():
                raise BrainfuckTimeout(output)
        return output
                    

@internationalizeDocstring
class Brainfuck(callbacks.Plugin):
    """Add the help for "@plugin help Brainfuck" here
    This should describe *how* to use this plugin."""
    threaded = True
    latestProcessor = None

    @internationalizeDocstring
    def checksyntax(self, irc, msg, args, code):
        """<command>

        Tests the Brainfuck syntax without running it. You should quote the
        code if you use brackets, because Supybot would interpret it as nested
        commands."""
        syntaxError = BrainfuckProcessor(dummy=True).checkSyntax(code)
        if syntaxError:
            irc.reply(syntaxError)
        else:
            irc.reply(_('Your code looks ok.'))
    checksyntax = wrap(checksyntax, ['text'])


    @internationalizeDocstring
    def brainfuck(self, irc, msg, args, opts, code):
        """[--recover] [--input <characters>] <command>

        Interprets the given Brainfuck code. You should quote the code if you
        use brackets, because Supybot would interpret it as nested commands.
        If --recover is given, the bot will recover the previous processor
        memory and memory pointer.
        The code will be fed the <characters> when it asks for input."""
        opts = dict(opts)
        if 'input' not in opts:
            opts['input'] = ''
        if 'recover' in opts:
            if self.latestProcessor is None:
                irc.error(_('No processor has been run for the moment.'))
                return
            else:
                processor = self.latestProcessor
        else:
            processor = BrainfuckProcessor()
            self.latestProcessor = processor

        try:
            output = processor.execute(code, input_=opts['input'])
        except BrainfuckSyntaxError as e:
            irc.error(_('Brainfuck syntax error: %s') % e.args[0])
            return
        except BrainfuckTimeout as e:
            if e.args[0] != '':
                irc.reply(e.args[0])
            irc.error(_('Brainfuck processor timed out.'))
            return
        except NotEnoughInput:
            irc.error(_('Input too short.'))
            return
        except SegmentationFault as e:
            irc.error(_('Segmentation fault: %s') % e.args[0])
            return
        except InvalidCharacter as e:
            irc.error(_('Tried to output invalid character: %s') % e.args[0])
            return
        irc.reply(output)
    brainfuck = wrap(brainfuck, [getopts({'recover': '',
                                          'input': 'something'}),
                                 'text'])



Class = Brainfuck


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class BrainfuckTestCase(PluginTestCase):
    plugins = ('Brainfuck',)

    def testBrainfuck(self):
        self.assertResponse('brainfuck "'
                            '++++++++++[>+++++++>++++++++++>+++>+<<<<-]'
                            '>++.>+.+++++++..+++.>++.<<+++++++++++++++.'
                            '>.+++.------.--------.>+."', 'Hello World!')
        self.assertResponse('brainfuck "'
                            '++++++++++[>+++++++>++++++++++>+++>+<<<<-]'
                            '>++.>+.+++++++..+++.>++.<<+++++++++++++++.'
                            '>.+++.------.--------.>+."', 'Hello World!')

    def testInput(self):
        self.assertResponse('brainfuck --input b ",++."', 'd')
        self.assertResponse('brainfuck --input b ",,++."',
                'Error: Input too short.')

    def testTimeout(self):
        self.assertResponse('brainfuck "+[]"',
                'Error: Brainfuck processor timed out.')

    def testCheckSyntax(self):
        self.assertResponse('checksyntax "[[["',
                'Got end of string, expected `]`.')
        self.assertResponse('checksyntax "[[]"',
                'Got end of string, expected `]`.')
        self.assertResponse('checksyntax "[[]]]"',
                'Got `]` (at index 5), expected whatever you want but not that.')
        self.assertRegexp('brainfuck "[[]]]"',
                'Error: Brainfuck syntax error: .*whatever.*')

    def testRecover(self):
        self.assertNotError('brainfuck --input a ,.')
        self.assertResponse('brainfuck .', "'\\x00'")
        self.assertNotError('brainfuck --input a ,.')
        self.assertResponse('brainfuck --recover .', 'a')

    def testMemory(self):
        self.assertResponse('brainfuck <',
                'Error: Segmentation fault: Negative memory pointer.')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('ChannelStatus')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('ChannelStatus', True)


ChannelStatus = conf.registerPlugin('ChannelStatus')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(ChannelStatus, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))
conf.registerChannelValue(ChannelStatus, 'listed',
    registry.Boolean(False, _("""Determines whether or not this channel will
    be publicly listed on the web server.""")))
conf.registerChannelValue(ChannelStatus, 'nicks',
    registry.Boolean(False, _("""Determines whether or not the list of users
    in this channel will be listed.""")))
conf.registerChannelValue(ChannelStatus, 'topic',
    registry.Boolean(False, _("""Determines whether or not the topic of this
    channel will be displayed.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import sys
import urllib

import supybot.utils as utils
from supybot.commands import *
import supybot.world as world
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.httpserver as httpserver
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('ChannelStatus')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

PAGE_SKELETON = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>Channel status</title>
<link rel="stylesheet" href="/default.css" />
</head>
%s
</html>"""

DEFAULT_TEMPLATES = {
        'channelstatus/index.html': PAGE_SKELETON % """\
<body class="purelisting">
    <h1>Channels</h1>
    <ul>
        %(channels)s
    </ul>
</body>""",
        'channelstatus/channel.html': PAGE_SKELETON % """\
<body class="purelisting">
    <h1>%(channel)s@%(network)s</h1>
    <h2>Topic</h2>
    %(topic)s
    <h2>Users</h2>
    %(nicks)s
</body>""",
}

httpserver.set_default_templates(DEFAULT_TEMPLATES)

if sys.version_info[0] >= 3:
    quote = urllib.parse.quote
    unquote = urllib.parse.unquote
else:
    quote = urllib.quote
    unquote = urllib.unquote

class ChannelStatusCallback(httpserver.SupyHTTPServerCallback):
    name = 'Channels status'

    def _invalidChannel(self):
        self.send_response(404)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(httpserver.get_template('generic/error.html')%
            {'title': 'ChannelStatus - not a channel',
             'error': 'This is not a channel'})

    def doGet(self, handler, path):
        parts = path.split('/')[1:]
        if path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            template = httpserver.get_template('channelstatus/index.html')
            channels = set()
            for irc in world.ircs:
                channels |= set(['<li><a href="./%s/">%s@%s</a></li>' %
                    (quote('%s@%s' % (x, irc.network)), x, irc.network)
                    for x in irc.state.channels.keys()
                    if self._plugin.registryValue('listed', x)])
            channels = list(channels)
            channels.sort()
            self._write(template % {'channels': ('\n'.join(channels))})
        elif len(parts) == 2:
            (channel, network) = unquote(parts[0]).split('@')
            if not ircutils.isChannel(channel):
                self._invalidChannel()
                return
            for irc in world.ircs:
                if irc.network == network:
                    break
            if irc.network != network or channel not in irc.state.channels:
                self._invalidChannel()
                return
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            state = irc.state.channels[channel]
            replacements = {'channel': channel, 'network': network,
                    'nicks': _('Private'), 'topic': _('Private')}
            if self._plugin.registryValue('topic', channel):
                replacements['topic'] = state.topic
            if self._plugin.registryValue('nicks', channel):
                replacements['nicks'] = '<ul>' + \
                        '\n'.join(sorted(['<li>%s</li>' % x
                            for x in state.users])) + \
                        '</ul>'
            template = httpserver.get_template('channelstatus/channel.html')
            self._write(template % replacements)
    def _write(self, s):
        if sys.version_info[0] >= 3 and isinstance(s, str):
            s = s.encode()
        self.wfile.write(s)


class ChannelStatus(callbacks.Plugin):
    """Add the help for "@plugin help ChannelStatus" here
    This should describe *how* to use this plugin."""
    def __init__(self, irc):
        callbacks.Plugin.__init__(self, irc)
        self._startHttp()
    def _startHttp(self):
        callback = ChannelStatusCallback()
        callback._plugin = self
        httpserver.hook('channelstatus', callback)
        self._http_running = True
    def _stopHttp(self):
        httpserver.unhook('channelstatus')
        self._http_running = False
    def die(self):
        self._stopHttp()
        super(self.__class__, self).die()


Class = ChannelStatus


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class ChannelStatusTestCase(PluginTestCase):
    plugins = ('ChannelStatus',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = cleverbot
#!/usr/bin/python
# CleverBot Supybot Plugin v1.0
# (C) Copyright 2012 Albert H. (alberthrocks)
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
# This is from the pycleverbot library, found at:
# http://code.google.com/p/pycleverbot/
# 

"""
This library lets you open chat session with cleverbot (www.cleverbot.com)

Example of how to use the bindings:

>>> import cleverbot
>>> cb=cleverbot.Session()
>>> print cb.Ask("Hello there")
'Hello.'

"""

import hashlib
import sys
import re

if sys.version_info[0] >= 3:
    import urllib
    Request = urllib.request.Request
    urlopen = urllib.request.urlopen
    def u(s):
        return s
    def b(s):
        return s.encode('utf-8')
else:
    import urllib2
    from urllib import urlencode, urlopen
    Request = urllib2.Request
    def u(s):
        return unicode(s, "unicode_escape")
    def b(s):
        return s

class ServerFullError(Exception):
    pass

ReplyFlagsRE = re.compile('<INPUT NAME=(.+?) TYPE=(.+?) VALUE="(.*?)">', re.IGNORECASE | re.MULTILINE)

class Session(object):
    keylist=['stimulus','start','sessionid','vText8','vText7','vText6','vText5','vText4','vText3','vText2','icognoid','icognocheck','prevref','emotionaloutput','emotionalhistory','asbotname','ttsvoice','typing','lineref','fno','sub','islearning','cleanslate']
    headers={}
    headers['User-Agent']='Mozilla/5.0 (Windows NT 6.1; WOW64; rv:7.0.1) Gecko/20100101 Firefox/7.0'
    headers['Accept']='text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    headers['Accept-Language']='en-us;q=0.8,en;q=0.5'
    headers['X-Moz']='prefetch'
    headers['Accept-Charset']='ISO-8859-1,utf-8;q=0.7,*;q=0.7'
    headers['Referer']='http://www.cleverbot.com'
    headers['Cache-Control']='no-cache, no-cache'
    headers['Pragma']='no-cache'

    def __init__(self):
        self.arglist=['','y','','','','','','','','','wsf','','','','','','','','','0','Say','1','false']
        self.MsgList=[]

    def Send(self):
        data=encode(self.keylist,self.arglist)
        digest_txt=data[9:29]
        hash=hashlib.md5(b(digest_txt)).hexdigest()
        self.arglist[self.keylist.index('icognocheck')]=hash
        data=encode(self.keylist,self.arglist)
        req=Request("http://www.cleverbot.com/webservicemin",b(data),self.headers)
        f=urlopen(req, timeout=9) #Needed to prevent supybot errors
        reply=f.read()
        if sys.version_info[0] >= 3:
            reply = reply.decode()
        return reply

    def Ask(self,q):
        self.arglist[self.keylist.index('stimulus')]=q
        if self.MsgList: self.arglist[self.keylist.index('lineref')]='!0'+str(len(self.MsgList)/2)
        asw=self.Send()
        self.MsgList.append(q)
        answer = parseAnswers(asw)
        for k,v in answer.items():
            try:
                self.arglist[self.keylist.index(k)] = v
            except ValueError:
                pass
        self.arglist[self.keylist.index('emotionaloutput')]=''
        text = answer['ttsText']
        self.MsgList.append(text)
        return text

def parseAnswers(text):
    d = {}
    keys = ["text", "sessionid", "logurl", "vText8", "vText7", "vText6", "vText5", "vText4", "vText3",
            "vText2", "prevref", "foo", "emotionalhistory", "ttsLocMP3", "ttsLocTXT",
            "ttsLocTXT3", "ttsText", "lineRef", "lineURL", "linePOST", "lineChoices",
            "lineChoicesAbbrev", "typingData", "divert"]
    values = text.split("\r")
    i = 0
    for key in keys:
        d[key] = values[i]
        i += 1
    return d

def encode(keylist,arglist):
    text=''
    for i in range(len(keylist)):
        k=keylist[i]; v=quote(arglist[i])
        text+='&'+k+'='+v
    text=text[1:]
    return text

always_safe = ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
               'abcdefghijklmnopqrstuvwxyz'
               '0123456789' '_.-')
def quote(s, safe = '/'):   #quote('abc def') -> 'abc%20def'
    safe += always_safe
    safe_map = {}
    for i in range(256):
        c = chr(i)
        safe_map[c] = (c in safe) and c or  ('%%%02X' % i)
    res = map(safe_map.__getitem__, s)
    return ''.join(res)


def main():
    import sys
    cb = Session()

    q = ''
    while q != 'bye':
        try:
            if sys.version_info[0] < 3:
                q = raw_input("> ")
            else:
                q = input("> ")
        except KeyboardInterrupt:
            print()
            sys.exit()
        print(cb.Ask(q))

if __name__ == "__main__":
    main()



########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
# CleverBot Supybot Plugin v1.0
# (C) Copyright 2012 Albert H. (alberthrocks)
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
 
import supybot.conf as conf
import supybot.registry as registry
 
def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Cleverbot', True)
 
 
Cleverbot = conf.registerPlugin('Cleverbot')
#conf.registerGlobalValue(Cleverbot,'bot',registry.String('923c98f3de35606b',"""bot ID"""))
conf.registerGlobalValue(Cleverbot,'bot',registry.String('9c1423d9be345c5c',"""bot ID"""))
conf.registerGlobalValue(Cleverbot,'name',registry.String('AaronBot',"""bot name"""))
conf.registerChannelValue(Cleverbot,'react',registry.Boolean(True,"""Determine whether the bot should respond to errors."""))
conf.registerChannelValue(Cleverbot,'reactprivate',registry.Boolean(True,"""Determine whether the bot should respond to private chat errors."""))
conf.registerChannelValue(Cleverbot,'enable',registry.Boolean(False,"""Determine whether the Cleverbot response is enabled or not"""))
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Cleverbot, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))
 
 
# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
########NEW FILE########
__FILENAME__ = plugin
# CleverBot Supybot Plugin v1.0
# (C) Copyright 2012 Albert H. (alberthrocks)
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
 
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import re, random, time, sys

if sys.version_info[0] >= 3:
    from html.entities import name2codepoint
else:
    from htmlentitydefs import name2codepoint

from . import cleverbot
 
class Cleverbot(callbacks.Plugin):
    """This plugin replies using the Cleverbot API upon intercepting an invalid command."""
    threaded = True
    callAfter = ['MoobotFactoids','Factoids','Infobot']
    def __init__(self,irc):
        self.__parent = super(Cleverbot,self)
        self.__parent.__init__(irc)
        self.nicks = {}
        self.hashes = {}
        self.sessions = {}

    @staticmethod
    def decode_htmlentities(s):
        def substitute_entity(match):
            ent = match.group(3)
            if match.group(1) == "#":    # number, decimal or hexadecimal
                return unichr(int(ent)) if match.group(2) == '' else unichr(int('0x'+ent,16))
            else:    # name
                cp = name2codepoint.get(ent)
                return unichr(cp) if cp else match.group()
        return re.compile(r'&(#?)(x?)(\w+);').subn(substitute_entity,s)[0]

    @staticmethod
    def _randHash():
        return '%016x'%random.getrandbits(64)

    @classmethod
    def _post(cls,bot,hash,line,sess):
        m = sess.Ask(line)
        if m:
            return m
        return None

    @classmethod
    def _identify(cls,bot,hash,name):
        return cleverbot.Session()

    def getHash(self,nick):
        nick = nick.lower()
        if nick not in self.nicks:
            self.nicks[nick] = self._randHash()
        return self.nicks[nick]

    def getResponse(self,irc,msg,line):
        hash = self.getHash(msg.nick)
        args = (self.registryValue('bot'),hash)
        if hash not in self.hashes or time.time()-self.hashes[hash] > 300:
            sess = self._identify(*(args+(msg.nick,)))
            self.sessions[hash] = sess
        else:
            sess = self.sessions[hash]
        self.hashes[hash] = time.time()
        line = re.compile(r'\b'+re.escape(irc.nick)+r'\b',re.I).sub('you',re.compile(r'^'+re.escape(irc.nick)+r'\S',re.I).sub('',line))
        reply = self._post(*(args+(line,sess,)))
        if reply is None:
            return None
        name = self.registryValue('name')
        return reply

    def invalidCommand(self,irc,msg,tokens):
        try:
            self.log.debug('Channel is: "+str(irc.isChannel(msg.args[0]))')
            self.log.debug("Message is: "+str(msg.args))
        except:
            self.log.error("message not retrievable.")

        if irc.isChannel(msg.args[0]) and self.registryValue('react',msg.args[0]):
            channel = msg.args[0]
            self.log.debug("Fetching response...")
            reply = self.getResponse(irc,msg,ircutils.stripFormatting(msg.args[1]).strip())
            self.log.debug("Got response!")
            if reply is not None:
                self.log.debug("Reply is: "+str(reply))
                if self.registryValue('enable', channel):
                     irc.reply(reply)
            else:
                irc.reply("My AI is down, sorry! :( I couldn't process what you said... blame it on a brain fart. :P")
        elif (msg.args[0] == irc.nick) and self.registryValue('reactprivate',msg.args[0]):
            err = ""
            self.log.debug("Fetching response...")
            reply = self.getResponse(irc,msg,ircutils.stripFormatting(msg.args[1]).strip())
            self.log.debug("Got response!")
            if reply is not None:
                self.log.debug("Reply is: "+str(reply))
                if self.registryValue('enable', channel):
                     irc.reply(reply)
            else:
                irc.reply("My AI is down, sorry! :( I couldn't process what you said... blame it on a brain fart. :P", err, None, True, None, None)

    def Cleverbot(self,irc,msg,args,line):
        """<line>
        Fetches response from Cleverbot
        """
        reply = self.getResponse(irc,msg,line)
        if reply is not None:
            irc.reply('Cleverbot: %s'%reply)
        else:
            irc.reply('There was no response.')
    Cleverbot = wrap(Cleverbot,['text'])

    def doNick(self,irc,msg):
        try:
            del self.nicks[msg.nick.lower()]
        except KeyError:
            pass
        self.nicks[msg.args[0].lower()] = self._randHash()
        self._identify(self.registryValue('bot'),self.getHash(msg.args[0].lower()),msg.args[0])
#    def doKick(self,irc,msg):
#        del self.nicks[msg.args[1]]
#    def doPart(self,irc,msg):
#        del self.nicks[msg.nick.lower()]

    def doQuit(self,irc,msg):
        try:
            del self.nicks[msg.nick.lower()]
        except KeyError:
            pass
 
 
Class = Cleverbot
 
 
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
# CleverBot Supybot Plugin v1.0
# (C) Copyright 2012 Albert H. (alberthrocks)
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
from supybot.test import *

class PandorabotsTestCase(PluginTestCase):
    plugins = ('Pandorabots',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Coffee')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Coffee', True)


Coffee = conf.registerPlugin('Coffee')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Coffee, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('Coffee')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

@internationalizeDocstring
class Coffee(callbacks.Plugin):
    """Add the help for "@plugin help Coffee" here
    This should describe *how* to use this plugin."""

    @internationalizeDocstring
    def coffee(self, irc, msg, args):
        """takes no arguments

        Makes coffee using the  Hyper Text Coffee Pot Control Protocol
        (HTCPCP/1.0). More info at http://www.ietf.org/rfc/rfc2324.txt
        Warning: this command has side effect if no compatible device
        is found on the channel."""
        coffee = r"""        {
     }   }   {
    {   {  }  }
     }   }{  {
    {  }{  }  }
   ( }{ }{  { )
 .- { { }  { }} -.
(  ( } { } { } }  )
|`-..________ ..-'|
|                 |
|                 ;--.
|                (__  \
|                 | )  )
|                 |/  /
|                 (  /
|                 y'
|                 |
 `-.._________..-'"""
        for line in coffee.split('\n'):
            irc.reply(line)
        irc.reply(_('Ahah, you really believed this? Supybot can do mostly '
                'everything, but not coffee!'))

Class = Coffee


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class CoffeeTestCase(PluginTestCase):
    plugins = ('Coffee',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Coinpan')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Coinpan', True)


Coinpan = conf.registerPlugin('Coinpan')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Coinpan, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))
conf.registerChannelValue(Coinpan, 'enable',
    registry.Boolean(False, _("""Determines whether Coinpan is enabled on
    this channel""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
# -*- coding: utf8 -*-
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import re

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Coinpan')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

REGEXP = '[cçk]^([o0öôØ]^[i1ïî]|[i1]^[o0Ø])^[nñ]'
_regexp = re.compile(REGEXP.replace('^', ''), re.I)
def replacer(match):
    coin = match.group(0)
    assert len(coin) == 4
    reverse = coin[1] in 'i1I'
    if reverse:
        assert coin[2] in 'oO0'
        coin = coin[0] + coin[2] + coin[1] + coin[3]
        reverse = True
    strike = 'Ø' in coin
    if strike:
        coin = coin.replace('Ø', 'o')
    pan = ''
    if coin[0] in 'ck':
        pan += 'p'
    elif coin[0] in 'CK':
        pan += 'P'
    elif coin[0] == 'ç':
        pan += '\u0327p'
    elif coin[0] == 'Ç':
        pan += '\u0327P'
    else:
        raise AssertionError(coin)
    if strike:
        pan += '\u0336'
    if coin[1] == '0' or coin[2] == '1':
        pan += '4'
    elif coin[1:3] in 'Oï OÏ oÏ Öi ÖI öI Öï ÖÏ öÏ'.split(' '):
        pan += 'Ä'
    elif coin[1:3] in 'Oî OÎ oÎ Ôi ÔI ôI Ôî ÔÎ ôÎ'.split(' '):
        pan += 'Â'
    elif coin[1:3] in 'öi öï oï'.split(' '):
        pan += 'ä'
    elif coin[1:3] in 'ôi ôî oî'.split(' '):
        pan += 'â'
    elif coin[1] in 'ôÔöÖ' and coin[2] in 'îÎïÏ':
        if coin[0] in 'kK':
            return'KOINKOINKOINPANGPANGPANG'
        elif coin[0] in 'ĉĈ':
            return'ĈOINĈOINĈOINPANPANPAN'
        else:
            return'COINCOINCOINPANPANPAN'
    elif coin[1] == 'O' or coin[2] == 'I':
        pan += 'A'
    elif coin[1] == 'o' and coin[2] == 'i':
        pan += 'a'
    else:
        raise AssertionError(coin)
    if coin[3] == 'n':
        pan += 'n'
    elif coin[3] == 'N':
        pan += 'N'
    elif coin[3] == 'ñ':
        pan += 'ñ'
    elif coin[3] == 'Ñ':
        pan += 'Ñ'
    else:
        raise AssertionError(coin)
    if coin[0] == 'k':
        pan += 'g'
    elif coin[0] == 'K':
        pan += 'G'
    if reverse:
        pan = pan.replace('a', 'ɐ')
        pan = pan.replace('A', '∀')
        pan = pan.replace('4', 'ㄣ')
    return pan

def snarfer_generator():
    def coinSnarfer(self, irc, msg, match):
        if self.registryValue('enable', msg.args[0]):
            txt = msg.args[1]
            txt = txt.replace('\u200b', '')
            txt = txt.replace('Ο', 'O')
            txt = txt.replace('>o_/', '>x_/').replace('\_o<', '\_x<')
            txt = txt.replace('>O_/', '>x_/').replace('\_O<', '\_x<')
            irc.reply(_regexp.sub(replacer, txt), prefixNick=False)
    regexp = '(?i).*(%s|>^o^_^/|\^_^[Oo]^<).*' % REGEXP
    regexp = regexp.replace('^', '\u200b*')
    coinSnarfer.__doc__ = regexp
    return coinSnarfer

class Coinpan(callbacks.PluginRegexp):
    """Add the help for "@plugin help Coinpan" here
    This should describe *how* to use this plugin."""

    regexps = ['coinSnarfer']
    coinSnarfer = snarfer_generator()


Class = Coinpan


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
# -*- coding: utf8 -*-
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import sys
from unittest import skip
from supybot.test import *

class CoinpanTestCase(ChannelPluginTestCase):
    plugins = ('Coinpan',)
    config = {'supybot.plugins.Coinpan.enable': True}

    def testCoinpan(self):
        self.assertSnarfNoResponse('foo')
        self.assertSnarfResponse('coin coin', 'pan pan')
        self.assertSnarfResponse('foo coin bar', 'foo pan bar')
        self.assertSnarfResponse('foo COIN bar', 'foo PAN bar')
        self.assertSnarfResponse('foo Coin bar', 'foo Pan bar')
        self.assertSnarfResponse('foo c01n bar', 'foo p4n bar')

        self.assertSnarfResponse('foo coïn bar', 'foo pän bar')
        self.assertSnarfResponse('foo cöïn bar', 'foo pän bar')
        self.assertSnarfResponse('foo côîn bar', 'foo pân bar')
        self.assertSnarfResponse('foo côïn bar', 'foo COINCOINCOINPANPANPAN bar')
        self.assertSnarfResponse('foo coiÑ bar', 'foo paÑ bar')
        self.assertSnarfResponse('foo KOIN bar', 'foo PANG bar')

        self.assertSnarfResponse('foo KOIN >o_/ bar', 'foo PANG >x_/ bar')

        self.assertSnarfResponse('foo CION bar', 'foo P∀N bar')
        self.assertSnarfResponse('foo cion bar', 'foo pɐn bar')

    if sys.version_info < (2, 7, 0):
        def testCoinpan(self):
            pass
    elif sys.version_info < (3, 0, 0):
        testCoinpan = skip('Plugin not compatible with Python2.')(testCoinpan)

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2003-2005, James Vega
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('AttackProtector')
except:
    _ = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('Debian', True)

class ValidFileBranch(registry.OnlySomeStrings):
    validStrings = ('oldstable', 'stable', 'testing', 'unstable',
            'experimental')
class ValidFileMode(registry.OnlySomeStrings):
    validStrings = ('path', 'exactfilename', 'filename')
class ValidFileSection(registry.OnlySomeStrings):
    validStrings = ('any', 'main', 'contrib', 'non-free')

class ValidVersionBranch(registry.OnlySomeStrings):
    validStrings = ('oldstable', 'stable', 'testing', 'unstable',
            'experimental', 'all')
class ValidVersionSection(registry.OnlySomeStrings):
    validStrings = ('all', 'main', 'contrib', 'non-free')
class ValidVersionSearchon(registry.OnlySomeStrings):
    validStrings = ('names', 'all', 'sourcenames')

Debian = conf.registerPlugin('Debian')
conf.registerChannelValue(Debian, 'bold',
    registry.Boolean(True, _("""Determines whether the plugin will use bold in
    the responses to some of its commands.""")))
conf.registerGroup(Debian, 'defaults')
conf.registerGroup(Debian.defaults, 'file')
conf.registerChannelValue(Debian.defaults.file, 'branch',
    ValidFileBranch('stable', _("""Determines the default branch, ie. the
    branch selected if --branch is not given.""")))
conf.registerChannelValue(Debian.defaults.file, 'mode',
    ValidFileMode('path', _("""Determines the default mode, ie. the mode
    selected if --mode is not given.""")))
conf.registerChannelValue(Debian.defaults.file, 'section',
    ValidFileSection('any', _("""Determines the default section, ie. the
    section selected if --section is not given.""")))
conf.registerChannelValue(Debian.defaults.file, 'arch',
    registry.String('any', _("""Determines the default architecture,
    ie. the architecture selected if --arch is not given.""")))

conf.registerGroup(Debian.defaults, 'version')
conf.registerChannelValue(Debian.defaults.version, 'branch',
    ValidVersionBranch('all', _("""Determines the default branch, ie. the
    branch selected if --branch is not given.""")))
conf.registerChannelValue(Debian.defaults.version, 'section',
    ValidVersionSection('all', _("""Determines the default section, ie. the
    section selected if --section is not given.""")))
conf.registerChannelValue(Debian.defaults.version, 'searchon',
    ValidVersionSearchon('names', _("""Determines the default 'searchon', ie.
    where to search if --searchon is not given.""")))


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2003-2005, James Vega
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import os
import re
import time
import urllib
import fnmatch

import bs4 as BeautifulSoup

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.utils.iter import all

class Debian(callbacks.Plugin):
    threaded = True

    _debreflags = re.DOTALL | re.MULTILINE
    _deblistreFileExact = re.compile(r'<a href="/[^/>]+/[^/>]+">([^<]+)</a>',
                                     _debreflags)
    def file(self, irc, msg, args, optlist, filename):
        """[--exact] \
        [--mode {path,filename,exactfilename}] \
        [--branch {oldstable,stable,testing,unstable,experimental}] \
        [--arch <architecture>] \
        [--section {main,contrib,non-free}] <file name>

        Returns the package(s) containing the <file name>.
        --mode defaults to path, and defines how to search.
        --branch defaults to stable, and defines in what branch to search."""
        url = 'http://packages.debian.org/search?searchon=contents' + \
              '&keywords=%(keywords)s&mode=%(mode)s&suite=%(suite)s' + \
              '&arch=%(arch)s'
        def reg(name):
            return self.registryValue('defaults.file.%s' % name, msg.args[0])
        args = {'keywords': None,
                'mode': reg('mode'),
                'suite': reg('branch'),
                'section': reg('section'),
                'arch': reg('arch')}
        exact = ('exact', True) in optlist
        for (key, value) in optlist:
            if key == 'branch':
                args['suite'] = value
            elif key == 'section':
                args['section'] = value
            elif key == 'arch':
                args['arch'] = value
            elif key == 'mode':
                args['mode'] = value
        responses = []
        if '*' in filename:
            irc.error('Wildcard characters can not be specified.', Raise=True)
        args['keywords'] = utils.web.urlquote(filename, '')
        url %= args
        try:
            html = utils.web.getUrl(url).decode()
        except utils.web.Error as e:
            irc.error(format('I couldn\'t reach the search page (%s).', e),
                      Raise=True)
        if 'is down at the moment' in html:
            irc.error('Packages.debian.org is down at the moment.  '
                      'Please try again later.', Raise=True)
        step = 0
        pkgs = []
        for line in html.split('\n'):
            if '<span class="keyword">' in line:
                step += 1
            elif step == 1 or (step >= 1 and not exact):
                pkgs.extend(self._deblistreFileExact.findall(line))
        if pkgs == []:
            irc.reply(format('No filename found for %s (%s)',
                      utils.web.urlunquote(filename), args['suite']))
        else:
            # Filter duplicated
            pkgs = dict(map(lambda x:(x, None), pkgs)).keys()
            irc.reply(format('%i matches found: %s (%s)',
                          len(pkgs), '; '.join(pkgs), args['suite']))
    file = wrap(file, [getopts({'exact': '',
                                'branch': ('literal', ('oldstable',
                                                       'stable',
                                                       'testing',
                                                       'unstable',
                                                       'experimental')),
                                'mode': ('literal', ('path',
                                                     'exactfilename',
                                                     'filename')),
                                'section': ('literal', ('main',
                                                     'contrib',
                                                     'non-free')),
                                'arch': 'somethingWithoutSpaces'}),
                                'text'])

    _debreflags = re.DOTALL | re.IGNORECASE
    _deblistreVersion = re.compile(r'<h3>Package ([^<]+)</h3>(.*?)</ul>', _debreflags)
    def version(self, irc, msg, args, optlist, package):
        """[--exact] \
        [--searchon {names,all,sourcenames}] \
        [--branch {oldstable,stable,testing,unstable,experimental}] \
        [--section {main,contrib,non-free}] <package name>

        Returns the current version(s) of the Debian package <package name>.
        --exact, if given, means you want only the <package name>, and not
        package names containing this name.
        --searchon defaults to names, and defines where to search.
        --branch defaults to all, and defines in what branch to search.
        --section defaults to all, and defines in what section to search."""
        url = 'http://packages.debian.org/search?keywords=%(keywords)s' + \
              '&searchon=%(searchon)s&suite=%(suite)s&section=%(section)s'
        def reg(name):
            return self.registryValue('defaults.version.%s' % name, msg.args[0])
        args = {'keywords': None,
                'searchon': reg('searchon'),
                'suite': reg('branch'),
                'section': reg('section')}
        for (key, value) in optlist:
            if key == 'exact':
                url += '&exact=1'
            elif key == 'branch':
                args['suite'] = value
            elif key == 'section':
                args['section'] = value
            elif key == 'searchon':
                args['searchon'] = value
        responses = []
        if '*' in package:
            irc.error('Wildcard characters can not be specified.', Raise=True)
        args['keywords'] = utils.web.urlquote(package)
        url %= args
        try:
            html = utils.web.getUrl(url).decode()
        except utils.web.Error as e:
            irc.error(format('I couldn\'t reach the search page (%s).', e),
                      Raise=True)
        if 'is down at the moment' in html:
            irc.error('Packages.debian.org is down at the moment.  '
                      'Please try again later.', Raise=True)
        pkgs = self._deblistreVersion.findall(html)
        if not pkgs:
            irc.reply(format('No package found for %s (%s)',
                      utils.web.urlunquote(package), args['suite']))
        else:
            for pkg in pkgs:
                pkgMatch = pkg[0]
                soup = BeautifulSoup.BeautifulSoup(pkg[1])
                liBranches = soup.find_all('li')
                branches = []
                versions = []
                def branchVers(br):
                    vers = [b.next.string.strip() for b in br]
                    return [utils.str.rsplit(v, ':', 1)[0] for v in vers]
                for li in liBranches:
                    branches.append(li.a.string)
                    versions.append(branchVers(li.find_all('br')))
                if branches and versions:
                    for pairs in  zip(branches, versions):
                        branch = pairs[0]
                        ver = ', '.join(pairs[1])
                        s = format('%s (%s)', pkgMatch,
                                   ': '.join([branch, ver]))
                        responses.append(s)
            resp = format('%i matches found: %s',
                          len(responses), '; '.join(responses))
            irc.reply(resp)
    version = wrap(version, [getopts({'exact': '',
                                      'searchon': ('literal', ('names',
                                                               'all',
                                                               'sourcenames')),
                                      'branch': ('literal', ('oldstable',
                                                             'stable',
                                                             'testing',
                                                             'unstable',
                                                             'experimental')),
                                      'arch': ('literal', ('main',
                                                           'contrib',
                                                           'non-free'))}),
                                      'text'])

    _incomingRe = re.compile(r'<a href="(.*?\.deb)">', re.I)
    def incoming(self, irc, msg, args, optlist, globs):
        """[--{regexp,arch} <value>] [<glob> ...]

        Checks debian incoming for a matching package name.  The arch
        parameter defaults to i386; --regexp returns only those package names
        that match a given regexp, and normal matches use standard *nix
        globbing.
        """
        predicates = []
        archPredicate = lambda s: ('_i386.' in s)
        for (option, arg) in optlist:
            if option == 'regexp':
                predicates.append(r.search)
            elif option == 'arch':
                arg = '_%s.' % arg
                archPredicate = lambda s, arg=arg: (arg in s)
        predicates.append(archPredicate)
        for glob in globs:
            glob = fnmatch.translate(glob)
            predicates.append(re.compile(glob).search)
        packages = []
        try:
            fd = utils.web.getUrlFd('http://incoming.debian.org/')
        except utils.web.Error as e:
            irc.error(str(e), Raise=True)
        for line in fd:
            m = self._incomingRe.search(line.decode())
            if m:
                name = m.group(1)
                if all(None, map(lambda p: p(name), predicates)):
                    realname = utils.str.rsplit(name, '_', 1)[0]
                    packages.append(realname)
        if len(packages) == 0:
            irc.error('No packages matched that search.')
        else:
            irc.reply(format('%L', packages))
    incoming = thread(wrap(incoming,
                           [getopts({'regexp': 'regexpMatcher',
                                     'arch': 'something'}),
                            any('glob')]))

    def bold(self, s):
        if self.registryValue('bold', dynamic.channel):
            return ircutils.bold(s)
        return s

    _update = re.compile(r' : ([^<]+)</body')
    _bugsCategoryTitle = re.compile(r'<dt id="bugs_.." title="([^>]+)">')
    _latestVersion = re.compile(r'<span id="latest_version">(.+)</span>')
    _maintainer = re.compile(r'<a href=".*login=(?P<email>[^<]+)">.*'
                             '<span class="name" title="maintainer">'
                             '(?P<name>[^<]+)</span>', re.S)
    def stats(self, irc, msg, args, pkg):
        """<source package>

        Reports various statistics (from http://packages.qa.debian.org/) about
        <source package>.
        """
        pkg = pkg.lower()
        try:
            text = utils.web.getUrl('http://packages.qa.debian.org/%s/%s.html' %
                                    (pkg[0], pkg)).decode('utf8')
        except utils.web.Error:
            irc.errorInvalid('source package name')
        for line in text.split('\n'):
            match = self._latestVersion.search(text)
            if match is not None:
                break
        assert match is not None
        version = '%s: %s' % (self.bold('Last version'),
                              match.group(1))
        updated = None
        m = self._update.search(text)
        if m:
            updated = m.group(1)
        soup = BeautifulSoup.BeautifulSoup(text)
        pairs = zip(soup.find_all('dt'),
                    soup.find_all('dd'))
        for (label, content) in pairs:
            try:
                title = self._bugsCategoryTitle.search(str(label)).group(1)
            except AttributeError: # Didn't match
                if str(label).startswith('<dt id="bugs_all">'):
                    title = 'All bugs'
                elif str(label) == '<dt title="Maintainer and Uploaders">' + \
                                   'maint</dt>':
                    title = 'Maintainer and Uploaders'
                else:
                    continue
            if title == 'Maintainer and Uploaders':
                match = self._maintainer.search(str(content))
                name, email = match.group('name'), match.group('email')
                maintainer = format('%s: %s %u', self.bold('Maintainer'),
                                    name, utils.web.mungeEmail(email))
            elif title == 'All bugs':
                bugsAll = format('%i Total', content.span.string)
            elif title == 'Release Critical':
                bugsRC = format('%i RC', content.span.string)
            elif title == 'Important and Normal':
                bugs = format('%i Important/Normal',
                              content.span.string)
            elif title == 'Minor and Wishlist':
                bugsMinor = format('%i Minor/Wishlist',
                                   content.span.string)
            elif title == 'Fixed and Pending':
                bugsFixed = format('%i Fixed/Pending',
                                   content.span.string)
        bugL = (bugsAll, bugsRC, bugs, bugsMinor, bugsFixed)
        s = '.  '.join((version, maintainer,
                        '%s: %s' % (self.bold('Bugs'), '; '.join(bugL))))
        if updated:
            s = 'As of %s, %s' % (updated, s)
        irc.reply(s)
    stats = wrap(stats, ['somethingWithoutSpaces'])

    _newpkgre = re.compile(r'<li><a href[^>/]+>([^<]+)</a>')
    def new(self, irc, msg, args, section, version, glob):
        """[{main,contrib,non-free}] [<version>] [<glob>]

        Checks for packages that have been added to Debian's unstable branch
        in the past week.  If no glob is specified, returns a list of all
        packages.  If no section is specified, defaults to main.
        """
        if version is None:
            version = 'unstable'
        try:
            fd = utils.web.getUrlFd('http://packages.debian.org/%s/%s/newpkg' %
                    (version, section))
        except utils.web.Error as e:
            irc.error(str(e), Raise=True)
        packages = []
        for line in fd:
            m = self._newpkgre.search(line.decode())
            if m:
                m = m.group(1)
                if fnmatch.fnmatch(m, glob):
                    packages.append(m)
        fd.close()
        if packages:
            irc.reply(format('%L', packages))
        else:
            irc.error('No packages matched that search.')
    new = wrap(new, [optional(('literal', ('main', 'contrib', 'non-free')),
                              'main'),
                     optional('something'),
                     additional('glob', '*')])

    _severity = re.compile(r'<p>Severity: ([^<]+)</p>', re.I)
    _package = re.compile(r'<pre class="message">Package: ([^<\n]+)\n',
                          re.I | re.S)
    _reporter = re.compile(r'Reported by: <[^>]+>([^<]+)<', re.I | re.S)
    _subject = re.compile(r'<span class="headerfield">Subject:</span> [^:]+: ([^<]+)</div>', re.I | re.S)
    _date = re.compile(r'<span class="headerfield">Date:</span> ([^\n]+)\n</div>', re.I | re.S)
    _tags = re.compile(r'<p>Tags: ([^<]+)</p>', re.I)
    _searches = (_package, _subject, _reporter, _date)
    def bug(self, irc, msg, args, bug):
        """<num>

        Returns a description of the bug with bug id <num>.
        """
        url = 'http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=%s' % bug
        try:
            text = utils.web.getUrl(url).decode()
        except utils.web.Error as e:
            irc.error(str(e), Raise=True)
        if "There is no record of Bug" in text:
            irc.error('I could not find a bug report matching that number.',
                      Raise=True)
        searches = list(map(lambda p: p.search(text), self._searches))
        sev = self._severity.search(text)
        tags = self._tags.search(text)
        # This section should be cleaned up to ease future modifications
        if all(None, searches):
            L = map(self.bold, ('Package', 'Subject', 'Reported'))
            resp = format('%s: %%s; %s: %%s; %s: by %%s on %%s', *L)
            L = map(utils.web.htmlToText, map(lambda p: p.group(1), searches))
            resp = format(resp, *L)
            if sev:
                sev = list(filter(None, sev.groups()))
                if sev:
                    sev = utils.web.htmlToText(sev[0])
                    resp += format('; %s: %s', self.bold('Severity'), sev)
            if tags:
                resp += format('; %s: %s', self.bold('Tags'), tags.group(1))
            resp += format('; %u', url)
            irc.reply(resp)
        else:
            irc.error('I was unable to properly parse the BTS page.')
    bug = wrap(bug, [('id', 'bug')])

Class = Debian


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2003-2005, James Vega
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import os
import time

from supybot.test import *

class DebianTestCase(PluginTestCase):
    plugins = ('Debian',)
    timeout = 100
    cleanDataDir = False
    fileDownloaded = False
    if network:
        def testDebBug(self):
            self.assertNotRegexp('debian bug 539859', r'\<em\>')
            self.assertResponse('debian bug 539859',
                                '\x02Package\x02: supybot; '
                                '\x02Subject\x02: configurable error in '
                                'ShrinkUrl; '
                                '\x02Reported\x02: by Clint Adams '
                                '<clintATdebian.org> on '
                                'Tue, 4 Aug 2009 03:39:37 +0000; '
                                '\x02Severity\x02: wishlist; '
                                '\x02Tags\x02: fixed-upstream; '
                                '<http://bugs.debian.org/cgi-bin/'
                                'bugreport.cgi?bug=539859>'.replace('AT', '@'))
            self.assertError('debian bug 551215216542')

        def testDebversion(self):
            self.assertHelp('debian version')
            self.assertRegexp('debian version lakjdfad',
                              r'^No package.*\(all\)')
            self.assertRegexp('debian version --branch unstable alkdjfad',
                r'^No package.*\(unstable\)')
            self.assertRegexp('debian version --branch stable gaim',
                              r'\d+ matches found:.*gaim.*\(stable')
            self.assertRegexp('debian version linux-wlan',
                              r'\d+ matches found:.*linux-wlan.*')
            self.assertRegexp('debian version --exact linux-wlan',
                              r'^No package.*\(all\)')
            self.assertNotError('debian version unstable')
            self.assertRegexp('debian version --branch stable unstable',
                              r'^No package.*')

        def testDebfile(self):
            self.assertHelp('debian file')
            self.assertRegexp('debian file oigrgrgregg',
                              r'^No filename.*\(stable\)')
            self.assertRegexp('debian file --branch unstable alkdjfad',
                r'^No filename.*\(unstable\)')
            self.assertResponse('debian file --exact --branch stable /bin/sh',
                    r'1 matches found: dash (stable)')
            self.assertRegexp('debian file --branch stable /bin/sh',
                              r'2 matches found:.*(?:dash.*|klibc-utils.*)')

        def testDebincoming(self):
            self.assertNotError('incoming')

        def testDebstats(self):
            self.assertNotError('stats supybot')


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('ERepublik')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('ERepublik', True)


ERepublik = conf.registerPlugin('ERepublik')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(ERepublik, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))

conf.registerGlobalValue(ERepublik, 'apikey',
    registry.String('', _("""The API key."""), private=True))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import re
import json

import string

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('ERepublik')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def flatten_subdicts(dicts, flat=None):
    """Change dict of dicts into a dict of strings/integers. Useful for
    using in string formatting."""
    if flat is None:
        # Instanciate the dictionnary when the function is run and now when it
        # is declared; otherwise the same dictionnary instance will be kept and
        # it will have side effects (memory exhaustion, ...)
        flat = {}
    if isinstance(dicts, list):
        return flatten_subdicts(dict(enumerate(dicts)))
    elif isinstance(dicts, dict):
        for key, value in dicts.items():
            if isinstance(value, dict):
                value = dict(flatten_subdicts(value))
                for subkey, subvalue in value.items():
                    flat['%s__%s' % (key, subkey)] = subvalue
            else:
                flat[key] = value
        return flat
    else:
        return dicts


class Template(string.Template):
    # Original string.Template does not accept variables starting with a
    # number.
    idpattern = r'[_a-z0-9]+'

class ERepublik(callbacks.Plugin):
    threaded = True


    ##############################################################
    # Battle
    ##############################################################

    class battle(callbacks.Commands):
        def _get(self, irc, name):
            key = conf.supybot.plugins.ERepublik.apikey()
            if not key:
                irc.error(_('No API key set. Ask the owner to add one.'),
                        Raise=True)
            try:
                base = 'http://api.erpk.org/battle/%s.json?key=%s'
                data = json.load(utils.web.getUrlFd(base % (name, key)))
                return data
            except:
                irc.error(_('This battle does not exist.'), Raise=True)

        def _advinfo(self, irc, msg, args, format_, name):
            """<format> <id>

            Returns informations about a battle with advanced formating."""
            battle = flatten_subdicts(self._get(irc, name))
            repl = lambda x:Template(x).safe_substitute(battle)
            irc.replies(map(repl, format_.split('\\n')))
        advinfo = wrap(_advinfo, ['something', 'int'])

        def active(self, irc, msg, args):
            """takes no arguments

            Returns list of active battles."""
            key = conf.supybot.plugins.ERepublik.apikey()
            base = 'http://api.erpk.org/battle/active.json?key=%s'
            data = json.load(utils.web.getUrlFd(base % key))
            irc.reply(format('%L', map(str, data)))
        active = wrap(active)

        def calc(self, irc, msg, args, name):
            """<name|id>

            Calculates how many damages you can make in one hit."""
            citizen = ERepublik.citizen()._get(irc, name)
            rank = citizen['rank']['level']
            strength = citizen['strength']
            dmg = (((float (rank-1) / 20) + 0.3) * ((strength / 10) +40))
            format_ = 'Q%i: \x02%i\x02'
            irc.reply(', '.join(map(lambda x: format_ % (x, dmg*(1+(0.2*x))),
                xrange(0, 8))))
        calc = wrap(calc, ['text'])


        def _gen(format_, name, doc):
            format_ = re.sub('[ \n]+', ' ', format_)
            def f(self, irc, msg, args, *ids):
                self._advinfo(irc, msg, args, format_, *ids)
            f.__doc__ = """<id>

            %s""" % doc
            return wrap(f, ['int'], name=name)
            
        battle = _gen("""Region: \x02\x0310$region__name\x02 \x03(URL:\x02\x0310 $url\x03\x02)\x0310,\\n\x03Total Points: \x02\x0310$attacker__name\x03 .: \x0310$attacker__points \x03.::. \x0304$defender__points \x03:.\x0304 $defender__name. """,
        'battle',
        'Returns general informations about a battle.')

    ##############################################################
    # Citizen
    ##############################################################

    class citizen(callbacks.Commands):
        def _get(self, irc, name):
            key = conf.supybot.plugins.ERepublik.apikey()
            if not key:
                irc.error(_('No API key set. Ask the owner to add one.'),
                        Raise=True)
            try:
                if name.isdigit():
                    base = 'http://api.erpk.org/citizen/profile/%s.json?key=%s'
                    data = json.load(utils.web.getUrlFd(base % (name, key)))
                    color = 3 if data['online'] else 4
                    data['name'] = '\x030%i%s\x0f' % (color, data['name'])
                    return data
                else:
                    base = 'http://api.erpk.org/citizen/search/%s/1.json?key=%s'
                    data = json.load(utils.web.getUrlFd(base % (name, key)))
                    return self._get(irc, str(data[0]['id']))
            except:
                irc.error(_('This citizen does not exist.'), Raise=True)

        def _advinfo(self, irc, msg, args, format_, name):
            """<format> <name|id>

            Returns informations about a citizen with advanced formating."""
            citizen = flatten_subdicts(self._get(irc, name), flat={
                    'party__name': 'None',
                    'party__id': 0,
                    'party__role': 'N/A',
                    'army__name': 'None',
                    'army__id': 0,
                    'army__role': 'N/A',
                    })
            repl = lambda x:Template(x).safe_substitute(citizen)
            irc.replies(map(repl, format_.split('\\n')))
        advinfo = wrap(_advinfo, ['something', 'text'])

        def _gen(format_, name, doc):
            format_ = re.sub('[ \n]+', ' ', format_)
            def f(self, irc, msg, args, *ids):
                self._advinfo(irc, msg, args, format_, *ids)
            f.__doc__ = """<name|id>

            %s""" % doc
            return wrap(f, ['text'], name=name)

        info = _gen("""\x02Name: $name (ID:\x0310 $id\x03)\x0310,\x03 Level: \x0310$level,\x03 Strength:\x0310 $strength,\x03 Residence:
        \x0310$residence__region__name, $residence__country__name,\x03 Citizenship:
        \x0310$citizenship__name,\x03 Rank: \x0310$rank__name,\x03 Party: \x0310$party__name,\x03 MU:
        \x0310$army__name.
        """,
        'info',
        'Returns general informations about a citizen.')

        link = _gen("""\x02$name's link\x0310 <->\x03 http://www.erepublik.com/sq/citizen/profile/$id    """,
        'link',
        'Returns link informations about a citizen.')

        donate = _gen("""\x02$name's donate link\x0310 <->\x03 http://www.erepublik.com/sq/economy/donate-items/$id    """,
        'donate',
        'Returns link to danate.')

        avatar = _gen("""\x02$name's avatar link\x0310 <->\x03 $avatar    """,
        'avatar',
        'Returns avatar link of citizen.')

        @internationalizeDocstring
        def medals(self, irc, msg, args, name):
            """<name|id>

            Displays the citizen's medals."""
            citizen = self._get(irc, name)
            medals = ['%s (%i)' % x for x in citizen['medals'].items() if x[1]]
            irc.reply(_('%s has the following medal(s): %s') %
                      (name, ', '.join(medals)))
        medals = wrap(medals, ['text'])


    ##############################################################
    # Country
    ##############################################################

    class country(callbacks.Commands):
        def _get(self, irc, name):
            key = conf.supybot.plugins.ERepublik.apikey()
            if not key:
                irc.error(_('No API key set. Ask the owner to add one.'),
                        Raise=True)
            try:
                base = 'http://api.erpk.org/country/%s/%s.json?key=%s'
                data = json.load(utils.web.getUrlFd(base %
                    (name, 'economy', key)))
                data.update(json.load(utils.web.getUrlFd(base %
                    (name, 'society', key))))
                return data
            except:
                irc.error(_('This country does not exist.'), Raise=True)

        def _advinfo(self, irc, msg, args, format_, name):
            """<format> <code>

            Returns informations about a country with advanced formating."""
            country = flatten_subdicts(self._get(irc, name))
            repl = lambda x:Template(x).safe_substitute(country)
            irc.replies(map(repl, format_.split('\\n')))
        advinfo = wrap(_advinfo, ['something', 'something'])

        def _gen(format_, name, doc):
            format_ = re.sub('[ \n]+', ' ', format_)
            def f(self, irc, msg, args, *ids):
                self._advinfo(irc, msg, args, format_, *ids)
            f.__doc__ = """<code>

            %s""" % doc
            return wrap(f, ['something'], name=name)
            
        society = _gen("""\x02Country: \x0310$name \x03(URL:\x0310 http://www.erepublik.com/en/country/society/$name\x03) \\n\x02\x03Active citizens \x0310$active_citizens,000\x03, \x03Online now \x0310$online_now\x03, \x03New citizens today \x0310$new_citizens_today\x03. """,
        'society',
        'Returns link informations about a citizen.')

        economy = _gen("""\x02Country: \x0310$name \x03(URL:\x0310 http://www.erepublik.com/en/country/economy/$name\x03) \\n\x02\x03Economy \x0310$treasury__gold Gold - $treasury__cc CC \x03, \x03Taxes import: -Food \x0310$taxes__food__import\x03, -Weapons \x0310$taxes__weapons__import\x03, -Tickets \x0310$taxes__tickets__import\x03, -Frm \x0310$taxes__frm__import\x03, -Wrm \x0310$taxes__wrm__import\x03, -Hospital \x0310$taxes__hospital__import\x03, -Defense \x0310$taxes__defense__import\x03. """,
        'society',
        'Returns link informations about a citizen.')


    ##############################################################
    # Job market
    ##############################################################

    class jobmarket(callbacks.Commands):
        def _get(self, irc, country, page):
            page = page or 1
            key = conf.supybot.plugins.ERepublik.apikey()
            if not key:
                irc.error(_('No API key set. Ask the owner to add one.'),
                        Raise=True)
            try:
                base = 'http://api.erpk.org/jobmarket/%s.json?key=%s'
                ids = '/'.join((country, str(page)))
                data = json.load(utils.web.getUrlFd(base % (ids, key)))
                return data
            except:
                irc.error(_('This job market does not exist.'), Raise=True)

        def _advinfo(self, irc, msg, args, format_,
                country, industry, quality, page):
            """<format> <country> [<page>]

            Returns informations about a job market with advanced formating."""
            jobmarket = flatten_subdicts(self._get(irc, name))
            repl = lambda x:Template(x).safe_substitute(jobmarket)
            irc.replies(map(repl, format_.split('\\n')))
        advinfo = wrap(_advinfo, ['something', 'something', optional('int')])

        def _gen(format_, name, doc):
            format_ = re.sub('[ \n]+', ' ', format_)
            def f(self, irc, msg, args, *ids):
                self._advinfo(irc, msg, args, format_, *ids)
            f.__doc__ = """<format> <country> [<page>]

            %s""" % doc
            return wrap(f, ['something', optional('int')], name=name)


    ##############################################################
    # Market
    ##############################################################

    class market(callbacks.Commands):
        def _get(self, irc, country, industry, quality, page):
            page = page or 1
            key = conf.supybot.plugins.ERepublik.apikey()
            if not key:
                irc.error(_('No API key set. Ask the owner to add one.'),
                        Raise=True)
            try:
                base = 'http://api.erpk.org/market/%s.json?key=%s'
                ids = '/'.join((country, industry, str(quality), str(page)))
                data = json.load(utils.web.getUrlFd(base % (ids, key)))
                return data
            except:
                irc.error(_('This market does not exist.'), Raise=True)

        def _advinfo(self, irc, msg, args, format_, *ids):
            """<format> <country> <industry> <quality> [<page>]

            Returns informations about a market with advanced formating."""
            market = flatten_subdicts(self._get(irc, *ids))
            repl = lambda x:Template(x).safe_substitute(market)
            irc.replies(map(repl, format_.split('\\n')))
        advinfo = wrap(_advinfo, ['something', 'something', 'something',
            'int', optional('int')])

        def _gen(format_, name, doc):
            format_ = re.sub('[ \n]+', ' ', format_)
            def f(self, irc, msg, args, *ids):
                self._advinfo(irc, msg, args, format_, *ids)
            f.__doc__ = """<format> <country> <industry> <quality> [<page>]

            %s""" % doc
            return wrap(f, ['something', 'something', 'int', optional('int')],
                    name=name)


    ##############################################################
    # Mu
    ##############################################################

    class mu(callbacks.Commands):
        def _get(self, irc, name):
            key = conf.supybot.plugins.ERepublik.apikey()
            if not key:
                irc.error(_('No API key set. Ask the owner to add one.'),
                        Raise=True)
            try:
                base = 'http://api.erpk.org/mu/%s.json?key=%s'
                data = json.load(utils.web.getUrlFd(base % (name, key)))
                return data
            except:
                irc.error(_('This Military Unit does not exist.'), Raise=True)

        def _advinfo(self, irc, msg, args, format_, name):
            """<format> <id>

            Returns informations about a Military Unit with advanced formating."""
            mu = flatten_subdicts(self._get(irc, name))
            repl = lambda x:Template(x).safe_substitute(mu)
            irc.replies(map(repl, format_.split('\\n')))
        advinfo = wrap(_advinfo, ['something', 'int'])

        def _gen(format_, name, doc):
            format_ = re.sub('[ \n]+', ' ', format_)
            def f(self, irc, msg, args, *ids):
                self._advinfo(irc, msg, args, format_, *ids)
            f.__doc__ = """<id>

            %s""" % doc
            return wrap(f, ['int'], name=name)


    ##############################################################
    # Party
    ##############################################################

    class party(callbacks.Commands):
        def _get(self, irc, name):
            key = conf.supybot.plugins.ERepublik.apikey()
            if not key:
                irc.error(_('No API key set. Ask the owner to add one.'),
                        Raise=True)
            try:
                base = 'http://api.erpk.org/party/%s.json?key=%s'
                data = json.load(utils.web.getUrlFd(base % (name, key)))
                return data
            except:
                irc.error(_('This party does not exist.'), Raise=True)

        def _advinfo(self, irc, msg, args, format_, name):
            """<format> <id>

            Returns informations about a party with advanced formating."""
            party = flatten_subdicts(self._get(irc, name))
            repl = lambda x:Template(x).safe_substitute(party)
            irc.replies(map(repl, format_.split('\\n')))
        advinfo = wrap(_advinfo, ['something', 'int'])

        def _gen(format_, name, doc):
            format_ = re.sub('[ \n]+', ' ', format_)
            def f(self, irc, msg, args, *ids):
                self._advinfo(irc, msg, args, format_, *ids)
            f.__doc__ = """<id>

            %s""" % doc
            return wrap(f, ['int'], name=name)

ERepublik = internationalizeDocstring(ERepublik)
Class = ERepublik


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class ERepublikTestCase(PluginTestCase):
    plugins = ('ERepublik',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Eureka')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Eureka', True)


Eureka = conf.registerPlugin('Eureka')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Eureka, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))

conf.registerGroup(Eureka, 'format')
conf.registerChannelValue(Eureka.format, 'score',
    registry.String('$nick ($score)', _("""Determines the format used by the
    bot to display the score of a user.""")))
conf.registerChannelValue(Eureka.format, 'separator',
    registry.String(' // ', _("""Determines the string between two
    user scores.""")))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import os
import re
import time
import operator
import threading

import supybot.log as log
import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.schedule as schedule
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Eureka')

STATE_STOPPED = 1
STATE_STARTED = 2
STATE_PAUSED = 3

class State:
    def __init__(self, filename):
        self.state = STATE_STOPPED
        self.scores = {}
        self.issue = 0
        filename = os.path.abspath(filename)
        self.fd = open(filename)
        self._waitingForAnswer = threading.Event()

    _matchQuestion = re.compile('(?P<value>[0-9]+) (?P<question>.*)')
    _matchClue = re.compile('(?P<delay>[0-9]+) (?P<clue>.*)')
    _matchAnswer = re.compile('(?P<mode>[a-z]) (?P<answer>.*)')
    def loadBlock(self):
        self._waitingForAnswer.clear()
        self._waitingForAnswer = threading.Event()
        self.question = None
        self.answers = []
        if self.issue is None: # Previous question didn't expire
            for line in self.fd:
                line = line.strip()
                if line.startswith('=== '):
                    break
        self.issue = None
        for line in self.fd:
            line = line.strip()
            if line == '---':
                break
            elif line != '':
                match = self._matchQuestion.match(line)
                if match is None:
                    log.error('Bad question format for question %r: %r' %
                            (self.question, line))
                    continue
                (value, question) = match.group('value', 'question')
                # We are sure that value is an integer, thanks to the regexp
                self.question = (int(value), question)
                self._waitingForAnswer.set()
        if self.question == '':
            self.state = STATE_STOPPED
            return

        for line in self.fd:
            line = line.strip()
            if line == '---':
                break
            elif line != '':
                match = self._matchAnswer.match(line)
                if match is None:
                    log.error('Bad answer format for question %r: %r' %
                            (self.question, line))
                    continue
                (mode, answer) = match.group('mode', 'answer')
                if mode == 'r':
                    pass
                elif mode == 'm':
                    answer = re.compile(answer)
                else:
                    log.error('Unsupported mode: %r. Only \'r\' (raw)'% mode +
                            'is supported for the moment.')
                    continue
                self.answers.append((mode, answer))


    def getClue(self):
        for line in self.fd:
            line = line.strip()
            if line.startswith('=== '):
                try:
                    self.issue = int(line[4:])
                except ValueError:
                    log.error('Bad end of block for question %r: %r' %
                            (self.question, line))
                return (self.issue, None, None) # No more clue
            elif line != '':
                match = self._matchClue.match(line)
                if match is None:
                    log.error('Bad clue format for question %r: %r' %
                            (self.question, line))
                    continue
                (delay, clue) = match.group('delay', 'clue')
                # We are sure that delay is an integer, thanks to the
                # regexp
                return (int(delay), clue, self._waitingForAnswer)

    def adjust(self, nick, count):
        assert isinstance(count, int)
        if nick not in self.scores:
            self.scores[nick] = count
        else:
            self.scores[nick] += count

@internationalizeDocstring
class Eureka(callbacks.Plugin):
    """Add the help for "@plugin help Eureka" here
    This should describe *how* to use this plugin."""

    states = {}

    def _ask(self, irc, channel, now=False):
        assert channel in self.states, \
            'Asked to ask on a channel where Eureka is not enabled.'
        state = self.states[channel]
        def event():
            state.loadBlock()
            if state.question is None:
                state.state = STATE_STOPPED
                return
            irc.reply(state.question[1], prefixNick=False)

            self._giveClue(irc, channel)
        if now:
            event()
        else:
            schedule.addEvent(event, time.time() + state.issue,
                    'Eureka-ask-%s' % channel)

    def _giveClue(self, irc, channel, now=False):
        state = self.states[channel]
        (delay, clue, valid) = state.getClue()
        def event():
            try:
                schedule.removeEvent('Eureka-nextClue-%s' % channel)
            except KeyError:
                pass
            if clue is None:
                assert valid is None
                irc.reply(_('Nobody replied with (one of this) '
                    'answer(s): %r.') %
                    ', '.join([y for x,y in state.answers
                               if x == 'r']),
                    prefixNick=False)
                self._ask(irc, channel)
            else:
                irc.reply(_('Another clue: %s') % clue, prefixNick=False)
                self._giveClue(irc, channel)
        eventName = 'Eureka-nextClue-%s' % channel
        if now and eventName in schedule.schedule.events:
            schedule.schedule.events[eventName]()
            schedule.removeEvent(eventName)
        schedule.addEvent(event, time.time() + delay, eventName)

    def doPrivmsg(self, irc, msg):
        channel = msg.args[0]
        nick = msg.prefix.split('!')[0]
        if channel not in self.states:
            return
        reply = None
        state = self.states[channel]
        for mode, answer in state.answers:
            if mode == 'r':
                if msg.args[1].lower() == answer.lower():
                    state.adjust(nick, state.question[0])
                    reply = _('Congratulations %s! The answer was %r.')
                    reply %= (nick, answer)
            elif mode == 'm':
                if answer.match(msg.args[1]):
                    state.adjust(nick, state.question[0])
                    reply = _('Congratulations %s! The answer was %r.')
                    reply %= (nick, msg.args[1])
        if reply is not None:
            schedule.removeEvent('Eureka-nextClue-%s' % channel)
            otherAnswers = [y for x,y in state.answers
                    if x == 'r' and y.lower() != msg.args[1].lower()]
            if len(otherAnswers) == 1:
                reply += ' ' + _('Another valid answer is: \'%s\'.')
                reply %= otherAnswers[0]
            elif len(otherAnswers) >= 2:
                reply += ' ' + _('Other valid answers are: \'%s\'.')
                reply %= '\', \''.join([x for x in otherAnswers])
            irc.reply(reply, prefixNick=False)
            self._ask(irc, channel, True)


    @internationalizeDocstring
    def scores(self, irc, msg, args, channel):
        """[<channel>]

        Return the scores on the <channel>. If <channel> is not given, it
        defaults to the current channel."""
        if channel not in self.states:
            irc.error(_('Eureka is not enabled on this channel'))
            return
        scores = list(self.states[channel].scores.items())
        if scores == []:
            irc.reply(_('Noone played yet.'))
        else:
            scores.sort(key=operator.itemgetter(1))
            scores.reverse()
            irc.reply(', '.join(['%s(%i)' % x for x in scores]))
    scores = wrap(scores, ['channel'])

    @internationalizeDocstring
    def score(self, irc, msg, args, channel, nick):
        """[<channel>] <nick>

        Return the score of <nick> on the <channel>. If <channel> is not
        given, it defaults to the current channel."""
        if channel not in self.states:
            irc.error(_('Eureka is not enabled on this channel'))
            return
        state = self.states[channel]
        if nick not in state.scores:
            irc.error(_('This user did not play yet.'))
            return
        irc.reply(str(state.scores[nick]))
    score = wrap(score, ['channel', 'nick'])

    @internationalizeDocstring
    def start(self, irc, msg, args, channel):
        """[<channel>]

        Start the Eureka on the given <channel>. If <channel> is not given,
        it defaults to the current channel."""
        if channel in self.states and \
                self.states[channel].state != STATE_STOPPED:
            irc.error(_('Eureka is already enabled on this channel'))
            return
        state = State(os.path.join(conf.supybot.directories.data(),
            'Eureka.%s.questions' % channel))
        state.state = STATE_STARTED
        self.states[channel] = state
        self._ask(irc, channel, True)
    start = wrap(start, ['op'])

    @internationalizeDocstring
    def stop(self, irc, msg, args, channel):
        """[<channel>]

        Stop the Eureka on the given <channel>. If <channel> is not given,
        it defaults to the current channel."""
        if channel not in self.states or \
                self.states[channel].state == STATE_STOPPED:
            irc.error(_('Eureka is not enabled on this channel'))
            return
        self.states[channel].state = STATE_STOPPED
        schedule.removeEvent('Eureka-nextClue-%s' % channel)
        irc.replySuccess()
    stop = wrap(stop, ['op'])

    @internationalizeDocstring
    def pause(self, irc, msg, args, channel):
        """[<channel>]

        Pause the Eureka on the given <channel>. If <channel> is not given,
        it defaults to the current channel."""
        if channel not in self.states or \
                self.states[channel].state == STATE_STOPPED:
            irc.error(_('Eureka is not enabled on this channel'))
            return
        state = self.states[channel]
        if state.state == STATE_PAUSED:
            irc.error(_('Eureka is already paused.'))
            return
        state.state = STATE_PAUSED
        schedule.removeEvent('Eureka-nextClue-%s' % channel)
        irc.replySuccess()
    pause = wrap(pause, ['op'])

    @internationalizeDocstring
    def resume(self, irc, msg, args, channel):
        """[<channel>]

        Resume the Eureka on the given <channel>. If <channel> is not given,
        it defaults to the current channel."""
        if channel not in self.states or \
                self.states[channel].state == STATE_STOPPED:
            irc.error(_('Eureka is not enabled on this channel'))
            return
        state = self.states[channel]
        if state.state != STATE_PAUSED:
            irc.error(_('Eureka is not paused.'))
            return
        state.state = STATE_STARTED
        self._giveClue(irc, channel, True)
    resume = wrap(resume, ['op'])

    @internationalizeDocstring
    def adjust(self, irc, msg, args, channel, nick, count):
        """[<channel>] <nick> <number>

        Increase or decrease the score of <nick> on the <channel>.
        If <channel> is not given, it defaults to the current channel."""
        self.states[channel].adjust(nick, count)
        irc.replySuccess()
    adjust = wrap(adjust, ['op', 'nick', 'int'])

    @internationalizeDocstring
    def skip(self, irc, msg, args, channel):
        """[<channel>]

        Give up with this question, and switch to the next one."""
        if channel not in self.states or \
                self.states[channel].state == STATE_STOPPED:
            irc.error(_('Eureka is not enabled on this channel'))
            return
        try:
            schedule.removeEvent('Eureka-nextClue-%s' % channel)
        except KeyError:
            pass
        self._ask(irc, channel, True)
    skip = wrap(skip, ['op'])

    @internationalizeDocstring
    def clue(self, irc, msg, args, channel):
        """[<channel>]

        Give the next clue."""
        self._giveClue(irc, channel, True)
    clue = wrap(clue, ['op'])

Class = Eureka


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from __future__ import with_statement

from supybot.test import *
import supybot.conf as conf
import supybot.schedule as schedule

class EurekaTestCase(ChannelPluginTestCase):
    plugins = ('Eureka', 'User')

    _unpickleScore = re.compile(conf.supybot.plugins.Eureka.format.score() \
            .replace('$nick', '(?P<nick>[^ ]+)') \
            .replace('$score', '(?P<score>[^ ]+)'))
    def _unpickleScores(self, raw):
        rawScores = raw.split(conf.supybot.plugins.Eureka.format.separator)
        scores = {}
        for rawScore in rawScores:
            (nick, score) = _unpickleScore.group('nick', 'score')
            scores[nick] = score
        return scores
    def _clearMsg(self):
        msg = 1
        while msg is not None:
            msg = self.irc.takeMsg()

    def setUp(self):
        # Avoid conflicts between tests.
        # We use .keys() in order to prevent this error:
        # RuntimeError: dictionary changed size during iteration
        for name in list(schedule.schedule.events.keys()):
            schedule.removeEvent(name)
        self.prefix1 = 'test!user@host.domain.tld'
        self.prefix2 = 'foo!bar@baz'
        self.prefix3 = 'toto!titi@tata'
        self.prefix4 = 'spam!egg@lol'
        path = conf.supybot.directories.data()
        self._path = os.path.join(os.path.abspath(path),
                'Eureka.%s.questions' % self.channel)
        ChannelPluginTestCase.setUp(self)
        with open(self._path, 'a') as fd:
            fd.write("""
            2 Who wrote this plugin?
            ---
            r ProgVal
            ---
            5 P***V**
            5 Pr**Va*
            2 Pro*Val
            === 5

            4 What is the name of this bot?
            ---
            r Limnoria
            r Supybot
            ---
            5 L******a
            2 Li****ia
            2 Lim**ria
            === 5

            3 Who is the original author of Supybot?
            ---
            r jemfinch
            ---
            1 j*******
            1 jem*****
            === 1

            1 Give a number.
            ---
            r 42
            m [0-9]+
            ---
            === 2

            1 Give another number.
            ---
            r 42
            m [0-9]+
            ---
            === 2
            """)
        self.prefix = self.prefix1 # Just to be sure

    def testStartStop(self):
        self.assertError('scores')
        self.assertError('score')
        self.assertError('skip')
        self.assertError('stop')
        self.assertError('pause')
        self.assertError('resume')

        self.assertNotError('start')
        self._clearMsg()
        self.assertNotError('stop')
        self.assertNotError('start')
        self._clearMsg()

        self.assertError('start')
        self.assertNotError('scores')
        self.assertNotError('skip')
        self.assertError('resume')
        self.assertNotError('stop')
        self.assertNotError('start')

        self.assertNotError('pause')

        self.assertNotError('resume')
        self.assertError('resume')
        self.assertNotError('pause')
        self.assertError('pause')
        self.assertNotError('skip')

        self.assertNotError('stop')
        self.assertError('resume')

    def testBasics(self):
        msg = ircmsgs.privmsg(self.channel, 'foo', prefix=self.prefix)
        self.irc.feedMsg(msg)
        self.assertNoResponse(' ')

        self.assertResponse('start', 'Who wrote this plugin?')

        msg = ircmsgs.privmsg(self.channel, 'foo', prefix=self.prefix)
        self.irc.feedMsg(msg)
        self.assertNoResponse(' ')

        msg = ircmsgs.privmsg(self.channel, 'ProgVal', prefix=self.prefix)
        self.irc.feedMsg(msg)
        self.assertResponse(' ', 'Congratulations test! The answer was '
                '\'ProgVal\'.')

        self.assertResponse(' ', 'What is the name of this bot?')
        msg = ircmsgs.privmsg(self.channel, 'Limnoria', prefix=self.prefix2)
        self.irc.feedMsg(msg)
        self.assertResponse(' ', 'Congratulations foo! The answer was '
                '\'Limnoria\'. Another valid answer is: \'Supybot\'.')

        self.assertResponse(' ', 'Who is the original author of Supybot?')
        self.timeout = 0.2
        self.assertNoResponse(' ', 0.9)
        self.assertResponse(' ', 'Another clue: j*******')
        self.assertNoResponse(' ', 0.9)
        self.assertResponse(' ', 'Another clue: jem*****')
        self.assertNoResponse(' ', 0.9)
        self.assertResponse(' ', 'Nobody replied with (one of this) '
                'answer(s): \'jemfinch\'.')

        self.timeout = 1
        self.assertResponse(' ', 'Give a number.')
        msg = ircmsgs.privmsg(self.channel, 'foo', prefix=self.prefix)
        self.irc.feedMsg(msg)
        self.assertNoResponse(' ')
        msg = ircmsgs.privmsg(self.channel, '12', prefix=self.prefix)
        self.irc.feedMsg(msg)
        self.assertResponse(' ', 'Congratulations test! The answer was \'12\'. '
                'Another valid answer is: \'42\'.')

        self.timeout = 1
        self.assertResponse(' ', 'Give another number.')
        msg = ircmsgs.privmsg(self.channel, 'foo', prefix=self.prefix)
        self.irc.feedMsg(msg)
        self.assertNoResponse(' ')
        msg = ircmsgs.privmsg(self.channel, '42', prefix=self.prefix)
        self.irc.feedMsg(msg)
        self.assertResponse(' ', 'Congratulations test! The answer was '
                '\'42\'.')

        self.assertError('stop')
        self.assertError('pause')
        self.assertError('resume')
        self.assertNotError('start')

    def testCaseSensitivity(self):
        self.assertNotError('start')
        self._clearMsg()
        msg = ircmsgs.privmsg(self.channel, 'PROGVAL', prefix=self.prefix)
        self.irc.feedMsg(msg)
        self.assertResponse(' ', 'Congratulations test! The answer was '
                '\'ProgVal\'.')
    def testAdjust(self):
        self.assertNotError('start')
        self.assertRegexp('scores', 'noone')
        self.assertError('score foo')
        self.assertError('score bar')
        self.assertError('score baz')
        self.assertNotError('adjust foo 5')
        self.assertResponse('scores', 'foo(5)')
        self.assertResponse('score foo', '5')
        self.assertError('score bar')
        self.assertError('score baz')
        self.assertNotError('adjust bar 2')
        self.assertResponse('scores', 'foo(5), bar(2)')
        self.assertResponse('score foo', '5')
        self.assertResponse('score bar', '2')
        self.assertError('score baz')
        self.assertNotError('adjust bar 7')
        self.assertResponse('scores', 'bar(9), foo(5)')
        self.assertResponse('score foo', '5')
        self.assertResponse('score bar', '9')
        self.assertError('score baz')
    def testClue(self):
        self.timeout = 0.2
        self.assertResponse('start', 'Who wrote this plugin?')
        self.assertResponse('clue', 'Another clue: P***V**')
    def testScore(self):
        self.assertNotError('start')
        self.assertRegexp('scores', 'noone')
        self.assertError('score test')
        msg = ircmsgs.privmsg(self.channel, 'foo', prefix=self.prefix)
        self.irc.feedMsg(msg)
        self.assertRegexp('scores', 'noone')
        self.assertError('score test')
        msg = ircmsgs.privmsg(self.channel, 'ProgVal', prefix=self.prefix)
        self.irc.feedMsg(msg)
        self._clearMsg()
        self.assertResponse('scores', 'test(2)')
        msg = ircmsgs.privmsg(self.channel, 'ProgVal', prefix=self.prefix)
        self.irc.feedMsg(msg)
        self._clearMsg()
        self.assertResponse('scores', 'test(2)')
        self.prefix = self.prefix2
        msg = ircmsgs.privmsg(self.channel, 'supybot', prefix=self.prefix)
        self.irc.feedMsg(msg)
        self._clearMsg()
        self.assertResponse('scores', 'foo(4), test(2)')
        self.prefix = self.prefix1
        msg = ircmsgs.privmsg(self.channel, 'jemfinch', prefix=self.prefix)
        self.irc.feedMsg(msg)
        self._clearMsg()
        self.assertResponse('scores', 'test(5), foo(4)')



# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('GitHub')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('GitHub', True)


GitHub = conf.registerPlugin('GitHub')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(GitHub, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))
conf.registerGroup(GitHub, 'api')
conf.registerGlobalValue(GitHub.api, 'url',
        registry.String('https://api.github.com', _("""The URL of the
        GitHub API to use. You probably don't need to edit it, but I let it
        there, just in case.""")))
conf.registerGlobalValue(GitHub, 'announces',
        registry.String('', _("""You shouldn't edit this configuration
        variable yourself, unless you know what you do. Use '@Github announce
        add' or '@Github announce remove' instead.""")))

conf.registerGroup(GitHub, 'format')
conf.registerChannelValue(GitHub.format, 'push',
        registry.String('echo ' +
        _('$repository__owner__name/\x02$repository__name\x02 '
        '(in \x02$ref__branch\x02): $__commit__author__name committed '
        '\x02$__commit__message__firstline\x02 $__commit__url__tiny') \
        .replace('\n        ', ' '),
        _("""Format for push events.""")))
conf.registerChannelValue(GitHub.format, 'commit_comment',
        registry.String('echo ' +
        _('$repository__owner__name/\x02$repository__name\x02 '
        '(in \x02$ref__branch\x02): $__comment__user__login commented on '
        'commit \x02$__commit__message__firstline\x02 $comment__html_url__tiny') \
        .replace('\n        ', ' '),
        _("""Format for commit comment events.""")))
conf.registerChannelValue(GitHub.format, 'issues',
        registry.String('echo ' +
        _('$repository__owner__login/\x02$repository__name\x02: '
        '\x02$sender__login\x02 $action issue #$issue__number: '
        '\x02$issue__title\x02 $issue__html_url') \
        .replace('\n        ', ' '),
        _("""Format for issue events.""")))
conf.registerChannelValue(GitHub.format, 'issue_comment',
        registry.String('echo ' +
        _('$repository__owner__login/\x02$repository__name\x02: '
        '\x02$sender__login\x02 $action comment on issue #$issue__number: '
        '\x02$issue__title\x02 $issue__url__tiny') \
        .replace('\n        ', ' '),
        _("""Format for issue comment events.""")))
conf.registerChannelValue(GitHub.format, 'status',
        registry.String('echo ' +
        _('$repository__owner__login/\x02$repository__name\x02: Status '
        'for commit "\x02$commit__commit__message__firstline\x02" '
        'by \x02$commit__commit__committer__name\x02: \x02$description\x02 '
        '$target_url__tiny') \
        .replace('\n        ', ' '),
        _("""Format for status events.""")))
conf.registerChannelValue(GitHub.format, 'pull_request',
        registry.String('echo ' +
        _('$repository__owner__login/\x02$repository__name\x02: '
        '\x02$sender__login\x02 $action pull request #$number (to '
        '\x02$pull_request__base__ref\x02): \x02$pull_request__title\x02 '
        '$pull_request__html_url__tiny') \
        .replace('\n        ', ' '),
        _("""Format for pullrequest events.""")))
conf.registerChannelValue(GitHub.format, 'pull_request_review_comment',
        registry.String('echo ' +
        _('$repository__owner__login/\x02$repository__name\x02: '
        '\x02$comment__user__login\x02 reviewed pull request #$number (to '
        '\x02$pull_request__base__ref\x02): \x02$pull_request__title\x02 '
        '$pull_request__html_url__tiny') \
        .replace('\n        ', ' '),
        _("""Format for pull_request review comment events.""")))

for event_type in ('create', 'delete', 'deployment',
        'deployment_status', 'download', 'follow', 'fork', 'fork_apply',
        'gist', 'gollum', 'member', 'public',
        'pull_request_review_comment', 'release',
        'team_add', 'watch'):
    conf.registerChannelValue(GitHub.format, event_type,
            registry.String('', _("""Format for %s events.""") % event_type))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011-2014, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import sys
import json
import time
import urllib
import socket
import threading
from string import Template
import supybot.log as log
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.httpserver as httpserver

if sys.version_info[0] < 3:
    from cStringIO import StringIO
    quote_plus = urllib.quote_plus
else:
    from io import StringIO
    quote_plus = urllib.parse.quote_plus
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('GitHub')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

if sys.version_info[0] >= 3:
    def b(s):
        return s.encode('utf-8')
    def u(s):
        return s
    urlencode = urllib.parse.urlencode
else:
    def u(s):
        return s.decode('utf-8')
    def b(s):
        return s
    urlencode = urllib.urlencode

def flatten_subdicts(dicts, flat=None):
    """Change dict of dicts into a dict of strings/integers. Useful for
    using in string formatting."""
    if flat is None:
        # Instanciate the dictionnary when the function is run and now when it
        # is declared; otherwise the same dictionnary instance will be kept and
        # it will have side effects (memory exhaustion, ...)
        flat = {}
    if isinstance(dicts, list):
        return flatten_subdicts(dict(enumerate(dicts)))
    elif isinstance(dicts, dict):
        for key, value in dicts.items():
            if isinstance(value, dict):
                value = dict(flatten_subdicts(value))
                for subkey, subvalue in value.items():
                    flat['%s__%s' % (key, subkey)] = subvalue
            else:
                flat[key] = value
        return flat
    else:
        return dicts

#####################
# Server stuff
#####################

class GithubCallback(httpserver.SupyHTTPServerCallback):
    name = "GitHub announce callback"
    defaultResponse = _("""
    You shouldn't be here, this subfolder is not for you. Go back to the
    index and try out other plugins (if any).""")
    def doPost(self, handler, path, form):
        if not handler.address_string().endswith('.rs.github.com') and \
                not handler.address_string().endswith('.cloud-ips.com') and \
                not handler.address_string() == 'localhost' and \
                not handler.address_string().startswith('127.0.0.') and \
                not handler.address_string().startswith('192.30.252.') and \
                not handler.address_string().startswith('204.232.175.'):
            log.warning("""'%s' tried to act as a web hook for Github,
            but is not GitHub.""" % handler.address_string())
            self.send_response(403)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b('Error: you are not a GitHub server.'))
        else:
            headers = dict(self.headers)
            try:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b('Thanks.'))
            except socket.error:
                pass
            if 'X-GitHub-Event' in headers:
                event = headers['X-GitHub-Event']
            else:
                # WTF?
                event = headers['x-github-event']
            if event == 'ping':
                log.info('Got ping event from GitHub.')
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b('Thanks.'))
                return
            self.plugin.announce.onPayload(headers, json.loads(form['payload'].value))

#####################
# API access stuff
#####################

def query(caller, type_, uri_end, args):
    args = dict([(x,y) for x,y in args.items() if y is not None])
    url = '%s/%s/%s?%s' % (caller._url(), type_, uri_end,
                           urlencode(args))
    if sys.version_info[0] >= 3:
        return json.loads(utils.web.getUrl(url).decode('utf8'))
    else:
        return json.load(utils.web.getUrlFd(url))

#####################
# Plugin itself
#####################

instance = None

@internationalizeDocstring
class GitHub(callbacks.Plugin):
    """Add the help for "@plugin help GitHub" here
    This should describe *how* to use this plugin."""

    def __init__(self, irc):
        global instance
        self.__parent = super(GitHub, self)
        callbacks.Plugin.__init__(self, irc)
        instance = self

        callback = GithubCallback()
        callback.plugin = self
        httpserver.hook('github', callback)
        for cb in self.cbs:
            cb.plugin = self

        if 'reply_env' not in ircmsgs.IrcMsg.__slots__:
            log.error("Your version of Supybot is not compatible with "
                      "reply environments. So, the GitHub plugin won't "
                      "be able to announce events from GitHub.")



    class announce(callbacks.Commands):
        def _shorten_url(self, url):
            try:
                data = urlencode({'url': url})
                if sys.version_info[0] >= 3:
                    data = data.encode()
                    f = utils.web.getUrlFd('http://git.io/', data=data)
                    url = list(filter(lambda x:x[0] == 'Location',
                        f.headers._headers))[0][1].strip()
                else:
                    f = utils.web.getUrlFd('http://git.io/', data=data)
                    url = filter(lambda x:x.startswith('Location: '),
                            f.headers.headers)[0].split(': ', 1)[1].strip()
            except Exception as e:
                log.error('Cannot connect to git.io: %s' % e)
                return None
            return url
        def _createPrivmsg(self, irc, channel, payload, event, hidden=None):
            bold = ircutils.bold

            format_ = self.plugin.registryValue('format.%s' % event, channel)
            if not format_.strip():
                return
            repl = flatten_subdicts(payload)
            try_gitio = True
            for (key, value) in dict(repl).items():
                if key.endswith('url'):
                    if try_gitio:
                        url = self._shorten_url(value)
                    else:
                        url = None
                    if url:
                        repl[key + '__tiny'] = url
                    else:
                        repl[key + '__tiny'] = value
                        try_gitio = False
                elif key.endswith('ref'):
                    try:
                        repl[key + '__branch'] = value.split('/', 2)[2]
                    except IndexError:
                        pass
                elif isinstance(value, str) or \
                        (sys.version_info[0] < 3 and isinstance(value, unicode)):
                    repl[key + '__firstline'] = value.split('\n', 1)[0]
            repl.update({'__hidden': hidden or 0})
            #if hidden is not None:
            #    s += _(' (+ %i hidden commits)') % hidden
            #if sys.version_info[0] < 3:
            #        s = s.encode('utf-8')
            tokens = callbacks.tokenize(format_)
            if not tokens:
                return
            fake_msg = ircmsgs.IrcMsg(command='PRIVMSG',
                    args=(channel, 'GITHUB'), prefix='github!github@github',
                    reply_env=repl)
            try:
                self.plugin.Proxy(irc, fake_msg, tokens)
            except Exception as  e:
                self.plugin.log.exception('Error occured while running triggered command:')

        def onPayload(self, headers, payload):
            if 'reply_env' not in ircmsgs.IrcMsg.__slots__:
                log.error("Got event payload from GitHub, but your version "
                          "of Supybot is not compatible with reply "
                          "environments, so, the GitHub plugin can't "
                          "announce it.")
            if 'full_name' in payload['repository']:
                repo = payload['repository']['full_name']
            elif 'name' in payload['repository']['owner']:
                repo = '%s/%s' % (payload['repository']['owner']['name'],
                                  payload['repository']['name'])
            else:
                repo = '%s/%s' % (payload['repository']['owner']['login'],
                                  payload['repository']['name'])
            if 'X-GitHub-Event' in headers:
                event = headers['X-GitHub-Event']
            else:
                # WTF?
                event = headers['x-github-event']
            announces = self._load()
            repoAnnounces = []
            for (dbRepo, network, channel) in announces:
                if dbRepo == repo:
                    repoAnnounces.append((network, channel))
            if len(repoAnnounces) == 0:
                log.info('Commit for repo %s not announced anywhere' % repo)
                return
            for (network, channel) in repoAnnounces:
                # Compatability with DBs without a network
                if network == '':
                    for irc in world.ircs:
                        if channel in irc.state.channels:
                            break
                else:
                    irc = world.getIrc(network)
                    if not irc:
                        log.warning('Received GitHub payload with announcing '
                                    'enabled in %s on unloaded network %s.',
                                    channel, network)
                        return
                if channel not in irc.state.channels:
                    log.info(('Cannot announce event for repo '
                             '%s in %s on %s because I\'m not in %s.') %
                             (repo, channel, irc.network, channel))
                if event == 'push':
                    commits = payload['commits']
                    if len(commits) == 0:
                        log.warning('GitHub push hook called without any commit.')
                    else:
                        hidden = None
                        last_commit = commits[-1]
                        if last_commit['message'].startswith('Merge ') and \
                                len(commits) > 5:
                            hidden = len(commits) + 1
                            commits = [last_commit]
                        payload2 = dict(payload)
                        for commit in commits:
                            payload2['__commit'] = commit
                            self._createPrivmsg(irc, channel, payload2,
                                    'push', hidden)
                else:
                    self._createPrivmsg(irc, channel, payload, event)

        def _load(self):
            announces = instance.registryValue('announces').split(' || ')
            if announces == ['']:
                return []
            announces = [x.split(' | ') for x in announces]
            output = []
            for annc in announces:
                repo = annc[0]
                # Compatibility with old DBs without a network set
                if len(annc) < 3:
                    net = ''
                    chan = annc[1]
                else:
                    net = annc[1]
                    chan = annc[2]
                output.append((repo, net, chan))
            return output

        def _save(self, data):
            stringList = []
            for announcement in data:
                stringList.extend([' | '.join(announcement)])
            string = ' || '.join(stringList)
            instance.setRegistryValue('announces', value=string)

        @internationalizeDocstring
        def add(self, irc, msg, args, channel, owner, name):
            """[<channel>] <owner> <name>

            Announce the commits of the GitHub repository called
            <owner>/<name> in the <channel>.
            <channel> defaults to the current channel."""
            repo = '%s/%s' % (owner, name)
            announces = self._load()
            for (dbRepo, net, chan) in announces:
                if dbRepo == repo and\
                        (net == '' or net == irc.network) and\
                        chan == channel:
                    irc.error(_('This repository is already announced to '
                                'this channel.'))
                    return
            announces.append((repo, irc.network, channel))
            self._save(announces)
            irc.replySuccess()
        add = wrap(add, ['channel', 'something', 'something'])

        @internationalizeDocstring
        def remove(self, irc, msg, args, channel, owner, name):
            """[<channel>] <owner> <name>

            Don't announce the commits of the GitHub repository called
            <owner>/<name> in the <channel> anymore.
            <channel> defaults to the current channel."""
            repo = '%s/%s' % (owner, name)
            announces = self._load()
            for annc in announces:
                if annc[0] == repo and\
                        (annc[1] == '' or annc[1] == irc.network) and\
                        annc[2] == channel:
                    announces.remove(annc)
                    self._save(announces)
                    irc.replySuccess()
                    return
            irc.error(_('This repository is not yet announced to this '
                        'channel.'))
        remove = wrap(remove, ['channel', 'something', 'something'])



    class repo(callbacks.Commands):
        def _url(self):
            url = instance.registryValue('api.url')
            if url == 'http://github.com/api/v2/json': # old api
                url = 'https://api.github.com'
                instance.setRegistryValue('api.url', value=url)
            return url

        @internationalizeDocstring
        def search(self, irc, msg, args, search, optlist):
            """<searched string> [--page <id>] [--language <language>]

            Searches the string in the repository names database. You can
            specify the page <id> of the results, and restrict the search
            to a particular programming <language>."""
            args = {'page': None, 'language': None}
            for name, value in optlist:
                if name in args:
                    args[name] = value
            results = query(self, 'legacy/repos/search',
                    quote_plus(search), args)
            reply = ' & '.join('%s/%s' % (x['owner'], x['name'])
                               for x in results['repositories'])
            if reply == '':
                irc.error(_('No repositories matches your search.'))
            else:
                irc.reply(u(reply))
        search = wrap(search, ['something',
                               getopts({'page': 'id',
                                        'language': 'somethingWithoutSpaces'})])
        @internationalizeDocstring
        def info(self, irc, msg, args, owner, name, optlist):
            """<owner> <repository> [--enable <feature> <feature> ...] \
            [--disable <feature> <feature>]

            Displays informations about <owner>'s <repository>.
            Enable or disable features (ie. displayed data) according to the
            request)."""
            enabled = ['watchers', 'forks', 'pushed_at', 'open_issues',
                       'description']
            for mode, features in optlist:
                features = features.split(' ')
                for feature in features:
                    if mode == 'enable':
                        enabled.append(feature)
                    else:
                        try:
                            enabled.remove(feature)
                        except ValueError:
                            # No error is raised, because:
                            # 1. it wouldn't break anything
                            # 2. it enhances cross-compatiblity
                            pass
            results = query(self, 'repos', '%s/%s' % (owner, name), {})
            output = []
            for key, value in results.items():
                if key in enabled:
                    output.append('%s: %s' % (key, value))
            irc.reply(u(', '.join(output)))
        info = wrap(info, ['something', 'something',
                           getopts({'enable': 'anything',
                                    'disable': 'anything'})])
    def die(self):
        self.__parent.die()
        httpserver.unhook('github')


Class = GitHub


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class GitHubTestCase(PluginTestCase):
    plugins = ('GitHub', 'Config')
    def testAnnounceAdd(self):
        self.assertNotError('config supybot.plugins.GitHub.announces ""')
        self.assertNotError('github announce add #foo ProgVal Limnoria')
        self.assertResponse('config supybot.plugins.GitHub.announces',
                            'ProgVal/Limnoria | test | #foo')
        self.assertNotError('github announce add #bar ProgVal Supybot-plugins')
        self.assertResponse('config supybot.plugins.GitHub.announces',
                            'ProgVal/Limnoria | test | #foo || '
                            'ProgVal/Supybot-plugins | test | #bar')


    def testAnnounceRemove(self):
        self.assertNotError('config supybot.plugins.GitHub.announces '
                            'ProgVal/Limnoria | test | #foo || '
                            'ProgVal/Supybot-plugins | #bar')
        self.assertNotError('github announce remove #foo ProgVal Limnoria')
        self.assertResponse('config supybot.plugins.GitHub.announces',
                            'ProgVal/Supybot-plugins |  | #bar')
        self.assertNotError('github announce remove #bar '
                            'ProgVal Supybot-plugins')
        self.assertResponse('config supybot.plugins.GitHub.announces', ' ')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Glob2Chan', True)


Glob2Chan = conf.registerPlugin('Glob2Chan')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Glob2Chan, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))
conf.registerGlobalValue(Glob2Chan, 'nowelcome', registry.String('',
    '''List of nick that doesn't get the welcome message.'''))
conf.registerGlobalValue(Glob2Chan, 'gamers', registry.String('',
    '''List of nick that are notified when someone calls @ask4game.'''))
conf.registerGlobalValue(Glob2Chan, 'helpers', registry.String('',
    '''List of nick that are notified when someone calls @ask4help.'''))



# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
# -*- coding: utf8 -*-
###
# Copyright (c) 2010-2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from __future__ import unicode_literals
import sys

GEOIP_PATH ='/usr/share/GeoIP/GeoIP.dat' 
from . import pygeoip
from . import pycountry

import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.httpserver as httpserver

class Glob2ChanCallback(httpserver.SupyHTTPServerCallback):
    name = "Glob2 server notifications"
    defaultResponse = """
    You shouldn't be there, this subfolder is not for you. Go back to the
    index and try out other plugins (if any)."""
    def doGet(self, handler, path):
        host = handler.address_string()
        if host in ('localhost', '127.0.0.1', '::1'):
            assert path.startswith('/status/')
            status = path[len('/status/'):].replace('/', ' ')
            self.plugin._announce(ircutils.bold('[YOG]') +
                    ' YOG server at %s is %s.' % (host, status))
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Channel notified.')
        else:
            self.send_response(403)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not authorized.')

instance = None

class Glob2Chan(callbacks.Plugin):
    def __init__(self, irc):
        global instance
        self.__parent = super(Glob2Chan, self)
        callbacks.Plugin.__init__(self, irc)
        instance = self

        callback = Glob2ChanCallback()
        callback.plugin = self
        httpserver.hook('glob2', callback)
        self._users = {}
    def die(self):
        self.__parent.die()
        httpserver.unhook('glob2')

    def _announce(self, message):
        for irc in world.ircs:
            if '#glob2' in irc.state.channels:
                break
        assert '#glob2' in irc.state.channels
        irc.queueMsg(ircmsgs.privmsg('#glob2', message))

    def doJoin(self, irc, msg):
        channel = msg.args[0]
        if channel != '#glob2':
            return
        nick = msg.nick
        self._users.update({msg.nick: msg.prefix.split('@')[1]})
        if nick.startswith('[YOG]'):
            irc.queueMsg(ircmsgs.IrcMsg(s='WHOIS %s' % nick))

    def do311(self, irc, msg):
        nick = msg.args[1]
        if not nick.startswith('[YOG]') or nick in self.registryValue('nowelcome').split(' '):
            return
        realname = msg.args[5]
        hostname = self._users.pop(nick)
        try:
            version = 'Glob2 version %s' % realname.split('-')[1]
        except:
            version = 'unknown version'
        if not utils.net.isIP(hostname):
            hostname = utils.net.getAddressFromHostname(hostname)
        code = pygeoip.Database(GEOIP_PATH).lookup(hostname).country
        country = pycountry.countries.get(alpha2=code).name
        if code == 'FR':
            irc.queueMsg(ircmsgs.privmsg(nick, ('Bonjour %s, bienvenue dans le '
                'salon de jeu Globulation2 en ligne. Il y a actuellement %i '
                'personnes connectées via IRC, elles pourraient se réveiller et '
                'jouer avec vous. Attendez ici au moins quelques minutes, '
                'quelqu\'un pourrait se connecter d\'ici là.') %
                (nick, len(irc.state.channels['#glob2'].users))))
            irc.queueMsg(ircmsgs.privmsg(nick, ('Si vous avez une question ou '
                'que vous voulez programmer une partie, vous pouvez contacter '
                'ProgVal à l\'adresse progval (arobase) progval (point) '
                'net.')))
        else:
            irc.queueMsg(ircmsgs.privmsg(nick, ('Hi %s, welcome to the '
                'globulation online game room. There are currently %i '
                'people connected via IRC, they may awaken and challenge '
                'you to a game. Please stay here at least a few minutes, '
                'someone may connect in the meantime.') %
                (nick, len(irc.state.channels['#glob2'].users))))
            irc.queueMsg(ircmsgs.privmsg(nick, ('If you have any question or '
                'want to schedule a game, feel free to contact ProgVal at '
                'progval at progval dot net.')))
        irc.queueMsg(ircmsgs.privmsg('#glob2', ('Welcome to %s, running %s '
            'and connecting from %s.') % (nick, version, country)))

    def g2help(self, irc, msg, args, mode):
        """[{irc|yog}]

        Prints help for IRC/YOG users."""
        channel = msg.args[0]
        if channel != '#glob2':
            return
        nick = msg.nick
        if mode is None and nick.startswith('[YOG]'):
            mode = 'yog'
        elif mode is None:
            mode = 'irc'
        if mode == 'yog':
            irc.reply('\x02(help for YOG users:)\x02 If you are fed up with '
                'getting a welcome message each time you log in, type '
                '"\x02@nowelcome\x02". '
                'If you want to send an automatic alert to everybody '
                'who wants to play but who is not reading the chat, type '
                '"\x02@ask4game\x02". For more information, ask for help, with '
                'typing "\x02@ask4help\x02".')
        elif mode == 'irc':
            irc.reply('\x02(help for IRC users:)\x02 If you want to be notified each '
                'time someone uses "\x02@ask4game\x02" (game query) or "\x02@ask4help\x02" '
                '(help query), type "\x02@subscribe ask4game\x02" or "\x02@subscribe '
                'ask4help\x02" (depending on what you want). The opposite of '
                '"\x02@subscribe\x02" is "\x02@unsubscribe\x02".')
        else:
            irc.error('Modes can are only "irc" and "yog"')
        irc.reply('I am a Supybot-powered IRC bot. Don\'t try to talk or play '
                  'with me ;) If you have questions, bug reports, feature '
                  'requests, ... ask my owner, he is \x02ProgVal\x02. '
                  'You can find stats about this channel '
                  'at \x02http://openihs.org:7412/webstats/global/glob2/\x02')
    g2help = wrap(g2help, [optional('somethingWithoutSpaces')])

    def nowelcome(self, irc, msg, args):
        """takes no arguments

        Disable the welcome message"""
        channel = msg.args[0]
        if channel != '#glob2':
            return
        nick = msg.nick
        if not nick.startswith('[YOG]'):
            irc.error('You are not a YOG user, so, their is no reason I send '
                'you a welcome message, but you ask me to stop sending them '
                'to you. Are you crazy?')
            return
        self.setRegistryValue('nowelcome', value='%s %s' %
                (self.registryValue('nowelcome'), nick))
        irc.reply('I will not send you again the welcome message')
    nowelcome = wrap(nowelcome, [])

    def ask4game(self, irc, msg, args):
        """takes no arguments

        Notifies the gamers who subscribed to the alert list you want
        to play."""
        channel = msg.args[0]
        if channel != '#glob2':
            return
        online = irc.state.channels[channel].users
        gamers = self.registryValue('gamers')
        onlineGamers = [x for x in online if x in gamers and x != msg.nick]
        if len(onlineGamers) == 0:
            irc.reply('Sorry, no registered gamer is online')
            return
        irc.reply('%s: %s' % (' & '.join(onlineGamers),
                              'Someone is asking for a game!'),
                  prefixNick=False)
    ask4game = wrap(ask4game, [])

    def ask4help(self, irc, msg, args):
        """takes no arguments

        Notifies the helers who subscribed to the alert list you want
        to play."""
        channel = msg.args[0]
        if channel != '#glob2':
            return
        online = irc.state.channels[channel].users
        helpers = self.registryValue('helpers')
        onlineHelpers = [x for x in online if x in helpers and x != msg.nick]
        if len(onlineHelpers) == 0:
            irc.reply('Sorry, no registered helper is online')
            return
        irc.reply('%s: %s' % (' & '.join(onlineHelpers),
                              'Someone is asking for help!'),
                  prefixNick=False)
    ask4help = wrap(ask4help, [])

    def subscribe(self, irc, msg, args, type_):
        """{ask4game|ask4help}

        Subscribes you to the gamers/helpers alert list."""
        channel = msg.args[0]
        if channel != '#glob2':
            return
        nick = msg.nick
        if type_ == 'ask4game':
            if nick in self.registryValue('gamers').split(' '):
                irc.error('You already subscribed to this list')
                return
            self.setRegistryValue('gamers', value='%s %s' %
                (self.registryValue('gamers'), nick))
        elif type_ == 'ask4help':
            if nick in self.registryValue('helpers').split(' '):
                irc.error('You already subscribed to this list')
                return
            self.setRegistryValue('helpers', value='%s %s' %
                (self.registryValue('helpers'), nick))
        else:
            irc.error('The only available subscriptions are ask4game and '
                'ask4help.')
        irc.reply('I will notify you each time someone uses %s.' % type_)
    subscribe = wrap(subscribe, ['somethingWithoutSpaces'])

    def unsubscribe(self, irc, msg, args, type_):
        """{ask4game|ask4help}

        Unsubscribes you from the gamers/helpers alert list."""
        channel = msg.args[0]
        if channel != '#glob2':
            return
        nick = msg.nick
        if type_ == 'ask4game':
            if nick not in self.registryValue('gamers').split(' '):
                irc.error('You didn\'t subscribe to this list')
                return
            nickslist = self.registryValue('gamers').split(' ')
            nickslist.remove(nick)
            self.setRegistryValue('gamers', value=' '.join(nickslist))
        elif type_ == 'ask4help':
            if nick in self.registryValue('helpers').split(' '):
                irc.error('You didn\'t subscribe to this list')
                return
            nickslist = self.registryValue('helpers').split(' ')
            nickslist.remove(nick)
            self.setRegistryValue('helpers', value=' '.join(nickslist))
        else:
            irc.error('The only available unsubscriptions are ask4game and '
                'ask4help.')
        irc.reply('I won\'t notify you each time someone uses %s anymore.' %
                  type_)
    unsubscribe = wrap(unsubscribe, ['somethingWithoutSpaces'])

Class = Glob2Chan


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = db
# vim:fileencoding=utf-8
# Copyright (c) 2008 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Generic database code."""

import logging
from xml.dom import minidom

logger = logging.getLogger('pycountry.db')


class Data(object):

    def __init__(self, element, **kw):
        self._element = element
        for key, value in kw.items():
            setattr(self, key, value)


class Database(object):

    # Override those names in sub-classes for specific ISO database.
    field_map = dict()
    data_class_base = Data
    data_class_name = None
    xml_tag = None
    no_index = []

    def __init__(self, filename):
        self.objects = []
        self.indices = {}

        self.data_class = type(self.data_class_name, (self.data_class_base,),
                               {})

        f = open(filename, 'rb')

        tree = minidom.parse(f)

        for entry in tree.getElementsByTagName(self.xml_tag):
            mapped_data = {}
            for key in entry.attributes.keys():
                mapped_data[self.field_map[key]] = (
                    entry.attributes.get(key).value)
            entry_obj = self.data_class(entry, **mapped_data)
            self.objects.append(entry_obj)

        tree.unlink()

        # Construct list of indices: primary single-column indices
        indices = []
        for key in self.field_map.values():
            if key in self.no_index:
                continue
            # Slightly horrible hack: to evaluate `key` at definition time of
            # the lambda I pass it as a keyword argument.
            getter = lambda x, key=key: getattr(x, key, None)
            indices.append((key, getter))

        # Create indices
        for name, _ in indices:
            self.indices[name] = {}

        # Update indices
        for obj in self.objects:
            for name, rule in indices:
                value = rule(obj)
                if value is None:
                    continue
                if value in self.indices[name]:
                    logger.error(
                        '%s %r already taken in index %r and will be '
                        'ignored. This is an error in the XML databases.' %
                        (self.data_class_name, value, name))
                self.indices[name][value] = obj

    def __iter__(self):
        return iter(self.objects)

    def __len__(self):
        return len(self.objects)

    def get(self, **kw):
        assert len(kw) == 1, 'Only one criteria may be given.'
        field, value = list(kw.items())[0]
        return self.indices[field][value]

########NEW FILE########
__FILENAME__ = tests
# vim:fileencoding=utf-8
# Copyright (c) 2008 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Test harness for pycountry."""

import doctest
import unittest


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocFileSuite('README.txt',
                                       optionflags=doctest.ELLIPSIS))
    return suite

########NEW FILE########
__FILENAME__ = pygeoip
#!/usr/bin/env python2.5

'''
Pure Python reader for GeoIP Country Edition databases.
'''

__author__ = 'David Wilson <dw@botanicus.net>'


import os
import sys
import struct

if sys.version_info[0] >= 3:
    from io import BytesIO
else:
    from cBytesIO import BytesIO as BytesIO


#
# Constants.
#

# From GeoIP.h.
SEGMENT_RECORD_LENGTH = 3
STANDARD_RECORD_LENGTH = 3
ORG_RECORD_LENGTH = 4
MAX_RECORD_LENGTH = 4
FULL_RECORD_LENGTH = 50
NUM_DB_TYPES = 20

GEOIP_COUNTRY_EDITION     = 1
GEOIP_REGION_EDITION_REV0 = 7
GEOIP_CITY_EDITION_REV0   = 6
GEOIP_ORG_EDITION         = 5
GEOIP_ISP_EDITION         = 4
GEOIP_CITY_EDITION_REV1   = 2
GEOIP_REGION_EDITION_REV1 = 3
GEOIP_PROXY_EDITION       = 8
GEOIP_ASNUM_EDITION       = 9
GEOIP_NETSPEED_EDITION    = 10
GEOIP_DOMAIN_EDITION      = 11
GEOIP_COUNTRY_EDITION_V6  = 12

COUNTRY_BEGIN = 16776960
STATE_BEGIN_REV0 = 16700000
STATE_BEGIN_REV1 = 16000000
STRUCTURE_INFO_MAX_SIZE = 20
DATABASE_INFO_MAX_SIZE = 100

GeoIP_country_code = '''
    AP EU AD AE AF AG AI AL AM AN AO AQ AR AS AT AU AW AZ BA BB BD BE BF BG BH
    BI BJ BM BN BO BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR
    CU CV CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR FX
    GA GB GD GE GF GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID
    IE IL IN IO IQ IR IS IT JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC
    LI LK LR LS LT LU LV LY MA MC MD MG MH MK ML MM MN MO MP MQ MR MS MT MU MV
    MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM
    PN PR PS PT PW PY QA RE RO RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO
    SR ST SV SY SZ TC TD TF TG TH TJ TK TM TN TO TL TR TT TV TW TZ UA UG UM US
    UY UZ VA VC VE VG VI VN VU WF WS YE YT RS ZA ZM ME ZW A1 A2 O1 AX GG IM JE
    BL MF
'''.split()

GeoIP_country_continent = '''
    AS EU EU AS AS SA SA EU AS SA AF AN SA OC EU OC SA AS EU SA AS EU AF EU AS
    AF AF SA AS SA SA SA AS AF AF EU SA NA AS AF AF AF EU AF OC SA AF AS SA SA
    SA AF AS AS EU EU AF EU SA SA AF SA EU AF AF AF EU AF EU OC SA OC EU EU EU
    AF EU SA AS SA AF EU SA AF AF SA AF EU SA SA OC AF SA AS AF SA EU SA EU AS
    EU AS AS AS AS AS EU EU SA AS AS AF AS AS OC AF SA AS AS AS SA AS AS AS SA
    EU AS AF AF EU EU EU AF AF EU EU AF OC EU AF AS AS AS OC SA AF SA EU AF AS
    AF NA AS AF AF OC AF OC AF SA EU EU AS OC OC OC AS SA SA OC OC AS AS EU SA
    OC SA AS EU OC SA AS AF EU AS AF AS OC AF AF EU AS AF EU EU EU AF EU AF AF
    SA AF SA AS AF SA AF AF AF AS AS OC AS AF OC AS AS SA OC AS AF EU AF OC NA
    SA AS EU SA SA SA SA AS OC OC OC AS AF EU AF AF EU AF -- -- -- EU EU EU EU
    SA SA
'''.split()


#
# Helper functions.
#

def addr_to_num(ip):
    '''
    Convert an IPv4 address from a string to its integer representation.

    @param[in]  ip      IPv4 address as a string.
    @returns            Address as an integer.
    '''

    try:
        w, x, y, z = map(int, ip.split('.'))
        if w>255 or x>255 or y>255 or z>255:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('%r is not an IPv4 address.' % (ip,))

    return (w << 24) | (x << 16) | (y << 8) | z


def num_to_addr(num):
    '''
    Convert an IPv4 address from its integer representation to a string.

    @param[in]  num     Address as an integer.
    @returns            IPv4 address as a string.
    '''

    return '%d.%d.%d.%d' % ((num >> 24) & 0xff,
                            (num >> 16) & 0xff,
                            (num >> 8) & 0xff,
                            (num & 0xff))

def latin1_to_utf8(string):
    return string.decode('latin-1').encode('utf-8')


def safe_lookup(lst, idx):
    if idx is None:
        return None
    return lst[idx]


#
# Classes.
#


class ReadBuffer(object):
    '''
    Utility to read data more easily.
    '''

    buffer = None

    def __init__(self, source, size, seek_offset=None, seek_whence=os.SEEK_SET):
        fp = BytesIO(source)
        if seek_offset is not None:
            fp.seek(seek_offset, seek_whence)
        self.buffer = fp.read(size)

    def read_string(self):
        '''
        Read a null-terminated string.

        @returns            Result as a string.
        '''
        result, self.buffer = self.buffer.split('\0', 1)
        return result

    def read_int(self, size):
        '''
        Read a multibyte integer.

        @param[in]  size    Number of bytes to read as an integer.
        @returns            Result as an integer.
        '''
        result = sum(ord(self.buffer[i]) << (8*i) for i in range(size))
        self.buffer = self.buffer[size:]
        return result


class AddressInfo(object):
    '''
    Representation of a database lookup result.
    '''

    __slots__ = [ 'ip', 'ipnum', 'prefix', 'country', 'continent' ]

    def __init__(self, ip=None, ipnum=None, prefix=None, country_id=None):
        self.ip = ip
        self.ipnum = ipnum
        self.prefix = prefix
        self.country = safe_lookup(GeoIP_country_code, country_id)
        self.continent = safe_lookup(GeoIP_country_continent, country_id)

    network = property(lambda self:
        num_to_addr(self.ipnum & ~((32-self.prefix)**2-1)))

    def __str__(self):
        return '[%s of network %s/%d in country %s]' %\
               (self.ip, self.network, self.prefix, self.country)


class BigAddressInfo(AddressInfo):
    '''
    Representation of a database lookup result with more info in it.
    '''

    # __slots__ is inherited and appended to.
    __slots__ = [ 'city', 'region', 'postal_code', 'metro_code', 'area_code', 'longitude', 'latitude' ]

    def __init__(self, ip=None, ipnum=None, prefix=None, country_id=None,
                 city=None, region=None, postal_code=None, metro_code=None, area_code=None,
                 longitude=None, latitude=None):
        AddressInfo.__init__(self, ip, ipnum, prefix, country_id)
        self.city = city or None
        self.region = region or None
        self.postal_code = postal_code or None
        self.metro_code = metro_code
        self.area_code = area_code
        self.longitude = longitude
        self.latitude = latitude

    def __str__(self):
        return '[%s of network %s/%d in city %s, %s]' %\
               (self.ip, self.network, self.prefix, self.city, self.country)


class Database(object):
    '''
    GeoIP database reader implementation. Currently only supports country
    edition.
    '''

    def __init__(self, filename):
        '''
        Initialize a new GeoIP reader instance.

        @param[in]  filename    Path to GeoIP.dat as a string.
        '''

        self.filename = filename
        self.cache = open(filename, 'rb').read()
        self._setup_segments()

        if self.db_type not in (GEOIP_COUNTRY_EDITION,
                                GEOIP_CITY_EDITION_REV0,
                                GEOIP_CITY_EDITION_REV1):
            raise NotImplementedError('Database edition is not supported yet; '
                                      'Please use a Country or City database.')

    def _setup_segments(self):
        self.segments = None

        # default to GeoIP Country Edition
        self.db_type = GEOIP_COUNTRY_EDITION
        self.record_length = STANDARD_RECORD_LENGTH

        fp = BytesIO(self.cache)
        fp.seek(-3, os.SEEK_END)

        for i in range(STRUCTURE_INFO_MAX_SIZE):
            delim = fp.read(3)

            if delim != '\xFF\xFF\xFF':
                fp.seek(-4, os.SEEK_CUR)
                continue

            self.db_type = ord(fp.read(1))

            # Region Edition, pre June 2003.
            if self.db_type == GEOIP_REGION_EDITION_REV0:
                self.segments = [STATE_BEGIN_REV0]

            # Region Edition, post June 2003.
            elif self.db_type == GEOIP_REGION_EDITION_REV1:
                self.segments = [STATE_BEGIN_REV1]

            # City/Org Editions have two segments, read offset of second segment
            elif self.db_type in (GEOIP_CITY_EDITION_REV0,
                                  GEOIP_CITY_EDITION_REV1,
                                  GEOIP_ORG_EDITION, GEOIP_ISP_EDITION,
                                  GEOIP_ASNUM_EDITION):
                self.segments = [0]

                for idx, ch in enumerate(fp.read(SEGMENT_RECORD_LENGTH)):
                    self.segments[0] += ord(ch) << (idx * 8)

                if self.db_type in (GEOIP_ORG_EDITION, GEOIP_ISP_EDITION):
                    self.record_length = ORG_RECORD_LENGTH

            break

        if self.db_type in (GEOIP_COUNTRY_EDITION, GEOIP_PROXY_EDITION,
                       GEOIP_NETSPEED_EDITION, GEOIP_COUNTRY_EDITION_V6):
            self.segments = [COUNTRY_BEGIN]

    def info(self):
        '''
        Return a string describing the loaded database version.

        @returns    English text string, or None if database is ancient.
        '''

        fp = BytesIO(self.cache)
        fp.seek(-3, os.SEEK_END)

        hasStructureInfo = False

        # first get past the database structure information
        for i in range(STRUCTURE_INFO_MAX_SIZE):
            if fp.read(3) == '\xFF\xFF\xFF':
                hasStructureInfo = True
                break

            fp.seek(-4, os.SEEK_CUR)

        if hasStructureInfo:
            fp.seek(-6, os.SEEK_CUR)
        else:
            # no structure info, must be pre Sep 2002 database, go back to end.
            fp.seek(-3, os.SEEK_END)

        for i in range(DATABASE_INFO_MAX_SIZE):
            if fp.read(3) == '\0\0\0':
                return fp.read(i)

            fp.seek(-4, os.SEEK_CUR)

    def _decode(self, buf, branch):
        '''
        @param[in]  buf         Record buffer.
        @param[in]  branch      1 for left, 2 for right.
        @returns                X.
        '''

        offset = 3 * branch
        if self.record_length == 3:
            return buf[offset] | (buf[offset+1] << 8) | (buf[offset+2] << 16)

        # General case.
        end = branch * self.record_length
        x = 0

        for j in range(self.record_length):
            x = (x << 8) | buf[end - j]

        return x

    def _seek_record(self, ipnum):
        fp = BytesIO(self.cache)
        offset = 0

        for depth in range(31, -1, -1):
            fp.seek(self.record_length * 2 * offset)
            buf = fp.read(self.record_length * 2)

            x = self._decode(buf, int(bool(ipnum & (1 << depth))))
            if x >= self.segments[0]:
                return 32 - depth, x

            offset = x

        assert False, \
            "Error Traversing Database for ipnum = %lu: "\
            "Perhaps database is corrupt?" % ipnum


    def _lookup_country(self, ip):
        "Lookup a country db entry."

        ipnum = addr_to_num(ip)
        prefix, num = self._seek_record(ipnum)

        num -= COUNTRY_BEGIN
        if num:
            country_id = num - 1
        else:
            country_id = None

        return AddressInfo(country_id=country_id, ip=ip, ipnum=ipnum, prefix=prefix)

    def _lookup_city(self, ip):
        "Look up a city db entry."

        ipnum = addr_to_num(ip)
        prefix, num = self._seek_record(ipnum)
        record, next_record_ptr = self._extract_record(num, None)
        return BigAddressInfo(ip=ip, ipnum=ipnum, prefix=prefix, **record)

    def _extract_record(self, seek_record, next_record_ptr):
        if seek_record == self.segments[0]:
            return {'country_id': None}, next_record_ptr

        seek_offset = seek_record + (2 * self.record_length - 1) * self.segments[0]
        record_buf = ReadBuffer(self.cache, FULL_RECORD_LENGTH, seek_offset)
        record = {}

        # get country
        record['country_id'] = record_buf.read_int(1) - 1

        # get region
        record['region'] = record_buf.read_string()

        # get city
        record['city'] = latin1_to_utf8(record_buf.read_string())

        # get postal code
        record['postal_code'] = record_buf.read_string()

        # get latitude
        record['latitude'] = record_buf.read_int(3) / 10000.0 - 180

        # get longitude
        record['longitude'] = record_buf.read_int(3) / 10000.0 - 180

        # get area code and metro code for post April 2002 databases and for US locations
        if (self.db_type == GEOIP_CITY_EDITION_REV1) and (GeoIP_country_code[record['country_id']] == 'US'):
            metro_area_combo = record_buf.read_int(3)
            record['metro_code'] = metro_area_combo / 1000
            record['area_code'] = metro_area_combo % 1000

        # Used for GeoIP_next_record (which this code doesn't have.)
        if next_record_ptr is not None:
            next_record_ptr = seek_record - len(record_buf)

        return record, next_record_ptr

    def lookup(self, ip):
        '''
        Lookup an IP address returning an AddressInfo (or BigAddressInfo)
        instance describing its location.

        @param[in]  ip      IPv4 address as a string.
        @returns            AddressInfo (or BigAddressInfo) instance.
        '''

        if self.db_type in (GEOIP_COUNTRY_EDITION, GEOIP_PROXY_EDITION, GEOIP_NETSPEED_EDITION):
            return self._lookup_country(ip)
        elif self.db_type in (GEOIP_CITY_EDITION_REV0, GEOIP_CITY_EDITION_REV1):
            return self._lookup_city(ip)




if __name__ == '__main__':
    import time, sys

    dbfile = 'GeoIP.dat'
    if len(sys.argv) > 1:
        dbfile = sys.argv[1]

    t1 = time.time()
    db = Database(dbfile)
    t2 = time.time()

    print(db.info())

    t3 = time.time()

    tests = '''
        127.0.0.1
        83.198.135.28
        83.126.35.59
        192.168.1.1
        194.168.1.255
        196.25.210.14
        64.22.109.113
    '''.split()

    for test in tests:
        addr_info = db.lookup(test)
        print(addr_info)
        if isinstance(addr_info, BigAddressInfo):
            print("   ", dict((key, getattr(addr_info, key)) for key in dir(addr_info) if not key.startswith('_')))

    t4 = time.time()

    print("Open: %dms" % ((t2-t1) * 1000,))
    print("Info: %dms" % ((t3-t2) * 1000,))
    print("Lookup: %dms" % ((t4-t3) * 1000,))

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *
import supybot.ircmsgs as ircmsgs

class Glob2ChanTestCase(PluginTestCase):
    plugins = ('Glob2Chan',)



# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf8 -*-
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('GoodFrench', True)


GoodFrench = conf.registerPlugin('GoodFrench')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(GoodFrench, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))
conf.registerChannelValue(GoodFrench, 'kick',
    registry.Boolean(False, """Détermine si un utilisateur faisant une faute
    de Français sera kické (au lieu de recevoir un avertissement)."""))
conf.registerChannelValue(GoodFrench, 'level',
    registry.Integer(0, """Le niveau de filtrage. Le niveau N filtre
    ce que le niveau N-1 filtrait, avec des choses en plus.
    0 : pas de filtrage ;
    1 : filtre le langage SMS
    2 : filtre les erreurs de pluriel ;
    3 : filtre les fautes de conjugaison courantes ;
    4 : filtre les fautes d'orthographe courantes ;
    5 : filtre les abbréviations ("t'as" au lieu de "tu as") ;
    6 : filtre les erreurs de typographie (note : a tendance à avoir la
    gachette facile)
    7 : filtre les 'lol'"""))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
# -*- coding: utf8 -*-
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import re
import supybot.world as world
import supybot.ircmsgs as ircmsgs
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

class SpellChecker:
    def __init__(self, text, level):
        # 0 : pas de filtrage ;
        # 1 : filtre le langage SMS
        # 2 : filtre les erreurs de pluriel ;
        # 3 : filtre les fautes de conjugaison courantes ;
        # 4 : filtre les fautes d'orthographe courantes ;
        # 5 : filtre les abbréviations ("t'as" au lieu de "tu as")
        self._text = text
        self._errors = []
        if level >= 1:
            self._checking = 'SMS'
            self.checkSMS()
        if level >= 2:
            self._checking = 'pluriel'
            self.checkPlural()
        if level >= 3:
            self._checking = 'conjugaison'
            self.checkConjugaison()
        if level >= 4:
            self._checking = 'orthographe'
            self.checkSpelling()
        if level >= 5:
            self._checking = 'abbréviation'
            self.checkAbbreviation()
        if level >= 6:
            self._checking = 'typographie'
            self.checkTypographic()
        if level >= 7:
            self._checking = 'lol'
            self.checkLol()

    def _raise(self, message):
        self._errors.append('[%s] %s' % (self._checking, message))

    def _detect(self, mode, correct, mask, displayedMask=None, wizard=' '):
        if displayedMask is None:
            displayedMask = mask
        raise_ = False
        text = re.sub('[a-zA-Z0-9]+://[^ ]+', '', self._text)
        nickRemover = re.match('[^ ]*: (?P<text>.*)', text)
        if nickRemover is not None:
            text = nickRemover.group('text')
        text = '%s%s%s' % (wizard, text, wizard)
        AntislashDoubleYou = '[^a-zA-Z0-9éèàùâêûôîäëüïöç’\']'
        if mode == 'single' and re.match('.*%s%s%s.*' % (AntislashDoubleYou,
                                                        mask,
                                                        AntislashDoubleYou),
                                         text, re.IGNORECASE) is not None:
            raise_ = True
        elif mode == 'regexp' and re.match('.*%s.*' % mask, text):
            raise_ = True

        if raise_:
            if self._checking == 'conjugaison' or \
            self._checking == 'typographie':
                self._raise(correct)
            else:
                if correct.__class__ == list:
                    correct = '« %s »' % ' » , ou « '.join(correct)
                else:
                    correct = '« %s »' % correct

                if displayedMask.__class__ == list:
                    displayedMask = '« %s »' % ' » ou « '.join(displayedMask)
                else:
                    displayedMask = '« %s »' % displayedMask
                self._raise('On ne dit pas %s mais %s' %
                           (displayedMask, correct))

    def checkSMS(self):
        bad = {
                't': 't\'es',
                'ki': 'qui',
                'koi': 'quoi',
                'tqvu': 't\'as vu',
                'tt': 'tout',
                'ct': 'c\'était',
                'v': 'vais',
                'twa': 'toi',
                'toa': 'toi',
                'mwa': 'moi',
                'moa': 'moi',
                'tro': 'trop',
                'bi1': 'bien',
                'çay': 'c\'est',
                'fé': ['fais', 'fait'],
                'm': ['aime', 'aimes', 'aiment'],
                'u': ['eu', 'eut'],
            }
        for mask, correct in bad.items():
            self._detect(mode='single', correct=correct, mask=mask)

        self._detect(mode='regexp', correct="c'est",
                     mask="(?<!(du|Du|le|Le|en|En)) C (?<!c')",
                     displayedMask='C')

    def checkPlural(self):
        pass
    def checkConjugaison(self):
        self._detect(mode='regexp', correct="tu as oublié un « ne » ou un « n’ »",
                     mask="(je|tu|on|il|elle|nous|vous|ils|elles) [^'’ ]+ pas ")
        self._detect(mode='regexp', correct="tu as oublié un « ne » ou un « n’ »",
                     mask="j'[^'’ ]+ pas")
        firstPerson = 'un verbe à la première personne ne finit pas par un « t »'
        notAS = 'ce verbe ne devrait pas se finir par un « s » à cette personne.'
        self._detect(mode='regexp', correct=firstPerson, mask="j'[^ ]*t\W")
        self._detect(mode='regexp', correct=firstPerson,mask="je( ne)? [^ ]*t\W")
        self._detect(mode='regexp', correct=notAS,
                     mask=" (il|elle|on)( ne | n['’]| )[^ ]*[^u]s\W")
                     # [^u] is added in order to not detect 'il [vn]ous...'
    def checkSpelling(self):
        self._detect(mode='regexp', correct='quelle', mask='quel [^ ]+ la',
                     displayedMask='quel')
        self._detect(mode='regexp', correct='quel', mask='quelle [^ ]+ le',
                     displayedMask='quelle')
        self._detect(mode='regexp', correct=['quels', 'quelles'],
                     mask='quel [^ ]+ les',
                     displayedMask='quel')
        self._detect(mode='regexp', correct=['quels', 'quelles'],
                     mask='quelle [^ ]+ les',
                     displayedMask='quelle')
        self._detect(mode='single',
                     correct=['quel', 'quels', 'quelle', 'quelles'],
                     mask='kel')
        self._detect(mode='single',
                     correct=['quel', 'quels', 'quelle', 'quelles'],
                     mask='kelle')
        self._detect(mode='single',
                     correct=['quel', 'quels', 'quelle', 'quelles'],
                     mask='kels')
        self._detect(mode='single',
                     correct=['quel', 'quels', 'quelle', 'quelles'],
                     mask='kelles')
    def checkAbbreviation(self):
        pass
    def checkLol(self):
        self._detect(mode='regexp', correct='mdr', mask='[Ll1][oO0iu]+[lL1]',
                     displayedMask='lol')
        self._detect(mode='regexp', correct='mdr', mask=' [Ll1] +[lL1] ',
                     displayedMask='lol')
    def checkTypographic(self):
        self._detect(mode='regexp',
                     correct="Un caractère de ponctuation double est toujours "
                     "précédé d'une espace",
                     mask="[a-zA-Z0-9]{2}[:!?;][^/]", wizard='_')
        self._detect(mode='regexp',
                     correct="Un caractère de ponctuation double est toujours "
                     "suivi d'une espace",
                     mask="(?<!(tp|ps|.[^ a-zA-Z]))[:!?;][a-zA-Z0-9]{2}", wizard='_')
        self._detect(mode='regexp',
                     correct="Un caractère de ponctuation simple n'est jamais "
                     "précédé d'une espace",
                     mask=" ,", wizard='_')
        self._detect(mode='regexp',
                     correct="Un caractère de ponctuation simple est toujours "
                     "suivi d'une espace",
                     mask=",[^ _]", wizard='_')

    def getErrors(self):
        return self._errors

class GoodFrench(callbacks.Plugin):
    def detect(self, irc, msg, args, text):
        """<texte>

        Cherche des fautes dans le <texte>, en fonction de la valeur locale de
        supybot.plugins.GoodFrench.level."""
        checker = SpellChecker(text, self.registryValue('level', msg.args[0]))
        errors = checker.getErrors()
        if len(errors) == 0:
            irc.reply('La phrase semble correcte')
        elif len(errors) == 1:
            irc.reply('Il semble y avoir une erreur : %s' % errors[0])
        else:
            irc.reply('Il semble y avoir des erreurs : %s' %
                      ' | '.join(errors))
    def doPrivmsg(self, irc, msg):
        channel = msg.args[0]
        text = msg.args[1]
        prefix = msg.prefix
        nick = prefix.split('!')[0]
        if callbacks.addressed(irc.nick, msg): #message is direct command
            return

        checker = SpellChecker(text, self.registryValue('level', channel))
        errors = checker.getErrors()
        if len(errors) == 0:
            return
        elif len(errors) == 1:
            reason = 'Erreur : %s' % errors[0]
        else:
            reason = 'Erreurs : %s' % ' | '.join(errors)
        if self.registryValue('kick'):
            msg = ircmsgs.kick(channel, nick, reason)
            irc.queueMsg(msg)
        else:
            irc.reply(reason)

    detect = wrap(detect, ['text'])


Class = GoodFrench


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
# -*- coding: utf8 -*-
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class GoodFrenchTestCase(ChannelPluginTestCase):
    plugins = ('GoodFrench',)
    config = {'plugins.GoodFrench.level': 7, 'plugins.GoodFrench.kick': True}

    def _isKicked(self):
        m = self.irc.takeMsg()
        while m is not None:
            if m.command == 'KICK':
                return True
            m = self.irc.takeMsg()
        return False

    _bad = "C tt"
    _good = "C'est tout"

    def testDetect(self):
        self.assertRegexp("GoodFrench detect %s" % self._bad, 'erreurs : ')
        self.assertRegexp("GoodFrench detect %s" % self._good, 'correcte')

    def testKick(self):
        msg = ircmsgs.privmsg(self.channel, self._bad,
                              prefix=self.prefix)
        self.irc.feedMsg(msg)
        self.failIf(self._isKicked() == False, 'Not kicked on misspell')

        msg = ircmsgs.privmsg(self.channel, self._good,
                              prefix=self.prefix)
        self.irc.feedMsg(msg)
        self.failIf(self._isKicked(), 'Kicked on correct sentence')

    def assertMistake(self, text):
        try:
            self.assertRegexp("GoodFrench detect %s" % text, 'erreurs? : ')
        except AssertionError as e:
            raise e

    def testMistakes(self):
        for text in ["je suis pas là", "j'ai pas faim", "j'ait", "je ait",
                     "il es", "quel est la", "quelle est le",
                     "C'est bon; il est parti", "C'est bon , il est parti",
                     "C'est bon ,il est parti", "C'est bon ;il est parti",
                     "lol", "loooool", "LOOO00ool", "10001"]:
            self.assertMistake(text)

    def assertNoMistake(self, text):
        try:
            self.assertRegexp("GoodFrench detect %s" % text, 'correcte')
        except AssertionError as e:
            raise e

    def testNotMistakes(self):
        for text in ["je ne suis pas là", "je n'ai pas faim", "j'ai",
                     "il est", "quelle est la", "quel est le", "je sais",
                     "C'est bon ; il est parti", "C'est bon, il est parti"]:
            self.assertNoMistake(text)



# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry

try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('GUI')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('GUI', True)


GUI = conf.registerPlugin('GUI')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(GUI, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))
conf.registerGlobalValue(GUI, 'host',
    registry.String('127.0.0.1', _("""The host the server will bind.""")))
conf.registerGlobalValue(GUI, 'port',
    registry.Integer(14789, _("""The port the server will bind.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = connection
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'connection.ui'
#
# Created: Sat Feb 12 14:04:00 2011
#      by: PyQt4 UI code generator 4.7.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_connection(object):
    def setupUi(self, connection):
        connection.setObjectName("connection")
        connection.resize(400, 153)
        self.formLayout = QtGui.QFormLayout(connection)
        self.formLayout.setObjectName("formLayout")
        self.buttonBox = QtGui.QDialogButtonBox(connection)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Close|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.formLayout.setWidget(6, QtGui.QFormLayout.FieldRole, self.buttonBox)
        self.editServer = QtGui.QLineEdit(connection)
        self.editServer.setObjectName("editServer")
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.editServer)
        self.labelServer = QtGui.QLabel(connection)
        self.labelServer.setObjectName("labelServer")
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.labelServer)
        self.editUsername = QtGui.QLineEdit(connection)
        self.editUsername.setObjectName("editUsername")
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.editUsername)
        self.labelUsername = QtGui.QLabel(connection)
        self.labelUsername.setObjectName("labelUsername")
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.labelUsername)
        self.labelPassword = QtGui.QLabel(connection)
        self.labelPassword.setObjectName("labelPassword")
        self.formLayout.setWidget(3, QtGui.QFormLayout.LabelRole, self.labelPassword)
        self.labelState = QtGui.QLabel(connection)
        self.labelState.setObjectName("labelState")
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.labelState)
        self.state = QtGui.QLabel(connection)
        self.state.setObjectName("state")
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.state)
        self.editPassword = QtGui.QLineEdit(connection)
        self.editPassword.setEchoMode(QtGui.QLineEdit.Password)
        self.editPassword.setObjectName("editPassword")
        self.formLayout.setWidget(3, QtGui.QFormLayout.FieldRole, self.editPassword)

        self.retranslateUi(connection)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), connection.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), connection.reject)
        QtCore.QMetaObject.connectSlotsByName(connection)

    def retranslateUi(self, connection):
        connection.setWindowTitle(QtGui.QApplication.translate("connection", "Connection", None, QtGui.QApplication.UnicodeUTF8))
        self.editServer.setText(QtGui.QApplication.translate("connection", "localhost:14789", None, QtGui.QApplication.UnicodeUTF8))
        self.labelServer.setText(QtGui.QApplication.translate("connection", "Server:port", None, QtGui.QApplication.UnicodeUTF8))
        self.labelUsername.setText(QtGui.QApplication.translate("connection", "Username", None, QtGui.QApplication.UnicodeUTF8))
        self.labelPassword.setText(QtGui.QApplication.translate("connection", "Password", None, QtGui.QApplication.UnicodeUTF8))
        self.labelState.setText(QtGui.QApplication.translate("connection", "State", None, QtGui.QApplication.UnicodeUTF8))
        self.state.setText(QtGui.QApplication.translate("connection", "Not connected", None, QtGui.QApplication.UnicodeUTF8))


########NEW FILE########
__FILENAME__ = frontend
#!/usr/bin/env python
# -*- coding: utf8 -*-

###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

# Standard library
from __future__ import print_function
import threading
import hashlib
import socket
import time
import sys
import re

# Third-party modules
from PyQt4 import QtCore, QtGui

# Local modules
import connection
import window



# FIXME: internationalize
_ = lambda x:x

refreshingTree = threading.Lock()
class ConfigurationTreeRefresh:
    def __init__(self, eventsManager, window):
        if not refreshingTree.acquire(False):
            return
        self._eventsManager = eventsManager

        parentItem = QtGui.QStandardItemModel()
        window.connect(parentItem, QtCore.SIGNAL('itemClicked()'),
                       window.configurationItemActivated)
        window.configurationTree.setModel(parentItem)
        self.items = {'supybot': parentItem}

        hash_ = eventsManager.sendCommand('config search ""')
        eventsManager.hook(hash_, self.slot)

    def slot(self, reply):
        """Slot called when a childs list is got."""
        childs = reply.split(', ')
        for child in childs:
            if '\x02' in child:
                hash_ = self._eventsManager.sendCommand('more')
                self._eventsManager.hook(hash_, self.slot)
                break
            elif ' ' in child:
                refreshingTree.release()
                break
            splitted = child.split('.')
            parent, name = '.'.join(splitted[0:-1]), splitted[-1]
            item = QtGui.QStandardItem(name)
            item.name = QtCore.QString(child)
            self.items[parent].appendRow(item)
            self.items[child] = item



class Connection(QtGui.QTabWidget, connection.Ui_connection):
    """Represents the connection dialog."""
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.setupUi(self)

    def accept(self):
        """Signal called when the button 'accept' is clicked."""
        self.state.text = _('Connecting...')
        if not self._connect():
            self.state.text = _('Connection failed.')
            return

        self.state.text = _('Connected. Loading GUI...')

        window = Window(self._eventsManager)
        window.show()
        window.commandEdit.setFocus()

        self._eventsManager.callbackConnectionClosed = window.connectionClosed
        self._eventsManager.defaultCallback = window.replyReceived

        self.hide()

    def _connect(self):
        """Connects to the server, using the filled fields in the GUI.
        Return wheter or not the connection succeed. Note that a successful
        connection with a failed authentication is interpreted as successful.
        """
        server = str(self.editServer.text()).split(':')
        username = str(self.editUsername.text())
        password = str(self.editPassword.text())

        assert len(server) == 2
        assert re.match('[0-9]+', server[1])
        assert ' ' not in username
        assert ' ' not in password

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server[1] = int(server[1])
        try:
            sock.connect(tuple(server))
        except socket.error:
            return False
        sock.settimeout(0.01)

        self._eventsManager = EventsManager(sock)

        self._eventsManager.sendCommand('identify %s %s' %
                                        (username, password))
        return True

    def reject(self):
        """Signal called when the button 'close' is clicked."""
        exit()

class Window(QtGui.QTabWidget, window.Ui_window):
    """Represents the main window."""
    def __init__(self, eventsManager, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self._eventsManager = eventsManager

        self.setupUi(self)
        self.connect(self.commandEdit, QtCore.SIGNAL('returnPressed()'),
                     self.commandSendHandler)
        self.connect(self.commandSend, QtCore.SIGNAL('clicked()'),
                     self.commandSendHandler)

        self.connect(self.refreshConfigurationTree, QtCore.SIGNAL('clicked()'),
                     self._refreshConfigurationTree)

    def commandSendHandler(self):
        """Slot called when the user clicks 'Send' or presses 'Enter' in the
        raw commands tab."""
        command = self.commandEdit.text()
        self.commandEdit.clear()
        try:
            # No hooking, because the callback would be the default callback
            self._eventsManager.sendCommand(command)
            s = _('<-- ') + command
        except socket.error:
            s = _('(not sent) <-- ') + command
        self.commandsHistory.appendPlainText(s)

    def replyReceived(self, reply):
        """Called by the events manager when a reply to a raw command is
        received."""
        self.commandsHistory.appendPlainText(_('--> ') + reply.decode('utf8'))

    def connectionClosed(self):
        """Called by the events manager when a special message has to be
        displayed."""
        self.commandsHistory.appendPlainText(_('* connection closed *'))
        self.commandEdit.readOnly = True
        self._eventsManager.stop()

    def _refreshConfigurationTree(self):
        """Slot called when the user clicks 'Refresh' under the configuration
        tree."""
        ConfigurationTreeRefresh(self._eventsManager, self)

    def configurationItemActivated(self, item):
        print(repr(item))




class EventsManager(QtCore.QObject):
    """This class handles all incoming messages, and call the associated
    callback (using hook() method)"""
    def __init__(self, sock):
        self._sock = sock
        self.defaultCallback = lambda x:x
        self._currentLine = ''
        self._hooks = {} # FIXME: should be cleared every minute

        self._timerGetReplies = QtCore.QTimer()
        self.connect(self._timerGetReplies, QtCore.SIGNAL('timeout()'),
                     self._getReplies);
        self._timerGetReplies.start(100)

        self._timerCleanHooks = QtCore.QTimer()
        self.connect(self._timerCleanHooks, QtCore.SIGNAL('timeout()'),
                     self._cleanHooks);
        self._timerCleanHooks.start(100)

    def _getReplies(self):
        """Called by the QTimer; fetches the messages and calls the hooks."""
        currentLine = self._currentLine
        self.currentLine = ''
        if not '\n' in currentLine:
            try:
                data = self._sock.recv(65536)
                if not data: # Frontend closed connection
                    self.callbackConnectionClosed()
                    return
                currentLine += data
            except socket.timeout:
                return
        if '\n' in currentLine:
            splitted = currentLine.split('\n')
            nextLines = '\n'.join(splitted[1:-1])
            splitted = splitted[0].split(': ')
            hash_, reply = splitted[0], ': '.join(splitted[1:])
            if hash_ in self._hooks:
                self._hooks[hash_][0](reply)
            else:
                self.defaultCallback(reply)
        else:
            nextLines = currentLine
        self._currentLine = nextLines

    def hook(self, hash_, callback, lifeTime=60):
        """Attach a callback to a hash: everytime a reply with this hash is
        received, the callback is called."""
        self._hooks[hash_] = (callback, time.time() + lifeTime)

    def unhook(self, hash_):
        """Undo hook()."""
        return self._hooks.pop(hash_)

    def _cleanHooks(self):
        for hash_, data in self._hooks.items():
            if data[1] < time.time():
                self._hooks.pop(hash_)

    def sendCommand(self, command):
        """Get a command, send it, and returns a unique hash, used to identify
        replies to this command."""
        hash_ = hashlib.sha1(str(time.time()) + command).hexdigest()
        command = '%s: %s\n' % (hash_, unicode(command).encode('utf8', 'replace'))
        self._sock.send(command)
        return hash_

    def stop(self):
        """Stops the loop."""
        self._timer.stop()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    connection = Connection()
    connection.show()


    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = window
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'window.ui'
#
# Created: Sat Feb 12 17:11:05 2011
#      by: PyQt4 UI code generator 4.7.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_window(object):
    def setupUi(self, window):
        window.setObjectName("window")
        window.resize(761, 591)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        window.setWindowIcon(icon)
        window.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        self.configurationTab = QtGui.QWidget()
        self.configurationTab.setObjectName("configurationTab")
        self.horizontalLayout = QtGui.QHBoxLayout(self.configurationTab)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.configurationTreeLayout = QtGui.QVBoxLayout()
        self.configurationTreeLayout.setObjectName("configurationTreeLayout")
        self.configurationTree = QtGui.QTreeView(self.configurationTab)
        self.configurationTree.setObjectName("configurationTree")
        self.configurationTreeLayout.addWidget(self.configurationTree)
        self.refreshConfigurationTree = QtGui.QPushButton(self.configurationTab)
        self.refreshConfigurationTree.setObjectName("refreshConfigurationTree")
        self.configurationTreeLayout.addWidget(self.refreshConfigurationTree)
        self.horizontalLayout.addLayout(self.configurationTreeLayout)
        self.configurationDetailsLayout = QtGui.QVBoxLayout()
        self.configurationDetailsLayout.setObjectName("configurationDetailsLayout")
        self.configurationEditLayout = QtGui.QVBoxLayout()
        self.configurationEditLayout.setObjectName("configurationEditLayout")
        self.configurationVariableLabel = QtGui.QLabel(self.configurationTab)
        self.configurationVariableLabel.setObjectName("configurationVariableLabel")
        self.configurationEditLayout.addWidget(self.configurationVariableLabel)
        self.configurationValueEdit = QtGui.QPlainTextEdit(self.configurationTab)
        self.configurationValueEdit.setObjectName("configurationValueEdit")
        self.configurationEditLayout.addWidget(self.configurationValueEdit)
        self.configurationEditButtonsLayout = QtGui.QHBoxLayout()
        self.configurationEditButtonsLayout.setObjectName("configurationEditButtonsLayout")
        self.configurationDefaultButton = QtGui.QPushButton(self.configurationTab)
        self.configurationDefaultButton.setObjectName("configurationDefaultButton")
        self.configurationEditButtonsLayout.addWidget(self.configurationDefaultButton)
        self.configurationSetButton = QtGui.QPushButton(self.configurationTab)
        self.configurationSetButton.setObjectName("configurationSetButton")
        self.configurationEditButtonsLayout.addWidget(self.configurationSetButton)
        self.configurationEditLayout.addLayout(self.configurationEditButtonsLayout)
        self.configurationDetailsLayout.addLayout(self.configurationEditLayout)
        self.configurationHelpLabel = QtGui.QLabel(self.configurationTab)
        self.configurationHelpLabel.setObjectName("configurationHelpLabel")
        self.configurationDetailsLayout.addWidget(self.configurationHelpLabel)
        self.configurationHelp = QtGui.QPlainTextEdit(self.configurationTab)
        self.configurationHelp.setObjectName("configurationHelp")
        self.configurationDetailsLayout.addWidget(self.configurationHelp)
        self.horizontalLayout.addLayout(self.configurationDetailsLayout)
        window.addTab(self.configurationTab, "")
        self.commandsTab = QtGui.QWidget()
        self.commandsTab.setObjectName("commandsTab")
        self.verticalLayout = QtGui.QVBoxLayout(self.commandsTab)
        self.verticalLayout.setObjectName("verticalLayout")
        self.commandsHistory = QtGui.QPlainTextEdit(self.commandsTab)
        self.commandsHistory.setTextInteractionFlags(QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.commandsHistory.setObjectName("commandsHistory")
        self.verticalLayout.addWidget(self.commandsHistory)
        self.commandsWritingLayout = QtGui.QHBoxLayout()
        self.commandsWritingLayout.setObjectName("commandsWritingLayout")
        self.commandEdit = QtGui.QLineEdit(self.commandsTab)
        self.commandEdit.setObjectName("commandEdit")
        self.commandsWritingLayout.addWidget(self.commandEdit)
        self.commandSend = QtGui.QPushButton(self.commandsTab)
        self.commandSend.setObjectName("commandSend")
        self.commandsWritingLayout.addWidget(self.commandSend)
        self.verticalLayout.addLayout(self.commandsWritingLayout)
        window.addTab(self.commandsTab, "")

        self.retranslateUi(window)
        window.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(window)

    def retranslateUi(self, window):
        window.setWindowTitle(QtGui.QApplication.translate("window", "Supybot GUI", None, QtGui.QApplication.UnicodeUTF8))
        self.refreshConfigurationTree.setText(QtGui.QApplication.translate("window", "Refresh", None, QtGui.QApplication.UnicodeUTF8))
        self.configurationVariableLabel.setText(QtGui.QApplication.translate("window", "Value", None, QtGui.QApplication.UnicodeUTF8))
        self.configurationDefaultButton.setText(QtGui.QApplication.translate("window", "Default", None, QtGui.QApplication.UnicodeUTF8))
        self.configurationSetButton.setText(QtGui.QApplication.translate("window", "Set", None, QtGui.QApplication.UnicodeUTF8))
        self.configurationHelpLabel.setText(QtGui.QApplication.translate("window", "Help", None, QtGui.QApplication.UnicodeUTF8))
        window.setTabText(window.indexOf(self.configurationTab), QtGui.QApplication.translate("window", "Configuration", None, QtGui.QApplication.UnicodeUTF8))
        self.commandSend.setText(QtGui.QApplication.translate("window", "Send", None, QtGui.QApplication.UnicodeUTF8))
        window.setTabText(window.indexOf(self.commandsTab), QtGui.QApplication.translate("window", "Commands", None, QtGui.QApplication.UnicodeUTF8))


########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import re
import time
import socket
import hashlib
import threading
import SocketServer
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.commands as commands
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('GUI')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x
parseMessage = re.compile('\w+: (?P<content>.*)')
class FakeIrc:
    def __init__(self, irc):
        self.message = ''
        self._irc = irc
    def reply(self, message):
        self.message += 'Reply: %s\n' % message
    def error(self, message=''):
        self.message += 'Error: %s\n' % message
    def queueMsg(self, message):
        self._rawData = message
        if message.command in ('PRIVMSG', 'NOTICE'):
            parsed = parseMessage.match(message.args[1])
            if parsed is not None:
                message = parsed.group('content')
            else:
                message = message.args[1]
        self.message = message
    def __getattr__(self, name):
        return getattr(self.__dict__['_irc'], name)

class ThreadedTCPServer(SocketServer.TCPServer):
    pass

class RequestHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        def hash_(data):
            return hashlib.sha1(str(time.time()) + data).hexdigest()
        self.request.settimeout(0.5)
        currentLine = ''
        prefix = 'a%s!%s@%s.supybot-gui' % tuple([hash_(x)[0:6] for x in 'abc'])
        while self.server.enabled:
            if not '\n' in currentLine:
                try:
                    data = self.request.recv(4096)
                except socket.timeout:
                    time.sleep(0.1) # in case of odd problem
                    continue
            if not data: # Server closed connection
                return
            if '\n' in data:
                splitted = (currentLine + data).split('\n')
                currentLine = splitted[0]
                nextLines = '\n'.join(splitted[1:])
            else:
                continue
            splitted = currentLine.split(': ')
            hash_, command = splitted[0], ': '.join(splitted[1:])

            tokens = callbacks.tokenize(command)
            fakeIrc = FakeIrc(self.server._irc)
            msg = ircmsgs.privmsg(self.server._irc.nick, currentLine, prefix)
            self.server._plugin.Proxy(fakeIrc, msg, tokens)

            self.request.send('%s: %s\n' % (hash_, fakeIrc.message))
            currentLine = nextLines


class GUI(callbacks.Plugin):
    threaded  = True
    def __init__(self, irc):
        self.__parent = super(GUI, self)
        callbacks.Plugin.__init__(self, irc)
        host = self.registryValue('host')
        port = self.registryValue('port')
        while True:
            try:
                self._server = ThreadedTCPServer((host, port),
                                                 RequestHandler)
                break
            except socket.error: # Address already in use
                time.sleep(1)
        self._server.timeout = 0.5

        # Used by request handlers:
        self._server._irc = irc
        self._server._plugin = self
        self._server.enabled = True

        threading.Thread(target=self._server.serve_forever,
                         name='GUI server').start()

    def die(self):
        self.__parent.die()
        self._server.enabled = False
        time.sleep(1)
        self._server.shutdown()
        del self._server



Class = GUI


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class GUITestCase(PluginTestCase):
    plugins = ('GUI',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import sys

import supybot.conf as conf
import supybot.registry as registry

from .plugin import Placeholder as Placeholder

if 'supybot.i18n' not in sys.modules:
    sys.modules['supybot.i18n'] = Placeholder()

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('I18nPlaceholder', True)


I18nPlaceholder = conf.registerPlugin('I18nPlaceholder')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(I18nPlaceholder, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import sys

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

class Placeholder:
    internationalizeDocstring = lambda self,y:y

    def PluginInternationalization(self, plugin_name):
        return lambda x:x


class I18nPlaceholder(callbacks.Plugin):
    """Add the help for "@plugin help I18nPlaceholder" here
    This should describe *how* to use this plugin."""
    def __init__(self, *args, **kwargs):
        super(I18nPlaceholder, self).__init__(*args, **kwargs)

        if 'supybot.i18n' not in sys.modules:
            sys.modules['supybot.i18n'] = Placeholder()


Class = I18nPlaceholder


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class I18nPlaceholderTestCase(PluginTestCase):
    plugins = ('I18nPlaceholder',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2012, Dan
# All rights reserved.
#
#
###

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('IMDb', True)


IMDb = conf.registerPlugin('IMDb')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(IMDb, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2012, Dan
# All rights reserved.
#
#
###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

import sys
import json
import socket
import unicodedata
from lxml import html

if sys.version_info[0] >= 3:
    def u(s):
        return s
    import urllib
    Request = urllib.request.Request
    urlopen = urllib.request.urlopen
    HTTPError = urllib.error.HTTPError
    URLError = urllib.error.URLError
    urlencode = urllib.parse.urlencode
else:
    import urllib2
    from urllib import urlencode
    Request = urllib2.Request
    urlopen = urllib2.urlopen
    HTTPError = urllib2.HTTPError
    URLError = urllib2.URLError
    def u(s):
        return unicode(s, "unicode_escape")

def unid(s):
    if sys.version_info[0] < 3 and isinstance(s, unicode):
        return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore')
    else:
        return s

class IMDb(callbacks.Plugin):
    """Add the help for "@plugin help IMDb" here
    This should describe *how* to use this plugin."""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(IMDb, self)
        self.__parent.__init__(irc)


    def imdb(self, irc, msg, args, opts, text):
        """<movie>
        output info from IMDb about a movie"""

        textencoded = urlencode({'q': 'site:http://www.imdb.com/title/ %s' % text})
        url = 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&%s' % (textencoded)
        request = Request(url)
        try:
            page = urlopen(request)
        except socket.timeout as e:
            irc.error('\x0304Connection timed out.\x03', prefixNick=False)
            return
        except HTTPError as e:
            irc.error('\x0304HTTP Error\x03', prefixNick=False)
            return
        except URLError as e:
            irc.error('\x0304URL Error\x03', prefixNick=False)
            return

        result = json.loads(page.read().decode('utf-8'))

        if result['responseStatus'] != 200:
            irc.error('\x0304Google search didnt work, returned status %s' % result['responseStatus'])
            return

        imdb_url = None

        for r in result['responseData']['results']:
            if r['url'][-1] == '/':
                imdb_url = r['url']
                break

        if imdb_url is None:
            irc.error('\x0304Couldnt find a title')
            return

        request = Request(imdb_url, 
                headers={'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:5.0) Gecko/20100101 Firefox/5.0',
                        'Accept-Language': 'en-us,en;q=0.5'})
        try:
            page = urlopen(request)
        except socket.timeout as e:
            irc.error('\x0304Connection timed out.\x03', prefixNick=False)
            return
        except HTTPError as e:
            irc.error('\x0304HTTP Error\x03', prefixNick=False)
            return
        except URLError as e:
            irc.error('\x0304URL Error\x03', prefixNick=False)
            return

        root = html.parse(page)

        elem = root.xpath('//h1/span[@itemprop="name"]')
        name = unid(elem[0].text.strip())

        elem = root.xpath('//h2[@class="tv_header"]')
        if elem:
            tv = unid(elem[0].text_content().strip().replace('\n        ', ''))
        else:
            tv = ''

        elem = root.xpath('//div[@itemprop="genre"]')
        if elem:
            genres = unid(' '.join(elem[0].text_content().split()).strip().replace('Genres: ', ''))
        else:
            genres = ''

        elem = root.xpath('//div[h4="Stars:"]')
        if elem:
            stars = unid(' '.join(elem[0].text_content().split()).replace('Stars: ', '').replace(' | See full cast and crew', ''))
        else:
            stars = ''

        elem = root.xpath('//div[h4="Plot Keywords:"]')
        if elem:
            plot_keywords = unid(' '.join(elem[0].text_content().replace(u('\xbb'), '').split()).strip().replace(' | See more', '').replace('Plot Keywords: ', ''))
        else:
            plot_keywords = ''

        elem = root.xpath('//h1[span/@itemprop="name"]/span[last()]/a')
        if elem:
            year = elem[0].text
        else:
            year = unid(root.xpath('//h1[span/@itemprop="name"]/span[last()]')[0].text.strip().strip(')(').replace(u('\u2013'), '-'))

        elem = root.xpath('//div[@class="star-box-details"]/strong/span|//div[@class="star-box-details"]/span[@class="mellow"]/span')
        if elem:
            rating = elem[0].text + '/' + elem[1].text
        else:
            rating = '-/10'

        elem = root.xpath('//p[@itemprop="description"]')
        if elem:
            description = elem[0].text_content()
            description = unid(description.replace(u('\xbb'), '').strip().replace('See full summary', '').strip())
        else:
            description = ''

        elem = root.xpath('//div[@itemprop="director"]/a/span')
        if elem:
            director = unid(elem[0].text)
        else:
            director = ''

        elem = root.xpath('//div[h4="\n  Creator:\n  "]/a')
        if elem:
            creator = unid(elem[0].text)
        else:
            creator = ''

        elem = root.xpath('//div[h4="Runtime:"]/time')
        if elem:
            runtime = elem[0].text
        else:
            runtime = ''

        irc.reply('\x02\x031,8IMDb\x03 %s' % imdb_url, prefixNick=False)
        if tv:
            irc.reply('\x02TV Show\x02 /\x0311 %s' % tv, prefixNick=False)
        irc.reply('\x02\x0304\x1F%s\x1F\x0311\x02 (%s) %s' % (name, year, rating), prefixNick=False)
        if description:
            irc.reply('\x0305Description\03 /\x0311 %s' % description, prefixNick=False)
        if creator:
            irc.reply('\x0305Creator\03 /\x0311 %s' % creator, prefixNick=False)

        out = []
        if director:
            out.append('\x0305Director\03 /\x0311 %s' % director)
        if stars:
            out.append('\x0305Stars\x03 /\x0311 %s' % stars)
        if out:
            irc.reply('  '.join(out), prefixNick=False)

        out = []
        if genres:
            out.append('\x0305Genres\03 /\x0311 %s' % genres)
        if plot_keywords:
            out.append('\x0305Plot Keywords\03 /\x0311 %s' % plot_keywords)
        if out:
            irc.reply('  '.join(out), prefixNick=False)

        if runtime:
            irc.reply('\x0305Runtime\x03 /\x0311 %s' % runtime, prefixNick=False)

    imdb = wrap(imdb, [getopts({'s': '', 'short': ''}), 'text'])


Class = IMDb


# vim:set shiftwidth=4 softtabstop=4 expandtab:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2012, Dan
# All rights reserved.
#
#
###

from supybot.test import *

class IMDbTestCase(PluginTestCase):
    plugins = ('IMDb',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry

try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('Iwant')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Iwant', True)


Iwant = conf.registerPlugin('Iwant')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Iwant, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))

conf.registerChannelValue(Iwant, 'wishlist',
    registry.Json([], _("""List of wanted things. Don't edit this variable
    unless you know what you do.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import random

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('Iwant')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def unserialize(string):
    return string

def serialize(list):
    return list

@internationalizeDocstring
class Iwant(callbacks.Plugin):
    """Add the help for "@plugin help Iwant" here
    This should describe *how* to use this plugin."""

    @internationalizeDocstring
    def iwant(self, irc, msg, args, channel, thing):
        """[<channel>] <thing>

        Tell the bot you want the <thing>. <channel> is only needed if you
        don't send the message on the channel itself."""
        wishlist = unserialize(self.registryValue('wishlist', channel))
        if thing in wishlist:
            irc.error(_('This thing is already wanted.'))
            return
        wishlist.append(thing)
        self.setRegistryValue('wishlist', serialize(wishlist), channel)
        irc.replySuccess()
    iwant = wrap(iwant, ['channel', 'text'])

    @internationalizeDocstring
    def list(self, irc, msg, args, channel):
        """[<channel>]

        Returns the list of wanted things for the <channel>. <channel> defaults
        to the current channel."""
        wishlist = unserialize(self.registryValue('wishlist', channel))
        if list(wishlist) == 0:
            irc.error(_('No wish for the moment.'))
            return
        indexes = range(1, len(wishlist) + 1)
        wishlist_with_index = zip(indexes, wishlist)
        formatted_wishlist = [_('#%i: %s') % x for x in wishlist_with_index]
        irc.reply(utils.str.format('%L', formatted_wishlist))
    list = wrap(list, ['channel'])

    @internationalizeDocstring
    def get(self, irc, msg, args, channel, id):
        """[<channel>] <id>

        Tell you the thing number <id>. <channel> is only needed if you
        don't send the message on the channel itself."""
        wishlist = unserialize(self.registryValue('wishlist', channel))
        if len(wishlist) < id:
            irc.error(_('No thing has this id.'))
            return
        irc.reply(_('Wish #%i is %s.') % (id, wishlist[id - 1]))
    get = wrap(get, ['channel', 'id'])

    @internationalizeDocstring
    def random(self, irc, msg, args, channel):
        """[<channel>]

        Tell you a random thing. <channel> is only needed if you
        don't send the message on the channel itself."""
        wishlist = unserialize(self.registryValue('wishlist', channel))
        if list(wishlist) == 0:
            irc.error(_('No wish for the moment.'))
            return
        indexes = range(1, len(wishlist) + 1)
        wishlist_with_index = list(zip(indexes, wishlist))
        wish = random.sample(wishlist_with_index, 1)[0]
        irc.reply(_('Wish #%i is %s.') % wish)
    random = wrap(random, ['channel'])

    @internationalizeDocstring
    def delete(self, irc, msg, args, channel, id):
        """[<channel>] <id>

        Deletes the thing number <id>. <channel> is only needed if you
        don't send the message on the channel itself."""
        wishlist = unserialize(self.registryValue('wishlist', channel))
        if len(wishlist) < id:
            irc.error(_('No thing has this id.'))
            return
        thing = wishlist.pop(id - 1)
        self.setRegistryValue('wishlist', serialize(wishlist), channel)
        irc.reply(_('Successfully deleted: %s') % thing)
    delete = wrap(delete, ['channel', 'id'])


Class = Iwant


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class IwantTestCase(ChannelPluginTestCase):
    plugins = ('Iwant',)

    def testIwant(self):
        self.assertError('iwant random')
        self.assertError('iwant list')
        self.assertNotError('iwant you')
        self.assertNotError('iwant "a working plugin"')
        self.assertResponse('iwant list', '#1: you and #2: a working plugin')
        self.assertResponse('iwant get 2', 'Wish #2 is a working plugin.')
        self.assertNotError('iwant "be cool"')
        self.assertResponse('iwant list', '#1: you, #2: a working plugin, and '
                            '#3: be cool')
        self.assertResponse('iwant get 2', 'Wish #2 is a working plugin.')
        self.assertNotError('iwant random')
        self.assertResponse('delete 1', 'Successfully deleted: you')
        self.assertResponse('iwant list', '#1: a working plugin and '
                            '#2: be cool')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Kickme')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Kickme', True)


Kickme = conf.registerPlugin('Kickme')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Kickme, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Kickme')

@internationalizeDocstring
class Kickme(callbacks.Plugin):
    """Add the help for "@plugin help Kickme" here
    This should describe *how* to use this plugin."""
    def kickme(self, irc, msg, args, reason):
        """[<reason>]

        Kick yourself."""
        irc.queueMsg(ircmsgs.kick(msg.args[0], msg.nick, reason or ''))
    kickme = wrap(kickme, [optional('text')])


Class = Kickme


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class KickmeTestCase(PluginTestCase):
    plugins = ('Kickme',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('LimnoriaChan')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('LimnoriaChan', True)


LimnoriaChan = conf.registerPlugin('LimnoriaChan')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(LimnoriaChan, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))
conf.registerGlobalValue(LimnoriaChan, 'login',
    registry.String('Limnoria', _("Login to GitHub (to post issues)")))
conf.registerGlobalValue(LimnoriaChan, 'token',
    registry.String('', _("Auth toket to GitHub (to post issues)"),
    private=True))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import re
import json
import urllib

import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('LimnoriaChan')

WEB_REPO = 'https://github.com/ProgVal/Limnoria'
PLUGINS_WEB_REPO = 'https://github.com/ProgVal/Supybot-plugins'
staticFactoids = {
        'git':          'git://github.com/ProgVal/Limnoria.git',
        'git-pl':       'git://github.com/ProgVal/Supybot-plugins.git',
        'gh':           WEB_REPO,
        'gh-pl':        PLUGINS_WEB_REPO,
        'wiki':         WEB_REPO + '/wiki',
        'issues':       WEB_REPO + '/issues',
        'issues-pl':    PLUGINS_WEB_REPO + '/issues',
        'supybook':     'http://supybook.fealdia.org/',
        }
dynamicFactoids = {
        'gh':           WEB_REPO + '/tree/master/%s',
        'gh-pl':        PLUGINS_WEB_REPO + '/tree/master/%s',
        'file':         WEB_REPO + '/blob/master/%s',
        'file-pl':      PLUGINS_WEB_REPO + '/blob/master/%s',
        'commit':       WEB_REPO + '/commit/%s',
        'commit-pl':    PLUGINS_WEB_REPO + '/commit/%s',
        'wiki':         WEB_REPO + '/wiki/%s',
        'issue':        WEB_REPO + '/issues/%s',
        'issue-pl':     PLUGINS_WEB_REPO + '/issues/%s',
        }

@internationalizeDocstring
class LimnoriaChan(callbacks.Plugin):
    """Add the help for "@plugin help LimnoriaChan" here
    This should describe *how* to use this plugin."""

    def issue(self, irc, msg, args, user, title):
        """<title>

        Opens an issue on Limnoria bugtracker called <title>."""
        self._issue(irc, msg, args, user, title, 'ProgVal/Limnoria')
    issue = wrap(issue, ['user', 'text'])

    def issuepl(self, irc, msg, args, user, title):
        """<title>

        Opens an issue on ProgVal/Supybot-plugins bugtracker called <title>.
        """
        self._issue(irc, msg, args, user, title, 'ProgVal/Supybot-plugins')
    issuepl = wrap(issuepl, ['user', 'text'])

    def _issue(self, irc, msg, args, user, title, repoName):
        if not world.testing and \
                msg.args[0] not in ('#limnoria', '#limnoria-bots'):
            irc.error('This command can be run only on #limnoria or '
                    '#limnoria-bots on Freenode.')
        body = 'Issue sent from %s at %s by %s (registered as %s)' % \
                (msg.args[0], irc.network, msg.nick, user.name)
        login = self.registryValue('login')
        token = self.registryValue('token')
        data='title=%s&body=%s&login=%s&token=%s' % (title, body, login, token)
        url = 'https://api.github.com/repos/' + repoName + '/issues'
        response = json.loads(urllib.urlopen(url, data=data).read())
        id = response['number']
        irc.reply('Issue #%i has been opened.' % id)

    _addressed = re.compile('^([^ :]+):')
    _factoid = re.compile('%%([^ ]+)')
    _dynamicFactoid = re.compile('^(?P<name>[^#]+)#(?P<arg>.*)$')
    def doPrivmsg(self, irc, msg):
        if not world.testing and \
                msg.args[0] not in ('#limnoria', '#limnoria-bots'):
            return
        if callbacks.addressed(irc.nick, msg):
            return

        # Internal
        match = self._addressed.match(msg.args[1])
        if match is None:
            prefix = ''
        else:
            prefix = match.group(1) + ': '
        def reply(string):
            irc.reply(prefix + string, prefixNick=False)

        # Factoids
        matches = self._factoid.findall(msg.args[1])
        for name in matches:
            arg = None
            match = self._dynamicFactoid.match(name)
            if match is not None:
                name = match.group('name')
                arg = match.group('arg')
            name = name.lower()
            if arg is None:
                if name in staticFactoids:
                    reply(staticFactoids[name])
            else:
                if name in dynamicFactoids:
                    reply(dynamicFactoids[name] % arg)

Class = LimnoriaChan


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class LimnoriaChanTestCase(ChannelPluginTestCase):
    plugins = ('LimnoriaChan',)

    def testFactoids(self):
        self.assertResponse('Hi, see the %%git repo!',
                'git://github.com/ProgVal/Limnoria.git',
                usePrefixChar=False)
        self.assertResponse('foobar: Hi, see the %%git-pl repo!',
                'foobar: git://github.com/ProgVal/Supybot-plugins.git',
                usePrefixChar=False)
        self.assertNoResponse('This does %%not exist', usePrefixChar=False)

        self.assertResponse('Hi, see %%commit#a234b0e at the Git repo.',
                'https://github.com/ProgVal/Limnoria/commit/a234b0e',
                usePrefixChar=False)


        

        # test is the bot's nick
        self.assertError('test: Hi, see the %%git repo!', usePrefixChar=False)
        self.assertError('Hi, see the %%git repo!')



# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2010, quantumlemur
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import supybot.conf as conf
import supybot.ircutils as ircutils
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('LinkRelay')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('LinkRelay', True)


class ColorNumber(registry.String):
    """Value must be a valid color number (01, 02, 03, 04, ..., 16)"""
    def set(self, s):
        if s not in ('01', '02', '03', '04', '05', '06', '07', '08', '09',
                     '10', '11', '12', '13', '14', '15', '16'):
            self.error()
            return
        self.setValue(s)
try:
    ColorNumber = internationalizeDocstring(ColorNumber)
except TypeError:
    # Pypy
    pass


LinkRelay = conf.registerPlugin('LinkRelay')
conf.registerChannelValue(LinkRelay, 'color',
    registry.Boolean(False, _("""Determines whether the bot will color Relayed
    PRIVMSGs so as to make the messages easier to read.""")))
conf.registerChannelValue(LinkRelay, 'topicSync',
    registry.Boolean(True, _("""Determines whether the bot will synchronize
    topics between networks in the channels it Relays.""")))
conf.registerChannelValue(LinkRelay, 'hostmasks',
    registry.Boolean(False, _("""Determines whether the bot will Relay the
    hostmask of the person joining or parting the channel when he or she joins
    or parts.""")))
conf.registerChannelValue(LinkRelay, 'nicks',
    registry.Boolean(True, _("""Determines whether the bot will relay the
    nick of the person sending a message.""")))
conf.registerChannelValue(LinkRelay, 'includeNetwork',
    registry.Boolean(True, _("""Determines whether the bot will include the
    network in Relayed PRIVMSGs; if you're only Relaying between two networks,
    it's somewhat redundant, and you may wish to save the space.""")))

class ValidNonPrivmsgsHandling(registry.OnlySomeStrings):
    validStrings = ('privmsg', 'notice', 'nothing')
conf.registerChannelValue(LinkRelay, 'nonPrivmsgs',
    ValidNonPrivmsgsHandling('privmsg', _("""Determines whether the
    bot will use PRIVMSGs (privmsg), NOTICEs (notice), for non-PRIVMSG Relay
    messages (i.e., joins, parts, nicks, quits, modes, etc.), or whether it
    won't relay such messages (nothing)""")))

conf.registerGlobalValue(LinkRelay, 'relays',
    registry.String('', _("""You shouldn't edit this configuration variable
    yourself unless you know what you do. Use @LinkRelay {add|remove} instead.""")))

conf.registerGlobalValue(LinkRelay, 'substitutes',
    registry.String('', _("""You shouldn't edit this configuration variable
    yourself unless you know what you do. Use @LinkRelay (no)substitute instead.""")))

conf.registerGroup(LinkRelay, 'colors')
for name, color in {'info': '02',
                    'truncated': '14',
                    'mode': '14',
                    'join': '14',
                    'part': '14',
                    'kick': '14',
                    'nick': '14',
                    'quit': '14'}.items():
    conf.registerChannelValue(LinkRelay.colors, name,
        ColorNumber(color, _("""Color used for relaying %s.""") % color))


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2010, quantumlemur
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import re
import time
import copy
import string
import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.irclib as irclib
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('LinkRelay')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

@internationalizeDocstring
class LinkRelay(callbacks.Plugin):
    """Advanced message relay between channels."""
    noIgnore = True
    threaded = True

    class Relay():
        def __init__(self, sourceChannel, sourceNetwork, targetChannel,
                     targetNetwork, channelRegex, networkRegex, messageRegex):
            self.sourceChannel = sourceChannel
            self.sourceNetwork = sourceNetwork
            self.targetChannel = targetChannel
            self.targetNetwork = targetNetwork
            self.channelRegex = channelRegex
            self.networkRegex = networkRegex
            self.messageRegex = messageRegex
            self.hasSourceIRCChannels = False


    def __init__(self, irc):
        self.__parent = super(LinkRelay, self)
        self.__parent.__init__(irc)
        self._loadFromConfig()
        self.ircstates = {}
        try:
            conf.supybot.plugins.LinkRelay.substitutes.addCallback(
                    self._loadFromConfig)
            conf.supybot.plugins.LinkRelay.relays.addCallback(
                    self._loadFromConfig)
        except registry.NonExistentRegistryEntry:
            log.error("Your version of Supybot is not compatible with "
                      "configuration hooks. So, LinkRelay won't be able "
                      "to reload the configuration if you use the Config "
                      "plugin.")

    def _loadFromConfig(self, name=None):
        self.relays = []
        for relay in self.registryValue('relays').split(' || '):
            if relay.endswith('|'):
                relay += ' '
            relay = relay.split(' | ')
            if not len(relay) == 5:
                continue
            try:
                self.relays.append(self.Relay(relay[0],
                                          relay[1],
                                          relay[2],
                                          relay[3],
                                          re.compile('^%s$' % relay[0], re.I),
                                          re.compile('^%s$' % relay[1]),
                                          re.compile(relay[4])))
            except:
                log.error('Failed adding relay: %r' % relay)

        self.nickSubstitutions = {}
        for substitute in self.registryValue('substitutes').split(' || '):
            if substitute.endswith('|'):
                substitute += ' '
            substitute = substitute.split(' | ')
            if not len(substitute) == 2:
                continue
            self.nickSubstitutions[substitute[0]] = substitute[1]



    def simpleHash(self, s):
        colors = ["\x0305", "\x0304", "\x0303", "\x0309", "\x0302", "\x0312",
                  "\x0306",   "\x0313", "\x0310", "\x0311", "\x0307"]
        num = 0
        for i in s:
            num += ord(i)
        num = num % 11
        return colors[num]


    def getPrivmsgData(self, channel, nick, text, colored):
        color = self.simpleHash(nick)
        if nick in self.nickSubstitutions:
            nick = self.nickSubstitutions[nick]
        if not self.registryValue('nicks', channel):
            nick = ''
        if re.match('^\x01ACTION .*\x01$', text):
            text = text.strip('\x01')
            text = text[ 7 : ]
            if colored:
                return ('* \x03%(color)s%(nick)s%(network)s\017 %(text)s',
                        {'nick': nick, 'color': color, 'text': text})
            else:
                return ('* %(nick)s%(network)s %(text)s',
                        {'nick': nick, 'text': text})
        else:
            if colored:
                return ('<\x03%(color)s%(nick)s%(network)s\017> %(text)s',
                        {'color': color, 'nick': nick, 'text': text})
            else:
                return ('<%(nick)s%(network)s> %(text)s',
                        {'nick': nick, 'text': text})
        return s


    @internationalizeDocstring
    def list(self, irc, msg, args):
        """takes no arguments

        Returns all the defined relay links"""
        if not self.relays:
            irc.reply(_('This is no relay enabled. Use "linkrelay add" to '
                'add one.'))
            return
        replies = []
        for relay in self.relays:
            if world.getIrc(relay.targetNetwork):
                hasIRC = 'Link healthy!'
            else:
                hasIRC = '\x03%sNot connected to network.\017' % \
                        self.registryValue('colors.info', msg.args[0])
            s ='\x02%s\x02 on \x02%s\x02 ==> \x02%s\x02 on \x02%s\x02.  %s'
            if not self.registryValue('color', msg.args[0]):
                s = s.replace('\x02', '')
            replies.append(s %
                        (relay.sourceChannel,
                         relay.sourceNetwork,
                         relay.targetChannel,
                         relay.targetNetwork,
                         hasIRC))
        irc.replies(replies)

    def doPrivmsg(self, irc, msg):
        channel = msg.args[0]
        s = msg.args[1]
        s, args = self.getPrivmsgData(channel, msg.nick, s,
                               self.registryValue('color', channel))
        if channel not in irc.state.channels: # in private
            # cuts off the end of commands, so that passwords
            # won't be revealed in relayed PM's
            if callbacks.addressed(irc.nick, msg):
                if self.registryValue('color', channel):
                    color = '\x03' + self.registryValue('colors.truncated',
                            channel)
                    match = '(>\017 \w+) .*'
                else:
                    color = ''
                    match = '(> \w+) .*'
                s = re.sub(match, '\\1 %s[%s]' % (color, _('truncated')), s)
            s = '(via PM) %s' % s
        self.sendToOthers(irc, channel, s, args, isPrivmsg=True)


    def outFilter(self, irc, msg):
        if msg.command == 'PRIVMSG':
            if not msg.relayedMsg:
                if msg.args[0] in irc.state.channels:
                    s, args = self.getPrivmsgData(msg.args[0], irc.nick, msg.args[1],
                                    self.registryValue('color', msg.args[0]))
                    self.sendToOthers(irc, msg.args[0], s, args, isPrivmsg=True)
        return msg


    def doMode(self, irc, msg):
        args = {'nick': msg.nick, 'channel': msg.args[0],
                'mode': ' '.join(msg.args[1:]), 'color': ''}
        if self.registryValue('color', msg.args[0]):
            args['color'] = '\x03%s' % self.registryValue('colors.mode', msg.args[0])
        s = '%(color)s' + _('*/* %(nick)s changed mode on '
                '%(channel)s%(network)s to %(mode)s')
        self.sendToOthers(irc, msg.args[0], s, args)

    def doJoin(self, irc, msg):
        args = {'nick': msg.nick, 'channel': msg.args[0], 'color': ''}
        if self.registryValue('color', msg.args[0]):
            args['color'] = '\x03%s' % self.registryValue('colors.join', msg.args[0])
        if self.registryValue('hostmasks', msg.args[0]):
            args['nick'] = msg.prefix
        s = '%(color)s' + _('--> %(nick)s has joined %(channel)s%(network)s')
        self.sendToOthers(irc, msg.args[0], s, args)

    def doPart(self, irc, msg):
        args = {'nick': msg.nick, 'channel': msg.args[0], 'color': ''}
        if self.registryValue('color', msg.args[0]):
            args['color'] = '\x03%s' % self.registryValue('colors.part', msg.args[0])
        if self.registryValue('hostmasks', msg.args[0]):
            args['nick'] = msg.prefix
        s = '%(color)s' + _('<-- %(nick)s has left %(channel)s%(network)s')
        self.sendToOthers(irc, msg.args[0], s, args)

    def doKick(self, irc, msg):
        args = {'kicked': msg.args[1], 'channel': msg.args[0],
                'kicker': msg.nick, 'message': msg.args[2], 'color': ''}
        if self.registryValue('color', msg.args[0]):
            args['color'] = '\x03%s' % self.registryValue('colors.kick',
                    msg.args[0])
        s = '%(color)s' + _('<-- %(kicked)s has been kicked from '
                '%(channel)s%(network)s by %(kicker)s (%(message)s)')
        self.sendToOthers(irc, msg.args[0], s, args)

    def doNick(self, irc, msg):
        args = {'oldnick': msg.nick, 'network': irc.network,
                'newnick': msg.args[0], 'color': ''}
        if self.registryValue('color', msg.args[0]):
            args['color'] = '\x03%s' % self.registryValue('colors.nick', msg.args[0])
        s = _('*/* %(oldnick)s (%(network)s) changed their nickname to '
                '%(newnick)s')
        for (channel, c) in irc.state.channels.items():
            if msg.args[0] in c.users:
                self.sendToOthers(irc, channel, s, args)

    def doQuit(self, irc, msg):
        args = {'nick': msg.nick, 'network': irc.network,
                'message': msg.args[0], 'color': ''}
        if self.registryValue('color', msg.args[0]):
            args['color'] = '\x03%s' % self.registryValue('colors.quit', msg.args[0])
        s = _('<-- %(nick)s has quit on %(network)s (%(message)s)')
        self.sendToOthers(irc, None, s, args, msg.nick)

    def sendToOthers(self, irc, channel, s, args, nick=None, isPrivmsg=False):
        assert channel is not None or nick is not None
        def format_(relay, s, args):
            if 'network' not in args:
                if self.registryValue('includeNetwork', relay.targetChannel):
                    args['network'] = '@' + irc.network
                else:
                    args['network'] = ''
            return s % args
        def send(s):
            targetIRC = world.getIrc(relay.targetNetwork)
            if not targetIRC:
                self.log.info('LinkRelay:  Not connected to network %s.' %
                              relay.targetNetwork)
            elif targetIRC.zombie:
                self.log.info('LinkRelay:  IRC %s appears to be a zombie'%
                              relay.targetNetwork)
            elif irc.isChannel(relay.targetChannel) and \
                    relay.targetChannel not in targetIRC.state.channels:
                self.log.info('LinkRelay:  I\'m not in in %s on %s' %
                              (relay.targetChannel, relay.targetNetwork))
            else:
                if isPrivmsg or \
                        self.registryValue('nonPrivmsgs', channel) == 'privmsg':
                    f = ircmsgs.privmsg
                elif self.registryValue('nonPrivmsgs', channel) == 'notice':
                    f = ircmsgs.notice
                else:
                    return
                allowedLength = conf.get(conf.supybot.reply.mores.length,
                         relay.targetChannel) or 470
                cont = _('(continuation)')
                remainingLength = allowedLength - len(cont) - 1
                head = s[0:allowedLength]
                tail = [cont + ' ' + s[i:i+remainingLength] for i in
                        range(allowedLength, len(s), remainingLength)]
                for s in [head] + tail:
                    msg = f(relay.targetChannel, s)
                    msg.tag('relayedMsg')
                    targetIRC.sendMsg(msg)

        if channel is None:
            for relay in self.relays:
                if not relay.hasSourceIRCChannels:
                    continue
                for channel in relay.sourceIRCChannels:
                    new_s = format_(relay, s, args)
                    if nick in relay.sourceIRCChannels[channel].users and \
                            relay.channelRegex.match(channel) and \
                            relay.networkRegex.match(irc.network)and \
                            relay.messageRegex.search(new_s):
                        send(new_s)
        else:
            for relay in self.relays:
                new_s = format_(relay, s, args)
                if relay.channelRegex.match(channel) and \
                        relay.networkRegex.match(irc.network)and \
                        relay.messageRegex.search(new_s):
                    send(new_s)


    @internationalizeDocstring
    def nicks(self, irc, msg, args, channel):
        """[<channel>]

        Returns the nicks of the people in the linked channels.
        <channel> is only necessary if the message
        isn't sent on the channel itself."""
        for relay in self.relays:
            if relay.sourceChannel == channel and \
                    relay.sourceNetwork == irc.network:
                if not world.getIrc(relay.targetNetwork):
                    irc.reply(_('Not connected to network %s.') %
                              relay.targetNetwork)
                else:
                    users = []
                    ops = []
                    halfops = []
                    voices = []
                    normals = []
                    numUsers = 0
                    target = relay.targetChannel

                    channels = world.getIrc(relay.targetNetwork).state.channels
                    found = False
                    for key, channel_ in channels.items():
                        if re.match(relay.targetChannel, key):
                            found = True
                            break
                    if not found:
                        continue

                    for s in channel_.users:
                        s = s.strip()
                        if not s:
                            continue
                        numUsers += 1
                        if s in channel_.ops:
                            users.append('@%s' % s)
                        elif s in channel_.halfops:
                            users.append('%%%s' % s)
                        elif s in channel_.voices:
                            users.append('+%s' % s)
                        else:
                            users.append(s)
                    #utils.sortBy(ircutils.toLower, ops)
                    #utils.sortBy(ircutils.toLower, halfops)
                    #utils.sortBy(ircutils.toLower, voices)
                    #utils.sortBy(ircutils.toLower, normals)
                    users.sort()
                    msg.tag('relayedMsg')
                    s = _('%d users in %s on %s:  %s') % (numUsers,
                            relay.targetChannel,
                            relay.targetNetwork,
                            utils.str.commaAndify(users))
                    irc.reply(s)
        irc.noReply()
    nicks = wrap(nicks, ['Channel'])


    # The fellowing functions handle configuration
    def _writeToConfig(self, from_, to, regexp, add):
        from_, to = from_.split('@'), to.split('@')
        args = from_
        args.extend(to)
        args.append(regexp)
        s = ' | '.join(args)

        currentConfig = self.registryValue('relays')
        config = list(map(ircutils.IrcString, currentConfig.split(' || ')))
        if add == True:
            if s in config:
                return False
            if currentConfig == '':
                self.setRegistryValue('relays', value=s)
            else:
                self.setRegistryValue('relays',
                                      value=' || '.join((currentConfig, s)))
        else:
            if s not in config:
                return False
            config.remove(s)
            self.setRegistryValue('relays', value=' || '.join(config))
        return True

    def _parseOptlist(self, irc, msg, tupleOptlist):
        optlist = {}
        for key, value in tupleOptlist:
            optlist.update({key: value})
        if 'from' not in optlist and 'to' not in optlist:
            irc.error(_('You must give at least --from or --to.'))
            return
        for name in ('from', 'to'):
            if name not in optlist:
                optlist.update({name: '%s@%s' % (msg.args[0], irc.network)})
        if 'regexp' not in optlist:
            optlist.update({'regexp': ''})
        if 'reciprocal' in optlist:
            optlist.update({'reciprocal': True})
        else:
            optlist.update({'reciprocal': False})
        if not len(optlist['from'].split('@')) == 2:
            irc.error(_('--from should be like "--from #channel@network"'))
            return
        if not len(optlist['to'].split('@')) == 2:
            irc.error(_('--to should be like "--to #channel@network"'))
            return
        return optlist

    @internationalizeDocstring
    def add(self, irc, msg, args, optlist):
        """[--from <channel>@<network>] [--to <channel>@<network>] [--regexp <regexp>] [--reciprocal]

        Adds a relay to the list. You must give at least --from or --to; if
        one of them is not given, it defaults to the current channel@network.
        Only messages matching <regexp> will be relayed; if <regexp> is not
        given, everything is relayed.
        If --reciprocal is given, another relay will be added automatically,
        in the opposite direction."""
        optlist = self._parseOptlist(irc, msg, optlist)
        if optlist is None:
            return

        failedWrites = 0
        if not self._writeToConfig(optlist['from'], optlist['to'],
                                   optlist['regexp'], True):
            failedWrites += 1
        if optlist['reciprocal']:
            if not self._writeToConfig(optlist['to'], optlist['from'],
                                       optlist['regexp'], True):
                failedWrites +=1

        self._loadFromConfig()
        if failedWrites == 0:
            irc.replySuccess()
        else:
            irc.error(_('One (or more) relay(s) already exists and has not '
                        'been added.'))
    add = wrap(add, [('checkCapability', 'admin'),
                     getopts({'from': 'something',
                              'to': 'something',
                              'regexp': 'something',
                              'reciprocal': ''})])

    @internationalizeDocstring
    def remove(self, irc, msg, args, optlist):
        """[--from <channel>@<network>] [--to <channel>@<network>] [--regexp <regexp>] [--reciprocal]

        Remove a relay from the list. You must give at least --from or --to; if
        one of them is not given, it defaults to the current channel@network.
        Only messages matching <regexp> will be relayed; if <regexp> is not
        given, everything is relayed.
        If --reciprocal is given, another relay will be removed automatically,
        in the opposite direction."""
        optlist = self._parseOptlist(irc, msg, optlist)
        if optlist is None:
            return

        failedWrites = 0
        if not self._writeToConfig(optlist['from'], optlist['to'],
                                   optlist['regexp'], False):
            failedWrites += 1
        if optlist['reciprocal']:
            if not self._writeToConfig(optlist['to'], optlist['from'],
                                       optlist['regexp'], False):
                failedWrites +=1

        self._loadFromConfig()
        if failedWrites == 0:
            irc.replySuccess()
        else:
            irc.error(_('One (or more) relay(s) did not exist and has not '
                        'been removed.'))
    remove = wrap(remove, [('checkCapability', 'admin'),
                     getopts({'from': 'something',
                              'to': 'something',
                              'regexp': 'something',
                              'reciprocal': ''})])

    def _getSubstitutes(self):
        # Get a list of strings
        substitutes = self.registryValue('substitutes').split(' || ')
        if substitutes == ['']:
            return {}
        # Convert it to a list of tuples
        substitutes = [tuple(x.split(' | ')) for x in substitutes]
        # Finally, make a dictionnary
        substitutes = dict(substitutes)

        return substitutes

    def _setSubstitutes(self, substitutes):
        # Get a list of tuples from the dictionnary
        substitutes = substitutes.items()
        # Make it a list of strings
        substitutes = ['%s | %s' % (x,y) for x,y in substitutes]
        # Finally, get a string
        substitutes = ' || '.join(substitutes)

        self.setRegistryValue('substitutes', value=substitutes)


    @internationalizeDocstring
    def substitute(self, irc, msg, args, regexp, to):
        """<regexp> <replacement>

        Replaces all nicks that matches the <regexp> by the <replacement>
        string."""
        substitutes = self._getSubstitutes()
        # Don't check if it is already in the config: if will be overriden
        # automatically and that is a good thing.
        substitutes.update({regexp: to})
        self._setSubstitutes(substitutes)
        self._loadFromConfig()
        irc.replySuccess()
    substitute = wrap(substitute, [('checkCapability', 'admin'),
                                   'something',
                                   'text'])

    @internationalizeDocstring
    def nosubstitute(self, irc, msg, args, regexp):
        """<regexp>

        Undo a substitution."""
        substitutes = self._getSubstitutes()
        if regexp not in substitutes:
            irc.error(_('This regexp was not in the nick substitutions '
                        'database'))
            return
        # Don't check if it is already in the config: if will be overriden
        # automatically and that is a good thing.
        substitutes.pop(regexp)
        self._setSubstitutes(substitutes)
        self._loadFromConfig()
        irc.replySuccess()
    nosubstitute = wrap(nosubstitute, [('checkCapability', 'admin'),
                                       'something'])



Class = LinkRelay

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2010, quantumlemur
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

from supybot.test import *

class LinkRelayTestCase(ChannelPluginTestCase):
    plugins = ('LinkRelay','Config', 'User')

    def testAdd(self):
        self.assertNotError('config supybot.plugins.LinkRelay.relays ""')
        self.assertNotError('linkrelay add --from #foo@bar --to #baz@bam')
        self.assertResponse('config supybot.plugins.LinkRelay.relays',
                            '#foo | bar | #baz | bam | ')

        self.assertNotError('config supybot.plugins.LinkRelay.relays ""')
        self.assertNotError('linkrelay add --from #foo@bar --to #baz@bam '
                            '--reciprocal')
        self.assertResponse('config supybot.plugins.LinkRelay.relays',
                            '#foo | bar | #baz | bam |  || '
                            '#baz | bam | #foo | bar | ')

        self.assertNotError('config supybot.plugins.LinkRelay.relays ""')
        self.assertNotError('linkrelay add --from #foo@bar')
        self.assertResponse('config supybot.plugins.LinkRelay.relays',
                            '#foo | bar | #test | test | ')

        self.assertNotError('config supybot.plugins.LinkRelay.relays ""')
        self.assertNotError('linkrelay add --to #foo@bar')
        self.assertResponse('config supybot.plugins.LinkRelay.relays',
                            '#test | test | #foo | bar | ')

        self.assertRegexp('linkrelay add --to #foo@bar', 'already exists')
        self.assertRegexp('linkrelay add --to #FOO@bar', 'already exists')

    def testRemove(self):
        self.assertNotError('config supybot.plugins.LinkRelay.relays '
                            '"#foo | bar | #baz | bam | "')
        self.assertNotError('linkrelay remove --from #foo@bar --to #baz@bam')
        self.assertResponse('config supybot.plugins.LinkRelay.relays', ' ')

    def testSubstitute(self):
        self.assertNotError('config supybot.plugins.LinkRelay.substitutes ""')
        self.assertNotError('linkrelay substitute foobar foo*bar')
        self.assertResponse('config supybot.plugins.LinkRelay.substitutes',
                            'foobar | foo*bar')
        self.assertNotError('linkrelay substitute baz b*z')
        try:
            self.assertResponse('config supybot.plugins.LinkRelay.substitutes',
                                'baz | b*z || foobar | foo*bar')
        except AssertionError:
            self.assertResponse('config supybot.plugins.LinkRelay.substitutes',
                                'foobar | foo*bar || baz | b*z')

    def testNoSubstitute(self):
        self.assertNotError('config supybot.plugins.LinkRelay.substitutes '
                            'foobar | foo*bar || baz | b*z')
        self.assertNotError('linkrelay nosubstitute baz')
        self.assertResponse('config supybot.plugins.LinkRelay.substitutes',
                            'foobar | foo*bar')
        self.assertNotError('linkrelay nosubstitute foobar')
        self.assertResponse('config supybot.plugins.LinkRelay.substitutes', ' ')



# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:


########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('ListEmpty')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('ListEmpty', True)


ListEmpty = conf.registerPlugin('ListEmpty')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(ListEmpty, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('ListEmpty')

@internationalizeDocstring
class ListEmpty(callbacks.Plugin):
    """Add the help for "@plugin help ListEmpty" here
    This should describe *how* to use this plugin."""

    def listempty(self, irc, msg, args, max_):
        """<Maximum number of users>

        Returns the list of channels with a few users."""
        results = []
        for (channel, c) in irc.state.channels.iteritems():
            if len(c.users) < max_:
                results.append('%s (%i)' % (channel, len(c.users)))
        irc.reply(', '.join(results))
    listempty = wrap(listempty, ['admin', 'int'])


Class = ListEmpty


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class ListEmptyTestCase(PluginTestCase):
    plugins = ('ListEmpty',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2010, quantumlemur
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry

from supybot.i18n import PluginInternationalization
from supybot.i18n import internationalizeDocstring
_ = PluginInternationalization('Listener')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Listener', True)


Listener = conf.registerPlugin('Listener')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Listener, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))

conf.registerGlobalValue(Listener, 'relays',
    registry.String('[]', _("""JSON-formatted relays. Do not edit this
    configuration variable unless you know what you are doing.""")))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2010, quantumlemur
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import json
import time
import socket
import threading
import traceback
import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks

from supybot.i18n import PluginInternationalization
from supybot.i18n import internationalizeDocstring
_ = PluginInternationalization('Listener')

def serialize_relay(relay):
    format_ = _('from %(host)s:%(port)s to %(channel)s@%(network)s')
    return format_ % relay

class Listener(callbacks.Plugin):
    """Add the help for "@plugin help Listener" here
    This should describe *how* to use this plugin."""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(Listener, self)
        self.__parent.__init__(irc)
        self.listenerThreads = []
        try:
            conf.supybot.plugins.Listener.relays.addCallback(
                    self._loadFromConfig)
        except registry.NonExistentRegistryEntry:
            log.error("Your version of Supybot is not compatible with "
                      "configuration hooks. So, Listener won't be able "
                      "to reload the configuration if you use the Config "
                      "plugin.")
        self._loadFromConfig()

    def _loadFromConfig(self, name=None):
        relays = json.loads(self.registryValue('relays'))
        for thread in self.listenerThreads:
            thread.active = False
            thread.listener.close()
        time.sleep(2)
        self.listenerThreads = []
        for relay in relays:
            try:
                log.debug('Starting listener thread: %s' %
                        serialize_relay(relay))
                thread = self.ListeningThread(**relay)
                thread.start()
                self.listenerThreads.append(thread)
            except TypeError:
                irc.error('Cannot load relay: %s' % serialize_relay(relay))


    class ListeningThread(threading.Thread):
        def __init__(self, network, channel, host, port):
            threading.Thread.__init__(self)
            self.network = network
            self.channel = channel
            self.host = host
            self.port = port
            self.buffer = ''
            self.active = True
            self.listener = socket.socket()
            self.listener.settimeout(0.5)
            self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listener.bind((self.host, self.port))
            self.listener.listen(4)

        def run(self):
            while self.active:
                try:
                    conn, addr = self.listener.accept()
                    self.buffer = conn.recv(4092).split('\n')[0].rstrip('\r')
                    conn.close()
                except IOError:
                    pass
                if self.buffer:
                    for IRC in world.ircs:
                        if IRC.network == self.network:
                            try:
                                IRC.queueMsg(ircmsgs.privmsg(self.channel, self.buffer))
                            except Exception as e:
                                traceback.print_exc(e)
                    self.buffer = ''
            self.listener.close()

    def add(self, irc, msg, args, channel, network, host, port):
        """[<channel>] [<network>] <host> <port>

        Start listening on <host>:<port> and relays messages to <channel> @
        <network>.
        <channel> and <network> default to the current ones."""
        relays = json.loads(self.registryValue('relays'))
        relay = {'channel': channel, 'network': network.network,
            'host': host, 'port': port}
        if relay in relays:
            irc.error(_('This relay already exists.'), Raise=True)
        relays.append(relay)
        self.setRegistryValue('relays', value=json.dumps(relays))
        self._loadFromConfig()
        irc.replySuccess()
    add = wrap(add, ['channel', 'networkIrc', 'somethingWithoutSpaces',
        ('int', 'port', lambda x: (x<65536))])

    def remove(self, irc, msg, args, channel, network, host, port):
        """[<channel>] [<network>] <host> <port>

        Start listening on <host>:<port> and relays messages to <channel> @
        <network>.
        <channel> and <network> default to the current ones."""
        relays = json.loads(self.registryValue('relays'))
        relay = {'channel': channel, 'network': network.network,
            'host': host, 'port': port}
        try:
            relays.remove(relay)
        except ValueError:
            irc.error(_('This relay does not exist.'), Raise=True)
        self.setRegistryValue('relays', value=json.dumps(relays))
        self._loadFromConfig()
        irc.replySuccess()
    remove = wrap(remove, ['channel', 'networkIrc', 'somethingWithoutSpaces',
        ('int', 'port', lambda x: (x<65536))])

    def list(self, irc, msg, args):
        """takes no arguments

        Return a list of all relays."""
        relays = json.loads(self.registryValue('relays'))
        irc.replies([serialize_relay(x) for x in relays])
    list = wrap(list)

    def stop(self, irc, msg, args):
        """takes no arguments

        Tries to close all listening sockets"""
        for thread in self.listenerThreads:
            thread.active = False
            thread.listener.close()
        self.listenerThreads = []
        irc.replySuccess()
    stop = wrap(stop)

    def die(self):
        for thread in self.listenerThreads:
            thread.active = False
            thread.listener.close()
        self.listenerThreads = []
        time.sleep(2)

Class = Listener


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2010, quantumlemur
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class ListenerTestCase(PluginTestCase):
    plugins = ('Listener',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('MegaHAL')
except:
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('MegaHAL', True)


MegaHAL = conf.registerPlugin('MegaHAL')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(MegaHAL, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))

conf.registerGroup(MegaHAL, 'learn')
conf.registerGlobalValue(MegaHAL.learn, 'commands',
    registry.Boolean(False, _("""Determines whether the bot answers to messages
    beginning by a non-alphanumeric char.""")))
conf.registerGroup(MegaHAL, 'answer')
conf.registerChannelValue(MegaHAL.answer, 'commands',
    registry.Boolean(False, _("""Determines whether messages beginning by a
    non-alphanumeric char are learned.""")))
conf.registerChannelValue(MegaHAL.answer, 'probability',
    registry.Integer(10, _("""Determines the percent of messages the bot will
    answer (zero is recommended if you have a tiny database).""")))
conf.registerChannelValue(MegaHAL.answer, 'probabilityWhenAddressed',
    registry.Integer(100, _("""Determines the percent of messages adressed to
    the bot the bot will answer.""")))



# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import re
import os
import sys
import random
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

if sys.version_info[0] < 3:
    from cStringIO import StringIO
else:
    from io import StringIO

try:
    import mh_python as megahal
except ImportError:
    raise callbacks.Error('You need to have MegaHAL installed to use this '
                          'plugin.  Download it at '
                          '<http://megahal.alioth.debian.org/>'
                          'or with <apt-get install megahal>')

try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('MegaHAL')
except:
    # This are useless function that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

class MegaHAL(callbacks.Plugin):
    """This plugins provides a MegaHAL integration for Supybot.
    MegaHAL must be installed ('apt-get install megahal' on Debian)"""
    callAfter = ['MoobotFactoids', 'Factoids', 'Infobot']
    callBefore = ['Dunno']
    
    def __init__(self, irc):
        # Call Supybot's scripts
        self.__parent = super(MegaHAL, self)
        self.__parent.__init__(irc)
        
        # Save state
        saved = (sys.stdout, os.getcwd())
        
        # Create proxy for MegaHAL
        os.chdir(conf.supybot.directories.data())
        sys.stdout = StringIO()
        
        # Initialize MegaHAL
        megahal.initbrain()
        
        # Restore state
        sys.stdout, cwd = saved
        os.chdir(cwd)
        
        random.seed()
    
    _dontKnow = [
                 'I don\'t know enough to answer you yet!',
                 'I am utterly speechless!',
                 'I forgot what I was going to say!'
                ]
    _translations = {
                     'I don\'t know enough to answer you yet!':
                         _('I don\'t know enough to answer you yet!'),
                     'I am utterly speechless!':
                         _('I am utterly speechless!'),
                     'I forgot what I was going to say!':
                         _('I forgot what I was going to say!'),
                    }

    def _response(self, msg, prb, reply):
        if random.randint(0, 100) < prb:
            response = megahal.doreply(msg)
            if self._translations.has_key(response):
                response = self._translations[response]
            reply(response, prefixNick=False)
        else:
            megahal.learn(msg)

    def doPrivmsg(self, irc, msg):
        if not msg.args[0].startswith('#'): # It is a private message
            return
        message = msg.args[1]
        
        if message.startswith(irc.nick) or re.match('\W.*', message):
            # Managed by invalidCommand
            return
        
        probability = self.registryValue('answer.probability', msg.args[0])
        self._response(message, probability, irc.reply)

    def invalidCommand(self, irc, msg, tokens):
        if not msg.args[0].startswith('#'): # It is a private message
            # Actually, we would like to answer, but :
            # 1) It may be a mistyped identify command (or whatever)
            # 2) MegaHAL can't reply without learning
            return
        message = msg.args[1]
        usedToStartWithNick = False
        if message.startswith(message):
            parsed = re.match('(.+ |\W)?(?P<message>\w.*)', message)
            message = parsed.group('message')
            usedToStartWithNick = True
        if self.registryValue('answer.commands') or usedToStartWithNick:
            self._response(message,
                        self.registryValue('answer.probabilityWhenAddressed',
                                           msg.args[0]),
                        irc.reply)
        elif self.registryValue('learn.commands'):
            megahal.learn(message)
    
    @internationalizeDocstring
    def cleanup(self, irc, msg, args):
        """takes no argument
        
        Saves MegaHAL brain to disk."""
        megahal.cleanup()
        irc.replySuccess()

Class = MegaHAL


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class MegaHALTestCase(PluginTestCase):
    plugins = ('MegaHAL',)
    
    def testCleanup(self):
        self.assertNotError('cleanup')
    
    def testAnswer(self):
        self.assertNotRegexp('foo', '.*not a valid.*')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry

try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('MilleBornes')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('MilleBornes', True)


MilleBornes = conf.registerPlugin('MilleBornes')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(MilleBornes, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import world.testing as testing
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('MilleBornes')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x


@internationalizeDocstring
class MilleBornes(callbacks.Plugin):
    pass
Class = MilleBornes


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class MilleBornesTestCase(PluginTestCase):
    plugins = ('MilleBornes',)
    def testInit(self):
        self.prefix = 'test!foo@bar'
        self.assertRegexp('start', 'test started.*')
        self.assertError('start')
        self.assertRegexp('drivers', '.*test.*')
        self.assertError('drive')
        self.assertResponse('abandon', 'test has left the game')
        self.assertNotRegexp('drivers', '.*test.*')
        self.assertResponse('drive', 'test is now playing!')
        self.assertRegexp('drivers', '.*test.*')
        self.prefix = 'foo!bar@baz'
        self.assertResponse('drive', 'foo is now playing!')
        self.assertRegexp('drivers', '.*test.*foo.*')
        self.assertError('drive')
        self.prefix = 'test!bar!baz'
        self.assertError('drive')
        self.prefix = 'foo!bar@baz'
        self.assertResponse('abandon', 'foo has left the game')
        self.assertRegexp('drivers', '.*test.*')
        self.assertResponse('drive', 'test is now playing!')
        self.assertRegexp('drivers', '.*foo.*test.*')
        self.prefix = 'test!bar!baz'
        self.assertResponse('abandon', 'test has left the game')
        self.assertRegexp('drivers', '.*foo.*')
        self.assertNoError('go')

    def testCheckCards(self):
        self.assertNoError('start')
        self.assertNoError('go')
        self.assertError('play 250', 'Allow cards that doesn\'t exist.')
        self.assertNoError('setcards', '50 50 50 50 50 50 50')
        self.assertError('play 100')

    def testReachGoal(self):
        self.assertNoError('start')
        self.assertNoError('go')
        self.assertNoError('setcards', '200 200 200 200 200 200 200')
        for i in range(0, 4):
            self.assertNotRegexp('play 200', '.*win.*')
        self.assertRegexp('play 200', '.*win.*')

    def testDoesntReachGoal(self):
        self.assertNoError('start')
        self.assertNoError('go')
        self.assertNoError('setcards', '200 200 200 200 200 100 50')
        for i in range(0, 3):
            self.assertNoError('play 200')
        self.assertNoError('play 100')
        self.assertError('play 200')
        self.assertError('play 50') # Has loosed the game, so he cannot play


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import json
import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('NoisyKarma')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('NoisyKarma', True)

def value_validator(value):
    if not isinstance(value, list):
        return _('Dict key must be a list')
    for subvalue in value:
        if not isinstance(subvalue, dict):
            return _('List items must be dicts.')
        if set(value.keys()) != set(['action', 'message']):
            return _('List items must be dicts with "action" and "message" '
                    'as keys.')
    return None

class KarmaMessages(registry.Json):
    def set(self, v):
        try:
            data = json.loads(v)
        except ValueError:
            self.error(_('Value must be json data.'))
            return
        if not isinstance(data, dict):
            self.error(_('Value must be a json dict.'))
            return
        if any(map(lambda x:not isinstance(x, int), data.keys())):
            self.error(_('Dict keys must be integers.'))
            return
        if any(map(lambda x:x<=0, data.keys())):
            self.error(_('Dict keys must be non-negative integers.'))
            return
        errors = list(filter(bool, map(value_validator, data.values())))
        if errors:
            self.error(errors[0])
            return
        self.setValue(data)

NoisyKarma = conf.registerPlugin('NoisyKarma')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(NoisyKarma, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))
conf.registerGroup(NoisyKarma, 'messages')
conf.registerChannelValue(NoisyKarma.messages, 'positive',
    KarmaMessages({}, _("""Messages shown for things with positive karma.
    For a given karma, the message with the closest key to the karma will
    be selected, among messages with a key greater than the karma.""")))
conf.registerChannelValue(NoisyKarma.messages, 'negative',
    KarmaMessages({}, _("""Messages shown for things with negative karma.
    For a given absolute karma, the message with the closest key to the
    karma will be selected, among messages with an absolute key greater
    than the absolute karma""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('NoisyKarma')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

class NoisyKarma(callbacks.Plugin):
    """Add the help for "@plugin help NoisyKarma" here
    This should describe *how* to use this plugin."""

    def doPrivmsg(self, irc, msg):
        Karma = irc.getCallback('Karma')
        channel = msg.args[0]
        if Karma and not msg.addressed and not msg.repliedTo and \
                irc.isChannel(channel):
            (L, neutrals) = Karma.db.gets(channel, msg.args[1].split(' ')) 
            if not L:
                return
            (thing, karma) = L[0] if abs(L[0][1]) > abs(L[-1][1]) else L[-1]
            if karma > 0:
                registry_value = conf.supybot.plugins.NoisyKarma.messages.positive
            elif karma < 0:
                registry_value = conf.supybot.plugins.NoisyKarma.messages.negative
                karma = -karma
            else:
                return
            registry_value = registry_value.get(channel)
            last_key = 0
            last_value = None
            for key, value in sorted(registry_value().items(), key=lambda x:x[0]):
                if int(key) > karma:
                    break
                (last_key, last_value) = (key, value)
            if last_key == 0:
                return
            msg = last_value['message']
            try:
                msg %= thing
            except TypeError:
                pass
            irc.reply(msg, action=last_value['action'], prefixNick=False)

    @wrap(['channel', 'int', getopts({'action': ''}), 'text'])
    def add(self, irc, msg, args, channel, karma, tuple_optlist, message):
        """[<channel>] <min karma> [--action] <msg>

        Adds a new <msg> to be triggered when a thing with a positive
        (respectively negative) karma greater than (resp. lower than)
        <min karma> is saw on the <channel>."""
        optlist = {}
        for key, value in tuple_optlist:
            optlist.update({key: value})
        if karma > 0:
            registry_value = conf.supybot.plugins.NoisyKarma.messages.positive
        elif karma < 0:
            registry_value = conf.supybot.plugins.NoisyKarma.messages.negative
            karma = -karma
        else:
            irc.error(_('Karma cannot be null.', Raise=True))
        registry_value = registry_value.get(channel)
        with registry_value.editable() as rv:
            if str(karma) in rv:
                # Why do we need this????
                del rv[str(karma)]
            rv[karma] = {'action': 'action' in optlist, 'message': message}
        irc.replySuccess()

    @wrap(['channel', 'int'])
    def remove(self, irc, msg, args, channel, tuple_optlist, karma):
        """[<channel>] <min karma>

        Removes the message associated with <thing> and <min karma>."""
        optlist = {}
        for key, value in tuple_optlist:
            optlist.update({key: value})
        if karma > 0:
            registry_value = conf.supybot.plugins.NoisyKarma.messages.positive
        elif karma < 0:
            registry_value = conf.supybot.plugins.NoisyKarma.messages.negative
            karma = -karma
        else:
            irc.error(_('Karma cannot be null.', Raise=True))
        registry_value = registry_value.get(channel)
        with registry_value.editable() as rv:
            del rv[karma]
        irc.replySuccess()


Class = NoisyKarma


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
from supybot.test import *

class NoisyKarmaTestCase(ChannelPluginTestCase):
    plugins = ('NoisyKarma', 'Karma')

    def setUp(self):
        super(NoisyKarmaTestCase, self).setUp()
        conf.supybot.plugins.NoisyKarma.messages.positive.get(self.channel).set('{}')
        conf.supybot.plugins.NoisyKarma.messages.negative.get(self.channel).set('{}')

    def testPositive(self):
        self.assertSnarfNoResponse('foo')
        self.assertNotError('noisykarma add 2 Interesting, %s.')
        self.assertNotError('noisykarma add 4 %s is cool!')
        self.assertSnarfNoResponse('foo')
        self.assertNoResponse('foo++')
        self.assertSnarfNoResponse('foo')
        self.assertNoResponse('foo++')
        self.assertSnarfResponse('foo', 'Interesting, foo.')
        self.assertNoResponse('foo++')
        self.assertSnarfResponse('foo', 'Interesting, foo.')
        self.assertNoResponse('foo++')
        self.assertSnarfResponse('foo', 'foo is cool!')
        self.assertNoResponse('foo++')
        self.assertSnarfResponse('foo', 'foo is cool!')
        self.assertNoResponse('foo--')
        self.assertSnarfResponse('foo', 'foo is cool!')
        self.assertNoResponse('foo--')
        self.assertSnarfResponse('foo', 'Interesting, foo.')

    def testNegative(self):
        self.assertNotError('noisykarma add -2 Eww, %s.')
        self.assertNotError('noisykarma add -4 Oh no, not %s!')
        self.assertSnarfNoResponse('bar')
        self.assertNoResponse('bar--')
        self.assertSnarfNoResponse('bar')
        self.assertNoResponse('bar--')
        self.assertSnarfResponse('bar', 'Eww, bar.')
        self.assertNoResponse('bar--')
        self.assertSnarfResponse('bar', 'Eww, bar.')
        self.assertNoResponse('bar--')
        self.assertSnarfResponse('bar', 'Oh no, not bar!')

    def testAction(self):
        self.assertNotError('noisykarma add -2 --action doesn\'t like %s.')
        self.assertSnarfNoResponse('baz')
        self.assertNoResponse('baz--')
        self.assertSnarfNoResponse('baz')
        self.assertNoResponse('baz--')
        self.assertSnarfResponse('baz', '\x01ACTION doesn\'t like baz.\x01')

    def testOverwrite(self):
        self.assertNotError('noisykarma add -2 --action doesn\'t like %s.')
        self.assertSnarfNoResponse('qux')
        self.assertNoResponse('qux--')
        self.assertSnarfNoResponse('qux')
        self.assertNoResponse('qux--')
        self.assertSnarfResponse('qux', '\x01ACTION doesn\'t like qux.\x01')
        self.assertNotError('noisykarma add -2 Eww, %s.')
        self.assertNoResponse('qux--')
        self.assertSnarfResponse('qux', 'Eww, qux.')
        

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('NoLatin1')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('NoLatin1', True)


NoLatin1 = conf.registerPlugin('NoLatin1')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(NoLatin1, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))
conf.registerChannelValue(NoLatin1, 'enable',
        registry.Boolean(False, _("""Determines whether or not the bot will
        notice chatters they have to use Unicode instead of Latin-1.""")))
conf.registerChannelValue(NoLatin1, 'remember',
        registry.Integer(3600, _("""After this time (in seconds), the number
        of warnings will be reset.""")))
conf.registerChannelValue(NoLatin1, 'maxWarningsBeforeAlert',
        registry.Integer(5, _("""After a certain number of warning, the bot
        will call someone (defined in supybot.plugins.NoLatin1.operator)""")))
conf.registerChannelValue(NoLatin1, 'operator',
        registry.String('KwisatzHaderach', _("""The person the bot will alert
        when a user insists in using Latin-1""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import time
import chardet
import supybot.log as log
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('NoLatin1')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

@internationalizeDocstring
class NoLatin1(callbacks.Plugin):
    """Add the help for "@plugin help NoLatin1" here
    This should describe *how* to use this plugin."""

    _warnings = {}

    def doPrivmsg(self, irc, msg):
        channel = msg.args[0]
        content = msg.args[1]
        if not self.registryValue('enable', channel):
            return
        encoding = chardet.detect(content)['encoding']
        if encoding not in ('utf-8', 'ascii'):
            log.info('Warning %s (using %s)' % (msg.prefix, encoding))
            self._warn(irc, channel, msg.prefix.split('!')[0])

    def _warn(self, irc, channel, nick):
        id_ = '%s@%s' % (nick, channel)
        if id_ in self._warnings:
            warnLevel = self._warnings[id_]
            remember = self.registryValue('remember',channel)
            if warnLevel[0] < time.time() - remember:
                warnLevel = 1 # Reset to 0 + 1
            else:
                warnLevel = warnLevel[1] + 1
        else:
            warnLevel = 1
        self._warnings.update({id_: (time.time(), warnLevel)})
        maxWarningsBeforeAlert = self.registryValue('maxWarningsBeforeAlert')
        operator = self.registryValue('operator')
        if warnLevel >= maxWarningsBeforeAlert:
            irc.reply(_('User %s is still using Latin-1 after %i alerts') %
                      (nick, maxWarningsBeforeAlert), private=True, to=operator)
            warnLevel = 0
        else:
            irc.reply(_('Please use Unicode/UTF-8 instead of '
                        'Latin1/ISO-8859-1 on %s.') % channel,
                      private=True)
        self._warnings.update({id_: (time.time(), warnLevel)})



Class = NoLatin1


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
# -*- coding: utf8 -*-
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import time
from supybot.test import *

class NoLatin1TestCase(ChannelPluginTestCase):
    plugins = ('NoLatin1',)
    config = {'supybot.reply.whenNotCommand': False,
              'supybot.plugins.NoLatin1.enable': True,
              'supybot.plugins.NoLatin1.remember': 2}

    def testNoLatin1(self):
        for foo in range(0, 4):
            self.assertRegexp('blah \xe9 blah', 'Please use.*')
        self.assertRegexp('blah \xe9 blah', 'User test is still.*')
        self.assertRegexp('blah \xe9 blah', 'Please use.*')

    def testNoWarningOnUnicode(self):
        msg = ircmsgs.privmsg(self.channel, 'Hi !', prefix=self.prefix)
        self.irc.feedMsg(msg)
        msg = self.irc.takeMsg()
        assert msg is None, msg
        msg = ircmsgs.privmsg(self.channel, 'é', prefix=self.prefix)
        self.irc.feedMsg(msg)
        msg = self.irc.takeMsg()
        assert msg is None, msg

    def testCleanUp(self):
        for foo in range(0, 4):
            self.assertRegexp('blah \xe9 blah', 'Please use.*')
        time.sleep(3)
        self.assertRegexp('blah \xe9 blah', 'Please use.*')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('OEIS')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('OEIS', True)


OEIS = conf.registerPlugin('OEIS')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(OEIS, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = oeis
# Author: Valentin Lorentz
# CC-0 license.
#
# Note that you have to follow OEIS' license.

import re
import sys
import logging

class InvalidEntry(Exception):
    pass

class ParseError(Exception):
    pass

class OEISEntry(dict):
    _assignments = {
            'A': 'author',
            'E': 'references',
            'O': 'offset',
            }
    _appendings = {
            'C': 'comments',
            'D': 'detreferences',
            'F': 'formula',
            'H': 'references',
            'e': 'examples',
            }
    _concatenations = {
            'p': 'maple',
            't': 'mathematica',
            'o': 'programming',
            }
    def __init__(self, fd, logger=None):
        self._logger = logger
        for key in ('sequence', 'signed'):
            self[key] = []
        for key in self._appendings.values():
            self[key] = []
        for key in self._concatenations.values():
            self[key] = ''
        for line in fd:
            line = line[0:-1]
            if not line:
                break
            if sys.version_info[0] >= 3 and isinstance(line, bytes):
                line = line.decode()
            if line.startswith('#'):
                continue
            try:
                (mode, id_, data) = line.split(' ', 2)
            except ValueError:
                (mode, id_) = line.split(' ', 1)
                data = None
            self['id'] = id_
            self._add(mode[1:], data)
        if not self['sequence']:
            raise InvalidEntry()
        for key in self._appendings.values():
            if not self[key]:
                del self[key]
        for key in self._concatenations.values():
            if not self[key]:
                del self[key]

    def _add(self, mode, data):
        if mode in self._assignments:
            self[self._assignments[mode]] = data
        elif mode in self._appendings:
            self[self._appendings[mode]].append(data)
        elif mode in self._concatenations:
            self[self._concatenations[mode]] += data
        elif mode == 'I':
            self['ids'] = data.split(' ') if data else None
        elif mode == 'K':
            self['keywords'] = data.split(',')
        elif mode == 'N':
            assert 'name' not in self
            self['name'] = data
        elif mode in 'STU':
            self['sequence'].extend([int(x) for x in data.split(',') if x])
        elif mode in 'VWX':
            self['signed'].extend([int(x) for x in data.split(',') if x])
        elif mode == 'Y':
            self['seealso'] = (data[len('Cf. '):-1]).split(', ')
        elif self._logger:
            self._logger.info('Unknown OEIS data mode: %s: %s' % (mode, data))



    _paging_regexp = re.compile('Showing ([0-9]+)-([0-9]+) of ([0-9]+)')

    @classmethod
    def query(cls, fd, logger=None):
        """Fetches a page from the OEIS.

        Return format: ((from, to, total), [results])"""
        paging = None
        for line in fd:
            line = line[0:-1]
            if sys.version_info[0] >= 3 and isinstance(line, bytes):
                line = line.decode()
            if line.startswith('No results.'):
                return ((0, 0, 0), [])
            if line.startswith('Showing '):
                match = cls._paging_regexp.match(line)
                paging = match.groups()
                break
        if not paging:
            raise ParseError
        fd.readline()
        results = []
        try:
            while True:
                results.append(cls(fd, logger))
        except InvalidEntry:
            pass
        return (paging, results)

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from string import Template

import supybot.log as log
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('OEIS')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

from .oeis import OEISEntry, ParseError

def query(logger, q):
    return OEISEntry.query(logger=logger,
            fd=utils.web.getUrlFd('http://oeis.org/search?fmt=text&q=%s' % q))

class OEIS(callbacks.Plugin):
    """Add the help for "@plugin help OEIS" here
    This should describe *how* to use this plugin."""
    threaded = True

    def _advsearch(self, irc, msg, args, format_, sequence):
        """<format> <sequence>

        Search with advanced formating options (Python dict-formating)."""
        try:
            (paging, results) = query(self.log, sequence)
        except ParseError:
            irc.error(_('Could not parse OEIS answer.'), Raise=True)
        if results:
            repl = Template(format_).safe_substitute
            irc.reply(format('%L', map(repl, results)))
        else:
            irc.reply(_('No entry matches this sequence.'))
    advsearch = wrap(_advsearch, ['something', 'somethingWithoutSpaces'])

    def _gen(format_, name, doc):
        def f(self, irc, msg, args, sequence):
            self._advsearch(irc, msg, args, format_, sequence)
        f.__doc__ = """<sequence>

        %s""" % doc
        return wrap(f, ['somethingWithoutSpaces'], name=name)

    names = _gen('$name ($id)', 'names',
            'Return names of matching entries.')


Class = OEIS


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class OEISTestCase(PluginTestCase):
    plugins = ('OEIS',)

    if network:
        def testNames(self):
            self.assertRegexp('names 1,2,6,24,120', '(?i)factorial.*(A000142)')
            self.assertRegexp('names 15454454651,198448,228454456', 'No entry')

        def testAdvsearch(self):
            self.assertRegexp('advsearch "$id" 1,2,6,24,120', 'A000142')
            self.assertNotRegexp('advsearch "$id" 1,2,6,24,120', 'factorial')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Pinglist')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Pinglist', True)


Pinglist = conf.registerPlugin('Pinglist')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Pinglist, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Pinglist')

@internationalizeDocstring
class Pinglist(callbacks.Plugin):
    """Add the help for "@plugin help Pinglist" here
    This should describe *how* to use this plugin."""

    def __init__(self, irc):
        super(Pinglist, self).__init__(irc)
        self._subscriptions = ircutils.IrcDict()

    @internationalizeDocstring 
    def pingall(self, irc, msg, args, channel, meeting):
        """[<channel>] <meeting>

        Ping all participants of the <meeting>.
        <channel> defaults to the current channel."""
        try:
            subscribers = self._subscriptions[channel][meeting]
        except KeyError:
            irc.error(_('No such meeting.'), Raise=True)
        if subscribers:
            irc.reply(format(_('Ping %L'), list(subscribers)))
        else:
            # Should not happen
            irc.error(_('No subscribers.'))
    pingall = wrap(pingall, ['channel', 'something'])

    @internationalizeDocstring
    def subscribe(self, irc, msg, args, channel, meeting):
        """[<channel>] <meeting>

        Subscribe to the <meeting>.
        <channel> defaults to the current channel."""
        if channel not in self._subscriptions:
            self._subscriptions[channel] = ircutils.IrcDict()
        if meeting not in self._subscriptions[channel]:
            self._subscriptions[channel][meeting] = ircutils.IrcSet()
        self._subscriptions[channel][meeting].add(msg.nick)
        irc.replySuccess()
    subscribe = wrap(subscribe, ['channel', 'something'])

    @internationalizeDocstring
    def unsubscribe(self, irc, msg, args, channel, meeting):
        """[<channel>] <meeting>

        Unsubscribe from the <meeting>.
        <channel> defaults to the current channel."""
        if channel not in self._subscriptions:
            irc.error(_('No such meeting.'))
        if meeting not in self._subscriptions[channel]:
            irc.error(_('No such meeting.'))
        try:
            self._subscriptions[channel][meeting].remove(msg.nick)
        except KeyError:
            irc.error(_('You did not subscribe.'), Raise=True)
        if not self._subscriptions[channel][meeting]:
            del self._subscriptions[channel][meeting]
        if not self._subscriptions[channel]:
            del self._subscriptions[channel]
        irc.replySuccess()
    unsubscribe = wrap(unsubscribe, ['channel', 'something'])





Class = Pinglist


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

prefixes = {'foo': 'foo!bar@baz',
            'qux': 'qux!quux@corge',
            'spam': 'spam!egg@test',
            'su': 'su!py@bot'}

class PinglistTestCase(ChannelPluginTestCase):
    plugins = ('Pinglist',)

    def testPing(self):
        self.prefix = prefixes['foo']
        self.assertResponse('pingall testing', 'Error: No such meeting.')
        self.assertNotError('subscribe testing')
        self.assertResponse('pingall testing', 'Ping foo')

        self.prefix = prefixes['qux']
        self.assertResponse('pingall testing', 'Ping foo')
        self.assertNotError('subscribe testing')
        self.assertRegexp('pingall testing', 'Ping (foo and qux|qux and foo)')
        self.assertResponse('pingall "something else"', 'Error: No such meeting.')
        self.assertNotError('subscribe "something else"')
        self.assertResponse('pingall "something else"', 'Ping qux')
        self.assertRegexp('pingall testing', 'Ping (foo and qux|qux and foo)')
        self.assertNotError('unsubscribe testing')
        self.assertResponse('pingall testing', 'Ping foo')
        self.assertResponse('unsubscribe testing', 'Error: You did not subscribe.')
        self.assertResponse('unsubscribe supybot', 'Error: No such meeting.')
        


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('PingTime')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('PingTime', True)


PingTime = conf.registerPlugin('PingTime')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(PingTime, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import time

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('PingTime')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

# TODO: Make this configurable/internationalizable
triggers_base = r'^((?P<nick>%s)[,:]? %%s|%%s (?P<nick2>%s))$' % \
        ((ircutils.nickRe.pattern[1:-1],)*2)
class PingTime(callbacks.PluginRegexp):
    """Add the help for "@plugin help PingTime" here
    This should describe *how* to use this plugin."""
    regexps = ('onPing', 'onPong')

    _pings = {} # {channel: {(from, to): timestamp}}

    def onPing(self, irc, msg, match):
        channel = msg.args[0]
        from_ = msg.nick
        to = match.group('nick') or match.group('nick2')
        if not ircutils.isChannel(channel):
            return
        if channel not in self._pings:
            self._pings[channel] = {}
        self._pings[channel][(from_, to)] = time.time()
    onPing.__doc__ = triggers_base % (('ping',)*2)

    def onPong(self, irc, msg, match):
        channel = msg.args[0]
        from_ = msg.nick
        to = match.group('nick') or match.group('nick2')
        if not ircutils.isChannel(channel):
            return
        try:
            pinged_at = self._pings[channel].pop((to, from_))
        except KeyError:
            return
        else:
            delta = time.time()-pinged_at
            if delta > 1:
                irc.reply(utils.str.format(_('Ping time: %T'), delta))

    onPong.__doc__ = triggers_base % (('pong',)*2)


Class = PingTime


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class PingTimeTestCase(ChannelPluginTestCase):
    plugins = ('PingTime',)

    def testBasics(self):
        self.assertSnarfNoResponse('pong foo', frm='bar!a@a',)
        self.assertSnarfNoResponse('ping bar', frm='foo!a@a')
        time.sleep(2)
        self.assertSnarfResponse('pong foo', 'bar: Ping time: 2 seconds',
                frm='bar!a@a',)
        self.assertSnarfNoResponse('foo, pong', frm='bar!a@a',)

        self.assertSnarfNoResponse('bar: ping', frm='foo!a@a')
        time.sleep(2)
        self.assertSnarfResponse('pong foo', 'bar: Ping time: 2 seconds',
                frm='bar!a@a',)
        self.assertSnarfNoResponse('pong foo', frm='bar!a@a',)

    def testFastReply(self):
        self.assertSnarfNoResponse('ping bar', frm='foo!a@a')
        time.sleep(0.5)
        self.assertSnarfNoResponse('pong foo', frm='bar!a@a',)
        time.sleep(2)
        self.assertSnarfNoResponse('pong foo', frm='bar!a@a',)

    


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('RateLimit')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('RateLimit', True)


RateLimit = conf.registerPlugin('RateLimit')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(RateLimit, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))
conf.registerChannelValue(RateLimit, 'error',
    registry.Boolean(False, _("""Determines whether an error message will
    be sent if a user reaches the rate limit.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import time

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('RateLimit')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

if not hasattr(callbacks.Commands, 'pre_command_callbacks'):
    raise callbacks.Error(
            'Your version of Supybot is not compatible with '
            'this plugin (it does not have support for '
            'pre-command-call callbacks).')

class RateLimitRecord(dbi.Record):
    __fields__ = ('channel', 'user', 'count', 'interval', 'command')
class RateLimitDB(dbi.DB):
    Record = RateLimitRecord
    def set_user_limit(self, channel, user, count, interval, command):
        record = RateLimitRecord(channel=channel, user=user, count=count,
                interval=interval, command=command)
        try:
            previous_record = list(filter(
                    lambda x:x.user == user and
                             x.command == command and
                             x.channel == channel,
                    self))[0]
        except IndexError:
            self.add(record)
        else:
            self.set(previous_record.id, record)
    def unset_user_limit(self, channel, user, command):
        try:
            record = list(filter(
                    lambda x:x.user == user and
                             x.command == command and
                             x.channel == channel,
                    self))[0]
        except IndexError:
            raise
        else:
            self.remove(record.id)

    def get_limits(self, command):
        return filter(lambda x:x.command == command, self)
    def get_user_limit(self, user, command):
        records = list(filter(lambda x:x.user in (user, '*', 'global'),
                         self.get_limits(command)))
        # TODO: Add channel support.
        try:
            return list(filter(lambda x:x.user == user, records))[0]
        except IndexError:
            return list(records)[0] # May raise IndexError too

filename = conf.supybot.directories.data.dirize('RateLimit.db')

def format_ratelimit(record):
    return _('%(count)s per %(interval)s sec') % {
            'count': record.count,
            'interval': record.interval
            }

class RateLimit(callbacks.Plugin):
    """Add the help for "@plugin help RateLimit" here
    This should describe *how* to use this plugin."""

    def __init__(self, irc):
        super(RateLimit, self).__init__(irc)
        self.db = RateLimitDB(filename)
        callbacks.Commands.pre_command_callbacks.append(
                self._pre_command_callback)
        self._history = {} # {command: [(user, timestamp)]}

    def die(self):
        callbacks.Commands.pre_command_callbacks.remove(
                self._pre_command_callback)

    def _pre_command_callback(self, plugin, command, irc, msg, *args, **kwargs):
        command = ' '.join(command)
        try:
            user = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            user = None
        try:
            record = self.db.get_user_limit(user, command)
        except IndexError:
            return False
        else:
            if command not in self._history:
                list_ = []
                self._history[command] = list_
            else:
                list_ = self._history[command]
            timestamp = time.time() - record.interval
            list_ = list(filter(lambda x:x[1] > timestamp and
                                         (x[0]==user or record.user=='global'),
                                list_))
            if len(list_) >= record.count:
                self.log.info('Throttling command %r call (rate limited).',
                        command)
                if self.registryValue('error', msg.args[0]):
                    irc.error(_('This command has been called more than {0} '
                                'times in the last {1} seconds.').format(
                              record.count, record.interval))
                return True
            list_.append((user, time.time()))
            self._history[command] = list_
            return False

    @wrap([optional(first('otherUser', ('literal', '*'))),
        'nonNegativeInt', 'nonNegativeInt', 'commandName', 'admin'])
    def set(self, irc, msg, args, user, count, interval, command):
        """[<user>] <how many in interval> <interval length> <command>

        Sets the rate limit of the <command> for the <user>.
        If <user> is not given, the rate limit will be enforced globally,
        and if * is given as the <user>, the rate limit will be enforced
        for everyone."""
        if user is None:
            user = 'global'
        elif user != '*':
            user = user.id
        self.db.set_user_limit(None, user, count, interval, command)
        irc.replySuccess()

    @wrap([optional(first('otherUser', ('literal', '*'))),
        'commandName', 'admin'])
    def unset(self, irc, msg, args, user, command):
        """[<user>] <command>

        Unsets the rate limit of the <command> for the <user>.
        If <user> is not given, the rate limit will be enforced globally,
        and if * is given as the <user>, the rate limit will be enforced
        for everyone."""
        if user is None:
            user = 'global'
        elif user != '*':
            user = user.id
        try:
            self.db.unset_user_limit(None, user, command)
        except IndexError:
            irc.error(_('This rate limit did not exist.'))
        else:
            irc.replySuccess()

    @wrap(['commandName'])
    def get(self, irc, msg, args, command):
        """<command>

        Return rate limits set for the given <command>."""
        records = self.db.get_limits(command)
        global_ = 'none'
        star = 'none'
        users = []
        for record in records:
            if record.user == 'global':
                global_ = format_ratelimit(record)
            elif record.user == '*':
                star = format_ratelimit(record)
            else:
                users.append('%s: %s' % (ircdb.users.getUser(record.user).name,
                                         format_ratelimit(record)))
        irc.reply(', '.join([_('global: %s') % global_,
                             _('*: %s') % star] +
                            users))



Class = RateLimit


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *
import supybot.conf as conf

class RateLimitTestCase(PluginTestCase):
    plugins = ('RateLimit', 'User', 'Utilities')

    def setUp(self):
        super(RateLimitTestCase, self).setUp()
        for name in ('foo', 'bar', 'baz'):
            self.assertNotError('register %s passwd' % name,
                    frm='%s!a@a' % name)

    def testSingleUser(self):
        self.assertResponse('ratelimit get echo',
                'global: none, *: none')
        self.assertNotError('ratelimit set foo 3 1 echo')
        self.assertResponse('ratelimit get echo',
                'global: none, *: none, foo: 3 per 1 sec')
        self.assertResponse('echo spam', 'spam', frm='foo!a@a')
        time.sleep(1.1)
        self.assertResponse('echo spam', 'spam', frm='foo!a@a')
        self.assertResponse('echo spam', 'spam', frm='foo!a@a')
        self.assertResponse('echo spam', 'spam', frm='foo!a@a')
        self.assertNoResponse('echo spam', frm='foo!a@a')
        self.assertResponse('echo spam', 'spam', frm='bar!a@a')
        with conf.supybot.plugins.RateLimit.Error.context(True):
            self.assertRegexp('echo spam', 'called more than 3 times',
                    frm='foo!a@a')

        time.sleep(1.1)

        self.assertNotError('ratelimit unset foo echo')
        self.assertResponse('ratelimit get echo',
                'global: none, *: none')
        self.assertResponse('echo spam', 'spam', frm='foo!a@a')
        self.assertResponse('echo spam', 'spam', frm='foo!a@a')
        self.assertResponse('echo spam', 'spam', frm='foo!a@a')
        self.assertResponse('echo spam', 'spam', frm='foo!a@a')

        self.assertRegexp('ratelimit unset foo echo',
                'Error:.*did not exist')

    def testStar(self):
        self.assertResponse('ratelimit get echo',
                'global: none, *: none')
        self.assertNotError('ratelimit set * 3 1 echo')
        self.assertResponse('ratelimit get echo',
                'global: none, *: 3 per 1 sec')
        self.assertResponse('echo spam', 'spam', frm='foo!a@a')
        self.assertResponse('echo spam', 'spam', frm='foo!a@a')
        self.assertResponse('echo spam', 'spam', frm='foo!a@a')
        self.assertNoResponse('echo spam', frm='foo!a@a')
        self.assertResponse('echo spam', 'spam', frm='bar!a@a')

    def testGlobal(self):
        self.assertResponse('ratelimit get echo',
                'global: none, *: none')
        self.assertNotError('ratelimit set 3 1 echo')
        self.assertResponse('ratelimit get echo',
                'global: 3 per 1 sec, *: none')
        self.assertResponse('echo spam', 'spam', frm='foo!a@a')
        self.assertResponse('echo spam', 'spam', frm='bar!a@a')
        self.assertResponse('echo spam', 'spam', frm='baz!a@a')
        self.assertNoResponse('echo spam', frm='foo!a@a')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('Rbls')
except:
    # These are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Rbls', True)


Rbls = conf.registerPlugin('Rbls')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Rbls, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))
conf.registerChannelValue(Rbls, 'enable',
    registry.Boolean(False, _("""Determines whether or not this plugin will
    kickban users blacklisted with Rbls.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Rbls')
except:
    # These are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x

class Rbls(callbacks.Plugin):
    """Add the help for "@plugin help Rbls" here
    This should describe *how* to use this plugin."""
    threaded = True

    def doJoin(self, irc, msg):
        channel = msg.args[0]
        if not self.registryValue('enable', channel):
            return
        nick, ident, host = ircutils.splitHostmask(msg.prefix)

        fd = utils.web.getUrlFd('http://rbls.org/%s' % host)
        line = ' '
        while line and not line.startswith('<title>'):
            line = fd.readline()
        if not line:
            return
        if 'is listed in' in line:
            irc.queueMsg(ircmsgs.ban(channel, '*!*@%s' % host))
            irc.queueMsg(ircmsgs.kick(channel, nick))
        else:
            assert 'is not listed' in line



Class = Rbls


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class RblsTestCase(ChannelPluginTestCase):
    plugins = ('Rbls',)
    config = {'supybot.plugins.Rbls.enable': 'True'}

    if network:
        def testBan(self):
            self.irc.feedMsg(ircmsgs.join(self.channel,
                                          prefix='foo!bar@166.205.64.165'))
            m = self.irc.takeMsg()
            self.assertNotEqual(m, None)
            self.assertEqual(m.command, 'MODE')
            m = self.irc.takeMsg()
            self.assertNotEqual(m, None)
            self.assertEqual(m.command, 'KICK')
        def testNoban(self):
            self.irc.feedMsg(ircmsgs.join(self.channel,
                                          prefix='foo!bar@88.175.48.15'))
            self.assertEqual(self.irc.takeMsg(), None)




# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Redmine')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Redmine', True)


Redmine = conf.registerPlugin('Redmine')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Redmine, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))

conf.registerGlobalValue(Redmine, 'sites',
    registry.Json({}, _("""JSON-formatted dict of site data. Don't edit
    this unless you known what you are doing. Use @site add and @site
    remove instead.""")))
conf.registerChannelValue(Redmine, 'defaultsite',
    registry.String('', _("""Default site for this channel.""")))
conf.registerGroup(Redmine, 'format')
conf.registerChannelValue(Redmine.format, 'projects',
    registry.String('$name ($identifier)',
    _("""Format of projects displayed by @projects.""")))
conf.registerChannelValue(Redmine.format, 'issues',
    registry.String('\x02#$id)i: $subject\x02 (last update: '
    '$updated_on / status: $status__name)',
    _("""Format of issues displayed by @issues.""")))
conf.registerChannelValue(Redmine.format, 'issue',
    registry.String('\x02#$id)i ($status__name)\x02: \x02$subject\x02 '
    'in \x02$project__name\x02 ($project__id)i). Created by '
    '\x02$author__name\x02 ($author__id)i) on \x02$created_on\x02, '
    'last updated on \x02$updated_on', 
    _("""Format of issues displayed by @issue.""")))
conf.registerGroup(Redmine.format, 'announces')
conf.registerChannelValue(Redmine.format.announces, 'issue',
    registry.String('Updated issue: \x02#$id)i ($status__name)\x02: '
    '\x02$subject\x02 in \x02$project__name\x02 ($project__id)i).',
    _("""Format of issues displayed by @issue.""")))

conf.registerGroup(Redmine, 'announce')
conf.registerChannelValue(Redmine.announce, 'sites',
    registry.SpaceSeparatedListOfStrings([],
    _("""List of sites announced on this channel.""")))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import sys
import json
import time
from string import Template

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Redmine')

class ResourceNotFound(Exception):
    pass

class AmbiguousResource(Exception):
    pass

class AccessDenied(Exception):
    pass

def fetch(site, uri, **kwargs):
    url = site['url'] + uri + '.json'
    if kwargs:
        url += '?' + utils.web.urlencode(kwargs).decode()
    try:
        data = utils.web.getUrl(url)
        if sys.version_info[0] >= 3:
            data = data.decode('utf8')
        return json.loads(data)
    except utils.web.Error:
        raise ResourceNotFound()

def flatten_subdicts(dicts):
    """Change dict of dicts into a dict of strings/integers. Useful for
    using in string formatting."""
    flat = {}
    for key, value in dicts.items():
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                flat['%s__%s' % (key, subkey)] = subvalue
        else:
            flat[key] = value
    return flat

def get_project(site, project):
    projects = []
    for variable in ('id', 'identifier', 'name'):
        projects = list(filter(lambda x:x[variable] == project,
                fetch(site, 'projects')['projects']))
        if projects:
            break
    projects = list(projects)
    if not projects:
        raise ResourceNotFound()
    elif len(projects) > 1:
        raise AmbiguousResource()
    else:
        return projects[0]

def get_project_or_error(irc, site, project):
    try:
        return get_project(site, project)
    except ResourceNotFound:
        irc.error(_('Project not found.'), Raise=True)
    except AmbiguousResource:
        irc.error(_('Ambiguous project name.'), Raise=True)

def get_user(site, user):
    if user.isdigit():
        return fetch(site, 'users/%s' % user)
    else:
        # TODO: Find a way to get user data from their name...
        # (authenticating as admin seems the only way)
        raise AccessDenied()

def get_user_or_error(irc, site, user):
    try:
        return get_user(site, user)
    except ResourceNotFound:
        irc.error(_('User not found.'), Raise=True)
    except AmbiguousResource:
        irc.error(_('Ambiguous user name.'), Raise=True)
    except AccessDenied:
        irc.error(_('Cannot get a user id from their name.'), Raise=True)

def handle_site_arg(wrap_args):
    """Decorator for handling the <site> argument of all commands, because
    I am lazy."""
    if 'project' in wrap_args:
        assert wrap_args[0] == 'project'
        wrap_args[0] = 'somethingWithoutSpaces'
        project = True
    else:
        project = False
    assert 'project' not in wrap_args
    wrap_args = [optional('somethingWithoutSpaces')] + wrap_args

    def decorator(f):
        def newf(self, irc, msg, args, site_name, *args2):
            if not site_name:
                site_name = self.registryValue('defaultsite', msg.args[0])
                if not site_name:
                    irc.error(_('No default site.'), Raise=True)
            sites = self.registryValue('sites')
            if site_name not in sites:
                irc.error(_('Invalid site name.'), Raise=True)
            site = sites[site_name]

            return f(self, irc, msg, args, site, *args2)
            
        newf.__doc__ = """[<site>] %s
            
            If <site> is not given, it defaults to the default set for this
            channel, if any.
            """ % f.__doc__
        return wrap(newf, wrap_args)
    return decorator

@internationalizeDocstring
class Redmine(callbacks.Plugin):
    """Add the help for "@plugin help Redmine" here
    This should describe *how* to use this plugin."""
    threaded = True

    _last_fetch = {} # {site: (time, data)}
    def __call__(self, irc, msg):
        super(Redmine, self).__call__(irc, msg)
        with self.registryValue('sites', value=False).editable() as sites:
            assert isinstance(sites, dict), repr(sites)
            for site_name, site in sites.items():
                if 'interval' not in site:
                    site['interval'] = 60
                if site_name in self._last_fetch:
                    last_time, last_data = self._last_fetch[site_name]
                    if last_time>time.time()-site['interval']:
                        continue
                data = fetch(site, 'issues', sort='updated_on:desc')
                self._last_fetch[site_name] = (time.time(), data)
                if 'last_time' not in locals():
                    continue
                try:
                    last_update = last_data['issues'][0]['updated_on']
                except IndexError:
                    # There was no issue submitted before
                    last_update = ''

                announces = []
                for issue in data['issues']:
                    if issue['updated_on'] <= last_update:
                        break
                    announces.append(issue)
                for channel in irc.state.channels:
                    if site_name in self.registryValue('announce.sites',
                            channel):
                        format_ = self.registryValue('format.announces.issue',
                                channel)
                        for issue in announces:
                            repl = flatten_subdicts(issue)
                            s = Template(format_).safe_substitute(repl)
                            if sys.version_info[0] < 3:
                                s = s.encode('utf8', errors='replace')
                            msg = ircmsgs.privmsg(channel, s)
                            irc.sendMsg(msg)



    class site(callbacks.Commands):
        conf = conf.supybot.plugins.Redmine
        @internationalizeDocstring
        def add(self, irc, msg, args, name, url):
            """<name> <base url>

            Add a site to the list of known redmine sites."""
            if not url.endswith('/'):
                url += '/'
            if not name:
                irc.error(_('Invalid site name.'), Raise=True)
            if name in self.conf.sites():
                irc.error(_('This site name is already registered.'), Raise=True)
            data = utils.web.getUrl(url + 'projects.json')
            if sys.version_info[0] >= 3:
                data = data.decode('utf8')
            data = json.loads(data)
            assert 'total_count' in data
            #try:
            #    data = json.load(utils.web.getUrlFd(url + 'projects.json'))
            #    assert 'total_count' in data
            #except:
            #    irc.error(_('This is not a valid Redmine site.'), Raise=True)
            with self.conf.sites.editable() as sites:
                sites[name] = {'url': url}
            irc.replySuccess()
        add = wrap(add, ['admin', 'somethingWithoutSpaces', 'url'])

        @internationalizeDocstring
        def remove(self, irc, msg, args, name):
            """<name>

            Remove a site form the list of known redmine sites."""
            if name not in self.conf.sites():
                irc.error(_('This site name does not exist.'), Raise=True)
            with self.conf.sites.editable() as sites:
                del sites[name]
            irc.replySuccess()
        remove = wrap(remove, ['admin', 'somethingWithoutSpaces'])

        @internationalizeDocstring
        def list(self, irc, msg, args):
            """takes no arguments

            Return the list of known redmine sites."""
            sites = self.conf.sites().keys()
            if sites:
                irc.reply(format('%L', list(sites)))
            else:
                irc.reply(_('No registered Redmine site.'))
        list = wrap(list, [])

    @internationalizeDocstring
    @handle_site_arg([])
    def projects(self, irc, msg, args, site):
        """

        Return the list of projects of the Redmine <site>."""
        repl = Template(self.registryValue('format.projects')).safe_substitute
        projects = map(repl, fetch(site, 'projects')['projects'])
        irc.reply(format('%L', projects))

    @internationalizeDocstring
    @handle_site_arg([getopts({'project': 'something',
                               'author': 'something',
                               'assignee': 'something',
                              })])
    def issues(self, irc, msg, args, site, optlist):
        """[--project <project>] [--author <username>] \
        [--assignee <username>]

        Return a list of issues on the Redmine <site>, filtered with
        given parameters."""
        fetch_args = {}
        for (key, value) in optlist:
            if key == 'project':
                fetch_args['project_id'] = get_project_or_error(irc, site, value)['id']
            elif key == 'author':
                fetch_args['author_id'] = get_user_or_error(irc, site, value)['user']['id']
            elif key == 'assignee':
                fetch_args['assigned_to_id'] = get_user_or_error(irc, site, value)['user']['id']
            else:
                raise AssertionError((key, value))
        issues = fetch(site, 'issues', sort='updated_on:desc', **fetch_args)
        issues = issues['issues']
        new_issues = []
        for issue in issues:
            new_issues.append(flatten_subdicts(issue))
        repl = Template(self.registryValue('format.issues')).safe_substitute
        issues = map(repl, new_issues)
        irc.reply(format('%L', issues))

    @internationalizeDocstring
    @handle_site_arg(['positiveInt'])
    def issue(self, irc, msg, args, site, issueid):
        """<issue id>

        Return informations on an issue."""
        try:
            issue = fetch(site, 'issues/%i' % issueid)['issue']
            issue = flatten_subdicts(issue)
            irc.reply(Template(self.registryValue('format.issue')) \
                    .safe_substitute(issue))
        except ResourceNotFound:
            irc.error(_('Issue not found.'), Raise=True)
        except KeyError as e:
            irc.error(_('Bad format in plugins.Redmine.format.issue: '
                '%r is an unknown key.') % e.args[0])


Class = Redmine


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import time

import supybot.conf as conf
from supybot.test import *

def init(f):
    def newf(self):
        self.assertNotError('site add lqdn https://projets.lqdn.fr/')
        try:
            f(self)
        finally:
            self.assertNotError('site remove lqdn')
    return newf

class RedmineTestCase(ChannelPluginTestCase):
    plugins = ('Redmine', 'Config', 'Utilities')

    def testSite(self):
        self.assertRegexp('site list', 'No registered')
        self.assertNotError('site add lqdn https://projets.lqdn.fr/')
        self.assertResponse('site list', 'lqdn')
        self.assertNotError('site add lqdn2 https://projets.lqdn.fr/')
        self.assertRegexp('site list', 'lqdn2? and lqdn2?')
        self.assertNotError('site remove lqdn')
        self.assertResponse('site list', 'lqdn2')

    @init
    def testProjects(self):
        self.assertRegexp('projects lqdn', 'Campagnes \(campagne\), ')

    @init
    def testIssues(self):
        self.assertRegexp('issues lqdn --project campagne', '^\x02.*\x02 \(last.*\)')
        self.assertRegexp('issues lqdn --author 19', '^\x02.*\x02 \(last.*\)')
        self.assertRegexp('issues lqdn --assignee 19', '^\x02.*\x02 \(last.*\)')

    @init
    def testIssue(self):
        self.assertNotError('issue lqdn 130')
        self.assertResponse('issue lqdn 999999', 'Error: Issue not found.')

    @init
    def testAnnounce(self):
        pl = self.irc.getCallback('Redmine')

        self.assertNotError('ping')
        self.assertNotError('config plugins.Redmine.announce.sites lqdn')
        with conf.supybot.plugins.Redmine.sites.editable() as sites:
            sites['lqdn']['interval'] = 1

        # Make sure it does not update everytime a message is received
        self.assertNotError('ping')
        self.assertIs(self.irc.takeMsg(), None)
        last_fetch = pl._last_fetch.copy()
        self.assertNotError('ping')
        self.assertEqual(last_fetch, pl._last_fetch)
        self.assertIs(self.irc.takeMsg(), None)

        # Make sure it updates after the interval is finished, but there is
        # nothing new
        time.sleep(1.1)
        self.assertNotError('ping')
        self.assertNotEqual(last_fetch, pl._last_fetch)
        self.assertIs(self.irc.takeMsg(), None)

        # Let's cheat a little and "olderize" the latest issue.
        pl._last_fetch['lqdn'][1]['issues'][0]['updated_on'] = \
                '2012/12/09 20:37:27 +0100'
        time.sleep(1.1)
        self.assertNotError('ping')
        self.assertNotEqual(last_fetch, pl._last_fetch)
        m = self.irc.takeMsg()
        self.assertIsNot(m, None)


if not network:
    del RedmineTestCase

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Scheme')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Scheme', True)


Scheme = conf.registerPlugin('Scheme')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Scheme, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import ast
import copy
import operator
import fractions
import functools
import collections

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Scheme')

NUMBER_TYPES = (
        ('integer', int),
        ('rational', fractions.Fraction),
        ('real', float),
        ('complex', complex),
        ('number', str),
        )

class SchemeException(Exception):
    pass

def no_side_effect(f):
    def newf(tree, env):
        return f(tree, env.copy())
    return newf

def eval_argument(arg, env):
    if isinstance(arg, list):
        return eval_scheme(arg, env)
    elif isinstance(arg, str):
        if arg in env:
            return eval_argument(env[arg], {})
        else:
            for name, parser in NUMBER_TYPES:
                try:
                    return parser(arg)
                except ValueError:
                    pass
            # You shall not pass
            raise SchemeException(_('Unbound variable: %s') % arg)
    else:
        return arg

def py2scheme(tree):
    if isinstance(tree, list):
        return '(%s)' % (' '.join(map(py2scheme, tree)))
    else:
        return str(tree)

def schemify_math(f):
    # Makes a two-arguments function an *args function, with correct
    # type parsing.
    def rec(args):
        if args[2:]:
            return f(args[0], rec(args[1:]))
        else:
            return f(args[0], args[1])
    def newf(tree, env):
        return rec(map(functools.partial(eval_argument, env=env), tree[1:]))
    newf.__name__ = 'schemified_%s' % f.__name__
    return newf

ARGUMENTS_ERROR = _('%s takes %s %i arguments not %i (in (%s))')
@no_side_effect
def scm_lambda(tree, env):
    try:
        self, args, expr = tree
    except ValueError:
        raise SchemeException(ARGUMENTS_ERROR %
            ('lambda', _('exactly'), 2, len(tree)-1, py2scheme(tree)))
    if not isinstance(args, list):
        args = ['.', args]
    try:
        if args.index('.') != len(args)-2:
            raise SchemeException(_('Invalid arguments list: %s') %
                py2scheme(args))
        rest = args[-1]
        args = args[0:-2]
    except ValueError: # No rest
        rest = None
    @no_side_effect
    def f(tree2, env2):
        self2, args2 = tree2[0], tree2[1:]
        arguments_error = ARGUMENTS_ERROR % \
                    (self2, '%s', len(args), len(args2), tree2)
        env3 = env2.copy()
        if len(args2) < len(args):
            raise SchemeException(arguments_error %
                _('at least') if rest else _('exactly'))
        elif not rest and len(args2) > len(args):
            raise SchemeException(arguments_error % _('exactly'))
        else:
            env3.update(dict(zip(args, args2)))
            if rest:
                env3.update({rest: args2[len(args):]})
        return eval_scheme(expr, env3)
    f.__name__ = 'scheme_%s' % py2scheme(tree)
    return f

def scm_begin(tree, env):
    for arg in tree[1:-1]:
        eval_scheme(arg)
    return eval_scheme(tree[-1])

def scm_set(tree, env):
    try:
        self, name, value = tree
    except ValueError:
        raise SchemeException(ARGUMENTS_ERROR %
            ('set!', _('exactly'), 2, len(tree)-1, py2scheme(tree)))
    env[name] = value

DEFAULT_ENV = [
    ('lambda', scm_lambda),
    ('begin', scm_begin),
    ('set!', scm_set),
    ]
# Add some math operators
DEFAULT_ENV += map(lambda x:(x[0], schemify_math(x[1])), (
    ('+', operator.add),
    ('-', operator.sub),
    ('*', operator.mul),
    ('/', operator.truediv),
    ))

DEFAULT_ENV = dict(DEFAULT_ENV)


def parse_scheme(code, start=0, end=None, unpack=False):
    if end is None:
        end = len(code)-1
    while code[start] == ' ':
        start += 1
    while code[end] == ' ':
        end -= 1
    if code[start] == '(' and code[end] == ')':
        return parse_scheme(code, start+1, end-1, unpack=False)
    level = 0
    in_string = False
    escaped = False
    tokens = []
    token_start = start
    for i in xrange(start, end+1):
        if code[i] == '"' and not escaped:
            in_string = not in_string
        elif in_string:
            pass
        elif code[i] == '\'':
            escaped = not escaped
        elif code[i] == '(':
            level += 1
        elif code[i] == ')':
            level -=1
            if level == -1:
                raise SchemeException(_('At index %i, unexpected `)\' near %s')
                        % (end, code[max(0, end-10):end+10]))
            elif level == 0:
                tokens.append(parse_scheme(code, token_start, i))
                token_start = i+1
        elif level == 0 and code[i] == ' ' and token_start != i:
            tokens.append(parse_scheme(code, token_start, i))
            token_start = i+1
        else:
            continue # Nothing to do
    if level != 0:
        raise SchemeException(_('Unclosed parenthesis in: %s') %
                code[start:end+1])
    if start == token_start:
        return code[start:end+1]
    elif start < end:
        tokens.append(parse_scheme(code, token_start, end))
    tokens = filter(bool, tokens)
    if unpack:
        assert len(tokens) == 1, tokens
        tokens = tokens[0]
    return tokens

def eval_scheme(tree, env=DEFAULT_ENV):
    if isinstance(tree, str):
        if tree in env:
            return env[tree]
        else:
            print(repr(env))
            raise SchemeException(_('Undefined keyword %s.') % tree)
    first = eval_scheme(tree[0])
    if callable(first):
        return first(tree, env)
    else:
        return tree

def eval_scheme_result(tree):
    if isinstance(tree, list):
        return '(%s)' % ' '.join(map(eval_scheme_result, tree))
    else:
        return str(eval_argument(tree, []))

@internationalizeDocstring
class Scheme(callbacks.Plugin):
    """Add the help for "@plugin help Scheme" here
    This should describe *how* to use this plugin."""
    threaded = True

    @internationalizeDocstring
    def scheme(self, irc, msg, args, code):
        """<code>

        Evaluates Scheme."""
        try:
            tree = parse_scheme(code)
        except SchemeException as e:
            irc.error('Syntax error: ' + e.args[0], Raise=True)
        try:
            result = eval_scheme(tree)
        except SchemeException as e:
            irc.error('Runtime error: ' + e.args[0], Raise=True)
        irc.reply(eval_scheme_result(result))
    scheme = wrap(scheme, ['text'])

Class = Scheme


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

from . import plugin

class SchemeTestCase(PluginTestCase):
    plugins = ('Scheme',)

    def testParse(self):
        self.assertEqual(plugin.parse_scheme('(+ 11 12)'),
                ['+', '11', '12'])
        self.assertEqual(plugin.parse_scheme('(+ 5 4)'),
                ['+', '5', '4'])
        self.assertEqual(plugin.parse_scheme('(+ 5 (* 4 6))'),
            ['+', '5', ['*', '4', '6']])
        self.assertEqual(plugin.parse_scheme('((lambda x x) 1 2 3)')[1:],
                ['1', '2', '3'])
        self.assertEqual(plugin.parse_scheme('((lambda (x y) (+ x y)) 11 12)'),
                [['lambda', ['x', 'y'], ['+', 'x', 'y']], '11', '12'])
    def testEval(self):
        self.assertResponse('scheme (+ 11 12)', '23')
        self.assertResponse('scheme (+ 5 4 2)', '11')
        self.assertResponse('scheme (+ 5 (* 5 2))', '15')

    def testLambda(self):
        self.assertResponse('scheme ((lambda x x) 1 2 3)', '(1 2 3)')
        self.assertResponse('scheme ((lambda (x y) (+ x y)) 11 12)', '23')

    def testSet(self):
        self.assertResponse('scheme (begin (set! x 42) x)', '42')

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2010, Pablo Joubert
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Seeks', True)


Seeks = conf.registerPlugin('Seeks')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Seeks, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))

conf.registerChannelValue(Seeks, 'url',
        registry.String('http://www.seeks.fr/search?expansion=1&'
        'action=expand&output=json&q=', """The Seeks server
        that this plugin will use."""))
conf.registerChannelValue(Seeks, 'separator',
        registry.String('/', """The character(s) to use between search
        results."""))
conf.registerChannelValue(Seeks, 'format',
        registry.String('%(url)s - %(seeks_score)s', """The format used to
        display each result."""))
conf.registerChannelValue(Seeks, 'number',
        registry.Integer(5, """The number of results to display."""))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2010, Pablo Joubert
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import urllib
import json

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

class Seeks(callbacks.Plugin):
    """Simply calls a seeks node, requesting json"""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(Seeks, self)
        self.__parent.__init__(irc)
        # should be changed for your node

    def search(self, irc, msg, args, query):
        """<query>

        Searches the <query> in a seeks node."""
        query_str = self.registryValue('url', msg.args[0])
        query = urllib.quote(query).replace('%20', '+')
        raw_page = urllib.urlopen(query_str + query)
        page = raw_page.read()
        try:
            content = json.loads(page)
        except:
            raise
            irc.error("Server's JSON is corrupted")
            return
        snippets = content["snippets"]
        if len(snippets) == 0:
            irc.reply('No results')
            return
        separator = self.registryValue('separator', msg.args[0])
        format_ = self.registryValue('format', msg.args[0])
        number = self.registryValue('number', msg.args[0])
        answer = " / ".join(format_ % x for x in snippets[:number-1])
        irc.reply(answer)

    search = wrap(search, ['text'])

Class = Seeks

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2010, Pablo Joubert
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class SeeksTestCase(PluginTestCase):
    plugins = ('Seeks',)

    if network:
        def testSearch(self):
            self.assertRegexp('seeks search supybot',
                    'http://sourceforge.net/projects/supybot/')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('StdoutCapture')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('StdoutCapture', True)


StdoutCapture = conf.registerPlugin('StdoutCapture')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(StdoutCapture, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))
conf.registerChannelValue(StdoutCapture, 'pastebin',
    registry.String('http://paste.progval.net/', _("""Default pastebin.
    The pastebin has to support the LodgeIt API.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import sys
import json
import logging
import weakref

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('StdoutCapture')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

class StdoutBuffer:
    _buffer = utils.structures.RingBuffer(100)
    def __init__(self, stdout):
        self._real = stdout
    def write(self, data):
        self._real.write(data)
        if data == '\n':
            self._buffer[-1] += '\n'
        else:
            self._buffer.append(data)
    def flush(self):
        pass

class StdoutCapture(callbacks.Plugin):
    """Add the help for "@plugin help StdoutCapture" here
    This should describe *how* to use this plugin."""
    def __init__(self, irc):
        super(StdoutCapture, self).__init__(irc)
        self.StdoutBuffer = StdoutBuffer
        sys.stdout = self.StdoutBuffer(sys.stdout)
        sys.stderr = self.StdoutBuffer(sys.stderr)
        # I'm being a bit evil here.
        for logger in logging._handlerList:
            if isinstance(logger, weakref.ref):
                logger = logger()
            if not hasattr(logger, 'stream'):
                continue
            if logger.stream is sys.stdout._real:
                logger.stream = sys.stderr
            elif logger.stream is sys.stderr._real:
                logger.stream = sys.stderr
    def die(self):
        super(self.__class__, self).die()
        assert isinstance(sys.stdout, self.StdoutBuffer)
        assert isinstance(sys.stdout, self.StdoutBuffer)
        for logger in logging._handlerList:
            logger = logger()
            if not hasattr(logger, 'stream'):
                continue
            if logger.stream in (sys.stdout, sys.stderr):
                logger.stream = logger.stream._real
        sys.stdout = sys.stdout._real
        sys.stderr = sys.stderr._real

    def history(self, irc, msg, args, number):
        """<number>

        Return the last lines displayed in the console."""
        irc.replies(StdoutBuffer._buffer[-number:])
    history = wrap(history, ['positiveInt', 'owner'])

    def pastebin(self, irc, msg, args, number, url=None):
        """<number> [<pastebin url>]

        Paste the last lines displayed in the console on a pastebin and
        returns the URL.
        The pastebin has to support the LodgeIt API."""
        base = url or self.registryValue('pastebin', msg.args[0])
        if base.endswith('/'):
            base = base[0:-1]
        fd = utils.web.getUrlFd(base+'/json/?method=pastes.newPaste',
                data=json.dumps({
                    'language': 'text',
                    'code': ''.join(StdoutBuffer._buffer[-number:]),
                    }),
                headers={'Content-Type': 'application/json'})
        irc.reply('%s/show/%s' % (base, json.load(fd)['data']))

    pastebin = wrap(pastebin, ['owner', 'positiveInt', optional('text')])


Class = StdoutCapture


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class StdoutCaptureTestCase(PluginTestCase):
    plugins = ('StdoutCapture',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('Sudo')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Sudo', True)


Sudo = conf.registerPlugin('Sudo')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Sudo, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import re
import os
import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.plugins as plugins
import supybot.registry as registry
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('Sudo')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x
try:
    import sqlite3
except ImportError:
    from pysqlite2 import dbapi2 as sqlite3 # for python2.4

class DuplicatedName(Exception):
    pass
class NonExistantName(Exception):
    pass

class SudoRule:
    def __init__(self, priority, mode, hostmask, regexp):
        self.priority = int(priority)
        self.mode = mode
        self.hostmask = hostmask
        self.regexp = regexp

    def __repr__(self):
        return '\n'.join([str(self.priority), self.mode, self.hostmask,
                          self.regexp])

class SudoDB:
    def __init__(self):
        self.rules = {}

    def add(self, name, rule):
        """Add a rule with the given ID."""
        if name in self.rules:
            raise DuplicatedName()
        self.rules.update({name: rule})

    def remove(self, name):
        """Remove the rule associated with the name, and returns it."""
        if name not in self.rules:
            raise NonExistantName()
        return self.rules.pop(name)

    def getRuleMatching(self, command):
        currentName = None
        currentRule = None
        for name, rule in self.rules.items():
            if not re.match(rule.regexp, command):
                continue
            if currentRule is None or currentRule.priority < rule.priority:
                currentName = name
                currentRule = rule
        if currentRule is None or currentRule.mode == 'deny':
            return None, None
        return currentName, currentRule

    def save(self, file_):
        file_.write(repr(self))

    def load(self, file_):
        currentName = None
        currentArgs = []
        for line in file_:
            if line != '\n' and currentName is None:
                currentName = line[0:-1]
            elif currentName is not None and len(currentArgs) != 4:
                currentArgs.append(line[0:-1])
            elif currentName is not None:
                self.rules.update({currentName: SudoRule(*currentArgs)})
                currentName = None
                currentArgs = []
        if currentName is not None:
            assert currentArgs != []
            self.rules.update({currentName: SudoRule(*currentArgs)})


    def __repr__(self):
        return '\n\n'.join(['%s\n%s' % (x,repr(y))
                            for x,y in self.rules.items()]) + '\n'





@internationalizeDocstring
class Sudo(callbacks.Plugin):
    """Plugin that allows to run commands as someone else"""
    def __init__(self, irc):
        callbacks.Plugin.__init__(self, irc)
        self.db = SudoDB()
        self._path = os.path.join(conf.supybot.directories.data(), 'sudo.db')
        if not world.testing and os.path.isfile(self._path):
            self.db.load(open(self._path, 'r'))

    @internationalizeDocstring
    def add(self, irc, msg, args, priority, name, mode, hostmask, regexp):
        """[<priority>] <name> {allow,deny} [<hostmask>] <regexp>

        Sets a new Sudo rule, called <name> with the given <priority>
        (greatest numbers have precedence),
        allowing or denying to run commands matching the pattern <regexp>,
        from users to run commands as wearing the <hostmask>.
        The <priority> must be a relative integer.
        If <priority> is not given, it defaults to 0.
        The <hostmask> defaults to your hostmask.
        The <hostmask> is only needed if you set an 'allow' rule.
        """
        try:
            if mode == 'deny' and hostmask is not None:
                irc.error(_('You don\'t have to give a hostmask when setting '
                            'a "deny" rule.'))
                return
            if hostmask is None:
                hostmask = msg.prefix
            if priority is None:
                priority = 0
            self.db.add(name, SudoRule(priority, mode, hostmask, regexp))
        except DuplicatedName:
            irc.error(_('This name already exists'))
            return
        irc.replySuccess()
    add = wrap(add, ['owner', optional('int'), 'something',
                     ('literal', ('allow', 'deny')), optional('hostmask'),
                     'text'])

    @internationalizeDocstring
    def remove(self, irc, msg, args, name):
        """<id>

        Remove a Sudo rule."""
        try:
            self.db.remove(name)
        except NonExistantId:
            irc.error(_('This name does not exist.'))
            return
        irc.replySuccess()
    remove = wrap(remove, ['owner', 'something'])

    @internationalizeDocstring
    def sudo(self, irc, msg, args, command):
        """<command> [<arg1> [<arg2> ...]]

        Runs the command following the Sudo rules."""
        name, rule = self.db.getRuleMatching(command)
        bannedChars = conf.supybot.commands.nested.brackets()
        if name is None:
            log.warning('Sudo for %r not granted to "%s"' %
                    (command, msg.prefix))
            irc.error(_('Sudo not granted.'))
        else:
            assert rule is not None
            log.info('Sudo granted to "%s" with rule %s' % (msg.prefix, name))
            msg.prefix = rule.hostmask
            tokens = callbacks.tokenize(command)
            msg.nick = msg.prefix.split('!')[0]
            self.Proxy(irc.irc, msg, tokens)
    sudo = wrap(sudo, ['text'])

    @internationalizeDocstring
    def fakehostmask(self, irc, msg, args, hostmask, command):
        """<hostmask> <command>

        Runs <command> as if you were wearing the <hostmask>. Of course, usage
        of the command is restricted to the owner."""
        log.info('fakehostmask used to run "%s" as %s' % (command, hostmask))
        msg.prefix = hostmask
        tokens = callbacks.tokenize(command)
        self.Proxy(irc.irc, msg, tokens)
    fakehostmask = wrap(fakehostmask, ['owner', 'hostmask', 'text'])

    def die(self):
        if not world.testing:
            try:
                os.unlink(self._path)
            except OSError:
                pass
            self.db.save(open(self._path, 'a'))
        callbacks.Plugin.die(self)


Class = Sudo


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.ircutils as ircutils
from supybot.test import *
from . import plugin
assert hasattr(plugin, 'SudoDB')

from cStringIO import StringIO

# Disable Admin protection against giving the 'owner' capability.
strEqual = ircutils.strEqual
def fakeStrEqual(first, second):
    if first == 'owner' and second == 'owner':
        return False
ircutils.strEqual = fakeStrEqual

class SudoTestCase(PluginTestCase):
    plugins = ('Sudo', 'User', 'Admin', 'Alias', 'Utilities')

    def testAllow(self):
        self.assertNotError('register Prog Val')
        self.assertResponse('whoami', 'Prog')
        self.assertError('sudo whoami')
        self.assertNotError('capability add Prog owner')
        self.assertResponse('capabilities', '[owner]')
        self.assertError('sudo whoami')
        self.assertNotError('Sudo add spam allow foo!bar@baz whoami.*')
        self.assertResponse('whoami', 'Prog')
        self.assertResponse('sudo whoami', 'I don\'t recognize you.')
        self.assertResponse('capabilities', '[owner]')
        self.assertResponse('sudo capabilities', 'Error: Sudo not granted.')

    def testForbid(self):
        self.assertNotError('register Prog Val')
        self.assertResponse('whoami', 'Prog')
        self.assertError('sudo whoami')
        self.assertNotError('capability add Prog owner')
        self.assertResponse('capabilities', '[owner]')
        self.assertError('sudo whoami')
        self.assertNotError('Sudo add -1 spam allow foo!bar@baz .*i.*')
        self.assertResponse('sudo whoami', 'I don\'t recognize you.')
        self.assertNotError('Sudo add egg deny .*mi')
        self.assertResponse('whoami', 'Prog')
        self.assertError('sudo whoami')
        self.assertResponse('capabilities', '[owner]')
        self.assertRegexp('sudo capabilities', 'Error: '
                          'You must be registered to use this command.*')

    def testNesting(self):
        self.assertNotError('register Prog Val')
        self.assertResponse('whoami', 'Prog')
        self.assertNotError('sudo add test allow test test')
        self.assertNotError('alias add test "echo [echo $nick]"')
        self.assertResponse('echo $nick', self.prefix.split('!')[0])
        self.assertResponse('sudo test', self.prefix.split('!')[0])
        self.prefix = '[foo]!' + self.prefix.split('!')[1]
        self.assertResponse('echo $nick', self.prefix.split('!')[0])

        # This is the main command to test. If there are nesting issues, it
        # will reply `Error: "foo" is not a valid command.` which is
        # ***very*** dangerous.
        self.assertNotRegexp('sudo test', 'valid command')

    def testSave(self):
        one = 'spam\n-1\nallow\nfoo!bar@baz\n.*'
        two = 'egg\n0\ndeny\n\n.*forbid.*'
        db = plugin.SudoDB()
        db.add('spam', plugin.SudoRule(-1, 'allow', 'foo!bar@baz', '.*'))
        assert repr(db) == one + '\n', repr(repr(db))
        db.add('egg', plugin.SudoRule(0, 'deny', '', '.*forbid.*'))
        assert repr(db) == '%s\n\n%s\n' % (one, two) or \
               repr(db) == '%s\n\n%s\n' % (two, one), repr(repr(db))

    def testLoad(self):
        one = 'spam\n-1\nallow\nfoo!bar@baz\n.*'
        two = 'egg\n0\ndeny\n\n.*forbid.*'
        file_ = StringIO()
        file_.write('%s\n\n%s\n' % (one, two))
        file_.seek(0)
        db = plugin.SudoDB()
        db.load(file_)
        assert repr(db) == '%s\n\n%s\n' % (one, two) or \
               repr(db) == '%s\n\n%s\n' % (two, one), repr(repr(db))

    def testFakehostmask(self):
        self.assertNotError('register Prog Val')
        self.assertNotError('capability add Prog owner')
        self.assertResponse('whoami', 'Prog')
        self.assertResponse('fakehostmask %s whoami' % self.prefix, 'Prog')
        self.assertResponse('fakehostmask prog!val@home whoami',
                'I don\'t recognize you.')




# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry

try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('SupyML')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('SupyML', True)


SupyML = conf.registerPlugin('SupyML')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(SupyML, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))

conf.registerGlobalValue(SupyML, 'maxnodes', registry.Integer(30, """Determines
    the maximum number of nodes processed by the 'SupyML eval' command."""))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import re
import sys
import copy
import time
import supybot.conf as conf
from xml.dom import minidom
import supybot.world as world
import supybot.utils as utils
from supybot.commands import *
from supybot.irclib import IrcMsgQueue
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('SupyML')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

class ParseError(Exception):
    pass

class LoopError(Exception):
    pass

class LoopTypeIsMissing(Exception):
    pass

class MaximumNodesNumberExceeded(Exception):
    pass

parseMessage = re.compile('\w+: (?P<content>.*)')
class FakeIrc():
    def __init__(self, irc):
        self._irc = irc
        self._message = ''
        self._data = ''
        self._rawData = None
    def error(self, message):
        message = message
        self._data = message
    def reply(self, message):
        self._data = message
    def queueMsg(self, message):
        self._rawData = message
        if message.command in ('PRIVMSG', 'NOTICE'):
            parsed = parseMessage.match(message.args[1])
            if parsed is not None:
                message = parsed.group('content')
            else:
                message = message.args[1]
        self._data = message
    def __getattr__(self, name):
        if name == '_data' or name == '_rawData':
            return self.__dict__[name]
        return getattr(self.__dict__['_irc'], name)

class SupyMLParser:
    def __init__(self, plugin, irc, msg, code, maxNodes):
        self._plugin = plugin
        self._irc = irc
        self._msg = msg
        self._code = code
        self.warnings = []
        self._maxNodes = maxNodes
        self.nodesCount = 0
        self.data = self._parse(code)

    def _startNode(self):
        self.nodesCount += 1
        if self.nodesCount >= self._maxNodes:
            raise MaximumNodesNumberExceeded()

    def _run(self, code, nested):
        """Runs the command using Supybot engine"""
        tokens = callbacks.tokenize(str(code))
        fakeIrc = FakeIrc(self._irc)
        callbacks.NestedCommandsIrcProxy(fakeIrc, self._msg, tokens,
                nested=(1 if nested else 0))
        self.rawData = fakeIrc._rawData
        # TODO : don't wait if the plugin is not threaded
        time.sleep(0.1)
        return fakeIrc._data

    def _parse(self, code, variables={}):
        """Returns a dom object from the code."""
        self._startNode()
        dom = minidom.parseString(code)
        output = self._processDocument(dom, variables)
        return output

    def _processDocument(self, dom, variables={}):
        """Handles the root node and call child nodes"""
        for childNode in dom.childNodes:
            if isinstance(childNode, minidom.Element):
                output = self._processNode(childNode, variables, nested=False)
        return output

    def _processNode(self, node, variables, nested=True):
        """Returns the value of an internapreted node."""

        if isinstance(node, minidom.Text):
            return node.data
        output = node.nodeName + ' '
        for childNode in node.childNodes:
            self._startNode()
            if not repr(node) == repr(childNode.parentNode):
                continue
            if childNode.nodeName == 'loop':
                output += self._processLoop(childNode, variables)
            elif childNode.nodeName == 'if':
                output += self._processId(childNode, variables)
            elif childNode.nodeName == 'var':
                output += self._processVar(childNode, variables)
            elif childNode.nodeName == 'set':
                output += self._processSet(childNode, variables)
            else:
                output += self._processNode(childNode, variables) or ''
        value = self._run(output, nested)
        return value

    def _processSet(self, node, variables):
        """Handles the <set> tag"""
        variableName = str(node.attributes['name'].value)
        value = ''
        for childNode in node.childNodes:
            value += self._processNode(childNode, variables)
        variables.update({variableName: value})
        return ''

    def _processVar(self, node, variables):
        """Handles the <var /> tag"""
        variableName = node.attributes['name'].value
        self._checkVariableName(variableName)
        try:
            return variables[variableName]
        except KeyError:
            self.warnings.append('Access to non-existing variable: %s' %
                                 variableName)
            return ''

    def _processLoop(self, node, variables):
        """Handles the <loop> tag"""
        loopType = None
        loopCond = 'false'
        loopContent = ''
        output = ''
        for childNode in node.childNodes:
            if loopType is None and childNode.nodeName not in ('while'):
                raise LoopTypeIsMissing(node.toxml())
            elif loopType is None:
                loopType = childNode.nodeName
                loopCond = childNode.toxml()
                loopCond = loopCond[len(loopType+'<>'):-len(loopType+'</>')]
            else:
                loopContent += childNode.toxml()
        if loopType == 'while':
            try:
                while utils.str.toBool(self._parse(loopCond, variables,
                                                  ).split(': ')[-1]):
                    loopContent = '<echo>%s</echo>' % loopContent
                    output += self._parse(loopContent) or ''
            except AttributeError: # toBool() failed
                pass
            except ValueError: # toBool() failed
                pass
        return output


    def _checkVariableName(self, variableName):
        if len(variableName) == 0:
            self.warnings.append('Empty variable name')
        if re.match('\W+', variableName):
            self.warnings.append('Variable name shouldn\'t contain '
                                 'special chars (%s)' % variableName)

class SupyML(callbacks.Plugin):
    """SupyML is a plugin that read SupyML scripts.
    This scripts (Supybot Markup Language) are script written in a XML-based
    language."""
    #threaded = True
    def eval(self, irc, msg, args, optlist, code):
        """[--warnings] <SupyML script>

        Executes the <SupyML script>"""
        parser = SupyMLParser(self, irc, msg, code,
                              self.registryValue('maxnodes')+2)
        for item in optlist:
            if ('warnings', True) == item and len(parser.warnings) != 0:
                irc.error(' & '.join(parser.warnings))
        if parser.rawData is not None:
            irc.queueMsg(parser.rawData)
        else:
            irc.reply(parser.data)

    eval=wrap(eval, [getopts({'warnings':''}), 'text'])

SupyML = internationalizeDocstring(SupyML)

Class = SupyML


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import time
from supybot.test import *

class SupyMLTestCase(ChannelPluginTestCase):
    plugins = ('SupyML', 'Utilities', 'Conditional', 'Math')
    #################################
    # Utilities
    def _getIfAnswerIsEqual(self, msg):
        time.sleep(0.1)
        m = self.irc.takeMsg()
        while m is not None:
            if repr(m) == repr(msg):
                return True
            m = self.irc.takeMsg()
        return False


    def testBasic(self):
        self.assertError('SupyML eval')
        self.assertResponse('SupyML eval <echo>foo</echo>', 'foo')
        msg = ircmsgs.privmsg(self.channel, '@SupyML eval ' \
            '<tell><echo>ProgVal</echo> <echo>foo</echo></tell>',
                                  prefix=self.prefix)
        self.irc.feedMsg(msg)
        answer = ircmsgs.IrcMsg(prefix="", command="PRIVMSG",
                        args=('ProgVal', 'test wants me to tell you: foo'))
        self.failIf(self._getIfAnswerIsEqual(answer) == False)
        self.assertResponse('SupyML eval <nne>4 5</nne>', 'true')
        self.assertResponse('SupyML eval <echo><nne>4 5</nne></echo>', 'true')

    def testNoMoreThanOneAnswer(self):
        self.assertResponse('SupyML eval '
                            '<echo>'
                                '<echo>foo</echo>'
                                '<echo>bar</echo>'
                            '</echo>',
                            'foobar')

    def testVar(self):
        self.assertResponse('SupyML eval '
                            '<echo>'
                                '<set name="foo">bar</set>'
                                '<echo>'
                                    '<var name="foo" />'
                                '</echo>'
                            '</echo>',
                            'bar')

    def testVarLifetime(self):
        self.assertResponse('SupyML eval '
                            '<echo>'
                                '<set name="foo">bar</set>'
                                '<echo>'
                                    '<var name="foo" />'
                                    'baz'
                                '</echo>'
                            '</echo>',
                            'barbaz')
        self.assertResponse('SupyML eval '
                            '<echo>'
                                '<set name="foo">bar</set>'
                                '<echo>'
                                    '<set name="foo">bar</set>'
                                    '<var name="foo" />'
                                '</echo>'
                                '<echo>'
                                    '<var name="foo" />'
                                '</echo>'
                            '</echo>',
                            'barbar')

    def testWhile(self):
        self.assertResponse('SupyML eval '
                            '<echo>'
                                '<set name="foo">4</set>'
                                '<loop>'
                                    '<while>'
                                        '<nne>'
                                            '<var name="foo" /> 5'
                                        '</nne>'
                                    '</while>'
                                    '<set name="foo">5</set>'
                                    '<echo>'
                                        'bar'
                                    '</echo>'
                                '</loop>'
                            '</echo>',
                            'bar')
        self.assertResponse('SupyML eval '
                            '<echo>'
                                '<set name="foo">3</set>'
                                '<loop>'
                                    '<while>'
                                        '<nne>'
                                            '<var name="foo" /> 5'
                                        '</nne>'
                                    '</while>'
                                    '<set name="foo">'
                                        '<calc>'
                                            '<var name="foo" /> + 1'
                                        '</calc>'
                                    '</set>'
                                    '<echo>'
                                        '<var name="foo" />'
                                    '</echo>'
                                '</loop>'
                            '</echo>',
                            '45')

    def testNesting(self):
        self.assertNotError('SupyML eval ' +
                         '<echo>'*30+
                            'foo' +
                         '</echo>'*30
                        )
        self.assertError('SupyML eval ' +
                         '<echo>'*31+
                            'foo' +
                         '</echo>'*31
                        )
        self.assertResponse('SupyML eval <echo>foo <tell>bar baz</tell></echo>',
                'foo This command cannot be nested.')

    def testWarnings(self):
        self.assertResponse('SupyML eval <echo>'
                                '<set name="">'
                                    'bar'
                                '</set>'
                                '<var name="" />'
                            '</echo>', 'bar')
        self.assertResponse('SupyML eval --warnings <echo>'
                                '<set name="">'
                                    'bar'
                                '</set>'
                                '<var name="" />'
                            '</echo>', 'Error: Empty variable name')

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf8 -*-
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('SupySandbox', True)


SupySandbox = conf.registerPlugin('SupySandbox')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(SupySandbox, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = fschfsch
#!/usr/bin/env python
# this file is under the WTFPLv2 [http://sam.zoy.org/wtfpl]
# v1: 2010/05/23
# Author: Tila

# You need a configuration file: ~/.fschfsch.py. Config example:
# ---
# host = 'irc.freenode.net'
# port = 7000
# ssl = True
# nickname = 'botnickname'
# password = 'secret'
# channels = ['##fschfsch', '#channel2', '#channel3']
# texts = {'help': 'I am fschfsch, a robot snake that evals python code',
#         'sandbox': "I am powered by setrlimit and pysandbox [http://github.com/haypo/pysandbox], I don't fear you"}
# ---

'''
fschfsch is a Python-evaluating bot. fschfsch is pronounced "fssshh! fssshh!".
'''

IN_MAXLEN = 300 # bytes
OUT_MAXLEN = 300 # bytes
TIMEOUT = 3  # seconds

EVAL_MAXTIMESECONDS = TIMEOUT
EVAL_MAXMEMORYBYTES = 10 * 1024 * 1024 # 10 MiB


try:
    import sandbox as S
except ImportError:
    print 'You need pysandbox in order to run fschfsch [http://github.com/haypo/pysandbox].'
    raise
try:
    import twisted
except ImportError:
    print 'You need twisted in order to run fschfsch.'
    raise
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet import ssl, reactor
from twisted.words.im.ircsupport import IRCProto
from twisted.words.protocols.irc import IRCClient
# other imports
import re
import sys
import os
import resource as R
import select
import signal
import time
import threading
import random

def createSandboxConfig():
    cfg = S.SandboxConfig(
        'stdout',
        'stderr',
        'regex',
        'unicodedata', # flow wants u'\{ATOM SYMBOL}' :-)
        'future',
        'code',
        'time',
        'datetime',
        'math',
        'itertools',
        'random',
        'encodings',
    )
    cfg.allowModule('sys',
        'version', 'hexversion', 'version_info')
    return cfg

def _evalPython(line, locals):
    locals = dict(locals)
    try:
        if "\n" in line:
            raise SyntaxError()
        code = compile(line, "<irc>", "single")
    except SyntaxError:
        code = compile(line, "<irc>", "exec")
    exec code in locals

def evalPython(line, locals=None):
    sandbox = S.Sandbox(config=createSandboxConfig())

    if locals is not None:
        locals = dict(locals)
    else:
        locals = dict()
    try:
        sandbox.call(_evalPython, line, locals)
    except BaseException, e:
        print 'Error: [%s] %s' % (e.__class__.__name__, str(e))
    except:
        print 'Error: <unknown exception>'
    sys.stdout.flush()

def childProcess(line, w, locals):
    # reseed after a fork to avoid generating the same sequence for each child
    random.seed()

    sys.stdout = sys.stderr = os.fdopen(w, 'w')

    R.setrlimit(R.RLIMIT_CPU, (EVAL_MAXTIMESECONDS, EVAL_MAXTIMESECONDS))
    R.setrlimit(R.RLIMIT_AS, (EVAL_MAXMEMORYBYTES, EVAL_MAXMEMORYBYTES))
    R.setrlimit(R.RLIMIT_NPROC, (0, 0)) # 0 forks

    evalPython(line, locals)

def handleChild(childpid, r):
    txt = ''
    if any(select.select([r], [], [], TIMEOUT)):
        txt = os.read(r, OUT_MAXLEN + 1)
    os.close(r)
    if OUT_MAXLEN < len(txt):
        txt = txt[:OUT_MAXLEN] + '...'

    n = 0
    while n < 6:
        pid, status = os.waitpid(childpid, os.WNOHANG)
        if pid:
            break
        time.sleep(.5)
        n += 1
    if not pid:
        os.kill(childpid, signal.SIGKILL)
        return 'Timeout'
    elif os.WIFEXITED(status):
        txts = txt.rstrip().split('\n')
        if len(txts) > 1:
            txt = txts[0].rstrip() + ' [+ %d line(s)]' % (len(txts) - 1)
        else:
            txt = txts[0].rstrip()
        return 'Output: ' + txt
    elif os.WIFSIGNALED(status):
        return 'Killed'



class EvalJob(threading.Thread):
    def __init__(self, line, irc, channel):
        super(EvalJob, self).__init__()
        self.line = line
        self.irc = irc
        self.channel = channel

    def run(self):
        output = self.handle_line(self.line)
        reactor.callFromThread(self.irc.say, self.channel, output)
        self.irc.executionLock.release()

    def handle_line(self, line):
        if IN_MAXLEN < len(line):
            return '(command is too long: %s bytes, the maximum is %s)' % (len(line), IN_MAXLEN)

        print("Process %s" % repr(line))
        r, w = os.pipe()
        childpid = os.fork()
        if not childpid:
            os.close(r)
            childProcess(line, w, self.irc.factory.morevars)
            os._exit(0)
        else:
            os.close(w)
            result = handleChild(childpid, r)
            print("=> %s" % repr(result))
            return result



class EvalBot(IRCClient):
    versionName = 'fschfsch'
    versionNum = '0.1'

    #~ def __init__(self, *a, **k):
    def connectionMade(self):
        self.nickname = self.factory.nick
        self.password = self.factory.password
        self.talkre = re.compile('^%s[>:,] (.*)$' % self.nickname)

        self.executionLock = threading.Semaphore()
        self.pingSelfId = None

        IRCClient.connectionMade(self)

    def signedOn(self):
        self.pingSelfId = reactor.callLater(180, self.pingSelf)
        for chan in self.factory.channels:
            self.join(chan)

    def pingSelf(self):
        # used to avoid some timeouts where fschfsch does not reconnect
        self.ping(self.nickname)
        self.pingSelfId = reactor.callLater(180, self.pingSelf)

    def privmsg(self, user, channel, message):
        if self.pingSelfId is not None:
            self.pingSelfId.reset(180)
        if user.startswith('haypo') and message.startswith('exit'):
            os._exit(0)
        if not channel:
            return
        if not message.startswith(self.nickname):
            return
        if not self.talkre.match(message):
            return
        if not self.executionLock.acquire(blocking=False):
            return

        pyline = self.talkre.match(message).group(1)
        pyline = pyline.replace(' $$ ', '\n')

        self.handleThread = EvalJob(pyline, self, channel)
        self.handleThread.start()


class MyFactory(ReconnectingClientFactory):
    def __init__(self, **kw):
        for k in kw:
            if k in ('nick', 'password', 'channels', 'morevars'):
                setattr(self, k, kw[k])
    protocol = EvalBot

def check_output(expr, expected, locals=None):
    from cStringIO import StringIO
    original_stdout = sys.stdout
    try:
        output = StringIO()
        sys.stdout = output
        evalPython(expr, locals)
        stdout = output.getvalue()
        assert stdout == expected, "%r != %r" % (stdout, expected)
    finally:
        sys.stdout = original_stdout

def runTests():
    # single
    check_output('1+1', '2\n')
    check_output('1; 2', '1\n2\n')
    check_output(
        # written in a single line
        "prime=lambda n,i=2:"
            "False if n%i==0 else prime(n,i+1) if i*i<n else True; "
        "prime(17)",
        "True\n")

    # exec
    check_output('def f(): print("hello")\nf()', 'hello\n')
    check_output('print 1\nprint 2', '1\n2\n')
    check_output('text', "'abc'\n", {'text': 'abc'})
    return True

def main():
    if len(sys.argv) == 2 and sys.argv[1] == 'tests':
        ok = runTests()
        if ok:
            print("no failure")
        else:
            print("failure!")
        sys.exit(int(not ok))
    elif len(sys.argv) != 1:
        print 'usage: %s -- run the bot' % sys.argv[0]
        print '   or: %s tests -- run self tests' % sys.argv[0]
        print
        print 'Edit ~/.fschfschrc.py first'
        sys.exit(4)

    conf = {}
    execfile(os.path.expanduser('~/.fschfschrc.py'), conf)
    factory = MyFactory(nick=conf['nickname'], password=conf.get('password', None), channels=conf.get('channels', []), morevars=conf.get('texts', {}))
    if conf.get('ssl', 0):
        reactor.connectSSL(conf['host'], conf['port'], factory, ssl.ClientContextFactory())
    else:
        reactor.connectTCP(conf['host'], conf['port'], factory)
    reactor.run()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2010-2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# pysandbox were originally writen by haypo (under the BSD license), 
# and fschfsch by Tila (under the WTFPL license).

###

IN_MAXLEN = 1000 # bytes
OUT_MAXLEN = 1000 # bytes
TIMEOUT = 3  # seconds

EVAL_MAXTIMESECONDS = TIMEOUT
EVAL_MAXMEMORYBYTES = 75 * 1024 * 1024 # 10 MiB

import re
import os
import sys
import time
import random
import select
import signal
import contextlib
import resource as R
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from cStringIO import StringIO

try:
    import sandbox as S
except ImportError:
    print('You need pysandbox in order to run SupySandbox plugin '
          '[http://github.com/haypo/pysandbox].')
    raise
except SyntaxError:
    raise callbacks.Error('the pysandbox is not compatible with your Python '
            'version.')

class SandboxError(Exception):
    pass

def createSandboxConfig():
    cfg = S.SandboxConfig(
        'stdout',
        'stderr',
        'regex',
        'unicodedata', # flow wants u'\{ATOM SYMBOL}' :-)
        'future',
        #'code',
        'time',
        'datetime',
        'math',
        'itertools',
        'random',
        'encodings',
    )
    cfg.max_memory = EVAL_MAXMEMORYBYTES
    cfg.timeout = EVAL_MAXTIMESECONDS
    cfg.allowModule('sys',
        'version', 'hexversion', 'version_info')
    return cfg

evalPythonInSandbox = r"""
try:
    if "\n" in line:
        raise SyntaxError()
    code = compile(line, "<irc>", "single")
except SyntaxError:
    code = compile(line, "<irc>", "exec")
exec code in namespace, namespace
del code
del namespace
"""

def evalPython(line, locals=None):
    try:
        config = createSandboxConfig()
        sandbox = S.Sandbox(config=config)

        if locals is None:
            locals = {}
        sandbox.execute(
            evalPythonInSandbox,
            locals={'namespace': locals, 'line': line})
    except BaseException as  e:
        print('Error: [%s] %s' % (e.__class__.__name__, str(e)))
    except:
        print('Error: <unknown exception>')
    sys.stdout.flush()

@contextlib.contextmanager
def capture_stdout():
    import sys
    import tempfile
    stdout_fd = sys.stdout.fileno()
    with tempfile.TemporaryFile(mode='w+b') as tmp:
        stdout_copy = os.dup(stdout_fd)
        try:
            os.dup2(tmp.fileno(), stdout_fd)
            yield tmp
        finally:
            os.dup2(stdout_copy, stdout_fd)
            os.close(stdout_copy)

def evalLine(line, locals):
    with capture_stdout() as stdout:
        evalPython(line, locals)
        stdout.seek(0)
        txt = stdout.read()

    print("Output: %r" % txt)

    txts = txt.rstrip().split('\n')
    if len(txts) > 1:
        txt = txts[0].rstrip() + ' [+ %d line(s)]' % (len(txts) - 1)
    else:
        txt = txts[0].rstrip()
    return 'Output: ' + txt

def handle_line(line):
    if IN_MAXLEN < len(line):
        return '(command is too long: %s bytes, the maximum is %s)' % (len(line), IN_MAXLEN)

    print("Process %s" % repr(line))
    result = evalLine(line, {})
    print("=> %s" % repr(result))
    return result

class SupySandbox(callbacks.Plugin):
    """Add the help for "@plugin help SupySandbox" here
    This should describe *how* to use this plugin."""

    _parser = re.compile(r'(.*sandbox)? (?P<code>.*)')
    _parser = re.compile(r'(.?sandbox)? (?P<code>.*)')
    def sandbox(self, irc, msg, args, code):
        """<code>
        
        Runs Python code safely thanks to pysandbox"""
        try:
            irc.reply(handle_line(code.replace(' $$ ', '\n')))
        except SandboxError as  e:
            irc.error('; '.join(e.args))
    sandbox = wrap(sandbox, ['text'])
        
    def runtests(self, irc, msg, args):
        irc.reply(runTests())


Class = SupySandbox


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
# -*- coding: utf8 -*-
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class SupySandboxTestCase(PluginTestCase):
    plugins = ('SupySandbox',)

    def testFschfschTestcase(self):
        self.assertResponse('runtests', 'True')

    def testCodeIsSuccessfullyRunned(self):
        self.assertResponse('sandbox 1+1', "2")
        self.assertResponse('sandbox print 1+1', "2")
        self.assertResponse('sandbox print \'toto\'', "toto")

    def testMultine(self):
        self.assertResponse('sandbox print 1; print 2', "'1\\n2'")
        self.assertResponse('sandbox print 1 $$ print 2', "'1\\n2'")
        self.assertResponse('sandbox toto=True $$ while toto: $$   print "foo"'
                            ' $$   toto=False', "foo")

    def testProtections(self):
        self.assertError('sandbox while True: pass')
        self.assertError('sandbox foo="bar"; $$ while True:foo=foo*10')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
try:
        from supybot.i18n import PluginInternationalization
        from supybot.i18n import internationalizeDocstring
        _ = PluginInternationalization('Trigger')
except:
        # This are useless functions that's allow to run the plugin on a bot
        # without the i18n plugin
        _ = lambda x:x
        internationalizeDocstring = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Trigger', True)


Trigger = conf.registerPlugin('Trigger')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Trigger, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))
conf.registerGroup(Trigger, 'triggers')

for trigger in 'join part privmsg notice highlight nick quit kick'.split(' '):
    conf.registerChannelValue(Trigger.triggers, trigger,
        registry.String('', _("""Command triggered by %ss""" % trigger),
            private=True))

conf.registerGlobalValue(Trigger.triggers, 'connect',
    registry.String('', _("""Command triggered on connect. This shouldn't be
    a Supybot command, but an IRC command (as given to ircquote)."""),
    private=True))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('Trigger')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x


@internationalizeDocstring
class Trigger(callbacks.Plugin):
    """Add the help for "@plugin help Trigger" here
    This should describe *how* to use this plugin."""
    def __init__(self, irc):
        super(Trigger, self).__init__(irc)
        self.lastMsgs = {}
        self.lastStates = {}
    def __call__(self, irc, msg):
        try:
            super(Trigger, self).__call__(irc, msg)
            if irc in self.lastMsgs:
                if irc not in self.lastStates:
                    self.lastStates[irc] = irc.state.copy()
                self.lastStates[irc].addMsg(irc, self.lastMsgs[irc])
        finally:
            # We must make sure this always gets updated.
            self.lastMsgs[irc] = msg
    def _run(self, irc, msg, triggerName, channel=None):
        if channel is None:
            channel = msg.args[0]
        command = self.registryValue('triggers.%s' % triggerName, channel)
        if not list(filter(lambda x:x!=' ', command)):
            return
        tokens = callbacks.tokenize(command)
        if not tokens:
            return
        try:
            msg.args = (channel,) + msg.args[1:]
            self.Proxy(irc.irc, msg, tokens)
        except Exception as  e:
            self.log.exception('Error occured while running triggered command:')
    def doJoin(self, irc, msg):
        self._run(irc, msg, 'join')
    def doPart(self, irc, msg):
        self._run(irc, msg, 'part')
    def doKick(self, irc, msg):
        self._run(irc, msg, 'kick')
    def doPrivmsg(self, irc, msg):
        self._run(irc, msg, 'privmsg')
        if irc.nick in msg.args[1]:
            self._run(irc, msg, 'highlight')
    def doNotice(self, irc, msg):
        self._run(irc, msg, 'notice')
    def doQuit(self, irc, msg):
        for (channel, c) in self.lastStates[irc].channels.items():
            if msg.nick in c.users:
                self._run(irc, msg, 'quit', channel)
    def doNick(self, irc, msg):
        for (channel, c) in irc.state.channels.items():
            if msg.args[0] in c.users:
                self._run(irc, msg, 'nick', channel)
    def do376(self, irc, msg):
        command = self.registryValue('triggers.connect')
        if command != '':
            irc.queueMsg(ircmsgs.IrcMsg(command))


Class = Trigger


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import time
from supybot.test import *

class TriggerTestCase(ChannelPluginTestCase):
    plugins = ('Trigger', 'Utilities')
    config = {'supybot.plugins.Trigger.triggers.join': 'echo Hi $nick',
              'supybot.plugins.Trigger.triggers.part': 'echo foo',
              'supybot.plugins.Trigger.triggers.highlight': 'echo foobar',
              'supybot.plugins.Trigger.triggers.privmsg': 'echo bar',
              'supybot.plugins.Trigger.triggers.notice': 'echo baz'}

    def _getIfAnswerIsEqual(self, msg):
        time.sleep(0.1)
        m = self.irc.takeMsg()
        while m is not None:
            if repr(m) == repr(msg):
                return True
            m = self.irc.takeMsg()
        return False

    def testBasics(self):
        self.irc.feedMsg(ircmsgs.part(self.channel, prefix=self.prefix))
        msg = ircmsgs.privmsg(self.channel, 'foo')
        self.failIf(not self._getIfAnswerIsEqual(msg), 'Does not reply to '
                'triggered echo on part')

        self.irc.feedMsg(ircmsgs.privmsg(self.channel,'lol',prefix=self.prefix))
        msg = ircmsgs.privmsg(self.channel, 'bar')
        self.failIf(not self._getIfAnswerIsEqual(msg), 'Does not reply to '
                'triggered echo on privmsg')

        self.irc.feedMsg(ircmsgs.privmsg(self.channel,'lol %s test' % self.nick,
            prefix=self.prefix))
        msg = ircmsgs.privmsg(self.channel, 'bar')
        self.failIf(not self._getIfAnswerIsEqual(msg), 'Does not reply to '
                'triggered echo on privmsg')
        msg = ircmsgs.privmsg(self.channel, 'foobar')
        self.failIf(not self._getIfAnswerIsEqual(msg), 'Does not reply to '
                'triggered echo on highlight')

        self.irc.feedMsg(ircmsgs.notice(self.channel,'lol',prefix=self.prefix))
        msg = ircmsgs.privmsg(self.channel, 'baz')
        self.failIf(not self._getIfAnswerIsEqual(msg), 'Does not reply to '
                'triggered echo on notice')

    def testSubstitude(self):
        self.irc.feedMsg(ircmsgs.join(self.channel, prefix=self.prefix))
        msg = ircmsgs.privmsg(self.channel, 'Hi test')
        self.failIf(not self._getIfAnswerIsEqual(msg), 'Does not welcome me')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2010, quantumlemur
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Trivia')
def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Trivia', True)


Trivia = conf.registerPlugin('Trivia')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Trivia, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))

conf.registerChannelValue(Trivia, 'blankChar',
        registry.String('*', _("""The character used for a blank when
        displaying hints""")))

conf.registerChannelValue(Trivia, 'numHints',
        registry.PositiveInteger(3, _("""The number of hints to be given for
        each question""")))

conf.registerChannelValue(Trivia, 'timeout',
        registry.PositiveInteger(90, _("""The number of seconds to allow for
        each question""")))

conf.registerChannelValue(Trivia, 'hintPercentage',
        registry.Probability(0.25, _("""The fraction of the answer that
        should be revealed with each hint""")))

conf.registerChannelValue(Trivia, 'flexibility',
        registry.PositiveInteger(8, _("""The flexibility of the trivia answer
        checker.  One typo will be allowed for every __ characters.""")))

conf.registerChannelValue(Trivia, 'color',
        registry.PositiveInteger(10, _("""The mIRC color to use for trivia
        questions""")))

conf.registerChannelValue(Trivia, 'inactiveShutoff',
        registry.Integer(6, _("""The number of questions that can go
        unanswered before the trivia stops automatically.""")))

conf.registerGlobalValue(Trivia, 'scoreFile',
        registry.String('scores.txt', _("""The path to the scores file.
        If it doesn't exist, it will be created.""")))

conf.registerGlobalValue(Trivia, 'questionFile',
        registry.String('questions.txt', _("""The path to the questions file.
        If it doesn't exist, it will be created.""")))

conf.registerChannelValue(Trivia, 'defaultRoundLength',
        registry.PositiveInteger(10, _("""The default number of questions to
        be asked in a round of trivia.""")))

conf.registerGlobalValue(Trivia, 'questionFileSeparator',
        registry.String('*', _("""The separator used between the questions
        and answers in your trivia file.""")))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2010, quantumlemur
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import re
import os
import time
import math
import string
import random
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.schedule as schedule
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Trivia')

class Trivia(callbacks.Plugin):
    """Add the help for "@plugin help Trivia" here
    This should describe *how* to use this plugin."""
    threaded = True


    def __init__(self, irc):
        self.__parent = super(Trivia, self)
        self.__parent.__init__(irc)
        self.games = {}
        self.scores = {}
        questionfile = self.registryValue('questionFile')
        if not os.path.exists(questionfile):
            f = open(questionfile, 'w')
            f.write(('If you\'re seeing this question, it means that the '
                     'questions file that you specified wasn\'t found, and '
                     'a new one has been created.  Go get some questions!%s'
                     'No questions found') %
                    self.registryValue('questionFileSeparator'))
            f.close()
        self.scorefile = self.registryValue('scoreFile')
        if not os.path.exists(self.scorefile):
            f = open(self.scorefile, 'w')
            f.close()
        f = open(self.scorefile, 'r')
        line = f.readline()
        while line:
            (name, score) = line.split(' ')
            self.scores[name] = int(score.strip('\r\n'))
            line = f.readline()
        f.close()


    def doPrivmsg(self, irc, msg):
        channel = ircutils.toLower(msg.args[0])
        if not irc.isChannel(channel):
            return
        if callbacks.addressed(irc.nick, msg):
            return
        if channel in self.games:
            self.games[channel].answer(msg)


    class Game:
        def __init__(self, irc, channel, num, plugin):
            self.rng = random.Random()
            self.rng.seed()
            self.registryValue = plugin.registryValue
            self.irc = irc
            self.channel = channel
            self.num = num
            self.numAsked = 0
            self.hints = 0
            self.games = plugin.games
            self.scores = plugin.scores
            self.scorefile = plugin.scorefile
            self.questionfile = self.registryValue('questionFile')
            self.total = num
            self.active = True
            self.questions = []
            self.roundscores = {}
            self.unanswered = 0
            f = open(self.questionfile, 'r')
            line = f.readline()
            while line:
                self.questions.append(line.strip('\n\r'))
                line = f.readline()
            f.close()
            try:
                schedule.removeEvent('next_%s' % self.channel)
            except KeyError:
                pass
            self.newquestion()


        def newquestion(self):
            inactiveShutoff = self.registryValue('inactiveShutoff',
                                                 self.channel)
            if self.num == 0:
                self.active = False
            elif self.unanswered > inactiveShutoff and inactiveShutoff >= 0:
                self.reply(_('Seems like no one\'s playing any more.'))
                self.active = False
            elif len(self.questions) == 0:
                self.reply(_('Oops!  I ran out of questions!'))
                self.active = False
            if not self.active:
                self.stop()
                return
            self.hints = 0
            self.num -= 1
            self.numAsked += 1
            which = self.rng.randint(0, len(self.questions)-1)
            q = self.questions.pop(which)
            sep = self.registryValue('questionFileSeparator')
            self.q = q[:q.find(sep)]
            self.a = q[q.find(sep)+len(sep):].split(sep)
            color = self.registryValue('color', self.channel)
            self.reply(_('\x03%s#%d of %d: %s') % (color, self.numAsked,
                                                self.total, self.q))
            def event():
                self.timedEvent()
            timeout = self.registryValue('timeout', self.channel)
            numHints = self.registryValue('numHints', self.channel)
            eventTime = time.time() + timeout / (numHints + 1)
            if self.active:
                schedule.addEvent(event, eventTime, 'next_%s' % self.channel)


        def stop(self):
            self.reply(_('Trivia stopping.'))
            self.active = False
            try:
                schedule.removeEvent('next_%s' % self.channel)
            except KeyError:
                pass
            scores = self.roundscores.iteritems()
            sorted = []
            for i in range(0, len(self.roundscores)):
                item = scores.next()
                sorted.append(item)
            def cmp(a, b):
                return b[1] - a[1]
            sorted.sort(cmp)
            max = 3
            if len(sorted) < max:
                max = len(sorted)
                #self.reply('max: %d.  len: %d' % (max, len(sorted)))
            s = _('Top finishers: ')
            if max > 0:
                recipients = []
                maxp = sorted[0][1]
                for i in range(0, max):
                    item = sorted[i]
                    s = _('%s %s %s.') % (s, item[0], item[1])
                self.reply(s)
            del self.games[self.channel]


        def timedEvent(self):
            if self.hints >= self.registryValue('numHints', self.channel):
                self.reply(_('No one got the answer!  It was: %s') % self.a[0])
                self.unanswered += 1
                self.newquestion()
            else:
                self.hint()


        def hint(self):
            self.hints += 1
            ans = self.a[0]
            hintPercentage = self.registryValue('hintPercentage', self.channel)
            divider = int(math.ceil(len(ans) * hintPercentage * self.hints ))
            if divider == len(ans):
                divider -= 1
            show = ans[ : divider]
            blank = ans[divider : ]
            blankChar = self.registryValue('blankChar', self.channel)
            blank = re.sub('\w', blankChar, blank)
            self.reply(_('HINT: %s%s') % (show, blank))
            def event():
                self.timedEvent()
            timeout = self.registryValue('timeout', self.channel)
            numHints = self.registryValue('numHints', self.channel)
            eventTime = time.time() + timeout / (numHints + 1)
            if self.active:
                schedule.addEvent(event, eventTime, 'next_%s' % self.channel)


        def answer(self, msg):
            correct = False
            for ans in self.a:
                dist = self.DL(str.lower(msg.args[1]), str.lower(ans))
                flexibility = self.registryValue('flexibility', self.channel)
                if dist <= len(ans) / flexibility:
                    correct = True
                #if self.registryValue('debug'):
                #    self.reply('Distance: %d' % dist)
            if correct:
                if not msg.nick in self.scores:
                    self.scores[msg.nick] = 0
                self.scores[msg.nick] += 1
                if not msg.nick in self.roundscores:
                    self.roundscores[msg.nick] = 0
                self.roundscores[msg.nick] += 1
                self.unanswered = 0
                self.reply(_('%s got it!  The full answer was: %s. Points: %d') %
                           (msg.nick, self.a[0], self.scores[msg.nick]))
                schedule.removeEvent('next_%s' % self.channel)
                self.writeScores()
                self.newquestion()


        def reply(self, s):
            self.irc.queueMsg(ircmsgs.privmsg(self.channel, s))


        def writeScores(self):
            f = open(self.scorefile, 'w')
            scores = self.scores.iteritems()
            for i in range(0, len(self.scores)):
                score = scores.next()
                f.write('%s %s\n' % (score[0], score[1]))
            f.close()


        def DL(self, seq1, seq2):
            oneago = None
            thisrow = range(1, len(seq2) + 1) + [0]
            for x in xrange(len(seq1)):
                # Python lists wrap around for negative indices, so put the
                # leftmost column at the *end* of the list. This matches with
                # the zero-indexed strings and saves extra calculation.
                twoago, oneago, thisrow = oneago, thisrow, [0]*len(seq2)+[x+1]
                for y in xrange(len(seq2)):
                    delcost = oneago[y] + 1
                    addcost = thisrow[y - 1] + 1
                    subcost = oneago[y - 1] + (seq1[x] != seq2[y])
                    thisrow[y] = min(delcost, addcost, subcost)
                    # This block deals with transpositions
                    if x > 0 and y > 0 and seq1[x] == seq2[y - 1] and \
                            seq1[x-1] == seq2[y] and seq1[x] != seq2[y]:
                        thisrow[y] = min(thisrow[y], twoago[y - 2] + 1)
            return thisrow[len(seq2) - 1]

    @internationalizeDocstring
    def start(self, irc, msg, args, channel, num):
        """[<channel>] [<number of questions>]

        Starts a game of trivia.  <channel> is only necessary if the message
        isn't sent in the channel itself."""
        if num == None:
            num = self.registryValue('defaultRoundLength', channel)
        #elif num > 100:
        #    irc.reply('sorry, for now, you can\'t start games with more '
        #              'than 100 questions :(')
        #    num = 100
        channel = ircutils.toLower(channel)
        if channel in self.games:
            if not self.games[channel].active:
                del self.games[channel]
                try:
                    schedule.removeEvent('next_%s' % channel)
                except KeyError:
                    pass
                irc.reply(_('Orphaned trivia game found and removed.'))
            else:
                self.games[channel].num += num
                self.games[channel].total += num
                irc.reply(_('%d questions added to active game!') % num)
        else:
            self.games[channel] = self.Game(irc, channel, num, self)
        irc.noReply()
    start = wrap(start, ['channel', optional('positiveInt')])

    @internationalizeDocstring
    def stop(self, irc, msg, args, channel):
        """[<channel>]

        Stops a running game of trivia.  <channel> is only necessary if the
        message isn't sent in the channel itself."""
        channel = ircutils.toLower(channel)
        try:
            schedule.removeEvent('next_%s' % channel)
        except KeyError:
            irc.error(_('No trivia started'))
        if channel in self.games:
            if self.games[channel].active:
                self.games[channel].stop()
            else:
                del self.games[channel]
                irc.reply(_('Trivia stopped'))
        else:
            irc.noReply()
    stop = wrap(stop, ['channel'])


Class = Trivia


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class TriviaTestCase(ChannelPluginTestCase):
    plugins = ('Trivia',)

    def testStartStop(self):
        self.assertRegexp('start', '...#1 of 10:.*')
        self.assertResponse('stop', 'Trivia stopping.')
        self.assertError('stop')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry

try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('Twitter')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Twitter', True)


Twitter = conf.registerPlugin('Twitter')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Twitter, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))

conf.registerChannelValue(Twitter, 'prefixusername',
        registry.Boolean(True, _("""Determines whether or not the name of the
        user posting a tweet will be shown prefixed.""")))

conf.registerGroup(Twitter, 'accounts')

helpGetToken = _('running get_access_token.py is a way to get it')

conf.registerGroup(Twitter, 'consumer')
conf.registerGlobalValue(Twitter.consumer, 'key',
        registry.String('bItq1HZhBGyx5Y8ardIeQ',
            _("""The consumer key of the application.""")))
conf.registerGlobalValue(Twitter.consumer, 'secret',
        registry.String('qjC6Ye6xSMM3XPLR3LLeMqOP4ri0rgoYFT2si1RpY',
            _("""The consumer secret of the application."""), private=True))

conf.registerGroup(Twitter.accounts, 'bot')
conf.registerGlobalValue(Twitter.accounts.bot, 'key',
        registry.String('', _("""The Twitter Access Token key for the bot's
        account (%s)""") % helpGetToken))
conf.registerGlobalValue(Twitter.accounts.bot, 'secret',
        registry.String('', _("""The Twitter Access Token secret for the bot's
        account (%s)""") % helpGetToken, private=True))
conf.registerGlobalValue(Twitter.accounts.bot, 'api',
        registry.String('https://api.twitter.com/1.1', _("""The URL to the
        base API URL (by default, it is Twitter.com, but you can use it
        for twitter-compatible services, such as identica/statusnet.""")))

conf.registerGroup(Twitter.accounts, 'channel')
conf.registerChannelValue(Twitter.accounts.channel, 'key',
        registry.String('', _("""The Twitter Access Token key for this
        channel's account (%s)""") % helpGetToken))
conf.registerChannelValue(Twitter.accounts.channel, 'secret',
        registry.String('', _("""The Twitter Access Token secret for this
        channel's account (%s)""") % helpGetToken, private=True))
conf.registerChannelValue(Twitter.accounts.channel, 'api',
        registry.String('https://api.twitter.com/1.1', _("""The URL to the
        base API URL (by default, it is Twitter.com, but you can use it
        for twitter-compatible services, such as identica/statusnet.""")))

conf.registerGroup(Twitter, 'announce')
conf.registerChannelValue(Twitter.announce, 'interval',
        registry.NonNegativeInteger(0, _("""The interval (in seconds) between
        two fetches of new tweets from the timeline. 0 (zero) disables this
        feature.""")))
conf.registerChannelValue(Twitter.announce, 'withid',
        registry.Boolean(True, _("""Determines whether or not the ID of
        announced tweets will be displayed.""")))
conf.registerChannelValue(Twitter.announce, 'withshortid',
        registry.Boolean(True, _("""Determines whether or not the ID of
        announced tweets will be displayed.""")))
conf.registerChannelValue(Twitter.announce, 'oneline',
        registry.Boolean(True, _("""Determines whether or not all tweets will
        be shown in one line.""")))
conf.registerChannelValue(Twitter.announce, 'retweets',
        registry.Boolean(True, _("""Determines whether or not the bot will
        show retweets in addition to native tweets.""")))
conf.registerChannelValue(Twitter.announce, 'timeline',
        registry.Boolean(True, _("""Determines whether the bot will stream
        the timeline of the linked account on the channel (only if
        supybot.plugins.Twitter.announce.interval is greater than 0).""")))
conf.registerChannelValue(Twitter.announce, 'mentions',
        registry.Boolean(True, _("""Determines whether the bot will stream
        mentions to the linked account on the channel (only if
        supybot.plugins.Twitter.announce.interval is greater than 0).""")))
conf.registerChannelValue(Twitter.announce, 'users',
        registry.SpaceSeparatedListOfStrings([], _("""Determines users whose
        tweets will be announced on the channel.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = get_access_token
#!/usr/bin/python
#
# Copyright 2007 The Python-Twitter Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import sys

# parse_qsl moved to urlparse module in v2.6
try:
  from urlparse import parse_qsl
except:
  from cgi import parse_qsl

import oauth2 as oauth

REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
ACCESS_TOKEN_URL  = 'https://api.twitter.com/oauth/access_token'
AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'
SIGNIN_URL        = 'https://api.twitter.com/oauth/authenticate'

consumer_key    = 'bItq1HZhBGyx5Y8ardIeQ'
consumer_secret = 'qjC6Ye6xSMM3XPLR3LLeMqOP4ri0rgoYFT2si1RpY'

if consumer_key is None or consumer_secret is None:
  print 'You need to edit this script and provide values for the'
  print 'consumer_key and also consumer_secret.'
  print ''
  print 'The values you need come from Twitter - you need to register'
  print 'as a developer your "application".  This is needed only until'
  print 'Twitter finishes the idea they have of a way to allow open-source'
  print 'based libraries to have a token that can be used to generate a'
  print 'one-time use key that will allow the library to make the request'
  print 'on your behalf.'
  print ''
  sys.exit(1)

signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()
oauth_consumer             = oauth.Consumer(key=consumer_key, secret=consumer_secret)
oauth_client               = oauth.Client(oauth_consumer)

print 'Requesting temp token from Twitter'

resp, content = oauth_client.request(REQUEST_TOKEN_URL, 'GET')

if resp['status'] != '200':
  print 'Invalid respond from Twitter requesting temp token: %s' % resp['status']
else:
  request_token = dict(parse_qsl(content))

  print ''
  print 'Please visit this Twitter page and retrieve the pincode to be used'
  print 'in the next step to obtaining an Authentication Token:'
  print ''
  print '%s?oauth_token=%s' % (AUTHORIZATION_URL, request_token['oauth_token'])
  print ''

  pincode = raw_input('Pincode? ')

  token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
  token.set_verifier(pincode)

  print ''
  print 'Generating and signing request for an access token'
  print ''

  oauth_client  = oauth.Client(oauth_consumer, token)
  resp, content = oauth_client.request(ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % pincode)
  access_token  = dict(parse_qsl(content))

  if resp['status'] != '200':
    print 'The request for a Token did not succeed: %s' % resp['status']
    print access_token
  else:
    print 'Your Twitter Access Token key: %s' % access_token['oauth_token']
    print '          Access Token secret: %s' % access_token['oauth_token_secret']
    print ''


########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from __future__ import division


import re
import sys
import time
import json
import operator
import functools
import threading
import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks
if sys.version_info[0] < 3:
    import htmlentitydefs
else:
    import html.entities as htmlentitydefs
    from imp import reload
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('Twitter')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

try:
    import twitter
except ImportError:
    raise callbacks.Error('You need the python-twitter library.')
except Exception as e:
    raise callbacks.Error('Unknown exception importing twitter: %r' % e)
reload(twitter)
if not hasattr(twitter, '__version__') or \
        twitter.__version__.split('.') < ['0', '8', '0']:
    raise ImportError('You current version of python-twitter is to old, '
                      'you need at least version 0.8.0, because older '
                      'versions do not support OAuth authentication.')


class ExtendedApi(twitter.Api):
    """Api with retweet support."""

    def PostRetweet(self, id):
        '''Retweet a tweet with the Retweet API

        The twitter.Api instance must be authenticated.

        Args:
        id: The numerical ID of the tweet you are retweeting

        Returns:
        A twitter.Status instance representing the retweet posted
        '''
        if hasattr(api, '_oauth_consumer') and not api._oauth_consumer:
            raise TwitterError("The twitter.Api instance must be authenticated.")
        try:
            if int(id) <= 0:
                raise TwitterError("'id' must be a positive number")
        except ValueError:
            raise TwitterError("'id' must be an integer")
        url = 'http://api.twitter.com/1/statuses/retweet/%s.json' % id
        data = self._FetchUrl(url, post_data={'dummy': None})
        data = json.loads(data)
        self._CheckForTwitterError(data)
        return twitter.Status.NewFromJsonDict(data)

_tco_link_re = re.compile('http://t.co/[a-zA-Z0-9]+')
def expandLinks(tweet):
    if 'Untiny.plugin' in sys.modules:
        def repl(link):
            return sys.modules['Untiny.plugin'].Untiny(None) \
                    ._untiny(None, link.group(0))
        return _tco_link_re.sub(repl, tweet)
    else:
        return tweet

def fetch(method, maxIds, name):
    if name not in maxIds:
        maxIds[name] = None
    if maxIds[name] is None:
        tweets = method()
    else:
        tweets = method(since_id=maxIds[name])
    if not tweets:
        return []

    if maxIds[name] is None:
        maxIds[name] = tweets[0].id
        return []
    else:
        maxIds[name] = tweets[0].id
        return tweets


@internationalizeDocstring
class Twitter(callbacks.Plugin):
    """Add the help for "@plugin help Twitter" here
    This should describe *how* to use this plugin."""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(Twitter, self)
        callbacks.Plugin.__init__(self, irc)
        self._apis = {}
        self._died = False
        if world.starting:
            try:
                self._getApi().PostUpdate(_('I just woke up. :)'))
            except:
                pass
        self._runningAnnounces = []
        try:
            conf.supybot.plugins.Twitter.consumer.key.addCallback(
                    self._dropApiObjects)
            conf.supybot.plugins.Twitter.consumer.secret.addCallback(
                    self._dropApiObjects)
            conf.supybot.plugins.Twitter.accounts.channel.key.addCallback(
                    self._dropApiObjects)
            conf.supybot.plugins.Twitter.accounts.channel.secret.addCallback(
                    self._dropApiObjects)
            conf.supybot.plugins.Twitter.accounts.channel.api.addCallback(
                    self._dropApiObjects)
        except registry.NonExistentRegistryEntry:
            log.error('Your version of Supybot is not compatible with '
                      'configuration hooks. So, Twitter won\'t be able '
                      'to apply changes to the consumer key/secret '
                      'and token key/secret unless you reload it.')
        self._shortids = {}
        self._current_shortid = 0

    def _dropApiObjects(self, name=None):
        self._apis = {}


    def _getApi(self, channel):
        if channel in self._apis:
            # TODO: handle configuration changes (using Limnoria's config hooks)
            return self._apis[channel]
        if channel is None:
            key = self.registryValue('accounts.bot.key')
            secret = self.registryValue('accounts.bot.secret')
            url = self.registryValue('accounts.bot.api')
        else:
            key = self.registryValue('accounts.channel.key', channel)
            secret = self.registryValue('accounts.channel.secret', channel)
            url = self.registryValue('accounts.channel.api')
        if key == '' or secret == '':
            return ExtendedApi(base_url=url)
        api = ExtendedApi(consumer_key=self.registryValue('consumer.key'),
                consumer_secret=self.registryValue('consumer.secret'),
                access_token_key=key,
                access_token_secret=secret,
                base_url=url)
        self._apis[channel] = api
        return api

    def _get_shortid(self, longid):
        characters = '0123456789abcdefghijklmnopwrstuvwyz'
        id_ = self._current_shortid + 1
        id_ %= (36**4)
        self._current_shortid = id_
        shortid = ''
        while len(shortid) < 3:
            quotient, remainder = divmod(id_, 36)
            shortid = characters[remainder] + shortid
            id_ = quotient
        self._shortids[shortid] = longid
        return shortid

    def _unescape(self, text):
        """Created by Fredrik Lundh (http://effbot.org/zone/re-sub.htm#unescape-html)"""
        text = text.replace("\n", " ")
        def fixup(m):
            text = m.group(0)
            if text[:2] == "&#":
                # character reference
                try:
                    if text[:3] == "&#x":
                        return unichr(int(text[3:-1], 16))
                    else:
                        return unichr(int(text[2:-1]))
                except (ValueError, OverflowError):
                    pass
            else:
                # named entity
                try:
                    text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
                except KeyError:
                    pass
            return text # leave as is
        return re.sub("&#?\w+;", fixup, text)

    def __call__(self, irc, msg):
        super(Twitter, self).__call__(irc, msg)
        irc = callbacks.SimpleProxy(irc, msg)
        for channel in irc.state.channels:
            if self.registryValue('announce.interval', channel) != 0 and \
                    channel not in self._runningAnnounces:
                threading.Thread(target=self._fetchTimeline,
                        args=(irc, channel),
                        name='Twitter timeline for %s' % channel).start()

    def _fetchTimeline(self, irc, channel):
        if channel in self._runningAnnounces:
            # Prevent race conditions
            return
        lastRun = time.time()
        maxIds = {}
        self._runningAnnounces.append(channel)
        try:
            while not irc.zombie and not self._died and \
                    self.registryValue('announce.interval', channel) != 0:
                while lastRun is not None and \
                        lastRun+self.registryValue('announce.interval', channel)>time.time():
                    time.sleep(5)
                lastRun = time.time()
                self.log.debug(_('Fetching tweets for channel %s') % channel)
                api = self._getApi(channel) # Reload it from conf everytime
                if hasattr(api, '_oauth_consumer') and not api._oauth_consumer:
                    return
                retweets = self.registryValue('announce.retweets', channel)
                try:
                    tweets = []
                    if self.registryValue('announce.timeline', channel):
                        tweets.extend(fetch(
                            functools.partial(api.GetFriendsTimeline,
                                              retweets=retweets),
                            maxIds, 'timeline'))
                    if self.registryValue('announce.mentions', channel):
                        tweets.extend(fetch(api.GetReplies,
                            maxIds, 'mentions'))
                    for user in self.registryValue('announce.users', channel):
                        if not user.startswith('@'):
                            user = '@' + user
                        tweets.extend(fetch(
                            functools.partial(api.GetUserTimeline,
                                screen_name=user[1:]),
                            maxIds, user))
                except twitter.TwitterError as e:
                    self.log.error('Could not fetch timeline: %s' % e)
                    continue
                if not tweets:
                    continue
                tweets.sort(key=operator.attrgetter('id'))
                format_ = '@%(user)s> %(msg)s'
                if self.registryValue('announce.withid', channel):
                    format_ = '[%(longid)s] ' + format_
                if self.registryValue('announce.withshortid', channel):
                    format_ = '(%(shortid)s) ' + format_
                replies = [format_ % {'longid': x.id,
                                      'shortid': self._get_shortid(x.id),
                                      'user': x.user.screen_name,
                                      'msg': x.text
                                     } for x in tweets]

                replies = map(self._unescape, replies)
                replies = map(expandLinks, replies)
                if self.registryValue('announce.oneline', channel):
                    irc.replies(replies, prefixNick=False, joiner=' | ',
                            to=channel)
                else:
                    for reply in replies:
                        irc.reply(reply, prefixNick=False, to=channel)
        finally:
            assert channel in self._runningAnnounces
            self._runningAnnounces.remove(channel)



    @internationalizeDocstring
    def following(self, irc, msg, args, channel, user):
        """[<channel>] [<user>]

        Replies with the people this <user> follows. If <user> is not given, it
        defaults to the <channel>'s account. If <channel> is not given, it
        defaults to the current channel."""
        api = self._getApi(channel)
        if hasattr(api, '_oauth_consumer') and not api._oauth_consumer and user is None:
            irc.error(_('No account is associated with this channel. Ask '
                        'an op, try with another channel, or provide '
                        'a user name.'))
            return
        following = api.GetFriends(user) # If user is not given, it defaults
                                       # to None, and giving None to
                                       # GetFriends() has the expected
                                       # behaviour.
        reply = utils.str.format("%L", ['%s (%s)' % (x.name, x.screen_name)
                                        for x in following])
        reply = self._unescape(reply)
        irc.reply(reply)
    following = wrap(following, ['channel',
                                     optional('somethingWithoutSpaces')])

    @internationalizeDocstring
    def followers(self, irc, msg, args, channel):
        """[<channel>]

        Replies with the people that follow this account. If <channel> is not
        given, it defaults to the current channel."""
        api = self._getApi(channel)
        if hasattr(api, '_oauth_consumer') and not api._oauth_consumer:
            irc.error(_('No account is associated with this channel. Ask '
                        'an op, try with another channel, or provide '
                        'a user name.'))
            return
        followers = api.GetFollowers()
        reply = utils.str.format("%L", ['%s (%s)' % (x.name, x.screen_name)
                                        for x in followers])
        reply = self._unescape(reply)
        irc.reply(reply)
    followers = wrap(followers, ['channel'])

    @internationalizeDocstring
    def dm(self, irc, msg, args, user, channel, recipient, message):
        """[<channel>] <recipient> <message>

        Sends a <message> to <recipient> from the account associated with the
        given <channel>. If <channel> is not given, it defaults to the current
        channel."""
        api = self._getApi(channel)
        if hasattr(api, '_oauth_consumer') and not api._oauth_consumer:
            irc.error(_('No account is associated with this channel. Ask '
                        'an op or try with another channel.'))
            return

        if len(message) > 140:
            irc.error(_('Sorry, your message exceeds 140 characters (%i)') %
                    len(message))
        else:
            api.PostDirectMessage(recipient, message)
            irc.replySuccess()
    dm = wrap(dm, ['user', ('checkChannelCapability', 'twitteradmin'),
                   'somethingWithoutSpaces', 'text'])

    @internationalizeDocstring
    def post(self, irc, msg, args, user, channel, message):
        """[<channel>] <message>

        Updates the status of the account associated with the given <channel>
        to the <message>. If <channel> is not given, it defaults to the
        current channel."""
        api = self._getApi(channel)
        if hasattr(api, '_oauth_consumer') and not api._oauth_consumer:
            irc.error(_('No account is associated with this channel. Ask '
                        'an op or try with another channel.'))
            return
        tweet = message
        if self.registryValue('prefixusername', channel):
            tweet = '[%s] %s' % (user.name, tweet)
        if len(tweet) > 140:
            irc.error(_('Sorry, your tweet exceeds 140 characters (%i)') %
                    len(tweet))
        else:
            api.PostUpdate(tweet)
            irc.replySuccess()
    post = wrap(post, ['user', ('checkChannelCapability', 'twitterpost'), 'text'])

    @internationalizeDocstring
    def retweet(self, irc, msg, args, user, channel, id_):
        """[<channel>] <id>

        Retweets the message with the given ID."""
        api = self._getApi(channel)
        try:
            if len(id_) <= 3:
                try:
                    id_ = self._shortids[id_]
                except KeyError:
                    irc.error(_('This is not a valid ID.'))
                    return
            else:
                try:
                    id_ = int(id_)
                except ValueError:
                    irc.error(_('This is not a valid ID.'))
                    return
            api.PostRetweet(id_)
            irc.replySuccess()
        except twitter.TwitterError as e:
            irc.error(e.args[0])
    retweet = wrap(retweet, ['user', ('checkChannelCapability', 'twitterpost'),
            'somethingWithoutSpaces'])

    @internationalizeDocstring
    def timeline(self, irc, msg, args, channel, tupleOptlist, user):
        """[<channel>] [--since <oldest>] [--max <newest>] [--count <number>] \
        [--noretweet] [--with-id] [<user>]

        Replies with the timeline of the <user>.
        If <user> is not given, it defaults to the account associated with the
        <channel>.
        If <channel> is not given, it defaults to the current channel.
        If given, --since and --max take tweet IDs, used as boundaries.
        If given, --count takes an integer, that stands for the number of
        tweets to display.
        If --noretweet is given, only native user's tweet will be displayed.
        """
        optlist = {}
        for key, value in tupleOptlist:
            optlist.update({key: value})
        for key in ('since', 'max', 'count'):
            if key not in optlist:
                optlist[key] = None
        optlist['noretweet'] = 'noretweet' in optlist
        optlist['with-id'] = 'with-id' in optlist

        api = self._getApi(channel)
        if hasattr(api, '_oauth_consumer') and not api._oauth_consumer and user is None:
            irc.error(_('No account is associated with this channel. Ask '
                        'an op, try with another channel.'))
            return
        try:
            timeline = api.GetUserTimeline(screen_name=user,
                                           since_id=optlist['since'],
                                           max_id=optlist['max'],
                                           count=optlist['count'],
                                           include_rts=not optlist['noretweet'])
        except twitter.TwitterError:
            irc.error(_('This user protects his tweets; you need to fetch '
                        'them from a channel whose associated account can '
                        'fetch this timeline.'))
            return
        if optlist['with-id']:
            reply = ' | '.join(['[%s] %s' % (x.id, expandLinks(x.text))
                    for x in timeline])
        else:
            reply = ' | '.join([expandLinks(x.text) for x in timeline])

        reply = self._unescape(reply)
        irc.reply(reply)
    timeline = wrap(timeline, ['channel',
                               getopts({'since': 'int',
                                        'max': 'int',
                                        'count': 'int',
                                        'noretweet': '',
                                        'with-id': ''}),
                               optional('somethingWithoutSpaces')])

    @internationalizeDocstring
    def public(self, irc, msg, args, channel, tupleOptlist):
        """[<channel>] [--since <oldest>]

        Replies with the public timeline.
        If <channel> is not given, it defaults to the current channel.
        If given, --since takes a tweet ID, used as a boundary
        """
        optlist = {}
        for key, value in tupleOptlist:
            optlist.update({key: value})

        if 'since' not in optlist:
            optlist['since'] = None

        api = self._getApi(channel)
        try:
            public = api.GetPublicTimeline(since_id=optlist['since'])
        except twitter.TwitterError:
            irc.error(_('No tweets'))
            return
        reply = ' | '.join([expandLinks(x.text) for x in public])

        reply = self._unescape(reply)
        irc.reply(reply)
    public = wrap(public, ['channel', getopts({'since': 'int'})])

    @internationalizeDocstring
    def replies(self, irc, msg, args, channel, tupleOptlist):
        """[<channel>] [--since <oldest>]

        Replies with the replies timeline.
        If <channel> is not given, it defaults to the current channel.
        If given, --since takes a tweet ID, used as a boundary
        """
        optlist = {}
        for key, value in tupleOptlist:
            optlist.update({key: value})

        if 'since' not in optlist:
            optlist['since'] = None
        id_ = optlist['since'] or '0000'

        if len(id_) <= 3:
            try:
                id_ = self._shortids[id_]
            except KeyError:
                irc.error(_('This is not a valid ID.'))
                return
        else:
            try:
                id_ = int(id_)
            except ValueError:
                irc.error(_('This is not a valid ID.'))
                return

        api = self._getApi(channel)
        try:
            replies = api.GetReplies(since_id=id_)
        except twitter.TwitterError:
            irc.error(_('No tweets'))
            return
        reply = ' | '.join(["%s: %s" % (x.user.screen_name, expandLinks(x.text))
                for x in replies])

        reply = self._unescape(reply)
        irc.reply(reply)
    replies = wrap(replies, ['channel',
        getopts({'since': 'somethingWithoutSpaces'})])

    @internationalizeDocstring
    def trends(self, irc, msg, args, channel):
        """[<channel>]

        Current trending topics
        If <channel> is not given, it defaults to the current channel.
        """

        api = self._getApi(channel)
        try:
            trends = api.GetTrendsCurrent()
        except twitter.TwitterError:
            irc.error(_('No tweets'))
            return
        reply = self._unescape(reply)
        irc.reply(reply)
    trends = wrap(trends, ['channel'])

    @internationalizeDocstring
    def follow(self, irc, msg, args, channel, user):
        """[<channel>] <user>

        Follow a specified <user>
        If <channel> is not given, it defaults to the current channel.
        """

        api = self._getApi(channel)
        if hasattr(api, '_oauth_consumer') and not api._oauth_consumer:
            irc.error(_('No account is associated with this channel. Ask '
                        'an op, try with another channel.'))
            return
        try:
            follow = api.CreateFriendship(user)
        except twitter.TwitterError:
            irc.error(_('An error occurred'))
            return

        irc.replySuccess()
    follow = wrap(follow, ['channel', ('checkChannelCapability', 'twitteradmin'),
                           'somethingWithoutSpaces'])

    @internationalizeDocstring
    def unfollow(self, irc, msg, args, channel, user):
        """[<channel>] <user>

        Unfollow a specified <user>
        If <channel> is not given, it defaults to the current channel.
        """

        api = self._getApi(channel)
        if hasattr(api, '_oauth_consumer') and not api._oauth_consumer:
            irc.error(_('No account is associated with this channel. Ask '
                        'an op, try with another channel.'))
            return
        try:
            unfollow = api.DestroyFriendship(user)
        except twitter.TwitterError:
            irc.error(_('An error occurred'))
            return

        irc.replySuccess()
    unfollow = wrap(unfollow, ['channel',
                               ('checkChannelCapability', 'twitteradmin'),
                               'somethingWithoutSpaces'])

    @internationalizeDocstring
    def delete(self, irc, msg, args, channel, id_):
        """[<channel>] <id>

        Delete a specified status with id <id>
        If <channel> is not given, it defaults to the current channel.
        """
        if len(id_) <= 3:
            try:
                id_ = self._shortids[id_]
            except KeyError:
                irc.error(_('This is not a valid ID.'))
                return
        else:
            try:
                id_ = int(id_)
            except ValueError:
                irc.error(_('This is not a valid ID.'))
                return

        api = self._getApi(channel)
        if hasattr(api, '_oauth_consumer') and not api._oauth_consumer:
            irc.error(_('No account is associated with this channel. Ask '
                        'an op, try with another channel.'))
            return
        try:
            delete = api.DestroyStatus(id_)
        except twitter.TwitterError:
            irc.error(_('An error occurred'))
            return

        irc.replySuccess()
    delete = wrap(delete, ['channel',
                               ('checkChannelCapability', 'twitteradmin'),
                               'somethingWithoutSpaces'])

    @internationalizeDocstring
    def stats(self, irc, msg, args, channel):
        """[<channel>]

        Print some stats
        If <channel> is not given, it defaults to the current channel.
        """
        api = self._getApi(channel)
        try:
            reply = {}
            reply['followers'] = len(api.GetFollowers())
            reply['following'] = len(api.GetFriends(None))
        except twitter.TwitterError:
            irc.error(_('An error occurred'))
            return
        reply = "I am following %d people and have %d followers" % (reply['following'], reply['followers'])
        irc.reply(reply)
    stats = wrap(stats, ['channel'])

    @internationalizeDocstring
    def profile(self, irc, msg, args, channel, user=None):
        """[<channel>] [<user>]

        Return profile image for a specified <user>
        If <channel> is not given, it defaults to the current channel.
        """

        api = self._getApi(channel)
        if hasattr(api, '_oauth_consumer') and not api._oauth_consumer:
            irc.error(_('No account is associated with this channel. Ask '
                        'an op, try with another channel.'))
            return
        try:
            if user:
                profile = api.GetUser(user)
            else:
                profile = api.VerifyCredentials()
        except twitter.TwitterError:
            irc.error(_('An error occurred'))
            return

        irc.reply(('Name: @%s (%s). Profile picture: %s. Biography: %s') %
                (profile.screen_name,
                 profile.name,
                 profile.GetProfileImageUrl().replace('_normal', ''),
                 profile.description))
    profile = wrap(profile, ['channel', optional('somethingWithoutSpaces')])


    def die(self):
        self.__parent.die()
        self._died = True

Class = Twitter


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:


########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

from . import plugin

class TwitterTestCase(ChannelPluginTestCase):
    plugins = ('Twitter', 'Untiny')

    if network:
        def testExpandLinks(self):
            self.assertEqual(plugin.expandLinks('foo http://t.co/zIgJjeBV bar'),
                    'foo http://osteele.com/posts/2004/11/ides bar')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = twitter
#!/usr/bin/python2.4
#
# Copyright 2007 The Python-Twitter Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''A library that provides a Python interface to the Twitter API'''

__author__ = 'python-twitter@googlegroups.com'
__version__ = '0.8.3'


import base64
import calendar
import datetime
import httplib
import os
import rfc822
import sys
import tempfile
import textwrap
import time
import calendar
import urllib
import urllib2
import urlparse
import gzip
import StringIO

try:
  # Python >= 2.6
  import json as simplejson
except ImportError:
  try:
    # Python < 2.6
    import simplejson
  except ImportError:
    try:
      # Google App Engine
      from django.utils import simplejson
    except ImportError:
      raise ImportError, "Unable to load a json library"

# parse_qsl moved to urlparse module in v2.6
try:
  from urlparse import parse_qsl, parse_qs
except ImportError:
  from cgi import parse_qsl, parse_qs

try:
  from hashlib import md5
except ImportError:
  from md5 import md5

import oauth2 as oauth


CHARACTER_LIMIT = 140

# A singleton representing a lazily instantiated FileCache.
DEFAULT_CACHE = object()

REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
ACCESS_TOKEN_URL  = 'https://api.twitter.com/oauth/access_token'
AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'
SIGNIN_URL        = 'https://api.twitter.com/oauth/authenticate'


class TwitterError(Exception):
  '''Base class for Twitter errors'''

  @property
  def message(self):
    '''Returns the first argument used to construct this error.'''
    return self.args[0]


class Status(object):
  '''A class representing the Status structure used by the twitter API.
  
  The Status structure exposes the following properties:
  
    status.created_at
    status.created_at_in_seconds # read only
    status.favorited
    status.in_reply_to_screen_name
    status.in_reply_to_user_id
    status.in_reply_to_status_id
    status.truncated
    status.source
    status.id
    status.text
    status.location
    status.relative_created_at # read only
    status.user
    status.urls
    status.user_mentions
    status.hashtags
    status.geo
    status.place
    status.coordinates
    status.contributors
  '''
  def __init__(self,
               created_at=None,
               favorited=None,
               id=None,
               text=None,
               location=None,
               user=None,
               in_reply_to_screen_name=None,
               in_reply_to_user_id=None,
               in_reply_to_status_id=None,
               truncated=None,
               source=None,
               now=None,
               urls=None,
               user_mentions=None,
               hashtags=None,
               geo=None,
               place=None,
               coordinates=None,
               contributors=None,
               retweeted=None,
               retweeted_status=None,
               retweet_count=None):
    '''An object to hold a Twitter status message.

    This class is normally instantiated by the twitter.Api class and
    returned in a sequence.

    Note: Dates are posted in the form "Sat Jan 27 04:17:38 +0000 2007"

    Args:
      created_at:
        The time this status message was posted. [Optional]
      favorited:
        Whether this is a favorite of the authenticated user. [Optional]
      id:
        The unique id of this status message. [Optional]
      text:
        The text of this status message. [Optional]
      location:
        the geolocation string associated with this message. [Optional]
      relative_created_at:
        A human readable string representing the posting time. [Optional]
      user:
        A twitter.User instance representing the person posting the
        message. [Optional]
      now:
        The current time, if the client choses to set it.
        Defaults to the wall clock time. [Optional]
      urls:
      user_mentions:
      hashtags:
      geo:
      place:
      coordinates:
      contributors:
      retweeted:
      retweeted_status:
      retweet_count:
    '''
    self.created_at = created_at
    self.favorited = favorited
    self.id = id
    self.text = text
    self.location = location
    self.user = user
    self.now = now
    self.in_reply_to_screen_name = in_reply_to_screen_name
    self.in_reply_to_user_id = in_reply_to_user_id
    self.in_reply_to_status_id = in_reply_to_status_id
    self.truncated = truncated
    self.retweeted = retweeted
    self.source = source
    self.urls = urls
    self.user_mentions = user_mentions
    self.hashtags = hashtags
    self.geo = geo
    self.place = place
    self.coordinates = coordinates
    self.contributors = contributors
    self.retweeted_status = retweeted_status
    self.retweet_count = retweet_count

  def GetCreatedAt(self):
    '''Get the time this status message was posted.

    Returns:
      The time this status message was posted
    '''
    return self._created_at

  def SetCreatedAt(self, created_at):
    '''Set the time this status message was posted.

    Args:
      created_at:
        The time this status message was created
    '''
    self._created_at = created_at

  created_at = property(GetCreatedAt, SetCreatedAt,
                        doc='The time this status message was posted.')

  def GetCreatedAtInSeconds(self):
    '''Get the time this status message was posted, in seconds since the epoch.

    Returns:
      The time this status message was posted, in seconds since the epoch.
    '''
    return calendar.timegm(rfc822.parsedate(self.created_at))

  created_at_in_seconds = property(GetCreatedAtInSeconds,
                                   doc="The time this status message was "
                                       "posted, in seconds since the epoch")

  def GetFavorited(self):
    '''Get the favorited setting of this status message.

    Returns:
      True if this status message is favorited; False otherwise
    '''
    return self._favorited

  def SetFavorited(self, favorited):
    '''Set the favorited state of this status message.

    Args:
      favorited:
        boolean True/False favorited state of this status message
    '''
    self._favorited = favorited

  favorited = property(GetFavorited, SetFavorited,
                       doc='The favorited state of this status message.')

  def GetId(self):
    '''Get the unique id of this status message.

    Returns:
      The unique id of this status message
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this status message.

    Args:
      id:
        The unique id of this status message
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this status message.')

  def GetInReplyToScreenName(self):
    return self._in_reply_to_screen_name

  def SetInReplyToScreenName(self, in_reply_to_screen_name):
    self._in_reply_to_screen_name = in_reply_to_screen_name

  in_reply_to_screen_name = property(GetInReplyToScreenName, SetInReplyToScreenName,
                                     doc='')

  def GetInReplyToUserId(self):
    return self._in_reply_to_user_id

  def SetInReplyToUserId(self, in_reply_to_user_id):
    self._in_reply_to_user_id = in_reply_to_user_id

  in_reply_to_user_id = property(GetInReplyToUserId, SetInReplyToUserId,
                                 doc='')

  def GetInReplyToStatusId(self):
    return self._in_reply_to_status_id

  def SetInReplyToStatusId(self, in_reply_to_status_id):
    self._in_reply_to_status_id = in_reply_to_status_id

  in_reply_to_status_id = property(GetInReplyToStatusId, SetInReplyToStatusId,
                                   doc='')

  def GetTruncated(self):
    return self._truncated

  def SetTruncated(self, truncated):
    self._truncated = truncated

  truncated = property(GetTruncated, SetTruncated,
                       doc='')

  def GetRetweeted(self):
    return self._retweeted

  def SetRetweeted(self, retweeted):
    self._retweeted = retweeted

  retweeted = property(GetRetweeted, SetRetweeted,
                       doc='')

  def GetSource(self):
    return self._source

  def SetSource(self, source):
    self._source = source

  source = property(GetSource, SetSource,
                    doc='')

  def GetText(self):
    '''Get the text of this status message.

    Returns:
      The text of this status message.
    '''
    return self._text

  def SetText(self, text):
    '''Set the text of this status message.

    Args:
      text:
        The text of this status message
    '''
    self._text = text

  text = property(GetText, SetText,
                  doc='The text of this status message')

  def GetLocation(self):
    '''Get the geolocation associated with this status message

    Returns:
      The geolocation string of this status message.
    '''
    return self._location

  def SetLocation(self, location):
    '''Set the geolocation associated with this status message

    Args:
      location:
        The geolocation string of this status message
    '''
    self._location = location

  location = property(GetLocation, SetLocation,
                      doc='The geolocation string of this status message')

  def GetRelativeCreatedAt(self):
    '''Get a human redable string representing the posting time

    Returns:
      A human readable string representing the posting time
    '''
    fudge = 1.25
    delta  = long(self.now) - long(self.created_at_in_seconds)

    if delta < (1 * fudge):
      return 'about a second ago'
    elif delta < (60 * (1/fudge)):
      return 'about %d seconds ago' % (delta)
    elif delta < (60 * fudge):
      return 'about a minute ago'
    elif delta < (60 * 60 * (1/fudge)):
      return 'about %d minutes ago' % (delta / 60)
    elif delta < (60 * 60 * fudge) or delta / (60 * 60) == 1:
      return 'about an hour ago'
    elif delta < (60 * 60 * 24 * (1/fudge)):
      return 'about %d hours ago' % (delta / (60 * 60))
    elif delta < (60 * 60 * 24 * fudge) or delta / (60 * 60 * 24) == 1:
      return 'about a day ago'
    else:
      return 'about %d days ago' % (delta / (60 * 60 * 24))

  relative_created_at = property(GetRelativeCreatedAt,
                                 doc='Get a human readable string representing '
                                     'the posting time')

  def GetUser(self):
    '''Get a twitter.User reprenting the entity posting this status message.

    Returns:
      A twitter.User reprenting the entity posting this status message
    '''
    return self._user

  def SetUser(self, user):
    '''Set a twitter.User reprenting the entity posting this status message.

    Args:
      user:
        A twitter.User reprenting the entity posting this status message
    '''
    self._user = user

  user = property(GetUser, SetUser,
                  doc='A twitter.User reprenting the entity posting this '
                      'status message')

  def GetNow(self):
    '''Get the wallclock time for this status message.

    Used to calculate relative_created_at.  Defaults to the time
    the object was instantiated.

    Returns:
      Whatever the status instance believes the current time to be,
      in seconds since the epoch.
    '''
    if self._now is None:
      self._now = time.time()
    return self._now

  def SetNow(self, now):
    '''Set the wallclock time for this status message.

    Used to calculate relative_created_at.  Defaults to the time
    the object was instantiated.

    Args:
      now:
        The wallclock time for this instance.
    '''
    self._now = now

  now = property(GetNow, SetNow,
                 doc='The wallclock time for this status instance.')

  def GetGeo(self):
    return self._geo

  def SetGeo(self, geo):
    self._geo = geo

  geo = property(GetGeo, SetGeo,
                 doc='')

  def GetPlace(self):
    return self._place

  def SetPlace(self, place):
    self._place = place

  place = property(GetPlace, SetPlace,
                   doc='')

  def GetCoordinates(self):
    return self._coordinates

  def SetCoordinates(self, coordinates):
    self._coordinates = coordinates

  coordinates = property(GetCoordinates, SetCoordinates,
                         doc='')

  def GetContributors(self):
    return self._contributors

  def SetContributors(self, contributors):
    self._contributors = contributors

  contributors = property(GetContributors, SetContributors,
                          doc='')

  def GetRetweeted_status(self):
    return self._retweeted_status

  def SetRetweeted_status(self, retweeted_status):
    self._retweeted_status = retweeted_status

  retweeted_status = property(GetRetweeted_status, SetRetweeted_status,
                              doc='')

  def GetRetweetCount(self):
    return self._retweet_count

  def SetRetweetCount(self, retweet_count):
    self._retweet_count = retweet_count

  retweet_count = property(GetRetweetCount, SetRetweetCount,
                           doc='')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
             self.created_at == other.created_at and \
             self.id == other.id and \
             self.text == other.text and \
             self.location == other.location and \
             self.user == other.user and \
             self.in_reply_to_screen_name == other.in_reply_to_screen_name and \
             self.in_reply_to_user_id == other.in_reply_to_user_id and \
             self.in_reply_to_status_id == other.in_reply_to_status_id and \
             self.truncated == other.truncated and \
             self.retweeted == other.retweeted and \
             self.favorited == other.favorited and \
             self.source == other.source and \
             self.geo == other.geo and \
             self.place == other.place and \
             self.coordinates == other.coordinates and \
             self.contributors == other.contributors and \
             self.retweeted_status == other.retweeted_status and \
             self.retweet_count == other.retweet_count
    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.Status instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.Status instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.Status instance.

    Returns:
      A JSON string representation of this twitter.Status instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.Status instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.Status instance
    '''
    data = {}
    if self.created_at:
      data['created_at'] = self.created_at
    if self.favorited:
      data['favorited'] = self.favorited
    if self.id:
      data['id'] = self.id
    if self.text:
      data['text'] = self.text
    if self.location:
      data['location'] = self.location
    if self.user:
      data['user'] = self.user.AsDict()
    if self.in_reply_to_screen_name:
      data['in_reply_to_screen_name'] = self.in_reply_to_screen_name
    if self.in_reply_to_user_id:
      data['in_reply_to_user_id'] = self.in_reply_to_user_id
    if self.in_reply_to_status_id:
      data['in_reply_to_status_id'] = self.in_reply_to_status_id
    if self.truncated is not None:
      data['truncated'] = self.truncated
    if self.retweeted is not None:
      data['retweeted'] = self.retweeted
    if self.favorited is not None:
      data['favorited'] = self.favorited
    if self.source:
      data['source'] = self.source
    if self.geo:
      data['geo'] = self.geo
    if self.place:
      data['place'] = self.place
    if self.coordinates:
      data['coordinates'] = self.coordinates
    if self.contributors:
      data['contributors'] = self.contributors
    if self.hashtags:
      data['hashtags'] = [h.text for h in self.hashtags]
    if self.retweeted_status:
      data['retweeted_status'] = self.retweeted_status.AsDict()
    if self.retweet_count:
      data['retweet_count'] = self.retweet_count
    if self.urls:
      data['urls'] = dict([(url.url, url.expanded_url) for url in self.urls])
    if self.user_mentions:
      data['user_mentions'] = [um.AsDict() for um in self.user_mentions]                                                                                                                                       
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data: A JSON dict, as converted from the JSON in the twitter API
    Returns:
      A twitter.Status instance
    '''
    if 'user' in data:
      user = User.NewFromJsonDict(data['user'])
    else:
      user = None
    if 'retweeted_status' in data:
      retweeted_status = Status.NewFromJsonDict(data['retweeted_status'])
    else:
      retweeted_status = None
    urls = None
    user_mentions = None
    hashtags = None
    if 'entities' in data:
      if 'urls' in data['entities']:
        urls = [Url.NewFromJsonDict(u) for u in data['entities']['urls']]
      if 'user_mentions' in data['entities']:
        user_mentions = [User.NewFromJsonDict(u) for u in data['entities']['user_mentions']]
      if 'hashtags' in data['entities']:
        hashtags = [Hashtag.NewFromJsonDict(h) for h in data['entities']['hashtags']]
    return Status(created_at=data.get('created_at', None),
                  favorited=data.get('favorited', None),
                  id=data.get('id', None),
                  text=data.get('text', None),
                  location=data.get('location', None),
                  in_reply_to_screen_name=data.get('in_reply_to_screen_name', None),
                  in_reply_to_user_id=data.get('in_reply_to_user_id', None),
                  in_reply_to_status_id=data.get('in_reply_to_status_id', None),
                  truncated=data.get('truncated', None),
                  retweeted=data.get('retweeted', None),
                  source=data.get('source', None),
                  user=user,
                  urls=urls,
                  user_mentions=user_mentions,
                  hashtags=hashtags,
                  geo=data.get('geo', None),
                  place=data.get('place', None),
                  coordinates=data.get('coordinates', None),
                  contributors=data.get('contributors', None),
                  retweeted_status=retweeted_status,
                  retweet_count=data.get('retweet_count', None))


class User(object):
  '''A class representing the User structure used by the twitter API.

  The User structure exposes the following properties:

    user.id
    user.name
    user.screen_name
    user.location
    user.description
    user.profile_image_url
    user.profile_background_tile
    user.profile_background_image_url
    user.profile_sidebar_fill_color
    user.profile_background_color
    user.profile_link_color
    user.profile_text_color
    user.protected
    user.utc_offset
    user.time_zone
    user.url
    user.status
    user.statuses_count
    user.followers_count
    user.friends_count
    user.favourites_count
    user.geo_enabled
    user.verified
    user.lang
    user.notifications
    user.contributors_enabled
    user.created_at
    user.listed_count
  '''
  def __init__(self,
               id=None,
               name=None,
               screen_name=None,
               location=None,
               description=None,
               profile_image_url=None,
               profile_background_tile=None,
               profile_background_image_url=None,
               profile_sidebar_fill_color=None,
               profile_background_color=None,
               profile_link_color=None,
               profile_text_color=None,
               protected=None,
               utc_offset=None,
               time_zone=None,
               followers_count=None,
               friends_count=None,
               statuses_count=None,
               favourites_count=None,
               url=None,
               status=None,
               geo_enabled=None,
               verified=None,
               lang=None,
               notifications=None,
               contributors_enabled=None,
               created_at=None,
               listed_count=None):
    self.id = id
    self.name = name
    self.screen_name = screen_name
    self.location = location
    self.description = description
    self.profile_image_url = profile_image_url
    self.profile_background_tile = profile_background_tile
    self.profile_background_image_url = profile_background_image_url
    self.profile_sidebar_fill_color = profile_sidebar_fill_color
    self.profile_background_color = profile_background_color
    self.profile_link_color = profile_link_color
    self.profile_text_color = profile_text_color
    self.protected = protected
    self.utc_offset = utc_offset
    self.time_zone = time_zone
    self.followers_count = followers_count
    self.friends_count = friends_count
    self.statuses_count = statuses_count
    self.favourites_count = favourites_count
    self.url = url
    self.status = status
    self.geo_enabled = geo_enabled
    self.verified = verified
    self.lang = lang
    self.notifications = notifications
    self.contributors_enabled = contributors_enabled
    self.created_at = created_at
    self.listed_count = listed_count

  def GetId(self):
    '''Get the unique id of this user.

    Returns:
      The unique id of this user
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this user.

    Args:
      id: The unique id of this user.
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this user.')

  def GetName(self):
    '''Get the real name of this user.

    Returns:
      The real name of this user
    '''
    return self._name

  def SetName(self, name):
    '''Set the real name of this user.

    Args:
      name: The real name of this user
    '''
    self._name = name

  name = property(GetName, SetName,
                  doc='The real name of this user.')

  def GetScreenName(self):
    '''Get the short twitter name of this user.

    Returns:
      The short twitter name of this user
    '''
    return self._screen_name

  def SetScreenName(self, screen_name):
    '''Set the short twitter name of this user.

    Args:
      screen_name: the short twitter name of this user
    '''
    self._screen_name = screen_name

  screen_name = property(GetScreenName, SetScreenName,
                         doc='The short twitter name of this user.')

  def GetLocation(self):
    '''Get the geographic location of this user.

    Returns:
      The geographic location of this user
    '''
    return self._location

  def SetLocation(self, location):
    '''Set the geographic location of this user.

    Args:
      location: The geographic location of this user
    '''
    self._location = location

  location = property(GetLocation, SetLocation,
                      doc='The geographic location of this user.')

  def GetDescription(self):
    '''Get the short text description of this user.

    Returns:
      The short text description of this user
    '''
    return self._description

  def SetDescription(self, description):
    '''Set the short text description of this user.

    Args:
      description: The short text description of this user
    '''
    self._description = description

  description = property(GetDescription, SetDescription,
                         doc='The short text description of this user.')

  def GetUrl(self):
    '''Get the homepage url of this user.

    Returns:
      The homepage url of this user
    '''
    return self._url

  def SetUrl(self, url):
    '''Set the homepage url of this user.

    Args:
      url: The homepage url of this user
    '''
    self._url = url

  url = property(GetUrl, SetUrl,
                 doc='The homepage url of this user.')

  def GetProfileImageUrl(self):
    '''Get the url of the thumbnail of this user.

    Returns:
      The url of the thumbnail of this user
    '''
    return self._profile_image_url

  def SetProfileImageUrl(self, profile_image_url):
    '''Set the url of the thumbnail of this user.

    Args:
      profile_image_url: The url of the thumbnail of this user
    '''
    self._profile_image_url = profile_image_url

  profile_image_url= property(GetProfileImageUrl, SetProfileImageUrl,
                              doc='The url of the thumbnail of this user.')

  def GetProfileBackgroundTile(self):
    '''Boolean for whether to tile the profile background image.

    Returns:
      True if the background is to be tiled, False if not, None if unset.
    '''
    return self._profile_background_tile

  def SetProfileBackgroundTile(self, profile_background_tile):
    '''Set the boolean flag for whether to tile the profile background image.

    Args:
      profile_background_tile: Boolean flag for whether to tile or not.
    '''
    self._profile_background_tile = profile_background_tile

  profile_background_tile = property(GetProfileBackgroundTile, SetProfileBackgroundTile,
                                     doc='Boolean for whether to tile the background image.')

  def GetProfileBackgroundImageUrl(self):
    return self._profile_background_image_url

  def SetProfileBackgroundImageUrl(self, profile_background_image_url):
    self._profile_background_image_url = profile_background_image_url

  profile_background_image_url = property(GetProfileBackgroundImageUrl, SetProfileBackgroundImageUrl,
                                          doc='The url of the profile background of this user.')

  def GetProfileSidebarFillColor(self):
    return self._profile_sidebar_fill_color

  def SetProfileSidebarFillColor(self, profile_sidebar_fill_color):
    self._profile_sidebar_fill_color = profile_sidebar_fill_color

  profile_sidebar_fill_color = property(GetProfileSidebarFillColor, SetProfileSidebarFillColor)

  def GetProfileBackgroundColor(self):
    return self._profile_background_color

  def SetProfileBackgroundColor(self, profile_background_color):
    self._profile_background_color = profile_background_color

  profile_background_color = property(GetProfileBackgroundColor, SetProfileBackgroundColor)

  def GetProfileLinkColor(self):
    return self._profile_link_color

  def SetProfileLinkColor(self, profile_link_color):
    self._profile_link_color = profile_link_color

  profile_link_color = property(GetProfileLinkColor, SetProfileLinkColor)

  def GetProfileTextColor(self):
    return self._profile_text_color

  def SetProfileTextColor(self, profile_text_color):
    self._profile_text_color = profile_text_color

  profile_text_color = property(GetProfileTextColor, SetProfileTextColor)

  def GetProtected(self):
    return self._protected

  def SetProtected(self, protected):
    self._protected = protected

  protected = property(GetProtected, SetProtected)

  def GetUtcOffset(self):
    return self._utc_offset

  def SetUtcOffset(self, utc_offset):
    self._utc_offset = utc_offset

  utc_offset = property(GetUtcOffset, SetUtcOffset)

  def GetTimeZone(self):
    '''Returns the current time zone string for the user.

    Returns:
      The descriptive time zone string for the user.
    '''
    return self._time_zone

  def SetTimeZone(self, time_zone):
    '''Sets the user's time zone string.

    Args:
      time_zone:
        The descriptive time zone to assign for the user.
    '''
    self._time_zone = time_zone

  time_zone = property(GetTimeZone, SetTimeZone)

  def GetStatus(self):
    '''Get the latest twitter.Status of this user.

    Returns:
      The latest twitter.Status of this user
    '''
    return self._status

  def SetStatus(self, status):
    '''Set the latest twitter.Status of this user.

    Args:
      status:
        The latest twitter.Status of this user
    '''
    self._status = status

  status = property(GetStatus, SetStatus,
                    doc='The latest twitter.Status of this user.')

  def GetFriendsCount(self):
    '''Get the friend count for this user.

    Returns:
      The number of users this user has befriended.
    '''
    return self._friends_count

  def SetFriendsCount(self, count):
    '''Set the friend count for this user.

    Args:
      count:
        The number of users this user has befriended.
    '''
    self._friends_count = count

  friends_count = property(GetFriendsCount, SetFriendsCount,
                           doc='The number of friends for this user.')

  def GetListedCount(self):
    '''Get the listed count for this user.

    Returns:
      The number of lists this user belongs to.
    '''
    return self._listed_count

  def SetListedCount(self, count):
    '''Set the listed count for this user.

    Args:
      count:
        The number of lists this user belongs to.
    '''
    self._listed_count = count

  listed_count = property(GetListedCount, SetListedCount,
                          doc='The number of lists this user belongs to.')

  def GetFollowersCount(self):
    '''Get the follower count for this user.

    Returns:
      The number of users following this user.
    '''
    return self._followers_count

  def SetFollowersCount(self, count):
    '''Set the follower count for this user.

    Args:
      count:
        The number of users following this user.
    '''
    self._followers_count = count

  followers_count = property(GetFollowersCount, SetFollowersCount,
                             doc='The number of users following this user.')

  def GetStatusesCount(self):
    '''Get the number of status updates for this user.

    Returns:
      The number of status updates for this user.
    '''
    return self._statuses_count

  def SetStatusesCount(self, count):
    '''Set the status update count for this user.

    Args:
      count:
        The number of updates for this user.
    '''
    self._statuses_count = count

  statuses_count = property(GetStatusesCount, SetStatusesCount,
                            doc='The number of updates for this user.')

  def GetFavouritesCount(self):
    '''Get the number of favourites for this user.

    Returns:
      The number of favourites for this user.
    '''
    return self._favourites_count

  def SetFavouritesCount(self, count):
    '''Set the favourite count for this user.

    Args:
      count:
        The number of favourites for this user.
    '''
    self._favourites_count = count

  favourites_count = property(GetFavouritesCount, SetFavouritesCount,
                              doc='The number of favourites for this user.')

  def GetGeoEnabled(self):
    '''Get the setting of geo_enabled for this user.

    Returns:
      True/False if Geo tagging is enabled
    '''
    return self._geo_enabled

  def SetGeoEnabled(self, geo_enabled):
    '''Set the latest twitter.geo_enabled of this user.

    Args:
      geo_enabled:
        True/False if Geo tagging is to be enabled
    '''
    self._geo_enabled = geo_enabled

  geo_enabled = property(GetGeoEnabled, SetGeoEnabled,
                         doc='The value of twitter.geo_enabled for this user.')

  def GetVerified(self):
    '''Get the setting of verified for this user.

    Returns:
      True/False if user is a verified account
    '''
    return self._verified

  def SetVerified(self, verified):
    '''Set twitter.verified for this user.

    Args:
      verified:
        True/False if user is a verified account
    '''
    self._verified = verified

  verified = property(GetVerified, SetVerified,
                      doc='The value of twitter.verified for this user.')

  def GetLang(self):
    '''Get the setting of lang for this user.

    Returns:
      language code of the user
    '''
    return self._lang

  def SetLang(self, lang):
    '''Set twitter.lang for this user.

    Args:
      lang:
        language code for the user
    '''
    self._lang = lang

  lang = property(GetLang, SetLang,
                  doc='The value of twitter.lang for this user.')

  def GetNotifications(self):
    '''Get the setting of notifications for this user.

    Returns:
      True/False for the notifications setting of the user
    '''
    return self._notifications

  def SetNotifications(self, notifications):
    '''Set twitter.notifications for this user.

    Args:
      notifications:
        True/False notifications setting for the user
    '''
    self._notifications = notifications

  notifications = property(GetNotifications, SetNotifications,
                           doc='The value of twitter.notifications for this user.')

  def GetContributorsEnabled(self):
    '''Get the setting of contributors_enabled for this user.

    Returns:
      True/False contributors_enabled of the user
    '''
    return self._contributors_enabled

  def SetContributorsEnabled(self, contributors_enabled):
    '''Set twitter.contributors_enabled for this user.

    Args:
      contributors_enabled:
        True/False contributors_enabled setting for the user
    '''
    self._contributors_enabled = contributors_enabled

  contributors_enabled = property(GetContributorsEnabled, SetContributorsEnabled,
                                  doc='The value of twitter.contributors_enabled for this user.')

  def GetCreatedAt(self):
    '''Get the setting of created_at for this user.

    Returns:
      created_at value of the user
    '''
    return self._created_at

  def SetCreatedAt(self, created_at):
    '''Set twitter.created_at for this user.

    Args:
      created_at:
        created_at value for the user
    '''
    self._created_at = created_at

  created_at = property(GetCreatedAt, SetCreatedAt,
                        doc='The value of twitter.created_at for this user.')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
             self.id == other.id and \
             self.name == other.name and \
             self.screen_name == other.screen_name and \
             self.location == other.location and \
             self.description == other.description and \
             self.profile_image_url == other.profile_image_url and \
             self.profile_background_tile == other.profile_background_tile and \
             self.profile_background_image_url == other.profile_background_image_url and \
             self.profile_sidebar_fill_color == other.profile_sidebar_fill_color and \
             self.profile_background_color == other.profile_background_color and \
             self.profile_link_color == other.profile_link_color and \
             self.profile_text_color == other.profile_text_color and \
             self.protected == other.protected and \
             self.utc_offset == other.utc_offset and \
             self.time_zone == other.time_zone and \
             self.url == other.url and \
             self.statuses_count == other.statuses_count and \
             self.followers_count == other.followers_count and \
             self.favourites_count == other.favourites_count and \
             self.friends_count == other.friends_count and \
             self.status == other.status and \
             self.geo_enabled == other.geo_enabled and \
             self.verified == other.verified and \
             self.lang == other.lang and \
             self.notifications == other.notifications and \
             self.contributors_enabled == other.contributors_enabled and \
             self.created_at == other.created_at and \
             self.listed_count == other.listed_count

    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.User instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.User instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.User instance.

    Returns:
      A JSON string representation of this twitter.User instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.User instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.User instance
    '''
    data = {}
    if self.id:
      data['id'] = self.id
    if self.name:
      data['name'] = self.name
    if self.screen_name:
      data['screen_name'] = self.screen_name
    if self.location:
      data['location'] = self.location
    if self.description:
      data['description'] = self.description
    if self.profile_image_url:
      data['profile_image_url'] = self.profile_image_url
    if self.profile_background_tile is not None:
      data['profile_background_tile'] = self.profile_background_tile
    if self.profile_background_image_url:
      data['profile_sidebar_fill_color'] = self.profile_background_image_url
    if self.profile_background_color:
      data['profile_background_color'] = self.profile_background_color
    if self.profile_link_color:
      data['profile_link_color'] = self.profile_link_color
    if self.profile_text_color:
      data['profile_text_color'] = self.profile_text_color
    if self.protected is not None:
      data['protected'] = self.protected
    if self.utc_offset:
      data['utc_offset'] = self.utc_offset
    if self.time_zone:
      data['time_zone'] = self.time_zone
    if self.url:
      data['url'] = self.url
    if self.status:
      data['status'] = self.status.AsDict()
    if self.friends_count:
      data['friends_count'] = self.friends_count
    if self.followers_count:
      data['followers_count'] = self.followers_count
    if self.statuses_count:
      data['statuses_count'] = self.statuses_count
    if self.favourites_count:
      data['favourites_count'] = self.favourites_count
    if self.geo_enabled:
      data['geo_enabled'] = self.geo_enabled
    if self.verified:
      data['verified'] = self.verified
    if self.lang:
      data['lang'] = self.lang
    if self.notifications:
      data['notifications'] = self.notifications
    if self.contributors_enabled:
      data['contributors_enabled'] = self.contributors_enabled
    if self.created_at:
      data['created_at'] = self.created_at
    if self.listed_count:
      data['listed_count'] = self.listed_count

    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data:
        A JSON dict, as converted from the JSON in the twitter API

    Returns:
      A twitter.User instance
    '''
    if 'status' in data:
      status = Status.NewFromJsonDict(data['status'])
    else:
      status = None
    return User(id=data.get('id', None),
                name=data.get('name', None),
                screen_name=data.get('screen_name', None),
                location=data.get('location', None),
                description=data.get('description', None),
                statuses_count=data.get('statuses_count', None),
                followers_count=data.get('followers_count', None),
                favourites_count=data.get('favourites_count', None),
                friends_count=data.get('friends_count', None),
                profile_image_url=data.get('profile_image_url', None),
                profile_background_tile = data.get('profile_background_tile', None),
                profile_background_image_url = data.get('profile_background_image_url', None),
                profile_sidebar_fill_color = data.get('profile_sidebar_fill_color', None),
                profile_background_color = data.get('profile_background_color', None),
                profile_link_color = data.get('profile_link_color', None),
                profile_text_color = data.get('profile_text_color', None),
                protected = data.get('protected', None),
                utc_offset = data.get('utc_offset', None),
                time_zone = data.get('time_zone', None),
                url=data.get('url', None),
                status=status,
                geo_enabled=data.get('geo_enabled', None),
                verified=data.get('verified', None),
                lang=data.get('lang', None),
                notifications=data.get('notifications', None),
                contributors_enabled=data.get('contributors_enabled', None),
                created_at=data.get('created_at', None),
                listed_count=data.get('listed_count', None))

class List(object):
  '''A class representing the List structure used by the twitter API.
  
  The List structure exposes the following properties:
  
    list.id
    list.name
    list.slug
    list.description
    list.full_name
    list.mode
    list.uri
    list.member_count
    list.subscriber_count
    list.following
  '''
  def __init__(self,
               id=None,
               name=None,
               slug=None,
               description=None,
               full_name=None,
               mode=None,
               uri=None,
               member_count=None,
               subscriber_count=None,
               following=None,
               user=None):
    self.id = id
    self.name = name
    self.slug = slug
    self.description = description
    self.full_name = full_name
    self.mode = mode
    self.uri = uri
    self.member_count = member_count
    self.subscriber_count = subscriber_count
    self.following = following
    self.user = user

  def GetId(self):
    '''Get the unique id of this list.

    Returns:
      The unique id of this list
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this list.

    Args:
      id:
        The unique id of this list.
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this list.')

  def GetName(self):
    '''Get the real name of this list.

    Returns:
      The real name of this list
    '''
    return self._name

  def SetName(self, name):
    '''Set the real name of this list.

    Args:
      name:
        The real name of this list
    '''
    self._name = name

  name = property(GetName, SetName,
                  doc='The real name of this list.')

  def GetSlug(self):
    '''Get the slug of this list.

    Returns:
      The slug of this list
    '''
    return self._slug

  def SetSlug(self, slug):
    '''Set the slug of this list.

    Args:
      slug:
        The slug of this list.
    '''
    self._slug = slug

  slug = property(GetSlug, SetSlug,
                  doc='The slug of this list.')

  def GetDescription(self):
    '''Get the description of this list.

    Returns:
      The description of this list
    '''
    return self._description

  def SetDescription(self, description):
    '''Set the description of this list.

    Args:
      description:
        The description of this list.
    '''
    self._description = description

  description = property(GetDescription, SetDescription,
                         doc='The description of this list.')

  def GetFull_name(self):
    '''Get the full_name of this list.

    Returns:
      The full_name of this list
    '''
    return self._full_name

  def SetFull_name(self, full_name):
    '''Set the full_name of this list.

    Args:
      full_name:
        The full_name of this list.
    '''
    self._full_name = full_name

  full_name = property(GetFull_name, SetFull_name,
                       doc='The full_name of this list.')

  def GetMode(self):
    '''Get the mode of this list.

    Returns:
      The mode of this list
    '''
    return self._mode

  def SetMode(self, mode):
    '''Set the mode of this list.

    Args:
      mode:
        The mode of this list.
    '''
    self._mode = mode

  mode = property(GetMode, SetMode,
                  doc='The mode of this list.')

  def GetUri(self):
    '''Get the uri of this list.

    Returns:
      The uri of this list
    '''
    return self._uri

  def SetUri(self, uri):
    '''Set the uri of this list.

    Args:
      uri:
        The uri of this list.
    '''
    self._uri = uri

  uri = property(GetUri, SetUri,
                 doc='The uri of this list.')

  def GetMember_count(self):
    '''Get the member_count of this list.

    Returns:
      The member_count of this list
    '''
    return self._member_count

  def SetMember_count(self, member_count):
    '''Set the member_count of this list.

    Args:
      member_count:
        The member_count of this list.
    '''
    self._member_count = member_count

  member_count = property(GetMember_count, SetMember_count,
                          doc='The member_count of this list.')

  def GetSubscriber_count(self):
    '''Get the subscriber_count of this list.

    Returns:
      The subscriber_count of this list
    '''
    return self._subscriber_count

  def SetSubscriber_count(self, subscriber_count):
    '''Set the subscriber_count of this list.

    Args:
      subscriber_count:
        The subscriber_count of this list.
    '''
    self._subscriber_count = subscriber_count

  subscriber_count = property(GetSubscriber_count, SetSubscriber_count,
                              doc='The subscriber_count of this list.')

  def GetFollowing(self):
    '''Get the following status of this list.

    Returns:
      The following status of this list
    '''
    return self._following

  def SetFollowing(self, following):
    '''Set the following status of this list.

    Args:
      following:
        The following of this list.
    '''
    self._following = following

  following = property(GetFollowing, SetFollowing,
                       doc='The following status of this list.')

  def GetUser(self):
    '''Get the user of this list.

    Returns:
      The owner of this list
    '''
    return self._user

  def SetUser(self, user):
    '''Set the user of this list.

    Args:
      user:
        The owner of this list.
    '''
    self._user = user

  user = property(GetUser, SetUser,
                  doc='The owner of this list.')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
             self.id == other.id and \
             self.name == other.name and \
             self.slug == other.slug and \
             self.description == other.description and \
             self.full_name == other.full_name and \
             self.mode == other.mode and \
             self.uri == other.uri and \
             self.member_count == other.member_count and \
             self.subscriber_count == other.subscriber_count and \
             self.following == other.following and \
             self.user == other.user

    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.List instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.List instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.List instance.

    Returns:
      A JSON string representation of this twitter.List instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.List instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.List instance
    '''
    data = {}
    if self.id:
      data['id'] = self.id
    if self.name:
      data['name'] = self.name
    if self.slug:
      data['slug'] = self.slug
    if self.description:
      data['description'] = self.description
    if self.full_name:
      data['full_name'] = self.full_name
    if self.mode:
      data['mode'] = self.mode
    if self.uri:
      data['uri'] = self.uri
    if self.member_count is not None:
      data['member_count'] = self.member_count
    if self.subscriber_count is not None:
      data['subscriber_count'] = self.subscriber_count
    if self.following is not None:
      data['following'] = self.following
    if self.user is not None:
      data['user'] = self.user
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data:
        A JSON dict, as converted from the JSON in the twitter API

    Returns:
      A twitter.List instance
    '''
    if 'user' in data:
      user = User.NewFromJsonDict(data['user'])
    else:
      user = None
    return List(id=data.get('id', None),
                name=data.get('name', None),
                slug=data.get('slug', None),
                description=data.get('description', None),
                full_name=data.get('full_name', None),
                mode=data.get('mode', None),
                uri=data.get('uri', None),
                member_count=data.get('member_count', None),
                subscriber_count=data.get('subscriber_count', None),
                following=data.get('following', None),
                user=user)

class DirectMessage(object):
  '''A class representing the DirectMessage structure used by the twitter API.
  
  The DirectMessage structure exposes the following properties:
  
    direct_message.id
    direct_message.created_at
    direct_message.created_at_in_seconds # read only
    direct_message.sender_id
    direct_message.sender_screen_name
    direct_message.recipient_id
    direct_message.recipient_screen_name
    direct_message.text
  '''

  def __init__(self,
               id=None,
               created_at=None,
               sender_id=None,
               sender_screen_name=None,
               recipient_id=None,
               recipient_screen_name=None,
               text=None):
    '''An object to hold a Twitter direct message.

    This class is normally instantiated by the twitter.Api class and
    returned in a sequence.

    Note: Dates are posted in the form "Sat Jan 27 04:17:38 +0000 2007"

    Args:
      id:
        The unique id of this direct message. [Optional]
      created_at:
        The time this direct message was posted. [Optional]
      sender_id:
        The id of the twitter user that sent this message. [Optional]
      sender_screen_name:
        The name of the twitter user that sent this message. [Optional]
      recipient_id:
        The id of the twitter that received this message. [Optional]
      recipient_screen_name:
        The name of the twitter that received this message. [Optional]
      text:
        The text of this direct message. [Optional]
    '''
    self.id = id
    self.created_at = created_at
    self.sender_id = sender_id
    self.sender_screen_name = sender_screen_name
    self.recipient_id = recipient_id
    self.recipient_screen_name = recipient_screen_name
    self.text = text

  def GetId(self):
    '''Get the unique id of this direct message.

    Returns:
      The unique id of this direct message
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this direct message.

    Args:
      id:
        The unique id of this direct message
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this direct message.')

  def GetCreatedAt(self):
    '''Get the time this direct message was posted.

    Returns:
      The time this direct message was posted
    '''
    return self._created_at

  def SetCreatedAt(self, created_at):
    '''Set the time this direct message was posted.

    Args:
      created_at:
        The time this direct message was created
    '''
    self._created_at = created_at

  created_at = property(GetCreatedAt, SetCreatedAt,
                        doc='The time this direct message was posted.')

  def GetCreatedAtInSeconds(self):
    '''Get the time this direct message was posted, in seconds since the epoch.

    Returns:
      The time this direct message was posted, in seconds since the epoch.
    '''
    return calendar.timegm(rfc822.parsedate(self.created_at))

  created_at_in_seconds = property(GetCreatedAtInSeconds,
                                   doc="The time this direct message was "
                                       "posted, in seconds since the epoch")

  def GetSenderId(self):
    '''Get the unique sender id of this direct message.

    Returns:
      The unique sender id of this direct message
    '''
    return self._sender_id

  def SetSenderId(self, sender_id):
    '''Set the unique sender id of this direct message.

    Args:
      sender_id:
        The unique sender id of this direct message
    '''
    self._sender_id = sender_id

  sender_id = property(GetSenderId, SetSenderId,
                doc='The unique sender id of this direct message.')

  def GetSenderScreenName(self):
    '''Get the unique sender screen name of this direct message.

    Returns:
      The unique sender screen name of this direct message
    '''
    return self._sender_screen_name

  def SetSenderScreenName(self, sender_screen_name):
    '''Set the unique sender screen name of this direct message.

    Args:
      sender_screen_name:
        The unique sender screen name of this direct message
    '''
    self._sender_screen_name = sender_screen_name

  sender_screen_name = property(GetSenderScreenName, SetSenderScreenName,
                doc='The unique sender screen name of this direct message.')

  def GetRecipientId(self):
    '''Get the unique recipient id of this direct message.

    Returns:
      The unique recipient id of this direct message
    '''
    return self._recipient_id

  def SetRecipientId(self, recipient_id):
    '''Set the unique recipient id of this direct message.

    Args:
      recipient_id:
        The unique recipient id of this direct message
    '''
    self._recipient_id = recipient_id

  recipient_id = property(GetRecipientId, SetRecipientId,
                doc='The unique recipient id of this direct message.')

  def GetRecipientScreenName(self):
    '''Get the unique recipient screen name of this direct message.

    Returns:
      The unique recipient screen name of this direct message
    '''
    return self._recipient_screen_name

  def SetRecipientScreenName(self, recipient_screen_name):
    '''Set the unique recipient screen name of this direct message.

    Args:
      recipient_screen_name:
        The unique recipient screen name of this direct message
    '''
    self._recipient_screen_name = recipient_screen_name

  recipient_screen_name = property(GetRecipientScreenName, SetRecipientScreenName,
                doc='The unique recipient screen name of this direct message.')

  def GetText(self):
    '''Get the text of this direct message.

    Returns:
      The text of this direct message.
    '''
    return self._text

  def SetText(self, text):
    '''Set the text of this direct message.

    Args:
      text:
        The text of this direct message
    '''
    self._text = text

  text = property(GetText, SetText,
                  doc='The text of this direct message')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
          self.id == other.id and \
          self.created_at == other.created_at and \
          self.sender_id == other.sender_id and \
          self.sender_screen_name == other.sender_screen_name and \
          self.recipient_id == other.recipient_id and \
          self.recipient_screen_name == other.recipient_screen_name and \
          self.text == other.text
    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.DirectMessage instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.DirectMessage instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.DirectMessage instance.

    Returns:
      A JSON string representation of this twitter.DirectMessage instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.DirectMessage instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.DirectMessage instance
    '''
    data = {}
    if self.id:
      data['id'] = self.id
    if self.created_at:
      data['created_at'] = self.created_at
    if self.sender_id:
      data['sender_id'] = self.sender_id
    if self.sender_screen_name:
      data['sender_screen_name'] = self.sender_screen_name
    if self.recipient_id:
      data['recipient_id'] = self.recipient_id
    if self.recipient_screen_name:
      data['recipient_screen_name'] = self.recipient_screen_name
    if self.text:
      data['text'] = self.text
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data:
        A JSON dict, as converted from the JSON in the twitter API

    Returns:
      A twitter.DirectMessage instance
    '''
    return DirectMessage(created_at=data.get('created_at', None),
                         recipient_id=data.get('recipient_id', None),
                         sender_id=data.get('sender_id', None),
                         text=data.get('text', None),
                         sender_screen_name=data.get('sender_screen_name', None),
                         id=data.get('id', None),
                         recipient_screen_name=data.get('recipient_screen_name', None))

class Hashtag(object):
  ''' A class represeinting a twitter hashtag
  '''
  def __init__(self,
               text=None):
    self.text = text

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data:
        A JSON dict, as converted from the JSON in the twitter API

    Returns:
      A twitter.Hashtag instance
    '''
    return Hashtag(text = data.get('text', None))

class Trend(object):
  ''' A class representing a trending topic
  '''
  def __init__(self, name=None, query=None, timestamp=None):
    self.name = name
    self.query = query
    self.timestamp = timestamp

  def __str__(self):
    return 'Name: %s\nQuery: %s\nTimestamp: %s\n' % (self.name, self.query, self.timestamp)

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
          self.name == other.name and \
          self.query == other.query and \
          self.timestamp == other.timestamp
    except AttributeError:
      return False

  @staticmethod
  def NewFromJsonDict(data, timestamp = None):
    '''Create a new instance based on a JSON dict

    Args:
      data:
        A JSON dict
      timestamp:
        Gets set as the timestamp property of the new object

    Returns:
      A twitter.Trend object
    '''
    return Trend(name=data.get('name', None),
                 query=data.get('query', None),
                 timestamp=timestamp)

class Url(object):
  '''A class representing an URL contained in a tweet'''
  def __init__(self,
               url=None,
               expanded_url=None):
    self.url = url
    self.expanded_url = expanded_url

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data:
        A JSON dict, as converted from the JSON in the twitter API

    Returns:
      A twitter.Url instance
    '''
    return Url(url=data.get('url', None),
               expanded_url=data.get('expanded_url', None))

class Api(object):
  '''A python interface into the Twitter API

  By default, the Api caches results for 1 minute.

  Example usage:

    To create an instance of the twitter.Api class, with no authentication:

      >>> import twitter
      >>> api = twitter.Api()

    To fetch the most recently posted public twitter status messages:

      >>> statuses = api.GetPublicTimeline()
      >>> print [s.user.name for s in statuses]
      [u'DeWitt', u'Kesuke Miyagi', u'ev', u'Buzz Andersen', u'Biz Stone'] #...

    To fetch a single user's public status messages, where "user" is either
    a Twitter "short name" or their user id.

      >>> statuses = api.GetUserTimeline(user)
      >>> print [s.text for s in statuses]

    To use authentication, instantiate the twitter.Api class with a
    consumer key and secret; and the oAuth key and secret:

      >>> api = twitter.Api(consumer_key='twitter consumer key',
                            consumer_secret='twitter consumer secret',
                            access_token_key='the_key_given',
                            access_token_secret='the_key_secret')

    To fetch your friends (after being authenticated):

      >>> users = api.GetFriends()
      >>> print [u.name for u in users]

    To post a twitter status message (after being authenticated):

      >>> status = api.PostUpdate('I love python-twitter!')
      >>> print status.text
      I love python-twitter!

    There are many other methods, including:

      >>> api.PostUpdates(status)
      >>> api.PostDirectMessage(user, text)
      >>> api.GetUser(user)
      >>> api.GetReplies()
      >>> api.GetUserTimeline(user)
      >>> api.GetStatus(id)
      >>> api.DestroyStatus(id)
      >>> api.GetFriendsTimeline(user)
      >>> api.GetFriends(user)
      >>> api.GetFollowers()
      >>> api.GetFeatured()
      >>> api.GetDirectMessages()
      >>> api.PostDirectMessage(user, text)
      >>> api.DestroyDirectMessage(id)
      >>> api.DestroyFriendship(user)
      >>> api.CreateFriendship(user)
      >>> api.GetUserByEmail(email)
      >>> api.VerifyCredentials()
  '''

  DEFAULT_CACHE_TIMEOUT = 60 # cache for 1 minute
  _API_REALM = 'Twitter API'

  def __init__(self,
               consumer_key=None,
               consumer_secret=None,
               access_token_key=None,
               access_token_secret=None,
               input_encoding=None,
               request_headers=None,
               cache=DEFAULT_CACHE,
               shortner=None,
               base_url=None,
               use_gzip_compression=False,
               debugHTTP=False):
    '''Instantiate a new twitter.Api object.

    Args:
      consumer_key:
        Your Twitter user's consumer_key.
      consumer_secret:
        Your Twitter user's consumer_secret.
      access_token_key:
        The oAuth access token key value you retrieved
        from running get_access_token.py.
      access_token_secret:
        The oAuth access token's secret, also retrieved
        from the get_access_token.py run.
      input_encoding:
        The encoding used to encode input strings. [Optional]
      request_header:
        A dictionary of additional HTTP request headers. [Optional]
      cache:
        The cache instance to use. Defaults to DEFAULT_CACHE.
        Use None to disable caching. [Optional]
      shortner:
        The shortner instance to use.  Defaults to None.
        See shorten_url.py for an example shortner. [Optional]
      base_url:
        The base URL to use to contact the Twitter API.
        Defaults to https://api.twitter.com. [Optional]
      use_gzip_compression:
        Set to True to tell enable gzip compression for any call
        made to Twitter.  Defaults to False. [Optional]
      debugHTTP:
        Set to True to enable debug output from urllib2 when performing
        any HTTP requests.  Defaults to False. [Optional]
    '''
    self.SetCache(cache)
    self._urllib         = urllib2
    self._cache_timeout  = Api.DEFAULT_CACHE_TIMEOUT
    self._input_encoding = input_encoding
    self._use_gzip       = use_gzip_compression
    self._debugHTTP      = debugHTTP
    self._oauth_consumer = None
    self._shortlink_size = 19

    self._InitializeRequestHeaders(request_headers)
    self._InitializeUserAgent()
    self._InitializeDefaultParameters()

    if base_url is None:
      self.base_url = 'https://api.twitter.com/1'
    else:
      self.base_url = base_url

    if consumer_key is not None and (access_token_key is None or
                                     access_token_secret is None):
      print >> sys.stderr, 'Twitter now requires an oAuth Access Token for API calls.'
      print >> sys.stderr, 'If your using this library from a command line utility, please'
      print >> sys.stderr, 'run the the included get_access_token.py tool to generate one.'

      raise TwitterError('Twitter requires oAuth Access Token for all API access')

    self.SetCredentials(consumer_key, consumer_secret, access_token_key, access_token_secret)

  def SetCredentials(self,
                     consumer_key,
                     consumer_secret,
                     access_token_key=None,
                     access_token_secret=None):
    '''Set the consumer_key and consumer_secret for this instance

    Args:
      consumer_key:
        The consumer_key of the twitter account.
      consumer_secret:
        The consumer_secret for the twitter account.
      access_token_key:
        The oAuth access token key value you retrieved
        from running get_access_token.py.
      access_token_secret:
        The oAuth access token's secret, also retrieved
        from the get_access_token.py run.
    '''
    self._consumer_key        = consumer_key
    self._consumer_secret     = consumer_secret
    self._access_token_key    = access_token_key
    self._access_token_secret = access_token_secret
    self._oauth_consumer      = None

    if consumer_key is not None and consumer_secret is not None and \
       access_token_key is not None and access_token_secret is not None:
      self._signature_method_plaintext = oauth.SignatureMethod_PLAINTEXT()
      self._signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()

      self._oauth_token    = oauth.Token(key=access_token_key, secret=access_token_secret)
      self._oauth_consumer = oauth.Consumer(key=consumer_key, secret=consumer_secret)

  def ClearCredentials(self):
    '''Clear the any credentials for this instance
    '''
    self._consumer_key        = None
    self._consumer_secret     = None
    self._access_token_key    = None
    self._access_token_secret = None
    self._oauth_consumer      = None

  def GetPublicTimeline(self,
                        since_id=None,
                        include_rts=None,
                        include_entities=None):
    '''Fetch the sequence of public twitter.Status message for all users.

    Args:
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occured since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      include_rts:
        If True, the timeline will contain native retweets (if they
        exist) in addition to the standard stream of tweets. [Optional]
      include_entities:
        If True, each tweet will include a node called "entities,".
        This node offers a variety of metadata about the tweet in a
        discreet structure, including: user_mentions, urls, and
        hashtags. [Optional]

    Returns:
      An sequence of twitter.Status instances, one for each message
    '''
    parameters = {}

    if since_id:
      parameters['since_id'] = since_id
    if include_rts:
      parameters['include_rts'] = 1
    if include_entities:
      parameters['include_entities'] = 1

    url  = '%s/statuses/public_timeline.json' % self.base_url
    json = self._FetchUrl(url,  parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(x) for x in data]

  def FilterPublicTimeline(self,
                           term,
                           since_id=None):
    '''Filter the public twitter timeline by a given search term on
    the local machine.

    Args:
      term:
        term to search by.
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occured since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]

    Returns:
      A sequence of twitter.Status instances, one for each message
      containing the term
    '''
    statuses = self.GetPublicTimeline(since_id)
    results  = []

    for s in statuses:
      if s.text.lower().find(term.lower()) != -1:
        results.append(s)

    return results

  def GetSearch(self,
                term=None,
                geocode=None,
                since_id=None,
                per_page=15,
                page=1,
                lang="en",
                show_user="true",
                query_users=False):
    '''Return twitter search results for a given term.

    Args:
      term:
        term to search by. Optional if you include geocode.
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occured since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      geocode:
        geolocation information in the form (latitude, longitude, radius)
        [Optional]
      per_page:
        number of results to return.  Default is 15 [Optional]
      page:
        Specifies the page of results to retrieve.
        Note: there are pagination limits. [Optional]
      lang:
        language for results.  Default is English [Optional]
      show_user:
        prefixes screen name in status
      query_users:
        If set to False, then all users only have screen_name and
        profile_image_url available.
        If set to True, all information of users are available,
        but it uses lots of request quota, one per status.

    Returns:
      A sequence of twitter.Status instances, one for each message containing
      the term
    '''
    # Build request parameters
    parameters = {}

    if since_id:
      parameters['since_id'] = since_id

    if term is None and geocode is None:
      return []

    if term is not None:
      parameters['q'] = term

    if geocode is not None:
      parameters['geocode'] = ','.join(map(str, geocode))

    parameters['show_user'] = show_user
    parameters['lang'] = lang
    parameters['rpp'] = per_page
    parameters['page'] = page

    # Make and send requests
    url  = 'http://search.twitter.com/search.json'
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)

    results = []

    for x in data['results']:
      temp = Status.NewFromJsonDict(x)

      if query_users:
        # Build user object with new request
        temp.user = self.GetUser(urllib.quote(x['from_user']))
      else:
        temp.user = User(screen_name=x['from_user'], profile_image_url=x['profile_image_url'])

      results.append(temp)

    # Return built list of statuses
    return results # [Status.NewFromJsonDict(x) for x in data['results']]

  def GetTrendsCurrent(self, exclude=None):
    '''Get the current top trending topics

    Args:
      exclude:
        Appends the exclude parameter as a request parameter.
        Currently only exclude=hashtags is supported. [Optional]

    Returns:
      A list with 10 entries. Each entry contains the twitter.
    '''
    parameters = {}
    if exclude:
      parameters['exclude'] = exclude
    url  = '%s/trends/current.json' % self.base_url
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)

    trends = []

    for t in data['trends']:
      for item in data['trends'][t]:
        trends.append(Trend.NewFromJsonDict(item, timestamp = t))
    return trends

  def GetTrendsWoeid(self, woeid, exclude=None):
    '''Return the top 10 trending topics for a specific WOEID, if trending
    information is available for it.

    Args:
      woeid:
        the Yahoo! Where On Earth ID for a location.
      exclude:
        Appends the exclude parameter as a request parameter.
        Currently only exclude=hashtags is supported. [Optional]

    Returns:
      A list with 10 entries. Each entry contains a Trend.
    '''
    parameters = {}
    if exclude:
      parameters['exclude'] = exclude
    url  = '%s/trends/%s.json' % (self.base_url, woeid)
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)

    trends = []
    timestamp = data[0]['as_of']

    for trend in data[0]['trends']:
        trends.append(Trend.NewFromJsonDict(trend, timestamp = timestamp))
    return trends

  def GetTrendsDaily(self, exclude=None, startdate=None):
    '''Get the current top trending topics for each hour in a given day

    Args:
      startdate:
        The start date for the report.
        Should be in the format YYYY-MM-DD. [Optional]
      exclude:
        Appends the exclude parameter as a request parameter.
        Currently only exclude=hashtags is supported. [Optional]

    Returns:
      A list with 24 entries. Each entry contains the twitter.
      Trend elements that were trending at the corresponding hour of the day.
    '''
    parameters = {}
    if exclude:
      parameters['exclude'] = exclude
    if not startdate:
      startdate = time.strftime('%Y-%m-%d', time.gmtime())
    parameters['date'] = startdate
    url  = '%s/trends/daily.json' % self.base_url
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)

    trends = []

    for i in xrange(24):
      trends.append(None)
    for t in data['trends']:
      idx = int(time.strftime('%H', time.strptime(t, '%Y-%m-%d %H:%M')))
      trends[idx] = [Trend.NewFromJsonDict(x, timestamp = t)
        for x in data['trends'][t]]
    return trends

  def GetTrendsWeekly(self, exclude=None, startdate=None):
    '''Get the top 30 trending topics for each day in a given week.

    Args:
      startdate:
        The start date for the report.
        Should be in the format YYYY-MM-DD. [Optional]
      exclude:
        Appends the exclude parameter as a request parameter.
        Currently only exclude=hashtags is supported. [Optional]
    Returns:
      A list with each entry contains the twitter.
      Trend elements of trending topics for the corrsponding day of the week
    '''
    parameters = {}
    if exclude:
      parameters['exclude'] = exclude
    if not startdate:
      startdate = time.strftime('%Y-%m-%d', time.gmtime())
    parameters['date'] = startdate
    url  = '%s/trends/weekly.json' % self.base_url
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)

    trends = []

    for i in xrange(7):
      trends.append(None)
    # use the epochs of the dates as keys for a dictionary
    times = dict([(calendar.timegm(time.strptime(t, '%Y-%m-%d')),t)
      for t in data['trends']])
    cnt = 0
    # create the resulting structure ordered by the epochs of the dates
    for e in sorted(times.keys()):
      trends[cnt] = [Trend.NewFromJsonDict(x, timestamp = times[e])
        for x in data['trends'][times[e]]]
      cnt +=1
    return trends

  def GetFriendsTimeline(self,
                         count=None,
                         page=None,
                         since_id=None,
                         retweets=None,
                         include_entities=None):
    '''Fetch the sequence of twitter.Status messages for a user's friends

    The twitter.Api instance must be authenticated if the user is private.

    Args:
      user:
        Specifies the ID or screen name of the user for whom to return
        the friends_timeline.  If not specified then the authenticated
        user set in the twitter.Api instance will be used.  [Optional]
      count:
        Specifies the number of statuses to retrieve. May not be
        greater than 100. [Optional]
      page:
         Specifies the page of results to retrieve.
         Note: there are pagination limits. [Optional]
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occured since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      retweets:
        If True, the timeline will contain native retweets. [Optional]
      include_entities:
        If True, each tweet will include a node called "entities,".
        This node offers a variety of metadata about the tweet in a
        discreet structure, including: user_mentions, urls, and
        hashtags. [Optional]

    Returns:
      A sequence of twitter.Status instances, one for each message
    '''
    if not self._oauth_consumer:
      raise TwitterError("API is not authenticated.")
    url = '%s/statuses/home_timeline.json' % self.base_url
    parameters = {}
    if count is not None:
      try:
        if int(count) > 100:
          raise TwitterError("'count' may not be greater than 100")
      except ValueError:
        raise TwitterError("'count' must be an integer")
      parameters['count'] = count
    if page is not None:
      try:
        parameters['page'] = int(page)
      except ValueError:
        raise TwitterError("'page' must be an integer")
    if since_id:
      parameters['since_id'] = since_id
    if retweets:
      parameters['include_rts'] = True
    if include_entities:
      parameters['include_entities'] = True
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetUserTimeline(self,
                      id=None,
                      user_id=None,
                      screen_name=None,
                      since_id=None,
                      max_id=None,
                      count=None,
                      page=None,
                      include_rts=None,
                      include_entities=None,
                      exclude_replies=None):
    '''Fetch the sequence of public Status messages for a single user.

    The twitter.Api instance must be authenticated if the user is private.

    Args:
      id:
        Specifies the ID or screen name of the user for whom to return
        the user_timeline. [Optional]
      user_id:
        Specfies the ID of the user for whom to return the
        user_timeline. Helpful for disambiguating when a valid user ID
        is also a valid screen name. [Optional]
      screen_name:
        Specfies the screen name of the user for whom to return the
        user_timeline. Helpful for disambiguating when a valid screen
        name is also a user ID. [Optional]
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occured since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      max_id:
        Returns only statuses with an ID less than (that is, older
        than) or equal to the specified ID. [Optional]
      count:
        Specifies the number of statuses to retrieve. May not be
        greater than 200.  [Optional]
      page:
        Specifies the page of results to retrieve.
        Note: there are pagination limits. [Optional]
      include_rts:
        If True, the timeline will contain native retweets (if they
        exist) in addition to the standard stream of tweets. [Optional]
      include_entities:
        If True, each tweet will include a node called "entities,".
        This node offers a variety of metadata about the tweet in a
        discreet structure, including: user_mentions, urls, and
        hashtags. [Optional]
       exclude_replies:
        If True, this will prevent replies from appearing in the returned
        timeline. Using exclude_replies with the count parameter will mean you
        will receive up-to count tweets - this is because the count parameter
        retrieves that many tweets before filtering out retweets and replies.
        This parameter is only supported for JSON and XML responses. [Optional]

    Returns:
      A sequence of Status instances, one for each message up to count
    '''
    parameters = {}

    if id:
      url = '%s/statuses/user_timeline/%s.json' % (self.base_url, id)
    elif user_id:
      url = '%s/statuses/user_timeline.json?user_id=%s' % (self.base_url, user_id)
    elif screen_name:
      url = ('%s/statuses/user_timeline.json?screen_name=%s' % (self.base_url,
             screen_name))
    elif not self._oauth_consumer:
      raise TwitterError("User must be specified if API is not authenticated.")
    else:
      url = '%s/statuses/user_timeline.json' % self.base_url

    if since_id:
      try:
        parameters['since_id'] = long(since_id)
      except:
        raise TwitterError("since_id must be an integer")

    if max_id:
      try:
        parameters['max_id'] = long(max_id)
      except:
        raise TwitterError("max_id must be an integer")

    if count:
      try:
        parameters['count'] = int(count)
      except:
        raise TwitterError("count must be an integer")

    if page:
      try:
        parameters['page'] = int(page)
      except:
        raise TwitterError("page must be an integer")

    if include_rts:
      parameters['include_rts'] = 1

    if include_entities:
      parameters['include_entities'] = 1

    if exclude_replies:
      parameters['exclude_replies'] = 1

    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetStatus(self, id, include_entities=None):
    '''Returns a single status message.

    The twitter.Api instance must be authenticated if the
    status message is private.

    Args:
      id:
        The numeric ID of the status you are trying to retrieve.
      include_entities:
        If True, each tweet will include a node called "entities".
        This node offers a variety of metadata about the tweet in a
        discreet structure, including: user_mentions, urls, and
        hashtags. [Optional]
    Returns:
      A twitter.Status instance representing that status message
    '''
    try:
      if id:
        long(id)
    except:
      raise TwitterError("id must be an long integer")

    parameters = {}
    if include_entities:
      parameters['include_entities'] = 1

    url  = '%s/statuses/show/%s.json' % (self.base_url, id)
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return Status.NewFromJsonDict(data)

  def DestroyStatus(self, id):
    '''Destroys the status specified by the required ID parameter.

    The twitter.Api instance must be authenticated and the
    authenticating user must be the author of the specified status.

    Args:
      id:
        The numerical ID of the status you're trying to destroy.

    Returns:
      A twitter.Status instance representing the destroyed status message
    '''
    try:
      if id:
        long(id)
    except:
      raise TwitterError("id must be an integer")
    url  = '%s/statuses/destroy/%s.json' % (self.base_url, id)
    json = self._FetchUrl(url, post_data={'id': id})
    data = self._ParseAndCheckTwitter(json)
    return Status.NewFromJsonDict(data)

  @classmethod
  def _calculate_status_length(cls, status, linksize=19):
    dummy_link_replacement = 'https://-%d-chars%s/' % (linksize, '-'*(linksize - 18))
    shortened = ' '.join([x if not (x.startswith('http://') or
                                    x.startswith('https://'))
                            else
                                dummy_link_replacement
                            for x in status.split(' ')])
    return len(shortened)

  def PostUpdate(self, status, in_reply_to_status_id=None):
    '''Post a twitter status message from the authenticated user.

    The twitter.Api instance must be authenticated.

    Args:
      status:
        The message text to be posted.
        Must be less than or equal to 140 characters.
      in_reply_to_status_id:
        The ID of an existing status that the status to be posted is
        in reply to.  This implicitly sets the in_reply_to_user_id
        attribute of the resulting status to the user ID of the
        message being replied to.  Invalid/missing status IDs will be
        ignored. [Optional]
    Returns:
      A twitter.Status instance representing the message posted.
    '''
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")

    url = '%s/statuses/update.json' % self.base_url

    if isinstance(status, unicode) or self._input_encoding is None:
      u_status = status
    else:
      u_status = unicode(status, self._input_encoding)

    if self._calculate_status_length(u_status, self._shortlink_size) > CHARACTER_LIMIT:
      raise TwitterError("Text must be less than or equal to %d characters. "
                         "Consider using PostUpdates." % CHARACTER_LIMIT)

    data = {'status': status}
    if in_reply_to_status_id:
      data['in_reply_to_status_id'] = in_reply_to_status_id
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return Status.NewFromJsonDict(data)

  def PostUpdates(self, status, continuation=None, **kwargs):
    '''Post one or more twitter status messages from the authenticated user.

    Unlike api.PostUpdate, this method will post multiple status updates
    if the message is longer than 140 characters.

    The twitter.Api instance must be authenticated.

    Args:
      status:
        The message text to be posted.
        May be longer than 140 characters.
      continuation:
        The character string, if any, to be appended to all but the
        last message.  Note that Twitter strips trailing '...' strings
        from messages.  Consider using the unicode \u2026 character
        (horizontal ellipsis) instead. [Defaults to None]
      **kwargs:
        See api.PostUpdate for a list of accepted parameters.

    Returns:
      A of list twitter.Status instance representing the messages posted.
    '''
    results = list()
    if continuation is None:
      continuation = ''
    line_length = CHARACTER_LIMIT - len(continuation)
    lines = textwrap.wrap(status, line_length)
    for line in lines[0:-1]:
      results.append(self.PostUpdate(line + continuation, **kwargs))
    results.append(self.PostUpdate(lines[-1], **kwargs))
    return results

  def GetUserRetweets(self, count=None, since_id=None, max_id=None, include_entities=False):
     '''Fetch the sequence of retweets made by a single user.

     The twitter.Api instance must be authenticated.

     Args:
       count:
         The number of status messages to retrieve. [Optional]
       since_id:
         Returns results with an ID greater than (that is, more recent
         than) the specified ID. There are limits to the number of
         Tweets which can be accessed through the API. If the limit of
         Tweets has occured since the since_id, the since_id will be
         forced to the oldest ID available. [Optional]
       max_id:
         Returns results with an ID less than (that is, older than) or
         equal to the specified ID. [Optional]
       include_entities:
         If True, each tweet will include a node called "entities,".
         This node offers a variety of metadata about the tweet in a
         discreet structure, including: user_mentions, urls, and
         hashtags. [Optional]

     Returns:
       A sequence of twitter.Status instances, one for each message up to count
     '''
     url = '%s/statuses/retweeted_by_me.json' % self.base_url
     if not self._oauth_consumer:
       raise TwitterError("The twitter.Api instance must be authenticated.")
     parameters = {}
     if count is not None:
       try:
         if int(count) > 100:
           raise TwitterError("'count' may not be greater than 100")
       except ValueError:
         raise TwitterError("'count' must be an integer")
     if count:
       parameters['count'] = count
     if since_id:
       parameters['since_id'] = since_id
     if include_entities:
       parameters['include_entities'] = True
     if max_id:
       try:
         parameters['max_id'] = long(max_id)
       except:
         raise TwitterError("max_id must be an integer")
     json = self._FetchUrl(url, parameters=parameters)
     data = self._ParseAndCheckTwitter(json)
     return [Status.NewFromJsonDict(x) for x in data]

  def GetReplies(self, since=None, since_id=None, page=None):
    '''Get a sequence of status messages representing the 20 most
    recent replies (status updates prefixed with @twitterID) to the
    authenticating user.

    Args:
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occured since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      page:
        Specifies the page of results to retrieve.
        Note: there are pagination limits. [Optional]
      since:

    Returns:
      A sequence of twitter.Status instances, one for each reply to the user.
    '''
    url = '%s/statuses/mentions_timeline.json' % self.base_url
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    parameters = {}
    if since:
      parameters['since'] = since
    if since_id:
      parameters['since_id'] = since_id
    if page:
      parameters['page'] = page
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetRetweets(self, statusid):
    '''Returns up to 100 of the first retweets of the tweet identified
    by statusid

    Args:
      statusid:
        The ID of the tweet for which retweets should be searched for

    Returns:
      A list of twitter.Status instances, which are retweets of statusid
    '''
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instsance must be authenticated.")
    url = '%s/statuses/retweets/%s.json?include_entities=true&include_rts=true' % (self.base_url, statusid)
    parameters = {}
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(s) for s in data]

  def GetFriends(self, user=None, cursor=-1):
    '''Fetch the sequence of twitter.User instances, one for each friend.

    The twitter.Api instance must be authenticated.

    Args:
      user:
        The twitter name or id of the user whose friends you are fetching.
        If not specified, defaults to the authenticated user. [Optional]

    Returns:
      A sequence of twitter.User instances, one for each friend
    '''
    if not user and not self._oauth_consumer:
      raise TwitterError("twitter.Api instance must be authenticated")
    url = '%s/friends/list.json' % self.base_url
    parameters = {}
    if user:
        parameters['screen_name'] = user
    parameters['cursor'] = cursor
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [User.NewFromJsonDict(x) for x in data['users']]

  def GetFriendIDs(self, user=None, cursor=-1):
      '''Returns a list of twitter user id's for every person
      the specified user is following.

      Args:
        user:
          The id or screen_name of the user to retrieve the id list for
          [Optional]

      Returns:
        A list of integers, one for each user id.
      '''
      if not user and not self._oauth_consumer:
          raise TwitterError("twitter.Api instance must be authenticated")
      if user:
          url = '%s/friends/ids/%s.json' % (self.base_url, user)
      else:
          url = '%s/friends/ids.json' % self.base_url
      parameters = {}
      parameters['cursor'] = cursor
      json = self._FetchUrl(url, parameters=parameters)
      data = self._ParseAndCheckTwitter(json)
      return data

  def GetFollowerIDs(self, userid=None, cursor=-1):
    '''Fetch the sequence of twitter.User instances, one for each follower

    The twitter.Api instance must be authenticated.

    Returns:
      A sequence of twitter.User instances, one for each follower
    '''
    url = '%s/followers/ids.json' % self.base_url
    parameters = {}
    parameters['cursor'] = cursor
    if userid:
      parameters['user_id'] = userid
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return data

  def GetFollowers(self, cursor=-1):
    '''Fetch the sequence of twitter.User instances, one for each follower

    The twitter.Api instance must be authenticated.

    Args:
      cursor:
        Specifies the Twitter API Cursor location to start at. [Optional]
        Note: there are pagination limits.

    Returns:
      A sequence of twitter.User instances, one for each follower
    '''
    if not self._oauth_consumer:
      raise TwitterError("twitter.Api instance must be authenticated")
    url = '%s/followers/list.json' % self.base_url
    result = []
    while True:
      parameters = { 'cursor': cursor }
      json = self._FetchUrl(url, parameters=parameters)
      data = self._ParseAndCheckTwitter(json)
      result += [User.NewFromJsonDict(x) for x in data['users']]
      if 'next_cursor' in data:
        if data['next_cursor'] == 0 or data['next_cursor'] == data['previous_cursor']:
          break
      else:
        break
    return result

  def GetFeatured(self):
    '''Fetch the sequence of twitter.User instances featured on twitter.com

    The twitter.Api instance must be authenticated.

    Returns:
      A sequence of twitter.User instances
    '''
    url  = '%s/statuses/featured.json' % self.base_url
    json = self._FetchUrl(url)
    data = self._ParseAndCheckTwitter(json)
    return [User.NewFromJsonDict(x) for x in data]

  def UsersLookup(self, user_id=None, screen_name=None, users=None):
    '''Fetch extended information for the specified users.

    Users may be specified either as lists of either user_ids,
    screen_names, or twitter.User objects. The list of users that
    are queried is the union of all specified parameters.

    The twitter.Api instance must be authenticated.

    Args:
      user_id:
        A list of user_ids to retrieve extended information.
        [Optional]
      screen_name:
        A list of screen_names to retrieve extended information.
        [Optional]
      users:
        A list of twitter.User objects to retrieve extended information.
        [Optional]

    Returns:
      A list of twitter.User objects for the requested users
    '''

    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    if not user_id and not screen_name and not users:
      raise TwitterError("Specify at least on of user_id, screen_name, or users.")
    url = '%s/users/lookup.json' % self.base_url
    parameters = {}
    uids = list()
    if user_id:
      uids.extend(user_id)
    if users:
      uids.extend([u.id for u in users])
    if len(uids):
      parameters['user_id'] = ','.join(["%s" % u for u in uids])
    if screen_name:
      parameters['screen_name'] = ','.join(screen_name)
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [User.NewFromJsonDict(u) for u in data]

  def GetUser(self, user):
    '''Returns a single user.

    The twitter.Api instance must be authenticated.

    Args:
      user: The twitter name or id of the user to retrieve.

    Returns:
      A twitter.User instance representing that user
    '''
    url  = '%s/users/show/%s.json' % (self.base_url, user)
    json = self._FetchUrl(url)
    data = self._ParseAndCheckTwitter(json)
    return User.NewFromJsonDict(data)

  def GetDirectMessages(self, since=None, since_id=None, page=None):
    '''Returns a list of the direct messages sent to the authenticating user.

    The twitter.Api instance must be authenticated.

    Args:
      since:
        Narrows the returned results to just those statuses created
        after the specified HTTP-formatted date. [Optional]
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occured since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      page:
        Specifies the page of results to retrieve.
        Note: there are pagination limits. [Optional]

    Returns:
      A sequence of twitter.DirectMessage instances
    '''
    url = '%s/direct_messages.json' % self.base_url
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    parameters = {}
    if since:
      parameters['since'] = since
    if since_id:
      parameters['since_id'] = since_id
    if page:
      parameters['page'] = page
    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [DirectMessage.NewFromJsonDict(x) for x in data]

  def PostDirectMessage(self, user, text):
    '''Post a twitter direct message from the authenticated user

    The twitter.Api instance must be authenticated.

    Args:
      user: The ID or screen name of the recipient user.
      text: The message text to be posted.  Must be less than 140 characters.

    Returns:
      A twitter.DirectMessage instance representing the message posted
    '''
    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    url  = '%s/direct_messages/new.json' % self.base_url
    data = {'text': text, 'user': user}
    json = self._FetchUrl(url, post_data=data)
    data = self._ParseAndCheckTwitter(json)
    return DirectMessage.NewFromJsonDict(data)

  def DestroyDirectMessage(self, id):
    '''Destroys the direct message specified in the required ID parameter.

    The twitter.Api instance must be authenticated, and the
    authenticating user must be the recipient of the specified direct
    message.

    Args:
      id: The id of the direct message to be destroyed

    Returns:
      A twitter.DirectMessage instance representing the message destroyed
    '''
    url  = '%s/direct_messages/destroy/%s.json' % (self.base_url, id)
    json = self._FetchUrl(url, post_data={'id': id})
    data = self._ParseAndCheckTwitter(json)
    return DirectMessage.NewFromJsonDict(data)

  def CreateFriendship(self, user):
    '''Befriends the user specified in the user parameter as the authenticating user.

    The twitter.Api instance must be authenticated.

    Args:
      The ID or screen name of the user to befriend.
    Returns:
      A twitter.User instance representing the befriended user.
    '''
    url  = '%s/friendships/create.json' % (self.base_url,)
    json = self._FetchUrl(url, post_data={'screen_name': user})
    data = self._ParseAndCheckTwitter(json)
    return User.NewFromJsonDict(data)

  def DestroyFriendship(self, user):
    '''Discontinues friendship with the user specified in the user parameter.

    The twitter.Api instance must be authenticated.

    Args:
      The ID or screen name of the user  with whom to discontinue friendship.
    Returns:
      A twitter.User instance representing the discontinued friend.
    '''
    url  = '%s/friendships/destroy.json' % (self.base_url,)
    json = self._FetchUrl(url, post_data={'screen_name': user})
    data = self._ParseAndCheckTwitter(json)
    return User.NewFromJsonDict(data)

  def CreateFavorite(self, status):
    '''Favorites the status specified in the status parameter as the authenticating user.
    Returns the favorite status when successful.

    The twitter.Api instance must be authenticated.

    Args:
      The twitter.Status instance to mark as a favorite.
    Returns:
      A twitter.Status instance representing the newly-marked favorite.
    '''
    url  = '%s/favorites/create/%s.json' % (self.base_url, status.id)
    json = self._FetchUrl(url, post_data={'id': status.id})
    data = self._ParseAndCheckTwitter(json)
    return Status.NewFromJsonDict(data)

  def DestroyFavorite(self, status):
    '''Un-favorites the status specified in the ID parameter as the authenticating user.
    Returns the un-favorited status in the requested format when successful.

    The twitter.Api instance must be authenticated.

    Args:
      The twitter.Status to unmark as a favorite.
    Returns:
      A twitter.Status instance representing the newly-unmarked favorite.
    '''
    url  = '%s/favorites/destroy/%s.json' % (self.base_url, status.id)
    json = self._FetchUrl(url, post_data={'id': status.id})
    data = self._ParseAndCheckTwitter(json)
    return Status.NewFromJsonDict(data)

  def GetFavorites(self,
                   user=None,
                   page=None):
    '''Return a list of Status objects representing favorited tweets.
    By default, returns the (up to) 20 most recent tweets for the
    authenticated user.

    Args:
      user:
        The twitter name or id of the user whose favorites you are fetching.
        If not specified, defaults to the authenticated user. [Optional]
      page:
        Specifies the page of results to retrieve.
        Note: there are pagination limits. [Optional]
    '''
    parameters = {}

    if page:
      parameters['page'] = page

    if user:
      url = '%s/favorites/%s.json' % (self.base_url, user)
    elif not user and not self._oauth_consumer:
      raise TwitterError("User must be specified if API is not authenticated.")
    else:
      url = '%s/favorites.json' % self.base_url

    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetMentions(self,
                  since_id=None,
                  max_id=None,
                  page=None):
    '''Returns the 20 most recent mentions (status containing @twitterID)
    for the authenticating user.

    Args:
      since_id:
        Returns results with an ID greater than (that is, more recent
        than) the specified ID. There are limits to the number of
        Tweets which can be accessed through the API. If the limit of
        Tweets has occured since the since_id, the since_id will be
        forced to the oldest ID available. [Optional]
      max_id:
        Returns only statuses with an ID less than
        (that is, older than) the specified ID.  [Optional]
      page:
        Specifies the page of results to retrieve.
        Note: there are pagination limits. [Optional]

    Returns:
      A sequence of twitter.Status instances, one for each mention of the user.
    '''

    url = '%s/statuses/mentions.json' % self.base_url

    if not self._oauth_consumer:
      raise TwitterError("The twitter.Api instance must be authenticated.")

    parameters = {}

    if since_id:
      parameters['since_id'] = since_id
    if max_id:
      try:
        parameters['max_id'] = long(max_id)
      except:
        raise TwitterError("max_id must be an integer")
    if page:
      parameters['page'] = page

    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [Status.NewFromJsonDict(x) for x in data]

  def CreateList(self, user, name, mode=None, description=None):
    '''Creates a new list with the give name

    The twitter.Api instance must be authenticated.

    Args:
      user:
        Twitter name to create the list for
      name:
        New name for the list
      mode:
        'public' or 'private'.
        Defaults to 'public'. [Optional]
      description:
        Description of the list. [Optional]

    Returns:
      A twitter.List instance representing the new list
    '''
    url = '%s/%s/lists.json' % (self.base_url, user)
    parameters = {'name': name}
    if mode is not None:
      parameters['mode'] = mode
    if description is not None:
      parameters['description'] = description
    json = self._FetchUrl(url, post_data=parameters)
    data = self._ParseAndCheckTwitter(json)
    return List.NewFromJsonDict(data)

  def DestroyList(self, user, id):
    '''Destroys the list from the given user

    The twitter.Api instance must be authenticated.

    Args:
      user:
        The user to remove the list from.
      id:
        The slug or id of the list to remove.
    Returns:
      A twitter.List instance representing the removed list.
    '''
    url  = '%s/%s/lists/%s.json' % (self.base_url, user, id)
    json = self._FetchUrl(url, post_data={'_method': 'DELETE'})
    data = self._ParseAndCheckTwitter(json)
    return List.NewFromJsonDict(data)

  def CreateSubscription(self, owner, list):
    '''Creates a subscription to a list by the authenticated user

    The twitter.Api instance must be authenticated.

    Args:
      owner:
        User name or id of the owner of the list being subscribed to.
      list:
        The slug or list id to subscribe the user to

    Returns:
      A twitter.List instance representing the list subscribed to
    '''
    url  = '%s/%s/%s/subscribers.json' % (self.base_url, owner, list)
    json = self._FetchUrl(url, post_data={'list_id': list})
    data = self._ParseAndCheckTwitter(json)
    return List.NewFromJsonDict(data)

  def DestroySubscription(self, owner, list):
    '''Destroys the subscription to a list for the authenticated user

    The twitter.Api instance must be authenticated.

    Args:
      owner:
        The user id or screen name of the user that owns the
        list that is to be unsubscribed from
      list:
        The slug or list id of the list to unsubscribe from

    Returns:
      A twitter.List instance representing the removed list.
    '''
    url  = '%s/%s/%s/subscribers.json' % (self.base_url, owner, list)
    json = self._FetchUrl(url, post_data={'_method': 'DELETE', 'list_id': list})
    data = self._ParseAndCheckTwitter(json)
    return List.NewFromJsonDict(data)

  def GetSubscriptions(self, user, cursor=-1):
    '''Fetch the sequence of Lists that the given user is subscribed to

    The twitter.Api instance must be authenticated.

    Args:
      user:
        The twitter name or id of the user
      cursor:
        "page" value that Twitter will use to start building the
        list sequence from.  -1 to start at the beginning.
        Twitter will return in the result the values for next_cursor
        and previous_cursor. [Optional]

    Returns:
      A sequence of twitter.List instances, one for each list
    '''
    if not self._oauth_consumer:
      raise TwitterError("twitter.Api instance must be authenticated")

    url = '%s/%s/lists/subscriptions.json' % (self.base_url, user)
    parameters = {}
    parameters['cursor'] = cursor

    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [List.NewFromJsonDict(x) for x in data['lists']]

  def GetLists(self, user, cursor=-1):
    '''Fetch the sequence of lists for a user.

    The twitter.Api instance must be authenticated.

    Args:
      user:
        The twitter name or id of the user whose friends you are fetching.
        If the passed in user is the same as the authenticated user
        then you will also receive private list data.
      cursor:
        "page" value that Twitter will use to start building the
        list sequence from.  -1 to start at the beginning.
        Twitter will return in the result the values for next_cursor
        and previous_cursor. [Optional]

    Returns:
      A sequence of twitter.List instances, one for each list
    '''
    if not self._oauth_consumer:
      raise TwitterError("twitter.Api instance must be authenticated")

    url = '%s/%s/lists.json' % (self.base_url, user)
    parameters = {}
    parameters['cursor'] = cursor

    json = self._FetchUrl(url, parameters=parameters)
    data = self._ParseAndCheckTwitter(json)
    return [List.NewFromJsonDict(x) for x in data['lists']]

  def GetUserByEmail(self, email):
    '''Returns a single user by email address.

    Args:
      email:
        The email of the user to retrieve.

    Returns:
      A twitter.User instance representing that user
    '''
    url = '%s/users/show.json?email=%s' % (self.base_url, email)
    json = self._FetchUrl(url)
    data = self._ParseAndCheckTwitter(json)
    return User.NewFromJsonDict(data)

  def VerifyCredentials(self):
    '''Returns a twitter.User instance if the authenticating user is valid.

    Returns:
      A twitter.User instance representing that user if the
      credentials are valid, None otherwise.
    '''
    if not self._oauth_consumer:
      raise TwitterError("Api instance must first be given user credentials.")
    url = '%s/account/verify_credentials.json' % self.base_url
    try:
      json = self._FetchUrl(url, no_cache=True)
    except urllib2.HTTPError, http_error:
      if http_error.code == httplib.UNAUTHORIZED:
        return None
      else:
        raise http_error
    data = self._ParseAndCheckTwitter(json)
    return User.NewFromJsonDict(data)

  def SetCache(self, cache):
    '''Override the default cache.  Set to None to prevent caching.

    Args:
      cache:
        An instance that supports the same API as the twitter._FileCache
    '''
    if cache == DEFAULT_CACHE:
      self._cache = _FileCache()
    else:
      self._cache = cache

  def SetUrllib(self, urllib):
    '''Override the default urllib implementation.

    Args:
      urllib:
        An instance that supports the same API as the urllib2 module
    '''
    self._urllib = urllib

  def SetCacheTimeout(self, cache_timeout):
    '''Override the default cache timeout.

    Args:
      cache_timeout:
        Time, in seconds, that responses should be reused.
    '''
    self._cache_timeout = cache_timeout

  def SetUserAgent(self, user_agent):
    '''Override the default user agent

    Args:
      user_agent:
        A string that should be send to the server as the User-agent
    '''
    self._request_headers['User-Agent'] = user_agent

  def SetXTwitterHeaders(self, client, url, version):
    '''Set the X-Twitter HTTP headers that will be sent to the server.

    Args:
      client:
         The client name as a string.  Will be sent to the server as
         the 'X-Twitter-Client' header.
      url:
         The URL of the meta.xml as a string.  Will be sent to the server
         as the 'X-Twitter-Client-URL' header.
      version:
         The client version as a string.  Will be sent to the server
         as the 'X-Twitter-Client-Version' header.
    '''
    self._request_headers['X-Twitter-Client'] = client
    self._request_headers['X-Twitter-Client-URL'] = url
    self._request_headers['X-Twitter-Client-Version'] = version

  def SetSource(self, source):
    '''Suggest the "from source" value to be displayed on the Twitter web site.

    The value of the 'source' parameter must be first recognized by
    the Twitter server.  New source values are authorized on a case by
    case basis by the Twitter development team.

    Args:
      source:
        The source name as a string.  Will be sent to the server as
        the 'source' parameter.
    '''
    self._default_params['source'] = source

  def GetRateLimitStatus(self):
    '''Fetch the rate limit status for the currently authorized user.

    Returns:
      A dictionary containing the time the limit will reset (reset_time),
      the number of remaining hits allowed before the reset (remaining_hits),
      the number of hits allowed in a 60-minute period (hourly_limit), and
      the time of the reset in seconds since The Epoch (reset_time_in_seconds).
    '''
    url  = '%s/account/rate_limit_status.json' % self.base_url
    json = self._FetchUrl(url, no_cache=True)
    data = self._ParseAndCheckTwitter(json)
    return data

  def MaximumHitFrequency(self):
    '''Determines the minimum number of seconds that a program must wait
    before hitting the server again without exceeding the rate_limit
    imposed for the currently authenticated user.

    Returns:
      The minimum second interval that a program must use so as to not
      exceed the rate_limit imposed for the user.
    '''
    rate_status = self.GetRateLimitStatus()
    reset_time  = rate_status.get('reset_time', None)
    limit       = rate_status.get('remaining_hits', None)

    if reset_time:
      # put the reset time into a datetime object
      reset = datetime.datetime(*rfc822.parsedate(reset_time)[:7])

      # find the difference in time between now and the reset time + 1 hour
      delta = reset + datetime.timedelta(hours=1) - datetime.datetime.utcnow()

      if not limit:
          return int(delta.seconds)

      # determine the minimum number of seconds allowed as a regular interval
      max_frequency = int(delta.seconds / limit) + 1

      # return the number of seconds
      return max_frequency

    return 60

  def _BuildUrl(self, url, path_elements=None, extra_params=None):
    # Break url into consituent parts
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)

    # Add any additional path elements to the path
    if path_elements:
      # Filter out the path elements that have a value of None
      p = [i for i in path_elements if i]
      if not path.endswith('/'):
        path += '/'
      path += '/'.join(p)

    # Add any additional query parameters to the query string
    if extra_params and len(extra_params) > 0:
      extra_query = self._EncodeParameters(extra_params)
      # Add it to the existing query
      if query:
        query += '&' + extra_query
      else:
        query = extra_query

    # Return the rebuilt URL
    return urlparse.urlunparse((scheme, netloc, path, params, query, fragment))

  def _InitializeRequestHeaders(self, request_headers):
    if request_headers:
      self._request_headers = request_headers
    else:
      self._request_headers = {}

  def _InitializeUserAgent(self):
    user_agent = 'Python-urllib/%s (python-twitter/%s)' % \
                 (self._urllib.__version__, __version__)
    self.SetUserAgent(user_agent)

  def _InitializeDefaultParameters(self):
    self._default_params = {}

  def _DecompressGzippedResponse(self, response):
    raw_data = response.read()
    if response.headers.get('content-encoding', None) == 'gzip':
      url_data = gzip.GzipFile(fileobj=StringIO.StringIO(raw_data)).read()
    else:
      url_data = raw_data
    return url_data

  def _Encode(self, s):
    if self._input_encoding:
      return unicode(s, self._input_encoding).encode('utf-8')
    else:
      return unicode(s).encode('utf-8')

  def _EncodeParameters(self, parameters):
    '''Return a string in key=value&key=value form

    Values of None are not included in the output string.

    Args:
      parameters:
        A dict of (key, value) tuples, where value is encoded as
        specified by self._encoding

    Returns:
      A URL-encoded string in "key=value&key=value" form
    '''
    if parameters is None:
      return None
    else:
      return urllib.urlencode(dict([(k, self._Encode(v)) for k, v in parameters.items() if v is not None]))

  def _EncodePostData(self, post_data):
    '''Return a string in key=value&key=value form

    Values are assumed to be encoded in the format specified by self._encoding,
    and are subsequently URL encoded.

    Args:
      post_data:
        A dict of (key, value) tuples, where value is encoded as
        specified by self._encoding

    Returns:
      A URL-encoded string in "key=value&key=value" form
    '''
    if post_data is None:
      return None
    else:
      return urllib.urlencode(dict([(k, self._Encode(v)) for k, v in post_data.items()]))

  def _ParseAndCheckTwitter(self, json):
    """Try and parse the JSON returned from Twitter and return
    an empty dictionary if there is any error. This is a purely
    defensive check because during some Twitter network outages
    it will return an HTML failwhale page."""
    try:
      data = simplejson.loads(json)
      self._CheckForTwitterError(data)
    except ValueError:
      if "<title>Twitter / Over capacity</title>" in json:
        raise TwitterError("Capacity Error")
      if "<title>Twitter / Error</title>" in json:
        raise TwitterError("Technical Error")
      raise TwitterError("json decoding")

    return data

  def _CheckForTwitterError(self, data):
    """Raises a TwitterError if twitter returns an error message.

    Args:
      data:
        A python dict created from the Twitter json response

    Raises:
      TwitterError wrapping the twitter error message if one exists.
    """
    # Twitter errors are relatively unlikely, so it is faster
    # to check first, rather than try and catch the exception
    if 'error' in data:
      raise TwitterError(data['error'])
    if 'errors' in data:
      raise TwitterError(data['errors'])

  def _FetchUrl(self,
                url,
                post_data=None,
                parameters=None,
                no_cache=None,
                use_gzip_compression=None):
    '''Fetch a URL, optionally caching for a specified time.

    Args:
      url:
        The URL to retrieve
      post_data:
        A dict of (str, unicode) key/value pairs.
        If set, POST will be used.
      parameters:
        A dict whose key/value pairs should encoded and added
        to the query string. [Optional]
      no_cache:
        If true, overrides the cache on the current request
      use_gzip_compression:
        If True, tells the server to gzip-compress the response.
        It does not apply to POST requests.
        Defaults to None, which will get the value to use from
        the instance variable self._use_gzip [Optional]

    Returns:
      A string containing the body of the response.
    '''
    # Build the extra parameters dict
    extra_params = {}
    if self._default_params:
      extra_params.update(self._default_params)
    if parameters:
      extra_params.update(parameters)

    if post_data:
      http_method = "POST"
    else:
      http_method = "GET"

    if self._debugHTTP:
      _debug = 1
    else:
      _debug = 0

    http_handler  = self._urllib.HTTPHandler(debuglevel=_debug)
    https_handler = self._urllib.HTTPSHandler(debuglevel=_debug)

    opener = self._urllib.OpenerDirector()
    opener.add_handler(http_handler)
    opener.add_handler(https_handler)

    if use_gzip_compression is None:
      use_gzip = self._use_gzip
    else:
      use_gzip = use_gzip_compression

    # Set up compression
    if use_gzip and not post_data:
      opener.addheaders.append(('Accept-Encoding', 'gzip'))

    if self._oauth_consumer is not None:
      if post_data and http_method == "POST":
        parameters = post_data.copy()

      req = oauth.Request.from_consumer_and_token(self._oauth_consumer,
                                                  token=self._oauth_token,
                                                  http_method=http_method,
                                                  http_url=url, parameters=parameters)

      req.sign_request(self._signature_method_hmac_sha1, self._oauth_consumer, self._oauth_token)

      headers = req.to_header()

      if http_method == "POST":
        encoded_post_data = req.to_postdata()
      else:
        encoded_post_data = None
        url = req.to_url()
    else:
      url = self._BuildUrl(url, extra_params=extra_params)
      encoded_post_data = self._EncodePostData(post_data)

    # Open and return the URL immediately if we're not going to cache
    if encoded_post_data or no_cache or not self._cache or not self._cache_timeout:
      response = opener.open(url, encoded_post_data)
      url_data = self._DecompressGzippedResponse(response)
      opener.close()
    else:
      # Unique keys are a combination of the url and the oAuth Consumer Key
      if self._consumer_key:
        key = self._consumer_key + ':' + url
      else:
        key = url

      # See if it has been cached before
      last_cached = self._cache.GetCachedTime(key)

      # If the cached version is outdated then fetch another and store it
      if not last_cached or time.time() >= last_cached + self._cache_timeout:
        try:
          response = opener.open(url, encoded_post_data)
          url_data = self._DecompressGzippedResponse(response)
          self._cache.Set(key, url_data)
        except urllib2.HTTPError, e:
          print e
        opener.close()
      else:
        url_data = self._cache.Get(key)

    # Always return the latest version
    return url_data

class _FileCacheError(Exception):
  '''Base exception class for FileCache related errors'''

class _FileCache(object):

  DEPTH = 3

  def __init__(self,root_directory=None):
    self._InitializeRootDirectory(root_directory)

  def Get(self,key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return open(path).read()
    else:
      return None

  def Set(self,key,data):
    path = self._GetPath(key)
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
      os.makedirs(directory)
    if not os.path.isdir(directory):
      raise _FileCacheError('%s exists but is not a directory' % directory)
    temp_fd, temp_path = tempfile.mkstemp()
    temp_fp = os.fdopen(temp_fd, 'w')
    temp_fp.write(data)
    temp_fp.close()
    if not path.startswith(self._root_directory):
      raise _FileCacheError('%s does not appear to live under %s' %
                            (path, self._root_directory))
    if os.path.exists(path):
      os.remove(path)
    os.rename(temp_path, path)

  def Remove(self,key):
    path = self._GetPath(key)
    if not path.startswith(self._root_directory):
      raise _FileCacheError('%s does not appear to live under %s' %
                            (path, self._root_directory ))
    if os.path.exists(path):
      os.remove(path)

  def GetCachedTime(self,key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return os.path.getmtime(path)
    else:
      return None

  def _GetUsername(self):
    '''Attempt to find the username in a cross-platform fashion.'''
    try:
      return os.getenv('USER') or \
             os.getenv('LOGNAME') or \
             os.getenv('USERNAME') or \
             os.getlogin() or \
             'nobody'
    except (AttributeError, IOError, OSError), e:
      return 'nobody'

  def _GetTmpCachePath(self):
    username = self._GetUsername()
    cache_directory = 'python.cache_' + username
    return os.path.join(tempfile.gettempdir(), cache_directory)

  def _InitializeRootDirectory(self, root_directory):
    if not root_directory:
      root_directory = self._GetTmpCachePath()
    root_directory = os.path.abspath(root_directory)
    if not os.path.exists(root_directory):
      os.mkdir(root_directory)
    if not os.path.isdir(root_directory):
      raise _FileCacheError('%s exists but is not a directory' %
                            root_directory)
    self._root_directory = root_directory

  def _GetPath(self,key):
    try:
        hashed_key = md5(key).hexdigest()
    except TypeError:
        hashed_key = md5.new(key).hexdigest()

    return os.path.join(self._root_directory,
                        self._GetPrefix(hashed_key),
                        hashed_key)

  def _GetPrefix(self,hashed_key):
    return os.path.sep.join(hashed_key[0:_FileCache.DEPTH])

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('TwitterStream')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('TwitterStream', True)


TwitterStream = conf.registerPlugin('TwitterStream')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(TwitterStream, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
import supybot.schedule as schedule
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
try:
    import twitter
except ImportError:
    raise callbacks.Error('You have to install python-twitter.')
except Exception as e:
    raise callbacks.Error('Unknown exception importing twitter: %r' % e)
try:
    import requests
except ImportError:
    raise callbacks.Error('You have to install python-requests.')
except Exception as e:
    raise callbacks.Error('Unknown exception importing requests: %r' % e)


_ = PluginInternationalization('TwitterStream')

@internationalizeDocstring
class TwitterStream(callbacks.Plugin):
    """Add the help for "@plugin help TwitterStream" here
    This should describe *how* to use this plugin."""
    threaded = True

    _users = {}
    _searches = {}

    def user(self, irc, msg, arg, username):
        """<username>

        Start usering a Twitter account."""
        name = 'twitterstream_user_'+username
        api = twitter.Api()
        def fetch(send=True):
            timeline = api.GetUserTimeline(username,
                    since_id=self._users[name])
            for tweet in timeline:
                self._users[name] = max(self._users[name], tweet.id)
            format_ = '@%(user)s> %(msg)s'
            replies = [format_ % {'longid': x.id,
                                  'user': x.user.screen_name,
                                  'msg': x.text
                                 } for x in timeline]
            replies = [x.replace("&lt;", "<").replace("&gt;", ">")
                    .replace("&amp;", "&") for x in replies]
            if send:
                for reply in replies:
                    irc.reply(reply, prefixNick=False)
        self._users[name] = 0
        fetch(False)
        schedule.addPeriodicEvent(fetch, 60, name)
        irc.replySuccess()
    user = wrap(user, ['text'])

    def search(self, irc, msg, arg, search):
        """<terms>

        Start streaming a Twitter search."""
        name = 'twitterstream_search_'+search
        api = twitter.Api()
        def fetch(send=True):
            url = 'http://search.twitter.com/search.json?q=%s&since_id=%i' % \
                    (search, self._searches[name])
            timeline = requests.get(url).json['results']
            for tweet in timeline:
                self._searches[name] = max(self._searches[name], tweet['id'])
            format_ = '@%(user)s> %(msg)s'
            replies = [format_ % {'longid': x['id'],
                                  'user': x['from_user'],
                                  'msg': x['text']
                                 } for x in timeline
                                 if not x['text'].startswith('RT ')]
            replies = [x.replace("&lt;", "<").replace("&gt;", ">")
                    .replace("&amp;", "&") for x in replies]
            if send:
                for reply in replies:
                    irc.reply(reply, prefixNick=False)
        self._searches[name] = 0
        fetch(False)
        schedule.addPeriodicEvent(fetch, 60, name)
        irc.replySuccess()
    search = wrap(search, ['text'])

    def die(self):
        for user in self._users:
            schedule.removeEvent(user)
        for search in self._searches:
            schedule.removeEvent(search)
        self._streams = []
        self._searches = []


Class = TwitterStream


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class TwitterStreamTestCase(PluginTestCase):
    plugins = ('TwitterStream',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('TWSS')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('TWSS', True)


TWSS = conf.registerPlugin('TWSS')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(TWSS, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))

conf.registerChannelValue(TWSS, 'enable',
    registry.Boolean(False, _("""Determines whether or not the plugin will
    be enabled.""")))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import threading

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('TWSS')

class Jenny:
    _msg = None
    def say(self, msg):
        self._msg = msg

@internationalizeDocstring
class TWSS(callbacks.Plugin):
    """Add the help for "@plugin help TWSS" here
    This should describe *how* to use this plugin."""

    def __init__(self, irc):
        super(TWSS, self).__init__(irc)
        self._twss = None
        threading.Thread(target=self._import_twss).start()

    def _import_twss(self):
        import twss
        self._twss = twss

    def doPrivmsg(self, irc, msg):
        if self.registryValue('enable', msg.args[0]) and self._twss:
            jenni = Jenny()
            self._twss.say_it(jenni, msg.args[1])
            if jenni._msg:
                irc.reply(jenni._msg)


Class = TWSS


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class TWSSTestCase(PluginTestCase):
    plugins = ('TWSS',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = twss
#!/usr/bin/env python
"""
twss.py - Jenni's That's What She Said Module
Copyright 2011 - Joel Friedly and Matt Meinwald
Licensed under the Eiffel Forum License 2.

More info:
 * Jenni: https://github.com/myano/jenni/
 * Phenny: http://inamidst.com/phenny/

This module detects common phrases that many times can be responded with
"That's what she said."

It also allows users to add new "that's what she said" jokes to it's library
by following any appropriate statement with ".twss".
"""

import supybot.conf as conf
import urllib2
import re
import os
import sys

path = conf.supybot.directories.conf.dirize

last = "DEBUG_ME" # if you see this in the terminal, something broke.

if not os.path.exists(path('TWSS.txt')):
    with open(path('TWSS.txt'), "w") as f:
        with open(os.path.join(os.path.dirname(__file__), 'twss.txt'), 'r') as f2:
            f.write(f2.read())


def say_it(jenni, input):
    global last
    user_quotes = None
    with open(path('TWSS.txt')) as f:
        scraped_quotes = frozenset([line.rstrip() for line in f])
    if os.path.exists(path('TWSS.txt')):
        with open(path('TWSS.txt')) as f2:
            user_quotes = frozenset([line.rstrip() for line in f2])
    quotes = scraped_quotes.union(user_quotes) if user_quotes else scraped_quotes
    formatted = input.lower()
    if re.sub("[^\w\s]", "", formatted) in quotes:
        jenni.say("That's what she said.")
    last = re.sub("[^\w\s]", "", formatted)
say_it.rule = r"(.*)"
say_it.priority = "low"

def add_twss(jenni, input):
    print last
    with open(path('TWSS.txt'), "a") as f:
        f.write(re.sub(r"[^\w\s]", "", last.lower()) + "\n")
        f.close()
    jenni.say("That's what she said.")
add_twss.commands = ["twss"]
add_twss.priority = "low"
add_twss.threading = False

if __name__ == '__main__':
    print __doc__.strip()

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Untiny')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Untiny', True)


Untiny = conf.registerPlugin('Untiny')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Untiny, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))
conf.registerGlobalValue(Untiny, 'service',
    registry.String('http://untiny.me/api/1.0/extract?url=%s&format=json',
    _('The untiny service to be used. %s will be replace by the tiny URL.')))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import json

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
from supybot.utils.web import getUrl
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Untiny')

@internationalizeDocstring
class Untiny(callbacks.Plugin):
    """Add the help for "@plugin help Untiny" here
    This should describe *how* to use this plugin."""

    def _untiny(self, irc, url):
        data = json.loads(getUrl(self.registryValue('service') % url).decode())
        if 'org_url' in data:
            if irc:
                irc.reply(data['org_url'])
            else:
                return data['org_url'] # Used by other plugins
        elif 'error' in data:
            num, msg = data['error']
            messages = {
                    '0': _('Invalid URL'),
                    '1': _('Unsupported tinyurl service'),
                    '2': _('Connection to tinyurl service failed'),
                    '3': _('Unable to get the original URL'),
                    }
            if irc:
                irc.error(messages[num])
            else:
                return url

    @internationalizeDocstring
    def untiny(self, irc, msg, args, url):
        """<url>

        Return the whole URL for a tiny URL."""
        self._untiny(irc, url)
    untiny = wrap(untiny, ['text'])


Class = Untiny


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2012, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class UntinyTestCase(PluginTestCase):
    plugins = ('Untiny',)

    def testTinyurl(self):
        self.assertResponse('untiny http://tinyurl.com/gribble',
                    'http://www.gribble.org')
        self.assertResponse('untiny TinyURL.com/gribble',
                'http://www.gribble.org')

    def testGoogl(self):
        self.assertResponse('untiny http://goo.gl/LmaUr',
                'https://github.com/ProgVal/Limnoria')

    def testError(self):
        self.assertResponse('untiny epogj', 'Error: Invalid URL')
        self.assertResponse('untiny http://example.org/',
                'Error: Unsupported tinyurl service')
        self.assertResponse('untiny http://goo.gl/GrgigGj',
                'Error: Unable to get the original URL')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Variables')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Variables', True)


Variables = conf.registerPlugin('Variables')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Variables, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import os

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

try:
    import sqlite3
except ImportError:
    from pysqlite2 import dbapi2 as sqlite3 # for python2.4

_ = PluginInternationalization('Variables')

class VariableDoesNotExist(Exception):
    pass

@internationalizeDocstring
class Variables(callbacks.Plugin):
    """Add the help for "@plugin help Variables" here
    This should describe *how* to use this plugin."""

    def __init__(self, irc):
        callbacks.Plugin.__init__(self, irc)
        self._filename = os.path.join(conf.supybot.directories.data(),
                'Variables.db')
        self._load()

    def _load(self):
        if hasattr(self, '_connection'):
            self._connection.close()
        createDatabase = not os.path.exists(self._filename)
        self._connection = sqlite3.connect(self._filename)
        self._connection.text_factory = str
        if createDatabase:
            self._makeDb()

    def _makeDb(self):
        cursor = self._connection.cursor()
        cursor.execute("""CREATE TABLE variables (
                          domainType TEXT,
                          domainName TEXT,
                          variableName TEXT,
                          value TEXT,
                          sticky BOOLEAN
                          )""")
        self._connection.commit()

    def _getDomain(self, irc, msg, opts):
        opts = dict(opts)
        if 'domain' not in opts:
            domainType = 'global'
        else:
            domainType = opts['domain']
        if 'name' not in opts:
            if domainType == 'global':
                domainName = 'default'
            elif domainType == 'channel':
                domainName = msg.args[0]
            elif domainType == 'network':
                domainName = irc.network
        else:
            domainName = opts['name']
        return domainType, domainName

    def _getVariable(self, domainType, domainName, variableName):
        cursor = self._connection.cursor()
        cursor.execute("""SELECT value FROM variables WHERE
                          domainType=? AND domainName=? AND variableName=?""",
                          (domainType, domainName, variableName))
        row = cursor.fetchone()
        if row is None:
            raise VariableDoesNotExist()
        else:
            return row[0]

    @internationalizeDocstring
    def set(self, irc, msg, args, opts, name, value):
        """[--domain <domaintype>] [--name <domainname>] <name> <value>

        Sets a variable called <name> to be <value>, in the domain matching
        the <domaintype> and the <domainname>.
        If <domainname> is not given, it defaults to the current domain
        matching the <domaintype>.
        If <domaintype> is not given, it defaults to the global domain.
        Valid domain types are 'global', 'channel', and 'network'.
        Note that channel domains are channel-specific, but are cross-network.
        """
        domainType, domainName = self._getDomain(irc, msg, opts)
        cursor = self._connection.cursor()
        try:
            self._getVariable(domainType, domainName, name)
            cursor.execute("""DELETE FROM variables WHERE
                              domainType=? AND domainName=? AND
                              variableName=?""",
                          (domainType, domainName, name))
        except VariableDoesNotExist:
            pass
        cursor.execute("""INSERT INTO variables VALUES (?,?,?,?,?)""",
                          (domainType, domainName, name, value, True))
        self._connection.commit()
        irc.replySuccess()
    set = wrap(set, [getopts({'domain': ('literal', ('global', 'network', 'channel')),
                              'name': 'something'}),
                     'something', 'text'])

    @internationalizeDocstring
    def get(self, irc, msg, args, opts, name):
        """[--domain <domaintype>] [--name <domainname>] <name>

        Get the value of the variable called <name>, in the domain matching
        the <domaintype> and the <domainname>.
        If <domainname> is not given, it defaults to the current domain
        matching the <domaintype>.
        If <domaintype> is not given, it defaults to the global domain.
        Valid domain types are 'global', 'channel', and 'network'.
        Note that channel domains are channel-specific, but are cross-network.
        """
        domainType, domainName = self._getDomain(irc, msg, opts)
        try:
            irc.reply(self._getVariable(domainType, domainName, name))
        except VariableDoesNotExist:
            irc.error(_('Variable does not exist.'))

    get = wrap(get, [getopts({'domain': ('literal', ('global', 'network', 'channel')),
                              'name': 'something'}),
                     'something'])


Class = Variables


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class VariablesTestCase(ChannelPluginTestCase):
    plugins = ('Variables',)

    def testSetGet(self):
        self.assertError('get foo')
        self.assertNotError('set foo bar')
        self.assertResponse('get foo', 'bar')
        self.assertNotError('set foo baz')
        self.assertResponse('get foo', 'baz')

    def testChannel(self):
        self.assertError('get --domain channel foo')
        self.assertError('get --domain channel --name #test foo')
        self.assertError('get --domain channel --name #egg foo')
        self.assertError('get foo')
        self.assertNotError('set --domain channel foo bar')
        self.assertResponse('get --domain channel foo', 'bar')
        self.assertResponse('get --domain channel --name #test foo', 'bar')
        self.assertError('get --domain channel --name #egg foo')
        self.assertError('get foo')

    def testNetwork(self):
        self.assertError('get --domain network foo')
        self.assertError('get --domain network --name test foo')
        self.assertError('get --domain network --name foonet foo')
        self.assertError('get foo')
        self.assertNotError('set --domain network foo bar')
        self.assertResponse('get --domain network foo', 'bar')
        self.assertResponse('get --domain network --name test foo', 'bar')
        self.assertError('get --domain network --name foonet foo')
        self.assertError('get foo')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('WebDoc')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('WebDoc', True)


WebDoc = conf.registerPlugin('WebDoc')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerglobalvalue(webdoc, 'someconfigvariablename',
#     registry.boolean(false, _("""help for someconfigvariablename.""")))
conf.registerGlobalValue(WebDoc, 'withFullName',
    registry.Boolean(False, _("""Determines whether the name of the command
    will be displayed in the same cell as the doc.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import cgi
import sys
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.httpserver as httpserver
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('WebDoc')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

PAGE_SKELETON = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <title>Supybot web documentation</title>
        <link rel="stylesheet" media="screen" type="text/css" title="Design" href="/default.css" />
    </head>
    <body class="%s">
%s
    </body>
</html>
"""

DEFAULT_TEMPLATES = {
        'webdoc/index.html': PAGE_SKELETON % ('purelisting', """\
<h1>Loaded plugins</h1>

<ul class="pluginslist">
%(plugins)s
</ul>"""),
        'webdoc/plugin.html': PAGE_SKELETON % ('puretable', """\
<a href="../">Plugin list</a>

<h1>%(plugin)s</h1>

<p>%(description)s</p>

<table>
    <tr>
        <th>Command</th>
        <th>Help</th>
    </tr>
%(table)s
</table>"""),
        }

httpserver.set_default_templates(DEFAULT_TEMPLATES)

class WebDocServerCallback(httpserver.SupyHTTPServerCallback):
    def __init__(self, plugin, irc):
        super(WebDocServerCallback, self).__init__()
        self._irc = irc
        self._plugin = plugin
    name = 'WebDoc'
    def doGet(self, handler, path):
        splitted_path = path.split('/')
        if len(splitted_path) == 2:
            names = filter(lambda x: conf.supybot.plugins.get(x).public(),
                    map(lambda cb:cb.name(), self._irc.callbacks))
            plugins = ''.join(map(lambda x:'<li><a href="%s/">%s</a></li>'%(x,x),
                sorted(names)))
            response = 200
            output = httpserver.get_template('webdoc/index.html') % {
                    'plugins': plugins,
                    }
        elif len(splitted_path) == 3:
            name = splitted_path[1]
            cbs = dict(map(lambda cb:(cb.name(), cb),
                self._irc.callbacks))
            if name not in cbs or \
                    not conf.supybot.plugins.get(name).public():
                response = 404
                output = httpserver.get_template('generic/error.html') % \
                    {'title': 'PluginsDoc',
                     'error': 'Requested plugin is not found. Sorry.'}
            else:
                response = 200
                callback = cbs[name]
                commands = callback.listCommands()
                description = callback.__doc__
                if not description or description.startswith('Add the help for'):
                    description = ''
                if commands:
                    commands.sort()
                def formatter(command):
                    command = list(map(callbacks.canonicalName,
                        command.split(' ')))
                    doc = callback.getCommandMethod(command).__doc__
                    if not doc:
                        return '<tr><td>%s</td><td> </td></tr>' % \
                                ' '.join(command)
                    doclines = doc.splitlines()
                    if self._plugin.registryValue('withFullName'):
                        s = '%s %s %s' % (name, ' '.join(command), doclines.pop(0))
                    else:
                        s = doclines.pop(0)
                    s = cgi.escape(s)
                    if doclines:
                        help_ = cgi.escape('\n'.join(doclines))
                        s = '<strong>%s</strong><br />%s' % \
                                (ircutils.bold(s), help_)
                    return '<tr><td>%s</td><td>%s</td></tr>' % \
                            (' '.join(command), s)

                table = ''.join(map(formatter, commands))
                output = httpserver.get_template('webdoc/plugin.html') % {
                        'plugin': name,
                        'table': table,
                        'description': description
                        }
                
        self.send_response(response)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        if sys.version_info[0] >= 3:
            output = output.encode()
        self.wfile.write(output)
                

class WebDoc(callbacks.Plugin):
    """Add the help for "@plugin help WebDoc" here
    This should describe *how* to use this plugin."""
    def __init__(self, irc):
        self.__parent = super(WebDoc, self)
        callbacks.Plugin.__init__(self, irc)

        callback = WebDocServerCallback(self, irc)
        httpserver.hook('plugindoc', callback)

    def die(self):
        httpserver.unhook('plugindoc')
        self.__parent.die()


Class = WebDoc


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2013, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class WebDocTestCase(PluginTestCase):
    plugins = ('WebDoc',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('WebLogs')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('WebLogs', True)


WebLogs = conf.registerPlugin('WebLogs')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(WebLogs, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))
conf.registerChannelValue(WebLogs, 'enabled',
    registry.Boolean(False, _("""Determines whether the web logs for this
    channel are available.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import re
import os
import sys
import cgi
import time
import urllib

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.irclib as irclib
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.httpserver as httpserver
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('WebLogs')

if sys.version_info[0] >= 3:
    def b(s):
        if isinstance(s, str):
            return s.encode()
        else:
            return s
    def s(b):
        if isinstance(b, bytes):
            return b.decode()
        else:
            return b
else:
    def b(s):
        return s
    def s(b):
        return b

page_template = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="fr" >
    <head>
        <title>%(title)s - WebLogs</title>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <style type="text/css">
            h1 {
                display: inline;
            }
            .line .timestamp {
                display: none;
            }
            .line:hover .timestamp, .line:focus .timestamp {
                display: inline;
                float: right;
            }
            .command-PART { color: maroon; }
            .command-QUIT { color: maroon; }
            .command-JOIN { color: green; }
            .command-MODE { color: olive; }
            .command-KICK { color: red; }
        </style>
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.6.4/jquery.min.js">
        </script>
        <script>
            $(document).ready(function() {
                $("div.day div").hide();
                $("div.day input.hide").hide();
                $("input.reveal").click(function() {
                        $(this).hide();
                        $(this).parents("div").children("div.day input.hide").fadeIn(600);
                        $(this).parents("div").children("div.day div").fadeIn(600);
                });
                $("input.hide").click(function() {
                        $(this).hide();
                        $(this).parents("div").children("div.day input.reveal").fadeIn(600);
                        $(this).parents("div").children("div.day div").fadeOut(600);
                });
            });
        </script>
    </head>
    <body>
        %(body)s
    </body>
</html>"""

# From http://stackoverflow.com/questions/1071191/detect-urls-in-a-string
URL_REGEXP = re.compile(r'''((?:mailto:|ftp://|http://)[^ <>'"{}|\\^`[\]]*)''')

def format_logs(logs):
    def format_nick(nick):
        template = '<span style="color: %(color)s;">%(nick)s</span>'
        colors = ['red', 'orange', 'blue', 'lime', 'grey', 'green', 'purple',
                'black', 'olive']
        hash_ = sum([ord(x) for x in nick]) % len(colors)
        return template % {'color': colors[hash_], 'nick': nick}
    html_logs = '<div>' # Will be closed by the first "Changed day"
    old_gmtime_day = None
    for line in logs.split('\n'):
        words = line.split(' ')
        if len(words) < 2:
            continue
        timestamp = words[0]
        command = words[1]
        new_line = None
        if command == 'PRIVMSG' or command == 'NOTICE':
            if command == 'PRIVMSG':
                nick_delimiters = ('&lt;', '&gt;')
            else:
                nick_delimiters = ('*', '*')
            formatted_nick = nick_delimiters[0] + format_nick(words[2]) + \
                    nick_delimiters[1]
            new_line = _('%(formatted_nick)s %(message)s') % {
                    'formatted_nick': formatted_nick,
                    'message': cgi.escape(' '.join(words[3:]))}
        elif command == 'PRIVMSG-ACTION':
            new_line = _('* %(nick)s %(message)s') % {
                    'nick': format_nick(words[2]),
                    'message': cgi.escape(' '.join(words[3:]))}
        elif command == 'PART':
            new_line = _('<-- %(nick)s has left the channel (%(reason)s)') % \
                    {'nick': format_nick(words[2]),
                    'reason': cgi.escape(' '.join(words[3:]))}
        elif command == 'QUIT':
            new_line = _('<-- %(nick)s has quit the network (%(reason)s)') % \
                    {'nick': format_nick(words[2]),
                    'reason': cgi.escape(' '.join(words[3:]))}
        elif command == 'JOIN':
            new_line = _('--> %(nick)s has joined the channel') % \
                    {'nick': format_nick(words[2])}
        elif command == 'MODE':
            new_line = _('*/* %(nick)s has set mode %(modes)s') % \
                    {'nick': format_nick(words[2]),
                    'modes': ' '.join(words[3:])}
        elif command == 'KICK':
            new_line = _('<-- %(kicked)s has been kicked by %(kicker)s (%(reason)s)') % \
                    {'kicked': format_nick(words[3]),
                    'kicker': format_nick(words[2]),
                    'reason': cgi.escape(' '.join(words[4:]))}
        if new_line is not None:
            template = """
                <div class="line command-%(command)s">
                    <span class="timestamp">%(timestamp)s</span>
                    %(line)s
                </div>"""
            new_line = URL_REGEXP.sub(r'<a href="\1">\1</a>', new_line)

            # Timestamp handling
            gmtime = time.gmtime(int(words[0]))
            gmtime_day = (gmtime.tm_mday, gmtime.tm_mon, gmtime.tm_year)
            if old_gmtime_day != gmtime_day:
                html_logs += '</div><div class="day">'
                html_logs += """
                    <input type="button" value="reveal" class="reveal" />
                    <input type="button" value="hide" class="hide" />
                    """
                html_logs += '<h1>%i/%i/%i</h1>' % \
                        gmtime_day
                old_gmtime_day = gmtime_day
            timestamp = time.strftime('%H:%M:%S', gmtime)


            html_logs += template % {'line': new_line,
                    'timestamp': timestamp, 'command': command}
    return html_logs


class WebLogsMiddleware(object):
    """Class for reading and parsing WebLogs data."""
    __shared_states = {}
    def __init__(self, channel):
        if channel in self.__shared_states:
            self.__dict__ = self.__shared_states[channel]
        else:
            self._channel = channel
            path = conf.supybot.directories.data.dirize('WebLogs_%s.log' %
                    channel)
            self.fd = open(path, 'a+')
            self.__shared_states.update({channel: self.__dict__})

    @classmethod
    def get_channel_list(cls):
        channels = [x[len('WebLogs_'):-len('.log')]
                for x in os.listdir(conf.supybot.directories.data())
                if x.endswith('.log')]
        return [x for x in channels
                if cls._plugin.registryValue('enabled', x)]

    def get_logs(self):
        self.fd.seek(0)
        return self.fd.read()

    def write(self, *args):
        self.fd.read()
        self.fd.write(s('%i %s\n' % (time.time(), ' '.join(args))))

class WebLogsServerCallback(httpserver.SupyHTTPServerCallback):
    name = 'WebLogs'

    def doGet(self, handler, path):
        if path == '':
            self.send_response(301)
            self.send_header('Location', '/weblogs/')
            self.end_headers()
            return
        elif path == '/':
            splitted_path = []
        else:
            splitted_path = path[1:].split('/')
        if len(splitted_path) == 0:
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            page_body = """Here is a list of available logs:<ul>"""
            for channel in WebLogsMiddleware.get_channel_list():
                page_body += '<li><a href="./html/%s/">%s</a></li>' % (
                        utils.web.urlquote(channel), channel)
            page_body += '</ul>'
            self.wfile.write(b(page_template %
                    {'title': 'Index', 'body': page_body}))
            return
        elif len(splitted_path) == 3:
            mode, channel, page = splitted_path
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(b('Bad URL.'))
            return
        assert mode in ('html', 'json')
        channel = utils.web.urlunquote(channel)
        if channel not in WebLogsMiddleware.get_channel_list():
            self.send_response(404)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(b('This channel is not logged.'))
            return

        middleware = WebLogsMiddleware(channel)
        if page == '':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b(page_template % {
                'title': channel,
                'body': format_logs(middleware.get_logs())}))

def check_enabled(f):
    def newf(self, irc, msg):
        channel = msg.args[0]
        if irc.isChannel(channel) and self.registryValue('enabled', channel) \
                and not msg.tagged('relayedMsg'):
            return f(self, irc, msg, WebLogsMiddleware(channel))
        return msg
    return newf

@internationalizeDocstring
class WebLogs(callbacks.Plugin):
    """Add the help for "@plugin help WebLogs" here
    This should describe *how* to use this plugin."""

    def __init__(self, irc):
        # Some stuff needed by Supybot
        self.__parent = super(WebLogs, self)
        callbacks.Plugin.__init__(self, irc)

        self.lastStates = {}
        WebLogsMiddleware._plugin = self

        # registering the callback
        callback = WebLogsServerCallback() # create an instance of the callback
        httpserver.hook('weblogs', callback)

    @check_enabled
    def doPrivmsg(self, irc, msg, middleware):
        if ircmsgs.isAction(msg):
            middleware.write('PRIVMSG-ACTION', msg.nick,
                    ircmsgs.unAction(msg))
        else:
            middleware.write('PRIVMSG', msg.nick, msg.args[1])

    @check_enabled
    def outFilter(self, irc, msg, middleware):
        if msg.command == 'PRIVMSG':
            middleware.write('PRIVMSG', irc.nick, msg.args[1])
        elif msg.command == 'NOTICE':
            middleware.write('NOTICE', irc.nick, msg.args[1])
        return msg

    @check_enabled
    def doNotice(self, irc, msg, middleware):
        middleware.write('NOTICE', msg.nick, msg.args[1])

    @check_enabled
    def doPart(self, irc, msg, middleware):
        if len(msg.args) == 1:
            reason = ''
        else:
            reason = msg.args[1]
        middleware.write('PART', msg.nick, reason)

    @check_enabled
    def doJoin(self, irc, msg, middleware):
        middleware.write('JOIN', msg.nick)

    @check_enabled
    def doMode(self, irc, msg, middleware):
        middleware.write('MODE', msg.nick, msg.args[1], ' '.join(msg.args[2:]))

    @check_enabled
    def doKick(self, irc, msg, middleware):
        middleware.write('KICK', msg.nick, ' '.join(msg.args[1:]))

    def __call__(self, irc, msg):
        self.__parent.__call__(irc, msg)
        self.lastStates[irc] = irc.state.copy()
    def doQuit(self, irc, msg):
        if len(msg.args) == 0:
            reason = ''
        else:
            reason = msg.args[0]

        if not isinstance(irc, irclib.Irc):
            irc = irc.getRealIrc()
        for (channel, chan) in self.lastStates[irc].channels.items():
            if msg.nick in chan.users:
                if self.registryValue('enabled', channel):
                    middleware = WebLogsMiddleware(channel)
                    middleware.write('QUIT', msg.nick, reason)

    def die(self):
        # unregister the callback
        httpserver.unhook('weblogs')

        # Stuff for Supybot
        self.__parent.die()

Class = WebLogs


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class WebLogsTestCase(PluginTestCase):
    plugins = ('WebLogs',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Website')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Website', True)


Website = conf.registerPlugin('Website')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Website, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import re
import sys
import json
import supybot.world as world
import supybot.utils as utils
from supybot import httpserver
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

if sys.version_info[0] < 3:
    from urllib import urlencode
else:
    from urllib.parse import urlencode

_ = PluginInternationalization('Website')

class WebsiteCallback(httpserver.SupyHTTPServerCallback):
    name = 'Supybot website callback'
    defaultResponse = _("""
    You shouldn't be there, this subfolder is not for you. Go back to the
    index and try out other plugins (if any).""")
    def doPost(self, handler, path, form):
        try:
            self.plugin.announce.onPayload(form)
        except Exception as e:
            raise e
        finally:
            self.send_response(200)
            self.end_headers()

def query(path, args={}):
    args = dict([(x,y) for x,y in args.items() if y is not None])
    url = 'http://supybot.aperio.fr/api%s?%s' % (path, urlencode(args))
    data = utils.web.getUrl(url)
    if sys.version_info[0] >= 3:
        data = data.decode()
    return json.loads(data)

instance = None

bold = ircutils.bold

@internationalizeDocstring
class Website(callbacks.Plugin):
    """Add the help for "@plugin help Website" here
    This should describe *how* to use this plugin."""
    threaded = True

    def __init__(self, irc):
        global instance
        self.__parent = super(Website, self)
        callbacks.Plugin.__init__(self, irc)
        instance = self

        callback = WebsiteCallback()
        callback.plugin = self
        httpserver.hook('website', callback)

    class announce(callbacks.Commands):
        _matchers = {
                'id': re.compile('[a-zA-Z0-9]+'),
                'author': re.compile('[a-zA-Z0-9]+'),
                'lexer': re.compile('[a-zA-Z0-9 /]+'),
                }
        def onPayload(self, form):
            for name in ('id', 'author', 'lexer'):
                assert self._matchers[name].match(form[name].value), \
                        '%s is not valid.' % name
            id_ = form['id'].value
            author = form['author'].value
            try:
                name = form['name'].value
            except KeyError:
                name = 'Unnamed paste'
            channel = form['channel'].value
            lexer = form['lexer'].value
            assert channel in ('#limnoria', '#progval', '#supybot')
            for irc in world.ircs:
                if irc.network == 'freenode':
                    assert channel in irc.state.channels
                    s = ('%s just pasted %s (type: %s): '
                            'http://supybot.aperio.fr/paste/%s') % (
                            bold(author),
                            bold(name),
                            bold(lexer),
                            id_)
                    try:
                        irc.queueMsg(ircmsgs.privmsg(channel, s))
                    except KeyError:
                        pass

    def plugin(self, irc, msg, args, name):
        """<name>

        Returns informations about the plugin with that <name> on the
        website."""
        results = query('/plugins/view/%s/' % name)
        if len(results) == 0:
            irc.error(_('No plugin with that name.'))
            return
        irc.reply('%s %s' % (results['short_description'].replace('\r', '')
                                                         .replace('\n', ' '),
                             'http://supybot.aperio.fr/plugins/view/%s/' % name))
    plugin = wrap(plugin, ['something'])


    def die(self):
        self.__parent.die()
        httpserver.unhook('website')

Class = Website


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class WebsiteTestCase(PluginTestCase):
    plugins = ('Website',)

    if network:
        def testPlugin(self):
            self.assertError('plugin')
            self.assertError('plugin Eeigrg')
            self.assertResponse('plugin AttackProtector', 'This plugin aims to '
                    'provide a highly configurable protection against flood and '
                    'spam. http://supybot.aperio.fr/plugins/view/AttackProtector/')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('WebStats')
except:
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('WebStats', True)


WebStats = conf.registerPlugin('WebStats')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(WebStats, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))

conf.registerGroup(WebStats, 'channel')
conf.registerChannelValue(WebStats.channel, 'enable',
    registry.Boolean(False, _("""Determines whether the stats are enabled
        for this channel.""")))
conf.registerChannelValue(WebStats.channel, 'language',
    registry.String(_('en'), _("""Determines what language is used on the
        website""")))
conf.registerChannelValue(WebStats.channel, 'excludenicks',
    registry.String('', _("""Space-separated list of nicks excluded from
        stats.""")))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
# -*- coding: utf8 -*-
###
# Copyright (c) 2010-2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import re
import os
import sys
import time
import urllib
import random
import datetime
if sys.version_info[0] >= 3:
    from io import BytesIO
else:
    from cStringIO import StringIO as BytesIO

import supybot.conf as conf
import supybot.world as world
import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.irclib as irclib
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.httpserver as httpserver

try:
    import sqlite3
except ImportError:
    from pysqlite2 import dbapi2 as sqlite3 # for python2.4

try:
    from supybot.i18n import _PluginInternationalization
    class WebStatsInternationalization(_PluginInternationalization):
        def __init__(self):
            self.name = 'WebStats'
            try:
                self.loadLocale(conf.supybot.language())
            except:
                pass
    _ = WebStatsInternationalization()
except ImportError:
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

DEBUG = False

testing = world.testing
world.webStatsCacheLinks = {}

#####################################################################
# Utilities
#####################################################################

class FooException(Exception):
    pass

if not hasattr(world, 'webStatsCacheLinks'):
    world.webStatsCacheLinks = {}

colors = ['green', 'red', 'orange', 'blue', 'black', 'gray50', 'indigo']

def chooseColor(nick):
    global colors
    return random.choice(colors)

def progressbar(item, max_):
    template = """<td class="progressbar">
                      <div class="text">%i</div>
                      <div style="width: %i%%; background-color: %s"
                      class="color"></div>
                  </td>"""
    try:
        percent = round(float(item)/float(max_)*100)
        color = round((100-percent)/10)*3+59
        template %= (item, percent, '#ef%i%i' % (color, color))
    except ZeroDivisionError:
        template %= (item, 0, 'orange')
    return template

def fillTable(items, page, orderby=None):
    output = ''
    nbDisplayed = 0
    max_ = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    for index in items:
        for index_ in range(0, len(max_)):
            max_[index_] = max(max_[index_], items[index][index_])
    rowsList = []
    while len(items) > 0:
        maximumIndex = max(items.keys())
        highScore = -1
        for index in items:
            if orderby is not None and items[index][orderby] > highScore:
                maximumIndex = index
                highScore = items[index][orderby]
        item = items.pop(maximumIndex)
        try:
            int(index)
            indexIsInt = True
        except:
            indexIsInt = False
        if sum(item[0:1] + item[3:]) > 5 or indexIsInt:
            rowsList.append((maximumIndex, item))
            nbDisplayed += 1
    for row in rowsList[int(page):int(page)+25]:
        index, row = row
        output += '<tr><td>%s</td>' % index
        for cell in (progressbar(row[0], max_[0]),
                     progressbar(row[1], max_[1]),
                     progressbar(row[3], max_[3]),
                     progressbar(row[4], max_[4]),
                     progressbar(row[5], max_[5]),
                     progressbar(row[6], max_[6]),
                     progressbar(row[7], max_[7]),
                     progressbar(row[8], max_[8])
                     ):
            output += cell
        output += '</tr>'
    return output, nbDisplayed

headers = (_('Lines'), _('Words'), _('Joins'), _('Parts'),
           _('Quits'), _('Nick changes'), _('Kicks'), _('Kicked'))
tableHeaders = '<table><tr><th><a href="%s">%s</a></th>'
for header in headers:
    tableHeaders += '<th style="width: 150px;"><a href="%%s%s/">%s</a></th>' %\
                    (header, header)
tableHeaders += '</tr>'

nameToColumnIndex = {_('lines'):0,_('words'):1,_('chars'):2,_('joins'):3,
                     _('parts'):4,_('quits'):5,_('nick changes'):6,_('kickers'):7,
                     _('kicked'):8,_('kicks'):7}
def getTable(firstColumn, items, channel, urlLevel, page, orderby):
    percentParameter = tuple()
    for foo in range(1, len(tableHeaders.split('%s'))-1):
        percentParameter += ('./' + '../'*(urlLevel-4),)
        if len(percentParameter) == 1:
            percentParameter += (firstColumn,)
    output = tableHeaders % percentParameter
    if orderby is not None:
        if sys.version_info[0] >= 3:
            orderby = urllib.parse.unquote(orderby)
        else:
            orderby = urllib.unquote(orderby)
        try:
            index = nameToColumnIndex[orderby]
            html, nbDisplayed = fillTable(items, page, index)
        except KeyError:
            orderby = None
    if orderby is None:
        html, nbDisplayed = fillTable(items, page)
    output += html
    output += '</table>'
    return output, nbDisplayed

#####################################################################
# Templates
#####################################################################

PAGE_SKELETON = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <title>Supybot WebStats</title>
        <link rel="stylesheet" media="screen" type="text/css" title="Design" href="/default.css" />
        <link rel="stylesheet" media="screen" type="text/css" title="Design" href="/webstats/design.css" />
    </head>
    <body %%s>
%%s
        <p id="footer">
            <a href="https://github.com/ProgVal/Limnoria">Limnoria</a> and
            <a href="https://github.com/ProgVal/Supybot-plugins/tree/master/WebStats/">WebStats</a> powered.<br />
            Libre software available under BSD licence.<br />
            Page generated at %s.
        </p>
    </body>
</html>
""" % time.strftime('%H:%M:%S')

DEFAULT_TEMPLATES = {
        'webstats/design.css': """\
body, html {
    text-align: center;
}

li {
    list-style-type: none;
}

#footer {
    width: 100%;
    font-size: 0.6em;
    text-align: right;
}

.chanslist li a:visited {
    color: blue;
}

table {
    margin-left: auto;
    margin-right: auto;
}
.progressbar {
    border: orange 1px solid;
    height: 20px;
}
.progressbar .color {
    background-color: orange;
    height: 20px;
    text-align: center;
    -moz-border-radius: 10px;
    -webkit-border-radius: 10px;
}
.progressbar .text {
    position: absolute;
    width: 150px;
    text-align: center;
    margin-top: auto;
    margin-bottom: auto;
}""",
        'webstats/index.html': PAGE_SKELETON % ('class="purelisting"', """\
<h1>%(title)s</h1>

<ul class="chanslist">
%(channels)s
</ul>"""),
        'webstats/global.html': PAGE_SKELETON % ('', """\
<h1>Stats about %(channel)s channel</h1>

<p><a href="/webstats/nicks/%(escaped_channel)s/">View nick-by-nick stats</a></p>
<p><a href="/webstats/links/%(escaped_channel)s/">View links</a></p>

<p>There were %(quick_stats)s</p>

%(table)s"""),
        'webstats/nicks.html': PAGE_SKELETON % ('', """\
<h1>Stats about %(channel)s channel</h1>

<p><a href="/webstats/global/%(escaped_channel)s/">View global stats</a></p>
<p><a href="/webstats/links/%(escaped_channel)s/">View links</a></p>

%(table)s

<p>%(pagination)s</p>
"""),
}

httpserver.set_default_templates(DEFAULT_TEMPLATES)

#####################################################################
# Controller
#####################################################################

class WebStatsServerCallback(httpserver.SupyHTTPServerCallback):
    name = 'WebStats'
    def doGet(self, handler, path):
        output = ''
        splittedPath = path.split('/')
        try:
            if path == '/design.css':
                response = 200
                content_type = 'text/css; charset=utf-8'
                output = httpserver.get_template('webstats/design.css')
            elif path == '/':
                response = 200
                content_type = 'text/html; charset=utf-8'
                output = self.get_index()
            elif path == '/global/':
                response = 404
                content_type = 'text/html; charset=utf-8'
                output = """<p style="font-size: 20em">BAM!</p>
                <p>You played with the URL, you lost.</p>"""
            elif splittedPath[1] in ('nicks', 'global', 'links') \
                    and path[-1]=='/'\
                    or splittedPath[1] == 'nicks' and \
                    path.endswith('.htm'):
                response = 200
                content_type = 'text/html; charset=utf-8'
                if splittedPath[1] == 'links':
                    try:
                        import pygraphviz
                        content_type = 'image/png'
                    except ImportError:
                        content_type = 'text/plain; charset=utf-8'
                        response = 501
                        output = 'Links cannot be displayed; ask ' \
                                'the bot owner to install python-pygraphviz.'
                        return
                assert len(splittedPath) > 2
                chanName = splittedPath[2].replace('%20', '#')
                page = splittedPath[-1][0:-len('.htm')]
                if page == '':
                    page = '0'
                if splittedPath[1] == 'nicks':
                    formatter = self.get_nicks
                elif splittedPath[1] == 'global':
                    formatter = self.get_global
                elif splittedPath[1] == 'links':
                    formatter = self.get_links
                else:
                    raise AssertionError(splittedPath[1])
                
                if len(splittedPath) == 3:
                    _.loadLocale(self.plugin._getLanguage(chanName))
                    output = formatter(len(splittedPath), chanName, page)
                else:
                    assert len(splittedPath) > 3
                    _.loadLocale(self.plugin._getLanguage(chanName))
                    subdir = splittedPath[3].lower()
                    output = formatter(len(splittedPath), chanName, page,
                            subdir)
            else:
                response = 404
                content_type = 'text/html; charset=utf-8'
                output = httpserver.get_template('generic/error.html') % \
                    {'title': 'WebStats - not found',
                     'error': 'Requested page is not found. Sorry.'}
        except Exception as e:
            response = 500
            content_type = 'text/html; charset=utf-8'
            if output == '':
                error = '<h1>Internal server error</h1>'
                if DEBUG:
                    error = '<p>The server raised this exception: %s</p>' % \
                            repr(e)
                output = httpserver.get_template('generic/error.html') % \
                    {'title': 'Internal server error',
                     'error': error}
            import traceback
            traceback.print_exc()
        finally:
            self.send_response(response)
            self.send_header('Content-type', content_type)
            self.end_headers()
            if sys.version_info[0] >= 3:
                output = output.encode()
            self.wfile.write(output)

    def get_index(self):
        template = httpserver.get_template('webstats/index.html')
        channels = self.db.getChannels()
        if len(channels) == 0:
            title = _('Stats available for no channels')
        elif len(channels) == 1:
            title = _('Stats available for a channel:')
        else:
            title = _('Stats available for channels:')
        channels_html = ''
        for channel in channels:
            channels_html += ('<li><a href="/webstats/global/%s/" title="%s">'
                         '%s</a></li>') % \
                      (channel[1:].replace('#', ' '), # Strip the leading #
                      _('View the stats for the %s channel') % channel,
                      channel)
        return template % {'title': title, 'channels': channels_html}

    def get_global(self, urlLevel, channel, page, orderby=None):
        template = httpserver.get_template('webstats/global.html')
        channel = '#' + channel
        items = self.db.getChanGlobalData(channel)
        bound = self.db.getChanRecordingTimeBoundaries(channel)
        hourly_items = self.db.getChanXXlyData(channel, 'hour')
        replacement = {'channel': channel,
                'escaped_channel': channel[1:].replace('#', ' '),
                'quick_stats': utils.str.format(
                    '%n, %n, %n, %n, %n, %n, %n, and %n.',
                    (items[0], _('line')), (items[1], _('word')),
                    (items[2], _('char')), (items[3], _('join')),
                    (items[4], _('part')), (items[5], _('quit')),
                    (items[6], _('nick change')),
                    (items[8], _('kick'))),
                'table': getTable(_('Hour'), hourly_items, channel, urlLevel,
                    page, orderby)[0]
                }
        return template % replacement

    def get_nicks(self, urlLevel, channel, page, orderby=None):
        channel = '#' + channel
        template = httpserver.get_template('webstats/nicks.html')
        items = self.db.getChanGlobalData(channel)
        bound = self.db.getChanRecordingTimeBoundaries(channel)
        nickly_items = self.db.getChanNickGlobalData(channel, 20)
        table, nbItems = getTable(_('Nick'), nickly_items, channel,
                urlLevel, page, orderby)

        page = int(page)
        pagination = ''
        if nbItems >= 25:
            if page == 0:
                pagination += '1 '
            else:
                pagination += '<a href="0.htm">1</a> '
            if page > 100:
                pagination += '... '
            for i in range(int(max(1,page/25-3)),int(min(nbItems/25-1,page/25+3))):
                if page != i*25-1:
                    pagination += '<a href="%i.htm">%i</a> ' % (i*25-1, i*25)
                else:
                    pagination += '%i ' % (i*25)
            if nbItems - page > 100:
                pagination += '... '
            if page == nbItems-24-1:
                pagination += '%i' % (nbItems-24)
            else:
                pagination += '<a href="%i.htm">%i</a>' % (nbItems-24-1, nbItems-24)
        replacement = {
                'channel': channel,
                'escaped_channel': channel[1:].replace('#', ' '),
                'table': table,
                'pagination': pagination,
                }
        return template % replacement

    def get_links(self, urlLevel, channel, page, orderby=None):
        import pygraphviz
        cache = world.webStatsCacheLinks
        channel = '#' + channel
        items = self.db.getChanLinks(channel)
        output = ''
        if channel in cache and cache[channel][0] > time.time() - 3600:
            output = cache[channel][1]
        else:
            graph = pygraphviz.AGraph(strict=False, directed=True,
                                      start='regular', smoothing='spring',
                                      size='40') # /!\ Size is in inches /!\
            items = [(x,y,float(z)) for x,y,z in items]
            if not items:
                graph.add_node('No links for the moment.')
                buffer_ = BytesIO()
                graph.draw(buffer_, prog='circo', format='png')
                buffer_.seek(0)
                output = buffer_.read()
                return output
            graph.add_node('#root#', style='invisible')
            insertedNicks = {}
            divideBy = max([z for x,y,z in items])/10
            for item in items:
                for i in (0, 1):
                    if item[i] not in insertedNicks:
                        try:
                            insertedNicks.update({item[i]: chooseColor(item[i])})
                            graph.add_node(item[i], color=insertedNicks[item[i]],
                                           fontcolor=insertedNicks[item[i]])
                            graph.add_edge(item[i], '#root#', style='invisible',
                                           arrowsize=0, color='white')
                        except: # Probably unicode issue
                            pass
                graph.add_edge(item[0], item[1], arrowhead='vee',
                               color=insertedNicks[item[1]],
                               penwidth=item[2]/divideBy,
                               arrowsize=item[2]/divideBy/2+1)
            buffer_ = BytesIO()
            graph.draw(buffer_, prog='circo', format='png')
            buffer_.seek(0)
            output = buffer_.read()
            cache.update({channel: (time.time(), output)})
        return output

#####################################################################
# Database
#####################################################################

class WebStatsDB:
    def __init__(self):
        filename = conf.supybot.directories.data.dirize('WebStats.db')
        alreadyExists = os.path.exists(filename)
        if alreadyExists and testing:
            os.remove(filename)
            alreadyExists = False
        self._conn = sqlite3.connect(filename, check_same_thread = False)
        self._conn.text_factory = str
        if not alreadyExists:
            self.makeDb()

    def makeDb(self):
        """Create the tables in the database"""
        cursor = self._conn.cursor()
        cursor.execute("""CREATE TABLE messages (
                          chan VARCHAR(128),
                          nick VARCHAR(128),
                          time TIMESTAMP,
                          content TEXT
                          )""")
        cursor.execute("""CREATE TABLE moves (
                          chan VARCHAR(128),
                          nick VARCHAR(128),
                          time TIMESTAMP,
                          type VARCHAR(16),
                          content TEXT
                          )""")
        cursor.execute("""CREATE TABLE links_cache (
                          chan VARCHAR(128),
                          `from` VARCHAR(128),
                          `to` VARCHAR(128),
                          `count` VARCHAR(128))""")
        cacheTableCreator = """CREATE TABLE %s_cache (
                          chan VARCHAR(128),
                          %s
                          year INT,
                          month TINYINT,
                          day TINYINT,
                          dayofweek TINYINT,
                          hour TINYINT,
                          lines INTEGER,
                          words INTEGER,
                          chars INTEGER,
                          joins INTEGER,
                          parts INTEGER,
                          quits INTEGER,
                          nicks INTEGER,
                          kickers INTEGER,
                          kickeds INTEGER
                          )"""
        cursor.execute(cacheTableCreator % ('chans', ''))
        cursor.execute(cacheTableCreator % ('nicks', 'nick VARCHAR(128),'))
        self._conn.commit()
        cursor.close()

    def getChannels(self):
        """Get a list of channels in the database"""
        cursor = self._conn.cursor()
        cursor.execute("""SELECT DISTINCT(chan) FROM chans_cache""")
        results = []
        for row in cursor:
            results.append(row[0])
        cursor.close()
        return results

    def recordMessage(self, chan, nick, message):
        """Called by doPrivmsg or onNotice.

        Stores the message in the database"""
        cursor = self._conn.cursor()
        cursor.execute("""INSERT INTO messages VALUES (?,?,?,?)""",
                       (chan, nick, time.time(), message))
        self._conn.commit()
        cursor.close()
        if DEBUG or random.randint(0,50) == 10:
            self.refreshCache()

    def recordMove(self, chan, nick, type_, message=''):
        """Called by doJoin, doPart, or doQuit.

        Stores the 'move' in the database"""
        cursor = self._conn.cursor()
        cursor.execute("""INSERT INTO moves VALUES (?,?,?,?,?)""",
                       (chan, nick, time.time(), type_, message))
        self._conn.commit()
        cursor.close()
        if DEBUG or random.randint(0,50) == 10:
            self.refreshCache()

    _regexpAddressedTo = re.compile('^(?P<nick>[^:, ]+)[:,]')
    def refreshCache(self):
        """Clears the cache tables, and populate them"""
        self._truncateCache()
        tmp_chans_cache = {}
        tmp_nicks_cache = {}
        tmp_links_cache = {}
        cursor = self._conn.cursor()
        cursor.execute("""SELECT * FROM messages""")
        for row in cursor:
            chan, nick, timestamp, content = row
            chanindex, nickindex = self._getIndexes(chan, nick, timestamp)
            self._incrementTmpCache(tmp_chans_cache, chanindex, content)
            self._incrementTmpCache(tmp_nicks_cache, nickindex, content)

            matched = self._regexpAddressedTo.match(content)
            if matched is not None:
                to = matched.group('nick')
                if chan not in tmp_links_cache:
                    tmp_links_cache.update({chan: {}})
                if nick not in tmp_links_cache[chan]:
                    tmp_links_cache[chan].update({nick: {}})
                if to not in tmp_links_cache[chan][nick]:
                    tmp_links_cache[chan][nick].update({to: 0})
                tmp_links_cache[chan][nick][to] += 1
        for chan, nicks in list(tmp_links_cache.items()):
            for nick, tos in list(nicks.items()): # Yes, tos is the plural for to
                for to, count in list(tos.items()):
                    if to not in nicks:
                        continue
                    cursor.execute('INSERT INTO links_cache VALUES(?,?,?,?)',
                                   (chan, nick, to, count))
        cursor.close()
        cursor = self._conn.cursor()
        cursor.execute("""SELECT * FROM moves""")
        for row in cursor:
            chan, nick, timestamp, type_, content = row
            chanindex, nickindex = self._getIndexes(chan, nick, timestamp)
            self._addKeyInTmpCacheIfDoesNotExist(tmp_chans_cache, chanindex)
            self._addKeyInTmpCacheIfDoesNotExist(tmp_nicks_cache, nickindex)
            id = {'join':3,'part':4,'quit':5,'nick':6,'kicker':7,'kicked':8}
            id = id[type_]
            tmp_chans_cache[chanindex][id] += 1
            tmp_nicks_cache[nickindex][id] += 1
        cursor.close()
        self._writeTmpCacheToCache(tmp_chans_cache, 'chan')
        self._writeTmpCacheToCache(tmp_nicks_cache, 'nick')
        self._conn.commit()

    def _addKeyInTmpCacheIfDoesNotExist(self, tmpCache, key):
        """Takes a temporary cache list and key.

        If the key is not in the list, add it in the list with value list
        filled with zeros."""
        if key not in tmpCache:
            tmpCache.update({key: [0, 0, 0, 0, 0, 0, 0, 0, 0]})

    def _truncateCache(self):
        """Clears the cache tables"""
        cursor = self._conn.cursor()
        cursor.execute("""DELETE FROM chans_cache""")
        cursor.execute("""DELETE FROM nicks_cache""")
        cursor.execute("""DELETE FROM links_cache""")
        cursor.close()

    def _incrementTmpCache(self, tmpCache, index, content):
        """Takes a temporary cache list, the index it'll increment, and the
        message content.

        Updates the temporary cache to count the content."""
        self._addKeyInTmpCacheIfDoesNotExist(tmpCache, index)
        tmpCache[index][0] += 1
        tmpCache[index][1] += len(content.split(' '))
        tmpCache[index][2] += len(content)

    def _getIndexes(self, chan, nick, timestamp):
        """Takes a chan name, a nick, and a timestamp, and returns two index,
        to crawl the temporary chans and nicks caches."""
        dt = datetime.datetime.today()
        dt = dt.fromtimestamp(timestamp)
        chanindex = (chan,dt.year,dt.month,dt.day,dt.weekday(),dt.hour)
        nickindex = (chan,nick,dt.year,dt.month,dt.day,dt.weekday(),dt.hour)
        return chanindex, nickindex

    def _writeTmpCacheToCache(self, tmpCache, type_):
        """Takes a temporary cache list, its type, and write it in the cache
        database."""
        cursor = self._conn.cursor()
        for index in tmpCache:
            data = tmpCache[index]
            values = index + tuple(data)
            cursor.execute("""INSERT INTO %ss_cache
                    VALUES(%s)""" % (type_, ('?,'*len(values))[0:-1]), values)
        cursor.close()


    def getChanGlobalData(self, chanName):
        """Returns a tuple, containing the channel stats, on all the recording
        period."""
        cursor = self._conn.cursor()
        cursor.execute("""SELECT SUM(lines), SUM(words), SUM(chars),
                                 SUM(joins), SUM(parts), SUM(quits),
                                 SUM(nicks), SUM(kickers), SUM(kickeds)
                          FROM chans_cache WHERE chan=?""", (chanName,))
        row = cursor.fetchone()
        if None in row:
            oldrow = row
            row = None
            for item in oldrow:
                if row is None:
                    row = (0,)
                else:
                    row += (0,)
        assert None not in row
        return row

    def getChanRecordingTimeBoundaries(self, chanName):
        """Returns two tuples, containing the min and max values of each
        year/month/day/dayofweek/hour field.

        Note that this data comes from the cache, so they might be a bit
        outdated if DEBUG is False."""
        cursor = self._conn.cursor()
        cursor.execute("""SELECT MIN(year), MIN(month), MIN(day),
                                 MIN(dayofweek), MIN(hour)
                          FROM chans_cache WHERE chan=?""", (chanName,))
        min_ = cursor.fetchone()

        cursor = self._conn.cursor()
        cursor.execute("""SELECT MAX(year), MAX(month), MAX(day),
                                 MAX(dayofweek), MAX(hour)
                          FROM chans_cache WHERE chan=?""", (chanName,))
        max_ = cursor.fetchone()

        if None in min_:
            min_ = tuple([int('0') for x in max_])
        if None in max_:
            max_ = tuple([int('0') for x in max_])
        assert None not in min_
        assert None not in max_
        return min_, max_

    def getChanXXlyData(self, chanName, type_):
        """Same as getChanGlobalData, but for the given
        year/month/day/dayofweek/hour.

        For example, getChanXXlyData('#test', 'hour') returns a list of 24
        getChanGlobalData-like tuples."""
        sampleQuery = """SELECT SUM(lines), SUM(words), SUM(chars),
                         SUM(joins), SUM(parts), SUM(quits),
                         SUM(nicks), SUM(kickers), SUM(kickeds)
                         FROM chans_cache WHERE chan=? and %s=?"""
        min_, max_ = self.getChanRecordingTimeBoundaries(chanName)
        typeToIndex = {"year":0, "month":1, "day":2, "dayofweek":3, "hour":4}
        if type_ not in typeToIndex:
            raise ValueError("Invalid type")
        min_ = min_[typeToIndex[type_]]
        max_ = max_[typeToIndex[type_]]
        results = {}
        for index in range(min_, max_+1):
            query = sampleQuery % (type_)
            cursor = self._conn.cursor()
            cursor.execute(query, (chanName, index))
            try:
                row = cursor.fetchone()
                assert row is not None
                if None in row:
                    row=tuple([0 for x in range(0,len(row))])
                results.update({index: row})
            except:
                self._addKeyInTmpCacheIfDoesNotExist(results, index)
            cursor.close()
        assert None not in results
        return results

    def getChanNickGlobalData(self, chanName, nick):
        """Same as getChanGlobalData, but only for one nick."""
        cursor = self._conn.cursor()
        cursor.execute("""SELECT nick, lines, words, chars, joins, parts,
                                 quits, nicks, kickers, kickeds
                          FROM nicks_cache WHERE chan=?""", (chanName,))
        results = {}
        for row in cursor:
            if row[0] not in results:
                results.update({row[0]: row[1:]})
            else:
                results.update({row[0]: tuple(sum(i)
                    for i in zip(row[1:], results[row[0]]))})
        return results

    def getChanLinks(self, chanName):
        cursor = self._conn.cursor()
        cursor.execute("""SELECT `from`, `to`, `count` FROM links_cache
                          WHERE chan=?""", (chanName,))
        return cursor

    def clearChannel(self, channel):
        cursor = self._conn.cursor()
        for table in ('messages', 'moves', 'links_cache', 'chans_cache',
                'nicks_cache'):
            cursor.execute('DELETE FROM %s WHERE chan=?' % table, (channel,))

#####################################################################
# Plugin
#####################################################################

class WebStats(callbacks.Plugin):
    def __init__(self, irc):
        self.__parent = super(WebStats, self)
        callbacks.Plugin.__init__(self, irc)
        self.lastmsg = {}
        self.ircstates = {}
        self.db = WebStatsDB()

        callback = WebStatsServerCallback()
        callback.plugin = self
        callback.db = self.db
        httpserver.hook('webstats', callback)

    def die(self):
        httpserver.unhook('webstats')
        self.__parent.die()

    def clear(self, irc, msg, args, channel, optlist):
        """[<channel>]

        Clear database for the <channel>. If <channel> is not given,
        it defaults to the current channel."""
        capability = ircdb.makeChannelCapability(channel, 'op')
        if not ircdb.checkCapability(msg.prefix, capability):
            irc.errorNoCapability(capability, Raise=True)
        if not optlist:
            irc.reply(_('Running this command will wipe all webstats data '
                'for the channel. If you are sure you want to do this, '
                'add the --confirm switch.'))
            return
        self.db.clearChannel(channel)
        irc.replySuccess()
    clear = wrap(clear, ['channel', getopts({'confirm': ''})])

    def doPrivmsg(self, irc, msg):
        channel = msg.args[0]
        if not channel.startswith('#'):
            return
        if channel == 'AUTH':
            return
        if not self.registryValue('channel.enable', channel):
            return
        content = msg.args[1]
        nick = msg.prefix.split('!')[0]
        if nick in self.registryValue('channel.excludenicks', channel) \
                .split(' '):
            return
        self.db.recordMessage(channel, nick, content)
    doNotice = doPrivmsg

    def doJoin(self, irc, msg):
        channel = msg.args[0]
        if not self.registryValue('channel.enable', channel):
            return
        nick = msg.prefix.split('!')[0]
        if nick in self.registryValue('channel.excludenicks', channel) \
                .split(' '):
            return
        self.db.recordMove(channel, nick, 'join')

    def doPart(self, irc, msg):
        channel = msg.args[0]
        if not self.registryValue('channel.enable', channel):
            return
        if len(msg.args) > 1:
            message = msg.args[1]
        else:
            message = ''
        nick = msg.prefix.split('!')[0]
        if nick in self.registryValue('channel.excludenicks', channel) \
                .split(' '):
            return
        self.db.recordMove(channel, nick, 'part', message)

    def doQuit(self, irc, msg):
        nick = msg.prefix.split('!')[0]
        if len(msg.args) > 1:
            message = msg.args[1]
        else:
            message = ''
        for channel in self.ircstates[irc].channels:
            if nick in self.registryValue('channel.excludenicks', channel) \
                    .split(' '):
                continue
            if self.registryValue('channel.enable', channel) and \
                msg.nick in self.ircstates[irc].channels[channel].users:
                self.db.recordMove(channel, nick, 'quit', message)
    def doNick(self, irc, msg):
        nick = msg.prefix.split('!')[0]
        if len(msg.args) > 1:
            message = msg.args[1]
        else:
            message = ''
        for channel in self.ircstates[irc].channels:
            if nick in self.registryValue('channel.excludenicks', channel) \
                    .split(' '):
                continue
            if self.registryValue('channel.enable', channel) and \
                msg.nick in self.ircstates[irc].channels[channel].users:
                self.db.recordMove(channel, nick, 'nick', message)
    def doKick(self, irc, msg):
        nick = msg.prefix.split('!')[0]
        if len(msg.args) > 1:
            message = msg.args[1]
        else:
            message = ''
        for channel in self.ircstates[irc].channels:
            if nick in self.registryValue('channel.excludenicks', channel) \
                    .split(' '):
                continue
            if self.registryValue('channel.enable', channel) and \
                msg.nick in self.ircstates[irc].channels[channel].users:
                self.db.recordMove(channel, nick, 'kicker', message)
                self.db.recordMove(channel, msg.args[1], 'kicked', message)

    def _getLanguage(self, channel):
        return self.registryValue('channel.language', '#' + channel)

    # The fellowing functions comes from the Relay plugin, provided
    # with Supybot
    def __call__(self, irc, msg):
        try:
            irc = self._getRealIrc(irc)
            if irc not in self.ircstates:
                self._addIrc(irc)
            self.ircstates[irc].addMsg(irc, self.lastmsg[irc])
        finally:
            self.lastmsg[irc] = msg
        self.__parent.__call__(irc, msg)
    def _addIrc(self, irc):
        # Let's just be extra-special-careful here.
        if irc not in self.ircstates:
            self.ircstates[irc] = irclib.IrcState()
        if irc not in self.lastmsg:
            self.lastmsg[irc] = ircmsgs.ping('this is just a fake message')
        if irc.afterConnect:
            # We've probably been reloaded.  Let's send some messages to get
            # our IrcState objects up to current.
            for channel in irc.state.channels:
                irc.queueMsg(ircmsgs.who(channel))
                irc.queueMsg(ircmsgs.names(channel))
    def _getRealIrc(self, irc):
        if isinstance(irc, irclib.Irc):
            return irc
        else:
            return irc.getRealIrc()

Class = WebStats


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2010, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class WebStatsTestCase(ChannelHTTPPluginTestCase):
    plugins = ('WebStats',)

    def testHandling(self):
        self.assertHTTPResponse('/webstats/', 400, method='POST')
        self.assertHTTPResponse('/webstats/', 200)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2010, quantumlemur
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('Wikipedia')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Wikipedia', True)


Wikipedia = conf.registerPlugin('Wikipedia')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Wikipedia, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))

conf.registerChannelValue(Wikipedia, 'url',
        registry.String(_('en.wikipedia.org'), _("""URL of the website from
        where you want to pull pages (usually: your language's
        wikipedia)""")))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2010, quantumlemur
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###


import re
import sys
import string
import urllib
import lxml.html
from lxml import etree
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
if sys.version_info[0] < 3:
    import StringIO
else:
    from io import StringIO
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('Wikipedia')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

if sys.version_info[0] >= 3:
    quote_plus = urllib.parse.quote_plus
else:
    quote_plus = urllib.quote_plus


class Wikipedia(callbacks.Plugin):
    """Add the help for "@plugin help Wikipedia" here
    This should describe *how* to use this plugin."""
    threaded = True


    @internationalizeDocstring
    def wiki(self, irc, msg, args, search):
        """<search term>

        Returns the first paragraph of a Wikipedia article"""
        reply = ''
        # first, we get the page
        addr = 'https://%s/wiki/Special:Search?search=%s' % \
                    (self.registryValue('url', msg.args[0]),
                     quote_plus(search))
        article = utils.web.getUrl(addr)
        if sys.version_info[0] >= 3:
            article = article.decode()
        # parse the page
        tree = lxml.html.document_fromstring(article)
        # check if it gives a "Did you mean..." redirect
        didyoumean = tree.xpath('//div[@class="searchdidyoumean"]/a'
                                '[@title="Special:Search"]')
        if didyoumean:
            redirect = didyoumean[0].text_content().strip()
            if sys.version_info[0] < 3:
                if isinstance(redirect, unicode):
                    redirect = redirect.encode('utf-8','replace')
                if isinstance(search, unicode):
                    search = search.encode('utf-8','replace')
            reply += _('I didn\'t find anything for "%s".'
                       'Did you mean "%s"? ') % (search, redirect)
            addr = self.registryValue('url', msg.args[0]) + \
                   didyoumean[0].get('href')
            if not article.startswith('http'):
                article = utils.web.getUrl('https://' + addr)
            if sys.version_info[0] >= 3:
                article = article.decode()
            tree = lxml.html.document_fromstring(article)
            search = redirect
        # check if it's a page of search results (rather than an article), and
        # if so, retrieve the first result
        searchresults = tree.xpath('//div[@class="searchresults"]/ul/li/a')
        if searchresults:
            redirect = searchresults[0].text_content().strip()
            reply += _('I didn\'t find anything for "%s", but here\'s the '
                     'result for "%s": ') % (search, redirect)
            addr = self.registryValue('url', msg.args[0]) + \
                   searchresults[0].get('href')
            article = utils.web.getUrl(addr)
            if sys.version_info[0] >= 3:
                article = article.decode()

            tree = lxml.html.document_fromstring(article)
            search = redirect
        # otherwise, simply return the title and whether it redirected
        else:
            redirect = re.search('\(%s <a href=[^>]*>([^<]*)</a>\)' %
                                 _('Redirected from'), article)
            if redirect:
                redirect = tree.xpath('//div[@id="contentSub"]/a')[0]
                redirect = redirect.text_content().strip()
                title = tree.xpath('//*[@class="firstHeading"]')
                title = title[0].text_content().strip()
                if sys.version_info[0] < 3:
                    if isinstance(title, unicode):
                        title = title.encode('utf-8','replace')
                    if isinstance(redirect, unicode):
                        redirect = redirect.encode('utf-8','replace')
                reply += '"%s" (Redirect from "%s"): ' % (title, redirect)
        # extract the address we got it from
        addr = re.search(_('Retrieved from') + ' "<a href="([^"]*)">', article)
        addr = addr.group(1)
        # check if it's a disambiguation page
        disambig = tree.xpath('//table[@id="disambigbox"]')
        if disambig:
            disambig = tree.xpath('//div[@id="bodyContent"]/ul/li/a')
            disambig = disambig[:5]
            disambig = [item.text_content() for item in disambig]
            r = utils.str.commaAndify(disambig)
            reply += _('%s is a disambiguation page. '
                       'Possible results are: %s') % (addr, r)
        # or just as bad, a page listing events in that year
        elif re.search(_('This article is about the year [\d]*\. '
                       'For the [a-zA-Z ]* [\d]*, see'), article):
            reply += _('"%s" is a page full of events that happened in that '
                      'year.  If you were looking for information about the '
                      'number itself, try searching for "%s_(number)", but '
                      'don\'t expect anything useful...') % (search, search)
        else:
            ##### etree!
            p = tree.xpath("//div[@id='mw-content-text']/p[1]")
            if len(p) == 0 or addr.endswith('Special:Search'):
                reply += _('Not found, or page bad formed.')
            else:
                p = p[0]
                p = p.text_content()
                p = p.strip()
                if sys.version_info[0] < 3:
                    if isinstance(p, unicode):
                        p = p.encode('utf-8', 'replace')
                    if isinstance(reply, unicode):
                        reply = reply.encode('utf-8','replace')
                reply += '%s %s' % (p, ircutils.bold(addr))
        reply = reply.replace('&amp;','&')
        irc.reply(reply)
    wiki = wrap(wiki, ['text'])



Class = Wikipedia


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2010, quantumlemur
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class WikipediaTestCase(PluginTestCase):
    plugins = ('Wikipedia',)

    if network:
        def testWiki(self):
            self.assertRegexp('wiki Monty Python',
                              '^Monty Python \(sometimes known as The Pythons\).*')
            self.assertRegexp('wiki Python', '.*is a disambiguation page.*')
            self.assertRegexp('wiki Foo', '"Foobar" \(Redirect from "Foo"\): '
                                          'The terms foobar.*')
            self.assertRegexp('wiki roegdfjpoepo',
                              'Not found, or page bad formed.*')



# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('WikiTrans')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('WikiTrans', True)


WikiTrans = conf.registerPlugin('WikiTrans')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(WikiTrans, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import sys

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('WikiTrans')

import urllib
from xml.dom import minidom

if sys.version_info[0] == 2:
    quote_plus = urllib.quote_plus
else:
    quote_plus = urllib.parse.quote_plus

class WordNotFound(Exception):
    pass
class Untranslatable(Exception):
    pass
class ApiError(Exception):
    pass

# lllimit means "langlink limits". If we don't give this parameter, output
# will be restricted to the ten first links.
url = 'http://%s.wikipedia.org/w/api.php?action=query&format=xml&' + \
        'prop=langlinks&redirects&lllimit=300&titles=%s'
def translate(src, target, word):
    try:
        node = minidom.parse(utils.web.getUrlFd(url % (src,
                quote_plus(word))))
    except:
        # Usually an urllib error
        raise WordNotFound()

    # The tree containing the langs links
    expectedNodes = 'api query pages page langlinks'.split()
    # Iterate while the node is not a langlink
    while node.nodeName != 'langlinks':
        if not node.hasChildNodes():
            raise WordNotFound()
        node = node.firstChild
        # If this page is a redirection to another:
        if node.nodeName in ('redirects', 'normalized'):
            newword = node.firstChild.getAttribute('to')
            return translate(src, target, newword)
        expectedNode = expectedNodes.pop(0)
        # Iterate while the node is not valid
        while node.nodeName != expectedNode:
            node = node.nextSibling
        if node.nodeName != expectedNode:
            raise ApiError()

    link = node.firstChild
    # Iterate through the links, until we find the one matching the target
    # language
    while link is not None:
        assert link.tagName == 'll'
        if link.getAttribute('lang') != target:
            link = link.nextSibling
            continue
        if sys.version_info[0] < 3:
            return link.firstChild.data.encode('utf-8', 'replace')
        else:
            return link.firstChild.data
    # Too bad :-(
    # No lang links available for the target language
    raise Untranslatable()

@internationalizeDocstring
class WikiTrans(callbacks.Plugin):
    """Add the help for "@plugin help WikiTrans" here
    This should describe *how* to use this plugin."""
    threaded = True
    def translate(self, irc, msg, args, src, target, word):
        """<from language> <to language> <word>

        Translates the <word> (also works with expressions) using Wikipedia
        interlanguage links."""
        try:
            irc.reply(translate(src, target, word))
        except WordNotFound:
            irc.error(_('This word can\'t be found on Wikipedia'))
        except Untranslatable:
            irc.error(_('No translation found'))
        except ApiError:
            irc.error(_('Something went wrong with Wikipedia API.'))

    translate = wrap(translate, ['something', 'something', 'text'])



Class = WikiTrans


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
# -*- encoding: utf8 -*-
###
# Copyright (c) 2011, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from __future__ import unicode_literals

from supybot.test import *

class WikiTransTestCase(PluginTestCase):
    plugins = ('WikiTrans',)

    def testTranslate(self):
        self.assertResponse('translate en be IRC', 'IRC')
        self.assertResponse('translate en fr IRC', 'Internet Relay Chat')

        self.assertResponse('translate en fr IRC bot', 'Robot IRC')
        self.assertResponse('translate fr en robot IRC', 'IRC bot')

        self.assertResponse('translate fr en Chef-d\'œuvre', 'Masterpiece')
        try:
            self.assertResponse('translate en fr Masterpiece', 'Chef-d\'œuvre')
            self.assertResponse('translate en fr Master (Doctor Who)',
                    'Le Maître (Doctor Who)')
        except AssertionError:
            self.assertResponse('translate en fr Masterpiece',
                    'Chef-d\'œuvre'.encode('utf8'))
            self.assertResponse('translate en fr Master (Doctor Who)',
                    'Le Maître (Doctor Who)'.encode('utf8'))


        self.assertRegexp('translate fi en paremmin', 'This word can\'t be found')

        self.assertError('translate fr de Supybot')
        self.assertError('translate fr en pogjoeregml')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2005, James Vega
# Copyright (c) 2009-2010 Michael Tughan
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import supybot.conf as conf
import supybot.utils as utils
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('WunderWeather', True)

WunderWeather = conf.registerPlugin('WunderWeather')
conf.registerChannelValue(WunderWeather, 'imperial',
    registry.Boolean(True, """Shows imperial formatted data (Fahrenheit, miles/hour)
    in the weather output if true. You can have both imperial and metric enabled,
    and the bot will show both."""))
conf.registerChannelValue(WunderWeather, 'metric',
    registry.Boolean(True, """Shows metric formatted data (Celsius, kilometres/hour)
    in the weather output if true. You can have both imperial and metric enabled,
    and the bot will show both."""))
conf.registerChannelValue(WunderWeather, 'showPressure',
    registry.Boolean(True, """Determines whether the bot will show pressures in its
    output. The type of pressure shown will depend on the metric/imperial settings."""))
conf.registerChannelValue(WunderWeather, 'forecastDays',
    registry.NonNegativeInteger(0, """Determines how many days the forecast shows, up to 7.
    If set to 0, show all days. See showForecast configuration variable to turn off
    forecast display."""))
conf.registerChannelValue(WunderWeather, 'showCurrentByDefault',
    registry.Boolean(True, """If True, will show the current conditions in the weather
    output if no ouput control switches are given."""))
conf.registerChannelValue(WunderWeather, 'showForecastByDefault',
    registry.Boolean(True, """If True, will show the forecast in the weather
    output if no ouput control switches are given."""))

conf.registerUserValue(conf.users.plugins.WunderWeather, 'lastLocation',
    registry.String('', ''))


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2005, James Vega
# Copyright (c) 2009-2010 Michael Tughan
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import sys
import xml.dom.minidom as dom

import supybot.utils as utils
from supybot.commands import wrap, additional, getopts
import supybot.callbacks as callbacks

from . import shortforms

# Name 'reload' is used by Supybot
from imp import reload as reload_
reload_(shortforms)

if sys.version_info[0] >= 3:
    def u(s):
        return s
else:
    def u(s):
        return unicode(s, "unicode_escape")

noLocationError = 'No such location could be found.'
class NoLocation(callbacks.Error):
    pass

class WunderWeather(callbacks.Plugin):
    """Uses the Wunderground XML API to get weather conditions for a given location.
    Always gets current conditions, and by default shows a 7-day forecast as well."""
    threaded = True
    
    
    ##########    GLOBAL VARIABLES    ##########
    
    _weatherCurrentCondsURL = 'http://api.wunderground.com/auto/wui/geo/WXCurrentObXML/index.xml?query=%s'
    _weatherForecastURL = 'http://api.wunderground.com/auto/wui/geo/ForecastXML/index.xml?query=%s'
    
    
    ##########    EXPOSED METHODS    ##########
    
    def weather(self, irc, msg, args, options, location):
        """[--current|--forecast|--all] [US zip code | US/Canada city, state | Foreign city, country]

        Returns the approximate weather conditions for a given city from Wunderground.
        --current, --forecast, and --all control what kind of information the command
        shows.
        """
        matchedLocation = self._commandSetup(irc, msg, location)
        locationName = self._getNodeValue(matchedLocation[0], 'full', 'Unknown Location')
        
        output = []
        showCurrent = False
        showForecast = False
        
        if not options:
            # use default output
            showCurrent = self.registryValue('showCurrentByDefault', self.__channel)
            showForecast = self.registryValue('showForecastByDefault', self.__channel)
        else:
            for (type, arg) in options:
                if type == 'current':
                    showCurrent = True
                elif type == 'forecast':
                    showForecast = True
                elif type == 'all':
                    showCurrent = True
                    showForecast = True
        
        if showCurrent and showForecast:
            output.append(u('Weather for ') + locationName)
        elif showCurrent:
            output.append(u('Current weather for ') + locationName)
        elif showForecast:
            output.append(u('Forecast for ') + locationName)
        
        if showCurrent:
            output.append(self._getCurrentConditions(matchedLocation[0]))
        
        if showForecast:
            # _getForecast returns a list, so we have to call extend rather than append
            output.extend(self._getForecast(matchedLocation[1]))
        
        if not showCurrent and not showForecast:
            irc.error("Something weird happened... I'm not supposed to show current conditions or a forecast!")
        
        irc.reply(self._formatUnicodeOutput(output))
    weather = wrap(weather, [getopts({'current': '', 'forecast': '', 'all': ''}), additional('text')])
    
    
    ##########    SUPPORTING METHODS    ##########
    
    def _checkLocation(self, location):
        if not location:
            location = self.userValue('lastLocation', self.__msg.prefix)
        if not location:
            raise callbacks.ArgumentError
        self.setUserValue('lastLocation', self.__msg.prefix, location, ignoreNoUser=True)
        
        # Check for shortforms, because Wunderground will attempt to check
        # for US locations without a full country name.
        
        # checkShortforms may return Unicode characters in the country name.
        # Need Latin 1 for Supybot's URL handlers to work
        webLocation = shortforms.checkShortforms(location)
        conditions = self._getDom(self._weatherCurrentCondsURL % utils.web.urlquote(webLocation))
        observationLocation = conditions.getElementsByTagName('observation_location')[0]
        
        # if there's no city name in the XML, we didn't get a match
        if observationLocation.getElementsByTagName('city')[0].childNodes.length < 1:
            # maybe the country shortform given conflicts with a state shortform and wasn't replaced before
            webLocation = shortforms.checkConflictingShortforms(location)
            
            # if no conflicting short names match, we have the same query as before
            if webLocation == None:
                return None
            
            conditions = self._getDom(self._weatherCurrentCondsURL % utils.web.urlquote(webLocation))
            observationLocation = conditions.getElementsByTagName('observation_location')[0]
            
            # if there's still no match, nothing more we can do
            if observationLocation.getElementsByTagName('city')[0].childNodes.length < 1:
                return None
        
        # if we get this far, we got a match. Return the DOM and location
        return (conditions, webLocation)
    
    def _commandSetup(self, irc, msg, location):
        channel = None
        if irc.isChannel(msg.args[0]):
            channel = msg.args[0]
        
        # set various variables for submethods use
        self.__irc = irc
        self.__msg = msg
        self.__channel = channel
        
        matchedLocation = self._checkLocation(location)
        if not matchedLocation:
            self._noLocation()
        
        return matchedLocation
    
    # format temperatures using _formatForMetricOrImperial
    def _formatCurrentConditionTemperatures(self, dom, string):
        tempC = self._getNodeValue(dom, string + '_c', u('N/A')) + u('\xb0C')
        tempF = self._getNodeValue(dom, string + '_f', u('N/A')) + u('\xb0F')
        return self._formatForMetricOrImperial(tempF, tempC)
    
    def _formatForecastTemperatures(self, dom, type):
        tempC = self._getNodeValue(dom.getElementsByTagName(type)[0], 'celsius', u('N/A')) + u('\xb0C')
        tempF = self._getNodeValue(dom.getElementsByTagName(type)[0], 'fahrenheit', u('N/A')) + u('\xb0F')
        return self._formatForMetricOrImperial(tempF, tempC)
    
    # formats any imperial or metric values according to the config
    def _formatForMetricOrImperial(self, imperial, metric):
        returnValues = []
        
        if self.registryValue('imperial', self.__channel):
            returnValues.append(imperial)
        if self.registryValue('metric', self.__channel):
            returnValues.append(metric)
        
        if not returnValues:
            returnValues = (imperial, metric)
        
        return u(' / ').join(returnValues)
    
    def _formatPressures(self, dom):
        # lots of function calls, but it just divides pressure_mb by 10 and rounds it
        pressureKpa = str(round(float(self._getNodeValue(dom, 'pressure_mb', u('0'))) / 10, 1)) + 'kPa'
        pressureIn = self._getNodeValue(dom, 'pressure_in', u('0')) + 'in'
        return self._formatForMetricOrImperial(pressureIn, pressureKpa)
    
    def _formatSpeeds(self, dom, string):
        mphValue = float(self._getNodeValue(dom, string, u('0')))
        speedM = u('%dmph') % round(mphValue)
        speedK = u('%dkph') % round(mphValue * 1.609344) # thanks Wikipedia for the conversion rate
        return self._formatForMetricOrImperial(speedM, speedK)
    
    def _formatUpdatedTime(self, dom):
        observationTime = self._getNodeValue(dom, 'observation_epoch', None)
        localTime = self._getNodeValue(dom, 'local_epoch', None)
        if not observationTime or not localTime:
            return self._getNodeValue(dom, 'observation_time', 'Unknown Time').lstrip(u('Last Updated on '))
        
        seconds = int(localTime) - int(observationTime)
        minutes = int(seconds / 60)
        seconds -= minutes * 60
        hours = int(minutes / 60)
        minutes -= hours * 60
        
        if seconds == 1:
            seconds = '1 sec'
        else:
            seconds = '%d secs' % seconds
        
        if minutes == 1:
            minutes = '1 min'
        else:
            minutes = '%d mins' % minutes
        
        if hours == 1:
            hours = '1 hr'
        else:
            hours = '%d hrs' % hours
        
        if hours == '0 hrs':
            if minutes == '0 mins':
                return '%s ago' % seconds
            return '%s, %s ago' % (minutes, seconds)
        return '%s, %s, %s ago' % (hours, minutes, seconds)
    
    def _getCurrentConditions(self, dom):
        output = []
        
        temp = self._formatCurrentConditionTemperatures(dom, 'temp')
        if self._getNodeValue(dom, 'heat_index_string') != 'NA':
            temp += u(' (Heat Index: %s)') % self._formatCurrentConditionTemperatures(dom, 'heat_index')
        if self._getNodeValue(dom, 'windchill_string') != 'NA':
            temp += u(' (Wind Chill: %s)') % self._formatCurrentConditionTemperatures(dom, 'windchill')
        output.append(u('Temperature: ') + temp)
        
        output.append(u('Humidity: ') + self._getNodeValue(dom, 'relative_humidity', u('N/A%')))
        if self.registryValue('showPressure', self.__channel):
            output.append(u('Pressure: ') + self._formatPressures(dom))
        output.append(u('Conditions: ') + self._getNodeValue(dom, 'weather').capitalize())
        output.append(u('Wind: ') + self._getNodeValue(dom, 'wind_dir', u('None')).capitalize() + ', ' + self._formatSpeeds(dom, 'wind_mph'))
        output.append(u('Updated: ') + self._formatUpdatedTime(dom))
        return u('; ').join(output)
    
    def _getDom(self, url):
        try:
            xmlString = utils.web.getUrl(url)
            return dom.parseString(xmlString)
        except utils.web.Error as e:
            error = e.args[0].capitalize()
            if error[-1] != '.':
                error = error + '.'
            self.__irc.error(error, Raise=True)
    
    def _getForecast(self, location):
        dom = self._getDom(self._weatherForecastURL % utils.web.urlquote(location))
        output = []
        count = 0
        max = self.registryValue('forecastDays', self.__channel)
        
        forecast = dom.getElementsByTagName('simpleforecast')[0]
        
        for day in forecast.getElementsByTagName('forecastday'):
            if count >= max and max != 0:
                break
            forecastOutput = []
            
            forecastOutput.append('Forecast for ' + self._getNodeValue(day, 'weekday').capitalize() + ': ' + self._getNodeValue(day, 'conditions').capitalize())
            forecastOutput.append('High of ' + self._formatForecastTemperatures(day, 'high'))
            forecastOutput.append('Low of ' + self._formatForecastTemperatures(day, 'low'))
            output.append('; '.join(forecastOutput))
            count += 1
        
        return output
    
    
    ##########    STATIC METHODS    ##########
    
    def _formatUnicodeOutput(output):
        # UTF-8 encoding is required for Supybot to handle \xb0 (degrees) and other special chars
        # We can't (yet) pass it a Unicode string on its own (an oddity, to be sure)
        s = u(' | ').join(output)
        if sys.version_info[0] < 3:
            s = s.encode('utf-8')
        return s
    _formatUnicodeOutput = staticmethod(_formatUnicodeOutput)
    
    def _getNodeValue(dom, value, default=u('Unknown')):
        subTag = dom.getElementsByTagName(value)
        if len(subTag) < 1:
            return default
        subTag = subTag[0].firstChild
        if subTag == None:
            return default
        return subTag.nodeValue
    _getNodeValue = staticmethod(_getNodeValue)
    
    def _noLocation():
        raise NoLocation(noLocationError)
    _noLocation = staticmethod(_noLocation)

Class = WunderWeather


########NEW FILE########
__FILENAME__ = shortforms
# coding=utf-8
###
# Copyright (c) 2009 Michael Tughan
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import sys

encoding = 'utf-8'
if sys.version_info[0] >= 3:
    def u(s):
        return s
else:
    def u(s):
        return unicode(s, "unicode_escape")

# Provinces.  (Province being a metric state measurement mind you. :D)
_shortforms = {
    # Canadian provinces
    'ab': 'alberta', 
    'bc': 'british columbia', 
    'mb': 'manitoba', 
    'nb': 'new brunswick', 
    'nf': 'newfoundland', 
    'ns': 'nova scotia', 
    'nt': 'northwest territories',
    'nwt':'northwest territories',
    'nu': 'nunavut', 
    'on': 'ontario', 
    'pe': 'prince edward island', 
    'pei':'prince edward island', 
    'qc': 'quebec', 
    'sk': 'saskatchewan', 
    'yk': 'yukon',
    
    # Countries
    'ad': 'andorra',
    'ae': 'united arab emirates',
    'af': 'afghanistan',
    'ag': 'antigua and barbuda',
    'ai': 'anguilla',
    'am': 'armenia',
    'an': 'netherlands antilles',
    'ao': 'angola',
    'aq': 'antarctica',
    'as': 'american samoa',
    'at': 'austria',
    'au': 'australia',
    'aw': 'aruba',
    'ax': u('åland islands'),
    'ba': 'bosnia and herzegovina',
    'bb': 'barbados',
    'bd': 'bangladesh',
    'be': 'belgium',
    'bf': 'burkina faso',
    'bg': 'bulgaria',
    'bh': 'bahrain',
    'bi': 'burundi',
    'bj': 'benin',
    'bl': 'saint barthélemy',
    'bm': 'bermuda',
    'bn': 'brunei darussalam',
    'bo': 'bolivia',
    'br': 'brazil',
    'bs': 'bahamas',
    'bt': 'bhutan',
    'bv': 'bouvet island',
    'bw': 'botswana',
    'by': 'belarus',
    'bz': 'belize',
    'cc': 'cocos (keeling) islands',
    'cd': 'congo, the democratic republic of the',
    'cf': 'central african republic',
    'cg': 'congo',
    'ch': 'switzerland',
    'ci': 'côte d\'ivoire',
    'ck': 'cook islands',
    'cl': 'chile',
    'cm': 'cameroon',
    'cn': 'china',
    'cr': 'costa rica',
    'cu': 'cuba',
    'cv': 'cape verde',
    'cx': 'christmas island',
    'cy': 'cyprus',
    'cz': 'czech republic',
    'dj': 'djibouti',
    'dk': 'denmark',
    'dm': 'dominica',
    'do': 'dominican republic',
    'dz': 'algeria',
    'ec': 'ecuador',
    'ee': 'estonia',
    'eg': 'egypt',
    'eh': 'western sahara',
    'er': 'eritrea',
    'es': 'spain',
    'et': 'ethiopia',
    'fi': 'finland',
    'fj': 'fiji',
    'fk': 'falkland islands',
    'fm': 'micronesia',
    'fo': 'faroe islands',
    'fr': 'france',
    'gb': 'united kingdom',
    'gd': 'grenada',
    'ge': 'georgia',
    'gf': 'french guiana',
    'gg': 'guernsey',
    'gh': 'ghana',
    'gi': 'gibraltar',
    'gl': 'greenland',
    'gm': 'gambia',
    'gn': 'guinea',
    'gp': 'guadeloupe',
    'gq': 'equatorial guinea',
    'gr': 'greece',
    'gs': 'south georgia and the south sandwich islands',
    'gt': 'guatemala',
    'gu': 'guam',
    'gw': 'guinea-bissau',
    'gy': 'guyana',
    'hk': 'hong kong',
    'hm': 'heard island and mcdonald islands',
    'hn': 'honduras',
    'hr': 'croatia',
    'ht': 'haiti',
    'hu': 'hungary',
    'ie': 'ireland',
    'im': 'isle of man',
    'io': 'british indian ocean territory',
    'iq': 'iraq',
    'ir': 'iran, islamic republic of',
    'is': 'iceland',
    'it': 'italy',
    'je': 'jersey',
    'jm': 'jamaica',
    'jo': 'jordan',
    'jp': 'japan',
    'ke': 'kenya',
    'kg': 'kyrgyzstan',
    'kh': 'cambodia',
    'ki': 'kiribati',
    'km': 'comoros',
    'kn': 'saint kitts and nevis',
    'kp': 'north korea',
    'kr': 'south korea',
    'kw': 'kuwait',
    'kz': 'kazakhstan',
    'lb': 'lebanon',
    'lc': 'saint lucia',
    'li': 'liechtenstein',
    'lk': 'sri lanka',
    'lr': 'liberia',
    'ls': 'lesotho',
    'lt': 'lithuania',
    'lu': 'luxembourg',
    'lv': 'latvia',
    'ly': 'libyan arab jamahiriya',
    'mc': 'monaco',
    'mf': 'saint martin',
    'mg': 'madagascar',
    'mh': 'marshall islands',
    'mk': 'macedonia, the former yugoslav republic of',
    'ml': 'mali',
    'mm': 'myanmar',
    'mp': 'northern mariana islands',
    'mq': 'martinique',
    'mr': 'mauritania',
    'mu': 'mauritius',
    'mv': 'maldives',
    'mw': 'malawi',
    'mx': 'mexico',
    'my': 'malaysia',
    'mz': 'mozambique',
    'na': 'namibia',
    'nf': 'norfolk island',
    'ng': 'nigeria',
    'ni': 'nicaragua',
    'nl': 'netherlands',
    'no': 'norway',
    'np': 'nepal',
    'nr': 'nauru',
    'nu': 'niue',
    'nz': 'new zealand',
    'om': 'oman',
    'pe': 'peru',
    'pf': 'french polynesia',
    'pg': 'papua new guinea',
    'ph': 'philippines',
    'pk': 'pakistan',
    'pl': 'poland',
    'pm': 'saint pierre and miquelon',
    'pn': 'pitcairn',
    'pr': 'puerto rico',
    'ps': 'palestinian territory',
    'pt': 'portugal',
    'pw': 'palau',
    'py': 'paraguay',
    'qa': 'qatar',
    're': 'réunion',
    'ro': 'romania',
    'rs': 'serbia',
    'ru': 'russian federation',
    'rw': 'rwanda',
    'sa': 'saudi arabia',
    'sb': 'solomon islands',
    'se': 'sweden',
    'sg': 'singapore',
    'sh': 'saint helena',
    'si': 'slovenia',
    'sj': 'svalbard and jan mayen',
    'sk': 'slovakia',
    'sl': 'sierra leone',
    'sm': 'san marino',
    'sn': 'senegal',
    'so': 'somalia',
    'sr': 'suriname',
    'st': 'sao tome and principe',
    'sv': 'el salvador',
    'sy': 'syrian arab republic',
    'sz': 'swaziland',
    'tc': 'turks and caicos islands',
    'td': 'chad',
    'tf': 'french southern territories',
    'tg': 'togo',
    'th': 'thailand',
    'tj': 'tajikistan',
    'tk': 'tokelau',
    'tl': 'timor-leste',
    'tm': 'turkmenistan',
    'to': 'tonga',
    'tr': 'turkey',
    'tt': 'trinidad and tobago',
    'tv': 'tuvalu',
    'tw': 'taiwan',
    'tz': 'tanzania',
    'ua': 'ukraine',
    'ug': 'uganda',
    'um': 'united states minor outlying islands',
    'uy': 'uruguay',
    'uz': 'uzbekistan',
    'vc': 'saint vincent and the grenadines',
    've': 'venezuela, bolivarian republic of',
    'vg': 'virgin islands, british',
    'vi': 'virgin islands, u.s.',
    'vn': 'viet nam',
    'vu': 'vanuatu',
    'wf': 'wallis and futuna',
    'ws': 'samoa',
    'ye': 'yemen',
    'yt': 'mayotte',
    'za': 'south africa',
    'zm': 'zambia',
    'zw': 'zimbabwe'
}

_conflictingShortforms = {
    'al': 'albania',
    'ar': 'argentina',
    'az': 'azerbaijan',
    'ca': 'canada',
    'co': 'colombia',
    'de': 'germany',
    'ga': 'gabon',
    'id': 'indonesia',
    'il': 'israel',
    'in': 'india',
    'ky': 'cayman islands',
    'la': 'laos',
    'ma': 'morocco',
    'md': 'moldova',
    'me': 'montenegro',
    'mn': 'mongolia',
    'mo': 'macao',
    'ms': 'montserrat',
    'mt': 'malta',
    'nc': 'new caledonia',
    'ne': 'niger',
    'pa': 'panama',
    'sc': 'seychelles',
    'sd': 'sudan',
    'tn': 'tunisia',
    'va': 'vatican city'
}

def checkShortforms(query): # being Canadian, I often use something like "Toronto, ON"
                            # but wunderground needs "Toronto, Ontario"
    if ' ' not in query and ',' not in query:
        return query # if there's no spaces or commas, it's one word, no need to check for provinces
    
    lastWord = query.split()[-1].lower() # split by spaces, see if the last word is a province shortform
    if lastWord in _shortforms:
        return (query[0:0 - len(lastWord)] + _shortforms[lastWord]).encode(encoding)
    
    lastWord = query.split(',')[-1].lower() # if it's not separated by spaces, maybe commas
    if lastWord in _shortforms:
        return (query[0:0 - len(lastWord)] + _shortforms[lastWord]).encode(encoding)
    
    return query # nope, probably not a province name, return original query

def checkConflictingShortforms(query):
    if ' ' not in query and ',' not in query:
        return None
    
    lastWord = query.split()[-1].lower()
    if lastWord in _conflictingShortforms:
        return (query[0:0 - len(lastWord)] + _conflictingShortforms[lastWord]).encode(encoding)
    
    lastWord = query.split(',')[-1].lower()
    if lastWord in _conflictingShortforms:
        return (query[0:0 - len(lastWord)] + _conflictingShortforms[lastWord]).encode(encoding)
    
    return None

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2005, James Vega
# Copyright (c) 2009 Michael Tughan
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

from supybot.test import *

class WeatherTestCase(PluginTestCase):
    plugins = ('WunderWeather',)
    if network:
        def testWeather(self):
            self.assertNotError('weather Columbus, OH')
            self.assertNotError('weather 43221')
            self.assertNotRegexp('weather Paris, FR', 'Virginia')
            self.assertError('weather alsdkfjasdl, asdlfkjsadlfkj')
            self.assertNotError('weather London, uk')
            self.assertNotError('weather London, UK')
            self.assertNotError('weather London, england')
            self.assertNotError('weather Munich, de')
            self.assertNotError('weather Munich, germany')
            self.assertNotError('weather Tucson, AZ')
            # "Multiple locations found" test
            self.assertNotError('weather hell')
            self.assertNotError('weather sandwich')


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
