__FILENAME__ = broadcast
###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ['startClient', 'startServer']

import pkg_resources
import os, socket, binascii

from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.static import File

from autobahn.twisted.websocket import connectWS, \
                                       listenWS, \
                                       WebSocketClientFactory, \
                                       WebSocketClientProtocol, \
                                       WebSocketServerFactory, \
                                       WebSocketServerProtocol


class BroadcastServerProtocol(WebSocketServerProtocol):

   def onOpen(self):
      self.factory.register(self)

   def onClose(self, wasClean, code, reason):
      self.factory.unregister(self)

   def onMessage(self, payload, isBinary):
      self.factory.broadcast(payload, isBinary)



class BroadcastServerFactory(WebSocketServerFactory):

   protocol = BroadcastServerProtocol

   def __init__(self, url, debug = False):
      WebSocketServerFactory.__init__(self, url, debug = debug, debugCodePaths = debug)

   def startFactory(self):
      self.clients = set()
      self.tickcount = 0
      self.tick()

   def register(self, client):
      self.clients.add(client)

   def unregister(self, client):
      self.clients.discard(client)

   def broadcast(self, payload, isBinary = False):
      for c in self.clients:
         c.sendMessage(payload, isBinary)

   def tick(self):
      self.tickcount += 1
      self.broadcast("tick %d" % self.tickcount)
      reactor.callLater(1, self.tick)



class BroadcastClientProtocol(WebSocketClientProtocol):

   def sendHello(self):
      self.sendMessage("hello from %s[%d]" % (socket.gethostname(), os.getpid()))
      reactor.callLater(2, self.sendHello)

   def onOpen(self):
      self.sendHello()

   def onMessage(self, payload, isBinary):
      if isBinary:
         print "received: ", binascii.b2a_hex(payload)
      else:
         print "received: ", payload



class BroadcastClientFactory(WebSocketClientFactory):

   protocol = BroadcastClientProtocol

   def __init__(self, url, debug = False):
      WebSocketClientFactory.__init__(self, url, debug = debug, debugCodePaths = debug)



def startClient(wsuri, debug = False):
   factory = BroadcastClientFactory(wsuri, debug)
   connectWS(factory)
   return True



def startServer(wsuri, sslKey = None, sslCert = None, debug = False):
   factory = BroadcastServerFactory(wsuri, debug)
   if sslKey and sslCert:
      sslContext = ssl.DefaultOpenSSLContextFactory(sslKey, sslCert)
   else:
      sslContext = None
   listenWS(factory, sslContext)

   webdir = File(pkg_resources.resource_filename("autobahntestsuite", "web/broadcastserver"))
   web = Site(webdir)
   reactor.listenTCP(8080, web)

   return True

########NEW FILE########
__FILENAME__ = case
###############################################################################
##
##  Copyright 2011-2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

import pickle


class Case:

   FAILED = "FAILED"
   OK = "OK"
   NON_STRICT = "NON-STRICT"
   WRONG_CODE = "WRONG CODE"
   UNCLEAN = "UNCLEAN"
   FAILED_BY_CLIENT = "FAILED BY CLIENT"
   INFORMATIONAL = "INFORMATIONAL"
   UNIMPLEMENTED = "UNIMPLEMENTED"

   # to remove
   NO_CLOSE = "NO_CLOSE"

   SUBCASES = []

   def __init__(self, protocol):
      self.p = protocol
      self.received = []
      self.expected = {}
      self.expectedClose = {}
      self.behavior = Case.FAILED
      self.behaviorClose = Case.FAILED
      self.result = "Actual events differ from any expected."
      self.resultClose = "TCP connection was dropped without close handshake"
      self.reportTime = False
      self.reportCompressionRatio = False
      self.trafficStats = None
      self.subcase = None
      self.suppressClose = False # suppresses automatic close behavior (used in cases that deliberately send bad close behavior)

      ## defaults for permessage-deflate - will be overridden in
      ## permessage-deflate test cases (but only for those)
      ##
      self.perMessageDeflate = False
      self.perMessageDeflateOffers = []
      self.perMessageDeflateAccept = lambda connectionRequest, acceptNoContextTakeover, acceptMaxWindowBits, requestNoContextTakeover, requestMaxWindowBits: None

      self.init()

   def getSubcaseCount(self):
      return len(Case.SUBCASES)

   def setSubcase(self, subcase):
      self.subcase = subcase

   def init(self):
      pass

   def onOpen(self):
      pass

   def onMessage(self, msg, binary):
      self.received.append(("message", msg, binary))
      self.finishWhenDone()

   def onPing(self, payload):
      self.received.append(("ping", payload))
      self.finishWhenDone()

   def onPong(self, payload):
      self.received.append(("pong", payload))
      self.finishWhenDone()

   def onClose(self, wasClean, code, reason):
      pass

   def compare(self, obj1, obj2):
      return pickle.dumps(obj1) == pickle.dumps(obj2)

   def onConnectionLost(self, failedByMe):
      # check if we passed the test
      for e in self.expected:
         if self.compare(self.received, self.expected[e]):
            self.behavior = e
            self.passed = True
            self.result = "Actual events match at least one expected."
            break

      # check the close status
      if self.expectedClose["closedByMe"] != self.p.closedByMe:
         self.behaviorClose = Case.FAILED
         self.resultClose = "The connection was failed by the wrong endpoint"
      elif self.expectedClose["requireClean"] and not self.p.wasClean:
         self.behaviorClose = Case.UNCLEAN
         self.resultClose = "The spec requires the connection to be failed cleanly here"
      elif self.p.remoteCloseCode != None and self.p.remoteCloseCode not in self.expectedClose["closeCode"]:
         self.behaviorClose = Case.WRONG_CODE
         self.resultClose = "The close code should have been %s or empty" % ','.join(map(str,self.expectedClose["closeCode"]))
      elif not self.p.factory.isServer and self.p.droppedByMe:
         self.behaviorClose = Case.FAILED_BY_CLIENT
         self.resultClose = "It is preferred that the server close the TCP connection"
      else:
         self.behaviorClose = Case.OK
         self.resultClose = "Connection was properly closed"

      ## for UTF8 tests, closing by wrong endpoint means case failure, since
      ## the peer then did not detect the invalid UTF8 at all
      ##
      closedByWrongEndpointIsFatal = self.expectedClose.get("closedByWrongEndpointIsFatal", False)
      if closedByWrongEndpointIsFatal and self.expectedClose["closedByMe"] != self.p.closedByMe:
         self.behavior = Case.FAILED

   def finishWhenDone(self):
      # if we match at least one expected outcome check if we are supposed to
      # start the closing handshake and if so, do it.
      for e in self.expected:
         if not self.compare(self.received, self.expected[e]):
            return
      if self.expectedClose["closedByMe"] and not self.suppressClose:
         self.p.sendClose(self.expectedClose["closeCode"][0])


########NEW FILE########
__FILENAME__ = case10_1_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case10_1_1(Case):

   DESCRIPTION = """Send text message with payload of length 65536 auto-fragmented with <b>autoFragmentSize = 1300</b>."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent and transmitted frame counts as expected). Clean close with normal code."""

   def onOpen(self):
      self.payload = "*" * 65536
      self.p.autoFragmentSize = 1300
      self.expected[Case.OK] = [("message", self.payload, False)]
      self.expectedClose = {"closedByMe": True, "closeCode": [self.p.CLOSE_STATUS_CODE_NORMAL], "requireClean": True}
      self.p.sendMessage(self.payload)
      self.p.killAfter(10)

   def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)
      frames_expected = {}
      frames_expected[0] = len(self.payload) / self.p.autoFragmentSize
      frames_expected[1] = 1 if len(self.payload) % self.p.autoFragmentSize > 0 else 0
      frames_got = {}
      frames_got[0] = self.p.txFrameStats[0]
      frames_got[1] = self.p.txFrameStats[1]
      if frames_expected == frames_got:
         pass
      else:
         self.behavior = Case.FAILED
         self.result = "Frames transmitted %s does not match what we expected %s." % (str(frames_got), str(frames_expected))

########NEW FILE########
__FILENAME__ = case12_x_x
###############################################################################
##
##  Copyright (C) 2013-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ['Case12_X_X',
           'Case12_X_X_CaseSubCategories',
           'Case13_X_X',
           'Case13_X_X_CaseSubCategories',
           ]

import copy, os, pkg_resources, hashlib, binascii

from case import Case
from autobahn.websocket.compress import *


## list of (payload length, message count, case timeout, auto-fragment size)
##
MSG_SIZES = [
   (16,     1000, 60 , 0),
   (64,     1000, 60 , 0),
   (256,    1000, 120, 0),
   (1024,   1000, 240, 0),
   (4096,   1000, 480, 0),
   (8192,   1000, 480, 0),
   (16384,  1000, 480, 0),
   (32768,  1000, 480, 0),
   (65536,  1000, 480, 0),
   (131072, 1000, 480, 0),

   (8192,   1000, 480, 256),
   (16384,  1000, 480, 256),
   (32768,  1000, 480, 256),
   (65536,  1000, 480, 256),
   (131072, 1000, 480, 256),
   (131072, 1000, 480, 1024),
   (131072, 1000, 480, 4096),
   (131072, 1000, 480, 32768),
]

## test data set
##
WS_COMPRESSION_TESTDATA = {
   'gutenberg_faust':
      {'desc': "Human readable text, Goethe's Faust I (German)",
       'url': 'http://www.gutenberg.org/cache/epub/2229/pg2229.txt',
       'file': 'pg2229.txt',
       'binary': True
       },
   'lena512':
      {'desc': 'Lena Picture, Bitmap 512x512 bw',
       'url': 'http://www.ece.rice.edu/~wakin/images/lena512.bmp',
       'file': 'lena512.bmp',
       'binary': True
       },
   'ooms':
      {'desc': 'A larger PDF',
       'url': 'http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.105.5439',
       'file': '10.1.1.105.5439.pdf',
       'binary': True
       },
   'json_data1':
      {'desc': 'Large JSON data file',
       'url': None,
       'file': 'data1.json',
       'binary': False
       },
   'html_data1':
      {'desc': 'Large HTML file',
       'url': None,
       'file': 'data1.html',
       'binary': False
       }
}



def __init__(self, protocol):
   Case.__init__(self, protocol)


def init(self):
   self.reportTime = True
   self.reportCompressionRatio = True

   self.expectedClose = {"closedByMe": True,
                         "closeCode": [self.p.CLOSE_STATUS_CODE_NORMAL],
                         "requireClean": True}

   ## permessage-deflate setup
   ##
   if self.p.factory.isServer:
      self.p.perMessageCompressionAccept = self.SERVER_ACCEPT

   else:
      self.p.perMessageCompressionOffers = self.CLIENT_OFFERS

      def accept(response):
         if isinstance(response, PerMessageDeflateResponse):
            return PerMessageDeflateResponseAccept(response)

      self.p.perMessageCompressionAccept = accept


   self.payloadRXPtr = 0
   self.payloadTXPtr = 0

   fn = pkg_resources.resource_filename("autobahntestsuite", "testdata/%s" % self.TESTDATA['file'])
   self.testData = open(fn, 'rb').read()
   self.testDataLen = len(self.testData)


def onOpen(self):
   self.p.enableWirelog(False)
   self.p.autoFragmentSize = self.AUTOFRAGSIZE

   if self.p._perMessageCompress is None:
      self.behavior = Case.UNIMPLEMENTED
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)
   else:
      self.behavior = Case.FAILED
      self.result = "Case did not finish within %d seconds." % self.WAITSECS
      self.p.closeAfter(self.WAITSECS)

      self.count = 0
      self.sendOne()


def sendOne(self):
   if self.LEN > 0:
      idxFrom = self.payloadRXPtr
      idxTo = (self.payloadRXPtr + self.LEN) % self.testDataLen
      if idxTo > idxFrom:
         msg = self.testData[idxFrom:idxTo]
      else:
         msg = self.testData[idxFrom:] + self.testData[:idxTo]
      self.payloadRXPtr = idxTo
   else:
      msg = ''

   m = hashlib.sha1()
   m.update(msg)
   self._expected_hash = m.digest()

   self.p.sendMessage(msg, self.TESTDATA['binary'])
   self.count += 1


def onMessage(self, msg, binary):
   m = hashlib.sha1()
   m.update(msg)
   received_hash = m.digest()

   if binary != self.TESTDATA['binary'] or len(msg) != self.LEN or received_hash != self._expected_hash:

      self.behavior = Case.FAILED
      self.p.enableWirelog(True)
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)

      if binary != self.TESTDATA['binary']:
         self.result = "Echo'ed message type differs from what I sent (got binary {}, expected binary {}).".format(binary, self.TESTDATA['binary'])

      elif len(msg) != self.LEN:
         self.result = "Echo'ed message length differs from what I sent (got length {}, expected length {}).".format(len(msg), self.LEN)

      elif received_hash != self._expected_hash:
         self.result = "Echo'ed message contents differs from what I sent (got SHA1 {}, expected SHA1 {}).".format(binascii.hexlify(received_hash), binascii.hexlify(self._expected_hash))

      else:
         ## should not arrive here
         raise Exception("logic error")

   elif self.count < self.COUNT:
      self.sendOne()

   else:
      self.behavior = Case.OK
      self.result = "Ok, received all echo'ed messages in time."
      self.trafficStats = copy.deepcopy(self.p.trafficStats)
      self.p.enableWirelog(True)
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)



##
## Cases 12.x.x
##
Case12_X_X = []
Case12_X_X_CaseSubCategories = {}

def accept_deflate(self, offers):
   for offer in offers:
      if isinstance(offer, PerMessageDeflateOffer):
         return PerMessageDeflateOfferAccept(offer)

j = 1
for td in WS_COMPRESSION_TESTDATA:

   isBinary = WS_COMPRESSION_TESTDATA[td]["binary"]
   fn = pkg_resources.resource_filename("autobahntestsuite", "testdata/%s" % WS_COMPRESSION_TESTDATA[td]['file'])
   fileSize = os.path.getsize(fn)

   Case12_X_X_CaseSubCategories['12.%d' % j] = WS_COMPRESSION_TESTDATA[td]["desc"] + (" (%s, %s bytes)" % ("binary" if isBinary else "utf8", fileSize))

   i = 1
   for s in MSG_SIZES:
      cc = "Case12_%d_%d" % (j, i)
      DESCRIPTION = """Send %d compressed messages each of payload size %d, auto-fragment to %s octets. Use default permessage-deflate offer.""" % (s[1], s[0], s[3])
      EXPECTATION = """Receive echo'ed messages (with payload as sent). Timeout case after %d secs.""" % (s[2])
      C = type(cc,
                (object, Case, ),
                {"LEN": s[0],
                 "COUNT": s[1],
                 "WAITSECS": s[2],
                 "AUTOFRAGSIZE": s[3],
                 "CLIENT_OFFERS": [PerMessageDeflateOffer()],
                 "SERVER_ACCEPT": accept_deflate,
                 "TESTDATA": WS_COMPRESSION_TESTDATA[td],
                 "DESCRIPTION": """%s""" % DESCRIPTION,
                 "EXPECTATION": """%s""" % EXPECTATION,
                 "__init__": __init__,
                 "init": init,
                 "onOpen": onOpen,
                 "onMessage": onMessage,
                 "sendOne": sendOne,
                 })
      Case12_X_X.append(C)
      i += 1
   j += 1




##
## Cases 13.x.x
##
Case13_X_X = []
Case13_X_X_CaseSubCategories = {}


def accept1(self, offers):
   """
   server accept (requestNoContextTakeover, requestMaxWindowBits): [(False, 0)]
   """
   for offer in offers:
      if isinstance(offer, PerMessageDeflateOffer):
         return PerMessageDeflateOfferAccept(offer)

def accept2(self, offers):
   """
   server accept (requestNoContextTakeover, requestMaxWindowBits): [(True, 0)]
   """
   for offer in offers:
      if isinstance(offer, PerMessageDeflateOffer):
         if offer.acceptNoContextTakeover:
            return PerMessageDeflateOfferAccept(offer, requestNoContextTakeover = True)

def accept3(self, offers):
   """
   server accept (requestNoContextTakeover, requestMaxWindowBits): [(False, 8)]
   """
   for offer in offers:
      if isinstance(offer, PerMessageDeflateOffer):
         if offer.acceptMaxWindowBits:
            return PerMessageDeflateOfferAccept(offer, requestMaxWindowBits = 8)

def accept4(self, offers):
   """
   server accept (requestNoContextTakeover, requestMaxWindowBits): [(False, 15)]
   """
   for offer in offers:
      if isinstance(offer, PerMessageDeflateOffer):
         if offer.acceptMaxWindowBits:
            return PerMessageDeflateOfferAccept(offer, requestMaxWindowBits = 15)

def accept5(self, offers):
   """
   server accept (requestNoContextTakeover, requestMaxWindowBits): [(True, 8)]
   """
   for offer in offers:
      if isinstance(offer, PerMessageDeflateOffer):
         if offer.acceptNoContextTakeover and offer.acceptMaxWindowBits:
            return PerMessageDeflateOfferAccept(offer, requestMaxWindowBits = 8, requestNoContextTakeover = True)

def accept6(self, offers):
   """
   server accept (requestNoContextTakeover, requestMaxWindowBits): [(True, 15)]
   """
   for offer in offers:
      if isinstance(offer, PerMessageDeflateOffer):
         if offer.acceptNoContextTakeover and offer.acceptMaxWindowBits:
            return PerMessageDeflateOfferAccept(offer, requestMaxWindowBits = 15, requestNoContextTakeover = True)

def accept7(self, offers):
   """
   server accept (requestNoContextTakeover, requestMaxWindowBits): [(True, 8), (True, 0), (False, 0)]
   """
   a = accept5(self, offers)
   if a:
      return a
   else:
      a = accept2(self, offers)
      if a:
         return a
      else:
         return accept1(self, offers)


DEFLATE_PARAMS = [
   (accept1, [PerMessageDeflateOffer()]),
   (accept2, [PerMessageDeflateOffer(requestNoContextTakeover = True, requestMaxWindowBits = 0)]),
   (accept3, [PerMessageDeflateOffer(requestNoContextTakeover = False, requestMaxWindowBits = 8)]),
   (accept4, [PerMessageDeflateOffer(requestNoContextTakeover = False, requestMaxWindowBits = 15)]),
   (accept5, [PerMessageDeflateOffer(requestNoContextTakeover = True, requestMaxWindowBits = 8)]),
   (accept6, [PerMessageDeflateOffer(requestNoContextTakeover = True, requestMaxWindowBits = 15)]),
   (accept7, [PerMessageDeflateOffer(requestNoContextTakeover = True, requestMaxWindowBits = 8), PerMessageDeflateOffer(requestNoContextTakeover = True), PerMessageDeflateOffer()])
]


TEST_DATA = WS_COMPRESSION_TESTDATA['json_data1']


j = 1
for dp in DEFLATE_PARAMS:

   sa = dp[0]
   co = dp[1]

   isBinary = TEST_DATA["binary"]
   fn = pkg_resources.resource_filename("autobahntestsuite", "testdata/%s" % TEST_DATA['file'])
   fileSize = os.path.getsize(fn)

   co_desc = "client offers (requestNoContextTakeover, requestMaxWindowBits): {}".format([(x.requestNoContextTakeover, x.requestMaxWindowBits) for x in co])
   sa_desc = sa.__doc__.strip()

   Case13_X_X_CaseSubCategories['13.%d' % j] = TEST_DATA["desc"] + (" (%s, %s bytes)" % ("binary" if isBinary else "utf8", fileSize)) + " - " + co_desc + " / " + sa_desc

   i = 1
   for s in MSG_SIZES:
      cc = "Case13_%d_%d" % (j, i)
      DESCRIPTION = """Send %d compressed messages each of payload size %d, auto-fragment to %s octets. Use permessage-deflate %s""" % (s[1], s[0], s[3], co_desc)
      EXPECTATION = """Receive echo'ed messages (with payload as sent). Timeout case after %d secs.""" % (s[2])
      C = type(cc,
                (object, Case, ),
                {"LEN": s[0],
                 "COUNT": s[1],
                 "WAITSECS": s[2],
                 "AUTOFRAGSIZE": s[3],
                 "CLIENT_OFFERS": co,
                 "SERVER_ACCEPT": sa,
                 "TESTDATA": TEST_DATA,
                 "DESCRIPTION": """%s""" % DESCRIPTION,
                 "EXPECTATION": """%s""" % EXPECTATION,
                 "__init__": __init__,
                 "init": init,
                 "onOpen": onOpen,
                 "onMessage": onMessage,
                 "sendOne": sendOne,
                 })
      Case13_X_X.append(C)
      i += 1
   j += 1

########NEW FILE########
__FILENAME__ = case1_1_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case1_1_1(Case):

   DESCRIPTION = """Send text message with payload 0."""

   EXPECTATION = """Receive echo'ed text message (with empty payload). Clean close with normal code."""

   def onOpen(self):
      payload = ""
      self.expected[Case.OK] = [("message", payload, False)]      
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 1, payload = payload)
      self.p.killAfter(1)

      

########NEW FILE########
__FILENAME__ = case1_1_2
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case1_1_2(Case):

   DESCRIPTION = """Send text message message with payload of length 125."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent). Clean close with normal code."""

   def onOpen(self):
      payload = "*" * 125
      self.expected[Case.OK] = [("message", payload, False)]    
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      
      self.p.sendFrame(opcode = 1, payload = payload)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case1_1_3
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case1_1_3(Case):

   DESCRIPTION = """Send text message message with payload of length 126."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent). Clean close with normal code."""

   def onOpen(self):
      payload = "*" * 126
      self.expected[Case.OK] = [("message", payload, False)]      
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      
      self.p.sendFrame(opcode = 1, payload = payload)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case1_1_4
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case1_1_4(Case):

   DESCRIPTION = """Send text message message with payload of length 127."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent). Clean close with normal code."""

   def onOpen(self):
      payload = "*" * 127
      self.expected[Case.OK] = [("message", payload, False)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 1, payload = payload)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case1_1_5
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case1_1_5(Case):

   DESCRIPTION = """Send text message message with payload of length 128."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent). Clean close with normal code."""

   def onOpen(self):
      payload = "*" * 128
      self.expected[Case.OK] = [("message", payload, False)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 1, payload = payload)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case1_1_6
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case1_1_6(Case):

   DESCRIPTION = """Send text message message with payload of length 65535."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent). Clean close with normal code."""

   def onOpen(self):
      payload = "*" * 65535
      self.expected[Case.OK] = [("message", payload, False)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 1, payload = payload)
      self.p.killAfter(10)

########NEW FILE########
__FILENAME__ = case1_1_7
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case1_1_7(Case):

   DESCRIPTION = """Send text message message with payload of length 65536."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent). Clean close with normal code."""

   def onOpen(self):
      payload = "*" * 65536
      self.expected[Case.OK] = [("message", payload, False)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 1, payload = payload)
      self.p.killAfter(10)

########NEW FILE########
__FILENAME__ = case1_1_8
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case1_1_8(Case):

   DESCRIPTION = """Send text message message with payload of length 65536. Sent out data in chops of 997 octets."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent). Clean close with normal code."""

   def onOpen(self):
      payload = "*" * 65536
      self.expected[Case.OK] = [("message", payload, False)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 1, payload = payload, chopsize = 997)
      self.p.killAfter(10)

########NEW FILE########
__FILENAME__ = case1_2_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case1_2_1(Case):

   DESCRIPTION = """Send binary message with payload 0."""

   EXPECTATION = """Receive echo'ed binary message (with empty payload). Clean close with normal code."""

   def onOpen(self):
      payload = ""
      self.expected[Case.OK] = [("message", payload, True)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 2, payload = payload)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case1_2_2
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case1_2_2(Case):

   DESCRIPTION = """Send binary message message with payload of length 125."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent). Clean close with normal code."""

   def onOpen(self):
      payload = "\xfe" * 125
      self.expected[Case.OK] = [("message", payload, True)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 2, payload = payload)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case1_2_3
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case1_2_3(Case):

   DESCRIPTION = """Send binary message message with payload of length 126."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent). Clean close with normal code."""

   def onOpen(self):
      payload = "\xfe" * 126
      self.expected[Case.OK] = [("message", payload, True)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 2, payload = payload)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case1_2_4
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case1_2_4(Case):

   DESCRIPTION = """Send binary message message with payload of length 127."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent). Clean close with normal code."""

   def onOpen(self):
      payload = "\xfe" * 127
      self.expected[Case.OK] = [("message", payload, True)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 2, payload = payload)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case1_2_5
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case1_2_5(Case):

   DESCRIPTION = """Send binary message message with payload of length 128."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent). Clean close with normal code."""

   def onOpen(self):
      payload = "\xfe" * 128
      self.expected[Case.OK] = [("message", payload, True)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 2, payload = payload)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case1_2_6
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case1_2_6(Case):

   DESCRIPTION = """Send binary message message with payload of length 65535."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent). Clean close with normal code."""

   def onOpen(self):
      payload = "\xfe" * 65535
      self.expected[Case.OK] = [("message", payload, True)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 2, payload = payload)
      self.p.killAfter(10)

########NEW FILE########
__FILENAME__ = case1_2_7
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case1_2_7(Case):

   DESCRIPTION = """Send binary message message with payload of length 65536."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent). Clean close with normal code."""

   def onOpen(self):
      payload = "\xfe" * 65536
      self.expected[Case.OK] = [("message", payload, True)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 2, payload = payload)
      self.p.killAfter(10)

########NEW FILE########
__FILENAME__ = case1_2_8
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case1_2_8(Case):

   DESCRIPTION = """Send binary message message with payload of length 65536. Sent out data in chops of 997 octets."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent). Clean close with normal code."""

   def onOpen(self):
      payload = "\xfe" * 65536
      self.expected[Case.OK] = [("message", payload, True)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 2, payload = payload, chopsize = 997)
      self.p.killAfter(10)

########NEW FILE########
__FILENAME__ = case2_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case2_1(Case):

   DESCRIPTION = """Send ping without payload."""

   EXPECTATION = """Pong (with empty payload) is sent in reply to Ping. Clean close with normal code."""

   def onOpen(self):
      self.expected[Case.OK] = [("pong", "")]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 9)
      self.p.closeAfter(1)
########NEW FILE########
__FILENAME__ = case2_10
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case2_10(Case):

   DESCRIPTION = """Send 10 Pings with payload."""

   EXPECTATION = """Pongs for our Pings with all the payloads. Note: This is not required by the Spec .. but we check for this behaviour anyway. Clean close with normal code."""

   def init(self):
      self.chopsize = None

   def onOpen(self):
      self.expected[Case.OK] = []
      for i in xrange(0, 10):
         payload = "payload-%d" % i
         self.expected[Case.OK].append(("pong", payload))
         self.p.sendFrame(opcode = 9, payload = payload, chopsize = self.chopsize)
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.closeAfter(3)

########NEW FILE########
__FILENAME__ = case2_11
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case2_10 import *

class Case2_11(Case2_10):

   DESCRIPTION = """Send 10 Pings with payload. Send out octets in octet-wise chops."""

   EXPECTATION = """Pongs for our Pings with all the payloads. Note: This is not required by the Spec .. but we check for this behaviour anyway. Clean close with normal code."""

   def init(self):
      self.chopsize = 1

########NEW FILE########
__FILENAME__ = case2_2
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case2_2(Case):

   DESCRIPTION = """Send ping with small text payload."""

   EXPECTATION = """Pong with payload echo'ed is sent in reply to Ping. Clean close with normal code."""

   def onOpen(self):
      payload = "Hello, world!"
      self.expected[Case.OK] = [("pong", payload)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 9, payload = payload)
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case2_3
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case2_3(Case):

   DESCRIPTION = """Send ping with small binary (non UTF-8) payload."""

   EXPECTATION = """Pong with payload echo'ed is sent in reply to Ping. Clean close with normal code."""

   def onOpen(self):
      payload = "\x00\xff\xfe\xfd\xfc\xfb\x00\xff"
      
      self.expected[Case.OK] = [("pong", payload)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 9, payload = payload)
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case2_4
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case2_4(Case):

   DESCRIPTION = """Send ping with binary payload of 125 octets."""

   EXPECTATION = """Pong with payload echo'ed is sent in reply to Ping. Clean close with normal code."""

   def onOpen(self):
      payload = "\xfe" * 125
      self.expected[Case.OK] = [("pong", payload)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 9, payload = payload)
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case2_5
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case2_5(Case):

   DESCRIPTION = """Send ping with binary payload of 126 octets."""

   EXPECTATION = """Connection is failed immediately (1002/Protocol Error), since control frames are only allowed to have payload up to and including 125 octets.."""

   def onOpen(self):
      payload = "\xfe" * 126
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 9, payload = payload)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case2_6
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case2_6(Case):

   DESCRIPTION = """Send ping with binary payload of 125 octets, send in octet-wise chops."""

   EXPECTATION = """Pong with payload echo'ed is sent in reply to Ping. Implementations must be TCP clean. Clean close with normal code."""

   def onOpen(self):
      payload = "\xfe" * 125
      self.expected[Case.OK] = [("pong", payload)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 9, payload = payload, chopsize = 1)
      self.p.closeAfter(2)

########NEW FILE########
__FILENAME__ = case2_7
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case2_7(Case):

   DESCRIPTION = """Send unsolicited pong without payload. Verify nothing is received. Clean close with normal code."""

   EXPECTATION = """Nothing."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 10)
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case2_8
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case2_8(Case):

   DESCRIPTION = """Send unsolicited pong with payload. Verify nothing is received. Clean close with normal code."""

   EXPECTATION = """Nothing."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 10, payload = "unsolicited pong payload")
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)
      self.p.closeAfter(1)
      
      
########NEW FILE########
__FILENAME__ = case2_9
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case2_9(Case):

   DESCRIPTION = """Send unsolicited pong with payload. Send ping with payload. Verify pong for ping is received."""

   EXPECTATION = """Nothing in reply to own Pong, but Pong with payload echo'ed in reply to Ping. Clean close with normal code."""

   def onOpen(self):
      payload = "ping payload"
      self.expected[Case.OK] = [("pong",payload)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 10, payload = "unsolicited pong payload")
      self.p.sendFrame(opcode = 9, payload = payload)
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case3_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case3_1(Case):

   DESCRIPTION = """Send small text message with <b>RSV = 1</b>."""

   EXPECTATION = """The connection is failed immediately (1002/protocol error), since RSV must be 0, when no extension defining RSV meaning has been negoiated."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe": False,
                            "closeCode": [self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],
                            "requireClean": False}
      self.p.sendFrame(opcode = 1, payload = "Hello, world!", rsv = 1)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case3_2
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case3_2(Case):

   DESCRIPTION = """Send small text message, then send again with <b>RSV = 2</b>, then send Ping."""

   EXPECTATION = """Echo for first message is received, but then connection is failed immediately, since RSV must be 0, when no extension defining RSV meaning has been negoiated. The Pong is not received."""

   def onOpen(self):
      payload = "Hello, world!"
      self.expected[Case.OK] = [("message", payload, False)]
      self.expected[Case.NON_STRICT] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 1, payload = payload)
      self.p.sendFrame(opcode = 1, payload = payload, rsv = 2)
      self.p.sendFrame(opcode = 9)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case3_3
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case3_3(Case):

   DESCRIPTION = """Send small text message, then send again with <b>RSV = 3</b>, then send Ping. Octets are sent in frame-wise chops. Octets are sent in octet-wise chops."""

   EXPECTATION = """Echo for first message is received, but then connection is failed immediately, since RSV must be 0, when no extension defining RSV meaning has been negoiated. The Pong is not received."""

   def onOpen(self):
      payload = "Hello, world!"
      self.expected[Case.OK] = [("message", payload, False)]
      self.expected[Case.NON_STRICT] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 1, payload = payload, sync = True)
      self.p.sendFrame(opcode = 1, payload = payload, rsv = 3, sync = True)
      self.p.sendFrame(opcode = 9, sync = True)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case3_4
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case3_4(Case):

   DESCRIPTION = """Send small text message, then send again with <b>RSV = 4</b>, then send Ping. Octets are sent in octet-wise chops."""

   EXPECTATION = """Echo for first message is received, but then connection is failed immediately, since RSV must be 0, when no extension defining RSV meaning has been negoiated. The Pong is not received."""

   def onOpen(self):
      payload = "Hello, world!"
      self.expected[Case.OK] = [("message", payload, False)]
      self.expected[Case.NON_STRICT] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 1, payload = payload, chopsize = 1)
      self.p.sendFrame(opcode = 1, payload = payload, rsv = 4, chopsize = 1)
      self.p.sendFrame(opcode = 9, chopsize = 1)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case3_5
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case3_5(Case):

   DESCRIPTION = """Send small binary message with <b>RSV = 5</b>."""

   EXPECTATION = """The connection is failed immediately, since RSV must be 0."""

   def onOpen(self):
      payload = "\x00\xff\xfe\xfd\xfc\xfb\x00\xff"
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 2, payload = payload, rsv = 5)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case3_6
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case3_6(Case):

   DESCRIPTION = """Send Ping with <b>RSV = 6</b>."""

   EXPECTATION = """The connection is failed immediately, since RSV must be 0."""

   def onOpen(self):
      payload = "Hello, world!"
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 2, payload = payload, rsv = 6)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case3_7
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case3_7(Case):

   DESCRIPTION = """Send Close with <b>RSV = 7</b>."""

   EXPECTATION = """The connection is failed immediately, since RSV must be 0."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 8, rsv = 7)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case4_1_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case4_1_1(Case):

   DESCRIPTION = """Send frame with reserved non-control <b>Opcode = 3</b>."""

   EXPECTATION = """The connection is failed immediately."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 3)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case4_1_2
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case4_1_2(Case):

   DESCRIPTION = """Send frame with reserved non-control <b>Opcode = 4</b> and non-empty payload."""

   EXPECTATION = """The connection is failed immediately."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 4, payload = "reserved opcode payload")
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case4_1_3
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case4_1_3(Case):

   DESCRIPTION = """Send small text message, then send frame with reserved non-control <b>Opcode = 5</b>, then send Ping."""

   EXPECTATION = """Echo for first message is received, but then connection is failed immediately, since reserved opcode frame is used. A Pong is not received."""

   def onOpen(self):
      payload = "Hello, world!"
      self.expected[Case.OK] = [("message", payload, False)]
      self.expected[Case.NON_STRICT] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 1, payload = payload)
      self.p.sendFrame(opcode = 5)
      self.p.sendFrame(opcode = 9)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case4_1_4
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case4_1_4(Case):

   DESCRIPTION = """Send small text message, then send frame with reserved non-control <b>Opcode = 6</b> and non-empty payload, then send Ping."""

   EXPECTATION = """Echo for first message is received, but then connection is failed immediately, since reserved opcode frame is used. A Pong is not received."""

   def onOpen(self):
      payload = "Hello, world!"
      self.expected[Case.OK] = [("message", payload, False)]
      self.expected[Case.NON_STRICT] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 1, payload = payload)
      self.p.sendFrame(opcode = 6, payload = payload)
      self.p.sendFrame(opcode = 9)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case4_1_5
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case4_1_5(Case):

   DESCRIPTION = """Send small text message, then send frame with reserved non-control <b>Opcode = 7</b> and non-empty payload, then send Ping."""

   EXPECTATION = """Echo for first message is received, but then connection is failed immediately, since reserved opcode frame is used. A Pong is not received."""

   def onOpen(self):
      payload = "Hello, world!"
      self.expected[Case.OK] = [("message", payload, False)]
      self.expected[Case.NON_STRICT] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 1, payload = payload, chopsize = 1)
      self.p.sendFrame(opcode = 7, payload = payload, chopsize = 1)
      self.p.sendFrame(opcode = 9, chopsize = 1)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case4_2_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case4_2_1(Case):

   DESCRIPTION = """Send frame with reserved control <b>Opcode = 11</b>."""

   EXPECTATION = """The connection is failed immediately."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 11)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case4_2_2
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case4_2_2(Case):

   DESCRIPTION = """Send frame with reserved control <b>Opcode = 12</b> and non-empty payload."""

   EXPECTATION = """The connection is failed immediately."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 12, payload = "reserved opcode payload")
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case4_2_3
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case4_2_3(Case):

   DESCRIPTION = """Send small text message, then send frame with reserved control <b>Opcode = 13</b>, then send Ping."""

   EXPECTATION = """Echo for first message is received, but then connection is failed immediately, since reserved opcode frame is used. A Pong is not received."""

   def onOpen(self):
      payload = "Hello, world!"
      self.expected[Case.OK] = [("message", payload, False)]
      self.expected[Case.NON_STRICT] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 1, payload = payload)
      self.p.sendFrame(opcode = 13)
      self.p.sendFrame(opcode = 9)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case4_2_4
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case4_2_4(Case):

   DESCRIPTION = """Send small text message, then send frame with reserved control <b>Opcode = 14</b> and non-empty payload, then send Ping."""

   EXPECTATION = """Echo for first message is received, but then connection is failed immediately, since reserved opcode frame is used. A Pong is not received."""

   def onOpen(self):
      payload = "Hello, world!"
      self.expected[Case.OK] = [("message", payload, False)]
      self.expected[Case.NON_STRICT] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 1, payload = payload)
      self.p.sendFrame(opcode = 14, payload = payload)
      self.p.sendFrame(opcode = 9)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case4_2_5
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case4_2_5(Case):

   DESCRIPTION = """Send small text message, then send frame with reserved control <b>Opcode = 15</b> and non-empty payload, then send Ping."""

   EXPECTATION = """Echo for first message is received, but then connection is failed immediately, since reserved opcode frame is used. A Pong is not received."""

   def onOpen(self):
      payload = "Hello, world!"
      self.expected[Case.OK] = [("message", payload, False)]
      self.expected[Case.NON_STRICT] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 1, payload = payload, chopsize = 1)
      self.p.sendFrame(opcode = 15, payload = payload, chopsize = 1)
      self.p.sendFrame(opcode = 9, chopsize = 1)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case5_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_1(Case):

   DESCRIPTION = """Send Ping fragmented into 2 fragments."""

   EXPECTATION = """Connection is failed immediately, since control message MUST NOT be fragmented."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 9, fin = False, payload = "fragment1")
      self.p.sendFrame(opcode = 0, fin = True, payload = "fragment2")
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case5_10
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_10(Case):

   DESCRIPTION = """Send unfragmented Text Message after Continuation Frame with FIN = true, where there is nothing to continue, sent in per-frame chops."""

   EXPECTATION = """The connection is failed immediately, since there is no message to continue."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 0, fin = True, payload = "non-continuation payload", sync = True)
      self.p.sendFrame(opcode = 1, fin = True, payload = "Hello, world!", sync = True)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case5_11
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_11(Case):

   DESCRIPTION = """Send unfragmented Text Message after Continuation Frame with FIN = true, where there is nothing to continue, sent in octet-wise chops."""

   EXPECTATION = """The connection is failed immediately, since there is no message to continue."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 0, fin = True, payload = "non-continuation payload", chopsize = 1)
      self.p.sendFrame(opcode = 1, fin = True, payload = "Hello, world!", chopsize = 1)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case5_12
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_12(Case):

   DESCRIPTION = """Send unfragmented Text Message after Continuation Frame with FIN = false, where there is nothing to continue, sent in one chop."""

   EXPECTATION = """The connection is failed immediately, since there is no message to continue."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 0, fin = False, payload = "non-continuation payload")
      self.p.sendFrame(opcode = 1, fin = True, payload = "Hello, world!")
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case5_13
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_13(Case):

   DESCRIPTION = """Send unfragmented Text Message after Continuation Frame with FIN = false, where there is nothing to continue, sent in per-frame chops."""

   EXPECTATION = """The connection is failed immediately, since there is no message to continue."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 0, fin = False, payload = "non-continuation payload", sync = True)
      self.p.sendFrame(opcode = 1, fin = True, payload = "Hello, world!", sync = True)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case5_14
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_14(Case):

   DESCRIPTION = """Send unfragmented Text Message after Continuation Frame with FIN = false, where there is nothing to continue, sent in octet-wise chops."""

   EXPECTATION = """The connection is failed immediately, since there is no message to continue."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 0, fin = False, payload = "non-continuation payload", chopsize = 1)
      self.p.sendFrame(opcode = 1, fin = True, payload = "Hello, world!", chopsize = 1)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case5_15
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_15(Case):

   DESCRIPTION = """Send text Message fragmented into 2 fragments, then Continuation Frame with FIN = false where there is nothing to continue, then unfragmented Text Message, all sent in one chop."""

   EXPECTATION = """The connection is failed immediately, since there is no message to continue."""

   def onOpen(self):
      fragments = ["fragment1", "fragment2", "fragment3", "fragment4"]
      self.expected[Case.OK] = [("message", ''.join(fragments[:2]), False)]
      self.expected[Case.NON_STRICT] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 1, fin = False, payload = fragments[0])
      self.p.sendFrame(opcode = 0, fin = True, payload = fragments[1])
      self.p.sendFrame(opcode = 0, fin = False, payload = fragments[2])
      self.p.sendFrame(opcode = 1, fin = True, payload = fragments[3])
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case5_16
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_16(Case):

   DESCRIPTION = """Repeated 2x: Continuation Frame with FIN = false (where there is nothing to continue), then text Message fragmented into 2 fragments."""

   EXPECTATION = """The connection is failed immediately, since there is no message to continue."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      for i in xrange(0, 2):
         self.p.sendFrame(opcode = 0, fin = False, payload = "fragment1")
         self.p.sendFrame(opcode = 1, fin = False, payload = "fragment2")
         self.p.sendFrame(opcode = 0, fin = True, payload = "fragment3")
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case5_17
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_17(Case):

   DESCRIPTION = """Repeated 2x: Continuation Frame with FIN = true (where there is nothing to continue), then text Message fragmented into 2 fragments."""

   EXPECTATION = """The connection is failed immediately, since there is no message to continue."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      for i in xrange(0, 2):
         self.p.sendFrame(opcode = 0, fin = True, payload = "fragment1")
         self.p.sendFrame(opcode = 1, fin = False, payload = "fragment2")
         self.p.sendFrame(opcode = 0, fin = True, payload = "fragment3")
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case5_18
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_18(Case):

   DESCRIPTION = """Send text Message fragmented into 2 fragments, with both frame opcodes set to text, sent in one chop."""

   EXPECTATION = """The connection is failed immediately, since all data frames after the initial data frame must have opcode 0."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 1, fin = False, payload = "fragment1")
      self.p.sendFrame(opcode = 1, fin = True, payload = "fragment2")
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case5_19
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_19(Case):

   DESCRIPTION = """A fragmented text message is sent in multiple frames. After
   sending the first 2 frames of the text message, a Ping is sent. Then we wait 1s,
   then we send 2 more text fragments, another Ping and then the final text fragment.
   Everything is legal."""

   EXPECTATION = """The peer immediately answers the first Ping before
   it has received the last text message fragment. The peer pong's back the Ping's
   payload exactly, and echo's the payload of the fragmented message back to us."""


   def init(self):
      self.sync = False


   def onOpen(self):

      self.fragments = ["fragment1", "fragment2", "fragment3", "fragment4", "fragment5"]
      self.pings = ["pongme 1!", "pongme 2!"]

      self.expected[Case.OK] = [("pong", self.pings[0]), ("pong", self.pings[1]), ("message", ''.join(self.fragments), False)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}

      self.p.sendFrame(opcode = 1, fin = False, payload = self.fragments[0], sync = self.sync)
      self.p.sendFrame(opcode = 0, fin = False, payload = self.fragments[1], sync = self.sync)
      self.p.sendFrame(opcode = 9, fin = True, payload = self.pings[0], sync = self.sync)
      self.p.continueLater(1, self.part2)


   def part2(self):

      self.p.sendFrame(opcode = 0, fin = False, payload = self.fragments[2], sync = self.sync)
      self.p.sendFrame(opcode = 0, fin = False, payload = self.fragments[3], sync = self.sync)
      self.p.sendFrame(opcode = 9, fin = True, payload = self.pings[1], sync = self.sync)
      self.p.sendFrame(opcode = 0, fin = True, payload = self.fragments[4], sync = self.sync)
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case5_2
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_2(Case):

   DESCRIPTION = """Send Pong fragmented into 2 fragments."""

   EXPECTATION = """Connection is failed immediately, since control message MUST NOT be fragmented."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 10, fin = False, payload = "fragment1")
      self.p.sendFrame(opcode = 0, fin = True, payload = "fragment2")
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case5_20
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case5_19 import *

class Case5_20(Case5_19):

   DESCRIPTION = """Same as Case 5.19, but send all frames with SYNC = True.
   Note, this does not change the octets sent in any way, only how the stream
   is chopped up on the wire."""

   EXPECTATION = """Same as Case 5.19. Implementations must be agnostic to how
   octet stream is chopped up on wire (must be TCP clean)."""

   def init(self):
      self.sync = True

########NEW FILE########
__FILENAME__ = case5_3
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_3(Case):

   DESCRIPTION = """Send text Message fragmented into 2 fragments."""

   EXPECTATION = """Message is processed and echo'ed back to us."""

   def onOpen(self):
      fragments = ["fragment1", "fragment2"]
      self.expected[Case.OK] = [("message", ''.join(fragments), False)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 1, fin = False, payload = fragments[0])
      self.p.sendFrame(opcode = 0, fin = True, payload = fragments[1])
      self.p.closeAfter(1)
########NEW FILE########
__FILENAME__ = case5_4
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_4(Case):

   DESCRIPTION = """Send text Message fragmented into 2 fragments, octets are sent in frame-wise chops."""

   EXPECTATION = """Message is processed and echo'ed back to us."""

   def onOpen(self):
      fragments = ["fragment1", "fragment2"]
      self.expected[Case.OK] = [("message", ''.join(fragments), False)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 1, fin = False, payload = fragments[0], sync = True)
      self.p.sendFrame(opcode = 0, fin = True, payload = fragments[1], sync = True)
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case5_5
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_5(Case):

   DESCRIPTION = """Send text Message fragmented into 2 fragments, octets are sent in octet-wise chops."""

   EXPECTATION = """Message is processed and echo'ed back to us."""

   def onOpen(self):
      fragments = ["fragment1", "fragment2"]
      self.expected[Case.OK] = [("message", ''.join(fragments), False)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 1, fin = False, payload = fragments[0], chopsize = 1)
      self.p.sendFrame(opcode = 0, fin = True, payload = fragments[1], chopsize = 1)
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case5_6
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_6(Case):

   DESCRIPTION = """Send text Message fragmented into 2 fragments, one ping with payload in-between."""

   EXPECTATION = """A pong is received, then the message is echo'ed back to us."""

   def onOpen(self):
      ping_payload = "ping payload"
      fragments = ["fragment1", "fragment2"]
      self.expected[Case.OK] = [("pong", ping_payload), ("message", ''.join(fragments), False)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 1, fin = False, payload = fragments[0])
      self.p.sendFrame(opcode = 9, fin = True, payload = ping_payload)
      self.p.sendFrame(opcode = 0, fin = True, payload = fragments[1])
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case5_7
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_7(Case):

   DESCRIPTION = """Send text Message fragmented into 2 fragments, one ping with payload in-between. Octets are sent in frame-wise chops."""

   EXPECTATION = """A pong is received, then the message is echo'ed back to us."""

   def onOpen(self):
      ping_payload = "ping payload"
      fragments = ["fragment1", "fragment2"]
      self.expected[Case.OK] = [("pong", ping_payload), ("message", ''.join(fragments), False)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 1, fin = False, payload = fragments[0], sync = True)
      self.p.sendFrame(opcode = 9, fin = True, payload = ping_payload, sync = True)
      self.p.sendFrame(opcode = 0, fin = True, payload = fragments[1], sync = True)
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case5_8
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_8(Case):

   DESCRIPTION = """Send text Message fragmented into 2 fragments, one ping with payload in-between. Octets are sent in octet-wise chops."""

   EXPECTATION = """A pong is received, then the message is echo'ed back to us."""

   def onOpen(self):
      ping_payload = "ping payload"
      fragments = ["fragment1", "fragment2"]
      self.expected[Case.OK] = [("pong", ping_payload), ("message", ''.join(fragments), False)]
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 1, fin = False, payload = fragments[0], chopsize = 1)
      self.p.sendFrame(opcode = 9, fin = True, payload = ping_payload, chopsize = 1)
      self.p.sendFrame(opcode = 0, fin = True, payload = fragments[1], chopsize = 1)
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case5_9
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case5_9(Case):

   DESCRIPTION = """Send unfragmented Text Message after Continuation Frame with FIN = true, where there is nothing to continue, sent in one chop."""

   EXPECTATION = """The connection is failed immediately, since there is no message to continue."""

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":False,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendFrame(opcode = 0, fin = True, payload = "non-continuation payload")
      self.p.sendFrame(opcode = 1, fin = True, payload = "Hello, world!")
      self.p.killAfter(1)


########NEW FILE########
__FILENAME__ = case6_1_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case6_1_1(Case):

   DESCRIPTION = """Send text message of length 0."""

   EXPECTATION = """A message is echo'ed back to us (with empty payload)."""

   def onOpen(self):
      self.expected[Case.OK] = [("message", "", False)]
      self.expectedClose = {"closedByMe": True,
                            "closeCode": [self.p.CLOSE_STATUS_CODE_NORMAL],
                            "requireClean": True}
      self.p.sendFrame(opcode = 1, payload = "")
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case6_1_2
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case6_1_2(Case):

   DESCRIPTION = """Send fragmented text message, 3 fragments each of length 0."""

   EXPECTATION = """A message is echo'ed back to us (with empty payload)."""

   def onOpen(self):
      self.expected[Case.OK] = [("message", "", False)]
      self.expectedClose = {"closedByMe": True,
                            "closeCode": [self.p.CLOSE_STATUS_CODE_NORMAL],
                            "requireClean": True}
      self.p.sendFrame(opcode = 1, fin = False, payload = "")
      self.p.sendFrame(opcode = 0, fin = False, payload = "")
      self.p.sendFrame(opcode = 0, fin = True, payload = "")
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case6_1_3
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case6_1_3(Case):

   DESCRIPTION = """Send fragmented text message, 3 fragments, first and last of length 0, middle non-empty."""

   EXPECTATION = """A message is echo'ed back to us (with payload = payload of middle fragment)."""

   def onOpen(self):
      payload = "middle frame payload"
      self.expected[Case.OK] = [("message", payload, False)]
      self.expectedClose = {"closedByMe": True,
                            "closeCode": [self.p.CLOSE_STATUS_CODE_NORMAL],
                            "requireClean": True}
      self.p.sendFrame(opcode = 1, fin = False, payload = "")
      self.p.sendFrame(opcode = 0, fin = False, payload = payload)
      self.p.sendFrame(opcode = 0, fin = True, payload = "")
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case6_2_1
# coding=utf-8

###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case
import binascii

class Case6_2_1(Case):

   PAYLOAD = "Hello-µ@ßöäüàá-UTF-8!!"

   DESCRIPTION = """Send a valid UTF-8 text message in one fragment.<br><br>MESSAGE:<br>%s<br>%s""" % (PAYLOAD, binascii.b2a_hex(PAYLOAD))

   EXPECTATION = """The message is echo'ed back to us."""

   def onOpen(self):

      self.expected[Case.OK] = [("message", self.PAYLOAD, False)]
      self.expectedClose = {"closedByMe": True,
                            "closeCode": [self.p.CLOSE_STATUS_CODE_NORMAL],
                            "requireClean": True}
      self.p.sendMessage(self.PAYLOAD, isBinary = False)
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case6_2_2
# coding=utf-8

###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case
import binascii

class Case6_2_2(Case):

   PAYLOAD1 = "Hello-µ@ßöä"
   PAYLOAD2 = "üàá-UTF-8!!"

   DESCRIPTION = """Send a valid UTF-8 text message in two fragments, fragmented on UTF-8 code point boundary.<br><br>MESSAGE FRAGMENT 1:<br>%s<br>%s<br><br>MESSAGE FRAGMENT 2:<br>%s<br>%s""" % (PAYLOAD1, binascii.b2a_hex(PAYLOAD1), PAYLOAD2, binascii.b2a_hex(PAYLOAD2))

   EXPECTATION = """The message is echo'ed back to us."""

   def onOpen(self):

      self.expected[Case.OK] = [("message", self.PAYLOAD1 + self.PAYLOAD2, False)]
      self.expectedClose = {"closedByMe": True,
                            "closeCode": [self.p.CLOSE_STATUS_CODE_NORMAL],
                            "requireClean": True}
      self.p.sendFrame(opcode = 1, fin = False, payload = self.PAYLOAD1)
      self.p.sendFrame(opcode = 0, fin = True, payload = self.PAYLOAD2)
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case6_2_3
# coding=utf-8

###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case
import binascii

class Case6_2_3(Case):

   PAYLOAD = "Hello-µ@ßöäüàá-UTF-8!!"

   DESCRIPTION = """Send a valid UTF-8 text message in fragments of 1 octet, resulting in frames ending on positions which are not code point ends.<br><br>MESSAGE:<br>%s<br>%s""" % (PAYLOAD, binascii.b2a_hex(PAYLOAD))

   EXPECTATION = """The message is echo'ed back to us."""

   def onOpen(self):

      self.expected[Case.OK] = [("message", self.PAYLOAD, False)]
      self.expectedClose = {"closedByMe": True,
                            "closeCode": [self.p.CLOSE_STATUS_CODE_NORMAL],
                            "requireClean": True}
      self.p.sendMessage(self.PAYLOAD, isBinary = False, fragmentSize = 1)
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case6_2_4
# coding=utf-8

###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case
import binascii

class Case6_2_4(Case):

   PAYLOAD = '\xce\xba\xe1\xbd\xb9\xcf\x83\xce\xbc\xce\xb5'

   DESCRIPTION = """Send a valid UTF-8 text message in fragments of 1 octet, resulting in frames ending on positions which are not code point ends.<br><br>MESSAGE:<br>%s<br>%s""" % (PAYLOAD, binascii.b2a_hex(PAYLOAD))

   EXPECTATION = """The message is echo'ed back to us."""

   def onOpen(self):

      self.expected[Case.OK] = [("message", self.PAYLOAD, False)]
      self.expectedClose = {"closedByMe": True,
                            "closeCode": [self.p.CLOSE_STATUS_CODE_NORMAL],
                            "requireClean": True}
      self.p.sendMessage(self.PAYLOAD, isBinary = False, fragmentSize = 1)
      self.p.closeAfter(1)

########NEW FILE########
__FILENAME__ = case6_3_1
# coding=utf-8

###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case
import binascii

class Case6_3_1(Case):

   # invalid exactly on byte 12 (\xa0)
   PAYLOAD1 = '\xce\xba\xe1\xbd\xb9\xcf\x83\xce\xbc\xce\xb5'
   PAYLOAD2 = '\xed\xa0\x80'
   PAYLOAD3 = '\x65\x64\x69\x74\x65\x64'
   PAYLOAD = PAYLOAD1 + PAYLOAD2 + PAYLOAD3

   DESCRIPTION = """Send invalid UTF-8 text message unfragmented.<br><br>MESSAGE:<br>%s""" % binascii.b2a_hex(PAYLOAD)

   EXPECTATION = """The connection is failed immediately, since the payload is not valid UTF-8."""

   def onOpen(self):

      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe": False,
                            "closeCode": [self.p.CLOSE_STATUS_CODE_INVALID_PAYLOAD],
                            "requireClean": False,
                            "closedByWrongEndpointIsFatal": True}
      self.p.sendMessage(self.PAYLOAD, isBinary = False)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case6_3_2
# coding=utf-8

###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case
from case6_3_1 import Case6_3_1
import binascii

class Case6_3_2(Case6_3_1):

   DESCRIPTION = """Send invalid UTF-8 text message in fragments of 1 octet, resulting in frames ending on positions which are not code point ends.<br><br>MESSAGE:<br>%s""" % binascii.b2a_hex(Case6_3_1.PAYLOAD)

   EXPECTATION = """The connection is failed immediately, since the payload is not valid UTF-8."""

   def onOpen(self):

      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe": False,
                            "closeCode": [self.p.CLOSE_STATUS_CODE_INVALID_PAYLOAD],
                            "requireClean": False,
                            "closedByWrongEndpointIsFatal": True}
      self.p.sendMessage(self.PAYLOAD, isBinary = False, fragmentSize = 1)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case6_4_1
# coding=utf-8

###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

import binascii
from case import Case
from autobahn.websocket.protocol import WebSocketProtocol


class Case6_4_1(Case):

   PAYLOAD1 = '\xce\xba\xe1\xbd\xb9\xcf\x83\xce\xbc\xce\xb5'
   #PAYLOAD2 = '\xed\xa0\x80' # invalid exactly on byte 12 (\xa0)
   PAYLOAD2 = '\xf4\x90\x80\x80' #invalid exactly on byte 12 (\x90)
   PAYLOAD3 = '\x65\x64\x69\x74\x65\x64'
   PAYLOAD = PAYLOAD1 + PAYLOAD2 + PAYLOAD3

   DESCRIPTION = """Send invalid UTF-8 text message in 3 fragments (frames).
First frame payload is valid, then wait, then 2nd frame which contains the payload making the sequence invalid, then wait, then 3rd frame with rest.
Note that PART1 and PART3 are valid UTF-8 in themselves, PART2 is a 0x110000 encoded as in the UTF-8 integer encoding scheme, but the codepoint is invalid (out of range).
<br><br>MESSAGE PARTS:<br>
PART1 = %s<br>
PART2 = %s<br>
PART3 = %s<br>
""" % (binascii.b2a_hex(PAYLOAD1), binascii.b2a_hex(PAYLOAD2), binascii.b2a_hex(PAYLOAD3))

   EXPECTATION = """The first frame is accepted, we expect to timeout on the first wait. The 2nd frame should be rejected immediately (fail fast on UTF-8). If we timeout, we expect the connection is failed at least then, since the complete message payload is not valid UTF-8."""

   def onOpen(self):

      self.expected[Case.OK] = [("timeout", "A")]
      self.expected[Case.NON_STRICT] = [("timeout", "A"), ("timeout", "B")]

      self.expectedClose = {"closedByMe": False,
                            "closeCode": [self.p.CLOSE_STATUS_CODE_INVALID_PAYLOAD],
                            "requireClean": False,
                            "closedByWrongEndpointIsFatal": True}

      self.p.sendFrame(opcode = 1, fin = False, payload = self.PAYLOAD1)
      self.p.continueLater(1, self.part2, "A")

   def part2(self):
      if self.p.state == WebSocketProtocol.STATE_OPEN:
         self.received.append(("timeout", "A"))
         self.p.sendFrame(opcode = 0, fin = False, payload = self.PAYLOAD2)
         self.p.continueLater(1, self.part3, "B")

   def part3(self):
      if self.p.state == WebSocketProtocol.STATE_OPEN:
         self.received.append(("timeout", "B"))
         self.p.sendFrame(opcode = 0, fin = True, payload = self.PAYLOAD3)
         self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case6_4_2
# coding=utf-8

###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

import binascii
from case import Case
from case6_4_1 import Case6_4_1
from autobahn.websocket.protocol import WebSocketProtocol


class Case6_4_2(Case6_4_1):

   DESCRIPTION = """Same as Case 6.4.1, but in 2nd frame, we send only up to and including the octet making the complete payload invalid.
<br><br>MESSAGE PARTS:<br>
PART1 = %s<br>
PART2 = %s<br>
PART3 = %s<br>
""" % (binascii.b2a_hex(Case6_4_1.PAYLOAD[:12]), binascii.b2a_hex(Case6_4_1.PAYLOAD[12]), binascii.b2a_hex(Case6_4_1.PAYLOAD[13:]))

   EXPECTATION = """The first frame is accepted, we expect to timeout on the first wait. The 2nd frame should be rejected immediately (fail fast on UTF-8). If we timeout, we expect the connection is failed at least then, since the complete message payload is not valid UTF-8."""

   def onOpen(self):

      self.expected[Case.OK] = [("timeout", "A")]
      self.expected[Case.NON_STRICT] = [("timeout", "A"), ("timeout", "B")]

      self.expectedClose = {"closedByMe": False,
                            "closeCode": [self.p.CLOSE_STATUS_CODE_INVALID_PAYLOAD],
                            "requireClean": False,
                            "closedByWrongEndpointIsFatal": True}

      self.p.sendFrame(opcode = 1, fin = False, payload = self.PAYLOAD[:12])
      self.p.continueLater(1, self.part2, "A")

   def part2(self):
      if self.p.state == WebSocketProtocol.STATE_OPEN:
         self.received.append(("timeout", "A"))
         self.p.sendFrame(opcode = 0, fin = False, payload = self.PAYLOAD[12])
         self.p.continueLater(1, self.part3, "B")

   def part3(self):
      if self.p.state == WebSocketProtocol.STATE_OPEN:
         self.received.append(("timeout", "B"))
         self.p.sendFrame(opcode = 0, fin = True, payload = self.PAYLOAD[13:])
         self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case6_4_3
# coding=utf-8

###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

import binascii
from case import Case
from case6_4_1 import Case6_4_1
from autobahn.websocket.protocol import WebSocketProtocol


class Case6_4_3(Case6_4_1):

   DESCRIPTION = """Same as Case 6.4.1, but we send message not in 3 frames, but in 3 chops of the same message frame.
<br><br>MESSAGE PARTS:<br>
PART1 = %s<br>
PART2 = %s<br>
PART3 = %s<br>
""" % (binascii.b2a_hex(Case6_4_1.PAYLOAD1), binascii.b2a_hex(Case6_4_1.PAYLOAD2), binascii.b2a_hex(Case6_4_1.PAYLOAD3))

   EXPECTATION = """The first chop is accepted, we expect to timeout on the first wait. The 2nd chop should be rejected immediately (fail fast on UTF-8). If we timeout, we expect the connection is failed at least then, since the complete message payload is not valid UTF-8."""

   def onOpen(self):

      self.expected[Case.OK] = [("timeout", "A")]
      self.expected[Case.NON_STRICT] = [("timeout", "A"), ("timeout", "B")]

      self.expectedClose = {"closedByMe": False,
                            "closeCode": [self.p.CLOSE_STATUS_CODE_INVALID_PAYLOAD],
                            "requireClean": False,
                            "closedByWrongEndpointIsFatal": True}

      self.p.beginMessage()
      self.p.beginMessageFrame(len(self.PAYLOAD))
      self.p.sendMessageFrameData(self.PAYLOAD1)
      self.p.continueLater(1, self.part2, "A")

   def part2(self):
      if self.p.state == WebSocketProtocol.STATE_OPEN:
         self.received.append(("timeout", "A"))
         self.p.sendMessageFrameData(self.PAYLOAD2)
         self.p.continueLater(1, self.part3, "B")

   def part3(self):
      if self.p.state == WebSocketProtocol.STATE_OPEN:
         self.received.append(("timeout", "B"))
         self.p.sendMessageFrameData(self.PAYLOAD3)
         self.p.endMessage()
         self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case6_4_4
# coding=utf-8

###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

import binascii
from case import Case
from case6_4_1 import Case6_4_1
from autobahn.websocket.protocol import WebSocketProtocol


class Case6_4_4(Case6_4_1):

   DESCRIPTION = """Same as Case 6.4.2, but we send message not in 3 frames, but in 3 chops of the same message frame.
<br><br>MESSAGE PARTS:<br>
PART1 = %s<br>
PART2 = %s<br>
PART3 = %s<br>
""" % (binascii.b2a_hex(Case6_4_1.PAYLOAD[:12]), binascii.b2a_hex(Case6_4_1.PAYLOAD[12]), binascii.b2a_hex(Case6_4_1.PAYLOAD3[13:]))

   EXPECTATION = """The first chop is accepted, we expect to timeout on the first wait. The 2nd chop should be rejected immediately (fail fast on UTF-8). If we timeout, we expect the connection is failed at least then, since the complete message payload is not valid UTF-8."""

   def onOpen(self):

      self.expected[Case.OK] = [("timeout", "A")]
      self.expected[Case.NON_STRICT] = [("timeout", "A"), ("timeout", "B")]

      self.expectedClose = {"closedByMe": False,
                            "closeCode": [self.p.CLOSE_STATUS_CODE_INVALID_PAYLOAD],
                            "requireClean": False,
                            "closedByWrongEndpointIsFatal": True}

      self.p.beginMessage()
      self.p.beginMessageFrame(len(self.PAYLOAD))
      self.p.sendMessageFrameData(self.PAYLOAD[:12])
      self.p.continueLater(1, self.part2, "A")

   def part2(self):
      if self.p.state == WebSocketProtocol.STATE_OPEN:
         self.received.append(("timeout", "A"))
         self.p.sendMessageFrameData(self.PAYLOAD[12])
         self.p.continueLater(1, self.part3, "B")

   def part3(self):
      if self.p.state == WebSocketProtocol.STATE_OPEN:
         self.received.append(("timeout", "B"))
         self.p.sendMessageFrameData(self.PAYLOAD[13:])
         self.p.endMessage()
         self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case6_x_x
# coding=utf-8

###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

import binascii
from case import Case
from autobahn.websocket.utf8validator import Utf8Validator


def createUtf8TestSequences():
   """
   Create test sequences for UTF-8 decoder tests from
   http://www.cl.cam.ac.uk/~mgk25/ucs/examples/UTF-8-test.txt
   """

   UTF8_TEST_SEQUENCES = []

   # 1 Some correct UTF-8 text
   vss = '\xce\xba\xe1\xbd\xb9\xcf\x83\xce\xbc\xce\xb5'
   vs = ["Some valid UTF-8 sequences", []]
   vs[1].append((True, 'hello\x24world')) # U+0024
   vs[1].append((True, 'hello\xC2\xA2world')) # U+00A2
   vs[1].append((True, 'hello\xE2\x82\xACworld')) # U+20AC
   vs[1].append((True, 'hello\xF0\xA4\xAD\xA2world')) # U+24B62
   vs[1].append((True, vss))
   UTF8_TEST_SEQUENCES.append(vs)

   # All prefixes of correct UTF-8 text
   vs = ["All prefixes of a valid UTF-8 string that contains multi-byte code points", []]
   v = Utf8Validator()
   for i in xrange(1, len(vss) + 1):
      v.reset()
      res = v.validate(vss[:i])
      vs[1].append((res[0] and res[1], vss[:i]))
   UTF8_TEST_SEQUENCES.append(vs)

   # 2.1 First possible sequence of a certain length
   vs = ["First possible sequence of a certain length", []]
   vs[1].append((True, '\x00'))
   vs[1].append((True, '\xc2\x80'))
   vs[1].append((True, '\xe0\xa0\x80'))
   vs[1].append((True, '\xf0\x90\x80\x80'))
   UTF8_TEST_SEQUENCES.append(vs)

   # the following conform to the UTF-8 integer encoding scheme, but
   # valid UTF-8 only allows for Unicode code points up to U+10FFFF
   vs = ["First possible sequence length 5/6 (invalid codepoints)", []]
   vs[1].append((False, '\xf8\x88\x80\x80\x80'))
   vs[1].append((False, '\xfc\x84\x80\x80\x80\x80'))
   UTF8_TEST_SEQUENCES.append(vs)

   # 2.2 Last possible sequence of a certain length
   vs = ["Last possible sequence of a certain length", []]
   vs[1].append((True, '\x7f'))
   vs[1].append((True, '\xdf\xbf'))
   vs[1].append((True, '\xef\xbf\xbf'))
   vs[1].append((True, '\xf4\x8f\xbf\xbf'))
   UTF8_TEST_SEQUENCES.append(vs)

   # the following conform to the UTF-8 integer encoding scheme, but
   # valid UTF-8 only allows for Unicode code points up to U+10FFFF
   vs = ["Last possible sequence length 4/5/6 (invalid codepoints)", []]
   vs[1].append((False, '\xf7\xbf\xbf\xbf'))
   vs[1].append((False, '\xfb\xbf\xbf\xbf\xbf'))
   vs[1].append((False, '\xfd\xbf\xbf\xbf\xbf\xbf'))
   UTF8_TEST_SEQUENCES.append(vs)

   # 2.3 Other boundary conditions
   vs = ["Other boundary conditions", []]
   vs[1].append((True, '\xed\x9f\xbf'))
   vs[1].append((True, '\xee\x80\x80'))
   vs[1].append((True, '\xef\xbf\xbd'))
   vs[1].append((True, '\xf4\x8f\xbf\xbf'))
   vs[1].append((False, '\xf4\x90\x80\x80'))
   UTF8_TEST_SEQUENCES.append(vs)

   # 3.1  Unexpected continuation bytes
   vs = ["Unexpected continuation bytes", []]
   vs[1].append((False, '\x80'))
   vs[1].append((False, '\xbf'))
   vs[1].append((False, '\x80\xbf'))
   vs[1].append((False, '\x80\xbf\x80'))
   vs[1].append((False, '\x80\xbf\x80\xbf'))
   vs[1].append((False, '\x80\xbf\x80\xbf\x80'))
   vs[1].append((False, '\x80\xbf\x80\xbf\x80\xbf'))
   s = ""
   for i in xrange(0x80, 0xbf):
      s += chr(i)
   vs[1].append((False, s))
   UTF8_TEST_SEQUENCES.append(vs)

   # 3.2  Lonely start characters
   vs = ["Lonely start characters", []]
   m = [(0xc0, 0xdf), (0xe0, 0xef), (0xf0, 0xf7), (0xf8, 0xfb), (0xfc, 0xfd)]
   for mm in m:
      s = ''
      for i in xrange(mm[0], mm[1]):
         s += chr(i)
         s += chr(0x20)
      vs[1].append((False, s))
   UTF8_TEST_SEQUENCES.append(vs)

   # 3.3  Sequences with last continuation byte missing
   vs = ["Sequences with last continuation byte missing", []]
   k = ['\xc0', '\xe0\x80', '\xf0\x80\x80', '\xf8\x80\x80\x80', '\xfc\x80\x80\x80\x80',
        '\xdf', '\xef\xbf', '\xf7\xbf\xbf', '\xfb\xbf\xbf\xbf', '\xfd\xbf\xbf\xbf\xbf']
   for kk in k:
      vs[1].append((False, kk))
   UTF8_TEST_SEQUENCES.append(vs)

   # 3.4  Concatenation of incomplete sequences
   vs = ["Concatenation of incomplete sequences", []]
   vs[1].append((False, ''.join(k)))
   UTF8_TEST_SEQUENCES.append(vs)

   # 3.5  Impossible bytes
   vs = ["Impossible bytes", []]
   vs[1].append((False, '\xfe'))
   vs[1].append((False, '\xff'))
   vs[1].append((False, '\xfe\xfe\xff\xff'))
   UTF8_TEST_SEQUENCES.append(vs)

   # 4.1  Examples of an overlong ASCII character
   vs = ["Examples of an overlong ASCII character", []]
   vs[1].append((False, '\xc0\xaf'))
   vs[1].append((False, '\xe0\x80\xaf'))
   vs[1].append((False, '\xf0\x80\x80\xaf'))
   vs[1].append((False, '\xf8\x80\x80\x80\xaf'))
   vs[1].append((False, '\xfc\x80\x80\x80\x80\xaf'))
   UTF8_TEST_SEQUENCES.append(vs)

   # 4.2  Maximum overlong sequences
   vs = ["Maximum overlong sequences", []]
   vs[1].append((False, '\xc1\xbf'))
   vs[1].append((False, '\xe0\x9f\xbf'))
   vs[1].append((False, '\xf0\x8f\xbf\xbf'))
   vs[1].append((False, '\xf8\x87\xbf\xbf\xbf'))
   vs[1].append((False, '\xfc\x83\xbf\xbf\xbf\xbf'))
   UTF8_TEST_SEQUENCES.append(vs)

   # 4.3  Overlong representation of the NUL character
   vs = ["Overlong representation of the NUL character", []]
   vs[1].append((False, '\xc0\x80'))
   vs[1].append((False, '\xe0\x80\x80'))
   vs[1].append((False, '\xf0\x80\x80\x80'))
   vs[1].append((False, '\xf8\x80\x80\x80\x80'))
   vs[1].append((False, '\xfc\x80\x80\x80\x80\x80'))
   UTF8_TEST_SEQUENCES.append(vs)

   # 5.1 Single UTF-16 surrogates
   vs = ["Single UTF-16 surrogates", []]
   vs[1].append((False, '\xed\xa0\x80'))
   vs[1].append((False, '\xed\xad\xbf'))
   vs[1].append((False, '\xed\xae\x80'))
   vs[1].append((False, '\xed\xaf\xbf'))
   vs[1].append((False, '\xed\xb0\x80'))
   vs[1].append((False, '\xed\xbe\x80'))
   vs[1].append((False, '\xed\xbf\xbf'))
   UTF8_TEST_SEQUENCES.append(vs)

   # 5.2 Paired UTF-16 surrogates
   vs = ["Paired UTF-16 surrogates", []]
   vs[1].append((False, '\xed\xa0\x80\xed\xb0\x80'))
   vs[1].append((False, '\xed\xa0\x80\xed\xbf\xbf'))
   vs[1].append((False, '\xed\xad\xbf\xed\xb0\x80'))
   vs[1].append((False, '\xed\xad\xbf\xed\xbf\xbf'))
   vs[1].append((False, '\xed\xae\x80\xed\xb0\x80'))
   vs[1].append((False, '\xed\xae\x80\xed\xbf\xbf'))
   vs[1].append((False, '\xed\xaf\xbf\xed\xb0\x80'))
   vs[1].append((False, '\xed\xaf\xbf\xed\xbf\xbf'))
   UTF8_TEST_SEQUENCES.append(vs)

   # 5.3 Other illegal code positions
   # Those are non-character code points and valid UTF-8 by RFC 3629
   vs = ["Non-character code points (valid UTF-8)", []]
   # https://bug686312.bugzilla.mozilla.org/attachment.cgi?id=561257
   # non-characters: EF BF [BE-BF]
   vs[1].append((True, '\xef\xbf\xbe'))
   vs[1].append((True, '\xef\xbf\xbf'))
   # non-characters: F[0-7] [89AB]F BF [BE-BF]
   for z1 in ['\xf0', '\xf1', '\xf2', '\xf3', '\xf4']:
      for z2 in ['\x8f', '\x9f', '\xaf', '\xbf']:
         if not (z1 == '\xf4' and z2 != '\x8f'): # those encode codepoints >U+10FFFF
            for z3 in ['\xbe', '\xbf']:
               zz = z1 + z2 + '\xbf' + z3
               if zz not in ['\xf0\x8f\xbf\xbe', '\xf0\x8f\xbf\xbf']: # filter overlong sequences
                  vs[1].append((True, zz))
   UTF8_TEST_SEQUENCES.append(vs)

   # Unicode "specials", such as replacement char etc
   # http://en.wikipedia.org/wiki/Specials_%28Unicode_block%29
   vs = ["Unicode specials (i.e. replacement char)", []]
   vs[1].append((True, '\xef\xbf\xb9'))
   vs[1].append((True, '\xef\xbf\xba'))
   vs[1].append((True, '\xef\xbf\xbb'))
   vs[1].append((True, '\xef\xbf\xbc'))
   vs[1].append((True, '\xef\xbf\xbd')) # replacement char
   vs[1].append((True, '\xef\xbf\xbe'))
   vs[1].append((True, '\xef\xbf\xbf'))
   UTF8_TEST_SEQUENCES.append(vs)

   return UTF8_TEST_SEQUENCES


def createValidUtf8TestSequences():
   """
   Generate some exotic, but valid UTF8 test strings.
   """
   VALID_UTF8_TEST_SEQUENCES = []
   for test in createUtf8TestSequences():
      valids = [x[1] for x in test[1] if x[0]]
      if len(valids) > 0:
         VALID_UTF8_TEST_SEQUENCES.append([test[0], valids])
   return VALID_UTF8_TEST_SEQUENCES


def test_utf8(validator):
   """
   These tests verify the UTF-8 decoder/validator on the various test cases from
   http://www.cl.cam.ac.uk/~mgk25/ucs/examples/UTF-8-test.txt
   """
   vs = []
   for k in createUtf8TestSequences():
      vs.extend(k[1])

   # All Unicode code points
   for i in xrange(0, 0xffff): # should by 0x10ffff, but non-wide Python build is limited to 16-bits
      if i < 0xD800 or i > 0xDFFF: # filter surrogate code points, which are disallowed to encode in UTF-8
         vs.append((True, unichr(i).encode("utf-8")))

   # 5.1 Single UTF-16 surrogates
   for i in xrange(0xD800, 0xDBFF): # high-surrogate
      ss = unichr(i).encode("utf-8")
      vs.append((False, ss))
   for i in xrange(0xDC00, 0xDFFF): # low-surrogate
      ss = unichr(i).encode("utf-8")
      vs.append((False, ss))

   # 5.2 Paired UTF-16 surrogates
   for i in xrange(0xD800, 0xDBFF): # high-surrogate
      for j in xrange(0xDC00, 0xDFFF): # low-surrogate
         ss1 = unichr(i).encode("utf-8")
         ss2 = unichr(j).encode("utf-8")
         vs.append((False, ss1 + ss2))
         vs.append((False, ss2 + ss1))

   print "testing validator %s on %d UTF8 sequences" % (validator, len(vs))

   # now test and assert ..
   for s in vs:
      validator.reset()
      r = validator.validate(s[1])
      res = r[0] and r[1] # no UTF-8 decode error and everything consumed
      assert res == s[0]

   print "ok, validator works!"
   print


def test_utf8_incremental(validator, withPositions = True):
   """
   These tests verify that the UTF-8 decoder/validator can operate incrementally.
   """
   if withPositions:
      k = 4
      print "testing validator %s on incremental detection with positions" % validator
   else:
      k = 2
      print "testing validator %s on incremental detection without positions" % validator

   validator.reset()
   assert (True, True, 15, 15)[:k] == validator.validate("µ@ßöäüàá")[:k]

   validator.reset()
   assert (False, False, 0, 0)[:k] == validator.validate("\xF5")[:k]

   ## the following 3 all fail on eating byte 7 (0xA0)
   validator.reset()
   assert (True, True, 6, 6)[:k] == validator.validate("\x65\x64\x69\x74\x65\x64")[:k]
   assert (False, False, 1, 7)[:k] == validator.validate("\xED\xA0\x80")[:k]

   validator.reset()
   assert (True, True, 4, 4)[:k] == validator.validate("\x65\x64\x69\x74")[:k]
   assert (False, False, 3, 7)[:k] == validator.validate("\x65\x64\xED\xA0\x80")[:k]

   validator.reset()
   assert (True, False, 7, 7)[:k] == validator.validate("\x65\x64\x69\x74\x65\x64\xED")[:k]
   assert (False, False, 0, 7)[:k] == validator.validate("\xA0\x80")[:k]

   print "ok, validator works!"
   print


Case6_X_X = []
Case6_X_X_CaseSubCategories = {}


def __init__(self, protocol):
   Case.__init__(self, protocol)

def onOpen(self):

   if self.isValid:
      self.expected[Case.OK] = [("message", self.PAYLOAD, False)]
      self.expectedClose = {"closedByMe": True,
                            "closeCode": [self.p.CLOSE_STATUS_CODE_NORMAL],
                            "requireClean": True}
   else:
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe": False,
                            "closeCode": [self.p.CLOSE_STATUS_CODE_INVALID_PAYLOAD],
                            "requireClean": False,
                            "closedByWrongEndpointIsFatal": True}

   self.p.sendMessage(self.PAYLOAD, False)
   self.p.killAfter(0.5)


i = 5
for t in createUtf8TestSequences():
   j = 1
   Case6_X_X_CaseSubCategories["6.%d" % i] = t[0]
   for p in t[1]:
      if p[0]:
         desc = "Send a text message with payload which is valid UTF-8 in one fragment."
         exp = "The message is echo'ed back to us."
      else:
         desc = "Send a text message with payload which is not valid UTF-8 in one fragment."
         exp = "The connection is failed immediately, since the payload is not valid UTF-8."
      C = type("Case6_%d_%d" % (i, j),
                (object, Case, ),
                {"PAYLOAD": p[1],
                 "isValid": p[0],
                 "DESCRIPTION": """%s<br><br>Payload: 0x%s""" % (desc, binascii.b2a_hex(p[1])),
                 "EXPECTATION": """%s""" % exp,
                 "__init__": __init__,
                 "onOpen": onOpen})
      Case6_X_X.append(C)
      j += 1
   i += 1


import binascii
import array

def encode(c):
   """
   Encode Unicode code point into UTF-8 byte string.
   """
   if c <= 0x7F:
      b1 = c>>0  & 0x7F | 0x00
      return array.array('B', [b1]).tostring()
   elif c <= 0x07FF:
      b1 = c>>6  & 0x1F | 0xC0
      b2 = c>>0  & 0x3F | 0x80
      return array.array('B', [b1, b2]).tostring()
   elif c <= 0xFFFF:
      b1 = c>>12 & 0x0F | 0xE0
      b2 = c>>6  & 0x3F | 0x80
      b3 = c>>0  & 0x3F | 0x80
      return array.array('B', [b1, b2, b3]).tostring()
   elif c <= 0x1FFFFF:
      b1 = c>>18 & 0x07 | 0xF0
      b2 = c>>12 & 0x3F | 0x80
      b3 = c>>6  & 0x3F | 0x80
      b4 = c>>0  & 0x3F | 0x80
      return array.array('B', [b1, b2, b3, b4]).tostring()
   elif c <= 0x3FFFFFF:
      b1 = c>>24 & 0x03 | 0xF8
      b2 = c>>18 & 0x3F | 0x80
      b3 = c>>12 & 0x3F | 0x80
      b4 = c>>6  & 0x3F | 0x80
      b5 = c>>0  & 0x3F | 0x80
      return array.array('B', [b1, b2, b3, b4, b5]).tostring()
   elif c <= 0x7FFFFFFF:
      b1 = c>>30 & 0x01 | 0xFC
      b2 = c>>24 & 0x3F | 0x80
      b3 = c>>18 & 0x3F | 0x80
      b4 = c>>12 & 0x3F | 0x80
      b5 = c>>6  & 0x3F | 0x80
      b6 = c>>0  & 0x3F | 0x80
      return array.array('B', [b1, b2, b3, b4, b5, b6]).tostring()
   else:
      raise Exception("invalid unicode codepoint")


def test_encode(testpoints):
   """
   Compare Python UTF-8 encoding with adhoc implementation.
   """
   for tp in testpoints:
      if tp[0]:
         print binascii.b2a_hex(encode(tp[0]))
      else:
         print tp[0]
      if tp[1]:
         print binascii.b2a_hex(tp[1].encode("utf8"))
      else:
         print tp[1]


if __name__ == '__main__':
   """
   Run unit tests.
   """

   validator = Utf8Validator()
   test_utf8(validator)
   test_utf8_incremental(validator, withPositions = True)

   #TESTPOINTS = [(0xfffb, u'\ufffb'),
   #              # (0xd807, u'\ud807'), # Jython does not like this
   #              (0x11000, None),
   #              (0x110000, None)]
   #test_encode(TESTPOINTS)

   #from pprint import pprint
   #pprint(createValidUtf8TestSequences())

########NEW FILE########
__FILENAME__ = case7_13_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case


class Case7_13_1(Case):

   DESCRIPTION = """Send close with close code 5000"""

   EXPECTATION = """Actual events are undefined by the spec."""
   
   def init(self):
      self.code = 5000
      self.suppressClose = True
   
   def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)
      
      self.passed = True
      self.behavior = Case.INFORMATIONAL
      self.behaviorClose = Case.INFORMATIONAL
      self.result = "Actual events are undefined by the spec."
   
   def onOpen(self):
      self.payload = '\xce\xba\xe1\xbd\xb9\xcf\x83\xce\xbc\xce\xb5\xed\xa0\x80\x65\x64\x69\x74\x65\x64'
      self.expected[Case.OK] = []      
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL,self.code,self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendCloseFrame(self.code)
      self.p.killAfter(1)

      

########NEW FILE########
__FILENAME__ = case7_13_2
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case


class Case7_13_2(Case):

   DESCRIPTION = """Send close with close code 65536"""

   EXPECTATION = """Actual events are undefined by the spec."""
   
   def init(self):
      self.code = 65535
      self.suppressClose = True
   
   def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)
      
      self.passed = True
      self.behavior = Case.INFORMATIONAL
      self.behaviorClose = Case.INFORMATIONAL
      self.result = "Actual events are undefined by the spec."
   
   def onOpen(self):
      self.payload = '\xce\xba\xe1\xbd\xb9\xcf\x83\xce\xbc\xce\xb5\xed\xa0\x80\x65\x64\x69\x74\x65\x64'
      self.expected[Case.OK] = []      
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL,self.code,self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendCloseFrame(self.code)
      self.p.killAfter(1)

      

########NEW FILE########
__FILENAME__ = case7_1_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case7_1_1(Case):

   DESCRIPTION = """Send a message followed by a close frame"""

   EXPECTATION = """Echoed message followed by clean close with normal code."""

   def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)
      
      if self.behaviorClose == Case.WRONG_CODE:
         self.behavior = Case.FAILED
         self.passed = False
         self.result = self.resultClose

   def onOpen(self):
      payload = "Hello World!"
      self.expected[Case.OK] = [("message", payload, False)]      
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 1, payload = payload)
      #self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL);
      #self.p.sendFrame(opcode = 1, payload = payload)
      self.p.killAfter(1)

      

########NEW FILE########
__FILENAME__ = case7_1_2
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case7_1_2(Case):

   DESCRIPTION = """Send two close frames"""

   EXPECTATION = """Clean close with normal code. Second close frame ignored."""
   
   def init(self):
      self.suppressClose = True
   
   def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)
      
      if self.behaviorClose == Case.WRONG_CODE:
         self.behavior = Case.FAILED
         self.passed = False
         self.result = self.resultClose
   
   def onOpen(self):
      payload = "Hello World!"
      self.expected[Case.OK] = []      
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)
      self.p.sendFrame(opcode = 8)
      self.p.killAfter(1)

      

########NEW FILE########
__FILENAME__ = case7_1_3
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case7_1_3(Case):

   DESCRIPTION = """Send a ping after close message"""

   EXPECTATION = """Clean close with normal code, no pong."""
   
   def init(self):
      self.suppressClose = True

   def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)
      
      if self.behaviorClose == Case.WRONG_CODE:
         self.behavior = Case.FAILED
         self.passed = False
         self.result = self.resultClose

   def onOpen(self):
      payload = "Hello World!"
      self.expected[Case.OK] = []      
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      #self.p.sendFrame(opcode = 1, payload = payload)
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)
      self.p.sendFrame(opcode = 9)
      self.p.killAfter(1)

      

########NEW FILE########
__FILENAME__ = case7_1_4
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case7_1_4(Case):

   DESCRIPTION = """Send text message after sending a close frame."""

   EXPECTATION = """Clean close with normal code. Text message ignored."""
   
   def init(self):
      self.suppressClose = True

   def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)
      
      if self.behaviorClose == Case.WRONG_CODE:
         self.behavior = Case.FAILED
         self.passed = False
         self.result = self.resultClose

   def onOpen(self):
      payload = "Hello World!"
      self.expected[Case.OK] = []      
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)
      self.p.sendFrame(opcode = 1, payload = payload)
      self.p.killAfter(1)

      

########NEW FILE########
__FILENAME__ = case7_1_5
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case7_1_5(Case):

   DESCRIPTION = """Send message fragment1 followed by close then fragment"""

   EXPECTATION = """Clean close with normal code."""
   
   def init(self):
      self.suppressClose = True

   def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)
      
      if self.behaviorClose == Case.WRONG_CODE:
         self.behavior = Case.FAILED
         self.passed = False
         self.result = self.resultClose

   def onOpen(self):
      fragments = ["fragment1", "fragment2"]
      self.expected[Case.OK] = []      
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 1, fin = False, payload = fragments[0])
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)
      self.p.sendFrame(opcode = 0, fin = True, payload = fragments[1])
      self.p.killAfter(1)

      

########NEW FILE########
__FILENAME__ = case7_1_6
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case7_1_6(Case):

   DESCRIPTION = """Send 256K message followed by close then a ping"""

   EXPECTATION = """Case outcome depends on implimentation defined close behavior. Message and close frame are sent back to back. If the close frame is processed before the text message write is complete (as can happen in asyncronous processing models) the close frame is processed first and the text message may not be recieved or may only be partially recieved."""
   
   def init(self):
      self.suppressClose = True
      self.DATALEN = 256 * 2**10
      self.PAYLOAD = "BAsd7&jh23"

   def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)
      
      self.passed = True
      
      
      if self.behavior == Case.OK:
         self.result = "Text message was processed before close."
      elif self.behavior == Case.NON_STRICT:
         self.result = "Close was processed before text message could be returned."
      
      self.behavior = Case.INFORMATIONAL
      self.behaviorClose = Case.INFORMATIONAL
      
   def onOpen(self):
      payload = "Hello World!"
      self.expected[Case.OK] = [("message", payload, False)] 
      self.expected[Case.NON_STRICT] = []      
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendFrame(opcode = 1, payload = self.PAYLOAD, payload_len = self.DATALEN)
      self.p.sendFrame(opcode = 1, payload = payload)
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)
      self.p.sendFrame(opcode = 9)
      self.p.killAfter(1)

      

########NEW FILE########
__FILENAME__ = case7_3_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case7_3_1(Case):

   DESCRIPTION = """Send a close frame with payload length 0 (no close code, no close reason)"""

   EXPECTATION = """Clean close with normal code."""

   def init(self):
      self.suppressClose = True

   def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)
      
      if self.behaviorClose == Case.WRONG_CODE:
         self.behavior = Case.FAILED
         self.passed = False
         self.result = self.resultClose

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendCloseFrame()
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case7_3_2
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case7_3_2(Case):

   DESCRIPTION = """Send a close frame with payload length 1"""

   EXPECTATION = """Clean close with protocol error or drop TCP."""

   def init(self):
      self.suppressClose = True

   def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)

      if self.behaviorClose == Case.WRONG_CODE:
         self.behavior = Case.FAILED
         self.passed = False
         self.result = self.resultClose

   def onOpen(self):
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendCloseFrame(reasonUtf8 = "a")
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case7_3_3
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case7_3_3(Case):

   DESCRIPTION = """Send a close frame with payload length 2 (regular close with a code)"""

   EXPECTATION = """Clean close with normal code."""
   
   def init(self):
      self.suppressClose = True

   def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)
      
      if self.behaviorClose == Case.WRONG_CODE:
         self.behavior = Case.FAILED
         self.passed = False
         self.result = self.resultClose

   def onOpen(self):
      self.expected[Case.OK] = []      
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)
      self.p.killAfter(1)

      

########NEW FILE########
__FILENAME__ = case7_3_4
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case7_3_4(Case):

   DESCRIPTION = """Send a close frame with close code and close reason"""

   EXPECTATION = """Clean close with normal code."""

   def init(self):
      self.suppressClose = True
      
   def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)
      
      if self.behaviorClose == Case.WRONG_CODE:
         self.behavior = Case.FAILED
         self.passed = False
         self.result = self.resultClose 
   def onOpen(self):
      self.payload = "Hello World!"
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL,self.payload)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case7_3_5
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case7_3_5(Case):

   DESCRIPTION = """Send a close frame with close code and close reason of maximum length (123)"""

   EXPECTATION = """Clean close with normal code."""

   def init(self):
      self.suppressClose = True
      
   def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)
      
      if self.behaviorClose == Case.WRONG_CODE:
         self.behavior = Case.FAILED
         self.passed = False
         self.result = self.resultClose 
         
   def onOpen(self):
      self.payload = "*" * 123
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL,self.payload)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case7_3_6
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case7_3_6(Case):

   DESCRIPTION = """Send a close frame with close code and close reason which is too long (124) - total frame payload 126 octets"""

   EXPECTATION = """Clean close with protocol error code or dropped TCP connection."""

   def init(self):
      self.suppressClose = True

   def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)
      
      if self.behaviorClose == Case.WRONG_CODE:
         self.behavior = Case.FAILED
         self.passed = False
         self.result = self.resultClose

   def onOpen(self):
      self.payload = "*" * 124
      self.expected[Case.OK] = []
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
      self.p.sendCloseFrame(self.p.CLOSE_STATUS_CODE_NORMAL, reasonUtf8 = self.payload)
      self.p.killAfter(1)

########NEW FILE########
__FILENAME__ = case7_5_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case
import binascii

class Case7_5_1(Case):

   DESCRIPTION = """Send a close frame with invalid UTF8 payload"""

   EXPECTATION = """Clean close with protocol error or invalid utf8 code or dropped TCP."""
   
   def init(self):
      self.suppressClose = True
   
   def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)
      
      if self.behaviorClose == Case.WRONG_CODE:
         self.behavior = Case.FAILED
         self.passed = False
         self.result = self.resultClose

      ## the close reason we sent was invalid UTF8, so we
      ## convert to HEX representation for later case reporting
      self.p.localCloseReason = binascii.b2a_hex(self.p.localCloseReason)

   def onOpen(self):
      self.payload = '\xce\xba\xe1\xbd\xb9\xcf\x83\xce\xbc\xce\xb5\xed\xa0\x80\x65\x64\x69\x74\x65\x64'
      self.expected[Case.OK] = []      
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR,self.p.CLOSE_STATUS_CODE_INVALID_PAYLOAD],"requireClean":False}
      #self.p.sendFrame(opcode = 8,payload = self.payload)
      self.p.sendCloseFrame(self.p.CLOSE_STATUS_CODE_NORMAL, reasonUtf8 = self.payload)
      self.p.killAfter(1)

      

########NEW FILE########
__FILENAME__ = case7_7_X
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

## list of some valid close codes
tests = [1000,1001,1002,1003,1007,1008,1009,1010,1011,3000,3999,4000,4999]

Case7_7_X = []

def __init__(self, protocol):
   Case.__init__(self, protocol)

def onOpen(self):
   self.expected[Case.OK] = []
   self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL,self.CLOSE_CODE],"requireClean":True}
   self.p.sendCloseFrame(self.CLOSE_CODE)
   self.p.killAfter(1)

def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)

      if self.behaviorClose == Case.WRONG_CODE:
         self.behavior = Case.FAILED
         self.passed = False
         self.result = self.resultClose

i = 1
for s in tests:
   DESCRIPTION = """Send close with valid close code %d""" % s
   EXPECTATION = """Clean close with normal or echoed code"""
   C = type("Case7_7_%d" % i,
         (object, Case, ),
         {"CLOSE_CODE": s,
          "DESCRIPTION": """%s""" % DESCRIPTION,
          "EXPECTATION": """%s""" % EXPECTATION,
          "__init__": __init__,
          "onOpen": onOpen,
          "onConnectionLost": onConnectionLost,
          })
   Case7_7_X.append(C)
   i += 1

########NEW FILE########
__FILENAME__ = case7_9_X
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

## list of some invalid close codes
tests = [0,999,1004,1005,1006,1012,1013,1014,1015,1016,1100,2000,2999]

Case7_9_X = []

def __init__(self, protocol):
   Case.__init__(self, protocol)

def onConnectionLost(self, failedByMe):
      Case.onConnectionLost(self, failedByMe)

      if self.behaviorClose == Case.WRONG_CODE:
         self.behavior = Case.FAILED
         self.passed = False
         self.result = self.resultClose

def onOpen(self):
   self.expected[Case.OK] = []
   self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_PROTOCOL_ERROR],"requireClean":False}
   self.p.sendCloseFrame(self.CLOSE_CODE)
   self.p.killAfter(1)

i = 1
for s in tests:
   DESCRIPTION = """Send close with invalid close code %d""" % s
   EXPECTATION = """Clean close with protocol error code or drop TCP"""
   C = type("Case7_9_%d" % i,
            (object, Case, ),
            {"CLOSE_CODE": s,
             "DESCRIPTION": """%s""" % DESCRIPTION,
             "EXPECTATION": """%s""" % EXPECTATION,
             "__init__": __init__,
             "onOpen": onOpen,
             "onConnectionLost": onConnectionLost,
             })
   Case7_9_X.append(C)
   i += 1

########NEW FILE########
__FILENAME__ = case9_1_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case9_1_1(Case):

   DESCRIPTION = """Send text message message with payload of length 64 * 2**10 (64k)."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def init(self):
      self.DATALEN = 64 * 2**10
      self.PAYLOAD = "BAsd7&jh23"
      self.WAITSECS = 10
      self.reportTime = True

   def onOpen(self):
      self.p.createWirelog = False
      self.behavior = Case.FAILED

      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}

      self.result = "Did not receive message within %d seconds." % self.WAITSECS
      self.p.sendFrame(opcode = 1, payload = self.PAYLOAD, payload_len = self.DATALEN)
      self.p.closeAfter(self.WAITSECS)

   def onMessage(self, msg, binary):
      if binary:
         self.result = "Expected text message with payload, but got binary."
      else:
         if len(msg) != self.DATALEN:
            self.result = "Expected text message with payload of length %d, but got %d." % (self.DATALEN, len(msg))
         else:
            ## FIXME : check actual content
            ##
            self.behavior = Case.OK
            self.result = "Received text message of length %d." % len(msg)
      self.p.createWirelog = True
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)

########NEW FILE########
__FILENAME__ = case9_1_2
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_1_1 import *

class Case9_1_2(Case9_1_1):

   DESCRIPTION = """Send text message message with payload of length 256 * 2**10 (256k)."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def init(self):
      self.DATALEN = 256 * 2**10
      self.PAYLOAD = "BAsd7&jh23"
      self.WAITSECS = 10
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_1_3
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_1_1 import *

class Case9_1_3(Case9_1_1):

   DESCRIPTION = """Send text message message with payload of length 1 * 2**20 (1M)."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def init(self):
      self.DATALEN = 1 * 2**20
      self.PAYLOAD = "BAsd7&jh23"
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_1_4
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_1_1 import *

class Case9_1_4(Case9_1_1):

   DESCRIPTION = """Send text message message with payload of length 4 * 2**20 (4M)."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.PAYLOAD = "BAsd7&jh23"
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_1_5
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_1_1 import *

class Case9_1_5(Case9_1_1):

   DESCRIPTION = """Send text message message with payload of length 8 * 2**20 (8M)."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def init(self):
      self.DATALEN = 8 * 2**20
      self.PAYLOAD = "BAsd7&jh23"
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_1_6
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_1_1 import *

class Case9_1_6(Case9_1_1):

   DESCRIPTION = """Send text message message with payload of length 16 * 2**20 (16M)."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def init(self):
      self.DATALEN = 16 * 2**20
      self.PAYLOAD = "BAsd7&jh23"
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_2_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case9_2_1(Case):

   DESCRIPTION = """Send binary message message with payload of length 64 * 2**10 (64k)."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent)."""

   def init(self):
      self.DATALEN = 64 * 2**10
      self.PAYLOAD = "\x00\xfe\x23\xfa\xf0"
      self.WAITSECS = 10
      self.reportTime = True

   def onOpen(self):
      self.p.createWirelog = False
      self.behavior = Case.FAILED
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.result = "Did not receive message within %d seconds." % self.WAITSECS
      self.p.sendFrame(opcode = 2, payload = self.PAYLOAD, payload_len = self.DATALEN)
      self.p.closeAfter(self.WAITSECS)

   def onMessage(self, msg, binary):
      if not binary:
         self.result = "Expected binary message with payload, but got text."
      else:
         if len(msg) != self.DATALEN:
            self.result = "Expected binary message with payload of length %d, but got %d." % (self.DATALEN, len(msg))
         else:
            ## FIXME : check actual content
            ##
            self.behavior = Case.OK
            self.result = "Received binary message of length %d." % len(msg)
      self.p.createWirelog = True
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)



########NEW FILE########
__FILENAME__ = case9_2_2
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_2_1 import *

class Case9_2_2(Case9_2_1):

   DESCRIPTION = """Send binary message message with payload of length 256 * 2**10 (256k)."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent)."""

   def init(self):
      self.DATALEN = 256 * 2**10
      self.PAYLOAD = "\x00\xfe\x23\xfa\xf0"
      self.WAITSECS = 10
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_2_3
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_2_1 import *

class Case9_2_3(Case9_2_1):

   DESCRIPTION = """Send binary message message with payload of length 1 * 2**20 (1M)."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent)."""

   def init(self):
      self.DATALEN = 1 * 2**20
      self.PAYLOAD = "\x00\xfe\x23\xfa\xf0"
      self.WAITSECS = 10
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_2_4
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_2_1 import *

class Case9_2_4(Case9_2_1):

   DESCRIPTION = """Send binary message message with payload of length 4 * 2**20 (4M)."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.PAYLOAD = "\x00\xfe\x23\xfa\xf0"
      self.WAITSECS = 10
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_2_5
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_2_1 import *

class Case9_2_5(Case9_2_1):

   DESCRIPTION = """Send binary message message with payload of length 8 * 2**20 (16M)."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent)."""

   def init(self):
      self.DATALEN = 8 * 2**20
      self.PAYLOAD = "\x00\xfe\x23\xfa\xf0"
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_2_6
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_2_1 import *

class Case9_2_6(Case9_2_1):

   DESCRIPTION = """Send binary message message with payload of length 16 * 2**20 (16M)."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent)."""

   def init(self):
      self.DATALEN = 16 * 2**20
      self.PAYLOAD = "\x00\xfe\x23\xfa\xf0"
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_3_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case9_3_1(Case):

   DESCRIPTION = """Send fragmented text message message with message payload of length 4 * 2**20 (4M). Sent out in fragments of 64."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 64
      self.PAYLOAD = "*" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

   def onOpen(self):
      self.p.createWirelog = False
      self.behavior = Case.FAILED
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.result = "Did not receive message within %d seconds." % self.WAITSECS
      self.p.sendMessage(payload = self.PAYLOAD, isBinary = False, fragmentSize = self.FRAGSIZE)
      self.p.closeAfter(self.WAITSECS)

   def onMessage(self, payload, isBinary):
      if isBinary:
         self.result = "Expected text message with payload, but got binary."
      else:
         if len(payload) != self.DATALEN:
            self.result = "Expected text message with payload of length %d, but got %d." % (self.DATALEN, len(payload))
         else:
            ## FIXME : check actual content
            ##
            self.behavior = Case.OK
            self.result = "Received text message of length %d." % len(payload)
      self.p.createWirelog = True
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)



########NEW FILE########
__FILENAME__ = case9_3_2
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_3_1 import Case9_3_1

class Case9_3_2(Case9_3_1):

   DESCRIPTION = """Send fragmented text message message with message payload of length 4 * 2**20 (4M). Sent out in fragments of 256."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 256
      self.PAYLOAD = "*" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_3_3
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_3_1 import Case9_3_1

class Case9_3_3(Case9_3_1):

   DESCRIPTION = """Send fragmented text message message with message payload of length 4 * 2**20 (4M). Sent out in fragments of 1k."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 1 * 2**10
      self.PAYLOAD = "*" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_3_4
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_3_1 import Case9_3_1

class Case9_3_4(Case9_3_1):

   DESCRIPTION = """Send fragmented text message message with message payload of length 4 * 2**20 (4M). Sent out in fragments of 4k."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 4 * 2**10
      self.PAYLOAD = "*" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_3_5
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_3_1 import Case9_3_1

class Case9_3_5(Case9_3_1):

   DESCRIPTION = """Send fragmented text message message with message payload of length 4 * 2**20 (4M). Sent out in fragments of 16k."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 16 * 2**10
      self.PAYLOAD = "*" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_3_6
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_3_1 import Case9_3_1

class Case9_3_6(Case9_3_1):

   DESCRIPTION = """Send fragmented text message message with message payload of length 4 * 2**20 (4M). Sent out in fragments of 64k."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 64 * 2**10
      self.PAYLOAD = "*" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_3_7
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_3_1 import Case9_3_1

class Case9_3_7(Case9_3_1):

   DESCRIPTION = """Send fragmented text message message with message payload of length 4 * 2**20 (4M). Sent out in fragments of 256k."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 256 * 2**10
      self.PAYLOAD = "*" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_3_8
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_3_1 import Case9_3_1

class Case9_3_8(Case9_3_1):

   DESCRIPTION = """Send fragmented text message message with message payload of length 4 * 2**20 (4M). Sent out in fragments of 1M."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 1 * 2**20
      self.PAYLOAD = "*" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_3_9
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_3_1 import Case9_3_1

class Case9_3_9(Case9_3_1):

   DESCRIPTION = """Send fragmented text message message with message payload of length 4 * 2**20 (8M). Sent out in fragments of 4M."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 4 * 2**20
      self.PAYLOAD = "*" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_4_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case9_4_1(Case):

   DESCRIPTION = """Send fragmented binary message message with message payload of length 4 * 2**20 (4M). Sent out in fragments of 64."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 64
      self.PAYLOAD = "\xfe" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

   def onOpen(self):
      self.p.createWirelog = False
      self.behavior = Case.FAILED
      self.result = "Did not receive message within %d seconds." % self.WAITSECS
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.p.sendMessage(payload = self.PAYLOAD, isBinary = True, fragmentSize = self.FRAGSIZE)
      self.p.closeAfter(self.WAITSECS)

   def onMessage(self, payload, isBinary):
      if not isBinary:
         self.result = "Expected binary message with payload, but got binary."
      else:
         if len(payload) != self.DATALEN:
            self.result = "Expected binary message with payload of length %d, but got %d." % (self.DATALEN, len(payload))
         else:
            ## FIXME : check actual content
            ##
            self.behavior = Case.OK
            self.result = "Received binary message of length %d." % len(payload)
      self.p.createWirelog = True
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)


########NEW FILE########
__FILENAME__ = case9_4_2
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_4_1 import Case9_4_1

class Case9_4_2(Case9_4_1):

   DESCRIPTION = """Send fragmented binary message message with message payload of length 4 * 2**20 (4M). Sent out in fragments of 256."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 256
      self.PAYLOAD = "*" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_4_3
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_4_1 import Case9_4_1

class Case9_4_3(Case9_4_1):

   DESCRIPTION = """Send fragmented binary message message with message payload of length 4 * 2**20 (4M). Sent out in fragments of 1k."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 1 * 2**10
      self.PAYLOAD = "*" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_4_4
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_4_1 import Case9_4_1

class Case9_4_4(Case9_4_1):

   DESCRIPTION = """Send fragmented binary message message with message payload of length 4 * 2**20 (4M). Sent out in fragments of 4k."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 4 * 2**10
      self.PAYLOAD = "*" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_4_5
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_4_1 import Case9_4_1

class Case9_4_5(Case9_4_1):

   DESCRIPTION = """Send fragmented binary message message with message payload of length 4 * 2**20 (4M). Sent out in fragments of 16k."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 16 * 2**10
      self.PAYLOAD = "*" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_4_6
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_4_1 import Case9_4_1

class Case9_4_6(Case9_4_1):

   DESCRIPTION = """Send fragmented binary message message with message payload of length 4 * 2**20 (4M). Sent out in fragments of 64k."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 64 * 2**10
      self.PAYLOAD = "*" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_4_7
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_4_1 import Case9_4_1

class Case9_4_7(Case9_4_1):

   DESCRIPTION = """Send fragmented binary message message with message payload of length 4 * 2**20 (4M). Sent out in fragments of 256k."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 256 * 2**10
      self.PAYLOAD = "*" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_4_8
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_4_1 import Case9_4_1

class Case9_4_8(Case9_4_1):

   DESCRIPTION = """Send fragmented binary message message with message payload of length 4 * 2**20 (4M). Sent out in fragments of 1M."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 1 * 2**20
      self.PAYLOAD = "*" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_4_9
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_4_1 import Case9_4_1

class Case9_4_9(Case9_4_1):

   DESCRIPTION = """Send fragmented binary message message with message payload of length 4 * 2**20 (4M). Sent out in fragments of 4M."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent)."""

   def init(self):
      self.DATALEN = 4 * 2**20
      self.FRAGSIZE = 4 * 2**20
      self.PAYLOAD = "*" * self.DATALEN
      self.WAITSECS = 100
      self.reportTime = True

########NEW FILE########
__FILENAME__ = case9_5_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case9_5_1(Case):

   DESCRIPTION = """Send text message message with payload of length 1 * 2**20 (1M). Sent out data in chops of 64 octets."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def setChopSize(self):
      self.chopsize = 64

   def init(self):
      self.DATALEN = 1 * 2**20
      self.PAYLOAD = "BAsd7&jh23"
      self.WAITSECS = 1000
      self.reportTime = True
      self.setChopSize()

   def onOpen(self):
      self.p.createWirelog = False
      self.behavior = Case.FAILED
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.result = "Did not receive message within %d seconds." % self.WAITSECS
      self.p.sendFrame(opcode = 1, payload = self.PAYLOAD, payload_len = self.DATALEN, chopsize = self.chopsize)
      self.p.closeAfter(self.WAITSECS)

   def onMessage(self, msg, binary):
      if binary:
         self.result = "Expected text message with payload, but got binary."
      else:
         if len(msg) != self.DATALEN:
            self.result = "Expected text message with payload of length %d, but got %d." % (self.DATALEN, len(msg))
         else:
            ## FIXME : check actual content
            ##
            self.behavior = Case.OK
            self.result = "Received text message of length %d." % len(msg)
      self.p.createWirelog = True
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)

########NEW FILE########
__FILENAME__ = case9_5_2
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_5_1 import Case9_5_1

class Case9_5_2(Case9_5_1):

   DESCRIPTION = """Send text message message with payload of length 1 * 2**20 (1M). Sent out data in chops of 128 octets."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def setChopSize(self):
      self.chopsize = 128

########NEW FILE########
__FILENAME__ = case9_5_3
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_5_1 import Case9_5_1

class Case9_5_3(Case9_5_1):

   DESCRIPTION = """Send text message message with payload of length 1 * 2**20 (1M). Sent out data in chops of 256 octets."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def setChopSize(self):
      self.chopsize = 256

########NEW FILE########
__FILENAME__ = case9_5_4
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_5_1 import Case9_5_1

class Case9_5_4(Case9_5_1):

   DESCRIPTION = """Send text message message with payload of length 1 * 2**20 (1M). Sent out data in chops of 512 octets."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def setChopSize(self):
      self.chopsize = 512

########NEW FILE########
__FILENAME__ = case9_5_5
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_5_1 import Case9_5_1

class Case9_5_5(Case9_5_1):

   DESCRIPTION = """Send text message message with payload of length 1 * 2**20 (1M). Sent out data in chops of 1024 octets."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def setChopSize(self):
      self.chopsize = 1024

########NEW FILE########
__FILENAME__ = case9_5_6
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_5_1 import Case9_5_1

class Case9_5_6(Case9_5_1):

   DESCRIPTION = """Send text message message with payload of length 1 * 2**20 (1M). Sent out data in chops of 2048 octets."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def setChopSize(self):
      self.chopsize = 2048

########NEW FILE########
__FILENAME__ = case9_6_1
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

class Case9_6_1(Case):

   DESCRIPTION = """Send binary message message with payload of length 1 * 2**20 (1M). Sent out data in chops of 64 octets."""

   EXPECTATION = """Receive echo'ed binary message (with payload as sent)."""

   def setChopSize(self):
      self.chopsize = 64

   def init(self):
      self.DATALEN = 1 * 2**20
      self.PAYLOAD = "\x00\xfe\x23\xfa\xf0"
      self.WAITSECS = 1000
      self.reportTime = True
      self.setChopSize()

   def onOpen(self):
      self.p.createWirelog = False
      self.behavior = Case.FAILED
      self.expectedClose = {"closedByMe":True,"closeCode":[self.p.CLOSE_STATUS_CODE_NORMAL],"requireClean":True}
      self.result = "Did not receive message within %d seconds." % self.WAITSECS
      self.p.sendFrame(opcode = 2, payload = self.PAYLOAD, payload_len = self.DATALEN, chopsize = self.chopsize)
      self.p.closeAfter(self.WAITSECS)

   def onMessage(self, msg, binary):
      if not binary:
         self.result = "Expected binary message with payload, but got text."
      else:
         if len(msg) != self.DATALEN:
            self.result = "Expected binary message with payload of length %d, but got %d." % (self.DATALEN, len(msg))
         else:
            ## FIXME : check actual content
            ##
            self.behavior = Case.OK
            self.result = "Received binary message of length %d." % len(msg)
      self.p.createWirelog = True
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)

########NEW FILE########
__FILENAME__ = case9_6_2
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_6_1 import Case9_6_1

class Case9_6_2(Case9_6_1):

   DESCRIPTION = """Send binary message message with payload of length 1 * 2**20 (1M). Sent out data in chops of 128 octets."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def setChopSize(self):
      self.chopsize = 128

########NEW FILE########
__FILENAME__ = case9_6_3
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_6_1 import Case9_6_1

class Case9_6_3(Case9_6_1):

   DESCRIPTION = """Send binary message message with payload of length 1 * 2**20 (1M). Sent out data in chops of 256 octets."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def setChopSize(self):
      self.chopsize = 256

########NEW FILE########
__FILENAME__ = case9_6_4
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_6_1 import Case9_6_1

class Case9_6_4(Case9_6_1):

   DESCRIPTION = """Send binary message message with payload of length 1 * 2**20 (1M). Sent out data in chops of 512 octets."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def setChopSize(self):
      self.chopsize = 512

########NEW FILE########
__FILENAME__ = case9_6_5
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_6_1 import Case9_6_1

class Case9_6_5(Case9_6_1):

   DESCRIPTION = """Send binary message message with payload of length 1 * 2**20 (1M). Sent out data in chops of 1024 octets."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def setChopSize(self):
      self.chopsize = 1024

########NEW FILE########
__FILENAME__ = case9_6_6
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case9_6_1 import Case9_6_1

class Case9_6_6(Case9_6_1):

   DESCRIPTION = """Send binary message message with payload of length 1 * 2**20 (1M). Sent out data in chops of 2048 octets."""

   EXPECTATION = """Receive echo'ed text message (with payload as sent)."""

   def setChopSize(self):
      self.chopsize = 2048

########NEW FILE########
__FILENAME__ = case9_7_X
###############################################################################
##
##  Copyright 2011 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case

## list of (payload length, message count, case timeout)
tests = [(0, 1000, 60),
         (16, 1000, 60),
         (64, 1000, 60),
         (256, 1000, 120),
         (1024, 1000, 240),
         (4096, 1000, 480)]

Case9_7_X = []
Case9_8_X = []


def __init__(self, protocol):
   Case.__init__(self, protocol)
   self.reportTime = True

def onOpen(self):
   self.p.enableWirelog(False)
   self.behavior = Case.FAILED
   self.expectedClose = {"closedByMe": True, "closeCode": [self.p.CLOSE_STATUS_CODE_NORMAL], "requireClean": True}
   self.result = "Case did not finish within %d seconds." % self.WAITSECS
   self.p.closeAfter(self.WAITSECS)
   self.count = 0
   self.sendOne()

def sendOne(self):
   if self.BINARY:
      self.p.sendFrame(opcode = 2, payload = "\xfe", payload_len = self.LEN)
   else:
      self.p.sendFrame(opcode = 1, payload = "*", payload_len = self.LEN)
   self.count += 1

def onMessage(self, msg, binary):
   if binary != self.BINARY or len(msg) != self.LEN:
      self.behavior = Case.FAILED
      self.result = "Echo'ed message type or length differs from what I sent (got binary = %s, payload length = %s)." % (binary, len(msg))
      self.p.enableWirelog(True)
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)
   elif self.count < self.COUNT:
      self.sendOne()
   else:
      self.behavior = Case.OK
      self.result = "Ok, received all echo'ed messages in time."
      self.p.enableWirelog(True)
      self.p.sendClose(self.p.CLOSE_STATUS_CODE_NORMAL)

for b in [False, True]:
   i = 1
   for s in tests:
      if b:
         mt = "binary"
         cc = "Case9_8_%d"
      else:
         mt = "text"
         cc = "Case9_7_%d"
      DESCRIPTION = """Send %d %s messages of payload size %d to measure implementation/network RTT (round trip time) / latency.""" % (s[1], mt, s[0])
      EXPECTATION = """Receive echo'ed %s messages (with payload as sent). Timeout case after %d secs.""" % (mt, s[2])
      C = type(cc % i,
                (object, Case, ),
                {"LEN": s[0],
                 "COUNT": s[1],
                 "WAITSECS": s[2],
                 "BINARY": b,
                 "DESCRIPTION": """%s""" % DESCRIPTION,
                 "EXPECTATION": """%s""" % EXPECTATION,
                 "__init__": __init__,
                 "onOpen": onOpen,
                 "onMessage": onMessage,
                 "sendOne": sendOne,
                 })
      if b:
         Case9_8_X.append(C)
      else:
         Case9_7_X.append(C)
      i += 1

########NEW FILE########
__FILENAME__ = case9_9_1
# coding=utf-8

###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from case import Case
from autobahn.websocket.protocol import WebSocketProtocol
import binascii
from zope.interface import implements
from twisted.internet import reactor, interfaces


class FrameProducer:

   implements(interfaces.IPushProducer)

   def __init__(self, proto, payload):
      self.proto = proto
      self.payload = payload
      self.paused = False
      self.stopped = False

   def pauseProducing(self):
      self.paused = True

   def resumeProducing(self):
      if self.stopped:
         return
      self.paused = False
      while not self.paused:
         self.proto.sendMessageFrame(self.payload)

   def stopProducing(self):
      self.stopped = True


class Case9_9_1(Case):

   PAYLOAD = "*" * 2**10 * 4

   DESCRIPTION = """Send a text message consisting of an infinite sequence of frames with payload 4k. Do this for X seconds."""

   EXPECTATION = """..."""

   def onOpen(self):

      self.expected[Case.OK] = [("timeout", "A"), ("timeout", "B")]
      self.expectedClose = {"closedByMe": True, "closeCode": [self.p.CLOSE_STATUS_CODE_NORMAL], "requireClean": True}

      self.p.createWirelog = False
      self.producer = FrameProducer(self.p, self.PAYLOAD)
      self.p.registerProducer(self.producer, True)
      self.p.beginMessage(opcode = WebSocketProtocol.MESSAGE_TYPE_TEXT)
      self.producer.resumeProducing()
      self.p.continueLater(3, self.part2, "A")

   def part2(self):
      self.received.append(("timeout", "A"))
      self.producer.stopProducing()
      self.p.endMessage()
      self.p.continueLater(5, self.part3, "B")

   def part3(self):
      self.received.append(("timeout", "B"))
      self.p.createWirelog = True
      self.p.sendClose(WebSocketProtocol.CLOSE_STATUS_CODE_NORMAL, "You have survived;)")

   def onConnectionLost(self, failedByMe):
      self.producer.stopProducing()
      Case.onConnectionLost(self, failedByMe)

########NEW FILE########
__FILENAME__ = caseset
###############################################################################
##
##  Copyright (C) 2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ("CaseSet",)


import re


class CaseSet:

   def __init__(self, CaseSetName, CaseBaseName, Cases, CaseCategories, CaseSubCategories):
      self.CaseSetName = CaseSetName
      self.CaseBaseName = CaseBaseName
      self.Cases = Cases
      self.CaseCategories = CaseCategories
      self.CaseSubCategories = CaseSubCategories

      ## Index:
      ## "1.2.3" => Index (1-based) of Case1_2_3 in Cases
      ##
      self.CasesIndices = {}
      i = 1
      for c in self.Cases:
         self.CasesIndices[self.caseClasstoId(c)] = i
         i += 1

      ## Index:
      ## "1.2.3" => Case1_2_3
      ##
      self.CasesById = {}
      for c in self.Cases:
         self.CasesById[self.caseClasstoId(c)] = c


   def caseClasstoId(self, klass):
      """
      Class1_2_3 => '1.2.3'
      """
      l = len(self.CaseBaseName)
      return '.'.join(klass.__name__[l:].split("_"))


   def caseClasstoIdTuple(self, klass):
      """
      Class1_2_3 => (1, 2, 3)
      """
      l = len(self.CaseBaseName)
      return tuple([int(x) for x in klass.__name__[l:].split("_")])


   def caseIdtoIdTuple(self, id):
      """
      '1.2.3' => (1, 2, 3)
      """
      return tuple([int(x) for x in id.split('.')])


   def caseIdTupletoId(self, idt):
      """
      (1, 2, 3) => '1.2.3'
      """
      return '.'.join([str(x) for x in list(idt)])


   def caseClassToPrettyDescription(self, klass):
      """
      Truncates the rest of the description after the first HTML tag
      and coalesces whitespace
      """
      return ' '.join(klass.DESCRIPTION.split('<')[0].split())


   def resolveCasePatternList(self, patterns):
      """
      Return list of test cases that match against a list of case patterns.
      """
      specCases = []
      for c in patterns:
         if c.find('*') >= 0:
            s = c.replace('.', '\.').replace('*', '.*')
            p = re.compile(s)
            t = []
            for x in self.CasesIndices.keys():
               if p.match(x):
                  t.append(self.caseIdtoIdTuple(x))
            for h in sorted(t):
               specCases.append(self.caseIdTupletoId(h))
         else:
            specCases.append(c)
      return specCases


   def parseSpecCases(self, spec):
      """
      Return list of test cases that match against case patterns, minus exclude patterns.
      """
      specCases = self.resolveCasePatternList(spec["cases"])
      if spec.has_key("exclude-cases"):
         excludeCases = self.resolveCasePatternList(spec["exclude-cases"])
      else:
         excludeCases = []
      c = list(set(specCases) - set(excludeCases))
      cases = [self.caseIdTupletoId(y) for y in sorted([self.caseIdtoIdTuple(x) for x in c])]
      return cases


   def parseExcludeAgentCases(self, spec):
      """
      Parses "exclude-agent-cases" from the spec into a list of pairs
      of agent pattern and case pattern list.
      """
      if spec.has_key("exclude-agent-cases"):
         ee = spec["exclude-agent-cases"]
         pats1 = []
         for e in ee:
            s1 = "^" + e.replace('.', '\.').replace('*', '.*') + "$"
            p1 = re.compile(s1)
            pats2 = []
            for z in ee[e]:
               s2 = "^" + z.replace('.', '\.').replace('*', '.*') + "$"
               p2 = re.compile(s2)
               pats2.append(p2)
            pats1.append((p1, pats2))
         return pats1
      else:
         return []


   def checkAgentCaseExclude(self, patterns, agent, case):
      """
      Check if we should exclude a specific case for given agent.
      """
      for p in patterns:
         if p[0].match(agent):
            for pp in p[1]:
               if pp.match(case):
                  return True
      return False


   def getCasesByAgent(self, spec):
      caseIds = self.parseSpecCases(spec)
      epats = self.parseExcludeAgentCases(spec)
      res = []
      for server in spec['testees']:
         agent = server['name']
         res2 = []
         for caseId in caseIds:
            if not self.checkAgentCaseExclude(epats, agent, caseId):
               res2.append(self.CasesById[caseId])
         if len(res2) > 0:
            o = {}
            o['name'] = str(server['name'])
            o['url'] = str(server['url'])
            o['auth'] = server.get('auth', None)
            o['cases'] = res2
            res.append(o)
      return res

   def generateCasesByTestee(self, spec):
      caseIds = self.parseSpecCases(spec)
      epats = self.parseExcludeAgentCases(spec)
      res = {}
      for obj in spec['testees']:
         testee = obj['name']
         res[testee] = []
         for caseId in caseIds:
            if not self.checkAgentCaseExclude(epats, testee, caseId):
               res[testee].append(self.CasesById[caseId])
      return res

########NEW FILE########
__FILENAME__ = choosereactor
###############################################################################
##
##  Copyright 2011,2012 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

import sys, json

## Install Twisted reactor. This needs to be done here,
## before importing any other Twisted/Autobahn stuff!
##
if 'bsd' in sys.platform or sys.platform.startswith('darwin'):
   try:
      v = sys.version_info
      if v[0] == 1 or (v[0] == 2 and v[1] < 6) or (v[0] == 2 and v[1] == 6 and v[2] < 5):
         raise Exception("Python version too old (%s)" % sys.version)
      from twisted.internet import kqreactor
      kqreactor.install()
   except Exception, e:
      print """
WARNING: Running on BSD or Darwin, but cannot use kqueue Twisted reactor.

 => %s

To use the kqueue Twisted reactor, you will need:

  1. Python >= 2.6.5 or PyPy > 1.8
  2. Twisted > 12.0

Note the use of >= and >.

Will let Twisted choose a default reactor (potential performance degradation).
""" % str(e)
      pass


## temporarily disable IOCP, causing problems with chopped up tests
##
if False and sys.platform in ['win32']:
   try:
      from twisted.application.reactors import installReactor
      installReactor("iocp")
   except Exception, e:
      print """
WARNING: Running on Windows, but cannot use IOCP Twisted reactor.

 => %s

Will let Twisted choose a default reactor (potential performance degradation).
""" % str(e)

if sys.platform.startswith('linux'):
   try:
      from twisted.internet import epollreactor
      epollreactor.install()
   except Exception, e:
      print """
WARNING: Running on Linux, but cannot use Epoll Twisted reactor.

 => %s

Will let Twisted choose a default reactor (potential performance degradation).
""" % str(e)

########NEW FILE########
__FILENAME__ = echo
###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ['startClient', 'startServer']


from autobahn.twisted.websocket import connectWS, \
                                       listenWS, \
                                       WebSocketClientFactory, \
                                       WebSocketClientProtocol, \
                                       WebSocketServerFactory, \
                                       WebSocketServerProtocol


class EchoServerProtocol(WebSocketServerProtocol):

   def onMessage(self, payload, isBinary):
      self.sendMessage(payload, isBinary)



class EchoServerFactory(WebSocketServerFactory):

   protocol = EchoServerProtocol

   def __init__(self, url, debug = False):
      WebSocketServerFactory.__init__(self, url, debug = debug, debugCodePaths = debug)



class EchoClientProtocol(WebSocketClientProtocol):

   def onMessage(self, payload, isBinary):
      self.sendMessage(payload, isBinary)



class EchoClientFactory(WebSocketClientFactory):

   protocol = EchoClientProtocol

   def __init__(self, url, debug = False):
      WebSocketClientFactory.__init__(self, url, debug = debug, debugCodePaths = debug)



def startClient(wsuri, debug = False):
   factory = EchoClientFactory(wsuri, debug)
   connectWS(factory)
   return True



def startServer(wsuri, sslKey = None, sslCert = None, debug = False):
   factory = EchoServerFactory(wsuri, debug)
   if sslKey and sslCert:
      sslContext = ssl.DefaultOpenSSLContextFactory(sslKey, sslCert)
   else:
      sslContext = None
   listenWS(factory, sslContext)

   return True

########NEW FILE########
__FILENAME__ = fuzzing
###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ['startClient', 'startServer', 'WS_COMPRESSION_TESTDATA']


import os, json, binascii, time, textwrap, pkg_resources

from twisted.python import log, usage
from twisted.internet import reactor, ssl
from twisted.web.server import Site
from twisted.web.static import File

# for versions
import autobahn
import autobahntestsuite

from autobahn.websocket.protocol import WebSocketProtocol
from autobahn.twisted.websocket import connectWS, listenWS
from autobahn.twisted.websocket import WebSocketServerFactory, \
                                       WebSocketServerProtocol, \
                                       WebSocketClientFactory, \
                                       WebSocketClientProtocol

from case import Case, \
                 Cases, \
                 CaseCategories, \
                 CaseSubCategories, \
                 CaseSetname, \
                 CaseBasename

from caseset import CaseSet

from autobahn.util import utcnow

from report import CSS_COMMON, \
                   CSS_DETAIL_REPORT, \
                   CSS_MASTER_REPORT, \
                   JS_MASTER_REPORT


def binLogData(data, maxlen = 64):
   ellipses = " ..."
   if len(data) > maxlen - len(ellipses):
      dd = binascii.b2a_hex(data[:maxlen]) + ellipses
   else:
      dd = binascii.b2a_hex(data)
   return dd



def asciiLogData(data, maxlen = 64, replace = False):
   ellipses = " ..."
   try:
      if len(data) > maxlen - len(ellipses):
         dd = data[:maxlen] + ellipses
      else:
         dd = data
      return dd.decode('utf8', errors = 'replace' if replace else 'strict')
   except:
      return '0x' + binLogData(data, maxlen)



class FuzzingProtocol:
   """
   Common mixin-base class for fuzzing server and client protocols.
   """

   MAX_WIRE_LOG_DATA = 256

   def connectionMade(self):

      attrs = ['case', 'runCase', 'caseAgent', 'caseStarted']

      for attr in attrs:
         if not hasattr(self, attr):
            setattr(self, attr, None)

      #self.case = None
      #self.runCase = None
      #self.caseAgent = None
      #self.caseStarted = None

      self.caseStart = 0
      self.caseEnd = 0

      ## wire log
      ##
      self.createWirelog = True
      self.wirelog = []

      ## stats for octets and frames
      ##
      self.createStats = True
      self.rxOctetStats = {}
      self.rxFrameStats = {}
      self.txOctetStats = {}
      self.txFrameStats = {}


   def connectionLost(self, reason):
      if self.runCase:

         self.runCase.onConnectionLost(self.failedByMe)
         self.caseEnd = time.time()

         caseResult = {"case": self.case,
                       "id": self.factory.CaseSet.caseClasstoId(self.Case),
                       "description": self.Case.DESCRIPTION,
                       "expectation": self.Case.EXPECTATION,
                       "agent": self.caseAgent,
                       "started": self.caseStarted,
                       "duration": int(round(1000. * (self.caseEnd - self.caseStart))), # case execution time in ms
                       "reportTime": self.runCase.reportTime, # True/False switch to control report output of duration
                       "reportCompressionRatio": self.runCase.reportCompressionRatio,
                       "behavior": self.runCase.behavior,
                       "behaviorClose": self.runCase.behaviorClose,
                       "expected": self.runCase.expected,
                       "expectedClose": self.runCase.expectedClose,
                       "received": self.runCase.received,
                       "result": self.runCase.result,
                       "resultClose": self.runCase.resultClose,
                       "wirelog": self.wirelog,
                       "createWirelog": self.createWirelog,
                       "closedByMe": self.closedByMe,
                       "failedByMe": self.failedByMe,
                       "droppedByMe": self.droppedByMe,
                       "wasClean": self.wasClean,
                       "wasNotCleanReason": self.wasNotCleanReason,
                       "wasServerConnectionDropTimeout": self.wasServerConnectionDropTimeout,
                       "wasOpenHandshakeTimeout": self.wasOpenHandshakeTimeout,
                       "wasCloseHandshakeTimeout": self.wasCloseHandshakeTimeout,
                       "localCloseCode": self.localCloseCode,
                       "localCloseReason": self.localCloseReason,
                       "remoteCloseCode": self.remoteCloseCode,
                       "remoteCloseReason": self.remoteCloseReason,
                       "isServer": self.factory.isServer,
                       "createStats": self.createStats,
                       "rxOctetStats": self.rxOctetStats,
                       "rxFrameStats": self.rxFrameStats,
                       "txOctetStats": self.txOctetStats,
                       "txFrameStats": self.txFrameStats,
                       "httpRequest": self.http_request_data if hasattr(self, 'http_request_data') else '?',
                       "httpResponse": self.http_response_data if hasattr(self, 'http_response_data') else '?',
                       "trafficStats": self.runCase.trafficStats.__json__() if self.runCase.trafficStats else None}

         def cleanBin(e_old):
            e_new = []
            for t in e_old:
               if t[0] == 'message':
                  e_new.append((t[0], asciiLogData(t[1]), t[2]))
               elif t[0] in ['ping', 'pong']:
                  e_new.append((t[0], asciiLogData(t[1])))
               elif t[0] == 'timeout':
                  e_new.append(t)
               else:
                  print t
                  raise Exception("unknown part type %s" % t[0])
            return e_new

         for k in caseResult['expected']:
            e_old = caseResult['expected'][k]
            caseResult['expected'][k] = cleanBin(e_old)

         caseResult['received'] = cleanBin(caseResult['received'])

         ## now log the case results
         ##
         self.factory.logCase(caseResult)


   def enableWirelog(self, enable):
      if enable != self.createWirelog:
         self.createWirelog = enable
         self.wirelog.append(("WLM", enable))


   def logRxOctets(self, data):
      if self.createStats:
         l = len(data)
         self.rxOctetStats[l] = self.rxOctetStats.get(l, 0) + 1
      if self.createWirelog:
         self.wirelog.append(("RO", (len(data), binLogData(data))))


   def logTxOctets(self, data, sync):
      if self.createStats:
         l = len(data)
         self.txOctetStats[l] = self.txOctetStats.get(l, 0) + 1
      if self.createWirelog:
         self.wirelog.append(("TO", (len(data), binLogData(data)), sync))


   def logRxFrame(self, frameHeader, payload):
      if self.createStats:
         self.rxFrameStats[frameHeader.opcode] = self.rxFrameStats.get(frameHeader.opcode, 0) + 1
      if self.createWirelog:
         p = ''.join(payload)
         self.wirelog.append(("RF",
                              (len(p), asciiLogData(p)),
                              frameHeader.opcode,
                              frameHeader.fin,
                              frameHeader.rsv,
                              frameHeader.mask is not None,
                              binascii.b2a_hex(frameHeader.mask) if frameHeader.mask else None))


   def logTxFrame(self, frameHeader, payload, repeatLength, chopsize, sync):
      if self.createStats:
         self.txFrameStats[frameHeader.opcode] = self.txFrameStats.get(frameHeader.opcode, 0) + 1
      if self.createWirelog:
         self.wirelog.append(("TF",
                              (len(payload), asciiLogData(payload)),
                              frameHeader.opcode,
                              frameHeader.fin,
                              frameHeader.rsv,
                              binascii.b2a_hex(frameHeader.mask) if frameHeader.mask else None,
                              repeatLength,
                              chopsize,
                              sync))


   def executeContinueLater(self, fun, tag):
      if self.state != WebSocketProtocol.STATE_CLOSED:
         self.wirelog.append(("CTE", tag))
         fun()
      else:
         pass # connection already gone


   def continueLater(self, delay, fun, tag = None):
      self.wirelog.append(("CT", delay, tag))
      reactor.callLater(delay, self.executeContinueLater, fun, tag)


   def executeKillAfter(self):
      if self.state != WebSocketProtocol.STATE_CLOSED:
         self.wirelog.append(("KLE", ))
         self.failConnection()
      else:
         pass # connection already gone


   def killAfter(self, delay):
      self.wirelog.append(("KL", delay))
      reactor.callLater(delay, self.executeKillAfter)


   def executeCloseAfter(self):
      if self.state != WebSocketProtocol.STATE_CLOSED:
         self.wirelog.append(("TIE", ))
         self.sendClose()
      else:
         pass # connection already gone


   def closeAfter(self, delay):
      self.wirelog.append(("TI", delay))
      reactor.callLater(delay, self.executeCloseAfter)


   def onOpen(self):

      if self.runCase:

         cc_id = self.factory.CaseSet.caseClasstoId(self.runCase.__class__)
         if self.factory.CaseSet.checkAgentCaseExclude(self.factory.specExcludeAgentCases, self.caseAgent, cc_id):
            print "Skipping test case %s for agent %s by test configuration!" % (cc_id, self.caseAgent)
            self.runCase = None
            self.sendClose()
            return
         else:
            self.caseStart = time.time()
            self.runCase.onOpen()

      elif self.path == "/updateReports":
         self.factory.createReports()
         self.sendClose()

      elif self.path == "/getCaseCount":
         self.sendMessage(json.dumps(len(self.factory.specCases)))
         self.sendClose()

      elif self.path == "/getCaseStatus":
         def sendResults(results):
            self.sendMessage(json.dumps({
               'behavior':results['behavior']
            }))
            self.sendClose()

         self.factory.addResultListener(self.caseAgent, self.factory.CaseSet.caseClasstoId(self.Case), sendResults)

      elif self.path == "/getCaseInfo":
         self.sendMessage(json.dumps({
            'id': self.factory.CaseSet.caseClasstoId(self.Case),
            'description': self.factory.CaseSet.caseClassToPrettyDescription(self.Case),
         }))
         self.sendClose()

      else:
         pass


   def onPong(self, payload):
      if self.runCase:
         self.runCase.onPong(payload)
      else:
         if self.debug:
            log.msg("Pong received: " + payload)


   def onClose(self, wasClean, code, reason):
      if self.runCase:
         self.runCase.onClose(wasClean, code, reason)
      else:
         if self.debug:
            log.msg("Close received: %s - %s" % (code, reason))

   def onMessage(self, msg, binary):

      if self.runCase:
         self.runCase.onMessage(msg, binary)

      else:

         if binary:

            raise Exception("binary command message")

         else:

            try:
               obj = json.loads(msg)
            except:
               raise Exception("could not parse command")

            ## send one frame as specified
            ##
            if obj[0] == "sendframe":
               pl = obj[1].get("payload", "")
               self.sendFrame(opcode = obj[1]["opcode"],
                              payload = pl.encode("UTF-8"),
                              fin = obj[1].get("fin", True),
                              rsv = obj[1].get("rsv", 0),
                              mask = obj[1].get("mask", None),
                              payload_len = obj[1].get("payload_len", None),
                              chopsize = obj[1].get("chopsize", None),
                              sync = obj[1].get("sync", False))

            ## send multiple frames as specified
            ##
            elif obj[0] == "sendframes":
               frames = obj[1]
               for frame in frames:
                  pl = frame.get("payload", "")
                  self.sendFrame(opcode = frame["opcode"],
                                 payload = pl.encode("UTF-8"),
                                 fin = frame.get("fin", True),
                                 rsv = frame.get("rsv", 0),
                                 mask = frame.get("mask", None),
                                 payload_len = frame.get("payload_len", None),
                                 chopsize = frame.get("chopsize", None),
                                 sync = frame.get("sync", False))

            ## send close
            ##
            elif obj[0] == "close":
               spec = obj[1]
               self.sendClose(spec.get("code", None), spec.get("reason", None))

            ## echo argument
            ##
            elif obj[0] == "echo":
               spec = obj[1]
               self.sendFrame(opcode = 1, payload = spec.get("payload", ""), payload_len = spec.get("payload_len", None))

            else:
               raise Exception("fuzzing peer received unknown command" % obj[0])



class FuzzingFactory:
   """
   Common mixin-base class for fuzzing server and client protocol factory.
   """

   MAX_CASE_PICKLE_LEN = 1000

   def __init__(self, outdir):
      self.repeatAgentRowPerSubcategory = True
      self.outdir = outdir
      self.agents = {}
      self.cases = {}
      self.resultListeners = {}

   def logCase(self, caseResults):
      """
      Called from FuzzingProtocol instances when case has been finished to store case results.
      """

      agent = caseResults["agent"]
      case = caseResults["id"]

      ## index by agent->case
      ##
      if not self.agents.has_key(agent):
         self.agents[agent] = {}
      self.agents[agent][case] = caseResults

      ## index by case->agent
      ##
      if not self.cases.has_key(case):
         self.cases[case] = {}
      self.cases[case][agent] = caseResults

      if (agent, case) in self.resultListeners:
         callback = self.resultListeners.pop((agent, case))
         callback(caseResults)

   def addResultListener(self, agent, caseId, resultsCallback):
      if agent in self.agents and caseId in self.agents[agent]:
         resultsCallback(self.agents[agent][caseId])
      else:
         self.resultListeners[(agent,caseId)] = resultsCallback


   def createReports(self, produceHtml = True, produceJson = True):
      """
      Create reports from all data stored for test cases which have been executed.
      """

      ## create output directory when non-existent
      ##
      if not os.path.exists(self.outdir):
         os.makedirs(self.outdir)

      ## create master report
      ##
      if produceHtml:
         self.createMasterReportHTML(self.outdir)
      if produceJson:
         self.createMasterReportJSON(self.outdir)

      ## create case detail reports
      ##
      for agentId in self.agents:
         for caseId in self.agents[agentId]:
            if produceHtml:
               self.createAgentCaseReportHTML(agentId, caseId, self.outdir)
            if produceJson:
               self.createAgentCaseReportJSON(agentId, caseId, self.outdir)


   def cleanForFilename(self, str):
      """
      Clean a string for use as filename.
      """
      s0 = ''.join([c if c in "abcdefghjiklmnopqrstuvwxyz0123456789" else " " for c in str.strip().lower()])
      s1 = s0.strip()
      s2 = s1.replace(' ', '_')
      return s2


   def makeAgentCaseReportFilename(self, agentId, caseId, ext):
      """
      Create filename for case detail report from agent and case.
      """
      c = caseId.replace('.', '_')
      return self.cleanForFilename(agentId) + "_case_" + c + "." + ext


   def limitString(self, s, limit, indicator = " ..."):
      ss = str(s)
      if len(ss) > limit - len(indicator):
         return ss[:limit - len(indicator)] + indicator
      else:
         return ss


   def createMasterReportJSON(self, outdir):
      """
      Create report master JSON file.

      :param outdir: Directory where to create file.
      :type outdir: str
      :returns: str -- Name of created file.
      """
      res = {}
      for agentId in self.agents:
         if not res.has_key(agentId):
            res[agentId] = {}
         for caseId in self.agents[agentId]:
            case = self.agents[agentId][caseId]
            c = {}
            report_filename = self.makeAgentCaseReportFilename(agentId, caseId, ext = 'json')
            c["behavior"] = case["behavior"]
            c["behaviorClose"] = case["behaviorClose"]
            c["remoteCloseCode"] = case["remoteCloseCode"]
            c["duration"] = case["duration"]
            c["reportfile"] = report_filename
            res[agentId][caseId] = c

      report_filename = "index.json"
      f = open(os.path.join(outdir, report_filename), 'w')
      f.write(json.dumps(res, sort_keys = True, indent = 3, separators = (',', ': ')))
      f.close()


   def createMasterReportHTML(self, outdir):
      """
      Create report master HTML file.

      :param outdir: Directory where to create file.
      :type outdir: str
      :returns: str -- Name of created file.
      """

      ## open report file in create / write-truncate mode
      ##
      report_filename = "index.html"
      f = open(os.path.join(outdir, report_filename), 'w')

      ## write HTML
      ##
      f.write('<!DOCTYPE html>\n')
      f.write('<html>\n')
      f.write('   <head>\n')
      f.write('      <meta charset="utf-8" />\n')
      f.write('      <style lang="css">%s</style>\n' % CSS_COMMON)
      f.write('      <style lang="css">%s</style>\n' % CSS_MASTER_REPORT)
      f.write('      <script language="javascript">%s</script>\n' % JS_MASTER_REPORT % {"agents_cnt": len(self.agents.keys())})
      f.write('   </head>\n')
      f.write('   <body>\n')
      f.write('      <a href="#"><div id="toggle_button" class="unselectable" onclick="toggleClose();">Toggle Details</div></a>\n')
      f.write('      <a name="top"></a>\n')
      f.write('      <br/>\n')

      ## top logos
      f.write('      <center><a href="http://autobahn.ws/testsuite" title="Autobahn WebSockets Testsuite"><img src="http://autobahn.ws/static/img/ws_protocol_test_report.png"          border="0" width="820" height="46" alt="Autobahn WebSockets Testsuite Report"></img></a></center>\n')
      f.write('      <center><a href="http://autobahn.ws"           title="Autobahn WebSockets">          <img src="http://autobahn.ws/static/img/ws_protocol_test_report_autobahn.png" border="0" width="300" height="68" alt="Autobahn WebSockets">                 </img></a></center>\n')

      ## write report header
      ##
      f.write('      <div id="master_report_header" class="block">\n')
      f.write('         <p id="intro">Summary report generated on %s (UTC) by <a href="%s">Autobahn WebSockets Testsuite</a> v%s/v%s.</p>\n' % (utcnow(), "http://autobahn.ws/testsuite", autobahntestsuite.version, autobahn.version))
      f.write("""
      <table id="case_outcome_desc">
         <tr>
            <td class="case_ok">Pass</td>
            <td class="outcome_desc">Test case was executed and passed successfully.</td>
         </tr>
         <tr>
            <td class="case_non_strict">Non-Strict</td>
            <td class="outcome_desc">Test case was executed and passed non-strictly.
            A non-strict behavior is one that does not adhere to a SHOULD-behavior as described in the protocol specification or
            a well-defined, canonical behavior that appears to be desirable but left open in the protocol specification.
            An implementation with non-strict behavior is still conformant to the protocol specification.</td>
         </tr>
         <tr>
            <td class="case_failed">Fail</td>
            <td class="outcome_desc">Test case was executed and failed. An implementation which fails a test case - other
            than a performance/limits related one - is non-conforming to a MUST-behavior as described in the protocol specification.</td>
         </tr>
         <tr>
            <td class="case_info">Info</td>
            <td class="outcome_desc">Informational test case which detects certain implementation behavior left unspecified by the spec
            but nevertheless potentially interesting to implementors.</td>
         </tr>
         <tr>
            <td class="case_missing">Missing</td>
            <td class="outcome_desc">Test case is missing, either because it was skipped via the test suite configuration
            or deactivated, i.e. because the implementation does not implement the tested feature or breaks during running
            the test case.</td>
         </tr>
      </table>
      """)
      f.write('      </div>\n')

      ## write big agent/case report table
      ##
      f.write('      <table id="agent_case_results">\n')

      ## sorted list of agents for which test cases where run
      ##
      agentList = sorted(self.agents.keys())

      ## create list ordered list of case Ids
      ##
      cl = []
      for c in Cases:
         t = self.CaseSet.caseClasstoIdTuple(c)
         cl.append((t, self.CaseSet.caseIdTupletoId(t)))
      cl = sorted(cl)
      caseList = []
      for c in cl:
         caseList.append(c[1])

      lastCaseCategory = None
      lastCaseSubCategory = None

      for caseId in caseList:

         caseCategoryIndex = caseId.split('.')[0]
         caseCategory = CaseCategories.get(caseCategoryIndex, "Misc")
         caseSubCategoryIndex = '.'.join(caseId.split('.')[:2])
         caseSubCategory = CaseSubCategories.get(caseSubCategoryIndex, None)

         ## Category/Agents row
         ##
         if caseCategory != lastCaseCategory or (self.repeatAgentRowPerSubcategory and caseSubCategory != lastCaseSubCategory):
            f.write('         <tr class="case_category_row">\n')
            f.write('            <td class="case_category">%s %s</td>\n' % (caseCategoryIndex, caseCategory))
            for agentId in agentList:
               f.write('            <td class="agent close_flex" colspan="2">%s</td>\n' % agentId)
            f.write('         </tr>\n')
            lastCaseCategory = caseCategory
            lastCaseSubCategory = None

         ## Subcategory row
         ##
         if caseSubCategory != lastCaseSubCategory:
            f.write('         <tr class="case_subcategory_row">\n')
            f.write('            <td class="case_subcategory" colspan="%d">%s %s</td>\n' % (len(agentList) * 2 + 1, caseSubCategoryIndex, caseSubCategory))
            f.write('         </tr>\n')
            lastCaseSubCategory = caseSubCategory

         ## Cases row
         ##
         f.write('         <tr class="agent_case_result_row">\n')
         f.write('            <td class="case"><a href="#case_desc_%s">Case %s</a></td>\n' % (caseId.replace('.', '_'), caseId))

         ## Case results
         ##
         for agentId in agentList:
            if self.agents[agentId].has_key(caseId):

               case = self.agents[agentId][caseId]

               if case["behavior"] != Case.UNIMPLEMENTED:

                  agent_case_report_file = self.makeAgentCaseReportFilename(agentId, caseId, ext = 'html')

                  if case["behavior"] == Case.OK:
                     td_text = "Pass"
                     td_class = "case_ok"
                  elif case["behavior"] == Case.NON_STRICT:
                     td_text = "Non-Strict"
                     td_class = "case_non_strict"
                  elif case["behavior"] == Case.NO_CLOSE:
                     td_text = "No Close"
                     td_class = "case_no_close"
                  elif case["behavior"] == Case.INFORMATIONAL:
                     td_text = "Info"
                     td_class = "case_info"
                  else:
                     td_text = "Fail"
                     td_class = "case_failed"

                  if case["behaviorClose"] == Case.OK:
                     ctd_text = "%s" % str(case["remoteCloseCode"])
                     ctd_class = "case_ok"
                  elif case["behaviorClose"] == Case.FAILED_BY_CLIENT:
                     ctd_text = "%s" % str(case["remoteCloseCode"])
                     ctd_class = "case_almost"
                  elif case["behaviorClose"] == Case.WRONG_CODE:
                     ctd_text = "%s" % str(case["remoteCloseCode"])
                     ctd_class = "case_non_strict"
                  elif case["behaviorClose"] == Case.UNCLEAN:
                     ctd_text = "Unclean"
                     ctd_class = "case_failed"
                  elif case["behaviorClose"] == Case.INFORMATIONAL:
                     ctd_text = "%s" % str(case["remoteCloseCode"])
                     ctd_class = "case_info"
                  else:
                     ctd_text = "Fail"
                     ctd_class = "case_failed"

                  detail = ""

                  if case["reportTime"]:
                     detail += "%d ms" % case["duration"]

                  if case["reportCompressionRatio"] and case["trafficStats"] is not None:
                     crIn = case["trafficStats"]["incomingCompressionRatio"]
                     crOut = case["trafficStats"]["outgoingCompressionRatio"]
                     detail += " [%s/%s]" % ("%.3f" % crIn if crIn is not None else "-", "%.3f" % crOut if crOut is not None else "-")

                  if detail != "":
                     f.write('            <td class="%s"><a href="%s">%s</a><br/><span class="case_duration">%s</span></td><td class="close close_hide %s"><span class="close_code">%s</span></td>\n' % (td_class, agent_case_report_file, td_text, detail, ctd_class, ctd_text))
                  else:
                     f.write('            <td class="%s"><a href="%s">%s</a></td><td class="close close_hide %s"><span class="close_code">%s</span></td>\n' % (td_class, agent_case_report_file, td_text, ctd_class, ctd_text))

               else:
                  f.write('            <td class="case_unimplemented close_flex" colspan="2">Unimplemented</td>\n')

            else:
               f.write('            <td class="case_missing close_flex" colspan="2">Missing</td>\n')

         f.write("         </tr>\n")

      f.write("      </table>\n")
      f.write("      <br/><hr/>\n")

      ## Case descriptions
      ##
      f.write('      <div id="test_case_descriptions">\n')
      for caseId in caseList:
         CCase = self.CaseSet.CasesById[caseId]
         f.write('      <br/>\n')
         f.write('      <a name="case_desc_%s"></a>\n' % caseId.replace('.', '_'))
         f.write('      <h2>Case %s</h2>\n' % caseId)
         f.write('      <a class="up" href="#top">Up</a>\n')
         f.write('      <p class="case_text_block case_desc"><b>Case Description</b><br/><br/>%s</p>\n' % CCase.DESCRIPTION)
         f.write('      <p class="case_text_block case_expect"><b>Case Expectation</b><br/><br/>%s</p>\n' % CCase.EXPECTATION)
      f.write('      </div>\n')
      f.write("      <br/><hr/>\n")

      ## end of HTML
      ##
      f.write("   </body>\n")
      f.write("</html>\n")

      ## close created HTML file and return filename
      ##
      f.close()
      return report_filename


   def createAgentCaseReportJSON(self, agentId, caseId, outdir):
      """
      Create case detail report JSON file.

      :param agentId: ID of agent for which to generate report.
      :type agentId: str
      :param caseId: ID of case for which to generate report.
      :type caseId: str
      :param outdir: Directory where to create file.
      :type outdir: str
      :returns: str -- Name of created file.
      """

      if not self.agents.has_key(agentId):
         raise Exception("no test data stored for agent %s" % agentId)

      if not self.agents[agentId].has_key(caseId):
         raise Exception("no test data stored for case %s with agent %s" % (caseId, agentId))

      ## get case to generate report for
      ##
      case = self.agents[agentId][caseId]

      ## open report file in create / write-truncate mode
      ##
      report_filename = self.makeAgentCaseReportFilename(agentId, caseId, ext = 'json')
      f = open(os.path.join(outdir, report_filename), 'w')
      f.write(json.dumps(case, sort_keys = True, indent = 3, separators = (',', ': ')))
      f.close()


   def createAgentCaseReportHTML(self, agentId, caseId, outdir):
      """
      Create case detail report HTML file.

      :param agentId: ID of agent for which to generate report.
      :type agentId: str
      :param caseId: ID of case for which to generate report.
      :type caseId: str
      :param outdir: Directory where to create file.
      :type outdir: str
      :returns: str -- Name of created file.
      """

      if not self.agents.has_key(agentId):
         raise Exception("no test data stored for agent %s" % agentId)

      if not self.agents[agentId].has_key(caseId):
         raise Exception("no test data stored for case %s with agent %s" % (caseId, agentId))

      ## get case to generate report for
      ##
      case = self.agents[agentId][caseId]

      ## open report file in create / write-truncate mode
      ##
      report_filename = self.makeAgentCaseReportFilename(agentId, caseId, ext = 'html')
      f = open(os.path.join(outdir, report_filename), 'w')

      ## write HTML
      ##
      f.write('<!DOCTYPE html>\n')
      f.write('<html>\n')
      f.write('   <head>\n')
      f.write('      <meta charset="utf-8" />\n')
      f.write('      <style lang="css">%s</style>\n' % CSS_COMMON)
      f.write('      <style lang="css">%s</style>\n' % CSS_DETAIL_REPORT)
      f.write('   </head>\n')
      f.write('   <body>\n')
      f.write('      <a name="top"></a>\n')
      f.write('      <br/>\n')

      ## top logos
      f.write('      <center><a href="http://autobahn.ws/testsuite" title="Autobahn WebSockets Testsuite"><img src="http://autobahn.ws/static/img/ws_protocol_test_report.png"          border="0" width="820" height="46" alt="Autobahn WebSockets Testsuite Report"></img></a></center>\n')
      f.write('      <center><a href="http://autobahn.ws"           title="Autobahn WebSockets">          <img src="http://autobahn.ws/static/img/ws_protocol_test_report_autobahn.png" border="0" width="300" height="68" alt="Autobahn WebSockets">                 </img></a></center>\n')
      f.write('      <br/>\n')


      ## Case Summary
      ##
      if case["behavior"] == Case.OK:
         style = "case_ok"
         text = "Pass"
      elif case["behavior"] ==  Case.NON_STRICT:
         style = "case_non_strict"
         text = "Non-Strict"
      elif case["behavior"] ==  Case.INFORMATIONAL:
         style = "case_info"
         text = "Informational"
      else:
         style = "case_failed"
         text = "Fail"
      f.write('      <p class="case %s">%s - <span style="font-size: 1.3em;"><b>Case %s</b></span> : %s - <span style="font-size: 0.9em;"><b>%d</b> ms @ %s</a></p>\n' % (style, case["agent"], caseId, text, case["duration"], case["started"]))


      ## Case Description, Expectation, Outcome, Case Closing Behavior
      ##
      f.write('      <p class="case_text_block case_desc"><b>Case Description</b><br/><br/>%s</p>\n' % case["description"])
      f.write('      <p class="case_text_block case_expect"><b>Case Expectation</b><br/><br/>%s</p>\n' % case["expectation"])
      f.write("""
      <p class="case_text_block case_outcome">
         <b>Case Outcome</b><br/><br/>%s<br/><br/>
         <i>Expected:</i><br/><span class="case_pickle">%s</span><br/><br/>
         <i>Observed:</i><br><span class="case_pickle">%s</span>
      </p>\n""" % (case.get("result", ""), self.limitString(case.get("expected", ""), FuzzingFactory.MAX_CASE_PICKLE_LEN), self.limitString(case.get("received", ""), FuzzingFactory.MAX_CASE_PICKLE_LEN)))
      f.write('      <p class="case_text_block case_closing_beh"><b>Case Closing Behavior</b><br/><br/>%s (%s)</p>\n' % (case.get("resultClose", ""), case.get("behaviorClose", "")))
      f.write("      <br/><hr/>\n")


      ## Opening Handshake
      ##
      f.write('      <h2>Opening Handshake</h2>\n')
      f.write('      <pre class="http_dump">%s</pre>\n' % case["httpRequest"].strip())
      f.write('      <pre class="http_dump">%s</pre>\n' % case["httpResponse"].strip())
      f.write("      <br/><hr/>\n")


      ## Closing Behavior
      ##
      cbv = [("isServer", "True, iff I (the fuzzer) am a server, and the peer is a client."),
             ("closedByMe", "True, iff I have initiated closing handshake (that is, did send close first)."),
             ("failedByMe", "True, iff I have failed the WS connection (i.e. due to protocol error). Failing can be either by initiating closing handshake or brutal drop TCP."),
             ("droppedByMe", "True, iff I dropped the TCP connection."),
             ("wasClean", "True, iff full WebSockets closing handshake was performed (close frame sent and received) _and_ the server dropped the TCP (which is its responsibility)."),
             ("wasNotCleanReason", "When wasClean == False, the reason what happened."),
             ("wasServerConnectionDropTimeout", "When we are a client, and we expected the server to drop the TCP, but that didn't happen in time, this gets True."),
             ("wasOpenHandshakeTimeout", "When performing the opening handshake, but the peer did not finish in time, this gets True."),
             ("wasCloseHandshakeTimeout", "When we initiated a closing handshake, but the peer did not respond in time, this gets True."),
             ("localCloseCode", "The close code I sent in close frame (if any)."),
             ("localCloseReason", "The close reason I sent in close frame (if any)."),
             ("remoteCloseCode", "The close code the peer sent me in close frame (if any)."),
             ("remoteCloseReason", "The close reason the peer sent me in close frame (if any).")
            ]
      f.write('      <h2>Closing Behavior</h2>\n')
      f.write('      <table>\n')
      f.write('         <tr class="stats_header"><td>Key</td><td class="left">Value</td><td class="left">Description</td></tr>\n')
      for c in cbv:
         f.write('         <tr class="stats_row"><td>%s</td><td class="left">%s</td><td class="left">%s</td></tr>\n' % (c[0], case[c[0]], c[1]))
      f.write('      </table>')
      f.write("      <br/><hr/>\n")


      ## Wire Statistics
      ##
      f.write('      <h2>Wire Statistics</h2>\n')
      if not case["createStats"]:
         f.write('      <p style="margin-left: 40px; color: #f00;"><i>Statistics for octets/frames disabled!</i></p>\n')
      else:
         ## octet stats
         ##
         for statdef in [("Received", case["rxOctetStats"]), ("Transmitted", case["txOctetStats"])]:
            f.write('      <h3>Octets %s by Chop Size</h3>\n' % statdef[0])
            f.write('      <table>\n')
            stats = statdef[1]
            total_cnt = 0
            total_octets = 0
            f.write('         <tr class="stats_header"><td>Chop Size</td><td>Count</td><td>Octets</td></tr>\n')
            for s in sorted(stats.keys()):
               f.write('         <tr class="stats_row"><td>%d</td><td>%d</td><td>%d</td></tr>\n' % (s, stats[s], s * stats[s]))
               total_cnt += stats[s]
               total_octets += s * stats[s]
            f.write('         <tr class="stats_total"><td>Total</td><td>%d</td><td>%d</td></tr>\n' % (total_cnt, total_octets))
            f.write('      </table>\n')

         ## frame stats
         ##
         for statdef in [("Received", case["rxFrameStats"]), ("Transmitted", case["txFrameStats"])]:
            f.write('      <h3>Frames %s by Opcode</h3>\n' % statdef[0])
            f.write('      <table>\n')
            stats = statdef[1]
            total_cnt = 0
            f.write('         <tr class="stats_header"><td>Opcode</td><td>Count</td></tr>\n')
            for s in sorted(stats.keys()):
               f.write('         <tr class="stats_row"><td>%d</td><td>%d</td></tr>\n' % (s, stats[s]))
               total_cnt += stats[s]
            f.write('         <tr class="stats_total"><td>Total</td><td>%d</td></tr>\n' % (total_cnt))
            f.write('      </table>\n')
      f.write("      <br/><hr/>\n")


      ## Wire Log
      ##
      f.write('      <h2>Wire Log</h2>\n')
      if not case["createWirelog"]:
         f.write('      <p style="margin-left: 40px; color: #f00;"><i>Wire log after handshake disabled!</i></p>\n')

      f.write('      <div id="wirelog">\n')
      wl = case["wirelog"]
      i = 0
      for t in wl:

         if t[0] == "RO":
            prefix = "RX OCTETS"
            css_class = "wirelog_rx_octets"

         elif t[0] == "TO":
            prefix = "TX OCTETS"
            if t[2]:
               css_class = "wirelog_tx_octets_sync"
            else:
               css_class = "wirelog_tx_octets"

         elif t[0] == "RF":
            prefix = "RX FRAME "
            css_class = "wirelog_rx_frame"

         elif t[0] == "TF":
            prefix = "TX FRAME "
            if t[8] or t[7] is not None:
               css_class = "wirelog_tx_frame_sync"
            else:
               css_class = "wirelog_tx_frame"

         elif t[0] in ["CT", "CTE", "KL", "KLE", "TI", "TIE", "WLM"]:
            pass

         else:
            raise Exception("logic error (unrecognized wire log row type %s - row %s)" % (t[0], str(t)))

         if t[0] in ["RO", "TO", "RF", "TF"]:

            payloadLen = t[1][0]
            lines = textwrap.wrap(t[1][1], 100)

            if t[0] in ["RO", "TO"]:
               if len(lines) > 0:
                  f.write('         <pre class="%s">%03d %s: %s</pre>\n' % (css_class, i, prefix, lines[0]))
                  for ll in lines[1:]:
                     f.write('         <pre class="%s">%s%s</pre>\n' % (css_class, (2+4+len(prefix))*" ", ll))
            else:
               if t[0] == "RF":
                  if t[6]:
                     mmask = binascii.b2a_hex(t[6])
                  else:
                     mmask = str(t[6])
                  f.write('         <pre class="%s">%03d %s: OPCODE=%s, FIN=%s, RSV=%s, PAYLOAD-LEN=%s, MASKED=%s, MASK=%s</pre>\n' % (css_class, i, prefix, str(t[2]), str(t[3]), str(t[4]), payloadLen, str(t[5]), mmask))
               elif t[0] == "TF":
                  f.write('         <pre class="%s">%03d %s: OPCODE=%s, FIN=%s, RSV=%s, PAYLOAD-LEN=%s, MASK=%s, PAYLOAD-REPEAT-LEN=%s, CHOPSIZE=%s, SYNC=%s</pre>\n' % (css_class, i, prefix, str(t[2]), str(t[3]), str(t[4]), payloadLen, str(t[5]), str(t[6]), str(t[7]), str(t[8])))
               else:
                  raise Exception("logic error")
               for ll in lines:
                  f.write('         <pre class="%s">%s%s</pre>\n' % (css_class, (2+4+len(prefix))*" ", ll.encode('utf8')))

         elif t[0] == "WLM":
            if t[1]:
               f.write('         <pre class="wirelog_delay">%03d WIRELOG ENABLED</pre>\n' % (i))
            else:
               f.write('         <pre class="wirelog_delay">%03d WIRELOG DISABLED</pre>\n' % (i))

         elif t[0] == "CT":
            f.write('         <pre class="wirelog_delay">%03d DELAY %f sec for TAG %s</pre>\n' % (i, t[1], t[2]))

         elif t[0] == "CTE":
            f.write('         <pre class="wirelog_delay">%03d DELAY TIMEOUT on TAG %s</pre>\n' % (i, t[1]))

         elif t[0] == "KL":
            f.write('         <pre class="wirelog_kill_after">%03d FAIL CONNECTION AFTER %f sec</pre>\n' % (i, t[1]))

         elif t[0] == "KLE":
            f.write('         <pre class="wirelog_kill_after">%03d FAILING CONNECTION</pre>\n' % (i))

         elif t[0] == "TI":
            f.write('         <pre class="wirelog_kill_after">%03d CLOSE CONNECTION AFTER %f sec</pre>\n' % (i, t[1]))

         elif t[0] == "TIE":
            f.write('         <pre class="wirelog_kill_after">%03d CLOSING CONNECTION</pre>\n' % (i))

         else:
            raise Exception("logic error (unrecognized wire log row type %s - row %s)" % (t[0], str(t)))

         i += 1

      if case["droppedByMe"]:
         f.write('         <pre class="wirelog_tcp_closed_by_me">%03d TCP DROPPED BY ME</pre>\n' % i)
      else:
         f.write('         <pre class="wirelog_tcp_closed_by_peer">%03d TCP DROPPED BY PEER</pre>\n' % i)
      f.write('      </div>\n')
      f.write("      <br/><hr/>\n")

      ## end of HTML
      ##
      f.write("   </body>\n")
      f.write("</html>\n")

      ## close created HTML file and return filename
      ##
      f.close()
      return report_filename



class FuzzingServerProtocol(FuzzingProtocol, WebSocketServerProtocol):

   def connectionMade(self):
      WebSocketServerProtocol.connectionMade(self)
      FuzzingProtocol.connectionMade(self)


   def connectionLost(self, reason):
      WebSocketServerProtocol.connectionLost(self, reason)
      FuzzingProtocol.connectionLost(self, reason)


   def onConnect(self, connectionRequest):
      if self.debug:
         log.msg("connection received from %s speaking WebSockets protocol %d - upgrade request for host '%s', path '%s', params %s, origin '%s', protocols %s, headers %s" % (connectionRequest.peer, connectionRequest.version, connectionRequest.host, connectionRequest.path, str(connectionRequest.params), connectionRequest.origin, str(connectionRequest.protocols), str(connectionRequest.headers)))

      if connectionRequest.params.has_key("agent"):
         if len(connectionRequest.params["agent"]) > 1:
            raise Exception("multiple agents specified")
         self.caseAgent = connectionRequest.params["agent"][0]
      else:
         #raise Exception("no agent specified")
         self.caseAgent = None

      if connectionRequest.params.has_key("case"):
         if len(connectionRequest.params["case"]) > 1:
            raise Exception("multiple test cases specified")
         try:
            self.case = int(connectionRequest.params["case"][0])
         except:
            raise Exception("invalid test case ID %s" % connectionRequest.params["case"][0])

      if self.case:
         if self.case >= 1 and self.case <= len(self.factory.specCases):
            self.Case = self.factory.CaseSet.CasesById[self.factory.specCases[self.case - 1]]
            if connectionRequest.path == "/runCase":
               self.runCase = self.Case(self)
         else:
            raise Exception("case %s not found" % self.case)

      if connectionRequest.path == "/runCase":
         if not self.runCase:
            raise Exception("need case to run")
         if not self.caseAgent:
            raise Exception("need agent to run case")
         self.caseStarted = utcnow()
         print "Running test case ID %s for agent %s from peer %s" % (self.factory.CaseSet.caseClasstoId(self.Case), self.caseAgent, connectionRequest.peer)

      elif connectionRequest.path == "/updateReports":
         if not self.caseAgent:
            raise Exception("need agent to update reports for")
         print "Updating reports, requested by peer %s" % connectionRequest.peer

      elif connectionRequest.path == "/getCaseInfo":
         if not self.Case:
            raise Exception("need case to get info")

      elif connectionRequest.path == "/getCaseStatus":
         if not self.Case:
            raise Exception("need case to get status")
         if not self.caseAgent:
            raise Exception("need agent to get status")

      elif connectionRequest.path == "/getCaseCount":
         pass

      else:
         print "Entering direct command mode for peer %s" % connectionRequest.peer

      self.path = connectionRequest.path

      return None



class FuzzingServerFactory(FuzzingFactory, WebSocketServerFactory):

   protocol = FuzzingServerProtocol

   def __init__(self, spec, debug = False):

      WebSocketServerFactory.__init__(self, debug = debug, debugCodePaths = debug)
      FuzzingFactory.__init__(self, spec.get("outdir", "./reports/clients/"))

      # needed for wire log / stats
      self.logOctets = True
      self.logFrames = True

      ## WebSocket session parameters
      ##
      self.setSessionParameters(url = spec["url"],
                                protocols = spec.get("protocols", []),
                                server = "AutobahnTestSuite/%s-%s" % (autobahntestsuite.version, autobahn.version))

      ## WebSocket protocol options
      ##
      self.setProtocolOptions(failByDrop = False) # spec conformance
      self.setProtocolOptions(**spec.get("options", {}))

      self.spec = spec

      self.CaseSet = CaseSet(CaseSetname, CaseBasename, Cases, CaseCategories, CaseSubCategories)

      self.specCases = self.CaseSet.parseSpecCases(self.spec)
      self.specExcludeAgentCases = self.CaseSet.parseExcludeAgentCases(self.spec)
      print "Autobahn WebSockets %s/%s Fuzzing Server (Port %d%s)" % (autobahntestsuite.version, autobahn.version, self.port, ' TLS' if self.isSecure else '')
      print "Ok, will run %d test cases for any clients connecting" % len(self.specCases)
      print "Cases = %s" % str(self.specCases)



class FuzzingClientProtocol(FuzzingProtocol, WebSocketClientProtocol):

   def connectionMade(self):
      FuzzingProtocol.connectionMade(self)
      WebSocketClientProtocol.connectionMade(self)
      self.caseStarted = utcnow()


   def onConnect(self, response):
      if not self.caseAgent:
         self.caseAgent = response.headers.get('server', 'UnknownServer')
      print "Running test case ID %s for agent %s from peer %s" % (self.factory.CaseSet.caseClasstoId(self.Case), self.caseAgent, self.peer)


   def connectionLost(self, reason):
      WebSocketClientProtocol.connectionLost(self, reason)
      FuzzingProtocol.connectionLost(self, reason)



class FuzzingClientFactory(FuzzingFactory, WebSocketClientFactory):

   protocol = FuzzingClientProtocol

   def __init__(self, spec, debug = False):

      WebSocketClientFactory.__init__(self, debug = debug, debugCodePaths = debug)
      FuzzingFactory.__init__(self, spec.get("outdir", "./reports/servers/"))

      # needed for wire log / stats
      self.logOctets = True
      self.logFrames = True

      self.spec = spec

      self.CaseSet = CaseSet(CaseSetname, CaseBasename, Cases, CaseCategories, CaseSubCategories)

      self.specCases = self.CaseSet.parseSpecCases(self.spec)
      self.specExcludeAgentCases = self.CaseSet.parseExcludeAgentCases(self.spec)
      print "Autobahn Fuzzing WebSocket Client (Autobahn Version %s / Autobahn Testsuite Version %s)" % (autobahntestsuite.version, autobahn.version)
      print "Ok, will run %d test cases against %d servers" % (len(self.specCases), len(spec["servers"]))
      print "Cases = %s" % str(self.specCases)
      print "Servers = %s" % str([x["url"] for x in spec["servers"]])

      self.currServer = -1
      if self.nextServer():
         if self.nextCase():
            connectWS(self)


   def buildProtocol(self, addr):
      proto = FuzzingClientProtocol()
      proto.factory = self

      proto.caseAgent = self.agent
      proto.case = self.currentCaseIndex
      proto.Case = Cases[self.currentCaseIndex - 1]
      proto.runCase = proto.Case(proto)

      return proto


   def nextServer(self):
      self.currSpecCase = -1
      self.currServer += 1
      if self.currServer < len(self.spec["servers"]):
         ## run tests for next server
         ##
         server = self.spec["servers"][self.currServer]

         ## agent (=server) string for reports
         ##
         self.agent = server.get("agent")

         ## WebSocket session parameters
         ##
         self.setSessionParameters(url = server["url"],
                                   origin = server.get("origin", None),
                                   protocols = server.get("protocols", []),
                                   useragent = "AutobahnTestSuite/%s-%s" % (autobahntestsuite.version, autobahn.version))

         ## WebSocket protocol options
         ##
         self.resetProtocolOptions() # reset to defaults
         self.setProtocolOptions(failByDrop = False) # spec conformance
         self.setProtocolOptions(**self.spec.get("options", {})) # set spec global options
         self.setProtocolOptions(**server.get("options", {})) # set server specific options
         return True
      else:
         return False


   def nextCase(self):
      self.currSpecCase += 1
      if self.currSpecCase < len(self.specCases):
         self.currentCaseId = self.specCases[self.currSpecCase]
         self.currentCaseIndex = self.CaseSet.CasesIndices[self.currentCaseId]
         return True
      else:
         return False


   def clientConnectionLost(self, connector, reason):
      if self.nextCase():
         connector.connect()
      else:
         if self.nextServer():
            if self.nextCase():
               connectWS(self)
         else:
            self.createReports()
            reactor.stop()


   def clientConnectionFailed(self, connector, reason):
      print "Connection to %s failed (%s)" % (self.spec["servers"][self.currServer]["url"], reason.getErrorMessage())
      if self.nextServer():
         if self.nextCase():
            connectWS(self)
      else:
         self.createReports()
         reactor.stop()


def startClient(spec, debug = False):
   factory = FuzzingClientFactory(spec, debug)
   # no connectWS done here, since this is done within
   # FuzzingClientFactory automatically to orchestrate tests
   return True



def startServer(spec, sslKey = None, sslCert = None, debug = False):
   ## use TLS server key/cert from spec, but allow overriding
   ## from cmd line
   if not sslKey:
      sslKey = spec.get('key', None)
   if not sslCert:
      sslCert = spec.get('cert', None)

   factory = FuzzingServerFactory(spec, debug)

   if sslKey and sslCert:
      sslContext = ssl.DefaultOpenSSLContextFactory(sslKey, sslCert)
   else:
      sslContext = None

   listenWS(factory, sslContext)

   webdir = File(pkg_resources.resource_filename("autobahntestsuite",
                                                 "web/fuzzingserver"))
   curdir = File('.')
   webdir.putChild('cwd', curdir)
   web = Site(webdir)
   if factory.isSecure:
      reactor.listenSSL(spec.get("webport", 8080), web, sslContext)
   else:
      reactor.listenTCP(spec.get("webport", 8080), web)

   return True

########NEW FILE########
__FILENAME__ = interfaces
###############################################################################
##
##  Copyright 2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ('ITestDb', 'IReportGenerator', )

import zope
from zope.interface import Interface, Attribute

class ICaseSet(Interface):
   """
   """
   pass


class ITestDb(Interface):
   """
   A Test database provides storage and query capabilities
   for test cases, results and related data.
   """

   def newRun(specId):
      """
      Create a new testsuite run.

      :param mode: The testsuite mode.
      :type mode: str
      :param spec: The test specification.
      :type spec: object (a JSON serializable test spec)
      :returns Deferred -- The test run ID.
      """


   def closeRun(runId):
      """
      Closes a testsuite run. After a testsuite run is closed,
      the test result data cannot be changed or new data added.

      :param testRunId: ID of test run as previsouly returned by newRun().
      :type testRunId: str
      """


   def generateCasesByTestee(specId):
      """
      """


   def saveResult(runId, testRun, test, result):
      """
      Saves a test result in the database.

      :param runId: The test run ID.
      :type runId: str
      :param result: The test result. An instance of TestResult.
      :type result: object
      :returns Deferred -- The test result ID.
      """

   # def registerResultFile(resultId, type, sha1, path):
   #    """
   #    When a report file generator has produced it's output
   #    and created (or recreated/modified) a file, it should
   #    register the file location via this function.

   #    :param resultId: The ID of the test result this file was generated for.
   #    :type resultId: str
   #    :param type: The type of file produced (FIXME: ['html', 'json'] ??)
   #    :type type: FIXME
   #    :param sha1: The SHA-1 computed over the generated octet stream.
   #    :type sha1 str
   #    :param path: The filesystem path to the generated file.
   #    :type path: str
   #    """

ITestDb.TESTMODES = set(['fuzzingwampclient', 'fuzzingclient'])
"""
The list of implemented test modes.
"""


class ITestRunner(Interface):
   """
   """

   def runAndObserve(specName, observers = [], saveResults = True):
      """
      :param observers: An iterable of ITestRunObserver instances.
      :type observers: iterable
      """


class IReportGenerator(Interface):
   """
   A Report generator is able to produce report files (in a
   format the generator supports) from test results stored
   in a Test database.
   """

   outputDirectory = Attribute("""Default output directory base path. (e.g. 'reports/wamp/servers')""")

   fileExtension = Attribute("""Default file extension for report files (e.g. '.html').""")

   mimeType = Attribute("""Default MIME type for generated reports (e.g. 'text/html').""")


   def writeReportIndexFile(runId, file = None):
      """
      Generate a test report index and write to file like object or
      to an automatically chosen report file (under the default
      output directory

      :param runId: The test run ID for which to generate the index for.
      :type runId: object
      :param file: A file like object or None (automatic)
      :type file: object
      :returns -- None if file was provided, or the pathname
                  of the created report file (automatic).
      """

   def writeReportFile(resultId, file = None):
      """
      Generate a test report and write to file like object or
      to an automatically chosen report file (under the default
      output directory

      :param resultId: The test result ID for which to generate the report for.
      :type resultId: object
      :param file: A file like object or None (automatic)
      :type file: object
      :returns -- None if file was provided, or the pathname
                  of the created report file (automatic).
      """




class ITestRun(Interface):
   """
   """

   def next():
      """
      Returns the next test case for this run or None when
      the test run is finished.

      :returns ICase -- The next test case or None.
      """

   def remaining():
      """
      Number of remaining test cases in this test run.

      :returns int -- Number of remaining test cases.
      """

   def __len__():
      """
      The length of this test run (note that fetching
      test cases does not change the length).
      """


class ITestRunObserver(Interface):
   """
   """

   def progress(runId, testRun, testCase, result, remaining):
      """
      """


class ITestCase(Interface):
   """
   Tests are instantiated as objects providing this interface.
   They have their run() method called exactly once before
   being disposed.
   """
   index = Attribute("""Test case index - a tuple of ints.""")
   description = Attribute("""Test case description.""")
   expectation = Attribute("""Test case expectation.""")
   params = Attribute("""Test case parameters.""")

   def run():
      """
      Run the test case. Returns a deferred that provides an instance
      of TestResult when successful.
      """

########NEW FILE########
__FILENAME__ = massconnect
###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ['startClient']


import time, sys

from twisted.internet import defer, reactor
from twisted.internet.defer import Deferred, returnValue, inlineCallbacks

from autobahn.twisted.websocket import connectWS, \
                                       WebSocketClientFactory, \
                                       WebSocketClientProtocol


class MassConnectProtocol(WebSocketClientProtocol):

   wasHandshaked = False

   def onOpen(self):
      ## WebSocket opening handshake complete => log
      self.factory.test.onConnected()
      self.factory.test.protos.append(self)
      self.wasHandshaked = True


class MassConnectFactory(WebSocketClientFactory):

   protocol = MassConnectProtocol

   def clientConnectionFailed(self, connector, reason):
      if self.test.onFailed():
         reactor.callLater(float(self.retrydelay)/1000., connector.connect)

   def clientConnectionLost(self, connector, reason):
      if self.test.onLost():
         reactor.callLater(float(self.retrydelay)/1000., connector.connect)


class MassConnect:

   def __init__(self, name, uri, connections, batchsize, batchdelay, retrydelay):
      self.name = name
      self.uri = uri
      self.batchsize = batchsize
      self.batchdelay = batchdelay
      self.retrydelay = retrydelay
      self.failed = 0
      self.lost = 0
      self.targetCnt = connections
      self.currentCnt = 0
      self.actual = 0
      self.protos = []

   def run(self):
      self.d = Deferred()
      self.started = time.clock()
      self.connectBunch()
      return self.d

   def onFailed(self):
      self.failed += 1
      sys.stdout.write("!")
      return True

   def onLost(self):
      self.lost += 1
      #sys.stdout.write("*")
      return False
      return True

   def onConnected(self):
      self.actual += 1
      if self.actual % self.batchsize == 0:
         sys.stdout.write(".")
      if self.actual == self.targetCnt:
         self.ended = time.clock()
         duration = self.ended - self.started
         print " connected %d clients to %s at %s in %s seconds (retries %d = failed %d + lost %d)" % (self.currentCnt, self.name, self.uri, duration, self.failed + self.lost, self.failed, self.lost)
         result = {'name': self.name,
                   'uri': self.uri,
                   'connections': self.targetCnt,
                   'retries': self.failed + self.lost,
                   'lost': self.lost,
                   'failed': self.failed,
                   'duration': duration}
         for p in self.protos:
            p.sendClose()
         #self.d.callback(result)

   def connectBunch(self):
      if self.currentCnt + self.batchsize < self.targetCnt:
         c = self.batchsize
         redo = True
      else:
         c = self.targetCnt - self.currentCnt
         redo = False
      for i in xrange(0, c):
         factory = MassConnectFactory(self.uri)
         factory.test = self
         factory.retrydelay = self.retrydelay
         connectWS(factory)
         self.currentCnt += 1
      if redo:
         reactor.callLater(float(self.batchdelay)/1000., self.connectBunch)


class MassConnectTest:
   def __init__(self, spec):
      self.spec = spec

   @inlineCallbacks
   def run(self):
      print self.spec
      res = []
      for s in self.spec['servers']:
         t = MassConnect(s['name'],
                         s['uri'],
                         self.spec['options']['connections'],
                         self.spec['options']['batchsize'],
                         self.spec['options']['batchdelay'],
                         self.spec['options']['retrydelay'])
         r = yield t.run()
         res.append(r)
      returnValue(res)


def startClient(spec, debug = False):
   test = MassConnectTest(spec)
   d = test.run()
   return d

########NEW FILE########
__FILENAME__ = report
###############################################################################
##
##  Copyright 2011-2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################
import jinja2
import os
import sys


__all__ = ("CSS_COMMON",
           "CSS_MASTER_REPORT",
           "CSS_DETAIL_REPORT",
           "JS_MASTER_REPORT",
           "HtmlReport")

## TODO: Move the constants to jinja2 template files

##
## CSS/JS include bits for WebSocket and WAMP test reports
##

## CSS common for all reports
##
CSS_COMMON = """
body {
   background-color: #F4F4F4;
   color: #333;
   font-family: Segoe UI,Tahoma,Arial,Verdana,sans-serif;
}

p#intro {
   font-family: Cambria,serif;
   font-size: 1.1em;
   color: #444;
}

p#intro a {
   color: #444;
}

p#intro a:visited {
   color: #444;
}

.block {
   background-color: #e0e0e0;
   padding: 16px;
   margin: 20px;
}

p.case_text_block {
   border-radius: 10px;
   border: 1px solid #aaa;
   padding: 16px;
   margin: 4px 20px;
   color: #444;
}

p.case_desc {
}

p.case_expect {
}

p.case_outcome {
}

p.case_closing_beh {
}

pre.http_dump {
   font-family: Consolas, "Courier New", monospace;
   font-size: 0.8em;
   color: #333;
   border-radius: 10px;
   border: 1px solid #aaa;
   padding: 16px;
   margin: 4px 20px;
}

span.case_pickle {
   font-family: Consolas, "Courier New", monospace;
   font-size: 0.7em;
   color: #000;
}

p#case_result,p#close_result {
   border-radius: 10px;
   background-color: #e8e2d1;
   padding: 20px;
   margin: 20px;
}

h1 {
   margin-left: 60px;
}

h2 {
   margin-left: 30px;
}

h3 {
   margin-left: 50px;
}

a.up {
   float: right;
   border-radius: 16px;
   margin-top: 16px;
   margin-bottom: 10px;

   margin-right: 30px;
   padding-left: 10px;
   padding-right: 10px;
   padding-bottom: 2px;
   padding-top: 2px;
   background-color: #666;
   color: #fff;
   text-decoration: none;
   font-size: 0.8em;
}

a.up:visited {
}

a.up:hover {
   background-color: #028ec9;
}
"""

## CSS for Master report
##
CSS_MASTER_REPORT = """
table {
   border-collapse: collapse;
   border-spacing: 0px;
}

td {
   margin: 0;
   border: 1px solid #fff;
   padding-top: 6px;
   padding-bottom: 6px;
   padding-left: 16px;
   padding-right: 16px;
   font-size: 0.9em;
   color: #fff;
}

table#agent_case_results {
   border-collapse: collapse;
   border-spacing: 0px;
   border-radius: 10px;
   margin-left: 20px;
   margin-right: 20px;
   margin-bottom: 40px;
}

td.outcome_desc {
   width: 100%;
   color: #333;
   font-size: 0.8em;
}

tr.agent_case_result_row a {
   color: #eee;
}

td.agent {
   color: #fff;
   font-size: 1.0em;
   text-align: center;
   background-color: #048;
   font-size: 0.8em;
   word-wrap: break-word;
   padding: 4px;
   width: 140px;
}

td.case {
   background-color: #666;
   text-align: left;
   padding-left: 40px;
   font-size: 0.9em;
}

td.case_category {
   color: #fff;
   background-color: #000;
   text-align: left;
   padding-left: 20px;
   font-size: 1.0em;
}

td.case_subcategory {
   color: #fff;
   background-color: #333;
   text-align: left;
   padding-left: 30px;
   font-size: 0.9em;
}

td.close {
   width: 15px;
   padding: 6px;
   font-size: 0.7em;
   color: #fff;
   min-width: 0px;
}

td.case_ok {
   background-color: #0a0;
   text-align: center;
}

td.case_almost {
   background-color: #6d6;
   text-align: center;
}

td.case_non_strict, td.case_no_close {
   background-color: #9a0;
   text-align: center;
}

td.case_info {
   background-color: #4095BF;
   text-align: center;
}

td.case_unimplemented {
   background-color: #800080;
   text-align: center;
}

td.case_failed {
   background-color: #900;
   text-align: center;
}

td.case_missing {
   color: #fff;
   background-color: #a05a2c;
   text-align: center;
}

span.case_duration {
   font-size: 0.7em;
   color: #fff;
}

*.unselectable {
   user-select: none;
   -moz-user-select: -moz-none;
   -webkit-user-select: none;
   -khtml-user-select: none;
}

div#toggle_button {
   position: fixed;
   bottom: 10px;
   right: 10px;
   background-color: rgba(60, 60, 60, 0.5);
   border-radius: 12px;
   color: #fff;
   font-size: 0.7em;
   padding: 5px 10px;
}

div#toggle_button:hover {
   background-color: #028ec9;
}
"""

## CSS for Agent/Case detail report
##
CSS_DETAIL_REPORT = """
p.case {
   color: #fff;
   border-radius: 10px;
   padding: 20px;
   margin: 12px 20px;
   font-size: 1.2em;
}

p.case_ok {
   background-color: #0a0;
}

p.case_non_strict, p.case_no_close {
   background-color: #9a0;
}

p.case_info {
   background-color: #4095BF;
}

p.case_failed {
   background-color: #900;
}

table {
   border-collapse: collapse;
   border-spacing: 0px;
   margin-left: 80px;
   margin-bottom: 12px;
   margin-top: 0px;
}

td
{
   margin: 0;
   font-size: 0.8em;
   border: 1px #fff solid;
   padding-top: 6px;
   padding-bottom: 6px;
   padding-left: 16px;
   padding-right: 16px;
   text-align: right;
}

td.right {
   text-align: right;
}

td.left {
   text-align: left;
}

tr.stats_header {
   color: #eee;
   background-color: #000;
}

tr.stats_row {
   color: #000;
   background-color: #fc3;
}

tr.stats_total {
   color: #fff;
   background-color: #888;
}

div#wirelog {
   margin-top: 20px;
   margin-bottom: 80px;
}

pre.wirelog_rx_octets {color: #aaa; margin: 0; background-color: #060; padding: 2px;}
pre.wirelog_tx_octets {color: #aaa; margin: 0; background-color: #600; padding: 2px;}
pre.wirelog_tx_octets_sync {color: #aaa; margin: 0; background-color: #606; padding: 2px;}

pre.wirelog_rx_frame {color: #fff; margin: 0; background-color: #0a0; padding: 2px;}
pre.wirelog_tx_frame {color: #fff; margin: 0; background-color: #a00; padding: 2px;}
pre.wirelog_tx_frame_sync {color: #fff; margin: 0; background-color: #a0a; padding: 2px;}

pre.wirelog_delay {color: #fff; margin: 0; background-color: #000; padding: 2px;}
pre.wirelog_kill_after {color: #fff; margin: 0; background-color: #000; padding: 2px;}

pre.wirelog_tcp_closed_by_me {color: #fff; margin: 0; background-color: #008; padding: 2px;}
pre.wirelog_tcp_closed_by_peer {color: #fff; margin: 0; background-color: #000; padding: 2px;}
"""

## JavaScript for master report
##
## Template vars:
##    agents_cnt => int => len(self.agents.keys())
##
JS_MASTER_REPORT = """
var isClosed = false;

function closeHelper(display,colspan) {
   // hide all close codes
   var a = document.getElementsByClassName("close_hide");
   for (var i in a) {
      if (a[i].style) {
         a[i].style.display = display;
      }
   }

   // set colspans
   var a = document.getElementsByClassName("close_flex");
   for (var i in a) {
      a[i].colSpan = colspan;
   }

   var a = document.getElementsByClassName("case_subcategory");
   for (var i in a) {
      a[i].colSpan = %(agents_cnt)d * colspan + 1;
   }
}

function toggleClose() {
   if (window.isClosed == false) {
      closeHelper("none",1);
      window.isClosed = true;
   } else {
      closeHelper("table-cell",2);
      window.isClosed = false;
   }
}
"""


REPORT_DIR_PERMISSIONS = 0770


from zope.interface import implementer
from interfaces import IReportGenerator


@implementer(IReportGenerator)
class HtmlReportGenerator(object):

    def __init__(self, test_db, report_dirname):
        self.test_db = test_db
        self.report_dirname = report_dirname
        env = jinja2.Environment(
            loader=jinja2.PackageLoader("autobahntestsuite", "templates"),
            line_statement_prefix="#",
            line_comment_prefix="##")
        self.wamp_details_tpl = env.get_template("wamp_details.html")
        self.wamp_index_tpl = env.get_template("wamp_overview.html")

        # Check if the 'reports' directory exists; try to create it otherwise.
        if not os.path.isdir(report_dirname):
            self.createReportDirectory()

    def writeReportIndexFile(self, runId, file = None):
       # return a Deferred that yields the automatically
       # chose filename if no file-like objct was provided,
       # and None otherwise
       raise Exception("implement me")
       
    def writeReportFile(self, resultId, file = None):
       # return a Deferred that yields the automatically
       # chose filename if no file-like objct was provided,
       # and None otherwise
       raise Exception("implement me")
       
    def createReportDirectory(self):
       """
       Create the directory for storing the reports. If this is not possible,
       terminate the script.
       """
       try:
          os.makedirs(self.report_dirname, REPORT_DIR_PERMISSIONS)
       except OSError, exc:
          print "Could not create directory: %s" % exc
          sys.exit(1)


    ### TODO: Move the creation of reports to a separate class.
    def createReport(self, res, report_filename, readable_test_name, agent,
                     description):
       """
       Create an HTML file called `report_filename` in the
       `report_dirname` directory with details about the test case.
       """
       report_path = os.path.join(self.report_dirname, report_filename)
       try:
          f = open(report_path, "w")
       except IOError, ex:
          print "Could not create file %s: %s." % (report_path, ex)
          return
       try:
           f.write(self.formatResultAsHtml(res, readable_test_name, agent,
                                           description))
       except Exception, ex:
           print "Could not write report: %s." % ex
       f.close()


    def formatResultAsHtml(self, res, readable_test_name, agent, description):
       """
       Create an HTML document with a table containing information about
       the test outcome.
       """
       html = self.wamp_details_tpl.render(record_list=res[3],
                                           test_name = readable_test_name,
                                           expected=res[1],
                                           observed=res[2],
                                           outcome="Pass" if res[0] else "Fail",
                                           agent=agent,
                                           description=description)
       return html

    
    def createIndex(self, reports):
        """
        Create an HTML document with a table containing an overview of all
        tests and links to the detailed documents.
        """
        try:
            with open(os.path.join(self.report_dirname, "index.html"),
                      "w") as f:
                html = self.wamp_index_tpl.render(categories=reports)
                f.write(html)
        except Exception, ex:
            print "Could not create index file: %s" % ex

########NEW FILE########
__FILENAME__ = rinterfaces
###############################################################################
##
##  Copyright 2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ('RITestDb', 'RITestRunner', )

import zope
from zope.interface import Interface, Attribute


class RITestDb(Interface):
   """
   A Test database provides storage and query capabilities for test cases, results and related data.

   This interface is remoted as a set of WAMP endpoints.
   """

   URI = Attribute("The base URI under which methods are exposed for WAMP.")


   def importSpec(spec):
      """
      Import a test specification into the test database.

      Returns a pair `(op, id)`, where `op` specifies the operation that
      actually was carried out:

          - None: unchanged
          - 'U': updated
          - 'I': inserted

      The `id` is the new (or existing) database object ID for the spec.
      """


   def getSpecs(activeOnly = True):
      """
      """


   def getSpec(specId):
      """
      """


   def getSpecByName(name):
      """
      Find a (currently active, if any) test specification by name.
      """


   def getTestRuns(limit = 10):
      """
      Return a list of latest testruns.
      """


   def getTestResult(resultId):
      """
      Get a single test result by ID.

      :param resultId: The ID of the test result to retrieve.
      :type resultId: str
      :returns Deferred -- A single instance of TestResult.
      """


   def getTestRunIndex(runId):
      """
      """


   def getTestRunSummary(runId):
      """
      """



class RITestRunner(Interface):
   """
   """

   def run(specName, saveResults = True):
      """
      """

########NEW FILE########
__FILENAME__ = serializer
###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from __future__ import absolute_import

__all__ = ['start']

import json
import binascii
from autobahn import wamp
from autobahn.wamp.tests.test_serializer import generate_test_messages


def start(outfilename, debug = False):
   with open(outfilename, 'wb') as outfile:
      ser_json = wamp.serializer.JsonSerializer()
      ser_msgpack = wamp.serializer.MsgPackSerializer()

      res = []
      for msg in generate_test_messages():
         case = {}
         case['name'] = str(msg)
         case['rmsg'] = msg.marshal()

         ## serialize message to JSON
         bytes, binary = ser_json.serialize(msg)
         case['json'] = bytes

         ## serialize message to MsgPack
         bytes, binary = ser_msgpack.serialize(msg)
         case['msgpack'] = binascii.hexlify(bytes)

         res.append(case)

      outfile.write(json.dumps(res, indent = 3))

########NEW FILE########
__FILENAME__ = spectemplate
###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__= ("SPEC_FUZZINGSERVER",
          "SPEC_FUZZINGCLIENT",
          "SPEC_FUZZINGWAMPSERVER",
          "SPEC_FUZZINGWAMPCLIENT",
          "SPEC_WSPERFCONTROL",
          "SPEC_MASSCONNECT",)


SPEC_FUZZINGSERVER = """
{
   "url": "ws://127.0.0.1:9001",
   "outdir": "./reports/clients",
   "webport": 8080,
   "cases": ["*"],
   "exclude-cases": [],
   "exclude-agent-cases": {}
}
"""

SPEC_FUZZINGCLIENT = """
{
   "outdir": "./reports/servers",
   "servers": [
                  {
                     "agent": "AutobahnPython",
                     "url": "ws://127.0.0.1:9001"
                  }
              ],
   "cases": ["*"],
   "exclude-cases": [],
   "exclude-agent-cases": {}
}
"""

SPEC_FUZZINGWAMPSERVER = """
{
   "url": "ws://127.0.0.1:9001",

   "options": {},
   "outdir": "./reports/wampclients",

   "cases": ["*"],
   "exclude-cases": [],
   "exclude-agent-cases": {}
}
"""

SPEC_FUZZINGWAMPCLIENT = """
{
   "options": {},
   "outdir": "./reports/wampservers",

   "testees": [
                  {
                     "name": "AutobahnPython",
                     "url": "ws://127.0.0.1:9001",
                     "options": {},
                     "auth": null
                  }
               ],

   "cases": ["*"],
   "exclude-cases": [],
   "exclude-agent-cases": {}
}
"""

SPEC_WSPERFCONTROL = """
{
   "options": {
      "debug": false
   },
   "servers":  [
                  {
                     "name": "AutobahnPython",
                     "uri": "ws://127.0.0.1:9000",
                     "desc": "Autobahn WebSocket Python on localhost"
                  }
               ],
   "testsets": [
      {
         "mode": "echo",
         "options": {
            "outfile": "report_echo.txt",
            "digits": 0,
            "sep": "\\t",
            "rtts": false,
            "quantile_count": 10,

            "count": 1000,
            "timeout": 100000,
            "binary": false,
            "sync": true,
            "verify": false
         },
         "cases": [
                     {"size": 0},
                     {"size": 64},
                     {"size": 1024},
                     {"count": 100, "size": 524288}
                  ]
      }
   ]
}
"""

SPEC_MASSCONNECT = """
{
   "options": {
      "connections": 10000,
      "batchsize": 100,
      "batchdelay": 10,
      "retrydelay": 10
   },
   "servers":  [
                  {
                     "name": "AutobahnPython",
                     "uri": "ws://127.0.0.1:9000",
                     "desc": "Autobahn WebSocket Python on localhost"
                  }
               ]
}
"""

########NEW FILE########
__FILENAME__ = testdb
###############################################################################
##
##  Copyright 2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ("TestDb",)

import os, sys
import types
import sqlite3
import json

from zope.interface import implementer

from twisted.python import log
from twisted.enterprise import adbapi
from twisted.internet.defer import Deferred

from autobahn.util import utcnow, newid
from autobahn.wamp import exportRpc

from interfaces import ITestDb
from rinterfaces import RITestDb
from testrun import TestResult
from util import envinfo


@implementer(ITestDb)
@implementer(RITestDb)
class TestDb:
   """
   sqlite3 based test database implementing ITestDb. Usually, a single
   instance exists application wide (singleton). Test runners store their
   test results in the database and report generators fetch test results
   from the database. This allows to decouple application parts.
   """

   URI = "http://api.testsuite.autobahn.ws/testdb/"


   def __init__(self, caseSets, dbfile = None, debug = False):

      self._debug = debug
      self.dispatch = None

      if not dbfile:
         dbfile = ".wstest.db"

      self._dbfile = os.path.abspath(dbfile)
      if not os.path.isfile(self._dbfile):
         self._createDb()
      else:
         self._checkDb()

      self._dbpool = adbapi.ConnectionPool('sqlite3',
                                           self._dbfile,
                                           check_same_thread = False # http://twistedmatrix.com/trac/ticket/3629
                                          )

      self._caseSets = caseSets
      self._initCaseSets()


   def _initCaseSets(self):
      self._cs = {}
      self._css = {}
      for cs in self._caseSets:
         if not self._cs.has_key(cs.CaseSetName):
            self._cs[cs.CaseSetName] = {}
            self._css[cs.CaseSetName] = cs
         else:
            raise Exception("duplicate case set name")
         for c in cs.Cases:
            idx = tuple(c.index)
            if not self._cs[cs.CaseSetName].has_key(idx):
               self._cs[cs.CaseSetName][idx] = c
            else:
               raise Exception("duplicate case index")


   def _createDb(self):
      log.msg("creating test database at %s .." % self._dbfile)
      db = sqlite3.connect(self._dbfile)
      cur = db.cursor()

      cur.execute("""
                  CREATE TABLE testspec (
                     id                TEXT     PRIMARY KEY,
                     before_id         TEXT,
                     valid_from        TEXT     NOT NULL,
                     valid_to          TEXT,
                     name              TEXT     NOT NULL,
                     desc              TEXT,
                     mode              TEXT     NOT NULL,
                     caseset           TEXT     NOT NULL,
                     spec              TEXT     NOT NULL)
                  """)

      cur.execute("""
                  CREATE UNIQUE INDEX
                     idx_testspec_name_valid_to
                        ON testspec (name, valid_to)
                  """)

      cur.execute("""
                  CREATE TABLE testrun (
                     id                TEXT     PRIMARY KEY,
                     testspec_id       TEXT     NOT NULL,
                     env               TEXT     NOT NULL,
                     started           TEXT     NOT NULL,
                     ended             TEXT)
                  """)

      cur.execute("""
                  CREATE TABLE testresult (
                     id                TEXT     PRIMARY KEY,
                     testrun_id        TEXT     NOT NULL,
                     inserted          TEXT     NOT NULL,
                     testee            TEXT     NOT NULL,
                     c1                INTEGER  NOT NULL,
                     c2                INTEGER  NOT NULL,
                     c3                INTEGER  NOT NULL,
                     c4                INTEGER  NOT NULL,
                     c5                INTEGER  NOT NULL,
                     duration          REAL     NOT NULL,
                     passed            INTEGER  NOT NULL,
                     result            TEXT     NOT NULL)
                  """)

      cur.execute("""
                  CREATE TABLE testlog (
                     testresult_id     TEXT     NOT NULL,
                     lineno            INTEGER  NOT NULL,
                     timestamp         REAL     NOT NULL,
                     sessionidx        INTEGER,
                     sessionid         TEXT,
                     line              TEXT     NOT NULL,
                     PRIMARY KEY (testresult_id, lineno))
                  """)

      ## add: testee, testcase, testspec?


   def _checkDb(self):
      ## FIXME
      pass


   def newRun(self, specId):

      def do(txn):
         txn.execute("SELECT mode FROM testspec WHERE id = ? AND valid_to IS NULL", [specId])
         res = txn.fetchone()
         if res is None:
            raise Exception("no such spec or spec not active")

         mode = res[0]
         if not mode in ITestDb.TESTMODES:
            raise Exception("mode '%s' invalid or not implemented" % mode)

         id = newid()
         now = utcnow()
         env = envinfo()
         txn.execute("INSERT INTO testrun (id, testspec_id, env, started) VALUES (?, ?, ?, ?)", [id, specId, json.dumps(env), now])
         return id

      return self._dbpool.runInteraction(do)


   def closeRun(self, runId):

      def do(txn):
         now = utcnow()

         ## verify that testrun exists and is not closed already
         ##
         txn.execute("SELECT started, ended FROM testrun WHERE id = ?", [runId])
         res = txn.fetchone()
         if res is None:
            raise Exception("no such test run")
         if res[1] is not None:
            raise Exception("test run already closed")

         ## close test run
         ##
         txn.execute("UPDATE testrun SET ended = ? WHERE id = ?", [now, runId])

      return self._dbpool.runInteraction(do)


   def generateCasesByTestee(self, specId):

      def do(txn):

         txn.execute("SELECT valid_to, mode, caseset, spec FROM testspec WHERE id = ?", [specId])
         row = txn.fetchone()

         if row is None:
            raise Exception("no test specification with ID '%s'" % specId)
         else:
            validTo, mode, caseset, spec = row
            if validTo is not None:
               raise Exception("test spec no longer active")
            if not self._css.has_key(caseset):
               raise Exception("case set %s not loaded in database" % caseset)
            spec = json.loads(spec)
            res = self._css[caseset].generateCasesByTestee(spec)
            return res

      return self._dbpool.runInteraction(do)


   def saveResult(self, runId, testRun, testCase, result, saveLog = True):

      def do(txn):
         ## verify that testrun exists and is not closed already
         ##
         txn.execute("SELECT started, ended FROM testrun WHERE id = ?", [runId])
         res = txn.fetchone()
         if res is None:
            raise Exception("no such test run")
         if res[1] is not None:
            raise Exception("test run already closed")

         ## save test case results with foreign key to test run
         ##
         id = newid()
         now = utcnow()

         ci = []
         for i in xrange(5):
            if len(testCase.index) > i:
               ci.append(testCase.index[i])
            else:
               ci.append(0)

         if saveLog:
            log = result.log
         else:
            log = []
         result.log = None

         resultData = result.serialize()

         txn.execute("""
            INSERT INTO testresult
               (id, testrun_id, inserted, testee, c1, c2, c3, c4, c5, duration, passed, result)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
               id,
               runId,
               now,
               testRun.testee.name,
               ci[0],
               ci[1],
               ci[2],
               ci[3],
               ci[4],
               result.ended - result.started,
               1 if result.passed else 0,
               resultData])

         ## save test case log with foreign key to test result
         ##
         if log:
            lineno = 1
            for l in log:
               txn.execute("""
                  INSERT INTO testlog
                     (testresult_id, lineno, timestamp, sessionidx, sessionid, line)
                        VALUES (?, ?, ?, ?, ?, ?)
                  """, [
                  id,
                  lineno,
                  l[0],
                  l[1],
                  l[2],
                  l[3]])
               lineno += 1

         return id

      return self._dbpool.runInteraction(do)


   def _checkTestSpec(self, spec):
      if type(spec) != dict:
         raise Exception("test spec must be a dict")

      sig_spec = {'name': (True, [str, unicode]),
                  'desc': (False, [str, unicode]),
                  'mode': (True, [str, unicode]),
                  'caseset': (True, [str, unicode]),
                  'cases': (True, [list]),
                  'exclude': (False, [list]),
                  'options': (False, [dict]),
                  'testees': (True, [list])}

      sig_spec_modes = ['fuzzingwampclient']
      sig_spec_casesets = ['wamp']

      sig_spec_options = {'rtt': (False, [int, float]),
                          'randomize': (False, [bool]),
                          'parallel': (False, [bool])}

      sig_spec_testee = {'name': (True, [str, unicode]),
                         'desc': (False, [str, unicode]),
                         'url': (True, [str, unicode]),
                         'auth': (False, [dict]),
                         'exclude': (False, [list]),
                         'options': (False, [dict])}

      sig_spec_testee_auth = {'authKey': (True, [str, unicode, types.NoneType]),
                              'authSecret': (False, [str, unicode, types.NoneType]),
                              'authExtra': (False, [dict])}

      sig_spec_testee_options = {'rtt': (False, [int, float]),
                                'randomize': (False, [bool])}


      def verifyDict(obj, sig, signame):
         for att in obj:
            if att not in sig.keys():
               raise Exception("invalid attribute '%s' in %s" % (att, signame))

         for key, (required, atypes) in sig.items():
            if required and not obj.has_key(key):
               raise Exception("missing mandatory %s attribute '%s'" % (signame, key))
            if obj.has_key(key) and type(obj[key]) not in atypes:
               raise Exception("invalid type '%s' for %s attribute '%s'" % (type(sig[key]), signame, key))

      verifyDict(spec, sig_spec, 'test specification')
      if spec.has_key('options'):
         verifyDict(spec['options'], sig_spec_options, 'test options')

      for testee in spec['testees']:
         verifyDict(testee, sig_spec_testee, 'testee description')

         if testee.has_key('auth'):
            verifyDict(testee['auth'], sig_spec_testee_auth, 'testee authentication credentials')

         if testee.has_key('options'):
            verifyDict(testee['options'], sig_spec_testee_options, 'testee options')

      if spec['mode'] not in sig_spec_modes:
         raise Exception("invalid mode '%s' in test specification" % spec['mode'])

      if spec['caseset'] not in sig_spec_casesets:
         raise Exception("invalid caseset '%s' in test specification" % spec['caseset'])


   @exportRpc
   def importSpec(self, spec):

      self._checkTestSpec(spec)

      name = spec['name']
      mode = spec['mode']
      caseset = spec['caseset']
      desc = spec.get('desc', None)

      def do(txn):
         data = json.dumps(spec, ensure_ascii = False, allow_nan = False, separators = (',', ':'), indent = None)

         now = utcnow()
         id = newid()

         txn.execute("SELECT id, spec FROM testspec WHERE name = ? AND valid_to IS NULL", [name])
         res = txn.fetchone()
         op = None

         if res is not None:
            currId, currSpec = res
            if currSpec == data:
               return (op, currId, name)
            else:
               beforeId = currId
               op = 'U'
               txn.execute("UPDATE testspec SET valid_to = ? WHERE id = ?", [now, currId])
         else:
            beforeId = None
            op = 'I'

         txn.execute("INSERT INTO testspec (id, before_id, valid_from, name, desc, mode, caseset, spec) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [id, beforeId, now, name, desc, mode, caseset, data])
         return (op, id, name)

      return self._dbpool.runInteraction(do)


   @exportRpc
   def getSpecs(self, activeOnly = True):

      def do(txn):

         if activeOnly:
            txn.execute("""
               SELECT id, before_id, valid_from, valid_to, name, desc, mode, caseset
                  FROM testspec WHERE valid_to IS NULL ORDER BY name ASC""")
         else:
            txn.execute("""
               SELECT id, before_id, valid_from, valid_to, name, desc, mode, caseset
                  FROM testspec ORDER BY name ASC, valid_from DESC""")

         res = []
         for row in txn.fetchall():
            o = {'id': row[0],
                 'beforeId': row[1],
                 'validFrom': row[2],
                 'validTo': row[3],
                 'name': row[4],
                 'desc': row[5],
                 'mode': row[6],
                 'caseset': row[7]
                 }
            res.append(o)

         return res

      return self._dbpool.runInteraction(do)


   @exportRpc
   def getSpec(self, specId): # Status: OK.

      def do(txn):

         txn.execute("SELECT spec FROM testspec WHERE id = ?", [specId])
         res = txn.fetchone()

         if res is None:
            raise Exception("no test specification with ID '%s'" % specId)
         else:
            return json.loads(res[0])

      return self._dbpool.runInteraction(do)


   @exportRpc
   def getSpecByName(self, specName): # Status: OK.

      def do(txn):

         txn.execute("SELECT id, spec FROM testspec WHERE name = ? AND valid_to IS NULL", [specName])
         res = txn.fetchone()

         if res is None:
            raise Exception("no (active) test specification with name '%s'" % specName)
         else:
            id, data = res
            return (id, json.loads(data))

      return self._dbpool.runInteraction(do)


   @exportRpc
   def getTestRuns(self, limit = 10):

      def do(txn):

         txn.execute("""
            SELECT r.id, s.id, s.name, s.mode, s.caseset, r.started, r.ended, e.testee_count, e.testee_failed_count, e.passed, e.total
               FROM testrun r
                  INNER JOIN testspec s ON r.testspec_id = s.id
                     LEFT JOIN (
                        SELECT testrun_id,
                               COUNT(DISTINCT testee) testee_count,
                               COUNT(DISTINCT (CASE WHEN passed = 0 THEN testee ELSE NULL END)) testee_failed_count,
                               SUM(passed) AS passed,
                               COUNT(*) AS total
                           FROM testresult x
                              GROUP BY testrun_id) e ON r.id = e.testrun_id
               ORDER BY r.started DESC LIMIT ?""", [limit])

         res = []
         for row in txn.fetchall():
            o = {'id': row[0],
                 'specId':row[1],
                 'specName':row[2],
                 'runMode': row[3],
                 'caseSetName': row[4],
                 'started': row[5],
                 'ended': row[6],
                 'testeeCount': row[7],
                 'testeeFailedCount': row[8],
                 'passed': row[9],
                 'total': row[10]
                 }
            res.append(o)

         return res

      return self._dbpool.runInteraction(do)


   @exportRpc
   def getTestResult(self, resultId):

      def do(txn):
         txn.execute("SELECT id, testrun_id, testee, c1, c2, c3, c4, c5, passed, duration, result FROM testresult WHERE id = ?", [resultId])
         res = txn.fetchone()
         if res is None:
            raise Exception("no such test result")
         id, runId, testeeName, c1, c2, c3, c4, c5, passed, duration, data = res

         caseName = "WampCase" + '.'.join([str(x) for x in [c1, c2, c3, c4, c5]])

         result = TestResult()
         result.deserialize(data)
         result.id, result.runId, result.testeeName, result.caseName = id, runId, testeeName, caseName

         idx = (c1, c2, c3, c4)
         caseKlass = self._cs['wamp'][idx]
         #print caseName, idx, caseKlass
         result.description = caseKlass.description
         result.expectation = caseKlass.expectation

         result.log = []
         txn.execute("SELECT timestamp, sessionidx, sessionid, line FROM testlog WHERE testresult_id = ? ORDER BY lineno ASC", [result.id])
         for l in txn.fetchall():
            result.log.append(l)

         return result

      return self._dbpool.runInteraction(do)


   @exportRpc
   def getTestRunIndex(self, runId):

      def do(txn):
         txn.execute("""
            SELECT r.id, r.testee, r.c1, r.c2, r.c3, r.c4, r.c5, r.passed, r.duration,
                   rr.started, rr.ended,
                   s.id AS spec_id, s.name AS spec_name, s.mode, s.caseset
               FROM testresult r
                  INNER JOIN testrun rr ON r.testrun_id = rr.id
                     INNER JOIN testspec s ON rr.testspec_id = s.id
               WHERE r.testrun_id = ?
         """, [runId])

         res = {}
         for row in txn.fetchall():

            index = (row[2], row[3], row[4], row[5], row[6])

            id, testee, passed, duration = row[0], row[1], row[7], row[8]

            if not res.has_key(index):
               res[index] = {}

            if res[index].has_key(testee):
               raise Exception("logic error")

            res[index][testee] = {'id': id, 'passed': passed, 'duration': duration}

         sres = []
         for index in sorted(res.keys()):
            sres.append({'index': list(index),  'results': res[index]})

         return sres

      return self._dbpool.runInteraction(do)


   @exportRpc
   def getTestRunSummary(self, runId):

      def do(txn):

         ## verify that testrun exists and is not closed already
         ##
         txn.execute("SELECT started, ended FROM testrun WHERE id = ?", [runId])
         res = txn.fetchone()
         if res is None:
            raise Exception("no such test run")
         if res[1] is None:
            print "Warning: test run not closed yet"

         txn.execute("SELECT testee, SUM(passed), COUNT(*) FROM testresult WHERE testrun_id = ? GROUP BY testee", [runId])
         res = txn.fetchall()
         r = {}
         for row in res:
            testee, passed, count = row
            r[testee] = {'name': testee,
                         'passed': passed,
                         'failed': count - passed,
                         'count': count}
         return [r[k] for k in sorted(r.keys())]

      return self._dbpool.runInteraction(do)

########NEW FILE########
__FILENAME__ = testee
###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ['startClient', 'startServer']


from twisted.internet import reactor

import autobahn

from autobahn.twisted.websocket import connectWS, listenWS

from autobahn.twisted.websocket import WebSocketClientFactory, \
                                       WebSocketClientProtocol

from autobahn.twisted.websocket import WebSocketServerFactory, \
                                       WebSocketServerProtocol

from autobahn.websocket.compress import *



class TesteeServerProtocol(WebSocketServerProtocol):

   def onMessage(self, payload, isBinary):
      self.sendMessage(payload, isBinary)


class StreamingTesteeServerProtocol(WebSocketServerProtocol):

   def onMessageBegin(self, isBinary):
      #print "onMessageBegin"
      WebSocketServerProtocol.onMessageBegin(self, isBinary)
      self.beginMessage(isBinary = isBinary)

   def onMessageFrameBegin(self, length):
      #print "onMessageFrameBegin"
      WebSocketServerProtocol.onMessageFrameBegin(self, length)
      self.beginMessageFrame(length)

   def onMessageFrameData(self, data):
      #print "onMessageFrameData", len(data)
      self.sendMessageFrameData(data)

   def onMessageFrameEnd(self):
      #print "onMessageFrameEnd"
      pass

   def onMessageEnd(self):
      #print "onMessageEnd"
      self.endMessage()


class TesteeServerFactory(WebSocketServerFactory):

   protocol = TesteeServerProtocol
   #protocol = StreamingTesteeServerProtocol

   def __init__(self, url, debug = False, ident = None):
      if ident is not None:
         server = ident
      else:
         server = "AutobahnPython/%s" % autobahn.version
      WebSocketServerFactory.__init__(self, url, debug = debug, debugCodePaths = debug, server = server)
      self.setProtocolOptions(failByDrop = False) # spec conformance
      #self.setProtocolOptions(failByDrop = True) # needed for streaming mode
      #self.setProtocolOptions(utf8validateIncoming = False)

      ## enable permessage-XXX compression extensions
      ##
      def accept(offers):
         for offer in offers:
            if isinstance(offer, PerMessageDeflateOffer):
               return PerMessageDeflateOfferAccept(offer)

            elif isinstance(offer, PerMessageBzip2Offer):
               return PerMessageBzip2OfferAccept(offer)

            elif isinstance(offer, PerMessageSnappyOffer):
               return PerMessageSnappyOfferAccept(offer)

      self.setProtocolOptions(perMessageCompressionAccept = accept)



class TesteeClientProtocol(WebSocketClientProtocol):

   def onOpen(self):
      if self.factory.endCaseId is None:
         print "Getting case count .."
      elif self.factory.currentCaseId <= self.factory.endCaseId:
         print "Running test case %d/%d as user agent %s on peer %s" % (self.factory.currentCaseId, self.factory.endCaseId, self.factory.agent, self.peer)

   def onMessage(self, msg, binary):
      if self.factory.endCaseId is None:
         self.factory.endCaseId = int(msg)
         print "Ok, will run %d cases" % self.factory.endCaseId
      else:
         self.sendMessage(msg, binary)



class TesteeClientFactory(WebSocketClientFactory):

   protocol = TesteeClientProtocol

   def __init__(self, url, debug = False, ident = None):
      WebSocketClientFactory.__init__(self, url, useragent = ident, debug = debug, debugCodePaths = debug)
      self.setProtocolOptions(failByDrop = False) # spec conformance

      ## enable permessage-XXX compression extensions
      ##
      offers = [PerMessageDeflateOffer()]
      #offers = [PerMessageSnappyOffer(), PerMessageBzip2Offer(), PerMessageDeflateOffer()]
      self.setProtocolOptions(perMessageCompressionOffers = offers)

      def accept(response):
         if isinstance(response, PerMessageDeflateResponse):
            return PerMessageDeflateResponseAccept(response)

         elif isinstance(response, PerMessageBzip2Response):
            return PerMessageBzip2ResponseAccept(response)

         elif isinstance(response, PerMessageSnappyResponse):
            return PerMessageSnappyResponseAccept(response)

      self.setProtocolOptions(perMessageCompressionAccept = accept)


      self.endCaseId = None
      self.currentCaseId = 0

      self.updateReports = True
      if ident is not None:
         self.agent = ident
      else:
         self.agent = "AutobahnPython/%s" % autobahn.version
      self.resource = "/getCaseCount"

   def clientConnectionLost(self, connector, reason):
      self.currentCaseId += 1
      if self.currentCaseId <= self.endCaseId:
         self.resource = "/runCase?case=%d&agent=%s" % (self.currentCaseId, self.agent)
         connector.connect()
      elif self.updateReports:
         self.resource = "/updateReports?agent=%s" % self.agent
         self.updateReports = False
         connector.connect()
      else:
         reactor.stop()

   def clientConnectionFailed(self, connector, reason):
      print "Connection to %s failed (%s)" % (self.url, reason.getErrorMessage())
      reactor.stop()



def startClient(wsuri, ident = None, debug = False):
   factory = TesteeClientFactory(wsuri, ident = ident, debug = debug)
   connectWS(factory)
   return True



def startServer(wsuri, sslKey = None, sslCert = None, debug = False):
   factory = TesteeServerFactory(wsuri, debug)
   if sslKey and sslCert:
      sslContext = ssl.DefaultOpenSSLContextFactory(sslKey, sslCert)
   else:
      sslContext = None
   listenWS(factory, sslContext)
   return True

########NEW FILE########
__FILENAME__ = testrun
###############################################################################
##
##  Copyright 2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ("TestRun", "Testee", "TestResult",)


import random
from collections import deque

from zope.interface import implementer
from interfaces import ITestRun

from util import AttributeBag


class Testee(AttributeBag):

   ATTRIBUTES = ['id',
                 'name',
                 'url',
                 'auth',
                 'options',
                 'debug']



class TestResult(AttributeBag):

   ATTRIBUTES = ['id',
                 'runId',
                 'passed',
                 'description',
                 'expectation',
                 'expected',
                 'observed',
                 'log',
                 'started',
                 'ended']


@implementer(ITestRun)
class TestRun:
   """
   A TestRun contains an ordered sequence of test case classes.
   A test runner instantiates tests from these test case classes.
   The test case classes must derive from WampCase or Case.
   """

   def __init__(self, testee, cases, randomize = False):
      assert(isinstance(testee, Testee))
      self.testee = testee
      _cases = cases[:]
      if randomize:
         random.shuffle(_cases)
      _cases.reverse()
      self._len = len(_cases)
      self._cases = deque(_cases)

   def next(self):
      try:
         return self._cases.pop()
      except IndexError:
         return None

   def remaining(self):
      return len(self._cases)

   def __len__(self):
      return self._len;

########NEW FILE########
__FILENAME__ = test_wamptestee
from twisted.trial import unittest
from autobahntestsuite import wamptestee
import types
import datetime


class TestEchoService(unittest.TestCase):
    """
    This test case checks if the echo service behaves as expected.
    """
    
    def setUp(self):
        self.echo_service = wamptestee.EchoService()

        
    def testEcho(self):
        """
        The echo service should echo received parameters correctly,
        regardless of their type.
        """
        for val in ["Hallo", 5, -1000, datetime.datetime.now(), True]:
            self.assertEquals(self.echo_service.echo(val), val)


            
class TestStringService(unittest.TestCase):
    """
    This test case checks if the string service behaves as expected.
    """

    
    def setUp(self):
        self.string_service = wamptestee.StringService()

        
    def testConcat(self):
        """
        The string service should concatenate strings correctly.
        """
        self.assertEquals(self.string_service.concat("a", "b"), "ab")
        self.assertEquals(self.string_service.concat("", "xxx"), "xxx")
        self.assertEquals(self.string_service.concat("", ""), "")


class TestNumberService(unittest.TestCase):
    """
    This test case checks if the number service behaves as expected.
    """

    def setUp(self):
        self.number_service = wamptestee.NumberService()


    def testAddIntegers(self):
        """
        The number service should add integers correctly.
        """
        self.assertEquals(self.number_service.add(1, 2, 3), 6)
        self.assertEquals(self.number_service.add(5, 0), 5)

    def testAddFloats(self):
        """
        The number service should add floats correctly.
        """
        # Use assertAlmostEquals to handle the (inevitable) rounding error.
        self.assertAlmostEquals(self.number_service.add(1.3, 2.9, 3.6), 7.8)
        self.assertEquals(self.number_service.add(5.3, 0.0), 5.3)

    def testAddingSingleNumber(self):
        """
        The number service should raise an assertion error if one
        tries to add just one number.
        """
        self.assertRaises(AssertionError, self.number_service.add, 5)

    def testAddStringToNumber(self):
        """
        The number service should raise an assertion error if one
        tries to add a string to a number.
        """
        self.assertRaises(AssertionError, self.number_service.add,
                          1, "5")


class TestTesteeWampServer(unittest.TestCase):
    """
    This test case checks if the testee WAMP server protocol behaves
    as expected.
    """

    
    def setUp(self):
        self.testee = wamptestee.TesteeWampServerProtocol()
        self.testee.debugWamp = True # mock setup of debugWamp
        self.testee.procs = {} # mock setup of `procs` attribute
        self.testee.initializeServices()


    def testAttributeSetup(self):
        self.failUnless(hasattr(self.testee, "echo_service"),
                        "Attribute `echo_service` is missing.")
        self.assertEquals(self.testee.echo_service.__class__,
                          wamptestee.EchoService)
        self.failUnless(hasattr(self.testee, "string_service"),
                        "Attribute `string_service` is missing.")
        self.assertEquals(self.testee.string_service.__class__,
                          wamptestee.StringService)


    def testRegistrations(self):
        for case_number in [wamptestee.ECHO_NUMBER_ID,
                            wamptestee.ECHO_STRING_ID]:
            for idx in range(1, 5):
                self._checkUriSetup(wamptestee.EchoService, case_number, idx)
        self._checkUriSetup(wamptestee.EchoService,
                            wamptestee.ECHO_DATE_ID)
        self._checkUriSetup(wamptestee.StringService,
                            wamptestee.CONCAT_STRINGS_ID)
        self._checkUriSetup(wamptestee.NumberService,
                            wamptestee.ADD_TWO_NUMBERS_ID)
        self._checkUriSetup(wamptestee.NumberService,
                            wamptestee.ADD_THREE_NUMBERS_ID)


    def _checkUriSetup(self, service_cls, case_number, ref=None):
        uri = wamptestee.setupUri(case_number, ref)
        self.failUnless(uri in self.testee.procs)
        service, method, flag = self.testee.procs[uri]
        self.failUnless(isinstance(service, service_cls))
        self.assertEquals(type(method), types.MethodType)
        self.assertEquals(flag, False)

########NEW FILE########
__FILENAME__ = util
###############################################################################
##
##  Copyright 2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ("AttributeBag", "Tabify", "perf_counter", )


import json, platform, sys
from datetime import datetime

from twisted.python import log

import autobahn
import autobahntestsuite
from autobahn.websocket.utf8validator import Utf8Validator
from autobahn.websocket.xormasker import XorMaskerNull



# http://docs.python.org/dev/library/time.html#time.perf_counter
# http://www.python.org/dev/peps/pep-0418/
# until time.perf_counter becomes available in Python 2 we do:
import time
if not hasattr(time, 'perf_counter'):
   import os
   if os.name == 'nt':
      perf_counter = time.clock
   else:
      perf_counter = time.time
else:
   perf_counter = time.perf_counter


class AttributeBag:

   def __init__(self, **args):

      for attr in self.ATTRIBUTES:
         setattr(self, attr, None)

      self.set(args)


   def serialize(self):
      obj = {}
      for attr in self.ATTRIBUTES:
         obj[attr] = getattr(self, attr)
      return json.dumps(obj)


   def deserialize(self, data):
      obj = json.loads(data)
      self.set(obj)


   def set(self, obj):
      for attr in obj.keys():
         if attr in self.ATTRIBUTES:
            setattr(self, attr, obj[attr])
         else:
            if self.debug:
               log.msg("Warning: skipping unknown attribute '%s'" % attr)


   def __repr__(self):
      s = []
      for attr in self.ATTRIBUTES:
         s.append("%s = %s" % (attr, getattr(self, attr)))
      return self.__class__.__name__ + '(' + ', '.join(s) + ')'


class Tabify:

   def __init__(self, formats, truncate = 120, filler = ['-', '+']):
      self._formats = formats
      self._truncate = truncate
      self._filler = filler


   def tabify(self, fields = None):
      """
      Tabified output formatting.
      """

      ## compute total length of all fields
      ##
      totalLen = 0
      flexIndicators = 0
      flexIndicatorIndex = None
      for i in xrange(len(self._formats)):
         ffmt = self._formats[i][1:]
         if ffmt != "*":
            totalLen += int(ffmt)
         else:
            flexIndicators += 1
            flexIndicatorIndex = i

      if flexIndicators > 1:
         raise Exception("more than 1 flex field indicator")

      ## reserve space for column separators (" | " or " + ")
      ##
      totalLen += 3 * (len(self._formats) - 1)

      if totalLen > self._truncate:
         raise Exception("cannot fit content in truncate length %d" % self._truncate)

      r = []
      for i in xrange(len(self._formats)):

         if i == flexIndicatorIndex:
            N = self._truncate - totalLen
         else:
            N = int(self._formats[i][1:])

         if fields:
            s = str(fields[i])
            if len(s) > N:
               s = s[:N-2] + ".."
            l = N - len(s)
            m = self._formats[i][0]
         else:
            s = ''
            l = N
            m = '+'

         if m == 'l':
            r.append(s + ' ' * l)
         elif m == 'r':
            r.append(' ' * l + s)
         elif m == 'c':
            c1 = l / 2
            c2 = l - c1
            r.append(' ' * c1 + s + ' ' * c2)
         elif m == '+':
            r.append(self._filler[0] * l)
         else:
            raise Exception("invalid field format")

      if m == '+':
         return (self._filler[0] + self._filler[1] + self._filler[0]).join(r)
      else:
         return ' | '.join(r)


def envinfo():

   res = {}

   res['platform'] = {'hostname': platform.node(),
                      'os': platform.platform()}

   res['python'] = {'version': platform.python_version(),
                    'implementation': platform.python_implementation(),
                    'versionVerbose': sys.version.replace('\n', ' ')}

   res['twisted'] = {'version': None, 'reactor': None}
   try:
      import pkg_resources
      res['twisted']['version'] = pkg_resources.require("Twisted")[0].version
   except:
      ## i.e. no setuptools installed ..
      pass
   try:
      from twisted.internet import reactor
      res['twisted']['reactor'] = str(reactor.__class__.__name__)
   except:
      pass

   v1 = str(Utf8Validator)
   v1 = v1[v1.find("'")+1:-2]

   v2 = str(XorMaskerNull)
   v2 = v2[v2.find("'")+1:-2]

   res['autobahn'] = {'version': autobahn.version,
                      'utf8Validator': v1,
                      'xorMasker': v2,
                      'jsonProcessor': '%s-%s' % (autobahn.wamp.json_lib.__name__, autobahn.wamp.json_lib.__version__)}

   res['autobahntestsuite'] = {'version': autobahntestsuite.version}

   return res




# http://stackoverflow.com/a/1551394/192791
def pprint_timeago(time = False):
   now = datetime.utcnow()
   if type(time) is int:
      diff = now - datetime.fromtimestamp(time)
   elif isinstance(time, datetime):
      diff = now - time
   elif not time:
      diff = now - now

   second_diff = diff.seconds
   day_diff = diff.days
   if day_diff < 0:
      return ''

   if day_diff == 0:
      if second_diff < 10:
         return "just now"
      if second_diff < 60:
         return str(second_diff) + " seconds ago"
      if second_diff < 120:
         return "a minute ago"
      if second_diff < 3600:
         return str( second_diff / 60 ) + " minutes ago"
      if second_diff < 7200:
         return "an hour ago"
      if second_diff < 86400:
         return str( second_diff / 3600 ) + " hours ago"
   if day_diff == 1:
      return "Yesterday"
   if day_diff < 7:
      return str(day_diff) + " days ago"
   if day_diff < 31:
      return str(day_diff/7) + " weeks ago"
   if day_diff < 365:
      return str(day_diff/30) + " months ago"
   return str(day_diff/365) + " years ago"



# Help string to be presented if the user wants to use an encrypted connection
# but didn't specify key and / or certificate
OPENSSL_HELP = """
Server key and certificate required for WSS
To generate server test key/certificate:

openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr
openssl x509 -req -days 3650 -in server.csr -signkey server.key -out server.crt

Then start wstest:

wstest -m echoserver -w wss://localhost:9000 -k server.key -c server.crt
"""


def _createWssContext(self, options, factory):
   """Create an SSL context factory for WSS connections.
   """

   if not factory.isSecure:
      return None

   # Check if an OpenSSL library can be imported; abort if it's missing.
   try:
      from twisted.internet import ssl
   except ImportError, e:
      print ("You need OpenSSL/pyOpenSSL installed for secure WebSockets"
             "(wss)!")
      sys.exit(1)

   # Make sure the necessary options ('key' and 'cert') are available
   if options['key'] is None or options['cert'] is None:
      print OPENSSL_HELP
      sys.exit(1)

   # Create the context factory based on the given key and certificate
   key = str(options['key'])
   cert = str(options['cert'])
   return ssl.DefaultOpenSSLContextFactory(key, cert)

########NEW FILE########
__FILENAME__ = wampcase
###############################################################################
##
##  Copyright 2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ('WampCase', 'WampCaseProtocol', 'WampCaseFactory',)


import json, random

from zope.interface import implementer

from twisted.internet import reactor
from twisted.internet.defer import Deferred, DeferredList, maybeDeferred

from autobahn.twisted.websocket import connectWS
from autobahn.wamp import WampClientFactory, WampCraClientProtocol

from autobahntestsuite.testrun import TestResult
from autobahntestsuite.util import AttributeBag, perf_counter
from autobahntestsuite.interfaces import ITestCase



class WampCaseProtocol(WampCraClientProtocol):


   def sendMessage(self, payload):
      self.factory.log('<pre class="wamp">TX => %s</pre>' % payload)
      WampCraClientProtocol.sendMessage(self, payload)


   def onMessage(self, payload, binary):
      self.factory.log('<pre class="wamp">RX <= %s</pre>' % payload)
      WampCraClientProtocol.onMessage(self, payload, binary)


   def onSessionOpen(self):
      self.factory.log("WAMP session opened to <strong>%s</strong> at <strong>%s</strong>." % (self.session_server, self.peer))

      self.factory.result.observed[self.session_id] = []

      if self.factory.test.testee.auth:
         d = self.authenticate(**self.factory.test.testee.auth)
         d.addCallbacks(self.onAuthSuccess, self.onAuthError)
      else:
         self.test()


   def onAuthSuccess(self, permissions):
      self.factory.log("WAMP session %s authenticated with credentials: <pre>%s</pre>" % (self.session_id, self.factory.test.testee.auth))
      self.test()


   def onAuthError(self, e):
      uri, desc, details = e.value.args
      self.factory.log("WAMP authentication error: %s" % details)
      self.sendClose()


   def test(self):
      raise Exception("not implemented")


   def ready(self):
      self.factory.log("Test client prepared and ready.")
      self.factory.onReady.callback(self.session_id)


   def onEvent(self, topic, event):
      self.factory.log("Received event for topic <pre>%s</pre> and payload <pre>%s</pre>" % (topic, event))
      self.factory.result.observed[self.session_id].append((topic, event))


class WampCaseParams(AttributeBag):
   """
   """

   ATTRIBUTES = ['peerCount']


class WampCaseFactory(WampClientFactory):

   protocol = None

   def __init__(self, peerIndex, onReady, onGone, test, result):
      assert(self.protocol)
      WampClientFactory.__init__(self, test.testee.url)
      self.peerIndex = peerIndex
      self.onReady = onReady
      self.onGone = onGone
      self.test = test
      self.result = result
      self.proto = None

   def buildProtocol(self, addr):
      proto = self.protocol()
      proto.factory = self
      proto.session_id = None
      self.proto = proto
      return proto

   def log(self, msg):
      ts = perf_counter()
      sessionId = self.proto.session_id if self.proto else None
      self.result.log.append((ts, self.peerIndex, sessionId, msg.encode('utf8')))
      return ts

   def clientConnectionLost(self, connector, reason):
      reason = str(reason.value)
      self.log("Client connection lost: %s" % reason)
      self.onGone.callback(None)

   def clientConnectionFailed(self, connector, reason):
      reason = str(reason.value)
      self.log("Client connection failed: %s" % reason)
      self.onGone.callback(reason)



@implementer(ITestCase)
class WampCase:

   factory = None
   index = None
   description = None
   expectation = None
   params = None


   def __init__(self, testee, spec):
      self.testee = testee
      self.spec = spec

      self._uriSuffix = '#' + str(random.randint(0, 1000000))

      if self.testee.options.has_key('rtt'):
         self._rtt = self.testee.options['rtt']
      elif self.spec.has_key('options') and self.spec['options'].has_key('rtt'):
         self._rtt = self.spec['options']['rtt']
      else:
         self._rtt = 0.2


   def test(self, result, clients):
      raise Exception("not implemented")


   def run(self):
      assert(self.factory)
      assert(self.index)
      assert(self.params)

      result = TestResult()
      finished = Deferred()

      result.passed = None
      result.observed = {}
      result.expected = {}
      result.log = []

      def log(msg, sessionIndex = None, sessionId = None):
         ts = perf_counter()
         result.log.append((ts, sessionIndex, sessionId, msg.encode('utf8')))
         return ts

      result.started = log("Test started.")

      clients = []
      peersready = []
      peersgone = []
      i = 1
      for peerIndex in xrange(self.params.peerCount):
         ready = Deferred()
         gone = Deferred()
         client = self.factory(peerIndex, ready, gone, self, result)
         clients.append(client)
         peersready.append(ready)
         peersgone.append(gone)
         connectWS(client)
         i += 1

      def shutdown(_):
         for client in clients:
            client.proto.sendClose()
            log("Test client closing ...", client.peerIndex, client.proto.session_id)

      def launch(_):
         wait = 2.5 * self._rtt

         def afterwait():
            log("Continuing test ..")
            d = maybeDeferred(self.test, log, result, clients)
            d.addCallback(shutdown)

         def beforewait():
            log("Sleeping for  <strong>%s ms</strong> ..." % (1000. * wait))
            reactor.callLater(wait, afterwait)

         beforewait()

      def error(err):
         ## FIXME
         print "ERROR", err
         shutdown()
         finished.errback(err)


      def done(res):
         result.ended = log("Test ended.")

         for r in res:
            if not r[0]:
               log("Client error: %s" % r[1].value)

         #assert(result.passed is not None)

         finished.callback(result)

      DeferredList(peersready).addCallbacks(launch, error)
      DeferredList(peersgone).addCallbacks(done, error)

      return finished

########NEW FILE########
__FILENAME__ = wampcase2_2_x_x
###############################################################################
##
##  Copyright 2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ['Cases']

## The set of cases we construct and export from this module.
## Everything else is private.
Cases = []

import json

from zope.interface import implementer

from twisted.internet import reactor
from twisted.internet.defer import Deferred, DeferredList

from autobahn.twisted.websocket import connectWS
from autobahn.wamp import WampClientFactory, WampCraClientProtocol

from autobahntestsuite.testrun import TestResult
from autobahntestsuite.util import AttributeBag, perf_counter
from autobahntestsuite.interfaces import ITestCase


#### BEGIN OF CONFIG


###############################################################################
##
##   WampCase 2.1.*
##
###############################################################################


## the topic our test publisher will publish to
##
TOPIC_PUBLISHED_TO = "http://example.com/simple"

## some topic the test publisher will NOT publish to
##
TOPIC_NOT_PUBLISHED_TO = "http://example.com/foobar"

## topic that we will publish to, but that is not
## reigstered on the testee, and hence no events
## shalle be dispatched
##
TOPIC_NOT_REGISTERED = "http://example.com/barbaz"


## for each peer, list of topics the peer subscribes to
## the publisher is always the first peer in this list
##
PEERSET0_1 = [
   [TOPIC_PUBLISHED_TO],
   [TOPIC_PUBLISHED_TO],
   [TOPIC_PUBLISHED_TO, TOPIC_NOT_PUBLISHED_TO],
   [TOPIC_NOT_PUBLISHED_TO],
   []
]

PEERSET0_2 = [
   [],
   [TOPIC_PUBLISHED_TO],
   [TOPIC_PUBLISHED_TO, TOPIC_NOT_PUBLISHED_TO],
   [TOPIC_NOT_PUBLISHED_TO],
   []
]

PEERSET0_3 = [
   [TOPIC_PUBLISHED_TO],
   [TOPIC_PUBLISHED_TO],
   [TOPIC_PUBLISHED_TO, TOPIC_NOT_PUBLISHED_TO],
   [TOPIC_NOT_PUBLISHED_TO],
   []
]

PEERSET0_4 = [
   [TOPIC_NOT_REGISTERED],
   [TOPIC_NOT_REGISTERED],
   [TOPIC_NOT_REGISTERED, TOPIC_NOT_PUBLISHED_TO],
   [TOPIC_NOT_PUBLISHED_TO],
   []
]

PEERSET0_5 = [
   [TOPIC_PUBLISHED_TO],
   [TOPIC_PUBLISHED_TO],
   [TOPIC_PUBLISHED_TO],
   [TOPIC_PUBLISHED_TO],
   [TOPIC_PUBLISHED_TO],
   [TOPIC_PUBLISHED_TO],
   [TOPIC_PUBLISHED_TO],
   [TOPIC_PUBLISHED_TO],
   [TOPIC_PUBLISHED_TO],
   [TOPIC_PUBLISHED_TO]
]

SETTINGS0 = [
## (peers,      publicationTopic,     excludeMe, exclude, eligible, expectedReceivers)
   (PEERSET0_1, TOPIC_PUBLISHED_TO,   None,      None,    None,     [1, 2]),
   (PEERSET0_2, TOPIC_PUBLISHED_TO,   None,      None,    None,     [1, 2]),
   (PEERSET0_3, TOPIC_NOT_REGISTERED, None,      None,    None,     []),
   (PEERSET0_4, TOPIC_NOT_REGISTERED, None,      None,    None,     []),
   (PEERSET0_5, TOPIC_PUBLISHED_TO,   None,      None,    None,     [1, 2, 3, 4, 5, 6, 7, 8, 9]),
]


PAYLOADS0 = [
   [None],
   [100],
   [-0.248], # value has exact representation in _binary_ float (JSON is IEEE binary)
   [-1000000],
   ["hello"],
   [True],
   [False],
   [666, 23, 999],
   [{}, [], None],
   [100, "hello", {u'foo': u'bar'}, [1, 2, 3], ["hello", 20, {'baz': 'poo'}]]
]


###############################################################################
##
##   WampCase 2.2.*
##
###############################################################################


TOPIC_PUBLISHED_TO = "http://example.com/simple"


PEERSET1 = [
   [TOPIC_PUBLISHED_TO],
   [TOPIC_PUBLISHED_TO]
]


SETTINGS1 = [
##
## (peers,    publicationTopic,   excludeMe, exclude, eligible, expectedReceivers)
##
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      None,    None,     [1]),
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      None,    None,     [1]),
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     None,    None,     [0, 1]),

   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [],      None,     [0, 1]),
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [],      None,     [0, 1]), # exclude has precedence over excludeMe !
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [],      None,     [0, 1]),

   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [0],     None,     [1]),
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [0],     None,     [1]),
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [0],     None,     [1]), # exclude has precedence over excludeMe !

   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [1],     None,     [0]), # exclude has precedence over excludeMe !
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [1],     None,     [0]), # exclude has precedence over excludeMe !
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [1],     None,     [0]), # exclude has precedence over excludeMe !

   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [0, 1],  None,     []), # exclude has precedence over excludeMe !
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [0, 1],  None,     []), # exclude has precedence over excludeMe !
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [0, 1],  None,     []), # exclude has precedence over excludeMe !

##
## (peers,    publicationTopic,   excludeMe, exclude, eligible, expectedReceivers)
##
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      None,    [],       []),
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      None,    [0],      []),
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      None,    [1],      [1]),
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      None,    [0, 1],   [1]),

   (PEERSET1, TOPIC_PUBLISHED_TO, True,      None,    [],       []),
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      None,    [0],      []),
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      None,    [1],      [1]),
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      None,    [0, 1],   [1]),

   (PEERSET1, TOPIC_PUBLISHED_TO, False,     None,    [],       []),
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     None,    [0],      [0]),
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     None,    [1],      [1]),
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     None,    [0, 1],   [0, 1]),

##
## (peers,    publicationTopic,   excludeMe, exclude, eligible, expectedReceivers)
##
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [],      [],       []),
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [],      [0],      [0]),     # !!
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [],      [1],      [1]),
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [],      [0, 1],   [0, 1]),  # !!

   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [],      [],       []),
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [],      [0],      [0]),     # !!
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [],      [1],      [1]),
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [],      [0, 1],   [0, 1]),  # !!

   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [],      [],       []),
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [],      [0],      [0]),
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [],      [1],      [1]),
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [],      [0, 1],   [0, 1]),

##
## (peers,    publicationTopic,   excludeMe, exclude, eligible, expectedReceivers)
##
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [0],     [],       []),
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [0],     [0],      []),
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [0],     [1],      [1]),
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [0],     [0, 1],   [1]),

   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [0],     [],       []),
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [0],     [0],      []),
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [0],     [1],      [1]),
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [0],     [0, 1],   [1]),

   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [0],     [],       []),
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [0],     [0],      []),
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [0],     [1],      [1]),
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [0],     [0, 1],   [1]),

##
## (peers,    publicationTopic,   excludeMe, exclude, eligible, expectedReceivers)
##
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [1],     [],       []),
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [1],     [0],      [0]),
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [1],     [1],      []),
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [1],     [0, 1],   [0]),

   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [1],     [],       []),
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [1],     [0],      [0]),
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [1],     [1],      []),
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [1],     [0, 1],   [0]),

   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [1],     [],       []),
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [1],     [0],      [0]),
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [1],     [1],      []),
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [1],     [0, 1],   [0]),

##
## (peers,    publicationTopic,   excludeMe, exclude, eligible, expectedReceivers)
##
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [0, 1],  [],       []),
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [0, 1],  [0],      []),
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [0, 1],  [1],      []),
   (PEERSET1, TOPIC_PUBLISHED_TO, None,      [0, 1],  [0, 1],   []),

   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [0, 1],  [],       []),
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [0, 1],  [0],      []),
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [0, 1],  [1],      []),
   (PEERSET1, TOPIC_PUBLISHED_TO, True,      [0, 1],  [0, 1],   []),

   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [0, 1],  [],       []),
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [0, 1],  [0],      []),
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [0, 1],  [1],      []),
   (PEERSET1, TOPIC_PUBLISHED_TO, False,     [0, 1],  [0, 1],   []),
]

## The event payloads the publisher sends in one session.
##
## Note: be aware of JSON roundtripping "issues" like
##    (ujson.loads(ujson.dumps(0.1234)) == 0.1234) => False
##
PAYLOADS1 = [["Hello, world!"]]


#### END OF CONFIG


class WampCase2_2_x_x_Protocol(WampCraClientProtocol):


   def onSessionOpen(self):
      self.test.result.log.append((perf_counter(), self.factory.peerIndex, self.session_id, "WAMP session opened to <strong>%s</strong> at <strong>%s</strong>." % (self.session_server, self.peer)))
      if self.test.testee.auth:
         d = self.authenticate(**self.test.testee.auth)
         d.addCallbacks(self.onAuthSuccess, self.onAuthError)
      else:
         self.main()


   def sendMessage(self, payload):
      self.test.result.log.append((perf_counter(), self.factory.peerIndex, self.session_id, '<pre class="wamp">TX => %s</pre>' % payload))
      WampCraClientProtocol.sendMessage(self, payload)


   def onMessage(self, payload, binary):
      self.test.result.log.append((perf_counter(), self.factory.peerIndex, self.session_id, '<pre class="wamp">RX <= %s</pre>' % payload))
      WampCraClientProtocol.onMessage(self, payload, binary)


   def onAuthSuccess(self, permissions):
      self.test.result.log.append((perf_counter(), self.factory.peerIndex, self.session_id, "WAMP session %s authenticated with credentials: <pre>%s</pre>" % (self.session_id, self.test.testee.auth)))
      self.main()


   def onAuthError(self, e):
      uri, desc, details = e.value.args
      self.test.result.log.append((perf_counter(), self.factory.peerIndex, self.session_id, "WAMP authentication error: %s" % details))
      print "Authentication Error!", uri, desc, details


   def main(self):
      subscribeTopics = self.test.params.peers[self.factory.peerIndex]
      for topic in subscribeTopics:
         topic += self.factory.test._uriSuffix
         self.subscribe(topic, self.onEvent)
         self.test.result.log.append((perf_counter(), self.factory.peerIndex, self.session_id, "Subscribed to <pre>%s</pre>" % topic))
      self.factory.onReady.callback(self.session_id)


   def onEvent(self, topic, event):
      self.test.result.log.append((perf_counter(), self.factory.peerIndex, self.session_id, "Received event for topic <pre>%s</pre> and payload <pre>%s</pre>" % (topic, event)))
      if not self.test.result.observed.has_key(self.session_id):
         self.test.result.observed[self.session_id] = []
      self.test.result.observed[self.session_id].append((topic, event))



class WampCase2_2_x_x_Factory(WampClientFactory):

   protocol = WampCase2_2_x_x_Protocol

   def __init__(self, test, peerIndex, onReady, onGone):
      WampClientFactory.__init__(self, test.testee.url)
      self.test = test
      self.peerIndex = peerIndex
      self.onReady = onReady
      self.onGone = onGone
      self.proto = None

   def buildProtocol(self, addr):
      proto = self.protocol()
      proto.factory = self
      proto.test = self.test
      proto.session_id = None
      self.proto = proto
      return proto

   def clientConnectionLost(self, connector, reason):
      reason = str(reason.value)
      if self.proto and hasattr(self.proto, 'session_id'):
         sid = self.proto.session_id
      else:
         sid = None
      self.test.result.log.append((perf_counter(), self.peerIndex, sid, "Client connection lost: %s" % reason))
      self.onGone.callback(None)

   def clientConnectionFailed(self, connector, reason):
      reason = str(reason.value)
      self.test.result.log.append((perf_counter(), self.peerIndex, None, "Client connection failed: %s" % reason))
      self.onGone.callback(reason)



class WampCase2_2_x_x_Params(AttributeBag):
   """
   Test parameter set for configuring instances of WampCase2_*_*.

   peers: a list with one item per WAMP session run during the test, where each item contains a list of topics each peer _subscribes_ to. The publisher that publishes during the test is always the first item in the list.

   publicationTopic, excludeMe, exclude, eligible: paramters controlling how events are published during the test.

   eventPayloads: a list of payloads each tested as event payload to the test at hand.

   expectedReceivers: a list of session indices, where each index references a WAMP session created for the list in `peers`.
   """

   ATTRIBUTES = ['peers',
                 'publicationTopic',
                 'publicationMethod',
                 'excludeMe',
                 'exclude',
                 'eligible',
                 'eventPayloads',
                 'expectedReceivers']


import random


@implementer(ITestCase)
class WampCase2_2_x_x_Base:

   def __init__(self, testee, spec):
      self.testee = testee
      self.spec = spec
      self.result = TestResult()
      self.result.passed = False
      self.result.observed = {}
      self.result.expected = {}
      self.result.log = []

      self._uriSuffix = '#' + str(random.randint(0, 1000000))

      if self.testee.options.has_key('rtt'):
         self._rtt = self.testee.options['rtt']
      elif self.spec.has_key('options') and self.spec['options'].has_key('rtt'):
         self._rtt = self.spec['options']['rtt']
      else:
         self._rtt = 0.2


   def run(self):
      self.result.started = perf_counter()
      self.result.log.append((self.result.started, None, None, "Test started."))

      self.clients = []
      peersready = []
      peersgone = []
      i = 1
      for peerIndex in xrange(len(self.params.peers)):
         ready = Deferred()
         gone = Deferred()
         client = WampCase2_2_x_x_Factory(self, peerIndex, ready, gone)
         self.clients.append(client)
         peersready.append(ready)
         peersgone.append(gone)
         connectWS(client)
         i += 1


      def shutdown():
         for c in self.clients:
            c.proto.sendClose()
            self.result.log.append((perf_counter(), c.peerIndex, c.proto.session_id, "Test client closing ..."))


      def test():
         for c in self.clients:
            self.result.expected[c.proto.session_id] = []
            self.result.observed[c.proto.session_id] = []

         publisherPeerIndex = 0
         publisher = self.clients[publisherPeerIndex]
         publisherSessionId = publisher.proto.session_id
         topic = self.params.publicationTopic + self._uriSuffix
         payloads = self.params.eventPayloads

         expectedReceivers = [self.clients[i] for i in self.params.expectedReceivers]
         for r in expectedReceivers:
            for p in payloads:
               self.result.expected[r.proto.session_id].append((topic, p))

         args = {}

         if self.params.excludeMe is not None:
            args['excludeMe'] = self.params.excludeMe

         if self.params.exclude is not None:
            ## map exclude indices to session IDs
            args['exclude'] = []
            for i in self.params.exclude:
               args['exclude'].append(self.clients[i].proto.session_id)

         if self.params.eligible is not None:
            ## map exclude indices to session IDs
            args['eligible'] = []
            for i in self.params.eligible:
               args['eligible'].append(self.clients[i].proto.session_id)

         d_pl = []

         for pl in payloads:

            if self.params.publicationMethod == 0:

               ## publish using standard WAMP event publication
               ##
               publisher.proto.publish(topic, pl, **args)

            elif self.params.publicationMethod == 1:

               ## publish indirectly by instructing the peer to
               ## dispatch an event
               ##
               args['me'] = publisherSessionId
               ENDPOINT = "http://api.testsuite.wamp.ws/testee/control#dispatch"
               #ENDPOINT = "http://api.testsuite.wamp.ws/autobahn/testee/control#dispatch"
               cd = publisher.proto.call(ENDPOINT, topic, pl, args)
               del args['me'] # don't show this in test log
               d_pl.append(cd)

            else:
               raise Exception("no such publication method: %s" % self.params.publicationMethod)

            s_args = ["%s=%s" % (k,v) for (k,v) in args.items()]
            if len(s_args) > 0:
               s_args = 'with options <pre>%s</pre> ' % ', '.join(s_args)
            else:
               s_args = ''

            if self.params.publicationMethod == 0:
               msg = "Published event to topic <pre>%s</pre> %sand payload <pre>%s</pre>" % (topic, s_args, pl)
            elif self.params.publicationMethod == 1:
               msg = "Initiated server dispatched event to topic <pre>%s</pre> %sand payload <pre>%s</pre>" % (topic, s_args, pl)
            else:
               msg = ""

            self.result.log.append((perf_counter(), publisherPeerIndex, publisher.proto.session_id, msg))

         ## After having published everything the test had specified,
         ## we need to _wait_ to receive events on all our WAMP sessions
         ## to compare with our expectation. By default, we wait 3x the
         ## specified/default RTT.
         ##
         wait = 1.5 * self._rtt

         def afterwait():
            self.result.log.append((perf_counter(), None, None, "Continuing test .."))
            shutdown()

         def beforewait():
            self.result.log.append((perf_counter(), None, None, "Sleeping for <strong>%s ms</strong> ..." % (1000. * wait)))
            reactor.callLater(wait, afterwait)

         if self.params.publicationMethod == 1 and len(d_pl) > 0:
            d = DeferredList(d_pl)
            def onres(res):
               self.result.log.append((perf_counter(), None, None, "Event init call result: %s" % res))
               beforewait()
            d.addCallback(onres)
         else:
            #reactor.callLater(0, beforewait)
            beforewait()


      def launch(_):
         ## After all our clients have signaled "peersready", these
         ## clients will just have sent their subscribe WAMP messages,
         ## and since with WAMPv1, there is no reply (to wait on), the
         ## clients immediately signal readiness and we need to _wait_
         ## here to give the testee time to receive and actually subscribe
         ## the clients. When we don't wait, we might publish test events
         ## before the testee has subscribed all clients as needed.
         ## We need acknowledgement of subscribe for WAMPv2!
         ##
         wait = 2.5 * self._rtt
         def afterwait():
            self.result.log.append((perf_counter(), None, None, "Continuing test .."))
            test()
         self.result.log.append((perf_counter(), None, None, "Sleeping for  <strong>%s ms</strong> ..." % (1000. * wait)))
         def beforewait():
            reactor.callLater(wait, afterwait)
         reactor.callLater(0, beforewait)


      def error(err):
         ## FIXME
         print "ERROR", err
         shutdown()
         self.finished.errback(err)


      def done(res):
         self.result.ended = perf_counter()
         self.result.log.append((self.result.ended, None, None, "Test ended."))

         clientErrors = []
         for r in res:
            if not r[0]:
               clientErrors.append(str(r[1].value))

         if len(clientErrors) > 0:
            passed = False
            print "Client errors", clientErrors
         else:
            passed = json.dumps(self.result.observed) == json.dumps(self.result.expected)
            if False and not passed:
               print
               print "EXPECTED"
               print self.result.expected
               print "OBSERVED"
               print self.result.observed
               print

         self.result.passed = passed
         self.finished.callback(self.result)

      DeferredList(peersready).addCallbacks(launch, error)
      DeferredList(peersgone).addCallbacks(done, error)

      self.finished = Deferred()
      return self.finished



def generate_WampCase2_2_x_x_classes(baseIndex, settings, payloads, publicationMethod = 0):
   ## dynamically create case classes
   ##
   res = []

   jc = 1
   for setting in settings:

      ic = 1
      for payload in payloads:

         params = WampCase2_2_x_x_Params(peers = setting[0],
                                         publicationTopic = setting[1],
                                         publicationMethod = publicationMethod,
                                         excludeMe = setting[2],
                                         exclude = setting[3],
                                         eligible = setting[4],
                                         eventPayloads = payload,
                                         expectedReceivers = setting[5])

         pl = len(params.eventPayloads)
         plc = "s" if pl else ""

         s = []
         i = 0
         for p in params.peers:
            if len(p) > 0:
               s.append("<strong>%s</strong>: <i>%s</i>" % (i, ' & '.join(p)))
            else:
               s.append("<strong>%s</strong>: <i>%s</i>" % (i, '-'))
            i += 1
         s = ', '.join(s)

         o = []
         if params.excludeMe is not None:
            o.append("excludeMe = %s" % params.excludeMe)
         if params.exclude is not None:
            o.append("exclude = %s" % params.exclude)
         if params.eligible is not None:
            o.append("eligible = %s" % params.eligible)
         if len(o) > 0:
            o = ', '.join(o)
         else:
            o = "-"

         description = """The test connects <strong>%s</strong> WAMP clients to the testee, subscribes \
the sessions to topics %s, waits <strong>3xRTT</strong> seconds and \
then publishes <strong>%d</strong> event%s to the topic <i>%s</i> with payload%s <i>%s</i> from the first session. \
The test then waits <strong>3xRTT</strong> seconds to receive events dispatched from the testee.
<br><br>
For publishing of test events, the following publication options are used: <i>%s</i>.
<br><br>
Note that the test has used the topic URIs from above description with a session specific suffix, e.g. <i>#6011</i>. \
See the log for actual URIs used.
""" % (len(params.peers),
       s,
       pl,
       plc,
       params.publicationTopic,
       plc,
       ', '.join([str(x) for x in params.eventPayloads]),
       o)

         expectation = """We expect the testee to dispatch the events to us on \
the sessions %s""" % ', '.join(['<strong>%s</strong>' % x for x in params.expectedReceivers])

         index = (baseIndex[0], baseIndex[1], jc, ic)
         klassname = "WampCase%d_%d_%d_%d" % index

         Klass = type(klassname,
                      (object, WampCase2_2_x_x_Base, ),
                      {
                         "__init__": WampCase2_2_x_x_Base.__init__,
                         "run": WampCase2_2_x_x_Base.run,
                         "index": index,
                         "description": description,
                         "expectation": expectation,
                         "params": params
                       })

         res.append(Klass)
         ic += 1
      jc += 1

   return res


## standard WAMP publication
##
Cases.extend(generate_WampCase2_2_x_x_classes((2, 1), SETTINGS0, PAYLOADS0, 0))
Cases.extend(generate_WampCase2_2_x_x_classes((2, 2), SETTINGS0, PAYLOADS0, 0))

## peer-initiated event dispatching
##
Cases.extend(generate_WampCase2_2_x_x_classes((2, 3), SETTINGS1, PAYLOADS1, 1))
Cases.extend(generate_WampCase2_2_x_x_classes((2, 4), SETTINGS1, PAYLOADS1, 1))

########NEW FILE########
__FILENAME__ = wampcase2_5_x_x
###############################################################################
##
##  Copyright 2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ['Cases']

## The set of cases we construct and export from this module.
## Everything else is private.
Cases = []

import random, json
from pprint import pprint

from twisted.internet import reactor
from twisted.internet.defer import Deferred, DeferredList

from autobahntestsuite.util import AttributeBag
from wampcase import WampCase, WampCaseFactory, WampCaseProtocol



class WampCase4_1_1_Params(AttributeBag):

   ATTRIBUTES = ['peerCount',
                 'topicCount',
                 'subsCount',
                 'pubsCount']


class WampCase4_1_1_Protocol(WampCaseProtocol):

   def test(self):
      ## WAMP session opened and authenticated.

      self.factory.result.observed[self.session_id] = {}
      self.factory.result.expected[self.session_id] = {}

      self._topics = []

      expected = self.factory.result.expected
      observed = self.factory.result.observed

      for i in xrange(self.factory.test.params.subsCount):

         topic = "http://example.com/simple#" + str(random.randint(0, self.factory.test.params.topicCount))
         self.subscribe(topic, self.onEvent)

         expected[self.session_id][topic] = 0
         observed[self.session_id][topic] = 0

         self._topics.append(topic)

      ## Signal the test controller our readiness.
      self.ready()

   def monkeyPublish(self, event):
      i = random.randint(0, len(self._topics) - 1)
      topic = self._topics[i]
      self.publish(topic, event, excludeMe = False)
      #print topic

      expected = self.factory.result.expected
      rcnt = 0
      for e in expected:
         if expected[e].has_key(topic):
            expected[e][topic] += 1
            rcnt += 1
      self.factory.totalExpected += rcnt


   def onEvent(self, topic, event):
      observed = self.factory.result.observed[self.session_id]
      if not observed.has_key(topic):
         observed[topic] = 0
      observed[topic] += 1
      self.factory.totalObserved += 1

      print self.factory.totalObserved, self.factory.totalExpected



class WampCase4_1_1_Factory(WampCaseFactory):

   protocol = WampCase4_1_1_Protocol

   def buildProtocol(self, addr):
      proto = WampCaseFactory.buildProtocol(self, addr)
      self.totalExpected = 0
      self.totalObserved = 0
      return proto




class WampCase4_1_1(WampCase):

   index = (4, 1, 1, 0)
   factory = WampCase4_1_1_Factory
   params = WampCase4_1_1_Params(peerCount = 10,
                                 topicCount = 10,
                                 subsCount = 5,
                                 pubsCount = 200)

   description = "A NOP test."
   expectation = "Nothing."



   def test(self, log, result, clients):
      msg = "NOP test running using %d sessions\n" % len(clients)
      log(msg)
      print msg

      for i in xrange(self.params.pubsCount):
         j = random.randint(0, len(clients) - 1)
         clients[j].proto.monkeyPublish("Hello, world!")
      result.passed = True

      d = Deferred()
      wait = 80 * self._rtt

      def afterwait():
         log("Continuing test ..")

         if False:
            print
            print "Expected:"
            for r in result.expected:
               print r
               pprint(result.expected[r])
               print

            print
            print "Observed:"
            for r in result.observed:
               print r
               pprint(result.observed[r])
               print

         result.passed = json.dumps(result.observed) == json.dumps(result.expected)

         d.callback(None)

      def beforewait():
         log("Sleeping for  <strong>%s ms</strong> ..." % (1000. * wait))
         reactor.callLater(wait, afterwait)

      beforewait()
      return d


Cases.append(WampCase4_1_1)

########NEW FILE########
__FILENAME__ = wampcase3_1_x_x
###############################################################################
##
##  Copyright 2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ['Cases']

## The set of cases we construct and export from this module.
## Everything else is private.
Cases = []


#### BEGIN OF CONFIG


#### END OF CONFIG


import json, time

from zope.interface import implementer

from twisted.internet import reactor
from twisted.internet.defer import Deferred, DeferredList, maybeDeferred

from autobahn.twisted.websocket import connectWS
from autobahn.wamp import WampClientFactory, WampCraClientProtocol

from autobahntestsuite.testrun import TestResult
from autobahntestsuite.util import AttributeBag, perf_counter
from autobahntestsuite.interfaces import ITestCase


class WampCase3_1_x_x_Protocol(WampCraClientProtocol):

   def onSessionOpen(self):
      if self.test.testee.auth:
         d = self.authenticate(**self.test.testee.auth)
         d.addCallbacks(self.onAuthSuccess, self.onAuthError)
      else:
         self.main()

   def onAuthSuccess(self, permissions):
      self.main()

   def onAuthError(self, e):
      uri, desc, details = e.value.args
      print "Authentication Error!", uri, desc, details

   def main(self):
      self.factory.onReady(self)



class WampCase3_1_x_x_Factory(WampClientFactory):

   protocol = WampCase3_1_x_x_Protocol

   def __init__(self, test, onReady, onGone):
      WampClientFactory.__init__(self, test.testee.url)
      self.test = test
      self.onReady = onReady
      self.onGone = onGone
      self.proto = None

   def buildProtocol(self, addr):
      proto = self.protocol()
      proto.factory = self
      proto.test = self.test
      self.proto = proto
      return proto

   def clientConnectionLost(self, connector, reason):
      self.onGone(self.proto)

   def clientConnectionFailed(self, connector, reason):
      self.onGone(self.proto)



class WampCase3_1_x_x_Params(AttributeBag):
   """
   Test parameter set for configuring instances of WampCase2_*_*.

   peers: a list with one item per WAMP session run during the test, where each item contains a list of topics each peer _subscribes_ to. The publisher that publishes during the test is always the first item in the list.

   publicationTopic, excludeMe, exclude, eligible: paramters controlling how events are published during the test.

   eventPayloads: a list of payloads each tested as event payload to the test at hand.

   expectedReceivers: a list of session indices, where each index references a WAMP session created for the list in `peers`.
   """

   ATTRIBUTES = ['peers',
                 'publicationTopic',
                 'excludeMe',
                 'exclude',
                 'eligible',
                 'eventPayloads',
                 'expectedReceivers']



@implementer(ITestCase)
class WampCase3_1_x_x_Base:

   DESCRIPTION = "Undefined."
   EXPECTATION = "Undefined."

   def __init__(self, testee):
      self.testee = testee
      self.client = None
      self.result = TestResult()
      self.result.received = {}
      self.result.expected = {}
      self.result.log = []


   def run(self):
      self.result.started = perf_counter()

      def shutdown():
         if self.client:
            self.client.proto.sendClose()


      def test(proto):
         #res = yield self.call("http://api.testsuite.wamp.ws/case/3.1.1#1", 23)
         ## after having published everything the test had specified,
         ## we need to _wait_ for events on all our WAMP sessions to
         ## compare with our expectation. by default, we wait 3x the
         ## specified/default RTT
         def perform(i, p):
            d = proto.call("http://api.testsuite.wamp.ws/case/3.1.1#1", float(p))
            def got(res):
               self.result.received[i] = float(res)
            d.addCallback(got)

         payloads = []
         payloads.extend([0])
         payloads.extend([2**7-1, 2**8-1, 2**15-1, 2**16-1, 2**24])
         #payloads.extend([2**7-1, 2**8-1, 2**15-1, 2**16-1, 2**24, 2**31-1, 2**32-1, 2**53])
         #payloads.extend([2**53+1, 2**63-1, 2**64-1])
         #payloads.extend([-2**7, -2**15, -2**24, -2**31, -2**53])
         payloads.extend([-2**7, -2**15, -2**24])
         #payloads.extend([-2**63])
         i = 0
         for p in payloads:
            self.result.expected[i] = float(p)
            perform(i, p)
            i += 1

         wait = 3 * self.testee.options.get("rtt", 0.2)
         reactor.callLater(wait, shutdown)


      def launch(proto):
         ## FIXME: explain why the following needed, since
         ## without the almost zero delay (which triggers a
         ## reactor loop), the code will not work as expected!

         #test() # <= does NOT work
         reactor.callLater(0.00001, test, proto)


      def error(err):
         ## FIXME
         print "ERROR", err
         shutdown()
         self.finished.errback(err)


      def done(proto):
         self.result.ended = perf_counter()
         passed = json.dumps(self.result.received) == json.dumps(self.result.expected)
         if not passed:
            print "EXPECTED", self.result.expected
            print "RECEIVED", self.result.received
         self.result.passed = passed
         self.finished.callback(self.result)

      self.client = WampCase3_1_x_x_Factory(self, launch, done)
      connectWS(self.client)

      self.finished = Deferred()
      return self.finished



class WampCase3_1_1_1(WampCase3_1_x_x_Base):
   pass


Cases = [WampCase3_1_1_1]


def generate_WampCase3_1_x_x_classes2():
   ## dynamically create case classes
   ##
   res = []
   jc = 1
   for setting in SETTINGS:
      ic = 1
      for payload in PAYLOADS:

         params = WampCase2_2_x_x_Params(peers = setting[0],
                                       publicationTopic = setting[1],
                                       excludeMe = setting[2],
                                       exclude = setting[3],
                                       eligible = setting[4],
                                       eventPayloads = payload,
                                       expectedReceivers = setting[5])

         pl = len(params.eventPayloads)
         plc = "s" if pl else ""

         s = []
         i = 0
         for p in params.peers:
            if len(p) > 0:
               s.append("%d: %s" % (i, ' & '.join(p)))
            else:
               s.append("%d: %s" % (i, '-'))
            i += 1
         s = ', '.join(s)

         o = []
         if params.excludeMe is not None:
            o.append("excludeMe = %s" % params.excludeMe)
         if params.exclude is not None:
            o.append("exclude = %s" % params.exclude)
         if params.eligible is not None:
            o.append("eligible = %s" % params.eligible)
         if len(o) > 0:
            o = ', '.join(o)
         else:
            o = "-"

         description = """The test connects %d WAMP clients to the testee, subscribes \
the sessions to topics %s and \
then publishes %d event%s to the topic %s with payload%s %s from the first session. \
The test sets the following publication options: %s.
""" % (len(params.peers),
       s,
       pl,
       plc,
       params.publicationTopic,
       plc,
       ', '.join(['"' + str(x) + '"' for x in params.eventPayloads]),
       o)

         expectation = """We expect the testee to dispatch the events to us on \
the sessions %s""" % (params.expectedReceivers,)

         klassname = "WampCase3_1_%d_%d" % (jc, ic)

         Klass = type(klassname,
                      (object, WampCase3_1_x_x_Base, ),
                      {
                         "__init__": WampCase3_1_x_x_Base.__init__,
                         "run": WampCase3_1_x_x_Base.run,
                         "description": description,
                         "expectation": expectation,
                         "params": params
                       })

         res.append(Klass)
         ic += 1
      jc += 1
   return res



#Cases.extend(generate_WampCase3_1_x_x_classes())

########NEW FILE########
__FILENAME__ = wampcase_tmpl
###############################################################################
##
##  Copyright 2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ['Cases']

## The set of cases we construct and export from this module.
## Everything else is private.
Cases = []

from autobahntestsuite.util import AttributeBag
from wampcase import WampCase, WampCaseFactory, WampCaseProtocol



class WampCase4_1_1_Params(AttributeBag):

   ATTRIBUTES = ['peerCount']


class WampCase4_1_1_Protocol(WampCaseProtocol):

   def test(self):
      ## WAMP session opened and authenticated.

      ## .. may do stuff here ..

      ## Signal the test controller our readiness.
      self.ready()


class WampCase4_1_1_Factory(WampCaseFactory):

   protocol = WampCase4_1_1_Protocol


class WampCase4_1_1(WampCase):

   factory = WampCase4_1_1_Factory
   index = (4, 1, 1, 0)
   description = "A NOP test."
   expectation = "Nothing."
   params = WampCase4_1_1_Params(peerCount = 10)


   def test(self, log, result, clients):
      msg = "NOP test running using %d sessions\n" % len(clients)
      log(msg)
      print msg
      result.passed = True


Cases.append(WampCase4_1_1)

########NEW FILE########
__FILENAME__ = wampfuzzing
###############################################################################
##
##  Copyright (C) 2013-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ("FuzzingWampClient",)

from zope.interface import implementer
from zope.interface.verify import verifyObject, verifyClass

from twisted.internet.defer import returnValue, \
                                   inlineCallbacks

import autobahn
import autobahntestsuite

from autobahn.wamp1.protocol import exportRpc, \
                                    WampServerProtocol, \
                                    WampServerFactory

from interfaces import ITestRunner, ITestDb
from rinterfaces import RITestDb, RITestRunner
from testrun import TestRun, Testee



@implementer(ITestRunner)
@implementer(RITestRunner)
class FuzzingWampClient(object):
   """
   A test driver for WAMP test cases.

   The test driver takes a test specification and orchestrates the execution of tests
   against the set of testees (as specified in the test spec).
   """

   MODENAME = 'fuzzingwampclient'


   def __init__(self, testDb, debug = False):

      assert(verifyObject(ITestDb, testDb))
      assert(verifyObject(RITestDb, testDb))

      self._testDb = testDb
      self._debug = debug
      self.dispatch = None


   @exportRpc
   def run(self, specName, saveResults = True):
      return self.runAndObserve(specName, saveResults = saveResults)


   @inlineCallbacks
   def runAndObserve(self, specName, observers_ = [], saveResults = True):

      specId, spec = yield self._testDb.getSpecByName(specName)
      casesByTestee = yield self._testDb.generateCasesByTestee(specId)
      _observers = observers_[:]
      #_observers = observers_

      ## publish WAMP event on test case finished
      ##
      def notify(runId, testRun, testCase, result, remaining):
         if testCase:
            evt = {
               'testee': testRun.testee.name,
               'runId': runId,
               'index': testCase.index,
               'passed': result.passed,
               'remaining': remaining
            }
            topic = "http://api.testsuite.wamp.ws/testrun#onResult"
         else:
            evt = {
               'testee': testRun.testee.name,
               'runId': runId
            }
            topic = "http://api.testsuite.wamp.ws/testrun#onComplete"

         self.dispatch(topic, evt)
         #if result and not result.passed:
         #   print topic, evt

      if self.dispatch:
         _observers.append(notify)

      ## save test results to test database
      ##
      def save(runId, testRun, testCase, result, remaining):
         if testCase:
            self._testDb.saveResult(runId, testRun, testCase, result, saveResults)

      if saveResults:
         _observers.append(save)

      testRuns = []
      for obj in spec['testees']:
         testee = Testee(**obj)
         cases = casesByTestee.get(testee.name, [])
         if testee.options.has_key('randomize') and testee.options['randomize'] is not None:
            randomize = testee.options['randomize']
         elif spec.has_key('options') and spec['options'].has_key('randomize') and spec['options']['randomize'] is not None:
            randomize = spec['options']['randomize']
         else:
            randomize = False
         testRun = TestRun(testee, cases, randomize = randomize)
         testRuns.append(testRun)

      runId = yield self._testDb.newRun(specId)

      print
      print "Autobahn Fuzzing WAMP Client"
      print
      print "Autobahn Version          : %s" % autobahn.version
      print "AutobahnTestsuite Version : %s" % autobahntestsuite.version
      #print "WAMP Test Cases           : %d" % len(self._caseSet.Cases)
      print "WAMP Testees              : %d" % len(spec["testees"])
      print
      for testRun in testRuns:
         print "%s @ %s : %d test cases prepared" % (testRun.testee.name, testRun.testee.url, testRun.remaining())
      print
      print

      def progress(runId, testRun, testCase, result, remaining):
         for obsv in _observers:
            try:
               obsv(runId, testRun, testCase, result, remaining)
            except Exception, e:
               print e

      if spec.get('parallel', False):
         fails, resultIds = yield self._runParallel(runId, spec, testRuns, progress)
      else:
         fails, resultIds = yield self._runSequential(runId, spec, testRuns, progress)

      yield self._testDb.closeRun(runId)

      returnValue((runId, resultIds))


   @inlineCallbacks
   def _runSequential(self, runId, spec, testRuns, progress):
      """
      Execute all test runs sequentially - that is for each
      testee (one after another), run the testee's set of
      test cases sequentially.
      """
      ## we cumulate number of test fails and progress() return values
      ##
      fails = 0
      progressResults = []

      for testRun in testRuns:
         while True:
            ## get next test case _class_ for test run
            ##
            TestCase = testRun.next()

            if TestCase:
               ## run test case, let fire progress() callback and cumulate results
               ##
               try:
                  testCase = TestCase(testRun.testee, spec)
               except Exception, e:
                  print "ERROR 1", e
               else:
                  try:
                     result = yield testCase.run()
                  except Exception, e:
                     print "ERROR 2", e
               if not result.passed:
                  fails += 1
               pres = yield progress(runId, testRun, testCase, result, testRun.remaining())
               progressResults.append(pres)
            else:
               ## signal end of test run by firing progress() one last time ..
               ##
               yield progress(runId, testRun, None, None, 0)
               break

      returnValue((fails, progressResults))


   def _runParallel(self, runId, spec, testRuns, progress):
      """
      Execute all test runs in parallel - that is run
      each testee's set of test cases sequentially
      against that testee, but do so for all testees
      in parallel.
      """
      raise Exception("implement me")


class WsTestWampProtocol(WampServerProtocol):

   def onSessionOpen(self):
      self.registerForPubSub("http://api.testsuite.wamp.ws", True)
      self.registerForRpc(self.factory._testDb, "http://api.testsuite.wamp.ws/testdb/")
      self.registerForRpc(self.factory._testRunner, "http://api.testsuite.wamp.ws/testrunner/")


class WsTestWampFactory(WampServerFactory):

   protocol = WsTestWampProtocol

   def __init__(self, testDb, testRunner, url, debug = False):
      assert(verifyObject(ITestDb, testDb))
      assert(verifyObject(ITestRunner, testRunner))
      WampServerFactory.__init__(self, url, debug = True, debugWamp = True)
      self._testDb = testDb
      self._testRunner = testRunner


@inlineCallbacks
def startFuzzingWampClient(self, specName):
   """
   Start a WAMP fuzzing client test run using a spec previously imported.
   """
   testSet = WampCaseSet()
   testDb = TestDb([testSet])
   testRunner = FuzzingWampClient(testDb)

   def progress(runId, testRun, testCase, result, remaining):
      if testCase:
         print "%s - %s %s (%d tests remaining)" % (testRun.testee.name, "PASSED   : " if result.passed else "FAILED  : ", testCase.__class__.__name__, remaining)
      else:
         print "FINISHED : Test run for testee '%s' ended." % testRun.testee.name

   runId, resultIds = yield testRunner.runAndObserve(specName, [progress])

   print
   print "Tests finished: run ID %s, result IDs %d" % (runId, len(resultIds))
   print

   summary = yield testDb.getTestRunSummary(runId)

   tab = Tabify(['l32', 'r5', 'r5'])
   print
   print tab.tabify(['Testee', 'Pass', 'Fail'])
   print tab.tabify()
   for t in summary:
      print tab.tabify([t['name'], t['passed'], t['failed']])
   print


def startImportSpec(self, specFilename):
   """
   Import a test specification into the test database.
   """
   specFilename = os.path.abspath(specFilename)
   print "Importing spec from %s ..." % specFilename
   try:
      spec = json.loads(open(specFilename).read())
   except Exception, e:
      raise Exception("Error: invalid JSON data - %s" % e)

   ## FIXME: this should allow to import not only WAMP test specs,
   ## but WebSocket test specs as well ..
   testSet = WampCaseSet()
   db = TestDb([testSet])

   def done(res):
      op, id, name = res
      if op is None:
         print "Spec under name '%s' already imported and unchanged (Object ID %s)." % (name, id)
      elif op == 'U':
         print "Updated spec under name '%s' (Object ID %s)." % (name, id)
      elif op == 'I':
         print "Imported spec under new name '%s' (Object ID %s)." % (name, id)
      print

   def failed(failure):
      print "Error: spec import failed - %s." % failure.value

   d = db.importSpec(spec)
   d.addCallbacks(done, failed)
   return d


def startExportSpec(self, specName, specFilename = None):
   """
   Export a (currently active, if any) test specification from the test database by name.
   """
   if specFilename:
      specFilename = os.path.abspath(specFilename)
      fout = open(specFilename, 'w')
   else:
      fout = sys.stdout

   testSet = WampCaseSet()
   db = TestDb([testSet])

   def done(res):
      id, spec = res
      data = json.dumps(spec, sort_keys = True, indent = 3, separators = (',', ': '))
      fout.write(data)
      fout.write('\n')
      if specFilename:
         print "Exported spec '%s' to %s." % (specName, specFilename)
         print

   def failed(failure):
      print "Error: spec export failed - %s" % failure.value
      print

   d = db.getSpecByName(specName)
   d.addCallbacks(done, failed)
   return d


def startWeb(self, port = 7070, debug = False):
   """
   Start Web service for test database.
   """
   app = klein.Klein()
   app.debug = debug
   app.templates = jinja2.Environment(loader = jinja2.FileSystemLoader('autobahntestsuite/templates'))

   app.db = TestDb([WampCaseSet()], debug = debug)
   app.runner = FuzzingWampClient(app.db, debug = debug)


   @app.route('/')
   @inlineCallbacks
   def page_home(request):
      testruns = yield app.db.getTestRuns(limit = 20)
      rm = {'fuzzingwampclient': 'WAMP/client'}
      cs = {'wamp': 'WAMP'}
      for tr in testruns:
         started = parseutc(tr['started'])
         ended = parseutc(tr['ended'])
         endedOrNow = ended if ended else datetime.utcnow()
         duration = (endedOrNow - started).seconds
         tr['duration'] = duration

         if started:
            tr['started'] = pprint_timeago(started)
         if ended:
            tr['ended'] = pprint_timeago(ended)

         if tr['total']:
            tr['failed'] = tr['total'] - tr['passed']
         else:
            tr['failed'] = 0

         tr['runMode'] = rm[tr['runMode']]
         tr['caseSetName'] = cs[tr['caseSetName']]
      page = app.templates.get_template('index.html')
      returnValue(page.render(testruns = testruns))


   @app.route('/testrun/<path:runid>')
   @inlineCallbacks
   def page_show_testrun(*args, **kwargs):
      runid = kwargs.get('runid', None)
      testees = yield app.db.getTestRunSummary(runid)
      testresults = yield app.db.getTestRunIndex(runid)
      for tr in testresults:
         tr['index'] = "Case " + '.'.join(str(x) for x in tr['index'][0:4])
         for r in tr['results']:
            tr['results'][r]['duration'] *= 1000

      page = app.templates.get_template('testrun.html')
      returnValue(page.render(testees = testees, testresults = testresults))


   @app.route('/testresult/<path:resultid>')
   @inlineCallbacks
   def page_show_testresult(*args, **kwargs):
      resultid = kwargs.get('resultid', None)
      testresult = yield app.db.getTestResult(resultid)

      n = 0
      for k in testresult.expected:
         n += len(testresult.expected[k])
      if n == 0:
         testresult.expected = None

      n = 0
      for k in testresult.observed:
         n += len(testresult.observed[k])
      if n == 0:
         testresult.observed = None

      testresult.duration = 1000. * (testresult.ended - testresult.started)
      page = app.templates.get_template('testresult.html')
      returnValue(page.render(testresult = testresult))


   @app.route('/home')
   def page_home_deferred_style(request):
      d1 = Deferred()
      db = TestDb()
      d2 = db.getTestRuns()
      def process(result):
         res = []
         for row in result:
            obj = {}
            obj['runId'] = row[0]
            obj['mode'] = row[1]
            obj['started'] = row[2]
            obj['ended'] = row[3]
            res.append(obj)
         d1.callback(json.dumps(res))
      d2.addCallback(process)
      return d1

   ## serve statuc stuff from a standard File resource
   static_resource = File("autobahntestsuite/static")

   ## serve a WAMP server to access the testsuite
   wamp_factory = WsTestWampFactory(app.db, app.runner, "ws://localhost:%d" % port, debug = debug)

   ## we MUST start the factory manually here .. Twisted Web won't
   ## do for us.
   wamp_factory.startFactory()

   ## wire up "dispatch" so that test db/runner can notify
   app.db.dispatch = wamp_factory.dispatch
   app.runner.dispatch = wamp_factory.dispatch

   ## wrap in a Twisted Web resource
   wamp_resource = WebSocketResource(wamp_factory)

   ## we need to wrap our resources, since the Klein Twisted Web resource
   ## does not seem to support putChild(), and we want to have a WebSocket
   ## resource under path "/ws" and our static file serving under "/static"
   root_resource = WSGIRootResource(app.resource(),
      {
         'static': static_resource,
         'ws': wamp_resource
      }
   )

   ## serve everything from one port
   reactor.listenTCP(port, Site(root_resource), interface = "0.0.0.0")

   return True


@inlineCallbacks
def startFuzzingService(self):
   spec = self._loadSpec()

   if self.mode == 'fuzzingwampclient':

      testSet = WampCaseSet()
      testDb = TestDb([testSet])
      testRunner = FuzzingWampClient(testDb)

      runId, resultIds = yield testRunner.run(spec)

      print
      print "Tests finished: run ID %s, result IDs %d" % (runId, len(resultIds))
      print

      summary = yield testDb.getTestRunSummary(runId)
      tab = Tabify(['l32', 'r5', 'r5'])
      print
      print tab.tabify(['Testee', 'Pass', 'Fail'])
      print tab.tabify()
      #for t in sorted(summary.keys()):
      for t in summary:
         print tab.tabify([t['name'], t['passed'], t['failed']])
      print

      #for rid in resultIds:
      #   res = yield testDb.getResult(rid)
      #   print r.runId, r.id, r.passed, r.started, r.ended, r.ended - r.started
      #   #pprint(result)

      reactor.stop()

   elif self.mode == 'fuzzingwampserver':
      raise Exception("not implemented")

   else:
      raise Exception("logic error")


########NEW FILE########
__FILENAME__ = wamptestee
###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from autobahn.wamp1 import protocol as wamp
import types


# Test case IDs for the echo service
ECHO_NUMBER_ID = "3.1.1"
ECHO_STRING_ID = "3.1.2"
ECHO_DATE_ID = "1.3.1"


class EchoService(object):
    """
    Provides a simple 'echo' service: returns whatever it receives.
    """

    def echo(self, val):
        return val


# Test case ID for the string service
CONCAT_STRINGS_ID = "1.1.5"


class StringService(object):
    """
    Provides basic string services.
    """

    def concat(self, str_1, str_2):
        """
        Concatenates two strings and returns the resulting string.
        """
        assert type(str_1) == types.StringType
        assert type(str_2) == types.StringType
        return str_1 + str_2


# Test case IDs for the number service
ADD_TWO_NUMBERS_ID = "1.2.4"
ADD_THREE_NUMBERS_ID = "1.2.5"


class NumberService(object):
    """
    Provides a simple service for calculating with numbers.
    """

    def add(self, *numbers):
        """
        Adds an unspecified number of numbers and returns the result.
        """
        assert len(numbers) >= 2
        assert [n for n in numbers if type(n) not in [types.IntType,
                                                      types.FloatType,
                                                      types.LongType]] == []
        return sum(numbers)


# Template for creating an URI used for registering a method
URI_CASE_TEMPLATE = "http://api.testsuite.wamp.ws/case/%s"


def setupUri(case, ref=None):
    """
    Prepares the URI for registering a certain service.
    """
    assert type(ref) in (types.NoneType, types.IntType)
    uri = URI_CASE_TEMPLATE % case
    if ref is not None:
        uri = "%s#%s" % (uri, ref)
    return uri



class MyTopicService:

   def __init__(self, allowedTopicIds):
      self.allowedTopicIds = allowedTopicIds
      self.serial = 0


   @wamp.exportSub("foobar", True)
   def subscribe(self, topicUriPrefix, topicUriSuffix):
      """
      Custom topic subscription handler.
      """
      print "client wants to subscribe to %s%s" % (topicUriPrefix, topicUriSuffix)
      try:
         i = int(topicUriSuffix)
         if i in self.allowedTopicIds:
            print "Subscribing client to topic Foobar %d" % i
            return True
         else:
            print "Client not allowed to subscribe to topic Foobar %d" % i
            return False
      except:
         print "illegal topic - skipped subscription"
         return False


   @wamp.exportPub("foobar", True)
   def publish(self, topicUriPrefix, topicUriSuffix, event):
      """
      Custom topic publication handler.
      """
      print "client wants to publish to %s%s" % (topicUriPrefix, topicUriSuffix)
      try:
         i = int(topicUriSuffix)
         if type(event) == dict and event.has_key("count"):
            if event["count"] > 0:
               self.serial += 1
               event["serial"] = self.serial
               print "ok, published enriched event"
               return event
            else:
               print "event count attribute is negative"
               return None
         else:
            print "event is not dict or misses count attribute"
            return None
      except:
         print "illegal topic - skipped publication of event"
         return None



class TesteeWampServerProtocol(wamp.WampServerProtocol):
    """
    A WAMP test server for testing the AutobahnPython WAMP functionality.
    """


    def onSessionOpen(self):
        self.initializePubSub()
        self.initializeServices()
        self.debugWamp = True
        self.debugWs = False
        self.debug = False


    #@wamp.exportRpc("dispatch")
    def testDispatch(self, topic, event, options):
        """
        Simulate a server initiated event controlled by the tester.
        """
        if options.has_key('exclude'):
            exclude = options['exclude']
        else:
            excludeMe = options.get('excludeMe', None)
            if excludeMe is None or excludeMe == True:
                exclude = [self.session_id]
            else:
                exclude = []

        exclude = self.factory.sessionIdsToProtos(exclude)

        eligible = options.get('eligible', None)
        if eligible:
            eligible = self.factory.sessionIdsToProtos(eligible)

        self.factory.dispatch(topic, event, exclude = exclude, eligible = eligible)


    def initializeServices(self):
        """
        Initialize the services and register the RPC methods.
        """
        #self.registerForRpc("http://api.testsuite.wamp.ws/testee/control#", self)
        self.registerMethodForRpc("http://api.testsuite.wamp.ws/testee/control#dispatch", self, TesteeWampServerProtocol.testDispatch)

        self.echo_service = EchoService()
        self.string_service = StringService()
        self.number_service = NumberService()
        for case_id in [ECHO_NUMBER_ID, ECHO_STRING_ID]:
            for idx in range(1, 5):
                self.registerMethodForRpc(setupUri(case_id, idx),
                                          self.echo_service,
                                          EchoService.echo
                                          )
        self.registerMethodForRpc(setupUri(ECHO_DATE_ID),
                                  self.echo_service,
                                  EchoService.echo
                                  )
        self.registerMethodForRpc(setupUri(CONCAT_STRINGS_ID),
                                  self.string_service,
                                  StringService.concat
                                  )
        for case_id in [ADD_TWO_NUMBERS_ID, ADD_THREE_NUMBERS_ID]:
            self.registerMethodForRpc(setupUri(case_id),
                                  self.number_service,
                                  NumberService.add
                                  )

    def initializePubSub(self):
        ## Tests publish events to topics having this prefix.
        ##
        self.registerForPubSub("http://example.com/simple", True)

        ## Tests publish events to this topic expecting events
        ## to be dispatched. Tests also publish to topics with
        ## this URI as prefix, but then expect no dispatching to
        ## happen, since the URI was not registered
        ## with prefix = True.
        ##
        self.registerForPubSub("http://example.com/foobar")

        ## This topic is intentionally left unregistered
        ## Tests will publish to this topic and check that
        ## events are not dispatched.
        ##
        #self.registerForPubSub("http://example.com/barbaz")


        #self.registerForPubSub("http://example.com/event#", True)
        #self.registerForPubSub("http://example.com/event/simple")
        #self.topicservice = MyTopicService([1, 3, 7])
        #self.registerHandlerForPubSub(self.topicservice, "http://example.com/event/")


def startServer(wsuri, sslKey = None, sslCert = None, debug = False):
   factory = WampServerFactory(wsuri, self.debug)
   factory.protocol = TesteeWampServerProtocol

   if sslKey and sslCert:
      sslContext = ssl.DefaultOpenSSLContextFactory(sslKey, sslCert)
   else:
      sslContext = None

   listenWS(factory, sslContext)
   return True

########NEW FILE########
__FILENAME__ = wamptestserver
###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

import math, shelve, decimal

from twisted.internet import reactor, defer

from autobahn.wamp1.protocol import exportRpc, \
                                    exportSub, \
                                    exportPub, \
                                    WampServerFactory, \
                                    WampServerProtocol


class Simple:
   """
   A simple calc service we will export for Remote Procedure Calls (RPC).

   All you need to do is use the @exportRpc decorator on methods
   you want to provide for RPC and register a class instance in the
   server factory (see below).

   The method will be exported under the Python method name, or
   under the (optional) name you can provide as an argument to the
   decorator (see asyncSum()).
   """

   @exportRpc
   def add(self, x, y):
      return x + y

   @exportRpc
   def sub(self, x, y):
      return x - y

   @exportRpc
   def square(self, x):
      if x > 1000:
         ## raise a custom exception
         raise Exception("http://example.com/error#number_too_big",
                         "number %d too big to square" % x)
      return x * x

   @exportRpc
   def sum(self, list):
      return reduce(lambda x, y: x + y, list)

   @exportRpc
   def pickySum(self, list):
      errs = []
      for i in list:
         if i % 3 == 0:
            errs.append(i)
      if len(errs) > 0:
         raise Exception("http://example.com/error#invalid_numbers",
                         "one or more numbers are multiples of 3", errs)
      return reduce(lambda x, y: x + y, list)

   @exportRpc
   def sqrt(self, x):
      return math.sqrt(x)

   @exportRpc("asum")
   def asyncSum(self, list):
      ## Simulate a slow function.
      d = defer.Deferred()
      reactor.callLater(3, d.callback, self.sum(list))
      return d


class KeyValue:
   """
   Simple, persistent key-value store.
   """

   def __init__(self, filename):
      self.store = shelve.open(filename)

   @exportRpc
   def set(self, key = None, value = None):
      if key is not None:
         k = str(key)
         if value is not None:
            self.store[k] = value
         else:
            if self.store.has_key(k):
               del self.store[k]
      else:
         self.store.clear()

   @exportRpc
   def get(self, key = None):
      if key is None:
         return self.store.items()
      else:
         return self.store.get(str(key), None)

   @exportRpc
   def keys(self):
      return self.store.keys()



class Calculator:
   """
   Woooohoo. Simple decimal arithmetic calculator.
   """

   def __init__(self):
      self.clear()

   def clear(self, arg = None):
      self.op = None
      self.current = decimal.Decimal(0)

   @exportRpc
   def calc(self, arg):

      op = arg["op"]

      if op == "C":
         self.clear()
         return str(self.current)

      num = decimal.Decimal(arg["num"])
      if self.op:
         if self.op == "+":
            self.current += num
         elif self.op == "-":
            self.current -= num
         elif self.op == "*":
            self.current *= num
         elif self.op == "/":
            self.current /= num
         self.op = op
      else:
         self.op = op
         self.current = num

      res = str(self.current)
      if op == "=":
         self.clear()

      return res


class MyTopicService:

   def __init__(self, allowedTopicIds):
      self.allowedTopicIds = allowedTopicIds
      self.serial = 0


   @exportSub("foobar", True)
   def subscribe(self, topicUriPrefix, topicUriSuffix):
      """
      Custom topic subscription handler.
      """
      print "client wants to subscribe to %s%s" % (topicUriPrefix, topicUriSuffix)
      try:
         i = int(topicUriSuffix)
         if i in self.allowedTopicIds:
            print "Subscribing client to topic Foobar %d" % i
            return True
         else:
            print "Client not allowed to subscribe to topic Foobar %d" % i
            return False
      except:
         print "illegal topic - skipped subscription"
         return False


   @exportPub("foobar", True)
   def publish(self, topicUriPrefix, topicUriSuffix, event):
      """
      Custom topic publication handler.
      """
      print "client wants to publish to %s%s" % (topicUriPrefix, topicUriSuffix)
      try:
         i = int(topicUriSuffix)
         if type(event) == dict and event.has_key("count"):
            if event["count"] > 0:
               self.serial += 1
               event["serial"] = self.serial
               print "ok, published enriched event"
               return event
            else:
               print "event count attribute is negative"
               return None
         else:
            print "event is not dict or misses count attribute"
            return None
      except:
         print "illegal topic - skipped publication of event"
         return None



class WampTestServerProtocol(WampServerProtocol):

   def onSessionOpen(self):
      self.initSimpleRpc()
      self.initKeyValue()
      self.initCalculator()
      self.initSimplePubSub()
      self.initPubSubAuth()

   def initSimpleRpc(self):
      ## Simple RPC
      self.simple = Simple()
      self.registerForRpc(self.simple, "http://example.com/simple/calc#")

   def initKeyValue(self):
      ## Key-Value Store
      self.registerForRpc(self.factory.keyvalue, "http://example.com/simple/keyvalue#")

   def initCalculator(self):
      ## Decimal Calculator
      self.calculator = Calculator()
      self.registerForRpc(self.calculator, "http://example.com/simple/calculator#")

   def initSimplePubSub(self):
      ## register a single, fixed URI as PubSub topic
      self.registerForPubSub("http://example.com/simple")

      ## register a URI and all URIs having the string as prefix as PubSub topic
      self.registerForPubSub("http://example.com/event#", True)

      ## register any URI (string) as topic
      #self.registerForPubSub("", True)

   def initPubSubAuth(self):
      ## register a single, fixed URI as PubSub topic
      self.registerForPubSub("http://example.com/event/simple")

      ## register a URI and all URIs having the string as prefix as PubSub topic
      #self.registerForPubSub("http://example.com/event/simple", True)

      ## register any URI (string) as topic
      #self.registerForPubSub("", True)

      ## register a topic handler to control topic subscriptions/publications
      self.topicservice = MyTopicService([1, 3, 7])
      self.registerHandlerForPubSub(self.topicservice, "http://example.com/event/")



class WampTestServerFactory(WampServerFactory):

   protocol = WampTestServerProtocol

   def __init__(self, url, debug = False):
      WampServerFactory.__init__(self, url, debugWamp = debug)
      self.setProtocolOptions(allowHixie76 = True)

      ## the key-value store resides on the factory object, since it is to
      ## be shared among all client connections
      self.keyvalue = KeyValue("keyvalue.dat")

      decimal.getcontext().prec = 20

########NEW FILE########
__FILENAME__ = wsperfcontrol
###############################################################################
##
##  Copyright (C) 2012-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ['startClient', 'startServer']


import sys, json, pprint

from twisted.internet import reactor

from autobahn.twisted.websocket import WebSocketClientFactory, \
                                       WebSocketClientProtocol, \
                                       connectWS

from autobahn.util import newid


class WsPerfControlProtocol(WebSocketClientProtocol):
   """
   A client for wsperf running in server mode.

      stress_test:
         token:               Token included in test results.
         uri:                 WebSocket URI of testee.
         handshake_delay:     Delay in ms between opening new WS connections. What about failed connection attempts?
         connection_count:    How many WS connections to open. Definitely opened, or excluding failed?
         con_duration:        How long the WS sits idle before closing the WS. How does that work if msg_count > 0?
         con_lifetime:        ?
         msg_count:           Number of messages per WS connection.
         msg_size:            Size of each message.
         msg_mode:            ?
         ?:                   ? Any other? What about the other parameters available in message_test?
   """

   WSPERF_CMDS = {"echo": """message_test:uri=%(uri)s;token=%(token)s;size=%(size)d;count=%(count)d;quantile_count=%(quantile_count)d;timeout=%(timeout)d;binary=%(binary)s;sync=%(sync)s;rtts=%(rtts)s;correctness=%(correctness)s;""",
                  "stress": """stress_test:uri=%(uri)s;token=%(token)s;handshake_delay=%(handshake_delay)d;connection_count=%(connection_count)d;%(con_duration)d;msg_count=%(msg_count)d;msg_size=%(msg_size)d;rtts=%(rtts)s;"""
                  }

   def sendNext(self):
      if self.currentTestset == len(self.testsets):
         return True
      else:
         if self.currentTest == len(self.testsets[self.currentTestset][1]):
            self.currentTestset += 1
            self.currentTest = 0
            return self.sendNext()
         else:
            test = self.testsets[self.currentTestset][1][self.currentTest]
            cmd = self.WSPERF_CMDS[test['mode']] % test
            if self.factory.debugWsPerf:
               print "Starting test for testee %s" % test['name']
               print cmd
            sys.stdout.write('.')
            self.sendMessage(cmd)
            self.currentTest += 1
            return False


   def setupTests(self):
      i = 0
      cnt = 0
      for testset in self.factory.spec['testsets']:
         self.testsets.append((testset, []))
         for server in self.factory.spec['servers']:
            for case in testset['cases']:
               id = newid()

               if testset['mode'] == 'echo':
                  test = {'token': id,

                          'mode': testset['mode'],
                          'uri': server['uri'].encode('utf8'),
                          'name': server['name'].encode('utf8'),
                          'quantile_count': testset['options']['quantile_count'],
                          'rtts': 'true' if testset['options']['rtts'] else 'false',

                          'count': case['count'] if case.has_key('count') else testset['options']['count'],
                          'size': case['size'] if case.has_key('size') else testset['options']['size'],

                          'timeout': case['timeout'] if case.has_key('timeout') else testset['options']['timeout'],
                          'binary': 'true' if (case['binary'] if case.has_key('binary') else testset['options']['binary']) else 'false',
                          'sync': 'true' if (case['sync'] if case.has_key('sync') else testset['options']['sync']) else 'false',
                          'correctness': 'exact' if (case['verify'] if case.has_key('verify') else testset['options']['verify']) else 'length',
                          'count': case['count'] if case.has_key('count') else testset['options']['count']
                          }

               else:
                  raise Exception("unknown mode %s" % testset['mode'])

               self.testsets[i][1].append(test)
               cnt += 1
         i += 1
      sys.stdout.write("Running %d tests in total against %d servers: " % (cnt, len(self.factory.spec['servers'])))


   def toMicroSec(self, value, digits = 0):
      return ("%." + str(digits) + "f") % round(float(value), digits)


   def getMicroSec(self, result, field, digits = 0):
      return self.toMicroSec(result['data'][field], digits)


   def onTestsComplete(self):
      print " All tests finished."
      print

      if self.factory.debugWsPerf:
         self.pp.pprint(self.testresults)

      for testset in self.testsets:

         if testset[0]['options'].has_key('outfile'):
            outfilename = testset[0]['options']['outfile']
            outfile = open(outfilename, 'w')
         else:
            outfilename = None
            outfile = sys.stdout

         if testset[0]['options'].has_key('digits'):
            digits = testset[0]['options']['digits']
         else:
            digits = 0

         if testset[0]['options'].has_key('sep'):
            sep = testset[0]['options']['sep']
         else:
            sep = "\t"

         if testset[0]['mode'] == 'echo':
            outfile.write(sep.join(['name', 'outcome', 'count', 'size', 'min', 'median', 'max', 'avg', 'stddev']))

            quantile_count = testset[0]['options']['quantile_count']

            for i in xrange(quantile_count):
               outfile.write(sep)
               outfile.write("q%d" % i)
            outfile.write('\n')
            for test in testset[1]:
               result = self.testresults[test['token']]

               outcome = result['data']['result']
               if outcome == 'connection_failed':
                  outfile.write(sep.join([test['name'], 'UNREACHABLE']))
                  outfile.write('\n')
               elif outcome == 'time_out':
                  outfile.write(sep.join([test['name'], 'TIMEOUT']))
                  outfile.write('\n')
               elif outcome == 'fail':
                  outfile.write(sep.join([test['name'], 'FAILED']))
                  outfile.write('\n')
               elif outcome == 'pass':
                  outfile.write(sep.join([str(x) for x in [test['name'],
                                                           'PASSED',
                                                           test['count'],
                                                           test['size'],
                                                           self.getMicroSec(result, 'min', digits),
                                                           self.getMicroSec(result, 'median', digits),
                                                           self.getMicroSec(result, 'max', digits),
                                                           self.getMicroSec(result, 'avg', digits),
                                                           self.getMicroSec(result, 'stddev', digits),
                                                           ]]))
                  for i in xrange(quantile_count):
                     outfile.write(sep)
                     if result['data'].has_key('quantiles'):
                        outfile.write(self.toMicroSec(result['data']['quantiles'][i][1]))
                  outfile.write('\n')
               else:
                  raise Exception("unknown case outcome '%s'" % outcome)

            if outfilename:
               print "Test data written to %s." % outfilename

         else:
            raise Exception("logic error")

      reactor.stop()


   def onOpen(self):
      self.pp = pprint.PrettyPrinter(indent = 3)
      self.testresults = {}
      self.testsets = []
      self.currentTestset = 0
      self.currentTest = 0
      self.setupTests()
      self.sendNext()


   def onMessage(self, msg, binary):
      if not binary:
         try:
            o = json.loads(msg)
            if o['type'] == u'test_complete':
               if self.sendNext():
                  self.onTestsComplete()
            elif o['type'] == u'test_data':
               if self.factory.debugWsPerf:
                  self.pp.pprint(o)
               self.testresults[o['token']] = o
         except ValueError, e:
            pass


class WsPerfControlFactory(WebSocketClientFactory):

   protocol = WsPerfControlProtocol



def startClient(wsuri, spec, debug = False):
   factory = WsPerfControlFactory(wsuri)
   factory.spec = spec
   factory.debugWsPerf = spec['options']['debug']
   connectWS(factory)
   return True

########NEW FILE########
__FILENAME__ = wsperfmaster
###############################################################################
##
##  Copyright (C) 2012-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################


__all__ = ['startServer']


import sys, json, pprint

from twisted.python import log

from autobahn.util import newid, utcnow

from autobahn.websocket.http import HttpException, \
                                    BAD_REQUEST

from autobahn.twisted.websocket import listenWS, \
                                       WebSocketServerFactory, \
                                       WebSocketServerProtocol

from autobahn.wamp1.protocol import WampServerFactory, \
                                    WampServerProtocol, \
                                    exportRpc


URI_RPC = "http://wsperf.org/api#"
URI_EVENT = "http://wsperf.org/event#"



class WsPerfMasterProtocol(WebSocketServerProtocol):

   WSPERF_PROTOCOL_ERROR = 3000
   WSPERF_CMD = """message_test:uri=%(uri)s;token=%(token)s;size=%(size)d;count=%(count)d;quantile_count=%(quantile_count)d;timeout=%(timeout)d;binary=%(binary)s;sync=%(sync)s;rtts=%(rtts)s;correctness=%(correctness)s;"""

   def toMicroSec(self, value):
      return ("%." + str(self.factory.digits) + "f") % round(float(value), self.factory.digits)

   def getMicroSec(self, result, field):
      return self.toMicroSec(result['data'][field])

   def onConnect(self, connectionRequest):
      if 'wsperf' in connectionRequest.protocols:
         return 'wsperf'
      else:
         raise HttpException(BAD_REQUEST[0], "You need to speak wsperf subprotocol with this server!")

   def onOpen(self):
      self.pp = pprint.PrettyPrinter(indent = 3)
      self.slaveConnected = False
      self.slaveId = newid()

   def onClose(self, wasClean, code, reason):
      self.factory.removeSlave(self)
      self.slaveConnected = False
      self.slaveId = None

   def runCase(self, workerRunId, caseDef):
      test = {'uri': caseDef['uri'].encode('utf8'),
              'name': "foobar",
              'count': caseDef['count'],
              'quantile_count': caseDef['quantile_count'],
              'timeout': caseDef['timeout'],
              'binary': 'true' if caseDef['binary'] else 'false',
              'sync': 'true' if caseDef['sync'] else 'false',
              'rtts': 'true' if False else 'false',
              'correctness': str(caseDef['correctness']),
              'size': caseDef['size'],
              'token': workerRunId}

      cmd = self.WSPERF_CMD % test
      if self.factory.debugWsPerf:
         self.pp.pprint(cmd)
      self.sendMessage(cmd)
      return self.slaveId

   def protocolError(self, msg):
      self.sendClose(self, self.WSPERF_PROTOCOL_ERROR, msg)
      log.err("WSPERF_PROTOCOL_ERROR - %s" % msg)

   def onMessage(self, msg, binary):
      if not binary:
         if msg is not None:
            try:
               o = json.loads(msg)
               if self.factory.debugWsPerf:
                  self.pp.pprint(o)

               ## ERROR
               if o['type'] == u'error':
                  log.err("received ERROR")
                  self.pp.pprint(o)

               ## START
               elif o['type'] == u'test_start':
                  workerRunId = o['token']
                  workerId = o['data']['worker_id']
                  self.factory.caseStarted(workerRunId, workerId)

               ## DATA
               elif o['type'] == u'test_data':
                  workerRunId = o['token']
                  result = o['data']
                  self.factory.caseResult(workerRunId, result)

               ## COMPLETE
               elif o['type'] == u'test_complete':
                  workerRunId = o['token']
                  self.factory.caseCompleted(workerRunId)

               ## WELCOME
               elif o['type'] == u'test_welcome':
                  if self.slaveConnected:
                     self.protocolError("duplicate welcome message")
                  else:
                     self.slaveConnected = True
                     self.factory.addSlave(self, self.slaveId, self.peer.host, self.peer.port, o['version'], o['num_workers'], o['ident'])

            except ValueError, e:
               self.protocolError("could not decode text message as JSON (%s)" % str(e))
         else:
            self.protocolError("unexpected empty message")
      else:
         self.protocolError("unexpected binary message")



class WsPerfMasterFactory(WebSocketServerFactory):

   protocol = WsPerfMasterProtocol

   def startFactory(self):
      self.slavesToProtos = {}
      self.protoToSlaves = {}
      self.slaves = {}
      self.runs = {}
      self.workerRunsToRuns = {}

   def addSlave(self, proto, id, host, port, version, num_workers, ident):
      if not self.protoToSlaves.has_key(proto):
         self.protoToSlaves[proto] = id
      else:
         raise Exception("logic error - duplicate proto in addSlave")
      if not self.slavesToProtos.has_key(id):
         self.slavesToProtos[id] = proto
      else:
         raise Exception("logic error - duplicate id in addSlave")
      self.slaves[id] = {'id': id, 'host': host, 'port': port, 'version': version, 'ident': ident, 'num_workers': num_workers}
      self.uiFactory.slaveConnected(id, host, port, version, num_workers, ident)

   def removeSlave(self, proto):
      if self.protoToSlaves.has_key(proto):
         id = self.protoToSlaves[proto]
         del self.protoToSlaves[proto]
         if self.slavesToProtos.has_key(id):
            del self.slavesToProtos[id]
         if self.slaves.has_key(id):
            del self.slaves[id]
         self.uiFactory.slaveDisconnected(id)

   def getSlaves(self):
      return self.slaves.values()

   def runCase(self, caseDef):
      """
      Start a new test run on all currently connected slaves.
      """
      runId = newid()
      self.runs[runId] = {}
      workerRunCount = 0
      for proto in self.protoToSlaves:
         workerRunId = newid()
         slaveId = proto.runCase(workerRunId, caseDef)
         self.runs[runId][workerRunId] = {'slaveId': slaveId,
                                          'results': []}
         self.workerRunsToRuns[workerRunId] = runId
      return runId

   def caseStarted(self, workerRunId, workerId):
      runId = self.workerRunsToRuns[workerRunId]
      run = self.runs[runId][workerRunId]
      run['workerId'] = workerId

   def caseResult(self, workerRunId, result):
      runId = self.workerRunsToRuns[workerRunId]
      run = self.runs[runId][workerRunId]
      run['results'].append(result)
      self.uiFactory.caseResult(runId,
                                run['slaveId'],
                                run['workerId'],
                                result)

   def caseCompleted(self, workerRunId):
      runId = self.workerRunsToRuns[workerRunId]
      #del self.workerRunsToRuns[workerRunId]
      #del self.runs[runId]



class WsPerfMasterUiProtocol(WampServerProtocol):

   @exportRpc
   def runCase(self, caseDef):
      return self.factory.runCase(caseDef)

   @exportRpc
   def getSlaves(self):
      return self.factory.getSlaves()

   def onSessionOpen(self):
      self.registerForRpc(self, URI_RPC)
      self.registerForPubSub(URI_EVENT, True)


class WsPerfMasterUiFactory(WampServerFactory):

   protocol = WsPerfMasterUiProtocol

   def slaveConnected(self, id, host, port, version, num_workers, ident):
      self._dispatchEvent(URI_EVENT + "slaveConnected", {'id': id,
                                                         'host': host,
                                                         'port': port,
                                                         'version': version,
                                                         'num_workers': num_workers,
                                                         'ident': ident})

   def slaveDisconnected(self, id):
      self._dispatchEvent(URI_EVENT + "slaveDisconnected", {'id': id})

   def getSlaves(self):
      return self.slaveFactory.getSlaves()

   def runCase(self, caseDef):
      return self.slaveFactory.runCase(caseDef)

   def caseResult(self, runId, slaveId, workerId, result):
      event = {'runId': runId,
               'slaveId': slaveId,
               'workerId': workerId,
               'result': result}
      self._dispatchEvent(URI_EVENT + "caseResult", event)



def startServer(self, debug = False):
   ## WAMP Server for wsperf slaves
   ##
   wsperf = WsPerfMasterFactory("ws://localhost:9090")
   wsperf.debugWsPerf = debug
   listenWS(wsperf)

   ## Web Server for UI static files
   ##
   webdir = File(pkg_resources.resource_filename("autobahntestsuite", "web/wsperfmaster"))
   web = Site(webdir)
   reactor.listenTCP(8080, web)

   ## WAMP Server for UI
   ##
   wsperfUi = WsPerfMasterUiFactory("ws://localhost:9091")
   wsperfUi.debug = debug
   wsperfUi.debugWamp = debug
   listenWS(wsperfUi)

   ## Connect servers
   ##
   wsperf.uiFactory = wsperfUi
   wsperfUi.slaveFactory = wsperf

########NEW FILE########
__FILENAME__ = wstest
###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

## don't touch: must be first import!
import choosereactor

import os, json, sys, pkg_resources

from twisted.internet import reactor
from twisted.python import log, usage
from twisted.internet.defer import Deferred


## for versions
import autobahn
import autobahntestsuite
from autobahn.websocket.utf8validator import Utf8Validator
from autobahn.websocket.xormasker import XorMaskerNull

## WebSocket testing modes
import testee
import fuzzing

## WAMP testing modes
import wamptestee
import wampfuzzing

## Misc testing modes
import echo
import broadcast
import massconnect
import wsperfcontrol
import wsperfmaster
import serializer


from spectemplate import SPEC_FUZZINGSERVER, \
                         SPEC_FUZZINGCLIENT, \
                         SPEC_FUZZINGWAMPSERVER, \
                         SPEC_FUZZINGWAMPCLIENT, \
                         SPEC_WSPERFCONTROL, \
                         SPEC_MASSCONNECT



class WsTestOptions(usage.Options):
   """
   Reads options from the command-line and checks them for plausibility.
   """

   # Available modes, specified with the --mode (or short: -m) flag.
   MODES = ['echoserver',
            'echoclient',
            'broadcastclient',
            'broadcastserver',
            'fuzzingserver',
            'fuzzingclient',
            #'fuzzingwampserver',
            #'fuzzingwampclient',
            'testeeserver',
            'testeeclient',
            #'wsperfcontrol',
            #'wsperfmaster',
            #'wampserver',
            #'wamptesteeserver',
            #'wampclient',
            'massconnect',
            #'web',
            #'import',
            #'export',
            'serializer'
            ]

   # Modes that need a specification file
   MODES_NEEDING_SPEC = ['fuzzingclient',
                         'fuzzingserver',
                         'fuzzingwampserver',
                         'fuzzingwampclient',
                         'wsperfcontrol',
                         'massconnect',
                         'import']

   # Modes that need a Websocket URI
   MODES_NEEDING_WSURI = ['echoclient',
                          'echoserver',
                          'broadcastclient',
                          'broadcastserver',
                          'testeeclient',
                          'testeeserver',
                          'wsperfcontrol',
                          'wampserver',
                          'wampclient',
                          'wamptesteeserver']

   # Default content of specification files for various modes
   DEFAULT_SPECIFICATIONS = {'fuzzingclient':     SPEC_FUZZINGCLIENT,
                             'fuzzingserver':     SPEC_FUZZINGSERVER,
                             'wsperfcontrol':     SPEC_WSPERFCONTROL,
                             'massconnect':       SPEC_MASSCONNECT,
                             'fuzzingwampclient': SPEC_FUZZINGWAMPCLIENT,
                             'fuzzingwampserver': SPEC_FUZZINGWAMPSERVER}

   optParameters = [
      ['mode', 'm', None, 'Test mode, one of: %s [required]' % ', '.join(MODES)],
      ['testset', 't', None, 'Run a test set from an import test spec.'],
      ['spec', 's', None, 'Test specification file [required in some modes].'],
      ['outfile', 'o', None, 'Output filename for modes that generate testdata.'],
      ['wsuri', 'w', None, 'WebSocket URI [required in some modes].'],
      ['ident', 'i', None, ('Testee client identifier [optional for client testees].')],
      ['key', 'k', None, ('Server private key file for secure WebSocket (WSS) [required in server modes for WSS].')],
      ['cert', 'c', None, ('Server certificate file for secure WebSocket (WSS) [required in server modes for WSS].')]
   ]

   optFlags = [
      ['debug', 'd', 'Debug output [default: off].'],
      ['autobahnversion', 'a', 'Print version information for Autobahn and AutobahnTestSuite.']
   ]

   def postOptions(self):
      """
      Process the given options. Perform plausibility checks, etc...
      """

      if self['autobahnversion']:
         print "Autobahn %s" % autobahn.version
         print "AutobahnTestSuite %s" % autobahntestsuite.version
         sys.exit(0)

      if not self['mode']:
         raise usage.UsageError, "a mode must be specified to run!"

      if self['mode'] not in WsTestOptions.MODES:
         raise usage.UsageError, (
            "Mode '%s' is invalid.\nAvailable modes:\n\t- %s" % (
               self['mode'], "\n\t- ".join(sorted(WsTestOptions.MODES))))

      if (self['mode'] in WsTestOptions.MODES_NEEDING_WSURI and not self['wsuri']):
         raise usage.UsageError, "mode needs a WebSocket URI!"



class WsTestRunner(object):
   """
   Testsuite driver.
   """

   def __init__(self, options, spec = None):
      self.options = options
      self.spec = spec

      self.debug = self.options.get('debug', False)
      if self.debug:
         log.startLogging(sys.stdout)

      self.mode = str(self.options['mode'])


   def startService(self):
      """
      Start mode specific services.
      """
      print
      print "Using Twisted reactor class %s" % str(reactor.__class__)
      print "Using UTF8 Validator class %s" % str(Utf8Validator)
      print "Using XOR Masker classes %s" % str(XorMaskerNull)
      #print "Using JSON processor module '%s'" % str(autobahn.wamp.json_lib.__name__)
      print

      if self.mode == "import":
         return self.startImportSpec(self.options['spec'])

      elif self.mode == "export":
         return self.startExportSpec(self.options['testset'], self.options.get('spec', None))

      elif self.mode == "fuzzingwampclient":
         return self.startFuzzingWampClient(self.options['testset'])

      elif self.mode == "web":
         return self.startWeb(debug = self.debug)

      elif self.mode == "testeeclient":
         return testee.startClient(self.options['wsuri'], ident = self.options['ident'], debug = self.debug)

      elif self.mode == "testeeserver":
         return testee.startServer(self.options['wsuri'], debug = self.debug)

      elif self.mode == "broadcastclient":
         return broadcast.startClient(self.options['wsuri'], debug = self.debug)

      elif self.mode == "broadcastserver":
         return broadcast.startServer(self.options['wsuri'], debug = self.debug)

      elif self.mode == "echoclient":
         return echo.startClient(self.options['wsuri'], debug = self.debug)

      elif self.mode == "echoserver":
         return echo.startServer(self.options['wsuri'], debug = self.debug)

      elif self.mode == "fuzzingclient":
         return fuzzing.startClient(self.spec, debug = self.debug)

      elif self.mode == "fuzzingserver":
         return fuzzing.startServer(self.spec, debug = self.debug)

      elif self.mode == "wsperfcontrol":
         return wsperfcontrol.startClient(self.options['wsuri'], self.spec, debug = self.debug)

      elif self.mode == "wsperfmaster":
         return wsperfmaster.startServer(debug = self.debug)

      elif self.mode == "massconnect":
         return massconnect.startClient(self.spec, debug = self.debug)

      elif self.mode == "serializer":
         return serializer.start(outfilename = self.options['outfile'], debug = self.debug)

      else:
         raise Exception("no mode '%s'" % self.mode)



def start(options, spec = None):
   """
   Actually startup a wstest run.

   :param options: Global options controlling wstest.
   :type options: dict
   :param spec: Test specification needed for certain modes. If none is given, but
                a spec is needed, a default spec is used.
   :type spec: dict
   """
   if options['mode'] in WsTestOptions.MODES_NEEDING_SPEC and spec is None:
      spec = json.loads(WsTestOptions.DEFAULT_SPECIFICATIONS[options['mode']])

   wstest = WsTestRunner(options, spec)
   res = wstest.startService()

   ## only start reactor for modes needing it
   ##
   if res:
      ## if mode wants to shutdown reactor after done (e.g. clients),
      ## hook up machinery to do so
      ##
      if isinstance(res, Deferred):
         def shutdown(_):
            reactor.stop()
         res.addBoth(shutdown)
      reactor.run()



def run():
   """
   Run wstest from command line. This parses command line args etc.
   """

   ## parse wstest command lines options
   ##
   cmdOpts = WsTestOptions()
   try:
      cmdOpts.parseOptions()
   except usage.UsageError, errortext:
      print '%s %s\n' % (sys.argv[0], errortext)
      print 'Try %s --help for usage details\n' % sys.argv[0]
      sys.exit(1)
   else:
      options = cmdOpts.opts

   ## check if mode needs a spec ..
   ##
   if options['mode'] in WsTestOptions.MODES_NEEDING_SPEC:

      ## .. if none was given ..
      ##
      if not options['spec']:

         ## .. assume canonical specfile name ..
         ##
         filename = "%s.json" % options['mode']
         options['spec'] = filename

         if not os.path.isfile(filename):

            ## .. if file does not exist, autocreate a spec file
            ##
            content = WsTestOptions.DEFAULT_SPECIFICATIONS[options['mode']]
            print "Auto-generating spec file '%s'" % filename
            f = open(filename, 'w')
            f.write(content)
            f.close()
         else:
            ## .. use existing one
            ##
            print "Using implicit spec file '%s'" % filename

      else:
         ## use explicitly given specfile
         ##
         print "Using explicit spec file '%s'" % options['spec']

      ## now load the spec ..
      ##
      spec_filename = os.path.abspath(options['spec'])
      print "Loading spec from %s" % spec_filename
      spec = json.loads(open(spec_filename).read())

   else:
      ## mode does not rely on spec
      ##
      spec = None

   ## now start a wstest run ..
   ##
   start(options, spec)



if __name__ == '__main__':
   run()

########NEW FILE########
__FILENAME__ = _version
###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__version__ = "0.6.2"

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# AutobahnTestsuite documentation build configuration file, created by
# sphinx-quickstart on Thu Mar 20 15:17:08 2014.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'AutobahnTestsuite'
copyright = u'2011-2014 <a href="http://tavendo.com">Tavendo GmbH</a>, <a href="http://creativecommons.org/licenses/by-sa/3.0/">Creative Commons CC-BY-SA</a><br>Tavendo, WAMP and "Autobahn WebSocket" are trademarks of <a href="http://tavendo.com">Tavendo GmbH</a>'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.6.1'
# The full version, including alpha/beta/rc tags.
release = '0.6.1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all
# documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
#pygments_style = 'sphinx'
pygments_style = 'flask_theme_support.FlaskyStyle'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#html_theme = 'default'

sys.path.append(os.path.abspath('_themes'))
html_theme_path = ['_themes']
html_theme = 'kr'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

# additional variables which become accessible in the template engine's context for
# all pages
# html_context = {'widgeturl': 'http://192.168.1.147:8090/widget'}
html_context = {'widgeturl': 'https://demo.crossbar.io/clandeckwidget'}

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

html_sidebars = {
    # 'index':    ['side-primary.html', 'searchbox.html'],
    '**':       ['side-secondary.html', 'stay_informed.html', 'sidetoc.html',
                 'previous_next.html', 'searchbox.html' ]
}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'AutobahnTestsuitedoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'AutobahnTestsuite.tex', u'AutobahnTestsuite Documentation',
   u'Tavendo GmbH', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'autobahntestsuite', u'AutobahnTestsuite Documentation',
     [u'Tavendo GmbH'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'AutobahnTestsuite', u'AutobahnTestsuite Documentation',
   u'Tavendo GmbH', 'AutobahnTestsuite', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}


rst_epilog = """
.. |ab| replace:: **Autobahn**\|Testsuite
"""

rst_prolog = """
.. container:: topnav

   :doc:`Overview <index>`   :doc:`installation`  :doc:`usage` :doc:`table_of_contents`

"""

########NEW FILE########
__FILENAME__ = flask_theme_support
# flasky extensions.  flasky pygments style based on tango style
from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Whitespace, Punctuation, Other, Literal


class FlaskyStyle(Style):
    background_color = "#f8f8f8"
    default_style = ""

    styles = {
        # No corresponding class for the following:
        #Text:                     "", # class:  ''
        Whitespace:                "underline #f8f8f8",      # class: 'w'
        Error:                     "#a40000 border:#ef2929", # class: 'err'
        Other:                     "#000000",                # class 'x'

        Comment:                   "italic #8f5902", # class: 'c'
        Comment.Preproc:           "noitalic",       # class: 'cp'

        Keyword:                   "bold #004461",   # class: 'k'
        Keyword.Constant:          "bold #004461",   # class: 'kc'
        Keyword.Declaration:       "bold #004461",   # class: 'kd'
        Keyword.Namespace:         "bold #004461",   # class: 'kn'
        Keyword.Pseudo:            "bold #004461",   # class: 'kp'
        Keyword.Reserved:          "bold #004461",   # class: 'kr'
        Keyword.Type:              "bold #004461",   # class: 'kt'

        Operator:                  "#582800",   # class: 'o'
        Operator.Word:             "bold #004461",   # class: 'ow' - like keywords

        Punctuation:               "bold #000000",   # class: 'p'

        # because special names such as Name.Class, Name.Function, etc.
        # are not recognized as such later in the parsing, we choose them
        # to look the same as ordinary variables.
        Name:                      "#000000",        # class: 'n'
        Name.Attribute:            "#c4a000",        # class: 'na' - to be revised
        Name.Builtin:              "#004461",        # class: 'nb'
        Name.Builtin.Pseudo:       "#3465a4",        # class: 'bp'
        Name.Class:                "#000000",        # class: 'nc' - to be revised
        Name.Constant:             "#000000",        # class: 'no' - to be revised
        Name.Decorator:            "#888",           # class: 'nd' - to be revised
        Name.Entity:               "#ce5c00",        # class: 'ni'
        Name.Exception:            "bold #cc0000",   # class: 'ne'
        Name.Function:             "#000000",        # class: 'nf'
        Name.Property:             "#000000",        # class: 'py'
        Name.Label:                "#f57900",        # class: 'nl'
        Name.Namespace:            "#000000",        # class: 'nn' - to be revised
        Name.Other:                "#000000",        # class: 'nx'
        Name.Tag:                  "bold #004461",   # class: 'nt' - like a keyword
        Name.Variable:             "#000000",        # class: 'nv' - to be revised
        Name.Variable.Class:       "#000000",        # class: 'vc' - to be revised
        Name.Variable.Global:      "#000000",        # class: 'vg' - to be revised
        Name.Variable.Instance:    "#000000",        # class: 'vi' - to be revised

        Number:                    "#990000",        # class: 'm'

        Literal:                   "#000000",        # class: 'l'
        Literal.Date:              "#000000",        # class: 'ld'

        String:                    "#4e9a06",        # class: 's'
        String.Backtick:           "#4e9a06",        # class: 'sb'
        String.Char:               "#4e9a06",        # class: 'sc'
        String.Doc:                "italic #8f5902", # class: 'sd' - like a comment
        String.Double:             "#4e9a06",        # class: 's2'
        String.Escape:             "#4e9a06",        # class: 'se'
        String.Heredoc:            "#4e9a06",        # class: 'sh'
        String.Interpol:           "#4e9a06",        # class: 'si'
        String.Other:              "#4e9a06",        # class: 'sx'
        String.Regex:              "#4e9a06",        # class: 'sr'
        String.Single:             "#4e9a06",        # class: 's1'
        String.Symbol:             "#4e9a06",        # class: 'ss'

        Generic:                   "#000000",        # class: 'g'
        Generic.Deleted:           "#a40000",        # class: 'gd'
        Generic.Emph:              "italic #000000", # class: 'ge'
        Generic.Error:             "#ef2929",        # class: 'gr'
        Generic.Heading:           "bold #000080",   # class: 'gh'
        Generic.Inserted:          "#00A000",        # class: 'gi'
        Generic.Output:            "#888",           # class: 'go'
        Generic.Prompt:            "#745334",        # class: 'gp'
        Generic.Strong:            "bold #000000",   # class: 'gs'
        Generic.Subheading:        "bold #800080",   # class: 'gu'
        Generic.Traceback:         "bold #a40000",   # class: 'gt'
    }

########NEW FILE########
