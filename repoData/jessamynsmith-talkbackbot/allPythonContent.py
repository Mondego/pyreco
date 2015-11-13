__FILENAME__ = bot
import logging

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol

from quotation_selector import QuotationSelector


class TalkBackBot(irc.IRCClient):

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        logging.info("connectionMade")

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        logging.info("connectionLost")

    # callbacks for events

    def signedOn(self):
        """Called when bot has successfully signed on to server."""
        logging.info("Signed on")
        self.join(self.factory.channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        logging.info("[%s has joined %s]"
            % (self.nickname, self.factory.channel))

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        
        trigger_found = False
        send_to = channel
        if self.factory.settings.NICKNAME.startswith(channel) or \
                channel.startswith(self.factory.settings.NICKNAME):
            trigger_found = True
            send_to = user.split('!')[0]
        else:
            for trigger in self.factory.settings.TRIGGERS:
                if msg.lower().find(trigger) >= 0:
                    trigger_found = True
                    break

        if trigger_found:
            quote = self.factory.quotation.select()
            self.msg(send_to, quote)
            logging.info("sent message to %s:\n\t%s" % (send_to, quote))


class TalkBackBotFactory(protocol.ClientFactory):

    def __init__(self, settings):
        self.settings = settings
        self.channel = self.settings.CHANNEL
        self.quotation = QuotationSelector(self.settings.QUOTES_FILE)

    def buildProtocol(self, addr):
        bot = TalkBackBot()
        bot.factory = self
        bot.nickname = self.settings.NICKNAME
        bot.realname = self.settings.REALNAME
        return bot

    def clientConnectionLost(self, connector, reason):
        logging.info("connection lost, reconnecting")
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        logging.info("connection failed: %s" % (reason))
        reactor.stop()
########NEW FILE########
__FILENAME__ = quotation_selector
from random import choice


class QuotationSelector(object):

    def __init__(self, quotes_filename):
        with open(quotes_filename) as quotes_file:
            self.quotes = quotes_file.readlines()

    def select(self):
        return choice(self.quotes).strip()
########NEW FILE########
__FILENAME__ = test_quotation_selector
import os
import unittest

from talkback.quotation_selector import QuotationSelector

class TestQuotationSelector(unittest.TestCase):

    QUOTE1 = "A fool without fear is sometimes wiser than an angel with fear. ~ Nancy Astor"
    QUOTE2 = "You don't manage people, you manage things. You lead people. ~ Grace Hopper"

    def setUp(self):
        super(TestQuotationSelector, self).setUp()

    def test_select(self):
        selector = QuotationSelector(os.path.join(os.getcwd(),
            "tests/test_quotes.txt"))

        quote = selector.select()

        self.assertTrue(quote in (self.QUOTE1, self.QUOTE2),
            "Got unexpected quote: '%s'" % (quote))
########NEW FILE########
__FILENAME__ = test_settings
# IRC settings
HOST = "test.example.com"
PORT = 6667
USE_SSL = False
NICKNAME = "shesaidbot"
REALNAME = "bot: provides quotations from notable women"

CHANNEL = "#test"

# Trigger phrases, in lowercase
TRIGGERS = (
    "twss",
    )

# Process settings
LOG_FILE = "./talkbackbot.log"
QUOTES_FILE = "tests/test_quote.txt"
########NEW FILE########
__FILENAME__ = test_talkbackbot
import unittest
import mock

from talkback.bot import TalkBackBotFactory
import test_settings

class TestTalkBackBot(unittest.TestCase):
    
    CHANNEL = "#testchannel"
    QUOTE = "Nobody minds having what is too good for them. ~ Jane Austen"
    USERNAME = "tester"

    def setUp(self):
        super(TestTalkBackBot, self).setUp()
        factory = TalkBackBotFactory(test_settings)
        self.bot = factory.buildProtocol(None)
        self.bot.msg = mock.MagicMock()

    def test_privmsg__no_trigger(self):
        """Shouldn't send a quote if message does not match trigger"""
        self.bot.privmsg(self.USERNAME, self.CHANNEL, "hi")
        self.assertFalse(self.bot.msg.called)

    def test_privmsg__with_trigger(self):
        """Should send a quote if message matches trigger"""
        self.bot.privmsg(self.USERNAME, self.CHANNEL, "twss")
        self.bot.msg.assert_called_with(self.CHANNEL, self.QUOTE)

    def test_privmsg__private_message(self):
        """ For private messages, should send quote directly to user """
        self.bot.privmsg(self.USERNAME, test_settings.NICKNAME, "hi")
        self.bot.msg.assert_called_with(self.USERNAME, self.QUOTE)

    def test_privmsg__private_message_truncated_nickname(self):
        """ Send quote directly to user even if name is truncated """
        self.bot.privmsg(self.USERNAME, test_settings.NICKNAME[:-2], "hi")
        self.bot.msg.assert_called_with(self.USERNAME, self.QUOTE)

    def test_privmsg__private_message_alternate_nickname(self):
        """ Send quote directly to user even if using alternate nickname """
        self.bot.privmsg(self.USERNAME, test_settings.NICKNAME + '_', "hi")
        self.bot.msg.assert_called_with(self.USERNAME, self.QUOTE)
        
########NEW FILE########
__FILENAME__ = talkbackbot_plugin
#!/usr/bin/env python
import logging

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet
from twisted.internet import ssl

from zope.interface import implements

import settings
from talkback.bot import TalkBackBotFactory

logging.basicConfig(filename=settings.LOG_FILE, level=logging.DEBUG)


class Options(usage.Options):
    optParameters = []


class BotServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "twsrs"
    description = "IRC bot that provides quotations from notable women"
    options = Options

    def makeService(self, options):
        """
        Construct the talkbackbot TCP client
        """
        if settings.USE_SSL:
            bot = internet.SSLClient(settings.HOST, settings.PORT,
                TalkBackBotFactory(settings), ssl.ClientContextFactory())
        else:
            bot = internet.TCPClient(settings.HOST, settings.PORT,
                TalkBackBotFactory(settings))
        return bot


# Now construct an object which *provides* the relevant interfaces
# The name of this variable is irrelevant, as long as there is *some*
# name bound to a provider of IPlugin and IServiceMaker.

serviceMaker = BotServiceMaker()
########NEW FILE########
