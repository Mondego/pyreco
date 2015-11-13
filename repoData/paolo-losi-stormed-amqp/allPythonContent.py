__FILENAME__ = benchmark
#!/usr/bin/env python

from tornado import ioloop, web, httpserver
from stormed import Message, Connection

"""
RoundTrip benchmark.
For each single request:
1. publish is own id on the broker
2. the broker replies with the id
3. the request is "finished"

1. Run this example
2. ab -n 1000 -c 10 http://localhost:8001/round_trip
"""

XNAME = "tornado_test_exchage"
QNAME = "tornado_test_queue"


request_map = dict()

def finish_request(msg):
    req_id = msg.body
    request = request_map.pop(req_id)
    request.write(req_id)
    request.finish()


class RoundTripHandler(web.RequestHandler):

    @web.asynchronous
    def get(self):
        req_id = str(id(self))
        request_map[req_id] = self
        msg = Message(req_id, delivery_mode=1)
        ch.publish(msg, exchange=XNAME)


def on_amqp_connection():
    global ch
    ch = conn.channel()
    ch.exchange_declare(exchange=XNAME, type="fanout")
    ch.queue_declare(queue=QNAME, durable=False)
    ch.queue_bind(queue=QNAME, exchange=XNAME)
    ch.consume(QNAME, finish_request, no_ack=True)

    application = web.Application([
        (r"/round_trip", RoundTripHandler),
    ])

    http_server = httpserver.HTTPServer(application)
    http_server.listen(8001)

ch = None
conn = None

def main():
    global ch, conn
    conn = Connection(host='localhost')
    conn.connect(on_amqp_connection)

    ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        conn.close()

########NEW FILE########
__FILENAME__ = receive
#! /usr/bin/env python

import logging
from tornado.ioloop import IOLoop
from stormed import Connection, Message

def on_connect():
    ch = conn.channel()
    ch.queue_declare(queue='hello')
    ch.consume('hello', callback, no_ack=True)

def callback(msg):
    print " [x] Received %r" % msg.body

logging.basicConfig()
conn = Connection(host='localhost')
conn.connect(on_connect)
io_loop = IOLoop.instance()
print ' [*] Waiting for messages. To exit press CTRL+C'
try:
    io_loop.start()
except KeyboardInterrupt:
    conn.close(io_loop.stop)

########NEW FILE########
__FILENAME__ = send
#! /usr/bin/env python

import logging
from tornado.ioloop import IOLoop
from stormed import Connection, Message

msg = Message('Hello World!')

def on_connect():
    ch = conn.channel()
    ch.queue_declare(queue='hello')
    ch.publish(msg, exchange='', routing_key='hello')
    conn.close(callback=done)

def done():
    print " [x] Sent 'Hello World!'"
    io_loop.stop()

logging.basicConfig()
conn = Connection(host='localhost')
conn.connect(on_connect)
io_loop = IOLoop.instance()
io_loop.start()

########NEW FILE########
__FILENAME__ = new_task
#! /usr/bin/env python

import logging
import sys
from tornado.ioloop import IOLoop
from stormed import Connection, Message

# delivery_mode=2 makes message persistent
msg = Message(' '.join(sys.argv[1:]) or 'Hello World!', delivery_mode=2)

def on_connect():
    ch = conn.channel()
    ch.queue_declare(queue='task_queue', durable=True)
    ch.publish(msg, exchange='', routing_key='task_queue')
    conn.close(callback=done)

def done():
    print " [x] Sent %r" % msg.body
    io_loop.stop()

logging.basicConfig()
conn = Connection(host='localhost')
conn.connect(on_connect)
io_loop = IOLoop.instance()
io_loop.start()

########NEW FILE########
__FILENAME__ = worker
#! /usr/bin/env python

import logging
import time
from tornado.ioloop import IOLoop
from stormed import Connection, Message

def on_connect():
    ch = conn.channel()
    ch.queue_declare(queue='task_queue', durable=True)
    ch.qos(prefetch_count=1)
    ch.consume('task_queue', callback)

def callback(msg):
    print " [x] Received %r" % msg.body
    sleep_time = msg.body.count('.')
    io_loop.add_timeout(time.time() + sleep_time, lambda: done(msg))

def done(msg):
    print " [x] Done"
    msg.ack()

logging.basicConfig()
conn = Connection(host='localhost')
conn.connect(on_connect)
io_loop = IOLoop.instance()
print ' [*] Waiting for messages. To exit press CTRL+C'
try:
    io_loop.start()
except KeyboardInterrupt:
    conn.close(io_loop.stop)

########NEW FILE########
__FILENAME__ = emit_log
#! /usr/bin/env python

import logging
import sys
from tornado.ioloop import IOLoop
from stormed import Connection, Message

# delivery_mode=2 makes message persistent
msg = Message(' '.join(sys.argv[1:]) or 'info: Hello World!')

def on_connect():
    ch = conn.channel()
    ch.exchange_declare(exchange='logs', type='fanout')
    ch.publish(msg, exchange='logs', routing_key='')
    conn.close(callback=done)

def done():
    print " [x] Sent %r" % msg.body
    io_loop.stop()

logging.basicConfig()
conn = Connection(host='localhost')
conn.connect(on_connect)
io_loop = IOLoop.instance()
io_loop.start()

########NEW FILE########
__FILENAME__ = receive_logs
#! /usr/bin/env python

import logging
from tornado.ioloop import IOLoop
from stormed import Connection, Message

ch = None

def on_connect():
    global ch
    ch = conn.channel()
    ch.exchange_declare(exchange='logs', type='fanout')
    ch.queue_declare(exclusive=True, callback=with_temp_queue)

def with_temp_queue(qinfo):
    ch.queue_bind(exchange='logs', queue=qinfo.queue)
    ch.consume(qinfo.queue, callback, no_ack=True)

def callback(msg):
    print " [x] %r" % msg.body

logging.basicConfig()
conn = Connection(host='localhost')
conn.connect(on_connect)
io_loop = IOLoop.instance()
print ' [*] Waiting for logs. To exit press CTRL+C'
try:
    io_loop.start()
except KeyboardInterrupt:
    conn.close(io_loop.stop)

########NEW FILE########
__FILENAME__ = emit_log_direct
#! /usr/bin/env python

import logging
import sys
from tornado.ioloop import IOLoop
from stormed import Connection, Message

# delivery_mode=2 makes message persistent
severity = sys.argv[1] if len(sys.argv) > 1 else 'info'
msg = Message(' '.join(sys.argv[2:]) or 'Hello World!')

def on_connect():
    ch = conn.channel()
    ch.exchange_declare(exchange='direct_logs', type='direct')
    ch.publish(msg, exchange='direct_logs', routing_key=severity)
    conn.close(callback=done)

def done():
    print " [x] Sent %r:%r" % (severity, msg.body)
    io_loop.stop()

logging.basicConfig()
conn = Connection(host='localhost')
conn.connect(on_connect)
io_loop = IOLoop.instance()
io_loop.start()

########NEW FILE########
__FILENAME__ = receive_logs_direct
#! /usr/bin/env python

import logging
import sys
from tornado.ioloop import IOLoop
from stormed import Connection, Message

severities = sys.argv[1:]
if not severities:
    print >> sys.stderr, "Usage: %s [info] [warning] [error]" % sys.argv[0]
    sys.exit(1)

ch = None

def on_connect():
    global ch
    ch = conn.channel()
    ch.exchange_declare(exchange='direct_logs', type='direct')
    ch.queue_declare(exclusive=True, callback=with_temp_queue)

def with_temp_queue(qinfo):
    for severity in severities:
        ch.queue_bind(exchange='direct_logs',
                      queue=qinfo.queue,
                      routing_key=severity)
    ch.consume(qinfo.queue, callback, no_ack=True)

def callback(msg):
    print " [x] %r:%r" % (msg.rx_data.routing_key, msg.body)

logging.basicConfig()
conn = Connection(host='localhost')
conn.connect(on_connect)
io_loop = IOLoop.instance()
print ' [*] Waiting for logs. To exit press CTRL+C'
try:
    io_loop.start()
except KeyboardInterrupt:
    conn.close(io_loop.stop)

########NEW FILE########
__FILENAME__ = emit_log_topic
#! /usr/bin/env python

import logging
import sys
from tornado.ioloop import IOLoop
from stormed import Connection, Message

# delivery_mode=2 makes message persistent
routing_key = sys.argv[1] if len(sys.argv) > 1 else 'anonymous.info'
msg = Message(' '.join(sys.argv[2:]) or 'Hello World!')

def on_connect():
    ch = conn.channel()
    ch.exchange_declare(exchange='topic_logs', type='topic')
    ch.publish(msg, exchange='topic_logs', routing_key=routing_key)
    conn.close(callback=done)

def done():
    print " [x] Sent %r:%r" % (routing_key, msg.body)
    io_loop.stop()

logging.basicConfig()
conn = Connection(host='localhost')
conn.connect(on_connect)
io_loop = IOLoop.instance()
io_loop.start()

########NEW FILE########
__FILENAME__ = receive_logs_topic
#! /usr/bin/env python

import logging
import sys
from tornado.ioloop import IOLoop
from stormed import Connection, Message

binding_keys = sys.argv[1:]
if not binding_keys:
    print >> sys.stderr, "Usage: %s [binding_key] ..." % sys.argv[0]
    sys.exit(1)

ch = None

def on_connect():
    global ch
    ch = conn.channel()
    ch.exchange_declare(exchange='topic_logs', type='topic')
    ch.queue_declare(exclusive=True, callback=with_temp_queue)

def with_temp_queue(qinfo):
    for binding_key in binding_keys:
        ch.queue_bind(exchange='topic_logs',
                      queue=qinfo.queue,
                      routing_key=binding_key)
    ch.consume(qinfo.queue, callback, no_ack=True)

def callback(msg):
    print " [x] %r:%r" % (msg.rx_data.routing_key, msg.body)

logging.basicConfig()
conn = Connection(host='localhost')
conn.connect(on_connect)
io_loop = IOLoop.instance()
print ' [*] Waiting for logs. To exit press CTRL+C'
try:
    io_loop.start()
except KeyboardInterrupt:
    conn.close(io_loop.stop)

########NEW FILE########
__FILENAME__ = rpc_client
#!/usr/bin/env python

import logging
import sys
import uuid
from tornado.ioloop import IOLoop
from stormed import Connection, Message

class FibonacciRpcClient(object):
    def __init__(self, n):
        self.conn = Connection(host='localhost')
        self.conn.connect(self.on_connect)
        self.n = n
    
    def on_connect(self):
        self.ch = self.conn.channel()
        self.ch.queue_declare(exclusive=True, callback=self.on_queue_declare)
    
    def on_queue_declare(self, q_info):
        callback_queue = q_info.queue
        self.ch.consume(callback_queue, self.on_response)
        self.corr_id = str(uuid.uuid4())
        msg = Message(str(self.n), delivery_mode=2, reply_to=callback_queue,
                      correlation_id=self.corr_id)
        self.ch.publish(msg, exchange='', routing_key='rpc_queue')
    
    def on_response(self, msg):
        if self.corr_id == msg.correlation_id:
            print " [x] Received %r" % msg.body
            self.conn.close(callback=IOLoop.instance().stop)
            print 'Closing connection.'

logging.basicConfig()
try:
    n = int(sys.argv[1])
except:
    n = 30
io_loop = IOLoop.instance()
fibonacci_rpc = FibonacciRpcClient(n)
print ' [x] Requesting fib(%s)' % n
try:
    io_loop.start()
except:
    io_loop.stop()

########NEW FILE########
__FILENAME__ = rpc_server
#!/usr/bin/env python

import logging
from tornado.ioloop import IOLoop
from stormed import Connection, Message

def fib(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n-1) + fib(n-2)

def on_connect():
    global ch
    ch = conn.channel()
    ch.queue_declare(queue='rpc_queue', durable=True)
    ch.qos(prefetch_count=1)
    ch.consume('rpc_queue', on_request)

def on_request(msg):
    n = int(msg.body)
    print " [.] fib(%s)" % n
    response = str(fib(n))
    response_msg = Message(response, delivery_mode=2,
                           correlation_id=msg.correlation_id)
    ch.publish(response_msg, exchange='', routing_key=msg.reply_to)
    msg.ack()

logging.basicConfig()
ch = None
conn = Connection(host='localhost')
conn.connect(on_connect)
io_loop = IOLoop.instance()
print ' [*] Waiting for messages. To exit press CTRL+C'
try:
    io_loop.start()
except KeyboardInterrupt:
    conn.close(io_loop.stop)

########NEW FILE########
__FILENAME__ = channel
from stormed.util import AmqpError
from stormed.method.channel import Open, Close, Flow
from stormed.method import exchange as _exchange, basic, queue as _queue, tx
from stormed.frame import FrameHandler, status

class FlowStoppedException(AmqpError): pass

class Channel(FrameHandler):
    """An AMQP Channel

    And AMQP Channel represent a logical connection to the AMQP server.
    Unless there are really specific needs, there is no reason to use
    more than one Channel instance per process for a
    standard stormed-amqp / tornadoweb application.

    Then Channel class should be only instantiated by
    stormed.Connection.channel method.

    Channel.on_error callback is called in case of "Soft" AMQP Error with
    a ChannelError instance as argument:

        def on_channel_error(channel_error):
            print channel_error.reply_code
            print channel_error.reply_text
            print channel_error.method

        channel.on_error = on_channel_error

    Channel.on_return is called when the AMQP server returns a
    message published by the client ("basic.return").
    the callback receives a stormed.Message as argument:

        def on_msg_returned(msg):
            print msg.rx_data.reply_code

        channel.on_return = on_msg_returnedi
    """

    def __init__(self, channel_id, conn):
        self.channel_id = channel_id
        self.consumers = {}
        self.status = status.CLOSED
        self.on_error = None
        self.on_return = None
        self.flow_stopped = False
        super(Channel, self).__init__(conn)

    def open(self, callback=None):
        self.status = status.OPENING
        self.send_method(Open(out_of_band=''), callback)

    def close(self, callback=None):
        self.status = status.CLOSING
        _close = Close(reply_code=0, reply_text='', class_id=0, method_id=0)
        self.send_method(_close, callback)

    def exchange_declare(self, exchange, type="direct", durable=False,
                               callback=None):
        self.send_method(_exchange.Declare(ticket      = 0,
                                           exchange    = exchange,
                                           type        = type,
                                           passive     = False,
                                           durable     = durable,
                                           auto_delete = False,
                                           internal    = False,
                                           nowait      = False,
                                           arguments   = dict()), callback)

    def exchange_delete(self, exchange, if_unused=False, callback=None):
        self.send_method(_exchange.Delete(ticket    = 0,
                                          exchange  = exchange,
                                          if_unused = if_unused,
                                          nowait    = False), callback)

    def queue_declare(self, queue='', passive=False, durable=True,
                            exclusive=False, auto_delete=False, callback=None):
        """implements "queue.declare" AMQP method

        the callback receives as argument a queue.DeclareOk method instance:

            def on_creation(qinfo):
                print qinfo.queue # queue name
                print qinfo.message_count
                print qinfo.consumer_count

            channel.queue_declare('queue_name', callback=on_creation)
        """

        self.send_method(_queue.Declare(ticket      = 0,
                                        queue       = queue,
                                        passive     = passive,
                                        durable     = durable,
                                        exclusive   = exclusive,
                                        auto_delete = auto_delete,
                                        nowait      = False,
                                        arguments   = dict()), callback)

    def queue_delete(self, queue, if_unused=False, if_empty=False,
                           callback=None):
        self.send_method(_queue.Delete(ticket    = 0,
                                       queue     = queue,
                                       if_unused = if_unused,
                                       if_empty  = if_empty,
                                       nowait    = False), callback)

    def queue_bind(self, queue, exchange, routing_key='', callback=None):
        self.send_method(_queue.Bind(ticket      = 0,
                                     queue       = queue,
                                     exchange    = exchange,
                                     routing_key = routing_key,
                                     nowait      = False,
                                     arguments   = dict()), callback)

    def queue_unbind(self, queue, exchange, routing_key='', callback=None):
        self.send_method(_queue.Unind(ticket      = 0,
                                      queue       = queue,
                                      exchange    = exchange,
                                      routing_key = routing_key,
                                      nowait      = False,
                                      arguments   = dict()), callback)

    def queue_purge(self, queue, callback=None):
        """implements "queue.purge" AMQP method

        the callback receives as argument the number of purged messages:

            def queue_purged(message_count):
                print message_count

            channel.queue_purge('queue_name')
        """

        self.send_method(_queue.Purge(ticket=0, queue=queue, nowait=False),
                         callback)

    def qos(self, prefetch_size=0, prefetch_count=0, _global=False,
                  callback=None):
        self.send_method(basic.Qos(prefetch_size  = prefetch_size,
                                   prefetch_count = prefetch_count,
                                   _global        = _global), callback)

    def publish(self, message, exchange, routing_key='', immediate=False,
                      mandatory=False):
        if self.flow_stopped:
            raise FlowStoppedException
        if (immediate or mandatory) and self.on_return is None:
            raise AmqpError("on_return callback must be set for "
                            "immediate or mandatory publishing")
        self.send_method(basic.Publish(ticket = 0,
                                       exchange = exchange,
                                       routing_key = routing_key,
                                       mandatory = mandatory,
                                       immediate = immediate), message=message)

    def get(self, queue, callback, no_ack=False):
        """implements "basic.get" AMQP method

        the callback receives as argument a stormed.Message instance
        or None if the AMQP queue is empty:

            def on_msg(msg):
                if msg is not None:
                    print msg.body
                else:
                    print "empty queue"

            channel.get('queue_name', on_msg)
        """
        _get = basic.Get(ticket=0, queue=queue, no_ack=no_ack)
        self.send_method(_get, callback)

    def consume(self, queue, consumer, no_local=False, no_ack=False,
                      exclusive=False):
        """implements "basic.consume" AMQP method

        The consumer argument is either a callback or a Consumer instance.
        The callback is called, with a Message instance as argument,
        each time the client receives a message from the server.
        """
        if not isinstance(consumer, Consumer):
            consumer = Consumer(consumer)
        def set_consumer(consumer_tag):
            consumer.tag = consumer_tag
            consumer.channel = self
            self.consumers[consumer_tag] = consumer
        _consume = basic.Consume(ticket       = 0,
                                 queue        = queue,
                                 consumer_tag = '',
                                 no_local     = no_local,
                                 no_ack       = no_ack,
                                 exclusive    = exclusive,
                                 nowait       = False,
                                 arguments    = dict())
        self.send_method(_consume, set_consumer)

    def recover(self, requeue=False, callback=None):
        self.send_method(basic.Recover(requeue=requeue), callback)

    def flow(self, active, callback=None):
        self.send_method(Flow(active=active), callback)

    def select(self, callback=None):
        if self.on_error is None:
            raise AmqpError("Channel.on_error callback must be set for tx mode")
        self.send_method(tx.Select(), callback)

    def commit(self, callback=None):
        self.send_method(tx.Commit(), callback)

    def rollback(self, callback=None):
        self.send_method(tx.Rollback(), callback)

class Consumer(object):
    """AMQP Queue consumer

    the Consumer can be used as Channel.consume() "consumer" argument
    when the application must be able to stop a specific basic.consume message
    flow from the server.
    """

    def __init__(self, callback):
        self.tag = None
        self.channel = None
        self.callback = callback

    def cancel(self, callback):
        """implements "basic.cancel" AMQP method"""
        _cancel = basic.Cancel(consumer_tag=self.tag, nowait=False)
        self.channel.send_method(_cancel, callback)

########NEW FILE########
__FILENAME__ = connection
import time
import socket

from tornado.iostream import IOStream
from tornado.ioloop import IOLoop

from stormed.util import logger
from stormed.frame import FrameReader, FrameHandler, status
from stormed.channel import Channel
from stormed.method.connection import Close

TORNADO_1_2 = hasattr(IOStream, 'connect')

class Connection(FrameHandler):
    """A "physical" TCP connection to the AMQP server

    heartbeat: int, optional
               the requested time interval in seconds for heartbeat frames.

    Connection.on_error callback, when set, is called in case of
    "hard" AMQP Error. It receives a ConnectionErrorinstance as argument:

        def handle_error(conn_error):
            print conn_error.method
            print conn_error.reply_code

        conn.on_error = handle_error

    Connection.on_disconnect callback, when set, is called in case of
    heartbeat timeout or TCP low level disconnection. It receives no args.
    """

    def __init__(self, host, username='guest', password='guest', vhost='/',
                       port=5672, heartbeat=0, io_loop=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.vhost = vhost
        self.heartbeat = heartbeat
        self.last_received_frame = None
        self.frame_max = 0
        self.io_loop = io_loop or IOLoop.instance()
        self.stream = None
        self.status = status.CLOSED
        self.channels = [self]
        self.channel_id = 0
        self.on_connect = None
        self.on_disconnect = None
        self.on_error = None
        self._close_callback = None
        self._frame_count = 0
        super(Connection, self).__init__(connection=self)

    def connect(self, callback):
        """open the connection to the server"""
        if self.status is not status.CLOSED:
            raise Exception('Connection status is %s' % self.status)
        self.status = status.OPENING
        sock = socket.socket()
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        self.on_connect = callback
        if TORNADO_1_2:
            self.stream = IOStream(sock, io_loop=self.io_loop)
            self.stream.set_close_callback(self.on_closed_stream)
            self.stream.connect((self.host, self.port), self._handshake)
        else:
            sock.connect((self.host, self.port))
            self.stream = IOStream(sock, io_loop=self.io_loop)
            self.stream.set_close_callback(self.on_closed_stream)
            self._handshake()

    def close(self, callback=None):
        """cleanly closes the connection to the server.

        all pending tasks are flushed before connection shutdown"""

        if self.status != status.CLOSING:
            self._close_callback = callback
            self.status = status.CLOSING
        channels = [ch for ch in self.channels if ch is not self]
        opened_chs  = [ch for ch in channels if ch.status in (status.OPENED,
                                                              status.OPENING)]
        closing_chs = [ch for ch in channels if ch.status == status.CLOSING]
        if opened_chs:
            for ch in opened_chs:
                ch.close(self.close)
        elif closing_chs:
            pass # let's wait
        else:
            m = Close(reply_code=0, reply_text='', class_id=0, method_id=0)
            self.send_method(m, self._close_callback)

    def channel(self, callback=None):
        """get a Channel instance"""
        if self.status == status.OPENED:
            ch = Channel(channel_id=len(self.channels), conn=self)
            self.channels.append(ch)
            ch.open(callback)
            return ch
        else:
            raise ValueError('connection is not opened')

    def _handshake(self):
        self.stream.write('AMQP\x00\x00\x09\x01')
        FrameReader(self.stream, self._frame_loop)

    def _frame_loop(self, frame):
        if self.heartbeat:
            self.last_received_frame = time.time()
        self.channels[frame.channel].process_frame(frame)
        self._frame_count += 1
        if self.stream:
            # Every 5 frames ioloop gets the control back in order
            # to avoid hitting the recursion limit
            # reading one frame cost 13 levels of stack recursion
            # TODO check if always using _callbacks is faster that frame
            # counting
            if self._frame_count == 5:
                self._frame_count = 0
                cb = lambda: FrameReader(self.stream, self._frame_loop)
                self._add_ioloop_callback(cb)
            else:
                FrameReader(self.stream, self._frame_loop)

    if TORNADO_1_2:
        def _add_ioloop_callback(self, callback):
            self.io_loop._callbacks.append(callback)
    else:
        def _add_ioloop_callback(self, callback):
            self.io_loop._callbacks.add(callback)

    def close_stream(self):
        if self.stream is None:
            return

        try:
            self.stream.close()
        finally:
            self.status = status.CLOSED
            self.stream = None

    def on_closed_stream(self):
        if self.status != status.CLOSED:
            if self.on_disconnect:
                try:
                    self.on_disconnect()
                except Exception:
                    logger.error('ERROR in on_disconnect() callback',
                                                                 exc_info=True)

    def reset(self):
        for c in self.channels:
            if c is not self:
                c.reset()
        super(Connection, self).reset()
        self.close_stream()

########NEW FILE########
__FILENAME__ = frame
import struct

from stormed.util import Enum, AmqpError, logger
from stormed.message import MessageBuilder
from stormed.serialization import parse_method, dump_method, \
                                  parse_content_header, dump_content_header

status = Enum('OPENING', 'OPENED', 'CLOSED', 'CLOSING')

frame_header = struct.Struct('!cHL')

class FrameReader(object):

    def __init__(self, stream, callback):
        self.stream = stream
        self.callback = callback
        self.frame = None
        self._read_header()

    def _read_header(self):
        self.stream.read_bytes(7, self._with_header)

    def _with_header(self, header):
        frame_type, channel, size = frame_header.unpack(header)
        #TODO assert frame_type
        self.frame = Frame(frame_type, channel, size)
        self.stream.read_bytes(size+1, self._with_payload)

    def _with_payload(self, payload_with_end):
        payload = payload_with_end[:-1]
        frame_end = payload_with_end[-1]
        if frame_end != '\xCE': #TODO use AMQP constants
            raise AmqpError('unexpected frame end')
        self.frame.set_payload(payload)
        self.callback(self.frame)

class Frame(object):

    def __init__(self, frame_type, channel, size):
        self.channel = channel
        self.size = size
        self.payload = None
        self.frame_type = frame_type

    def set_payload(self, payload):
        if self.frame_type == '\x01':
            self.payload = parse_method(payload)
            self.frame_type = 'method'
        elif self.frame_type == '\x02':
            self.payload = parse_content_header(payload)
            self.frame_type = 'content_header'
        elif self.frame_type == '\x03':
            self.payload = payload
            self.frame_type = 'content_body'
        elif self.frame_type == '\x08':
            self.frame_type = 'heartbeat'
        else:
            #FIXME logging instead of exception
            raise ValueError('unsupported frame type')

    def __repr__(self):
        return '<Frame(type=%r, channel=%d, size=%d)>' % (self.frame_type,
                                                          self.channel,
                                                          self.size)

def from_method(method, ch):
    payload = dump_method(method)
    header = frame_header.pack('\x01', ch.channel_id, len(payload))
    return '%s%s%s' % (header, payload, '\xCE')

def content_header_from_msg(msg, ch):
    payload = dump_content_header(msg)
    header = frame_header.pack('\x02', ch.channel_id, len(payload))
    return '%s%s%s' % (header, payload, '\xCE')

def body_frames_from_msg(msg, ch):
    max_size = ch.conn.frame_max - frame_header.size - 1 # 1 -> end marker size
    frames = []
    for offset in range(0, len(msg.body), max_size):
        payload = msg.body[offset:offset + max_size]
        header = frame_header.pack('\x03', ch.channel_id, len(payload))
        frames.append('%s%s%s' % (header, payload, '\xCE'))
    return frames

HEARTBEAT = '\x08\x00\x00\x00\x00\x00\x00\xCE'

class FrameHandler(object):

    def __init__(self, connection):
        self.conn = connection
        self._method_queue = []
        self._pending_meth = None
        self._pending_cb = None
        self._msg_builder = None

    @property
    def message(self):
        return self._msg_builder.get_msg()

    @property
    def callback(self):
        return self._pending_cb

    def invoke_callback(self, *args, **kargs):
        if self._pending_cb:
            try:
                self._pending_cb(*args, **kargs)
            except Exception:
                logger.error('Error in callback for %s', self._pending_meth,
                                                         exc_info=True)
            self._pending_cb = None

    def process_frame(self, frame):
        processor = getattr(self, 'process_'+frame.frame_type)
        processor(frame.payload)

    def process_method(self, method):
        if method._content:
            self._msg_builder = MessageBuilder(content_method=method)
        else:
            self._msg_builder = None
            self.handle_method(method)

    def process_content_header(self, ch):
        self._msg_builder.add_content_header(ch)

    def process_content_body(self, cb):
        # FIXME better error checking
        self._msg_builder.add_content_body(cb)
        if self._msg_builder.msg_complete:
            self.handle_method(self._msg_builder.content_method)

    def process_heartbeat(self, hb):
        self.conn.stream.write(HEARTBEAT)

    def handle_method(self, method):
        pending_meth = self._pending_meth
        if hasattr(method, 'handle'):
            try:
                method.handle(self)
            except AmqpError:
                logger.error('Error while handling %s', method, exc_info=True)
                self.reset()
                return
        if pending_meth and method._name.startswith(pending_meth._name):
            self.invoke_callback()
            self._flush()

    def send_method(self, method, callback=None, message=None):
        self._method_queue.append( (method, callback, message) )
        if not self._pending_meth:
            self._flush()

    def _flush(self):
        self._pending_cb = None
        self._pending_meth = None
        while self._pending_meth is None and self._method_queue:
            method, callback, msg = self._method_queue.pop(0)
            self.write_method(method)
            if msg:
                self.write_msg(msg)
            if method._sync:
                self._pending_meth = method
                self._pending_cb = callback
            else:
                if callback is not None:
                    callback()

    def write_method(self, method):
        f = from_method(method, self)
        self.conn.stream.write(f)

    def write_msg(self, msg):
        frames = []
        frames.append(content_header_from_msg(msg, self))
        frames.extend(body_frames_from_msg(msg, self))
        self.conn.stream.write(''.join(frames))

    def reset(self):
        self.status = status.CLOSED
        self._method_queue = []
        self._pending_meth = None
        self._pending_cb = None
        self._msg_builder = None

########NEW FILE########
__FILENAME__ = heartbeat
import time

from stormed.frame import status

class HeartbeatMonitor(object):

    def __init__(self, connection):
        self.conn = connection
        self.timeout = connection.heartbeat * 2
        self.when = None

    def start(self):
        self._schedule()

    def _schedule(self):
        when = time.time() + self.timeout
        self.conn.io_loop.add_timeout(when, self._check)
        self.when = when

    def _check(self):
        if self.conn.status != status.CLOSED:
            last_received = self.conn.last_received_frame
            if not last_received or (self.when - last_received) > self.timeout:
                self.conn.close_stream()
                if self.conn.on_disconnect:
                    self.conn.on_disconnect()
            else:
                self._schedule()

########NEW FILE########
__FILENAME__ = message
from stormed.util import WithFields
from stormed.method import basic

class Message(WithFields):

    """An AMQP Message

    The body parameter represents the message content. If the parameter
    is a unicode object, it is encoded to UTF8.

    The optional properties are those defined in the AMQP standard
    (see stormed.method.codegen.basic.properties)

    When the message is received from the server the rx_data attribute
    contains the AMQP method instance (e.g. basic.GetOk, basic.Deliver).
    This instance carries the server metadata (e.g. the redelivered bit).

    A message received from the server can be acknowledged o rejected
    with the Message.ack() and Message.reject() methods if required.
    """

    _fields = basic.properties

    def __init__(self, body, **properties):
        self.body = body
        if isinstance(body, unicode):
            encoding = properties.setdefault('content_encoding', 'utf8')
            self.body = body.encode(encoding)
        else:
            properties.setdefault('content_type', 'application/octet-stream')
        self.rx_data = None
        self.rx_channel = None
        super(Message, self).__init__(**properties)

    def ack(self, multiple=False):
        """acknowledge the message"""
        if self.rx_channel is None:
            raise ValueError('cannot ack an unreceived message')
        method = basic.Ack(delivery_tag=self.rx_data.delivery_tag,
                           multiple=multiple)
        self.rx_channel.send_method(method)

    def reject(self, requeue=True):
        """reject the message"""
        if self.rx_channel is None:
            raise ValueError('cannot reject an unreceived message')
        method = basic.Reject(delivery_tag=self.rx_data.delivery_tag,
                              requeue=requeue)
        self.rx_channel.send_method(method)


class ContentHeader(object):

    def __init__(self, size, properties):
        self.size = size
        self.properties = properties


class MessageBuilder(object):

    def __init__(self, content_method):
        self.content_method = content_method
        self.content_header = None
        self.chunks = []
        self.received_size = 0

    def add_content_header(self, content_header):
        self.content_header = content_header

    def add_content_body(self, content_body):
        self.chunks.append(content_body)
        self.received_size += len(content_body)

    @property
    def msg_complete(self):
        return self.content_header.size == self.received_size

    def get_msg(self):
        assert self.msg_complete
        body = ''.join(self.chunks)
        msg = Message(body, **self.content_header.properties)
        msg.rx_data = self.content_method
        return msg

########NEW FILE########
__FILENAME__ = basic
from stormed.util import add_method, logger
from stormed.method.codegen.basic import *

@add_method(GetOk)
def handle(self, ch):
    msg = ch.message
    msg.rx_channel = ch
    ch.invoke_callback(msg)

@add_method(GetEmpty)
def handle(self, ch):
    ch.invoke_callback(None)

@add_method(ConsumeOk)
def handle(self, ch):
    ch.invoke_callback(self.consumer_tag)

@add_method(CancelOk)
def handle(self, ch):
    del ch.consumers[self.consumer_tag]

@add_method(Deliver)
def handle(self, ch):
    msg = ch.message
    msg.rx_channel = ch
    ch.consumers[self.consumer_tag].callback(msg)

@add_method(Return)
def handle(self, ch):
    msg = ch.message
    msg.rx_channel = ch
    if ch.on_return:
        try:
            ch.on_return(msg)
        except Exception:
            logger.error('ERROR in on_return() callback', exc_info=True)

########NEW FILE########
__FILENAME__ = channel
from stormed.util import add_method, Enum, logger
from stormed.serialization import table2str
from stormed.frame import status
from stormed.method.codegen.channel import *
from stormed.method.codegen import id2class
from stormed.method.constant import id2constant

@add_method(OpenOk)
def handle(self, channel):
    channel.status = status.OPENED

@add_method(CloseOk)
def handle(self, channel):
    channel.status = status.CLOSED

class ChannelError(object):

    def __init__(self, reply_code, reply_text, method):
        self.reply_code = reply_code
        self.reply_text = reply_text
        self.method = method

@add_method(Close)
def handle(self, channel):
    try:
        mod = id2class[self.class_id]
        method = getattr(mod, 'id2method')[self.method_id]
    except:
        method = None
        raise
    channel.reset()
    error_code = id2constant.get(self.reply_code, '')
    logger.warn('Soft Error. channel=%r code=%r. %s', channel.channel_id,
                                                      error_code,
                                                      self.reply_text)
    if channel.on_error:
        try:
            channel.on_error(ChannelError(error_code, self.reply_text, method))
        except Exception:
            logger.error('ERROR in on_error() callback for channel %d',
                                             channel.channel_id, exc_info=True)

@add_method(Flow)
def handle(self, channel):
    channel.flow_stopped = not self.active
    self.send_method(FlowOk(active=self.active))

########NEW FILE########
__FILENAME__ = access

from stormed.util import WithFields

class Request(WithFields):

    _name      = "access.request"
    _class_id  = 30
    _method_id = 10
    _sync      = True
    _content   = False
    _fields    = [
        ('realm'             , 'shortstr'),
        ('exclusive'         , 'bit'),
        ('passive'           , 'bit'),
        ('active'            , 'bit'),
        ('write'             , 'bit'),
        ('read'              , 'bit'),
    ]

class RequestOk(WithFields):

    _name      = "access.request-ok"
    _class_id  = 30
    _method_id = 11
    _sync      = False
    _content   = False
    _fields    = [
        ('ticket'            , 'short'),
    ]


id2method = {
    10: Request,
    11: RequestOk,
}

########NEW FILE########
__FILENAME__ = basic

from stormed.util import WithFields

properties = [
        ('content_type'      , 'shortstr'),
        ('content_encoding'  , 'shortstr'),
        ('headers'           , 'table'),
        ('delivery_mode'     , 'octet'),
        ('priority'          , 'octet'),
        ('correlation_id'    , 'shortstr'),
        ('reply_to'          , 'shortstr'),
        ('expiration'        , 'shortstr'),
        ('message_id'        , 'shortstr'),
        ('timestamp'         , 'timestamp'),
        ('type'              , 'shortstr'),
        ('user_id'           , 'shortstr'),
        ('app_id'            , 'shortstr'),
        ('cluster_id'        , 'shortstr'),

]

class Qos(WithFields):

    _name      = "basic.qos"
    _class_id  = 60
    _method_id = 10
    _sync      = True
    _content   = False
    _fields    = [
        ('prefetch_size'     , 'long'),
        ('prefetch_count'    , 'short'),
        ('_global'           , 'bit'),
    ]

class QosOk(WithFields):

    _name      = "basic.qos-ok"
    _class_id  = 60
    _method_id = 11
    _sync      = False
    _content   = False
    _fields    = [
    ]

class Consume(WithFields):

    _name      = "basic.consume"
    _class_id  = 60
    _method_id = 20
    _sync      = True
    _content   = False
    _fields    = [
        ('ticket'            , 'short'),
        ('queue'             , 'shortstr'),
        ('consumer_tag'      , 'shortstr'),
        ('no_local'          , 'bit'),
        ('no_ack'            , 'bit'),
        ('exclusive'         , 'bit'),
        ('nowait'            , 'bit'),
        ('arguments'         , 'table'),
    ]

class ConsumeOk(WithFields):

    _name      = "basic.consume-ok"
    _class_id  = 60
    _method_id = 21
    _sync      = False
    _content   = False
    _fields    = [
        ('consumer_tag'      , 'shortstr'),
    ]

class Cancel(WithFields):

    _name      = "basic.cancel"
    _class_id  = 60
    _method_id = 30
    _sync      = True
    _content   = False
    _fields    = [
        ('consumer_tag'      , 'shortstr'),
        ('nowait'            , 'bit'),
    ]

class CancelOk(WithFields):

    _name      = "basic.cancel-ok"
    _class_id  = 60
    _method_id = 31
    _sync      = False
    _content   = False
    _fields    = [
        ('consumer_tag'      , 'shortstr'),
    ]

class Publish(WithFields):

    _name      = "basic.publish"
    _class_id  = 60
    _method_id = 40
    _sync      = False
    _content   = True
    _fields    = [
        ('ticket'            , 'short'),
        ('exchange'          , 'shortstr'),
        ('routing_key'       , 'shortstr'),
        ('mandatory'         , 'bit'),
        ('immediate'         , 'bit'),
    ]

class Return(WithFields):

    _name      = "basic.return"
    _class_id  = 60
    _method_id = 50
    _sync      = False
    _content   = True
    _fields    = [
        ('reply_code'        , 'short'),
        ('reply_text'        , 'shortstr'),
        ('exchange'          , 'shortstr'),
        ('routing_key'       , 'shortstr'),
    ]

class Deliver(WithFields):

    _name      = "basic.deliver"
    _class_id  = 60
    _method_id = 60
    _sync      = False
    _content   = True
    _fields    = [
        ('consumer_tag'      , 'shortstr'),
        ('delivery_tag'      , 'longlong'),
        ('redelivered'       , 'bit'),
        ('exchange'          , 'shortstr'),
        ('routing_key'       , 'shortstr'),
    ]

class Get(WithFields):

    _name      = "basic.get"
    _class_id  = 60
    _method_id = 70
    _sync      = True
    _content   = False
    _fields    = [
        ('ticket'            , 'short'),
        ('queue'             , 'shortstr'),
        ('no_ack'            , 'bit'),
    ]

class GetOk(WithFields):

    _name      = "basic.get-ok"
    _class_id  = 60
    _method_id = 71
    _sync      = False
    _content   = True
    _fields    = [
        ('delivery_tag'      , 'longlong'),
        ('redelivered'       , 'bit'),
        ('exchange'          , 'shortstr'),
        ('routing_key'       , 'shortstr'),
        ('message_count'     , 'long'),
    ]

class GetEmpty(WithFields):

    _name      = "basic.get-empty"
    _class_id  = 60
    _method_id = 72
    _sync      = False
    _content   = False
    _fields    = [
        ('cluster_id'        , 'shortstr'),
    ]

class Ack(WithFields):

    _name      = "basic.ack"
    _class_id  = 60
    _method_id = 80
    _sync      = False
    _content   = False
    _fields    = [
        ('delivery_tag'      , 'longlong'),
        ('multiple'          , 'bit'),
    ]

class Reject(WithFields):

    _name      = "basic.reject"
    _class_id  = 60
    _method_id = 90
    _sync      = False
    _content   = False
    _fields    = [
        ('delivery_tag'      , 'longlong'),
        ('requeue'           , 'bit'),
    ]

class RecoverAsync(WithFields):

    _name      = "basic.recover-async"
    _class_id  = 60
    _method_id = 100
    _sync      = False
    _content   = False
    _fields    = [
        ('requeue'           , 'bit'),
    ]

class Recover(WithFields):

    _name      = "basic.recover"
    _class_id  = 60
    _method_id = 110
    _sync      = True
    _content   = False
    _fields    = [
        ('requeue'           , 'bit'),
    ]

class RecoverOk(WithFields):

    _name      = "basic.recover-ok"
    _class_id  = 60
    _method_id = 111
    _sync      = False
    _content   = False
    _fields    = [
    ]


id2method = {
    10: Qos,
    11: QosOk,
    20: Consume,
    21: ConsumeOk,
    30: Cancel,
    31: CancelOk,
    40: Publish,
    50: Return,
    60: Deliver,
    70: Get,
    71: GetOk,
    72: GetEmpty,
    80: Ack,
    90: Reject,
    100: RecoverAsync,
    110: Recover,
    111: RecoverOk,
}

########NEW FILE########
__FILENAME__ = channel

from stormed.util import WithFields

class Open(WithFields):

    _name      = "channel.open"
    _class_id  = 20
    _method_id = 10
    _sync      = True
    _content   = False
    _fields    = [
        ('out_of_band'       , 'shortstr'),
    ]

class OpenOk(WithFields):

    _name      = "channel.open-ok"
    _class_id  = 20
    _method_id = 11
    _sync      = False
    _content   = False
    _fields    = [
        ('channel_id'        , 'longstr'),
    ]

class Flow(WithFields):

    _name      = "channel.flow"
    _class_id  = 20
    _method_id = 20
    _sync      = True
    _content   = False
    _fields    = [
        ('active'            , 'bit'),
    ]

class FlowOk(WithFields):

    _name      = "channel.flow-ok"
    _class_id  = 20
    _method_id = 21
    _sync      = False
    _content   = False
    _fields    = [
        ('active'            , 'bit'),
    ]

class Close(WithFields):

    _name      = "channel.close"
    _class_id  = 20
    _method_id = 40
    _sync      = True
    _content   = False
    _fields    = [
        ('reply_code'        , 'short'),
        ('reply_text'        , 'shortstr'),
        ('class_id'          , 'short'),
        ('method_id'         , 'short'),
    ]

class CloseOk(WithFields):

    _name      = "channel.close-ok"
    _class_id  = 20
    _method_id = 41
    _sync      = False
    _content   = False
    _fields    = [
    ]


id2method = {
    10: Open,
    11: OpenOk,
    20: Flow,
    21: FlowOk,
    40: Close,
    41: CloseOk,
}

########NEW FILE########
__FILENAME__ = connection

from stormed.util import WithFields

class Start(WithFields):

    _name      = "connection.start"
    _class_id  = 10
    _method_id = 10
    _sync      = True
    _content   = False
    _fields    = [
        ('version_major'     , 'octet'),
        ('version_minor'     , 'octet'),
        ('server_properties' , 'table'),
        ('mechanisms'        , 'longstr'),
        ('locales'           , 'longstr'),
    ]

class StartOk(WithFields):

    _name      = "connection.start-ok"
    _class_id  = 10
    _method_id = 11
    _sync      = False
    _content   = False
    _fields    = [
        ('client_properties' , 'table'),
        ('mechanism'         , 'shortstr'),
        ('response'          , 'longstr'),
        ('locale'            , 'shortstr'),
    ]

class Secure(WithFields):

    _name      = "connection.secure"
    _class_id  = 10
    _method_id = 20
    _sync      = True
    _content   = False
    _fields    = [
        ('challenge'         , 'longstr'),
    ]

class SecureOk(WithFields):

    _name      = "connection.secure-ok"
    _class_id  = 10
    _method_id = 21
    _sync      = False
    _content   = False
    _fields    = [
        ('response'          , 'longstr'),
    ]

class Tune(WithFields):

    _name      = "connection.tune"
    _class_id  = 10
    _method_id = 30
    _sync      = True
    _content   = False
    _fields    = [
        ('channel_max'       , 'short'),
        ('frame_max'         , 'long'),
        ('heartbeat'         , 'short'),
    ]

class TuneOk(WithFields):

    _name      = "connection.tune-ok"
    _class_id  = 10
    _method_id = 31
    _sync      = False
    _content   = False
    _fields    = [
        ('channel_max'       , 'short'),
        ('frame_max'         , 'long'),
        ('heartbeat'         , 'short'),
    ]

class Open(WithFields):

    _name      = "connection.open"
    _class_id  = 10
    _method_id = 40
    _sync      = True
    _content   = False
    _fields    = [
        ('virtual_host'      , 'shortstr'),
        ('capabilities'      , 'shortstr'),
        ('insist'            , 'bit'),
    ]

class OpenOk(WithFields):

    _name      = "connection.open-ok"
    _class_id  = 10
    _method_id = 41
    _sync      = False
    _content   = False
    _fields    = [
        ('known_hosts'       , 'shortstr'),
    ]

class Close(WithFields):

    _name      = "connection.close"
    _class_id  = 10
    _method_id = 50
    _sync      = True
    _content   = False
    _fields    = [
        ('reply_code'        , 'short'),
        ('reply_text'        , 'shortstr'),
        ('class_id'          , 'short'),
        ('method_id'         , 'short'),
    ]

class CloseOk(WithFields):

    _name      = "connection.close-ok"
    _class_id  = 10
    _method_id = 51
    _sync      = False
    _content   = False
    _fields    = [
    ]


id2method = {
    10: Start,
    11: StartOk,
    20: Secure,
    21: SecureOk,
    30: Tune,
    31: TuneOk,
    40: Open,
    41: OpenOk,
    50: Close,
    51: CloseOk,
}

########NEW FILE########
__FILENAME__ = exchange

from stormed.util import WithFields

class Declare(WithFields):

    _name      = "exchange.declare"
    _class_id  = 40
    _method_id = 10
    _sync      = True
    _content   = False
    _fields    = [
        ('ticket'            , 'short'),
        ('exchange'          , 'shortstr'),
        ('type'              , 'shortstr'),
        ('passive'           , 'bit'),
        ('durable'           , 'bit'),
        ('auto_delete'       , 'bit'),
        ('internal'          , 'bit'),
        ('nowait'            , 'bit'),
        ('arguments'         , 'table'),
    ]

class DeclareOk(WithFields):

    _name      = "exchange.declare-ok"
    _class_id  = 40
    _method_id = 11
    _sync      = False
    _content   = False
    _fields    = [
    ]

class Delete(WithFields):

    _name      = "exchange.delete"
    _class_id  = 40
    _method_id = 20
    _sync      = True
    _content   = False
    _fields    = [
        ('ticket'            , 'short'),
        ('exchange'          , 'shortstr'),
        ('if_unused'         , 'bit'),
        ('nowait'            , 'bit'),
    ]

class DeleteOk(WithFields):

    _name      = "exchange.delete-ok"
    _class_id  = 40
    _method_id = 21
    _sync      = False
    _content   = False
    _fields    = [
    ]

class Bind(WithFields):

    _name      = "exchange.bind"
    _class_id  = 40
    _method_id = 30
    _sync      = True
    _content   = False
    _fields    = [
        ('ticket'            , 'short'),
        ('destination'       , 'shortstr'),
        ('source'            , 'shortstr'),
        ('routing_key'       , 'shortstr'),
        ('nowait'            , 'bit'),
        ('arguments'         , 'table'),
    ]

class BindOk(WithFields):

    _name      = "exchange.bind-ok"
    _class_id  = 40
    _method_id = 31
    _sync      = False
    _content   = False
    _fields    = [
    ]

class Unbind(WithFields):

    _name      = "exchange.unbind"
    _class_id  = 40
    _method_id = 40
    _sync      = True
    _content   = False
    _fields    = [
        ('ticket'            , 'short'),
        ('destination'       , 'shortstr'),
        ('source'            , 'shortstr'),
        ('routing_key'       , 'shortstr'),
        ('nowait'            , 'bit'),
        ('arguments'         , 'table'),
    ]

class UnbindOk(WithFields):

    _name      = "exchange.unbind-ok"
    _class_id  = 40
    _method_id = 51
    _sync      = False
    _content   = False
    _fields    = [
    ]


id2method = {
    10: Declare,
    11: DeclareOk,
    20: Delete,
    21: DeleteOk,
    30: Bind,
    31: BindOk,
    40: Unbind,
    51: UnbindOk,
}

########NEW FILE########
__FILENAME__ = queue

from stormed.util import WithFields

class Declare(WithFields):

    _name      = "queue.declare"
    _class_id  = 50
    _method_id = 10
    _sync      = True
    _content   = False
    _fields    = [
        ('ticket'            , 'short'),
        ('queue'             , 'shortstr'),
        ('passive'           , 'bit'),
        ('durable'           , 'bit'),
        ('exclusive'         , 'bit'),
        ('auto_delete'       , 'bit'),
        ('nowait'            , 'bit'),
        ('arguments'         , 'table'),
    ]

class DeclareOk(WithFields):

    _name      = "queue.declare-ok"
    _class_id  = 50
    _method_id = 11
    _sync      = False
    _content   = False
    _fields    = [
        ('queue'             , 'shortstr'),
        ('message_count'     , 'long'),
        ('consumer_count'    , 'long'),
    ]

class Bind(WithFields):

    _name      = "queue.bind"
    _class_id  = 50
    _method_id = 20
    _sync      = True
    _content   = False
    _fields    = [
        ('ticket'            , 'short'),
        ('queue'             , 'shortstr'),
        ('exchange'          , 'shortstr'),
        ('routing_key'       , 'shortstr'),
        ('nowait'            , 'bit'),
        ('arguments'         , 'table'),
    ]

class BindOk(WithFields):

    _name      = "queue.bind-ok"
    _class_id  = 50
    _method_id = 21
    _sync      = False
    _content   = False
    _fields    = [
    ]

class Purge(WithFields):

    _name      = "queue.purge"
    _class_id  = 50
    _method_id = 30
    _sync      = True
    _content   = False
    _fields    = [
        ('ticket'            , 'short'),
        ('queue'             , 'shortstr'),
        ('nowait'            , 'bit'),
    ]

class PurgeOk(WithFields):

    _name      = "queue.purge-ok"
    _class_id  = 50
    _method_id = 31
    _sync      = False
    _content   = False
    _fields    = [
        ('message_count'     , 'long'),
    ]

class Delete(WithFields):

    _name      = "queue.delete"
    _class_id  = 50
    _method_id = 40
    _sync      = True
    _content   = False
    _fields    = [
        ('ticket'            , 'short'),
        ('queue'             , 'shortstr'),
        ('if_unused'         , 'bit'),
        ('if_empty'          , 'bit'),
        ('nowait'            , 'bit'),
    ]

class DeleteOk(WithFields):

    _name      = "queue.delete-ok"
    _class_id  = 50
    _method_id = 41
    _sync      = False
    _content   = False
    _fields    = [
        ('message_count'     , 'long'),
    ]

class Unbind(WithFields):

    _name      = "queue.unbind"
    _class_id  = 50
    _method_id = 50
    _sync      = True
    _content   = False
    _fields    = [
        ('ticket'            , 'short'),
        ('queue'             , 'shortstr'),
        ('exchange'          , 'shortstr'),
        ('routing_key'       , 'shortstr'),
        ('arguments'         , 'table'),
    ]

class UnbindOk(WithFields):

    _name      = "queue.unbind-ok"
    _class_id  = 50
    _method_id = 51
    _sync      = False
    _content   = False
    _fields    = [
    ]


id2method = {
    10: Declare,
    11: DeclareOk,
    20: Bind,
    21: BindOk,
    30: Purge,
    31: PurgeOk,
    40: Delete,
    41: DeleteOk,
    50: Unbind,
    51: UnbindOk,
}

########NEW FILE########
__FILENAME__ = build
#! /usr/bin/env python

import json
import os.path
from keyword import iskeyword

codegen_dir = os.path.join(os.path.dirname(__file__), '..')

json_source = os.path.join(os.path.dirname(__file__),
                           'amqp-rabbitmq-0.9.1.json')

def gen_constant(specs):
    constants_filename = os.path.join(codegen_dir, '..', 'constant.py')
    fout = open(constants_filename, 'w')
    for c in specs['constants']:
        c['name'] = fix_name(c['name'])
        template = '%(name)-20s = %(value)r %(comment)s\n'
        c.update(comment = '# %(class)s' % c if 'class' in c else '')
        fout.write(template % c)
    fout.write('\nid2constant = {\n')
    for c in specs['constants']:
        c['name'] = fix_name(c['name'])
        template = '    %(value)4r: "%(name)s",\n'
        fout.write(template % c)
    fout.write('}\n')
        

properties_template = "properties = [\n%s\n]\n\n"

def gen_properties(properties):
    if not properties:
        return ""
    prop_s = [ "        (%-20r, %r),\n" % (fix_name(p['name']),
                                           str(p['type']))
               for p in properties ]
    return properties_template % (''.join(prop_s))
        

file_template = \
"""
from stormed.util import WithFields

%s%s

id2method = {
%s
}
"""

method_template = \
"""class %(klass_name)s(WithFields):

    _name      = "%(class_name)s.%(method_name)s"
    _class_id  = %(class_id)d
    _method_id = %(method_id)d
    _sync      = %(sync)s
    _content   = %(content)s
    _fields    = [%(fields)s
    ]
"""

def gen_methods(specs):
    domains = dict( (k,v) for k,v in specs['domains'] )
    for c in specs['classes']:
        class_filename = os.path.join(codegen_dir, '%s.py' % c['name'])
        method_classes = []
        id2method_entries = []
        for m in c['methods']:
            fields = []
            for f in m['arguments']:
                typ = f['type'] if 'type' in f else domains[f['domain']]
                fname = fix_name(f['name'])
                fields.append("\n        (%-20r, %r)," % (fname, str(typ)))
            klass_name = _camel_case(m['name'])
            method_classes.append(method_template % dict(
                klass_name  = klass_name,
                class_name  = c['name'],
                method_name = m['name'],
                class_id    = c['id'],
                method_id   = m['id'],
                sync        = m.get('synchronous', False),
                content     = m.get('content', False),
                fields      = ''.join(fields),
            ))
            id2method_entries.append('    %-2d: %s,' % (m['id'], klass_name))

        properties = gen_properties(c.get('properties', []))
        s = file_template % (properties,
                             '\n'.join(method_classes),
                             '\n'.join(id2method_entries))
        fout = open(class_filename, 'w')
        fout.write(s)
        fout.close()

init_template = \
"""%s

id2class = {
%s
}
"""

def gen_classes(specs):
    init_filename = os.path.join(codegen_dir, '__init__.py')
    imports = []
    id2class_entries = []
    for c in specs['classes']:
        imports.append('from stormed.method.codegen import %s' % c['name'])
        id2class_entries.append('    %-2d: %s,' % (c['id'], c['name']))
    
    s = init_template % ('\n'.join(imports),
                         '\n'.join(id2class_entries))
    fout = open(init_filename, 'w')
    fout.write(s)
    fout.close()

def main():
    specs = json.load(open(json_source))
    gen_constant(specs)
    gen_methods(specs)
    gen_classes(specs)

def _camel_case(s):
    return s.title().replace('-', '')

def fix_name(s):
    s = s.replace(' ','_').replace('-','_').encode('ascii')
    return "_"+s if iskeyword(s) else s
        

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = tx

from stormed.util import WithFields

class Select(WithFields):

    _name      = "tx.select"
    _class_id  = 90
    _method_id = 10
    _sync      = True
    _content   = False
    _fields    = [
    ]

class SelectOk(WithFields):

    _name      = "tx.select-ok"
    _class_id  = 90
    _method_id = 11
    _sync      = False
    _content   = False
    _fields    = [
    ]

class Commit(WithFields):

    _name      = "tx.commit"
    _class_id  = 90
    _method_id = 20
    _sync      = True
    _content   = False
    _fields    = [
    ]

class CommitOk(WithFields):

    _name      = "tx.commit-ok"
    _class_id  = 90
    _method_id = 21
    _sync      = False
    _content   = False
    _fields    = [
    ]

class Rollback(WithFields):

    _name      = "tx.rollback"
    _class_id  = 90
    _method_id = 30
    _sync      = True
    _content   = False
    _fields    = [
    ]

class RollbackOk(WithFields):

    _name      = "tx.rollback-ok"
    _class_id  = 90
    _method_id = 31
    _sync      = False
    _content   = False
    _fields    = [
    ]


id2method = {
    10: Select,
    11: SelectOk,
    20: Commit,
    21: CommitOk,
    30: Rollback,
    31: RollbackOk,
}

########NEW FILE########
__FILENAME__ = connection
from stormed.util import add_method, AmqpError, logger
from stormed.serialization import table2str
from stormed.heartbeat import HeartbeatMonitor
from stormed.frame import status
from stormed.method.codegen import id2class
from stormed.method.constant import id2constant
from stormed.method.codegen.connection import *

@add_method(Start)
def handle(self, conn):
    if 'AMQPLAIN' not in self.mechanisms.split(' '):
        raise AmqpError("'AMQPLAIN' not in mechanisms")
    if 'en_US' not in self.locales.split(' '):
        raise AmqpError("'en_US' not in locales")
    response = table2str(dict(LOGIN    = conn.username,
                              PASSWORD = conn.password))
    client_properties = {'client': 'stormed-amqp'}

    start_ok = StartOk(client_properties=client_properties,
                       mechanism='AMQPLAIN', response=response,
                       locale='en_US')
    conn.write_method(start_ok)

@add_method(Tune)
def handle(self, conn):
    conn.frame_max = self.frame_max or 2**16
    tune_ok = TuneOk(frame_max   = 2**16,
                     channel_max = self.channel_max,
                     heartbeat   = conn.heartbeat)
    conn.write_method(tune_ok)
    _open = Open(virtual_host = conn.vhost,
                 capabilities = '',
                 insist       = 0)
    conn.write_method(_open)

@add_method(OpenOk)
def handle(self, conn):
    conn.status = status.OPENED
    if conn.heartbeat:
        HeartbeatMonitor(conn).start()
    try:
        conn.on_connect()
    except Exception:
        logger.error('ERROR in on_connect() callback', exc_info=True)

@add_method(CloseOk)
def handle(self, conn):
    conn.invoke_callback()
    conn.reset()

class ConnectionError(object):

    def __init__(self, reply_code, reply_text, method):
        self.reply_code = reply_code
        self.reply_text = reply_text
        self.method = method

@add_method(Close)
def handle(self, conn):
    try:
        mod = id2class[self.class_id]
        method = getattr(mod, 'id2method')[self.method_id]
    except:
        method = None
    conn.reset()
    error_code = id2constant.get(self.reply_code, '')
    logger.warn('Connection Hard Error. code=%r. %s', error_code,
                                                      self.reply_text)
    if conn.on_error:
        try:
            conn.on_error(ConnectionError(error_code, self.reply_text, method))
        except Exception:
            logger.error('ERROR in on_error() callback', exc_info=True)

########NEW FILE########
__FILENAME__ = constant
FRAME_METHOD         = 1 
FRAME_HEADER         = 2 
FRAME_BODY           = 3 
FRAME_HEARTBEAT      = 8 
FRAME_MIN_SIZE       = 4096 
FRAME_END            = 206 
REPLY_SUCCESS        = 200 
CONTENT_TOO_LARGE    = 311 # soft-error
NO_ROUTE             = 312 # soft-error
NO_CONSUMERS         = 313 # soft-error
ACCESS_REFUSED       = 403 # soft-error
NOT_FOUND            = 404 # soft-error
RESOURCE_LOCKED      = 405 # soft-error
PRECONDITION_FAILED  = 406 # soft-error
CONNECTION_FORCED    = 320 # hard-error
INVALID_PATH         = 402 # hard-error
FRAME_ERROR          = 501 # hard-error
SYNTAX_ERROR         = 502 # hard-error
COMMAND_INVALID      = 503 # hard-error
CHANNEL_ERROR        = 504 # hard-error
UNEXPECTED_FRAME     = 505 # hard-error
RESOURCE_ERROR       = 506 # hard-error
NOT_ALLOWED          = 530 # hard-error
NOT_IMPLEMENTED      = 540 # hard-error
INTERNAL_ERROR       = 541 # hard-error

id2constant = {
       1: "FRAME_METHOD",
       2: "FRAME_HEADER",
       3: "FRAME_BODY",
       8: "FRAME_HEARTBEAT",
    4096: "FRAME_MIN_SIZE",
     206: "FRAME_END",
     200: "REPLY_SUCCESS",
     311: "CONTENT_TOO_LARGE",
     312: "NO_ROUTE",
     313: "NO_CONSUMERS",
     403: "ACCESS_REFUSED",
     404: "NOT_FOUND",
     405: "RESOURCE_LOCKED",
     406: "PRECONDITION_FAILED",
     320: "CONNECTION_FORCED",
     402: "INVALID_PATH",
     501: "FRAME_ERROR",
     502: "SYNTAX_ERROR",
     503: "COMMAND_INVALID",
     504: "CHANNEL_ERROR",
     505: "UNEXPECTED_FRAME",
     506: "RESOURCE_ERROR",
     530: "NOT_ALLOWED",
     540: "NOT_IMPLEMENTED",
     541: "INTERNAL_ERROR",
}

########NEW FILE########
__FILENAME__ = exchange
from stormed.method.codegen.exchange import *

########NEW FILE########
__FILENAME__ = queue
from stormed.util import add_method
from stormed.method.codegen.queue import *

@add_method(DeclareOk)
def handle(self, ch):
    if ch.callback:
        ch.invoke_callback(self)

@add_method(PurgeOk)
def handle(self, channel):
    channel.invoke_callback(self.message_count)

########NEW FILE########
__FILENAME__ = tx
from stormed.method.codegen.tx import *

########NEW FILE########
__FILENAME__ = serialization
import time
import datetime
from struct import Struct
from itertools import izip

from stormed import method
from stormed.message import ContentHeader, Message

def parse_fields(fields, data):
    vals = []
    offset = 0
    bit_parser = None
    for f in fields:
        if f == 'bit':
            if bit_parser is None:
                bit_parser = BitParser(data[offset])
            vals.append(bit_parser.get_bit())
        else:
            if bit_parser is not None:
                bit_parser = None
                offset += 1
            parser = globals()['parse_%s' % f]
            val, offset = parser(data, offset)
            vals.append(val)

    assert offset + int(bit_parser is not None) == len(data), \
                                                 '%d %d' % (offset, len(data))
    return vals

def dump(o):
    dumped_vals = []
    bit_dumper = None
    for name, typ in o._fields:
        val = getattr(o, name)
        if val is None:
            continue
        if typ == 'bit':
            if bit_dumper is None:
                bit_dumper = BitDumper()
            bit_dumper.add_bit(val)
        else:
            if bit_dumper is not None:
                dumped_vals.append(bit_dumper.get_octet())
                bit_dumper = None
            dumper = globals()['dump_%s' % typ]
            v = dumper(val)
            dumped_vals.append(v)
    if bit_dumper is not None:
        dumped_vals.append(bit_dumper.get_octet())
    return ''.join(dumped_vals)

#TODO MOVE TO frame.py
method_header = Struct('!HH')
def parse_method(data):
    class_id, method_id = method_header.unpack(data[:4])
    mod = method.id2class[class_id]
    inst = getattr(mod, 'id2method')[method_id]()
    names = [ name for name, typ in inst._fields ]
    types = [ typ  for name, typ in inst._fields ]
    vals = parse_fields(types, data[4:])
    for name, val in izip(names, vals):
        setattr(inst, name, val)
    return inst

#TODO MOVE TO frame.py
def dump_method(m):
    header = method_header.pack(m._class_id, m._method_id)
    return '%s%s' % (header, dump(m))

content_header = Struct('!HHQH')
def parse_content_header(data):
    hlen = content_header.size
    class_id, _, msg_size, prop_flags = content_header.unpack(data[:hlen])
    assert class_id == 60 # basic class
    fields = []
    for offset, fspec in zip(range(15, 0, -1), Message._fields):
        if prop_flags & (1 << offset):
            fields.append(fspec)
    names = [ name for name, typ in fields ]
    types = [ typ  for name, typ in fields ]
    prop_vals = parse_fields(types, data[hlen:])
    properties = dict( (k,v) for k,v in zip(names, prop_vals) )
    return ContentHeader(msg_size, properties)

#TODO MOVE TO frame.py
def dump_content_header(msg):
    assert len(msg._fields) <= 15, "prop_flags > 15 not supported"
    prop_flags = 0
    for offset, (fname, ftype) in zip(range(15, 0, -1), msg._fields):
        if getattr(msg, fname) is not None:
            prop_flags |= 1 << offset
    chp = content_header.pack(60, #basic class
                              0,
                              len(msg.body),
                              prop_flags)
    return '%s%s' % (chp, dump(msg))

# --- low level parsing/dumping ---

class BitParser(object):

    def __init__(self, octet):
        self.bit_offset = 0
        self.octet = ord(octet)

    def get_bit(self):
        assert self.bit_offset <= 7, "unpacking more that 8 bits is unsupported"
        bit = self.octet & (1 << self.bit_offset)
        self.bit_offset += 1
        return bool(bit)

class BitDumper(object):

    def __init__(self):
        self.bit_offset = 0
        self.octet = 0

    def add_bit(self, bit):
        assert self.bit_offset <= 7, "packing more that 8 bits is unsupported"
        self.octet |= (1 if bit else 0) << self.bit_offset
        self.bit_offset += 1

    def get_octet(self):
        return chr(self.octet)

def parse_octet(data, offset):
    return ord(data[offset]), offset+1

def dump_octet(i):
    return chr(i)

short = Struct('!H')
def parse_short(data, offset):
    val = short.unpack_from(data, offset)[0]
    return val, offset+2

def dump_short(i):
    return short.pack(i)

_long = Struct('!L')
def parse_long(data, offset):
    val = _long.unpack_from(data, offset)[0]
    return val, offset+4

def dump_long(i):
    return _long.pack(i)

_longlong = Struct('!Q')
def parse_longlong(data, offset):
    val = _longlong.unpack_from(data, offset)[0]
    return val, offset+8

def dump_longlong(i):
    return _longlong.pack(i)

longstr_header = Struct('!L')
def parse_longstr(data, offset):
    l = longstr_header.unpack_from(data, offset)[0]
    val = data[offset+4: offset+4+l]
    return val, offset+4+l

def dump_longstr(s):
    encoded_s = s.encode('utf8')
    return '%s%s' % (longstr_header.pack(len(encoded_s)), encoded_s)

def parse_shortstr(data, offset):
    l = ord(data[offset])
    val = data[offset+1: offset+1+l]
    return val, offset+1+l

def dump_shortstr(s):
    encoded_s = s.encode('utf8')
    return '%s%s' % (chr(len(encoded_s)), encoded_s)

def parse_boolean(data, offset):
    octet, offset = parse_octet(data, offset)
    return bool(octet), offset

def dump_boolean(b):
    if b:
        return chr(1)
    else:
        return chr(0)

def dump_timestamp(dt):
    secs = time.mktime(dt.timetuple())
    return dump_longlong(secs)

def parse_timestamp(data, offset):
    secs, offset = parse_longlong(data, offset)
    dt = datetime.datetime.fromtimestamp(secs)
    return dt, offset

def parse_table(data, offset):
    s, new_offset = parse_longstr(data, offset)
    d = {}
    s_len = len(s)
    offset = 0
    while offset < s_len:
        key, offset = parse_shortstr(s, offset)
        typ = s[offset]
        assert typ in field_type_dict, typ
        val, offset = field_type_dict[typ](s, offset+1)
        d[key] = val
    return d, new_offset

field_type_dict = {
  'F': parse_table,
  's': parse_shortstr,
  'S': parse_longstr,
  't': parse_boolean,
  'T': parse_timestamp,
}

def table2str(d):
    return ''.join([ '%sS%s' % (dump_shortstr(k), dump_longstr(v))
                     for k, v in d.items() ])

def dump_table(d):
    entries = table2str(d)
    return dump_longstr(entries)

########NEW FILE########
__FILENAME__ = util
import logging

logger = logging.getLogger('stormed-amqp')

class AmqpError(Exception): pass

class Enum(object):

    def __init__(self, *names):
        self._names = set(names)

    def __getattr__(self, name):
        if name in self._names:
            return name
        raise AttributeError

class WithFields(object):

    _fields = []

    def __init__(self, **kargs):
        fnames = [ fname for fname, ftype in self._fields ]
        unvalid_kargs = set(kargs.keys()) - set(fnames)
        if unvalid_kargs:
            raise AttributeError('invalid field name/s: %s' % unvalid_kargs)
        for fn in fnames:
            setattr(self, fn, kargs.get(fn))

    def __repr__(self):
        fs = ['%s=%r' % (f, getattr(self,f)) for f, _ in self._fields]
        t = type(self)
        klass = (getattr(self, '_name', None) or
                 '%s.%s' % (t.__module__, t.__name__))
        return '%s(%s)' % (klass, ', '.join(fs))

def add_method(klass):
    def decorator(f):
        setattr(klass, f.__name__, f)
    return decorator

########NEW FILE########
__FILENAME__ = test_channel
import unittest

from tornado import testing

from stormed.connection import Connection
from stormed.channel import Consumer
from stormed.message import Message
from stormed.method import queue
from stormed.frame import status

class TestChannel(testing.AsyncTestCase):

    def test_open(self):
        conn = Connection('localhost', io_loop=self.io_loop)

        def clean_up(**kargs):
            conn.close(self.stop)
    
        def on_connect():
            ch = conn.channel(callback=clean_up)

        conn.connect(on_connect)
        self.wait()

    def test_publish(self):
        conn = Connection('localhost', io_loop=self.io_loop)
        test_msg = Message('test')

        def on_connect():
            ch = conn.channel()
            ch.exchange_declare('test_exchange', durable=False)
            ch.publish(test_msg, exchange='test_exchange', routing_key='test')
            conn.close(self.stop)

        conn.connect(on_connect)
        self.wait()

    def test_queue(self):
        conn = Connection('localhost', io_loop=self.io_loop)

        def on_creation(qinfo):
            assert qinfo.queue == 'test_queue'
            assert qinfo.message_count == 0
            assert qinfo.consumer_count == 0

        def on_connect():
            ch = conn.channel()
            ch.queue_delete('test_queue')
            ch.queue_declare('test_queue', durable=False,
                             callback=on_creation)
            conn.close(self.stop)

        conn.connect(on_connect)
        self.wait()

    def test_get(self):
        conn = Connection('localhost', io_loop=self.io_loop)
        ch = None
        test_msg = Message('test')

        def on_msg(msg):
            global ch
            assert msg.body == 'test'
            msg.ack()
            ch.get('test_queue', on_missing_msg)

        def on_missing_msg(msg):
            assert msg is None
            conn.close(self.stop)

        def on_connect():
            global ch
            ch = conn.channel()
            ch.exchange_declare('test_exchange', durable=False)
            ch.queue_declare('test_queue', durable=False)
            ch.queue_bind('test_queue', 'test_exchange', 'test')
            ch.publish(test_msg, exchange='test_exchange', routing_key='test')
            ch.get('test_queue', on_msg)

        conn.connect(on_connect)
        self.wait()

    def test_consume(self):
        global count
        conn = Connection('localhost', io_loop=self.io_loop)
        test_msg = Message('test')
        count = 0

        def clean_up():
            assert not ch.consumers
            conn.close(self.stop)

        def consume_callback(msg):
            global ch, count, consumer
            count += 1
            assert msg.body == 'test'
            if count == 50:
                consumer.cancel(clean_up)

        def on_connect():
            global ch, consumer
            ch = conn.channel()
            ch.exchange_declare('test_exchange', durable=False)
            ch.queue_declare('test_queue', durable=False)
            ch.queue_bind('test_queue', 'test_exchange', 'test')
            for _ in xrange(50):
                ch.publish(test_msg, exchange='test_exchange',
                                     routing_key='test')
            consumer = Consumer(consume_callback)
            ch.consume('test_queue', consumer, no_ack=True)

        conn.connect(on_connect)
        self.wait()

    def test_channel_error(self):
        
        conn = Connection('localhost', io_loop=self.io_loop)

        def on_connect():
            self.ch = conn.channel()
            self.ch.on_error = on_error
            self.ch.queue_bind('foo', 'bar')

        def on_error(ch_error):
            assert ch_error.method == queue.Bind, ch_error.method
            assert ch_error.reply_code == 'NOT_FOUND'
            assert self.ch.status == status.CLOSED
            conn.close(self.stop)

        conn.connect(on_connect)
        self.wait()

    def test_channel_flow(self):

        conn = Connection('localhost', io_loop=self.io_loop)

        def on_connect():
            self.ch = conn.channel()
            self.ch.flow(active=False, callback=cleanup)

        def cleanup():
            conn.close(self.stop)

        conn.connect(on_connect)
        self.wait()

    def test_purge_queue(self):

        test_msg = Message('test')
        conn = Connection('localhost', io_loop=self.io_loop)

        def on_connect():
            self.ch = conn.channel()
            self.ch.queue_declare('test_purge_queue', auto_delete=True)
            self.ch.exchange_declare('test_purge_exchange', durable=False)
            self.ch.queue_bind(queue='test_purge_queue',
                            exchange='test_purge_exchange')

            self.ch.queue_purge('test_purge_queue')
            for _ in xrange(3):
                self.ch.publish(test_msg, exchange='test_purge_exchange')
            self.ch.queue_purge('test_purge_queue', purged)

        def purged(msg_count):
            assert msg_count==3, msg_count
            conn.close(self.stop)

        conn.connect(on_connect)
        self.wait()

    def test_basic_return(self):
        test_msg = Message('test')
        conn = Connection('localhost', io_loop=self.io_loop)

        def on_connect():
            ch = conn.channel()
            ch.on_return = on_return
            ch.exchange_declare('test_imm', durable=False)
            ch.publish(test_msg, exchange='test_imm', immediate=True)

        def on_return(msg):
            rx = msg.rx_data
            assert rx.reply_code == 313, rx.reply_code  # NO_CONSUMERS
            assert rx.exchange == 'test_imm', rx.exchange_declare
            conn.close(self.stop)

        conn.connect(on_connect)
        self.wait()

    def test_reliable_publishing(self):
        test_msg = Message('test')
        conn = Connection('localhost', io_loop=self.io_loop)

        def on_connect():
            ch = conn.channel()
            ch.exchange_declare('test_imm', durable=False)
            ch.on_error = lambda: None
            ch.select()
            ch.publish(test_msg, exchange='test_imm')
            ch.commit(lambda: conn.close(self.stop))

        conn.connect(on_connect)
        self.wait()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_connection
import time
import unittest

from tornado import testing

from stormed.connection import Connection, status
from stormed.method.connection import Tune
from stormed.heartbeat import HeartbeatMonitor

class TestConnectionHandshake(testing.AsyncTestCase):

    def test_handshake(self):
        conn = Connection('localhost', io_loop=self.io_loop)
        def on_connect():
            self.assertEquals(conn.status, status.OPENED)
            conn.close(self.stop)
        conn.connect(on_connect)
        self.wait()

    def test_heartbeat(self):
        conn = Connection('localhost', heartbeat=1, io_loop=self.io_loop)
        def clean_up():
            conn.status == status.OPENED
            conn.close(self.stop)
        conn.connect(lambda: None)
        self.io_loop.add_timeout(time.time()+4, clean_up)
        self.wait()

    def test_heartbeat_server_disconnected(self):
        conn = Connection('localhost', io_loop=self.io_loop)
        def clean_up():
            conn.status == status.CLOSED
            self.stop()
        conn.on_disconnect = clean_up

        def launch_heartbeat():
            conn.heartbeat=1
            HeartbeatMonitor(conn).start()
        conn.connect(launch_heartbeat)

        self.io_loop.add_timeout(time.time()+3, clean_up)
        self.wait()

    def test_heartbeat_client_disconnected(self):
        conn = Connection('localhost', heartbeat=1, io_loop=self.io_loop)
        conn.process_heartbeat = lambda hb: None
        conn.on_disconnect = self.stop
        conn.connect(lambda: None)
        self.wait()

    def test_conn_error(self):
        conn = Connection('localhost', io_loop=self.io_loop)

        def send_wrong_method():
            tune = Tune(frame_max   = 0,
                        channel_max = 0,
                        heartbeat   = 0)
            conn.send_method(tune, callback=done)

        def done(conn_error):
            assert conn_error.method == Tune, repr(conn_error.method)
            assert conn_error.reply_code == 'CHANNEL_ERROR'
            assert conn.status == status.CLOSED
            self.stop()

        conn.on_error = done
        conn.connect(send_wrong_method)
        self.wait()
        

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_serialization
import unittest
from datetime import datetime

from stormed.util import WithFields
from stormed.serialization import parse_method, dump_method, dump, \
                                  parse_timestamp, dump_timestamp
from stormed.method import connection

connection_start_payload = \
    ('\x00\n\x00\n\x00\t\x00\x00\x00\xfb\x07productS\x00\x00\x00\x08RabbitMQ'
     '\x07versionS\x00\x00\x00\x052.1.1\x08platformS\x00\x00\x00\nErlang/OTP'
     '\tcopyrightS\x00\x00\x00gCopyright (C) 2007-2010 LShift Ltd., Cohesive '
     'Financial Technologies LLC., and Rabbit Technologies Ltd.\x0binformation'
     'S\x00\x00\x005Licensed under the MPL.  See http://www.rabbitmq.com/'
     '\x00\x00\x00\x0ePLAIN AMQPLAIN\x00\x00\x00\x05en_US')

class TestMethodSerialization(unittest.TestCase):

    def test_parse_start(self):
        m = parse_method(connection_start_payload)
        self.assertEquals(m._method_id, 10)
        self.assertEquals(m._class_id,  10)
        self.assertEquals(m.version_major, 0)
        self.assertEquals(m.version_minor, 9)
        self.assertEquals(m.server_properties['version'], '2.1.1')
        self.assertEquals(m.mechanisms, 'PLAIN AMQPLAIN')
        self.assertEquals(m.locales, 'en_US')

    def test_parse_dump_startok(self):
        peer_properties = dict(client="stormed-amqp")
        start_ok = connection.StartOk(client_properties=peer_properties,
                                      mechanism='PLAIN', response='',
                                      locale='en_US')
        data = dump_method(start_ok)
        self.assertEquals(len(data), 48)
        start_ok2 = parse_method(data)
        self.assertEquals(start_ok.mechanism, start_ok2.mechanism)
        self.assertEquals(start_ok.response,  start_ok2.response)
        self.assertEquals(start_ok.locale,    start_ok2.locale)
        self.assertEquals(start_ok.client_properties['client'],
                          start_ok2.client_properties['client'])


class TestBitSerialization(unittest.TestCase):

    def test_dump_bit(self):
        class Bunch(WithFields):
            _fields = [('o1', 'octet'),
                       ('b1', 'bit'),
                       ('b2', 'bit'),
                       ('o2', 'octet')]
        o = Bunch(o1=97, b1 = False, b2 = True, o2=98)
        self.assertEquals(dump(o), 'a\x02b')

    def test_dump_bit_at_end(self):
        class Bunch(WithFields):
            _fields = [('o1', 'octet'),
                       ('b1', 'bit'),
                       ('b2', 'bit'),
                       ('b3', 'bit')]
        o = Bunch(o1=97, b1 = False, b2 = True, b3=True)
        self.assertEquals(dump(o), 'a\x06')

class TestTimeStamp(unittest.TestCase):

    def test_from_to(self):
        dt = datetime(2011, 1, 1, 10, 5)
        dt2, offset = parse_timestamp(dump_timestamp(dt), 0)
        self.assertEquals(dt, dt2)

    def test_from(self):
        parsed_dt, offset = parse_timestamp('\x00\x00\x00\x00M\x1e`p', 0)
        self.assertEquals(offset, 8)
        self.assertEquals(parsed_dt, datetime(2011, 1, 1))

    def test_to(self):
        dt = datetime(2011, 1, 1)
        self.assertEquals(dump_timestamp(dt), '\x00\x00\x00\x00M\x1e`p')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
