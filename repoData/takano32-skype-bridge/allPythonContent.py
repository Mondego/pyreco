__FILENAME__ = chat_list
#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
# encoding: utf-8

import Skype4Py
import time
import pprint
import os

os.environ['DISPLAY'] = ":64"
os.environ['XAUTHORITY'] = "/var/www/.Xauthority"
pp = pprint.PrettyPrinter(indent = 4)

def handler(msg, event):
    if event == u"RECEIVED":
        # pp.pprint(msg.Sender.FullName)
        # print ""
        print "ChatName %s" % msg.ChatName
        print "Body %s" % msg.Body
        print ""

def chat_list():
    skype = Skype4Py.Skype()
    skype.OnMessageStatus = handler
    skype.Attach()
    while True:
        time.sleep(1)

class MergeList:
    pass

def main():
    chat_list()

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = config
from configobj import ConfigObj

config = ConfigObj()
config.filename = "skype-lingr.conf"

config['lingr'] = {'verifier': 'hoge'}

config['arakawatomonori'] = {'skype': '#yuiseki/$4425ae72bc11c305', 'lingr': 'arakawatomonori'}
config['pirate'] = {'skype': 'foo', 'lingr': 'pirate'}
# config.write()

config = ConfigObj("skype-lingr.conf")

import pprint
pp = pprint.PrettyPrinter(indent = 4)

pp.pprint(config)
print config['arakawatomonori']['lingr']

for key in config:
	if key == 'lingr' or key == 'skype':
		continue
	print config[key]['skype']
	print config[key]['lingr']



########NEW FILE########
__FILENAME__ = emoticons
# -*- coding: utf-8 -*-

shortcodes = [
    [u':)', 100],
    [u':=)', 100],
    [u':-)', 100],
    [u':(', 101],
    [u':=(', 101],
    [u':-(', 101],
    [u':D', 102],
    [u':=D', 102],
    [u':-D', 102],
    [u':d', 102],
    [u':=d', 102],
    [u':-d', 102],
    [u'8)', 103],
    [u'8=)', 103],
    [u'8-)', 103],
    [u'B)', 103],
    [u'B=)', 103],
    [u'B-)', 103],
    [u'(cool)', 103],
    [u':o', 105],
    [u':=o', 105],
    [u':-o', 105],
    [u':O', 105],
    [u':=O', 105],
    [u':-O', 105],
    [u';(', 106],
    [u';-(', 106],
    [u';=(', 106],
    [u'(sweat)', 107],
    [u'(:|', 107],
    [u':|', 108],
    [u':=|', 108],
    [u':-|', 108],
    [u':*', 109],
    [u':=*', 109],
    [u':-*', 109],
    [u':P', 110],
    [u':=P', 110],
    [u':-P', 110],
    [u':p', 110],
    [u':=p', 110],
    [u':-p', 110],
    [u'(blush)', 111],
    [u':$', 111],
    [u':-$', 111],
    [u':=$', 111],
    [u':">', 111],
    [u':^)', 112],
    [u'|-)', 113],
    [u'I-)', 113],
    [u'I=)', 113],
    [u'(snooze)', 113],
    [u'|(', 114],
    [u'|-(', 114],
    [u'|=(', 114],
    [u'(inlove)', 115],
    [u']:)', 116],
    [u'>:)', 116],
    [u'(grin)', 116],
    [u'(talk)', 117],
    [u'(yawn)', 118],
    [u'|-()', 118],
    [u'(puke)', 119],
    [u':&', 119],
    [u':-&', 119],
    [u':=&', 119],
    [u'(doh)', 120],
    [u':@', 121],
    [u':-@', 121],
    [u':=@', 121],
    [u'x(', 121],
    [u'x-(', 121],
    [u'x=(', 121],
    [u'X(', 121],
    [u'X-(', 121],
    [u'X=(', 121],
    [u'(wasntme)', 122],
    [u'(party)', 123],
    [u':S', 124],
    [u':-S', 124],
    [u':=S', 124],
    [u':s', 124],
    [u':-s', 124],
    [u':=s', 124],
    [u'(mm)', 125],
    [u'8-|', 126],
    [u'B-|', 126],
    [u'8|', 126],
    [u'B|', 126],
    [u'8=|', 126],
    [u'B=|', 126],
    [u'(nerd)', 126],
    [u':x', 127],
    [u':-x', 127],
    [u':X', 127],
    [u':-X', 127],
    [u':#', 127],
    [u':-#', 127],
    [u':=x', 127],
    [u':=X', 127],
    [u':=#', 127],
    [u'(hi)', 128],
    [u'(call)', 129],
    [u'(devil)', 130],
    [u'(angel)', 131],
    [u'(envy)', 132],
    [u'(wait)', 133],
    [u'(bear)', 134],
    [u'(hug)', 134],
    [u'(makeup)', 135],
    [u'(kate)', 135],
    [u'(giggle)', 136],
    [u'(chuckle)', 136],
    [u'(clap)', 137],
    [u'(think)', 138],
    [u':?', 138],
    [u':-?', 138],
    [u':=?', 138],
    [u'(bow)', 139],
    [u'(rofl)', 140],
    [u'(whew)', 141],
    [u'(happy)', 142],
    [u'(smirk)', 143],
    [u'(nod)', 144],
    [u'(shake)', 145],
    [u'(punch)', 146],
    [u'(emo)', 147],
    [u'(y)', 148],
    [u'(Y)', 148],
    [u'(ok)', 148],
    [u'(n)', 149],
    [u'(N)', 149],
    [u'(handshake)', 150],
    [u'(skype)', 151],
    [u'(ss)', 151],
    [u'(h)', 152],
    [u'(H)', 152],
    [u'(l)', 152],
    [u'(L)', 152],
    [u'(u)', 153],
    [u'(U)', 153],
    [u'(e)', 154],
    [u'(m)', 154],
    [u'(f)', 155],
    [u'(F)', 155],
    [u'(rain)', 156],
    [u'(london)', 156],
    [u'(st)', 156],
    [u'(sun)', 157],
    [u'(o)', 158],
    [u'(O)', 158],
    [u'(time)', 158],
    [u'(music)', 159],
    [u'(~)', 160],
    [u'(film)', 160],
    [u'(movie)', 160],
    [u'(mp)', 161],
    [u'(ph)', 161],
    [u'(coffee)', 162],
    [u'(pizza)', 163],
    [u'(pi)', 163],
    [u'(cash)', 164],
    [u'(mo)', 164],
    [u'($)', 164],
    [u'(muscle)', 165],
    [u'(flex)', 165],
    [u'(^)', 166],
    [u'(cake)', 166],
    [u'(beer)', 167],
    [u'(d)', 168],
    [u'(D)', 168],
    [u'(dance)', 169],
    [u'\o/', 169],
    [u'\:D/', 169],
    [u'\:d/', 169],
    [u'(ninja)', 170],
    [u'(*)', 171],
    [u'(mooning)', 172],
    [u'(finger)', 173],
    [u'(bandit)', 174],
    [u'(drunk)', 175],
    [u'(smoking)', 176],
    [u'(smoke)', 176],
    [u'(ci)', 176],
    [u'(toivo)', 177],
    [u'(rock)', 178],
    [u'(headbang)', 179],
    [u'(banghead)', 179],
    [u'(bug)', 180],
    [u'(fubar)', 181],
    [u'(poolparty)', 182],
    [u'(swear)', 183],
    [u'(tmi)', 184],
    [u'(heidy)', 185],
    [u'(MySpace)', 186]]


emoji_map = {
    100: [u'Smile', u'emoticon-0100-smile.gif'],
    101: [u'Sad Smile', u'emoticon-0101-sadsmile.gif'],
    102: [u'Big Smile', u'emoticon-0102-bigsmile.gif'],
    103: [u'Cool', u'emoticon-0103-cool.gif'],
    105: [u'Wink', u'emoticon-0105-wink.gif'],
    106: [u'Crying', u'emoticon-0106-crying.gif'],
    107: [u'Sweating', u'emoticon-0107-sweating.gif'],
    108: [u'Speechless', u'emoticon-0108-speechless.gif'],
    109: [u'Kiss', u'emoticon-0109-kiss.gif'],
    110: [u'Tongue Out', u'emoticon-0110-tongueout.gif'],
    111: [u'Blush', u'emoticon-0111-blush.gif'],
    112: [u'Wondering', u'emoticon-0112-wondering.gif'],
    113: [u'Sleepy', u'emoticon-0113-sleepy.gif'],
    114: [u'Dull', u'emoticon-0114-dull.gif'],
    115: [u'In love', u'emoticon-0115-inlove.gif'],
    116: [u'Evil grin', u'emoticon-0116-evilgrin.gif'],
    117: [u'Talking', u'emoticon-0117-talking.gif'],
    118: [u'Yawn', u'emoticon-0118-yawn.gif'],
    119: [u'Puke', u'emoticon-0119-puke.gif'],
    120: [u'Doh!', u'emoticon-0120-doh.gif'],
    121: [u'Angry', u'emoticon-0121-angry.gif'],
    122: [u"It wasn't me", u'emoticon-0122-itwasntme.gif'],
    123: [u'Party!!!', u'emoticon-0123-party.gif'],
    124: [u'Worried', u'emoticon-0124-worried.gif'],
    125: [u'Mmm...', u'emoticon-0125-mmm.gif'],
    126: [u'Nerd', u'emoticon-0126-nerd.gif'],
    127: [u'Lips Sealed', u'emoticon-0127-lipssealed.gif'],
    128: [u'Hi', u'emoticon-0128-hi.gif'],
    129: [u'Call', u'emoticon-0129-call.gif'],
    130: [u'Devil', u'emoticon-0130-devil.gif'],
    131: [u'Angel', u'emoticon-0131-angel.gif'],
    132: [u'Envy', u'emoticon-0132-envy.gif'],
    133: [u'Wait', u'emoticon-0133-wait.gif'],
    134: [u'Bear', u'emoticon-0134-bear.gif'],
    135: [u'Make-up', u'emoticon-0135-makeup.gif'],
    136: [u'Covered Laugh', u'emoticon-0136-giggle.gif'],
    137: [u'Clapping Hands', u'emoticon-0137-clapping.gif'],
    138: [u'Thinking', u'emoticon-0138-thinking.gif'],
    139: [u'Bow', u'emoticon-0139-bow.gif'],
    140: [u'Rolling on the floor laughing', u'emoticon-0140-rofl.gif'],
    141: [u'Whew', u'emoticon-0141-whew.gif'],
    142: [u'Happy', u'emoticon-0142-happy.gif'],
    143: [u'Smirking', u'emoticon-0143-smirk.gif'],
    144: [u'Nodding', u'emoticon-0144-nod.gif'],
    145: [u'Shaking', u'emoticon-0145-shake.gif'],
    146: [u'Punch', u'emoticon-0146-punch.gif'],
    147: [u'Emo', u'emoticon-0147-emo.gif'],
    148: [u'Yes', u'emoticon-0148-yes.gif'],
    149: [u'No', u'emoticon-0149-no.gif'],
    150: [u'Shaking Hands', u'emoticon-0150-handshake.gif'],
    151: [u'Skype', u'emoticon-0151-skype.gif'],
    152: [u'Heart', u'emoticon-0152-heart.gif'],
    153: [u'Broken heart', u'emoticon-0153-brokenheart.gif'],
    154: [u'Mail', u'emoticon-0154-mail.gif'],
    155: [u'Flower', u'emoticon-0155-flower.gif'],
    156: [u'Rain', u'emoticon-0156-rain.gif'],
    157: [u'Sun', u'emoticon-0157-sun.gif'],
    158: [u'Time', u'emoticon-0158-time.gif'],
    159: [u'Music', u'emoticon-0159-music.gif'],
    160: [u'Movie', u'emoticon-0160-movie.gif'],
    161: [u'Phone', u'emoticon-0161-phone.gif'],
    162: [u'Coffee', u'emoticon-0162-coffee.gif'],
    163: [u'Pizza', u'emoticon-0163-pizza.gif'],
    164: [u'Cash', u'emoticon-0164-cash.gif'],
    165: [u'Muscle', u'emoticon-0165-muscle.gif'],
    166: [u'Cake', u'emoticon-0166-cake.gif'],
    167: [u'Beer', u'emoticon-0167-beer.gif'],
    168: [u'Drink', u'emoticon-0168-drink.gif'],
    169: [u'Dance', u'emoticon-0169-dance.gif'],
    170: [u'Ninja', u'emoticon-0170-ninja.gif'],
    171: [u'Star', u'emoticon-0171-star.gif'],
    172: [u'Mooning', u'emoticon-0172-mooning.gif'],
    173: [u'Finger', u'emoticon-0173-middlefinger.gif'],
    174: [u'Bandit', u'emoticon-0174-bandit.gif'],
    175: [u'Drunk', u'emoticon-0175-drunk.gif'],
    176: [u'Smoking', u'emoticon-0176-smoke.gif'],
    177: [u'Toivo', u'emoticon-0177-toivo.gif'],
    178: [u'Rock', u'emoticon-0178-rock.gif'],
    179: [u'Headbang', u'emoticon-0179-headbang.gif'],
    180: [u'Bug', u'emoticon-0180-bug.gif'],
    181: [u'Fubar', u'emoticon-0181-fubar.gif'],
    182: [u'Poolparty', u'emoticon-0182-poolparty.gif'],
    183: [u'Swearing', u'emoticon-0183-swear.gif'],
    184: [u'TMI', u'emoticon-0184-tmi.gif'],
    185: [u'Heidy', u'emoticon-0185-heidy.gif'],
    186: [u'MySpace', u'emoticon-0186-myspace.gif']
}


def get_value(id):
    return emoji_map.get(id)


def get_name(id):
    value = get_value(id)
    if value == None:
        return None

    try:
        name = value[0]
        return name
    except IndexError, e:
        raise e


def get_gif_name(id):
    value = get_value(id)
    if value == None:
        return None

    try:
        name = value[1]
        return name
    except IndexError, e:
        raise e


def shortcode(text):
    for pair in shortcodes:
        pattern = pair[0]
        id = pair[1]
        gif_name = get_gif_name(id)
        url = u'\nhttp://factoryjoe.s3.amazonaws.com/emoticons/%s\n' % gif_name
        text = text.replace(pattern, url)
    return text


#if __name__ == '__main__':
#    print(shortcode(':-)'))
#    print(shortcode('xxx :-) xxx:-(xxx'))

########NEW FILE########
__FILENAME__ = headline
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32
#

import sys
#sys.path.append('/usr/lib/pymodules/python2.5')
#sys.path.append('/usr/lib/pymodules/python2.5/gtk-2.0')

import os
os.environ['DISPLAY'] = ":32"
os.environ['XAUTHORITY'] = "/home/takano32/.Xauthority"

ROOM="#yuiseki/$4425ae72bc11c305"

import Skype4Py

import feedparser
d = feedparser.parse("http://pipes.yahoo.com/pipes/pipe.run?_id=8f34c1abdb8fc99e9aa057fac8e510e1&_render=rss")

def handler(msg, event):
	pass

skype = Skype4Py.Skype()
skype.OnMessageStatus = handler
skype.Attach()

room = skype.Chat(ROOM)

for item in d['items'][:5]:
    text = item.title + "\n" + item.link
	room.SendMessage(text)



########NEW FILE########
__FILENAME__ = chat_list
#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
# encoding: utf-8

import Skype4Py
import time
import pprint
import os

os.environ['DISPLAY'] = ":16"
pp = pprint.PrettyPrinter(indent = 4)

def handler(msg, event):
    if event == u"RECEIVED":
        print "ChatName %s" % msg.ChatName
        print "Body %s" % msg.Body
        print ""

def chat_list():
    skype = Skype4Py.Skype()
    skype.OnMessageStatus = handler
    skype.Attach()
    while True:
        time.sleep(1)

class MergeList:
    pass

def main():
    chat_list()

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = irc2skype
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak@no32 dot tk>
#

import sys
import os
import Skype4Py
import pprint
import time
import threading
import xmlrpclib
from configobj import ConfigObj

os.environ['DISPLAY'] = ":16"
os.environ['XAUTHORITY'] = "/home/takano32/.Xauthority"

pp = pprint.PrettyPrinter(indent = 4)

SERVER = "irc.freenode.net"
PORT = 6667
WAIT = None
NICKNAME = "to_skype"

from ircbot import SingleServerIRCBot
from irclib import nm_to_n

config = ConfigObj("skype-bridge.conf")

if config.has_key('irc') and config['irc'].has_key('server'):
	SERVER = config['irc']['server']

if config.has_key('irc') and config['irc'].has_key('port'):
	PORT = int(config['irc']['port'])

if config.has_key('irc') and config['irc'].has_key('wait'):
	WAIT = float(config['irc']['wait'])

class FromIrcToSkype(SingleServerIRCBot):
	def __init__(self, skype, server = SERVER):
		SingleServerIRCBot.__init__(self, [(SERVER, PORT)], NICKNAME, NICKNAME)
		xmlrpc_host = config['skype']['xmlrpc_host']
		xmlrpc_port = config['skype']['xmlrpc_port']
		self.skype = xmlrpclib.ServerProxy('http://%s:%s' % (xmlrpc_host, xmlrpc_port))
		self.channel = "#takano32bot"

	def on_nicknameinuse(self, c, e):
		c.nick(c.get_nickname() + "_")

	def on_welcome(self, c, e):
		c.join(self.channel)
		for key in config:
			if key == 'skype' or key == 'irc':
				continue
			if config[key].has_key('irc'):
				channel = config[key]['irc']
				c.join(channel)

	def say(self, channel, msg):
		self.connection.privmsg(channel, msg)

	def notice(self, channel, msg):
		self.connection.notice(channel, msg)

	def do_command(self, c, e):
		try:
			msg = unicode(e.arguments()[0], "utf8")
			self.say(self.channel, msg.encode('utf-8'))
		except UnicodeDecodeError, err:
			print "UnicodeDecodeError occured"
			return

	def skype_handler_for_pubmsg(self, c, e):
		return self.skype_handler(c, e, True)

	def skype_handler_for_pubnotice(self, c, e):
		return self.skype_handler(c, e, True)

	def skype_handler(self, c, e, notice = False):
		nick = e.nick = nm_to_n(e.source())
		if nick.startswith(u'skype'): return
		try:
			msg = unicode(e.arguments()[0], "utf8")
		except UnicodeDecodeError, err:
			print "UnicodeDecodeError occured"
			return
		for key in config:
			if key == 'skype' or key == 'irc':
				continue
			if config[key].has_key('irc2skype'):
				if config[key]['irc2skype'].title() == 'False':
					continue
			if config[key].has_key('irc'):
				channel = config[key]['irc']
				if channel == e.target():
					room = config[key]['skype']
					self.send_message(room, nick, msg, notice)

	def send_message(self, room, nick, msg, notice = False):
		try:
			if not notice and msg.startswith(u'@'):
				self.skype.send_message(room, msg)
				notice = '# %s is issuing the above command.' % nick
				self.skype.send_message(room, notice)
				return
			text = '%s: %s' % (nick, msg)
			self.skype.send_message(room, text)
		except xmlrpclib.Fault, err:
			print "A fault occurred"
			print "Fault code: %d" % err.faultCode
			print "Fault string: %s" % err.faultString
			#print "Skype4Py.errors.ISkypeError"
			return

	on_pubnotice = skype_handler_for_pubnotice
	on_privnotice = do_command
	on_pubmsg = skype_handler_for_pubmsg
	on_privmsg = do_command

def skype_handler(msg, event):
	pass

skype = Skype4Py.Skype()
skype.OnMessageStatus = skype_handler
skype.Attach()
# skype.ClearChatHistory()
# skype.ResetCache()

time.sleep(3)

bridge = FromIrcToSkype(skype)
bridge.start()


########NEW FILE########
__FILENAME__ = irc_skype_bridge
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak at no32.tk>
#

from ircbot import SingleServerIRCBot
from irclib import nm_to_n
from configobj import ConfigObj
from SimpleXMLRPCServer import SimpleXMLRPCServer

import sys, xmlrpclib

CONFIG = ConfigObj("bridge.conf")
SERVER = 'irc.freenode.net'
PORT = 6667
NICKNAME = 'skype2'

class IrcSkypeBridge(SingleServerIRCBot):
	def __init__(self, server = SERVER):
		self.channel = '#takano32bot'
		SingleServerIRCBot.__init__(self, [(SERVER, PORT)], NICKNAME, NICKNAME)

		xmlrpc_host = CONFIG['skype']['xmlrpc_host']
		xmlrpc_port = CONFIG['skype']['xmlrpc_port']
		self.skype = xmlrpclib.ServerProxy('http://%s:%s' % (xmlrpc_host, xmlrpc_port))

	def on_nicknameinuse(self, c, e):
		c.nick(c.get_nickname() + "_")

	def on_welcome(self, c, e):
		c.join(self.channel)
		for key in CONFIG:
			if key == 'skype' or key == 'irc':
				continue
			if CONFIG[key].has_key('irc'):
				channel = CONFIG[key]['irc']
				c.join(channel)

	def say(self, channel, msg):
		self.connection.privmsg(channel, msg)
		return True

	def do_command(self, c, e):
		msg = unicode(e.arguments()[0], "utf8")
		self.say(self.channel, msg.encode('utf-8'))

	def handler(self, c, e):
		e.nick = nm_to_n(e.source())
		msg = unicode(e.arguments()[0], "utf8")
		text = '%s: %s' % (e.nick, msg)
		for key in CONFIG:
			if key == 'skype' or key == 'irc':
				continue
			if CONFIG[key].has_key('irc'):
				channel = CONFIG[key]['irc']
				if channel == e.target():
					self.skype.say(CONFIG[key]['skype'], text)

	on_pubnotice = do_command
	on_privnotice = do_command
	on_pubmsg = handler
	on_privmsg = do_command

if __name__ == "__main__":
	host = CONFIG['irc']['xmlrpc_host']
	port = CONFIG['irc']['xmlrpc_port']
	sv = SimpleXMLRPCServer((host, int(port)))
	bridge = IrcSkypeBridge()
	bridge.start()
	sv.register_instance(bridge)
	sv.serve_forever()


########NEW FILE########
__FILENAME__ = messagesender
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak at no32.tk>
#

from configobj import ConfigObj
import sys, xmlrpclib

CONFIG = ConfigObj("skype-bridge.conf")

xmlrpc_host = CONFIG['skype']['xmlrpc_host']
xmlrpc_port = CONFIG['skype']['xmlrpc_port']
sendmessage = xmlrpclib.ServerProxy('http://%s:%s' % (xmlrpc_host, xmlrpc_port))

room = '#takano32/$mitsuhiro.takano;46c33855977e8974'
sendmessage.send_message(room, 'hogefuga')


########NEW FILE########
__FILENAME__ = sendmessage
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak at no32.tk>
#

import Skype4Py
from configobj import ConfigObj
from SimpleXMLRPCServer import SimpleXMLRPCServer
import threading
import os

os.environ['DISPLAY'] = ":16"
os.environ['XAUTHORITY'] = "/home/takano32/.Xauthority"

CONFIG = ConfigObj("skype-bridge.conf")

class SendMessage():
	def __init__(self):
		self.skype = Skype4Py.Skype()
		self.skype.Attach()
		self.lock = threading.Lock()

	def send_message(self, room, msg):
		with self.lock:
			room = self.skype.Chat(room)
			room.SendMessage(msg)
		return True

if __name__ == "__main__":
	host = CONFIG['skype']['xmlrpc_host']
	port = CONFIG['skype']['xmlrpc_port']
	sv = SimpleXMLRPCServer((host, int(port)))
	sv.register_instance(SendMessage())
	sv.serve_forever()


########NEW FILE########
__FILENAME__ = skype-irc-bridge
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# http://d.hatena.ne.jp/nishiohirokazu/20071203/1196670766
#

import sys
#sys.path.append('/usr/lib/pymodules/python2.5')
#sys.path.append('/usr/lib/pymodules/python2.5/gtk-2.0')
import os
import Skype4Py
import time
import pprint
from configobj import ConfigObj

pp = pprint.PrettyPrinter(indent = 4)

SERVER = "irc.freenode.net"
PORT = 6667
WAIT = None
CHANNEL = "#takano32bot"
NICKNAME = "skype"
COLOR_TAG = "\x0310" #aqua
REVERSE_TAG = "\x16" #reverse
NORMAL_TAG = "\x0F" #normal
COLOR_TAG = "" #none


from ircbot import SingleServerIRCBot
from irclib import nm_to_n

config = ConfigObj("skype-irc-bridge.conf")

if config.has_key('irc') and config['irc'].has_key('server'):
	SERVER = config['irc']['server']

if config.has_key('irc') and config['irc'].has_key('port'):
	PORT = int(config['irc']['port'])

if config.has_key('irc') and config['irc'].has_key('wait'):
	WAIT = float(config['irc']['wait'])

def skype_handler(msg, event):
	if len(msg.Body) == 0:
		return
	if event == u"RECEIVED":
		for key in config:
			if key == 'lingr' or key == 'skype' or key == 'irc':
				continue
			if config[key].has_key('skype') and msg.ChatName == config[key]['skype']:
				name = msg.Sender.FullName
				if len(name) == 0 or len(name) > 16:
					name = msg.Sender.Handle
				if config[key].has_key('irc'):
					channel = config[key]['irc']
					for line in msg.Body.splitlines():
						if name == 'Lingr':
							text = line
						else:
							text = '%s: %s' % (name, line)
						bridge.say(channel, text.encode('utf-8'))
						if WAIT != None:
							time.sleep(WAIT)
						else:
							time.sleep(len(text) / 20.0)

class SkypeIRCBridge(SingleServerIRCBot):
	def __init__(self, skype, server = SERVER):
		SingleServerIRCBot.__init__(self, [(SERVER, PORT)], NICKNAME, NICKNAME)
		self.skype = skype
		self.channel = CHANNEL

	def on_nicknameinuse(self, c, e):
		c.nick(c.get_nickname() + "_")

	def on_welcome(self, c, e):
		c.join(self.channel)
		for key in config:
			if key == 'lingr' or key == 'skype' or key == 'irc':
				continue
			if config[key].has_key('irc'):
				channel = config[key]['irc']
				c.join(channel)

	def say(self, channel, msg):
		self.connection.privmsg(channel, COLOR_TAG + msg)

	def do_command(self, c, e):
		msg = unicode(e.arguments()[0], "utf8")
		self.say(self.channel, msg.encode('utf-8'))

	def skype_handler(self, c, e):
		e.nick = nm_to_n(e.source())
		msg = unicode(e.arguments()[0], "utf8")
		text = '%s: %s' % (e.nick, msg)
		for key in config:
			if key == 'lingr' or key == 'skype' or key == 'irc':
				continue
			if config[key].has_key('irc'):
				channel = config[key]['irc']
				if channel == e.target():
					room = self.skype.Chat(config[key]['skype'])
					room.SendMessage(text)

	on_pubnotice = do_command
	on_privnotice = do_command
	on_pubmsg = skype_handler
	on_privmsg = do_command

skype = Skype4Py.Skype()
skype.OnMessageStatus = skype_handler
skype.Attach()

for key in config:
	if key == 'lingr' or key == 'skype' or key == 'irc':
		continue
	if config[key].has_key('irc'):
		channel = config[key]['irc']
		room = config[key]['skype']
		bridge = SkypeIRCBridge(skype)
		bridge.start()


########NEW FILE########
__FILENAME__ = skype2irc
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak@no32 dot tk>
#

import sys
import os
import Skype4Py
import pprint
import time
import threading
import xmlrpclib
from configobj import ConfigObj

os.environ['DISPLAY'] = ":16"
os.environ['XAUTHORITY'] = "/home/takano32/.Xauthority"

pp = pprint.PrettyPrinter(indent = 4)

SERVER = "irc.freenode.net"
PORT = 6667
WAIT = None
NICKNAME = "skype"

from ircbot import SingleServerIRCBot
from irclib import nm_to_n

config = ConfigObj("skype-bridge.conf")

if config.has_key('irc') and config['irc'].has_key('server'):
	SERVER = config['irc']['server']

if config.has_key('irc') and config['irc'].has_key('port'):
	PORT = int(config['irc']['port'])

if config.has_key('irc') and config['irc'].has_key('wait'):
	WAIT = float(config['irc']['wait'])

bridge_lock = threading.Lock()

def skype_handler_without_lock(msg, event):
	try:
		skype_handler(msg, event)
	except Skype4Py.errors.ISkypeError, err:
		# print "A fault occurred"
		# print "Fault code: %d" % err.faultCode
		# print "Fault string: %s" % err.faultString
		print "Skype4Py.errors.ISkypeError occured"
		return


def skype_handler(msg, event):
	if len(msg.Body) == 0:
		return
	if event == u"RECEIVED":
		for key in config:
			if key == 'skype' or key == 'irc':
				continue
			if config[key].has_key('skype2irc'):
				if config[key]['skype2irc'].title() == 'False':
					continue
			if config[key].has_key('skype') and msg.ChatName == config[key]['skype']:
				name = msg.Sender.FullName
				if len(name) == 0 or len(name) > 16:
					name = msg.Sender.Handle
				if config[key].has_key('irc'):
					channel = config[key]['irc']
					send_message(channel, name, msg.Body)

def send_message(channel, name, msg):
	lines = msg.splitlines()
	if name.startswith('IRC'):
		return
	if len(lines) == 1 and msg.startswith('@'):
		text = lines[0]
		with bridge_lock:
			bridge.say(channel, text.encode('utf-8'))
		notice = '# %s is issuing the above command.' % name
		with bridge_lock:
			bridge.notice(channel, notice.encode('utf-8'))
		return
	for line in lines:
		texts = list()
		while 150 < len(line):
			text = '%s: %s' % (name, line[:150])
			texts.append(text)
			line = line[149:]
		text = '%s: %s' % (name, line)
		texts.append(text)
		for text in texts:
			with bridge_lock:
				bridge.say(channel, text.encode('utf-8'))
			if WAIT != None:
				time.sleep(WAIT)
			else:
				time.sleep(len(text) / 20.0)

class FromSkypeToIrc(SingleServerIRCBot):
	def __init__(self, server = SERVER):
		SingleServerIRCBot.__init__(self, [(SERVER, PORT)], NICKNAME, NICKNAME)
		self.channel = '#takano32bot'

	def on_nicknameinuse(self, c, e):
		c.nick(c.get_nickname() + "_")

	def on_welcome(self, c, e):
		c.join(self.channel)
		for key in config:
			if key == 'skype' or key == 'irc':
				continue
			if config[key].has_key('irc'):
				channel = config[key]['irc']
				c.join(channel)

	def say(self, channel, msg):
		self.connection.privmsg(channel, msg)

	def notice(self, channel, msg):
		self.connection.notice(channel, msg)

	def do_command(self, c, e):
		try:
			msg = unicode(e.arguments()[0], "utf8")
			self.say(self.channel, msg.encode('utf-8'))
		except UnicodeDecodeError, err:
			print "UnicodeDecodeError occured"


	on_pubnotice = do_command
	on_privnotice = do_command
	on_pubmsg = do_command
	on_privmsg = do_command

skype = Skype4Py.Skype()
skype.OnMessageStatus = skype_handler_without_lock
skype.Attach()
# skype.ClearChatHistory()
# skype.ResetCache()

time.sleep(3)

bridge = FromSkypeToIrc()
bridge.start()


########NEW FILE########
__FILENAME__ = skype_irc_bridge
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak at no32.tk>
#

import Skype4Py
import os
import time
from SimpleXMLRPCServer import SimpleXMLRPCServer
import sys, socket
from configobj import ConfigObj
import sys, xmlrpclib

os.environ['DISPLAY'] = ":16"
os.environ['XAUTHORITY'] = "/home/takano32/.Xauthority"

CONFIG = ConfigObj("bridge.conf")

class SkypeIrcBridge():
	xmlrpc_host = CONFIG['irc']['xmlrpc_host']
	xmlrpc_port = CONFIG['irc']['xmlrpc_port']
	irc = xmlrpclib.ServerProxy('http://%s:%s' % (xmlrpc_host, xmlrpc_port))
	def __init__(self):
		self.skype = Skype4Py.Skype()
		self.start()

	@staticmethod
	def handler(msg, event):
		if len(msg.Body) == 0:
			return
		if event == u"RECEIVED":
			for key in CONFIG:
				if key == 'skype' or key == 'irc':
					continue
				if CONFIG[key].has_key('skype') and msg.ChatName == CONFIG[key]['skype']:
					name = msg.Sender.FullName
					if len(name) == 0 or len(name) > 16:
						name = msg.Sender.Handle
					if CONFIG[key].has_key('irc'):
						channel = CONFIG[key]['irc']
						for line in msg.Body.splitlines():
							text = '%s: %s' % (name, line)
							print "before"
							SkypeIrcBridge.irc.say(channel, text.encode('utf-8'))
							print "after"
							if WAIT != None:
								time.sleep(WAIT)
							else:
								time.sleep(len(text) / 20.0)

	@staticmethod
	def inspect_handler(msg, event):
		if event == u"RECEIVED":
			print "ChatName %s" % msg.ChatName
			print "Body %s" % msg.Body
			print ""
#
	def say(self, channel, msg):
		room = self.skype.Chat(channel)
		room.SendMessage(msg)
		return True

	def start(self):
		self.skype.OnMessageStatus = SkypeIrcBridge.handler
		self.skype.Attach()

if __name__ == "__main__":
	host = CONFIG['skype']['xmlrpc_host']
	port = CONFIG['skype']['xmlrpc_port']
	sv = SimpleXMLRPCServer((host, int(port)))
	sv.register_instance(SkypeIrcBridge())
	sv.serve_forever()


########NEW FILE########
__FILENAME__ = chat_list
#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
# encoding: utf-8

import Skype4Py
import time
import pprint
import os

os.environ['DISPLAY'] = ":64"
os.environ['XAUTHORITY'] = "/var/www/.Xauthority"
pp = pprint.PrettyPrinter(indent = 4)

def handler(msg, event):
    if event == u"RECEIVED":
        # pp.pprint(msg.Sender.FullName)
        # print ""
        print "ChatName %s" % msg.ChatName
        print "Body %s" % msg.Body
        print ""

def chat_list():
    skype = Skype4Py.Skype()
    skype.OnMessageStatus = handler
    skype.Attach()
    while True:
        time.sleep(1)

class MergeList:
    pass

def main():
    chat_list()

if __name__ == "__main__":
    # merge_bot()
    main()


########NEW FILE########
__FILENAME__ = lingr-say
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import sys
sys.path.insert(0, '/usr/lib/pymodules/python2.5')
import urllib, urllib2
import cgi

from configobj import ConfigObj
config = ConfigObj("../skype-bridge.conf")
verifier = config['lingr']['verifier']
request = "http://lingr.com/api/room/say?room=%s&bot=%s&text=%s&bot_verifier=%s"
text = urllib.quote_plus('うへー')
request  = request % ('arakawatomonori', 'skype', text, verifier)
print request
response = urllib2.urlopen(request)


########NEW FILE########
__FILENAME__ = lingr-skype
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import sys
import os
os.environ['DISPLAY'] = ":64"
os.environ['XAUTHORITY'] = "/var/www/.Xauthority"

import json
import re

import pprint
pp = pprint.PrettyPrinter(indent = 4)

import Skype4Py

from configobj import ConfigObj
config_path = '/home/takano32/workspace/skype-bridge/Skype4Py/skype-bridge.conf'
config = ConfigObj(config_path)

if not os.environ.has_key('CONTENT_LENGTH'):
    exit()

content_length = int(os.environ['CONTENT_LENGTH'])
request_content = sys.stdin.read(content_length)

from_lingr = json.JSONDecoder().decode(request_content)

print "Content-Type: text/plain"
print

if not from_lingr.has_key('events'):
    print
    exit()

def handler(msg, event):
    pass

def send_message(room, text):
    room.SendMessage(text)

skype = Skype4Py.Skype()
skype.OnMessageStatus = handler
skype.Attach()

for event in from_lingr['events']:
    if not event.has_key('message'):
        continue
    for key in config:
        if key == 'lingr' or key == 'skype' or key == 'irc':
            continue
        if not config[key].has_key('lingr'):
            continue
        if not config[key].has_key('skype'):
            continue
        if event['message']['room'] == config[key]['lingr']:
            text = event['message']['text']
            name = event['message']['nickname']
            if re.compile(u'荒.*?川.*?智.*?則').match(name):
                name = event['message']['speaker_id']
            if len(name) > 16:
                name = event['message']['speaker_id']
            room = config[key]['skype']
            room = skype.Chat(room)
            for line in text.splitlines():
                msg = '%s: %s' % (name, line)
                send_message(room, msg)
print
exit()
# for debug
#print pp.pformat(from_lingr)


########NEW FILE########
__FILENAME__ = messagesender
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak@no32 dot tk>
#

from configobj import ConfigObj
import sys, xmlrpclib

CONFIG = ConfigObj("skype-bridge.conf")

xmlrpc_host = CONFIG['skype']['xmlrpc_host']
xmlrpc_port = CONFIG['skype']['xmlrpc_port']
sendmessage = xmlrpclib.ServerProxy('http://%s:%s' % (xmlrpc_host, xmlrpc_port))

room = '#yuiseki/$4425ae72bc11c305'
sendmessage.send_message(room, 'hogefuga')


########NEW FILE########
__FILENAME__ = minecraft
#!/usr/bin/env python
# encoding: utf-8
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import urllib2
import json
import math

class Minecraft():
    def __init__(self):
        self.servers = dict()
        self.servers[u'HolyGrail'] = u'holy-grail.jp'
        self.servers[u'futoase'] = u'192.168.32.10'
        self.servers[u'ariela']  = u'ariela.jp'

    def time(self, server_time):
        hours = math.floor((((server_time / 1000.0)+8)%24))
        minutes = math.floor((((server_time/1000.0)%1)*60))
        seconds = math.floor((((((server_time/1000.0)%1)*60)%1)*60))
        return u"%02d:%02d:%02d" % (hours, minutes, seconds)

    def status(self, server_name, server_addr):
        response = urllib2.urlopen(u'http://%s:8123/up/world/world/1' % server_addr).read()
        data = json.JSONDecoder().decode(response)
        weather = u'☀'
        if data[u'hasStorm']:
            weather = u'☂'
        elif data[u'isThundering']:
            weather = u'⚡'
        time = self.time(data[u'servertime'])
        return u"%-16s [%s] %s" % (server_name, time, weather)

    def statuses(self):
        result = []
        for name, addr in self.servers.items():
           result.append(self.status(name, addr))
        return result
            

        
if __name__ == '__main__':
    m = Minecraft()
    print m.statuses()


########NEW FILE########
__FILENAME__ = sendmessage
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak@no32 dot tk>
#

import Skype4Py
from configobj import ConfigObj
from SimpleXMLRPCServer import SimpleXMLRPCServer
import threading
import os

os.environ['DISPLAY'] = ":64"
os.environ['XAUTHORITY'] = "/var/www/.Xauthority"

CONFIG = ConfigObj("/home/takano32/workspace/skype-bridge/Skype4Py/skype-bridge.conf")

class SendMessage():
	def __init__(self):
		self.skype = Skype4Py.Skype()
		self.skype.Attach()
		self.lock = threading.Lock()

	def send_message(self, room, msg):
		with self.lock:
			room = self.skype.Chat(room)
			room.SendMessage(msg)
		return True

	def re_attach(self):
		self.skype.ResetCache()
		self.skype = Skype4Py.Skype()
		self.skype.Attach()
		return True

if __name__ == "__main__":
	host = CONFIG['skype']['xmlrpc_host']
	port = CONFIG['skype']['xmlrpc_port']
	sv = SimpleXMLRPCServer((host, int(port)))
	sv.register_instance(SendMessage())
	sv.serve_forever()


########NEW FILE########
__FILENAME__ = skype-lingr
#!/usr/bin/env python
# encoding: utf-8
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import sys
import Skype4Py
import time
import pprint
import os
import urllib, urllib2
import cgi
from configobj import ConfigObj
from minecraft import Minecraft

pp = pprint.PrettyPrinter(indent = 4)

def send_message(room, text, verifier):
    request = "http://lingr.com/api/room/say?room=%s&bot=%s&text=%s&bot_verifier=%s"
    text = urllib.quote_plus(text.encode('utf-8'))
    request  = request % (room, 'skype', text, verifier)
    response = urllib2.urlopen(request)
    if response.code != 200:
        print 'HTTP Response Code is %d: %s' % (response.code, time.ctime(time.time()))
        time.sleep(3)
        send_message(room, text, verifier)

def handler_with_try(msg, event):
    try:
        handler(msg, event)
    except SkypeAPIError, err:
        print 'Fault time is', time.ctime(time.time())
        time.sleep(5)
        handler(msg, event)

def handler(msg, event):
    if len(msg.Body) == 0:
        return
    if event == u"RECEIVED":
        config = ConfigObj("/home/takano32/workspace/skype-bridge/Skype4Py/skype-bridge.conf")
        for key in config:
            if key == 'lingr' or key == 'skype':
                continue
            if config[key].has_key('skype') and msg.ChatName == config[key]['skype']:
                name = msg.Sender.FullName
                if len(name) == 0 or len(name) > 16:
                    name = msg.Sender.Handle
                room = config[key]['lingr']
                verifier = config['lingr']['verifier']
                for line in msg.Body.splitlines():
                    if name == 'IRC':
                        text = line
                    else:
                        text = '%s: %s' % (name, line)
                    send_message(room, text, verifier)
                    continue # below function is for minecraft
                    if room == 'hametsu_mine' and line == ':minecraft':
                        for status in Minecraft().statuses():
                            text = '%s: %s' % ('minecraft', status)
                            send_message(room, text, verifier)

def bridge():
    skype = Skype4Py.Skype()
    skype.OnMessageStatus = handler_with_try
    skype.Attach()
    for i in range(0, 60 * 5):
        time.sleep(1)
    skype.ResetCache()
    # skype.ClearChatHistory()
    exit()

if __name__ == "__main__":
    bridge()


########NEW FILE########
__FILENAME__ = bot_daemon
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak@no32 dot tk>
#


from configobj import ConfigObj

# START using SkypeKit
import sys
import keypair
import time

sys.path.append(keypair.distroRoot + '/ipc/python');
sys.path.append(keypair.distroRoot + '/interfaces/skype/python');
try:
	import Skype;
except ImportError:
	raise SystemExit('Program requires Skype and skypekit modules');
# END using SkypeKit

CONFIG = ConfigObj("../skype-bridge.conf")
ACCOUNT_NAME = CONFIG['bot']['skype_id']
ACCOUNT_PSW = CONFIG['bot']['skype_password']
LOGGED_IN = False

class SkypeDaemon():
	def __init__(self):
		global ACCOUNT_NAME, ACCOUNT_PSW
		self.accountName = ACCOUNT_NAME
		self.accountPsw = ACCOUNT_PSW

	@staticmethod
	def OnMessage(self, message, changesInboxTimestamp, supersedesHistoryMessage, conversation):
		if message.author == ACCOUNT_NAME: return

	@staticmethod
	def AccountOnChange(self, property_name):
		print self.status
		if property_name == 'status' and self.status == 'LOGGED_IN':
			global ACCOUNT_NAME
			print "Logging in with", ACCOUNT_NAME
			global LOGGED_IN
			LOGGED_IN = True

	def login(self):
		global LOGGED_IN
		LOGGED_IN = False
		Skype.Skype.OnMessage = self.OnMessage;
		try:
			self.skype = Skype.GetSkype(keypair.keyFileName, port = 8963)
			self.skype.Start()
		except Exception:
			raise SystemExit('Unable to create skype instance');
		Skype.Account.OnPropertyChange = self.AccountOnChange
		account = self.skype.GetAccount(self.accountName)
		account.LoginWithPassword(self.accountPsw, False, False)
		print "logging in..."
		while LOGGED_IN == False:
			time.sleep(1)
		print "login successfully."

	def stop(self):
		self.skype.stop()

	def send_message(self, room, msg):
		conv = self.skype.GetConversationByIdentity(room)
		conv.PostText(msg, False)
		return True

from SimpleXMLRPCServer import SimpleXMLRPCServer

if __name__ == "__main__":
	host = CONFIG['bot']['xmlrpc_host']
	port = CONFIG['bot']['xmlrpc_port']
	sd = SkypeDaemon()
	sd.login()
	sv = SimpleXMLRPCServer((host, int(port)))
	sv.register_instance(sd)
	sv.serve_forever()


########NEW FILE########
__FILENAME__ = finance
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak@no32 dot tk>
#

codes = [
		'NASDAQ:AKAM', # Akamai
		'NASDAQ:GOOG', # Google
		'NASDAQ:AAPL', # Apple
		'NASDAQ:YHOO', # Yahoo!
		'TYO:4689',    # Yahoo! Japan
		'TYO:3632',    # GREE
		'TYO:2432',    # DeNA
		'TYO:2121',    # mixi
		'TYO:4751',    # CyberAgent
		'TYO:3715',    # Dwango
		'TYO:2193',    # COOKPAD
		'TYO:7733',    # OLYMPUS
		'TYO:6501',    # Hitachi
		]

import urllib2
from BeautifulSoup import BeautifulSoup
import re

# Skype START
from configobj import ConfigObj
CONFIG = ConfigObj('../skype-bridge.conf')
ROOM = "#yuiseki/$4425ae72bc11c305"

import xmlrpclib
xmlrpc_host = CONFIG['bot']['xmlrpc_host']
xmlrpc_port = CONFIG['bot']['xmlrpc_port']
DAEMON = xmlrpclib.ServerProxy('http://%s:%s' % (xmlrpc_host, xmlrpc_port))
# Skype END

opener = urllib2.build_opener()

base_url = 'http://www.google.com/finance?q='
texts = [base_url]
for code in codes:
	html = opener.open(base_url + code).read()
	soup = BeautifulSoup(html)
	com = soup.find('h3').text.replace('&nbsp;', '').split()[:1][0]
	l  = soup.find(id = re.compile('ref_[0-9]+_l')).text
	unit = 'JPY'
	if code.startswith('NASDAQ'): unit = 'USD'
	c  = soup.find(id = re.compile('ref_[0-9]+_c')).text
	cp = soup.find(id = re.compile('ref_[0-9]+_cp')).text
	code = '[%s]' % code
	texts.append("%-12s %-16s %12s %s w/ %-s %s" % (code, com, l, unit, c, cp) )

text = "\n".join(texts)
DAEMON.send_message(ROOM, text)


########NEW FILE########
__FILENAME__ = headline
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak@no32 dot tk>
#

ROOM = "#yuiseki/$4425ae72bc11c305"

import pprint
pp = pprint.PrettyPrinter(indent = 4)

from configobj import ConfigObj
CONFIG = ConfigObj('../skype-bridge.conf')

import xmlrpclib
xmlrpc_host = CONFIG['bot']['xmlrpc_host']
xmlrpc_port = CONFIG['bot']['xmlrpc_port']
DAEMON = xmlrpclib.ServerProxy('http://%s:%s' % (xmlrpc_host, xmlrpc_port))

import feedparser
feed = feedparser.parse("http://pipes.yahoo.com/pipes/pipe.run?_id=8f34c1abdb8fc99e9aa057fac8e510e1&_render=rss")

for item in feed['items'][:5]:
	text = item.title + "\n" + item.link
	DAEMON.send_message(ROOM, text)
# for debug
#print pp.pformat(from_lingr)


########NEW FILE########
__FILENAME__ = keypair
# You will need to replace keyFileName with a valid keypair filename
import os
home = os.environ['HOME']
keyFileName = home + '/opt/SkypeKit/keys/Bot/1.0-RELEASE.crt'
distroRoot 	= home + '/opt/SkypeKit/sdp-distro-desktop-skypekit'

########NEW FILE########
__FILENAME__ = nicolv
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak@no32 dot tk>
#
communities = [
		'co80029',   # Dark
		'co1513375', # Light
		'co600306',  # np-complete
		'co9320',    # プログラミング生放送
		'co1495908', # JK
		# 'co244678',  # 神回
		# 'co23655',   # アリーナ
		# 'co1024634', # まるはに
		# 'co405315',  # プログラマ
		]

ROOMS = [
		'#yuiseki/$4425ae72bc11c305',
		#'#pha_pha_/$7604f24b1d42a542',
		#"#takano32/$d380f06c719822e7",
		]

import urllib2
from BeautifulSoup import BeautifulSoup
import re, time

# Skype START
from configobj import ConfigObj
CONFIG = ConfigObj('../skype-bridge.conf')

import xmlrpclib
xmlrpc_host = CONFIG['bot']['xmlrpc_host']
xmlrpc_port = CONFIG['bot']['xmlrpc_port']
DAEMON = xmlrpclib.ServerProxy('http://%s:%s' % (xmlrpc_host, xmlrpc_port))
# Skype END

opener = urllib2.build_opener()

base_url = 'http://com.nicovideo.jp/community/'

latest_urls = {}
for community in communities:
	latest_urls[community] = None

while True:
	for community in communities:
		url = base_url + community
		try:
			html = opener.open(url).read()
		except Exception as err:
			print err
			print community
			print
			continue
		soup = BeautifulSoup(html)
		title = soup.find('title').text
		link = soup.find('a', {'class': 'community'})
		if link == None: continue
		texts = []
		# community
		#texts.append(title)
		#texts.append(url)
		texts.append(link.text)
		href = link['href'].replace(r'?ref=community', '')
		texts.append(href)
		texts.append('--')
		text = "\n".join(texts)
		if latest_urls[community] == href: continue
		latest_urls[community] = href

		for room in ROOMS:
			DAEMON.send_message(room, text)
		#print text
	time.sleep(30.0)
	print time.ctime(time.time())


########NEW FILE########
__FILENAME__ = sengoku
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak@no32 dot tk>
#

# Skype START
from configobj import ConfigObj
CONFIG = ConfigObj('../skype-bridge.conf')
ROOM = "#yuiseki/$4425ae72bc11c305"

import xmlrpclib
xmlrpc_host = CONFIG['bot']['xmlrpc_host']
xmlrpc_port = CONFIG['bot']['xmlrpc_port']
DAEMON = xmlrpclib.ServerProxy('http://%s:%s' % (xmlrpc_host, xmlrpc_port))
# Skype END

text = []
text.append('(devil) 戰じゃ〜！出陣せよ〜！ (devil)')
text.append('7:00~8:00 / 12:00~13:00 / 19:00~20:00 / 22:00~23:00')

DAEMON.send_message(ROOM, "\n".join(text))


########NEW FILE########
__FILENAME__ = chat
print('****************************************************************************');
print('SkypeKit Python Wrapper Tutorial: Sending and Receiving Chat Messages');
print('****************************************************************************');

# This example demonstrates, how to:
# 1. Detect incoming text messages.
# 2. Post text messages into a conversation.

# NB! You will need to launch the SkypeKit runtime before running this example.

#----------------------------------------------------------------------------------
# Importing necessary libraries. Note that you will need to set the keyFileName value
# in the keypair.py file.

import sys;
import keypair;
from time import sleep;

sys.path.append(keypair.distroRoot + '/ipc/python');
sys.path.append(keypair.distroRoot + '/interfaces/skype/python');

try:
	import Skype;
except ImportError:
    raise SystemExit('Program requires Skype and skypekit modules');

#----------------------------------------------------------------------------------
# Taking skypename and password arguments from command-line.

if len(sys.argv) != 3:
	print('Usage: python chat.py <skypename> <password>');
	sys.exit();

accountName = sys.argv[1];
accountPsw  = sys.argv[2];
loggedIn	= False;

#----------------------------------------------------------------------------------
# To get the Skype instance to react to the incoming chat messages, we need to 
# assign The Skype class a custom OnMessage callback handler. The OnMessage callback
# is conveniently equipped with conversation argument, so we can use that to send
# out an automated reply from inside OnMessage immediately.
#
# To display the text of chat messages, we can use the message.body_xml property.
# In case of plain text messages, there is no actual XML in it. For special messages,
# such as conversation live status changes or file transfer notifications, your UI
# will need to parse the body_xml property. This also goes for incoming messages that 
# contain smileys (try it!) and flag icons.

def OnMessage(self, message, changesInboxTimestamp, supersedesHistoryMessage, conversation):
	print conversation.identity, message.author, message.body_xml
	#if conversation.identity != '#yuiseki/$4425ae72bc11c305': return
	#if message.author != accountName:
	#	print(message.author_displayname + ': ' + message.body_xml);
	#	if message.body_xml.find('(xss)') != -1:
	#		msg = '(\"\';alert(String.fromCharCode(88,83,83)))()'
	#		conversation.PostText(msg, True);
	#	# !!! conversation.PostText('Automated reply.', False);

Skype.Skype.OnMessage = OnMessage;

try:
	MySkype = Skype.GetSkype(keypair.keyFileName, port = 8888);
except Exception:
	raise SystemExit('Unable to create skype instance');

	
#----------------------------------------------------------------------------------
# Defining our own Account property change callback and assigning it to the
# Skype.Account class.

def AccountOnChange (self, property_name):
	global loggedIn;
	#if property_name == 'status':
	#	if self.status == 'LOGGED_IN':
	#		conv = MySkype.GetConversationByIdentity('#yuiseki/$4425ae72bc11c305')
	#		pants = conv.GetParticipants()
	#		for pant in pants:
	#			print pant.identity
	#			print pant.rank
	#			print 
	if property_name == 'status':
		if self.status == 'LOGGED_IN':
			loggedIn = True;
			print('Login complete.');

Skype.Account.OnPropertyChange = AccountOnChange;

#----------------------------------------------------------------------------------
# Retrieving account and logging in with it.

account = MySkype.GetAccount(accountName);

print('Logging in with ' + accountName);
account.LoginWithPassword(accountPsw, False, False);

while loggedIn == False:
	sleep(1);

print('Now accepting incoming chat messages.');
print('Press ENTER to quit.');
raw_input('');
print('Exiting..');
MySkype.stop();

########NEW FILE########
__FILENAME__ = inspect_chat_members
# This example demonstrates, how to:
# 1. Detect incoming text messages.
# 2. Post text messages into a conversation.

# NB! You will need to launch the SkypeKit runtime before running this example.

#----------------------------------------------------------------------------------
# Importing necessary libraries. Note that you will need to set the keyFileName value
# in the keypair.py file.

import sys;
import keypair;
from time import sleep;

sys.path.append(keypair.distroRoot + '/ipc/python');
sys.path.append(keypair.distroRoot + '/interfaces/skype/python');

try:
	import Skype;
except ImportError:
    raise SystemExit('Program requires Skype and skypekit modules');

#----------------------------------------------------------------------------------
# Taking skypename and password arguments from command-line.

if len(sys.argv) != 3:
	print('Usage: python chat.py <skypename> <password>');
	sys.exit();

accountName = sys.argv[1];
accountPsw  = sys.argv[2];
loggedIn	= False;

#----------------------------------------------------------------------------------
# To get the Skype instance to react to the incoming chat messages, we need to 
# assign The Skype class a custom OnMessage callback handler. The OnMessage callback
# is conveniently equipped with conversation argument, so we can use that to send
# out an automated reply from inside OnMessage immediately.
#
# To display the text of chat messages, we can use the message.body_xml property.
# In case of plain text messages, there is no actual XML in it. For special messages,
# such as conversation live status changes or file transfer notifications, your UI
# will need to parse the body_xml property. This also goes for incoming messages that 
# contain smileys (try it!) and flag icons.

def OnMessage(self, message, changesInboxTimestamp, supersedesHistoryMessage, conversation):
	if conversation.identity != '#yuiseki/$4425ae72bc11c305': return
	if message.author != accountName:
		print(message.author_displayname + ': ' + message.body_xml);
		if message.body_xml.find('(xss)') != -1:
			msg = '''
(\"';alert(String.fromCharCode(88,83,83)))()
'''
			conversation.PostText(msg, True);
		# !!! conversation.PostText('Automated reply.', False);

Skype.Skype.OnMessage = OnMessage;

try:
	MySkype = Skype.GetSkype(keypair.keyFileName);
except Exception:
	raise SystemExit('Unable to create skype instance');

	
#----------------------------------------------------------------------------------
# Defining our own Account property change callback and assigning it to the
# Skype.Account class.

def AccountOnChange (self, property_name):
	global loggedIn;
	if property_name == 'status':
		if self.status == 'LOGGED_IN':
			conv = MySkype.GetConversationByIdentity('#yuiseki/$4425ae72bc11c305')
			pants = conv.GetParticipants()
			for pant in pants:
				print pant.identity
				print pant.rank
				print 
			print('Login complete.');
			loggedIn = True;

Skype.Account.OnPropertyChange = AccountOnChange;

#----------------------------------------------------------------------------------
# Retrieving account and logging in with it.

account = MySkype.GetAccount(accountName);

print('Logging in with ' + accountName);
print
account.LoginWithPassword(accountPsw, False, False);

while loggedIn == False:
	sleep(1);

MySkype.stop();


########NEW FILE########
__FILENAME__ = bridge_daemon
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak@no32 dot tk>
#


from configobj import ConfigObj
from SimpleXMLRPCServer import SimpleXMLRPCServer

# START using SkypeKit
import sys
import keypair
from time import sleep

sys.path.append(keypair.distroRoot + '/ipc/python');
sys.path.append(keypair.distroRoot + '/interfaces/skype/python');
try:
	import Skype;
except ImportError:
	raise SystemExit('Program requires Skype and skypekit modules');
# END using SkypeKit

CONFIG = ConfigObj("skype-bridge.conf")
ACCOUNT_NAME = CONFIG['irc']['skype_id']
ACCOUNT_PSW = CONFIG['irc']['skype_password']
LOGGED_IN = False

import Queue
IRC_MESSAGES = Queue.Queue()
ROOMS = {}

class SkypeDaemon():
	def __init__(self):
		global ACCOUNT_NAME, ACCOUNT_PSW
		self.accountName = ACCOUNT_NAME
		self.accountPsw = ACCOUNT_PSW

	@staticmethod
	def OnMessage(self, message, changesInboxTimestamp, supersedesHistoryMessage, conversation):
		global CONFIG
		global ACCOUNT_NAME
		if message.author != ACCOUNT_NAME:
			for key in CONFIG:
				if key == 'skype' or key == 'irc':
						continue
				if CONFIG[key].has_key('skype2irc'):
						if CONFIG[key]['skype2irc'].title() == 'False':
								continue
				if CONFIG[key].has_key('skype') and conversation.identity == CONFIG[key]['skype']:
						if CONFIG[key].has_key('irc'):
								channel = CONFIG[key]['irc']
								nick = message.author_displayname
								text = message.body_xml
								global IRC_MESSAGES
								print channel, text
								IRC_MESSAGES.put((channel, nick, text))

	@staticmethod
	def AccountOnChange(self, property_name):
		print self.status
		if property_name == 'status' and self.status == 'LOGGED_IN':
			global ACCOUNT_NAME
			print "Logging in with", ACCOUNT_NAME
			global LOGGED_IN
			LOGGED_IN = True

	def login(self):
		global LOGGED_IN
		LOGGED_IN = False
		Skype.Skype.OnMessage = self.OnMessage;
		try:
			self.skype = Skype.GetSkype(keypair.keyFileName, port = 8962);
			self.skype.Start()
		except Exception:
			raise SystemExit('Unable to create skype instance');
		Skype.Account.OnPropertyChange = self.AccountOnChange
		account = self.skype.GetAccount(self.accountName)
		account.LoginWithPassword(self.accountPsw, False, False)
		print "logging in"
		while LOGGED_IN == False:
			sleep(1)
		print "logged in"

	def stop(self):
		self.skype.stop()

class SkypeDaemonServer():
	def __init__(self, skype):
		self.skype = skype

	def send_message(self, room, msg):
		global ROOMS
		if ROOMS.has_key(room):
			conv = ROOMS[room]
		else:
			conv = self.skype.skype.GetConversationByIdentity(room)
			ROOMS[room] = conv
		conv.PostText(msg, False)
		return True

	def pop_message(self):
		global IRC_MESSAGES
		try:
			message = IRC_MESSAGES.get_nowait()
		except Queue.Empty as err:
			message = False
		return message

if __name__ == "__main__":
	host = CONFIG['irc']['xmlrpc_host']
	port = CONFIG['irc']['xmlrpc_port']
	sd = SkypeDaemon()
	sd.login()
	sds = SkypeDaemonServer(sd)
	sv = SimpleXMLRPCServer((host, int(port)))
	sv.register_instance(sds)
	sv.serve_forever()


########NEW FILE########
__FILENAME__ = irc2skype
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak@no32 dot tk>
#

import sys
import os
import pprint
import time
import random
import threading
import xmlrpclib
from configobj import ConfigObj
import re

pp = pprint.PrettyPrinter(indent = 4)

SERVER = "irc.freenode.net"
PORT = 6667
WAIT = None
NICKNAME = "to_skype"

from ircbot import SingleServerIRCBot
from irclib import nm_to_n

config = ConfigObj("skype-bridge.conf")

if config.has_key('irc') and config['irc'].has_key('server'):
	SERVER = config['irc']['server']

if config.has_key('irc') and config['irc'].has_key('port'):
	PORT = int(config['irc']['port'])

if config.has_key('irc') and config['irc'].has_key('wait'):
	WAIT = float(config['irc']['wait'])

class IRC2Skype(SingleServerIRCBot):
	def __init__(self, server = SERVER):
		SingleServerIRCBot.__init__(self, [(SERVER, PORT)], NICKNAME, NICKNAME)
		xmlrpc_host = config['irc']['xmlrpc_host']
		xmlrpc_port = config['irc']['xmlrpc_port']
		self.skype = xmlrpclib.ServerProxy('http://%s:%s' % (xmlrpc_host, xmlrpc_port))
		self.channel = "#takano32bot"

	def on_nicknameinuse(self, c, e):
		c.nick(c.get_nickname() + "_")

	def on_welcome(self, c, e):
		c.join(self.channel)
		for key in config:
			if key == 'skype' or key == 'irc':
				continue
			if config[key].has_key('irc'):
				channel = config[key]['irc']
				c.join(channel)

	def say(self, channel, msg):
		self.connection.privmsg(channel, msg)

	def notice(self, channel, msg):
		self.connection.notice(channel, msg)

	def do_command(self, c, e):
		try:
			msg = unicode(e.arguments()[0], "utf8")
			self.say(self.channel, msg.encode('utf-8'))
		except UnicodeDecodeError, err:
			print "UnicodeDecodeError occured"
			return

	def skype_handler_for_pubmsg(self, c, e):
		return self.skype_handler(c, e, True)

	def skype_handler_for_pubnotice(self, c, e):
		return self.skype_handler(c, e, True)

	def skype_handler(self, c, e, notice = False):
		nick = e.nick = nm_to_n(e.source())
		if nick.startswith(u'skype') or re.compile(u'S_*').match(nick): return
		try:
			msg = unicode(e.arguments()[0], "utf8")
		except UnicodeDecodeError, err:
			print "UnicodeDecodeError occured"
			return
		for key in config:
			if key == 'skype' or key == 'irc':
				continue
			if config[key].has_key('irc2skype'):
				if config[key]['irc2skype'].title() == 'False':
					continue
			if config[key].has_key('irc'):
				channel = config[key]['irc']
				if channel == e.target():
					room = config[key]['skype']
					print time.ctime(time.time()), ': ', channel
					self.send_message(room, nick, msg, notice)

	def send_message(self, room, nick, msg, notice = False, retry = 3):
		if retry == 0: return
		try:
			if not notice and msg.startswith(u'@'):
				self.skype.send_message(room, msg)
				notice = '# %s is issuing the above command.' % nick
				self.skype.send_message(room, notice)
				return
			text = '%s: %s' % (nick, msg)
			self.skype.send_message(room, text)
		except xmlrpclib.Fault, err:
			print "A fault occurred"
			print "Fault code: %d" % err.faultCode
			print "Fault string: %s" % err.faultString
			#print "Skype4Py.errors.ISkypeError"
			print 'Fault time: ', time.ctime(time.time())
			pp.pprint(room)
			pp.pprint(text)
			self.send_message(room, nick, msg, notice, retry - 1)

	on_pubnotice = skype_handler_for_pubnotice
	on_privnotice = do_command
	on_pubmsg = skype_handler_for_pubmsg
	on_privmsg = do_command

bridge = IRC2Skype()
bridge.start()


########NEW FILE########
__FILENAME__ = keypair
# You will need to replace keyFileName with a valid keypair filename
import os
home = os.environ['HOME']
keyFileName = home + '/opt/SkypeKit/IRC/RELEASE-1.0.crt'
distroRoot 	= home + '/opt/SkypeKit/skypekit-sdk'


########NEW FILE########
__FILENAME__ = skype2irc
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak@no32 dot tk>
#

import sys
import os
import pprint
import time
import random
import threading
import xmlrpclib
from configobj import ConfigObj
import xml.etree.ElementTree

pp = pprint.PrettyPrinter(indent = 4)

SERVER = "irc.freenode.net"
PORT = 6667
WAIT = None
NICKNAME = "skype"

from ircbot import SingleServerIRCBot
from irclib import nm_to_n

CONFIG = ConfigObj("skype-bridge.conf")

if CONFIG.has_key('irc') and CONFIG['irc'].has_key('server'):
	SERVER = CONFIG['irc']['server']

if CONFIG.has_key('irc') and CONFIG['irc'].has_key('port'):
	PORT = int(CONFIG['irc']['port'])

if CONFIG.has_key('irc') and CONFIG['irc'].has_key('wait'):
	WAIT = float(CONFIG['irc']['wait'])

class Skype2IRC(SingleServerIRCBot):
	def __init__(self, server = SERVER):
		SingleServerIRCBot.__init__(self, [(SERVER, PORT)], NICKNAME, NICKNAME)
		xmlrpc_host = CONFIG['irc']['xmlrpc_host']
		xmlrpc_port = CONFIG['irc']['xmlrpc_port']
		self.daemon = xmlrpclib.ServerProxy('http://%s:%s' % (xmlrpc_host, xmlrpc_port))
		self.channel = "#takano32bot"

	def on_nicknameinuse(self, c, e):
		c.nick(c.get_nickname() + "_")

	def on_welcome(self, c, e):
		c.join(self.channel)
		for key in CONFIG:
			if key == 'skype' or key == 'irc':
				continue
			if CONFIG[key].has_key('irc'):
				channel = CONFIG[key]['irc']
				c.join(channel)
		self.timer_handler()

	def timer_handler(self):
		try:
			message = self.daemon.pop_message()
		except xml.parsers.expat.ExpatError, err:
			message = False
		if message != False:
			(channel, nick, body_xml) = message
			print time.ctime(time.time()), ': ', channel
			elem = xml.etree.ElementTree.fromstring("<body>%s</body>" % body_xml.encode('utf-8'))
			text = ""
			for t in elem.itertext():
				text += t
			lines = text.splitlines()
			if len(lines) == 1 and text.startswith('@'):
				text = lines[0]
				self.say(channel, text.encode('utf-8'))
				notice = '# %s is issuing the above command.' % nick
				self.notice(channel, notice.encode('utf-8'))
			else:
				for line in lines:
					texts = list()
					while 150 < len(line):
						text = '%s: %s' % (nick, line[:150])
						texts.append(text)
						line = line[149:]
					text = '%s: %s' % (nick, line)
					texts.append(text)
					for text in texts:
						self.say(channel, text.encode('utf-8'))
						if WAIT != None:
							time.sleep(WAIT)
						else:
							time.sleep(len(text) / 20.0)
			t = threading.Timer(0.1, self.timer_handler)
			t.start()
		else:
			time.sleep(1)
			t = threading.Timer(1.0, self.timer_handler)
			t.start()

	def say(self, channel, msg):
		self.connection.privmsg(channel, msg)

	def notice(self, channel, msg):
		self.connection.notice(channel, msg)

	def do_command(self, c, e):
		try:
			msg = unicode(e.arguments()[0], "utf8")
			self.say(self.channel, msg.encode('utf-8'))
		except UnicodeDecodeError, err:
			print "UnicodeDecodeError occured"
			return

	on_pubnotice = do_command
	on_privnotice = do_command
	on_pubmsg = do_command
	on_privmsg = do_command

bridge = Skype2IRC()
bridge.start()


########NEW FILE########
__FILENAME__ = keypair
# You will need to replace keyFileName with a valid keypair filename
import os
home = os.environ['HOME']
keyFileName = home + '/opt/SkypeKit/KeyPair.crt';
distroRoot 	= home + '/opt/SkypeKit/skypekit-sdk';

########NEW FILE########
__FILENAME__ = chatwork
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak@no32 dot tk>
#

import json

from configobj import ConfigObj
CONFIG = ConfigObj('skype-bridge.conf')
ROOM = "arakawatomonori"
VERIFIER = CONFIG['lingr']['verifier']

def say(room, text, verifier):
	request = "http://lingr.com/api/room/say?room=%s&bot=%s&text=%s&bot_verifier=%s"
	request  = request % (room, 'skype', text, verifier)
	try:
		response = urllib2.urlopen(request)
	except urllib2.HTTPError as err:
		print 'urllib2.HTTPError: %s' % time.ctime(time.time())
		time.sleep(3)
		say(room, text, verifier)
		return
	if response.code == 200:
		res = json.JSONDecoder().decode(response.read())
		if res.has_key('status'):
			if res['status'] == 'ok':
				return
			else:
				pass

import urllib2
import random
class HeadRequest(urllib2.Request):
	def get_method(self):
		return "HEAD"

while True:
	x = int(random.random() * 3)
	y = int(random.random() * 3800)
	for ext in ['jpg', 'png', 'gif']:
		url = 'http://chat-work-appdata.s3.amazonaws.com/icon/%d/%d.%s' % (x, y, ext)
		request = HeadRequest(url)
		try:
			res = urllib2.urlopen(request)
		except Exception as err:
			continue

		try:
			if res.code == 200:
				for key, value in res.info().items():
					if key.title() == 'Content-Length':
						if int(value) > 8192:
							say(ROOM, url, VERIFIER)
							break
						else:
							raise
		except Exception as err:
			continue

		exit()


########NEW FILE########
__FILENAME__ = keypair
# You will need to replace keyFileName with a valid keypair filename
import os
home = os.environ['HOME']
keyFileName = home + '/opt/SkypeKit/keys/Lingr/1.0-RELEASE.crt'
distroRoot 	= home + '/opt/SkypeKit/sdp-distro-desktop-skypekit'
print distroRoot

########NEW FILE########
__FILENAME__ = lingr



def room_command(message):
	return message.title().startswith('Lingr>Room')




########NEW FILE########
__FILENAME__ = lingr2skype
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak@no32 dot tk>
#


import sys
import os
import json
import re

import pprint
pp = pprint.PrettyPrinter(indent = 4)

from configobj import ConfigObj
config = ConfigObj('/home/takano32/workspace/skype-bridge/SkypeKit/skype-bridge.conf')

import xmlrpclib
xmlrpc_host = config['lingr']['xmlrpc_host']
xmlrpc_port = config['lingr']['xmlrpc_port']
skype_daemon = xmlrpclib.ServerProxy('http://%s:%s' % (xmlrpc_host, xmlrpc_port))

if not os.environ.has_key('CONTENT_LENGTH'):
	exit()

content_length = int(os.environ['CONTENT_LENGTH'])
request_content = sys.stdin.read(content_length)

from_lingr = json.JSONDecoder().decode(request_content)

print "Content-Type: text/plain"
print

if not from_lingr.has_key('events'):
	print
	exit()

for event in from_lingr['events']:
	if not event.has_key('message'):
		continue
	for key in config:
		if key == 'lingr' or key == 'skype' or key == 'irc':
			continue
		if not config[key].has_key('lingr'): continue
		if not config[key].has_key('skype'): continue
		if event['message']['room'] == config[key]['lingr']:
			text = event['message']['text']
			name = event['message']['nickname']
			if re.compile(u'荒.*?川.*?智.*?則').match(name):
				name = event['message']['speaker_id']
			if len(name) > 16:
				name = event['message']['speaker_id']
			room = config[key]['skype']
			for line in text.splitlines():
				msg = '%s: %s' % (name, line)
				skype_daemon.send_message(room, msg)
print
exit()
# for debug
#print pp.pformat(from_lingr)


########NEW FILE########
__FILENAME__ = skype2lingr
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak@no32 dot tk>
#


from configobj import ConfigObj
from SimpleXMLRPCServer import SimpleXMLRPCServer
import httplib, urllib, urllib2
import json
import xml.etree.ElementTree
import lingr
import re

# START using SkypeKit
import sys
import keypair
import time

sys.path.append(keypair.distroRoot + '/ipc/python');
sys.path.append(keypair.distroRoot + '/interfaces/skype/python');
try:
	import Skype;
except ImportError:
	raise SystemExit('Program requires Skype and skypekit modules');
# END using SkypeKit

CONFIG = ConfigObj("skype-bridge.conf")
ACCOUNT_NAME = CONFIG['lingr']['skype_id']
ACCOUNT_PSW = CONFIG['lingr']['skype_password']
LOGGED_IN = False

class SkypeDaemon():
	def __init__(self):
		global ACCOUNT_NAME, ACCOUNT_PSW
		self.accountName = ACCOUNT_NAME
		self.accountPsw = ACCOUNT_PSW

	@staticmethod
	def SendMessage(room, text, verifier):
		request = "http://lingr.com/api/room/say?room=%s&bot=%s&text=%s&bot_verifier=%s"
		text = urllib.quote_plus(text.encode('utf-8'))
		request  = request % (room, 'skype', text, verifier)
		try:
			response = urllib2.urlopen(request)
		except urllib2.URLError as err:
			print 'urllib2.URLError: %s' % time.ctime(time.time())
			print room
			return
		except urllib2.HTTPError as err:
			print 'urllib2.HTTPError: %s' % time.ctime(time.time())
			print room
			#time.sleep(3)
			#SkypeDaemon.SendMessage(room, text, verifier)
			return
		except httplib.BadStatusLine as err:
			print 'httplib.BadStatusLine: %s' % time.ctime(time.time())
			time.sleep(3)
			SkypeDaemon.SendMessage(room, text, verifier)
			return

		if response.code == 200:
			try:
				res = json.JSONDecoder().decode(response.read())
			except ValueError as err:
				print err
			if res.has_key('status'):
				if res['status'] == 'ok':
					return
				else:
					print 'Response status from Lingr: %s' % res['status']
					time.sleep(3)
					SkypeDaemon.SendMessage(room, text, verifier)
			else:
				print 'Response from Lingr dont have status code'
				time.sleep(3)
				SkypeDaemon.SendMessage(room, text, verifier)
		else:
			print 'HTTP Response Code is %d: %s' % (response.code, time.ctime(time.time()))
			time.sleep(3)
			SkypeDaemon.SendMessage(room, text, verifier)

	@staticmethod
	def SendMessageWithName(room, name, text, verifier):
		lines = text.splitlines()
		for line in lines:
			if name == 'IRC':
				text = line
			else:
				try:
					text = '%s: %s' % (name, line)
				except UnicodeDecodeError as err:
					print 'UnicodeDecodeError: %s' % time.ctime(time.time())
					print name
					print line
					print
					return
			SkypeDaemon.SendMessage(room, text, verifier)

	@staticmethod
	def OnMessage(self, message, changesInboxTimestamp, supersedesHistoryMessage, conversation):
		global CONFIG, ACCOUNT_NAME
		if message.timestamp < time.mktime(time.localtime()) - 300: return
		if message.author == ACCOUNT_NAME: return
		for key in CONFIG:
			if key == 'skype' or key == 'lingr':
					continue
			if CONFIG[key].has_key('skype2lingr'):
				if CONFIG[key]['skype2lingr'].title() == 'False':
					continue
			if not CONFIG[key].has_key('skype'): continue
			if not conversation.identity == CONFIG[key]['skype']: continue
			if CONFIG[key].has_key('lingr'):
				room = CONFIG[key]['lingr']
				verifier = CONFIG['lingr']['verifier']
				name = message.author_displayname
				if len(name) == 0 or len(name) > 16:
					name = message.author

				try:
					elem = xml.etree.ElementTree.fromstring("<body>%s</body>" % message.body_xml.encode('utf-8'))
					text = ""
					for t in elem.itertext():
						text += t
				except Exception as err:
					print message.body_xml.encode('utf-8')
					print err
					text = message.body_xml.encode('utf-8')

				if len(text.splitlines()) == 1 and lingr.room_command(text):
					conversation.PostText('System: bridging w/ http://lingr.com/room/%s' % room)
					return
				print room, text
				# discard_private_code = re.compile('[\uE000-\uF8FF]'.encode('utf-8'))
				# name = discard_private_code.sub('', name)
				# text = discard_private_code.sub('', text)
				SkypeDaemon.SendMessageWithName(room, name, text, verifier)

	@staticmethod
	def AccountOnChange(self, property_name):
		print self.status
		if property_name == 'status' and self.status == 'LOGGED_IN':
			global ACCOUNT_NAME
			print "Logging in with", ACCOUNT_NAME
			global LOGGED_IN
			LOGGED_IN = True

	def login(self):
		global LOGGED_IN
		LOGGED_IN = False
		Skype.Skype.OnMessage = self.OnMessage;
		try:
			self.skype = Skype.GetSkype(keypair.keyFileName, port = 8964)
			self.skype.Start()
		except Exception:
			raise SystemExit('Unable to create skype instance');
		Skype.Account.OnPropertyChange = self.AccountOnChange
		account = self.skype.GetAccount(self.accountName)
		account.LoginWithPassword(self.accountPsw, False, False)
		print "logging in"
		while LOGGED_IN == False:
			time.sleep(1)
		print "logged in"

	def stop(self):
		self.skype.stop()

class SkypeDaemonServer():
	def __init__(self, skype):
		self.skype = skype

	def send_message(self, room, msg):
		conv = self.skype.skype.GetConversationByIdentity(room)
		conv.PostText(msg, False)
		return True

if __name__ == "__main__":
	host = CONFIG['lingr']['xmlrpc_host']
	port = CONFIG['lingr']['xmlrpc_port']
	sd = SkypeDaemon()
	sd.login()
	sds = SkypeDaemonServer(sd)
	sv = SimpleXMLRPCServer((host, int(port)))
	sv.register_instance(sds)
	sv.serve_forever()


########NEW FILE########
