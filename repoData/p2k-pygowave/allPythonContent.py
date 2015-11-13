__FILENAME__ = message_processor

#
# PyGoWave Server
# Copyright (C) 2010 Patrick "p2k" Schneider <patrick.schneider@wavexperts.de>
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
#

class PyGoWaveMessageProcessor(object):
	def purge_connections(self):
		pass
	
	def log_stats(self):
		pass
	
	def process(self, rkey, message_data):
		return {}

########NEW FILE########
__FILENAME__ = service

#
# PyGoWave Server
# Copyright (C) 2010 Patrick "p2k" Schneider <patrick.schneider@wavexperts.de>
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
#

from twisted.application.service import IService, Service
from twisted.internet.task import LoopingCall
from twisted.internet.interfaces import IProtocolFactory
from twisted.python import components, log
from zope.interface import implements

__all__ = ["IPyGoWaveService", "IStompProtocolFactory", "PyGoWaveService"]

class IStompProtocolFactory(IProtocolFactory):
	"""
	Base class for the client and server protocol factory interfaces
	
	"""
	
	def sendMessagesTo(rkey, messages):
		"""
		Send a list of messages to a message queue with the given
		routing key.
		
		"""

class IPyGoWaveService(IService):
	"""
	Interface for all Services which work with PyGoWave messages.
	
	"""
	
	def process(rkey, message_data):
		"""
		Process one or more messages received by the protocol.
		
		rkey is the routing key for the messages.
		message_data is a list of messages, which are dictionaries.
		
		This function must return a dictionary where the keys are the target
		routing keys and the values are lists of messages to be sent to the
		targets.
		
		"""
	
	def factoryReady():
		"""
		Callback from factory when the connection is up and running.
		
		"""
	
	def messageQueueInfo():
		"""
		This gets called by the Stomp client implementation in order
		to retrieve information about the message queue to subscribe
		to.
		
		It must return a dictionary with the following items:
		"queue_name" - Name of the message queue to subscribe to
		"exchange" - Name of the exchange for messages
		"routing_key" - Routing key (with wildcards) for messages
		"exchange_type" - Type of the exchange (should be "topic")
		
		It may return a list of dictionaries, if you want to
		subscribe to multiple queues.
		
		"""

class PyGoWaveService(Service):
	"""
	Main service for PyGoWave, which processes incoming messages.
	
	"""
	
	implements(IPyGoWaveService)
	
	def factoryReady(self, factory):
		log.msg("=> PyGoWave Server factory ready <=")
	
	def messageQueueInfo(self):
		return [
			{
				"queue_name": "wavelet_server_singlethread",
				"exchange": "wavelet.topic",
				"routing_key": "*.*.clientop",
				"exchange_type": "topic",
			},
			{
				"queue_name": "wavelet_server_singlethread",
				"exchange": "federation.topic",
				"routing_key": "*.*.fedinop",
				"exchange_type": "topic",
			},
		]
	
	def startService(self):
		from message_processor import PyGoWaveMessageProcessor
		self.mp = PyGoWaveMessageProcessor()
		
		self.lc = LoopingCall(self.mp.purge_connections)
		self.lc2 = LoopingCall(self.mp.log_stats)
		self.lc.start(10 * 60) # Purge every 10 minutes
		self.lc2.start(60 * 60, now=False) # Stats every 60 minutes
		
		log.msg("=> PyGoWave Server service ready <=")
	
	def stopService(self):
		if self.lc.running:
			self.lc.stop()
		if self.lc2.running:
			self.lc2.stop()
		
		self.lc = None
		self.lc2 = None
		self.mp = None
	
	def process(self, rkey, message_data):
		return self.mp.process(rkey, message_data)

########NEW FILE########
__FILENAME__ = stomp_client

#
# PyGoWave Server
# Copyright (C) 2010 Patrick "p2k" Schneider <patrick.schneider@wavexperts.de>
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
#

from twisted.internet.protocol import Protocol, ReconnectingClientFactory
from twisted.python import components
from zope.interface import implements, Attribute

import stomper, simplejson

from service import IPyGoWaveService, IStompProtocolFactory

# This module registers an adapter, please use
# IStompClientProtocolFactory(service) to create a factory from a service
__all__ = ["IStompClientProtocolFactory"]

class IStompClientProtocolFactory(IStompProtocolFactory):
	"""Interface for a stomp client protocol factory"""
	username = Attribute("Username for the Stomp connection")
	password = Attribute("Password for the Stomp connection")

class StompMessageProcessor(stomper.Engine):
	def __init__(self, protocol):
		super(StompMessageProcessor, self).__init__()
		self.proto = protocol
	
	def connect(self):
		"""Generate the STOMP connect command to get a session."""
		return stomper.connect(self.proto.factory.username, self.proto.factory.password)
	
	def connected(self, msg):
		"""Once I've connected I want to subscribe to my the message queue(s)."""
		super(StompMessageProcessor, self).connected(msg)
		
		self.proto.factory.protocolConnected(self.proto)
		
		mqis = self.proto.service.messageQueueInfo()
		
		if not isinstance(mqis, list):
			mqis = [mqis]
		
		out = ""
		for mqi in mqis:
			f = stomper.Frame()
			f.unpack(stomper.subscribe(mqi["queue_name"]))
			f.headers["exchange"] = mqi["exchange"]
			f.headers["routing_key"] = mqi["routing_key"]
			f.headers["exchange_type"] = mqi["exchange_type"]
			out += f.pack()
		return out
	
	def ack(self, message):
		rkey = message["headers"]["destination"]
		message_data = simplejson.loads(message["body"].decode("utf-8"))
		
		msg_dict = self.proto.service.process(rkey, message_data)
		
		out_frames = ""
		for out_rkey, messages in msg_dict.iteritems():
			out_frames += self.send(out_rkey, messages)
		
		return super(StompMessageProcessor, self).ack(message) + out_frames

	def send(self, routing_key, messages):
		"""Convert a routing key and a list of messages into a STOMP frame."""
		f = stomper.Frame()
		f.unpack(stomper.send(routing_key, simplejson.dumps(messages)))
		f.headers["exchange"] = "wavelet.direct"
		f.headers["content-type"] = "application/json"
		return f.pack().encode("utf-8")

class StompClientProtocol(Protocol):
	def __init__(self, service):
		self.service = service
		self.mp = StompMessageProcessor(self)
		self.stompBuffer = stomper.stompbuffer.StompBuffer()
	
	def connectionMade(self):
		"""Register with the stomp server."""
		self.factory.connection = self
		self.transport.write(self.mp.connect())
	
	def connectionLost(self, reason):
		"""Shut down."""
	
	def dataReceived(self, data):
		"""Data received, react to it and respond."""
		self.stompBuffer.appendData(data.replace('\0', '\0\n'))
		
		while True:
			msg = self.stompBuffer.getOneMessage()
			
			if self.stompBuffer.buffer.startswith('\n'):
				self.stompBuffer.buffer = self.stompBuffer.buffer[1:]
			
			if msg is None:
				break
			
			returned = self.mp.react(msg)
			if returned:
				self.transport.write(returned)
	
	def sendMessagesTo(self, rkey, messages):
		"""Convert a routing key and a list of messages into a STOMP frame and send it."""
		self.transport.write(self.mp.send(rkey, messages))

class StompClientFactoryFromService(ReconnectingClientFactory):
	
	implements(IStompClientProtocolFactory)
	
	def __init__(self, service):
		self.service = service
	
	def startedConnecting(self, connector):
		"""Started to connect."""
	
	def clientConnectionLost(self, connector, reason):
		"""Lost connection."""
	
	def buildProtocol(self, addr):
		"""Transport level connected now create the communication protocol."""
		p = StompClientProtocol(self.service)
		p.factory = self
		return p
	
	def protocolConnected(self, protocol):
		self.connected_protocol = protocol
		self.service.factoryReady(self)
	
	def sendMessagesTo(self, rkey, messages):
		# Forwarding to the currently connected protocol object
		if self.connected_protocol == None:
			return
		self.connected_protocol.sendMessagesTo(rkey, messages)
	
	#def clientConnectionFailed(self, connector, reason):
	#	"""Connection failed."""
	#	super(StompClientFactory, self).clientConnectionFailed(connector, reason)
	
	def __repr__(self):
		return "StompClientFactory"

components.registerAdapter(StompClientFactoryFromService, IPyGoWaveService, IStompClientProtocolFactory)

########NEW FILE########
__FILENAME__ = stomp_server

#
# PyGoWave Server
# Copyright (C) 2010 Patrick "p2k" Schneider <patrick.schneider@wavexperts.de>
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
#

from twisted.internet.protocol import Protocol, ServerFactory
from twisted.python import components
from zope.interface import implements

import stomper, simplejson, traceback

from service import IPyGoWaveService, IStompProtocolFactory

# This module registers an adapter, please use
# IStompServerProtocolFactory(service) to create a factory from a service
__all__ = ["IStompServerProtocolFactory"]

class IStompServerProtocolFactory(IStompProtocolFactory):
	"""Marker interface for a stomp server protocol factory"""

class StompServerProtocol(Protocol):
	id = 0
	def __init__(self):
		self.state = 'initial'
		self.stompBuffer = stomper.stompbuffer.StompBuffer()
		StompServerProtocol.id += 1
		self.id = StompServerProtocol.id
	
	def dataReceived(self, data):
		self.stompBuffer.appendData(data.replace('\0', '\0\n'))
		
		while True:
			msg = self.stompBuffer.getOneMessage()
			
			if self.stompBuffer.buffer.startswith('\n'):
				self.stompBuffer.buffer = self.stompBuffer.buffer[1:]
			
			if msg is None or (not msg['headers'] and not msg['body'] and not msg['cmd']):
				break
			
			msg['cmd'] = msg['cmd'].lower()
			getattr(self, 'read_%s' % self.state)(**msg)
	
	def read_initial(self, cmd, headers, body):
		assert cmd == 'connect', "Invalid cmd: expected CONNECT"
		self.state = 'connected'
		self.sendFrame('CONNECTED', {"session": self.id}, "")
		self.factory.connected(self)
	
	def sendError(self, e):
		exception, instance, tb = traceback.sys.exc_info()
		tbOutput= "".join(traceback.format_tb(tb))
		self.sendFrame('ERROR', {'message': str(e) }, tbOutput)
	
	def sendFrame(self, cmd, headers, body):
		f = stomper.Frame()
		f.cmd = cmd
		f.headers.update(headers)
		f.body = body
		self.transport.write(f.pack())
	
	def read_connected(self, cmd, headers, body):
		return getattr(self, 'frame_%s' % cmd)(headers, body)
	
	def frame_subscribe(self, headers, body):
		self.factory.subscribe(self, headers['destination'])
	
	def frame_unsubscribe(self, headers, body):
		self.factory.unsubscribe(self, headers['destination'])
	
	def frame_send(self, headers, body):
		self.factory.send(headers['destination'], body, headers)
	
	def frame_disconnect(self, headers, body):
		self.transport.loseConnection()
	
	def connectionLost(self, reason):
		self.factory.disconnected(self)

class StompServerFactoryFromService(ServerFactory):
	protocol = StompServerProtocol
	
	implements(IStompServerProtocolFactory)
	
	def __init__(self, service):
		self.service = service
		self.subscriptions = {}
		self.destinations = {}
	
	def subscribe(self, proto, name):
		self.subscriptions[proto.id].append(name)
		self.destinations[name] = proto
	
	def unsubscribe(self, proto, name):
		self.subscriptions[proto.id].remove(name)
		del self.destinations[name]
	
	def connected(self, proto):
		self.subscriptions[proto.id] = []
	
	def disconnected(self, proto):
		for sub in self.subscriptions[proto.id]:
			self.unsubscribe(proto, sub)
		del self.subscriptions[proto.id]
	
	def send(self, dest_name, body, headers={}):
		msg_dict = self.service.process(dest_name, simplejson.loads(body.decode("utf-8")))
		
		for out_rkey, messages in msg_dict.iteritems():
			self.sendMessagesTo(out_rkey, messages)
	
	def sendMessagesTo(self, rkey, messages):
		if self.destinations.has_key(rkey):
			self.destinations[rkey].sendFrame('MESSAGE', {'destination': str(rkey)}, simplejson.dumps(messages).encode("utf-8"))
	
	def startFactory(self):
		ServerFactory.startFactory(self)
		self.service.factoryReady(self)
	
	def __repr__(self):
		return "StompServerFactory"

components.registerAdapter(StompServerFactoryFromService, IPyGoWaveService, IStompServerProtocolFactory)

########NEW FILE########
