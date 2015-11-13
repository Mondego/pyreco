__FILENAME__ = CmdClient
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
from Yowsup.connectionmanager import YowsupConnectionManager
import time, datetime, sys


if sys.version_info >= (3, 0):
	raw_input = input

class WhatsappCmdClient:
	
	def __init__(self, phoneNumber, keepAlive = False, sendReceipts = False):
		self.sendReceipts = sendReceipts
		self.phoneNumber = phoneNumber
		self.jid = "%s@s.whatsapp.net" % phoneNumber
		
		self.sentCache = {}
		
		connectionManager = YowsupConnectionManager()
		connectionManager.setAutoPong(keepAlive)
		self.signalsInterface = connectionManager.getSignalsInterface()
		self.methodsInterface = connectionManager.getMethodsInterface()
		
		self.signalsInterface.registerListener("auth_success", self.onAuthSuccess)
		self.signalsInterface.registerListener("auth_fail", self.onAuthFailed)
		self.signalsInterface.registerListener("message_received", self.onMessageReceived)
		self.signalsInterface.registerListener("receipt_messageSent", self.onMessageSent)
		self.signalsInterface.registerListener("presence_updated", self.onPresenceUpdated)
		self.signalsInterface.registerListener("disconnected", self.onDisconnected)
		
		
		self.commandMappings = {"lastseen":lambda: self.methodsInterface.call("presence_request", ( self.jid,)),
								"available": lambda: self.methodsInterface.call("presence_sendAvailable"),
								"unavailable": lambda: self.methodsInterface.call("presence_sendUnavailable")
								 }
		
		self.done = False
		#signalsInterface.registerListener("receipt_messageDelivered", lambda jid, messageId: methodsInterface.call("delivered_ack", (jid, messageId)))
	
	def login(self, username, password):
		self.username = username
		self.methodsInterface.call("auth_login", (username, password))

		while not self.done:
			time.sleep(0.5)

	def onAuthSuccess(self, username):
		print("Authed %s" % username)
		self.methodsInterface.call("ready")
		self.goInteractive(self.phoneNumber)

	def onAuthFailed(self, username, err):
		print("Auth Failed!")

	def onDisconnected(self, reason):
		print("Disconnected because %s" %reason)
		
	def onPresenceUpdated(self, jid, lastSeen):
		formattedDate = datetime.datetime.fromtimestamp(long(time.time()) - lastSeen).strftime('%d-%m-%Y %H:%M')
		self.onMessageReceived(0, jid, "LAST SEEN RESULT: %s"%formattedDate, long(time.time()), False, None, False)

	def onMessageSent(self, jid, messageId):
		formattedDate = datetime.datetime.fromtimestamp(self.sentCache[messageId][0]).strftime('%d-%m-%Y %H:%M')
		print("%s [%s]:%s"%(self.username, formattedDate, self.sentCache[messageId][1]))
		print(self.getPrompt())

	def runCommand(self, command):
		if command[0] == "/":
			command = command[1:].split(' ')
			try:
				self.commandMappings[command[0]]()
				return 1
			except KeyError:
				return 0
		
		return 0
			
	def onMessageReceived(self, messageId, jid, messageContent, timestamp, wantsReceipt, pushName, isBroadcast):
		if jid[:jid.index('@')] != self.phoneNumber:
			return
		formattedDate = datetime.datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y %H:%M')
		print("%s [%s]:%s"%(jid, formattedDate, messageContent))
		
		if wantsReceipt and self.sendReceipts:
			self.methodsInterface.call("message_ack", (jid, messageId))

		print(self.getPrompt())
	
	def goInteractive(self, jid):
		print("Starting Interactive chat with %s" % jid)
		jid = "%s@s.whatsapp.net" % jid
		print(self.getPrompt())
		while True:
			message = raw_input()
			message = message.strip()
			if not len(message):
				continue
			if not self.runCommand(message.strip()):
				msgId = self.methodsInterface.call("message_send", (jid, message))
				self.sentCache[msgId] = [int(time.time()), message]
		self.done = True
	def getPrompt(self):
		return "Enter Message or command: (/%s)" % ", /".join(self.commandMappings)

########NEW FILE########
__FILENAME__ = EchoClient
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)
import time

from Yowsup.connectionmanager import YowsupConnectionManager

class WhatsappEchoClient:
	
	def __init__(self, target, message, waitForReceipt=False):
		
		self.jids = []
		
		if '-' in target:
			self.jids = ["%s@g.us" % target]
		else:
			self.jids = ["%s@s.whatsapp.net" % t for t in target.split(',')]

		self.message = message
		self.waitForReceipt = waitForReceipt
		
		connectionManager = YowsupConnectionManager()
		self.signalsInterface = connectionManager.getSignalsInterface()
		self.methodsInterface = connectionManager.getMethodsInterface()
		
		self.signalsInterface.registerListener("auth_success", self.onAuthSuccess)
		self.signalsInterface.registerListener("auth_fail", self.onAuthFailed)
		if waitForReceipt:
			self.signalsInterface.registerListener("receipt_messageSent", self.onMessageSent)
			self.gotReceipt = False
		self.signalsInterface.registerListener("disconnected", self.onDisconnected)

		self.done = False
	
	def login(self, username, password):
		self.username = username
		self.methodsInterface.call("auth_login", (username, password))

		while not self.done:
			time.sleep(0.5)

	def onAuthSuccess(self, username):
		print("Authed %s" % username)

		if self.waitForReceipt:
			self.methodsInterface.call("ready")
		
		
		if len(self.jids) > 1:
			self.methodsInterface.call("message_broadcast", (self.jids, self.message))
		else:
			self.methodsInterface.call("message_send", (self.jids[0], self.message))
		print("Sent message")
		if self.waitForReceipt:
			timeout = 5
			t = 0;
			while t < timeout and not self.gotReceipt:
				time.sleep(0.5)
				t+=1

			if not self.gotReceipt:
				print("print timedout!")
			else:
				print("Got sent receipt")

		self.done = True

	def onAuthFailed(self, username, err):
		print("Auth Failed!")

	def onDisconnected(self, reason):
		print("Disconnected because %s" %reason)

	def onMessageSent(self, jid, messageId):
		self.gotReceipt = True

########NEW FILE########
__FILENAME__ = ListenerClient
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)
import datetime, sys

if sys.version_info >= (3, 0):
	raw_input = input

from Yowsup.connectionmanager import YowsupConnectionManager

class WhatsappListenerClient:
	
	def __init__(self, keepAlive = False, sendReceipts = False):
		self.sendReceipts = sendReceipts
		
		connectionManager = YowsupConnectionManager()
		connectionManager.setAutoPong(keepAlive)

		self.signalsInterface = connectionManager.getSignalsInterface()
		self.methodsInterface = connectionManager.getMethodsInterface()
		
		self.signalsInterface.registerListener("message_received", self.onMessageReceived)
		self.signalsInterface.registerListener("auth_success", self.onAuthSuccess)
		self.signalsInterface.registerListener("auth_fail", self.onAuthFailed)
		self.signalsInterface.registerListener("disconnected", self.onDisconnected)
		
		self.cm = connectionManager
	
	def login(self, username, password):
		self.username = username
		self.methodsInterface.call("auth_login", (username, password))
		
		
		while True:
			raw_input()	

	def onAuthSuccess(self, username):
		print("Authed %s" % username)
		self.methodsInterface.call("ready")

	def onAuthFailed(self, username, err):
		print("Auth Failed!")

	def onDisconnected(self, reason):
		print("Disconnected because %s" %reason)

	def onMessageReceived(self, messageId, jid, messageContent, timestamp, wantsReceipt, pushName, isBroadCast):
		formattedDate = datetime.datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y %H:%M')
		print("%s [%s]:%s"%(jid, formattedDate, messageContent))

		if wantsReceipt and self.sendReceipts:
			self.methodsInterface.call("message_ack", (jid, messageId))
	
########NEW FILE########
__FILENAME__ = auth
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

from .mechanisms.wauth import WAuth as AuthMechanism

from Yowsup.Common.constants import Constants
from Yowsup.Common.debugger import Debugger

class YowsupAuth:
	def __init__(self, connection):
		Debugger.attach(self)

		self.connection = connection
		self.mechanism = AuthMechanism
		self.authenticated = False

		self.username = None
		self.password = None
		self.domain = None
		self.resource = None

		self.supportsReceiptAcks = True
		self.accountKind = None
		self.expireData = None

		self.authCallbacks = []

	def isAuthenticated(self):
		return self.authenticated

	def onAuthenticated(self, callback):
		self.authCallbacks.append(callback)

	def authenticationComplete(self):
		self.authenticated = True
		#should process callbacks

	def authenticationFailed(self):
		self._d("Authentication failed!!")

	def authenticate(self, username, password, domain, resource):
		self._d("Connecting to %s" % Constants.host)
		#connection = ConnectionEngine()
		self.connection.connect((Constants.host, Constants.port));

		
		self.mechanism = AuthMechanism(self.connection)
		self.mechanism.setAuthObject(self)

		self.username = username
		self.password = password
		self.domain = domain
		self.resource = resource
		self.jid = "%s@%s"%(self.username,self.domain)
		
	
		
		connection = self.mechanism.login(username, password, domain, resource)
		return connection

########NEW FILE########
__FILENAME__ = digest
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''


import base64, random;
import os,binascii
import socket
from Tools.debugger import Debugger
import hashlib
from ConnectionIO.protocoltreenode import ProtocolTreeNode

class DigestAuth():

	def __init__(self,conn):
		Debugger.attach(self);

		self.conn = conn
		self._d("Yowsup DigestAuth INIT");

	def setAuthObject(self, authObject):
		self.authObject = authObject
	
	def login(self, username, password, domain, resource):

		try:
			self._d("Starting stream")
			self.conn.writer.streamStart(domain,resource);

			self._d("Sending Features")
			self.sendFeatures();

			self._d("Sending Auth");
			self.sendAuth();

			self._d("Read stream start");
			self.conn.reader.streamStart();

			self._d("Read features and challenge");
			challengeData = self.readFeaturesAndChallenge();
			
			self._d("Sending Response")
			self.sendResponse(challengeData);

			self._d("Read success")
			self.readSuccess();
			
			self.conn.jid = "%s@%s" % (username, domain)
			return self.conn

		except socket.error:
			return self.connectionError.emit()


	def sendFeatures(self):
		toWrite = ProtocolTreeNode("stream:features",None,[ ProtocolTreeNode("receipt_acks",None,None),ProtocolTreeNode("w:profile:picture",{"type":"all"},None), ProtocolTreeNode("w:profile:picture",{"type":"group"},None),ProtocolTreeNode("notification",{"type":"participant"},None), ProtocolTreeNode("status",None,None) ]);
		self.conn.writer.write(toWrite);

	def sendAuth(self):
		# "user":self.connection.user,
		node = ProtocolTreeNode("auth",{"xmlns":"urn:ietf:params:xml:ns:xmpp-sasl","mechanism":"DIGEST-MD5-1"});
		self.conn.writer.write(node);

	def readFeaturesAndChallenge(self):
		server_supports_receipt_acks = True;
		root = self.conn.reader.nextTree();

		while root is not None:
			if ProtocolTreeNode.tagEquals(root,"stream:features"):
				self._d("GOT FEATURES !!!!");
				self.authObject.supportsReceiptAcks  = root.getChild("receipt_acks") is not None;
				root = self.conn.reader.nextTree();

				continue;

			if ProtocolTreeNode.tagEquals(root,"challenge"):
				self._d("GOT CHALLENGE !!!!");
				data = base64.b64decode(root.data);
				return data;
		raise Exception("fell out of loop in readFeaturesAndChallenge");


	def sendResponse(self,challengeData):

		response = self.getResponse(challengeData);
		node = ProtocolTreeNode("response",{"xmlns":"urn:ietf:params:xml:ns:xmpp-sasl"}, None, str(base64.b64encode(response)));
		self.conn.writer.write(node);
		self.conn.reader.inn.buf = [];

	def getResponse(self,challenge):
		self._d(str(challenge))
		nonce_key = "nonce=\""
		i = challenge.index(nonce_key);

		i+=len(nonce_key);
		j = challenge.index('"',i);

		nonce = challenge[i:j];
		
		cnonce = binascii.b2a_hex(os.urandom(6))

		nc = "00000001";
		bos = bytearray();
		bos.extend(hashlib.md5(self.authObject.username + ":" + self.authObject.domain + ":" + self.authObject.password).digest());
		bos.append(58);
		bos.extend(nonce);
		bos.append(58);
		bos.extend(cnonce);

		digest_uri = "xmpp/"+self.authObject.domain;

		A1 = buffer(bos)
		A2 = "AUTHENTICATE:" + digest_uri;

		KD = hashlib.md5(A1).hexdigest() + ":"+nonce+":"+nc+":"+cnonce+":auth:"+ hashlib.md5(A2).hexdigest();

		response = hashlib.md5(KD).hexdigest();
		bigger_response = "";
		bigger_response += "realm=\"";
		bigger_response += self.authObject.domain
		bigger_response += "\",response=";
		bigger_response += response
		bigger_response += ",nonce=\"";
		bigger_response += nonce
		bigger_response += "\",digest-uri=\""
		bigger_response += digest_uri
		bigger_response += "\",cnonce=\""
		bigger_response += cnonce
		bigger_response += "\",qop=auth";
		bigger_response += ",username=\""
		bigger_response += self.authObject.username
		bigger_response += "\",nc="
		bigger_response += nc

		self._d(str(bigger_response))
		return bigger_response;

	def readSuccess(self):
		node = self.conn.reader.nextTree();
		self._d("Login Status: %s"%(node.tag));

		if ProtocolTreeNode.tagEquals(node,"failure"):
			self.authObject.authenticationFailed()
			raise Exception("Login Failure");

		ProtocolTreeNode.require(node,"success");

		expiration = node.getAttributeValue("expiration");

		if expiration is not None:
			self._d("Expires: "+str(expiration));
			self.authObject.expireDate = expiration;

		kind = node.getAttributeValue("kind");
		self._d("Account type: %s"%(kind))

		if kind == "paid":
			self.authObject.accountKind = 1;
		elif kind == "free":
			self.authObject.accountKind = 0;
		else:
			self.authObject.accountKind = -1;

		status = node.getAttributeValue("status");
		self._d("Account status: %s"%(status));

		if status == "expired":
			self.loginFailed.emit()
			raise Exception("Account expired on "+str(self.authObject.expireDate));

		if status == "active":
			if expiration is None:
				#raise Exception ("active account with no expiration");
				'''@@TODO expiration changed to creation'''
		else:
			self.authObject.accountKind = 1;

		self.conn.reader.inn.buf = [];

		self.authObject.authenticationComplete()
########NEW FILE########
__FILENAME__ = wauth
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import socket, hashlib, hmac, sys
from Yowsup.Common.debugger import Debugger
from Yowsup.Common.watime import WATime
from Yowsup.ConnectionIO.protocoltreenode import ProtocolTreeNode

from struct import pack
from operator import xor
from itertools import starmap
from hashlib import sha1


def _bytearray(data):

	if type(data) == str:
		return data
	elif type(data) == list:
		tmp = [chr(x) if type(x) == int else x for x in data]
		return "".join(tmp)
	elif type(data) == int:
		tmp = ""
		#for i in range(0,data):
		#	tmp = tmp + chr(0)
		#	return tmp
		return [0] * data

	return ""

class WAuth():

	def __init__(self,conn):
		Debugger.attach(self);

		self.conn = conn
		self._d("Yowsup WAUTH-1 INIT");

	def setAuthObject(self, authObject):
		self.authObject = authObject
	
	def login(self, username, password, domain, resource):

		self.username = username

		try:
			self._d("Starting stream")
			self.conn.writer.streamStart(domain,resource);

			self._d("Sending Features")
			self.sendFeatures();

			self._d("Sending Auth");
			self.sendAuth();

			self._d("Read stream start");
			self.conn.reader.streamStart();

			self._d("Read features and challenge");
			challengeData = self.readFeaturesAndChallenge();

			self._d("Sending Response")
			self.sendResponse(challengeData);

			self._d("Read success")
			
			if not self.readSuccess(): return 0

			self.conn.jid = "%s@%s" % (username, domain)
			return self.conn

		except socket.error:
			return self.connectionError.emit()


	def sendFeatures(self):
		toWrite = ProtocolTreeNode("stream:features",None,[ ProtocolTreeNode("receipt_acks",None,None),ProtocolTreeNode("w:profile:picture",{"type":"all"},None), ProtocolTreeNode("w:profile:picture",{"type":"group"},None),ProtocolTreeNode("notification",{"type":"participant"},None), ProtocolTreeNode("status",None,None) ])


		self.conn.writer.write(toWrite);

	def sendAuth(self):
		# "user":self.connection.user,
		blob = []
		node = ProtocolTreeNode("auth",{"user":self.username,"xmlns":"urn:ietf:params:xml:ns:xmpp-sasl","mechanism":"WAUTH-1"}, None, ''.join(map(chr, blob)));
		self.conn.writer.write(node);

	def readFeaturesAndChallenge(self):
		root = self.conn.reader.nextTree();

		while root is not None:
			if ProtocolTreeNode.tagEquals(root,"stream:features"):
				self._d("GOT FEATURES !!!!");
				self.authObject.supportsReceiptAcks  = root.getChild("receipt_acks") is not None;
				root = self.conn.reader.nextTree();

				continue;

			if ProtocolTreeNode.tagEquals(root,"challenge"):
				self._d("GOT CHALLENGE !!!!");
				#data = base64.b64decode(root.data);
				return root.data;
		raise Exception("fell out of loop in readFeaturesAndChallenge");


	def sendResponse(self,challengeData):

		authBlob = self.getAuthBlob(challengeData);
		node = ProtocolTreeNode("response",{"xmlns":"urn:ietf:params:xml:ns:xmpp-sasl"}, None, authBlob);
		self.conn.writer.write(node);
		self.conn.reader.inn.buf = [];

	def getAuthBlob(self, nonce):
		numArray = _bytearray(KeyStream.keyFromPasswordAndNonce(self.authObject.password, nonce))
		self.conn.reader.inputKey = self.inputKey = KeyStream(numArray)
		self.outputKey = KeyStream(numArray)

		nums = []

		for i in range(0,4):
			nums.append(0)

		nums.extend(self.username)
		nums.extend(nonce)

		wt = WATime()
		utcNow = int(wt.utcTimestamp())
		nums.extend(str(utcNow))

		encoded = self.outputKey.encodeMessage(nums, 0, 4, len(nums) - 4)
		encoded = "".join(map(chr, encoded))

		return encoded

	def readSuccess(self):
		node = self.conn.reader.nextTree();
		self._d("Login Status: %s"%(node.tag));

		if ProtocolTreeNode.tagEquals(node,"failure"):
			self.authObject.authenticationFailed()
			return 0
			#raise Exception("Login Failure");

		ProtocolTreeNode.require(node,"success");

		expiration = node.getAttributeValue("expiration");

		if expiration is not None:
			self._d("Expires: "+str(expiration));
			self.authObject.expireDate = expiration;

		kind = node.getAttributeValue("kind");
		self._d("Account type: %s"%(kind))

		if kind == "paid":
			self.authObject.accountKind = 1;
		elif kind == "free":
			self.authObject.accountKind = 0;
		else:
			self.authObject.accountKind = -1;

		status = node.getAttributeValue("status");
		self._d("Account status: %s"%(status));

		if status == "expired":
			self.loginFailed.emit()
			raise Exception("Account expired on "+str(self.authObject.expireDate));

		if status == "active":
			if expiration is None:
				#raise Exception ("active account with no expiration");
				'''@@TODO expiration changed to creation'''
		else:
			self.authObject.accountKind = 1;

		self.conn.reader.inn.buf = [];

		self.conn.writer.outputKey = self.outputKey
		self.authObject.authenticationComplete()
		return 1


class RC4:
	def __init__(self, key, drop):
		self.s = []
		self.i = 0;
		self.j = 0;
		
		self.s = [0] * 256
		
		for i in range(0, len(self.s)):
			self.s[i] = i
		
		for i in range(0, len(self.s)):
			self.j = (self.j + self.s[i] + ord(key[i % len(key)])) % 256
			RC4.swap(self.s, i, self.j)
		
		self.j = 0;
		
		self.cipher(_bytearray(drop), 0, drop)
	
	
	def cipher(self, data, offset, length):
		while True:
			num = length
			length = num - 1
			
			if num == 0: break
			
			self.i = (self.i+1) % 256
			self.j = (self.j + self.s[self.i]) % 256
			
			RC4.swap(self.s, self.i, self.j)
			
			num2 = offset
			offset = num2 + 1
			
			data[num2] = ord(data[num2]) if type(data[num2]) == str else data[num2]
			data[num2] = (data[num2] ^ self.s[(self.s[self.i] + self.s[self.j]) % 256])
	
	@staticmethod
	def swap(arr, i, j):
		tmp = arr[i]
		arr[i] = arr[j]
		arr[j] = tmp


if sys.version_info >= (3, 0):
	buffer = lambda x: bytes(x, 'iso-8859-1') if type(x) is str else bytes(x)
	_bytearray = lambda x: [0]*x if type(x) is int else x


class KeyStream:

	def __init__(self, key):
		self.key = key if sys.version_info < (3, 0) else bytes(key, 'iso-8859-1')
		self.rc4 = RC4(key, 256)

	def decodeMessage(self, bufdata, macOffset, offset, length):

		buf = bufdata[:]
		#hashed = hmac.new(buffer(self.key), buffer(_bytearray(buf[offset:])), sha1)
		hashed = hmac.new(self.key, bytes(buf[offset:]), sha1)
		numArray = hashed.digest()

		numArray = [ord(x) for x in numArray.decode('iso-8859-1')];

		rest2 = bufdata[0:offset]
		rest2.extend(numArray)

		num = 0
		while num < 4:
			if buf[macOffset + num] == rest2[num]:
				num += 1
			else:
				raise Exception("INVALID MAC")

		self.rc4.cipher(buf, offset, length)

		return [x for x in buf]

	def encodeMessage(self, buf, macOffset, offset, length):
		#buf = _bytearray(buf)
		self.rc4.cipher(buf, offset, length)

		#hashed = hmac.new(buffer(self.key), buffer(_bytearray(buf[offset:length+offset])), sha1)

		hashed = hmac.new(self.key, buffer("".join(map(chr, buf[offset:length+offset]))), sha1)
		#hashed = hmac.new(self.key, bytes(buf[offset:length+offset]), sha1)
		
		
		
		numArray = hashed.digest()#binascii.b2a_base64(hashed.digest())[:-1]
		numArray = [ord(x) for x in numArray.decode('iso-8859-1')]
		
		for i in range(0,4):
			buf[macOffset + i] = numArray[i]

		return [x for x in buf]

	@staticmethod
	def keyFromPasswordAndNonce(password, nonce):
		
		if sys.version_info < (3, 0):
			k = KeyStream.pbkdf2(password, nonce, 16, 20)
		else:

			k = KeyStream.pbkdf2(password, nonce.encode('iso-8859-1'), 16, 20)

		return k

	@staticmethod
	def pbkdf2( password, salt, itercount, keylen, hashfn = hashlib.sha1 ):
	
		def pbkdf2_F( h, salt, itercount, blocknum ):
	
			def prf( h, data ):
				hm = h.copy()
				hm.update( buffer(_bytearray(data)) )
				#hm.update(bytes(data))
				d = hm.digest()
				
				#return map(ord, d)
				#print (hm.digest())
				
				#if sys.version_info < (3, 0):
				return [ord(i) for i in d.decode('iso-8859-1')]
	
			
			U = prf( h, salt + pack('>i',blocknum ) )
			T = U
	
			for i in range(2, itercount+1):
				U = prf( h, U )
				T = starmap(xor, zip(T, U))
	
			return T
	
		digest_size = hashfn().digest_size
		l = int(keylen / digest_size)
		if keylen % digest_size != 0:
			l += 1
	
		h = hmac.new( password, None, hashfn )
	
		T = []
		for i in range(1, l+1):
			tmp = pbkdf2_F( h, salt, itercount, i )
			#tmp = map(chr, tmp)
			#print(tmp)
			#for item in tmp:
			#	print(item)
			#sys.exit(1)
			T.extend(tmp)
			
		#print(T)
		#sys.exit()
		T = [chr(i) for i in T]
		return "".join(T[0: keylen])
########NEW FILE########
__FILENAME__ = constants
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

class Constants:
	'''dictionary = [ None, None, None, None, None,  "1", "1.0", "ack", "action", "active", "add", "all", "allow", "apple", "audio", "auth", "author",
			"available", "bad-request", "base64", "Bell.caf", "bind", "body", "Boing.caf", "cancel", "category", "challenge", "chat", "clean",
			"code", "composing", "config", "conflict", "contacts", "create", "creation", "default", "delay", "delete", "delivered", "deny",
			"DIGEST-MD5", "DIGEST-MD5-1", "dirty", "en", "enable", "encoding", "error", "expiration", "expired", "failure", "false", "favorites",
			"feature", "field", "free", "from", "g.us", "get", "Glass.caf", "google", "group", "groups", "g_sound", "Harp.caf",
			"http://etherx.jabber.org/streams", "http://jabber.org/protocol/chatstates", "id", "image", "img", "inactive", "internal-server-error",
			"iq", "item", "item-not-found", "jabber:client", "jabber:iq:last", "jabber:iq:privacy", "jabber:x:delay", "jabber:x:event", "jid",
			"jid-malformed", "kind", "leave", "leave-all", "list", "location", "max_groups", "max_participants", "max_subject", "mechanism", "mechanisms",
			"media", "message", "message_acks", "missing", "modify", "name", "not-acceptable", "not-allowed", "not-authorized", "notify", "Offline Storage",
			"order", "owner", "owning", "paid", "participant", "participants", "participating", "fail", "paused", "picture", "ping", "PLAIN", "platform",
			"presence", "preview", "probe", "prop", "props", "p_o", "p_t", "query", "raw", "receipt", "receipt_acks", "received", "relay", "remove",
			"Replaced by new connection", "request", "resource", "resource-constraint", "response", "result", "retry", "rim", "s.whatsapp.net", "seconds",
			"server", "session", "set", "show", "sid", "sound", "stamp", "starttls", "status", "stream:error", "stream:features", "subject", "subscribe",
			"success", "system-shutdown", "s_o", "s_t", "t", "TimePassing.caf", "timestamp", "to", "Tri-tone.caf", "type", "unavailable", "uri", "url",
			"urn:ietf:params:xml:ns:xmpp-bind", "urn:ietf:params:xml:ns:xmpp-sasl", "urn:ietf:params:xml:ns:xmpp-session", "urn:ietf:params:xml:ns:xmpp-stanzas",
			"urn:ietf:params:xml:ns:xmpp-streams", "urn:xmpp:delay", "urn:xmpp:ping", "urn:xmpp:receipts", "urn:xmpp:whatsapp", "urn:xmpp:whatsapp:dirty",
			"urn:xmpp:whatsapp:mms", "urn:xmpp:whatsapp:push", "value", "vcard", "version", "video", "w", "w:g", "w:p:r", "wait", "x", "xml-not-well-formed",
			"xml:lang", "xmlns", "xmlns:stream", "Xylophone.caf", "account", "digest", "g_notify", "method", "password", "registration", "stat", "text", "user",
			"username", "event", "latitude", "longitude", "true", "after", "before", "broadcast", "count", "features", "first", "index", "invalid-mechanism",
			"last", "max", "offline", "proceed", "required", "sync", "elapsed", "ip", "microsoft", "mute", "nokia", "off", "pin", "pop_mean_time", "pop_plus_minus",
			"port", "reason", "server-error", "silent", "timeout", "lc", "lg", "bad-protocol", "none", "remote-server-timeout", "service-unavailable", "w:p", "w:profileicture",
			"notification" ]
	'''

	dictionary = [None, None, None, None, None, "account", "ack", "action", "active", "add", "after", "ib", "all", "allow", "apple", "audio", "auth", "author", "available", "bad-protocol", "bad-request", "before", "Bell.caf", "body", "Boing.caf", "cancel", "category", "challenge", "chat", "clean", "code", "composing", "config", "conflict", "contacts", "count", "create", "creation", "default", "delay", "delete", "delivered", "deny", "digest", "DIGEST-MD5-1", "DIGEST-MD5-2", "dirty", "elapsed", "broadcast", "enable", "encoding", "duplicate", "error", "event", "expiration", "expired", "fail", "failure", "false", "favorites", "feature", "features", "field", "first", "free", "from", "g.us", "get", "Glass.caf", "google", "group", "groups", "g_notify", "g_sound", "Harp.caf", "http://etherx.jabber.org/streams", "http://jabber.org/protocol/chatstates", "id", "image", "img", "inactive", "index", "internal-server-error", "invalid-mechanism", "ip", "iq", "item", "item-not-found", "user-not-found", "jabber:iq:last", "jabber:iq:privacy", "jabber:x:delay", "jabber:x:event", "jid", "jid-malformed", "kind", "last", "latitude", "lc", "leave", "leave-all", "lg", "list", "location", "longitude", "max", "max_groups", "max_participants", "max_subject", "mechanism", "media", "message", "message_acks", "method", "microsoft", "missing", "modify", "mute", "name", "nokia", "none", "not-acceptable", "not-allowed", "not-authorized", "notification", "notify", "off", "offline", "order", "owner", "owning", "paid", "participant", "participants", "participating", "password", "paused", "picture", "pin", "ping", "platform", "pop_mean_time", "pop_plus_minus", "port", "presence", "preview", "probe", "proceed", "prop", "props", "p_o", "p_t", "query", "raw", "reason", "receipt", "receipt_acks", "received", "registration", "relay", "remote-server-timeout", "remove", "Replaced by new connection", "request", "required", "resource", "resource-constraint", "response", "result", "retry", "rim", "s.whatsapp.net", "s.us", "seconds", "server", "server-error", "service-unavailable", "set", "show", "sid", "silent", "sound", "stamp", "unsubscribe", "stat", "status", "stream:error", "stream:features", "subject", "subscribe", "success", "sync", "system-shutdown", "s_o", "s_t", "t", "text", "timeout", "TimePassing.caf", "timestamp", "to", "Tri-tone.caf", "true", "type", "unavailable", "uri", "url", "urn:ietf:params:xml:ns:xmpp-sasl", "urn:ietf:params:xml:ns:xmpp-stanzas", "urn:ietf:params:xml:ns:xmpp-streams", "urn:xmpp:delay", "urn:xmpp:ping", "urn:xmpp:receipts", "urn:xmpp:whatsapp", "urn:xmpp:whatsapp:account", "urn:xmpp:whatsapp:dirty", "urn:xmpp:whatsapp:mms", "urn:xmpp:whatsapp:push", "user", "username", "value", "vcard", "version", "video", "w", "w:g", "w:p", "w:p:r", "w:profile:picture", "wait", "x", "xml-not-well-formed", "xmlns", "xmlns:stream", "Xylophone.caf", "1", "WAUTH-1"]

	host = "c2.whatsapp.net"
	port = 443
	domain = "s.whatsapp.net"

	v="0.82"

	tokenData = {
		"v": "2.12.15",
		"r": "S40-2.12.15",
		"u": "WhatsApp/2.12.15 S40Version/14.26 Device/Nokia302",
		"t": "PdA2DJyKoUrwLw1Bg6EIhzh502dF9noR9uFCllGk1391039105258{phone}",
		"d": "Nokia302"
	}

	tokenStorage = "~/.yowsup/t_%s"%(v.replace(".", "_"))
	tokenSource = ("openwhatsapp.org", "/t")

	#t



########NEW FILE########
__FILENAME__ = datastructures
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''


class ByteArray():
	def __init__(self,size=0):
		self.size = size;
		self.buf = [0] * size#bytearray(size);

	def toByteArray(self):
		res = ByteArray();
		for b in self.buf:
			res.buf.append(b);

		return res;

	def reset(self):
		self.buf = [0] * self.size;

	def getBuffer(self):
		return self.buf

	def read(self):
		return self.buf.pop(0);

	def read2(self,b,off,length):
		'''reads into a buffer'''
		if off < 0 or length < 0 or (off+length)>len(b):
			raise Exception("Out of bounds");

		if length == 0:
			return 0;

		if b is None:
			raise Exception("XNull pointerX");

		count = 0;

		while count < length:

			#self.read();
			#print "OKIIIIIIIIIIII";
			#exit();
			b[off+count]=self.read();
			count= count+1;


		return count;

	def write(self,data):
		if type(data) is int:
			self.writeInt(data);
		elif type(data) is chr:
			self.buf.append(ord(data));
		elif type(data) is str:
			self.writeString(data);
		elif type(data) is list:
			self.writeByteArray(data);
		else:
			raise Exception("Unsupported datatype "+str(type(data)));

	def writeByteArray(self,b):
		for i in b:
			self.buf.append(i);

	def writeInt(self,integer):
		self.buf.append(integer);

	def writeString(self,string):
		for c in string:
			self.writeChar(c);

	def writeChar(self,char):
		self.buf.append(ord(char))


########NEW FILE########
__FILENAME__ = debugger
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import time

class Debugger():
	enabled = True
	def __init__(self):
		
		cname = self.__class__.__name__
		self.type= cname[:cname.index("Debug")]
	
	@staticmethod
	def attach(instance):
		d = Debugger()
		d.type = instance.__class__.__name__;
		instance._d = d.d
	
	@staticmethod
	def stdDebug(message,messageType="General"):
		#enabledTypes = ["general","stanzareader","sql","conn","waxmpp","wamanager","walogin","waupdater","messagestore"];
		
		if not Debugger.enabled:
			return
		
		disabledTypes = ["sql"]
		if messageType.lower() not in disabledTypes:
			try:
				print(message)
			except UnicodeEncodeError:
				print ("Skipped debug message because of UnicodeDecodeError")
	
	def formatMessage(self,message):
		#default = "{type}:{time}:\t{message}"
		t = time.time()
		message = "%s:\t%s"%(self.type,message)
		return message
	
	def debug(self,message):
		if Debugger.enabled:
			Debugger.stdDebug(self.formatMessage(message),self.type)
		
	def d(self,message):
		self.debug(message)
########NEW FILE########
__FILENAME__ = warequest
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import urllib,sys, os

if sys.version_info < (3, 0):
	import httplib
	from urllib import urlencode
else:
	from http import client as httplib
	from urllib.parse import urlencode

import hashlib
from .waresponseparser import ResponseParser
from Yowsup.Common.debugger import Debugger as WADebug
from Yowsup.Common.constants import Constants
from Yowsup.Common.utilities import Utilities

class WARequest(object):

	OK = 200

	#moved to Constants

	def __init__(self):
		WADebug.attach(self)

		self.pvars = [];
		self.port = 443;
		self.type = "GET"
		self.parser = None
		self.params = []
		self.headers = {}

		self.sent = False
		self.response = None



	def setParsableVariables(self, pvars):
		self.pvars = pvars;

	def onResponse(self, name, value):
		if name == "status":
			self.status = value
		elif name == "result":
			self.result = value

	def addParam(self,name,value):
		self.params.append((name,value.encode('utf-8')))

	def removeParam(self, name):
		for i in range(0, len(self.params)):
			if self.params[i][0] == name:
				del self.params[i]


	def addHeaderField(self, name, value):
		self.headers[name] = value;

	def clearParams(self):
		self.params = []

	def getUserAgent(self):

		tokenData = Utilities.readToken()

		if tokenData:
			agent = tokenData["u"]
		else:
			agent = Constants.tokenData["u"]
		return agent

	def getToken(self, phone, token):
		return hashlib.md5(token.format(phone=phone).encode()).hexdigest()

	def send(self, parser = None):

		if self.type == "POST":
			return self.sendPostRequest(parser)

		return self.sendGetRequest(parser)

	def setParser(self, parser):
		if isinstance(parser, ResponseParser):
			self.parser = parser
		else:
			self._d("Invalid parser")

	def getConnectionParameters(self):

		if not self.url:
			return ("", "", self.port)

		try:
			url = self.url.split("://", 1)
			url = url[0] if len(url) == 1 else url[1]

			host, path = url.split('/', 1)
		except ValueError:
			host = url
			path = ""

		path = "/" + path

		return (host, self.port, path)

	def sendGetRequest(self, parser = None):
		self.response = None
		params =  self.params#[param.items()[0] for param in self.params];

		parser = parser or self.parser or ResponseParser()

		headers = dict(list({"User-Agent":self.getUserAgent(),
				"Accept": parser.getMeta()
			}.items()) + list(self.headers.items()));

		host,port,path = self.getConnectionParameters()
		self.response = WARequest.sendRequest(host, port, path, headers, params, "GET")

		if not self.response.status == WARequest.OK:
			self._d("Request not success, status was %s"%self.response.status)
			return {}

		data = self.response.read()
		self._d(data);

		self.sent = True
		return parser.parse(data.decode(), self.pvars)

	def sendPostRequest(self, parser = None):
		self.response = None
		params =  self.params #[param.items()[0] for param in self.params];

		parser = parser or self.parser or ResponseParser()

		headers = dict(list({"User-Agent":self.getUserAgent(),
				"Accept": parser.getMeta(),
				"Content-Type":"application/x-www-form-urlencoded"
			}.items()) + list(self.headers.items()));

		host,port,path = self.getConnectionParameters()
		self.response = WARequest.sendRequest(host, port, path, headers, params, "POST")


		if not self.response.status == WARequest.OK:
			self._d("Request not success, status was %s"%self.response.status)
			return {}

		data = self.response.read()

		self._d(data);

		self.sent = True
		return parser.parse(data.decode(), self.pvars)


	@staticmethod
	def sendRequest(host, port, path, headers, params, reqType="GET"):

		params = urlencode(params);


		path = path + "?"+ params if reqType == "GET" and params else path

		if len(headers):
			WADebug.stdDebug(headers)
		if len(params):
			WADebug.stdDebug(params)

		WADebug.stdDebug("Opening connection to %s" % host);

		conn = httplib.HTTPSConnection(host ,port) if port == 443 else httplib.HTTPConnection(host ,port)

		WADebug.stdDebug("Sending %s request to %s" % (reqType, path))
		conn.request(reqType, path, params, headers);

		response = conn.getresponse()

		return response

########NEW FILE########
__FILENAME__ = waresponseparser
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import json, sys
from xml.dom import minidom
import plistlib

class ResponseParser(object):
	def __init__(self):
		self.meta = "*"
		
	def parse(self, text, pvars):
		return text
	
	def getMeta(self):
		return self.meta
	
	
	def getVars(self, pvars):

		if type(pvars) is dict:
			return pvars

		if type(pvars) is list:
			
			out = {}
			
			for p in pvars:
				out[p] = p
				
			return out

class XMLResponseParser(ResponseParser):
	
	def __init__(self):
		
		try:
			import libxml2
		except ImportError:
			print("libxml2 XMLResponseParser requires libxml2")
			sys.exit(1)

		self.meta = "text/xml";

	def parse(self, xml, pvars):
		import libxml2
		doc = libxml2.parseDoc(xml)
		
		pvars = self.getVars(pvars)
		vals = {}
		for k, v in pvars.items():
			res = doc.xpathEval(v)
			vals[k] = []
			for r in res:
				
				#if not vals.has_key(r.name):
				#	vals[r.name] = []
				
				if r.type == 'element':
					#vals[r.name].append(self.xmlToDict(minidom.parseString(str(r)))[r.name])
					vals[k].append(self.xmlToDict(minidom.parseString(str(r)))[r.name])
				elif r.type == 'attribute':
					vals[k].append(r.content)
				else:
					print("UNKNOWN TYPE")
			
			if len(vals[k]) == 1:
				vals[k] = vals[k][0]
			elif len(vals[k]) == 0:
				vals[k] = None

		return vals
	
	def xmlToDict(self, xmlNode):
		if xmlNode.nodeName == "#document":
			
			node = {xmlNode.firstChild.nodeName:{}}
			
			node[xmlNode.firstChild.nodeName] = self.xmlToDict(xmlNode.firstChild)
			return node
		
		node = {}
		curr = node
		
		if xmlNode.attributes:
			for name, value in xmlNode.attributes.items():
				curr[name] = value

		for n in xmlNode.childNodes:
			
			if n.nodeType == n.TEXT_NODE:
				curr["__TEXT__"] = n.data
				continue
			
			if not n.nodeName in curr:
				curr[n.nodeName] = []

			if len(xmlNode.getElementsByTagName(n.nodeName)) > 1:
				#curr[n.nodeName] = []
				curr[n.nodeName].append(self.xmlToDict(n))
			else:
				curr[n.nodeName] = self.xmlToDict(n)
			
			
		return node

class JSONResponseParser(ResponseParser):
	
	def __init__(self):
		self.meta = "text/json"

	def parse(self, jsonData, pvars):
		
		d = json.loads(jsonData)
		pvars = self.getVars(pvars)
		
		parsed = {}		
		
		for k,v in pvars.items():
			parsed[k] = self.query(d, v)

		return parsed
	
	def query(self, d, key):
		keys = key.split('.', 1)
			
		currKey = keys[0]
		
		if(currKey in d):
			item = d[currKey]
			
			if len(keys) == 1:
					return item
			
			if type(item) is dict:
				return self.query(item, keys[1])
			
			elif type(item) is list:
				output = []

				for i in item:
					output.append(self.query(i, keys[1]))
				return output
			
			else:
				return None

class PListResponseParser(ResponseParser):
	def __init__(self):
		self.meta = "text/xml"
	
	def parse(self, xml, pvars):
		
		#tmp = minidom.parseString(xml)
		
		if sys.version_info >= (3, 0):
			pl = plistlib.readPlistFromBytes(xml.encode());
		else:
			pl = plistlib.readPlistFromString(xml);
		
		parsed= {}
		pvars = self.getVars(pvars)
		
		for k,v in pvars.items():
			parsed[k] = pl[k] if  k in pl else None
		
		return parsed;
		

########NEW FILE########
__FILENAME__ = utilities
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import hashlib, string, os, base64, ast, sys
from Yowsup.Common.constants import Constants
class Utilities:

	tokenCacheEnabled = True

	@staticmethod
	def processIdentity(identifier):
		try:
			identifier.index(":")
			identifier = identifier.upper()
			identifier = identifier + identifier

		except:
			identifier = identifier[::-1]

		digest = hashlib.md5(identifier.encode("utf-8"))
		return digest.hexdigest()

	@staticmethod
	def decodeString(encoded):
		return "".join(map(chr,  map(lambda x: x ^ 19, encoded)))


	@staticmethod
	def persistToken(token):
		tPath = os.path.expanduser(Constants.tokenStorage)
		dirname = os.path.dirname(tPath)

		if not os.path.exists(dirname):
			os.makedirs(dirname)

		with open(tPath, "w") as out:
			out.write(base64.b64encode(token).decode())

	@staticmethod
	def readToken():
		if not Utilities.tokenCacheEnabled:
			return None

		token = None
		tPath = os.path.expanduser(Constants.tokenStorage)

		if os.path.exists(tPath):
			with open(tPath, "r") as f:
				tdec = base64.b64decode(f.readline().encode()).decode()
				token = ast.literal_eval(tdec)

		return token

	@staticmethod
	def str( number, radix ):
		"""str( number, radix ) -- reverse function to int(str,radix) and long(str,radix)"""

		if not 2 <= radix <= 36:
			raise ValueError("radix must be in 2..36")

		abc = string.digits + string.ascii_letters

		result = ''

		if number < 0:
			number = -number
			sign = '-'
		else:
			sign = ''

		while True:
			number, rdigit = divmod( number, radix )
			result = abc[rdigit] + result
			if number == 0:
				return sign + result

########NEW FILE########
__FILENAME__ = watime
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import time,datetime,re
try:
	from dateutil import tz
except ImportError:
	from .dateutil import tz

class WATime():
	def parseIso(self,iso):
		d=datetime.datetime(*map(int, re.split('[^\d]', iso)[:-1]))
		return d
		
	def utcToLocal(self,dt):
		utc = tz.gettz('UTC');
		local = tz.tzlocal()
		dtUtc =  dt.replace(tzinfo=utc);
		
		return dtUtc.astimezone(local)

	def utcTimestamp(self):
		#utc = tz.gettz('UTC')
		utcNow = datetime.datetime.utcnow()
		return self.datetimeToTimestamp(utcNow)
	
	def datetimeToTimestamp(self,dt):
		return time.mktime(dt.timetuple());
	

########NEW FILE########
__FILENAME__ = bintreenode
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

from Yowsup.Common.debugger import Debugger
from Yowsup.Common.datastructures import ByteArray
from Yowsup.Common.constants import Constants


from .protocoltreenode import ProtocolTreeNode
from .ioexceptions import InvalidReadException

class BinTreeNodeReader():
    def __init__(self,inputstream):
        
        Debugger.attach(self)

        self.inputKey = None
        
        self._d('Reader init');
        self.tokenMap = Constants.dictionary;
        self.rawIn = inputstream;
        self.inn = ByteArray();
        self.buf = []#bytearray(1024);
        self.bufSize = 0;
        self.readSize = 1;
        

    def readStanza(self):

        num = self.readInt8(self.rawIn)
        stanzaSize = self.readInt16(self.rawIn,1);

        header = (num << 16) + stanzaSize#self.readInt24(self.rawIn)
        
        flags = (header >> 20);
        #stanzaSize =  ((header & 0xF0000) >> 16) | ((header & 0xFF00) >> 8) | (header & 0xFF);
        isEncrypted = ((flags & 8) != 0)
        
        self.fillBuffer(stanzaSize);
        
        if self.inputKey is not None and isEncrypted:
            #self.inn.buf = bytearray(self.inn.buf)
            self.inn.buf = self.inputKey.decodeMessage(self.inn.buf, 0, 4, len(self.inn.buf)-4)[4:]

    def streamStart(self):

        self.readStanza();
        
        tag = self.inn.read();
        size = self.readListSize(tag);
        tag = self.inn.read();
        if tag != 1:
            raise Exception("expecting STREAM_START in streamStart");
        attribCount = (size - 2 + size % 2) / 2;
        self.readAttributes(attribCount);
    
    def readInt8(self,i):
        return i.read();
        
    def readInt16(self,i,socketOnly=0):
        intTop = i.read(socketOnly);
        intBot = i.read(socketOnly);
        #Utilities.debug(str(intTop)+"------------"+str(intBot));
        value = (intTop << 8) + intBot;
        if value is not None:
            return value;
        else:
            return "";
    
    
    def readInt24(self,i):
        int1 = i.read();
        int2 = i.read();
        int3 = i.read();
        value = (int1 << 16) + (int2 << 8) + (int3 << 0);
        return value;
        

    
    def readListSize(self,token):
        size = 0;
        if token == 0:
            size = 0;
        else:
            if token == 248:
                size = self.readInt8(self.inn);
            else:
                if token == 249:
                    size = self.readInt16(self.inn);
                else:
                    #size = self.readInt8(self.inn);
                    raise Exception("invalid list size in readListSize: token " + str(token));
        return size;
    
    def readAttributes(self,attribCount):
        attribs = {};
        
        for i in range(0, int(attribCount)):
            key = self.readString(self.inn.read());
            value = self.readString(self.inn.read());
            attribs[key]=value;
        return attribs;
    
    def getToken(self,token):
        if (token >= 0 and token < len(self.tokenMap)):
            ret = self.tokenMap[token];
        else:
            raise Exception("invalid token/length in getToken %i "%token);
        
        return ret;
        
    
    def readString(self,token):
        
        if token == -1:
            raise Exception("-1 token in readString");
        
        if token > 4 and token < 245:
            return self.getToken(token);
        
        if token == 0:
            return None;
            

        if token == 252:
            size8 = self.readInt8(self.inn);
            buf8 = [0] * size8;
            
            self.fillArray(buf8,len(buf8),self.inn);
            #print self.inn.buf;
            return "".join(map(chr, buf8));
            #return size8;
            
        
        if token == 253:
            size24 = self.readInt24(self.inn);
            buf24 = [0] * size24;
            self.fillArray(buf24,len(buf24),self.inn);
            return "".join(map(chr, buf24));
            
        if token == 254:
            token = self.inn.read();
            return self.getToken(245+token);
        if token == 250:
            user = self.readString(self.inn.read());
            server = self.readString(self.inn.read());
            if user is not None and server is not None:
                return user + "@" + server;
            if server is not None:
                return server;
            raise Exception("readString couldn't reconstruct jid");
        
        raise Exception("readString couldn't match token "+str(token));
        
    def nextTree(self):
        self.inn.buf = [];
        
        self.readStanza();
        
        ret = self.nextTreeInternal();
        self._d("Incoming")
        if ret is not None:
            if '<picture type="' in ret.toString():
                self._d("<Picture!!!>");
            else:
                self._d("\n%s"%ret.toString());
        return ret;
    
    def fillBuffer(self,stanzaSize):
        #if len(self.buf) < stanzaSize:
        #   newsize = stanzaSize#max(len(self.buf)*3/2,stanzaSize);

        self.buf = [0 for i in range(0,stanzaSize)]
        self.bufSize = stanzaSize;
        self.fillArray(self.buf, stanzaSize, self.rawIn);
        self.inn = ByteArray();
        self.inn.write(self.buf);
        
        #this.in = new ByteArrayInputStream(this.buf, 0, stanzaSize);
        #self.inn.setReadSize(stanzaSize);
        #Utilities.debug(str(len(self.buf))+":::"+str(stanzaSize));
    
    def fillArray(self, buf,length,inputstream):
        count = 0;
        while count < length:
            count+=inputstream.read2(buf,count,length-count);

    def nextTreeInternal(self):
        
        b = self.inn.read();
        
        size = self.readListSize(b);
        b = self.inn.read();
        if b == 2:
            return None;
        
        
        tag = self.readString(b);
        if size == 0 or tag is None:
            raise InvalidReadException("nextTree sees 0 list or null tag");
        
        attribCount = (size - 2 + size%2)/2;
        attribs = self.readAttributes(attribCount);
        if size % 2 ==1:
            return ProtocolTreeNode(tag,attribs);
            
        b = self.inn.read();

        if self.isListTag(b):
            return ProtocolTreeNode(tag,attribs,self.readList(b));
        
        return ProtocolTreeNode(tag,attribs,None,self.readString(b));
        
    def readList(self,token):
        size = self.readListSize(token);
        listx = []
        for i in range(0,size):
            listx.append(self.nextTreeInternal());
        
        return listx;    
        
    def isListTag(self,b):
        return (b == 248) or (b == 0) or (b == 249);



class BinTreeNodeWriter():
    STREAM_START = 1;
    STREAM_END = 2;
    LIST_EMPTY = 0;
    LIST_8 = 248;
    LIST_16 = 249;
    JID_PAIR = 250;
    BINARY_8 = 252;
    BINARY_24 = 253;
    TOKEN_8 = 254;
    #socket out; #FunXMPP.WAByteArrayOutputStream
    #socket realOut;
    tokenMap={}
    
    def __init__(self,o):
        Debugger.attach(self)

        self.outputKey = None

        dictionary = Constants.dictionary
        self.realOut = o;
        #self.out = o;
        self.tokenMap = {}
        self.out = ByteArray();
        #this.tokenMap = new Hashtable(dictionary.length);
        for i in range(0,len(dictionary)):
            if dictionary[i] is not None:
                self.tokenMap[dictionary[i]]=i
        
        #Utilities.debug(self.tokenMap);
        '''
        for (int i = 0; i < dictionary.length; i++)
            if (dictionary[i] != null)
                this.tokenMap.put(dictionary[i], new Integer(i));
        '''

    def streamStart(self,domain,resource):
        
        self.realOut.write(87);
        self.realOut.write(65);
        self.realOut.write(1);
        self.realOut.write(2);

        streamOpenAttributes  = {"to":domain,"resource":resource};
        self.writeListStart(len(streamOpenAttributes )*2+1);

        self.out.write(1);

        self.writeAttributes(streamOpenAttributes);
        self.flushBuffer(False);


    def write(self, node,needsFlush = 0):
        if node is None:
            self.out.write(0);
        else:
            self._d("Outgoing");
            self._d("\n %s" % node.toString());
            self.writeInternal(node);

        self.flushBuffer(needsFlush);
        self.out.buf = [];


    def processBuffer(self):
        buf = self.out.getBuffer()

        prep = [0,0,0]
        prep.extend(buf)

        length1 = len(self.out.buf)
        num = 0

        if self.outputKey is not None:
            num = 1
            prep.extend([0,0,0,0])
            length1 += 4

            #prep = bytearray(prep)
            res = self.outputKey.encodeMessage(prep, len(prep) - 4 , 3, len(prep)-4-3)

            res[0] = ((num << 4) | (length1 & 16711680) >> 16) % 256
            res[1] = ((length1 & 65280) >> 8) % 256
            res[2] = (length1 & 255) % 256

            self.out.buf = res

            return
        else:
            prep[0] = ((num << 4) | (length1 & 16711680) >> 16) % 256
            prep[1] = ((length1 & 65280) >> 8) % 256
            prep[2] = (length1 & 255) % 256
            self.out.buf = prep

    def flushBuffer(self, flushNetwork):
        '''define flush buffer here '''
        self.processBuffer()

        size = len(self.out.getBuffer());
        if (size & 0xFFFFF) != size:
            raise Exception("Buffer too large: "+str(size));

        #self.realOut.write(0)
        #self.writeInt16(size,self.realOut);


        self.realOut.write(self.out.getBuffer());
        self.out.reset();

        if flushNetwork:
            self.realOut.flush();

    def writeInternal(self,node):
        '''define write internal here'''
        
        x = 1 + (0 if node.attributes is None else len(node.attributes) * 2) + (0 if node.children is None else 1) + (0 if node.data is None else 1);
    
        self.writeListStart(1 + (0 if node.attributes is None else len(node.attributes) * 2) + (0 if node.children is None else 1) + (0 if node.data is None else 1));
        
        self.writeString(node.tag);
        self.writeAttributes(node.attributes);
        
        if node.data is not None:
            self.writeBytes(node.data)
            '''if type(node.data) == bytearray:
                self.writeBytes(node.data);
            else:
                self.writeBytes(bytearray(node.data));
            '''
        
        if node.children is not None:
            self.writeListStart(len(node.children));
            for c in node.children:
                self.writeInternal(c);
    
    
    def writeAttributes(self,attributes):
        if attributes is not None:
            for key, value in attributes.items():
                self.writeString(key);
                self.writeString(value);
        
        
    def writeBytes(self,bytes):

        length = len(bytes);
        if length >= 256:
            self.out.write(253);
            self.writeInt24(length);
        else:
            self.out.write(252);
            self.writeInt8(length);
            
        for b in bytes:
            self.out.write(b);
        
    def writeInt8(self,v):
        self.out.write(v & 0xFF);

    
    def writeInt16(self,v, o = None):
        if o is None:
            o = self.out;

        o.write((v & 0xFF00) >> 8);
        o.write((v & 0xFF) >> 0);

    
    def writeInt24(self,v):
        self.out.write((v & 0xFF0000) >> 16);
        self.out.write((v & 0xFF00) >> 8);
        self.out.write((v & 0xFF) >> 0);
    

    def writeListStart(self,i):
        #Utilities.debug("list start "+str(i));
        if i == 0:
            self.out.write(0)
        elif i < 256:
            self.out.write(248);
            self.writeInt8(i);#f
        else:
            self.out.write(249);
            #write(i >> 8 & 0xFF);
            self.writeInt16(i); #write(i >> 8 & 0xFF);
        
    def writeToken(self, intValue):
        if intValue < 245:
            self.out.write(intValue)
        elif intValue <=500:
            self.out.write(254)
            self.out.write(intValue - 245);
    
    def writeString(self,tag):
        try:
            key = self.tokenMap[tag];
            self.writeToken(key);
        except KeyError:
            try:

                at = '@'.encode() if type(tag) == bytes else '@'
                atIndex = tag.index(at);

                if atIndex < 1:
                    raise ValueError("atIndex < 1");
                else:
                    server = tag[atIndex+1:];
                    user = tag[0:atIndex];
                    #Utilities.debug("GOT "+user+"@"+server);
                    self.writeJid(user, server);

            except ValueError:
                self.writeBytes(self.encodeString(tag));

    def encodeString(self, string):
        res = [];
        
        if type(string) == bytes:
            for char in string:
                res.append(char)
        else:
            for char in string:
                res.append(ord(char))
        return res;
    
    def writeJid(self,user,server):
        self.out.write(250);
        if user is not None:
            self.writeString(user);
        else:
            self.writeToken(0);
        self.writeString(server);

        
    def getChild(self,string):
        if self.children is None:
            return None
        
        for c in self.children:
            if string == c.tag:
                return c;
        return None;
        
    def getAttributeValue(self,string):
        
        if self.attributes is None:
            return None;
        
        try:
            val = self.attributes[string]
            return val;
        except KeyError:
            return None;
 

########NEW FILE########
__FILENAME__ = connectionengine
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import socket;
import sys
from .bintreenode import BinTreeNodeReader, BinTreeNodeWriter

from Yowsup.Common.debugger import Debugger

from .ioexceptions import ConnectionClosedException

class ConnectionEngine(socket.socket):
	
	def __init__(self):
		Debugger.attach(self)

		self.reader = BinTreeNodeReader(self)
		self.writer = BinTreeNodeWriter(self)
		
		self.readSize = 1;
		self.buf = [];
		self.maxBufRead = 0;
		self.connected = 0
		
		self.jid = ""
		
		super(ConnectionEngine,self).__init__(socket.AF_INET, socket.SOCK_STREAM);

	def getId(self):
		return self.id


	def setId(self, idx):
		self.id = idx

	def flush(self):
		'''FLUSH'''
		self.write();
		
	def getBuffer(self):
		return self.buffer;
	
	
	
	def reset(self):
		self.buffer = "";		
	
	def write(self,data):
			
		if type(data) is int:
			try:
				self.sendall(chr(data)) if sys.version_info < (3, 0) else self.sendall(chr(data).encode('iso-8859-1'))
			except:
				self._d("socket 1 write crashed, reason: %s" % sys.exc_info()[1])
				raise ConnectionClosedException("socket 1 write crashed, reason: %s" % sys.exc_info()[1])
		else:
			tmp = "";
			
			for d in data:
				tmp += chr(d)

			try:
				self.sendall(tmp) if sys.version_info < (3, 0) else self.sendall(tmp.encode('iso-8859-1'))
			except:
				self._d("socket 2 write crashed, reason: %s" % sys.exc_info()[1])
				raise ConnectionClosedException("socket 2 write crashed, reason: %s" % sys.exc_info()[1])
		
		
	def setReadSize(self,size):
		self.readSize = size;

		
	def read(self, socketOnly = 0):
		x = ""
		try:
			x = self.recv(self.readSize)#.decode('iso-8859-1');
		except:
			self._d("socket read crashed, reason %s " % sys.exc_info()[1])
			raise ConnectionClosedException("socket read crashed, reason %s " % sys.exc_info()[1])

		#x= self.recvX(self.readSize);
		
		if len(x) == 1:
			#Utilities.debug("GOT "+str(ord((x))));
			return ord(x);
		else:
			raise ConnectionClosedException("Got 0 bytes, connection closed");
			#return x;
		
	def read2(self,b,off,length):
		'''reads into a buffer'''
		if off < 0 or length < 0 or (off+length)>len(b):
			raise Exception("Out of bounds");
		
		if length == 0:
			return 0;
		
		if b is None:
			raise Exception("XNull pointerX");
		
		count = 0;
		
		while count < length:
			
			#self.read();
			#print "OKIIIIIIIIIIII";
			#exit();
			b[off+count]=self.read(0);
			count= count+1;
		
	
		return count;

########NEW FILE########
__FILENAME__ = ioexceptions
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

class InvalidReadException(Exception):
    pass

class ConnectionClosedException(Exception):
    pass

########NEW FILE########
__FILENAME__ = protocoltreenode
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

from Yowsup.Common.debugger import Debugger


class ProtocolTreeNode():
	
	def __init__(self,tag,attributes,children=None,data=None):

		Debugger.attach(self)
		
		self.tag = tag;
		self.attributes = attributes;
		self.children = children;
		self.data = data
		
	def toString(self):
		try:
			out = "<"+self.tag;
			if self.attributes is not None:
				for key,val in self.attributes.items():
					out+= " "+key+'="'+val+'"'
			out+= ">\n";
			if self.data is not None:
				out += self.data;
			
			if self.children is not None:
				for c in self.children:
					out+=c.toString();
			#print sel
			out+= "</"+self.tag+">\n"
			return out
		except TypeError:
			print("ignored toString call, probably encountered byte")
		except UnicodeDecodeError:
			print("ingnored toString call, encountered unicode error")
		
		
	
	@staticmethod	
	def tagEquals(node,string):
		return node is not None and node.tag is not None and node.tag == string;
		
		
	@staticmethod
	def require(node,string):
		if not ProtocolTreeNode.tagEquals(node,string):
			raise Exception("failed require. string: "+string);
	
	
	def getChild(self,identifier):

		if self.children is None or len(self.children) == 0:
			return None
		if type(identifier) == int:
			if len(self.children) > identifier:
				return self.children[identifier]
			else:
				return None

		for c in self.children:
			if identifier == c.tag:
				return c;

		return None;
		
	def getAttributeValue(self,string):
		
		if self.attributes is None:
			return None;
		
		try:
			val = self.attributes[string]
			return val;
		except KeyError:
			return None;

	def getAllChildren(self,tag = None):
		ret = [];
		if self.children is None:
			return ret;
			
		if tag is None:
			return self.children
		
		for c in self.children:
			if tag == c.tag:
				ret.append(c)
		
		return ret;

		
	

########NEW FILE########
__FILENAME__ = connectionmanager
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

from Yowsup.ConnectionIO.protocoltreenode import ProtocolTreeNode
from Yowsup.ConnectionIO.ioexceptions import ConnectionClosedException
from Yowsup.ConnectionIO.connectionengine import ConnectionEngine
from Yowsup.Common.utilities import Utilities

from Yowsup.Common.debugger import Debugger
import threading, select, time
from Yowsup.Common.watime import WATime
from .Auth.auth import YowsupAuth
from Yowsup.Common.constants import Constants
from Yowsup.Interfaces.Lib.LibInterface import LibMethodInterface, LibSignalInterface
import tempfile
from random import randrange
import socket
import hashlib
import base64
import sys



import traceback
class YowsupConnectionManager:
	
	def __init__(self):
		Debugger.attach(self)
		self.currKeyId = 1
		self.iqId = 0
		self.verbose = True
		self.state = 0
		self.lock = threading.Lock()
		self.autoPong = True
		
		self.domain = "s.whatsapp.net"
	
		#self.methodInterface = MethodInterface(authenticatedSocketConnection.getId())
		#self.signalInterface = SignalInterface(authenticatedSocketConnection.getId())
		self.readerThread = None
		
		self.methodInterface = LibMethodInterface()
		self.signalInterface = LibSignalInterface()
		self.readerThread = ReaderThread()
		self.readerThread.setSignalInterface(self.signalInterface)
		

		self.bindMethods()
	
	
	def setInterfaces(self, signalInterface, methodInterface):
		self.methodInterface = methodInterface
		self.signalInterface = signalInterface
		
		self.readerThread.setSignalInterface(self.signalInterface)
		
		self.bindMethods()
		
	def getSignalsInterface(self):
		return self.signalInterface
	
	def getMethodsInterface(self):
		return self.methodInterface

	def setAutoPong(self, autoPong):
		self.autoPong = self.readerThread.autoPong = autoPong
	
	def startReader(self):
		if self.readerThread.isAlive():
			self._d("Reader already started")
			return 0

		self._d("starting reader")
		try:
			self.readerThread.start()
			self._d("started")
		except RuntimeError:
			self._d("Reader already started before")
			self.readerThread.sendDisconnected()
			return 0
		
		return 1
	
	
	def block(self):
		self.readerThread.join()

	def bindMethods(self):
		self.methodInterface.registerCallback("getVersion", lambda: Constants.v)
		self.methodInterface.registerCallback("message_send",self.sendText)
		self.methodInterface.registerCallback("message_imageSend",self.sendImage)
		self.methodInterface.registerCallback("message_audioSend",self.sendAudio)
		self.methodInterface.registerCallback("message_videoSend",self.sendVideo)
		self.methodInterface.registerCallback("message_locationSend",self.sendLocation)
		self.methodInterface.registerCallback("message_vcardSend",self.sendVCard)
		
		self.methodInterface.registerCallback("message_broadcast",self.sendBroadcast)

		self.methodInterface.registerCallback("message_ack",self.sendMessageReceipt)

		self.methodInterface.registerCallback("notification_ack", self.sendNotificationReceipt)
		
		self.methodInterface.registerCallback("clientconfig_send",self.sendClientConfig)

		self.methodInterface.registerCallback("delivered_ack",self.sendDeliveredReceiptAck)

		self.methodInterface.registerCallback("visible_ack",self.sendVisibleReceiptAck)

		self.methodInterface.registerCallback("ping",self.sendPing)
		self.methodInterface.registerCallback("pong",self.sendPong)

		self.methodInterface.registerCallback("typing_send",self.sendTyping)
		self.methodInterface.registerCallback("typing_paused",self.sendPaused)

		self.methodInterface.registerCallback("subject_ack",self.sendSubjectReceived)

		self.methodInterface.registerCallback("group_getGroups", self.sendGetGroups)
		self.methodInterface.registerCallback("group_getInfo",self.sendGetGroupInfo)
		self.methodInterface.registerCallback("group_create",self.sendCreateGroupChat)
		self.methodInterface.registerCallback("group_addParticipants",self.sendAddParticipants)
		self.methodInterface.registerCallback("group_removeParticipants",self.sendRemoveParticipants)
		self.methodInterface.registerCallback("group_end",self.sendEndGroupChat)
		self.methodInterface.registerCallback("group_setSubject",self.sendSetGroupSubject)
		self.methodInterface.registerCallback("group_setPicture", self.sendSetPicture)
		self.methodInterface.registerCallback("group_getPicture", self.sendGetPicture)
		
		self.methodInterface.registerCallback("group_getParticipants",self.sendGetParticipants)

		self.methodInterface.registerCallback("picture_get",self.sendGetPicture)
		self.methodInterface.registerCallback("picture_getIds",self.sendGetPictureIds)

		self.methodInterface.registerCallback("contact_getProfilePicture", self.sendGetPicture)

		self.methodInterface.registerCallback("status_update",self.sendChangeStatus)

		self.methodInterface.registerCallback("presence_request",self.getLastOnline)
		#self.methodInterface.registerCallback("presence_unsubscribe",self.sendUnsubscribe)#@@TODO implement method
		self.methodInterface.registerCallback("presence_subscribe",self.sendSubscribe)
		self.methodInterface.registerCallback("presence_sendAvailableForChat",self.sendAvailableForChat)
		self.methodInterface.registerCallback("presence_sendAvailable",self.sendAvailable)
		self.methodInterface.registerCallback("presence_sendUnavailable",self.sendUnavailable)
		
		
		self.methodInterface.registerCallback("profile_setPicture", self.sendSetProfilePicture)
		self.methodInterface.registerCallback("profile_getPicture", self.sendGetProfilePicture)
		
		self.methodInterface.registerCallback("profile_setStatus", self.sendChangeStatus)

		self.methodInterface.registerCallback("disconnect", self.disconnect)
		self.methodInterface.registerCallback("ready", self.startReader)
		
		self.methodInterface.registerCallback("auth_login", self.auth )
		#self.methodInterface.registerCallback("auth_login", self.auth)
		
		self.methodInterface.registerCallback("media_requestUpload", self.sendRequestUpload)


	def disconnect(self, reason=""):
		self._d("Disconnect sequence initiated")
		self._d("Sending term signal to reader thread")
		if self.readerThread.isAlive():
			self.readerThread.terminate()
			self._d("Shutting down socket")
			self.socket.close()
			self._d("Waiting for readerThread to die")
			self.readerThread.join()
		self._d("Disconnected!")
		self._d(reason)
		self.state = 0
		self.readerThread.sendDisconnected(reason)


	def getConnection(self):
		return self.socket

	def triggerEvent(self, eventName, stanza):
		if eventName in self.events and self.events[eventName] is not None:
			self.events[eventName](stanza)

	def bindEvent(self, eventName, callback):
		if eventName in self.events:
			self.events[eventName] = callback

	##########################################################

	def _writeNode(self, node):
		if self.state == 2:
			try:
				self.out.write(node)
				return True
			except ConnectionClosedException:
				self._d("CONNECTION DOWN")
				#self.disconnect("closed")
				if self.readerThread.isAlive():
					self.readerThread.terminate()
					self.readerThread.join()
					self.readerThread.sendDisconnected("closed")
		
		return False
		
	def onDisconnected(self):
		self._d("Setting state to 0")
		self.state = 0

	def auth(self, username, password):
		self._d(">>>>>>>>                         AUTH CALLED")
		username = str(username)
		#password = str(password)
		#traceback.print_stack()
		
		self.lock.acquire()
		if self.state == 0 :
		
			
			if self.readerThread.isAlive():
				raise Exception("TWO READER THREADS ON BOARD!!")
			
			self.readerThread = ReaderThread()
			self.readerThread.autoPong = self.autoPong
			self.readerThread.setSignalInterface(self.signalInterface)
			yAuth = YowsupAuth(ConnectionEngine())
			try:
				self.state = 1
				tokenData = Utilities.readToken()
				resource = tokenData["r"] if tokenData else Constants.tokenData["r"]
				connection = yAuth.authenticate(username, password, Constants.domain, resource)
			except socket.gaierror:
				self._d("DNS ERROR")
				self.readerThread.sendDisconnected("dns")
				#self.signalInterface.send("disconnected", ("dns",))
				self.lock.release()
				self.state = 0
				
				return 0
			except socket.error:
				self._d("Socket error, connection timed out")
				self.readerThread.sendDisconnected("closed")
				#self.signalInterface.send("disconnected", ("closed",))
				self.lock.release()
				self.state = 0
				
				return 0
			except ConnectionClosedException:
				self._d("Conn closed Exception")
				self.readerThread.sendDisconnected("closed")
				#self.signalInterface.send("disconnected", ("closed",))
				self.lock.release()
				self.state = 0
				
				return 0
		
			if not connection:
				self.state = 0
				self.signalInterface.send("auth_fail", (username, "invalid"))
				self.lock.release()
				return 0
			
			self.state = 2
			
			
	
			self.socket = connection
			self.jid = self.socket.jid
			#@@TODO REPLACE PROPERLY
			self.out = self.socket.writer
			
			self.readerThread.setSocket(self.socket)
			self.readerThread.disconnectedCallback = self.onDisconnected
			self.readerThread.onPing = self.sendPong
			self.readerThread.ping = self.sendPing
			
	
			self.signalInterface.send("auth_success", (username,))
		self.lock.release()
			
		
		
		
	def sendTyping(self,jid):
		self._d("SEND TYPING TO JID")
		composing = ProtocolTreeNode("composing",{"xmlns":"http://jabber.org/protocol/chatstates"})
		message = ProtocolTreeNode("message",{"to":jid,"type":"chat"},[composing]);
		self._writeNode(message);



	def sendPaused(self,jid):
		self._d("SEND PAUSED TO JID")
		composing = ProtocolTreeNode("paused",{"xmlns":"http://jabber.org/protocol/chatstates"})
		message = ProtocolTreeNode("message",{"to":jid,"type":"chat"},[composing]);
		self._writeNode(message);



	def getSubjectMessage(self,to,msg_id,child):
		messageNode = ProtocolTreeNode("message",{"to":to,"type":"subject","id":msg_id},[child]);

		return messageNode

	def sendSubjectReceived(self,to,msg_id):
		self._d("Sending subject recv receipt")
		receivedNode = ProtocolTreeNode("received",{"xmlns": "urn:xmpp:receipts"});
		messageNode = self.getSubjectMessage(to,msg_id,receivedNode);
		self._writeNode(messageNode);



	def sendMessageReceipt(self, jid, msgId):
		self.sendReceipt(jid, "chat", msgId)

	def sendNotificationReceipt(self, jid, notificationId):
		self.sendReceipt(jid, "notification", notificationId)

	def sendReceipt(self,jid,mtype,mid):
		self._d("sending message received to "+jid+" - type:"+mtype+" - id:"+mid)
		receivedNode = ProtocolTreeNode("received",{"xmlns": "urn:xmpp:receipts"})
		messageNode = ProtocolTreeNode("message",{"to":jid,"type":mtype,"id":mid},[receivedNode]);
		self._writeNode(messageNode);


	def sendDeliveredReceiptAck(self,to,msg_id):
		self._writeNode(self.getReceiptAck(to,msg_id,"delivered"));

	def sendVisibleReceiptAck(self,to,msg_id):
		self._writeNode(self.getReceiptAck(to,msg_id,"visible"));

	def getReceiptAck(self,to,msg_id,receiptType):
		ackNode = ProtocolTreeNode("ack",{"xmlns":"urn:xmpp:receipts","type":receiptType})
		messageNode = ProtocolTreeNode("message",{"to":to,"type":"chat","id":msg_id},[ackNode]);
		return messageNode;

	def makeId(self,prefix):
		self.iqId += 1
		idx = ""
		if self.verbose:
			idx += prefix + str(self.iqId);
		else:
			idx = "%x" % self.iqId

		return idx

	def sendPing(self):

		idx = self.makeId("ping_")

		self.readerThread.requests[idx] = self.readerThread.parsePingResponse;

		pingNode = ProtocolTreeNode("ping",{"xmlns":"w:p"});
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"get","to":self.domain},[pingNode]);
		self._writeNode(iqNode);
		return idx


	def sendPong(self,idx):
		iqNode = ProtocolTreeNode("iq",{"type":"result","to":self.domain,"id":idx})
		self._writeNode(iqNode);

	def getLastOnline(self,jid):

		if len(jid.split('-')) == 2 or jid == "Server@s.whatsapp.net": #SUPER CANCEL SUBSCRIBE TO GROUP AND SERVER
			return

		self.sendSubscribe(jid);

		self._d("presence request Initiated for %s"%(jid))
		idx = self.makeId("last_")
		self.readerThread.requests[idx] = self.readerThread.parseLastOnline;

		query = ProtocolTreeNode("query",{"xmlns":"jabber:iq:last"});
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"get","to":jid},[query]);
		self._writeNode(iqNode)


	def sendIq(self):
		node = ProtocolTreeNode("iq",{"to":"g.us","type":"get","id":str(int(time.time()))+"-0"},None,'expired');
		self._writeNode(node);

		node = ProtocolTreeNode("iq",{"to":"s.whatsapp.net","type":"set","id":str(int(time.time()))+"-1"},None,'expired');
		self._writeNode(node);

	def sendAvailableForChat(self, pushname):
		presenceNode = ProtocolTreeNode("presence",{"name":pushname})
		self._writeNode(presenceNode);

	def sendAvailable(self):
		presenceNode = ProtocolTreeNode("presence",{"type":"available"})
		self._writeNode(presenceNode);


	def sendUnavailable(self):
		presenceNode = ProtocolTreeNode("presence",{"type":"unavailable"})
		self._writeNode(presenceNode);


	def sendSubscribe(self,to):
		presenceNode = ProtocolTreeNode("presence",{"type":"subscribe","to":to});

		self._writeNode(presenceNode);


	def mediaNode(fn):
		def wrapped(self, *args):
				mediaType = fn(self, *args)
				
				
				url = args[1]
				name = args[2]
				size = args[3]
				
				mmNode = ProtocolTreeNode("media", {"xmlns":"urn:xmpp:whatsapp:mms","type":mediaType,"file":name,"size":size,"url":url},None, args[4:][0] if args[4:] else None);
				return mmNode
			
		return wrapped
	
	def sendMessage(fn):
			def wrapped(self, *args):
				node = fn(self, *args)
				jid = "broadcast" if type(args[0]) == list else args[0]
				messageNode = self.getMessageNode(jid, node)
				
				self._writeNode(messageNode);

				return messageNode.getAttributeValue("id")
			
			return wrapped
		
	def sendChangeStatus(self,status):
		self._d("updating status to: %s"%(status))
		
		bodyNode = ProtocolTreeNode("body",None,None,status);
		messageNode = self.getMessageNode("s.us",bodyNode)
		self._writeNode(messageNode);
		
		return messageNode.getAttributeValue("id")
		
		
	
	@sendMessage
	def sendText(self,jid, content):
		return ProtocolTreeNode("body",None,None,content);

	@sendMessage
	@mediaNode
	def sendImage(self, jid, url, name, size, preview):
		return "image"
	
	@sendMessage
	@mediaNode
	def sendVideo(self, jid, url, name, size, preview):
		return "video"
	
	@sendMessage
	@mediaNode
	def sendAudio(self, jid, url, name, size):
		return "audio"

	@sendMessage
	def sendLocation(self, jid, latitude, longitude, preview):
		self._d("sending location (" + latitude + ":" + longitude + ")")

		return ProtocolTreeNode("media", {"xmlns":"urn:xmpp:whatsapp:mms","type":"location","latitude":latitude,"longitude":longitude},None,preview)
		
	@sendMessage
	def sendVCard(self, jid, data, name):
		
		cardNode = ProtocolTreeNode("vcard",{"name":name},None,data);
		return ProtocolTreeNode("media", {"xmlns":"urn:xmpp:whatsapp:mms","type":"vcard"},[cardNode])
	
	@sendMessage
	def sendBroadcast(self, jids, content):
		
		broadcastNode = ProtocolTreeNode("broadcast", None, [ProtocolTreeNode("to", {"jid": jid}) for jid in jids])
		
		messageNode = ProtocolTreeNode("body",None,None,content);
		
		return [broadcastNode, messageNode]

	def sendClientConfig(self,sound,pushID,preview,platform):
		idx = self.makeId("config_");
		configNode = ProtocolTreeNode("config",{"xmlns":"urn:xmpp:whatsapp:push","sound":sound,"id":pushID,"preview":"1" if preview else "0","platform":platform})
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"set","to":self.domain},[configNode]);

		self._writeNode(iqNode);


	# gtype should be either "participating" or "owning"
	def sendGetGroups(self,gtype):
		self._d("getting groups %s"%(gtype))
		idx = self.makeId("get_groups_")
		self.readerThread.requests[idx] = self.readerThread.parseGroups;

		queryNode = ProtocolTreeNode("list",{"xmlns":"w:g","type":gtype})
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"get","to":"g.us"},[queryNode])

		self._writeNode(iqNode)


	def sendGetGroupInfo(self,jid):
		self._d("getting group info for %s"%(jid))
		idx = self.makeId("get_g_info_")
		self.readerThread.requests[idx] = self.readerThread.parseGroupInfo;

		queryNode = ProtocolTreeNode("query",{"xmlns":"w:g"})
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"get","to":jid},[queryNode])

		self._writeNode(iqNode)


	def sendCreateGroupChat(self,subject):
		self._d("creating group: %s"%(subject))
		idx = self.makeId("create_group_")
		self.readerThread.requests[idx] = self.readerThread.parseGroupCreated;

		queryNode = ProtocolTreeNode("group",{"xmlns":"w:g","action":"create","subject":subject})
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"set","to":"g.us"},[queryNode])

		self._writeNode(iqNode)


	def sendAddParticipants(self, gjid, participants):
		self._d("opening group: %s"%(gjid))
		self._d("adding participants: %s"%(participants))
		idx = self.makeId("add_group_participants_")
		self.readerThread.requests[idx] = self.readerThread.parseAddedParticipants;
		
		innerNodeChildren = []

		for part in participants:
			innerNodeChildren.append( ProtocolTreeNode("participant",{"jid":part}) )

		queryNode = ProtocolTreeNode("add",{"xmlns":"w:g"},innerNodeChildren)
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"set","to":gjid},[queryNode])

		self._writeNode(iqNode)


	def sendRemoveParticipants(self,gjid, participants):
		self._d("opening group: %s"%(gjid))
		self._d("removing participants: %s"%(participants))
		idx = self.makeId("remove_group_participants_")
		self.readerThread.requests[idx] = self.readerThread.parseRemovedParticipants;

		innerNodeChildren = []
		for part in participants:
			innerNodeChildren.append( ProtocolTreeNode("participant",{"jid":part}) )

		queryNode = ProtocolTreeNode("remove",{"xmlns":"w:g"},innerNodeChildren)
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"set","to":gjid},[queryNode])

		self._writeNode(iqNode)


	def sendEndGroupChat(self,gjid):
		self._d("removing group: %s"%(gjid))
		idx = self.makeId("leave_group_")
		self.readerThread.requests[idx] = self.readerThread.parseGroupEnded;

		innerNodeChildren = []
		innerNodeChildren.append( ProtocolTreeNode("group",{"id":gjid}) )

		queryNode = ProtocolTreeNode("leave",{"xmlns":"w:g"},innerNodeChildren)
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"set","to":"g.us"},[queryNode])

		self._writeNode(iqNode)

	def sendSetGroupSubject(self,gjid,subject):
		#subject = subject.encode('utf-8')
		#self._d("setting group subject of " + gjid + " to " + subject)
		idx = self.makeId("set_group_subject_")
		self.readerThread.requests[idx] = self.readerThread.parseGroupSubject

		queryNode = ProtocolTreeNode("subject",{"xmlns":"w:g","value":subject})
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"set","to":gjid},[queryNode]);

		self._writeNode(iqNode)


	def sendGetParticipants(self,jid):
		idx = self.makeId("get_participants_")
		self.readerThread.requests[idx] = self.readerThread.parseParticipants

		listNode = ProtocolTreeNode("list",{"xmlns":"w:g"})
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"get","to":jid},[listNode]);

		self._writeNode(iqNode)


	def sendGetPicture(self,jid):
		self._d("GETTING PICTURE FROM " + jid)
		idx = self.makeId("get_picture_")

		#@@TODO, ?!
		self.readerThread.requests[idx] =  self.readerThread.parseGetPicture

		listNode = ProtocolTreeNode("picture",{"xmlns":"w:profile:picture","type":"image"})
		iqNode = ProtocolTreeNode("iq",{"id":idx,"to":jid,"type":"get"},[listNode]);

		self._writeNode(iqNode)



	def sendGetPictureIds(self,jids):
		idx = self.makeId("get_picture_ids_")
		self.readerThread.requests[idx] = self.readerThread.parseGetPictureIds

		innerNodeChildren = []
		for jid in jids:
			innerNodeChildren.append( ProtocolTreeNode("user",{"jid": jid}) )

		queryNode = ProtocolTreeNode("list",{"xmlns":"w:profile:picture"},innerNodeChildren)
		iqNode = ProtocolTreeNode("iq",{"id":idx,"type":"get"},[queryNode])

		self._writeNode(iqNode)

	
	def sendGetProfilePicture(self):
		return self.sendGetPicture(self.jid)
	
	def sendSetProfilePicture(self, filepath):
		return self.sendSetPicture(self.jid, filepath)
	
	def sendSetPicture(self, jid, imagePath):

		f = open(imagePath, 'rb')
		imageData = f.read()
		imageData = bytearray(imageData)
		f.close()
		
		idx = self.makeId("set_picture_")
		self.readerThread.requests[idx] = self.readerThread.parseSetPicture

		listNode = ProtocolTreeNode("picture",{"xmlns":"w:profile:picture","type":"image"}, None, imageData)

		iqNode = ProtocolTreeNode("iq",{"id":idx,"to":jid,"type":"set"},[listNode])

		self._writeNode(iqNode)

	
	def sendRequestUpload(self, b64Hash, t, size, b64OrigHash = None):
		idx = self.makeId("upload_")
		
		self.readerThread.requests[idx] = lambda iqresnode: self.readerThread.parseRequestUpload(iqresnode, b64Hash)

		if type(size) is not str:
			size = str(size)

		attribs = {"xmlns":"w:m","hash":b64Hash, "type":t, "size":size}

		if b64OrigHash:
			attribs["orighash"] = b64OrigHash

		mediaNode = ProtocolTreeNode("media", attribs)
		iqNode = ProtocolTreeNode("iq",{"id":idx,"to":"s.whatsapp.net","type":"set"},[mediaNode])
		
		
		self._writeNode(iqNode)

	def getMessageNode(self, jid, child):
			requestNode = None;
			serverNode = ProtocolTreeNode("server",None);
			xNode = ProtocolTreeNode("x",{"xmlns":"jabber:x:event"},[serverNode]);
			childCount = (0 if requestNode is None else 1) +2;
			messageChildren = []#[None]*childCount;
			if requestNode is not None:
				messageChildren.append(requestNode);
			#System.currentTimeMillis() / 1000L + "-"+1
			messageChildren.append(xNode)
			
			if type(child) == list:
				messageChildren.extend(child)
			else:
				messageChildren.append(child)
				
			msgId = str(int(time.time()))+"-"+ str(self.currKeyId)
			
			messageNode = ProtocolTreeNode("message",{"to":jid,"type":"chat","id":msgId},messageChildren)
			
			self.currKeyId += 1


			return messageNode;


class ReaderThread(threading.Thread):
	def __init__(self):
		Debugger.attach(self);

		self.signalInterface = None
		#self.socket = connection
		self.terminateRequested = False
		self.disconnectedSent = False
		self.timeout = 180
		self.selectTimeout = 3
		self.requests = {};
		self.lock = threading.Lock()
		self.disconnectedCallback = None
		self.autoPong = True
		self.onPing = self.ping = None

		self.lastPongTime = int(time.time())
		super(ReaderThread,self).__init__();

		self.daemon = True
	def setSocket(self, connection):
		self.socket = connection

	def setSignalInterface(self, signalInterface):
		self.signalInterface = signalInterface

	def terminate(self):
		self._d("attempting to exit gracefully")
		self.terminateRequested = True
		

	def sendDisconnected(self, reason="noreason"):
		self._d("Sending disconnected because of %s" % reason)
		self.lock.acquire()
		if not self.disconnectedSent:
			self.disconnectedSent = True
			if self.disconnectedCallback:
				self.disconnectedCallback()
			self.lock.release()
			self.signalInterface.send("disconnected", (reason,))

	def run(self):
		self._d("Read thread startedX");
		while True:

			
			countdown = self.timeout - ((int(time.time()) - self.lastPongTime))
			
			remainder = countdown % self.selectTimeout
			countdown = countdown - remainder
					
			if countdown <= 0:
				self._d("No hope, dying!")
				self.sendDisconnected("closed")
				return
			else:
				if countdown % (self.selectTimeout*10) == 0 or countdown < 11:
					self._d("Waiting, time to die: T-%i seconds" % countdown )
					
				if self.timeout-countdown == 150 and self.ping and self.autoPong:
					self.ping()

				self.selectTimeout = 1 if countdown < 11 else 3


			try:
				ready = select.select([self.socket.reader.rawIn], [], [], self.selectTimeout)
			except:
				self._d("Error in ready")
				raise
				return
			
			if self.terminateRequested:
				return

			if ready[0]:
				try:
					node = self.socket.reader.nextTree()
				except ConnectionClosedException:
					#print traceback.format_exc()
					self._d("Socket closed, got 0 bytes!")
					#self.signalInterface.send("disconnected", ("closed",))
					self.sendDisconnected("closed")
					return

				self.lastPongTime = int(time.time());

				if node is not None:
					if ProtocolTreeNode.tagEquals(node,"iq"):
						iqType = node.getAttributeValue("type")
						idx = node.getAttributeValue("id")

						if iqType is None:
							raise Exception("iq doesn't have type")

						if iqType == "result":
							if idx in self.requests:
								self.requests[idx](node)
								del self.requests[idx]
							elif idx.startswith(self.connection.user):
								accountNode = node.getChild(0)
								ProtocolTreeNode.require(accountNode,"account")
								kind = accountNode.getAttributeValue("kind")

								if kind == "paid":
									self.connection.account_kind = 1
								elif kind == "free":
									self.connection.account_kind = 0
								else:
									self.connection.account_kind = -1

								expiration = accountNode.getAttributeValue("expiration")

								if expiration is None:
									raise Exception("no expiration")

								try:
									self.connection.expire_date = long(expiration)
								except ValueError:
									raise IOError("invalid expire date %s"%(expiration))

								self.eventHandler.onAccountChanged(self.connection.account_kind,self.connection.expire_date)
						elif iqType == "error":
							if idx in self.requests:
								self.requests[idx](node)
								del self.requests[idx]
						elif iqType == "get":
							childNode = node.getChild(0)
							if ProtocolTreeNode.tagEquals(childNode,"ping"):
								if self.autoPong:
									self.onPing(idx)
									
								self.signalInterface.send("ping", (idx,))	
							elif ProtocolTreeNode.tagEquals(childNode,"query") and node.getAttributeValue("from") is not None and "http://jabber.org/protocol/disco#info" == childNode.getAttributeValue("xmlns"):
								pin = childNode.getAttributeValue("pin");
								timeoutString = childNode.getAttributeValue("timeout");
								try:
									timeoutSeconds = int(timeoutString) if timeoutString is not None else None
								except ValueError:
									raise Exception("relay-iq exception parsing timeout %s "%(timeoutString))

								if pin is not None:
									self.eventHandler.onRelayRequest(pin,timeoutSeconds,idx)
						elif iqType == "set":
							childNode = node.getChild(0)
							if ProtocolTreeNode.tagEquals(childNode,"query"):
								xmlns = childNode.getAttributeValue("xmlns")

								if xmlns == "jabber:iq:roster":
									itemNodes = childNode.getAllChildren("item");
									ask = ""
									for itemNode in itemNodes:
										jid = itemNode.getAttributeValue("jid")
										subscription = itemNode.getAttributeValue("subscription")
										ask = itemNode.getAttributeValue("ask")
						else:
							raise Exception("Unkown iq type %s"%(iqType))

					elif ProtocolTreeNode.tagEquals(node,"presence"):
						xmlns = node.getAttributeValue("xmlns")
						jid = node.getAttributeValue("from")

						if (xmlns is None or xmlns == "urn:xmpp") and jid is not None:
							presenceType = node.getAttributeValue("type")
							if presenceType == "unavailable":
								self.signalInterface.send("presence_unavailable", (jid,))
							elif presenceType is None or presenceType == "available":
								self.signalInterface.send("presence_available", (jid,))

						elif xmlns == "w" and jid is not None:
							status = node.getAttributeValue("status")

							if status == "dirty":
								#categories = self.parseCategories(node); #@@TODO, send along with signal
								self._d("WILL SEND DIRTY")
								self.signalInterface.send("status_dirty")
								self._d("SENT DIRTY")

					elif ProtocolTreeNode.tagEquals(node,"message"):
						self.parseMessage(node)
					

		self._d("Reader thread terminating now!")
					
	def parseOfflineMessageStamp(self,stamp):

		watime = WATime();
		parsed = watime.parseIso(stamp)
		local = watime.utcToLocal(parsed)
		stamp = watime.datetimeToTimestamp(local)

		return stamp


	def parsePingResponse(self, node):
		idx = node.getAttributeValue("id")
		self.lastPongTime = int(time.time())
		
		

	def parseLastOnline(self,node):
		jid = node.getAttributeValue("from");
		firstChild = node.getChild(0);

		if "error" in firstChild.toString():
			return

		ProtocolTreeNode.require(firstChild,"query");
		seconds = firstChild.getAttributeValue("seconds");
		status = None
		status = firstChild.data #@@TODO discarded?

		try:
			if seconds is not None and jid is not None:
				self.signalInterface.send("presence_updated", (jid, int(seconds)))
		except:
			self._d("Ignored exception in handleLastOnline "+ sys.exc_info()[1])


	def parseGroups(self,node):
		children = node.getAllChildren("group");
		for groupNode in children:
			jid = groupNode.getAttributeValue("id") + "@g.us"
			owner = groupNode.getAttributeValue("owner")
			subject = groupNode.getAttributeValue("subject") if sys.version_info < (3, 0) else groupNode.getAttributeValue("subject").encode('latin-1').decode() 
			subjectT = groupNode.getAttributeValue("s_t")
			subjectOwner = groupNode.getAttributeValue("s_o")
			creation = groupNode.getAttributeValue("creation")

			self.signalInterface.send("group_gotInfo",(jid, owner, subject, subjectOwner, int(subjectT),int(creation)))


	def parseGroupInfo(self,node):
		jid = node.getAttributeValue("from");
		groupNode = node.getChild(0)
		if "error code" in groupNode.toString():
			self.signalInterface.send("group_infoError",(0,)) #@@TODO replace with real error code
		else:
			ProtocolTreeNode.require(groupNode,"group")
			#gid = groupNode.getAttributeValue("id")
			owner = groupNode.getAttributeValue("owner")
			subject = groupNode.getAttributeValue("subject") if sys.version_info < (3, 0) else groupNode.getAttributeValue("subject").encode('latin-1').decode();
			subjectT = groupNode.getAttributeValue("s_t")
			subjectOwner = groupNode.getAttributeValue("s_o")
			creation = groupNode.getAttributeValue("creation")
		
			self.signalInterface.send("group_gotInfo",(jid, owner, subject, subjectOwner, int(subjectT),int(creation)))

	def parseAddedParticipants(self, node):
		jid = node.getAttributeValue("from");
		jids = []
		
		addNodes = node.getAllChildren("add")

		for a in addNodes:
			t = a.getAttributeValue("type")
			if t == "success":
				jids.append(a.getAttributeValue("participant"))
			else:
				self._d("Failed to add %s" % jids.append(a.getAttributeValue("participant")))
		
		self.signalInterface.send("group_addParticipantsSuccess", (jid, jids))


	def parseRemovedParticipants(self,node): #fromm, successVector=None,failTable=None
		jid = node.getAttributeValue("from");
		jids = []
		
		addNodes = node.getAllChildren("remove")

		for a in addNodes:
			t = a.getAttributeValue("type")
			if t == "success":
				jids.append(a.getAttributeValue("participant"))
			else:
				self._d("Failed to add %s" % jids.append(a.getAttributeValue("participant")))
		self._d("handleRemovedParticipants DONE!");

		self.signalInterface.send("group_removeParticipantsSuccess", (jid, jids))

	def parseGroupCreated(self,node):
		jid = node.getAttributeValue("from");
		groupNode = node.getChild(0)
		
		if ProtocolTreeNode.tagEquals(groupNode,"error"):
			errorCode = groupNode.getAttributeValue("code")
			self.signalInterface.send("group_createFail", (errorCode,))
			return

		ProtocolTreeNode.require(groupNode,"group")
		group_id = groupNode.getAttributeValue("id")
		self.signalInterface.send("group_createSuccess", (group_id + "@g.us",))

	def parseGroupEnded(self,node):
		#jid = node.getAttributeValue("from");
		
		leaveNode = node.getChild(0)
		groupNode = leaveNode.getChild(0)
		
		jid = groupNode.getAttributeValue("id")
		
		self.signalInterface.send("group_endSuccess", (jid,))

	def parseGroupSubject(self,node):
		jid = node.getAttributeValue("from");
		self.signalInterface.send("group_setSubjectSuccess", (jid,))

	def parseParticipants(self,node):
		jid = node.getAttributeValue("from");
		children = node.getAllChildren("participant");
		jids = []
		for c in children:
			jids.append(c.getAttributeValue("jid"))

		self.signalInterface.send("group_gotParticipants", (jid, jids))

	#@@TODO PICTURE STUFF


	def createTmpFile(self, data, mode = "w"):
		
		tmp = tempfile.mkstemp()[1]
		
		tmpfile = open(tmp, mode)
		tmpfile.write(data)
		tmpfile.close()

		return tmp
	
	def parseGetPicture(self,node):
		jid = node.getAttributeValue("from");
		if "error code" in node.toString():
			return;

		pictureNode = node.getChild("picture")
		if pictureNode.data is not None:
			tmp = self.createTmpFile(pictureNode.data if sys.version_info < (3, 0) else pictureNode.data.encode('latin-1'), "wb")

			pictureId = int(pictureNode.getAttributeValue('id'))
			try:
				jid.index('-')
				self.signalInterface.send("group_gotPicture", (jid, pictureId, tmp))
			except ValueError:
				self.signalInterface.send("contact_gotProfilePicture", (jid, pictureId, tmp))


	def parseGetPictureIds(self,node):
		jid = node.getAttributeValue("from");
		groupNode = node.getChild("list")
		#self._d(groupNode.toString())
		children = groupNode.getAllChildren("user");
		#pids = []
		for c in children:
			if c.getAttributeValue("id") is not None:
				#pids.append({"jid":c.getAttributeValue("jid"),"id":c.getAttributeValue("id")})
				self.signalInterface.send("contact_gotProfilePictureId", (c.getAttributeValue("jid"), c.getAttributeValue("id")))
		#self.signalInterface.send("contact_gotProfilePictureIds", (pids,))


	def parseSetPicture(self,node):
		jid = node.getAttributeValue("from");
		picNode = node.getChild("picture")
		
		try:
			jid.index('-')
			
			if picNode is None:
				self.signalInterface.send("group_setPictureError", (jid,0)) #@@TODO SEND correct error code
			else:
				pictureId = int(picNode.getAttributeValue("id"))
				self.signalInterface.send("group_setPictureSuccess", (jid, pictureId))
		except ValueError:
			if picNode is None:
				self.signalInterface.send("profile_setPictureError", (0,)) #@@TODO SEND correct error code
			else:
				pictureId = int(picNode.getAttributeValue("id"))
				self.signalInterface.send("profile_setPictureSuccess", (pictureId,))
	
	
	def parseRequestUpload(self, iqNode, _hash):

		mediaNode = iqNode.getChild("media")
		
		
		if mediaNode:

			url = mediaNode.getAttributeValue("url")
			
			resumeFrom = mediaNode.getAttributeValue("resume")
			
			if not resumeFrom:
				resumeFrom = 0
	
			if url:
				self.signalInterface.send("media_uploadRequestSuccess", (_hash, url, resumeFrom))
			else:
				self.signalInterface.send("media_uploadRequestFailed", (_hash,))
		else:
			duplicateNode = iqNode.getChild("duplicate")
			
			if duplicateNode:
				
				url = duplicateNode.getAttributeValue("url")
				
				
				self.signalInterface.send("media_uploadRequestDuplicate", (_hash, url))
		
			else:
				self.signalInterface.send("media_uploadRequestFailed", (_hash,))
				

	def parseMessage(self,messageNode):


		bodyNode = messageNode.getChild("body");
#		offlineNode = messageNode.getChild("offline")

		
		newSubject = "" if bodyNode is None else bodyNode.data;
		msgData = None
#		timestamp =long(time.time()*1000) if not offlineNode else int(messageNode.getAttributeValue("t"))*1000;
		timestamp =int(messageNode.getAttributeValue("t"))
		isGroup = False
		isBroadcast = False
		
		if newSubject.find("New version of WhatsApp Messenger is now available")>-1:
			self._d("Rejecting whatsapp server message")
			return #REJECT THIS FUCKING MESSAGE!


		fromAttribute = messageNode.getAttributeValue("from");

		try:
			fromAttribute.index('-')
			isGroup = True
		except:
			pass

		author = messageNode.getAttributeValue("author");
		#@@TODO reactivate blocked contacts check from client
		'''if fromAttribute is not None and fromAttribute in self.eventHandler.blockedContacts:
			self._d("CONTACT BLOCKED!")
			return

		if author is not None and author in self.eventHandler.blockedContacts:
			self._d("CONTACT BLOCKED!")
			return
		'''

		pushName = None
		notifNode = messageNode.getChild("notify")
		if notifNode is not None:
			pushName = notifNode.getAttributeValue("name");
			#pushName = pushName.decode("utf8")


		msgId = messageNode.getAttributeValue("id");
		attribute_t = messageNode.getAttributeValue("t");

		typeAttribute = messageNode.getAttributeValue("type");

		if typeAttribute == "error":
			errorCode = 0;
			errorNodes = messageNode.getAllChildren("error");
			for errorNode in errorNodes:
				codeString = errorNode.getAttributeValue("code")
				try:
					errorCode = int(codeString);
				except ValueError:
					'''catch value error'''
				self.signalInterface.send("message_error", (msgId, fromAttribute, errorCode))

		elif typeAttribute == "notification":

			receiptRequested = False;
			pictureUpdated = None

			pictureUpdated = messageNode.getChild("notification").getAttributeValue("type");

			wr = None
			wr = messageNode.getChild("request").getAttributeValue("xmlns");
			if wr == "urn:xmpp:receipts":
				receiptRequested = True
				
			if pictureUpdated == "picture":
				notifNode = messageNode.getChild("notification");
				#bodyNode = messageNode.getChild("notification").getChild("set") or messageNode.getChild("notification").getChild("delete")

				bodyNode = notifNode.getChild("set")
				
				if bodyNode:
					pictureId = int(bodyNode.getAttributeValue("id"))
					if isGroup:
						self.signalInterface.send("notification_groupPictureUpdated",(bodyNode.getAttributeValue("jid"), bodyNode.getAttributeValue("author"), timestamp, msgId, pictureId, receiptRequested))
					else:
						self.signalInterface.send("notification_contactProfilePictureUpdated",(bodyNode.getAttributeValue("jid"), timestamp, msgId, pictureId, receiptRequested))

				else:
					bodyNode = notifNode.getChild("delete")

					if bodyNode:
						if isGroup:
							self.signalInterface.send("notification_groupPictureRemoved",(bodyNode.getAttributeValue("jid"), bodyNode.getAttributeValue("author"), timestamp, msgId, receiptRequested))
						else:
							self.signalInterface.send("notification_contactProfilePictureRemoved",(bodyNode.getAttributeValue("jid"), timestamp, msgId, receiptRequested))

				#if isGroup:
				#	
				#	self.signalInterface.send("notification_groupPictureUpdated",(bodyNode.getAttributeValue("jid"), bodyNode.getAttributeValue("author"), timestamp, msgId, receiptRequested))
				#else:
				#	self.signalInterface.send("notification_contactProfilePictureUpdated",(bodyNode.getAttributeValue("jid"), timestamp, msgId, receiptRequested))

			else:
				addSubject = None
				removeSubject = None
				author = None

				bodyNode = messageNode.getChild("notification").getChild("add");
				if bodyNode is not None:
					addSubject = bodyNode.getAttributeValue("jid");
					author = bodyNode.getAttributeValue("author") or addSubject

				bodyNode = messageNode.getChild("notification").getChild("remove");
				if bodyNode is not None:
					removeSubject = bodyNode.getAttributeValue("jid");
					author = bodyNode.getAttributeValue("author") or removeSubject

				if addSubject is not None:
					
					self.signalInterface.send("notification_groupParticipantAdded", (fromAttribute, addSubject, author, timestamp, msgId, receiptRequested))
					
				if removeSubject is not None:
					self.signalInterface.send("notification_groupParticipantRemoved", (fromAttribute, removeSubject, author, timestamp, msgId, receiptRequested))


		elif typeAttribute == "subject":
			receiptRequested = False;
			requestNodes = messageNode.getAllChildren("request");
			for requestNode in requestNodes:
				if requestNode.getAttributeValue("xmlns") == "urn:xmpp:receipts":
					receiptRequested = True;

			bodyNode = messageNode.getChild("body");
			newSubject = None if bodyNode is None else (bodyNode.data if sys.version_info < (3, 0) else bodyNode.data.encode('latin-1').decode());
			
			if newSubject is not None:
				self.signalInterface.send("group_subjectReceived",(msgId, fromAttribute, author, newSubject, int(attribute_t),  receiptRequested))

		elif typeAttribute == "chat":
			wantsReceipt = False;
			messageChildren = [] if messageNode.children is None else messageNode.children

			for childNode in messageChildren:
				if ProtocolTreeNode.tagEquals(childNode,"request"):
					wantsReceipt = True;
				
				if ProtocolTreeNode.tagEquals(childNode,"broadcast"):
					isBroadcast = True
				elif ProtocolTreeNode.tagEquals(childNode,"composing"):
						self.signalInterface.send("contact_typing", (fromAttribute,))
				elif ProtocolTreeNode.tagEquals(childNode,"paused"):
						self.signalInterface.send("contact_paused",(fromAttribute,))

				elif ProtocolTreeNode.tagEquals(childNode,"media") and msgId is not None:
	
					self._d("MULTIMEDIA MESSAGE!");
					
					mediaUrl = messageNode.getChild("media").getAttributeValue("url");
					mediaType = messageNode.getChild("media").getAttributeValue("type")
					mediaSize = messageNode.getChild("media").getAttributeValue("size")
					encoding = messageNode.getChild("media").getAttributeValue("encoding")
					mediaPreview = None


					if mediaType == "image":
						mediaPreview = messageNode.getChild("media").data
						
						if encoding == "raw" and mediaPreview:
							mediaPreview = base64.b64encode(mediaPreview) if sys.version_info < (3, 0) else base64.b64encode(mediaPreview.encode('latin-1')).decode()

						if isGroup:
							self.signalInterface.send("group_imageReceived", (msgId, fromAttribute, author, mediaPreview, mediaUrl, mediaSize, wantsReceipt))
						else:
							self.signalInterface.send("image_received", (msgId, fromAttribute, mediaPreview, mediaUrl, mediaSize,  wantsReceipt, isBroadcast))

					elif mediaType == "video":
						mediaPreview = messageNode.getChild("media").data
						
						if encoding == "raw" and mediaPreview:
							mediaPreview = base64.b64encode(mediaPreview) if sys.version_info < (3, 0) else base64.b64encode(mediaPreview.encode('latin-1')).decode()

						if isGroup:
							self.signalInterface.send("group_videoReceived", (msgId, fromAttribute, author, mediaPreview, mediaUrl, mediaSize, wantsReceipt))
						else:
							self.signalInterface.send("video_received", (msgId, fromAttribute, mediaPreview, mediaUrl, mediaSize, wantsReceipt, isBroadcast))

					elif mediaType == "audio":
						mediaPreview = messageNode.getChild("media").data

						if isGroup:
							self.signalInterface.send("group_audioReceived", (msgId, fromAttribute, author, mediaUrl, mediaSize, wantsReceipt))
						else:
							self.signalInterface.send("audio_received", (msgId, fromAttribute, mediaUrl, mediaSize, wantsReceipt, isBroadcast))

					elif mediaType == "location":
						mlatitude = messageNode.getChild("media").getAttributeValue("latitude")
						mlongitude = messageNode.getChild("media").getAttributeValue("longitude")
						name = messageNode.getChild("media").getAttributeValue("name")
						
						if name and not sys.version_info < (3, 0):
							name = name.encode('latin-1').decode()
						
						mediaPreview = messageNode.getChild("media").data
						
						if encoding == "raw" and mediaPreview:
							mediaPreview = base64.b64encode(mediaPreview) if sys.version_info < (3, 0) else base64.b64encode(mediaPreview.encode('latin-1')).decode()

						if isGroup:
							self.signalInterface.send("group_locationReceived", (msgId, fromAttribute, author, name or "", mediaPreview, mlatitude, mlongitude, wantsReceipt))
						else:
							self.signalInterface.send("location_received", (msgId, fromAttribute, name or "", mediaPreview, mlatitude, mlongitude, wantsReceipt, isBroadcast))
		
					elif mediaType =="vcard":
						#return
						#mediaItem.preview = messageNode.getChild("media").data
						vcardData = messageNode.getChild("media").getChild("vcard").toString()
						vcardName = messageNode.getChild("media").getChild("vcard").getAttributeValue("name")
						
						if vcardName and not sys.version_info < (3, 0):
							vcardName = vcardName.encode('latin-1').decode()
						
						if vcardData is not None:
							n = vcardData.find(">") +1
							vcardData = vcardData[n:]
							vcardData = vcardData.replace("</vcard>","")

							if isGroup:
								self.signalInterface.send("group_vcardReceived", (msgId, fromAttribute, author, vcardName, vcardData, wantsReceipt))
							else:
								self.signalInterface.send("vcard_received", (msgId, fromAttribute, vcardName, vcardData, wantsReceipt, isBroadcast))
							
					else:
						self._d("Unknown media type")
						return

				elif ProtocolTreeNode.tagEquals(childNode,"body") and msgId is not None:
					msgData = childNode.data;
					
					#fmsg.setData({"status":0,"key":key.toString(),"content":msgdata,"type":WAXMPP.message_store.store.Message.TYPE_RECEIVED});

				elif ProtocolTreeNode.tagEquals(childNode,"received") and fromAttribute is not None and msgId is not None:

					if fromAttribute == "s.us":
						self.signalInterface.send("profile_setStatusSuccess", ("s.us", msgId,))
						return;

					#@@TODO autosend ack from client
					#print "NEW MESSAGE RECEIVED NOTIFICATION!!!"
					#self.connection.sendDeliveredReceiptAck(fromAttribute,msg_id);
					self.signalInterface.send("receipt_messageDelivered", (fromAttribute, msgId))
					
					return


				elif not (ProtocolTreeNode.tagEquals(childNode,"active")):
					if ProtocolTreeNode.tagEquals(childNode,"request"):
						wantsReceipt = True;

					elif ProtocolTreeNode.tagEquals(childNode,"notify"):
						notify_name = childNode.getAttributeValue("name");


					elif ProtocolTreeNode.tagEquals(childNode,"delay"):
						xmlns = childNode.getAttributeValue("xmlns");
						if "urn:xmpp:delay" == xmlns:
							stamp_str = childNode.getAttributeValue("stamp");
							if stamp_str is not None:
								stamp = stamp_str
								timestamp = self.parseOfflineMessageStamp(stamp)*1000;

					elif ProtocolTreeNode.tagEquals(childNode,"x"):
						xmlns = childNode.getAttributeValue("xmlns");
						if "jabber:x:event" == xmlns and msgId is not None:
							
							if fromAttribute == "broadcast":
								self.signalInterface.send("receipt_broadcastSent", (msgId,))
							else:
								self.signalInterface.send("receipt_messageSent", (fromAttribute, msgId))

						elif "jabber:x:delay" == xmlns:
							continue; #@@TODO FORCED CONTINUE, WHAT SHOULD I DO HERE? #wtf?
							stamp_str = childNode.getAttributeValue("stamp");
							if stamp_str is not None:
								stamp = stamp_str
								timestamp = stamp;
					else:
						if ProtocolTreeNode.tagEquals(childNode,"delay") or not ProtocolTreeNode.tagEquals(childNode,"received") or msgId is None:
							continue;

							
							receipt_type = childNode.getAttributeValue("type");
							if receipt_type is None or receipt_type == "delivered":
								self.signalInterface.send("receipt_messageDelivered", (fromAttribute, msgId))
							elif receipt_type == "visible":
								self.signalInterface.send("receipt_visible", (fromAttribute, msgId))
							




			if msgData:
				msgData = msgData if sys.version_info < (3, 0) else msgData.encode('latin-1').decode()
				if isGroup:
					self.signalInterface.send("group_messageReceived", (msgId, fromAttribute, author, msgData, timestamp, wantsReceipt, pushName))

				else:
					self.signalInterface.send("message_received", (msgId, fromAttribute, msgData, timestamp, wantsReceipt, pushName, isBroadcast))

				##@@TODO FROM CLIENT
				'''if conversation.type == "group":
					if conversation.subject is None:
						signal = False
						self._d("GETTING GROUP INFO")
						self.connection.sendGetGroupInfo(fromAttribute)
				'''
					#if not len(conversation.getContacts()):
					#	self._d("GETTING GROUP CONTACTS")
					#	self.connection.sendGetParticipants(fromAttribute)

				'''@@TODO FROM CLIENT
				if ret is None:
					conversation.incrementNew();
					WAXMPP.message_store.pushMessage(fromAttribute,fmsg)
					fmsg.key = key
				else:
					fmsg.key = eval(ret.key)
					duplicate = True;
				'''
			

########NEW FILE########
__FILENAME__ = contacts
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

from Yowsup.Common.Http.warequest import WARequest
from Yowsup.Common.Http.waresponseparser import JSONResponseParser
from hashlib import md5
import random, sys
from Yowsup.Common.utilities import Utilities

class WAContactsSyncRequest():

    def __init__(self, username, password, contacts):
        
        self.username = username
        self.password = password
        
        self.contacts = contacts
        self.authReq = WAContactsSyncAuth(username, password)
        
    def setCredentials(self, username, password):
        self.username = username
        self.password = password
        self.authReq = WAContactsSyncAuth(username, password)
        
    def setContacts(self, contacts):
        self.contacts = contacts
        
    def send(self):
        auth = self.authReq.send()
        
        if not auth["message"] == "next token":
            return auth
        
        response = self.authReq.response
        
        respH = response.getheader("www-authenticate")
        
        self.authReq._d(respH)
        
        tmp = respH[respH.index('nonce="')+len('nonce="'):]
        nonce = tmp[:tmp.index('"')]
        
        q = WAContactsSyncQuery(self.username, self.password, nonce, self.contacts)
        
        resp = q.send()
        
        return resp
        
        
        
class WAContactsSyncAuth(WARequest):
    
    nc = "00000001"
    realm = "s.whatsapp.net"
    qop = "auth"
    digestUri = "WAWA/s.whatsapp.net"
    charSet = "utf-8"
    authMethod = "X-WAWA"
    
    authTemplate = '{auth_method}: username="{username}",realm="{realm}",nonce="{nonce}",cnonce="{cnonce}",nc="{nc}",qop="auth",\
digest-uri="{digest_uri}",response="{response}",charset="utf-8"'
    
    def __init__(self, username, password, nonce = "0"):
        
        super(WAContactsSyncAuth, self).__init__();
        self.url = "sro.whatsapp.net/v2/sync/a"
        self.type = "POST"
        cnonce = Utilities.str(random.randint(100000000000000,1000000000000000), 36)
        
        credentials = bytearray((username+":s.whatsapp.net:").encode())
        credentials.extend(password)

        if sys.version_info >= (3, 0):
            buf = lambda x: bytes(x, 'iso-8859-1') if type(x) is str else bytes(x)
        else:
            buf = buffer
        

        response = self.encode(
                        self.md5(
                            self.encode(
                                self.md5(
                                    self.md5( buf ( credentials ) ) 
                                        + (":" + nonce + ":" + cnonce).encode()  
                                    )
                                )
                                 + (":"+nonce+":" + WAContactsSyncAuth.nc+":" + cnonce + ":auth:").encode()
                                + self.encode(
                                        self.md5(("AUTHENTICATE:"+WAContactsSyncAuth.digestUri).encode())
                                ))).decode()
        
        
        
        authField = WAContactsSyncAuth.authTemplate.format(auth_method = WAContactsSyncAuth.authMethod,
                                                           username = username,
                                                           realm = WAContactsSyncAuth.realm,
                                                           nonce = nonce,
                                                           cnonce = cnonce,
                                                           nc= WAContactsSyncAuth.nc,
                                                           digest_uri = WAContactsSyncAuth.digestUri,
                                                           response = response)
        
        self.addHeaderField("Authorization", authField)        

        self.pvars = ["message"]
        
        self.setParser(JSONResponseParser())
        
        
    def md5(self, data):
        return md5(data).digest();
        
    def getResponseDigest(self):
        pass
    
    def encode(self, inp):
        res = []
        
        
        def _enc(n):
            if n < 10:
                return n + 48
            return n + 87
        
        for c in inp:
            
            if type(inp) is str:
                c = ord(c)
            
            if c < 0: c += 256
            
            res.append(_enc(c >> 4))
            res.append(_enc(c % 16))
        
        
        return "".join(map(chr, res)).encode();
    
    
class WAContactsSyncQuery(WAContactsSyncAuth):
    def __init__(self, username, password, nonce, contacts):
        
        super(WAContactsSyncQuery, self).__init__(username, password, nonce)
        
        
        self.url = "sro.whatsapp.net/v2/sync/q"
        
        self.pvars = ["c"]
        
        
        self.addParam("ut", "all")
        #self.addParam("ut", "wa")
        self.addParam("t", "c")
        #self.addParam("t", "w")
        
        for c in contacts:
            self.addParam("u[]", c)

########NEW FILE########
__FILENAME__ = DBusInterface
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import dbus.service

import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__+"/..")))
os.sys.path.insert(0,parentdir)

from Interfaces.Interface import SignalInterfaceBase, MethodInterfaceBase
from connectionmanager import YowsupConnectionManager


class DBusInitInterface(dbus.service.Object):
	DBUS_INTERFACE = "com.yowsup.methods"
	def __init__(self):
		self.busName = dbus.service.BusName(self.DBUS_INTERFACE, bus=dbus.SessionBus())
		dbus.service.Object.__init__(self,self.busName, '/com/yowsup/methods')
		
		self.connections = {}
		
		super(DBusInitInterface, self).__init__()
		
	@dbus.service.method(DBUS_INTERFACE)
	def init(self, username):
		man = YowsupConnectionManager()
		man.setInterfaces(DBusSignalInterface(username), DBusMethodInterface(username))
		self.connections[username] = man
		
		return username
		

class DBusSignalInterface(SignalInterfaceBase, dbus.service.Object):

	DBUS_INTERFACE = "com.yowsup.signals"
	
	def __init__(self, connectionId):
		self.connectionId = connectionId
		self.busName = dbus.service.BusName(self.DBUS_INTERFACE, bus=dbus.SessionBus())
		dbus.service.Object.__init__(self, self.busName, '/com/yowsup/%s/signals'%connectionId)

		super(DBusSignalInterface,self).__init__();

		self._attachDbusSignalsToSignals()


	@dbus.service.method(DBUS_INTERFACE)
	def getSignals(self):
		return self.signals
	
	def _attachDbusSignalsToSignals(self):
		for s in self.signals:
			try:
				currBusSig = getattr(self, s)
				self.registerListener(s, currBusSig)
				print("Registered %s on Dbus " % s)
			except AttributeError:
				print("Skipping %s" %s)

	## Signals ##
	
	
	@dbus.service.signal(DBUS_INTERFACE)
	def auth_success(self, username):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def auth_fail(self, username, reason):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def presence_updated(self, jid, lastSeen):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def presence_available(self, jid):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def presence_unavailable(self, jid):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def message_received(self, msgId, jid, content, timestamp, wantsReceipt, isBroadcast):
		pass
#--------------------------------------------------------------------------- Groups
	@dbus.service.signal(DBUS_INTERFACE)
	def group_messageReceived(self, msgId, jid, author, content, timestamp, wantsReceipt):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def group_gotInfo(self, jid, owner, subject, subjectOwner, subjectT, creation):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def group_setSubjectSuccess(self, jid):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def group_subjectReceived(self, msgId, fromAttribute, author, newSubject, timestamp, receiptRequested):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def group_addParticipantsSuccess(self, jid, jids):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def group_removeParticipantsSuccess(self, jid, jids):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def group_createSuccess(self, jid):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def group_createFail(self, errorCode):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def group_endSuccess(self, jid):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def group_gotPicture(self, jid, pictureId, filepath):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def group_infoError(self, errorCode):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def group_gotParticipants(self,jid, jids):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def group_setPictureSuccess(self, jid, pictureId):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def group_setPictureError(self, jid, errorCode):
		pass
	
#------------------------------------------------------------------------------ 
	
	@dbus.service.signal(DBUS_INTERFACE)
	def profile_setStatusSuccess(self, jid, messageId):
		pass
	
	
	@dbus.service.signal(DBUS_INTERFACE)
	def profile_setPictureSuccess(self, pictureId):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def profile_setPictureError(self, errorCode):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def status_dirty(self):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def receipt_messageSent(self, jid, msgId):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def receipt_messageDelivered(self, jid, msgId):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def receipt_visible(self, jid, msgId):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def contact_gotProfilePictureId(self, jid, pictureId):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def contact_typing(self, jid):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def contact_paused(self, jid):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def contact_gotProfilePicture(self, jid, pictureId, filename):
		pass


	@dbus.service.signal(DBUS_INTERFACE)
	def notification_contactProfilePictureUpdated(self, jid, timestamp, messageId, pictureId, wantsReceipt = True):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def notification_contactProfilePictureRemoved(self, jid, timestamp, messageId, wantsReceipt = True):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def notification_groupParticipantAdded(self, gJid, jid, author, timestamp, messageId, wantsReceipt = True):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def notification_groupParticipantRemoved(self, gjid, jid, author, timestamp, messageId, wantsReceipt = True):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def notification_groupPictureUpdated(self, jid, author, timestamp, messageId, pictureId, wantsReceipt = True):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def notification_groupPictureRemoved(self, jid, author, timestamp, messageId, wantsReceipt = True):
		pass


	@dbus.service.signal(DBUS_INTERFACE)
	def image_received(self, messageId, jid, preview, url, size, wantsReceipt, isBroadcast):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def video_received(self, messageId, jid, preview, url, size, wantsReceipt, isBroadcast):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def audio_received(self, messageId, jid, url, size, wantsReceipt, isBroadcast):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def location_received(self, messageId, jid, name, preview, latitude, longitude, isBroadcast):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def vcard_received(self, messageId, jid, name, data, isBroadcast):
		pass


	@dbus.service.signal(DBUS_INTERFACE)
	def group_imageReceived(self, messageId, jid, author, preview, url, size, wantsReceipt):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def group_videoReceived(self, messageId, jid, author, preview, url, size, wantsReceipt):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def group_audioReceived(self, messageId, jid, author, url, size, wantsReceipt):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def group_locationReceived(self, messageId, jid, author, name, preview, latitude, longitude, wantsReceipt):
		pass

	@dbus.service.signal(DBUS_INTERFACE)
	def group_vcardReceived(self, messageId, jid, author, name, data, wantsReceipt):
		pass
	
	
	@dbus.service.signal(DBUS_INTERFACE)
	def message_error(self, messageId, jid, errorCode):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def disconnected(self, reason):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def ping(self, pingId):
		pass
	
	@dbus.service.signal(DBUS_INTERFACE)
	def pong(self):
		pass

	
		
class DBusMethodInterface(MethodInterfaceBase, dbus.service.Object):
	DBUS_INTERFACE = 'com.yowsup.methods'

	def __init__(self, connectionId):
		self.connectionId = connectionId
		super(DBusMethodInterface,self).__init__();

		busName = dbus.service.BusName(self.DBUS_INTERFACE, bus=dbus.SessionBus())
		dbus.service.Object.__init__(self, busName, '/com/yowsup/%s/methods'%connectionId)


	def interfaceMethod(fn):
		def wrapped(self, *args):
			fnName = fn.__name__
			return self.call(fnName, args)
		return wrapped

	@dbus.service.method(DBUS_INTERFACE)
	def getMethods(self):
		return self.methods
	
	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def getVersion(self):
		pass
	
	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def auth_login(self, number, password):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def message_send(self, jid, message):
		pass
	
	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def message_imageSend(self, jid, url, name, size, preview):
		pass
	
	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def message_videoSend(self, jid, url, name, size, preview):
		pass
	
	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def message_audioSend(self, jid, url, name, size):
		pass
	
	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def message_locationSend(self, jid, latitude, longitude, preview): #@@TODO add name to location?
		pass
	
	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def message_vcardSend(self, jid, data, name):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def message_ack(self, jid, msgId):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def notification_ack(self, jid, msgId):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def clientconfig_send(self):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def delivered_ack(self, jid, msgId):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def visible_ack(self, jid, msgId):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def ping(self):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def pong(self, pingId):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def typing_send(self, jid):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def typing_paused(self,jid):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def subject_ack(self, jid, msgId):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def group_getInfo(self,jid):
		pass
	
	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def group_getPicture(self,jid):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def group_create(self, subject):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def group_addParticipants(self, jid, participants):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def group_removeParticipants(self, jid, participants):
		pass
	
	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def group_setPicture(self, jid, filepath):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def group_end(self, jid):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def group_setSubject(self, jid, subject):
		pass

	
	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def group_getParticipants(self, jid):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def presence_sendAvailable(self):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def presence_request(self, jid):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def presence_sendUnavailable(self):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def presence_sendAvailableForChat(self):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def presence_subscribe(self, jid):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def presence_unsubscribe(self, jid):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def contact_getProfilePicture(self, jid):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def picture_getIds(self,jids):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def profile_getPicture(self):
		pass
	
	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def profile_setStatus(self, status):
		pass
	
	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def profile_setPicture(self, filepath):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def ready(self):
		pass

	@dbus.service.method(DBUS_INTERFACE)
	@interfaceMethod
	def disconnect(self, reason):
		pass


########NEW FILE########
__FILENAME__ = Interface
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''


import threading
class SignalInterfaceBase(object):

	signals = [	
			
			"auth_success",
			"auth_fail",
			
			"message_received", #k
			"image_received",
			"vcard_received",
			"video_received",
			"audio_received",
			"location_received",
			
			"message_error",

			"receipt_messageSent", #k
			"receipt_messageDelivered", #k
			"receipt_visible", #k
			"receipt_broadcastSent",
			"status_dirty",

			"presence_updated", #k
			"presence_available", #k
			"presence_unavailable", #k
			
			"group_subjectReceived",
			"group_createSuccess",
			"group_createFail",
			"group_endSuccess",
			"group_gotInfo",
			"group_infoError",
			"group_addParticipantsSuccess",
			"group_removeParticipantsSuccess",
			"group_gotParticipants",
			"group_setSubjectSuccess",
			"group_messageReceived",
			"group_imageReceived",
			"group_vcardReceived",
			"group_videoReceived",
			"group_audioReceived",
			"group_locationReceived",
			"group_setPictureSuccess",
			"group_setPictureError",
			"group_gotPicture",
			"group_gotGroups",			
			
			"notification_contactProfilePictureUpdated",
			"notification_contactProfilePictureRemoved",
			"notification_groupPictureUpdated",
			"notification_groupPictureRemoved",
			"notification_groupParticipantAdded",
			"notification_groupParticipantRemoved",

			"contact_gotProfilePictureId",
			"contact_gotProfilePicture",
			"contact_typing",
			"contact_paused",
			
			"profile_setPictureSuccess",
			"profile_setPictureError",
			"profile_setStatusSuccess",

			"ping",
			"pong",
			"disconnected",
			
			"media_uploadRequestSuccess",
			"media_uploadRequestFailed",
			"media_uploadRequestDuplicate"
		]
	
	def __init__(self):#@@TODO unified naming pattern
		self.registeredSignals = {}
	
	def getSignals(self):
		return self.signals

	def registerListener(self,signalName, callback):
		if self.hasSignal(signalName):
			if self.isRegistered(signalName):
				self.registeredSignals[signalName].append(callback)
			else:
				self.registeredSignals[signalName] = [callback]
				
	def _sendAsync(self, signalName, args=()):
		#print "Sending signal %s" % signalName
		listeners = self.getListeners(signalName)
		for l in listeners:
			threading.Thread(target = l, args = args).start()

	def send(self, signalName, args = ()):
		self._sendAsync(signalName, args)
	
	def getListeners(self, signalName):
		if self.hasSignal(signalName):
			
			
			try:
				self.registeredSignals[signalName]
				return self.registeredSignals[signalName]
			except KeyError:
				pass

		return []

	def isRegistered(self, signalName):
		try:
			self.registeredSignals[signalName]
			return True
		except KeyError:
			return False
	
	def hasSignal(self, signalName):
		try:
			self.signals.index(signalName)
			return True

		except ValueError:
			return False

class MethodInterfaceBase(object):

	methods = [	
			"getVersion",

			"auth_login",
			"message_send", #B
			"message_imageSend",
			"message_audioSend",
			"message_videoSend",
			"message_locationSend",
			"message_vcardSend",

			"message_ack", #BF

			"notification_ack",

			"clientconfig_send",

			"delivered_ack", #B

			"visible_ack", #B

			"ping", #B
			"pong", #B

			"typing_send", #B
			"typing_paused", #B

			"subject_ack", #B

			"group_getGroups",
			"group_getInfo",
			"group_create",
			"group_addParticipants",
			"group_removeParticipants",
			"group_end",
			"group_setSubject",
			"group_setPicture",
			"group_getParticipants",
			"group_getPicture",

			"picture_get",
			"picture_getIds",

			"contact_getProfilePicture",

			"presence_request", #B
			"presence_unsubscribe", #B
			"presence_subscribe", #B
			"presence_sendAvailableForChat", #B
			"presence_sendAvailable", #B
			"presence_sendUnavailable", #B
			
			"profile_getPicture",
			"profile_setPicture",
			"profile_setStatus",

			
			"ready",
			"disconnect",
			
			"message_broadcast",
			
			"media_requestUpload"
			]
	def __init__(self):
		self.registeredMethods = {}


	def call(self, methodName, params=()):
		#print "SHOULD CALL"
		#print methodName
		callback = self.getCallback(methodName)
		if callback:
			return callback(*params)
		#@@TODO raise no method exception
		return None

	def getMethods(self):
		return self.methods

	def getCallback(self, methodName):
		if self.hasMethod(methodName):
			return self.registeredMethods[methodName]

		return None

	def isRegistered(self, methodName):
		try:
			self.registeredMethods[methodName]
			return True
		except KeyError:
			return False
	
	def registerCallback(self, methodName, callback):
		if self.hasMethod(methodName):
			self.registeredMethods[methodName] = callback

	def hasMethod(self, methodName):
		try:
			self.methods.index(methodName)
			return True

		except ValueError:
			return False

########NEW FILE########
__FILENAME__ = LibInterface
import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)


from Interface import SignalInterfaceBase, MethodInterfaceBase

class LibSignalInterface(SignalInterfaceBase):
	def __init__(self):
		super(LibSignalInterface,self).__init__();
		
class LibMethodInterface(MethodInterfaceBase):
	def __init__(self):
		super(LibMethodInterface,self).__init__();


########NEW FILE########
__FILENAME__ = downloader
from ..Common.Http.warequest import WARequest
import tempfile, sys

if sys.version_info >= (3, 0):
    from urllib.request import urlopen
    from urllib.parse import urlencode
else:
    from urllib2 import urlopen
    from urllib import urlencode

class MediaDownloader(WARequest):
    def __init__(self, successClbk = None, errorClbk = None, progressCallback = None):
        
        super(MediaDownloader, self).__init__()
        
        self.successCallback = successClbk
        self.errorCallback = errorClbk
        self.progressCallback = progressCallback
        

    def download(self, url = ""):
        try:
            
            if not url:
                if self.url:
                    url = "https://" if self.port == 443 else "http://"
                    url = url + self.url
                    url = url + "?" + urlencode(self.params)
                    print(url)
                else:
                    raise Exception("No url specified for fetching")
            
            u = urlopen(url)
            
            path = tempfile.mkstemp()[1]
            f = open(path, "wb")
            meta = u.info()

            if sys.version_info >= (3, 0):
                fileSize = int(u.getheader("Content-Length"))
            else:
                fileSize = int(meta.getheaders("Content-Length")[0])

            fileSizeDl = 0
            blockSz = 8192
            lastEmit = 0
            while True:
                buf = u.read(blockSz)
                
                if not buf:
                    break

                fileSizeDl += len(buf)
                f.write(buf)
                status = (fileSizeDl * 100 / fileSize)
            
                if self.progressCallback and lastEmit != status:
                    self.progressCallback(int(status))
                    lastEmit = status;
            
            f.close()
            if self.successCallback:
                self.successCallback(path)
        except:
            print("Error occured at transfer %s"%sys.exc_info()[1])
            if self.errorCallback:
                self.errorCallback();
########NEW FILE########
__FILENAME__ = uploader
from ..Common.Http.warequest import WARequest
from ..Common.Http.waresponseparser import JSONResponseParser
import socket, ssl, mimetypes, os, hashlib, sys
from time import sleep

class MediaUploader(WARequest):
    def __init__(self, jid, accountJid, successClbk = None, errorClbk = None, progressCallback = None):
        super(MediaUploader, self).__init__()

        #self.url = "mms819.whatsapp.net"
        
        self.jid = jid;
        self.accountJid = accountJid;

        self.successCallback = successClbk
        self.errorCallback = errorClbk
        self.progressCallback = progressCallback
        
        self.pvars = ["name", "type", "size", "url", "error", "mimetype", "filehash", "width", "height"]
        
        self.setParser(JSONResponseParser())
        
        self.sock = socket.socket();
        
    def upload(self, sourcePath, uploadUrl):
        
        _host = uploadUrl.replace("https://","")

        self.url = _host[:_host.index('/')]
        
        
        try:
            filename = os.path.basename(sourcePath)
            filetype = mimetypes.guess_type(filename)[0]
            filesize = os.path.getsize(sourcePath)
    
            self.sock.connect((self.url, self.port));
            ssl_sock = ssl.wrap_socket(self.sock)
    
            m = hashlib.md5()
            m.update(filename.encode())
            crypto = m.hexdigest() + os.path.splitext(filename)[1]
    
            boundary = "zzXXzzYYzzXXzzQQ"#"-------" + m.hexdigest() #"zzXXzzYYzzXXzzQQ"
            contentLength = 0

            hBAOS = "--" + boundary + "\r\n"
            hBAOS += "Content-Disposition: form-data; name=\"to\"\r\n\r\n"
            hBAOS += self.jid + "\r\n"
            hBAOS += "--" + boundary + "\r\n"
            hBAOS += "Content-Disposition: form-data; name=\"from\"\r\n\r\n"
            hBAOS += self.accountJid.replace("@whatsapp.net","") + "\r\n"
    
            hBAOS += "--" + boundary + "\r\n"
            hBAOS += "Content-Disposition: form-data; name=\"file\"; filename=\"" + crypto + "\"\r\n"
            hBAOS  += "Content-Type: " + filetype + "\r\n\r\n"
    
            fBAOS = "\r\n--" + boundary + "--\r\n"
            
            contentLength += len(hBAOS)
            contentLength += len(fBAOS)
            contentLength += filesize
    
            #POST = "POST https://mms.whatsapp.net/client/iphone/upload.php HTTP/1.1\r\n"
            POST = "POST %s\r\n" % uploadUrl
            POST += "Content-Type: multipart/form-data; boundary=" + boundary + "\r\n"
            POST += "Host: %s\r\n" % self.url
            POST += "User-Agent: %s\r\n" % self.getUserAgent()
            POST += "Content-Length: " + str(contentLength) + "\r\n\r\n"
            
            self._d(POST)
            self._d("sending REQUEST ")
            self._d(hBAOS)
            ssl_sock.write(bytearray(POST.encode()))
            ssl_sock.write(bytearray(hBAOS.encode()))
    
            totalsent = 0
            buf = 1024
            f = open(sourcePath, 'rb')
            stream = f.read()
            f.close()
            status = 0
            lastEmit = 0
    
            while totalsent < int(filesize):
                ssl_sock.write(stream[:buf])
                status = totalsent * 100 / filesize
                if lastEmit!=status and status!=100 and filesize>12288:
                    if self.progressCallback:
                        self.progressCallback(int(status))
                lastEmit = status
                stream = stream[buf:]
                totalsent = totalsent + buf
    
            ssl_sock.write(bytearray(fBAOS.encode()))
    
            sleep(1)
            self._d("Reading response...")
            data = ssl_sock.recv(8192)
            data += ssl_sock.recv(8192)
            data += ssl_sock.recv(8192)
            data += ssl_sock.recv(8192)
            data += ssl_sock.recv(8192)
            data += ssl_sock.recv(8192)
            data += ssl_sock.recv(8192)
            self._d(data)
            
            if self.progressCallback:
                self.progressCallback(100)
                
            
            lines = data.decode().splitlines()
            
            
            result = None

            for l in lines:
                if l.startswith("{"):
                    result = self.parser.parse(l, self.pvars)
                    break
            
            if not result:
                raise Exception("json data not found")
            

            self._d(result)
            
            if result["url"] is not None:
                if self.successCallback:
                    self.successCallback(result["url"])
            else:
                self.errorCallback()

        except:
            print("Error occured at transfer %s"%sys.exc_info()[1])
            if self.errorCallback:
                self.errorCallback();

########NEW FILE########
__FILENAME__ = coderequest
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

from Yowsup.Common.Http.warequest import WARequest
from Yowsup.Common.Http.waresponseparser import XMLResponseParser
import hashlib
from xml.dom import minidom

class WACodeRequest(WARequest):

	def __init__(self,cc, p_in, method="sms"):
		super(WACodeRequest,self).__init__();

		self.addParam("cc",cc);
		self.addParam("in",p_in);
		self.addParam("to",cc+p_in);
		self.addParam("lc","US");
		self.addParam("lg","en");
		self.addParam("mcc","000");
		self.addParam("mnc","000");
		self.addParam("imsi","000000000000000");
		self.addParam("method",method);

		self.addParam("token", self.getToken(p_in))

		self.url = "r.whatsapp.net/v1/code.php"

		self.pvars = {"status": "/code/response/@status",
					  "result": "/code/response/@result"
					}

		self.type = "POST"

		self.setParser(XMLResponseParser())


########NEW FILE########
__FILENAME__ = existsrequest
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

from Yowsup.Common.Http.warequest import WARequest
from Yowsup.Common.Http.waresponseparser import XMLResponseParser

class WAExistsRequest(WARequest):

	def __init__(self,cc, p_in, password):
		super(WAExistsRequest,self).__init__();

		self.addParam("cc",cc);
		self.addParam("in",p_in);
		self.addParam("udid", password);

		self.url = "r.whatsapp.net/v1/exist.php"

		self.pvars = {"status": "/exist/response/@status",
					  "result": "/exist/response/@result"
					}
		
		self.type = "POST"
		self.setParser(XMLResponseParser())
########NEW FILE########
__FILENAME__ = regrequest
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

from Yowsup.Common.Http.warequest import WARequest
from Yowsup.Common.Http.waresponseparser import XMLResponseParser

class WARegRequest(WARequest):
	
	def __init__(self,cc, p_in, code, password):
		super(WARegRequest,self).__init__();
		
		self.addParam("cc",cc);
		self.addParam("in",p_in);
		self.addParam("code",code);
		self.addParam("udid", password);

		self.url = "r.whatsapp.net/v1/register.php"
		
		self.pvars = {"status": "/register/response/@status",
					  "login": "/register/response/@login",
					  "result": "/register/response/@result"
					}

		self.type = "POST"

		self.setParser(XMLResponseParser())		
########NEW FILE########
__FILENAME__ = coderequest
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

from Yowsup.Common.Http.warequest import WARequest
from Yowsup.Common.Http.waresponseparser import JSONResponseParser
from Yowsup.Common.constants import Constants
from Yowsup.Common.utilities import Utilities
import os
class WACodeRequest(WARequest):

	def __init__(self,cc, p_in, idx, method="sms"):
		super(WACodeRequest,self).__init__();

		self.p_in = p_in #number

		self.addParam("cc", cc);
		self.addParam("in", p_in);
		self.addParam("lc", "US");
		self.addParam("lg", "en");
		self.addParam("mcc", "000");
		self.addParam("mnc", "000");
		self.addParam("method", method);
		self.addParam("id", idx)

		self.currentToken = Utilities.readToken()

		if self.currentToken:
			print("Read token from %s " % os.path.expanduser(Constants.tokenStorage))
		else:
			self.currentToken = Constants.tokenData

		self.addParam("token", self.getToken(p_in, self.currentToken["t"]))

		self.url = "v.whatsapp.net/v2/code"

		self.pvars = ["status","reason","length", "method", "retry_after", "code", "param"] +\
					["login", "pw", "type", "expiration", "kind", "price", "cost", "currency", "price_expiration"]

		self.setParser(JSONResponseParser())

	def send(self, parser = None):
		res = super(WACodeRequest, self).send(parser)

		#attempt recovery by fetching new token
		if res:
			if res["status"] == "fail":
				if res["reason"] in ("old_version", "bad_token") and Utilities.tokenCacheEnabled:

					print("Failed, reason: %s. Checking for a new token.." % res["reason"])

					res = WARequest.sendRequest(Constants.tokenSource[0], 80, Constants.tokenSource[1], {}, {})

					if res:
						tokenData = res.read()
						pvars = ["v", "r", "u", "t", "d"]
						jParser = JSONResponseParser()
						parsed = jParser.parse(tokenData.decode(), pvars)

						if(
									parsed["v"] != self.currentToken["v"]
							or 	parsed["r"] != self.currentToken["r"]
							or 	parsed["u"] != self.currentToken["u"]
							or 	parsed["t"] != self.currentToken["t"]
							or 	parsed["d"] != self.currentToken["d"]
						):
							self.currentToken = parsed
							print("Fetched a new token, persisting !")

							self.removeParam("token")

							print("Now retrying the request..")
							self.addParam("token", self.getToken(self.p_in, self.currentToken["t"]))
						else:
							print("No new tokens :(")

						res = super(WACodeRequest, self).send(parser)

						if res and res["status"] != "fail":
							Utilities.persistToken(tokenData) #good token

		return res	


########NEW FILE########
__FILENAME__ = existsrequest
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

from Yowsup.Common.Http.warequest import WARequest
from Yowsup.Common.Http.waresponseparser import JSONResponseParser

class WAExistsRequest(WARequest):
	
	def __init__(self,cc, p_in, idx):
		super(WAExistsRequest,self).__init__();

		self.addParam("cc",cc);
		self.addParam("in",p_in);
		self.addParam("id", idx);

		self.url = "v.whatsapp.net/v2/exist"

		self.pvars = ["status", "reason", "sms_length", "voice_length", "result","param", "pw", "login", "type", "expiration", "kind",
					"price", "cost", "currency", "price_expiration"
					]

		self.setParser(JSONResponseParser())
########NEW FILE########
__FILENAME__ = regrequest
'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

from Yowsup.Common.Http.warequest import WARequest
from Yowsup.Common.Http.waresponseparser import JSONResponseParser

class WARegRequest(WARequest):

	def __init__(self,cc, p_in, code, idx):
		super(WARegRequest,self).__init__();

		self.addParam("cc", cc);
		self.addParam("in", p_in);
		self.addParam("id", idx)
		self.addParam("code", code)

		self.url = "v.whatsapp.net/v2/register"

		self.pvars = ["status", "login", "pw", "type", "expiration", "kind", "price", "cost", "currency", "price_expiration",
					  "reason","retry_after"]

		self.setParser(JSONResponseParser())
		
	def register(self):
		return self.send();
########NEW FILE########
