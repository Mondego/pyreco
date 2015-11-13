__FILENAME__ = base
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     base.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import time
import random
import string
import json

# twisted specific imports
from twisted.internet.defer import Deferred


PASSES = 3

# Default
SIZES = [3, 10, 20, 42, 88, 183, 379, 784, 1623, 3359, 6951, 14384, 29763,
         61584, 127427, 263665, 545559, 1128837, 2335721, 4832930, 10000000]

# Amazon R2C
#SIZES = [3, 10, 20, 42, 88, 183, 379, 784, 1623, 3359,
#         6951, 7938, 9310, 11216, 13864, 17544, 22658, 29763,
#         61584, 127427, 263665, 545559, 1128837, 2335721, 4832930, 10000000]


def delay(response, delta, reactor):
    d = Deferred()
    reactor.callLater(delta, d.callback, response)
    return d


class TestBase(object):
    def __init__(self, conn, iTag, testType):
        self._conn = conn
        self._iTag = iTag
        self._testType = testType

        self._data = []

    def _activate(self):
        pass

    def _deactivate(self):
        pass

    def _run(self):
        raise NotImplementedError

    def run(self, _):
        self._deferred = Deferred()
        self._conn.reactor.callLater(1, self._activate)
        self._conn.reactor.callLater(2, self._run)
        return self._deferred

    def _done(self):
        self._deactivate()
        self._deferred.callback(None)

    def __str__(self):
        return json.dumps({'type' : self._testType, 'data' : self._data})


class RemoteTest(TestBase):
    def _activate(self):
        self._srv = self._conn.serviceClient(self._iTag, 'Test/StringTest',
                                             self._process)

    def _deactivate(self):
        self._srv = None

    def _run(self):
        self._srv.call({'testType' : self._testType})

    def _process(self, msg):
        self._data.append(msg['times'])
        self._conn.reactor.callLater(0, self._done)


class LocalTest(TestBase):
    def _activate(self):
        self._data.append([])
        self._str = None
        self._ready = False
        self._dropCnt = 0

    def _run(self):
        self._req()

    def _req(self):
        count = len(self._data[-1])

        if count >= len(SIZES):
            self._conn.reactor.callLater(0, self._done)
            return

        if SIZES[count] > 10:
            sample = ''.join(random.choice(string.lowercase)
                             for _ in xrange(10))
            rep = int(SIZES[count] / 10)
            tail = 'A' * (SIZES[count] % 10)

            self._str = sample * rep + tail
        else:
            self._str = ''.join(random.choice(string.lowercase)
                                for _ in xrange(SIZES[count]))

        self._time = time.time()
        self._sendReq()

    def _resp(self, data):
        stop = time.time()

        if not self._ready:
            if self._dropCnt > 3:
                self._data[-1] = [-1.0] * len(SIZES)
                self._conn.reactor.callLater(0, self._done)
                return

            if (not self._str
                or len(self._str) != len(data) or self._str[:10] != data[:10]):
                self._dropCnt += 1
                return

            self._ready = True

        if len(self._str) != len(data) or self._str[:10] != data[:10]:
            delta = -1
        else:
            delta = (stop - self._time) * 1000

        self._data[-1].append(delta)
        self._req()

    def _sendReq(self):
        raise NotImplementedError


class LocalServiceTest(LocalTest):
    def __init__(self, conn, iTag):
        super(LocalServiceTest, self).__init__(conn, iTag, 'service')

    def _activate(self):
        super(LocalServiceTest, self)._activate()

        self._srv = self._conn.serviceClient(self._iTag, 'Test/StringEcho',
                                             self._resp)

    def _deactivate(self):
        self._srv = None

    def _sendReq(self):
        self._srv.call({'data' : self._str})

    def _resp(self, resp):
        super(LocalServiceTest, self)._resp(resp['data'])


class LocalTopicTest(LocalTest):
    def __init__(self, conn, iTag):
        super(LocalTopicTest, self).__init__(conn, iTag, 'topic')

    def _activate(self):
        super(LocalTopicTest, self)._activate()

        self._pub = self._conn.publisher(self._iTag[0], 'std_msgs/String')
        self._sub = self._conn.subscriber(self._iTag[1], 'std_msgs/String',
                                          self._resp)

    def _deactivate(self):
        self._pub = None
        self._sub.unsubscribe()
        self._sub = None

    def _sendReq(self):
        self._pub.publish({'data' : self._str})

    def _resp(self, resp):
        super(LocalServiceTest, self)._resp(resp['data'])

########NEW FILE########
__FILENAME__ = c2c
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     c2c.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import json

# twisted specific imports
from twisted.internet.defer import Deferred

# rce specific imports
from rce.client.connection import Connection

# local imports
from base import PASSES, SIZES, delay, RemoteTest


class Measurement(object):
    TAG = 'tester'
    TYPES = ('service', 'topic')

    def __init__(self, runs, conn, robot, reactor):
        self._conn = conn
        self._robot = robot

        self._tests = [RemoteTest(conn, self.TAG, name) for name in self.TYPES]

        self._deferred = d = Deferred()

        d.addCallback(self._setup)
        d.addCallback(delay, 20, reactor)

        for _ in xrange(runs):
            for test in self._tests:
                d.addCallback(test.run)

        d.addCallback(self._postProcess)
        d.addCallback(delay, 2, reactor)

        def stop(_):
            reactor.stop()
            print('\ndone')

        d.addCallback(stop)

    def run(self, _):
        if not self._tests:
            print('No tests to run.')
            return

        if self._deferred.called:
            print('Can run the measurement only once.')

        self._deferred.callback(None)

    def _setup(self, _):
        print('Setup environments...')

        ### Add containers
        self._cTag = ('c1', 'c2')
        for cTag in self._cTag:
            self._conn.createContainer(cTag)

        ### Add the nodes
        self._conn.addNode(self._cTag[0], 'strTester', 'Test',
                           'stringTester.py')
        self._conn.addNode(self._cTag[1], 'strEcho', 'Test', 'stringEcho.py')

        ### Add interfaces and connections
        # Connections Robot - StringTester
        tag = self.TAG
        cls = 'Test/StringTest'
        self._conn.addInterface(self._cTag[0], tag, 'ServiceClientInterface',
                                cls, 'stringTest')
        self._conn.addInterface(self._robot, tag, 'ServiceProviderConverter',
                                cls)
        self._conn.addConnection('{0}/{1}'.format(self._cTag[0], tag),
                                 '{0}/{1}'.format(self._robot, tag))

        # Connections StringTester - StringEcho (service)
        tag = 'testEchoSrv'
        cls = 'Test/StringEcho'
        srv = 'stringEchoService'
        self._conn.addInterface(self._cTag[0], tag, 'ServiceProviderInterface',
                                cls, srv)
        self._conn.addInterface(self._cTag[1], tag, 'ServiceClientInterface',
                                cls, srv)
        self._conn.addConnection('{0}/{1}'.format(self._cTag[0], tag),
                                 '{0}/{1}'.format(self._cTag[1], tag))

        # Connections StringTester - StringEcho (topic)
        tag = 'testEchoReq'
        cls = 'std_msgs/String'
        tpc = 'stringEchoReq'
        self._conn.addInterface(self._cTag[0], tag, 'SubscriberInterface',
                                cls, tpc)
        self._conn.addInterface(self._cTag[1], tag, 'PublisherInterface',
                                cls, tpc)
        self._conn.addConnection('{0}/{1}'.format(self._cTag[0], tag),
                                 '{0}/{1}'.format(self._cTag[1], tag))

        tag = 'testEchoResp'
        cls = 'std_msgs/String'
        tpc = 'stringEchoResp'
        self._conn.addInterface(self._cTag[0], tag, 'PublisherInterface',
                                cls, tpc)
        self._conn.addInterface(self._cTag[1], tag, 'SubscriberInterface',
                                cls, tpc)
        self._conn.addConnection('{0}/{1}'.format(self._cTag[0], tag),
                                 '{0}/{1}'.format(self._cTag[1], tag))

    def _postProcess(self, _):
        with open('c2c.data', 'w') as f:
            f.write(json.dumps(SIZES))
            f.write('\n')

            for test in self._tests:
                f.write(str(test))
                f.write('\n')

        for cTag in self._cTag:
            self._conn.destroyContainer(cTag)


def _get_argparse():
    from argparse import ArgumentParser

    parser = ArgumentParser(prog='c2c',
                            description='Run communication measurement for RCE '
                                        'between two containers using '
                                        'a string message.')

    parser.add_argument('--passes', help='Number of passes to do.',
                        type=int, default=PASSES)
    parser.add_argument('ipMaster', help='IP address of master process.',
                        type=str)

    return parser


def main(reactor, passes, ip):
    user = 'testUser'
    robot = 'testRobot'
    connection = Connection(user, robot, user, reactor)
    measurement = Measurement(passes, connection, robot, reactor)

    print('Connect...')
    d = Deferred()
    d.addCallback(measurement.run)
    connection.connect('http://{0}:9000/'.format(ip), d)

    reactor.run()


if __name__ == '__main__':
    from twisted.internet import reactor

    args = _get_argparse().parse_args()

    main(reactor, args.passes, args.ipMaster)

########NEW FILE########
__FILENAME__ = plot
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     plot.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

import numpy
import pylab
import json


def main(fileNames, ylog, remote, plotStyle):
    if ylog:
        pylab.subplot(111, xscale='log', yscale='log')
    else:
        pylab.subplot(111, xscale='log')

    for fileName in fileNames:
        with open(fileName, 'r') as f:
            size = numpy.array(json.loads(f.readline())[1:])
            benchmark = map(json.loads, f.readlines())

        for test in benchmark:
            if not remote and test['label'].endswith('R-to-C'):
                continue

            rawData = test.pop('data')
            data = [d for d in rawData if -1.0 not in d]
            length = len(data)

            if length != len(rawData):
                print('Invalid measurement encountered in '
                      '{0}.'.format(test['label']))

            data = numpy.array(data)

            if length > 1:
                mean = numpy.mean(data, 0)[1:]
                var = numpy.var(data, 0)[1:]
                minVal = numpy.min(data, 0)[1:]
                maxVal = numpy.max(data, 0)[1:]
            elif length == 1:
                mean = numpy.array(data[0][1:])
                var = None
            else:
                print('No valid measurements for {0}.'.format(test['label']))
                continue

            if plotStyle == 'minmax':
                pylab.errorbar(size, mean, numpy.array([minVal, maxVal]),
                               **test)
            elif plotStyle == 'variance':
                pylab.errorbar(size, mean, var, **test)
            else:
                pylab.errorbar(size, mean, **test)

    if 'paper.data' in fileNames:
        pylab.figtext(0.8, 0.8, 'green: paper measurements', ha='right')

    pylab.xlabel('number of characters')
    pylab.ylabel('time [ms]')
    pylab.legend(loc='upper left')
    pylab.show()


def _get_argparse():
    from argparse import ArgumentParser

    parser = ArgumentParser(prog='benchmark',
                            description='Run communication benchmark using a '
                                        'string message for RCE.')

    parser.add_argument('--ylog', help='Flag to activate log scale for y axis.',
                        action='store_true')
    parser.add_argument('--show', help='Flag to activate the display the R-to-C'
                                       ' measurements.', action='store_true')
    parser.add_argument('--errorbar', help='Argument which is used to define '
                                           'the type of errorbar to display.',
                        type=str, choices=('minmax', 'variance'))
    parser.add_argument('--paper', help='Flag to add measurement from paper for'
                                        ' comparison.', action='store_true')

    return parser


if __name__ == '__main__':
    args = _get_argparse().parse_args()

    files = ['benchmark.data']

    if args.paper:
        files.append('paper.data')

    main(files, args.ylog, args.show, args.errorbar)

########NEW FILE########
__FILENAME__ = r2c
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     r2c.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import json

# twisted specific imports
from twisted.internet.defer import Deferred

# rce specific imports
from rce.client.connection import Connection

# local imports
from base import PASSES, SIZES, delay, LocalTopicTest, LocalServiceTest


class Measurement(object):
    TYPES = ((LocalServiceTest, 'test'),
             (LocalTopicTest, ('testReqTopic', 'testRespTopic')))

    def __init__(self, runs, conn, robot, reactor):
        self._conn = conn
        self._robot = robot

        self._tests = [cls(conn, iTag) for cls, iTag in self.TYPES]

        self._deferred = d = Deferred()

        d.addCallback(self._setup)
        d.addCallback(delay, 20, reactor)

        for _ in xrange(runs):
            for test in self._tests:
                d.addCallback(test.run)

        d.addCallback(self._postProcess)
        d.addCallback(delay, 2, reactor)

        def stop(_):
            reactor.stop()
            print('\ndone')

        d.addCallback(stop)

    def run(self, _):
        if not self._tests:
            print('No tests to run.')
            return

        if self._deferred.called:
            print('Can run the measurement only once.')

        self._deferred.callback(None)

    def _setup(self, _):
        print('Setup environment...')

        # Add containers
        self._cTag = 'c1'
        self._conn.createContainer(self._cTag)

        # Add the node
        self._conn.addNode(self._cTag, 'strEcho', 'Test', 'stringEcho.py')

        # Connections Robot - StringEcho (service)
        tag = self.TYPES[0][1]
        cls = 'Test/StringEcho'
        self._conn.addInterface(self._cTag, tag, 'ServiceClientInterface',
                                cls, 'stringEchoService')
        self._conn.addInterface(self._robot, tag, 'ServiceProviderConverter',
                                cls)
        self._conn.addConnection('{0}/{1}'.format(self._cTag, tag),
                                 '{0}/{1}'.format(self._robot, tag))

        # Connections Robot - StringEcho (topic)
        tag = self.TYPES[1][1][0]
        cls = 'std_msgs/String'
        self._conn.addInterface(self._cTag, tag, 'PublisherInterface',
                                cls, 'stringEchoReq')
        self._conn.addInterface(self._robot, tag, 'SubscriberConverter',
                                cls)
        self._conn.addConnection('{0}/{1}'.format(self._cTag, tag),
                                 '{0}/{1}'.format(self._robot, tag))

        tag = self.TYPES[1][1][1]
        cls = 'std_msgs/String'
        self._conn.addInterface(self._cTag, tag, 'SubscriberInterface',
                                cls, 'stringEchoResp')
        self._conn.addInterface(self._robot, tag, 'PublisherConverter',
                                cls)
        self._conn.addConnection('{0}/{1}'.format(self._cTag, tag),
                                 '{0}/{1}'.format(self._robot, tag))

    def _postProcess(self, _):
        with open('r2c.data', 'w') as f:
            f.write(json.dumps(SIZES))
            f.write('\n')

            for test in self._tests:
                f.write(str(test))
                f.write('\n')

        self._conn.destroyContainer(self._cTag)


def _get_argparse():
    from argparse import ArgumentParser

    parser = ArgumentParser(prog='r2c',
                            description='Run communication measurement for RCE '
                                        'between a robot and a container using '
                                        'a string message.')

    parser.add_argument('--passes', help='Number of passes to do.',
                        type=int, default=PASSES)
    parser.add_argument('ipMaster', help='IP address of master process.',
                        type=str)

    return parser


def main(reactor, passes, ip):
    user = 'testUser'
    robot = 'testRobot'
    connection = Connection(user, robot, user, reactor)
    measurement = Measurement(passes, connection, robot, reactor)

    print('Connect...')
    d = Deferred()
    d.addCallback(measurement.run)
    connection.connect('http://{0}:9000/'.format(ip), d)

    reactor.run()


if __name__ == '__main__':
    from twisted.internet import reactor

    args = _get_argparse().parse_args()

    main(reactor, args.passes, args.ipMaster)

########NEW FILE########
__FILENAME__ = rosbridge
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rosbridge.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import json
from collections import defaultdict, Counter

# twisted specific imports
from twisted.internet.defer import Deferred

# Autobahn specific imports
from autobahn.websocket import WebSocketClientFactory, \
                               WebSocketClientProtocol, \
                               connectWS

# local imports
from base import PASSES, SIZES, LocalServiceTest, LocalTopicTest


class Interface(object):
    def __init__(self, conn, addr):
        self._conn = conn
        self._addr = '/{0}'.format(addr)


class CBInterface(Interface):
    _INTERFACE_TYPE = None

    def __init__(self, conn, addr, cb):
        super(CBInterface, self).__init__(conn, addr)

        self._cb = cb
        conn.registerCb(self._INTERFACE_TYPE, self._addr, cb)
        self._registered = True

    def unsubscribe(self):
        if self._registered:
            self._conn.unregisterCb(self._INTERFACE_TYPE, self._addr, self._cb)
            self._registered = False

    def __del__(self):
        self.unsubscribe()


class ServiceClient(CBInterface):
    _INTERFACE_TYPE = 'srv'

    def call(self, msg):
        self._conn.sendMessage(json.dumps({'op':'call_service',
                                           'service':self._addr,
                                           'args':msg}))


class Publisher(Interface):
    def __init__(self, conn, addr, msgType):
        super(Publisher, self).__init__(conn, addr)

        conn.sendMessage(json.dumps({'op':'advertise',
                                     'topic':self._addr,
                                     'type':msgType}))

    def publish(self, msg):
        self._conn.sendMessage(json.dumps({'op':'publish',
                                           'topic':self._addr,
                                           'msg':msg}))

    def __del__(self):
        self._conn.sendMessage(json.dumps({'op':'unadvertise',
                                           'topic':self._addr}))


class Subscriber(CBInterface):
    _INTERFACE_TYPE = 'tpc'

    def __init__(self, conn, addr, cb):
        super(Subscriber, self).__init__(conn, addr, cb)

        conn.sendMessage(json.dumps({'op':'subscribe',
                                     'topic':self._addr}))

    def unsubscribe(self):
        if self._registered:
            self._conn.sendMessage(json.dumps({'op':'unsubscribe',
                                               'topic':self._addr}))

        super(Subscriber, self).unsubscribe()


class Connection(WebSocketClientProtocol):
    def __init__(self, reactor, deferred):
        self._reactor = reactor
        self._deferred = deferred

        self._srvCb = defaultdict(Counter)
        self._tpcCb = defaultdict(Counter)

    @property
    def reactor(self):
        return self._reactor

    def serviceClient(self, addr, _, cb):
        return ServiceClient(self, addr, cb)

    def publisher(self, addr, msgType):
        return Publisher(self, addr, msgType)

    def subscriber(self, addr, _, cb):
        return Subscriber(self, addr, cb)

    def registerCb(self, iType, addr, cb):
        if iType == 'srv':
            self._srvCb[addr][cb] += 1
        elif iType == 'tpc':
            self._tpcCb[addr][cb] += 1
        else:
            raise TypeError('Invalid interface type ({0}).'.format(iType))


    def unregisterCb(self, iType, addr, cb):
        if iType == 'srv':
            cbs = self._srvCb[addr]
        elif iType == 'tpc':
            cbs = self._tpcCb[addr]
        else:
            raise TypeError('Invalid interface type ({0}).'.format(iType))

        cbs[cb] -= 1

        if not cbs[cb]:
            del cbs[cb]

    def onMessage(self, msg, binary):
        msg = json.loads(msg)

        if msg['op'] == 'service_response':
            data = msg.get('values', {})

            for cb in self._srvCb[msg['service']]:
                cb(data)
        elif msg["op"] == "publish":
            data = msg['msg']

            for cb in self._tpcCb[msg['topic']]:
                cb(data)

    def onOpen(self):
        if self._deferred:
            self._deferred.callback(self)

    def onClose(self, wasClean, code, reason):
        if self._deferred and not self._deferred.called:
            self._deferred.errback(self)


class ConnectionFactory(WebSocketClientFactory):
    def __init__(self, url, reactor, deferred, **kw):
        WebSocketClientFactory.__init__(self, url, **kw)

        self._reactor = reactor
        self._deferred = deferred

    def buildProtocol(self, addr):
        p = Connection(self._reactor, self._deferred)
        p.factory = self
        return p


class Measurement(object):
    TYPES = ((LocalServiceTest, 'stringEchoService'),
             (LocalTopicTest, ('stringEchoReq', 'stringEchoResp')))

    def __init__(self, runs):
        self._runs = runs

    def run(self, conn):
        self._tests = [cls(conn, iTag) for cls, iTag in self.TYPES]

        d = Deferred()

        for _ in xrange(self._runs):
            for test in self._tests:
                d.addCallback(test.run)

        d.addCallback(self._postProcess)
        d.callback(None)

        def stop(_):
            reactor.stop()
            print('\ndone')

        d.addCallback(stop)

    def _postProcess(self, _):
        with open('rosbridge.data', 'w') as f:
            f.write(json.dumps(SIZES))
            f.write('\n')

            for test in self._tests:
                f.write(str(test))
                f.write('\n')


def _get_argparse():
    from argparse import ArgumentParser

    parser = ArgumentParser(prog='rosbridge',
                            description='Run communication measurement for '
                                        'rosbridge between a robot and a '
                                        'container using a string message.')

    parser.add_argument('--passes', help='Number of passes to do.',
                        type=int, default=PASSES)
    parser.add_argument('ipROSbridge', help='IP address of rosbridge.',
                        type=str)

    return parser


def main(reactor, passes, ip):
    measurement = Measurement(passes)

    d = Deferred()
    d.addCallback(measurement.run)

    factory = ConnectionFactory('ws://{0}:9090'.format(ip), reactor, d)
    connectWS(factory)

    reactor.run()


if __name__ == '__main__':
    from twisted.internet import reactor

    args = _get_argparse().parse_args()

    main(reactor, args.passes, args.ipROSbridge)

########NEW FILE########
__FILENAME__ = twisted_test
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     twisted_test.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import json

# twisted specific imports
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol, ClientFactory

# local imports
from base import PASSES, SIZES, LocalTest


class TwistedTest(LocalTest):
    def _activate(self):
        super(TwistedTest, self)._activate()
        print('Run twisted test...')
    
    def _sendReq(self):
        self._conn.sendMessage(self._str, self._resp)


class Connection(Protocol):
    def __init__(self, reactor, deferred):
        self._reactor = reactor
        self._deferred = deferred

        self._len = 0
        self._buf = ''
        self._cb = None

    @property
    def reactor(self):
        return self._reactor

    def sendMessage(self, msg, cb):
        assert self._cb is None
        self._cb = cb
        self._len = len(msg)
        self.transport.write(msg)

    def dataReceived(self, data):
        self._buf += data
        
        if len(self._buf) == self._len:
            assert self._cb is not None
            buf, self._buf = self._buf, ''
            cb, self._cb = self._cb, None
            cb(buf)
        elif len(self._buf) > self._len:
            raise ValueError('Message is too big.')

    def connectionMade(self):
        if self._deferred:
            self._deferred.callback(self)

    def connectionLost(self, reason):
        if self._deferred and not self._deferred.called:
            self._deferred.errback(self)


class ConnectionFactory(ClientFactory):
    def __init__(self, reactor, deferred):
        self._reactor = reactor
        self._deferred = deferred

    def buildProtocol(self, addr):
        p = Connection(self._reactor, self._deferred)
        p.factory = self
        return p


class Measurement(object):
    def __init__(self, runs):
        self._runs = runs

    def run(self, conn):
        self._tests = [TwistedTest(conn, '', 'twisted')]

        d = Deferred()

        for _ in xrange(self._runs):
            for test in self._tests:
                d.addCallback(test.run)

        d.addCallback(self._postProcess)
        d.callback(None)

        def stop(_):
            reactor.stop()
            print('\ndone')

        d.addCallback(stop)

    def _postProcess(self, _):
        with open('twisted.data', 'w') as f:
            f.write(json.dumps(SIZES))
            f.write('\n')

            for test in self._tests:
                f.write(str(test))
                f.write('\n')


def _get_argparse():
    from argparse import ArgumentParser

    parser = ArgumentParser(prog='twisted_test',
                            description='Run communication measurement for '
                                        'Twisted using a string message.')

    parser.add_argument('--passes', help='Number of passes to do.',
                        type=int, default=PASSES)
    parser.add_argument('ip', help='IP address of WebSocket Echo Server.',
                        type=str)

    return parser


def main(reactor, passes, ip):
    measurement = Measurement(passes)

    d = Deferred()
    d.addCallback(measurement.run)

    factory = ConnectionFactory(reactor, d)
    reactor.connectTCP(ip, 8000, factory)

    reactor.run()


if __name__ == '__main__':
    from twisted.internet import reactor

    args = _get_argparse().parse_args()

    main(reactor, args.passes, args.ip)

########NEW FILE########
__FILENAME__ = ws_test
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ws_test.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import json

# twisted specific imports
from twisted.internet.defer import Deferred

# Autobahn specific imports
from autobahn.websocket import WebSocketClientFactory, \
                               WebSocketClientProtocol, \
                               connectWS

# local imports
from base import PASSES, SIZES, LocalTest


class WebSocketTest(LocalTest):
    def __init__(self, conn, binary, testType):
        super(WebSocketTest, self).__init__(conn, None, testType)
        self._binary = binary

    def _activate(self):
        super(WebSocketTest, self)._activate()
        print('Run twisted test...')

    def _sendReq(self):
        self._conn.sendMessage(self._str, self._binary, self._resp)


class Connection(WebSocketClientProtocol):
    def __init__(self, reactor, deferred):
        self._reactor = reactor
        self._deferred = deferred
        self._cb = None

    @property
    def reactor(self):
        return self._reactor

    def sendMessage(self, msg, binary, cb):
        assert self._cb is None
        self._cb = cb
        WebSocketClientProtocol.sendMessage(self, msg, binary)

    def onMessage(self, msg, binary):
        assert self._cb is not None
        cb, self._cb = self._cb, None
        cb(msg)

    def onOpen(self):
        if self._deferred:
            self._deferred.callback(self)

    def onClose(self, wasClean, code, reason):
        if self._deferred and not self._deferred.called:
            self._deferred.errback(self)


class ConnectionFactory(WebSocketClientFactory):
    def __init__(self, url, reactor, deferred, **kw):
        WebSocketClientFactory.__init__(self, url, **kw)

        self._reactor = reactor
        self._deferred = deferred

    def buildProtocol(self, addr):
        p = Connection(self._reactor, self._deferred)
        p.factory = self
        return p


class Measurement(object):
    TYPES = ((False, 'text'), (True, 'binary'))

    def __init__(self, runs):
        self._runs = runs

    def run(self, conn):
        self._tests = [WebSocketTest(conn, b, t) for b, t in self.TYPES]

        d = Deferred()

        for _ in xrange(self._runs):
            for test in self._tests:
                d.addCallback(test.run)

        d.addCallback(self._postProcess)
        d.callback(None)

        def stop(_):
            reactor.stop()
            print('\ndone')

        d.addCallback(stop)

    def _postProcess(self, _):
        with open('websocket.data', 'w') as f:
            f.write(json.dumps(SIZES))
            f.write('\n')

            for test in self._tests:
                f.write(str(test))
                f.write('\n')


def _get_argparse():
    from argparse import ArgumentParser

    parser = ArgumentParser(prog='ws_test',
                            description='Run communication measurement for '
                                        'WebSocket using a string message.')

    parser.add_argument('--passes', help='Number of passes to do.',
                        type=int, default=PASSES)
    parser.add_argument('ip', help='IP address of WebSocket Echo Server.',
                        type=str)

    return parser


def main(reactor, passes, ip):
    measurement = Measurement(passes)

    d = Deferred()
    d.addCallback(measurement.run)

    factory = ConnectionFactory('ws://{0}:9000'.format(ip), reactor, d)
    connectWS(factory)

    reactor.run()


if __name__ == '__main__':
    from twisted.internet import reactor

    args = _get_argparse().parse_args()

    main(reactor, args.passes, args.ip)

########NEW FILE########
__FILENAME__ = connection
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-client/rce/client/connection.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import weakref
import re

# zope specific imports
from zope.interface import implements

# rce specific imports
from rce.comm.interfaces import IRobot, IClient
from rce.comm.client import RCE, ConnectionError
from rce.client.interface import HAS_ROS
from rce.client.interface import Publisher, Subscriber, \
    ServiceClient, ServiceProvider

if HAS_ROS:
    from rce.client.interface import ROSPublisher, ROSSubscriber, \
        ROSServiceClient, ROSServiceProvider
    from rce.util.loader import Loader


_IP_V4_REGEX = re.compile('^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.)'
                          '{3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')


class _Connection(object):
    """ Abstract implementation of a Connection.
    """
    implements(IRobot, IClient)

    INTERFACE_MAP = {}

    def __init__(self, userID, robotID, password, reactor):
        """ Initialize the Connection.

            @param userID:      User ID which will be used to authenticate the
                                connection.
            @type  userID:      str

            @param robotID:     Robot ID which will be used to authenticate the
                                connection.
            @type  robotID:     str

            @param password:    Password which will be used to authenticate the
                                connection.
            @type  password:    str

            @param reactor:     Reference to reactor which is used for this
                                connection.
            @type  reactor:     twisted::reactor
        """
        self._userID = userID
        self._robotID = robotID
        self._password = password
        self._reactor = reactor

        self._rce = None
        self._interfaces = {}

        self.disconnect()

    def __del__(self):
        self.disconnect()

    @property
    def reactor(self):
        """ Reference to twisted::reactor. """
        return self._reactor

    def connect(self, masterUrl, deferred):
        """ Connect to RCE.

            @param masterUrl:   URL of Authentication Handler of Master Manager
            @type  masterUrl:   str

            @param deferred:    Deferred which is called as soon as the
                                connection was successfully established.
            @type  deferred:    twisted.internet.defer.Deferred

            @raise:             ConnectionError, if no connection could be
                                established.
        """
        if self._rce:
            raise ConnectionError('There is already a connection registered.')

        self._rce = RCE(self, self._userID, self._robotID, self._password,
                        self._reactor)

        # Connect
        self._rce.connect(masterUrl, deferred)

    def disconnect(self):
        """ Disconnect from RCE.
        """
        if self._rce:
            self._rce.close()

        self._rce = None

    # Callback Interface objects

    def registerInterface(self, iTag, interface):
        """ Callback for Interface.

            @param iTag:        Tag of interface which should be registered.
            @type  iTag:        str

            @param interface:   Interface instance which should be registered.
            @type  interface:   rce.client.interface.*
        """
        if iTag not in self._interfaces:
            self._interfaces[iTag] = weakref.WeakSet()
        elif interface.UNIQUE:
            raise ValueError('Can not have multiple interfaces with the same '
                             'tag.')

        self._interfaces[iTag].add(interface)

    def unregisterInterface(self, iTag, interface):
        """ Callback for Interfaces.

            @param iTag:        Tag of interface which should be unregistered.
            @type  iTag:        str

            @param interface:   Interface instance which should be
                                unregistered.
            @type  interface:   rce.client.interface.*
        """
        if iTag not in self._interfaces:
            raise ValueError('No Interface registered with tag '
                             "'{0}'.".format(iTag))

        interfaces = self._interfaces[iTag]
        interfaces.discard(interface)

        if not interfaces:
            del self._interfaces[iTag]

    # Callback Client Protocol

    def processReceivedMessage(self, iTag, clsName, msgID, msg):
        try:
            interfaces = self._interfaces[iTag].copy()
        except (KeyError, weakref.ReferenceError):
            interfaces = []

        for interface in interfaces:
            if interface.CALLABLE:
                interface.callback(clsName, msg, msgID)

    processReceivedMessage.__doc__ = \
        IClient.get('processReceivedMessage').getDoc()

    def processInterfaceStatusUpdate(self, iTag, status):
        try:
            interfaces = self._interfaces[iTag].copy()
        except (KeyError, weakref.ReferenceError):
            interfaces = []

        for interface in interfaces:
            interface.setEnabled(status)

    processInterfaceStatusUpdate.__doc__ = \
        IClient.get('processInterfaceStatusUpdate').getDoc()

    # Forwarding

    def sendMessage(self, dest, msgType, msg, msgID):
        if not self._rce:
            raise ConnectionError('No connection to RCE.')

        self._rce.sendMessage(dest, msgType, msg, msgID)

    sendMessage.__doc__ = RCE.sendMessage.__doc__  #@UndefinedVariable

    def createContainer(self, cTag, group='', groupIp='', size=1, cpu=0,
                        memory=0, bandwidth=0, specialFeatures=[]):
        if not self._rce:
            raise ConnectionError('No connection to RCE.')

        # ensure all whitespace characters around group are stripped
        group = group.strip()

        if groupIp and not _IP_V4_REGEX.match(groupIp):
            raise ValueError('Invalid IPv4 address')

        self._rce.createContainer(cTag, group, groupIp, size, cpu, memory,
                                  bandwidth, specialFeatures)

    createContainer.__doc__ = RCE.createContainer.__doc__  #@UndefinedVariable

    def destroyContainer(self, cTag):
        if not self._rce:
            raise ConnectionError('No connection to RCE.')

        self._rce.destroyContainer(cTag)

    destroyContainer.__doc__ = RCE.destroyContainer.__doc__  #@UndefinedVariable

    def addNode(self, cTag, nTag, pkg, exe, args='', name='', namespace=''):
        if not self._rce:
            raise ConnectionError('No connection to RCE.')

        self._rce.addNode(cTag, nTag, pkg, exe, args, name, namespace)

    addNode.__doc__ = RCE.addNode.__doc__  #@UndefinedVariable

    def removeNode(self, cTag, nTag):
        if not self._rce:
            raise ConnectionError('No connection to RCE.')

        self._rce.removeNode(cTag, nTag)

    removeNode.__doc__ = RCE.removeNode.__doc__  #@UndefinedVariable

    def addParameter(self, cTag, name, value):
        if not self._rce:
            raise ConnectionError('No connection to RCE.')

        self._rce.addParameter(cTag, name, value)

    addParameter.__doc__ = RCE.addParameter.__doc__  #@UndefinedVariable

    def removeParameter(self, cTag, name):
        if not self._rce:
            raise ConnectionError('No connection to RCE.')

        self._rce.removeParameter(cTag, name)

    removeParameter.__doc__ = RCE.removeParameter.__doc__  #@UndefinedVariable

    def addInterface(self, eTag, iTag, iType, iCls, addr=''):
        if not self._rce:
            raise ConnectionError('No connection to RCE.')

        iType = self.INTERFACE_MAP.get(iType, iType)
        self._rce.addInterface(eTag, iTag, iType, iCls, addr)

    addInterface.__doc__ = RCE.addInterface.__doc__  #@UndefinedVariable

    def removeInterface(self, eTag, iTag):
        if not self._rce:
            raise ConnectionError('No connection to RCE.')

        self._rce.removeInterface(eTag, iTag)

    removeInterface.__doc__ = RCE.removeInterface.__doc__  #@UndefinedVariable

    def addConnection(self, tagA, tagB):
        if not self._rce:
            raise ConnectionError('No connection to RCE.')

        self._rce.addConnection(tagA, tagB)

    addConnection.__doc__ = RCE.addConnection.__doc__  #@UndefinedVariable

    def removeConnection(self, tagA, tagB):
        if not self._rce:
            raise ConnectionError('No connection to RCE.')

        self._rce.removeConnection(tagA, tagB)

    removeConnection.__doc__ = RCE.removeConnection.__doc__  #@UndefinedVariable


class Connection(_Connection):
    """ Connection which should be used for JSON based messages.
    """
    INTERFACE_MAP = {
        'ServiceClientForwarder'   : 'ServiceClientConverter',
        'ServiceProviderForwarder' : 'ServiceProviderConverter',
        'PublisherForwarder'       : 'PublisherConverter',
        'SubscriberForwarder'      : 'SubscriberConverter'
    }

    def publisher(self, iTag, msgType):
        """ Create a Publisher.

            @param iTag:        Unique tag which will be used to identify the
                                publisher.
            @type  iTag:        str

            @param msgType:     ROS message which will be published, e.g.
                                'std_msgs/String'
            @type  msgType:     str

            @return:            New Publisher instance.
            @rtype:             rce.client.interface.Publisher
        """
        return Publisher(self, iTag, msgType)

    def subscriber(self, iTag, msgType, cb):
        """ Create a Subscriber.

            @param iTag:        Unique tag which will be used to identify the
                                subscriber.
            @type  iTag:        str

            @param msgType:     ROS message to which will be subscribed, e.g.
                                    'std_msgs/String'
            @type  msgType:     str

            @param cb:          Callback which will takes as single argument
                                the received message.
            @type  cb:          callable

            @return:            New Subscriber instance.
            @rtype:             rce.client.interface.Subscriber
        """
        if not callable(cb):
            raise TypeError('Callback has to be callable.')

        return Subscriber(self, iTag, msgType, cb)

    def serviceClient(self, iTag, srvType, cb=None):
        """ Create a Service Client.

            @param iTag:        Unique tag which will be used to identify the
                                service.
            @type  iTag:        str

            @param srvType:     ROS Service which will used.
            @type  srvType:     str

            @param cb:          Can be used to specify a default callback for
                                received service responses; it should take the
                                response as the single argument.
            @type  cb:          callable

            @return:            New Service Client instance.
            @rtype:             rce.client.interface.ServiceClient
        """
        if cb and not callable(cb):
            raise TypeError('Callback has to be callable.')

        return ServiceClient(self, iTag, srvType, cb)

    def serviceProvider(self, iTag, srvType, cb, *args):
        """ Create a Service Provider.

            @param iTag:        Unique tag which will be used to identify the
                                service.
            @type  iTag:        str

            @param srvType:     ROS Service which will be provided.
            @type  srvType:     str

            @param cb:          Callback which will be called when a request has
                                been received. The callback will receive the
                                request as first argument and all additional
                                arguments. The callback should return the
                                response message if the request was successful
                                and None otherwise.
            @type  cb:          callable

            @param *args:       All additional arguments are passed to the
                                callback.

            @return:            New Service Provider instance.
            @rtype:             rce.client.interface.ServiceProvider
        """
        if cb and not callable(cb):
            raise TypeError('Callback has to be callable.')

        return ServiceProvider(self, iTag, srvType, cb, args)


if HAS_ROS:
    class ROSConnection(_Connection):
        """ Connection which should be used for ROS based messages.
        """
        INTERFACE_MAP = {
            'ServiceClientConverter'   : 'ServiceClientForwarder',
            'ServiceProviderConverter' : 'ServiceProviderForwarder',
            'PublisherConverter'       : 'PublisherForwarder',
            'SubscriberConverter'      : 'SubscriberForwarder'
        }

        _LOADER = Loader()

        @property
        def loader(self):
            """ Reference to Loader. """
            return self._LOADER

        def publisher(self, iTag, msgType, addr):
            """ Create a Publisher using ROS.

                @param iTag:        Unique tag which will be used to identify
                                    the publisher.
                @type  iTag:        str

                @param msgType:     ROS message which will be published, e.g.
                                    'std_msgs/String'
                @type  msgType:     str

                @param addr:        Topic where the publisher will listen for
                                    messages which should be published to the
                                    cloud engine.
                @type  addr:        str

                @return:            New Publisher instance.
                @rtype:             rce.client.interface.ROSPublisher
            """
            return ROSPublisher(self, iTag, msgType, addr)

        def subscriber(self, iTag, msgType, addr):
            """ Create a Subscriber using ROS.

                @param iTag:        Unique tag which will be used to identify
                                    the subscriber.
                @type  iTag:        str

                @param msgType:     ROS message to which will be subscribed,
                                    e.g. 'std_msgs/String'
                @type  msgType:     str

                @param addr:        Topic where the subscriber will publish
                                    received messages from to the RCE.
                @type  addr:        str

                @return:            New Subscriber instance.
                @rtype:             rce.client.interface.ROSSubscriber
            """
            return ROSSubscriber(self, iTag, msgType, addr)

        def serviceClient(self, iTag, srvType, addr):
            """ Create a Service Client using ROS.

                @param iTag:        Unique tag which will be used to identify
                                    the service.
                @type  iTag:        str

                @param srvType:     ROS Service which will used.
                @type  srvType:     str

                @param addr:        Address where the service will be available.

                @return:            New Service Client instance.
                @rtype:             rce.client.interface.ROSServiceClient
            """
            return ROSServiceClient(self, iTag, srvType, addr)

        def serviceProvider(self, iTag, srvType, addr):
            """ Create a Service Provider using ROS.

                @param iTag:        Unique tag which will be used to identify
                                    the service.
                @type  iTag:        str

                @param srvType:     ROS Service which will be provided.
                @type  srvType:     str

                @param addr:        Address where the service will be available.

                @return:            New Service Provider instance.
                @rtype:             rce.client.interface.ROSServiceProvider
            """
            return ROSServiceProvider(self, iTag, srvType, addr)

########NEW FILE########
__FILENAME__ = interface
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-client/rce/client/interface.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import zlib
from uuid import uuid4
from threading import Condition, Lock

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

# ROS specific imports; if available
try:
    import rospy
    import genpy.message
    HAS_ROS = True
except ImportError:
    HAS_ROS = False

# twisted specific imports
from twisted.internet.defer import Deferred
from twisted.internet.threads import deferToThreadPool


# Compression level used for communication
#     0:    use no compression
#     1-9:  use compression (1: fastest; 9: slowest, best compression)
_GZIP_LVL = 0


class InterfaceDisabledError(Exception):
    """ Exception is raised when an interface is called even though the
        interface is disabled.
    """


class _Base(object):
    """ Abstract base for all Interface classes.
    """
    UNIQUE = False
    CALLABLE = False

    _UP_MSG = "Interface '{0}' is up."
    _DOWN_MSG = "Interface '{0}' is down."

    def __init__(self, conn, iTag, clsName):
        """ Initialize the Interface.
        """
        self._status = False
        self._statusListener = set()

        print(self._UP_MSG.format(iTag))
        self._conn = conn
        self._iTag = iTag
        self._clsName = clsName

        conn.registerInterface(iTag, self)
        self._registered = True

    def __del__(self):
        """ Finalize the Interface.
        """
        self._unregister()

        if hasattr(self, '_iTag'):
            print(self._DOWN_MSG.format(self._iTag))

    @property
    def status(self):
        """ Status (enabled/disabled) of the interface.
        """
        return self._status

    def registerStatusListener(self, cb):
        """ Register a status listener which will be called with status changes.

            @param cb:          Callable which takes this interface instance as
                                first and the status flag as second argument.
            @type  cb:          callable
        """
        self._statusListener.add(cb)

    def unregisterStatusListener(self, cb):
        """ Unregister a previously registered status listener.

            @param cb:          Callable which should unregistered.
            @type  cb:          callable
        """
        self._statusListener.discard(cb)

    def setEnabled(self, status):
        """ Callback for RCE client to enable/disable the interface.
        """
        self._status = status

        if status:
            self._start()
        else:
            self._stop()

        for cb in self._statusListener:
            cb(self, status)

    def _start(self):
        """ Hook which is called when the status of the interface switches from
            disabled to enabled.
        """

    def _stop(self):
        """ Hook which is called when the status of the interface switches from
            enabled to disabled.
        """

    def _unregister(self):
        """ Internally used method to unregister the interface from the RCE
            client.
        """
        if hasattr(self, '_registered') and self._registered:
            self._conn.unregisterInterface(self._iTag, self)
            self._registered = False


class _CallableBase(_Base):
    """ Abstract base for all Interface classes which are callable by the RCE
        client.
    """
    CALLABLE = True

    def callback(self, msgType, msg, msgID):
        """ Callback for RCE. To implement the callback overwrite the hook
            '_callback'.
        """
        if not self._status:
            raise InterfaceDisabledError('A disabled interface should not be '
                                         'called by the RCE client.')

        if not msgType == self._clsName:
            raise TypeError('Received unexpected message type.')

        self._callback(msg, msgID)

    def _callback(self, msg, msgID):
        """ Callback to process the received message.
        """
        raise NotImplementedError('Method _callback has not been implemented.')


class _Publisher(_Base):
    """ Abstract implementation of a Publisher Interface.
    """
    _UP_MSG = "Publisher to RCE Interface '{0}' is up."
    _DOWN_MSG = "Publisher to RCE Interface '{0}' is down."

    def publish(self, msg):
        """ Publish a message.
        """
        if not self._status:
            raise InterfaceDisabledError('A disabled interface should not be '
                                         'called.')

        self._conn.sendMessage(self._iTag, self._clsName, msg, 'nil')


class _Subscriber(_CallableBase):
    """ Abstract implementation of a Subscriber Interface.
    """
    _UP_MSG = "Subscriber to RCE Interface '{0}' is up."
    _DOWN_MSG = "Subscriber to RCE Interface '{0}' is down."

    def __init__(self, conn, iTag, msgType, cb):
        """ Initialize the Subscriber.
        """
        self._cb = cb

        super(_Subscriber, self).__init__(conn, iTag, msgType)

    def unsubscribe(self):
        """ Unsubscribe interface from topic. Afterwards no more messages are
            given to the registered callback. To resubscribe a new interface
            has to be created.
        """
        self._unregister()

    def _callback(self, msg, _):
        """ Callback hook.
        """
        self._cb(msg)


class _ServiceClient(_CallableBase):
    """ Abstract implementation of a Service Client Interface.
    """
    UNIQUE = True

    _UP_MSG = "Service Client to RCE Interface '{0}' is up."
    _DOWN_MSG = "Service Client to RCE Interface '{0}' is down."

    def __init__(self, conn, iTag, srvType):
        """ Initialize the Service Client.
        """
        self._responses = {}

        super(_ServiceClient, self).__init__(conn, iTag, srvType)

    def _call(self, msg, cb, *args):
        """ Internally used method which should be used to call the service.

            @param msg:         Request message which should be sent.

            @param cb:          Callback which should be called to process
                                response. The response will be the first
                                argument and additional arguments passed to the
                                _call method will be passed to the callback.

            @param *args:       Additional arguments which will be passed to the
                                callback.
        """
        if not self._status:
            raise InterfaceDisabledError('A disabled interface should not be '
                                         'called.')

        if not callable(cb):
            raise TypeError('Callback has to be callable.')

        uid = uuid4().hex
        deferred = Deferred()
        deferred.addCallback(cb, *args)
        self._responses[uid] = deferred

        self._conn.sendMessage(self._iTag, self._clsName, msg, uid)

    def _callback(self, msg, msgID):
        """ Callback hook.
        """
        deferred = self._responses.pop(msgID, None)

        if deferred:
            deferred.callback(msg)
        else:
            print('Received service response which can not be associated '
                  'with any request.')


class _ServiceProvider(_CallableBase):
    """ Abstract implementation of a Service Provider Interface.
    """
    UNIQUE = True

    _UP_MSG = "Service Provider to RCE Interface '{0}' is up."
    _DOWN_MSG = "Service Provider to RCE Interface '{0}' is down."

    def __init__(self, conn, iTag, srvType, cb, args):
        """ Initialize the Service Provider.
        """
        self._cb = cb
        self._args = args

        super(_ServiceProvider, self).__init__(conn, iTag, srvType)

    def unregister(self):
        """ Unregister the service provider. Afterwards no more service requests
            are given to the registered callback. To reregister the service
            provider a new interface has to be created.
        """
        self._unregister()

    def _callback(self, msg, msgID):
        """ Callback hook.
        """
        reactor = self._conn._reactor
        d = deferToThreadPool(reactor, reactor.getThreadPool(),
                              self._cb, msg, *self._args)
        d.addCallback(self._response_success, msgID)
        d.addErrback(self._response_failure, msgID)

    def _response_success(self, msg, msgID):
        """ Internally used method which is executed when the service has been
            successfully called.
        """
        if not self._status:
            # Can not help it if the response takes some time and in the mean
            # time the interface is disabled; therefore, don't raise an error
            # instead just skip sending the response
            return

        self._conn.sendMessage(self._iTag, self._clsName, msg, msgID)

    def _response_failure(self, failure, msgID):
        """ Internally used method which is executed when the service call has
            failed.
        """
        if not self._status:
            # Can not help it if the response takes some time and in the mean
            # time the interface is disabled; therefore, don't raise an error
            # instead just skip sending the response
            return

        # TODO: Return something useful to the cloud here!
        print('Service call failed.')


class Publisher(_Publisher):
    """ Representation of a Publisher Interface.
    """


class Subscriber(_Subscriber):
    """ Representation of a Subscriber Interface.
    """


class ServiceClient(_ServiceClient):
    """ Representation of a Service Client Interface.
    """
    def __init__(self, conn, iTag, srvType, cb):
        """ Initialize the Service Client.
        """
        super(ServiceClient, self).__init__(conn, iTag, srvType)

        self._cb = cb

    def call(self, msg, cb=None):
        """ Call the Service Client.

            @param msg:     Request message which should be sent.
            @type  msg:     JSON compatible dictionary.

            @param cb:      Callback function which will be called with the
                            response message as argument. If parameter is
                            omitted the default callback is tried as fall-back.
            @type  cb:      Callable / None
        """
        self._call(msg, cb or self._cb)


class ServiceProvider(_ServiceProvider):
    """ Representation of a Service Provider Interface.
    """


if HAS_ROS:
    class TimeoutExceeded(Exception):
        """ Exception is raised when the timeout has passed without getting the
            reference of the Event.
        """


    class _EventRef(object):
        """ Helper class which acts as a threading.Event, but which can be used
            to pass a reference when signaling the event.
        """
        def __init__(self):
            self._cond = Condition(Lock())
            self._flag = False
            self._ref = None

        def isSet(self):
            return self._flag

        def set(self, ref):
            with self._cond:
                assert self._ref is None
                self._ref = ref
                self._flag = True
                self._cond.notifyAll()

        def get(self, timeout=None):
            with self._cond:
                if not self._flag:
                    self._cond.wait(timeout)

                if not self._flag:
                    raise TimeoutExceeded('Could not get the reference.')

                return self._ref

        def clear(self, ref):
            with self._cond:
                self._ref = None
                self._flag = False


    class ROSPublisher(_Publisher):
        """ Representation of a Publisher Interface using ROS.
        """
        def __init__(self, conn, iTag, msgType, addr):
            """ Initialize the Publisher.
            """
            self._sub = None
            self._addr = addr

            super(ROSPublisher, self).__init__(conn, iTag, msgType)

        def _rosCB(self, msg):
            """ Internally used callback for ROS Subscriber.
            """
            if _GZIP_LVL:
                self.publish(StringIO(zlib.compress(msg._buff, _GZIP_LVL)))
            else:
                self.publish(StringIO(msg._buff))

        def _start(self):
            self._sub = rospy.Subscriber(self._addr, rospy.AnyMsg, self._rosCB)
            print("Local ROS Subscriber on topic '{0}' is "
                  'up.'.format(self._addr))

        def _stop(self):
            self._sub.unregister()
            self._sub = None
            print("Local ROS Subscriber on topic '{0}' is "
                  'down.'.format(self._addr))

        def __del__(self):
            """ Finalize the Publisher.
            """
            if self._sub:
                self._stop()

            super(ROSPublisher, self).__del__()


    class ROSSubscriber(_Subscriber):
        """ Representation of a Subscriber Interface using ROS.
        """
        def __init__(self, conn, iTag, msgType, addr):
            """ Initialize the Subscriber.
            """
            self._pub = None
            self._addr = addr
            self._args = msgType.split('/')

            if len(self._args) != 2:
                raise ValueError('Message type is not valid. Has to be of the '
                                 'form pkg/msg, i.e. std_msgs/Int8.')

            super(ROSSubscriber, self).__init__(conn, iTag, msgType,
                                                self._rceCB)

        def _rceCB(self, msg):
            """ Internally used method to send received messages to the ROS
                Publisher.
            """
            rosMsg = rospy.AnyMsg()

            if _GZIP_LVL:
                rosMsg._buff = zlib.decompress(msg.getvalue())
            else:
                rosMsg._buff = msg.getvalue()

            self._pub.publish(rosMsg)

        def _start(self):
            self._pub = rospy.Publisher(self._addr,
                                        self._conn.loader.loadMsg(*self._args))
            print("Local ROS Publisher on topic '{0}' is "
                  'up.'.format(self._addr))

        def _stop(self):
            self._pub.unregister()
            self._pub = None
            print("Local ROS Publisher on topic '{0}' is "
                  'down.'.format(self._addr))

        def __del__(self):
            """ Finalize the Subscriber.
            """
            if self._pub:
                self._stop()

            super(ROSSubscriber, self).__del__()


    class ROSServiceClient(_ServiceClient):
        """ Representation of a Service Client Interface using ROS.
        """
        def __init__(self, conn, iTag, srvType, addr):
            """ Initialize the Service Client.
            """
            self._service = None
            self._addr = addr
            self._lock = Lock()
            self._pending = set()

            args = srvType.split('/')

            if len(args) != 2:
                raise ValueError('Service type is not valid. Has to be of the '
                                 'form pkg/srv, i.e. std_msgs/Int8.')

            self._srvCls = conn.loader.loadSrv(*args)
            self._srvCls._request_class = rospy.AnyMsg
            self._srvCls._response_class = rospy.AnyMsg

            super(ROSServiceClient, self).__init__(conn, iTag, srvType)

        def _rosCB(self, rosReq):
            """ Internally used callback for ROS Service.
            """
            event = _EventRef()

            if _GZIP_LVL:
                req = StringIO(zlib.compress(rosReq._buff, _GZIP_LVL))
            else:
                req = StringIO(rosReq._buff)

            with self._lock:
                self._pending.add(event)

            self._call(req, self._rceCB, event)

            with self._lock:
                self._pending.discard(event)

            rosResp = event.get()

            if not isinstance(rosResp, genpy.message.Message):
                raise rospy.ServiceException('Service call interrupted.')

            return rosResp

        def _rceCB(self, resp, event):
            """ Internally used method to send received message to the ROS
                Service as response.
            """
            rosResp = rospy.AnyMsg()

            if _GZIP_LVL:
                rosResp._buff = zlib.decompress(resp.getvalue())
            else:
                rosResp._buff = resp.getvalue()

            event.set(rosResp)

        def _start(self):
            self._service = rospy.Service(self._addr, self._srvCls, self._rosCB)
            print("Local ROS Service on address '{0}' is "
                  'up.'.format(self._addr))

        def _stop(self):
            self._service.shutdown()
            self._service = None
            print("Local ROS Service on address '{0}' is "
                  'down.'.format(self._addr))

            with self._lock:
                for event in self._pending:
                    event.set(None)

        def __del__(self):
            """ Finalize the Service.
            """
            if self._service:
                self._stop()

            assert len(self._pending) == 0

            super(ROSServiceClient, self).__del__()


    class ROSServiceProvider(_ServiceProvider):
        """ Representation of a Service Provider Interface using ROS.
        """
        def __init__(self, conn, iTag, srvType, addr):
            """ Initialize the Service Client.
            """
            self._addr = addr

            args = srvType.split('/')

            if len(args) != 2:
                raise ValueError('Service type is not valid. Has to be of the '
                                 'form pkg/srv, i.e. std_msgs/Int8.')

            self._srvCls = conn.loader.loadSrv(*args)
            self._srvCls._request_class = rospy.AnyMsg
            self._srvCls._response_class = rospy.AnyMsg

            super(ROSServiceProvider, self).__init__(conn, iTag, srvType,
                                                     self._rceCB, ())

        def _rceCB(self, req):
            """ Internally used method to send received message to the ROS
                Service as request.
            """
            rosReq = rospy.AnyMsg()

            if _GZIP_LVL:
                rosReq._buff = zlib.decompress(req.getvalue())
            else:
                rosReq._buff = req.getvalue()

            rospy.wait_for_service(self._addr, timeout=5)
            serviceFunc = rospy.ServiceProxy(self._addr, self._srvCls)
            rosResp = serviceFunc(rosReq)

            if _GZIP_LVL:
                resp = StringIO(zlib.compress(rosResp._buff, _GZIP_LVL))
            else:
                resp = StringIO(rosResp._buff)

            return resp

########NEW FILE########
__FILENAME__ = ros
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-client/rce/client/ros.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# ROS specific imports
try:
    import rospy
except ImportError:
    print('Can not import ROS Python client.')
    exit(1)

# twisted specific imports
from twisted.internet.defer import Deferred

# rce specific imports
from rce.util.ros import decorator_has_connection
from rce.client.connection import ConnectionError, ROSConnection


# Patch the method 'rospy.topics._TopicImpl.has_connection'
rospy.topics._TopicImpl.has_connection = \
    decorator_has_connection(rospy.topics._TopicImpl.has_connection)


_MAP = {'ServiceClientConverter'   : 'serviceProvider',
        'ServiceProviderConverter' : 'serviceClient',
        'PublisherConverter'       : 'subscriber',
        'SubscriberConverter'      : 'publisher'}


class Environment(object):
    def __init__(self, reactor, conn, config):
        self._reactor = reactor
        self._conn = conn

        self._containers = config.get('containers', [])
        self._nodes = config.get('nodes', [])
        self._parameters = config.get('parameters', [])
        self._interfaces = config.get('interfaces', [])
        self._connections = config.get('connections', [])

        self._ifs = []

    def run(self, _):
        try:
            for container in self._containers:
                self._conn.createContainer(**container)

            for parameter in self._parameters:
                self._conn.addParameter(**parameter)

            for node in self._nodes:
                self._conn.addNode(**node)

            for interface in self._interfaces:
                self._conn.addInterface(**interface)

            for connection in self._connections:
                self._conn.addConnection(**connection)

            for ros in self._interfaces:
                iType = ros['iType']

                if iType in _MAP:
                    self._ifs.append(
                        getattr(self._conn, _MAP[iType])(ros['iTag'],
                                                         ros['iCls'],
                                                         ros['addr'])
                    )
        except Exception as e:
            import traceback
            print(''.join(traceback.format_exception_only(type(e), e)))
            rospy.signal_shutdown('Error')

    def terminate(self):
        try:
            for parameter in self._parameters:
                self._conn.removeParameter(parameter['cTag'],
                                           parameter['name'])

            for container in self._containers:
                self._conn.destroyContainer(container.get('cTag'))
        except ConnectionError:
            pass

        self._ifs = []

        self._reactor.callLater(1, self._reactor.callFromThread,
                                self._reactor.stop)


def main(config, reactor):
    rospy.init_node('RCE_ROS_Client', anonymous=True)

    try:
        userID = config['userID']
        robotID = config['robotID']
        password = config['password']
        url = config['url']
    except KeyError as e:
        print('Configuration is missing the key {0}.'.format(e))
        return 1

    conn = ROSConnection(userID, robotID, password, reactor)
    env = Environment(reactor, conn, config)

    deferred = Deferred()
    deferred.addCallback(env.run)

    conn.connect(url, deferred)

    rospy.on_shutdown(env.terminate)

    reactor.run(installSignalHandlers=False)

########NEW FILE########
__FILENAME__ = assembler
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-comm/rce/comm/assembler.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import json
from datetime import datetime, timedelta
from uuid import uuid4

try:
    from cStringIO import StringIO, InputType, OutputType
    from StringIO import StringIO as pyStringIO

    def _checkIsStringIO(obj):
        return isinstance(obj, (InputType, OutputType, pyStringIO))
except ImportError:
    from StringIO import StringIO

    def _checkIsStringIO(obj):
        return isinstance(obj, StringIO)

# twisted specific imports
from twisted.python import log
from twisted.internet.task import LoopingCall

# rce specific imports
from rce.comm.error import InvalidRequest


class AssemblerError(Exception):
    """ Exception is raised when an error in the message assembler occurs.
    """


def recursiveBinarySearch(multidict):
    """ Search a JSON message for StringIO instances which should be replaced
        with a reference to a binary message. Returns a list of all binary
        messages and the modified JSON string message.

        @param multidict:       JSON message which might contain StringIO
                                instances and which should be prepared for
                                sending.
        @type  multidict:       { str : ... }

        @return:                A list of tuples containing the URI and the
                                matching StringIO instance. Also the modified
                                JSON message where the StringIO instances have
                                been replaced with the URIs is returned.
        @rtype:                 ((str, StringIO), { str : ... })
    """
    uriBinary = []
    keys = []

    for k, v in multidict.iteritems():
        if isinstance(v, dict):
            uriBinaryPart, multidictPart = recursiveBinarySearch(v)
            uriBinary += uriBinaryPart
            multidict[k] = multidictPart
        elif isinstance(v, (list, tuple)):
            if v and _checkIsStringIO(v[0]):
                for e in v:
                    if not _checkIsStringIO(e):
                        raise ValueError('Can not mix binary and string '
                                         'message in an array.')

                keys.append(k)
        elif _checkIsStringIO(v):
            keys.append(k)

    for k in keys:
        ele = multidict.pop(k)

        if isinstance(ele, (list, tuple)):
            uris = []

            for e in ele:
                tmpURI = uuid4().hex
                uris.append(tmpURI)
                uriBinary.append((tmpURI, e))

            ele = uris
        else:
            tmpURI = uuid4().hex
            uriBinary.append((tmpURI, ele))
            ele = tmpURI

        multidict['{0}*'.format(k)] = ele

    return uriBinary, multidict


class _IncompleteMsg(object):
    """ Class which represents an incomplete class.
    """
    def __init__(self, assembler, msg, uris):
        """ Initialize the incomplete message.

            @param assembler:   Assembler to which the this instance
                                belongs.
            @type  assembler:   client.assembler.MessageAssembler

            @param msg:         Incomplete message as a dictionary.
            @type  msg:         dict

            @param uris:        Return value of _recursiveURISearch
            @type  nr:          [ (str, dict, str) ]
        """
        self._assembler = assembler
        self._msg = msg
        self._uris = {}

        for uri, msgDict, key in uris:
            self._uris[uri] = (msgDict, key)

        self._added = datetime.now()

    @property
    def msg(self):
        """ Get the represented message. """
        if self._uris:
            raise AssemblerError('Message still contains missing references.')

        return self._msg

    def older(self, timestamp):
        """ Returns True if this incomplete message is older the the given
            timestamp.
        """
        return self._added < timestamp

    def addBinary(self, uri, binaryData):
        """ Add the binary data with the given uri.

            @return:    True if the binary was used; False otherwise.
        """
        ref = self._uris.pop(uri, None)

        if ref:
            parent, key = ref
            parent[key] = binaryData

            if self._uris:
                self._added = datetime.now()
            else:
                self._assembler.forwardCompleteMessage(self)

            return True
        else:
            return False


class MessageAssembler(object):
    """ Class which is used to store incomplete messages for a certain time
        and which is used to assemble them when possible.
    """
    def __init__(self, protocol, timeout):
        """ Initialize the binary assembler.

            @param protocol:    Protocol instance for which this assembler is
                                used.

            @param timeout:     Timeout in seconds after which incomplete
                                messages are discarded.
            @type  timeout:     int
        """
        self._protocol = protocol
        self._timeout = timeout

        # Set of _IncompleteMessage instances
        self._incompleteMsgs = set()

        # Dictionary with binary UID as key and the binary as value
        self._binaries = {}

        # Setup repeated calling of the clean up method
        self._cleaner = LoopingCall(self._cleanUp)

    def forwardCompleteMessage(self, msgRepr):
        """ Callback for rce.comm.assembler._IncompleteMsg to send a completed
            message to the correct handler.
        """
        self._incompleteMsgs.remove(msgRepr)
        self._protocol.processCompleteMessage(msgRepr.msg)

    def _handleString(self, msg, uris):
        """ Try to process the received incomplete string message, i.e.
            assemble the message with the waiting binary data. Forward the
            message if it can be completed and store the incomplete message
            otherwise.

            @param msg:     Received string message.
            @type  msg:     str

            @param uris:    Return value of self._recursiveURISearch
            @type  uris:    [ (str, dict, str) or (str, list, int) ]
        """
        missing = []

        for ref in uris:
            uri, parent, key = ref
            binaryData = self._binaries.pop(uri, None)

            if binaryData:
                parent[key] = binaryData[0]
            else:
                missing.append(ref)

        if missing:
            self._incompleteMsgs.add(_IncompleteMsg(self, msg, missing))
        else:
            self._protocol.processCompleteMessage(msg)

    def _handleBinary(self, msg):
        """ Try to process a received binary message, i.e. assemble the waiting
            string message with the received binary data. Forward the message
            if the received binary data completes the waiting message and store
            the binary message otherwise.

            @param msg:     Received binary message.
            @type  msg:     str
        """
        uri = msg[:32]
        binaryData = StringIO()
        binaryData.write(msg[32:])

        for msg in self._incompleteMsgs:
            if msg.addBinary(uri, binaryData):
                break
        else:
            self._binaries[uri] = (binaryData, datetime.now())

    def _recursiveURISearch(self, multidict):
        """ Internally used method to find binary data in incoming messages.

            @return:    List of tuples of the forms (uri, dict, key) or
                        (uri, list, index)
        """
        valueList = []
        keys = []

        for k, v in multidict.iteritems():
            if isinstance(v, dict):
                valueList += self._recursiveURISearch(v)
            elif k[-1] == '*':
                keys.append(k)

        for k in keys:
            ele = multidict.pop(k)

            if isinstance(ele, list):
                lst = [None] * len(ele)
                multidict[k[:-1]] = lst

                for i, uri in enumerate(ele):
                    valueList.append((uri, lst, i))
            else:
                valueList.append((ele, multidict, k[:-1]))

        return valueList

    def processMessage(self, msg, binary):
        """ This method is used to process any messages which should pass
            through the assembler.
        """
        if binary:
            self._handleBinary(msg)
        else:
            try:
                msg = json.loads(msg)
            except ValueError:
                raise InvalidRequest('Message is not in valid JSON format.')

            uris = self._recursiveURISearch(msg)

            if uris:
                self._handleString(msg, uris)
            else:
                self._protocol.processCompleteMessage(msg)

    def start(self):
        """ Start the cleaner of the assembler.
        """
        self._cleaner.start(self._timeout / 4)

    def stop(self):
        """ Stop the cleaner of the assembler and remove any circular
            references.
        """
        self._incompleteMsgs = set()

        if self._cleaner.running:
            self._cleaner.stop()

    def _cleanUp(self):
        """ Internally used method to remove old incomplete messages.
        """
        limit = datetime.now() - timedelta(seconds=self._timeout)

        toClean = [msg for msg in self._incompleteMsgs if msg.older(limit)]

        if toClean:
            for msg in toClean:
                self._incompleteMsgs.remove(msg)

            log.msg('{0} incomplete messages have been dropped '
                    'from assembler.'.format(len(toClean)))

        toClean = [uri for uri, (_, timestamp) in self._binaries.iteritems()
                   if timestamp < limit]

        if toClean:
            for uri in toClean:
                del self._binaries[uri]

            log.msg('{0} unused binaries have been dropped '
                    'from assembler.'.format(len(toClean)))

########NEW FILE########
__FILENAME__ = client
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-comm/rce/comm/client.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import json
import itertools
from urllib import urlencode
from urllib2 import urlopen, HTTPError
from hashlib import sha256

# zope specific imports
from zope.interface import implements

# twisted specific imports
from twisted.python.threadable import isInIOThread
from twisted.internet.threads import deferToThreadPool

# Autobahn specific imports
from autobahn.websocket import connectWS, WebSocketClientFactory, \
    WebSocketClientProtocol

# rce specific imports
from rce.comm import types
from rce.comm._version import CURRENT_VERSION
from rce.comm.interfaces import IRobot, IClient
from rce.comm.assembler import recursiveBinarySearch, MessageAssembler
from rce.util.interface import verifyObject


class RCERobotProtocol(WebSocketClientProtocol):
    """ WebSocket client protocol which is used to communicate with the Robot
        Manager.
    """
    def __init__(self, conn):
        """ Initialize the protocol.

            @param conn:        Connection instance which provides callback
                                functions.
            @type  conn:        rce.comm.client.RCE
        """
        self._connection = conn
        self._assembler = MessageAssembler(self, 60)
        self._registered = False

    def onOpen(self):
        """ This method is called by twisted as soon as the WebSocket
            connection has been successfully established.
        """
        self._assembler.start()
        self._connection.registerConnection(self)
        self._registered = True

    def onMessage(self, msg, binary):
        """ This method is called by twisted when a new message has been
            received.
        """
        self._assembler.processMessage(msg, binary)

    def processCompleteMessage(self, msg):
        """ Callback for MessageAssembler which will be called as soon as a
            message has been completed and is ready for processing.
        """
        self._connection.receivedMessage(msg)

    def sendMessage(self, msg):
        """ Internally used method to send messages via WebSocket connection.
            Thread-safe implementation.

            @param msg:         Message which should be sent.
        """
        binaries, msg = recursiveBinarySearch(msg)
        msg = json.dumps(msg)

        if isInIOThread():
            self._send(msg, binaries)
        else:
            self._connection.reactor.callFromThread(self._send, msg, binaries)

    def _send(self, msg, binaries):
        """ Internally used method to send messages via WebSocket connection.
            Handles the actual sending of the message. (Not thread-safe; use
            sendMessage instead.)
        """
        WebSocketClientProtocol.sendMessage(self, msg)

        for data in binaries:
            binMsg = data[0] + data[1].getvalue()
            WebSocketClientProtocol.sendMessage(self, binMsg, binary=True)

    def onClose(self, *args):
        """ This method is called by twisted when the connection has been
            closed.
        """
        if self._registered:
            self._connection.unregisterConnection(self)
            self._assembler.stop()
            self._registered = False

    def failHandshake(self, reason):
        """ This method is called by twisted when the connection could not be
            initialized.
        """
        print(reason)
        WebSocketClientProtocol.failHandshake(self, reason)


class RCERobotFactory(WebSocketClientFactory):
    """ WebSocket protocol factory which is used for the communication with the
        Robot Manager.
    """
    def __init__(self, url, conn):
        """ Initialize the factory.

            @param url:         URL of the Robot process.
            @type  url:         str

            @param conn:        Connection instance which provides callback
                                functions.
            @type  conn:        rce.comm.client.RCE
        """
        WebSocketClientFactory.__init__(self, url)
        self._connection = conn

    def buildProtocol(self, addr):
        """ This method is called by twisted when a new connection should be
            made.
        """
        p = RCERobotProtocol(self._connection)
        p.factory = self
        return p


class ConnectionError(Exception):
    """ Error is raised when there is no connection or the connection is
        not valid.
    """


class RCE(object):
    """ Class represents a connection to the RoboEarth Cloud Engine.
    """
    implements(IRobot)

    _PREFIXES = ['ServiceClient', 'ServiceProvider', 'Publisher', 'Subscriber']
    _SUFFIXES = ['Interface', 'Converter', 'Forwarder']
    _INTERFACES = [''.join(t) for t in itertools.product(_PREFIXES, _SUFFIXES)]

    def __init__(self, receiver, userID, robotID, password, reactor):
        """ Initialize the Connection.

            @param receiver:    Object which is responsible for the processing
                                of received data messages.
            @type  receiver:    rce.comm.interfaces.IMessageReceiver

            @param userID:      User ID which will be used to authenticate the
                                connection.
            @type  userID:      str

            @param robotID:     Robot ID which will be used to authenticate the
                                connection.
            @type  robotID:     str

            @param password:    Password which will be used to authenticate the
                                connection.
            @type  password:    str

            @param reactor:     Reference to reactor which is used for this
                                connection.
            @type  reactor:     twisted::reactor
        """
        verifyObject(IClient, receiver)

        self._receiver = receiver
        self._userID = userID
        self._robotID = robotID
        self._password = sha256(password).hexdigest()
        self._reactor = reactor
        self._conn = None
        self._connectedDeferred = None

    @property
    def reactor(self):
        """ Reference to twisted::reactor. """
        return self._reactor

    def registerConnection(self, conn):
        """ Callback for RCERobotProtocol.

            @param conn:        Connection which should be registered.
            @type  conn:        rce.comm.client.RCERobotProtocol
        """
        if self._conn:
            raise ConnectionError('There is already a connection registered.')

        self._conn = conn
        print('Connection to RCE established.')

        if self._connectedDeferred:
            self._connectedDeferred.callback(self)
            self._connectedDeferred = None

    def unregisterConnection(self, conn):
        """ Callback for RCERobotProtocol.

            @param conn:        Connection which should be unregistered.
            @type  conn:        rce.comm.client.RCERobotProtocol
        """
        if not self._conn:
            raise ConnectionError('There is no connection registered.')

        if self._conn != conn:
            raise ConnectionError('This connection is not registered.')

        self._conn = None
        print('Connection closed.')

    def _getRobotURL(self, masterUrl):
        """ Internally used method to connect to the Master process to get
            a URL of a Robot process.
        """
        print('Connect to Master Process on: {0}'.format(masterUrl))

        args = urlencode((('userID', self._userID),
                          ('version', CURRENT_VERSION)))

        try:
            f = urlopen('{0}?{1}'.format(masterUrl, args))
        except HTTPError as e:
            msg = e.read()

            if msg:
                msg = ' - {0}'.format(msg)

            raise ConnectionError('HTTP Error {0}: '
                                  '{1}{2}'.format(e.getcode(), e.msg, msg))

        return json.loads(f.read())

    def _robotConnect(self, resp):
        """ Internally used method to connect to the Robot process.
        """
        # Read the response
        url = resp['url']
        current = resp.get('current', None)

        if current:
            print("Warning: There is a newer client (version: '{0}') "
                  'available.'.format(current))

        print('Connect to Robot Process on: {0}'.format(url))

        # Make WebSocket connection to Robot Manager
        args = urlencode((('userID', self._userID), ('robotID', self._robotID),
                          ('password', self._password)))
        factory = RCERobotFactory('{0}?{1}'.format(url, args), self)
        connectWS(factory)

    def connect(self, masterUrl, deferred):
        """ Connect to RCE.

            @param masterUrl:   URL of Master process.
            @type  masterUrl:   str

            @param deferred:    Deferred which is called as soon as the
                                connection was successfully established.
            @type  deferred:    twisted.internet.defer.Deferred

            @raise:             ConnectionError, if no connection could be
                                established.
        """
        self._connectedDeferred = deferred

        def eb(e):
            print(e.getErrorMessage())

            if self._connectedDeferred:
                self._connectedDeferred.errback(e)
                self._connectedDeferred = None

        d = deferToThreadPool(self._reactor, self._reactor.getThreadPool(),
                              self._getRobotURL, masterUrl)
        d.addCallback(self._robotConnect)
        d.addErrback(eb)

    def close(self):
        """ Disconnect from RCE.
        """
        if self._conn:
            self._conn.dropConnection()

    def _sendMessage(self, msgType, msgData):
        """ Internally used method to send messages via RCERobotProtocol.

            @param msgType:     String describing the type of the message.
            @type  msgType:     str

            @param msgData:     Message which should be sent.
        """
        if not self._conn:
            raise ConnectionError('No connection registered.')

        self._conn.sendMessage({'type':msgType, 'data':msgData})

    def sendMessage(self, dest, msgType, msg, msgID):
        """ Send a data message to the cloud engine.

            @param dest:        Interface tag of message destination.
            @type  dest:        str

            @param msgType:     ROS Message type in format "pkg/msg", e.g.
                                'std_msgs/String'
            @type  msgType:     str

            @param msg:         Message which should be sent in form of a
                                dictionary matching the structure of the ROS
                                message and using StringIO instances for binary
                                message parts.
            @type msg:          { str : {} / base_types / StringIO }

            @param msgID:       Message ID which is used to match request and
                                response message.
            @type  msgID:       str
        """
        self._sendMessage(types.DATA_MESSAGE, {'iTag':dest, 'type':msgType,
                                               'msgID':msgID, 'msg':msg})

    def createContainer(self, cTag, group='', groupIp='', size=1, cpu=0,
                        memory=0, bandwidth=0, specialFeatures=[]):
        """ Create a container.

            @param cTag:                Unique tag which will be used to
                                        identify the container to create.
            @type  cTag:                str

            @param group:               The container group to which the
                                        container will be added.
            @type  group:               str

            @param groupIp:             The static IPv4 address which will be
                                        assigned to the container inside the
                                        group.
            @type  groupIp:             str

            @param size:                The container instance size.
            @type  size:                int

            @param cpu:                 CPU Allocation.
            @type  cpu:                 int

            @param memory:              Memory Allocation.
            @type  memory:              int

            @param bandwidth:           Bandwidth allocation.
            @type  bandwidth:           int

            @param specialFeatures:     Special features required,
                                        e.g. ['gpu','hadoop','avxii'].
            @type  specialFeatures:     list
        """
        print("Request creation of container '{0}'.".format(cTag))
        data = {}

        if group:
            data['group'] = group

        if groupIp:
            data['groupIp'] = groupIp

        if size:
            data['size'] = size

        if cpu:
            data['cpu'] = cpu

        if memory:
            data['memory'] = memory

        if bandwidth:
            data['bandwidth'] = bandwidth

        if specialFeatures:
            data['specialFeatures'] = specialFeatures

        container = {'containerTag':cTag}

        if data:
            container['containerData'] = data

        self._sendMessage(types.CREATE_CONTAINER, container)

    def destroyContainer(self, cTag):
        """ Destroy a container.

            @param cTag:        Tag of the container to remove.
            @type  cTag:        str
        """
        print("Request destruction of container '{0}'.".format(cTag))
        self._sendMessage(types.DESTROY_CONTAINER, {'containerTag':cTag})

    def addNode(self, cTag, nTag, pkg, exe, args='', name='', namespace=''):
        """ Add a node.

            @param cTag:        Tag of container in which the node should be
                                added.
            @type  cTag:        str

            @param nTag:        Unique tag within a container which will be
                                used to identify the node to add.
            @type  nTag:        str

            @param pkg:         Name of ROS package where the executable can be
                                found.
            @type  pkg:         str

            @param exe:         Name of the executable which should be
                                executed.
            @type  exe:         str

            @param args:        Optional arguments which should be passed to
                                the executable as a single string. Can contain
                                the directives $(find PKG) or $(env VAR). Other
                                special characters as '$' or ';' are not
                                allowed.
            @type  args:        str

            @param name:        Optional argument which defines the name used
                                in the ROS environment.
            @type  name:        str

            @param namespace:   Optional argument which defines the namespace
                                used in the ROS environment.
            @type  namespace:   str
        """
        print("Request addition of node '{0}' to container '{1}' "
              '[pkg: {2}; exe: {3}].'.format(nTag, cTag, pkg, exe))
        node = {'containerTag':cTag, 'nodeTag':nTag, 'pkg':pkg, 'exe':exe}

        if args:
            node['args'] = args

        if name:
            node['name'] = name

        if namespace:
            node['namespace'] = namespace

        self._sendMessage(types.CONFIGURE_COMPONENT, {'addNodes':[node]})

    def removeNode(self, cTag, nTag):
        """ Remove a node.

            @param cTag:        Tag of container in which the node should be
                                removed.
            @type  cTag:        str

            @param nTag:        Tag the node to remove.
            @type  nTag:        str
        """
        print("Request removal of node '{0}' from container "
              "'{1}'.".format(nTag, cTag))
        node = {'containerTag':cTag, 'nodeTag':nTag}
        self._sendMessage(types.CONFIGURE_COMPONENT, {'removeNodes':[node]})

    def addParameter(self, cTag, name, value):
        """ Add a parameter.

            @param cTag:        Tag of container in which the parameter should
                                be added.
            @type  cTag:        str

            @param name:        Name of the parameter which is used to identify
                                the parameter and which is used inside the
                                ROS environment.
            @type  name:        str

            @param value:       Value which should be added. String values can
                                contain the directives $(find PKG) or
                                $(env VAR).
            @type  value:       int/float/bool/str/[]
        """
        print("Request addition of parameter '{0}' to container "
              "'{1}'.".format(name, cTag))
        param = {'containerTag':cTag, 'name':name, 'value':value}
        self._sendMessage(types.CONFIGURE_COMPONENT, {'setParam':[param]})

    def removeParameter(self, cTag, name):
        """ Remove a parameter.

            @param cTag:        Tag of container in which the parameter should
                                be removed.
            @type  cTag:        str

            @param name:        Name of the parameter to remove.
            @type  name:        str
        """
        print("Request removal of parameter '{0}' from container "
              "'{1}'.".format(name, cTag))
        param = {'containerTag':cTag, 'name':name}
        self._sendMessage(types.CONFIGURE_COMPONENT, {'deleteParam':[param]})

    def addInterface(self, eTag, iTag, iType, iCls, addr=''):
        """ Add an interface.

            @param eTag:        Tag of endpoint to which the interface should
                                be added. (Either a container tag or robot ID)
            @type  eTag:        str

            @param iTag:        Unique tag which will be used to identify the
                                interface to add.
            @type  iTag:        str

            @param iType:       Type of the interface, which needs one of the
                                following prefix:
                                    Service, ServiceProvider,
                                    Publisher, Subscriber
                                and on of the following suffix:
                                    Interface, Converter
            @type  iType:       str

            @param iCls:        ROS Message/Service type in format "pkg/msg",
                                e.g. 'std_msgs/String'
            @type  iCls:        str

            @param addr:        Optional argument which is used for ROS
                                Interfaces where the argument will provide
                                the name under which the interface will be
                                available in the local ROS environment.
            @type  addr:        str
        """
        print("Request addition of interface '{0}' of type '{1}' to endpoint "
              "'{2}'.".format(iTag, iType, eTag))
        if iType not in self._INTERFACES:
            raise TypeError('Interface type is not valid.')

        iface = {'endpointTag':eTag, 'interfaceTag':iTag,
                 'interfaceType':iType, 'className':iCls}

        if addr:
            iface['addr'] = addr

        self._sendMessage(types.CONFIGURE_COMPONENT, {'addInterfaces':[iface]})

    def removeInterface(self, eTag, iTag):
        """ Remove an interface.

            @param eTag:        Tag of endpoint from which the interface should
                                be removed. (Either a container tag or
                                robot ID)
            @type  eTag:        str

            @param iTag:        Tag of interface to remove.
            @type  iTag:        str
        """
        print("Request removal of interface '{0}'.".format(iTag))
        iface = {'endpointTag':eTag, 'interfaceTag':iTag}
        self._sendMessage(types.CONFIGURE_COMPONENT,
                          {'removeInterfaces':[iface]})

    def addConnection(self, tagA, tagB):
        """ Create a connection.

            @param tagX:        One of the interfaces which should be
                                connected. The tag has to be of the form
                                    [endpoint tag]/[interface tag]
            @type  tagX:        str
        """
        print("Request creation of connection between interface '{0}' and "
              "'{1}'.".format(tagA, tagB))
        conn = {'tagA':tagA, 'tagB':tagB}
        self._sendMessage(types.CONFIGURE_CONNECTION, {'connect':[conn]})

    def removeConnection(self, tagA, tagB):
        """ Destroy a connection.

            @param tagX:        One of the interfaces which should be
                                disconnected. The tag has to be of the form
                                    [endpoint tag]/[interface tag]
            @type  tagX:        str
        """
        print("Request destruction of connection between interface '{0}' and "
              "'{1}'.".format(tagA, tagB))
        conn = {'tagA':tagA, 'tagB':tagB}
        self._sendMessage(types.CONFIGURE_CONNECTION, {'disconnect':[conn]})

    def receivedMessage(self, msg):
        """ Callback from RCERobotProtocol.

            @param msg:         Message which has been received.
            @type  msg:         { str : {} / base_types / StringIO }
        """
        try:
            msgType = msg['type']
            data = msg['data']
        except KeyError as e:
            raise ValueError('Received message from robot process is missing '
                             'the key {0}.'.format(e))

        if msgType == types.ERROR:
            print('Received ERROR message: {0}'.format(data))
        elif msgType == types.STATUS:
            try:
                topic = data['topic']
            except KeyError as e:
                raise ValueError('Received STATUS message from robot process '
                                 'is missing the key {0}.'.format(e))

            if topic == types.STATUS_INTERFACE:
                try:
                    iTag = data['iTag']
                    status = data['status']
                except KeyError as e:
                    raise ValueError('Received STATUS message (Interface '
                                     'Status Update) from robot process is '
                                     'missing the key {0}.'.format(e))

                self._receiver.processInterfaceStatusUpdate(iTag, status)
            else:
                print('Received STATUS message with unknown content type: '
                      '{0}'.format(topic))
        elif msgType == types.DATA_MESSAGE:
            try:
                iTag = data['iTag']
                clsName = data['type']
                rosMsg = data['msg']
                msgID = data['msgID']
            except KeyError as e:
                raise ValueError('Received DATA message from robot process '
                                 'is missing the key {0}.'.format(e))

            self._receiver.processReceivedMessage(iTag, clsName, msgID, rosMsg)
        else:
            print('Received message with unknown message type: '
                  '{0}'.format(msgType))

########NEW FILE########
__FILENAME__ = error
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-comm/rce/comm/error.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

class InvalidRequest(Exception):
    """ Exception is used to signal an invalid request.
    """


class DeadConnection(Exception):
    """ Exception is used to signal to the client protocol that the connection
        is dead.
    """

########NEW FILE########
__FILENAME__ = interfaces
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-comm/rce/comm/interfaces.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# zope specific imports
from zope.interface import Interface


class IMasterRealm(Interface):
    """ Interface which the Master realm has to implement.
    """
    def requestURL(userID):  #@NoSelf
        """ Callback for Robot resource to retrieve the location of the Robot
            process to which a WebSocket connection should be established.

            @param userID:      User ID under which the robot will login.
                                (Can be used to do optimizations in distributing
                                the load.)
            @type  userID:      str

            @return:            The IP address of Robot process to which a
                                WebSocket connection should be established.
                                (type: str)
            @rtype:             twisted.internet.defer.Deferred
        """


class IRobotRealm(Interface):
    """ Interface which the Robot realm has to implement.
    """
    def login(userID, robotID, password):  #@NoSelf
        """ Callback for Robot connection to login and authenticate.

            @param userID:      User ID under which the robot is logging in.
            @type  userID:      str

            @param robotID:     Unique ID of the robot in the namespace of the
                                user under which the robot is logging in.
            @type  robotID:     str

            @param password:    Hashed password as hex-encoded string which is
                                used to authenticate the user.
            @type  password:    str

            @return:            Representation of the connection to the robot
                                which is used in the Robot process.
                                (type: rce.robot.Connection)
            @rtype:             twisted.internet.defer.Deferred
        """

    def registerWebsocketProtocol(connection, protocol):  #@NoSelf
        """ Register the client protocol with a Connection object.

            @param connection:  Connection where the protocol should be
                                registered.
            @type  connection:  rce.robot.Connection

            @param protocol:    Protocol which should be registered.
            @type  protocol:    rce.comm.interfaces.IServersideProtocol
        """

    def unregisterWebsocketProtocol(connection, protocol):  #@NoSelf
        """ Unregister the client protocol from a Connection object.

            @param connection:  Connection where the protocol should be
                                unregistered.
            @type  connection:  rce.robot.Connection

            @param protocol:    Protocol which should be unregistered.
            @type  protocol:    rce.comm.interfaces.IServersideProtocol
        """


class IProtocol(Interface):
    """ Interface which the Protocol has to implement on the server side.
    """
    def sendDataMessage(iTag, clsName, msgID, msg):  #@NoSelf
        """ Send a data message to the robot client.

            @param iTag:        Tag which is used to identify the interface to
                                which this message should be sent.
            @type  iTag:        str

            @param clsName:     Message type/Service type consisting of the
                                package and the name of the message/service,
                                i.e. 'std_msgs/Int32'.
            @type  clsName:     str

            @param msgID:       Message ID which can be used to get a
                                correspondence between request and response
                                message for a service call.
            @type  msgID:       str

            @param msg:         Message which should be sent. It has to be a
                                JSON compatible dictionary where part or the
                                complete message can be replaced by a StringIO
                                instance which is interpreted as binary data.
            @type  msg:         {str : {} / base_types / StringIO} / StringIO
        """

    def sendInterfaceStatusUpdateMessage(iTag, status): #@NoSelf
        """ Send a status change to the client such that the client can start
            or stop its client-side interface implementation according to the
            status information.

            @param iTag:        Tag which is used to identify the interface
                                which changed its status.
            @type  iTag:        str

            @param status:      Boolean indicating whether the interface should
                                be active or not.
            @type  status:      bool
        """

    def sendErrorMessage(msg):  #@NoSelf
        """ Send an error message to the robot client.

            @param msg:         Error message which should be sent.
            @type  msg:         str
        """

    def dropConnection():  #@NoSelf
        """ Request that the protocol drops the connection to the client.
        """


class IRobot(Interface):
    """ Interface which the Robot Avatar has to implement.
    """
    def createContainer(tag, data={}):  #@NoSelf
        """ Create a new Container object.

            @param tag:         Tag which is used to identify the container
                                in subsequent requests.
            @type  tag:         str

            @param data:        Extra data which is used to configure the
                                container.
            @type  data:        dict
        """

    def destroyContainer(tag):  #@NoSelf
        """ Destroy a Container object.

            @param tag:         Tag which is used to identify the container
                                which should be destroyed.
            @type  tag:         str
        """

    def addNode(cTag, nTag, pkg, exe, args='', name='', namespace=''):  #@NoSelf
        """ Add a node to a container / ROS environment.

            @param cTag:        Tag which is used to identify the container /
                                ROS environment to which the node should be
                                added.
            @type  cTag:        str

            @param nTag:        Tag which is used to identify the node in
                                subsequent requests.
            @type  nTag:        str

            @param pkg:         Name of ROS package where the node can be
                                found.
            @type  pkg:         str

            @param exe:         Name of executable (node) which should be
                                launched.
            @type  exe:         str

            @param args:        Additional arguments which should be used for
                                the launch. Can contain the directives
                                $(find PKG) and/or $(env VAR). Other special
                                characters such as '$' or ';' are not allowed.
            @type  args:        str

            @param name:        Name of the node under which the node should be
                                launched.
            @type  name:        str

            @param namespace:   Namespace in which the node should be started
                                in the environment.
            @type  namespace:   str
        """

    def removeNode(cTag, nTag):  #@NoSelf
        """ Remove a node from a container / ROS environment.

            @param cTag:        Tag which is used to identify the container /
                                ROS environment from which the node should be
                                removed.
            @type  cTag:        str

            @param nTag:        Tag which is used to identify the ROS node
                                which should removed.
            @type  nTag:        str
        """

    def addInterface(eTag, iTag, iType, clsName, addr=''):  #@NoSelf
        """ Add an interface to an endpoint, i.e. a ROS environment or a
            Robot object.

            @param eTag:        Tag which is used to identify the endpoint to
                                which the interface should be added; either
                                a container tag or robot ID.
            @type  eTag:        str

            @param iTag:        Tag which is used to identify the interface in
                                subsequent requests.
            @type  iTag:        str

            @param iType:       Type of the interface. The type consists of a
                                prefix and a suffix.
                                 - Valid prefixes are:
                                     ServiceClient, ServiceProvider,
                                     Publisher, Subscriber
                                 - Valid suffixes are:
                                     Interface, Converter, Forwarder
            @type  iType:       str

            @param clsName:     Message type/Service type consisting of the
                                package and the name of the message/service,
                                i.e. 'std_msgs/Int32'.
            @type  clsName:     str

            @param addr:        ROS name/address which the interface should
                                use. Only necessary if the suffix of @param
                                iType is 'Interface'.
            @type  addr:        str
        """

    def removeInterface(eTag, iTag):  #@NoSelf
        """ Remove an interface from an endpoint, i.e. a ROS environment or a
            Robot object.

            @param eTag:        Tag which is used to identify the endpoint from
                                which the interface should be removed; either
                                a container tag or robot ID.
            @type  eTag:        str

            @param iTag:        Tag which is used to identify the interface
                                which should be removed.
            @type  iTag:        str
        """

    def addParameter(cTag, name, value):  #@NoSelf
        """ Add a parameter to a container / ROS environment.

            @param cTag:        Tag which is used to identify the container /
                                ROS environment to which the parameter should
                                be added.
            @type  cTag:        str

            @param name:        Name of the parameter which should be added.
                                It is also used to identify the parameter in
                                subsequent requests.
            @type  name:        str

            @param value:       Value of the parameter which should be added.
                                Top-level string values can contain the
                                directives $(find PKG) and/or $(env VAR).
            @type  value:       str, int, float, bool, list
        """

    def removeParameter(cTag, name):  #@NoSelf
        """ Remove a parameter from a container / ROS environment.

            @param cTag:        Tag which is used to identify the container /
                                ROS environment from which the parameter should
                                be removed.
            @type  cTag:        str

            @param name:        Name of the parameter which should be removed.
            @type  name:        str
        """

    def addConnection(tagA, tagB):  #@NoSelf
        """ Create a connection between two interfaces.

            @param tagX:        Tag which is used to identify the interface
                                which should be connected. It has to be of the
                                form:
                                    [endpoint tag]/[interface tag]
                                For example:
                                    testRobot/logPublisher
            @type  tagX:        str
        """

    def removeConnection(tagA, tagB):  #@NoSelf
        """ Destroy a connection between two interfaces.

            @param tagX:        Tag which is used to identify the interface
                                which should be disconnected. It has to be of
                                the form:
                                    [endpoint tag]/[interface tag]
                                For example:
                                    testRobot/logPublisher
            @type  tagX:        str
        """


class IMessageReceiver(Interface):
    """ Interface which declares the necessary callback for the communication
        client/server.
    """
    def processReceivedMessage(iTag, clsName, msgID, msg):  #@NoSelf
        """ Process a data message which has been received from the server side.

            @param iTag:        Tag which is used to identify the interface to
                                which this message should be sent.
            @type  iTag:        str

            @param clsName:     Message type/Service type consisting of the
                                package and the name of the message/service,
                                i.e. 'std_msgs/Int32'.
            @type  clsName:     str

            @param msgID:       Message ID which can be used to get a
                                correspondence between request and response
                                message for a service call.
            @type  msgID:       str

            @param msg:         Message which should be sent. It has to be a
                                JSON compatible dictionary where part or the
                                complete message can be replaced by a StringIO
                                instance which is interpreted as binary data.
            @type  msg:         {str : {} / base_types / StringIO} / StringIO
        """


class IClient(IMessageReceiver):
    """ Interface which declares additional necessary callback for the
        communication on the client side.
    """
    def processInterfaceStatusUpdate(iTag, status): #@NoSelf
        """ Process a interface status update message received from the server
            side.

            @param iTag:        Tag which is used to identify the interface
                                which changed its status.
            @type  iTag:        str

            @param status:      Boolean indicating whether the interface should
                                be active or not.
            @type  status:      bool
        """

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-comm/rce/comm/server.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import json

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO  #@UnusedImport

# zope specific imports
from zope.interface import implements

# twisted specific imports
#from twisted.python import log
from twisted.python.failure import Failure
from twisted.cred.error import UnauthorizedLogin
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

# Autobahn specific imports
from autobahn import httpstatus
from autobahn.websocket import HttpException, \
    WebSocketServerFactory, WebSocketServerProtocol

# rce specific imports
from rce.comm import types
from rce.comm._version import MINIMAL_VERSION, CURRENT_VERSION
from rce.comm.error import InvalidRequest, DeadConnection
from rce.comm.assembler import recursiveBinarySearch, MessageAssembler
from rce.comm.interfaces import IMasterRealm, IRobotRealm, \
    IProtocol, IRobot, IMessageReceiver
from rce.util.interface import verifyObject


class _VersionError(Exception):
    """ Error is raised during Master-Robot authentication in case the used
        client version is insufficient.
    """


class RobotResource(Resource):
    """ Twisted web.Resource which is used in the Master to distribute new
        robots connections.
    """
    isLeaf = True

    def __init__(self, realm):
        """ Initialize the Robot resource.

            @param realm:       Master realm implementing necessary callback
                                methods.
            @type  realm:       rce.comm.interfaces.IMasterRealm
        """
        Resource.__init__(self)

        verifyObject(IMasterRealm, realm)
        self._realm = realm

    @classmethod
    def _render(cls, request, code, ctype, msg):
        """ Internally used method to render the response to a GET request.
        """
        request.setResponseCode(code)
        request.setHeader('content-type', ctype)
        request.write(msg)
        request.finish()

    @classmethod
    def _build_response(cls, addr, version, request):
        """ Internally used method to build the response to a GET request.
        """
        msg = {'url' : 'ws://{0}/'.format(addr)}

        if version < CURRENT_VERSION:
            msg['current'] = CURRENT_VERSION
        elif version > CURRENT_VERSION:
            # Should never happen; is already handled in render_GET
            raise ValueError

        cls._render(request, httpstatus.HTTP_STATUS_CODE_OK[0],
                    'application/json; charset=utf-8', json.dumps(msg))

    @classmethod
    def _handle_error(cls, e, request):
        """ Internally used method to process an error to a GET request.
        """
        if e.check(InvalidRequest):
            msg = e.getErrorMessage()
            code = httpstatus.HTTP_STATUS_CODE_BAD_REQUEST[0]
        else:
            e.printTraceback()
            msg = 'Fatal Error'
            code = httpstatus.HTTP_STATUS_CODE_INTERNAL_SERVER_ERROR[0]

        cls._render(request, code, 'text/plain; charset=utf-8', msg)

    def render_GET(self, request):
        """ This method is called by the twisted framework when a GET request
            was received.
        """
        # First check if the version is ok
        try:
            version = request.args['version']
        except KeyError:
            request.setResponseCode(httpstatus.HTTP_STATUS_CODE_BAD_REQUEST[0])
            request.setHeader('content-type', 'text/plain; charset=utf-8')
            return "Request is missing parameter: 'version'"

        if len(version) != 1:
            request.setResponseCode(httpstatus.HTTP_STATUS_CODE_BAD_REQUEST[0])
            request.setHeader('content-type', 'text/plain; charset=utf-8')
            return "Parameter 'version' has to be unique in request."

        version = version[0]

        if version < MINIMAL_VERSION:
            request.setResponseCode(httpstatus.HTTP_STATUS_CODE_GONE[0])
            request.setHeader('content-type', 'text/plain; charset=utf-8')
            return ('Client version is insufficient. Minimal version is '
                    "'{0}'.".format(MINIMAL_VERSION))
        elif version > CURRENT_VERSION:
            request.setResponseCode(httpstatus.HTTP_STATUS_CODE_NOT_IMPLEMENTED[0])
            request.setHeader('content-type', 'text/plain; charset=utf-8')
            return 'Client version is newer than version supported by server.'

        # Version is ok, now the GET request can be processed
        # Extract and check the arguments
        try:
            userID = request.args['userID']
        except KeyError:
            request.setResponseCode(httpstatus.HTTP_STATUS_CODE_BAD_REQUEST[0])
            request.setHeader('content-type', 'text/plain; charset=utf-8')
            return "Request is missing parameter: 'userID'"

        if len(userID) != 1:
            request.setResponseCode(httpstatus.HTTP_STATUS_CODE_BAD_REQUEST[0])
            request.setHeader('content-type', 'text/plain; charset=utf-8')
            return "Parameter 'userID' has to be unique in request."

        userID = userID[0]

        # Get the URL of a Robot process
        d = self._realm.requestURL(userID)
        d.addCallback(self._build_response, version, request)
        d.addErrback(self._handle_error, request)

        return NOT_DONE_YET


class RobotWebSocketProtocol(WebSocketServerProtocol):
    """ Protocol which is used for the connections from the robots to the
        robot manager.
    """
    implements(IProtocol)

    # CONFIG
    MSG_QUEUE_TIMEOUT = 60

    def __init__(self, realm):
        """ Initialize the Protocol.

            @param realm:       Robot realm implementing necessary callback
                                methods.
            @type  realm:       rce.comm.interfaces.IRobotRealm
        """
        verifyObject(IRobotRealm, realm)

        self._realm = realm
        self._assembler = MessageAssembler(self, self.MSG_QUEUE_TIMEOUT)
        self._avatar = None

    def onConnect(self, req):
        """ Method is called by the Autobahn engine when a request to establish
            a connection has been received.

            @param req:     Connection Request object.
            @type  req:     autobahn.websocket.ConnectionRequest

            @return:        Deferred which fires callback with None or errback
                            with autobahn.websocket.HttpException
        """
        params = req.params

        try:
            userID = params['userID']
            robotID = params['robotID']
            password = params['password']
        except KeyError as e:
            raise HttpException(httpstatus.HTTP_STATUS_CODE_BAD_REQUEST[0],
                                'Request is missing parameter: {0}'.format(e))

        for name, param in [('userID', userID), ('robotID', robotID),
                            ('password', password)]:
            if len(param) != 1:
                raise HttpException(httpstatus.HTTP_STATUS_CODE_BAD_REQUEST[0],
                                    "Parameter '{0}' has to be unique in "
                                    'request.'.format(name))

        d = self._realm.login(userID[0], robotID[0], password[0])
        d.addCallback(self._authenticate_success)
        d.addErrback(self._authenticate_failed)
        return d

    def _authenticate_success(self, avatar):
        """ Method is called by deferred when the connection has been
            successfully authenticated while being in 'onConnect'.
        """
        verifyObject(IRobot, avatar)
        verifyObject(IMessageReceiver, avatar)

        self._realm.registerWebsocketProtocol(avatar, self)
        self._avatar = avatar
        self._assembler.start()

    def _authenticate_failed(self, e):
        """ Method is called by deferred when the connection could not been
            authenticated while being in 'onConnect'.
        """
        if e.check(InvalidRequest):
            code = httpstatus.HTTP_STATUS_CODE_BAD_REQUEST[0]
            msg = e.getErrorMessage()
        elif e.check(UnauthorizedLogin):
            code = httpstatus.HTTP_STATUS_CODE_UNAUTHORIZED[0]
            msg = httpstatus.HTTP_STATUS_CODE_UNAUTHORIZED[1]
        else:
            e.printTraceback()
            code = httpstatus.HTTP_STATUS_CODE_INTERNAL_SERVER_ERROR[0]
            msg = httpstatus.HTTP_STATUS_CODE_INTERNAL_SERVER_ERROR[1]

        return Failure(HttpException(code, msg))

    def processCompleteMessage(self, msg):
        """ Process complete messages by calling the appropriate handler for
            the manager. (Called by rce.comm.assembler.MessageAssembler)
        """
        try:
            msgType = msg['type']
            data = msg['data']
        except KeyError as e:
            raise InvalidRequest('Message is missing key: {0}'.format(e))

        if msgType == types.DATA_MESSAGE:
            self._process_DataMessage(data)
        elif msgType == types.CONFIGURE_COMPONENT:
            self._process_configureComponent(data)
        elif msgType == types.CONFIGURE_CONNECTION:
            self._process_configureConnection(data)
        elif msgType == types.CREATE_CONTAINER:
            self._process_createContainer(data)
        elif msgType == types.DESTROY_CONTAINER:
            self._process_destroyContainer(data)
        else:
            raise InvalidRequest('This message type is not supported.')

    def _process_createContainer(self, data):
        """ Internally used method to process a request to create a container.
        """
        try:
            self._avatar.createContainer(data['containerTag'],
                                         data.get('containerData', {}))
        except KeyError as e:
            raise InvalidRequest("Can not process 'CreateContainer' request. "
                                 'Missing key: {0}'.format(e))

    def _process_destroyContainer(self, data):
        """ Internally used method to process a request to destroy a container.
        """
        try:
            self._avatar.destroyContainer(data['containerTag'])
        except KeyError as e:
            raise InvalidRequest("Can not process 'DestroyContainer' request. "
                                 'Missing key: {0}'.format(e))

    def _process_configureComponent(self, data):
        """ Internally used method to process a request to configure
            components.
        """
        for node in data.pop('addNodes', []):
            try:
                self._avatar.addNode(node['containerTag'],
                                     node['nodeTag'],
                                     node['pkg'],
                                     node['exe'],
                                     node.get('args', ''),
                                     node.get('name', ''),
                                     node.get('namespace', ''))
            except KeyError as e:
                raise InvalidRequest("Can not process 'ConfigureComponent' "
                                     "request. 'addNodes' is missing key: "
                                     '{0}'.format(e))

        for node in data.pop('removeNodes', []):
            try:
                self._avatar.removeNode(node['containerTag'],
                                        node['nodeTag'])
            except KeyError as e:
                raise InvalidRequest("Can not process 'ConfigureComponent' "
                                     "request. 'removeNodes' is missing key: "
                                     '{0}'.format(e))

        for conf in data.pop('addInterfaces', []):
            try:
                self._avatar.addInterface(conf['endpointTag'],
                                          conf['interfaceTag'],
                                          conf['interfaceType'],
                                          conf['className'],
                                          conf.get('addr', ''))
            except KeyError as e:
                raise InvalidRequest("Can not process 'ConfigureComponent' "
                                     "request. 'addInterfaces' is missing "
                                     'key: {0}'.format(e))

        for conf in data.pop('removeInterfaces', []):
            try:
                self._avatar.removeInterface(conf['endpointTag'],
                                             conf['interfaceTag'])
            except KeyError as e:
                raise InvalidRequest("Can not process 'ConfigureComponent' "
                                     "request. 'removeInterfaces' is missing "
                                     'key: {0}'.format(e))

        for param in data.pop('setParam', []):
            try:
                self._avatar.addParameter(param['containerTag'],
                                          param['name'],
                                          param['value'])
            except KeyError as e:
                raise InvalidRequest("Can not process 'ConfigureComponent' "
                                     "request. 'setParam' is missing key: "
                                     '{0}'.format(e))

        for param in data.pop('deleteParam', []):
            try:
                self._avatar.removeParameter(param['containerTag'],
                                             param['name'])
            except KeyError as e:
                raise InvalidRequest("Can not process 'ConfigureComponent' "
                                     "request. 'deleteParam' is missing key: "
                                     '{0}'.format(e))

    def _process_configureConnection(self, data):
        """ Internally used method to process a request to configure
            connections.
        """
        for conf in data.pop('connect', []):
            try:
                self._avatar.addConnection(conf['tagA'], conf['tagB'])
            except KeyError as e:
                raise InvalidRequest("Can not process 'ConfigureComponent' "
                                     "request. 'connect' is missing key: "
                                     '{0}'.format(e))

        for conf in data.pop('disconnect', []):
            try:
                self._avatar.removeConnection(conf['tagA'], conf['tagB'])
            except KeyError as e:
                raise InvalidRequest("Can not process 'ConfigureComponent' "
                                     "request. 'disconnect' is missing key: "
                                     '{0}'.format(e))

    def _process_DataMessage(self, data):
        """ Internally used method to process a data message.
        """
        try:
            iTag = str(data['iTag'])
            mType = str(data['type'])
            msgID = str(data['msgID'])
            msg = data['msg']
        except KeyError as e:
            raise InvalidRequest("Can not process 'DataMessage' request. "
                                 'Missing key: {0}'.format(e))

        if len(msgID) > 255:
            raise InvalidRequest("Can not process 'DataMessage' request. "
                                 'Message ID can not be longer than 255.')

        self._avatar.processReceivedMessage(iTag, mType, msgID, msg)

    def onMessage(self, msg, binary):
        """ Method is called by the Autobahn engine when a message has been
            received from the client.

            @param msg:         Message which was received as a string.
            @type  msg:         str

            @param binary:      Flag which is True if the message has binary
                                format and False otherwise.
            @type  binary:      bool
        """
#        print('WebSocket: Received new message from client. '
#              '(binary={0})'.format(binary))

        try:
            self._assembler.processMessage(msg, binary)
        except InvalidRequest as e:
            self.sendErrorMessage('Invalid Request: {0}'.format(e))
        except DeadConnection:
            self.sendErrorMessage('Dead Connection')
            self.dropConnection()
        except:
            import traceback
            traceback.print_exc()
            self.sendErrorMessage('Fatal Error')

    def sendMessage(self, msg):
        """ Internally used method to send a message to the robot.

            Should not be used from outside the Protocol; instead use the
            methods 'sendDataMessage' or 'sendErrorMessage'.

            (Overwrites method from autobahn.websocket.WebSocketServerProtocol)

            @param msg:     Message which should be sent.
        """
        uriBinary, msgURI = recursiveBinarySearch(msg)

        WebSocketServerProtocol.sendMessage(self, json.dumps(msgURI))

        for binData in uriBinary:
            WebSocketServerProtocol.sendMessage(self,
                binData[0] + binData[1].getvalue(), binary=True)

    def sendDataMessage(self, iTag, clsName, msgID, msg):
        """ Callback for Connection object to send a data message to the robot
            using this WebSocket connection.

            @param iTag:        Tag which is used to identify the interface
                                from the message is sent.
            @type  iTag:        str

            @param clsName:     Message type/Service type consisting of the
                                package and the name of the message/service,
                                i.e. 'std_msgs/Int32'.
            @type  clsName:     str

            @param msgID:       Message ID which can be used to get a
                                correspondence between request and response
                                message for a service call.
            @type  msgID:       str

            @param msg:         Message which should be sent. It has to be a
                                JSON compatible dictionary where part or the
                                complete message can be replaced by a StringIO
                                instance which is interpreted as binary data.
            @type  msg:         {str : {} / base_types / StringIO} / StringIO
        """
        self.sendMessage({'type' : types.DATA_MESSAGE,
                          'data' : {'iTag' : iTag, 'type' : clsName,
                                    'msgID' : msgID, 'msg' : msg}})

    def sendInterfaceStatusUpdateMessage(self, iTag, status):
        """ Callback for Connection object to send a interface status message to
            the robot using this WebSocket connection.

            @param iTag:        Tag which is used to identify the interface
                                which changed its status.
            @type  iTag:        str

            @param status:      Boolean indicating whether the interface should
                                be active or not.
            @type  status:      bool
        """
        self.sendMessage({'type' : types.STATUS,
                          'data' : {'topic' : types.STATUS_INTERFACE,
                                    'iTag' : iTag, 'status' : status}})

    def sendErrorMessage(self, msg):
        """ Callback for Connection object to send an error message to the robot
            using this WebSocket connection.

            @param msg:         Message which should be sent to the robot.
            @type  msg:         str
        """
        self.sendMessage({'type' : types.ERROR, 'data' : msg})

    def onClose(self, wasClean, code, reason):
        """ Method is called by the Autobahn engine when the connection has
            been lost.
        """
        if self._avatar:
            self._realm.unregisterWebsocketProtocol(self._avatar, self)

        self._assembler.stop()

        self._avatar = None
        self._assembler = None


class CloudEngineWebSocketFactory(WebSocketServerFactory):
    """ Factory which is used for the connections from the robots to the
        RoboEarth Cloud Engine.
    """
    def __init__(self, realm, url, **kw):
        """ Initialize the Factory.

            @param realm:       Robot realm implementing necessary callback
                                methods for the protocol.
            @type  realm:       rce.comm.interfaces.IRobotRealm

            @param url:         URL where the WebSocket server factory will
                                listen for connections. For more information
                                refer to the base class:
                                    autobahn.websocket.WebSocketServerFactory
            @type  url:         str

            @param kw:          Additional keyworded arguments will be passed
                                to the __init__ of the base class.
        """
        WebSocketServerFactory.__init__(self, url, **kw)

        self._realm = realm

    def buildProtocol(self, addr):
        """ Method is called by the twisted reactor when a new connection
            attempt is made.
        """
        p = RobotWebSocketProtocol(self._realm)
        p.factory = self
        return p

########NEW FILE########
__FILENAME__ = types
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-comm/rce/comm/types.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

""" Message Types of RCE Client Protocol:

        CC      Create a container
        DC      Destroy a container

        CN      Change a (ROS) component (Node, Parameter, Interface)
        CX      Change connections between Interfaces

        DM      ROS Message

        ST      Status message
        ER      Error message


    Content Types of RCE Client Status Messages (ST):

        iu      Interface status update
"""

CREATE_CONTAINER = 'CC'
DESTROY_CONTAINER = 'DC'

CONFIGURE_COMPONENT = 'CN'
CONFIGURE_CONNECTION = 'CX'

DATA_MESSAGE = 'DM'

STATUS = 'ST'
ERROR = 'ER'

STATUS_INTERFACE = 'iu'

########NEW FILE########
__FILENAME__ = _version
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-comm/rce/comm/_version.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

CURRENT_VERSION = '20130902'
MINIMAL_VERSION = '20130415'

########NEW FILE########
__FILENAME__ = console
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-console/rce/console/console.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Mayank Singh
#
#

# Python specific imports
import sys
import os
import termios
import tty
import json
import getopt
from urllib import urlencode
from urllib2 import urlopen, HTTPError
from hashlib import sha256

# twisted specific imports
from twisted.python import usage
from twisted.python.log import err, startLogging
from twisted.cred.credentials import UsernamePassword
from twisted.internet import reactor
from twisted.internet import stdio
from twisted.spread.pb import PBClientFactory
from twisted.conch.recvline import HistoricRecvLine
from twisted.conch.insults.insults import ServerProtocol


class CustomOptions(usage.Options):
    """ Custom Class to override functionality of usage.Options
    """
    def __init__(self, terminal):
        """ Initialize the CustomOptions Class

            @param terminal:    Reference to the running terminal
            @type  terminal:    ConsoleClient.terminal
        """
        super(CustomOptions, self).__init__()
        self.longdesc = ""
        self.terminal = terminal

    def parseOptions(self, options=None):
        """
        The guts of the command-line parser.
        """
        if options is None:
            options = sys.argv[1:]

        try:
            opts, args = getopt.getopt(options, self.shortOpt, self.longOpt)
        except getopt.error as e:
            raise usage.UsageError(str(e))

        for opt, arg in opts:
            if opt[1] == '-':
                opt = opt[2:]
            else:
                opt = opt[1:]

            optMangled = opt
            if optMangled not in self.synonyms:
                optMangled = opt.replace("-", "_")
                if optMangled not in self.synonyms:
                    raise usage.UsageError("No such option '{0}'".format(opt))

            optMangled = self.synonyms[optMangled]
            if isinstance(self._dispatch[optMangled], usage.CoerceParameter):
                self._dispatch[optMangled].dispatch(optMangled, arg)
            else:
                self._dispatch[optMangled](optMangled, arg)

        if (getattr(self, 'subCommands', None)
            and (args or self.defaultSubCommand is not None)):
            if not args:
                args = [self.defaultSubCommand]
            sub, rest = args[0], args[1:]
            for (cmd, short, parser, _) in self.subCommands:
                if sub == cmd or sub == short:
                    self.subCommand = cmd
                    self.subOptions = parser(self.terminal)
                    self.subOptions.parent = self
                    self.subOptions.parseOptions(rest)
                    break
            else:
                raise usage.UsageError("Unknown command: {0}".format(sub))
        else:
            try:
                self.parseArgs(*args)
            except TypeError:
                raise usage.UsageError("Wrong number of arguments.")

        self.postOptions()

    def getSynopsis(self):
        """
        Returns a string containing a description of these options and how to
        pass them to the executed file.
        """

        if self.parent is None:
            command = self.__class__.__name__
            offset = command.find('Options')
            default = "Usage: {0}{1}".format(command[:offset],
                                       (self.longOpt and " [options]") or '')
        else:
            default = (self.longOpt and " [options]") or ''

        synopsis = getattr(self, "synopsis", default).rstrip()

        if self.parent is not None:
            synopsis = ' '.join((self.parent.getSynopsis(),
                                 self.parent.subCommand, synopsis))

        return synopsis

    def opt_help(self):
        """help option"""
        self.terminal.write(self.__str__())

    def opt_version(self):
        self.terminal.write('vestigial option')


# Various Option Classes follow
class UserAddOptions(CustomOptions):
    """
        Parameters for user add.
    """
    optParameters = (
        ("username", "u", None, "Username"),
        ("password", "p", None, "Password"),
    )


class UserRemoveOptions(CustomOptions):
    """
        Parameters for user remove.
    """
    optParameters = (
        ("username", "u", None, "Username"),
    )


class UserUpdateOptions(CustomOptions):
    """
        Parameters for user update.
    """
    optParameters = (
        ("username", "u", None, "Username"),
        ("password", "p", None, "New Password"),
    )

class UserChangePasswordOptions(CustomOptions):
    """
        Parameters for changing password by a non-admin.
    """
    optParameters = (
        ("new", "p", None, "New Password"),
        ("old", "o", None, "Old Password"),
    )

class UserOptions(CustomOptions):
    """
        Options for user command.
    """
    subCommands = (
        ('add', None, UserAddOptions, "Add User"),
        ('remove', None, UserRemoveOptions, "Remove User"),
        ('update', None, UserUpdateOptions, "Update User"),
        ('passwd', None, UserChangePasswordOptions, "Change Password"),
    )
    optFlags = (
        ("list", "l", "List all Users"),
    )


class ContainerStartOptions(CustomOptions):
    """
        Parameters for container start.
    """
    optParameters = (
        ("name", "n", None , "Container Name"),
        ("group", "g", None, "Container Group"),
        ("groupIp", "a", None , "Container Group IPv4 address"),
        ("size", "s", None , "Container Size"),
        ("cpu", "c", None , "CPU options"),
        ("memory", "m", None , "memory options"),
        ("bandwidth", "b", None , "Bandwidth options"),
        ("specialopts", "o", None , "Special features options"),
    )


class ContainerOptions(CustomOptions):
    """
        Options for container command.
    """
    optParameters = (
        ("stop", "t", None, "Stop a Container"),
        ("services", "v", None, "List services running on the container"),
        ("topics", "o", None, "List topics running on the container"),
        ("username", "u", None, "List containers by username"),
    )
    optFlags = (
        ("list", "l", "List all containers of the user logged in"),
    )

    subCommands = (
        ("start", None, ContainerStartOptions, "Start a Container"),
    )


class NodeStartOptions(CustomOptions):
    """
        Parameters for node start.
    """
    optParameters = (
        ("ctag", "c", None, "Container tag"),
        ("ntag", "n", None, "Node tag"),
        ("pkg", "p", None, "Package"),
        ("exe", "e", None, "Executable"),
        ("args", "a", None, "Arguments"),
    )


class NodeStopOptions(CustomOptions):
    """
        Parameters for node stop.
    """
    optParameters = (
        ("ctag", "c", None, "Container tag"),
        ("ntag", "n", None, "Node tag"),
    )


class NodeOptions(CustomOptions):
    """
        Options for node command.
    """
    subCommands = (
        ('start', None, NodeStartOptions, "Start Node"),
        ('stop', None, NodeStopOptions, "Stop Node"),
    )


class ParameterAddOptions(CustomOptions):
    """
        Parameters for adding ROS parameters.
    """
    optParameters = (
        ("ctag", "c", None, "Container tag"),
        ("name", "n", None, "Name of parameter"),
        ("value", "v", None, "Value of parameter"),
    )


class ParameterRemoveOptions(CustomOptions):
    """
        Parameters for removing ROS parameters.
    """
    optParameters = (
        ("ctag", "c", None, "Container tag"),
        ("name", "n", None, "Name of parameter"),
    )


class ParameterOptions(CustomOptions):
    """
        Options for parameter command.
    """
    subCommands = (
        ('add', None, ParameterAddOptions, 'Add parameter'),
        ('remove', None, ParameterRemoveOptions, 'Remove parameter'),
    )


class InterfaceAddOptions(CustomOptions):
    """
        Parameters for adding interfaces.
    """
    optParameters = (
        ("etag", "e", None, "Endpoint tag"),
        ("itag", "i", None, "Interface tag"),
        ("itype", "t", None, "Interface type"),
        ("icls", "c", None, "Interface Class"),
        ("addr", "a", None, "Address"),
    )


class InterfaceRemoveOptions(CustomOptions):
    """
        Parameters for removing interfaces.
    """
    optParameters = (
        ("etag", "e", None, "Endpoint tag"),
        ("itag", "i", None, "Interface tag"),
    )


class InterfaceOptions(CustomOptions):
    """
        Options for interface command.
    """
    subCommands = (
        ('add', None, InterfaceAddOptions, 'Add interface'),
        ('remove', None, InterfaceRemoveOptions, 'Remove interface'),
    )


class ConnectionSubOptions(CustomOptions):
    """
        Sub options for connection subcommands.
    """
    optParameters = (
        ("tag1", "1", None, "First Interface"),
        ("tag2", "2", None, "Second Interface"),
    )


class ConnectionOptions(CustomOptions):
    """
        Options for connection command.
    """
    subCommands = (
        ('add', None, ConnectionSubOptions, 'Connect Interfaces'),
        ('remove', None, ConnectionSubOptions, 'Disconnect Interfaces'),
    )


class RobotOptions(CustomOptions):
    """
        Options for robot command.
    """
    optParameters = (
        ("username", "u", None, "List Robots by Username"),
    )
    optFlags = (
        ("list", "l", "List all Robots"),
    )


class MachineOptions(CustomOptions):
    """
        Options for machine command.
    """
    optParameters = (
        ("stats", "s", None, "Statistics of Machine by IP"),
        ("containers", "c", None, "List Containers by Machine's IP"),
    )
    optFlags = (
        ("list", "l", "List all Machines"),
    )


def _errorHandle(func):
        def call(self, *args, **kwargs):
            try:
                func(self, *args, **kwargs)
            except AttributeError:
                self.terminal.write("Cannot use that command.")
        return call


class ConsoleClient(HistoricRecvLine):
    """ The class creates the terminal and manages connections with Master
        and ROSAPI servers on specific containers
    """
    def __init__(self, masterIP, consolePort):
        """ Initialize the ConsoleClient.

            @param masterIP:        The IP of the master server
            @type  masterIP:        string

            @param consolePort:     Port of the master server
            @type  consolePort:     int
        """
        self._user = None
        self._masterIP = masterIP
        self._console_port = consolePort
        self._mode = "Username"
        self._username = None
        self._password = None
        self._factory = None
        self._connected_rosapi_nodes = {}
        self._privilege = None

    def showPrompt(self):
        """ Show the prompt >>>
        """
        self.terminal.nextLine()
        self.terminal.write(self.ps[self.pn])

    def connectionMade(self):
        """ Create a PBClientFactory and connect to master when ConsoleClient
            connected to StandardIO. Prompt user for Username
        """
        HistoricRecvLine.connectionMade(self)
        self._factory = PBClientFactory()

        reactor.connectTCP(self._masterIP, self._console_port, self._factory)  #@UndefinedVariable
        self.terminal.write("Username: ")

    def lineReceived(self, line):
        """ Manage state/mode after connection. Code uses states to take
            credential input and then starts terminal input.

            @param line:    line typed on terminal
            @type  line:    string
        """
        def _cbError(why, msg):
            err(why, msg)
            reactor.stop()  #@UndefinedVariable

        def _cbConnectionSuccess(view):
            self._user = view

            if isinstance(self._user, dict):
                self._privilege = 'console'
            else:
                self._privilege = 'admin'

            self.terminal.write('Connection to Master Established.')
            self.showPrompt()

        if self._mode == 'Username':
            self._mode = 'Password'
            self._username = line
            self.terminal.write('Password: ')
        elif self._mode == 'Password':
            self._mode = 'Terminal'
            self._password = line
            cred = UsernamePassword(self._username,
                                    sha256(self._password).hexdigest())
            d = self._factory.login(cred)
            d.addCallback(lambda p: p.callRemote("getUserView", True))
            d.addCallback(_cbConnectionSuccess)
            d.addErrback(_cbError, "Username/password login failed")
        else:
            self.parseInputLine(line)

    def parseInputLine(self, line):
        """ A function to route various commands entered via Console.

            @param line:    The text entered on the Console
            @type  line:    string
        """
        if line is not None and line is not '':
            func = getattr(self, 'cmd_' + line.split()[0].upper(), None)
            if func is not None:
                func(line.split()[1:])
            else:
                self.terminal.write('No such command')
        self.showPrompt()

    @_errorHandle
    def callToRosProxy(self, command, parameter):
        """ Function to handle call to ROSAPI Proxy Server.

            @param command:      The command to execute in ROS environment.
            @type  command:      string

            @param parameter:    A parameter for the command.
            @type  parameter:    string
        """
        def perform_action((url, key)):
            self._connected_rosapi_nodes[parameter] = (url, key)
            argList = [('userID', self._username), ('action', command),
                       ('key', key)]

            try:
                f = urlopen('{0}?{1}'.format(url, urlencode(argList)))
                response = json.loads(f.read())
                self.terminal.write(str(response['key']))
            except HTTPError as e:
                msg = e.read()
                if msg:
                    msg = ' - {0}'.format(msg)

                self.terminal.write('HTTP Error {0}: '
                                    '{1}{2}'.format(e.getcode(), e.msg, msg))

        try:
            url, key = self._connected_rosapi_nodes[parameter]
            perform_action((url, key))
        except KeyError:
            d = self._user['console'].callRemote('get_rosapi_connect_info',
                                                 parameter)
            d.addCallback(perform_action)
            d.addErrback(lambda err: self.terminal.write("Problem "
                                "in connection with master: "
                                "{0}".format(err)))

    @_errorHandle
    def callToUser(self, command, domain, *args):
        """ A wrapper function for call to remote user.

            @param command:    The command to be executed
            @type  command:    string
        """
        if domain == 'admin':
            self._user.callRemote(command, *args)
        else:
            self._user[domain].callRemote(command, *args)

    @_errorHandle
    def callToUserAndDisplay(self, command, domain, *args):
        """ A wrapper function around call to user and displaying the result

            @param command:    The command to be executed
            @type  command:    string
        """
        if domain == 'admin':
            d = self._user.callRemote(command, *args)
            d.addCallback(lambda result: self.terminal.write(str(result)))
        else:
            d = self._user[domain].callRemote(command, *args)
            d.addCallback(lambda result: self.terminal.write(str(result)))

    # Various commands follow
    def cmd_EXIT(self, line):
        """ Handler for exit command.

            @param line:    line input from terminal.
            @type  line:    string
        """
        reactor.stop()  # @UndefinedVariable

    def cmd_USER(self, line):
        """ Handler for user command.

            @param line:    line input from terminal.
            @type  line:    string
        """
        config = UserOptions(self.terminal)

        try:
            config.parseOptions(line)
            cmd = config.subCommand
            opts = config.subOptions if hasattr(config, 'subOptions') else {}
        except usage.UsageError as errortext:
            self.terminal.write("BUG in usage: {0}".format(errortext))
        else:
            if cmd == 'add':
                if opts['username'] and opts['password']:
                    self.callToUser('add_user', 'admin', opts['username'],
                                    opts['password'])
            elif cmd == 'remove':
                if opts['username']:
                    self.callToUser('remove_user', 'admin', opts['username'])
            elif cmd == 'update':
                if opts['username'] and opts['password']:
                    self.callToUser('update_user', 'admin',
                                    opts['username'], opts['password'])
            elif cmd == 'passwd':
                if opts['new'] and opts['old']:
                    self.callToUser('update_user', 'console', opts['new'],
                                    opts['old'])
            elif config['list']:
                self.callToUserAndDisplay('list_users', 'admin')

    def cmd_CONTAINER(self, line):
        """ Handler for container command.

            @param line:    line input from terminal.
            @type  line:    string
        """
        config = ContainerOptions(self.terminal)

        try:
            config.parseOptions(line)
            cmd = config.subCommand
            opts = config.subOptions if hasattr(config, 'subOptions') else {}
        except usage.UsageError as errortext:
            self.terminal.write("BUG in usage: {0}".format(errortext))
        else:
            if cmd == 'start':
                if (opts['name']):
                    data = {}
                    if opts.get('group'):
                        data['group'] = opts['group']
                    if opts.get('groupIp'):
                        data['groupIp'] = opts['groupIp']
                    if opts.get('size'):
                        data['size'] = opts['size']
                    if opts.get('bandwidth'):
                        data['bandwidth'] = opts['bandwidth']
                    if opts.get('memory'):
                        data['memory'] = opts['memory']
                    if opts.get('specialopts'):
                        data['specialFeatures'] = opts['specialopts']
                    self.callToUser('createContainer', 'robot', opts['name'],
                                    data)

            elif config['stop']:
                self.callToUser('destroyContainer', 'robot', config['stop'])
            elif config['services']:
                self.callToRosProxy('services', config['services'])
            elif config['topics']:
                self.callToRosProxy('topics', config['topics'])
            elif config['list']:
                self.callToUserAndDisplay('list_containers', 'console')
            elif config['username']:
                self.callToUserAndDisplay('list_containers_by_user', 'admin',
                                          config['username'])

    def cmd_NODE(self, line):
        """ Handler for node command.

            @param line:    line input from terminal.
            @type  line:    string
        """
        config = NodeOptions(self.terminal)

        try:
            config.parseOptions(line)
            cmd = config.subCommand
            opts = config.subOptions if hasattr(config, 'subOptions') else {}
        except usage.UsageError as errortext:
            self.terminal.write("BUG in usage: {0}".format(errortext))
        else:
            if cmd == 'start':
                if (opts['args'] and opts['ctag'] and opts['ntag']
                    and opts['pkg'] and opts['exe']):
                    self.callToUser('addNode', 'robot', opts['ctag'],
                                    opts['ntag'], opts['pkg'], opts['exe'],
                                    opts['args'])
                elif (opts['ctag'] and opts['ntag']  and opts['pkg']
                      and opts['exe']):
                    self.callToUser('addNode', 'robot', opts['ctag'],
                                    opts['ntag'], opts['pkg'], opts['exe'])
            elif cmd == 'stop':
                if opts['ctag'] and opts['ntag']:
                    self.callToUser('removeNode', 'robot', opts['ctag'],
                                    opts['ntag'])

    def cmd_PARAMETER(self, line):
        """ Handler for parameter command.

            @param line:    line input from terminal.
            @type  line:    string
        """
        config = ParameterOptions(self.terminal)

        try:
            config.parseOptions(line)
            cmd = config.subCommand
            opts = config.subOptions if hasattr(config, 'subOptions') else {}
        except usage.UsageError as errortext:
            self.terminal.write("BUG in usage: {0}".format(errortext))
        else:
            if cmd == 'add':
                if opts['ctag'] and opts['name'] and opts['value']:
                    self.callToUser('addParameter', 'robot', opts['ctag'],
                                    opts['name'], opts['value'])
            elif cmd == 'remove':
                if opts['ctag'] and opts['name']:
                    self.callToUser('removeParameter', 'robot', opts['ctag'],
                                    opts['name'])

    def cmd_INTERFACE(self, line):
        """ Handler for interface command.

            @param line:    line input from terminal.
            @type  line:    string
        """
        config = InterfaceOptions(self.terminal)

        try:
            config.parseOptions(line)
            cmd = config.subCommand
            opts = config.subOptions if hasattr(config, 'subOptions') else {}
        except usage.UsageError as errortext:
            self.terminal.write("BUG in usage: {0}".format(errortext))
        else:
            if cmd == 'add':
                if (opts['addr'] and opts['etag'] and opts['itag']
                    and opts['itype'] and opts['icls']):
                    self.callToUser('addInterface', 'robot', opts['etag'],
                                    opts['itag'], opts['itype'], opts['icls'],
                                    opts['addr'])
                elif (opts['etag'] and opts['itag'] and opts['itype'] and
                      opts['icls']):
                    self.callToUser('addInterface', 'robot', opts['etag'],
                                    opts['itag'], opts['itype'], opts['icls'])
            elif cmd == 'remove':
                if opts['etag'] and opts['itag']:
                    self.callToUser('removeInterface', 'robot', opts['etag'],
                                    opts['itag'])

    def cmd_CONNECTION(self, line):
        """ Handler for connection command.

            @param line:    line input from terminal.
            @type  line:    string
        """
        config = ConnectionOptions(self.terminal)

        try:
            config.parseOptions(line)
            cmd = config.subCommand
            opts = config.subOptions if hasattr(config, 'subOptions') else {}
        except usage.UsageError as errortext:
            self.terminal.write("BUG in usage: {0}".format(errortext))
        else:
            if cmd == 'add':
                if opts['tag1'] and opts['tag2']:
                    self.callToUser('addConnection', 'robot', opts['tag1'],
                                    opts['tag2'])
            elif cmd == 'remove':
                if opts['tag1'] and opts['tag2']:
                    self.callToUser('removeConnection', 'robot', opts['tag1'],
                                    opts['tag2'])

    def cmd_ROBOT(self, line):
        """ Handler for robot command.

            @param line:    line input from terminal.
            @type  line:    string
        """
        config = RobotOptions(self.terminal)
        try:
            config.parseOptions(line)
        except usage.UsageError as errortext:
            self.terminal.write("BUG in usage: {0}".format(errortext))
        else:
            if config['list']:
                self.callToUserAndDisplay('list_robots', 'console')
            elif config['username']:
                self.callToUserAndDisplay('list_robots_by_user', 'admin',
                                          config['username'])

    def cmd_MACHINE(self, line):
        """ Handler for machine command.

            @param line:    line input from terminal.
            @type  line:    string
        """
        config = MachineOptions(self.terminal)
        try:
            config.parseOptions(line)
        except usage.UsageError as errortext:
            self.terminal.write("BUG in usage: {0}".format(errortext))
        else:
            if config['list']:
                self.callToUserAndDisplay('list_machines', 'admin')
            elif config['stats']:
                self.callToUserAndDisplay('stats_machine', 'admin',
                                          config['stats'])
            elif config['containers']:
                self.callToUserAndDisplay('machine_containers', 'admin',
                                          config['containers'])

    def cmd_HELP(self, line):
        """ Handler for help command.

            @param line:    line input from terminal.
            @type  line:    string
        """
        configs = [UserOptions(self.terminal), ContainerOptions(self.terminal),
                   NodeOptions(self.terminal), ParameterOptions(self.terminal),
                   InterfaceOptions(self.terminal),
                   ConnectionOptions(self.terminal),
                   RobotOptions(self.terminal), MachineOptions(self.terminal)]

        for config in configs:
            self.terminal.nextLine()
            config.opt_help()


def runWithProtocol(klass, masterIP, port):
    """ Function overridden from twisted.conch.stdio to allow Ctrl+C interrupt

        @param klass:     A callable which will be invoked with
                          *a, **kw and should return an ITerminalProtocol
                          implementor. This will be invoked when a connection
                          to this ServerProtocol is established.

        @param masterIP:  IP of the master server.
        @type  masterIP:  string
    """
    fd = sys.stdin.fileno()
    oldSettings = termios.tcgetattr(fd)
    tty.setcbreak(fd)

    try:
        p = ServerProtocol(klass, masterIP, port)
        stdio.StandardIO(p)
        reactor.run()  #@UndefinedVariable
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, oldSettings)
        os.write(fd, "\r\x1bc\r")


def main(ip, port):
    startLogging(sys.stdout)
    runWithProtocol(ConsoleClient, ip, port)

########NEW FILE########
__FILENAME__ = container
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/container.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import os
import sys
import stat
import shutil
from random import choice
from string import letters

try:
    import pkg_resources
except ImportError:
    print("Can not import the package 'pkg_resources'.")
    exit(1)

pjoin = os.path.join
load_resource = pkg_resources.resource_string  #@UndefinedVariable

try:
    import iptc
except ImportError:
    print("Can not import the package 'python-iptables'.")
    print('    see: http://github.com/ldx/python-iptables')
    exit(1)

# twisted specific imports
from twisted.python import log
from twisted.internet.defer import  DeferredList, succeed
from twisted.spread.pb import Referenceable, PBClientFactory, \
    DeadReferenceError, PBConnectionLost

# rce specific imports
from rce.util.error import InternalError
from rce.util.container import Container
from rce.util.cred import salter, encodeAES, cipher
from rce.util.network import isLocalhost
from rce.util.process import execute
from rce.core.error import MaxNumberExceeded
# from rce.util.ssl import createKeyCertPair, loadCertFile, loadKeyFile, \
#    writeCertToFile, writeKeyToFile


# Helper function to generate random strings
randomString = lambda length: ''.join(choice(letters) for _ in xrange(length))


_UPSTART_COMM = load_resource('rce.core', 'data/comm.upstart')
# _UPSTART_LAUNCHER = load_resource('rce.core', 'data/launcher.upstart')
_UPSTART_ROSAPI = load_resource('rce.core', 'data/rosapi.upstart')
_LXC_NETWORK_SCRIPT = load_resource('rce.core', 'data/lxc-network.script')


def passthrough(f):
    """ Decorator which is used to add a function as a Deferred callback and
        passing the input unchanged to the output.

        @param f:           Function which should be decorated.
        @type  f:           callable
    """
    def wrapper(response):
        f()
        return response

    return wrapper


class RCEContainer(Referenceable):
    """ Container representation which is used to run a ROS environment.
    """
    def __init__(self, client, nr, uid, data):
        """ Initialize the deployment container.

            @param client:      Container client which is responsible for
                                monitoring the containers in this machine.
            @type  client:      rce.container.ContainerClient

            @param nr:          Unique number which will be used for the IP
                                address and the hostname of the container.
            @type  nr:          int

            @param uid:         Unique ID which is used by the environment
                                process to login to the Master.
            @type  uid:         str

            @param data:        Extra data used to configure the container.
            @type  data:        dict
        """
        self._client = client
        self._nr = nr
        self._name = name = 'C{0}'.format(nr)
        self._terminating = None

        # Additional container parameters to use
        # TODO: At the moment not used; currently data also does not contain
        #       these information
#        self._size = data.get('size', 1)
#        self._cpu = data.get('cpu', 0)
#        self._memory = data.get('memory', 0)
#        self._bandwidth = data.get('bandwidth', 0)
#        self._specialFeatures = data.get('specialFeatures', [])

        client.registerContainer(self)

        # Create the directories for the container
        self._confDir = confDir = pjoin(client.confDir, name)
        self._dataDir = dataDir = pjoin(client.dataDir, name)

        if os.path.isdir(confDir):
            raise ValueError('There is already a configuration directory for '
                             "'{0}' \n Please remove it manually if the engine "
                             'did not shut down correctly on last execution and '
                             'you are sure it is not in use. \n dir: {1}.'.format(name, confDir))

        if os.path.isdir(dataDir):
            raise ValueError('There is already a data directory for '
                             "'{0}' \n Please remove it manually if the engine "
                             'did not shut down correctly on last execution and '
                             'you are sure it is not in use. \n dir: {1}.'.format(name, dataDir))
        os.mkdir(confDir)
        os.mkdir(dataDir)

        # Create additional folders for the container
        rceDir = pjoin(dataDir, 'rce')
        rosDir = pjoin(dataDir, 'ros')

        os.mkdir(rceDir)
        os.mkdir(rosDir)

        if client.rosRel > 'fuerte':
            # TODO: Switch to user 'ros' when the launcher is used again
            shutil.copytree(pjoin(client.rootfs, 'root/.ros/rosdep'),
                            pjoin(rceDir, '.ros/rosdep'))

        # Create network variables
        bridgeIP = client.bridgeIP
        ip = '{0}.{1}'.format(bridgeIP.rsplit('.', 1)[0], nr)
        self._address = '{0}:{1}'.format(ip, client.envPort)
        self._rosproxyAddress = '{0}:{1}'.format(ip, client.rosproxyPort)
        self._fwdPort = str(nr + 8700)
        self._rosproxyFwdPort = str(nr + 10700)

        ovsname = data.get('name')
        ovsip = data.get('ip')

        if ovsname and ovsip:
            ovsif = 'eth1'
            ovsup = pjoin(confDir, 'ovsup')

            if client.ubuntuRel > 'quantal':
                ovsdown = pjoin(confDir, 'ovsdown')
            else:
                ovsdown = None
        else:
            ovsif = ovsup = ovsdown = None

        # Construct password
        passwd = encodeAES(cipher(client.masterPassword),
                           salter(uid, client.infraPassword))

        # Create upstart scripts
        upComm = pjoin(confDir, 'upstartComm')
        with open(upComm, 'w') as f:
            f.write(_UPSTART_COMM.format(masterIP=client.masterIP,
                                         masterPort=client.masterPort,
                                         internalPort=client.envPort,
                                         uid=uid, passwd=passwd))

        upRosapi = pjoin(confDir, 'upstartRosapi')
        with open(upRosapi, 'w') as f:
            f.write(_UPSTART_ROSAPI.format(proxyPort=client.rosproxyPort))

        # TODO: For the moment there is no upstart script for the launcher.
#        upLauncher = pjoin(confDir, 'upstartLauncher')
#        with open(upLauncher, 'w') as f:
#            f.write(_UPSTART_LAUNCHER)

        # Setup network
        networkIF = pjoin(confDir, 'networkInterfaces')
        with open(networkIF, 'w') as f:
            f.write('auto lo\n')
            f.write('iface lo inet loopback\n')
            f.write('\n')
            f.write('auto eth0\n')
            f.write('iface eth0 inet static\n')
            f.write('    address {0}\n'.format(ip))
            f.write('    gateway {0}\n'.format(bridgeIP))
            f.write('    dns-nameservers {0} 127.0.0.1\n'.format(bridgeIP))

            if ovsif:
                f.write('\n')
                f.write('auto {0}\n'.format(ovsif))
                f.write('iface {0} inet static\n'.format(ovsif))
                f.write('    address {0}\n'.format(ovsip))

        # Create up/down script for virtual network interface if necessary
        if ovsup:
            with open(ovsup, 'w') as f:
                f.write(_LXC_NETWORK_SCRIPT.format(if_op='up', ovs_op='add',
                                                   name=ovsname))

            os.chmod(ovsup, stat.S_IRWXU)

        if ovsdown:
            with open(ovsdown, 'w') as f:
                f.write(_LXC_NETWORK_SCRIPT.format(if_op='down', ovs_op='del',
                                                   name=ovsname))

            os.chmod(ovsdown, stat.S_IRWXU)

        # TODO: SSL stuff
#        if self._USE_SSL:
#            # Create a new certificate and key for environment node
#            caCertPath = pjoin(self._SSL_DIR, 'Container.cert')
#            caCert = loadCertFile(caCertPath)
#            caKey = loadKeyFile(pjoin(self._SSL_DIR, 'container/env.key'))
#            (cert, key) = createKeyCertPair(commID, caCert, caKey)
#
#            # Copy/save file to data directory
#            shutil.copyfile(caCertPath, os.path.join(rceDir, 'ca.pem'))
#            writeCertToFile(cert, os.path.join(rceDir, 'cert.pem'))
#            writeKeyToFile(key, os.path.join(rceDir, 'key.pem'))

        # Create the container
        self._container = container = Container(client.reactor, client.rootfs,
                                                confDir, name)

        # Add lxc bridge
        container.addNetworkInterface('eth0', client.bridgeIF, ip)

        # Add the virtual network bridge if necessary
        if ovsname and ovsip:
            container.addNetworkInterface(ovsif, None, ovsip, ovsup, ovsdown)

        # Add additional lines to fstab file of container
        container.extendFstab(rosDir, 'home/ros', False)
        container.extendFstab(rceDir, 'opt/rce/data', False)
        container.extendFstab(upComm, 'etc/init/rceComm.conf', True)
        # TODO: For the moment there is no upstart script for the launcher.
#        container.extendFstab(upLauncher, 'etc/init/rceLauncher.conf', True)
        container.extendFstab(upRosapi, 'etc/init/rceRosapi.conf', True)
        container.extendFstab(networkIF, 'etc/network/interfaces', True)

        for srcPath, destPath in client.pkgDirIter:
            container.extendFstab(srcPath, destPath, True)

    def start(self):
        """ Method which starts the container.
        """
        # NOTE: can raise iptc.xtables.XTablesError
        # add remote rule for RCE internal communication
        rule = iptc.Rule()
        rule.protocol = 'tcp'
        rule.dst = self._client.internalIP
        m = rule.create_match('tcp')
        m.dport = self._fwdPort
        t = rule.create_target('DNAT')
        t.to_destination = self._address
        self._remoteRule = rule

        # add local (loopback) rule for RCE internal communication
        rule = iptc.Rule()
        rule.protocol = 'tcp'
        rule.out_interface = 'lo'
        rule.dst = self._client.internalIP
        m = rule.create_match('tcp')
        m.dport = self._fwdPort
        t = rule.create_target('DNAT')
        t.to_destination = self._address
        self._localRule = rule

        # add remote rule for rosproxy
        rule = iptc.Rule()
        rule.protocol = 'tcp'
        rule.dst = self._client.internalIP
        m = rule.create_match('tcp')
        m.dport = self._rosproxyFwdPort
        t = rule.create_target('DNAT')
        t.to_destination = self._rosproxyAddress
        self._rosremoteRule = rule

        # add local(loopback) rule for rosproxy
        rule = iptc.Rule()
        rule.protocol = 'tcp'
        rule.out_interface = 'lo'
        rule.dst = self._client.internalIP
        m = rule.create_match('tcp')
        m.dport = self._rosproxyFwdPort
        t = rule.create_target('DNAT')
        t.to_destination = self._rosproxyAddress
        self._roslocalRule = rule

        self._client.prerouting.insert_rule(self._remoteRule)
        self._client.output.insert_rule(self._localRule)
        self._client.prerouting.insert_rule(self._rosremoteRule)
        self._client.output.insert_rule(self._roslocalRule)

        return self._container.start(self._name)

    def remote_getPort(self):
        """ Get the port which can be used together with the host IP address
            to reach connect with the container.

            @return:            Port number of host machine which will be
                                forwarded to the container.
            @rtype:             int
        """
        return int(self._fwdPort)

    def _stop(self):
        """ Method which stops the container.
        """
        self._client.prerouting.delete_rule(self._remoteRule)
        self._client.output.delete_rule(self._localRule)
        self._client.prerouting.delete_rule(self._rosremoteRule)
        self._client.output.delete_rule(self._roslocalRule)

        return self._container.stop(self._name)

    def _destroy(self):
        """ Internally used method to clean up after the container has been
            stopped.
        """
        if self._client:
            self._client.returnNr(self._nr)
            self._client.unregisterContainer(self)
            self._client = None

        if self._confDir:
            shutil.rmtree(self._confDir, True)
            self._confDir = None

        if self._dataDir:
            shutil.rmtree(self._dataDir, True)
            self._dataDir = None

    def remote_destroy(self):
        """ Method should be called to destroy the container.
        """
        if not self._terminating:
            if self._container:
                self._terminating = self._stop()
                self._terminating.addBoth(passthrough(self._destroy))
            else:
                self._terminating = succeed(None)

        return self._terminating

    def __del__(self):
        self._destroy()


class ContainerClient(Referenceable):
    """ Container client is responsible for the creation and destruction of
        containers in a machine.

        There can be only one Container Client per machine.
    """
    _UID_LEN = 8

    def __init__(self, reactor, masterIP, masterPort, masterPasswd, infraPasswd,
                 bridgeIF, intIP, bridgeIP, envPort, rosproxyPort, rootfsDir,
                 confDir, dataDir, pkgDir, ubuntuRel, rosRel, data):
        """ Initialize the Container Client.

            @param reactor:         Reference to the twisted reactor.
            @type  reactor:         twisted::reactor

            @param masterIP:        IP address of the Master process.
            @type  masterIP:        str

            @param masterPort:      Port of the Master process used for internal
                                    communications.
            @type  masterPort:      int

            @param masterPasswd:    SHA 256 Digested Master Password.
            @type  masterPasswd:    str

            @param infraPasswd:     SHA 256 Digested Infra Password.
            @type  infraPasswd:     str

            @param bridgeIF:        Network interface used for the container
                                    communication.
            @type  bridgeIF:        str

            @param intIP:           IP address of the network interface used for
                                    the internal communication.
            @type  intIP:           str

            @param bridgeIP:        IP address of the network interface used for
                                    the container communication.
            @type  bridgeIP:        str

            @param envPort:         Port where the environment process running
                                    inside the container is listening for
                                    connections to other endpoints. (Used for
                                    port forwarding.)
            @type  envPort:         int

            @param rosproxyPort:    Port where the rosproxy process running
                                    inside the container is listening for
                                    connections to console clients. (Used for
                                    port forwarding.)
            @type  rosproxyPort:    int

            @param rootfsDir:       Filesystem path to the root directory of the
                                    container filesystem.
            @type  rootfsDir:       str

            @param confDir:         Filesystem path to the directory where
                                    container configuration files should be
                                    stored.
            @type  confDir:         str

            @param dataDir:         Filesystem path to the directory where
                                    temporary data of a container should be
                                    stored.
            @type  dataDir:         str

            @param pkgDir:          Filesystem paths to the package directories
                                    as a list of tuples where each tuple
                                    contains the path to the directory in the
                                    host machine and the path to the directory
                                    to which the host directory will be bound in
                                    the container filesystem (without the
                                    @param rootfsDir).
            @type  pkgDir:          [(str, str)]

            @param ubuntuRel:       Host filesystem Ubuntu release used in this
                                    machine.
            @type  ubuntuRel:       str

            @param rosRel:          Container filesytem ROS release in this
                                    deployment instance of the cloud engine
            @type  rosRel:          str

            @param data:            More data about the machine configuration.
            @type  data:            dict
        """
        self._reactor = reactor
        self._internalIP = intIP
        self._envPort = envPort
        self._rosproxyPort = rosproxyPort
        self._masterPort = masterPort

        if isLocalhost(masterIP):
            self._masterIP = bridgeIP
        else:
            self._masterIP = masterIP

        self._masterPasswd = masterPasswd
        self._infraPasswd = infraPasswd

        # Container directories
        self._rootfs = rootfsDir
        self._confDir = confDir
        self._dataDir = dataDir
        self._pkgDir = pkgDir

        # Release info
        self._ubuntuRel = ubuntuRel
        self._rosRel = rosRel

        for _, path in self._pkgDir:
            os.mkdir(os.path.join(self._rootfs, path))

        # Container info
        self._nrs = set(range(100, 200))
        self._containers = set()

        # Network configuration
        self._bridgeIF = bridgeIF
        self._bridgeIP = bridgeIP

        # Virtual network
        self._bridges = set()
        self._uid = {}

        # Physical parameters of machine
        # TODO: Is a human settings at this time,
        #       rce.util.sysinfo should fill this role soon
        self._size = data.get('size')
        self._cpu = data.get('cpu')
        self._memeory = data.get('memory')
        self._bandwidth = data.get('bandwidth')
        self._specialFeatures = data.get('special_features')

        # Common iptables references
        nat = iptc.Table(iptc.Table.NAT)
        self._prerouting = iptc.Chain(nat, 'PREROUTING')
        self._output = iptc.Chain(nat, 'OUTPUT')

    def remote_getSysinfo(self, request):
        """ Get realtime Sysinfo data from machine.

            @param request:     data desired
            @type  request:     # TODO: Add type

            @return:            # TODO: What?
            @rtype:             # TODO: Add type
        """
        # TODO : replace these calls with call to rce.util.sysinfo
        response_table = {
            'size':self._size,
            'cpu':self._cpu,
            'memory': self._memeory,
            'bandwidth': self._bandwidth,
            # 'keyword': some value or function to provide the data
        }

        return response_table[request]

    def remote_setSysinfo(self, request, value):
        """ Set some system parameter to the machine.

            @param request:     data desired
            @type  request:     # TODO: Add type

            @param value:       data value
            @type  value:       # TODO: Add type
        """
        raise NotImplementedError

    @property
    def reactor(self):
        """ Reference to twisted::reactor. """
        return self._reactor

    @property
    def internalIP(self):
        """ IP address of this process in the internal network. """
        return self._internalIP

    @property
    def masterPort(self):
        """ Port of the master process used for internal communications. """
        return self._masterPort

    @property
    def envPort(self):
        """ Port where the environment process running inside the container is
            listening for new connections.
        """
        return self._envPort

    @property
    def rosproxyPort(self):
        """ Port where the ROS proxy running inside the container is listening
            for new connections.
        """
        return self._rosproxyPort

    @property
    def rootfs(self):
        """ Host filesystem path of container filesystem root directory. """
        return self._rootfs

    @property
    def confDir(self):
        """ Filesystem path of configuration directory. """
        return self._confDir

    @property
    def dataDir(self):
        """ Filesystem path of temporary data directory. """
        return self._dataDir

    @property
    def pkgDirIter(self):
        """ Iterator over all file system paths of package directories. """
        return self._pkgDir.__iter__()

    @property
    def ubuntuRel(self):
        """ Host filesystem Ubuntu release in this machine. """
        return self._ubuntuRel

    @property
    def rosRel(self):
        """ Container filesytem ROS release in this deployment instance of the
            cloud engine.
        """
        return self._rosRel

    @property
    def bridgeIF(self):
        """ Network interface used for the communication with the containers.
        """
        return self._bridgeIF

    @property
    def bridgeIP(self):
        """ IP address of network interface used for the communication with
            the containers.
        """
        return self._bridgeIP

    @property
    def masterIP(self):
        """ IP address of master process. """
        return self._masterIP

    @property
    def masterPassword(self):
        """ SHA 256 Digested Master Password. """
        return self._masterPasswd

    @property
    def infraPassword(self):
        """ SHA 256 Digested Infra Password. """
        return self._infraPasswd

    @property
    def prerouting(self):
        """ Reference to iptables' chain PREROUTING of the table NAT. """
        return self._prerouting

    @property
    def output(self):
        """ Reference to iptables' chain OUTPUT of the table NAT. """
        return self._output

    def remote_createContainer(self, uid, data):
        """ Create a new Container.

            @param uid:         Unique ID which the environment process inside
                                the container needs to login to the Master
                                process.
            @type  uid:         str

            @param data:        Extra data which is used to configure the
                                container.
            @type  data:        dict

            @return:            New Container instance.
            @rtype:             rce.container.RCEContainer
        """
        try:
            nr = self._nrs.pop()
        except KeyError:
            raise MaxNumberExceeded('Can not manage any additional container.')

        container = RCEContainer(self, nr, uid, data)
        return container.start().addCallback(lambda _: container)

    def registerContainer(self, container):
        assert container not in self._containers
        self._containers.add(container)

    def remote_createBridge(self, name):
        """ Create a new OVS Bridge.

            @param name:        Unique name of the network group.
            @type  name:        str

            @return:            Exit status of command.
            @rtype:             twisted.internet.defer.Deferred
        """
        if name in self._bridges:
            raise InternalError('Bridge already exists.')

        self._bridges.add(name)
        return execute(('/usr/bin/ovs-vsctl', '--', '--may-exist', 'add-br',
                        'br-{0}'.format(name)), reactor=self._reactor)

    def remote_destroyBridge(self, name):
        """ Destroy a OVS Bridge.

            @param name:        Unique name of the network group.
            @type  name:        str

            @return:            Exit status of command.
            @rtype:             twisted.internet.defer.Deferred
        """
        if name not in self._bridges:
            raise InternalError('Bridge does not exist.')

        self._bridges.remove(name)
        return execute(('/usr/bin/ovs-vsctl', 'del-br',
                        'br-{0}'.format(name)), reactor=self._reactor)


    def remote_createTunnel(self, name, targetIP):
        """ Create a new GRE Tunnel.

            @param name:        Unique name of the network group.
            @type  name:        str

            @param targetIP:    Target IP for the GRE Tunnel.
            @type  targetIP:    str

            @return:            Exit status of command.
            @rtype:             twisted.internet.defer.Deferred
        """
        if name not in self._bridges:
            raise InternalError('Bridge does not exist.')

        key = (name, targetIP)

        if key in self._uid:
            raise InternalError('Tunnel already exists.')

        while 1:
            uid = randomString(self._UID_LEN)

            if uid not in self._uid.itervalues():
                break

        self._uid[key] = uid
        port = 'gre-{0}'.format(uid)

        return execute(('/usr/bin/ovs-vsctl', 'add-port', 'br-{0}'.format(name),
                        port, '--', 'set', 'interface', port, 'type=gre',
                        'options:remote_ip={0}'.format(targetIP)),
                       reactor=self._reactor)

    def remote_destroyTunnel(self, name, targetIP):
        """ Destroy a GRE Tunnel.

            @param name:        Unique name of the network group.
            @type  name:        str

            @param targetIP:    Target IP for the GRE Tunnel.
            @type  targetIP:    str

            @return:            Exit status of command.
            @rtype:             twisted.internet.defer.Deferred
        """
        if name not in self._bridges:
            raise InternalError('Bridge does not exist.')

        key = (name, targetIP)

        if key not in self._uid:
            raise InternalError('Tunnel deos not exist.')

        return execute(('/usr/bin/ovs-vsctl', 'del-port',
                        'gre-{0}'.format(self._uid.pop(key))),
                       reactor=self._reactor)

    def unregisterContainer(self, container):
        assert container in self._containers
        self._containers.remove(container)

        def eb(failure):
            if not failure.check(PBConnectionLost):
                log.err(failure)

        try:
            self._avatar.callRemote('containerDied', container).addErrback(eb)
        except (DeadReferenceError, PBConnectionLost):
            pass

    def returnNr(self, nr):
        """ Callback for Container to return a container number when it is
            no longer in use such that it can be reused.
        """
        if nr in self._nrs:
            raise InternalError('Number was never rented out.')

        self._nrs.add(nr)

    def _cleanPackageDir(self, *_):
        """ Internally used method to clean-up the container filesystem.
        """
        for _, path in self._pkgDir:
            os.rmdir(os.path.join(self._rootfs, path))

        assert len(self._containers) == 0

    def terminate(self):
        """ Method should be called to terminate all running containers before
            the reactor is stopped.
        """
        deferreds = []

        for container in self._containers.copy():
            deferreds.append(container.remote_destroy())

        if deferreds:
            deferredList = DeferredList(deferreds)
            deferredList.addCallback(self._cleanPackageDir)
            return deferredList
        else:
            self._cleanPackageDir()


def main(reactor, cred, masterIP, masterPort, masterPassword, infraPasswd,
         bridgeIF, internalIP, bridgeIP, envPort, rosproxyPort, rootfsDir,
         confDir, dataDir, pkgDir, ubuntuRel, rosRel, data):
    log.startLogging(sys.stdout)

    def _err(reason):
        print(reason)
        reactor.stop()

    factory = PBClientFactory()
    reactor.connectTCP(masterIP, masterPort, factory)

    client = ContainerClient(reactor, masterIP, masterPort, masterPassword,
                             infraPasswd, bridgeIF, internalIP, bridgeIP,
                             envPort, rosproxyPort, rootfsDir, confDir, dataDir,
                             pkgDir, ubuntuRel, rosRel, data)

    d = factory.login(cred, (client, data))
    d.addCallback(lambda ref: setattr(client, '_avatar', ref))
    d.addErrback(_err)

    reactor.addSystemEventTrigger('before', 'shutdown', client.terminate)
    reactor.run()

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/core/base.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# twisted specific imports
from twisted.python import log
from twisted.python.failure import Failure
from twisted.internet.defer import Deferred, succeed, fail
from twisted.spread.pb import RemoteReference, \
    DeadReferenceError, PBConnectionLost

# rce specific imports
from rce.core.error import AlreadyDead


class Proxy(object):
    """ The Proxy should be used to represent an object from a slave process in
        the Master.
        It provides the same methods as the twisted.spread.pb.RemoteReference.
        Additionally, the Proxy is callable to get a Deferred which fires as
        soon as the RemoteReference or a Failure is present.
    """
    def __init__(self, *args, **kw):
        """ Initialize the Proxy.
        """
        super(Proxy, self).__init__(*args, **kw)

        # Stores the remote reference
        self.__obj = None
        self.__failure = None

        self.__cbs = set()
        self.__pending = []

    def callRemote(self, _name, *args, **kw):
        """ Make a call to the RemoteReference and return the result as a
            Deferred. It exists to allow queuing of calls to remote reference
            before the remote reference has arrived.

            For more information refer to twisted.spread.pb.RemoteReference.

            @param _name:       Name of the method which should be called.
                                The prefix 'remote_' will be added to the name
                                in the remote object to select the method which
                                should be called.
            @type  _name:       str

            @param *args:       Positional arguments which will be passed to
                                the remote method.

            @param **kw:        Keyworded arguments which will be passed to the
                                remote method.

            @return:            Deferred which will fire with the result of the
                                call or a Failure if there was a problem.
            @rtype:             twisted.internet.defer.Deferred
        """
        if self.__failure is not None:
            d = fail(self.__failure)
        elif self.__pending is not None:
            d = Deferred()
            self.__pending.append(d)
        else:
            d = succeed(self.__obj)

        d.addCallback(lambda ref: ref.callRemote(_name, *args, **kw))
        d.addErrback(self.__filter, _name)
        return d

    def callback(self, obj):
        """ Register the remote reference which provides the necessary methods
            for this Proxy. Fires all pending callbacks passing on the remote
            reference as a parameter.

            Exactly one call can be made to either 'callback' or 'errback'!

            @param obj:         Remote reference which should be registered.
            @type  obj:         twisted.spread.pb.RemoteReference
        """
        assert self.__obj is None, 'Only one object can be registered.'
        assert isinstance(obj, RemoteReference)

        # Store the remote reference
        self.__obj = obj

        # inform when the remote reference is disconnected using __disconnected
        obj.notifyOnDisconnect(self.__disconnected)

        # Call all remaining remote calls made before the remote reference
        # arrived
        for pending in self.__pending:
            pending.callback(obj)

        self.__pending = None

    def errback(self, f):
        """ Register a failure object which was received during the creation
            of the object in the remote process.

            Exactly one call can be made to either 'callback' or 'errback'!

            @param f:           Failure object which should be registered.
            @type  f:           twisted.python.failure.Failure
        """
        assert self.__obj is None, 'Only one object can be registered.'
        assert isinstance(f, Failure), "Failure has to be of type 'Failure'."
        self.__notify(f)

    def notifyOnDeath(self, cb):
        """ Register a callback which will be called once the remote object is
            dead, i.e. no longer connected to this process or a failure was
            received.

            @param cb:          Callback which should be registered. It should
                                take this instance as only argument.
            @type  cb:          callable
        """
        assert callable(cb)

        try:
            self.__cbs.add(cb)
        except AttributeError:
            raise AlreadyDead('{0} is already '
                              'dead.'.format(self.__class__.__name__))

    def dontNotifyOnDeath(self, cb):
        """ Unregister a callback which would have been called once the remote
            object is dead.

            @param cb:          Callback which should be unregistered.
            @type  cb:          callable
        """
        try:
            self.__cbs.remove(cb)
        except AttributeError:
            pass

    def __call__(self):
        """ Return a reference to the remote object as soon as the reference
            is available.

            @return:            Reference to the RemoteObject instance.
                                (type: rce.master.base.RemoteReference)
            @rtype:             twisted.internet.defer.Deferred
        """
        if self.__failure is not None:
            return fail(self.__failure)

        if self.__pending is not None:
            d = Deferred()
            self.__pending.append(d)
            return d

        return succeed(self.__obj)

    def destroy(self):
        """ Method should be called to destroy the Proxy as well as the remote
            object.
        """
        self.__destroy()

    def destroyExternal(self, remoteObject):
        """ Method to compare given remote reference with Proxy's remote
            reference and destroy if they are the same.
        """
        if remoteObject == self.__obj:
            self.destroy()
            return True

        return False

    def __filter(self, failure, name):
        """ Internally used method which is used as an errback to check the
            failure for errors indicating that the Proxy is dead.
        """
        if failure.check(DeadReferenceError, PBConnectionLost):
            self.__notify(failure)
        else:
            print('Received the following error message when calling {0} from '
                  'class {1}: {2}'.format(name, self.__class__.__name__,
                                          failure.getErrorMessage()))

        return failure

    def __notify(self, failure):
        """ Method is used as a callback to inform the Proxy that a failure
            occurred.
        """
        # if the Proxy already stores a failure then do nothing
        if self.__failure:
            return

        # Disconnect callback for disconnect
        if self.__obj:
            self.__obj.dontNotifyOnDisconnect(self.__disconnected)

        # Mark that the Proxy is a failure and doesn't store remote reference.
        self.__failure = failure

        # fire errbacks on all remote calls
        if self.__pending is not None:
            for pending in self.__pending:
                pending.errback(failure)

            self.__pending = None

        # fire all callbacks to notify of the proxy's death
        for cb in self.__cbs:
            cb(self)

        self.__cbs = None

    def __destroy(self):
        """ Method to destroy Proxy. Takes care of whether it's been called from
            the remote side or the local side. Calls __notify to clear up
            pending callbacks of callRemote or notifyOnDeath. Calls
            remote reference's (self.__obj) destroy function to make sure object
            on the remote side is also dead
        """
        m = 'Referenced object {0} dead.'.format(self.__class__.__name__)
        self.__notify(Failure(DeadReferenceError(m)))

        # Destroy object on the remote side. Takes care if it's already
        # destroyed.
        if self.__obj:
            def eb(failure):
                from twisted.spread.pb import PBConnectionLost #@Reimport
                if not failure.check(PBConnectionLost):
                    log.err(failure)

            try:
                self.__obj.callRemote('destroy').addErrback(eb)
            except DeadReferenceError, PBConnectionLost:
                pass

        self.__obj = None

    def __disconnected(self, _):
        self.__notify(Failure(DeadReferenceError('Broker is disconnected.')))
        self.__obj = None

########NEW FILE########
__FILENAME__ = container
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/core/container.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# twisted specific imports
from twisted.internet.address import IPv4Address
from twisted.internet.defer import Deferred, succeed

# rce specific imports
from rce.core.base import Proxy
from rce.util.error import InternalError


class Container(Proxy):
    """ Representation of an LXC container.
    """
    def __init__(self, data, userID, group, ip):
        """ Initialize the Container.

            @param data:        Extra data used to configure the container.
            @type  data:        dict

            @param userID:      ID of the user who created the container.
            @type  userID:      str

            # TODO: Add doc
        """
        super(Container, self).__init__()

        self._machine = None
        self._userID = userID
        self._group = group
        self._ip = ip

        self._size = data.pop('size', 1)
        self._cpu = data.pop('cpu', 0)
        self._memory = data.pop('memory', 0)
        self._bandwidth = data.pop('bandwidth', 0)
        self._specialFeatures = data.pop('specialFeatures', [])

        self._pending = set()
        self._address = None

    @property
    def size(self):
        """ # TODO: Add doc """
        return self._size

    @property
    def cpu(self):
        """ # TODO: Add doc """
        return self._cpu

    @property
    def memory(self):
        """ # TODO: Add doc """
        return self._memory

    @property
    def bandwidth(self):
        """ # TODO: Add doc """
        return self._bandwidth

    @property
    def specialFeatures(self):
        """ # TODO: Add doc """
        return self._specialFeatures

    @property
    def userID(self):
        """ # TODO: Add doc """
        return self._userID

    @property
    def machine(self):
        """ Reference to the machine proxy in which the container resides. """
        return self._machine

    @property
    def serialized(self):
        """ Property is used to store the relevant container information for
            the container process.
        """
        return {'name':self._group.name, 'ip':self._ip}

    def assignMachine(self, machine):
        """ # TODO: Add doc
        """
        if self._machine:
            raise InternalError('Can not assign the same container multiple '
                                'times.')

        self._machine = machine

        self._group.registerContainer(self)
        machine.registerContainer(self)

    def getAddress(self):
        """ Get the address which should be used to connect to the environment
            process for the cloud engine internal communication. The method
            gets the address only once and caches the address for subsequent
            calls.

            @return:            twisted::IPv4Address which can be used to
                                connect to the ServerFactory of the cloud
                                engine internal communication protocol.
                                (type: twisted.internet.address.IPv4Address)
            @rtype:             twisted.internet.defer.Deferred
        """
        if self._address is None:
            if not self._pending:
                # This is the first time this method is called dispatch a call
                # to fetch the address
                def cb(result):
                    self._address = result

                    for p in self._pending:
                        p.callback(result)

                    self._pending = set()

                addr = self.callRemote('getPort')
                addr.addCallback(lambda port: IPv4Address('TCP',
                                                          self._machine.IP,
                                                          port))
                addr.addBoth(cb)

            d = Deferred()
            self._pending.add(d)
            return d

        return succeed(self._address)

    def destroy(self):
        """ Method should be called to destroy the container and will take care
            of deleting all circular references.
        """
        if self._group:
            if self._machine:
                self._group.unregisterContainer(self)
                self._machine.unregisterContainer(self)
                self._machine = None

            self._group = None

            super(Container, self).destroy()
        else:
            print('container.Container destroy() called multiple times...')

########NEW FILE########
__FILENAME__ = environment
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/core/environment.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# rce specific imports
from rce.util.error import InternalError
from rce.core.base import Proxy
from rce.core.network import Endpoint, Namespace, EndpointAvatar


class Node(Proxy):
    """ Representation of a node (ROS process) inside a ROS environment.
    """
    def __init__(self, namespace):
        """ Initialize the Node.

            @param namespace:   Namespace in which the node was created.
            @type  namespace:   rce.core.network.Namespace
        """
        super(Node, self).__init__()

        self._namespace = namespace
        namespace.registerNode(self)

    def destroy(self):
        """ Method should be called to destroy the node and will take care
            of deleting all circular references.
        """
        self._namespace.unregisterNode(self)
        self._namespace = None

        super(Node, self).destroy()


class Parameter(Proxy):
    """ Representation of a parameter inside a ROS environment.
    """
    def __init__(self, namespace):
        """ Initialize the Parameter.

            @param namespace:   Namespace in which the parameter was created.
            @type  namespace:   rce.core.network.Namespace
        """
        super(Parameter, self).__init__()

        self._namespace = namespace
        namespace.registerParameter(self)

    def destroy(self):
        """ Method should be called to destroy the parameter and will take
            care of deleting all circular references.
        """
        self._namespace.unregisterParameter(self)
        self._namespace = None

        super(Parameter, self).destroy()


class Environment(Namespace):
    """ Representation of a namespace which has a ROS environment assigned and
        is part of the cloud engine internal communication.
    """
    def __init__(self, endpoint):
        """ Initialize the Environment.

            @param endpoint:    Endpoint in which the environment was created.
            @type  endpoint:    rce.core.network.Endpoint
        """
        super(Environment, self).__init__(endpoint)

        self._nodes = set()
        self._parameters = set()

    def createNode(self, pkg, exe, args, name, nspace):
        """ Create a node (ROS process) inside the environment.

            @param pkg:         Name of ROS package where the node can be
                                found.
            @type  pkg:         str

            @param exe:         Name of executable (node) which should be
                                launched.
            @type  exe:         str

            @param args:        Additional arguments which should be used for
                                the launch.
            @type  args:        str

            @param name:        Name of the node under which the node should be
                                launched.
            @type  name:        str

            @param nspace:      Namespace in which the node should be started
                                in the environment.
            @type  nspace:      str
        """
        node = Node(self)
        self.callRemote('createNode', pkg, exe, args, name,
                        nspace).chainDeferred(node)
        return node

    def createParameter(self, name, value):
        """ Create a parameter (in ROS parameter server) inside the
            environment.

            @param name:        Name of the parameter which should be added.
                                It is also used to identify the parameter in
                                subsequent requests.
            @type  name:        str

            @param value:       Value of the parameter which should be added.
            @type  value:       str, int, float, bool, list
        """
        parameter = Parameter(self)
        self.callRemote('createParameter', name, value).chainDeferred(parameter)
        return parameter

    def getAddress(self):
        """ Get the address of the endpoint of the environment namespace.
        """
        return self._endpoint.getAddress()

    def registerNode(self, node):
        assert node not in self._nodes
        self._nodes.add(node)

    def registerParameter(self, parameter):
        assert parameter not in self._parameters
        self._parameters.add(parameter)

    def unregisterNode(self, node):
        assert node in self._nodes
        self._nodes.remove(node)

    def unregisterParameter(self, parameter):
        assert parameter in self._parameters
        self._parameters.remove(parameter)

    def registerConsole(self, userID, key):
        """ Register a console user with the environment.
        """
        self._endpoint.registerConsole(userID, key)

    def destroyNode(self, remoteNode):
        """ Method should be called to destroy the node proxy referenced by the
            remote node namespace.

            @param remoteNode:  Reference to Node Namespace in Environment
                                process.
            @type  remoteNode:  twisted.spread.pb.RemoteReference
        """
        for node in self._nodes:
            if node.destroyExternal(remoteNode):
                break

    def destroyParameter(self, remoteParam):
        """ Method should be called to destroy the parameter proxy referenced by
            the remote parameter namespace.

            @param remoteParam: Reference to Parameter Namespace in Environment
                                process.
            @type  remoteParam: twisted.spread.pb.RemoteReference
        """
        for parameter in self._parameters:
            if parameter.destroyExternal(remoteParam):
                break

    def destroy(self):
        """ Method should be called to destroy the environment and will take
            care of destroying all objects owned by this Environment as well
            as deleting all circular references.
        """
        for node in self._nodes.copy():
            node.destroy()

        for parameter in self._parameters.copy():
            parameter.destroy()

        assert len(self._nodes) == 0
        assert len(self._parameters) == 0

        super(Environment, self).destroy()


class EnvironmentEndpoint(Endpoint):
    """ Representation of an endpoint which is a process that lives inside a
        container and is part of the cloud engine internal communication.
    """
    def __init__(self, network, container):
        """ Initialize the Environment Endpoint.

            @param network:     Network to which the endpoint belongs.
            @type  network:     rce.core.network.Network

            @param container:   Container in which the enpoint is living.
            @type  container:   rce.core.container.Container
        """
        super(EnvironmentEndpoint, self).__init__(network)

        self._container = container

    def getAddress(self):
        """ Get the address of the environment endpoint's internal
            communication server.

            @return:            Address of the environment endpoint's internal
                                communication server.
                                (type: twisted.internet.address.IPv4Address)
            @rtype:             twisted.internet.defer.Deferred
        """
        return self._container.getAddress()

    def registerConsole(self, userID, key):
        self.callRemote('addUsertoROSProxy', userID, key)

    def unregisterConsole(self, userID, key):
        self.callRemote('removeUserfromROSProxy', userID)

    def createNamespace(self):
        """ Create a Environment object in the environment endpoint.

            @return:            New Environment instance.
            @rtype:             rce.master.environment.Environment
                                (subclass of rce.core.base.Proxy)
        """
        if self._namespaces:
            raise InternalError('Can not have more than one namespace '
                                'in an Environment endpoint at a time.')

        return Environment(self)

    def registerRemoteEnvironment(self, remoteNamespace):
        """ Register a Namespace object of the endpoint.

            @param remoteNamespace: Reference to Environment namespace in
                                    Environment process.
            @type  remoteNamespace: twisted.spread.pb.RemoteReference
        """
        # TODO: Workaround for now...
        try:
            iter(self._namespaces).next().callback(remoteNamespace)
        except StopIteration:
            pass

    def destroyNode(self, remoteNode):
        """ Method should be called to destroy the node proxy referenced by the
            remote node namespace.

            @param remoteNode:  Reference to Node Namespace in Environment
                                process.
            @type  remoteNode:  twisted.spread.pb.RemoteReference
        """
        # TODO: Workaround for now...
        try:
            iter(self._namespaces).next().destroyNode(remoteNode)
        except StopIteration:
            pass

    def destroyParameter(self, remoteParam):
        """ Method should be called to destroy the parameter proxy referenced by
            the remote parameter namespace.

            @param remoteParam: Reference to Parameter Namespace in Environment
                                process.
            @type  remoteParam: twisted.spread.pb.RemoteReference
        """
        # TODO: Workaround for now...
        try:
            iter(self._namespaces).next().destroyParameter(remoteParam)
        except StopIteration:
            pass

    def destroy(self):
        """ Method should be called to destroy the endpoint and will take care
            of destroying all objects owned by this Endpoint as well as
            deleting all circular references.
        """
        print('Destroying Connection to Environment Process.')
        self._container = None
        super(EnvironmentEndpoint, self).destroy()


class EnvironmentEndpointAvatar(EndpointAvatar):
    """ Avatar for internal PB connection from an Environment Endpoint.
    """
    def perspective_setupNamespace(self, remoteNamespace):
        """ Register a namespace with the Master process.

            @param remoteNamespace: Reference to the Namesapce in the slave
                                    process.
            @type  remoteNamespace: twisted.spread.pb.RemoteReference
        """
        self._endpoint.registerRemoteEnvironment(remoteNamespace)

    def perspective_nodeDied(self, remoteNode):
        """ Notify that a remote node died.

            @param remoteNode:  Reference to the Node in the Environment
                                process.
            @type  remoteNode:  twisted.spread.pb.RemoteReference
        """
        self._endpoint.destroyNode(remoteNode)

    def perspective_parameterDied(self, remoteParameter):
        """ Notify that a remote parameter died.

            @param remoteParam: Reference to the Parameter in the Environment
                                process.
            @type  remoteParam: twisted.spread.pb.RemoteReference
        """
        self._endpoint.destroyParameter(remoteParameter)

########NEW FILE########
__FILENAME__ = error
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/core/error.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# twisted specific imports
from twisted.spread.pb import Error


class MaxNumberExceeded(Error):
    """ Indicates that a quantity has exceeded an upper limit.
    """


class AlreadyDead(Error):
    """ Exception is raised when a object is called which is already dead.
    """


class InvalidRequest(Error):
    """ Exception is raised if the request can not be processed.
    """

########NEW FILE########
__FILENAME__ = machine
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/core/machine.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
from collections import Counter
from random import choice
from string import letters

# twisted specific imports
from twisted.spread.pb import Avatar

# rce specific imports
from rce.util.error import InternalError
from rce.util.settings import getSettings
from rce.util.network import isLocalhost
from rce.util.iaas import IaasHook
from rce.core.error import InvalidRequest, MaxNumberExceeded
from rce.core.container import Container


# Helper function to generate random strings
randomString = lambda length: ''.join(choice(letters) for _ in xrange(length))


class ContainerProcessError(Exception):
    """ Exception is raised if there is no free container process.
    """


class RobotProcessError(Exception):
    """ Exception is raised if there is no free robot process.
    """


class Distributor(object):
    """ The Distributor is responsible for selecting the appropriate robot
        process to create a WebSocket connection. It therefore also keeps track
        of all the robot processes registered with the cloud engine.

        There should only one instance running in the Master process.
    """
    def __init__(self):
        """ Initialize the Distributor.
        """
        self._robots = set()

    def registerRobotProcess(self, robot):
        assert robot not in self._robots
        self._robots.add(robot)

    def unregisterRobotProcess(self, robot):
        assert robot in self._robots
        self._robots.remove(robot)

    def getNextLocation(self):
        """ Get the next endpoint running in an robot process to create a new
            robot WebSocket connection.

            @return:            Next robot endpoint.
            @rtype:             rce.core.robot.RobotEndpoint
                                (subclass of rce.core.base.Proxy)
        """
        try:
            return min(self._robots, key=lambda r: r.active)
        except ValueError:
            raise RobotProcessError('There is no free robot process.')

    def cleanUp(self):
        assert len(self._robots) == 0


# TODO: Should probably be renamed...
class LoadBalancer(object):
    """ The Load Balancer is responsible for selecting the appropriate
        container to launch a new container. It therefore also keeps track
        of all the container processes registered with the cloud engine.

        There should only one instance running in the Master process.
    """
    _UID_LEN = 8

    def __init__(self):
        """ Initialize the Load Balancer.
        """
        self._empty = EmptyNetworkGroup()
        self._groups = {}
        self._uid = set()
        self._machines = set()
        self._iaas = None

    def createMachine(self, ref, data):
        """ Create a new Machine object, which can be used to create new
            containers.

            @param ref:         Remote reference to the ContainerClient in the
                                container process.
            @type  ref:         twisted.spread.pb.RemoteReference

            @param data:        Data about the machine
            @type  data:        dict

            @return:            New Machine instance.
            @rtype:             rce.core.machine.Machine
        """
        machine = Machine(ref, data, self)

        if machine in self._machines:
            raise InternalError('Tried to add the same machine multiple times.')

        self._machines.add(machine)
        return machine

    def destroyMachine(self, machine):
        """ Destroy a Machine object.

            @param machine:     Machine instance which should be destroyed.
            @type  machine:     rce.core.machine.Machine
        """
        try:
            self._machines.remove(machine)
        except KeyError:
            raise InternalError('Tried to remove a non existent machine.')

        machine.destroy()

    def _createContainer(self, data, userID):
        """ # TODO: Add doc
        """
        name = data.pop('group', None)

        if name:
            key = (userID, name)
            group = self._groups.get(key)

            if not group:
                while 1:
                    uid = randomString(self._UID_LEN)

                    if uid not in self._uid:
                        break

                self._uid.add(uid)
                group = NetworkGroup(self, key, uid)
                self._groups[key] = group
        else:
            # There is no group, i.e. 'special' group required
            group = self._empty

        return group.createContainer(data, userID)

    def _getMachine(self, container):
        """ Internally used method to assign a machine to the container which
            should be created.

            @param container:   Container which should be created.
            @type  container:   rce.core.container.Container

            @return:            Machine to which the container should be
                                assigned.
            @rtype:             rce.core.machine.Machine
        """
        size = container.size
        userID = container.userID

        # TODO: At the moment not used
#        cpu = container.cpu
#        memory = container.memory
#        bandwidth = container.bandwidth
#        specialFeatures = container.specialFeatures

        machines = [m for m in self._machines if m.availability >= size]

        # TODO: The above uses block assumptions, implement fine grain control
        #       at bottom. Like check memory data, use filters to get machines
        #       with special features like gpu, avxii, mmx sse
        if not machines:
#            if self._iaas:
#                self._iaas.spin_up()  # count, type, special_request
#                # TODO: Need to get the current list of machines here!
#                #       However, spin up of a new instance has most certainly a
#                #       delay; therefore, probably a Deferred has to be used...
#            else:
                raise ContainerProcessError('You seem to have run out of '
                                            'capacity. Add more nodes.')

        candidates = [m for m in machines if m.getUserCount(userID)]

        if candidates:
            return max(candidates, key=lambda m: m.availability)
        else:
            return max(machines, key=lambda m: m.availability)

    def createContainer(self, uid, userID, data):
        """ Select an appropriate machine and create a container.

            @param uid:         Unique ID which is used to identify the
                                environment process when he connects to the
                                Master.
            @type  uid:         str

            @param userID:      UserID of the user who created the container.
            @type  userID:      str

            @param data:        Extra data used to configure the container.
            @type  data:        dict

            @return:            New Container instance.
            @rtype:             rce.core.container.Container
        """
        container = self._createContainer(data, userID)
        self._getMachine(container).assignContainer(container, uid)
        return container

    def registerIAASHook(self, hook):
        """ Register an IAAS Hook object.

             # TODO: Add doc
        """
        if not isinstance(hook, IaasHook):
            raise InternalError('IAAS hook has to be a subclass of '
                                'rce.util.iaas.IaasHook.')

        self._iaas = hook

    def unregisterIAASHook(self):
        """ Method should be called to destroy all machines.
        """
        if self._iaas:
            self._iaas.disconnect()
            self._iaas = None

    def freeGroup(self, key, uid):
        """ # TODO: Add doc
        """
        self._uid.remove(uid)
        del self._groups[key]

    def cleanUp(self):
        """ Method should be called to destroy all machines.
        """
        for group in self._groups.values():
            group.destroy()

        assert len(self._groups) == 0

        for machine in self._machines.copy():
            self.destroyMachine(machine)

        assert len(self._machines) == 0

        self.unregisterIAASHook()


class Machine(object):
    """ Representation of a machine in which containers can be created. It
        keeps track of all the containers running in the machine.
    """
    def __init__(self, ref, data, balancer):
        """ Initialize the Machine.

            @param ref:         Remote reference to the ContainerClient in the
                                container process.
            @type  ref:         twisted.spread.pb.RemoteReference

            @param data:        Data about the machine.
            @type  data:        dict

            @param balancer:    Reference to the load balancer which is
                                responsible for this machine.
            @type  balancer:    rce.core.machine.LoadBalancer
        """
        self._ref = ref

        self._size = data.get('size')
        self._cpu = data.get('cpu')
        self._memeory = data.get('memory')
        self._bandwidth = data.get('bandwidth')
        self._specialFeatures = data.get('specialFeatures')

        ip = ref.broker.transport.getPeer().host
        self._ip = getSettings().internal_IP if isLocalhost(ip) else ip
        self._balancer = balancer

        self._containers = set()
        self._users = Counter()

    @property
    def active(self):
        """ The number of active containers in the machine. """
        return len(self._containers)

    @property
    def size(self):
        """ Machine Capacity. """
        return self._size

    @property
    def cpu(self):
        """ Machine CPU Info. """
        return self._cpu

    @property
    def memory(self):
        """ Machine Memory Info. """
        return self._memory

    @property
    def bandwidth(self):
        """ Machine Bandwidth Info. """
        return self._bandwidth

    @property
    def specialFeatures(self):
        """ Machine Special Features Info. """
        return self._specialFeatures

    @property
    def availability(self):
        """ Free Machine Capacity. """
        return self._size - sum(c.size for c in self._containers)

    @property
    def IP(self):
        """ The IP address used for the internal communication of the machine.
        """
        return self._ip

    def getUserCount(self, userID):
        """ # TODO: Add doc
        """
        return self._users[userID]

    def assignContainer(self, container, uid):
        """ # TODO: Add doc
        """
        if self.availability < container.size:
            raise MaxNumberExceeded('Machine has run out of container '
                                    'capacity.')

        container.assignMachine(self)
        d = self._ref.callRemote('createContainer', uid, container.serialized)
        d.chainDeferred(container)

    def createBridge(self, name):
        """ Create a new OVS Bridge.

            @param name:        Unique name of the network group.
            @type  name:        str
        """
        return self._ref.callRemote('createBridge', name)

    def destroyBridge(self, name):
        """ Destroy a OVS Bridge.

            @param name:        Unique name of the network group.
            @type  name:        str
        """
        return self._ref.callRemote('destroyBridge', name)

    def createTunnel(self, name, targetIP):
        """ Create a new GRE Tunnel.

            @param name:        Unique name of the network group.
            @type  name:        str

            @param targetIP:    Target IP for the GRE Tunnel.
            @type  targetIP:    str
        """
        return self._ref.callRemote('createTunnel', name, targetIP)

    def destroyTunnel(self, name, targetIP):
        """ Destroy a GRE Tunnel.

            @param name:        Unique name of the network group.
            @type  name:        str

            @param targetIP:    Target IP for the GRE Tunnel.
            @type  targetIP:    str
        """
        return self._ref.callRemote('destroyTunnel', name, targetIP)

    def getSysinfo(self, request):
        """ Get realtime Sysinfo data from machine.

            @param request:     data desired
            @type  request:     # TODO: Add type
        """
        return self._ref.callRemote('getSysinfo')

    def setSysinfo(self, request, value):
        """ Set some system parameter to the machine.

            @param request:     data desired
            @type  request:     # TODO: Add type

            @param value:       data value
            @type  value:       # TODO: Add type
        """
        return self._ref.callRemote('setSysinfo', value)

    def registerContainer(self, container):
        assert container not in self._containers
        self._containers.add(container)
        self._users[container.userID] += 1

    def unregisterContainer(self, container):
        assert container in self._containers
        self._containers.remove(container)
        cnt = self._users[container.userID] - 1
        if cnt:
            self._users[container.userID] = cnt
        else:
            del self._users[container.userID]

# TODO: Not used
#    def listContainers(self):
#        """ # TODO: Add doc
#        """
#        return self._containers

    def destroyContainer(self, remoteContainer):
        """ Destroy Container proxy.
        """
        for container in self._containers:
            if container.destroyExternal(remoteContainer):
                break

    def destroy(self):
        """ Method should be called to destroy the machine and will take care
            of deleting all circular references.
        """
        for container in self._containers.copy():
            container.destroy()

        assert len(self._containers) == 0

    def __eq__(self, other):
        return self._ip == other._ip

    def __ne__(self, other):
        return self._ip != other._ip

    def __hash__(self):
        return hash(self._ip)


class MachineAvatar(Avatar):
    """ Avatar for internal PB connection from a Machine.
    """
    def __init__(self, machine, balancer):
        """ Initialize the Machine avatar.

            @param machine:     Representation of the Machine.
            @type  machine:     rce.core.machine.Machine

            @param balancer:    The load balancer.
            @type  balancer:    rce.core.machine.LoadBalancer
        """
        self._machine = machine
        self._balancer = balancer

    def perspective_containerDied(self, remoteContainer):
        """ Notify that a remote container died.

            @param remoteContainer: Reference to the remote Container.
            @type  remoteContainer: twisted.spread.pb.RemoteReference
        """
        self._machine.destroyContainer(remoteContainer)

    def logout(self):
        """ Callback which should be called upon disconnection of the Machine
        """
        self._balancer.destroyMachine(self._machine)


class EmptyNetworkGroup(object):
    """ # TODO: Add doc
    """
    @property
    def name(self):
        """ Name of the network group. """
        return None

    def createContainer(self, data, userID):
        return Container(data, userID, self, None)

    def registerContainer(self, _):
        pass

    def unregisterContainer(self, _):
        pass


class NetworkGroup(object):
    """ # TODO: Add doc
    """
    # TODO: Should the IP address be configurable?
    _NETWORK_ADDR = '192.168.1'

    def __init__(self, manager, key, uid):
        """ # TODO: Add doc
        """
        self._manager = manager
        self._key = key
        self._uid = uid
        self._ips = set(xrange(2, 255))
        self._containers = set()
        self._machines = {}

    @property
    def name(self):
        """ Name of the network group. """
        return self._uid

    def createContainer(self, data, userID):
        """ # TODO: Add doc
        """
        if not self._ips:
            raise InvalidRequest('No more free IP addresses in subnet.')

        ip = data.pop('groupIP', None)

        if ip:
            addr, nr = ip.rsplit('.', 1)
            nr = int(nr)

            if addr != self._NETWORK_ADDR:
                addr = '{0}.0'.format(self._NETWORK_ADDR)
                raise InvalidRequest("IP address '{0}' is not in network range "
                                     "'{1}'".format(ip, addr))

            try:
                self._ips.remove(nr)
            except KeyError:
                raise InvalidRequest("IP address '{0}' is already in "
                                     'use.'.format(ip))
        else:
            ip = '{1}.{0}'.format(self._ips.pop(), self._NETWORK_ADDR)

        return Container(data, userID, self, ip)

    def registerContainer(self, container):
        assert container not in self._containers
        self._containers.add(container)
        self._registerMachine(container.machine)

    def unregisterContainer(self, container):
        assert container in self._containers
        self._containers.remove(container)
        self._unregisterMachine(container.machine)
        if not self._containers:
            self.destroy()

    def _registerMachine(self, machine):
        """ # TODO: Add doc
        """
        if machine not in self._machines:
            machine.createBridge(self._uid)

            for m in self._machines:
                machine.createTunnel(self._uid, m.IP)
                m.createTunnel(self._uid, machine.IP)

            self._machines[machine] = 1
        else:
            self._machines[machine] += 1

    def _unregisterMachine(self, machine):
        """ # TODO: Add doc
        """
        cnt = self._machines[machine] - 1

        if cnt:
            self._machines[machine] = cnt
        else:
            del self._machines[machine]

            for m in self._machines:
                machine.destroyTunnel(self._uid, m.IP)
                m.destroyTunnel(self._uid, machine.IP)

            machine.destroyBridge(self._uid)

    def destroy(self):
        """ # TODO: Add doc
        """
        self._manager.freeGroup(self._key, self._uid)
        self._manager = None

########NEW FILE########
__FILENAME__ = network
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/core/network.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
from uuid import uuid4

# twisted specific imports
from twisted.python.failure import Failure
from twisted.internet.defer import Deferred, DeferredList
from twisted.spread.pb import Referenceable, Error, PBConnectionLost, Avatar

# rce specific imports
from rce.util.error import InternalError
from rce.core.base import Proxy, AlreadyDead


class ConnectionError(Error):
    """ Error is raised when the connection failed unexpectedly.
    """


class InvalidKey(Error):
    """ this class is used to signal an invalid key during the initialization
        of the ROS message connections.
    """


class Network(object):
    """ The network is responsible for keeping track of all endpoints,
        namespaces, and interfaces in the cloud engine. Additionally, it
        provides the method to connect two interface.
    """
    def __init__(self):
        """ Initialize the Network.
        """
        self._endpoints = {}

    def registerEndpoint(self, endpoint):
        assert endpoint not in self._endpoints
        self._endpoints[endpoint] = set()

    def unregisterEndpoint(self, endpoint):
        assert endpoint in self._endpoints

        # First remove the endpoint from the dictionary
        endedConnections = self._endpoints.pop(endpoint)

        # Inform the endpoint connections that they are no longer valid
        for connection in endedConnections:
            connection.destroy()

        # Now remove all references to the ended connections
        for connections in self._endpoints.itervalues():
            connections -= endedConnections

    def _getEndpointConnection(self, epA, epB):
        """ Internally used method to get the connection between two endpoints.

            @param epX:         The endpoint which is part of the connection
                                that should be retrieved.
            @type  epX:         rce.core.network.Endpoint

            @return:            Connection between the two endpoints.
            @rtype:             rce.core.network.EndpointConnection
        """
        if epA not in self._endpoints or epB not in self._endpoints:
            raise InternalError('Endpoint is not part of this network.')

        if epA == epB:
            return epA.getLoopback()
        else:
            connectionsA = self._endpoints[epA]
            connectionsB = self._endpoints[epB]

            candidates = connectionsA.intersection(connectionsB)

            if candidates:
                if len(candidates) != 1:
                    raise InternalError('There are more than one possible '
                                        'endpoint connections.')

                return candidates.pop()
            else:
                connection = EndpointConnection(epA, epB)
                connectionsA.add(connection)
                connectionsB.add(connection)
                return connection

    def createConnection(self, interfaceA, interfaceB):
        """ Create a connection between two interfaces.

            @param interfaceX:  The interface which should be connected.
            @type  interfaceX:  rce.core.network.Interface

            @return:            Connection between the two interfaces.
            @rtype:             rce.core.network.Connection
        """
        assert interfaceA != interfaceB

        epA = interfaceA.endpoint
        epB = interfaceB.endpoint

        epA_epB = self._getEndpointConnection(epA, epB)

        pA_iA = epA.getInterfaceConnection(interfaceA,
                                           epA_epB.getProtocol(epA))
        pB_iB = epB.getInterfaceConnection(interfaceB,
                                           epA_epB.getProtocol(epB))

        return Connection(pA_iA, pB_iB)

    def cleanUp(self):
        """ Method should be called to destroy all machines and therefore all
            namespaces and interfaces.
        """
        for endpoint in self._endpoints.keys():
            endpoint.destroy()

        assert len(self._endpoints) == 0


class Endpoint(Proxy):
    """ Representation of an endpoint, which is a process which is part of the
        cloud engine internal communication.

        This class is an abstract implementation, where some methods have to
        be adapted.
    """
    def __init__(self, network):
        """ Initialize the Endpoint.

            @param network:     Network to which the endpoint belongs.
            @type  network:     rce.core.network.Network
        """
        super(Endpoint, self).__init__()

        self._network = network
        network.registerEndpoint(self)

        self._addr = None
        self._loopback = None
        self._namespaces = set()
        self._interfaces = {}
        self._protocols = {}

        self._uids = set()

    def getAddress(self):
        """ Get the address of the endpoint's internal communication server.

            @return:            Address of the endpoint's internal
                                communication server.
                                (type: twisted.internet.address.IPv4Address)
            @rtype:             twisted.internet.defer.Deferred
        """
        raise NotImplementedError('Endpoint can not be used directly.')

    def getUID(self):
        """ Get a ID which is unique within the endpoint.

            @return:            Unique ID (within the endpoint)
            @rtype:             uuid.UUID
        """
        while 1:
            uid = uuid4()

            if uid not in self._uids:
                self._uids.add(uid)
                return uid

    def returnUID(self, uid):
        """ Return a unique ID such that it could be reused again.

            @return:            Unique ID which should be returned.
            @rtype:             uuid.UUID
        """
        assert uid in self._uids
        self._uids.remove(uid)

    def createNamespace(self):
        """ Create a Namespace object in the endpoint.

            @return:            New namespace instance.
            @rtype:             rce.core.namespace.Namespace
                                (subclass of rce.core.base.Proxy)
        """
        raise NotImplementedError('Endpoint can not be used directly.')

    def getLoopback(self):
        """ Get the 'loopback' protocol, which is a special protocol that is
            used to connect two interfaces which are in the same endpoint.

            @return:            Loopback protocol.
            @rtype:             rce.core.network.LoopbackConnection
        """
        if not self._loopback:
            protocol = Protocol(self)
            self._loopback = LoopbackConnection(protocol)
            self.callRemote('getLoopback').chainDeferred(protocol)

        return self._loopback

    def prepareConnection(self, connID, key, auth):
        """ Prepare the endpoint for the connection attempt by adding the
            necessary connection information to the remote process. When the
            returned Deferred fires the endpoint is ready for the connection.

            @param connID:      Unique ID which is used to identify the
                                connection and respond with the appropriate
                                key.
            @type  connID:      str

            @param key:         Key which is used by the other side to
                                authenticate the endpoint.
            @type  key:         str

            @param auth:        Authenticator which is used to validate the
                                key from the other side.
            @type  auth:        rce.core.network._ConnectionValidator

            @return:            None. Deferred fires as soon as the endpoint is
                                ready for the connection attempt.
            @rtype:             twisted.internet.defer.Deferred
        """
        return self.callRemote('prepareConnection', connID, key, auth)

    def connect(self, connID, addr):
        """ Tell the endpoint to connect to the given address using the
            authentication details matching the given connection ID. This
            means that the connection has to be first prepared using
            'prepareConnection', before the actual command can be sent.
            Only one side should get the 'connect' command, because the
            receiver will be the client and not both sides can be the client.

            @param connID:      Unique ID which is used to identify the
                                connection.
            @type  connID:      str

            @param addr:        Address to which the endpoint should connect.
                                It consists of an IP address and a port number.
            @type  addr:        (str, int)

            @return:            None.
            @rtype:             twisted.internet.defer.Deferred
        """
        return self.callRemote('connect', connID, addr)

    def registerNamespace(self, namespace):
        assert namespace not in self._namespaces
        self._namespaces.add(namespace)

    def registerInterface(self, interface):
        assert interface not in self._interfaces
        self._interfaces[interface] = set()

    def registerProtocol(self, protocol):
        assert protocol not in self._protocols
        self._protocols[protocol] = set()

    def unregisterNamespace(self, namespace):
        assert namespace in self._namespaces
        self._namespaces.remove(namespace)

    def unregisterInterface(self, interface):
        assert interface in self._interfaces

        # First remove the interface from the dictionary
        endedConnections = self._interfaces.pop(interface)

        # Inform the interface connections that they are no longer valid
        for connection in endedConnections:
            connection.destroy()

        # Now remove all references to the ended connections
        for connections in self._protocols.itervalues():
            connections -= endedConnections

    def unregisterProtocol(self, protocol):
        assert protocol in self._protocols

        # First remove the protocol from the dictionary
        endedConnections = self._protocols.pop(protocol)

        # Inform the interface connections that they are no longer valid
        for connection in endedConnections:
            connection.destroy()

        # Now remove all references to the ended connections
        for connections in self._interfaces.itervalues():
            connections -= endedConnections

        # Handle special case where the protocol is the Loopback protocol
        if self._loopback == protocol:
            self._loopback = None

    def getInterfaceConnection(self, interface, protocol):
        """ Get the connection between an interface and a protocol.

            @param interface:   Interface which belongs to this endpoint and
                                which is on one side of the connection.
            @type  interface:   rce.core.network.Interface

            @param protocol:    Protocol which belongs to this endpoint and
                                which is on one side of the connection.
            @type  protocol:    rce.core.network.Protocol

            @return:            Connection between the interface and the
                                protocol.
            @rtype:             rce.core.network.InterfaceConnection
        """
        try:
            connectionI = self._interfaces[interface]
        except KeyError:
            raise InternalError('Interface does not belong to this endpoint.')

        try:
            connectionP = self._protocols[protocol]
        except KeyError:
            raise InternalError('Protocol does not belong to this endpoint.')

        candidates = connectionP.intersection(connectionI)

        if candidates:
            if len(candidates) != 1:
                raise InternalError('There are more than one possible '
                                    'interface-protocol connections.')

            return candidates.pop()
        else:
            connection = InterfaceConnection(interface, protocol)
            connectionI.add(connection)
            connectionP.add(connection)
            return connection

    def destroyNamespace(self, remoteNamespace):
        """ Method should be called to destroy the namespace proxy referenced by
            the remote namespace.

            @param remoteNamespace: Reference to Namespace in Remote process.
            @type  remoteNamespace: twisted.spread.pb.RemoteReference
        """
        for namespace in self._namespaces:
            if namespace.destroyExternal(remoteNamespace):
                break

    def destroyProtocol(self, remoteProtocol):
        """ Method should be called to destroy the protocol proxy referenced by
            the remote namespace.

            @param remoteProtocol:  Reference to Protocol in Remote process.
            @type  remoteProtocol:  twisted.spread.pb.RemoteReference
        """
        for protocol in self._protocols:
            if protocol.destroyExternal(remoteProtocol):
                break

    def destroyInterface(self, remoteInterface):
        """ Method should be called to destroy the interface proxy referenced by
            the remote namespace.

            @param remoteInterface: Reference to Interface in Remote process.
            @type  remoteInterface: twisted.spread.pb.RemoteReference
        """
        for interface in self._interfaces:
            if interface.destroyExternal(remoteInterface):
                break

    def destroy(self):
        """ Method should be called to destroy the endpoint and will take care
            of destroying all objects owned by this Endpoint as well as
            deleting all circular references.
        """
        # Protocols should be implicitly destroyed by the Network
        # Interfaces should be implicitly destroyed by the Namespaces

        if self._loopback:
            self._loopback.destroy()
            self._loopback = None

        for namespace in self._namespaces.copy():
            namespace.destroy()

        self._network.unregisterEndpoint(self)
        self._network = None

        assert len(self._protocols) == 0
        assert len(self._interfaces) == 0
        assert len(self._namespaces) == 0

        super(Endpoint, self).destroy()


class EndpointAvatar(Avatar):
    """ Avatar for internal PB connection from an Endpoint.
    """
    def __init__(self, realm, endpoint):
        """ Initialize the Endpoint avatar.

            @param realm:       User realm from which a user object can be
                                retrieved.
            @type  realm:       # TODO: Check this

            @param endpoint:    Representation of the Endpoint.
            @type  endpoint:    rce.core.network.Endpoint
        """
        self._realm = realm  # Required in subclass
        self._endpoint = endpoint

    def perspective_setupNamespace(self, remoteNamespace):
        """ Register a namespace with the Master process.

            @param remoteNamespace: Reference to the Namesapce in the slave
                                    process.
            @type  remoteNamespace: twisted.spread.pb.RemoteReference
        """
        raise NotImplementedError

    def perspective_interfaceDied(self, remoteInterface):
        """ Notify that a remote interface died.

            @param remoteInterface: Reference to the Interface in the slave
                                    process.
            @type  remoteInterface: twisted.spread.pb.RemoteReference
        """
        self._endpoint.destroyInterface(remoteInterface)

    def perspective_protocolDied(self, remoteProtocol):
        """ Notify that a remote protocol died.

            @param remoteProtocol:  Reference to the Protocol in the slave
                                    process.
            @type  remoteProtocol:  twisted.spread.pb.RemoteReference
        """
        self._endpoint.destroyProtocol(remoteProtocol)

    def perspective_namespaceDied(self, remoteNamespace):
        """ Notify that a remote namespace died.

            @param remoteNamespace: Reference to the Namespace in the slave
                                    process.
            @type  remoteNamespace: twisted.spread.pb.RemoteReference
        """
        self._endpoint.destroyNamespace(remoteNamespace)

    def logout(self):
        """ Callback which should be called upon disconnection of the Endpoint.
        """
        self._endpoint.destroy()


class Namespace(Proxy):
    """ Representation of a namespace, which is part of the cloud engine
        internal communication.
    """
    def __init__(self, endpoint):
        """ Initialize the Namespace.

            @param endpoint:    Endpoint in which the namespace was created.
            @type  endpoint:    rce.master.network.Endpoint
        """
        super(Namespace, self).__init__()

        self._endpoint = endpoint
        endpoint.registerNamespace(self)

        self._interfaces = set()

    def createInterface(self, iType, clsName, addr):
        """ Create an Interface object in the namespace and therefore endpoint.

            @param iType:       Type of the interface encoded as an integer.
                                Refer to rce.slave.interface.Types for more
                                information.
            @type  IType:       int

            @param clsName:     Message type/Service type consisting of the
                                package and the name of the message/service,
                                i.e. 'std_msgs/Int32'.
            @type  clsName:     str

            @return:            New Interface instance.
            @rtype:             rce.core.network.Interface
                                (subclass of rce.core.base.Proxy)
        """
        uid = self._endpoint.getUID()
        interface = Interface(self._endpoint, self, uid)
        self.callRemote('createInterface', uid.bytes, iType, clsName,
                        addr).chainDeferred(interface)
        return interface

    def registerInterface(self, interface):
        assert interface not in self._interfaces
        self._interfaces.add(interface)

    def unregisterInterface(self, interface):
        assert interface in self._interfaces
        self._interfaces.remove(interface)

    def destroy(self):
        """ Method should be called to destroy the namespace and will take care
            of destroying all objects owned by this Namespace as well as
            deleting all circular references.
        """
        for interface in self._interfaces.copy():
            interface.destroy()

        assert len(self._interfaces) == 0

        self._endpoint.unregisterNamespace(self)
        self._endpoint = None

        super(Namespace, self).destroy()


class Interface(Proxy):
    """ Representation of an interface, which is part of the cloud engine
        internal communication.
    """
    def __init__(self, endpoint, namespace, uid):
        """ Initialize the Interface.

            @param endpoint:    Endpoint in which the interface is created.
            @type  endpoint:    rce.core.network.Endpoint

            @param namespace:   Namespace in which the interface is created.
            @type  namespace:   rce.core.network.Namespace

            @param uid:         Unique ID which is used to identify the
                                interface in the internal communication.
            @type  uid:         uuid.UUID
        """
        super(Interface, self).__init__()

        self._endpoint = endpoint
        endpoint.registerInterface(self)

        self._namespace = namespace
        namespace.registerInterface(self)

        self._uid = uid

        self._connections = set()

    @property
    def UID(self):
        """ Unique ID of the interface. """
        return self._uid

    @property
    def endpoint(self):
        """ Reference to endpoint to which this interface belongs. """
        return self._endpoint

    def registerConnection(self, connection):
        assert connection not in self._connections
        self._connections.add(connection)

    def unregisterConnection(self, connection):
        assert connection in self._connections
        self._connections.remove(connection)

    def registerRemoteID(self, protocol, remoteID):
        """ Register an interface (using its unique ID) with this interface,
            which means that this and the indicated interface will be
            connected.

            @param protocol:    Protocol which provides the connection to the
                                other side, i.e. the other endpoint. (Could
                                also be the loopback protocol which would mean
                                that both interfaces are in the same endpoint.)
            @type  protocol:    rce.master.network.Protocol

            @param remoteID:    Unique ID of the interface at the other side
                                of the connection, i.e. in the other endpoint.
            @type  remoteID:    uuid.UUID

            @return:            None.
            @rtype:             twisted.internet.defer.Deferred
        """
        return protocol().addCallback(self._remoteID, remoteID, 'connect')

    def unregisterRemoteID(self, protocol, remoteID):
        """ Unregister an interface (using its unique ID) with this interface,
            which means that this and the indicated interface will no longer
            be connected.

            @param protocol:    Protocol which provides the connection to the
                                other side, i.e. the other endpoint. (Could
                                also be the loopback protocol which would mean
                                that both interfaces are in the same endpoint.)
            @type  protocol:    rce.core.network.Protocol

            @param remoteID:    Unique ID of the interface at the other side
                                of the connection, i.e. in the other endpoint.
            @type  remoteID:    uuid.UUID

            @return:            None.
            @rtype:             twisted.internet.defer.Deferred
        """
        def eb(failure):
            failure.trap(PBConnectionLost)

        d = protocol()
        d.addCallback(self._remoteID, remoteID, 'disconnect')
        d.addErrback(eb)
        return d

    def _remoteID(self, protocol, remoteID, name):
        return self.callRemote(name, protocol, remoteID.bytes)

    def destroy(self):
        """ Method should be called to destroy the interface and will take care
            of destroying all objects owned by this Interface as well as
            deleting all circular references.
        """
        self._endpoint.unregisterInterface(self)
        self._endpoint = None

        self._namespace.unregisterInterface(self)
        self._namespace = None

        # Endpoint should destroy all connections
        assert len(self._connections) == 0

        super(Interface, self).destroy()


class Protocol(Proxy):
    """ Representation of a protocol, which is part of the cloud engine
        internal communication.
    """
    def __init__(self, endpoint):
        """ Initialize the Protocol.

            @param endpoint:    Endpoint in which the protocol was created.
            @type  endpoint:    rce.core.network.Endpoint
        """
        super(Protocol, self).__init__()

        self._endpoint = endpoint
        endpoint.registerProtocol(self)

        self._connections = set()

    def registerConnection(self, connection):
        assert connection not in self._connections
        self._connections.add(connection)

    def unregisterConnection(self, connection):
        assert connection in self._connections
        self._connections.remove(connection)

    def destroy(self):
        """ Method should be called to destroy the protocol and will take care
            of destroying all objects owned by this Protocol as well as
            deleting all circular references.
        """
        # TODO: WHY ???
        if not self._endpoint:
            return

        self._endpoint.unregisterProtocol(self)
        self._endpoint = None

        # Endpoint should destroy all connections
        assert len(self._connections) == 0

        super(Protocol, self).destroy()


class _ConnectionValidator(Referenceable):
    """ Small helper to provide a callback to the endpoint to validate the
        connection and to register the protocol who is responsible for the it.
    """
    def __init__(self, key):
        """ Initialize the Connection Validator.

            @param key:         Key which is the correct.
            @type  key:         str
        """
        self._key = key
        self._authenticated = Deferred()

    @property
    def result(self):
        """ Get the result of the validation as soon as its available.

            @return:            Protocol instance which sent the validation
                                request.
                                (type: twisted.spred.pb.RemoteReference)
            @rtype:             twisted.internet.defer.Deferred
        """
        # For now only one Deferred is used for the result as there is no
        # reason to have a list here
        return self._authenticated

    def remote_verifyKey(self, key, protocol):
        """ Verify that the provided key matches the correct value. This method
            can be called only once, after which an error is raised.

            In case the key could be validated the protocol is registered with
            the connection.

            @param key:         Key which should be validated.
            @type  key:         str

            @param protocol:    Protocol who is responsible for the
                                validation request and one partner of the
                                new connection.
            @type  protocol:    twisted.spread.pb.RemoteReference

            @return:            None
        """
        if self._authenticated.called:
            return Failure(InvalidKey('Only one guess is possible.'))

        if isinstance(protocol, Failure):
            self._authenticated.errback(protocol)
        else:
            if self._key != key:
                e = Failure(InvalidKey('Wrong key supplied.'))
                self._authenticated.errback(e)
                return e

            self._authenticated.callback(protocol)


class LoopbackConnection(object):
    def __init__(self, protocol):
        """ Initialize the loopback connection for an endpoint.

            @param protocol:    Protocol instance providing loopback
                                functionality in the endpoint.
            @type  protocol:    rce.core.network.Protocol
        """
        self._protocol = protocol

    def getProtocol(self, _):
        """ Get the protocol which is part of this connection.

            @return:            Protocol which belongs to the endpoint and is
                                part of this connection.
            @rtype:             rce.core.network.Protocol
                                (subclass of rce.core.base.Proxy)
        """
        return self._protocol

    def destroy(self):
        """ Method should be called to destroy the endpoint connection and will
            take care of destroying the participating protocols as well as
            deleting all circular references.
        """
        self._protocol.destroy()

        self._protocol = None


class EndpointConnection(object):
    """ Representation of a connection between two endpoints, where the two
        endpoints are not the same.
    """
    def __init__(self, endpointA, endpointB):
        """ Initialize the connection between the two endpoints.
            The connection will be scheduled to be created here.

            @param endpointX:   Endpoint which is part of the new connection.
            @type  endpointX:   rce.core.network.Endpoint
        """
        assert endpointA != endpointB

        # Register the endpoints and create Protocol proxies
        self._serverEndpoint = endpointA
        self._clientEndpoint = endpointB

        self._serverProtocol = Protocol(endpointA)
        self._clientProtocol = Protocol(endpointB)

        # Create the keys used to validate the connection
        connectionID = uuid4().bytes
        serverKey = uuid4().bytes
        clientKey = uuid4().bytes

        # Create Validators and get result Deferred
        authServer = _ConnectionValidator(serverKey)
        authClient = _ConnectionValidator(clientKey)
        authServerResult = authServer.result
        authClientResult = authClient.result

        authenticator = DeferredList([authServerResult, authClientResult])
        authenticator.addCallback(self._validate)
        authenticator.addErrback(self._logError)

        readyServer = endpointA.prepareConnection(connectionID, serverKey,
                                                  authClient)
        readyClient = endpointB.prepareConnection(connectionID, clientKey,
                                                  authServer)
        ready = DeferredList([readyServer, readyClient])
        ready.addCallback(self._getAddress)
        ready.addCallback(self._connect, connectionID)
        ready.addErrback(self._connectPrepError, authenticator)
        ready.addErrback(self._logError)

    def _getAddress(self, result):
        """ Internally used method which is part of a callback chain.
            Its task is to verify that both endpoints are ready for the
            connection attempt. In case both signal readiness the address
            of the designated server endpoint is retrieved.

            @param result:      Response of the DeferredList containing the
                                Deferreds of the 'prepareConnection' calls.

            @return:            Address of the endpoint's internal
                                communication server.
            @rtype:             twisted.internet.address.IPv4Address
        """
        ((serverReady, _), (clientReady, _)) = result

        if not (serverReady and clientReady):
            # There was a problem in making the server/client ready for the
            # connection attempt
            # TODO: What should we do here?
            return Failure(InternalError('Server/Client could not be prepared '
                                         'for connection attempt.'))

        return self._serverEndpoint.getAddress()

    def _connect(self, addr, connID):
        """ Internally used method which is part of a callback chain.
            Its task is to send the 'connect' command to the client.

            @param addr:        Address of the endpoint's internal
                                communication server.
            @rtype:             twisted.internet.address.IPv4Address

            @param connID:      Connection ID which is used to identify the
                                appropriate authentication key.
            @type  connID:      str

            @return:            None.
            @rtype:             twisted.internet.defer.Deferred
        """
        return self._clientEndpoint.connect(connID, (addr.host, addr.port))

    def _connectPrepError(self, failure, authenticator):
        """ Internally used method which is part of an errback chain.
            Its task is to signal to the authenticator that the connection can
            not be attempted by cancelling the Deferred.
        """
        authenticator.cancel()
        return failure

    def _validate(self, result):
        """ Internally used method which is part of a callback chain.
            Its task is to verify that both sides of the connection could be
            authenticated. In case both signal success the corresponding
            protocols are registered.
        """
        ((serverAuth, clientProtocol), (clientAuth, serverProtocol)) = result

        if not (serverAuth and clientAuth):
            # There was a problem in authenticating the connection
            # TODO: What should we do here?
            return Failure(InternalError('Connection could not be '
                                         'authenticated.'))

        self._serverProtocol.callback(serverProtocol)
        self._clientProtocol.callback(clientProtocol)

    def _logError(self, failure):
        """ Internally used method to print out the errors for now...
        """
        try:
            failure.printTraceback()
        except:
            print('Could not print traceback of failure, print error '
                  'message instead:')
            print(failure.getErrorMessage())

    def getProtocol(self, endpoint):
        """ Get the protocol which is part of this connection and belongs to
            the given endpoint.

            @param endpoint:    Endpoint to which the protocol has to belong.
            @type  endpoint:    rce.core.network.Endpoint

            @return:            Protocol which belongs to the endpoint and is
                                part of this connection.
            @rtype:             rce.core.network.Protocol
                                (subclass of rce.core.base.Proxy)
        """
        if not (self._serverProtocol and self._serverEndpoint and
                self._clientProtocol and self._clientEndpoint):
            raise ConnectionError('Endpoint connection is dead.')

        if self._serverEndpoint == endpoint:
            return self._serverProtocol
        elif self._clientEndpoint == endpoint:
            return self._clientProtocol
        else:
            raise InternalError('The endpoint is not part of this connection.')

    def destroy(self):
        """ Method should be called to destroy the endpoint connection and will
            take care of destroying the participating protocols as well as
            deleting all circular references.
        """
        self._serverProtocol.destroy()
        self._clientProtocol.destroy()

        self._serverProtocol = None
        self._clientProtocol = None

        self._serverEndpoint = None
        self._clientEndpoint = None


class InterfaceConnection(object):
    """ Representation of a connection between an interface and a protocol,
        where both blong to the same endpoint.
    """
    def __init__(self, interface, protocol):
        """ Initialize the interface-protocol connection.

            @param interface:   Interface which is on one side of the
                                connection.
            @type  interface:   rce.core.network.Interface

            @param protocol:    Protocol which is on one side of the
                                connection.
            @type  protocol:    rce.core.network.Protocol
        """
        assert protocol._endpoint == interface._endpoint

        self._interface = interface
        interface.registerConnection(self)

        self._protocol = protocol
        protocol.registerConnection(self)

        self._users = set()

    def registerUser(self, connection, remoteID):
        assert connection not in self._users
        self._users.add(connection)
        self._interface.registerRemoteID(self._protocol, remoteID)

    def unregisterUser(self, connection, remoteID):
        assert connection in self._users
        self._users.remove(connection)
        self._interface.unregisterRemoteID(self._protocol, remoteID)

    def getID(self):
        """ Get the unique ID of the interface which is part of this
            connection.

            @return:            Unique ID of the interface.
            @rtype:             uuid.UUID
        """
        return self._interface.UID

    def destroy(self):
        """ Method should be called to destroy the interface-protocol
            connection and will take care of destroying all objects owned by
            this connection as well as deleting all circular references.
        """
        for user in self._users.copy():
            user.destroy()

        assert len(self._users) == 0

        self._interface.unregisterConnection(self)
        self._interface = None

        self._protocol.unregisterConnection(self)
        self._protocol = None


class Connection(object):
    """ Representation of a connection between two interfaces.
    """
    def __init__(self, connectionA, connectionB):
        """ Initialize the connection, which is represented by two
            interface-protocol connections.

            @param connectionX: Interface-Protocol connection which is part
                                of the connection.
            @type  connectionX: rce.core.network.InterfaceConnection
        """
        assert connectionA != connectionB

        self._connectionA = connectionA
        connectionA.registerUser(self, connectionB.getID())

        self._connectionB = connectionB
        connectionB.registerUser(self, connectionA.getID())

        self._cbs = set()

    def notifyOnDeath(self, cb):
        """ Method is used to  to register a callback which will be called
            when the connection died.

            @param cb:          Callback which should be registered. The
                                callback should take the died connection as
                                only argument.
            @type  cb:          callable
        """
        assert callable(cb)

        try:
            self._cbs.add(cb)
        except AttributeError:
            raise AlreadyDead('{0} is already '
                              'dead.'.format(self.__class__.__name__))

    def dontNotifyOnDeath(self, cb):
        """ Method is used to unregister a callback which should have been
            called when the connection died.

            @param cb:          Callback which should be unregistered.
            @type  cb:          callable
        """
        try:
            self._cbs.remove(cb)
        except AttributeError:
            pass

    def destroy(self):
        """ Method should be called to destroy the connection and will
            take care deleting all circular references.
        """
        if self._cbs:
            for cb in self._cbs:
                cb(self)

            self._cbs = None

        if self._connectionA:
            self._connectionA.unregisterUser(self, self._connectionB.getID())
            self._connectionB.unregisterUser(self, self._connectionA.getID())

            self._connectionA = None
            self._connectionB = None
        else:
            print('network.Connection destroy() called multiple times...')

########NEW FILE########
__FILENAME__ = robot
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/core/robot.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# twisted specific imports
from twisted.internet.address import IPv4Address

# rce specific imports
from rce.util.settings import getSettings
from rce.util.network import isLocalhost
from rce.core.error import InvalidRequest
from rce.core.network import Endpoint, Namespace, EndpointAvatar


class Robot(Namespace):
    """ Representation of a namespace which has a WebSocket connection from a
        robot assigned and is part of the cloud engine internal communication.
    """
    def __init__(self, endpoint):
        """ Initialize the Robot.

            @param endpoint:    Endpoint in which the robot was created.
            @type  endpoint:    rce.core.network.Endpoint
        """
        super(Robot, self).__init__(endpoint)

    def getWebsocketAddress(self):
        """ Get the address which can be used to connect to this robot
            namespace.

            @return:            Address of the endpoint containing the robot
                                namespace. The address has the form
                                    [IP]:[port] (type: str)
            @rtype:             twisted.internet.defer.Deferred
        """
        return self._endpoint.getWebsocketAddress()


class RobotEndpoint(Endpoint):
    """ Representation of an endpoint which is a process that acts as a server
        for WebSocket connections from robots and is part of the cloud engine
        internal communication.
    """
    def __init__(self, network, distributor, port):
        """ Initialize the Environment Endpoint.

            @param network:     Network to which the endpoint belongs.
            @type  network:     rce.master.network.Network

            @param distributor: Distributor which is responsible for assigning
                                new robot WebSocket connections to robot
                                endpoints.
            @type  distributor: rce.core.robot.Distributor

            @param port:        Port where the robot process is listening for
                                connections to other endpoints.
            @type  port:        int
        """
        super(RobotEndpoint, self).__init__(network)

        self._distributor = distributor
        distributor.registerRobotProcess(self)

        self._port = port

    @property
    def active(self):
        """ The number of active robot websocket connections in the
            robot process.
        """
        return len(self._namespaces)

    def getAddress(self):
        """ Get the address of the robot endpoint's internal communication
            server.

            @return:            Address of the robot endpoint's internal
                                communication server.
                                (type: twisted.internet.address.IPv4Address)
            @rtype:             twisted.internet.defer.Deferred
        """
        def cb(remote):
            ip = remote.broker.transport.getPeer().host
            ip = getSettings().internal_IP if isLocalhost(ip) else ip
            return IPv4Address('TCP', ip, self._port)

        return self().addCallback(cb)

    def getWebsocketAddress(self):
        """ Get the address which can be used to connect to the robot
            namespaces which belong to this endpoint.

            @return:            Address of the endpoint process. The address
                                has the form [IP]:[port] (type: str)
            @rtype:             twisted.internet.defer.Deferred
        """
        return self.callRemote('getWebsocketAddress')

    def registerRemoteRobot(self, remoteRobot):
        """ Register a Namespace object of the endpoint.

            @param remoteRobot: Reference to Robot namespace in Robot process.
            @type  remoteRobot: twisted.spread.pb.RemoteReference

            @return:            New Robot instance.
            @rtype:             rce.core.robot.Robot
                                (subclass of rce.core.base.Proxy)
        """
        robot = Robot(self)
        robot.callback(remoteRobot)
        return robot

    def destroy(self):
        """ Method should be called to destroy the robot endpoint and will take
            care of destroying all objects owned by this RobotEndpoint as well
            as deleting all circular references.
        """
        if self._distributor:
            print('Destroying Connection to Robot Process.')
            self._distributor.unregisterRobotProcess(self)
            self._distributor = None
            super(RobotEndpoint, self).destroy()
        else:
            print('robot.RobotEndpoint destroy() called multiple times...')


class RobotEndpointAvatar(EndpointAvatar):
    """ Avatar for internal PB connection form a Robot Endpoint.
    """
    def perspective_setupNamespace(self, remoteRobot, userID, robotID):
        """ Register a Robot namespace with the Master process.

            @param remoteRobot: Reference to the Robot namespace in the Robot
                                process.
            @type  remoteRobot: twisted.spread.pb.RemoteReference

            @param userID:      User ID of the robot owner.
            @type  userID:      str

            @param robotID:     Unique ID which is used to identify the robot.
            @type  robotID:     str
        """
        user = self._realm.getUser(userID)
        robot = self._endpoint.registerRemoteRobot(remoteRobot)

        try:
            user.registerRobot(robot, robotID)
        except InvalidRequest:
            robot.destroy()
            raise

########NEW FILE########
__FILENAME__ = user
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/core/user.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# twisted specific imports
from twisted.spread.pb import Avatar

# rce specific imports
from rce.util.name import validateName, IllegalName
from rce.core.error import InvalidRequest
from rce.core.view import MonitorView, AdminMonitorView, ControlView
from rce.core.wrapper import Robot


class User(Avatar):
    """ Represents a User avatar. It has references to all objects the User is
        currently using. For this to happen, each Robot object in the robot
        processes has a remote reference to on of the User instances in the
        Master. To modify the data the Robot objects should used Views.
    """
    def __init__(self, realm, userID):
        """ Initialize the User.

            @param realm:       The realm of the RoboEarth Cloud Engine master.
            @type  realm:       rce.core.RoboEarthCloudEngine

            @param userID:      The user ID associated with the user.
            @type  userID:      str
        """
        self._realm = realm
        self._userID = userID

        self.robots = {}
        self.containers = {}
        self.connections = {}

    @property
    def realm(self):
        """ Realm to which this User belongs. """
        return self._realm

    @property
    def userID(self):
        """ User ID of this User. """
        return self._userID

    def registerRobot(self, robot, robotID):
        """ Create a new Robot Wrapper.

            # TODO: Add description of arguments

            @raise:             rce.core.error.InvalidRequest
        """
        try:
            validateName(robotID)
        except IllegalName as e:
            raise InvalidRequest('Robot ID is invalid: {0}'.format(e))

        if (robotID in self.robots or robotID in self.containers):
            raise InvalidRequest('ID is already used for a container '
                                 'or robot.')

        robot = Robot(robot)
        self.robots[robotID] = robot
        robot.notifyOnDeath(self.robotDied)

    def perspective_getUserView(self, console=True):
        """
        """
        if self._userID == 'admin' and not console:
            raise InvalidRequest('Administrator cannot login via robot')
        elif self._userID == 'admin':
            return AdminMonitorView()
        elif not console:
            return ControlView()
        else:
            return {'console': MonitorView(), 'robot': ControlView()}

    def getEndpoint(self, tag):
        """ Get an endpoint of the user matching the given tag.

            @param tag:         Tag which is used to identify the endpoint which
                                should be returned.
            @type  tag:         str

            @return:            Endpoint which was requested.
            @rtype:             rce.core.network.Endpoint

            @raise:             rce.core.error.InvalidRequest
        """
        if tag in self.robots:
            return self.robots[tag]
        elif tag in self.containers:
            return self.containers[tag]
        else:
            raise InvalidRequest('Can not get a non existent endpoint '
                                 "'{0}'.".format(tag))

    def containerDied(self, container):
        """ Callback which is used to inform the user of the death of a
            container.
        """
        if self.containers:
            for uid, candidate in self.containers.iteritems():
                if candidate == container:
                    del self.containers[uid]
                    break
        else:
            print('Received notification for dead Container, '
                  'but User is already destroyed.')

    def robotDied(self, robot):
        """ Callback which is used to inform the user of the death of a robot.
        """
        if self.robots:
            for uid, candidate in self.robots.iteritems():
                if candidate == robot:
                    del self.robots[uid]
                    break
        else:
            print('Received notification for dead Robot, '
                  'but User is already destroyed.')

    def connectionDied(self, connection):
        """ Callback which is used to inform the user of the death of a
            connection.
        """
        if self.connections:
            for uid, candidate in self.connections.iteritems():
                if candidate == connection:
                    del self.connections[uid]
                    break
        else:
            print('Received notification for dead Connection, '
                  'but User is already destroyed.')

    def destroy(self):
        """ Method should be called to destroy the user and will take care of
            destroying all objects owned by this User as well as deleting all
            circular references.
        """
        for connection in self.connections.itervalues():
            connection.dontNotifyOnDeath(self.connectionDied)

        for container in self.containers.itervalues():
            container.dontNotifyOnDeath(self.containerDied)

        for robot in self.robots.itervalues():
            robot.dontNotifyOnDeath(self.robotDied)

        for container in self.containers.itervalues():
            container.destroy()

        for robot in self.robots.itervalues():
            robot.destroy()

        self.connections = None
        self.containers = None
        self.robots = None

########NEW FILE########
__FILENAME__ = view
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     view.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker, Mayank Singh
#
#

# Python specific imports
from uuid import uuid4
from hashlib import md5

# twisted specific imports
from twisted.internet.defer import DeferredList
from twisted.spread.pb import Viewable

# rce specific imports
from rce.util.name import validateName, IllegalName
from rce.core.error import InvalidRequest
from rce.core.wrapper import Container
from rce.slave.interface import Types


class ControlView(Viewable):
    """ View implementing all control actions which a user can perform to
        interact with the cloud engine.
    """
    def view_createContainer(self, user, tag, data={}):
        """ Create a new Container object.

            @param user:        User for which the container will be created.
            @type  user:        rce.core.user.User

            @param tag:         Tag which is used to identify the container
                                in subsequent requests.
            @type  tag:         str

            @param data:        Extra data used to configure the container.
            @type  data:        dict
        """
        try:
            validateName(tag)
        except IllegalName as e:
            raise InvalidRequest('Container tag is invalid: {0}'.format(e))

        if tag in user.containers or tag in user.robots:
            raise InvalidRequest('Tag is already used for a container '
                                 'or robot.')

        namespace, remote_container = user.realm.createContainer(user.userID,
                                                                 data)
        container = Container(namespace, remote_container)
        user.containers[tag] = container
        container.notifyOnDeath(user.containerDied)

        m = 'Container {0} successfully created.'.format(tag)
        d = DeferredList([namespace(), remote_container()],
                         fireOnOneErrback=True, consumeErrors=True)
        return d.addCallback(lambda _: m)

    def view_destroyContainer(self, user, tag):
        """ Destroy a Container object.

            @param user:        User for which the container will be destroyed.
            @type  user:        rce.core.user.User

            @param tag:         Tag which is used to identify the container
                                which should be destroyed.
            @type  tag:         str
        """
        try:
            container = user.containers.pop(tag)
        except KeyError:
            raise InvalidRequest('Can not destroy non existent container.')

        container.dontNotifyOnDeath(user.containerDied)
        container.destroy()

        # TODO: Return some info about success/failure of request

    def view_addNode(self, user, cTag, nTag, pkg, exe, args='', name='',
                     namespace=''):
        """ Add a node to a ROS environment.

            @param user:        User for which the node will be added.
            @type  user:        rce.core.user.User

            @param cTag:        Tag which is used to identify the ROS
                                environment to which the node should be added.
            @type  cTag:        str

            @param nTag:        Tag which is used to identify the node in
                                subsequent requests.
            @type  nTag:        str

            @param pkg:         Name of ROS package where the node can be
                                found.
            @type  pkg:         str

            @param exe:         Name of executable (node) which should be
                                launched.
            @type  exe:         str

            @param args:        Additional arguments which should be used for
                                the launch. Can contain the directives
                                $(find PKG) or $(env VAR). Other special
                                characters as '$' or ';' are not allowed.
            @type  args:        str

            @param name:        Name of the node under which the node should be
                                launched.
            @type  name:        str

            @param namespace:   Namespace in which the node should be started
                                in the environment.
            @type  namespace:   str
        """
        try:
            user.containers[cTag].addNode(nTag, pkg, exe, args, name, namespace)
        except KeyError:
            raise InvalidRequest('Can not add Node, because Container {0} '
                                 'does not exist.'.format(cTag))

        # TODO: Return some info about success/failure of request

    def view_removeNode(self, user, cTag, nTag):
        """ Remove a node from a ROS environment.

            @param user:        User for which the node will be destroyed.
            @type  user:        rce.core.user.User

            @param cTag:        Tag which is used to identify the ROS
                                environment from which the node should be
                                removed.
            @type  cTag:        str

            @param nTag:        Tag which is used to identify the ROS node
                                which should removed.
            @type  nTag:        str
        """
        try:
            user.containers[cTag].removeNode(nTag)
        except KeyError:
            raise InvalidRequest('Can not remove Node, because Container {0} '
                                 'does not exist.'.format(cTag))

        # TODO: Return some info about success/failure of request

    def view_addParameter(self, user, cTag, name, value):
        """ Add a parameter to a ROS environment.

            @param user:        User for which the parameter will be added.
            @type  user:        rce.core.user.User

            @param cTag:        Tag which is used to identify the ROS
                                environment to which the parameter should be
                                added.
            @type  cTag:        str

            @param name:        Name of the parameter which should be added.
                                It is also used to identify the parameter in
                                subsequent requests.
            @type  name:        str

            @param value:       Value of the parameter which should be added.
                                String values can contain the directives
                                $(find PKG) or $(env VAR).
            @type  value:       str, int, float, bool, list
        """
        try:
            user.containers[cTag].addParameter(name, value)
        except KeyError:
            raise InvalidRequest('Can not add Parameter, because Container '
                                 '{0} does not exist.'.format(cTag))

        # TODO: Return some info about success/failure of request

    def view_removeParameter(self, user, cTag, name):
        """ Remove a parameter from a ROS environment.

            @param user:        User for which the parameter will be destroyed.
            @type  user:        rce.core.user.User

            @param cTag:        Tag which is used to identify the ROS
                                environment from which the parameter should be
                                removed.
            @type  cTag:        str

            @param name:        Name of the parameter which should be removed.
            @type  name:        str
        """
        try:
            user.containers[cTag].removeParameter(name)
        except KeyError:
            raise InvalidRequest('Can not remove Parameter, because Container '
                                 '{0} does not exist.'.format(cTag))

        # TODO: Return some info about success/failure of request

    def view_addInterface(self, user, eTag, iTag, iType, clsName, addr=''):
        """ Add an interface to an endpoint, i.e. a ROS environment or a
            Robot object.

            @param user:        User for which the interface will be added.
            @type  user:        rce.core.user.User

            @param eTag:        Tag which is used to identify the endpoint to
                                which the interface should be added; either
                                a container tag or robot ID.
            @type  eTag:        str

            @param iTag:        Tag which is used to identify the interface in
                                subsequent requests.
            @type  iTag:        str

            @param iType:       Type of the interface. The type consists of a
                                prefix and a suffix.
                                 - Valid prefixes are:
                                     ServiceClient, ServiceProvider,
                                     Publisher, Subscriber
                                 - Valid suffixes are:
                                     Interface, Converter, Forwarder
            @type  iType:       str

            @param clsName:     Message type/Service type consisting of the
                                package and the name of the message/service,
                                i.e. 'std_msgs/Int32'.
            @type  clsName:     str

            @param addr:        ROS name/address which the interface should
                                use. Only necessary if the suffix of @param
                                iType is 'Interface'.
            @type  addr:        str
        """
        if iType.endswith('Converter') or iType.endswith('Forwarder'):
            try:
                user.robots[eTag].addInterface(iTag, iType, clsName)
            except KeyError:
                raise InvalidRequest('Can not add Interface, because Robot '
                                     '{0} does not exist.'.format(eTag))
        elif iType.endswith('Interface'):
            try:
                user.containers[eTag].addInterface(iTag, iType, clsName, addr)
            except KeyError:
                raise InvalidRequest('Can not add Interface, because '
                                     'Container {0} does not '
                                     'exist.'.format(eTag))
        else:
            raise InvalidRequest('Interface type is invalid (Unknown suffix).')

        # TODO: Return some info about success/failure of request

    def view_removeInterface(self, user, eTag, iTag):
        """ Remove an interface from an endpoint, i.e. a ROS environment or a
            Robot object.

            @param user:        User for which the interface will be destroyed.
            @type  user:        rce.core.user.User

            @param eTag:        Tag which is used to identify the endpoint from
                                which the interface should be removed; either
                                a container tag or robot ID.
            @type  eTag:        str

            @param iTag:        Tag which is used to identify the interface
                                which should be removed.
            @type  iTag:        str
        """
        user.getEndpoint(eTag).removeInterface(iTag)

        # TODO: Return some info about success/failure of request

    def view_addConnection(self, user, tagA, tagB):
        """ Create a connection between two interfaces.

            @param user:        User for which the connection will be created.
            @type  user:        rce.core.user.User

            @param tagX:        Tag which is used to identify the interface
                                which should be connected. It has to be of the
                                form:
                                    [endpoint tag]/[interface tag]
                                For example:
                                    testRobot/logPublisher
            @type  tagX:        str
        """
        eTagA, iTagA = tagA.split('/', 2)
        eTagB, iTagB = tagB.split('/', 2)

        ifA = user.getEndpoint(eTagA).getInterface(iTagA)
        ifB = user.getEndpoint(eTagB).getInterface(iTagB)

        if ifA.clsName != ifB.clsName:
            raise InvalidRequest('Can not connect two interfaces with '
                                 'different message/service type.')

        if not Types.connectable(ifA.iType, ifB.iType):
            raise InvalidRequest('Can not connect an interface of type {0} '
                                 'and an interface of type '
                                 '{1}.'.format(Types.decode(ifA.iType),
                                               Types.decode(ifB.iType)))

        key = int(md5(tagA).hexdigest(), 16) ^ int(md5(tagB).hexdigest(), 16)

        if key in user.connections:
            raise InvalidRequest('Can not add the same connection twice.')

        connection = user.realm.createConnection(ifA.obj, ifB.obj)
        user.connections[key] = connection
        connection.notifyOnDeath(user.connectionDied)

        # TODO: Return some info about success/failure of request

    def view_removeConnection(self, user, tagA, tagB):
        """ Destroy a connection between two interfaces.

            @param user:        User for which the connection will be destroyed.
            @type  user:        rce.core.user.User

            @param tagX:        Tag which is used to identify the interface
                                which should be disconnected. It has to be of
                                the form:
                                    [endpoint tag]/[interface tag]
                                For example:
                                    testRobot/logPublisher
            @type  tagX:        str
        """
        key = int(md5(tagA).hexdigest(), 16) ^ int(md5(tagB).hexdigest(), 16)

        try:
            connection = user.connections.pop(key)
        except KeyError:
                raise InvalidRequest('Can not disconnect two unconnected '
                                     'interfaces.')

        connection.dontNotifyOnDeath(user.connectionDied)
        connection.destroy()

        # TODO: Return some info about success/failure of request


class MonitorView(Viewable):
    """ View implementing all monitor actions which a normal user can perform to
        interact with the cloud engine.
    """
    def view_update_user(self, user, new_pw, old_pw):
        """ Remote call to edit user information.

            @param user:        User for which the login information will be
                                updated.
            @type  user:        rce.core.user.User

            @param new_pw:      The new password
            @type  new_pw:      str

            @param old_pw:      Old password
            @type  old_pw:      str
        """
        user.realm._checker.passwd(user.userID, new_pw, old_pw)

    def view_list_containers(self, user):
        """ Remote call to list containers under the logged-in user.

            @param user:        User for which the running container should be
                                listed.
            @type  user:        rce.core.user.User

            @return:            List of the container tags of running
                                containers.
            @rtype:             [ str ]
        """
        return user.containers.keys()

    def view_list_robots(self, user):
        """ List Robots under the logged in user.

            @param user:        User for which the connected robots should be
                                listed.
            @type  user:        rce.core.user.User

            @return:            List of the robot IDs of connected robots.
            @rtype:             [ str ]
        """
        return user.robots.keys()

    def view_get_rosapi_connect_info(self, user, tag):
        """ Remote call to get ROSAPI request URL and key for a particular
            container.

            @param user:        User who owns the container for which the URL
                                is requested.
            @type  user:        rce.core.user.User

            @param tag:         Tag used to identify the container.
            @type  tag:         str

            @return:            URL which can be used to connect to the rosproxy
                                running inside the container as well as the key
                                necessary to use the rosproxy.
                                (type: (str, str))
            @rtype:             twisted.internet.defer.Deferred
        """
        try:
            container = user.containers[tag]
        except KeyError:
            raise InvalidRequest('Container {0} does not exist.'.format(tag))

        uid = uuid4().hex
        container._obj.registerConsole(user.userID, uid)
        d = container.getConnectInfo()
        d.addCallback(lambda addr: (addr, uid))
        return d


class AdminMonitorView(Viewable):
    """ View implementing all monitor actions which an admin user can perform to
        interact with the cloud engine.
    """
    def view_list_machines(self, user):
        """ Remote call to list machine IPs.
        """
        return [machine.IP for machine in user.realm._balancer._machines]

    def view_machine_containers(self, user, machineIP):
        """ Remote call to list containers in a machine with given IP.

            @param user:        User who requested the container list.
            @type  user:        rce.core.user.User

            @param machineIP:   IP of machine for which the running containers
                                should be listed.
            @type  machineIP:   str

            @return:            List of running containers.
            @rtype:             # TODO: Depends on modification below.
        """
        # TODO: Can not return rce.master.container.Container instances need
        #       some conversion into string, tuple, or some other base type
        try:
            return (machine for machine in user.realm._balancer._machines
                    if machineIP == machine.IP).next()._containers
        except StopIteration:
            raise InvalidRequest('No such machine.')

    def view_stats_machine(self, user, machineIP):
        """ Remote call to list stats of machine with given IP.

            @param user:        User who requested the stats.
            @type  user:        rce.core.user.User

            @param machineIP:   IP of machine for which the stats should be
                                listed.
            @type  machineIP:   str

            @return:            Stats of the machine.
            @rtype:             { str : int }
        """
        try:
            machine = (machine for machine in user.realm._balancer._machines
                       if machineIP == machine.IP).next()
            return {'active':machine.active, 'size':machine.size}
        except StopIteration:
            raise InvalidRequest('No such machine.')

    def view_list_users(self, user):
        """ Remote call to list all users currently logged into
            the RoboEarth Cloud Engine.

            @param user:        User who requested the listing of logged-in
                                users.
            @type  user:        rce.core.user.User

            @return:            List of the user IDs of logged-in users.
            @rtype:             [ str ]
        """
        return user.realm._users.keys()

    def view_add_user(self, user, username, password):
        """ Remote call to add user.

            @param user:        User who requested the addtion of a new user.
            @type  user:        rce.core.user.User

            @param username:    The username of the new user.
            @type  username:    str

            @param password:    The password of the new user.
            @type  password:    str
        """
        user.realm._checker.addUser(username, password)

    def view_remove_user(self, user, username):
        """ Remote call to remove user.

            @param user:        User who requested the removal of the user.
            @type  user:        rce.core.user.User

            @param username:    The username of the user which should be
                                removed.
            @type  username:    str
        """
        user.realm._checker.removeUser(username)

    def view_update_user(self, user, username, password):
        """ Remote call to edit user information.

            @param user:        User who requested the addtion of a new user.
            @type  user:        rce.core.user.User

            @param username:    The username of the user which should be
                                updated.
            @type  username:    str

            @param password:    The new password for the user which should be
                                updated.
            @type  password:    str
        """
        user.realm._checker.passwd(username, password, True)

    def view_list_containers_by_user(self, user, userID):
        """ Remote call to list containers under a given user.

            @param user:        User who requested the listing of the containers
                                of a particular user.
            @type  user:        rce.core.user.User

            @param userID:      The username of the user for which the
                                containers should be listed.
            @type  userID:      str
        """
        return user._realm.getUser(userID).containers.keys()

    def view_list_robots_by_user(self, user, userID):
        """ List robots under the user specified.

            @param user:        User who requested the listing of the robots
                                of a particular user.
            @type  user:        rce.core.user.User

            @param userID:      The username of the user for which the robots
                                should be listed.
            @type  userID:      str
        """
        return user._realm.getUser(userID).robots.keys()

########NEW FILE########
__FILENAME__ = wrapper
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     wrapper.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# rce specific imports
from rce.util.name import validateName, IllegalName
from rce.core.error import InvalidRequest, AlreadyDead
from rce.slave.interface import Types


class _Wrapper(object):
    """ Base class for Wrapper classes, which are used to store additional
        information (of interest to the User) with the cloud engine
        representation of the objects.
    """
    def __init__(self, obj):
        """ Initialize the Wrapper around the object 'obj'.

            @param obj:         Object which should be wrapped.
            @type  obj:         rce.core.base.Proxy
        """
        self._obj = obj
        obj.notifyOnDeath(self._selfDied)

        self._cbs = set()

    def notifyOnDeath(self, cb):
        """ Method is used to forward 'notifyOnDeath' calls to the wrapped
            object. It is used to register a callback which will be called
            when the wrapped object died.

            @param cb:          Callback which should be registered. The
                                callback should take the died object as only
                                argument.
            @type  cb:          callable
        """
        assert callable(cb)

        try:
            self._cbs.add(cb)
        except AttributeError:
            raise AlreadyDead('{0} is already '
                              'dead.'.format(self.__class__.__name__))

    def dontNotifyOnDeath(self, cb):
        """ Method is used to forward 'dontNotifyOnDeath' calls to the wrapped
            object. It is used to unregister a callback which should have been
            called when the wrapped object died.

            @param cb:          Callback which should be unregistered.
            @type  cb:          callable
        """
        try:
            self._cbs.remove(cb)
        except AttributeError:
            pass

    def _selfDied(self, _):
        for cb in self._cbs:
            cb(self)

        self._cbs = None

    def destroy(self):
        """ Method should be called to destroy the Wrapper and will take care
            of destroying the wrapped object.
        """
        self._obj.destroy()
        self._obj = None


class Robot(_Wrapper):
    """ Wrapper for a Robot object. The underlying object is a Robot namespace.
    """
    def __init__(self, namespace):
        """ Initialize the Robot wrapper.

            @param namespace:   Namespace of the Robot object which should be
                                wrapped.
            @type  namespace:   rce.core.robot.Robot
        """
        super(Robot, self).__init__(namespace)

        self._interfaces = {}

    def getConnectInfo(self):
        """ Get the information necessary to the robot to establish a WebSocket
            connection.

            @return:            The authentication key and address which are
                                used for the WebSocket connection.
            @rtype:             twisted.internet.defer.Deferred
        """
        d = self._obj.getWebsocketAddress()
        d.addCallback(lambda addr: addr)
        return d

    def addInterface(self, iTag, iType, clsName):
        """ Add an interface to the Robot object.

            @param iTag:        Tag which is used to identify the interface in
                                subsequent requests.
            @type  iTag:        str

            @param iType:       Type of the interface. The type consists of a
                                prefix and a suffix.
                                 - Valid prefixes are:
                                     ServiceClient, ServiceProvider,
                                     Publisher, Subscriber
                                 - Valid suffixes are:
                                     Converter, Forwarder
            @type  iType:       str

            @param clsName:     Message type/Service type consisting of the
                                package and the name of the message/service,
                                i.e. 'std_msgs/Int32'.
            @type  clsName:     str
        """
        try:
            validateName(iTag)
        except IllegalName as e:
            raise InvalidRequest('Interface tag is invalid: {0}'.format(e))

        if iTag in self._interfaces:
            raise InvalidRequest("Can not use the same interface tag '{0}' "
                                 'in the same robot twice.'.format(iTag))

        try:
            iType = Types.encode(iType)
        except TypeError:
            raise InvalidRequest('Interface type is invalid.')

        interface = self._obj.createInterface(iType, clsName, iTag)
        interface = Interface(interface, iType, clsName)
        self._interfaces[iTag] = interface
        interface.notifyOnDeath(self._interfaceDied)

    def removeInterface(self, iTag):
        """ Remove an interface from the Robot object.

            @param iTag:        Tag which is used to identify the interface
                                which should be removed.
            @type  iTag:        str
        """
        try:
            self._interfaces.pop(iTag).destroy()
        except KeyError:
            raise InvalidRequest('Can not remove a non existent interface '
                                 "'{0}' from the robot.".format(iTag))

    def getInterface(self, iTag):
        """ Return the wrapped interface instance matching the given tag.

            @param iTag:        Tag which is used to identify the interface
                                which should be returned.
            @type  iTag:        str

            @return:            Wrapped interface instance which was requested.
            @rtype:             rce.core.user.Interface
        """
        try:
            return self._interfaces[iTag]
        except KeyError:
            raise InvalidRequest('Can not get a non existent interface '
                                 "'{0}' from the robot.".format(iTag))

    def _interfaceDied(self, interface):
        if self._interfaces:
            for key, value in self._interfaces.iteritems():
                if value == interface:
                    del self._interfaces[key]
                    break
        else:
            print('Received notification for dead Interface, '
                  'but Robot is already destroyed.')

    def destroy(self):
        """ Method should be called to destroy the robot and will take care of
            destroying all objects owned by this Robot as well as deleting all
            circular references.
        """
        for interface in self._interfaces.itervalues():
            interface.dontNotifyOnDeath(self._interfaceDied)

        self._interfaces = None

        super(Robot, self).destroy()


class Container(_Wrapper):
    """ Wrapper for a Container object. The underlying object is a Environment
        namespace.
    """
    def __init__(self, namespace, container):
        """ Initialize the Container wrapper.

            @param namespace:   Namespace of the Container object which should
                                be wrapped.
            @type  namespace:   rce.core.environment.Environment

            @param container:   Reference to Container.
            @type  container:   rce.core.container.Container
        """
        super(Container, self).__init__(namespace)

        self._container = container
        container.notifyOnDeath(self._containerDied)

        self._nodes = {}
        self._parameters = {}
        self._interfaces = {}

    def addNode(self, nTag, pkg, exe, args, name, namespace):
        """ Add a node to the ROS environment inside the container.

            @param nTag:        Tag which is used to identify the node in
                                subsequent requests.
            @type  nTag:        str

            @param pkg:         Name of ROS package where the node can be
                                found.
            @type  pkg:         str

            @param exe:         Name of executable (node) which should be
                                launched.
            @type  exe:         str

            @param args:        Additional arguments which should be used for
                                the launch.
            @type  args:        str

            @param name:        Name of the node under which the node should be
                                launched.
            @type  name:        str

            @param namespace:   Namespace in which the node should be started
                                in the environment.
            @type  namespace:   str
        """
        try:
            validateName(nTag)
        except IllegalName:
            raise InvalidRequest('Node tag is not a valid.')

        if nTag in self._nodes:
            raise InvalidRequest("Can not use the same node tag '{0}' in the "
                                 'same container twice.'.format(nTag))

        node = self._obj.createNode(pkg, exe, args, name, namespace)
        self._nodes[nTag] = node
        node.notifyOnDeath(self._nodeDied)

    def removeNode(self, nTag):
        """ Remove a node from the ROS environment inside the container.

            @param nTag:        Tag which is used to identify the ROS node
                                which should removed.
            @type  nTag:        str
        """
        try:
            self._nodes.pop(nTag).destroy()
        except KeyError:
            raise InvalidRequest('Can not remove a non existent node '
                                 "'{0}' from the container.".format(nTag))

    def addParameter(self, name, value):
        """ Add a parameter to the ROS environment inside the container.

            @param name:        Name of the parameter which should be added.
                                It is also used to identify the parameter in
                                subsequent requests.
            @type  name:        str

            @param value:       Value of the parameter which should be added.
            @type  value:       str, int, float, bool, list
        """
        if not name:
            raise InvalidRequest('Parameter name is not a valid.')

        if name in self._parameters:
            raise InvalidRequest("Can not use the same parameter name '{0}' "
                                 'in the same container twice.'.format(name))

        parameter = self._obj.createParameter(name, value)
        self._parameters[name] = parameter
        parameter.notifyOnDeath(self._parameterDied)

    def removeParameter(self, name):
        """ Remove a parameter from the ROS environment inside the container.

            @param name:        Name of the parameter which should be removed.
            @type  name:        str
        """
        try:
            self._parameters.pop(name).destroy()
        except KeyError:
            raise InvalidRequest('Can not remove a non existent node '
                                 "'{0}' from the container.".format(name))

    def addInterface(self, iTag, iType, clsName, addr):
        """ Add an interface to the ROS environment inside the container.

            @param iTag:        Tag which is used to identify the interface in
                                subsequent requests.
            @type  iTag:        str

            @param iType:       Type of the interface. The type has to be of
                                the form:
                                    {prefix}Interface
                                whit valid prefixes:
                                    ServiceClient, ServiceProvider,
                                    Publisher, Subscriber
            @type  iType:       str

            @param clsName:     Message type/Service type consisting of the
                                package and the name of the message/service,
                                i.e. 'std_msgs/Int32'.
            @type  clsName:     str

            @param addr:        ROS name/address which the interface should
                                use.
            @type  addr:        str
        """
        try:
            validateName(iTag)
        except IllegalName:
            raise InvalidRequest('Interface tag is not a valid.')

        if iTag in self._interfaces:
            raise InvalidRequest("Can not use the same interface tag '{0}' "
                                 'in the same container twice.'.format(iTag))

        try:
            iType = Types.encode(iType)
        except TypeError:
            raise InvalidRequest('Interface type is invalid (Unknown prefix).')

        interface = self._obj.createInterface(iType, clsName, addr)
        interface = Interface(interface, iType, clsName)
        self._interfaces[iTag] = interface
        interface.notifyOnDeath(self._interfaceDied)

    def removeInterface(self, iTag):
        """ Remove an interface from the ROS environment inside the container.

            @param iTag:        Tag which is used to identify the interface
                                which should be removed.
            @type  iTag:        str
        """
        try:
            self._interfaces.pop(iTag).destroy()
        except KeyError:
            raise InvalidRequest('Can not remove a non existent interface '
                                 "'{0}' from the container.".format(iTag))

    def getInterface(self, iTag):
        """ Return the wrapped interface instance matching the given tag.

            @param iTag:        Tag which is used to identify the interface
                                which should be returned.
            @type  iTag:        str

            @return:            Wrapped interface instance which was requested.
            @rtype:             rce.core.user.Interface
        """
        try:
            return self._interfaces[iTag]
        except KeyError:
            raise InvalidRequest('Can not get a non existent interface '
                                 "'{0}' from the container.".format(iTag))

    def getConnectInfo(self):
        """ Get connection information for the given container for rosproxy
            calls.
        """
        d = self._obj.getAddress()
        d.addCallback(lambda addr: 'http://{0}:{1}/'.format(addr.host,
                                                            addr.port + 2000))
        return d

    def _containerDied(self, container):
        if self._container:
            assert container == self._container
            self._container = None
            self.destroy()
        else:
            print('Received notification for dead Container, '
                  'but Container is already destroyed.')

    def _nodeDied(self, node):
        if self._nodes:
            for key, value in self._nodes.iteritems():
                if value == node:
                    del self._nodes[key]
                    break
        else:
            print('Received notification for dead Node, '
                  'but Container is already destroyed.')

    def _parameterDied(self, parameter):
        if self._parameters:
            for key, value in self._parameters.iteritems():
                if value == parameter:
                    del self._parameters[key]
                    break
        else:
            print('Received notification for dead Parameter, '
                  'but Container is already destroyed.')

    def _interfaceDied(self, interface):
        if self._interfaces:
            for key, value in self._interfaces.iteritems():
                if value == interface:
                    del self._interfaces[key]
                    break
        else:
            print('Received notification for dead Interface, '
                  'but Container is already destroyed.')

    def destroy(self):
        """ Method should be called to destroy the container and will take care
            of destroying all objects owned by this Container as well as
            deleting all circular references.
        """
        for node in self._nodes.itervalues():
            node.dontNotifyOnDeath(self._nodeDied)

        for parameter in self._parameters.itervalues():
            parameter.dontNotifyOnDeath(self._parameterDied)

        for interface in self._interfaces.itervalues():
            interface.dontNotifyOnDeath(self._interfaceDied)

        self._nodes = None
        self._parameters = None
        self._interfaces = None

        if self._container:
            self._container.dontNotifyOnDeath(self._containerDied)
            self._container.destroy()

        super(Container, self).destroy()


class Interface(_Wrapper):
    """ Wrapper for a Container object. The underlying object is an Interface.
    """
    def __init__(self, interface, iType, clsName):
        """ Initialize the Interface wrapper.

            @param interface:   Interface which should be wrapped.
            @type  interface:   rce.core.network.Interface

            @param iType:       Type of the interface encoded as an integer.
                                Refer to rce.slave.interface.Types for more
                                information.
            @type  iType:       int

            @param clsName:     Message type/Service type consisting of the
                                package and the name of the message/service,
                                i.e. 'std_msgs/Int32'.
            @type  clsName:     str
        """
        super(Interface, self).__init__(interface)

        self.iType = iType
        self.clsName = clsName

    @property
    def obj(self):
        """ Reference to the wrapped Interface instance. """
        return self._obj

########NEW FILE########
__FILENAME__ = environment
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/environment.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import fcntl

# ROS specific imports
import rospy

# twisted specific imports
from twisted.python import log
from twisted.spread.pb import PBClientFactory

# rce specific imports
from rce.util.error import InternalError
from rce.util.loader import Loader
from rce.monitor.node import Node
from rce.monitor.parameter import Parameter
from rce.monitor.interface.environment import PublisherInterface, \
    SubscriberInterface, ServiceClientInterface, ServiceProviderInterface
from rce.slave.endpoint import Endpoint
from rce.slave.namespace import Namespace
from rce.slave.interface import Types


class Environment(Namespace):
    """ Representation of the namespace in the environment process, which is
        part of the cloud engine internal communication.
    """
    def __init__(self, endpoint):
        """ Initialize the Environment.

            @param endpoint:    Environment Client which is responsible for
                                monitoring the environment in this process.
            @type  endpoint:    rce.robot.EnvironmentClient
        """
        Namespace.__init__(self, endpoint)

        interface_map = {
            Types.encode('PublisherInterface') : PublisherInterface,
            Types.encode('SubscriberInterface') : SubscriberInterface,
            Types.encode('ServiceClientInterface') : ServiceClientInterface,
            Types.encode('ServiceProviderInterface') : ServiceProviderInterface
        }
        self._map.update(interface_map)

        self._nodes = set()
        self._parameters = set()

    def registerNode(self, node):
        assert node not in self._nodes
        self._nodes.add(node)

    def unregisterNode(self, node):
        assert node in self._nodes
        self._nodes.remove(node)
        self._endpoint.referenceDied('nodeDied', node)

    def registerParameter(self, parameter):
        assert parameter not in self._parameters
        self._parameters.add(parameter)

    def unregisterParameter(self, parameter):
        assert parameter in self._parameters
        self._parameters.remove(parameter)
        self._endpoint.referenceDied('parameterDied', parameter)

    def remote_createNode(self, pkg, exe, args, name, namespace):
        """ Create a Node object in the environment namespace and
            therefore in the endpoint.

            @param pkg:         Name of ROS package where the node can be
                                found.
            @type  pkg:         str

            @param exe:         Name of executable (node) which should be
                                launched.
            @type  exe:         str

            @param args:        Additional arguments which should be used for
                                the launch.
            @type  args:        str

            @param name:        Name of the node under which the node should be
                                launched.
            @type  name:        str

            @param namespace:   Namespace in which the node should be started
                                in the environment.
            @type  namespace:   str
        """
        return Node(self, pkg, exe, args, name, namespace)

    def remote_createParameter(self, name, value):
        """ Create a Parameter object in the environment namespace and
            therefore in the endpoint.

            @param name:        Name of the parameter which should be added.
            @type  name:        str

            @param value:       Value of the parameter which should be added.
            @type  value:       str, int, float, bool, list
        """
        return Parameter(self, name, value)

    def remote_destroy(self):
        """ Method should be called to destroy the environment and will take
            care of destroying all objects owned by this Environment as well
            as deleting all circular references.
        """
        for node in self._nodes.copy():
            node.remote_destroy()

        for parameter in self._parameters.copy():
            parameter.remote_destroy()

        # Can not check here, because nodes are unregistered when the
        # node (process) exits and remote_destroy only requests to stop the
        # node (process)
        #assert len(self._nodes) == 0
        assert len(self._parameters) == 0

        Namespace.remote_destroy(self)


class EnvironmentClient(Endpoint):
    """ Environment client is responsible for the cloud engine components
        inside a container.
    """
    def __init__(self, reactor, commPort):
        """ Initialize the Environment Client.

            @param reactor:     Reference to the twisted reactor used in this
                                robot process.
            @type  reactor:     twisted::reactor

            @param commPort:    Port where the server for the cloud engine
                                internal communication will listen for incoming
                                connections.
            @type  commPort:    int
        """
        Endpoint.__init__(self, reactor, Loader(), commPort)

        self._dbFile = '/opt/rce/data/rosenvbridge.db' # TODO: Hardcoded?

    def createEnvironment(self, _):
        """ Create the Environment namespace.
        """
        if self._namespaces:
            raise InternalError('The environment can have only one namespace '
                                'at a time.')

        environment = Environment(self)
        return self._avatar.callRemote('setupNamespace', environment)

    def remote_addUsertoROSProxy(self, userID, key):
        """ Method to add username and key to rosproxy-environment bridge
            file that maintains list of users that can call functions of
            rosproxy.

            @param userID:      Username
            @type  userID:      str

            @param key:         Secret key
            @type  key:         str
        """
        # TODO: Should this be deferred to a separate thread due to flock,
        #       which is a blocking call?
        with open(self._dbFile, "a") as bridgefile:
            fcntl.flock(bridgefile.fileno(), fcntl.LOCK_EX)
            bridgefile.write('{0}:{1}\n'.format(userID, key))


def main(reactor, cred, masterIP, masterPort, commPort, uid):
    f = open('/opt/rce/data/env.log', 'w') # TODO: Use os.getenv('HOME') ?
    log.startLogging(f)

    rospy.init_node('RCE_Master')
    print 'connect to ', masterIP, masterPort

    factory = PBClientFactory()
    reactor.connectTCP(masterIP, masterPort, factory)

    client = EnvironmentClient(reactor, commPort)

    def terminate():
        reactor.callFromThread(client.terminate)
        reactor.callFromThread(reactor.stop)

    rospy.on_shutdown(terminate)

    def _err(reason):
        print(reason)
        terminate()

    d = factory.login(cred, (client, uid))
    d.addCallback(client.registerAvatar)
    d.addCallback(client.createEnvironment)
    d.addErrback(_err)

    reactor.run(installSignalHandlers=False)

    f.close()

########NEW FILE########
__FILENAME__ = master
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/master.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import sys
from uuid import uuid4

# zope specific imports
from zope.interface import implements

# twisted specific imports
from twisted.python import log
from twisted.cred.portal import IRealm, Portal
from twisted.spread.pb import IPerspective, PBServerFactory
from twisted.web.server import Site

# rce specific imports
from rce.util.error import InternalError
from rce.util.cred import CredentialError
from rce.comm.interfaces import IMasterRealm
from rce.comm.server import RobotResource
from rce.core.machine import LoadBalancer, ContainerProcessError, \
    Distributor, RobotProcessError, MachineAvatar
from rce.core.network import Network
from rce.core.environment import EnvironmentEndpoint, EnvironmentEndpointAvatar
from rce.core.robot import RobotEndpoint, RobotEndpointAvatar
from rce.core.user import User


class UserRealm(object):
    """
    """
    implements(IRealm)

    def __init__(self, rce):
        self._rce = rce

    def requestAvatar(self, avatarId, mind, *interfaces):
        if IPerspective not in interfaces:
            raise NotImplementedError('RoboEarthCloudEngine only '
                                      'handles IPerspective.')

        return IPerspective, self._rce.getUser(avatarId), lambda: None


class RoboEarthCloudEngine(object):
    """ Realm for the twisted cred system. It is responsible for storing all
        cloud engine relevant informations by having a reference to a Network,
        Load Balancer, and Distributor instance, where each is responsible for
        part of the system. Additionally, the realm keeps a list of all User
        object.

        There should be only one instance running in the Master process.
    """
    implements(IRealm, IMasterRealm)

    def __init__(self, checker, port):
        """ Initialize the RoboEarth Cloud Engine realm.

            @param checker:     Login checker which authenticates the User when
                                an initial request is received.
            @type  checker:     twisted.cred.checkers.ICredentialsChecker

            @param port:        Port where the robot process is listening for
                                connections from other endpoints.
            @type  port:        int
        """
        self._checker = checker
        self._port = port

        self._network = Network()
        self._balancer = LoadBalancer()
        self._distributor = Distributor()

        self._users = {}
        self._pendingContainer = {}

    def requestAvatar(self, avatarId, mind, *interfaces):
        """ Returns Avatar for slave processes of the cloud engine.

            Implementation for IRealm
        """
        if IPerspective not in interfaces:
            raise NotImplementedError('RoboEarthCloudEngine only '
                                      'handles IPerspective.')

        # There are three possible roles (=avatarId):
        #     'container', 'robot', and 'environment'
        if avatarId == 'container':
            machine = self._balancer.createMachine(mind[0], mind[1])
            avatar = MachineAvatar(machine, self._balancer)
            detach = lambda: avatar.logout()
            print('Connection to Container process established.')
        elif avatarId == 'robot':
            endpoint = RobotEndpoint(self._network, self._distributor,
                                     self._port)
            endpoint.callback(mind)
            avatar = RobotEndpointAvatar(self, endpoint)
            detach = lambda: avatar.logout()
            print('Connection to Robot process established.')
        elif avatarId == 'environment':
            endpoint = self._pendingContainer.pop(mind[1])
            endpoint.callback(mind[0])
            avatar = EnvironmentEndpointAvatar(self, endpoint)
            detach = lambda: avatar.logout()
            print('Connection to Environment process established.')
        else:
            raise InternalError('Invalid avatar ID received.')

        return IPerspective, avatar, detach

    def getUser(self, userID):
        """ Get the user object matching the given user ID.

            @param userID:      user ID of the user which should be retrieved.
            @type  userID:      str

            @return:            User object matching the user ID.
            @rtype:             rce.core.user.User
        """
        if userID not in self._users:
            self._users[userID] = User(self, userID)

        return self._users[userID]

    def requestURL(self, userID):
        """ Callback for Robot resource to retrieve the location of the Robot
            process to which a WebSocket connection should be established.

            @param userID:      User ID under which the robot will login.
                                (Can be used to do optimizations in distributing
                                the load.)
            @type  userID:      str

            @return:            The IP address of Robot process to which a
                                WebSocket connection should be established.
                                (type: str)
            @rtype:             twisted.internet.defer.Deferred
        """
        try:
            location = self._distributor.getNextLocation()
        except RobotProcessError:
            # TODO: What should we do here?
            raise InternalError('Robot can not be created.')

        return location.getWebsocketAddress()

    def createContainer(self, userID, data):
        """ Callback for User instance to create a new Container object in a
            container process.

            @param userID:      UserID of the user who created the container.
            @type  userID:      str

            @param data:        Extra data which is used to configure the
                                container.
            @param data:        dict

            @return:            New Namespace and Container instance.
            @rtype:             (rce.core.environment.Environment,
                                 rce.core.container.Container)
                                 (subclasses of rce.core.base.Proxy)
        """
        while 1:
            uid = uuid4().hex

            if uid not in self._pendingContainer:
                break

        try:
            container = self._balancer.createContainer(uid, userID, data)
        except ContainerProcessError:
            # TODO: What should we do here?
            raise InternalError('Container can not be created.')

        endpoint = EnvironmentEndpoint(self._network, container)
        self._pendingContainer[uid] = endpoint
        return endpoint.createNamespace(), container

    def checkUIDValidity(self, uid):
        """Method to check if incoming environment ID is valid.

            @param uid:         UID to be tested.
            @type  uid:         str
        """
        if uid not in self._pendingContainer:
            raise CredentialError('Invalid environment ID.')

    def createConnection(self, interfaceA, interfaceB):
        """ Callback for User instance to create a new connection between two
            interfaces.

            @param interfaceX:  Interface which should be connected.
            @type  interfaceX:  rce.master.network.Interface

            @return:            New Connection instance.
            @rtype:             rce.core.network.Connection
        """
        return self._network.createConnection(interfaceA, interfaceB)

    def preShutdown(self):
        """ Method is executed by the twisted reactor when a shutdown event
            is triggered, before the reactor is being stopped.
        """
        for user in self._users.values():
            user.destroy()

    def postShutdown(self):
        """ Method is executed by the twisted reactor when a shutdown event
            is triggered, after the reactor has been stopped.
        """
        self._network.cleanUp()
        self._balancer.cleanUp()
        self._distributor.cleanUp()


def main(reactor, internalCred, externalCred, internalPort, externalPort,
         commPort, consolePort):
    log.startLogging(sys.stdout)

    # Realms
    rce = RoboEarthCloudEngine(externalCred, commPort)
    user = UserRealm(rce)

    internalCred.add_checker(rce.checkUIDValidity)

    # Portals
    rcePortal = Portal(rce, (internalCred,))
    consolePortal = Portal(user, (externalCred,))

    # Internal Communication
    reactor.listenTCP(internalPort, PBServerFactory(rcePortal))

    # Client Connections
    reactor.listenTCP(consolePort, PBServerFactory(consolePortal))
    reactor.listenTCP(externalPort, Site(RobotResource(rce)))

    reactor.addSystemEventTrigger('before', 'shutdown', rce.preShutdown)
    reactor.addSystemEventTrigger('after', 'shutdown', rce.postShutdown)

    reactor.run()

########NEW FILE########
__FILENAME__ = common
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/monitor/common.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import os
import re


class EnvironmentVariableNotFound(Exception):
    """ Exception is raised in case the requested environment variable was not
        found.
    """


class ArgumentMixin(object):
    """ Class which can be used as a mixin to add similar capabilities to
        dynamically modify arguments as for a ROS launch file.
    """
    _RE_FIND = re.compile('\\$\\( *find +(?P<pkg>[a-zA-Z][a-zA-z0-9_]*) *\\)')
    _RE_ENV = re.compile('\\$\\( *env +(?P<var>[a-zA-Z][a-zA-z0-9_]*) *\\)')

    def __init__(self, loader, *args, **kw):
        """ Initialize the argument mixin. It needs the manager instance as
            fist argument.

            @param loader:      Loader which can be used to import ROS
                                resources.
            @type  loader:      rce.util.loader.Loader
        """
        self._loader = loader

    def _replaceFind(self, match):
        """ Internally used method to replace found matches of _RE_FIND regular
            expression with corresponding package path.
        """
        path = self._loader.findPkgPath(match.group('pkg'))
        return '"{0}"'.format(path) if ' ' in path else path

    def _replaceEnv(self, match):
        """ Internally used method to replace found matches of _RE_ENV regular
            expression with corresponding environment variable.
        """
        var = match.group('var')

        try:
            return os.environ[var]
        except KeyError:
            raise EnvironmentVariableNotFound('Can not find environment '
                                              'variable: {0}'.format(var))

    def processArgument(self, value):
        """ Run the replacement methods over the argument if it is a string.

            @param value:       Value which should be modified if necessary.

            @return:            Value which should be used instead of the given
                                value.
        """
        if not isinstance(value, basestring):
            return value

        value = self._RE_FIND.subn(self._replaceFind, value)[0]
        value = self._RE_ENV.subn(self._replaceEnv, value)[0]

        return value

########NEW FILE########
__FILENAME__ = environment
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/monitor/interface/environment.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
from threading import Event, Lock
from uuid import uuid4

# ROS specific imports
from genmsg.names import package_resource_name
from genpy.message import Message
import rospy

# twisted specific imports
from twisted.internet.threads import deferToThreadPool

# rce specific imports
from rce.util.error import InternalError
from rce.util.ros import decorator_has_connection
from rce.slave.interface import Interface, InvalidResoureName


# Patch the method 'rospy.topics._TopicImpl.has_connection'
rospy.topics._TopicImpl.has_connection = \
    decorator_has_connection(rospy.topics._TopicImpl.has_connection)


class _ROSInterfaceBase(Interface):
    """ Abstract base class which provides the basics for the ROS-side
        interfaces.
    """
    def __init__(self, owner, uid, clsName, addr):
        """ Initialize the ROS-side Interface.

            @param owner:       Namespace to which this interface belongs.
            @type  owner:       rce.environment.Environment

            @param uid:         Unique ID which is used to identify the
                                interface in the internal communication.
            @type  uid:         uuid.UUID

            @param clsName:     Message type/Service type consisting of the
                                package and the name of the message/service,
                                i.e. 'std_msgs/Int32'.
            @type  clsName:     str

            @param addr:        ROS name/address which the interface should
                                use.
            @type  addr:        str

            @raise:             rce.util.loader.ResourceNotFound
        """
        Interface.__init__(self, owner, uid, addr)

        self._reactor = owner.reactor


class ServiceClientInterface(_ROSInterfaceBase):
    """ Class which is used as a Service-Client Interface.
    """
    def __init__(self, owner, uid, clsName, addr):
        _ROSInterfaceBase.__init__(self, owner, uid, clsName, ('SC', addr))

        try:
            pkg, name = package_resource_name(clsName)
        except ValueError:
            raise InvalidResoureName('Service type is not valid. Has to be of '
                                     'the form pkg/srv, i.e. std_srvs/Empty.')

        self._srvCls = owner.loader.loadSrv(pkg, name)
        self._srvCls._request_class = rospy.AnyMsg
        self._srvCls._response_class = rospy.AnyMsg

    __init__.__doc__ = _ROSInterfaceBase.__init__.__doc__

    def _send(self, msg, msgID, protocol, remoteID):
        d = deferToThreadPool(self._reactor, self._reactor.getThreadPool(),
                              self._threadedCall, msg)
        d.addCallback(self._respond, msgID, protocol, remoteID)
        d.addErrback(self._errHandler)

    def _threadedCall(self, msg):
        rosMsg = rospy.AnyMsg()
        rosMsg._buff = msg

        rospy.wait_for_service(self._addr[1], timeout=5)
        serviceFunc = rospy.ServiceProxy(self._addr[1], self._srvCls)
        return serviceFunc(rosMsg)

    def _respond(self, resp, msgID, protocol, remoteID):
        self.respond(resp._buff, msgID, protocol, remoteID)

    def _errHandler(self, e):
        if e.check(rospy.ROSInterruptException):
            pass  # TODO: How should the error be returned?
        elif e.check(rospy.ROSSerializationException):
            pass  # TODO: How should the error be returned?
        else:
            e.printTraceback()


class ServiceProviderInterface(_ROSInterfaceBase):
    """ Class which is used as a Service-Provider Interface.
    """
    def __init__(self, owner, uid, clsName, addr):
        _ROSInterfaceBase.__init__(self, owner, uid, clsName, ('SP', addr))

        try:
            pkg, name = package_resource_name(clsName)
        except ValueError:
            raise InvalidResoureName('Service type is not valid. Has to be of '
                                     'the form pkg/srv, i.e. std_srvs/Empty.')

        self._service = None
        self._pendingLock = Lock()
        self._pending = {}

        self._srvCls = owner.loader.loadSrv(pkg, name)
        self._srvCls._request_class = rospy.AnyMsg
        self._srvCls._response_class = rospy.AnyMsg

    __init__.__doc__ = _ROSInterfaceBase.__init__.__doc__

    def remote_connect(self, protocol, remoteID):
        if self._protocols:
            raise InternalError('Can not register more than one interface '
                                'at a time with a Service-Provider.')

        return _ROSInterfaceBase.remote_connect(self, protocol, remoteID)

    remote_connect.__doc__ = _ROSInterfaceBase.remote_connect.__doc__

    def _start(self):
        self._service = rospy.Service(self._addr[1], self._srvCls, self._callback)

    def _stop(self):
        self._service.shutdown()
        self._service = None

        with self._pendingLock:
            for event in self._pending.itervalues():
                event.set()

            self._pending = {}

    def _send(self, msg, msgID, protocol, remoteID):
        rosMsg = rospy.AnyMsg()
        rosMsg._buff = msg

        try:
            with self._pendingLock:
                event = self._pending[msgID]
                self._pending[msgID] = rosMsg
        except KeyError:
            return

        event.set()

    def _callback(self, request):
        """ This method is called by the ROS framework when a Service request
            has arrived.
            Each call runs in a separate thread and has to block until a
            response is present, because the return value of this method is
            used as response to the request.
        """
        msgID = uuid4().hex
        event = Event()

        with self._pendingLock:
            self._pending[msgID] = event

        self._reactor.callFromThread(self.received, request._buff, msgID)

        # Block execution here until the event is set, i.e. a response has
        # arrived
        event.wait()

        with self._pendingLock:
            response = self._pending.pop(msgID, None)

        if not isinstance(response, Message):
            # TODO: Change exception?
            raise rospy.ROSInterruptException('Interrupted.')

        return response


class PublisherInterface(_ROSInterfaceBase):
    """ Class which is used as a Publisher Interface.
    """
    def __init__(self, owner, uid, clsName, addr):
        _ROSInterfaceBase.__init__(self, owner, uid, clsName, ('TP', addr))

        try:
            pkg, name = package_resource_name(clsName)
        except ValueError:
            raise InvalidResoureName('Message type is not valid. Has to be of '
                                     'the form pkg/msg, i.e. std_msgs/Int8.')

        self._msgCls = owner.loader.loadMsg(pkg, name)

    __init__.__doc__ = _ROSInterfaceBase.__init__.__doc__

    def _start(self):
        # TODO: Is 'latch=True' really necessary?
        #       Should this be configurable?
        self._publisher = rospy.Publisher(self._addr[1], self._msgCls,
                                          latch=True)

    def _stop(self):
        self._publisher.unregister()
        self._publisher = None

    def _send(self, msg, msgID, protocol, remoteID):
        rosMsg = rospy.AnyMsg()
        rosMsg._buff = msg

        try:
            self._publisher.publish(rosMsg)
        except rospy.ROSInterruptException:
            pass  # TODO: How should the error be returned?
        except rospy.ROSSerializationException:
            pass  # TODO: How should the error be returned?


class SubscriberInterface(_ROSInterfaceBase):
    """ Class which is used as a Subscriber Interface.
    """
    def __init__(self, owner, uid, clsName, addr):
        _ROSInterfaceBase.__init__(self, owner, uid, clsName, ('TS', addr))

    def _start(self):
        self._subscriber = rospy.Subscriber(self._addr[1], rospy.AnyMsg,
                                            self._callback)

    def _stop(self):
        self._subscriber.unregister()
        self._subscriber = None

    def _callback(self, msg):
        self._reactor.callFromThread(self.received, msg._buff, uuid4().hex)

########NEW FILE########
__FILENAME__ = robot
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/monitor/interface/robot.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import zlib
from uuid import uuid4

try:
    from cStringIO import StringIO, InputType, OutputType
    from StringIO import StringIO as pyStringIO

    def _checkIsStringIO(obj):
        return isinstance(obj, (InputType, OutputType, pyStringIO))
except ImportError:
    from StringIO import StringIO

    def _checkIsStringIO(obj):
        return isinstance(obj, StringIO)

# rce specific imports
from rce.util.error import InternalError
from rce.slave.interface import Interface, InvalidResoureName
from rce.util.settings import getSettings
settings = getSettings()


class ConversionError(Exception):
    """ Exception is raised in case a ROS message could not be converted.
    """


class ServiceError(Exception):
    """ Exception is raised in case a response message was received, but not
        corresponding request is available.
    """


class _AbstractRobotInterface(Interface, object):
    # Important to inherit from object here to properly use the Mixins!
    """ Abstract base class which provides the basics for the robot-side
        interfaces.
    """
    def __init__(self, owner, uid, clsName, tag):
        """ Initialize the robot-side Interface.

            @param owner:       Namespace to which this interface belongs.
            @type  owner:       rce.robot.Robot

            @param uid:         Unique ID which is used to identify the
                                interface in the internal communication.
            @type  uid:         uuid.UUID

            @param clsName:     Message type/Service type consisting of the
                                package and the name of the message/service,
                                i.e. 'std_msgs/Int32'.
            @type  clsName:     str

            @param tag:         Unique ID which is used to identify the
                                interface in the external communication.
            @type  tag:         str
        """
        Interface.__init__(self, owner, uid, tag)

        self._clsName = clsName

    def _start(self):
        self._owner.sendToClientInterfaceStatusUpdate(self._addr, True)

    def _stop(self):
        self._owner.sendToClientInterfaceStatusUpdate(self._addr, False)


class _ConverterBase(_AbstractRobotInterface):
    """ Class which implements the basic functionality of a Converter.

        For the actual communication with the robot-side a Mixin has to be used.
    """
    def __init__(self, owner, uid, clsName, tag):
        _AbstractRobotInterface.__init__(self, owner, uid, clsName, tag)

        self._converter = owner.converter

        self._inputMsgCls = None
        self._outputMsgCls = None

        self._loadClass(owner.loader)

    __init__.__doc__ = _AbstractRobotInterface.__init__.__doc__

    def _loadClass(self, loader):
        """ This method is used as a hook to load the necessary ROS class
            for the interface. And is called as last step in the constructor.

            This method has to be overwritten!

            References to the loaded classes have to be stored in the instance
            attributes '_inputMsgCls' and '_outputMsgCls'.
            If there is no reference stored, i.e. None, it is assumed that
            the converter can not convert the messages in the given direction
            and an error is raised.
        """
        raise NotImplementedError("The method 'loadClass' has to "
                                  'be implemented.')

    def receive(self, clsName, msgID, msg):
        """ Convert a JSON encoded message into a ROS message.

            @param clsName:     Message/Service type of the received message.
            @type  clsName:     str

            @param msgID:       Identifier which is used to match request /
                                response message.
            @type  msgID:       str

            @param msg:         JSON compatible message which should be
                                processed.
            @type  msg:         dict
        """
        if not self._inputMsgCls:
            raise InternalError('This converter can not handle incoming'
                                ' messages.')

        if clsName != self._clsName:
            raise InvalidResoureName('Sent message type does not match the '
                                     'used message type for this interface.')

        try:
            msg = self._converter.decode(self._inputMsgCls, msg)
        except (TypeError, ValueError) as e:
            raise ConversionError(str(e))

        buf = StringIO()
        msg.serialize(buf)
        msg = buf.getvalue()

        self._receive(msg, msgID)

    def _send(self, msg, msgID, protocol, remoteID):
        """ Convert a ROS message into a JSON encoded message.

            @param msg:         Received ROS message in serialized form.
            @type  msg:         str

            @param msgID:       Unique ID to identify the message.
            @type  msgID:       str

            @param protocol:    Protocol instance through which the message
                                was sent.
            @type  protocol:    rce.slave.protocol._Protocol

            @param remoteID:    Unique ID of the Interface which sent the
                                message.
            @type  remoteID:    uuid.UUID
        """
        if not self._outputMsgCls:
            raise InternalError('This converter can not handle outgoing '
                                'messages.')

        rosMsg = self._outputMsgCls()
        rosMsg.deserialize(msg)

        try:
            jsonMsg = self._converter.encode(rosMsg)
        except (TypeError, ValueError) as e:
            raise ConversionError(str(e))

        self._sendToClient(jsonMsg, msgID, protocol, remoteID)


class _ForwarderBase(_AbstractRobotInterface):
    """ Class which implements the basic functionality of a Forwarder.

        For the actual communication with the robot-side a Mixin has to be used.
    """
    _GZIP_LVL = settings.gzip_lvl

    def receive(self, clsName, msgID, msg):
        """ Unwrap and inflate a JSON encoded ROS message.

            @param clsName:     Message/Service type of the received message.
            @type  clsName:     str

            @param msgID:       Identifier which is used to match request /
                                response message.
            @type  msgID:       str

            @param msg:         JSON compatible message which should be
                                processed.
            @type  msg:         dict
        """
        if clsName != self._clsName:
            raise InvalidResoureName('Sent message type does not match the '
                                     'used message type for this interface.')

        if not _checkIsStringIO(msg):
            raise ConversionError('Sent message is not a binary message.')

        if self._GZIP_LVL:
            self._receive(zlib.decompress(msg.getvalue()), msgID)
        else:
            self._receive(msg.getvalue(), msgID)

    def _send(self, msg, msgID, protocol, remoteID):
        """ Wrap and deflate a ROS message in a JSON encoded message.

            @param msg:         Received ROS message in serialized form.
            @type  msg:         str

            @param msgID:       Unique ID to identify the message.
            @type  msgID:       str

            @param protocol:    Protocol instance through which the message
                                was sent.
            @type  protocol:    rce.slave.protocol._Protocol

            @param remoteID:    Unique ID of the Interface which sent the
                                message.
            @type  remoteID:    uuid.UUID
        """
        if self._GZIP_LVL:
            self._sendToClient(StringIO(zlib.compress(msg, self._GZIP_LVL)),
                               msgID, protocol, remoteID)
        else:
            self._sendToClient(StringIO(msg), msgID, protocol, remoteID)


class _ServiceClient(object):
    """ Mixin which provides the implementation for the communication with the
        robot-side for a Service-Client.
    """
    def __init__(self, *args, **kw):
        super(_ServiceClient, self).__init__(*args, **kw)

        self._pendingRequests = {}

    __init__.__doc__ = _AbstractRobotInterface.__init__.__doc__

    def _receive(self, msg, uid):
        try:
            msgID, protocol, remoteID = self._pendingRequests.pop(uid)
        except KeyError:
            raise ServiceError('Service Client does not wait for a response '
                               'with message ID {0}.'.format(msgID))

        self.respond(msg, msgID, protocol, remoteID)

    def _sendToClient(self, msg, msgID, protocol, remoteID):
        while 1:
            uid = uuid4().hex

            if uid not in self._pendingRequests:
                break

        self._pendingRequests[uid] = (msgID, protocol, remoteID)
        self._owner.sendToClient(self._addr, self._clsName, uid, msg)


class _ServiceProvider(object):
    """ Mixin which provides the implementation for the communication with the
        robot-side for a Service-Provider.
    """
    def remote_connect(self, protocol, remoteID):
        if self._protocols:
            raise InternalError('Can not register more than one interface '
                                'at a time with a Service-Provider.')

        return super(_ServiceProvider, self).remote_connect(protocol, remoteID)

    remote_connect.__doc__ = _AbstractRobotInterface.remote_connect.__doc__

    def _receive(self, msg, msgID):
        self.received(msg, msgID)

    def _sendToClient(self, msg, msgID, protocol, remoteID):
        self._owner.sendToClient(self._addr, self._clsName, msgID, msg)


class _Publisher(object):
    """ Mixin which provides the implementation for the communication with the
        robot-side for a Publisher.
    """
    def _receive(self, msg, msgID):
        self.received(msg, msgID)

    def _sendToClient(self, msg, msgID, protocol, remoteID):
        self._owner.sendToClient(self._addr, self._clsName, msgID, msg)


class _Subscriber(object):
    """ Mixin which provides the implementation for the communication with the
        robot-side for a Subscriber.
    """
    def _receive(self, msg, msgID):
        self.received(msg, msgID)

    def _sendToClient(self, msg, msgID, protocol, remoteID):
        self._owner.sendToClient(self._addr, self._clsName, msgID, msg)


class ServiceClientConverter(_ServiceClient, _ConverterBase):
    """ Class which is used as a Service-Client Converter.
    """
    def _loadClass(self, loader):
        args = self._clsName.split('/')

        if len(args) != 2:
            raise InvalidResoureName('srv type is not valid. Has to be of the '
                                     'from pkg/msg, i.e. std_msgs/Int8.')

        srvCls = loader.loadSrv(*args)
        self._inputMsgCls = srvCls._response_class
        self._outputMsgCls = srvCls._request_class


class ServiceProviderConverter(_ServiceProvider, _ConverterBase):
    """ Class which is used as a Service-Provider Converter.
    """
    def _loadClass(self, loader):
        args = self._clsName.split('/')

        if len(args) != 2:
            raise InvalidResoureName('srv type is not valid. Has to be of the '
                                     'from pkg/msg, i.e. std_msgs/Int8.')

        srvCls = loader.loadSrv(*args)
        self._inputMsgCls = srvCls._request_class
        self._outputMsgCls = srvCls._response_class


class PublisherConverter(_Publisher, _ConverterBase):
    """ Class which is used as a Publisher Converter.
    """
    def _loadClass(self, loader):
        args = self._clsName.split('/')

        if len(args) != 2:
            raise InvalidResoureName('msg type is not valid. Has to be of the '
                                     'from pkg/msg, i.e. std_msgs/Int8.')

        self._outputMsgCls = loader.loadMsg(*args)


class SubscriberConverter(_Subscriber, _ConverterBase):
    """ Class which is used as a Subscriber Converter.
    """
    def _loadClass(self, loader):
        args = self._clsName.split('/')

        if len(args) != 2:
            raise InvalidResoureName('msg type is not valid. Has to be of the '
                                     'from pkg/msg, i.e. std_msgs/Int8.')

        self._inputMsgCls = loader.loadMsg(*args)


class ServiceClientForwarder(_ServiceClient, _ForwarderBase):
    """ Class which is used as a Service-Client Forwarder.
    """


class ServiceProviderForwarder(_ServiceProvider, _ForwarderBase):
    """ Class which is used as a Service-Provider Forwarder.
    """


class PublisherForwarder(_Publisher, _ForwarderBase):
    """ Class which is used as a Publisher Forwarder.
    """


class SubscriberForwarder(_Subscriber, _ForwarderBase):
    """ Class which is used as a Subscriber Forwarder.
    """

########NEW FILE########
__FILENAME__ = node
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/monitor/node.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import os
import shlex
from uuid import uuid4

# twisted specific imports
from twisted.python import log
from twisted.internet.error import ProcessExitedAlready
from twisted.internet.protocol import ProcessProtocol
from twisted.spread.pb import Referenceable

# rce specific imports
from rce.monitor.common import ArgumentMixin


class NodeProtocol(ProcessProtocol):
    """ Node process protocol.

        It is used to monitor the health of a node and logging the stdout and
        stderr to files.
    """
    def __init__(self, monitor, out, err):
        self._monitor = monitor

        self._out = open(out, 'w')
        self._err = open(err, 'w')

        # Overwrite method from base class
        self.outReceived = self._out.write
        self.errReceived = self._err.write

    def connectionMade(self):
        self._monitor.started()

    def processEnded(self, reason):
        self._monitor.stopped(reason.value.exitCode)
        self._monitor = None

    def __del__(self):
        self._out.close()
        self._err.close()


class Node(Referenceable, ArgumentMixin):
    """ Representation of a ROS Node (process) inside an environment.
    """
    # CONFIG
    _STOP_ESCALATION = [('INT', 15), ('TERM', 2), ('KILL', None)]
    _LOG_DIR = '/opt/rce/data'  # TODO: After splitting process: '/home/ros'

    def __init__(self, owner, pkg, exe, args, name, namespace):
        """ Initialize and start the Node.

            @param owner:       Environment in which the node will be created.
            @type  owner:       rce.environment.Environment

            @param pkg:         Name of ROS package where the node can be
                                found.
            @type  pkg:         str

            @param exe:         Name of executable (node) which should be
                                launched.
            @type  exe:         str

            @param args:        Additional arguments which should be used for
                                the launch. Can contain the directives
                                $(find PKG) and/or $(env VAR). Other special
                                characters such as '$' or ';' are not allowed.
            @type  args:        str

            @param name:        Name of the node under which the node should be
                                launched.
            @type  name:        str

            @param namespace:   Namespace in which the node should be started
                                in the environment.
            @type  namespace:   str

            @raise:             rce.util.loader.ResourceNotFound
        """
        ArgumentMixin.__init__(self, owner.loader)

        owner.registerNode(self)
        self._owner = owner

        self._reactor = owner.reactor
        self._call = None
        self._protocol = None

        # Find and validate executable
        cmd = [self._loader.findNode(pkg, exe)]  # raises ResourceNotFound

        # Add arguments
        args = self.processArgument(args)

        # TODO: Is it necessary to limit the possible characters here?
#        for char in '$;':
#            if char in args:
#                raise ValueError('Argument can not contain special '
#                                 "character '{0}'.".format(char))

        cmd += shlex.split(args)

        # Process name and namespace argument
        if name:
            cmd.append('__name:={0}'.format(name))

        if namespace:
            cmd.append('__ns:={0}'.format(namespace))

        # Create protocol instance
        uid = uuid4().hex
        out = os.path.join(self._LOG_DIR,
                           '{0}-{1}-out.log'.format(uid, name or exe))
        err = os.path.join(self._LOG_DIR,
                           '{0}-{1}-err.log'.format(uid, name or exe))

        self._protocol = NodeProtocol(self, out, err)

        # Start node
        log.msg('Start Node {0}/{1} [pkg: {2}, exe: '
                '{3}].'.format(namespace, name or exe, pkg, exe))
        self._reactor.spawnProcess(self._protocol, cmd[0], cmd, env=os.environ)

        self._name = '{0}/{1}'.format(pkg, exe)

    def started(self):
        """ Callback for NodeProtocol to signal that the process has started.
        """

    def stopped(self, exitCode):
        """ Callback for NodeProtocol to signal that the process has died.
        """
        self._protocol = None

        if self._call:
            self._call.cancel()

        if exitCode:
            log.msg('Node ({0}) terminated with exit code: '
                    '{1}'.format(self._name, exitCode))

        if self._owner:
            self._owner.unregisterNode(self)
            self._owner = None

    def remote_destroy(self):
        """ Method should be called to stop/kill this node.
        """
        self._destroy()

    def _destroy(self, lvl=0):
        if not self._protocol:
            return

        cmd, delay = self._STOP_ESCALATION[lvl]

        try:
            self._protocol.transport.signalProcess(cmd)
        except ProcessExitedAlready:
            return

        if delay is not None:
            self._call = self._reactor.callLater(delay, self._destroy, lvl + 1)
        else:
            self._call = None

########NEW FILE########
__FILENAME__ = parameter
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/monitor/parameter.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# ROS specific imports
import rospy

# twisted specific imports
from twisted.python import log
from twisted.spread.pb import Referenceable

# rce specific imports
from rce.util.error import InternalError
from rce.monitor.common import ArgumentMixin


class Parameter(Referenceable, ArgumentMixin):
    """ Representation of a Parameter inside an environment.
    """
    def __init__(self, owner, name, value):
        """ Add the Parameter to the parameter server.

            @param owner:       Environment in which the node will be created.
            @type  owner:       rce.environment.Environment

            @param name:        Name of the parameter which should be added.
            @type  name:        str

            @param value:       Value of the parameter which should be added.
                                Top-level string values can contain the
                                directives $(find PKG) and/or $(env VAR).
            @type  value:       str, int, float, bool, list
        """
        self._registered = False

        ArgumentMixin.__init__(self, owner.loader)

        owner.registerParameter(self)
        self._owner = owner

        if isinstance(value, basestring):
            value = self.processArgument(value)

        self._name = name

        try:
            if rospy.has_param(name):
                log.msg('Warning: Parameter already exists.')

            rospy.set_param(name, value)
            self._registered = True
        except rospy.ROSException as e:
            raise InternalError('ROS Parameter Server reported an error: '
                                '{0}'.format(e))

    def remote_destroy(self):
        """ Method should be called to delete the Parameter from the parameter
            server.
        """
        if self._registered:
            try:
                rospy.delete_param(self._name)
            except rospy.ROSException:
                pass

            self._registered = False

        if self._owner:
            self._owner.unregisterParameter(self)
            self._owner = None

########NEW FILE########
__FILENAME__ = robot
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/robot.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import sys

# ROS specific imports
from rospkg.environment import get_ros_paths

# zope specific imports
from zope.interface import implements

# twisted specific imports
from twisted.python import log
from twisted.cred.credentials import UsernamePassword
from twisted.spread.pb import PBClientFactory, \
    DeadReferenceError, PBConnectionLost

# Autobahn specific imports
from autobahn.websocket import listenWS

# rce specific imports
from rce.util.converter import Converter
from rce.util.loader import Loader
from rce.util.interface import verifyObject
from rce.comm.error import DeadConnection
from rce.comm.interfaces import IRobotRealm, IProtocol, \
    IRobot, IMessageReceiver
from rce.comm.server import CloudEngineWebSocketFactory
from rce.monitor.interface.robot import PublisherConverter, \
    SubscriberConverter, ServiceClientConverter, ServiceProviderConverter, \
    PublisherForwarder, SubscriberForwarder, \
    ServiceClientForwarder, ServiceProviderForwarder
from rce.slave.endpoint import Endpoint
from rce.slave.namespace import Namespace
from rce.slave.interface import Types


class ForwardingError(Exception):
    """ Exception is raised if the call could not be forwarded.
    """


class Connection(object):
    """ Representation of a connection to a robot client.
    """
    implements(IRobot, IMessageReceiver)

    def __init__(self, client, userID, robotID):
        """ Initialize the representation of a connection to a robot client.

            @param client:      Client which is responsible for managing the
                                Robot process.
            @type  client:      rce.robot.RobotClient

            @param userID:      User ID of the robot owner
            @type  userID:      str

            @param robotID:     Unique ID which is used to identify the robot.
            @type  robotID:     str
        """
        client.registerConnection(self)
        self._client = client
        self._userID = userID
        self._robotID = robotID
        self._avatar = None
        self._view = None
        self._namespace = None
        self._protocol = None

    @property
    def userID(self):
        """ User ID of the user owing this connection. """
        return self._userID

    @property
    def robotID(self):
        """ Robot ID used to identify the connected robot. """
        return self._robotID

    def destroy(self):
        """ # TODO: Add doc
        """
        if self._protocol:
            self._protocol.dropConnection()

        if self._client:
            self._client.unregisterConnection(self)

        if self._view:
            self._view.destroy()

        if self._namespace:
            self._namespace.destroy()

        self._client = None
        self._namespace = None
        self._view = None
        self._avatar = None
        self._protocol = None

    # Callbacks for RobotClient

    def registerAvatar(self, avatar):
        """ Register User Avatar.

            # TODO: Add description
        """
        assert self._avatar is None
        self._avatar = avatar

    def registerView(self, view):
        """ # TODO: Add doc
        """
        assert self._view is None
        self._view = view

    def registerNamespace(self, namespace):
        """ # TODO: Add doc
        """
        assert self._namespace is None
        self._namespace = namespace

    def registerProtocol(self, protocol):
        """ Register the client protocol.

            @param protocol:    Protocol which should be registered.
            @type  protocol:    rce.comm.interfaces.IServersideProtocol
        """
        assert self._protocol is None
        verifyObject(IProtocol, protocol)
        self._protocol = protocol

    def unregisterProtocol(self, protocol):
        """ Unregister the client protocol.

            @param protocol:    Protocol which should be unregistered.
            @type  protocol:    rce.comm.interfaces.IServersideProtocol
        """
        self._protocol = None

    # Callbacks for View & Namespace

    def reportError(self, msg):
        self._protocol.sendErrorMessage(msg)

    reportError.__doc__ = IProtocol.get('sendErrorMessage').getDoc()

    def sendMessage(self, iTag, clsName, msgID, msg):
        if not self._protocol:
            # TODO: What should we do here?
            #       One solution would be to queue the messages here for some
            #       time...
            return

        self._protocol.sendDataMessage(iTag, clsName, msgID, msg)

    sendMessage.__doc__ = IProtocol.get('sendDataMessage').getDoc()

    def sendInterfaceStatusUpdate(self, iTag, status):
        if not self._protocol:
            # TODO: What should we do here?
            #       One solution would be to queue the messages here for some
            #       time...
            return

        self._protocol.sendInterfaceStatusUpdateMessage(iTag, status)

    sendInterfaceStatusUpdate.__doc__ = \
        IProtocol.get('sendInterfaceStatusUpdateMessage').getDoc()

    # Forwarding to View

    def createContainer(self, tag, data={}):
        if not self._view:
            raise ForwardingError('Reference of the view is missing.')

        self._view.createContainer(tag, data)

    createContainer.__doc__ = IRobot.get('createContainer').getDoc()

    def destroyContainer(self, tag):
        if not self._view:
            raise ForwardingError('Reference of the view is missing.')

        self._view.destroyContainer(tag)

    destroyContainer.__doc__ = IRobot.get('destroyContainer').getDoc()

    def addNode(self, cTag, nTag, pkg, exe, args='', name='', namespace=''):
        if not self._view:
            raise ForwardingError('Reference of the view is missing.')

        self._view.addNode(cTag, nTag, pkg, exe, args, name, namespace)

    addNode.__doc__ = IRobot.get('addNode').getDoc()

    def removeNode(self, cTag, nTag):
        if not self._view:
            raise ForwardingError('Reference of the view is missing.')

        self._view.removeNode(cTag, nTag)

    removeNode.__doc__ = IRobot.get('removeNode').getDoc()

    def addInterface(self, eTag, iTag, iType, clsName, addr=''):
        if not self._view:
            raise ForwardingError('Reference of the view is missing.')

        self._view.addInterface(eTag, iTag, iType, clsName, addr)

    addInterface.__doc__ = IRobot.get('addInterface').getDoc()

    def removeInterface(self, eTag, iTag):
        if not self._view:
            raise ForwardingError('Reference of the view is missing.')

        self._view.removeInterface(eTag, iTag)

    removeInterface.__doc__ = IRobot.get('removeInterface').getDoc()

    def addParameter(self, cTag, name, value):
        if not self._view:
            raise ForwardingError('Reference of the view is missing.')

        self._view.addParameter(cTag, name, value)

    addParameter.__doc__ = IRobot.get('addParameter').getDoc()

    def removeParameter(self, cTag, name):
        if not self._view:
            raise ForwardingError('Reference of the view is missing.')

        self._view.removeParameter(cTag, name)

    removeParameter.__doc__ = IRobot.get('removeParameter').getDoc()

    def addConnection(self, tagA, tagB):
        if not self._view:
            raise ForwardingError('Reference of the view is missing.')

        self._view.addConnection(tagA, tagB)

    addConnection.__doc__ = IRobot.get('addConnection').getDoc()

    def removeConnection(self, tagA, tagB):
        if not self._view:
            raise ForwardingError('Reference of the view is missing.')

        self._view.removeConnection(tagA, tagB)

    removeConnection.__doc__ = IRobot.get('removeConnection').getDoc()

    # Forwarding to Namespace

    def processReceivedMessage(self, iTag, clsName, msgID, msg):
        if not self._namespace:
            raise ForwardingError('Reference of the namespace is missing.')

        self._namespace.receivedFromClient(iTag, clsName, msgID, msg)

    processReceivedMessage.__doc__ = \
        IMessageReceiver.get('processReceivedMessage').getDoc()


class RobotView(object):
    """ Wrapper for a RemoteReference of type RobotView.
    """
    implements(IRobot)

    def __init__(self, view, connection):
        """ Initialize the wrapper.

            @param view:        Remote reference referencing the RobotView
                                object in the Master process.
            @type  view:        twisted.spread.pb.RemoteReference

            @param connection:  Representation of the connection to a robot
                                client for which the wrapped RobotView was
                                retrieved from the Master process.
            @type  connection:  rce.robot.Connection
        """
        self._view = view
        self._connection = connection

    def _reportError(self, failure):
        """ Method is used internally as an errback to send an error message to
            the robot client.
        """
        self._connection.reportError(failure.getErrorMessage())

    def createContainer(self, tag, data={}):
        try:
            d = self._view.callRemote('createContainer', tag, data)
        except (DeadReferenceError, PBConnectionLost):
            raise DeadConnection

        d.addErrback(self._reportError)

    createContainer.__doc__ = IRobot.get('createContainer').getDoc()

    def destroyContainer(self, tag):
        try:
            d = self._view.callRemote('destroyContainer', tag)
        except (DeadReferenceError, PBConnectionLost):
            raise DeadConnection

        d.addErrback(self._reportError)

    destroyContainer.__doc__ = IRobot.get('destroyContainer').getDoc()

    def addNode(self, cTag, nTag, pkg, exe, args='', name='', namespace=''):
        try:
            d = self._view.callRemote('addNode', cTag, nTag, pkg, exe, args,
                                      name, namespace)
        except (DeadReferenceError, PBConnectionLost):
            raise DeadConnection

        d.addErrback(self._reportError)

    addNode.__doc__ = IRobot.get('addNode').getDoc()

    def removeNode(self, cTag, nTag):
        try:
            d = self._view.callRemote('removeNode', cTag, nTag)
        except (DeadReferenceError, PBConnectionLost):
            raise DeadConnection

        d.addErrback(self._reportError)

    removeNode.__doc__ = IRobot.get('removeNode').getDoc()

    def addInterface(self, eTag, iTag, iType, clsName, addr=''):
        try:
            d = self._view.callRemote('addInterface', eTag, iTag, iType,
                                      clsName, addr)
        except (DeadReferenceError, PBConnectionLost):
            raise DeadConnection

        d.addErrback(self._reportError)

    addInterface.__doc__ = IRobot.get('addInterface').getDoc()

    def removeInterface(self, eTag, iTag):
        try:
            d = self._view.callRemote('removeInterface', eTag, iTag)
        except (DeadReferenceError, PBConnectionLost):
            raise DeadConnection

        d.addErrback(self._reportError)

    removeInterface.__doc__ = IRobot.get('removeInterface').getDoc()

    def addParameter(self, cTag, name, value):
        try:
            d = self._view.callRemote('addParameter', cTag, name, value)
        except (DeadReferenceError, PBConnectionLost):
            raise DeadConnection

        d.addErrback(self._reportError)

    addParameter.__doc__ = IRobot.get('addParameter').getDoc()

    def removeParameter(self, cTag, name):
        try:
            d = self._view.callRemote('removeParameter', cTag, name)
        except (DeadReferenceError, PBConnectionLost):
            raise DeadConnection

        d.addErrback(self._reportError)

    removeParameter.__doc__ = IRobot.get('removeParameter').getDoc()

    def addConnection(self, tagA, tagB):
        try:
            d = self._view.callRemote('addConnection', tagA, tagB)
        except (DeadReferenceError, PBConnectionLost):
            raise DeadConnection

        d.addErrback(self._reportError)

    addConnection.__doc__ = IRobot.get('addConnection').getDoc()

    def removeConnection(self, tagA, tagB):
        try:
            d = self._view.callRemote('removeConnection', tagA, tagB)
        except (DeadReferenceError, PBConnectionLost):
            raise DeadConnection

        d.addErrback(self._reportError)

    removeConnection.__doc__ = IRobot.get('removeConnection').getDoc()

    def destroy(self):
        """ # TODO: Add doc
        """
        self._connection = None
        self._view = None


class Robot(Namespace):
    """ Representation of a namespace in the robot process, which is part of
        the cloud engine internal communication.
    """
    def __init__(self, endpoint, connection):
        """ Initialize the Robot.

            @param endpoint:    Robot Client which is responsible for
                                monitoring the robots in this process.
            @type  endpoint:    rce.robot.RobotClient

            @param connection:  The connection manager for robot namespaces.
            @type  connection:  rce.robot.Connection
        """
        Namespace.__init__(self, endpoint)

        interface_map = {
            Types.encode('PublisherConverter') : PublisherConverter,
            Types.encode('SubscriberConverter') : SubscriberConverter,
            Types.encode('ServiceClientConverter') : ServiceClientConverter,
            Types.encode('ServiceProviderConverter') : ServiceProviderConverter,
            Types.encode('PublisherForwarder') : PublisherForwarder,
            Types.encode('SubscriberForwarder') : SubscriberForwarder,
            Types.encode('ServiceClientForwarder') : ServiceClientForwarder,
            Types.encode('ServiceProviderForwarder') : ServiceProviderForwarder
        }
        self._map.update(interface_map)

        self._connection = connection

    @property
    def converter(self):
        """ Reference to the message converter used by the Converter
            interfaces.
        """
        return self._endpoint.converter

    def receivedFromClient(self, iTag, clsName, msgID, msg):
        """ Process a data message which has been received from the robot
            client and send the message to the appropriate interface.

            @param iTag:        Tag which is used to identify the interface to
                                which this message should be sent.
            @type  iTag:        str

            @param clsName:     Message type/Service type consisting of the
                                package and the name of the message/service,
                                i.e. 'std_msgs/Int32'.
            @type  clsName:     str

            @param msgID:       Message ID which can be used to get a
                                correspondence between request and response
                                message for a service call.
            @type  msgID:       str

            @param msg:         Message which should be sent. It has to be a
                                JSON compatible dictionary where part or the
                                complete message can be replaced by a StringIO
                                instance which is interpreted as binary data.
            @type  msg:         {str : {} / base_types / StringIO} / StringIO
        """
        # TODO: What should we do, if the interface exists, but there are no
        #       connections?
        #       For now the message is just dropped, which is fatal if it is a
        #       service call, i.e. the caller will wait forever for a response
        try:
            self._interfaces[iTag].receive(clsName, msgID, msg)
        except (DeadReferenceError, PBConnectionLost):
            raise DeadConnection

    def sendToClient(self, iTag, msgType, msgID, msg):
        """ Process a data message which has been received from an interface
            send the message to the registered connection.

            @param iTag:        Tag which is used to identify the interface
                                from which this message was sent.
            @type  iTag:        str

            @param clsName:     Message type/Service type consisting of the
                                package and the name of the message/service,
                                i.e. 'std_msgs/Int32'.
            @type  clsName:     str

            @param msgID:       Message ID which can be used to get a
                                correspondence between request and response
                                message for a service call.
            @type  msgID:       str

            @param msg:         Message which should be sent. It has to be a
                                JSON compatible dictionary where part or the
                                complete message can be replaced by a StringIO
                                instance which is interpreted as binary data.
            @type  msg:         {str : {} / base_types / StringIO} / StringIO
        """
        if not self._connection:
            # It is possible that the connection is already lost when a data
            # message is sent, e.g. when the client just disconnects without
            # properly removing the interfaces, then the interfaces are only
            # removed after given TIMEOUT, but the connection will already be
            # gone
            # TODO: What is the proper reaction to a missing connection, i.e.
            #       once reconnecting clients are available... ?
            return

        self._connection.sendMessage(iTag, msgType, msgID, msg)

    def sendToClientInterfaceStatusUpdate(self, iTag, status):
        """ Send a status change which should be used to start or stop the
            corresponding interface on the client-side to the registered
            connection.

            @param iTag:        Tag which is used to identify the interface
                                which changed its status.
            @type  iTag:        str

            @param status:      Boolean indicating whether the interface should
                                be active or not.
            @type  status:      bool
        """
        if not self._connection:
            # It is possible that the connection is already lost when a status
            # message is sent, e.g. when the client just disconnects without
            # properly removing the interfaces, then the interfaces are only
            # removed after given TIMEOUT, but the connection will already be
            # gone
            # TODO: What is the proper reaction to a missing connection, i.e.
            #       once reconnecting clients are available... ?
            return

        self._connection.sendInterfaceStatusUpdate(iTag, status)

    def destroy(self):
        """ # TODO: Add doc
        """
        self._connection = None
        Namespace.remote_destroy(self)

    def remote_destroy(self):
        """ Method should be called to destroy the robot and will take care
            of destroying all objects owned by this robot as well as
            deleting all circular references.
        """
        if self._connection:
            self._connection.destroy()

        self.destroy()


class RobotClient(Endpoint):
    """ Realm for the connections to the robots. It is responsible for storing
        all connections.
    """
    implements(IRobotRealm)

    # CONFIG
    CONNECT_TIMEOUT = 30
    RECONNECT_TIMEOUT = 10

    def __init__(self, reactor, masterIP, masterPort, commPort, extIP, extPort,
                 loader, converter):
        """ Initialize the Robot Client.

            @param reactor:     Reference to the twisted reactor used in this
                                robot process.
            @type  reactor:     twisted::reactor

            @param masterIP:    IP address of the Master process.
            @type  masterIP:    str

            @param masterPort:  Port which should be used to authenticate the
                                user with the Master process.
            @type  masterPort:  int

            @param commPort:    Port where the server for the cloud engine
                                internal communication is listening for
                                incoming connections.
            @type  commPort:    int

            @param extIP:       IP address of network interface used for the
                                external communication.
            @type  extIP:       str

            @param extPort:     Port where the server for the external
                                communication is listening for WebSocket
                                connections.
            @type  extPort:     int

            @param loader:      Object which is used to load Python modules
                                from ROS packages.
            @type  loader:      rce.util.loader.Loader

            @param converter:   Converter which takes care of converting the
                                messages from JSON to ROS message and vice
                                versa.
            @type  converter:   rce.util.converter.Converter
        """
        Endpoint.__init__(self, reactor, loader, commPort)

        self._masterIP = masterIP
        self._masterPort = masterPort
        self._extAddress = '{0}:{1}'.format(extIP, extPort)
        self._loader = loader
        self._converter = converter

        self._connections = set()
        self._deathCandidates = {}

    @property
    def converter(self):
        """ Reference to the message converter used by the Converter
            interfaces.
        """
        return self._converter

    def registerConnection(self, connection):
        assert connection not in self._connections
        self._connections.add(connection)

        # Add the connection also to the death candidates
        assert connection not in self._deathCandidates
        deathCall = self._reactor.callLater(self.CONNECT_TIMEOUT,
                                            self._killConnection, connection)
        self._deathCandidates[connection] = deathCall


    def unregisterConnection(self, connection):
        assert connection in self._connections

        # First remove the connection from the death candidates if necessary
        deathCall = self._deathCandidates.pop(connection, None)
        if deathCall and deathCall.active():
            deathCall.cancel()

        # Unregister the candidates
        self._connections.remove(connection)

    def _killConnection(self, connection):
        """ Internally used method to destroy a connection whose reconnect
            timeout was reached or which never as successfully connected.

            @param connection:  Connection which should be destroyed.
            @type  connection:  rce.robot.Connection
        """
        assert connection in self._connections
        assert connection in self._deathCandidates

        deathCall = self._deathCandidates.pop(connection)
        if deathCall.active():
            deathCall.cancel()

        connection.destroy()

    def _cbAuthenticated(self, avatar, connection):
        """ Method is used internally as a callback which is called when the
            user of a newly connected robot has been successfully authenticated
            by the Master process.

            @param avatar:      User avatar returned by the Master process upon
                                successful login and authentication.
            @type  avatar:      twisted.spread.pb.RemoteReference

            @param connection:  Representation of the connection to the robot
                                which is used in the Robot process.
            @type  connection:  rce.robot.Connection
        """
        connection.registerAvatar(avatar)
        return avatar.callRemote('getUserView', False)

    def _cbConnected(self, view, connection):
        """ Method is used internally as a callback which is called when the
            Robot view has been successfully retrieved from the Master process
            for the user of a newly connected robot.

            @param view:        Robot view returned by the Master process.
            @type  view:        twisted.spread.pb.RemoteReference

            @param connection:  Representation of the connection to the robot
                                which is used in the Robot process.
            @type  connection:  rce.robot.Connection
        """
        if not self._avatar:  # This is RobotEndpointAvatar and not User Avatar.
            raise ForwardingError('Avatar reference is missing.')

        view = RobotView(view, connection)
        namespace = Robot(self, connection)
        connection.registerView(view)
        connection.registerNamespace(namespace)
        return self._avatar.callRemote('setupNamespace', namespace,
                                       connection.userID, connection.robotID)

    def login(self, userID, robotID, password):
        """ Callback for Robot connection to login and authenticate.

            @param userID:      User ID under which the robot is logging in.
            @type  userID:      str

            @param robotID:     Unique ID of the robot in the namespace of the
                                user under which the robot is logging in.
            @type  robotID:     str

            @param password:    Hashed password as hex-encoded string which is
                                used to authenticate the user.
            @type  password:    str

            @return:            Representation of the connection to the robot
                                which is used in the Robot process.
                                (type: rce.robot.Connection)
            @rtype:             twisted.internet.defer.Deferred
        """
        conn = Connection(self, userID, robotID)

        factory = PBClientFactory()
        self._reactor.connectTCP(self._masterIP, self._masterPort, factory)

        d = factory.login(UsernamePassword(userID, password))
        d.addCallback(self._cbAuthenticated, conn)
        d.addCallback(self._cbConnected, conn)
        d.addCallback(lambda _: conn)
        return d

    def registerWebsocketProtocol(self, connection, protocol):
        """ Register the client protocol with a Connection object.

            @param connection:  Connection where the protocol should be
                                registered.
            @type  connection:  rce.robot.Connection

            @param protocol:    Protocol which should be registered.
            @type  protocol:    rce.comm.interfaces.IServersideProtocol
        """
        assert connection in self._deathCandidates
        connection.registerProtocol(protocol)
        self._deathCandidates.pop(connection).cancel()

    def unregisterWebsocketProtocol(self, connection, protocol):
        """ Unregister the client protocol from a Connection object.

            @param connection:  Connection where the protocol should be
                                unregistered.
            @type  connection:  rce.robot.Connection

            @param protocol:    Protocol which should be unregistered.
            @type  protocol:    rce.comm.interfaces.IServersideProtocol
        """
        assert connection not in self._deathCandidates
        deathCall = self._reactor.callLater(self.RECONNECT_TIMEOUT,
                                            self._killConnection, connection)
        self._deathCandidates[connection] = deathCall

        connection.unregisterProtocol(protocol)

    def remote_getWebsocketAddress(self):
        """ Get the address of the WebSocket server running in this process.

            @return:            Address which can be used to connect to the
                                cloud engine using a WebSocket connection. The
                                address has the form [IP]:[port]
            @rtype:             str
        """
        return self._extAddress

    def terminate(self):
        """ Method should be called to terminate the client before the reactor
            is stopped.

            @return:            Deferred which fires as soon as the client is
                                ready to stop the reactor.
            @rtype:             twisted.internet.defer.Deferred
        """
        for call in self._deathCandidates.itervalues():
            call.cancel()

        self._deathCandidates = {}

        for connection in self._connections.copy():
            connection.destroy()
        assert len(self._connections) == 0

        Endpoint.terminate(self)


def main(reactor, cred, masterIP, masterPort, consolePort,
                extIP, extPort, commPort, pkgPath, customConverters):
    log.startLogging(sys.stdout)

    def _err(reason):
        print(reason)
        reactor.stop()

    factory = PBClientFactory()
    reactor.connectTCP(masterIP, masterPort, factory)

    rosPath = []
    for path in get_ros_paths() + [p for p, _ in pkgPath]:
        if path not in rosPath:
            rosPath.append(path)

    loader = Loader(rosPath)
    converter = Converter(loader)

    for customConverter in customConverters:
        # Get correct path/name of the converter
        module, className = customConverter.rsplit('.', 1)

        # Load the converter
        mod = __import__(module, fromlist=[className])
        converter.addCustomConverter(getattr(mod, className))

    client = RobotClient(reactor, masterIP, consolePort, commPort, extIP,
                         extPort, loader, converter)
    d = factory.login(cred, client)
    d.addCallback(lambda ref: setattr(client, '_avatar', ref))
    d.addErrback(_err)

    # portal = Portal(client, (client,))
    robot = CloudEngineWebSocketFactory(client,
                                        'ws://localhost:{0}'.format(extPort))
    listenWS(robot)

    reactor.addSystemEventTrigger('before', 'shutdown', client.terminate)
    reactor.run()

########NEW FILE########
__FILENAME__ = rosproxy
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/rosproxy.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Mayank Singh
#
#

# Python specific imports
import httplib
import json
import fcntl

# ROS specific imports
import rospy
from rosservice import get_service_list
# TODO: Unused imports
#from rosservice import get_service_type as rosservice_get_service_type
#from rosservice import get_service_node as rosservice_get_service_node
#from rosservice import get_service_uri
#from rostopic import find_by_type
#from rosnode import get_node_names
#from rosgraph.masterapi import Master

get_published_topics = rospy.get_published_topics

# twisted specific imports
from twisted.cred.error import UnauthorizedLogin
from twisted.python import log
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET, Site
from twisted.internet.defer import fail, succeed

# rce specific imports
from rce.util.error import InternalError


class InvalidRequest(Exception):
    """ Exception is raised in case the HTTP request could not be processed.
    """


class ROSProxy(object):
    def get_services(self):
        """ Returns a list of all the services advertised in the ROS system
        """
        return get_service_list()

    def get_topics(self):
        """ Returns a list of all the topics being published in the ROS system
        """
        return [x[0] for x in get_published_topics()]


class ConsoleROSProxyAuthentication(Resource):
    """ Authenticator and Request handler for the ROS Proxy Web Server.
    """
    isLeaf = True

    def __init__(self):
        self._ros = ROSProxy()
        self._dbFile = "/opt/rce/data/rosenvbridge.db"

    def _checkDB(self, userID, key):
        """ Method to check the rosproxy database to authenticate a web
            request.

            @param userID:    Username
            @type userID:     string

            @param key:       Secret key
            @type key:        string
        """
        # TODO: Why not return True directly instead all lines will be read
        # TODO: Should this be deferred to a separate thread due to flock,
        #       which is a blocking call?
        found = False
        with open(self._dbFile, 'r') as bridgefile:
            fcntl.flock(bridgefile.fileno(), fcntl.LOCK_EX)
            lines = bridgefile.readlines()
            for line in lines:
                g = line.split(':')
                if g[0] == userID and str(g[1].rstrip()) == str(key):
                    found = True
        return found

    def _processGETReq(self, args):
        """ Internally used method to process a GET request.
        """
        try:
            action = args['action']
            userID = args['userID']
            key = args['key']
        except KeyError as e:
            return fail(InvalidRequest('Request is missing parameter: '
                                       '{0}'.format(e)))

        if not self._checkDB(userID[0], key[0]):
            return fail(UnauthorizedLogin("Unknown user or key"))

        for name, param in [('action', action), ('userID', userID),
                            ('key', key)]:
            if len(param) != 1:
                return fail(InvalidRequest("Parameter '{0}' has to be unique "
                                           'in request.'.format(name)))

        return self.parseInputLine(action)

    def parseInputLine(self, action):
        """ Function to route various command requests.
            @param action:    The command to be executed.
            @type action:     list
        """
        output = None
        if action is not None and action is not '':
            func = getattr(self, 'cmd_' + str(action[0]).upper(), None)
            if func is not None:
                output = func()
            else:
                return fail(InvalidRequest("No such action"))
        return succeed(output)

    def cmd_SERVICES(self):
        """ Handler for services call.
        """
        return self._ros.get_services()

    def cmd_TOPICS(self):
        """ Handler for topics call.
        """
        return self._ros.get_topics()

    def _processGETResp(self, output, request):
        """ Internally used method to process a response to a GET request from
            the realm.
        """
        msg = {'key' : output}

        self._render_GET(request, httplib.OK,
                         'application/json; charset=utf-8', json.dumps(msg))

    def _processGETErr(self, e, request):
        """ Internally used method to process an error to a GET request from
            the realm.
        """
        if e.check(InvalidRequest):
            msg = e.getErrorMessage()
            code = httplib.BAD_REQUEST
        elif e.check(UnauthorizedLogin):
            msg = e.getErrorMessage()
            code = httplib.UNAUTHORIZED
        elif e.check(InternalError):
            e.printTraceback()
            msg = 'Internal Error'
            code = httplib.INTERNAL_SERVER_ERROR
        else:
            e.printTraceback()
            msg = 'Fatal Error'
            code = httplib.INTERNAL_SERVER_ERROR

        self._render_GET(request, code, 'text/plain; charset=utf-8', msg)

    def _render_GET(self, request, code, ctype, msg):
        """ Internally used method to render the response to a GET request.
        """
        request.setResponseCode(code)
        request.setHeader('content-type', ctype)
        request.write(msg)
        request.finish()

    def render_GET(self, request):
        """ This method is called by the twisted framework when a GET request
            was received.
        """
        d = self._processGETReq(request.args)
        d.addCallback(self._processGETResp, request)
        d.addErrback(self._processGETErr, request)

        return NOT_DONE_YET


def main(reactor, rosproxyPort):
    f = open('/opt/rce/data/rosproxy.log', 'w')
    log.startLogging(f)

    def terminate():
        reactor.callFromThread(reactor.stop)

    rospy.on_shutdown(terminate)

    #HTTP Server
    reactor.listenTCP(rosproxyPort, Site(ConsoleROSProxyAuthentication()))

    reactor.run(installSignalHandlers=False)

    f.close()

########NEW FILE########
__FILENAME__ = endpoint
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/slave/endpoint.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# twisted specific imports
from twisted.python import log
from twisted.python.failure import Failure
from twisted.internet.defer import fail
from twisted.internet.protocol import ServerFactory, ClientCreator
from twisted.spread.pb import Referenceable, Error, \
    DeadReferenceError, PBConnectionLost

# rce specific imports
from rce.slave.protocol import Loopback, RCEInternalProtocol


class ConnectionError(Error):
    """ Error is raised when the connection failed unexpectedly.
    """


class Endpoint(Referenceable):
    """ Abstract base class for an Endpoint in a slave process.
    """
    def __init__(self, reactor, loader, commPort):
        """ Initialize the Endpoint.

            @param reactor:     Reference to the twisted reactor used in this
                                robot process.
            @type  reactor:     twisted::reactor

            @param loader:      Reference to object which is used to load
                                resources from ROS packages.
            @type  loader:      rce.util.loader.Loader

            @param commPort:    Port where the server for the cloud engine
                                internal communication will listen for incoming
                                connections.
            @type  commPort:    int
        """
        self._avatar = None
        self._reactor = reactor
        self._loader = loader

        reactor.listenTCP(commPort, _RCEInternalServerFactory(self))

        self._namespaces = set()

        self._loopback = None
        self._pendingConnections = {}
        self._protocols = set()

    @property
    def reactor(self):
        """ Reference to twisted::reactor. """
        return self._reactor

    @property
    def loader(self):
        """ Reference to ROS components loader. """
        return self._loader

    def registerAvatar(self, avatar):
        """ Register the PB Avatar received from the master process.

            @param avatar:      Avatar which should be registered.
            @type  avatar:      twisted.spread.pb.RemoteReference
        """
        assert self._avatar is None
        self._avatar = avatar

    def registerNamespace(self, namespace):
        assert namespace not in self._namespaces
        self._namespaces.add(namespace)

    def unregisterNamespace(self, namespace):
        assert namespace in self._namespaces
        self._namespaces.remove(namespace)
        self.referenceDied('namespaceDied', namespace)

    def remote_getLoopback(self):
        """ Get the loopback protocol.

            @return:            Reference to the loopback protocol.
            @rtype:             rce.slave.protocol.Loopback
        """
        if not self._loopback:
            self._loopback = Loopback(self)

        return self._loopback

    def remote_prepareConnection(self, connID, key, auth):
        """ Prepare the endpoint for the connection attempt by adding the
            necessary connection information to the remote process.

            @param connID:      Unique ID which is used to identify the
                                connection and respond with the appropriate
                                key.
            @type  connID:      str

            @param key:         Key which is sent to the other side to
                                authenticate the endpoint.
            @type  key:         str

            @param auth:        Authenticator which is used to validate the
                                key received from the other side.
            @type  auth:        twisted.spread.pb.RemoteReference
        """
        assert connID not in self._pendingConnections
        self._pendingConnections[connID] = [key, auth]

    def remote_connect(self, connID, addr):
        """ Connect to the endpoint with the given address using the
            connection information matching the received ID.

            @param connID:      Unique ID which is used to identify the tuple
                                containing the connection information.
            @type  connID:      str

            @param addr:        Address to which the endpoint should connect.
                                It consists of an IP address and a port number.
            @type  addr:        (str, int)
        """
        assert connID in self._pendingConnections

        # Retrieve the key which should be sent and replace it with None to
        # indicate that the key has already been sent
        info = self._pendingConnections[connID]
        key, auth = info
        info[0] = None

        client = ClientCreator(self._reactor, RCEInternalProtocol, self)
        d = client.connectTCP(*addr)
        d.addCallback(lambda p: p.sendInit(connID, key))
        d.addErrback(self._connectError, auth)

    def _connectError(self, failure, auth):
        failure.printTraceback()
        # TODO: Signal back the error
        # v does not work
        #auth.callRemote('verifyKey', None, failure)

    def processInit(self, protocol, connID, remoteKey):
        """ Callback for the RCE Internal Protocol which is called when the
            protocol received an init message which has to be processed.

            @param protocol:    Protocol instance which received the init
                                message.
            @type  protocol:    rce.slave.protocol.RCEInternalProtocol

            @param connID:      Unique ID which is used to identify the
                                connection.
            @type  connID:      str

            @param remoteKey:   Key which was received from the other side to
                                authenticate the endpoint.
            @type  remoteKey:   str

            @return:            True if the connection should be accepted.
            @rtype:             twisted.internet.defer.Deferred
        """
        try:
            key, auth = self._pendingConnections[connID]
        except KeyError:
            return fail(Failure(ConnectionError('Connection was not '
                                                'expected.')))

        try:
            if key:
                protocol.sendInit(connID, key)
        except Exception as e:
            failure = Failure(e)
            # TODO: Signal back the error
            # v does not work
            #auth.callRemote('verifyKey', None, failure)
            return fail(failure)
        else:
            return auth.callRemote('verifyKey', remoteKey, protocol)

        # Should never be reached...
        raise RuntimeError

    def registerProtocol(self, protocol):
        assert protocol not in self._protocols
        self._protocols.add(protocol)

    def unregisterProtocol(self, protocol):
        assert protocol in self._protocols
        self._protocols.remove(protocol)
        self.referenceDied('protocolDied', protocol)

    def referenceDied(self, method, reference):
        """ Internally used method to inform the Master process that a remote
            referenced object has died.
        """
        def eb(failure):
            if not failure.check(PBConnectionLost):
                log.err(failure)

        try:
            self._avatar.callRemote(method, reference).addErrback(eb)
        except (DeadReferenceError, PBConnectionLost):
            pass

    def terminate(self):
        """ Method should be called to terminate the endpoint before the
            reactor is stopped.

            @return:            Deferred which fires as soon as the client is
                                ready to stop the reactor.
            @rtype:             twisted.internet.defer.Deferred
        """
        self._pendingConnections = {}

        for protocol in self._protocols.copy():
            protocol.remote_destroy()
        # Can not check here, because protocols are unregistered when the
        # connection is lost and remote_destroy only requests to lose the
        # connection
        #assert len(self._protocols) == 0

        if self._loopback:
            self._loopback.remote_destroy()
            self._loopback = None

        for namespace in self._namespaces.copy():
            namespace.remote_destroy()

        assert len(self._namespaces) == 0

        self._factory = None


class _RCEInternalServerFactory(ServerFactory):
    """ Server Factory for the cloud engine internal communication.
    """
    def __init__(self, endpoint):
        self._endpoint = endpoint

    def buildProtocol(self, addr):
        return RCEInternalProtocol(self._endpoint)

########NEW FILE########
__FILENAME__ = interface
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/slave/interface.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
from uuid import UUID

# twisted specific imports
from twisted.python import log
from twisted.spread.pb import Referenceable, Error

# rce specific imports
from rce.util.error import InternalError


class Types(object):
    """ Available Interface types.
    """
    SERVICE_CLIENT = 0
    SERVICE_PROVIDER = 3
    PUBLISHER = 1
    SUBSCRIBER = 2
    _PREFIX_NAMES = ['ServiceClient', 'Publisher',
                     'Subscriber', 'ServiceProvider']

    CONVERTER = 0
    FORWARDER = 1
    INTERFACE = 2
    _SUFFIX_NAMES = ['Converter', 'Forwarder', 'Interface']

    @staticmethod
    def encode(typename):
        """ Encode an Interface type in string form as as an int.

            @param typename:    Interface type which should be encoded.
            @type  typename:    str

            @return:            Encoded Interface type.
            @rtype:             int
        """
        if typename.startswith(Types._PREFIX_NAMES[1]):
            typeint = Types.PUBLISHER
        elif typename.startswith(Types._PREFIX_NAMES[2]):
            typeint = Types.SUBSCRIBER
        elif typename.startswith(Types._PREFIX_NAMES[3]):
            typeint = Types.SERVICE_PROVIDER
        elif typename.startswith(Types._PREFIX_NAMES[0]):
            typeint = Types.SERVICE_CLIENT
        else:
            raise TypeError('Invalid interface type provided.')

        if typename.endswith(Types._SUFFIX_NAMES[2]):
            typeint += 4 * Types.INTERFACE
        elif typename.endswith(Types._SUFFIX_NAMES[0]):
            typeint += 4 * Types.CONVERTER
        elif typename.endswith(Types._SUFFIX_NAMES[1]):
            typeint += 4 * Types.FORWARDER
        else:
            raise TypeError('Invalid interface type provided.')

        return typeint

    @staticmethod
    def decode(typenr):
        """ Decode an Interface type in int form as as a string.

            @param typenr:      Encoded Interface type which should be decoded.
            @type  typenr:      int

            @return:            Interface type.
            @rtype:             str
        """
        assert 0 <= typenr < 12
        return ''.join((Types._PREFIX_NAMES[typenr % 4],
                        Types._SUFFIX_NAMES[int(typenr / 4)]))

    @staticmethod
    def connectable(iTypeA, iTypeB):
        """ Check if the two Interfaces are connectable.

            @param iTypeX:      Encoded Interface type.
            @type  iTypeX:      int

            @return:            True, if they are connectable; False otherwise.
            @rtype:             bool
        """
        return (iTypeA % 4) + (iTypeB % 4) == 3


class InvalidResoureName(Error):
    """ Exception is raised in case the interface resource name is invalid.
    """


class Interface(Referenceable):
    """ Abstract base class for an Interface in a slave process.
    """
    def __init__(self, owner, uid, addr):
        """ Initialize the Interface.

            @param owner:       Namespace for which the Interface is created.
            @param owner:       rce.slave.namespace.Namespace

            @param uid:         Unique ID which is used to identify the
                                interface in the internal communication.
            @type  uid:         uuid.UUID

            @param addr:        Unique address which is used to identify the
                                interface in the external communication.
            @type  addr:        str
        """
        self._owner = owner
        self._uid = uid
        self._addr = addr

        # Has to be called after assignment of 'self._addr', because
        # 'registerInterface' uses the property 'addr'
        owner.registerInterface(self)

        self._protocols = {}
        self._ready = False

    @property
    def UID(self):
        """ Unique ID of the interface (internal communication). """
        return self._uid

    @property
    def addr(self):
        """ Unique ID of the interface (external communication). """
        return self._addr

    def unregisterProtocol(self, protocol):
        """ Callback for the protocol to inform the interface that the
            protocol has died and should no longer be used.

            @param protocol:    Protocol which should be unregistered.
            @type  protocol:    rce.slave.protocol._Protocol
        """
        assert protocol in self._protocols
        del self._protocols[protocol]

        if not self._protocols:
            self.stop()

    def remote_connect(self, protocol, remoteID):
        """ Connect this interface to another interface using a local protocol.

            @param protocol:    Protocol instance which should be used to
                                establish the connection.
            @type  protocol:    rce.slave.protocol._Protocol

            @param remoteID:    Unique ID of the interface to which this
                                interface should be connected.
            @type  remoteID:    str
        """
        if not self._protocols:
            self.start()

        remoteID = UUID(bytes=remoteID)

        if protocol not in self._protocols:
            self._protocols[protocol] = set()

        assert remoteID not in self._protocols[protocol]
        self._protocols[protocol].add(remoteID)

        protocol.registerConnection(self, remoteID)

    def remote_disconnect(self, protocol, remoteID):
        """ Disconnect this interface from another interface.

            @param protocol:    Protocol instance which was used for the
                                connection.
            @type  protocol:    rce.slave.protocol._Protocol

            @param remoteID:    Unique ID of the interface from which this
                                interface should be disconnected.
            @type  remoteID:    str
        """
        remoteID = UUID(bytes=remoteID)

        protocol.unregisterConnection(self, remoteID)

        assert remoteID in self._protocols[protocol]
        self._protocols[protocol].remove(remoteID)

        if not self._protocols[protocol]:
            del self._protocols[protocol]

        if not self._protocols:
            self.stop()

    def remote_destroy(self):
        """ Method should be called to destroy the interface and will take care
            of deleting all circular references.
        """
        # TODO: WHY ???
        if not self._owner:
            return

        self.stop()

        if self._owner:
            self._owner.unregisterInterface(self)
            self._owner = None

    def start(self):
        """ This method is used to setup the interface.

            Don't overwrite this method; instead overwrite the hook _start.

            @raise:     rce.error.InternalError if the interface can not be
                        started.
        """
        if self._ready:
            return

        self._start()
        self._ready = True

    def stop(self):
        """ This method is used to stop the interface.

            Don't overwrite this method; instead overwrite the hook _stop.
        """
        if not self._ready:
            return

        self._stop()
        self._ready = False

    def send(self, msg, msgID, protocol, remoteID):
        """ This method is used to send a message to the endpoint.

            Don't overwrite this method; instead overwrite the method _send.
            If the interface does not overwrite the method _send, it is assumed
            that the interface does not support this action and an
            InternalError is raised when send is called.

            @param msg:         Message which should be sent in serialized
                                form.
            @type  msg:         str

            @param msgID:       Message ID which is used to match response
                                message.
            @type  msgID:       str

            @param protocol:    Protocol instance through which the message
                                was sent.
            @type  protocol:    rce.slave.protocol._Protocol

            @param remoteID:    Unique ID of the Interface which sent the
                                message.
            @type  remoteID:    uuid.UUID
        """
        if not self._ready:
            raise InternalError('Interface is not ready to send a message.')

        try:
            if remoteID not in self._protocols[protocol]:
                raise KeyError
        except KeyError:
            log.msg('Received message dropped, because interface does not '
                    'expected the message.')

        self._send(msg, msgID, protocol, remoteID)

    def received(self, msg, msgID):
        """ This method is used to send a received message from the endpoint
            to the appropriate protocols.

            @param msg:         Message which should be sent in serialized
                                form.
            @type  msg:         str

            @param msgID:       Message ID which is used to match response
                                message.
            @type  msgID:       str
        """
        for protocol in self._protocols:
            protocol.sendMessage(self, msg, msgID)

    def respond(self, msg, msgID, protocol, remoteID):
        """ This method is used to send a received message from the endpoint
            to the specified protocol/interface as a response.

            @param msg:         Message which should be sent in serialized
                                form.
            @type  msg:         str

            @param msgID:       Message ID which is used to match response
                                message.
            @type  msgID:       str

            @param protocol:    Protocol instance to which the response should
                                be sent.
            @type  protocol:    rce.slave.protocol._Protocol

            @param remoteID:    Unique ID of the Interface to which the
                                response be sent.
            @type  remoteID:    uuid.UUID
        """
        protocol.sendMessage(self, msg, msgID, remoteID)

    ###
    ### Hooks which can / have to be overwritten in Interface implementation
    ###

    def _start(self):
        pass

    def _stop(self):
        pass

    def _send(self, msg, msgID, protocol, remoteID):
        raise InternalError('Interface does not support sending of a message.')

########NEW FILE########
__FILENAME__ = namespace
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/slave/namespace.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
from uuid import UUID

# twisted specific imports
from twisted.spread.pb import Referenceable

# rce specific imports
from rce.util.error import InternalError


class Namespace(Referenceable):
    """ Abstract base class for a Namespace in a slave process.
    """
    def __init__(self, endpoint):
        """ Initialize the Namespace.
        """
        self._endpoint = endpoint
        endpoint.registerNamespace(self)

        self._interfaces = {}
        self._map = {}

    @property
    def reactor(self):
        """ Reference to twisted::reactor. """
        return self._endpoint.reactor

    @property
    def loader(self):
        """ Reference to ROS components loader. """
        return self._endpoint.loader

    def registerInterface(self, interface):
        addr = interface.addr

        assert addr not in self._interfaces
        self._interfaces[addr] = interface

    def unregisterInterface(self, interface):
        addr = interface.addr

        assert addr in self._interfaces
        del self._interfaces[addr]
        self._endpoint.referenceDied('interfaceDied', interface)

    def remote_createInterface(self, uid, iType, msgType, addr):
        """ Create an Interface object in the namespace and therefore in
            the endpoint.

            @param uid:         Unique ID which is used to identify the
                                interface in the internal communication.
            @type  uid:         str

            @param iType:       Type of the interface encoded as an integer.
                                Refer to rce.slave.interface.Types for more
                                information.
            @type  IType:       int

            @param clsName:     Message type/Service type consisting of the
                                package and the name of the message/service,
                                i.e. 'std_msgs/Int32'.
            @type  clsName:     str

            @param addr:        Unique address which is used to identify the
                                interface in the external communication.
            @type  addr:        str

            @return:            New Interface instance.
            @rtype:             rce.slave.interface.Interface
        """
        try:
            cls = self._map[iType]
        except KeyError:
            raise InternalError('Interface type is not supported by this '
                                'namespace.')

        return cls(self, UUID(bytes=uid), msgType, addr)

    def remote_destroy(self):
        """ Method should be called to destroy the namespace and will take care
            of destroying all interfaces owned by this namespace as well as
            deleting all circular references.
        """
        for interface in self._interfaces.values():
            interface.remote_destroy()

        assert len(self._interfaces) == 0

        if self._endpoint:
            self._endpoint.unregisterNamespace(self)
            self._endpoint = None

########NEW FILE########
__FILENAME__ = protocol
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/slave/protocol.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import struct
from uuid import UUID

# twisted specific imports
from twisted.python import log
from twisted.protocols.basic import Int32StringReceiver
from twisted.spread.pb import Referenceable

# rce specific imports
from rce.util.error import InternalError


class _Protocol(Referenceable):
    """ Abstract base class for a internal Protocol which interacts with the
        Endpoint, Namespace, and Interfaces in a slave process.
    """
    def __init__(self, endpoint):
        """ Initialize the Protocol.
        """
        self._receivers = {}
        self._endpoint = endpoint
        endpoint.registerProtocol(self)

    def sendMessage(self, interface, msg, msgID, remoteID=None):
        """ Send a message received from an Interface to the other side.

            @param interface:   Interface which wants to send the message.
            @type  interface:   rce.slave.interface.Interface

            @param msg:         Message which should be sent.
            @type  msg:         str

            @param msgID:       Unique ID which can be used to find a
                                correspondence between request / response
                                message.
            @type  msgID:       uuid.UUID

            @param remoteID:    If the remote ID is supplied than only this
                                Interface will receive the message, regardless
                                of additional interfaces which might be
                                registered.
            @type  remoteID:    uuid.UUID
        """
        raise NotImplementedError("Method 'sendMessage' has to be "
                                  'implemented.')

    def messageReceived(self, remoteID, msg, msgID, destID=None):
        """ Protocol internal method used to send a received message to the
            stored receivers.

            @param remoteID:    Unique ID of the Interface on the other side
                                which sent the message.
            @type  remoteID:    uuid.UUID

            @param msg:         Message which was received.
            @type  msg:         str

            @param msgID:       Unique ID which can be used to find a
                                correspondence between request / response
                                message.
            @type  msgID:       uuid.UUID

            @param destID:      If the dest ID is supplied than only this
                                Interface will receive the message, regardless
                                of additional interfaces which might be
                                registered.
            @type  destID:      uuid.UUID
        """
        if remoteID not in self._receivers:
            log.msg('Received message dropped, because there is no interface '
                    'ready for the message.')
            return

        for interface in self._receivers[remoteID]:
            if destID:
                if interface.UID == destID:
                    interface.send(msg, msgID, self, remoteID)
                    break
            else:
                interface.send(msg, msgID, self, remoteID)

    def registerConnection(self, interface, remoteID):
        """ Register the connection between the local Interface and the remote
            Interface such that the two interfaces can communicate with each
            other.

            @param interface:   Reference to the local Interface.
            @type  interface:   rce.slave.interface.Interface

            @param remoteID:    Unique ID of the remote Interface.
            @type  remoteID:    uuid.UUID
        """
        if remoteID not in self._receivers:
            self._receivers[remoteID] = set()
        else:
            assert interface not in self._receivers[remoteID]

        self._receivers[remoteID].add(interface)

    def unregisterConnection(self, interface, remoteID):
        """ Unregister the connection between the local Interface and the
            remote Interface such that the two interfaces can no longer
            communicate with each other.

            @param interface:   Reference to the local Interface.
            @type  interface:   rce.slave.interface.Interface

            @param remoteID:    Unique ID of the remote Interface.
            @type  remoteID:    uuid.UUID
        """
        assert remoteID in self._receivers
        receivers = self._receivers[remoteID]

        assert interface in receivers
        receivers.remove(interface)

        if not receivers:
            del self._receivers[remoteID]

    def remote_destroy(self):
        """ Method should be called to destroy the protocol and will take care
            of destroying all connections of this Protocol as well as
            deleting all circular references.
        """
        if self._receivers:
            for interface in reduce(set.union, self._receivers.itervalues()):
                interface.unregisterProtocol(self)

            self._receivers = None

        if self._endpoint:
            self._endpoint.unregisterProtocol(self)
            self._endpoint = None


class Loopback(_Protocol):
    """ Special Protocol 'Loopback' which can be used to connect Interfaces
        which are in the same Endpoint.
    """
    def sendMessage(self, interface, msg, msgID, remoteID=None):
        self.messageReceived(interface.UID, msg, msgID, remoteID)

    sendMessage.__doc__ = _Protocol.sendMessage.__doc__


class RCEInternalProtocol(Int32StringReceiver, _Protocol):
    """ Protocol which is used to connect Endpoints such that Interfaces in
        different Endpoint are able to communicate.
    """
    # CONFIG
    MAX_LENGTH = 30000000  # Maximal message length in bytes

    _MSG_ID_STRUCT = struct.Struct('!B')
    _TRUE = struct.pack('!?', True)
    _FALSE = struct.pack('!?', False)

    def __init__(self, endpoint):
        """ Initialize the Protocol.

            @param endpoint:    Endpoint for which this Protocol is created.
            @type  endpoint:    rce.slave.endpoint.Endpoint
        """
        _Protocol.__init__(self, endpoint)

        self._initialized = False
        self.stringReceived = self._initReceived

    def _initReceived(self, msg):
        """ Internally used method process a complete string message as long as
            the connection is not yet initialized.

            @param msg:         Message which was received.
            @type  msg:         str
        """
        if len(msg) != 32:
            log.msg('Protocol Error: iInit message has invalid format.')
            self.transport.loseConnection()
            return

        d = self._endpoint.processInit(self, msg[:16], msg[16:])
        d.addCallbacks(self._initSuccessful, self._initFailed)

    def _initSuccessful(self, _):
        self.stringReceived = self._messageReceived
        self._initialized = True

    def _initFailed(self, failure):
        log.msg('Protocol Error: {0}'.format(failure.getErrorMessage()))
        self.transport.loseConnection()

    def _messageReceived(self, msg):
        """ Internally used method process a complete string message after
            the connection has been initialized.

            @param msg:         Message which was received.
            @type  msg:         str
        """
        if len(msg) < 17:
            self.transport.loseConnection()

        flag = msg[:1]

        if flag == self._TRUE:
            destID = UUID(bytes=msg[1:17])
            offset = 17
        elif flag == self._FALSE:
            destID = None
            offset = 1
        else:
            log.msg('Protocol Error: Could not identify flag.')
            self.transport.loseConnection()
            return

        remoteID = UUID(bytes=msg[offset:offset + 16])
        offset += 16

        idLen, = self._MSG_ID_STRUCT.unpack(msg[offset:offset + 1])
        offset += 1

        msgID = msg[offset:offset + idLen]
        offset += idLen

        self.messageReceived(remoteID, buffer(msg, offset), msgID, destID)

    def sendInit(self, connID, key):
        """ Send an init message to the other side.

            @param connID:      Unique ID which is used to identify the
                                connection.
            @type  connID:      str

            @param key:         Key which should be sent with the init message
                                to authenticate this endpoint.
            @type  key:         str
        """
        assert len(connID) == 16
        assert len(key) == 16

        self.sendString(connID + key)

    def sendMessage(self, interface, msg, msgID, remoteID=None):
        assert self._initialized

        uid = interface.UID.bytes
        assert len(uid) == 16

        try:
            idLen = self._MSG_ID_STRUCT.pack(len(msgID))
        except struct.error:
            raise InternalError('Message ID is too long.')

        if remoteID:
            flag = self._TRUE
            rmtID = remoteID.bytes
            assert len(rmtID) == 16
        else:
            flag = self._FALSE
            rmtID = ''

        self.sendString(''.join((flag, rmtID, uid, idLen, msgID, msg)))

    sendMessage.__doc__ = _Protocol.sendMessage.__doc__

    def connectionLost(self, reason):
        """ Method is called by the twisted framework when the connection is
            lost.
        """
        _Protocol.remote_destroy(self)

    def remote_destroy(self):
        """ Method should be called to destroy the connection and the protocol.
            It also takes care of any circular references.
        """
        self.transport.loseConnection()

    def lengthLimitExceeded(self, length):
        print('LENGTH LIMIT EXCEEDED {0}'.format(length))
        Int32StringReceiver.lengthLimitExceeded(self, length)

########NEW FILE########
__FILENAME__ = container
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/util/container.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import os

pjoin = os.path.join

# twisted specific imports
from twisted.python import log

# rce specific imports
from rce.util.process import execute


_CONFIG_CGROUP = """
lxc.cgroup.devices.deny = a
# /dev/null and zero
lxc.cgroup.devices.allow = c 1:3 rwm
lxc.cgroup.devices.allow = c 1:5 rwm
# consoles
lxc.cgroup.devices.allow = c 5:1 rwm
lxc.cgroup.devices.allow = c 5:0 rwm
lxc.cgroup.devices.allow = c 4:0 rwm
lxc.cgroup.devices.allow = c 4:1 rwm
# /dev/{,u}random
lxc.cgroup.devices.allow = c 1:9 rwm
lxc.cgroup.devices.allow = c 1:8 rwm
lxc.cgroup.devices.allow = c 136:* rwm
lxc.cgroup.devices.allow = c 5:2 rwm
# rtc
lxc.cgroup.devices.allow = c 254:0 rwm
"""

_CONFIG_CAP = """
# restrict capabilities
#   can't use: lxc.cap.drop = sys_admin
#   see: man capabilities for more information
#lxc.cap.drop = audit_control
#lxc.cap.drop = audit_write
#lxc.cap.drop = mac_admin
#lxc.cap.drop = mac_override
#lxc.cap.drop = mknod
#lxc.cap.drop = setfcap
#lxc.cap.drop = setpcap
#lxc.cap.drop = sys_boot
#lxc.cap.drop = sys_chroot
#lxc.cap.drop = sys_module
#lxc.cap.drop = sys_rawio
#lxc.cap.drop = sys_time
"""

_FSTAB_BASE = """
proc    {proc}    proc    nodev,noexec,nosuid    0 0
devpts    {devpts}    devpts    defaults    0 0
sysfs    {sysfs}    sysfs    defaults    0 0
"""

_FSTAB_BIND = """
{srcDir}    {dstDir}    none    bind{ro}    0 0
"""


class Container(object):
    """ Class representing a single container.
    """
    def __init__(self, reactor, rootfs, conf, hostname):
        """ Initialize the Container.

            @param reactor:     Reference to the twisted::reactor
            @type  reactor:     twisted::reactor

            @param rootfs:      Filesystem path of the root directory of the
                                container filesystem.
            @type  rootfs:      str

            @param conf:        Filesystem path of folder where configuration
                                files for the container should be stored.
            @type  conf:        str

            @param hostname:    Host name of the container.
            @type  hostname:    str
        """
        self._reactor = reactor
        self._rootfs = rootfs
        self._conf = pjoin(conf, 'config')
        self._fstab = pjoin(conf, 'fstab')
        self._hostname = hostname

        if not os.path.isabs(conf):
            raise ValueError('Container configuration directory is not an '
                             'absolute path.')

        if not os.path.isdir(conf):
            raise ValueError('Container Configuration directory does not '
                             'exist: {0}'.format(conf))

        if os.path.exists(self._conf):
            raise ValueError('There is already a config file in the container '
                             "configuration directory '{0}'.".format(conf))

        if os.path.exists(self._fstab):
            raise ValueError('There is already a fstab file in the container '
                             "configuration directory '{0}'.".format(conf))

        self._ifs = []
        self._fstabExt = []

    def addNetworkInterface(self, name, link=None, ip=None, up=None, down=None):
        """ Add a network interface to the configuration file.

            @param name:    Name of the network interface inside the container.
            @type  name:    str

            @param link:    Name of the network interface in the host system
                            which will be connected to the container network
                            interface.
            @type  link:    str

            @param ip:      IP address which will be assigned to the container
                            network interface. Use '0.0.0.0' for DHCP.
            @type  ip:      str

            @param up:      Path to a script which should be executed in the
                            host system once the interface has to be set up.
            @type  up:      str

            @param down:    Path to a script which should be executed in the
                            host system once the interface has to teared down.
            @type  down:    str
        """
        if up:
            if not os.path.isabs(up):
                raise ValueError('Path to up script has to be absolute.')

            if not os.path.isfile(up):
                raise ValueError('Path to up script is not a file.')

            if not os.access(up, os.X_OK):
                raise ValueError('Up script is not executable.')

        if down:
            if not os.path.isabs(down):
                raise ValueError('Path to down script has to be absolute.')

            if not os.path.isfile(down):
                raise ValueError('Path to down script is not a file.')

            if not os.access(down, os.X_OK):
                raise ValueError('Down script is not executable.')

        self._ifs.append((name, link, ip, up, down))

    def extendFstab(self, src, fs, ro):
        """ Add a line to the fstab file using bind.

            @param src:     Source path in host filesystem.
            @type  src:     str

            @param fs:      Path in container filesystem to which the source
                            should be bound.
            @type  fs:      str

            @param ro:      Flag to indicate whether bind should be read-only
                            or not.
            @type  ro:      bool
        """
        dst = pjoin(self._rootfs, fs)

        if not os.path.isabs(src):
            raise ValueError('Source path has to be absolute.')

        if not os.path.exists(src):
            raise ValueError('Source path does not exist.')

        if not os.path.exists(dst):
            raise ValueError('Destination path does not exist.')

        self._fstabExt.append((src, dst, ro))

    def _setupFiles(self):
        """ Setup the configuration and fstab file.
        """
        with open(self._conf, 'w') as f:
            # Write base config
            f.write('lxc.utsname = {0}\n'.format(self._hostname))
            f.write('\n')
            f.write('lxc.rootfs = {0}\n'.format(self._rootfs))
            f.write('lxc.mount = {0}\n'.format(self._fstab))

            # Write interface config
            for name, link, ip, up, down in self._ifs:
                f.write('\n')
                f.write('lxc.network.type = veth\n')
                f.write('lxc.network.flags = up\n')
                f.write('lxc.network.name = {0}\n'.format(name))

                if link:
                    f.write('lxc.network.link = {0}\n'.format(link))

                if ip:
                    f.write('lxc.network.ipv4 = {0}/24\n'.format(ip))

                if up:
                    f.write('lxc.network.script.up = {0}\n'.format(up))

                if down:
                    f.write('lxc.network.script.down = {0}\n'.format(down))


            # Write cgroup config
            f.write(_CONFIG_CGROUP)

            # Write capabilities config
            # TODO: Add at some point?
            # f.write(_CONFIG_CAP)

        with open(self._fstab, 'w') as f:
            f.write(_FSTAB_BASE.format(proc=pjoin(self._rootfs, 'proc'),
                                       devpts=pjoin(self._rootfs, 'dev/pts'),
                                       sysfs=pjoin(self._rootfs, 'sys')))

            for src, dst, ro in self._fstabExt:
                f.write(_FSTAB_BIND.format(srcDir=src, dstDir=dst,
                                           ro=',ro' if ro else ''))

    def start(self, name):
        """ Start the container.

            @param name:    Name of the container which should be started.
            @type  name:    str

            @return:        Deferred whose callback is triggered on success or
                            whose errback is triggered on failure with an
                            error message.
            @rtype:         twisted.internet.defer.Deferred
        """
        self._setupFiles()

        log.msg("Start container '{0}'".format(name))
        return execute(('/usr/bin/lxc-start', '-n', name, '-f', self._conf,
                        '-d'), reactor=self._reactor)

    def stop(self, name):
        """ Stop the container.

            @param name:        Name of the container which should be stopped.
            @type  name:        str

            @param command:     Deferred whose callback is triggered on success
                                or whose errback is triggered on failure with
                                an error message.
            @type  command:     twisted.internet.defer.Deferred
        """
        log.msg("Stop container '{0}'".format(name))
        return execute(('/usr/bin/lxc-stop', '-n', name), reactor=self._reactor)

########NEW FILE########
__FILENAME__ = converter
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/util/converter.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import time
from datetime import datetime
from functools import partial

try:
    from cStringIO import StringIO, InputType, OutputType
    from StringIO import StringIO as pyStringIO

    def _checkIsStringIO(obj):
        return isinstance(obj, (InputType, OutputType, pyStringIO))
except ImportError:
    from StringIO import StringIO

    def _checkIsStringIO(obj):
        return isinstance(obj, StringIO)

# ROS specific imports
try:
    from genmsg.names import package_resource_name
    from genpy.message import Message
    from rospy.rostime import Duration, Time
except ImportError:
    print('Can not import ROS Python libraries.')
    print('Make sure they are installed and the ROS Environment is setup.')
    exit(1)

# zope specific imports
from zope.interface import implements

# rce specific imports
from rce.util.error import InternalError
from rce.util.interface import verifyClass
from rce.util.converters.interfaces import ICustomROSConverter


def _stringify(obj):
    """ Internally used method to make sure that strings are of type str
        and not of type unicode.
    """
    if isinstance(obj, unicode):
        return obj.encode('utf-8')
    elif isinstance(obj, str):
        return obj
    else:
        raise TypeError('Object is not a string.')


class _DurationConverter(object):
    """ Convert ROS Duration type to JSON style and back.
    """
    implements(ICustomROSConverter)

    def decode(self, data):
        """ Generate a rospy.rostime.Duration instance based on the given data
            which should be a string representation of a float.
        """
        return Duration.from_sec(float(data))

    def encode(self, rosMsg):
        """ Transform the rospy.rostime.Duration instance to a float.
        """
        try:
            return (rosMsg.to_sec(), {})
        except AttributeError:
            raise TypeError('Received object is not a Duration instance.')


class _TimeConverter(object):
    """ Convert ROS Time type to JSON style and back.
    """
    implements(ICustomROSConverter)

    def decode(self, data):
        """ Generate a rospy.rostime.Time instance based on the given data of
            the form 'YYYY-MM-DDTHH:MM:SS.mmmmmm' (ISO 8601).
        """
        if '+' in data:
            data = data[:data.index('+')]

        try:
            dt = datetime(year=int(data[0:4]), month=int(data[5:7]),
                          day=int(data[8:10]), hour=int(data[11:13]),
                          minute=int(data[14:16]), second=int(data[17:19]),
                          microsecond=int(data[20:]))
        except ValueError:
            return Time()

        return Time.from_sec(time.mktime(dt.timetuple()))

    def encode(self, rosMsg):
        """ Transform the rospy.rostime.Time instance to a string of the form
            'YYYY-MM-DDTHH:MM:SS.mmmmmm' (ISO 8601).
        """
        try:
            dt = datetime.fromtimestamp(rosMsg.to_sec())
        except AttributeError:
            raise TypeError('Received object is not a Time instance.')

        return (dt.isoformat(), {})


# Check custom time classes whether the interface is correctly implemented
verifyClass(ICustomROSConverter, _DurationConverter)
verifyClass(ICustomROSConverter, _TimeConverter)


class Converter(object):
    """ This class is used to provide a possibility to convert a ROS message to
        a JSON compatible format and back.

        To add customized Converters use the method 'addCustomConverter' and
        the class must implement the interface 'IROSConverter'.
        As an example view the class ImageConverter.
    """
    _BASE_TYPES = { 'bool'    : bool,
                    'byte'    : int,
                    'char'    : int,
                    'uint8'   : int,
                    'int8'    : int,
                    'uint16'  : int,
                    'int16'   : int,
                    'uint32'  : int,
                    'int32'   : int,
                    'uint64'  : long,
                    'int64'   : long,
                    'float32' : float,
                    'float64' : float,
                    'string'  : str }

    _SPECIAL_TYPES = {  'time'     : _TimeConverter,
                        'duration' : _DurationConverter }

    def __init__(self, loader):
        """ Initialize the Converter.

            @param loader:      Used loader for ROS resources.
            @type  loader:      Loader
        """
        self._loader = loader
        self._customTypes = {}

    def addCustomConverter(self, converter):
        """ Register a new custom Converter.

            @raise:     rce.error.InternalError,
                        rce.util.interfaces.InterfaceError
        """
        verifyClass(ICustomROSConverter, converter)

        if converter.MESSAGE_TYPE in self._customTypes:
            raise InternalError('There are multiple Converters given for '
                                'message type "{0}".'.format(
                                    converter.MESSAGE_TYPE))

        try:
            pkg, name = package_resource_name(converter.MESSAGE_TYPE)
        except ValueError:
            raise InternalError('msg type is not valid. Has to be of the from '
                                'pkg/msg, i.e. std_msgs/Int8.')

        self._customTypes[converter.MESSAGE_TYPE] = (converter,
            self._loader.loadMsg(pkg, name))

    def removeCustomConverter(self, msgType):
        """ Unregister a custom Converter.

            @param msgType:     Message type of ROS message as a string, i.e.
                                'std_msgs/Int8', for which the converter should
                                be removed.
            @type  msgType:     str
        """
        try:
            del self._customTypes[msgType]
        except KeyError:
            InternalError('Tried to remove a custom converter which was '
                          'never added.')

    def _encode(self, rosMsg):
        """ Internally used method which is responsible for the heavy lifting.
        """
        data = {}

        for (slotName, slotType) in zip(rosMsg.__slots__, rosMsg._slot_types):
            if '[]' == slotType[-2:]:
                listBool = True
                slotType = slotType[:-2]
            else:
                listBool = False

            if slotType in self._BASE_TYPES:
                convFunc = self._BASE_TYPES[slotType]
            elif slotType in self._SPECIAL_TYPES:
                convFunc = self._SPECIAL_TYPES[slotType]().encode
            elif slotType in self._customTypes:
                convFunc = self._customTypes[slotType][0]().encode
            else:
                convFunc = self._encode

            if listBool:
                convFunc = partial(map, convFunc)

            try:
                data[slotName] = convFunc(getattr(rosMsg, slotName))
            except ValueError as e:
                raise ValueError('{0}.{1}: {2}'.format(
                                     rosMsg.__class__.__name__, slotName, e))

        return data

    def encode(self, rosMsg):
        """ Generate JSON compatible data from a ROS message.

            @param rosMsg:  The ROS message instance which should be converted.
            @type  rosMsg:  ROS message instance

            @return:        Dictionary containing the parsed message. The basic
                            form does map each field in the ROS message to a
                            key / value pair in the returned data dict. Binaries
                            are added as StringIO instances.
            @rtype:         {}

            @raise:         TypeError, ValueError
        """
        if not isinstance(rosMsg, Message):
            raise TypeError('Given rosMsg object is not an instance of '
                            'genpy.message.Message.')

        for converter, cls in self._customTypes.itervalues():
            if isinstance(rosMsg, cls):
                return converter().encode(rosMsg)

        return self._encode(rosMsg)

    def _decode(self, msgCls, data):
        """ Internally used method which is responsible for the heavy lifting.
        """
        rosMsg = msgCls()

        for (slotName, slotType) in zip(rosMsg.__slots__, rosMsg._slot_types):
            if slotName not in data:
                continue

            if '[]' == slotType[-2:]:
                listBool = True
                slotType = slotType[:-2]
            else:
                listBool = False

            field = data[slotName]

            if listBool and not isinstance(field, (list, tuple)):
                raise TypeError('Given data does not match the definition of '
                                'the ROS message.')

            if slotType == 'string':
                convFunc = _stringify
            elif slotType in self._BASE_TYPES:
                convFunc = self._BASE_TYPES[slotType]
            elif slotType in self._SPECIAL_TYPES:
                convFunc = self._SPECIAL_TYPES[slotType]().decode
            elif slotType in self._customTypes and _checkIsStringIO(field):
                convFunc = self._customTypes[slotType][0]().decode
            else:
                convFunc = partial(self._decode,
                                   self._loader.loadMsg(*slotType.split('/')))

            if listBool:
                convFunc = partial(map, convFunc)

            setattr(rosMsg, slotName, convFunc(field))

        return rosMsg

    def decode(self, msgCls, data):
        """ Generate a ROS message from JSON compatible data.

            @param msgCls:  ROS message class into which the decoded data
                            should filled.
            @type  msgCls:  ROS Message class

            @param data:    Dictionary with keys matching the fields in the
                            desired ROS message. Binary files should be
                            included as StringIO instances.
            @param data:    { str : {} }

            @return:        ROS message of type rosMsg containing the given
                            data.

            @raise:         TypeError, ValueError,
                            rce.util.loader.ResourceNotFound
        """
        if _checkIsStringIO(data):
            for converter, cls in self._customTypes.itervalues():
                if msgCls == cls:
                    return converter().decode(msgCls, data)

        return self._decode(msgCls, data)

########NEW FILE########
__FILENAME__ = image
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/util/converters/image.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
try:
    from cStringIO import StringIO, InputType, OutputType
    from StringIO import StringIO as pyStringIO

    def _checkIsStringIO(obj):
        return isinstance(obj, (InputType, OutputType, pyStringIO))
except ImportError:
    from StringIO import StringIO

    def _checkIsStringIO(obj):
        return isinstance(obj, StringIO)

try:
    import Image
except ImportError:
    print('Can not import Python Image Library.')
    exit(1)

# ROS specific imports
try:
    import sensor_msgs.msg
except ImportError:
    print("Can not import the required ROS Python library 'sensor_msgs'.")
    print('Make sure they are installed and the ROS Environment is setup.')
    exit(1)

# zope specific imports
from zope.interface import implements

# rce specific imports
from rce.util.converters.interfaces import ICustomROSConverter


class ImageConverter(object):
    """ Convert images from PNG file format to ROS sensor message format and
        back.
    """
    implements(ICustomROSConverter)

    MESSAGE_TYPE = 'sensor_msgs/Image'

    _ENCODINGMAP_PY_TO_ROS = { 'L' : 'mono8', 'RGB' : 'rgb8',
                               'RGBA' : 'rgba8', 'YCbCr' : 'yuv422' }
    _ENCODINGMAP_ROS_TO_PY = { 'mono8' : 'L', 'rgb8' : 'RGB',
                               'rgba8' : 'RGBA', 'yuv422' : 'YCbCr' }
    _PIL_MODE_CHANNELS = { 'L' : 1, 'RGB' : 3, 'RGBA' : 4, 'YCbCr' : 3 }

    def decode(self, imgObj):
        """ Convert a image stored (PIL library readable image file format)
            in a StringIO object to a ROS compatible message
            (sensor_msgs.Image).
        """
        if not _checkIsStringIO(imgObj):
            raise TypeError('Given object is not a StringIO instance.')

        # Checking of image according to django.forms.fields.ImageField
        try:
            imgObj.seek(0)
            img = Image.open(imgObj)
            img.verify()
        except:
            raise ValueError('Content of given image could not be verified.')

        imgObj.seek(0)
        img = Image.open(imgObj)
        img.load()

        # Everything ok, convert PIL.Image to ROS and return it
        if img.mode == 'P':
            img = img.convert('RGB')

        rosimage = sensor_msgs.msg.Image()
        rosimage.encoding = ImageConverter._ENCODINGMAP_PY_TO_ROS[img.mode]
        (rosimage.width, rosimage.height) = img.size
        rosimage.step = (ImageConverter._PIL_MODE_CHANNELS[img.mode]
                         * rosimage.width)
        rosimage.data = img.tostring()
        return rosimage

    def encode(self, rosMsg):
        """ Convert a ROS compatible message (sensor_msgs.Image) to a
            PNG encoded image stored in a StringIO object.
        """
        if not isinstance(rosMsg, sensor_msgs.msg.Image):
            raise TypeError('Given object is not a sensor_msgs.msg.Image '
                            'instance.')

        # Convert to PIL Image
        pil = Image.fromstring(
                ImageConverter._ENCODINGMAP_ROS_TO_PY[rosMsg.encoding],
                (rosMsg.width, rosMsg.height),
                rosMsg.data,
                'raw',
                ImageConverter._ENCODINGMAP_ROS_TO_PY[rosMsg.encoding],
                0,
                1)

        # Save to StringIO
        img = StringIO()
        pil.save(img, 'PNG')
        return img

########NEW FILE########
__FILENAME__ = interfaces
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/util/converters/interfaces.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# zope specific imports
from zope.interface import Interface, Attribute


class ICustomROSConverter(Interface):
    """ Interface which declares the necessary methods which all ROS message
        types converters have to implement.
    """
    MESSAGE_TYPE = Attribute("""
    Identifier which is used to select the ROS converter.
    """)

    def encode(rosMsg): #@NoSelf
        """ Generate dictionary from a ROS message.

            @param rosMsg:  The ROS message instance which should be converted.
            @type  rosMsg:  genpy.message.Message

            @return:        Dictionary containing the parsed message. The basic
                            form does map each field in the ROS message to a
                            key / value pair in the returned data dict. Binaries
                            are added as StringIO instances.
            @rtype:         {}

            @raise:         TypeError, ValueError
        """

    def decode(data): #@NoSelf
        """ Generate a ROS message from dictionary.

            @param data:    Dictionary with keys matching the fields in the
                            desired ROS message.
                            Binary files should be included as StringIO
                            instances.
            @param data:    { str : {} }

            @return:        ROS message of type @param rosMsgType containing the
                            given data.
            @rtype:         ROS message of type @param rosMsgType

            @raise:         TypeError, ValueError,
                            rce.util.loader.ResourceNotFound
        """

########NEW FILE########
__FILENAME__ = cred
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/util/cred.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dhananjay Sathe
#
#

# Python specific imports
import os
import fileinput
import re
import base64
from hashlib import sha256
from Crypto.Cipher import AES
from collections import namedtuple

# zope specific imports
from zope.interface import implements

# twisted specific imports
from twisted.internet import defer
from twisted.python import failure
from twisted.cred import error
from twisted.cred.credentials import IUsernameHashedPassword
from twisted.cred.checkers import ICredentialsChecker

# rce specific imports
from rce.util.name import validateName, IllegalName


# AES Encryptors strength depends on input password length, ensure it with
# appropriate hash
# the block size for the cipher object; must be 32 for AES 256
_BLOCK_SIZE = 32

# the character used for padding
#   with a block cipher such as AES, the value you encrypt must be a multiple
#   of BLOCK_SIZE in length. This character is used to ensure that your value
#   is always a multiple of BLOCK_SIZE
_PADDING = '{'

# one-liner to sufficiently pad the text to be encrypted
pad = lambda s: s + (_BLOCK_SIZE - len(str(s)) % _BLOCK_SIZE) * _PADDING

# one-liners to encrypt/encode and decrypt/decode a string
# encrypt with AES, encode with base64
encodeAES = lambda c, s: base64.b64encode(c.encrypt(pad(s)))
cipher = lambda passwd: AES.new(passwd.decode('hex'))
salter = lambda u, p: sha256(u + p).hexdigest()

# one-liner to format user-info to write to the credentials file
formatUser = lambda name, pw, mode, groups: '\t'.join((name, pw, mode,
                                                       ':'.join(groups)))

# Cloud engine specific Types and Declarations
UserInfo = namedtuple('UserInfo', 'password mode groups')

# User mode mask length, modify these for future adaptations
_MODE_LENGTH = 1
_DEFAULT_USER_MODE = '1'  # should be as many digits as the above e.g.: 1, 01

# default groups a user belongs to
_DEFAULT_GROUPS = ('user',)

# Used Regex patterns
_RE = r'(\w+)\s([0-9a-fA-F]{64})\s(\d{' + str(_MODE_LENGTH) + '})\s([\w:]+)$'
_PASS_RE = r'^.*(?=.{4,20})(?=.*[a-z])(?=.*[A-Z])(?=.*[\d])(?=.*[\W]).*$'

# Used doc strings
_PASSWORD_FAIL = ('Password must be between 4-20 digits long and has to '
                  'contain at least one uppercase, lowercase, digit, and '
                  'special character. No whitespace allowed.')
_FIRST_RUN_MSG = ('It appears this is your first run or your credentials '
                  'database has changed or is incomplete. You must set the '
                  'passwords for the Admin and Admin-Infrastructure accounts.')
_NEW_PASS_PROMPT = ('\nNote: The password must be between 4-20 characters long '
                    'and contain no whitespace and at least one'
                    '\n\t* lowercase,'
                    '\n\t* uppercase,'
                    '\n\t* digit'
                    '\n\t* special character\n')


class CredentialError(Exception):
    """ Exception is raised if the CredChecker encountered an error.
    """


class RCECredChecker(object):
    """The RCE file-based, text-based username/password database.
    """
    implements(ICredentialsChecker)

    credentialInterfaces = (IUsernameHashedPassword,)

    cache = False
    _credCache = None
    _cacheTimestamp = 0

    def __init__(self, pw_file, provision=False):
        """ Initialize the credentials checker for the RoboEarth Cloud Engine.

            @param pw_file:     Path to the credentials database.
            @type  pw_file:     str

            @param provision:   Flag which is set if the database is going to
                                be provisioned.
            @type  provision:   bool
        """
        self.filename = pw_file
        self.scanner = re.compile(_RE)
        pass_re = re.compile(_PASS_RE)
        self.pass_validator = lambda x: True if pass_re.match(x) else False

        # Run some basic tests to check if the settings file is valid
        if self.filename is None:
            print('Settings variable PASSWORD_FILE not set')
            exit()

        if not os.access(os.path.dirname(self.filename), os.W_OK):
            print('The user lacks privileges to access/modify '
                  'the password file.')
            exit()

        if not provision:
            if not os.path.exists(self.filename):
                print('Credential file missing please run the provision script '
                      'first.')
                exit()

    def get_new_password(self, user):
        """ Method which is used to interactively get a new password from the
            user.

            @param user:        User ID of the user for which a new password
                                has to be entered.
            @type  user:        str

            @return:            The new password for the user.
            @rtype:             str
        """
        print (_NEW_PASS_PROMPT)
        msg_pw = "Enter a password for the user '{0}': ".format(user)
        msg_cf = "Please confirm the password for the user '{0}': ".format(user)

        while True:
            passwd = raw_input(msg_pw).strip()
            if passwd == raw_input(msg_cf).strip():
                if ' ' not in passwd and self.pass_validator(passwd):
                    return passwd
                else:
                    print('Password does not contain appropriate characters.')
            else:
                print('Passwords do not match.')

    def _cbPasswordMatch(self, matched, username):
        """ Internal method which is called in case the password could be
            successfully matched.
        """
        if matched:
            return username
        else:
            return failure.Failure(error.UnauthorizedLogin())

    def _loadCredentials(self):
        """ Internal method to read the credentials database.
        """
        with open(self.filename) as f:
            for line in f:
                try:
                    parts = self.scanner.match(line).groups()
                except AttributeError:
                    raise CredentialError('Credential database corrupted')
                try:
                    yield parts[0], UserInfo(parts[1], int(parts[2]),
                                             set(parts[3].split(':')))
                except KeyError:
                    raise CredentialError('Credential database corrupted')

    def getUser(self, username):
        """ Fetch username from db or cache. (Internal method)
        """
        if (self._credCache is None or
            os.path.getmtime(self.filename) > self._cacheTimestamp):
            self._cacheTimestamp = os.path.getmtime(self.filename)
            self._credCache = dict(self._loadCredentials())
        return self._credCache[username]

    def getUserMode(self, username):
        """ Fetch mode for a user.

            @param username:    username for who the mode is to be set.
            @type  username:    str

            @return:            Mode
            @rtype:             int
        """
        return self.getUser(username).mode

    def getUserGroups(self, username):
        """ Fetch groups for a user.

            @param username:    username for who the mode is to be set.
            @type  username:    str

            @return:            groups
            @rtype:             set
        """
        return self.getUser(username).groups

    def userMemebership(self, username, group):
        """ Test if a user is member of a certain group

            @param username:    username of the user
            @type  username:    str

            @param group:       group for which membership is to be tested
                                of the user
            @type  group:       str

            @return:            Result indicating membership
            @rtype:             bool
        """
        return group in self.getUserGroups(username)

    def requestAvatarId(self, c):
        try:
            passwd = self.getUser(c.username).password
        except KeyError:
            return defer.fail(error.UnauthorizedLogin())
        else:
            return defer.maybeDeferred(c.checkPassword, passwd
                        ).addCallback(self._cbPasswordMatch, c.username)

    def setUserMode(self, username, mode):
        """ Set the mode for a user

            Default mode for a user is 1. Like in Unix Admin mode is 0.
            The rest are open to custom extensions later in the engine.

            @param username:    username for who the mode is to be set.
            @type  username:    str

            @param mode:        Mode length is set by the _MODE_LENGTH [1]
                                parameter (1 for user; 0 for admin)
            @type  mode:        int

            @return:            Result of Operation
            @rtype:             bool
        """
        # mode sanity check and ensure only a single digit
        mode = str(mode)
        if len(mode) != _MODE_LENGTH:
            raise CredentialError('Invalid Mode Length')
        try:
            props = self.getUser(username)
        except KeyError:
            raise CredentialError('No such user')
        # Now process the file in the required mode
        for line in fileinput.input(self.filename, inplace=1):
                if  self.scanner.match(line).groups()[0] != username:
                    print(line[:-1])
                else:
                    print(formatUser(username, props.password, mode,
                                     props.groups))
        return True

    def addUserGroups(self, username, *groups):
        """ Add Group membership to certain groups.

            @param username:    username for who the mode is to be set.
            @type  username:    str

            @param groups:      groups membership to add to user
            @type  groups:      csv strings, e.g. group1,group2

            @return:            Result of Operation
            @rtype:             bool
        """
        # mode sanity check and ensure only a single digit
        try:
            props = self.getUser(username)
        except KeyError:
            raise CredentialError('No such user')
        groups = set(groups).union(props.groups)
        # Now process the file in the required mode
        for line in fileinput.input(self.filename, inplace=1):
                if  self.scanner.match(line).groups()[0] != username:
                    print(line[:-1])
                else:
                    print(formatUser(username, props.password, str(props.mode),
                                     groups))
        return True

    def removeUserGroups(self, username, *groups):
        """ Remove Group membership to certain groups.

            @param username:    username for who the mode is to be set.
            @type  username:    str

            @param groups:      groups membership to remove from the user
            @type  groups:      csv strings eg : group1,group2

            @return:            Result of Operation
            @rtype:             bool
        """
        # mode sanity check and ensure only a single digit
        try:
            props = self.getUser(username)
        except KeyError:
            raise CredentialError('No such user')
        groups = props.groups - set(groups)
        # Now process the file in the required mode
        for line in fileinput.input(self.filename, inplace=1):
                if  self.scanner.match(line).groups()[0] != username:
                    print(line[:-1])
                else:
                    print(formatUser(username, props.password, str(props.mode),
                                     groups))
        return True

    def addUser(self, username, password, provision=False):
        """ Change password for the username:

            @param username:    username
            @type  username:    str

            @param password:    password
            @type  password:    str

            @param provision:   Special flag to indicate provisioning mode
            @type  provision:   bool

            @return:            Result of Operation
            @rtype:             bool
        """
        try:
            validateName(username)
        except IllegalName as e:
            raise CredentialError(str(e))

        if not (self.pass_validator(password) or provision):
            raise CredentialError(_PASSWORD_FAIL)

        if provision:
            with open(self.filename, 'a') as f:
                f.write(formatUser(username, sha256(password).hexdigest(),
                                   _DEFAULT_USER_MODE, _DEFAULT_GROUPS))
                f.write('\n')
            return True

        try:
            self.getUser(username)
            raise CredentialError('Given user already exists')
        except KeyError:
            with open(self.filename, 'a') as f:
                f.write(formatUser(username, sha256(password).hexdigest(),
                                   _DEFAULT_USER_MODE, _DEFAULT_GROUPS))
                f.write('\n')
            return True

    def removeUser(self, username):
        """ Remove the given users

            @param username:    username
            @type  username:    str

            @return:            Result of Operation
            @rtype:             bool
        """
        try:
            self.getUser(username)
            for line in fileinput.input(self.filename, inplace=1):
                if self.scanner.match(line).groups()[0] != username:
                    print(line[:-1])
        except KeyError:
                raise CredentialError('No such user')

    def passwd(self, username, new_password, control_mode):
        """ Change password for the username.

            In admin mode you need to set the boolean indicating admin Mode.
            In case of a normal user you need to pass the old password for
            the user.

            Note : In admin mode, the admin is free to set any password he
                   likes as the strict password strength validation is turned
                   off in this case.

            @param username:        username
            @type  username:        str

            @param new_password:    new password
            @type  new_password:    str

            @param control_mode:    in user mode:  old password
                                    in admin mode: True
            @type  control_mode:    in user mode:  str
                                    in admin mode: bool

            @return:                Result of Operation
            @rtype:                 bool
        """
        try:
            props = self.getUser(username)
            if isinstance(control_mode, str):
                if props.password != sha256(control_mode).hexdigest():
                    raise CredentialError('Invalid Password')
                if not self.pass_validator(new_password):
                    raise CredentialError(_PASSWORD_FAIL)
        except KeyError:
            raise CredentialError('No such user')
        # Now process the file in the required mode
        for line in fileinput.input(self.filename, inplace=1):
            if  self.scanner.match(line).groups()[0] != username:
                print(line[:-1])
            else:
                print(formatUser(username, sha256(new_password).hexdigest(),
                                 str(props.mode), props.groups))
        return True


class RCEInternalChecker(object):
    """ RCE Internal Auth system
    """
    implements(ICredentialsChecker)

    def __init__(self, cred_checker):
        """
            @param cred_checker:    Cred Checker used to authenticate the cloud
                                    engine
            @type  cred_checker:    rce.util.cred.RCECredChecker
        """
        self._root_checker = cred_checker
        self.credentialInterfaces = (IUsernameHashedPassword,)

    def add_checker(self, method):
        """ Add a method to check the validity of a UUID.

            This method belongs to the RCE Realm Object, has access to the
            valid uuid and checks them, and raises a CredentialError if absent.
        """
        self.checkUidValidity = method

    def _cbPasswordMatch(self, matched, username):
        """ Internal method in case of success
        """
        if matched:
            return username
        else:
            return failure.Failure(error.UnauthorizedLogin())

    def requestAvatarId(self, c):
        try:
            if c.username in ('container', 'robot'):
                p = self._root_checker.getUser('adminInfra').password
                user = c.username
            else:  # it is the environment uuid
                try:
                    # this method is set by the real object instance
                    self.checkUidValidity(c.username)
                except CredentialError:
                    return defer.fail(error.UnauthorizedLogin())

                infra = self._root_checker.getUser('adminInfra').password
                main = self._root_checker.getUser('admin').password
                p = encodeAES(cipher(main), salter(c.username, infra))
                user = 'environment'
        except KeyError:
            return defer.fail(error.UnauthorizedLogin())
        else:
            return defer.maybeDeferred(c.checkPassword, p
                        ).addCallback(self._cbPasswordMatch, user)


########NEW FILE########
__FILENAME__ = error
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       rce-core/rce/error.py
#
#       This file is part of the RoboEarth Cloud Engine framework.
#
#       This file was originally created for RoboEearth
#       http://www.roboearth.org/
#
#       The research leading to these results has received funding from
#       the European Union Seventh Framework Programme FP7/2007-2013 under
#       grant agreement no248942 RoboEarth.
#
#       Copyright 2012 RoboEarth
#
#       Licensed under the Apache License, Version 2.0 (the "License");
#       you may not use this file except in compliance with the License.
#       You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#       Unless required by applicable law or agreed to in writing, software
#       distributed under the License is distributed on an "AS IS" BASIS,
#       WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#       See the License for the specific language governing permissions and
#       limitations under the License.
#
#       \author/s: Dominique Hunziker
#
#

# twisted specific imports
from twisted.spread.pb import Error


class InternalError(Error):
    """ This class is used to signal an internal error.
    """

########NEW FILE########
__FILENAME__ = iaas
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/util/iaas.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# TODO: This needs some work on specification:
#        - define interface
#        - create a class for each IAAS type implementing interface
class IaasHook(object):
    """ # TODO: Add doc
    """
    def disconnect(self):
        """ Method is called when shutting down the engine to relieve the hook.
        """
        # TODO: Should destroy all instances which have been started dynamically
        raise NotImplementedError

    def spin_up(self, count=1, type=None, specialRequest=None):
        """ Call to spin up more instances.

            @param count:           Number of instances to be spun up.
            @type  count:           int

            @param type:            Type (generally size) of instance requested
            @type  type:            TDB by implementation

            @param specialRequest:  Special request (gpu, cluster, hadoop)
            @type  specialRequest:  TDB by implementation
        """
        raise NotImplementedError

    def spin_down(self):
        """ # TODO: ???
        """
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = name
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/util/name.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import re

# twisted specific imports
from twisted.spread.pb import Error


# ASCII char followed by (alphanumeric, _)
_NAME_RE = re.compile('^[A-Za-z][\w_]*$')


class IllegalName(Error):
    """ Exception is raised in case the name is not legal.
    """


def validateName(name):
    """ Check if the name is legal, i.e. if it starts with an ASCII char
        followed by alphanumeric chars or '_'.

        @param name:    Name which should be checked.
        @type  name:    str

        @raise:         IllegalName, if the name is not valid.
    """
    if not name:
        raise IllegalName('Name can not be an empty string.')

    m = _NAME_RE.match(name)

    if m is None or m.group(0) != name:
        raise IllegalName('Name has to start with a letter followed by an '
                          'arbitrary number of alphanumeric characters or '
                          'underscores.')

########NEW FILE########
__FILENAME__ = network
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/util/network.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# rce specific imports
from rce.util.settings import getSettings
settings = getSettings()


def isLocalhost(ip):
    """ Check if the IP address matches the loopback address.

        @param ip:          IP address which should be checked
        @type  ip:          str

        @return:            True if the address is the loopback address;
                            False otherwise.
        @rtype:             bool
    """
    return ip in (settings.localhost_IP, 'localhost')

########NEW FILE########
__FILENAME__ = process
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/util/process.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

from twisted.python.failure import Failure
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ProcessProtocol


class ExecutionError(Exception):
    """ Exception is raised in case the command could not be executed.
    """


class _ProcessProtocol(ProcessProtocol):
    """ Protocol used to retrieve the exit code of a child process.
    """
    def __init__(self, cmd, deferred):
        """ Initialize the ProcessProtocol which is used in the function
            'execute'.

            @param cmd:         Command which has been executed.
            @type  cmd:         str

            @param deferred:    Deferred which will be used to report the
                                return value of the command.
            @type  deferred:    twisted.internet.defer.Deferred
        """
        self.cmd = cmd
        self.deferred = deferred

    def processEnded(self, reason):
        """ Method is called by the twisted framework once the child process has
            terminated.
        """
        if reason.value.exitCode == 0:
            self.deferred.callback("Command '{0}' successfully "
                                   'executed.'.format(self.cmd))
        else:
            e = ExecutionError("Execution of '{0}' failed: "
                               'Received exit code '
                               '{1}.'.format(self.cmd, reason.value.exitCode))
            self.deferred.errback(Failure(e))


def execute(cmd, env=None, path=None, reactor=None):
    """ Execute a command using twisted's Process Protocol and returns a
        Deferred firing when the command as terminated.

        @param cmd:         Command which should be executed. It has to be a
                            tuple containing the executable as first argument
                            and all additional arguments which will be passed
                            to the executable.
        @type  cmd:         tuple

        @param env:         Can be used to use custom environment variables to
                            execute the command. If argument is omitted the
                            environment of os.environ is used.
        @type  env:         dict

        @param path:        Path which will be used as working directory to
                            execute the command. If argument is omitted the
                            current directory is used.
        @type  path:        str

        @param reactor:     Reference to twisted's reactor. If argument is
                            omitted the standard twisted reactor is imported and
                            used.
        @type  reactor:     twisted::reactor
    """
    deferred = Deferred()
    protocol = _ProcessProtocol(' '.join(cmd), deferred)

    try:
        reactor.spawnProcess(protocol, cmd[0], cmd, env, path)
    except OSError:
        e = ExecutionError('Command could not be executed.')
        deferred.errback(Failure(e))

    return deferred

########NEW FILE########
__FILENAME__ = settings
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/util/settings.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dhananjay Sathe, Dominique Hunziker
#
#

# Python specific imports
import os
import string
import socket
import fcntl
import struct
import re
import urllib2
from ConfigParser import SafeConfigParser, Error

# rce specific imports
from rce.util.name import validateName, IllegalName


# Global storage of config parser
_settings = None

# Path where the configuration file can be found
PATH = os.path.join(os.getenv('HOME'), '.rce', 'config.ini')


def get_host_ubuntu_release():
    """ Parse configuration file to get the codename of the Ubuntu release of
        the host filesystem.
    """
    with open('/etc/lsb-release') as config:
        for line in config:
            k, v = line.split('=')

            if k == 'DISTRIB_CODENAME':
                return v.strip(string.whitespace + '\'"')

    raise ValueError('Corrupt release information.')


class NoValidSettings(Exception):
    """ Exception is raised in case there is no valid configuration found
        for the cloud engine.
    """


def getSettings(throw=False, checks=True):
    """ Get the cloud engine settings.
        The configuration file is parsed only once and cached for later.

        @raise:                 rce.util.settings.NoValidSettings
    """
    global _settings

    if not _settings:
        try:
            _settings = _getSettings(checks)
        except NoValidSettings as e:
            _settings = e

    if isinstance(_settings, NoValidSettings):
        if throw:
            raise _settings
        else:
            print(str(e))
            print('Please check your configuration.')
            exit(1)

    return _settings


def _getSettings(checks):
    """ Get the settings for the cloud engine. Does the heavy lifting.
    """
    parser = _RCESettingsParser()

    if PATH not in parser.read(PATH):
        raise NoValidSettings('Config file is missing.')

    try:
        return _Settings.load(parser, checks)
    except (Error, ValueError) as e:
        raise NoValidSettings(str(e))


def _path_exists(path, description):
    """ Check if the path is valid and exists.

        @param path:            Path which should be checked.
        @type  path:            str

        @param description:     Description which is used for the error
                                message if necessary.
        @type  description:     str

        @raise:                 ValueError, if path is not valid.
    """
    if not os.path.isabs(path):
        raise ValueError('{0} is not an absolute path.'.format(description))

    if not os.path.exists(path):
        raise ValueError('{0} does not exist: {1}'.format(description, path))


def _valid_dir(path, description):
    """ Check if the path is a valid directory.

        @param path:            Path which should be checked.
        @type  path:            str

        @param description:     Description which is used for the error
                                message if necessary.
        @type  description:     str

        @raise:                 ValueError, if path is not valid.
    """
    _path_exists(path, description)

    if not os.path.isdir(path):
        raise ValueError('{0} is not directory.'.format(description))


def _getIP(ifname):
    """ Get the IP address associated with a network interface.

        Based on:
            http://code.activestate.com/recipes/439094-get-the-ip-address-
            associated-with-a-network-inter/

            PSF License (Python Software Foundation)

        @param ifname:          The name of the network interface for which the
                                IP address should be retrieved.
        @type  finame:          str

        @return:                IP address as a string, i.e. x.x.x.x
        @rtype:                 str
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', ifname[:15])
        )[20:24])
    except IOError:
        raise ValueError("Either the interface '{0}' isn't connected or there "
                         "seems to be a network error".format(ifname))


class _Settings(object):
    """ Class contains all settings variables.
    """
    def __init__(self):
        """ Initialize the variables with None. To load the Settings use the
            classmethod 'load'.
        """
        # Global
        self._gzip_lvl = None
        self._dev_mode = None
        self._pw_file = None
        self._host_ubuntu = None
        self._host_ros = None
        self._container_ubuntu = None
        self._container_ros = None

        # Network
        self._container_if = None
        self._external_ip = None
        self._internal_ip = None
        self._container_ip = None
        self._localhost_ip = None

        # Comm
        self._http_port = None
        self._ws_port = None
        self._internal_port = None
        self._external_port = None
        self._comm_port = None
        self._ros_proxy_port = None

        # Converters
        self._converters = None

        # Machine
        self._size = None
        self._cpu = None
        self._memory = None
        self._bandwidth = None
        self._special_features = None
        self._rootfs = None
        self._conf_dir = None
        self._data_dir = None
        self._packages = None

    @property
    def gzip_lvl(self):
        """ Compression level used in ROS message forwarder. """
        return self._gzip_lvl

    @property
    def dev_mode(self):
        """ Flag which is True if the cloud engine runs in developer mode. """
        return self._dev_mode

    @property
    def pw_file(self):
        """ Path to the credentials database. """
        return self._pw_file

    @property
    def host_ubuntu_release(self):
        """ Ubuntu release used in the host filesystem. """
        return self._host_ubuntu

    @property
    def host_ros_release(self):
        """ ROS release used in the host filesystem. """
        return self._host_ros

    @property
    def container_ubuntu_release(self):
        """ Ubuntu release used inside the container. """
        return self._container_ubuntu

    @property
    def container_ros_release(self):
        """ ROS release used inside the container. """
        return self._container_ros

    @property
    def container_interface(self):
        """ Name of the container network interface. """
        return self._container_if

    @property
    def external_IP(self):
        """ IP address of network interface used for external communication. """
        return self._external_ip

    @property
    def internal_IP(self):
        """ IP address of network interface used for internal communication. """
        return self._internal_ip

    @property
    def container_IP(self):
        """ IP address of network interface used for communication with
            containers.
        """
        return self._container_ip

    @property
    def localhost_IP(self):
        """ IP address of loopback network interface. """
        return self._localhost_ip

    @property
    def http_port(self):
        """ Port on which the Master process is listening for HTTP requests
            from the cloud engine clients.
        """
        return self._http_port

    @property
    def ws_port(self):
        """ Port on which the Robot processes are listening for WebSocket
            connections from the cloud engine clients.
        """
        return self._ws_port

    @property
    def external_port(self):
        """ Port on which the Master process is listening for external
            PerspectiveBroker connections.
        """
        return self._external_port

    @property
    def internal_port(self):
        """ Port on which the Master process is listening for cloud engine
            internal PerspectiveBroker connections.
        """
        return self._internal_port

    @property
    def comm_port(self):
        """ Port on which the Endpoint processes are listening for cloud engine
            internal data protocol connections.
        """
        return self._comm_port

    @property
    def ros_proxy_port(self):
        """ Port on which the ROS proxy processes are listening for HTTP
            requests from the cloud engine clients.
        """
        return self._ros_proxy_port

    @property
    def converters(self):
        """ List of custom message converters which are used in the Robot
            processes.
        """
        return self._converters

    @property
    def size(self):
        """ Maximum number of containers which can run in the machine. """
        return self._size

    @property
    def cpu(self):
        """ Parameter to define CPU attributes/capacity. """
        return self._cpu

    @property
    def memory(self):
        """ Parameter to define memory attributes/capacity. """
        return self._memory

    @property
    def bandwidth(self):
        """ Parameter to define bandwidth attributes/capacity. """
        return self._bandwidth

    @property
    def special_features(self):
        """ Parameter to define special attributes like avx,gpu,hadoop, etc. """
        return self._special_features

    @property
    def rootfs(self):
        """ Path to the root directory of the container filesystem. """
        return self._rootfs

    @property
    def conf_dir(self):
        """ Path to the directory in which temporary configuration files for
            the containers are stored.
        """
        return self._conf_dir

    @property
    def data_dir(self):
        """ Path to the directory in which temporary data files for the
            containers are stored.
        """
        return self._data_dir

    @property
    def packages(self):
        """ List of custom ROS packages which are mounted using bind into the
            container filesystem. Each element is a tuple containing the
            path to the directory of the ROS package in the host filesystem as
            well as the path to the directory of the ROS package in the
            container filesystem.
        """
        return self._packages

    @classmethod
    def load(cls, parser, checks):
        """ Factory method which creates a new Settings object using the
            provided cloud engine settings parser.

            @param parser:      Cloud engine settings parser which is used to
                                parse the configuration file.
            @type  parser:      rce.util.settings._RCESettingsParser

            @param checks:      Enable/Disable path checks.
            @type  checks:      bool

            @return:            New _Settings instance containing the parsed
                                settings.
            @rtype:             rce.util.settings._Settings
        """
        settings = cls()

        # Global
        settings._gzip_lvl = parser.getint('global', 'gzip_lvl')
        settings._dev_mode = parser.getboolean('global', 'dev_mode')
        settings._pw_file = parser.get('global', 'password_file')
        settings._host_ubuntu = get_host_ubuntu_release()
        settings._host_ros = parser.get('global', 'host_ros_release')
        settings._container_ros = parser.get('global', 'container_ros_release')
        settings._container_ubuntu = parser.get('global',
                                                'container_ubuntu_release')

        # Network
        settings._container_if = parser.get('network', 'container_if')
        settings._external_ip = parser.getIP('network', 'external_if')
        settings._internal_ip = parser.getIP('network', 'internal_if')
        settings._container_ip = parser.getIP('network', 'container_if')
        settings._localhost_ip = _getIP('lo')

        # Comm
        settings._http_port = parser.getint('comm', 'http_port')
        settings._ws_port = parser.getint('comm', 'ws_port')
        settings._internal_port = parser.getint('comm', 'internal_port')
        settings._external_port = parser.getint('comm', 'external_port')
        settings._comm_port = parser.getint('comm', 'comm_port')
        settings._ros_proxy_port = parser.getint('comm', 'ros_proxy_port')

        # Converters
        settings._converters = tuple(c for _, c in parser.items('converters'))

        # Machine
        settings._size = parser.getint('machine', 'size')
        settings._cpu = parser.getint('machine', 'cpu')
        settings._memory = parser.getint('machine', 'memory')
        settings._bandwidth = parser.getint('machine', 'bandwidth')
        settings._rootfs = parser.get('machine', 'rootfs')
        settings._conf_dir = parser.get('machine', 'conf_dir')
        settings._data_dir = parser.get('machine', 'data_dir')
        # Figure out the special features
        special_features = parser.get('machine', 'special_features')
        settings._special_features = [i.strip() for i in
                                      special_features.strip('[]').split(',')]

        # ROS packages
        settings._packages = []
        usedNames = set()

        if checks:
            for name, path in parser.items('machine/packages'):
                _valid_dir(path, "ROS package '{0}'".format(name))

                try:
                    validateName(name)
                except IllegalName:
                    raise ValueError("Package name '{0}' is not a legal "
                                     'name.'.format(name))

                if name in usedNames:
                    raise ValueError("Package name '{0}' is not "
                                     'unique.'.format(name))

                usedNames.add(name)

                settings._packages.append((path,
                                           os.path.join('opt/rce/packages', name)))

            settings._packages = tuple(settings._packages)

            # Validate paths
            _valid_dir(settings._rootfs, 'Container file system')
            _valid_dir(settings._conf_dir, 'Configuration directory')
            _valid_dir(settings._data_dir, 'Data directory')

        return settings


class _RCESettingsParser(SafeConfigParser, object):
    """ Configuration parser used for the cloud engine settings.
    """
    # case where in a custom setup the global IP address is preconfigured
    # and does not necessarily bind to a network interface
    # e.g.: ElasticIP or custom DNS routings
    _IP_V4_REGEX = re.compile('^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.)'
                              '{3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')

    # Internal AWS url metadata retrieval address for type 'public-ipv4'
    _AWS_IP_V4_ADDR = 'http://169.254.169.254/latest/meta-data/public-ipv4'

    def __init__(self, *args, **kwargs):
        super(_RCESettingsParser, self).__init__(*args, **kwargs)
        self._get_iface_list()

    def _get_iface_list(self):
        self._ifaces = set()
        with open('/proc/net/dev') as net_devices:
            for line in net_devices.readlines()[2:]:
                self._ifaces.add(line.split(':')[0].strip())

    def getIP(self, section, option):
        """ Get IP address.

            @param section:     Section from which the option should be
                                retrieved.
            @type  section:     str

            @param option:      Option which should be parsed for an IP address.
            @type  option:      str

            @return:            IP address as a string, i.e. x.x.x.x
            @rtype:             str
        """
        ifname = self.get(section, option)

        if _RCESettingsParser._IP_V4_REGEX.match(ifname):
            return ifname

        # AWS Specific IP resolution method for the global ipv4 address
        try:
            if ifname == 'aws_dns':
                return urllib2.urlopen(_RCESettingsParser._AWS_IP_V4_ADDR,
                                       timeout=3).read()
        except urllib2.URLError:
            raise NoValidSettings('There seems to be something wrong with '
                                  'AWS or configuration settings.')

        if ifname not in self._ifaces:
            raise NoValidSettings("The network device '{0}' does not exist on "
                                  'your system check your '
                                  'configuration.'.format(ifname))

        return _getIP(ifname)

########NEW FILE########
__FILENAME__ = sysinfo
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-core/rce/util/sysinfo.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     Adapted from the psutil package and rewritten in pure Python with
#     relevant required functions. psutil is licensed under the BSD license
#
#         Copyright (c) 2009, Jay Loden, Dave Daeschler, Giampaolo Rodola
#         https://code.google.com/p/psutil/
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dhananjay Sathe : dhananjaysathe@gmail.com
#                Giampaolo Rodola : g.rodola@gmail.com
#

import os
import errno
import socket
import struct
import sys
import base64
import glob
import re
import stat
import time

from collections import namedtuple, defaultdict

# Necessary Object Declarations

class NoSuchProcess(Exception):
    """Exception raised when a process with a certain PID doesn't
    or no longer exists (zombie).
    """

    def __init__(self, pid, name=None, msg=None):
        self.pid = pid
        self.name = name
        self.msg = msg
        if msg is None:
            if name:
                details = "(pid=%s, name=%s)" % (self.pid, repr(self.name))
            else:
                details = "(pid=%s)" % self.pid
            self.msg = "process no longer exists " + details

    def __str__(self):
        return self.msg

class AccessDenied(Exception):
    """Exception raised when permission to perform an action is denied."""

    def __init__(self, pid=None, name=None, msg=None):
        self.pid = pid
        self.name = name
        self.msg = msg
        if msg is None:
            if (pid is not None) and (name is not None):
                self.msg = "(pid=%s, name=%s)" % (pid, repr(name))
            elif (pid is not None):
                self.msg = "(pid=%s)" % self.pid
            else:
                self.msg = ""

    def __str__(self):
        return self.msg


class constant(int):
    """A constant type; overrides base int to provide a useful name on str()."""

    def __new__(cls, value, name, doc=None):
        inst = super(constant, cls).__new__(cls, value)
        inst._name = name
        if doc is not None:
            inst.__doc__ = doc
        return inst

    def __str__(self):
        return self._name

    def __eq__(self, other):
        # Use both int or str values when comparing for equality
        # (useful for serialization):
        # >>> st = constant(0, "running")
        # >>> st == 0
        # True
        # >>> st == 'running'
        # True
        if isinstance(other, int):
            return int(self) == other
        if isinstance(other, long):
            return long(self) == other
        if isinstance(other, str):
            return self._name == other
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

# Convenience functions

def _get_boot_time():
    """Return system boot time (epoch in seconds)"""
    f = open('/proc/stat', 'r')
    try:
        for line in f:
            if line.startswith('btime'):
                return float(line.strip().split()[1])
        raise RuntimeError("line not found")
    finally:
        f.close()


def _get_sys_totalmem():
    f = open('/proc/meminfo', 'r')
    total = None
    try:
        for line in f:
            if line.startswith('MemTotal:'):
                total = int(line.split()[1]) * 1024

            if  total is not None :
                break
        else:
            raise RuntimeError("line(s) not found")
    finally:
        f.close()
    return total


def _get_terminal_map():
    ret = {}
    ls = glob.glob('/dev/tty*') + glob.glob('/dev/pts/*')
    for name in ls:
        assert name not in ret
        ret[os.stat(name).st_rdev] = name
    return ret

_pmap = {}


def get_pid_list():
    """Returns a list of PIDs currently running on the system."""
    pids = [int(x) for x in os.listdir('/proc') if x.isdigit()]
    return pids


def pid_exists(pid):
    """Check whether pid exists in the current process table."""
    if not isinstance(pid, int):
        raise TypeError('an integer is required')
    if pid < 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        e = sys.exc_info()[1]
        return e.errno == errno.EPERM
    else:
        return True


def process_iter():
    """Return a generator yielding a Process class instance for all
    running processes on the local machine.

    Every new Process instance is only created once and then cached
    into an internal table which is updated every time this is used.

    The sorting order in which processes are yielded is based on
    their PIDs.
    """
    def add(pid):
        proc = Process(pid)
        _pmap[proc.pid] = proc
        return proc

    def remove(pid):
        _pmap.pop(pid, None)

    a = set(get_pid_list())
    b = set(_pmap.keys())
    new_pids = a - b
    gone_pids = b - a

    for pid in gone_pids:
        remove(pid)
    for pid, proc in sorted(list(_pmap.items()) + \
                            list(dict.fromkeys(new_pids).items())):
        try:
            if proc is None:  # new process
                yield add(pid)
            else:
                # use is_running() to check whether PID has been reused by
                # another process in which case yield a new Process instance
                if proc.is_running():
                    yield proc
                else:
                    yield add(pid)
        except NoSuchProcess:
            remove(pid)
        except AccessDenied:
            # Process creation time can't be determined hence there's
            # no way to tell whether the pid of the cached process
            # has been reused. Just return the cached version.
            yield proc


def _get_num_cpus():
    """Return the number of CPUs on the system"""
    # we try to determine num CPUs by using different approaches.
    # SC_NPROCESSORS_ONLN seems to be the safer and it is also
    # used by multiprocessing module
    try:
        return os.sysconf("SC_NPROCESSORS_ONLN")
    except ValueError:
        # as a second fallback we try to parse /proc/cpuinfo
        num = 0
        f = open('/proc/cpuinfo', 'r')
        try:
            lines = f.readlines()
        finally:
            f.close()
        for line in lines:
            if line.lower().startswith('processor'):
                num += 1

    # unknown format (e.g. amrel/sparc architectures), see:
    # http://code.google.com/p/psutil/issues/detail?id=200
    # try to parse /proc/stat as a last resort
    if num == 0:
        f = open('/proc/stat', 'r')
        try:
            lines = f.readlines()
        finally:
            f.close()
        search = re.compile('cpu\d')
        for line in lines:
            line = line.split(' ')[0]
            if search.match(line):
                num += 1

    if num == 0:
        raise RuntimeError("can't determine number of CPUs")
    return num


def isfile_strict(path):
    """Same as os.path.isfile() but does not swallow EACCES / EPERM
    exceptions, see:
    http://mail.python.org/pipermail/python-dev/2012-June/120787.html
    """
    try:
        st = os.stat(path)
    except OSError:
        err = sys.exc_info()[1]
        if err.errno in (errno.EPERM, errno.EACCES):
            raise
        return False
    else:
        return stat.S_ISREG(st.st_mode)


# --- decorators

def wrap_exceptions(callable):
    """Call callable into a try/except clause and translate ENOENT,
    EACCES and EPERM in NoSuchProcess or AccessDenied exceptions.
    """
    def wrapper(self, *args, **kwargs):
        try:
            return callable(self, *args, **kwargs)
        except EnvironmentError:
            # ENOENT (no such file or directory) gets raised on open().
            # ESRCH (no such process) can get raised on read() if
            # process is gone in meantime.
            err = sys.exc_info()[1]
            if err.errno in (errno.ENOENT, errno.ESRCH):
                raise NoSuchProcess(self.pid, self._process_name)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(self.pid, self._process_name)
            raise
    return wrapper


# DECLARATIONS AND CONSTANTS

_CLOCK_TICKS = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
_PAGESIZE = os.sysconf("SC_PAGE_SIZE")
BOOT_TIME = _get_boot_time()
NUM_CPUS = _get_num_cpus()
TOTAL_PHYMEM = _get_sys_totalmem()

# --- constants

STATUS_RUNNING = constant(0, "running")
STATUS_SLEEPING = constant(1, "sleeping")
STATUS_DISK_SLEEP = constant(2, "disk sleep")
STATUS_STOPPED = constant(3, "stopped")
STATUS_TRACING_STOP = constant(4, "tracing stop")
STATUS_ZOMBIE = constant(5, "zombie")
STATUS_DEAD = constant(6, "dead")
STATUS_WAKE_KILL = constant(7, "wake kill")
STATUS_WAKING = constant(8, "waking")

# taken from /fs/proc/array.c
_status_map = {"R" : STATUS_RUNNING,
               "S" : STATUS_SLEEPING,
               "D" : STATUS_DISK_SLEEP,
               "T" : STATUS_STOPPED,
               "t" : STATUS_TRACING_STOP,
               "Z" : STATUS_ZOMBIE,
               "X" : STATUS_DEAD,
               "x" : STATUS_DEAD,
               "K" : STATUS_WAKE_KILL,
               "W" : STATUS_WAKING}


# http://students.mimuw.edu.pl/lxr/source/include/net/tcp_states.h
_TCP_STATES_TABLE = {"01" : "ESTABLISHED",
                     "02" : "SYN_SENT",
                     "03" : "SYN_RECV",
                     "04" : "FIN_WAIT1",
                     "05" : "FIN_WAIT2",
                     "06" : "TIME_WAIT",
                     "07" : "CLOSE",
                     "08" : "CLOSE_WAIT",
                     "09" : "LAST_ACK",
                     "0A" : "LISTEN",
                     "0B" : "CLOSING"
                     }

# named tuples for system functions
nt_sys_cputimes = namedtuple('cputimes', 'user nice system idle iowait irq softirq')
nt_virtmem_info = namedtuple('vmem', ' '.join([
    'total', 'available', 'percent', 'used', 'free',
    'active', 'inactive', 'buffers', 'cached']))
nt_net_iostat = namedtuple('iostat',
    'bytes_sent bytes_recv packets_sent packets_recv errin errout dropin dropout')
nt_disk_iostat = namedtuple('iostat', 'read_count write_count read_bytes write_bytes read_time write_time')


# named tuples for processes
nt_io = namedtuple('io', 'read_count write_count read_bytes write_bytes')
nt_cputimes = namedtuple('cputimes', 'user system')
nt_meminfo = namedtuple('meminfo', 'rss vms')
nt_ctxsw = namedtuple('amount', 'voluntary involuntary')
nt_thread = namedtuple('thread', 'id user_time system_time')
nt_openfile = namedtuple('openfile', 'path fd')
nt_connection = namedtuple('connection', 'fd family type local_address remote_address status')
nt_uids = namedtuple('user', 'real effective saved')
nt_gids = namedtuple('group', 'real effective saved')


# SYSTEM FUNCTIONS

# System - CPU

def _get_sys_cpu_times():
    """Return a named tuple representing the following CPU times:
    user, nice, system, idle, iowait, irq, softirq.
    """
    f = open('/proc/stat', 'r')
    try:
        values = f.readline().split()
    finally:
        f.close()

    values = values[1:8]
    values = tuple([float(x) / _CLOCK_TICKS for x in values])
    return nt_sys_cputimes(*values[:7])


def _get_sys_per_cpu_times():
    """Return a list of namedtuple representing the CPU times
    for every CPU available on the system.
    """
    cpus = []
    f = open('/proc/stat', 'r')
    # get rid of the first line who refers to system wide CPU stats
    try:
        f.readline()
        for line in f.readlines():
            if line.startswith('cpu'):
                values = line.split()[1:8]
                values = tuple([float(x) / _CLOCK_TICKS for x in values])
                entry = nt_sys_cputimes(*values[:7])
                cpus.append(entry)
        return cpus
    finally:
        f.close()

# top level wrapper functions for cpu
def cpu_times(percpu=False):
    """Return system-wide CPU times as a namedtuple object.
    Every CPU time represents the time CPU has spent in the given mode.
    The attributes availability varies depending on the platform.
    Here follows a list of all available attributes:
     - user
     - system
     - idle
     - nice (UNIX)
     - iowait (Linux)
     - irq (Linux, FreeBSD)
     - softirq (Linux)

    When percpu is True return a list of nameduples for each CPU.
    First element of the list refers to first CPU, second element
    to second CPU and so on.
    The order of the list is consistent across calls.
    """
    if not percpu:
        return _get_sys_cpu_times()
    else:
        return _get_sys_per_cpu_times()


_last_cpu_times = cpu_times()
_last_per_cpu_times = cpu_times(percpu=True)

def cpu_percent(interval=0.1, percpu=False):
    """Return a float representing the current system-wide CPU
    utilization as a percentage.

    When interval is > 0.0 compares system CPU times elapsed before
    and after the interval (blocking).

    When interval is 0.0 or None compares system CPU times elapsed
    since last call or module import, returning immediately.
    In this case is recommended for accuracy that this function be
    called with at least 0.1 seconds between calls.

    When percpu is True returns a list of floats representing the
    utilization as a percentage for each CPU.
    First element of the list refers to first CPU, second element
    to second CPU and so on.
    The order of the list is consistent across calls.
    """
    global _last_cpu_times
    global _last_per_cpu_times
    blocking = interval is not None and interval > 0.0

    def calculate(t1, t2):
        t1_all = sum(t1)
        t1_busy = t1_all - t1.idle

        t2_all = sum(t2)
        t2_busy = t2_all - t2.idle

        # this usually indicates a float precision issue
        if t2_busy <= t1_busy:
            return 0.0

        busy_delta = t2_busy - t1_busy
        all_delta = t2_all - t1_all
        busy_perc = (busy_delta / all_delta) * 100
        return round(busy_perc, 1)

    # system-wide usage
    if not percpu:
        if blocking:
            t1 = cpu_times()
            time.sleep(interval)
        else:
            t1 = _last_cpu_times
        _last_cpu_times = cpu_times()
        return calculate(t1, _last_cpu_times)
    # per-cpu usage
    else:
        ret = []
        if blocking:
            tot1 = cpu_times(percpu=True)
            time.sleep(interval)
        else:
            tot1 = _last_per_cpu_times
        _last_per_cpu_times = cpu_times(percpu=True)
        for t1, t2 in zip(tot1, _last_per_cpu_times):
            ret.append(calculate(t1, t2))
        return ret


# System - Memory

def usage_percent(used, total, _round=None):
    """Calculate percentage usage of 'used' against 'total'."""
    try:
        ret = (used / total) * 100
    except ZeroDivisionError:
        ret = 0
    if _round is not None:
        return round(ret, _round)
    else:
        return ret


def get_sys_meminfo():
    f = open('/proc/meminfo', 'r')
    total = free = buffers = cached = active = inactive = None
    try:
        for line in f:
            if line.startswith('MemTotal:'):
                total = int(line.split()[1]) * 1024
            elif line.startswith('MemFree:'):
                free = int(line.split()[1]) * 1024
            elif line.startswith('Buffers:'):
                buffers = int(line.split()[1]) * 1024
            elif line.startswith('Cached:'):
                cached = int(line.split()[1]) * 1024
            elif line.startswith('Active:'):
                active = int(line.split()[1]) * 1024
            elif line.startswith('Inactive:'):
                inactive = int(line.split()[1]) * 1024
            if  total is not None \
            and free is not None \
            and buffers is not None \
            and cached is not None \
            and active is not None \
            and inactive is not None:
                break
        else:
            raise RuntimeError("line(s) not found")
    finally:
        f.close()
    avail = free + buffers + cached
    used = total - free
    percent = usage_percent((total - avail), total, _round=1)
    return nt_virtmem_info(total, avail, percent, used, free,
                           active, inactive, buffers, cached)


# System - Network

def network_io_counters():
    """Return network I/O statistics for every network interface
    installed on the system as a dict of raw tuples.
    """
    f = open("/proc/net/dev", "r")
    try:
        lines = f.readlines()
    finally:
        f.close()

    retdict = dict()
    for line in lines[2:]:
        colon = line.find(':')
        assert colon > 0, line
        name = line[:colon].strip()
        fields = line[colon + 1:].strip().split()
        bytes_recv = int(fields[0])
        packets_recv = int(fields[1])
        errin = int(fields[2])
        dropin = int(fields[2])
        bytes_sent = int(fields[8])
        packets_sent = int(fields[9])
        errout = int(fields[10])
        dropout = int(fields[11])
        retdict[name] = nt_net_iostat(bytes_sent, bytes_recv, packets_sent, packets_recv,
                         errin, errout, dropin, dropout)
    return retdict


# System disk

def disk_io_counters():
    """Return disk I/O statistics for every disk installed on the
    system as a dict of raw tuples.
    """
    # man iostat states that sectors are equivalent with blocks and
    # have a size of 512 bytes since 2.4 kernels. This value is
    # needed to calculate the amount of disk I/O in bytes.
    SECTOR_SIZE = 512

    # determine partitions we want to look for
    partitions = []
    f = open("/proc/partitions", "r")
    try:
        lines = f.readlines()[2:]
    finally:
        f.close()
    for line in lines:
        _, _, _, name = line.split()
        if name[-1].isdigit():
            partitions.append(name)
    #
    retdict = {}
    f = open("/proc/diskstats", "r")
    try:
        lines = f.readlines()
    finally:
        f.close()
    for line in lines:
        _, _, name, reads, _, rbytes, rtime, writes, _, wbytes, wtime = \
            line.split()[:11]
        if name in partitions:
            rbytes = int(rbytes) * SECTOR_SIZE
            wbytes = int(wbytes) * SECTOR_SIZE
            reads = int(reads)
            writes = int(writes)
            rtime = int(rtime)
            wtime = int(wtime)
            retdict[name] = nt_disk_iostat(reads, writes, rbytes, wbytes, rtime, wtime)
    return retdict


# Representation and methods for a process

class Process(object):
    """Linux process implementation."""

    __slots__ = ["pid", "_process_name", "_last_sys_cpu_times",
                 "_last_proc_cpu_times", "_gone", "create_time",
                 "ppid"]

    def __init__(self, pid):
        if not isinstance(pid, int):
            raise TypeError('pid must be an integer')
        self.pid = pid
        self._process_name = None
        self._last_sys_cpu_times = None
        self._last_proc_cpu_times = None
        self._gone = False
        self.create_time = self.get_process_create_time()
        self.ppid = self.get_process_ppid()

    @wrap_exceptions
    def get_process_name(self):
        f = open("/proc/%s/stat" % self.pid)
        try:
            name = f.read().split(' ')[1].replace('(', '').replace(')', '')
        finally:
            f.close()
        # XXX - gets changed later and probably needs refactoring
        return name

    def is_running(self):
        """Return whether this process is running."""
        if self._gone:
            return False
        try:
            # Checking if pid is alive is not enough as the pid might
            # have been reused by another process.
            # pid + creation time, on the other hand, is supposed to
            # identify a process univocally.
            return self.create_time == \
                   self.get_process_create_time()
        except NoSuchProcess:
            self._gone = True
            return False

    def get_process_exe(self):
        try:
            exe = os.readlink("/proc/%s/exe" % self.pid)
        except (OSError, IOError):
            err = sys.exc_info()[1]
            if err.errno == errno.ENOENT:
                # no such file error; might be raised also if the
                # path actually exists for system processes with
                # low pids (about 0-20)
                if os.path.lexists("/proc/%s/exe" % self.pid):
                    return ""
                else:
                    # ok, it is a process which has gone away
                    raise NoSuchProcess(self.pid, self._process_name)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(self.pid, self._process_name)
            raise

        # readlink() might return paths containing null bytes causing
        # problems when used with other fs-related functions (os.*,
        # open(), ...)
        exe = exe.replace('\x00', '')
        # Certain names have ' (deleted)' appended. Usually this is
        # bogus as the file actually exists. Either way that's not
        # important as we don't want to discriminate executables which
        # have been deleted.
        if exe.endswith(" (deleted)") and not os.path.exists(exe):
            exe = exe[:-10]
        return exe

    @wrap_exceptions
    def get_process_cmdline(self):
        f = open("/proc/%s/cmdline" % self.pid)
        try:
            # return the args as a list
            return [x for x in f.read().split('\x00') if x]
        finally:
            f.close()

    @wrap_exceptions
    def get_process_terminal(self):
        f = open("/proc/%s/stat" % self.pid)
        try:
            tty_nr = int(f.read().split(' ')[6])
        finally:
            f.close()
        try:
            return _get_terminal_map()[tty_nr]
        except KeyError:
            return None

    @wrap_exceptions
    def get_process_io_counters(self):
        f = open("/proc/%s/io" % self.pid)
        try:
            for line in f:
                if line.startswith("rchar"):
                    read_count = int(line.split()[1])
                elif line.startswith("wchar"):
                    write_count = int(line.split()[1])
                elif line.startswith("read_bytes"):
                    read_bytes = int(line.split()[1])
                elif line.startswith("write_bytes"):
                    write_bytes = int(line.split()[1])
            return nt_io(read_count, write_count, read_bytes, write_bytes)
        finally:
            f.close()

    if not os.path.exists('/proc/%s/io' % os.getpid()):
        def get_process_io_counters(self):
            raise NotImplementedError('/proc/PID/io is not available')

    @wrap_exceptions
    def get_cpu_times(self):
        f = open("/proc/%s/stat" % self.pid)
        try:
            st = f.read().strip()
        finally:
            f.close()
        # ignore the first two values ("pid (exe)")
        st = st[st.find(')') + 2:]
        values = st.split(' ')
        utime = float(values[11]) / _CLOCK_TICKS
        stime = float(values[12]) / _CLOCK_TICKS
        return nt_cputimes(utime, stime)

    def get_cpu_percent(self, interval=0.1):
        """Return a float representing the current process CPU
        utilization as a percentage.

        When interval is > 0.0 compares process times to system CPU
        times elapsed before and after the interval (blocking).

        When interval is 0.0 or None compares process times to system CPU
        times elapsed since last call, returning immediately.
        In this case is recommended for accuracy that this function be
        called with at least 0.1 seconds between calls.
        """
        blocking = interval is not None and interval > 0.0
        if blocking:
            st1 = sum(cpu_times())
            pt1 = self.get_cpu_times()
            time.sleep(interval)
            st2 = sum(cpu_times())
            pt2 = self.get_cpu_times()
        else:
            st1 = self._last_sys_cpu_times
            pt1 = self._last_proc_cpu_times
            st2 = sum(cpu_times())
            pt2 = self.get_cpu_times()
            if st1 is None or pt1 is None:
                self._last_sys_cpu_times = st2
                self._last_proc_cpu_times = pt2
                return 0.0

        delta_proc = (pt2.user - pt1.user) + (pt2.system - pt1.system)
        delta_time = st2 - st1
        # reset values for next call in case of interval == None
        self._last_sys_cpu_times = st2
        self._last_proc_cpu_times = pt2

        try:
            # the utilization split between all CPUs
            overall_percent = (delta_proc / delta_time) * 100
        except ZeroDivisionError:
            # interval was too low
            return 0.0
        # the utilization of a single CPU
        single_cpu_percent = overall_percent * NUM_CPUS
        # on posix a percentage > 100 is legitimate
        # http://stackoverflow.com/questions/1032357/comprehending-top-cpu-usage
        # on windows we use this ugly hack to avoid troubles with float
        # precision issues
        if os.name != 'posix':
            if single_cpu_percent > 100.0:
                return 100.0
        return round(single_cpu_percent, 1)


    @wrap_exceptions
    def get_process_create_time(self):
        f = open("/proc/%s/stat" % self.pid)
        try:
            st = f.read().strip()
        finally:
            f.close()
        # ignore the first two values ("pid (exe)")
        st = st[st.rfind(')') + 2:]
        values = st.split(' ')
        # According to documentation, starttime is in field 21 and the
        # unit is jiffies (clock ticks).
        # We first divide it for clock ticks and then add uptime returning
        # seconds since the epoch, in UTC.
        starttime = (float(values[19]) / _CLOCK_TICKS) + BOOT_TIME
        return starttime


    def get_children(self, recursive=False):
        """Return the children of this process as a list of Process
        objects.
        If recursive is True return all the parent descendants.

        Example (A == this process):

         A ─┐
            │
            ├─ B (child) ─┐
            │             └─ X (grandchild) ─┐
            │                                └─ Y (great grandchild)
            ├─ C (child)
            └─ D (child)

        >>> p.get_children()
        B, C, D
        >>> p.get_children(recursive=True)
        B, X, Y, C, D

        Note that in the example above if process X disappears
        process Y won't be returned either as the reference to
        process A is lost.
        """
        if not self.is_running():
            name = self._process_name
            raise NoSuchProcess(self.pid, name)

        ret = []
        if not recursive:
            for p in process_iter():
                try:
                    if p.ppid == self.pid:
                        # if child happens to be older than its parent
                        # (self) it means child's PID has been reused
                        if self.create_time <= p.create_time:
                            ret.append(p)
                except NoSuchProcess:
                    pass
        else:
            # construct a dict where 'values' are all the processes
            # having 'key' as their parent
            table = defaultdict(list)
            for p in process_iter():
                try:
                    table[p.ppid].append(p)
                except NoSuchProcess:
                    pass
            # At this point we have a mapping table where table[self.pid]
            # are the current process's children.
            # Below, we look for all descendants recursively, similarly
            # to a recursive function call.
            checkpids = [self.pid]
            for pid in checkpids:
                for child in table[pid]:
                    try:
                        # if child happens to be older than its parent
                        # (self) it means child's PID has been reused
                        intime = self.create_time <= child.create_time
                    except NoSuchProcess:
                        pass
                    else:
                        if intime:
                            ret.append(child)
                            if child.pid not in checkpids:
                                checkpids.append(child.pid)
        return ret


    @wrap_exceptions
    def get_memory_info(self):
        f = open("/proc/%s/statm" % self.pid)
        try:
            vms, rss = f.readline().split()[:2]
            return nt_meminfo(int(rss) * _PAGESIZE,
                              int(vms) * _PAGESIZE)
        finally:
            f.close()

    _nt_ext_mem = namedtuple('meminfo', 'rss vms shared text lib data dirty')

    @wrap_exceptions
    def get_ext_memory_info(self):
        #  ============================================================
        # | FIELD  | DESCRIPTION                         | AKA  | TOP  |
        #  ============================================================
        # | rss    | resident set size                   |      | RES  |
        # | vms    | total program size                  | size | VIRT |
        # | shared | shared pages (from shared mappings) |      | SHR  |
        # | text   | text ('code')                       | trs  | CODE |
        # | lib    | library (unused in Linux 2.6)       | lrs  |      |
        # | data   | data + stack                        | drs  | DATA |
        # | dirty  | dirty pages (unused in Linux 2.6)   | dt   |      |
        #  ============================================================
        f = open("/proc/%s/statm" % self.pid)
        try:
            vms, rss, shared, text, lib, data, dirty = \
              [int(x) * _PAGESIZE for x in f.readline().split()[:7]]
        finally:
            f.close()
        return self._nt_ext_mem(rss, vms, shared, text, lib, data, dirty)

    _mmap_base_fields = ['path', 'rss', 'size', 'pss', 'shared_clean',
                         'shared_dirty', 'private_clean', 'private_dirty',
                         'referenced', 'anonymous', 'swap']
    nt_mmap_grouped = namedtuple('mmap', ' '.join(_mmap_base_fields))
    nt_mmap_ext = namedtuple('mmap', 'addr perms ' + ' '.join(_mmap_base_fields))

    def get_memory_percent(self):
        """Compare physical system memory to process resident memory and
        calculate process memory utilization as a percentage.
        """
        rss = self.get_memory_info()[0]
        try:
            return (rss / float(TOTAL_PHYMEM)) * 100
        except ZeroDivisionError:
            return 0.0

    def get_memory_maps(self):
        """Return process's mapped memory regions as a list of nameduples.
        Fields are explained in 'man proc'; here is an updated (Apr 2012)
        version: http://goo.gl/fmebo
        """
        f = None
        try:
            f = open("/proc/%s/smaps" % self.pid)
            first_line = f.readline()
            current_block = [first_line]

            def get_blocks():
                data = {}
                for line in f:
                    fields = line.split(None, 5)
                    if len(fields) >= 5:
                        yield (current_block.pop(), data)
                        current_block.append(line)
                    else:
                        data[fields[0]] = int(fields[1]) * 1024
                yield (current_block.pop(), data)

            if first_line:  # smaps file can be empty
                for header, data in get_blocks():
                    hfields = header.split(None, 5)
                    try:
                        addr, perms, offset, dev, inode, path = hfields
                    except ValueError:
                        addr, perms, offset, dev, inode, path = hfields + ['']
                    if not path:
                        path = '[anon]'
                    else:
                        path = path.strip()
                    yield (addr, perms, path,
                           data['Rss:'],
                           data['Size:'],
                           data.get('Pss:', 0),
                           data['Shared_Clean:'], data['Shared_Clean:'],
                           data['Private_Clean:'], data['Private_Dirty:'],
                           data['Referenced:'],
                           data['Anonymous:'],
                           data['Swap:'])
            f.close()
        except EnvironmentError:
            # XXX - Can't use wrap_exceptions decorator as we're
            # returning a generator;  this probably needs some
            # refactoring in order to avoid this code duplication.
            if f is not None:
                f.close()
            err = sys.exc_info()[1]
            if err.errno in (errno.ENOENT, errno.ESRCH):
                raise NoSuchProcess(self.pid, self._process_name)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(self.pid, self._process_name)
            raise
        except:
            if f is not None:
                f.close()
            raise

    if not os.path.exists('/proc/%s/smaps' % os.getpid()):
        def get_shared_libs(self, ext):
            msg = "this Linux version does not support /proc/PID/smaps " \
                  "(kernel < 2.6.14 or CONFIG_MMU kernel configuration " \
                  "option is not enabled)"
            raise NotImplementedError(msg)

    @wrap_exceptions
    def get_process_cwd(self):
        # readlink() might return paths containing null bytes causing
        # problems when used with other fs-related functions (os.*,
        # open(), ...)
        path = os.readlink("/proc/%s/cwd" % self.pid)
        return path.replace('\x00', '')

    @wrap_exceptions
    def get_num_ctx_switches(self):
        vol = unvol = None
        f = open("/proc/%s/status" % self.pid)
        try:
            for line in f:
                if line.startswith("voluntary_ctxt_switches"):
                    vol = int(line.split()[1])
                elif line.startswith("nonvoluntary_ctxt_switches"):
                    unvol = int(line.split()[1])
                if vol is not None and unvol is not None:
                    return nt_ctxsw(vol, unvol)
            raise RuntimeError("line not found")
        finally:
            f.close()

    @wrap_exceptions
    def get_process_num_threads(self):
        f = open("/proc/%s/status" % self.pid)
        try:
            for line in f:
                if line.startswith("Threads:"):
                    return int(line.split()[1])
            raise RuntimeError("line not found")
        finally:
            f.close()

    @wrap_exceptions
    def get_process_threads(self):
        thread_ids = os.listdir("/proc/%s/task" % self.pid)
        thread_ids.sort()
        retlist = []
        hit_enoent = False
        for thread_id in thread_ids:
            try:
                f = open("/proc/%s/task/%s/stat" % (self.pid, thread_id))
            except EnvironmentError:
                err = sys.exc_info()[1]
                if err.errno == errno.ENOENT:
                    # no such file or directory; it means thread
                    # disappeared on us
                    hit_enoent = True
                    continue
                raise
            try:
                st = f.read().strip()
            finally:
                f.close()
            # ignore the first two values ("pid (exe)")
            st = st[st.find(')') + 2:]
            values = st.split(' ')
            utime = float(values[11]) / _CLOCK_TICKS
            stime = float(values[12]) / _CLOCK_TICKS
            ntuple = nt_thread(int(thread_id), utime, stime)
            retlist.append(ntuple)
        if hit_enoent:
            # raise NSP if the process disappeared on us
            os.stat('/proc/%s' % self.pid)
        return retlist


    @wrap_exceptions
    def get_process_status(self):
        f = open("/proc/%s/status" % self.pid)
        try:
            for line in f:
                if line.startswith("State:"):
                    letter = line.split()[1]
                    if letter in _status_map:
                        return _status_map[letter]
                    return constant(-1, '?')
        finally:
            f.close()

    @wrap_exceptions
    def get_open_files(self):
        retlist = []
        files = os.listdir("/proc/%s/fd" % self.pid)
        hit_enoent = False
        for fd in files:
            fd_file = "/proc/%s/fd/%s" % (self.pid, fd)
            if os.path.islink(fd_file):
                try:
                    fd_file = os.readlink(fd_file)
                except OSError:
                    # ENOENT == fd_file which is gone in the meantime
                    err = sys.exc_info()[1]
                    if err.errno == errno.ENOENT:
                        hit_enoent = True
                        continue
                    raise
                else:
                    # If file is not an absolute path there's no way
                    # to tell whether it's a regular file or not,
                    # so we skip it. A regular file is always supposed
                    # to be absolutized though.
                    if fd_file.startswith('/') and isfile_strict(fd_file):
                        ntuple = nt_openfile(fd_file, int(fd))
                        retlist.append(ntuple)
        if hit_enoent:
            # raise NSP if the process disappeared on us
            os.stat('/proc/%s' % self.pid)
        return retlist

    @wrap_exceptions
    def get_connections(self, kind='inet'):
        """Return connections opened by process as a list of namedtuples.
        The kind parameter filters for connections that fit the following
        criteria:

        Kind Value      Number of connections using
        inet            IPv4 and IPv6
        inet4           IPv4
        inet6           IPv6
        tcp             TCP
        tcp4            TCP over IPv4
        tcp6            TCP over IPv6
        udp             UDP
        udp4            UDP over IPv4
        udp6            UDP over IPv6
        all             the sum of all the possible families and protocols
        """
        # Note: in case of UNIX sockets we're only able to determine the
        # local bound path while the remote endpoint is not retrievable:
        # http://goo.gl/R3GHM
        inodes = {}
        # os.listdir() is gonna raise a lot of access denied
        # exceptions in case of unprivileged user; that's fine:
        # lsof does the same so it's unlikely that we can to better.
        for fd in os.listdir("/proc/%s/fd" % self.pid):
            try:
                inode = os.readlink("/proc/%s/fd/%s" % (self.pid, fd))
            except OSError:
                continue
            if inode.startswith('socket:['):
                # the process is using a socket
                inode = inode[8:][:-1]
                inodes[inode] = fd

        if not inodes:
            # no connections for this process
            return []

        def process(fin, family, type_):
            retlist = []
            try:
                f = open(fin, 'r')
            except IOError:
                # IPv6 not supported on this platform
                err = sys.exc_info()[1]
                if err.errno == errno.ENOENT and fin.endswith('6'):
                    return []
                else:
                    raise
            try:
                f.readline()  # skip the first line
                for line in f:
                    # IPv4 / IPv6
                    if family in (socket.AF_INET, socket.AF_INET6):
                        _, laddr, raddr, status, _, _, _, _, _, inode = \
                                                                line.split()[:10]
                        if inode in inodes:
                            laddr = self._decode_address(laddr, family)
                            raddr = self._decode_address(raddr, family)
                            if type_ == socket.SOCK_STREAM:
                                status = _TCP_STATES_TABLE[status]
                            else:
                                status = ""
                            fd = int(inodes[inode])
                            conn = nt_connection(fd, family, type_, laddr,
                                                 raddr, status)
                            retlist.append(conn)
                    elif family == socket.AF_UNIX:
                        tokens = line.split()
                        _, _, _, _, type_, _, inode = tokens[0:7]
                        if inode in inodes:

                            if len(tokens) == 8:
                                path = tokens[-1]
                            else:
                                path = ""
                            fd = int(inodes[inode])
                            type_ = int(type_)
                            conn = nt_connection(fd, family, type_, path,
                                                 None, "")
                            retlist.append(conn)
                    else:
                        raise ValueError(family)
                return retlist
            finally:
                f.close()

        tcp4 = ("tcp" , socket.AF_INET , socket.SOCK_STREAM)
        tcp6 = ("tcp6", socket.AF_INET6, socket.SOCK_STREAM)
        udp4 = ("udp" , socket.AF_INET , socket.SOCK_DGRAM)
        udp6 = ("udp6", socket.AF_INET6, socket.SOCK_DGRAM)
        unix = ("unix", socket.AF_UNIX, None)

        tmap = {
            "all"  : (tcp4, tcp6, udp4, udp6, unix),
            "tcp"  : (tcp4, tcp6),
            "tcp4" : (tcp4,),
            "tcp6" : (tcp6,),
            "udp"  : (udp4, udp6),
            "udp4" : (udp4,),
            "udp6" : (udp6,),
            "unix" : (unix,),
            "inet" : (tcp4, tcp6, udp4, udp6),
            "inet4": (tcp4, udp4),
            "inet6": (tcp6, udp6),
        }
        if kind not in tmap:
            raise ValueError("invalid %r kind argument; choose between %s"
                             % (kind, ', '.join([repr(x) for x in tmap])))
        ret = []
        for f, family, type_ in tmap[kind]:
            ret += process("/proc/net/%s" % f, family, type_)
        # raise NSP if the process disappeared on us
        os.stat('/proc/%s' % self.pid)
        return ret

    @wrap_exceptions
    def get_num_fds(self):
        return len(os.listdir("/proc/%s/fd" % self.pid))

    @wrap_exceptions
    def get_process_ppid(self):
        f = open("/proc/%s/status" % self.pid)
        try:
            for line in f:
                if line.startswith("PPid:"):
                    # PPid: nnnn
                    return int(line.split()[1])
            raise RuntimeError("line not found")
        finally:
            f.close()

    @wrap_exceptions
    def get_process_uids(self):
        f = open("/proc/%s/status" % self.pid)
        try:
            for line in f:
                if line.startswith('Uid:'):
                    _, real, effective, saved, fs = line.split()
                    return nt_uids(int(real), int(effective), int(saved))
            raise RuntimeError("line not found")
        finally:
            f.close()

    @wrap_exceptions
    def get_process_gids(self):
        f = open("/proc/%s/status" % self.pid)
        try:
            for line in f:
                if line.startswith('Gid:'):
                    _, real, effective, saved, fs = line.split()
                    return nt_gids(int(real), int(effective), int(saved))
            raise RuntimeError("line not found")
        finally:
            f.close()

    @staticmethod
    def _decode_address(addr, family):
        """Accept an "ip:port" address as displayed in /proc/net/*
        and convert it into a human readable form, like:

        "0500000A:0016" -> ("10.0.0.5", 22)
        "0000000000000000FFFF00000100007F:9E49" -> ("::ffff:127.0.0.1", 40521)

        The IP address portion is a little or big endian four-byte
        hexadecimal number; that is, the least significant byte is listed
        first, so we need to reverse the order of the bytes to convert it
        to an IP address.
        The port is represented as a two-byte hexadecimal number.

        Reference:
        http://linuxdevcenter.com/pub/a/linux/2000/11/16/LinuxAdmin.html
        """
        ip, port = addr.split(':')
        port = int(port, 16)
        # this usually refers to a local socket in listen mode with
        # no end-points connected
        if not port:
            return ()
        if family == socket.AF_INET:
            # see: http://code.google.com/p/psutil/issues/detail?id=201
            if sys.byteorder == 'little':
                ip = socket.inet_ntop(family, base64.b16decode(ip)[::-1])
            else:
                ip = socket.inet_ntop(family, base64.b16decode(ip))
        else:  # IPv6
            # old version - let's keep it, just in case...
            # ip = ip.decode('hex')
            # return socket.inet_ntop(socket.AF_INET6,
            #          ''.join(ip[i:i+4][::-1] for i in xrange(0, 16, 4)))
            ip = base64.b16decode(ip)
            # see: http://code.google.com/p/psutil/issues/detail?id=201
            if sys.byteorder == 'little':
                ip = socket.inet_ntop(socket.AF_INET6,
                                struct.pack('>4I', *struct.unpack('<4I', ip)))
            else:
                ip = socket.inet_ntop(socket.AF_INET6,
                                struct.pack('<4I', *struct.unpack('<4I', ip)))
        return (ip, port)

########NEW FILE########
__FILENAME__ = interface
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-util/rce/util/interface.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# zope specific imports
from zope.interface import verify
from zope.interface.exceptions import Invalid


class InterfaceError(Exception):
    """ This error occurs when zope throws an error during an object or a class
        verification.
    """
    pass


def verifyObject(interfaceCls, obj):
    """ Verifies if the object implements the specified interface. Raises an
        InterfaceError if this is not the case.

        @param interfaceCls:    Interface class which the object should
                                implement.
        @type  interfaceCls:    zope.interface.Interface

        @param obj:             Object which should be verified.

        @raise:                 rce.util.interface.InterfaceError
    """
    try:
        verify.verifyObject(interfaceCls, obj)
    except Invalid as e:
        raise InterfaceError('Verification of the object of type "{0}" '
                             'failed: {1}'.format(obj.__class__.__name__, e))


def verifyClass(interfaceCls, cls):
    """ Verifies if the class implements the specified interface. Raises an
        InterfaceError if this is not the case.

        @param interfaceCls:    Interface class which the class should
                                implement.
        @type  interfaceCls:    zope.interface.Interface

        @param cls:             Class which should be verified.

        @raise:                 rce.util.interface.InterfaceError
    """
    try:
        verify.verifyClass(interfaceCls, cls)
    except Invalid as e:
        raise InterfaceError('Verification of the class of type "{0}" '
                             'failed: {1}'.format(cls.__name__, e))

########NEW FILE########
__FILENAME__ = loader
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     rce-util/rce/util/loader.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#     This file is based on the module roslib.launcher of the ROS library:
#
#         Licensed under the Software License Agreement (BSD License)
#
#         Copyright (c) 2008, Willow Garage, Inc.
#         All rights reserved.
#
#         Redistribution and use in source and binary forms, with or without
#         modification, are permitted provided that the following conditions
#         are met:
#
#          * Redistributions of source code must retain the above copyright
#            notice, this list of conditions and the following disclaimer.
#          * Redistributions in binary form must reproduce the above
#            copyright notice, this list of conditions and the following
#            disclaimer in the documentation and/or other materials provided
#            with the distribution.
#          * Neither the name of Willow Garage, Inc. nor the names of its
#            contributors may be used to endorse or promote products derived
#            from this software without specific prior written permission.
#
#         THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#         "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#         LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
#         FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
#         COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
#         INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
#         BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#         LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#         CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
#         LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
#         ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#         POSSIBILITY OF SUCH DAMAGE.
#
#

# Python specific imports
import os
import sys

# ROS specific imports
try:
    import rospkg
    import roslib.packages
except ImportError:
    print('Can not import ROS Python libraries.')
    print('Make sure they are installed and the ROS Environment is setup.')
    exit(1)

class ResourceNotFound(Exception):
    """ Exception is raised by the Loader when a resource can not be found.
    """


class Loader(object):
    """ The Loader should be used to dynamically find and load message and
        service classes. Additionally, the Loader can be used to locate
        nodes/executables in packages.
        To increase the speed the Loader has a cache for the classes and the
        paths to the nodes.
    """
    def __init__(self, rosPath=None):
        """ Initialize the Loader.

            @param rosPath:     Ordered list of paths to search for resources.
                                If None (default), use environment ROS path.
            @type  rosPath:     [str] / None
        """
        self._rp = rospkg.RosPack(rosPath)

        # List of all packages which are already added to sys.path
        self._packages = set()

        # Key:    tuple (package name, clsType, cls)
        # Value:  msg/srv module
        self._moduleCache = {}

    def _getDepends(self, pkg):
        """ roslib.launcher

            Get all package dependencies which are not catkin-ized.

            @param pkg:     Name of the package for which the dependencies
                            should be returned.
            @type  pkg:     str

            @return:        List of all non catkin-ized dependencies.
            @rtype:         [str]
        """
        vals = self._rp.get_depends(pkg, implicit=True)
        return [v for v in vals if not self._rp.get_manifest(v).is_catkin]

    def _appendPackagePaths(self, manifest, paths, pkgDir):
        """ roslib.launcher

            Add paths for package to paths.

            @param manifest:    Package manifest
            @type  manifest:    Manifest

            @param paths:       List of paths to append to
            @type  paths:       [str]

            @param pkgDir:      Package's filesystem directory path
            @type  pkgDir:      str
        """
        exports = manifest.get_export('python', 'path')

        if exports:
            paths.extend(e.replace('${prefix}', pkgDir)
                             for export in exports
                                 for e in export.split(':'))
        else:
            dirs = [os.path.join(pkgDir, d) for d in ['src', 'lib']]
            paths.extend(d for d in dirs if os.path.isdir(d))

    def _generatePythonPath(self, pkg):
        """ roslib.launcher

            Recursive subroutine for building dependency list and Python path.

            @param pkg:     Name of package for which Python paths should be
                            generated.
            @type  pkg:     str
        """
        if pkg in self._packages:
            return []

        # short-circuit if this is a catkin-ized package
        m = self._rp.get_manifest(pkg)

        if m.is_catkin:
            self._packages.add(pkg)
            return []

        packages = self._getDepends(pkg)
        packages.append(pkg)

        paths = []

        try:
            for p in packages:
                m = self._rp.get_manifest(p)
                d = self._rp.get_path(p)
                self._appendPackagePaths(m, paths, d)
                self._packages.add(p)
        except:
            self._packages.discard(pkg)
            raise

        return paths

    def _loadManifest(self, pkg):
        """ roslib.launcher

            Update the Python sys.path with package's dependencies.

            @param pkg:     Name of the package for which the manifest should
                            be loaded.
            @type  pkg:     str
        """
        if pkg in self._packages:
            return

        sys.path = self._generatePythonPath(pkg) + sys.path

    def _checkPermission(self, module):
        """ Internally used method to check if there might me a candidate for
            the module for which we have insufficient permissions.

            @return:        True if there is a directory which we can not
                            access and which has the correct module name.
                            False if there is no candidate with insufficient
                            permissions.
            @rtype:         bool
        """
        permission = []

        for p in sys.path:
            path = os.path.join(p, module[0])

            if os.path.isdir(path):
                if not os.access(path, os.R_OK | os.X_OK):
                    permission.append(True)
                elif (len(module) > 1 and
                      any(os.access(os.path.join(path, init), os.F_OK)
                          for init in ['__init__.py', '__init__.pyc'])):
                    permission.append(self._checkPermission(module[1:]))

        return bool(permission and all(permission))

    def _loadModule(self, pkg, clsType, cls):
        """ Internally used method to load a module.
        """
        try:
            self._loadManifest(pkg)
        except rospkg.ResourceNotFound:
            raise ResourceNotFound('Can not load manifest for ROS package '
                                   '"{0}".'.format(pkg))

        try:
            return __import__('.'.join([pkg, clsType]), fromlist=[cls])
        except ImportError as e:
            if self._checkPermission([pkg, clsType]):
                raise ResourceNotFound('Can not import {0}.{1} of ROS package '
                                       '{2}: There is a module candidate for '
                                       'whose directory I have insufficient '
                                       'permissions.')

            raise ResourceNotFound('Can not import {0}.{1} of ROS package '
                                   '{2}: {1}'.format(clsType, cls, pkg, e))

    def loadMsg(self, pkg, cls):
        """ Get the message class matching the string pair.
            This method uses a internal cache; therefore, changes on the
            filesystem will be ignored once the class is loaded into the cache.

            @param pkg:     Package name from where the class should be loaded.
            @type  pkg:     str

            @param cls:     Class name of the message class which should be
                            loaded.
            @type  cls:     str

            @return:        Class matching the string pair.
            @rtype:         subclass of genpy.message.Message

            @raise:         ValueError, rce.util.loader.ResourceNotFound
        """
        if isinstance(pkg, unicode):
            try:
                pkg = str(pkg)
            except UnicodeEncodeError:
                raise ValueError('The package "{0}" is not valid.'.format(pkg))

        if isinstance(cls, unicode):
            try:
                cls = str(cls)
            except UnicodeEncodeError:
                raise ValueError('The class "{0}" is not valid.'.format(cls))

        key = (pkg, 'msg', cls)

        try:
            module = self._moduleCache[key]
        except KeyError:
            module = self._loadModule(*key)
            self._moduleCache[key] = module

        try:
            return getattr(module, cls)
        except AttributeError:
            raise ResourceNotFound('ROS package "{0}" does not have '
                                   'message class "{1}"'.format(pkg, cls))

    def loadSrv(self, pkg, cls):
        """ Get the service class matching the string pair.
            This method uses a internal cache; therefore, changes on the
            filesystem will be ignored once the class is loaded into the cache.

            @param pkg:     Package name from where the class should be loaded.
            @type  pkg:     str

            @param cls:     Class name of the message class which should be
                            loaded.
            @type  cls:     str

            @return:        Class matching the string pair.
            @rtype:         ROS service class

            @raise:         ValueError, rce.util.loader.ResourceNotFound
        """
        if isinstance(pkg, unicode):
            try:
                pkg = str(pkg)
            except UnicodeEncodeError:
                raise ValueError('The package "{0}" is not valid.'.format(pkg))

        if isinstance(cls, unicode):
            try:
                cls = str(cls)
            except UnicodeEncodeError:
                raise ValueError('The class "{0}" is not valid.'.format(cls))

        key = (pkg, 'srv', cls)

        try:
            module = self._moduleCache[key]
        except KeyError:
            module = self._loadModule(*key)
            self._moduleCache[key] = module

        try:
            return getattr(module, cls)
        except AttributeError:
            raise ResourceNotFound('ROS package "{0}" does not have '
                                   'service class "{1}"'.format(pkg, cls))

    def findPkgPath(self, pkg):
        """ Find the path to the given package.

            @param pkg:     Package name in for which the path should be
                            returned.
            @type  pkg:     str

            @return:        Path to the package.
            @rtype:         str

            @raise:         rce.util.loader.ResourceNotFound
        """
        try:
            return self._rp.get_path(pkg)
        except rospkg.ResourceNotFound:
            raise ResourceNotFound('Can not find ROS package '
                                   '"{0}".'.format(pkg))

    def findNode(self, pkg, exe):
        """ Find the node/executable in the given package.

            @param pkg:     Package name in which the node should be localized.
            @type  pkg:     str

            @param exe:     Name of the node/executable which should be
                            localized.
            @type  exe:     str

            @return:        Path to the executable in package.
            @rtype:         str

            @raise:         rce.util.loader.ResourceNotFound
        """
        try:
            return roslib.packages.find_node(pkg, exe, rospack=self._rp)[0]
        except rospkg.ResourceNotFound:
            raise ResourceNotFound('Can not find ROS package '
                                   '"{0}".'.format(pkg))
        except IndexError:
            raise ResourceNotFound('Can not find executable "{0}" in '
                                   'ROS package "{1}".'.format(exe, pkg))

########NEW FILE########
__FILENAME__ = ros
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#     
#     rce-util/rce/util/ros.py
#     
#     This file is part of the RoboEarth Cloud Engine framework.
#     
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#     
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#     
#     Copyright 2013 RoboEarth
#     
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#     
#     http://www.apache.org/licenses/LICENSE-2.0
#     
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#     
#     \author/s: Dominique Hunziker 
#     
#     

# Python specific imports
from functools import wraps

# ROS specific imports
try:
    from rospy.core import get_node_uri
except ImportError:
    print('Can not import ROS Python client.')
    exit(1)


def decorator_has_connection(f):
    """ Decorator used to monkey patch the method 'has_connection' of the
        rospy Topic Implementation 'rospy.topics._TopicImpl.has_connection' to
        prevent publishers from sending messages to subscribers using the same
        endpoint ID as the publisher.
    """
    @wraps(f)
    def wrapper(self, endpoint_id):
        if endpoint_id == get_node_uri():
            return True
        
        return f(self, endpoint_id)
    
    return wrapper

########NEW FILE########
__FILENAME__ = converterTest
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     converterTest.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

import os.path

try:
    import Image
except ImportError:
    print('Requires Python Imaging Library.\n')
    exit(0)

import roslib; roslib.load_manifest('Test')
import rospy
import sensor_msgs.msg

from Test.srv import ConverterTest


_ENCODE_MAP = {'L' : 'mono8', 'RGB' : 'rgb8', 'RGBA' : 'rgba8',
               'YCbCr' : 'yuv422'}
_CHANNEL_MAP = { 'L' : 1, 'RGB' : 3, 'RGBA' : 4, 'YCbCr' : 3 }


def callback(req):
    path = roslib.packages.get_pkg_dir('Test')
    img = Image.open(os.path.join(path, 'data/roboEarth_logo.png'))

    rosImg = sensor_msgs.msg.Image()
    rosImg.encoding = _ENCODE_MAP[img.mode]
    (rosImg.width, rosImg.height) = img.size
    rosImg.step = _CHANNEL_MAP[img.mode] * rosImg.width
    rosImg.data = img.tostring()

    return QueryTestResponse(req.a + req.b, rosImg)


def converter_test_server():
    rospy.init_node('test_server')
    s = rospy.Service('test', ConverterTest, callback)
    rospy.spin()


if __name__ == "__main__":
    converter_test_server()

########NEW FILE########
__FILENAME__ = paramTest
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     paramTest.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

import sys

import roslib; roslib.load_manifest('Test')
import rospy

from Test.srv import ParameterTest


def callback(arg):
    msg = 'int:   {0}\nstr:   {1}\nfloat: {2}\nbool:  {3}'  #\narray: {4}'
    return msg.format(rospy.get_param('int'), rospy.get_param('str'),
                      rospy.get_param('float'), rospy.get_param('bool'))  #,
                      #rospy.get_param('array'))


def parameter_test_server(arg):
    rospy.init_node('parameter_test_server')
    rospy.Service('parameterTest', ParameterTest, lambda req: callback(arg))
    rospy.spin()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: paramTest.py [arg]')
        exit(1)

    parameter_test_server(sys.argv[1])

########NEW FILE########
__FILENAME__ = stringEcho
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     stringEcho.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

import roslib; roslib.load_manifest('Test')
import rospy
from std_msgs.msg import String

from Test.srv import StringEcho


def string_echo_server():
    rospy.init_node('stringEchoNode')

    pub = rospy.Publisher('stringEchoResp', String, latch=True)
    rospy.Subscriber('stringEchoReq', String, pub.publish)
    rospy.Service('stringEchoService', StringEcho, lambda msg: msg.data)
    rospy.spin()


if __name__ == "__main__":
    string_echo_server()

########NEW FILE########
__FILENAME__ = stringTester
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     stringTester.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# ROS specific imports
import roslib; roslib.load_manifest('Test')
import rospy

from Test.srv import StringTest

from center import TestCenter

def main():
    rospy.init_node('stringTesterNode')

    testCenter = TestCenter()
    rospy.Service('stringTest', StringTest,
                  lambda msg: (testCenter.runTest(msg.testType),))
    rospy.spin()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = testRunner
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     testRunner.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import json

# ROS specific imports
import roslib; roslib.load_manifest('Test')
import rospy

# rce test specific imports
from center import SIZES, TestCenter


PASSES = 3


def main(passes, testType, filename):
    rospy.init_node('testRunner')

    times = []
    testCenter = TestCenter()

    for _ in xrange(passes):
        times.append(testCenter.runTest(testType))

    with open(filename, 'w') as f:
        f.write(json.dumps(SIZES))
        f.write('\n')

        f.write(json.dumps(times))
        f.write('\n')


def _get_argparse():
    from argparse import ArgumentParser

    parser = ArgumentParser(prog='testRunner',
                            description='Run communication measurement for RCE '
                                        'between two ROS nodes using '
                                        'a string message.')

    parser.add_argument('--passes', type=int, help='Number of passes to do.',
                        default=PASSES)
    parser.add_argument('test', type=str, help='Test which should be run.',
                        choices=['service', 'topic'])
    parser.add_argument('output', type=str,
                        help='Filename to which the data should be written.')

    return parser


if __name__ == "__main__":
    args = _get_argparse().parse_args()

    main(args.passes, args.test, args.output)

########NEW FILE########
__FILENAME__ = center
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     center.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# Python specific imports
import string
import random
import time
from threading import Event

# ROS specific imports
import roslib; roslib.load_manifest('Test')
import rospy
from std_msgs.msg import String

# rce test specific imports
from Test.srv import StringEcho


SIZES = [3, 10, 20, 42, 88, 183, 379, 784, 1623, 3359, 6951, 14384, 29763,
         61584, 127427, 263665, 545559, 1128837, 2335721, 4832930, 10000000]


class TestCenter(object):
    _TIMEOUT = 15

    def __init__(self):
        self._times = []

        self._counter = 0
        self._event = None
        self._pub = None
        self._str = None
        self._time = None

        rospy.Subscriber('stringEchoResp', String, self._resp)

    def _runService(self):
        try:
            rospy.wait_for_service('stringEchoService', timeout=5)
        except rospy.ROSException:
            return [-1.0] * len(SIZES)

        times = []

        serviceFunc = rospy.ServiceProxy('stringEchoService', StringEcho)

        for size in SIZES:
            if size > 10:
                sample = ''.join(random.choice(string.lowercase)
                                 for _ in xrange(10))
                s = sample * int(size / 10) + 'A' * (size % 10)
            else:
                s = ''.join(random.choice(string.lowercase)
                            for _ in xrange(size))

            start = time.time()
            response = serviceFunc(s)
            end = time.time()

            if response.data != s:
                times.append(-1.0)
            else:
                times.append((end - start) * 1000)

        return times

    def _req(self):
        if self._counter >= len(SIZES):
            self._event.set()
        else:
            if SIZES[self._counter] > 10:
                sample = ''.join(random.choice(string.lowercase)
                                 for _ in xrange(10))
                rep = int(SIZES[self._counter] / 10)
                tail = 'A' * (SIZES[self._counter] % 10)

                self._str = sample * rep + tail
            else:
                self._str = ''.join(random.choice(string.lowercase)
                                    for _ in xrange(SIZES[self._counter]))

            self._time = time.time()
            self._pub.publish(self._str)

    def _resp(self, msg):
        stop = time.time()

        if not self._pub:
            return

        if len(self._str) == len(msg.data) and self._str[:10] == msg.data[:10]:
            self._times.append((stop - self._time) * 1000)
            self._time = None
            self._counter += 1
            self._req()

    def _runTopic(self):
        self._counter = 0
        self._times = []
        self._event = Event()
        self._pub = rospy.Publisher('stringEchoReq', String, latch=True)
        self._req()

        if (not self._event.wait(self._TIMEOUT) or
                len(self._times) != len(SIZES)):
            times = [-1.0] * len(SIZES)
        else:
            times = self._times

        self._pub = None
        return times

    def runTest(self, test):
        if test == 'service':
            times = self._runService()
        elif test == 'topic':
            times = self._runTopic()
        else:
            print('Unknown test: {0}'.format(test))
            times = [-1.0]

        return times

########NEW FILE########
__FILENAME__ = twisted_echo_server
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     twisted_echo_server.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# twisted specific imports
from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ServerFactory


class EchoServerProtocol(Protocol):
    def dataReceived(self, data):
        self.transport.write(data)


if __name__ == '__main__':
    factory = ServerFactory()
    factory.protocol = EchoServerProtocol
    reactor.listenTCP(8000, factory)

    reactor.run()

########NEW FILE########
__FILENAME__ = ws_echo_server
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ws_echo_server.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2013 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dominique Hunziker
#
#

# twisted specific imports
from twisted.internet import reactor

# Autobahn specific imports
from autobahn.websocket import WebSocketServerFactory, \
                               WebSocketServerProtocol, \
                               listenWS


class EchoServerProtocol(WebSocketServerProtocol):
    def onMessage(self, message, binary):
        self.sendMessage(message, binary)


if __name__ == '__main__':
    factory = WebSocketServerFactory("ws://localhost:9000")
    factory.protocol = EchoServerProtocol
    listenWS(factory)

    reactor.run()

########NEW FILE########
