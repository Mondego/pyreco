__FILENAME__ = base
"""

Backend base classes.

"""
from carrot import serialization

ACKNOWLEDGED_STATES = frozenset(["ACK", "REJECTED", "REQUEUED"])


class MessageStateError(Exception):
    """The message has already been acknowledged."""


class BaseMessage(object):
    """Base class for received messages."""
    _state = None

    MessageStateError = MessageStateError

    def __init__(self, backend, **kwargs):
        self.backend = backend
        self.body = kwargs.get("body")
        self.delivery_tag = kwargs.get("delivery_tag")
        self.content_type = kwargs.get("content_type")
        self.content_encoding = kwargs.get("content_encoding")
        self.delivery_info = kwargs.get("delivery_info", {})
        self._decoded_cache = None
        self._state = "RECEIVED"

    def decode(self):
        """Deserialize the message body, returning the original
        python structure sent by the publisher."""
        return serialization.decode(self.body, self.content_type,
                                    self.content_encoding)

    @property
    def payload(self):
        """The decoded message."""
        if not self._decoded_cache:
            self._decoded_cache = self.decode()
        return self._decoded_cache

    def ack(self):
        """Acknowledge this message as being processed.,
        This will remove the message from the queue.

        :raises MessageStateError: If the message has already been
            acknowledged/requeued/rejected.

        """
        if self.acknowledged:
            raise self.MessageStateError(
                "Message already acknowledged with state: %s" % self._state)
        self.backend.ack(self.delivery_tag)
        self._state = "ACK"

    def reject(self):
        """Reject this message.

        The message will be discarded by the server.

        :raises MessageStateError: If the message has already been
            acknowledged/requeued/rejected.

        """
        if self.acknowledged:
            raise self.MessageStateError(
                "Message already acknowledged with state: %s" % self._state)
        self.backend.reject(self.delivery_tag)
        self._state = "REJECTED"

    def requeue(self):
        """Reject this message and put it back on the queue.

        You must not use this method as a means of selecting messages
        to process.

        :raises MessageStateError: If the message has already been
            acknowledged/requeued/rejected.

        """
        if self.acknowledged:
            raise self.MessageStateError(
                "Message already acknowledged with state: %s" % self._state)
        self.backend.requeue(self.delivery_tag)
        self._state = "REQUEUED"

    @property
    def acknowledged(self):
        return self._state in ACKNOWLEDGED_STATES


class BaseBackend(object):
    """Base class for backends."""
    default_port = None
    extra_options = None

    connection_errors = ()
    channel_errors = ()

    def __init__(self, connection, **kwargs):
        self.connection = connection
        self.extra_options = kwargs.get("extra_options")

    def queue_declare(self, *args, **kwargs):
        """Declare a queue by name."""
        pass

    def queue_delete(self, *args, **kwargs):
        """Delete a queue by name."""
        pass

    def exchange_declare(self, *args, **kwargs):
        """Declare an exchange by name."""
        pass

    def queue_bind(self, *args, **kwargs):
        """Bind a queue to an exchange."""
        pass

    def get(self, *args, **kwargs):
        """Pop a message off the queue."""
        pass

    def declare_consumer(self, *args, **kwargs):
        pass

    def consume(self, *args, **kwargs):
        """Iterate over the declared consumers."""
        pass

    def cancel(self, *args, **kwargs):
        """Cancel the consumer."""
        pass

    def ack(self, delivery_tag):
        """Acknowledge the message."""
        pass

    def queue_purge(self, queue, **kwargs):
        """Discard all messages in the queue. This will delete the messages
        and results in an empty queue."""
        return 0

    def reject(self, delivery_tag):
        """Reject the message."""
        pass

    def requeue(self, delivery_tag):
        """Requeue the message."""
        pass

    def purge(self, queue, **kwargs):
        """Discard all messages in the queue."""
        pass

    def message_to_python(self, raw_message):
        """Convert received message body to a python datastructure."""
        return raw_message

    def prepare_message(self, message_data, delivery_mode, **kwargs):
        """Prepare message for sending."""
        return message_data

    def publish(self, message, exchange, routing_key, **kwargs):
        """Publish a message."""
        pass

    def close(self):
        """Close the backend."""
        pass

    def establish_connection(self):
        """Establish a connection to the backend."""
        pass

    def close_connection(self, connection):
        """Close the connection."""
        pass

    def flow(self, active):
        """Enable/disable flow from peer."""
        pass

    def qos(self, prefetch_size, prefetch_count, apply_global=False):
        """Request specific Quality of Service."""
        pass

########NEW FILE########
__FILENAME__ = librabbitmq
"""

`amqplib`_ backend for carrot.

.. _`amqplib`: http://barryp.org/software/py-amqplib/

"""
import pylibrabbitmq as amqp
from pylibrabbitmq import ChannelError, ConnectionError
from carrot.backends.base import BaseMessage, BaseBackend
from itertools import count
import warnings
import weakref

DEFAULT_PORT = 5672


class Message(BaseMessage):
    """A message received by the broker.

    Usually you don't insantiate message objects yourself, but receive
    them using a :class:`carrot.messaging.Consumer`.

    :param backend: see :attr:`backend`.
    :param amqp_message: see :attr:`_amqp_message`.


    .. attribute:: body

        The message body.

    .. attribute:: delivery_tag

        The message delivery tag, uniquely identifying this message.

    .. attribute:: backend

        The message backend used.
        A subclass of :class:`carrot.backends.base.BaseBackend`.

    .. attribute:: _amqp_message

        A :class:`amqplib.client_0_8.basic_message.Message` instance.
        This is a private attribute and should not be accessed by
        production code.

    """

    def __init__(self, backend, amqp_message, **kwargs):
        self._amqp_message = amqp_message
        self.backend = backend
        kwargs["body"] = amqp_message.body
        properties = amqp_message.properties
        kwargs["content_type"] = properties["content_type"]
        kwargs["content_encoding"] = properties["content_encoding"]
        kwargs["delivery_info"] = amqp_message.delivery_info
        kwargs["delivery_tag"] = amqp_message.delivery_info["delivery_tag"]

        super(Message, self).__init__(backend, **kwargs)


class Backend(BaseBackend):
    """amqplib backend

    :param connection: see :attr:`connection`.


    .. attribute:: connection

    A :class:`carrot.connection.BrokerConnection` instance. An established
    connection to the broker.

    """
    default_port = DEFAULT_PORT

    Message = Message

    def __init__(self, connection, **kwargs):
        self.connection = connection
        self.default_port = kwargs.get("default_port", self.default_port)
        self._channel_ref = None

    @property
    def _channel(self):
        return callable(self._channel_ref) and self._channel_ref()

    @property
    def channel(self):
        """If no channel exists, a new one is requested."""
        if not self._channel:
            self._channel_ref = weakref.ref(self.connection.get_channel())
        return self._channel

    def establish_connection(self):
        """Establish connection to the AMQP broker."""
        conninfo = self.connection
        if not conninfo.hostname:
            raise KeyError("Missing hostname for AMQP connection.")
        if conninfo.userid is None:
            raise KeyError("Missing user id for AMQP connection.")
        if conninfo.password is None:
            raise KeyError("Missing password for AMQP connection.")
        if not conninfo.port:
            conninfo.port = self.default_port
        conn = amqp.Connection(host=conninfo.hostname,
                               port=conninfo.port,
                               userid=conninfo.userid,
                               password=conninfo.password,
                               virtual_host=conninfo.virtual_host)
        return conn

    def close_connection(self, connection):
        """Close the AMQP broker connection."""
        connection.close()

    def queue_exists(self, queue):
        return True

    def queue_delete(self, queue, if_unused=False, if_empty=False):
        """Delete queue by name."""
        pass

    def queue_purge(self, queue, **kwargs):
        """Discard all messages in the queue. This will delete the messages
        and results in an empty queue."""
        return self.channel.queue_purge(queue=queue)

    def queue_declare(self, queue, durable, exclusive, auto_delete,
            warn_if_exists=False):
        """Declare a named queue."""
        return self.channel.queue_declare(queue=queue,
                                          durable=durable,
                                          exclusive=exclusive,
                                          auto_delete=auto_delete)

    def exchange_declare(self, exchange, type, durable, auto_delete):
        """Declare an named exchange."""
        return self.channel.exchange_declare(exchange=exchange,
                                             type=type,
                                             durable=durable,
                                             auto_delete=auto_delete)

    def queue_bind(self, queue, exchange, routing_key, arguments=None):
        """Bind queue to an exchange using a routing key."""
        return self.channel.queue_bind(queue=queue,
                                       exchange=exchange,
                                       routing_key=routing_key,
                                       arguments=arguments)

    def message_to_python(self, raw_message):
        """Convert encoded message body back to a Python value."""
        return self.Message(backend=self, amqp_message=raw_message)

    def get(self, queue, no_ack=False):
        """Receive a message from a declared queue by name.

        :returns: A :class:`Message` object if a message was received,
            ``None`` otherwise. If ``None`` was returned, it probably means
            there was no messages waiting on the queue.

        """
        raw_message = self.channel.basic_get(queue, no_ack=no_ack)
        if not raw_message:
            return None
        return self.message_to_python(raw_message)

    def declare_consumer(self, queue, no_ack, callback, consumer_tag,
            nowait=False):
        """Declare a consumer."""
        return self.channel.basic_consume(queue=queue,
                                          no_ack=no_ack,
                                          callback=callback,
                                          consumer_tag=consumer_tag)

    def consume(self, limit=None):
        """Returns an iterator that waits for one message at a time."""
        for total_message_count in count():
            if limit and total_message_count >= limit:
                raise StopIteration

            if not self.channel.is_open:
                raise StopIteration

            self.channel.conn.drain_events()
            yield True

    def cancel(self, consumer_tag):
        """Cancel a channel by consumer tag."""
        if not self.channel.conn:
            return
        self.channel.basic_cancel(consumer_tag)

    def close(self):
        """Close the channel if open."""
        if self._channel and self._channel.is_open:
            self._channel.close()
        self._channel_ref = None

    def ack(self, delivery_tag):
        """Acknowledge a message by delivery tag."""
        return self.channel.basic_ack(delivery_tag)

    def reject(self, delivery_tag):
        """Reject a message by deliver tag."""
        return self.channel.basic_reject(delivery_tag, requeue=False)

    def requeue(self, delivery_tag):
        """Reject and requeue a message by delivery tag."""
        return self.channel.basic_reject(delivery_tag, requeue=True)

    def prepare_message(self, message_data, delivery_mode, priority=None,
                content_type=None, content_encoding=None):
        """Encapsulate data into a AMQP message."""
        return amqp.Message(message_data, properties={
                "delivery_mode": delivery_mode,
                "priority": priority,
                "content_type": content_type,
                "content_encoding": content_encoding})

    def publish(self, message, exchange, routing_key, mandatory=None,
            immediate=None, headers=None):
        """Publish a message to a named exchange."""

        if headers:
            message.properties["headers"] = headers

        ret = self.channel.basic_publish(message, exchange=exchange,
                                         routing_key=routing_key,
                                         mandatory=mandatory,
                                         immediate=immediate)
        if mandatory or immediate:
            self.close()

    def qos(self, prefetch_size, prefetch_count, apply_global=False):
        """Request specific Quality of Service."""
        pass
        #self.channel.basic_qos(prefetch_size, prefetch_count,
        #                        apply_global)

    def flow(self, active):
        """Enable/disable flow from peer."""
        pass
        #self.channel.flow(active)

########NEW FILE########
__FILENAME__ = pikachu
import asyncore
import weakref
import functools
import itertools

import pika

from carrot.backends.base import BaseMessage, BaseBackend

DEFAULT_PORT = 5672


class Message(BaseMessage):

    def __init__(self, backend, amqp_message, **kwargs):
        channel, method, header, body = amqp_message
        self._channel = channel
        self._method = method
        self._header = header
        self.backend = backend

        kwargs.update({"body": body,
                       "delivery_tag": method.delivery_tag,
                       "content_type": header.content_type,
                       "content_encoding": header.content_encoding,
                       "delivery_info": dict(
                            consumer_tag=method.consumer_tag,
                            routing_key=method.routing_key,
                            delivery_tag=method.delivery_tag,
                            exchange=method.exchange)})

        super(Message, self).__init__(backend, **kwargs)


class SyncBackend(BaseBackend):
    default_port = DEFAULT_PORT
    _connection_cls = pika.BlockingConnection

    Message = Message

    def __init__(self, connection, **kwargs):
        self.connection = connection
        self.default_port = kwargs.get("default_port", self.default_port)
        self._channel_ref = None

    @property
    def _channel(self):
        return callable(self._channel_ref) and self._channel_ref()

    @property
    def channel(self):
        """If no channel exists, a new one is requested."""
        if not self._channel:
            self._channel_ref = weakref.ref(self.connection.get_channel())
        return self._channel

    def establish_connection(self):
        """Establish connection to the AMQP broker."""
        conninfo = self.connection
        if not conninfo.port:
            conninfo.port = self.default_port
        credentials = pika.PlainCredentials(conninfo.userid,
                                            conninfo.password)
        return self._connection_cls(pika.ConnectionParameters(
                                           conninfo.hostname,
                                           port=conninfo.port,
                                           virtual_host=conninfo.virtual_host,
                                           credentials=credentials))

    def close_connection(self, connection):
        """Close the AMQP broker connection."""
        connection.close()

    def queue_exists(self, queue):
        return False # FIXME

    def queue_delete(self, queue, if_unused=False, if_empty=False):
        """Delete queue by name."""
        return self.channel.queue_delete(queue=queue, if_unused=if_unused,
                                         if_empty=if_empty)

    def queue_purge(self, queue, **kwargs):
        """Discard all messages in the queue. This will delete the messages
        and results in an empty queue."""
        return self.channel.queue_purge(queue=queue).message_count

    def queue_declare(self, queue, durable, exclusive, auto_delete,
            warn_if_exists=False, arguments=None):
        """Declare a named queue."""

        return self.channel.queue_declare(queue=queue,
                                          durable=durable,
                                          exclusive=exclusive,
                                          auto_delete=auto_delete,
                                          arguments=arguments)

    def exchange_declare(self, exchange, type, durable, auto_delete):
        """Declare an named exchange."""
        return self.channel.exchange_declare(exchange=exchange,
                                             type=type,
                                             durable=durable,
                                             auto_delete=auto_delete)

    def queue_bind(self, queue, exchange, routing_key, arguments={}):
        """Bind queue to an exchange using a routing key."""
        if not arguments:
            arguments = {}
        return self.channel.queue_bind(queue=queue,
                                       exchange=exchange,
                                       routing_key=routing_key,
                                       arguments=arguments)

    def message_to_python(self, raw_message):
        """Convert encoded message body back to a Python value."""
        return self.Message(backend=self, amqp_message=raw_message)

    def get(self, queue, no_ack=False):
        """Receive a message from a declared queue by name.

        :returns: A :class:`Message` object if a message was received,
            ``None`` otherwise. If ``None`` was returned, it probably means
            there was no messages waiting on the queue.

        """
        raw_message = self.channel.basic_get(queue=queue, no_ack=no_ack)
        if not raw_message:
            return None
        return self.message_to_python(raw_message)

    def declare_consumer(self, queue, no_ack, callback, consumer_tag,
            nowait=False):
        """Declare a consumer."""

        @functools.wraps(callback)
        def _callback_decode(channel, method, header, body):
            return callback((channel, method, header, body))

        return self.channel.basic_consume(_callback_decode,
                                          queue=queue,
                                          no_ack=no_ack,
                                          consumer_tag=consumer_tag)

    def consume(self, limit=None):
        """Returns an iterator that waits for one message at a time."""
        for total_message_count in itertools.count():
            if limit and total_message_count >= limit:
                raise StopIteration
            self.connection.connection.drain_events()
            yield True

    def cancel(self, consumer_tag):
        """Cancel a channel by consumer tag."""
        if not self._channel:
            return
        self.channel.basic_cancel(consumer_tag)

    def close(self):
        """Close the channel if open."""
        if self._channel and not self._channel.handler.channel_close:
            self._channel.close()
        self._channel_ref = None

    def ack(self, delivery_tag):
        """Acknowledge a message by delivery tag."""
        return self.channel.basic_ack(delivery_tag)

    def reject(self, delivery_tag):
        """Reject a message by deliver tag."""
        return self.channel.basic_reject(delivery_tag, requeue=False)

    def requeue(self, delivery_tag):
        """Reject and requeue a message by delivery tag."""
        return self.channel.basic_reject(delivery_tag, requeue=True)

    def prepare_message(self, message_data, delivery_mode, priority=None,
            content_type=None, content_encoding=None):
        """Encapsulate data into a AMQP message."""
        properties = pika.BasicProperties(priority=priority,
                                          content_type=content_type,
                                          content_encoding=content_encoding,
                                          delivery_mode=delivery_mode)
        return message_data, properties

    def publish(self, message, exchange, routing_key, mandatory=None,
            immediate=None, headers=None):
        """Publish a message to a named exchange."""
        body, properties = message

        if headers:
            properties.headers = headers

        ret = self.channel.basic_publish(body=body,
                                         properties=properties,
                                         exchange=exchange,
                                         routing_key=routing_key,
                                         mandatory=mandatory,
                                         immediate=immediate)
        if mandatory or immediate:
            self.close()

    def qos(self, prefetch_size, prefetch_count, apply_global=False):
        """Request specific Quality of Service."""
        self.channel.basic_qos(prefetch_size, prefetch_count,
                                apply_global)

    def flow(self, active):
        """Enable/disable flow from peer."""
        self.channel.flow(active)


class AsyncoreBackend(SyncBackend):
    _connection_cls = pika.AsyncoreConnection

########NEW FILE########
__FILENAME__ = pyamqplib
"""

`amqplib`_ backend for carrot.

.. _`amqplib`: http://barryp.org/software/py-amqplib/

"""
from amqplib.client_0_8 import transport
# amqplib's handshake mistakenly identifies as protocol version 1191,
# this breaks in RabbitMQ tip, which no longer falls back to
# 0-8 for unknown ids.
transport.AMQP_PROTOCOL_HEADER = "AMQP\x01\x01\x08\x00"

from amqplib import client_0_8 as amqp
from amqplib.client_0_8.exceptions import AMQPConnectionException
from amqplib.client_0_8.exceptions import AMQPChannelException
from amqplib.client_0_8.serialization import AMQPReader, AMQPWriter
from carrot.backends.base import BaseMessage, BaseBackend
from itertools import count

import socket
import warnings
import weakref

DEFAULT_PORT = 5672


class Connection(amqp.Connection):

    def drain_events(self, allowed_methods=None, timeout=None):
        """Wait for an event on any channel."""
        return self.wait_multi(self.channels.values(), timeout=timeout)

    def wait_multi(self, channels, allowed_methods=None, timeout=None):
        """Wait for an event on a channel."""
        chanmap = dict((chan.channel_id, chan) for chan in channels)
        chanid, method_sig, args, content = self._wait_multiple(
                chanmap.keys(), allowed_methods, timeout=timeout)

        channel = chanmap[chanid]

        if content \
        and channel.auto_decode \
        and hasattr(content, 'content_encoding'):
            try:
                content.body = content.body.decode(content.content_encoding)
            except Exception:
                pass

        amqp_method = channel._METHOD_MAP.get(method_sig, None)

        if amqp_method is None:
            raise Exception('Unknown AMQP method (%d, %d)' % method_sig)

        if content is None:
            return amqp_method(channel, args)
        else:
            return amqp_method(channel, args, content)

    def read_timeout(self, timeout=None):
        if timeout is None:
            return self.method_reader.read_method()
        sock = self.transport.sock
        prev = sock.gettimeout()
        sock.settimeout(timeout)
        try:
            return self.method_reader.read_method()
        finally:
            sock.settimeout(prev)

    def _wait_multiple(self, channel_ids, allowed_methods, timeout=None):
        for channel_id in channel_ids:
            method_queue = self.channels[channel_id].method_queue
            for queued_method in method_queue:
                method_sig = queued_method[0]
                if (allowed_methods is None) \
                or (method_sig in allowed_methods) \
                or (method_sig == (20, 40)):
                    method_queue.remove(queued_method)
                    method_sig, args, content = queued_method
                    return channel_id, method_sig, args, content

        # Nothing queued, need to wait for a method from the peer
        while True:
            channel, method_sig, args, content = self.read_timeout(timeout)

            if (channel in channel_ids) \
            and ((allowed_methods is None) \
                or (method_sig in allowed_methods) \
                or (method_sig == (20, 40))):
                return channel, method_sig, args, content

            # Not the channel and/or method we were looking for. Queue
            # this method for later
            self.channels[channel].method_queue.append((method_sig,
                                                        args,
                                                        content))

            #
            # If we just queued up a method for channel 0 (the Connection
            # itself) it's probably a close method in reaction to some
            # error, so deal with it right away.
            #
            if channel == 0:
                self.wait()


class QueueAlreadyExistsWarning(UserWarning):
    """A queue with that name already exists, so a recently changed
    ``routing_key`` or other settings might be ignored unless you
    rename the queue or restart the broker."""


class Message(BaseMessage):
    """A message received by the broker.

    Usually you don't insantiate message objects yourself, but receive
    them using a :class:`carrot.messaging.Consumer`.

    :param backend: see :attr:`backend`.
    :param amqp_message: see :attr:`_amqp_message`.


    .. attribute:: body

        The message body.

    .. attribute:: delivery_tag

        The message delivery tag, uniquely identifying this message.

    .. attribute:: backend

        The message backend used.
        A subclass of :class:`carrot.backends.base.BaseBackend`.

    .. attribute:: _amqp_message

        A :class:`amqplib.client_0_8.basic_message.Message` instance.
        This is a private attribute and should not be accessed by
        production code.

    """

    def __init__(self, backend, amqp_message, **kwargs):
        self._amqp_message = amqp_message
        self.backend = backend

        for attr_name in ("body",
                          "delivery_tag",
                          "content_type",
                          "content_encoding",
                          "delivery_info"):
            kwargs[attr_name] = getattr(amqp_message, attr_name, None)

        super(Message, self).__init__(backend, **kwargs)


class Backend(BaseBackend):
    """amqplib backend

    :param connection: see :attr:`connection`.


    .. attribute:: connection

    A :class:`carrot.connection.BrokerConnection` instance. An established
    connection to the broker.

    """
    default_port = DEFAULT_PORT

    connection_errors = (AMQPConnectionException,
                         socket.error,
                         IOError,
                         OSError)
    channel_errors = (AMQPChannelException, )

    Message = Message

    def __init__(self, connection, **kwargs):
        self.connection = connection
        self.default_port = kwargs.get("default_port", self.default_port)
        self._channel_ref = None

    @property
    def _channel(self):
        return callable(self._channel_ref) and self._channel_ref()

    @property
    def channel(self):
        """If no channel exists, a new one is requested."""
        if not self._channel:
            connection = self.connection.connection
            self._channel_ref = weakref.ref(connection.channel())
        return self._channel

    def establish_connection(self):
        """Establish connection to the AMQP broker."""
        conninfo = self.connection
        if not conninfo.hostname:
            raise KeyError("Missing hostname for AMQP connection.")
        if conninfo.userid is None:
            raise KeyError("Missing user id for AMQP connection.")
        if conninfo.password is None:
            raise KeyError("Missing password for AMQP connection.")
        if not conninfo.port:
            conninfo.port = self.default_port
        return Connection(host=conninfo.host,
                          userid=conninfo.userid,
                          password=conninfo.password,
                          virtual_host=conninfo.virtual_host,
                          insist=conninfo.insist,
                          ssl=conninfo.ssl,
                          connect_timeout=conninfo.connect_timeout)

    def close_connection(self, connection):
        """Close the AMQP broker connection."""
        connection.close()

    def queue_exists(self, queue):
        """Check if a queue has been declared.

        :rtype bool:

        """
        try:
            self.channel.queue_declare(queue=queue, passive=True)
        except AMQPChannelException, e:
            if e.amqp_reply_code == 404:
                return False
            raise e
        else:
            return True

    def queue_delete(self, queue, if_unused=False, if_empty=False):
        """Delete queue by name."""
        return self.channel.queue_delete(queue, if_unused, if_empty)

    def queue_purge(self, queue, **kwargs):
        """Discard all messages in the queue. This will delete the messages
        and results in an empty queue."""
        return self.channel.queue_purge(queue=queue)

    def queue_declare(self, queue, durable, exclusive, auto_delete,
            warn_if_exists=False, arguments=None):
        """Declare a named queue."""
        if warn_if_exists and self.queue_exists(queue):
            warnings.warn(QueueAlreadyExistsWarning(
                QueueAlreadyExistsWarning.__doc__))

        return self.channel.queue_declare(queue=queue,
                                          durable=durable,
                                          exclusive=exclusive,
                                          auto_delete=auto_delete,
                                          arguments=arguments)

    def exchange_declare(self, exchange, type, durable, auto_delete):
        """Declare an named exchange."""
        return self.channel.exchange_declare(exchange=exchange,
                                             type=type,
                                             durable=durable,
                                             auto_delete=auto_delete)

    def queue_bind(self, queue, exchange, routing_key, arguments=None):
        """Bind queue to an exchange using a routing key."""
        return self.channel.queue_bind(queue=queue,
                                       exchange=exchange,
                                       routing_key=routing_key,
                                       arguments=arguments)

    def message_to_python(self, raw_message):
        """Convert encoded message body back to a Python value."""
        return self.Message(backend=self, amqp_message=raw_message)

    def get(self, queue, no_ack=False):
        """Receive a message from a declared queue by name.

        :returns: A :class:`Message` object if a message was received,
            ``None`` otherwise. If ``None`` was returned, it probably means
            there was no messages waiting on the queue.

        """
        raw_message = self.channel.basic_get(queue, no_ack=no_ack)
        if not raw_message:
            return None
        return self.message_to_python(raw_message)

    def declare_consumer(self, queue, no_ack, callback, consumer_tag,
            nowait=False):
        """Declare a consumer."""
        return self.channel.basic_consume(queue=queue,
                                          no_ack=no_ack,
                                          callback=callback,
                                          consumer_tag=consumer_tag,
                                          nowait=nowait)

    def consume(self, limit=None):
        """Returns an iterator that waits for one message at a time."""
        for total_message_count in count():
            if limit and total_message_count >= limit:
                raise StopIteration

            if not self.channel.is_open:
                raise StopIteration

            self.channel.wait()
            yield True

    def cancel(self, consumer_tag):
        """Cancel a channel by consumer tag."""
        if not self.channel.connection:
            return
        self.channel.basic_cancel(consumer_tag)

    def close(self):
        """Close the channel if open."""
        if self._channel and self._channel.is_open:
            self._channel.close()
        self._channel_ref = None

    def ack(self, delivery_tag):
        """Acknowledge a message by delivery tag."""
        return self.channel.basic_ack(delivery_tag)

    def reject(self, delivery_tag):
        """Reject a message by deliver tag."""
        return self.channel.basic_reject(delivery_tag, requeue=False)

    def requeue(self, delivery_tag):
        """Reject and requeue a message by delivery tag."""
        return self.channel.basic_reject(delivery_tag, requeue=True)

    def prepare_message(self, message_data, delivery_mode, priority=None,
                content_type=None, content_encoding=None):
        """Encapsulate data into a AMQP message."""
        message = amqp.Message(message_data, priority=priority,
                               content_type=content_type,
                               content_encoding=content_encoding)
        message.properties["delivery_mode"] = delivery_mode
        return message

    def publish(self, message, exchange, routing_key, mandatory=None,
            immediate=None, headers=None):
        """Publish a message to a named exchange."""

        if headers:
            message.properties["headers"] = headers

        ret = self.channel.basic_publish(message, exchange=exchange,
                                         routing_key=routing_key,
                                         mandatory=mandatory,
                                         immediate=immediate)
        if mandatory or immediate:
            self.close()

    def qos(self, prefetch_size, prefetch_count, apply_global=False):
        """Request specific Quality of Service."""
        self.channel.basic_qos(prefetch_size, prefetch_count,
                                apply_global)

    def flow(self, active):
        """Enable/disable flow from peer."""
        self.channel.flow(active)

########NEW FILE########
__FILENAME__ = pystomp
import time
import socket
from itertools import count

from stompy import Client
from stompy import Empty as QueueEmpty

from carrot.backends.base import BaseMessage, BaseBackend

DEFAULT_PORT = 61613


class Message(BaseMessage):
    """A message received by the STOMP broker.

    Usually you don't insantiate message objects yourself, but receive
    them using a :class:`carrot.messaging.Consumer`.

    :param backend: see :attr:`backend`.
    :param frame: see :attr:`_frame`.

    .. attribute:: body

        The message body.

    .. attribute:: delivery_tag

        The message delivery tag, uniquely identifying this message.

    .. attribute:: backend

        The message backend used.
        A subclass of :class:`carrot.backends.base.BaseBackend`.

    .. attribute:: _frame

        The frame received by the STOMP client. This is considered a private
        variable and should never be used in production code.

    """

    def __init__(self, backend, frame, **kwargs):
        self._frame = frame
        self.backend = backend

        kwargs["body"] = frame.body
        kwargs["delivery_tag"] = frame.headers["message-id"]
        kwargs["content_type"] = frame.headers.get("content-type")
        kwargs["content_encoding"] = frame.headers.get("content-encoding")
        kwargs["priority"] = frame.headers.get("priority")

        super(Message, self).__init__(backend, **kwargs)

    def ack(self):
        """Acknowledge this message as being processed.,
        This will remove the message from the queue.

        :raises MessageStateError: If the message has already been
            acknowledged/requeued/rejected.

        """
        if self.acknowledged:
            raise self.MessageStateError(
                "Message already acknowledged with state: %s" % self._state)
        self.backend.ack(self._frame)
        self._state = "ACK"

    def reject(self):
        raise NotImplementedError(
            "The STOMP backend does not implement basic.reject")

    def requeue(self):
        raise NotImplementedError(
            "The STOMP backend does not implement requeue")


class Backend(BaseBackend):
    Stomp = Client
    Message = Message
    default_port = DEFAULT_PORT

    def __init__(self, connection, **kwargs):
        self.connection = connection
        self.default_port = kwargs.get("default_port", self.default_port)
        self._channel = None
        self._consumers = {} # open consumers by consumer tag
        self._callbacks = {}

    def establish_connection(self):
        conninfo = self.connection
        if not conninfo.port:
            conninfo.port = self.default_port
        stomp = self.Stomp(conninfo.hostname, conninfo.port)
        stomp.connect(username=conninfo.userid, password=conninfo.password)
        stomp.drain_events = self.drain_events
        return stomp

    def close_connection(self, connection):
        try:
            connection.disconnect()
        except socket.error:
            pass

    def queue_exists(self, queue):
        return True

    def queue_purge(self, queue, **kwargs):
        for purge_count in count(0):
            try:
                frame = self.channel.get_nowait()
            except QueueEmpty:
                return purge_count
            else:
                self.channel.ack(frame)

    def declare_consumer(self, queue, no_ack, callback, consumer_tag,
            **kwargs):
        ack = no_ack and "auto" or "client"
        self.channel.subscribe(queue, ack=ack)
        self._consumers[consumer_tag] = queue
        self._callbacks[queue] = callback

    def drain_events(self, timeout=None):
        start_time = time.time()
        while True:
            frame = self.channel.get()
            if frame:
                break
            if time.time() - time_start > timeout:
                raise socket.timeout("the operation timed out.")
        queue = frame.headers.get("destination")
        if not queue or queue not in self._callbacks:
            return
        self._callbacks[queue](frame)

    def consume(self, limit=None):
        """Returns an iterator that waits for one message at a time."""
        for total_message_count in count():
            if limit and total_message_count >= limit:
                raise StopIteration
            self.drain_events()
            yield True

    def queue_declare(self, queue, *args, **kwargs):
        self.channel.subscribe(queue, ack="client")

    def get(self, queue, no_ack=False):
        try:
            frame = self.channel.get_nowait()
        except QueueEmpty:
            return None
        else:
            return self.message_to_python(frame)

    def ack(self, frame):
        self.channel.ack(frame)

    def message_to_python(self, raw_message):
        """Convert encoded message body back to a Python value."""
        return self.Message(backend=self, frame=raw_message)

    def prepare_message(self, message_data, delivery_mode, priority=0,
            content_type=None, content_encoding=None):
        persistent = "false"
        if delivery_mode == 2:
            persistent = "true"
        priority = priority or 0
        return {"body": message_data,
                "persistent": persistent,
                "priority": priority,
                "content-encoding": content_encoding,
                "content-type": content_type}

    def publish(self, message, exchange, routing_key, **kwargs):
        message["destination"] = exchange
        self.channel.stomp.send(message)

    def cancel(self, consumer_tag):
        if not self._channel or consumer_tag not in self._consumers:
            return
        queue = self._consumers.pop(consumer_tag)
        self.channel.unsubscribe(queue)

    def close(self):
        for consumer_tag in self._consumers.keys():
            self.cancel(consumer_tag)
        if self._channel:
            try:
                self._channel.disconnect()
            except socket.error:
                pass

    @property
    def channel(self):
        if not self._channel:
            # Sorry, but the python-stomp library needs one connection
            # for each channel.
            self._channel = self.establish_connection()
        return self._channel

########NEW FILE########
__FILENAME__ = queue
"""

    Backend for unit-tests, using the Python :mod:`Queue` module.

"""
from Queue import Queue
from carrot.backends.base import BaseMessage, BaseBackend
import time
import itertools

mqueue = Queue()


class Message(BaseMessage):
    """Message received from the backend.

    See :class:`carrot.backends.base.BaseMessage`.

    """


class Backend(BaseBackend):
    """Backend using the Python :mod:`Queue` library. Usually only
    used while executing unit tests.

    Please not that this backend does not support queues, exchanges
    or routing keys, so *all messages will be sent to all consumers*.

    """

    Message = Message

    def get(self, *args, **kwargs):
        """Get the next waiting message from the queue.

        :returns: A :class:`Message` instance, or ``None`` if there is
            no messages waiting.

        """
        if not mqueue.qsize():
            return None
        message_data, content_type, content_encoding = mqueue.get()
        return self.Message(backend=self, body=message_data,
                       content_type=content_type,
                       content_encoding=content_encoding)

    def establish_connection(self):
        # for drain_events
        return self

    def drain_events(self, timeout=None):
        message = self.get()
        if message:
            self.callback(message)
        else:
            time.sleep(0.1)

    def consume(self, limit=None):
        """Go into consume mode."""
        for total_message_count in itertools.count():
            if limit and total_message_count >= limit:
                raise StopIteration
            self.drain_events()
            yield True

    def declare_consumer(self, queue, no_ack, callback, consumer_tag,
                         nowait=False):
        self.queue = queue
        self.no_ack = no_ack
        self.callback = callback
        self.consumer_tag = consumer_tag
        self.nowait = nowait

    def queue_purge(self, queue, **kwargs):
        """Discard all messages in the queue."""
        qsize = mqueue.qsize()
        mqueue.queue.clear()
        return qsize

    def prepare_message(self, message_data, delivery_mode,
                        content_type, content_encoding, **kwargs):
        """Prepare message for sending."""
        return (message_data, content_type, content_encoding)

    def publish(self, message, exchange, routing_key, **kwargs):
        """Publish a message to the queue."""
        mqueue.put(message)

########NEW FILE########
__FILENAME__ = connection
"""

Getting a connection to the AMQP server.

"""
import socket
import warnings

from collections import deque
from copy import copy
from Queue import Queue, Empty as QueueEmpty

from amqplib.client_0_8.connection import AMQPConnectionException
from carrot.backends import get_backend_cls
from carrot.utils import retry_over_time

DEFAULT_CONNECT_TIMEOUT = 5 # seconds
SETTING_PREFIX = "BROKER"
COMPAT_SETTING_PREFIX = "AMQP"
ARG_TO_DJANGO_SETTING = {
        "hostname": "HOST",
        "userid": "USER",
        "password": "PASSWORD",
        "virtual_host": "VHOST",
        "port": "PORT",
}
SETTING_DEPRECATED_FMT = "Setting %s has been renamed to %s and is " \
                         "scheduled for removal in version 1.0."


class BrokerConnection(object):
    """A network/socket connection to an AMQP message broker.

    :param hostname: see :attr:`hostname`.
    :param userid: see :attr:`userid`.
    :param password: see :attr:`password`.

    :keyword virtual_host: see :attr:`virtual_host`.
    :keyword port: see :attr:`port`.
    :keyword insist: see :attr:`insist`.
    :keyword connect_timeout: see :attr:`connect_timeout`.
    :keyword ssl: see :attr:`ssl`.

    .. attribute:: hostname

        The hostname to the AMQP server

    .. attribute:: userid

        A valid username used to authenticate to the server.

    .. attribute:: password

        The password used to authenticate to the server.

    .. attribute:: virtual_host

        The name of the virtual host to work with. This virtual host must
        exist on the server, and the user must have access to it. Consult
        your brokers manual for help with creating, and mapping
        users to virtual hosts.
        Default is ``"/"``.

    .. attribute:: port

        The port of the AMQP server.  Default is ``5672`` (amqp).

    .. attribute:: insist

        Insist on connecting to a server. In a configuration with multiple
        load-sharing servers, the insist option tells the server that the
        client is insisting on a connection to the specified server.
        Default is ``False``.

    .. attribute:: connect_timeout

        The timeout in seconds before we give up connecting to the server.
        The default is no timeout.

    .. attribute:: ssl

        Use SSL to connect to the server.
        The default is ``False``.

    .. attribute:: backend_cls

        The messaging backend class used. Defaults to the ``pyamqplib``
        backend.

    """
    virtual_host = "/"
    port = None
    insist = False
    connect_timeout = DEFAULT_CONNECT_TIMEOUT
    ssl = False
    _closed = True
    backend_cls = None

    ConnectionException = AMQPConnectionException

    @property
    def host(self):
        """The host as a hostname/port pair separated by colon."""
        return ":".join([self.hostname, str(self.port)])

    def __init__(self, hostname=None, userid=None, password=None,
            virtual_host=None, port=None, pool=None, **kwargs):
        self.hostname = hostname
        self.userid = userid
        self.password = password
        self.virtual_host = virtual_host or self.virtual_host
        self.port = port or self.port
        self.insist = kwargs.get("insist", self.insist)
        self.pool = pool
        self.connect_timeout = kwargs.get("connect_timeout",
                                          self.connect_timeout)
        self.ssl = kwargs.get("ssl", self.ssl)
        self.backend_cls = (kwargs.get("backend_cls") or
                                kwargs.get("transport"))
        self._closed = None
        self._connection = None

    def __copy__(self):
        return self.__class__(self.hostname, self.userid, self.password,
                              self.virtual_host, self.port,
                              insist=self.insist,
                              connect_timeout=self.connect_timeout,
                              ssl=self.ssl,
                              backend_cls=self.backend_cls,
                              pool=self.pool)

    @property
    def connection(self):
        if self._closed == True:
            return
        if not self._connection:
            self._connection = self._establish_connection()
            self._closed = False
        return self._connection

    def __enter__(self):
        return self

    def __exit__(self, e_type, e_value, e_trace):
        if e_type:
            raise e_type(e_value)
        self.close()

    def _establish_connection(self):
        return self.create_backend().establish_connection()

    def get_backend_cls(self):
        """Get the currently used backend class."""
        backend_cls = self.backend_cls
        if not backend_cls or isinstance(backend_cls, basestring):
            backend_cls = get_backend_cls(backend_cls)
        return backend_cls

    def create_backend(self):
        """Create a new instance of the current backend in
        :attr:`backend_cls`."""
        backend_cls = self.get_backend_cls()
        return backend_cls(connection=self)

    def channel(self):
        """For Kombu compatibility."""
        return self.create_backend()

    def get_channel(self):
        """Request a new AMQP channel."""
        return self.connection.channel()

    def connect(self):
        """Establish a connection to the AMQP server."""
        self._closed = False
        return self.connection

    def drain_events(self, **kwargs):
        return self.connection.drain_events(**kwargs)

    def ensure_connection(self, errback=None, max_retries=None,
            interval_start=2, interval_step=2, interval_max=30):
        """Ensure we have a connection to the server.

        If not retry establishing the connection with the settings
        specified.

        :keyword errback: Optional callback called each time the connection
          can't be established. Arguments provided are the exception
          raised and the interval that will be slept ``(exc, interval)``.

        :keyword max_retries: Maximum number of times to retry.
          If this limit is exceeded the connection error will be re-raised.

        :keyword interval_start: The number of seconds we start sleeping for.
        :keyword interval_step: How many seconds added to the interval
          for each retry.
        :keyword interval_max: Maximum number of seconds to sleep between
          each retry.

        """
        retry_over_time(self.connect, self.connection_errors, (), {},
                        errback, max_retries,
                        interval_start, interval_step, interval_max)
        return self

    def close(self):
        """Close the currently open connection."""
        try:
            if self._connection:
                backend = self.create_backend()
                backend.close_connection(self._connection)
        except socket.error:
            pass
        self._closed = True

    def release(self):
        if not self.pool:
            raise NotImplementedError(
                    "Trying to release connection not part of a pool")
        self.pool.release(self)

    def info(self):
        """Get connection info."""
        backend_cls = self.backend_cls or "amqplib"
        port = self.port or self.create_backend().default_port
        return {"hostname": self.hostname,
                "userid": self.userid,
                "password": self.password,
                "virtual_host": self.virtual_host,
                "port": port,
                "insist": self.insist,
                "ssl": self.ssl,
                "transport_cls": backend_cls,
                "backend_cls": backend_cls,
                "connect_timeout": self.connect_timeout}

    @property
    def connection_errors(self):
        """List of exceptions that may be raised by the connection."""
        return self.create_backend().connection_errors

    @property
    def channel_errors(self):
        """List of exceptions that may be raised by the channel."""
        return self.create_backend().channel_errors

# For backwards compatability.
AMQPConnection = BrokerConnection


class ConnectionLimitExceeded(Exception):
    """The maximum number of pool connections has been exceeded."""


class ConnectionPool(object):

    def __init__(self, source_connection, min=2, max=None, preload=True):
        self.source_connection = source_connection
        self.min = min
        self.max = max
        self.preload = preload
        self.source_connection.pool = self

        self._connections = Queue()
        self._dirty = deque()

        self._connections.put(self.source_connection)
        for i in range(min - 1):
            self._connections.put_nowait(self._new_connection())

    def acquire(self, block=False, timeout=None, connect_timeout=None):
        try:
            conn = self._connections.get(block=block, timeout=timeout)
        except QueueEmpty:
            conn = self._new_connection()
        self._dirty.append(conn)
        if connect_timeout is not None:
            conn.connect_timeout = connect_timeout
        return conn

    def release(self, connection):
        self._dirty.remove(connection)
        self._connections.put_nowait(connection)

    def _new_connection(self):
        if len(self._dirty) >= self.max:
            raise ConnectionLimitExceeded(self.max)
        return copy(self.source_connection)





def get_django_conninfo(settings=None):
    # FIXME can't wait to remove this mess in 1.0 [askh]
    ci = {}
    if settings is None:
        from django.conf import settings

    ci["backend_cls"] = getattr(settings, "CARROT_BACKEND", None)

    for arg_name, setting_name in ARG_TO_DJANGO_SETTING.items():
        setting = "%s_%s" % (SETTING_PREFIX, setting_name)
        compat_setting = "%s_%s" % (COMPAT_SETTING_PREFIX, setting_name)
        if hasattr(settings, setting):
            ci[arg_name] = getattr(settings, setting, None)
        elif hasattr(settings, compat_setting):
            ci[arg_name] = getattr(settings, compat_setting, None)
            warnings.warn(DeprecationWarning(SETTING_DEPRECATED_FMT % (
                compat_setting, setting)))

    if "hostname" not in ci:
        if hasattr(settings, "AMQP_SERVER"):
            ci["hostname"] = settings.AMQP_SERVER
            warnings.warn(DeprecationWarning(
                "AMQP_SERVER has been renamed to BROKER_HOST and is"
                "scheduled for removal in version 1.0."))

    return ci


class DjangoBrokerConnection(BrokerConnection):
    """A version of :class:`BrokerConnection` that takes configuration
    from the Django ``settings.py`` module.

    :keyword hostname: The hostname of the AMQP server to connect to,
        if not provided this is taken from ``settings.BROKER_HOST``.

    :keyword userid: The username of the user to authenticate to the server
        as. If not provided this is taken from ``settings.BROKER_USER``.

    :keyword password: The users password. If not provided this is taken
        from ``settings.BROKER_PASSWORD``.

    :keyword virtual_host: The name of the virtual host to work with.
        This virtual host must exist on the server, and the user must
        have access to it. Consult your brokers manual for help with
        creating, and mapping users to virtual hosts. If not provided
        this is taken from ``settings.BROKER_VHOST``.

    :keyword port: The port the AMQP server is running on. If not provided
        this is taken from ``settings.BROKER_PORT``, or if that is not set,
        the default is ``5672`` (amqp).

    """
    def __init__(self, *args, **kwargs):
        settings = kwargs.pop("settings", None)
        kwargs = dict(get_django_conninfo(settings), **kwargs)
        super(DjangoBrokerConnection, self).__init__(*args, **kwargs)

# For backwards compatability.
DjangoAMQPConnection = DjangoBrokerConnection

########NEW FILE########
__FILENAME__ = messaging
"""

Sending/Receiving Messages.

"""
from itertools import count
from carrot.utils import gen_unique_id
import warnings

from carrot import serialization


class Consumer(object):
    """Message consumer.

    :param connection: see :attr:`connection`.
    :param queue: see :attr:`queue`.
    :param exchange: see :attr:`exchange`.
    :param routing_key: see :attr:`routing_key`.

    :keyword durable: see :attr:`durable`.
    :keyword auto_delete: see :attr:`auto_delete`.
    :keyword exclusive: see :attr:`exclusive`.
    :keyword exchange_type: see :attr:`exchange_type`.
    :keyword auto_ack: see :attr:`auto_ack`.
    :keyword no_ack: see :attr:`no_ack`.
    :keyword auto_declare: see :attr:`auto_declare`.


    .. attribute:: connection

        The connection to the broker.
        A :class:`carrot.connection.BrokerConnection` instance.

    .. attribute:: queue

       Name of the queue.

    .. attribute:: exchange

        Name of the exchange the queue binds to.

    .. attribute:: routing_key

        The routing key (if any). The interpretation of the routing key
        depends on the value of the :attr:`exchange_type` attribute:

            * direct exchange

                Matches if the routing key property of the message and
                the :attr:`routing_key` attribute are identical.

            * fanout exchange

                Always matches, even if the binding does not have a key.

            * topic exchange

                Matches the routing key property of the message by a primitive
                pattern matching scheme. The message routing key then consists
                of words separated by dots (``"."``, like domain names), and
                two special characters are available; star (``"*"``) and hash
                (``"#"``). The star matches any word, and the hash matches
                zero or more words. For example ``"*.stock.#"`` matches the
                routing keys ``"usd.stock"`` and ``"eur.stock.db"`` but not
                ``"stock.nasdaq"``.

    .. attribute:: durable

        Durable exchanges remain active when a server restarts. Non-durable
        exchanges (transient exchanges) are purged when a server restarts.
        Default is ``True``.

    .. attribute:: auto_delete

        If set, the exchange is deleted when all queues have finished
        using it. Default is ``False``.

    .. attribute:: exclusive

        Exclusive queues may only be consumed from by the current connection.
        When :attr:`exclusive` is on, this also implies :attr:`auto_delete`.
        Default is ``False``.

    .. attribute:: exchange_type

        AMQP defines four default exchange types (routing algorithms) that
        covers most of the common messaging use cases. An AMQP broker can
        also define additional exchange types, so see your message brokers
        manual for more information about available exchange types.

            * Direct

                Direct match between the routing key in the message, and the
                routing criteria used when a queue is bound to this exchange.

            * Topic

                Wildcard match between the routing key and the routing pattern
                specified in the binding. The routing key is treated as zero
                or more words delimited by ``"."`` and supports special
                wildcard characters. ``"*"`` matches a single word and ``"#"``
                matches zero or more words.

            * Fanout

                Queues are bound to this exchange with no arguments. Hence any
                message sent to this exchange will be forwarded to all queues
                bound to this exchange.

            * Headers

                Queues are bound to this exchange with a table of arguments
                containing headers and values (optional). A special argument
                named "x-match" determines the matching algorithm, where
                ``"all"`` implies an ``AND`` (all pairs must match) and
                ``"any"`` implies ``OR`` (at least one pair must match).

                Use the :attr:`routing_key`` is used to specify the arguments,
                the same when sending messages.

            This description of AMQP exchange types was shamelessly stolen
            from the blog post `AMQP in 10 minutes: Part 4`_ by
            Rajith Attapattu. Recommended reading.

            .. _`AMQP in 10 minutes: Part 4`:
                http://bit.ly/amqp-exchange-types

    .. attribute:: callbacks

        List of registered callbacks to trigger when a message is received
        by :meth:`wait`, :meth:`process_next` or :meth:`iterqueue`.

    .. attribute:: warn_if_exists

        Emit a warning if the queue has already been declared. If a queue
        already exists, and you try to redeclare the queue with new settings,
        the new settings will be silently ignored, so this can be
        useful if you've recently changed the :attr:`routing_key` attribute
        or other settings.

    .. attribute:: auto_ack

        Acknowledgement is handled automatically once messages are received.
        This means that the :meth:`carrot.backends.base.BaseMessage.ack` and
        :meth:`carrot.backends.base.BaseMessage.reject` methods
        on the message object are no longer valid.
        By default :attr:`auto_ack` is set to ``False``, and the receiver is
        required to manually handle acknowledgment.

    .. attribute:: no_ack

        Disable acknowledgement on the server-side. This is different from
        :attr:`auto_ack` in that acknowledgement is turned off altogether.
        This functionality increases performance but at the cost of
        reliability. Messages can get lost if a client dies before it can
        deliver them to the application.

    .. attribute auto_declare

        If this is ``True`` the following will be automatically declared:

            * The queue if :attr:`queue` is set.
            * The exchange if :attr:`exchange` is set.
            * The :attr:`queue` will be bound to the :attr:`exchange`.

        This is the default behaviour.


    :raises `amqplib.client_0_8.channel.AMQPChannelException`: if the queue is
        exclusive and the queue already exists and is owned by another
        connection.


    Example Usage

        >>> consumer = Consumer(connection=DjangoBrokerConnection(),
        ...               queue="foo", exchange="foo", routing_key="foo")
        >>> def process_message(message_data, message):
        ...     print("Got message %s: %s" % (
        ...             message.delivery_tag, message_data))
        >>> consumer.register_callback(process_message)
        >>> consumer.wait() # Go into receive loop

    """
    queue = ""
    exchange = ""
    routing_key = ""
    durable = True
    exclusive = False
    auto_delete = False
    exchange_type = "direct"
    channel_open = False
    warn_if_exists = False
    auto_declare = True
    auto_ack = False
    queue_arguments = None
    no_ack = False
    _closed = True
    _init_opts = ("durable", "exclusive", "auto_delete",
                  "exchange_type", "warn_if_exists",
                  "auto_ack", "auto_declare",
                  "queue_arguments")
    _next_consumer_tag = count(1).next

    def __init__(self, connection, queue=None, exchange=None,
            routing_key=None, **kwargs):
        self.connection = connection
        self.backend = kwargs.get("backend", None)
        if not self.backend:
            self.backend = self.connection.create_backend()
        self.queue = queue or self.queue

        # Binding.
        self.queue = queue or self.queue
        self.exchange = exchange or self.exchange
        self.routing_key = routing_key or self.routing_key
        self.callbacks = []

        # Options
        for opt_name in self._init_opts:
            opt_value = kwargs.get(opt_name)
            if opt_value is not None:
                setattr(self, opt_name, opt_value)

        # exclusive implies auto-delete.
        if self.exclusive:
            self.auto_delete = True

        self.consumer_tag = self._generate_consumer_tag()

        if self.auto_declare:
            self.declare()

    def __enter__(self):
        return self

    def __exit__(self, e_type, e_value, e_trace):
        if e_type:
            raise e_type(e_value)
        self.close()

    def __iter__(self):
        """iter(Consumer) -> Consumer.iterqueue(infinite=True)"""
        return self.iterqueue(infinite=True)

    def _generate_consumer_tag(self):
        """Generate a unique consumer tag.

        :rtype string:

        """
        return "%s.%s%s" % (
                self.__class__.__module__,
                self.__class__.__name__,
                self._next_consumer_tag())

    def declare(self):
        """Declares the queue, the exchange and binds the queue to
        the exchange."""
        arguments = None
        routing_key = self.routing_key
        if self.exchange_type == "headers":
            arguments, routing_key = routing_key, ""

        if self.queue:
            self.backend.queue_declare(queue=self.queue, durable=self.durable,
                                       exclusive=self.exclusive,
                                       auto_delete=self.auto_delete,
                                       arguments=self.queue_arguments,
                                       warn_if_exists=self.warn_if_exists)
        if self.exchange:
            self.backend.exchange_declare(exchange=self.exchange,
                                          type=self.exchange_type,
                                          durable=self.durable,
                                          auto_delete=self.auto_delete)
        if self.queue:
            self.backend.queue_bind(queue=self.queue,
                                    exchange=self.exchange,
                                    routing_key=routing_key,
                                    arguments=arguments)
        self._closed = False
        return self

    def _receive_callback(self, raw_message):
        """Internal method used when a message is received in consume mode."""
        message = self.backend.message_to_python(raw_message)

        if self.auto_ack and not message.acknowledged:
            message.ack()
        self.receive(message.payload, message)

    def fetch(self, no_ack=None, auto_ack=None, enable_callbacks=False):
        """Receive the next message waiting on the queue.

        :returns: A :class:`carrot.backends.base.BaseMessage` instance,
            or ``None`` if there's no messages to be received.

        :keyword enable_callbacks: Enable callbacks. The message will be
            processed with all registered callbacks. Default is disabled.
        :keyword auto_ack: Override the default :attr:`auto_ack` setting.
        :keyword no_ack: Override the default :attr:`no_ack` setting.

        """
        no_ack = no_ack or self.no_ack
        auto_ack = auto_ack or self.auto_ack
        message = self.backend.get(self.queue, no_ack=no_ack)
        if message:
            if auto_ack and not message.acknowledged:
                message.ack()
            if enable_callbacks:
                self.receive(message.payload, message)
        return message

    def process_next(self):
        """**DEPRECATED** Use :meth:`fetch` like this instead:

            >>> message = self.fetch(enable_callbacks=True)

        """
        warnings.warn(DeprecationWarning(
            "Consumer.process_next has been deprecated in favor of \
            Consumer.fetch(enable_callbacks=True)"))
        return self.fetch(enable_callbacks=True)

    def receive(self, message_data, message):
        """This method is called when a new message is received by
        running :meth:`wait`, :meth:`process_next` or :meth:`iterqueue`.

        When a message is received, it passes the message on to the
        callbacks listed in the :attr:`callbacks` attribute.
        You can register callbacks using :meth:`register_callback`.

        :param message_data: The deserialized message data.

        :param message: The :class:`carrot.backends.base.BaseMessage` instance.

        :raises NotImplementedError: If no callbacks has been registered.

        """
        if not self.callbacks:
            raise NotImplementedError("No consumer callbacks registered")
        for callback in self.callbacks:
            callback(message_data, message)

    def register_callback(self, callback):
        """Register a callback function to be triggered by :meth:`receive`.

        The ``callback`` function must take two arguments:

            * message_data

                The deserialized message data

            * message

                The :class:`carrot.backends.base.BaseMessage` instance.
        """
        self.callbacks.append(callback)

    def purge(self):
        return self.backend.queue_purge(self.queue)

    def discard_all(self, filterfunc=None):
        """Discard all waiting messages.

        :param filterfunc: A filter function to only discard the messages this
            filter returns.

        :returns: the number of messages discarded.

        *WARNING*: All incoming messages will be ignored and not processed.

        Example using filter:

            >>> def waiting_feeds_only(message):
            ...     try:
            ...         message_data = message.decode()
            ...     except: # Should probably be more specific.
            ...         pass
            ...
            ...     if message_data.get("type") == "feed":
            ...         return True
            ...     else:
            ...         return False
        """
        if not filterfunc:
            return self.backend.queue_purge(self.queue)

        if self.no_ack or self.auto_ack:
            raise Exception("discard_all: Can't use filter with auto/no-ack.")

        discarded_count = 0
        while True:
            message = self.fetch()
            if message is None:
                return discarded_count

            if filterfunc(message):
                message.ack()
                discarded_count += 1

    def iterconsume(self, limit=None, no_ack=None):
        """Iterator processing new messages as they arrive.
        Every new message will be passed to the callbacks, and the iterator
        returns ``True``. The iterator is infinite unless the ``limit``
        argument is specified or someone closes the consumer.

        :meth:`iterconsume` uses transient requests for messages on the
        server, while :meth:`iterequeue` uses synchronous access. In most
        cases you want :meth:`iterconsume`, but if your environment does not
        support this behaviour you can resort to using :meth:`iterqueue`
        instead.

        Also, :meth:`iterconsume` does not return the message
        at each step, something which :meth:`iterqueue` does.

        :keyword limit: Maximum number of messages to process.

        :raises StopIteration: if limit is set and the message limit has been
            reached.

        """
        self.consume(no_ack=no_ack)
        return self.backend.consume(limit=limit)

    def consume(self, no_ack=None):
        """Declare consumer."""
        no_ack = no_ack or self.no_ack
        self.backend.declare_consumer(queue=self.queue, no_ack=no_ack,
                                      callback=self._receive_callback,
                                      consumer_tag=self.consumer_tag,
                                      nowait=True)
        self.channel_open = True

    def wait(self, limit=None):
        """Go into consume mode.

        Mostly for testing purposes and simple programs, you probably
        want :meth:`iterconsume` or :meth:`iterqueue` instead.

        This runs an infinite loop, processing all incoming messages
        using :meth:`receive` to apply the message to all registered
        callbacks.

        """
        it = self.iterconsume(limit)
        while True:
            it.next()

    def iterqueue(self, limit=None, infinite=False):
        """Infinite iterator yielding pending messages, by using
        synchronous direct access to the queue (``basic_get``).

        :meth:`iterqueue` is used where synchronous functionality is more
        important than performance. If you can, use :meth:`iterconsume`
        instead.

        :keyword limit: If set, the iterator stops when it has processed
            this number of messages in total.

        :keyword infinite: Don't raise :exc:`StopIteration` if there is no
            messages waiting, but return ``None`` instead. If infinite you
            obviously shouldn't consume the whole iterator at once without
            using a ``limit``.

        :raises StopIteration: If there is no messages waiting, and the
            iterator is not infinite.

        """
        for items_since_start in count():
            item = self.fetch()
            if (not infinite and item is None) or \
                    (limit and items_since_start >= limit):
                raise StopIteration
            yield item

    def cancel(self):
        """Cancel a running :meth:`iterconsume` session."""
        if self.channel_open:
            try:
                self.backend.cancel(self.consumer_tag)
            except KeyError:
                pass

    def close(self):
        """Close the channel to the queue."""
        self.cancel()
        self.backend.close()
        self._closed = True

    def flow(self, active):
        """This method asks the peer to pause or restart the flow of
        content data.

        This is a simple flow-control mechanism that a
        peer can use to avoid oveflowing its queues or otherwise
        finding itself receiving more messages than it can process.
        Note that this method is not intended for window control.  The
        peer that receives a request to stop sending content should
        finish sending the current content, if any, and then wait
        until it receives the ``flow(active=True)`` restart method.

        """
        self.backend.flow(active)

    def qos(self, prefetch_size=0, prefetch_count=0, apply_global=False):
        """Request specific Quality of Service.

        This method requests a specific quality of service.  The QoS
        can be specified for the current channel or for all channels
        on the connection.  The particular properties and semantics of
        a qos method always depend on the content class semantics.
        Though the qos method could in principle apply to both peers,
        it is currently meaningful only for the server.

        :param prefetch_size: Prefetch window in octets.
            The client can request that messages be sent in
            advance so that when the client finishes processing a
            message, the following message is already held
            locally, rather than needing to be sent down the
            channel.  Prefetching gives a performance improvement.
            This field specifies the prefetch window size in
            octets.  The server will send a message in advance if
            it is equal to or smaller in size than the available
            prefetch size (and also falls into other prefetch
            limits). May be set to zero, meaning "no specific
            limit", although other prefetch limits may still
            apply. The ``prefetch_size`` is ignored if the
            :attr:`no_ack` option is set.

        :param prefetch_count: Specifies a prefetch window in terms of whole
            messages. This field may be used in combination with
            ``prefetch_size``; A message will only be sent
            in advance if both prefetch windows (and those at the
            channel and connection level) allow it. The prefetch-
            count is ignored if the :attr:`no_ack` option is set.

        :keyword apply_global: By default the QoS settings apply to the
            current channel only. If this is set, they are applied
            to the entire connection.

        """
        return self.backend.qos(prefetch_size, prefetch_count, apply_global)


class Publisher(object):
    """Message publisher.

    :param connection: see :attr:`connection`.
    :param exchange: see :attr:`exchange`.
    :param routing_key: see :attr:`routing_key`.

    :keyword exchange_type: see :attr:`Consumer.exchange_type`.
    :keyword durable: see :attr:`Consumer.durable`.
    :keyword auto_delete: see :attr:`Consumer.auto_delete`.
    :keyword serializer: see :attr:`serializer`.
    :keyword auto_declare: See :attr:`auto_declare`.


    .. attribute:: connection

        The connection to the broker.
        A :class:`carrot.connection.BrokerConnection` instance.

    .. attribute:: exchange

        Name of the exchange we send messages to.

    .. attribute:: routing_key

        The default routing key for messages sent using this publisher.
        See :attr:`Consumer.routing_key` for more information.
        You can override the routing key by passing an explicit
        ``routing_key`` argument to :meth:`send`.

    .. attribute:: delivery_mode

        The default delivery mode used for messages. The value is an integer.
        The following delivery modes are supported by (at least) RabbitMQ:

            * 1 or "transient"

                The message is transient. Which means it is stored in
                memory only, and is lost if the server dies or restarts.

            * 2 or "persistent"
                The message is persistent. Which means the message is
                stored both in-memory, and on disk, and therefore
                preserved if the server dies or restarts.

        The default value is ``2`` (persistent).

    .. attribute:: exchange_type

        See :attr:`Consumer.exchange_type`.

    .. attribute:: durable

        See :attr:`Consumer.durable`.

    .. attribute:: auto_delete

        See :attr:`Consumer.auto_delete`.

    .. attribute:: auto_declare

        If this is ``True`` and the :attr:`exchange` name is set, the exchange
        will be automatically declared at instantiation.
        You can manually the declare the exchange by using the :meth:`declare`
        method.

        Auto declare is on by default.

    .. attribute:: serializer

        A string identifying the default serialization method to use.
        Defaults to ``json``. Can be ``json`` (default), ``raw``,
        ``pickle``, ``hessian``, ``yaml``, or any custom serialization
        methods that have been registered with
        :mod:`carrot.serialization.registry`.

    """

    NONE_PERSISTENT_DELIVERY_MODE = 1
    TRANSIENT_DELIVERY_MODE = 1
    PERSISTENT_DELIVERY_MODE = 2
    DELIVERY_MODES = {
            "transient": TRANSIENT_DELIVERY_MODE,
            "persistent": PERSISTENT_DELIVERY_MODE,
            "non-persistent": TRANSIENT_DELIVERY_MODE,
    }

    exchange = ""
    routing_key = ""
    delivery_mode = PERSISTENT_DELIVERY_MODE
    _closed = True
    exchange_type = "direct"
    durable = True
    auto_delete = False
    auto_declare = True
    serializer = None
    _init_opts = ("exchange_type", "durable", "auto_delete",
                  "serializer", "delivery_mode", "auto_declare")

    def __init__(self, connection, exchange=None, routing_key=None, **kwargs):
        self.connection = connection
        self.backend = self.connection.create_backend()
        self.exchange = exchange or self.exchange
        self.routing_key = routing_key or self.routing_key
        for opt_name in self._init_opts:
            opt_value = kwargs.get(opt_name)
            if opt_value is not None:
                setattr(self, opt_name, opt_value)
        self.delivery_mode = self.DELIVERY_MODES.get(self.delivery_mode,
                                                     self.delivery_mode)
        self._closed = False

        if self.auto_declare and self.exchange:
            self.declare()


    def declare(self):
        """Declare the exchange.

        Creates the exchange on the broker.

        """
        self.backend.exchange_declare(exchange=self.exchange,
                                      type=self.exchange_type,
                                      durable=self.durable,
                                      auto_delete=self.auto_delete)

    def __enter__(self):
        return self

    def __exit__(self, e_type, e_value, e_trace):
        self.close()

    def create_message(self, message_data, delivery_mode=None, priority=None,
                       content_type=None, content_encoding=None,
                       serializer=None):
        """With any data, serialize it and encapsulate it in a AMQP
        message with the proper headers set."""

        delivery_mode = delivery_mode or self.delivery_mode

        # No content_type? Then we're serializing the data internally.
        if not content_type:
            serializer = serializer or self.serializer
            (content_type, content_encoding,
             message_data) = serialization.encode(message_data,
                                                  serializer=serializer)
        else:
            # If the programmer doesn't want us to serialize,
            # make sure content_encoding is set.
            if isinstance(message_data, unicode):
                if not content_encoding:
                    content_encoding = 'utf-8'
                message_data = message_data.encode(content_encoding)

            # If they passed in a string, we can't know anything
            # about it.  So assume it's binary data.
            elif not content_encoding:
                content_encoding = 'binary'

        return self.backend.prepare_message(message_data, delivery_mode,
                                            priority=priority,
                                            content_type=content_type,
                                            content_encoding=content_encoding)

    def send(self, message_data, routing_key=None, delivery_mode=None,
            mandatory=False, immediate=False, priority=0, content_type=None,
            content_encoding=None, serializer=None, exchange=None):
        """Send a message.

        :param message_data: The message data to send. Can be a list,
            dictionary or a string.

        :keyword routing_key: A custom routing key for the message.
            If not set, the default routing key set in the :attr:`routing_key`
            attribute is used.

        :keyword mandatory: If set, the message has mandatory routing.
            By default the message is silently dropped by the server if it
            can't be routed to a queue. However - If the message is mandatory,
            an exception will be raised instead.

        :keyword immediate: Request immediate delivery.
            If the message cannot be routed to a queue consumer immediately,
            an exception will be raised. This is instead of the default
            behaviour, where the server will accept and queue the message,
            but with no guarantee that the message will ever be consumed.

        :keyword delivery_mode: Override the default :attr:`delivery_mode`.

        :keyword priority: The message priority, ``0`` to ``9``.

        :keyword content_type: The messages content_type. If content_type
            is set, no serialization occurs as it is assumed this is either
            a binary object, or you've done your own serialization.
            Leave blank if using built-in serialization as our library
            properly sets content_type.

        :keyword content_encoding: The character set in which this object
            is encoded. Use "binary" if sending in raw binary objects.
            Leave blank if using built-in serialization as our library
            properly sets content_encoding.

        :keyword serializer: Override the default :attr:`serializer`.

        :keyword exchange: Override the exchange to publish to.
            Note that this exchange must have been declared.

        """
        headers = None
        routing_key = routing_key or self.routing_key

        if self.exchange_type == "headers":
            headers, routing_key = routing_key, ""

        exchange = exchange or self.exchange

        message = self.create_message(message_data, priority=priority,
                                      delivery_mode=delivery_mode,
                                      content_type=content_type,
                                      content_encoding=content_encoding,
                                      serializer=serializer)
        self.backend.publish(message,
                             exchange=exchange, routing_key=routing_key,
                             mandatory=mandatory, immediate=immediate,
                             headers=headers)

    def close(self):
        """Close connection to queue."""
        self.backend.close()
        self._closed = True


class Messaging(object):
    """A combined message publisher and consumer."""
    queue = ""
    exchange = ""
    routing_key = ""
    publisher_cls = Publisher
    consumer_cls = Consumer
    _closed = True

    def __init__(self, connection, **kwargs):
        self.connection = connection
        self.exchange = kwargs.get("exchange", self.exchange)
        self.queue = kwargs.get("queue", self.queue)
        self.routing_key = kwargs.get("routing_key", self.routing_key)
        self.publisher = self.publisher_cls(connection,
                exchange=self.exchange, routing_key=self.routing_key)
        self.consumer = self.consumer_cls(connection, queue=self.queue,
                exchange=self.exchange, routing_key=self.routing_key)
        self.consumer.register_callback(self.receive)
        self.callbacks = []
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, e_type, e_value, e_trace):
        if e_type:
            raise e_type(e_value)
        self.close()

    def register_callback(self, callback):
        """See :meth:`Consumer.register_callback`"""
        self.callbacks.append(callback)

    def receive(self, message_data, message):
        """See :meth:`Consumer.receive`"""
        if not self.callbacks:
            raise NotImplementedError("No consumer callbacks registered")
        for callback in self.callbacks:
            callback(message_data, message)

    def send(self, message_data, delivery_mode=None):
        """See :meth:`Publisher.send`"""
        self.publisher.send(message_data, delivery_mode=delivery_mode)

    def fetch(self, **kwargs):
        """See :meth:`Consumer.fetch`"""
        return self.consumer.fetch(**kwargs)

    def close(self):
        """Close any open channels."""
        self.consumer.close()
        self.publisher.close()
        self._closed = True


class ConsumerSet(object):
    """Receive messages from multiple consumers.

    :param connection: see :attr:`connection`.
    :param from_dict: see :attr:`from_dict`.
    :param consumers: see :attr:`consumers`.
    :param callbacks: see :attr:`callbacks`.
    :param on_decode_error: see :attr:`on_decode_error`.

    .. attribute:: connection

        The connection to the broker.
        A :class:`carrot.connection.BrokerConnection` instance.

    .. attribute:: callbacks

        A list of callbacks to be called when a message is received.
        See :class:`Consumer.register_callback`.

    .. attribute:: from_dict

        Add consumers from a dictionary configuration::

            {
                "webshot": {
                            "exchange": "link_exchange",
                            "exchange_type": "topic",
                            "binding_key": "links.webshot",
                            "default_routing_key": "links.webshot",
                    },
                "retrieve": {
                            "exchange": "link_exchange",
                            "exchange_type" = "topic",
                            "binding_key": "links.*",
                            "default_routing_key": "links.retrieve",
                            "auto_delete": True,
                            # ...
                    },
            }

    .. attribute:: consumers

        Add consumers from a list of :class:`Consumer` instances.

    .. attribute:: auto_ack

        Default value for the :attr:`Consumer.auto_ack` attribute.

    .. attribute:: on_decode_error

        Callback called if an error occurs while decoding a message.
        The callback is called with the following signature::

            callback(message, exception)

    """
    auto_ack = False
    on_decode_error = None

    def __init__(self, connection, from_dict=None, consumers=None,
            callbacks=None, **options):
        self.connection = connection
        self.options = options
        self.from_dict = from_dict or {}
        self.consumers = []
        self.callbacks = callbacks or []
        self._open_consumers = {}

        self.backend = self.connection.create_backend()

        self.auto_ack = options.get("auto_ack", self.auto_ack)

        if consumers:
            [self.add_consumer(consumer) for consumer in consumers]

        [self.add_consumer_from_dict(queue_name, **queue_options)
                for queue_name, queue_options in self.from_dict.items()]

    def _receive_callback(self, raw_message):
        """Internal method used when a message is received in consume mode."""
        message = self.backend.message_to_python(raw_message)
        if self.auto_ack and not message.acknowledged:
            message.ack()
        try:
            decoded = message.decode()
        except Exception, exc:
            if not self.on_decode_error:
                raise
            self.on_decode_error(message, exc)
        else:
            self.receive(decoded, message)

    def add_consumer_from_dict(self, queue, **options):
        """Add another consumer from dictionary configuration."""
        options.setdefault("routing_key", options.pop("binding_key", None))
        consumer = Consumer(self.connection, queue=queue,
                            backend=self.backend, **options)
        self.consumers.append(consumer)
        return consumer

    def add_consumer(self, consumer):
        """Add another consumer from a :class:`Consumer` instance."""
        consumer.backend = self.backend
        self.consumers.append(consumer)

    def register_callback(self, callback):
        """Register new callback to be called when a message is received.
        See :meth:`Consumer.register_callback`"""
        self.callbacks.append(callback)

    def receive(self, message_data, message):
        """What to do when a message is received.
        See :meth:`Consumer.receive`."""
        if not self.callbacks:
            raise NotImplementedError("No consumer callbacks registered")
        for callback in self.callbacks:
            callback(message_data, message)

    def _declare_consumer(self, consumer, nowait=False):
        """Declare consumer so messages can be received from it using
        :meth:`iterconsume`."""
        if consumer.queue not in self._open_consumers:
            # Use the ConsumerSet's consumer by default, but if the
            # child consumer has a callback, honor it.
            callback = consumer.callbacks and \
                consumer._receive_callback or self._receive_callback
            self.backend.declare_consumer(queue=consumer.queue,
                                          no_ack=consumer.no_ack,
                                          nowait=nowait,
                                          callback=callback,
                                          consumer_tag=consumer.consumer_tag)
            self._open_consumers[consumer.queue] = consumer.consumer_tag

    def consume(self):
        """Declare consumers."""
        head = self.consumers[:-1]
        tail = self.consumers[-1]
        [self._declare_consumer(consumer, nowait=True)
                for consumer in head]
        self._declare_consumer(tail, nowait=False)

    def iterconsume(self, limit=None):
        """Cycle between all consumers in consume mode.

        See :meth:`Consumer.iterconsume`.
        """
        self.consume()
        return self.backend.consume(limit=limit)

    def discard_all(self):
        """Discard all messages. Does not support filtering.
        See :meth:`Consumer.discard_all`."""
        return sum([consumer.discard_all()
                        for consumer in self.consumers])

    def flow(self, active):
        """This method asks the peer to pause or restart the flow of
        content data.

        See :meth:`Consumer.flow`.

        """
        self.backend.flow(active)

    def qos(self, prefetch_size=0, prefetch_count=0, apply_global=False):
        """Request specific Quality of Service.

        See :meth:`Consumer.cos`.

        """
        self.backend.qos(prefetch_size, prefetch_count, apply_global)

    def cancel(self):
        """Cancel a running :meth:`iterconsume` session."""
        for consumer_tag in self._open_consumers.values():
            try:
                self.backend.cancel(consumer_tag)
            except KeyError:
                pass
        self._open_consumers.clear()

    def cancel_by_queue(self, queue):
        consumer_tag = self._open_consumers.pop(queue)
        self.backend.cancel(consumer_tag)

    def close(self):
        """Close all consumers."""
        self.cancel()
        for consumer in self.consumers:
            consumer.close()

########NEW FILE########
__FILENAME__ = serialization
"""
Centralized support for encoding/decoding of data structures.
Requires a json library (`cjson`_, `simplejson`_, or `Python 2.6+`_).

Pickle support is built-in.

Optionally installs support for ``YAML`` if the `PyYAML`_ package
is installed.

Optionally installs support for `msgpack`_ if the `msgpack-python`_
package is installed.

.. _`cjson`: http://pypi.python.org/pypi/python-cjson/
.. _`simplejson`: http://code.google.com/p/simplejson/
.. _`Python 2.6+`: http://docs.python.org/library/json.html
.. _`PyYAML`: http://pyyaml.org/
.. _`msgpack`: http://msgpack.sourceforge.net/
.. _`msgpack-python`: http://pypi.python.org/pypi/msgpack-python/

"""

import codecs

__all__ = ['SerializerNotInstalled', 'registry']


class SerializerNotInstalled(StandardError):
    """Support for the requested serialization type is not installed"""


class SerializerRegistry(object):
    """The registry keeps track of serialization methods."""

    def __init__(self):
        self._encoders = {}
        self._decoders = {}
        self._default_encode = None
        self._default_content_type = None
        self._default_content_encoding = None

    def register(self, name, encoder, decoder, content_type,
                 content_encoding='utf-8'):
        """Register a new encoder/decoder.

        :param name: A convenience name for the serialization method.

        :param encoder: A method that will be passed a python data structure
            and should return a string representing the serialized data.
            If ``None``, then only a decoder will be registered. Encoding
            will not be possible.

        :param decoder: A method that will be passed a string representing
            serialized data and should return a python data structure.
            If ``None``, then only an encoder will be registered.
            Decoding will not be possible.

        :param content_type: The mime-type describing the serialized
            structure.

        :param content_encoding: The content encoding (character set) that
            the :param:`decoder` method will be returning. Will usually be
            ``utf-8``, ``us-ascii``, or ``binary``.

        """
        if encoder:
            self._encoders[name] = (content_type, content_encoding, encoder)
        if decoder:
            self._decoders[content_type] = decoder

    def _set_default_serializer(self, name):
        """
        Set the default serialization method used by this library.

        :param name: The name of the registered serialization method.
            For example, ``json`` (default), ``pickle``, ``yaml``,
            or any custom methods registered using :meth:`register`.

        :raises SerializerNotInstalled: If the serialization method
            requested is not available.
        """
        try:
            (self._default_content_type, self._default_content_encoding,
             self._default_encode) = self._encoders[name]
        except KeyError:
            raise SerializerNotInstalled(
                "No encoder installed for %s" % name)

    def encode(self, data, serializer=None):
        """
        Serialize a data structure into a string suitable for sending
        as an AMQP message body.

        :param data: The message data to send. Can be a list,
            dictionary or a string.

        :keyword serializer: An optional string representing
            the serialization method you want the data marshalled
            into. (For example, ``json``, ``raw``, or ``pickle``).

            If ``None`` (default), then `JSON`_ will be used, unless
            ``data`` is a ``str`` or ``unicode`` object. In this
            latter case, no serialization occurs as it would be
            unnecessary.

            Note that if ``serializer`` is specified, then that
            serialization method will be used even if a ``str``
            or ``unicode`` object is passed in.

        :returns: A three-item tuple containing the content type
            (e.g., ``application/json``), content encoding, (e.g.,
            ``utf-8``) and a string containing the serialized
            data.

        :raises SerializerNotInstalled: If the serialization method
              requested is not available.
        """
        if serializer == "raw":
            return raw_encode(data)
        if serializer and not self._encoders.get(serializer):
            raise SerializerNotInstalled(
                        "No encoder installed for %s" % serializer)

        # If a raw string was sent, assume binary encoding
        # (it's likely either ASCII or a raw binary file, but 'binary'
        # charset will encompass both, even if not ideal.
        if not serializer and isinstance(data, str):
            # In Python 3+, this would be "bytes"; allow binary data to be
            # sent as a message without getting encoder errors
            return "application/data", "binary", data

        # For unicode objects, force it into a string
        if not serializer and isinstance(data, unicode):
            payload = data.encode("utf-8")
            return "text/plain", "utf-8", payload

        if serializer:
            content_type, content_encoding, encoder = \
                    self._encoders[serializer]
        else:
            encoder = self._default_encode
            content_type = self._default_content_type
            content_encoding = self._default_content_encoding

        payload = encoder(data)
        return content_type, content_encoding, payload

    def decode(self, data, content_type, content_encoding):
        """Deserialize a data stream as serialized using ``encode``
        based on :param:`content_type`.

        :param data: The message data to deserialize.

        :param content_type: The content-type of the data.
            (e.g., ``application/json``).

        :param content_encoding: The content-encoding of the data.
            (e.g., ``utf-8``, ``binary``, or ``us-ascii``).

        :returns: The unserialized data.
        """
        content_type = content_type or 'application/data'
        content_encoding = (content_encoding or 'utf-8').lower()

        # Don't decode 8-bit strings or unicode objects
        if content_encoding not in ('binary', 'ascii-8bit') and \
                not isinstance(data, unicode):
            data = codecs.decode(data, content_encoding)

        try:
            decoder = self._decoders[content_type]
        except KeyError:
            return data

        return decoder(data)


"""
.. data:: registry

Global registry of serializers/deserializers.

"""
registry = SerializerRegistry()

"""
.. function:: encode(data, serializer=default_serializer)

Encode data using the registry's default encoder.

"""
encode = registry.encode

"""
.. function:: decode(data, content_type, content_encoding):

Decode data using the registry's default decoder.

"""
decode = registry.decode


def raw_encode(data):
    """Special case serializer."""
    content_type = 'application/data'
    payload = data
    if isinstance(payload, unicode):
        content_encoding = 'utf-8'
        payload = payload.encode(content_encoding)
    else:
        content_encoding = 'binary'
    return content_type, content_encoding, payload


def register_json():
    """Register a encoder/decoder for JSON serialization."""
    from anyjson import serialize as json_serialize
    from anyjson import deserialize as json_deserialize

    registry.register('json', json_serialize, json_deserialize,
                      content_type='application/json',
                      content_encoding='utf-8')


def register_yaml():
    """Register a encoder/decoder for YAML serialization.

    It is slower than JSON, but allows for more data types
    to be serialized. Useful if you need to send data such as dates"""
    try:
        import yaml
        registry.register('yaml', yaml.safe_dump, yaml.safe_load,
                          content_type='application/x-yaml',
                          content_encoding='utf-8')
    except ImportError:

        def not_available(*args, **kwargs):
            """In case a client receives a yaml message, but yaml
            isn't installed."""
            raise SerializerNotInstalled(
                "No decoder installed for YAML. Install the PyYAML library")
        registry.register('yaml', None, not_available, 'application/x-yaml')


def register_pickle():
    """The fastest serialization method, but restricts
    you to python clients."""
    import cPickle
    registry.register('pickle', cPickle.dumps, cPickle.loads,
                      content_type='application/x-python-serialize',
                      content_encoding='binary')


def register_msgpack():
    """See http://msgpack.sourceforge.net/"""
    try:
        import msgpack
        registry.register('msgpack', msgpack.packs, msgpack.unpacks,
                content_type='application/x-msgpack',
                content_encoding='binary')
    except ImportError:

        def not_available(*args, **kwargs):
            """In case a client receives a msgpack message, but yaml
            isn't installed."""
            raise SerializerNotInstalled(
                    "No decoder installed for msgpack. "
                    "Install the msgpack library")
        registry.register('msgpack', None, not_available,
                          'application/x-msgpack')

# Register the base serialization methods.
register_json()
register_pickle()
register_yaml()
register_msgpack()

# JSON is assumed to always be available, so is the default.
# (this matches the historical use of carrot.)
registry._set_default_serializer('json')

########NEW FILE########
__FILENAME__ = utils
from uuid import UUID, uuid4, _uuid_generate_random
try:
    import ctypes
except ImportError:
    ctypes = None


def gen_unique_id():
    """Generate a unique id, having - hopefully - a very small chance of
    collission.

    For now this is provided by :func:`uuid.uuid4`.
    """
    # Workaround for http://bugs.python.org/issue4607
    if ctypes and _uuid_generate_random:
        buffer = ctypes.create_string_buffer(16)
        _uuid_generate_random(buffer)
        return str(UUID(bytes=buffer.raw))
    return str(uuid4())


def _compat_rl_partition(S, sep, direction=None):
    if direction is None:
        direction = S.split
    items = direction(sep, 1)
    if len(items) == 1:
        return items[0], sep, ''
    return items[0], sep, items[1]


def _compat_partition(S, sep):
    """``partition(S, sep) -> (head, sep, tail)``

    Search for the separator ``sep`` in ``S``, and return the part before
    it, the separator itself, and the part after it. If the separator is not
    found, return ``S`` and two empty strings.

    """
    return _compat_rl_partition(S, sep, direction=S.split)


def _compat_rpartition(S, sep):
    """``rpartition(S, sep) -> (tail, sep, head)``

    Search for the separator ``sep`` in ``S``, starting at the end of ``S``,
    and return the part before it, the separator itself, and the part
    after it. If the separator is not found, return two empty
    strings and ``S``.

    """
    return _compat_rl_partition(S, sep, direction=S.rsplit)



def partition(S, sep):
    if hasattr(S, 'partition'):
        return S.partition(sep)
    else:  # Python <= 2.4:
        return _compat_partition(S, sep)


def rpartition(S, sep):
    if hasattr(S, 'rpartition'):
        return S.rpartition(sep)
    else:  # Python <= 2.4:
        return _compat_rpartition(S, sep)


def repeatlast(it):
    """Iterate over all elements in the iterator, and when its exhausted
    yield the last value infinitely."""
    for item in it:
        yield item
    while 1: # pragma: no cover
        yield item


def retry_over_time(fun, catch, args=[], kwargs={}, errback=None,
        max_retries=None, interval_start=2, interval_step=2, interval_max=30):
    """Retry the function over and over until max retries is exceeded.

    For each retry we sleep a for a while before we try again, this interval
    is increased for every retry until the max seconds is reached.

    :param fun: The function to try
    :param catch: Exceptions to catch, can be either tuple or a single
        exception class.
    :keyword args: Positional arguments passed on to the function.
    :keyword kwargs: Keyword arguments passed on to the function.
    :keyword errback: Callback for when an exception in ``catch`` is raised.
        The callback must take two arguments: ``exc`` and ``interval``, where
        ``exc`` is the exception instance, and ``interval`` is the time in
        seconds to sleep next..
    :keyword max_retries: Maximum number of retries before we give up.
        If this is not set, we will retry forever.
    :keyword interval_start: How long (in seconds) we start sleeping between
        retries.
    :keyword interval_step: By how much the interval is increased for each
        retry.
    :keyword interval_max: Maximum number of seconds to sleep between retries.

    """
    retries = 0
    interval_range = xrange(interval_start,
                            interval_max + interval_start,
                            interval_step)

    for retries, interval in enumerate(repeatlast(interval_range)):
        try:
            retval = fun(*args, **kwargs)
        except catch, exc:
            if max_retries and retries > max_retries:
                raise
            if errback:
                errback(exc, interval)
            sleep(interval)
        else:
            return retval

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Carrot documentation build configuration file, created by
# sphinx-quickstart on Mon May 18 21:37:44 2009.
#
# This file is execfile()d with the current directory set to its
#containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed
#automatically).
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
sys.path.insert(0, "../")
import carrot


# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings.
# They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Carrot'
copyright = u'2009, Ask Solem'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ".".join(map(str, carrot.VERSION[0:2]))
# The full version, including alpha/beta/rc tags.
release = carrot.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['.build']

# The reST default role (used for this markup: `text`) to use for all
# documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'trac'

#html_translator_class = "djangodocs.DjangoHTMLTranslator"


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
#html_style = 'agogo.css'

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
html_static_path = ['.static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
html_use_modindex = True

# If false, no index is generated.
html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Carrotdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class
# [howto/manual]).
latex_documents = [
  ('index', 'Carrot.tex', ur'Carrot Documentation',
   ur'Ask Solem', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

html_theme = "nature"
html_theme_path = ["_theme"]

########NEW FILE########
__FILENAME__ = applyxrefs
"""Adds xref targets to the top of files."""

import sys
import os

testing = False

DONT_TOUCH = (
        './index.txt',
        )


def target_name(fn):
    if fn.endswith('.txt'):
        fn = fn[:-4]
    return '_' + fn.lstrip('./').replace('/', '-')


def process_file(fn, lines):
    lines.insert(0, '\n')
    lines.insert(0, '.. %s:\n' % target_name(fn))
    try:
        f = open(fn, 'w')
    except IOError:
        print("Can't open %s for writing. Not touching it." % fn)
        return
    try:
        f.writelines(lines)
    except IOError:
        print("Can't write to %s. Not touching it." % fn)
    finally:
        f.close()


def has_target(fn):
    try:
        f = open(fn, 'r')
    except IOError:
        print("Can't open %s. Not touching it." % fn)
        return (True, None)
    readok = True
    try:
        lines = f.readlines()
    except IOError:
        print("Can't read %s. Not touching it." % fn)
        readok = False
    finally:
        f.close()
        if not readok:
            return (True, None)

    #print fn, len(lines)
    if len(lines) < 1:
        print("Not touching empty file %s." % fn)
        return (True, None)
    if lines[0].startswith('.. _'):
        return (True, None)
    return (False, lines)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    if len(argv) == 1:
        argv.extend('.')

    files = []
    for root in argv[1:]:
        for (dirpath, dirnames, filenames) in os.walk(root):
            files.extend([(dirpath, f) for f in filenames])
    files.sort()
    files = [os.path.join(p, fn) for p, fn in files if fn.endswith('.txt')]
    #print files

    for fn in files:
        if fn in DONT_TOUCH:
            print("Skipping blacklisted file %s." % fn)
            continue

        target_found, lines = has_target(fn)
        if not target_found:
            if testing:
                print '%s: %s' % (fn, lines[0]),
            else:
                print "Adding xref to %s" % fn
                process_file(fn, lines)
        else:
            print "Skipping %s: already has a xref" % fn

if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = literals_to_xrefs
"""
Runs through a reST file looking for old-style literals, and helps replace them
with new-style references.
"""

import re
import sys
import shelve

refre = re.compile(r'``([^`\s]+?)``')

ROLES = (
    'attr',
    'class',
    "djadmin",
    'data',
    'exc',
    'file',
    'func',
    'lookup',
    'meth',
    'mod',
    "djadminopt",
    "ref",
    "setting",
    "term",
    "tfilter",
    "ttag",

    # special
    "skip",
)

ALWAYS_SKIP = [
    "NULL",
    "True",
    "False",
]


def fixliterals(fname):
    data = open(fname).read()

    last = 0
    new = []
    storage = shelve.open("/tmp/literals_to_xref.shelve")
    lastvalues = storage.get("lastvalues", {})

    for m in refre.finditer(data):

        new.append(data[last:m.start()])
        last = m.end()

        line_start = data.rfind("\n", 0, m.start())
        line_end = data.find("\n", m.end())
        prev_start = data.rfind("\n", 0, line_start)
        next_end = data.find("\n", line_end + 1)

        # Skip always-skip stuff
        if m.group(1) in ALWAYS_SKIP:
            new.append(m.group(0))
            continue

        # skip when the next line is a title
        next_line = data[m.end():next_end].strip()
        if next_line[0] in "!-/:-@[-`{-~" and \
                all(c == next_line[0] for c in next_line):
            new.append(m.group(0))
            continue

        sys.stdout.write("\n"+"-"*80+"\n")
        sys.stdout.write(data[prev_start+1:m.start()])
        sys.stdout.write(colorize(m.group(0), fg="red"))
        sys.stdout.write(data[m.end():next_end])
        sys.stdout.write("\n\n")

        replace_type = None
        while replace_type is None:
            replace_type = raw_input(
                colorize("Replace role: ", fg="yellow")).strip().lower()
            if replace_type and replace_type not in ROLES:
                replace_type = None

        if replace_type == "":
            new.append(m.group(0))
            continue

        if replace_type == "skip":
            new.append(m.group(0))
            ALWAYS_SKIP.append(m.group(1))
            continue

        default = lastvalues.get(m.group(1), m.group(1))
        if default.endswith("()") and \
                replace_type in ("class", "func", "meth"):
            default = default[:-2]
        replace_value = raw_input(
            colorize("Text <target> [", fg="yellow") + default + \
                    colorize("]: ", fg="yellow")).strip()
        if not replace_value:
            replace_value = default
        new.append(":%s:`%s`" % (replace_type, replace_value))
        lastvalues[m.group(1)] = replace_value

    new.append(data[last:])
    open(fname, "w").write("".join(new))

    storage["lastvalues"] = lastvalues
    storage.close()


def colorize(text='', opts=(), **kwargs):
    """
    Returns your text, enclosed in ANSI graphics codes.

    Depends on the keyword arguments 'fg' and 'bg', and the contents of
    the opts tuple/list.

    Returns the RESET code if no parameters are given.

    Valid colors:
        'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'

    Valid options:
        'bold'
        'underscore'
        'blink'
        'reverse'
        'conceal'
        'noreset' - string will not be auto-terminated with the RESET code

    Examples:
        colorize('hello', fg='red', bg='blue', opts=('blink',))
        colorize()
        colorize('goodbye', opts=('underscore',))
        print colorize('first line', fg='red', opts=('noreset',))
        print 'this should be red too'
        print colorize('and so should this')
        print 'this should not be red'
    """
    color_names = ('black', 'red', 'green', 'yellow',
                   'blue', 'magenta', 'cyan', 'white')
    foreground = dict([(color_names[x], '3%s' % x) for x in range(8)])
    background = dict([(color_names[x], '4%s' % x) for x in range(8)])

    RESET = '0'
    opt_dict = {'bold': '1',
                'underscore': '4',
                'blink': '5',
                'reverse': '7',
                'conceal': '8'}

    text = str(text)
    code_list = []
    if text == '' and len(opts) == 1 and opts[0] == 'reset':
        return '\x1b[%sm' % RESET
    for k, v in kwargs.iteritems():
        if k == 'fg':
            code_list.append(foreground[v])
        elif k == 'bg':
            code_list.append(background[v])
    for o in opts:
        if o in opt_dict:
            code_list.append(opt_dict[o])
    if 'noreset' not in opts:
        text = text + '\x1b[%sm' % RESET
    return ('\x1b[%sm' % ';'.join(code_list)) + text

if __name__ == '__main__':
    try:
        fixliterals(sys.argv[1])
    except (KeyboardInterrupt, SystemExit):
        print

########NEW FILE########
__FILENAME__ = backend
import os
import sys
import unittest
import pickle
import time

from itertools import count

sys.path.insert(0, os.pardir)
sys.path.append(os.getcwd())

from carrot.messaging import Consumer, Publisher, ConsumerSet
from carrot import serialization
from tests.utils import establish_test_connection


class AdvancedDataType(object):

    def __init__(self, something):
        self.data = something


def fetch_next_message(consumer):
    while True:
        message = consumer.fetch()
        if message:
            return message


class BackendMessagingCase(unittest.TestCase):
    nextq = count(1).next

    def setUp(self):
        self.conn = establish_test_connection()
        self.queue = TEST_QUEUE
        self.exchange = TEST_EXCHANGE
        self.routing_key = TEST_ROUTING_KEY

    def create_consumer(self, **options):
        queue = "%s%s" % (self.queue, self.nextq())
        return Consumer(connection=self.conn,
                        queue=queue, exchange=self.exchange,
                        routing_key=self.routing_key, **options)

    def create_consumerset(self, queues={}, consumers=[], **options):
        return ConsumerSet(connection=self.conn,
                           from_dict=queues, consumers=consumers, **options)

    def create_publisher(self, exchange=None, routing_key=None, **options):
        exchange = exchange or self.exchange
        routing_key = routing_key or self.routing_key
        return Publisher(connection=self.conn,
                        exchange=exchange, routing_key=routing_key,
                        **options)

    def test_regression_implied_auto_delete(self):
        consumer = self.create_consumer(exclusive=True, auto_declare=False)
        self.assertTrue(consumer.auto_delete, "exclusive implies auto_delete")
        consumer.close()

        consumer = self.create_consumer(durable=True, auto_delete=False,
                                        auto_declare=False)
        self.assertFalse(consumer.auto_delete,
            """durable does *not* imply auto_delete.
            regression: http://github.com/ask/carrot/issues/closed#issue/2""")
        consumer.close()

    def test_consumer_options(self):
        opposite_defaults = {
                "queue": "xyxyxyxy",
                "exchange": "xyxyxyxy",
                "routing_key": "xyxyxyxy",
                "durable": False,
                "exclusive": True,
                "auto_delete": True,
                "exchange_type": "topic",
        }
        consumer = Consumer(connection=self.conn, **opposite_defaults)
        for opt_name, opt_value in opposite_defaults.items():
            self.assertEquals(getattr(consumer, opt_name), opt_value)
        consumer.close()

    def test_consumer_backend(self):
        consumer = self.create_consumer()
        self.assertTrue(consumer.backend.connection is self.conn)
        consumer.close()

    def test_consumer_queue_declared(self):
        consumer = self.create_consumer()
        self.assertTrue(consumer.backend.queue_exists(consumer.queue))
        consumer.close()

    def test_consumer_callbacks(self):
        consumer = self.create_consumer()
        publisher = self.create_publisher()

        # raises on no callbacks
        self.assertRaises(NotImplementedError, consumer.receive, {}, {})

        callback1_scratchpad = {}

        def callback1(message_data, message):
            callback1_scratchpad["message_data"] = message_data

        callback2_scratchpad = {}

        def callback2(message_data, message):
            callback2_scratchpad.update({"delivery_tag": message.delivery_tag,
                                         "message_body": message.body})

        self.assertFalse(consumer.callbacks, "no default callbacks")
        consumer.register_callback(callback1)
        consumer.register_callback(callback2)
        self.assertEquals(len(consumer.callbacks), 2, "callbacks registered")

        self.assertTrue(consumer.callbacks[0] is callback1,
                "callbacks are ordered")
        self.assertTrue(consumer.callbacks[1] is callback2,
                "callbacks are ordered")

        body = {"foo": "bar"}

        message = self.create_raw_message(publisher, body, "Elaine was here")
        consumer._receive_callback(message)

        self.assertEquals(callback1_scratchpad.get("message_data"), body,
                "callback1 was called")
        self.assertEquals(callback2_scratchpad.get("delivery_tag"),
                "Elaine was here")

        consumer.close()
        publisher.close()

    def create_raw_message(self, publisher, body, delivery_tag):
        raw_message = publisher.create_message(body)
        raw_message.delivery_tag = delivery_tag
        return raw_message

    def test_empty_queue_returns_None(self):
        consumer = self.create_consumer()
        consumer.discard_all()
        self.assertFalse(consumer.fetch())
        consumer.close()

    def test_custom_serialization_scheme(self):
        serialization.registry.register('custom_test',
                pickle.dumps, pickle.loads,
                content_type='application/x-custom-test',
                content_encoding='binary')

        consumer = self.create_consumer()
        publisher = self.create_publisher()
        consumer.discard_all()

        data = {"string": "The quick brown fox jumps over the lazy dog",
                "int": 10,
                "float": 3.14159265,
                "unicode": u"The quick brown fox jumps over the lazy dog",
                "advanced": AdvancedDataType("something"),
                "set": set(["george", "jerry", "elaine", "cosmo"]),
                "exception": Exception("There was an error"),
        }

        publisher.send(data, serializer='custom_test')
        message = fetch_next_message(consumer)
        backend = self.conn.create_backend()
        self.assertTrue(isinstance(message, backend.Message))
        self.assertEquals(message.payload.get("int"), 10)
        self.assertEquals(message.content_type, 'application/x-custom-test')
        self.assertEquals(message.content_encoding, 'binary')

        decoded_data = message.decode()

        self.assertEquals(decoded_data.get("string"),
                "The quick brown fox jumps over the lazy dog")
        self.assertEquals(decoded_data.get("int"), 10)
        self.assertEquals(decoded_data.get("float"), 3.14159265)
        self.assertEquals(decoded_data.get("unicode"),
                u"The quick brown fox jumps over the lazy dog")
        self.assertEquals(decoded_data.get("set"),
            set(["george", "jerry", "elaine", "cosmo"]))
        self.assertTrue(isinstance(decoded_data.get("exception"), Exception))
        self.assertEquals(decoded_data.get("exception").args[0],
            "There was an error")
        self.assertTrue(isinstance(decoded_data.get("advanced"),
            AdvancedDataType))
        self.assertEquals(decoded_data["advanced"].data, "something")

        consumer.close()
        publisher.close()

    def test_consumer_fetch(self):
        consumer = self.create_consumer()
        publisher = self.create_publisher()
        consumer.discard_all()

        data = {"string": "The quick brown fox jumps over the lazy dog",
                "int": 10,
                "float": 3.14159265,
                "unicode": u"The quick brown fox jumps over the lazy dog",
        }

        publisher.send(data)
        message = fetch_next_message(consumer)
        backend = self.conn.create_backend()
        self.assertTrue(isinstance(message, backend.Message))

        self.assertEquals(message.decode(), data)

        consumer.close()
        publisher.close()

    def test_consumer_process_next(self):
        consumer = self.create_consumer()
        publisher = self.create_publisher()
        consumer.discard_all()

        scratchpad = {}

        def callback(message_data, message):
            scratchpad["delivery_tag"] = message.delivery_tag
        consumer.register_callback(callback)

        publisher.send({"name_discovered": {
                            "first_name": "Cosmo",
                            "last_name": "Kramer"}})

        while True:
            message = consumer.fetch(enable_callbacks=True)
            if message:
                break

        self.assertEquals(scratchpad.get("delivery_tag"),
                message.delivery_tag)

        consumer.close()
        publisher.close()

    def test_consumer_discard_all(self):
        consumer = self.create_consumer()
        publisher = self.create_publisher()
        consumer.discard_all()

        for i in xrange(100):
            publisher.send({"foo": "bar"})
        time.sleep(0.5)

        self.assertEquals(consumer.discard_all(), 100)

        consumer.close()
        publisher.close()

    def test_iterqueue(self):
        consumer = self.create_consumer()
        publisher = self.create_publisher()
        num = consumer.discard_all()

        it = consumer.iterqueue(limit=100)
        consumer.register_callback(lambda *args: args)

        for i in xrange(100):
            publisher.send({"foo%d" % i: "bar%d" % i})
        time.sleep(0.5)

        for i in xrange(100):
            try:
                message = it.next()
                data = message.decode()
                self.assertTrue("foo%d" % i in data, "foo%d not in data" % i)
                self.assertEquals(data.get("foo%d" % i), "bar%d" % i)
            except StopIteration:
                self.assertTrue(False, "iterqueue fails StopIteration")

        self.assertRaises(StopIteration, it.next)

        # no messages on queue raises StopIteration if infinite=False
        it = consumer.iterqueue()
        self.assertRaises(StopIteration, it.next)

        it = consumer.iterqueue(infinite=True)
        self.assertTrue(it.next() is None,
                "returns None if no messages and inifite=True")

        consumer.close()
        publisher.close()

    def test_publisher_message_priority(self):
        consumer = self.create_consumer()
        publisher = self.create_publisher()
        consumer.discard_all()

        m = publisher.create_message("foo", priority=9)

        publisher.send({"foo": "bar"}, routing_key="nowhere", priority=9,
                mandatory=False, immediate=False)

        consumer.discard_all()

        consumer.close()
        publisher.close()

    def test_backend_survives_channel_close_regr17(self):
        """
        test that a backend instance is still functional after
        a method that results in a channel closure.
        """
        backend = self.create_publisher().backend
        assert not backend.queue_exists('notaqueue')
        # after calling this once, the channel seems to close, but the
        # backend may be holding a reference to it...
        assert not backend.queue_exists('notaqueue')

    def disabled_publisher_mandatory_flag_regr16(self):
        """
        Test that the publisher "mandatory" flag
        raises exceptions at appropriate times.
        """
        routing_key = 'black_hole'

        assert self.conn.connection is not None

        message = {'foo': 'mandatory'}

        # sanity check cleanup from last test
        assert not self.create_consumer().backend.queue_exists(routing_key)

        publisher = self.create_publisher()

        # this should just get discarded silently, it's not mandatory
        publisher.send(message, routing_key=routing_key, mandatory=False)

        # This raises an unspecified exception because there is no queue to
        # deliver to
        self.assertRaises(Exception, publisher.send, message,
                          routing_key=routing_key, mandatory=True)

        # now bind a queue to it
        consumer = Consumer(connection=self.conn,
                            queue=routing_key, exchange=self.exchange,
                            routing_key=routing_key, durable=False,
                            exclusive=True)

        # check that it exists
        assert self.create_consumer().backend.queue_exists(routing_key)

        # this should now get routed to our consumer with no exception
        publisher.send(message, routing_key=routing_key, mandatory=True)

    def test_consumer_auto_ack(self):
        consumer = self.create_consumer(auto_ack=True)
        publisher = self.create_publisher()
        consumer.discard_all()

        publisher.send({"foo": "Baz"})
        message = fetch_next_message(consumer)
        self.assertEquals(message._state, "ACK")
        consumer.close()
        publisher.close()

        publisher = self.create_publisher()
        consumer = self.create_consumer(auto_ack=False)
        publisher.send({"foo": "Baz"})
        message = fetch_next_message(consumer)
        self.assertEquals(message._state, "RECEIVED")

        consumer.close()
        publisher.close()

    def test_consumer_consume(self):
        consumer = self.create_consumer(auto_ack=True)
        publisher = self.create_publisher()
        consumer.discard_all()

        data = {"foo": "Baz"}
        publisher.send(data)
        try:
            data2 = {"company": "Vandelay Industries"}
            publisher.send(data2)
            scratchpad = {}

            def callback(message_data, message):
                scratchpad["data"] = message_data
            consumer.register_callback(callback)

            it = consumer.iterconsume()
            it.next()
            self.assertEquals(scratchpad.get("data"), data)
            it.next()
            self.assertEquals(scratchpad.get("data"), data2)

            # Cancel consumer/close and restart.
            consumer.close()
            consumer = self.create_consumer(auto_ack=True)
            consumer.register_callback(callback)
            consumer.discard_all()
            scratchpad = {}

            # Test limits
            it = consumer.iterconsume(limit=4)
            publisher.send(data)
            publisher.send(data2)
            publisher.send(data)
            publisher.send(data2)
            publisher.send(data)

            it.next()
            self.assertEquals(scratchpad.get("data"), data)
            it.next()
            self.assertEquals(scratchpad.get("data"), data2)
            it.next()
            self.assertEquals(scratchpad.get("data"), data)
            it.next()
            self.assertEquals(scratchpad.get("data"), data2)
            self.assertRaises(StopIteration, it.next)


        finally:
            consumer.close()
            publisher.close()

    def test_consumerset_iterconsume(self):
        consumerset = self.create_consumerset(queues={
            "bar": {
                "exchange": "foo",
                "exchange_type": "direct",
                "routing_key": "foo.bar",
            },
            "baz": {
                "exchange": "foo",
                "exchange_type": "direct",
                "routing_key": "foo.baz",
            },
            "bam": {
                "exchange": "foo",
                "exchange_type": "direct",
                "routing_key": "foo.bam",
            },
            "xuzzy": {
                "exchange": "foo",
                "exchange_type": "direct",
                "routing_key": "foo.xuzzy",
            }})
        publisher = self.create_publisher(exchange="foo")
        consumerset.discard_all()

        scratchpad = {}

        def callback(message_data, message):
            scratchpad["data"] = message_data

        def assertDataIs(what):
            self.assertEquals(scratchpad.get("data"), what)

        try:
            consumerset.register_callback(callback)
            it = consumerset.iterconsume()
            publisher.send({"rkey": "foo.xuzzy"}, routing_key="foo.xuzzy")
            it.next()
            assertDataIs({"rkey": "foo.xuzzy"})

            publisher.send({"rkey": "foo.xuzzy"}, routing_key="foo.xuzzy")
            publisher.send({"rkey": "foo.bar"}, routing_key="foo.bar")
            publisher.send({"rkey": "foo.baz"}, routing_key="foo.baz")
            publisher.send({"rkey": "foo.bam"}, routing_key="foo.bam")

            it.next()
            assertDataIs({"rkey": "foo.xuzzy"})
            it.next()
            assertDataIs({"rkey": "foo.bar"})
            it.next()
            assertDataIs({"rkey": "foo.baz"})
            it.next()
            assertDataIs({"rkey": "foo.bam"})

        finally:
            consumerset.close()
            publisher.close()

########NEW FILE########
__FILENAME__ = test_django
import os
import sys
import unittest
import pickle
import time
sys.path.insert(0, os.pardir)
sys.path.append(os.getcwd())

from tests.utils import BROKER_HOST, BROKER_PORT, BROKER_VHOST, \
                        BROKER_USER, BROKER_PASSWORD
from carrot.connection import DjangoBrokerConnection, BrokerConnection
from UserDict import UserDict

CARROT_BACKEND = "amqp"


class DictWrapper(UserDict):

    def __init__(self, data):
        self.data = data

    def __getattr__(self, key):
        try:
            return self.data[key]
        except KeyError:
            raise AttributeError("'%s' object has no attribute '%s'" % (
                self.__class__.__name__, key))


def configured_or_configure(settings, **conf):
    if settings.configured:
        for conf_name, conf_value in conf.items():
            setattr(settings, conf_name, conf_value)
    else:
        settings.configure(default_settings=DictWrapper(conf))


class TestDjangoSpecific(unittest.TestCase):

    def test_DjangoBrokerConnection(self):
        try:
            from django.conf import settings
        except ImportError:
            sys.stderr.write(
                "Django is not installed. \
                Not testing django specific features.\n")
            return
        configured_or_configure(settings,
                CARROT_BACKEND=CARROT_BACKEND,
                BROKER_HOST=BROKER_HOST,
                BROKER_PORT=BROKER_PORT,
                BROKER_VHOST=BROKER_VHOST,
                BROKER_USER=BROKER_USER,
                BROKER_PASSWORD=BROKER_PASSWORD)

        expected_values = {
            "backend_cls": CARROT_BACKEND,
            "hostname": BROKER_HOST,
            "port": BROKER_PORT,
            "virtual_host": BROKER_VHOST,
            "userid": BROKER_USER,
            "password": BROKER_PASSWORD}

        conn = DjangoBrokerConnection()
        self.assertTrue(isinstance(conn, BrokerConnection))

        for val_name, val_value in expected_values.items():
            self.assertEquals(getattr(conn, val_name, None), val_value)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_examples
import os
import sys
import unittest
sys.path.insert(0, os.pardir)
sys.path.append(os.getcwd())

from tests.utils import establish_test_connection
from carrot.connection import BrokerConnection
from carrot.backends.pyamqplib import Message

README_QUEUE = "feed"
README_EXCHANGE = "feed"
README_ROUTING_KEY = "feed"


class TimeoutError(Exception):
    """The operation timed out."""


def receive_a_message(consumer):
    while True:
        message = consumer.fetch()
        if message:
            return message


def emulate_wait(consumer):
    message = receive_a_message(consumer)
    consumer._receive_callback(message)


class CallbacksTestable(object):
    last_feed = None
    last_status = None
    last_body = None
    last_delivery_tag = None

    def import_feed(self, message_data, message):
        feed_url = message_data.get("import_feed")
        self.last_feed = feed_url
        if not feed_url:
            self.last_status = "REJECT"
            message.reject()
        else:
            self.last_status = "ACK"
            message.ack()

    def dump_message(self, message_data, message):
        self.last_body = message.body
        self.last_delivery_tag = message.delivery_tag


def create_README_consumer(amqpconn):
    from carrot.messaging import Consumer
    consumer = Consumer(connection=amqpconn,
                        queue=README_QUEUE, exchange=README_EXCHANGE,
                        routing_key=README_ROUTING_KEY)
    tcallbacks = CallbacksTestable()
    consumer.register_callback(tcallbacks.import_feed)
    consumer.register_callback(tcallbacks.dump_message)
    return consumer, tcallbacks


def create_README_publisher(amqpconn):
    from carrot.messaging import Publisher
    publisher = Publisher(connection=amqpconn, exchange=README_EXCHANGE,
                          routing_key=README_ROUTING_KEY)
    return publisher


class TestExamples(unittest.TestCase):

    def setUp(self):
        self.conn = establish_test_connection()
        self.consumer, self.tcallbacks = create_README_consumer(self.conn)
        self.consumer.discard_all()

    def test_connection(self):
        self.assertTrue(self.conn)
        self.assertTrue(self.conn.connection.channel())

    def test_README_consumer(self):
        consumer = self.consumer
        tcallbacks = self.tcallbacks
        self.assertTrue(consumer.connection)
        self.assertTrue(isinstance(consumer.connection, BrokerConnection))
        self.assertEquals(consumer.queue, README_QUEUE)
        self.assertEquals(consumer.exchange, README_EXCHANGE)
        self.assertEquals(consumer.routing_key, README_ROUTING_KEY)
        self.assertTrue(len(consumer.callbacks), 2)

    def test_README_publisher(self):
        publisher = create_README_publisher(self.conn)
        self.assertTrue(publisher.connection)
        self.assertTrue(isinstance(publisher.connection, BrokerConnection))
        self.assertEquals(publisher.exchange, README_EXCHANGE)
        self.assertEquals(publisher.routing_key, README_ROUTING_KEY)

    def test_README_together(self):
        consumer = self.consumer
        tcallbacks = self.tcallbacks

        publisher = create_README_publisher(self.conn)
        feed_url = "http://cnn.com/rss/edition.rss"
        body = {"import_feed": feed_url}
        publisher.send(body)
        publisher.close()
        emulate_wait(consumer)

        self.assertEquals(tcallbacks.last_feed, feed_url)
        self.assertTrue(tcallbacks.last_delivery_tag)
        self.assertEquals(tcallbacks.last_status, "ACK")

        publisher = create_README_publisher(self.conn)
        body = {"foo": "FOO"}
        publisher.send(body)
        publisher.close()
        emulate_wait(consumer)

        self.assertFalse(tcallbacks.last_feed)
        self.assertTrue(tcallbacks.last_delivery_tag)
        self.assertEquals(tcallbacks.last_status, "REJECT")

    def test_subclassing(self):
        from carrot.messaging import Consumer, Publisher
        feed_url = "http://cnn.com/rss/edition.rss"
        testself = self

        class TConsumer(Consumer):
            queue = README_QUEUE
            exchange = README_EXCHANGE
            routing_key = README_ROUTING_KEY

            def receive(self, message_data, message):
                testself.assertTrue(isinstance(message, Message))
                testself.assertTrue("import_feed" in message_data)
                testself.assertEquals(message_data.get("import_feed"),
                        feed_url)

        class TPublisher(Publisher):
            exchange = README_EXCHANGE
            routing_key = README_ROUTING_KEY

        consumer = TConsumer(connection=self.conn)
        publisher = TPublisher(connection=self.conn)

        consumer.discard_all()
        publisher.send({"import_feed": feed_url})
        publisher.close()
        emulate_wait(consumer)

        consumer.close()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_pyamqplib
import os
import sys
import unittest
import pickle
import time
sys.path.insert(0, os.pardir)
sys.path.append(os.getcwd())

from tests.utils import establish_test_connection
from carrot.connection import BrokerConnection
from carrot.messaging import Consumer, Publisher, ConsumerSet
from carrot.backends.pyamqplib import Backend as AMQPLibBackend
from carrot.backends.pyamqplib import Message as AMQPLibMessage
from carrot import serialization
from tests.backend import BackendMessagingCase

TEST_QUEUE = "carrot.unittest"
TEST_EXCHANGE = "carrot.unittest"
TEST_ROUTING_KEY = "carrot.unittest"

TEST_QUEUE_TWO = "carrot.unittest.two"
TEST_EXCHANGE_TWO = "carrot.unittest.two"
TEST_ROUTING_KEY_TWO = "carrot.unittest.two"

TEST_CELERY_QUEUE = {
            TEST_QUEUE: {
                "exchange": TEST_EXCHANGE,
                "exchange_type": "direct",
                "routing_key": TEST_ROUTING_KEY,
            },
            TEST_QUEUE_TWO: {
                "exchange": TEST_EXCHANGE_TWO,
                "exchange_type": "direct",
                "routing_key": TEST_ROUTING_KEY_TWO,
            },
        }


class TestAMQPlibMessaging(BackendMessagingCase):

    def setUp(self):
        self.conn = establish_test_connection()
        self.queue = TEST_QUEUE
        self.exchange = TEST_EXCHANGE
        self.routing_key = TEST_ROUTING_KEY
BackendMessagingCase = None

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_pyqueue
import os
import sys
import unittest
import uuid
sys.path.insert(0, os.pardir)
sys.path.append(os.getcwd())

from carrot.backends.queue import Message as PyQueueMessage
from carrot.backends.queue import Backend as PyQueueBackend
from carrot.connection import BrokerConnection
from carrot.messaging import Messaging, Consumer, Publisher


def create_backend():
    return PyQueueBackend(connection=BrokerConnection())


class TestPyQueueMessage(unittest.TestCase):

    def test_message(self):
        b = create_backend()
        self.assertTrue(b)

        message_body = "George Constanza"
        delivery_tag = str(uuid.uuid4())

        m1 = PyQueueMessage(backend=b,
                            body=message_body,
                            delivery_tag=delivery_tag)
        m2 = PyQueueMessage(backend=b,
                            body=message_body,
                            delivery_tag=delivery_tag)
        m3 = PyQueueMessage(backend=b,
                            body=message_body,
                            delivery_tag=delivery_tag)
        self.assertEquals(m1.body, message_body)
        self.assertEquals(m1.delivery_tag, delivery_tag)

        m1.ack()
        m2.reject()
        m3.requeue()


class TestPyQueueBackend(unittest.TestCase):

    def test_backend(self):
        b = create_backend()
        message_body = "Vandelay Industries"
        b.publish(b.prepare_message(message_body, "direct",
                                    content_type='text/plain',
                                    content_encoding="ascii"),
                  exchange="test",
                  routing_key="test")
        m_in_q = b.get()
        self.assertTrue(isinstance(m_in_q, PyQueueMessage))
        self.assertEquals(m_in_q.body, message_body)
    
    def test_consumer_interface(self):
        to_send = ['No', 'soup', 'for', 'you!']
        messages = []
        def cb(message_data, message):
            messages.append(message_data)
        conn = BrokerConnection(backend_cls='memory')
        consumer = Consumer(connection=conn, queue="test",
                            exchange="test", routing_key="test")
        consumer.register_callback(cb)
        publisher = Publisher(connection=conn, exchange="test",
                              routing_key="test")
        for i in to_send:
            publisher.send(i)
        it = consumer.iterconsume()
        for i in range(len(to_send)):
            it.next()
        self.assertEqual(messages, to_send)


class TMessaging(Messaging):
    exchange = "test"
    routing_key = "test"
    queue = "test"


class TestMessaging(unittest.TestCase):

    def test_messaging(self):
        m = TMessaging(connection=BrokerConnection(backend_cls=PyQueueBackend))
        self.assertTrue(m)

        self.assertEquals(m.fetch(), None)
        mdata = {"name": "Cosmo Kramer"}
        m.send(mdata)
        next_msg = m.fetch()
        next_msg_data = next_msg.decode()
        self.assertEquals(next_msg_data, mdata)
        self.assertEquals(m.fetch(), None)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_serialization
#!/usr/bin/python
# -*- coding: utf-8 -*-

import cPickle
import sys
import os
import unittest
import uuid
sys.path.insert(0, os.pardir)
sys.path.append(os.getcwd())


from carrot.serialization import registry

# For content_encoding tests
unicode_string = u'abcdé\u8463'
unicode_string_as_utf8 = unicode_string.encode('utf-8')
latin_string = u'abcdé'
latin_string_as_latin1 = latin_string.encode('latin-1')
latin_string_as_utf8 = latin_string.encode('utf-8')


# For serialization tests
py_data = {"string": "The quick brown fox jumps over the lazy dog",
        "int": 10,
        "float": 3.14159265,
        "unicode": u"Thé quick brown fox jumps over thé lazy dog",
        "list": ["george", "jerry", "elaine", "cosmo"],
}

# JSON serialization tests
json_data = ('{"int": 10, "float": 3.1415926500000002, '
             '"list": ["george", "jerry", "elaine", "cosmo"], '
             '"string": "The quick brown fox jumps over the lazy '
             'dog", "unicode": "Th\\u00e9 quick brown fox jumps over '
             'th\\u00e9 lazy dog"}')

# Pickle serialization tests
pickle_data = cPickle.dumps(py_data)

# YAML serialization tests
yaml_data = ('float: 3.1415926500000002\nint: 10\n'
             'list: [george, jerry, elaine, cosmo]\n'
             'string: The quick brown fox jumps over the lazy dog\n'
             'unicode: "Th\\xE9 quick brown fox '
             'jumps over th\\xE9 lazy dog"\n')


msgpack_py_data = dict(py_data)
# msgpack only supports tuples
msgpack_py_data["list"] = tuple(msgpack_py_data["list"])
# Unicode chars are lost in transmit :(
msgpack_py_data["unicode"] = 'Th quick brown fox jumps over th lazy dog'
msgpack_data = ('\x85\xa3int\n\xa5float\xcb@\t!\xfbS\xc8\xd4\xf1\xa4list'
                '\x94\xa6george\xa5jerry\xa6elaine\xa5cosmo\xa6string\xda'
                '\x00+The quick brown fox jumps over the lazy dog\xa7unicode'
                '\xda\x00)Th quick brown fox jumps over th lazy dog')


def say(m):
    sys.stderr.write("%s\n" % (m, ))


class TestSerialization(unittest.TestCase):

    def test_content_type_decoding(self):
        content_type = 'plain/text'

        self.assertEquals(unicode_string,
                          registry.decode(
                              unicode_string_as_utf8,
                              content_type='plain/text',
                              content_encoding='utf-8'))
        self.assertEquals(latin_string,
                          registry.decode(
                              latin_string_as_latin1,
                              content_type='application/data',
                              content_encoding='latin-1'))

    def test_content_type_binary(self):
        content_type = 'plain/text'

        self.assertNotEquals(unicode_string,
                             registry.decode(
                                 unicode_string_as_utf8,
                                 content_type='application/data',
                                 content_encoding='binary'))

        self.assertEquals(unicode_string_as_utf8,
                          registry.decode(
                              unicode_string_as_utf8,
                              content_type='application/data',
                              content_encoding='binary'))

    def test_content_type_encoding(self):
        # Using the "raw" serializer
        self.assertEquals(unicode_string_as_utf8,
                          registry.encode(
                              unicode_string, serializer="raw")[-1])
        self.assertEquals(latin_string_as_utf8,
                          registry.encode(
                              latin_string, serializer="raw")[-1])
        # And again w/o a specific serializer to check the
        # code where we force unicode objects into a string.
        self.assertEquals(unicode_string_as_utf8,
                            registry.encode(unicode_string)[-1])
        self.assertEquals(latin_string_as_utf8,
                            registry.encode(latin_string)[-1])

    def test_json_decode(self):
        self.assertEquals(py_data,
                          registry.decode(
                              json_data,
                              content_type='application/json',
                              content_encoding='utf-8'))

    def test_json_encode(self):
        self.assertEquals(registry.decode(
                              registry.encode(py_data, serializer="json")[-1],
                              content_type='application/json',
                              content_encoding='utf-8'),
                          registry.decode(
                              json_data,
                              content_type='application/json',
                              content_encoding='utf-8'))

    def test_msgpack_decode(self):
        try:
            import msgpack
        except ImportError:
            return say("* msgpack-python not installed, will not execute "
                       "related tests.")
        self.assertEquals(msgpack_py_data,
                          registry.decode(
                              msgpack_data,
                              content_type='application/x-msgpack',
                              content_encoding='binary'))

    def test_msgpack_encode(self):
        try:
            import msgpack
        except ImportError:
            return say("* msgpack-python not installed, will not execute "
                       "related tests.")
        self.assertEquals(registry.decode(
                registry.encode(msgpack_py_data, serializer="msgpack")[-1],
                content_type='application/x-msgpack',
                content_encoding='binary'),
                registry.decode(
                    msgpack_data,
                    content_type='application/x-msgpack',
                    content_encoding='binary'))


    def test_yaml_decode(self):
        try:
            import yaml
        except ImportError:
            return say("* PyYAML not installed, will not execute "
                       "related tests.")
        self.assertEquals(py_data,
                          registry.decode(
                              yaml_data,
                              content_type='application/x-yaml',
                              content_encoding='utf-8'))

    def test_yaml_encode(self):
        try:
            import yaml
        except ImportError:
            return say("* PyYAML not installed, will not execute "
                       "related tests.")
        self.assertEquals(registry.decode(
                              registry.encode(py_data, serializer="yaml")[-1],
                              content_type='application/x-yaml',
                              content_encoding='utf-8'),
                          registry.decode(
                              yaml_data,
                              content_type='application/x-yaml',
                              content_encoding='utf-8'))

    def test_pickle_decode(self):
        self.assertEquals(py_data,
                          registry.decode(
                              pickle_data,
                              content_type='application/x-python-serialize',
                              content_encoding='binary'))

    def test_pickle_encode(self):
        self.assertEquals(pickle_data,
                          registry.encode(py_data,
                              serializer="pickle")[-1])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_utils
import unittest

from carrot import utils


class TestUtils(unittest.TestCase):

    def test_partition_unicode(self):
        s = u'hi mom'
        self.assertEqual(utils.partition(s, ' '), (u'hi', u' ', u'mom'))

    def test_rpartition_unicode(self):
        s = u'hi mom !'
        self.assertEqual(utils.rpartition(s, ' '), (u'hi mom', u' ', u'!'))

########NEW FILE########
__FILENAME__ = test_with_statement
from __future__ import with_statement
import os
import sys
import unittest
sys.path.insert(0, os.pardir)
sys.path.append(os.getcwd())

from tests.utils import test_connection_args
from carrot.connection import BrokerConnection
from carrot.messaging import Consumer, Publisher


class TestTransactioned(unittest.TestCase):

    def test_with_statement(self):

        with BrokerConnection(**test_connection_args()) as conn:
            self.assertFalse(conn._closed)
            with Publisher(connection=conn, exchange="F", routing_key="G") \
                    as publisher:
                        self.assertFalse(publisher._closed)
        self.assertTrue(conn._closed)
        self.assertTrue(publisher._closed)

        with BrokerConnection(**test_connection_args()) as conn:
            self.assertFalse(conn._closed)
            with Consumer(connection=conn, queue="E", exchange="F",
                    routing_key="G") as consumer:
                        self.assertFalse(consumer._closed)
        self.assertTrue(conn._closed)
        self.assertTrue(consumer._closed)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = utils
import os

from carrot.connection import BrokerConnection


BROKER_HOST = os.environ.get('BROKER_HOST', "localhost")
BROKER_PORT = os.environ.get('BROKER_PORT', 5672)
BROKER_VHOST = os.environ.get('BROKER_VHOST', "/")
BROKER_USER = os.environ.get('BROKER_USER', "guest")
BROKER_PASSWORD = os.environ.get('BROKER_PASSWORD', "guest")

STOMP_HOST = os.environ.get('STOMP_HOST', 'localhost')
STOMP_PORT = os.environ.get('STOMP_PORT', 61613)
STOMP_QUEUE = os.environ.get('STOMP_QUEUE', '/queue/testcarrot')


def test_connection_args():
    return {"hostname": BROKER_HOST, "port": BROKER_PORT,
            "virtual_host": BROKER_VHOST, "userid": BROKER_USER,
            "password": BROKER_PASSWORD}


def test_stomp_connection_args():
    return {"hostname": STOMP_HOST, "port": STOMP_PORT}


def establish_test_connection():
    return BrokerConnection(**test_connection_args())

########NEW FILE########
__FILENAME__ = xxxstmop
import os
import sys
import unittest
import uuid
sys.path.insert(0, os.pardir)
sys.path.append(os.getcwd())

try:
    import stompy
except ImportError:
    stompy = None
    Frame = StompMessage = StompBackend = object

else:
    from carrot.backends.pystomp import Message as StompMessage
    from carrot.backends.pystomp import Backend as StompBackend
    from stompy.frame import Frame

from carrot.connection import BrokerConnection
from carrot.messaging import Publisher, Consumer
from tests.utils import test_stomp_connection_args, STOMP_QUEUE
from carrot.serialization import encode

_no_stompy_msg = "* stompy (python-stomp) not installed. " \
               + "Will not execute related tests."
_no_stompy_msg_emitted = False


def stompy_or_None():

    def emit_no_stompy_msg():
        global _no_stompy_msg_emitted
        if not _no_stompy_msg_emitted:
            sys.stderr.write("\n" + _no_stompy_msg + "\n")
            _no_stompy_msg_emitted = True

    if stompy is None:
        emit_no_stompy_msg()
        return None
    return stompy


def create_connection():
    return BrokerConnection(backend_cls=StompBackend,
                            **test_stomp_connection_args())


def create_backend():
    return create_connection().create_backend()


class MockFrame(Frame):

    def mock(self, command=None, headers=None, body=None):
        self.command = command
        self.headers = headers
        self.body = body
        return self


class TestStompMessage(unittest.TestCase):

    def test_message(self):
        if not stompy_or_None():
            return
        b = create_backend()

        self.assertTrue(b)

        message_body = "George Constanza"
        delivery_tag = str(uuid.uuid4())

        frame = MockFrame().mock(body=message_body, headers={
            "message-id": delivery_tag,
            "content_type": "text/plain",
            "content_encoding": "utf-8",
        })

        m1 = StompMessage(backend=b, frame=frame)
        m2 = StompMessage(backend=b, frame=frame)
        m3 = StompMessage(backend=b, frame=frame)
        self.assertEquals(m1.body, message_body)
        self.assertEquals(m1.delivery_tag, delivery_tag)

        #m1.ack()
        self.assertRaises(NotImplementedError, m2.reject)
        self.assertRaises(NotImplementedError, m3.requeue)


class TestPyStompMessaging(unittest.TestCase):

    def setUp(self):
        if stompy_or_None():
            self.conn = create_connection()
        self.queue = STOMP_QUEUE
        self.exchange = STOMP_QUEUE
        self.routing_key = STOMP_QUEUE

    def create_consumer(self, **options):
        return Consumer(connection=self.conn,
                        queue=self.queue, exchange=self.exchange,
                        routing_key=self.routing_key, **options)

    def create_publisher(self, **options):
        return Publisher(connection=self.conn,
                exchange=self.exchange,
                routing_key=self.routing_key, **options)

    def test_backend(self):
        if not stompy_or_None():
            return
        publisher = self.create_publisher()
        consumer = self.create_consumer()
        for i in range(100):
            publisher.send({"foo%d" % i: "bar%d" % i})
        publisher.close()

        discarded = consumer.discard_all()
        self.assertEquals(discarded, 100)
        publisher.close()
        consumer.close()

        publisher = self.create_publisher()
        for i in range(100):
            publisher.send({"foo%d" % i: "bar%d" % i})

        consumer = self.create_consumer()
        for i in range(100):
            while True:
                message = consumer.fetch()
                if message:
                    break
            self.assertTrue("foo%d" % i in message.payload)
            message.ack()

        publisher.close()
        consumer.close()


        consumer = self.create_consumer()
        discarded = consumer.discard_all()
        self.assertEquals(discarded, 0)

    def create_raw_message(self, publisher, body, delivery_tag):
        content_type, content_encoding, payload = encode(body)
        frame = MockFrame().mock(body=payload, headers={
            "message-id": delivery_tag,
            "content-type": content_type,
            "content-encoding": content_encoding,
        })
        return frame

########NEW FILE########
