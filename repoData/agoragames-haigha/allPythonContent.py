__FILENAME__ = gevent_hello
#!/usr/bin/env python

""" Demonstrates publishing and receiving a message via Haigha library using
gevent-based transport.

Assumes AMQP broker (e.g., RabbitMQ) is running on same machine (localhost)
and is configured with default parameters:
  user: guest
  password: guest
  port: 5672
  vhost: '/'
"""
import sys, os
sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath(".."))

import logging

import gevent
import gevent.event as gevent_event

from haigha.connection import Connection as haigha_Connection
from haigha.message import Message


class HaighaGeventHello(object):
  
  def __init__(self, done_cb):
    self._done_cb = done_cb
    
    # Connect to AMQP broker with default connection and authentication
    # settings (assumes broker is on localhost)
    self._conn = haigha_Connection(transport='gevent',
                                   close_cb=self._connection_closed_cb,
                                   logger=logging.getLogger())
    
    # Start message pump
    self._message_pump_greenlet = gevent.spawn(self._message_pump_greenthread)
    
    # Create message channel
    self._channel = self._conn.channel()
    self._channel.add_close_listener(self._channel_closed_cb)
    
    # Create and configure message exchange and queue
    self._channel.exchange.declare('test_exchange', 'direct')
    self._channel.queue.declare('test_queue', auto_delete=True)
    self._channel.queue.bind('test_queue', 'test_exchange', 'test_routing_key')
    self._channel.basic.consume(queue='test_queue',
                                consumer=self._handle_incoming_messages)
    
    # Publish a message on the channel
    msg = Message('body', application_headers={'hello':'world'})
    print "Publising message: %s" % (msg,)
    self._channel.basic.publish(msg, 'test_exchange', 'test_routing_key')
    return
  
  
  def _message_pump_greenthread(self):
    print "Entering Message Pump"
    try:
      while self._conn is not None:
        # Pump
        self._conn.read_frames()
        
        # Yield to other greenlets so they don't starve
        gevent.sleep()
    finally:
      print "Leaving Message Pump"
      self._done_cb()
    return
  
  
  def _handle_incoming_messages(self, msg):
    print
    print "Received message: %s" % (msg,)
    print
    
    # Initiate graceful closing of the channel
    self._channel.basic.cancel(consumer=self._handle_incoming_messages)
    self._channel.close()
    return
  
  
  def _channel_closed_cb(self, ch):
    print "AMQP channel closed; close-info: %s" % (
      self._channel.close_info,)
    self._channel = None
    
    # Initiate graceful closing of the AMQP broker connection
    self._conn.close()
    return
  
  def _connection_closed_cb(self):
    print "AMQP broker connection closed; close-info: %s" % (
      self._conn.close_info,)
    self._conn = None
    return


def main():
  waiter = gevent_event.AsyncResult()
  
  HaighaGeventHello(waiter.set)
  
  print "Waiting for I/O to complete..."
  waiter.wait()
  
  print "Done!"
  return
  


if __name__ == '__main__':
  logging.basicConfig()
  main()










########NEW FILE########
__FILENAME__ = rpc_client
#!/usr/bin/env python
'''
demostrate how to write a rpc client
'''
import sys, os, uuid, time
sys.path.append(os.path.abspath(".."))

from haigha.connection import Connection
from haigha.message import Message

class FibonacciRpcClient(object):
    def __init__(self):
        self.connection = Connection(host='localhost', heartbeat=None, debug=True)

        self.channel = self.connection.channel()

        result = self.channel.queue.declare(exclusive=True)
        self.callback_queue = result[0]
        print("callback_queue:", self.callback_queue)

        self.channel.basic.consume(self.callback_queue, self.on_response, no_ack=True)

    def on_response(self, msg):
        if msg.properties["correlation_id"] == self.corr_id:
             self.response = msg.body

    def call(self, n):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        msg = Message(str(n), reply_to=self.callback_queue, correlation_id=self.corr_id)
        self.channel.basic.publish(msg, '', 'rpc_queue')
        while self.response is None:
            self.connection.read_frames()
        return int(self.response)

fibonacci_rpc = FibonacciRpcClient()

print " [x] Requesting fib(30)"
response = fibonacci_rpc.call(30)
print " [.] Got %r" % (response,)


########NEW FILE########
__FILENAME__ = rpc_server
#!/usr/bin/env python
'''
demostrate how to write a rpc server
'''
import sys, os, uuid, time
sys.path.append(os.path.abspath(".."))

from haigha.connection import Connection
from haigha.message import Message

connection = Connection(host='localhost', heartbeat=None, debug=True)
channel = connection.channel()
channel.queue.declare(queue='rpc_queue', auto_delete=False)

def fib(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n-1) + fib(n-2)

def on_request(msg):
    n = int(msg.body)

    print " [.] fib(%s)"  % (n,)
    result = fib(n)

    reply_to = msg.properties["reply_to"]
    correlation_id = msg.properties["correlation_id"]
    resp = Message(str(result), correlation_id=correlation_id)
    channel.basic.publish(resp,'',reply_to)

    delivery_info = msg.delivery_info
    channel.basic.ack(delivery_info["delivery_tag"])

channel.basic.qos(prefetch_count=1)
channel.basic.consume('rpc_queue', on_request, no_ack=False)

print " [x] Awaiting RPC requests"
while not channel.closed:
    connection.read_frames()


########NEW FILE########
__FILENAME__ = channel
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from collections import deque

from haigha.classes.protocol_class import ProtocolClass
from haigha.frames.frame import Frame
from haigha.frames.content_frame import ContentFrame
from haigha.frames.header_frame import HeaderFrame
from haigha.exceptions import ChannelError, ChannelClosed, ConnectionClosed

# Defined here so it's easier to test


class SyncWrapper(object):

    def __init__(self, cb):
        self._cb = cb
        self._read = True
        self._result = None

    def __eq__(self, other):
        return other == self._cb or \
            (isinstance(other, SyncWrapper) and other._cb == self._cb)

    def __call__(self, *args, **kwargs):
        self._read = False
        self._result = self._cb(*args, **kwargs)


class Channel(object):

    '''
    Define a channel
    '''

    class InvalidClass(ChannelError):
        '''The method frame referenced an invalid class.  Non-fatal.'''

    class InvalidMethod(ChannelError):
        '''The method frame referenced an invalid method.  Non-fatal.'''

    class Inactive(ChannelError):
        '''
        Tried to send a content frame while the channel was inactive.
        Non-fatal.
        '''

    def __init__(self, connection, channel_id, class_map, **kwargs):
        '''
        Initialize with a handle to the connection and an id. Caller must
        supply a mapping of {class_id:ProtocolClass} which defines what
        classes and methods this channel will support.
        '''
        self._connection = connection
        self._channel_id = channel_id

        self._class_map = {}
        for _id, _class in class_map.iteritems():
            impl = _class(self)
            setattr(self, impl.name, impl)
            self._class_map[_id] = impl

        # Out-bound mix of pending frames and synchronous callbacks
        self._pending_events = deque()

        # Incoming frame buffer
        self._frame_buffer = deque()

        # Listeners for when channel opens
        self._open_listeners = set()

        # Listeners for when channel closes
        self._close_listeners = set()

        # Moving state out of protocol class so that it's accessible even
        # after we've closed and deleted references to the protocol classes.
        # Note though that many of these fields are written to directly
        # from within ChannelClass.
        self._closed = False
        self._close_info = {
            'reply_code': 0,
            'reply_text': 'first connect',
            'class_id': 0,
            'method_id': 0
        }
        self._active = True

        self._synchronous = kwargs.get('synchronous', False)

    @property
    def connection(self):
        return self._connection

    @property
    def channel_id(self):
        return self._channel_id

    @property
    def logger(self):
        '''Return a shared logger handle for the channel.'''
        return self._connection.logger

    @property
    def closed(self):
        '''Return whether this channel has been closed.'''
        return self._closed

    @property
    def close_info(self):
        '''Return dict with information on why this channel is closed.  Will
        return None if the channel is open.'''
        return self._close_info if self._closed else None

    @property
    def active(self):
        '''
        Return True if flow control turned off, False if flow control is on.
        '''
        return self._active

    @property
    def synchronous(self):
        '''
        Return if this channel is acting synchronous, of its own accord or
        because the connection is synchronous.
        '''
        return self._synchronous or self._connection.synchronous

    def add_open_listener(self, listener):
        '''
        Add a listener for open events on this channel. The listener should be
        a callable that can take one argument, the channel that is opened.
        Listeners will not be called in any particular order.
        '''
        self._open_listeners.add(listener)

    def remove_open_listener(self, listener):
        '''
        Remove an open event listener. Will do nothing if the listener is not
        registered.
        '''
        self._open_listeners.discard(listener)

    def _notify_open_listeners(self):
        '''Call all the open listeners.'''
        for listener in self._open_listeners:
            listener(self)

    def add_close_listener(self, listener):
        '''
        Add a listener for close events on this channel. The listener should be
        a callable that can take one argument, the channel that is closed.
        Listeners will not be called in any particular order.
        '''
        self._close_listeners.add(listener)

    def remove_close_listener(self, listener):
        '''
        Remove a close event listener. Will do nothing if the listener is not
        registered.
        '''
        self._close_listeners.discard(listener)

    def _notify_close_listeners(self):
        '''Call all the close listeners.'''
        for listener in self._close_listeners:
            listener(self)

    def open(self):
        '''
        Open this channel.  Routes to channel.open.
        '''
        self.channel.open()

    def close(self, reply_code=0, reply_text='', class_id=0, method_id=0):
        '''
        Close this channel.  Routes to channel.close.
        '''
        # In the off chance that we call this twice. A good example is if
        # there's an error in close listeners and so we're still inside a
        # single call to process_frames, which will try to close this channel
        # if there's an exception.
        if hasattr(self, 'channel'):
            self.channel.close(reply_code, reply_text, class_id, method_id)

    def publish(self, *args, **kwargs):
        '''
        Standard publish.  See basic.publish.
        '''
        self.basic.publish(*args, **kwargs)

    def publish_synchronous(self, *args, **kwargs):
        '''
        Helper for publishing a message using transactions.  If 'cb' keyword
        arg is supplied, will be called when the transaction is committed.
        '''
        cb = kwargs.pop('cb', None)
        self.tx.select()
        self.basic.publish(*args, **kwargs)
        self.tx.commit(cb=cb)

    def dispatch(self, method_frame):
        '''
        Dispatch a method.
        '''
        klass = self._class_map.get(method_frame.class_id)
        if klass:
            klass.dispatch(method_frame)
        else:
            raise Channel.InvalidClass(
                "class %d is not supported on channel %d",
                method_frame.class_id, self.channel_id)

    def buffer_frame(self, frame):
        '''
        Buffer an input frame.  Will append to current list of frames and
        ensure there's a pending event to process the queue.
        '''
        self._frame_buffer.append(frame)

    def process_frames(self):
        '''
        Process the input buffer.
        '''
        while len(self._frame_buffer):
            try:
                # It would make sense to call next_frame, but it's
                # technically faster to repeat the code here.
                frame = self._frame_buffer.popleft()
                self.dispatch(frame)
            except ProtocolClass.FrameUnderflow:
                return
            except (ConnectionClosed, ChannelClosed):
                # Immediately raise if connection or channel is closed
                raise
            except Exception:
                # Spec says that channel should be closed if there's a framing
                # error. Unsure if we can send close if the current exception
                # is transport level (e.g. gevent.GreenletExit)
                try:
                    self.close(500, "Failed to dispatch %s" % (str(frame)))
                finally:
                    raise

    def next_frame(self):
        '''
        Pop the next frame off the input queue. If the queue is empty, will
        return None.
        '''
        if len(self._frame_buffer):
            return self._frame_buffer.popleft()
        return None

    def requeue_frames(self, frames):
        '''
        Requeue a list of frames. Will append to the head of the frame buffer.
        Frames should be in reverse order. Really only used to support
        BasicClass content consumers.
        '''
        self._frame_buffer.extendleft(frames)

    def send_frame(self, frame):
        '''
        Queue a frame for sending.  Will send immediately if there are no
        pending synchronous transactions on this connection.
        '''
        if self.closed:
            if self.close_info and len(self.close_info['reply_text']) > 0:
                raise ChannelClosed(
                    "channel %d is closed: %s : %s",
                    self.channel_id,
                    self.close_info['reply_code'],
                    self.close_info['reply_text'])
            raise ChannelClosed()

        # If there's any pending event at all, then it means that when the
        # current dispatch loop started, all possible frames were flushed
        # and the remaining item(s) starts with a sync callback. After careful
        # consideration, it seems that it's safe to assume the len>0 means to
        # buffer the frame. The other advantage here is
        if not len(self._pending_events):
            if not self._active and \
                    isinstance(frame, (ContentFrame, HeaderFrame)):
                raise Channel.Inactive(
                    "Channel %d flow control activated", self.channel_id)
            self._connection.send_frame(frame)
        else:
            self._pending_events.append(frame)

    def add_synchronous_cb(self, cb):
        '''
        Add an expectation of a callback to release a synchronous transaction.
        '''
        if self.connection.synchronous or self._synchronous:
            wrapper = SyncWrapper(cb)
            self._pending_events.append(wrapper)
            while wrapper._read:
                # Don't check that the channel has been closed until after
                # reading frames, in the case that this is processing a clean
                # channel closed. If there's a protocol error during
                # read_frames, this will loop back around and result in a
                # channel closed exception.
                if self.closed:
                    if self.close_info and \
                            len(self.close_info['reply_text']) > 0:
                        raise ChannelClosed(
                            "channel %d is closed: %s : %s",
                            self.channel_id,
                            self.close_info['reply_code'],
                            self.close_info['reply_text'])
                    raise ChannelClosed()
                self.connection.read_frames()

            return wrapper._result
        else:
            self._pending_events.append(cb)

    def clear_synchronous_cb(self, cb):
        '''
        If the callback is the current expected callback, will clear it off the
        stack.  Else will raise in exception if there's an expectation but this
        doesn't satisfy it.
        '''
        if len(self._pending_events):
            ev = self._pending_events[0]

            # We can't have a strict check using this simple mechanism,
            # because we could be waiting for a synch response while messages
            # are being published. So for now, if it's not in the list, do a
            # check to see if the callback is in the pending list, and if so,
            # then raise, because it means we received stuff out of order.
            # Else just pass it through. Note that this situation could happen
            # on any broker-initiated message.
            if ev == cb:
                self._pending_events.popleft()
                self._flush_pending_events()
                return ev

            elif cb in self._pending_events:
                raise ChannelError(
                    "Expected synchronous callback %s, got %s", ev, cb)
        # Return the passed-in callback by default
        return cb

    def _flush_pending_events(self):
        '''
        Send pending frames that are in the event queue.
        '''
        while len(self._pending_events) and \
                isinstance(self._pending_events[0], Frame):
            self._connection.send_frame(self._pending_events.popleft())

    def _closed_cb(self, final_frame=None):
        '''
        "Private" callback from the ChannelClass when a channel is closed. Only
        called after broker initiated close, or we receive a close_ok. Caller
        has the option to send a final frame, to be used to bypass any
        synchronous or otherwise-pending frames so that the channel can be
        cleanly closed.
        '''
        # delete all pending data and send final frame if thre is one. note
        # that it bypasses send_frame so that even if the closed state is set,
        # the frame is published.
        if final_frame:
            self._connection.send_frame(final_frame)

        try:
            self._notify_close_listeners()
        finally:
            self._pending_events = deque()
            self._frame_buffer = deque()

            # clear out other references for faster cleanup
            for protocol_class in self._class_map.values():
                protocol_class._cleanup()
                delattr(self, protocol_class.name)
            self._connection = None
            self._class_map = None
            self._close_listeners = set()

########NEW FILE########
__FILENAME__ = channel_pool
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from collections import deque


class ChannelPool(object):

    '''
    Manages a pool of channels for transaction-based publishing.  This allows a
    client to use as many channels as are necessary to publish while not
    creating a backlog of transactions that slows throughput and consumes
    memory.

    The pool can accept an optional `size` argument in the ctor, which caps
    the number of channels which the pool will allocate. If no channels are
    available on `publish()`, the message will be locally queued and sent as
    soon as a channel is available. It is recommended that you use the pool
    with a max size, as each channel consumes memory on the broker and it is
    possible to exercise memory limit protection seems on the broker due to
    number of channels.
    '''

    def __init__(self, connection, size=None):
        '''Initialize the channel on a connection.'''
        self._connection = connection
        self._free_channels = set()
        self._size = size
        self._queue = deque()
        self._channels = 0

    def publish(self, *args, **kwargs):
        '''
        Publish a message. Caller can supply an optional callback which will
        be fired when the transaction is committed. Tries very hard to avoid
        closed and inactive channels, but a ChannelError or ConnectionError
        may still be raised.
        '''
        user_cb = kwargs.pop('cb', None)

        # If the first channel we grab is inactive, continue fetching until
        # we get an active channel, then put the inactive channels back in
        # the pool. Try to keep the overhead to a minimum.
        channel = self._get_channel()

        if channel and not channel.active:
            inactive_channels = set()
            while channel and not channel.active:
                inactive_channels.add(channel)
                channel = self._get_channel()
            self._free_channels.update(inactive_channels)

        # When the transaction is committed, add the channel back to the pool
        # and call any user-defined callbacks. If there is anything in queue,
        # pop it and call back to publish(). Only do so if the channel is
        # still active though, because otherwise the message will end up at
        # the back of the queue, breaking the original order.
        def committed():
            self._free_channels.add(channel)
            if channel.active and not channel.closed:
                self._process_queue()
            if user_cb is not None:
                user_cb()

        if channel:
            channel.publish_synchronous(*args, cb=committed, **kwargs)
        else:
            kwargs['cb'] = user_cb
            self._queue.append((args, kwargs))

    def _process_queue(self):
        '''
        If there are any message in the queue, process one of them.
        '''
        if len(self._queue):
            args, kwargs = self._queue.popleft()
            self.publish(*args, **kwargs)

    def _get_channel(self):
        '''
        Fetch a channel from the pool. Will return a new one if necessary. If
        a channel in the free pool is closed, will remove it. Will return None
        if we hit the cap. Will clean up any channels that were published to
        but closed due to error.
        '''
        while len(self._free_channels):
            rval = self._free_channels.pop()
            if not rval.closed:
                return rval
            # don't adjust _channels value because the callback will do that
            # and we don't want to double count it.

        if not self._size or self._channels < self._size:
            rval = self._connection.channel()
            self._channels += 1
            rval.add_close_listener(self._channel_closed_cb)
            return rval

    def _channel_closed_cb(self, channel):
        '''
        Callback when channel closes.
        '''
        self._channels -= 1
        self._process_queue()

########NEW FILE########
__FILENAME__ = basic_class
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from collections import deque

from haigha.message import Message
from haigha.writer import Writer
from haigha.frames.method_frame import MethodFrame
from haigha.frames.header_frame import HeaderFrame
from haigha.frames.content_frame import ContentFrame
from haigha.classes.protocol_class import ProtocolClass


class BasicClass(ProtocolClass):

    '''
    Implements the AMQP Basic class
    '''

    def __init__(self, *args, **kwargs):
        super(BasicClass, self).__init__(*args, **kwargs)
        self.dispatch_map = {
            11: self._recv_qos_ok,
            21: self._recv_consume_ok,
            31: self._recv_cancel_ok,
            50: self._recv_return,
            60: self._recv_deliver,
            71: self._recv_get_response,   # see impl
            72: self._recv_get_response,   # see impl
            111: self._recv_recover_ok,
        }

        self._consumer_tag_id = 0
        self._pending_consumers = deque()
        self._consumer_cb = {}
        self._get_cb = deque()
        self._recover_cb = deque()
        self._cancel_cb = deque()

    @property
    def name(self):
        return 'basic'

    def _cleanup(self):
        '''
        Cleanup all the local data.
        '''
        self._pending_consumers = None
        self._consumer_cb = None
        self._get_cb = None
        self._recover_cb = None
        self._cancel_cb = None
        super(BasicClass, self)._cleanup()

    def _generate_consumer_tag(self):
        '''
        Generate the next consumer tag.

        The consumer tag is local to a channel, so two clients can use the
        same consumer tags.
        '''
        self._consumer_tag_id += 1
        return "channel-%d-%d" % (self.channel_id, self._consumer_tag_id)

    def qos(self, prefetch_size=0, prefetch_count=0, is_global=False):
        '''
        Set QoS on this channel.
        '''
        args = Writer()
        args.write_long(prefetch_size).\
            write_short(prefetch_count).\
            write_bit(is_global)
        self.send_frame(MethodFrame(self.channel_id, 60, 10, args))

        self.channel.add_synchronous_cb(self._recv_qos_ok)

    def _recv_qos_ok(self, _method_frame):
        # No arguments, nothing to do
        pass

    def consume(self, queue, consumer, consumer_tag='', no_local=False,
                no_ack=True, exclusive=False, nowait=True, ticket=None,
                cb=None):
        '''
        Start a queue consumer. If `cb` is supplied, will be called when
        broker confirms that consumer is registered.
        '''
        nowait = nowait and self.allow_nowait() and not cb

        if nowait and consumer_tag == '':
            consumer_tag = self._generate_consumer_tag()

        args = Writer()
        args.write_short(ticket or self.default_ticket).\
            write_shortstr(queue).\
            write_shortstr(consumer_tag).\
            write_bits(no_local, no_ack, exclusive, nowait).\
            write_table({})  # unused according to spec
        self.send_frame(MethodFrame(self.channel_id, 60, 20, args))

        if not nowait:
            self._pending_consumers.append((consumer, cb))
            self.channel.add_synchronous_cb(self._recv_consume_ok)
        else:
            self._consumer_cb[consumer_tag] = consumer

    def _recv_consume_ok(self, method_frame):
        consumer_tag = method_frame.args.read_shortstr()
        consumer, cb = self._pending_consumers.popleft()

        self._consumer_cb[consumer_tag] = consumer
        if cb:
            cb()

    def cancel(self, consumer_tag='', nowait=True, consumer=None, cb=None):
        '''
        Cancel a consumer. Can choose to delete based on a consumer tag or
        the function which is consuming.  If deleting by function, take care
        to only use a consumer once per channel.
        '''
        if consumer:
            for (tag, func) in self._consumer_cb.iteritems():
                if func == consumer:
                    consumer_tag = tag
                    break

        nowait = nowait and self.allow_nowait() and not cb

        args = Writer()
        args.write_shortstr(consumer_tag).\
            write_bit(nowait)
        self.send_frame(MethodFrame(self.channel_id, 60, 30, args))

        if not nowait:
            self._cancel_cb.append(cb)
            self.channel.add_synchronous_cb(self._recv_cancel_ok)
        else:
            try:
                del self._consumer_cb[consumer_tag]
            except KeyError:
                self.logger.warning(
                    'no callback registered for consumer tag " %s "',
                    consumer_tag)

    def _recv_cancel_ok(self, method_frame):
        consumer_tag = method_frame.args.read_shortstr()
        try:
            del self._consumer_cb[consumer_tag]
        except KeyError:
            self.logger.warning(
                'no callback registered for consumer tag " %s "', consumer_tag)

        cb = self._cancel_cb.popleft()
        if cb:
            cb()

    def publish(self, msg, exchange, routing_key, mandatory=False,
                immediate=False, ticket=None):
        '''
        publish a message.
        '''
        args = Writer()
        args.write_short(ticket or self.default_ticket).\
            write_shortstr(exchange).\
            write_shortstr(routing_key).\
            write_bits(mandatory, immediate)

        self.send_frame(MethodFrame(self.channel_id, 60, 40, args))
        self.send_frame(
            HeaderFrame(self.channel_id, 60, 0, len(msg), msg.properties))

        f_max = self.channel.connection.frame_max
        for f in ContentFrame.create_frames(self.channel_id, msg.body, f_max):
            self.send_frame(f)

    def return_msg(self, reply_code, reply_text, exchange, routing_key):
        '''
        Return a failed message.  Not named "return" because python interpreter
        can't deal with that.
        '''
        args = Writer()
        args.write_short(reply_code).\
            write_shortstr(reply_text).\
            write_shortstr(exchange).\
            write_shortstr(routing_key)

        self.send_frame(MethodFrame(self.channel_id, 60, 50, args))

    def _recv_return(self, _method_frame):
        # This seems like the right place to callback that the operation has
        # completed.
        pass

    def _recv_deliver(self, method_frame):
        msg = self._read_msg(method_frame,
                             with_consumer_tag=True, with_message_count=False)

        func = self._consumer_cb.get(msg.delivery_info['consumer_tag'], None)
        if func:
            func(msg)

    def get(self, queue, consumer=None, no_ack=True, ticket=None):
        '''
        Ask to fetch a single message from a queue.  If a consumer is supplied,
        the consumer will be called with either a Message argument, or None if
        there is no message in queue. If a synchronous transport, Message or
        None is returned.
        '''
        args = Writer()
        args.write_short(ticket or self.default_ticket).\
            write_shortstr(queue).\
            write_bit(no_ack)

        self._get_cb.append(consumer)
        self.send_frame(MethodFrame(self.channel_id, 60, 70, args))
        return self.channel.add_synchronous_cb(self._recv_get_response)

    def _recv_get_response(self, method_frame):
        '''
        Handle either get_ok or get_empty. This is a hack because the
        synchronous callback stack is expecting one method to satisfy the
        expectation. To keep that loop as tight as possible, work within
        those constraints. Use of get is not recommended anyway.
        '''
        if method_frame.method_id == 71:
            return self._recv_get_ok(method_frame)
        elif method_frame.method_id == 72:
            return self._recv_get_empty(method_frame)

    def _recv_get_ok(self, method_frame):
        msg = self._read_msg(method_frame,
                             with_consumer_tag=False, with_message_count=True)
        cb = self._get_cb.popleft()
        if cb:
            cb(msg)
        return msg

    def _recv_get_empty(self, _method_frame):
        # On empty, call back with None as the argument so that user code knows
        # it's empty and can take next action
        cb = self._get_cb.popleft()
        if cb:
            cb(None)

    def ack(self, delivery_tag, multiple=False):
        '''
        Acknowledge delivery of a message.  If multiple=True, acknowledge up-to
        and including delivery_tag.
        '''
        args = Writer()
        args.write_longlong(delivery_tag).\
            write_bit(multiple)

        self.send_frame(MethodFrame(self.channel_id, 60, 80, args))

    def reject(self, delivery_tag, requeue=False):
        '''
        Reject a message.
        '''
        args = Writer()
        args.write_longlong(delivery_tag).\
            write_bit(requeue)

        self.send_frame(MethodFrame(self.channel_id, 60, 90, args))

    def recover_async(self, requeue=False):
        '''
        Redeliver all unacknowledged messages on this channel.

        This method is deprecated in favour of the synchronous
        recover/recover-ok
        '''
        args = Writer()
        args.write_bit(requeue)

        self.send_frame(MethodFrame(self.channel_id, 60, 100, args))

    def recover(self, requeue=False, cb=None):
        '''
        Ask server to redeliver all unacknowledged messages.
        '''
        args = Writer()
        args.write_bit(requeue)

        # The XML spec is incorrect; this method is always synchronous
        #  http://lists.rabbitmq.com/pipermail/rabbitmq-discuss/2011-January/010738.html
        self._recover_cb.append(cb)
        self.send_frame(MethodFrame(self.channel_id, 60, 110, args))
        self.channel.add_synchronous_cb(self._recv_recover_ok)

    def _recv_recover_ok(self, _method_frame):
        cb = self._recover_cb.popleft()
        if cb:
            cb()

    def _read_msg(self, method_frame, with_consumer_tag=False,
                  with_message_count=False):
        '''
        Support method to read a Message from the current frame buffer.
        Will return a Message, or re-queue current frames and raise a
        FrameUnderflow. Takes an optional argument on whether to read the
        consumer tag so it can be used for both deliver and get-ok.
        '''
        # No need to assert that is instance of Header or Content frames
        # because failure to access as such will result in exception that
        # channel will pick up and handle accordingly.
        header_frame = self.channel.next_frame()
        if header_frame:
            size = header_frame.size
            body = bytearray()
            rbuf_frames = deque([header_frame, method_frame])

            while len(body) < size:
                content_frame = self.channel.next_frame()
                if content_frame:
                    rbuf_frames.appendleft(content_frame)
                    body.extend(content_frame.payload.buffer())
                else:
                    self.channel.requeue_frames(rbuf_frames)
                    raise self.FrameUnderflow()
        else:
            self.channel.requeue_frames([method_frame])
            raise self.FrameUnderflow()

        if with_consumer_tag:
            consumer_tag = method_frame.args.read_shortstr()
        delivery_tag = method_frame.args.read_longlong()
        redelivered = method_frame.args.read_bit()
        exchange = method_frame.args.read_shortstr()
        routing_key = method_frame.args.read_shortstr()
        if with_message_count:
            message_count = method_frame.args.read_long()

        delivery_info = {
            'channel': self.channel,
            'delivery_tag': delivery_tag,
            'redelivered': redelivered,
            'exchange': exchange,
            'routing_key': routing_key,
        }
        if with_consumer_tag:
            delivery_info['consumer_tag'] = consumer_tag
        if with_message_count:
            delivery_info['message_count'] = message_count

        return Message(body=body, delivery_info=delivery_info,
                       **header_frame.properties)

########NEW FILE########
__FILENAME__ = channel_class
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from haigha.classes.protocol_class import ProtocolClass
from haigha.frames.method_frame import MethodFrame
from haigha.writer import Writer


class ChannelClass(ProtocolClass):

    '''
    Implements the AMQP Channel class
    '''

    def __init__(self, *args, **kwargs):
        super(ChannelClass, self).__init__(*args, **kwargs)
        self.dispatch_map = {
            11: self._recv_open_ok,
            20: self._recv_flow,
            21: self._recv_flow_ok,
            40: self._recv_close,
            41: self._recv_close_ok,
        }
        self._flow_control_cb = None

    @property
    def name(self):
        return 'channel'

    def set_flow_cb(self, cb):
        '''
        Set a callback that will be called when the state of flow control has
        changed. The caller should use closures if they need to receive a
        handle to the channel on which flow control changes.
        '''
        self._flow_control_cb = cb

    def open(self):
        '''
        Open the channel for communication.
        '''
        args = Writer()
        args.write_shortstr('')
        self.send_frame(MethodFrame(self.channel_id, 20, 10, args))
        self.channel.add_synchronous_cb(self._recv_open_ok)

    def _recv_open_ok(self, method_frame):
        '''
        Channel is opened.
        '''
        self.channel._notify_open_listeners()

    def activate(self):
        '''
        Activate this channel (disable flow control).
        '''
        if not self.channel.active:
            self._send_flow(True)

    def deactivate(self):
        '''
        Deactivate this channel (enable flow control).
        '''
        if self.channel.active:
            self._send_flow(False)

    def _send_flow(self, active):
        '''
        Send a flow control command.
        '''
        args = Writer()
        args.write_bit(active)
        self.send_frame(MethodFrame(self.channel_id, 20, 20, args))
        self.channel.add_synchronous_cb(self._recv_flow_ok)

    def _recv_flow(self, method_frame):
        '''
        Receive a flow control command from the broker
        '''
        self.channel._active = method_frame.args.read_bit()

        args = Writer()
        args.write_bit(self.channel.active)
        self.send_frame(MethodFrame(self.channel_id, 20, 21, args))

        if self._flow_control_cb is not None:
            self._flow_control_cb()

    def _recv_flow_ok(self, method_frame):
        '''
        Receive a flow control ack from the broker.
        '''
        self.channel._active = method_frame.args.read_bit()
        if self._flow_control_cb is not None:
            self._flow_control_cb()

    def close(self, reply_code=0, reply_text='', class_id=0, method_id=0):
        '''
        Close this channel.  Caller has the option of specifying the reason for
        closure and the class and method ids of the current frame in which an
        error occurred.  If in the event of an exception, the channel will be
        marked as immediately closed.  If channel is already closed, call is
        ignored.
        '''
        if not getattr(self, 'channel', None) or self.channel._closed:
            return

        self.channel._close_info = {
            'reply_code': reply_code,
            'reply_text': reply_text,
            'class_id': class_id,
            'method_id': method_id
        }

        # exceptions here likely due to race condition as connection is closing
        # cap the reply_text we send because it may be arbitrarily long
        try:
            args = Writer()
            args.write_short(reply_code)
            args.write_shortstr(reply_text[:255])
            args.write_short(class_id)
            args.write_short(method_id)
            self.send_frame(MethodFrame(self.channel_id, 20, 40, args))

            self.channel.add_synchronous_cb(self._recv_close_ok)
        finally:
            # Immediately set the closed flag so no more frames can be sent
            # NOTE: in synchronous mode, by the time this is called we will
            # have already run self.channel._closed_cb and so the channel
            # reference is gone.
            if self.channel:
                self.channel._closed = True

    def _recv_close(self, method_frame):
        '''
        Receive a close command from the broker.
        '''
        self.channel._close_info = {
            'reply_code': method_frame.args.read_short(),
            'reply_text': method_frame.args.read_shortstr(),
            'class_id': method_frame.args.read_short(),
            'method_id': method_frame.args.read_short()
        }

        self.channel._closed = True
        self.channel._closed_cb(
            final_frame=MethodFrame(self.channel_id, 20, 41))

    def _recv_close_ok(self, method_frame):
        '''
        Receive a close ack from the broker.
        '''
        self.channel._closed = True
        self.channel._closed_cb()

########NEW FILE########
__FILENAME__ = exchange_class
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from collections import deque

from haigha.writer import Writer
from haigha.frames.method_frame import MethodFrame
from haigha.classes.protocol_class import ProtocolClass


class ExchangeClass(ProtocolClass):

    '''
    Implements the AMQP Exchange class
    '''

    def __init__(self, *args, **kwargs):
        super(ExchangeClass, self).__init__(*args, **kwargs)
        self.dispatch_map = {
            11: self._recv_declare_ok,
            21: self._recv_delete_ok,
        }

        self._declare_cb = deque()
        self._delete_cb = deque()

    @property
    def name(self):
        return 'exchange'

    def _cleanup(self):
        '''
        Cleanup local data.
        '''
        self._declare_cb = None
        self._delete_cb = None
        super(ExchangeClass, self)._cleanup()

    def declare(self, exchange, type, passive=False, durable=False,
                nowait=True, arguments=None, ticket=None, cb=None):
        """
        Declare the exchange.

        exchange - The name of the exchange to declare
        type - One of
        """
        nowait = nowait and self.allow_nowait() and not cb

        args = Writer()
        args.write_short(ticket or self.default_ticket).\
            write_shortstr(exchange).\
            write_shortstr(type).\
            write_bits(passive, durable, False, False, nowait).\
            write_table(arguments or {})
        self.send_frame(MethodFrame(self.channel_id, 40, 10, args))

        if not nowait:
            self._declare_cb.append(cb)
            self.channel.add_synchronous_cb(self._recv_declare_ok)

    def _recv_declare_ok(self, _method_frame):
        '''
        Confirmation that exchange was declared.
        '''
        cb = self._declare_cb.popleft()
        if cb:
            cb()

    def delete(self, exchange, if_unused=False, nowait=True, ticket=None,
               cb=None):
        '''
        Delete an exchange.
        '''
        nowait = nowait and self.allow_nowait() and not cb

        args = Writer()
        args.write_short(ticket or self.default_ticket).\
            write_shortstr(exchange).\
            write_bits(if_unused, nowait)
        self.send_frame(MethodFrame(self.channel_id, 40, 20, args))

        if not nowait:
            self._delete_cb.append(cb)
            self.channel.add_synchronous_cb(self._recv_delete_ok)

    def _recv_delete_ok(self, _method_frame):
        '''
        Confirmation that exchange was deleted.
        '''
        cb = self._delete_cb.popleft()
        if cb:
            cb()

########NEW FILE########
__FILENAME__ = protocol_class
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''


class ProtocolClass(object):

    '''
    The base class of all protocol classes.
    '''

    class ProtocolError(Exception):
        pass

    class InvalidMethod(ProtocolError):
        pass

    class FrameUnderflow(ProtocolError):
        pass

    dispatch_map = {}

    def __init__(self, channel):
        '''
        Construct this protocol class on a channel.
        '''
        # Cache the channel id so that cleanup can remove the circular channel
        # reference but id is still accessible (it's useful!)
        self._channel = channel
        self._channel_id = channel.channel_id

    @property
    def channel(self):
        return self._channel

    @property
    def channel_id(self):
        return self._channel_id

    @property
    def logger(self):
        return self._channel.logger

    @property
    def default_ticket(self):
        return 0

    @property
    def name(self):
        '''The name given this in the protocol, i.e. 'basic', 'tx', etc'''
        raise NotImplementedError('must provide a name for %s' % (self))

    def allow_nowait(self):
        '''
        Return True if the transport or  channel allows nowait,
        False otherwise.
        '''
        return not self._channel.synchronous

    def _cleanup(self):
        '''
        "Private" call from Channel when it's shutting down so that local
        data can be cleaned up and references closed out. It's strongly
        recommended that subclasses call this /after/ doing their own cleanup .
        Note that this removes reference to both the channel and the dispatch
        map.
        '''
        self._channel = None
        self.dispatch_map = None

    def dispatch(self, method_frame):
        '''
        Dispatch a method for this protocol.
        '''
        method = self.dispatch_map.get(method_frame.method_id)
        if method:
            callback = self.channel.clear_synchronous_cb(method)
            callback(method_frame)
        else:
            raise self.InvalidMethod(
                "no method is registered with id: %d" % method_frame.method_id)

    def send_frame(self, frame):
        '''
        Send a frame
        '''
        self.channel.send_frame(frame)

########NEW FILE########
__FILENAME__ = queue_class
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from haigha.writer import Writer
from haigha.frames.method_frame import MethodFrame
from haigha.classes.protocol_class import ProtocolClass

from collections import deque


class QueueClass(ProtocolClass):

    '''
    Implements the AMQP Queue class
    '''

    def __init__(self, *args, **kwargs):
        super(QueueClass, self).__init__(*args, **kwargs)
        self.dispatch_map = {
            11: self._recv_declare_ok,
            21: self._recv_bind_ok,
            31: self._recv_purge_ok,
            41: self._recv_delete_ok,
            51: self._recv_unbind_ok,
        }

        self._declare_cb = deque()
        self._bind_cb = deque()
        self._unbind_cb = deque()
        self._delete_cb = deque()
        self._purge_cb = deque()

    @property
    def name(self):
        return 'queue'

    def _cleanup(self):
        '''
        Cleanup all the local data.
        '''
        self._declare_cb = None
        self._bind_cb = None
        self._unbind_cb = None
        self._delete_cb = None
        self._purge_cb = None
        super(QueueClass, self)._cleanup()

    def declare(self, queue='', passive=False, durable=False,
                exclusive=False, auto_delete=True, nowait=True,
                arguments={}, ticket=None, cb=None):
        '''
        Declare a queue. By default is asynchronoous but will be synchronous
        if nowait=False or a callback is defined. In synchronous mode,
        returns (message_count, consumer_count)

        queue - The name of the queue
        cb - An optional method which will be called with
              (queue_name, msg_count, consumer_count) if nowait=False
        '''
        nowait = nowait and self.allow_nowait() and not cb

        args = Writer()
        args.write_short(ticket or self.default_ticket).\
            write_shortstr(queue).\
            write_bits(passive, durable, exclusive, auto_delete, nowait).\
            write_table(arguments)
        self.send_frame(MethodFrame(self.channel_id, 50, 10, args))

        if not nowait:
            self._declare_cb.append(cb)
            return self.channel.add_synchronous_cb(self._recv_declare_ok)

    def _recv_declare_ok(self, method_frame):
        queue = method_frame.args.read_shortstr()
        message_count = method_frame.args.read_long()
        consumer_count = method_frame.args.read_long()

        cb = self._declare_cb.popleft()
        if cb:
            cb(queue, message_count, consumer_count)
        return queue, message_count, consumer_count

    def bind(self, queue, exchange, routing_key='', nowait=True, arguments={},
             ticket=None, cb=None):
        '''
        bind to a queue.
        '''
        nowait = nowait and self.allow_nowait() and not cb

        args = Writer()
        args.write_short(ticket or self.default_ticket).\
            write_shortstr(queue).\
            write_shortstr(exchange).\
            write_shortstr(routing_key).\
            write_bit(nowait).\
            write_table(arguments)
        self.send_frame(MethodFrame(self.channel_id, 50, 20, args))

        if not nowait:
            self._bind_cb.append(cb)
            self.channel.add_synchronous_cb(self._recv_bind_ok)

    def _recv_bind_ok(self, _method_frame):
        # No arguments defined.
        cb = self._bind_cb.popleft()
        if cb:
            cb()

    def unbind(self, queue, exchange, routing_key='', arguments={},
               ticket=None, cb=None):
        '''
        Unbind a queue from an exchange.  This is always synchronous.
        '''
        args = Writer()
        args.write_short(ticket or self.default_ticket).\
            write_shortstr(queue).\
            write_shortstr(exchange).\
            write_shortstr(routing_key).\
            write_table(arguments)
        self.send_frame(MethodFrame(self.channel_id, 50, 50, args))

        self._unbind_cb.append(cb)
        self.channel.add_synchronous_cb(self._recv_unbind_ok)

    def _recv_unbind_ok(self, _method_frame):
        # No arguments defined
        cb = self._unbind_cb.popleft()
        if cb:
            cb()

    def purge(self, queue, nowait=True, ticket=None, cb=None):
        '''
        Purge all messages in a queue.
        '''
        nowait = nowait and self.allow_nowait() and not cb

        args = Writer()
        args.write_short(ticket or self.default_ticket).\
            write_shortstr(queue).\
            write_bit(nowait)
        self.send_frame(MethodFrame(self.channel_id, 50, 30, args))

        if not nowait:
            self._purge_cb.append(cb)
            return self.channel.add_synchronous_cb(self._recv_purge_ok)

    def _recv_purge_ok(self, method_frame):
        message_count = method_frame.args.read_long()
        cb = self._purge_cb.popleft()
        if cb:
            cb(message_count)
        return message_count

    def delete(self, queue, if_unused=False, if_empty=False, nowait=True,
               ticket=None, cb=None):
        '''
        queue delete.
        '''
        nowait = nowait and self.allow_nowait() and not cb

        args = Writer()
        args.write_short(ticket or self.default_ticket).\
            write_shortstr(queue).\
            write_bits(if_unused, if_empty, nowait)
        self.send_frame(MethodFrame(self.channel_id, 50, 40, args))

        if not nowait:
            self._delete_cb.append(cb)
            return self.channel.add_synchronous_cb(self._recv_delete_ok)

    def _recv_delete_ok(self, method_frame):
        message_count = method_frame.args.read_long()
        cb = self._delete_cb.popleft()
        if cb:
            cb(message_count)
        return message_count

########NEW FILE########
__FILENAME__ = transaction_class
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from haigha.frames.method_frame import MethodFrame
from haigha.classes.protocol_class import ProtocolClass

from collections import deque


class TransactionClass(ProtocolClass):

    '''
    Implements the AMQP Transaction class
    '''

    class TransactionsNotEnabled(ProtocolClass.ProtocolError):

        '''Tried to use transactions without enabling them.'''

    def __init__(self, *args, **kwargs):
        super(TransactionClass, self).__init__(*args, **kwargs)
        self.dispatch_map = {
            11: self._recv_select_ok,
            21: self._recv_commit_ok,
            31: self._recv_rollback_ok,
        }

        self._enabled = False
        self._select_cb = deque()
        self._commit_cb = deque()
        self._rollback_cb = deque()

    @property
    def name(self):
        return 'tx'

    @property
    def enabled(self):
        '''Get whether transactions have been enabled.'''
        return self._enabled

    def _cleanup(self):
        '''
        Cleanup all the local data.
        '''
        self._select_cb = None
        self._commit_cb = None
        self._rollback_cb = None
        super(TransactionClass, self)._cleanup()

    def select(self, cb=None):
        '''
        Set this channel to use transactions.
        '''
        if not self._enabled:
            self._enabled = True
            self.send_frame(MethodFrame(self.channel_id, 90, 10))
            self._select_cb.append(cb)
            self.channel.add_synchronous_cb(self._recv_select_ok)

    def _recv_select_ok(self, _method_frame):
        cb = self._select_cb.popleft()
        if cb:
            cb()

    def commit(self, cb=None):
        '''
        Commit the current transaction.  Caller can specify a callback to use
        when the transaction is committed.
        '''
        # Could call select() but spec 1.9.2.3 says to raise an exception
        if not self.enabled:
            raise self.TransactionsNotEnabled()

        self.send_frame(MethodFrame(self.channel_id, 90, 20))
        self._commit_cb.append(cb)
        self.channel.add_synchronous_cb(self._recv_commit_ok)

    def _recv_commit_ok(self, _method_frame):
        cb = self._commit_cb.popleft()
        if cb:
            cb()

    def rollback(self, cb=None):
        '''
        Abandon all message publications and acks in the current transaction.
        Caller can specify a callback to use when the transaction has been
        aborted.
        '''
        # Could call select() but spec 1.9.2.5 says to raise an exception
        if not self.enabled:
            raise self.TransactionsNotEnabled()

        self.send_frame(MethodFrame(self.channel_id, 90, 30))
        self._rollback_cb.append(cb)
        self.channel.add_synchronous_cb(self._recv_rollback_ok)

    def _recv_rollback_ok(self, _method_frame):
        cb = self._rollback_cb.popleft()
        if cb:
            cb()

########NEW FILE########
__FILENAME__ = connection
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from haigha.channel import Channel
from haigha.frames.frame import Frame
from haigha.frames.heartbeat_frame import HeartbeatFrame
from haigha.frames.method_frame import MethodFrame
from haigha.classes.basic_class import BasicClass
from haigha.classes.channel_class import ChannelClass
from haigha.classes.exchange_class import ExchangeClass
from haigha.classes.queue_class import QueueClass
from haigha.classes.transaction_class import TransactionClass
from haigha.writer import Writer
from haigha.reader import Reader
from haigha.transports.transport import Transport
from exceptions import ConnectionError, ConnectionClosed

import haigha
import time

from logging import root as root_logger

# From the rabbitmq mailing list
# AMQP1180 = 0-8
# AMQP1109 = 0-9
# AMQP0091 = 0-9-1
# http://lists.rabbitmq.com/pipermail/rabbitmq-discuss/2010-July/008231.html
# PROTOCOL_HEADER = 'AMQP\x01\x01\x09\x01'
PROTOCOL_HEADER = 'AMQP\x00\x00\x09\x01'

# Client property info that gets sent to the server on connection startup
LIBRARY_PROPERTIES = {
    'library': 'Haigha',
    'library_version': haigha.__version__,
}


class Connection(object):

    class TooManyChannels(ConnectionError):
        '''This connection has too many channels open.  Non-fatal.'''

    class InvalidChannel(ConnectionError):
        '''
        The channel id does not correspond to an existing channel.  Non-fatal.
        '''

    def __init__(self, **kwargs):
        '''
        Initialize the connection.
        '''
        self._debug = kwargs.get('debug', False)
        self._logger = kwargs.get('logger', root_logger)

        self._user = kwargs.get('user', 'guest')
        self._password = kwargs.get('password', 'guest')
        self._host = kwargs.get('host', 'localhost')
        self._port = kwargs.get('port', 5672)
        self._vhost = kwargs.get('vhost', '/')

        self._connect_timeout = kwargs.get('connect_timeout', 5)
        self._sock_opts = kwargs.get('sock_opts')
        self._sock = None
        self._heartbeat = kwargs.get('heartbeat')
        self._open_cb = kwargs.get('open_cb')
        self._close_cb = kwargs.get('close_cb')

        self._login_method = kwargs.get('login_method', 'AMQPLAIN')
        self._locale = kwargs.get('locale', 'en_US')
        self._client_properties = kwargs.get('client_properties')

        self._properties = LIBRARY_PROPERTIES.copy()
        if self._client_properties:
            self._properties.update(self._client_properties)

        self._closed = False
        self._connected = False
        self._close_info = {
            'reply_code': 0,
            'reply_text': 'first connect',
            'class_id': 0,
            'method_id': 0
        }

        # Not sure what's better here, setdefaults or require the caller to
        # pass the whole thing in.
        self._class_map = kwargs.get('class_map', {}).copy()
        self._class_map.setdefault(20, ChannelClass)
        self._class_map.setdefault(40, ExchangeClass)
        self._class_map.setdefault(50, QueueClass)
        self._class_map.setdefault(60, BasicClass)
        self._class_map.setdefault(90, TransactionClass)

        self._channels = {
            0: ConnectionChannel(self, 0, {})
        }

        # Login response seems a total hack of protocol
        # Skip the length at the beginning
        login_response = Writer()
        login_response.write_table(
            {'LOGIN': self._user, 'PASSWORD': self._password})
        self._login_response = login_response.buffer()[4:]

        self._channel_counter = 0
        self._channel_max = 65535
        self._frame_max = 65535

        self._frames_read = 0
        self._frames_written = 0

        # Default to the socket strategy
        transport = kwargs.get('transport', 'socket')
        if not isinstance(transport, Transport):
            if transport == 'event':
                from haigha.transports.event_transport import EventTransport
                self._transport = EventTransport(self)
            elif transport == 'gevent':
                from haigha.transports.gevent_transport import GeventTransport
                self._transport = GeventTransport(self)
            elif transport == 'gevent_pool':
                from haigha.transports.gevent_transport import \
                    GeventPoolTransport
                self._transport = GeventPoolTransport(self, **kwargs)
            elif transport == 'socket':
                from haigha.transports.socket_transport import SocketTransport
                self._transport = SocketTransport(self)
        else:
            self._transport = transport

        # Set these after the transport is initialized, so that we can access
        # the synchronous property
        self._synchronous = kwargs.get('synchronous', False)
        self._synchronous_connect = kwargs.get(
            'synchronous_connect', False) or self.synchronous

        self._output_frame_buffer = []
        self.connect(self._host, self._port)

    @property
    def logger(self):
        return self._logger

    @property
    def debug(self):
        return self._debug

    @property
    def frame_max(self):
        return self._frame_max

    @property
    def channel_max(self):
        return self._channel_max

    @property
    def frames_read(self):
        '''Number of frames read in the lifetime of this connection.'''
        return self._frames_read

    @property
    def frames_written(self):
        '''Number of frames written in the lifetime of this connection.'''
        return self._frames_written

    @property
    def closed(self):
        '''Return the closed state of the connection.'''
        return self._closed

    @property
    def close_info(self):
        '''
        Return dict with information on why this connection is closed.  Will
        return None if the connections is open.
        '''
        return self._close_info if (
            self._closed or not self._connected) else None

    @property
    def transport(self):
        '''Get the value of the current transport.'''
        return self._transport

    @property
    def synchronous(self):
        '''
        True if transport is synchronous or the connection has been forced
        into synchronous mode, False otherwise.
        '''
        if self._transport is None:
            if self._close_info and len(self._close_info['reply_text']) > 0:
                raise ConnectionClosed("connection is closed: %s : %s" %
                                       (self._close_info['reply_code'],
                                        self._close_info['reply_text']))
            raise ConnectionClosed("connection is closed")
        return self.transport.synchronous or self._synchronous

    def connect(self, host, port):
        '''
        Connect to a host and port.
        '''
        # Clear the connect state immediately since we're no longer connected
        # at this point.
        self._connected = False

        # Only after the socket has connected do we clear this state; closed
        # must be False so that writes can be buffered in writePacket(). The
        # closed state might have been set to True due to a socket error or a
        # redirect.
        self._host = "%s:%d" % (host, port)
        self._closed = False
        self._close_info = {
            'reply_code': 0,
            'reply_text': 'failed to connect to %s' % (self._host),
            'class_id': 0,
            'method_id': 0
        }

        self._transport.connect((host, port))
        self._transport.write(PROTOCOL_HEADER)

        if self._synchronous_connect:
            # Have to queue this callback just after connect, it can't go
            # into the constructor because the channel needs to be
            # "always there" for frame processing, but the synchronous
            # callback can't be added until after the protocol header has
            # been written. This SHOULD be registered before the protocol
            # header is written, in the case where the header bytes are
            # written, but this thread/greenlet/context does not return until
            # after another thread/greenlet/context has read and processed the
            # recv_start frame. Without more re-write to add_sync_cb though,
            # it will block on reading responses that will never arrive
            # because the protocol header isn't written yet. TBD if needs
            # refactoring. Could encapsulate entirely here, wherein
            # read_frames exits if protocol header not yet written. Like other
            # synchronous behaviors, adding this callback will result in a
            # blocking frame read and process loop until _recv_start and any
            # subsequent synchronous callbacks have been processed. In the
            # event that this is /not/ a synchronous transport, but the
            # caller wants the connect to be synchronous so as to ensure that
            # the connection is ready, then do a read frame loop here.
            self._channels[0].add_synchronous_cb(self._channels[0]._recv_start)
            while not self._connected:
                self.read_frames()

    def disconnect(self):
        '''
        Disconnect from the current host, but do not update the closed state.
        After the transport is disconnected, the closed state will be True if
        this is called after a protocol shutdown, or False if the disconnect
        was in error.

        TODO: do we really need closed vs. connected states? this only adds
        complication and the whole reconnect process has been scrapped anyway.

        '''
        self._connected = False
        if self._transport is not None:
            try:
                self._transport.disconnect()
            except Exception:
                self.logger.error(
                    "Failed to disconnect from %s", self._host, exc_info=True)
                raise
            finally:
                self._transport = None

    ###
    # Transport methods
    ###
    def transport_closed(self, **kwargs):
        """
        Called by Transports when they close unexpectedly, not as a result of
        Connection.disconnect().

        TODO: document args
        """
        msg = 'unknown cause'
        self.logger.warning('transport to %s closed : %s' %
                            (self._host, kwargs.get('msg', msg)))
        self._close_info = {
            'reply_code': kwargs.get('reply_code', 0),
            'reply_text': kwargs.get('msg', msg),
            'class_id': kwargs.get('class_id', 0),
            'method_id': kwargs.get('method_id', 0)
        }

        # We're not connected any more, but we're not closed without an
        # explicit close call.
        self._connected = False
        self._transport = None

        # Call back to a user-provided close function
        self._callback_close()

    ###
    # Connection methods
    ###
    def _next_channel_id(self):
        '''Return the next possible channel id.  Is a circular enumeration.'''
        self._channel_counter += 1
        if self._channel_counter >= self._channel_max:
            self._channel_counter = 1
        return self._channel_counter

    def channel(self, channel_id=None, synchronous=False):
        """
        Fetch a Channel object identified by the numeric channel_id, or
        create that object if it doesn't already exist.  If channel_id is not
        None but no channel exists for that id, will raise InvalidChannel.  If
        there are already too many channels open, will raise TooManyChannels.

        If synchronous=True, then the channel will act synchronous in all cases
        where a protocol method supports `nowait=False`, or where there is an
        implied callback in the protocol.
        """
        if channel_id is None:
            # adjust for channel 0
            if len(self._channels) - 1 >= self._channel_max:
                raise Connection.TooManyChannels(
                    "%d channels already open, max %d",
                    len(self._channels) - 1,
                    self._channel_max)
            channel_id = self._next_channel_id()
            while channel_id in self._channels:
                channel_id = self._next_channel_id()
        elif channel_id in self._channels:
            return self._channels[channel_id]
        else:
            raise Connection.InvalidChannel(
                "%s is not a valid channel id", channel_id)

        # Call open() here so that ConnectionChannel doesn't have it called.
        # Could also solve this other ways, but it's a HACK regardless.
        rval = Channel(
            self, channel_id, self._class_map, synchronous=synchronous)
        self._channels[channel_id] = rval
        rval.add_close_listener(self._channel_closed)
        rval.open()
        return rval

    def _channel_closed(self, channel):
        '''
        Close listener on a channel.
        '''
        try:
            del self._channels[channel.channel_id]
        except KeyError:
            pass

    def close(self, reply_code=0, reply_text='', class_id=0, method_id=0,
              disconnect=False):
        '''
        Close this connection.
        '''
        self._close_info = {
            'reply_code': reply_code,
            'reply_text': reply_text,
            'class_id': class_id,
            'method_id': method_id
        }
        if disconnect:
            self._closed = True
            self.disconnect()
            self._callback_close()
        else:
            self._channels[0].close()

    def _callback_open(self):
        '''
        Callback to any open handler that was provided in the ctor. Handler is
        responsible for exceptions.
        '''
        if self._open_cb:
            self._open_cb()

    def _callback_close(self):
        '''
        Callback to any close handler that was provided in the ctor. Handler is
        responsible for exceptions.
        '''
        if self._close_cb:
            self._close_cb()

    def read_frames(self):
        '''
        Read frames from the transport and process them. Some transports may
        choose to do this in the background, in several threads, and so on.
        '''
        # It's possible in a concurrent environment that our transport handle
        # has gone away, so handle that cleanly.
        # TODO: Consider moving this block into Translator base class. In many
        # ways it belongs there. One of the problems though is that this is
        # essentially the read loop. Each Transport has different rules for
        # how to kick this off, and in the case of gevent, this is how a
        # blocking call to read from the socket is kicked off.
        if self._transport is None:
            return

        # Send a heartbeat (if needed)
        self._channels[0].send_heartbeat()

        data = self._transport.read(self._heartbeat)
        if data is None:
            return

        reader = Reader(data)
        p_channels = set()

        try:
            for frame in Frame.read_frames(reader):
                if self._debug > 1:
                    self.logger.debug("READ: %s", frame)
                self._frames_read += 1
                ch = self.channel(frame.channel_id)
                ch.buffer_frame(frame)
                p_channels.add(ch)
        except Frame.FrameError as e:
            # Frame error in the peer, disconnect
            self.close(reply_code=501,
                       reply_text='frame error from %s : %s' % (
                           self._host, str(e)),
                       class_id=0, method_id=0, disconnect=True)
            raise ConnectionClosed("connection is closed: %s : %s" %
                                   (self._close_info['reply_code'],
                                    self._close_info['reply_text']))

        self._transport.process_channels(p_channels)

        # HACK: read the buffer contents and re-buffer.  Would prefer to pass
        # buffer back, but there's no good way of asking the total size of the
        # buffer, comparing to tell(), and then re-buffering.  There's also no
        # ability to clear the buffer up to the current position. It would be
        # awesome if we could free that memory without a new allocation.
        if reader.tell() < len(data):
            self._transport.buffer(data[reader.tell():])

    def _flush_buffered_frames(self):
        '''
        Callback when protocol has been initialized on channel 0 and we're
        ready to send out frames to set up any channels that have been
        created.
        '''
        # In the rare case (a bug) where this is called but send_frame thinks
        # they should be buffered, don't clobber.
        frames = self._output_frame_buffer
        self._output_frame_buffer = []
        for frame in frames:
            self.send_frame(frame)

    def send_frame(self, frame):
        '''
        Send a single frame. If there is no transport or we're not connected
        yet, append to the output buffer, else send immediately to the socket.
        This is called from within the MethodFrames.
        '''
        if self._closed:
            if self._close_info and len(self._close_info['reply_text']) > 0:
                raise ConnectionClosed("connection is closed: %s : %s" %
                                       (self._close_info['reply_code'],
                                        self._close_info['reply_text']))
            raise ConnectionClosed("connection is closed")

        if self._transport is None or \
                (not self._connected and frame.channel_id != 0):
            self._output_frame_buffer.append(frame)
            return

        if self._debug > 1:
            self.logger.debug("WRITE: %s", frame)

        buf = bytearray()
        frame.write_frame(buf)
        if len(buf) > self._frame_max:
            self.close(
                reply_code=501,
                reply_text='attempted to send frame of %d bytes, frame max %d' % (
                    len(buf), self._frame_max),
                class_id=0, method_id=0, disconnect=True)
            raise ConnectionClosed(
                "connection is closed: %s : %s" %
                (self._close_info['reply_code'],
                 self._close_info['reply_text']))
        self._transport.write(buf)

        self._frames_written += 1


class ConnectionChannel(Channel):

    '''
    A special channel for the Connection class.  It's used for performing the
    special methods only available on the main connection channel.  It's also
    partly used to hide the 'connection' protocol implementation, which would
    show up as a property, from the more useful 'connection' property that is
    a handle to a Channel's Connection object.
    '''

    def __init__(self, *args):
        super(ConnectionChannel, self).__init__(*args)

        self._method_map = {
            10: self._recv_start,
            20: self._recv_secure,
            30: self._recv_tune,
            41: self._recv_open_ok,
            50: self._recv_close,
            51: self._recv_close_ok,
        }
        self._last_heartbeat_send = 0

    def dispatch(self, frame):
        '''
        Override the default dispatch since we don't need the rest of
        the stack.
        '''
        if frame.type() == HeartbeatFrame.type():
            self.send_heartbeat()

        elif frame.type() == MethodFrame.type():
            if frame.class_id == 10:
                cb = self._method_map.get(frame.method_id)
                if cb:
                    method = self.clear_synchronous_cb(cb)
                    method(frame)
                else:
                    raise Channel.InvalidMethod(
                        "unsupported method %d on channel %d",
                        frame.method_id, self.channel_id)
            else:
                raise Channel.InvalidClass(
                    "class %d is not supported on channel %d",
                    frame.class_id, self.channel_id)

        else:
            raise Frame.InvalidFrameType(
                "frame type %d is not supported on channel %d",
                frame.type(), self.channel_id)

    def close(self, reply_code=0, reply_text='', class_id=0, method_id=0):
        '''
        Close the main connection connection channel.
        '''
        self._send_close()

    def send_heartbeat(self):
        '''
        Send a heartbeat if needed. Tracks last heartbeat send time.
        '''
        # Note that this does not take into account the time that we last
        # sent a frame. Hearbeats are so small the effect should be quite
        # limited. Also note that we're looking for something near to our
        # scheduled interval, because if this is exact, then we'll likely
        # actually send a heartbeat at twice the period, which could cause
        # a broker to kill the connection if the period is large enough. The
        # 90% bound is arbitrary but seems a sensible enough default.
        if self.connection._heartbeat:
            if time.time() >= (self._last_heartbeat_send + 0.9 *
                               self.connection._heartbeat):
                self.send_frame(HeartbeatFrame(self.channel_id))
                self._last_heartbeat_send = time.time()

    def _recv_start(self, method_frame):
        self.connection._closed = False
        self._send_start_ok()

    def _send_start_ok(self):
        '''Send the start_ok message.'''
        args = Writer()
        args.write_table(self.connection._properties)
        args.write_shortstr(self.connection._login_method)
        args.write_longstr(self.connection._login_response)
        args.write_shortstr(self.connection._locale)
        self.send_frame(MethodFrame(self.channel_id, 10, 11, args))

        self.add_synchronous_cb(self._recv_tune)

    def _recv_tune(self, method_frame):
        self.connection._channel_max = method_frame.args.read_short(
        ) or self.connection._channel_max
        self.connection._frame_max = method_frame.args.read_long(
        ) or self.connection._frame_max

        # Note that 'is' test is required here, as 0 and None are distinct
        if self.connection._heartbeat is None:
            self.connection._heartbeat = method_frame.args.read_short()

        self._send_tune_ok()
        self._send_open()

        # 4.2.7: The client should start sending heartbeats after receiving a
        # Connection.Tune method
        self.send_heartbeat()

    def _send_tune_ok(self):
        args = Writer()
        args.write_short(self.connection._channel_max)
        args.write_long(self.connection._frame_max)

        if self.connection._heartbeat:
            args.write_short(self.connection._heartbeat)
        else:
            args.write_short(0)

        self.send_frame(MethodFrame(self.channel_id, 10, 31, args))

    def _recv_secure(self, method_frame):
        self._send_open()

    def _send_open(self):
        args = Writer()
        args.write_shortstr(self.connection._vhost)
        args.write_shortstr('')
        args.write_bit(True)  # insist flag for older amqp, not used in 0.9.1

        self.send_frame(MethodFrame(self.channel_id, 10, 40, args))
        self.add_synchronous_cb(self._recv_open_ok)

    def _recv_open_ok(self, method_frame):
        self.connection._connected = True
        self.connection._flush_buffered_frames()
        self.connection._callback_open()

    def _send_close(self):
        args = Writer()
        args.write_short(self.connection._close_info['reply_code'])
        args.write_shortstr(self.connection._close_info['reply_text'][:255])
        args.write_short(self.connection._close_info['class_id'])
        args.write_short(self.connection._close_info['method_id'])
        self.send_frame(MethodFrame(self.channel_id, 10, 50, args))
        self.add_synchronous_cb(self._recv_close_ok)

    def _recv_close(self, method_frame):
        self.connection._close_info = {
            'reply_code': method_frame.args.read_short(),
            'reply_text': method_frame.args.read_shortstr(),
            'class_id': method_frame.args.read_short(),
            'method_id': method_frame.args.read_short()
        }

        # TODO: wait to disconnect until the close_ok has been flushed, but
        # that's a pain
        self._send_close_ok()

        self.connection._closed = True
        self.connection.disconnect()
        self.connection._callback_close()

    def _send_close_ok(self):
        self.send_frame(MethodFrame(self.channel_id, 10, 51))

    def _recv_close_ok(self, method_frame):
        self.connection._closed = True
        self.connection.disconnect()
        self.connection._callback_close()

########NEW FILE########
__FILENAME__ = rabbit_connection
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from collections import deque

from haigha.connection import Connection
from haigha.classes.basic_class import BasicClass
from haigha.classes.exchange_class import ExchangeClass
from haigha.classes.protocol_class import ProtocolClass
from haigha.writer import Writer
from haigha.frames.method_frame import MethodFrame


class RabbitConnection(Connection):

    '''
    A connection specific to RabbitMQ that supports its extensions.
    '''

    def __init__(self, **kwargs):
        '''
        Initialize the connection
        '''
        class_map = kwargs.get('class_map', {}).copy()
        class_map.setdefault(40, RabbitExchangeClass)
        class_map.setdefault(60, RabbitBasicClass)
        class_map.setdefault(85, RabbitConfirmClass)
        kwargs['class_map'] = class_map

        super(RabbitConnection, self).__init__(**kwargs)


class RabbitExchangeClass(ExchangeClass):

    '''
    Exchange class Rabbit extensions
    '''

    def __init__(self, *args, **kwargs):
        super(RabbitExchangeClass, self).__init__(*args, **kwargs)
        self.dispatch_map[31] = self._recv_bind_ok
        self.dispatch_map[51] = self._recv_unbind_ok

        self._bind_cb = deque()
        self._unbind_cb = deque()

    # I hate the code copying here. Probably a better solution, like
    # functools.
    def declare(self, exchange, type, passive=False, durable=False,
                auto_delete=True, internal=False, nowait=True,
                arguments=None, ticket=None, cb=None):
        """
        Declare the exchange.

        exchange - The name of the exchange to declare
        type - One of
        """
        nowait = nowait and self.allow_nowait() and not cb

        args = Writer()
        args.write_short(ticket or self.default_ticket).\
            write_shortstr(exchange).\
            write_shortstr(type).\
            write_bits(passive, durable, auto_delete, internal, nowait).\
            write_table(arguments or {})
        self.send_frame(MethodFrame(self.channel_id, 40, 10, args))

        if not nowait:
            self._declare_cb.append(cb)
            self.channel.add_synchronous_cb(self._recv_declare_ok)

    def bind(self, exchange, source, routing_key='', nowait=True,
             arguments={}, ticket=None, cb=None):
        '''
        Bind an exchange to another.
        '''
        nowait = nowait and self.allow_nowait() and not cb

        args = Writer()
        args.write_short(ticket or self.default_ticket).\
            write_shortstr(exchange).\
            write_shortstr(source).\
            write_shortstr(routing_key).\
            write_bit(nowait).\
            write_table(arguments or {})
        self.send_frame(MethodFrame(self.channel_id, 40, 30, args))

        if not nowait:
            self._bind_cb.append(cb)
            self.channel.add_synchronous_cb(self._recv_bind_ok)

    def _recv_bind_ok(self, _method_frame):
        '''Confirm exchange bind.'''
        cb = self._bind_cb.popleft()
        if cb:
            cb()

    def unbind(self, exchange, source, routing_key='', nowait=True,
               arguments={}, ticket=None, cb=None):
        '''
        Unbind an exchange from another.
        '''
        nowait = nowait and self.allow_nowait() and not cb

        args = Writer()
        args.write_short(ticket or self.default_ticket).\
            write_shortstr(exchange).\
            write_shortstr(source).\
            write_shortstr(routing_key).\
            write_bit(nowait).\
            write_table(arguments or {})
        self.send_frame(MethodFrame(self.channel_id, 40, 40, args))

        if not nowait:
            self._unbind_cb.append(cb)
            self.channel.add_synchronous_cb(self._recv_unbind_ok)

    def _recv_unbind_ok(self, _method_frame):
        '''Confirm exchange unbind.'''
        cb = self._unbind_cb.popleft()
        if cb:
            cb()


class RabbitBasicClass(BasicClass):

    '''
    Support Rabbit extensions to Basic class.
    '''

    def __init__(self, *args, **kwargs):
        super(RabbitBasicClass, self).__init__(*args, **kwargs)
        self.dispatch_map[80] = self._recv_ack
        self.dispatch_map[120] = self._recv_nack

        self._ack_listener = None
        self._nack_listener = None

        self._msg_id = 0
        self._last_ack_id = 0

    def set_ack_listener(self, cb):
        '''
        Set a callback for ack listening, to be used when the channel is
        in publisher confirm mode. Will be called with a single integer
        argument which is the id of the message as returned from publish().

        cb(message_id)
        '''
        self._ack_listener = cb

    def set_nack_listener(self, cb):
        '''
        Set a callbnack for nack listening, to be used when the channel is
        in publisher confirm mode. Will be called with a single integer
        argument which is the id of the message as returned from publish()
        and a boolean flag indicating if it can be requeued.

        cb(message_id, reque)
        '''
        self._nack_listener = cb

    # Probably a better solution here, like functools
    def publish(self, *args, **kwargs):
        '''
        Publish a message. Will return the id of the message if publisher
        confirmations are enabled, else will return 0.
        '''
        if self.channel.confirm._enabled:
            self._msg_id += 1
        super(RabbitBasicClass, self).publish(*args, **kwargs)
        return self._msg_id

    def _recv_ack(self, method_frame):
        '''Receive an ack from the broker.'''
        if self._ack_listener:
            delivery_tag = method_frame.args.read_longlong()
            multiple = method_frame.args.read_bit()
            if multiple:
                while self._last_ack_id < delivery_tag:
                    self._last_ack_id += 1
                    self._ack_listener(self._last_ack_id)
            else:
                self._last_ack_id = delivery_tag
                self._ack_listener(self._last_ack_id)

    def nack(self, delivery_tag, multiple=False, requeue=False):
        '''Send a nack to the broker.'''
        args = Writer()
        args.write_longlong(delivery_tag).\
            write_bits(multiple, requeue)

        self.send_frame(MethodFrame(self.channel_id, 60, 120, args))

    def _recv_nack(self, method_frame):
        '''Receive a nack from the broker.'''
        if self._nack_listener:
            delivery_tag = method_frame.args.read_longlong()
            multiple, requeue = method_frame.args.read_bits(2)
            if multiple:
                while self._last_ack_id < delivery_tag:
                    self._last_ack_id += 1
                    self._nack_listener(self._last_ack_id, requeue)
            else:
                self._last_ack_id = delivery_tag
                self._nack_listener(self._last_ack_id, requeue)


class RabbitConfirmClass(ProtocolClass):

    '''
    Implementation of Rabbit's confirm class.
    '''

    def __init__(self, *args, **kwargs):
        super(RabbitConfirmClass, self).__init__(*args, **kwargs)
        self.dispatch_map = {
            11: self._recv_select_ok,
        }

        self._enabled = False
        self._select_cb = deque()

    @property
    def name(self):
        return 'confirm'

    def select(self, nowait=True, cb=None):
        '''
        Set this channel to use publisher confirmations.
        '''
        nowait = nowait and self.allow_nowait() and not cb

        if not self._enabled:
            self._enabled = True
            self.channel.basic._msg_id = 0
            self.channel.basic._last_ack_id = 0
            args = Writer()
            args.write_bit(nowait)

            self.send_frame(MethodFrame(self.channel_id, 85, 10, args))

            if not nowait:
                self._select_cb.append(cb)
                self.channel.add_synchronous_cb(self._recv_select_ok)

    def _recv_select_ok(self, _method_frame):
        cb = self._select_cb.popleft()
        if cb:
            cb()

########NEW FILE########
__FILENAME__ = exceptions
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''


class ConnectionError(Exception):

    '''Base class for all connection errors.'''


class ConnectionClosed(ConnectionError):

    '''The connection is closed.  Fatal.'''


class ChannelError(Exception):

    '''Base class for all channel errors.'''


class ChannelClosed(ChannelError):

    '''The channel is closed. Fatal.'''

########NEW FILE########
__FILENAME__ = content_frame
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from haigha.writer import Writer
from haigha.frames.frame import Frame


class ContentFrame(Frame):

    '''
    Frame for reading in content.
    '''

    @classmethod
    def type(cls):
        return 3

    @property
    def payload(self):
        return self._payload

    @classmethod
    def parse(self, channel_id, payload):
        return ContentFrame(channel_id, payload)

    @classmethod
    def create_frames(self, channel_id, buf, frame_max):
        '''
        A generator which will create frames from a buffer given a max
        frame size.
        '''
        size = frame_max - 8   # 8 bytes overhead for frame header and footer
        offset = 0
        while True:
            payload = buf[offset:(offset + size)]
            if len(payload) == 0:
                break
            offset += size

            yield ContentFrame(channel_id, payload)
            if offset >= len(buf):
                break

    def __init__(self, channel_id, payload):
        Frame.__init__(self, channel_id)
        self._payload = payload

    def __str__(self):
        if isinstance(self._payload, str):
            payload = ''.join(['\\x%s' % (c.encode('hex'))
                               for c in self._payload])
        else:
            payload = str(self._payload)

        return "%s[channel: %d, payload: %s]" % (
            self.__class__.__name__, self.channel_id, payload)

    def write_frame(self, buf):
        '''
        Write the frame into an existing buffer.
        '''
        writer = Writer(buf)

        writer.write_octet(self.type()).\
            write_short(self.channel_id).\
            write_long(len(self._payload)).\
            write(self._payload).\
            write_octet(0xce)


ContentFrame.register()

########NEW FILE########
__FILENAME__ = frame
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

import struct
import sys
from collections import deque
from haigha.reader import Reader


class Frame(object):

    '''
    Base class for a frame.
    '''

    # Exceptions
    class FrameError(Exception):

        '''Base class for all frame errors'''
    class FormatError(FrameError):

        '''The frame was mal-formed.'''
    class InvalidFrameType(FrameError):

        '''The frame type is unknown.'''

    # Class data
    _frame_type_map = {}

    # Class methods
    @classmethod
    def register(cls):
        '''
        Register a frame type.
        '''
        cls._frame_type_map[cls.type()] = cls

    @classmethod
    def type(self):
        '''
        Fetch the type of this frame.  Should be an octet.
        '''
        raise NotImplementedError()

    @classmethod
    def read_frames(cls, reader):
        '''
        Read one or more frames from an IO stream.  Buffer must support file
        object interface.

        After reading, caller will need to check if there are bytes remaining
        in the stream. If there are, then that implies that there is one or
        more incomplete frames and more data needs to be read.  The position
        of the cursor in the frame stream will mark the point at which the
        last good frame was read. If the caller is expecting a sequence of
        frames and only received a part of that sequence, they are responsible
        for buffering those frames until the rest of the frames in the sequence
        have arrived.
        '''
        rval = deque()

        while True:
            frame_start_pos = reader.tell()
            try:
                frame = Frame._read_frame(reader)
            except Reader.BufferUnderflow:
                # No more data in the stream
                frame = None
            except Reader.ReaderError as e:
                # Some other format error
                raise Frame.FormatError, str(e), sys.exc_info()[-1]
            except struct.error as e:
                raise Frame.FormatError, str(e), sys.exc_info()[-1]

            if frame is None:
                reader.seek(frame_start_pos)
                break

            rval.append(frame)

        return rval

    @classmethod
    def _read_frame(cls, reader):
        '''
        Read a single frame from a Reader.  Will return None if there is an
        incomplete frame in the stream.

        Raise MissingFooter if there's a problem reading the footer byte.
        '''
        frame_type = reader.read_octet()
        channel_id = reader.read_short()
        size = reader.read_long()

        payload = Reader(reader, reader.tell(), size)

        # Seek to end of payload
        reader.seek(size, 1)

        ch = reader.read_octet()  # footer
        if ch != 0xce:
            raise Frame.FormatError(
                'Framing error, unexpected byte: %x.  frame type %x. channel %d, payload size %d',
                ch, frame_type, channel_id, size)

        frame_class = cls._frame_type_map.get(frame_type)
        if not frame_class:
            raise Frame.InvalidFrameType("Unknown frame type %x", frame_type)
        return frame_class.parse(channel_id, payload)

    # Instance methods
    def __init__(self, channel_id=-1):
        self._channel_id = channel_id

    @classmethod
    def parse(cls, channel_id, payload):
        '''
        Subclasses need to implement parsing of their frames.  Should return
        a new instance of their type.
        '''
        raise NotImplementedError()

    @property
    def channel_id(self):
        return self._channel_id

    def __str__(self):
        return "%s[channel: %d]" % (self.__class__.__name__, self.channel_id)

    def __repr__(self):
        # Have to actually call the method rather than __repr__==__str__
        # because subclasses overload __str__
        return str(self)

    def write_frame(self, stream):
        '''
        Write this frame.
        '''
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = header_frame
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from collections import deque

from haigha.writer import Writer
from haigha.reader import Reader
from haigha.frames.frame import Frame


class HeaderFrame(Frame):

    '''
    Header frame for content.
    '''
    PROPERTIES = [
        ('content_type', 'shortstr', Reader.read_shortstr,
         Writer.write_shortstr, 1 << 15),
        ('content_encoding', 'shortstr', Reader.read_shortstr,
         Writer.write_shortstr, 1 << 14),
        ('application_headers', 'table',
            Reader.read_table, Writer.write_table, 1 << 13),
        ('delivery_mode', 'octet', Reader.read_octet,
            Writer.write_octet, 1 << 12),
        ('priority', 'octet', Reader.read_octet, Writer.write_octet, 1 << 11),
        ('correlation_id', 'shortstr', Reader.read_shortstr,
            Writer.write_shortstr, 1 << 10),
        ('reply_to', 'shortstr', Reader.read_shortstr,
            Writer.write_shortstr, 1 << 9),
        ('expiration', 'shortstr', Reader.read_shortstr,
            Writer.write_shortstr, 1 << 8),
        ('message_id', 'shortstr', Reader.read_shortstr,
            Writer.write_shortstr, 1 << 7),
        ('timestamp', 'timestamp', Reader.read_timestamp,
            Writer.write_timestamp, 1 << 6),
        ('type', 'shortstr', Reader.read_shortstr,
            Writer.write_shortstr, 1 << 5),
        ('user_id', 'shortstr', Reader.read_shortstr,
            Writer.write_shortstr, 1 << 4),
        ('app_id', 'shortstr', Reader.read_shortstr,
            Writer.write_shortstr, 1 << 3),
        ('cluster_id', 'shortstr', Reader.read_shortstr,
            Writer.write_shortstr, 1 << 2)
    ]
    DEFAULT_PROPERTIES = True

    @classmethod
    def type(cls):
        return 2

    @property
    def class_id(self):
        return self._class_id

    @property
    def weight(self):
        return self._weight

    @property
    def size(self):
        return self._size

    @property
    def properties(self):
        return self._properties

    @classmethod
    def parse(self, channel_id, payload):
        '''
        Parse a header frame for a channel given a Reader payload.
        '''
        class_id = payload.read_short()
        weight = payload.read_short()
        size = payload.read_longlong()
        properties = {}

        # The AMQP spec is overly-complex when it comes to handling header
        # frames. The spec says that in addition to the first 16bit field,
        # additional ones can follow which /may/ then be in the property list
        # (because bit flags aren't in the list). Properly implementing custom
        # values requires the ability change the properties and their types,
        # which someone is welcome to do, but seriously, what's the point?
        # Because the complexity of parsing and writing this frame directly
        # impacts the speed at which messages can be processed, there are two
        # branches for both a fast parse which assumes no changes to the
        # properties and a slow parse. For now it's up to someone using custom
        # headers to flip the flag.
        if self.DEFAULT_PROPERTIES:
            flag_bits = payload.read_short()
            for key, proptype, rfunc, wfunc, mask in self.PROPERTIES:
                if flag_bits & mask:
                    properties[key] = rfunc(payload)
        else:
            flags = []
            while True:
                flag_bits = payload.read_short()
                flags.append(flag_bits)
                if flag_bits & 1 == 0:
                    break

            shift = 0
            for key, proptype, rfunc, wfunc, mask in self.PROPERTIES:
                if shift == 0:
                    if not flags:
                        break
                    flag_bits, flags = flags[0], flags[1:]
                    shift = 15
                if flag_bits & (1 << shift):
                    properties[key] = rfunc(payload)
                shift -= 1

        return HeaderFrame(channel_id, class_id, weight, size, properties)

    def __init__(self, channel_id, class_id, weight, size, properties={}):
        Frame.__init__(self, channel_id)
        self._class_id = class_id
        self._weight = weight
        self._size = size
        self._properties = properties

    def __str__(self):
        return "%s[channel: %d, class_id: %d, weight: %d, size: %d, properties: %s]" % (
            self.__class__.__name__, self.channel_id, self._class_id,
            self._weight, self._size, self._properties)

    def write_frame(self, buf):
        '''
        Write the frame into an existing buffer.
        '''
        writer = Writer(buf)
        writer.write_octet(self.type())
        writer.write_short(self.channel_id)

        # Track the position where we're going to write the total length
        # of the frame arguments.
        stream_args_len_pos = len(buf)
        writer.write_long(0)

        stream_method_pos = len(buf)

        writer.write_short(self._class_id)
        writer.write_short(self._weight)
        writer.write_longlong(self._size)

        # Like frame parsing, branch to faster code for default properties
        if self.DEFAULT_PROPERTIES:
            # Track the position where we're going to write the flags.
            flags_pos = len(buf)
            writer.write_short(0)
            flag_bits = 0
            for key, proptype, rfunc, wfunc, mask in self.PROPERTIES:
                val = self._properties.get(key, None)
                if val is not None:
                    flag_bits |= mask
                    wfunc(writer, val)
            writer.write_short_at(flag_bits, flags_pos)
        else:
            shift = 15
            flag_bits = 0
            flags = []
            stack = deque()
            for key, proptype, rfunc, wfunc, mask in self.PROPERTIES:
                val = self._properties.get(key, None)
                if val is not None:
                    if shift == 0:
                        flags.append(flag_bits)
                        flag_bits = 0
                        shift = 15

                    flag_bits |= (1 << shift)
                    stack.append((wfunc, val))

                shift -= 1

            flags.append(flag_bits)
            for flag_bits in flags:
                writer.write_short(flag_bits)
            for method, val in stack:
                method(writer, val)

        # Write the total length back at the beginning of the frame
        stream_len = len(buf) - stream_method_pos
        writer.write_long_at(stream_len, stream_args_len_pos)

        writer.write_octet(0xce)

HeaderFrame.register()

########NEW FILE########
__FILENAME__ = heartbeat_frame
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from haigha.frames.frame import Frame
from haigha.writer import Writer


class HeartbeatFrame(Frame):

    '''
    Frame for heartbeats.
    '''

    @classmethod
    def type(cls):
        # NOTE: The PDF spec say this should be 4 but the xml spec say it
        # should be 8 RabbitMQ seems to implement this as 8, but maybe that's
        # a difference between 0.8 and 0.9 protocols
        # Using Rabbit 2.1.1 and protocol 0.9.1 it seems that 8 is indeed
        # the correct type @AW
        # PDF spec: http://www.amqp.org/confluence/download/attachments/720900/amqp0-9-1.pdf?version=1&modificationDate=1227526523000
        # XML spec: http://www.amqp.org/confluence/download/attachments/720900/amqp0-9-1.xml?version=1&modificationDate=1227526672000
        # This is addressed in
        # http://dev.rabbitmq.com/wiki/Amqp091Errata#section_29
        return 8

    @classmethod
    def parse(self, channel_id, payload):
        return HeartbeatFrame(channel_id)

    def write_frame(self, buf):
        writer = Writer(buf)
        writer.write_octet(self.type())
        writer.write_short(self.channel_id)
        writer.write_long(0)
        writer.write_octet(0xce)

HeartbeatFrame.register()

########NEW FILE########
__FILENAME__ = method_frame
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from haigha.frames.frame import Frame
from haigha.reader import Reader
from haigha.writer import Writer


class MethodFrame(Frame):

    '''
    Frame which carries identifier for methods.
    '''

    @classmethod
    def type(cls):
        return 1

    @property
    def class_id(self):
        return self._class_id

    @property
    def method_id(self):
        return self._method_id

    @property
    def args(self):
        return self._args

    @classmethod
    def parse(self, channel_id, payload):
        class_id = payload.read_short()
        method_id = payload.read_short()
        return MethodFrame(channel_id, class_id, method_id, payload)

    def __init__(self, channel_id, class_id, method_id, args=None):
        Frame.__init__(self, channel_id)
        self._class_id = class_id
        self._method_id = method_id
        self._args = args

    def __str__(self):
        if isinstance(self.args, (Reader, Writer)):
            return "%s[channel: %d, class_id: %d, method_id: %d, args: %s]" %\
                (self.__class__.__name__, self.channel_id,
                 self.class_id, self.method_id, str(self.args))
        else:
            return "%s[channel: %d, class_id: %d, method_id: %d, args: None]" %\
                (self.__class__.__name__, self.channel_id,
                 self.class_id, self.method_id)

    def write_frame(self, buf):
        writer = Writer(buf)
        writer.write_octet(self.type())
        writer.write_short(self.channel_id)

        # Write a temporary value for the total length of the frame
        stream_args_len_pos = len(buf)
        writer.write_long(0)

        # Mark the point in the stream where we start writing arguments,
        # *including* the class and method ids.
        stream_method_pos = len(buf)

        writer.write_short(self.class_id)
        writer.write_short(self.method_id)

        # This is assuming that args is a Writer
        if self._args is not None:
            writer.write(self._args.buffer())

        # Write the total length back at the position we allocated
        stream_len = len(buf) - stream_method_pos
        writer.write_long_at(stream_len, stream_args_len_pos)

        # Write the footer
        writer.write_octet(0xce)


MethodFrame.register()

########NEW FILE########
__FILENAME__ = message
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''


class Message(object):

    '''
    Represents an AMQP message.
    '''

    def __init__(self, body='', delivery_info=None, **properties):
        if isinstance(body, unicode):
            if 'content_encoding' not in properties:
                properties['content_encoding'] = 'utf-8'
            body = body.encode(properties['content_encoding'])

        if not isinstance(body, (str, unicode, bytearray)):
            raise TypeError("Invalid message content type %s" % (type(body)))

        self._body = body
        self._delivery_info = delivery_info
        self._properties = properties

    @property
    def body(self):
        return self._body

    def __len__(self):
        return len(self._body)

    def __nonzero__(self):
        '''Have to define this because length is defined.'''
        return True

    def __eq__(self, other):
        if isinstance(other, Message):
            return self._properties == other._properties and \
                self._body == other._body
        return False

    @property
    def delivery_info(self):
        return self._delivery_info

    @property
    def properties(self):
        return self._properties

    def __str__(self):
        return "Message[body: %s, delivery_info: %s, properties: %s]" %\
            (str(self._body).encode('string_escape'),
             self._delivery_info, self._properties)

########NEW FILE########
__FILENAME__ = reader
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from struct import Struct
from datetime import datetime
from decimal import Decimal


class Reader(object):

    """
    A stream-like reader object that supports all the basic data types of AMQP.
    """

    class ReaderError(Exception):

        '''Base class for all reader errors.'''
    class BufferUnderflow(ReaderError):

        '''Not enough bytes to satisfy the request.'''
    class FieldError(ReaderError):

        '''Unsupported field type was read.'''

    def __init__(self, source, start_pos=0, size=None):
        """
        source should be a bytearray, io object with a read() method, another
        Reader, a plain or unicode string. Can be allocated over a slice
        of source.
        """
        # Note: buffer used here because unpack_from can't accept an array,
        # which I think is related to http://bugs.python.org/issue7827
        if isinstance(source, bytearray):
            self._input = buffer(source)
        elif isinstance(source, Reader):
            self._input = source._input
        elif hasattr(source, 'read'):
            self._input = buffer(source.read())
        elif isinstance(source, str):
            self._input = buffer(source)
        elif isinstance(source, unicode):
            self._input = buffer(source.encode('utf8'))
        else:
            raise ValueError(
                'Reader needs a bytearray, io object or plain string')

        self._start_pos = self._pos = start_pos
        self._end_pos = len(self._input)
        if size:
            self._end_pos = self._start_pos + size

    def __str__(self):
        return ''.join(['\\x%s' % (c.encode('hex')) for c in
                       self._input[self._start_pos:self._end_pos]])

    def tell(self):
        '''
        Current position
        '''
        return self._pos

    def seek(self, offset, whence=0):
        '''
        Simple seek. Follows standard interface.
        '''
        if whence == 0:
            self._pos = self._start_pos + offset
        elif whence == 1:
            self._pos += offset
        else:
            self._pos = (self._end_pos - 1) + offset

    def _check_underflow(self, n):
        '''
        Raise BufferUnderflow if there's not enough bytes to satisfy
        the request.
        '''
        if self._pos + n > self._end_pos:
            raise self.BufferUnderflow()

    def __len__(self):
        '''
        Supports content framing in Channel
        '''
        return self._end_pos - self._start_pos

    def buffer(self):
        '''
        Get a copy of the buffer that this is reading from. Returns a
        buffer object
        '''
        return buffer(self._input, self._start_pos,
                      (self._end_pos - self._start_pos))

    def read(self, n):
        """
        Read n bytes.

        Will raise BufferUnderflow if there's not enough bytes in the buffer.
        """
        self._check_underflow(n)
        rval = self._input[self._pos:self._pos + n]
        self._pos += n
        return rval

    def read_bit(self):
        """
        Read a single boolean value, returns 0 or 1. Convience for single
        bit fields.

        Will raise BufferUnderflow if there's not enough bytes in the buffer.
        """
        # Perform a faster check on underflow
        if self._pos >= self._end_pos:
            raise self.BufferUnderflow()
        result = ord(self._input[self._pos]) & 1
        self._pos += 1
        return result

    def read_bits(self, num):
        '''
        Read several bits packed into the same field. Will return as a list.
        The bit field itself is little-endian, though the order of the
        returned array looks big-endian for ease of decomposition.

        Reader('\x02').read_bits(2) -> [False,True]
        Reader('\x08').read_bits(2) ->
            [False,True,False,False,False,False,False,False]
        first_field, second_field = Reader('\x02').read_bits(2)

        Will raise BufferUnderflow if there's not enough bytes in the buffer.
        Will raise ValueError if num < 0 or num > 9
        '''
        # Perform a faster check on underflow
        if self._pos >= self._end_pos:
            raise self.BufferUnderflow()
        if num < 0 or num >= 9:
            raise ValueError("8 bits per field")
        field = ord(self._input[self._pos])
        result = map(lambda x: field >> x & 1, xrange(num))
        self._pos += 1
        return result

    def read_octet(self, unpacker=Struct('B').unpack_from,
                   size=Struct('B').size):
        """
        Read one byte, return as an integer

        Will raise BufferUnderflow if there's not enough bytes in the buffer.
        Will raise struct.error if the data is malformed
        """
        # Technically should look at unpacker.size, but skipping that is way
        # faster and this method is the most-called of the readers
        if self._pos >= self._end_pos:
            raise self.BufferUnderflow()
        rval = unpacker(self._input, self._pos)[0]
        self._pos += size
        return rval

    def read_short(self, unpacker=Struct('>H').unpack_from,
                   size=Struct('>H').size):
        """
        Read an unsigned 16-bit integer

        Will raise BufferUnderflow if there's not enough bytes in the buffer.
        Will raise struct.error if the data is malformed
        """
        self._check_underflow(size)
        rval = unpacker(self._input, self._pos)[0]
        self._pos += size
        return rval

    def read_long(self, unpacker=Struct('>I').unpack_from,
                  size=Struct('>I').size):
        """
        Read an unsigned 32-bit integer

        Will raise BufferUnderflow if there's not enough bytes in the buffer.
        Will raise struct.error if the data is malformed
        """
        self._check_underflow(size)
        rval = unpacker(self._input, self._pos)[0]
        self._pos += size
        return rval

    def read_longlong(self, unpacker=Struct('>Q').unpack_from,
                      size=Struct('>Q').size):
        """
        Read an unsigned 64-bit integer

        Will raise BufferUnderflow if there's not enough bytes in the buffer.
        Will raise struct.error if the data is malformed
        """
        self._check_underflow(size)
        rval = unpacker(self._input, self._pos)[0]
        self._pos += size
        return rval

    def read_shortstr(self):
        """
        Read a utf-8 encoded string that's stored in up to
        255 bytes.

        Will raise BufferUnderflow if there's not enough bytes in the buffer.
        Will raise UnicodeDecodeError if the text is mal-formed.
        Will raise struct.error if the data is malformed
        """
        slen = self.read_octet()
        return self.read(slen)

    def read_longstr(self):
        """
        Read a string that's up to 2**32 bytes, the encoding
        isn't specified in the AMQP spec, so just return it as
        a plain Python string.

        Will raise BufferUnderflow if there's not enough bytes in the buffer.
        Will raise struct.error if the data is malformed
        """
        slen = self.read_long()
        return self.read(slen)

    def read_timestamp(self):
        """
        Read and AMQP timestamp, which is a 64-bit integer representing
        seconds since the Unix epoch in 1-second resolution.  Return as
        a Python datetime.datetime object, expressed as UTC time.

        Will raise BufferUnderflow if there's not enough bytes in the buffer.
        Will raise struct.error if the data is malformed
        """
        return datetime.utcfromtimestamp(self.read_longlong())

    def read_table(self):
        """
        Read an AMQP table, and return as a Python dictionary.

        Will raise BufferUnderflow if there's not enough bytes in the buffer.
        Will raise UnicodeDecodeError if the text is mal-formed.
        Will raise struct.error if the data is malformed
        """
        # Only need to check underflow on the table once
        tlen = self.read_long()
        self._check_underflow(tlen)
        end_pos = self._pos + tlen
        result = {}
        while self._pos < end_pos:
            name = self._field_shortstr()
            result[name] = self._read_field()
        return result

    def _read_field(self):
        '''
        Read a single byte for field type, then read the value.
        '''
        ftype = self._input[self._pos]
        self._pos += 1

        reader = self.field_type_map.get(ftype)
        if reader:
            return reader(self)

        raise Reader.FieldError('Unknown field type %s', ftype)

    def _field_bool(self):
        result = ord(self._input[self._pos]) & 1
        self._pos += 1
        return result

    def _field_short_short_int(self, unpacker=Struct('b').unpack_from,
                               size=Struct('b').size):
        rval = unpacker(self._input, self._pos)[0]
        self._pos += size
        return rval

    def _field_short_short_uint(self, unpacker=Struct('B').unpack_from,
                                size=Struct('B').size):
        rval = unpacker(self._input, self._pos)[0]
        self._pos += size
        return rval

    def _field_short_int(self, unpacker=Struct('>h').unpack_from,
                         size=Struct('>h').size):
        rval = unpacker(self._input, self._pos)[0]
        self._pos += size
        return rval

    def _field_short_uint(self, unpacker=Struct('>H').unpack_from,
                          size=Struct('>H').size):
        rval = unpacker(self._input, self._pos)[0]
        self._pos += size
        return rval

    def _field_long_int(self, unpacker=Struct('>i').unpack_from,
                        size=Struct('>i').size):
        rval = unpacker(self._input, self._pos)[0]
        self._pos += size
        return rval

    def _field_long_uint(self, unpacker=Struct('>I').unpack_from,
                         size=Struct('>I').size):
        rval = unpacker(self._input, self._pos)[0]
        self._pos += size
        return rval

    def _field_long_long_int(self, unpacker=Struct('>q').unpack_from,
                             size=Struct('>q').size):
        rval = unpacker(self._input, self._pos)[0]
        self._pos += size
        return rval

    def _field_long_long_uint(self, unpacker=Struct('>Q').unpack_from,
                              size=Struct('>Q').size):
        rval = unpacker(self._input, self._pos)[0]
        self._pos += size
        return rval

    def _field_float(self, unpacker=Struct('>f').unpack_from,
                     size=Struct('>f').size):
        rval = unpacker(self._input, self._pos)[0]
        self._pos += size
        return rval

    def _field_double(self, unpacker=Struct('>d').unpack_from,
                      size=Struct('>d').size):
        rval = unpacker(self._input, self._pos)[0]
        self._pos += size
        return rval

    # Coding to http://dev.rabbitmq.com/wiki/Amqp091Errata#section_3 which
    # differs from spec in that the value is signed.
    def _field_decimal(self):
        d = self._field_short_short_uint()
        n = self._field_long_int()
        return Decimal(n) / Decimal(10 ** d)

    def _field_shortstr(self):
        slen = self._field_short_short_uint()
        rval = self._input[self._pos:self._pos + slen]
        self._pos += slen
        return rval

    def _field_longstr(self):
        slen = self._field_long_uint()
        rval = self._input[self._pos:self._pos + slen]
        self._pos += slen
        return rval

    def _field_array(self):
        alen = self.read_long()
        end_pos = self._pos + alen
        rval = []
        while self._pos < end_pos:
            rval.append(self._read_field())
        return rval

    def _field_timestamp(self):
        """
        Read and AMQP timestamp, which is a 64-bit integer representing
        seconds since the Unix epoch in 1-second resolution.  Return as
        a Python datetime.datetime object, expressed as UTC time.

        Will raise BufferUnderflow if there's not enough bytes in the buffer.
        Will raise struct.error if the data is malformed
        """
        return datetime.utcfromtimestamp(self._field_long_long_uint())

    def _field_bytearray(self):
        slen = self._field_long_uint()
        rval = bytearray(self._input[self._pos:self._pos + slen])
        self._pos += slen
        return rval

    def _field_none(self):
        return None

    # A mapping for quick lookups
    # Rabbit and Qpid 0.9.1 mapping
    # Based on: http://www.rabbitmq.com/amqp-0-9-1-errata.html (3. Field types)
    field_type_map = {
        't': _field_bool,
        'b': _field_short_short_int,
        's': _field_short_int,
        'I': _field_long_int,
        'l': _field_long_long_int,
        'f': _field_float,
        'd': _field_double,
        'D': _field_decimal,
        'S': _field_longstr,
        'A': _field_array,
        'T': _field_timestamp,
        'F': read_table,
        'V': _field_none,
        'x': _field_bytearray,
    }

    # 0.9.1 spec mapping
    #  field_type_map = {
    #   't' : _field_bool,
    #   'b' : _field_short_short_int,
    #   'B' : _field_short_short_uint,
    #   'U' : _field_short_int,
    #   'u' : _field_short_uint,
    #   'I' : _field_long_int,
    #   'i' : _field_long_uint,
    #   'L' : _field_long_long_int,
    #   'l' : _field_long_long_uint,
    #   'f' : _field_float,
    #   'd' : _field_double,
    #   'D' : _field_decimal,
    #   's' : _field_shortstr,
    #   'S' : _field_longstr,
    #   'A' : _field_array,
    #   'T' : _field_timestamp,
    #   'F' : read_table,
    #   'V' : _field_none,
    # }

########NEW FILE########
__FILENAME__ = event_transport
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

import warnings

from haigha.transports.transport import Transport

try:
    from eventsocket import EventSocket
    import event
except ImportError:
    warnings.warn('Failed to load EventSocket and event modules')
    EventSocket = None
    event = None


class EventTransport(Transport):

    '''
    Transport using libevent-based EventSocket.
    '''

    def __init__(self, *args):
        super(EventTransport, self).__init__(*args)
        self._synchronous = False

    ###
    # EventSocket callbacks
    ###
    def _sock_close_cb(self, sock):
        self._connection.transport_closed(
            msg='socket to %s closed unexpectedly' % (self._host),
        )

    def _sock_error_cb(self, sock, msg, exception=None):
        self._connection.transport_closed(
            msg='error on connection to %s: %s' % (self._host, msg)
        )

    def _sock_read_cb(self, sock):
        self.connection.read_frames()

    ###
    # Transport API
    ###
    def connect(self, (host, port)):
        '''
        Connect assuming a host and port tuple. Implemented as non-blocking,
        and will close the transport if there's an error
        '''
        self._host = "%s:%s" % (host, port)
        self._sock = EventSocket(
            read_cb=self._sock_read_cb,
            close_cb=self._sock_close_cb,
            error_cb=self._sock_error_cb,
            debug=self.connection.debug,
            logger=self.connection.logger)
        if self.connection._sock_opts:
            for k, v in self.connection._sock_opts.iteritems():
                family, type = k
                self._sock.setsockopt(family, type, v)
        self._sock.setblocking(False)
        self._sock.connect(
            (host, port), timeout=self.connection._connect_timeout)
        self._heartbeat_timeout = None

    def read(self, timeout=None):
        '''
        Read from the transport. If no data is available, should return None.
        The timeout is ignored as this returns only data that has already
        been buffered locally.
        '''
        # NOTE: copying over this comment from Connection, because there is
        # knowledge captured here, even if the details are stale
        # Because of the timer callback to dataRead when we re-buffered,
        # there's a chance that in between we've lost the socket. If that's
        # the case, just silently return as some code elsewhere would have
        # already notified us. That bug could be fixed by improving the
        # message reading so that we consume all possible messages and ensure
        # that only a partial message was rebuffered, so that we can rely on
        # the next read event to read the subsequent message.
        if not hasattr(self, '_sock'):
            return None

        # This is sort of a hack because we're faking that data is ready, but
        # it works for purposes of supporting timeouts
        if timeout:
            if self._heartbeat_timeout:
                self._heartbeat_timeout.delete()
            self._heartbeat_timeout = \
                event.timeout(timeout, self._sock_read_cb, self._sock)
        elif self._heartbeat_timeout:
            self._heartbeat_timeout.delete()
            self._heartbeat_timeout = None

        return self._sock.read()

    def buffer(self, data):
        '''
        Buffer unused bytes from the input stream.
        '''
        if not hasattr(self, '_sock'):
            return None
        self._sock.buffer(data)

    def write(self, data):
        '''
        Write some bytes to the transport.
        '''
        if not hasattr(self, '_sock'):
            return
        self._sock.write(data)

    def disconnect(self):
        '''
        Disconnect from the transport. Typically socket.close(). This call is
        welcome to raise exceptions, which the Connection will catch.

        The transport is encouraged to allow for any pending writes to complete
        before closing the socket.
        '''
        if not hasattr(self, '_sock'):
            return

        # TODO: If there are bytes left on the output, queue the close for
        # later.
        self._sock.close_cb = None
        self._sock.close()

########NEW FILE########
__FILENAME__ = gevent_transport
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

import warnings

from haigha.transports.socket_transport import SocketTransport

try:
    import gevent
    from gevent.event import Event
    try:
        # Semaphore moved here since gevent-1.0b2
        from gevent.lock import Semaphore
    except ImportError:
        from gevent.coros import Semaphore
    from gevent import socket
    from gevent import pool
except ImportError:
    warnings.warn('Failed to load gevent modules')
    gevent = None
    Event = None
    Semaphore = None
    socket = None
    pool = None


class GeventTransport(SocketTransport):

    '''
    Transport using gevent backend. It relies on gevent's implementation of
    sendall to send whole frames at a time. On the input side, it uses a gevent
    semaphore to ensure exclusive access to the socket and input buffer.
    '''

    def __init__(self, *args, **kwargs):
        super(GeventTransport, self).__init__(*args)

        self._synchronous = False
        self._read_lock = Semaphore()
        self._write_lock = Semaphore()
        self._read_wait = Event()

    ###
    # Transport API
    ###

    def connect(self, (host, port)):
        '''
        Connect using a host,port tuple
        '''
        super(GeventTransport, self).connect((host, port), klass=socket.socket)

    def read(self, timeout=None):
        '''
        Read from the transport. If no data is available, should return None.
        If timeout>0, will only block for `timeout` seconds.
        '''
        # If currently locked, another greenlet is trying to read, so yield
        # control and then return none. Required if a Connection is configured
        # to be synchronous, a sync callback is trying to read, and there's
        # another read loop running read_frames. Without it, the run loop will
        # release the lock but then immediately acquire it again. Yielding
        # control in the reading thread after bytes are read won't fix
        # anything, because it's quite possible the bytes read resulted in a
        # frame that satisfied the synchronous callback, and so this needs to
        # return immediately to first check the current status of synchronous
        # callbacks before attempting to read again.
        if self._read_lock.locked():
            self._read_wait.wait(timeout)
            return None

        self._read_lock.acquire()
        try:
            return super(GeventTransport, self).read(timeout=timeout)
        finally:
            self._read_lock.release()
            self._read_wait.set()
            self._read_wait.clear()

    def buffer(self, data):
        '''
        Buffer unused bytes from the input stream.
        '''
        self._read_lock.acquire()
        try:
            return super(GeventTransport, self).buffer(data)
        finally:
            self._read_lock.release()

    def write(self, data):
        '''
        Write some bytes to the transport.
        '''
        # MUST use a lock here else gevent could raise an exception if 2
        # greenlets try to write at the same time. I was hoping that
        # sendall() would do that blocking for me, but I guess not. May
        # require an eventsocket-like buffer to speed up under high load.
        self._write_lock.acquire()
        try:
            return super(GeventTransport, self).write(data)
        finally:
            self._write_lock.release()


class GeventPoolTransport(GeventTransport):

    def __init__(self, *args, **kwargs):
        super(GeventPoolTransport, self).__init__(*args)

        self._pool = kwargs.get('pool', None)
        if not self._pool:
            self._pool = gevent.pool.Pool()

    @property
    def pool(self):
        '''Get a handle to the gevent pool.'''
        return self._pool

    def process_channels(self, channels):
        '''
        Process a set of channels by calling Channel.process_frames() on each.
        Some transports may choose to do this in unique ways, such as through
        a pool of threads.

        The default implementation will simply iterate over them and call
        process_frames() on each.
        '''
        for channel in channels:
            self._pool.spawn(channel.process_frames)

########NEW FILE########
__FILENAME__ = socket_transport
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from haigha.transports.transport import Transport

import errno
import socket


class SocketTransport(Transport):

    '''
    A simple blocking socket transport.
    '''

    def __init__(self, *args):
        super(SocketTransport, self).__init__(*args)
        self._synchronous = True
        self._buffer = bytearray()

    ###
    # Transport API
    ###
    def connect(self, (host, port), klass=socket.socket):
        '''
        Connect assuming a host and port tuple.
        '''
        self._host = "%s:%s" % (host, port)
        self._sock = klass()
        self._sock.setblocking(True)
        self._sock.settimeout(self.connection._connect_timeout)
        if self.connection._sock_opts:
            for k, v in self.connection._sock_opts.iteritems():
                family, type = k
                self._sock.setsockopt(family, type, v)
        self._sock.connect((host, port))

        # After connecting, switch to full-blocking mode.
        self._sock.settimeout(None)

    def read(self, timeout=None):
        '''
        Read from the transport. If timeout>0, will only block for `timeout`
        seconds.
        '''
        e = None
        if not hasattr(self, '_sock'):
            return None

        try:
            # Note that we ignore both None and 0, i.e. we either block with a
            # timeout or block completely and let gevent sort it out.
            if timeout:
                self._sock.settimeout(timeout)
            else:
                self._sock.settimeout(None)
            data = self._sock.recv(
                self._sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF))

            if len(data):
                if self.connection.debug > 1:
                    self.connection.logger.debug(
                        'read %d bytes from %s' % (len(data), self._host))
                if len(self._buffer):
                    self._buffer.extend(data)
                    data = self._buffer
                    self._buffer = bytearray()
                return data

            # Note that no data means the socket is closed and we'll mark that
            # below

        except socket.timeout as e:
            # Note that this is implemented differently and though it would be
            # caught as an EnvironmentError, it has no errno. Not sure whose
            # fault that is.
            return None

        except EnvironmentError as e:
            # thrown if we have a timeout and no data
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EINTR):
                return None

            self.connection.logger.exception(
                'error reading from %s' % (self._host))

        self.connection.transport_closed(
            msg='error reading from %s' % (self._host))
        if e:
            raise

    def buffer(self, data):
        '''
        Buffer unused bytes from the input stream.
        '''
        if not hasattr(self, '_sock'):
            return None

        # data will always be a byte array
        if len(self._buffer):
            self._buffer.extend(data)
        else:
            self._buffer = bytearray(data)

    def write(self, data):
        '''
        Write some bytes to the transport.
        '''
        if not hasattr(self, '_sock'):
            return None

        try:
            self._sock.sendall(data)

            if self.connection.debug > 1:
                self.connection.logger.debug(
                    'sent %d bytes to %s' % (len(data), self._host))

            return
        except EnvironmentError:
            # sockets raise this type of error, and since if sendall() fails
            # we're left in an indeterminate state, assume that any error we
            # catch means that the connection is dead. Note that this
            # assumption requires this to be a blocking socket; if we ever
            # support non-blocking in this class then this whole method has
            # to change a lot.
            self.connection.logger.exception(
                'error writing to %s' % (self._host))

        self.connection.transport_closed(
            msg='error writing to %s' % (self._host))

    def disconnect(self):
        '''
        Disconnect from the transport. Typically socket.close(). This call is
        welcome to raise exceptions, which the Connection will catch.
        '''
        if not hasattr(self, '_sock'):
            return None

        try:
            self._sock.close()
        finally:
            self._sock = None

########NEW FILE########
__FILENAME__ = transport
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''


class Transport(object):

    '''
    Base class and API for Transports
    '''

    def __init__(self, connection):
        '''
        Initialize a transport on a haigha.Connection instance.
        '''
        self._connection = connection

    @property
    def synchronous(self):
        '''Return True if this is a synchronous transport, False otherwise.'''
        # Note that subclasses must define this.
        return self._synchronous

    @property
    def connection(self):
        return self._connection

    def process_channels(self, channels):
        '''
        Process a set of channels by calling Channel.process_frames() on each.
        Some transports may choose to do this in unique ways, such as through
        a pool of threads.

        The default implementation will simply iterate over them and call
        process_frames() on each.
        '''
        for channel in channels:
            channel.process_frames()

    def read(self, timeout=None):
        '''
        Read from the transport. If no data is available, should return None.
        The return value can be any data type that is supported by the
        haigha.Reader class.

        Caller passes in an optional timeout. Each transport determines how to
        implement this.
        '''
        return None

    def buffer(self, data):
        '''
        Buffer unused bytes from the input stream.
        '''

    def write(self, data):
        '''
        Write some bytes to the transport.
        '''

    def disconnect(self):
        '''
        Disconnect from the transport. Typically socket.close(). This call is
        welcome to raise exceptions, which the Connection will catch.

        The transport is encouraged to allow for any pending writes to complete
        before closing the socket.
        '''

########NEW FILE########
__FILENAME__ = writer
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from struct import Struct
from calendar import timegm
from datetime import datetime
from decimal import Decimal
from operator import xor


class Writer(object):

    """
    Implements writing of structured AMQP data. Buffers data directly to a
    bytearray or a buffer supplied in the constructor. The buffer must
    supply append, extend and struct.pack_into semantics.
    """

    def __init__(self, buf=None):
        if buf is not None:
            self._output_buffer = buf
        else:
            self._output_buffer = bytearray()

    def __str__(self):
        return ''.join([
            '\\x%s' % (chr(c).encode('hex')) for c in self._output_buffer])

    __repr__ = __str__

    def __eq__(self, other):
        if isinstance(other, Writer):
            return self._output_buffer == other._output_buffer
        return False

    def buffer(self):
        '''
        Get the buffer that this has written to. Returns bytearray.
        '''
        return self._output_buffer

    def write(self, s):
        """
        Write a plain Python string, with no special encoding.
        """
        self._output_buffer.extend(s)
        return self

    def write_bits(self, *args):
        '''
        Write multiple bits in a single byte field. The bits will be written in
        little-endian order, but should be supplied in big endian order. Will
        raise ValueError when more than 8 arguments are supplied.

        write_bits(True, False) => 0x02
        '''
        # Would be nice to make this a bit smarter
        if len(args) > 8:
            raise ValueError("Can only write 8 bits at a time")

        self._output_buffer.append(chr(
            reduce(lambda x, y: xor(x, args[y] << y), xrange(len(args)), 0)))

        return self

    def write_bit(self, b, pack=Struct('B').pack):
        '''
        Write a single bit. Convenience method for single bit args.
        '''
        self._output_buffer.append(pack(True if b else False))
        return self

    def write_octet(self, n, pack=Struct('B').pack):
        """
        Write an integer as an unsigned 8-bit value.
        """
        if 0 <= n <= 255:
            self._output_buffer.append(pack(n))
        else:
            raise ValueError('Octet %d out of range 0..255', n)
        return self

    def write_short(self, n, pack=Struct('>H').pack):
        """
        Write an integer as an unsigned 16-bit value.
        """
        if 0 <= n <= 0xFFFF:
            self._output_buffer.extend(pack(n))
        else:
            raise ValueError('Short %d out of range 0..0xFFFF', n)
        return self

    def write_short_at(self, n, pos, pack_into=Struct('>H').pack_into):
        '''
        Write an unsigned 16bit value at a specific position in the buffer.
        Used for writing tables and frames.
        '''
        if 0 <= n <= 0xFFFF:
            pack_into(self._output_buffer, pos, n)
        else:
            raise ValueError('Short %d out of range 0..0xFFFF', n)
        return self

    def write_long(self, n, pack=Struct('>I').pack):
        """
        Write an integer as an unsigned 32-bit value.
        """
        if 0 <= n <= 0xFFFFFFFF:
            self._output_buffer.extend(pack(n))
        else:
            raise ValueError('Long %d out of range 0..0xFFFFFFFF', n)
        return self

    def write_long_at(self, n, pos, pack_into=Struct('>I').pack_into):
        '''
        Write an unsigned 32bit value at a specific position in the buffer.
        Used for writing tables and frames.
        '''
        if 0 <= n <= 0xFFFFFFFF:
            pack_into(self._output_buffer, pos, n)
        else:
            raise ValueError('Long %d out of range 0..0xFFFFFFFF', n)
        return self

    def write_longlong(self, n, pack=Struct('>Q').pack):
        """
        Write an integer as an unsigned 64-bit value.
        """
        if 0 <= n <= 0xFFFFFFFFFFFFFFFF:
            self._output_buffer.extend(pack(n))
        else:
            raise ValueError(
                'Longlong %d out of range 0..0xFFFFFFFFFFFFFFFF', n)
        return self

    def write_shortstr(self, s):
        """
        Write a string up to 255 bytes long after encoding.  If passed
        a unicode string, encode as UTF-8.
        """
        if isinstance(s, unicode):
            s = s.encode('utf-8')
        self.write_octet(len(s))
        self.write(s)
        return self

    def write_longstr(self, s):
        """
        Write a string up to 2**32 bytes long after encoding.  If passed
        a unicode string, encode as UTF-8.
        """
        if isinstance(s, unicode):
            s = s.encode('utf-8')
        self.write_long(len(s))
        self.write(s)
        return self

    def write_timestamp(self, t, pack=Struct('>Q').pack):
        """
        Write out a Python datetime.datetime object as a 64-bit integer
        representing seconds since the Unix UTC epoch.
        """
        # Double check timestamp, can't imagine why it would be signed
        self._output_buffer.extend(pack(long(timegm(t.timetuple()))))
        return self

    # NOTE: coding to http://dev.rabbitmq.com/wiki/Amqp091Errata#section_3 and
    # NOT spec 0.9.1. It seems that Rabbit and other brokers disagree on this
    # section for now.
    def write_table(self, d):
        """
        Write out a Python dictionary made of up string keys, and values
        that are strings, signed integers, Decimal, datetime.datetime, or
        sub-dictionaries following the same constraints.
        """
        # HACK: encoding of AMQP tables is broken because it requires the
        # length of the /encoded/ data instead of the number of items. To
        # support streaming, fiddle with cursor position, rewinding to write
        # the real length of the data. Generally speaking, I'm not a fan of
        # the AMQP encoding scheme, it could be much faster.
        table_len_pos = len(self._output_buffer)
        self.write_long(0)
        table_data_pos = len(self._output_buffer)

        for key, value in d.iteritems():
            self._write_item(key, value)

        table_end_pos = len(self._output_buffer)
        table_len = table_end_pos - table_data_pos

        self.write_long_at(table_len, table_len_pos)
        return self

    def _write_item(self, key, value):
        self.write_shortstr(key)
        self._write_field(value)

    def _write_field(self, value):
        writer = self.field_type_map.get(type(value))
        if writer:
            writer(self, value)
        else:
            for kls, writer in self.field_type_map.items():
                if isinstance(value, kls):
                    writer(self, value)
                    break
            else:
                # Write a None because we've already written a key
                self._field_none(value)

    def _field_bool(self, val, pack=Struct('B').pack):
        self._output_buffer.append('t')
        self._output_buffer.append(pack(True if val else False))

    def _field_int(self, val, short_pack=Struct('>h').pack,
                   int_pack=Struct('>i').pack, long_pack=Struct('>q').pack):
        if -2 ** 15 <= val < 2 ** 15:
            self._output_buffer.append('s')
            self._output_buffer.extend(short_pack(val))
        elif -2 ** 31 <= val < 2 ** 31:
            self._output_buffer.append('I')
            self._output_buffer.extend(int_pack(val))
        else:
            self._output_buffer.append('l')
            self._output_buffer.extend(long_pack(val))

    def _field_double(self, val, pack=Struct('>d').pack):
        self._output_buffer.append('d')
        self._output_buffer.extend(pack(val))

    # Coding to http://dev.rabbitmq.com/wiki/Amqp091Errata#section_3 which
    # differs from spec in that the value is signed.
    def _field_decimal(self, val, exp_pack=Struct('B').pack,
                       dig_pack=Struct('>i').pack):
        self._output_buffer.append('D')
        sign, digits, exponent = val.as_tuple()
        v = 0
        for d in digits:
            v = (v * 10) + d
        if sign:
            v = -v
        self._output_buffer.append(exp_pack(-exponent))
        self._output_buffer.extend(dig_pack(v))

    def _field_str(self, val):
        self._output_buffer.append('S')
        self.write_longstr(val)

    def _field_unicode(self, val):
        val = val.encode('utf-8')
        self._output_buffer.append('S')
        self.write_longstr(val)

    def _field_timestamp(self, val):
        self._output_buffer.append('T')
        self.write_timestamp(val)

    def _field_table(self, val):
        self._output_buffer.append('F')
        self.write_table(val)

    def _field_none(self, val):
        self._output_buffer.append('V')

    def _field_bytearray(self, val):
        self._output_buffer.append('x')
        self.write_longstr(val)

    def _field_iterable(self, val):
        self._output_buffer.append('A')
        for x in val:
            self._write_field(x)

    field_type_map = {
        bool: _field_bool,
        int: _field_int,
        long: _field_int,
        float: _field_double,
        Decimal: _field_decimal,
        str: _field_str,
        unicode: _field_unicode,
        datetime: _field_timestamp,
        dict: _field_table,
        type(None): _field_none,
        bytearray: _field_bytearray,
    }

    # 0.9.1 spec mapping
    # field_type_map = {
    #   bool      : _field_bool,
    #   int       : _field_int,
    #   long      : _field_int,
    #   float     : _field_double,
    #   Decimal   : _field_decimal,
    #   str       : _field_str,
    #   unicode   : _field_unicode,
    #   datetime  : _field_timestamp,
    #   dict      : _field_table,
    #   None      : _field_none,
    #   bytearray : _field_bytearray,
    #   list      : _field_iterable,
    #   tuple     : _field_iterable,
    #   set       : _field_iterable,
    # }

########NEW FILE########
__FILENAME__ = channel_pool_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from collections import deque

from chai import Chai

from haigha.channel_pool import ChannelPool


class ChannelPoolTest(Chai):

    def test_init(self):
        c = ChannelPool('connection')
        self.assertEquals('connection', c._connection)
        self.assertEquals(set(), c._free_channels)
        assert_equals(None, c._size)
        assert_equals(0, c._channels)
        assert_equals(deque(), c._queue)

        c = ChannelPool('connection', size=50)
        self.assertEquals('connection', c._connection)
        self.assertEquals(set(), c._free_channels)
        assert_equals(50, c._size)
        assert_equals(0, c._channels)
        assert_equals(deque(), c._queue)

    def test_publish_without_user_cb(self):
        ch = mock()
        cp = ChannelPool(None)

        expect(cp._get_channel).returns(ch)
        expect(ch.publish_synchronous).args(
            'arg1', 'arg2', cb=var('cb'), doit='harder')

        cp.publish('arg1', 'arg2', doit='harder')
        assert_equals(set(), cp._free_channels)

        # run committed callback
        var('cb').value()
        assert_equals(set([ch]), cp._free_channels)

    def test_publish_with_user_cb(self):
        ch = mock()
        cp = ChannelPool(None)
        user_cb = mock()

        expect(cp._get_channel).returns(ch)
        expect(ch.publish_synchronous).args(
            'arg1', 'arg2', cb=var('cb'), doit='harder')

        cp.publish('arg1', 'arg2', cb=user_cb, doit='harder')
        assert_equals(set(), cp._free_channels)

        expect(user_cb)
        var('cb').value()
        assert_equals(set([ch]), cp._free_channels)

    def test_publish_resends_queued_messages_if_channel_is_active(self):
        ch = mock()
        cp = ChannelPool(None)
        user_cb = mock()
        ch.active = True
        ch.closed = False
        cp._queue.append((('a1', 'a2'), {'cb': 'foo', 'yo': 'dawg'}))

        expect(cp._get_channel).returns(ch)
        expect(ch.publish_synchronous).args(
            'arg1', 'arg2', cb=var('cb'), doit='harder')

        cp.publish('arg1', 'arg2', cb=user_cb, doit='harder')
        assert_equals(set(), cp._free_channels)
        assert_equals(1, len(cp._queue))

        expect(cp._process_queue)
        expect(user_cb)
        var('cb').value()
        assert_equals(set([ch]), cp._free_channels)

    def test_publish_does_not_resend_queued_messages_if_channel_is_inactive(self):
        ch = mock()
        cp = ChannelPool(None)
        user_cb = mock()
        ch.active = True
        ch.closed = False
        cp._queue.append((('a1', 'a2'), {'cb': 'foo', 'yo': 'dawg'}))

        expect(cp._get_channel).returns(ch)
        expect(ch.publish_synchronous).args(
            'arg1', 'arg2', cb=var('cb'), doit='harder')

        cp.publish('arg1', 'arg2', cb=user_cb, doit='harder')
        assert_equals(set(), cp._free_channels)
        assert_equals(1, len(cp._queue))

        ch.active = False

        stub(cp._process_queue)
        expect(user_cb)
        var('cb').value()
        assert_equals(set([ch]), cp._free_channels)
        assert_equals(1, len(cp._queue))

    def test_publish_does_not_resend_queued_messages_if_channel_is_closed(self):
        ch = mock()
        cp = ChannelPool(None)
        user_cb = mock()
        ch.active = True
        ch.closed = False
        cp._queue.append((('a1', 'a2'), {'cb': 'foo', 'yo': 'dawg'}))

        expect(cp._get_channel).returns(ch)
        expect(ch.publish_synchronous).args(
            'arg1', 'arg2', cb=var('cb'), doit='harder')

        cp.publish('arg1', 'arg2', cb=user_cb, doit='harder')
        assert_equals(set(), cp._free_channels)
        assert_equals(1, len(cp._queue))

        ch.closed = True
        stub(cp._process_queue)
        expect(user_cb)
        var('cb').value()
        assert_equals(set([ch]), cp._free_channels)
        assert_equals(1, len(cp._queue))

    def test_publish_searches_for_active_channel(self):
        ch1 = mock()
        ch2 = mock()
        ch3 = mock()
        ch1.active = ch2.active = False
        ch3.active = True
        cp = ChannelPool(None)

        expect(cp._get_channel).returns(ch1)
        expect(cp._get_channel).returns(ch2)
        expect(cp._get_channel).returns(ch3)
        expect(ch3.publish_synchronous).args('arg1', 'arg2', cb=ignore())

        cp.publish('arg1', 'arg2')
        self.assertEquals(set([ch1, ch2]), cp._free_channels)

    def test_publish_appends_to_queue_when_no_ready_channels(self):
        cp = ChannelPool(None)

        expect(cp._get_channel).returns(None)

        cp.publish('arg1', 'arg2', arg3='foo', cb='usercb')
        self.assertEquals(set(), cp._free_channels)
        assert_equals(deque([(('arg1', 'arg2'), {'arg3': 'foo', 'cb': 'usercb'})]),
                      cp._queue)

    def test_publish_appends_to_queue_when_no_ready_channels_out_of_several(self):
        ch1 = mock()
        cp = ChannelPool(None)
        ch1.active = False

        expect(cp._get_channel).returns(ch1)
        expect(cp._get_channel).returns(None)

        cp.publish('arg1', 'arg2', arg3='foo', cb='usercb')
        self.assertEquals(set([ch1]), cp._free_channels)
        assert_equals(deque([(('arg1', 'arg2'), {'arg3': 'foo', 'cb': 'usercb'})]),
                      cp._queue)

    def test_process_queue(self):
        cp = ChannelPool(None)
        cp._queue = deque([
            (('foo',), {'a': 1}),
            (('bar',), {'b': 2}),
        ])
        expect(cp.publish).args('foo', a=1)
        expect(cp.publish).args('bar', b=2)

        cp._process_queue()
        cp._process_queue()
        cp._process_queue()

    def test_get_channel_returns_new_when_none_free_and_not_at_limit(self):
        conn = mock()
        cp = ChannelPool(conn)
        cp._channels = 1

        with expect(conn.channel).returns(mock()) as newchannel:
            expect(newchannel.add_close_listener).args(cp._channel_closed_cb)
            self.assertEquals(newchannel, cp._get_channel())
        self.assertEquals(set(), cp._free_channels)
        assert_equals(2, cp._channels)

    def test_get_channel_returns_new_when_none_free_and_at_limit(self):
        conn = mock()
        cp = ChannelPool(conn, 1)
        cp._channels = 1

        stub(conn.channel)

        self.assertEquals(None, cp._get_channel())
        self.assertEquals(set(), cp._free_channels)

    def test_get_channel_when_one_free_and_not_closed(self):
        conn = mock()
        ch = mock()
        ch.closed = False
        cp = ChannelPool(conn)
        cp._free_channels = set([ch])

        self.assertEquals(ch, cp._get_channel())
        self.assertEquals(set(), cp._free_channels)

    def test_get_channel_when_two_free_and_one_closed(self):
        # Because we can't mock builtins ....
        class Set(set):

            def pop(self):
                pass

        conn = mock()
        ch1 = mock()
        ch1.closed = True
        ch2 = mock()
        ch2.closed = False
        cp = ChannelPool(conn)
        cp._free_channels = Set([ch1, ch2])
        cp._channels = 2

        # Because we want them in order
        expect(cp._free_channels.pop).returns(
            ch1).side_effect(super(Set, cp._free_channels).pop)
        expect(cp._free_channels.pop).returns(
            ch2).side_effect(super(Set, cp._free_channels).pop)

        self.assertEquals(ch2, cp._get_channel())
        self.assertEquals(set(), cp._free_channels)
        assert_equals(2, cp._channels)

    def test_get_channel_when_two_free_and_all_closed(self):
        conn = mock()
        ch1 = mock()
        ch1.closed = True
        ch2 = mock()
        ch2.closed = True
        cp = ChannelPool(conn)
        cp._free_channels = set([ch1, ch2])
        cp._channels = 2

        with expect(conn.channel).returns(mock()) as newchannel:
            expect(newchannel.add_close_listener).args(cp._channel_closed_cb)
            self.assertEquals(newchannel, cp._get_channel())

        self.assertEquals(set(), cp._free_channels)
        assert_equals(3, cp._channels)

    def test_channel_closed_cb(self):
        cp = ChannelPool(None)
        cp._channels = 32

        expect(cp._process_queue)
        cp._channel_closed_cb('channel')
        assert_equals(31, cp._channels)

########NEW FILE########
__FILENAME__ = channel_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai
from collections import deque

from haigha import channel
from haigha.channel import Channel, SyncWrapper
from haigha.exceptions import ChannelError, ChannelClosed, ConnectionClosed
from haigha.classes.basic_class import BasicClass
from haigha.classes.channel_class import ChannelClass
from haigha.classes.exchange_class import ExchangeClass
from haigha.classes.queue_class import QueueClass
from haigha.classes.transaction_class import TransactionClass
from haigha.classes.protocol_class import ProtocolClass
from haigha.frames.method_frame import MethodFrame
from haigha.frames.heartbeat_frame import HeartbeatFrame
from haigha.frames.header_frame import HeaderFrame
from haigha.frames.content_frame import ContentFrame


class SyncWrapperTest(Chai):

    def test_init(self):
        s = SyncWrapper('cb')
        assert_equals('cb', s._cb)
        assert_true(s._read)
        assert_equals(None, s._result)

    def test_eq_when_other_is_same_cb(self):
        s = SyncWrapper('cb')
        assert_equals('cb', s)
        assert_not_equals('bb', s)

    def test_eq_when_other_has_same_cb(self):
        s = SyncWrapper('cb')
        other = SyncWrapper('cb')
        another = SyncWrapper('bb')

        assert_equals(s, other)
        assert_not_equals(s, another)

    def test_call(self):
        cb = mock()
        s = SyncWrapper(cb)

        expect(cb).args('foo', 'bar', hello='mars')
        s('foo', 'bar', hello='mars')
        assert_false(s._read)


class ChannelTest(Chai):

    def test_init(self):
        c = Channel('connection', 'id', {
            20: ChannelClass,
            40: ExchangeClass,
            50: QueueClass,
            60: BasicClass,
            90: TransactionClass,
        })
        assert_equals('connection', c._connection)
        assert_equals('id', c._channel_id)
        assert_true(isinstance(c.channel, ChannelClass))
        assert_true(isinstance(c.exchange, ExchangeClass))
        assert_true(isinstance(c.queue, QueueClass))
        assert_true(isinstance(c.basic, BasicClass))
        assert_true(isinstance(c.tx, TransactionClass))
        assert_false(c._synchronous)
        assert_equals(c._class_map[20], c.channel)
        assert_equals(c._class_map[40], c.exchange)
        assert_equals(c._class_map[50], c.queue)
        assert_equals(c._class_map[60], c.basic)
        assert_equals(c._class_map[90], c.tx)
        assert_equals(deque([]), c._pending_events)
        assert_equals(deque([]), c._frame_buffer)
        assert_equals(set([]), c._open_listeners)
        assert_equals(set([]), c._close_listeners)
        assert_false(c._closed)
        assert_equals(
            {
                'reply_code': 0,
                'reply_text': 'first connect',
                'class_id': 0,
                'method_id': 0
            }, c._close_info)
        assert_true(c._active)

        c = Channel('connection', 'id', {
            20: ChannelClass,
            40: ExchangeClass,
            50: QueueClass,
            60: BasicClass,
            90: TransactionClass,
        }, synchronous=True)
        assert_true(c._synchronous)

    def test_properties(self):
        connection = mock()
        connection.logger = 'logger'
        connection.synchronous = False

        c = Channel(connection, 'id', {})
        c._closed = 'yes'
        c._close_info = 'ithappened'
        c._active = 'record'

        assert_equals(connection, c.connection)
        assert_equals('id', c.channel_id)
        assert_equals('logger', c.logger)
        assert_equals('yes', c.closed)
        assert_equals('ithappened', c.close_info)
        assert_equals('record', c.active)
        assert_false(c.synchronous)

        c._closed = False
        assert_equals(None, c.close_info)

        connection.synchronous = False
        c = Channel(connection, 'id', {}, synchronous=True)
        assert_true(c.synchronous)

        connection.synchronous = True
        c = Channel(connection, 'id', {})
        assert_true(c.synchronous)

        connection.synchronous = True
        c = Channel(connection, 'id', {}, synchronous=False)
        assert_true(c.synchronous)

    def test_add_open_listener(self):
        c = Channel(None, None, {})
        c.add_open_listener('foo')
        assert_equals(set(['foo']), c._open_listeners)

    def test_remove_open_listener(self):
        c = Channel(None, None, {})
        c.add_open_listener('foo')
        c.remove_open_listener('foo')
        c.remove_open_listener('bar')
        assert_equals(set([]), c._open_listeners)

    def test_notify_open_listeners(self):
        c = Channel(None, None, {})
        cb1 = mock()
        cb2 = mock()
        c._open_listeners = set([cb1, cb2])
        expect(cb1).args(c)
        expect(cb2).args(c)
        c._notify_open_listeners()

    def test_add_close_listener(self):
        c = Channel(None, None, {})
        c.add_close_listener('foo')
        assert_equals(set(['foo']), c._close_listeners)

    def test_remove_close_listener(self):
        c = Channel(None, None, {})
        c.add_close_listener('foo')
        c.remove_close_listener('foo')
        c.remove_close_listener('bar')
        assert_equals(set([]), c._close_listeners)

    def test_notify_close_listeners(self):
        c = Channel(None, None, {})
        cb1 = mock()
        cb2 = mock()
        c._close_listeners = set([cb1, cb2])
        expect(cb1).args(c)
        expect(cb2).args(c)
        c._notify_close_listeners()

    def test_open(self):
        c = Channel(None, None, {})
        expect(mock(c, 'channel').open)
        c.open()

    def test_active(self):
        c = Channel(None, None, {})
        expect(mock(c, 'channel').open)
        c.open()
        assertTrue(c.active)

    def test_close_with_no_args(self):
        c = Channel(None, None, {})
        expect(mock(c, 'channel').close).args(0, '', 0, 0)
        c.close()

    def test_close_with_args(self):
        c = Channel(None, None, {})
        expect(mock(c, 'channel').close).args(1, 'two', 3, 4)
        expect(c.channel.close).args(1, 'two', 3, 4)

        c.close(1, 'two', 3, 4)
        c.close(reply_code=1, reply_text='two', class_id=3, method_id=4)

    def test_close_when_channel_attr_cleared(self):
        c = Channel(None, None, {})
        assert_false(hasattr(c, 'channel'))
        c.close()

    def test_publish(self):
        c = Channel(None, None, {})
        expect(mock(c, 'basic').publish).args('arg1', 'arg2', foo='bar')
        c.publish('arg1', 'arg2', foo='bar')

    def test_publish_synchronous(self):
        c = Channel(None, None, {})
        expect(mock(c, 'tx').select)
        expect(mock(c, 'basic').publish).args('arg1', 'arg2', foo='bar')
        expect(c.tx.commit).args(cb='a_cb')

        c.publish_synchronous('arg1', 'arg2', foo='bar', cb='a_cb')

    def test_dispatch(self):
        c = Channel(None, None, {})
        frame = mock()
        frame.class_id = 32
        klass = mock()

        c._class_map[32] = klass
        expect(klass.dispatch).args(frame)
        c.dispatch(frame)

        frame.class_id = 33
        assert_raises(Channel.InvalidClass, c.dispatch, frame)

    def test_buffer_frame(self):
        c = Channel(None, None, {})
        c.buffer_frame('f1')
        c.buffer_frame('f2')
        assert_equals(deque(['f1', 'f2']), c._frame_buffer)

    def test_process_frames_when_no_frames(self):
        # Not that this should ever happen, but to be sure
        c = Channel(None, None, {})
        stub(c.dispatch)
        c.process_frames()

    def test_process_frames_stops_when_buffer_is_empty(self):
        c = Channel(None, None, {})
        f0 = MethodFrame('ch_id', 'c_id', 'm_id')
        f1 = MethodFrame('ch_id', 'c_id', 'm_id')
        c._frame_buffer = deque([f0, f1])

        expect(c.dispatch).args(f0)
        expect(c.dispatch).args(f1)

        c.process_frames()
        assert_equals(deque(), c._frame_buffer)

    def test_process_frames_stops_when_frameunderflow_raised(self):
        c = Channel(None, None, {})
        f0 = MethodFrame('ch_id', 'c_id', 'm_id')
        f1 = MethodFrame('ch_id', 'c_id', 'm_id')
        c._frame_buffer = deque([f0, f1])

        expect(c.dispatch).args(f0).raises(ProtocolClass.FrameUnderflow)

        c.process_frames()
        assert_equals(f1, c._frame_buffer[0])

    def test_process_frames_when_connectionclosed_on_dispatch(self):
        c = Channel(None, None, {})
        c._connection = mock()
        c._connection.logger = mock()

        f0 = MethodFrame(20, 30, 40)
        f1 = MethodFrame('ch_id', 'c_id', 'm_id')
        c._frame_buffer = deque([f0, f1])

        expect(c.dispatch).args(f0).raises(
            ConnectionClosed('something darkside'))
        stub(c.close)  # assert not called

        assert_raises(ConnectionClosed, c.process_frames)

    def test_process_frames_logs_and_closes_when_dispatch_error_raised(self):
        c = Channel(None, None, {})
        c._connection = mock()
        c._connection.logger = mock()

        f0 = MethodFrame(20, 30, 40)
        f1 = MethodFrame('ch_id', 'c_id', 'm_id')
        c._frame_buffer = deque([f0, f1])

        expect(c.dispatch).args(f0).raises(RuntimeError("zomg it broked"))
        expect(c.close).args(500, 'Failed to dispatch %s' % (str(f0)))

        assert_raises(RuntimeError, c.process_frames)
        assert_equals(f1, c._frame_buffer[0])

    def test_process_frames_logs_and_closes_when_dispatch_error_raised_even_when_exception_on_close(self):
        c = Channel(None, None, {})
        c._connection = mock()
        c._connection.logger = mock()

        f0 = MethodFrame(20, 30, 40)
        f1 = MethodFrame('ch_id', 'c_id', 'm_id')
        c._frame_buffer = deque([f0, f1])

        expect(c.dispatch).args(f0).raises(RuntimeError("zomg it broked"))
        expect(c.close).raises(ValueError())

        assert_raises(RuntimeError, c.process_frames)
        assert_equals(f1, c._frame_buffer[0])

    def test_process_frames_logs_and_closes_when_systemexit_raised(self):
        c = Channel(None, None, {})
        c._connection = mock()
        c._connection.logger = mock()

        f0 = MethodFrame(20, 30, 40)
        f1 = MethodFrame('ch_id', 'c_id', 'm_id')
        c._frame_buffer = deque([f0, f1])

        expect(c.dispatch).args(f0).raises(SystemExit())
        stub(c.close)

        assert_raises(SystemExit, c.process_frames)
        assert_equals(f1, c._frame_buffer[0])

    def test_next_frame_with_a_frame(self):
        c = Channel(None, None, {})
        ch_id, c_id, m_id = 0, 1, 2
        f0 = MethodFrame(ch_id, c_id, m_id)
        f1 = MethodFrame(ch_id, c_id, m_id)
        c._frame_buffer = deque([f0, f1])
        assert_equals(c.next_frame(), f0)

    def test_next_frame_with_no_frames(self):
        c = Channel(None, None, {})
        c._frame_buffer = deque()
        assert_equals(c.next_frame(), None)

    def test_requeue_frames(self):
        c = Channel(None, None, {})
        ch_id, c_id, m_id = 0, 1, 2
        f = [MethodFrame(ch_id, c_id, m_id) for i in xrange(4)]
        c._frame_buffer = deque(f[:2])

        c.requeue_frames(f[2:])
        assert_equals(c._frame_buffer, deque([f[i] for i in [3, 2, 0, 1]]))

    def test_send_frame_when_not_closed_no_flow_control_no_pending_events(self):
        conn = mock()
        c = Channel(conn, 32, {})

        expect(conn.send_frame).args('frame')

        c.send_frame('frame')

    def test_send_frame_when_not_closed_no_flow_control_pending_event(self):
        conn = mock()
        c = Channel(conn, 32, {})
        c._pending_events.append('cb')

        c.send_frame('frame')
        assert_equals(deque(['cb', 'frame']), c._pending_events)

    def test_send_frame_when_not_closed_and_flow_control(self):
        conn = mock()
        c = Channel(conn, 32, {})
        c._active = False

        method = MethodFrame(1, 2, 3)
        heartbeat = HeartbeatFrame()
        header = HeaderFrame(1, 2, 3, 4)
        content = ContentFrame(1, 'foo')

        expect(conn.send_frame).args(method)
        expect(conn.send_frame).args(heartbeat)

        c.send_frame(method)
        c.send_frame(heartbeat)
        assert_raises(Channel.Inactive, c.send_frame, header)
        assert_raises(Channel.Inactive, c.send_frame, content)

    def test_send_frame_when_closed_for_a_reason(self):
        conn = mock()
        c = Channel(conn, 32, {})
        c._closed = True
        c._close_info = {'reply_code': 42, 'reply_text': 'bad'}

        assert_raises(ChannelClosed, c.send_frame, 'frame')

    def test_send_frame_when_closed_for_no_reason(self):
        conn = mock()
        c = Channel(conn, 32, {})
        c._closed = True
        c._close_info = {'reply_code': 42, 'reply_text': ''}

        assert_raises(ChannelClosed, c.send_frame, 'frame')

    def test_add_synchronous_cb_when_transport_asynchronous(self):
        conn = mock()
        conn.synchronous = False
        c = Channel(conn, None, {})

        assert_equals(deque([]), c._pending_events)
        c.add_synchronous_cb('foo')
        assert_equals(deque(['foo']), c._pending_events)

    def test_add_synchronous_cb_when_transport_asynchronous_but_channel_synchronous(self):
        conn = mock()
        conn.synchronous = False
        c = Channel(conn, None, {}, synchronous=True)

        wrapper = mock()
        wrapper._read = True
        wrapper._result = 'done'

        expect(channel.SyncWrapper).args('foo').returns(wrapper)
        expect(conn.read_frames)
        expect(conn.read_frames).side_effect(
            lambda: setattr(wrapper, '_read', False))

        assert_equals(deque([]), c._pending_events)
        assert_equals('done', c.add_synchronous_cb('foo'))

        # This is technically cleared in runtime, but assert that it's not cleared
        # in this method
        assert_equals(deque([wrapper]), c._pending_events)

    def test_add_synchronous_cb_when_transport_synchronous(self):
        conn = mock()
        conn.synchronous = True
        c = Channel(conn, None, {})

        wrapper = mock()
        wrapper._read = True
        wrapper._result = 'done'

        expect(channel.SyncWrapper).args('foo').returns(wrapper)
        expect(conn.read_frames)
        expect(conn.read_frames).side_effect(
            lambda: setattr(wrapper, '_read', False))

        assert_equals(deque([]), c._pending_events)
        assert_equals('done', c.add_synchronous_cb('foo'))

        # This is technically cleared in runtime, but assert that it's not cleared
        # in this method
        assert_equals(deque([wrapper]), c._pending_events)

    def test_add_synchronous_cb_when_transport_synchronous_and_channel_closes(self):
        conn = mock()
        conn.synchronous = True
        c = Channel(conn, None, {})

        wrapper = mock()
        wrapper._read = True
        wrapper._result = 'done'

        expect(channel.SyncWrapper).args('foo').returns(wrapper)
        expect(conn.read_frames)
        expect(conn.read_frames).side_effect(
            lambda: setattr(c, '_closed', True))

        with assert_raises(ChannelClosed):
            c.add_synchronous_cb('foo')

    def test_clear_synchronous_cb_when_no_pending(self):
        c = Channel(None, None, {})
        stub(c._flush_pending_events)

        assert_equals(deque([]), c._pending_events)
        assert_equals('foo', c.clear_synchronous_cb('foo'))

    def test_clear_synchronous_cb_when_pending_cb_matches(self):
        c = Channel(None, None, {})
        c._pending_events = deque(['foo'])

        expect(c._flush_pending_events)

        assert_equals('foo', c.clear_synchronous_cb('foo'))
        assert_equals(deque([]), c._pending_events)

    def test_clear_synchronous_cb_when_pending_cb_doesnt_match_but_isnt_in_list(self):
        c = Channel(None, None, {})
        c._pending_events = deque(['foo'])

        expect(c._flush_pending_events)

        assert_equals('bar', c.clear_synchronous_cb('bar'))
        assert_equals(deque(['foo']), c._pending_events)

    def test_clear_synchronous_cb_when_pending_cb_doesnt_match_but_isnt_in_list(self):
        c = Channel(None, None, {})
        stub(c._flush_pending_events)
        c._pending_events = deque(['foo', 'bar'])

        assert_raises(ChannelError, c.clear_synchronous_cb, 'bar')
        assert_equals(deque(['foo', 'bar']), c._pending_events)

    def test_flush_pending_events_flushes_all_leading_frames(self):
        conn = mock()
        c = Channel(conn, 42, {})
        f1 = MethodFrame(1, 2, 3)
        f2 = MethodFrame(1, 2, 3)
        f3 = MethodFrame(1, 2, 3)
        c._pending_events = deque([f1, f2, 'cb', f3])

        expect(conn.send_frame).args(f1)
        expect(conn.send_frame).args(f2)

        c._flush_pending_events()
        assert_equals(deque(['cb', f3]), c._pending_events)

    def test_closed_cb_without_final_frame(self):
        c = Channel('connection', None, {
            20: ChannelClass,
            40: ExchangeClass,
            50: QueueClass,
            60: BasicClass,
            90: TransactionClass,
        })
        c._pending_events = 'foo'
        c._frame_buffer = 'foo'

        for val in c._class_map.values():
            expect(val._cleanup)
        expect(c._notify_close_listeners)

        c._closed_cb()
        assert_equals(deque([]), c._pending_events)
        assert_equals(deque([]), c._frame_buffer)
        assert_equals(None, c._connection)
        assert_false(hasattr(c, 'channel'))
        assert_false(hasattr(c, 'exchange'))
        assert_false(hasattr(c, 'queue'))
        assert_false(hasattr(c, 'basic'))
        assert_false(hasattr(c, 'tx'))
        assert_equals(None, c._class_map)
        assert_equals(set(), c._close_listeners)

    def test_closed_cb_with_final_frame(self):
        conn = mock()
        c = Channel(conn, None, {})

        expect(conn.send_frame).args('final')
        for val in c._class_map.values():
            expect(val._cleanup)

        c._closed_cb('final')

########NEW FILE########
__FILENAME__ = basic_class_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai

from haigha.classes import basic_class
from haigha.classes.protocol_class import ProtocolClass
from haigha.classes.basic_class import BasicClass
from haigha.frames.method_frame import MethodFrame
from haigha.writer import Writer
from haigha.reader import Reader
from haigha.message import Message
from haigha.connection import Connection

from collections import deque


class BasicClassTest(Chai):

    def setUp(self):
        super(BasicClassTest, self).setUp()
        ch = mock()
        ch.channel_id = 42
        ch.logger = mock()
        self.klass = BasicClass(ch)

    def test_init(self):
        expect(ProtocolClass.__init__).args('foo', a='b')

        klass = BasicClass.__new__(BasicClass)
        klass.__init__('foo', a='b')

        assert_equals(
            {
                11: klass._recv_qos_ok,
                21: klass._recv_consume_ok,
                31: klass._recv_cancel_ok,
                50: klass._recv_return,
                60: klass._recv_deliver,
                71: klass._recv_get_response,
                72: klass._recv_get_response,
                111: klass._recv_recover_ok,
            }, klass.dispatch_map)
        assert_equals(0, klass._consumer_tag_id)
        assert_equals(deque(), klass._pending_consumers)
        assert_equals({}, klass._consumer_cb)
        assert_equals(deque(), klass._get_cb)
        assert_equals(deque(), klass._recover_cb)
        assert_equals(deque(), klass._cancel_cb)

    def test_cleanup(self):
        self.klass._cleanup()
        assert_equals(None, self.klass._pending_consumers)
        assert_equals(None, self.klass._consumer_cb)
        assert_equals(None, self.klass._get_cb)
        assert_equals(None, self.klass._recover_cb)
        assert_equals(None, self.klass._cancel_cb)
        assert_equals(None, self.klass._channel)
        assert_equals(None, self.klass.dispatch_map)

    def test_generate_consumer_tag(self):
        assert_equals(0, self.klass._consumer_tag_id)
        assert_equals('channel-42-1', self.klass._generate_consumer_tag())
        assert_equals(1, self.klass._consumer_tag_id)

    def test_qos_default_args(self):
        w = mock()
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_long).args(0).returns(w)
        expect(w.write_short).args(0).returns(w)
        expect(w.write_bit).args(False)
        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 10, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_qos_ok)

        self.klass.qos()

    def test_qos_with_args(self):
        w = mock()
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_long).args(1).returns(w)
        expect(w.write_short).args(2).returns(w)
        expect(w.write_bit).args(3)
        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 10, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_qos_ok)

        self.klass.qos(prefetch_size=1, prefetch_count=2, is_global=3)

    def test_recv_qos_ok(self):
        self.klass._recv_qos_ok('frame')

    def test_consume_default_args(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(self.klass._generate_consumer_tag).returns('ctag')
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_short).args(self.klass.default_ticket).returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_shortstr).args('ctag').returns(w)
        expect(w.write_bits).args(False, True, False, True).returns(w)
        expect(w.write_table).args({})
        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 20, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        assert_equals(deque(), self.klass._pending_consumers)
        assert_equals({}, self.klass._consumer_cb)
        self.klass.consume('queue', 'consumer')
        assert_equals(deque(), self.klass._pending_consumers)
        assert_equals({'ctag': 'consumer'}, self.klass._consumer_cb)

    def test_consume_with_args_including_nowait_and_ticket(self):
        w = mock()
        stub(self.klass.allow_nowait)
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_short).args('train').returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_shortstr).args('stag').returns(w)
        expect(w.write_bits).args('nloc', 'nack', 'mine', False).returns(w)
        expect(w.write_table).args({})
        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 20, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_consume_ok)

        assert_equals(deque(), self.klass._pending_consumers)
        assert_equals({}, self.klass._consumer_cb)
        self.klass.consume('queue', 'consumer', consumer_tag='stag', no_local='nloc',
                           no_ack='nack', exclusive='mine', nowait=False, ticket='train')
        assert_equals(
            deque([('consumer', None)]), self.klass._pending_consumers)
        assert_equals({}, self.klass._consumer_cb)

    def test_consume_with_args_including_nowait_no_ticket_with_callback(self):
        w = mock()
        stub(self.klass._generate_consumer_tag)
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_short).args(self.klass.default_ticket).returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_shortstr).args('stag').returns(w)
        expect(w.write_bits).args('nloc', 'nack', 'mine', False).returns(w)
        expect(w.write_table).args({})
        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 20, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_consume_ok)

        self.klass._pending_consumers = deque([('blargh', None)])
        assert_equals({}, self.klass._consumer_cb)
        self.klass.consume('queue', 'consumer', consumer_tag='stag', no_local='nloc',
                           no_ack='nack', exclusive='mine', nowait=False, cb='callback')
        assert_equals(deque(
            [('blargh', None), ('consumer', 'callback')]), self.klass._pending_consumers)
        assert_equals({}, self.klass._consumer_cb)

    def test_recv_consume_ok(self):
        frame = mock()
        cb = mock()
        expect(frame.args.read_shortstr).returns('ctag')
        self.klass._pending_consumers = deque(
            [('consumer', None), ('blargh', cb)])

        assert_equals({}, self.klass._consumer_cb)
        self.klass._recv_consume_ok(frame)
        assert_equals({'ctag': 'consumer'}, self.klass._consumer_cb)
        assert_equals(deque([('blargh', cb)]), self.klass._pending_consumers)

        # call again and assert that cb is called
        frame2 = mock()
        expect(frame2.args.read_shortstr).returns('ctag2')
        expect(cb)
        self.klass._recv_consume_ok(frame2)
        assert_equals(
            {'ctag': 'consumer', 'ctag2': 'blargh'}, self.klass._consumer_cb)
        assert_equals(deque(), self.klass._pending_consumers)

    def test_cancel_default_args(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_shortstr).args('').returns(w)
        expect(w.write_bit).args(True)

        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 30, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        self.klass._consumer_cb[''] = 'foo'
        assert_equals(deque(), self.klass._cancel_cb)
        self.klass.cancel()
        assert_equals(deque(), self.klass._cancel_cb)
        assert_equals({}, self.klass._consumer_cb)

    def test_cancel_nowait_and_consumer_tag_not_registered(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_shortstr).args('ctag').returns(w)
        expect(w.write_bit).args(True)

        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 30, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        expect(self.klass.logger.warning).args(
            'no callback registered for consumer tag " %s "', 'ctag')

        assert_equals(deque(), self.klass._cancel_cb)
        self.klass.cancel(consumer_tag='ctag')
        assert_equals(deque(), self.klass._cancel_cb)
        assert_equals({}, self.klass._consumer_cb)

    def test_cancel_wait_without_cb(self):
        w = mock()
        stub(self.klass.allow_nowait)
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_shortstr).args('').returns(w)
        expect(w.write_bit).args(False)

        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 30, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_cancel_ok)

        assert_equals(deque(), self.klass._cancel_cb)
        self.klass.cancel(nowait=False)
        assert_equals(deque([None]), self.klass._cancel_cb)
        assert_equals({}, self.klass._consumer_cb)

    def test_cancel_wait_with_cb(self):
        w = mock()
        stub(self.klass.allow_nowait)
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_shortstr).args('').returns(w)
        expect(w.write_bit).args(False)

        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 30, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_cancel_ok)

        self.klass._cancel_cb = deque(['blargh'])
        self.klass.cancel(nowait=False, cb='user_cb')
        assert_equals(deque(['blargh', 'user_cb']), self.klass._cancel_cb)
        assert_equals({}, self.klass._consumer_cb)

    def test_cancel_resolves_to_ctag_when_consumer_arg_supplied(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_shortstr).args('ctag').returns(w)
        expect(w.write_bit).args(True)

        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 30, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        self.klass._consumer_cb['ctag'] = 'consumer'
        assert_equals(deque(), self.klass._cancel_cb)
        self.klass.cancel(consumer='consumer')
        assert_equals(deque(), self.klass._cancel_cb)
        assert_equals({}, self.klass._consumer_cb)

    def test_recv_cancel_ok_when_consumer_and_callback(self):
        frame = mock()
        cancel_cb = mock()
        expect(frame.args.read_shortstr).returns('ctag')
        self.klass._consumer_cb['ctag'] = 'foo'
        self.klass._cancel_cb = deque([cancel_cb, mock()])
        expect(cancel_cb)

        self.klass._recv_cancel_ok(frame)
        assert_equals(1, len(self.klass._cancel_cb))
        assert_false(cancel_cb in self.klass._cancel_cb)

    def test_recv_cancel_ok_when_no_consumer_or_callback(self):
        frame = mock()
        expect(frame.args.read_shortstr).returns('ctag')
        expect(self.klass.logger.warning).args(
            'no callback registered for consumer tag " %s "', 'ctag')
        self.klass._cancel_cb = deque([None, mock()])

        self.klass._recv_cancel_ok(frame)
        assert_equals(1, len(self.klass._cancel_cb))
        assert_false(None in self.klass._cancel_cb)

    def test_publish_default_args(self):
        args = Writer()
        msg = Message('hello, world')
        args.write_short(0)\
            .write_shortstr('exchange')\
            .write_shortstr('routing_key')\
            .write_bits(False, False)
        self.klass.channel.connection.frame_max = 3

        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 40, args).returns('methodframe')
        expect(mock(basic_class, 'HeaderFrame')).args(
            42, 60, 0, len(msg), msg.properties).returns('headerframe')
        expect(mock(basic_class, 'ContentFrame').create_frames).args(
            42, msg.body, 3).returns(['f0', 'f1', 'f2'])
        expect(self.klass.send_frame).args('methodframe')
        expect(self.klass.send_frame).args('headerframe')
        expect(self.klass.send_frame).args('f0')
        expect(self.klass.send_frame).args('f1')
        expect(self.klass.send_frame).args('f2')
        self.klass.publish(msg, 'exchange', 'routing_key')

    def test_publish_with_args(self):
        w = mock()
        msg = Message('hello, world')
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_short).args('ticket').returns(w)
        expect(w.write_shortstr).args('exchange').returns(w)
        expect(w.write_shortstr).args('route').returns(w)
        expect(w.write_bits).args('m', 'i')
        self.klass.channel.connection.frame_max = 3

        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 40, w).returns('methodframe')
        expect(mock(basic_class, 'HeaderFrame')).args(
            42, 60, 0, len(msg), msg.properties).returns('headerframe')
        expect(mock(basic_class, 'ContentFrame').create_frames).args(
            42, msg.body, 3).returns(['f0', 'f1', 'f2'])
        expect(self.klass.send_frame).args('methodframe')
        expect(self.klass.send_frame).args('headerframe')
        expect(self.klass.send_frame).args('f0')
        expect(self.klass.send_frame).args('f1')
        expect(self.klass.send_frame).args('f2')

        self.klass.publish(
            msg, 'exchange', 'route', mandatory='m', immediate='i', ticket='ticket')

    def test_return_msg(self):
        args = Writer()
        args.write_short(3)
        args.write_shortstr('reply_text')
        args.write_shortstr('exchange')
        args.write_shortstr('routing_key')
        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 50, args).returns('frame')
        expect(self.klass.send_frame).args('frame')
        self.klass.return_msg(3, 'reply_text', 'exchange', 'routing_key')

    def test_recv_return(self):
        self.klass._recv_return('frame')

    def test_recv_deliver_with_cb(self):
        msg = mock()
        msg.delivery_info = {'consumer_tag': 'ctag'}
        cb = mock()
        self.klass._consumer_cb['ctag'] = cb

        expect(self.klass._read_msg).args(
            'frame', with_consumer_tag=True, with_message_count=False).returns(msg)
        expect(cb).args(msg)

        self.klass._recv_deliver('frame')

    def test_recv_deliver_without_cb(self):
        msg = mock()
        msg.delivery_info = {'consumer_tag': 'ctag'}

        expect(self.klass._read_msg).args(
            'frame', with_consumer_tag=True, with_message_count=False).returns(msg)

        self.klass._recv_deliver('frame')

    def test_get_default_args(self):
        w = mock()
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_short).args(self.klass.default_ticket).returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_bit).args(True)
        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 70, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_get_response).returns('msg')

        assert_equals(deque(), self.klass._get_cb)
        assert_equals('msg', self.klass.get('queue'))
        assert_equals(deque([None]), self.klass._get_cb)

    def test_get_with_args(self):
        w = mock()
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_short).args('ticket').returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_bit).args('ack')
        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 70, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_get_response).returns('msg')

        self.klass._get_cb = deque(['blargh'])
        assert_equals(
            'msg', self.klass.get('queue', 'consumer', no_ack='ack', ticket='ticket'))
        assert_equals(deque(['blargh', 'consumer']), self.klass._get_cb)

    def test_recv_get_response(self):
        frame = mock()
        frame.method_id = 71
        expect(self.klass._recv_get_ok).args(frame).returns('msg')
        assert_equals('msg', self.klass._recv_get_response(frame))

        frame.method_id = 72
        expect(self.klass._recv_get_empty).args(frame).returns('nada')
        assert_equals('nada', self.klass._recv_get_response(frame))

    def test_recv_get_ok_with_cb(self):
        cb = mock()
        self.klass._get_cb.append(cb)
        self.klass._get_cb.append(mock())

        expect(self.klass._read_msg).args(
            'frame', with_consumer_tag=False, with_message_count=True).returns('msg')
        expect(cb).args('msg')

        assert_equals('msg', self.klass._recv_get_ok('frame'))
        assert_equals(1, len(self.klass._get_cb))
        assert_false(cb in self.klass._get_cb)

    def test_recv_get_ok_without_cb(self):
        self.klass._get_cb.append(None)
        self.klass._get_cb.append(mock())

        expect(self.klass._read_msg).args(
            'frame', with_consumer_tag=False, with_message_count=True).returns('msg')

        self.klass._recv_get_ok('frame')
        assert_equals(1, len(self.klass._get_cb))
        assert_false(None in self.klass._get_cb)

    def test_recv_get_empty_with_cb(self):
        cb = mock()
        self.klass._get_cb.append(cb)
        self.klass._get_cb.append(mock())

        expect(cb).args(None)

        self.klass._recv_get_empty('frame')
        assert_equals(1, len(self.klass._get_cb))
        assert_false(cb in self.klass._get_cb)

    def test_recv_get_empty_without_cb(self):
        self.klass._get_cb.append(None)
        self.klass._get_cb.append(mock())

        self.klass._recv_get_empty('frame')
        assert_equals(1, len(self.klass._get_cb))
        assert_false(None in self.klass._get_cb)

    def test_ack_default_args(self):
        w = mock()
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_longlong).args(8675309).returns(w)
        expect(w.write_bit).args(False)
        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 80, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        self.klass.ack(8675309)

    def test_ack_with_args(self):
        w = mock()
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_longlong).args(8675309).returns(w)
        expect(w.write_bit).args('many')
        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 80, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        self.klass.ack(8675309, multiple='many')

    def test_reject_default_args(self):
        w = mock()
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_longlong).args(8675309).returns(w)
        expect(w.write_bit).args(False)
        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 90, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        self.klass.reject(8675309)

    def test_reject_with_args(self):
        w = mock()
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_longlong).args(8675309).returns(w)
        expect(w.write_bit).args('sure')
        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 90, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        self.klass.reject(8675309, requeue='sure')

    def test_recover_async(self):
        w = mock()
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_bit).args(False)
        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 100, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        self.klass.recover_async()

    def test_recover_default_args(self):
        w = mock()
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_bit).args(False)
        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 110, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_recover_ok)

        self.klass.recover()
        assert_equals(deque([None]), self.klass._recover_cb)

    def test_recover_with_args(self):
        w = mock()
        expect(mock(basic_class, 'Writer')).returns(w)
        expect(w.write_bit).args('requeue')
        expect(mock(basic_class, 'MethodFrame')).args(
            42, 60, 110, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_recover_ok)

        self.klass._recover_cb = deque(['blargh'])
        self.klass.recover(requeue='requeue', cb='callback')
        assert_equals(deque(['blargh', 'callback']), self.klass._recover_cb)

    def test_recv_recover_ok_with_cb(self):
        cb = mock()
        self.klass._recover_cb.append(cb)
        self.klass._recover_cb.append(mock())

        expect(cb)

        self.klass._recv_recover_ok('frame')
        assert_equals(1, len(self.klass._recover_cb))
        assert_false(cb in self.klass._recover_cb)

    def test_recv_recover_ok_without_cb(self):
        self.klass._recover_cb.append(None)
        self.klass._recover_cb.append(mock())

        self.klass._recv_recover_ok('frame')
        assert_equals(1, len(self.klass._recover_cb))
        assert_false(None in self.klass._recover_cb)

    def test_read_msg_raises_frameunderflow_when_no_header_frame(self):
        expect(self.klass.channel.next_frame).returns(None)
        expect(self.klass.channel.requeue_frames).args(['method_frame'])
        assert_raises(
            self.klass.FrameUnderflow, self.klass._read_msg, 'method_frame')

    def test_read_msg_raises_frameunderflow_when_no_content_frames(self):
        header_frame = mock()
        header_frame.size = 1000000
        expect(self.klass.channel.next_frame).returns(header_frame)
        expect(self.klass.channel.next_frame).returns(None)
        expect(self.klass.channel.requeue_frames).args(
            deque([header_frame, 'method_frame']))
        assert_raises(
            self.klass.FrameUnderflow, self.klass._read_msg, 'method_frame')

    def test_read_msg_when_body_length_0_no_cb(self):
        method_frame = mock()
        header_frame = mock()
        header_frame.size = 0
        header_frame.properties = {'foo': 'bar'}
        delivery_info = {'channel': self.klass.channel,
                         'consumer_tag': 'consumer_tag',
                         'delivery_tag': 9,
                         'redelivered': False,
                         'exchange': 'exchange',
                         'routing_key': 'routing_key'}

        expect(self.klass.channel.next_frame).returns(header_frame)
        expect(method_frame.args.read_shortstr).returns('consumer_tag')
        expect(method_frame.args.read_longlong).returns(9)
        expect(method_frame.args.read_bit).returns(False)
        expect(method_frame.args.read_shortstr).returns('exchange')
        expect(method_frame.args.read_shortstr).returns('routing_key')
        expect(Message).args(
            body=bytearray(), delivery_info=delivery_info, foo='bar').returns('message')

        assert_equals('message', self.klass._read_msg(
            method_frame, with_consumer_tag=True))

    def test_read_msg_when_body_length_greater_than_0_with_cb(self):
        method_frame = mock()
        header_frame = mock()
        header_frame.size = 100
        header_frame.properties = {}
        cframe1 = mock()
        cframe2 = mock()
        self.klass._consumer_cb['ctag'] = mock()
        delivery_info = {
            'channel': self.klass.channel,
            'delivery_tag': 'dtag',
            'redelivered': 'no',
            'exchange': 'exchange',
            'routing_key': 'routing_key',
            'message_count': 8675309,
        }

        expect(self.klass.channel.next_frame).returns(header_frame)
        expect(self.klass.channel.next_frame).returns(cframe1)
        expect(cframe1.payload.buffer).returns('x' * 50)
        expect(self.klass.channel.next_frame).returns(cframe2)
        expect(cframe2.payload.buffer).returns('x' * 50)
        expect(method_frame.args.read_longlong).returns('dtag')
        expect(method_frame.args.read_bit).returns('no')
        expect(method_frame.args.read_shortstr).returns('exchange')
        expect(method_frame.args.read_shortstr).returns('routing_key')
        expect(method_frame.args.read_long).returns(8675309)
        expect(Message).args(
            body=bytearray('x' * 100), delivery_info=delivery_info).returns('message')

        assert_equals('message', self.klass._read_msg(
            method_frame, with_message_count=True))

########NEW FILE########
__FILENAME__ = channel_class_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai

from haigha.channel import Channel
from haigha.classes import channel_class
from haigha.classes.protocol_class import ProtocolClass
from haigha.classes.channel_class import ChannelClass
from haigha.frames.method_frame import MethodFrame
from haigha.writer import Writer


class ChannelClassTest(Chai):

    def setUp(self):
        super(ChannelClassTest, self).setUp()
        connection = mock()
        ch = Channel(connection, 42, {})
        connection._logger = mock()
        self.klass = ChannelClass(ch)

    def test_init(self):
        expect(ProtocolClass.__init__).args('foo', a='b')

        klass = ChannelClass.__new__(ChannelClass)
        klass.__init__('foo', a='b')

        assert_equals(
            {
                11: klass._recv_open_ok,
                20: klass._recv_flow,
                21: klass._recv_flow_ok,
                40: klass._recv_close,
                41: klass._recv_close_ok,
            }, klass.dispatch_map)
        assert_equals(None, klass._flow_control_cb)

    def test_cleanup(self):
        self.klass._cleanup()
        assert_equals(None, self.klass._channel)
        assert_equals(None, self.klass.dispatch_map)

    def test_set_flow_cb(self):
        assert_equals(None, self.klass._flow_control_cb)
        self.klass.set_flow_cb('foo')
        assert_equals('foo', self.klass._flow_control_cb)

    def test_open(self):
        writer = mock()
        expect(mock(channel_class, 'Writer')).returns(writer)
        expect(writer.write_shortstr).args('')
        expect(mock(channel_class, 'MethodFrame')).args(
            42, 20, 10, writer).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_open_ok)

        self.klass.open()

    def test_recv_open_ok(self):
        expect(self.klass.channel._notify_open_listeners)
        self.klass._recv_open_ok('methodframe')

    def test_activate_when_not_active(self):
        self.klass.channel._active = False
        expect(self.klass._send_flow).args(True)
        self.klass.activate()

    def test_activate_when_active(self):
        self.klass.channel._active = True
        stub(self.klass._send_flow)
        self.klass.activate()

    def test_deactivate_when_not_active(self):
        self.klass.channel._active = False
        stub(self.klass._send_flow)
        self.klass.deactivate()

    def test_deactivate_when_active(self):
        self.klass.channel._active = True
        expect(self.klass._send_flow).args(False)
        self.klass.deactivate()

    def test_send_flow(self):
        writer = mock()
        expect(mock(channel_class, 'Writer')).returns(writer)
        expect(writer.write_bit).args('active')
        expect(mock(channel_class, 'MethodFrame')).args(
            42, 20, 20, writer).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_flow_ok)

        self.klass._send_flow('active')

    def test_recv_flow_no_cb(self):
        self.klass._flow_control_cb = None
        rframe = mock()
        writer = mock()
        expect(rframe.args.read_bit).returns('active')

        expect(mock(channel_class, 'Writer')).returns(writer)
        expect(writer.write_bit).args('active')
        expect(mock(channel_class, 'MethodFrame')).args(
            42, 20, 21, writer).returns('frame')
        expect(self.klass.send_frame).args('frame')

        self.klass._recv_flow(rframe)
        assert_equals('active', self.klass.channel._active)

    def test_recv_flow_with_cb(self):
        self.klass._flow_control_cb = mock()
        rframe = mock()
        writer = mock()
        expect(rframe.args.read_bit).returns('active')

        expect(mock(channel_class, 'Writer')).returns(writer)
        expect(writer.write_bit).args('active')
        expect(mock(channel_class, 'MethodFrame')).args(
            42, 20, 21, writer).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass._flow_control_cb)

        self.klass._recv_flow(rframe)

    def test_recv_flow_ok_no_cb(self):
        self.klass._flow_control_cb = None
        rframe = mock()
        expect(rframe.args.read_bit).returns('active')

        self.klass._recv_flow_ok(rframe)
        assert_equals('active', self.klass.channel._active)

    def test_recv_flow_ok_with_cb(self):
        self.klass._flow_control_cb = mock()
        rframe = mock()
        expect(rframe.args.read_bit).returns('active')
        expect(self.klass._flow_control_cb)

        self.klass._recv_flow_ok(rframe)
        assert_equals('active', self.klass.channel._active)

    def test_close_when_not_closed(self):
        writer = mock()
        expect(mock(channel_class, 'Writer')).returns(writer)
        expect(writer.write_short).args('rcode')
        expect(writer.write_shortstr).args(('reason' * 60)[:255])
        expect(writer.write_short).args('cid')
        expect(writer.write_short).args('mid')
        expect(mock(channel_class, 'MethodFrame')).args(
            42, 20, 40, writer).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_close_ok)

        self.klass.close('rcode', 'reason' * 60, 'cid', 'mid')
        assert_true(self.klass.channel._closed)
        assert_equals({
            'reply_code': 'rcode',
            'reply_text': 'reason' * 60,
            'class_id': 'cid',
            'method_id': 'mid',
        }, self.klass.channel._close_info)

    def test_close_when_closed(self):
        self.klass.channel._closed = True
        stub(self.klass.send_frame)

        self.klass.close()

    def test_close_when_channel_reference_cleared_in_recv_close_ok(self):
        writer = mock()
        expect(mock(channel_class, 'Writer')).returns(writer)
        expect(writer.write_short).args('rcode')
        expect(writer.write_shortstr).args('reason')
        expect(writer.write_short).args('cid')
        expect(writer.write_short).args('mid')
        expect(mock(channel_class, 'MethodFrame')).args(
            42, 20, 40, writer).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(self.klass._recv_close_ok).side_effect(
            setattr, self.klass, '_channel', None)

        # assert nothing raised
        self.klass.close('rcode', 'reason', 'cid', 'mid')

    def test_close_when_error_sending_frame(self):
        self.klass.channel._closed = False
        writer = mock()
        expect(mock(channel_class, 'Writer')).returns(writer)
        expect(writer.write_short).args(0)
        expect(writer.write_shortstr).args('')
        expect(writer.write_short).args(0)
        expect(writer.write_short).args(0)
        expect(mock(channel_class, 'MethodFrame')).args(
            42, 20, 40, writer).returns('frame')
        expect(self.klass.send_frame).args(
            'frame').raises(RuntimeError('fail'))

        assert_raises(RuntimeError, self.klass.close)
        assert_true(self.klass.channel._closed)
        assert_equals({
            'reply_code': 0,
            'reply_text': '',
            'class_id': 0,
            'method_id': 0,
        }, self.klass.channel._close_info)

    def test_recv_close(self):
        rframe = mock()
        expect(rframe.args.read_short).returns('rcode')
        expect(rframe.args.read_shortstr).returns('reason')
        expect(rframe.args.read_short).returns('cid')
        expect(rframe.args.read_short).returns('mid')

        expect(mock(channel_class, 'MethodFrame')).args(
            42, 20, 41).returns('frame')
        expect(self.klass.channel._closed_cb).args(final_frame='frame')

        assert_false(self.klass.channel._closed)
        self.klass._recv_close(rframe)
        assert_true(self.klass.channel._closed)
        assert_equals({
            'reply_code': 'rcode',
            'reply_text': 'reason',
            'class_id': 'cid',
            'method_id': 'mid',
        }, self.klass.channel._close_info)

    def test_recv_close_ok(self):
        expect(self.klass.channel._closed_cb)

        self.klass.channel._closed = False
        self.klass._recv_close_ok('frame')
        assert_true(self.klass.channel._closed)

########NEW FILE########
__FILENAME__ = exchange_class_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''
from collections import deque

from chai import Chai

from haigha.classes import exchange_class
from haigha.classes.protocol_class import ProtocolClass
from haigha.classes.exchange_class import ExchangeClass
from haigha.frames.method_frame import MethodFrame
from haigha.writer import Writer


class ExchangeClassTest(Chai):

    def setUp(self):
        super(ExchangeClassTest, self).setUp()
        ch = mock()
        ch.channel_id = 42
        ch.logger = mock()
        self.klass = ExchangeClass(ch)

    def test_init(self):
        expect(ProtocolClass.__init__).args('foo', a='b')

        klass = ExchangeClass.__new__(ExchangeClass)
        klass.__init__('foo', a='b')

        assert_equals(
            {
                11: klass._recv_declare_ok,
                21: klass._recv_delete_ok,
            }, klass.dispatch_map)
        assert_equals(deque(), klass._declare_cb)
        assert_equals(deque(), klass._delete_cb)

    def test_cleanup(self):
        self.klass._cleanup()
        assert_equals(None, self.klass._declare_cb)
        assert_equals(None, self.klass._delete_cb)
        assert_equals(None, self.klass._channel)
        assert_equals(None, self.klass.dispatch_map)

    def test_declare_default_args(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(mock(exchange_class, 'Writer')).returns(w)
        expect(w.write_short).args(self.klass.default_ticket).returns(w)
        expect(w.write_shortstr).args('exchange').returns(w)
        expect(w.write_shortstr).args('topic').returns(w)
        expect(w.write_bits).args(False, False, False, False, True).returns(w)
        expect(w.write_table).args({})
        expect(mock(exchange_class, 'MethodFrame')).args(
            42, 40, 10, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        stub(self.klass.channel.add_synchronous_cb)

        self.klass.declare('exchange', 'topic')
        assert_equals(deque(), self.klass._declare_cb)

    def test_declare_with_args(self):
        w = mock()
        stub(self.klass.allow_nowait)
        expect(mock(exchange_class, 'Writer')).returns(w)
        expect(w.write_short).args('t').returns(w)
        expect(w.write_shortstr).args('exchange').returns(w)
        expect(w.write_shortstr).args('topic').returns(w)
        expect(w.write_bits).args('p', 'd', False, False, False).returns(w)
        expect(w.write_table).args('table')
        expect(mock(exchange_class, 'MethodFrame')).args(
            42, 40, 10, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_declare_ok)

        self.klass.declare('exchange', 'topic', passive='p', durable='d',
                           nowait=False, arguments='table', ticket='t')
        assert_equals(deque([None]), self.klass._declare_cb)

    def test_declare_with_cb(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(mock(exchange_class, 'Writer')).returns(w)
        expect(w.write_short).args('t').returns(w)
        expect(w.write_shortstr).args('exchange').returns(w)
        expect(w.write_shortstr).args('topic').returns(w)
        expect(w.write_bits).args('p', 'd', False, False, False).returns(w)
        expect(w.write_table).args('table')
        expect(mock(exchange_class, 'MethodFrame')).args(
            42, 40, 10, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_declare_ok)

        self.klass.declare('exchange', 'topic', passive='p', durable='d',
                           nowait=True, arguments='table', ticket='t', cb='foo')
        assert_equals(deque(['foo']), self.klass._declare_cb)

    def test_recv_declare_ok_no_cb(self):
        self.klass._declare_cb = deque([None])
        self.klass._recv_declare_ok('frame')
        assert_equals(deque(), self.klass._declare_cb)

    def test_recv_declare_ok_with_cb(self):
        cb = mock()
        self.klass._declare_cb = deque([cb])
        expect(cb)
        self.klass._recv_declare_ok('frame')
        assert_equals(deque(), self.klass._declare_cb)

    def test_delete_default_args(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(mock(exchange_class, 'Writer')).returns(w)
        expect(w.write_short).args(self.klass.default_ticket).returns(w)
        expect(w.write_shortstr).args('exchange').returns(w)
        expect(w.write_bits).args(False, True)
        expect(mock(exchange_class, 'MethodFrame')).args(
            42, 40, 20, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        stub(self.klass.channel.add_synchronous_cb)

        self.klass.delete('exchange')
        assert_equals(deque(), self.klass._delete_cb)

    def test_delete_with_args(self):
        w = mock()
        stub(self.klass.allow_nowait)
        expect(mock(exchange_class, 'Writer')).returns(w)
        expect(w.write_short).args('t').returns(w)
        expect(w.write_shortstr).args('exchange').returns(w)
        expect(w.write_bits).args('maybe', False)
        expect(mock(exchange_class, 'MethodFrame')).args(
            42, 40, 20, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_delete_ok)

        self.klass.delete(
            'exchange', if_unused='maybe', nowait=False, ticket='t')
        assert_equals(deque([None]), self.klass._delete_cb)

    def test_delete_with_cb(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(mock(exchange_class, 'Writer')).returns(w)
        expect(w.write_short).args('t').returns(w)
        expect(w.write_shortstr).args('exchange').returns(w)
        expect(w.write_bits).args('maybe', False)
        expect(mock(exchange_class, 'MethodFrame')).args(
            42, 40, 20, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_delete_ok)

        self.klass.delete(
            'exchange', if_unused='maybe', nowait=True, ticket='t', cb='foo')
        assert_equals(deque(['foo']), self.klass._delete_cb)

    def test_recv_delete_ok_no_cb(self):
        self.klass._delete_cb = deque([None])
        self.klass._recv_delete_ok('frame')
        assert_equals(deque(), self.klass._delete_cb)

    def test_recv_delete_ok_with_cb(self):
        cb = mock()
        self.klass._delete_cb = deque([cb])
        expect(cb)
        self.klass._recv_delete_ok('frame')
        assert_equals(deque(), self.klass._delete_cb)

########NEW FILE########
__FILENAME__ = protocol_class_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai

from haigha.classes import protocol_class
from haigha.classes.protocol_class import ProtocolClass


class ProtocolClassTest(Chai):

    def test_dispatch_when_in_dispatch_map(self):
        ch = mock()
        frame = mock()
        frame.method_id = 42

        klass = ProtocolClass(ch)
        klass.dispatch_map = {42: 'method'}

        with expect(ch.clear_synchronous_cb).args('method').returns(mock()) as cb:
            expect(cb).args(frame)

        klass.dispatch(frame)

########NEW FILE########
__FILENAME__ = queue_class_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai

from haigha.classes import queue_class
from haigha.classes.protocol_class import ProtocolClass
from haigha.classes.queue_class import QueueClass
from haigha.frames.method_frame import MethodFrame
from haigha.writer import Writer

from collections import deque


class QueueClassTest(Chai):

    def setUp(self):
        super(QueueClassTest, self).setUp()
        ch = mock()
        ch.channel_id = 42
        ch.logger = mock()
        self.klass = QueueClass(ch)

    def test_init(self):
        expect(ProtocolClass.__init__).args('foo', a='b')

        klass = QueueClass.__new__(QueueClass)
        klass.__init__('foo', a='b')

        assert_equals(
            {
                11: klass._recv_declare_ok,
                21: klass._recv_bind_ok,
                31: klass._recv_purge_ok,
                41: klass._recv_delete_ok,
                51: klass._recv_unbind_ok,

            }, klass.dispatch_map)
        assert_equals(deque(), self.klass._declare_cb)
        assert_equals(deque(), self.klass._bind_cb)
        assert_equals(deque(), self.klass._unbind_cb)
        assert_equals(deque(), self.klass._delete_cb)
        assert_equals(deque(), self.klass._purge_cb)

    def test_cleanup(self):
        self.klass._cleanup()
        assert_equals(None, self.klass._declare_cb)
        assert_equals(None, self.klass._bind_cb)
        assert_equals(None, self.klass._unbind_cb)
        assert_equals(None, self.klass._delete_cb)
        assert_equals(None, self.klass._purge_cb)
        assert_equals(None, self.klass._channel)
        assert_equals(None, self.klass.dispatch_map)

    def test_declare_default_args(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(mock(queue_class, 'Writer')).returns(w)
        expect(w.write_short).args(self.klass.default_ticket).returns(w)
        expect(w.write_shortstr).args('').returns(w)
        expect(w.write_bits).args(False, False, False, True, True).returns(w)
        expect(w.write_table).args({})
        expect(mock(queue_class, 'MethodFrame')).args(
            42, 50, 10, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        stub(self.klass.channel.add_synchronous_cb)

        assert_equals(deque(), self.klass._declare_cb)
        self.klass.declare()
        assert_equals(deque(), self.klass._declare_cb)

    def test_declare_with_args_and_no_cb(self):
        w = mock()
        stub(self.klass.allow_nowait)
        expect(mock(queue_class, 'Writer')).returns(w)
        expect(w.write_short).args('ticket').returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_bits).args('p', 'd', 'e', 'a', False).returns(w)
        expect(w.write_table).args({'foo': 'bar'})
        expect(mock(queue_class, 'MethodFrame')).args(
            42, 50, 10, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect( self.klass.channel.add_synchronous_cb ).args( self.klass._recv_declare_ok ).\
            returns('stuffs')

        assert_equals(deque(), self.klass._declare_cb)
        assert_equals('stuffs', self.klass.declare('queue', passive='p', durable='d', exclusive='e',
                                                   auto_delete='a', nowait=False, arguments={'foo': 'bar'}, ticket='ticket'))
        assert_equals(deque([None]), self.klass._declare_cb)

    def test_declare_with_args_and_cb(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(mock(queue_class, 'Writer')).returns(w)
        expect(w.write_short).args('ticket').returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_bits).args('p', 'd', 'e', 'a', False).returns(w)
        expect(w.write_table).args({'foo': 'bar'})
        expect(mock(queue_class, 'MethodFrame')).args(
            42, 50, 10, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect( self.klass.channel.add_synchronous_cb ).args( self.klass._recv_declare_ok ).\
            returns('stuffs')

        # assert it's put in the right spot too
        self.klass._declare_cb = deque(['blargh'])
        assert_equals('stuffs', self.klass.declare('queue', passive='p', durable='d', exclusive='e',
                                                   auto_delete='a', nowait=True, arguments={'foo': 'bar'}, ticket='ticket',
                                                   cb='callback'))
        assert_equals(deque(['blargh', 'callback']), self.klass._declare_cb)

    def test_recv_declare_ok_with_callback(self):
        rframe = mock()
        cb = mock()
        self.klass._declare_cb.append(cb)
        self.klass._declare_cb.append(mock())  # assert not called

        expect(rframe.args.read_shortstr).returns('queue')
        expect(rframe.args.read_long).returns(32)
        expect(rframe.args.read_long).returns(5)
        expect(cb).args('queue', 32, 5)

        assert_equals(('queue', 32, 5), self.klass._recv_declare_ok(rframe))
        assert_equals(1, len(self.klass._declare_cb))
        assert_false(cb in self.klass._declare_cb)

    def test_recv_declare_ok_without_callback(self):
        rframe = mock()
        cb = mock()
        self.klass._declare_cb.append(None)
        self.klass._declare_cb.append(cb)

        expect(rframe.args.read_shortstr).returns('queue')
        expect(rframe.args.read_long).returns(32)
        expect(rframe.args.read_long).returns(5)

        assert_equals(('queue', 32, 5), self.klass._recv_declare_ok(rframe))
        assert_equals(1, len(self.klass._declare_cb))
        assert_false(None in self.klass._declare_cb)

    def test_bind_default_args(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(mock(queue_class, 'Writer')).returns(w)
        expect(w.write_short).args(self.klass.default_ticket).returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_shortstr).args('exchange').returns(w)
        expect(w.write_shortstr).args('').returns(w)
        expect(w.write_bit).args(True).returns(w)
        expect(w.write_table).args({})
        expect(mock(queue_class, 'MethodFrame')).args(
            42, 50, 20, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        stub(self.klass.channel.add_synchronous_cb)

        assert_equals(deque(), self.klass._declare_cb)
        self.klass.bind('queue', 'exchange')
        assert_equals(deque(), self.klass._declare_cb)

    def test_bind_with_args_and_no_cb(self):
        w = mock()
        stub(self.klass.allow_nowait)
        expect(mock(queue_class, 'Writer')).returns(w)
        expect(w.write_short).args('ticket').returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_shortstr).args('exchange').returns(w)
        expect(w.write_shortstr).args('route').returns(w)
        expect(w.write_bit).args(False).returns(w)
        expect(w.write_table).args({'foo': 'bar'})
        expect(mock(queue_class, 'MethodFrame')).args(
            42, 50, 20, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_bind_ok)

        assert_equals(deque(), self.klass._bind_cb)
        self.klass.bind('queue', 'exchange', routing_key='route', nowait=False,
                        arguments={'foo': 'bar'}, ticket='ticket')
        assert_equals(deque([None]), self.klass._bind_cb)

    def test_bind_with_args_and_cb(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(mock(queue_class, 'Writer')).returns(w)
        expect(w.write_short).args('ticket').returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_shortstr).args('exchange').returns(w)
        expect(w.write_shortstr).args('route').returns(w)
        expect(w.write_bit).args(False).returns(w)
        expect(w.write_table).args({'foo': 'bar'})
        expect(mock(queue_class, 'MethodFrame')).args(
            42, 50, 20, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_bind_ok)

        self.klass._bind_cb = deque(['blargh'])
        self.klass.bind('queue', 'exchange', routing_key='route', nowait=True,
                        arguments={'foo': 'bar'}, ticket='ticket', cb='callback')
        assert_equals(deque(['blargh', 'callback']), self.klass._bind_cb)

    def test_recv_bind_ok_with_cb(self):
        cb = mock()
        self.klass._bind_cb.append(cb)
        self.klass._bind_cb.append(mock())  # assert not called

        expect(cb)

        self.klass._recv_bind_ok('frame')
        assert_equals(1, len(self.klass._bind_cb))
        assert_false(cb in self.klass._bind_cb)

    def test_recv_bind_ok_without_cb(self):
        self.klass._bind_cb.append(None)
        self.klass._bind_cb.append(mock())  # assert not called

        self.klass._recv_bind_ok('frame')
        assert_equals(1, len(self.klass._bind_cb))
        assert_false(None in self.klass._bind_cb)

    def test_unbind_default_args(self):
        w = mock()
        expect(mock(queue_class, 'Writer')).returns(w)
        expect(w.write_short).args(self.klass.default_ticket).returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_shortstr).args('exchange').returns(w)
        expect(w.write_shortstr).args('').returns(w)
        expect(w.write_table).args({})
        expect(mock(queue_class, 'MethodFrame')).args(
            42, 50, 50, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_unbind_ok)

        assert_equals(deque(), self.klass._unbind_cb)
        self.klass.unbind('queue', 'exchange')
        assert_equals(deque([None]), self.klass._unbind_cb)

    def test_unbind_with_args(self):
        w = mock()
        expect(mock(queue_class, 'Writer')).returns(w)
        expect(w.write_short).args('ticket').returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_shortstr).args('exchange').returns(w)
        expect(w.write_shortstr).args('route').returns(w)
        expect(w.write_table).args({'foo': 'bar'})
        expect(mock(queue_class, 'MethodFrame')).args(
            42, 50, 50, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_unbind_ok)

        self.klass._unbind_cb = deque(['blargh'])
        self.klass.unbind('queue', 'exchange', routing_key='route',
                          arguments={'foo': 'bar'}, ticket='ticket', cb='callback')
        assert_equals(deque(['blargh', 'callback']), self.klass._unbind_cb)

    def test_recv_unbind_ok_with_cb(self):
        cb = mock()
        self.klass._unbind_cb.append(cb)
        self.klass._unbind_cb.append(mock())  # assert not called

        expect(cb)

        self.klass._recv_unbind_ok('frame')
        assert_equals(1, len(self.klass._unbind_cb))
        assert_false(cb in self.klass._unbind_cb)

    def test_recv_unbind_ok_without_cb(self):
        self.klass._unbind_cb.append(None)
        self.klass._unbind_cb.append(mock())  # assert not called

        self.klass._recv_unbind_ok('frame')
        assert_equals(1, len(self.klass._unbind_cb))
        assert_false(None in self.klass._unbind_cb)

    def test_purge_default_args(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(mock(queue_class, 'Writer')).returns(w)
        expect(w.write_short).args(self.klass.default_ticket).returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_bit).args(True)
        expect(mock(queue_class, 'MethodFrame')).args(
            42, 50, 30, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        stub(self.klass.channel.add_synchronous_cb)

        assert_equals(deque(), self.klass._purge_cb)
        self.klass.purge('queue')
        assert_equals(deque(), self.klass._purge_cb)

    def test_purge_with_args_and_no_cb(self):
        w = mock()
        stub(self.klass.allow_nowait)
        expect(mock(queue_class, 'Writer')).returns(w)
        expect(w.write_short).args('ticket').returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_bit).args(False)
        expect(mock(queue_class, 'MethodFrame')).args(
            42, 50, 30, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_purge_ok).returns('fifty')

        assert_equals(deque(), self.klass._purge_cb)
        assert_equals(
            'fifty', self.klass.purge('queue', nowait=False, ticket='ticket'))
        assert_equals(deque([None]), self.klass._purge_cb)

    def test_purge_with_args_and_cb(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(mock(queue_class, 'Writer')).returns(w)
        expect(w.write_short).args('ticket').returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_bit).args(False)
        expect(mock(queue_class, 'MethodFrame')).args(
            42, 50, 30, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_purge_ok).returns('fifty')

        self.klass._purge_cb = deque(['blargh'])
        assert_equals('fifty', self.klass.purge(
            'queue', nowait=True, ticket='ticket', cb='callback'))
        assert_equals(deque(['blargh', 'callback']), self.klass._purge_cb)

    def test_recv_purge_ok_with_cb(self):
        rframe = mock()
        cb = mock()
        self.klass._purge_cb.append(cb)
        self.klass._purge_cb.append(mock())  # assert not called

        expect(rframe.args.read_long).returns(42)
        expect(cb).args(42)

        assert_equals(42, self.klass._recv_purge_ok(rframe))
        assert_equals(1, len(self.klass._purge_cb))
        assert_false(cb in self.klass._purge_cb)

    def test_recv_purge_ok_without_cb(self):
        rframe = mock()
        self.klass._purge_cb.append(None)
        self.klass._purge_cb.append(mock())  # assert not called

        expect(rframe.args.read_long).returns(42)

        assert_equals(42, self.klass._recv_purge_ok(rframe))
        assert_equals(1, len(self.klass._purge_cb))
        assert_false(None in self.klass._purge_cb)

    def test_delete_default_args(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(mock(queue_class, 'Writer')).returns(w)
        expect(w.write_short).args(self.klass.default_ticket).returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_bits).args(False, False, True)
        expect(mock(queue_class, 'MethodFrame')).args(
            42, 50, 40, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        stub(self.klass.channel.add_synchronous_cb)

        assert_equals(deque(), self.klass._delete_cb)
        self.klass.delete('queue')
        assert_equals(deque(), self.klass._delete_cb)

    def test_delete_with_args_and_no_cb(self):
        w = mock()
        stub(self.klass.allow_nowait)
        expect(mock(queue_class, 'Writer')).returns(w)
        expect(w.write_short).args('ticket').returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_bits).args('yes', 'no', False)
        expect(mock(queue_class, 'MethodFrame')).args(
            42, 50, 40, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_delete_ok).returns('five')

        assert_equals(deque(), self.klass._delete_cb)
        assert_equals('five', self.klass.delete('queue', if_unused='yes', if_empty='no', nowait=False,
                                                ticket='ticket'))
        assert_equals(deque([None]), self.klass._delete_cb)

    def test_delete_with_args_and_cb(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(mock(queue_class, 'Writer')).returns(w)
        expect(w.write_short).args('ticket').returns(w)
        expect(w.write_shortstr).args('queue').returns(w)
        expect(w.write_bits).args('yes', 'no', False)
        expect(mock(queue_class, 'MethodFrame')).args(
            42, 50, 40, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_delete_ok)

        self.klass._delete_cb = deque(['blargh'])
        self.klass.delete('queue', if_unused='yes', if_empty='no', nowait=True,
                          ticket='ticket', cb='callback')
        assert_equals(deque(['blargh', 'callback']), self.klass._delete_cb)

    def test_recv_delete_ok_with_cb(self):
        rframe = mock()
        cb = mock()
        self.klass._delete_cb.append(cb)
        self.klass._delete_cb.append(mock())  # assert not called

        expect(rframe.args.read_long).returns(42)
        expect(cb).args(42)

        self.klass._recv_delete_ok(rframe)
        assert_equals(1, len(self.klass._delete_cb))
        assert_false(cb in self.klass._delete_cb)

    def test_recv_delete_ok_without_cb(self):
        rframe = mock()
        self.klass._delete_cb.append(None)
        self.klass._delete_cb.append(mock())  # assert not called

        expect(rframe.args.read_long).returns(42)

        self.klass._recv_delete_ok(rframe)
        assert_equals(1, len(self.klass._delete_cb))
        assert_false(None in self.klass._delete_cb)

########NEW FILE########
__FILENAME__ = transaction_class_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai

from haigha.classes import transaction_class
from haigha.classes.protocol_class import ProtocolClass
from haigha.classes.transaction_class import TransactionClass
from haigha.frames.method_frame import MethodFrame
from haigha.writer import Writer

from collections import deque


class TransactionClassTest(Chai):

    def setUp(self):
        super(TransactionClassTest, self).setUp()
        ch = mock()
        ch.channel_id = 42
        ch.logger = mock()
        self.klass = TransactionClass(ch)

    def test_init(self):
        expect(ProtocolClass.__init__).args('foo', a='b')

        klass = TransactionClass.__new__(TransactionClass)
        klass.__init__('foo', a='b')

        assert_equals(
            {
                11: klass._recv_select_ok,
                21: klass._recv_commit_ok,
                31: klass._recv_rollback_ok,
            }, klass.dispatch_map)
        assert_false(klass._enabled)
        assert_equals(deque(), klass._select_cb)
        assert_equals(deque(), klass._commit_cb)
        assert_equals(deque(), klass._rollback_cb)

    def test_cleanup(self):
        self.klass._cleanup()
        assert_equals(None, self.klass._select_cb)
        assert_equals(None, self.klass._commit_cb)
        assert_equals(None, self.klass._rollback_cb)
        assert_equals(None, self.klass._channel)
        assert_equals(None, self.klass.dispatch_map)

    def test_properties(self):
        self.klass._enabled = 'maybe'
        assert_equals('maybe', self.klass.enabled)

    def test_select_when_not_enabled_and_no_cb(self):
        self.klass._enabled = False
        expect(mock(transaction_class, 'MethodFrame')).args(
            42, 90, 10).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_select_ok)

        self.klass.select()
        assert_true(self.klass.enabled)
        assert_equals(deque([None]), self.klass._select_cb)

    def test_select_when_not_enabled_with_cb(self):
        self.klass._enabled = False
        expect(mock(transaction_class, 'MethodFrame')).args(
            42, 90, 10).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_select_ok)

        self.klass.select(cb='foo')
        assert_true(self.klass.enabled)
        assert_equals(deque(['foo']), self.klass._select_cb)

    def test_select_when_already_enabled(self):
        self.klass._enabled = True
        stub(self.klass.send_frame)

        assert_equals(deque(), self.klass._select_cb)
        self.klass.select()
        assert_equals(deque(), self.klass._select_cb)

    def test_recv_select_ok_with_cb(self):
        cb = mock()
        self.klass._select_cb.append(cb)
        self.klass._select_cb.append(mock())
        expect(cb)
        self.klass._recv_select_ok('frame')
        assert_equals(1, len(self.klass._select_cb))
        assert_false(cb in self.klass._select_cb)

    def test_recv_select_ok_without_cb(self):
        self.klass._select_cb.append(None)
        self.klass._select_cb.append(mock())

        self.klass._recv_select_ok('frame')
        assert_equals(1, len(self.klass._select_cb))
        assert_false(None in self.klass._select_cb)

    def test_commit_when_enabled_no_cb(self):
        self.klass._enabled = True

        expect(mock(transaction_class, 'MethodFrame')).args(
            42, 90, 20).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_commit_ok)

        assert_equals(deque(), self.klass._commit_cb)
        self.klass.commit()
        assert_equals(deque([None]), self.klass._commit_cb)

    def test_commit_when_enabled_with_cb(self):
        self.klass._enabled = True

        expect(mock(transaction_class, 'MethodFrame')).args(
            42, 90, 20).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_commit_ok)

        self.klass._commit_cb = deque(['blargh'])
        self.klass.commit(cb='callback')
        assert_equals(deque(['blargh', 'callback']), self.klass._commit_cb)

    def test_commit_raises_transactionsnotenabled_when_not_enabled(self):
        self.klass._enabled = False
        assert_raises(
            TransactionClass.TransactionsNotEnabled, self.klass.commit)

    def test_recv_commit_ok_with_cb(self):
        cb = mock()
        self.klass._commit_cb.append(cb)
        self.klass._commit_cb.append(mock())
        expect(cb)

        self.klass._recv_commit_ok('frame')
        assert_equals(1, len(self.klass._commit_cb))
        assert_false(cb in self.klass._commit_cb)

    def test_recv_commit_ok_without_cb(self):
        self.klass._commit_cb.append(None)
        self.klass._commit_cb.append(mock())

        self.klass._recv_commit_ok('frame')
        assert_equals(1, len(self.klass._commit_cb))
        assert_false(None in self.klass._commit_cb)

    def test_rollback_when_enabled_no_cb(self):
        self.klass._enabled = True

        expect(mock(transaction_class, 'MethodFrame')).args(
            42, 90, 30).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_rollback_ok)

        assert_equals(deque(), self.klass._rollback_cb)
        self.klass.rollback()
        assert_equals(deque([None]), self.klass._rollback_cb)

    def test_rollback_when_enabled_with_cb(self):
        self.klass._enabled = True

        expect(mock(transaction_class, 'MethodFrame')).args(
            42, 90, 30).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_rollback_ok)

        self.klass._rollback_cb = deque(['blargh'])
        self.klass.rollback(cb='callback')
        assert_equals(deque(['blargh', 'callback']), self.klass._rollback_cb)

    def test_rollback_raises_transactionsnotenabled_when_not_enabled(self):
        self.klass._enabled = False
        assert_raises(
            TransactionClass.TransactionsNotEnabled, self.klass.rollback)

    def test_recv_rollback_ok_with_cb(self):
        cb = mock()
        self.klass._rollback_cb.append(cb)
        self.klass._rollback_cb.append(mock())
        expect(cb)

        self.klass._recv_rollback_ok('frame')
        assert_equals(1, len(self.klass._rollback_cb))
        assert_false(cb in self.klass._rollback_cb)

    def test_recv_rollback_ok_without_cb(self):
        self.klass._rollback_cb.append(None)
        self.klass._rollback_cb.append(mock())

        self.klass._recv_rollback_ok('frame')
        assert_equals(1, len(self.klass._rollback_cb))
        assert_false(None in self.klass._rollback_cb)

########NEW FILE########
__FILENAME__ = rabbit_connection_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from collections import deque
import logging
from chai import Chai

from haigha.connections import rabbit_connection
from haigha.connections.rabbit_connection import *
from haigha.connection import Connection
from haigha.writer import Writer
from haigha.frames import *
from haigha.classes import *


class RabbitConnectionTest(Chai):

    def test_init(self):
        with expect(mock(rabbit_connection, 'super')).args(is_arg(RabbitConnection), RabbitConnection).returns(mock()) as c:
            expect(c.__init__).args(class_map=var('classes'), foo='bar')

        rc = RabbitConnection(foo='bar')
        assert_equals(var('classes').value, {
            40: RabbitExchangeClass,
            60: RabbitBasicClass,
            85: RabbitConfirmClass
        })


class RabbitExchangeClassTest(Chai):

    def setUp(self):
        super(RabbitExchangeClassTest, self).setUp()
        ch = mock()
        ch.channel_id = 42
        ch.logger = mock()
        self.klass = RabbitExchangeClass(ch)

    def test_init(self):
        assert_equals(self.klass.dispatch_map[31], self.klass._recv_bind_ok)
        assert_equals(self.klass.dispatch_map[51], self.klass._recv_unbind_ok)
        assert_equals(deque(), self.klass._bind_cb)
        assert_equals(deque(), self.klass._unbind_cb)

    def test_declare_default_args(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(mock(rabbit_connection, 'Writer')).returns(w)
        expect(w.write_short).args(self.klass.default_ticket).returns(w)
        expect(w.write_shortstr).args('exchange').returns(w)
        expect(w.write_shortstr).args('topic').returns(w)
        expect(w.write_bits).args(False, False, True, False, True).returns(w)
        expect(w.write_table).args({})
        expect(mock(rabbit_connection, 'MethodFrame')).args(
            42, 40, 10, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        stub(self.klass.channel.add_synchronous_cb)

        self.klass.declare('exchange', 'topic')
        assert_equals(deque(), self.klass._declare_cb)

    def test_declare_with_args(self):
        w = mock()
        stub(self.klass.allow_nowait)
        expect(mock(rabbit_connection, 'Writer')).returns(w)
        expect(w.write_short).args('t').returns(w)
        expect(w.write_shortstr).args('exchange').returns(w)
        expect(w.write_shortstr).args('topic').returns(w)
        expect(w.write_bits).args('p', 'd', 'ad', 'yes', False).returns(w)
        expect(w.write_table).args('table')
        expect(mock(rabbit_connection, 'MethodFrame')).args(
            42, 40, 10, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_declare_ok)

        self.klass.declare('exchange', 'topic', passive='p', durable='d',
                           nowait=False, arguments='table', ticket='t',
                           auto_delete='ad', internal='yes')
        assert_equals(deque([None]), self.klass._declare_cb)

    def test_declare_with_cb(self):
        w = mock()
        expect(self.klass.allow_nowait).returns(True)
        expect(mock(rabbit_connection, 'Writer')).returns(w)
        expect(w.write_short).args('t').returns(w)
        expect(w.write_shortstr).args('exchange').returns(w)
        expect(w.write_shortstr).args('topic').returns(w)
        expect(w.write_bits).args('p', 'd', True, False, False).returns(w)
        expect(w.write_table).args('table')
        expect(mock(rabbit_connection, 'MethodFrame')).args(
            42, 40, 10, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_declare_ok)

        self.klass.declare('exchange', 'topic', passive='p', durable='d',
                           nowait=True, arguments='table', ticket='t', cb='foo')
        assert_equals(deque(['foo']), self.klass._declare_cb)

    def test_bind_default_args(self):
        w = mock()

        expect(self.klass.allow_nowait).returns(True)
        expect(mock(rabbit_connection, 'Writer')).returns(w)
        expect(w.write_short).args(0).returns(w)
        expect(w.write_shortstr).args('destination').returns(w)
        expect(w.write_shortstr).args('source').returns(w)
        expect(w.write_shortstr).args('').returns(w)
        expect(w.write_bit).args(True).returns(w)
        expect(w.write_table).args({})
        expect(mock(rabbit_connection, 'MethodFrame')).args(
            42, 40, 30, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        self.klass.bind('destination', 'source')
        assert_equals(deque(), self.klass._bind_cb)

    def test_bind_with_args(self):
        w = mock()

        stub(self.klass.allow_nowait)
        expect(mock(rabbit_connection, 'Writer')).returns(w)
        expect(w.write_short).args('t').returns(w)
        expect(w.write_shortstr).args('destination').returns(w)
        expect(w.write_shortstr).args('source').returns(w)
        expect(w.write_shortstr).args('route').returns(w)
        expect(w.write_bit).args(False).returns(w)
        expect(w.write_table).args('table')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_bind_ok)
        expect(mock(rabbit_connection, 'MethodFrame')).args(
            42, 40, 30, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        self.klass.bind('destination', 'source', routing_key='route',
                        ticket='t', nowait=False, arguments='table')
        assert_equals(deque([None]), self.klass._bind_cb)

    def test_bind_with_cb(self):
        w = mock()

        expect(self.klass.allow_nowait).returns(True)
        expect(mock(rabbit_connection, 'Writer')).returns(w)
        expect(w.write_short).args('t').returns(w)
        expect(w.write_shortstr).args('destination').returns(w)
        expect(w.write_shortstr).args('source').returns(w)
        expect(w.write_shortstr).args('route').returns(w)
        expect(w.write_bit).args(False).returns(w)
        expect(w.write_table).args('table')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_bind_ok)
        expect(mock(rabbit_connection, 'MethodFrame')).args(
            42, 40, 30, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        self.klass.bind('destination', 'source', routing_key='route',
                        ticket='t', arguments='table', cb='foo')
        assert_equals(deque(['foo']), self.klass._bind_cb)

    def test_recv_bind_ok_no_cb(self):
        self.klass._bind_cb = deque([None])
        self.klass._recv_bind_ok('frame')
        assert_equals(deque(), self.klass._bind_cb)

    def test_recv_bind_ok_with_cb(self):
        cb = mock()
        self.klass._bind_cb = deque([cb])
        expect(cb)
        self.klass._recv_bind_ok('frame')
        assert_equals(deque(), self.klass._bind_cb)

    def test_unbind_default_args(self):
        w = mock()

        expect(self.klass.allow_nowait).returns(True)
        expect(mock(rabbit_connection, 'Writer')).returns(w)
        expect(w.write_short).args(0).returns(w)
        expect(w.write_shortstr).args('destination').returns(w)
        expect(w.write_shortstr).args('source').returns(w)
        expect(w.write_shortstr).args('').returns(w)
        expect(w.write_bit).args(True).returns(w)
        expect(w.write_table).args({})
        expect(mock(rabbit_connection, 'MethodFrame')).args(
            42, 40, 40, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        self.klass.unbind('destination', 'source')
        assert_equals(deque(), self.klass._unbind_cb)

    def test_unbind_with_args(self):
        w = mock()

        stub(self.klass.allow_nowait)
        expect(mock(rabbit_connection, 'Writer')).returns(w)
        expect(w.write_short).args('t').returns(w)
        expect(w.write_shortstr).args('destination').returns(w)
        expect(w.write_shortstr).args('source').returns(w)
        expect(w.write_shortstr).args('route').returns(w)
        expect(w.write_bit).args(False).returns(w)
        expect(w.write_table).args('table')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_unbind_ok)
        expect(mock(rabbit_connection, 'MethodFrame')).args(
            42, 40, 40, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        self.klass.unbind('destination', 'source', routing_key='route',
                          ticket='t', nowait=False, arguments='table')
        assert_equals(deque([None]), self.klass._unbind_cb)

    def test_unbind_with_cb(self):
        w = mock()

        expect(self.klass.allow_nowait).returns(True)
        expect(mock(rabbit_connection, 'Writer')).returns(w)
        expect(w.write_short).args('t').returns(w)
        expect(w.write_shortstr).args('destination').returns(w)
        expect(w.write_shortstr).args('source').returns(w)
        expect(w.write_shortstr).args('route').returns(w)
        expect(w.write_bit).args(False).returns(w)
        expect(w.write_table).args('table')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_unbind_ok)
        expect(mock(rabbit_connection, 'MethodFrame')).args(
            42, 40, 40, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        self.klass.unbind('destination', 'source', routing_key='route',
                          ticket='t', arguments='table', cb='foo')
        assert_equals(deque(['foo']), self.klass._unbind_cb)

    def test_recv_unbind_ok_no_cb(self):
        self.klass._unbind_cb = deque([None])
        self.klass._recv_unbind_ok('frame')
        assert_equals(deque(), self.klass._unbind_cb)

    def test_recv_unbind_ok_with_cb(self):
        cb = mock()
        self.klass._unbind_cb = deque([cb])
        expect(cb)
        self.klass._recv_unbind_ok('frame')
        assert_equals(deque(), self.klass._unbind_cb)


class RabbitBasicClassTest(Chai):

    def setUp(self):
        super(RabbitBasicClassTest, self).setUp()
        ch = mock()
        ch.channel_id = 42
        ch.logger = mock()
        self.klass = RabbitBasicClass(ch)

    def test_init(self):
        assert_equals(self.klass.dispatch_map[80], self.klass._recv_ack)
        assert_equals(self.klass.dispatch_map[120], self.klass._recv_nack)
        assert_equals(None, self.klass._ack_listener)
        assert_equals(None, self.klass._nack_listener)
        assert_equals(0, self.klass._msg_id)
        assert_equals(0, self.klass._last_ack_id)

    def test_set_ack_listener(self):
        self.klass.set_ack_listener('foo')
        assert_equals('foo', self.klass._ack_listener)

    def test_set_nack_listener(self):
        self.klass.set_nack_listener('foo')
        assert_equals('foo', self.klass._nack_listener)

    def test_publish_when_not_confirming(self):
        self.klass.channel.confirm._enabled = False
        with expect(mock(rabbit_connection, 'super')).args(
                is_arg(RabbitBasicClass), RabbitBasicClass).returns(mock()) as klass:
            expect(klass.publish).args('a', 'b', c='d')

        assert_equals(0, self.klass.publish('a', 'b', c='d'))
        assert_equals(0, self.klass._msg_id)

    def test_publish_when_confirming(self):
        self.klass.channel.confirm._enabled = True
        with expect(mock(rabbit_connection, 'super')).args(
                is_arg(RabbitBasicClass), RabbitBasicClass).returns(mock()) as klass:
            expect(klass.publish).args('a', 'b', c='d')

        assert_equals(1, self.klass.publish('a', 'b', c='d'))
        assert_equals(1, self.klass._msg_id)

    def test_recv_ack_no_listener(self):
        self.klass._recv_ack('frame')

    def test_recv_ack_with_listener_single_msg(self):
        self.klass._ack_listener = mock()
        frame = mock()
        expect(frame.args.read_longlong).returns(42)
        expect(frame.args.read_bit).returns(False)
        expect(self.klass._ack_listener).args(42)

        self.klass._recv_ack(frame)
        assert_equals(42, self.klass._last_ack_id)

    def test_recv_ack_with_listener_multiple_msg(self):
        self.klass._ack_listener = mock()
        self.klass._last_ack_id = 40
        frame = mock()
        expect(frame.args.read_longlong).returns(42)
        expect(frame.args.read_bit).returns(True)
        expect(self.klass._ack_listener).args(41)
        expect(self.klass._ack_listener).args(42)

        self.klass._recv_ack(frame)
        assert_equals(42, self.klass._last_ack_id)

    def test_nack_default_args(self):
        w = mock()
        expect(mock(rabbit_connection, 'Writer')).returns(w)
        expect(w.write_longlong).args(8675309).returns(w)
        expect(w.write_bits).args(False, False)
        expect(mock(rabbit_connection, 'MethodFrame')).args(
            42, 60, 120, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        self.klass.nack(8675309)

    def test_nack_with_args(self):
        w = mock()
        expect(mock(rabbit_connection, 'Writer')).returns(w)
        expect(w.write_longlong).args(8675309).returns(w)
        expect(w.write_bits).args('many', 'sure')
        expect(mock(rabbit_connection, 'MethodFrame')).args(
            42, 60, 120, w).returns('frame')
        expect(self.klass.send_frame).args('frame')

        self.klass.nack(8675309, multiple='many', requeue='sure')

    def test_recv_nack_no_listener(self):
        self.klass._recv_nack('frame')

    def test_recv_nack_with_listener_single_msg(self):
        self.klass._nack_listener = mock()
        frame = mock()
        expect(frame.args.read_longlong).returns(42)
        expect(frame.args.read_bits).args(2).returns((False, False))
        expect(self.klass._nack_listener).args(42, False)

        self.klass._recv_nack(frame)
        assert_equals(42, self.klass._last_ack_id)

    def test_recv_nack_with_listener_multiple_msg(self):
        self.klass._nack_listener = mock()
        self.klass._last_ack_id = 40
        frame = mock()
        expect(frame.args.read_longlong).returns(42)
        expect(frame.args.read_bits).args(2).returns((True, True))
        expect(self.klass._nack_listener).args(41, True)
        expect(self.klass._nack_listener).args(42, True)

        self.klass._recv_nack(frame)
        assert_equals(42, self.klass._last_ack_id)


class RabbitConfirmClassTest(Chai):

    def setUp(self):
        super(RabbitConfirmClassTest, self).setUp()
        ch = mock()
        ch.channel_id = 42
        ch.logger = mock()
        self.klass = RabbitConfirmClass(ch)

    def test_init(self):
        assert_equals(
            {11: self.klass._recv_select_ok}, self.klass.dispatch_map)
        assert_false(self.klass._enabled)
        assert_equals(deque(), self.klass._select_cb)

    def test_name(self):
        assert_equals('confirm', self.klass.name)

    def test_select_when_not_enabled_and_no_cb(self):
        self.klass._enabled = False
        w = mock()
        expect(mock(rabbit_connection, 'Writer')).returns(w)
        expect(self.klass.allow_nowait).returns(True)
        expect(w.write_bit).args(True)
        expect(mock(rabbit_connection, 'MethodFrame')).args(
            42, 85, 10, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        stub(self.klass.channel.add_synchronous_cb)

        self.klass.select()
        assert_true(self.klass._enabled)
        assert_equals(deque(), self.klass._select_cb)

    def test_select_when_not_enabled_and_no_cb_but_synchronous(self):
        self.klass._enabled = False
        w = mock()
        expect(mock(rabbit_connection, 'Writer')).returns(w)
        stub(self.klass.allow_nowait)
        expect(w.write_bit).args(False)
        expect(mock(rabbit_connection, 'MethodFrame')).args(
            42, 85, 10, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_select_ok)

        self.klass.select(nowait=False)
        assert_true(self.klass._enabled)
        assert_equals(deque([None]), self.klass._select_cb)

    def test_select_when_not_enabled_with_cb(self):
        self.klass._enabled = False
        w = mock()
        expect(mock(rabbit_connection, 'Writer')).returns(w)
        expect(self.klass.allow_nowait).returns(True)
        expect(w.write_bit).args(False)
        expect(mock(rabbit_connection, 'MethodFrame')).args(
            42, 85, 10, w).returns('frame')
        expect(self.klass.send_frame).args('frame')
        expect(self.klass.channel.add_synchronous_cb).args(
            self.klass._recv_select_ok)

        self.klass.select(cb='foo')
        assert_true(self.klass._enabled)
        assert_equals(deque(['foo']), self.klass._select_cb)

    def test_select_when_already_enabled(self):
        self.klass._enabled = True
        stub(self.klass.allow_nowait)
        stub(self.klass.send_frame)
        expect(self.klass.allow_nowait).returns(True)

        assert_equals(deque(), self.klass._select_cb)
        self.klass.select()
        assert_equals(deque(), self.klass._select_cb)

    def test_recv_select_ok_no_cb(self):
        self.klass._select_cb = deque([None])
        self.klass._recv_select_ok('frame')
        assert_equals(deque(), self.klass._select_cb)

    def test_recv_select_ok_with_cb(self):
        cb = mock()
        self.klass._select_cb = deque([cb])
        expect(cb)
        self.klass._recv_select_ok('frame')
        assert_equals(deque(), self.klass._select_cb)

########NEW FILE########
__FILENAME__ = connection_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

import logging
from chai import Chai

from haigha import connection, __version__
from haigha.connection import Connection, ConnectionChannel, ConnectionError, ConnectionClosed
from haigha.channel import Channel
from haigha.frames.frame import Frame
from haigha.frames.method_frame import MethodFrame
from haigha.frames.heartbeat_frame import HeartbeatFrame
from haigha.frames.header_frame import HeaderFrame
from haigha.frames.content_frame import ContentFrame
from haigha.classes.basic_class import BasicClass
from haigha.classes.channel_class import ChannelClass
from haigha.classes.exchange_class import ExchangeClass
from haigha.classes.queue_class import QueueClass
from haigha.classes.transaction_class import TransactionClass
from haigha.classes.protocol_class import ProtocolClass

from haigha.transports import event_transport
from haigha.transports import gevent_transport
from haigha.transports import socket_transport


class ConnectionTest(Chai):

    def setUp(self):
        super(ConnectionTest, self).setUp()

        self.connection = Connection.__new__(Connection)
        self.connection._debug = False
        self.connection._logger = self.mock()
        self.connection._user = 'guest'
        self.connection._password = 'guest'
        self.connection._host = 'localhost'
        self.connection._vhost = '/'
        self.connection._connect_timeout = 5
        self.connection._sock_opts = None
        self.connection._sock = None  # mock anything?
        self.connection._heartbeat = None
        self.connection._open_cb = self.mock()
        self.connection._close_cb = self.mock()
        self.connection._login_method = 'AMQPLAIN'
        self.connection._locale = 'en_US'
        self.connection._client_properties = None
        self.connection._properties = {
            'library': 'Haigha',
            'library_version': 'x.y.z',
        }
        self.connection._closed = False
        self.connection._connected = False
        self.connection._close_info = {
            'reply_code': 0,
            'reply_text': 'first connect',
            'class_id': 0,
            'method_id': 0
        }
        self.connection._class_map = {}
        self.connection._channels = {
            0: self.mock()
        }
        self.connection._login_response = 'loginresponse'
        self.connection._channel_counter = 0
        self.connection._channel_max = 65535
        self.connection._frame_max = 65535
        self.connection._frames_read = 0
        self.connection._frames_written = 0
        self.connection._strategy = self.mock()
        self.connection._output_frame_buffer = []
        self.connection._transport = mock()
        self.connection._synchronous = False
        self.connection._synchronous_connect = False

    def test_init_without_keyword_args(self):
        conn = Connection.__new__(Connection)
        strategy = mock()
        transport = mock()
        mock(connection, 'ConnectionChannel')

        expect(connection.ConnectionChannel).args(
            conn, 0, {}).returns('connection_channel')
        expect(socket_transport.SocketTransport).args(conn).returns(transport)
        expect(conn.connect).args('localhost', 5672)

        conn.__init__()

        assert_false(conn._debug)
        assert_equal(logging.root, conn._logger)
        assert_equal('guest', conn._user)
        assert_equal('guest', conn._password)
        assert_equal('localhost', conn._host)
        assert_equal(5672, conn._port)
        assert_equal('/', conn._vhost)
        assert_equal(5, conn._connect_timeout)
        assert_equal(None, conn._sock_opts)
        assert_equal(None, conn._sock)
        assert_equal(None, conn._heartbeat)
        assert_equal(None, conn._open_cb)
        assert_equal(None, conn._close_cb)
        assert_equal('AMQPLAIN', conn._login_method)
        assert_equal('en_US', conn._locale)
        assert_equal(None, conn._client_properties)
        assert_equal(conn._properties, {
            'library': 'Haigha',
            'library_version': __version__,
        })
        assert_false(conn._closed)
        assert_false(conn._connected)
        assert_equal(conn._close_info, {
            'reply_code': 0,
            'reply_text': 'first connect',
            'class_id': 0,
            'method_id': 0
        })
        assert_equals({
            20: ChannelClass,
            40: ExchangeClass,
            50: QueueClass,
            60: BasicClass,
            90: TransactionClass
        }, conn._class_map)
        assert_equal({0: 'connection_channel'}, conn._channels)
        assert_equal(
            '\x05LOGINS\x00\x00\x00\x05guest\x08PASSWORDS\x00\x00\x00\x05guest', conn._login_response)
        assert_equal(0, conn._channel_counter)
        assert_equal(65535, conn._channel_max)
        assert_equal(65535, conn._frame_max)
        assert_equal([], conn._output_frame_buffer)
        assert_equal(transport, conn._transport)

        transport.synchronous = True
        assert_false(conn._synchronous)
        assert_true(conn.synchronous)
        assert_true(conn._synchronous_connect)

    def test_init_with_event_transport(self):
        conn = Connection.__new__(Connection)
        strategy = mock()
        transport = mock()

        mock(connection, 'ConnectionChannel')

        expect(connection.ConnectionChannel).args(
            conn, 0, {}).returns('connection_channel')
        expect(event_transport.EventTransport).args(conn).returns(transport)
        expect(conn.connect).args('localhost', 5672)

        conn.__init__(transport='event')

    def test_properties(self):
        assert_equal(self.connection._logger, self.connection.logger)
        assert_equal(self.connection._debug, self.connection.debug)
        assert_equal(self.connection._frame_max, self.connection.frame_max)
        assert_equal(self.connection._channel_max, self.connection.channel_max)
        assert_equal(self.connection._frames_read, self.connection.frames_read)
        assert_equal(
            self.connection._frames_written, self.connection.frames_written)
        assert_equal(self.connection._closed, self.connection.closed)
        # sync property tested in the test_inits

    def test_synchronous_when_no_transport(self):
        self.connection._transport = None
        with assert_raises(connection.ConnectionClosed):
            self.connection.synchronous

        self.connection._close_info = {
            'reply_code': 100,
            'reply_text': 'breakdown'
        }
        with assert_raises(connection.ConnectionClosed):
            self.connection.synchronous

    def test_synchronous_when_transport(self):
        self.connection._transport.synchronous = True
        assert_true(self.connection.synchronous)
        self.connection._transport.synchronous = False
        assert_false(self.connection.synchronous)

    def test_connect_when_asynchronous_transport(self):
        self.connection._transport.synchronous = False
        self.connection._connected = 'maybe'
        self.connection._closed = 'possibly'
        self.connection._debug = 'sure'
        self.connection._connect_timeout = 42
        self.connection._sock_opts = {
            ('f1', 't1'): 5,
            ('f2', 't2'): 6
        }

        expect(self.connection._transport.connect).args(('host', 5672))
        expect(self.connection._transport.write).args('AMQP\x00\x00\x09\x01')

        self.connection.connect('host', 5672)
        assert_false(self.connection._connected)
        assert_false(self.connection._closed)
        assert_equals(self.connection._close_info,
                      {
                          'reply_code': 0,
                          'reply_text': 'failed to connect to host:5672',
                          'class_id': 0,
                          'method_id': 0
                      })
        assert_equals('host:5672', self.connection._host)

    def test_connect_when_asynchronous_transport_but_synchronous_connect(self):
        self.connection._transport.synchronous = False
        self.connection._synchronous_connect = True
        self.connection._connected = 'maybe'
        self.connection._closed = 'possibly'
        self.connection._debug = 'sure'
        self.connection._connect_timeout = 42
        self.connection._sock_opts = {
            ('f1', 't1'): 5,
            ('f2', 't2'): 6
        }

        expect(self.connection._transport.connect).args(('host', 5672))
        expect(self.connection._transport.write).args('AMQP\x00\x00\x09\x01')
        expect(self.connection._channels[0].add_synchronous_cb).args(
            self.connection._channels[0]._recv_start)

        expect(self.connection.read_frames)
        expect(self.connection.read_frames).side_effect(
            lambda: setattr(self.connection, '_connected', True))

        self.connection.connect('host', 5672)
        assert_true(self.connection._connected)
        assert_false(self.connection._closed)
        assert_equals(self.connection._close_info,
                      {
                          'reply_code': 0,
                          'reply_text': 'failed to connect to host:5672',
                          'class_id': 0,
                          'method_id': 0
                      })
        assert_equals('host:5672', self.connection._host)

    def test_connect_when_synchronous_transport(self):
        self.connection._transport.synchronous = True
        # would have been written in ctor
        self.connection._synchronous_connect = True
        self.connection._connected = 'maybe'
        self.connection._closed = 'possibly'
        self.connection._debug = 'sure'
        self.connection._connect_timeout = 42
        self.connection._sock_opts = {
            ('f1', 't1'): 5,
            ('f2', 't2'): 6
        }

        expect(self.connection._transport.connect).args(('host', 5672))
        expect(self.connection._transport.write).args('AMQP\x00\x00\x09\x01')
        expect(self.connection._channels[0].add_synchronous_cb)

        expect(self.connection.read_frames)
        expect(self.connection.read_frames).side_effect(
            lambda: setattr(self.connection, '_connected', True))

        self.connection.connect('host', 5672)
        assert_true(self.connection._connected)
        assert_false(self.connection._closed)
        assert_equals(self.connection._close_info,
                      {
                          'reply_code': 0,
                          'reply_text': 'failed to connect to host:5672',
                          'class_id': 0,
                          'method_id': 0
                      })
        assert_equals('host:5672', self.connection._host)

    def test_disconnect_when_transport_disconnects(self):
        self.connection._connected = 'yup'

        expect(self.connection._transport.disconnect)
        self.connection.disconnect()

        assert_false(self.connection._connected)
        assert_equals(None, self.connection._transport)

    def test_disconnect_when_transport_disconnects_with_error(self):
        self.connection._connected = 'yup'
        self.connection._host = 'server'

        expect(self.connection._transport.disconnect).raises(
            RuntimeError('fail'))
        expect(self.connection.logger.error).args(
            "Failed to disconnect from %s", 'server', exc_info=True)
        assert_raises(RuntimeError, self.connection.disconnect)

        assert_false(self.connection._connected)
        assert_equals(None, self.connection._transport)

    def test_disconnect_when_systemexit(self):
        self.connection._connected = 'yup'
        self.connection._host = 'server'

        expect(self.connection._transport.disconnect).raises(SystemExit())
        stub(self.connection.logger.error)
        assert_raises(SystemExit, self.connection.disconnect)

        assert_false(self.connection._connected)
        assert_equals(None, self.connection._transport)

    def test_transport_closed_with_no_args(self):
        self.connection._host = 'server'
        self.connection._connected = 'yes'

        expect(self.connection.logger.warning).args(
            'transport to server closed : unknown cause')
        expect(self.connection._callback_close)

        self.connection.transport_closed()

        assert_equals(0, self.connection._close_info['reply_code'])
        assert_equals(
            'unknown cause', self.connection._close_info['reply_text'])
        assert_equals(0, self.connection._close_info['class_id'])
        assert_equals(0, self.connection._close_info['method_id'])

    def test_next_channel_id_when_less_than_max(self):
        self.connection._channel_counter = 32
        self.connection._channel_max = 23423
        assert_equals(33, self.connection._next_channel_id())

    def test_next_channel_id_when_at_max(self):
        self.connection._channel_counter = 32
        self.connection._channel_max = 32
        assert_equals(1, self.connection._next_channel_id())

    def test_channel_creates_new_when_not_at_limit(self):
        ch = mock()
        expect(self.connection._next_channel_id).returns(1)
        mock(connection, 'Channel')
        expect(connection.Channel).args(
            self.connection, 1, self.connection._class_map, synchronous=False).returns(ch)
        expect(ch.add_close_listener).args(self.connection._channel_closed)
        expect(ch.open)

        assert_equals(ch, self.connection.channel())
        assert_equals(ch, self.connection._channels[1])

    def test_channel_creates_optionally_synchronous(self):
        ch = mock()
        expect(self.connection._next_channel_id).returns(1)
        mock(connection, 'Channel')
        expect(connection.Channel).args(
            self.connection, 1, self.connection._class_map, synchronous=True).returns(ch)
        expect(ch.add_close_listener).args(self.connection._channel_closed)
        expect(ch.open)

        assert_equals(ch, self.connection.channel(synchronous=True))
        assert_equals(ch, self.connection._channels[1])

    def test_channel_finds_the_first_free_channel_id(self):
        self.connection._channels[1] = 'foo'
        self.connection._channels[2] = 'bar'
        self.connection._channels[4] = 'cat'
        ch = mock()
        expect(self.connection._next_channel_id).returns(1)
        expect(self.connection._next_channel_id).returns(2)
        expect(self.connection._next_channel_id).returns(3)
        mock(connection, 'Channel')
        expect(connection.Channel).args(
            self.connection, 3, self.connection._class_map, synchronous=False).returns(ch)
        expect(ch.add_close_listener).args(self.connection._channel_closed)
        expect(ch.open)

        assert_equals(ch, self.connection.channel())
        assert_equals(ch, self.connection._channels[3])

    def test_channel_raises_toomanychannels(self):
        self.connection._channels[1] = 'foo'
        self.connection._channels[2] = 'bar'
        self.connection._channels[4] = 'cat'
        self.connection._channel_max = 3
        assert_raises(Connection.TooManyChannels, self.connection.channel)

    def test_channel_returns_cached_instance_if_known(self):
        self.connection._channels[1] = 'foo'
        assert_equals('foo', self.connection.channel(1))

    def test_channel_raises_invalidchannel_if_unknown_id(self):
        assert_raises(Connection.InvalidChannel, self.connection.channel, 42)

    def test_channel_closed(self):
        ch = mock()
        ch.channel_id = 42
        self.connection._channels[42] = ch

        self.connection._channel_closed(ch)
        assert_false(42 in self.connection._channels)

        ch.channel_id = 500424834
        self.connection._channel_closed(ch)

    def test_close(self):
        self.connection._channels[0] = mock()
        expect(self.connection._channels[0].close)

        self.connection.close()
        assert_equals({'reply_code': 0, 'reply_text': '', 'class_id': 0, 'method_id': 0},
                      self.connection._close_info)

        self.connection.close(1, 'foo', 2, 3)
        assert_equals({'reply_code': 1, 'reply_text': 'foo', 'class_id': 2, 'method_id': 3},
                      self.connection._close_info)

    def test_close_when_disconnect(self):
        self.connection._channels[0] = mock()
        stub(self.connection._channels[0].close)

        assert_false(self.connection._closed)
        expect(self.connection.disconnect)
        expect(self.connection._callback_close)
        self.connection.close(1, 'foo', 2, 3, disconnect=True)
        assert_true(self.connection._closed)
        assert_equals({'reply_code': 1, 'reply_text': 'foo', 'class_id': 2, 'method_id': 3},
                      self.connection._close_info)

    def test_callback_open_when_no_cb(self):
        self.connection._open_cb = None
        self.connection._callback_open()

    def test_callback_open_when_user_cb(self):
        self.connection._open_cb = mock()
        expect(self.connection._open_cb)
        self.connection._callback_open()

    def test_callback_open_raises_when_user_cb_does(self):
        self.connection._open_cb = mock()
        expect(self.connection._open_cb).raises(SystemExit())
        assert_raises(SystemExit, self.connection._callback_open)

    def test_callback_close_when_no_cb(self):
        self.connection._close_cb = None
        self.connection._callback_close()

    def test_callback_close_when_user_cb(self):
        self.connection._close_cb = mock()
        expect(self.connection._close_cb)
        self.connection._callback_close()

    def test_callback_close_raises_when_user_cb_does(self):
        self.connection._close_cb = mock()
        expect(self.connection._close_cb).raises(SystemExit())
        assert_raises(SystemExit, self.connection._callback_close)

    def test_read_frames_when_no_transport(self):
        self.connection._transport = None
        self.connection.read_frames()
        assert_equals(0, self.connection._frames_read)

    def test_read_frames_when_transport_returns_no_data(self):
        self.connection._heartbeat = None
        expect(self.connection._channels[0].send_heartbeat)
        expect(self.connection._transport.read).args(None).returns(None)
        self.connection.read_frames()
        assert_equals(0, self.connection._frames_read)

    def test_read_frames_when_transport_when_frame_data_and_no_debug_and_no_buffer(self):
        reader = mock()
        frame = mock()
        frame.channel_id = 42
        channel = mock()
        mock(connection, 'Reader')
        self.connection._heartbeat = 3

        expect(self.connection._channels[0].send_heartbeat)
        expect(self.connection._transport.read).args(3).returns('data')
        expect(connection.Reader).args('data').returns(reader)
        expect(connection.Frame.read_frames).args(reader).returns([frame])
        expect(self.connection.channel).args(42).returns(channel)
        expect(channel.buffer_frame).args(frame)
        expect(self.connection._transport.process_channels).args(
            set([channel]))
        expect(reader.tell).returns(4)

        self.connection.read_frames()
        assert_equals(1, self.connection._frames_read)

    def test_read_frames_when_transport_when_frame_data_and_debug_and_buffer(self):
        reader = mock()
        frame = mock()
        frame.channel_id = 42
        channel = mock()
        mock(connection, 'Reader')
        self.connection._debug = 2

        expect(self.connection._channels[0].send_heartbeat)
        expect(self.connection._transport.read).args(None).returns('data')
        expect(connection.Reader).args('data').returns(reader)
        expect(connection.Frame.read_frames).args(reader).returns([frame])
        expect(self.connection.logger.debug).args('READ: %s', frame)
        expect(self.connection.channel).args(42).returns(channel)
        expect(channel.buffer_frame).args(frame)
        expect(self.connection._transport.process_channels).args(
            set([channel]))
        expect(reader.tell).times(2).returns(2)
        expect(self.connection._transport.buffer).args('ta')

        self.connection.read_frames()
        assert_equals(1, self.connection._frames_read)

    def test_read_frames_when_read_frame_error(self):
        reader = mock()
        frame = mock()
        frame.channel_id = 42
        channel = mock()
        mock(connection, 'Reader')
        self.connection._heartbeat = 3

        expect(self.connection._channels[0].send_heartbeat)
        expect(self.connection._transport.read).args(3).returns('data')
        expect(connection.Reader).args('data').returns(reader)
        expect(connection.Frame.read_frames).args(
            reader).raises(Frame.FrameError)
        stub(self.connection.channel)
        stub(channel.buffer_frame)
        stub(self.connection._transport.process_channels)
        stub(reader.tell)
        stub(self.connection._transport.buffer)
        expect(self.connection.close).args(
            reply_code=501, reply_text=str, class_id=0, method_id=0, disconnect=True)

        assert_raises(ConnectionError, self.connection.read_frames)

    def test_flush_buffered_frames(self):
        self.connection._output_frame_buffer = ['frame1', 'frame2']
        expect(self.connection.send_frame).args('frame1')
        expect(self.connection.send_frame).args('frame2')

        self.connection._flush_buffered_frames()
        assert_equals([], self.connection._output_frame_buffer)

    def test_send_frame_when_connected_and_transport_and_no_debug(self):
        frame = mock()
        expect(frame.write_frame).args(var('ba'))
        expect(self.connection._transport.write).args(var('ba'))

        self.connection._connected = True
        self.connection.send_frame(frame)
        assert_true(isinstance(var('ba').value, bytearray))
        assert_equals(1, self.connection._frames_written)

    def test_send_frame_when_not_connected_and_not_channel_0(self):
        frame = mock()
        frame.channel_id = 42
        stub(frame.write_frame)
        stub(self.connection._transport.write)

        self.connection._connected = False
        self.connection.send_frame(frame)
        assert_equals([frame], self.connection._output_frame_buffer)

    def test_send_frame_when_not_connected_and_channel_0(self):
        frame = mock()
        frame.channel_id = 0
        expect(frame.write_frame).args(var('ba'))
        expect(self.connection._transport.write).args(var('ba'))

        self.connection._connected = False
        self.connection.send_frame(frame)
        assert_true(isinstance(var('ba').value, bytearray))
        assert_equals(1, self.connection._frames_written)

    def test_send_frame_when_debugging(self):
        frame = mock()
        expect(self.connection.logger.debug).args('WRITE: %s', frame)
        expect(frame.write_frame).args(var('ba'))
        expect(self.connection._transport.write).args(var('ba'))

        self.connection._connected = True
        self.connection._debug = 2
        self.connection.send_frame(frame)
        assert_true(isinstance(var('ba').value, bytearray))
        assert_equals(1, self.connection._frames_written)

    def test_send_frame_when_closed(self):
        self.connection._closed = True
        self.connection._close_info['reply_text'] = 'failed'
        assert_raises(connection.ConnectionClosed,
                      self.connection.send_frame, 'frame')

        self.connection._close_info['reply_text'] = ''
        assert_raises(connection.ConnectionClosed,
                      self.connection.send_frame, 'frame')

        self.connection._close_info = None
        assert_raises(connection.ConnectionClosed,
                      self.connection.send_frame, 'frame')

    def test_send_frame_when_frame_overflow(self):
        frame = mock()
        self.connection._frame_max = 100
        expect(frame.write_frame).side_effect(
            lambda buf: buf.extend('a' * 200))
        expect(self.connection.close).args(
            reply_code=501, reply_text=var('reply'), class_id=0, method_id=0, disconnect=True)
        stub(self.connection._transport.write)

        self.connection._connected = True
        with assert_raises(ConnectionClosed):
            self.connection.send_frame(frame)


class ConnectionChannelTest(Chai):

    def setUp(self):
        super(ConnectionChannelTest, self).setUp()
        self.connection = mock()
        self.ch = ConnectionChannel(self.connection, 0, {})

    def test_init(self):
        mock(connection, 'super')
        with expect(connection, 'super').args(is_arg(ConnectionChannel), ConnectionChannel).returns(mock()) as s:
            expect(s.__init__).args('a', 'b')

        c = ConnectionChannel('a', 'b')
        assert_equals(c._method_map,
                      {
                          10: c._recv_start,
                          20: c._recv_secure,
                          30: c._recv_tune,
                          41: c._recv_open_ok,
                          50: c._recv_close,
                          51: c._recv_close_ok,
                      }
                      )
        assert_equal(0, c._last_heartbeat_send)

    def test_dispatch_on_heartbeat_frame(self):
        frame = mock()

        expect(frame.type).returns(HeartbeatFrame.type())
        expect(self.ch.send_heartbeat)

        self.ch.dispatch(frame)

    def test_dispatch_method_frame_class_10(self):
        frame = mock()
        frame.class_id = 10
        frame.method_id = 10
        method = self.ch._method_map[10] = mock()

        expect(frame.type).returns(MethodFrame.type())
        expect(method).args(frame)

        self.ch.dispatch(frame)

    def test_dispatch_runs_callbacks(self):
        frame = mock()
        frame.class_id = 10
        frame.method_id = 10
        method = self.ch._method_map[10] = mock()
        cb = mock()

        expect(frame.type).returns(MethodFrame.type())
        expect(self.ch.clear_synchronous_cb).args(method).returns(cb)
        expect(cb).args(frame)

        self.ch.dispatch(frame)

    def test_dispatch_method_frame_raises_invalidmethod(self):
        frame = mock()
        frame.class_id = 10
        frame.method_id = 500

        expect(frame.type).returns(MethodFrame.type())

        with assert_raises(Channel.InvalidMethod):
            self.ch.dispatch(frame)

    def test_dispatch_method_frame_raises_invalidclass(self):
        frame = mock()
        frame.class_id = 11
        frame.method_id = 10

        expect(frame.type).returns(MethodFrame.type())

        with assert_raises(Channel.InvalidClass):
            self.ch.dispatch(frame)

    def test_dispatch_method_frame_raises_invalidframetype(self):
        frame = mock()

        expect(frame.type).returns(HeaderFrame.type())

        with assert_raises(Frame.InvalidFrameType):
            self.ch.dispatch(frame)

    def test_close(self):
        expect(self.ch._send_close)
        self.ch.close()

    def test_send_heartbeat_when_no_heartbeat(self):
        stub(self.ch.send_frame)
        self.ch.connection._heartbeat = None

        self.ch.send_heartbeat()

    def test_send_heartbeat_when_not_sent_yet(self):
        mock(connection, 'time')
        self.ch.connection._heartbeat = 3
        self.ch._last_heartbeat_send = 0

        expect(connection.time.time).returns(4200.3).times(2)
        expect(self.ch.send_frame).args(HeartbeatFrame)

        self.ch.send_heartbeat()
        assert_equals(4200.3, self.ch._last_heartbeat_send)

    def test_send_heartbeat_when_sent_long_ago(self):
        mock(connection, 'time')
        self.ch.connection._heartbeat = 3
        self.ch._last_heartbeat_send = 4196

        expect(connection.time.time).returns(4200.3).times(2)
        expect(self.ch.send_frame).args(HeartbeatFrame)

        self.ch.send_heartbeat()
        assert_equals(4200.3, self.ch._last_heartbeat_send)

    def test_send_heart_when_sent_recently(self):
        mock(connection, 'time')
        self.ch.connection._heartbeat = 3
        self.ch._last_heartbeat_send = 4199

        expect(connection.time.time).returns(4200.3)
        stub(self.ch.send_frame)

        self.ch.send_heartbeat()
        assert_equals(4199, self.ch._last_heartbeat_send)

    def test_recv_start(self):
        expect(self.ch._send_start_ok)
        self.ch.connection._closed = 'maybe'

        self.ch._recv_start('frame')
        assert_false(self.ch.connection._closed)

    def test_send_start_ok(self):
        self.ch.connection._properties = 'props'
        self.ch.connection._login_method = 'please'
        self.ch.connection._login_response = 'thanks'
        self.ch.connection._locale = 'home'

        with expect(mock(connection, 'Writer')).returns(mock()) as writer:
            expect(writer.write_table).args('props')
            expect(writer.write_shortstr).args('please')
            expect(writer.write_longstr).args('thanks')
            expect(writer.write_shortstr).args('home')

            expect(mock(connection, 'MethodFrame')).args(
                0, 10, 11, writer).returns('frame')
            expect(self.ch.send_frame).args('frame')
        expect(self.ch.add_synchronous_cb).args(self.ch._recv_tune)

        self.ch._send_start_ok()

    def test_recv_tune_when_no_broker_max_and_defined_heartbeat(self):
        self.ch.connection._channel_max = 42
        self.ch.connection._frame_max = 43
        self.ch.connection._heartbeat = 8

        frame = mock()
        expect(frame.args.read_short).returns(0)
        expect(frame.args.read_long).returns(0)

        expect(self.ch._send_tune_ok)
        expect(self.ch._send_open)
        expect(self.ch.send_heartbeat)

        self.ch._recv_tune(frame)
        assert_equals(42, self.ch.connection._channel_max)
        assert_equals(43, self.ch.connection._frame_max)
        assert_equals(8, self.ch.connection._heartbeat)

    def test_recv_tune_when_broker_max_and_undefined_heartbeat(self):
        self.ch.connection._channel_max = 42
        self.ch.connection._frame_max = 43
        self.ch.connection._heartbeat = None

        frame = mock()
        expect(frame.args.read_short).returns(500)
        expect(frame.args.read_long).returns(501)
        expect(frame.args.read_short).returns(7)

        expect(self.ch._send_tune_ok)
        expect(self.ch._send_open)
        expect(self.ch.send_heartbeat)

        self.ch._recv_tune(frame)
        assert_equals(500, self.ch.connection._channel_max)
        assert_equals(501, self.ch.connection._frame_max)
        assert_equals(7, self.ch.connection._heartbeat)

    def test_send_tune_ok_when_heartbeat(self):
        self.ch.connection._channel_max = 42
        self.ch.connection._frame_max = 43
        self.ch.connection._heartbeat = 8

        with expect(mock(connection, 'Writer')).returns(mock()) as writer:
            expect(writer.write_short).args(42)
            expect(writer.write_long).args(43)
            expect(writer.write_short).args(8)

            expect(mock(connection, 'MethodFrame')).args(
                0, 10, 31, writer).returns('frame')
            expect(self.ch.send_frame).args('frame')

        self.ch._send_tune_ok()

    def test_send_tune_ok_when_no_heartbeat(self):
        self.ch.connection._channel_max = 42
        self.ch.connection._frame_max = 43
        self.ch.connection._heartbeat = None

        with expect(mock(connection, 'Writer')).returns(mock()) as writer:
            expect(writer.write_short).args(42)
            expect(writer.write_long).args(43)
            expect(writer.write_short).args(0)

            expect(mock(connection, 'MethodFrame')).args(
                0, 10, 31, writer).returns('frame')
            expect(self.ch.send_frame).args('frame')

        self.ch._send_tune_ok()

    def test_recv_secure(self):
        expect(self.ch._send_open)
        self.ch._recv_secure('frame')

    def test_send_open(self):
        self.connection._vhost = '/foo'

        with expect(mock(connection, 'Writer')).returns(mock()) as writer:
            expect(writer.write_shortstr).args('/foo')
            expect(writer.write_shortstr).args('')
            expect(writer.write_bit).args(True)

            expect(mock(connection, 'MethodFrame')).args(
                0, 10, 40, writer).returns('frame')
            expect(self.ch.send_frame).args('frame')
        expect(self.ch.add_synchronous_cb).args(self.ch._recv_open_ok)

        self.ch._send_open()

    def test_recv_open_ok(self):
        self.ch.connection._connected = False
        expect(self.ch.connection._flush_buffered_frames)
        expect(self.ch.connection._callback_open)

        self.ch._recv_open_ok('frame')
        assert_true(self.ch.connection._connected)

    def test_send_close(self):
        self.ch.connection._close_info = {
            'reply_code': 42,
            'reply_text': 'wrong answer' * 60,
            'class_id': 4,
            'method_id': 20,
        }

        with expect(mock(connection, 'Writer')).returns(mock()) as writer:
            expect(writer.write_short).args(42)
            expect(writer.write_shortstr).args(('wrong answer' * 60)[:255])
            expect(writer.write_short).args(4)
            expect(writer.write_short).args(20)

            expect(mock(connection, 'MethodFrame')).args(
                0, 10, 50, writer).returns('frame')
            expect(self.ch.send_frame).args('frame')
        expect(self.ch.add_synchronous_cb).args(self.ch._recv_close_ok)

        self.ch._send_close()

    def test_recv_close(self):
        self.ch.connection._closed = False

        frame = mock()
        expect(frame.args.read_short).returns(42)
        expect(frame.args.read_shortstr).returns('wrong answer')
        expect(frame.args.read_short).returns(4)
        expect(frame.args.read_short).returns(20)

        expect(self.ch._send_close_ok)
        expect(self.ch.connection.disconnect)
        expect(self.ch.connection._callback_close)

        self.ch._recv_close(frame)
        assert_equals(self.ch.connection._close_info, {
            'reply_code': 42,
            'reply_text': 'wrong answer',
            'class_id': 4,
            'method_id': 20,
        })
        assert_true(self.ch.connection._closed)

    def test_send_close_ok(self):
        expect(mock(connection, 'MethodFrame')).args(
            0, 10, 51).returns('frame')
        expect(self.ch.send_frame).args('frame')
        self.ch._send_close_ok()

    def test_recv_close_ok(self):
        self.ch.connection._closed = False
        expect(self.ch.connection.disconnect)
        expect(self.ch.connection._callback_close)

        self.ch._recv_close_ok('frame')
        assert_true(self.ch.connection._closed)

########NEW FILE########
__FILENAME__ = content_frame_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai

from haigha.frames import content_frame
from haigha.frames.content_frame import ContentFrame
from haigha.frames.frame import Frame


class ContentFrameTest(Chai):

    def test_type(self):
        assert_equals(3, ContentFrame.type())

    def test_payload(self):
        klass = ContentFrame(42, 'payload')
        assert_equals('payload', klass.payload)

    def test_parse(self):
        frame = ContentFrame.parse(42, 'payload')
        assert_true(isinstance(frame, ContentFrame))
        assert_equals(42, frame.channel_id)
        assert_equals('payload', frame.payload)

    def test_create_frames(self):
        itr = ContentFrame.create_frames(42, 'helloworld', 13)

        frame = itr.next()
        assert_true(isinstance(frame, ContentFrame))
        assert_equals(42, frame.channel_id)
        assert_equals('hello', frame.payload)

        frame = itr.next()
        assert_true(isinstance(frame, ContentFrame))
        assert_equals(42, frame.channel_id)
        assert_equals('world', frame.payload)

        assert_raises(StopIteration, itr.next)

    def test_init(self):
        expect(Frame.__init__).args(is_a(ContentFrame), 42)
        frame = ContentFrame(42, 'payload')
        assert_equals('payload', frame._payload)

    def test_str(self):
        # Test both branches but don't assert the actual content because its
        # not worth it
        frame = ContentFrame(42, 'payload')
        str(frame)

        frame = ContentFrame(42, 8675309)
        str(frame)

    def test_write_frame(self):
        w = mock()
        expect(mock(content_frame, 'Writer')).args('buffer').returns(w)
        expect(w.write_octet).args(3).returns(w)
        expect(w.write_short).args(42).returns(w)
        expect(w.write_long).args(5).returns(w)
        expect(w.write).args('hello').returns(w)
        expect(w.write_octet).args(0xce)

        frame = ContentFrame(42, 'hello')
        frame.write_frame('buffer')

########NEW FILE########
__FILENAME__ = frame_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai
import struct
from collections import deque

from haigha.frames import frame
from haigha.frames.frame import Frame
from haigha.reader import Reader


class FrameTest(Chai):

    def test_register(self):
        class DummyFrame(Frame):

            @classmethod
            def type(self):
                return 42

        assertEquals(None, Frame._frame_type_map.get(42))
        DummyFrame.register()
        assertEquals(DummyFrame, Frame._frame_type_map[42])

    def test_type_raises_not_implemented(self):
        assertRaises(NotImplementedError, Frame.type)

    def test_read_frames_reads_until_buffer_underflow(self):
        reader = mock()

        expect(reader.tell).returns(0)
        expect(Frame._read_frame).args(reader).returns('frame1')

        expect(reader.tell).returns(2)
        expect(Frame._read_frame).args(reader).returns('frame2')

        expect(reader.tell).returns(3)
        expect(Frame._read_frame).args(reader).raises(Reader.BufferUnderflow)

        expect(reader.seek).args(3)

        assertEquals(deque(['frame1', 'frame2']), Frame.read_frames(reader))

    def test_read_frames_handles_reader_errors(self):
        reader = mock()
        self.mock(Frame, '_read_frame')

        expect(reader.tell).returns(0)
        expect(Frame._read_frame).args(
            reader).raises(Reader.ReaderError("bad!"))

        assertRaises(Frame.FormatError, Frame.read_frames, reader)

    def test_read_frames_handles_struct_errors(self):
        reader = mock()
        self.mock(Frame, '_read_frame')

        expect(reader.tell).returns(0)
        expect(Frame._read_frame).args(reader).raises(struct.error("bad!"))

        self.assertRaises(Frame.FormatError, Frame.read_frames, reader)

    def test_read_frame_on_full_frame(self):
        class FrameReader(Frame):

            @classmethod
            def type(self):
                return 45

            @classmethod
            def parse(self, channel_id, payload):
                return 'no_frame'
        FrameReader.register()

        self.mock(frame, 'Reader')
        reader = self.mock()
        payload = self.mock()

        expect(reader.read_octet).returns(45)  # frame type
        expect(reader.read_short).returns(32)  # channel id
        expect(reader.read_long).returns(42)  # size

        expect(reader.tell).returns(5)
        expect(frame.Reader).args(reader, 5, 42).returns(payload)
        expect(reader.seek).args(42, 1)

        expect(reader.read_octet).returns(0xce)
        expect(FrameReader.parse).args(32, payload).returns('a_frame')

        assertEquals('a_frame', Frame._read_frame(reader))

    def test_read_frame_raises_bufferunderflow_when_incomplete_payload(self):
        self.mock(frame, 'Reader')
        reader = self.mock()

        expect(reader.read_octet).returns(45)  # frame type
        expect(reader.read_short).returns(32)  # channel id
        expect(reader.read_long).returns(42)  # size

        expect(reader.tell).returns(5)
        expect(frame.Reader).args(reader, 5, 42).returns('payload')
        expect(reader.seek).args(42, 1)

        expect(reader.read_octet).raises(Reader.BufferUnderflow)
        assert_raises(Reader.BufferUnderflow, Frame._read_frame, reader)

    def test_read_frame_raises_formaterror_if_bad_footer(self):
        self.mock(frame, 'Reader')
        reader = self.mock()

        expect(reader.read_octet).returns(45)  # frame type
        expect(reader.read_short).returns(32)  # channel id
        expect(reader.read_long).returns(42)  # size

        expect(reader.tell).returns(5)
        expect(frame.Reader).args(reader, 5, 42).returns('payload')
        expect(reader.seek).args(42, 1)
        expect(reader.read_octet).returns(0xff)

        assert_raises(Frame.FormatError, Frame._read_frame, reader)

    def test_read_frame_raises_invalidframetype_for_unregistered_frame_type(self):
        self.mock(frame, 'Reader')
        reader = self.mock()
        payload = self.mock()

        expect(reader.read_octet).returns(54)  # frame type
        expect(reader.read_short).returns(32)  # channel id
        expect(reader.read_long).returns(42)  # size

        expect(reader.tell).returns(5)
        expect(frame.Reader).args(reader, 5, 42).returns(payload)
        expect(reader.seek).args(42, 1)

        expect(reader.read_octet).returns(0xce)

        assertRaises(Frame.InvalidFrameType, Frame._read_frame, reader)

    def test_parse_raises_not_implemented(self):
        assertRaises(NotImplementedError, Frame.parse, 'channel_id', 'payload')

    def test_properties(self):
        frame = Frame('channel_id')
        assert_equals('channel_id', frame.channel_id)

    def test_str(self):
        frame = Frame(42)
        assert_equals('Frame[channel: 42]', str(frame))

    def test_repr(self):
        expect(Frame.__str__).returns('foo')
        frame = Frame(42)
        assert_equals('foo', repr(frame))

    def test_write_frame(self):
        frame = Frame(42)
        assert_raises(NotImplementedError, frame.write_frame, 'stream')

########NEW FILE########
__FILENAME__ = header_frame_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai
import struct
import time
from datetime import datetime

from haigha.frames import header_frame
from haigha.frames.header_frame import HeaderFrame
from haigha.reader import Reader
from haigha.writer import Writer


class HeaderFrameTest(Chai):

    def test_type(self):
        assert_equals(2, HeaderFrame.type())

    def test_properties(self):
        frame = HeaderFrame(42, 'class_id', 'weight', 'size', 'props')
        assert_equals(42, frame.channel_id)
        assert_equals('class_id', frame.class_id)
        assert_equals('weight', frame.weight)
        assert_equals('size', frame.size)
        assert_equals('props', frame.properties)

    def test_str(self):
        # Don't bother checking the copy
        frame = HeaderFrame(42, 5, 6, 7, 'props')
        assert_equals('HeaderFrame[channel: 42, class_id: 5, weight: 6, size: 7, properties: props]',
                      str(frame))

    def test_parse_fast_for_standard_properties(self):
        bit_writer = Writer()
        val_writer = Writer()

        # strip ms because amqp doesn't include it
        now = datetime.utcfromtimestamp(
            long(time.mktime(datetime.now().timetuple())))

        bit_field = 0
        for pname, ptype, reader, writer, mask in HeaderFrame.PROPERTIES:
            bit_field = (bit_field << 1) | 1

            if ptype == 'shortstr':
                val_writer.write_shortstr(pname)
            elif ptype == 'octet':
                val_writer.write_octet(42)
            elif ptype == 'timestamp':
                val_writer.write_timestamp(now)
            elif ptype == 'table':
                val_writer.write_table({'foo': 'bar'})

        bit_field <<= (16 - len(HeaderFrame.PROPERTIES))
        bit_writer.write_short(bit_field)

        header_writer = Writer()
        header_writer.write_short(5)
        header_writer.write_short(6)
        header_writer.write_longlong(7)
        payload = header_writer.buffer()
        payload += bit_writer.buffer()
        payload += val_writer.buffer()

        reader = Reader(payload)
        frame = HeaderFrame.parse(4, reader)

        for pname, ptype, reader, writer, mask in HeaderFrame.PROPERTIES:
            if ptype == 'shortstr':
                self.assertEquals(pname, frame.properties[pname])
            elif ptype == 'octet':
                self.assertEquals(42, frame.properties[pname])
            elif ptype == 'timestamp':
                self.assertEquals(now, frame.properties[pname])
            elif ptype == 'table':
                self.assertEquals({'foo': 'bar'}, frame.properties[pname])

        assert_equals(4, frame.channel_id)
        assert_equals(5, frame._class_id)
        assert_equals(6, frame._weight)
        assert_equals(7, frame._size)

    def test_parse_slow_for_standard_properties(self):
        HeaderFrame.DEFAULT_PROPERTIES = False
        bit_writer = Writer()
        val_writer = Writer()

        # strip ms because amqp doesn't include it
        now = datetime.utcfromtimestamp(
            long(time.mktime(datetime.now().timetuple())))

        bit_field = 0
        for pname, ptype, reader, writer, mask in HeaderFrame.PROPERTIES:
            bit_field = (bit_field << 1) | 1

            if ptype == 'shortstr':
                val_writer.write_shortstr(pname)
            elif ptype == 'octet':
                val_writer.write_octet(42)
            elif ptype == 'timestamp':
                val_writer.write_timestamp(now)
            elif ptype == 'table':
                val_writer.write_table({'foo': 'bar'})

        bit_field <<= (16 - len(HeaderFrame.PROPERTIES))
        bit_writer.write_short(bit_field)

        header_writer = Writer()
        header_writer.write_short(5)
        header_writer.write_short(6)
        header_writer.write_longlong(7)
        payload = header_writer.buffer()
        payload += bit_writer.buffer()
        payload += val_writer.buffer()

        reader = Reader(payload)
        frame = HeaderFrame.parse(4, reader)
        HeaderFrame.DEFAULT_PROPERTIES = True

        for pname, ptype, reader, writer, mask in HeaderFrame.PROPERTIES:
            if ptype == 'shortstr':
                self.assertEquals(pname, frame.properties[pname])
            elif ptype == 'octet':
                self.assertEquals(42, frame.properties[pname])
            elif ptype == 'timestamp':
                self.assertEquals(now, frame.properties[pname])
            elif ptype == 'table':
                self.assertEquals({'foo': 'bar'}, frame.properties[pname])

        assert_equals(4, frame.channel_id)
        assert_equals(5, frame._class_id)
        assert_equals(6, frame._weight)
        assert_equals(7, frame._size)

    def test_write_frame_fast_for_standard_properties(self):
        bit_field = 0
        properties = {}
        now = datetime.utcfromtimestamp(
            long(time.mktime(datetime.now().timetuple())))
        for pname, ptype, reader, writer, mask in HeaderFrame.PROPERTIES:
            bit_field |= mask

            if ptype == 'shortstr':
                properties[pname] = pname
            elif ptype == 'octet':
                properties[pname] = 42
            elif ptype == 'timestamp':
                properties[pname] = now
            elif ptype == 'table':
                properties[pname] = {'foo': 'bar'}

        frame = HeaderFrame(42, 5, 6, 7, properties)
        buf = bytearray()
        frame.write_frame(buf)

        reader = Reader(buf)
        assert_equals(2, reader.read_octet())
        assert_equals(42, reader.read_short())
        size = reader.read_long()
        start_pos = reader.tell()
        assert_equals(5, reader.read_short())
        assert_equals(6, reader.read_short())
        assert_equals(7, reader.read_longlong())
        assert_equals(0b1111111111111100, reader.read_short())

        for pname, ptype, rfunc, wfunc, mask in HeaderFrame.PROPERTIES:
            if ptype == 'shortstr':
                assertEquals(pname, reader.read_shortstr())
            elif ptype == 'octet':
                assertEquals(42, reader.read_octet())
            elif ptype == 'timestamp':
                assertEquals(now, reader.read_timestamp())
            elif ptype == 'table':
                assertEquals({'foo': 'bar'}, reader.read_table())

        end_pos = reader.tell()
        assert_equals(size, end_pos - start_pos)
        assert_equals(0xce, reader.read_octet())

    def test_write_frame_slow_for_standard_properties(self):
        HeaderFrame.DEFAULT_PROPERTIES = False
        bit_field = 0
        properties = {}
        now = datetime.utcfromtimestamp(
            long(time.mktime(datetime.now().timetuple())))
        for pname, ptype, reader, writer, mask in HeaderFrame.PROPERTIES:
            bit_field |= mask

            if ptype == 'shortstr':
                properties[pname] = pname
            elif ptype == 'octet':
                properties[pname] = 42
            elif ptype == 'timestamp':
                properties[pname] = now
            elif ptype == 'table':
                properties[pname] = {'foo': 'bar'}

        frame = HeaderFrame(42, 5, 6, 7, properties)
        buf = bytearray()
        frame.write_frame(buf)
        HeaderFrame.DEFAULT_PROPERTIES = True

        reader = Reader(buf)
        assert_equals(2, reader.read_octet())
        assert_equals(42, reader.read_short())
        size = reader.read_long()
        start_pos = reader.tell()
        assert_equals(5, reader.read_short())
        assert_equals(6, reader.read_short())
        assert_equals(7, reader.read_longlong())
        assert_equals(0b1111111111111100, reader.read_short())

        for pname, ptype, rfunc, wfunc, mask in HeaderFrame.PROPERTIES:
            if ptype == 'shortstr':
                assertEquals(pname, reader.read_shortstr())
            elif ptype == 'octet':
                assertEquals(42, reader.read_octet())
            elif ptype == 'timestamp':
                assertEquals(now, reader.read_timestamp())
            elif ptype == 'table':
                assertEquals({'foo': 'bar'}, reader.read_table())

        end_pos = reader.tell()
        assert_equals(size, end_pos - start_pos)
        assert_equals(0xce, reader.read_octet())

########NEW FILE########
__FILENAME__ = heartbeat_frame_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai

from haigha.frames import heartbeat_frame
from haigha.frames.heartbeat_frame import HeartbeatFrame
from haigha.frames.frame import Frame


class HeartbeatFrameTest(Chai):

    def test_type(self):
        assert_equals(8, HeartbeatFrame.type())

    def test_parse(self):
        frame = HeartbeatFrame.parse(42, 'payload')
        assert_true(isinstance(frame, HeartbeatFrame))
        assert_equals(42, frame.channel_id)

    def test_write_frame(self):
        w = mock()
        expect(mock(heartbeat_frame, 'Writer')).args('buffer').returns(w)
        expect(w.write_octet).args(8).returns(w)
        expect(w.write_short).args(42).returns(w)
        expect(w.write_long).args(0).returns(w)
        expect(w.write_octet).args(0xce)

        frame = HeartbeatFrame(42)
        frame.write_frame('buffer')

########NEW FILE########
__FILENAME__ = method_frame_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai
import struct
import time
from datetime import datetime

from haigha.frames import method_frame
from haigha.frames.method_frame import MethodFrame
from haigha.reader import Reader
from haigha.writer import Writer


class MethodFrameTest(Chai):

    def test_type(self):
        assert_equals(1, MethodFrame.type())

    def test_properties(self):
        frame = MethodFrame('channel_id', 'class_id', 'method_id', 'args')
        assert_equals('channel_id', frame.channel_id)
        assert_equals('class_id', frame.class_id)
        assert_equals('method_id', frame.method_id)
        assert_equals('args', frame.args)

    def test_parse(self):
        reader = mock()
        expect(reader.read_short).returns('class_id')
        expect(reader.read_short).returns('method_id')
        frame = MethodFrame.parse(42, reader)

        assert_equals(42, frame.channel_id)
        assert_equals('class_id', frame.class_id)
        assert_equals('method_id', frame.method_id)
        assert_equals(reader, frame.args)

    def test_str(self):
        frame = MethodFrame(42, 5, 6, Reader(bytearray('hello')))
        assert_equals(
            'MethodFrame[channel: 42, class_id: 5, method_id: 6, args: \\x68\\x65\\x6c\\x6c\\x6f]', str(frame))

        frame = MethodFrame(42, 5, 6)
        assert_equals(
            'MethodFrame[channel: 42, class_id: 5, method_id: 6, args: None]', str(frame))

    def test_write_frame(self):
        args = mock()
        expect(args.buffer).returns('hello')

        frame = MethodFrame(42, 5, 6, args)
        buf = bytearray()
        frame.write_frame(buf)

        reader = Reader(buf)
        assert_equals(1, reader.read_octet())
        assert_equals(42, reader.read_short())
        size = reader.read_long()
        start_pos = reader.tell()
        assert_equals(5, reader.read_short())
        assert_equals(6, reader.read_short())
        args_pos = reader.tell()
        assert_equals('hello', reader.read(size - (args_pos - start_pos)))
        assert_equals(0xce, reader.read_octet())

########NEW FILE########
__FILENAME__ = message_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai

from haigha.message import Message


class MessageTest(Chai):

    def test_init_no_args(self):
        m = Message()
        self.assertEquals('', m._body)
        self.assertEquals(None, m._delivery_info)
        self.assertEquals({}, m._properties)

    def test_init_with_args(self):
        m = Message('foo', 'delivery', foo='bar')
        self.assertEquals('foo', m._body)
        self.assertEquals('delivery', m._delivery_info)
        self.assertEquals({'foo': 'bar'}, m._properties)

        m = Message(u'D\xfcsseldorf')
        self.assertEquals('D\xc3\xbcsseldorf', m._body)
        self.assertEquals({'content_encoding': 'utf-8'}, m._properties)

    def test_properties(self):
        m = Message('foo', 'delivery', foo='bar')
        self.assertEquals('foo', m.body)
        self.assertEquals('delivery', m.delivery_info)
        self.assertEquals({'foo': 'bar'}, m.properties)

    def test_len(self):
        m = Message('foobar')
        self.assertEquals(6, len(m))

    def test_nonzero(self):
        m = Message()
        self.assertTrue(m)

    def test_eq(self):
        l = Message()
        r = Message()
        self.assertEquals(l, r)

        l = Message('foo')
        r = Message('foo')
        self.assertEquals(l, r)

        l = Message(foo='bar')
        r = Message(foo='bar')
        self.assertEquals(l, r)

        l = Message('hello', foo='bar')
        r = Message('hello', foo='bar')
        self.assertEquals(l, r)

        l = Message('foo')
        r = Message('bar')
        self.assertNotEquals(l, r)

        l = Message(foo='bar')
        r = Message(foo='brah')
        self.assertNotEquals(l, r)

        l = Message('hello', foo='bar')
        r = Message('goodbye', foo='bar')
        self.assertNotEquals(l, r)

        l = Message('hello', foo='bar')
        r = Message('hello', foo='brah')
        self.assertNotEquals(l, r)

        self.assertNotEquals(Message(), object())

    def test_str(self):
        m = Message('foo', 'delivery', foo='bar')
        str(m)

########NEW FILE########
__FILENAME__ = reader_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai
from datetime import datetime
from io import BytesIO
from decimal import Decimal

from haigha.reader import Reader
import struct
import operator


class ReaderTest(Chai):

    def test_init(self):
        ba = Reader(bytearray('foo'))
        assert_true(isinstance(ba._input, buffer))
        assert_equals('foo', str(ba._input))
        assert_equals(0, ba._start_pos)
        assert_equals(0, ba._pos)
        assert_equals(3, ba._end_pos)

        s = Reader('foo')
        assert_true(isinstance(s._input, buffer))
        assert_equals('foo', str(s._input))

        u = Reader(u'D\xfcsseldorf')
        assert_true(isinstance(u._input, buffer))
        assert_equals('D\xc3\xbcsseldorf', str(u._input))

        b = BytesIO('foo')
        i = Reader(b)
        assert_true(isinstance(i._input, buffer))
        assert_equals('foo', str(i._input))

        src = Reader('foo')
        r = Reader(src)
        assert_true(isinstance(r._input, buffer))
        assert_equals(id(src._input), id(r._input))
        assert_equals(0, r._start_pos)
        assert_equals(3, r._end_pos)

        src = Reader('hello world')
        r = Reader(src, 3, 5)
        assert_true(isinstance(r._input, buffer))
        assert_equals(id(src._input), id(r._input))
        assert_equals(3, r._start_pos)
        assert_equals(8, r._end_pos)
        assert_equals(3, r._pos)

        assert_raises(ValueError, Reader, 1)

    def test_str(self):
        assert_equals('\\x66\\x6f\\x6f', str(Reader('foo')))

    def test_tell(self):
        r = Reader('')
        r._pos = 'foo'
        assert_equals('foo', r.tell())

    def test_seek_whence_zero(self):
        r = Reader('', 3)
        assert_equals(3, r._pos)
        r.seek(5)
        assert_equals(8, r._pos)

    def test_seek_whence_one(self):
        r = Reader('')
        r._pos = 2
        r.seek(5, 1)
        assert_equals(7, r._pos)

    def test_seek_whence_two(self):
        r = Reader('foo bar')
        r.seek(-3, 2)
        assert_equals(3, r._pos)

    def test_check_underflow(self):
        r = Reader('')
        r._pos = 0
        r._end_pos = 5
        r._check_underflow(3)
        assert_raises(Reader.BufferUnderflow, r._check_underflow, 8)

    def test_check_len(self):
        r = Reader('foo bar')
        self.assert_equals(7, len(r))
        r = Reader('foo bar', 3)
        self.assert_equals(4, len(r))

    def test_buffer(self):
        r = Reader('hello world', 3, 5)
        self.assert_equals(buffer('lo wo'), r.buffer())

    def test_read(self):
        b = Reader('foo')
        assert_equals('foo', b.read(3))

        b = Reader('foo')
        assert_equals('fo', b.read(2))

        b = Reader('foo')
        assert_raises(Reader.BufferUnderflow, b.read, 4)

    def test_read_bit(self):
        b = Reader('\x01')
        assert_true(b.read_bit())

        b = Reader('\x00')
        assert_false(b.read_bit())

        b = Reader('\x02')
        assert_false(b.read_bit())

        b = Reader('')
        assert_raises(Reader.BufferUnderflow, b.read_bit)

    def test_read_bits(self):
        b = Reader('\x01')
        assert_equals([True], b.read_bits(1))

        b = Reader('\x00')
        assert_equals([False], b.read_bits(1))

        b = Reader('\x02')
        assert_equals([False, True], b.read_bits(2))

        b = Reader('\x02')
        assert_equals(
            [False, True, False, False, False, False, False, False], b.read_bits(8))

        b = Reader('\x00')
        assert_raises(ValueError, b.read_bits, 9)
        assert_raises(ValueError, b.read_bits, -1)
        assert_equals([], b.read_bits(0))

        b = Reader('')
        assert_raises(Reader.BufferUnderflow, b.read_bits, 2)

    def test_read_octet(self):
        b = Reader('\xff')
        assert_equals(255, b.read_octet())
        assert_raises(Reader.BufferUnderflow, b.read_octet)

    def test_read_short(self):
        b = Reader('\xff\x00')
        assert_equals(65280, b.read_short())
        assert_raises(Reader.BufferUnderflow, b.read_short)

    def test_read_long(self):
        b = Reader('\xff\x00\xff\x00')
        assert_equals(4278255360, b.read_long())
        assert_raises(Reader.BufferUnderflow, b.read_long)

    def test_read_longlong(self):
        b = Reader('\xff\x00\xff\x00\xff\x00\xff\x00')
        assert_equals(18374966859414961920L, b.read_longlong())
        assert_raises(Reader.BufferUnderflow, b.read_longlong)

    def test_read_shortstr(self):
        b = Reader('\x05hello')
        assert_equals('hello', b.read_shortstr())
        assert_raises(Reader.BufferUnderflow, b.read_shortstr)

        b = Reader('\x0bD\xc3\xbcsseldorf')
        assert_equals('D\xc3\xbcsseldorf', b.read_shortstr())

        b = Reader('\x05hell')
        assert_raises(Reader.BufferUnderflow, b.read_shortstr)

    def test_read_longstr(self):
        b = Reader('\x00\x00\x01\x00' + ('a' * 256))
        assert_equals('a' * 256, b.read_longstr())

        b = Reader('\x00\x00\x01\x00' + ('a' * 255))
        assert_raises(Reader.BufferUnderflow, b.read_longstr)

    def test_read_timestamp(self):
        b = Reader('\x00\x00\x00\x00\x4d\x34\xc4\x71')
        d = datetime(2011, 1, 17, 22, 36, 33)

        assert_equals(d, b.read_timestamp())

    def test_read_table(self):
        # mock everything to keep this simple
        r = Reader('')
        expect(r.read_long).returns(42)
        expect(r._check_underflow).args(42)
        expect(r._field_shortstr).returns('a')
        expect(r._read_field).returns(3.14).side_effect(
            lambda: setattr(r, '_pos', 20))
        expect(r._field_shortstr).returns('b')
        expect(r._read_field).returns('pi').side_effect(
            lambda: setattr(r, '_pos', 42))

        assert_equals({'a': 3.14, 'b': 'pi'}, r.read_table())

    def test_read_field(self):
        r = Reader('Z')
        r.field_type_map['Z'] = mock()
        expect(r.field_type_map['Z']).args(r)

        r._read_field()

    def test_read_field_raises_fielderror_on_unknown_type(self):
        r = Reader('X')
        assert_raises(Reader.FieldError, r._read_field)

    def test_field_bool(self):
        r = Reader('\x00\x01\xf5')
        assert_false(r._field_bool())
        assert_true(r._field_bool())
        assert_true(r._field_bool())
        assert_equals(3, r._pos)

    def test_field_short_short_int(self):
        r = Reader(struct.pack('bb', 5, -5))
        assert_equals(5, r._field_short_short_int())
        assert_equals(-5, r._field_short_short_int())
        assert_equals(2, r._pos)

    def test_field_short_short_uint(self):
        r = Reader(struct.pack('BB', 5, 255))
        assert_equals(5, r._field_short_short_uint())
        assert_equals(255, r._field_short_short_uint())
        assert_equals(2, r._pos)

    def test_field_short_int(self):
        r = Reader(struct.pack('>hh', 256, -256))
        assert_equals(256, r._field_short_int())
        assert_equals(-256, r._field_short_int())
        assert_equals(4, r._pos)

    def test_field_short_uint(self):
        r = Reader(struct.pack('>HH', 256, 512))
        assert_equals(256, r._field_short_uint())
        assert_equals(512, r._field_short_uint())
        assert_equals(4, r._pos)

    def test_field_long_int(self):
        r = Reader(struct.pack('>ii', 2 ** 16, -2 ** 16))
        assert_equals(2 ** 16, r._field_long_int())
        assert_equals(-2 ** 16, r._field_long_int())
        assert_equals(8, r._pos)

    def test_field_long_uint(self):
        r = Reader(struct.pack('>I', 2 ** 32 - 1))
        assert_equals(2 ** 32 - 1, r._field_long_uint())
        assert_equals(4, r._pos)

    def test_field_long_long_int(self):
        r = Reader(struct.pack('>qq', 2 ** 32, -2 ** 32))
        assert_equals(2 ** 32, r._field_long_long_int())
        assert_equals(-2 ** 32, r._field_long_long_int())
        assert_equals(16, r._pos)

    def test_field_long_long_uint(self):
        r = Reader(struct.pack('>Q', 2 ** 64 - 1))
        assert_equals(2 ** 64 - 1, r._field_long_long_uint())
        assert_equals(8, r._pos)

    def test_field_float(self):
        r = Reader(struct.pack('>f', 3.1421))
        assert_almost_equals(3.1421, r._field_float(), 4)
        assert_equals(4, r._pos)

    def test_field_double(self):
        r = Reader(struct.pack('>d', 8675309.1138))
        assert_almost_equals(8675309.1138, r._field_double(), 4)
        assert_equals(8, r._pos)

    def test_field_decimal(self):
        r = Reader(struct.pack('>Bi', 2, 5))
        assert_equals(Decimal('0.05'), r._field_decimal())
        assert_equals(5, r._pos)

        r = Reader(struct.pack('>Bi', 2, -5))
        assert_equals(Decimal('-0.05'), r._field_decimal())
        assert_equals(5, r._pos)

    def test_field_shortstr(self):
        r = Reader('\x05hello')
        assert_equals('hello', r._field_shortstr())
        assert_equals(6, r._pos)

    def test_field_longstr(self):
        r = Reader('\x00\x00\x01\x00' + ('a' * 256))
        assert_equals('a' * 256, r._field_longstr())
        assert_equals(260, r._pos)

    def test_field_array(self):
        # easier to mock the behavior here
        r = Reader('')
        expect(r.read_long).returns(42)
        expect(r._read_field).returns(3.14).side_effect(
            lambda: setattr(r, '_pos', 20))
        expect(r._read_field).returns('pi').side_effect(
            lambda: setattr(r, '_pos', 42))

        assert_equals([3.14, 'pi'], r._field_array())

    def test_field_timestamp(self):
        b = Reader('\x00\x00\x00\x00\x4d\x34\xc4\x71')
        d = datetime(2011, 1, 17, 22, 36, 33)

        assert_equals(d, b._field_timestamp())

    def test_field_bytearray(self):
        b = Reader('\x00\x00\x00\x03\x04\x05\x06')
        assert_equals(bytearray('\x04\x05\x06'), b._field_bytearray())

    def test_field_none(self):
        b = Reader('')
        assert_equals(None, b._field_none())

    def test_field_type_map_rabbit_errata(self):
        # http://dev.rabbitmq.com/wiki/Amqp091Errata#section_3
        assert_equals(
            {
                't': Reader._field_bool.im_func,
                'b': Reader._field_short_short_int.im_func,
                's': Reader._field_short_int.im_func,
                'I': Reader._field_long_int.im_func,
                'l': Reader._field_long_long_int.im_func,
                'f': Reader._field_float.im_func,
                'd': Reader._field_double.im_func,
                'D': Reader._field_decimal.im_func,
                'S': Reader._field_longstr.im_func,
                'A': Reader._field_array.im_func,
                'T': Reader._field_timestamp.im_func,
                'F': Reader.read_table.im_func,
                'V': Reader._field_none.im_func,
                'x': Reader._field_bytearray.im_func,
            }, Reader.field_type_map)

    # def test_field_type_map_091_spec(self):
    #  assert_equals(
    #    {
    #      't' : Reader._field_bool.im_func,
    #      'b' : Reader._field_short_short_int.im_func,
    #      'B' : Reader._field_short_short_uint.im_func,
    #      'U' : Reader._field_short_int.im_func,
    #      'u' : Reader._field_short_uint.im_func,
    #      'I' : Reader._field_long_int.im_func,
    #      'i' : Reader._field_long_uint.im_func,
    #      'L' : Reader._field_long_long_int.im_func,
    #      'l' : Reader._field_long_long_uint.im_func,
    #      'f' : Reader._field_float.im_func,
    #      'd' : Reader._field_double.im_func,
    #      'D' : Reader._field_decimal.im_func,
    #      's' : Reader._field_shortstr.im_func,
    #      'S' : Reader._field_longstr.im_func,
    #      'A' : Reader._field_array.im_func,
    #      'T' : Reader._field_timestamp.im_func,
    #      'F' : Reader.read_table.im_func,
    #    }, Reader.field_type_map )

########NEW FILE########
__FILENAME__ = event_transport_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai

from haigha.transports import event_transport
from haigha.transports.event_transport import *


class EventTransportTest(Chai):

    def setUp(self):
        super(EventTransportTest, self).setUp()

        self.connection = mock()
        self.transport = EventTransport(self.connection)
        self.transport._host = 'server'

    def test_sock_close_cb(self):
        expect(self.connection.transport_closed).args(
            msg='socket to server closed unexpectedly')
        self.transport._sock_close_cb('sock')

    def test_sock_error_cb(self):
        expect(self.connection.transport_closed).args(
            msg='error on connection to server: amsg')
        self.transport._sock_error_cb('sock', 'amsg')

    def test_sock_read_cb(self):
        expect(self.connection.read_frames)
        self.transport._sock_read_cb('sock')

    def test_connect(self):
        sock = mock()
        mock(event_transport, 'EventSocket')
        self.connection._connect_timeout = 4.12
        self.connection._sock_opts = {
            ('family', 'tcp'): 34,
            ('range', 'ipv6'): 'hex'
        }

        expect(event_transport.EventSocket).args(
            read_cb=self.transport._sock_read_cb,
            close_cb=self.transport._sock_close_cb,
            error_cb=self.transport._sock_error_cb,
            debug=self.connection.debug,
            logger=self.connection.logger,
        ).returns(sock)
        expect(sock.setsockopt).args('family', 'tcp', 34).any_order()
        expect(sock.setsockopt).args('range', 'ipv6', 'hex').any_order()
        expect(sock.setblocking).args(False)
        expect(sock.connect).args(('host', 5309), timeout=4.12)

        self.transport.connect(('host', 5309))

    def test_read(self):
        self.transport._heartbeat_timeout = None
        self.transport._sock = mock()
        expect(self.transport._sock.read).returns('buffereddata')
        assert_equals('buffereddata', self.transport.read())

    def test_read_with_timeout_and_no_current_one(self):
        self.transport._heartbeat_timeout = None
        self.transport._sock = mock()
        mock(event_transport, 'event')
        expect(event_transport.event.timeout).args(
            'timeout', self.transport._sock_read_cb, self.transport._sock).returns(
            'timer')

        expect(self.transport._sock.read).returns('buffereddata')
        assert_equals('buffereddata', self.transport.read('timeout'))
        assert_equals('timer', self.transport._heartbeat_timeout)

    def test_read_with_timeout_and_current_one(self):
        self.transport._heartbeat_timeout = mock()
        self.transport._sock = mock()
        mock(event_transport, 'event')
        expect(self.transport._heartbeat_timeout.delete)
        expect(event_transport.event.timeout).args(
            'timeout', self.transport._sock_read_cb, self.transport._sock).returns(
            'timer')

        expect(self.transport._sock.read).returns('buffereddata')
        assert_equals('buffereddata', self.transport.read('timeout'))
        assert_equals('timer', self.transport._heartbeat_timeout)

    def test_read_without_timeout_but_current_one(self):
        self.transport._heartbeat_timeout = mock()
        self.transport._sock = mock()
        mock(event_transport, 'event')
        expect(self.transport._heartbeat_timeout.delete)

        expect(self.transport._sock.read).returns('buffereddata')
        assert_equals('buffereddata', self.transport.read())
        assert_equals(None, self.transport._heartbeat_timeout)

    def test_read_when_no_sock(self):
        self.transport.read()

    def test_buffer(self):
        self.transport._sock = mock()
        expect(self.transport._sock.buffer).args('somedata')
        self.transport.buffer('somedata')

    def test_buffer_when_no_sock(self):
        self.transport.buffer('somedata')

    def test_write(self):
        self.transport._sock = mock()
        expect(self.transport._sock.write).args('somedata')
        self.transport.write('somedata')

    def test_write_when_no_sock(self):
        self.transport.write('somedata')

    def test_disconnect(self):
        self.transport._sock = mock()
        self.transport._sock.close_cb = 'cb'
        expect(self.transport._sock.close)
        self.transport.disconnect()
        assert_equals(None, self.transport._sock.close_cb)

    def test_disconnect_when_no_sock(self):
        self.transport.disconnect()

########NEW FILE########
__FILENAME__ = gevent_transport_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai
import errno
import gevent
from gevent.coros import Semaphore
from gevent import socket
from gevent.pool import Pool

from haigha.transports import gevent_transport
from haigha.transports.gevent_transport import *


class GeventTransportTest(Chai):

    def setUp(self):
        super(GeventTransportTest, self).setUp()

        self.connection = mock()
        self.transport = GeventTransport(self.connection)
        self.transport._host = 'server:1234'

    def test_init(self):
        assert_equals(bytearray(), self.transport._buffer)
        assert_true(isinstance(self.transport._read_lock, Semaphore))
        assert_true(isinstance(self.transport._write_lock, Semaphore))

    def test_connect(self):
        with expect(mock(gevent_transport, 'super')).args(is_arg(GeventTransport), GeventTransport).returns(mock()) as parent:
            expect(parent.connect).args(
                ('host', 'port'), klass=is_arg(socket.socket)).returns('somedata')

        self.transport.connect(('host', 'port'))

    def test_read(self):
        #self.transport._read_lock = mock()
        #expect( self.transport._read_lock.locked ).returns( False )
        expect(self.transport._read_lock.acquire)
        with expect(mock(gevent_transport, 'super')).args(is_arg(GeventTransport), GeventTransport).returns(mock()) as parent:
            expect(parent.read).args(timeout=None).returns('somedata')
        expect(self.transport._read_lock.release)
        expect(self.transport._read_wait.set)
        expect(self.transport._read_wait.clear)

        assert_equals('somedata', self.transport.read())

    def test_read_when_already_locked(self):
        expect(self.transport._read_lock.locked).returns(True)
        stub(self.transport._read_lock.acquire)
        stub(mock(gevent_transport, 'super'))
        stub(self.transport._read_lock.release)
        expect(self.transport._read_wait.wait)

        assert_equals(None, self.transport.read())

    def test_read_when_raises_exception(self):
        #self.transport._read_lock = mock()
        expect(self.transport._read_lock.acquire)
        with expect(mock(gevent_transport, 'super')).args(is_arg(GeventTransport), GeventTransport).returns(mock()) as parent:
            expect(parent.read).args(timeout='5').raises(Exception('fail'))
        expect(self.transport._read_lock.release)

        assert_raises(Exception, self.transport.read, timeout='5')

    def test_buffer(self):
        #self.transport._read_lock = mock()
        expect(self.transport._read_lock.acquire)
        with expect(mock(gevent_transport, 'super')).args(is_arg(GeventTransport), GeventTransport).returns(mock()) as parent:
            expect(parent.buffer).args('datas')
        expect(self.transport._read_lock.release)

        self.transport.buffer('datas')

    def test_buffer_when_raises_exception(self):
        #self.transport._read_lock = mock()
        expect(self.transport._read_lock.acquire)
        with expect(mock(gevent_transport, 'super')).args(is_arg(GeventTransport), GeventTransport).returns(mock()) as parent:
            expect(parent.buffer).args('datas').raises(Exception('fail'))
        expect(self.transport._read_lock.release)

        assert_raises(Exception, self.transport.buffer, 'datas')

    def test_write(self):
        #self.transport._write_lock = mock()
        expect(self.transport._write_lock.acquire)
        with expect(mock(gevent_transport, 'super')).args(is_arg(GeventTransport), GeventTransport).returns(mock()) as parent:
            expect(parent.write).args('datas')
        expect(self.transport._write_lock.release)

        self.transport.write('datas')

    def test_write_when_raises_an_exception(self):
        #self.transport._write_lock = mock()
        expect(self.transport._write_lock.acquire)
        with expect(mock(gevent_transport, 'super')).args(is_arg(GeventTransport), GeventTransport).returns(mock()) as parent:
            expect(parent.write).args('datas').raises(Exception('fail'))
        expect(self.transport._write_lock.release)

        assert_raises(Exception, self.transport.write, 'datas')


class GeventPoolTransportTest(Chai):

    def setUp(self):
        super(GeventPoolTransportTest, self).setUp()

        self.connection = mock()
        self.transport = GeventPoolTransport(self.connection)
        self.transport._host = 'server:1234'

    def test_init(self):
        assert_equals(bytearray(), self.transport._buffer)
        assert_true(isinstance(self.transport._read_lock, Semaphore))
        assert_true(isinstance(self.transport.pool, Pool))

        trans = GeventPoolTransport(self.connection, pool='inground')
        assert_equals('inground', trans.pool)

    def test_process_channels(self):
        chs = [mock(), mock()]
        self.transport._pool = mock()

        expect(self.transport._pool.spawn).args(chs[0].process_frames)
        expect(self.transport._pool.spawn).args(chs[1].process_frames)

        self.transport.process_channels(chs)

########NEW FILE########
__FILENAME__ = socket_transport_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai
import errno
import socket

from haigha.transports import socket_transport
from haigha.transports.socket_transport import *


class SocketTransportTest(Chai):

    def setUp(self):
        super(SocketTransportTest, self).setUp()

        self.connection = mock()
        self.transport = SocketTransport(self.connection)
        self.transport._host = 'server:1234'

    def test_init(self):
        assert_equals(bytearray(), self.transport._buffer)
        assert_true(self.transport._synchronous)

    def test_connect_with_no_klass_arg(self):
        klass = mock()
        sock = mock()
        orig_defaults = self.transport.connect.im_func.func_defaults
        self.transport.connect.im_func.func_defaults = (klass,)
        expect(klass).returns(sock)
        self.connection._connect_timeout = 4.12
        self.connection._sock_opts = {
            ('family', 'tcp'): 34,
            ('range', 'ipv6'): 'hex'
        }

        expect(sock.setblocking).args(True)
        expect(sock.settimeout).args(4.12)
        expect(sock.setsockopt).any_order().args(
            'family', 'tcp', 34).any_order()
        expect(sock.setsockopt).any_order().args(
            'range', 'ipv6', 'hex').any_order()
        expect(sock.connect).args(('host', 5309))
        expect(sock.settimeout).args(None)

        self.transport.connect(('host', 5309))
        self.transport.connect.im_func.func_defaults = orig_defaults

    def test_connect_with_klass_arg(self):
        klass = mock()
        sock = mock()
        expect(klass).returns(sock)
        self.connection._connect_timeout = 4.12
        self.connection._sock_opts = {
            ('family', 'tcp'): 34,
            ('range', 'ipv6'): 'hex'
        }

        expect(sock.setblocking).args(True)
        expect(sock.settimeout).args(4.12)
        expect(sock.setsockopt).any_order().args(
            'family', 'tcp', 34).any_order()
        expect(sock.setsockopt).any_order().args(
            'range', 'ipv6', 'hex').any_order()
        expect(sock.connect).args(('host', 5309))
        expect(sock.settimeout).args(None)

        self.transport.connect(('host', 5309), klass=klass)

    def test_read(self):
        self.transport._sock = mock()
        self.transport.connection.debug = False

        expect(self.transport._sock.settimeout).args(None)
        expect(self.transport._sock.getsockopt).args(
            socket.SOL_SOCKET, socket.SO_RCVBUF).returns(4095)
        expect(self.transport._sock.recv).args(4095).returns('buffereddata')

        assert_equals('buffereddata', self.transport.read())

    def test_read_when_data_buffered(self):
        self.transport._sock = mock()
        self.transport.connection.debug = False
        self.transport._buffer = bytearray('buffered')

        expect(self.transport._sock.settimeout).args(3)
        expect(self.transport._sock.getsockopt).any_args().returns(4095)
        expect(self.transport._sock.recv).args(4095).returns('data')

        assert_equals('buffereddata', self.transport.read(3))
        assert_equals(bytearray(), self.transport._buffer)

    def test_read_when_debugging(self):
        self.transport._sock = mock()
        self.transport.connection.debug = 2

        expect(self.transport._sock.settimeout).args(None)
        expect(self.transport._sock.getsockopt).any_args().returns(4095)
        expect(self.transport._sock.recv).args(4095).returns('buffereddata')
        expect(self.transport.connection.logger.debug).args(
            'read 12 bytes from server:1234')

        assert_equals('buffereddata', self.transport.read(0))

    def test_read_when_socket_closes(self):
        self.transport._sock = mock()
        self.transport.connection.debug = 2

        expect(self.transport._sock.settimeout).args(None)
        expect(self.transport._sock.getsockopt).any_args().returns(4095)
        expect(self.transport._sock.recv).args(4095).returns('')
        expect(self.transport.connection.transport_closed).args(
            msg='error reading from server:1234')

        self.transport.read()

    def test_read_when_socket_timeout(self):
        self.transport._sock = mock()
        self.transport.connection.debug = 2

        expect(self.transport._sock.settimeout).args(42)
        expect(self.transport._sock.getsockopt).any_args().returns(4095)
        expect(self.transport._sock.recv).args(4095).raises(
            socket.timeout('not now'))

        assert_equals(None, self.transport.read(42))

    def test_read_when_raises_eagain(self):
        self.transport._sock = mock()
        self.transport.connection.debug = 2

        expect(self.transport._sock.settimeout).args(42)
        expect(self.transport._sock.getsockopt).any_args().returns(4095)
        expect(self.transport._sock.recv).args(4095).raises(
            EnvironmentError(errno.EAGAIN, 'tryagainlater'))

        assert_equals(None, self.transport.read(42))

    def test_read_when_raises_socket_timeout(self):
        self.transport._sock = mock()
        self.transport.connection.debug = 2

        expect(self.transport._sock.settimeout).args(42)
        expect(self.transport._sock.getsockopt).any_args().returns(4095)
        expect(self.transport._sock.recv).args(4095).raises(
            socket.timeout())

        assert_equals(None, self.transport.read(42))

    def test_read_when_raises_other_errno(self):
        self.transport._sock = mock()
        self.transport.connection.debug = 2

        expect(self.transport._sock.settimeout).args(42)
        expect(self.transport._sock.getsockopt).any_args().returns(4095)
        expect(self.transport._sock.recv).args(4095).raises(
            EnvironmentError(errno.EBADF, 'baddog'))
        expect(self.transport.connection.logger.exception).args(
            'error reading from server:1234')
        expect(self.transport.connection.transport_closed).args(
            msg='error reading from server:1234')

        with assert_raises(EnvironmentError):
            self.transport.read(42)

    def test_read_when_no_sock(self):
        self.transport.read()

    def test_buffer(self):
        self.transport._sock = mock()

        self.transport.buffer(bytearray('somedata'))
        assert_equals(bytearray('somedata'), self.transport._buffer)

    def test_buffer_when_already_buffered(self):
        self.transport._sock = mock()
        self.transport._buffer = bytearray('some')

        self.transport.buffer(bytearray('data'))
        assert_equals(bytearray('somedata'), self.transport._buffer)

    def test_buffer_when_no_sock(self):
        self.transport.buffer('somedata')

    def test_write(self):
        self.transport._sock = mock()
        self.transport.connection.debug = False

        expect(self.transport._sock.sendall).args('somedata')
        self.transport.write('somedata')

    def test_write_when_sendall_fails(self):
        self.transport._sock = mock()
        self.transport.connection.debug = False

        expect(self.transport._sock.sendall).args(
            'somedata').raises(Exception('fail'))
        assert_raises(Exception, self.transport.write, 'somedata')

    def test_write_when_sendall_raises_environmenterror(self):
        self.transport._sock = mock()
        self.transport.connection.debug = False

        expect(self.transport._sock.sendall).args('somedata').raises(
            EnvironmentError(errno.EAGAIN, 'tryagainlater'))
        expect(self.transport.connection.logger.exception).args(
            'error writing to server:1234')
        expect(self.transport.connection.transport_closed).args(
            msg='error writing to server:1234')
        self.transport.write('somedata')

    def test_write_when_debugging(self):
        self.transport._sock = mock()
        self.transport.connection.debug = 2

        expect(self.transport._sock.sendall).args('somedata')
        expect(self.transport.connection.logger.debug).args(
            'sent 8 bytes to server:1234')

        self.transport.write('somedata')

    def test_write_when_no_sock(self):
        self.transport.write('somedata')

    def test_disconnect(self):
        self.transport._sock = mock()
        expect(self.transport._sock.close)
        self.transport.disconnect()
        assert_equals(None, self.transport._sock)

    def test_disconnect_when_no_sock(self):
        self.transport.disconnect()

########NEW FILE########
__FILENAME__ = transport_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai

from haigha.transports.transport import Transport


class TransportTest(Chai):

    def test_init_and_connection_property(self):
        t = Transport('conn')
        assert_equals('conn', t._connection)
        assert_equals('conn', t.connection)

    def test_process_channels(self):
        t = Transport('conn')
        ch1 = mock()
        ch2 = mock()
        chs = set([ch1, ch2])
        expect(ch1.process_frames)
        expect(ch2.process_frames)

        t.process_channels(chs)

########NEW FILE########
__FILENAME__ = writer_test
'''
Copyright (c) 2011-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/haigha/blob/master/LICENSE.txt
'''

from chai import Chai
from datetime import datetime
from decimal import Decimal

from haigha.writer import Writer


class WriterTest(Chai):

    def test_init(self):
        w = Writer()
        assert_equals(bytearray(), w._output_buffer)

        w = Writer(buf='foo')
        assert_equals('foo', w._output_buffer)

    def test_str(self):
        w = Writer(bytearray('\x03\xfb\x4d'))
        assert_equals('\\x03\\xfb\\x4d', str(w))
        assert_equals('\\x03\\xfb\\x4d', repr(w))

    def test_eq(self):
        assert_equals(Writer(bytearray('foo')), Writer(bytearray('foo')))
        assert_not_equals(Writer(bytearray('foo')), Writer(bytearray('bar')))

    def test_buffer(self):
        b = bytearray('pbt')
        assert_true(b is Writer(b).buffer())

    def test_write(self):
        w = Writer()
        assert_true(w is w.write('foo'))
        assert_equals(bytearray('foo'), w._output_buffer)

    def test_write_bits(self):
        w = Writer()
        assert_true(w is w.write_bits(False, True))
        assert_equals(bytearray('\x02'), w._output_buffer)
        w = Writer()
        assert_true(w is w.write_bits(False, False, True, True, True))
        assert_equals(bytearray('\x1c'), w._output_buffer)

        assert_raises(ValueError, w.write_bits, *((True,) * 9))

    def test_write_bit(self):
        w = Writer()
        assert_true(w is w.write_bit(True))
        assert_equals(bytearray('\x01'), w._output_buffer)

    def test_write_octet(self):
        w = Writer()
        assert_true(w is w.write_octet(0))
        assert_true(w is w.write_octet(255))
        assert_equals(bytearray('\x00\xff'), w._output_buffer)

        assert_raises(ValueError, w.write_octet, -1)
        assert_raises(ValueError, w.write_octet, 2 ** 8)

    def test_write_short(self):
        w = Writer()
        assert_true(w is w.write_short(0))
        assert_true(w is w.write_short(2 ** 16 - 2))
        assert_equals(bytearray('\x00\x00\xff\xfe'), w._output_buffer)

        assert_raises(ValueError, w.write_short, -1)
        assert_raises(ValueError, w.write_short, 2 ** 16)

    def test_write_short_at(self):
        w = Writer(bytearray('\x00' * 6))
        assert_true(w is w.write_short_at(2 ** 16 - 1, 2))
        assert_equals(bytearray('\x00\x00\xff\xff\x00\x00'), w._output_buffer)

        assert_raises(ValueError, w.write_short_at, -1, 2)
        assert_raises(ValueError, w.write_short_at, 2 ** 16, 3)

    def test_write_long(self):
        w = Writer()
        assert_true(w is w.write_long(0))
        assert_true(w is w.write_long(2 ** 32 - 2))
        assert_equals(
            bytearray('\x00\x00\x00\x00\xff\xff\xff\xfe'), w._output_buffer)

        assert_raises(ValueError, w.write_long, -1)
        assert_raises(ValueError, w.write_long, 2 ** 32)

    def test_write_long_at(self):
        w = Writer(bytearray('\x00' * 8))
        assert_true(w is w.write_long_at(2 ** 32 - 1, 2))
        assert_equals(
            bytearray('\x00\x00\xff\xff\xff\xff\x00\x00'), w._output_buffer)

        assert_raises(ValueError, w.write_long_at, -1, 2)
        assert_raises(ValueError, w.write_long_at, 2 ** 32, 3)

    def test_write_long_long(self):
        w = Writer()
        assert_true(w is w.write_longlong(0))
        assert_true(w is w.write_longlong(2 ** 64 - 2))
        assert_equals(
            bytearray(
                '\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xfe'),
            w._output_buffer)

        assert_raises(ValueError, w.write_longlong, -1)
        assert_raises(ValueError, w.write_longlong, 2 ** 64)

    def test_write_shortstr(self):
        w = Writer()
        assert_true(w is w.write_shortstr(''))
        assert_equals(bytearray('\x00'), w._output_buffer)
        w = Writer()
        assert_true(w is w.write_shortstr('a' * 255))
        assert_equals(bytearray('\xff' + ('a' * 255)), w._output_buffer)
        w = Writer()
        assert_true(w is w.write_shortstr('Au\xc3\x9ferdem'.decode('utf8')))
        assert_equals(bytearray('\x09Au\xc3\x9ferdem'), w._output_buffer)

        assert_raises(ValueError, w.write_shortstr, 'a' * 256)

    def test_write_longstr(self):
        # We can't actually build a string 2**32 long, so can't also test the
        # valueerror without mocking
        w = Writer()
        assert_true(w is w.write_longstr(''))
        assert_equals(bytearray('\x00\x00\x00\x00'), w._output_buffer)
        w = Writer()
        assert_true(w is w.write_longstr('a' * (2 ** 16)))
        assert_equals(
            bytearray('\x00\x01\x00\x00' + ('a' * 2 ** 16)), w._output_buffer)
        w = Writer()
        assert_true(w is w.write_longstr('Au\xc3\x9ferdem'.decode('utf8')))
        assert_equals(
            bytearray('\x00\x00\x00\x09Au\xc3\x9ferdem'), w._output_buffer)

        # TODO: mock valueerror when chai fixes the '__len__' problems with Mocks
        # since we can't actually create a long-enough string

    def test_write_timestamp(self):
        w = Writer()
        w.write_timestamp(datetime(2011, 1, 17, 22, 36, 33))

        assert_equals('\x00\x00\x00\x00\x4d\x34\xc4\x71', w._output_buffer)

    def test_write_table(self):
        w = Writer()
        expect(w._write_item).args('a', 'foo').any_order().side_effect(
            lambda *args: (setattr(w, '_pos', 20), w._output_buffer.extend('afoo')))
        expect(w._write_item).args('b', 'bar').any_order().side_effect(
            lambda *args: (setattr(w, '_pos', 20), w._output_buffer.extend('bbar')))

        assert_true(w is w.write_table({'a': 'foo', 'b': 'bar'}))
        assert_equals('\x00\x00\x00\x08', w._output_buffer[:4])
        assert_equals(12, len(w._output_buffer))

    def test_write_item(self):
        w = Writer()
        expect(w.write_shortstr).args('key')
        expect(w._write_field).args('value')
        w._write_item('key', 'value')

    def test_write_field(self):
        w = Writer()
        unknown = mock()
        expect(w._field_none).args(unknown)
        w._write_field(unknown)

        Writer.field_type_map[type(unknown)] = unknown
        expect(unknown).args(w, unknown)
        w._write_field(unknown)

    def test_field_bool(self):
        w = Writer()
        w._field_bool(True)
        w._field_bool(False)
        assert_equals('t\x01t\x00', w._output_buffer)

    def test_field_int(self):
        w = Writer()
        w._field_int(-2 ** 15)
        w._field_int(2 ** 15 - 1)
        assert_equals('s\x80\x00s\x7f\xff', w._output_buffer)

        w = Writer()
        w._field_int(-2 ** 31)
        w._field_int(2 ** 31 - 1)
        assert_equals('I\x80\x00\x00\x00I\x7f\xff\xff\xff', w._output_buffer)

        w = Writer()
        w._field_int(-2 ** 63)
        w._field_int(2 ** 63 - 1)
        assert_equals(
            'l\x80\x00\x00\x00\x00\x00\x00\x00l\x7f\xff\xff\xff\xff\xff\xff\xff',
            w._output_buffer)

    def test_field_double(self):
        w = Writer()
        w._field_double(3.1457923)
        assert_equals('d\x40\x09\x2a\x95\x27\x44\x11\xa8', w._output_buffer)

    def test_field_decimal(self):
        w = Writer()
        w._field_decimal(Decimal('1.50'))
        assert_equals('D\x02\x00\x00\x00\x96', w._output_buffer)

        w = Writer()
        w._field_decimal(Decimal('-1.50'))
        assert_equals('D\x02\xff\xff\xff\x6a', w._output_buffer)

    def test_field_str(self):
        w = Writer()
        w._field_str('foo')
        assert_equals('S\x00\x00\x00\x03foo', w._output_buffer)

    def test_field_unicode(self):
        w = Writer()
        w._field_unicode('Au\xc3\x9ferdem'.decode('utf8'))
        assert_equals('S\x00\x00\x00\x09Au\xc3\x9ferdem', w._output_buffer)

    def test_field_timestamp(self):
        w = Writer()
        w._field_timestamp(datetime(2011, 1, 17, 22, 36, 33))

        assert_equals('T\x00\x00\x00\x00\x4d\x34\xc4\x71', w._output_buffer)

    def test_field_table(self):
        w = Writer()
        expect(w.write_table).args({'foo': 'bar'}).side_effect(
            lambda *args: w._output_buffer.extend('tdata'))
        w._field_table({'foo': 'bar'})

        assert_equals('Ftdata', w._output_buffer)

    def test_field_none(self):
        w = Writer()
        w._field_none(None)
        w._field_none('zomg')
        assert_equals('VV', w._output_buffer)

    def test_field_bytearray(self):
        w = Writer()
        w._field_bytearray(bytearray('foo'))
        assert_equals('x\x00\x00\x00\x03foo', w._output_buffer)

    def test_write_field_supports_subclasses(self):
        class SubString(str):
            pass
        w = Writer()
        w._write_field(SubString('foo'))
        assert_equals('S\x00\x00\x00\x03foo', w._output_buffer)

    def test_field_iterable(self):
        w = Writer()
        expect(w._write_field).args('la').side_effect(
            lambda field: w._output_buffer.append('a'))
        expect(w._write_field).args('lb').side_effect(
            lambda field: w._output_buffer.append('b'))
        w._field_iterable(['la', 'lb'])

        expect(w._write_field).args('ta').side_effect(
            lambda field: w._output_buffer.append('a'))
        expect(w._write_field).args('tb').side_effect(
            lambda field: w._output_buffer.append('b'))
        w._field_iterable(('ta', 'tb'))

        expect(w._write_field).args('sa').any_order().side_effect(
            lambda field: w._output_buffer.append('s'))
        expect(w._write_field).args('sb').any_order().side_effect(
            lambda field: w._output_buffer.append('s'))
        w._field_iterable(set(('sa', 'sb')))

        assert_equals('AabAabAss', w._output_buffer)

    def test_field_type_map(self):
        assert_equals(
            {
                bool: Writer._field_bool.im_func,
                int: Writer._field_int.im_func,
                long: Writer._field_int.im_func,
                float: Writer._field_double.im_func,
                Decimal: Writer._field_decimal.im_func,
                str: Writer._field_str.im_func,
                unicode: Writer._field_unicode.im_func,
                datetime: Writer._field_timestamp.im_func,
                dict: Writer._field_table.im_func,
                type(None): Writer._field_none.im_func,
                bytearray: Writer._field_bytearray.im_func,
            }, Writer.field_type_map)

########NEW FILE########
