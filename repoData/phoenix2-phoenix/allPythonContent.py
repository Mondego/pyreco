__FILENAME__ = cpu
# THIS IS AN EXAMPLE KERNEL FOR PHOENIX 2.
# THOUGH IT IS FULLY FUNCTIONAL, IT IS QUITE SLOW. IT IS INTENDED FOR
# DEMONSTRATION PURPOSES ONLY.

# Additionally, this doesn't demonstrate QueueReader, which is the preferred
# way of making kernels that dispatch a separate thread to handle NonceRanges
# (as this one does)

import time
from twisted.internet import reactor, defer

# You should really look at the functions defined here. They are useful.
from phoenix2.core.KernelInterface import KernelOption

# This class needs to be defined in all Phoenix 2 kernels. The required
# functions are __init__, start, and stop. Everything else is optional.
class PhoenixKernel(object):
    # Here you can define options that the kernel will accept from the
    # configuration file.
    GREETING = KernelOption('greeting', str, default='',
                            help='Defines what debug message should be '
                                 'printed at kernel start-up time.')

    def __init__(self, interface):
        self.interface = interface
        self._stop = False

        # Here we can ask the interface for the Phoenix 2 device ID, which is a
        # lower-case (it is lower-cased by Phoenix even if caps are used in the
        # configuration file) string identifying a specific device on the
        # system.
        # We don't need this for much, given that this is a CPU miner, but
        # let's just show how to access it.
        if not self.interface.getDeviceID().startswith('cpu:'):
            self.interface.fatal('This kernel is only for CPUs!')
            return

        # Let's also print that configuration message that we set up before...
        self.interface.debug('Greeting: ' + self.GREETING)

        # We can also provide metadata on what the kernel is doing.
        self.interface.setMeta('cores', '1')

    @classmethod
    def autodetect(cls, callback):
        # This class method is used when Phoenix loads the kernel to autodetect
        # the devices that it supports. When this function runs, the kernel is
        # to look for all supported devices present on the system, and call
        # callback(devid) for each one.
        # It is also legal to store the callback and trigger the callback in
        # the event of hotplug. If this is the case, the kernel must also
        # define a class method called stopAutodetect() that disables hotplug
        # detection.
        # Also note that it is legal to call this function multiple times
        # without calling stopAutodetect in between. If this function is called
        # again, the kernel must redetect all devices present and send them all
        # through the callback again, even the ones it has already detected.

        # In this case, there is only one device this kernel supports: the CPU
        # (which we know is present) - the CPU is identified by devid cpu:0 by
        # default. The user can use cpu:1, etc, if he wishes to run several CPU
        # kernels in tandem (for some reason), but the canonical ID for
        # "the CPU" is always cpu:0.
        callback('cpu:0')

    @classmethod
    def analyzeDevice(cls, devid):
        # This class method is for analyzing how well a kernel will support a
        # specific device to help Phoenix automatically choose kernels.
        # It is to return a tuple: (suitability, config, ids)
        # Where 'suitability' is a number in the following table:
        # 0 - DO NOT USE THIS KERNEL
        # 1 - WILL WORK AS A FALLBACK
        # 2 - INTENDED USE FOR THIS CLASS OF HARDWARE
        # 3 - OPTIMIZED FOR THIS BRAND OF HARDWARE
        # 4 - OPTIMIZED FOR THIS SPECIFIC MODEL OF HARDWARE
        # 5 - OPTIMIZED FOR THIS HARDWARE'S CURRENT CONFIGURATION
        #     (e.g. kernels that work well when clocks are low, etc)
        # And config is a dictionary of recommended configuration values, which
        # will get used unless the user explicitly disables autoconfiguration.
        # Finally, ids is the list of IDs that the device is known by, with the
        # "preferred" ID being the first one.

        if devid.startswith('cpu:'):
            return (1, {}, [devid])
        else:
            return (0, {}, [devid])

    def start(self):
        self._stop = False
        reactor.callInThread(self.mine)

    def stop(self):
        self._stop = True

    def _fetchRangeHelper(self, d):
        # This function is a workaround for Twisted's threading model. The
        # callFromThread function, which is necessary to invoke a function in
        # the main thread, does not come back with return values. So, this
        # function accepts a deferred, fetches some work, and fires the work
        # through the deferred. QueueReader deals with all of this internally.
        self.interface.fetchRange().chainDeferred(d)

    # inlineCallbacks is a Twisted thing, it means you can do "x = yield y"
    # where y is a Deferred, and it will pause your function until the Deferred
    # fires back with a value
    @defer.inlineCallbacks
    def mine(self):
        # This is rate-counting logic...
        nonceCounter = 0
        nonceTime = time.time()

        while True:
            d = defer.Deferred()
            reactor.callFromThread(self._fetchRangeHelper, d)
            nr = yield d
            # Now we work on nr...
            # This is defined in WorkQueue.py
            for nonce in xrange(nr.base, nr.base+nr.size):
                # Here we simply have to test nonce. We can do this ourselves,
                # but the interface has a convenience function to do this for
                # us. (It doesn't communicate elsewhere with Phoenix and is
                # therefore safe to use without reactor.callFromThread)
                hash = self.interface.calculateHash(nr.unit, nonce)

                # There's also a convenience function for comparing the hash
                # against the target.
                if self.interface.checkTarget(hash, nr.unit.target):
                    # It's good! Let's send it in...
                    reactor.callFromThread(self.interface.foundNonce, nr.unit,
                                           nonce)

                # Count the nonce we just did, and report the rate, in
                # kilohashes, to the interface.
                nonceCounter += 1
                if nonceCounter >= 0x100:
                    now = time.time()
                    dt = now - nonceTime
                    reactor.callFromThread(self.interface.updateRate,
                                           int(nonceCounter/dt/1000))
                    nonceCounter = 0
                    nonceTime = now

                # Finally, this thread needs to die if the kernel has been
                # asked to stop...
                if self._stop:
                    return

########NEW FILE########
__FILENAME__ = phoenix
#!/usr/bin/env python

from phoenix2 import main

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = ClientBase
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import struct

class AssignedWork(object):
    data = None
    mask = None
    target = None
    maxtime = None
    time = None
    identifier = None
    def setMaxTimeIncrement(self, n):
        self.time = n
        self.maxtime = struct.unpack('>I', self.data[68:72])[0] + n

class ClientBase(object):
    callbacksActive = True

    def _deactivateCallbacks(self):
        """Shut down the runCallback function. Typically used post-disconnect.
        """
        self.callbacksActive = False

    def runCallback(self, callback, *args):
        """Call the callback on the handler, if it's there, specifying args."""

        if not self.callbacksActive:
            return

        func = getattr(self.handler, 'on' + callback.capitalize(), None)
        if callable(func):
            func(*args)
########NEW FILE########
__FILENAME__ = MMPProtocol
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from twisted.internet import reactor, defer
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.protocols.basic import LineReceiver

from ClientBase import *

class MMPProtocolBase(LineReceiver):
    delimiter = '\r\n'
    commands = {} # To be overridden by superclasses...

    def lineReceived(self, line):
        # The protocol uses IRC-style argument passing. i.e. space-separated
        # arguments, with the final one optionally beginning with ':' (in which
        # case, the final argument is the only one that may contain spaces).
        halves = line.split(' :', 1)
        args = halves[0].split(' ') # The space-separated part.
        if len(halves) == 2:
            args.append(halves[1]) # The final argument; could contain spaces.

        cmd = args[0]
        args = args[1:]

        self.handleCommand(cmd, args)

    def handleCommand(self, cmd, args):
        """Handle a parsed command.

        This function takes care of converting arguments to their appropriate
        types and then calls the function handler. If a command is unknown,
        it is dispatched to illegalCommand.
        """
        function = getattr(self, 'cmd_' + cmd, None)

        if function is None or cmd not in self.commands:
            return

        types = self.commands[cmd]

        if len(types) != len(args):
            converted = False
        else:
            converted = True # Unless the below loop has a conversion problem.
            for i,t in enumerate(types):
                try:
                    args[i] = t(args[i])
                except (ValueError, TypeError):
                    converted = False
                    break

        if converted:
            function(*args)
        else:
            self.illegalCommand(cmd)

    def illegalCommand(self, cmd):
        pass # To be overridden by superclasses...

class MMPClientProtocol(MMPProtocolBase, ClientBase):
    """The actual connection to an MMP server. Probably not a good idea to use
    this directly, use MMPClient instead.
    """

    # A suitable default, but the server really should set this itself.
    target = ('\xff'*28) + ('\x00'*4)
    time = 0

    metaSent = False

    commands = {
        'MSG':      (str,),
        'TARGET':   (str,),
        'WORK':     (str, int),
        'BLOCK':    (int,),
        'ACCEPTED': (str,),
        'REJECTED': (str,),
        'TIME':     (int,),
    }

    def connectionMade(self):
        self.factory.connection = self
        self.runCallback('connect')
        self.sendLine('LOGIN %s :%s' % (self.factory.username,
                                        self.factory.password))
        # Got meta?
        for var,value in self.factory.meta.items():
            self.sendMeta(var, value)
        self.metaSent = True

    def connectionLost(self, reason):
        self.runCallback('disconnect')
        self.factory.connection = None
        self.factory._purgeDeferreds()

    def sendMeta(self, var, value):
        # Don't include ':' when sending a meta int, as per the protocol spec.
        colon = '' if isinstance(value, int) else ':'
        self.sendLine('META %s %s%s' % (var, colon, value))

    def cmd_MSG(self, message):
        self.runCallback('msg', message)

    def cmd_TARGET(self, target):
        try:
            t = target.decode('hex')
        except (ValueError, TypeError):
            return
        if len(t) == 32:
            self.target = t

    def cmd_TIME(self, time):
        self.time = time

    def cmd_WORK(self, work, mask):
        try:
            data = work.decode('hex')
        except (ValueError, TypeError):
            return
        if len(data) != 80:
            return
        aw = AssignedWork()
        aw.data = data
        aw.mask = mask
        aw.target = self.target
        aw.setMaxTimeIncrement(self.time)
        aw.identifier = data[4:36]
        self.runCallback('work', aw)
        # Since the server is giving work, we know it has accepted our
        # login details, so we can reset the factory's reconnect delay.
        self.factory.resetDelay()

    def cmd_BLOCK(self, block):
        self.runCallback('block', block)

    def cmd_ACCEPTED(self, data):
        self.factory._resultReturned(data, True)
    def cmd_REJECTED(self, data):
        self.factory._resultReturned(data, False)

class MMPClient(ReconnectingClientFactory, ClientBase):
    """This class implements an outbound connection to an MMP server.

    It's a factory so that it can automatically reconnect when the connection
    is lost.
    """

    protocol = MMPClientProtocol
    maxDelay = 60
    initialDelay = 0.2

    username = None
    password = None
    meta = {'version': 'MMPClient v1.0 by CFSworks'}

    deferreds = {}
    connection = None

    def __init__(self, handler, host, port, username, password):
        self.handler = handler
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def buildProtocol(self, addr):
        p = self.protocol()
        p.factory = self
        p.handler = self.handler
        return p

    def clientConnectionFailed(self, connector, reason):
        self.runCallback('failure')

        return ReconnectingClientFactory.clientConnectionFailed(
            self, connector, reason)

    def connect(self):
        """Tells the MMPClient to connect if it hasn't already."""

        reactor.connectTCP(self.host, self.port, self)

    def disconnect(self):
        """Tells the MMPClient to disconnect or stop connecting.
        The MMPClient shouldn't be used again.
        """

        self._deactivateCallbacks()

        if self.connection is not None:
            self.connection.transport.loseConnection()

        self.stopTrying()

    def requestWork(self):
        """If connected, ask the server for more work. The request is not sent
        if the client isn't connected, since the server will provide work upon
        next login anyway.
        """
        if self.connection is not None:
            self.connection.sendLine('MORE')

    def setMeta(self, var, value):
        """Set a metavariable, which gets sent to the server on-connect (or
        immediately, if already connected.)
        """
        self.meta[var] = value
        if self.connection and self.connection.metaSent:
            self.connection.sendMeta(var, value)

    def setVersion(self, shortname, longname=None, version=None, author=None):
        """Tells the protocol the application's version."""

        vstr = longname if longname is not None else shortname

        if version is not None:
            if not version.startswith('v') and not version.startswith('r'):
                version = 'v' + version
            vstr += ' ' + version

        if author is not None:
            vstr += ' by ' + author

        self.setMeta('version', vstr)

    def sendResult(self, result):
        """Submit a work result to the server. Returns a deferred which
        provides a True/False depending on whether or not the server
        accepetd the work.
        """
        if self.connection is None:
            return defer.succeed(False)

        d = defer.Deferred()

        if result in self.deferreds:
            self.deferreds[result].chainDeferred(d)
        else:
            self.deferreds[result] = d

        self.connection.sendLine('RESULT ' + result.encode('hex'))
        return d

    def _purgeDeferreds(self):
        for d in self.deferreds.values():
            d.callback(False)
        self.deferreds = {}

    def _resultReturned(self, data, accepted):
        try:
            data = data.decode('hex')
        except (TypeError, ValueError):
            return

        if data in self.deferreds:
            self.deferreds[data].callback(accepted)
            del self.deferreds[data]
########NEW FILE########
__FILENAME__ = RPCProtocol
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import urlparse
import json
import sys
import httplib
import socket
from twisted.internet import defer, reactor, error, threads
from twisted.python import failure

from ClientBase import ClientBase, AssignedWork

class ServerMessage(Exception): pass

class HTTPBase(object):
    connection = None
    timeout = None
    __lock = None
    __response = None

    def __makeResponse(self, *args, **kwargs):
        # This function exists as a workaround: If the connection is closed,
        # we also want to kill the response to allow the socket to die, but
        # httplib doesn't keep the response hanging around at all, so we need
        # to intercept its creation (hence this function) and store it.
        self.__response = httplib.HTTPResponse(*args, **kwargs)
        return self.__response

    def doRequest(self, *args):
        if self.__lock is None:
            self.__lock = defer.DeferredLock()
        return self.__lock.run(threads.deferToThread, self._doRequest, *args)

    def closeConnection(self):
        if self.connection is not None:
            if self.connection.sock is not None:
                self.connection.sock._sock.shutdown(socket.SHUT_RDWR)
            try:
                self.connection.close()
            except (AttributeError):
                #This is to fix "'NoneType' object has no attribute 'close'"
                #Theoretically this shouldn't be possible as we specifically
                #verify that self.connection isn't NoneType before trying to
                #call close(). I would add a debug message here, but HTTPBase
                #isn't passed a reference to the miner. The stack trace causing
                #this problem originates from the errback on line 138 (ask())
                #Most likely some sort of threading problem (race condition)
                pass

        if self.__response is not None:
            try:
                self.__response.close()
            except (AttributeError):
                #This was added for the same reason as the above
                pass
        self.connection = None
        self.__response = None

    def _doRequest(self, url, *args):
        if self.connection is None:
            connectionClass = (httplib.HTTPSConnection
                               if url.scheme.lower() == 'https' else
                               httplib.HTTPConnection)
            self.connection = connectionClass(url.hostname,
                                              url.port,
                                              timeout=self.timeout)
            # Intercept the creation of the response class (see above)
            self.connection.response_class = self.__makeResponse
            self.connection.connect()
            self.connection.sock.setsockopt(socket.SOL_TCP,
                                            socket.TCP_NODELAY, 1)
            self.connection.sock.setsockopt(socket.SOL_SOCKET,
                                            socket.SO_KEEPALIVE, 1)
        try:
            self.connection.request(*args)
            response = self.connection.getresponse()
            headers = response.getheaders()
            data = response.read()
            return dict(headers), data
        except (httplib.HTTPException, socket.error):
            self.closeConnection()
            raise

class RPCPoller(HTTPBase):
    """Polls the root's chosen bitcoind or pool RPC server for work."""

    timeout = 5

    def __init__(self, root):
        self.root = root
        self.askInterval = None
        self.askCall = None
        self.currentAsk = None

    def setInterval(self, interval):
        """Change the interval at which to poll the getwork() function."""
        self.askInterval = interval
        self._startCall()

    def _startCall(self):
        self._stopCall()
        if self.root.disconnected:
            return
        if self.askInterval:
            self.askCall = reactor.callLater(self.askInterval, self.ask)
        else:
            self.askCall = None

    def _stopCall(self):
        if self.askCall:
            try:
                self.askCall.cancel()
            except (error.AlreadyCancelled, error.AlreadyCalled):
                pass
            self.askCall = None

    def ask(self):
        """Run a getwork request immediately."""

        if self.currentAsk and not self.currentAsk.called:
             return
        self._stopCall()

        self.currentAsk = self.call('getwork')

        def errback(failure):
            try:
                if failure.check(ServerMessage):
                    self.root.runCallback('msg', failure.getErrorMessage())
                self.root._failure()
            finally:
                self._startCall()

        self.currentAsk.addErrback(errback)

        def callback(x):
            try:
                try:
                    (headers, result) = x
                except TypeError:
                    return
                self.root.handleWork(result, headers)
                self.root.handleHeaders(headers)
            finally:
                self._startCall()
        self.currentAsk.addCallback(callback)

    @defer.inlineCallbacks
    def call(self, method, params=[]):
        """Call the specified remote function."""

        body = json.dumps({'method': method, 'params': params, 'id': 1})
        path = self.root.url.path or '/'
        if self.root.url.query:
            path += '?' + self.root.url.query
        response = yield self.doRequest(
            self.root.url,
            'POST',
            path,
            body,
            {
                'Authorization': self.root.auth,
                'User-Agent': self.root.version,
                'Content-Type': 'application/json',
                'X-Work-Identifier': '1',
                'X-Mining-Extensions': self.root.EXTENSIONS
            })

        (headers, data) = response
        result = self.parse(data)
        defer.returnValue((headers, result))

    @classmethod
    def parse(cls, data):
        """Attempt to load JSON-RPC data."""

        response = json.loads(data)
        try:
            message = response['error']['message']
        except (KeyError, TypeError):
            pass
        else:
            raise ServerMessage(message)

        return response.get('result')

class LongPoller(HTTPBase):
    """Polls a long poll URL, reporting any parsed work results to the
    callback function.
    """

    # 10 minutes should be a sane value for this.
    timeout = 600

    def __init__(self, url, root):
        self.url = url
        self.root = root
        self.polling = False

    def start(self):
        """Begin requesting data from the LP server, if we aren't already..."""
        if self.polling:
            return
        self.polling = True
        self._request()

    def _request(self):
        if self.polling:
            path = self.url.path or '/'
            if self.url.query:
                path += '?' + self.url.query
            d = self.doRequest(
                self.url,
                'GET',
                path,
                None,
                {
                    'Authorization': self.root.auth,
                    'User-Agent': self.root.version,
                    'X-Work-Identifier': '1',
                    'X-Mining-Extensions': self.root.EXTENSIONS
                })
            d.addBoth(self._requestComplete)

    def stop(self):
        """Stop polling. This LongPoller probably shouldn't be reused."""
        self.polling = False
        self.closeConnection()

    def _requestComplete(self, response):
        try:
            if not self.polling:
                return

            if isinstance(response, failure.Failure):
                return

            try:
                (headers, data) = response
            except TypeError:
                #handle case where response doesn't contain valid data
                self.root.runCallback('debug', 'TypeError in LP response:')
                self.root.runCallback('debug', str(response))
                return

            try:
                result = RPCPoller.parse(data)
            except ValueError:
                return
            except ServerMessage:
                exctype, value = sys.exc_info()[:2]
                self.root.runCallback('msg', str(value))
                return

        finally:
            self._request()

        self.root.handleWork(result, headers, True)

class RPCClient(ClientBase):
    """The actual root of the whole RPC client system."""

    EXTENSIONS = ' '.join([
        'midstate',
        'submitold',
        'rollntime'
    ])

    def __init__(self, handler, url):
        self.handler = handler
        self.url = url
        self.params = {}
        for param in url.params.split('&'):
            s = param.split('=',1)
            if len(s) == 2:
                self.params[s[0]] = s[1]
        self.auth = 'Basic ' + ('%s:%s' % (
            url.username, url.password)).encode('base64').strip()
        self.version = 'RPCClient/2.0'

        self.poller = RPCPoller(self)
        self.longPoller = None # Gets created later...
        self.disconnected = False
        self.saidConnected = False
        self.submitold = False
        self.block = None
        self.setupMaxtime()

    def connect(self):
        """Begin communicating with the server..."""

        self.poller.ask()

    def disconnect(self):
        """Cease server communications immediately. The client is probably not
        reusable, so it's probably best not to try.
        """

        self._deactivateCallbacks()
        self.disconnected = True
        self.poller.setInterval(None)
        self.poller.closeConnection()
        if self.longPoller:
            self.longPoller.stop()
            self.longPoller = None

    def setupMaxtime(self):
        try:
            self.maxtime = int(self.params['maxtime'])
            if self.maxtime < 0:
                self.maxtime = 0
            elif self.maxtime > 3600:
                self.maxtime = 3600
        except (KeyError, ValueError):
            self.maxtime = 60

    def setMeta(self, var, value):
        """RPC clients do not support meta. Ignore."""

    def setVersion(self, shortname, longname=None, version=None, author=None):
        if version is not None:
            self.version = '%s/%s' % (shortname, version)
        else:
            self.version = shortname

    def requestWork(self):
        """Application needs work right now. Ask immediately."""
        self.poller.ask()

    def sendResult(self, result):
        """Sends a result to the server, returning a Deferred that fires with
        a bool to indicate whether or not the work was accepted.
        """

        # Must be a 128-byte response, but the last 48 are typically ignored.
        result += '\x00'*48

        d = self.poller.call('getwork', [result.encode('hex')])

        def errback(*ignored):
            return False # ANY error while turning in work is a Bad Thing(TM).

        #we need to return the result, not the headers
        def callback(x):
            try:
                (headers, accepted) = x
            except TypeError:
                self.runCallback('debug',
                        'TypeError in RPC sendResult callback:')
                self.runCallback('debug', str(x))
                return False

            if (not accepted):
                self.handleRejectReason(headers)

            return accepted

        d.addCallback(callback)
        d.addErrback(errback)
        return d

    #if the server sends a reason for reject then print that
    def handleRejectReason(self, headers):
        reason = headers.get('x-reject-reason')
        if reason is not None:
            self.runCallback('debug', 'Reject reason: ' + str(reason))

    def useAskrate(self, variable):
        defaults = {'askrate': 10, 'retryrate': 15, 'lpaskrate': 0}
        try:
            askrate = int(self.params[variable])
        except (KeyError, ValueError):
            askrate = defaults.get(variable, 10)
        self.poller.setInterval(askrate)

    def handleWork(self, work, headers, pushed=False):
        if work is None:
            return;

        rollntime = headers.get('x-roll-ntime')

        submitold = work.get('submitold')
        if submitold is not None:
            self.submitold = bool(submitold)

        if rollntime:
            if rollntime.lower().startswith('expire='):
                try:
                    maxtime = int(rollntime[7:])
                except:
                    #if the server supports rollntime but doesn't format the
                    #request properly, then use a sensible default
                    maxtime = self.maxtime
            else:
                if rollntime.lower() in ('t', 'true', 'on', '1', 'y', 'yes'):
                    maxtime = self.maxtime
                elif rollntime.lower() in ('f', 'false', 'off', '0', 'n', 'no'):
                    maxtime = 0
                else:
                    try:
                        maxtime = int(rollntime)
                    except:
                        maxtime = self.maxtime
        else:
            maxtime = 0

        if self.maxtime < maxtime:
            maxtime = self.maxtime

        if not self.saidConnected:
            self.saidConnected = True
            self.runCallback('connect')
            self.useAskrate('askrate')

        aw = AssignedWork()
        aw.data = work['data'].decode('hex')[:80]
        aw.target = work['target'].decode('hex')
        aw.mask = work.get('mask', 32)
        aw.setMaxTimeIncrement(maxtime)
        aw.identifier = work.get('identifier', aw.data[4:36])
        if pushed:
            self.runCallback('push', aw)
        self.runCallback('work', aw)

    def handleHeaders(self, headers):
        try:
            block = int(headers['x-blocknum'])
        except (KeyError, ValueError):
            pass
        else:
            if self.block != block:
                self.block = block
                self.runCallback('block', block)
        try:
            longpoll = headers.get('x-long-polling')
        except:
            longpoll = None

        if longpoll:
            lpParsed = urlparse.urlparse(longpoll)
            lpURL = urlparse.ParseResult(
                lpParsed.scheme or self.url.scheme,
                lpParsed.netloc or self.url.netloc,
                lpParsed.path, lpParsed.query, '', '')
            if self.longPoller and self.longPoller.url != lpURL:
                self.longPoller.stop()
                self.longPoller = None
            if not self.longPoller:
                self.longPoller = LongPoller(lpURL, self)
                self.longPoller.start()
                self.useAskrate('lpaskrate')
                self.runCallback('longpoll', True)
        elif self.longPoller:
            self.longPoller.stop()
            self.longPoller = None
            self.useAskrate('askrate')
            self.runCallback('longpoll', False)

    def _failure(self):
        if self.saidConnected:
            self.saidConnected = False
            self.runCallback('disconnect')
        else:
            self.runCallback('failure')
        self.useAskrate('retryrate')
        if self.longPoller:
            self.longPoller.stop()
            self.longPoller = None
            self.runCallback('longpoll', False)

########NEW FILE########
__FILENAME__ = KernelInterface
# Copyright (C) 2011-2012 by jedi95 <jedi95@gmail.com> and
#                            CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sys
import os
import traceback
import time
from struct import pack, unpack
from hashlib import sha256
from twisted.internet import defer, reactor
from weakref import WeakKeyDictionary

from phoenix2.core.PhoenixLogger import *

# I'm using this as a sentinel value to indicate that an option has no default;
# it must be specified.
REQUIRED = object()

class KernelOption(object):
    """This works like a property, and is used in defining easy option tables
    for kernels.
    """

    def __init__(self, name, type, help=None, default=REQUIRED,
        advanced=False, **kwargs):
        self.localValues = WeakKeyDictionary()
        self.name = name
        self.type = type
        self.help = help
        self.default = default
        self.advanced = advanced

    def __get__(self, instance, owner):
        if instance in self.localValues:
            return self.localValues[instance]
        else:
            return instance.interface._getOption(
                self.name, self.type, self.default)

    def __set__(self, instance, value):
        self.localValues[instance] = value

class KernelInterface(object):
    """This is an object passed to kernels as an API back to the Phoenix
    framework.
    """

    def __init__(self, deviceID, core, options):
        self.deviceID = deviceID
        self.core = core
        self.options = options
        self.meta = {}
        self._fatal = False
        self.rateCounters = {}
        self.results = 0
        self.accepted = 0
        self.rejected = 0
        self.started = time.time()

    def getDeviceID(self):
        """Kernels should query this first, to get the device identifier."""
        return self.deviceID

    def getName(self):
        """Gets the configured name for this kernel."""
        return self.options.get('name', self.deviceID)

    def _getOption(self, name, optType, default):
        """KernelOption uses this to read the actual value of the option."""
        name = name.lower()
        if not name in self.options:
            if default == REQUIRED:
                self.fatal('Required option %s not provided!' % name)
            else:
                return default

        givenOption = self.options[name]
        if optType == bool:
            if type(givenOption) == bool:
                return givenOption
            # The following are considered true
            return givenOption is None or \
                givenOption.lower() in ('t', 'true', 'on', '1', 'y', 'yes')

        try:
            return optType(givenOption)
        except (TypeError, ValueError):
            self.fatal('Option %s expects a value of type %s!' %
                       (name, type.__name__))

    def getVersion(self):
        """Return the Phoenix core version, as a 4-tuple, so that kernels can
        require a minimum version before operating (such as if they rely on a
        certain feature added in a certain version)
        """

        return self.core.VER

    def setMeta(self, var, value):
        """Set metadata for this kernel."""

        self.meta[var] = value
        # TODO: Change this to distinguish between multiple kernels.
        self.core.setMeta(var, value)

    def getRate(self):
        """Get the total rate of this kernel, in khps"""

        total = 0
        for rc in self.rateCounters.values():
            if rc:
                total += sum(rc)/len(rc)
        return total

    def updateRate(self, rate, index=None):
        rc = self.rateCounters.setdefault(index, [])
        rc.append(rate)

        # Now limit to the sliding window:
        samples = self.core.config.get('general', 'ratesamples', int, 10)
        self.rateCounters[index] = rc[-samples:]

        self.core._recalculateTotalRate()

    def fetchRange(self, size=None):
        """Fetch a range from the WorkQueue, optionally specifying a size
        (in nonces) to include in the range.
        """

        if size is None:
            return self.core.queue.fetchRange()
        else:
            return self.core.queue.fetchRange(size)

    def fetchUnit(self):
        """Fetch a raw WorkUnit directly from the WorkQueue."""
        return self.core.queue.fetchUnit()

    def checkTarget(self, hash, target):
        """Utility function that the kernel can use to see if a nonce meets a
        target before sending it back to the core.
        Since the target is checked before submission anyway, this is mostly
        intended to be used in hardware sanity-checks.
        """

        # This for loop compares the bytes of the target and hash in reverse
        # order, because both are 256-bit little endian.
        for t,h in zip(target[::-1], hash[::-1]):
            if ord(t) > ord(h):
                return True
            elif ord(t) < ord(h):
                return False
        return True

    def calculateHash(self, wu, nonce, timestamp = None):
        """Given a NonceRange/WorkUnit and a nonce, calculate the SHA-256
        hash of the solution. The resulting hash is returned as a string, which
        may be compared with the target as a 256-bit little endian unsigned
        integer.
        """

        #If timestamp is not specified then use the one in the WorkUnit
        if timestamp is None:
            timestamp = wu.timestamp

        staticDataUnpacked = list(unpack('>' + 'I'*19, wu.data[:76]))
        staticDataUnpacked[-2] = timestamp
        staticData = pack('<' + 'I'*19, *staticDataUnpacked)
        hashInput = pack('>76sI', staticData, nonce)
        return sha256(sha256(hashInput).digest()).digest()

    def foundNonce(self, wu, nonce, timestamp = None):
        """Called by kernels when they may have found a nonce."""

        self.results += 1

        #If timestamp is not specified then use the one in the WorkUnit
        if timestamp is None:
            timestamp = wu.timestamp

        # Check if the hash meets the full difficulty before sending.
        hash = self.calculateHash(wu, nonce, timestamp)

        # Check if the block has changed while this NonceRange was being
        # processed by the kernel. If so, don't send it to the server.
        if wu.isStale and not getattr(self.core.connection,
                                      'submitold', False):
            return False

        if self.checkTarget(hash, wu.target):
            formattedResult = pack('>68sI4s', wu.data[:68], timestamp,
                                    wu.data[72:76]) + pack('<I', nonce)
            d = self.core.connection.sendResult(formattedResult)
            def callback(accepted):
                self.core.logger.dispatch(ResultLog(self, hash, accepted))
                if accepted:
                    self.accepted += 1
                else:
                    self.rejected += 1
            d.addCallback(callback)
            return True
        else:
            self.core.logger.debug("Result didn't meet full "
                                   "difficulty, not sending")
            return False

    def debugException(self):
        """Call this from an except: block to drop the exception out to the
        logger as verbose messages.
        """

        exc = sys.exc_info()[1]

        msg = 'Exception: '
        for filename, ln, func, txt in traceback.extract_tb(sys.exc_info()[2]):
            filename = os.path.split(filename)[1]
            msg += '%s:%d, ' % (filename, ln)
        msg += '%s: %s' % (exc.__class__.__name__, exc)
        self.debug(msg)

    def debug(self, msg):
        """Log information as debug so that it can be viewed only when -v is
        enabled.
        """
        self.core.logger.dispatch(DebugLog(msg, self))

    def log(self, msg):
        """Log some general kernel information to the console."""
        self.core.logger.dispatch(PhoenixLog(msg, self))

    def error(self, msg=None):
        """The kernel has an issue that requires user attention."""
        self.core.logger.dispatch(KernelErrorLog(self, msg))

    def fatal(self, msg=None):
        """The kernel has an issue that is preventing it from continuing to
        operate.
        """
        self.core.logger.dispatch(KernelFatalLog(self, msg))
        self._fatal = True

        self.core.stopKernel(self.deviceID)

########NEW FILE########
__FILENAME__ = PhoenixConfig
# Copyright (C) 2012 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

class PhoenixConfig(object):
    PRESENT = object() # Special identifier to indicate a value is present
                       # but has no overridden value.

    def __init__(self, filename):
        self.filename = filename
        self.text = ''
        self.sections = {}
        self.sectionlist = [] # An in-order list
        self.load()

    def load(self):
        self.setraw(open(self.filename, 'r').read())

    def setraw(self, text):
        self.text = text
        self.sections = self._parse(self.text)

    def save(self):
        try:
            open(self.filename, 'w').write(self.text)
        except IOError:
            pass # Read-only filesystem?

    def set(self, section, var, value):
        section = section.lower().replace('#','').strip()
        var = var.lower().replace('#','').strip()
        if value is not None:
            value = str(value).replace('#','').strip()
            self.sections.setdefault(section, {})[var] = value
        else:
            if section not in self.sections:
                return # Don't create an empty section just to delete a var.
            section_dict = self.sections[section]
            if var not in section_dict:
                return # Don't bother deleting an already-missing var.
            del section_dict[var]
        self._alter(section, var, value)
        if section not in self.sectionlist:
            self.sectionlist.append(section)
        assert self._parse(self.text) == self.sections
        assert set(self.sectionlist) == set(self.sections.keys())

    def get(self, section, var, type, default=None):
        section = section.lower(); var = var.lower();
        value = self.sections.get(section, {}).get(var, None)
        if value is None:
            return default
        else:
            if type == bool:
                return (value == self.PRESENT or
                        value.lower() in ('t', 'true', 'on', '1', 'y', 'yes'))
            elif value == self.PRESENT:
                return default
            else:
                return type(value)

    def listsections(self):
        return self.sectionlist

    def getsection(self, section):
        return self.sections.get(section, {})

    @classmethod
    def _3strip(cls, text):
        # Performs a 3-way strip on the text, returning a tuple:
        # (left, stripped, right)
        # Where left/right contain the whitespace removed from the text.
        # N.B. this considers comments to be whitespace and will thus be
        # included in "right"
        s = text.split('#',1)
        ls = s[0].lstrip()
        left = s[0][:-len(ls)]
        stripped = ls.rstrip()
        right = ls[len(stripped):]
        if len(s) == 2:
            right += '#' + s[1]
        return (left, stripped, right)

    @classmethod
    def _parseLine(cls, line):
        _, line, _ = cls._3strip(line)
        if not line:
            return None, None

        if line == '[' + line[1:-1] + ']':
            return None, line[1:-1].lower()

        linesplit = line.split('=', 1)

        if len(linesplit) == 2:
            value = linesplit[1].strip()
        else:
            value = None

        return linesplit[0].strip().lower(), value

    def _parse(self, text):
        sections = {}
        section = None
        self.sectionlist = []

        for line in text.splitlines():
            var, value = self._parseLine(line)

            if var is None and value is None:
                pass
            elif var is None:
                section = sections.setdefault(value, {})
                self.sectionlist.append(value)
            else:
                if value is None:
                    value = self.PRESENT
                if section is not None:
                    section.setdefault(var, value) # First is greatest priority

        return sections

    def _alter(self, section, var, value):
        thisSection = None
        i = 0
        lastLineEnd = 0
        for line in self.text.splitlines(True):
            linevar, linevalue = self._parseLine(line)

            if linevar is None and linevalue is None:
                pass # Ignore blank lines entirely.
            elif linevar is None:
                if thisSection == section:
                    # Instead of leaving the section, insert the line:
                    self.text = (self.text[:lastLineEnd]
                                 + ('%s = %s\n' % (var, value))
                                 + self.text[lastLineEnd:])
                    return
                else:
                    thisSection = linevalue
                    lastLineEnd = i+len(line)
            elif linevar == var and thisSection == section:
                if value is None:
                    self.text = self.text[:i] + self.text[i+len(line):]
                    return
                # Carefully split to preserve whitespace and comment...
                left, stripped, right = self._3strip(line)
                split = stripped.split('=',1)
                if len(split) == 2:
                    ws, _, _ = self._3strip(split[1])
                    split[1] = ws + value
                else:
                    split[0] += ' = ' + value
                stripped = '='.join(split)
                self.text = (self.text[:i]
                             + left + stripped + right
                             + self.text[i+len(line):])
                return
            else:
                lastLineEnd = i+len(line)

            i += len(line)

        # Fell out of the loop without making a modification to a variable!
        if thisSection == section:
            # Already in the correct section, just add variable.
            if not self.text.endswith('\n'):
                self.text += '\n'
            self.text += '%s = %s\n' % (var, value)
        else:
            # Section isn't in the file... Just add it to the bottom.
            self.text += '\n[%s]\n%s = %s\n' % (section, var, value)

########NEW FILE########
__FILENAME__ = PhoenixCore
# Copyright (C) 2012 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sys
import imp
import os
import platform
import time
from weakref import WeakKeyDictionary

from twisted.internet import reactor, task, defer

from .. import backend
from ..backend.MMPProtocol import MMPClient

from .WorkQueue import WorkQueue
from .PhoenixLogger import *
from .KernelInterface import KernelInterface
from .PhoenixConfig import PhoenixConfig
from .PhoenixRPC import PhoenixRPC
from .PluginInterface import PluginInterface

class PhoenixCore(object):
    """The root-level object of a Phoenix mining instance."""

    # This must be manually set for Git
    VER = (2, 0, 0)
    VERSION = 'v%s.%s.%s' % VER

    def __init__(self, cfgFilename='phoenix.cfg'):
        self.kernelTypes = {}
        self.connection = None
        self.connectionURL = None
        self.connected = False
        self.connectionType = 'none'
        self.failbackLoop = None

        if not hasattr(sys, 'frozen'):
            self.basedir = os.path.dirname(os.path.dirname(__file__))
        else:
            self.basedir = os.path.dirname(sys.executable)

        self.config = PhoenixConfig(cfgFilename)
        self.logger = PhoenixLogger(self)
        self.queue = WorkQueue(self)
        self.rpc = PhoenixRPC(self)

        self.pluginModules = {}

        self.pluginIntf = PluginInterface(self)
        self.plugins = {}

        self.kernels = {}
        self.interfaces = WeakKeyDictionary()
        self.deviceIDs = []
        self.deviceAutoconfig = {}

        self.idle = True
        self.lastMetaRate = 0
        self.lastRate = 0

        self.startTime = time.time()

        self._analysisMemo = {}

    def start(self):
        self._meta = {}

        self.logger.log('Welcome to Phoenix ' + self.VERSION)
        self.startTime = time.time()

        self.discoverPlugins()
        self.startAllKernels()
        self.startAutodetect()

        self.setMeta('os', '%s %s' % (platform.system(), platform.version()))

        self.configChanged()
        self.switchURL(self.config.get('general', 'backend', str))

        reactor.addSystemEventTrigger('before', 'shutdown', self._shutdown)

    def configChanged(self):
        self.rpc.start() # In case the ip/port changed...

    def _shutdown(self):
        self.stopAutodetect()
        self.switchURL(None)
        for kernel in self.kernels.values():
            if kernel is not None:
                kernel.stop()
        self.kernels = {}

    def loadPlugin(self, name, silent=False):
        if name in self.pluginModules:
            return

        plugindir = os.path.join(self.basedir, 'plugins')

        def importPlugin(name):
            self.loadPlugin(name, silent=True)
            if name not in self.pluginModules:
                raise ImportError('Dependency on a plugin that failed to load')
            else:
                # Inject it into the caller's namespace rather than return it.
                callerNamespace = sys._getframe().f_back.f_locals
                callerNamespace[name] = self.pluginModules[name]

        import __builtin__
        __builtin__.importPlugin = importPlugin

        try:
            file, filename, smt = imp.find_module(name, [plugindir])
            plugin = imp.load_module(name, file, filename, smt)
            self.pluginModules[name] = plugin
            if hasattr(plugin, 'PhoenixKernel'):
                self.kernelTypes[name] = plugin.PhoenixKernel
            else:
                self.plugins[name] = plugin.PhoenixPlugin(self.pluginIntf)
        except (ImportError, AttributeError):
            if not silent:
                self.logger.log('Failed to load plugin "%s"' % name)

    def discoverPlugins(self):
        plugindir = os.path.join(self.basedir, 'plugins')
        for name in os.listdir(plugindir):
            if name.endswith('.pyo') or name.endswith('.pyc'):
                if os.path.isfile(os.path.join(plugindir, name[:-1])):
                    continue
            name = name.split('.',1)[0] # Strip off . and anything after...
            self.loadPlugin(name)

    def startAutodetect(self):
        # NOTICE: It is legal to call this function more than once. If this
        # happens, kernels are expected to re-report the devices.
        for kernel in self.kernelTypes.values():
            if hasattr(kernel, 'autodetect'):
                kernel.autodetect(self._autodetectCallback)

    def stopAutodetect(self):
        for kernel in self.kernelTypes.values():
            if hasattr(kernel, 'stopAutodetect'):
                kernel.stopAutodetect()

    def redetect(self, terminate=False):
        if terminate:
            for devid in self.kernels.keys():
                devidset = None
                for idset in self.deviceIDs:
                    if devid in idset:
                        devidset = idset
                        break

                assert devidset is not None

                if not self.checkRules(devidset):
                    self.stopKernel(devid)
                    del self.kernels[devid] # Totally forget about it.
                    self.deviceIDs.remove(devidset)

        self.startAutodetect()

    def checkRules(self, ids):
        types = [x.split(':',1)[0] for x in ids]

        rules = self.config.get('general', 'autodetect', str, '')
        rules = rules.lower().replace(',', ' ').split()

        use = False
        for rule in rules:
            if rule.lstrip('-+') in types:
                use = not rule.startswith('-')

        return use

    def _autodetectCallback(self, device):
        device = device.lower()

        for idset in self.deviceIDs:
            if device in idset:
                if idset[0] in self.kernels:
                    return

        kernel, ranking, autoconfiguration, ids = self._analyzeDevice(device)

        if self.checkRules(ids):
            if self.startKernel(ids[0]):
                name = autoconfiguration.get('name', device)
                kernelName = [x for x,y in self.kernelTypes.items() if y ==
                              kernel][0]
                self.logger.debug('Detected [%s]: [%s] using %s (rating %s)' %
                                  (device, name, kernelName, ranking))

    def _analyzeDevice(self, device):
        if device in self._analysisMemo:
            return self._analysisMemo[device]

        ids = set()

        bestKernel = None
        bestRanking = 0
        bestConfig = None
        bestKernelID = device

        toAnalyze = [device]
        while toAnalyze:
            analyzing = toAnalyze.pop(0)
            assert analyzing not in ids
            ids.add(analyzing)

            for kernel in self.kernelTypes.values():
                if not hasattr(kernel, 'analyzeDevice'):
                    continue

                ranking, configuration, names = kernel.analyzeDevice(analyzing)

                if ranking > bestRanking:
                    bestRanking = ranking
                    bestKernel = kernel
                    if names:
                        bestKernelID = names[0]
                    else:
                        bestKernelID = analyzing
                    bestConfig = configuration

                for name in names:
                    if name not in ids and name not in toAnalyze:
                        toAnalyze.append(name)

        # We need to make sure the preferred ID comes first, so...
        ids.remove(bestKernelID)
        ids = [bestKernelID] + list(ids)

        self._analysisMemo[device] = (bestKernel, bestRanking, bestConfig, ids)

        return bestKernel, bestRanking, bestConfig, ids

    def switchURL(self, url):
        """Connects the Phoenix miner to a new URL immediately.

        Issue None to disconnect.
        """

        if self.connectionURL == url:
            return

        if self.connection is not None:
            self.connection.disconnect()
            self.connection = None
            self.onDisconnect() # Make sure the disconnect log goes through...

        self.connectionURL = url

        if self.failbackLoop:
            self.failbackLoop.stop()
            self.failbackLoop = None

        if not url:
            return

        self.connection = backend.openURL(url, self)

        if isinstance(self.connection, MMPClient):
            self.connectionType = 'mmp'
        else:
            self.connectionType = 'rpc'
        self.logger.refreshStatus()

        self.connection.setVersion('phoenix', 'Phoenix Miner', self.VERSION)
        for var, value in self._meta.iteritems():
            self.connection.setMeta(var, value)

        self.connection.connect()

    def getKernelConfig(self, devid):
        kernel = self.kernels.get(devid)
        if kernel:
            return self.interfaces[kernel].options

        options = {}
        for key, value in self.config.getsection(devid).items():
            options[key.lower()] = value

        # Autoconfiguration is enabled for devices that aren't in the config
        # file, and disabled (by default) for devices that are.
        inConfig = devid in self.config.listsections()
        if self.config.get(devid, 'autoconfigure', bool, not inConfig):
            autoconfig = dict(self.deviceAutoconfig.get(devid, {}))
            autoconfig.update(options)
            return autoconfig
        else:
            return options

    def startAllKernels(self):
        for section in self.config.listsections():
            if ':' in section: # It's a device if it contains a :
                if self.config.get(section, 'start_undetected', bool, True):
                    self.startKernel(section)

    def startKernel(self, device):
        """Start a brand-new kernel on 'device', passing an optional
        dictionary of kernel parameters.

        The newly-created kernel is returned.
        """

        device = device.lower()

        if self.config.get(device, 'disabled', bool, False):
            return

        kernelType, _, autoconfiguration, ids = self._analyzeDevice(device)

        for idset in self.deviceIDs:
            for devid in ids:
                if devid in idset:
                    if self.kernels.get(idset[0]) is not None:
                        return

        kernelOption = self.config.get(device, 'kernel', str, None)
        if kernelOption:
            kernelType = self.kernelTypes.get(kernelOption)
            if hasattr(kernelType, 'analyzeDevice'):
                _, autoconfiguration, _ = kernelType.analyzeDevice(device)
            else:
                autoconfiguration = {}

        if not kernelType:
            interface = KernelInterface(device, self,
                                        self.getKernelConfig(device))
            self.logger.dispatch(KernelFatalLog(interface,
                                                'No kernel; disabled.'))
            return

        self.deviceAutoconfig[device] = autoconfiguration

        interface = KernelInterface(device, self, self.getKernelConfig(device))
        kernel = kernelType(interface)
        interface.kernel = kernel

        if interface._fatal:
            # The kernel had a fatal error in initialization...
            return None

        self.kernels[device] = kernel
        self.interfaces[kernel] = interface

        ids.remove(device)
        ids.insert(0, device) # Canonical device MUST be first.
        for idset in self.deviceIDs:
            if device in idset:
                break
        else:
            self.deviceIDs.append(ids)

        kernel.start()

        if not interface._fatal:
            return kernel

    def stopKernel(self, device):
        """Stop an already-running kernel."""
        if device not in self.kernels or self.kernels[device] is None:
            return

        self.kernels[device].stop()
        self.kernels[device] = None

        self._recalculateTotalRate()

    def setMeta(self, var, value):
        self._meta[var] = value
        if self.connection is not None:
            self.connection.setMeta(var, value)

    def requestWork(self):
        if self.connection is not None:
            self.connection.requestWork()

    def _recalculateTotalRate(self):
        # Query all mining cores for their Khash/sec rate and sum.

        self.lastRate = 0
        if not self.idle:
            for kernel in self.kernels.values():
                if kernel is not None:
                    self.lastRate += self.interfaces[kernel].getRate()

        self.logger.dispatch(RateUpdateLog(self.lastRate))

        # Let's not spam the server with rate messages.
        if self.lastMetaRate+30 < time.time():
            self.setMeta('rate', self.lastRate)
            self.lastMetaRate = time.time()

    # Callback from WorkQueue
    def reportIdle(self, idle):
        if self.idle == idle:
            return
        self.idle = idle

        if self.idle:
            self.logger.log("Warning: work queue empty, miner is idle")
            self.logger.dispatch(RateUpdateLog(0))
            self.setMeta('rate', 0)

    @defer.inlineCallbacks
    def attemptFailback(self):
        backendURL = self.config.get('general', 'backend', str, '')
        ok = yield backend.testURL(backendURL)
        if not self.failbackLoop:
            return
        if ok:
            self.logger.log('Primary backend is available, switching back...')
            self.switchURL(backendURL)

    # Connection callback handlers
    def onFailure(self):
        backups = self.config.get('general', 'backups', str, '').split()
        backups.insert(0, self.config.get('general', 'backend', str, ''))
        try:
            index = backups.index(self.connectionURL)
        except ValueError:
            index = -1
        nextIndex = (index+1)%len(backups)
        nextBackend = backups[nextIndex]
        if nextBackend == self.connectionURL:
            self.logger.log("Couldn't connect to server, retrying...")
        else:
            self.logger.log("Couldn't connect to server, switching backend...")
            self.switchURL(nextBackend)
            if nextIndex != 0:
                assert not self.failbackLoop
                failbackInterval = self.config.get('general', 'failback',
                                                   int, 600)
                if failbackInterval:
                    self.failbackLoop = task.LoopingCall(self.attemptFailback)
                    self.failbackLoop.start(failbackInterval)

    def onConnect(self):
        if not self.connected:
            self.logger.dispatch(ConnectionLog(True, self.connectionURL))
            self.connected = True
            self.logger.refreshStatus()
    def onDisconnect(self):
        if self.connected:
            self.logger.dispatch(ConnectionLog(False, self.connectionURL))
            self.connected = False
            self.logger.refreshStatus()
    def onBlock(self, block):
        self.logger.dispatch(BlockChangeLog(block))
    def onMsg(self, msg):
        self.logger.log('MSG: ' + str(msg))
    def onWork(self, work):
        self.logger.debug('Server gave new work; passing to WorkQueue')
        self.queue.storeWork(work)
    def onLongpoll(self, lp):
        self.connectionType = 'rpclp' if lp else 'rpc'
        self.logger.refreshStatus()
    def onPush(self, ignored):
        self.logger.dispatch(LongPollPushLog())
    def onLog(self, message):
        self.logger.log(message)
    def onDebug(self, message):
        self.logger.debug(message)

########NEW FILE########
__FILENAME__ = PhoenixLogger
# Copyright (C) 2012 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sys
import time
import atexit

from twisted.internet import reactor

class PhoenixLog(object):
    """Base class for all manner of logs that may occur."""

    TYPE = 'general'

    def __init__(self, msg, kernelif=None):
        self._setup(kernelif)
        self.msg = msg

    def _setup(self, kernelif=None):
        self.time = time.time()
        self.kernelif = kernelif
        self.msg = ''

    # --- INTENDED TO BE OVERRIDDEN BY SUBCLASSES ---
    def toConsole(self, logger): return True
    def toFile(self, logger): return True
    def toRPC(self, logger): return True
    def getMsg(self, verbose): return self.msg
    def getType(self): return self.TYPE
    def getDetails(self): return {}
    # -----------------------------------------------

    def formatRPC(self, logger):
        if self.kernelif:
            devid = self.kernelif.getDeviceID()
        else:
            devid = None

        return {'id': devid, 'timestamp': int(self.time),
                'msg': self.getMsg(logger.isVerbose()),
                'type': self.getType(), 'details': self.getDetails()}

    def formatConsole(self, logger, fullDate=False):
        """Format this log for appearance in the console."""

        timeformat = '%m/%d/%Y %H:%M:%S' if fullDate else '%H:%M:%S'

        output = '[%s] ' % time.strftime(timeformat, time.localtime(self.time))
        if self.kernelif:
            output += '[%s] ' % self.kernelif.getName()

        output += self.getMsg(logger.isVerbose())

        return output

    def formatFile(self, logger):
        return self.formatConsole(logger, True)

# --- VARIOUS LOGS ---

class DebugLog(PhoenixLog):
    TYPE = 'debug'
    def toConsole(self, logger): return logger.isVerbose()

class RateUpdateLog(PhoenixLog):
    TYPE = 'rate'

    def __init__(self, rate):
        self._setup()
        self.rate = rate

    def toConsole(self, logger): return False
    def toFile(self, logger): return False
    def toRPC(self, logger): return False

class LongPollPushLog(PhoenixLog):
    TYPE = 'lppush'

    def __init__(self):
        self._setup()
        self.msg = 'LP: New work pushed'

class BlockChangeLog(PhoenixLog):
    TYPE = 'block'

    def __init__(self, block):
        self._setup()
        self.block = block

    def getMsg(self, verbose):
        return 'Currently on block: %s' % self.block

    def getDetails(self): return {'block': self.block}

class ResultLog(PhoenixLog):
    TYPE = 'result'

    def __init__(self, kernelif, hash, accepted):
        self._setup(kernelif)
        self.hash = hash
        self.accepted = accepted

    def getMsg(self, verbose):
        status = ('ACCEPTED' if self.accepted else 'REJECTED')
        if verbose:
            hash = self.hash[:23:-1].encode('hex') + '...'
        else:
            hash = self.hash[27:23:-1].encode('hex')
        return 'Result %s %s' % (hash, status)

    def getDetails(self):
        return {'hash': self.hash[::-1].encode('hex'),
                'accepted': self.accepted}

class ConnectionLog(PhoenixLog):
    TYPE = 'connection'

    def __init__(self, connected, url):
        self._setup()
        self.connected = connected
        self.url = url

    def getMsg(self, verbose):
        if self.connected:
            return 'Connected to server'
        else:
            return 'Disconnected from server'

    def getDetails(self): return {'connected': self.connected, 'url': self.url}

class KernelErrorLog(PhoenixLog):
    TYPE = 'error'

    def __init__(self, kernelif, error):
        self._setup(kernelif)
        self.error = error

    def toConsole(self, logger): return bool(self.error)
    def toFile(self, logger): return bool(self.error)

    def getMsg(self, verbose):
        if self.error:
            return 'Error: ' + self.error

    def getDetails(self): return {'error': self.error}

class KernelFatalLog(KernelErrorLog):
    TYPE = 'fatal'
    def getMsg(self, verbose):
        if self.error:
            return 'Fatal error: ' + self.error

# --------------------

class ConsoleOutput(object):
    def __init__(self):
        self._status = ''
        atexit.register(self._exit)

    def _exit(self):
        self._status += '  ' # In case the shell added a ^C
        self.status('')

    def status(self, status):
        update = '\r'
        update += status
        update += ' ' * (len(self._status) - len(status))
        update += '\b' * (len(self._status) - len(status))
        sys.stderr.write(update)
        self._status = status

    def printline(self, line):
        update = '\r'
        update += line + ' ' * (len(self._status) - len(line)) + '\n'
        update += self._status
        sys.stderr.write(update)

class PhoenixLogger(object):
    def __init__(self, core):
        self.console = ConsoleOutput()
        self.core = core
        self.rateText = '0 Khash/s'

        self.accepted = 0
        self.rejected = 0

        self.consoleDay = None

        self.logfile = None
        self.logfileName = None

        self.rpcLogs = []
        self.rpcIndex = 0

        self.nextRefresh = 0
        self.refreshScheduled = False
        self.refreshStatus()

    def isVerbose(self):
        return self.core.config.get('general', 'verbose', bool, False)

    def log(self, msg):
        self.dispatch(PhoenixLog(msg))

    def debug(self, msg):
        self.dispatch(DebugLog(msg))

    def writeToFile(self, text):
        logfileName = self.core.config.get('general', 'logfile', str, None)
        if logfileName != self.logfileName:
            self.logfileName = logfileName
            if self.logfile:
                self.logfile.close()
                self.logfile = None
            if logfileName:
                self.logfile = open(logfileName, 'a')

        if self.logfile:
            self.logfile.write(text + '\n')
            self.logfile.flush()

    def addToRPC(self, log):
        self.rpcLogs.append(log)
        rpcLimit = self.core.config.get('web', 'logbuffer', int, 1000)
        if len(self.rpcLogs) > rpcLimit:
            prune = len(self.rpcLogs) - rpcLimit
            self.rpcIndex += prune
            self.rpcLogs = self.rpcLogs[prune:]

    def dispatch(self, log):
        if log.toConsole(self):
            day = time.localtime(log.time)[:3]
            self.console.printline(log.formatConsole(self, day !=
                                                     self.consoleDay))
            self.consoleDay = day
        if log.toFile(self):
            self.writeToFile(log.formatFile(self))
        if log.toRPC(self):
            self.addToRPC(log)

        if isinstance(log, ResultLog):
            if log.accepted:
                self.accepted += 1
            else:
                self.rejected += 1
            self.refreshStatus()
        elif isinstance(log, RateUpdateLog):
            self.rateText = self.formatNumber(log.rate) + 'hash/s'
            self.refreshStatus()

    def refreshStatus(self):
        now = time.time()
        if now < self.nextRefresh:
            if not self.refreshScheduled:
                reactor.callLater(self.nextRefresh - now,
                                  self.refreshStatus)
            self.refreshScheduled = True
            return

        self.refreshScheduled = False
        self.nextRefresh = time.time() + self.core.config.get('general',
                                                              'statusinterval',
                                                              float, 1.0)

        if self.core.connected:
            connectionType = {'mmp': 'MMP', 'rpc': 'RPC',
                              'rpclp': 'RPC (+LP)'
                             }.get(self.core.connectionType, 'OTHER')
        else:
            connectionType = 'DISCONNECTED'
        self.console.status('[%s] [%s Accepted] [%s Rejected] [%s]' %
                            (self.rateText, self.accepted,
                             self.rejected, connectionType))

    @classmethod
    def formatNumber(cls, n):
        """Format a positive integer in a more readable fashion."""
        if n < 0:
            raise ValueError('can only format positive integers')
        prefixes = 'KMGTP'
        whole = str(int(n))
        decimal = ''
        i = 0
        while len(whole) > 3:
            if i + 1 < len(prefixes):
                decimal = '.%s' % whole[-3:-1]
                whole = whole[:-3]
                i += 1
            else:
                break
        return '%s%s %s' % (whole, decimal, prefixes[i])

########NEW FILE########
__FILENAME__ = PhoenixRPC
# Copyright (C) 2012 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sys
import time
import os
import json

from twisted.internet import reactor, defer, error
from twisted.web import server, script
from twisted.web.resource import Resource
from twisted.web.static import File

def rpcError(code, msg):
    return '{"result": null, "error": {"code": %d, "message": "%s"}, ' \
            '"id": null, "jsonrpc": "2.0"}' % (code, msg)

class PhoenixRPC(Resource):
    def __init__(self, core):
        Resource.__init__(self)
        self.core = core

        self.listen = None

        self.port = None
        self.ip = None

    def start(self):
        """Read configuration and start hosting the webserver."""
        disabled = self.core.config.get('web', 'disabled', bool, False)
        port = self.core.config.get('web', 'port', int, 7780)
        ip = self.core.config.get('web', 'bind', str, '')

        if not disabled and port != self.port or ip != self.ip:
            self.port = port
            self.ip = ip
            if self.listen:
                self.listen.stopListening()
            try:
                self.listen = reactor.listenTCP(port, server.Site(self),
                                                interface=ip)
            except error.CannotListenError:
                self.listen = None

    def getChild(self, name, request):
        versionString = 'phoenix/%s' % self.core.VERSION
        request.setHeader('Server', versionString)
        if request.method == 'POST' and request.path == '/':
            return self
        else:
            docroot = os.path.join(self.core.basedir, 'www')
            root = File(self.core.config.get('web', 'root', str, docroot))
            root.processors = {'.rpy': script.ResourceScript}
            return root.getChild(name, request)

    def render_POST(self, request):
        request.setHeader('Content-Type', 'application/json')

        passwordGood = (request.getPassword() ==
                        self.core.config.get('web', 'password', str,
                                             'phoenix'))

        # This is a workaround for WebKit bug #32916, Mozilla bug #282547,
        # et al... Don't send the WWW-Authenticate header for present, but
        # invalid, credentials.
        if not request.getHeader('Authorization') or passwordGood:
            request.setHeader('WWW-Authenticate', 'Basic realm="Phoenix RPC"')

        if not passwordGood:
            request.setResponseCode(401)
            return rpcError(-1, 'Password invalid.')

        try:
            data = json.loads(request.content.read())
            id = data['id']
            method = str(data['method'])
            if 'params' in data:
                params = tuple(data['params'])
            else:
                params = ()
        except ValueError:
            return rpcError(-32700, 'Parse error.')
        except (KeyError, TypeError):
            return rpcError(-32600, 'Invalid request.')

        func = getattr(self.core.pluginIntf, method, None)
        if func is None or getattr(func, 'rpc_forbidden', False):
            return rpcError(-32601, 'Method not found.')

        d = defer.maybeDeferred(func, *params)

        def callback(result):
            jsonResult = json.dumps({'result': result, 'error': None,
                                     'id': id, "jsonrpc": "2.0"})
            request.write(jsonResult)
            request.finish()
        d.addCallback(callback)

        def errback(failure):
            if failure.trap(TypeError, ValueError):
                request.write(rpcError(-1, 'Invalid arguments.'))
                request.finish()
        d.addErrback(errback)

        return server.NOT_DONE_YET

########NEW FILE########
__FILENAME__ = PluginInterface
# Copyright (C) 2012 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import time

from twisted.internet import reactor

def norpc(func):
    """This is a quick decorator to mark a function as FORBIDDEN to the RPC
    server. It's intended for useful plugin functions that could pose security
    risks if inadvertently exposed over the network.
    """

    func.rpc_forbidden = True
    return func

class PluginInterface(object):
    """All of the functions that do not start with a _ are acceptable to use in
    third-party plugins.
    """
    @norpc
    def __init__(self, core):
        self.core = core

    def getstatus(self):
        return {'uptime': int(time.time() - self.core.startTime),
                'connection': {'type': self.core.connectionType,
                               'connected': self.core.connected,
                               'url': self.core.connectionURL},
                'results': {'accepted': self.core.logger.accepted,
                            'rejected': self.core.logger.rejected}}

    def getrawconfig(self):
        return self.core.config.text

    def setrawconfig(self, text):
        text = str(text)
        self.core.config.setraw(text)
        self.core.config.save()
        self.core.configChanged()

    @norpc
    def _checkSection(self, section):
        if ':' in section and section not in self.core.config.listsections():
            # Make sure autoconfiguration is preserved.
            self.core.config.set(section, 'autoconfigure', True)
            self.core.config.set(section, 'start_undetected',
                                 False)

    def getconfig(self, section, var):
        section = str(section)
        var = str(var)
        return self.core.config.get(section, var, str, None)

    def setconfig(self, section, var, value):
        section = str(section)
        var = str(var)
        # value doesn't get converted to str - set does that (unless it's None)
        self._checkSection(section)
        self.core.config.set(section, var, value)
        self.core.config.save()
        self.core.configChanged()

    def redetect(self, terminate=False):
        self.core.redetect(terminate)

    def switchto(self, backend=None):
        if backend is None:
            backend = self.core.config.get('general', 'backend', str)
        else:
            backend = str(backend)
        self.core.switchURL(backend)

    @norpc
    def _getminers(self):
        miners = [section for section in self.core.config.listsections()
                  if ':' in section]
        miners.extend([miner for miner in self.core.kernels
                       if miner is not None and miner not in miners])
        return miners

    def listdevices(self):
        devices = []
        for miner in self._getminers():
            device = {'id': miner}

            config = self.core.getKernelConfig(miner)

            if self.core.kernels.get(miner) is not None:
                kernel = self.core.kernels[miner]
                interface = self.core.interfaces[kernel]

                device['status'] = 'running'
                device['name'] = interface.getName()
                device['rate'] = interface.getRate()
                device['config'] = config
                device['meta'] = interface.meta
                device['uptime'] = int(time.time() - interface.started)
                device['results'] = interface.results
                device['accepted'] = interface.accepted
                device['rejected'] = interface.rejected
            else:
                disabled = self.core.config.get(miner, 'disabled', bool, False)

                device['status'] = ('disabled' if disabled else 'suspended')
                device['name'] = config.get('name', miner)
                device['rate'] = 0
                device['config'] = config
                for key, value in self.core.config.getsection(miner).items():
                    device['config'][key.lower()] = value
                device['meta'] = {}
                device['uptime'] = 0
                device['results'] = 0
                device['accepted'] = 0
                device['rejected'] = 0

            devices.append(device)

        return devices

    def getlogs(self, skip, limit=0):
        skip = int(skip)
        limit = int(limit)

        total = len(self.core.logger.rpcLogs) + self.core.logger.rpcIndex
        if skip < 0:
            skip %= total

        buf = [{'id': None, 'timestamp': None, 'msg': None, 'type': 'purged',
                'details': {}}] * (self.core.logger.rpcIndex - skip)
        skip = max(0, skip - self.core.logger.rpcIndex)

        if limit == 0:
            limit = None

        return (buf + [log.formatRPC(self.core.logger) for log in
                       self.core.logger.rpcLogs[skip:]])[:limit]

    @norpc
    def _manage(self, minerID, action):
        # Just a quick helper function to be used for the next 4...
        if minerID is not None:
            minerID = str(minerID)

        saveConfig = False
        managed = False
        for miner in self._getminers():
            running = self.core.kernels.get(miner) is not None
            disabled = self.core.config.get(miner, 'disabled', bool, False)
            if minerID is None or miner == minerID.lower():
                if action == 'suspend':
                    if running:
                        self.core.stopKernel(miner)
                        managed = True
                elif action == 'restart':
                    if running:
                        self.core.stopKernel(miner)
                        self.core.startKernel(miner)
                        managed = True
                elif action == 'disable':
                    if running:
                        self.core.stopKernel(miner)
                    if not disabled:
                        self._checkSection(miner)
                        self.core.config.set(miner, 'disabled', True)
                        saveConfig = True
                        managed = True
                elif action == 'start':
                    if disabled:
                        continue # Can't use start(null) for disabled.
                    if self.core.startKernel(miner):
                        managed = True

        if saveConfig:
            self.core.config.save()
        return managed

    def restart(self, minerID=None):
        return self._manage(minerID, 'restart')

    def suspend(self, minerID=None):
        return self._manage(minerID, 'suspend')

    def disable(self, minerID):
        return self._manage(minerID, 'disable')

    def start(self, minerID=None):
        if minerID is None:
            return self._manage(None, 'start')
        else:
            self.core.config.set(minerID, 'disabled', None)
            self.core.config.save()
            return self.core.startKernel(minerID) is not None

    def shutdown(self):
        reactor.callLater(0.01, reactor.stop)

########NEW FILE########
__FILENAME__ = WorkQueue
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import struct

from collections import deque
from time import time
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.defer import DeferredLock
from ..util.Midstate import calculateMidstate

"""A WorkUnit is a single unit containing up to 2^32 nonces. A single getWork
request returns a WorkUnit.
"""
class WorkUnit(object):

    def __init__(self, aw):
        self.data = aw.data
        self.target = aw.target
        self.identifier = aw.identifier
        self.maxtime = aw.maxtime
        try:
            self.nonces = 2 ** aw.mask
        except AttributeError:
            self.nonces = aw.nonces
        self.base = 0
        self.midstate = calculateMidstate(self.data[:64])
        self.isStale = False
        self.time = aw.time
        self.downloaded = time()
        self.callbacks = set()

    def set_timestamp(self, timestamp):
        self.data = (self.data[:68] + struct.pack('>I', timestamp) +
                     self.data[72:])
    def get_timestamp(self):
        return struct.unpack('>I', self.data[68:72])[0]
    timestamp = property(get_timestamp, set_timestamp)

    def addStaleCallback(self, callback):
        if self.isStale:
            callback(self)
        else:
            self.callbacks.add(callback)

    def removeStaleCallback(self, callback):
        self.callbacks.remove(callback)

    def stale(self):
        if self.isStale:
            return
        self.isStale = True
        for cb in list(self.callbacks):
            cb(self)

"""A NonceRange is a range of nonces from a WorkUnit, to be dispatched in a
single execution of a mining kernel. The size of the NonceRange can be
adjusted to tune the performance of the kernel.

This class doesn't actually do anything, it's just a well-defined container
that kernels can pull information out of.
"""
class NonceRange(object):

    def __init__(self, unit, base, size):
        self.unit = unit # The WorkUnit this NonceRange comes from.
        self.base = base # The base nonce.
        self.size = size # How many nonces this NonceRange says to test.

class WorkQueue(object):
    """A WorkQueue contains WorkUnits and dispatches NonceRanges when requested
    by the miner. WorkQueues dispatch deffereds when they runs out of nonces.
    """

    def __init__(self, core):

        self.core = core
        self.logger = core.logger
        self.queueSize = core.config.get('general', 'queuesize', int, 1)
        self.queueDelay = core.config.get('general', 'queuedelay', int, 5)

        self.lock = DeferredLock()
        self.queue = deque('', self.queueSize)
        self.deferredQueue = deque()
        self.currentUnit = None
        self.lastBlock = None
        self.block = ''

        self.staleCallbacks = []

    def storeWork(self, aw):

        #check if this work matches the previous block
        if (self.lastBlock is not None) and (aw.identifier == self.lastBlock):
            self.logger.debug('Server gave work from the previous '
                              'block, ignoring.')
            #if the queue is too short request more work
            if self.checkQueue():
                if self.core.connection:
                    self.core.connection.requestWork()
            return

        #create a WorkUnit
        work = WorkUnit(aw)
        reactor.callLater(max(60, aw.time - 1) - self.queueDelay,
                            self.checkWork)
        reactor.callLater(max(60, aw.time - 1), self.workExpire, work)

        #check if there is a new block, if so reset queue
        newBlock = (aw.identifier != self.block)
        if newBlock:
            self.queue.clear()
            self.currentUnit = None
            self.lastBlock = self.block
            self.block = aw.identifier
            self.logger.debug("New block (WorkQueue)")

        #add new WorkUnit to queue
        if work.data and work.target and work.midstate and work.nonces:
            self.queue.append(work)

        #if the queue is too short request more work
        workRequested = False
        if self.checkQueue():
            if self.core.connection:
                self.core.connection.requestWork()
                workRequested = True

        #if there is a new block notify kernels that their work is now stale
        if newBlock:
            for callback in self.staleCallbacks:
                callback()
            self.staleCallbacks = []
        self.staleCallbacks.append(work.stale)

        #check if there are deferred WorkUnit requests pending
        #since requests to fetch a WorkUnit can add additional deferreds to
        #the queue, cache the size beforehand to avoid infinite loops.
        for i in range(len(self.deferredQueue)):
            df = self.deferredQueue.popleft()
            d = self.fetchUnit(workRequested)
            d.chainDeferred(df)

        #clear the idle flag since we just added work to queue
        self.core.reportIdle(False)

    def checkWork(self):
        # Called 5 seconds before any work expires in order to fetch more
        if self.checkQueue():
            if self.core.connection:
                self.core.requestWork()

    def checkQueue(self, added = False):

        # This function checks the queue length including the current unit
        size = 1

        # Check if the current unit will last long enough
        if self.currentUnit is None:
            if len(self.queue) == 0:
                return True
            else:
                size = 0
                if added:
                    rolls = self.queue[0].maxtime - self.queue[0].timestamp
                    # If new work can't be rolled, and queue would be too small
                    if rolls == 0 and (len(self.queue) - 1) < self.queueSize:
                        return True

        else:
            remaining = self.currentUnit.maxtime - self.currentUnit.timestamp
            # Check if we are about to run out of rolltime on current unit
            if remaining < (self.queueDelay):
                size = 0

            # Check if the current unit is about to expire
            age = self.currentUnit.downloaded + self.currentUnit.time
            lifetime = age - time()
            if lifetime < (2 * self.queueDelay):
                size = 0

        # Check if the queue will last long enough
        queueLength = 0
        for i in range(len(self.queue)):
            age = self.queue[0].downloaded + max(60, self.queue[0].time - 1)
            lifetime = age - time()
            if lifetime > (2 * self.queueDelay):
                queueLength += 1

        # Return True/False indicating if more work should be fetched
        return size + queueLength < self.queueSize

    def workExpire(self, wu):
        # Don't expire WorkUnits if idle and queue empty
        if (self.core.idle) and (len(self.queue) <= 1):
            return

        # Remove the WorkUnit from queue
        if len(self.queue) > 0:
            iSize = len(self.queue)
            if not (len(self.queue) == 1 and (self.currentUnit is None)):
                try:
                    self.queue.remove(wu)
                except ValueError: pass
            if self.currentUnit == wu:
                self.currentUnit = None

            # Check queue size
            if self.checkQueue() and (iSize != len(self.queue)):
                if self.core.connection:
                    self.core.connection.requestWork()

            # Flag the WorkUnit as stale
            wu.stale()
        else:
            # Check back again later if we didn't expire the work
            reactor.callLater(5, self.workExpire, wu)

    def getRangeFromUnit(self, size):

        #get remaining nonces
        noncesLeft = self.currentUnit.nonces - self.currentUnit.base

        # Flag indicating if the WorkUnit was depeleted by this request
        depleted = False

        #if there are enough nonces to fill the full reqest
        if noncesLeft >= size:
            nr = NonceRange(self.currentUnit, self.currentUnit.base, size)

            #check if this uses up the rest of the WorkUnit
            if size >= noncesLeft:
                depleted = True
            else:
                self.currentUnit.base += size

        #otherwise send whatever is left
        else:
            nr = NonceRange(
                self.currentUnit, self.currentUnit.base, noncesLeft)
            depleted = True

        #return the range
        return nr, depleted

    def checkRollTime(self, wu):
    # This function checks if a WorkUnit could be time rolled
        if wu.maxtime > wu.timestamp and not wu.isStale:
            remaining = (wu.downloaded + wu.time) - time()
            if remaining > (self.queueDelay) or len(self.queue) < 1:
                # If it has been more than 5 minutes probably better to idle
                if time() - wu.downloaded < 300:
                    return True

        return False

    def rollTime(self, wu):

        # Check if this WorkUnit supports rolling time, return None if not
        if not self.checkRollTime(wu):
            return None

        # Create the new WU
        newWU = WorkUnit(wu)

        # Increment the timestamp
        newWU.timestamp += 1

        # Reset the download time to the original WU's
        newWU.downloaded = wu.downloaded

        # Set a stale callback for this WU
        self.staleCallbacks.append(newWU.stale)

        # Setup a workExpire callback
        remaining = max(self.queueDelay, (wu.downloaded + wu.time) - time())
        reactor.callLater(remaining - 1, self.workExpire, newWU)

        # Return the new WU
        return newWU

    def fetchUnit(self, delayed = False):
        #if there is a unit in queue
        if len(self.queue) >= 1:

            #check if the queue has fallen below the desired size
            if self.checkQueue(True) and (not delayed):
                #Request more work to maintain minimum queue size
                if self.core.connection:
                    self.core.connection.requestWork()

            #get the next unit from queue
            wu = self.queue.popleft()

            #return the unit
            return defer.succeed(wu)

        #if the queue is empty
        else:

            #request more work
            if self.core.connection:
                self.core.connection.requestWork()

            #report that the miner is idle
            self.core.reportIdle(True)

            #set up and return deferred
            df = defer.Deferred()
            self.deferredQueue.append(df)
            return df

    #make sure that only one fetchRange request runs at a time
    def fetchRange(self, size=0x10000):
        return self.lock.run(self._fetchRange, size)

    def _fetchRange(self, size):

        #make sure size is not too large
        size = min(size, 0x100000000)

        #check if the current unit exists
        if self.currentUnit is not None:

            # Get a nonce range
            nr, depleated = self.getRangeFromUnit(size)

            # If we depleted the Workunit then try to roll time
            if depleated:
                self.currentUnit = self.rollTime(self.currentUnit)

            # Return the range
            return defer.succeed(nr)

        #if there is no current unit
        else:

            # Check if we can get a new unit with rolltime
            def callback(wu):
                #get a new current unit
                self.currentUnit = wu

                #get a nonce range
                nr, depleated = self.getRangeFromUnit(size)

                # If we depleted the Workunit then try to roll time
                if depleated:
                    self.currentUnit = self.rollTime(self.currentUnit)

                #return the range
                return nr

            d = self.fetchUnit()
            d.addCallback(callback)
            return d

########NEW FILE########
__FILENAME__ = BFIPatcher
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import struct

# List of devices known to support BFI_INT patching
WHITELIST = [   'Antilles',
                'Barts',
                'BeaverCreek',
                'Caicos',
                'Cayman',
                'Cedar',
                'Cypress',
                'Devastator',
                'Hemlock',
                'Juniper',
                'Loveland',
                'Palm',
                'Redwood',
                'Scrapper',
                'Sumo',
                'Turks',
                'WinterPark',
                'Wrestler']

class PatchError(Exception): pass

class BFIPatcher(object):
    """Patches .ELF files compiled for VLIW4/VLIW5 GPUs; changes the microcode
    so that any BYTE_ALIGN_INT instructions become BFI_INT.
    """

    def __init__(self, interface):
        self.interface = interface

    def patch(self, data):
        """Run the process of patching an ELF."""

        self.interface.debug('Finding inner ELF...')
        innerPos = self.locateInner(data)
        self.interface.debug('Patching inner ELF...')
        inner = data[innerPos:]
        patched = self.patchInner(inner)
        self.interface.debug('Patch complete, returning to kernel...')
        return data[:innerPos] + patched

    def patchInner(self, data):
        sections = self.readELFSections(data)
        # We're looking for .text -- there should be two of them.
        textSections = filter(lambda x: x[0] == '.text', sections)
        if len(textSections) != 2:
            self.interface.debug('Inner ELF does not have 2 .text sections!')
            self.interface.debug('Sections are: %r' % sections)
            raise PatchError()
        name, offset, size = textSections[1]
        before, text2, after = (data[:offset], data[offset:offset+size],
            data[offset+size:])

        self.interface.debug('Patching instructions...')
        text2 = self.patchInstructions(text2)
        return before + text2 + after

    def patchInstructions(self, data):
        output = ''
        nPatched = 0
        for i in xrange(len(data)/8):
            inst, = struct.unpack('Q', data[i*8:i*8+8])
            # Is it BYTE_ALIGN_INT?
            if (inst&0x9003f00002001000) == 0x0001a00000000000:
                nPatched += 1
                inst ^=  (0x0001a00000000000 ^ 0x0000c00000000000) # BFI_INT
            output += struct.pack('Q', inst)
        self.interface.debug('BFI-patched %d instructions...' % nPatched)
        if nPatched < 60:
            self.interface.debug('Patch safety threshold not met!')
            raise PatchError()
        return output

    def locateInner(self, data):
        """ATI uses an ELF-in-an-ELF. I don't know why. This function's job is
        to find it.
        """

        pos = data.find('\x7fELF', 1)
        if pos == -1 or data.find('\x7fELF', pos+1) != -1: # More than 1 is bad
            self.interface.debug('Inner ELF not located!')
            raise PatchError()
        return pos

    def readELFSections(self, data):
        try:
            (ident1, ident2, type, machine, version, entry, phoff,
                shoff, flags, ehsize, phentsize, phnum, shentsize, shnum,
                shstrndx) = struct.unpack('QQHHIIIIIHHHHHH', data[:52])

            if ident1 != 0x64010101464c457f:
                self.interface.debug('Invalid ELF header!')
                raise PatchError()

            # No section header?
            if shoff == 0:
                return []

            # Find out which section contains the section header names
            shstr = data[shoff+shstrndx*shentsize:shoff+(shstrndx+1)*shentsize]
            (nameIdx, type, flags, addr, nameTableOffset, size, link, info,
                addralign, entsize) = struct.unpack('IIIIIIIIII', shstr)

            # Grab the section header.
            sh = data[shoff:shoff+shnum*shentsize]

            sections = []
            for i in xrange(shnum):
                rawEntry = sh[i*shentsize:(i+1)*shentsize]
                (nameIdx, type, flags, addr, offset, size, link, info,
                    addralign, entsize) = struct.unpack('IIIIIIIIII', rawEntry)
                nameOffset = nameTableOffset + nameIdx
                name = data[nameOffset:data.find('\x00', nameOffset)]
                sections.append((name, offset, size))

            return sections
        except struct.error:
            self.interface.debug('A struct.error occurred while reading ELF!')
            raise PatchError()
########NEW FILE########
__FILENAME__ = Midstate
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import struct

# Some SHA-256 constants...
K = [
     0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
     0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
     0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
     0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
     0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
     0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
     0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
     0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
     0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
     0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
     0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
    ]

A0 = 0x6a09e667
B0 = 0xbb67ae85
C0 = 0x3c6ef372
D0 = 0xa54ff53a
E0 = 0x510e527f
F0 = 0x9b05688c
G0 = 0x1f83d9ab
H0 = 0x5be0cd19

def rotateright(i,p):
    """i>>>p"""
    p &= 0x1F # p mod 32
    return i>>p | ((i<<(32-p)) & 0xFFFFFFFF)

def addu32(*i):
    return sum(list(i))&0xFFFFFFFF

def calculateMidstate(data, state=None, rounds=None):
    """Given a 512-bit (64-byte) block of (little-endian byteswapped) data,
    calculate a Bitcoin-style midstate. (That is, if SHA-256 were little-endian
    and only hashed the first block of input.)
    """
    if len(data) != 64:
        raise ValueError('data must be 64 bytes long')

    w = list(struct.unpack('<IIIIIIIIIIIIIIII', data))

    if state is not None:
        if len(state) != 32:
            raise ValueError('state must be 32 bytes long')
        a,b,c,d,e,f,g,h = struct.unpack('<IIIIIIII', state)
    else:
        a = A0
        b = B0
        c = C0
        d = D0
        e = E0
        f = F0
        g = G0
        h = H0

    consts = K if rounds is None else K[:rounds]
    for k in consts:
        s0 = rotateright(a,2) ^ rotateright(a,13) ^ rotateright(a,22)
        s1 = rotateright(e,6) ^ rotateright(e,11) ^ rotateright(e,25)
        ma = (a&b) ^ (a&c) ^ (b&c)
        ch = (e&f) ^ ((~e)&g)

        h = addu32(h,w[0],k,ch,s1)
        d = addu32(d,h)
        h = addu32(h,ma,s0)

        a,b,c,d,e,f,g,h = h,a,b,c,d,e,f,g

        s0 = rotateright(w[1],7) ^ rotateright(w[1],18) ^ (w[1] >> 3)
        s1 = rotateright(w[14],17) ^ rotateright(w[14],19) ^ (w[14] >> 10)
        w.append(addu32(w[0], s0, w[9], s1))
        w.pop(0)

    if rounds is None:
        a = addu32(a, A0)
        b = addu32(b, B0)
        c = addu32(c, C0)
        d = addu32(d, D0)
        e = addu32(e, E0)
        f = addu32(f, F0)
        g = addu32(g, G0)
        h = addu32(h, H0)

    return struct.pack('<IIIIIIII', a, b, c, d, e, f, g, h)
########NEW FILE########
__FILENAME__ = QueueReader
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from time import time
from Queue import Queue, Empty
from twisted.internet import reactor, defer

class QueueReader(object):
    """A QueueReader is a very efficient WorkQueue reader that keeps the next
    nonce range available at all times. The benefit is that threaded mining
    kernels waste no time getting the next range, since this class will have it
    completely requested and preprocessed for the next iteration.

    The QueueReader is iterable, so a dedicated mining thread needs only to do
    for ... in self.qr:
    """

    SAMPLES = 3

    def __init__(self, interface, preprocessor=None, workSizeCallback=None,
                 index=None):
        self.interface = interface
        self.preprocessor = preprocessor
        self.workSizeCallback = workSizeCallback
        self.index = index

        if self.preprocessor is not None:
            if not callable(self.preprocessor):
                raise TypeError('the given preprocessor must be callable')
        if self.workSizeCallback is not None:
            if not callable(self.workSizeCallback):
                raise TypeError('the given workSizeCallback must be callable')

        # This shuttles work to the dedicated thread.
        self.dataQueue = Queue()

        # Used in averaging the last execution times.
        self.executionTimeSamples = []
        self.averageExecutionTime = None

        # This gets changed by _updateWorkSize.
        self.executionSize = None

        # Statistics accessed by the dedicated thread.
        self.currentData = None
        self.startedAt = time()

    def start(self):
        """Called by the kernel when it's actually starting."""
        self._updateWorkSize(None, None)
        self._requestMore()

    def stop(self):
        """Called by the kernel when it's told to stop. This also brings down
        the loop running in the mining thread.
        """
        # Tell the other thread to exit cleanly.
        while not self.dataQueue.empty():
            try:
                self.dataQueue.get(False)
            except Empty:
                pass
        self.dataQueue.put(StopIteration())

    def _ranExecution(self, nr, dt):
        """An internal function called after an execution completes, with the
        time it took. Used to keep track of the time so kernels can use it to
        tune their execution times.
        """

        if dt > 0:
            self.interface.updateRate(int(nr.size/dt/1000), self.index)

        self.executionTimeSamples.append(dt)
        self.executionTimeSamples = self.executionTimeSamples[-self.SAMPLES:]

        if len(self.executionTimeSamples) == self.SAMPLES:
            averageExecutionTime = (sum(self.executionTimeSamples) /
                                    len(self.executionTimeSamples))

            self._updateWorkSize(averageExecutionTime, nr.size)

    def _updateWorkSize(self, time, size):
        """An internal function that tunes the executionSize to that specified
        by the workSizeCallback; which is in turn passed the average of the
        last execution times.
        """
        if self.workSizeCallback:
            self.executionSize = self.workSizeCallback(time, size)

    def _requestMore(self):
        """This is used to start the process of making a new item available in
        the dataQueue, so the dedicated thread doesn't have to block.
        """

        # This should only run if there's no ready-to-go work in the queue.
        if not self.dataQueue.empty():
            return

        if self.executionSize is None:
            d = self.interface.fetchRange()
        else:
            d = self.interface.fetchRange(self.executionSize)

        def preprocess(nr):
            nr.unit.addStaleCallback(self._staleCallback)

            # If preprocessing is not necessary, just tuplize right away.
            if not self.preprocessor:
                return (nr, nr)

            d2 = defer.maybeDeferred(self.preprocessor, nr)

            # Tuplize the preprocessed result.
            def callback(x):
                return (x, nr)
            d2.addCallback(callback)
            return d2
        d.addCallback(preprocess)

        d.addCallback(self.dataQueue.put_nowait)

    def _staleCallback(self, wu):
        """Called when a WorkUnit is rendered stale and no more work should be
        done on it.
        """

        notStale = []
        if not self.dataQueue.empty():
            # Out with the old...
            while not self.dataQueue.empty():
                try:
                    nr = self.dataQueue.get(False)
                    if nr[1].unit != wu:
                        notStale.append(nr)
                except Empty: continue
            # ...in with the new.
            if notStale:
                # Put all of the non-stale items back into the queue...
                for nr in notStale:
                    self.dataQueue.put_nowait(nr)
            else:
                # It's totally empty, ask the WorkQueue for more.
                self._requestMore()

    def __iter__(self):
        return self
    def next(self):
        """Since QueueReader is iterable, this is the function that runs the
        for-loop and dispatches work to the thread.
        This should be the only thread that executes outside of the Twisted
        main thread.
        """

        # If we just completed a range, we should tell the main thread.
        if self.currentData:
            # self.currentData[1] is the un-preprocessed NonceRange.
            now = time()
            dt = now - self.startedAt
            self.startedAt = now
            reactor.callFromThread(self._ranExecution, self.currentData[1], dt)

        # Block for more data from the main thread. In 99% of cases, though,
        # there should already be something here.
        # Note that this comes back with either a tuple, or a StopIteration()
        self.currentData = self.dataQueue.get(True)

        # Does the main thread want us to shut down, or pass some more data?
        if isinstance(self.currentData, StopIteration):
            raise self.currentData

        # We just took the only item in the queue. It needs to be restocked.
        reactor.callFromThread(self._requestMore)

        # currentData is actually a tuple, with item 0 intended for the kernel.
        return self.currentData[0]

########NEW FILE########
