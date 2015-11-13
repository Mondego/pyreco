__FILENAME__ = hpfeeds
#********************************************************************************
#*                               Dionaea
#*                           - catches bugs -
#*
#*
#*
#* Copyright (C) 2010  Mark Schloesser
#* 
#* This program is free software; you can redistribute it and/or
#* modify it under the terms of the GNU General Public License
#* as published by the Free Software Foundation; either version 2
#* of the License, or (at your option) any later version.
#* 
#* This program is distributed in the hope that it will be useful,
#* but WITHOUT ANY WARRANTY; without even the implied warranty of
#* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#* GNU General Public License for more details.
#* 
#* You should have received a copy of the GNU General Public License
#* along with this program; if not, write to the Free Software
#* Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#* 
#* 
#*             contact nepenthesdev@gmail.com  
#*
#*******************************************************************************/

from dionaea.core import ihandler, incident, g_dionaea, connection
from dionaea.util import sha512file

import os
import logging
import struct
import hashlib
import json
try: import pyev
except: pyev = None

logger = logging.getLogger('hpfeeds')
logger.setLevel(logging.DEBUG)

#def DEBUGPERF(msg):
#	print(msg)
#logger.debug = DEBUGPERF
#logger.critical = DEBUGPERF

BUFSIZ = 16384

OP_ERROR        = 0
OP_INFO         = 1
OP_AUTH         = 2
OP_PUBLISH      = 3
OP_SUBSCRIBE    = 4

MAXBUF = 1024**2
SIZES = {
	OP_ERROR: 5+MAXBUF,
	OP_INFO: 5+256+20,
	OP_AUTH: 5+256+20,
	OP_PUBLISH: 5+MAXBUF,
	OP_SUBSCRIBE: 5+256*2,
}

CONNCHAN = 'dionaea.connections'
CAPTURECHAN = 'dionaea.capture'
DCECHAN = 'dionaea.dcerpcrequests'
SCPROFCHAN = 'dionaea.shellcodeprofiles'
UNIQUECHAN = 'mwbinary.dionaea.sensorunique'

class BadClient(Exception):
        pass

# packs a string with 1 byte length field
def strpack8(x):
	if isinstance(x, str): x = x.encode('latin1')
	return struct.pack('!B', len(x)%0xff) + x

# unpacks a string with 1 byte length field
def strunpack8(x):
	l = x[0]
	return x[1:1+l], x[1+l:]
	
def msghdr(op, data):
	return struct.pack('!iB', 5+len(data), op) + data
def msgpublish(ident, chan, data):
	return msghdr(OP_PUBLISH, strpack8(ident) + strpack8(chan) + data)
def msgsubscribe(ident, chan):
	if isinstance(chan, str): chan = chan.encode('latin1')
	return msghdr(OP_SUBSCRIBE, strpack8(ident) + chan)
def msgauth(rand, ident, secret):
	hash = hashlib.sha1(bytes(rand)+secret).digest()
	return msghdr(OP_AUTH, strpack8(ident) + hash)

class FeedUnpack(object):
	def __init__(self):
		self.buf = bytearray()
	def __iter__(self):
		return self
	def __next__(self):
		return self.unpack()
	def feed(self, data):
		self.buf.extend(data)
	def unpack(self):
		if len(self.buf) < 5:
			raise StopIteration('No message.')

		ml, opcode = struct.unpack('!iB', self.buf[:5])
		if ml > SIZES.get(opcode, MAXBUF):
			raise BadClient('Not respecting MAXBUF.')

		if len(self.buf) < ml:
			raise StopIteration('No message.')

		data = self.buf[5:ml]
		del self.buf[:ml]
		return opcode, data

class hpclient(connection):
	def __init__(self, server, port, ident, secret):
		logger.debug('hpclient init')
		connection.__init__(self, 'tcp')
		self.unpacker = FeedUnpack()
		self.ident, self.secret = ident.encode('latin1'), secret.encode('latin1')

		self.connect(server, port)
		self.timeouts.reconnect = 10.0
		self.sendfiles = []
		self.msgqueue = []
		self.filehandle = None
		self.connected = False

	def handle_established(self):
		self.connected = True
		logger.debug('hpclient established')

	def handle_io_in(self, indata):
		self.unpacker.feed(indata)

		# if we are currently streaming a file, delay handling incoming messages
		if self.filehandle:
			return len(indata)

		try:
			for opcode, data in self.unpacker:
				logger.debug('hpclient msg opcode {0} data {1}'.format(opcode, data))
				if opcode == OP_INFO:
					name, rand = strunpack8(data)
					logger.debug('hpclient server name {0} rand {1}'.format(name, rand))
					self.send(msgauth(rand, self.ident, self.secret))

				elif opcode == OP_PUBLISH:
					ident, data = strunpack8(data)
					chan, data = strunpack8(data)
					logger.debug('publish to {0} by {1}: {2}'.format(chan, ident, data))

				elif opcode == OP_ERROR:
					logger.debug('errormessage from server: {0}'.format(data))
				else:
					logger.debug('unknown opcode message: {0}'.format(opcode))
		except BadClient:
			logger.critical('unpacker error, disconnecting.')
			self.close()

		return len(indata)

	def handle_io_out(self):
		if self.filehandle: self.sendfiledata()
		else:
			if self.msgqueue:
				m = self.msgqueue.pop(0)
				self.send(m)

	def publish(self, channel, **kwargs):
		if self.filehandle: self.msgqueue.append(msgpublish(self.ident, channel, json.dumps(kwargs).encode('latin1')))
		else: self.send(msgpublish(self.ident, channel, json.dumps(kwargs).encode('latin1')))

	def sendfile(self, filepath):
		# does not read complete binary into memory, read and send chunks
		if not self.filehandle:
			self.sendfileheader(filepath)
			self.sendfiledata()
		else: self.sendfiles.append(filepath)

	def sendfileheader(self, filepath):
		self.filehandle = open(filepath, 'rb')
		fsize = os.stat(filepath).st_size
		headc = strpack8(self.ident) + strpack8(UNIQUECHAN)
		headh = struct.pack('!iB', 5+len(headc)+fsize, OP_PUBLISH)
		self.send(headh + headc)

	def sendfiledata(self):
		tmp = self.filehandle.read(BUFSIZ)
		if not tmp:
			if self.sendfiles:
				fp = self.sendfiles.pop(0)
				self.sendfileheader(fp)
			else:
				self.filehandle = None
				self.handle_io_in(b'')
		else:
			self.send(tmp)

	def handle_timeout_idle(self):
		pass

	def handle_disconnect(self):
		logger.info('hpclient disconnect')
		self.connected = False
		return 1

	def handle_error(self, err):
		logger.warn('hpclient error {0}'.format(err))
		self.connected = False
		return 1

class hpfeedihandler(ihandler):
	def __init__(self, config):
		logger.debug('hpfeedhandler init')
		self.client = hpclient(config['server'], int(config['port']), config['ident'], config['secret'])
		ihandler.__init__(self, '*')

		self.dynip_resolve = config.get('dynip_resolve', '')
		self.dynip_timer = None
		self.ownip = None
		if self.dynip_resolve and 'http' in self.dynip_resolve:
			if pyev == None:
				logger.debug('You are missing the python pyev binding in your dionaea installation.')
			else:
				logger.debug('hpfeedihandler will use dynamic IP resolving!')
				self.loop = pyev.default_loop()
				self.dynip_timer = pyev.Timer(2., 300, self.loop, self._dynip_resolve)
				self.dynip_timer.start()

	def stop(self):
		if self.dynip_timer:
			self.dynip_timer.stop()
			self.dynip_timer = None
			self.loop = None

	def _ownip(self, icd):
		if self.dynip_resolve and 'http' in self.dynip_resolve and pyev != None:
			if self.ownip: return self.ownip
			else: raise Exception('Own IP not yet resolved!')
		return icd.con.local.host

	def __del__(self):
		#self.client.close()
		pass

	def connection_publish(self, icd, con_type):
		try:
			con=icd.con
			self.client.publish(CONNCHAN, connection_type=con_type, connection_transport=con.transport, connection_protocol=con.protocol, remote_host=con.remote.host, remote_port=con.remote.port, remote_hostname=con.remote.hostname, local_host=self._ownip(icd), local_port=con.local.port)
		except Exception as e:
			logger.warn('exception when publishing: {0}'.format(e))

	def handle_incident(self, i):
		pass
	
	def handle_incident_dionaea_connection_tcp_listen(self, icd):
		self.connection_publish(icd, 'listen')
		con=icd.con
		logger.info("listen connection on %s:%i" % 
			(con.remote.host, con.remote.port))

	def handle_incident_dionaea_connection_tls_listen(self, icd):
		self.connection_publish(icd, 'listen')
		con=icd.con
		logger.info("listen connection on %s:%i" % 
			(con.remote.host, con.remote.port))

	def handle_incident_dionaea_connection_tcp_connect(self, icd):
		self.connection_publish(icd, 'connect')
		con=icd.con
		logger.info("connect connection to %s/%s:%i from %s:%i" % 
			(con.remote.host, con.remote.hostname, con.remote.port, self._ownip(icd), con.local.port))

	def handle_incident_dionaea_connection_tls_connect(self, icd):
		self.connection_publish(icd, 'connect')
		con=icd.con
		logger.info("connect connection to %s/%s:%i from %s:%i" % 
			(con.remote.host, con.remote.hostname, con.remote.port, self._ownip(icd), con.local.port))

	def handle_incident_dionaea_connection_udp_connect(self, icd):
		self.connection_publish(icd, 'connect')
		con=icd.con
		logger.info("connect connection to %s/%s:%i from %s:%i" % 
			(con.remote.host, con.remote.hostname, con.remote.port, self._ownip(icd), con.local.port))

	def handle_incident_dionaea_connection_tcp_accept(self, icd):
		self.connection_publish(icd, 'accept')
		con=icd.con
		logger.info("accepted connection from  %s:%i to %s:%i" %
			(con.remote.host, con.remote.port, self._ownip(icd), con.local.port))

	def handle_incident_dionaea_connection_tls_accept(self, icd):
		self.connection_publish(icd, 'accept')
		con=icd.con
		logger.info("accepted connection from %s:%i to %s:%i" % 
			(con.remote.host, con.remote.port, self._ownip(icd), con.local.port))


	def handle_incident_dionaea_connection_tcp_reject(self, icd):
		self.connection_publish(icd, 'reject')
		con=icd.con
		logger.info("reject connection from %s:%i to %s:%i" % 
			(con.remote.host, con.remote.port, self._ownip(icd), con.local.port))

	def handle_incident_dionaea_connection_tcp_pending(self, icd):
		self.connection_publish(icd, 'pending')
		con=icd.con
		logger.info("pending connection from %s:%i to %s:%i" % 
			(con.remote.host, con.remote.port, self._ownip(icd), con.local.port))
	
	def handle_incident_dionaea_download_complete_unique(self, i):
		self.handle_incident_dionaea_download_complete_again(i)
		if not hasattr(i, 'con') or not self.client.connected: return
		logger.debug('unique complete, publishing md5 {0}, path {1}'.format(i.md5hash, i.file))
		try:
			self.client.sendfile(i.file)
		except Exception as e:
			logger.warn('exception when publishing: {0}'.format(e))

	def handle_incident_dionaea_download_complete_again(self, i):
		if not hasattr(i, 'con') or not self.client.connected: return
		logger.debug('hash complete, publishing md5 {0}, path {1}'.format(i.md5hash, i.file))
		try:
			sha512 = sha512file(i.file)
			self.client.publish(CAPTURECHAN, saddr=i.con.remote.host, 
				sport=str(i.con.remote.port), daddr=self._ownip(i),
				dport=str(i.con.local.port), md5=i.md5hash, sha512=sha512,
				url=i.url
			)
		except Exception as e:
			logger.warn('exception when publishing: {0}'.format(e))

	def handle_incident_dionaea_modules_python_smb_dcerpc_request(self, i):
		if not hasattr(i, 'con') or not self.client.connected: return
		logger.debug('dcerpc request, publishing uuid {0}, opnum {1}'.format(i.uuid, i.opnum))
		try:
			self.client.publish(DCECHAN, uuid=i.uuid, opnum=i.opnum,
				saddr=i.con.remote.host, sport=str(i.con.remote.port),
				daddr=self._ownip(i), dport=str(i.con.local.port),
			)
		except Exception as e:
			logger.warn('exception when publishing: {0}'.format(e))

	def handle_incident_dionaea_module_emu_profile(self, icd):
		if not hasattr(icd, 'con') or not self.client.connected: return
		logger.debug('emu profile, publishing length {0}'.format(len(icd.profile)))
		try:
			self.client.publish(SCPROFCHAN, profile=icd.profile)
		except Exception as e:
			logger.warn('exception when publishing: {0}'.format(e))

	def _dynip_resolve(self, events, data):
		i = incident("dionaea.upload.request")
		i._url = self.dynip_resolve
		i._callback = "dionaea.modules.python.hpfeeds.dynipresult"
		i.report()

	def handle_incident_dionaea_modules_python_hpfeeds_dynipresult(self, icd):
		fh = open(icd.path, mode="rb")
		self.ownip = fh.read().strip().decode('latin1')
		logger.debug('resolved own IP to: {0}'.format(self.ownip))
		fh.close()


########NEW FILE########
__FILENAME__ = hpfeeds
from kippo.core import dblog
from twisted.python import log

import os
import struct
import hashlib
import json
import socket
import uuid

BUFSIZ = 16384

OP_ERROR        = 0
OP_INFO         = 1
OP_AUTH         = 2
OP_PUBLISH      = 3
OP_SUBSCRIBE    = 4

MAXBUF = 1024**2
SIZES = {
	OP_ERROR: 5+MAXBUF,
	OP_INFO: 5+256+20,
	OP_AUTH: 5+256+20,
	OP_PUBLISH: 5+MAXBUF,
	OP_SUBSCRIBE: 5+256*2,
}

KIPPOCHAN = 'kippo.sessions'

class BadClient(Exception):
        pass

# packs a string with 1 byte length field
def strpack8(x):
	if isinstance(x, str): x = x.encode('latin1')
	return struct.pack('!B', len(x)) + x

# unpacks a string with 1 byte length field
def strunpack8(x):
	l = x[0]
	return x[1:1+l], x[1+l:]
	
def msghdr(op, data):
	return struct.pack('!iB', 5+len(data), op) + data
def msgpublish(ident, chan, data):
	return msghdr(OP_PUBLISH, strpack8(ident) + strpack8(chan) + data)
def msgsubscribe(ident, chan):
	if isinstance(chan, str): chan = chan.encode('latin1')
	return msghdr(OP_SUBSCRIBE, strpack8(ident) + chan)
def msgauth(rand, ident, secret):
	hash = hashlib.sha1(bytes(rand)+secret).digest()
	return msghdr(OP_AUTH, strpack8(ident) + hash)

class FeedUnpack(object):
	def __init__(self):
		self.buf = bytearray()
	def __iter__(self):
		return self
	def next(self):
		return self.unpack()
	def feed(self, data):
		self.buf.extend(data)
	def unpack(self):
		if len(self.buf) < 5:
			raise StopIteration('No message.')

		ml, opcode = struct.unpack('!iB', buffer(self.buf,0,5))
		if ml > SIZES.get(opcode, MAXBUF):
			raise BadClient('Not respecting MAXBUF.')

		if len(self.buf) < ml:
			raise StopIteration('No message.')

		data = bytearray(buffer(self.buf, 5, ml-5))
		del self.buf[:ml]
		return opcode, data

class hpclient(object):
	def __init__(self, server, port, ident, secret, debug):
		print 'hpfeeds client init broker {0}:{1}, identifier {2}'.format(server, port, ident)
		self.server, self.port = server, int(port)
		self.ident, self.secret = ident.encode('latin1'), secret.encode('latin1')
		self.debug = debug
		self.unpacker = FeedUnpack()
		self.state = 'INIT'

		self.connect()
		self.sendfiles = []
		self.filehandle = None

	def connect(self):
		self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.s.settimeout(3)
		try: self.s.connect((self.server, self.port))
		except:
			print 'hpfeeds client could not connect to broker.'
			self.s = None
		else:
			self.s.settimeout(None)
			self.handle_established()

	def send(self, data):
		if not self.s: return
		self.s.send(data)

	def close(self):
		self.s.close()
		self.s = None

	def handle_established(self):
		if self.debug: print 'hpclient established'
		while self.state != 'GOTINFO':
			self.read()

		#quickly try to see if there was an error message
		self.s.settimeout(0.5)
		self.read()
		self.s.settimeout(None)

	def read(self):
		if not self.s: return
		try: d = self.s.recv(BUFSIZ)
		except socket.timeout:
			return

		if not d:
			if self.debug: log.msg('hpclient connection closed?')
			self.close()
			return

		self.unpacker.feed(d)
		try:
			for opcode, data in self.unpacker:
				if self.debug: log.msg('hpclient msg opcode {0} data {1}'.format(opcode, data))
				if opcode == OP_INFO:
					name, rand = strunpack8(data)
					if self.debug: log.msg('hpclient server name {0} rand {1}'.format(name, rand))
					self.send(msgauth(rand, self.ident, self.secret))
					self.state = 'GOTINFO'

				elif opcode == OP_PUBLISH:
					ident, data = strunpack8(data)
					chan, data = strunpack8(data)
					if self.debug: log.msg('publish to {0} by {1}: {2}'.format(chan, ident, data))

				elif opcode == OP_ERROR:
					log.err('errormessage from server: {0}'.format(data))
				else:
					log.err('unknown opcode message: {0}'.format(opcode))
		except BadClient:
			log.err('unpacker error, disconnecting.')
			self.close()

	def publish(self, channel, **kwargs):
		try:
			self.send(msgpublish(self.ident, channel, json.dumps(kwargs).encode('latin1')))
		except Exception, e:
			log.err('connection to hpfriends lost: {0}'.format(e))
			log.err('connecting')
			self.connect()
			self.send(msgpublish(self.ident, channel, json.dumps(kwargs).encode('latin1')))

	def sendfile(self, filepath):
		# does not read complete binary into memory, read and send chunks
		if not self.filehandle:
			self.sendfileheader(i.file)
			self.sendfiledata()
		else: self.sendfiles.append(filepath)

	def sendfileheader(self, filepath):
		self.filehandle = open(filepath, 'rb')
		fsize = os.stat(filepath).st_size
		headc = strpack8(self.ident) + strpack8(UNIQUECHAN)
		headh = struct.pack('!iB', 5+len(headc)+fsize, OP_PUBLISH)
		self.send(headh + headc)

	def sendfiledata(self):
		tmp = self.filehandle.read(BUFSIZ)
		if not tmp:
			if self.sendfiles:
				fp = self.sendfiles.pop(0)
				self.sendfileheader(fp)
			else:
				self.filehandle = None
				self.handle_io_in(b'')
		else:
			self.send(tmp)


class DBLogger(dblog.DBLogger):
	def start(self, cfg):
		print 'hpfeeds DBLogger start'

		server	= cfg.get('database_hpfeeds', 'server')
		port	= cfg.get('database_hpfeeds', 'port')
		ident	= cfg.get('database_hpfeeds', 'identifier')
		secret	= cfg.get('database_hpfeeds', 'secret')
		debug	= cfg.get('database_hpfeeds', 'debug')

		self.client = hpclient(server, port, ident, secret, debug)
		self.meta = {}

	# We have to return an unique ID
	def createSession(self, peerIP, peerPort, hostIP, hostPort):
		session = uuid.uuid4().hex
		self.meta[session] = {'peerIP': peerIP, 'peerPort': peerPort, 
		'hostIP': hostIP, 'hostPort': hostPort, 'loggedin': None,
		'credentials':[], 'version': None, 'ttylog': None }
		return session

	def handleConnectionLost(self, session, args):
		log.msg('publishing metadata to hpfeeds')
		meta = self.meta[session]
		ttylog = self.ttylog(session)
		if ttylog: meta['ttylog'] = ttylog.encode('hex')
		self.client.publish(KIPPOCHAN, **meta)

	def handleLoginFailed(self, session, args):
		u, p = args['username'], args['password']
		self.meta[session]['credentials'].append((u,p))

	def handleLoginSucceeded(self, session, args):
		u, p = args['username'], args['password']
		self.meta[session]['loggedin'] = (u,p)

	def handleCommand(self, session, args):
		pass

	def handleUnknownCommand(self, session, args):
		pass

	def handleInput(self, session, args):
		pass

	def handleTerminalSize(self, session, args):
		pass

	def handleClientVersion(self, session, args):
		v = args['version']
		self.meta[session]['version'] = v

# vim: set sw=4 et:

########NEW FILE########
__FILENAME__ = feedbroker
#!/usr/bin/env python

import sys

import struct
import hashlib
import collections
import random

import logging

from evnet import loop, unloop, listenplain, EventGen
from evnet.mongodb import MongoConn

FBIP = '0.0.0.0'
FBPORT = 10000
FBNAME = '@hp2'
MONGOIP = '127.0.0.1'
MONGOPORT = 27017

OP_ERROR	= 0
OP_INFO		= 1
OP_AUTH		= 2
OP_PUBLISH	= 3
OP_SUBSCRIBE	= 4
OP_UNSUBSCRIBE	= 5

MAXBUF = 10* (1024**2)
SIZES = {
	OP_ERROR: 5+MAXBUF,
	OP_INFO: 5+256+20,
	OP_AUTH: 5+256+20,
	OP_PUBLISH: 5+MAXBUF,
	OP_SUBSCRIBE: 5+256*2,
	OP_UNSUBSCRIBE: 5+256*2,
}

class BadClient(Exception):
	pass

class FeedUnpack(object):
	def __init__(self):
		self.buf = bytearray()
	def __iter__(self):
		return self
	def next(self):
		return self.unpack()
	def feed(self, data):
		self.buf.extend(data)
	def unpack(self):
		if len(self.buf) < 5:
			raise StopIteration('No message.')

		ml, opcode = struct.unpack('!iB', buffer(self.buf,0,5))
		if ml > SIZES.get(opcode, MAXBUF):
			raise BadClient('Not respecting MAXBUF.')

		if len(self.buf) < ml:
			raise StopIteration('No message.')
		
		data = bytearray(buffer(self.buf, 5, ml-5))
		del self.buf[:ml]
		return opcode, data


class FeedConn(EventGen):
	def __init__(self, conn, addr, db):
		EventGen.__init__(self)
		self.conn = conn
		self.addr = addr
		self.db = db
		self.pubchans = set()
		self.subchans = set()
		self.idents = set()
		self.delay = False

		self.rand = struct.pack('<I', random.randint(2**31,2**32-1))
		self.fu = FeedUnpack()

		conn._on('read', self.io_in)
		conn._on('close', self.closed)

		self.sendinfo()

	def sendinfo(self):
		self.conn.write(self.msginfo())

	def auth(self, ident, hash):
		p = self.db.query('hpfeeds.auth_key', {'identifier': str(ident)}, limit=1)
		p._when(self.checkauth, hash)

		def dbexc(e):
			logging.critical('Database query exception. {0}'.format(e))
			self.error('Database query exception.')
		
		p._except(dbexc)

		self.delay = True

	def checkauth(self, r, hash):
		if len(r) > 0:
			akobj = r[0]
			akhash = hashlib.sha1('{0}{1}'.format(self.rand, akobj['secret'])).digest()
			if akhash == hash:
				self.pubchans.update(akobj.get('publish', []))
				self.subchans.update(akobj.get('subscribe', []))
				self.idents.add(akobj['identifier'])
				logging.info('Auth success by {0}.'.format(akobj['identifier']))
			else:
				self.error('authfail.')
				logging.info('Auth failure by {0}.'.format(akobj['identifier']))
		else:
			self.error('authfail.')

		self.delay = False
		self.io_in(b'')
	
	def closed(self, reason):
		logging.debug('Connection closed, {0}'.format(reason))
		self._event('close', self)

	def may_publish(self, chan):
		return chan in self.pubchans

	def may_subscribe(self, chan):
		return chan in self.subchans

	def io_in(self, data):
		self.fu.feed(data)
		if self.delay:
			return
		try:
			for opcode, data in self.fu:
				if opcode == OP_PUBLISH:
					rest = buffer(data, 0)
					ident, rest = rest[1:1+ord(rest[0])], buffer(rest, 1+ord(rest[0]))
					chan, rest = rest[1:1+ord(rest[0])], buffer(rest, 1+ord(rest[0]))

					if not ident in self.idents:
						self.error('identfail.')
						continue

					if not self.may_publish(chan):
						self.error('accessfail.')
						continue
					
					self._event('publish', self, chan, data)
				elif opcode == OP_SUBSCRIBE:
					rest = buffer(data, 0)
					ident, chan = rest[1:1+ord(rest[0])], rest[1+ord(rest[0]):]

					if not ident in self.idents:
						self.error('identfail.')
						continue

					checkchan = chan
					if chan.endswith('..broker'): checkchan = chan.rsplit('..broker', 1)[0]

					if not self.may_subscribe(checkchan):
						self.error('accessfail.')
						continue

					self._event('subscribe', self, chan, ident)
				elif opcode == OP_UNSUBSCRIBE:
					rest = buffer(data, 0)
					ident, chan = rest[1:1+ord(rest[0])], rest[1+ord(rest[0]):]

					if not ident in self.idents:
						self.error('identfail.')
						continue

					if not self.may_subscribe(chan):
						self.error('accessfail.')
						continue

					self._event('unsubscribe', self, chan, ident)
				elif opcode == OP_AUTH:
					rest = buffer(data, 0)
					ident, hash = rest[1:1+ord(rest[0])], rest[1+ord(rest[0]):]
					self.auth(ident, hash)
					if self.delay:
						return

		except BadClient:
			self.conn.close()
			logging.warn('Disconnecting bad client: {0}'.format(self.addr))

	def forward(self, data):
		self.conn.write(self.msghdr(OP_PUBLISH, data))

	def error(self, emsg):
		self.conn.write(self.msgerror(emsg))

	def msgerror(self, emsg):
		return self.msghdr(OP_ERROR, emsg)

	def msginfo(self):
		return self.msghdr(OP_INFO, '{0}{1}{2}'.format(chr(len(FBNAME)%0xff), FBNAME, self.rand))

	def msghdr(self, op, data):
		return struct.pack('!iB', 5+len(data), op) + data

	def msgpublish(self, ident, chan, data):
		return self.msghdr(OP_PUBLISH, struct.pack('!B', len(ident)) + ident + struct.pack('!B', len(chan)) + chan + data)

	def publish(self, ident, chan, data):
		self.conn.write(self.msgpublish(ident, chan, data))

class FeedBroker(object):
	def __init__(self):
		self.ready = False

		self.db = None
		self.initdb()

		self.listener = listenplain(host=FBIP, port=FBPORT)
		self.listener._on('close', self._lclose)
		self.listener._on('connection', self._newconn)

		self.connections = set()
		self.subscribermap = collections.defaultdict(list)
		self.conn2chans = collections.defaultdict(list)

	def initdb(self):
		self.db = MongoConn(MONGOIP, MONGOPORT)
		self.db._on('ready', self._dbready)
		self.db._on('close', self._dbclose)

	def _dbready(self):
		self.ready = True
		logging.info('Database ready.')

	def _dbclose(self, e):
		logging.critical('Database connection closed ({0}). Exiting.'.format(e))
		unloop()

	def _lclose(self, e):
		logging.critical('Listener closed ({0}). Exiting.'.format(e))
		unloop()

	def _newconn(self, c, addr):
		logging.debug('Connection from {0}.'.format(addr))
		fc = FeedConn(c, addr, self.db)
		self.connections.add(fc)
		fc._on('close', self._connclose)
		fc._on('subscribe', self._subscribe)
		fc._on('unsubscribe', self._unsubscribe)
		fc._on('publish', self._publish)

	def _connclose(self, c):
		self.connections.remove(c)
		for chan in self.conn2chans[c]:
			self.subscribermap[chan].remove(c)
			for ident in c.idents:
				self._brokerchan(c, chan, ident, 0)

	def _publish(self, c, chan, data):
		logging.debug('broker publish to {0} by {1}'.format(chan, c.addr))
		for c2 in self.subscribermap[chan]:
			if c2 == c: continue
			c2.forward(data)
		
	def _subscribe(self, c, chan, ident):
		logging.debug('broker subscribe to {0} by {2} @ {1}'.format(chan, c.addr, ident))
		self.subscribermap[chan].append(c)
		self.conn2chans[c].append(chan)
		self._brokerchan(c, chan, ident, 1)
	
	def _unsubscribe(self, c, chan, ident):
		logging.debug('broker unsubscribe to {0} by {1}'.format(chan, c.addr))
		self.subscribermap[chan].remove(c)
		self.conn2chans[c].remove(chan)
		self._brokerchan(c, chan, ident, 0)

	def _brokerchan(self, c, chan, ident, subscribe=0):
		data = 'join' if subscribe else 'leave'
		if self.subscribermap[chan+'..broker']:
			for c2 in self.subscribermap[chan+'..broker']:
				if c2 == c: continue
				c2.publish(ident, chan+'..broker', data)

def main():
	fb = FeedBroker()

	loop()
	return 0
 
if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	sys.exit(main())


########NEW FILE########
__FILENAME__ = testbroker
import sys
import feedbroker
from feedbroker import *
logging.basicConfig(level=logging.DEBUG)


FeedConnOrig = FeedConn
FeedBrokerOrig = FeedBroker


class FeedBroker(FeedBrokerOrig):
	def initdb(self):
		pass


class FeedConn(FeedConnOrig):
	def auth(self, ident, hash):
		self.checkauth([{'identifier': str(ident), 'secret': 'secretsecret'},], hash)

	def checkauth(self, r, hash):
		akobj = r[0]
		akhash = hashlib.sha1('{0}{1}'.format(self.rand, akobj['secret'])).digest()
		self.idents.add(akobj['identifier'])
		logging.info('Auth success by {0}, {1}.'.format(akobj['identifier'], self.conn.addr))

		self.io_in(b'')

	def may_publish(self, chan):
		return True

	def may_subscribe(self, chan):
		return True


feedbroker.FeedConn = FeedConn
feedbroker.FeedBroker = FeedBroker


def main():
	fb = FeedBroker()

	loop()
	return 0

if __name__ == '__main__':
	sys.exit(main())


########NEW FILE########
__FILENAME__ = basic_mongodb
#!/usr/bin/python

import sys
import logging
logging.basicConfig(level=logging.WARNING)
from  gridfs  import GridFS
import hpfeeds
import pymongo
import ast
import datetime
import md5

HOST = '127.0.0.1'
PORT = 10000
CHANNELS = ['dionaea.connections', 'geoloc.events','dionaea.dcerpcrequests','dionaea.shellcodeprofiles','mwbinary.dionaea.sensorunique','dionaea.capture']
IDENT = 'ww3ee@hp1'
SECRET = '7w35rippuhx7704h'

# Required
MONGOHOST = '127.0.0.1'
MONGOPORT = 27017
MONGODBNAME = 'dionaea'
# Optional
MONGOUSER = ''
MONGOPWD = ''

def get_db(host, port, name, user = '', passwd = ''):
        dbconn = pymongo.Connection(host, port)
        db = pymongo.database.Database(dbconn, name)
	if user != '' or passwd != '':
        	db.authenticate(user, passwd)
        return db


def main():
	hpc = hpfeeds.new(HOST, PORT, IDENT, SECRET)
	print >>sys.stderr, 'connected to', hpc.brokername

	insertCon = pymongo.Connection(host="localhost",port=27017)
	db = None
	collection = None
	
	def on_message(identifier, channel, payload):
		if channel == 'dionaea.connections':
			try:
				msg = ast.literal_eval(str(payload))
			except:
				print 'exception processing dionaea.connections event', repr(payload)
			else:
				msg["time"] = datetime.datetime.utcfromtimestamp(msg['time'])
				msg['rport'] = int(msg['rport'])
				msg['lport'] = int(msg['lport'])
				print 'inserting...', msg
				db = insertCon['dionaea']
				collection = db['connection']
				collection.insert(msg)
		elif channel == 'geoloc.events':
			try:
				payload_python = str(payload)
				msg = ast.literal_eval(payload_python.replace("null", "None"))
			except:
				print 'exception processing geoloc.events', repr(payload)
			else:
				msg['time'] = datetime.datetime.strptime(msg['time'], "%Y-%m-%d %H:%M:%S")
				print 'inserting...', msg
				db = insertCon['geoloc']
				collection =  db['events']
				collection.insert(msg)
		elif channel == 'dionaea.dcerpcrequests':
			try:
				payload_python = str(payload)
				msg = ast.literal_eval(payload_python.replace("null", "None"))
			except:
				print 'exception processing dionaea.dcerpcrequests', repr(payload)
			else:
				dt = datetime.datetime.now()
				msg['time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
				print 'inserting...', msg
				db = insertCon['dionaea']
				collection = db['dcerpcrequests']
				collection.insert(msg)
		elif channel == 'dionaea.shellcodeprofiles':
			try:
				payload_python = str(payload)
				msg = ast.literal_eval(payload_python.replace("null", "None"))
			except:
				print 'exception processing dionaea.shellcodeprofiles', repr(payload)
			else:
				dt = datetime.datetime.now()
				msg['time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
				print 'inserting...', msg
				db = insertCon['dionaea']
				collection = db['shellcodeprofiles']
				collection.insert(msg)
		elif channel == 'mwbinary.dionaea.sensorunique' :
			try:
				payload_python = str(payload)
			except:
				print 'exception processing mwbinary.dionaea.sensorunique', repr(payload)
			else:
				hash = md5.new()
				hash.update(payload_python)
				msg = hash.hexdigest()
				print 'inserting mwbinary...', msg
				
				db = insertCon['dionaea']
				gfsDate=GridFS(db)
				gfsDate.put(payload_python,filename=msg)
		elif channel == 'dionaea.capture':
			try:
				payload_python = str(payload)
				msg = ast.literal_eval(payload_python.replace("null", "None"))
			except:
				print 'exception processing dionaea.capture', repr(payload)
			else:
				dt = datetime.datetime.now()
				msg['time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
				print 'inserting...', msg
				db = insertCon['dionaea']
				collection = db['capture']
				collection.insert(msg)		
	def on_error(payload):
		print >>sys.stderr, ' -> errormessage from server: {0}'.format(payload)
		hpc.stop()

	hpc.subscribe(CHANNELS)
	hpc.run(on_message, on_error)
	hpc.close()
	return 0

if __name__ == '__main__':
	try: sys.exit(main())
	except KeyboardInterrupt:sys.exit(0)


########NEW FILE########
__FILENAME__ = basic_postgres

import sys
import datetime
import json
import logging
logging.basicConfig(level=logging.CRITICAL)

import psycopg2
import hpfeeds

HOST = 'hpfeeds.honeycloud.net'
PORT = 10000
CHANNELS = ['dionaea.capture', ]
IDENT = ''
SECRET = ''

def main():
	conn = psycopg2.connect("host=localhost dbname=hpfeeds user=username password=pw")
	cur = conn.cursor()

	try:
		hpc = hpfeeds.new(HOST, PORT, IDENT, SECRET)
	except hpfeeds.FeedException, e:
		print >>sys.stderr, 'feed exception:', e
		return 1

	print >>sys.stderr, 'connected to', hpc.brokername

	def on_message(identifier, channel, payload):
		cur.execute("INSERT INTO rawlog (identifier, channel, payload) VALUES (%s, %s, %s)", (identifier, channel, payload))
		conn.commit()

	def on_error(payload):
		print >>sys.stderr, ' -> errormessage from server: {0}'.format(payload)
		hpc.stop()

	hpc.subscribe(CHANNELS)
	try:
		hpc.run(on_message, on_error)
	except hpfeeds.FeedException, e:
		print >>sys.stderr, 'feed exception:', e
	except KeyboardInterrupt:
		pass
	finally:
		cur.close()
		conn.close()
		hpc.close()
	return 0

if __name__ == '__main__':
	try: sys.exit(main())
	except KeyboardInterrupt:sys.exit(0)


########NEW FILE########
__FILENAME__ = csv2file

import sys
import datetime
import json
import logging
logging.basicConfig(level=logging.CRITICAL)
from time import sleep
import hpfeeds

HOST = 'hpfeeds.honeycloud.net'
PORT = 10000
CHANNELS = ['dionaea.capture',]
IDENT = ''
SECRET = ''
OUTFILE = 'hpfeedcsv.log'

def main():
	try: outfd = open(OUTFILE, 'a')
	except:
		print >>sys.stderr, 'could not open output file for message log.'
		return 1

	def on_message(identifier, channel, payload):
		try: decoded = json.loads(str(payload))
		except: decoded = {'raw': payload}

		csv = ', '.join(['{0}={1}'.format(i,j) for i,j in decoded.items()])
		outmsg = '{0} PUBLISH chan={1}, identifier={2}, {3}'.format(
			datetime.datetime.now().ctime(), channel, identifier, csv
		)

		print >>outfd, outmsg
		outfd.flush()

	def on_error(payload):
		print >>sys.stderr, ' -> errormessage from server: {0}'.format(payload)
		hpc.stop()

	hpc = hpfeeds.new(HOST, PORT, IDENT, SECRET, reconnect=True)
	print >>sys.stderr, 'connected to', hpc.brokername
	hpc.subscribe(CHANNELS)
	hpc.run(on_message, on_error)
	hpc.close()
	return 0

if __name__ == '__main__':
	try: sys.exit(main())
	except KeyboardInterrupt:sys.exit(0)


########NEW FILE########
__FILENAME__ = geoloc
import sys
import datetime
import logging
logging.basicConfig(level=logging.CRITICAL)

import hpfeeds
from processors import *

import GeoIP

HOST = 'hpfeeds.honeycloud.net'
PORT = 10000
CHANNELS = [
	'dionaea.connections',
	'dionaea.capture',
	'glastopf.events',
    'beeswarm.hive',
	'kippo.sessions',
]
GEOLOC_CHAN = 'geoloc.events'
IDENT = ''
SECRET = ''

PROCESSORS = {
	'glastopf.events': [glastopf_event,],
	'dionaea.capture': [dionaea_capture,],
	'dionaea.connections': [dionaea_connections,],
    'beeswarm.hive': [beeswarm_hive,],
	'kippo.sessions': [kippo_sessions,],
}

def main():
	import socket
	gi = {}
	gi[socket.AF_INET] = GeoIP.open("/opt/GeoLiteCity.dat",GeoIP.GEOIP_STANDARD)
	gi[socket.AF_INET6] = GeoIP.open("/opt/GeoLiteCityv6.dat",GeoIP.GEOIP_STANDARD)

	try:
		hpc = hpfeeds.new(HOST, PORT, IDENT, SECRET)
	except hpfeeds.FeedException, e:
		print >>sys.stderr, 'feed exception:', e
		return 1

	print >>sys.stderr, 'connected to', hpc.brokername

	def on_message(identifier, channel, payload):
		procs = PROCESSORS.get(channel, [])
		p = None
		for p in procs:
			try:
				m = p(identifier, payload, gi)
			except:
				print "invalid message %s" % payload
				continue
			try: tmp = json.dumps(m)
			except: print 'DBG', m
			if m != None: hpc.publish(GEOLOC_CHAN, json.dumps(m))

		if not p:
			print 'not p?'

	def on_error(payload):
		print >>sys.stderr, ' -> errormessage from server: {0}'.format(payload)
		hpc.stop()

	hpc.subscribe(CHANNELS)
	try:
		hpc.run(on_message, on_error)
	except hpfeeds.FeedException, e:
		print >>sys.stderr, 'feed exception:', e
	except KeyboardInterrupt:
		pass
	except:
		import traceback
		traceback.print_exc()
	finally:
		hpc.close()
	return 0

if __name__ == '__main__':
	try: sys.exit(main())
	except KeyboardInterrupt:sys.exit(0)


########NEW FILE########
__FILENAME__ = processors

import json
import traceback
import datetime
import urlparse
import socket

class ezdict(object):
	def __init__(self, d):
		self.d = d
	def __getattr__(self, name):
		return self.d.get(name, None)

# time string
def timestr(dt):
	return dt.strftime("%Y-%m-%d %H:%M:%S")

# geoloc_none
def geoloc_none(t):
	if t == None: return {'latitude': None, 'longitude': None, 'city': None, 'country_name': None, 'country_code': None}
	if t['city'] != None: t['city'] = t['city'].decode('latin1')
	return t

def get_addr_family(addr):
        ainfo = socket.getaddrinfo(addr, 1, socket.AF_UNSPEC, socket.SOCK_STREAM)
        return ainfo[0][0]

def glastopf_event(identifier, payload, gi):
	try:
		dec = ezdict(json.loads(str(payload)))
		req = ezdict(dec.request)
		sip, sport = dec.source
		tstamp = datetime.datetime.strptime(dec.time, '%Y-%m-%d %H:%M:%S')
	except:
		print 'exception processing glastopf event', repr(payload)
		traceback.print_exc()
		return

	if dec.pattern == 'unknown': return None

	a_family = get_addr_family(sip)
	if a_family == socket.AF_INET:
		geoloc = geoloc_none( gi[a_family].record_by_addr(sip) )
	elif a_family == socket.AF_INET6:
		geoloc = geoloc_none( gi[a_family].record_by_addr_v6(sip) )

	return {'type': 'glastopf.events', 'sensor': identifier, 'time': str(tstamp), 'latitude': geoloc['latitude'], 'longitude': geoloc['longitude'], 'source': sip, 'city': geoloc['city'], 'country': geoloc['country_name'], 'countrycode': geoloc['country_code']}


def dionaea_capture(identifier, payload, gi):
	try:
		dec = ezdict(json.loads(str(payload)))
		tstamp = datetime.datetime.now()
	except:
		print 'exception processing dionaea event'
		traceback.print_exc()
		return

	a_family = get_addr_family(dec.saddr)
	if a_family == socket.AF_INET:
		geoloc = geoloc_none( gi[a_family].record_by_addr(dec.saddr) )
		geoloc2 = geoloc_none( gi[a_family].record_by_addr(dec.daddr) )
	elif a_family == socket.AF_INET6:
		geoloc = geoloc_none( gi[a_family].record_by_addr_v6(dec.saddr) )
		geoloc2 = geoloc_none( gi[a_family].record_by_addr_v6(dec.daddr) )

	
	return {'type': 'dionaea.capture', 'sensor': identifier, 'time': timestr(tstamp), 'latitude': geoloc['latitude'], 'longitude': geoloc['longitude'], 'source': dec.saddr, 'latitude2': geoloc2['latitude'], 'longitude2': geoloc2['longitude'], 'dest': dec.daddr, 'md5': dec.md5,
'city': geoloc['city'], 'country': geoloc['country_name'], 'countrycode': geoloc['country_code'],
'city2': geoloc2['city'], 'country2': geoloc2['country_name'], 'countrycode2': geoloc2['country_code']}


def dionaea_connections(identifier, payload, gi):
	try:
		dec = ezdict(json.loads(str(payload)))
		tstamp = datetime.datetime.now()
	except:
		print 'exception processing dionaea event'
		traceback.print_exc()
		return

	a_family = get_addr_family(dec.remote_host)
	if a_family == socket.AF_INET:
		geoloc = geoloc_none( gi[a_family].record_by_addr(dec.remote_host) )
		geoloc2 = geoloc_none( gi[a_family].record_by_addr(dec.local_host) )
	elif a_family == socket.AF_INET6:
		geoloc = geoloc_none( gi[a_family].record_by_addr_v6(dec.remote_host) )
		geoloc2 = geoloc_none( gi[a_family].record_by_addr_v6(dec.local_host) )

	
	return {'type': 'dionaea.connections', 'sensor': identifier, 'time': timestr(tstamp), 'latitude': geoloc['latitude'], 'longitude': geoloc['longitude'], 'source': dec.remote_host, 'latitude2': geoloc2['latitude'], 'longitude2': geoloc2['longitude'], 'dest': dec.local_host, 'md5': dec.md5,
'city': geoloc['city'], 'country': geoloc['country_name'], 'countrycode': geoloc['country_code'],
'city2': geoloc2['city'], 'country2': geoloc2['country_name'], 'countrycode2': geoloc2['country_code']}

def beeswarm_hive(identifier, payload, gi):
	try:
		dec = ezdict(json.loads(str(payload)))
		sip = dec.attacker_ip
		dip = dec.honey_ip
		tstamp = datetime.datetime.strptime(dec.timestamp, '%Y-%m-%dT%H:%M:%S.%f')
	except:
		print 'exception processing beeswarm.hive event', repr(payload)
		traceback.print_exc()
		return

	a_family = get_addr_family(sip)
	if a_family == socket.AF_INET:
		geoloc = geoloc_none( gi[a_family].record_by_addr(sip) )
		geoloc2 = geoloc_none( gi[a_family].record_by_addr(dip) )
	elif a_family == socket.AF_INET6:
		geoloc = geoloc_none( gi[a_family].record_by_addr_v6(sip) )
		geoloc2 = geoloc_none( gi[a_family].record_by_addr_v6(dip) )

	return {'type': 'beeswarm.hive', 'sensor': identifier, 'time': str(tstamp),
            'latitude': geoloc['latitude'], 'longitude': geoloc['longitude'], 'city': geoloc['city'], 'country': geoloc['country_name'], 'countrycode': geoloc['country_code'],
            'latitude2': geoloc2['latitude'], 'longitude2': geoloc2['longitude'], 'city2': geoloc2['city'], 'country2': geoloc2['country_name'], 'countrycode2': geoloc2['country_code']}

def kippo_sessions(identifier, payload, gi):
	try:
		dec = ezdict(json.loads(str(payload)))
		tstamp = datetime.datetime.now()
	except:
		print 'exception processing dionaea event'
		traceback.print_exc()
		return

	a_family = get_addr_family(dec.peerIP)
	if a_family == socket.AF_INET:
		geoloc = geoloc_none( gi[a_family].record_by_addr(dec.peerIP) )
		geoloc2 = geoloc_none( gi[a_family].record_by_addr(dec.hostIP) )
	elif a_family == socket.AF_INET6:
		geoloc = geoloc_none( gi[a_family].record_by_addr_v6(dec.peerIP) )
		geoloc2 = geoloc_none( gi[a_family].record_by_addr_v6(dec.hostIP) )


	return {'type': 'kippo.sessions', 'sensor': identifier, 'time': timestr(tstamp),
'latitude': geoloc['latitude'], 'longitude': geoloc['longitude'], 'source': dec.peerIP,
'latitude2': geoloc2['latitude'], 'longitude2': geoloc2['longitude'], 'dest': dec.hostIP,
'city': geoloc['city'], 'country': geoloc['country_name'], 'countrycode': geoloc['country_code'],
'city2': geoloc2['city'], 'country2': geoloc2['country_name'], 'countrycode2': geoloc2['country_code']}

########NEW FILE########
__FILENAME__ = grabmalware
#!/usr/bin/python
#
# this will grab just the binary payload and write it to $filedir/md5sum

import os
import sys
import datetime
import json
import hashlib
import logging
logging.basicConfig(level=logging.CRITICAL)

import hpfeeds

HOST = 'hpfeeds.honeycloud.net'
PORT = 10000
CHANNELS = ['mwbinary.dionaea.sensorunique',]
IDENT = ''
SECRET = ''
OUTFILE = './grabmw.log'
OUTDIR = './malware/'

def main():
	try: outfd = open(OUTFILE, 'a')
	except:
		print >>sys.stderr, 'could not open output file for message log.'
		return 1

	if not os.path.exists(OUTDIR): os.mkdir(OUTDIR)

	hpc = hpfeeds.new(HOST, PORT, IDENT, SECRET)
	print >>sys.stderr, 'connected to', hpc.brokername

	def on_message(identifier, channel, payload):
			# now store the file itself
			md5sum = hashlib.md5(payload).hexdigest()
			fpath = os.path.join(OUTDIR, md5sum)
			try:
				open(fpath, 'wb').write(payload)
			except:
				print >>outfd, '{0} ERROR could not write to {1}'.format(datetime.datetime.now().ctime(), fpath)
			outfd.flush()

	def on_error(payload):
		print >>sys.stderr, ' -> errormessage from server: {0}'.format(payload)
		hpc.stop()

	hpc.subscribe(CHANNELS)
	hpc.run(on_message, on_error)
	hpc.close()
	return 0

if __name__ == '__main__':
	try: sys.exit(main())
	except KeyboardInterrupt:sys.exit(0)


########NEW FILE########
__FILENAME__ = stdin2message

import os
import sys
import datetime
import json
import select
import traceback
import logging
logging.basicConfig(level=logging.CRITICAL)

import hpfeeds

HOST = 'hpfeeds.honeycloud.net'
PORT = 10000
CHANNELS = ['test.channel',]
IDENT = ''
SECRET = ''

def main():
    hpc = hpfeeds.new(HOST, PORT, IDENT, SECRET)
    print >>sys.stderr, 'connected to', hpc.brokername

    def on_message(identifier, channel, payload):
        try: decoded = json.loads(str(payload))
        except: decoded = {'raw': payload}

        print 'incoming message from {0} on channel {1}, length {2}'.format(identifier, channel, len(payload))

    def on_error(payload):
        print >>sys.stderr, ' -> errormessage from server: {0}'.format(payload)
        hpc.stop()

	#hpc.subscribe(CHANNELS)

    hpc.s.settimeout(0.01)

    while True:
        rrdy, wrdy, xrdy = select.select([hpc.s, sys.stdin], [], [])
        if hpc.s in rrdy:
            try: hpc.run(on_message, on_error)
            except socket.timeout: pass
        if sys.stdin in rrdy:
            try: l = sys.stdin.readline()
            except: traceback.print_exc()
            else:
                if l.strip(): hpc.publish(CHANNELS, l)
    
    print 'quit.'
    hpc.close()
    return 0

if __name__ == '__main__':
	try: sys.exit(main())
	except KeyboardInterrupt:sys.exit(0)


########NEW FILE########
__FILENAME__ = stripsensor
#!/usr/bin/python

import sys
import logging
logging.basicConfig(level=logging.WARNING)

import traceback
import json
import hpfeeds

HOST = '192.168.168.113'
PORT = 10000
CHANNELS = ['dionaea.capture', ]
IDENT = 'ident'
SECRET = 'secret'

RELAYCHAN = 'dionaea.capture.anon'

def main():
	hpc = hpfeeds.new(HOST, PORT, IDENT, SECRET)
	print >>sys.stderr, 'connected to', hpc.brokername

	def on_message(ident, channel, payload):
		try:
			dec = json.loads(str(payload))
			del dec['daddr']
			dec['identifier'] = ident
			enc = json.dumps(dec)
		except:
			traceback.print_exc()
			print >>sys.stderr, 'forward error for message from {0}.'.format(ident)
			return

		hpc.publish(RELAYCHAN, enc)

	def on_error(payload):
		print >>sys.stderr, ' -> errormessage from server: {0}'.format(payload)
		hpc.stop()

	hpc.subscribe(CHANNELS)
	hpc.run(on_message, on_error)
	hpc.close()
	return 0

if __name__ == '__main__':
	try: sys.exit(main())
	except KeyboardInterrupt:sys.exit(0)


########NEW FILE########
__FILENAME__ = template
#!/usr/bin/python

import sys
import logging
logging.basicConfig(level=logging.WARNING)

import hpfeeds

HOST = '192.168.168.113'
PORT = 10000
CHANNELS = ['dionaea.shellcodeprofiles', 'dionaea.capture', 'thug.events', ]
IDENT = 'ident'
SECRET = 'secret'

def main():
	hpc = hpfeeds.new(HOST, PORT, IDENT, SECRET)
	print >>sys.stderr, 'connected to', hpc.brokername

	def on_message(identifier, channel, payload):
		print 'msg', identifier, channel, payload

	def on_error(payload):
		print >>sys.stderr, ' -> errormessage from server: {0}'.format(payload)
		hpc.stop()

	hpc.subscribe(CHANNELS)
	hpc.run(on_message, on_error)
	hpc.close()
	return 0

if __name__ == '__main__':
	try: sys.exit(main())
	except KeyboardInterrupt:sys.exit(0)


########NEW FILE########
__FILENAME__ = thugfiles

import os
import sys
import time
import datetime
import json
import logging
import hpfeeds

HOST        = 'hpfeeds.honeycloud.net'
PORT        = 10000
CHANNELS    = ['thug.files',]
IDENT       = ''
SECRET      = ''
OUTFILE     = './grab.log'
OUTDIR      = './files/'

log       = logging.getLogger("thug.files")
handler   = logging.FileHandler(OUTFILE)
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)
log.setLevel(logging.INFO)

class ThugFiles:
    def __init__(self):
        if not os.path.exists(OUTDIR): 
            os.mkdir(OUTDIR)

    def run(self):
        def on_message(identifier, channel, payload):
            try: 
                decoded = json.loads(str(payload))
            except: 
                decoded = {'raw': payload}

            if not 'md5' in decoded or not 'data' in decoded:
                log.info("Received message does not contain hash or data - Ignoring it")
                return
            
            csv    = ', '.join(['{0} = {1}'.format(i, decoded[i]) for i in ['md5', 'sha1', 'type']])
            outmsg = 'PUBLISH channel = %s, identifier = %s, %s' % (channel, identifier, csv)
            log.info(outmsg)
            
            filedata = decoded['data'].decode('base64')
            fpath    = os.path.join(OUTDIR, decoded['md5'])

            with open(fpath, 'wb') as fd:
                fd.write(filedata)

        def on_error(payload):
            log.critical("Error message from server: %s" % (payload, ))
            self.hpc.stop()

        while True:
            try:
                self.hpc = hpfeeds.new(HOST, PORT, IDENT, SECRET)
                log.info("Connected to %s" % (self.hpc.brokername, ))
                self.hpc.subscribe(CHANNELS)
            except hpfeeds.FeedException:
                break

            try:
                self.hpc.run(on_message, on_error)
            except:
                self.hpc.close()
                time.sleep(20)

if __name__ == '__main__':
    try: 
        f = ThugFiles()
        f.run()
    except KeyboardInterrupt:
        sys.exit(0)


########NEW FILE########
__FILENAME__ = hpfeeds
# Copyright (C) 2010-2013 Mark Schloesser <ms@mwcollect.org
# This file is part of hpfeeds - https://github.com/rep/hpfeeds
# See the file 'LICENSE' for copying permission.

import sys
import struct
import socket
import hashlib
import logging
import time
import threading
import ssl

logger = logging.getLogger('pyhpfeeds')

OP_ERROR	= 0
OP_INFO		= 1
OP_AUTH		= 2
OP_PUBLISH	= 3
OP_SUBSCRIBE	= 4
BUFSIZ = 16384

__all__ = ["new", "FeedException"]

def msghdr(op, data):
	return struct.pack('!iB', 5+len(data), op) + data
def msgpublish(ident, chan, data):
#	if isinstance(data, str):
#		data = data.encode('latin1')
	return msghdr(OP_PUBLISH, struct.pack('!B', len(ident)) + ident + struct.pack('!B', len(chan)) + chan + data)
def msgsubscribe(ident, chan):
	return msghdr(OP_SUBSCRIBE, struct.pack('!B', len(ident)) + ident + chan)
def msgauth(rand, ident, secret):
	hash = hashlib.sha1(rand+secret).digest()
	return msghdr(OP_AUTH, struct.pack('!B', len(ident)) + ident + hash)

class FeedUnpack(object):
	def __init__(self):
		self.buf = bytearray()
	def __iter__(self):
		return self
	def next(self):
		return self.unpack()
	def feed(self, data):
		self.buf.extend(data)
	def unpack(self):
		if len(self.buf) < 5:
			raise StopIteration('No message.')

		ml, opcode = struct.unpack('!iB', buffer(self.buf,0,5))
		if len(self.buf) < ml:
			raise StopIteration('No message.')

		data = bytearray(buffer(self.buf, 5, ml-5))
		del self.buf[:ml]
		return opcode, data

class FeedException(Exception):
	pass
class Disconnect(Exception):
	pass

class HPC(object):
	def __init__(self, host, port, ident, secret, timeout=3, reconnect=True, sleepwait=20):
		self.host, self.port = host, port
		self.ident, self.secret = ident, secret
		self.timeout = timeout
		self.reconnect = reconnect
		self.sleepwait = sleepwait
		self.brokername = 'unknown'
		self.connected = False
		self.stopped = False
		self.s = None
		self.connecting_lock = threading.Lock()
		self.subscriptions = set()
		self.unpacker = FeedUnpack()

		self.tryconnect()

	def makesocket(self, addr_family):
		return socket.socket(addr_family, socket.SOCK_STREAM)

	def recv(self):
		try:
			d = self.s.recv(BUFSIZ)
		except socket.timeout:
			return ""
		except socket.error as e:
			logger.warn("Socket error: %s", e)
			raise Disconnect()

		if not d: raise Disconnect()
		return d

	def send(self, data):
		try:
			self.s.sendall(data)
		except socket.timeout:
			logger.warn("Timeout while sending - disconnect.")
			raise Disconnect()
		except socket.error as e:
			logger.warn("Socket error: %s", e)
			raise Disconnect()

		return True

	def tryconnect(self):
		with self.connecting_lock:
			if not self.connected:
				while True:
					try:
						self.connect()
						break
					except socket.error, e:
						logger.warn('Socket error while connecting: {0}'.format(e))
						time.sleep(self.sleepwait)
					except FeedException, e:
						logger.warn('FeedException while connecting: {0}'.format(e))
						time.sleep(self.sleepwait)
					except Disconnect as e:
						logger.warn('Disconnect while connecting.')
						time.sleep(self.sleepwait)

	def connect(self):
		self.close_old()

		logger.info('connecting to {0}:{1}'.format(self.host, self.port))

		# Try other resolved addresses (IPv4 or IPv6) if failed.
		ainfos = socket.getaddrinfo(self.host, 1, socket.AF_UNSPEC, socket.SOCK_STREAM)
		for ainfo in ainfos:
			addr_family = ainfo[0]
			addr = ainfo[4][0]
			try:
				self.s = self.makesocket(addr_family)
				self.s.settimeout(self.timeout)
				self.s.connect((addr, self.port))
			except:
				import traceback
				traceback.print_exc()
				#print 'Could not connect to broker. %s[%s]' % (self.host, addr)
				continue
			else:
				self.connected = True
				break

		if self.connected == False:
			raise FeedException('Could not connect to broker [%s].' % (self.host))

		try: d = self.s.recv(BUFSIZ)
		except socket.timeout: raise FeedException('Connection receive timeout.')

		self.unpacker.feed(d)
		for opcode, data in self.unpacker:
			if opcode == OP_INFO:
				rest = buffer(data, 0)
				name, rest = rest[1:1+ord(rest[0])], buffer(rest, 1+ord(rest[0]))
				rand = str(rest)

				logger.debug('info message name: {0}, rand: {1}'.format(name, repr(rand)))
				self.brokername = name

				self.send(msgauth(rand, self.ident, self.secret))
				break
			else:
				raise FeedException('Expected info message at this point.')

		self.s.settimeout(None)
		self.s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

		if sys.platform in ('linux2', ):
			self.s.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, 10)    

	def run(self, message_callback, error_callback):
		while not self.stopped:
			self._subscribe()
			while self.connected:
				try:
					d = self.recv()
					self.unpacker.feed(d)

					for opcode, data in self.unpacker:
						if opcode == OP_PUBLISH:
							rest = buffer(data, 0)
							ident, rest = rest[1:1+ord(rest[0])], buffer(rest, 1+ord(rest[0]))
							chan, content = rest[1:1+ord(rest[0])], buffer(rest, 1+ord(rest[0]))

							message_callback(str(ident), str(chan), content)
						elif opcode == OP_ERROR:
							error_callback(data)

				except Disconnect:
					self.connected = False
					logger.info('Disconnected from broker.')
					break

				# end run loops if stopped
				if self.stopped: break

			if not self.stopped and self.reconnect:
				# connect again if disconnected
				self.tryconnect()

		logger.info('Stopped, exiting run loop.')

	def wait(self, timeout=1):
		self.s.settimeout(timeout)

		d = self.recv()
		if not d: return None

		self.unpacker.feed(d)
		for opcode, data in self.unpacker:
			if opcode == OP_ERROR:
				return data

		return None

	def close_old(self):
		if self.s:
			try: self.s.close()
			except: pass

	def subscribe(self, chaninfo):
		if type(chaninfo) == str:
			chaninfo = [chaninfo,]
		for c in chaninfo:
			self.subscriptions.add(c)

	def _subscribe(self):
		for c in self.subscriptions:
			try:
				logger.debug('Sending subscription for {0}.'.format(c))
				self.send(msgsubscribe(self.ident, c))
			except Disconnect:
				self.connected = False
				logger.info('Disconnected from broker (in subscribe).')
				if not self.reconnect: raise
				break

	def publish(self, chaninfo, data):
		if type(chaninfo) == str:
			chaninfo = [chaninfo,]
		for c in chaninfo:
			try:
				self.send(msgpublish(self.ident, c, data))
			except Disconnect:
				self.connected = False
				logger.info('Disconnected from broker (in publish).')
				if self.reconnect:
					self.tryconnect()
				else:
					raise

	def stop(self):
		self.stopped = True

	def close(self):
		try: self.s.close()
		except: logger.debug('Socket exception when closing (ignored though).')


class HPC_SSL(HPC):
	def __init__(self, *args, **kwargs):
		self.certfile = kwargs.pop("certfile", None)
		HPC.__init__(self, *args, **kwargs)

	def makesocket(self, addr_family):
		s = socket.socket(addr_family, socket.SOCK_STREAM)
		return ssl.wrap_socket(s, ca_certs=self.certfile, ssl_version=3, cert_reqs=2)


def new(host=None, port=10000, ident=None, secret=None, timeout=3, reconnect=True, sleepwait=20, certfile=None):
	if certfile:
		return HPC_SSL(host, port, ident, secret, timeout, reconnect, certfile=certfile)
	return HPC(host, port, ident, secret, timeout, reconnect)

########NEW FILE########
