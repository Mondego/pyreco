__FILENAME__ = simple_server
""" WebSocket test resource.

This code will run a websocket resource on 8080 and reachable at ws://localhost:8080/test.
For compatibility with web-socket-js (a fallback to Flash for browsers that do not yet support
WebSockets) a policy server will also start on port 843.
See: http://github.com/gimite/web-socket-js
"""

__author__ = 'Reza Lotun'


from datetime import datetime

from twisted.internet.protocol import Protocol, Factory
from twisted.web import resource
from twisted.web.static import File
from twisted.internet import task

from websocket import WebSocketHandler, WebSocketSite


class Testhandler(WebSocketHandler):
    def __init__(self, transport):
        WebSocketHandler.__init__(self, transport)
        self.periodic_call = task.LoopingCall(self.send_time)

    def __del__(self):
        print 'Deleting handler'

    def send_time(self):
        # send current time as an ISO8601 string
        data = datetime.utcnow().isoformat().encode('utf8')
        self.transport.write(data)

    def frameReceived(self, frame):
        print 'Peer: ', self.transport.getPeer()
        self.transport.write(frame)
        self.periodic_call.start(0.5)

    def connectionMade(self):
        print 'Connected to client.'
        # here would be a good place to register this specific handler
        # in a dictionary mapping some client identifier (like IPs) against
        # self (this handler object)

    def connectionLost(self, reason):
        print 'Lost connection.'
        self.periodic_call.stop()
        del self.periodic_call
        # here is a good place to deregister this handler object


class FlashSocketPolicy(Protocol):
    """ A simple Flash socket policy server.
    See: http://www.adobe.com/devnet/flashplayer/articles/socket_policy_files.html
    """
    def connectionMade(self):
        policy = '<?xml version="1.0"?><!DOCTYPE cross-domain-policy SYSTEM ' \
                 '"http://www.macromedia.com/xml/dtds/cross-domain-policy.dtd">' \
                 '<cross-domain-policy><allow-access-from domain="*" to-ports="*" /></cross-domain-policy>'
        self.transport.write(policy)
        self.transport.loseConnection()



if __name__ == "__main__":
    from twisted.internet import reactor

    # run our websocket server
    # serve index.html from the local directory
    root = File('.')
    site = WebSocketSite(root)
    site.addHandler('/test', Testhandler)
    reactor.listenTCP(8080, site)
    # run policy file server
    factory = Factory()
    factory.protocol = FlashSocketPolicy
    reactor.listenTCP(843, factory)
    reactor.run()


########NEW FILE########
__FILENAME__ = test_websocket
# Copyright (c) 2009 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.web.websocket}.
"""

from twisted.internet.main import CONNECTION_DONE
from twisted.internet.error import ConnectionDone
from twisted.python.failure import Failure

from websocket import WebSocketHandler, WebSocketFrameDecoder
from websocket import WebSocketSite, WebSocketTransport

from twisted.web.resource import Resource
from twisted.web.server import Request, Site
from twisted.web.test.test_web import DummyChannel
from twisted.trial.unittest import TestCase



class DummyChannel(DummyChannel):
    """
    A L{DummyChannel} supporting the C{setRawMode} method.

    @ivar raw: C{bool} indicating if C{setRawMode} has been called.
    """

    raw = False

    def setRawMode(self):
        self.raw = True



class TestHandler(WebSocketHandler):
    """
    A L{WebSocketHandler} recording every frame received.

    @ivar frames: C{list} of frames received.
    @ivar lostReason: reason for connection closing.
    """

    def __init__(self, request):
        WebSocketHandler.__init__(self, request)
        self.frames = []
        self.lostReason = None


    def frameReceived(self, frame):
        self.frames.append(frame)


    def connectionLost(self, reason):
        self.lostReason = reason



class WebSocketSiteTestCase(TestCase):
    """
    Tests for L{WebSocketSite}.
    """

    def setUp(self):
        self.site = WebSocketSite(Resource())
        self.site.addHandler("/test", TestHandler)


    def renderRequest(self, headers=None, url="/test", ssl=False,
                      queued=False, body=None):
        """
        Render a request against C{self.site}, writing the WebSocket
        handshake.
        """
        if headers is None:
            headers = [
                ("Upgrade", "WebSocket"), ("Connection", "Upgrade"),
                ("Host", "localhost"), ("Origin", "http://localhost/")]
        channel = DummyChannel()
        if ssl:
            channel.transport = channel.SSL()
        channel.site = self.site
        request = self.site.requestFactory(channel, queued)
        for k, v in headers:
            request.requestHeaders.addRawHeader(k, v)
        request.gotLength(0)
        request.requestReceived("GET", url, "HTTP/1.1")
        if body:
            request.channel._transferDecoder.finishCallback(body)
        return channel


    def test_multiplePostpath(self):
        """
        A resource name can consist of several path elements.
        """
        handlers = []
        def handlerFactory(request):
            handler = TestHandler(request)
            handlers.append(handler)
            return handler
        self.site.addHandler("/foo/bar", handlerFactory)
        channel = self.renderRequest(url="/foo/bar")
        self.assertEquals(len(handlers), 1)
        self.assertFalse(channel.transport.disconnected)


    def test_queryArguments(self):
        """
        A resource name may contain query arguments.
        """
        handlers = []
        def handlerFactory(request):
            handler = TestHandler(request)
            handlers.append(handler)
            return handler
        self.site.addHandler("/test?foo=bar&egg=spam", handlerFactory)
        channel = self.renderRequest(url="/test?foo=bar&egg=spam")
        self.assertEquals(len(handlers), 1)
        self.assertFalse(channel.transport.disconnected)


    def test_noOriginHeader(self):
        """
        If no I{Origin} header is present, the connection is closed.
        """
        channel = self.renderRequest(
            headers=[("Upgrade", "WebSocket"), ("Connection", "Upgrade"),
                     ("Host", "localhost")])
        self.assertFalse(channel.transport.written.getvalue())
        self.assertTrue(channel.transport.disconnected)


    def test_multipleOriginHeaders(self):
        """
        If more than one I{Origin} header is present, the connection is
        dropped.
        """
        channel = self.renderRequest(
            headers=[("Upgrade", "WebSocket"), ("Connection", "Upgrade"),
                     ("Host", "localhost"), ("Origin", "foo"),
                     ("Origin", "bar")])
        self.assertFalse(channel.transport.written.getvalue())
        self.assertTrue(channel.transport.disconnected)


    def test_noHostHeader(self):
        """
        If no I{Host} header is present, the connection is dropped.
        """
        channel = self.renderRequest(
            headers=[("Upgrade", "WebSocket"), ("Connection", "Upgrade"),
                     ("Origin", "http://localhost/")])
        self.assertFalse(channel.transport.written.getvalue())
        self.assertTrue(channel.transport.disconnected)


    def test_multipleHostHeaders(self):
        """
        If more than one I{Host} header is present, the connection is
        dropped.
        """
        channel = self.renderRequest(
            headers=[("Upgrade", "WebSocket"), ("Connection", "Upgrade"),
                     ("Origin", "http://localhost/"), ("Host", "foo"),
                     ("Host", "bar")])
        self.assertFalse(channel.transport.written.getvalue())
        self.assertTrue(channel.transport.disconnected)


    def test_missingHandler(self):
        """
        If no handler is registered for the given resource, the connection is
        dropped.
        """
        channel = self.renderRequest(url="/foo")
        self.assertFalse(channel.transport.written.getvalue())
        self.assertTrue(channel.transport.disconnected)


    def test_noConnectionUpgrade(self):
        """
        If the I{Connection: Upgrade} header is not present, the connection is
        dropped.
        """
        channel = self.renderRequest(
            headers=[("Upgrade", "WebSocket"), ("Host", "localhost"),
                     ("Origin", "http://localhost/")])
        self.assertIn("404 Not Found", channel.transport.written.getvalue())


    def test_noUpgradeWebSocket(self):
        """
        If the I{Upgrade: WebSocket} header is not present, the connection is
        dropped.
        """
        channel = self.renderRequest(
            headers=[("Connection", "Upgrade"), ("Host", "localhost"),
                     ("Origin", "http://localhost/")])
        self.assertIn("404 Not Found", channel.transport.written.getvalue())


    def test_render(self):
        """
        If the handshake is successful, we can read back the server handshake,
        and the channel is setup for raw mode.
        """
        channel = self.renderRequest()
        self.assertTrue(channel.raw)
        self.assertEquals(
            channel.transport.written.getvalue(),
            "HTTP/1.1 101 Web Socket Protocol Handshake\r\n"
            "Upgrade: WebSocket\r\n"
            "Connection: Upgrade\r\n"
            "WebSocket-Origin: http://localhost/\r\n"
            "WebSocket-Location: ws://localhost/test\r\n\r\n")
        self.assertFalse(channel.transport.disconnected)

    def test_render_handShake76(self):
        """
        Test a hixie-76 handShake.
        """
        # we need to construct a challenge
        key1 = '1x0x0 0y00 0'  # 1000000
        key2 = '1b0b0 000 0'   # 1000000
        body = '12345678'
        headers = [
            ("Upgrade", "WebSocket"), ("Connection", "Upgrade"),
            ("Host", "localhost"), ("Origin", "http://localhost/"),
            ("Sec-WebSocket-Key1", key1), ("Sec-WebSocket-Key2", key2)]
        channel = self.renderRequest(headers=headers, body=body)

        self.assertTrue(channel.raw)

        result = channel.transport.written.getvalue()

        headers, response = result.split('\r\n\r\n')

        self.assertEquals(
            headers,
            "HTTP/1.1 101 Web Socket Protocol Handshake\r\n"
            "Upgrade: WebSocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Origin: http://localhost/\r\n"
            "Sec-WebSocket-Location: ws://localhost/test")

        # check challenge is correct
        from hashlib import md5
        import struct
        self.assertEquals(md5(struct.pack('>ii8s', 500000, 500000, body)).digest(), response)

        self.assertFalse(channel.transport.disconnected)

    def test_secureRender(self):
        """
        If the WebSocket connection is over SSL, the I{WebSocket-Location}
        header specified I{wss} as scheme.
        """
        channel = self.renderRequest(ssl=True)
        self.assertTrue(channel.raw)
        self.assertEquals(
            channel.transport.written.getvalue(),
            "HTTP/1.1 101 Web Socket Protocol Handshake\r\n"
            "Upgrade: WebSocket\r\n"
            "Connection: Upgrade\r\n"
            "WebSocket-Origin: http://localhost/\r\n"
            "WebSocket-Location: wss://localhost/test\r\n\r\n")
        self.assertFalse(channel.transport.disconnected)


    def test_frameReceived(self):
        """
        C{frameReceived} is called with the received frames after handshake.
        """
        handlers = []
        def handlerFactory(request):
            handler = TestHandler(request)
            handlers.append(handler)
            return handler
        self.site.addHandler("/test2", handlerFactory)
        channel = self.renderRequest(url="/test2")
        self.assertEquals(len(handlers), 1)
        handler = handlers[0]
        channel._transferDecoder.dataReceived("\x00hello\xff\x00boy\xff")
        self.assertEquals(handler.frames, ["hello", "boy"])


    def test_websocketProtocolAccepted(self):
        """
        The I{WebSocket-Protocol} header is echoed by the server if the
        protocol is among the supported protocols.
        """
        self.site.supportedProtocols.append("pixiedust")
        channel = self.renderRequest(
            headers = [
            ("Upgrade", "WebSocket"), ("Connection", "Upgrade"),
            ("Host", "localhost"), ("Origin", "http://localhost/"),
            ("WebSocket-Protocol", "pixiedust")])
        self.assertTrue(channel.raw)
        self.assertEquals(
            channel.transport.written.getvalue(),
            "HTTP/1.1 101 Web Socket Protocol Handshake\r\n"
            "Upgrade: WebSocket\r\n"
            "Connection: Upgrade\r\n"
            "WebSocket-Origin: http://localhost/\r\n"
            "WebSocket-Location: ws://localhost/test\r\n"
            "WebSocket-Protocol: pixiedust\r\n\r\n")
        self.assertFalse(channel.transport.disconnected)


    def test_tooManyWebSocketProtocol(self):
        """
        If more than one I{WebSocket-Protocol} headers are specified, the
        connection is dropped.
        """
        self.site.supportedProtocols.append("pixiedust")
        channel = self.renderRequest(
            headers = [
            ("Upgrade", "WebSocket"), ("Connection", "Upgrade"),
            ("Host", "localhost"), ("Origin", "http://localhost/"),
            ("WebSocket-Protocol", "pixiedust"),
            ("WebSocket-Protocol", "fairymagic")])
        self.assertFalse(channel.transport.written.getvalue())
        self.assertTrue(channel.transport.disconnected)


    def test_unsupportedProtocols(self):
        """
        If the I{WebSocket-Protocol} header specified an unsupported protocol,
        the connection is dropped.
        """
        self.site.supportedProtocols.append("pixiedust")
        channel = self.renderRequest(
            headers = [
            ("Upgrade", "WebSocket"), ("Connection", "Upgrade"),
            ("Host", "localhost"), ("Origin", "http://localhost/"),
            ("WebSocket-Protocol", "fairymagic")])
        self.assertFalse(channel.transport.written.getvalue())
        self.assertTrue(channel.transport.disconnected)


    def test_queued(self):
        """
        Queued requests are unsupported, thus closed by the
        C{WebSocketSite}.
        """
        channel = self.renderRequest(queued=True)
        self.assertFalse(channel.transport.written.getvalue())
        self.assertTrue(channel.transport.disconnected)


    def test_addHandlerWithoutSlash(self):
        """
        C{addHandler} raises C{ValueError} if the resource name doesn't start
        with a slash.
        """
        self.assertRaises(
            ValueError, self.site.addHandler, "test", TestHandler)



class WebSocketFrameDecoderTestCase(TestCase):
    """
    Test for C{WebSocketFrameDecoder}.
    """

    def setUp(self):
        self.channel = DummyChannel()
        request = Request(self.channel, False)
        transport = WebSocketTransport(request)
        handler = TestHandler(transport)
        transport._attachHandler(handler)
        self.decoder = WebSocketFrameDecoder(request, handler)
        self.decoder.MAX_LENGTH = 100


    def test_oneFrame(self):
        """
        We can send one frame handled with one C{dataReceived} call.
        """
        self.decoder.dataReceived("\x00frame\xff")
        self.assertEquals(self.decoder.handler.frames, ["frame"])


    def test_oneFrameSplitted(self):
        """
        A frame can be split into several C{dataReceived} calls, and will be
        combined again when sent to the C{WebSocketHandler}.
        """
        self.decoder.dataReceived("\x00fra")
        self.decoder.dataReceived("me\xff")
        self.assertEquals(self.decoder.handler.frames, ["frame"])


    def test_multipleFrames(self):
        """
        Several frames can be received in a single C{dataReceived} call.
        """
        self.decoder.dataReceived("\x00frame1\xff\x00frame2\xff")
        self.assertEquals(self.decoder.handler.frames, ["frame1", "frame2"])


    def test_missingNull(self):
        """
        If a frame not starting with C{\\x00} is received, the connection is
        dropped.
        """
        self.decoder.dataReceived("frame\xff")
        self.assertTrue(self.channel.transport.disconnected)


    def test_missingNullAfterGoodFrame(self):
        """
        If a frame not starting with C{\\x00} is received after a correct
        frame, the connection is dropped.
        """
        self.decoder.dataReceived("\x00frame\xfffoo")
        self.assertTrue(self.channel.transport.disconnected)
        self.assertEquals(self.decoder.handler.frames, ["frame"])


    def test_emptyReceive(self):
        """
        Received an empty string doesn't do anything.
        """
        self.decoder.dataReceived("")
        self.assertFalse(self.channel.transport.disconnected)


    def test_maxLength(self):
        """
        If a frame is received which is bigger than C{MAX_LENGTH}, the
        connection is dropped.
        """
        self.decoder.dataReceived("\x00" + "x" * 101)
        self.assertTrue(self.channel.transport.disconnected)


    def test_maxLengthFrameCompleted(self):
        """
        If a too big frame is received in several fragments, the connection is
        dropped.
        """
        self.decoder.dataReceived("\x00" + "x" * 90)
        self.decoder.dataReceived("x" * 11 + "\xff")
        self.assertTrue(self.channel.transport.disconnected)


    def test_frameLengthReset(self):
        """
        The length of frames is reset between frame, thus not creating an error
        when the accumulated length exceeds the maximum frame length.
        """
        for i in range(15):
            self.decoder.dataReceived("\x00" + "x" * 10 + "\xff")
        self.assertFalse(self.channel.transport.disconnected)



class WebSocketHandlerTestCase(TestCase):
    """
    Tests for L{WebSocketHandler}.
    """

    def setUp(self):
        self.channel = DummyChannel()
        self.request = request = Request(self.channel, False)
        # Simulate request handling
        request.startedWriting = True
        transport = WebSocketTransport(request)
        self.handler = TestHandler(transport)
        transport._attachHandler(self.handler)


    def test_write(self):
        """
        L{WebSocketTransport.write} adds the required C{\\x00} and C{\\xff}
        around sent frames, and write it to the request.
        """
        self.handler.transport.write("hello")
        self.handler.transport.write("world")
        self.assertEquals(
            self.channel.transport.written.getvalue(),
            "\x00hello\xff\x00world\xff")
        self.assertFalse(self.channel.transport.disconnected)


    def test_close(self):
        """
        L{WebSocketTransport.loseConnection} closes the underlying request.
        """
        self.handler.transport.loseConnection()
        self.assertTrue(self.channel.transport.disconnected)


    def test_connectionLost(self):
        """
        L{WebSocketHandler.connectionLost} is called with the reason of the
        connection closing when L{Request.connectionLost} is called.
        """
        self.request.connectionLost(Failure(CONNECTION_DONE))
        self.handler.lostReason.trap(ConnectionDone)

########NEW FILE########
__FILENAME__ = websocket
# -*- test-case-name: twisted.web.test.test_websocket -*-
# Copyright (c) 2009 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Note: This is from the associated branch for http://twistedmatrix.com/trac/ticket/4173
and includes support for the hixie-76 handshake.

WebSocket server protocol.

See U{http://tools.ietf.org/html/draft-hixie-thewebsocketprotocol} for the
current version of the specification.

@since: 10.1
"""

from hashlib import md5
import struct

from twisted.internet import interfaces
from twisted.web.http import datetimeToString
from twisted.web.http import _IdentityTransferDecoder
from twisted.web.server import Request, Site, version, unquote
from zope.interface import implements


_ascii_numbers = frozenset(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'])

class WebSocketRequest(Request):
    """
    A general purpose L{Request} supporting connection upgrade for WebSocket.
    """

    def process(self):
        if (self.requestHeaders.getRawHeaders("Upgrade") == ["WebSocket"] and
            self.requestHeaders.getRawHeaders("Connection") == ["Upgrade"]):
            return self.processWebSocket()
        else:
            return Request.process(self)

    def processWebSocket(self):
        """
        Process a specific web socket request.
        """
        # get site from channel
        self.site = self.channel.site

        # set various default headers
        self.setHeader("server", version)
        self.setHeader("date", datetimeToString())

        # Resource Identification
        self.prepath = []
        self.postpath = map(unquote, self.path[1:].split("/"))
        self.renderWebSocket()


    def _clientHandshake76(self):
        """
        Complete hixie-76 handshake, which consists of a challenge and response.

        If the request is not identified with a proper WebSocket handshake, the
        connection will be closed. Otherwise, the response to the handshake is
        sent and a C{WebSocketHandler} is created to handle the request.
        """
        def finish():
            self.channel.transport.loseConnection()
        if self.queued:
            return finish()

        secKey1 = self.requestHeaders.getRawHeaders("Sec-WebSocket-Key1", [])
        secKey2 = self.requestHeaders.getRawHeaders("Sec-WebSocket-Key2", [])

        if len(secKey1) != 1 or len(secKey2) != 1:
            return finish()

        # copied
        originHeaders = self.requestHeaders.getRawHeaders("Origin", [])
        if len(originHeaders) != 1:
            return finish()
        hostHeaders = self.requestHeaders.getRawHeaders("Host", [])
        if len(hostHeaders) != 1:
            return finish()
        handlerFactory = self.site.handlers.get(self.uri)
        if not handlerFactory:
            return finish()

        # key1 and key2 exist and are a string of characters
        # filter both keys to get a string with all numbers in order
        key1 = secKey1[0]
        key2 = secKey2[0]
        numBuffer1 = ''.join([x for x in key1 if x in _ascii_numbers])
        numBuffer2 = ''.join([x for x in key2 if x in _ascii_numbers])

        # make sure numbers actually exist
        if not numBuffer1 or not numBuffer2:
            return finish()

        # these should be int-like
        num1 = int(numBuffer1)
        num2 = int(numBuffer2)

        # count the number of spaces in each character string
        numSpaces1 = 0
        for x in key1:
            if x == ' ':
                numSpaces1 += 1
        numSpaces2 = 0
        for x in key2:
            if x == ' ':
                numSpaces2 += 1

        # there should be at least one space in each
        if numSpaces1 == 0 or numSpaces2 == 0:
            return finish()

        # get two resulting numbers, as specified in hixie-76
        num1 = num1 / numSpaces1
        num2 = num2 / numSpaces2

        transport = WebSocketTransport(self)
        handler = handlerFactory(transport)
        transport._attachHandler(handler)

        self.channel.setRawMode()

        def finishHandshake(nonce):
            """ Receive nonce value from request body, and calculate repsonse. """
            protocolHeaders = self.requestHeaders.getRawHeaders(
                "WebSocket-Protocol", [])
            if len(protocolHeaders) not in (0,  1):
                return finish()
            if protocolHeaders:
                if protocolHeaders[0] not in self.site.supportedProtocols:
                    return finish()
                protocolHeader = protocolHeaders[0]
            else:
                protocolHeader = None

            originHeader = originHeaders[0]
            hostHeader = hostHeaders[0]
            self.startedWriting = True
            handshake = [
                "HTTP/1.1 101 Web Socket Protocol Handshake",
                "Upgrade: WebSocket",
                "Connection: Upgrade"]
            handshake.append("Sec-WebSocket-Origin: %s" % (originHeader))
            if self.isSecure():
                scheme = "wss"
            else:
                scheme = "ws"
            handshake.append(
                "Sec-WebSocket-Location: %s://%s%s" % (
                scheme, hostHeader, self.uri))

            if protocolHeader is not None:
                handshake.append("Sec-WebSocket-Protocol: %s" % protocolHeader)

            for header in handshake:
                self.write("%s\r\n" % header)

            self.write("\r\n")

            # concatenate num1 (32 bit in), num2 (32 bit int), nonce, and take md5 of result
            res = struct.pack('>II8s', num1, num2, nonce)
            server_response = md5(res).digest()
            self.write(server_response)

            # XXX we probably don't want to set _transferDecoder
            self.channel._transferDecoder = WebSocketFrameDecoder(
                self, handler)

            transport._connectionMade()

        # we need the nonce from the request body
        self.channel._transferDecoder = _IdentityTransferDecoder(0, lambda _ : None, finishHandshake)


    def _checkClientHandshake(self):
        """
        Verify client handshake, closing the connection in case of problem.

        @return: C{None} if a problem was detected, or a tuple of I{Origin}
            header, I{Host} header, I{WebSocket-Protocol} header, and
            C{WebSocketHandler} instance. The I{WebSocket-Protocol} header will
            be C{None} if not specified by the client.
        """
        def finish():
            self.channel.transport.loseConnection()
        if self.queued:
            return finish()
        originHeaders = self.requestHeaders.getRawHeaders("Origin", [])
        if len(originHeaders) != 1:
            return finish()
        hostHeaders = self.requestHeaders.getRawHeaders("Host", [])
        if len(hostHeaders) != 1:
            return finish()

        handlerFactory = self.site.handlers.get(self.uri)
        if not handlerFactory:
            return finish()
        transport = WebSocketTransport(self)
        handler = handlerFactory(transport)
        transport._attachHandler(handler)

        protocolHeaders = self.requestHeaders.getRawHeaders(
            "WebSocket-Protocol", [])
        if len(protocolHeaders) not in (0,  1):
            return finish()
        if protocolHeaders:
            if protocolHeaders[0] not in self.site.supportedProtocols:
                return finish()
            protocolHeader = protocolHeaders[0]
        else:
            protocolHeader = None
        return originHeaders[0], hostHeaders[0], protocolHeader, handler


    def renderWebSocket(self):
        """
        Render a WebSocket request.

        If the request is not identified with a proper WebSocket handshake, the
        connection will be closed. Otherwise, the response to the handshake is
        sent and a C{WebSocketHandler} is created to handle the request.
        """
        # check for post-75 handshake requests
        isSecHandshake = self.requestHeaders.getRawHeaders("Sec-WebSocket-Key1", [])
        if isSecHandshake:
            self._clientHandshake76()
        else:
            check = self._checkClientHandshake()
            if check is None:
                return
            originHeader, hostHeader, protocolHeader, handler = check
            self.startedWriting = True
            handshake = [
                "HTTP/1.1 101 Web Socket Protocol Handshake",
                "Upgrade: WebSocket",
                "Connection: Upgrade"]
            handshake.append("WebSocket-Origin: %s" % (originHeader))
            if self.isSecure():
                scheme = "wss"
            else:
                scheme = "ws"
            handshake.append(
                "WebSocket-Location: %s://%s%s" % (
                scheme, hostHeader, self.uri))

            if protocolHeader is not None:
                handshake.append("WebSocket-Protocol: %s" % protocolHeader)

            for header in handshake:
                self.write("%s\r\n" % header)

            self.write("\r\n")
            self.channel.setRawMode()
            # XXX we probably don't want to set _transferDecoder
            self.channel._transferDecoder = WebSocketFrameDecoder(
                self, handler)
            handler.transport._connectionMade()
            return



class WebSocketSite(Site):
    """
    @ivar handlers: a C{dict} of names to L{WebSocketHandler} factories.
    @type handlers: C{dict}
    @ivar supportedProtocols: a C{list} of supported I{WebSocket-Protocol}
        values. If a value is passed at handshake and doesn't figure in this
        list, the connection is closed.
    @type supportedProtocols: C{list}
    """
    requestFactory = WebSocketRequest

    def __init__(self, resource, logPath=None, timeout=60*60*12,
                 supportedProtocols=None):
        Site.__init__(self, resource, logPath, timeout)
        self.handlers = {}
        self.supportedProtocols = supportedProtocols or []

    def addHandler(self, name, handlerFactory):
        """
        Add or override a handler for the given C{name}.

        @param name: the resource name to be handled.
        @type name: C{str}
        @param handlerFactory: a C{WebSocketHandler} factory.
        @type handlerFactory: C{callable}
        """
        if not name.startswith("/"):
            raise ValueError("Invalid resource name.")
        self.handlers[name] = handlerFactory



class WebSocketTransport(object):
    """
    Transport abstraction over WebSocket, providing classic Twisted methods and
    callbacks.
    """
    implements(interfaces.ITransport)

    _handler = None

    def __init__(self, request):
        self._request = request
        self._request.notifyFinish().addErrback(self._connectionLost)

    def _attachHandler(self, handler):
        """
        Attach the given L{WebSocketHandler} to this transport.
        """
        self._handler = handler

    def _connectionMade(self):
        """
        Called when a connection is made.
        """
        self._handler.connectionMade()

    def _connectionLost(self, reason):
        """
        Forward connection lost event to the L{WebSocketHandler}.
        """
        self._handler.connectionLost(reason)
        del self._request.transport
        del self._request
        del self._handler

    def getPeer(self):
        """
        Return a tuple describing the other side of the connection.

        @rtype: C{tuple}
        """
        return self._request.transport.getPeer()

    def getHost(self):
        """
        Similar to getPeer, but returns an address describing this side of the
        connection.

        @return: An L{IAddress} provider.
        """

        return self._request.transport.getHost()

    def write(self, frame):
        """
        Send the given frame to the connected client.

        @param frame: a I{UTF-8} encoded C{str} to send to the client.
        @type frame: C{str}
        """
        self._request.write("\x00%s\xff" % frame)

    def writeSequence(self, frames):
        """
        Send a sequence of frames to the connected client.
        """
        self._request.write("".join(["\x00%s\xff" % f for f in frames]))

    def loseConnection(self):
        """
        Close the connection.
        """
        self._request.transport.loseConnection()
        del self._request.transport
        del self._request
        del self._handler

class WebSocketHandler(object):
    """
    Base class for handling WebSocket connections. It mainly provides a
    transport to send frames, and a callback called when frame are received,
    C{frameReceived}.

    @ivar transport: a C{WebSocketTransport} instance.
    @type: L{WebSocketTransport}
    """

    def __init__(self, transport):
        """
        Create the handler, with the given transport
        """
        self.transport = transport


    def frameReceived(self, frame):
        """
        Called when a frame is received.

        @param frame: a I{UTF-8} encoded C{str} sent by the client.
        @type frame: C{str}
        """


    def frameLengthExceeded(self):
        """
        Called when too big a frame is received. The default behavior is to
        close the connection, but it can be customized to do something else.
        """
        self.transport.loseConnection()


    def connectionMade(self):
        """
        Called when a connection is made.
        """

    def connectionLost(self, reason):
        """
        Callback called when the underlying transport has detected that the
        connection is closed.
        """



class WebSocketFrameDecoder(object):
    """
    Decode WebSocket frames and pass them to the attached C{WebSocketHandler}
    instance.

    @ivar MAX_LENGTH: maximum len of the frame allowed, before calling
        C{frameLengthExceeded} on the handler.
    @type MAX_LENGTH: C{int}
    @ivar request: C{Request} instance.
    @type request: L{twisted.web.server.Request}
    @ivar handler: L{WebSocketHandler} instance handling the request.
    @type handler: L{WebSocketHandler}
    @ivar _data: C{list} of C{str} buffering the received data.
    @type _data: C{list} of C{str}
    @ivar _currentFrameLength: length of the current handled frame, plus the
        additional leading byte.
    @type _currentFrameLength: C{int}
    """

    MAX_LENGTH = 16384


    def __init__(self, request, handler):
        self.request = request
        self.handler = handler
        self._data = []
        self._currentFrameLength = 0

    def dataReceived(self, data):
        """
        Parse data to read WebSocket frames.

        @param data: data received over the WebSocket connection.
        @type data: C{str}
        """
        if not data:
            return
        while True:
            endIndex = data.find("\xff")
            if endIndex != -1:
                self._currentFrameLength += endIndex
                if self._currentFrameLength > self.MAX_LENGTH:
                    self.handler.frameLengthExceeded()
                    break
                self._currentFrameLength = 0
                frame = "".join(self._data) + data[:endIndex]
                self._data[:] = []
                if frame[0] != "\x00":
                    self.request.transport.loseConnection()
                    break
                self.handler.frameReceived(frame[1:])
                data = data[endIndex + 1:]
                if not data:
                    break
                if data[0] != "\x00":
                    self.request.transport.loseConnection()
                    break
            else:
                self._currentFrameLength += len(data)
                if self._currentFrameLength > self.MAX_LENGTH + 1:
                    self.handler.frameLengthExceeded()
                else:
                    self._data.append(data)
                break



__all__ = ["WebSocketHandler", "WebSocketSite"]


########NEW FILE########
