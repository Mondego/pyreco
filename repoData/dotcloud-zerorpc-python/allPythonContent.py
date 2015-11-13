__FILENAME__ = testutils
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import functools
import nose.exc
import random
import os

_tmpfiles = []

def random_ipc_endpoint():
    tmpfile = '/tmp/zerorpc_test_socket_{0}.sock'.format(
            str(random.random())[2:])
    _tmpfiles.append(tmpfile)
    return 'ipc://{0}'.format(tmpfile)

def teardown():
    global _tmpfiles
    for tmpfile in _tmpfiles:
        print 'unlink', tmpfile
        try:
            os.unlink(tmpfile)
        except Exception:
            pass
    _tmpfiles = []

def skip(reason):
    def _skip(test):
        @functools.wraps(test)
        def wrap():
            raise nose.exc.SkipTest(reason)
        return wrap
    return _skip

########NEW FILE########
__FILENAME__ = test_buffered_channel
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from nose.tools import assert_raises
import gevent
import sys

from zerorpc import zmq
import zerorpc
from testutils import teardown, random_ipc_endpoint


def test_close_server_bufchan():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=2)
    client_bufchan = zerorpc.BufferedChannel(client_hbchan)
    client_bufchan.emit('openthat', None)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=2)
    server_bufchan = zerorpc.BufferedChannel(server_hbchan)
    server_bufchan.recv()

    gevent.sleep(3)
    print 'CLOSE SERVER SOCKET!!!'
    server_bufchan.close()
    if sys.version_info < (2, 7):
        assert_raises(zerorpc.LostRemote, client_bufchan.recv)
    else:
        with assert_raises(zerorpc.LostRemote):
            client_bufchan.recv()
    print 'CLIENT LOST SERVER :)'
    client_bufchan.close()
    server.close()
    client.close()


def test_close_client_bufchan():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=2)
    client_bufchan = zerorpc.BufferedChannel(client_hbchan)
    client_bufchan.emit('openthat', None)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=2)
    server_bufchan = zerorpc.BufferedChannel(server_hbchan)
    server_bufchan.recv()

    gevent.sleep(3)
    print 'CLOSE CLIENT SOCKET!!!'
    client_bufchan.close()
    if sys.version_info < (2, 7):
        assert_raises(zerorpc.LostRemote, client_bufchan.recv)
    else:
        with assert_raises(zerorpc.LostRemote):
            client_bufchan.recv()
    print 'SERVER LOST CLIENT :)'
    server_bufchan.close()
    server.close()
    client.close()


def test_heartbeat_can_open_channel_server_close():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=2)
    client_bufchan = zerorpc.BufferedChannel(client_hbchan)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=2)
    server_bufchan = zerorpc.BufferedChannel(server_hbchan)

    gevent.sleep(3)
    print 'CLOSE SERVER SOCKET!!!'
    server_bufchan.close()
    if sys.version_info < (2, 7):
        assert_raises(zerorpc.LostRemote, client_bufchan.recv)
    else:
        with assert_raises(zerorpc.LostRemote):
            client_bufchan.recv()
    print 'CLIENT LOST SERVER :)'
    client_bufchan.close()
    server.close()
    client.close()


def test_heartbeat_can_open_channel_client_close():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=2)
    client_bufchan = zerorpc.BufferedChannel(client_hbchan)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=2)
    server_bufchan = zerorpc.BufferedChannel(server_hbchan)

    gevent.sleep(3)
    print 'CLOSE CLIENT SOCKET!!!'
    client_bufchan.close()
    client.close()
    if sys.version_info < (2, 7):
        assert_raises(zerorpc.LostRemote, client_bufchan.recv)
    else:
        with assert_raises(zerorpc.LostRemote):
            client_bufchan.recv()
    print 'SERVER LOST CLIENT :)'
    server_bufchan.close()
    server.close()


def test_do_some_req_rep():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=2)
    client_bufchan = zerorpc.BufferedChannel(client_hbchan)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=2)
    server_bufchan = zerorpc.BufferedChannel(server_hbchan)

    def client_do():
        for x in xrange(20):
            client_bufchan.emit('add', (x, x * x))
            event = client_bufchan.recv()
            assert event.name == 'OK'
            assert list(event.args) == [x + x * x]
        client_bufchan.close()

    coro_pool = gevent.pool.Pool()
    coro_pool.spawn(client_do)

    def server_do():
        for x in xrange(20):
            event = server_bufchan.recv()
            assert event.name == 'add'
            server_bufchan.emit('OK', (sum(event.args),))
        server_bufchan.close()

    coro_pool.spawn(server_do)

    coro_pool.join()
    client.close()
    server.close()


def test_do_some_req_rep_lost_server():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    def client_do():
        print 'running'
        client_channel = client.channel()
        client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=2)
        client_bufchan = zerorpc.BufferedChannel(client_hbchan)
        for x in xrange(10):
            client_bufchan.emit('add', (x, x * x))
            event = client_bufchan.recv()
            assert event.name == 'OK'
            assert list(event.args) == [x + x * x]
        client_bufchan.emit('add', (x, x * x))
        if sys.version_info < (2, 7):
            assert_raises(zerorpc.LostRemote, client_bufchan.recv)
        else:
            with assert_raises(zerorpc.LostRemote):
                client_bufchan.recv()
        client_bufchan.close()

    coro_pool = gevent.pool.Pool()
    coro_pool.spawn(client_do)

    def server_do():
        event = server.recv()
        server_channel = server.channel(event)
        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=2)
        server_bufchan = zerorpc.BufferedChannel(server_hbchan)
        for x in xrange(10):
            event = server_bufchan.recv()
            assert event.name == 'add'
            server_bufchan.emit('OK', (sum(event.args),))
        server_bufchan.close()

    coro_pool.spawn(server_do)

    coro_pool.join()
    client.close()
    server.close()


def test_do_some_req_rep_lost_client():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    def client_do():
        client_channel = client.channel()
        client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=2)
        client_bufchan = zerorpc.BufferedChannel(client_hbchan)

        for x in xrange(10):
            client_bufchan.emit('add', (x, x * x))
            event = client_bufchan.recv()
            assert event.name == 'OK'
            assert list(event.args) == [x + x * x]
        client_bufchan.close()

    coro_pool = gevent.pool.Pool()
    coro_pool.spawn(client_do)

    def server_do():
        event = server.recv()
        server_channel = server.channel(event)
        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=2)
        server_bufchan = zerorpc.BufferedChannel(server_hbchan)

        for x in xrange(10):
            event = server_bufchan.recv()
            assert event.name == 'add'
            server_bufchan.emit('OK', (sum(event.args),))

        if sys.version_info < (2, 7):
            assert_raises(zerorpc.LostRemote, server_bufchan.recv)
        else:
            with assert_raises(zerorpc.LostRemote):
                server_bufchan.recv()
        server_bufchan.close()

    coro_pool.spawn(server_do)

    coro_pool.join()
    client.close()
    server.close()


def test_do_some_req_rep_client_timeout():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    def client_do():
        client_channel = client.channel()
        client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=2)
        client_bufchan = zerorpc.BufferedChannel(client_hbchan)

        if sys.version_info < (2, 7):
            def _do_with_assert_raises():
                for x in xrange(10):
                    client_bufchan.emit('sleep', (x,))
                    event = client_bufchan.recv(timeout=3)
                    assert event.name == 'OK'
                    assert list(event.args) == [x]
            assert_raises(zerorpc.TimeoutExpired, _do_with_assert_raises)
        else:
            with assert_raises(zerorpc.TimeoutExpired):
                for x in xrange(10):
                    client_bufchan.emit('sleep', (x,))
                    event = client_bufchan.recv(timeout=3)
                    assert event.name == 'OK'
                    assert list(event.args) == [x]
        client_bufchan.close()

    coro_pool = gevent.pool.Pool()
    coro_pool.spawn(client_do)

    def server_do():
        event = server.recv()
        server_channel = server.channel(event)
        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=2)
        server_bufchan = zerorpc.BufferedChannel(server_hbchan)

        if sys.version_info < (2, 7):
            def _do_with_assert_raises():
                for x in xrange(20):
                    event = server_bufchan.recv()
                    assert event.name == 'sleep'
                    gevent.sleep(event.args[0])
                    server_bufchan.emit('OK', event.args)
            assert_raises(zerorpc.LostRemote, _do_with_assert_raises)
        else:
            with assert_raises(zerorpc.LostRemote):
                for x in xrange(20):
                    event = server_bufchan.recv()
                    assert event.name == 'sleep'
                    gevent.sleep(event.args[0])
                    server_bufchan.emit('OK', event.args)
        server_bufchan.close()


    coro_pool.spawn(server_do)

    coro_pool.join()
    client.close()
    server.close()


class CongestionError(Exception):
    pass


def test_congestion_control_server_pushing():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=2)
    client_bufchan = zerorpc.BufferedChannel(client_hbchan)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=2)
    server_bufchan = zerorpc.BufferedChannel(server_hbchan)

    def client_do():
        for x in xrange(200):
            event = client_bufchan.recv()
            assert event.name == 'coucou'
            assert event.args == x

    coro_pool = gevent.pool.Pool()
    coro_pool.spawn(client_do)

    def server_do():
        if sys.version_info < (2, 7):
            def _do_with_assert_raises():
                for x in xrange(200):
                    if not server_bufchan.emit('coucou', x, block=False):
                        raise CongestionError()  # will fail when x == 1
            assert_raises(CongestionError, _do_with_assert_raises)
        else:
            with assert_raises(CongestionError):
                for x in xrange(200):
                    if not server_bufchan.emit('coucou', x, block=False):
                        raise CongestionError()  # will fail when x == 1
        server_bufchan.emit('coucou', 1)  # block until receiver is ready
        if sys.version_info < (2, 7):
            def _do_with_assert_raises():
                for x in xrange(2, 200):
                    if not server_bufchan.emit('coucou', x, block=False):
                        raise CongestionError()  # will fail when x == 100
            assert_raises(CongestionError, _do_with_assert_raises)
        else:
            with assert_raises(CongestionError):
                for x in xrange(2, 200):
                    if not server_bufchan.emit('coucou', x, block=False):
                        raise CongestionError()  # will fail when x == 100
        for x in xrange(101, 200):
            server_bufchan.emit('coucou', x) # block until receiver is ready


    coro_pool.spawn(server_do)

    coro_pool.join()
    client_bufchan.close()
    client.close()
    server_bufchan.close()
    server.close()

########NEW FILE########
__FILENAME__ = test_channel
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from zerorpc import zmq
import zerorpc
from testutils import teardown, random_ipc_endpoint


def test_events_channel_client_side():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events)

    client_channel = client.channel()
    client_channel.emit('someevent', (42,))

    event = server.recv()
    print event
    assert list(event.args) == [42]
    assert event.header.get('zmqid', None) is not None

    server.emit('someanswer', (21,),
            xheader=dict(response_to=event.header['message_id'],
                zmqid=event.header['zmqid']))
    event = client_channel.recv()
    assert list(event.args) == [21]


def test_events_channel_client_side_server_send_many():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events)

    client_channel = client.channel()
    client_channel.emit('giveme', (10,))

    event = server.recv()
    print event
    assert list(event.args) == [10]
    assert event.header.get('zmqid', None) is not None

    for x in xrange(10):
        server.emit('someanswer', (x,),
                xheader=dict(response_to=event.header['message_id'],
                    zmqid=event.header['zmqid']))
    for x in xrange(10):
        event = client_channel.recv()
        assert list(event.args) == [x]


def test_events_channel_both_side():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events)

    client_channel = client.channel()
    client_channel.emit('openthat', (42,))

    event = server.recv()
    print event
    assert list(event.args) == [42]
    assert event.name == 'openthat'

    server_channel = server.channel(event)
    server_channel.emit('test', (21,))

    event = client_channel.recv()
    assert list(event.args) == [21]
    assert event.name == 'test'

    server_channel.emit('test', (22,))

    event = client_channel.recv()
    assert list(event.args) == [22]
    assert event.name == 'test'

    server_events.close()
    server_channel.close()
    client_channel.close()
    client_events.close()

########NEW FILE########
__FILENAME__ = test_client
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import gevent

import zerorpc
from testutils import teardown, random_ipc_endpoint

def test_client_connect():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client()
    client.connect(endpoint)

    assert client.lolita() == 42

def test_client_quick_connect():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(endpoint)

    assert client.lolita() == 42

########NEW FILE########
__FILENAME__ = test_client_async
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2013 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from nose.tools import assert_raises
import gevent
import sys

from zerorpc import zmq
import zerorpc
from testutils import teardown, random_ipc_endpoint


def test_client_server_client_timeout_with_async():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

        def add(self, a, b):
            gevent.sleep(10)
            return a + b

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(timeout=2)
    client.connect(endpoint)

    async_result = client.add(1, 4, async=True)

    if sys.version_info < (2, 7):
        def _do_with_assert_raises():
            print async_result.get()
        assert_raises(zerorpc.TimeoutExpired, _do_with_assert_raises)
    else:
        with assert_raises(zerorpc.TimeoutExpired):
            print async_result.get()
    client.close()
    srv.close()


def test_client_server_with_async():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

        def add(self, a, b):
            return a + b

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client()
    client.connect(endpoint)

    async_result = client.lolita(async=True)
    assert async_result.get() == 42

    async_result = client.add(1, 4, async=True)
    assert async_result.get() == 5

########NEW FILE########
__FILENAME__ = test_client_heartbeat
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import gevent

import zerorpc
from testutils import teardown, random_ipc_endpoint


def test_client_server_hearbeat():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

        def slow(self):
            gevent.sleep(10)

    srv = MySrv(heartbeat=1)
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(heartbeat=1)
    client.connect(endpoint)

    assert client.lolita() == 42
    print 'GOT ANSWER'


def test_client_server_activate_heartbeat():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            gevent.sleep(3)
            return 42

    srv = MySrv(heartbeat=1)
    srv.bind(endpoint)
    gevent.spawn(srv.run)
    gevent.sleep(0)

    client = zerorpc.Client(heartbeat=1)
    client.connect(endpoint)

    assert client.lolita() == 42
    print 'GOT ANSWER'


def test_client_server_passive_hearbeat():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

        def slow(self):
            gevent.sleep(3)
            return 2

    srv = MySrv(heartbeat=1)
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(heartbeat=1, passive_heartbeat=True)
    client.connect(endpoint)

    assert client.slow() == 2
    print 'GOT ANSWER'


def test_client_hb_doesnt_linger_on_streaming():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        @zerorpc.stream
        def iter(self):
            return xrange(42)

    srv = MySrv(heartbeat=1, context=zerorpc.Context())
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client1 = zerorpc.Client(endpoint, heartbeat=1, context=zerorpc.Context())

    def test_client():
        assert list(client1.iter()) == list(xrange(42))
        print 'sleep 3s'
        gevent.sleep(3)

    gevent.spawn(test_client).join()


def est_client_drop_few():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

    srv = MySrv(heartbeat=1, context=zerorpc.Context())
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client1 = zerorpc.Client(endpoint, heartbeat=1, context=zerorpc.Context())
    client2 = zerorpc.Client(endpoint, heartbeat=1, context=zerorpc.Context())
    client3 = zerorpc.Client(endpoint, heartbeat=1, context=zerorpc.Context())

    assert client1.lolita() == 42
    assert client2.lolita() == 42

    gevent.sleep(3)
    assert client3.lolita() == 42


def test_client_drop_empty_stream():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        @zerorpc.stream
        def iter(self):
            return []

    srv = MySrv(heartbeat=1, context=zerorpc.Context())
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client1 = zerorpc.Client(endpoint, heartbeat=1, context=zerorpc.Context())

    def test_client():
        print 'grab iter'
        i = client1.iter()

        print 'sleep 3s'
        gevent.sleep(3)

    gevent.spawn(test_client).join()


def test_client_drop_stream():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        @zerorpc.stream
        def iter(self):
            return xrange(500)

    srv = MySrv(heartbeat=1, context=zerorpc.Context())
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client1 = zerorpc.Client(endpoint, heartbeat=1, context=zerorpc.Context())

    def test_client():
        print 'grab iter'
        i = client1.iter()

        print 'consume some'
        assert list(next(i) for x in xrange(142)) == list(xrange(142))

        print 'sleep 3s'
        gevent.sleep(3)

    gevent.spawn(test_client).join()

########NEW FILE########
__FILENAME__ = test_events
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from zerorpc import zmq
import zerorpc
from testutils import teardown, random_ipc_endpoint

class MokupContext():
    _next_id = 0

    def new_msgid(self):
        new_id = MokupContext._next_id
        MokupContext._next_id += 1
        return new_id


def test_context():
    c = zerorpc.Context()
    assert c.new_msgid() is not None


def test_event():
    context = MokupContext()
    event = zerorpc.Event('mylittleevent', (None,), context=context)
    print event
    assert event.name == 'mylittleevent'
    assert event.header['message_id'] == 0
    assert event.args == (None,)

    event = zerorpc.Event('mylittleevent2', ('42',), context=context)
    print event
    assert event.name == 'mylittleevent2'
    assert event.header['message_id'] == 1
    assert event.args == ('42',)

    event = zerorpc.Event('mylittleevent3', ('a', 42), context=context)
    print event
    assert event.name == 'mylittleevent3'
    assert event.header['message_id'] == 2
    assert event.args == ('a', 42)

    event = zerorpc.Event('mylittleevent4', ('b', 21), context=context)
    print event
    assert event.name == 'mylittleevent4'
    assert event.header['message_id'] == 3
    assert event.args == ('b', 21)

    packed = event.pack()
    unpacked = zerorpc.Event.unpack(packed)
    print unpacked

    assert unpacked.name == 'mylittleevent4'
    assert unpacked.header['message_id'] == 3
    assert list(unpacked.args) == ['b', 21]

    event = zerorpc.Event('mylittleevent5', ('c', 24, True),
            header={'lol': 'rofl'}, context=None)
    print event
    assert event.name == 'mylittleevent5'
    assert event.header['lol'] == 'rofl'
    assert event.args == ('c', 24, True)

    event = zerorpc.Event('mod', (42,), context=context)
    print event
    assert event.name == 'mod'
    assert event.header['message_id'] == 4
    assert event.args == (42,)
    event.header.update({'stream': True})
    assert event.header['stream'] is True


def test_events_req_rep():
    endpoint = random_ipc_endpoint()
    server = zerorpc.Events(zmq.REP)
    server.bind(endpoint)

    client = zerorpc.Events(zmq.REQ)
    client.connect(endpoint)

    client.emit('myevent', ('arg1',))

    event = server.recv()
    print event
    assert event.name == 'myevent'
    assert list(event.args) == ['arg1']


def test_events_req_rep2():
    endpoint = random_ipc_endpoint()
    server = zerorpc.Events(zmq.REP)
    server.bind(endpoint)

    client = zerorpc.Events(zmq.REQ)
    client.connect(endpoint)

    for i in xrange(10):
        client.emit('myevent' + str(i), (i,))
        event = server.recv()
        print event
        assert event.name == 'myevent' + str(i)
        assert list(event.args) == [i]

        server.emit('answser' + str(i * 2), (i * 2,))
        event = client.recv()
        print event
        assert event.name == 'answser' + str(i * 2)
        assert list(event.args) == [i * 2]


def test_events_dealer_router():
    endpoint = random_ipc_endpoint()
    server = zerorpc.Events(zmq.ROUTER)
    server.bind(endpoint)

    client = zerorpc.Events(zmq.DEALER)
    client.connect(endpoint)

    for i in xrange(6):
        client.emit('myevent' + str(i), (i,))
        event = server.recv()
        print event
        assert event.name == 'myevent' + str(i)
        assert list(event.args) == [i]

        server.emit('answser' + str(i * 2), (i * 2,),
                xheader=dict(zmqid=event.header['zmqid']))
        event = client.recv()
        print event
        assert event.name == 'answser' + str(i * 2)
        assert list(event.args) == [i * 2]


def test_events_push_pull():
    endpoint = random_ipc_endpoint()
    server = zerorpc.Events(zmq.PULL)
    server.bind(endpoint)

    client = zerorpc.Events(zmq.PUSH)
    client.connect(endpoint)

    for x in xrange(10):
        client.emit('myevent', (x,))

    for x in xrange(10):
        event = server.recv()
        print event
        assert event.name == 'myevent'
        assert list(event.args) == [x]

########NEW FILE########
__FILENAME__ = test_heartbeat
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from nose.tools import assert_raises
import gevent
import sys

from zerorpc import zmq
import zerorpc
from testutils import teardown, random_ipc_endpoint


def test_close_server_hbchan():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=2)
    client_hbchan.emit('openthat', None)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=2)
    server_hbchan.recv()

    gevent.sleep(3)
    print 'CLOSE SERVER SOCKET!!!'
    server_hbchan.close()
    if sys.version_info < (2, 7):
        assert_raises(zerorpc.LostRemote, client_hbchan.recv)
    else:
        with assert_raises(zerorpc.LostRemote):
            client_hbchan.recv()
    print 'CLIENT LOST SERVER :)'
    client_hbchan.close()
    server.close()
    client.close()


def test_close_client_hbchan():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=2)
    client_hbchan.emit('openthat', None)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=2)
    server_hbchan.recv()

    gevent.sleep(3)
    print 'CLOSE CLIENT SOCKET!!!'
    client_hbchan.close()
    if sys.version_info < (2, 7):
        assert_raises(zerorpc.LostRemote, server_hbchan.recv)
    else:
        with assert_raises(zerorpc.LostRemote):
            server_hbchan.recv()
    print 'SERVER LOST CLIENT :)'
    server_hbchan.close()
    server.close()
    client.close()


def test_heartbeat_can_open_channel_server_close():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=2)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=2)

    gevent.sleep(3)
    print 'CLOSE SERVER SOCKET!!!'
    server_hbchan.close()
    if sys.version_info < (2, 7):
        assert_raises(zerorpc.LostRemote, client_hbchan.recv)
    else:
        with assert_raises(zerorpc.LostRemote):
            client_hbchan.recv()
    print 'CLIENT LOST SERVER :)'
    client_hbchan.close()
    server.close()
    client.close()


def test_heartbeat_can_open_channel_client_close():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=2)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=2)

    gevent.sleep(3)
    print 'CLOSE CLIENT SOCKET!!!'
    client_hbchan.close()
    client.close()
    if sys.version_info < (2, 7):
        assert_raises(zerorpc.LostRemote, server_hbchan.recv)
    else:
        with assert_raises(zerorpc.LostRemote):
            server_hbchan.recv()
    print 'SERVER LOST CLIENT :)'
    server_hbchan.close()
    server.close()


def test_do_some_req_rep():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=2)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=2)

    def client_do():
        for x in xrange(20):
            client_hbchan.emit('add', (x, x * x))
            event = client_hbchan.recv()
            assert event.name == 'OK'
            assert list(event.args) == [x + x * x]
        client_hbchan.close()

    client_task = gevent.spawn(client_do)

    def server_do():
        for x in xrange(20):
            event = server_hbchan.recv()
            assert event.name == 'add'
            server_hbchan.emit('OK', (sum(event.args),))
        server_hbchan.close()

    server_task = gevent.spawn(server_do)

    server_task.get()
    client_task.get()
    client.close()
    server.close()


def test_do_some_req_rep_lost_server():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    def client_do():
        print 'running'
        client_channel = client.channel()
        client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=2)
        for x in xrange(10):
            client_hbchan.emit('add', (x, x * x))
            event = client_hbchan.recv()
            assert event.name == 'OK'
            assert list(event.args) == [x + x * x]
        client_hbchan.emit('add', (x, x * x))
        if sys.version_info < (2, 7):
            assert_raises(zerorpc.LostRemote, client_hbchan.recv)
        else:
            with assert_raises(zerorpc.LostRemote):
                client_hbchan.recv()
        client_hbchan.close()

    client_task = gevent.spawn(client_do)

    def server_do():
        event = server.recv()
        server_channel = server.channel(event)
        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=2)
        for x in xrange(10):
            event = server_hbchan.recv()
            assert event.name == 'add'
            server_hbchan.emit('OK', (sum(event.args),))
        server_hbchan.close()

    server_task = gevent.spawn(server_do)

    server_task.get()
    client_task.get()
    client.close()
    server.close()


def test_do_some_req_rep_lost_client():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    def client_do():
        client_channel = client.channel()
        client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=2)

        for x in xrange(10):
            client_hbchan.emit('add', (x, x * x))
            event = client_hbchan.recv()
            assert event.name == 'OK'
            assert list(event.args) == [x + x * x]
        client_hbchan.close()

    client_task = gevent.spawn(client_do)

    def server_do():
        event = server.recv()
        server_channel = server.channel(event)
        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=2)

        for x in xrange(10):
            event = server_hbchan.recv()
            assert event.name == 'add'
            server_hbchan.emit('OK', (sum(event.args),))

        if sys.version_info < (2, 7):
            assert_raises(zerorpc.LostRemote, server_hbchan.recv)
        else:
            with assert_raises(zerorpc.LostRemote):
                server_hbchan.recv()
        server_hbchan.close()

    server_task = gevent.spawn(server_do)

    server_task.get()
    client_task.get()
    client.close()
    server.close()


def test_do_some_req_rep_client_timeout():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    def client_do():
        client_channel = client.channel()
        client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=2)

        if sys.version_info < (2, 7):
            def _do_with_assert_raises():
                for x in xrange(10):
                    client_hbchan.emit('sleep', (x,))
                    event = client_hbchan.recv(timeout=3)
                    assert event.name == 'OK'
                    assert list(event.args) == [x]
            assert_raises(zerorpc.TimeoutExpired, _do_with_assert_raises)
        else:
            with assert_raises(zerorpc.TimeoutExpired):
                for x in xrange(10):
                    client_hbchan.emit('sleep', (x,))
                    event = client_hbchan.recv(timeout=3)
                    assert event.name == 'OK'
                    assert list(event.args) == [x]
        client_hbchan.close()

    client_task = gevent.spawn(client_do)

    def server_do():
        event = server.recv()
        server_channel = server.channel(event)
        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=2)

        if sys.version_info < (2, 7):
            def _do_with_assert_raises():
                for x in xrange(20):
                    event = server_hbchan.recv()
                    assert event.name == 'sleep'
                    gevent.sleep(event.args[0])
                    server_hbchan.emit('OK', event.args)
            assert_raises(zerorpc.LostRemote, _do_with_assert_raises)
        else:
            with assert_raises(zerorpc.LostRemote):
                for x in xrange(20):
                    event = server_hbchan.recv()
                    assert event.name == 'sleep'
                    gevent.sleep(event.args[0])
                    server_hbchan.emit('OK', event.args)
        server_hbchan.close()

    server_task = gevent.spawn(server_do)

    server_task.get()
    client_task.get()
    client.close()
    server.close()

########NEW FILE########
__FILENAME__ = test_middleware
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from nose.tools import assert_raises
import gevent
import gevent.local
import random
import hashlib
import sys

from zerorpc import zmq
import zerorpc
from testutils import teardown, random_ipc_endpoint


def test_resolve_endpoint():
    test_endpoint = random_ipc_endpoint()
    c = zerorpc.Context()

    def resolve(endpoint):
        if endpoint == 'titi':
            return test_endpoint
        return endpoint

    cnt = c.register_middleware({
        'resolve_endpoint': resolve
        })
    print 'registered_count:', cnt
    assert cnt == 1

    print 'resolve titi:', c.hook_resolve_endpoint('titi')
    assert c.hook_resolve_endpoint('titi') == test_endpoint

    print 'resolve toto:', c.hook_resolve_endpoint('toto')
    assert c.hook_resolve_endpoint('toto') == 'toto'

    class Resolver():

        def resolve_endpoint(self, endpoint):
            if endpoint == 'toto':
                return test_endpoint
            return endpoint

    cnt = c.register_middleware(Resolver())
    print 'registered_count:', cnt
    assert cnt == 1

    print 'resolve titi:', c.hook_resolve_endpoint('titi')
    assert c.hook_resolve_endpoint('titi') == test_endpoint
    print 'resolve toto:', c.hook_resolve_endpoint('toto')
    assert c.hook_resolve_endpoint('toto') == test_endpoint

    c2 = zerorpc.Context()
    print 'resolve titi:', c2.hook_resolve_endpoint('titi')
    assert c2.hook_resolve_endpoint('titi') == 'titi'
    print 'resolve toto:', c2.hook_resolve_endpoint('toto')
    assert c2.hook_resolve_endpoint('toto') == 'toto'


def test_resolve_endpoint_events():
    test_endpoint = random_ipc_endpoint()
    c = zerorpc.Context()

    class Resolver():
        def resolve_endpoint(self, endpoint):
            if endpoint == 'some_service':
                return test_endpoint
            return endpoint

    class Srv(zerorpc.Server):
        def hello(self):
            print 'heee'
            return 'world'

    srv = Srv(heartbeat=1, context=c)
    if sys.version_info < (2, 7):
        assert_raises(zmq.ZMQError, srv.bind, 'some_service')
    else:
        with assert_raises(zmq.ZMQError):
            srv.bind('some_service')

    cnt = c.register_middleware(Resolver())
    assert cnt == 1
    srv.bind('some_service')
    gevent.spawn(srv.run)

    client = zerorpc.Client(heartbeat=1, context=c)
    client.connect('some_service')
    assert client.hello() == 'world'

    client.close()
    srv.close()


class Tracer:
    '''Used by test_task_context_* tests'''
    def __init__(self, identity):
        self._identity = identity
        self._locals = gevent.local.local()
        self._log = []

    @property
    def trace_id(self):
        return self._locals.__dict__.get('trace_id', None)

    def load_task_context(self, event_header):
        self._locals.trace_id = event_header.get('trace_id', None)
        print self._identity, 'load_task_context', self.trace_id
        self._log.append(('load', self.trace_id))

    def get_task_context(self):
        if self.trace_id is None:
            # just an ugly code to generate a beautiful little hash.
            self._locals.trace_id = '<{0}>'.format(hashlib.md5(
                    str(random.random())[3:]
                    ).hexdigest()[0:6].upper())
            print self._identity, 'get_task_context! [make a new one]', self.trace_id
            self._log.append(('new', self.trace_id))
        else:
            print self._identity, 'get_task_context! [reuse]', self.trace_id
            self._log.append(('reuse', self.trace_id))
        return { 'trace_id': self.trace_id }


def test_task_context():
    endpoint = random_ipc_endpoint()
    srv_ctx = zerorpc.Context()
    cli_ctx = zerorpc.Context()

    srv_tracer = Tracer('[server]')
    srv_ctx.register_middleware(srv_tracer)
    cli_tracer = Tracer('[client]')
    cli_ctx.register_middleware(cli_tracer)

    class Srv:
        def echo(self, msg):
            return msg

        @zerorpc.stream
        def stream(self):
            yield 42

    srv = zerorpc.Server(Srv(), context=srv_ctx)
    srv.bind(endpoint)
    srv_task = gevent.spawn(srv.run)

    c = zerorpc.Client(context=cli_ctx)
    c.connect(endpoint)

    assert c.echo('hello') == 'hello'
    for x in c.stream():
        assert x == 42

    srv.stop()
    srv_task.join()

    assert cli_tracer._log == [
            ('new', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ]
    assert srv_tracer._log == [
            ('load', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ('load', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ]

def test_task_context_relay():
    endpoint1 = random_ipc_endpoint()
    endpoint2 = random_ipc_endpoint()
    srv_ctx = zerorpc.Context()
    srv_relay_ctx = zerorpc.Context()
    cli_ctx = zerorpc.Context()

    srv_tracer = Tracer('[server]')
    srv_ctx.register_middleware(srv_tracer)
    srv_relay_tracer = Tracer('[server_relay]')
    srv_relay_ctx.register_middleware(srv_relay_tracer)
    cli_tracer = Tracer('[client]')
    cli_ctx.register_middleware(cli_tracer)

    class Srv:
        def echo(self, msg):
            return msg

    srv = zerorpc.Server(Srv(), context=srv_ctx)
    srv.bind(endpoint1)
    srv_task = gevent.spawn(srv.run)

    c_relay = zerorpc.Client(context=srv_relay_ctx)
    c_relay.connect(endpoint1)

    class SrvRelay:
        def echo(self, msg):
            return c_relay.echo('relay' + msg) + 'relayed'

    srv_relay = zerorpc.Server(SrvRelay(), context=srv_relay_ctx)
    srv_relay.bind(endpoint2)
    srv_relay_task = gevent.spawn(srv_relay.run)

    c = zerorpc.Client(context=cli_ctx)
    c.connect(endpoint2)

    assert c.echo('hello') == 'relayhellorelayed'

    srv_relay.stop()
    srv.stop()
    srv_relay_task.join()
    srv_task.join()

    assert cli_tracer._log == [
            ('new', cli_tracer.trace_id),
            ]
    assert srv_relay_tracer._log == [
            ('load', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ]
    assert srv_tracer._log == [
            ('load', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ]

def test_task_context_relay_fork():
    endpoint1 = random_ipc_endpoint()
    endpoint2 = random_ipc_endpoint()
    srv_ctx = zerorpc.Context()
    srv_relay_ctx = zerorpc.Context()
    cli_ctx = zerorpc.Context()

    srv_tracer = Tracer('[server]')
    srv_ctx.register_middleware(srv_tracer)
    srv_relay_tracer = Tracer('[server_relay]')
    srv_relay_ctx.register_middleware(srv_relay_tracer)
    cli_tracer = Tracer('[client]')
    cli_ctx.register_middleware(cli_tracer)

    class Srv:
        def echo(self, msg):
            return msg

    srv = zerorpc.Server(Srv(), context=srv_ctx)
    srv.bind(endpoint1)
    srv_task = gevent.spawn(srv.run)

    c_relay = zerorpc.Client(context=srv_relay_ctx)
    c_relay.connect(endpoint1)

    class SrvRelay:
        def echo(self, msg):
            def dothework(msg):
                return c_relay.echo(msg) + 'relayed'
            g = gevent.spawn(zerorpc.fork_task_context(dothework,
                srv_relay_ctx), 'relay' + msg)
            print 'relaying in separate task:', g
            r = g.get()
            print 'back to main task'
            return r

    srv_relay = zerorpc.Server(SrvRelay(), context=srv_relay_ctx)
    srv_relay.bind(endpoint2)
    srv_relay_task = gevent.spawn(srv_relay.run)

    c = zerorpc.Client(context=cli_ctx)
    c.connect(endpoint2)

    assert c.echo('hello') == 'relayhellorelayed'

    srv_relay.stop()
    srv.stop()
    srv_relay_task.join()
    srv_task.join()

    assert cli_tracer._log == [
            ('new', cli_tracer.trace_id),
            ]
    assert srv_relay_tracer._log == [
            ('load', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ('load', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ]
    assert srv_tracer._log == [
            ('load', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ]


def test_task_context_pushpull():
    endpoint = random_ipc_endpoint()
    puller_ctx = zerorpc.Context()
    pusher_ctx = zerorpc.Context()

    puller_tracer = Tracer('[puller]')
    puller_ctx.register_middleware(puller_tracer)
    pusher_tracer = Tracer('[pusher]')
    pusher_ctx.register_middleware(pusher_tracer)

    trigger = gevent.event.Event()

    class Puller:
        def echo(self, msg):
            trigger.set()

    puller = zerorpc.Puller(Puller(), context=puller_ctx)
    puller.bind(endpoint)
    puller_task = gevent.spawn(puller.run)

    c = zerorpc.Pusher(context=pusher_ctx)
    c.connect(endpoint)

    trigger.clear()
    c.echo('hello')
    trigger.wait()

    puller.stop()
    puller_task.join()

    assert pusher_tracer._log == [
            ('new', pusher_tracer.trace_id),
            ]
    assert puller_tracer._log == [
            ('load', pusher_tracer.trace_id),
            ]


def test_task_context_pubsub():
    endpoint = random_ipc_endpoint()
    subscriber_ctx = zerorpc.Context()
    publisher_ctx = zerorpc.Context()

    subscriber_tracer = Tracer('[subscriber]')
    subscriber_ctx.register_middleware(subscriber_tracer)
    publisher_tracer = Tracer('[publisher]')
    publisher_ctx.register_middleware(publisher_tracer)

    trigger = gevent.event.Event()

    class Subscriber:
        def echo(self, msg):
            trigger.set()

    subscriber = zerorpc.Subscriber(Subscriber(), context=subscriber_ctx)
    subscriber.bind(endpoint)
    subscriber_task = gevent.spawn(subscriber.run)

    c = zerorpc.Publisher(context=publisher_ctx)
    c.connect(endpoint)

    trigger.clear()
    # We need this retry logic to wait that the subscriber.run coroutine starts
    # reading (the published messages will go to /dev/null until then).
    for attempt in xrange(0, 10):
        c.echo('pub...')
        if trigger.wait(0.2):
            break

    subscriber.stop()
    subscriber_task.join()

    assert publisher_tracer._log == [
            ('new', publisher_tracer.trace_id),
            ]
    assert subscriber_tracer._log == [
            ('load', publisher_tracer.trace_id),
            ]


class InspectExceptionMiddleware(Tracer):
    def __init__(self, barrier=None):
        self.called = False
        self._barrier = barrier
        Tracer.__init__(self, identity='[server]')

    def server_inspect_exception(self, request_event, reply_event, task_context, exc_info):
        assert 'trace_id' in task_context
        assert request_event.name == 'echo'
        if self._barrier: # Push/Pull
            assert reply_event is None
        else: # Req/Rep or Req/Stream
            assert reply_event.name == 'ERR'
        exc_type, exc_value, exc_traceback = exc_info
        self.called = True
        if self._barrier:
            self._barrier.set()

class Srv(object):

    def echo(self, msg):
        raise RuntimeError(msg)

    @zerorpc.stream
    def echoes(self, msg):
        raise RuntimeError(msg)

def test_server_inspect_exception_middleware():
    endpoint = random_ipc_endpoint()

    middleware = InspectExceptionMiddleware()
    ctx = zerorpc.Context()
    ctx.register_middleware(middleware)

    module = Srv()
    server = zerorpc.Server(module, context=ctx)
    server.bind(endpoint)
    gevent.spawn(server.run)

    client = zerorpc.Client()
    client.connect(endpoint)

    try:
        client.echo('This is a test which should call the InspectExceptionMiddleware')
    except zerorpc.exceptions.RemoteError as ex:
        assert ex.name == 'RuntimeError'

    client.close()
    server.close()

    assert middleware.called is True

def test_server_inspect_exception_middleware_puller():
    endpoint = random_ipc_endpoint()

    barrier = gevent.event.Event()
    middleware = InspectExceptionMiddleware(barrier)
    ctx = zerorpc.Context()
    ctx.register_middleware(middleware)

    module = Srv()
    server = zerorpc.Puller(module, context=ctx)
    server.bind(endpoint)
    gevent.spawn(server.run)

    client = zerorpc.Pusher()
    client.connect(endpoint)

    barrier.clear()
    client.echo('This is a test which should call the InspectExceptionMiddleware')
    barrier.wait(timeout=2)

    client.close()
    server.close()

    assert middleware.called is True

def test_server_inspect_exception_middleware_stream():
    endpoint = random_ipc_endpoint()

    middleware = InspectExceptionMiddleware()
    ctx = zerorpc.Context()
    ctx.register_middleware(middleware)

    module = Srv()
    server = zerorpc.Server(module, context=ctx)
    server.bind(endpoint)
    gevent.spawn(server.run)

    client = zerorpc.Client()
    client.connect(endpoint)

    try:
        client.echo('This is a test which should call the InspectExceptionMiddleware')
    except zerorpc.exceptions.RemoteError as ex:
        assert ex.name == 'RuntimeError'

    client.close()
    server.close()

    assert middleware.called is True

########NEW FILE########
__FILENAME__ = test_middleware_before_after_exec
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import gevent
import zerorpc

from testutils import random_ipc_endpoint

class EchoModule(object):

    def __init__(self, trigger=None):
        self.last_msg = None
        self._trigger = trigger

    def echo(self, msg):
        self.last_msg = 'echo: ' + msg
        if self._trigger:
            self._trigger.set()
        return self.last_msg

    @zerorpc.stream
    def echoes(self, msg):
        self.last_msg = 'echo: ' + msg
        for i in xrange(0, 3):
            yield self.last_msg

class ServerBeforeExecMiddleware(object):

    def __init__(self):
        self.called = False

    def server_before_exec(self, request_event):
        assert request_event.name == "echo" or request_event.name == "echoes"
        self.called = True

def test_hook_server_before_exec():
    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Client()
    test_client.connect(endpoint)

    # Test without a middleware
    assert test_client.echo("test") == "echo: test"

    # Test with a middleware
    test_middleware = ServerBeforeExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    assert test_client.echo("test") == "echo: test"
    assert test_middleware.called == True

    test_server.stop()
    test_server_task.join()

def test_hook_server_before_exec_puller():
    zero_ctx = zerorpc.Context()
    trigger = gevent.event.Event()
    endpoint = random_ipc_endpoint()

    echo_module = EchoModule(trigger)
    test_server = zerorpc.Puller(echo_module, context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Pusher()
    test_client.connect(endpoint)

    # Test without a middleware
    test_client.echo("test")
    trigger.wait(timeout=2)
    assert echo_module.last_msg == "echo: test"
    trigger.clear()

    # Test with a middleware
    test_middleware = ServerBeforeExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    test_client.echo("test with a middleware")
    trigger.wait(timeout=2)
    assert echo_module.last_msg == "echo: test with a middleware"
    assert test_middleware.called == True

    test_server.stop()
    test_server_task.join()

def test_hook_server_before_exec_stream():
    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Client()
    test_client.connect(endpoint)

    # Test without a middleware
    for echo in test_client.echoes("test"):
        assert echo == "echo: test"

    # Test with a middleware
    test_middleware = ServerBeforeExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    it = test_client.echoes("test")
    assert test_middleware.called == True
    assert next(it) == "echo: test"
    for echo in it:
        assert echo == "echo: test"

    test_server.stop()
    test_server_task.join()

class ServerAfterExecMiddleware(object):

    def __init__(self):
        self.called = False

    def server_after_exec(self, request_event, reply_event):
        self.called = True
        self.request_event_name = getattr(request_event, 'name', None)
        self.reply_event_name = getattr(reply_event, 'name', None)

def test_hook_server_after_exec():
    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Client()
    test_client.connect(endpoint)

    # Test without a middleware
    assert test_client.echo("test") == "echo: test"

    # Test with a middleware
    test_middleware = ServerAfterExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    assert test_client.echo("test") == "echo: test"
    assert test_middleware.called == True
    assert test_middleware.request_event_name == 'echo'
    assert test_middleware.reply_event_name == 'OK'

    test_server.stop()
    test_server_task.join()

def test_hook_server_after_exec_puller():
    zero_ctx = zerorpc.Context()
    trigger = gevent.event.Event()
    endpoint = random_ipc_endpoint()

    echo_module = EchoModule(trigger)
    test_server = zerorpc.Puller(echo_module, context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Pusher()
    test_client.connect(endpoint)

    # Test without a middleware
    test_client.echo("test")
    trigger.wait(timeout=2)
    assert echo_module.last_msg == "echo: test"
    trigger.clear()

    # Test with a middleware
    test_middleware = ServerAfterExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    test_client.echo("test with a middleware")
    trigger.wait(timeout=2)
    assert echo_module.last_msg == "echo: test with a middleware"
    assert test_middleware.called == True
    assert test_middleware.request_event_name == 'echo'
    assert test_middleware.reply_event_name is None

    test_server.stop()
    test_server_task.join()

def test_hook_server_after_exec_stream():
    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Client()
    test_client.connect(endpoint)

    # Test without a middleware
    for echo in test_client.echoes("test"):
        assert echo == "echo: test"

    # Test with a middleware
    test_middleware = ServerAfterExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    it = test_client.echoes("test")
    assert next(it) == "echo: test"
    assert test_middleware.called == False
    for echo in it:
        assert echo == "echo: test"
    assert test_middleware.called == True
    assert test_middleware.request_event_name == 'echoes'
    assert test_middleware.reply_event_name == 'STREAM_DONE'

    test_server.stop()
    test_server_task.join()

class BrokenEchoModule(object):

    def __init__(self, trigger=None):
        self.last_msg = None
        self._trigger = trigger

    def echo(self, msg):
        try:
            self.last_msg = "Raise"
            raise RuntimeError("BrokenEchoModule")
        finally:
            if self._trigger:
                self._trigger.set()

    @zerorpc.stream
    def echoes(self, msg):
        self.echo(msg)

def test_hook_server_after_exec_on_error():
    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(BrokenEchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Client()
    test_client.connect(endpoint)

    test_middleware = ServerAfterExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    try:
        test_client.echo("test")
    except zerorpc.RemoteError:
        pass
    assert test_middleware.called == False

    test_server.stop()
    test_server_task.join()

def test_hook_server_after_exec_on_error_puller():
    zero_ctx = zerorpc.Context()
    trigger = gevent.event.Event()
    endpoint = random_ipc_endpoint()

    echo_module = BrokenEchoModule(trigger)
    test_server = zerorpc.Puller(echo_module, context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Pusher()
    test_client.connect(endpoint)

    test_middleware = ServerAfterExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    try:
        test_client.echo("test with a middleware")
        trigger.wait(timeout=2)
    except zerorpc.RemoteError:
        pass
    assert echo_module.last_msg == "Raise"
    assert test_middleware.called == False

    test_server.stop()
    test_server_task.join()

def test_hook_server_after_exec_on_error_stream():
    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(BrokenEchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Client()
    test_client.connect(endpoint)

    test_middleware = ServerAfterExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    try:
        test_client.echoes("test")
    except zerorpc.RemoteError:
        pass
    assert test_middleware.called == False

    test_server.stop()
    test_server_task.join()

########NEW FILE########
__FILENAME__ = test_middleware_client
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import gevent
import zerorpc

from testutils import random_ipc_endpoint

class EchoModule(object):

    def __init__(self, trigger=None):
        self.last_msg = None
        self._trigger = trigger

    def echo(self, msg):
        self.last_msg = "echo: " + msg
        if self._trigger:
            self._trigger.set()
        return self.last_msg

    @zerorpc.stream
    def echoes(self, msg):
        self.last_msg = "echo: " + msg
        for i in xrange(0, 3):
            yield self.last_msg

    def crash(self, msg):
        try:
            self.last_msg = "raise: " + msg
            raise RuntimeError("BrokenEchoModule")
        finally:
            if self._trigger:
                self._trigger.set()

    @zerorpc.stream
    def echoes_crash(self, msg):
        self.crash(msg)

    def timeout(self, msg):
        self.last_msg = "timeout: " + msg
        gevent.sleep(2)

def test_hook_client_before_request():

    class ClientBeforeRequestMiddleware(object):
        def __init__(self):
            self.called = False
        def client_before_request(self, event):
            self.called = True
            self.method = event.name

    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(context=zero_ctx)
    test_client.connect(endpoint)

    assert test_client.echo("test") == "echo: test"

    test_middleware = ClientBeforeRequestMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    assert test_client.echo("test") == "echo: test"
    assert test_middleware.called == True
    assert test_middleware.method == 'echo'

    test_server.stop()
    test_server_task.join()

class ClientAfterRequestMiddleware(object):
    def __init__(self):
        self.called = False
    def client_after_request(self, req_event, rep_event, exception):
        self.called = True
        assert req_event is not None
        assert req_event.name == "echo" or req_event.name == "echoes"
        self.retcode = rep_event.name
        assert exception is None

def test_hook_client_after_request():
    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(context=zero_ctx)
    test_client.connect(endpoint)

    assert test_client.echo("test") == "echo: test"

    test_middleware = ClientAfterRequestMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    assert test_client.echo("test") == "echo: test"
    assert test_middleware.called == True
    assert test_middleware.retcode == 'OK'

    test_server.stop()
    test_server_task.join()

def test_hook_client_after_request_stream():
    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(context=zero_ctx)
    test_client.connect(endpoint)

    it = test_client.echoes("test")
    assert next(it) == "echo: test"
    for echo in it:
        assert echo == "echo: test"

    test_middleware = ClientAfterRequestMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    it = test_client.echoes("test")
    assert next(it) == "echo: test"
    assert test_middleware.called == False
    for echo in it:
        assert echo == "echo: test"
    assert test_middleware.called == True
    assert test_middleware.retcode == 'STREAM_DONE'

    test_server.stop()
    test_server_task.join()

def test_hook_client_after_request_timeout():

    class ClientAfterRequestMiddleware(object):
        def __init__(self):
            self.called = False
        def client_after_request(self, req_event, rep_event, exception):
            self.called = True
            assert req_event is not None
            assert req_event.name == "timeout"
            assert rep_event is None

    zero_ctx = zerorpc.Context()
    test_middleware = ClientAfterRequestMiddleware()
    zero_ctx.register_middleware(test_middleware)
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(timeout=1, context=zero_ctx)
    test_client.connect(endpoint)

    assert test_middleware.called == False
    try:
        test_client.timeout("test")
    except zerorpc.TimeoutExpired as ex:
        assert test_middleware.called == True
        assert "timeout" in ex.args[0]

    test_server.stop()
    test_server_task.join()

class ClientAfterFailedRequestMiddleware(object):
    def __init__(self):
        self.called = False
    def client_after_request(self, req_event, rep_event, exception):
        assert req_event is not None
        assert req_event.name == "crash" or req_event.name == "echoes_crash"
        self.called = True
        assert isinstance(exception, zerorpc.RemoteError)
        assert exception.name == 'RuntimeError'
        assert 'BrokenEchoModule' in exception.msg
        assert rep_event.name == 'ERR'

def test_hook_client_after_request_remote_error():

    zero_ctx = zerorpc.Context()
    test_middleware = ClientAfterFailedRequestMiddleware()
    zero_ctx.register_middleware(test_middleware)
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(timeout=1, context=zero_ctx)
    test_client.connect(endpoint)

    assert test_middleware.called == False
    try:
        test_client.crash("test")
    except zerorpc.RemoteError:
        assert test_middleware.called == True

    test_server.stop()
    test_server_task.join()

def test_hook_client_after_request_remote_error_stream():

    zero_ctx = zerorpc.Context()
    test_middleware = ClientAfterFailedRequestMiddleware()
    zero_ctx.register_middleware(test_middleware)
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(timeout=1, context=zero_ctx)
    test_client.connect(endpoint)

    assert test_middleware.called == False
    try:
        test_client.echoes_crash("test")
    except zerorpc.RemoteError:
        assert test_middleware.called == True

    test_server.stop()
    test_server_task.join()

def test_hook_client_handle_remote_error_inspect():

    class ClientHandleRemoteErrorMiddleware(object):
        def __init__(self):
            self.called = False
        def client_handle_remote_error(self, event):
            self.called = True

    test_middleware = ClientHandleRemoteErrorMiddleware()
    zero_ctx = zerorpc.Context()
    zero_ctx.register_middleware(test_middleware)
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(context=zero_ctx)
    test_client.connect(endpoint)

    assert test_middleware.called == False
    try:
        test_client.crash("test")
    except zerorpc.RemoteError as ex:
        assert test_middleware.called == True
        assert ex.name == "RuntimeError"

    test_server.stop()
    test_server_task.join()

# This is a seriously broken idea, but possible nonetheless
class ClientEvalRemoteErrorMiddleware(object):
    def __init__(self):
        self.called = False
    def client_handle_remote_error(self, event):
        self.called = True
        name, msg, tb = event.args
        etype = eval(name)
        e = etype(tb)
        return e

def test_hook_client_handle_remote_error_eval():
    test_middleware = ClientEvalRemoteErrorMiddleware()
    zero_ctx = zerorpc.Context()
    zero_ctx.register_middleware(test_middleware)
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(context=zero_ctx)
    test_client.connect(endpoint)

    assert test_middleware.called == False
    try:
        test_client.crash("test")
    except RuntimeError as ex:
        assert test_middleware.called == True
        assert "BrokenEchoModule" in ex.args[0]

    test_server.stop()
    test_server_task.join()

def test_hook_client_handle_remote_error_eval_stream():
    test_middleware = ClientEvalRemoteErrorMiddleware()
    zero_ctx = zerorpc.Context()
    zero_ctx.register_middleware(test_middleware)
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(context=zero_ctx)
    test_client.connect(endpoint)

    assert test_middleware.called == False
    try:
        test_client.echoes_crash("test")
    except RuntimeError as ex:
        assert test_middleware.called == True
        assert "BrokenEchoModule" in ex.args[0]

    test_server.stop()
    test_server_task.join()

def test_hook_client_after_request_custom_error():

    # This is a seriously broken idea, but possible nonetheless
    class ClientEvalInspectRemoteErrorMiddleware(object):
        def __init__(self):
            self.called = False
        def client_handle_remote_error(self, event):
            name, msg, tb = event.args
            etype = eval(name)
            e = etype(tb)
            return e
        def client_after_request(self, req_event, rep_event, exception):
            assert req_event is not None
            assert req_event.name == "crash"
            self.called = True
            assert isinstance(exception, RuntimeError)

    test_middleware = ClientEvalInspectRemoteErrorMiddleware()
    zero_ctx = zerorpc.Context()
    zero_ctx.register_middleware(test_middleware)
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(context=zero_ctx)
    test_client.connect(endpoint)

    assert test_middleware.called == False
    try:
        test_client.crash("test")
    except RuntimeError as ex:
        assert test_middleware.called == True
        assert "BrokenEchoModule" in ex.args[0]

    test_server.stop()
    test_server_task.join()

########NEW FILE########
__FILENAME__ = test_pubpush
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import gevent
import gevent.event
import zerorpc

from testutils import teardown, random_ipc_endpoint


def test_pushpull_inheritance():
    endpoint = random_ipc_endpoint()

    pusher = zerorpc.Pusher()
    pusher.bind(endpoint)
    trigger = gevent.event.Event()

    class Puller(zerorpc.Puller):
        def lolita(self, a, b):
            print 'lolita', a, b
            assert a + b == 3
            trigger.set()

    puller = Puller()
    puller.connect(endpoint)
    gevent.spawn(puller.run)

    trigger.clear()
    pusher.lolita(1, 2)
    trigger.wait()
    print 'done'


def test_pubsub_inheritance():
    endpoint = random_ipc_endpoint()

    publisher = zerorpc.Publisher()
    publisher.bind(endpoint)
    trigger = gevent.event.Event()

    class Subscriber(zerorpc.Subscriber):
        def lolita(self, a, b):
            print 'lolita', a, b
            assert a + b == 3
            trigger.set()

    subscriber = Subscriber()
    subscriber.connect(endpoint)
    gevent.spawn(subscriber.run)

    trigger.clear()
    # We need this retry logic to wait that the subscriber.run coroutine starts
    # reading (the published messages will go to /dev/null until then).
    for attempt in xrange(0, 10):
        publisher.lolita(1, 2)
        if trigger.wait(0.2):
            print 'done'
            return

    raise RuntimeError("The subscriber didn't receive any published message")

def test_pushpull_composite():
    endpoint = random_ipc_endpoint()
    trigger = gevent.event.Event()

    class Puller(object):
        def lolita(self, a, b):
            print 'lolita', a, b
            assert a + b == 3
            trigger.set()

    pusher = zerorpc.Pusher()
    pusher.bind(endpoint)

    service = Puller()
    puller = zerorpc.Puller(service)
    puller.connect(endpoint)
    gevent.spawn(puller.run)

    trigger.clear()
    pusher.lolita(1, 2)
    trigger.wait()
    print 'done'


def test_pubsub_composite():
    endpoint = random_ipc_endpoint()
    trigger = gevent.event.Event()

    class Subscriber(object):
        def lolita(self, a, b):
            print 'lolita', a, b
            assert a + b == 3
            trigger.set()

    publisher = zerorpc.Publisher()
    publisher.bind(endpoint)

    service = Subscriber()
    subscriber = zerorpc.Subscriber(service)
    subscriber.connect(endpoint)
    gevent.spawn(subscriber.run)

    trigger.clear()
    # We need this retry logic to wait that the subscriber.run coroutine starts
    # reading (the published messages will go to /dev/null until then).
    for attempt in xrange(0, 10):
        publisher.lolita(1, 2)
        if trigger.wait(0.2):
            print 'done'
            return

    raise RuntimeError("The subscriber didn't receive any published message")

########NEW FILE########
__FILENAME__ = test_reqstream
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import gevent

import zerorpc
from testutils import teardown, random_ipc_endpoint


def test_rcp_streaming():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        @zerorpc.rep
        def range(self, max):
            return range(max)

        @zerorpc.stream
        def xrange(self, max):
            return xrange(max)

    srv = MySrv(heartbeat=2)
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(heartbeat=2)
    client.connect(endpoint)

    r = client.range(10)
    assert list(r) == list(range(10))

    r = client.xrange(10)
    assert getattr(r, 'next', None) is not None
    l = []
    print 'wait 4s for fun'
    gevent.sleep(4)
    for x in r:
        l.append(x)
    assert l == range(10)

########NEW FILE########
__FILENAME__ = test_server
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from nose.tools import assert_raises
import gevent
import sys

from zerorpc import zmq
import zerorpc
from testutils import teardown, random_ipc_endpoint


def test_server_manual():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

        def add(self, a, b):
            return a + b

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_channel.emit('lolita', tuple())
    event = client_channel.recv()
    assert list(event.args) == [42]
    client_channel.close()

    client_channel = client.channel()
    client_channel.emit('add', (1, 2))
    event = client_channel.recv()
    assert list(event.args) == [3]
    client_channel.close()
    srv.stop()


def test_client_server():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

        def add(self, a, b):
            return a + b

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client()
    client.connect(endpoint)

    print client.lolita()
    assert client.lolita() == 42

    print client.add(1, 4)
    assert client.add(1, 4) == 5


def test_client_server_client_timeout():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

        def add(self, a, b):
            gevent.sleep(10)
            return a + b

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(timeout=2)
    client.connect(endpoint)

    if sys.version_info < (2, 7):
        assert_raises(zerorpc.TimeoutExpired, client.add, 1, 4)
    else:
        with assert_raises(zerorpc.TimeoutExpired):
            print client.add(1, 4)
    client.close()
    srv.close()


def test_client_server_exception():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def raise_something(self, a):
            return a[4]

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(timeout=2)
    client.connect(endpoint)

    if sys.version_info < (2, 7):
        def _do_with_assert_raises():
            print client.raise_something(42)
        assert_raises(zerorpc.RemoteError, _do_with_assert_raises)
    else:
        with assert_raises(zerorpc.RemoteError):
            print client.raise_something(42)
    assert client.raise_something(range(5)) == 4
    client.close()
    srv.close()


def test_client_server_detailed_exception():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def raise_error(self):
            raise RuntimeError('oops!')

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(timeout=2)
    client.connect(endpoint)

    if sys.version_info < (2, 7):
        def _do_with_assert_raises():
            print client.raise_error()
        assert_raises(zerorpc.RemoteError, _do_with_assert_raises)
    else:
        with assert_raises(zerorpc.RemoteError):
            print client.raise_error()
    try:
        client.raise_error()
    except zerorpc.RemoteError as e:
        print 'got that:', e
        print 'name', e.name
        print 'msg', e.msg
        assert e.name == 'RuntimeError'
        assert e.msg == 'oops!'

    client.close()
    srv.close()


def test_exception_compat_v1():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):
        pass

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    rpccall = client.channel()
    rpccall.emit('donotexist', tuple())
    event = rpccall.recv()
    print event
    assert event.name == 'ERR'
    (name, msg, tb) = event.args
    print 'detailed error', name, msg, tb
    assert name == 'NameError'
    assert msg == 'donotexist'

    rpccall = client.channel()
    rpccall.emit('donotexist', tuple(), xheader=dict(v=1))
    event = rpccall.recv()
    print event
    assert event.name == 'ERR'
    (msg,) = event.args
    print 'msg only', msg
    assert msg == "NameError('donotexist',)"

    client_events.close()
    srv.close()


def test_removed_unscriptable_error_format_args_spec():

    class MySrv(zerorpc.Server):
        pass

    srv = MySrv()
    return_value = srv._format_args_spec(None)
    assert return_value is None

########NEW FILE########
__FILENAME__ = test_wrapped_events
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import random
import gevent

from zerorpc import zmq
import zerorpc
from testutils import teardown, random_ipc_endpoint


def test_sub_events():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_channel_events = zerorpc.WrappedEvents(client_channel)
    client_channel_events.emit('coucou', 42)

    event = server.recv()
    print event
    assert isinstance(event.args, (list, tuple))
    assert event.name == 'w'
    subevent = event.args
    print 'subevent:', subevent
    server_channel = server.channel(event)
    server_channel_events = zerorpc.WrappedEvents(server_channel)
    server_channel_channel = zerorpc.ChannelMultiplexer(server_channel_events)
    event = server_channel_channel.recv()
    print event
    assert event.name == 'coucou'
    assert event.args == 42

    server_events.close()
    client_events.close()


def test_multiple_sub_events():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel1 = client.channel()
    client_channel_events1 = zerorpc.WrappedEvents(client_channel1)
    client_channel2 = zerorpc.BufferedChannel(client.channel())
    client_channel_events2 = zerorpc.WrappedEvents(client_channel2)

    def emitstuff():
        client_channel_events1.emit('coucou1', 43)
        client_channel_events2.emit('coucou2', 44)
        client_channel_events2.emit('another', 42)
    gevent.spawn(emitstuff)

    event = server.recv()
    print event
    assert isinstance(event.args, (list, tuple))
    assert event.name == 'w'
    subevent = event.args
    print 'subevent:', subevent
    server_channel = server.channel(event)
    server_channel_events = zerorpc.WrappedEvents(server_channel)
    event = server_channel_events.recv()
    print 'ch1:', event
    assert event.name == 'coucou1'
    assert event.args == 43

    event = server.recv()
    print event
    assert isinstance(event.args, (list, tuple))
    assert event.name == 'w'
    subevent = event.args
    print 'subevent:', subevent
    server_channel = server.channel(event)

    server_channel_events = zerorpc.BufferedChannel(server_channel)
    server_channel_events = zerorpc.WrappedEvents(server_channel_events)
    event = server_channel_events.recv()
    print 'ch2:', event
    assert event.name == 'coucou2'
    assert event.args == 44

    event = server_channel_events.recv()
    print 'ch2:', event
    assert event.name == 'another'
    assert event.args == 42

    server_events.close()
    client_events.close()


def test_recursive_multiplexer():
    endpoint = random_ipc_endpoint()

    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    servermux = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    clientmux = zerorpc.ChannelMultiplexer(client_events,
        ignore_broadcast=True)

    def ping_pong(climux, srvmux):
        cli_chan = climux.channel()
        someid = random.randint(0, 1000000)
        print 'ping...'
        cli_chan.emit('ping', someid)
        print 'srv_chan got:'
        event = srvmux.recv()
        srv_chan = srvmux.channel(event)
        print event
        assert event.name == 'ping'
        assert event.args == someid
        print 'pong...'
        srv_chan.emit('pong', someid)
        print 'cli_chan got:'
        event = cli_chan.recv()
        print event
        assert event.name == 'pong'
        assert event.args == someid
        srv_chan.close()
        cli_chan.close()

    def create_sub_multiplexer(events, from_event=None,
            ignore_broadcast=False):
        channel = events.channel(from_event)
        sub_events = zerorpc.WrappedEvents(channel)
        sub_multiplexer = zerorpc.ChannelMultiplexer(sub_events,
                ignore_broadcast=ignore_broadcast)
        return sub_multiplexer

    def open_sub_multiplexer(climux, srvmux):
        someid = random.randint(0, 1000000)
        print 'open...'
        clisubmux = create_sub_multiplexer(climux, ignore_broadcast=True)
        clisubmux.emit('open that', someid)
        print 'srvsubmux got:'
        event = srvmux.recv()
        assert event.name == 'w'
        srvsubmux = create_sub_multiplexer(srvmux, event)
        event = srvsubmux.recv()
        print event
        return (clisubmux, srvsubmux)

    ping_pong(clientmux, servermux)

    (clientmux_lv2, servermux_lv2) = open_sub_multiplexer(clientmux, servermux)
    ping_pong(clientmux_lv2, servermux_lv2)

    (clientmux_lv3, servermux_lv3) = open_sub_multiplexer(clientmux_lv2,
            servermux_lv2)
    ping_pong(clientmux_lv3, servermux_lv3)

    (clientmux_lv4, servermux_lv4) = open_sub_multiplexer(clientmux_lv3,
            servermux_lv3)
    ping_pong(clientmux_lv4, servermux_lv4)

    ping_pong(clientmux_lv4, servermux_lv4)
    ping_pong(clientmux_lv3, servermux_lv3)
    ping_pong(clientmux_lv2, servermux_lv2)
    ping_pong(clientmux, servermux)
    ping_pong(clientmux, servermux)
    ping_pong(clientmux_lv2, servermux_lv2)
    ping_pong(clientmux_lv4, servermux_lv4)
    ping_pong(clientmux_lv3, servermux_lv3)

    (clientmux_lv5, servermux_lv5) = open_sub_multiplexer(clientmux_lv4,
            servermux_lv4)
    ping_pong(clientmux_lv5, servermux_lv5)

########NEW FILE########
__FILENAME__ = test_zmq
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import gevent

from zerorpc import zmq


def test1():
    def server():
        c = zmq.Context()
        s = c.socket(zmq.REP)
        s.bind('tcp://0.0.0.0:9999')
        while True:
            print 'srv recving...'
            r = s.recv()
            print 'srv', r
            print 'srv sending...'
            s.send('world')

        s.close()
        c.term()

    def client():
        c = zmq.Context()
        s = c.socket(zmq.REQ)
        s.connect('tcp://localhost:9999')

        print 'cli sending...'
        s.send('hello')
        print 'cli recving...'
        r = s.recv()
        print 'cli', r

        s.close()
        c.term()

    s = gevent.spawn(server)
    c = gevent.spawn(client)
    c.join()

########NEW FILE########
__FILENAME__ = zmqbug
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Based on https://github.com/traviscline/gevent-zeromq/blob/master/gevent_zeromq/core.py


import zmq

import gevent.event
import gevent.core

STOP_EVERYTHING = False


class ZMQSocket(zmq.Socket):

    def __init__(self, context, socket_type):
        super(ZMQSocket, self).__init__(context, socket_type)
        on_state_changed_fd = self.getsockopt(zmq.FD)
        self._readable = gevent.event.Event()
        self._writable = gevent.event.Event()
        try:
            # gevent>=1.0
            self._state_event = gevent.hub.get_hub().loop.io(
                on_state_changed_fd, gevent.core.READ)
            self._state_event.start(self._on_state_changed)
        except AttributeError:
            # gevent<1.0
            self._state_event = gevent.core.read_event(on_state_changed_fd,
                    self._on_state_changed, persist=True)

    def _on_state_changed(self, event=None, _evtype=None):
        if self.closed:
            self._writable.set()
            self._readable.set()
            return

        events = self.getsockopt(zmq.EVENTS)
        if events & zmq.POLLOUT:
            self._writable.set()
        if events & zmq.POLLIN:
            self._readable.set()

    def close(self):
        if not self.closed and getattr(self, '_state_event', None):
            try:
                # gevent>=1.0
                self._state_event.stop()
            except AttributeError:
                # gevent<1.0
                self._state_event.cancel()
        super(ZMQSocket, self).close()

    def send(self, data, flags=0, copy=True, track=False):
        if flags & zmq.NOBLOCK:
            return super(ZMQSocket, self).send(data, flags, copy, track)
        flags |= zmq.NOBLOCK
        while True:
            try:
                return super(ZMQSocket, self).send(data, flags, copy, track)
            except zmq.ZMQError, e:
                if e.errno != zmq.EAGAIN:
                    raise
            self._writable.clear()
            self._writable.wait()

    def recv(self, flags=0, copy=True, track=False):
        if flags & zmq.NOBLOCK:
            return super(ZMQSocket, self).recv(flags, copy, track)
        flags |= zmq.NOBLOCK
        while True:
            try:
                return super(ZMQSocket, self).recv(flags, copy, track)
            except zmq.ZMQError, e:
                if e.errno != zmq.EAGAIN:
                    raise
            self._readable.clear()
            while not self._readable.wait(timeout=10):
                events = self.getsockopt(zmq.EVENTS)
                if bool(events & zmq.POLLIN):
                    print "here we go, nobody told me about new messages!"
                    global STOP_EVERYTHING
                    STOP_EVERYTHING = True
                    raise gevent.GreenletExit()

zmq_context = zmq.Context()


def server():
    socket = ZMQSocket(zmq_context, zmq.REP)
    socket.bind('ipc://zmqbug')

    class Cnt:
        responded = 0

    cnt = Cnt()

    def responder():
        while not STOP_EVERYTHING:
            msg = socket.recv()
            socket.send(msg)
            cnt.responded += 1

    gevent.spawn(responder)

    while not STOP_EVERYTHING:
        print "cnt.responded=", cnt.responded
        gevent.sleep(0.5)


def client():
    socket = ZMQSocket(zmq_context, zmq.DEALER)
    socket.connect('ipc://zmqbug')

    class Cnt:
        recv = 0
        send = 0

    cnt = Cnt()

    def recvmsg():
        while not STOP_EVERYTHING:
            socket.recv()
            socket.recv()
            cnt.recv += 1

    def sendmsg():
        while not STOP_EVERYTHING:
            socket.send('', flags=zmq.SNDMORE)
            socket.send('hello')
            cnt.send += 1
            gevent.sleep(0)

    gevent.spawn(recvmsg)
    gevent.spawn(sendmsg)

    while not STOP_EVERYTHING:
        print "cnt.recv=", cnt.recv, "cnt.send=", cnt.send
        gevent.sleep(0.5)

gevent.spawn(server)
client()

########NEW FILE########
__FILENAME__ = channel
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import gevent.pool
import gevent.queue
import gevent.event
import gevent.local
import gevent.lock

from .exceptions import TimeoutExpired

from logging import getLogger

logger = getLogger(__name__)


class ChannelMultiplexer(object):
    def __init__(self, events, ignore_broadcast=False):
        self._events = events
        self._active_channels = {}
        self._channel_dispatcher_task = None
        self._broadcast_queue = None
        if events.recv_is_available and not ignore_broadcast:
            self._broadcast_queue = gevent.queue.Queue(maxsize=1)
            self._channel_dispatcher_task = gevent.spawn(
                self._channel_dispatcher)

    @property
    def recv_is_available(self):
        return self._events.recv_is_available

    def __del__(self):
        self.close()

    def close(self):
        if self._channel_dispatcher_task:
            self._channel_dispatcher_task.kill()

    def create_event(self, name, args, xheader=None):
        return self._events.create_event(name, args, xheader)

    def emit_event(self, event, identity=None):
        return self._events.emit_event(event, identity)

    def emit(self, name, args, xheader=None):
        return self._events.emit(name, args, xheader)

    def recv(self):
        if self._broadcast_queue is not None:
            event = self._broadcast_queue.get()
        else:
            event = self._events.recv()
        return event

    def _channel_dispatcher(self):
        while True:
            try:
                event = self._events.recv()
            except Exception as e:
                logger.error(
                    'zerorpc.ChannelMultiplexer, '
                    'ignoring error on recv: {0}'.format(e))
                continue
            channel_id = event.header.get('response_to', None)

            queue = None
            if channel_id is not None:
                channel = self._active_channels.get(channel_id, None)
                if channel is not None:
                    queue = channel._queue
            elif self._broadcast_queue is not None:
                queue = self._broadcast_queue

            if queue is None:
                logger.error(
                    'zerorpc.ChannelMultiplexer, '
                    'unable to route event: {0}'
                    .format(event.__str__(ignore_args=True)))
            else:
                queue.put(event)

    def channel(self, from_event=None):
        if self._channel_dispatcher_task is None:
            self._channel_dispatcher_task = gevent.spawn(
                self._channel_dispatcher)
        return Channel(self, from_event)

    @property
    def active_channels(self):
        return self._active_channels

    @property
    def context(self):
        return self._events.context


class Channel(object):

    def __init__(self, multiplexer, from_event=None):
        self._multiplexer = multiplexer
        self._channel_id = None
        self._zmqid = None
        self._queue = gevent.queue.Queue(maxsize=1)
        if from_event is not None:
            self._channel_id = from_event.header['message_id']
            self._zmqid = from_event.header.get('zmqid', None)
            self._multiplexer._active_channels[self._channel_id] = self
            self._queue.put(from_event)

    @property
    def recv_is_available(self):
        return self._multiplexer.recv_is_available

    def __del__(self):
        self.close()

    def close(self):
        if self._channel_id is not None:
            del self._multiplexer._active_channels[self._channel_id]
            self._channel_id = None

    def create_event(self, name, args, xheader=None):
        event = self._multiplexer.create_event(name, args, xheader)
        if self._channel_id is None:
            self._channel_id = event.header['message_id']
            self._multiplexer._active_channels[self._channel_id] = self
        else:
            event.header['response_to'] = self._channel_id
        return event

    def emit(self, name, args, xheader=None):
        event = self.create_event(name, args, xheader)
        self._multiplexer.emit_event(event, self._zmqid)

    def emit_event(self, event):
        self._multiplexer.emit_event(event, self._zmqid)

    def recv(self, timeout=None):
        try:
            event = self._queue.get(timeout=timeout)
        except gevent.queue.Empty:
            raise TimeoutExpired(timeout)
        return event

    @property
    def context(self):
        return self._multiplexer.context


class BufferedChannel(object):

    def __init__(self, channel, inqueue_size=100):
        self._channel = channel
        self._input_queue_size = inqueue_size
        self._remote_queue_open_slots = 1
        self._input_queue_reserved = 1
        self._remote_can_recv = gevent.event.Event()
        self._input_queue = gevent.queue.Queue()
        self._lost_remote = False
        self._verbose = False
        self._on_close_if = None
        self._recv_task = gevent.spawn(self._recver)

    @property
    def recv_is_available(self):
        return self._channel.recv_is_available

    @property
    def on_close_if(self):
        return self._on_close_if

    @on_close_if.setter
    def on_close_if(self, cb):
        self._on_close_if = cb

    def __del__(self):
        self.close()

    def close(self):
        if self._recv_task is not None:
            self._recv_task.kill()
            self._recv_task = None
        if self._channel is not None:
            self._channel.close()
            self._channel = None

    def _recver(self):
        while True:
            event = self._channel.recv()
            if event.name == '_zpc_more':
                try:
                    self._remote_queue_open_slots += int(event.args[0])
                except Exception as e:
                    logger.error(
                        'gevent_zerorpc.BufferedChannel._recver, '
                        'exception: ' + repr(e))
                if self._remote_queue_open_slots > 0:
                    self._remote_can_recv.set()
            elif self._input_queue.qsize() == self._input_queue_size:
                raise RuntimeError(
                    'BufferedChannel, queue overflow on event:', event)
            else:
                self._input_queue.put(event)
                if self._on_close_if is not None and self._on_close_if(event):
                    self._recv_task = None
                    self.close()
                    return

    def create_event(self, name, args, xheader=None):
        return self._channel.create_event(name, args, xheader)

    def emit_event(self, event, block=True, timeout=None):
        if self._remote_queue_open_slots == 0:
            if not block:
                return False
            self._remote_can_recv.clear()
            self._remote_can_recv.wait(timeout=timeout)
        self._remote_queue_open_slots -= 1
        try:
            self._channel.emit_event(event)
        except:
            self._remote_queue_open_slots += 1
            raise
        return True

    def emit(self, name, args, xheader=None, block=True, timeout=None):
        event = self.create_event(name, args, xheader)
        return self.emit_event(event, block, timeout)

    def _request_data(self):
        open_slots = self._input_queue_size - self._input_queue_reserved
        self._input_queue_reserved += open_slots
        self._channel.emit('_zpc_more', (open_slots,))

    def recv(self, timeout=None):
        if self._verbose:
            if self._input_queue_reserved < self._input_queue_size / 2:
                self._request_data()
        else:
            self._verbose = True

        try:
            event = self._input_queue.get(timeout=timeout)
        except gevent.queue.Empty:
            raise TimeoutExpired(timeout)

        self._input_queue_reserved -= 1
        return event

    @property
    def channel(self):
        return self._channel

    @property
    def context(self):
        return self._channel.context

########NEW FILE########
__FILENAME__ = cli
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import argparse
import json
import sys
import inspect
import os
from pprint import pprint

import zerorpc


parser = argparse.ArgumentParser(
    description='Make a zerorpc call to a remote service.'
)

client_or_server = parser.add_mutually_exclusive_group()
client_or_server.add_argument('--client', action='store_true', default=True,
        help='remote procedure call mode (default)')
client_or_server.add_argument('--server', action='store_false', dest='client',
        help='turn a given python module into a server')

parser.add_argument('--connect', action='append', metavar='address',
                    help='specify address to connect to. Can be specified \
                    multiple times and in conjunction with --bind')
parser.add_argument('--bind', action='append', metavar='address',
                    help='specify address to listen to. Can be specified \
                    multiple times and in conjunction with --connect')
parser.add_argument('--timeout', default=30, metavar='seconds', type=int,
                    help='abort request after X seconds. \
                    (default: 30s, --client only)')
parser.add_argument('--heartbeat', default=5, metavar='seconds', type=int,
                    help='heartbeat frequency. You should always use \
                    the same frequency as the server. (default: 5s)')
parser.add_argument('-j', '--json', default=False, action='store_true',
                    help='arguments are in JSON format and will be be parsed \
                    before being sent to the remote')
parser.add_argument('-pj', '--print-json', default=False, action='store_true',
                    help='print result in JSON format.')
parser.add_argument('-?', '--inspect', default=False, action='store_true',
                    help='retrieve detailed informations for the given \
                    remote (cf: command) method. If not method, display \
                    a list of remote methods signature. (only for --client).')
parser.add_argument('--active-hb', default=False, action='store_true',
                    help='enable active heartbeat. The default is to \
                    wait for the server to send the first heartbeat')
parser.add_argument('address', nargs='?', help='address to connect to. Skip \
                    this if you specified --connect or --bind at least once')
parser.add_argument('command', nargs='?',
                    help='remote procedure to call if --client (default) or \
                    python module/class to load if --server. If no command is \
                    specified, a list of remote methods are displayed.')
parser.add_argument('params', nargs='*',
                    help='parameters for the remote call if --client \
                    (default)')


def setup_links(args, socket):
    if args.bind:
        for endpoint in args.bind:
            print 'binding to "{0}"'.format(endpoint)
            socket.bind(endpoint)
    addresses = []
    if args.address:
        addresses.append(args.address)
    if args.connect:
        addresses.extend(args.connect)
    for endpoint in addresses:
        print 'connecting to "{0}"'.format(endpoint)
        socket.connect(endpoint)


def run_server(args):
    server_obj_path = args.command

    sys.path.insert(0, os.getcwd())
    if '.' in server_obj_path:
        modulepath, objname = server_obj_path.rsplit('.', 1)
        module = __import__(modulepath, fromlist=[objname])
        server_obj = getattr(module, objname)
    else:
        server_obj = __import__(server_obj_path)

    if callable(server_obj):
        server_obj = server_obj()

    server = zerorpc.Server(server_obj, heartbeat=args.heartbeat)
    setup_links(args, server)
    print 'serving "{0}"'.format(server_obj_path)
    return server.run()


# this function does a really intricate job to keep backward compatibility
# with a previous version of zerorpc, and lazily retrieving results if possible
def zerorpc_inspect_legacy(client, filter_method, long_doc, include_argspec):
    if filter_method is None:
        remote_methods = client._zerorpc_list()
    else:
        remote_methods = [filter_method]

    def remote_detailled_methods():
        for name in remote_methods:
            if include_argspec:
                argspec = client._zerorpc_args(name)
            else:
                argspec = None
            docstring = client._zerorpc_help(name)
            if docstring and not long_doc:
                docstring = docstring.split('\n', 1)[0]
            yield (name, argspec, docstring if docstring else '<undocumented>')

    if not include_argspec:
        longest_name_len = max(len(name) for name in remote_methods)
        return (longest_name_len, ((name, doc) for name, argspec, doc in
            remote_detailled_methods()))

    r = [(name + (inspect.formatargspec(*argspec)
                  if argspec else '(...)'), doc)
         for name, argspec, doc in remote_detailled_methods()]
    longest_name_len = max(len(name) for name, doc in r)
    return (longest_name_len, r)


# handle the 'python formatted' _zerorpc_inspect, that return the output of
# "getargspec" from the python lib "inspect".
def zerorpc_inspect_python_argspecs(remote_methods, filter_method, long_doc, include_argspec):
    def format_method(name, argspec, doc):
        if include_argspec:
            name += (inspect.formatargspec(*argspec) if argspec else
                '(...)')
        if not doc:
            doc = '<undocumented>'
        elif not long_doc:
            doc = doc.splitlines()[0]
        return (name, doc)
    r = [format_method(*methods_info) for methods_info in remote_methods if
         filter_method is None or methods_info[0] == filter_method]
    longest_name_len = max(len(name) for name, doc in r)
    return (longest_name_len, r)


def zerorpc_inspect_generic(remote_methods, filter_method, long_doc, include_argspec):
    def format_method(name, args, doc):
        if include_argspec:
            def format_arg(arg):
                def_val = arg.get('default')
                if def_val is None:
                    return arg['name']
                return '{0}={1}'.format(arg['name'], def_val)

            name += '({0})'.format(', '.join(map(format_arg, args)))
        if not doc:
            doc = '<undocumented>'
        elif not long_doc:
            doc = doc.splitlines()[0]
        return (name, doc)

    methods = [format_method(name, details['args'], details['doc']) for name, details in remote_methods.items()
            if filter_method is None or name == filter_method]

    longest_name_len = max(len(name) for name, doc in methods)
    return (longest_name_len, methods)


def zerorpc_inspect(client, method=None, long_doc=True, include_argspec=True):
    try:
        remote_methods = client._zerorpc_inspect()['methods']
        legacy = False
    except (zerorpc.RemoteError, NameError):
        legacy = True

    if legacy:
        return zerorpc_inspect_legacy(client, method,
                long_doc, include_argspec)

    if not isinstance(remote_methods, dict):
        return zerorpc_inspect_python_argspecs(remote_methods, method, long_doc,
                include_argspec)

    return zerorpc_inspect_generic(remote_methods, method, long_doc,
            include_argspec)


def run_client(args):
    client = zerorpc.Client(timeout=args.timeout, heartbeat=args.heartbeat,
            passive_heartbeat=not args.active_hb)
    setup_links(args, client)
    if not args.command:
        (longest_name_len, detailled_methods) = zerorpc_inspect(client,
                long_doc=False, include_argspec=args.inspect)
        if args.inspect:
            for (name, doc) in detailled_methods:
                print name
        else:
            for (name, doc) in detailled_methods:
                print '{0} {1}'.format(name.ljust(longest_name_len), doc)
        return
    if args.inspect:
        (longest_name_len, detailled_methods) = zerorpc_inspect(client,
                method=args.command)
        (name, doc) = detailled_methods[0]
        print '\n{0}\n\n{1}\n'.format(name, doc)
        return
    if args.json:
        call_args = [json.loads(x) for x in args.params]
    else:
        call_args = args.params
    results = client(args.command, *call_args)
    if getattr(results, 'next', None) is None:
        if args.print_json:
            json.dump(results, sys.stdout)
        else:
            pprint(results)
    else:
        # streaming responses
        if args.print_json:
            first = True
            sys.stdout.write('[')
            for result in results:
                if first:
                    first = False
                else:
                    sys.stdout.write(',')
                json.dump(result, sys.stdout)
            sys.stdout.write(']')
        else:
            for result in results:
                pprint(result)


def main():
    args = parser.parse_args()

    if args.bind or args.connect:
        if args.command:
            args.params.insert(0, args.command)
        args.command = args.address
        args.address = None

    if not (args.bind or args.connect or args.address):
        parser.print_help()
        return -1

    if args.client:
        return run_client(args)

    if not args.command:
        parser.print_help()
        return -1

    return run_server(args)

########NEW FILE########
__FILENAME__ = context
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import uuid
import random

import gevent_zmq as zmq


class Context(zmq.Context):
    _instance = None

    def __init__(self):
        super(zmq.Context, self).__init__()
        self._middlewares = []
        self._hooks = {
            'resolve_endpoint': [],
            'load_task_context': [],
            'get_task_context': [],
            'server_before_exec': [],
            'server_after_exec': [],
            'server_inspect_exception': [],
            'client_handle_remote_error': [],
            'client_before_request': [],
            'client_after_request': []
        }
        self._reset_msgid()

    # NOTE: pyzmq 13.0.0 messed up with setattr (they turned it into a
    # non-op) and you can't assign attributes normally anymore, hence the
    # tricks with self.__dict__ here

    @property
    def _middlewares(self):
        return self.__dict__['_middlewares']

    @_middlewares.setter
    def _middlewares(self, value):
        self.__dict__['_middlewares'] = value

    @property
    def _hooks(self):
        return self.__dict__['_hooks']

    @_hooks.setter
    def _hooks(self, value):
        self.__dict__['_hooks'] = value

    @property
    def _msg_id_base(self):
        return self.__dict__['_msg_id_base']

    @_msg_id_base.setter
    def _msg_id_base(self, value):
        self.__dict__['_msg_id_base'] = value

    @property
    def _msg_id_counter(self):
        return self.__dict__['_msg_id_counter']

    @_msg_id_counter.setter
    def _msg_id_counter(self, value):
        self.__dict__['_msg_id_counter'] = value

    @property
    def _msg_id_counter_stop(self):
        return self.__dict__['_msg_id_counter_stop']

    @_msg_id_counter_stop.setter
    def _msg_id_counter_stop(self, value):
        self.__dict__['_msg_id_counter_stop'] = value

    @staticmethod
    def get_instance():
        if Context._instance is None:
            Context._instance = Context()
        return Context._instance

    def _reset_msgid(self):
        self._msg_id_base = str(uuid.uuid4())[8:]
        self._msg_id_counter = random.randrange(0, 2 ** 32)
        self._msg_id_counter_stop = random.randrange(self._msg_id_counter, 2 ** 32)

    def new_msgid(self):
        if self._msg_id_counter >= self._msg_id_counter_stop:
            self._reset_msgid()
        else:
            self._msg_id_counter = (self._msg_id_counter + 1)
        return '{0:08x}{1}'.format(self._msg_id_counter, self._msg_id_base)

    def register_middleware(self, middleware_instance):
        registered_count = 0
        self._middlewares.append(middleware_instance)
        for hook in self._hooks.keys():
            functor = getattr(middleware_instance, hook, None)
            if functor is None:
                try:
                    functor = middleware_instance.get(hook, None)
                except AttributeError:
                    pass
            if functor is not None:
                self._hooks[hook].append(functor)
                registered_count += 1
        return registered_count

    #
    # client/server
    #
    def hook_resolve_endpoint(self, endpoint):
        for functor in self._hooks['resolve_endpoint']:
            endpoint = functor(endpoint)
        return endpoint

    def hook_load_task_context(self, event_header):
        for functor in self._hooks['load_task_context']:
            functor(event_header)

    def hook_get_task_context(self):
        event_header = {}
        for functor in self._hooks['get_task_context']:
            event_header.update(functor())
        return event_header

    #
    # Server-side hooks
    #
    def hook_server_before_exec(self, request_event):
        """Called when a method is about to be executed on the server."""

        for functor in self._hooks['server_before_exec']:
            functor(request_event)

    def hook_server_after_exec(self, request_event, reply_event):
        """Called when a method has been executed successfully.

        This hook is called right before the answer is sent back to the client.
        If the method streams its answer (i.e: it uses the zerorpc.stream
        decorator) then this hook will be called once the reply has been fully
        streamed (and right before the stream is "closed").

        The reply_event argument will be None if the Push/Pull pattern is used.

        """
        for functor in self._hooks['server_after_exec']:
            functor(request_event, reply_event)

    def hook_server_inspect_exception(self, request_event, reply_event, exc_infos):
        """Called when a method raised an exception.

        The reply_event argument will be None if the Push/Pull pattern is used.

        """
        task_context = self.hook_get_task_context()
        for functor in self._hooks['server_inspect_exception']:
            functor(request_event, reply_event, task_context, exc_infos)

    #
    # Client-side hooks
    #
    def hook_client_handle_remote_error(self, event):
        exception = None
        for functor in self._hooks['client_handle_remote_error']:
            ret = functor(event)
            if ret:
                exception = ret
        return exception

    def hook_client_before_request(self, event):
        """Called when the Client is about to send a request.

        You can see it as the counterpart of ``hook_server_before_exec``.

        """
        for functor in self._hooks['client_before_request']:
            functor(event)

    def hook_client_after_request(self, request_event, reply_event, exception=None):
        """Called when an answer or a timeout has been received from the server.

        This hook is called right before the answer is returned to the client.
        You can see it as the counterpart of the ``hook_server_after_exec``.

        If the called method was returning a stream (i.e: it uses the
        zerorpc.stream decorator) then this hook will be called once the reply
        has been fully streamed (when the stream is "closed") or when an
        exception has been raised.

        The optional exception argument will be a ``RemoteError`` (or whatever
        type returned by the client_handle_remote_error hook) if an exception
        has been raised on the server.

        If the request timed out, then the exception argument will be a
        ``TimeoutExpired`` object and reply_event will be None.

        """
        for functor in self._hooks['client_after_request']:
            functor(request_event, reply_event, exception)

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import sys
import traceback
import gevent.pool
import gevent.queue
import gevent.event
import gevent.local
import gevent.lock

import gevent_zmq as zmq
from .exceptions import TimeoutExpired, RemoteError, LostRemote
from .channel import ChannelMultiplexer, BufferedChannel
from .socket import SocketBase
from .heartbeat import HeartBeatOnChannel
from .context import Context
from .decorators import DecoratorBase, rep
import patterns
from logging import getLogger

logger = getLogger(__name__)


class ServerBase(object):

    def __init__(self, channel, methods=None, name=None, context=None,
            pool_size=None, heartbeat=5):
        self._multiplexer = ChannelMultiplexer(channel)

        if methods is None:
            methods = self

        self._context = context or Context.get_instance()
        self._name = name or self._extract_name()
        self._task_pool = gevent.pool.Pool(size=pool_size)
        self._acceptor_task = None
        self._methods = self._filter_methods(ServerBase, self, methods)

        self._inject_builtins()
        self._heartbeat_freq = heartbeat

        for (k, functor) in self._methods.items():
            if not isinstance(functor, DecoratorBase):
                self._methods[k] = rep(functor)

    @staticmethod
    def _filter_methods(cls, self, methods):
        if hasattr(methods, '__getitem__'):
            return methods
        server_methods = set(getattr(self, k) for k in dir(cls) if not
                             k.startswith('_'))
        return dict((k, getattr(methods, k))
                    for k in dir(methods)
                    if (callable(getattr(methods, k))
                        and not k.startswith('_')
                        and getattr(methods, k) not in server_methods
                        ))

    @staticmethod
    def _extract_name(methods):
        return getattr(type(methods), '__name__', None) or repr(methods)

    def close(self):
        self.stop()
        self._multiplexer.close()

    def _format_args_spec(self, args_spec, r=None):
        if args_spec:
            r = [dict(name=name) for name in args_spec[0]]
            default_values = args_spec[3]
            if default_values is not None:
                for arg, def_val in zip(reversed(r), reversed(default_values)):
                    arg['default'] = def_val
        return r

    def _zerorpc_inspect(self):
        methods = dict((m, f) for m, f in self._methods.items()
                    if not m.startswith('_'))
        detailled_methods = dict((m,
            dict(args=self._format_args_spec(f._zerorpc_args()),
                doc=f._zerorpc_doc())) for (m, f) in methods.items())
        return {'name': self._name,
                'methods': detailled_methods}

    def _inject_builtins(self):
        self._methods['_zerorpc_list'] = lambda: [m for m in self._methods
                if not m.startswith('_')]
        self._methods['_zerorpc_name'] = lambda: self._name
        self._methods['_zerorpc_ping'] = lambda: ['pong', self._name]
        self._methods['_zerorpc_help'] = lambda m: \
            self._methods[m]._zerorpc_doc()
        self._methods['_zerorpc_args'] = \
            lambda m: self._methods[m]._zerorpc_args()
        self._methods['_zerorpc_inspect'] = self._zerorpc_inspect

    def __call__(self, method, *args):
        if method not in self._methods:
            raise NameError(method)
        return self._methods[method](*args)

    def _print_traceback(self, protocol_v1, exc_infos):
        logger.exception('')

        exc_type, exc_value, exc_traceback = exc_infos
        if protocol_v1:
            return (repr(exc_value),)
        human_traceback = traceback.format_exc()
        name = exc_type.__name__
        human_msg = str(exc_value)
        return (name, human_msg, human_traceback)

    def _async_task(self, initial_event):
        protocol_v1 = initial_event.header.get('v', 1) < 2
        channel = self._multiplexer.channel(initial_event)
        hbchan = HeartBeatOnChannel(channel, freq=self._heartbeat_freq,
                passive=protocol_v1)
        bufchan = BufferedChannel(hbchan)
        exc_infos = None
        event = bufchan.recv()
        try:
            self._context.hook_load_task_context(event.header)
            functor = self._methods.get(event.name, None)
            if functor is None:
                raise NameError(event.name)
            functor.pattern.process_call(self._context, bufchan, event, functor)
        except LostRemote:
            exc_infos = list(sys.exc_info())
            self._print_traceback(protocol_v1, exc_infos)
        except Exception:
            exc_infos = list(sys.exc_info())
            human_exc_infos = self._print_traceback(protocol_v1, exc_infos)
            reply_event = bufchan.create_event('ERR', human_exc_infos,
                    self._context.hook_get_task_context())
            self._context.hook_server_inspect_exception(event, reply_event, exc_infos)
            bufchan.emit_event(reply_event)
        finally:
            del exc_infos
            bufchan.close()

    def _acceptor(self):
        while True:
            initial_event = self._multiplexer.recv()
            self._task_pool.spawn(self._async_task, initial_event)

    def run(self):
        self._acceptor_task = gevent.spawn(self._acceptor)
        try:
            self._acceptor_task.get()
        finally:
            self.stop()
            self._task_pool.join(raise_error=True)

    def stop(self):
        if self._acceptor_task is not None:
            self._acceptor_task.kill()
            self._acceptor_task = None


class ClientBase(object):

    def __init__(self, channel, context=None, timeout=30, heartbeat=5,
            passive_heartbeat=False):
        self._multiplexer = ChannelMultiplexer(channel,
                ignore_broadcast=True)
        self._context = context or Context.get_instance()
        self._timeout = timeout
        self._heartbeat_freq = heartbeat
        self._passive_heartbeat = passive_heartbeat

    def close(self):
        self._multiplexer.close()

    def _handle_remote_error(self, event):
        exception = self._context.hook_client_handle_remote_error(event)
        if not exception:
            if event.header.get('v', 1) >= 2:
                (name, msg, traceback) = event.args
                exception = RemoteError(name, msg, traceback)
            else:
                (msg,) = event.args
                exception = RemoteError('RemoteError', msg, None)

        return exception

    def _select_pattern(self, event):
        for pattern in patterns.patterns_list:
            if pattern.accept_answer(event):
                return pattern
        msg = 'Unable to find a pattern for: {0}'.format(event)
        raise RuntimeError(msg)

    def _process_response(self, request_event, bufchan, timeout):
        try:
            reply_event = bufchan.recv(timeout)
            pattern = self._select_pattern(reply_event)
            return pattern.process_answer(self._context, bufchan, request_event,
                    reply_event, self._handle_remote_error)
        except TimeoutExpired:
            bufchan.close()
            ex = TimeoutExpired(timeout,
                    'calling remote method {0}'.format(request_event.name))
            self._context.hook_client_after_request(request_event, None, ex)
            raise ex
        except:
            bufchan.close()
            raise

    def __call__(self, method, *args, **kargs):
        timeout = kargs.get('timeout', self._timeout)
        channel = self._multiplexer.channel()
        hbchan = HeartBeatOnChannel(channel, freq=self._heartbeat_freq,
                passive=self._passive_heartbeat)
        bufchan = BufferedChannel(hbchan, inqueue_size=kargs.get('slots', 100))

        xheader = self._context.hook_get_task_context()
        request_event = bufchan.create_event(method, args, xheader)
        self._context.hook_client_before_request(request_event)
        bufchan.emit_event(request_event)

        try:
            if kargs.get('async', False) is False:
                return self._process_response(request_event, bufchan, timeout)

            async_result = gevent.event.AsyncResult()
            gevent.spawn(self._process_response, request_event, bufchan,
                    timeout).link(async_result)
            return async_result
        except:
            # XXX: This is going to be closed twice if async is false and
            # _process_response raises an exception. I wonder if the above
            # async branch can raise an exception too, if no we can just remove
            # this code.
            bufchan.close()
            raise

    def __getattr__(self, method):
        return lambda *args, **kargs: self(method, *args, **kargs)


class Server(SocketBase, ServerBase):

    def __init__(self, methods=None, name=None, context=None, pool_size=None,
            heartbeat=5):
        SocketBase.__init__(self, zmq.ROUTER, context)
        if methods is None:
            methods = self

        name = name or ServerBase._extract_name(methods)
        methods = ServerBase._filter_methods(Server, self, methods)
        ServerBase.__init__(self, self._events, methods, name, context,
                pool_size, heartbeat)

    def close(self):
        ServerBase.close(self)
        SocketBase.close(self)


class Client(SocketBase, ClientBase):

    def __init__(self, connect_to=None, context=None, timeout=30, heartbeat=5,
            passive_heartbeat=False):
        SocketBase.__init__(self, zmq.DEALER, context=context)
        ClientBase.__init__(self, self._events, context, timeout, heartbeat,
                passive_heartbeat)
        if connect_to:
            self.connect(connect_to)

    def close(self):
        ClientBase.close(self)
        SocketBase.close(self)


class Pusher(SocketBase):

    def __init__(self, context=None, zmq_socket=zmq.PUSH):
        super(Pusher, self).__init__(zmq_socket, context=context)

    def __call__(self, method, *args):
        self._events.emit(method, args,
                self._context.hook_get_task_context())

    def __getattr__(self, method):
        return lambda *args: self(method, *args)


class Puller(SocketBase):

    def __init__(self, methods=None, context=None, zmq_socket=zmq.PULL):
        super(Puller, self).__init__(zmq_socket, context=context)

        if methods is None:
            methods = self

        self._methods = ServerBase._filter_methods(Puller, self, methods)
        self._receiver_task = None

    def close(self):
        self.stop()
        super(Puller, self).close()

    def __call__(self, method, *args):
        if method not in self._methods:
            raise NameError(method)
        return self._methods[method](*args)

    def _receiver(self):
        while True:
            event = self._events.recv()
            try:
                if event.name not in self._methods:
                    raise NameError(event.name)
                self._context.hook_load_task_context(event.header)
                self._context.hook_server_before_exec(event)
                self._methods[event.name](*event.args)
                # In Push/Pull their is no reply to send, hence None for the
                # reply_event argument
                self._context.hook_server_after_exec(event, None)
            except Exception:
                exc_infos = sys.exc_info()
                try:
                    logger.exception('')
                    self._context.hook_server_inspect_exception(event, None, exc_infos)
                finally:
                    del exc_infos

    def run(self):
        self._receiver_task = gevent.spawn(self._receiver)
        try:
            self._receiver_task.get()
        finally:
            self._receiver_task = None

    def stop(self):
        if self._receiver_task is not None:
            self._receiver_task.kill(block=False)


class Publisher(Pusher):

    def __init__(self, context=None):
        super(Publisher, self).__init__(context=context, zmq_socket=zmq.PUB)


class Subscriber(Puller):

    def __init__(self, methods=None, context=None):
        super(Subscriber, self).__init__(methods=methods, context=context,
                zmq_socket=zmq.SUB)
        self._events.setsockopt(zmq.SUBSCRIBE, '')


def fork_task_context(functor, context=None):
    '''Wrap a functor to transfer context.

        Usage example:
            gevent.spawn(zerorpc.fork_task_context(myfunction), args...)

        The goal is to permit context "inheritance" from a task to another.
        Consider the following example:

            zerorpc.Server receive a new event
              - task1 is created to handle this event this task will be linked
                to the initial event context. zerorpc.Server does that for you.
              - task1 make use of some zerorpc.Client instances, the initial
                event context is transfered on every call.

              - task1 spawn a new task2.
              - task2 make use of some zerorpc.Client instances, it's a fresh
                context. Thus there is no link to the initial context that
                spawned task1.

              - task1 spawn a new fork_task_context(task3).
              - task3 make use of some zerorpc.Client instances, the initial
                event context is transfered on every call.

        A real use case is a distributed tracer. Each time a new event is
        created, a trace_id is injected in it or copied from the current task
        context. This permit passing the trace_id from a zerorpc.Server to
        another via zerorpc.Client.

        The simple rule to know if a task need to be wrapped is:
            - if the new task will make any zerorpc call, it should be wrapped.
    '''
    context = context or Context.get_instance()
    header = context.hook_get_task_context()

    def wrapped(*args, **kargs):
        context.hook_load_task_context(header)
        return functor(*args, **kargs)
    return wrapped

########NEW FILE########
__FILENAME__ = decorators
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import inspect

from .patterns import *  # noqa


class DecoratorBase(object):
    pattern = None

    def __init__(self, functor):
        self._functor = functor
        self.__doc__ = functor.__doc__
        self.__name__ = functor.__name__

    def __get__(self, instance, type_instance=None):
        if instance is None:
            return self
        return self.__class__(self._functor.__get__(instance, type_instance))

    def __call__(self, *args, **kargs):
        return self._functor(*args, **kargs)

    def _zerorpc_doc(self):
        if self.__doc__ is None:
            return None
        return inspect.cleandoc(self.__doc__)

    def _zerorpc_args(self):
        try:
            args_spec = self._functor._zerorpc_args()
        except AttributeError:
            try:
                args_spec = inspect.getargspec(self._functor)
            except TypeError:
                try:
                    args_spec = inspect.getargspec(self._functor.__call__)
                except (AttributeError, TypeError):
                    args_spec = None
        return args_spec


class rep(DecoratorBase):
    pattern = ReqRep()


class stream(DecoratorBase):
    pattern = ReqStream()

########NEW FILE########
__FILENAME__ = events
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import msgpack
import gevent.pool
import gevent.queue
import gevent.event
import gevent.local
import gevent.lock


import gevent_zmq as zmq
from .context import Context


class Sender(object):

    def __init__(self, socket):
        self._socket = socket
        self._send_queue = gevent.queue.Channel()
        self._send_task = gevent.spawn(self._sender)

    def __del__(self):
        self.close()

    def close(self):
        if self._send_task:
            self._send_task.kill()

    def _sender(self):
        running = True
        for parts in self._send_queue:
            for i in xrange(len(parts) - 1):
                try:
                    self._socket.send(parts[i], flags=zmq.SNDMORE)
                except gevent.GreenletExit:
                    if i == 0:
                        return
                    running = False
                    self._socket.send(parts[i], flags=zmq.SNDMORE)
            self._socket.send(parts[-1])
            if not running:
                return

    def __call__(self, parts):
        self._send_queue.put(parts)


class Receiver(object):

    def __init__(self, socket):
        self._socket = socket
        self._recv_queue = gevent.queue.Channel()
        self._recv_task = gevent.spawn(self._recver)

    def __del__(self):
        self.close()

    def close(self):
        if self._recv_task:
            self._recv_task.kill()

    def _recver(self):
        running = True
        while True:
            parts = []
            while True:
                try:
                    part = self._socket.recv()
                except gevent.GreenletExit:
                    running = False
                    if len(parts) == 0:
                        return
                    part = self._socket.recv()
                parts.append(part)
                if not self._socket.getsockopt(zmq.RCVMORE):
                    break
            if not running:
                break
            self._recv_queue.put(parts)

    def __call__(self):
        return self._recv_queue.get()


class Event(object):

    __slots__ = ['_name', '_args', '_header']

    def __init__(self, name, args, context, header=None):
        self._name = name
        self._args = args
        if header is None:
            self._header = {
                'message_id': context.new_msgid(),
                'v': 3
            }
        else:
            self._header = header

    @property
    def header(self):
        return self._header

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, v):
        self._name = v

    @property
    def args(self):
        return self._args

    def pack(self):
        return msgpack.Packer().pack((self._header, self._name, self._args))

    @staticmethod
    def unpack(blob):
        unpacker = msgpack.Unpacker()
        unpacker.feed(blob)
        unpacked_msg = unpacker.unpack()

        try:
            (header, name, args) = unpacked_msg
        except Exception as e:
            raise Exception('invalid msg format "{0}": {1}'.format(
                unpacked_msg, e))

        # Backward compatibility
        if not isinstance(header, dict):
            header = {}

        return Event(name, args, None, header)

    def __str__(self, ignore_args=False):
        if ignore_args:
            args = '[...]'
        else:
            args = self._args
            try:
                args = '<<{0}>>'.format(str(self.unpack(self._args)))
            except:
                pass
        return '{0} {1} {2}'.format(self._name, self._header,
                args)


class Events(object):
    def __init__(self, zmq_socket_type, context=None):
        self._zmq_socket_type = zmq_socket_type
        self._context = context or Context.get_instance()
        self._socket = zmq.Socket(self._context, zmq_socket_type)
        self._send = self._socket.send_multipart
        self._recv = self._socket.recv_multipart
        if zmq_socket_type in (zmq.PUSH, zmq.PUB, zmq.DEALER, zmq.ROUTER):
            self._send = Sender(self._socket)
        if zmq_socket_type in (zmq.PULL, zmq.SUB, zmq.DEALER, zmq.ROUTER):
            self._recv = Receiver(self._socket)

    @property
    def recv_is_available(self):
        return self._zmq_socket_type in (zmq.PULL, zmq.SUB, zmq.DEALER, zmq.ROUTER)

    def __del__(self):
        try:
            if not self._socket.closed:
                self.close()
        except AttributeError:
            pass

    def close(self):
        try:
            self._send.close()
        except AttributeError:
            pass
        try:
            self._recv.close()
        except AttributeError:
            pass
        self._socket.close()

    def _resolve_endpoint(self, endpoint, resolve=True):
        if resolve:
            endpoint = self._context.hook_resolve_endpoint(endpoint)
        if isinstance(endpoint, (tuple, list)):
            r = []
            for sub_endpoint in endpoint:
                r.extend(self._resolve_endpoint(sub_endpoint, resolve))
            return r
        return [endpoint]

    def connect(self, endpoint, resolve=True):
        r = []
        for endpoint_ in self._resolve_endpoint(endpoint, resolve):
            r.append(self._socket.connect(endpoint_))
        return r

    def bind(self, endpoint, resolve=True):
        r = []
        for endpoint_ in self._resolve_endpoint(endpoint, resolve):
            r.append(self._socket.bind(endpoint_))
        return r

    def create_event(self, name, args, xheader=None):
        xheader = {} if xheader is None else xheader
        event = Event(name, args, context=self._context)
        for k, v in xheader.items():
            if k == 'zmqid':
                continue
            event.header[k] = v
        return event

    def emit_event(self, event, identity=None):
        if identity is not None:
            parts = list(identity)
            parts.extend(['', event.pack()])
        elif self._zmq_socket_type in (zmq.DEALER, zmq.ROUTER):
            parts = ('', event.pack())
        else:
            parts = (event.pack(),)
        self._send(parts)

    def emit(self, name, args, xheader=None):
        xheader = {} if xheader is None else xheader
        event = self.create_event(name, args, xheader)
        identity = xheader.get('zmqid', None)
        return self.emit_event(event, identity)

    def recv(self):
        parts = self._recv()
        if len(parts) == 1:
            identity = None
            blob = parts[0]
        else:
            identity = parts[0:-2]
            blob = parts[-1]
        event = Event.unpack(blob)
        if identity is not None:
            event.header['zmqid'] = identity
        return event

    def setsockopt(self, *args):
        return self._socket.setsockopt(*args)

    @property
    def context(self):
        return self._context


class WrappedEvents(object):

    def __init__(self, channel):
        self._channel = channel

    def close(self):
        pass

    @property
    def recv_is_available(self):
        return self._channel.recv_is_available

    def create_event(self, name, args, xheader=None):
        xheader = {} if xheader is None else xheader
        event = Event(name, args, self._channel.context)
        event.header.update(xheader)
        return event

    def emit_event(self, event, identity=None):
        event_payload = (event.header, event.name, event.args)
        wrapper_event = self._channel.create_event('w', event_payload)
        self._channel.emit_event(wrapper_event)

    def emit(self, name, args, xheader=None):
        wrapper_event = self.create_event(name, args, xheader)
        self.emit_event(wrapper_event)

    def recv(self, timeout=None):
        wrapper_event = self._channel.recv()
        (header, name, args) = wrapper_event.args
        return Event(name, args, None, header)

    @property
    def context(self):
        return self._channel.context

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


class LostRemote(Exception):
    pass


class TimeoutExpired(Exception):

    def __init__(self, timeout_s, when=None):
        msg = 'timeout after {0}s'.format(timeout_s)
        if when:
            msg = '{0}, when {1}'.format(msg, when)
        super(TimeoutExpired, self).__init__(msg)


class RemoteError(Exception):

    def __init__(self, name, human_msg, human_traceback):
        self.name = name
        self.msg = human_msg
        self.traceback = human_traceback

    def __str__(self):
        if self.traceback is not None:
            return self.traceback
        return '{0}: {1}'.format(self.name, self.msg)

########NEW FILE########
__FILENAME__ = gevent_zmq
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Based on https://github.com/traviscline/gevent-zeromq/

# We want to act like zmq
from zmq import *  # noqa

# A way to access original zmq
import zmq as _zmq

import gevent.event
import gevent.core
import errno
from logging import getLogger

logger = getLogger(__name__)


class Context(_zmq.Context):

    def socket(self, socket_type):
        if self.closed:
            raise _zmq.ZMQError(_zmq.ENOTSUP)
        return Socket(self, socket_type)


class Socket(_zmq.Socket):

    def __init__(self, context, socket_type):
        super(Socket, self).__init__(context, socket_type)
        on_state_changed_fd = self.getsockopt(_zmq.FD)
        # NOTE: pyzmq 13.0.0 messed up with setattr (they turned it into a
        # non-op) and you can't assign attributes normally anymore, hence the
        # tricks with self.__dict__ here
        self.__dict__["_readable"] = gevent.event.Event()
        self.__dict__["_writable"] = gevent.event.Event()
        try:
            # gevent>=1.0
            self.__dict__["_state_event"] = gevent.hub.get_hub().loop.io(
                on_state_changed_fd, gevent.core.READ)
            self._state_event.start(self._on_state_changed)
        except AttributeError:
            # gevent<1.0
            self.__dict__["_state_event"] = \
                gevent.core.read_event(on_state_changed_fd,
                                       self._on_state_changed, persist=True)

    def _on_state_changed(self, event=None, _evtype=None):
        if self.closed:
            self._writable.set()
            self._readable.set()
            return

        while True:
            try:
                events = self.getsockopt(_zmq.EVENTS)
                break
            except ZMQError as e:
                if e.errno not in (_zmq.EAGAIN, errno.EINTR):
                    raise

        if events & _zmq.POLLOUT:
            self._writable.set()
        if events & _zmq.POLLIN:
            self._readable.set()

    def close(self):
        if not self.closed and getattr(self, '_state_event', None):
            try:
                # gevent>=1.0
                self._state_event.stop()
            except AttributeError:
                # gevent<1.0
                self._state_event.cancel()
        super(Socket, self).close()

    def connect(self, *args, **kwargs):
        while True:
            try:
                return super(Socket, self).connect(*args, **kwargs)
            except _zmq.ZMQError, e:
                if e.errno not in (_zmq.EAGAIN, errno.EINTR):
                    raise

    def send(self, data, flags=0, copy=True, track=False):
        if flags & _zmq.NOBLOCK:
            return super(Socket, self).send(data, flags, copy, track)
        flags |= _zmq.NOBLOCK
        while True:
            try:
                msg = super(Socket, self).send(data, flags, copy, track)
                # The following call, force polling the state of the zmq socket
                # (POLLIN and/or POLLOUT). It seems that a POLLIN event is often
                # missed when the socket is used to send at the same time,
                # forcing to poll at this exact moment seems to reduce the
                # latencies when a POLLIN event is missed. The drawback is a
                # reduced throughput (roughly 8.3%) in exchange of a normal
                # concurrency. In other hand, without the following line, you
                # loose 90% of the performances as soon as there is simultaneous
                # send and recv on the socket.
                self._on_state_changed()
                return msg
            except _zmq.ZMQError, e:
                if e.errno not in (_zmq.EAGAIN, errno.EINTR):
                    raise
            self._writable.clear()
            # The following sleep(0) force gevent to switch out to another
            # coroutine and seems to refresh the notion of time that gevent may
            # have. This definitively eliminate the gevent bug that can trigger
            # a timeout too soon under heavy load. In theory it will incur more
            # CPU usage, but in practice it balance even with the extra CPU used
            # when the timeout triggers too soon in the following loop. So for
            # the same CPU load, you get a better throughput (roughly 18.75%).
            gevent.sleep(0)
            while not self._writable.wait(timeout=1):
                try:
                    if self.getsockopt(_zmq.EVENTS) & _zmq.POLLOUT:
                        logger.error("/!\\ gevent_zeromq BUG /!\\ "
                                     "catching up after missing event (SEND) /!\\")
                        break
                except ZMQError as e:
                    if e.errno not in (_zmq.EAGAIN, errno.EINTR):
                        raise

    def recv(self, flags=0, copy=True, track=False):
        if flags & _zmq.NOBLOCK:
            return super(Socket, self).recv(flags, copy, track)
        flags |= _zmq.NOBLOCK
        while True:
            try:
                msg = super(Socket, self).recv(flags, copy, track)
                # The following call, force polling the state of the zmq socket
                # (POLLIN and/or POLLOUT). It seems that a POLLOUT event is
                # often missed when the socket is used to receive at the same
                # time, forcing to poll at this exact moment seems to reduce the
                # latencies when a POLLOUT event is missed. The drawback is a
                # reduced throughput (roughly 8.3%) in exchange of a normal
                # concurrency. In other hand, without the following line, you
                # loose 90% of the performances as soon as there is simultaneous
                # send and recv on the socket.
                self._on_state_changed()
                return msg
            except _zmq.ZMQError, e:
                if e.errno not in (_zmq.EAGAIN, errno.EINTR):
                    raise
            self._readable.clear()
            # The following sleep(0) force gevent to switch out to another
            # coroutine and seems to refresh the notion of time that gevent may
            # have. This definitively eliminate the gevent bug that can trigger
            # a timeout too soon under heavy load. In theory it will incur more
            # CPU usage, but in practice it balance even with the extra CPU used
            # when the timeout triggers too soon in the following loop. So for
            # the same CPU load, you get a better throughput (roughly 18.75%).
            gevent.sleep(0)
            while not self._readable.wait(timeout=1):
                try:
                    if self.getsockopt(_zmq.EVENTS) & _zmq.POLLIN:
                        logger.error("/!\\ gevent_zeromq BUG /!\\ "
                                     "catching up after missing event (RECV) /!\\")
                        break
                except ZMQError as e:
                    if e.errno not in (_zmq.EAGAIN, errno.EINTR):
                        raise

########NEW FILE########
__FILENAME__ = heartbeat
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import time
import gevent.pool
import gevent.queue
import gevent.event
import gevent.local
import gevent.lock

from .exceptions import *  # noqa


class HeartBeatOnChannel(object):

    def __init__(self, channel, freq=5, passive=False):
        self._channel = channel
        self._heartbeat_freq = freq
        self._input_queue = gevent.queue.Channel()
        self._remote_last_hb = None
        self._lost_remote = False
        self._recv_task = gevent.spawn(self._recver)
        self._heartbeat_task = None
        self._parent_coroutine = gevent.getcurrent()
        self._compat_v2 = None
        if not passive:
            self._start_heartbeat()

    @property
    def recv_is_available(self):
        return self._channel.recv_is_available

    def __del__(self):
        self.close()

    def close(self):
        if self._heartbeat_task is not None:
            self._heartbeat_task.kill()
            self._heartbeat_task = None
        if self._recv_task is not None:
            self._recv_task.kill()
            self._recv_task = None
        if self._channel is not None:
            self._channel.close()
            self._channel = None

    def _heartbeat(self):
        while True:
            gevent.sleep(self._heartbeat_freq)
            if self._remote_last_hb is None:
                self._remote_last_hb = time.time()
            if time.time() > self._remote_last_hb + self._heartbeat_freq * 2:
                self._lost_remote = True
                gevent.kill(self._parent_coroutine,
                        self._lost_remote_exception())
                break
            self._channel.emit('_zpc_hb', (0,))  # 0 -> compat with protocol v2

    def _start_heartbeat(self):
        if self._heartbeat_task is None and self._heartbeat_freq is not None:
            self._heartbeat_task = gevent.spawn(self._heartbeat)

    def _recver(self):
        while True:
            event = self._channel.recv()
            if self._compat_v2 is None:
                self._compat_v2 = event.header.get('v', 0) < 3
            if event.name == '_zpc_hb':
                self._remote_last_hb = time.time()
                self._start_heartbeat()
                if self._compat_v2:
                    event.name = '_zpc_more'
                    self._input_queue.put(event)
            else:
                self._input_queue.put(event)

    def _lost_remote_exception(self):
        return LostRemote('Lost remote after {0}s heartbeat'.format(
            self._heartbeat_freq * 2))

    def create_event(self, name, args, xheader=None):
        if self._compat_v2 and name == '_zpc_more':
            name = '_zpc_hb'
        return self._channel.create_event(name, args, xheader)

    def emit_event(self, event):
        if self._lost_remote:
            raise self._lost_remote_exception()
        self._channel.emit_event(event)

    def emit(self, name, args, xheader=None):
        event = self.create_event(name, args, xheader)
        self.emit_event(event)

    def recv(self, timeout=None):
        if self._lost_remote:
            raise self._lost_remote_exception()

        try:
            event = self._input_queue.get(timeout=timeout)
        except gevent.queue.Empty:
            raise TimeoutExpired(timeout)

        return event

    @property
    def channel(self):
        return self._channel

    @property
    def context(self):
        return self._channel.context

########NEW FILE########
__FILENAME__ = patterns
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


class ReqRep:

    def process_call(self, context, bufchan, req_event, functor):
        context.hook_server_before_exec(req_event)
        result = functor(*req_event.args)
        rep_event = bufchan.create_event('OK', (result,),
                context.hook_get_task_context())
        context.hook_server_after_exec(req_event, rep_event)
        bufchan.emit_event(rep_event)

    def accept_answer(self, event):
        return True

    def process_answer(self, context, bufchan, req_event, rep_event,
            handle_remote_error):
        if rep_event.name == 'ERR':
            exception = handle_remote_error(rep_event)
            context.hook_client_after_request(req_event, rep_event, exception)
            raise exception
        context.hook_client_after_request(req_event, rep_event)
        bufchan.close()
        result = rep_event.args[0]
        return result


class ReqStream:

    def process_call(self, context, bufchan, req_event, functor):
        context.hook_server_before_exec(req_event)
        xheader = context.hook_get_task_context()
        for result in iter(functor(*req_event.args)):
            bufchan.emit('STREAM', result, xheader)
        done_event = bufchan.create_event('STREAM_DONE', None, xheader)
        # NOTE: "We" made the choice to call the hook once the stream is done,
        # the other choice was to call it at each iteration. I don't think that
        # one choice is better than the other, so I'm fine with changing this
        # or adding the server_after_iteration and client_after_iteration hooks.
        context.hook_server_after_exec(req_event, done_event)
        bufchan.emit_event(done_event)

    def accept_answer(self, event):
        return event.name in ('STREAM', 'STREAM_DONE')

    def process_answer(self, context, bufchan, req_event, rep_event,
            handle_remote_error):

        def is_stream_done(rep_event):
            return rep_event.name == 'STREAM_DONE'
        bufchan.on_close_if = is_stream_done

        def iterator(req_event, rep_event):
            while rep_event.name == 'STREAM':
                # Like in process_call, we made the choice to call the
                # after_exec hook only when the stream is done.
                yield rep_event.args
                rep_event = bufchan.recv()
            if rep_event.name == 'ERR':
                exception = handle_remote_error(rep_event)
                context.hook_client_after_request(req_event, rep_event, exception)
                raise exception
            context.hook_client_after_request(req_event, rep_event)
            bufchan.close()

        return iterator(req_event, rep_event)


patterns_list = [ReqStream(), ReqRep()]

########NEW FILE########
__FILENAME__ = socket
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from .context import Context
from .events import Events


class SocketBase(object):

    def __init__(self, zmq_socket_type, context=None):
        self._context = context or Context.get_instance()
        self._events = Events(zmq_socket_type, context)

    def close(self):
        self._events.close()

    def connect(self, endpoint, resolve=True):
        return self._events.connect(endpoint, resolve)

    def bind(self, endpoint, resolve=True):
        return self._events.bind(endpoint, resolve)

########NEW FILE########
__FILENAME__ = version
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

__title__ = 'zerorpc'
__version__ = '0.4.4'
__author__ = 'dotCloud, Inc.'
__license__ = 'MIT'
__copyright__ = 'Copyright 2012 dotCloud, Inc.'

########NEW FILE########
