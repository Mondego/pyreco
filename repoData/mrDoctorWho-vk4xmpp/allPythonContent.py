__FILENAME__ = attachments
# coding: utf-8
# This file is a part of VK4XMPP transport
# © simpleApps, 2013 — 2014.

import urllib

def parseAttachments(self, msg):
	result = ""
	if msg.has_key("attachments"):
		if msg["body"]:
			result += _("\nAttachments:")
		searchlink = "https://vk.com/search?c[q]=%s&c[section]=audio"
		attachments = msg["attachments"]
		for att in attachments:
			body = ""
			key = att.get("type")
			if key == "wall":
				body += "\nWall: https://vk.com/feed?w=wall%(to_id)s_%(id)s"
			elif key == "photo":
				keys = ("src_xxxbig", "src_xxbig", "src_xbig", "src_big", "src", "url", "src_small")
				for _key in keys:
					if _key in att[key]:
						body += "\n" + att[key][_key]
						break
			elif key == "video":
				body += "\nVideo: http://vk.com/video%(owner_id)s_%(vid)s — %(title)s"
			elif key == "audio":
				for _key in ("performer", "title"):
					if att[key].has_key(_key):
						att[key][_key] = uHTML(att[key][_key])

				url = searchlink % urllib.quote(str("%(performer)s %(title)s" % att[key]))
				att[key]["url"] = url
				body += "\nAudio: %(performer)s — %(title)s — %(url)s"
			elif key == "doc":
				body += "\nDocument: %(title)s — %(url)s"
			elif key == "sticker":
				keys = ("photo_256", "photo_128", "photo_64")
				for _key in keys:
					if _key in att[key]:
						body += "\nSticker: " + att[key][_key]
						break
			else:
				body += "\nUnknown attachment: " + str(att[key])
			result += body % att.get(key, {})
	return result

Handlers["msg01"].append(parseAttachments)

########NEW FILE########
__FILENAME__ = captcha_forms
# coding: utf-8
# This file is a part of VK4XMPP transport

from hashlib import sha1

def captchaSend(self):
	logger.debug("VKLogin: sending message with captcha to %s" % self.source)
	body = _("WARNING: VK sent captcha to you."
			 " Please, go to %s and enter text from image to chat."
			 " Example: !captcha my_captcha_key. Tnx") % self.engine.captcha["img"]
	msg = xmpp.Message(self.source, body, "chat", frm = TransportID)
	x = msg.setTag("x", namespace=xmpp.NS_OOB)
	x.setTagData("url", self.engine.captcha["img"])
	captcha = msg.setTag("captcha", namespace=xmpp.NS_CAPTCHA)
	image = vCardGetPhoto(self.engine.captcha["img"], False)
	if image:
		hash = sha1(image).hexdigest()
		encoded = image.encode("base64")
		form = utils.buildDataForm(type="form", fields = [{"var": "FORM_TYPE", "value": xmpp.NS_CAPTCHA, "type": "hidden"},
													  {"var": "from", "value": TransportID, "type": "hidden"},
													  {"var": "ocr", "label": _("Enter shown text"), 
													  	"payload": [xmpp.Node("required"), xmpp.Node("media", {"xmlns": xmpp.NS_MEDIA}, 
													  		[xmpp.Node("uri", {"type": "image/jpg"}, 
													  			["cid:sha1+%s@bob.xmpp.org" % hash])])]}])
		captcha.addChild(node=form)
		oob = msg.setTag("data", {"cid": "sha1+%s@bob.xmpp.org" % hash, "type": "image/jpg", "max-age": "0"}, xmpp.NS_URN_OOB)
		oob.setData(encoded)
	else:
		logger.critical("VKLogin: can't add captcha image to message url:%s" % self.engine.captcha["img"])
	Sender(Component, msg)
	Presence = xmpp.protocol.Presence(self.source, frm=TransportID)
	Presence.setStatus(body)
	Presence.setShow("xa")
	Sender(Component, Presence)

Handlers["evt04"].append(captchaSend)
########NEW FILE########
__FILENAME__ = forwardMessages
# coding: utf-8
# This file is a part of VK4XMPP transport
# © simpleApps, 2013.

from datetime import datetime

if not require("attachments"):
	raise AssertionError("'forwardMessages' requires 'attachments'")

def parseForwardMessages(self, msg, depth = 0):
	body = ""
	if msg.has_key("fwd_messages"):
		body += _("\nForward messages:")
		fwd_messages = sorted(msg["fwd_messages"], msgSort)
		for fwd in fwd_messages:
			idFrom = fwd["uid"]
			date = fwd["date"]
			fwdBody = escape("", uHTML(fwd["body"]))
			date = datetime.fromtimestamp(date).strftime("%d.%m.%Y %H:%M:%S")
			name = self.getUserData(idFrom)["name"]
			body += "\n[%s] <%s> %s" % (date, name, fwdBody)
			body += parseAttachments(self, fwd)
			if depth < MAXIMUM_FORWARD_DEPTH: 
				depth += 1
				body += parseForwardMessages(self, fwd, depth)
	return body

Handlers["msg01"].append(parseForwardMessages)

########NEW FILE########
__FILENAME__ = geo
# coding: utf-8
# This file is a part of VK4XMPP transport
# © simpleApps, 2013.

import urllib

GoogleMapLink = "https://maps.google.com/maps?q=%s"

def TimeAndRelativeDimensionInSpace(self, machine):
	body = ""
	if machine.has_key("geo"):
		WhereAreYou = machine["geo"]
		Place = WhereAreYou.get("place")
		Coordinates = WhereAreYou["coordinates"].split()
		Coordinates = "Lat.: {0}°, long: {1}°".format(*Coordinates)
		body = _("Point on the map: \n")
		if Place:
			body += _("Country: %s") % Place["country"]
			body += _("\nCity: %s\n") % Place["city"]
		body += _("Coordinates: %s") % Coordinates
		body += "\n%s — Google Maps" % GoogleMapLink % urllib.quote(WhereAreYou["coordinates"])
	return body

Handlers["msg01"].append(TimeAndRelativeDimensionInSpace)

########NEW FILE########
__FILENAME__ = groupchats
# coding: utf-8
# This file is a part of VK4XMPP transport
# © simpleApps, 2013 — 2014.
# File contains parts of code from 
# BlackSmith mark.1 XMPP Bot, © simpleApps 2011 — 2014.

if not require("attachments") or not require("forwardMessages"):
	raise

def IQSender(chat, attr, data, afrls, role, jidFrom):
	stanza = xmpp.Iq("set", to=chat, frm=jidFrom)
	query = xmpp.Node("query", {"xmlns": xmpp.NS_MUC_ADMIN})
	arole = query.addChild("item", {attr: data, afrls: role})
	stanza.addChild(node = query)
	Sender(Component, stanza)

def member(chat, jid, jidFrom):
	IQSender(chat, "jid", jid, "affiliation", "member", jidFrom)

def inviteUser(chat, jidTo, jidFrom, name):
	invite = xmpp.Message(to=chat, frm=jidFrom)
	x = xmpp.Node("x", {"xmlns": xmpp.NS_MUC_USER})
	inv = x.addChild("invite", {"to": jidTo})
	inv.setTagData("reason", _("You're invited by user «%s»") % name)
	invite.addChild(node=x)
	Sender(Component, invite)


## TODO: Set chatroom's name
def chatSetConfig(chat, jidFrom, exterminate=False):
	iq = xmpp.Iq("set", to=chat, frm=jidFrom)
	query = iq.addChild("query", namespace=xmpp.NS_MUC_OWNER)
	if exterminate:
		query.addChild("destroy")
	else:
		form = utils.buildDataForm(fields = [{"var": "FORM_TYPE", "type": "hidden", "value": xmpp.NS_MUC_ROOMCONFIG},
										 {"var": "muc#roomconfig_membersonly", "type": "boolean", "value": "1"},
										 {"var": "muc#roomconfig_publicroom", "type": "boolean", "value": "1"},
										 {"var": "muc#roomconfig_whois", "value": "anyone"}])
		query.addChild(node=form)
	Sender(Component, iq)

def chatPresence(chat, name, jidFrom, type=None):
	prs = xmpp.Presence("%s/%s" % (chat, name), type, frm=jidFrom)
	prs.setTag("c", {"node": "http://simpleapps.ru/caps/vk4xmpp", "ver": Revision}, xmpp.NS_CAPS)
	Sender(Component, prs)

def chatMessage(chat, text, jidFrom, subj=None, timestamp=0):
	message = xmpp.Message(chat, typ="groupchat")
	if timestamp:
		timestamp = time.gmtime(timestamp)
		message.setTimestamp(time.strftime("%Y%m%dT%H:%M:%S", timestamp))
	if not subj:
		message.setBody(text)
	else:
		message.setSubject(text)
	message.setFrom(jidFrom)
	Sender(Component, message)

def outgoungChatMessageHandler(self, msg):
	if msg.has_key("chat_id"):
		idFrom = msg["uid"]
		owner = msg["admin_id"]
		_owner = vk2xmpp(owner)
		chatID = "%s_chat#%s" % (self.UserID, msg["chat_id"])
		chat = "%s@%s" % (chatID, ConferenceServer)
		users = msg["chat_active"].split(",")
		users.append(self.UserID)
		if not users: ## is it possible?
			logger.debug("groupchats: all users exterminated in chat: %s" % chat)
			if chat in self.chatUsers:
				chatPresence(chat, self.getUserData(owner)["name"], vk2xmpp(self.UserID), "unavailable")
				del self.chatUsers[chat]
			return None

		if chat not in self.chatUsers:
			logger.debug("groupchats: creating %s. Users: %s; owner: %s" % (chat, msg["chat_active"], owner))
			self.chatUsers[chat] = []
			for usr in (owner, self.UserID):
				chatPresence(chat, self.getUserData(usr)["name"], vk2xmpp(usr))
			chatSetConfig(chat, _owner)
			member(chat, self.source, _owner)
			inviteUser(chat, self.source, _owner, self.getUserData(owner)["name"])
			chatMessage(chat, msg["title"], _owner, True, msg["date"])
	
		for user in users:
			if not user in self.chatUsers[chat]:
				logger.debug("groupchats: user %s has joined the chat %s" % (user, chat))
				self.chatUsers[chat].append(user)
				uName = self.getUserData(user)["name"]
				user = vk2xmpp(user)
				member(chat, user, _owner)
				chatPresence(chat, uName, user)
		
		for user in self.chatUsers[chat]:
			if not user in users:
				logger.debug("groupchats: user %s has left the chat %s" % (user, chat))
				self.chatUsers[chat].remove(user)
				uName = self.getUserData(user)["name"]
				chatPresence(chat, uName, vk2xmpp(user), "unavailable")

		body = escape("", uHTML(msg["body"]))
		body += parseAttachments(self, msg)
		body += parseForwardMessages(self, msg)
		if body:
			chatMessage(chat, body, vk2xmpp(idFrom), None, msg["date"])
		return None
	return ""

def incomingChatMessageHandler(msg):
	if msg.getType() == "groupchat":
		body = msg.getBody()
		destination = msg.getTo().getStripped()
		source = msg.getFrom().getStripped()
		html = msg.getTag("html")
		x = msg.getTag("x", {"xmlns": "http://jabber.org/protocol/muc#user"})

		if x and x.getTagAttr("status", "code") == "100":
			raise xmpp.NodeProcessed()

		if not msg.getTimestamp() and body:
			Node, Domain = source.split("@")
			if Domain == ConferenceServer:
				destination = vk2xmpp(destination)
				if destination in jidToID:
					jid = jidToID[destination]
					if jid in Transport:
						user = Transport[jid]
						if html and html.getTag("body"): ## XHTML-IM!
							logger.debug("groupchats: fetched xhtml image from %s" % source)
							try:
								xhtml = xhtmlParse(user, html, source, source, "chat_id")
							except Exception:
								xhtml = False
							if xhtml:
								raise xmpp.NodeProcessed()
						user.msg(body, Node.split("#")[1], "chat_id")


def chatDestroy(user):
	chats = user.vk.method("execute.getChats")
	for chat in chats:
		chatSetConfig("%s_chat#%s@%s" % (user.UserID, chat["chat_id"], ConferenceServer), vk2xmpp(chat["admin_id"]), True)

if ConferenceServer:
	TransportFeatures.append(xmpp.NS_GROUPCHAT)
	Handlers["msg01"].append(outgoungChatMessageHandler)
	Handlers["msg02"].append(incomingChatMessageHandler)
	Handlers["evt03"].append(chatDestroy)

else:
	del incomingChatMessageHandler, outgoungChatMessageHandler, inviteUser, chatPresence, chatMessage

########NEW FILE########
__FILENAME__ = gateway
#!/usr/bin/env python2
# coding: utf-8

# vk4xmpp gateway, v2a1
# © simpleApps, 2013 — 2014.
# Program published under MIT license.

import gc
import json
import logging
import os
import re
import select
import socket
import signal
import sys
import threading
import time

core = getattr(sys.modules["__main__"], "__file__", None)
if core:
	core = os.path.abspath(core)
	root = os.path.dirname(core)
	if root:
		os.chdir(root)

sys.path.insert(0, "library")
reload(sys).setdefaultencoding("utf-8")

import vkapi as api
import xmpp
import utils

from itypes import Database
from webtools import *
from writer import *
from stext import *
from stext import _

Transport = {}
WatcherList = []
WhiteList = []
jidToID = {}

TransportFeatures = [xmpp.NS_DISCO_ITEMS,
					xmpp.NS_DISCO_INFO,
					xmpp.NS_RECEIPTS,
					xmpp.NS_REGISTER,
					xmpp.NS_GATEWAY,
					xmpp.NS_VERSION,
					xmpp.NS_CAPTCHA,
					xmpp.NS_STATS,
					xmpp.NS_VCARD,
					xmpp.NS_DELAY,
					xmpp.NS_PING,
					xmpp.NS_LAST]

UserFeatures = [xmpp.NS_CHATSTATES]

IDentifier = {"type": "vk",
			"category": "gateway",
			"name": "VK4XMPP Transport"}

Semaphore = threading.Semaphore()

LOG_LEVEL = logging.DEBUG
SLICE_STEP = 8
USER_LIMIT = 0
DEBUG_XMPPPY = False
THREAD_STACK_SIZE = 0
MAXIMUM_FORWARD_DEPTH = 5

pidFile = "pidFile.txt"
logFile = "vk4xmpp.log"
crashDir = "crash"

from optparse import OptionParser
oParser = OptionParser(usage = "%prog [options]")
oParser.add_option("-c", "--config", dest = "Config",
				help = "general config file",
				metavar = "Config", default = "Config.txt")
(options, args) = oParser.parse_args()
Config = options.Config

PhotoSize = "photo_100"
DefLang = "ru"
evalJID = ""
AdditionalAbout = ""
ConferenceServer = ""

allowBePublic = True

startTime = int(time.time())

try:
	execfile(Config)
	Print("#-# Config loaded successfully.")
except Exception:
	Print("#! Error while loading config file:")
	wException()
	exit()

setVars(DefLang, root)


if THREAD_STACK_SIZE:
	threading.stack_size(THREAD_STACK_SIZE)

logger = logging.getLogger("vk4xmpp")
logger.setLevel(LOG_LEVEL)
loggerHandler = logging.FileHandler(logFile)
Formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(name)s %(message)s",
				"[%d.%m.%Y %H:%M:%S]")
loggerHandler.setFormatter(Formatter)
logger.addHandler(loggerHandler)

def gatewayRev():
	revNumber, rev = 167, 0 # 0. means testing.
	shell = os.popen("git describe --always && git log --pretty=format:''").readlines()
	if shell:
		revNumber, rev = len(shell), shell[0]
	return "#%s-%s" % (revNumber, rev)

OS = "{0} {2:.16} [{4}]".format(*os.uname())
Python = "{0} {1}.{2}.{3}".format(sys.subversion[0], *sys.version_info)
Revision = gatewayRev()

## Events (not finished yet so not sorted):
## 01 - start
## 02 - shutdown
## 03 - user deletion
## 04 - captcha
Handlers = {"msg01": [], "msg02": [],
			"evt01": [], "evt02": [],
			"evt03": [], "evt04": []}

Stats = {"msgin": 0, ## from vk
		 "msgout": 0} ## to vk

def initDatabase(filename):
	if not os.path.exists(filename):
		with Database(filename) as db:
			db("create table users (jid text, username text, token text, lastMsgID integer, rosterSet bool)")
			db.commit()
	return True

def execute(handler, list = ()):
	try:
		handler(*list)
	except SystemExit:
		pass
	except Exception:
		crashLog(handler.func_name)

## TODO: execute threaded handlers
def executeHandlers(type, list = ()):
	for handler in Handlers[type]:
		execute(handler, list)

def startThr(thr, number = 0):
	if number > 2:
		raise RuntimeError("exit")
	try:
		thr.start()
	except threading.ThreadError:
		startThr(thr, (number + 1))

def threadRun(func, args = (), name = None):
	thr = threading.Thread(target = execute, args = (func, args), name = name or func.func_name)
	try:
		thr.start()
	except threading.ThreadError:
		try:
			startThr(thr)
		except RuntimeError:
			thr.run()

badChars = [x for x in xrange(32) if x not in (9, 10, 13)] + [57003, 65535]
escape = re.compile("|".join(unichr(x) for x in badChars), re.IGNORECASE | re.UNICODE | re.DOTALL).sub
msgSort = lambda msgOne, msgTwo: msgOne.get("mid", 0) - msgTwo.get("mid", 0)
require = lambda name: os.path.exists("extensions/%s.py" % name)


class VKLogin(object):

	def __init__(self, number, password = None, source = None):
		self.number = number
		self.password = password
		self.Online = False
		self.source = source
		self.longConfig = {"mode": 66, "wait": 30, "act": "a_check"}
		self.longServer = ""
		self.longInitialized = False
		logger.debug("VKLogin.__init__ with number:%s from jid:%s" % (number, source))

	getToken = lambda self: self.engine.token

	def checkData(self):
		logger.debug("VKLogin: checking data for %s" % self.source)
		if not self.engine.token and self.password:
			logger.debug("VKLogin.checkData: trying to login via password")
			self.engine.loginByPassword()
			self.engine.confirmThisApp()
			if not self.checkToken():
				raise api.VkApiError("Incorrect phone or password")

		elif self.engine.token:
			logger.debug("VKLogin.checkData: trying to use token")
			if not self.checkToken():
				logger.error("VKLogin.checkData: token invalid: %s" % self.engine.token)
				raise api.TokenError("Token for user %s invalid: %s" % (self.source, self.engine.token))
		else:
			logger.error("VKLogin.checkData: no token and password for jid:%s" % self.source)
			raise api.TokenError("%s, Where are your token?" % self.source)

	## TODO: this function must been rewritten. We have dict from self.method, so it's bad way trying make int from dict.
	def checkToken(self):
		try:
			int(self.method("isAppUser", force = True))
		except (api.VkApiError, TypeError):
			return False
		return True

	def auth(self, token = None):
		logger.debug("VKLogin.auth %s token" % ("with" if token else "without"))
		self.engine = api.APIBinding(self.number, self.password, token = token)
		try:
			self.checkData()
		except api.AuthError as e:
			logger.error("VKLogin.auth failed with error %s" % e.message)
			return False
		except Exception:
			crashLog("VKLogin.auth")
			return False
		logger.debug("VKLogin.auth completed")
		self.Online = True
		self.initLongPoll() ## Check if it could be removed in future
		return True

	def initLongPoll(self):
		self.longInitialized = False ## Maybe we called re-init and failed somewhere
		logger.debug("longpoll: requesting server address for user: %s" % self.source)
		try:
			response = self.method("messages.getLongPollServer")
		except Exception:
			return False
		if not response:
			logger.error("longpoll: no response!")
			return False
		self.longServer = "http://%s" % response.pop("server") # hope it will be ok
		self.longConfig.update(response)
		logger.debug("longpoll: server: %s ts: %s" % (self.longServer, self.longConfig["ts"]))
		self.longInitialized = True
		return True

	def makePoll(self):
		if not self.longInitialized:
			raise api.LongPollError()
		return self.engine.RIP.getOpener(self.longServer, self.longConfig)

	def method(self, method, args = None, nodecode = False, force = False):
		args = args or {}
		result = {}
		if not self.engine.captcha and (self.Online or force):
			try:
				result = self.engine.method(method, args, nodecode)
			except api.CaptchaNeeded:
				logger.error("VKLogin: running captcha challenge for %s" % self.source)
				self.captchaChallenge()
				result = 0
			except api.NotAllowed:
				if self.engine.lastMethod[0] == "messages.send":
					msgSend(Component, self.source, _("You're not allowed to perform this action."), vk2xmpp(args.get("user_id", TransportID)))
			except api.VkApiError as e:
				roster = False
				if e.message == "User authorization failed: user revoke access for this token.":
					logger.critical("VKLogin: %s" % e.message)
					roster = True
				elif e.message == "User authorization failed: invalid access_token.":
					msgSend(Component, self.source, _(e.message + " Please, register again"), TransportID)
				try:
					deleteUser(Transport.get(self.source, self), roster, False)
				except KeyError:
					pass

				self.Online = False
				logger.error("VKLogin: apiError %s for user %s" % (e.message, self.source))
			except api.NetworkNotFound:
				logger.critical("VKLogin: network unavailable. Is vk down?")
				self.Online = False
		return result

	def captchaChallenge(self):
		if self.engine.captcha:
			executeHandlers("evt04", (self,))
		else:
			logger.error("VKLogin: captchaChallenge called without captcha for user %s" % self.source)

	def disconnect(self):
		logger.debug("VKLogin: user %s has left" % self.source)
		self.method("account.setOffline")
		self.Online = False

	def getFriends(self, fields = None):
		fields = fields or ["screen_name"]
		friendsRaw = self.method("friends.get", {"fields": ",".join(fields)}) or () # friends.getOnline
		friendsDict = {}
		for friend in friendsRaw:
			uid = friend["uid"]
			name = escape("", u"%s %s" % (friend["first_name"], friend["last_name"]))
			try:
				friendsDict[uid] = {"name": name, "online": friend["online"]}
				for key in fields:
					if key != "screen_name":
						friendsDict[uid][key] = friend.get(key)
			except KeyError:
				continue
		return friendsDict

	def getMessages(self, count = 5, lastMsgID = 0):
		values = {"out": 0, "filters": 1, "count": count}
		if lastMsgID:
			del values["count"]
			values["last_message_id"] = lastMsgID
		return self.method("messages.get", values)

def sendPresence(target, source, pType = None, nick = None, reason = None, caps = None):
	Presence = xmpp.Presence(target, pType, frm = source, status = reason)
	if nick:
		Presence.setTag("nick", namespace = xmpp.NS_NICK)
		Presence.setTagData("nick", nick)
	if caps:
		Presence.setTag("c", {"node": "http://simpleapps.ru/caps/vk4xmpp", "ver": Revision}, xmpp.NS_CAPS)
	Sender(Component, Presence)

class User(object):

	def __init__(self, data = (), source = ""):
		self.password = None
		if data:
			self.username, self.password = data
		self.friends = {}
		self.auth = None
		self.token = None
		self.lastMsgID = None
		self.rosterSet = None
		self.existsInDB = None
		self.last_udate = time.time()
		self.typing = {}
		self.source = source
		self.resources = []
		self.chatUsers = {}
		self.__sync = threading._allocate_lock()
		self.vk = VKLogin(self.username, self.password, self.source)
		logger.debug("initializing User for %s" % self.source)
		with Database(DatabaseFile, Semaphore) as db:
			db("select * from users where jid=?", (self.source,))
			desc = db.fetchone()
			if desc:
				if not self.token or not self.password:
					logger.debug("User: %s exists in db. Have to use it." % self.source)
					self.existsInDB = True
					self.source, self.username, self.token, self.lastMsgID, self.rosterSet = desc
				elif self.password or self.token:
					logger.debug("User: %s exists in db. Record would be deleted." % self.source)
					threadRun(deleteUser, (self,))

	def __eq__(self, user):
		if isinstance(user, User):
			return user.source == self.source
		return self.source == user

	def msg(self, body, id, mType="user_id", more={}):
		try:
			Stats["msgout"] += 1
			values = {mType: id, "message": body, "type": 0}
			values.update(more)
			Message = self.vk.method("messages.send", values)
		except Exception:
			crashLog("messages.send")
			Message = None
		return Message

	def connect(self):
		logger.debug("User: connecting %s" % self.source)
		self.auth = False
		## TODO: Check code below
		try:
			self.auth = self.vk.auth(self.token)
		except api.CaptchaNeeded:
			self.rosterSubscribe()
			self.vk.captchaChallenge()
			return True
		else:
			logger.debug("User: auth=%s for %s" % (self.auth, self.source))

		if self.auth and self.vk.getToken():
			logger.debug("User: updating db for %s because auth done " % self.source)
			if not self.existsInDB:
				with Database(DatabaseFile, Semaphore) as db:
					db("insert into users values (?,?,?,?,?)", (self.source, "",
						self.vk.getToken(), self.lastMsgID, self.rosterSet))
			elif self.password:
				with Database(DatabaseFile, Semaphore) as db:
					db("update users set token=? where jid=?", (self.vk.getToken(), self.source))

			self.getUserID()
			self.friends = self.vk.getFriends()
			self.vk.Online = True
		if not UseLastMessageID:
			self.lastMsgID = 0
		return self.vk.Online

	def getUserID(self):
		try:
			json = self.vk.method("users.get")
			self.UserID = json[0]["uid"]
		except (KeyError, TypeError):
			logger.error("User: could not recieve user id. JSON: %s" % str(json))
			self.UserID = 0

		if self.UserID:
			jidToID[self.UserID] = self.source
		return self.UserID

	def init(self, force = False, send = True):
		logger.debug("User: called init for user %s" % self.source)
		if not self.friends:
			self.friends = self.vk.getFriends()
		if self.friends and not self.rosterSet or force:
			logger.debug("User: calling subscribe with force:%s for %s" % (force, self.source))
			self.rosterSubscribe(self.friends)
		if send: self.sendInitPresence()
		self.sendMessages(True)

## TODO: Move this function otside class

	def sendInitPresence(self):
		if not self.friends:
			self.friends = self.vk.getFriends()
		logger.debug("User: sending init presence to %s (friends %s)" %
					(self.source, "exists" if self.friends else "empty"))
		for uid, value in self.friends.iteritems():
			if value["online"]:
				sendPresence(self.source, vk2xmpp(uid), None, value["name"], caps=True)
		sendPresence(self.source, TransportID, None, IDentifier["name"], caps=True)

	def sendOutPresence(self, target, reason=None):
		logger.debug("User: sending out presence to %s" % self.source)
		for uid in self.friends.keys() + [TransportID]:
			sendPresence(target, vk2xmpp(uid), "unavailable", reason=reason)

	def rosterSubscribe(self, dist=None):
		dist = dist or {}
		for uid, value in dist.iteritems():
			sendPresence(self.source, vk2xmpp(uid), "subscribe", value["name"])
		sendPresence(self.source, TransportID, "subscribe", IDentifier["name"])
		if dist:
			self.rosterSet = True
			with Database(DatabaseFile, Semaphore) as db:
				db("update users set rosterSet=? where jid=?",
					(self.rosterSet, self.source))

	def getUserData(self, uid, fields=None):
		if not fields:
			if uid in self.friends:
				return self.friends[uid]
			fields = ["screen_name"]
		data = self.vk.method("users.get", {"fields": ",".join(fields), "user_ids": uid}) or {}
		if not data:
			data = {"name": "None"}
			for key in fields:
				data[key] = "None"
		else:
			data = data.pop()
			data["name"] = escape("", u"%s %s" % (data.pop("first_name"), data.pop("last_name")))
		return data

	def sendMessages(self, init=False):
		with self.__sync:
			date = 0
			messages = self.vk.getMessages(200, self.lastMsgID if UseLastMessageID else 0)
			if not messages or not messages[0]:
				return None
			messages = sorted(messages[1:], msgSort)
			for message in messages:
				if message["out"]:
					continue
				Stats["msgin"] += 1
				fromjid = vk2xmpp(message["uid"])
				body = uHTML(message["body"])
				iter = Handlers["msg01"].__iter__()
				for func in iter:
					try:
						result = func(self, message)
					except Exception:
						result = None
						crashLog("handle.%s" % func.__name__)
					if result is None:
						for func in iter:
							apply(func, (self, message))
						break
					else:
						body += result
				else:
					if init:
						date = message["date"]
					msgSend(Component, self.source, escape("", body), fromjid, date)
			if messages:
				lastMsg = messages[-1]
				self.lastMsgID = lastMsg["mid"]
				if UseLastMessageID:
					with Database(DatabaseFile, Semaphore) as db:
						db("update users set lastMsgID=? where jid=?", (self.lastMsgID, self.source))

	def processPollResult(self, opener):
		try:
			data = opener.read()
		except socket.error:
			return 1

		if self.vk.engine.captcha:
			opener.close()
			return -1
	
		if not self.UserID:
			self.getUserID()

		if not data:
			logger.error("longpoll: no data. Will ask again.")
			return 1
		try:
			data = json.loads(data)
		except Exception:
			return 1

		if "failed" in data:
			logger.debug("longpoll: failed. Searching for new server.")
			return 0

		self.vk.longConfig["ts"] = data["ts"]
		for evt in data.get("updates", ()):
			typ = evt.pop(0)
			if typ == 4:  # message
				threadRun(self.sendMessages)
			elif typ == 8: # user online
				uid = abs(evt[0])
				sendPresence(self.source, vk2xmpp(uid), nick = self.getUserData(uid)["name"], caps = True)
			elif typ == 9: # user leaved
				uid = abs(evt[0])
				sendPresence(self.source, vk2xmpp(uid), "unavailable")
			elif typ == 61: # user typing
				if evt[0] not in self.typing:
					userTyping(self.source, vk2xmpp(evt[0]))
				self.typing[evt[0]] = time.time()
		return 1

	def updateTypingUsers(self, cTime):
		for user, last in self.typing.items():
			if cTime - last > 5:
				del self.typing[user]
				userTyping(self.source, vk2xmpp(user), "paused")

	def updateFriends(self, cTime):
		if cTime - self.last_udate > 360:
			self.vk.method("account.setOnline")
			self.last_udate = cTime
			friends = self.vk.getFriends()
			if not friends:
				logger.error("updateFriends: no friends received (user: %s)." % self.source)
				return None
			if friends:
				for uid in friends:
					if uid not in self.friends:
						self.rosterSubscribe({uid: friends[uid]})
				for uid in self.friends:
					if uid not in friends:
						sendPresence(self.source, vk2xmpp(uid), "unsubscribe")
						sendPresence(self.source, vk2xmpp(uid), "unsubscribed")
				self.friends = friends

	def tryAgain(self):
		logger.debug("calling reauth for user %s" % self.source)
		try:
			if not self.vk.Online:
				self.connect()
			self.init(True)
		except Exception:
			crashLog("tryAgain")

def deleteUser(user, roster = False, semph = Semaphore):
	logger.debug("User: deleting user %s from db." % user.source)
	with Database(DatabaseFile, semph) as db: ## WARNING: this may cause main thread lock
		db("delete from users where jid=?", (user.source,))
		db.commit()
	user.existsInDB = False
	friends = getattr(user, "friends", {})
	if roster and friends:
		logger.debug("User: deleting me from %s roster" % user.source)
		for id in friends.keys():
			jid = vk2xmpp(id)
			sendPresence(user.source, jid, "unsubscribe")
			sendPresence(user.source, jid, "unsubscribed")
		
	elif roster:
		sendPresence(user.source, TransportID, "unsubscribe")
		sendPresence(user.source, TransportID, "unsubscribed")
		executeHandlers("evt03", (user,))

	vk = getattr(user, "vk", user)
	if user.source in Transport:
		vk.Online = False
		del Transport[user.source]
	Poll.remove(user)

def Sender(cl, stanza):
	try:
		cl.send(stanza)
	except Exception:
		crashLog("Sender")

def msgSend(cl, destination, body, source, timestamp = 0):
	msg = xmpp.Message(destination, body, "chat", frm = source)
	msg.setTag("active", namespace = xmpp.NS_CHATSTATES)
	if timestamp:
		timestamp = time.gmtime(timestamp)
		msg.setTimestamp(time.strftime("%Y%m%dT%H:%M:%S", timestamp))
	Sender(cl, msg)

def apply(instance, args = ()):
	try:
		code = instance(*args)
	except Exception:
		code = None
	return code

isNumber = lambda obj: (not apply(int, (obj,)) is None)

def vk2xmpp(id):
	if not isNumber(id) and "@" in id:
		id = id.split("@")[0]
		if isNumber(id):
			id = int(id)
	elif id != TransportID:
		id = u"%s@%s" % (id, TransportID)
	return id

DESC = _("© simpleApps, 2013 — 2014."
	"\nYou can support developing of this project"
	" via donation by:\nYandex.Money: 410012169830956"
	"\nWebMoney: Z405564701378 | R330257574689.")

def getPid():
	nowPid = os.getpid()
	if os.path.exists(pidFile):
		oldPid = rFile(pidFile)
		if oldPid:
			Print("#-# Killing old transport instance: ", False)
			oldPid = int(oldPid)
			if nowPid != oldPid:
				try:
					os.kill(oldPid, 15)
					time.sleep(3)
					os.kill(oldPid, 9)
				except OSError:
					pass
				Print("%d killed.\n" % oldPid, False)
	wFile(pidFile, str(nowPid))

## TODO: remove this function and add it's code into msgSend.
def userTyping(target, instance, typ = "composing"):
	message = xmpp.Message(target, typ = "chat", frm = instance)
	message.setTag(typ, namespace = xmpp.NS_CHATSTATES)
	Sender(Component, message)


## TODO: make it as extension
def watcherMsg(text):
	for jid in WatcherList:
		msgSend(Component, jid, text, TransportID)

def disconnectHandler(crash = True):
	if crash:
		crashLog("main.disconnect")
	Poll.clear()
	try:
		if Component.isConnected():
			Component.disconnect()
	except (NameError, AttributeError):
		pass
	executeHandlers("evt02")
	Print("Reconnecting...")
	time.sleep(5)
	os.execl(sys.executable, sys.executable, *sys.argv)

## Public transport's list: http://anakee.ru/vkxmpp
def makeMeKnown():
	if WhiteList:
		WhiteList.append("anon.anakee.ru")
	if TransportID.split(".")[1] != "localhost":
		RIP = api.RequestProcessor()
		RIP.post("http://anakee.ru/vkxmpp/hosts.php", {"add": TransportID})
		Print("#! Information about myself successfully published.")

def garbageCollector():
	while True:
		time.sleep(60)
		gc.collect()

class Poll:

	__poll = {}
	__buff = set()
	__lock = threading._allocate_lock()

	@classmethod
	def __add(cls, user):
		try:
			opener = user.vk.makePoll()
		except Exception as e:
			logger.error("longpoll: failed make poll for user %s" % user.source)
			cls.__addToBuff(user)
		else:
			cls.__poll[opener.sock] = (user, opener)

	@classmethod
	def __addToBuff(cls, user):
		cls.__buff.add(user)
		logger.debug("longpoll: adding user %s to watcher" % user.source)
		threadRun(cls.__initPoll, (user,), cls.__initPoll.__name__)

	@classmethod
	def add(cls, some_user):
		with cls.__lock:
			if some_user in cls.__buff:
				return None
			for sock, (user, opener) in cls.__poll.iteritems():
				if some_user == user:
					break
			else:
				cls.__add(some_user)

	@classmethod
	def remove(cls, some_user):
		with cls.__lock:
			if some_user in cls.__buff:
				return cls.__buff.remove(some_user)
			for sock, (user, opener) in cls.__poll.iteritems():
				if some_user == user:
					del cls.__poll[sock]
					opener.close()
					break

	clear = staticmethod(__poll.clear)

	@classmethod
	def __initPoll(cls, user):
		for x in xrange(10):
			if user.source not in Transport:
				logger.debug("longpoll: while we wasted our time user %s has left" % user.source)
				with cls.__lock:
					if user in cls.__buff:
						cls.__buff.remove(user)
				return None
			if Transport[user.source].vk.initLongPoll():
				with cls.__lock:
					logger.debug("longpoll: %s successfully initialized longpoll" % user.source)
					if user not in cls.__buff:
						return None
					cls.__buff.remove(user)
					cls.__add(Transport[user.source])
					break
			time.sleep(10)
		else:
			with cls.__lock:
				if user not in cls.__buff:
					return None
				cls.__buff.remove(user)
			logger.error("longpoll: failed to add %s to poll in 10 retries" % user.source)

	@classmethod
	def process(cls):
		while True:
			socks = cls.__poll.keys()
			if not socks:
				time.sleep(0.02)
				continue
			try:
				ready, error = select.select(socks, [], socks, 2)[::2]
			except (select.error, socket.error) as e:
				continue

			for sock in error:
				with cls.__lock:
					try:
						cls.__add(cls.__poll.pop(sock)[0])
					except KeyError:
						continue
			for sock in ready:
				with cls.__lock:
					try:
						user, opener = cls.__poll.pop(sock)
					except KeyError:
						continue
					user = Transport.get(user.source)
					if not user:
						continue
					result = user.processPollResult(opener)
					if result == -1:
						continue
					elif result:
						cls.__add(user)
					else:
						cls.__addToBuff(user)

def updateCron():
	while True:
		for user in Transport.values():
			cTime = time.time()
			user.updateTypingUsers(cTime)
			user.updateFriends(cTime)
		time.sleep(2)

def main():
	global Component
	getPid()
	initDatabase(DatabaseFile)
	Component = xmpp.Component(Host, debug = DEBUG_XMPPPY)
	Print("\n#-# Connecting: ", False)
	if not Component.connect((Server, Port)):
		Print("fail.\n", False)
	else:
		Print("ok.\n", False)
		Print("#-# Auth: ", False)
		if not Component.auth(TransportID, Password):
			Print("fail (%s/%s)!\n" % (Component.lastErr, Component.lastErrCode), True)
			disconnectHandler(False)
		else:
			Print("ok.\n", False)
			Component.RegisterHandler("iq", iqHandler)
			Component.RegisterHandler("presence", prsHandler)
			Component.RegisterHandler("message", msgHandler)
			Component.RegisterDisconnectHandler(disconnectHandler)
			Component.set_send_interval(0.03125) # 32 messages per second
			Print("#-# Initializing users", False)
			with Database(DatabaseFile) as db:
				users = db("select jid from users").fetchall()
				for user in users:
					Print(".", False)
					Sender(Component, xmpp.Presence(user[0], "probe", frm = TransportID))
			Print("\n#-# Finished.")
			if allowBePublic:
				makeMeKnown()
			for num, event in enumerate(Handlers["evt01"]):
				threadRun(event, (), "extension-%d" % num)
			threadRun(garbageCollector, (), "gc")
			threadRun(Poll.process, (), "longPoll")
			threadRun(updateCron, (), "updateCron")

def exit(signal = None, frame = None):
	status = "Shutting down by %s" % ("SIGTERM" if signal == 15 else "SIGINT")
	Print("#! %s" % status, False)
	for user in Transport.itervalues():
		user.sendOutPresence(user.source, status)
		Print("." * len(user.friends), False)
	Print("\n")
	executeHandlers("evt02")
	try:
		os.remove(pidFile)
	except OSError:
		pass
	os._exit(1)

def loadSomethingMore(dir):
	for something in os.listdir(dir):
		execfile("%s/%s" % (dir, something), globals())

if __name__ == "__main__":
	signal.signal(signal.SIGTERM, exit)
	signal.signal(signal.SIGINT, exit)
	loadSomethingMore("extensions")
	loadSomethingMore("handlers")
	main()
	while True:
		try:
			Component.iter(6)
		except Exception:
			logger.critical("DISCONNECTED")
			crashLog("Component.iter")
			disconnectHandler(True)

########NEW FILE########
__FILENAME__ = IQ
# coding: utf-8
# This file is a part of VK4XMPP transport
# © simpleApps, 2013 — 2014.

def iqHandler(cl, iq):
	jidFrom = iq.getFrom()
	source = jidFrom.getStripped()
	if WhiteList:
		if jidFrom and jidFrom.getDomain() not in WhiteList:
			Sender(cl, iqBuildError(iq, xmpp.ERR_BAD_REQUEST, "You're not in the white-list"))
			raise xmpp.NodeProcessed()

	if iq.getType() == "set" and iq.getTagAttr("captcha", "xmlns") == xmpp.NS_CAPTCHA:
		if source in Transport:
			jidTo = iq.getTo()
			if jidTo == TransportID:
				cTag = iq.getTag("captcha")
				cxTag = cTag.getTag("x", {}, xmpp.NS_DATA)
				fcxTag = cxTag.getTag("field", {"var": "ocr"})
				cValue = fcxTag.getTagData("value")
				captchaAccept(cl, cValue, jidTo, source)

	ns = iq.getQueryNS()
	if ns == xmpp.NS_REGISTER:
		iqRegisterHandler(cl, iq)
	elif ns == xmpp.NS_GATEWAY:
		iqGatewayHandler(cl, iq)
	elif ns == xmpp.NS_STATS:
		iqStatsHandler(cl, iq)
	elif ns == xmpp.NS_VERSION:
		iqVersionHandler(cl, iq)
	elif ns == xmpp.NS_LAST:
		iqUptimeHandler(cl, iq)
	elif ns in (xmpp.NS_DISCO_INFO, xmpp.NS_DISCO_ITEMS):
		iqDiscoHandler(cl, iq)
	else:
		Tag = iq.getTag("vCard") or iq.getTag("ping")
		if Tag and Tag.getNamespace() == xmpp.NS_VCARD:
			iqVcardHandler(cl, iq)
		elif Tag and Tag.getNamespace() == xmpp.NS_PING:
			jidTo = iq.getTo()
			if jidTo == TransportID:
				Sender(cl, iq.buildReply("result"))


def iqBuildError(stanza, error = None, text = None):
	if not error:
		error = xmpp.ERR_FEATURE_NOT_IMPLEMENTED
	error = xmpp.Error(stanza, error, True)
	if text:
		eTag = error.getTag("error")
		eTag.setTagData("text", text)
	return error

URL_ACCEPT_APP = "http://simpleapps.ru/vk4xmpp.html"

def iqRegisterHandler(cl, iq):
	jidTo = iq.getTo()
	jidFrom = iq.getFrom()
	source = jidFrom.getStripped()
	destination = jidTo.getStripped()
	iType = iq.getType()
	IQChildren = iq.getQueryChildren()
	result = iq.buildReply("result")
	if USER_LIMIT:
		count = calcStats()[0]
		if count >= USER_LIMIT and not source in Transport:
			cl.send(iqBuildError(iq, xmpp.ERR_NOT_ALLOWED, _("Transport's admins limited registrations, sorry.")))
			raise xmpp.NodeProcessed()

	if iType == "get" and destination == TransportID and not IQChildren:
		form = xmpp.DataForm()
		logger.debug("Sending register form to %s" % source)
		form.addChild(node=xmpp.Node("instructions")).setData(_("Type data in fields")) ## TODO: Complete this by forms
		link = form.setField("link", URL_ACCEPT_APP, "text-single")
		link.setLabel(_("Autorization page"))
		link.setDesc(_("If you won't get access-token automatically, please, follow authorization link and authorize app,\n"\
					   "and then paste url to password field."))
		phone = form.setField("phone", "+", "text-single")
		phone.setLabel(_("Phone number"))
		phone.setDesc(_("Enter phone number in format +71234567890"))
		use_password = form.setField("use_password", "0", "boolean")
		use_password.setLabel(_("Get access-token automatically"))
		use_password.setDesc(_("Try to get access-token automatically. (NOT recommented, password required!)"))
		password = form.setField("password", None, "text-private")
		password.setLabel(_("Password/Access-token"))
		password.setDesc(_("Type password, access-token or url (recommented)"))
		result.setQueryPayload((form,))

	elif iType == "set" and destination == TransportID and IQChildren:
		phone, password, usePassword, token = False, False, False, False
		Query = iq.getTag("query")
		if Query.getTag("x"):
			for node in iq.getTags("query", namespace = xmpp.NS_REGISTER):
				for node in node.getTags("x", namespace = xmpp.NS_DATA):
					phone = node.getTag("field", {"var": "phone"})
					phone = phone and phone.getTagData("value")
					password = node.getTag("field", {"var": "password"})
					password = password and password.getTagData("value")
					usePassword = node.getTag("field", {"var": "use_password"})
					usePassword = usePassword and usePassword.getTagData("value")

			if not password:
				result = iqBuildError(iq, xmpp.ERR_BAD_REQUEST, _("Empty password"))
			if not isNumber(usePassword):
				if usePassword and usePassword.lower() == "true":
					usePassword = 1
				else:
					usePassword = 0
			usePassword = int(usePassword)
			if not usePassword:
				logger.debug("user %s won't use password" % source)
				token = password
				password = None
			else:
				logger.debug("user %s wants use password" % source)
				if not phone:
					result = iqBuildError(iq, xmpp.ERR_BAD_REQUEST, _("Phone incorrect."))
			if source in Transport:
				user = Transport[source]
				deleteUser(user, semph = False)
			else:
				user = User((phone, password), source)
			if not usePassword:
				try:
					token = token.split("#access_token=")[1].split("&")[0].strip()
				except (IndexError, AttributeError):
					pass
				user.token = token
			if not user.connect():
				logger.error("user %s connection failed (from iq)" % source)
				result = iqBuildError(iq, xmpp.ERR_BAD_REQUEST, _("Incorrect password or access token!"))
			else:
				try:
					user.init()
				except api.CaptchaNeeded:
					user.vk.captchaChallenge()
				except Exception:
					crashLog("iq.user.init")
					result = iqBuildError(iq, xmpp.ERR_BAD_REQUEST, _("Initialization failed."))
				else:
					Transport[source] = user
					Poll.add(Transport[source])
					watcherMsg(_("New user registered: %s") % source)

		elif Query.getTag("remove"): # Maybe exits a better way for it
			logger.debug("user %s wants remove me..." % source)
			if source in Transport:
				user = Transport[source]
				deleteUser(user, True, False)
				result.setPayload([], add = 0)
				watcherMsg(_("User removed registration: %s") % source)
			else:
				logger.debug("... but he do not know he already removed!")

		else:
			result = iqBuildError(iq, 0, _("Feature not implemented."))
	Sender(cl, result)

def calcStats():
	countTotal = 0
	countOnline = len(Transport)
	with Database(DatabaseFile, Semaphore) as db:
		db("select count(*) from users")
		countTotal = db.fetchone()[0]
	return [countTotal, countOnline]

def iqUptimeHandler(cl, iq):
	jidFrom = iq.getFrom()
	jidTo = iq.getTo()
	iType = iq.getType()
	if iType == "get" and jidTo == TransportID:
		uptime = int(time.time() - startTime)
		result = xmpp.Iq("result", to = jidFrom)
		result.setID(iq.getID())
		result.setTag("query", {"seconds": str(uptime)}, xmpp.NS_LAST)
		result.setTagData("query", IDentifier["name"])
		Sender(cl, result)

def iqVersionHandler(cl, iq):
	iType = iq.getType()
	jidTo = iq.getTo()
	if iType == "get" and jidTo == TransportID:
		result = iq.buildReply("result")
		Query = result.getTag("query")
		Query.setTagData("name", IDentifier["name"])
		Query.setTagData("version", Revision)
		Query.setTagData("os", "%s / %s" % (OS, Python))
		Sender(cl, result)

sDict = {
		"users/total": "users",
		"users/online": "users",
		"memory/virtual": "KB",
		"memory/real": "KB",
		"cpu/percent": "percent",
		"cpu/time": "seconds",
		"thread/active": "threads",
		"msg/in": "messages",
		"msg/out": "messages"
		}

def iqStatsHandler(cl, iq):
	destination = iq.getTo()
	iType = iq.getType()
	IQChildren = iq.getQueryChildren()
	result = iq.buildReply("result")
	if iType == "get" and destination == TransportID:
		QueryPayload = list()
		if not IQChildren:
			keys = sorted(sDict.keys(), reverse = True)
			for key in keys:
				Node = xmpp.Node("stat", {"name": key})
				QueryPayload.append(Node)
		else:
			users = calcStats()
			shell = os.popen("ps -o vsz,rss,%%cpu,time -p %s" % os.getpid()).readlines()
			memVirt, memReal, cpuPercent, cpuTime = shell[1].split()
			stats = {"users": users, "KB": [memVirt, memReal],
					 "percent": [cpuPercent], "seconds": [cpuTime], "threads": [threading.activeCount()],
					 "messages": [Stats["msgout"], Stats["msgin"]]}
			for Child in IQChildren:
				if Child.getName() != "stat":
					continue
				name = Child.getAttr("name")
				if name in sDict:
					attr = sDict[name]
					value = stats[attr].pop(0)
					Node = xmpp.Node("stat", {"units": attr})
					Node.setAttr("name", name)
					Node.setAttr("value", value)
					QueryPayload.append(Node)
		if QueryPayload:
			result.setQueryPayload(QueryPayload)
			Sender(cl, result)

def iqDiscoHandler(cl, iq):
	source = iq.getFrom().getStripped()
	destination = iq.getTo().getStripped()
	iType = iq.getType()
	ns = iq.getQueryNS()
	Node = iq.getTagAttr("query", "node")
	if iType == "get":
		if not Node:
			QueryPayload = []
			if destination == TransportID:
				features = TransportFeatures
			else:
				features = UserFeatures

			result = iq.buildReply("result")
			QueryPayload.append(xmpp.Node("identity", IDentifier))
			if ns == xmpp.NS_DISCO_INFO:
				for key in features:
					xNode = xmpp.Node("feature", {"var": key})
					QueryPayload.append(xNode)
				result.setQueryPayload(QueryPayload)
			
			elif ns == xmpp.NS_DISCO_ITEMS:
				result.setQueryPayload(QueryPayload)

			Sender(cl, result)

def iqGatewayHandler(cl, iq):
	jidTo = iq.getTo()
	iType = iq.getType()
	destination = jidTo.getStripped()
	IQChildren = iq.getQueryChildren()
	if destination == TransportID:
		result = iq.buildReply("result")
		if iType == "get" and not IQChildren:
			query = xmpp.Node("query", {"xmlns": xmpp.NS_GATEWAY})
			query.setTagData("desc", "Enter api token")
			query.setTag("prompt")
			result.setPayload([query])

		elif IQChildren and iType == "set":
			token = ""
			for node in IQChildren:
				if node.getName() == "prompt":
					token = node.getData()
					break
			if token:
				xNode = xmpp.simplexml.Node("prompt")
				xNode.setData(token[0])
				result.setQueryPayload([xNode])
		else:
			raise xmpp.NodeProcessed()
		Sender(cl, result)

def vCardGetPhoto(url, encode = True):
	try:
		opener = urllib.urlopen(url)
		data = opener.read()
		if data and encode:
			data = data.encode("base64")
		return data
	except IOError:
		pass
	except Exception:
		crashLog("vcard.getPhoto")

def iqVcardBuild(tags):
	vCard = xmpp.Node("vCard", {"xmlns": xmpp.NS_VCARD})
	for key in tags.keys():
		if key == "PHOTO":
			binVal = vCard.setTag("PHOTO")
			binVal.setTagData("BINVAL", vCardGetPhoto(tags[key]))
		else:
			vCard.setTagData(key, tags[key])
	return vCard

def iqVcardHandler(cl, iq):
	jidFrom = iq.getFrom()
	jidTo = iq.getTo()
	source = jidFrom.getStripped()
	destination = jidTo.getStripped()
	iType = iq.getType()
	result = iq.buildReply("result")
	if iType == "get":
		_DESC = '\n'.join((DESC, "_" * 16, AdditionalAbout)) if AdditionalAbout else DESC
		if destination == TransportID:
			vcard = iqVcardBuild({"NICKNAME": "VK4XMPP Transport",
								"DESC": _DESC,
								"PHOTO": "https://raw.github.com/mrDoctorWho/vk4xmpp/master/vk4xmpp.png",
								"URL": "http://simpleapps.ru"
								})
			result.setPayload([vcard])

		elif source in Transport:
			user = Transport[source]
			if user.friends:
				id = vk2xmpp(destination)
				json = user.getUserData(id, ["screen_name", PhotoSize])
				values = {"NICKNAME": json.get("name", str(json)),
						"URL": "http://vk.com/id%s" % id,
						"DESC": _("Contact uses VK4XMPP Transport\n%s") % _DESC
						}
				if id in user.friends.keys():
					values["PHOTO"] = json.get(PhotoSize) or URL_VCARD_NO_IMAGE
				vCard = iqVcardBuild(values)
				result.setPayload([vCard])
			else:
				result = iqBuildError(iq, xmpp.ERR_BAD_REQUEST, _("Your friend-list is empty."))
		else:
			result = iqBuildError(iq, xmpp.ERR_REGISTRATION_REQUIRED, _("You're not registered for this action."))
	else:
		raise xmpp.NodeProcessed()
	Sender(cl, result)

########NEW FILE########
__FILENAME__ = Message
# coding: utf-8
# This file is a part of VK4XMPP transport
# © simpleApps, 2013 — 2014.

import urllib
import random

def msgRecieved(msg, jidFrom, jidTo):
	if msg.getTag("request"):
		answer = xmpp.Message(jidFrom)
		tag = answer.setTag("received", namespace = "urn:xmpp:receipts")
		tag.setAttr("id", msg.getID())
		answer.setFrom(jidTo)
		answer.setID(msg.getID())
		return answer

def sendPhoto(user, data, type, address, mType):
	mask = user.vk.method("account.getAppPermissions")

	if mType == "chat_id":
		address = address.split("@")[0].split("#")[1]
		send = False
	else:
		destination = address
		address = vk2xmpp(address)
		send = True

	if address == TransportID:
		answer = _("Are you kidding me?")
	elif mask:
		if mask & 4 == 4: ## we have enough access?
			ext = type.split("/")[1]
			name = "vk4xmpp_%s.%s" % (random.randint(1000, 9000), ext)
			server = str(user.vk.method("photos.getMessagesUploadServer")["upload_url"])
			response = json.loads(user.vk.engine.RIP.post(
					server, 
					user.vk.engine.RIP.multipart("photo", str(name), str(type), data),
					urlencode = False)[0])
			
			photo = user.vk.method("photos.saveMessagesPhoto", response)[0]
			id = photo["id"]

			user.msg("", address, mType, {"attachment": id})
			logger.debug("sendPhoto: image was successfully sent by user %s" % user.source)
			answer = _("Your image was successfully sent.")
		else:
			answer = _("Sorry but we have failed to send this image."
				 	" Seems you haven't enough permissions. Your token should be updated, register again.")
	else:
		answer = _("Something went wrong. We are so sorry.")
	if send:
		msgSend(Component, user.source, answer, destination, timestamp = 1)

def xhtmlParse(user, html, source, destination, mType = "user_id"):
	body = html.getTag("body")
	if body:
		## TODO: Maybe would be better use regular expressions?
		src = body.getTagAttr("img", "src")
		raw_data = src.split("data:")[1]
		mime_type = raw_data.split(";")[0]
		data = raw_data.split("base64,")[1]
		if data:
			try:
				data = urllib.unquote(data).decode("base64")
			except Exception:
				logger.error("xhmtlParse: fetched wrong xhtml image from %s" % source)
				return False
			threadRun(sendPhoto, (user, data, mime_type, destination, mType))
	return True

def msgHandler(cl, msg):
	mType = msg.getType()
	body = msg.getBody()
	jidTo = msg.getTo()
	destination = jidTo.getStripped()
	jidFrom = msg.getFrom()
	source = jidFrom.getStripped()
	html = msg.getTag("html")

	if source in Transport and mType == "chat":
		user = Transport[source]
		if msg.getTag("composing"):
			target = vk2xmpp(destination)
			if target != TransportID:
				user.vk.method("messages.setActivity", {"user_id": target, "type": "typing"}, True)

		if html and html.getTag("body"): ## XHTML-IM!
			logger.debug("msgHandler: fetched xhtml image from %s" % source)
			try:
				xhtml = xhtmlParse(user, html, source, destination)
			except Exception:
				xhtml = False
			if xhtml:
				raise xmpp.NodeProcessed()

		if body:
			answer = None
			if jidTo == TransportID:
				raw = body.split(None, 1)
				if len(raw) > 1:
					text, args = raw
					args = args.strip()
					if text == "!captcha" and args:
						captchaAccept(cl, args, jidTo, source)
						answer = msgRecieved(msg, jidFrom, jidTo)
					elif text == "!eval" and args and source == evalJID:
						try:
							result = unicode(eval(args))
						except Exception:
							result = returnExc()
						msgSend(cl, source, result, jidTo)
					elif text == "!exec" and args and source == evalJID:
						try:
							exec(unicode(args + "\n"), globals())
						except Exception:
							result = returnExc()
						else:
							result = "Done."
						msgSend(cl, source, result, jidTo)
			else:
				uID = jidTo.getNode()
				vkMessage = user.msg(body, uID)
				if vkMessage:
					answer = msgRecieved(msg, jidFrom, jidTo)
			if answer:
				Sender(cl, answer)
	for func in Handlers["msg02"]:
		func(msg)
		

def captchaAccept(cl, args, jidTo, source):
	if args:
		answer = None
		user = Transport[source]
		if user.vk.engine.captcha:
			logger.debug("user %s called captcha challenge" % source)
			user.vk.engine.captcha["key"] = args
			retry = False
			try:
				logger.debug("retrying for user %s" % source)
				retry = user.vk.engine.retry()
			except api.CaptchaNeeded:
				logger.error("retry for user %s failed!" % source)
				user.vk.captchaChallenge()
			if retry:
				logger.debug("retry for user %s OK" % source)
				answer = _("Captcha valid.")
				Poll.add(user)
				Presence = xmpp.protocol.Presence(source, frm = TransportID)
				Presence.setShow("available")
				Sender(Component, Presence)
				user.tryAgain()
			else:
				answer = _("Captcha invalid.")
		else:
			answer = _("Not now. Ok?")
		if answer:
			msgSend(cl, source, answer, jidTo)

########NEW FILE########
__FILENAME__ = Presence
# coding: utf-8
# This file is a part of VK4XMPP transport
# © simpleApps, 2013 — 2014.


def prsHandler(cl, prs):
	pType = prs.getType()
	jidFrom = prs.getFrom()
	jidTo = prs.getTo()
	source = jidFrom.getStripped()
	destination = jidTo.getStripped()
	resource = jidFrom.getResource()
	if source in Transport:
		user = Transport[source]
		if pType in ("available", "probe", None):
			if jidTo == TransportID and resource not in user.resources:
				logger.debug("%s from user %s, will send sendInitPresence" % (pType, source))
				user.resources.append(resource)
				user.sendInitPresence()

		elif pType == "unavailable":
			if jidTo == TransportID and resource in user.resources:
				user.resources.remove(resource)
				if user.resources:
					user.sendOutPresence(jidFrom)
			if not user.resources:
				Sender(cl, xmpp.Presence(jidFrom, "unavailable", frm = TransportID))
				user.vk.disconnect()
				Poll.remove(user)
				try:
					del Transport[source]
				except KeyError:
					pass
	
		elif pType == "error":
			eCode = prs.getErrorCode()
			if eCode == "404":
				user.vk.disconnect()

		elif pType == "subscribe":
			if destination == TransportID:
				Sender(cl, xmpp.Presence(source, "subscribed", frm = TransportID))
				Sender(cl, xmpp.Presence(jidFrom, frm = TransportID))
			else:
				Sender(cl, xmpp.Presence(source, "subscribed", frm = jidTo))
				if user.friends:
					id = vk2xmpp(destination)
					if id in user.friends:
						if user.friends[id]["online"]:
							Sender(cl, xmpp.Presence(jidFrom, frm = jidTo))
	
		elif pType == "unsubscribe":
			if source in Transport and destination == TransportID:
				deleteUser(user, True, False)
				watcherMsg(_("User removed registration: %s") % source)


	elif pType in ("available", None) and destination == TransportID:
		logger.debug("User %s not in transport but want to be in" % source)
		with Database(DatabaseFile) as db:
			db("select jid,username from users where jid=?", (source,))
			data = db.fetchone()
			if data:
				logger.debug("User %s has been found in db" % source)
				jid, phone = data
				Transport[jid] = user = User((phone, None), jid)
				try:
					if user.connect():
						user.init(None, True) ## Maybe do it in another thread. 
						user.resources.append(resource)
						Poll.add(user)
					else:
						crashLog("prs.connect", 0, False)
						msgSend(Component, jid, _("Auth failed! If this error repeated, please register again. This incident will be reported."), TransportID)
				except Exception:
					crashLog("prs.init")

########NEW FILE########
__FILENAME__ = itypes
"""
Module "itypes"
itypes.py

Copyright (2010-2013) Al Korgun (alkorgun@gmail.com)

Distributed under the GNU GPLv3.
"""

try:
	import sqlite3
except ImportError:
	sqlite3 = None

	def connect(*args, **kwargs):
		raise RuntimeError("py-sqlite3 is not installed")

else:
	connect = sqlite3.connect

__all__ = [
	"Number",
	"Database"
]

__version__ = "0.8"

class Number(object):

	def __init__(self, number = int()):
		self.number = number

	def plus(self, number = 0x1):
		self.number += number
		return self.number

	def reduce(self, number = 0x1):
		self.number -= number
		return self.number

	__int__ = lambda self: self.number.__int__()

	_int = lambda self: self.__int__()

	__str__ = __repr__ = lambda self: self.number.__repr__()

	_str = lambda self: self.__str__()

	__float__ = lambda self: self.number.__float__()

	__oct__ = lambda self: self.number.__oct__()

	__eq__ = lambda self, number: self.number == number

	__ne__ = lambda self, number: self.number != number

	__gt__ = lambda self, number: self.number > number

	__lt__ = lambda self, number: self.number < number

	__ge__ = lambda self, number: self.number >= number

	__le__ = lambda self, number: self.number <= number

class LazyDescriptor(object): # not really lazy, but setter is not needed

	def __init__(self, function):
		self.fget = function

	__get__ = lambda self, instance, owner: self.fget(instance)

class Database(object):

	__connected = False

	def __init__(self, filename, lock = None, timeout = 8):
		self.filename = filename
		self.lock = lock
		self.timeout = timeout

	def __connect(self):

		assert not self.__connected, "already connected"

		self.db = connect(self.filename, timeout = self.timeout)
		self.cursor = self.db.cursor()
		self.__connected = True
		self.commit = self.db.commit
		self.execute = self.cursor.execute
		self.fetchone = self.cursor.fetchone
		self.fetchall = self.cursor.fetchall
		self.fetchmany = self.cursor.fetchmany

	@LazyDescriptor
	def execute(self):
		self.__connect()
		return self.execute

	__call__ = lambda self, *args: self.execute(*args)

	@LazyDescriptor
	def db(self):
		self.__connect()
		return self.db

	@LazyDescriptor
	def cursor(self):
		self.__connect()
		return self.cursor

	def close(self):

		assert self.__connected, "not connected"

		if self.cursor:
			self.cursor.close()
		if self.db.total_changes:
			self.commit()
		if self.db:
			self.db.close()

	def __enter__(self):
		if self.lock:
			self.lock.acquire()
		return self

	def __exit__(self, *args):
		if self.lock:
			self.lock.release()
		if self.__connected:
			self.close()

del LazyDescriptor

########NEW FILE########
__FILENAME__ = stext
# coding: utf-8
# (с) simpleApps, 25.06.12; 19:58:42
# License: GPLv3.

import os

def setVars(lang, path):
	globals()["locale"] = lang
	globals()["path"] = path

def rFile(name):
	with open(name, "r") as file:
		return file.read()

def _(what):
	name = "%s/locales/locale.%s" % (path, locale)
	what = what.replace("\n", "\\n")
	if locale != "en" and os.path.exists(name):
		data = open(name).readlines()
		for line in data:
			if line.startswith(what):
				what = line.split("=")[1].strip()
				break
	return what.replace("\\n", "\n")

########NEW FILE########
__FILENAME__ = utils
# coding: utf-8
# This file is a part of VK4XMPP transport
# © simpleApps, 2014.

import xmpp

def buildDataForm(form=None, type="submit", fields=[]):
	form = form or xmpp.DataForm(type)
	for key in fields:
		field = form.setField(key["var"], key.get("value"), key.get("type"))
		if key.get("payload"):
			field.setPayload(key["payload"])
		if key.get("label"):
			field.setLabel(key["label"])
	return form
########NEW FILE########
__FILENAME__ = vkapi
# coding: utf-8
# © simpleApps, 2013 — 2014.

import cookielib
import httplib
import json
import logging
import mimetools
import socket
import ssl
import time
import urllib
import urllib2
import webtools


logger = logging.getLogger("vk4xmpp")

def attemptTo(maxRetries, resultType, *errors):
	"""
	Tries to execute function ignoring specified errors specified number of
	times and returns specified result type on try limit.
	"""
	if not isinstance(resultType, type):
		resultType = lambda result = resultType: result
	if not errors:
		errors = Exception

	def decorator(func):

		def wrapper(*args, **kwargs):
			retries = 0
			while retries < maxRetries:
				try:
					data = func(*args, **kwargs)
				except errors as exc:
					retries += 1
					time.sleep(0.2)
				else:
					break
			else:
				if hasattr(exc, "errno") and exc.errno == 101:
					raise NetworkNotFound()
				data = resultType()
				logger.debug("Error %s occurred on executing %s" % (exc, func))
			return data

		wrapper.__name__ = func.__name__
		return wrapper

	return decorator


class AsyncHTTPRequest(httplib.HTTPConnection):

	def __init__(self, url, data=None, headers=(), timeout=30):
		host = urllib.splithost(urllib.splittype(url)[1])[0]
		httplib.HTTPConnection.__init__(self, host, timeout=timeout)
		self.url = url
		self.data = data
		self.headers = headers or {}

	def open(self):
		self.connect()
		self.request(("POST" if self.data else "GET"), self.url, self.data, self.headers)
		return self

	def read(self):
		with self as resp:
			return resp.read()

	def __enter__(self):
		return self.getresponse()

	def __exit__(self, *args):
		self.close()


class RequestProcessor(object):
	"""
	Processing base requests: POST (application/x-www-form-urlencoded and multipart/form-data) and GET.
	"""
	headers = {"User-agent": "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:21.0)"
					" Gecko/20130309 Firefox/21.0",
				"Accept-Language": "ru-RU, utf-8"}
	boundary = mimetools.choose_boundary()

	def __init__(self):
		self.cookieJar = cookielib.CookieJar()
		cookieProcessor = urllib2.HTTPCookieProcessor(self.cookieJar)
		self.open = urllib2.build_opener(cookieProcessor).open
		self.open.__func__.___defaults__ = (None, 30)

	def getCookie(self, name):
		for cookie in self.cookieJar:
			if cookie.name == name:
				return cookie.value

	def multipart(self, key, name, ctype, data):
		start = ["--" + self.boundary, "Content-Disposition: form-data; name=\"%s\"; filename=\"%s\"" % (key, name), \
									"Content-Type: %s" % ctype, "", ""] ## We already have content type so maybe we shouldn't detect it
		end = ["", "--" + self.boundary + "--", ""]
		start = "\n".join(start) #\r\n
		end = "\n".join(end) # \r\n
		data = start + data + end
		return data

	def request(self, url, data=None, headers=None, urlencode=True):
		headers = headers or self.headers
		if data and urlencode:
			headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
			data = urllib.urlencode(data)
		else:
			headers["Content-Type"] = "multipart/form-data; boundary=%s" % self.boundary
		request = urllib2.Request(url, data, headers)
		return request

	@attemptTo(5, tuple, urllib2.URLError, ssl.SSLError, socket.timeout, httplib.BadStatusLine)
	def post(self, url, data="", urlencode=True):
		resp = self.open(self.request(url, data, urlencode=urlencode))
		body = resp.read()
		return (body, resp)

	@attemptTo(5, tuple, urllib2.URLError, ssl.SSLError, socket.timeout, httplib.BadStatusLine)
	def get(self, url, query={}):
		if query:
			url += "?%s" % urllib.urlencode(query)
		resp = self.open(self.request(url))
		body = resp.read()
		return (body, resp)

	def getOpener(self, url, query={}):
		if query:
			url += "?%s" % urllib.urlencode(query)
		return AsyncHTTPRequest(url).open()




class APIBinding:
	def __init__(self, number=None, password=None, token=None, app_id=3789129,
	scope=69638):
		self.password = password
		self.number = number

		self.sid = None
		self.token = token
		self.captcha = {}
		self.last = []
		self.lastMethod = None

		self.app_id = app_id
		self.scope = scope

		self.RIP = RequestProcessor()
		self.attempts = 0

	def loginByPassword(self):
		url = "https://login.vk.com/"
		values = {"act": "login",
				"utf8": "1", # check if it needed
				"email": self.number,
				"pass": self.password}

		body, response = self.RIP.post(url, values)
		remixSID = self.RIP.getCookie("remixsid")

		if remixSID:
			self.sid = remixSID

		elif "sid=" in response.url:
			raise AuthError("Captcha!")
		else:
			raise AuthError("Invalid password")

		if "security_check" in response.url:
			# This code should be rewritten! Users from another countries can have problems because of it!
			hash = webtools.regexp(r"security_check.*?hash: '(.*?)'\};", body)[0]
			code = self.number[2:-2]
			if len(self.number) == 12:
				if not self.number.startswith("+"):
					code = self.number[3:-2]		# may be +375123456789

			elif len(self.number) == 13:			# so we need 1234567
				if self.number.startswith("+"):
					code = self.number[4:-2]

			values = {"act": "security_check",
					"al": "1",
					"al_page": "3",
					"code": code,
					"hash": hash,
					"to": ""}
			post = self.RIP.post("https://vk.com/login.php", values)
			body, response = post
			if response and not body.split("<!>")[4] == "4":
				raise AuthError("Incorrect number")

	def checkSid(self):
		if self.sid:
			url = "https://vk.com/feed2.php"
			get = self.RIP.get(url)
			if get:
				body, response = get
				if body and response:
					data = json.loads(body)
					if data["user"]["id"] != -1:
						return data

	def confirmThisApp(self):
		url = "https://oauth.vk.com/authorize/"
		values = {"display": "mobile",
				"scope": self.scope,
				"client_id": self.app_id,
				"response_type": "token",
				"redirect_uri": "https://oauth.vk.com/blank.html"}

		token = None
		body, response = self.RIP.get(url, values)
		if response:
			if "access_token" in response.url:
				token = response.url.split("=")[1].split("&")[0]
			else:
				postTarget = webtools.getTagArg("form method=\"post\"", "action", body, "form")
				if postTarget:
					body, response = self.RIP.post(postTarget)
					token = response.url.split("=")[1].split("&")[0]
				else:
					raise AuthError("Couldn't execute confirmThisApp()!")
		self.token = token


	def method(self, method, values=None, nodecode=False):
		values = values or {}
		url = "https://api.vk.com/method/%s" % method
		values["access_token"] = self.token
		values["v"] = "3.0"

		if self.captcha and self.captcha.has_key("key"):
			values["captcha_sid"] = self.captcha["sid"]
			values["captcha_key"] = self.captcha["key"]
			self.captcha = {}
		self.lastMethod = (method, values)
		self.last.append(time.time())
		if len(self.last) > 2:
			if (self.last.pop() - self.last.pop(0)) < 1.1:
				time.sleep(0.3)

		response = self.RIP.post(url, values)
		if response and not nodecode:
			body, response = response
			if body:
				try:
					body = json.loads(body)
				except ValueError:
					return {}
##	 Debug:
##			if method in ("users.get", "messages.get", "messages.send"):
##				print "method %s with values %s" % (method, str(values))
##				print "response for method %s: %s" % (method, str(body))
			if "response" in body:
				return body["response"]

			elif "error" in body:
				error = body["error"]
				eCode = error["error_code"]
	## TODO: Check code below
				if eCode == 5:     # invalid token
					self.attempts += 1
					if self.attempts < 3:
						retry = self.retry()
						if retry:
							self.attempts = 0
							return retry
					else:
						raise TokenError(error["error_msg"])
				if eCode == 6:     # too fast
					time.sleep(3)
					return self.method(method, values)
				elif eCode == 5:     # auth failed
					raise VkApiError("Logged out")
				elif eCode == 7:     # not allowed
					raise NotAllowed()
				elif eCode == 10:    # internal server error
					raise InternalServerError()
				elif eCode == 14:     # captcha
					if "captcha_sid" in error:
						self.captcha = {"sid": error["captcha_sid"], "img": error["captcha_img"]}
						raise CaptchaNeeded()
				elif eCode in (1, 9, 100): ## 1 is an unknown error / 100 is wrong method or parameters loss 
					return {"error": eCode}
				raise VkApiError(body["error"])

	def retry(self):
		if self.lastMethod:
			return self.method(*self.lastMethod)


class NetworkNotFound(Exception):  ## maybe network is unreachable or vk is down (same as 10 jan 2014)
	pass

class LongPollError(Exception):
	pass

class VkApiError(Exception):
	pass


class AuthError(VkApiError):
	pass


class InternalServerError(VkApiError):
	pass


class CaptchaNeeded(VkApiError):
	pass


class TokenError(VkApiError):
	pass


class NotAllowed(VkApiError):
	pass

########NEW FILE########
__FILENAME__ = webtools
# coding: utf-8

# BlackSmith-bot module.
# © simpleApps, 21.05.2012.

import re
import htmlentitydefs

edefs = dict()

for Name, Numb in htmlentitydefs.name2codepoint.iteritems():
	edefs[Name] = unichr(Numb)

del Name, Numb, htmlentitydefs

compile_ehtmls = re.compile("&(#?[xX]?(?:[0-9a-fA-F]+|\w{1,8}));")

def uHTML(data):
	if "&" in data:

		def e_sb(co):
			co = co.group(1)
			if co.startswith("#"):
				if chr(120) == co[1].lower():
					Char, c06 = co[2:], 16
				else:
					Char, c06 = co[1:], 10
				try:
					Numb = int(Char, c06)
					assert (-1 < Numb < 65535)
					Char = unichr(Numb)
				except Exception:
					Char = edefs.get(Char, "&%s;" % co)
			else:
				Char = edefs.get(co, "&%s;" % co)
			return Char

		data = compile_ehtmls.sub(e_sb, data)
	data = re.sub("</?br */?>", "\n", data)
	return data

def getTagArg(tag, argv, data, close_tag = 0):
	if not close_tag:
		close_tag = tag
	pattern = re.compile("<%(tag)s.? %(argv)s=[\"']?(.*?)[\"']?\">(.*?)</%(close_tag)s>" % vars(), flags = re.DOTALL | re.IGNORECASE)
	tagData = pattern.search(data)
	if tagData:
		tagData = tagData.group(1)
	return tagData or " "

########NEW FILE########
__FILENAME__ = writer
# coding: utf-8
# © simpleApps, 2010

import __main__
import os, sys, time, logging, traceback

logger = logging.getLogger("vk4xmpp")

fixme = lambda msg: Print("\n#! [%s] fixme: \"%s\"." % (time.strftime("%H:%M:%S"), msg))

lastErrorBody = None

def wFile(filename, data, mode = "w"):
	with open(filename, mode, 0) as file:
		file.write(data)

def rFile(filename):
	with open(filename, "r") as file:
		return file.read()

def crashLog(name, text = 0, fixMe = True):
	global lastErrorBody
	logger.error("writing crashlog %s" % name)
	if fixMe:
		fixme(name)
	try:
		File = "%s/%s.txt" % (__main__.crashDir, name)
		if not os.path.exists(__main__.crashDir):
			os.makedirs(__main__.crashDir)
		exception = wException(True)
		if exception not in ("None", lastErrorBody):
			Timestamp = time.strftime("| %d.%m.%Y (%H:%M:%S) |\n")
			wFile(File, Timestamp + exception + "\n", "a")
		lastErrorBody = exception
	except Exception:
		fixme("crashlog")
		wException()

def Print(text, line = True):
	try:
		if line:
			print text
		else:
			sys.stdout.write(text)
			sys.stdout.flush()
	except (IOError, OSError):
		pass

def wException(File = False):
	try:
		exception = traceback.format_exc().strip()
		if not File:
			Print(exception)
		return exception
	except (IOError, OSError):
		pass

def returnExc():
	exc = sys.exc_info()
	if all(exc):
		error = "\n%s: %s " % (exc[0].__name__, exc[1])
	else:
		error = "None"
	return error

########NEW FILE########
__FILENAME__ = auth
##   auth.py
##
##   Copyright (C) 2003-2005 Alexey "Snake" Nezhdanov
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

# $Id: auth.py, v1.42 2013/10/21 alkorgun Exp $

"""
Provides library with all Non-SASL and SASL authentication mechanisms.
Can be used both for client and transport authentication.
"""

import hashlib
from . import dispatcher

from base64 import encodestring, decodestring
from .plugin import PlugIn
from .protocol import *
from random import random as _random
from re import findall as re_findall

def HH(some):
	return hashlib.md5(some).hexdigest()

def H(some):
	return hashlib.md5(some).digest()

def C(some):
	return ":".join(some)

class NonSASL(PlugIn):
	"""
	Implements old Non-SASL (JEP-0078) authentication used in jabberd1.4 and transport authentication.
	"""
	def __init__(self, user, password, resource):
		"""
		Caches username, password and resource for auth.
		"""
		PlugIn.__init__(self)
		self.DBG_LINE = "gen_auth"
		self.user = user
		self.password = password
		self.resource = resource

	def plugin(self, owner):
		"""
		Determine the best auth method (digest/0k/plain) and use it for auth.
		Returns used method name on success. Used internally.
		"""
		if not self.resource:
			return self.authComponent(owner)
		self.DEBUG("Querying server about possible auth methods", "start")
		resp = owner.Dispatcher.SendAndWaitForResponse(Iq("get", NS_AUTH, payload=[Node("username", payload=[self.user])]))
		if not isResultNode(resp):
			self.DEBUG("No result node arrived! Aborting...", "error")
			return None
		iq = Iq(typ="set", node=resp)
		query = iq.getTag("query")
		query.setTagData("username", self.user)
		query.setTagData("resource", self.resource)
		if query.getTag("digest"):
			self.DEBUG("Performing digest authentication", "ok")
			hash = hashlib.sha1(owner.Dispatcher.Stream._document_attrs["id"] + self.password).hexdigest()
			query.setTagData("digest", hash)
			if query.getTag("password"):
				query.delChild("password")
			method = "digest"
		elif query.getTag("token"):
			token = query.getTagData("token")
			seq = query.getTagData("sequence")
			self.DEBUG("Performing zero-k authentication", "ok")
			hash = hashlib.sha1(hashlib.sha1(self.password).hexdigest() + token).hexdigest()
			for i in xrange(int(seq)):
				hash = hashlib.sha1(hash).hexdigest()
			query.setTagData("hash", hash)
			method = "0k"
		else:
			self.DEBUG("Sequre methods unsupported, performing plain text authentication", "warn")
			query.setTagData("password", self.password)
			method = "plain"
		resp = owner.Dispatcher.SendAndWaitForResponse(iq)
		if isResultNode(resp):
			self.DEBUG("Sucessfully authenticated with remove host.", "ok")
			owner.User = self.user
			owner.Resource = self.resource
			owner._registered_name = owner.User + "@" + owner.Server + "/" + owner.Resource
			return method
		self.DEBUG("Authentication failed!", "error")

	def authComponent(self, owner):
		"""
		Authenticate component. Send handshake stanza and wait for result. Returns "ok" on success.
		"""
		self.handshake = 0
		hash = hashlib.sha1(owner.Dispatcher.Stream._document_attrs["id"] + self.password).hexdigest()
		owner.send(Node(NS_COMPONENT_ACCEPT + " handshake", payload=[hash]))
		owner.RegisterHandler("handshake", self.handshakeHandler, xmlns=NS_COMPONENT_ACCEPT)
		while not self.handshake:
			self.DEBUG("waiting on handshake", "notify")
			owner.Process(1)
		owner._registered_name = self.user
		if self.handshake + 1:
			return "ok"

	def handshakeHandler(self, disp, stanza):
		"""
		Handler for registering in dispatcher for accepting transport authentication.
		"""
		if stanza.getName() == "handshake":
			self.handshake = 1
		else:
			self.handshake = -1

class SASL(PlugIn):
	"""
	Implements SASL authentication.
	"""
	def __init__(self, username, password):
		PlugIn.__init__(self)
		self.username = username
		self.password = password

	def plugin(self, owner):
		if "version" not in self._owner.Dispatcher.Stream._document_attrs:
			self.startsasl = "not-supported"
		elif self._owner.Dispatcher.Stream.features:
			try:
				self.FeaturesHandler(self._owner.Dispatcher, self._owner.Dispatcher.Stream.features)
			except NodeProcessed:
				pass
		else:
			self.startsasl = None

	def auth(self):
		"""
		Start authentication. Result can be obtained via "SASL.startsasl" attribute
		and will beeither "success" or "failure". Note that successfull
		auth will take at least two Dispatcher.Process() calls.
		"""
		if self.startsasl:
			pass
		elif self._owner.Dispatcher.Stream.features:
			try:
				self.FeaturesHandler(self._owner.Dispatcher, self._owner.Dispatcher.Stream.features)
			except NodeProcessed:
				pass
		else:
			self._owner.RegisterHandler("features", self.FeaturesHandler, xmlns=NS_STREAMS)

	def plugout(self):
		"""
		Remove SASL handlers from owner's dispatcher. Used internally.
		"""
		if hasattr(self._owner, "features"):
			self._owner.UnregisterHandler("features", self.FeaturesHandler, xmlns=NS_STREAMS)
		if hasattr(self._owner, "challenge"):
			self._owner.UnregisterHandler("challenge", self.SASLHandler, xmlns=NS_SASL)
		if hasattr(self._owner, "failure"):
			self._owner.UnregisterHandler("failure", self.SASLHandler, xmlns=NS_SASL)
		if hasattr(self._owner, "success"):
			self._owner.UnregisterHandler("success", self.SASLHandler, xmlns=NS_SASL)

	def FeaturesHandler(self, conn, feats):
		"""
		Used to determine if server supports SASL auth. Used internally.
		"""
		if not feats.getTag("mechanisms", namespace=NS_SASL):
			self.startsasl = "not-supported"
			self.DEBUG("SASL not supported by server", "error")
			return None
		mecs = []
		for mec in feats.getTag("mechanisms", namespace=NS_SASL).getTags("mechanism"):
			mecs.append(mec.getData())
		self._owner.RegisterHandler("challenge", self.SASLHandler, xmlns=NS_SASL)
		self._owner.RegisterHandler("failure", self.SASLHandler, xmlns=NS_SASL)
		self._owner.RegisterHandler("success", self.SASLHandler, xmlns=NS_SASL)
		if "ANONYMOUS" in mecs and self.username == None:
			node = Node("auth", attrs={"xmlns": NS_SASL, "mechanism": "ANONYMOUS"})
		elif "DIGEST-MD5" in mecs:
			node = Node("auth", attrs={"xmlns": NS_SASL, "mechanism": "DIGEST-MD5"})
		elif "PLAIN" in mecs:
			sasl_data = "%s\x00%s\x00%s" % ("@".join((self.username, self._owner.Server)), self.username, self.password)
			node = Node("auth", attrs={"xmlns": NS_SASL, "mechanism": "PLAIN"}, payload=[encodestring(sasl_data).replace("\r", "").replace("\n", "")])
		else:
			self.startsasl = "failure"
			self.DEBUG("I can only use DIGEST-MD5 and PLAIN mecanisms.", "error")
			return
		self.startsasl = "in-process"
		self._owner.send(node.__str__())
		raise NodeProcessed()

	def SASLHandler(self, conn, challenge):
		"""
		Perform next SASL auth step. Used internally.
		"""
		if challenge.getNamespace() != NS_SASL:
			return None
		if challenge.getName() == "failure":
			self.startsasl = "failure"
			try:
				reason = challenge.getChildren()[0]
			except Exception:
				reason = challenge
			self.DEBUG("Failed SASL authentification: %s" % reason, "error")
			raise NodeProcessed()
		elif challenge.getName() == "success":
			self.startsasl = "success"
			self.DEBUG("Successfully authenticated with remote server.", "ok")
			handlers = self._owner.Dispatcher.dumpHandlers()
			self._owner.Dispatcher.PlugOut()
			dispatcher.Dispatcher().PlugIn(self._owner)
			self._owner.Dispatcher.restoreHandlers(handlers)
			self._owner.User = self.username
			raise NodeProcessed()
		incoming_data = challenge.getData()
		chal = {}
		data = decodestring(incoming_data)
		self.DEBUG("Got challenge:" + data, "ok")
		for pair in re_findall('(\w+\s*=\s*(?:(?:"[^"]+")|(?:[^,]+)))', data):
			key, value = [x.strip() for x in pair.split("=", 1)]
			if value[:1] == '"' and value[-1:] == '"':
				value = value[1:-1]
			chal[key] = value
		if "qop" in chal and "auth" in [x.strip() for x in chal["qop"].split(",")]:
			resp = {}
			resp["username"] = self.username
			resp["realm"] = self._owner.Server
			resp["nonce"] = chal["nonce"]
			cnonce = ""
			for i in xrange(7):
				cnonce += hex(int(_random() * 65536 * 4096))[2:]
			resp["cnonce"] = cnonce
			resp["nc"] = ("00000001")
			resp["qop"] = "auth"
			resp["digest-uri"] = "xmpp/" + self._owner.Server
			A1 = C([H(C([resp["username"], resp["realm"], self.password])), resp["nonce"], resp["cnonce"]])
			A2 = C(["AUTHENTICATE", resp["digest-uri"]])
			response = HH(C([HH(A1), resp["nonce"], resp["nc"], resp["cnonce"], resp["qop"], HH(A2)]))
			resp["response"] = response
			resp["charset"] = "utf-8"
			sasl_data = ""
			for key in ("charset", "username", "realm", "nonce", "nc", "cnonce", "digest-uri", "response", "qop"):
				if key in ("nc", "qop", "response", "charset"):
					sasl_data += "%s=%s," % (key, resp[key])
				else:
					sasl_data += "%s=\"%s\"," % (key, resp[key])
			node = Node("response", attrs={"xmlns": NS_SASL}, payload=[encodestring(sasl_data[:-1]).replace("\r", "").replace("\n", "")])
			self._owner.send(node.__str__())
		elif "rspauth" in chal:
			self._owner.send(Node("response", attrs={"xmlns": NS_SASL}).__str__())
		else:
			self.startsasl = "failure"
			self.DEBUG("Failed SASL authentification: unknown challenge", "error")
		raise NodeProcessed()

class Bind(PlugIn):
	"""
	Bind some JID to the current connection to allow router know of our location.
	"""
	def __init__(self):
		PlugIn.__init__(self)
		self.DBG_LINE = "bind"
		self.bound = None

	def plugin(self, owner):
		"""
		Start resource binding, if allowed at this time. Used internally.
		"""
		if self._owner.Dispatcher.Stream.features:
			try:
				self.FeaturesHandler(self._owner.Dispatcher, self._owner.Dispatcher.Stream.features)
			except NodeProcessed:
				pass
		else:
			self._owner.RegisterHandler("features", self.FeaturesHandler, xmlns=NS_STREAMS)

	def plugout(self):
		"""
		Remove Bind handler from owner's dispatcher. Used internally.
		"""
		self._owner.UnregisterHandler("features", self.FeaturesHandler, xmlns=NS_STREAMS)

	def FeaturesHandler(self, conn, feats):
		"""
		Determine if server supports resource binding and set some internal attributes accordingly.
		"""
		if not feats.getTag("bind", namespace=NS_BIND):
			self.bound = "failure"
			self.DEBUG("Server does not requested binding.", "error")
			return None
		if feats.getTag("session", namespace=NS_SESSION):
			self.session = 1
		else:
			self.session = -1
		self.bound = []

	def Bind(self, resource=None):
		"""
		Perform binding. Use provided resource name or random (if not provided).
		"""
		while self.bound is None and self._owner.Process(1):
			pass
		if resource:
			resource = [Node("resource", payload=[resource])]
		else:
			resource = []
		resp = self._owner.SendAndWaitForResponse(Protocol("iq", typ="set", payload=[Node("bind", attrs={"xmlns": NS_BIND}, payload=resource)]))
		if isResultNode(resp):
			self.bound.append(resp.getTag("bind").getTagData("jid"))
			self.DEBUG("Successfully bound %s." % self.bound[-1], "ok")
			jid = JID(resp.getTag("bind").getTagData("jid"))
			self._owner.User = jid.getNode()
			self._owner.Resource = jid.getResource()
			resp = self._owner.SendAndWaitForResponse(Protocol("iq", typ="set", payload=[Node("session", attrs={"xmlns": NS_SESSION})]))
			if isResultNode(resp):
				self.DEBUG("Successfully opened session.", "ok")
				self.session = 1
				return "ok"
			else:
				self.DEBUG("Session open failed.", "error")
				self.session = 0
		elif resp:
			self.DEBUG("Binding failed: %s." % resp.getTag("error"), "error")
		else:
			self.DEBUG("Binding failed: timeout expired.", "error")
			return ""

class ComponentBind(PlugIn):
	"""
	ComponentBind some JID to the current connection to allow router know of our location.
	"""
	def __init__(self, sasl):
		PlugIn.__init__(self)
		self.DBG_LINE = "bind"
		self.bound = None
		self.needsUnregister = None
		self.sasl = sasl

	def plugin(self, owner):
		"""
		Start resource binding, if allowed at this time. Used internally.
		"""
		if not self.sasl:
			self.bound = []
			return None
		if self._owner.Dispatcher.Stream.features:
			try:
				self.FeaturesHandler(self._owner.Dispatcher, self._owner.Dispatcher.Stream.features)
			except NodeProcessed:
				pass
		else:
			self._owner.RegisterHandler("features", self.FeaturesHandler, xmlns=NS_STREAMS)
			self.needsUnregister = 1

	def plugout(self):
		"""
		Remove ComponentBind handler from owner's dispatcher. Used internally.
		"""
		if self.needsUnregister:
			self._owner.UnregisterHandler("features", self.FeaturesHandler, xmlns=NS_STREAMS)

	def FeaturesHandler(self, conn, feats):
		"""
		Determine if server supports resource binding and set some internal attributes accordingly.
		"""
		if not feats.getTag("bind", namespace=NS_BIND):
			self.bound = "failure"
			self.DEBUG("Server does not requested binding.", "error")
			return None
		if feats.getTag("session", namespace=NS_SESSION):
			self.session = 1
		else:
			self.session = -1
		self.bound = []

	def Bind(self, domain=None):
		"""
		Perform binding. Use provided domain name (if not provided).
		"""
		while self.bound is None and self._owner.Process(1):
			pass
		if self.sasl:
			xmlns = NS_COMPONENT_1
		else:
			xmlns = None
		self.bindresponse = None
		ttl = dispatcher.DefaultTimeout
		self._owner.RegisterHandler("bind", self.BindHandler, xmlns=xmlns)
		self._owner.send(Protocol("bind", attrs={"name": domain}, xmlns=NS_COMPONENT_1))
		while self.bindresponse is None and self._owner.Process(1) and ttl > 0:
			ttl -= 1
		self._owner.UnregisterHandler("bind", self.BindHandler, xmlns=xmlns)
		resp = self.bindresponse
		if resp and resp.getAttr("error"):
			self.DEBUG("Binding failed: %s." % resp.getAttr("error"), "error")
		elif resp:
			self.DEBUG("Successfully bound.", "ok")
			return "ok"
		else:
			self.DEBUG("Binding failed: timeout expired.", "error")
			return ""

	def BindHandler(self, conn, bind):
		self.bindresponse = bind
		pass

########NEW FILE########
__FILENAME__ = browser
##   browser.py
##
##   Copyright (C) 2004 Alexey "Snake" Nezhdanov
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

# $Id: browser.py, v1.13 2013/11/03 alkorgun Exp $

"""
Browser module provides DISCO server framework for your application.
This functionality can be used for very different purposes - from publishing
software version and supported features to building of "jabber site" that users
can navigate with their disco browsers and interact with active content.

Such functionality is achieved via registering "DISCO handlers" that are
automatically called when user requests some node of your disco tree.
"""

from .dispatcher import *
from .plugin import PlugIn

class Browser(PlugIn):
	"""
	WARNING! This class is for components only. It will not work in client mode!

	Standart xmpppy class that is ancestor of PlugIn and can be attached
	to your application.
	All processing will be performed in the handlers registered in the browser
	instance. You can register any number of handlers ensuring that for each
	node/jid combination only one (or none) handler registered.
	You can register static information or the fully-blown function that will
	calculate the answer dynamically.
	Example of static info (see JEP-0030, examples 13-14):
	# cl - your xmpppy connection instance.
	b = xmpp.browser.Browser()
	b.PlugIn(cl)
	items = []
	item = {}
	item["jid"] = "catalog.shakespeare.lit"
	item["node"] = "books"
	item["name"] = "Books by and about Shakespeare"
	items.append(item)
	item = {}
	item["jid"] = "catalog.shakespeare.lit"
	item["node"] = "clothing"
	item["name"] = "Wear your literary taste with pride"
	items.append(item)
	item = {}
	item["jid"] = "catalog.shakespeare.lit"
	item["node"] = "music"
	item["name"] = "Music from the time of Shakespeare"
	items.append(item)
	info = {"ids": [], "features": []}
	b.setDiscoHandler({"items": items, "info": info})

	items should be a list of item elements.
	every item element can have any of these four keys: "jid", "node", "name", "action"
	info should be a dicionary and must have keys "ids" and "features".
	Both of them should be lists:
		ids is a list of dictionaries and features is a list of text strings.
	Example (see JEP-0030, examples 1-2)
	# cl - your xmpppy connection instance.
	b = xmpp.browser.Browser()
	b.PlugIn(cl)
	items = []
	ids = []
	ids.append({"category": "conference", "type": "text", "name": "Play-Specific Chatrooms"})
	ids.append({"category": "directory", "type": "chatroom", "name": "Play-Specific Chatrooms"})
	features = [
		NS_DISCO_INFO,
		NS_DISCO_ITEMS,
		NS_MUC,
		NS_REGISTER,
		NS_SEARCH,
		NS_TIME,
		NS_VERSION
	]
	info = {"ids": ids, "features": features}
	# info["xdata"] = xmpp.protocol.DataForm() # JEP-0128
	b.setDiscoHandler({"items": [], "info": info})
	"""
	def __init__(self):
		"""
		Initialises internal variables. Used internally.
		"""
		PlugIn.__init__(self)
		DBG_LINE = "browser"
		self._exported_methods = []
		self._handlers = {"": {}}

	def plugin(self, owner):
		"""
		Registers it's own iq handlers in your application dispatcher instance.
		Used internally.
		"""
		owner.RegisterHandler("iq", self._DiscoveryHandler, typ="get", ns=NS_DISCO_INFO)
		owner.RegisterHandler("iq", self._DiscoveryHandler, typ="get", ns=NS_DISCO_ITEMS)

	def plugout(self):
		"""
		Unregisters browser's iq handlers from your application dispatcher instance.
		Used internally.
		"""
		self._owner.UnregisterHandler("iq", self._DiscoveryHandler, typ="get", ns=NS_DISCO_INFO)
		self._owner.UnregisterHandler("iq", self._DiscoveryHandler, typ="get", ns=NS_DISCO_ITEMS)

	def _traversePath(self, node, jid, set=0):
		"""
		Returns dictionary and key or None,None
		None - root node (w/o "node" attribute)
		/a/b/c - node
		/a/b/  - branch
		Set returns "" or None as the key
		get returns "" or None as the key or None as the dict.
		Used internally.
		"""
		if jid in self._handlers:
			cur = self._handlers[jid]
		elif set:
			self._handlers[jid] = {}
			cur = self._handlers[jid]
		else:
			cur = self._handlers[""]
		if node is None:
			node = [None]
		else:
			node = node.replace("/", " /").split("/")
		for i in node:
			if i != "" and i in cur:
				cur = cur[i]
			elif set and i != "":
				cur[i] = {dict: cur, str: i}
				cur = cur[i]
			elif set or "" in cur:
				return cur, ""
			else:
				return None, None
		if 1 in cur or set:
			return cur, 1
		raise Exception("Corrupted data")

	def setDiscoHandler(self, handler, node="", jid=""):
		"""
		This is the main method that you will use in this class.
		It is used to register supplied DISCO handler (or dictionary with static info)
		as handler of some disco tree branch.
		If you do not specify the node this handler will be used for all queried nodes.
		If you do not specify the jid this handler will be used for all queried JIDs.

		Usage:
		cl.Browser.setDiscoHandler(someDict, node, jid)
		or
		cl.Browser.setDiscoHandler(someDISCOHandler, node, jid)
		where

		someDict = {
			"items":[
				{"jid": "jid2", "action": "action2", "node":"node2", "name": "name2"},
				{"jid": "jid4", "node": "node4"}
			],
			"info" :{
				"ids":[
					{"category":" category1", "type": "type1", "name": "name1"},
					{"category":" category3", "type": "type3", "name": "name3"},
				],
				"features": ["feature1", "feature2", "feature3", "feature4"],
				"xdata": DataForm
			}
		}

		and/or

		def someDISCOHandler(session,request,TYR):
			# if TYR == "items":  # returns items list of the same format as shown above
			# elif TYR == "info": # returns info dictionary of the same format as shown above
			# else: # this case is impossible for now.
		"""
		self.DEBUG("Registering handler %s for \"%s\" node->%s" % (handler, jid, node), "info")
		node, key = self._traversePath(node, jid, 1)
		node[key] = handler

	def getDiscoHandler(self, node="", jid=""):
		"""
		Returns the previously registered DISCO handler
		that is resonsible for this node/jid combination.
		Used internally.
		"""
		node, key = self._traversePath(node, jid)
		if node:
			return node[key]

	def delDiscoHandler(self, node="", jid=""):
		"""
		Unregisters DISCO handler that is resonsible for this
		node/jid combination. When handler is unregistered the branch
		is handled in the same way that it's parent branch from this moment.
		"""
		node, key = self._traversePath(node, jid)
		if node:
			handler = node[key]
			del node[dict][node[str]]
			return handler

	def _DiscoveryHandler(self, conn, request):
		"""
		Servers DISCO iq request from the remote client.
		Automatically determines the best handler to use and calls it
		(to handle the request. Used internally.
		"""
		node = request.getQuerynode()
		if node:
			nodestr = node
		else:
			nodestr = "None"
		handler = self.getDiscoHandler(node, request.getTo())
		if not handler:
			self.DEBUG("No Handler for request with jid->%s node->%s ns->%s" % (request.getTo().__str__().encode("utf8"), nodestr.encode("utf8"), request.getQueryNS().encode("utf8")), "error")
			conn.send(Error(request, ERR_ITEM_NOT_FOUND))
			raise NodeProcessed()
		self.DEBUG("Handling request with jid->%s node->%s ns->%s" % (request.getTo().__str__().encode("utf8"), nodestr.encode("utf8"), request.getQueryNS().encode("utf8")), "ok")
		rep = request.buildReply("result")
		if node:
			rep.setQuerynode(node)
		q = rep.getTag("query")
		if request.getQueryNS() == NS_DISCO_ITEMS:
			# handler must return list: [{jid, action, node, name}]
			if isinstance(handler, dict):
				lst = handler["items"]
			else:
				lst = handler(conn, request, "items")
			if lst == None:
				conn.send(Error(request, ERR_ITEM_NOT_FOUND))
				raise NodeProcessed()
			for item in lst:
				q.addChild("item", item)
		elif request.getQueryNS() == NS_DISCO_INFO:
			if isinstance(handler, dict):
				dt = handler["info"]
			else:
				dt = handler(conn, request, "info")
			if dt == None:
				conn.send(Error(request, ERR_ITEM_NOT_FOUND))
				raise NodeProcessed()
			# handler must return dictionary:
			# {"ids": [{}, {}, {}, {}], "features": [fe, at, ur, es], "xdata": DataForm}
			for id in dt["ids"]:
				q.addChild("identity", id)
			for feature in dt["features"]:
				q.addChild("feature", {"var": feature})
			if "xdata" in dt:
				q.addChild(node=dt["xdata"])
		conn.send(rep)
		raise NodeProcessed()

########NEW FILE########
__FILENAME__ = client
##   client.py
##
##   Copyright (C) 2003-2005 Alexey "Snake" Nezhdanov
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

# $Id: client.py, v1.62 2013/10/21 alkorgun Exp $

"""
Provides PlugIn class functionality to develop extentions for xmpppy.
Also provides Client and Component classes implementations as the
examples of xmpppy structures usage.
These classes can be used for simple applications "AS IS" though.
"""

from . import debug
from . import transports
from . import dispatcher
from . import auth
from . import roster

from .plugin import PlugIn

Debug = debug
Debug.DEBUGGING_IS_ON = 1

Debug.Debug.colors["socket"] = debug.color_dark_gray
Debug.Debug.colors["CONNECTproxy"] = debug.color_dark_gray
Debug.Debug.colors["nodebuilder"] = debug.color_brown
Debug.Debug.colors["client"] = debug.color_cyan
Debug.Debug.colors["component"] = debug.color_cyan
Debug.Debug.colors["dispatcher"] = debug.color_green
Debug.Debug.colors["browser"] = debug.color_blue
Debug.Debug.colors["auth"] = debug.color_yellow
Debug.Debug.colors["roster"] = debug.color_magenta
Debug.Debug.colors["ibb"] = debug.color_yellow
Debug.Debug.colors["down"] = debug.color_brown
Debug.Debug.colors["up"] = debug.color_brown
Debug.Debug.colors["data"] = debug.color_brown
Debug.Debug.colors["ok"] = debug.color_green
Debug.Debug.colors["warn"] = debug.color_yellow
Debug.Debug.colors["error"] = debug.color_red
Debug.Debug.colors["start"] = debug.color_dark_gray
Debug.Debug.colors["stop"] = debug.color_dark_gray
Debug.Debug.colors["sent"] = debug.color_yellow
Debug.Debug.colors["got"] = debug.color_bright_cyan

DBG_CLIENT = "client"
DBG_COMPONENT = "component"


class CommonClient:
	"""
	Base for Client and Component classes.
	"""
	def __init__(self, server, port=5222, debug=["always", "nodebuilder"]):
		"""
		Caches server name and (optionally) port to connect to. "debug" parameter specifies
		the debug IDs that will go into debug output. You can either specifiy an "include"
		or "exclude" list. The latter is done via adding "always" pseudo-ID to the list.
		Full list: ["nodebuilder", "dispatcher", "gen_auth", "SASL_auth", "bind", "socket",
		"CONNECTproxy", "TLS", "roster", "browser", "ibb"].
		"""
		if isinstance(self, Client):
			self.Namespace, self.DBG = "jabber:client", DBG_CLIENT
		elif isinstance(self, Component):
			self.Namespace, self.DBG = dispatcher.NS_COMPONENT_ACCEPT, DBG_COMPONENT
		self.defaultNamespace = self.Namespace
		self.disconnect_handlers = []
		self.Server = server
		self.Port = port
		if debug and not isinstance(debug, list):
			debug = ["always", "nodebuilder"]
		self._DEBUG = Debug.Debug(debug)
		self.DEBUG = self._DEBUG.Show
		self.debug_flags = self._DEBUG.debug_flags
		self.debug_flags.append(self.DBG)
		self._owner = self
		self._registered_name = None
		self.RegisterDisconnectHandler(self.DisconnectHandler)
		self.connected = ""
		self._route = 0

	def RegisterDisconnectHandler(self, handler):
		"""
		Register handler that will be called on disconnect.
		"""
		self.disconnect_handlers.append(handler)

	def UnregisterDisconnectHandler(self, handler):
		"""
		Unregister handler that is called on disconnect.
		"""
		self.disconnect_handlers.remove(handler)

	def disconnected(self):
		"""
		Called on disconnection. Calls disconnect handlers and cleans things up.
		"""
		self.connected = ""
		self.DEBUG(self.DBG, "Disconnect detected", "stop")
		self.disconnect_handlers.reverse()
		for dhnd in self.disconnect_handlers:
			dhnd()
		self.disconnect_handlers.reverse()
		if hasattr(self, "TLS"):
			self.TLS.PlugOut()

	def DisconnectHandler(self):
		"""
		Default disconnect handler. Just raises an IOError.
		If you choosed to use this class in your production client,
		override this method or at least unregister it.
		"""
		raise IOError("Disconnected!")

	def event(self, eventName, args={}):
		"""
		Default event handler. To be overriden.
		"""
		print("Event: %s-%s" % (eventName, args))

	def isConnected(self):
		"""
		Returns connection state. F.e.: None / "tls" / "tcp+non_sasl" .
		"""
		return self.connected

	def reconnectAndReauth(self, handlerssave=None):
		"""
		Example of reconnection method. In fact, it can be used to batch connection and auth as well.
		"""
		Dispatcher_ = False
		if not handlerssave:
			Dispatcher_, handlerssave = True, self.Dispatcher.dumpHandlers()
		if hasattr(self, "ComponentBind"):
			self.ComponentBind.PlugOut()
		if hasattr(self, "Bind"):
			self.Bind.PlugOut()
		self._route = 0
		if hasattr(self, "NonSASL"):
			self.NonSASL.PlugOut()
		if hasattr(self, "SASL"):
			self.SASL.PlugOut()
		if hasattr(self, "TLS"):
			self.TLS.PlugOut()
		if Dispatcher_:
			self.Dispatcher.PlugOut()
		if hasattr(self, "HTTPPROXYsocket"):
			self.HTTPPROXYsocket.PlugOut()
		if hasattr(self, "TCPsocket"):
			self.TCPsocket.PlugOut()
		if not self.connect(server=self._Server, proxy=self._Proxy):
			return None
		if not self.auth(self._User, self._Password, self._Resource):
			return None
		self.Dispatcher.restoreHandlers(handlerssave)
		return self.connected

	def connect(self, server=None, proxy=None, ssl=None, use_srv=False):
		"""
		Make a tcp/ip connection, protect it with tls/ssl if possible and start XMPP stream.
		Returns None or "tcp" or "tls", depending on the result.
		"""
		if not server:
			server = (self.Server, self.Port)
		if proxy:
			sock = transports.HTTPPROXYsocket(proxy, server, use_srv)
		else:
			sock = transports.TCPsocket(server, use_srv)
		connected = sock.PlugIn(self)
		if not connected:
			sock.PlugOut()
			return None
		self._Server, self._Proxy = server, proxy
		self.connected = "tcp"
		if (ssl is None and self.Connection.getPort() in (5223, 443)) or ssl:
			try: # FIXME. This should be done in transports.py
				transports.TLS().PlugIn(self, now=1)
				self.connected = "ssl"
			except transports.socket.sslerror:
				return None
		dispatcher.Dispatcher().PlugIn(self)
		while self.Dispatcher.Stream._document_attrs is None:
			if not self.Process(1):
				return None
		if "version" in self.Dispatcher.Stream._document_attrs and self.Dispatcher.Stream._document_attrs["version"] == "1.0":
			while not self.Dispatcher.Stream.features and self.Process(1):
				pass # If we get version 1.0 stream the features tag MUST BE presented
		return self.connected

class Client(CommonClient):
	"""
	Example client class, based on CommonClient.
	"""
	def connect(self, server=None, proxy=None, secure=None, use_srv=True):
		"""
		Connect to jabber server. If you want to specify different ip/port to connect to you can
		pass it as tuple as first parameter. If there is HTTP proxy between you and server
		specify it's address and credentials (if needed) in the second argument.
		If you want ssl/tls support to be discovered and enable automatically - leave third argument as None. (ssl will be autodetected only if port is 5223 or 443)
		If you want to force SSL start (i.e. if port 5223 or 443 is remapped to some non-standard port) then set it to 1.
		If you want to disable tls/ssl support completely, set it to 0.
		Example: connect(("192.168.5.5", 5222), {"host": "proxy.my.net", "port": 8080, "user": "me", "password": "secret"})
		Returns "" or "tcp" or "tls", depending on the result.
		"""
		if not CommonClient.connect(self, server, proxy, secure, use_srv) or secure != None and not secure:
			return self.connected
		transports.TLS().PlugIn(self)
		if not hasattr(self, "Dispatcher"):
			return None
		if "version" not in self.Dispatcher.Stream._document_attrs or not self.Dispatcher.Stream._document_attrs["version"] == "1.0":
			return self.connected
		while not self.Dispatcher.Stream.features and self.Process(1):
			pass # If we get version 1.0 stream the features tag MUST BE presented
		if not self.Dispatcher.Stream.features.getTag("starttls"):
			return self.connected # TLS not supported by server
		while not self.TLS.starttls and self.Process(1):
			pass
		if not hasattr(self, "TLS") or self.TLS.starttls != "success":
			self.event("tls_failed")
			return self.connected
		self.connected = "tls"
		return self.connected

	def auth(self, user, password, resource="", sasl=1):
		"""
		Authenticate connnection and bind resource. If resource is not provided
		random one or library name used.
		"""
		self._User, self._Password, self._Resource = user, password, resource
		while not self.Dispatcher.Stream._document_attrs and self.Process(1):
			pass
		if "version" in self.Dispatcher.Stream._document_attrs and self.Dispatcher.Stream._document_attrs["version"] == "1.0":
			while not self.Dispatcher.Stream.features and self.Process(1):
				pass # If we get version 1.0 stream the features tag MUST BE presented
		if sasl:
			auth.SASL(user, password).PlugIn(self)
		if not sasl or self.SASL.startsasl == "not-supported":
			if not resource:
				resource = "xmpppy"
			if auth.NonSASL(user, password, resource).PlugIn(self):
				self.connected += "+old_auth"
				return "old_auth"
			return None
		self.SASL.auth()
		while self.SASL.startsasl == "in-process" and self.Process(1):
			pass
		if self.SASL.startsasl == "success":
			auth.Bind().PlugIn(self)
			while self.Bind.bound is None and self.Process(1):
				pass
			if self.Bind.Bind(resource):
				self.connected += "+sasl"
				return "sasl"
		elif hasattr(self, "SASL"):
			self.SASL.PlugOut()

	def getRoster(self):
		"""
		Return the Roster instance, previously plugging it in and
		requesting roster from server if needed.
		"""
		if not hasattr(self, "Roster"):
			roster.Roster().PlugIn(self)
		return self.Roster.getRoster()

	def sendInitPresence(self, requestRoster=1):
		"""
		Send roster request and initial <presence/>.
		You can disable the first by setting requestRoster argument to 0.
		"""
		self.sendPresence(requestRoster=requestRoster)

	def sendPresence(self, jid=None, typ=None, requestRoster=0):
		"""
		Send some specific presence state.
		Can also request roster from server if according agrument is set.
		"""
		if requestRoster:
			roster.Roster().PlugIn(self)
		self.send(dispatcher.Presence(to=jid, typ=typ))

class Component(CommonClient):
	"""
	Component class. The only difference from CommonClient is ability to perform component authentication.
	"""
	def __init__(self, transport, port=5347, typ=None, debug=["always", "nodebuilder"], domains=None, sasl=0, bind=0, route=0, xcp=0):
		"""
		Init function for Components.
		As components use a different auth mechanism which includes the namespace of the component.
		Jabberd1.4 and Ejabberd use the default namespace then for all client messages.
		Jabberd2 uses jabber:client.
		"transport" argument is a transport name that you are going to serve (f.e. "irc.localhost").
		"port" can be specified if "transport" resolves to correct IP. If it is not then you'll have to specify IP
		and port while calling "connect()".
		If you are going to serve several different domains with single Component instance - you must list them ALL
		in the "domains" argument.
		For jabberd2 servers you should set typ="jabberd2" argument.
		"""
		CommonClient.__init__(self, transport, port=port, debug=debug)
		self.typ = typ
		self.sasl = sasl
		self.bind = bind
		self.route = route
		self.xcp = xcp
		if domains:
			self.domains = domains
		else:
			self.domains = [transport]

	def connect(self, server=None, proxy=None):
		"""
		This will connect to the server, and if the features tag is found then set
		the namespace to be jabber:client as that is required for jabberd2.
		"server" and "proxy" arguments have the same meaning as in xmpp.Client.connect().
		"""
		if self.sasl:
			self.Namespace = auth.NS_COMPONENT_1
			self.Server = server[0]
		CommonClient.connect(self, server=server, proxy=proxy)
		if self.connected and (self.typ == "jabberd2" or not self.typ and self.Dispatcher.Stream.features != None) and (not self.xcp):
			self.defaultNamespace = auth.NS_CLIENT
			self.Dispatcher.RegisterNamespace(self.defaultNamespace)
			self.Dispatcher.RegisterProtocol("iq", dispatcher.Iq)
			self.Dispatcher.RegisterProtocol("message", dispatcher.Message)
			self.Dispatcher.RegisterProtocol("presence", dispatcher.Presence)
		return self.connected

	def dobind(self, sasl):
		# This has to be done before binding, because we can receive a route stanza before binding finishes
		self._route = self.route
		if self.bind:
			for domain in self.domains:
				auth.ComponentBind(sasl).PlugIn(self)
				while self.ComponentBind.bound is None:
					self.Process(1)
				if (not self.ComponentBind.Bind(domain)):
					self.ComponentBind.PlugOut()
					return None
				self.ComponentBind.PlugOut()

	def auth(self, name, password, dup=None):
		"""
		Authenticate component "name" with password "password".
		"""
		self._User, self._Password, self._Resource = name, password, ""
		try:
			if self.sasl:
				auth.SASL(name, password).PlugIn(self)
			if not self.sasl or self.SASL.startsasl == "not-supported":
				if auth.NonSASL(name, password, "").PlugIn(self):
					self.dobind(sasl=False)
					self.connected += "+old_auth"
					return "old_auth"
				return None
			self.SASL.auth()
			while self.SASL.startsasl == "in-process" and self.Process(1):
				pass
			if self.SASL.startsasl == "success":
				self.dobind(sasl=True)
				self.connected += "+sasl"
				return "sasl"
			else:
				raise auth.NotAuthorized(self.SASL.startsasl)
		except Exception:
			self.DEBUG(self.DBG, "Failed to authenticate %s" % name, "error")

########NEW FILE########
__FILENAME__ = commands
## Ad-Hoc Command manager

## Mike Albon (c) 5th January 2005

##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

# $Id: commands.py, v1.18 2013/11/05 alkorgun Exp $

"""
This module is a ad-hoc command processor for xmpppy. It uses the plug-in mechanism like most of the core library.
It depends on a DISCO browser manager.

There are 3 classes here, a command processor Commands like the Browser,
and a command template plugin Command, and an example command.

To use this module:

	Instansiate the module with the parent transport and disco browser manager as parameters.
	"Plug in" commands using the command template.
	The command feature must be added to existing disco replies where neccessary.

What it supplies:

	Automatic command registration with the disco browser manager.
	Automatic listing of commands in the public command list.
	A means of handling requests, by redirection though the command manager.
"""

from .plugin import PlugIn
from .protocol import *

class Commands(PlugIn):
	"""
	Commands is an ancestor of PlugIn and can be attached to any session.

	The commands class provides a lookup and browse mechnism.
	It follows the same priciple of the Browser class, for Service Discovery to provide the list of commands,
	it adds the "list" disco type to your existing disco handler function.

	How it works:
		The commands are added into the existing Browser on the correct nodes.
		When the command list is built the supplied discovery handler function needs to have a "list" option in type.
		This then gets enumerated, all results returned as None are ignored.
		The command executed is then called using it's Execute method.
		All session management is handled by the command itself.
	"""
	def __init__(self, browser):
		"""
		Initialises class and sets up local variables.
		"""
		PlugIn.__init__(self)
		DBG_LINE = "commands"
		self._exported_methods = []
		self._handlers = {"": {}}
		self._browser = browser

	def plugin(self, owner):
		"""
		Makes handlers within the session.
		"""
		# Plug into the session and the disco manager
		# We only need get and set, results are not needed by a service provider, only a service user.
		owner.RegisterHandler("iq", self._CommandHandler, typ="set", ns=NS_COMMANDS)
		owner.RegisterHandler("iq", self._CommandHandler, typ="get", ns=NS_COMMANDS)
		self._browser.setDiscoHandler(self._DiscoHandler, node=NS_COMMANDS, jid="")

	def plugout(self):
		"""
		Removes handlers from the session.
		"""
		# unPlug from the session and the disco manager
		self._owner.UnregisterHandler("iq", self._CommandHandler, ns=NS_COMMANDS)
		for jid in self._handlers:
			self._browser.delDiscoHandler(self._DiscoHandler, node=NS_COMMANDS)

	def _CommandHandler(self, conn, request):
		"""
		The internal method to process the routing of command execution requests.
		"""
		# This is the command handler itself.
		# We must:
		#   Pass on command execution to command handler
		#   (Do we need to keep session details here, or can that be done in the command?)
		jid = str(request.getTo())
		try:
			node = request.getTagAttr("command", "node")
		except Exception:
			conn.send(Error(request, ERR_BAD_REQUEST))
			raise NodeProcessed()
		if jid in self._handlers:
			if node in self._handlers[jid]:
				self._handlers[jid][node]["execute"](conn, request)
			else:
				conn.send(Error(request, ERR_ITEM_NOT_FOUND))
				raise NodeProcessed()
		elif node in self._handlers[""]:
			self._handlers[""][node]["execute"](conn, request)
		else:
			conn.send(Error(request, ERR_ITEM_NOT_FOUND))
			raise NodeProcessed()

	def _DiscoHandler(self, conn, request, typ):
		"""
		The internal method to process service discovery requests.
		"""
		# This is the disco manager handler.
		if typ == "items":
			# We must:
			# 	Generate a list of commands and return the list
			# 	* This handler does not handle individual commands disco requests.
			# Pseudo:
			#   Enumerate the "item" disco of each command for the specified jid
			#   Build responce and send
			#   To make this code easy to write we add an "list" disco type, it returns a tuple or "none" if not advertised
			list = []
			items = []
			jid = str(request.getTo())
			# Get specific jid based results
			if jid in self._handlers:
				for each in self._handlers[jid].keys():
					items.append((jid, each))
			else:
				# Get generic results
				for each in self._handlers[""].keys():
					items.append(("", each))
			if items:
				for each in items:
					i = self._handlers[each[0]][each[1]]["disco"](conn, request, "list")
					if i != None:
						list.append(Node(tag="item", attrs={"jid": i[0], "node": i[1], "name": i[2]}))
				iq = request.buildReply("result")
				if request.getQuerynode():
					iq.setQuerynode(request.getQuerynode())
				iq.setQueryPayload(list)
				conn.send(iq)
			else:
				conn.send(Error(request, ERR_ITEM_NOT_FOUND))
			raise NodeProcessed()
		if typ == "info":
			return {
				"ids": [{"category": "automation", "type": "command-list"}],
				"features": []
			}

	def addCommand(self, name, cmddisco, cmdexecute, jid=""):
		"""
		The method to call if adding a new command to the session,
		the requred parameters of cmddisco and cmdexecute
		are the methods to enable that command to be executed.
		"""
		# This command takes a command object and the name of the command for registration
		# We must:
		#   Add item into disco
		#   Add item into command list
		if jid not in self._handlers:
			self._handlers[jid] = {}
			self._browser.setDiscoHandler(self._DiscoHandler, node=NS_COMMANDS, jid=jid)
		if name in self._handlers[jid]:
			raise NameError("Command Exists")
		self._handlers[jid][name] = {"disco": cmddisco, "execute": cmdexecute}
		# Need to add disco stuff here
		self._browser.setDiscoHandler(cmddisco, node=name, jid=jid)

	def delCommand(self, name, jid=""):
		"""
		Removed command from the session.
		"""
		# This command takes a command object and the name used for registration
		# We must:
		#   Remove item from disco
		#   Remove item from command list
		if jid not in self._handlers:
			raise NameError("Jid not found")
		if name not in self._handlers[jid]:
			raise NameError("Command not found")
		# Do disco removal here
		command = self.getCommand(name, jid)["disco"]
		del self._handlers[jid][name]
		self._browser.delDiscoHandler(command, node=name, jid=jid)

	def getCommand(self, name, jid=""):
		"""
		Returns the command tuple.
		"""
		# This gets the command object with name
		# We must:
		#   Return item that matches this name
		if jid not in self._handlers:
			raise NameError("Jid not found")
		if name not in self._handlers[jid]:
			raise NameError("Command not found")
		return self._handlers[jid][name]

class Command_Handler_Prototype(PlugIn):
	"""
	This is a prototype command handler, as each command uses a disco method
	and execute method you can implement it any way you like, however this is
	my first attempt at making a generic handler that you can hang process
	stages on too. There is an example command below.

	The parameters are as follows:
	name: the name of the command within the jabber environment
	description: the natural language description
	discofeatures: the features supported by the command
	initial: the initial command in the from of {"execute": commandname}

	All stages set the "actions" dictionary for each session to represent the possible options available.
	"""
	name = "examplecommand"
	count = 0
	description = "an example command"
	discofeatures = [NS_COMMANDS, NS_DATA]

	# This is the command template
	def __init__(self, jid=""):
		"""
		Set up the class.
		"""
		PlugIn.__init__(self)
		DBG_LINE = "command"
		self.sessioncount = 0
		self.sessions = {}
		# Disco information for command list pre-formatted as a tuple
		self.discoinfo = {
			"ids": [{
				"category": "automation",
				"type": "command-node",
				"name": self.description
			}],
			"features": self.discofeatures
		}
		self._jid = jid

	def plugin(self, owner):
		"""
		Plug command into the commands class.
		"""
		# The owner in this instance is the Command Processor
		self._commands = owner
		self._owner = owner._owner
		self._commands.addCommand(self.name, self._DiscoHandler, self.Execute, jid=self._jid)

	def plugout(self):
		"""
		Remove command from the commands class.
		"""
		self._commands.delCommand(self.name, self._jid)

	def getSessionID(self):
		"""
		Returns an id for the command session.
		"""
		self.count += 1
		return "cmd-%s-%d" % (self.name, self.count)

	def Execute(self, conn, request):
		"""
		The method that handles all the commands, and routes them to the correct method for that stage.
		"""
		# New request or old?
		try:
			session = request.getTagAttr("command", "sessionid")
		except Exception:
			session = None
		try:
			action = request.getTagAttr("command", "action")
		except Exception:
			action = None
		if action == None:
			action = "execute"
		# Check session is in session list
		if session in self.sessions:
			if self.sessions[session]["jid"] == request.getFrom():
				# Check action is vaild
				if action in self.sessions[session]["actions"]:
					# Execute next action
					self.sessions[session]["actions"][action](conn, request)
				else:
					# Stage not presented as an option
					self._owner.send(Error(request, ERR_BAD_REQUEST))
					raise NodeProcessed()
			else:
				# Jid and session don't match. Go away imposter
				self._owner.send(Error(request, ERR_BAD_REQUEST))
				raise NodeProcessed()
		elif session != None:
			# Not on this sessionid you won't.
			self._owner.send(Error(request, ERR_BAD_REQUEST))
			raise NodeProcessed()
		else:
			# New session
			self.initial[action](conn, request)

	def _DiscoHandler(self, conn, request, typ):
		"""
		The handler for discovery events.
		"""
		if typ == "list":
			result = (request.getTo(), self.name, self.description)
		elif typ == "items":
			result = []
		elif typ == "info":
			result = self.discoinfo
		return result

class TestCommand(Command_Handler_Prototype):
	"""
	Example class. You should read source if you wish to understate how it works.
	Generally, it presents a "master" that giudes user through to calculate something.
	"""
	name = "testcommand"
	description = "a noddy example command"

	def __init__(self, jid=""):
		""" Init internal constants. """
		Command_Handler_Prototype.__init__(self, jid)
		self.initial = {"execute": self.cmdFirstStage}

	def cmdFirstStage(self, conn, request):
		"""
		Determine.
		"""
		# This is the only place this should be repeated as all other stages should have SessionIDs
		try:
			session = request.getTagAttr("command", "sessionid")
		except Exception:
			session = None
		if session == None:
			session = self.getSessionID()
			self.sessions[session] = {
				"jid": request.getFrom(),
				"actions": {
					"cancel": self.cmdCancel,
					"next": self.cmdSecondStage,
					"execute": self.cmdSecondStage
				},
				"data": {"type": None}
			}
		# As this is the first stage we only send a form
		reply = request.buildReply("result")
		form = DataForm(title="Select type of operation",
			data=[
				"Use the combobox to select the type of calculation you would like to do, then click Next.",
				DataField(name="calctype", desc="Calculation Type",
					value=self.sessions[session]["data"]["type"],
					options=[
						["circlediameter", "Calculate the Diameter of a circle"],
						["circlearea", "Calculate the area of a circle"]
					],
					typ="list-single",
					required=1
			)])
		replypayload = [Node("actions", attrs={"execute": "next"}, payload=[Node("next")]), form]
		reply.addChild(name="command",
			namespace=NS_COMMANDS,
			attrs={
				"node": request.getTagAttr("command", "node"),
				"sessionid": session,
				"status": "executing"
			},
			payload=replypayload
		)
		self._owner.send(reply)
		raise NodeProcessed()

	def cmdSecondStage(self, conn, request):
		form = DataForm(node=request.getTag(name="command").getTag(name="x", namespace=NS_DATA))
		self.sessions[request.getTagAttr("command", "sessionid")]["data"]["type"] = form.getField("calctype").getValue()
		self.sessions[request.getTagAttr("command", "sessionid")]["actions"] = {
			"cancel": self.cmdCancel,
			None: self.cmdThirdStage,
			"previous": self.cmdFirstStage,
			"execute": self.cmdThirdStage,
			"next": self.cmdThirdStage
		}
		# The form generation is split out to another method as it may be called by cmdThirdStage
		self.cmdSecondStageReply(conn, request)

	def cmdSecondStageReply(self, conn, request):
		reply = request.buildReply("result")
		form = DataForm(title="Enter the radius",
			data=[
				"Enter the radius of the circle (numbers only)",
				DataField(desc="Radius", name="radius", typ="text-single")
			])
		replypayload = [
			Node("actions",
			attrs={"execute": "complete"},
			payload=[Node("complete"),
			Node("prev")]),
			form
		]
		reply.addChild(name="command",
			namespace=NS_COMMANDS,
			attrs={
				"node": request.getTagAttr("command", "node"),
				"sessionid": request.getTagAttr("command", "sessionid"),
				"status": "executing"
			},
			payload=replypayload
		)
		self._owner.send(reply)
		raise NodeProcessed()

	def cmdThirdStage(self, conn, request):
		form = DataForm(node=request.getTag(name="command").getTag(name="x", namespace=NS_DATA))
		try:
			numb = float(form.getField("radius").getValue())
		except Exception:
			self.cmdSecondStageReply(conn, request)
		from math import pi
		if self.sessions[request.getTagAttr("command", "sessionid")]["data"]["type"] == "circlearea":
			result = (numb ** 2) * pi
		else:
			result = numb * 2 * pi
		reply = request.buildReply("result")
		form = DataForm(typ="result", data=[DataField(desc="result", name="result", value=result)])
		reply.addChild(name="command",
			namespace=NS_COMMANDS,
			attrs={
				"node": request.getTagAttr("command", "node"),
				"sessionid": request.getTagAttr("command", "sessionid"),
				"status": "completed"
			},
			payload=[form]
		)
		self._owner.send(reply)
		raise NodeProcessed()

	def cmdCancel(self, conn, request):
		reply = request.buildReply("result")
		reply.addChild(name="command",
			namespace=NS_COMMANDS,
			attrs={
				"node": request.getTagAttr("command", "node"),
				"sessionid": request.getTagAttr("command", "sessionid"),
				"status": "cancelled"
			})
		self._owner.send(reply)
		del self.sessions[request.getTagAttr("command", "sessionid")]

########NEW FILE########
__FILENAME__ = debug
##   debug.py
##
##   Copyright (C) 2003 Jacob Lundqvist
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU Lesser General Public License as published
##   by the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU Lesser General Public License for more details.

# $Id: debug.py, v1.41 2013/10/21 alkorgun Exp $

_version_ = "1.4.1"

import os
import sys
import time

from traceback import format_exception as traceback_format_exception

colors_enabled = "TERM" in os.environ

color_none = chr(27) + "[0m"
color_black = chr(27) + "[30m"
color_red = chr(27) + "[31m"
color_green = chr(27) + "[32m"
color_brown = chr(27) + "[33m"
color_blue = chr(27) + "[34m"
color_magenta = chr(27) + "[35m"
color_cyan = chr(27) + "[36m"
color_light_gray = chr(27) + "[37m"
color_dark_gray = chr(27) + "[30;1m"
color_bright_red = chr(27) + "[31;1m"
color_bright_green = chr(27) + "[32;1m"
color_yellow = chr(27) + "[33;1m"
color_bright_blue = chr(27) + "[34;1m"
color_purple = chr(27) + "[35;1m"
color_bright_cyan = chr(27) + "[36;1m"
color_white = chr(27) + "[37;1m"

class NoDebug:

	def __init__(self, *args, **kwargs):
		self.debug_flags = []

	def show(self, *args, **kwargs):
		pass

	def Show(self, *args, **kwargs):
		pass

	def is_active(self, flag):
		pass

	colors = {}

	def active_set(self, active_flags=None):
		return 0

LINE_FEED = "\n"

class Debug:

	def __init__(self, active_flags=None, log_file=sys.stderr, prefix="DEBUG: ", sufix="\n", time_stamp=0, flag_show=None, validate_flags=False, welcome=-1):
		self.debug_flags = []
		if welcome == -1:
			if active_flags and len(active_flags):
				welcome = 1
			else:
				welcome = 0
		self._remove_dupe_flags()
		if log_file:
			if isinstance(log_file, str):
				try:
					self._fh = open(log_file, "w")
				except Exception:
					print("ERROR: can open %s for writing." % log_file)
					sys.exit(0)
			else: # assume its a stream type object
				self._fh = log_file
		else:
			self._fh = sys.stdout
		if time_stamp not in (0, 1, 2):
			raise Exception("Invalid time_stamp param", str(time_stamp))
		self.prefix = prefix
		self.sufix = sufix
		self.time_stamp = time_stamp
		self.flag_show = None # must be initialised after possible welcome
		self.validate_flags = validate_flags
		self.active_set(active_flags)
		if welcome:
			self.show("")
			caller = sys._getframe(1) # used to get name of caller
			try:
				mod_name = ":%s" % caller.f_locals["__name__"]
			except Exception:
				mod_name = ""
			self.show("Debug created for %s%s" % (caller.f_code.co_filename, mod_name))
			self.show(" flags defined: %s" % ",".join(self.active))
		if isinstance(flag_show, (str, type(None))):
			self.flag_show = flag_show
		else:
			raise Exception("Invalid type for flag_show!", str(flag_show))

	def show(self, msg, flag=None, prefix=None, sufix=None, lf=0):
		"""
		flag can be of folowing types:
			None - this msg will always be shown if any debugging is on
			flag - will be shown if flag is active
			(flag1,flag2,,,) - will be shown if any of the given flags are active

		if prefix / sufix are not given, default ones from init will be used

		lf = -1 means strip linefeed if pressent
		lf = 1 means add linefeed if not pressent
		"""
		if self.validate_flags:
			self._validate_flag(flag)
		if not self.is_active(flag):
			return None
		if prefix:
			pre = prefix
		else:
			pre = self.prefix
		if sufix:
			suf = sufix
		else:
			suf = self.sufix
		if self.time_stamp == 2:
			output = "%s%s " % (
				pre,
				time.strftime("%b %d %H:%M:%S",
				time.localtime(time.time()))
			)
		elif self.time_stamp == 1:
			output = "%s %s" % (
				time.strftime("%b %d %H:%M:%S",
				time.localtime(time.time())),
				pre
			)
		else:
			output = pre
		if self.flag_show:
			if flag:
				output = "%s%s%s" % (output, flag, self.flag_show)
			else:
				# this call uses the global default, dont print "None", just show the separator
				output = "%s %s" % (output, self.flag_show)
		output = "%s%s%s" % (output, msg, suf)
		if lf:
			# strip/add lf if needed
			last_char = output[-1]
			if lf == 1 and last_char != LINE_FEED:
				output = output + LINE_FEED
			elif lf == -1 and last_char == LINE_FEED:
				output = output[:-1]
		try:
			self._fh.write(output)
		except Exception:
			# unicode strikes again ;)
			s = unicode()
			for i in xrange(len(output)):
				if ord(output[i]) < 128:
					c = output[i]
				else:
					c = "?"
				s += c
			self._fh.write("%s%s%s" % (pre, s, suf))
		self._fh.flush()

	def is_active(self, flag):
		"""
		If given flag(s) should generate output.
		"""
		# try to abort early to quicken code
		if not self.active:
			return 0
		if not flag or flag in self.active:
			return 1
		else:
			# check for multi flag type:
			if isinstance(flag, (list, tuple)):
				for s in flag:
					if s in self.active:
						return 1
		return 0

	def active_set(self, active_flags=None):
		"""
		Returns 1 if any flags where actually set, otherwise 0.
		"""
		r = 0
		ok_flags = []
		if not active_flags:
			# no debuging at all
			self.active = []
		elif isinstance(active_flags, (tuple, list)):
			flags = self._as_one_list(active_flags)
			for t in flags:
				if t not in self.debug_flags:
					sys.stderr.write("Invalid debugflag given: %s\n" % t)
				ok_flags.append(t)

			self.active = ok_flags
			r = 1
		else:
			# assume comma string
			try:
				flags = active_flags.split(",")
			except Exception:
				self.show("***")
				self.show("*** Invalid debug param given: %s" % active_flags)
				self.show("*** please correct your param!")
				self.show("*** due to this, full debuging is enabled")
				self.active = self.debug_flags
			for f in flags:
				s = f.strip()
				ok_flags.append(s)
			self.active = ok_flags
		self._remove_dupe_flags()
		return r

	def active_get(self):
		"""
		Returns currently active flags.
		"""
		return self.active

	def _as_one_list(self, items):
		"""
		Init param might contain nested lists, typically from group flags.
		This code organises lst and remves dupes.
		"""
		if not isinstance(items, (list, tuple)):
			return [items]
		r = []
		for l in items:
			if isinstance(l, list):
				lst2 = self._as_one_list(l)
				for l2 in lst2:
					self._append_unique_str(r, l2)
			elif l == None:
				continue
			else:
				self._append_unique_str(r, l)
		return r

	def _append_unique_str(self, lst, item):
		"""
		Filter out any dupes.
		"""
		if not isinstance(item, str):
			raise Exception("Invalid item type (should be string)", str(item))
		if item not in lst:
			lst.append(item)
		return lst

	def _validate_flag(self, flags):
		"""
		Verify that flag is defined.
		"""
		if flags:
			for flag in self._as_one_list(flags):
				if not flag in self.debug_flags:
					raise Exception("Invalid debugflag given", str(flag))

	def _remove_dupe_flags(self):
		"""
		If multiple instances of Debug is used in same app,
		some flags might be created multiple time, filter out dupes.
		"""
		unique_flags = []
		for f in self.debug_flags:
			if f not in unique_flags:
				unique_flags.append(f)
		self.debug_flags = unique_flags

	colors = {}

	def Show(self, flag, msg, prefix=""):
		msg = msg.replace("\r", "\\r").replace("\n", "\\n").replace("><", ">\n  <")
		if not colors_enabled:
			pass
		elif prefix in self.colors:
			msg = self.colors[prefix] + msg + color_none
		else:
			msg = color_none + msg
		if not colors_enabled:
			prefixcolor = ""
		elif flag in self.colors:
			prefixcolor = self.colors[flag]
		else:
			prefixcolor = color_none
		if prefix == "error":
			e = sys.exc_info()
			if e[0]:
				msg = msg + "\n" + "".join(traceback_format_exception(e[0], e[1], e[2])).rstrip()
		prefix = self.prefix + prefixcolor + (flag + " " * 12)[:12] + " " + (prefix + " " * 6)[:6]
		self.show(msg, flag, prefix)

	def is_active(self, flag):
		if not self.active:
			return 0
		if not flag or flag in self.active and DBG_ALWAYS not in self.active or flag not in self.active and DBG_ALWAYS in self.active:
			return 1
		return 0

DBG_ALWAYS = "always"

# Debug=NoDebug # Uncomment this to effectively disable all debugging and all debugging overhead.

########NEW FILE########
__FILENAME__ = dispatcher
##   transports.py
##
##   Copyright (C) 2003-2005 Alexey "Snake" Nezhdanov
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

# $Id: dispatcher.py, v1.45 2014/02/16 alkorgun Exp $

"""
Main xmpppy mechanism. Provides library with methods to assign different handlers
to different XMPP stanzas.
Contains one tunable attribute: DefaultTimeout (25 seconds by default). It defines time that
Dispatcher.SendAndWaitForResponce method will wait for reply stanza before giving up.
"""

import sys
import time
from . import simplexml

from .plugin import PlugIn
from .protocol import *
from select import select
from xml.parsers.expat import ExpatError

DefaultTimeout = 25
ID = 0

DBG_LINE = "dispatcher"

if sys.hexversion >= 0x30000F0:

	def deferredRaise(e):
		raise e[0](e[1]).with_traceback(e[2])

else:

	def deferredRaise(e):
		raise e[0], e[1], e[2]

class Dispatcher(PlugIn):
	"""
	Ancestor of PlugIn class. Handles XMPP stream, i.e. aware of stream headers.
	Can be plugged out/in to restart these headers (used for SASL f.e.).
	"""
	def __init__(self):
		PlugIn.__init__(self)
		self.handlers = {}
		self._expected = {}
		self._defaultHandler = None
		self._pendingExceptions = []
		self._eventHandler = None
		self._cycleHandlers = []
		self._exported_methods = [
			self.Process,
			self.RegisterHandler,
#			self.RegisterDefaultHandler,
			self.RegisterEventHandler,
			self.UnregisterCycleHandler,
			self.RegisterCycleHandler,
			self.RegisterHandlerOnce,
			self.UnregisterHandler,
			self.RegisterProtocol,
			self.WaitForResponse,
			self.SendAndWaitForResponse,
			self.send,
			self.SendAndCallForResponse,
			self.disconnect,
			self.iter
		]

	def dumpHandlers(self):
		"""
		Return set of user-registered callbacks in it's internal format.
		Used within the library to carry user handlers set over Dispatcher replugins.
		"""
		return self.handlers

	def restoreHandlers(self, handlers):
		"""
		Restores user-registered callbacks structure from dump previously obtained via dumpHandlers.
		Used within the library to carry user handlers set over Dispatcher replugins.
		"""
		self.handlers = handlers

	def _init(self):
		"""
		Registers default namespaces/protocols/handlers. Used internally.
		"""
		self.RegisterNamespace("unknown")
		self.RegisterNamespace(NS_STREAMS)
		self.RegisterNamespace(self._owner.defaultNamespace)
		self.RegisterProtocol("iq", Iq)
		self.RegisterProtocol("presence", Presence)
		self.RegisterProtocol("message", Message)
#		self.RegisterDefaultHandler(self.returnStanzaHandler)
		self.RegisterHandler("error", self.streamErrorHandler, xmlns=NS_STREAMS)

	def plugin(self, owner):
		"""
		Plug the Dispatcher instance into Client class instance and send initial stream header. Used internally.
		"""
		self._init()
		for method in self._old_owners_methods:
			if method.__name__ == "send":
				self._owner_send = method
				break
		self._owner.lastErrNode = None
		self._owner.lastErr = None
		self._owner.lastErrCode = None
		self.StreamInit()

	def plugout(self):
		"""
		Prepares instance to be destructed.
		"""
		self.Stream.dispatch = None
		self.Stream.DEBUG = None
		self.Stream.features = None
		self.Stream.destroy()

	def StreamInit(self):
		"""
		Send an initial stream header.
		"""
		self.Stream = simplexml.NodeBuilder()
		self.Stream._dispatch_depth = 2
		self.Stream.dispatch = self.dispatch
		self.Stream.stream_header_received = self._check_stream_start
		self._owner.debug_flags.append(simplexml.DBG_NODEBUILDER)
		self.Stream.DEBUG = self._owner.DEBUG
		self.Stream.features = None
		self._metastream = Node("stream:stream")
		self._metastream.setNamespace(self._owner.Namespace)
		self._metastream.setAttr("version", "1.0")
		self._metastream.setAttr("xmlns:stream", NS_STREAMS)
		self._metastream.setAttr("to", self._owner.Server)
		self._owner.send("<?xml version=\"1.0\"?>%s>" % str(self._metastream)[:-2])

	def _check_stream_start(self, ns, tag, attrs):
		if ns != NS_STREAMS or tag != "stream":
			raise ValueError("Incorrect stream start: (%s,%s). Terminating." % (tag, ns))

	def Process(self, timeout=8):
		"""
		Check incoming stream for data waiting. If "timeout" is positive - block for as max. this time.
		Returns:
		1) length of processed data if some data were processed;
		2) "0" string if no data were processed but link is alive;
		3) 0 (zero) if underlying connection is closed.
		Take note that in case of disconnection detect during Process() call
		disconnect handlers are called automatically.
		"""
		for handler in self._cycleHandlers:
			handler(self)
		if self._pendingExceptions:
			deferredRaise(self._pendingExceptions.pop())
		if self._owner.Connection.pending_data(timeout):
			try:
				data = self._owner.Connection.receive()
			except IOError:
				return None
			try:
				self.Stream.Parse(data)
			except ExpatError:
				pass
			if self._pendingExceptions:
				deferredRaise(self._pendingExceptions.pop())
			if data:
				return len(data)
		return "0"

	def RegisterNamespace(self, xmlns, order="info"):
		"""
		Creates internal structures for newly registered namespace.
		You can register handlers for this namespace afterwards. By default one namespace
		already registered (jabber:client or jabber:component:accept depending on context.
		"""
		self.DEBUG("Registering namespace \"%s\"" % xmlns, order)
		self.handlers[xmlns] = {}
		self.RegisterProtocol("unknown", Protocol, xmlns=xmlns)
		self.RegisterProtocol("default", Protocol, xmlns=xmlns)

	def RegisterProtocol(self, tag_name, Proto, xmlns=None, order="info"):
		"""
		Used to declare some top-level stanza name to dispatcher.
		Needed to start registering handlers for such stanzas.
		Iq, message and presence protocols are registered by default.
		"""
		if not xmlns:
			xmlns = self._owner.defaultNamespace
		self.DEBUG("Registering protocol \"%s\" as %s(%s)" % (tag_name, Proto, xmlns), order)
		self.handlers[xmlns][tag_name] = {"type": Proto, "default": []}

	def RegisterNamespaceHandler(self, xmlns, handler, typ="", ns="", makefirst=0, system=0):
		"""
		Register handler for processing all stanzas for specified namespace.
		"""
		self.RegisterHandler("default", handler, typ, ns, xmlns, makefirst, system)

	def RegisterHandler(self, name, handler, typ="", ns="", xmlns=None, makefirst=0, system=0):
		"""Register user callback as stanzas handler of declared type. Callback must take
		(if chained, see later) arguments: dispatcher instance (for replying), incomed
		return of previous handlers.
		The callback must raise xmpp.NodeProcessed just before return if it want preven
		callbacks to be called with the same stanza as argument _and_, more importantly
		library from returning stanza to sender with error set (to be enabled in 0.2 ve
		Arguments:
			"name" - name of stanza. F.e. "iq".
			"handler" - user callback.
			"typ" - value of stanza's "type" attribute. If not specified any value match
			"ns" - namespace of child that stanza must contain.
			"chained" - chain together output of several handlers.
			"makefirst" - insert handler in the beginning of handlers list instead of
				adding it to the end. Note that more common handlers (i.e. w/o "typ" and
				will be called first nevertheless).
			"system" - call handler even if NodeProcessed Exception were raised already.
		"""
		if not xmlns:
			xmlns = self._owner.defaultNamespace
		self.DEBUG("Registering handler %s for \"%s\" type->%s ns->%s(%s)" % (handler, name, typ, ns, xmlns), "info")
		if not typ and not ns:
			typ = "default"
		if xmlns not in self.handlers:
			self.RegisterNamespace(xmlns, "warn")
		if name not in self.handlers[xmlns]:
			self.RegisterProtocol(name, Protocol, xmlns, "warn")
		if typ + ns not in self.handlers[xmlns][name]:
			self.handlers[xmlns][name][typ + ns] = []
		if makefirst:
			self.handlers[xmlns][name][typ + ns].insert(0, {"func": handler, "system": system})
		else:
			self.handlers[xmlns][name][typ + ns].append({"func": handler, "system": system})

	def RegisterHandlerOnce(self, name, handler, typ="", ns="", xmlns=None, makefirst=0, system=0):
		"""
		Unregister handler after first call (not implemented yet).
		"""
		if not xmlns:
			xmlns = self._owner.defaultNamespace
		self.RegisterHandler(name, handler, typ, ns, xmlns, makefirst, system)

	def UnregisterHandler(self, name, handler, typ="", ns="", xmlns=None):
		"""
		Unregister handler. "typ" and "ns" must be specified exactly the same as with registering.
		"""
		if not xmlns:
			xmlns = self._owner.defaultNamespace
		if xmlns not in self.handlers:
			return None
		if not typ and not ns:
			typ = "default"
		for pack in self.handlers[xmlns][name][typ + ns]:
			if handler == pack["func"]:
				break
		else:
			pack = None
		try:
			self.handlers[xmlns][name][typ + ns].remove(pack)
		except ValueError:
			pass

	def RegisterDefaultHandler(self, handler):
		"""
		Specify the handler that will be used if no NodeProcessed exception were raised.
		This is returnStanzaHandler by default.
		"""
		self._defaultHandler = handler

	def RegisterEventHandler(self, handler):
		"""
		Register handler that will process events. F.e. "FILERECEIVED" event.
		"""
		self._eventHandler = handler

	def returnStanzaHandler(self, conn, stanza):
		"""
		Return stanza back to the sender with <feature-not-implemennted/> error set.
		"""
		if stanza.getType() in ("get", "set"):
			conn.send(Error(stanza, ERR_FEATURE_NOT_IMPLEMENTED))

	def streamErrorHandler(self, conn, error):
		name, text = "error", error.getData()
		for tag in error.getChildren():
			if tag.getNamespace() == NS_XMPP_STREAMS:
				if tag.getName() == "text":
					text = tag.getData()
				else:
					name = tag.getName()
		if name in stream_exceptions.keys():
			exc = stream_exceptions[name]
		else:
			exc = StreamError
		raise exc((name, text))

	def RegisterCycleHandler(self, handler):
		"""
		Register handler that will be called on every Dispatcher.Process() call.
		"""
		if handler not in self._cycleHandlers:
			self._cycleHandlers.append(handler)

	def UnregisterCycleHandler(self, handler):
		"""
		Unregister handler that will is called on every Dispatcher.Process() call.
		"""
		if handler in self._cycleHandlers:
			self._cycleHandlers.remove(handler)

	def Event(self, realm, event, data):
		"""
		Raise some event. Takes three arguments:
		1) "realm" - scope of event. Usually a namespace.
		2) "event" - the event itself. F.e. "SUCESSFULL SEND".
		3) data that comes along with event. Depends on event.
		"""
		if self._eventHandler:
			self._eventHandler(realm, event, data)

	def dispatch(self, stanza, session=None, direct=0):
		"""
		Main procedure that performs XMPP stanza recognition and calling apppropriate handlers for it.
		Called internally.
		"""
		if not session:
			session = self
		session.Stream._mini_dom = None
		name = stanza.getName()
		if not direct and self._owner._route:
			if name == "route":
				if stanza.getAttr("error") == None:
					if len(stanza.getChildren()) == 1:
						stanza = stanza.getChildren()[0]
						name = stanza.getName()
					else:
						for each in stanza.getChildren():
							self.dispatch(each, session, direct=1)
						return None
			elif name == "presence":
				return None
			elif name in ("features", "bind"):
				pass
			else:
				raise UnsupportedStanzaType(name)
		if name == "features":
			session.Stream.features = stanza
		xmlns = stanza.getNamespace()
		if xmlns not in self.handlers:
			self.DEBUG("Unknown namespace: " + xmlns, "warn")
			xmlns = "unknown"
		if name not in self.handlers[xmlns]:
			self.DEBUG("Unknown stanza: " + name, "warn")
			name = "unknown"
		else:
			self.DEBUG("Got %s/%s stanza" % (xmlns, name), "ok")
		if isinstance(stanza, Node):
			stanza = self.handlers[xmlns][name]["type"](node=stanza)
		typ = stanza.getType()
		if not typ:
			typ = ""
		stanza.props = stanza.getProperties()
		ID = stanza.getID()
		session.DEBUG("Dispatching %s stanza with type->%s props->%s id->%s" % (name, typ, stanza.props, ID), "ok")
		ls = ["default"] # we will use all handlers:
		if typ in self.handlers[xmlns][name]:
			ls.append(typ) # from very common...
		for prop in stanza.props:
			if prop in self.handlers[xmlns][name]:
				ls.append(prop)
			if typ and (typ + prop) in self.handlers[xmlns][name]:
				ls.append(typ + prop) # ...to very particular
		chain = self.handlers[xmlns]["default"]["default"]
		for key in ls:
			if key:
				chain = chain + self.handlers[xmlns][name][key]
		output = ""
		if ID in session._expected:
			user = 0
			if isinstance(session._expected[ID], tuple):
				cb, args = session._expected.pop(ID)
				session.DEBUG("Expected stanza arrived. Callback %s(%s) found!" % (cb, args), "ok")
				try:
					cb(session, stanza, **args)
				except NodeProcessed:
					pass
			else:
				session.DEBUG("Expected stanza arrived!", "ok")
				session._expected[ID] = stanza
		else:
			user = 1
		for handler in chain:
			if user or handler["system"]:
				try:
					handler["func"](session, stanza)
				except NodeProcessed:
					user = 0
				except Exception:
					self._pendingExceptions.insert(0, sys.exc_info())
		if user and self._defaultHandler:
			self._defaultHandler(session, stanza)

	def WaitForResponse(self, ID, timeout=DefaultTimeout):
		"""
		Block and wait until stanza with specific "id" attribute will come.
		If no such stanza is arrived within timeout, return None.
		If operation failed for some reason then owner's attributes
		lastErrNode, lastErr and lastErrCode are set accordingly.
		"""
		self._expected[ID] = None
		abort_time = time.time() + timeout
		self.DEBUG("Waiting for ID:%s with timeout %s..." % (ID, timeout), "wait")
		while not self._expected[ID]:
			if not self.Process(0.04):
				self._owner.lastErr = "Disconnect"
				return None
			if time.time() > abort_time:
				self._owner.lastErr = "Timeout"
				return None
		resp = self._expected.pop(ID)
		if resp.getErrorCode():
			self._owner.lastErrNode = resp
			self._owner.lastErr = resp.getError()
			self._owner.lastErrCode = resp.getErrorCode()
		return resp

	def SendAndWaitForResponse(self, stanza, timeout=DefaultTimeout):
		"""
		Put stanza on the wire and wait for recipient's response to it.
		"""
		return self.WaitForResponse(self.send(stanza), timeout)

	def SendAndCallForResponse(self, stanza, func, args={}):
		"""
		Put stanza on the wire and call back when recipient replies.
		Additional callback arguments can be specified in args.
		"""
		self._expected[self.send(stanza)] = (func, args)

	def send(self, stanza):
		"""
		Serialize stanza and put it on the wire. Assign an unique ID to it before send.
		Returns assigned ID.
		"""
		if isinstance(stanza, basestring):
			return self._owner_send(stanza)
		if not isinstance(stanza, Protocol):
			id = None
		elif not stanza.getID():
			global ID
			ID += 1
			id = repr(ID)
			stanza.setID(id)
		else:
			id = stanza.getID()
		if self._owner._registered_name and not stanza.getAttr("from"):
			stanza.setAttr("from", self._owner._registered_name)
		if self._owner._route and stanza.getName() != "bind":
			to = self._owner.Server
			if stanza.getTo() and stanza.getTo().getDomain():
				to = stanza.getTo().getDomain()
			frm = stanza.getFrom()
			if frm.getDomain():
				frm = frm.getDomain()
			route = Protocol("route", to=to, frm=frm, payload=[stanza])
			stanza = route
		stanza.setNamespace(self._owner.Namespace)
		stanza.setParent(self._metastream)
		self._owner_send(stanza)
		return id

	def disconnect(self):
		"""
		Send a stream terminator and and handle all incoming stanzas before stream closure.
		"""
		self._owner_send("</stream:stream>")
		while self.Process(1):
			pass

	iter = type(send)(Process.__code__, Process.__globals__, name = "iter", argdefs = Process.__defaults__, closure = Process.__closure__)

########NEW FILE########
__FILENAME__ = features
##   features.py
##
##   Copyright (C) 2003-2004 Alexey "Snake" Nezhdanov
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

# $Id: features.py, v1.26 2013/10/21 alkorgun Exp $

"""
This module contains variable stuff that is not worth splitting into separate modules.
Here is:
	DISCO client and agents-to-DISCO and browse-to-DISCO emulators.
	IBR and password manager.
	jabber:iq:privacy methods
All these methods takes "disp" first argument that should be already connected
(and in most cases already authorised) dispatcher instance.
"""

from .protocol import *

REGISTER_DATA_RECEIVED = "REGISTER DATA RECEIVED"

def _discover(disp, ns, jid, node=None, fb2b=0, fb2a=1):
	"""
	Try to obtain info from the remote object.
	If remote object doesn't support disco fall back to browse (if fb2b is true)
	and if it doesnt support browse (or fb2b is not true) fall back to agents protocol
	(if gb2a is true). Returns obtained info. Used internally.
	"""
	iq = Iq(to=jid, typ="get", queryNS=ns)
	if node:
		iq.setQuerynode(node)
	rep = disp.SendAndWaitForResponse(iq)
	if fb2b and not isResultNode(rep):
		rep = disp.SendAndWaitForResponse(Iq(to=jid, typ="get", queryNS=NS_BROWSE)) # Fallback to browse
	if fb2a and not isResultNode(rep):
		rep = disp.SendAndWaitForResponse(Iq(to=jid, typ="get", queryNS=NS_AGENTS)) # Fallback to agents
	if isResultNode(rep):
		return [n for n in rep.getQueryPayload() if isinstance(n, Node)]
	return []

def discoverItems(disp, jid, node=None):
	"""
	Query remote object about any items that it contains. Return items list.
	"""
	ret = []
	for i in _discover(disp, NS_DISCO_ITEMS, jid, node):
		if i.getName() == "agent" and i.getTag("name"):
			i.setAttr("name", i.getTagData("name"))
		ret.append(i.attrs)
	return ret

def discoverInfo(disp, jid, node=None):
	"""
	Query remote object about info that it publishes. Returns identities and features lists.
	"""
	identities, features = [], []
	for i in _discover(disp, NS_DISCO_INFO, jid, node):
		if i.getName() == "identity":
			identities.append(i.attrs)
		elif i.getName() == "feature":
			features.append(i.getAttr("var"))
		elif i.getName() == "agent":
			if i.getTag("name"):
				i.setAttr("name", i.getTagData("name"))
			if i.getTag("description"):
				i.setAttr("name", i.getTagData("description"))
			identities.append(i.attrs)
			if i.getTag("groupchat"):
				features.append(NS_GROUPCHAT)
			if i.getTag("register"):
				features.append(NS_REGISTER)
			if i.getTag("search"):
				features.append(NS_SEARCH)
	return identities, features

def getRegInfo(disp, host, info={}, sync=True):
	"""
	Gets registration form from remote host.
	You can pre-fill the info dictionary.
	F.e. if you are requesting info on registering user joey than specify
	info as {"username": "joey"}. See JEP-0077 for details.
	"disp" must be connected dispatcher instance.
	"""
	iq = Iq("get", NS_REGISTER, to=host)
	for i in info.keys():
		iq.setTagData(i, info[i])
	if sync:
		resp = disp.SendAndWaitForResponse(iq)
		_ReceivedRegInfo(disp.Dispatcher, resp, host)
		return resp
	else:
		disp.SendAndCallForResponse(iq, _ReceivedRegInfo, {"agent": host})

def _ReceivedRegInfo(con, resp, agent):
	iq = Iq("get", NS_REGISTER, to=agent)
	if not isResultNode(resp):
		return None
	df = resp.getTag("query", namespace=NS_REGISTER).getTag("x", namespace=NS_DATA)
	if df:
		con.Event(NS_REGISTER, REGISTER_DATA_RECEIVED, (agent, DataForm(node=df)))
		return None
	df = DataForm(typ="form")
	for i in resp.getQueryPayload():
		if not isinstance(i, Iq):
			pass
		elif i.getName() == "instructions":
			df.addInstructions(i.getData())
		else:
			df.setField(i.getName()).setValue(i.getData())
	con.Event(NS_REGISTER, REGISTER_DATA_RECEIVED, (agent, df))

def register(disp, host, info):
	"""
	Perform registration on remote server with provided info.
	disp must be connected dispatcher instance.
	Returns true or false depending on registration result.
	If registration fails you can get additional info from the dispatcher's owner
	attributes lastErrNode, lastErr and lastErrCode.
	"""
	iq = Iq("set", NS_REGISTER, to=host)
	if not isinstance(info, dict):
		info = info.asDict()
	for i in info.keys():
		iq.setTag("query").setTagData(i, info[i])
	resp = disp.SendAndWaitForResponse(iq)
	if isResultNode(resp):
		return 1

def unregister(disp, host):
	"""
	Unregisters with host (permanently removes account).
	disp must be connected and authorized dispatcher instance.
	Returns true on success.
	"""
	resp = disp.SendAndWaitForResponse(Iq("set", NS_REGISTER, to=host, payload=[Node("remove")]))
	if isResultNode(resp):
		return 1

def changePasswordTo(disp, newpassword, host=None):
	"""
	Changes password on specified or current (if not specified) server.
	disp must be connected and authorized dispatcher instance.
	Returns true on success."""
	if not host:
		host = disp._owner.Server
	resp = disp.SendAndWaitForResponse(Iq("set", NS_REGISTER, to=host,
		payload=[
			Node("username", payload=[disp._owner.User]),
			Node("password", payload=[newpassword])
		]))
	if isResultNode(resp):
		return 1

def getPrivacyLists(disp):
	"""
	Requests privacy lists from connected server.
	Returns dictionary of existing lists on success.
	"""
	dict = {"lists": []}
	try:
		resp = disp.SendAndWaitForResponse(Iq("get", NS_PRIVACY))
		if not isResultNode(resp):
			return None
		for list in resp.getQueryPayload():
			if list.getName() == "list":
				dict["lists"].append(list.getAttr("name"))
			else:
				dict[list.getName()] = list.getAttr("name")
	except Exception:
		pass
	else:
		return dict

def getPrivacyList(disp, listname):
	"""
	Requests specific privacy list listname. Returns list of XML nodes (rules)
	taken from the server responce.
	"""
	try:
		resp = disp.SendAndWaitForResponse(Iq("get", NS_PRIVACY, payload=[Node("list", {"name": listname})]))
		if isResultNode(resp):
			return resp.getQueryPayload()[0]
	except Exception:
		pass

def setActivePrivacyList(disp, listname=None, typ="active"):
	"""
	Switches privacy list "listname" to specified type.
	By default the type is "active". Returns true on success.
	"""
	if listname:
		attrs = {"name": listname}
	else:
		attrs = {}
	resp = disp.SendAndWaitForResponse(Iq("set", NS_PRIVACY, payload=[Node(typ, attrs)]))
	if isResultNode(resp):
		return 1

def setDefaultPrivacyList(disp, listname=None):
	"""
	Sets the default privacy list as "listname". Returns true on success.
	"""
	return setActivePrivacyList(disp, listname, "default")

def setPrivacyList(disp, list):
	"""
	Set the ruleset. "list" should be the simpleXML node formatted
	according to RFC 3921 (XMPP-IM) (I.e. Node("list", {"name": listname}, payload=[...]) )
	Returns true on success.
	"""
	resp = disp.SendAndWaitForResponse(Iq("set", NS_PRIVACY, payload=[list]))
	if isResultNode(resp):
		return 1

def delPrivacyList(disp, listname):
	"""
	Deletes privacy list "listname". Returns true on success.
	"""
	resp = disp.SendAndWaitForResponse(Iq("set", NS_PRIVACY, payload=[Node("list", {"name": listname})]))
	if isResultNode(resp):
		return 1

########NEW FILE########
__FILENAME__ = filetransfer
##   filetransfer.py
##
##   Copyright (C) 2004 Alexey "Snake" Nezhdanov
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

# $Id: filetransfer.py, v1.7 2013/10/21 alkorgun Exp $

"""
This module contains IBB class that is the simple implementation of JEP-0047.
Note that this is just a transport for data. You have to negotiate data transfer before
(via StreamInitiation most probably). Unfortunately SI is not implemented yet.
"""

from base64 import encodestring, decodestring
from .dispatcher import PlugIn
from .protocol import *

class IBB(PlugIn):
	"""
	IBB used to transfer small-sized data chunk over estabilished xmpp connection.
	Data is split into small blocks (by default 3000 bytes each), encoded as base 64
	and sent to another entity that compiles these blocks back into the data chunk.
	This is very inefficiend but should work under any circumstances. Note that
	using IBB normally should be the last resort.
	"""
	def __init__(self):
		"""
		Initialise internal variables.
		"""
		PlugIn.__init__(self)
		self.DBG_LINE = "ibb"
		self._exported_methods = [self.OpenStream]
		self._streams = {}
		self._ampnode = Node(NS_AMP + " amp",
			payload=[
				Node("rule", {"condition": "deliver-at", "value": "stored", "action": "error"}),
				Node("rule", {"condition": "match-resource", "value": "exact", "action": "error"})
			])

	def plugin(self, owner):
		"""
		Register handlers for receiving incoming datastreams. Used internally.
		"""
		self._owner.RegisterHandlerOnce("iq", self.StreamOpenReplyHandler)
		self._owner.RegisterHandler("iq", self.IqHandler, ns=NS_IBB)
		self._owner.RegisterHandler("message", self.ReceiveHandler, ns=NS_IBB)

	def IqHandler(self, conn, stanza):
		"""
		Handles streams state change. Used internally.
		"""
		typ = stanza.getType()
		self.DEBUG("IqHandler called typ->%s" % typ, "info")
		if typ == "set" and stanza.getTag("open", namespace=NS_IBB):
			self.StreamOpenHandler(conn, stanza)
		elif typ == "set" and stanza.getTag("close", namespace=NS_IBB):
			self.StreamCloseHandler(conn, stanza)
		elif typ == "result":
			self.StreamCommitHandler(conn, stanza)
		elif typ == "error":
			self.StreamOpenReplyHandler(conn, stanza)
		else:
			conn.send(Error(stanza, ERR_BAD_REQUEST))
		raise NodeProcessed()

	def StreamOpenHandler(self, conn, stanza):
		"""
		Handles opening of new incoming stream. Used internally.
		"""
		err = None
		sid = stanza.getTagAttr("open", "sid")
		blocksize = stanza.getTagAttr("open", "block-size")
		self.DEBUG("StreamOpenHandler called sid->%s blocksize->%s" % (sid, blocksize), "info")
		try:
			blocksize = int(blocksize)
		except Exception:
			err = ERR_BAD_REQUEST
		if not sid or not blocksize:
			err = ERR_BAD_REQUEST
		elif sid in self._streams.keys():
			err = ERR_UNEXPECTED_REQUEST
		if err:
			rep = Error(stanza, err)
		else:
			self.DEBUG("Opening stream: id %s, block-size %s" % (sid, blocksize), "info")
			rep = Protocol("iq", stanza.getFrom(), "result", stanza.getTo(), {"id": stanza.getID()})
			self._streams[sid] = {
				"direction": "<" + str(stanza.getFrom()),
				"block-size": blocksize,
				"fp": open("/tmp/xmpp_file_" + sid, "w"),
				"seq": 0,
				"syn_id": stanza.getID()
			}
		conn.send(rep)

	def OpenStream(self, sid, to, fp, blocksize=3000):
		"""
		Start new stream. You should provide stream id "sid", the endpoind jid "to",
		the file object containing info for send "fp". Also the desired blocksize can be specified.
		Take into account that recommended stanza size is 4k and IBB uses base64 encoding
		that increases size of data by 1/3.
		"""
		if sid in self._streams.keys():
			return None
		if not JID(to).getResource():
			return None
		self._streams[sid] = {"direction": "|>" + to, "block-size": blocksize, "fp": fp, "seq": 0}
		self._owner.RegisterCycleHandler(self.SendHandler)
		syn = Protocol("iq", to, "set", payload=[Node(NS_IBB + " open", {"sid": sid, "block-size": blocksize})])
		self._owner.send(syn)
		self._streams[sid]["syn_id"] = syn.getID()
		return self._streams[sid]

	def SendHandler(self, conn):
		"""
		Send next portion of data if it is time to do it. Used internally.
		"""
		self.DEBUG("SendHandler called", "info")
		for sid in self._streams.keys():
			stream = self._streams[sid]
			if stream["direction"][:2] == "|>":
				cont = 1
			elif stream["direction"][0] == ">":
				chunk = stream["fp"].read(stream["block-size"])
				if chunk:
					datanode = Node(NS_IBB + " data", {"sid": sid, "seq": stream["seq"]}, encodestring(chunk))
					stream["seq"] += 1
					if stream["seq"] == 65536:
						stream["seq"] = 0
					conn.send(Protocol("message", stream["direction"][1:], payload=[datanode, self._ampnode]))
				else:
					conn.send(Protocol("iq", stream["direction"][1:], "set", payload=[Node(NS_IBB + " close", {"sid": sid})]))
					conn.Event(self.DBG_LINE, "SUCCESSFULL SEND", stream)
					del self._streams[sid]
					self._owner.UnregisterCycleHandler(self.SendHandler)

	def ReceiveHandler(self, conn, stanza):
		"""
		Receive next portion of incoming datastream and store it write
		it to temporary file. Used internally.
		"""
		sid, seq, data = stanza.getTagAttr("data", "sid"), stanza.getTagAttr("data", "seq"), stanza.getTagData("data")
		self.DEBUG("ReceiveHandler called sid->%s seq->%s" % (sid, seq), "info")
		try:
			seq = int(seq)
			data = decodestring(data)
		except Exception:
			seq = data = ""
		err = None
		if not sid in self._streams.keys():
			err = ERR_ITEM_NOT_FOUND
		else:
			stream = self._streams[sid]
			if not data:
				err = ERR_BAD_REQUEST
			elif seq != stream["seq"]:
				err = ERR_UNEXPECTED_REQUEST
			else:
				self.DEBUG("Successfull receive sid->%s %s+%s bytes" % (sid, stream["fp"].tell(), len(data)), "ok")
				stream["seq"] += 1
				stream["fp"].write(data)
		if err:
			self.DEBUG("Error on receive: %s" % err, "error")
			conn.send(Error(Iq(to=stanza.getFrom(), frm=stanza.getTo(), payload=[Node(NS_IBB + " close")]), err, reply=0))

	def StreamCloseHandler(self, conn, stanza):
		"""
		Handle stream closure due to all data transmitted.
		Raise xmpppy event specifying successfull data receive.
		"""
		sid = stanza.getTagAttr("close", "sid")
		self.DEBUG("StreamCloseHandler called sid->%s" % sid, "info")
		if sid in self._streams.keys():
			conn.send(stanza.buildReply("result"))
			conn.Event(self.DBG_LINE, "SUCCESSFULL RECEIVE", self._streams[sid])
			del self._streams[sid]
		else:
			conn.send(Error(stanza, ERR_ITEM_NOT_FOUND))

	def StreamBrokenHandler(self, conn, stanza):
		"""
		Handle stream closure due to all some error while receiving data.
		Raise xmpppy event specifying unsuccessfull data receive.
		"""
		syn_id = stanza.getID()
		self.DEBUG("StreamBrokenHandler called syn_id->%s" % syn_id, "info")
		for sid in self._streams.keys():
			stream = self._streams[sid]
			if stream["syn_id"] == syn_id:
				if stream["direction"][0] == "<":
					conn.Event(self.DBG_LINE, "ERROR ON RECEIVE", stream)
				else:
					conn.Event(self.DBG_LINE, "ERROR ON SEND", stream)
				del self._streams[sid]

	def StreamOpenReplyHandler(self, conn, stanza):
		"""
		Handle remote side reply about is it agree or not to receive our datastream.
		Used internally. Raises xmpppy event specfiying if the data transfer is agreed upon.
		"""
		syn_id = stanza.getID()
		self.DEBUG("StreamOpenReplyHandler called syn_id->%s" % syn_id, "info")
		for sid in self._streams.keys():
			stream = self._streams[sid]
			if stream["syn_id"] == syn_id:
				if stanza.getType() == "error":
					if stream["direction"][0] == "<":
						conn.Event(self.DBG_LINE, "ERROR ON RECEIVE", stream)
					else:
						conn.Event(self.DBG_LINE, "ERROR ON SEND", stream)
					del self._streams[sid]
				elif stanza.getType() == "result":
					if stream["direction"][0] == "|":
						stream["direction"] = stream["direction"][1:]
						conn.Event(self.DBG_LINE, "STREAM COMMITTED", stream)
					else:
						conn.send(Error(stanza, ERR_UNEXPECTED_REQUEST))

########NEW FILE########
__FILENAME__ = plugin
##   plugin.py
##
##   Copyright (C) 2003-2005 Alexey "Snake" Nezhdanov
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

# $Id: plugin.py, v1.0 2013/10/21 alkorgun Exp $

"""
Provides library with all Non-SASL and SASL authentication mechanisms.
Can be used both for client and transport authentication.
"""

class PlugIn:
	"""
	Common xmpppy plugins infrastructure: plugging in/out, debugging.
	"""
	def __init__(self):
		self._exported_methods = []
		self.DBG_LINE = self.__class__.__name__.lower()

	def PlugIn(self, owner):
		"""
		Attach to main instance and register ourself and all our staff in it.
		"""
		self._owner = owner
		if self.DBG_LINE not in owner.debug_flags:
			owner.debug_flags.append(self.DBG_LINE)
		self.DEBUG("Plugging %s into %s" % (self, self._owner), "start")
		if hasattr(owner, self.__class__.__name__):
			return self.DEBUG("Plugging ignored: another instance already plugged.", "error")
		self._old_owners_methods = []
		for method in self._exported_methods:
			if hasattr(owner, method.__name__):
				self._old_owners_methods.append(getattr(owner, method.__name__))
			setattr(owner, method.__name__, method)
		setattr(owner, self.__class__.__name__, self)
		if hasattr(self, "plugin"):
			return self.plugin(owner)

	def PlugOut(self):
		"""
		Unregister all our staff from main instance and detach from it.
		"""
		self.DEBUG("Plugging %s out of %s." % (self, self._owner), "stop")
		if hasattr(self, "plugout"):
			rn = self.plugout()
		else:
			rn = None
		self._owner.debug_flags.remove(self.DBG_LINE)
		for method in self._exported_methods:
			delattr(self._owner, method.__name__)
		for method in self._old_owners_methods:
			setattr(self._owner, method.__name__, method)
		delattr(self._owner, self.__class__.__name__)
		return rn

	def DEBUG(self, text, severity="info"):
		"""
		Feed a provided debug line to main instance's debug facility along with our ID string.
		"""
		self._owner.DEBUG(self.DBG_LINE, text, severity)

########NEW FILE########
__FILENAME__ = protocol
##   protocol.py
##
##   Copyright (C) 2003-2005 Alexey "Snake" Nezhdanov
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

# $Id: protocol.py, v1.64 2014/01/10 alkorgun Exp $

"""
Protocol module contains tools that is needed for processing of
xmpp-related data structures.
"""

import time

from .simplexml import Node, XML_ls, XMLescape, ustr

NS_ACTIVITY			 = "http://jabber.org/protocol/activity"					# XEP-0108
NS_ADDRESS			 = "http://jabber.org/protocol/address"						# XEP-0033
NS_ADMIN			 = "http://jabber.org/protocol/admin"						# XEP-0133
NS_ADMIN_ADD_USER				 = NS_ADMIN + "#add-user"						# XEP-0133
NS_ADMIN_DELETE_USER			 = NS_ADMIN + "#delete-user"					# XEP-0133
NS_ADMIN_DISABLE_USER			 = NS_ADMIN + "#disable-user"					# XEP-0133
NS_ADMIN_REENABLE_USER			 = NS_ADMIN + "#reenable-user"					# XEP-0133
NS_ADMIN_END_USER_SESSION		 = NS_ADMIN + "#end-user-session"				# XEP-0133
NS_ADMIN_GET_USER_PASSWORD		 = NS_ADMIN + "#get-user-password"				# XEP-0133
NS_ADMIN_CHANGE_USER_PASSWORD	 = NS_ADMIN + "#change-user-password"			# XEP-0133
NS_ADMIN_GET_USER_ROSTER		 = NS_ADMIN + "#get-user-roster"				# XEP-0133
NS_ADMIN_GET_USER_LASTLOGIN		 = NS_ADMIN + "#get-user-lastlogin"				# XEP-0133
NS_ADMIN_USER_STATS				 = NS_ADMIN + "#user-stats"						# XEP-0133
NS_ADMIN_EDIT_BLACKLIST			 = NS_ADMIN + "#edit-blacklist"					# XEP-0133
NS_ADMIN_EDIT_WHITELIST			 = NS_ADMIN + "#edit-whitelist"					# XEP-0133
NS_ADMIN_REGISTERED_USERS_NUM	 = NS_ADMIN + "#get-registered-users-num"		# XEP-0133
NS_ADMIN_DISABLED_USERS_NUM		 = NS_ADMIN + "#get-disabled-users-num"			# XEP-0133
NS_ADMIN_ONLINE_USERS_NUM		 = NS_ADMIN + "#get-online-users-num"			# XEP-0133
NS_ADMIN_ACTIVE_USERS_NUM		 = NS_ADMIN + "#get-active-users-num"			# XEP-0133
NS_ADMIN_IDLE_USERS_NUM			 = NS_ADMIN + "#get-idle-users-num"				# XEP-0133
NS_ADMIN_REGISTERED_USERS_LIST	 = NS_ADMIN + "#get-registered-users-list"		# XEP-0133
NS_ADMIN_DISABLED_USERS_LIST	 = NS_ADMIN + "#get-disabled-users-list"		# XEP-0133
NS_ADMIN_ONLINE_USERS_LIST		 = NS_ADMIN + "#get-online-users-list"			# XEP-0133
NS_ADMIN_ACTIVE_USERS_LIST		 = NS_ADMIN + "#get-active-users-list"			# XEP-0133
NS_ADMIN_IDLE_USERS_LIST		 = NS_ADMIN + "#get-idle-users-list"			# XEP-0133
NS_ADMIN_ANNOUNCE				 = NS_ADMIN + "#announce"						# XEP-0133
NS_ADMIN_SET_MOTD				 = NS_ADMIN + "#set-motd"						# XEP-0133
NS_ADMIN_EDIT_MOTD				 = NS_ADMIN + "#edit-motd"						# XEP-0133
NS_ADMIN_DELETE_MOTD			 = NS_ADMIN + "#delete-motd"					# XEP-0133
NS_ADMIN_SET_WELCOME			 = NS_ADMIN + "#set-welcome"					# XEP-0133
NS_ADMIN_DELETE_WELCOME			 = NS_ADMIN + "#delete-welcome"					# XEP-0133
NS_ADMIN_EDIT_ADMIN				 = NS_ADMIN + "#edit-admin"						# XEP-0133
NS_ADMIN_RESTART				 = NS_ADMIN + "#restart"						# XEP-0133
NS_ADMIN_SHUTDOWN				 = NS_ADMIN + "#shutdown"						# XEP-0133
NS_AGENTS			 = "jabber:iq:agents"										# XEP-0094 (historical)
NS_AMP				 = "http://jabber.org/protocol/amp"							# XEP-0079
NS_AMP_ERRORS					 = NS_AMP + "#errors"							# XEP-0079
NS_AUTH				 = "jabber:iq:auth"											# XEP-0078
NS_AVATAR			 = "jabber:iq:avatar"										# XEP-0008 (historical)
NS_BIND				 = "urn:ietf:params:xml:ns:xmpp-bind"						# RFC 3920
NS_BROWSE			 = "jabber:iq:browse"										# XEP-0011 (historical)
NS_BYTESTREAM		 = "http://jabber.org/protocol/bytestreams"					# XEP-0065
NS_CAPS				 = "http://jabber.org/protocol/caps"						# XEP-0115
NS_CAPTCHA			 = "urn:xmpp:captcha"										# XEP-0158
NS_CHATSTATES		 = "http://jabber.org/protocol/chatstates"					# XEP-0085
NS_CLIENT			 = "jabber:client"											# RFC 3921
NS_COMMANDS			 = "http://jabber.org/protocol/commands"					# XEP-0050
NS_COMPONENT_ACCEPT	 = "jabber:component:accept"								# XEP-0114
NS_COMPONENT_1		 = "http://jabberd.jabberstudio.org/ns/component/1.0"		# Jabberd2
NS_COMPRESS			 = "http://jabber.org/protocol/compress"					# XEP-0138
NS_DATA				 = "jabber:x:data"											# XEP-0004
NS_DATA_LAYOUT		 = "http://jabber.org/protocol/xdata-layout"				# XEP-0141
NS_DATA_VALIDATE	 = "http://jabber.org/protocol/xdata-validate"				# XEP-0122
NS_DELAY			 = "jabber:x:delay"											# XEP-0091 (deprecated)
NS_DIALBACK			 = "jabber:server:dialback"									# RFC 3921
NS_DISCO			 = "http://jabber.org/protocol/disco"						# XEP-0030
NS_DISCO_INFO					 = NS_DISCO + "#info"							# XEP-0030
NS_DISCO_ITEMS					 = NS_DISCO + "#items"							# XEP-0030
NS_ENCRYPTED		 = "jabber:x:encrypted"										# XEP-0027
NS_EVENT			 = "jabber:x:event"											# XEP-0022 (deprecated)
NS_FEATURE			 = "http://jabber.org/protocol/feature-neg"					# XEP-0020
NS_FILE				 = "http://jabber.org/protocol/si/profile/file-transfer"	# XEP-0096
NS_GATEWAY			 = "jabber:iq:gateway"										# XEP-0100
NS_GEOLOC			 = "http://jabber.org/protocol/geoloc"						# XEP-0080
NS_GROUPCHAT		 = "gc-1.0"													# XEP-0045
NS_HTTP_BIND		 = "http://jabber.org/protocol/httpbind"					# XEP-0124
NS_IBB				 = "http://jabber.org/protocol/ibb"							# XEP-0047
NS_INVISIBLE		 = "presence-invisible"										# Jabberd2
NS_IQ				 = "iq"														# Jabberd2
NS_LAST				 = "jabber:iq:last"											# XEP-0012
NS_MEDIA			 = "urn:xmpp:media-element"									# XEP-0158
NS_MESSAGE			 = "message"												# Jabberd2
NS_MOOD				 = "http://jabber.org/protocol/mood"						# XEP-0107
NS_MUC				 = "http://jabber.org/protocol/muc"							# XEP-0045
NS_MUC_ADMIN					 = NS_MUC + "#admin"							# XEP-0045
NS_MUC_OWNER					 = NS_MUC + "#owner"							# XEP-0045
NS_MUC_UNIQUE					 = NS_MUC + "#unique"							# XEP-0045
NS_MUC_USER						 = NS_MUC + "#user"								# XEP-0045
NS_MUC_REGISTER					 = NS_MUC + "#register"							# XEP-0045
NS_MUC_REQUEST					 = NS_MUC + "#request"							# XEP-0045
NS_MUC_ROOMCONFIG				 = NS_MUC + "#roomconfig"						# XEP-0045
NS_MUC_ROOMINFO					 = NS_MUC + "#roominfo"							# XEP-0045
NS_MUC_ROOMS					 = NS_MUC + "#rooms"							# XEP-0045
NS_MUC_TRAFIC					 = NS_MUC + "#traffic"							# XEP-0045
NS_NICK				 = "http://jabber.org/protocol/nick"						# XEP-0172
NS_OFFLINE			 = "http://jabber.org/protocol/offline"						# XEP-0013
NS_OOB				 = "jabber:x:oob"											# XEP-0066
NS_PHYSLOC			 = "http://jabber.org/protocol/physloc"						# XEP-0112
NS_PRESENCE			 = "presence"												# Jabberd2
NS_PRIVACY			 = "jabber:iq:privacy"										# RFC 3921
NS_PRIVATE			 = "jabber:iq:private"										# XEP-0049
NS_PUBSUB			 = "http://jabber.org/protocol/pubsub"						# XEP-0060
NS_RC				 = "http://jabber.org/protocol/rc"							# XEP-0146
NS_REGISTER			 = "jabber:iq:register"										# XEP-0077
NS_RECEIPTS			 = "urn:xmpp:receipts"										# XEP-0184
NS_ROSTER			 = "jabber:iq:roster"										# RFC 3921
NS_ROSTERX			 = "http://jabber.org/protocol/rosterx"						# XEP-0144
NS_RPC				 = "jabber:iq:rpc"											# XEP-0009
NS_SASL				 = "urn:ietf:params:xml:ns:xmpp-sasl"						# RFC 3920
NS_SEARCH			 = "jabber:iq:search"										# XEP-0055
NS_SERVER			 = "jabber:server"											# RFC 3921
NS_SESSION			 = "urn:ietf:params:xml:ns:xmpp-session"					# RFC 3921
NS_SI				 = "http://jabber.org/protocol/si"							# XEP-0096
NS_SI_PUB			 = "http://jabber.org/protocol/sipub"						# XEP-0137
NS_SIGNED			 = "jabber:x:signed"										# XEP-0027
NS_SOFTWAREINFO		 = "urn:xmpp:dataforms:softwareinfo"						# XEP-0155
NS_STANZAS			 = "urn:ietf:params:xml:ns:xmpp-stanzas"					# RFC 3920
NS_STATS			 = "http://jabber.org/protocol/stats"						# XEP-0039
NS_STREAMS			 = "http://etherx.jabber.org/streams"						# RFC 3920
NS_TIME				 = "jabber:iq:time"											# XEP-0090 (deprecated)
NS_TLS				 = "urn:ietf:params:xml:ns:xmpp-tls"						# RFC 3920
NS_URN_ATTENTION	 = "urn:xmpp:attention:0"									# XEP-0224
NS_URN_OOB			 = "urn:xmpp:bob"											# XEP-0158
NS_URN_TIME			 = "urn:xmpp:time"											# XEP-0202
NS_VACATION			 = "http://jabber.org/protocol/vacation"					# XEP-0109
NS_VCARD			 = "vcard-temp"												# XEP-0054
NS_VCARD_UPDATE		 = "vcard-temp:x:update"									# XEP-0153
NS_VERSION			 = "jabber:iq:version"										# XEP-0092
NS_WAITINGLIST		 = "http://jabber.org/protocol/waitinglist"					# XEP-0130
NS_XHTML_IM			 = "http://jabber.org/protocol/xhtml-im"					# XEP-0071
NS_XMPP_STREAMS		 = "urn:ietf:params:xml:ns:xmpp-streams"					# RFC 3920
NS_PING				 = "urn:xmpp:ping"											# XEP-0199

NS_MUC_FILTER		 = "http://jabber.ru/muc-filter"

STREAM_NOT_AUTHORIZED			 = NS_XMPP_STREAMS + " not-authorized"
STREAM_REMOTE_CONNECTION_FAILED	 = NS_XMPP_STREAMS + " remote-connection-failed"
SASL_MECHANISM_TOO_WEAK			 = NS_SASL + " mechanism-too-weak"
STREAM_XML_NOT_WELL_FORMED		 = NS_XMPP_STREAMS + " xml-not-well-formed"
ERR_JID_MALFORMED				 = NS_STANZAS + " jid-malformed"
STREAM_SEE_OTHER_HOST			 = NS_XMPP_STREAMS + " see-other-host"
STREAM_BAD_NAMESPACE_PREFIX		 = NS_XMPP_STREAMS + " bad-namespace-prefix"
ERR_SERVICE_UNAVAILABLE			 = NS_STANZAS + " service-unavailable"
STREAM_CONNECTION_TIMEOUT		 = NS_XMPP_STREAMS + " connection-timeout"
STREAM_UNSUPPORTED_VERSION		 = NS_XMPP_STREAMS + " unsupported-version"
STREAM_IMPROPER_ADDRESSING		 = NS_XMPP_STREAMS + " improper-addressing"
STREAM_UNDEFINED_CONDITION		 = NS_XMPP_STREAMS + " undefined-condition"
SASL_NOT_AUTHORIZED				 = NS_SASL + " not-authorized"
ERR_GONE						 = NS_STANZAS + " gone"
SASL_TEMPORARY_AUTH_FAILURE		 = NS_SASL + " temporary-auth-failure"
ERR_REMOTE_SERVER_NOT_FOUND		 = NS_STANZAS + " remote-server-not-found"
ERR_UNEXPECTED_REQUEST			 = NS_STANZAS + " unexpected-request"
ERR_RECIPIENT_UNAVAILABLE		 = NS_STANZAS + " recipient-unavailable"
ERR_CONFLICT					 = NS_STANZAS + " conflict"
STREAM_SYSTEM_SHUTDOWN			 = NS_XMPP_STREAMS + " system-shutdown"
STREAM_BAD_FORMAT				 = NS_XMPP_STREAMS + " bad-format"
ERR_SUBSCRIPTION_REQUIRED		 = NS_STANZAS + " subscription-required"
STREAM_INTERNAL_SERVER_ERROR	 = NS_XMPP_STREAMS + " internal-server-error"
ERR_NOT_AUTHORIZED				 = NS_STANZAS + " not-authorized"
SASL_ABORTED					 = NS_SASL + " aborted"
ERR_REGISTRATION_REQUIRED		 = NS_STANZAS + " registration-required"
ERR_INTERNAL_SERVER_ERROR		 = NS_STANZAS + " internal-server-error"
SASL_INCORRECT_ENCODING			 = NS_SASL + " incorrect-encoding"
STREAM_HOST_GONE				 = NS_XMPP_STREAMS + " host-gone"
STREAM_POLICY_VIOLATION			 = NS_XMPP_STREAMS + " policy-violation"
STREAM_INVALID_XML				 = NS_XMPP_STREAMS + " invalid-xml"
STREAM_CONFLICT					 = NS_XMPP_STREAMS + " conflict"
STREAM_RESOURCE_CONSTRAINT		 = NS_XMPP_STREAMS + " resource-constraint"
STREAM_UNSUPPORTED_ENCODING		 = NS_XMPP_STREAMS + " unsupported-encoding"
ERR_NOT_ALLOWED					 = NS_STANZAS + " not-allowed"
ERR_ITEM_NOT_FOUND				 = NS_STANZAS + " item-not-found"
ERR_NOT_ACCEPTABLE				 = NS_STANZAS + " not-acceptable"
STREAM_INVALID_FROM				 = NS_XMPP_STREAMS + " invalid-from"
ERR_FEATURE_NOT_IMPLEMENTED		 = NS_STANZAS + " feature-not-implemented"
ERR_BAD_REQUEST					 = NS_STANZAS + " bad-request"
STREAM_INVALID_ID				 = NS_XMPP_STREAMS + " invalid-id"
STREAM_HOST_UNKNOWN				 = NS_XMPP_STREAMS + " host-unknown"
ERR_UNDEFINED_CONDITION			 = NS_STANZAS + " undefined-condition"
SASL_INVALID_MECHANISM			 = NS_SASL + " invalid-mechanism"
STREAM_RESTRICTED_XML			 = NS_XMPP_STREAMS + " restricted-xml"
ERR_RESOURCE_CONSTRAINT			 = NS_STANZAS + " resource-constraint"
ERR_REMOTE_SERVER_TIMEOUT		 = NS_STANZAS + " remote-server-timeout"
SASL_INVALID_AUTHZID			 = NS_SASL + " invalid-authzid"
ERR_PAYMENT_REQUIRED			 = NS_STANZAS + " payment-required"
STREAM_INVALID_NAMESPACE		 = NS_XMPP_STREAMS + " invalid-namespace"
ERR_REDIRECT					 = NS_STANZAS + " redirect"
STREAM_UNSUPPORTED_STANZA_TYPE	 = NS_XMPP_STREAMS + " unsupported-stanza-type"
ERR_FORBIDDEN					 = NS_STANZAS + " forbidden"

ERRORS = {
	"urn:ietf:params:xml:ns:xmpp-sasl not-authorized": ["", "", "The authentication failed because the initiating entity did not provide valid credentials (this includes but is not limited to the case of an unknown username); sent in reply to a <response/> element or an <auth/> element with initial response data."],
	"urn:ietf:params:xml:ns:xmpp-stanzas payment-required": ["402", "auth", "The requesting entity is not authorized to access the requested service because payment is required."],
	"urn:ietf:params:xml:ns:xmpp-sasl mechanism-too-weak": ["", "", "The mechanism requested by the initiating entity is weaker than server policy permits for that initiating entity; sent in reply to a <response/> element or an <auth/> element with initial response data."],
	"urn:ietf:params:xml:ns:xmpp-streams unsupported-encoding": ["", "", "The initiating entity has encoded the stream in an encoding that is not supported by the server."],
	"urn:ietf:params:xml:ns:xmpp-stanzas remote-server-timeout": ["504", "wait", "A remote server or service specified as part or all of the JID of the intended recipient could not be contacted within a reasonable amount of time."],
	"urn:ietf:params:xml:ns:xmpp-streams remote-connection-failed": ["", "", "The server is unable to properly connect to a remote resource that is required for authentication or authorization."],
	"urn:ietf:params:xml:ns:xmpp-streams restricted-xml": ["", "", "The entity has attempted to send restricted XML features such as a comment, processing instruction, DTD, entity reference, or unescaped character."],
	"urn:ietf:params:xml:ns:xmpp-streams see-other-host": ["", "", "The server will not provide service to the initiating entity but is redirecting traffic to another host."],
	"urn:ietf:params:xml:ns:xmpp-streams xml-not-well-formed": ["", "", "The initiating entity has sent XML that is not well-formed."],
	"urn:ietf:params:xml:ns:xmpp-stanzas subscription-required": ["407", "auth", "The requesting entity is not authorized to access the requested service because a subscription is required."],
	"urn:ietf:params:xml:ns:xmpp-streams internal-server-error": ["", "", "The server has experienced a misconfiguration or an otherwise-undefined internal error that prevents it from servicing the stream."],
	"urn:ietf:params:xml:ns:xmpp-sasl invalid-mechanism": ["", "", "The initiating entity did not provide a mechanism or requested a mechanism that is not supported by the receiving entity; sent in reply to an <auth/> element."],
	"urn:ietf:params:xml:ns:xmpp-streams policy-violation": ["", "", "The entity has violated some local service policy."],
	"urn:ietf:params:xml:ns:xmpp-stanzas conflict": ["409", "cancel", "Access cannot be granted because an existing resource or session exists with the same name or address."],
	"urn:ietf:params:xml:ns:xmpp-streams unsupported-stanza-type": ["", "", "The initiating entity has sent a first-level child of the stream that is not supported by the server."],
	"urn:ietf:params:xml:ns:xmpp-sasl incorrect-encoding": ["", "", "The data provided by the initiating entity could not be processed because the [BASE64]Josefsson, S., The Base16, Base32, and Base64 Data Encodings, July 2003. encoding is incorrect (e.g., because the encoding does not adhere to the definition in Section 3 of [BASE64]Josefsson, S., The Base16, Base32, and Base64 Data Encodings, July 2003.); sent in reply to a <response/> element or an <auth/> element with initial response data."],
	"urn:ietf:params:xml:ns:xmpp-stanzas registration-required": ["407", "auth", "The requesting entity is not authorized to access the requested service because registration is required."],
	"urn:ietf:params:xml:ns:xmpp-streams invalid-id": ["", "", "The stream ID or dialback ID is invalid or does not match an ID previously provided."],
	"urn:ietf:params:xml:ns:xmpp-sasl invalid-authzid": ["", "", "The authzid provided by the initiating entity is invalid, either because it is incorrectly formatted or because the initiating entity does not have permissions to authorize that ID; sent in reply to a <response/> element or an <auth/> element with initial response data."],
	"urn:ietf:params:xml:ns:xmpp-stanzas bad-request": ["400", "modify", "The sender has sent XML that is malformed or that cannot be processed."],
	"urn:ietf:params:xml:ns:xmpp-streams not-authorized": ["", "", "The entity has attempted to send data before the stream has been authenticated, or otherwise is not authorized to perform an action related to stream negotiation."],
	"urn:ietf:params:xml:ns:xmpp-stanzas forbidden": ["403", "auth", "The requesting entity does not possess the required permissions to perform the action."],
	"urn:ietf:params:xml:ns:xmpp-sasl temporary-auth-failure": ["", "", "The authentication failed because of a temporary error condition within the receiving entity; sent in reply to an <auth/> element or <response/> element."],
	"urn:ietf:params:xml:ns:xmpp-streams invalid-namespace": ["", "", "The streams namespace name is something other than \http://etherx.jabber.org/streams\" or the dialback namespace name is something other than \"jabber:server:dialback\"."],
	"urn:ietf:params:xml:ns:xmpp-stanzas feature-not-implemented": ["501", "cancel", "The feature requested is not implemented by the recipient or server and therefore cannot be processed."],
	"urn:ietf:params:xml:ns:xmpp-streams invalid-xml": ["", "", "The entity has sent invalid XML over the stream to a server that performs validation."],
	"urn:ietf:params:xml:ns:xmpp-stanzas item-not-found": ["404", "cancel", "The addressed JID or item requested cannot be found."],
	"urn:ietf:params:xml:ns:xmpp-streams host-gone": ["", "", "The value of the \"to\" attribute provided by the initiating entity in the stream header corresponds to a hostname that is no longer hosted by the server."],
	"urn:ietf:params:xml:ns:xmpp-stanzas recipient-unavailable": ["404", "wait", "The intended recipient is temporarily unavailable."],
	"urn:ietf:params:xml:ns:xmpp-stanzas not-acceptable": ["406", "cancel", "The recipient or server understands the request but is refusing to process it because it does not meet criteria defined by the recipient or server."],
	"urn:ietf:params:xml:ns:xmpp-streams invalid-from": ["cancel", "", "The JID or hostname provided in a \"from\" address does not match an authorized JID or validated domain negotiated between servers via SASL or dialback, or between a client and a server via authentication and resource authorization."],
	"urn:ietf:params:xml:ns:xmpp-streams bad-format": ["", "", "The entity has sent XML that cannot be processed."],
	"urn:ietf:params:xml:ns:xmpp-streams resource-constraint": ["", "", "The server lacks the system resources necessary to service the stream."],
	"urn:ietf:params:xml:ns:xmpp-stanzas undefined-condition": ["500", "", "The condition is undefined."],
	"urn:ietf:params:xml:ns:xmpp-stanzas redirect": ["302", "modify", "The recipient or server is redirecting requests for this information to another entity."],
	"urn:ietf:params:xml:ns:xmpp-streams bad-namespace-prefix": ["", "", "The entity has sent a namespace prefix that is unsupported, or has sent no namespace prefix on an element that requires such a prefix."],
	"urn:ietf:params:xml:ns:xmpp-streams system-shutdown": ["", "", "The server is being shut down and all active streams are being closed."],
	"urn:ietf:params:xml:ns:xmpp-streams conflict": ["", "", "The server is closing the active stream for this entity because a new stream has been initiated that conflicts with the existing stream."],
	"urn:ietf:params:xml:ns:xmpp-streams connection-timeout": ["", "", "The entity has not generated any traffic over the stream for some period of time."],
	"urn:ietf:params:xml:ns:xmpp-stanzas jid-malformed": ["400", "modify", "The value of the \"to\" attribute in the sender's stanza does not adhere to the syntax defined in Addressing Scheme."],
	"urn:ietf:params:xml:ns:xmpp-stanzas resource-constraint": ["500", "wait", "The server or recipient lacks the system resources necessary to service the request."],
	"urn:ietf:params:xml:ns:xmpp-stanzas remote-server-not-found": ["404", "cancel", "A remote server or service specified as part or all of the JID of the intended recipient does not exist."],
	"urn:ietf:params:xml:ns:xmpp-streams unsupported-version": ["", "", "The value of the \"version\" attribute provided by the initiating entity in the stream header specifies a version of XMPP that is not supported by the server."],
	"urn:ietf:params:xml:ns:xmpp-streams host-unknown": ["", "", "The value of the \"to\" attribute provided by the initiating entity in the stream header does not correspond to a hostname that is hosted by the server."],
	"urn:ietf:params:xml:ns:xmpp-stanzas unexpected-request": ["400", "wait", "The recipient or server understood the request but was not expecting it at this time (e.g., the request was out of order)."],
	"urn:ietf:params:xml:ns:xmpp-streams improper-addressing": ["", "", "A stanza sent between two servers lacks a \"to\" or \"from\" attribute (or the attribute has no value)."],
	"urn:ietf:params:xml:ns:xmpp-stanzas not-allowed": ["405", "cancel", "The recipient or server does not allow any entity to perform the action."],
	"urn:ietf:params:xml:ns:xmpp-stanzas internal-server-error": ["500", "wait", "The server could not process the stanza because of a misconfiguration or an otherwise-undefined internal server error."],
	"urn:ietf:params:xml:ns:xmpp-stanzas gone": ["302", "modify", "The recipient or server can no longer be contacted at this address."],
	"urn:ietf:params:xml:ns:xmpp-streams undefined-condition": ["", "", "The error condition is not one of those defined by the other conditions in this list."],
	"urn:ietf:params:xml:ns:xmpp-stanzas service-unavailable": ["503", "cancel", "The server or recipient does not currently provide the requested service."],
	"urn:ietf:params:xml:ns:xmpp-stanzas not-authorized": ["401", "auth", "The sender must provide proper credentials before being allowed to perform the action, or has provided improper credentials."],
	"urn:ietf:params:xml:ns:xmpp-sasl aborted": ["", "", "The receiving entity acknowledges an <abort/> element sent by the initiating entity; sent in reply to the <abort/> element."]
}

_errorcodes = {
	"302": "redirect",
	"400": "unexpected-request",
	"401": "not-authorized",
	"402": "payment-required",
	"403": "forbidden",
	"404": "remote-server-not-found",
	"405": "not-allowed",
	"406": "not-acceptable",
	"407": "subscription-required",
	"409": "conflict",
	"500": "undefined-condition",
	"501": "feature-not-implemented",
	"503": "service-unavailable",
	"504": "remote-server-timeout"
}

def isResultNode(node):
	"""
	Returns true if the node is a positive reply.
	"""
	return (node and node.getType() == "result")

def isGetNode(node):
	"""
	Returns true if the node is a positive reply.
	"""
	return (node and node.getType() == "get")

def isSetNode(node):
	"""
	Returns true if the node is a positive reply.
	"""
	return (node and node.getType() == "set")

def isErrorNode(node):
	"""
	Returns true if the node is a negative reply.
	"""
	return (node and node.getType() == "error")

class NodeProcessed(Exception):
	"""
	Exception that should be raised by handler when the handling should be stopped.
	"""

class StreamError(Exception):
	"""
	Base exception class for stream errors.
	"""

class BadFormat(StreamError): pass

class BadNamespacePrefix(StreamError): pass

class Conflict(StreamError): pass

class ConnectionTimeout(StreamError): pass

class HostGone(StreamError): pass

class HostUnknown(StreamError): pass

class ImproperAddressing(StreamError): pass

class InternalServerError(StreamError): pass

class InvalidFrom(StreamError): pass

class InvalidID(StreamError): pass

class InvalidNamespace(StreamError): pass

class InvalidXML(StreamError): pass

class NotAuthorized(StreamError): pass

class PolicyViolation(StreamError): pass

class RemoteConnectionFailed(StreamError): pass

class ResourceConstraint(StreamError): pass

class RestrictedXML(StreamError): pass

class SeeOtherHost(StreamError): pass

class SystemShutdown(StreamError): pass

class UndefinedCondition(StreamError): pass

class UnsupportedEncoding(StreamError): pass

class UnsupportedStanzaType(StreamError): pass

class UnsupportedVersion(StreamError): pass

class XMLNotWellFormed(StreamError): pass

stream_exceptions = {
	"bad-format": BadFormat,
	"bad-namespace-prefix": BadNamespacePrefix,
	"conflict": Conflict,
	"connection-timeout": ConnectionTimeout,
	"host-gone": HostGone,
	"host-unknown": HostUnknown,
	"improper-addressing": ImproperAddressing,
	"internal-server-error": InternalServerError,
	"invalid-from": InvalidFrom,
	"invalid-id": InvalidID,
	"invalid-namespace": InvalidNamespace,
	"invalid-xml": InvalidXML,
	"not-authorized": NotAuthorized,
	"policy-violation": PolicyViolation,
	"remote-connection-failed": RemoteConnectionFailed,
	"resource-constraint": ResourceConstraint,
	"restricted-xml": RestrictedXML,
	"see-other-host": SeeOtherHost,
	"system-shutdown": SystemShutdown,
	"undefined-condition": UndefinedCondition,
	"unsupported-encoding": UnsupportedEncoding,
	"unsupported-stanza-type": UnsupportedStanzaType,
	"unsupported-version": UnsupportedVersion,
	"xml-not-well-formed": XMLNotWellFormed
}

class JID:
	"""
	JID object. JID can be built from string, modified, compared, serialized into string.
	"""
	def __init__(self, jid=None, node="", domain="", resource=""):
		"""
		Constructor. JID can be specified as string (jid argument) or as separate parts.
		Examples:
		JID("node@domain/resource")
		JID(node="node", domain="domain.org")
		"""
		if not jid and not domain:
			raise ValueError("JID must contain at least domain name")
		elif isinstance(jid, self.__class__):
			self.node, self.domain, self.resource = jid.node, jid.domain, jid.resource
		elif domain:
			self.node, self.domain, self.resource = node, domain, resource
		else:
			if jid.find("@") + 1:
				self.node, jid = jid.split("@", 1)
			else:
				self.node = ""
			if jid.find("/") + 1:
				self.domain, self.resource = jid.split("/", 1)
			else:
				self.domain, self.resource = jid, ""

	def getNode(self):
		"""
		Return the node part of the JID.
		"""
		return self.node

	def setNode(self, node):
		"""
		Set the node part of the JID to new value. Specify None to remove the node part.
		"""
		self.node = node.lower()

	def getDomain(self):
		"""
		Return the domain part of the JID.
		"""
		return self.domain

	def setDomain(self, domain):
		"""
		Set the domain part of the JID to new value.
		"""
		self.domain = domain.lower()

	def getResource(self):
		"""
		Return the resource part of the JID.
		"""
		return self.resource

	def setResource(self, resource):
		"""
		Set the resource part of the JID to new value. Specify None to remove the resource part.
		"""
		self.resource = resource

	def getStripped(self):
		"""
		Return the bare representation of JID. I.e. string value w/o resource.
		"""
		return self.__str__(0)

	def __eq__(self, other):
		"""
		Compare the JID to another instance or to string for equality.
		"""
		try:
			other = JID(other)
		except ValueError:
			return False
		return self.resource == other.resource and self.__str__(0) == other.__str__(0)

	def __ne__(self, other):
		"""
		Compare the JID to another instance or to string for non-equality.
		"""
		return not self.__eq__(other)

	def bareMatch(self, other):
		"""
		Compare the node and domain parts of the JID's for equality.
		"""
		return self.__str__(0) == JID(other).__str__(0)

	def __str__(self, wresource=1):
		"""
		Serialize JID into string.
		"""
		jid = "@".join((self.node, self.domain)) if self.node else self.domain
		if wresource and self.resource:
			jid = "/".join((jid, self.resource))
		return jid

	def __hash__(self):
		"""
		Produce hash of the JID, Allows to use JID objects as keys of the dictionary.
		"""
		return hash(self.__str__())

class Protocol(Node):
	"""
	A "stanza" object class. Contains methods that are common for presences, iqs and messages.
	"""
	def __init__(self, name=None, to=None, typ=None, frm=None, attrs={}, payload=[], timestamp=None, xmlns=None, node=None):
		"""
		Constructor, name is the name of the stanza i.e. "message" or "presence" or "iq".
		to is the value of "to" attribure, "typ" - "type" attribute
		frn - from attribure, attrs - other attributes mapping, payload - same meaning as for simplexml payload definition
		timestamp - the time value that needs to be stamped over stanza
		xmlns - namespace of top stanza node
		node - parsed or unparsed stana to be taken as prototype.
		"""
		if not attrs:
			attrs = {}
		if to:
			attrs["to"] = to
		if frm:
			attrs["from"] = frm
		if typ:
			attrs["type"] = typ
		Node.__init__(self, tag=name, attrs=attrs, payload=payload, node=node)
		if not node and xmlns:
			self.setNamespace(xmlns)
		if self["to"]:
			self.setTo(self["to"])
		if self["from"]:
			self.setFrom(self["from"])
		if node and isinstance(node, self.__class__) and self.__class__ == node.__class__ and "id" in self.attrs:
			del self.attrs["id"]
		self.timestamp = None
		for x in self.getTags("x", namespace=NS_DELAY):
			try:
				if not self.getTimestamp() or x.getAttr("stamp") < self.getTimestamp():
					self.setTimestamp(x.getAttr("stamp"))
			except Exception:
				pass
		if timestamp is not None:
			self.setTimestamp(timestamp) # To auto-timestamp stanza just pass timestamp=""

	def getTo(self):
		"""
		Return value of the "to" attribute.
		"""
		try:
			to = self["to"]
		except Exception:
			to = None
		return to

	def getFrom(self):
		"""
		Return value of the "from" attribute.
		"""
		try:
			frm = self["from"]
		except Exception:
			frm = None
		return frm

	def getTimestamp(self):
		"""
		Return the timestamp in the "yyyymmddThhmmss" format.
		"""
		return self.timestamp

	def getID(self):
		"""
		Return the value of the "id" attribute.
		"""
		return self.getAttr("id")

	def setTo(self, val):
		"""
		Set the value of the "to" attribute.
		"""
		self.setAttr("to", JID(val))

	def getType(self):
		"""
		Return the value of the "type" attribute.
		"""
		return self.getAttr("type")

	def setFrom(self, val):
		"""
		Set the value of the "from" attribute.
		"""
		self.setAttr("from", JID(val))

	def setType(self, val):
		"""
		Set the value of the "type" attribute.
		"""
		self.setAttr("type", val)

	def setID(self, val):
		"""
		Set the value of the "id" attribute.
		"""
		self.setAttr("id", val)

	def getError(self):
		"""
		Return the error-condition (if present) or the textual description of the error (otherwise).
		"""
		errtag = self.getTag("error")
		if errtag:
			for tag in errtag.getChildren():
				if tag.getName() != "text":
					return tag.getName()
			return errtag.getData()

	def getErrorCode(self):
		"""
		Return the error code. Obsolette.
		"""
		return self.getTagAttr("error", "code")

	def setError(self, error, code=None):
		"""
		Set the error code. Obsolette. Use error-conditions instead.
		"""
		if code:
			if str(code) in _errorcodes.keys():
				error = ErrorNode(_errorcodes[str(code)], text=error)
			else:
				error = ErrorNode(ERR_UNDEFINED_CONDITION, code=code, typ="cancel", text=error)
		elif isinstance(error, basestring):
			error = ErrorNode(error)
		self.setType("error")
		self.addChild(node=error)

	def setTimestamp(self, val=None):
		"""
		Set the timestamp. timestamp should be the yyyymmddThhmmss string.
		"""
		if not val:
			val = time.strftime("%Y%m%dT%H:%M:%S", time.gmtime())
		self.timestamp = val
		self.setTag("x", {"stamp": self.timestamp}, namespace=NS_DELAY)

	def getProperties(self):
		"""
		Return the list of namespaces to which belongs the direct childs of element.
		"""
		props = []
		for child in self.getChildren():
			prop = child.getNamespace()
			if prop not in props:
				props.append(prop)
		return props

	def __setitem__(self, item, val):
		"""
		Set the item "item" to the value "val".
		"""
		if item in ["to", "from"]:
			val = JID(val)
		return self.setAttr(item, val)

class Message(Protocol):
	"""
	XMPP Message stanza - "push" mechanism.
	"""
	def __init__(self, to=None, body=None, typ=None, subject=None, attrs={}, frm=None, payload=[], timestamp=None, xmlns=NS_CLIENT, node=None):
		"""
		Create message object. You can specify recipient, text of message, type of message
		any additional attributes, sender of the message, any additional payload (f.e. jabber:x:delay element) and namespace in one go.
		Alternatively you can pass in the other XML object as the "node" parameted to replicate it as message.
		"""
		Protocol.__init__(self, "message", to=to, typ=typ, attrs=attrs, frm=frm, payload=payload, timestamp=timestamp, xmlns=xmlns, node=node)
		if body:
			self.setBody(body)
		if subject:
			self.setSubject(subject)

	def getBody(self):
		"""
		Returns text of the message.
		"""
		return self.getTagData("body")

	def getSubject(self):
		"""
		Returns subject of the message.
		"""
		return self.getTagData("subject")

	def getThread(self):
		"""
		Returns thread of the message.
		"""
		return self.getTagData("thread")

	def setBody(self, val):
		"""
		Sets the text of the message.
		"""
		self.setTagData("body", val)

	def setSubject(self, val):
		"""
		Sets the subject of the message.
		"""
		self.setTagData("subject", val)

	def setThread(self, val):
		"""
		Sets the thread of the message.
		"""
		self.setTagData("thread", val)

	def buildReply(self, text=None):
		"""
		Builds and returns another message object with specified text.
		The to, from type and thread properties of new message are pre-set as reply to this message.
		"""
		msg = Message(to=self.getFrom(), frm=self.getTo(), body=text)
		thr = self.getThread()
		if thr:
			msg.setThread(thr)
		return msg

class Presence(Protocol):
	"""
	XMPP Presence object.
	"""
	def __init__(self, to=None, typ=None, priority=None, show=None, status=None, attrs={}, frm=None, timestamp=None, payload=[], xmlns=NS_CLIENT, node=None):
		"""
		Create presence object. You can specify recipient, type of message, priority, show and status values
		any additional attributes, sender of the presence, timestamp, any additional payload (f.e. jabber:x:delay element) and namespace in one go.
		Alternatively you can pass in the other XML object as the "node" parameted to replicate it as presence.
		"""
		Protocol.__init__(self, "presence", to=to, typ=typ, attrs=attrs, frm=frm, payload=payload, timestamp=timestamp, xmlns=xmlns, node=node)
		if priority:
			self.setPriority(priority)
		if show:
			self.setShow(show)
		if status:
			self.setStatus(status)

	def getPriority(self):
		"""
		Returns the priority of the message.
		"""
		return self.getTagData("priority")

	def getShow(self):
		"""
		Returns the show value of the message.
		"""
		return self.getTagData("show")

	def getStatus(self):
		"""
		Returns the status string of the message.
		"""
		return self.getTagData("status")

	def setPriority(self, val):
		"""
		Sets the priority of the message.
		"""
		self.setTagData("priority", val)

	def setShow(self, val):
		"""
		Sets the show value of the message.
		"""
		self.setTagData("show", val)

	def setStatus(self, val):
		"""
		Sets the status string of the message.
		"""
		self.setTagData("status", val)

	def _muc_getItemAttr(self, tag, attr):
		for xtag in self.getTags("x", namespace=NS_MUC_USER):
			for child in xtag.getTags(tag):
				return child.getAttr(attr)

	def _muc_getSubTagDataAttr(self, tag, attr):
		for xtag in self.getTags("x", namespace=NS_MUC_USER):
			for child in xtag.getTags("item"):
				for cchild in child.getTags(tag):
					return cchild.getData(), cchild.getAttr(attr)
		return None, None

	def getRole(self):
		"""
		Returns the presence role (for groupchat).
		"""
		return self._muc_getItemAttr("item", "role")

	def getAffiliation(self):
		"""Returns the presence affiliation (for groupchat).
		"""
		return self._muc_getItemAttr("item", "affiliation")

	def getNick(self):
		"""
		Returns the nick value (for nick change in groupchat).
		"""
		return self._muc_getItemAttr("item", "nick")

	def getJid(self):
		"""
		Returns the presence jid (for groupchat).
		"""
		return self._muc_getItemAttr("item", "jid")

	def getReason(self):
		"""
		Returns the reason of the presence (for groupchat).
		"""
		return self._muc_getSubTagDataAttr("reason", "")[0]

	def getActor(self):
		"""
		Returns the reason of the presence (for groupchat).
		"""
		return self._muc_getSubTagDataAttr("actor", "jid")[1]

	def getStatusCode(self):
		"""
		Returns the status code of the presence (for groupchat).
		"""
		return self._muc_getItemAttr("status", "code")

class Iq(Protocol):
	"""
	XMPP Iq object - get/set dialog mechanism.
	"""
	def __init__(self, typ=None, queryNS=None, attrs={}, to=None, frm=None, payload=[], xmlns=NS_CLIENT, node=None):
		"""
		Create Iq object. You can specify type, query namespace
		any additional attributes, recipient of the iq, sender of the iq, any additional payload (f.e. jabber:x:data node) and namespace in one go.
		Alternatively you can pass in the other XML object as the "node" parameted to replicate it as an iq.
		"""
		Protocol.__init__(self, "iq", to=to, typ=typ, attrs=attrs, frm=frm, xmlns=xmlns, node=node)
		if payload:
			self.setQueryPayload(payload)
		if queryNS:
			self.setQueryNS(queryNS)

	def getQuery(self):
		"""
		Returns the query node.
		"""
		return self.getTag("query")

	def getQueryNS(self):
		"""
		Returns the namespace of the "query" child element.
		"""
		tag = self.getTag("query")
		if tag:
			return tag.getNamespace()

	def getQuerynode(self):
		"""
		Returns the "node" attribute value of the "query" child element.
		"""
		return self.getTagAttr("query", "node")

	def getQueryPayload(self):
		"""
		Returns the "query" child element payload.
		"""
		tag = self.getTag("query")
		if tag:
			return tag.getPayload()

	def getQueryChildren(self):
		"""
		Returns the "query" child element child nodes.
		"""
		tag = self.getTag("query")
		if tag:
			return tag.getChildren()

	def setQuery(self, name=None):
		"""
		Changes the name of the query node, creates it if needed.
		Keep the existing name if none is given (use "query" if it's a creation).
		Returns the query node.
		"""
		query = self.getQuery()
		if query is None:
			query = self.addChild("query")
		if name is not None:
			query.setName(name)
		return query

	def setQueryNS(self, namespace):
		"""
		Set the namespace of the "query" child element.
		"""
		self.setTag("query").setNamespace(namespace)

	def setQueryPayload(self, payload):
		"""
		Set the "query" child element payload.
		"""
		self.setTag("query").setPayload(payload)

	def setQuerynode(self, node):
		"""
		Set the "node" attribute value of the "query" child element.
		"""
		self.setTagAttr("query", "node", node)

	def buildReply(self, typ):
		"""
		Builds and returns another Iq object of specified type.
		The to, from and query child node of new Iq are pre-set as reply to this Iq.
		"""
		iq = Iq(typ, to=self.getFrom(), frm=self.getTo(), attrs={"id": self.getID()})
		if self.getTag("query"):
			iq.setQueryNS(self.getQueryNS())
		return iq

class ErrorNode(Node):
	"""
	XMPP-style error element.
	In the case of stanza error should be attached to XMPP stanza.
	In the case of stream-level errors should be used separately.
	"""
	def __init__(self, name, code=None, typ=None, text=None):
		"""
		Create new error node object.
		Mandatory parameter: name - name of error condition.
		Optional parameters: code, typ, text. Used for backwards compartibility with older jabber protocol.
		"""
		if name in ERRORS:
			cod, type, txt = ERRORS[name]
			ns = name.split()[0]
		else:
			cod, ns, type, txt = "500", NS_STANZAS, "cancel", ""
		if typ:
			type = typ
		if code:
			cod = code
		if text:
			txt = text
		Node.__init__(self, "error", {}, [Node(name)])
		if type:
			self.setAttr("type", type)
		if not cod:
			self.setName("stream:error")
		if txt:
			self.addChild(node=Node(ns + " text", {}, [txt]))
		if cod:
			self.setAttr("code", cod)

class Error(Protocol):
	"""
	Used to quickly transform received stanza into error reply.
	"""
	def __init__(self, node, error, reply=1):
		"""
		Create error reply basing on the received "node" stanza and the "error" error condition.
		If the "node" is not the received stanza but locally created ("to" and "from" fields needs not swapping)
		specify the "reply" argument as false.
		"""
		if reply:
			Protocol.__init__(self, to=node.getFrom(), frm=node.getTo(), node=node)
		else:
			Protocol.__init__(self, node=node)
		self.setError(error)
		if node.getType() == "error":
			self.__str__ = self.__dupstr__

	def __dupstr__(self, dup1=None, dup2=None):
		"""
		Dummy function used as preventor of creating error node in reply to error node.
		I.e. you will not be able to serialize "double" error into string.
		"""
		return ""

class DataField(Node):
	"""
	This class is used in the DataForm class to describe the single data item.
	If you are working with jabber:x:data (XEP-0004, XEP-0068, XEP-0122)
	then you will need to work with instances of this class.
	"""
	def __init__(self, name=None, value=None, typ=None, required=0, label=None, desc=None, options=[], node=None):
		"""
		Create new data field of specified name,value and type. Also "required", "desc" and "options" fields can be set.
		Alternatively other XML object can be passed in as the "node" parameted to replicate it as a new datafiled.
		"""
		Node.__init__(self, "field", node=node)
		if name:
			self.setVar(name)
		if isinstance(value, (list, tuple)):
			self.setValues(value)
		elif value:
			self.setValue(value)
		if typ:
			self.setType(typ)
#		elif not typ and not node:
#			self.setType("text-single")
		if required:
			self.setRequired(required)
		if label:
			self.setLabel(label)
		if desc:
			self.setDesc(desc)
		if options:
			self.setOptions(options)

	def setRequired(self, req=1):
		"""
		Change the state of the "required" flag.
		"""
		if req:
			self.setTag("required")
		else:
			try:
				self.delChild("required")
			except ValueError:
				return None

	def isRequired(self):
		"""
		Returns in this field a required one.
		"""
		return self.getTag("required")

	def setLabel(self, label):
		"""
		Set the label of this field.
		"""
		self.setAttr("label", label)

	def getLabel(self):
		"""
		Return the label of this field.
		"""
		return self.getAttr("label")

	def setDesc(self, desc):
		"""
		Set the description of this field.
		"""
		self.setTagData("desc", desc)

	def getDesc(self):
		"""
		Return the description of this field.
		"""
		return self.getTagData("desc")

	def setValue(self, val):
		"""
		Set the value of this field.
		"""
		self.setTagData("value", val)

	def getValue(self):
		return self.getTagData("value")

	def setValues(self, ls):
		"""
		Set the values of this field as values-list.
		Replaces all previous filed values! If you need to just add a value - use addValue method.
		"""
		while self.getTag("value"):
			self.delChild("value")
		for val in ls:
			self.addValue(val)

	def addValue(self, val):
		"""
		Add one more value to this field. Used in "get" iq's or such.
		"""
		self.addChild("value", {}, [val])

	def getValues(self):
		"""
		Return the list of values associated with this field.
		"""
		ret = []
		for tag in self.getTags("value"):
			ret.append(tag.getData())
		return ret

	def getOptions(self):
		"""
		Return label-option pairs list associated with this field.
		"""
		ret = []
		for tag in self.getTags("option"):
			ret.append([tag.getAttr("label"), tag.getTagData("value")])
		return ret

	def setOptions(self, ls):
		"""
		Set label-option pairs list associated with this field.
		"""
		while self.getTag("option"):
			self.delChild("option")
		for opt in ls:
			self.addOption(opt)

	def addOption(self, opt):
		"""
		Add one more label-option pair to this field.
		"""
		if isinstance(opt, basestring):
			self.addChild("option").setTagData("value", opt)
		else:
			self.addChild("option", {"label": opt[0]}).setTagData("value", opt[1])

	def getType(self):
		"""
		Get type of this field.
		"""
		return self.getAttr("type")

	def setType(self, val):
		"""
		Set type of this field.
		"""
		return self.setAttr("type", val)

	def getVar(self):
		"""
		Get "var" attribute value of this field.
		"""
		return self.getAttr("var")

	def setVar(self, val):
		"""
		Set "var" attribute value of this field.
		"""
		return self.setAttr("var", val)

class DataReported(Node):
	"""
	This class is used in the DataForm class to describe the "reported data field" data items which are used in
	"multiple item form results" (as described in XEP-0004).
	Represents the fields that will be returned from a search. This information is useful when
	you try to use the jabber:iq:search namespace to return dynamic form information.
	"""
	def __init__(self, node=None):
		"""
		Create new empty "reported data" field. However, note that, according XEP-0004:
		* It MUST contain one or more DataFields.
		* Contained DataFields SHOULD possess a "type" and "label" attribute in addition to "var" attribute
		* Contained DataFields SHOULD NOT contain a <value/> element.
		Alternatively other XML object can be passed in as the "node" parameted to replicate it as a new
		dataitem.
		"""
		Node.__init__(self, "reported", node=node)
		if node:
			newkids = []
			for n in self.getChildren():
				if n.getName() == "field":
					newkids.append(DataField(node=n))
				else:
					newkids.append(n)
			self.kids = newkids

	def getField(self, name):
		"""
		Return the datafield object with name "name" (if exists).
		"""
		return self.getTag("field", attrs={"var": name})

	def setField(self, name, typ=None, label=None):
		"""
		Create if nessessary or get the existing datafield object with name "name" and return it.
		If created, attributes "type" and "label" are applied to new datafield.
		"""
		field = self.getField(name)
		if not field:
			field = self.addChild(node=DataField(name, None, typ, 0, label))
		return field

	def asDict(self):
		"""
		Represent dataitem as simple dictionary mapping of datafield names to their values.
		"""
		ret = {}
		for field in self.getTags("field"):
			name = field.getAttr("var")
			typ = field.getType()
			if isinstance(typ, basestring) and typ.endswith("-multi"):
				val = []
				for i in field.getTags("value"):
					val.append(i.getData())
			else:
				val = field.getTagData("value")
			ret[name] = val
		if self.getTag("instructions"):
			ret["instructions"] = self.getInstructions()
		return ret

	def __getitem__(self, name):
		"""
		Simple dictionary interface for getting datafields values by their names.
		"""
		item = self.getField(name)
		if item:
			return item.getValue()
		raise IndexError("No such field")

	def __setitem__(self, name, val):
		"""
		Simple dictionary interface for setting datafields values by their names.
		"""
		return self.setField(name).setValue(val)

class DataItem(Node):
	"""
	This class is used in the DataForm class to describe data items which are used in "multiple
	item form results" (as described in XEP-0004).
	"""
	def __init__(self, node=None):
		"""
		Create new empty data item. However, note that, according XEP-0004, DataItem MUST contain ALL
		DataFields described in DataReported.
		Alternatively other XML object can be passed in as the "node" parameted to replicate it as a new
		dataitem.
		"""
		Node.__init__(self, "item", node=node)
		if node:
			newkids = []
			for n in self.getChildren():
				if n.getName() == "field":
					newkids.append(DataField(node=n))
				else:
					newkids.append(n)
			self.kids = newkids

	def getField(self, name):
		"""
		Return the datafield object with name "name" (if exists).
		"""
		return self.getTag("field", attrs={"var": name})

	def setField(self, name, value=None, typ=None):
		"""
		Create if nessessary or get the existing datafield object with name "name" and return it.
		"""
		field = self.getField(name)
		if not field:
			field = self.addChild(node=DataField(name, value, typ))
		return field

	def asDict(self):
		"""
		Represent dataitem as simple dictionary mapping of datafield names to their values.
		"""
		ret = {}
		for field in self.getTags("field"):
			name = field.getAttr("var")
			typ = field.getType()
			if isinstance(typ, basestring) and typ.endswith("-multi"):
				val = []
				for i in field.getTags("value"):
					val.append(i.getData())
			else:
				val = field.getTagData("value")
			ret[name] = val
		if self.getTag("instructions"):
			ret["instructions"] = self.getInstructions()
		return ret

	def __getitem__(self, name):
		"""
		Simple dictionary interface for getting datafields values by their names.
		"""
		item = self.getField(name)
		if item:
			return item.getValue()
		raise IndexError("No such field")

	def __setitem__(self, name, val):
		"""
		Simple dictionary interface for setting datafields values by their names.
		"""
		return self.setField(name).setValue(val)

class DataForm(Node):
	"""
	DataForm class. Used for manipulating dataforms in XMPP.
	Relevant XEPs: 0004, 0068, 0122.
	Can be used in disco, pub-sub and many other applications.
	"""
	def __init__(self, typ=None, data=[], title=None, node=None):
		"""
		Create new dataform of type "typ"; "data" is the list of DataReported,
		DataItem and DataField instances that this dataform contains; "title"
		is the title string.
		You can specify the "node" argument as the other node to be used as
		base for constructing this dataform.

		Title and instructions is optional and SHOULD NOT contain newlines.
		Several instructions MAY be present.
		"typ" can be one of ("form" | "submit" | "cancel" | "result" )
		"typ" of reply iq can be ( "result" | "set" | "set" | "result" ) respectively.
		"cancel" form can not contain any fields. All other forms contains AT LEAST one field.
		"title" MAY be included in forms of type "form" and "result".
		"""
		Node.__init__(self, "x", node=node)
		if node:
			newkids = []
			for n in self.getChildren():
				if n.getName() == "field":
					newkids.append(DataField(node=n))
				elif n.getName() == "item":
					newkids.append(DataItem(node=n))
				elif n.getName() == "reported":
					newkids.append(DataReported(node=n))
				else:
					newkids.append(n)
			self.kids = newkids
		if typ:
			self.setType(typ)
		self.setNamespace(NS_DATA)
		if title:
			self.setTitle(title)
		if isinstance(data, dict):
			newdata = []
			for name in data.keys():
				newdata.append(DataField(name, data[name]))
			data = newdata
		for child in data:
			if isinstance(child, basestring):
				self.addInstructions(child)
			elif isinstance(child, DataField):
				self.kids.append(child)
			elif isinstance(child, DataItem):
				self.kids.append(child)
			elif isinstance(child, DataReported):
				self.kids.append(child)
			else:
				self.kids.append(DataField(node=child))

	def getType(self):
		"""
		Return the type of dataform.
		"""
		return self.getAttr("type")

	def setType(self, typ):
		"""
		Set the type of dataform.
		"""
		self.setAttr("type", typ)

	def getTitle(self):
		"""
		Return the title of dataform.
		"""
		return self.getTagData("title")

	def setTitle(self, text):
		"""
		Set the title of dataform.
		"""
		self.setTagData("title", text)

	def getInstructions(self):
		"""
		Return the instructions of dataform.
		"""
		return self.getTagData("instructions")

	def setInstructions(self, text):
		"""
		Set the instructions of dataform.
		"""
		self.setTagData("instructions", text)

	def addInstructions(self, text):
		"""
		Add one more instruction to the dataform.
		"""
		self.addChild("instructions", {}, [text])

	def getField(self, name):
		"""
		Return the datafield object with name "name" (if exists).
		"""
		return self.getTag("field", attrs={"var": name})

	def setField(self, name, value=None, typ=None):
		"""
		Create if nessessary or get the existing datafield object with name "name" and return it.
		"""
		field = self.getField(name)
		if not field:
			field = self.addChild(node=DataField(name, value, typ))
		return field

	def asDict(self):
		"""
		Represent dataform as simple dictionary mapping of datafield names to their values.
		"""
		ret = {}
		for field in self.getTags("field"):
			name = field.getAttr("var")
			typ = field.getType()
			if isinstance(typ, basestring) and typ.endswith("-multi"):
				val = []
				for i in field.getTags("value"):
					val.append(i.getData())
			else:
				val = field.getTagData("value")
			ret[name] = val
		if self.getTag("instructions"):
			ret["instructions"] = self.getInstructions()
		return ret

	def __getitem__(self, name):
		"""
		Simple dictionary interface for getting datafields values by their names.
		"""
		item = self.getField(name)
		if item:
			return item.getValue()
		raise IndexError("No such field")

	def __setitem__(self, name, val):
		"""
		Simple dictionary interface for setting datafields values by their names.
		"""
		return self.setField(name).setValue(val)

########NEW FILE########
__FILENAME__ = roster
##   roster.py
##
##   Copyright (C) 2003-2005 Alexey "Snake" Nezhdanov
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

# $Id: roster.py, v1.21 2013/10/21 alkorgun Exp $

"""
Simple roster implementation. Can be used though for different tasks like
mass-renaming of contacts.
"""

from .plugin import PlugIn
from .protocol import *

class Roster(PlugIn):
	"""
	Defines a plenty of methods that will allow you to manage roster.
	Also automatically track presences from remote JIDs taking into
	account that every JID can have multiple resources connected. Does not
	currently support "error" presences.
	You can also use mapping interface for access to the internal representation of
	contacts in roster.
	"""
	def __init__(self):
		"""
		Init internal variables.
		"""
		PlugIn.__init__(self)
		self.DBG_LINE = "roster"
		self._data = {}
		self.set = None
		self._exported_methods = [self.getRoster]

	def plugin(self, owner, request=1):
		"""
		Register presence and subscription trackers in the owner's dispatcher.
		Also request roster from server if the "request" argument is set.
		Used internally.
		"""
		self._owner.RegisterHandler("iq", self.RosterIqHandler, "result", NS_ROSTER)
		self._owner.RegisterHandler("iq", self.RosterIqHandler, "set", NS_ROSTER)
		self._owner.RegisterHandler("presence", self.PresenceHandler)
		if request:
			self.Request()

	def Request(self, force=0):
		"""
		Request roster from server if it were not yet requested
		(or if the "force" argument is set).
		"""
		if self.set is None:
			self.set = 0
		elif not force:
			return None
		self._owner.send(Iq("get", NS_ROSTER))
		self.DEBUG("Roster requested from server", "start")

	def getRoster(self):
		"""
		Requests roster from server if neccessary and returns self.
		"""
		if not self.set:
			self.Request()
		while not self.set:
			self._owner.Process(10)
		return self

	def RosterIqHandler(self, dis, stanza):
		"""
		Subscription tracker. Used internally for setting items state in
		internal roster representation.
		"""
		for item in stanza.getTag("query").getTags("item"):
			jid = item.getAttr("jid")
			if item.getAttr("subscription") == "remove":
				if jid in self._data:
					del self._data[jid]
				raise NodeProcessed() # a MUST
			self.DEBUG("Setting roster item %s..." % jid, "ok")
			if jid not in self._data:
				self._data[jid] = {}
			self._data[jid]["name"] = item.getAttr("name")
			self._data[jid]["ask"] = item.getAttr("ask")
			self._data[jid]["subscription"] = item.getAttr("subscription")
			self._data[jid]["groups"] = []
			if "resources" not in self._data[jid]:
				self._data[jid]["resources"] = {}
			for group in item.getTags("group"):
				self._data[jid]["groups"].append(group.getData())
		self._data["@".join((self._owner.User, self._owner.Server))] = {"resources": {}, "name": None, "ask": None, "subscription": None, "groups": None, }
		self.set = 1
		raise NodeProcessed() # a MUST. Otherwise you'll get back an <iq type='error'/>

	def PresenceHandler(self, dis, pres):
		"""
		Presence tracker. Used internally for setting items' resources state in
		internal roster representation.
		"""
		jid = JID(pres.getFrom())
		if jid.getStripped() not in self._data:
			self._data[jid.getStripped()] = {"name": None, "ask": None, "subscription": "none", "groups": ["Not in roster"], "resources": {}}
		item = self._data[jid.getStripped()]
		typ = pres.getType()
		if not typ:
			self.DEBUG("Setting roster item %s for resource %s..." % (jid.getStripped(), jid.getResource()), "ok")
			item["resources"][jid.getResource()] = res = {"show": None, "status": None, "priority": "0", "timestamp": None}
			if pres.getTag("show"):
				res["show"] = pres.getShow()
			if pres.getTag("status"):
				res["status"] = pres.getStatus()
			if pres.getTag("priority"):
				res["priority"] = pres.getPriority()
			if not pres.getTimestamp():
				pres.setTimestamp()
			res["timestamp"] = pres.getTimestamp()
		elif typ == "unavailable" and jid.getResource() in item["resources"]:
			del item["resources"][jid.getResource()]
		# Need to handle type="error" also

	def _getItemData(self, jid, dataname):
		"""
		Return specific jid's representation in internal format. Used internally.
		"""
		jid = jid[:(jid + "/").find("/")]
		return self._data[jid][dataname]

	def _getResourceData(self, jid, dataname):
		"""
		Return specific jid's resource representation in internal format. Used internally.
		"""
		if jid.find("/") + 1:
			jid, resource = jid.split("/", 1)
			if resource in self._data[jid]["resources"]:
				return self._data[jid]["resources"][resource][dataname]
		elif self._data[jid]["resources"].keys():
			lastpri = -129
			for r in self._data[jid]["resources"].keys():
				if int(self._data[jid]["resources"][r]["priority"]) > lastpri:
					resource, lastpri = r, int(self._data[jid]["resources"][r]["priority"])
			return self._data[jid]["resources"][resource][dataname]

	def delItem(self, jid):
		"""
		Delete contact "jid" from roster.
		"""
		self._owner.send(Iq("set", NS_ROSTER, payload=[Node("item", {"jid": jid, "subscription": "remove"})]))

	def getAsk(self, jid):
		"""
		Returns "ask" value of contact "jid".
		"""
		return self._getItemData(jid, "ask")

	def getGroups(self, jid):
		"""
		Returns groups list that contact "jid" belongs to.
		"""
		return self._getItemData(jid, "groups")

	def getName(self, jid):
		"""
		Returns name of contact "jid".
		"""
		return self._getItemData(jid, "name")

	def getPriority(self, jid):
		"""
		Returns priority of contact "jid". "jid" should be a full (not bare) JID.
		"""
		return self._getResourceData(jid, "priority")

	def getRawRoster(self):
		"""
		Returns roster representation in internal format.
		"""
		return self._data

	def getRawItem(self, jid):
		"""
		Returns roster item "jid" representation in internal format.
		"""
		return self._data[jid[:(jid + "/").find("/")]]

	def getShow(self, jid):
		"""
		Returns "show" value of contact "jid". "jid" should be a full (not bare) JID.
		"""
		return self._getResourceData(jid, "show")

	def getStatus(self, jid):
		"""
		Returns "status" value of contact "jid". "jid" should be a full (not bare) JID.
		"""
		return self._getResourceData(jid, "status")

	def getSubscription(self, jid):
		"""
		Returns "subscription" value of contact "jid".
		"""
		return self._getItemData(jid, "subscription")

	def getResources(self, jid):
		"""
		Returns list of connected resources of contact "jid".
		"""
		return self._data[jid[:(jid + "/").find("/")]]["resources"].keys()

	def setItem(self, jid, name=None, groups=[]):
		"""
		Creates/renames contact "jid" and sets the groups list that it now belongs to.
		"""
		iq = Iq("set", NS_ROSTER)
		query = iq.getTag("query")
		attrs = {"jid": jid}
		if name:
			attrs["name"] = name
		item = query.setTag("item", attrs)
		for group in groups:
			item.addChild(node=Node("group", payload=[group]))
		self._owner.send(iq)

	def getItems(self):
		"""
		Return list of all [bare] JIDs that the roster is currently tracks.
		"""
		return self._data.keys()

	def keys(self):
		"""
		Same as getItems. Provided for the sake of dictionary interface.
		"""
		return self._data.keys()

	def __getitem__(self, item):
		"""
		Get the contact in the internal format. Raises KeyError if JID "item" is not in roster.
		"""
		return self._data[item]

	def getItem(self, item):
		"""
		Get the contact in the internal format (or None if JID "item" is not in roster).
		"""
		if item in self._data:
			return self._data[item]

	def Subscribe(self, jid):
		"""
		Send subscription request to JID "jid".
		"""
		self._owner.send(Presence(jid, "subscribe"))

	def Unsubscribe(self, jid):
		"""
		Ask for removing our subscription for JID "jid".
		"""
		self._owner.send(Presence(jid, "unsubscribe"))

	def Authorize(self, jid):
		"""
		Authorise JID "jid". Works only if these JID requested auth previously.
		"""
		self._owner.send(Presence(jid, "subscribed"))

	def Unauthorize(self, jid):
		"""
		Unauthorise JID "jid". Use for declining authorisation request
		or for removing existing authorization.
		"""
		self._owner.send(Presence(jid, "unsubscribed"))

########NEW FILE########
__FILENAME__ = simplexml
##   simplexml.py based on Mattew Allum's xmlstream.py
##
##   Copyright (C) 2003-2005 Alexey "Snake" Nezhdanov
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

# $Id: simplexml.py, v1.36 2014/01/10 alkorgun Exp $

"""
Simplexml module provides xmpppy library with all needed tools to handle
XML nodes and XML streams.
I'm personally using it in many other separate projects.
It is designed to be as standalone as possible.
"""

import xml.parsers.expat

XML_ls = (
	("&", "&amp;"),
	("<", "&lt;"),
	(">", "&gt;"),
	('"', "&quot;"),
	("'", "&apos;")
)

def XMLescape(body):
	for char, edef in XML_ls:
		body = body.replace(char, edef)
	return body.strip()

ENCODING = "utf-8"

def ustr(what):
	"""
	Converts object "what" to unicode string using it's own __str__ method if accessible or unicode method otherwise.
	"""
	if isinstance(what, unicode):
		return what
	try:
		what = what.__str__()
	except AttributeError:
		what = str(what)
	if not isinstance(what, unicode):
		return unicode(what, ENCODING)
	return what

class Node(object):
	"""
	Node class describes syntax of separate XML Node. It have a constructor that permits node creation
	from set of "namespace name", attributes and payload of text strings and other nodes.
	It does not natively support building node from text string and uses NodeBuilder class for that purpose.
	After creation node can be mangled in many ways so it can be completely changed.
	Also node can be serialized into string in one of two modes: default (where the textual representation
	of node describes it exactly) and "fancy" - with whitespace added to make indentation and thus make
	result more readable by human.

	Node class have attribute FORCE_NODE_RECREATION that is defaults to False thus enabling fast node
	replication from the some other node. The drawback of the fast way is that new node shares some
	info with the "original" node that is changing the one node may influence the other. Though it is
	rarely needed (in xmpppy it is never needed at all since I'm usually never using original node after
	replication (and using replication only to move upwards on the classes tree).
	"""
	FORCE_NODE_RECREATION = 0

	def __init__(self, tag=None, attrs={}, payload=[], parent=None, nsp=None, node_built=False, node=None):
		"""
		Takes "tag" argument as the name of node (prepended by namespace, if needed and separated from it
		by a space), attrs dictionary as the set of arguments, payload list as the set of textual strings
		and child nodes that this node carries within itself and "parent" argument that is another node
		that this one will be the child of. Also the __init__ can be provided with "node" argument that is
		either a text string containing exactly one node or another Node instance to begin with. If both
		"node" and other arguments is provided then the node initially created as replica of "node"
		provided and then modified to be compliant with other arguments.
		"""
		if node:
			if self.FORCE_NODE_RECREATION and isinstance(node, Node):
				node = str(node)
			if not isinstance(node, Node):
				node = NodeBuilder(node, self)
				node_built = True
			else:
				self.name, self.namespace, self.attrs, self.data, self.kids, self.parent, self.nsd = node.name, node.namespace, {}, [], [], node.parent, {}
				for key in node.attrs.keys():
					self.attrs[key] = node.attrs[key]
				for data in node.data:
					self.data.append(data)
				for kid in node.kids:
					self.kids.append(kid)
				for k, v in node.nsd.items():
					self.nsd[k] = v
		else:
			self.name, self.namespace, self.attrs, self.data, self.kids, self.parent, self.nsd = "tag", "", {}, [], [], None, {}
		if parent:
			self.parent = parent
		self.nsp_cache = {}
		if nsp:
			for k, v in nsp.items():
				self.nsp_cache[k] = v
		for attr, val in attrs.items():
			if attr == "xmlns":
				self.nsd[""] = val
			elif attr.startswith("xmlns:"):
				self.nsd[attr[6:]] = val
			self.attrs[attr] = attrs[attr]
		if tag:
			if node_built:
				pfx, self.name = ([""] + tag.split(":"))[-2:]
				self.namespace = self.lookup_nsp(pfx)
			elif " " in tag:
				self.namespace, self.name = tag.split()
			else:
				self.name = tag
		if isinstance(payload, basestring):
			payload = [payload]
		for i in payload:
			if isinstance(i, Node):
				self.addChild(node=i)
			else:
				self.data.append(ustr(i))

	def lookup_nsp(self, pfx=""):
		ns = self.nsd.get(pfx, None)
		if ns is None:
			ns = self.nsp_cache.get(pfx, None)
		if ns is None:
			if self.parent:
				ns = self.parent.lookup_nsp(pfx)
				self.nsp_cache[pfx] = ns
			else:
				return "http://www.gajim.org/xmlns/undeclared"
		return ns

	def __str__(self, fancy=0):
		"""
		Method used to dump node into textual representation.
		if "fancy" argument is set to True produces indented output for readability.
		"""
		s = (fancy - 1) * 2 * " " + "<" + self.name
		if self.namespace:
			if not self.parent or self.parent.namespace != self.namespace:
				if "xmlns" not in self.attrs:
					s += " xmlns=\"%s\"" % self.namespace
		for key in self.attrs.keys():
			val = ustr(self.attrs[key])
			s += " %s=\"%s\"" % (key, XMLescape(val))
		s += ">"
		cnt = 0
		if self.kids:
			if fancy:
				s += "\n"
			for a in self.kids:
				if not fancy and (len(self.data) - 1) >= cnt:
					s += XMLescape(self.data[cnt])
				elif (len(self.data) - 1) >= cnt:
					s += XMLescape(self.data[cnt].strip())
				if isinstance(a, Node):
					s += a.__str__(fancy and fancy + 1)
				elif a:
					s += a.__str__()
				cnt += 1
		if not fancy and (len(self.data) - 1) >= cnt:
			s += XMLescape(self.data[cnt])
		elif (len(self.data) - 1) >= cnt:
			s += XMLescape(self.data[cnt].strip())
		if not self.kids and s.endswith(">"):
			s = s[:-1] + " />"
			if fancy:
				s += "\n"
		else:
			if fancy and not self.data:
				s += (fancy - 1) * 2 * " "
			s += "</" + self.name + ">"
			if fancy:
				s += "\n"
		return s

	def getCDATA(self):
		"""
		Serialize node, dropping all tags and leaving CDATA intact.
		That is effectively kills all formatting, leaving only text were contained in XML.
		"""
		s = ""
		cnt = 0
		if self.kids:
			for a in self.kids:
				s += self.data[cnt]
				if a:
					s += a.getCDATA()
				cnt += 1
		if (len(self.data) - 1) >= cnt:
			s += self.data[cnt]
		return s

	def addChild(self, name=None, attrs={}, payload=[], namespace=None, node=None):
		"""
		If "node" argument is provided, adds it as child node. Else creates new node from
		the other arguments' values and adds it as well.
		"""
		if "xmlns" in attrs:
			raise AttributeError("Use namespace=x instead of attrs={\"xmlns\": x}")
		if node:
			newnode = node
			node.parent = self
		else:
			newnode = Node(tag=name, parent=self, attrs=attrs, payload=payload)
		if namespace:
			newnode.setNamespace(namespace)
		self.kids.append(newnode)
		self.data.append("")
		return newnode

	def addData(self, data):
		"""
		Adds some CDATA to node.
		"""
		self.data.append(ustr(data))
		self.kids.append(None)

	def clearData(self):
		"""
		Removes all CDATA from the node.
		"""
		self.data = []

	def delAttr(self, key):
		"""
		Deletes an attribute "key"
		"""
		del self.attrs[key]

	def delChild(self, node, attrs={}):
		"""
		Deletes the "node" from the node's childs list, if "node" is an instance.
		Else deletes the first node that have specified name and (optionally) attributes.
		"""
		if not isinstance(node, Node):
			node = self.getTag(node, attrs)
		self.kids[self.kids.index(node)] = None
		return node

	def getAttrs(self):
		"""
		Returns all node's attributes as dictionary.
		"""
		return self.attrs

	def getAttr(self, key):
		"""
		Returns value of specified attribute.
		"""
		try:
			attr = self.attrs[key]
		except Exception:
			attr = None
		return attr

	def getChildren(self):
		"""
		Returns all node's child nodes as list.
		"""
		return self.kids

	def getData(self):
		"""
		Returns all node CDATA as string (concatenated).
		"""
		return "".join(self.data)

	def getName(self):
		"""
		Returns the name of node.
		"""
		return self.name

	def getNamespace(self):
		"""
		Returns the namespace of node.
		"""
		return self.namespace

	def getParent(self):
		"""
		Returns the parent of node (if present).
		"""
		return self.parent

	def getPayload(self):
		"""
		Return the payload of node i.e. list of child nodes and CDATA entries.
		F.e. for "<node>text1<nodea/><nodeb/> text2</node>" will be returned list:
		["text1", <nodea instance>, <nodeb instance>, " text2"].
		"""
		pl = []
		for i in xrange(max(len(self.data), len(self.kids))):
			if i < len(self.data) and self.data[i]:
				pl.append(self.data[i])
			if i < len(self.kids) and self.kids[i]:
				pl.append(self.kids[i])
		return pl

	def getTag(self, name, attrs={}, namespace=None):
		"""
		Filters all child nodes using specified arguments as filter.
		Returns the first found or None if not found.
		"""
		return self.getTags(name, attrs, namespace, one=1)

	def getTagAttr(self, tag, attr):
		"""
		Returns attribute value of the child with specified name (or None if no such attribute).
		"""
		try:
			attr = self.getTag(tag).attrs[attr]
		except Exception:
			attr = None
		return attr

	def getTagData(self, tag):
		"""
		Returns cocatenated CDATA of the child with specified name.
		"""
		try:
			data = self.getTag(tag).getData()
		except Exception:
			data = None
		return data

	def getTags(self, name, attrs={}, namespace=None, one=0):
		"""
		Filters all child nodes using specified arguments as filter.
		Returns the list of nodes found.
		"""
		nodes = []
		for node in self.kids:
			if not node:
				continue
			if namespace and namespace != node.getNamespace():
				continue
			if node.getName() == name:
				for key in attrs.keys():
					if key not in node.attrs or node.attrs[key] != attrs[key]:
						break
				else:
					nodes.append(node)
			if one and nodes:
				return nodes[0]
		if not one:
			return nodes

	def iterTags(self, name, attrs={}, namespace=None):
		"""
		Iterate over all children using specified arguments as filter.
		"""
		for node in self.kids:
			if not node:
				continue
			if namespace is not None and namespace != node.getNamespace():
				continue
			if node.getName() == name:
				for key in attrs.keys():
					if key not in node.attrs or node.attrs[key] != attrs[key]:
						break
				else:
					yield node

	def setAttr(self, key, val):
		"""
		Sets attribute "key" with the value "val".
		"""
		self.attrs[key] = val

	def setData(self, data):
		"""
		Sets node's CDATA to provided string. Resets all previous CDATA!
		"""
		self.data = [ustr(data)]

	def setName(self, val):
		"""
		Changes the node name.
		"""
		self.name = val

	def setNamespace(self, namespace):
		"""
		Changes the node namespace.
		"""
		self.namespace = namespace

	def setParent(self, node):
		"""
		Sets node's parent to "node". WARNING: do not checks if the parent already present
		and not removes the node from the list of childs of previous parent.
		"""
		self.parent = node

	def setPayload(self, payload, add=0):
		"""
		Sets node payload according to the list specified. WARNING: completely replaces all node's
		previous content. If you wish just to add child or CDATA - use addData or addChild methods.
		"""
		if isinstance(payload, basestring):
			payload = [payload]
		if add:
			self.kids += payload
		else:
			self.kids = payload

	def setTag(self, name, attrs={}, namespace=None):
		"""
		Same as getTag but if the node with specified namespace/attributes not found, creates such
		node and returns it.
		"""
		node = self.getTags(name, attrs, namespace=namespace, one=1)
		if not node:
			node = self.addChild(name, attrs, namespace=namespace)
		return node

	def setTagAttr(self, tag, attr, val):
		"""
		Creates new node (if not already present) with name "tag"
		and sets it's attribute "attr" to value "val".
		"""
		try:
			self.getTag(tag).attrs[attr] = val
		except Exception:
			self.addChild(tag, attrs={attr: val})

	def setTagData(self, tag, val, attrs={}):
		"""
		Creates new node (if not already present) with name "tag"
		and (optionally) attributes "attrs" and sets it's CDATA to string "val".
		"""
		try:
			self.getTag(tag, attrs).setData(ustr(val))
		except Exception:
			self.addChild(tag, attrs, payload=[ustr(val)])

	def has_attr(self, key):
		"""
		Checks if node have attribute "key".
		"""
		return key in self.attrs

	def __getitem__(self, item):
		"""
		Returns node's attribute "item" value.
		"""
		return self.getAttr(item)

	def __setitem__(self, item, val):
		"""
		Sets node's attribute "item" value.
		"""
		return self.setAttr(item, val)

	def __delitem__(self, item):
		"""
		Deletes node's attribute "item".
		"""
		return self.delAttr(item)

	def __getattr__(self, attr):
		"""
		Reduce memory usage caused by T/NT classes - use memory only when needed.
		"""
		if attr == "T":
			self.T = T(self)
			return self.T
		if attr == "NT":
			self.NT = NT(self)
			return self.NT
		raise AttributeError()

class T:
	"""
	Auxiliary class used to quick access to node's child nodes.
	"""
	def __init__(self, node):
		self.__dict__["node"] = node

	def __getattr__(self, attr):
		return self.node.getTag(attr)

	def __setattr__(self, attr, val):
		if isinstance(val, Node):
			Node.__init__(self.node.setTag(attr), node=val)
		else:
			return self.node.setTagData(attr, val)

	def __delattr__(self, attr):
		return self.node.delChild(attr)

class NT(T):
	"""
	Auxiliary class used to quick create node's child nodes.
	"""
	def __getattr__(self, attr):
		return self.node.addChild(attr)

	def __setattr__(self, attr, val):
		if isinstance(val, Node):
			self.node.addChild(attr, node=val)
		else:
			return self.node.addChild(attr, payload=[val])

DBG_NODEBUILDER = "nodebuilder"

class NodeBuilder:
	"""
	Builds a Node class minidom from data parsed to it. This class used for two purposes:
	1. Creation an XML Node from a textual representation. F.e. reading a config file. See an XML2Node method.
	2. Handling an incoming XML stream. This is done by mangling
		the __dispatch_depth parameter and redefining the dispatch method.
	You do not need to use this class directly if you do not designing your own XML handler.
	"""
	def __init__(self, data=None, initial_node=None):
		"""
		Takes two optional parameters: "data" and "initial_node".
		By default class initialised with empty Node class instance.
		Though, if "initial_node" is provided it used as "starting point".
		You can think about it as of "node upgrade".
		"data" (if provided) feeded to parser immidiatedly after instance init.
		"""
		self.DEBUG(DBG_NODEBUILDER, "Preparing to handle incoming XML stream.", "start")
		self._parser = xml.parsers.expat.ParserCreate()
		self._parser.StartElementHandler = self.starttag
		self._parser.EndElementHandler = self.endtag
		self._parser.CharacterDataHandler = self.handle_cdata
		self._parser.StartNamespaceDeclHandler = self.handle_namespace_start
		self._parser.buffer_text = True
		self.Parse = self._parser.Parse
		self.__depth = 0
		self.__last_depth = 0
		self.__max_depth = 0
		self._dispatch_depth = 1
		self._document_attrs = None
		self._document_nsp = None
		self._mini_dom = initial_node
		self.last_is_data = 1
		self._ptr = None
		self.data_buffer = None
		self.streamError = ""
		if data:
			self._parser.Parse(data, 1)

	def check_data_buffer(self):
		if self.data_buffer:
			self._ptr.data.append("".join(self.data_buffer))
			del self.data_buffer[:]
			self.data_buffer = None

	def destroy(self):
		"""
		Method used to allow class instance to be garbage-collected.
		"""
		self.check_data_buffer()
		self._parser.StartElementHandler = None
		self._parser.EndElementHandler = None
		self._parser.CharacterDataHandler = None
		self._parser.StartNamespaceDeclHandler = None

	def starttag(self, tag, attrs):
		"""
		XML Parser callback. Used internally.
		"""
		self.check_data_buffer()
		self._inc_depth()
		self.DEBUG(DBG_NODEBUILDER, "DEPTH -> %i , tag -> %s, attrs -> %s" % (self.__depth, tag, repr(attrs)), "down")
		if self.__depth == self._dispatch_depth:
			if not self._mini_dom:
				self._mini_dom = Node(tag=tag, attrs=attrs, nsp=self._document_nsp, node_built=True)
			else:
				Node.__init__(self._mini_dom, tag=tag, attrs=attrs, nsp=self._document_nsp, node_built=True)
			self._ptr = self._mini_dom
		elif self.__depth > self._dispatch_depth:
			self._ptr.kids.append(Node(tag=tag, parent=self._ptr, attrs=attrs, node_built=True))
			self._ptr = self._ptr.kids[-1]
		if self.__depth == 1:
			self._document_attrs = {}
			self._document_nsp = {}
			nsp, name = ([""] + tag.split(":"))[-2:]
			for attr, val in attrs.items():
				if attr == "xmlns":
					self._document_nsp[""] = val
				elif attr.startswith("xmlns:"):
					self._document_nsp[attr[6:]] = val
				else:
					self._document_attrs[attr] = val
			ns = self._document_nsp.get(nsp, "http://www.gajim.org/xmlns/undeclared-root")
			try:
				self.stream_header_received(ns, name, attrs)
			except ValueError:
				self._document_attrs = None
				raise
		if not self.last_is_data and self._ptr.parent:
			self._ptr.parent.data.append("")
		self.last_is_data = 0

	def endtag(self, tag):
		"""
		XML Parser callback. Used internally.
		"""
		self.DEBUG(DBG_NODEBUILDER, "DEPTH -> %i , tag -> %s" % (self.__depth, tag), "up")
		self.check_data_buffer()
		if self.__depth == self._dispatch_depth:
			if self._mini_dom and self._mini_dom.getName() == "error":
				self.streamError = self._mini_dom.getChildren()[0].getName()
			self.dispatch(self._mini_dom)
		elif self.__depth > self._dispatch_depth:
			self._ptr = self._ptr.parent
		else:
			self.DEBUG(DBG_NODEBUILDER, "Got higher than dispatch level. Stream terminated?", "stop")
		self._dec_depth()
		self.last_is_data = 0
		if not self.__depth:
			self.stream_footer_received()

	def handle_cdata(self, data):
		"""
		XML Parser callback. Used internally.
		"""
		self.DEBUG(DBG_NODEBUILDER, data, "data")
		if self.last_is_data:
			if self.data_buffer:
				self.data_buffer.append(data)
		elif self._ptr:
			self.data_buffer = [data]
			self.last_is_data = 1

	def handle_namespace_start(self, prefix, uri):
		"""
		XML Parser callback. Used internally.
		"""
		self.check_data_buffer()

	def DEBUG(self, level, text, comment=None):
		"""
		Gets all NodeBuilder walking events. Can be used for debugging if redefined.
		"""
	def getDom(self):
		"""
		Returns just built Node.
		"""
		self.check_data_buffer()
		return self._mini_dom

	def dispatch(self, stanza):
		"""
		Gets called when the NodeBuilder reaches some level of depth on it's way up with the built
		node as argument. Can be redefined to convert incoming XML stanzas to program events.
		"""

	def stream_header_received(self, ns, tag, attrs):
		"""
		Method called when stream just opened.
		"""
		self.check_data_buffer()

	def stream_footer_received(self):
		"""
		Method called when stream just closed.
		"""
		self.check_data_buffer()

	def has_received_endtag(self, level=0):
		"""
		Return True if at least one end tag was seen (at level).
		"""
		return self.__depth <= level and self.__max_depth > level

	def _inc_depth(self):
		self.__last_depth = self.__depth
		self.__depth += 1
		self.__max_depth = max(self.__depth, self.__max_depth)

	def _dec_depth(self):
		self.__last_depth = self.__depth
		self.__depth -= 1

def XML2Node(xml):
	"""
	Converts supplied textual string into XML node. Handy f.e. for reading configuration file.
	Raises xml.parser.expat.parsererror if provided string is not well-formed XML.
	"""
	return NodeBuilder(xml).getDom()

def BadXML2Node(xml):
	"""
	Converts supplied textual string into XML node. Survives if xml data is cutted half way round.
	I.e. "<html>some text <br>some more text". Will raise xml.parser.expat.parsererror on misplaced
	tags though. F.e. "<b>some text <br>some more text</b>" will not work.
	"""
	return NodeBuilder(xml).getDom()

########NEW FILE########
__FILENAME__ = transports
##   transports.py
##
##   Copyright (C) 2003-2004 Alexey "Snake" Nezhdanov
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

# $Id: transports.py, v1.38 2014/02/16 alkorgun Exp $

"""
This module contains the low-level implementations of xmpppy connect methods or
(in other words) transports for xmpp-stanzas.
Currently here is three transports:
direct TCP connect - TCPsocket class
proxied TCP connect - HTTPPROXYsocket class (CONNECT proxies)
TLS connection - TLS class. Can be used for SSL connections also.

Transports are stackable so you - f.e. TLS use HTPPROXYsocket or TCPsocket as more low-level transport.

Also exception 'error' is defined to allow capture of this module specific exceptions.
"""

import sys
import socket
if sys.hexversion >= 0x20600F0:
	import ssl
import thread
import time
from . import dispatcher

from base64 import encodestring
from select import select
from .simplexml import ustr
from .plugin import PlugIn
from .protocol import *

# http://pydns.sourceforge.net
try:
	import dns
except ImportError:
	dns = None

DATA_RECEIVED = 'DATA RECEIVED'
DATA_SENT = 'DATA SENT'
DBG_CONNECT_PROXY = 'CONNECTproxy'

BUFLEN = 2024
SEND_INTERVAL = 0

class SendSemaphore(object):

	def __init__(self):
		self.__lock = thread.allocate_lock()
		self.__released = 0
		self.interval = SEND_INTERVAL

	def set_send_interval(self, interval):
		self.interval = interval

	def acquire(self, blocking=1):
		rc = self.__lock.acquire(blocking)
		if blocking and self.interval:
			elapsed = time.time() - self.__released
			if elapsed < self.interval:
				time.sleep(self.interval - elapsed)
		return rc

	__enter__ = acquire

	def release(self):
		self.__released = time.time()
		self.__lock.release()

	def __exit__(self, *args):
		self.release()

class error:
	"""
	An exception to be raised in case of low-level errors in methods of 'transports' module.
	"""
	def __init__(self, comment):
		"""
		Cache the descriptive string.
		"""
		self._comment = comment

	def __str__(self):
		"""
		Serialize exception into pre-cached descriptive string.
		"""
		return self._comment

class TCPsocket(PlugIn):
	"""
	This class defines direct TCP connection method.
	"""
	def __init__(self, server=None, use_srv=True):
		"""
		Cache connection point 'server'. 'server' is the tuple of (host, port)
		absolutely the same as standard tcp socket uses. However library will lookup for
		('_xmpp-client._tcp.' + host) SRV record in DNS and connect to the found (if it is)
		server instead.
		"""
		PlugIn.__init__(self)
		self.DBG_LINE = "socket"
		self._sequence = SendSemaphore()
		self.set_send_interval = self._sequence.set_send_interval
		self._exported_methods = [self.send, self.disconnect, self.set_send_interval]
		self._server, self.use_srv = server, use_srv

	def srv_lookup(self, server):
		"""
		SRV resolver. Takes server=(host, port) as argument. Returns new (host, port) pair.
		"""
		if dns:
			query = "_xmpp-client._tcp.%s" % server[0]
			try:
				dns.DiscoverNameServers()
				dns__ = dns.Request()
				response = dns__.req(query, qtype="SRV")
				if response.answers:
					# Sort by priority, according to RFC 2782.
					answers = sorted(response.answers, key=lambda a: a["data"][0])
					(port, host) = answers[0]["data"][2:]
					server = str(host), int(port)
			except dns.DNSError:
				self.DEBUG("An error occurred while looking up %s." % query, "warn")
		return server

	def plugin(self, owner):
		"""
		Fire up connection. Return non-empty string on success.
		Also registers self.disconnected method in the owner's dispatcher.
		Called internally.
		"""
		if not self._server:
			self._server = (self._owner.Server, 5222)
		if self.use_srv:
			server = self.srv_lookup(self._server)
		else:
			server = self._server
		if not self.connect(server):
			return None
		self._owner.Connection = self
		self._owner.RegisterDisconnectHandler(self.disconnected)
		return "ok"

	def getHost(self):
		"""
		Returns the 'host' value that is connection is [will be] made to.
		"""
		return self._server[0]

	def getPort(self):
		"""
		Returns the 'port' value that is connection is [will be] made to.
		"""
		return self._server[1]

	def connect(self, server=None):
		"""
		Try to connect to the given host/port.
		Returns non-empty string on success.
		"""
		if not server:
			server = self._server
		host, port = server
		socktype = socket.SOCK_STREAM
		try:
			lookup = reversed(socket.getaddrinfo(host, int(port), 0, socktype))
		except Exception:
			addr = (host, int(port))
			if ":" in host:
				af = socket.AF_INET6
				addr = addr.__add__((0, 0))
			else:
				af = socket.AF_INET
			lookup = [(af, socktype, 1, 6, addr)]
		for af, socktype, proto, cn, addr in lookup:
			try:
				self._sock = socket.socket(af, socktype)
				self._sock.connect(addr)
				self._send = self._sock.sendall
				self._recv = self._sock.recv
			except socket.error as error:
				if getattr(self, "_sock", None):
					self._sock.close()
				try:
					code, error = error
				except Exception:
					code = -1
				self.DEBUG("Failed to connect to remote host %s: %s (%s)" % (repr(server), error, code), "error")
			except Exception:
				pass
			else:
				self.DEBUG("Successfully connected to remote host %s." % repr(server), "start")
				return "ok"

	def plugout(self):
		"""
		Disconnect from the remote server and unregister self.disconnected method from
		the owner's dispatcher.
		"""
		if getattr(self, "_sock", None):
			self._sock.close()
		if hasattr(self._owner, "Connection"):
			del self._owner.Connection
			self._owner.UnregisterDisconnectHandler(self.disconnected)

	def receive(self):
		"""
		Reads all pending incoming data.
		In case of disconnection calls owner's disconnected() method and then raises IOError exception.
		"""
		try:
			data = self._recv(BUFLEN)
		except socket.sslerror as e:
			self._seen_data = 0
			if e[0] in (socket.SSL_ERROR_WANT_READ, socket.SSL_ERROR_WANT_WRITE):
				return ""
			self.DEBUG("Socket error while receiving data.", "error")
			sys.exc_clear()
			self._owner.disconnected()
			raise IOError("Disconnected!")
		except Exception:
			data = ""
		while self.pending_data(0):
			try:
				add = self._recv(BUFLEN)
			except Exception:
				break
			if not add:
				break
			data += add
		if data:
			self._seen_data = 1
			self.DEBUG(data, "got")
			if hasattr(self._owner, "Dispatcher"):
				self._owner.Dispatcher.Event("", DATA_RECEIVED, data)
		else:
			self.DEBUG("Socket error while receiving data.", "error")
			sys.exc_clear()
			self._owner.disconnected()
			raise IOError("Disconnected!")
		return data

	def send(self, data):
		"""
		Writes raw outgoing data. Blocks until done.
		If supplied data is unicode string, encodes it to utf-8 before send.
		"""
		if isinstance(data, unicode):
			data = data.encode("utf-8")
		elif not isinstance(data, str):
			data = ustr(data).encode("utf-8")
		with self._sequence:
			try:
				self._send(data)
			except Exception:
				self.DEBUG("Socket error while sending data.", "error")
				self._owner.disconnected()
			else:
				if not data.strip():
					data = repr(data)
				self.DEBUG(data, "sent")
				if hasattr(self._owner, "Dispatcher"):
					self._owner.Dispatcher.Event("", DATA_SENT, data)

	def pending_data(self, timeout=0):
		"""
		Returns true if there is a data ready to be read.
		"""
		return select([self._sock], [], [], timeout)[0]

	def disconnect(self):
		"""
		Closes the socket.
		"""
		self.DEBUG("Closing socket.", "stop")
		self._sock.close()

	def disconnected(self):
		"""
		Called when a Network Error or disconnection occurs.
		Designed to be overidden.
		"""
		self.DEBUG("Socket operation failed.", "error")

class HTTPPROXYsocket(TCPsocket):
	"""
	HTTP (CONNECT) proxy connection class. Uses TCPsocket as the base class
	redefines only connect method. Allows to use HTTP proxies like squid with
	(optionally) simple authentication (using login and password).
	"""
	def __init__(self, proxy, server, use_srv=True):
		"""
		Caches proxy and target addresses.
		'proxy' argument is a dictionary with mandatory keys 'host' and 'port' (proxy address)
		and optional keys 'user' and 'password' to use for authentication.
		'server' argument is a tuple of host and port - just like TCPsocket uses.
		"""
		TCPsocket.__init__(self, server, use_srv)
		self.DBG_LINE = DBG_CONNECT_PROXY
		self._proxy = proxy

	def plugin(self, owner):
		"""
		Starts connection. Used interally. Returns non-empty string on success.
		"""
		owner.debug_flags.append(DBG_CONNECT_PROXY)
		return TCPsocket.plugin(self, owner)

	def connect(self, dupe=None):
		"""
		Starts connection. Connects to proxy, supplies login and password to it
		(if were specified while creating instance). Instructs proxy to make
		connection to the target server. Returns non-empty sting on success.
		"""
		if not TCPsocket.connect(self, (self._proxy["host"], self._proxy["port"])):
			return None
		self.DEBUG("Proxy server contacted, performing authentification.", "start")
		connector = [
			"CONNECT %s:%s HTTP/1.0" % self._server,
			"Proxy-Connection: Keep-Alive",
			"Pragma: no-cache",
			"Host: %s:%s" % self._server,
			"User-Agent: HTTPPROXYsocket/v0.1"
		]
		if "user" in self._proxy and "password" in self._proxy:
			credentials = "%s:%s" % (self._proxy["user"], self._proxy["password"])
			credentials = encodestring(credentials).strip()
			connector.append("Proxy-Authorization: Basic " + credentials)
		connector.append("\r\n")
		self.send("\r\n".join(connector))
		try:
			reply = self.receive().replace("\r", "")
		except IOError:
			self.DEBUG("Proxy suddenly disconnected.", "error")
			self._owner.disconnected()
			return None
		try:
			proto, code, desc = reply.split("\n")[0].split(" ", 2)
		except Exception:
			raise error("Invalid proxy reply")
		if code != "200":
			self.DEBUG("Invalid proxy reply: %s %s %s" % (proto, code, desc), "error")
			self._owner.disconnected()
			return None
		while reply.find("\n\n") == -1:
			try:
				reply += self.receive().replace("\r", "")
			except IOError:
				self.DEBUG("Proxy suddenly disconnected.", "error")
				self._owner.disconnected()
				return None
		self.DEBUG("Authentification successfull. Jabber server contacted.", "ok")
		return "ok"

	def DEBUG(self, text, severity):
		"""
		Overwrites DEBUG tag to allow debug output be presented as 'CONNECTproxy'.
		"""
		return self._owner.DEBUG(DBG_CONNECT_PROXY, text, severity)

class TLS(PlugIn):
	"""
	TLS connection used to encrypts already estabilished tcp connection.
	"""
	def PlugIn(self, owner, now=0):
		"""
		If the 'now' argument is true then starts using encryption immidiatedly.
		If 'now' in false then starts encryption as soon as TLS feature is
		declared by the server (if it were already declared - it is ok).
		"""
		if hasattr(owner, "TLS"):
			return None
		PlugIn.PlugIn(self, owner)
		DBG_LINE = "TLS"
		if now:
			return self._startSSL()
		if self._owner.Dispatcher.Stream.features:
			try:
				self.FeaturesHandler(self._owner.Dispatcher, self._owner.Dispatcher.Stream.features)
			except NodeProcessed:
				pass
		else:
			self._owner.RegisterHandlerOnce("features", self.FeaturesHandler, xmlns=NS_STREAMS)
		self.starttls = None

	def plugout(self, now=0):
		"""
		Unregisters TLS handler's from owner's dispatcher. Take note that encription
		can not be stopped once started. You can only break the connection and start over.
		"""
		self._owner.UnregisterHandler("features", self.FeaturesHandler, xmlns=NS_STREAMS)
		self._owner.UnregisterHandler("proceed", self.StartTLSHandler, xmlns=NS_TLS)
		self._owner.UnregisterHandler("failure", self.StartTLSHandler, xmlns=NS_TLS)

	def FeaturesHandler(self, conn, feats):
		"""
		Used to analyse server <features/> tag for TLS support.
		If TLS is supported starts the encryption negotiation. Used internally.
		"""
		if not feats.getTag("starttls", namespace=NS_TLS):
			self.DEBUG("TLS unsupported by remote server.", "warn")
			return None
		self.DEBUG("TLS supported by remote server. Requesting TLS start.", "ok")
		self._owner.RegisterHandlerOnce("proceed", self.StartTLSHandler, xmlns=NS_TLS)
		self._owner.RegisterHandlerOnce("failure", self.StartTLSHandler, xmlns=NS_TLS)
		self._owner.Connection.send("<starttls xmlns=\"%s\"/>" % NS_TLS)
		raise NodeProcessed()

	def pending_data(self, timeout=0):
		"""
		Returns true if there possible is a data ready to be read.
		"""
		return self._tcpsock._seen_data or select([self._tcpsock._sock], [], [], timeout)[0]

	def _startSSL(self):
		tcpsock = self._owner.Connection
		if sys.hexversion >= 0x20600F0:
			tcpsock._sslObj = ssl.wrap_socket(tcpsock._sock, None, None)
		else:
			tcpsock._sslObj = socket.ssl(tcpsock._sock, None, None)
			tcpsock._sslIssuer = tcpsock._sslObj.issuer()
			tcpsock._sslServer = tcpsock._sslObj.server()
		tcpsock._recv = tcpsock._sslObj.read
		tcpsock._send = tcpsock._sslObj.write
		tcpsock._seen_data = 1
		self._tcpsock = tcpsock
		tcpsock.pending_data = self.pending_data
		tcpsock._sock.setblocking(0)
		self.starttls = "success"

	def StartTLSHandler(self, conn, starttls):
		"""
		Handle server reply if TLS is allowed to process. Behaves accordingly.
		Used internally.
		"""
		if starttls.getNamespace() != NS_TLS:
			return None
		self.starttls = starttls.getName()
		if self.starttls == "failure":
			self.DEBUG("Got starttls response: " + self.starttls, "error")
			return None
		self.DEBUG("Got starttls proceed response. Switching to TLS/SSL...", "ok")
		self._startSSL()
		self._owner.Dispatcher.PlugOut()
		dispatcher.Dispatcher().PlugIn(self._owner)

########NEW FILE########
