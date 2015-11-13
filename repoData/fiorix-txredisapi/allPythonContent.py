__FILENAME__ = cyclone_demo
#!/usr/bin/env python
# coding: utf-8
#
# Copyright 2010 Alexandre Fiori
# based on the original Tornado by Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import collections
import functools
import sys

import cyclone.web
import cyclone.redis

from twisted.python import log
from twisted.internet import defer, reactor


class Application(cyclone.web.Application):
    def __init__(self):
        handlers = [
            (r"/text/(.+)", TextHandler),
            (r"/queue/(.+)", QueueHandler),
        ]
        settings = dict(
            debug=True,
            static_path="./frontend/static",
            template_path="./frontend/template",
        )
        RedisMixin.setup("127.0.0.1", 6379, 0, 10)
        cyclone.web.Application.__init__(self, handlers, **settings)


class RedisMixin(object):
    dbconn = None
    psconn = None
    channels = collections.defaultdict(lambda: [])

    @classmethod
    def setup(self, host, port, dbid, poolsize):
        # PubSub client connection
        qf = cyclone.redis.SubscriberFactory()
        qf.maxDelay = 20
        qf.protocol = QueueProtocol
        reactor.connectTCP(host, port, qf)

        # Normal client connection
        RedisMixin.dbconn = cyclone.redis.lazyConnectionPool(host, port,
                                                             dbid, poolsize)

    def subscribe(self, channel):
        if RedisMixin.psconn is None:
            raise cyclone.web.HTTPError(503)  # Service Unavailable

        if channel not in RedisMixin.channels:
            log.msg("Subscribing entire server to %s" % channel)
            if "*" in channel:
                RedisMixin.psconn.psubscribe(channel)
            else:
                RedisMixin.psconn.subscribe(channel)

        RedisMixin.channels[channel].append(self)
        log.msg("Client %s subscribed to %s" %
                (self.request.remote_ip, channel))

    def unsubscribe_all(self, ign):
        # Unsubscribe peer from all channels
        for channel, peers in RedisMixin.channels.iteritems():
            try:
                peers.pop(peers.index(self))
            except:
                continue

            log.msg("Client %s unsubscribed from %s" %
                    (self.request.remote_ip, channel))

            # Unsubscribe from channel if no peers are listening
            if not len(peers) and RedisMixin.psconn is not None:
                log.msg("Unsubscribing entire server from %s" % channel)
                if "*" in channel:
                    RedisMixin.psconn.punsubscribe(channel)
                else:
                    RedisMixin.psconn.unsubscribe(channel)

    def broadcast(self, pattern, channel, message):
        peers = self.channels.get(pattern or channel)
        if not peers:
            return

        # Broadcast the message to all peers in channel
        for peer in peers:
            # peer is an HTTP client, RequestHandler
            peer.write("%s: %s\r\n" % (channel, message))
            peer.flush()


# Provide GET, SET and DELETE redis operations via HTTP
class TextHandler(cyclone.web.RequestHandler, RedisMixin):
    @defer.inlineCallbacks
    def get(self, key):
        try:
            value = yield self.dbconn.get(key)
        except Exception, e:
            log.err("Redis failed to get('%s'): %s" % (key, str(e)))
            raise cyclone.web.HTTPError(503)

        self.set_header("Content-Type", "text/plain")
        self.finish("%s=%s\r\n" % (key, value))

    @defer.inlineCallbacks
    def post(self, key):
        value = self.get_argument("value")
        try:
            yield self.dbconn.set(key, value)
        except Exception, e:
            r = (key, value, str(e))
            log.err("Redis failed to set('%s', '%s'): %s" % r)
            raise cyclone.web.HTTPError(503)

        self.set_header("Content-Type", "text/plain")
        self.finish("%s=%s\r\n" % (key, value))

    @defer.inlineCallbacks
    def delete(self, key):
        try:
            n = yield self.dbconn.delete(key)
        except Exception, e:
            log.err("Redis failed to del('%s'): %s" % (key, str(e)))
            raise cyclone.web.HTTPError(503)

        self.set_header("Content-Type", "text/plain")
        self.finish("DEL %s=%d\r\n" % (key, n))


# GET will subscribe to channels or patterns
# POST will (obviously) post messages to channels
class QueueHandler(cyclone.web.RequestHandler, RedisMixin):
    @cyclone.web.asynchronous
    def get(self, channels):
        try:
            channels = channels.split(",")
        except Exception, e:
            log.err("Could not split channel names: %s" % str(e))
            raise cyclone.web.HTTPError(400, str(e))

        self.set_header("Content-Type", "text/plain")
        self.notifyFinish().addCallback(
            functools.partial(RedisMixin.unsubscribe_all, self))

        for channel in channels:
            self.subscribe(channel)
            self.write("subscribed to %s\r\n" % channel)
        self.flush()

    @defer.inlineCallbacks
    def post(self, channel):
        message = self.get_argument("message")

        try:
            n = yield self.dbconn.publish(channel, message.encode("utf-8"))
        except Exception, e:
            log.msg("Redis failed to publish('%s', '%s'): %s" %
                    (channel, repr(message), str(e)))
            raise cyclone.web.HTTPError(503)

        self.set_header("Content-Type", "text/plain")
        self.finish("OK %d\r\n" % n)


class QueueProtocol(cyclone.redis.SubscriberProtocol, RedisMixin):
    def messageReceived(self, pattern, channel, message):
        # When new messages are published to Redis channels or patterns,
        # they are broadcasted to all HTTP clients subscribed to those
        # channels.
        RedisMixin.broadcast(self, pattern, channel, message)

    def connectionMade(self):
        RedisMixin.psconn = self

        # If we lost connection with Redis during operation, we
        # re-subscribe to all channels once the connection is re-established.
        for channel in self.channels:
            if "*" in channel:
                self.psubscribe(channel)
            else:
                self.subscribe(channel)

    def connectionLost(self, why):
        RedisMixin.psconn = None


def main():
    log.startLogging(sys.stdout)
    reactor.listenTCP(8888, Application(), interface="127.0.0.1")
    reactor.run()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = monitor
#!/usr/bin/env twistd -ny
# coding: utf-8
# Copyright 2012 Gleicon Moraes/Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# run: twistd -ny monitor.tac
# it takes the full connection so no extra commands can be issued


import txredisapi

from twisted.application import internet
from twisted.application import service


class myMonitor(txredisapi.MonitorProtocol):
    def connectionMade(self):
        print "waiting for monitor data"
        print "use the redis client to send commands in another terminal"
        self.monitor()

    def messageReceived(self, message):
        print ">> %s" % message

    def connectionLost(self, reason):
        print "lost connection:", reason


class myFactory(txredisapi.MonitorFactory):
    # also a wapper for the ReconnectingClientFactory
    maxDelay = 120
    continueTrying = True
    protocol = myMonitor


application = service.Application("monitor")
srv = internet.TCPClient("127.0.0.1", 6379, myFactory())
srv.setServiceParent(application)

########NEW FILE########
__FILENAME__ = sharding
#!/usr/bin/env python
# coding: utf-8

import txredisapi as redis

from twisted.internet import defer
from twisted.internet import reactor


@defer.inlineCallbacks
def main():
    # run two redis servers, one at port 6379 and another in 6380
    conn = yield redis.ShardedConnection(["localhost:6379", "localhost:6380"])
    print repr(conn)

    keys = ["test:%d" % x for x in xrange(100)]
    for k in keys:
        try:
            yield conn.set(k, "foobar")
        except:
            print 'ops'

    result = yield conn.mget(keys)
    print result

    # testing tags
    keys = ["test{lero}:%d" % x for x in xrange(100)]
    for k in keys:
        yield conn.set(k, "foobar")

    result = yield conn.mget(keys)
    print result

    yield conn.disconnect()

if __name__ == "__main__":
    main().addCallback(lambda ign: reactor.stop())
    reactor.run()

########NEW FILE########
__FILENAME__ = subscriber
#!/usr/bin/env twistd -ny
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# See the PUBSUB documentation for details:
# http://code.google.com/p/redis/wiki/PublishSubscribe
#
# run: twistd -ny subscriber.tac
# You may not use regular commands (like get, set, etc...) on the
# subscriber connection.

import txredisapi as redis

from twisted.application import internet
from twisted.application import service


class myProtocol(redis.SubscriberProtocol):
    def connectionMade(self):
        print "waiting for messages..."
        print "use the redis client to send messages:"
        print "$ redis-cli publish zz test"
        print "$ redis-cli publish foo.bar hello world"
        self.subscribe("zz")
        self.psubscribe("foo.*")
        #reactor.callLater(10, self.unsubscribe, "zz")
        #reactor.callLater(15, self.punsubscribe, "foo.*")

        # self.continueTrying = False
        # self.transport.loseConnection()

    def messageReceived(self, pattern, channel, message):
        print "pattern=%s, channel=%s message=%s" % (pattern, channel, message)

    def connectionLost(self, reason):
        print "lost connection:", reason


class myFactory(redis.SubscriberFactory):
    # SubscriberFactory is a wapper for the ReconnectingClientFactory
    maxDelay = 120
    continueTrying = True
    protocol = myProtocol


application = service.Application("subscriber")
srv = internet.TCPClient("127.0.0.1", 6379, myFactory())
srv.setServiceParent(application)

########NEW FILE########
__FILENAME__ = transaction
#!/usr/bin/env python
# coding: utf-8

import txredisapi as redis

from twisted.internet import defer
from twisted.internet import reactor


@defer.inlineCallbacks
def transactions():
    """
    The multi() method on txredisapi connections returns a transaction.
    All redis commands called on transactions are then queued by the server.
    Calling the transaction's .commit() method executes all the queued commands
    and returns the result for each queued command in a list.
    Calling the transaction's .discard() method flushes the queue and returns
    the connection to the default non-transactional state.

    multi() also takes an optional argument keys, which can be either a
    string or an iterable (list,tuple etc) of strings. If present, the keys
    are WATCHED on the server, and if any of the keys are modified by
    a different connection before the transaction is committed,
    commit() raises a WatchError exception.

    Transactions with WATCH make multi-command atomic all or nothing operations
    possible. If a transaction fails, you can be sure that none of the commands
    in it ran and you can retry it again.
    Read the redis documentation on Transactions for more.
    http://redis.io/topics/transactions

    Tip: Try to keep transactions as short as possible.
    Connections in a transaction cannot be reused until the transaction
    is either committed or discarded. For instance, if you have a
    ConnectionPool with 10 connections and all of them are in transactions,
    if you try to run a command on the connection pool,
    it'll raise a RedisError exception.
    """
    conn = yield redis.Connection()
    # A Transaction with nothing to watch on
    txn = yield conn.multi()
    txn.incr('test:a')
    txn.lpush('test:l', 'test')
    r = yield txn.commit()  # Commit txn,call txn.discard() to discard it
    print 'Transaction1: %s' % r

    # Another transaction with a few values to watch on
    txn1 = yield conn.multi(['test:l', 'test:h'])
    txn1.lpush('test:l', 'test')
    txn1.hset('test:h', 'test', 'true')
    # Transactions with watched keys will fail if any of the keys are modified
    # externally after calling .multi() and before calling transaction.commit()
    r = yield txn1.commit()  # This will raise if WatchError if txn1 fails.
    print 'Transaction2: %s' % r
    yield conn.disconnect()


def main():
    transactions().addCallback(lambda ign: reactor.stop())

if __name__ == '__main__':
    reactor.callWhenRunning(main)
    reactor.run()

########NEW FILE########
__FILENAME__ = twistedweb_server
#!/usr/bin/env twistd -ny
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# run:
#  twistd -ny twistwedweb_server.py

import txredisapi as redis

from twisted.application import internet
from twisted.application import service
from twisted.internet import defer
from twisted.web import server
from twisted.web import xmlrpc
from twisted.web.resource import Resource


class Root(Resource):
    isLeaf = False


class BaseHandler(object):
    isLeaf = True

    def __init__(self, db):
        self.db = db
        Resource.__init__(self)


class IndexHandler(BaseHandler, Resource):
    def _success(self, value, request, message):
        request.write(message % repr(value))
        request.finish()

    def _failure(self, error, request, message):
        request.write(message % str(error))
        request.finish()

    def render_GET(self, request):
        try:
            key = request.args["key"][0]
        except:
            request.setResponseCode(404, "not found")
            return ""

        d = self.db.get(key)
        d.addCallback(self._success, request, "get: %s\n")
        d.addErrback(self._failure, request, "get failed: %s\n")
        return server.NOT_DONE_YET

    def render_POST(self, request):
        try:
            key = request.args["key"][0]
            value = request.args["value"][0]
        except:
            request.setResponseCode(404, "not found")
            return ""

        d = self.db.set(key, value)
        d.addCallback(self._success, request, "set: %s\n")
        d.addErrback(self._failure, request, "set failed: %s\n")
        return server.NOT_DONE_YET


class InfoHandler(BaseHandler, Resource):
    def render_GET(self, request):
        return "redis: %s\n" % repr(self.db)


class XmlrpcHandler(BaseHandler, xmlrpc.XMLRPC):
    allowNone = True

    @defer.inlineCallbacks
    def xmlrpc_get(self, key):
        value = yield self.db.get(key)
        defer.returnValue(value)

    @defer.inlineCallbacks
    def xmlrpc_set(self, key, value):
        result = yield self.db.set(key, value)
        defer.returnValue(result)


# redis connection
_db = redis.lazyConnectionPool()

# http resources
root = Root()
root.putChild("", IndexHandler(_db))
root.putChild("info", InfoHandler(_db))
root.putChild("xmlrpc", XmlrpcHandler(_db))

application = service.Application("webredis")
srv = internet.TCPServer(8888, server.Site(root), interface="127.0.0.1")
srv.setServiceParent(application)

########NEW FILE########
__FILENAME__ = wordfreq
#!/usr/bin/env python
# coding: utf-8

import sys
import txredisapi as redis

from twisted.internet import defer
from twisted.internet import reactor


def wordfreq(file):
    try:
        f = open(file, 'r')
        words = f.read()
        f.close()
    except Exception, e:
        print "Exception: %s" % e
        return None

    wf = {}
    wlist = words.split()
    for b in wlist:
        a = b.lower()
        if a in wf:
            wf[a] = wf[a] + 1
        else:
            wf[a] = 1
    return len(wf), wf


@defer.inlineCallbacks
def main(wordlist):
    db = yield redis.ShardedConnection(("localhost:6379", "localhost:6380"))
    for k in wordlist:
        yield db.set(k, 1)

    reactor.stop()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Usage: wordfreq.py <file_to_count.txt>"
        sys.exit(-1)
    l, wfl = wordfreq(sys.argv[1])
    print "count: %d" % l
    main(wfl.keys())
    reactor.run()

########NEW FILE########
__FILENAME__ = chash_distribution
#!/usr/bin/env python
# coding: utf-8

from txredisapi import HashRing
from collections import defaultdict

if __name__ == "__main__":
    ch = HashRing(["server1", "server2", "server3"])
    key_history = {}
    node_histogram = defaultdict(lambda: 0)
    for x in xrange(1000):
        key_history[x] = ch.get_node("k:%d" % x)
        s = key_history[x]
        node_histogram[s] = node_histogram[s] + 1
    print "server\t\tkeys:"
    for a in node_histogram.keys():
        print "%s:\t%d" % (a, node_histogram[a])

########NEW FILE########
__FILENAME__ = mixins
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from twisted.trial import unittest
from twisted.internet import defer

REDIS_HOST = "localhost"
REDIS_PORT = 6379


class Redis26CheckMixin(object):
    @defer.inlineCallbacks
    def is_redis_2_6(self):
        """
        Returns true if the Redis version >= 2.6
        """
        d = yield self.db.info("server")
        if u'redis_version' not in d:
            defer.returnValue(False)
        ver = d[u'redis_version']
        self.redis_version = ver
        ver_list = [int(x) for x in ver.split(u'.')]
        if len(ver_list) < 2:
            defer.returnValue(False)
        if ver_list[0] > 2:
            defer.returnValue(True)
        elif ver_list[0] == 2 and ver_list[1] >= 6:
            defer.returnValue(True)
        defer.returnValue(False)

    def _skipCheck(self):
        if not self.redis_2_6:
            skipMsg = "Redis version < 2.6 (found version: %s)"
            raise unittest.SkipTest(skipMsg % self.redis_version)

########NEW FILE########
__FILENAME__ = test_bitops
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import operator

import txredisapi as redis
from twisted.internet import defer
from twisted.trial import unittest
from twisted.python import failure

from .mixins import Redis26CheckMixin, REDIS_HOST, REDIS_PORT


class TestBitOps(unittest.TestCase, Redis26CheckMixin):
    _KEYS = ['_bitops_test_key1', '_bitops_test_key2',
             '_bitops_test_key3']

    @defer.inlineCallbacks
    def setUp(self):
        self.db = yield redis.Connection(REDIS_HOST, REDIS_PORT,
                                         reconnect=False)
        self.db1 = None
        self.redis_2_6 = yield self.is_redis_2_6()
        yield self.db.delete(*self._KEYS)
        yield self.db.script_flush()

    @defer.inlineCallbacks
    def tearDown(self):
        yield self.db.delete(*self._KEYS)
        yield self.db.disconnect()

    @defer.inlineCallbacks
    def test_getbit(self):
        key = self._KEYS[0]
        yield self.db.set(key, '\xaa')
        l = [1, 0, 1, 0, 1, 0, 1, 0]
        for x in range(8):
            r = yield self.db.getbit(key, x)
            self.assertEqual(r, l[x])

    @defer.inlineCallbacks
    def test_setbit(self):
        key = self._KEYS[0]
        r = yield self.db.setbit(key, 7, 1)
        self.assertEqual(r, 0)
        r = yield self.db.setbit(key, 7, 0)
        self.assertEqual(r, 1)
        r = yield self.db.setbit(key, 7, True)
        self.assertEqual(r, 0)
        r = yield self.db.setbit(key, 7, False)
        self.assertEqual(r, 1)

    @defer.inlineCallbacks
    def test_bitcount(self):
        self._skipCheck()
        key = self._KEYS[0]
        yield self.db.set(key, "foobar")
        r = yield self.db.bitcount(key)
        self.assertEqual(r, 26)
        r = yield self.db.bitcount(key, 0, 0)
        self.assertEqual(r, 4)
        r = yield self.db.bitcount(key, 1, 1)
        self.assertEqual(r, 6)

    def test_bitop_not(self):
        return self._test_bitop([operator.__not__, operator.not_,
                                 'not', 'NOT', 'NoT'],
                                '\x0f\x0f\x0f\x0f',
                                None,
                                '\xf0\xf0\xf0\xf0')

    def test_bitop_or(self):
        return self._test_bitop([operator.__or__, operator.or_,
                                 'or', 'OR', 'oR'],
                                '\x0f\x0f\x0f\x0f',
                                '\xf0\xf0\xf0\xf0',
                                '\xff\xff\xff\xff')

    def test_bitop_and(self):
        return self._test_bitop([operator.__and__, operator.and_,
                                 'and', 'AND', 'AnD'],
                                '\x0f\x0f\x0f\x0f',
                                '\xf0\xf0\xf0\xf0',
                                '\x00\x00\x00\x00')

    def test_bitop_xor(self):
        return self._test_bitop([operator.__xor__, operator.xor,
                                 'xor', 'XOR', 'XoR'],
                                '\x9c\x9c\x9c\x9c',
                                '\x6c\x6c\x6c\x6c',
                                '\xf0\xf0\xf0\xf0')

    @defer.inlineCallbacks
    def _test_bitop(self, op_list, value1, value2, expected):
        self._skipCheck()
        src_key = self._KEYS[0]
        src_key1 = self._KEYS[1]
        dest_key = self._KEYS[2]
        is_unary = value2 is None
        yield self.db.set(src_key, value1)
        if not is_unary:
            yield self.db.set(src_key1, value2)
            t = (src_key, src_key1)
        else:
            t = (src_key, )
        for op in op_list:
            yield self.db.bitop(op, dest_key, *t)
            r = yield self.db.get(dest_key)
            self.assertEqual(r, expected)
            # Test out failure cases
            # Specify only dest and no src key(s)
            cases = [self.db.bitop(op, dest_key)]
            if is_unary:
                # Try calling unary operator with > 1 operands
                cases.append(self.db.bitop(op, dest_key, src_key, src_key1))
            for case in cases:
                try:
                    r = yield case
                except redis.RedisError:
                    pass
                except:
                    tb = failure.Failure().getTraceback()
                    raise self.failureException('%s raised instead of %s:\n %s'
                                                % (sys.exc_info()[0],
                                                   'txredisapi.RedisError',
                                                   tb))
                else:
                    raise self.failureException('%s not raised (%r returned)'
                                                % ('txredisapi.RedisError',
                                                    r))

########NEW FILE########
__FILENAME__ = test_blocking
import txredisapi as redis
from twisted.internet import defer
from twisted.trial import unittest

redis_host = "localhost"
redis_port = 6379

class TestBlockingCommands(unittest.TestCase):
    QUEUE_KEY = 'txredisapi:test_queue'
    TEST_KEY = 'txredisapi:test_key'
    QUEUE_VALUE = 'queue_value'

    @defer.inlineCallbacks
    def testBlocking(self):
        db = yield redis.ConnectionPool(redis_host, redis_port, poolsize=2,
                                        reconnect=False)
        yield db.delete(self.QUEUE_KEY, self.TEST_KEY)

        # Block first connection.
        d = db.brpop(self.QUEUE_KEY, timeout=3)
        # Use second connection.
        yield db.set(self.TEST_KEY, 'somevalue')
        # Should use second connection again. Will block till end of
        # brpop otherwise.
        yield db.lpush('txredisapi:test_queue', self.QUEUE_VALUE)

        brpop_result = yield d
        self.assertNotEqual(brpop_result, None)

        yield db.delete(self.QUEUE_KEY, self.TEST_KEY)
        yield db.disconnect()



########NEW FILE########
__FILENAME__ = test_connection
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import txredisapi as redis

from twisted.internet import base
from twisted.internet import defer
from twisted.trial import unittest

base.DelayedCall.debug = False
redis_host = "localhost"
redis_port = 6379


class TestConnectionMethods(unittest.TestCase):
    @defer.inlineCallbacks
    def test_Connection(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)
        self.assertEqual(isinstance(db, redis.ConnectionHandler), True)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_ConnectionDB1(self):
        db = yield redis.Connection(redis_host, redis_port, dbid=1,
                                    reconnect=False)
        self.assertEqual(isinstance(db, redis.ConnectionHandler), True)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_ConnectionPool(self):
        db = yield redis.ConnectionPool(redis_host, redis_port, poolsize=2,
                                        reconnect=False)
        self.assertEqual(isinstance(db, redis.ConnectionHandler), True)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_lazyConnection(self):
        db = redis.lazyConnection(redis_host, redis_port, reconnect=False)
        self.assertEqual(isinstance(db._connected, defer.Deferred), True)
        db = yield db._connected
        self.assertEqual(isinstance(db, redis.ConnectionHandler), True)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_lazyConnectionPool(self):
        db = redis.lazyConnectionPool(redis_host, redis_port, reconnect=False)
        self.assertEqual(isinstance(db._connected, defer.Deferred), True)
        db = yield db._connected
        self.assertEqual(isinstance(db, redis.ConnectionHandler), True)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_ShardedConnection(self):
        hosts = ["%s:%s" % (redis_host, redis_port)]
        db = yield redis.ShardedConnection(hosts, reconnect=False)
        self.assertEqual(isinstance(db, redis.ShardedConnectionHandler), True)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_ShardedConnectionPool(self):
        hosts = ["%s:%s" % (redis_host, redis_port)]
        db = yield redis.ShardedConnectionPool(hosts, reconnect=False)
        self.assertEqual(isinstance(db, redis.ShardedConnectionHandler), True)
        yield db.disconnect()

########NEW FILE########
__FILENAME__ = test_connection_charset
# coding: utf-8
# Copyright 2013 Ilia Glazkov
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import txredisapi as redis
from twisted.internet import defer
from twisted.trial import unittest


class TestConnectionCharset(unittest.TestCase):
    TEST_KEY = 'txredisapi:test_key'
    TEST_VALUE_UNICODE = u'\u262d' * 3
    TEST_VALUE_BINARY = TEST_VALUE_UNICODE.encode('utf-8')

    @defer.inlineCallbacks
    def test_charset_None(self):
        db = yield redis.Connection(charset=None)

        yield db.set(self.TEST_KEY, self.TEST_VALUE_BINARY)
        result = yield db.get(self.TEST_KEY)
        self.assertTrue(type(result) == str)
        self.assertEqual(result, self.TEST_VALUE_BINARY)

        yield db.delete(self.TEST_KEY)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_charset_default(self):
        db = yield redis.Connection()

        yield db.set(self.TEST_KEY, self.TEST_VALUE_UNICODE)
        result = yield db.get(self.TEST_KEY)
        self.assertTrue(type(result) == unicode)
        self.assertEqual(result, self.TEST_VALUE_UNICODE)

        yield db.delete(self.TEST_KEY)
        yield db.disconnect()

########NEW FILE########
__FILENAME__ = test_hash_ops
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import txredisapi as redis

from twisted.internet import defer
from twisted.trial import unittest

redis_host = "localhost"
redis_port = 6379


class TestRedisHashOperations(unittest.TestCase):
    @defer.inlineCallbacks
    def testRedisHSetHGet(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)
        for hk in ("foo", "bar"):
            yield db.hset("txredisapi:HSetHGet", hk, 1)
            result = yield db.hget("txredisapi:HSetHGet", hk)
            self.assertEqual(result, 1)

        yield db.disconnect()

    @defer.inlineCallbacks
    def testRedisHMSetHMGet(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)
        t_dict = {}
        t_dict['key1'] = 'uno'
        t_dict['key2'] = 'dos'
        yield db.hmset("txredisapi:HMSetHMGet", t_dict)
        ks = t_dict.keys()
        ks.reverse()
        vs = t_dict.values()
        vs.reverse()
        res = yield db.hmget("txredisapi:HMSetHMGet", ks)
        self.assertEqual(vs, res)

        yield db.disconnect()

    @defer.inlineCallbacks
    def testRedisHKeysHVals(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)
        t_dict = {}
        t_dict['key1'] = 'uno'
        t_dict['key2'] = 'dos'
        yield db.hmset("txredisapi:HKeysHVals", t_dict)

        vs_u = [unicode(v) for v in t_dict.values()]
        ks_u = [unicode(k) for k in t_dict.keys()]
        k_res = yield db.hkeys("txredisapi:HKeysHVals")
        v_res = yield db.hvals("txredisapi:HKeysHVals")
        self.assertEqual(ks_u, k_res)
        self.assertEqual(vs_u, v_res)

        yield db.disconnect()

    @defer.inlineCallbacks
    def testRedisHIncrBy(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)
        yield db.hset("txredisapi:HIncrBy", "value", 1)
        yield db.hincr("txredisapi:HIncrBy", "value")
        yield db.hincrby("txredisapi:HIncrBy", "value", 2)
        result = yield db.hget("txredisapi:HIncrBy", "value")
        self.assertEqual(result, 4)

        yield db.hincrby("txredisapi:HIncrBy", "value", 10)
        yield db.hdecr("txredisapi:HIncrBy", "value")
        result = yield db.hget("txredisapi:HIncrBy", "value")
        self.assertEqual(result, 13)

        yield db.disconnect()

    @defer.inlineCallbacks
    def testRedisHLenHDelHExists(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)
        t_dict = {}
        t_dict['key1'] = 'uno'
        t_dict['key2'] = 'dos'

        s = yield db.hmset("txredisapi:HDelHExists", t_dict)
        r_len = yield db.hlen("txredisapi:HDelHExists")
        self.assertEqual(r_len, 2)

        s = yield db.hdel("txredisapi:HDelHExists", "key2")
        r_len = yield db.hlen("txredisapi:HDelHExists")
        self.assertEqual(r_len, 1)

        s = yield db.hexists("txredisapi:HDelHExists", "key2")
        self.assertEqual(s, 0)

        yield db.disconnect()

    @defer.inlineCallbacks
    def testRedisHLenHDelMulti(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)
        t_dict = {}
        t_dict['key1'] = 'uno'
        t_dict['key2'] = 'dos'

        s = yield db.hmset("txredisapi:HDelHExists", t_dict)
        r_len = yield db.hlen("txredisapi:HDelHExists")
        self.assertEqual(r_len, 2)

        s = yield db.hdel("txredisapi:HDelHExists", ["key1", "key2"])
        r_len = yield db.hlen("txredisapi:HDelHExists")
        self.assertEqual(r_len, 0)

        s = yield db.hexists("txredisapi:HDelHExists", ["key1", "key2"])
        self.assertEqual(s, 0)

        yield db.disconnect()

    @defer.inlineCallbacks
    def testRedisHGetAll(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)

        d = {u"key1": u"uno", u"key2": u"dos"}
        yield db.hmset("txredisapi:HGetAll", d)
        s = yield db.hgetall("txredisapi:HGetAll")

        self.assertEqual(d, s)
        yield db.disconnect()

########NEW FILE########
__FILENAME__ = test_list_ops
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import txredisapi as redis

from twisted.internet import defer
from twisted.trial import unittest

redis_host = "localhost"
redis_port = 6379


class TestRedisListOperations(unittest.TestCase):
    @defer.inlineCallbacks
    def testRedisLPUSHSingleValue(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)
        yield db.delete("txredisapi:LPUSH")
        yield db.lpush("txredisapi:LPUSH", "singlevalue")
        result = yield db.lpop("txredisapi:LPUSH")
        self.assertEqual(result, "singlevalue")
        yield db.disconnect()

    @defer.inlineCallbacks
    def testRedisLPUSHListOfValues(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)
        yield db.delete("txredisapi:LPUSH")
        yield db.lpush("txredisapi:LPUSH", [1,2,3])
        result = yield db.lrange("txredisapi:LPUSH", 0, -1)
        self.assertEqual(result, [3,2,1])
        yield db.disconnect()

    @defer.inlineCallbacks
    def testRedisRPUSHSingleValue(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)
        yield db.delete("txredisapi:RPUSH")
        yield db.lpush("txredisapi:RPUSH", "singlevalue")
        result = yield db.lpop("txredisapi:RPUSH")
        self.assertEqual(result, "singlevalue")
        yield db.disconnect()

    @defer.inlineCallbacks
    def testRedisRPUSHListOfValues(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)
        yield db.delete("txredisapi:RPUSH")
        yield db.lpush("txredisapi:RPUSH", [1,2,3])
        result = yield db.lrange("txredisapi:RPUSH", 0, -1)
        self.assertEqual(result, [3,2,1])
        yield db.disconnect()




########NEW FILE########
__FILENAME__ = test_multibulk
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import txredisapi as redis
from twisted.internet import defer
from twisted.trial import unittest

redis_host = "localhost"
redis_port = 6379


class LargeMultiBulk(unittest.TestCase):
    _KEY = 'txredisapi:testlargemultibulk'

    @defer.inlineCallbacks
    def setUp(self):
        self.db = yield redis.Connection(
            redis_host, redis_port, reconnect=False)

    @defer.inlineCallbacks
    def tearDown(self):
        yield self.db.delete(self._KEY)
        yield self.db.disconnect()

    @defer.inlineCallbacks
    def _test_multibulk(self, data):
        yield defer.DeferredList([self.db.sadd(self._KEY, x) for x in data])
        res = yield self.db.smembers(self._KEY)
        self.assertEqual(set(res), data)

    def test_large_multibulk_int(self):
        data = set(range(1000))
        return self._test_multibulk(data)

    def test_large_multibulk_str(self):
        data = set([os.urandom(10).encode('base64') for x in range(100)])
        return self._test_multibulk(data)

    @defer.inlineCallbacks
    def test_bulk_numeric(self):
        test_values = [
            '', '.hello', '+world', '123test',
            +1, 0.1, 0.01, -0.1, 0, -10]
        for v in test_values:
            yield self.db.set(self._KEY, v)
            r = yield self.db.get(self._KEY)
            self.assertEqual(r, v)

    @defer.inlineCallbacks
    def test_bulk_corner_cases(self):
        '''
        Python's float() function consumes '+inf', '-inf' & 'nan' values.
        Currently, we only convert bulk strings floating point numbers
        if there's a '.' in the string.
        This test is to ensure this behavior isn't broken in the future.
        '''
        values = ['+inf', '-inf', 'NaN']
        for x in values:
            yield self.db.set(self._KEY, x)
            r = yield self.db.get(self._KEY)
            self.assertEqual(r, x)


class NestedMultiBulk(unittest.TestCase):
    @defer.inlineCallbacks
    def testNestedMultiBulkTransaction(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)

        test1 = {u"foo1": u"bar1", u"something": u"else"}
        test2 = {u"foo2": u"bar2", u"something": u"else"}

        t = yield db.multi()
        yield t.hmset("txredisapi:nmb:test1", test1)
        yield t.hgetall("txredisapi:nmb:test1")
        yield t.hmset("txredisapi:nmb:test2", test2)
        yield t.hgetall("txredisapi:nmb:test2")
        r = yield t.commit()

        self.assertEqual(r[0], "OK")
        self.assertEqual(sorted(r[1].keys()), sorted(test1.keys()))
        self.assertEqual(sorted(r[1].values()), sorted(test1.values()))
        self.assertEqual(r[2], "OK")
        self.assertEqual(sorted(r[3].keys()), sorted(test2.keys()))
        self.assertEqual(sorted(r[3].values()), sorted(test2.values()))

        yield db.disconnect()



########NEW FILE########
__FILENAME__ = test_operations
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import txredisapi as redis
from twisted.internet import defer, reactor
from twisted.trial import unittest

redis_host = "localhost"
redis_port = 6379


class TestRedisConnections(unittest.TestCase):
    @defer.inlineCallbacks
    def testRedisOperations1(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)

        # test set() operation
        kvpairs = (("txredisapi:test1", "foo"), ("txredisapi:test2", "bar"))
        for key, value in kvpairs:
            yield db.set(key, value)
            result = yield db.get(key)
            self.assertEqual(result, value)

        yield db.disconnect()

    @defer.inlineCallbacks
    def testRedisOperations2(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)

        k = ["txredisapi:a", "txredisapi:b"]
        v = [1, 2]
        yield db.mset(dict(zip(k, v)))
        values = yield db.mget(k)
        self.assertEqual(values, v)

        k = ['txredisapi:a', 'txredisapi:notset', 'txredisapi:b']
        values = yield db.mget(k)
        self.assertEqual(values, [1, None, 2])

        yield db.disconnect()

    @defer.inlineCallbacks
    def testRedisError(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)
        yield db.set('txredisapi:a', 'test')
        try:
            yield db.sort('txredisapi:a', end='a')
        except redis.RedisError:
            pass
        else:
            yield db.disconnect()
            self.fail('RedisError not raised')

        try:
            yield db.incr('txredisapi:a')
        except redis.ResponseError:
            pass
        else:
            yield db.disconnect()
            self.fail('ResponseError not raised on redis error')
        yield db.disconnect()
        try:
            yield db.get('txredisapi:a')
        except redis.ConnectionError:
            pass
        else:
            self.fail('ConnectionError not raised')

    @defer.inlineCallbacks
    def testRedisOperationsSet1(self):

        def sleep(secs):
            d = defer.Deferred()
            reactor.callLater(secs, d.callback, None)
            return d
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)
        key, value = "txredisapi:test1", "foo"
        # test expiration in milliseconds
        yield db.set(key, value, pexpire=10)
        result_1 = yield db.get(key)
        self.assertEqual(result_1, value)
        yield sleep(0.015)
        result_2 = yield db.get(key)
        self.assertEqual(result_2, None)

        # same thing but timeout in seconds
        yield db.set(key, value, expire=1)
        result_3 = yield db.get(key)
        self.assertEqual(result_3, value)
        yield sleep(1.001)
        result_4 = yield db.get(key)
        self.assertEqual(result_4, None)
        yield db.disconnect()

    @defer.inlineCallbacks
    def testRedisOperationsSet2(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)
        key, value = "txredisapi:test_exists", "foo"
        # ensure value does not exits and new value sets
        yield db.delete(key)
        yield db.set(key, value, only_if_not_exists=True)
        result_1 = yield db.get(key)
        self.assertEqual(result_1, value)

        # new values not set cos, values exists
        yield db.set(key, "foo2", only_if_not_exists=True)
        result_2 = yield db.get(key)
        # nothing changed result is same "foo"
        self.assertEqual(result_2, value)
        yield db.disconnect()


    @defer.inlineCallbacks
    def testRedisOperationsSet3(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)
        key, value = "txredisapi:test_not_exists", "foo_not_exists"
        # ensure that such key does not exits, and value not sets
        yield db.delete(key)
        yield db.set(key, value, only_if_exists=True)
        result_1 = yield db.get(key)
        self.assertEqual(result_1, None)

        # ensure key exits, and value updates
        yield db.set(key, value)
        yield db.set(key, "foo", only_if_exists=True)
        result_2 = yield db.get(key)
        self.assertEqual(result_2, "foo")
        yield db.disconnect()

########NEW FILE########
__FILENAME__ = test_pipelining
# coding: utf-8
# Copyright 2013 Matt Pizzimenti
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import txredisapi
from twisted.trial import unittest
from twisted.internet import defer, reactor
from twisted.python import log
import sys

log.startLogging(sys.stdout)

redis_host = "localhost"
redis_port = 6379


class InspectableTransport(object):

    def __init__(self, transport):
        self.original_transport = transport
        self.write_history = []

    def __getattr__(self, method):

        if method == "write":
            def write(data, *args, **kwargs):
                self.write_history.append(data)
                return self.original_transport.write(data, *args, **kwargs)
            return write
        return getattr(self.original_transport, method)


class TestRedisConnections(unittest.TestCase):

    @defer.inlineCallbacks
    def _assert_simple_sets_on_pipeline(self, db):

        pipeline = yield db.pipeline()
        self.assertTrue(pipeline.pipelining)

        # Hook into the transport so we can inspect what is happening
        # at the protocol level.
        pipeline.transport = InspectableTransport(pipeline.transport)

        pipeline.set("txredisapi:test_pipeline", "foo")
        pipeline.set("txredisapi:test_pipeline", "bar")
        pipeline.set("txredisapi:test_pipeline2", "zip")

        yield pipeline.execute_pipeline()
        self.assertFalse(pipeline.pipelining)

        result = yield db.get("txredisapi:test_pipeline")
        self.assertEqual(result, "bar")

        result = yield db.get("txredisapi:test_pipeline2")
        self.assertEqual(result, "zip")

        # Make sure that all SET commands were sent in a single pipelined write.
        write_history = pipeline.transport.write_history
        lines_in_first_write = write_history[0].split("\n")
        sets_in_first_write = sum([1 for w in lines_in_first_write if "SET" in w])
        self.assertEqual(sets_in_first_write, 3)

    @defer.inlineCallbacks
    def _wait_for_lazy_connection(self, db):

        # For lazy connections, wait for the internal deferred to indicate
        # that the connection is established.
        yield db._connected

    @defer.inlineCallbacks
    def test_Connection(self):

        db = yield txredisapi.Connection(redis_host, redis_port, reconnect=False)
        yield self._assert_simple_sets_on_pipeline(db=db)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_ConnectionDB1(self):

        db = yield txredisapi.Connection(redis_host, redis_port, dbid=1,
                                    reconnect=False)
        yield self._assert_simple_sets_on_pipeline(db=db)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_ConnectionPool(self):

        db = yield txredisapi.ConnectionPool(redis_host, redis_port, poolsize=2,
                                        reconnect=False)
        yield self._assert_simple_sets_on_pipeline(db=db)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_lazyConnection(self):

        db = txredisapi.lazyConnection(redis_host, redis_port, reconnect=False)
        yield self._wait_for_lazy_connection(db)
        yield self._assert_simple_sets_on_pipeline(db=db)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_lazyConnectionPool(self):

        db = txredisapi.lazyConnectionPool(redis_host, redis_port, reconnect=False)
        yield self._wait_for_lazy_connection(db)
        yield self._assert_simple_sets_on_pipeline(db=db)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_ShardedConnection(self):

        hosts = ["%s:%s" % (redis_host, redis_port)]
        db = yield txredisapi.ShardedConnection(hosts, reconnect=False)
        try:
            yield db.pipeline()
            raise self.failureException("Expected sharding to disallow pipelining")
        except NotImplementedError, e:
            self.assertTrue("not supported" in str(e).lower())
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_ShardedConnectionPool(self):

        hosts = ["%s:%s" % (redis_host, redis_port)]
        db = yield txredisapi.ShardedConnectionPool(hosts, reconnect=False)
        try:
            yield db.pipeline()
            raise self.failureException("Expected sharding to disallow pipelining")
        except NotImplementedError, e:
            self.assertTrue("not supported" in str(e).lower())
        yield db.disconnect()

########NEW FILE########
__FILENAME__ = test_publish
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import txredisapi as redis
from twisted.internet import defer
from twisted.trial import unittest

redis_host = "localhost"
redis_port = 6379


class TestRedisConnections(unittest.TestCase):
    @defer.inlineCallbacks
    def testRedisPublish(self):
        db = yield redis.Connection(redis_host, redis_port, reconnect=False)

        for value in ("foo", "bar"):
            yield db.publish("test_publish", value)

        yield db.disconnect()

########NEW FILE########
__FILENAME__ = test_scripting
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import hashlib

import txredisapi as redis

from twisted.internet import defer
from twisted.trial import unittest
from twisted.internet import reactor
from twisted.python import failure

from tests.mixins import Redis26CheckMixin, REDIS_HOST, REDIS_PORT


class TestScripting(unittest.TestCase, Redis26CheckMixin):
    _SCRIPT = "return {KEYS[1],KEYS[2],ARGV[1],ARGV[2]}"  # From redis example

    @defer.inlineCallbacks
    def setUp(self):
        self.db = yield redis.Connection(REDIS_HOST, REDIS_PORT,
                                         reconnect=False)
        self.db1 = None
        self.redis_2_6 = yield self.is_redis_2_6()
        yield self.db.script_flush()

    @defer.inlineCallbacks
    def tearDown(self):
        yield self.db.disconnect()
        if self.db1 is not None:
            yield self.db1.disconnect()

    @defer.inlineCallbacks
    def test_eval(self):
        self._skipCheck()
        keys=('key1', 'key2')
        args=('first', 'second')
        r = yield self.db.eval(self._SCRIPT, keys, args)
        self._check_eval_result(keys, args, r)
        r = yield self.db.eval("return 10")
        self.assertEqual(r, 10)
        r = yield self.db.eval("return {1,2,3.3333,'foo',nil,'bar'}")
        self.assertEqual(r, [1, 2, 3, "foo"])
        # Test the case where the hash is in script_hashes,
        # but redis doesn't have it
        h = self._hash_script(self._SCRIPT)
        yield self.db.script_flush()
        conn = yield self.db._factory.getConnection(True)
        conn.script_hashes.add(h)
        r = yield self.db.eval(self._SCRIPT, keys, args)
        self._check_eval_result(keys, args, r)

    @defer.inlineCallbacks
    def test_eval_keys_only(self):
        self._skipCheck()
        keys=['foo', 'bar']
        args=[]

        r = yield self.db.eval("return {KEYS[1],KEYS[2]}", keys, args)
        self.assertEqual(r, keys)

        r = yield self.db.eval("return {KEYS[1],KEYS[2]}", keys=keys)
        self.assertEqual(r, keys)

    @defer.inlineCallbacks
    def test_eval_args_only(self):
        self._skipCheck()
        keys=[]
        args=['first', 'second']

        r = yield self.db.eval("return {ARGV[1],ARGV[2]}", keys, args)
        self.assertEqual(r, args)

        r = yield self.db.eval("return {ARGV[1],ARGV[2]}", args=args)
        self.assertEqual(r, args)

    @defer.inlineCallbacks
    def test_eval_error(self):
        self._skipCheck()
        try:
            result = yield self.db.eval('return {err="My Error"}')
        except redis.ResponseError:
            pass
        except:
            raise self.failureException('%s raised instead of %s:\n %s'
                                        % (sys.exc_info()[0],
                                           'txredisapi.ResponseError',
                                           failure.Failure().getTraceback()))
        else:
            raise self.failureException('%s not raised (%r returned)'
                                        % ('txredisapi.ResponseError', result))

    @defer.inlineCallbacks
    def test_evalsha(self):
        self._skipCheck()
        r = yield self.db.eval(self._SCRIPT)
        h = self._hash_script(self._SCRIPT)
        r = yield self.db.evalsha(h)
        self._check_eval_result([], [], r)

    @defer.inlineCallbacks
    def test_evalsha_error(self):
        self._skipCheck()
        h = self._hash_script(self._SCRIPT)
        try:
            result = yield self.db.evalsha(h)
        except redis.ScriptDoesNotExist:
            pass
        except:
            raise self.failureException('%s raised instead of %s:\n %s'
                                        % (sys.exc_info()[0],
                                           'txredisapi.ScriptDoesNotExist',
                                           failure.Failure().getTraceback()))
        else:
            raise self.failureException('%s not raised (%r returned)'
                                        % ('txredisapi.ResponseError', result))

    @defer.inlineCallbacks
    def test_script_load(self):
        self._skipCheck()
        h = self._hash_script(self._SCRIPT)
        r = yield self.db.script_exists(h)
        self.assertFalse(r)
        r = yield self.db.script_load(self._SCRIPT)
        self.assertEqual(r, h)
        r = yield self.db.script_exists(h)
        self.assertTrue(r)

    @defer.inlineCallbacks
    def test_script_exists(self):
        self._skipCheck()
        h = self._hash_script(self._SCRIPT)
        script1 = "return 1"
        h1 = self._hash_script(script1)
        r = yield self.db.script_exists(h)
        self.assertFalse(r)
        r = yield self.db.script_exists(h, h1)
        self.assertEqual(r, [False, False])
        yield self.db.script_load(script1)
        r = yield self.db.script_exists(h, h1)
        self.assertEqual(r, [False, True])
        yield self.db.script_load(self._SCRIPT)
        r = yield self.db.script_exists(h, h1)
        self.assertEqual(r, [True, True])

    @defer.inlineCallbacks
    def test_script_kill(self):
        self._skipCheck()
        try:
            result = yield self.db.script_kill()
        except redis.NoScriptRunning:
            pass
        except:
            raise self.failureException('%s raised instead of %s:\n %s'
                                        % (sys.exc_info()[0],
                                           'txredisapi.NoScriptRunning',
                                           failure.Failure().getTraceback()))
        else:
            raise self.failureException('%s not raised (%r returned)'
                                        % ('txredisapi.ResponseError', result))
        # Run an infinite loop script from one connection
        # and kill it from another.
        inf_loop = "while 1 do end"
        self.db1 = yield redis.Connection(REDIS_HOST, REDIS_PORT,
                                          reconnect=False)
        eval_deferred = self.db1.eval(inf_loop)
        reactor.iterate()
        r = yield self.db.script_kill()
        self.assertEqual(r, 'OK')
        try:
            result = yield eval_deferred
        except redis.ResponseError:
            pass
        except:
            raise self.failureException('%s raised instead of %s:\n %s'
                                        % (sys.exc_info()[0],
                                           'txredisapi.ResponseError',
                                           failure.Failure().getTraceback()))
        else:
            raise self.failureException('%s not raised (%r returned)'
                                        % ('txredisapi.ResponseError', result))

    def _check_eval_result(self, keys, args, r):
        self.assertEqual(r, list(keys) + list(args))

    def _hash_script(self, script):
        return hashlib.sha1(script).hexdigest()

########NEW FILE########
__FILENAME__ = test_sets
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import random

import txredisapi as redis

from twisted.internet import defer
from twisted.trial import unittest

redis_host = "localhost"
redis_port = 6379


class SetsTests(unittest.TestCase):
    '''
    Tests to ensure that set returning operations return sets
    '''
    _KEYS = ['txredisapi:testsets1', 'txredisapi:testsets2',
             'txredisapi:testsets3', 'txredisapi:testsets4']
    N = 1024

    @defer.inlineCallbacks
    def setUp(self):
        self.db = yield redis.Connection(redis_host, redis_port,
                                         reconnect=False)

    @defer.inlineCallbacks
    def tearDown(self):
        yield defer.gatherResults([self.db.delete(x) for x in self._KEYS])
        yield self.db.disconnect()

    @defer.inlineCallbacks
    def test_saddrem(self):
        s = set(xrange(self.N))
        r = yield self.db.sadd(self._KEYS[0], s)
        self.assertEqual(r, len(s))
        a = s.pop()
        r = yield self.db.srem(self._KEYS[0], a)
        self.assertEqual(r, 1)
        l = [s.pop() for x in range(self.N >> 2)]
        r = yield self.db.srem(self._KEYS[0], l)
        self.assertEqual(r, len(l))
        r = yield self.db.srem(self._KEYS[0], self.N + 1)
        self.assertEqual(r, 0)
        r = yield self.db.smembers(self._KEYS[0])
        self.assertIsInstance(r, set)
        self.assertEqual(r, s)

    @defer.inlineCallbacks
    def _test_set(self, key, s):
        '''
        Check if the Redis set and the Python set are identical
        '''
        r = yield self.db.scard(key)
        self.assertEqual(r, len(s))
        r = yield self.db.smembers(key)
        self.assertEqual(r, s)

    @defer.inlineCallbacks
    def test_sunion(self):
        s = set(xrange(self.N))
        s1 = set()
        for x in range(4):
            ss = set(s.pop() for x in xrange(self.N >> 2))
            s1.update(ss)
            r = yield self.db.sadd(self._KEYS[x], ss)
            self.assertEqual(r, len(ss))
        r = yield self.db.sunion(self._KEYS[:4])
        self.assertIsInstance(r, set)
        self.assertEqual(r, s1)
        # Test sunionstore
        r = yield self.db.sunionstore(self._KEYS[0], self._KEYS[:4])
        self.assertEqual(r, len(s1))
        yield self._test_set(self._KEYS[0], s1)

    @defer.inlineCallbacks
    def test_sdiff(self):
        l = range(self.N)
        random.shuffle(l)
        p1 = set(l[:self.N >> 1])
        random.shuffle(l)
        p2 = set(l[:self.N >> 1])
        r = yield self.db.sadd(self._KEYS[0], p1)
        self.assertEqual(r, len(p1))
        r = yield self.db.sadd(self._KEYS[1], p2)
        self.assertEqual(r, len(p2))
        r = yield self.db.sdiff(self._KEYS[:2])
        self.assertIsInstance(r, set)
        a = p1 - p2
        self.assertEqual(r, a)
        # Test sdiffstore
        r = yield self.db.sdiffstore(self._KEYS[0], self._KEYS[:2])
        self.assertEqual(r, len(a))
        yield self._test_set(self._KEYS[0], a)

    @defer.inlineCallbacks
    def test_sinter(self):
        l = range(self.N)
        random.shuffle(l)
        p1 = set(l[:self.N >> 1])
        random.shuffle(l)
        p2 = set(l[:self.N >> 1])
        r = yield self.db.sadd(self._KEYS[0], p1)
        self.assertEqual(r, len(p1))
        r = yield self.db.sadd(self._KEYS[1], p2)
        self.assertEqual(r, len(p2))
        r = yield self.db.sinter(self._KEYS[:2])
        self.assertIsInstance(r, set)
        a = p1.intersection(p2)
        self.assertEqual(r, a)
        # Test sinterstore
        r = yield self.db.sinterstore(self._KEYS[0], self._KEYS[:2])
        self.assertEqual(r, len(a))
        yield self._test_set(self._KEYS[0], a)

    @defer.inlineCallbacks
    def test_smembers(self):
        s = set(xrange(self.N))
        r = yield self.db.sadd(self._KEYS[0], s)
        self.assertEqual(r, len(s))
        r = yield self.db.smembers(self._KEYS[0])
        self.assertIsInstance(r, set)
        self.assertEqual(r, s)

    @defer.inlineCallbacks
    def test_sismemember(self):
        yield self.db.sadd(self._KEYS[0], 1)
        r = yield self.db.sismember(self._KEYS[0], 1)
        self.assertIsInstance(r, bool)
        self.assertEqual(r, True)
        yield self.db.srem(self._KEYS[0], 1)
        r = yield self.db.sismember(self._KEYS[0], 1)
        self.assertIsInstance(r, bool)
        self.assertEqual(r, False)

    @defer.inlineCallbacks
    def test_smove(self):
        yield self.db.sadd(self._KEYS[0], [1, 2, 3])
        # Test moving an existing element
        r = yield self.db.smove(self._KEYS[0], self._KEYS[1], 1)
        self.assertIsInstance(r, bool)
        self.assertEqual(r, True)
        r = yield self.db.smembers(self._KEYS[1])
        self.assertEqual(r, set([1]))
        # Test moving an non existing element
        r = yield self.db.smove(self._KEYS[0], self._KEYS[1], 4)
        self.assertIsInstance(r, bool)
        self.assertEqual(r, False)
        r = yield self.db.smembers(self._KEYS[1])
        self.assertEqual(r, set([1]))

########NEW FILE########
__FILENAME__ = test_sort
# coding: utf-8
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from tests.mixins import REDIS_HOST, REDIS_PORT

import txredisapi as redis
from twisted.internet import defer
from twisted.trial import unittest


class TestRedisSort(unittest.TestCase):

    @defer.inlineCallbacks
    def setUp(self):
        self.db = yield redis.Connection(REDIS_HOST, REDIS_PORT, reconnect=False)
        yield self.db.delete('txredisapi:values')
        yield self.db.lpush('txredisapi:values', [5, 3, 19, 2, 4, 34, 12])

    @defer.inlineCallbacks
    def tearDown(self):
        yield self.db.disconnect()

    @defer.inlineCallbacks
    def testSort(self):
        r = yield self.db.sort('txredisapi:values')
        self.assertEqual([2, 3, 4, 5, 12, 19, 34], r)

    @defer.inlineCallbacks
    def testSortWithEndOnly(self):
        try:
            yield self.db.sort('txredisapi:values', end=3)
        except redis.RedisError:
            pass
        else:
            self.fail('RedisError not raised: no start parameter given')

    @defer.inlineCallbacks
    def testSortWithStartOnly(self):
        try:
            yield self.db.sort('txredisapi:values', start=3)
        except redis.RedisError:
            pass
        else:
            self.fail('RedisError not raised: no end parameter given')

    @defer.inlineCallbacks
    def testSortWithLimits(self):
        r = yield self.db.sort('txredisapi:values', start=2, end=4)
        self.assertEqual([4, 5, 12, 19], r)

    @defer.inlineCallbacks
    def testSortAlpha(self):
        yield self.db.delete('txredisapi:alphavals')
        yield self.db.lpush('txredisapi:alphavals', ['dog', 'cat', 'apple'])

        r = yield self.db.sort('txredisapi:alphavals', alpha=True)
        self.assertEquals(['apple', 'cat', 'dog'], r)



########NEW FILE########
__FILENAME__ = test_sortedsets
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import txredisapi as redis

from twisted.internet import defer
from twisted.trial import unittest
from twisted.python.failure import Failure

redis_host = "localhost"
redis_port = 6379


class SortedSetsTests(unittest.TestCase):
    '''
    Tests for sorted sets
    '''
    _KEYS = ['txredisapi:testssets1', 'txredisapi:testssets2',
             'txredisapi:testssets3', 'txredisapi:testssets4']

    _NUMBERS = ["zero", "one", "two", "three", "four",
                "five", "six", "seven", "eight", "nine"]

    @defer.inlineCallbacks
    def test_zaddrem(self):
        key = self._getKey()
        t = self.assertEqual
        r = yield self.db.zadd(key, 1, "one")
        t(r, 1)
        r = yield self.db.zadd(key, 2, "two")
        t(r, 1)
        # Try adding multiple items
        r = yield self.db.zadd(key, 3, "three", 4, "four", 5, "five")
        t(r, 3)
        r = yield self.db.zcount(key, '-inf', '+inf')
        t(r, 5)
        # Try deleting one item
        r = yield self.db.zrem(key, "one")
        # Try deleting some items
        r = yield self.db.zrem(key, "two", "three")
        # Test if calling zadd with odd number of arguments errors out
        yield self.db.zadd(key, 1, "one", 2).addBoth(
            self._check_invaliddata_error, shouldError=True)
        # Now try doing it the right way
        yield self.db.zadd(key, 1, "one", 2, "two").addBoth(
            self._check_invaliddata_error)

    @defer.inlineCallbacks
    def test_zcard_zcount(self):
        key = self._getKey()
        t = self.assertEqual
        yield self._make_sorted_set(key)
        r = yield self.db.zcard(key)   # Check ZCARD
        t(r, 10)
        r = yield self.db.zcount(key)  # ZCOUNT with default args
        t(r, 10)
        r = yield self.db.zcount(key, 1, 5)  # ZCOUNT with args
        t(r, 5)
        r = yield self.db.zcount(key, '(1', 5)  # Exclude arg1
        t(r, 4)
        r = yield self.db.zcount(key, '(1', '(3')  # Exclue arg1 & arg2
        t(r, 1)

    @defer.inlineCallbacks
    def test_zincrby(self):
        key = self._getKey()
        t = self.assertEqual
        yield self._make_sorted_set(key, 1, 3)
        r = yield self.db.zincrby(key, 2, "one")
        t(r, 3)
        r = yield self.db.zrange(key, withscores=True)
        t(r, [('two', 2), ('one', 3)])
        # Also test zincr
        r = yield self.db.zincr(key, "one")
        t(r, 4)
        r = yield self.db.zrange(key, withscores=True)
        t(r, [('two', 2), ('one', 4)])
        # And zdecr
        r = yield self.db.zdecr(key, "one")
        t(r, 3)
        r = yield self.db.zrange(key, withscores=True)
        t(r, [('two', 2), ('one', 3)])

    def test_zrange(self):
        return self._test_zrange(False)

    def test_zrevrange(self):
        return self._test_zrange(True)

    def test_zrank(self):
        return self._test_zrank(False)

    def test_zrevrank(self):
        return self._test_zrank(True)

    @defer.inlineCallbacks
    def test_zscore(self):
        key = self._getKey()
        r, l = yield self._make_sorted_set(key)
        for k, s in l:
            r = yield self.db.zscore(key, k)
            self.assertEqual(r, s)
        r = yield self.db.zscore(key, 'none')
        self.assertTrue(r is None)
        r = yield self.db.zscore('none', 'one')
        self.assertTrue(r is None)

    @defer.inlineCallbacks
    def test_zremrangebyrank(self):
        key = self._getKey()
        t = self.assertEqual
        r, l = yield self._make_sorted_set(key)
        r = yield self.db.zremrangebyrank(key)
        t(r, len(l))
        r = yield self.db.zrange(key)
        t(r, [])  # Check default args
        yield self._make_sorted_set(key, begin=1, end=4)
        r = yield self.db.zremrangebyrank(key, 0, 1)
        t(r, 2)
        r = yield self.db.zrange(key, withscores=True)
        t(r, [('three', 3)])

    @defer.inlineCallbacks
    def test_zremrangebyscore(self):
        key = self._getKey()
        t = self.assertEqual
        r, l = yield self._make_sorted_set(key, end=4)
        r = yield self.db.zremrangebyscore(key)
        t(r, len(l))
        r = yield self.db.zrange(key)
        t(r, [])  # Check default args
        yield self._make_sorted_set(key, begin=1, end=4)
        r = yield self.db.zremrangebyscore(key, '-inf', '(2')
        t(r, 1)
        r = yield self.db.zrange(key, withscores=True)
        t(r, [('two', 2), ('three', 3)])

    def test_zrangebyscore(self):
        return self._test_zrangebyscore(False)

    def test_zrevrangebyscore(self):
        return self._test_zrangebyscore(True)

    def test_zinterstore(self):
        agg_map = {
            'min': (('min', min), {
                    -1: [('three', -3)],
                    0: [(u'three', 0)],
                    1: [(u'three', 3)],
                    2: [(u'three', 3)],
                    }),
            'max': (('max', max), {
                    -1: [('three', 3)],
                    0: [('three', 3)],
                    1: [('three', 3)],
                    2: [('three', 6)],
                    }),
            'sum': (('sum', sum),  {
                    -1: [('three', 0)],
                    0: [('three', 3)],
                    1: [('three', 6)],
                    2: [('three', 9)],
                    })
        }
        return self._test_zunion_inter_store(agg_map)

    def test_zunionstore(self):
        agg_map = {
            'min': (('min', min), {
                -1: [('five', -5), ('four', -4), ('three', -3),
                    ('one', 1), ('two', 2)],
                0: [('five', 0), ('four', 0), ('three', 0),
                    ('one', 1), ('two', 2)],
                1: [('one', 1), ('two', 2), ('three', 3),
                    ('four', 4), ('five', 5)],
                2: [('one', 1), ('two', 2), ('three', 3),
                    ('four', 8), ('five', 10)]
            }),
            'max': (('max', max), {
                -1: [('five', -5), ('four', -4), ('one', 1),
                     ('two', 2), ('three', 3)],
                0: [('five', 0), ('four', 0), ('one', 1),
                    ('two', 2), ('three', 3)],
                1: [('one', 1), ('two', 2), ('three', 3),
                    ('four', 4), ('five', 5)],
                2: [('one', 1), ('two', 2), ('three', 6),
                    ('four', 8), ('five', 10)]
            }),
            'sum': (('sum', sum),  {
                -1: [('five', -5), ('four', -4), ('three', 0),
                   ('one', 1), ('two', 2)],
                0: [('five', 0), ('four', 0), ('one', 1),
                    ('two', 2), ('three', 3)],
                1: [('one', 1), ('two', 2), ('four', 4),
                                ('five', 5), ('three', 6)],
                2: [('one', 1), ('two', 2), ('four', 8),
                    ('three', 9), ('five', 10)]
            })
        }
        return self._test_zunion_inter_store(agg_map, True)

    @defer.inlineCallbacks
    def _test_zunion_inter_store(self, agg_function_map, union=False):
        if union:
            cmd = self.db.zunionstore
        else:
            cmd = self.db.zinterstore
        key = self._getKey()
        t = self.assertEqual
        key1 = self._getKey(1)
        destKey = self._getKey(2)
        r, l = yield self._make_sorted_set(key, begin=1, end=4)
        r1, l1 = yield self._make_sorted_set(key1, begin=3, end=6)
        for agg_fn_name in agg_function_map:
            for agg_fn in agg_function_map[agg_fn_name][0]:
                for key1_weight in range(-1, 3):
                    if key1_weight == 1:
                        keys = [key, key1]
                    else:
                        keys = {key: 1, key1: key1_weight}
                    r = yield cmd(destKey, keys, aggregate=agg_fn)
                    if union:
                        t(r, len(set(l + l1)))
                    else:
                        t(r, len(set(l) & set(l1)))
                    r = yield self.db.zrange(destKey, withscores=True)
                    t(r, agg_function_map[agg_fn_name][1][key1_weight])
                    yield self.db.delete(destKey)
        # Finally, test for invalid aggregate functions
        yield self.db.delete(key, key1)
        yield self._make_sorted_set(key, begin=1, end=4)
        yield self._make_sorted_set(key1, begin=3, end=6)
        yield cmd(destKey, [key, key1], aggregate='SIN').addBoth(
            self._check_invaliddata_error, shouldError=True)
        yield cmd(destKey, [key, key1], aggregate=lambda a, b: a + b).addBoth(
            self._check_invaliddata_error, shouldError=True)
        yield self.db.delete(destKey)

    @defer.inlineCallbacks
    def _test_zrangebyscore(self, reverse):
        key = self._getKey()
        t = self.assertEqual
        if reverse:
            command = self.db.zrevrangebyscore
        else:
            command = self.db.zrangebyscore
        for ws in [True, False]:
            r, l = yield self._make_sorted_set(key, begin=1, end=4)
            if reverse:
                l.reverse()
            r = yield command(key, withscores=ws)
            if ws:
                t(r, l)
            else:
                t(r, [x[0] for x in l])
            r = yield command(key, withscores=ws, offset=1, count=1)
            if ws:
                t(r, [('two', 2)])
            else:
                t(r, ['two'])
            yield self.db.delete(key)
        # Test for invalid offset and count
        yield self._make_sorted_set(key, begin=1, end=4)
        yield command(key, offset=1).addBoth(
            self._check_invaliddata_error, shouldError=True)
        yield command(key, count=1).addBoth(
            self._check_invaliddata_error, shouldError=True)

    @defer.inlineCallbacks
    def _test_zrank(self, reverse):
        key = self._getKey()
        r, l = yield self._make_sorted_set(key)
        if reverse:
            command = self.db.zrevrank
            l.reverse()
        else:
            command = self.db.zrank
        for k, s in l:
            r = yield command(key, k)
            self.assertEqual(l[r][0], k)
        r = yield command(key, 'none')  # non-existant member
        self.assertTrue(r is None)
        r = yield command('none', 'one')
        self.assertTrue(r is None)

    @defer.inlineCallbacks
    def _test_zrange(self, reverse):
        key = self._getKey()
        t = self.assertEqual
        r, l = yield self._make_sorted_set(key)
        if reverse:
            command = self.db.zrevrange
            l.reverse()
        else:
            command = self.db.zrange
        r = yield command(key)
        t(r, [x[0] for x in l])
        r = yield command(key, withscores=True)
        # Ensure that WITHSCORES returns tuples
        t(r, l)
        # Test with args
        r = yield command(key, start='5', end='8', withscores=True)
        t(r, l[5:9])
        # Test to ensure empty results return empty lists
        r = yield command(key, start=-20, end=-40, withscores=True)
        t(r, [])

    def _getKey(self, n=0):
        return self._KEYS[n]

    def _to_words(self, n):
        l = []
        while True:
            n, r = divmod(n, 10)
            l.append(self._NUMBERS[r])
            if n == 0:
                break
        return ' '.join(l)

    def _sorted_set_check(self, r, l):
        self.assertEqual(r, len(l))
        return r, l

    def _make_sorted_set(self, key, begin=0, end=10):
        l = []
        for x in range(begin, end):
            l.extend((x, self._to_words(x)))
        return self.db.zadd(key, *l).addCallback(
            self._sorted_set_check, zip(l[1::2], l[::2]))

    @defer.inlineCallbacks
    def setUp(self):
        self.db = yield redis.Connection(redis_host, redis_port,
                                         reconnect=False)

    def tearDown(self):
        return defer.gatherResults(
            [self.db.delete(x) for x in self._KEYS]).addCallback(
                lambda ign: self.db.disconnect())

    def _check_invaliddata_error(self, response, shouldError=False):
        if shouldError:
            self.assertIsInstance(response, Failure)
            self.assertIsInstance(response.value, redis.InvalidData)
        else:
            self.assertNotIsInstance(response, Failure)

########NEW FILE########
__FILENAME__ = test_subscriber
import txredisapi as redis
from twisted.internet import defer, reactor
from twisted.trial import unittest

redis_host = "localhost"
redis_port = 6379

class TestSubscriberProtocol(unittest.TestCase):
    @defer.inlineCallbacks
    def setUp(self):
        factory = redis.SubscriberFactory()
        factory.continueTrying = False
        reactor.connectTCP(redis_host, redis_port, factory)
        self.db = yield factory.deferred

    @defer.inlineCallbacks
    def tearDown(self):
        yield self.db.disconnect()

    @defer.inlineCallbacks
    def testDisconnectErrors(self):
        # Slightly dirty, but we want a reference to the actual
        # protocol instance
        conn = yield self.db._factory.getConnection(True)

        # This should return a deferred from the replyQueue; then
        # loseConnection will make it do an errback with a
        # ConnectionError instance
        d = self.db.subscribe('foo')

        conn.transport.loseConnection()
        try:
            yield d
            self.fail()
        except redis.ConnectionError:
            pass

        # This should immediately errback with a ConnectionError
        # instance when getConnection finds 0 active instances in the
        # factory
        try:
            yield self.db.subscribe('bar')
            self.fail()
        except redis.ConnectionError:
            pass

        # This should immediately raise a ConnectionError instance
        # when execute_command() finds that the connection is not
        # connected
        try:
            yield conn.subscribe('baz')
            self.fail()
        except redis.ConnectionError:
            pass

    @defer.inlineCallbacks
    def testSubscribe(self):
        reply = yield self.db.subscribe("test_subscribe1")
        self.assertEqual(reply, [u"subscribe", u"test_subscribe1", 1])

        reply = yield self.db.subscribe("test_subscribe2")
        self.assertEqual(reply, [u"subscribe", u"test_subscribe2", 2])

    @defer.inlineCallbacks
    def testUnsubscribe(self):
        yield self.db.subscribe("test_unsubscribe1")
        yield self.db.subscribe("test_unsubscribe2")

        reply = yield self.db.unsubscribe("test_unsubscribe1")
        self.assertEqual(reply, [u"unsubscribe", u"test_unsubscribe1", 1])
        reply = yield self.db.unsubscribe("test_unsubscribe2")
        self.assertEqual(reply, [u"unsubscribe", u"test_unsubscribe2", 0])

    @defer.inlineCallbacks
    def testPSubscribe(self):
        reply = yield self.db.psubscribe("test_psubscribe1.*")
        self.assertEqual(reply, [u"psubscribe", u"test_psubscribe1.*", 1])

        reply = yield self.db.psubscribe("test_psubscribe2.*")
        self.assertEqual(reply, [u"psubscribe", u"test_psubscribe2.*", 2])

    @defer.inlineCallbacks
    def testPUnsubscribe(self):
        yield self.db.psubscribe("test_punsubscribe1.*")
        yield self.db.psubscribe("test_punsubscribe2.*")

        reply = yield self.db.punsubscribe("test_punsubscribe1.*")
        self.assertEqual(reply, [u"punsubscribe", u"test_punsubscribe1.*", 1])
        reply = yield self.db.punsubscribe("test_punsubscribe2.*")
        self.assertEqual(reply, [u"punsubscribe", u"test_punsubscribe2.*", 0])

########NEW FILE########
__FILENAME__ = test_transactions
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import txredisapi
from twisted.trial import unittest
from twisted.internet import defer, reactor
from twisted.python import log                                                  
import sys

log.startLogging(sys.stdout)

redis_host="localhost"
redis_port=6379

class TestRedisConnections(unittest.TestCase):
    @defer.inlineCallbacks
    def testRedisConnection(self):
        rapi = yield txredisapi.Connection(redis_host, redis_port)
        
        # test set() operation
        transaction = yield rapi.multi("txredisapi:test_transaction")
        self.assertTrue(transaction.inTransaction)
        for key, value in (("txredisapi:test_transaction", "foo"), ("txredisapi:test_transaction", "bar")):
            yield transaction.set(key, value)
        yield transaction.commit()
        self.assertFalse(transaction.inTransaction)
        result = yield rapi.get("txredisapi:test_transaction")
        self.assertEqual(result, "bar")

        yield rapi.disconnect()

    @defer.inlineCallbacks
    def testRedisWithOnlyWatchUnwatch(self):
        rapi = yield txredisapi.Connection(redis_host, redis_port)

        k = "txredisapi:testRedisWithOnlyWatchAndUnwatch"
        tx = yield rapi.watch(k)
        self.assertTrue(tx.inTransaction)
        yield tx.set(k, "bar")
        v = yield tx.get(k)
        self.assertEqual("bar", v)
        yield tx.unwatch()
        self.assertFalse(tx.inTransaction)

        yield rapi.disconnect()

    @defer.inlineCallbacks
    def testRedisWithWatchAndMulti(self):
        rapi = yield txredisapi.Connection(redis_host, redis_port)

        tx = yield rapi.watch("txredisapi:testRedisWithWatchAndMulti")
        yield tx.multi()
        yield tx.unwatch()
        self.assertTrue(tx.inTransaction)
        yield tx.commit()
        self.assertFalse(tx.inTransaction)

        yield rapi.disconnect()

    # some sort of probabilistic test
    @defer.inlineCallbacks
    def testWatchAndPools_1(self):
        rapi = yield txredisapi.ConnectionPool(redis_host, redis_port, poolsize=2, reconnect=False)
        tx1 = yield rapi.watch("foobar")
        tx2 = yield tx1.watch("foobaz")
        self.assertTrue(id(tx1) == id(tx2))
        yield rapi.disconnect()

    # some sort of probabilistic test
    @defer.inlineCallbacks
    def testWatchAndPools_2(self):
        rapi = yield txredisapi.ConnectionPool(redis_host, redis_port, poolsize=2, reconnect=False)
        tx1 = yield rapi.watch("foobar")
        tx2 = yield rapi.watch("foobaz")
        self.assertTrue(id(tx1) != id(tx2))
        yield rapi.disconnect()

    @defer.inlineCallbacks
    def testWatchEdgeCase_1(self):
        rapi = yield txredisapi.Connection(redis_host, redis_port)

        tx = yield rapi.multi("foobar")
        yield tx.unwatch()
        self.assertTrue(tx.inTransaction)
        yield tx.discard()
        self.assertFalse(tx.inTransaction)

        yield rapi.disconnect()

    @defer.inlineCallbacks
    def testWatchEdgeCase_2(self):
        rapi = yield txredisapi.Connection(redis_host, redis_port)

        tx = yield rapi.multi()
        try:
            yield tx.watch("foobar")
        except txredisapi.ResponseError:
            pass
        yield tx.unwatch()
        self.assertTrue(tx.inTransaction)
        yield tx.discard()
        self.assertFalse(tx.inTransaction)
        yield rapi.disconnect()

    @defer.inlineCallbacks
    def testWatchEdgeCase_3(self):
        rapi = yield txredisapi.Connection(redis_host, redis_port)

        tx = yield rapi.watch("foobar")
        tx = yield tx.multi("foobaz")
        yield tx.unwatch()
        self.assertTrue(tx.inTransaction)
        yield tx.discard()
        self.assertFalse(tx.inTransaction)

        yield rapi.disconnect()

########NEW FILE########
__FILENAME__ = test_unix_connection
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import txredisapi as redis

from twisted.internet import base
from twisted.internet import defer
from twisted.trial import unittest

base.DelayedCall.debug = False
redis_sock = "/tmp/redis.sock"


class TestUnixConnectionMethods(unittest.TestCase):
    @defer.inlineCallbacks
    def test_UnixConnection(self):
        db = yield redis.UnixConnection(redis_sock, reconnect=False)
        self.assertEqual(isinstance(db, redis.UnixConnectionHandler), True)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_UnixConnectionDB1(self):
        db = yield redis.UnixConnection(redis_sock, dbid=1, reconnect=False)
        self.assertEqual(isinstance(db, redis.UnixConnectionHandler), True)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_UnixConnectionPool(self):
        db = yield redis.UnixConnectionPool(redis_sock, poolsize=2,
                                            reconnect=False)
        self.assertEqual(isinstance(db, redis.UnixConnectionHandler), True)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_lazyUnixConnection(self):
        db = redis.lazyUnixConnection(redis_sock, reconnect=False)
        self.assertEqual(isinstance(db._connected, defer.Deferred), True)
        db = yield db._connected
        self.assertEqual(isinstance(db, redis.UnixConnectionHandler), True)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_lazyUnixConnectionPool(self):
        db = redis.lazyUnixConnectionPool(redis_sock, reconnect=False)
        self.assertEqual(isinstance(db._connected, defer.Deferred), True)
        db = yield db._connected
        self.assertEqual(isinstance(db, redis.UnixConnectionHandler), True)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_ShardedUnixConnection(self):
        paths = [redis_sock]
        db = yield redis.ShardedUnixConnection(paths, reconnect=False)
        self.assertEqual(isinstance(db,
                                    redis.ShardedUnixConnectionHandler), True)
        yield db.disconnect()

    @defer.inlineCallbacks
    def test_ShardedUnixConnectionPool(self):
        paths = [redis_sock]
        db = yield redis.ShardedUnixConnectionPool(paths, reconnect=False)
        self.assertEqual(isinstance(db,
                                    redis.ShardedUnixConnectionHandler), True)
        yield db.disconnect()

if not os.path.exists(redis_sock):
    TestUnixConnectionMethods.skip = True

########NEW FILE########
__FILENAME__ = test_watch
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import txredisapi as redis
from twisted.internet import defer
from twisted.python.failure import Failure
from twisted.trial import unittest

redis_host = "localhost"
redis_port = 6379


class TestRedisConnections(unittest.TestCase):
    _KEYS = ['txredisapi:testwatch1', 'txredisapi:testwatch2']

    @defer.inlineCallbacks
    def setUp(self):
        self.connections = []
        self.db = yield self._getRedisConnection()
        yield self.db.delete(self._KEYS)

    @defer.inlineCallbacks
    def tearDown(self):
        for connection in self.connections:
            l = [connection.delete(k) for k in self._KEYS]
            yield defer.DeferredList(l)
            yield connection.disconnect()

    def _db_connected(self, connection):
        self.connections.append(connection)
        return connection

    def _getRedisConnection(self, host=redis_host, port=redis_port, db=0):
        return redis.Connection(
            host, port, dbid=db, reconnect=False).addCallback(
                self._db_connected)

    def _check_watcherror(self, response, shouldError=False):
        if shouldError:
            self.assertIsInstance(response, Failure)
            self.assertIsInstance(response.value, redis.WatchError)
        else:
            self.assertNotIsInstance(response, Failure)

    @defer.inlineCallbacks
    def testRedisWatchFail(self):
        db1 = yield self._getRedisConnection()
        yield self.db.set(self._KEYS[0], 'foo')
        t = yield self.db.multi(self._KEYS[0])
        self.assertIsInstance(t, redis.RedisProtocol)
        yield t.set(self._KEYS[1], 'bar')
        # This should trigger a failure
        yield db1.set(self._KEYS[0], 'bar1')
        yield t.commit().addBoth(self._check_watcherror, shouldError=True)

    @defer.inlineCallbacks
    def testRedisWatchSucceed(self):
        yield self.db.set(self._KEYS[0], 'foo')
        t = yield self.db.multi(self._KEYS[0])
        self.assertIsInstance(t, redis.RedisProtocol)
        yield t.set(self._KEYS[0], 'bar')
        yield t.commit().addBoth(self._check_watcherror, shouldError=False)

    @defer.inlineCallbacks
    def testRedisMultiNoArgs(self):
        yield self.db.set(self._KEYS[0], 'foo')
        t = yield self.db.multi()
        self.assertIsInstance(t, redis.RedisProtocol)
        yield t.set(self._KEYS[1], 'bar')
        yield t.commit().addBoth(self._check_watcherror, shouldError=False)

    @defer.inlineCallbacks
    def testRedisWithBulkCommands_transactions(self):
        t = yield self.db.watch(self._KEYS)
        yield t.mget(self._KEYS)
        t = yield t.multi()
        yield t.commit()
        self.assertEqual(0, t.transactions)
        self.assertFalse(t.inTransaction)

    @defer.inlineCallbacks
    def testRedisWithBulkCommands_inTransaction(self):
        t = yield self.db.watch(self._KEYS)
        yield t.mget(self._KEYS)
        self.assertTrue(t.inTransaction)
        yield t.unwatch()

    @defer.inlineCallbacks
    def testRedisWithBulkCommands_mget(self):
        yield self.db.set(self._KEYS[0], "foo")
        yield self.db.set(self._KEYS[1], "bar")

        m0 = yield self.db.mget(self._KEYS)
        t = yield self.db.watch(self._KEYS)
        m1 = yield t.mget(self._KEYS)
        t = yield t.multi()
        yield t.mget(self._KEYS)
        (m2,) = yield t.commit()

        self.assertEqual(["foo", "bar"], m0)
        self.assertEqual(m0, m1)
        self.assertEqual(m0, m2)

    @defer.inlineCallbacks
    def testRedisWithBulkCommands_hgetall(self):
        yield self.db.hset(self._KEYS[0], "foo", "bar")
        yield self.db.hset(self._KEYS[0], "bar", "foo")

        h0 = yield self.db.hgetall(self._KEYS[0])
        t = yield self.db.watch(self._KEYS[0])
        h1 = yield t.hgetall(self._KEYS[0])
        t = yield t.multi()
        yield t.hgetall(self._KEYS[0])
        (h2,) = yield t.commit()

        self.assertEqual({"foo": "bar", "bar": "foo"}, h0)
        self.assertEqual(h0, h1)
        self.assertEqual(h0, h2)

########NEW FILE########
__FILENAME__ = txredisapi
# coding: utf-8
# Copyright 2009 Alexandre Fiori
# https://github.com/fiorix/txredisapi
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# Credits:
#   The Protocol class is an improvement of txRedis' protocol,
#   by Dorian Raymer and Ludovico Magnocavallo.
#
#   Sharding and Consistent Hashing implementation by Gleicon Moraes.
#

import bisect
import collections
import functools
import operator
import re
import types
import warnings
import zlib
import string
import hashlib

from twisted.internet import defer
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.internet import task
from twisted.protocols import basic
from twisted.protocols import policies
from twisted.python import log
from twisted.python.failure import Failure


class RedisError(Exception):
    pass


class ConnectionError(RedisError):
    pass


class ResponseError(RedisError):
    pass


class ScriptDoesNotExist(ResponseError):
    pass


class NoScriptRunning(ResponseError):
    pass


class InvalidResponse(RedisError):
    pass


class InvalidData(RedisError):
    pass


class WatchError(RedisError):
    pass


def list_or_args(command, keys, args):
    oldapi = bool(args)
    try:
        iter(keys)
        if isinstance(keys, (str, unicode)):
            raise TypeError
    except TypeError:
        oldapi = True
        keys = [keys]

    if oldapi:
        warnings.warn(DeprecationWarning(
            "Passing *args to redis.%s is deprecated. "
            "Pass an iterable to ``keys`` instead" % command))
        keys.extend(args)
    return keys

# Possible first characters in a string containing an integer or a float.
_NUM_FIRST_CHARS = frozenset(string.digits + "+-.")


class MultiBulkStorage(object):
    def __init__(self, parent=None):
        self.items = None
        self.pending = None
        self.parent = parent

    def set_pending(self, pending):
        if self.pending is None:
            if pending < 0:
                self.items = None
                self.pending = 0
            else:
                self.items = []
                self.pending = pending
            return self
        else:
            m = MultiBulkStorage(self)
            m.set_pending(pending)
            return m

    def append(self, item):
        self.pending -= 1
        self.items.append(item)


class LineReceiver(protocol.Protocol, basic._PauseableMixin):
    line_mode = 1
    __buffer = ''
    delimiter = '\r\n'
    MAX_LENGTH = 16384

    def clearLineBuffer(self):
        b = self.__buffer
        self.__buffer = ""
        return b

    def dataReceived(self, data, unpause=False):
        if unpause is True:
            if self.__buffer:
                self.__buffer = data + self.__buffer
            else:
                self.__buffer += data

            self.resumeProducing()
        else:
            self.__buffer = self.__buffer + data

        while self.line_mode and not self.paused:
            try:
                line, self.__buffer = self.__buffer.split(self.delimiter, 1)
            except ValueError:
                if len(self.__buffer) > self.MAX_LENGTH:
                    line, self.__buffer = self.__buffer, ''
                    return self.lineLengthExceeded(line)
                break
            else:
                linelength = len(line)
                if linelength > self.MAX_LENGTH:
                    exceeded = line + self.__buffer
                    self.__buffer = ''
                    return self.lineLengthExceeded(exceeded)
                why = self.lineReceived(line)
                if why or self.transport and self.transport.disconnecting:
                    return why
        else:
            if not self.paused:
                data = self.__buffer
                self.__buffer = ''
                if data:
                    return self.rawDataReceived(data)

    def setLineMode(self, extra=''):
        self.line_mode = 1
        if extra:
            self.pauseProducing()
            reactor.callLater(0, self.dataReceived, extra, True)

    def setRawMode(self):
        self.line_mode = 0

    def rawDataReceived(self, data):
        raise NotImplementedError

    def lineReceived(self, line):
        raise NotImplementedError

    def sendLine(self, line):
        return self.transport.write(line + self.delimiter)

    def lineLengthExceeded(self, line):
        return self.transport.loseConnection()


class RedisProtocol(LineReceiver, policies.TimeoutMixin):
    """
    Redis client protocol.
    """

    def __init__(self, charset="utf-8", errors="strict"):
        self.charset = charset
        self.errors = errors

        self.bulk_length = 0
        self.bulk_buffer = []

        self.post_proc = []
        self.multi_bulk = MultiBulkStorage()

        self.replyQueue = defer.DeferredQueue()

        self.transactions = 0
        self.inTransaction = False
        self.unwatch_cc = lambda: ()
        self.commit_cc = lambda: ()

        self.script_hashes = set()

        self.pipelining = False
        self.pipelined_commands = []
        self.pipelined_replies = []

    @defer.inlineCallbacks
    def connectionMade(self):
        if self.factory.password is not None:
            try:
                response = yield self.auth(self.factory.password)
                if isinstance(response, ResponseError):
                    raise response
            except Exception, e:
                self.factory.continueTrying = False
                self.transport.loseConnection()

                msg = "Redis error: could not auth: %s" % (str(e))
                self.factory.connectionError(msg)
                if self.factory.isLazy:
                    log.msg(msg)
                defer.returnValue(None)

        if self.factory.dbid is not None:
            try:
                response = yield self.select(self.factory.dbid)
                if isinstance(response, ResponseError):
                    raise response
            except Exception, e:
                self.factory.continueTrying = False
                self.transport.loseConnection()

                msg = "Redis error: could not set dbid=%s: %s" % \
                      (self.factory.dbid, str(e))
                self.factory.connectionError(msg)
                if self.factory.isLazy:
                    log.msg(msg)
                defer.returnValue(None)

        self.connected = 1
        self.factory.addConnection(self)

    def connectionLost(self, why):
        self.connected = 0
        self.script_hashes.clear()
        self.factory.delConnection(self)
        LineReceiver.connectionLost(self, why)
        while self.replyQueue.waiting:
            self.replyReceived(ConnectionError("Lost connection"))

    def lineReceived(self, line):
        """
        Reply types:
          "-" error message
          "+" single line status reply
          ":" integer number (protocol level only?)
          "$" bulk data
          "*" multi-bulk data
        """
        if line:
            self.resetTimeout()
            token, data = line[0], line[1:]
        else:
            return

        if token == "$":  # bulk data
            try:
                self.bulk_length = long(data)
            except ValueError:
                self.replyReceived(InvalidResponse("Cannot convert data "
                                                   "'%s' to integer" % data))
            else:
                if self.bulk_length == -1:
                    self.bulk_length = 0
                    self.bulkDataReceived(None)
                else:
                    self.bulk_length += 2  # 2 == \r\n
                    self.setRawMode()

        elif token == "*":  # multi-bulk data
            try:
                n = long(data)
            except (TypeError, ValueError):
                self.multi_bulk = MultiBulkStorage()
                self.replyReceived(InvalidResponse("Cannot convert "
                                                   "multi-response header "
                                                   "'%s' to integer" % data))
            else:
                self.multi_bulk = self.multi_bulk.set_pending(n)
                if n in (0, -1):
                    self.multiBulkDataReceived()

        elif token == "+":  # single line status
            if data == "QUEUED":
                self.transactions += 1
                self.replyReceived(data)
            else:
                if self.multi_bulk.pending:
                    self.handleMultiBulkElement(data)
                else:
                    self.replyReceived(data)

        elif token == "-":  # error
            reply = ResponseError(data[4:] if data[:4] == "ERR" else data)
            if self.multi_bulk.pending:
                self.handleMultiBulkElement(reply)
            else:
                self.replyReceived(reply)

        elif token == ":":  # integer
            try:
                reply = int(data)
            except ValueError:
                reply = InvalidResponse(
                    "Cannot convert data '%s' to integer" % data)

            if self.multi_bulk.pending:
                self.handleMultiBulkElement(reply)
            else:
                self.replyReceived(reply)

    def rawDataReceived(self, data):
        """
        Process and dispatch to bulkDataReceived.
        """
        if self.bulk_length:
            data, rest = data[:self.bulk_length], data[self.bulk_length:]
            self.bulk_length -= len(data)
        else:
            rest = ""

        self.bulk_buffer.append(data)
        if self.bulk_length == 0:
            bulk_buffer = "".join(self.bulk_buffer)[:-2]
            self.bulk_buffer = []
            self.bulkDataReceived(bulk_buffer)
            self.setLineMode(extra=rest)

    def bulkDataReceived(self, data):
        """
        Receipt of a bulk data element.
        """
        el = None
        if data is not None:
            if data and data[0] in _NUM_FIRST_CHARS:  # Most likely a number
                try:
                    el = int(data) if data.find('.') == -1 else float(data)
                except ValueError:
                    pass

            if el is None:
                el = data
                if self.charset is not None:
                    try:
                        el = data.decode(self.charset)
                    except UnicodeDecodeError:
                        pass

        if self.multi_bulk.pending or self.multi_bulk.items:
            self.handleMultiBulkElement(el)
        else:
            self.replyReceived(el)

    def handleMultiBulkElement(self, element):
        self.multi_bulk.append(element)

        if not self.multi_bulk.pending:
            self.multiBulkDataReceived()

    def multiBulkDataReceived(self):
        """
        Receipt of list or set of bulk data elements.
        """
        while self.multi_bulk.parent and not self.multi_bulk.pending:
            p = self.multi_bulk.parent
            p.append(self.multi_bulk.items)
            self.multi_bulk = p

        if not self.multi_bulk.pending:
            reply = self.multi_bulk.items
            self.multi_bulk = MultiBulkStorage()

            if self.inTransaction and reply is not None: # watch or multi has been called
                if self.transactions > 0:
                    self.transactions -= len(reply)      # multi: this must be an exec [commit] reply
                if self.transactions == 0:
                    self.commit_cc()
                if self.inTransaction:                   # watch but no multi: process the reply as usual
                    f = self.post_proc[1:]
                    if len(f) == 1 and callable(f[0]):
                        reply = f[0](reply)
                else:                                    # multi: this must be an exec reply
                    tmp = []
                    for f, v in zip(self.post_proc[1:], reply):
                        if callable(f):
                            tmp.append(f(v))
                        else:
                            tmp.append(v)
                        reply = tmp
                self.post_proc = []

            self.replyReceived(reply)

    def replyReceived(self, reply):
        """
        Complete reply received and ready to be pushed to the requesting
        function.
        """
        self.replyQueue.put(reply)

    @staticmethod
    def handle_reply(r):
        if isinstance(r, Exception):
            raise r
        return r

    def execute_command(self, *args, **kwargs):
        if self.connected == 0:
            raise ConnectionError("Not connected")
        else:

            # Build the redis command.
            cmds = []
            cmd_template = "$%s\r\n%s\r\n"
            for s in args:
                if isinstance(s, str):
                    cmd = s
                elif isinstance(s, unicode):
                    if self.charset is None:
                        raise InvalidData("Encoding charset was not specified")
                    try:
                        cmd = s.encode(self.charset, self.errors)
                    except UnicodeEncodeError, e:
                        raise InvalidData(
                            "Error encoding unicode value '%s': %s" %
                            (repr(s), e))
                elif isinstance(s, float):
                    try:
                        cmd = format(s, "f")
                    except NameError:
                        cmd = "%0.6f" % s
                else:
                    cmd = str(s)
                cmds.append(cmd_template % (len(cmd), cmd))
            command = "*%s\r\n%s" % (len(cmds), "".join(cmds))

            # When pipelining, buffer this command into our list of
            # pipelined commands. Otherwise, write the command immediately.
            if self.pipelining:
                self.pipelined_commands.append(command)
            else:
                self.transport.write(command)

            # Return deferred that will contain the result of this command.
            # Note: when using pipelining, this deferred will NOT return
            # until after execute_pipeline is called.
            r = self.replyQueue.get().addCallback(self.handle_reply)

            # When pipelining, we need to keep track of the deferred replies
            # so that we can wait for them in a DeferredList when
            # execute_pipeline is called.
            if self.pipelining:
                self.pipelined_replies.append(r)

            if self.inTransaction:
                self.post_proc.append(kwargs.get("post_proc"))
            else:
                if "post_proc" in kwargs:
                    f = kwargs["post_proc"]
                    if callable(f):
                        r.addCallback(f)

            return r

    ##
    # REDIS COMMANDS
    ##

    # Connection handling
    def quit(self):
        """
        Close the connection
        """
        self.factory.continueTrying = False
        return self.execute_command("QUIT")

    def auth(self, password):
        """
        Simple password authentication if enabled
        """
        return self.execute_command("AUTH", password)

    def ping(self):
        """
        Ping the server
        """
        return self.execute_command("PING")

    # Commands operating on all value types
    def exists(self, key):
        """
        Test if a key exists
        """
        return self.execute_command("EXISTS", key)

    def delete(self, keys, *args):
        """
        Delete one or more keys
        """
        keys = list_or_args("delete", keys, args)
        return self.execute_command("DEL", *keys)

    def type(self, key):
        """
        Return the type of the value stored at key
        """
        return self.execute_command("TYPE", key)

    def keys(self, pattern="*"):
        """
        Return all the keys matching a given pattern
        """
        return self.execute_command("KEYS", pattern)

    def randomkey(self):
        """
        Return a random key from the key space
        """
        return self.execute_command("RANDOMKEY")

    def rename(self, oldkey, newkey):
        """
        Rename the old key in the new one,
        destroying the newname key if it already exists
        """
        return self.execute_command("RENAME", oldkey, newkey)

    def renamenx(self, oldkey, newkey):
        """
        Rename the oldname key to newname,
        if the newname key does not already exist
        """
        return self.execute_command("RENAMENX", oldkey, newkey)

    def dbsize(self):
        """
        Return the number of keys in the current db
        """
        return self.execute_command("DBSIZE")

    def expire(self, key, time):
        """
        Set a time to live in seconds on a key
        """
        return self.execute_command("EXPIRE", key, time)

    def persist(self, key):
        """
        Remove the expire from a key
        """
        return self.execute_command("PERSIST", key)

    def ttl(self, key):
        """
        Get the time to live in seconds of a key
        """
        return self.execute_command("TTL", key)

    def select(self, index):
        """
        Select the DB with the specified index
        """
        return self.execute_command("SELECT", index)

    def move(self, key, dbindex):
        """
        Move the key from the currently selected DB to the dbindex DB
        """
        return self.execute_command("MOVE", key, dbindex)

    def flush(self, all_dbs=False):
        warnings.warn(DeprecationWarning(
            "redis.flush() has been deprecated, "
            "use redis.flushdb() or redis.flushall() instead"))
        return all_dbs and self.flushall() or self.flushdb()

    def flushdb(self):
        """
        Remove all the keys from the currently selected DB
        """
        return self.execute_command("FLUSHDB")

    def flushall(self):
        """
        Remove all the keys from all the databases
        """
        return self.execute_command("FLUSHALL")

    # Commands operating on string values
    def set(self, key, value, expire=None, pexpire=None,
            only_if_not_exists=False, only_if_exists=False):
        """
        Set a key to a string value
        """
        args = []
        if expire is not None:
            args.extend(("EX", expire))
        if pexpire is not None:
            args.extend(("PX", pexpire))
        if only_if_not_exists and only_if_exists:
            raise RedisError("only_if_not_exists and only_if_exists "
                             "cannot be true simultaneously")
        if only_if_not_exists:
            args.append("NX")
        if only_if_exists:
            args.append("XX")
        return self.execute_command("SET", key, value, *args)

    def get(self, key):
        """
        Return the string value of the key
        """
        return self.execute_command("GET", key)

    def getbit(self, key, offset):
        """
        Return the bit value at offset in the string value stored at key
        """
        return self.execute_command("GETBIT", key, offset)

    def getset(self, key, value):
        """
        Set a key to a string returning the old value of the key
        """
        return self.execute_command("GETSET", key, value)

    def mget(self, keys, *args):
        """
        Multi-get, return the strings values of the keys
        """
        keys = list_or_args("mget", keys, args)
        return self.execute_command("MGET", *keys)

    def setbit(self, key, offset, value):
        """
        Sets or clears the bit at offset in the string value stored at key
        """
        if isinstance(value, bool):
            value = int(value)
        return self.execute_command("SETBIT", key, offset, value)

    def setnx(self, key, value):
        """
        Set a key to a string value if the key does not exist
        """
        return self.execute_command("SETNX", key, value)

    def setex(self, key, time, value):
        """
        Set+Expire combo command
        """
        return self.execute_command("SETEX", key, time, value)

    def mset(self, mapping):
        """
        Set the respective fields to the respective values.
        HMSET replaces old values with new values.
        """
        items = []
        for pair in mapping.iteritems():
            items.extend(pair)
        return self.execute_command("MSET", *items)

    def msetnx(self, mapping):
        """
        Set multiple keys to multiple values in a single atomic
        operation if none of the keys already exist
        """
        items = []
        for pair in mapping.iteritems():
            items.extend(pair)
        return self.execute_command("MSETNX", *items)

    def bitop(self, operation, destkey, *srckeys):
        """
        Perform a bitwise operation between multiple keys
        and store the result in the destination key.
        """
        srclen = len(srckeys)
        if srclen == 0:
            return defer.fail(RedisError("no ``srckeys`` specified"))
        if isinstance(operation, (str, unicode)):
            operation = operation.upper()
        elif operation is operator.and_ or operation is operator.__and__:
            operation = 'AND'
        elif operation is operator.or_ or operation is operator.__or__:
            operation = 'OR'
        elif operation is operator.__xor__ or operation is operator.xor:
            operation = 'XOR'
        elif operation is operator.__not__ or operation is operator.not_:
            operation = 'NOT'
        if operation not in ('AND', 'OR', 'XOR', 'NOT'):
            return defer.fail(InvalidData(
                "Invalid operation: %s" % operation))
        if operation == 'NOT' and srclen > 1:
            return defer.fail(RedisError(
                "bitop NOT takes only one ``srckey``"))
        return self.execute_command('BITOP', operation, destkey, *srckeys)

    def bitcount(self, key, start=None, end=None):
        if (end is None and start is not None) or \
                (start is None and end is not None):
            raise RedisError("``start`` and ``end`` must both be specified")
        if start is not None:
            t = (start, end)
        else:
            t = ()
        return self.execute_command("BITCOUNT", key, *t)

    def incr(self, key, amount=1):
        """
        Increment the integer value of key
        """
        return self.execute_command("INCRBY", key, amount)

    def incrby(self, key, amount):
        """
        Increment the integer value of key by integer
        """
        return self.incr(key, amount)

    def decr(self, key, amount=1):
        """
        Decrement the integer value of key
        """
        return self.execute_command("DECRBY", key, amount)

    def decrby(self, key, amount):
        """
        Decrement the integer value of key by integer
        """
        return self.decr(key, amount)

    def append(self, key, value):
        """
        Append the specified string to the string stored at key
        """
        return self.execute_command("APPEND", key, value)

    def substr(self, key, start, end=-1):
        """
        Return a substring of a larger string
        """
        return self.execute_command("SUBSTR", key, start, end)

    # Commands operating on lists
    def push(self, key, value, tail=False):
        warnings.warn(DeprecationWarning(
            "redis.push() has been deprecated, "
            "use redis.lpush() or redis.rpush() instead"))

        return tail and self.rpush(key, value) or self.lpush(key, value)

    def rpush(self, key, value):
        """
        Append an element to the tail of the List value at key
        """
        if isinstance(value, tuple) or isinstance(value, list):
            return self.execute_command("RPUSH", key, *value)
        else:
            return self.execute_command("RPUSH", key, value)

    def lpush(self, key, value):
        """
        Append an element to the head of the List value at key
        """
        if isinstance(value, tuple) or isinstance(value, list):
            return self.execute_command("LPUSH", key, *value)
        else:
            return self.execute_command("LPUSH", key, value)

    def llen(self, key):
        """
        Return the length of the List value at key
        """
        return self.execute_command("LLEN", key)

    def lrange(self, key, start, end):
        """
        Return a range of elements from the List at key
        """
        return self.execute_command("LRANGE", key, start, end)

    def ltrim(self, key, start, end):
        """
        Trim the list at key to the specified range of elements
        """
        return self.execute_command("LTRIM", key, start, end)

    def lindex(self, key, index):
        """
        Return the element at index position from the List at key
        """
        return self.execute_command("LINDEX", key, index)

    def lset(self, key, index, value):
        """
        Set a new value as the element at index position of the List at key
        """
        return self.execute_command("LSET", key, index, value)

    def lrem(self, key, count, value):
        """
        Remove the first-N, last-N, or all the elements matching value
        from the List at key
        """
        return self.execute_command("LREM", key, count, value)

    def pop(self, key, tail=False):
        warnings.warn(DeprecationWarning(
            "redis.pop() has been deprecated, "
            "user redis.lpop() or redis.rpop() instead"))

        return tail and self.rpop(key) or self.lpop(key)

    def lpop(self, key):
        """
        Return and remove (atomically) the first element of the List at key
        """
        return self.execute_command("LPOP", key)

    def rpop(self, key):
        """
        Return and remove (atomically) the last element of the List at key
        """
        return self.execute_command("RPOP", key)

    def blpop(self, keys, timeout=0):
        """
        Blocking LPOP
        """
        if isinstance(keys, (str, unicode)):
            keys = [keys]
        else:
            keys = list(keys)

        keys.append(timeout)
        return self.execute_command("BLPOP", *keys)

    def brpop(self, keys, timeout=0):
        """
        Blocking RPOP
        """
        if isinstance(keys, (str, unicode)):
            keys = [keys]
        else:
            keys = list(keys)

        keys.append(timeout)
        return self.execute_command("BRPOP", *keys)

    def brpoplpush(self, source, destination, timeout = 0):
        """
        Pop a value from a list, push it to another list and return
        it; or block until one is available.
        """
        return self.execute_command("BRPOPLPUSH", source, destination, timeout)

    def rpoplpush(self, srckey, dstkey):
        """
        Return and remove (atomically) the last element of the source
        List  stored at srckey and push the same element to the
        destination List stored at dstkey
        """
        return self.execute_command("RPOPLPUSH", srckey, dstkey)

    def _make_set(self, result):
        if isinstance(result, list):
            return set(result)
        return result

    # Commands operating on sets
    def sadd(self, key, members, *args):
        """
        Add the specified member to the Set value at key
        """
        members = list_or_args("sadd", members, args)
        return self.execute_command("SADD", key, *members)

    def srem(self, key, members, *args):
        """
        Remove the specified member from the Set value at key
        """
        members = list_or_args("srem", members, args)
        return self.execute_command("SREM", key, *members)

    def spop(self, key):
        """
        Remove and return (pop) a random element from the Set value at key
        """
        return self.execute_command("SPOP", key)

    def smove(self, srckey, dstkey, member):
        """
        Move the specified member from one Set to another atomically
        """
        return self.execute_command(
            "SMOVE", srckey, dstkey, member).addCallback(bool)

    def scard(self, key):
        """
        Return the number of elements (the cardinality) of the Set at key
        """
        return self.execute_command("SCARD", key)

    def sismember(self, key, value):
        """
        Test if the specified value is a member of the Set at key
        """
        return self.execute_command("SISMEMBER", key, value).addCallback(bool)

    def sinter(self, keys, *args):
        """
        Return the intersection between the Sets stored at key1, ..., keyN
        """
        keys = list_or_args("sinter", keys, args)
        return self.execute_command("SINTER", *keys).addCallback(
            self._make_set)

    def sinterstore(self, dstkey, keys, *args):
        """
        Compute the intersection between the Sets stored
        at key1, key2, ..., keyN, and store the resulting Set at dstkey
        """
        keys = list_or_args("sinterstore", keys, args)
        return self.execute_command("SINTERSTORE", dstkey, *keys)

    def sunion(self, keys, *args):
        """
        Return the union between the Sets stored at key1, key2, ..., keyN
        """
        keys = list_or_args("sunion", keys, args)
        return self.execute_command("SUNION", *keys).addCallback(
            self._make_set)

    def sunionstore(self, dstkey, keys, *args):
        """
        Compute the union between the Sets stored
        at key1, key2, ..., keyN, and store the resulting Set at dstkey
        """
        keys = list_or_args("sunionstore", keys, args)
        return self.execute_command("SUNIONSTORE", dstkey, *keys)

    def sdiff(self, keys, *args):
        """
        Return the difference between the Set stored at key1 and
        all the Sets key2, ..., keyN
        """
        keys = list_or_args("sdiff", keys, args)
        return self.execute_command("SDIFF", *keys).addCallback(
            self._make_set)

    def sdiffstore(self, dstkey, keys, *args):
        """
        Compute the difference between the Set key1 and all the
        Sets key2, ..., keyN, and store the resulting Set at dstkey
        """
        keys = list_or_args("sdiffstore", keys, args)
        return self.execute_command("SDIFFSTORE", dstkey, *keys)

    def smembers(self, key):
        """
        Return all the members of the Set value at key
        """
        return self.execute_command("SMEMBERS", key).addCallback(
            self._make_set)

    def srandmember(self, key):
        """
        Return a random member of the Set value at key
        """
        return self.execute_command("SRANDMEMBER", key)

    # Commands operating on sorted zsets (sorted sets)
    def zadd(self, key, score, member, *args):
        """
        Add the specified member to the Sorted Set value at key
        or update the score if it already exist
        """
        if args:
            # Args should be pairs (have even number of elements)
            if len(args) % 2:
                return defer.fail(InvalidData(
                    "Invalid number of arguments to ZADD"))
            else:
                l = [score, member]
                l.extend(args)
                args = l
        else:
            args = [score, member]
        return self.execute_command("ZADD", key, *args)

    def zrem(self, key, *args):
        """
        Remove the specified member from the Sorted Set value at key
        """
        return self.execute_command("ZREM", key, *args)

    def zincr(self, key, member):
        return self.zincrby(key, 1, member)

    def zdecr(self, key, member):
        return self.zincrby(key, -1, member)

    def zincrby(self, key, increment, member):
        """
        If the member already exists increment its score by increment,
        otherwise add the member setting increment as score
        """
        return self.execute_command("ZINCRBY", key, increment, member)

    def zrank(self, key, member):
        """
        Return the rank (or index) or member in the sorted set at key,
        with scores being ordered from low to high
        """
        return self.execute_command("ZRANK", key, member)

    def zrevrank(self, key, member):
        """
        Return the rank (or index) or member in the sorted set at key,
        with scores being ordered from high to low
        """
        return self.execute_command("ZREVRANK", key, member)

    def _handle_withscores(self, r):
        if isinstance(r, list):
            # Return a list tuples of form (value, score)
            return zip(r[::2], r[1::2])
        return r

    def _zrange(self, key, start, end, withscores, reverse):
        if reverse:
            cmd = "ZREVRANGE"
        else:
            cmd = "ZRANGE"
        if withscores:
            pieces = (cmd, key, start, end, "WITHSCORES")
        else:
            pieces = (cmd, key, start, end)
        r = self.execute_command(*pieces)
        if withscores:
            r.addCallback(self._handle_withscores)
        return r

    def zrange(self, key, start=0, end=-1, withscores=False):
        """
        Return a range of elements from the sorted set at key
        """
        return self._zrange(key, start, end, withscores, False)

    def zrevrange(self, key, start=0, end=-1, withscores=False):
        """
        Return a range of elements from the sorted set at key,
        exactly like ZRANGE, but the sorted set is ordered in
        traversed in reverse order, from the greatest to the smallest score
        """
        return self._zrange(key, start, end, withscores, True)

    def _zrangebyscore(self, key, min, max, withscores, offset, count, rev):
        if rev:
            cmd = "ZREVRANGEBYSCORE"
        else:
            cmd = "ZRANGEBYSCORE"
        if (offset is None) != (count is None):  # XNOR
            return defer.fail(InvalidData(
                "Invalid count and offset arguments to %s" % cmd))
        if withscores:
            pieces = [cmd, key, min, max, "WITHSCORES"]
        else:
            pieces = [cmd, key, min, max]
        if offset is not None and count is not None:
            pieces.extend(("LIMIT", offset, count))
        r = self.execute_command(*pieces)
        if withscores:
            r.addCallback(self._handle_withscores)
        return r

    def zrangebyscore(self, key, min='-inf', max='+inf', withscores=False,
                      offset=None, count=None):
        """
        Return all the elements with score >= min and score <= max
        (a range query) from the sorted set
        """
        return self._zrangebyscore(key, min, max, withscores, offset,
                                   count, False)

    def zrevrangebyscore(self, key, max='+inf', min='-inf', withscores=False,
                         offset=None, count=None):
        """
        ZRANGEBYSCORE in reverse order
        """
        # ZREVRANGEBYSCORE takes max before min
        return self._zrangebyscore(key, max, min, withscores, offset,
                                   count, True)

    def zcount(self, key, min='-inf', max='+inf'):
        """
        Return the number of elements with score >= min and score <= max
        in the sorted set
        """
        if min == '-inf' and max == '+inf':
            return self.zcard(key)
        return self.execute_command("ZCOUNT", key, min, max)

    def zcard(self, key):
        """
        Return the cardinality (number of elements) of the sorted set at key
        """
        return self.execute_command("ZCARD", key)

    def zscore(self, key, element):
        """
        Return the score associated with the specified element of the sorted
        set at key
        """
        return self.execute_command("ZSCORE", key, element)

    def zremrangebyrank(self, key, min=0, max=-1):
        """
        Remove all the elements with rank >= min and rank <= max from
        the sorted set
        """
        return self.execute_command("ZREMRANGEBYRANK", key, min, max)

    def zremrangebyscore(self, key, min='-inf', max='+inf'):
        """
        Remove all the elements with score >= min and score <= max from
        the sorted set
        """
        return self.execute_command("ZREMRANGEBYSCORE", key, min, max)

    def zunionstore(self, dstkey, keys, aggregate=None):
        """
        Perform a union over a number of sorted sets with optional
        weight and aggregate
        """
        return self._zaggregate("ZUNIONSTORE", dstkey, keys, aggregate)

    def zinterstore(self, dstkey, keys, aggregate=None):
        """
        Perform an intersection over a number of sorted sets with optional
        weight and aggregate
        """
        return self._zaggregate("ZINTERSTORE", dstkey, keys, aggregate)

    def _zaggregate(self, command, dstkey, keys, aggregate):
        pieces = [command, dstkey, len(keys)]
        if isinstance(keys, dict):
            keys, weights = zip(*keys.items())
        else:
            weights = None

        pieces.extend(keys)
        if weights:
            pieces.append("WEIGHTS")
            pieces.extend(weights)

        if aggregate:
            if aggregate is min:
                aggregate = 'MIN'
            elif aggregate is max:
                aggregate = 'MAX'
            elif aggregate is sum:
                aggregate = 'SUM'
            else:
                err_flag = True
                if isinstance(aggregate, (str, unicode)):
                    aggregate_u = aggregate.upper()
                    if aggregate_u in ('MIN', 'MAX', 'SUM'):
                        aggregate = aggregate_u
                        err_flag = False
                if err_flag:
                    return defer.fail(InvalidData(
                        "Invalid aggregate function: %s" % aggregate))
            pieces.extend(("AGGREGATE", aggregate))
        return self.execute_command(*pieces)

    # Commands operating on hashes
    def hset(self, key, field, value):
        """
        Set the hash field to the specified value. Creates the hash if needed
        """
        return self.execute_command("HSET", key, field, value)

    def hsetnx(self, key, field, value):
        """
        Set the hash field to the specified value if the field does not exist.
        Creates the hash if needed
        """
        return self.execute_command("HSETNX", key, field, value)

    def hget(self, key, field):
        """
        Retrieve the value of the specified hash field.
        """
        return self.execute_command("HGET", key, field)

    def hmget(self, key, fields):
        """
        Get the hash values associated to the specified fields.
        """
        return self.execute_command("HMGET", key, *fields)

    def hmset(self, key, mapping):
        """
        Set the hash fields to their respective values.
        """
        items = []
        for pair in mapping.iteritems():
            items.extend(pair)
        return self.execute_command("HMSET", key, *items)

    def hincr(self, key, field):
        return self.hincrby(key, field, 1)

    def hdecr(self, key, field):
        return self.hincrby(key, field, -1)

    def hincrby(self, key, field, integer):
        """
        Increment the integer value of the hash at key on field with integer.
        """
        return self.execute_command("HINCRBY", key, field, integer)

    def hexists(self, key, field):
        """
        Test for existence of a specified field in a hash
        """
        return self.execute_command("HEXISTS", key, field)

    def hdel(self, key, fields):
        """
        Remove the specified field or fields from a hash
        """
        if isinstance(fields, (str, unicode)):
            fields = [fields]
        else:
            fields = list(fields)
        return self.execute_command("HDEL", key, *fields)

    def hlen(self, key):
        """
        Return the number of items in a hash.
        """
        return self.execute_command("HLEN", key)

    def hkeys(self, key):
        """
        Return all the fields in a hash.
        """
        return self.execute_command("HKEYS", key)

    def hvals(self, key):
        """
        Return all the values in a hash.
        """
        return self.execute_command("HVALS", key)

    def hgetall(self, key):
        """
        Return all the fields and associated values in a hash.
        """
        f = lambda d: dict(zip(d[::2], d[1::2]))
        return self.execute_command("HGETALL", key, post_proc=f)

    # Sorting
    def sort(self, key, start=None, end=None, by=None, get=None,
             desc=None, alpha=False, store=None):
        if (start is not None and end is None) or \
           (end is not None and start is None):
            raise RedisError("``start`` and ``end`` must both be specified")

        pieces = [key]
        if by is not None:
            pieces.append("BY")
            pieces.append(by)
        if start is not None and end is not None:
            pieces.append("LIMIT")
            pieces.append(start)
            pieces.append(end)
        if get is not None:
            pieces.append("GET")
            pieces.append(get)
        if desc:
            pieces.append("DESC")
        if alpha:
            pieces.append("ALPHA")
        if store is not None:
            pieces.append("STORE")
            pieces.append(store)

        return self.execute_command("SORT", *pieces)

    def _clear_txstate(self):
        if self.inTransaction:
            self.inTransaction = False
            self.factory.connectionQueue.put(self)

    def watch(self, keys):
        if not self.inTransaction:
            self.inTransaction = True
            self.unwatch_cc = self._clear_txstate
            self.commit_cc = lambda: ()
        if isinstance(keys, (str, unicode)):
            keys = [keys]
        d = self.execute_command("WATCH", *keys).addCallback(self._tx_started)
        return d

    def unwatch(self):
        self.unwatch_cc()
        return self.execute_command("UNWATCH")

    # Transactions
    # multi() will return a deferred with a "connection" object
    # That object must be used for further interactions within
    # the transaction. At the end, either exec() or discard()
    # must be executed.
    def multi(self, keys=None):
        self.inTransaction = True
        self.unwatch_cc = lambda: ()
        self.commit_cc = self._clear_txstate
        if keys is not None:
            d = self.watch(keys)
            d.addCallback(lambda _: self.execute_command("MULTI"))
        else:
            d = self.execute_command("MULTI")
        d.addCallback(self._tx_started)
        return d

    def _tx_started(self, response):
        if response != 'OK':
            raise RedisError('Invalid response: %s' % response)
        return self

    def _commit_check(self, response):
        if response is None:
            self.transactions = 0
            self._clear_txstate()
            raise WatchError("Transaction failed")
        else:
            return response

    def commit(self):
        if self.inTransaction is False:
            raise RedisError("Not in transaction")
        return self.execute_command("EXEC").addCallback(self._commit_check)

    def discard(self):
        if self.inTransaction is False:
            raise RedisError("Not in transaction")
        self.post_proc = []
        self.transactions = 0
        self._clear_txstate()
        return self.execute_command("DISCARD")

    # Returns a proxy that works just like .multi() except that commands
    # are simply buffered to be written all at once in a pipeline.
    # http://redis.io/topics/pipelining
    def pipeline(self):

        # Return a deferred that returns self (rather than simply self) to allow
        # ConnectionHandler to wrap this method with async connection retrieval.
        self.pipelining = True
        self.pipelined_commands = []
        self.pipelined_replies = []
        d = defer.Deferred()
        d.addCallback(lambda x: x)
        d.callback(self)
        return d

    @defer.inlineCallbacks
    def execute_pipeline(self):
        if not self.pipelining:
            raise RedisError("Not currently pipelining commands, please use pipeline() first")

        # Flush all the commands at once to redis. Wait for all replies
        # to come back using a deferred list.
        try:
            self.transport.write("".join(self.pipelined_commands))
            results = yield defer.DeferredList(
                deferredList=self.pipelined_replies,
                fireOnOneErrback=True,
                consumeErrors=True,
                )
            defer.returnValue([value for success, value in results])

        finally:
            self.pipelining = False
            self.pipelined_commands = []
            self.pipelined_replies = []

    # Publish/Subscribe
    # see the SubscriberProtocol for subscribing to channels
    def publish(self, channel, message):
        """
        Publish message to a channel
        """
        return self.execute_command("PUBLISH", channel, message)

    # Persistence control commands
    def save(self):
        """
        Synchronously save the DB on disk
        """
        return self.execute_command("SAVE")

    def bgsave(self):
        """
        Asynchronously save the DB on disk
        """
        return self.execute_command("BGSAVE")

    def lastsave(self):
        """
        Return the UNIX time stamp of the last successfully saving of the
        dataset on disk
        """
        return self.execute_command("LASTSAVE")

    def shutdown(self):
        """
        Synchronously save the DB on disk, then shutdown the server
        """
        self.factory.continueTrying = False
        return self.execute_command("SHUTDOWN")

    def bgrewriteaof(self):
        """
        Rewrite the append only file in background when it gets too big
        """
        return self.execute_command("BGREWRITEAOF")

    def _process_info(self, r):
        keypairs = [x for x in r.split('\r\n') if
                    u':' in x and not x.startswith(u'#')]
        d = {}
        for kv in keypairs:
            k, v = kv.split(u':')
            d[k] = v
        return d

    # Remote server control commands
    def info(self, type=None):
        """
        Provide information and statistics about the server
        """
        if type is None:
            return self.execute_command("INFO")
        else:
            r = self.execute_command("INFO", type)
            return r.addCallback(self._process_info)

    # slaveof is missing

    # Redis 2.6 scripting commands
    def _eval(self, script, script_hash, keys, args):
        n = len(keys)
        keys_and_args = tuple(keys) + tuple(args)
        r = self.execute_command("EVAL", script, n, *keys_and_args)
        if script_hash in self.script_hashes:
            return r
        return r.addCallback(self._eval_success, script_hash)

    def _eval_success(self, r, script_hash):
        self.script_hashes.add(script_hash)
        return r

    def _evalsha_failed(self, err, script, script_hash, keys, args):
        if err.check(ScriptDoesNotExist):
            return self._eval(script, script_hash, keys, args)
        return err

    def eval(self, script, keys=[], args=[]):
        h = hashlib.sha1(script).hexdigest()
        if h in self.script_hashes:
            return self.evalsha(h, keys, args).addErrback(
                self._evalsha_failed, script, h, keys, args)
        return self._eval(script, h, keys, args)

    def _evalsha_errback(self, err, script_hash):
        if err.check(ResponseError):
            if err.value.args[0].startswith(u'NOSCRIPT'):
                if script_hash in self.script_hashes:
                    self.script_hashes.remove(script_hash)
                raise ScriptDoesNotExist("No script matching hash: %s found" %
                                         script_hash)
        return err

    def evalsha(self, sha1_hash, keys=[], args=[]):
        n = len(keys)
        keys_and_args = tuple(keys) + tuple(args)
        r = self.execute_command("EVALSHA",
                                 sha1_hash, n,
                                *keys_and_args).addErrback(self._evalsha_errback,
                                                   sha1_hash)
        if sha1_hash not in self.script_hashes:
            r.addCallback(self._eval_success, sha1_hash)
        return r

    def _script_exists_success(self, r):
        l = [bool(x) for x in r]
        if len(l) == 1:
            return l[0]
        else:
            return l

    def script_exists(self, *hashes):
        return self.execute_command("SCRIPT", "EXISTS",
                                    post_proc=self._script_exists_success,
                                    *hashes)

    def _script_flush_success(self, r):
        self.script_hashes.clear()
        return r

    def script_flush(self):
        return self.execute_command("SCRIPT", "FLUSH").addCallback(
            self._script_flush_success)

    def _handle_script_kill(self, r):
        if isinstance(r, Failure):
            if r.check(ResponseError):
                if r.value.args[0].startswith(u'NOTBUSY'):
                    raise NoScriptRunning("No script running")
        else:
            pass
        return r

    def script_kill(self):
        return self.execute_command("SCRIPT",
                                    "KILL").addBoth(self._handle_script_kill)

    def script_load(self, script):
        return self.execute_command("SCRIPT",  "LOAD", script)


class MonitorProtocol(RedisProtocol):
    """
    monitor has the same behavior as subscribe: hold the connection until
    something happens.

    take care with the performance impact: http://redis.io/commands/monitor
    """

    def messageReceived(self, message):
        pass

    def replyReceived(self, reply):
        self.messageReceived(reply)

    def monitor(self):
        return self.execute_command("MONITOR")

    def stop(self):
        self.transport.loseConnection()


class SubscriberProtocol(RedisProtocol):
    def messageReceived(self, pattern, channel, message):
        pass

    def replyReceived(self, reply):
        if isinstance(reply, list):
            if reply[-3] == u"message":
                self.messageReceived(None, *reply[-2:])
            elif len(reply) > 3 and reply[-4] == u"pmessage":
                self.messageReceived(*reply[-3:])
            else:
                self.replyQueue.put(reply[-3:])
        elif isinstance(reply, Exception):
            self.replyQueue.put(reply)

    def subscribe(self, channels):
        if isinstance(channels, (str, unicode)):
            channels = [channels]
        return self.execute_command("SUBSCRIBE", *channels)

    def unsubscribe(self, channels):
        if isinstance(channels, (str, unicode)):
            channels = [channels]
        return self.execute_command("UNSUBSCRIBE", *channels)

    def psubscribe(self, patterns):
        if isinstance(patterns, (str, unicode)):
            patterns = [patterns]
        return self.execute_command("PSUBSCRIBE", *patterns)

    def punsubscribe(self, patterns):
        if isinstance(patterns, (str, unicode)):
            patterns = [patterns]
        return self.execute_command("PUNSUBSCRIBE", *patterns)


class ConnectionHandler(object):
    def __init__(self, factory):
        self._factory = factory
        self._connected = factory.deferred

    def disconnect(self):
        self._factory.continueTrying = 0
        for conn in self._factory.pool:
            try:
                conn.transport.loseConnection()
            except:
                pass

        return self._factory.waitForEmptyPool()

    def __getattr__(self, method):
        def wrapper(*args, **kwargs):
            d = self._factory.getConnection()
            def callback(connection):
                protocol_method = getattr(connection, method)
                try:
                    d = protocol_method(*args, **kwargs)
                except:
                    self._factory.connectionQueue.put(connection)
                    raise

                def put_back(reply):
                    if not connection.inTransaction:
                        self._factory.connectionQueue.put(connection)
                    return reply

                def switch_to_errback(reply):
                    if isinstance(reply, Exception):
                        raise reply
                    return reply

                d.addBoth(put_back)
                d.addCallback(switch_to_errback)
                return d
            d.addCallback(callback)
            return d
        return wrapper

    def __repr__(self):
        try:
            cli = self._factory.pool[0].transport.getPeer()
        except:
            return "<Redis Connection: Not connected>"
        else:
            return "<Redis Connection: %s:%s - %d connection(s)>" % \
                   (cli.host, cli.port, self._factory.size)


class UnixConnectionHandler(ConnectionHandler):
    def __repr__(self):
        try:
            cli = self._factory.pool[0].transport.getPeer()
        except:
            return "<Redis Connection: Not connected>"
        else:
            return "<Redis Unix Connection: %s - %d connection(s)>" % \
                   (cli.name, self._factory.size)


ShardedMethods = frozenset([
    "decr",
    "delete",
    "exists",
    "expire",
    "get",
    "get_type",
    "getset",
    "hdel",
    "hexists",
    "hget",
    "hgetall",
    "hincrby",
    "hkeys",
    "hlen",
    "hmget",
    "hmset",
    "hset",
    "hvals",
    "incr",
    "lindex",
    "llen",
    "lrange",
    "lrem",
    "lset",
    "ltrim",
    "pop",
    "publish",
    "push",
    "rename",
    "sadd",
    "set",
    "setex",
    "setnx",
    "sismember",
    "smembers",
    "srem",
    "ttl",
    "zadd",
    "zcard",
    "zcount",
    "zdecr",
    "zincr",
    "zincrby",
    "zrange",
    "zrangebyscore",
    "zrevrangebyscore",
    "zrevrank",
    "zrank",
    "zrem",
    "zremrangebyscore",
    "zremrangebyrank",
    "zrevrange",
    "zscore",
])

_findhash = re.compile(r'.+\{(.*)\}.*')


class HashRing(object):
    """Consistent hash for redis API"""
    def __init__(self, nodes=[], replicas=160):
        self.nodes = []
        self.replicas = replicas
        self.ring = {}
        self.sorted_keys = []

        for n in nodes:
            self.add_node(n)

    def add_node(self, node):
        self.nodes.append(node)
        for x in xrange(self.replicas):
            crckey = zlib.crc32("%s:%d" % (node._factory.uuid, x))
            self.ring[crckey] = node
            self.sorted_keys.append(crckey)

        self.sorted_keys.sort()

    def remove_node(self, node):
        self.nodes.remove(node)
        for x in xrange(self.replicas):
            crckey = zlib.crc32("%s:%d" % (node, x))
            self.ring.remove(crckey)
            self.sorted_keys.remove(crckey)

    def get_node(self, key):
        n, i = self.get_node_pos(key)
        return n
    #self.get_node_pos(key)[0]

    def get_node_pos(self, key):
        if len(self.ring) == 0:
            return [None, None]
        crc = zlib.crc32(key)
        idx = bisect.bisect(self.sorted_keys, crc)
        # prevents out of range index
        idx = min(idx, (self.replicas * len(self.nodes)) - 1)
        return [self.ring[self.sorted_keys[idx]], idx]

    def iter_nodes(self, key):
        if len(self.ring) == 0:
            yield None, None
        node, pos = self.get_node_pos(key)
        for k in self.sorted_keys[pos:]:
            yield k, self.ring[k]

    def __call__(self, key):
        return self.get_node(key)


class ShardedConnectionHandler(object):
    def __init__(self, connections):
        if isinstance(connections, defer.DeferredList):
            self._ring = None
            connections.addCallback(self._makeRing)
        else:
            self._ring = HashRing(connections)

    def _makeRing(self, connections):
        connections = map(operator.itemgetter(1), connections)
        self._ring = HashRing(connections)
        return self

    @defer.inlineCallbacks
    def disconnect(self):
        if not self._ring:
            raise ConnectionError("Not connected")

        for conn in self._ring.nodes:
            yield conn.disconnect()
        defer.returnValue(True)

    def _wrap(self, method, *args, **kwargs):
        try:
            key = args[0]
            assert isinstance(key, (str, unicode))
        except:
            raise ValueError(
                "Method '%s' requires a key as the first argument" % method)

        m = _findhash.match(key)
        if m is not None and len(m.groups()) >= 1:
            node = self._ring(m.groups()[0])
        else:
            node = self._ring(key)

        return getattr(node, method)(*args, **kwargs)

    def pipeline(self):
        raise NotImplementedError("Pipelining is not supported across shards")

    def __getattr__(self, method):
        if method in ShardedMethods:
            return functools.partial(self._wrap, method)
        else:
            raise NotImplementedError("Method '%s' cannot be sharded" % method)

    @defer.inlineCallbacks
    def mget(self, keys, *args):
        """
        high-level mget, required because of the sharding support
        """

        keys = list_or_args("mget", keys, args)
        group = collections.defaultdict(lambda: [])
        for k in keys:
            node = self._ring(k)
            group[node].append(k)

        deferreds = []
        for node, keys in group.items():
            nd = node.mget(keys)
            deferreds.append(nd)

        result = []
        response = yield defer.DeferredList(deferreds)
        for (success, values) in response:
            if success:
                result += values

        defer.returnValue(result)

    def __repr__(self):
        nodes = []
        for conn in self._ring.nodes:
            try:
                cli = conn._factory.pool[0].transport.getPeer()
            except:
                pass
            else:
                nodes.append("%s:%s/%d" %
                             (cli.host, cli.port, conn._factory.size))
        return "<Redis Sharded Connection: %s>" % ", ".join(nodes)


class ShardedUnixConnectionHandler(ShardedConnectionHandler):
    def __repr__(self):
        nodes = []
        for conn in self._ring.nodes:
            try:
                cli = conn._factory.pool[0].transport.getPeer()
            except:
                pass
            else:
                nodes.append("%s/%d" %
                             (cli.name, conn._factory.size))
        return "<Redis Sharded Connection: %s>" % ", ".join(nodes)


class RedisFactory(protocol.ReconnectingClientFactory):
    maxDelay = 10
    protocol = RedisProtocol

    def __init__(self, uuid, dbid, poolsize, isLazy=False,
                 handler=ConnectionHandler, charset="utf-8", password=None):
        if not isinstance(poolsize, int):
            raise ValueError("Redis poolsize must be an integer, not %s" %
                             repr(poolsize))

        if not isinstance(dbid, (int, types.NoneType)):
            raise ValueError("Redis dbid must be an integer, not %s" %
                             repr(dbid))

        self.uuid = uuid
        self.dbid = dbid
        self.poolsize = poolsize
        self.isLazy = isLazy
        self.charset = charset
        self.password = password

        self.idx = 0
        self.size = 0
        self.pool = []
        self.deferred = defer.Deferred()
        self.handler = handler(self)
        self.connectionQueue = defer.DeferredQueue()
        self._waitingForEmptyPool = set()

    def buildProtocol(self, addr):
        if hasattr(self, 'charset'):
            p = self.protocol(self.charset)
        else:
            p = self.protocol()
        p.factory = self
        return p

    def addConnection(self, conn):
        self.connectionQueue.put(conn)
        self.pool.append(conn)
        self.size = len(self.pool)
        if self.deferred:
            if self.size == self.poolsize:
                self.deferred.callback(self.handler)
                self.deferred = None

    def delConnection(self, conn):
        try:
            self.pool.remove(conn)
        except Exception, e:
            log.msg("Could not remove connection from pool: %s" % str(e))

        self.size = len(self.pool)
        if not self.size and self._waitingForEmptyPool:
            deferreds = self._waitingForEmptyPool
            self._waitingForEmptyPool = set()
            for d in deferreds:
                d.callback(None)

    def _cancelWaitForEmptyPool(self, deferred):
        self._waitingForEmptyPool.discard(deferred)
        deferred.errback(defer.CancelledError())

    def waitForEmptyPool(self):
        """
        Returns a Deferred which fires when the pool size has reached 0.
        """
        if not self.size:
            return defer.succeed(None)
        d = defer.Deferred(self._cancelWaitForEmptyPool)
        self._waitingForEmptyPool.add(d)
        return d

    def connectionError(self, why):
        if self.deferred:
            self.deferred.errback(ValueError(why))
            self.deferred = None

    @defer.inlineCallbacks
    def getConnection(self, put_back=False):
        if not self.size:
            raise ConnectionError("Not connected")

        while True:
            conn = yield self.connectionQueue.get()
            if conn.connected == 0:
                log.msg('Discarding dead connection.')
            else:
                if put_back:
                    self.connectionQueue.put(conn)
                defer.returnValue(conn)


class SubscriberFactory(RedisFactory):
    protocol = SubscriberProtocol

    def __init__(self, isLazy=False, handler=ConnectionHandler):
        RedisFactory.__init__(self, None, None, 1, isLazy=isLazy,
                              handler=handler)


class MonitorFactory(RedisFactory):
    protocol = MonitorProtocol

    def __init__(self, isLazy=False, handler=ConnectionHandler):
        RedisFactory.__init__(self, None, None, 1, isLazy=isLazy,
                              handler=handler)


def makeConnection(host, port, dbid, poolsize, reconnect, isLazy, charset, password):
    uuid = "%s:%s" % (host, port)
    factory = RedisFactory(uuid, dbid, poolsize, isLazy, ConnectionHandler,
                           charset, password)
    factory.continueTrying = reconnect
    for x in xrange(poolsize):
        reactor.connectTCP(host, port, factory)

    if isLazy:
        return factory.handler
    else:
        return factory.deferred


def makeShardedConnection(hosts, dbid, poolsize, reconnect, isLazy, charset, password):
    err = "Please use a list or tuple of host:port for sharded connections"
    if not isinstance(hosts, (list, tuple)):
        raise ValueError(err)

    connections = []
    for item in hosts:
        try:
            host, port = item.split(":")
            port = int(port)
        except:
            raise ValueError(err)

        c = makeConnection(host, port, dbid, poolsize, reconnect, isLazy,
                           charset, password)
        connections.append(c)

    if isLazy:
        return ShardedConnectionHandler(connections)
    else:
        deferred = defer.DeferredList(connections)
        ShardedConnectionHandler(deferred)
        return deferred


def Connection(host="localhost", port=6379, dbid=None, reconnect=True,
               charset="utf-8", password=None):
    return makeConnection(host, port, dbid, 1, reconnect, False, charset, password)


def lazyConnection(host="localhost", port=6379, dbid=None, reconnect=True,
                   charset="utf-8", password=None):
    return makeConnection(host, port, dbid, 1, reconnect, True, charset, password)


def ConnectionPool(host="localhost", port=6379, dbid=None,
                   poolsize=10, reconnect=True, charset="utf-8", password=None):
    return makeConnection(host, port, dbid, poolsize, reconnect, False, charset, password)


def lazyConnectionPool(host="localhost", port=6379, dbid=None,
                       poolsize=10, reconnect=True, charset="utf-8", password=None):
    return makeConnection(host, port, dbid, poolsize, reconnect, True, charset, password)


def ShardedConnection(hosts, dbid=None, reconnect=True, charset="utf-8", password=None):
    return makeShardedConnection(hosts, dbid, 1, reconnect, False, charset, password)


def lazyShardedConnection(hosts, dbid=None, reconnect=True, charset="utf-8", password=None):
    return makeShardedConnection(hosts, dbid, 1, reconnect, True, charset, password)


def ShardedConnectionPool(hosts, dbid=None, poolsize=10, reconnect=True,
                          charset="utf-8", password=None):
    return makeShardedConnection(hosts, dbid, poolsize, reconnect, False,
                                 charset, password)


def lazyShardedConnectionPool(hosts, dbid=None, poolsize=10, reconnect=True,
                              charset="utf-8", password=None):
    return makeShardedConnection(hosts, dbid, poolsize, reconnect, True,
                                 charset, password)


def makeUnixConnection(path, dbid, poolsize, reconnect, isLazy, charset, password):
    factory = RedisFactory(path, dbid, poolsize, isLazy, UnixConnectionHandler,
                           charset, password)
    factory.continueTrying = reconnect
    for x in xrange(poolsize):
        reactor.connectUNIX(path, factory)

    if isLazy:
        return factory.handler
    else:
        return factory.deferred


def makeShardedUnixConnection(paths, dbid, poolsize, reconnect, isLazy,
                              charset, password):
    err = "Please use a list or tuple of paths for sharded unix connections"
    if not isinstance(paths, (list, tuple)):
        raise ValueError(err)

    connections = []
    for path in paths:
        c = makeUnixConnection(path, dbid, poolsize, reconnect, isLazy, charset, password)
        connections.append(c)

    if isLazy:
        return ShardedUnixConnectionHandler(connections)
    else:
        deferred = defer.DeferredList(connections)
        ShardedUnixConnectionHandler(deferred)
        return deferred


def UnixConnection(path="/tmp/redis.sock", dbid=None, reconnect=True,
                   charset="utf-8", password=None):
    return makeUnixConnection(path, dbid, 1, reconnect, False, charset, password)


def lazyUnixConnection(path="/tmp/redis.sock", dbid=None, reconnect=True,
                       charset="utf-8", password=None):
    return makeUnixConnection(path, dbid, 1, reconnect, True, charset, password)


def UnixConnectionPool(path="/tmp/redis.sock", dbid=None, poolsize=10,
                       reconnect=True, charset="utf-8", password=None):
    return makeUnixConnection(path, dbid, poolsize, reconnect, False, charset, password)


def lazyUnixConnectionPool(path="/tmp/redis.sock", dbid=None, poolsize=10,
                           reconnect=True, charset="utf-8", password=None):
    return makeUnixConnection(path, dbid, poolsize, reconnect, True, charset, password)


def ShardedUnixConnection(paths, dbid=None, reconnect=True, charset="utf-8", password=None):
    return makeShardedUnixConnection(paths, dbid, 1, reconnect, False, charset, password)


def lazyShardedUnixConnection(paths, dbid=None, reconnect=True,
                              charset="utf-8", password=None):
    return makeShardedUnixConnection(paths, dbid, 1, reconnect, True, charset, password)


def ShardedUnixConnectionPool(paths, dbid=None, poolsize=10, reconnect=True,
                              charset="utf-8", password=None):
    return makeShardedUnixConnection(paths, dbid, poolsize, reconnect, False,
                                     charset, password)


def lazyShardedUnixConnectionPool(paths, dbid=None, poolsize=10,
                                  reconnect=True, charset="utf-8", password=None):
    return makeShardedUnixConnection(paths, dbid, poolsize, reconnect, True,
                                     charset, password)


__all__ = [
    Connection, lazyConnection,
    ConnectionPool, lazyConnectionPool,
    ShardedConnection, lazyShardedConnection,
    ShardedConnectionPool, lazyShardedConnectionPool,
    UnixConnection, lazyUnixConnection,
    UnixConnectionPool, lazyUnixConnectionPool,
    ShardedUnixConnection, lazyShardedUnixConnection,
    ShardedUnixConnectionPool, lazyShardedUnixConnectionPool,
]

__author__ = "Alexandre Fiori"
__version__ = version = "1.1"

########NEW FILE########
