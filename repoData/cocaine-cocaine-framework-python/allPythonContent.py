__FILENAME__ = message
#
#    Copyright (c) 2011-2013 Anton Tyurin <noxiouz@yandex.ru>
#    Copyright (c) 2011-2013 Other contributors as noted in the AUTHORS file.
#
#    This file is part of Cocaine.
#
#    Cocaine is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Cocaine is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import msgpack


class RPC:
    PROTOCOL_LIST = (
        HANDSHAKE,
        HEARTBEAT,
        TERMINATE,
        INVOKE,
        CHUNK,
        ERROR,
        CHOKE) = range(7)


PROTOCOL = {
    RPC.HANDSHAKE: {
        'id': RPC.HANDSHAKE,
        'alias': 'Handshake',
        'tuple_type': ('uuid',)
    },
    RPC.HEARTBEAT: {
        'id': RPC.HEARTBEAT,
        'alias': 'Heartbeat',
        'tuple_type': ()
    },
    RPC.TERMINATE: {
        'id': RPC.TERMINATE,
        'alias': 'Terminate',
        'tuple_type': ('errno', 'reason')
    },
    RPC.INVOKE: {
        'id': RPC.INVOKE,
        'alias': 'Invoke',
        'tuple_type': ('event',)
    },
    RPC.CHUNK: {
        'id': RPC.CHUNK,
        'alias': 'Chunk',
        'tuple_type': ('data',)
    },
    RPC.ERROR: {
        'id': RPC.ERROR,
        'alias': 'Error',
        'tuple_type': ('errno', 'reason')
    },
    RPC.CHOKE: {
        'id': RPC.CHOKE,
        'alias': 'Choke',
        'tuple_type': ()
    }
}


def _make_packable(m_id, m_session, args):
    def wrapper():
        return msgpack.dumps([m_id, m_session, args])
    return wrapper


class BaseMessage(object):
    def __init__(self, protocol, id_, session, *args):
        prototype = protocol[id_]

        self.id = prototype['id']
        self.session = session
        self.args = args

        self.__class__.__name__ = prototype['alias']
        for attr, value in zip(prototype['tuple_type'], args):
            setattr(self, attr, value)

        setattr(self, 'pack', _make_packable(self.id, session, args))

    def __str__(self):
        return '{0}({1}, {2}, {3})'.format(self.__class__.__name__, self.id, self.session, self.args)


class Message(BaseMessage):
    def __init__(self, id_, session, *args):
        super(Message, self).__init__(PROTOCOL, id_, session, *args)

    @staticmethod
    def initialize(data):
        id_, session, args = data
        return Message(RPC.PROTOCOL_LIST[id_], session, *args)

########NEW FILE########
__FILENAME__ = protocol
#
#    Copyright (c) 2014+ Anton Tyurin <noxiouz@yandex.ru>
#    Copyright (c) 2014+ Evgeny Safronov <division494@gmail.com>
#    Copyright (c) 2011-2014 Other contributors as noted in the AUTHORS file.
#
#    This file is part of Cocaine.
#
#    Cocaine is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Cocaine is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#


import asyncio

import msgpack


class CocaineProtocol(asyncio.Protocol):
    def __init__(self, on_chunk, on_failure):
        self.buffer = msgpack.Unpacker()
        self.transport = None
        self.on_chunk = on_chunk
        self.on_failure = on_failure

    def connected(self):
        return self.transport is not None

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        # Replace with MixIn
        self.buffer.feed(data)
        for chunk in self.buffer:
            self.on_chunk(chunk)

    def connection_lost(self, exc):
        self.transport = None
        self.on_failure(exc)

    def write(self, data):
        self.transport.write(data)

    @staticmethod
    def factory(on_chunk, on_failure):
        return lambda: CocaineProtocol(on_chunk, on_failure)

########NEW FILE########
__FILENAME__ = rpc
#
#    Copyright (c) 2011-2013 Anton Tyurin <noxiouz@yandex.ru>
#    Copyright (c) 2011-2013 Other contributors as noted in the AUTHORS file.
#
#    This file is part of Cocaine.
#
#    Cocaine is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Cocaine is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#


class API:
    Locator = {
        'resolve': 0,
        'update': 1,
        'stats': 2,
    }

########NEW FILE########
__FILENAME__ = utils
#
#    Copyright (c) 2014+ Anton Tyurin <noxiouz@yandex.ru>
#    Copyright (c) 2014+ Evgeny Safronov <division494@gmail.com>
#    Copyright (c) 2011-2014 Other contributors as noted in the AUTHORS file.
#
#    This file is part of Cocaine.
#
#    Cocaine is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Cocaine is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import asyncio


class Timer(object):
    def __init__(self, callback, period, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        if period < 0:
            raise ValueError("Period must be a positive value")

        self.period = period
        self.callback = callback

        self._handler = None

    def start(self):
        if self._handler is None:
            self.schedule_next()
        else:
            raise Exception("Timer has already started")

    def stop(self):
        if self._handler is not None:
            self._handler.cancel()
            self._handler = None

    def schedule_next(self):
        self._handler = self.loop.call_later(self.period,
                                             self._run)

    def _run(self):
        try:
            self.callback()
        except Exception as err:
            context = {"message": str(err),
                       "exception": err,
                       "handle": self._handler}
            self.loop.call_exception_handler(context)
        self.schedule_next()

########NEW FILE########
__FILENAME__ = base
#
#    Copyright (c) 2014+ Anton Tyurin <noxiouz@yandex.ru>
#    Copyright (c) 2014+ Evgeny Safronov <division494@gmail.com>
#    Copyright (c) 2011-2014 Other contributors as noted in the AUTHORS file.
#
#    This file is part of Cocaine.
#
#    Cocaine is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Cocaine is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
from __future__ import with_statement

import asyncio
import itertools
import logging

import msgpack

from ..concurrent import Stream
from ..common import CocaineErrno
from ..asio.protocol import CocaineProtocol
from ..asio.message import RPC, Message
from ..asio.rpc import API


log = logging.getLogger('cocaine.service')


class BaseService(object):
    def __init__(self, name, host='localhost', port=10053, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self._state_lock = asyncio.Lock()
        self.host = host
        self.port = port
        self.name = name
        # Protocol
        self.pr = None
        # Should I add connection epoch?
        # Epoch is useful when on_failure is called
        self.sessions = {}
        self.counter = itertools.count()

        self.api = {}
        self._extra = {'service': self.name, 'id': id(self)}

    def connected(self):
        return self.pr and self.pr.connected()

    @asyncio.coroutine
    def connect(self):
        log.debug("checking if service connected", extra=self._extra)
        # Double checked locking
        if self.connected():
            log.debug("already connected", extra=self._extra)
            return

        with (yield self._state_lock):
            if self.connected():
                log.debug("already connected", extra=self._extra)
                return

            log.debug("connecting ...", extra=self._extra)
            proto_factory = CocaineProtocol.factory(self.on_message, self.on_failure)
            _, self.pr = yield self.loop.create_connection(proto_factory, self.host, self.port)
            log.debug("successfully connected: %s", [self.host, self.port], extra=self._extra)

    def on_message(self, unpacked_data):
        msg = Message.initialize(unpacked_data)
        log.debug("received message: %s", msg, extra=self._extra)

        stream = self.sessions.get(msg.session)
        if stream is None:
            log.error("unknown session id %d", msg.session, extra=self._extra)
            return

        # TODO: Replace with constants and message.initializer
        if msg.id == RPC.CHUNK:
            stream.push(msgpack.unpackb(msg.data))
        elif msg.id == RPC.CHOKE:
            stream.done()
        elif msg.id == RPC.ERROR:
            stream.error(msg.errno, msg.reason)

    def on_failure(self, exc):
        log.warn("service is disconnected: %s", exc, extra=self._extra)

        for stream in self.sessions.itervalues():
            stream.error(CocaineErrno.ESRVDISCON, "service %s is disconnected" % self.name)

    @asyncio.coroutine
    def _invoke(self, method, *args):
        log.debug("invoking '%s' method with args: %s", method, args, extra=self._extra)
        yield self.connect()
        method_id = self.api.get(method)

        if method_id is None:
            raise Exception("Method '%s' is not supported" % method)

        counter = self.counter.next()
        log.debug('sending message: %s', [method_id, counter, args], extra=self._extra)
        self.pr.write(msgpack.packb([method_id, counter, args]))

        stream = Stream()
        self.sessions[counter] = stream
        raise asyncio.Return(stream)

    def __getattr__(self, name):
        log.debug("invoking generic method: '%s'", name, extra=self._extra)

        def on_getattr(*args):
            return self._invoke(name, *args)
        return on_getattr


class Locator(BaseService):
    def __init__(self, host="localhost", port=10053, loop=None):
        super(Locator, self).__init__(name="locator", host=host, port=port, loop=loop)
        self.api = API.Locator


class Service(BaseService):
    def __init__(self, name, host="localhost", port=10053, version=0, loop=None):
        super(Service, self).__init__(name=name, loop=loop)
        self.locator = Locator(host=host, port=port, loop=loop)
        self.api = {}
        self.host = None
        self.port = None
        self.version = version

    @asyncio.coroutine
    def connect(self):
        log.debug("checking if service connected", extra=self._extra)
        if self.connected():
            log.debug("already connected", extra=self._extra)
            return

        log.info("resolving ...", extra=self._extra)
        stream = yield self.locator.resolve(self.name)
        (self.host, self.port), version, self.api = yield stream.get()
        log.info("successfully resolved", extra=self._extra)

        # Version compatibility should be checked here.
        if self.version == 0 or version == self.version:
            self.api = dict((v, k) for k, v in self.api.iteritems())
        else:
            raise Exception("wrong service `%s` API version %d, %d is needed" %
                            (self.name, version, self.version))
        yield super(Service, self).connect()

########NEW FILE########
__FILENAME__ = runtime
#
#    Copyright (c) 2014+ Anton Tyurin <noxiouz@yandex.ru>
#    Copyright (c) 2014+ Evgeny Safronov <division494@gmail.com>
#    Copyright (c) 2011-2014 Other contributors as noted in the AUTHORS file.
#
#    This file is part of Cocaine.
#
#    Cocaine is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Cocaine is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import msgpack

import os
import asyncio
import logging

logging.basicConfig()
log = logging.getLogger("asyncio")
log.setLevel(logging.DEBUG)


class RuntimeMock(object):
    def __init__(self, unixsocket, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.endpoint = unixsocket
        self.actions = list()
        self.event = asyncio.Event()

    def serve(self):
        @asyncio.coroutine
        def _serve():
            yield asyncio.async(asyncio.start_unix_server(self.on_client,
                                                          path=self.endpoint,
                                                          loop=self.loop))
            yield self.event.wait()

        try:
            self.loop.run_until_complete(_serve())
        finally:
            os.remove(self.endpoint)

    def on(self, message, action):
        self.actions.append((message, action))

    @asyncio.coroutine
    def on_client(self, reader, writer):
        buff = msgpack.Unpacker()
        while not reader.at_eof():
            data = yield reader.read(100)
            buff.feed(data)
            for i in buff:
                log.info("%s", i)
                try:
                    map(lambda clb: apply(clb, (writer,)),
                        [cbk for trigger, cbk in self.actions if trigger == i])
                except Exception as err:
                    log.exception(err)

    def stop(self):
        self.event.emit()


if __name__ == '__main__':
    unix_socket_path = "enp"
    l = asyncio.get_event_loop()
    r = RuntimeMock(unix_socket_path, loop=l)
    i = 0

    def on_heartbeat(w):
        global i
        i += 1
        w.write(msgpack.packb([1, 0, []]))
        w.write(msgpack.packb([3, i, ["echo"]]))
        w.write(msgpack.packb([4, i, ["echo"]]))
        w.write(msgpack.packb([6, i, []]))
    r.on([1, 0, []], on_heartbeat)
    r.serve()

########NEW FILE########
__FILENAME__ = request
#
#    Copyright (c) 2014+ Anton Tyurin <noxiouz@yandex.ru>
#    Copyright (c) 2014+ Evgeny Safronov <division494@gmail.com>
#    Copyright (c) 2011-2014 Other contributors as noted in the AUTHORS file.
#
#    This file is part of Cocaine.
#
#    Cocaine is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Cocaine is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

from ..concurrent import Stream


class RequestStream(Stream):

    def read(self, **kwargs):
        return self.get(**kwargs)

    def close(self):
        return self.done()

########NEW FILE########
__FILENAME__ = response
#
#    Copyright (c) 2014+ Anton Tyurin <noxiouz@yandex.ru>
#    Copyright (c) 2014+ Evgeny Safronov <division494@gmail.com>
#    Copyright (c) 2011-2014 Other contributors as noted in the AUTHORS file.
#
#    This file is part of Cocaine.
#
#    Cocaine is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Cocaine is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import traceback

import msgpack


class ResponseStream(object):
    def __init__(self, session, worker, event_name=""):
        self._m_state = 1
        self.worker = worker
        self.session = session
        self.event = event_name

    def write(self, chunk):
        chunk = msgpack.packb(chunk)
        if self._m_state is not None:
            self.worker.send_chunk(self.session, chunk)
            return
        traceback.print_stack()

    def close(self):
        if self._m_state is not None:
            self.worker.send_choke(self.session)
            self._m_state = None
            return
        traceback.print_stack()

    def error(self, code, message):
        if self._m_state is not None:
            self.worker.send_error(self.session, code, message)
            self.close()

    @property
    def closed(self):
        return self._m_state is None

########NEW FILE########
__FILENAME__ = worker
#
#    Copyright (c) 2014+ Anton Tyurin <noxiouz@yandex.ru>
#    Copyright (c) 2014+ Evgeny Safronov <division494@gmail.com>
#    Copyright (c) 2011-2014 Other contributors as noted in the AUTHORS file.
#
#    This file is part of Cocaine.
#
#    Cocaine is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Cocaine is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import logging
import sys
import traceback

import asyncio

from ..asio.message import RPC
from ..asio.message import Message
from ..asio.utils import Timer
from ..asio import CocaineProtocol
from ..common import CocaineErrno
from ._wrappers import default
from .response import ResponseStream
from .request import RequestStream

DEFAULT_HEARTBEAT_TIMEOUT = 20
DEFAULT_DISOWN_TIMEOUT = 5

logging.basicConfig()
log = logging.getLogger("asyncio")
log.setLevel(logging.DEBUG)


class Worker(object):
    def __init__(self, disown_timeout=DEFAULT_DISOWN_TIMEOUT,
                 heartbeat_timeout=DEFAULT_HEARTBEAT_TIMEOUT,
                 loop=None, **kwargs):
        if heartbeat_timeout < disown_timeout:
            raise ValueError("heartbeat timeout must be greater then disown")

        self.loop = loop or asyncio.get_event_loop()

        self.disown_timer = Timer(self.on_disown,
                                  disown_timeout, self.loop)

        self.heartbeat_timer = Timer(self.on_heartbeat_timer,
                                     heartbeat_timeout, self.loop)

        self._dispatcher = {
            RPC.HEARTBEAT: self._dispatch_heartbeat,
            RPC.TERMINATE: self._dispatch_terminate,
            RPC.INVOKE: self._dispatch_invoke,
            RPC.CHUNK: self._dispatch_chunk,
            # RPC.ERROR: self._dispatch_error,
            RPC.CHOKE: self._dispatch_choke
        }

        # TBD move into opts
        try:
            self.appname = kwargs.get("app") or sys.argv[sys.argv.index("--app") + 1]
            self.uuid = kwargs.get("uuid") or sys.argv[sys.argv.index("--uuid") + 1]
            self.endpoint = kwargs.get("endpoint") or sys.argv[sys.argv.index("--endpoint") + 1]
        except (ValueError, IndexError) as err:
            raise Exception("wrong commandline args %s" % err)

        # storehouse for sessions
        self.sessions = {}
        # handlers for events
        self._events = {}
        # protocol
        self.pr = None

        # avoid unnecessary dublicate packing of message
        self._heartbeat_msg = Message(RPC.HEARTBEAT, 0).pack()

    def async_connect(self):
        proto_factory = CocaineProtocol.factory(self.on_message,
                                                self.on_failure)

        @asyncio.coroutine
        def on_connect():
            log.debug("connecting to %s", self.endpoint)
            try:
                _, self.pr = yield self.loop.create_unix_connection(proto_factory,
                                                                    self.endpoint)
                log.debug("connected to %s", self.endpoint)
            except asyncio.FileNotFoundError as err:
                log.error("unable to connect to UNIX socket '%s'. No such file.",
                          self.endpoint)
            except Exception as err:
                log.error("unable to connect to '%s' %s", self.endpoint, err)
            else:
                self._send_handshake()
                self._send_heartbeat()
                return
            self.on_failure()

        asyncio.async(on_connect(), self.loop)

    def run(self, binds=None):
        if binds is None:
            binds = {}
        # attach handlers
        for event, handler in binds.iteritems():
            self.on(event, handler)

        # schedule connection establishment
        self.async_connect()
        # start heartbeat timer
        self.heartbeat_timer.start()

        if not self.loop.is_running():
            self.loop.run_forever()

    def on(self, event_name, event_handler):
        log.error(event_name)
        try:
            # Try to construct handler.
            closure = event_handler()
        except Exception:
            closure = default(event_handler)()
            if hasattr(closure, "_wrapped"):
                event_handler = default(event_handler)
        else:
            if not hasattr(closure, "_wrapped"):
                event_handler = default(event_handler)
        log.debug("attach handler for event %s", event_name)
        self._events[event_name] = event_handler

    # Events
    # healthmonitoring events
    def on_heartbeat_timer(self):
        self._send_heartbeat()

    def on_disown(self):
        try:
            log.error("disowned")
        finally:
            self._stop()

    # General dispathc method
    def on_message(self, args):
        log.debug("on_message")
        message = Message.initialize(args)
        callback = self._dispatcher.get(message.id)
        if callback is None:
            raise Exception("unknown message type %s" % str(message))

        callback(message)

    def terminate(self, code, reason):
        self.pr.write(Message(RPC.TERMINATE, 0,
                              code, reason).pack())
        self._stop()

    def _dispatch_heartbeat(self, _):
        log.debug("heartbeat has been received. Stop disown timer")
        self.disown_timer.stop()

    def _dispatch_terminate(self, msg):
        log.debug("terminate has been received %s %s", msg.reason, msg.message)
        self.terminate(msg.reason, msg.message)

    def _dispatch_invoke(self, msg):
        log.debug("invoke has been received %s", msg)
        request = RequestStream()
        response = ResponseStream(msg.session, self, msg.event)
        try:
            event_closure = self._events.get(msg.event)
            if event_closure is not None:
                event_handler = event_closure()
                event_handler.invoke(request, response, self.loop)
                self.sessions[msg.session] = request
            else:
                self._logger.warn("there is no handler for event %s",
                                  msg.event)
                response.error(CocaineErrno.ENOHANDLER,
                               "there is no handler for event %s" % msg.event)
        except (ImportError, SyntaxError) as err:
            response.error(CocaineErrno.EBADSOURCE,
                           "source is broken %s" % str(err))
            self.terminate(CocaineErrno.EBADSOURCE,
                           "source is broken")
        except Exception as err:
            log.error("invocation failed %s", err)
            traceback.print_stack()
            response.error(CocaineErrno.EINVFAILED,
                           "invocation failed %s" % err)

    def _dispatch_chunk(self, msg):
        log.debug("chunk has been received %d", msg.session)
        try:
            _session = self.sessions[msg.session]
            _session.push(msg.data)
        except Exception as err:
            log.error("pushing error %s", err)
            # self.terminate(1, "Push error: %s" % str(err))
            return

    def _dispatch_choke(self, msg):
        log.debug("choke has been received %d", msg.session)
        _session = self.sessions.get(msg.session)
        if _session is not None:
            _session.done()
            self.sessions.pop(msg.session)

    # On disconnection callback
    def on_failure(self, *args):
        log.error("connection has been lost")
        self.on_disown()

    # Private:
    def _send_handshake(self):
        self.pr.write(Message(RPC.HANDSHAKE, 0, self.uuid).pack())

    def _send_heartbeat(self):
        self.disown_timer.start()
        log.debug("heartbeat has been sent. Start disown timer")
        self.pr.write(self._heartbeat_msg)

    def send_choke(self, session):
        self.pr.write(Message(RPC.CHOKE, session).pack())

    def send_chunk(self, session, data):
        self.pr.write(Message(RPC.CHUNK, session, data).pack())

    def send_error(self, session, code, msg):
        self.pr.write(Message(RPC.ERROR, session, code, msg).pack())

    def _stop(self):
        self.loop.stop()

########NEW FILE########
__FILENAME__ = _wrappers
#
#    Copyright (c) 2014+ Anton Tyurin <noxiouz@yandex.ru>
#    Copyright (c) 2014+ Evgeny Safronov <division494@gmail.com>
#    Copyright (c) 2011-2014 Other contributors as noted in the AUTHORS file.
#
#    This file is part of Cocaine.
#
#    Cocaine is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Cocaine is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#


__all__ = ["proxy_factory"]

import asyncio

import inspect


class ChokeEvent(Exception):
    def __str__(self):
        return 'ChokeEvent'


class _Proxy(object):

    _wrapped = True

    @property
    def closed(self):
        return self._state is None


class _Coroutine(_Proxy):
    """Wrapper for coroutine function """

    def __init__(self, func):
        self._obj = func

    def invoke(self, request, response, loop):
        loop.call_soon_threadsafe(asyncio.async, self._obj(request, response))


def type_traits(func_or_generator):
    """ Return class object depends on type of callable object """
    if inspect.isgeneratorfunction(func_or_generator):
        return _Coroutine
    else:
        raise ValueError("Event handler must be a generatorfunction")


def patch_response(obj, response_handler):
    def decorator(handler):
        def dec(func):
            def wrapper(request, response):
                return func(request, handler(response))
            return wrapper
        return dec

    obj.invoke = decorator(response_handler)(obj.invoke)
    return obj


def patch_request(obj, request_handler):
    def req_decorator(handler):
        def dec(func):
            def wrapper(request, response):
                return func(handler(request), response)
            return wrapper
        return dec

    obj.invoke = req_decorator(request_handler)(obj.invoke)
    return obj


def proxy_factory(func, request_handler=None, response_handler=None):
    def wrapper():
        _factory = type_traits(func)
        obj = _factory(func)
        if response_handler is not None:
            obj = patch_response(obj, response_handler)
        if request_handler is not None:
            obj = patch_request(obj, request_handler)
        return obj
    return wrapper


def default(func):
    return proxy_factory(func, None, None)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
import sys
import os

print os.getcwd()

sys.path.insert(0, '..')


extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest']

source_suffix = '.rst'
master_doc = 'index'

# General information about the project.
project = u'cocaine-framework-python'
copyright = u'2013, Evgeny Safronov <division494@gmail.com>'
version = '0.11.0'
release = '0'

exclude_trees = ['_build']
exclude_patterns = []
pygments_style = 'sphinx'


html_theme = 'default'
html_title = "%s v%s" % (project, version)

########NEW FILE########
__FILENAME__ = check
#!/usr/bin/env python
import os
from tornado.ioloop import IOLoop
from cocaine import concurrent
import msgpack
import sys
from cocaine.protocol import ChokeEvent

from cocaine.services import Service

__author__ = 'EvgenySafronov <division494@gmail.com>'


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: chunker.py NUMBER_OF_CHUNKS')
        exit(os.EX_USAGE)

    @concurrent.engine
    def fetchAll():
        yield service.connect()
        df = service.enqueue('spam', str(sys.argv[1]))
        size = 0
        counter = 0
        try:
            while True:
                ch = yield df
                chunk = msgpack.loads(ch)
                size += len(chunk)
                counter += 1
                # print(counter, len(chunk), size)
                if chunk == 'Done':
                    break
        except ChokeEvent:
            pass
        except Exception as err:
            print(err)
        finally:
            IOLoop.current().stop()


    service = Service('chunker')
    fetchAll()
    IOLoop.current().start()
    print('Done')

########NEW FILE########
__FILENAME__ = chunker
#!/usr/bin/env python
import msgpack

from cocaine.server.worker import Worker

__author__ = 'EvgenySafronov <division494@gmail.com>'


def chunker(request, response):
    chunks = yield request.read()
    try:
        chunks = int(msgpack.loads(chunks))
    except ValueError:
        chunks = int(chunks)

    for num in xrange(chunks):
        response.write(msgpack.dumps('{0:-<1024}'.format(num)))
    response.write(msgpack.dumps('Done'))
    response.close()

W = Worker()
W.run({'spam': chunker})
########NEW FILE########
__FILENAME__ = docker
#!/usr/bin/env python
import msgpack

from cocaine.server.worker import Worker
from cocaine.logging import Logger

__author__ = 'Evgeny Safronov <division494@gmail.com>'

log = Logger()


def echo(request, response):
    message = yield request.read()
    log.debug('Message received: \'{0}\'. Sending it back ...'.format(message))
    response.write(msgpack.dumps(message))
    response.close()


W = Worker()
W.run({
    'doIt': echo,
})

########NEW FILE########
__FILENAME__ = dummy
#!/usr/bin/env python
# For YaSubbotnik at 15.06.2013

from cocaine.server.worker import Worker

W = Worker() # Dispatcher object

def event_handler(request, response):
    req = yield request.read() # Read incoming data
    if "Hello!" in req:
        response.write("Hello, world!") # Send data chunk
    else:
        response.write("Please, say 'Hello' to me!")
    response.close()

W.run({"hello" : event_handler}) # Run event loop - ready to work!

########NEW FILE########
__FILENAME__ = dummy_service
#!/usr/bin/env python

from cocaine.server.worker import Worker
from cocaine.services import Service

storage = Service("storage")

def write_dummy(request, response):
    req = yield request.read()
    yield storage.write("dummy-namespace", "dummy-key",
                        req, ["dummy-tag"])
    dummy = yield storage.read("dummy-namespace", "dummy-key")
    response.write(dummy)
    response.close()

W = Worker()
W.run({"write_dummy" : write_dummy})

########NEW FILE########
__FILENAME__ = check
from tornado.ioloop import IOLoop

from cocaine import concurrent
from cocaine.services import Service

__author__ = 'Evgeny Safronov <division494@gmail.com>'


@concurrent.engine
def pingV0():
    try:
        response = yield echo.enqueue('pingV0', 'Whatever.')
        print(response)
        assert response == 'Whatever.'
    except Exception as err:
        print(repr(err))
    finally:
        IOLoop.current().stop()


@concurrent.engine
def pingV1():
    try:
        response = [0, 0, 0, 0]
        channel = echo.enqueue('pingV1')
        response[0] = yield channel.read()
        response[1] = yield channel.write('Whatever.')
        response[2] = yield channel.read()
        response[3] = yield channel.write('Bye.')
        print(response)
        assert response == ['Hi!', 'Whatever.', 'Another message.', 'Bye.']
    except Exception as err:
        print(repr(err))
    finally:
        IOLoop.current().stop()


if __name__ == '__main__':
    echo = Service('echo')
    pingV1()
    IOLoop.current().start()
########NEW FILE########
__FILENAME__ = echo
#!/usr/bin/env python

from cocaine.server.worker import Worker
from cocaine.logging.defaults import log

__author__ = 'EvgenySafronov <division494@gmail.com>'


def echoV0(request, response):
    message = yield request.read()
    log.debug('Message received: \'{0}\'. Sending it back ...'.format(message))
    response.write(message)
    response.close()


def echoV1(request, response):
    response.write('Hi!')
    message = yield request.read()
    log.debug('Message received: \'{0}\'. Sending it back ...'.format(message))
    response.write(message)
    response.write('Another message.')
    message = yield request.read()
    log.debug('Message received: \'{0}\'. Sending it back ...'.format(message))
    response.write(message)
    response.close()


worker = Worker()
worker.run({
    'pingV0': echoV0,
    'pingV1': echoV1,
})

########NEW FILE########
__FILENAME__ = settings
# Django settings for enterprise project.
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': '',
        'PASSWORD': '',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '&+gey#2yhm&k%)m+k(jan+5p9s$^5v&ag1z%wl=d_tdk=39g#o'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'enterprise.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'enterprise.wsgi.application'

TEMPLATE_DIRS = (
    os.path.abspath('templates')
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'spock'
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

import spock.views

urlpatterns = patterns('',
    url(r'^apps/$', spock.views.apps),
    url(r'^info/$', spock.views.info),
)

########NEW FILE########
__FILENAME__ = wsgi
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "enterprise.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()



########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "enterprise.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = slave
#!/usr/bin/env python
import logging
import os

from cocaine.decorators.wsgi import django
from cocaine.logging import LoggerHandler
from cocaine.server.worker import Worker

__author__ = 'Evgeny Safronov <division494@gmail.com>'

PROJECT_NAME = 'enterprise'


log = logging.getLogger(__name__)
cocaineHandler = LoggerHandler()
log.addHandler(cocaineHandler)

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

worker = Worker()
worker.run({
    'work': django(**{
        'root': os.path.join(PROJECT_ROOT, PROJECT_NAME),
        'settings': '{0}.settings'.format(PROJECT_NAME),
        'async': True,
        'log': log
    })
})

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
import json
from django.http import HttpResponse
from django.shortcuts import render
from cocaine.tools.actions import common
from cocaine.services import Service


locator = Locator()
locator.connect('localhost', 10053, 1.0, blocking=True)
node = Service('node')


def apps(request):
    node = Service('node')
    list_ = yield node.list()
    yield render(request, 'list.html', {
        'apps': list_
    })


def info(request):
    info = yield common.NodeInfo(node, locator).execute()
    yield HttpResponse(json.dumps(info))
########NEW FILE########
__FILENAME__ = app
#!/usr/bin/env python
import StringIO

import qrcode

from cocaine.decorators import http
from cocaine.server.worker import Worker

__author__ = 'Evgeny Safronov <division494@gmail.com>'


"""
This example shows how to make simple HTTP Cocaine application using Cocaine Python Framework.

After waiting for http request, we read it and get some message from query string (?message=...). Then QR code
generation comes into.
Generated image is sending back via `response` stream.
"""


@http
def generate(request, response):
    request = yield request.read()
    try:
        message = request.request['message']
        out = StringIO.StringIO()
        img = qrcode.make(message)
        img.save(out, 'png')
        response.write_head(200, [('Content-type', 'image/png')])
        response.write(out.getvalue())
    except KeyError:
        response.write_head(400, [('Content-type', 'text/plain')])
        response.write('Query field "message" is required')
    except Exception as err:
        response.write_head(400, [('Content-type', 'text/plain')])
        response.write(str(err))
    finally:
        response.close()


w = Worker()
w.run({
    'generate': generate
})

########NEW FILE########
__FILENAME__ = elastic
import json
import time

from cocaine.services import Service

__author__ = 'Evgeny Safronov <division494@gmail.com>'


__doc__ = '''ELASTICSEARCH SERVICE USAGE EXAMPLE.
Elasticsearch must be started. Also elasticsearch cocaine plugin must be properly configured.
'''

now = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(time.time()))

elastic = Service('elasticsearch')

##### INDEX #####
print('Index simple message with index "/twitter/tweet/1"')
data = {
    'user': '3Hren',
    'post_date': now,
    'message': 'Hello, Elasticsearch!'
}
print('Result:', elastic.index(json.dumps(data), 'twitter', 'tweet', '1').get())
print('')

##### GET #####
print('And now get it')
print(elastic.get('twitter', 'tweet', '1').get())
print('')

##### INDEX GENERATE #####
print('Index simple message with id generated and get it')
data = {
    'user': '3Hren',
    'post_date': now,
    'message': 'Hello!'
}
status, index = elastic.index(json.dumps(data), 'twitter', 'tweet').get()
print([status, index])
print(elastic.get('twitter', 'tweet', '{0}'.format(index)).get())
print('')


##### SEARCH #####
print('Search records with message "Hello" from "/twitter/tweet"')
status, count, hits = elastic.search('twitter', 'tweet', 'message:Hello').get()
print(status, count, json.loads(hits))
print('')

print('Search 2 records with message "Hello" from "/twitter"')
status, count, hits = elastic.search('twitter', '', 'message:Hello', 2).get()
print(status, count, json.loads(hits))
print('')

##### DELETE #####
print('Do double delete record "/twitter/tweet/1" and get it')
print(elastic.delete('twitter', 'tweet', '1').get())
print(elastic.delete('twitter', 'tweet', '1').get())
print(elastic.get('twitter', 'tweet', '1').get())
########NEW FILE########
__FILENAME__ = docker
from __future__ import print_function

from cocaine.tools.actions import docker

__author__ = 'Evgeny Safronov <division494@gmail.com>'


client = docker.Client(url='http://localhost:4243', timeout=120.0)

print(client.info().get())
print(client.images().get())
client.build('/Users/esafronov/dock', tag='3hren/cocaine-test1:test-tag', quiet=True, streaming=print).get()
client.push('3hren/cocaine-test1', {
    'username': '3hren',
    'password': 'docker',
    'email': 'division494@gmail.com'
}, registry='localhost:5000', streaming=print).get()
print(client.containers().get())

########NEW FILE########
__FILENAME__ = manual
#!/usr/bin/env python
import os
import sys
from cocaine.protocol import ChokeEvent

import msgpack

from tornado.ioloop import IOLoop

from cocaine import concurrent
from cocaine.services import Service

__author__ = 'EvgenySafronov <division494@gmail.com>'


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: chunker.py NUMBER_OF_CHUNKS')
        exit(os.EX_USAGE)

    @concurrent.engine
    def test():
        deferred = service.enqueue('spam', str(sys.argv[1]))
        try:
            while True:
                chunk = yield deferred
                if chunk == 'Done':
                    break
        except ChokeEvent:
            pass
        except Exception as err:
            print('Error: {0}'.format(err))
        finally:
            loop.stop()

    service = Service('chunker')
    df = test()
    loop = IOLoop.current()
    loop.start()
    print('Done')

########NEW FILE########
__FILENAME__ = test_connector
#
#    Copyright (c) 2013+ Evgeny Safronov <division494@gmail.com>
#    Copyright (c) 2011-2013 Other contributors as noted in the AUTHORS file.
#
#    This file is part of Cocaine.
#
#    Cocaine is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Cocaine is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import logging
import socket
import sys

from mockito import when, unstub

from tornado import stack_context
from tornado.iostream import IOStream
from tornado.testing import AsyncTestCase

from cocaine.asio.exceptions import TimeoutError, ConnectError
from cocaine.services.base import Connector
from cocaine.testing.mocks import serve

__author__ = 'Evgeny Safronov <division494@gmail.com>'


log = logging.getLogger('cocaine')
h = logging.StreamHandler(stream=sys.stdout)
log.addHandler(h)
log.setLevel(logging.DEBUG)
log.propagate = False


class ConnectorTestCase(AsyncTestCase):
    def tearDown(self):
        unstub()

    def test_connect(self):
        def on_connect(future):
            stream = future.get()
            self.assertIsInstance(stream, IOStream)
            self.stop()

        with serve(60000):
            connector = Connector('localhost', 60000, io_loop=self.io_loop)
            deferred = connector.connect()
            deferred.add_callback(stack_context.wrap(on_connect))
            self.wait()

    def test_consequentially_connect(self):
        def on_connect(future):
            stream = future.get()
            self.assertIsInstance(stream, IOStream)
            self.stop()

        with serve(60000):
            when(socket).getaddrinfo('localhost', 60000, 0, socket.SOCK_STREAM).thenReturn([
                (30, 1, 6, '', ('::1', 59999, 0, 0)),
                (30, 1, 6, '', ('::1', 60000, 0, 0))
            ])

            connector = Connector('localhost', 60000, io_loop=self.io_loop)
            deferred = connector.connect()
            deferred.add_callback(stack_context.wrap(on_connect))
            self.wait()

    def test_throws_timeout_error_when_connection_timeout(self):
        def on_connect(future):
            self.assertRaises(TimeoutError, future.get)
            self.stop()

        with serve(60000):
            connector = Connector('localhost', 60000, timeout=0.000001, io_loop=self.io_loop)
            deferred = connector.connect()
            deferred.add_callback(stack_context.wrap(on_connect))
            self.wait()

    def test_throws_error_when_cannot_connect(self):
        def on_connect(future):
            self.assertRaises(ConnectError, future.get)
            self.stop()

        connector = Connector('localhost', 60000, io_loop=self.io_loop)
        deferred = connector.connect()
        deferred.add_callback(stack_context.wrap(on_connect))
        self.wait()

    def test_allow_multiple_invocation_of_connect_method(self):
        def on_connect(future):
            stream = future.get()
            self.assertIsInstance(stream, IOStream)
            self.stop()

        with serve(60000):
            connector = Connector('localhost', 60000, io_loop=self.io_loop)
            deferred = connector.connect()
            deferred_2 = connector.connect()
            deferred_3 = connector.connect()
            deferred.add_callback(stack_context.wrap(on_connect))
            self.assertEqual(deferred, deferred_2)
            self.assertEqual(deferred, deferred_3)
            self.wait()
########NEW FILE########
__FILENAME__ = test_generator
import logging
import os
import unittest
import sys

from tornado.testing import AsyncTestCase

from cocaine import concurrent
from cocaine.concurrent import Deferred, return_
from cocaine.concurrent.util import All, Any, PackagedTaskError
from cocaine.testing import trigger_check, DeferredMock


__author__ = 'Evgeny Safronov <division494@gmail.com>'


log = logging.getLogger('cocaine')


class DeferredTestCase(unittest.TestCase):
    def test_Class(self):
        Deferred()

    def test_CanStoreCallbacks(self):
        triggered = [False]
        actual = [None]

        def check(r):
            actual[0] = r.get()
            triggered[0] = True

        d = Deferred()
        d.add_callback(check)
        d.trigger('Test')

        self.assertTrue(triggered[0])
        self.assertEqual('Test', actual[0])

    def test_RaisesErrorOnErrorTrigger(self):
        triggered = [False]

        def check(r):
            self.assertRaises(ValueError, r.get)
            triggered[0] = True

        d = Deferred()
        d.add_callback(check)
        d.error(ValueError('Test'))

        self.assertTrue(triggered[0])

    def test_DoNotLoseChunkWhenCallbackIsNotSetYet(self):
        triggered = [False]
        actual = [None]

        d = Deferred()
        d.trigger('Test')

        def check(r):
            triggered[0] = True
            actual[0] = r.get()

        d.add_callback(check)

        self.assertTrue(triggered[0])
        self.assertEqual('Test', actual[0])


class EngineTestCase(AsyncTestCase):
    os.environ.setdefault('ASYNC_TEST_TIMEOUT', '0.5')

    def test_YieldDeferredWithSingleResult(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                d = DeferredMock([1], io_loop=self.io_loop)
                result = yield d
                self.assertEqual(1, result)
                trigger.toggle()
                self.stop()
            test()
            self.wait()

    def test_YieldDeferredWithTwoResults(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                d = DeferredMock([1, 2], io_loop=self.io_loop)
                r1 = yield d
                r2 = yield d
                self.assertEqual(1, r1)
                self.assertEqual(2, r2)
                trigger.toggle()
                self.stop()
            test()
            self.wait()

    def test_YieldDeferredWithMultipleResults(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                d = DeferredMock([1, 2, 3, 4, 5], io_loop=self.io_loop)
                r1 = yield d
                r2 = yield d
                r3 = yield d
                r4 = yield d
                r5 = yield d
                self.assertEqual(1, r1)
                self.assertEqual(2, r2)
                self.assertEqual(3, r3)
                self.assertEqual(4, r4)
                self.assertEqual(5, r5)
                trigger.toggle()
                self.stop()
            test()
            self.wait()

    def test_YieldTwoDeferredWithSingleResultsSequentially(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                d1 = DeferredMock([1], io_loop=self.io_loop)
                r1 = yield d1
                d2 = DeferredMock([2], io_loop=self.io_loop)
                r2 = yield d2
                self.assertEqual(1, r1)
                self.assertEqual(2, r2)
                trigger.toggle()
                self.stop()
            test()
            self.wait()

    def test_YieldTwoDeferredWithSingleResultsParallel(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                d1 = DeferredMock([1], io_loop=self.io_loop)
                d2 = DeferredMock([2], io_loop=self.io_loop)
                r1 = yield d1
                r2 = yield d2
                self.assertEqual(1, r1)
                self.assertEqual(2, r2)
                trigger.toggle()
                self.stop()
            test()
            self.wait()

    def test_YieldTwoDeferredWithSingleResultsParallelReverse(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                d1 = DeferredMock([1], io_loop=self.io_loop)
                d2 = DeferredMock([2], io_loop=self.io_loop)
                r2 = yield d2
                r1 = yield d1
                self.assertEqual(1, r1)
                self.assertEqual(2, r2)
                trigger.toggle()
                self.stop()
            test()
            self.wait()

    def test_YieldTwoDeferredWithMultipleResultsParallel(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                d1 = DeferredMock([1, 2, 3, 4], io_loop=self.io_loop)
                d2 = DeferredMock(['a', 'b', 'c', 'd'], io_loop=self.io_loop)
                d1r1 = yield d1
                d1r2 = yield d1
                d1r3 = yield d1
                d1r4 = yield d1
                d2r1 = yield d2
                d2r2 = yield d2
                d2r3 = yield d2
                d2r4 = yield d2
                self.assertEqual(1, d1r1)
                self.assertEqual(2, d1r2)
                self.assertEqual(3, d1r3)
                self.assertEqual(4, d1r4)
                self.assertEqual('a', d2r1)
                self.assertEqual('b', d2r2)
                self.assertEqual('c', d2r3)
                self.assertEqual('d', d2r4)
                trigger.toggle()
                self.stop()
            test()
            self.wait()

    def test_YieldTwoDeferredWithMultipleResultsParallelTinyMixed(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                d1 = DeferredMock([1, 2, 3, 4], io_loop=self.io_loop)
                d2 = DeferredMock(['a', 'b', 'c', 'd'], io_loop=self.io_loop)
                d1r1 = yield d1
                d2r1 = yield d2
                d1r2 = yield d1
                d1r3 = yield d1
                d1r4 = yield d1
                d2r2 = yield d2
                d2r3 = yield d2
                d2r4 = yield d2
                self.assertEqual(1, d1r1)
                self.assertEqual(2, d1r2)
                self.assertEqual(3, d1r3)
                self.assertEqual(4, d1r4)
                self.assertEqual('a', d2r1)
                self.assertEqual('b', d2r2)
                self.assertEqual('c', d2r3)
                self.assertEqual('d', d2r4)
                trigger.toggle()
                self.stop()
            test()
            self.wait()

    def test_YieldTwoDeferredWithMultipleResultsParallelPairMixed(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                d1 = DeferredMock([1, 2, 3, 4], io_loop=self.io_loop)
                d2 = DeferredMock(['a', 'b', 'c', 'd'], io_loop=self.io_loop)
                d1r1 = yield d1
                d2r1 = yield d2
                d1r2 = yield d1
                d2r2 = yield d2
                d1r3 = yield d1
                d2r3 = yield d2
                d1r4 = yield d1
                d2r4 = yield d2
                self.assertEqual(1, d1r1)
                self.assertEqual(2, d1r2)
                self.assertEqual(3, d1r3)
                self.assertEqual(4, d1r4)
                self.assertEqual('a', d2r1)
                self.assertEqual('b', d2r2)
                self.assertEqual('c', d2r3)
                self.assertEqual('d', d2r4)
                trigger.toggle()
                self.stop()
            test()
            self.wait()

    def test_YieldTwoDeferredWithMultipleResultsParallelCompletelyMixed(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                d1 = DeferredMock([1, 2, 3, 4], io_loop=self.io_loop)
                d2 = DeferredMock(['a', 'b', 'c', 'd'], io_loop=self.io_loop)
                d1r1 = yield d1
                d2r1 = yield d2
                d2r2 = yield d2
                d1r2 = yield d1
                d1r3 = yield d1
                d2r3 = yield d2
                d2r4 = yield d2
                d1r4 = yield d1
                self.assertEqual(1, d1r1)
                self.assertEqual(2, d1r2)
                self.assertEqual(3, d1r3)
                self.assertEqual(4, d1r4)
                self.assertEqual('a', d2r1)
                self.assertEqual('b', d2r2)
                self.assertEqual('c', d2r3)
                self.assertEqual('d', d2r4)
                trigger.toggle()
                self.stop()
            test()
            self.wait()

    def test_YieldDeferredWithSingleError(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                d = DeferredMock([ValueError()], io_loop=self.io_loop)
                try:
                    yield d
                except ValueError:
                    trigger.toggle()
                finally:
                    self.stop()
            test()
            self.wait()

    def test_YieldDeferredWithSingleValueAndError(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                d = DeferredMock([1, ValueError()], io_loop=self.io_loop)
                r1 = None
                try:
                    r1 = yield d
                    yield d
                except ValueError:
                    trigger.toggle()
                finally:
                    self.assertEqual(1, r1)
                    self.stop()
            test()
            self.wait()

    def test_YieldDeferredWithSingleErrorAndValue(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                d = DeferredMock([ValueError(), 1], io_loop=self.io_loop)
                try:
                    yield d
                except ValueError:
                    trigger.toggle()
                finally:
                    r1 = yield d
                    self.assertEqual(1, r1)
                    self.stop()
            test()
            self.wait()

    def test_YieldDeferredWithReturnStatement(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def outer():
                yield DeferredMock(['Outer Message'], io_loop=self.io_loop)
                return_('Return Statement')

            @concurrent.engine
            def inner():
                result = yield outer()
                self.assertEqual('Return Statement', result)
                trigger.toggle()
                self.stop()
            inner()
            self.wait()

    def test_YieldDeferredWithReturnStatementInTheTop(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def outer():
                return_('Return Statement')
                yield DeferredMock(['Outer Message'], io_loop=self.io_loop)
                yield DeferredMock(['Another Outer Message'], io_loop=self.io_loop)

            @concurrent.engine
            def inner():
                result = yield outer()
                self.assertEqual('Return Statement', result)
                trigger.toggle()
                self.stop()
            inner()
            self.wait()

    def test_YieldDeferredWithReturnStatementInTheMiddle(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def outer():
                yield DeferredMock(['Outer Message'], io_loop=self.io_loop)
                return_('Return Statement')
                yield DeferredMock(['Another Outer Message'], io_loop=self.io_loop)

            @concurrent.engine
            def inner():
                result = yield outer()
                self.assertEqual('Return Statement', result)
                trigger.toggle()
                self.stop()
            inner()
            self.wait()

    def test_PropagateErrorsInNestedDeferred(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def outer():
                if True:
                    raise ValueError('Test Error')
                else:
                    yield DeferredMock(['Never Reached Outer Message'], io_loop=self.io_loop)

            @concurrent.engine
            def inner():
                try:
                    yield outer()
                except ValueError:
                    trigger.toggle()
                finally:
                    self.stop()
            inner()
            self.wait()


class AllTestCase(AsyncTestCase):
    os.environ.setdefault('ASYNC_TEST_TIMEOUT', '0.5')

    def test_AllSingleDeferred(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                d = DeferredMock([1], io_loop=self.io_loop)
                result = yield All([d])
                self.assertEqual([1], result)
                trigger.toggle()
                self.stop()
            test()
            self.wait()

    def test_AllMultipleDeferreds(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                d1 = DeferredMock([1], io_loop=self.io_loop)
                d2 = DeferredMock([2], io_loop=self.io_loop)
                d3 = DeferredMock([3], io_loop=self.io_loop)
                result = yield All([d1, d2, d3])
                self.assertEqual([1, 2, 3], result)
                trigger.toggle()
                self.stop()
            test()
            self.wait()

    def test_AllSingleDeferredWithError(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                try:
                    d = DeferredMock([ValueError('Error message')], io_loop=self.io_loop)
                    yield All([d])
                except PackagedTaskError as err:
                    self.assertEqual(1, len(err.results))
                    self.assertTrue(isinstance(err.results[0], ValueError))
                    self.assertEqual('Error message', err.results[0].message)
                    trigger.toggle()
                finally:
                    self.stop()
            test()
            self.wait()

    def test_AllMultipleDeferredWithError(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                try:
                    d1 = DeferredMock([ValueError()], io_loop=self.io_loop)
                    d2 = DeferredMock([Exception()], io_loop=self.io_loop)
                    d3 = DeferredMock([SyntaxError()], io_loop=self.io_loop)
                    yield All([d1, d2, d3])
                except PackagedTaskError as err:
                    self.assertEqual(3, len(err.results))
                    self.assertTrue(isinstance(err.results[0], ValueError))
                    self.assertTrue(isinstance(err.results[1], Exception))
                    self.assertTrue(isinstance(err.results[2], SyntaxError))
                    trigger.toggle()
                finally:
                    self.stop()
            test()
            self.wait()

    def test_AllMultipleDeferredMixed(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                try:
                    d1 = DeferredMock([ValueError()], io_loop=self.io_loop)
                    d2 = DeferredMock(['Ok'], io_loop=self.io_loop)
                    d3 = DeferredMock([123], io_loop=self.io_loop)
                    yield All([d1, d2, d3])
                except PackagedTaskError as err:
                    self.assertEqual(3, len(err.results))
                    self.assertTrue(isinstance(err.results[0], ValueError))
                    self.assertEqual('Ok', err.results[1])
                    self.assertEqual(123, err.results[2])
                    trigger.toggle()
                finally:
                    self.stop()
            test()
            self.wait()


class AnyTestCase(AsyncTestCase):
    os.environ.setdefault('ASYNC_TEST_TIMEOUT', 0.5)

    def test_AnySingleDeferred(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                d = DeferredMock([1], io_loop=self.io_loop)
                result = yield Any([d])
                self.assertEqual([1], result)
                trigger.toggle()
                self.stop()
            test()
            self.wait()

    def test_AnyMultipleDeferreds(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                d1 = DeferredMock([1], io_loop=self.io_loop)
                d2 = DeferredMock([2], io_loop=self.io_loop)
                d3 = DeferredMock([3], io_loop=self.io_loop)
                result = yield Any([d1, d2, d3])
                self.assertEqual([1, None, None], result)
                trigger.toggle()
                self.stop()
            test()
            self.wait()

    def test_AnySingleDeferredWithError(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                try:
                    d = DeferredMock([ValueError('Error message')], io_loop=self.io_loop)
                    yield Any([d])
                except PackagedTaskError as err:
                    self.assertEqual(1, len(err.results))
                    self.assertTrue(isinstance(err.results[0], ValueError))
                    self.assertEqual('Error message', err.results[0].message)
                    trigger.toggle()
                finally:
                    self.stop()
            test()
            self.wait()

    def test_AnyMultipleDeferredWithError(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                try:
                    d1 = DeferredMock([ValueError()], io_loop=self.io_loop)
                    d2 = DeferredMock([Exception()], io_loop=self.io_loop)
                    d3 = DeferredMock([SyntaxError()], io_loop=self.io_loop)
                    yield Any([d1, d2, d3])
                except PackagedTaskError as err:
                    self.assertEqual(3, len(err.results))
                    self.assertTrue(isinstance(err.results[0], ValueError))
                    self.assertEqual(None, err.results[1])
                    self.assertEqual(None, err.results[2])
                    trigger.toggle()
                finally:
                    self.stop()
            test()
            self.wait()

    def test_AnyMultipleDeferredMixed(self):
        with trigger_check(self) as trigger:
            @concurrent.engine
            def test():
                try:
                    d2 = DeferredMock(['Ok'], io_loop=self.io_loop)
                    d1 = DeferredMock([ValueError()], io_loop=self.io_loop)
                    d3 = DeferredMock([123], io_loop=self.io_loop)
                    results = yield Any([d1, d2, d3])

                    self.assertEqual(3, len(results))
                    self.assertEqual(None, results[0])
                    self.assertEqual('Ok', results[1])
                    self.assertEqual(None, results[2])
                    trigger.toggle()
                finally:
                    self.stop()
            test()
            self.wait()
########NEW FILE########
__FILENAME__ = test_service
#
#    Copyright (c) 2013+ Evgeny Safronov <division494@gmail.com>
#    Copyright (c) 2011-2013 Other contributors as noted in the AUTHORS file.
#
#    This file is part of Cocaine.
#
#    Cocaine is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Cocaine is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import logging
import sys

from tornado.testing import AsyncTestCase

from cocaine import concurrent
from cocaine.services import Service
from cocaine.testing.mocks import RuntimeMock, Chunk, Choke

__author__ = 'Evgeny Safronov <division494@gmail.com>'


log = logging.getLogger('cocaine')


class RuntimeTestCase(AsyncTestCase):
    def setUp(self):
        super(RuntimeTestCase, self).setUp()
        self.runtime = self.get_runtime()

    def tearDown(self):
        super(RuntimeTestCase, self).tearDown()
        self.runtime.stop()

    def get_runtime(self):
        return RuntimeMock()


class ServiceTestCase(RuntimeTestCase):
    def test_single_chunk(self):
        self.runtime.register('node', 10054, 1, {0: 'list'})
        self.runtime.when('node').invoke(0).answer([
            Chunk(['echo']),
            Choke()
        ])
        self.runtime.start()

        @concurrent.engine
        def test():
            yield node.connect()
            self.assertTrue(node.connected())
            actual = yield node.list()
            self.assertEqual(['echo'], actual)
            self.stop()

        node = Service('node')
        test()
        self.wait()

    def test_single_chunk2(self):
        self.runtime.register('node', 10054, 1, {0: 'list'})
        self.runtime.when('node').invoke(0).answer([
            Chunk(['echo']),
            Choke()
        ])
        self.runtime.start()

        @concurrent.engine
        def test():
            yield node.connect()
            actual = yield node.list()
            self.assertEqual(['echo'], actual)
            self.stop()

        node = Service('node')
        test()
        self.wait()

########NEW FILE########
__FILENAME__ = test_state
import unittest

from cocaine.services.state import StateBuilder, RootState, State

__author__ = 'Evgeny Safronov <division494@gmail.com>'


class StateTestCase(unittest.TestCase):
    def test_state_builder(self):
        api = {
            0: (
                'enqueue', {
                    0: ('write', {}),
                    1: ('close', {})
                }
            ),
            1: ('info', {})
        }

        builder = StateBuilder()
        actual = builder.build(api)

        expected = RootState()
        state = State(0, 'enqueue', expected)
        State(1, 'info', expected)
        State(0, 'write', state)
        State(1, 'close', state)
        self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_stream
#
#    Copyright (c) 2013+ Evgeny Safronov <division494@gmail.com>
#    Copyright (c) 2011-2013 Other contributors as noted in the AUTHORS file.
#
#    This file is part of Cocaine.
#
#    Cocaine is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Cocaine is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import logging
import socket
import msgpack

from tornado.testing import AsyncTestCase

from cocaine.asio.stream import CocaineStream
from cocaine.testing.mocks import serve

__author__ = 'Evgeny Safronov <division494@gmail.com>'


log = logging.getLogger('cocaine')


class StreamTestCase(AsyncTestCase):
    def test_can_connect(self):
        with serve(60000):
            stream = CocaineStream(socket.socket(), self.io_loop)
            stream.connect(('127.0.0.1', 60000))
            self.assertFalse(stream.closed())
            self.assertTrue(stream.connecting())
            self.assertFalse(stream.connected())

    def test_triggers_close_callback_when_closed(self):
        def on_closed():
            self.stop()

        def on_connect():
            server.stop()

        with serve(60000) as server:
            stream = CocaineStream(socket.socket(), self.io_loop)
            stream.connect(('127.0.0.1', 60000), on_connect)
            stream.set_close_callback(on_closed)
            self.wait()

    def test_triggers_on_message_callback_with_message(self):
        def on_message(message):
            self.assertEqual([4, 1, ['name']], message)
            self.stop()

        def on_connect():
            server.connections[stream.address()].write(msgpack.dumps([4, 1, ['name']]))

        with serve(60000) as server:
            stream = CocaineStream(socket.socket(), self.io_loop)
            stream.connect(('127.0.0.1', 60000))
            server.on_connect(on_connect)
            stream.set_read_callback(on_message)
            self.wait()

########NEW FILE########
__FILENAME__ = test_synchrony
#
#    Copyright (c) 2013+ Evgeny Safronov <division494@gmail.com>
#    Copyright (c) 2011-2013 Other contributors as noted in the AUTHORS file.
#
#    This file is part of Cocaine.
#
#    Cocaine is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Cocaine is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import logging
import os
import sys

from tornado.ioloop import IOLoop
from tornado.testing import AsyncTestCase

from cocaine.services.fiber import synchrony, Service
from cocaine.testing.mocks import RuntimeMock, Chunk, Choke

__author__ = 'Evgeny Safronov <division494@gmail.com>'


log = logging.getLogger('cocaine.testing')


def autoclosable(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        finally:
            IOLoop.current().stop()
    return wrapper


class SynchronyTestCase(AsyncTestCase):
    os.environ.setdefault('ASYNC_TEST_TIMEOUT', '0.5')

    # @synchrony
    # @autoclosable
    # def test_single_chunk(self):
    #     runtime = RuntimeMock()
    #     runtime.register('node', 10054, 1, {0: 'list'})
    #     runtime.when('node').invoke(0).answer([
    #         Chunk(['echo']),
    #         Choke()
    #     ])
    #     runtime.start()
    #
    #     node = Service('node')
    #     self.assertEqual(['echo'], node.list())
    #     runtime.stop()
########NEW FILE########
__FILENAME__ = w
#!/usr/bin/env python

import asyncio

from cocaine.worker import Worker
from cocaine.services import Service


w = Worker(app="app", uuid="a", endpoint="enp",
           heartbeat_timeout=2, disown_timeout=1)

node = Service("node", version=0)


@asyncio.coroutine
def echo(request, response):
    yield asyncio.sleep(1)
    inp = yield request.read(timeout=1)
    print inp
    fut = yield node.list()
    result = yield fut.get()
    print result
    response.write(result)
    response.close()

w.on("echo", echo)
w.run()

########NEW FILE########
