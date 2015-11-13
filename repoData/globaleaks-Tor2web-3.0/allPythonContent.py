__FILENAME__ = dummyproxy
#!/usr/bin/env python
# coding: utf-8
#
# Simple TCP Proxy implemented using Twisted Library
#
# The proxy is intended to be used in conjuntion
# with Tor2web configured with a dummyproxy circuit.
# 
# Typical scenario involves a setup like this:
#
#      t2w -> dummyproxy -> dummyproxy -> dummyproxy -> HTTP/HTTPS application server
#
# Author: Giovanni Pellerano <evilaliv3@globaleaks.org>
#

import sys

from twisted.internet import protocol, reactor

class ClientProtocol(protocol.Protocol):
    def connectionMade(self):
        self.factory.server.client = self
        self.write(self.factory.server.buffer)
        self.factory.server.buffer = ''
 
    # Server => Proxy
    def dataReceived(self, data):
        self.factory.server.write(data)
 
    # Proxy => Server
    def write(self, data):
        if data:
            self.transport.write(data)

    def connectionLost(self, why):
        self.factory.server.transport.loseConnection()


class ServerProtocol(protocol.Protocol):
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.buffer = None
        self.client = None

    def connectionMade(self):
        factory = protocol.ClientFactory()
        factory.protocol = ClientProtocol
        factory.server = self

        reactor.connectTCP(self.ip, self.port, factory)

    # Client => Proxy
    def dataReceived(self, data):
        if self.client:
            self.client.write(data)
        else:
            self.buffer = data

    # Proxy => Client
    def write(self, data):
        self.transport.write(data)

    def connectionLost(self, why):
        self.transport.loseConnection()

class ServerFactory(protocol.Factory):
    protocol = ServerProtocol

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    def buildProtocol(self, addr):
        p = self.protocol(self.ip, self.port)
        p.factory = self
        return p

if __name__ == "__main__":

    if len(sys.argv) != 5:
        sys.stderr.write("Usage: " + sys.argv[0] + "<src-port> <dst-host> <dst-port>\n\n" \
                         "\texample: ./dummyproxy.py 127.0.0.1 80 127.0.0.1 8080\n" \
                         "\t         ./dummyproxy.py 0.0.0.0 88 google.com 80\n\n")
        sys.exit(1)

    src_ip = str(sys.argv[1])
    src_port = int(sys.argv[2])

    dst_ip = str(sys.argv[3])
    dst_port = int(sys.argv[4])

    factory = ServerFactory(dst_ip, dst_port)

    reactor.listenTCP(src_port, factory, interface=src_ip)

    reactor.run()

########NEW FILE########
__FILENAME__ = t2w
"""
    Tor2web
    Copyright (C) 2012 Hermes No Profit Association - GlobaLeaks Project

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""

:mod:`Tor2Web`
=====================================================

.. automodule:: Tor2Web
   :synopsis: Main Tor2web Server Implementation

.. moduleauthor:: Arturo Filasto' <art@globaleaks.org>
.. moduleauthor:: Giovanni Pellerano <evilaliv3@globaleaks.org>

"""

# -*- coding: utf-8 -*-

import os
import re
import sys
import mimetypes
import random
import signal
import socket

import zlib
import hashlib
from StringIO import StringIO
from random import choice
from functools import partial
from urlparse import urlparse
from cgi import parse_header

from zope.interface import implements
from twisted.spread import pb
from twisted.internet import reactor, protocol, defer
from twisted.internet.abstract import isIPAddress, isIPv6Address
from twisted.internet.endpoints import TCP4ClientEndpoint, SSL4ClientEndpoint
from twisted.protocols.policies import WrappingFactory
from twisted.web import http, client, _newclient
from twisted.web.error import SchemeNotSupported
from twisted.web.http import datetimeToString, StringTransport, _IdentityTransferDecoder, _ChunkedTransferDecoder, parse_qs
from twisted.web.http_headers import Headers
from twisted.web.server import NOT_DONE_YET
from twisted.web.template import flattenString, XMLString
from twisted.web.iweb import IBodyProducer
from twisted.python import log, logfile
from twisted.python.compat import networkString, intToBytes
from twisted.python.filepath import FilePath
from twisted.internet.task import LoopingCall

from tor2web import __version__
from tor2web.utils.config import Config
from tor2web.utils.daemon import T2WDaemon, set_pdeathsig, set_proctitle
from tor2web.utils.lists import List, TorExitNodeList
from tor2web.utils.mail import sendmail, sendexceptionmail
from tor2web.utils.misc import listenTCPonExistingFD, listenSSLonExistingFD, re_sub, verify_onion
from tor2web.utils.socks import SOCKS5ClientEndpoint, SOCKSError
from tor2web.utils.ssl import T2WSSLContextFactory
from tor2web.utils.stats import T2WStats
from tor2web.utils.storage import Storage
from tor2web.utils.templating import PageTemplate

SOCKS_errors = {
    0x00: "error_sock_generic.tpl",
    0x23: "error_sock_hs_not_found.tpl",
    0x24: "error_sock_hs_not_reachable.tpl"
}

class T2WRPCServer(pb.Root):
    def __init__(self, config):
        self.config = config
        self.stats = T2WStats()
        self.load_lists()

    def load_lists(self):
        self.access_list = []
        if config.mode == "TRANSLATION":
            pass

        elif config.mode == "WHITELIST":
            self.access_list = List(config.t2w_file_path('lists/whitelist.txt'))

        elif config.mode == "BLACKLIST":
            self.access_list = List(config.t2w_file_path('lists/blocklist_hashed.txt'),
                                    config.automatic_blocklist_updates_source,
                                    config.automatic_blocklist_updates_refresh)

            # clear local cleartext list
            # (load -> hash -> clear feature; for security reasons)
            self.blocklist_cleartext = List(config.t2w_file_path('lists/blocklist_cleartext.txt'))
            for i in self.blocklist_cleartext:
                self.access_list.add(hashlib.md5(i).hexdigest())

            self.access_list.dump()

            self.blocklist_cleartext.clear()
            self.blocklist_cleartext.dump()

        self.blocked_ua = []
        if config.blockcrawl:
            tmp = List(config.t2w_file_path('lists/blocked_ua.txt'))
            for ua in tmp:
                self.blocked_ua.append(ua.lower())

        # Load Exit Nodes list with the refresh rate configured  in config file
        self.TorExitNodes = TorExitNodeList(os.path.join(config.datadir, 'lists', 'exitnodelist.txt'),
                                            "https://onionoo.torproject.org/summary?type=relay",
                                            config.exit_node_list_refresh)

    def remote_get_config(self):
        return self.config.__dict__

    def remote_get_blocked_ua_list(self):
        return list(self.blocked_ua)

    def remote_get_access_list(self):
        return list(self.access_list)

    def remote_get_tor_exits_list(self):
        return list(self.TorExitNodes)

    def remote_update_stats(self, onion):
        self.stats.update(onion)

    def remote_get_yesterday_stats(self):
        return self.stats.yesterday_stats

    def remote_log_access(self, line):
        t2w_daemon.logfile_access.write(line)

    def remote_log_debug(self, line):
        date = datetimeToString()
        # noinspection PyCallByClass
        t2w_daemon.logfile_debug.write(date+" "+str(line)+"\n")


@defer.inlineCallbacks
def rpc(f, *args, **kwargs):
    d = rpc_factory.getRootObject()
    d.addCallback(lambda obj: obj.callRemote(f,  *args, **kwargs))
    ret = yield d
    defer.returnValue(ret)


def rpc_log(msg):
    rpc("log_debug", str(msg))


class T2WPP(protocol.ProcessProtocol):
    def __init__(self, father, childFDs, fds_https, fds_http):
        self.father = father
        self.childFDs = childFDs
        self.fds_https = fds_https
        self.fds_http = fds_http

    def connectionMade(self):
        self.pid = self.transport.pid

    def processExited(self, reason):
        for x in range(len(self.father.subprocesses)):
            if self.father.subprocesses[x] == self.pid:
                del self.father.subprocesses[x]
                break

        if not self.father.quitting:
            subprocess = spawnT2W(self.father, self.childFDs, self.fds_https, self.fds_http)
            self.father.subprocesses.append(subprocess.pid)

        if len(self.father.subprocesses) == 0:
            try:
                reactor.stop()
            except Exception:
                pass


def spawnT2W(father, childFDs, fds_https, fds_http):
    child_env = os.environ.copy()
    child_env['T2W_FDS_HTTPS'] = fds_https
    child_env['T2W_FDS_HTTP'] = fds_http

    return reactor.spawnProcess(T2WPP(father, childFDs, fds_https, fds_http),
                                sys.executable,
                                [sys.executable, __file__] + sys.argv[1:],
                                env=child_env,
                                childFDs=childFDs)


class Tor2webObj():
    def __init__(self):
        # The destination hidden service identifier
        self.onion = None

        # The path portion of the URI
        self.path = None

        # The full address (hostname + uri) that must be requested
        self.address = None

        # The headers to be sent
        self.headers = None

        # The requested uri
        self.uri = None

        # A boolean that keeps track of client gzip support
        self.client_supports_gzip = False

        # A boolean that keeps track of server gzip support
        self.server_response_is_gzip = False

        # A boolean that keeps track of document content type
        self.html = False


class BodyReceiver(protocol.Protocol):
    def __init__(self, finished):
        self._finished = finished
        self._data = []

    def dataReceived(self, chunk):
        self._data.append(chunk)

    def write(self, chunk):
        self._data.append(chunk)

    def connectionLost(self, reason):
        self._finished.callback(''.join(self._data))


class BodyStreamer(protocol.Protocol):
    def __init__(self, streamfunction, finished):
        self._finished = finished
        self._streamfunction = streamfunction

    def dataReceived(self, data):
        self._streamfunction(data)

    def connectionLost(self, reason):
        self._finished.callback('')


class BodyProducer(object):
    implements(IBodyProducer)

    def __init__(self):
        self.length = _newclient.UNKNOWN_LENGTH
        self.finished = defer.Deferred()
        self.consumer = None
        self.can_stream = False
        self.can_stream_d = defer.Deferred()

    def startProducing(self, consumer):
        self.consumer = consumer
        self.can_stream = True
        self.can_stream_d.callback(True)
        return self.finished

    @defer.inlineCallbacks
    def dataReceived(self, data):
        if not self.can_stream:
            yield self.can_stream_d
        self.consumer.write(data)

    def allDataReceived(self):
        self.finished.callback(None)

    def resumeProducing(self):
        pass

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


class HTTPConnectionPool(client.HTTPConnectionPool):
    _factory = client._HTTP11ClientFactory

    def startedConnecting(self, connector):
        pass

    _factory.startedConnecting = startedConnecting

    def __init__(self, reactor, persistent=True, maxPersistentPerHost=2, cachedConnectionTimeout=240, retryAutomatically=True):
        client.HTTPConnectionPool.__init__(self, reactor, persistent)
        self.maxPersistentPerHost = maxPersistentPerHost
        self.cachedConnectionTimeout = cachedConnectionTimeout
        self.retryAutomatically = retryAutomatically

class Agent(client.Agent):
    def __init__(self, reactor,
                 contextFactory=client.WebClientContextFactory(),
                 connectTimeout=None, bindAddress=None,
                 pool=None, sockhost=None, sockport=None):
        if pool is None:
            pool = HTTPConnectionPool(reactor, False)
        self._reactor = reactor
        self._pool = pool
        self._contextFactory = contextFactory
        self._connectTimeout = connectTimeout
        self._bindAddress = bindAddress
        self._sockhost = sockhost
        self._sockport = sockport

    def _getEndpoint(self, scheme, host, port):
        kwargs = {}
        if self._connectTimeout is not None:
            kwargs['timeout'] = self._connectTimeout
        kwargs['bindAddress'] = self._bindAddress
        if scheme == 'http':
            return TCP4ClientEndpoint(self._reactor, host, port, **kwargs)
        elif scheme == 'shttp':
            return SOCKS5ClientEndpoint(self._reactor, self._sockhost,
                                        self._sockport, host, port, config.socksoptimisticdata, **kwargs)
        elif scheme == 'https':
            return SSL4ClientEndpoint(self._reactor, host, port,
                                      self._wrapContextFactory(host, port),
                                      **kwargs)
        else:
            raise SchemeNotSupported("Unsupported scheme: %r" % (scheme,))


class T2WRequest(http.Request):
    """
    Used by Tor2webProxy to implement a simple web proxy.
    """
    def __init__(self, channel, queued, reactor=reactor):
        """
        Method overridden to change some part of proxy.Request and of the base http.Request
        """
        self.reactor = reactor
        self.notifications = []
        self.channel = channel
        self.queued = queued
        self.requestHeaders = Headers()
        self.received_cookies = {}
        self.responseHeaders = Headers()
        self.cookies = [] # outgoing cookies
        self.bodyProducer = BodyProducer()
        self.proxy_d = None
        self.proxy_response = None

        self.stream = ''

        self.header_injected = False
        # If we should disable the banner,
        # say that we have already injected it.
        if config.disable_banner:
            self.header_injected = True

        if queued:
            self.transport = StringTransport()
        else:
            self.transport = self.channel.transport

        self.obj = Tor2webObj()
        self.var = Storage()
        self.var['version'] = __version__
        self.var['basehost'] = config.basehost
        self.var['errorcode'] = None

        self.html = False

        self.decoderGzip = None
        self.encoderGzip = None

        self.pool = pool

    def _cleanup(self):
        """
        Method overridden to avoid self.content actions.
        """
        if self.producer:
            log.err(RuntimeError("Producer was not unregistered for %s" % self.uri))
            self.unregisterProducer()
        self.channel.requestDone(self)
        del self.channel
        for d in self.notifications:
            d.callback(None)
        self.notifications = []

    def getRequestHostname(self):
        """
            Function overload to fix ipv6 bug:
                http://twistedmatrix.com/trac/ticket/6014
        """
        host = self.getHeader(b'host')
        if host:
            if host[0]=='[':
                return host.split(']',1)[0] + "]"
            return networkString(host.split(':', 1)[0])
        return networkString(self.getHost().host)

    def forwardData(self, data, end=False):
        if not self.startedWriting:
            if self.obj.client_supports_gzip:
                self.setHeader(b'content-encoding', b'gzip')

            if data != '' and end:
                self.setHeader(b'content-length', intToBytes(len(data)))

        if data != '':
            try:
                self.write(data)
            except Exception:
                pass

    def requestReceived(self, command, path, version):
        """
        Method overridden to reduce the function actions
        """
        self.method, self.uri = command, path
        self.clientproto = version

        # cache the client and server information, we'll need this later to be
        # serialized and sent with the request so CGIs will work remotely
        self.client = self.channel.transport.getPeer()
        self.host = self.channel.transport.getHost()

        self.process()

    def add_banner(self, banner, data):
        """
        Inject tor2web banner inside the returned page
        """
        return str(data.group(1)) + str(banner)

    @defer.inlineCallbacks
    def handleFixPart(self, data):
        if self.obj.server_response_is_gzip:
            data = self.unzip(data)

        data = self.stream + data

        if len(data) >= 1000:
            data = re_sub(rexp['t2w'], r'https://\2.' + config.basehost, data)

            forward = data[:-500]
            if not self.header_injected and forward.find("<body") != -1:
                banner = yield flattenString(self, templates['banner.tpl'])
                forward = re.sub(rexp['body'], partial(self.add_banner, banner), forward)
                self.header_injected = True

            self.forwardData(self.handleCleartextForwardPart(forward))
            self.stream = data[-500:]
        else:
            self.stream = data

    @defer.inlineCallbacks
    def handleFixEnd(self, data):
        if self.obj.server_response_is_gzip:
            data = self.unzip(data, True)

        data = self.stream + data

        data = re_sub(rexp['t2w'], r'https://\2.' + config.basehost, data)

        if not self.header_injected and data.find("<body") != -1:
            banner = yield flattenString(self, templates['banner.tpl'])
            data = re.sub(rexp['body'], partial(self.add_banner, banner), data)
            self.header_injected = True

        data = self.handleCleartextForwardPart(data, True)
        self.forwardData(data, True)

        self.stream = ''

        try:
            self.finish()
        except Exception:
            pass

    def handleGzippedForwardPart(self, data, end=False):
        if not self.obj.client_supports_gzip:
            data = self.unzip(data, end)

        return data

    def handleCleartextForwardPart(self, data, end=False):
        if self.obj.client_supports_gzip:
           data = self.zip(data, end)

        return data

    def handleForwardPart(self, data):
        if self.obj.server_response_is_gzip:
            data = self.handleGzippedForwardPart(data)
        else:
            data = self.handleCleartextForwardPart(data)

        self.forwardData(data)

    def handleForwardEnd(self, data):
        if self.obj.server_response_is_gzip:
            data = self.handleGzippedForwardPart(data, True)
        else:
            data = self.handleCleartextForwardPart(data, True)

        self.forwardData(data, True)
        try:
            self.finish()
        except Exception:
            pass

    def contentFinish(self, data):
        if self.obj.client_supports_gzip:
            self.setHeader(b'content-encoding', b'gzip')
            data = self.zip(data, True)

        self.setHeader(b'content-length', intToBytes(len(data)))
        self.setHeader(b'cache-control', b'no-cache')

        if config.blockcrawl:
            self.setHeader(b'X-Robots-Tag', b'noindex')

        if self.isSecure():
            self.setHeader(b'strict-transport-security', b'max-age=31536000')

        try:
            self.write(data)
            self.finish()
        except Exception:
            pass

    def sendError(self, error=500, errortemplate='error_generic.tpl'):
        self.setResponseCode(error)
        self.setHeader(b'content-type', 'text/html')
        self.var['errorcode'] = error
        return flattenString(self, templates[errortemplate]).addCallback(self.contentFinish)

    def handleError(self, failure):
        if type(failure.value) is SOCKSError:
            self.setResponseCode(404)
            self.var['errorcode'] = failure.value.code
            if failure.value.code in SOCKS_errors:
                return flattenString(self, templates[SOCKS_errors[failure.value.code]]).addCallback(self.contentFinish)
            else:
                return flattenString(self, templates[SOCKS_errors[0x00]]).addCallback(self.contentFinish)
        else:
            self.sendError()

    def unzip(self, data, end=False):
        data1 = data2 = ''

        try:
            if self.decoderGzip is None:
                self.decoderGzip = zlib.decompressobj(16 + zlib.MAX_WBITS)

            if data != '':
                data1 = self.decoderGzip.decompress(data)

            if end:
                data2 = self.decoderGzip.flush()

        except Exception:
            pass

        return data1 + data2

    def zip(self, data, end=False):
        data1 = data2 = ''

        try:
            if self.encoderGzip is None:
                self.encoderGzip = zlib.compressobj(6, zlib.DEFLATED, 16 + zlib.MAX_WBITS)

            if data != '':
                data1 = self.encoderGzip.compress(data)

            if end:
                data2 = self.encoderGzip.flush()
        except Exception:
            pass

        return data1 + data2

    def process_request(self, req):
        """
        This function:
            - "resolves" the address;
            - alters and sets the proper headers.
        """
        rpc_log(req)

        self.obj.host_tor = "http://" + self.obj.onion
        self.obj.host_tor2web = "https://" + self.obj.onion.replace(".onion", "") + "." + config.basehost
        self.obj.address = "http://" + self.obj.onion + self.obj.uri

        self.obj.headers = req.headers

        rpc_log("Headers before fix:")
        rpc_log(self.obj.headers)

        self.obj.headers.removeHeader(b'if-modified-since')
        self.obj.headers.removeHeader(b'if-none-match')
        self.obj.headers.setRawHeaders(b'host', [self.obj.onion])
        self.obj.headers.setRawHeaders(b'connection', [b'keep-alive'])
        self.obj.headers.setRawHeaders(b'Accept-encoding', [b'gzip, chunked'])
        self.obj.headers.setRawHeaders(b'x-tor2web', [b'encrypted'])

        for key, values in self.obj.headers.getAllRawHeaders():
            fixed_values = []
            for value in values:
                value = re_sub(rexp['w2t'], r'http://\2.onion', value)
                fixed_values.append(value)

            self.obj.headers.setRawHeaders(key, fixed_values)

        rpc_log("Headers after fix:")
        rpc_log(self.obj.headers)

        return True

    @defer.inlineCallbacks
    def process(self):
        request = Storage()
        request.headers = self.requestHeaders
        request.host = self.getRequestHostname()
        request.uri = self.uri

        content_length = self.getHeader(b'content-length')
        transfer_encoding = self.getHeader(b'transfer-encoding')

        staticpath = request.uri
        staticpath = re.sub('/$', '/index.html', staticpath)
        staticpath = re.sub('^(/antanistaticmap/)?', '', staticpath)
        staticpath = re.sub('^/', '', staticpath)

        resource_is_local = (config.mode != "TRANSLATION" and
                             (request.host == config.basehost or
                              request.host == 'www.' + config.basehost)) or \
                            isIPAddress(request.host) or \
                            isIPv6Address(request.host) or \
                            (config.overriderobotstxt and request.uri == '/robots.txt') or \
                            request.uri.startswith('/antanistaticmap/')

        if content_length is not None:
            self.bodyProducer.length = int(content_length)
            producer = self.bodyProducer
            request.headers.removeHeader(b'content-length')
        elif transfer_encoding is not None:
            producer = self.bodyProducer
            request.headers.removeHeader(b'transfer-encoding')
        else:
            producer = None

        if config.mirror is not None:
            if config.basehost in config.mirror:
                config.mirror.remove(config.basehost)
            if len(config.mirror) > 1:
                self.var['mirror'] = choice(config.mirror)
            elif len(config.mirror) == 1:
                self.var['mirror'] = config.mirror[0]

        # we serve contents only over https
        if not self.isSecure() and (config.transport != 'HTTP'):
            self.redirect("https://" + request.host + request.uri)
            self.finish()
            defer.returnValue(None)

        # 0: Request admission control stage
        # we try to deny some ua/crawlers regardless the request is (valid or not) / (local or not)
        # we deny EVERY request to known user agents reconized with pattern matching
        if config.blockcrawl and request.headers.getRawHeaders(b'user-agent') is not None:
            for ua in blocked_ua_list:
                if re.match(ua, request.headers.getRawHeaders(b'user-agent')[0].lower()):
                    self.sendError(403, "error_blocked_ua.tpl")
                    defer.returnValue(NOT_DONE_YET)

        # 1: Client capability assessment stage
        if request.headers.getRawHeaders(b'accept-encoding') is not None:
            if re.search('gzip', request.headers.getRawHeaders(b'accept-encoding')[0]):
                self.obj.client_supports_gzip = True

        # 2: Content delivery stage
        # we need to verify if the requested resource is local (/antanistaticmap/*) or remote
        # because some checks must be done only for remote requests;
        # in fact local content is always served (css, js, and png in fact are used in errors)
        if resource_is_local:
            # the requested resource is local, we deliver it directly
            try:
                if staticpath == "dev/null":
                    content = "A" * random.randint(20, 1024)
                    self.setHeader(b'content-type', 'text/plain')
                    defer.returnValue(self.contentFinish(content))

                elif staticpath == "stats/yesterday":
                    self.setHeader(b'content-type', 'application/json')
                    content = yield rpc("get_yesterday_stats")
                    defer.returnValue(self.contentFinish(content))

                elif staticpath == "notification":

                    #################################################################
                    # Here we need to parse POST data in x-www-form-urlencoded format
                    #################################################################
                    content_receiver = BodyReceiver(defer.Deferred())
                    self.bodyProducer.startProducing(content_receiver)
                    yield self.bodyProducer.finished
                    content = ''.join(content_receiver._data)

                    args = {}

                    ctype = self.requestHeaders.getRawHeaders(b'content-type')
                    if ctype is not None:
                        ctype = ctype[0]

                    if self.method == b"POST" and ctype:
                        key, pdict = parse_header(ctype)
                        if key == b'application/x-www-form-urlencoded':
                            args.update(parse_qs(content, 1))
                    #################################################################

                    if 'by' in args and 'url' in args and 'comment' in args:
                        tmp = []
                        tmp.append("From: Tor2web Node %s.%s <%s>\n" % (config.nodename, config.basehost, config.smtpmail))
                        tmp.append("To: %s\n" % config.smtpmailto_notifications)
                        tmp.append("Subject: Tor2web Node (IPv4 %s, IPv6 %s): notification for %s\n" % (config.listen_ipv4, config.listen_ipv6, args['url'][0]))
                        tmp.append("Content-Type: text/plain; charset=ISO-8859-1\n")
                        tmp.append("Content-Transfer-Encoding: 8bit\n\n")
                        tmp.append("BY: %s\n" % (args['by'][0]))
                        tmp.append("URL: %s\n" % (args['url'][0]))
                        tmp.append("COMMENT: %s\n" % (args['comment'][0]))
                        message = StringIO(''.join(tmp))

                        try:
                            sendmail(config.smtpuser,
                                     config.smtppass,
                                     config.smtpmail,
                                     config.smtpmailto_notifications,
                                     message,
                                     config.smtpdomain,
                                     config.smtpport)
                        except Exception:
                            pass

                    self.setHeader(b'content-type', 'text/plain')
                    defer.returnValue(self.contentFinish(''))

                else:
                    if type(antanistaticmap[staticpath]) == str:
                        filename, ext = os.path.splitext(staticpath)
                        self.setHeader(b'content-type', mimetypes.types_map[ext])
                        content = antanistaticmap[staticpath]
                        defer.returnValue(self.contentFinish(content))

                    elif type(antanistaticmap[staticpath]) == PageTemplate:
                        defer.returnValue(flattenString(self, antanistaticmap[staticpath]).addCallback(self.contentFinish))

            except Exception:
                pass

            self.sendError(404)
            defer.returnValue(NOT_DONE_YET)

        else:
            self.obj.uri = request.uri

            if not request.host:
                self.sendError(406, 'error_invalid_hostname.tpl')
                defer.returnValue(NOT_DONE_YET)

            if config.mode == "TRANSLATION":
                self.obj.onion = config.onion
            else:
                self.obj.onion = request.host.split(".")[0] + ".onion"
                rpc_log("detected <onion_url>.tor2web Hostname: %s" % self.obj.onion)
                if not verify_onion(self.obj.onion):
                    self.sendError(406, 'error_invalid_hostname.tpl')
                    defer.returnValue(NOT_DONE_YET)

                if config.mode == "ACCESSLIST":
                    if not hashlib.md5(self.obj.onion) in access_list:
                        self.sendError(403, 'error_hs_completely_blocked.tpl')
                        defer.returnValue(NOT_DONE_YET)

                elif config.mode == "BLACKLIST":
                    if hashlib.md5(self.obj.onion).hexdigest() in access_list:
                        self.sendError(403, 'error_hs_completely_blocked.tpl')
                        defer.returnValue(NOT_DONE_YET)

                    if hashlib.md5(self.obj.onion + self.obj.uri).hexdigest() in access_list:
                        self.sendError(403, 'error_hs_specific_page_blocked.tpl')
                        defer.returnValue(NOT_DONE_YET)

            # we need to verify if the user is using tor;
            # on this condition it's better to redirect on the .onion
            if self.getClientIP() in tor_exits_list:
                self.redirect("http://" + self.obj.onion + request.uri)

                try:
                    self.finish()
                except Exception:
                    pass

                defer.returnValue(None)

            # Avoid image hotlinking
            if request.uri.lower().endswith(('gif','jpg','png')):
                if request.headers.getRawHeaders(b'referer') is not None and \
                   not config.basehost in request.headers.getRawHeaders(b'referer')[0].lower():
                    self.sendError(403)
                    defer.returnValue(NOT_DONE_YET)

            # the requested resource is remote, we act as proxy

            self.process_request(request)

            parsed = urlparse(self.obj.address)

            self.var['address'] = self.obj.address
            self.var['onion'] = self.obj.onion.replace(".onion", "")
            self.var['path'] = parsed[2]
            if parsed[3] is not None and parsed[3] != '':
                self.var['path'] += '?' + parsed[3]

            agent = Agent(reactor, sockhost=config.sockshost, sockport=config.socksport, pool=self.pool)

            if config.dummyproxy is None:
                proxy_url = 's' + self.obj.address
            else:
                proxy_url = config.dummyproxy + parsed[2] + '?' + parsed[3]

            self.proxy_d = agent.request(self.method,
                                         proxy_url,
                                         self.obj.headers, bodyProducer=producer)

            self.proxy_d.addCallback(self.cbResponse)
            self.proxy_d.addErrback(self.handleError)

            defer.returnValue(NOT_DONE_YET)

    def cbResponse(self, response):
        self.proxy_response = response
        if 600 <= int(response.code) <= 699:
            self.setResponseCode(500)
            self.var['errorcode'] = int(response.code) - 600
            if self.var['errorcode'] in SOCKS_errors:
                return flattenString(self, templates[SOCKS_errors[self.var['errorcode']]]).addCallback(self.contentFinish)
            else:
                return flattenString(self, templates[SOCKS_errors[0x00]]).addCallback(self.contentFinish)

        self.setResponseCode(response.code)

        self.processResponseHeaders(response.headers)

        if response.length is not 0:
            finished = defer.Deferred()
            if self.obj.html:
                response.deliverBody(BodyStreamer(self.handleFixPart, finished))
                finished.addCallback(self.handleFixEnd)
            else:
                response.deliverBody(BodyStreamer(self.handleForwardPart, finished))
                finished.addCallback(self.handleForwardEnd)

            return finished
        else:
            self.contentFinish('')
            return defer.succeed

    def handleHeader(self, key, values):
        keyLower = key.lower()

        # some headers does not allow multiple occurrences
        # in case of multiple occurrences we evaluate only the first
        valueLower = values[0].lower()

        if keyLower == 'transfer-encoding' and valueLower == 'chunked':
            return

        elif keyLower == 'content-encoding' and valueLower == 'gzip':
            self.obj.server_response_is_gzip = True
            return

        elif keyLower == 'content-type' and re.search('text/html', valueLower):
            self.obj.html = True

        elif keyLower == 'content-length':
            self.receivedContentLen = valueLower
            return

        elif keyLower == 'cache-control':
            return

        if keyLower in 'location':
            fixed_values = []
            for value in values:
                value = re_sub(rexp['t2w'], r'https://\2.' + config.basehost, value)
                fixed_values.append(value)
            values = fixed_values

        self.responseHeaders.setRawHeaders(key, values)

    def processResponseHeaders(self, headers):
        # currently we track only responding hidden services
        # we don't need to block on the rpc now so no yield is needed
        rpc("update_stats", str(self.obj.onion.replace(".onion", "")))

        for key, values in headers.getAllRawHeaders():
            self.handleHeader(key, values)

    def connectionLost(self, reason):
        try:
            if self.proxy_d:
                self.proxy_d.cancel()
        except Exception:
            pass

        try:
            if self.proxy_response:
                self.proxy_response._transport.stopProducing()
        except Exception:
            pass

        try:
            http.Request.connectionLost(self, reason)
        except Exception:
            pass

    def finish(self):
        try:
            http.Request.finish(self)
        except Exception:
            pass

class T2WProxy(http.HTTPChannel):
    requestFactory = T2WRequest

    def headerReceived(self, line):
        """
        Overridden to reduce the function actions and
        in particular to avoid self._transferDecoder actions and
        implement a streaming proxy
        """
        header, data = line.split(b':', 1)
        header = header.lower()
        data = data.strip()
        req = self.requests[-1]
        if header == b'content-length':
            try:
                self.length = int(data)
            except ValueError:
                self.transport.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                self.length = None
                self.transport.loseConnection()
                return
            self._transferDecoder = _IdentityTransferDecoder(
                self.length, req.bodyProducer.dataReceived, self._finishRequestBody)
        elif header == b'transfer-encoding' and data.lower() == b'chunked':
            self.length = None
            self._transferDecoder = _ChunkedTransferDecoder(
                req.bodyProducer.dataReceived, self._finishRequestBody)
        reqHeaders = req.requestHeaders
        values = reqHeaders.getRawHeaders(header)
        if values is not None:
            values.append(data)
        else:
            reqHeaders.setRawHeaders(header, [data])

    def allHeadersReceived(self):
        """
        Overridden to reduce the function actions
        """
        req = self.requests[-1]
        self.persistent = self.checkPersistence(req, self._version)

        req.requestReceived(self._command, self._path, self._version)

    def allContentReceived(self):
        if len(self.requests):
            req = self.requests[-1]
            req.bodyProducer.allDataReceived()

        # reset ALL state variables, so we don't interfere with next request
        self.length = 0
        self._receivedHeaderCount = 0
        self._HTTPChannel__first_line = 1
        self._transferDecoder = None
        del self._command, self._path, self._version

        # Disable the idle timeout, in case this request takes a long
        # time to finish generating output.
        if self.timeOut:
            self._savedTimeOut = self.setTimeout(None)

class T2WProxyFactory(http.HTTPFactory):
    protocol = T2WProxy

    def _openLogFile(self, path):
        return log.NullFile()
    def log(self, request):
        """
        Log a request's result to the logfile, by default in combined log format.
        """
        if config.logreqs:
            line = "127.0.0.1 (%s) - - %s \"%s\" %s %s \"%s\" \"%s\"\n" % (
                self._escape(request.getHeader(b'host')),
                self._logDateTime,
                '%s %s %s' % (self._escape(request.method),
                              self._escape(request.uri),
                              self._escape(request.clientproto)),
                request.code,
                request.sentLength or "-",
                self._escape(request.getHeader(b'referer') or "-"),
                self._escape(request.getHeader(b'user-agent') or "-"))

            rpc("log_access", str(line))

class T2WLimitedRequestsFactory(WrappingFactory):
    def __init__(self, wrappedFactory, allowedRequests):
        WrappingFactory.__init__(self, wrappedFactory)
        self.requests_countdown = allowedRequests

    def registerProtocol(self, p):
        """
        Called by protocol to register itself.
        """
        WrappingFactory.registerProtocol(self, p)

        if self.requests_countdown > 0:
            self.requests_countdown -= 1

        if self.requests_countdown == 0:
            # bai bai mai friend
            #
            # known bug: currently when the limit is reached all
            #            the active requests are trashed.
            #            this simple solution is used to achieve
            #            stronger stability.
            try:
                reactor.stop()
            except Exception:
                pass

def start_worker():
    global antanistaticmap
    global templates
    global pool
    global rexp
    global ports

    lc = LoopingCall(updateListsTask)
    lc.start(600)

    rexp = {
        'body': re.compile(r'(<body.*?\s*>)', re.I),
        'w2t': re.compile(r'(http.?:)?//([a-z0-9]{16}).' + config.basehost + '(?!:\d+)', re.I),
        't2w': re.compile(r'(http.?:)?//([a-z0-9]{16}).(?!' + config.basehost + ')onion(?!:\d+)', re.I)
    }

    ###############################################################################
    # Static Data loading
    #    Here we make a file caching to not handle I/O
    #    at run-time and achieve better performance
    ###############################################################################
    antanistaticmap = {}

    # system default static files
    sys_static_dir = os.path.join(config.sysdatadir, "static/")
    if os.path.exists(sys_static_dir):
        for root, dirs, files in os.walk(os.path.join(sys_static_dir)):
            for basename in files:
                filename = os.path.join(root, basename)
                f = FilePath(filename)
                antanistaticmap[filename.replace(sys_static_dir, "")] = f.getContent()

    # user defined static files
    usr_static_dir = os.path.join(config.datadir, "static/")
    if usr_static_dir != sys_static_dir and os.path.exists(usr_static_dir):
        for root, dirs, files in os.walk(os.path.join(usr_static_dir)):
            for basename in files:
                filename = os.path.join(root, basename)
                f = FilePath(filename)
                antanistaticmap[filename.replace(usr_static_dir, "")] = f.getContent()
    ###############################################################################

    ###############################################################################
    # Templates loading
    #    Here we make a templates cache in order to not handle I/O
    #    at run-time and achieve better performance
    ###############################################################################
    templates = {}

    # system default templates
    sys_tpl_dir = os.path.join(config.sysdatadir, "templates/")
    if os.path.exists(sys_tpl_dir):
        files = FilePath(sys_tpl_dir).globChildren("*.tpl")
        for f in files:
            f = FilePath(config.t2w_file_path(os.path.join('templates', f.basename())))
            templates[f.basename()] = PageTemplate(XMLString(f.getContent()))

    # user defined templates
    usr_tpl_dir = os.path.join(config.datadir, "templates/")
    if usr_tpl_dir != sys_tpl_dir and os.path.exists(usr_tpl_dir):
        files = FilePath(usr_tpl_dir).globChildren("*.tpl")
        for f in files:
            f = FilePath(config.t2w_file_path(os.path.join('templates', f.basename())))
            templates[f.basename()] = PageTemplate(XMLString(f.getContent()))
    ###############################################################################

    pool = HTTPConnectionPool(reactor, True,
                              config.sockmaxpersistentperhost,
                              config.sockcachedconnectiontimeout,
                              config.sockretryautomatically)

    factory = T2WProxyFactory()

    # we do not want all workers to die in the same moment
    requests_countdown = config.requests_per_process / random.randint(1, 3)

    factory = T2WLimitedRequestsFactory(factory, requests_countdown)

    context_factory = T2WSSLContextFactory(os.path.join(config.datadir, "certs/tor2web-key.pem"),
                                                       os.path.join(config.datadir, "certs/tor2web-intermediate.pem"),
                                                       os.path.join(config.datadir, "certs/tor2web-dh.pem"),
                                                       config.cipher_list)

    fds_https = []
    if  'T2W_FDS_HTTPS' in os.environ:
        fds_https = filter(None, os.environ['T2W_FDS_HTTPS'].split(","))
        fds_https = [int(i) for i in fds_https]

    fds_http = []
    if  'T2W_FDS_HTTP' in os.environ:
        fds_http = filter(None, os.environ['T2W_FDS_HTTP'].split(","))
        fds_http = [int(i) for i in fds_http]


    reactor.listenTCPonExistingFD = listenTCPonExistingFD
    reactor.listenSSLonExistingFD = listenSSLonExistingFD

    for fd in fds_https:
        ports.append(reactor.listenSSLonExistingFD(reactor,
                                                   fd=fd,
                                                   factory=factory,
                                                   contextFactory=context_factory))

    for fd in fds_http:
        ports.append(reactor.listenTCPonExistingFD(reactor,
                                                   fd=fd,
                                                   factory=factory))

    def MailException(etype, value, tb):
        sendexceptionmail(config, etype, value, tb)

    sys.excepthook = MailException

def updateListsTask():
    def set_access_list(l):
        global access_list
        access_list = l

    def set_blocked_ua_list(l):
        global blocked_ua_list
        blocked_ua_list = l

    def set_tor_exits_list(l):
        global tor_exits_list
        tor_exits_list = l

    rpc("get_access_list").addCallback(set_access_list)
    rpc("get_blocked_ua_list").addCallback(set_blocked_ua_list)
    rpc("get_tor_exits_list").addCallback(set_tor_exits_list)

def SigQUIT(SIG, FRM):
    try:
        reactor.stop()
    except Exception:
        pass

sys.excepthook = None
set_pdeathsig(signal.SIGINT)

##########################
# Security UMASK hardening
os.umask(077)

orig_umask = os.umask

def umask(mask):
    return orig_umask(077)

os.umask = umask
##########################

###############################################################################
# Basic Safety Checks
###############################################################################

config = Config()

if config.transport is None:
    config.transport = 'BOTH'

if config.automatic_blocklist_updates_source is None:
    config.automatic_blocklist_updates_source = ''

if config.automatic_blocklist_updates_refresh is None:
    config.automatic_blocklist_updates_refresh = 600

if config.exit_node_list_refresh is None:
    config.exit_node_list_refresh = 600

if not os.path.exists(config.datadir):
    print "Tor2web Startup Failure: unexistent directory (%s)" % config.datadir
    exit(1)

if config.mode not in [ 'TRANSLATION', 'WHITELIST', 'BLACKLIST' ]:
    print "Tor2web Startup Failure: config.mode must be one of: TRANSLATION / WHITELIST / BLACKLIST"
    exit(1)

if config.mode == "TRANSLATION":
    if not verify_onion(config.onion):
        print "Tor2web Startup Failure: TRANSLATION config.mode require config.onion configuration"
        exit(1)

for d in [ 'certs',  'logs']:
    path = os.path.join(config.datadir, d)
    if not os.path.exists(path):
        print "Tor2web Startup Failure: unexistent directory (%s)" % path
        exit(1)

files = ['certs/tor2web-key.pem', 'certs/tor2web-intermediate.pem', 'certs/tor2web-dh.pem']
for f in files:
    path = os.path.join(config.datadir, f)
    try:
        if (not os.path.exists(path) or
            not os.path.isfile(path) or
            not os.access(path, os.R_OK)):
            print "Tor2web Startup Failure: unexistent file (%s)" % path
            exit(1)
    except Exception:
        print "Tor2web Startup Failure: error while accessing file (%s)" % path
        exit(1)
###############################################################################


if config.listen_ipv6 == "::" or config.listen_ipv4 == config.listen_ipv6:
    # fix for incorrect configurations
    ipv4 = None
else:
    ipv4 = config.listen_ipv4
ipv6 = config.listen_ipv6

if 'T2W_FDS_HTTPS' not in os.environ and 'T2W_FDS_HTTP' not in os.environ:

     set_proctitle("tor2web")

     def open_listenin_socket(ip, port):
         try:
             s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
             s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
             s.setblocking(False)
             s.bind((ip, port))
             s.listen(1024)
             return s
         except Exception as e:
             print "Tor2web Startup Failure: error while binding on %s %s (%s)" % (ip, port, e)
             exit(1)

     def daemon_init(self):

         self.quitting = False
         self.subprocesses = []

         self.socket_rpc = open_listenin_socket('127.0.0.1', 8789)

         self.childFDs = {0: 0, 1: 1, 2: 2}

         self.fds = []

         self.fds_https = self.fds_http = ''

         i_https = i_http = 0

         for ip in [ipv4, ipv6]:
             if ip is not None:
                 if config.transport in ('HTTPS', 'BOTH'):
                     if i_https != 0:
                         self.fds_https += ','
                     s = open_listenin_socket(ip, config.listen_port_https)
                     self.fds.append(s)
                     self.childFDs[s.fileno()] = s.fileno()
                     self.fds_https += str(s.fileno())
                     i_https += 1

                 if config.transport in ('HTTP', 'BOTH'):
                     if i_http != 0:
                         self.fds_http += ','
                     s = open_listenin_socket(ip, config.listen_port_http)
                     self.fds.append(s)
                     self.childFDs[s.fileno()] = s.fileno()
                     self.fds_http += str(s.fileno())
                     i_http += 1


     def daemon_main(self):
         if config.logreqs:
             self.logfile_access = logfile.DailyLogFile.fromFullPath(os.path.join(config.datadir, 'logs', 'access.log'))
         else:
             self.logfile_access = log.NullFile()

         if config.debugmode:
             if config.debugtostdout and config.nodaemon:
                 self.logfile_debug = sys.stdout
             else:
                 self.logfile_debug = logfile.DailyLogFile.fromFullPath(os.path.join(config.datadir, 'logs', 'debug.log'))
         else:
             self.logfile_debug = log.NullFile()

         log.startLogging(self.logfile_debug)

         reactor.listenTCPonExistingFD = listenTCPonExistingFD

         reactor.listenUNIX(os.path.join(config.rundir, 'rpc.socket'), factory=pb.PBServerFactory(self.rpc_server))

         for i in range(config.processes):
             subprocess = spawnT2W(self, self.childFDs, self.fds_https, self.fds_http)
             self.subprocesses.append(subprocess.pid)

         def MailException(etype, value, tb):
             sendexceptionmail(config, etype, value, tb)

         sys.excepthook = MailException

         reactor.run()

     def daemon_reload(self):
         self.rpc_server.load_lists()

     def daemon_shutdown(self):
         self.quitting = True

         for pid in self.subprocesses:
             os.kill(pid, signal.SIGINT)

         self.subprocesses = []

     t2w_daemon = T2WDaemon(config)
     t2w_daemon.daemon_init = daemon_init
     t2w_daemon.daemon_main = daemon_main
     t2w_daemon.daemon_reload = daemon_reload
     t2w_daemon.daemon_shutdown = daemon_shutdown
     t2w_daemon.rpc_server = T2WRPCServer(config)

     t2w_daemon.run(config)

else:

     set_proctitle("tor2web-worker")

     access_list = []
     blocked_ua_list = []
     tor_exits_list = []
     ports = []

     rpc_factory = pb.PBClientFactory()

     reactor.connectUNIX(os.path.join(config.rundir, "rpc.socket"),  rpc_factory)
     os.chmod(os.path.join(config.rundir, "rpc.socket"), 0600)

     signal.signal(signal.SIGUSR1, SigQUIT)
     signal.signal(signal.SIGTERM, SigQUIT)
     signal.signal(signal.SIGINT, SigQUIT)

     start_worker()

     reactor.run()

########NEW FILE########
__FILENAME__ = config
"""
    Tor2web
    Copyright (C) 2012 Hermes No Profit Association - GlobaLeaks Project

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""

:mod:`Tor2Web`
=====================================================

.. automodule:: Tor2Web
   :synopsis: [GLOBALEAKS_MODULE_DESCRIPTION]

.. moduleauthor:: Arturo Filasto' <art@globaleaks.org>
.. moduleauthor:: Giovanni Pellerano <evilaliv3@globaleaks.org>

"""

# -*- coding: utf-8 -*-

import os
import re
import sys
import ConfigParser
from optparse import OptionParser
from storage import Storage

listpattern = re.compile(r'\s*("[^"]*"|.*?)\s*,')

class Config(Storage):
    """
    A Storage-like class which loads each attribute into a portable conf file.
    """
    def __init__(self):
        Storage.__init__(self)
        self._section = 'main'
        self._parser = ConfigParser.ConfigParser()

        parser = OptionParser()
        parser.add_option("-c", "--configfile", dest="configfile", default="/etc/tor2web.conf")
        parser.add_option("-p", "--pidfile", dest="pidfile", default='/var/run/tor2web/t2w.pid')
        parser.add_option("-u", "--uid", dest="uid", default='')
        parser.add_option("-g", "--gid", dest="gid", default='')
        parser.add_option("-n", "--nodaemon", dest="nodaemon", default=False, action="store_true")
        parser.add_option("-d", "--rundir", dest="rundir", default='/var/run/tor2web/')
        parser.add_option("-x", "--command", dest="command", default='start')
        (options, args) = parser.parse_args()

        self._file = options.configfile

        self.__dict__['configfile'] = options.configfile
        self.__dict__['pidfile'] = options.pidfile
        self.__dict__['uid'] = options.uid
        self.__dict__['gid'] = options.gid
        self.__dict__['nodaemon'] = options.nodaemon
        self.__dict__['command'] = options.command
        self.__dict__['nodename'] = 'tor2web'
        self.__dict__['datadir'] = '/home/tor2web'
        self.__dict__['rundir'] = options.rundir
        self.__dict__['logreqs'] = False
        self.__dict__['debugmode'] = False
        self.__dict__['debugtostdout'] = False
        self.__dict__['processes'] = 1
        self.__dict__['requests_per_process'] = 1000000
        self.__dict__['transport'] = 'BOTH'
        self.__dict__['listen_ipv4'] = '127.0.0.1'
        self.__dict__['listen_ipv6'] = None
        self.__dict__['listen_port_http'] = 80
        self.__dict__['listen_port_https'] = 443
        self.__dict__['basehost'] = 'tor2web.org'
        self.__dict__['sockshost'] = '127.0.0.1'
        self.__dict__['socksport'] = 9050
        self.__dict__['socksoptimisticdata'] = True
        self.__dict__['sockmaxpersistentperhost'] = 5
        self.__dict__['sockcachedconnectiontimeout'] = 240
        self.__dict__['sockretryautomatically'] = True
        self.__dict__['cipher_list'] = 'ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384:' \
                                       'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-SHA256:' \
                                       'ECDHE-RSA-AES256-SHA:DHE-DSS-AES256-SHA:DHE-RSA-AES128-SHA:' \
                                       'DES-CBC3-SHA' # this last one (not FS) is kept only for
                                                      # compatibility reasons :/
        self.__dict__['mode'] = 'BLACKLIST'
        self.__dict__['onion'] = None
        self.__dict__['blockcrawl'] = True
        self.__dict__['overriderobotstxt'] = True
        self.__dict__['disable_banner'] = False
        self.__dict__['smtp_user'] = ''
        self.__dict__['smtp_pass'] = ''
        self.__dict__['smtp_mail'] = ''
        self.__dict__['smtpmailto_exceptions'] = ''
        self.__dict__['smtpmailto_notifications'] = ''
        self.__dict__['smtpdomain'] = ''
        self.__dict__['smtpport'] = 587
        self.__dict__['exit_node_list_refresh'] = 600
        self.__dict__['automatic_blocklist_updates_source'] = ''
        self.__dict__['automatic_blocklist_updates_refresh'] = 600
        self.__dict__['mirror'] = []
        self.__dict__['dummyproxy'] = None

        # Development VS. Production
        localpath = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), "..", "data"))
        if os.path.exists(localpath):
            self.__dict__['sysdatadir'] = localpath
        else:
            self.__dict__['sysdatadir'] = '/usr/share/tor2web'

        self.load()

    def load(self):
        try:
            if (not os.path.exists(self._file) or
                not os.path.isfile(self._file) or
                not os.access(self._file, os.R_OK)):
                print "Tor2web Startup Failure: cannot open config file (%s)" % self._file
                exit(1)
        except Exception:
            print "Tor2web Startup Failure: error while accessing config file (%s)" % self._file
            exit(1)

        try:

            self._parser.read([self._file])

            for name in self._parser.options(self._section):
                self.__dict__[name] = self.parse(name)

        except Exception as e:
            print e
            raise Exception("Tor2web Error: invalid config file (%s)" % self._file)

    def splitlist(self, line):
        return [x[1:-1] if x[:1] == x[-1:] == '"' else x
            for x in listpattern.findall(line.rstrip(',') + ',')]

    def parse(self, name):
        try:

           value = self._parser.get(self._section, name)
           if value.isdigit():
                value = int(value)
           elif value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
           elif value.lower() in ('', 'none'):
                value = None
           elif value[0] == "[" and value[-1] == "]":
                value = self.splitlist(value[1:-1])

           return value

        except ConfigParser.NoOptionError:
            # if option doesn't exists returns None
            return None

    def __getattr__(self, name):
        return self.__dict__.get(name, None)

    def __setattr__(self, name, value):
        self.__dict__[name] = value

        # keep an open port with private attributes
        if name.startswith("_"):
            return

        try:

            # XXX: Automagically discover variable type
            self._parser.set(self._section, name, value)

        except ConfigParser.NoOptionError:
            raise NameError(name)

    def t2w_file_path(self, path):
        if os.path.exists(os.path.join(self.datadir, path)):
            return os.path.join(self.datadir, path)
        else:
            return os.path.join(self.sysdatadir, path)


########NEW FILE########
__FILENAME__ = daemon
"""
    Tor2web
    Copyright (C) 2012 Hermes No Profit Association - GlobaLeaks Project

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""

:mod:`Tor2Web`
=====================================================

.. automodule:: Tor2Web
   :synopsis: [GLOBALEAKS_MODULE_DESCRIPTION]

.. moduleauthor:: Arturo Filasto' <art@globaleaks.org>
.. moduleauthor:: Giovanni Pellerano <evilaliv3@globaleaks.org>

"""

# -*- coding: utf-8 -*-

import os
import sys
import time
import glob
import signal
import pwd
import grp
import atexit
import platform

import ctypes

class _NullDevice:
    """A substitute for stdout/stderr that writes to nowhere."""

    def isatty(self, *a, **kw):
        return False

    def write(self, s):
        pass

    def flush(self, s):
        pass


class T2WDaemon:
    def __init__(self, config):
        self.config = config

    def become_daemon(self):

        if os.fork() != 0:  # launch child and ...
            os._exit(0)     # kill off parent

        os.setsid()
        os.chdir(self.config.rundir)
        os.umask(077)

        if os.fork() != 0:  # fork again so we are not a session leader
            os._exit(0)

        sys.stdin.close()
        sys.__stdin__ = sys.stdin

        sys.stdout.close()
        sys.stdout = sys.__stdout__ = _NullDevice()

        sys.stderr.close()
        sys.stderr = sys.__stderr__ = _NullDevice()

    def daemon_start(self):
        self.daemon_init(self) # self must be explicit passed
                               # as the function is user defined

        if not os.path.exists(self.config.rundir):
            os.mkdir(self.config.rundir)

        os.chmod(self.config.rundir, 0700)

        if not self.config.nodaemon:
            self.become_daemon()

        with open(self.config.pidfile, 'w') as f:
            f.write("%s" % os.getpid())

        os.chmod(self.config.pidfile, 0600)

        @atexit.register
        def goodbye():
            try:
                os.unlink(self.config.pidfile)
            except Exception:
                pass

        if (self.config.uid != "") and (self.config.gid != ""):
            self.change_uid()

        def _daemon_reload(SIG, FRM):
            self.daemon_reload() # self must be explicit passed
                                 # as the function is user defined

        def _daemon_shutdown(SIG, FRM):
            self.daemon_shutdown(self) # self must be explicit passed
                                       # as the function is user defined

        signal.signal(signal.SIGHUP, _daemon_reload)
        signal.signal(signal.SIGTERM, _daemon_shutdown)
        signal.signal(signal.SIGINT, _daemon_shutdown)

        self.daemon_main(self) # self must be explicit passed
                               # as the function is user defined

    def daemon_stop(self):
        pid = self.get_pid()

        try:
            os.kill(pid, signal.SIGINT)  # SIGTERM is too harsh...
        except Exception:
            pass

        time.sleep(1)

        try:
            os.unlink(self.config.pidfile)
        except Exception:
            pass

    def get_pid(self):
        try:
            f = open(self.config.pidfile)
            pid = int(f.readline().strip())
            f.close()
        except IOError:
            pid = None
        return pid

    def is_process_running(self):
        pid = self.get_pid()
        if pid:
            try:
                os.kill(pid, 0)
                return 1
            except OSError:
                pass
        return 0

    def change_uid(self):
        c_user =  self.config.uid
        c_group = self.config.gid

        if os.getuid() == 0:
            cpw = pwd.getpwnam(c_user)
            c_uid = cpw.pw_uid
            if c_group:
                cgr = grp.getgrnam(c_group)
                c_gid = cgr.gr_gid
            else:
                c_gid = cpw.pw_gid

            c_groups = []
            for item in grp.getgrall():
                if c_user in item.gr_mem:
                    c_groups.append(item.gr_gid)
                if c_gid not in c_groups:
                    c_groups.append(c_gid)

            os.chown(self.config.rundir, c_uid, c_gid)
            os.chown(self.config.pidfile, c_uid, c_gid)

            for item in glob.glob(self.config.rundir + '/*'):
                os.chown(item, c_uid, c_gid)

            os.setgid(c_gid)
            os.setgroups(c_groups)
            os.setuid(c_uid)

    def run(self, config):

        if self.config.command == 'status':
            if not self.is_process_running():
                exit(1)
            else:
                exit(0)
        elif self.config.command == 'start':
            if not self.is_process_running():
                self.daemon_start()
                exit(0)
            else:
                print "Unable to start Tor2web: process is already running."
                exit(1)
        elif self.config.command == 'stop':
            if self.is_process_running():
                self.daemon_stop()
            exit(0)
        elif self.config.command == 'reload':
            if self.is_process_running():
                pid = self.get_pid()
                try:
                    os.kill(pid, signal.SIGHUP)
                except Exception:
                    pass
            else:
                self.daemon_start()
            exit(0)
        elif self.config.command == 'restart':
            self.daemon_stop()
            self.daemon_start()
            exit(0)
        else:
            print "Unknown command:", self.config.command
            raise SystemExit

        exit(1)

    def daemon_init(self):
        pass

    def daemon_reload(self):
        pass

    def daemon_shutdown(self):
        pass

    def daemon_main(self):
        pass

def set_proctitle(title):
    if platform.system() == 'Linux': # Virgil has Mac OS!
        libc = ctypes.cdll.LoadLibrary('libc.so.6')
        buff = ctypes.create_string_buffer(len(title) + 1)
        buff.value = title
        libc.prctl(15, ctypes.byref(buff), 0, 0, 0)

def set_pdeathsig(sig):
    if platform.system() == 'Linux': # Virgil has Mac OS!
        PR_SET_PDEATHSIG = 1
        libc = ctypes.cdll.LoadLibrary('libc.so.6')
        libc.prctl.argtypes = (ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                               ctypes.c_ulong, ctypes.c_ulong)
        libc.prctl(PR_SET_PDEATHSIG, sig, 0, 0, 0)

########NEW FILE########
__FILENAME__ = lists
"""
    Tor2web
    Copyright (C) 2012 Hermes No Profit Association - GlobaLeaks Project

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""

:mod:`Tor2Web`
=====================================================

.. automodule:: Tor2Web
   :synopsis: [GLOBALEAKS_MODULE_DESCRIPTION]

.. moduleauthor:: Arturo Filasto' <art@globaleaks.org>
.. moduleauthor:: Giovanni Pellerano <evilaliv3@globaleaks.org>

"""

# -*- coding: utf-8 -*-

import re
import gzip
import json
from StringIO import StringIO
import os
import glob

from OpenSSL import SSL
from twisted.internet import reactor, ssl
from twisted.internet.task import LoopingCall
from twisted.internet.defer import Deferred
from twisted.web.client import HTTPPageGetter, HTTPClientFactory, _URI
from OpenSSL.SSL import VERIFY_PEER, VERIFY_FAIL_IF_NO_PEER_CERT
from OpenSSL.crypto import load_certificate, FILETYPE_PEM


certificateAuthorityMap = {}

for certFileName in glob.glob("/etc/ssl/certs/*.pem"):
    # There might be some dead symlinks in there, so let's make sure it's real.
    if os.path.exists(certFileName):
        data = open(certFileName).read()
        x509 = load_certificate(FILETYPE_PEM, data)
        digest = x509.digest('sha1')
        # Now, de-duplicate in case the same cert has multiple names.
        certificateAuthorityMap[digest] = x509

class HTTPSVerifyingContextFactory(ssl.ClientContextFactory):
    def __init__(self, hostname):
        self.hostname = hostname

    def getContext(self):
        ctx = self._contextFactory(self.method)

        # Disallow SSLv2! It's insecure!
        ctx.set_options(SSL.OP_NO_SSLv2)

        ctx.set_options(SSL.OP_SINGLE_DH_USE)

        # http://en.wikipedia.org/wiki/CRIME_(security_exploit)
        # https://twistedmatrix.com/trac/ticket/5487
        # SSL_OP_NO_COMPRESSION = 0x00020000L
        ctx.set_options(0x00020000)

        store = ctx.get_cert_store()
        for value in certificateAuthorityMap.values():
            store.add_cert(value)
        ctx.set_verify(VERIFY_PEER | VERIFY_FAIL_IF_NO_PEER_CERT, self.verifyHostname)
        return ctx

    def verifyHostname(self, connection, x509, errno, depth, preverifyOK):
        if  depth == 0 and preverifyOK:
            cn = x509.get_subject().commonName

            if cn.startswith(b"*.") and self.hostname.split(b".")[1:] == cn.split(b".")[1:]:
                return True

            elif self.hostname == cn:
                return True

            return False

        return preverifyOK

def getPageCached(url, contextFactory=None, *args, **kwargs):
    """download a web page as a string, keep a cache of already downloaded pages

    Download a page. Return a deferred, which will callback with a
    page (as a string) or errback with a description of the error.

    See HTTPClientCacheFactory to see what extra args can be passed.
    """
    uri = _URI.fromBytes(url)
    scheme = uri.scheme
    host = uri.host
    port = uri.port

    factory = HTTPClientCacheFactory(url, *args, **kwargs)

    if scheme == 'https':
        if contextFactory is None:
            contextFactory = HTTPSVerifyingContextFactory(host)
        reactor.connectSSL(host, port, factory, contextFactory)
    else:
        reactor.connectTCP(host, port, factory)

    return factory.deferred

class HTTPCacheDownloader(HTTPPageGetter):
    def connectionMade(self, isCached=False):
        self.content_is_gzip = False

        if self.factory.url in self.factory.cache and 'response' in self.factory.cache[self.factory.url]:
            self.cache = self.factory.cache[self.factory.url]
        else:
            self.cache = None

        self.cachetemp = {}

        method = getattr(self.factory, 'method', 'GET')
        self.sendCommand(method, self.factory.path)
        if self.factory.scheme == 'http' and self.factory.port != 80:
            host = '%s:%s' % (self.factory.host, self.factory.port)
        elif self.factory.scheme == 'https' and self.factory.port != 443:
            host = '%s:%s' % (self.factory.host, self.factory.port)
        else:
            host = self.factory.host

        self.sendHeader('host', self.factory.headers.get('host', host))
        self.sendHeader('user-agent', self.factory.agent)
        self.sendHeader('accept-encoding', 'gzip')

        if self.cache and 'etag' in self.cache:
            self.sendHeader('etag', self.cache['etag'])

        if self.cache and 'if-modified-since' in self.cache:
            self.sendHeader('if-modified-since', self.cache['if-modified-since'])

        data = getattr(self.factory, 'postdata', None)
        if data is not None:
            self.sendHeader('content-length', str(len(data)))

        cookieData = []
        for (key, value) in self.factory.headers.items():
            if key.lower() not in self._specialHeaders:
                # we calculated it on our own
                self.sendHeader(key, value)
            if key.lower() == 'cookie':
                cookieData.append(value)
        for cookie, cookval in self.factory.cookies.items():
            cookieData.append('%s=%s' % (cookie, cookval))
        if cookieData:
            self.sendHeader('cookie', '; '.join(cookieData))

        self.endHeaders()
        self.headers = {}

        if data is not None:
            self.transport.write(data)

    def handleHeader(self, key, value):
        key = key.lower()

        if key == 'date' or key == 'last-modified':
            self.cachetemp[key] = value

        if key == 'etag':
            self.cachetemp[key] = value

        if key == 'content-encoding' and value == 'gzip':
            self.content_is_gzip = True

        HTTPPageGetter.handleHeader(self, key, value)

    def handleResponse(self, response):
        if self.content_is_gzip:
            c_f = StringIO(response)
            response = gzip.GzipFile(fileobj=c_f).read()

        self.cachetemp['response'] = response
        self.factory.cache[self.factory.url] = self.cachetemp
        HTTPPageGetter.handleResponse(self, response)

    def handleStatus(self, version, status, message):
        HTTPPageGetter.handleStatus(self, version, status, message)

    def handleStatus_304(self):
        # content not modified
        pass

class HTTPClientCacheFactory(HTTPClientFactory):
    protocol = HTTPCacheDownloader
    cache = {}

    def __init__(self, url, method='GET', postdata=None, headers=None,
                 agent="Tor2Web (https://github.com/globaleaks/tor2web-3.0)",
                 timeout=0, cookies=None,
                 followRedirect=1):

        headers = {}

        if url in self.cache:
            if 'etag' in self.cache[url]:
                headers['etag'] = self.cache[url]['etag']
            elif 'last-modified' in self.cache[url]:
                headers['if-modified-since'] = self.cache[url]['last-modified']
            elif 'date' in self.cache[url]:
                headers['if-modified-since'] = self.cache[url]['date']

        HTTPClientFactory.__init__(self, url=url, method=method,
                postdata=postdata, headers=headers, agent=agent,
                timeout=timeout, cookies=cookies, followRedirect=followRedirect)
        self.deferred = Deferred()


class List(set):
    def __init__(self, filename, url='', refreshPeriod=0):
        set.__init__(self)
        self.filename = filename
        self.url = url

        self.load()

        if url != '' and refreshPeriod != 0:
            self.lc = LoopingCall(self.update)
            self.lc.start(refreshPeriod)

    def load(self):
        """
        Load the list from the specified file.
        """
        self.clear()

        #simple touch to create non existent files
        try:
            open(self.filename, 'a').close()

            with open(self.filename, 'r') as fh:
                for l in fh.readlines():
                    self.add(re.split("#", l)[0].rstrip("[ , \n,\t]"))
        except:
            pass

    def dump(self):
        """
        Dump the list to the specified file.
        """
        try:
            with open(self.filename, 'w') as fh:
                for l in self:
                    fh.write(l + "\n")
        except:
            pass

    def handleData(self, data):
        for elem in data.split('\n'):
            if elem != '':
                self.add(elem)

    def processData(self, data):
        try:
            if len(data) != 0:
                self.handleData(data)
                self.dump()
        except Exception:
            pass

    def update(self):
        pageFetchedDeferred = getPageCached(self.url)
        pageFetchedDeferred.addCallback(self.processData)
        return pageFetchedDeferred

class TorExitNodeList(List):
    def handleData(self, data):
        self.clear()
        data = json.loads(data)
        for relay in data['relays']:
            for ip in relay['a']:
                if ip != '':
                    self.add(ip)

########NEW FILE########
__FILENAME__ = mail
"""
    Tor2web
    Copyright (C) 2012 Hermes No Profit Association - GlobaLeaks Project

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""

:mod:`Tor2Web`
=====================================================

.. automodule:: Tor2Web
   :synopsis: [GLOBALEAKS_MODULE_DESCRIPTION]

.. moduleauthor:: Arturo Filasto' <art@globaleaks.org>
.. moduleauthor:: Giovanni Pellerano <evilaliv3@globaleaks.org>

"""

# -*- coding: utf-8 -*-

import re
import traceback
from StringIO import StringIO

from OpenSSL import SSL
from twisted.internet import reactor, defer
from twisted.mail.smtp import ESMTPSenderFactory
from twisted.internet.ssl import ClientContextFactory

from tor2web import __version__


def sendmail(authenticationUsername, authenticationSecret, fromAddress, toAddress, messageFile, smtpHost, smtpPort=25):
    """
    Sends an email using SSLv3 over SMTP

    @param authenticationUsername: account username
    @param authenticationSecret: account password
    @param fromAddress: the from address field of the email
    @param toAddress: the to address field of the email
    @param messageFile: the message content
    @param smtpHost: the smtp host
    @param smtpPort: the smtp port
    """
    contextFactory = ClientContextFactory()
    contextFactory.method = SSL.SSLv3_METHOD

    resultDeferred = defer.Deferred()

    senderFactory = ESMTPSenderFactory(
        authenticationUsername,
        authenticationSecret,
        fromAddress,
        toAddress,
        messageFile,
        resultDeferred,
        contextFactory=contextFactory)

    reactor.connectTCP(smtpHost, smtpPort, senderFactory)

    return resultDeferred

def sendexceptionmail(config, etype, value, tb):
    """
    Formats traceback and exception data and emails the error

    @param etype: Exception class type
    @param value: Exception string value
    @param tb: Traceback string data
    """

    exc_type = re.sub("(<(type|class ')|'exceptions.|'>|__main__.)", "", str(etype))

    tmp = []
    tmp.append("From: Tor2web Node %s.%s <%s>\n" % (config.nodename, config.basehost, config.smtpmail))
    tmp.append("To: %s\n" % config.smtpmailto_exceptions)
    tmp.append("Subject: Tor2web Node Exception (IPV4: %s, IPv6: %s)\n" % (config.listen_ipv4, config.listen_ipv6))
    tmp.append("Content-Type: text/plain; charset=ISO-8859-1\n")
    tmp.append("Content-Transfer-Encoding: 8bit\n\n")
    tmp.append("Exception from Node %s (IPV4: %s, IPv6: %s)\n" % (config.nodename, config.listen_ipv4, config.listen_ipv6))
    tmp.append("Tor2web version: %s\n" % __version__)

    error_message = "%s %s" % (exc_type.strip(), etype.__doc__)
    tmp.append(error_message)

    traceinfo = '\n'.join(traceback.format_exception(etype, value, tb))
    tmp.append(traceinfo)

    info_string = ''.join(tmp)
    message = StringIO(info_string)

    sendmail(config.smtpuser, config.smtppass, config.smtpmail, config.smtpmailto_exceptions, message, config.smtpdomain, config.smtpport)

########NEW FILE########
__FILENAME__ = misc
"""
    Tor2web
    Copyright (C) 2012 Hermes No Profit Association - GlobaLeaks Project

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""

:mod:`Tor2Web`
=====================================================

.. automodule:: Tor2Web
   :synopsis: [GLOBALEAKS_MODULE_DESCRIPTION]

.. moduleauthor:: Arturo Filasto' <art@globaleaks.org>
.. moduleauthor:: Giovanni Pellerano <evilaliv3@globaleaks.org>

"""

# -*- coding: utf-8 -*-

import re
import socket

try:
    from twisted.protocols import tls

except ImportError:
    raise Exception("tor2web: ssl hack for listenSSLonExistingFD not implemented (tls only)")


def listenTCPonExistingFD(reactor, fd, factory):
    return reactor.adoptStreamPort(fd, socket.AF_INET, factory)

def listenSSLonExistingFD(reactor, fd, factory, contextFactory):

    tlsFactory = tls.TLSMemoryBIOFactory(contextFactory, False, factory)
    port = reactor.listenTCPonExistingFD(reactor, fd, tlsFactory)
    port._type = 'TLS'
    return port

def re_sub(pattern, replacement, string):
    def _r(m):
        # Now this is ugly.
        # Python has a "feature" where unmatched groups return None
        # then re_sub chokes on this.
        # see http://bugs.python.org/issue1519638

        # this works around and hooks into the internal of the re module...

        # the match object is replaced with a wrapper that
        # returns "" instead of None for unmatched groups

        class _m():
            def __init__(self, m):
                self.m=m
                self.string=m.string
            def group(self, n):
                return m.group(n) or ""

        return re._expand(pattern, _m(m), replacement)

    return re.sub(pattern, _r, string)

def verify_onion(address):
    """
    Check to see if the address is a .onion.
    returns the onion address as a string if True else returns False
    """
    try:
        onion, tld = address.split(".")
        if tld == 'onion' and len(onion) == 16 and onion.isalnum():
            return True
    except Exception:
        pass

    return False

########NEW FILE########
__FILENAME__ = socks
"""
    Tor2web
    Copyright (C) 2012 Hermes No Profit Association - GlobaLeaks Project

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""

:mod:`Tor2Web`
=====================================================

.. automodule:: Tor2Web
   :synopsis: [GLOBALEAKS_MODULE_DESCRIPTION]

.. moduleauthor:: Arturo Filasto' <art@globaleaks.org>
.. moduleauthor:: Giovanni Pellerano <evilaliv3@globaleaks.org>

"""

# -*- coding: utf-8 -*-

import struct

from zope.interface import implementer
from twisted.internet import defer, interfaces
from twisted.protocols.policies import ProtocolWrapper, WrappingFactory
from twisted.python.failure import Failure

from twisted.internet.protocol import Protocol

from zope.interface import directlyProvides, providedBy


class SOCKSError(Exception):
    def __init__(self, value):
        Exception.__init__(self)
        self.code = value

class SOCKSv5ClientProtocol(ProtocolWrapper):
    def __init__(self, factory, wrappedProtocol, connectedDeferred, host, port, optimistic = False):
        ProtocolWrapper.__init__(self, factory, wrappedProtocol)
        self._connectedDeferred = connectedDeferred
        self._host = host
        self._port = port
        self._optimistic = optimistic
        self._buf = ''
        self.state = 0

    def error(self, error):
        if not self._optimistic:
            self._connectedDeferred.errback(error)
        else:
            errorcode = 600 + error.value.code
            self.wrappedProtocol.dataReceived("HTTP/1.1 "+str(errorcode)+" ANTANI\r\n\r\n")

        self.transport.abortConnection()
        self.transport = None

    def socks_state_0(self):
        # error state
        self.error(SOCKSError(0x00))
        return

    def socks_state_1(self):
        if len(self._buf) < 2:
            return

        if self._buf[:2] != "\x05\x00":
            # Anonymous access denied
            self.error(Failure(SOCKSError(0x00)))
            return

        if not self._optimistic:
            self.transport.write(struct.pack("!BBBBB", 5, 1, 0, 3, len(self._host)) + self._host + struct.pack("!H", self._port))

        self._buf = self._buf[2:]

        self.state += 1

    def socks_state_2(self):
        if len(self._buf) < 10:
            return

        if self._buf[:2] != "\x05\x00":
            self.error(Failure(SOCKSError(ord(self._buf[1]))))
            return

        self._buf = self._buf[10:]

        if not self._optimistic:
            self.wrappedProtocol.makeConnection(self)
            try:
                self._connectedDeferred.callback(self.wrappedProtocol)
            except Exception:
                pass

        self.wrappedProtocol.dataReceived(self._buf)
        self._buf = ''

        self.state += 1

    def makeConnection(self, transport):
        """
        When a connection is made, register this wrapper with its factory,
        save the real transport, and connect the wrapped protocol to this
        L{ProtocolWrapper} to intercept any transport calls it makes.
        """
        directlyProvides(self, providedBy(transport))
        Protocol.makeConnection(self, transport)
        self.factory.registerProtocol(self)

        # We implement only Anonymous access
        self.transport.write(struct.pack("!BB", 5, len("\x00")) + "\x00")

        if self._optimistic:
            self.transport.write(struct.pack("!BBBBB", 5, 1, 0, 3, len(self._host)) + self._host + struct.pack("!H", self._port))
            self.wrappedProtocol.makeConnection(self)
            try:
                self._connectedDeferred.callback(self.wrappedProtocol)
            except Exception:
                pass

        self.state += 1

    def dataReceived(self, data):
        if self.state != 3:
            self._buf = ''.join([self._buf, data])
            getattr(self, 'socks_state_%s' % self.state)()
        else:
            self.wrappedProtocol.dataReceived(data)


class SOCKSv5ClientFactory(WrappingFactory):
    protocol = SOCKSv5ClientProtocol

    def __init__(self, wrappedFactory, host, port, optimistic):
        WrappingFactory.__init__(self, wrappedFactory)
        self._host = host
        self._port = port
        self._optimistic = optimistic
        self._onConnection = defer.Deferred()

    def buildProtocol(self, addr):
        try:
            proto = self.wrappedFactory.buildProtocol(addr)
        except Exception:
            self._onConnection.errback()
        else:
            return self.protocol(self, proto, self._onConnection,
                                 self._host, self._port, self._optimistic)

    def clientConnectionFailed(self, connector, reason):
        self._onConnection.errback(reason)

    def clientConnectionLost(self, connector, reason):
        pass

    def unregisterProtocol(self, p):
        """
        Called by protocols when they go away.
        """
        try:
            del self.protocols[p]
        except Exception:
            pass


@implementer(interfaces.IStreamClientEndpoint)
class SOCKS5ClientEndpoint(object):
    """
    SOCKS5 TCP client endpoint with an IPv4 configuration.
    """
    def __init__(self, reactor, sockhost, sockport,
                 host, port, optimistic, timeout=30, bindAddress=None):
        self._reactor = reactor
        self._sockhost = sockhost
        self._sockport = sockport
        self._host = host
        self._port = port
        self._optimistic = optimistic
        self._timeout = timeout
        self._bindAddress = bindAddress

    def connect(self, protocolFactory):
        try:
            wf = SOCKSv5ClientFactory(protocolFactory, self._host, self._port, self._optimistic)
            self._reactor.connectTCP(
                self._sockhost, self._sockport, wf,
                timeout=self._timeout, bindAddress=self._bindAddress)
            return wf._onConnection
        except Exception:
            return defer.fail()

########NEW FILE########
__FILENAME__ = ssl
"""
    Tor2web
    Copyright (C) 2012 Hermes No Profit Association - GlobaLeaks Project

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""

:mod:`Tor2Web`
=====================================================

.. automodule:: Tor2Web
   :synopsis: [GLOBALEAKS_MODULE_DESCRIPTION]

.. moduleauthor:: Arturo Filasto' <art@globaleaks.org>
.. moduleauthor:: Giovanni Pellerano <evilaliv3@globaleaks.org>

"""

# -*- coding: utf-8 -*-

from OpenSSL import SSL

from twisted.internet.ssl import ContextFactory

class T2WSSLContext(SSL.Context):

    def load_tmp_dh(self, dhfile):
        """
        Function overridden in order to enforce ECDH/PFS
        """

        from OpenSSL._util import (ffi as _ffi,
                                   lib as _lib)

        if not isinstance(dhfile, bytes):
            raise TypeError("dhfile must be a byte string")

        bio = _lib.BIO_new_file(dhfile, b"r")
        if bio == _ffi.NULL:
            _raise_current_error()
        bio = _ffi.gc(bio, _lib.BIO_free)

        dh = _lib.PEM_read_bio_DHparams(bio, _ffi.NULL, _ffi.NULL, _ffi.NULL)
        dh = _ffi.gc(dh, _lib.DH_free)
        _lib.SSL_CTX_set_tmp_dh(self._context, dh)

        ecdh = _lib.EC_KEY_new_by_curve_name(_lib.NID_X9_62_prime256v1)
        ecdh = _ffi.gc(ecdh, _lib.EC_KEY_free)
        _lib.SSL_CTX_set_tmp_ecdh(self._context, ecdh)


class T2WSSLContextFactory(ContextFactory):
    _context = None

    def __init__(self, privateKeyFileName, certificateChainFileName, dhFileName, cipherList):
        """
        @param privateKeyFileName: Name of a file containing a private key
        @param certificateChainFileName: Name of a file containing a certificate chain
        @param dhFileName: Name of a file containing diffie hellman parameters
        @param cipherList: The SSL cipher list selection to use
        """
        self.privateKeyFileName = privateKeyFileName
        self.certificateChainFileName = certificateChainFileName
        self.sslmethod = SSL.SSLv23_METHOD
        self.dhFileName = dhFileName
        self.cipherList = cipherList

        # Create a context object right now.  This is to force validation of
        # the given parameters so that errors are detected earlier rather
        # than later.
        self.cacheContext()

    def cacheContext(self):
        if self._context is None:
            ctx = SSL.Context(self.sslmethod)

            ctx.set_options(SSL.OP_CIPHER_SERVER_PREFERENCE |
                            SSL.OP_NO_SSLv2 |
                            SSL.OP_SINGLE_DH_USE |
                            SSL.OP_NO_COMPRESSION |
                            SSL.OP_NO_TICKET)

            ctx.set_mode(SSL.MODE_RELEASE_BUFFERS)

            ctx.use_certificate_chain_file(self.certificateChainFileName)
            ctx.use_privatekey_file(self.privateKeyFileName)
            ctx.set_cipher_list(self.cipherList)
            ctx.load_tmp_dh(self.dhFileName)
            self._context = ctx

    def getContext(self):
        """
        Return an SSL context.
        """
        return self._context

########NEW FILE########
__FILENAME__ = stats
"""
    Tor2web
    Copyright (C) 2012 Hermes No Profit Association - GlobaLeaks Project

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""

:mod:`Tor2Web`
=====================================================

.. automodule:: Tor2Web
   :synopsis: [GLOBALEAKS_MODULE_DESCRIPTION]

.. moduleauthor:: Arturo Filasto' <art@globaleaks.org>
.. moduleauthor:: Giovanni Pellerano <evilaliv3@globaleaks.org>

"""

# -*- coding: utf-8 -*-


from datetime import date, datetime, timedelta

import json

from twisted.internet import reactor
from twisted.internet.task import deferLater

class T2WStats(dict):
    def __init__(self):
        dict.__init__(self)
        self.yesterday_stats = ''

        self.update_stats()

    def update(self, key):
        if key not in self:
            self[key] = 0
        self[key] += 1

    def update_stats(self, run_again=True):
        yesterday = date.today() - timedelta(1)
        hidden_services = list()
        for k in self:
            hidden_services.append(({'id': k, 'access_count': self[k]}))

        self.yesterday_stats = json.dumps({'date': yesterday.strftime('%Y-%m-%d'),
                                           'hidden_services': hidden_services})
        self.clear()

        next_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + \
                    timedelta(days=1)
        next_delta = (next_time - datetime.now()).total_seconds()
        deferLater(reactor, next_delta, self.update_stats)

########NEW FILE########
__FILENAME__ = storage
"""
    Tor2web
    Copyright (C) 2012 Hermes No Profit Association - GlobaLeaks Project

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""

:mod:`Tor2Web`
=====================================================

.. automodule:: Tor2Web
   :synopsis: [GLOBALEAKS_MODULE_DESCRIPTION]

.. moduleauthor:: Arturo Filasto' <art@globaleaks.org>
.. moduleauthor:: Giovanni Pellerano <evilaliv3@globaleaks.org>

"""

# -*- coding: utf-8 -*-

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.

        >>> o = Storage(a=1)
        >>> o.a
        1
        >>> o['a']
        1
        >>> o.a = 2
        >>> o['a']
        2
        >>> del o.a
        >>> o.a
        None

    """
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            return None

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError as k:
            raise AttributeError, k

    def __repr__(self):
        return "<Storage " + dict.__repr__(self) + ">"

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, value):
        for (k, v) in value.items():
            self[k] = v

########NEW FILE########
__FILENAME__ = templating
"""
    Tor2web
    Copyright (C) 2012 Hermes No Profit Association - GlobaLeaks Project

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""

:mod:`Tor2Web`
=====================================================

.. automodule:: Tor2Web
   :synopsis: [GLOBALEAKS_MODULE_DESCRIPTION]

.. moduleauthor:: Arturo Filasto' <art@globaleaks.org>
.. moduleauthor:: Giovanni Pellerano <evilaliv3@globaleaks.org>

"""

# -*- coding: utf-8 -*-

from twisted.web.template import Element, renderer, tags
from twisted.web.error import MissingTemplateLoader

class PageTemplate(Element):
    def lookupRenderMethod(self, name):
        method = renderer.get(self, name, None)
        if method is None:
            def renderUsingDict(request, tag):
                if name.startswith("t2wvar-"):
                    prefix, var = name.split("-")
                    if var in request.var:
                        return tag('%s' % request.var[var])
                return tag('undefined-var')
            return renderUsingDict
        return method

    def render(self, request):
        loader = self.loader
        if loader is None:
            raise MissingTemplateLoader(self)
        return loader.load()

    @renderer
    def mirror(self, request, tag):
        if 'mirror' in request.var and request.var['mirror'] != '':
            url = "https://%s.%s%s" % (request.var['onion'], request.var['mirror'], request.var['path'])
            return ["This page is accessible also on the following random mirror: "], tags.a(href=url, title=url)(request.var['mirror'])
        return ""

########NEW FILE########
