__FILENAME__ = conf
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '../')
#needs_sphinx = '1.0'

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode',
              'sphinx.ext.intersphinx']

intersphinx_mapping = {'python': ('http://docs.python.org/2/objects.inv',
                                  'http://docs.python.org/2/objects.inv'),
                       'tornado': ('http://www.tornadoweb.org/en/stable/',
                                   'http://www.tornadoweb.org/en/stable/objects.inv')}

templates_path = ['_templates']

source_suffix = '.rst'
master_doc = 'index'

project = 'pika'
copyright = '2010-2013, Tony Garnock-Jones, Gavin M. Roy, VMWare and others.'

version = '0.9'
release = '0.9.13'

exclude_patterns = ['_build']
add_function_parentheses = True
add_module_names = True
show_authors = True
pygments_style = 'sphinx'
modindex_common_prefix = ['pika']
html_theme = 'default'
html_static_path = ['_static']
htmlhelp_basename = 'pikadoc'

########NEW FILE########
__FILENAME__ = confirmation
import pika
from pika import spec
import logging

ITERATIONS = 100

logging.basicConfig(level=logging.INFO)

confirmed = 0
errors = 0
published = 0

def on_open(connection):
    connection.channel(on_channel_open)


def on_channel_open(channel):
    global published
    channel.confirm_delivery(on_delivery_confirmation)
    for iteration in xrange(0, ITERATIONS):
        channel.basic_publish('test', 'test.confirm',
                              'message body value',
                               pika.BasicProperties(content_type='text/plain',
                                                    delivery_mode=1))
        published += 1

def on_delivery_confirmation(frame):
    global confirmed, errors
    if isinstance(frame.method, spec.Basic.Ack):
        confirmed += 1
        logging.info('Received confirmation: %r', frame.method)
    else:
        logging.error('Received negative confirmation: %r', frame.method)
        errors += 1
    if (confirmed + errors) == ITERATIONS:
        logging.info('All confirmations received, published %i, confirmed %i with %i errors', published, confirmed, errors)
        connection.close()

parameters = pika.URLParameters('amqp://guest:guest@localhost:5672/%2F?connection_attempts=50')
connection = pika.SelectConnection(parameters=parameters,
                                   on_open_callback=on_open)

try:
    connection.ioloop.start()
except KeyboardInterrupt:
    connection.close()
    connection.ioloop.start()

########NEW FILE########
__FILENAME__ = consume
import pika

def on_message(channel, method_frame, header_frame, body):
    channel.queue_declare(queue=body, auto_delete=True)

    if body.startswith("queue:"):
        queue = body.replace("queue:", "")
        key = body + "_key"
        print("Declaring queue %s bound with key %s" %(queue, key))
        channel.queue_declare(queue=queue, auto_delete=True)
        channel.queue_bind(queue=queue, exchange="test_exchange", routing_key=key)
    else:
        print("Message body", body)

    channel.basic_ack(delivery_tag=method_frame.delivery_tag)

credentials = pika.PlainCredentials('guest', 'guest')
parameters =  pika.ConnectionParameters('localhost', credentials=credentials)
connection = pika.BlockingConnection(parameters)

channel = connection.channel()
channel.exchange_declare(exchange="test_exchange", exchange_type="direct", passive=False, durable=True, auto_delete=False)
channel.queue_declare(queue="standard", auto_delete=True)
channel.queue_bind(queue="standard", exchange="test_exchange", routing_key="standard_key")
channel.basic_qos(prefetch_count=1)

channel.basic_consume(on_message, 'standard')

try:
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()

connection.close()

########NEW FILE########
__FILENAME__ = consumer_queued
#!/usr/bin/python
# -*- coding: utf-8 -*-

import pika
import json
import threading


buffer = []
lock = threading.Lock()

print('pika version: %s' % pika.__version__)


connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))

main_channel     = connection.channel()
consumer_channel = connection.channel()
bind_channel     = connection.channel()

if pika.__version__=='0.9.5':
    main_channel.exchange_declare(exchange='com.micex.sten',       type='direct')
    main_channel.exchange_declare(exchange='com.micex.lasttrades', type='direct')
else:
    main_channel.exchange_declare(exchange='com.micex.sten',       exchange_type='direct')
    main_channel.exchange_declare(exchange='com.micex.lasttrades', exchange_type='direct')

queue         = main_channel.queue_declare(exclusive=True).method.queue
queue_tickers = main_channel.queue_declare(exclusive=True).method.queue

main_channel.queue_bind(exchange='com.micex.sten', queue=queue, routing_key='order.stop.create')



def process_buffer():
    if not lock.acquire(False):
        print('locked!')
        return
    try:
        while len(buffer):
            body = buffer.pop(0)

            ticker = None
            if 'ticker' in body['data']['params']['condition']: ticker = body['data']['params']['condition']['ticker']
            if not ticker: continue

            print('got ticker %s, gonna bind it...' % ticker)
            bind_channel.queue_bind(exchange='com.micex.lasttrades', queue=queue_tickers, routing_key=str(ticker))
            print('ticker %s binded ok' % ticker)
    finally:
        lock.release()


def callback(ch, method, properties, body):
    body = json.loads(body)['order.stop.create']
    buffer.append(body)
    process_buffer()


consumer_channel.basic_consume(callback,
                               queue=queue, no_ack=True)

try:
    consumer_channel.start_consuming()
finally:
    connection.close()

########NEW FILE########
__FILENAME__ = consumer_simple
#!/usr/bin/python
# -*- coding: utf-8 -*-

import pika
import json


print(('pika version: %s') % pika.__version__)


connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))

main_channel     = connection.channel()
consumer_channel = connection.channel()
bind_channel     = connection.channel()

if pika.__version__=='0.9.5':
    main_channel.exchange_declare(exchange='com.micex.sten',       type='direct')
    main_channel.exchange_declare(exchange='com.micex.lasttrades', type='direct')
else:
    main_channel.exchange_declare(exchange='com.micex.sten',       exchange_type='direct')
    main_channel.exchange_declare(exchange='com.micex.lasttrades', exchange_type='direct')

queue         = main_channel.queue_declare(exclusive=True).method.queue
queue_tickers = main_channel.queue_declare(exclusive=True).method.queue

main_channel.queue_bind(exchange='com.micex.sten', queue=queue, routing_key='order.stop.create')


def hello():
    print('Hello world')

connection.add_timeout(5, hello)


def callback(ch, method, properties, body):
    body = json.loads(body)['order.stop.create']

    ticker = None
    if 'ticker' in body['data']['params']['condition']: ticker = body['data']['params']['condition']['ticker']
    if not ticker: return

    print('got ticker %s, gonna bind it...' % ticker)
    bind_channel.queue_bind(exchange='com.micex.lasttrades', queue=queue_tickers, routing_key=str(ticker))
    print('ticker %s binded ok' % ticker)


import logging
logging.basicConfig(level=logging.INFO)

consumer_channel.basic_consume(callback,
                               queue=queue, no_ack=True)

try:
    consumer_channel.start_consuming()
finally:
    connection.close()

########NEW FILE########
__FILENAME__ = producer
#!/usr/bin/python
# -*- coding: utf-8 -*-

import pika    
import json
import random

print(('pika version: %s') % pika.__version__)

connection   = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
main_channel = connection.channel()  

if pika.__version__=='0.9.5':
    main_channel.exchange_declare(exchange='com.micex.sten',       type='direct')
    main_channel.exchange_declare(exchange='com.micex.lasttrades', type='direct')
else:
    main_channel.exchange_declare(exchange='com.micex.sten',       exchange_type='direct')
    main_channel.exchange_declare(exchange='com.micex.lasttrades', exchange_type='direct')

tickers = {}
tickers['MXSE.EQBR.LKOH'] = (1933,1940)
tickers['MXSE.EQBR.MSNG'] = (1.35,1.45)
tickers['MXSE.EQBR.SBER'] = (90,92)
tickers['MXSE.EQNE.GAZP'] = (156,162)
tickers['MXSE.EQNE.PLZL'] = (1025,1040)
tickers['MXSE.EQNL.VTBR'] = (0.05,0.06)
def getticker(): return list(tickers.keys())[random.randrange(0,len(tickers)-1)]

_COUNT_ = 10

for i in range(0,_COUNT_):
    ticker = getticker()
    msg = {'order.stop.create':{'data':{'params':{'condition':{'ticker':ticker}}}}}
    main_channel.basic_publish(exchange='com.micex.sten', 
                               routing_key='order.stop.create', 
                               body=json.dumps(msg),
                               properties=pika.BasicProperties(content_type='application/json')
                              )                          
    print('send ticker %s' %  ticker)                         

connection.close()

########NEW FILE########
__FILENAME__ = publish
import pika
import logging

logging.basicConfig(level=logging.DEBUG)

credentials = pika.PlainCredentials('guest', 'guest')
parameters =  pika.ConnectionParameters('localhost', credentials=credentials)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()
channel.exchange_declare(exchange="test_exchange", exchange_type="direct",
                         passive=False, durable=True, auto_delete=False)

print("Sending message to create a queue")
channel.basic_publish('test_exchange', 'standard_key', 'queue:group',
                      pika.BasicProperties(content_type='text/plain',
                                           delivery_mode=1))

connection.sleep(5)

print("Sending text message to group")
channel.basic_publish('test_exchange', 'group_key', 'Message to group_key',
                      pika.BasicProperties(content_type='text/plain',
                                           delivery_mode=1))

connection.sleep(5)

print("Sending text message")
channel.basic_publish('test_exchange', 'standard_key', 'Message to standard_key',
                      pika.BasicProperties(content_type='text/plain',
                                           delivery_mode=1))

connection.close()

########NEW FILE########
__FILENAME__ = send
import pika
import time
import logging

logging.basicConfig(level=logging.DEBUG)

ITERATIONS = 100

connection = pika.BlockingConnection(pika.URLParameters('amqp://guest:guest@localhost:5672/%2F?heartbeat_interval=1'))
channel = connection.channel()

def closeit():
    print('Close it')
    connection.close()

connection.add_timeout(5, closeit)

connection.sleep(100)

"""
channel.confirm_delivery()
start_time = time.time()

for x in range(0, ITERATIONS):
    if not channel.basic_publish(exchange='test',
                                 routing_key='',
                                 body='Test 123',
                                 properties=pika.BasicProperties(content_type='text/plain',
                                                                 app_id='test',
                                                                 delivery_mode=1)):
        print 'Delivery not confirmed'
    else:
        print 'Confirmed delivery'

channel.close()
connection.close()

duration = time.time() - start_time
print "Published %i messages in %.4f seconds (%.2f messages per second)" % (ITERATIONS, duration, (ITERATIONS/duration))

"""

########NEW FILE########
__FILENAME__ = tmp
# -*- coding: utf-8 -*-
import logging
import pika
import json

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class ExamplePublisher(object):
    """This is an example publisher that will handle unexpected interactions
    with RabbitMQ such as channel and connection closures.

    If RabbitMQ closes the connection, it will reopen it. You should
    look at the output, as there are limited reasons why the connection may
    be closed, which usually are tied to permission related issues or
    socket timeouts.

    It uses delivery confirmations and illustrates one way to keep track of
    messages that have been sent and if they've been confirmed by RabbitMQ.

    """
    EXCHANGE = 'message'
    EXCHANGE_TYPE = 'topic'
    PUBLISH_INTERVAL = 1
    QUEUE = 'text'
    ROUTING_KEY = 'example.text'
    URLS = ['amqp://test:test@localhost:5672/%2F',
            'amqp://guest:guest@localhost:5672/%2F']

    def __init__(self):
        """Setup the example publisher object, passing in the URL we will use
        to connect to RabbitMQ.

        """
        self._connection = None
        self._channel = None
        self._deliveries = []
        self._acked = 0
        self._nacked = 0
        self._message_number = 0
        self._stopping = False
        self._closing = False
        self._url_offset = 0

    def connect(self):
        """This method connects to RabbitMQ, returning the connection handle.
        When the connection is established, the on_connection_open method
        will be invoked by pika.

        :rtype: pika.SelectConnection

        """
        url = self.URLS[self._url_offset]
        self._url_offset += 1
        if self._url_offset == len(self.URLS):
            self._url_offset = 0
        LOGGER.info('Connecting to %s', url)
        return pika.SelectConnection(pika.URLParameters(url),
                                     self.on_connection_open,
                                     False)

    def close_connection(self):
        """This method closes the connection to RabbitMQ."""
        LOGGER.info('Closing connection')
        self._closing = True
        self._connection.close()

    def add_on_connection_close_callback(self):
        """This method adds an on close callback that will be invoked by pika
        when RabbitMQ closes the connection to the publisher unexpectedly.

        """
        LOGGER.info('Adding connection close callback')
        self._connection.add_on_close_callback(self.on_connection_closed)

    def on_connection_closed(self, connection, reply_code, reply_text):
        """This method is invoked by pika when the connection to RabbitMQ is
        closed unexpectedly. Since it is unexpected, we will reconnect to
        RabbitMQ if it disconnects.

        :param pika.connection.Connection connection: The closed connection obj
        :param int reply_code: The server provided reply_code if given
        :param str reply_text: The server provided reply_text if given

        """
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            LOGGER.warning('Connection closed, reopening in 5 seconds: (%s) %s',
                           reply_code, reply_text)
            self._connection.add_timeout(5, self.reconnect)

    def on_connection_open(self, unused_connection):
        """This method is called by pika once the connection to RabbitMQ has
        been established. It passes the handle to the connection object in
        case we need it, but in this case, we'll just mark it unused.

        :type unused_connection: pika.SelectConnection

        """
        LOGGER.info('Connection opened')
        self.add_on_connection_close_callback()
        self.open_channel()

    def reconnect(self):
        """Will be invoked by the IOLoop timer if the connection is
        closed. See the on_connection_closed method.

        """
        # This is the old connection IOLoop instance, stop its ioloop
        self._connection.ioloop.stop()

        # Create a new connection
        self._connection = self.connect()

        # There is now a new connection, needs a new ioloop to run
        self._connection.ioloop.start()

    def add_on_channel_close_callback(self):
        """This method tells pika to call the on_channel_closed method if
        RabbitMQ unexpectedly closes the channel.

        """
        LOGGER.info('Adding channel close callback')
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reply_code, reply_text):
        """Invoked by pika when RabbitMQ unexpectedly closes the channel.
        Channels are usually closed if you attempt to do something that
        violates the protocol, such as re-declare an exchange or queue with
        different parameters. In this case, we'll close the connection
        to shutdown the object.

        :param pika.channel.Channel: The closed channel
        :param int reply_code: The numeric reason the channel was closed
        :param str reply_text: The text reason the channel was closed

        """
        LOGGER.warning('Channel was closed: (%s) %s', reply_code, reply_text)
        self._deliveries = []
        self._message_number = 0
        if not self._closing:
            self._connection.close()

    def on_channel_open(self, channel):
        """This method is invoked by pika when the channel has been opened.
        The channel object is passed in so we can make use of it.

        Since the channel is now open, we'll declare the exchange to use.

        :param pika.channel.Channel channel: The channel object

        """
        LOGGER.info('Channel opened')
        self._channel = channel
        self.add_on_channel_close_callback()
        self.setup_exchange(self.EXCHANGE)

    def setup_exchange(self, exchange_name):
        """Setup the exchange on RabbitMQ by invoking the Exchange.Declare RPC
        command. When it is complete, the on_exchange_declareok method will
        be invoked by pika.

        :param str|unicode exchange_name: The name of the exchange to declare

        """
        LOGGER.info('Declaring exchange %s', exchange_name)
        self._channel.exchange_declare(self.on_exchange_declareok,
                                       exchange_name,
                                       self.EXCHANGE_TYPE)

    def on_exchange_declareok(self, unused_frame):
        """Invoked by pika when RabbitMQ has finished the Exchange.Declare RPC
        command.

        :param pika.Frame.Method unused_frame: Exchange.DeclareOk response frame

        """
        LOGGER.info('Exchange declared')
        self.setup_queue(self.QUEUE)

    def setup_queue(self, queue_name):
        """Setup the queue on RabbitMQ by invoking the Queue.Declare RPC
        command. When it is complete, the on_queue_declareok method will
        be invoked by pika.

        :param str|unicode queue_name: The name of the queue to declare.

        """
        LOGGER.info('Declaring queue %s', queue_name)
        self._channel.queue_declare(self.on_queue_declareok, queue_name)

    def on_queue_declareok(self, method_frame):
        """Method invoked by pika when the Queue.Declare RPC call made in
        setup_queue has completed. In this method we will bind the queue
        and exchange together with the routing key by issuing the Queue.Bind
        RPC command. When this command is complete, the on_bindok method will
        be invoked by pika.

        :param pika.frame.Method method_frame: The Queue.DeclareOk frame

        """
        LOGGER.info('Binding %s to %s with %s',
                    self.EXCHANGE, self.QUEUE, self.ROUTING_KEY)
        self._channel.queue_bind(self.on_bindok, self.QUEUE,
                                 self.EXCHANGE, self.ROUTING_KEY)

    def on_delivery_confirmation(self, method_frame):
        """Invoked by pika when RabbitMQ responds to a Basic.Publish RPC
        command, passing in either a Basic.Ack or Basic.Nack frame with
        the delivery tag of the message that was published. The delivery tag
        is an integer counter indicating the message number that was sent
        on the channel via Basic.Publish. Here we're just doing house keeping
        to keep track of stats and remove message numbers that we expect
        a delivery confirmation of from the list used to keep track of messages
        that are pending confirmation.

        :param pika.frame.Method method_frame: Basic.Ack or Basic.Nack frame

        """
        confirmation_type = method_frame.method.NAME.split('.')[1].lower()
        LOGGER.info('Received %s for delivery tag: %i',
                    confirmation_type,
                    method_frame.method.delivery_tag)
        if confirmation_type == 'ack':
            self._acked += 1
        elif confirmation_type == 'nack':
            self._nacked += 1
        self._deliveries.remove(method_frame.method.delivery_tag)
        LOGGER.info('Published %i messages, %i have yet to be confirmed, '
                    '%i were acked and %i were nacked',
                    self._message_number, len(self._deliveries),
                    self._acked, self._nacked)

    def enable_delivery_confirmations(self):
        """Send the Confirm.Select RPC method to RabbitMQ to enable delivery
        confirmations on the channel. The only way to turn this off is to close
        the channel and create a new one.

        When the message is confirmed from RabbitMQ, the
        on_delivery_confirmation method will be invoked passing in a Basic.Ack
        or Basic.Nack method from RabbitMQ that will indicate which messages it
        is confirming or rejecting.

        """
        LOGGER.info('Issuing Confirm.Select RPC command')
        self._channel.confirm_delivery(self.on_delivery_confirmation)

    def publish_message(self):
        """If the class is not stopping, publish a message to RabbitMQ,
        appending a list of deliveries with the message number that was sent.
        This list will be used to check for delivery confirmations in the
        on_delivery_confirmations method.

        Once the message has been sent, schedule another message to be sent.
        The main reason I put scheduling in was just so you can get a good idea
        of how the process is flowing by slowing down and speeding up the
        delivery intervals by changing the PUBLISH_INTERVAL constant in the
        class.

        """
        if self._stopping:
            return

        message = {u'مفتاح': u' قيمة',
                   u'键': u'值',
                   u'キー': u'値'}
        properties = pika.BasicProperties(app_id='example-publisher',
                                          content_type='text/plain',
                                          headers=message)

        self._channel.basic_publish(self.EXCHANGE, self.ROUTING_KEY,
                                    json.dumps(message, ensure_ascii=False),
                                    properties)
        self._message_number += 1
        self._deliveries.append(self._message_number)
        LOGGER.info('Published message # %i', self._message_number)
        self.schedule_next_message()

    def schedule_next_message(self):
        """If we are not closing our connection to RabbitMQ, schedule another
        message to be delivered in PUBLISH_INTERVAL seconds.

        """
        if self._stopping:
            return
        LOGGER.info('Scheduling next message for %0.1f seconds',
                    self.PUBLISH_INTERVAL)
        self._connection.add_timeout(self.PUBLISH_INTERVAL,
                                     self.publish_message)

    def start_publishing(self):
        """This method will enable delivery confirmations and schedule the
        first message to be sent to RabbitMQ

        """
        LOGGER.info('Issuing consumer related RPC commands')
        self.enable_delivery_confirmations()
        self.schedule_next_message()

    def on_bindok(self, unused_frame):
        """This method is invoked by pika when it receives the Queue.BindOk
        response from RabbitMQ. Since we know we're now setup and bound, it's
        time to start publishing."""
        LOGGER.info('Queue bound')
        self.start_publishing()

    def close_channel(self):
        """Invoke this command to close the channel with RabbitMQ by sending
        the Channel.Close RPC command.

        """
        LOGGER.info('Closing the channel')
        if self._channel:
            self._channel.close()

    def open_channel(self):
        """This method will open a new channel with RabbitMQ by issuing the
        Channel.Open RPC command. When RabbitMQ confirms the channel is open
        by sending the Channel.OpenOK RPC reply, the on_channel_open method
        will be invoked.

        """
        LOGGER.info('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def run(self):
        """Run the example code by connecting and then starting the IOLoop.

        """
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        """Stop the example by closing the channel and connection. We
        set a flag here so that we stop scheduling new messages to be
        published. The IOLoop is started because this method is
        invoked by the Try/Catch below when KeyboardInterrupt is caught.
        Starting the IOLoop again will allow the publisher to cleanly
        disconnect from RabbitMQ.

        """
        LOGGER.info('Stopping')
        self._stopping = True
        self.close_channel()
        self.close_connection()
        self._connection.ioloop.start()
        LOGGER.info('Stopped')

def main():
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)

    example = ExamplePublisher()
    try:
        example.run()
    except KeyboardInterrupt:
        example.stop()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = asyncore_connection
"""
Use Pika with the stdlib :py:mod:`asyncore` module.

"""
import asyncore
import logging
import time

from pika.adapters import base_connection

LOGGER = logging.getLogger(__name__)


class PikaDispatcher(asyncore.dispatcher):

    # Use epoll's constants to keep life easy
    READ = 0x0001
    WRITE = 0x0004
    ERROR = 0x0008

    def __init__(self, sock=None, map=None, event_callback=None):
        # Is an old style class...
        asyncore.dispatcher.__init__(self, sock, map)
        self._timeouts = dict()
        self._event_callback = event_callback
        self.events = self.READ | self.WRITE

    def add_timeout(self, deadline, callback_method):
        """Add the callback_method to the IOLoop timer to fire after deadline
        seconds. Returns a handle to the timeout. Do not confuse with
        Tornado's timeout where you pass in the time you want to have your
        callback called. Only pass in the seconds until it's to be called.

        :param int deadline: The number of seconds to wait to call callback
        :param method callback_method: The callback method
        :rtype: str

        """
        value = {'deadline': time.time() + deadline,
                 'callback': callback_method}
        timeout_id = hash(frozenset(value.items()))
        self._timeouts[timeout_id] = value
        return timeout_id

    def fileno(self):
        return self.socket.fileno()

    def sendall(self, data):
        return self.socket.sendall(data)

    def readable(self):
        return bool(self.events & self.READ)

    def writable(self):
        return bool(self.events & self.WRITE)

    def handle_read(self):
        self._event_callback(self.socket.fileno, self.READ)

    def handle_write(self):
        self._event_callback(self.socket.fileno, self.WRITE, None, True)

    def process_timeouts(self):
        """Process the self._timeouts event stack"""
        start_time = time.time()
        for timeout_id in self._timeouts.keys():
            if self._timeouts[timeout_id]['deadline'] <= start_time:
                callback = self._timeouts[timeout_id]['callback']
                del self._timeouts[timeout_id]
                callback()

    def remove_timeout(self, timeout_id):
        """Remove a timeout if it's still in the timeout stack

        :param str timeout_id: The timeout id to remove

        """
        if timeout_id in self._timeouts:
            del self._timeouts[timeout_id]

    def start(self):
        LOGGER.debug('Starting IOLoop')
        asyncore.loop()

    def stop(self):
        LOGGER.debug('Stopping IOLoop')
        self.close()

    def update_handler(self, fileno_unused, events):
        """Set the events to the current events

        :param int fileno_unused: The file descriptor
        :param int events: The event mask

        """
        self.events = events


class AsyncoreConnection(base_connection.BaseConnection):
    """The AsyncoreConnection adapter uses the stdlib asyncore module as an
    IOLoop for asyncronous client development.

    :param pika.connection.Parameters parameters: Connection parameters
    :param method on_open_callback: Method to call on connection open
    :param on_open_error_callback: Method to call if the connection cant
                                   be opened
    :type on_open_error_callback: method
    :param method on_close_callback: Method to call on connection close
    :param bool stop_ioloop_on_close: Call ioloop.stop() if disconnected
    :raises: RuntimeError

    """
    def __init__(self,
                 parameters=None,
                 on_open_callback=None,
                 on_open_error_callback=None,
                 on_close_callback=None,
                 stop_ioloop_on_close=True):
        """Create a new instance of the Connection object.

        :param pika.connection.Parameters parameters: Connection parameters
        :param method on_open_callback: Method to call on connection open
        :param on_open_error_callback: Method to call if the connection cant
                                       be opened
        :type on_open_error_callback: method
        :param method on_close_callback: Method to call on connection close
        :param bool stop_ioloop_on_close: Call ioloop.stop() if disconnected
        :raises: RuntimeError

        """
        class ConnectingIOLoop(object):
            def add_timeout(self, duration, callback_method):
                time.sleep(duration)
                return callback_method()
        ioloop = ConnectingIOLoop()
        super(AsyncoreConnection, self).__init__(parameters, on_open_callback,
                                                 on_open_error_callback,
                                                 on_close_callback,
                                                 ioloop,
                                                 stop_ioloop_on_close)

    def _adapter_connect(self):
        """Connect to our RabbitMQ broker using AsyncoreDispatcher, then setting
        Pika's suggested buffer size for socket reading and writing. We pass
        the handle to self so that the AsyncoreDispatcher object can call back
        into our various state methods.

        """
        error = super(AsyncoreConnection, self)._adapter_connect()
        if not error:
            self.socket = PikaDispatcher(self.socket, None,
                                         self._handle_events)
            self.ioloop = self.socket
            self._on_connected()
        return error


########NEW FILE########
__FILENAME__ = base_connection
"""Base class extended by connection adapters. This extends the
connection.Connection class to encapsulate connection behavior but still
isolate socket and low level communication.

"""
import errno
import logging
import socket
import ssl

from pika import connection
from pika import exceptions

try:
    SOL_TCP = socket.SOL_TCP
except AttributeError:
    SOL_TCP = 6

LOGGER = logging.getLogger(__name__)


class BaseConnection(connection.Connection):
    """BaseConnection class that should be extended by connection adapters"""

    # Use epoll's constants to keep life easy
    READ = 0x0001
    WRITE = 0x0004
    ERROR = 0x0008

    ERRORS_TO_IGNORE = [errno.EWOULDBLOCK, errno.EAGAIN, errno.EINTR]
    DO_HANDSHAKE = True
    WARN_ABOUT_IOLOOP = False

    def __init__(self,
                 parameters=None,
                 on_open_callback=None,
                 on_open_error_callback=None,
                 on_close_callback=None,
                 ioloop=None,
                 stop_ioloop_on_close=True):
        """Create a new instance of the Connection object.

        :param pika.connection.Parameters parameters: Connection parameters
        :param method on_open_callback: Method to call on connection open
        :param on_open_error_callback: Method to call if the connection cant
                                       be opened
        :type on_open_error_callback: method
        :param method on_close_callback: Method to call on connection close
        :param object ioloop: IOLoop object to use
        :param bool stop_ioloop_on_close: Call ioloop.stop() if disconnected
        :raises: RuntimeError
        :raises: ValueError

        """
        if parameters and not isinstance(parameters, connection.Parameters):
            raise ValueError('Expected instance of Parameters, not %r' %
                             parameters)

        # Let the developer know we could not import SSL
        if parameters and parameters.ssl and not ssl:
            raise RuntimeError("SSL specified but it is not available")
        self.base_events = self.READ | self.ERROR
        self.event_state = self.base_events
        self.fd = None
        self.ioloop = ioloop
        self.socket = None
        self.stop_ioloop_on_close = stop_ioloop_on_close
        self.write_buffer = None
        super(BaseConnection, self).__init__(parameters,
                                             on_open_callback,
                                             on_open_error_callback,
                                             on_close_callback)

    def add_timeout(self, deadline, callback_method):
        """Add the callback_method to the IOLoop timer to fire after deadline
        seconds. Returns a handle to the timeout

        :param int deadline: The number of seconds to wait to call callback
        :param method callback_method: The callback method
        :rtype: str

        """
        return self.ioloop.add_timeout(deadline, callback_method)

    def close(self, reply_code=200, reply_text='Normal shutdown'):
        """Disconnect from RabbitMQ. If there are any open channels, it will
        attempt to close them prior to fully disconnecting. Channels which
        have active consumers will attempt to send a Basic.Cancel to RabbitMQ
        to cleanly stop the delivery of messages prior to closing the channel.

        :param int reply_code: The code number for the close
        :param str reply_text: The text reason for the close

        """
        super(BaseConnection, self).close(reply_code, reply_text)
        self._handle_ioloop_stop()

    def remove_timeout(self, timeout_id):
        """Remove the timeout from the IOLoop by the ID returned from
        add_timeout.

        :rtype: str

        """
        self.ioloop.remove_timeout(timeout_id)

    def _adapter_connect(self):
        """Connect to the RabbitMQ broker, returning True if connected

        :rtype: bool

        """
        # Get the addresses for the socket, supporting IPv4 & IPv6
        try:
            addresses = socket.getaddrinfo(self.params.host, self.params.port)
        except socket.error as error:
            LOGGER.critical('Could not get addresses to use: %s (%s)',
                            error, self.params.host)
            return error

        # If the socket is created and connected, continue on
        error = "No socket addresses available"
        for sock_addr in addresses:
            error = self._create_and_connect_to_socket(sock_addr)
            if not error:
                return None
        # Failed to connect
        return error

    def _adapter_disconnect(self):
        """Invoked if the connection is being told to disconnect"""
        if hasattr(self, 'heartbeat') and self.heartbeat is not None:
            self.heartbeat.stop()
        if self.socket:
            self.socket.close()
        self.socket = None
        self._check_state_on_disconnect()
        self._handle_ioloop_stop()
        self._init_connection_state()

    def _check_state_on_disconnect(self):
        """Checks to see if we were in opening a connection with RabbitMQ when
        we were disconnected and raises exceptions for the anticipated
        exception types.

        """
        if self.connection_state == self.CONNECTION_PROTOCOL:
            LOGGER.error('Incompatible Protocol Versions')
            raise exceptions.IncompatibleProtocolError
        elif self.connection_state == self.CONNECTION_START:
            LOGGER.error("Socket closed while authenticating indicating a "
                         "probable authentication error")
            raise exceptions.ProbableAuthenticationError
        elif self.connection_state == self.CONNECTION_TUNE:
            LOGGER.error("Socket closed while tuning the connection indicating "
                         "a probable permission error when accessing a virtual "
                         "host")
            raise exceptions.ProbableAccessDeniedError
        elif self.is_open:
            LOGGER.warning("Socket closed when connection was open")
        elif not self.is_closed:
            LOGGER.warning('Unknown state on disconnect: %i',
                           self.connection_state)

    def _create_and_connect_to_socket(self, sock_addr_tuple):
        """Create socket and connect to it, using SSL if enabled."""
        self.socket = socket.socket(sock_addr_tuple[0], socket.SOCK_STREAM, 0)
        self.socket.setsockopt(SOL_TCP, socket.TCP_NODELAY, 1)
        self.socket.settimeout(self.params.socket_timeout)

        # Wrap socket if using SSL
        if self.params.ssl:
            self.socket = self._wrap_socket(self.socket)
            ssl_text = " with SSL"
        else:
            ssl_text = ""

        LOGGER.info('Connecting to %s:%s%s',
                    sock_addr_tuple[4][0], sock_addr_tuple[4][1], ssl_text)

        # Connect to the socket
        try:
            self.socket.connect(sock_addr_tuple[4])
        except socket.timeout:
            error = 'Connection to %s:%s failed: timeout' % (
                sock_addr_tuple[4][0], sock_addr_tuple[4][1])
            LOGGER.error(error)
            return error
        except socket.error as error:
            error = 'Connection to %s:%s failed: %s' % (
                sock_addr_tuple[4][0], sock_addr_tuple[4][1], error)
            LOGGER.warning(error)
            return error

        # Handle SSL Connection Negotiation
        if self.params.ssl and self.DO_HANDSHAKE:
            try:
                self._do_ssl_handshake()
            except ssl.SSLError as error:
                error = 'SSL connection to %s:%s failed: %s' % (
                    sock_addr_tuple[4][0], sock_addr_tuple[4][1], error)
                LOGGER.error(error)
                return error
        # Made it this far
        return None

    def _do_ssl_handshake(self):
        """Perform SSL handshaking, copied from python stdlib test_ssl.py.

        """
        if not self.DO_HANDSHAKE:
            return
        while True:
            try:
                self.socket.do_handshake()
                break
            except ssl.SSLError as err:
                if err.args[0] == ssl.SSL_ERROR_WANT_READ:
                    self.event_state = self.READ
                elif err.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                    self.event_state = self.WRITE
                else:
                    raise
                self._manage_event_state()

    def _get_error_code(self, error_value):
        """Get the error code from the error_value accounting for Python
        version differences.

        :rtype: int

        """
        if not error_value:
            return None
        if hasattr(error_value, 'errno'):  # Python >= 2.6
            return error_value.errno
        elif error_value is not None:
            return error_value[0]  # Python <= 2.5
        return None

    def _flush_outbound(self):
        """Call the state manager who will figure out that we need to write."""
        self._manage_event_state()

    def _handle_disconnect(self):
        """Called internally when the socket is disconnected already
        """
        self._adapter_disconnect()
        self._on_connection_closed(None, True)

    def _handle_ioloop_stop(self):
        """Invoked when the connection is closed to determine if the IOLoop
        should be stopped or not.

        """
        if self.stop_ioloop_on_close and self.ioloop:
            self.ioloop.stop()
        elif self.WARN_ABOUT_IOLOOP:
            LOGGER.warning('Connection is closed but not stopping IOLoop')

    def _handle_error(self, error_value):
        """Internal error handling method. Here we expect a socket.error
        coming in and will handle different socket errors differently.

        :param int|object error_value: The inbound error

        """
        if 'timed out' in str(error_value):
            raise socket.timeout
        error_code = self._get_error_code(error_value)
        if not error_code:
            LOGGER.critical("Tried to handle an error where no error existed")
            return

        # Ok errors, just continue what we were doing before
        if error_code in self.ERRORS_TO_IGNORE:
            LOGGER.debug("Ignoring %s", error_code)
            return

        # Socket is closed, so lets just go to our handle_close method
        elif error_code in (errno.EBADF, errno.ECONNABORTED):
            LOGGER.error("Socket is closed")

        elif self.params.ssl and isinstance(error_value, ssl.SSLError):

            if error_value.args[0] == ssl.SSL_ERROR_WANT_READ:
                self.event_state = self.READ
            elif error_value.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                self.event_state = self.WRITE
            else:
                LOGGER.error("SSL Socket error on fd %d: %r",
                             self.socket.fileno(), error_value)
        elif error_code == errno.EPIPE:
            # Broken pipe, happens when connection reset
            LOGGER.error("Socket connection was broken")
        else:
            # Haven't run into this one yet, log it.
            LOGGER.error("Socket Error on fd %d: %s",
                         self.socket.fileno(), error_code)

        # Disconnect from our IOLoop and let Connection know what's up
        self._handle_disconnect()

    def _handle_events(self, fd, events, error=None, write_only=False):
        """Handle IO/Event loop events, processing them.

        :param int fd: The file descriptor for the events
        :param int events: Events from the IO/Event loop
        :param int error: Was an error specified
        :param bool write_only: Only handle write events

        """
        if not fd:
            LOGGER.error('Received events on closed socket: %d', fd)
            return

        if events & self.WRITE:
            self._handle_write()
            self._manage_event_state()

        if not write_only and (events & self.READ):
            self._handle_read()

        if write_only and (events & self.READ) and (events & self.ERROR):
            LOGGER.error('BAD libc:  Write-Only but Read+Error. '
                         'Assume socket disconnected.')
            self._handle_disconnect()

        if events & self.ERROR:
            LOGGER.error('Error event %r, %r', events, error)
            self._handle_error(error)

    def _handle_read(self):
        """Read from the socket and call our on_data_available with the data."""
        try:
            if self.params.ssl:
                data = self.socket.read(self._buffer_size)
            else:
                data = self.socket.recv(self._buffer_size)
        except socket.timeout:
            raise
        except socket.error as error:
            return self._handle_error(error)

        # Empty data, should disconnect
        if not data or data == 0:
            LOGGER.error('Read empty data, calling disconnect')
            return self._handle_disconnect()

        # Pass the data into our top level frame dispatching method
        self._on_data_available(data)
        return len(data)

    def _handle_write(self):
        """Handle any outbound buffer writes that need to take place."""
        bytes_written = 0
        if self.outbound_buffer:
            frame = self.outbound_buffer.popleft()
            try:
                self.socket.sendall(frame)
                bytes_written = len(frame)
            except socket.timeout:
                raise
            except socket.error as error:
                return self._handle_error(error)
        return bytes_written

    def _init_connection_state(self):
        """Initialize or reset all of our internal state variables for a given
        connection. If we disconnect and reconnect, all of our state needs to
        be wiped.

        """
        super(BaseConnection, self)._init_connection_state()
        self.fd = None
        self.base_events = self.READ | self.ERROR
        self.event_state = self.base_events
        self.socket = None

    def _manage_event_state(self):
        """Manage the bitmask for reading/writing/error which is used by the
        io/event handler to specify when there is an event such as a read or
        write.

        """
        if self.outbound_buffer:
            if not self.event_state & self.WRITE:
                self.event_state |= self.WRITE
                self.ioloop.update_handler(self.socket.fileno(),
                                           self.event_state)
        elif self.event_state & self.WRITE:
            self.event_state = self.base_events
            self.ioloop.update_handler(self.socket.fileno(), self.event_state)

    def _wrap_socket(self, sock):
        """Wrap the socket for connecting over SSL.

        :rtype: ssl.SSLSocket

        """
        return ssl.wrap_socket(sock,
                               do_handshake_on_connect=self.DO_HANDSHAKE,
                               **self.params.ssl_options)

########NEW FILE########
__FILENAME__ = blocking_connection
"""The blocking connection adapter module implements blocking semantics on top
of Pika's core AMQP driver. While most of the asynchronous expectations are
removed when using the blocking connection adapter, it attempts to remain true
to the asynchronous RPC nature of the AMQP protocol, supporting server sent
RPC commands.

The user facing classes in the module consist of the
:py:class:`~pika.adapters.blocking_connection.BlockingConnection`
and the :class:`~pika.adapters.blocking_connection.BlockingChannel`
classes.

"""
import os
import logging
import select
import socket
import time
import warnings
import errno
from functools import wraps

from pika import frame
from pika import callback
from pika import channel
from pika import exceptions
from pika import spec
from pika import utils
from pika.adapters import base_connection

if os.name == 'java':
    from select import cpython_compatible_select as select_function
else:
    from select import select as select_function

LOGGER = logging.getLogger(__name__)


def retry_on_eintr(f):
    @wraps(f)
    def inner(*args, **kwargs):
        while True:
            try:
                return f(*args, **kwargs)
            except select.error as e:
                if e[0] != errno.EINTR:
                    raise
    return inner


class ReadPoller(object):
    """A poller that will check to see if data is ready on the socket using
    very short timeouts to avoid having to read on the socket, speeding up the
    BlockingConnection._handle_read() method.

    """
    POLL_TIMEOUT = 10

    @retry_on_eintr
    def __init__(self, fd, poll_timeout=POLL_TIMEOUT):
        """Create a new instance of the ReadPoller which wraps poll and select
        to determine if the socket has data to read on it.

        :param int fd: The file descriptor for the socket
        :param float poll_timeout: How long to wait for events (milliseconds)

        """
        self.fd = fd
        self.poll_timeout = poll_timeout
        if hasattr(select, 'poll') and os.name != 'java':
            self.poller = select.poll()
            self.poll_events = select.POLLIN | select.POLLPRI
            self.poller.register(self.fd, self.poll_events)
        else:
            self.poller = None
            self.poll_timeout = float(poll_timeout) / 1000

    @retry_on_eintr
    def ready(self):
        """Check to see if the socket has data to read.

        :rtype: bool

        """
        if self.poller:
            events = self.poller.poll(self.poll_timeout)
            return bool(events)
        else:
            ready, unused_wri, unused_err = select_function([self.fd], [], [],
                                                            self.poll_timeout)
            return bool(ready)


class BlockingConnection(base_connection.BaseConnection):
    """The BlockingConnection creates a layer on top of Pika's asynchronous core
    providing methods that will block until their expected response has returned.
    Due to the asynchronous nature of the `Basic.Deliver` and `Basic.Return` calls
    from RabbitMQ to your application, you can still implement
    continuation-passing style asynchronous methods if you'd like to receive
    messages from RabbitMQ using
    :meth:`basic_consume <BlockingChannel.basic_consume>` or if you want  to be
    notified of a delivery failure when using
    :meth:`basic_publish <BlockingChannel.basic_publish>` .

    `Basic.Get` is a blocking call which will either return the Method Frame,
    Header Frame and Body of a message, or it will return a `Basic.GetEmpty`
    frame as the method frame.

    For more information about communicating with the blocking_connection
    adapter, be sure to check out the
    :class:`BlockingChannel <BlockingChannel>` class which implements the
    :class:`Channel <pika.channel.Channel>` based communication for the
    blocking_connection adapter.

    """
    WRITE_TO_READ_RATIO = 10
    DO_HANDSHAKE = True
    SLEEP_DURATION = 0.1
    SOCKET_CONNECT_TIMEOUT = 0.25
    SOCKET_TIMEOUT_THRESHOLD = 12
    SOCKET_TIMEOUT_CLOSE_THRESHOLD = 3
    SOCKET_TIMEOUT_MESSAGE = "Timeout exceeded, disconnected"

    def __init__(self, parameters=None):
        """Create a new instance of the Connection object.

        :param pika.connection.Parameters parameters: Connection parameters
        :raises: RuntimeError

        """
        super(BlockingConnection, self).__init__(parameters, None, False)

    def add_on_close_callback(self, callback_method_unused):
        """This is not supported in BlockingConnection. When a connection is
        closed in BlockingConnection, a pika.exceptions.ConnectionClosed
        exception will raised instead.

        :param method callback_method_unused: Unused
        :raises: NotImplementedError

        """
        raise NotImplementedError('Blocking connection will raise '
                                  'ConnectionClosed exception')

    def add_on_open_callback(self, callback_method_unused):
        """This method is not supported in BlockingConnection.

        :param method callback_method_unused: Unused
        :raises: NotImplementedError

        """
        raise NotImplementedError('Connection callbacks not supported in '
                                  'BlockingConnection')

    def add_on_open_error_callback(self, callback_method_unused,
                                   remove_default=False):
        """This method is not supported in BlockingConnection.

        A pika.exceptions.AMQPConnectionError will be raised instead.

        :param method callback_method_unused: Unused
        :raises: NotImplementedError

        """
        raise NotImplementedError('Connection callbacks not supported in '
                                  'BlockingConnection')

    def add_timeout(self, deadline, callback_method):
        """Add the callback_method to the IOLoop timer to fire after deadline
        seconds. Returns a handle to the timeout. Do not confuse with
        Tornado's timeout where you pass in the time you want to have your
        callback called. Only pass in the seconds until it's to be called.

        :param int deadline: The number of seconds to wait to call callback
        :param method callback_method: The callback method
        :rtype: str

        """

        value = {'deadline': time.time() + deadline,
                 'callback': callback_method}
        timeout_id = hash(frozenset(value.items()))
        self._timeouts[timeout_id] = value
        return timeout_id

    def channel(self, channel_number=None):
        """Create a new channel with the next available or specified channel #.

        :param int channel_number: Specify the channel number

        """
        self._channel_open = False
        if not channel_number:
            channel_number = self._next_channel_number()
        LOGGER.debug('Opening channel %i', channel_number)
        self._channels[channel_number] = BlockingChannel(self, channel_number)
        return self._channels[channel_number]

    def close(self, reply_code=200, reply_text='Normal shutdown'):
        """Disconnect from RabbitMQ. If there are any open channels, it will
        attempt to close them prior to fully disconnecting. Channels which
        have active consumers will attempt to send a Basic.Cancel to RabbitMQ
        to cleanly stop the delivery of messages prior to closing the channel.

        :param int reply_code: The code number for the close
        :param str reply_text: The text reason for the close

        """
        LOGGER.info("Closing connection (%s): %s", reply_code, reply_text)
        self._set_connection_state(self.CONNECTION_CLOSING)
        self._remove_connection_callbacks()
        if self._has_open_channels:
            self._close_channels(reply_code, reply_text)
        while self._has_open_channels:
            self.process_data_events()
        if self.socket:
            self._send_connection_close(reply_code, reply_text)
        while self.is_closing:
            self.process_data_events()
        if self.heartbeat:
            self.heartbeat.stop()
        self._remove_connection_callbacks()
        self._adapter_disconnect()

    def connect(self):
        """Invoke if trying to reconnect to a RabbitMQ server. Constructing the
        Connection object should connect on its own.

        """
        self._set_connection_state(self.CONNECTION_INIT)
        error = self._adapter_connect()
        if error:
            raise exceptions.AMQPConnectionError(error)

    def process_data_events(self):
        """Will make sure that data events are processed. Your app can
        block on this method.

        """
        try:
            if self._handle_read():
                self._socket_timeouts = 0
        except AttributeError:
            raise exceptions.ConnectionClosed()
        except socket.timeout:
            self._handle_timeout()
        self._flush_outbound()
        self.process_timeouts()

    def process_timeouts(self):
        """Process the self._timeouts event stack"""
        for timeout_id in self._timeouts.keys():
            if self._deadline_passed(timeout_id):
                self._call_timeout_method(self._timeouts.pop(timeout_id))

    def remove_timeout(self, timeout_id):
        """Remove the timeout from the IOLoop by the ID returned from
        add_timeout.

        :param str timeout_id: The id of the timeout to remove

        """
        if timeout_id in self._timeouts:
            del self._timeouts[timeout_id]

    def send_method(self, channel_number, method_frame, content=None):
        """Constructs a RPC method frame and then sends it to the broker.

        :param int channel_number: The channel number for the frame
        :param pika.object.Method method_frame: The method frame to send
        :param tuple content: If set, is a content frame, is tuple of
                              properties and body.

        """
        self._send_method(channel_number, method_frame, content)

    def sleep(self, duration):
        """A safer way to sleep than calling time.sleep() directly which will
        keep the adapter from ignoring frames sent from RabbitMQ. The
        connection will "sleep" or block the number of seconds specified in
        duration in small intervals.

        :param int duration: The time to sleep

        """
        deadline = time.time() + duration
        while time.time() < deadline:
            time.sleep(self.SLEEP_DURATION)
            self.process_data_events()

    def _adapter_connect(self):
        """Connect to the RabbitMQ broker

        :rtype: bool
        :raises: pika.Exceptions.AMQPConnectionError

        """
        # Remove the default behavior for connection errors
        self.callbacks.remove(0, self.ON_CONNECTION_ERROR)
        error = super(BlockingConnection, self)._adapter_connect()
        if error:
            raise exceptions.AMQPConnectionError(error)
        self.socket.settimeout(self.SOCKET_CONNECT_TIMEOUT)
        self._frames_written_without_read = 0
        self._socket_timeouts = 0
        self._timeouts = dict()
        self._read_poller = ReadPoller(self.socket.fileno())
        self._on_connected()
        while not self.is_open:
            self.process_data_events()
        self.socket.settimeout(self.params.socket_timeout)
        self._set_connection_state(self.CONNECTION_OPEN)

    def _adapter_disconnect(self):
        """Called if the connection is being requested to disconnect."""
        if self.socket:
            self.socket.close()
        self.socket = None
        self._check_state_on_disconnect()
        self._init_connection_state()

    def _call_timeout_method(self, timeout_value):
        """Execute the method that was scheduled to be called.

        :param dict timeout_value: The configuration for the timeout

        """
        LOGGER.debug('Invoking scheduled call of %s', timeout_value['callback'])
        timeout_value['callback']()

    def _deadline_passed(self, timeout_id):
        """Returns True if the deadline has passed for the specified timeout_id.

        :param str timeout_id: The id of the timeout to check
        :rtype: bool

        """
        if timeout_id not in self._timeouts.keys():
            return False
        return self._timeouts[timeout_id]['deadline'] <= time.time()

    def _handle_read(self):
        """If the ReadPoller says there is data to read, try adn read it in the
        _handle_read of the parent class. Once read, reset the counter that
        keeps track of how many frames have been written since the last read.

        """
        if self._read_poller.ready():
            super(BlockingConnection, self)._handle_read()
            self._frames_written_without_read = 0

    def _handle_timeout(self):
        """Invoked whenever the socket times out"""
        self._socket_timeouts += 1
        threshold = (self.SOCKET_TIMEOUT_THRESHOLD if not self.is_closing else
                     self.SOCKET_TIMEOUT_CLOSE_THRESHOLD)

        LOGGER.debug('Handling timeout %i with a threshold of %i',
                     self._socket_timeouts, threshold)
        if self.is_closing and self._socket_timeouts > threshold:
            if not self.is_closing:
                LOGGER.critical('Closing connection due to timeout')
            self._on_connection_closed(None, True)

    def _check_state_on_disconnect(self):
        """Checks closing corner cases to see why we were disconnected and if we should
        raise exceptions for the anticipated exception types.
        """
        super(BlockingConnection, self)._check_state_on_disconnect()
        if self.is_open:
            # already logged a warning in the base class, now fire an exception
            raise exceptions.ConnectionClosed()

    def _flush_outbound(self):
        """Flush the outbound socket buffer."""
        if self.outbound_buffer:
            try:
                if self._handle_write():
                    self._socket_timeouts = 0
            except socket.timeout:
                return self._handle_timeout()

    def _on_connection_closed(self, method_frame, from_adapter=False):
        """Called when the connection is closed remotely. The from_adapter value
        will be true if the connection adapter has been disconnected from
        the broker and the method was invoked directly instead of by receiving
        a Connection.Close frame.

        :param pika.frame.Method: The Connection.Close frame
        :param bool from_adapter: Called by the connection adapter
        :raises: pika.exceptions.ConnectionClosed

        """
        if self._is_connection_close_frame(method_frame):
            self.closing = (method_frame.method.reply_code,
                            method_frame.method.reply_text)
            LOGGER.warning("Disconnected from RabbitMQ at %s:%i (%s): %s",
                           self.params.host, self.params.port,
                           self.closing[0], self.closing[1])
        self._set_connection_state(self.CONNECTION_CLOSED)
        self._remove_connection_callbacks()
        if not from_adapter:
            self._adapter_disconnect()
        for channel in self._channels:
            self._channels[channel]._on_close(method_frame)
        self._remove_connection_callbacks()
        if self.closing[0] not in [0, 200]:
            raise exceptions.ConnectionClosed(*self.closing)

    def _send_frame(self, frame_value):
        """This appends the fully generated frame to send to the broker to the
        output buffer which will be then sent via the connection adapter.

        :param frame_value: The frame to write
        :type frame_value:  pika.frame.Frame|pika.frame.ProtocolHeader

        """
        super(BlockingConnection, self)._send_frame(frame_value)
        self._frames_written_without_read += 1
        if self._frames_written_without_read >= self.WRITE_TO_READ_RATIO:
            if not isinstance(frame_value, frame.Method):
                self._frames_written_without_read = 0
                self.process_data_events()


class BlockingChannel(channel.Channel):
    """The BlockingChannel implements blocking semantics for most things that
    one would use callback-passing-style for with the
    :py:class:`~pika.channel.Channel` class. In addition,
    the `BlockingChannel` class implements a :term:`generator` that allows you
    to :doc:`consume messages </examples/blocking_consumer_generator>` without
    using callbacks.

    Example of creating a BlockingChannel::

        import pika

        # Create our connection object
        connection = pika.BlockingConnection()

        # The returned object will be a blocking channel
        channel = connection.channel()

    :param BlockingConnection connection: The connection
    :param int channel_number: The channel number for this instance

    """
    NO_RESPONSE_FRAMES = ['Basic.Ack', 'Basic.Reject', 'Basic.RecoverAsync']

    def __init__(self, connection, channel_number):
        """Create a new instance of the Channel

        :param BlockingConnection connection: The connection
        :param int channel_number: The channel number for this instance

        """
        super(BlockingChannel, self).__init__(connection, channel_number)
        self.connection = connection
        self._confirmation = False
        self._force_data_events_override = None
        self._generator = None
        self._generator_messages = list()
        self._frames = dict()
        self._replies = list()
        self._wait = False
        self._received_response = False
        self.open()

    def basic_cancel(self, consumer_tag='', nowait=False):
        """This method cancels a consumer. This does not affect already
        delivered messages, but it does mean the server will not send any more
        messages for that consumer. The client may receive an arbitrary number
        of messages in between sending the cancel method and receiving the
        cancel-ok reply. It may also be sent from the server to the client in
        the event of the consumer being unexpectedly cancelled (i.e. cancelled
        for any reason other than the server receiving the corresponding
        basic.cancel from the client). This allows clients to be notified of
        the loss of consumers due to events such as queue deletion.

        :param str consumer_tag: Identifier for the consumer
        :param bool nowait: Do not expect a Basic.CancelOk response

        """
        if consumer_tag not in self._consumers:
            return
        self._cancelled.append(consumer_tag)
        replies = [(spec.Basic.CancelOk,
                   {'consumer_tag': consumer_tag})] if nowait is False else []
        self._rpc(spec.Basic.Cancel(consumer_tag=consumer_tag,
                                             nowait=nowait),
                  self._on_cancelok, replies)

    def basic_get(self, queue=None, no_ack=False):
        """Get a single message from the AMQP broker. The callback method
        signature should have 3 parameters: The method frame, header frame and
        the body, like the consumer callback for Basic.Consume.

        :param queue: The queue to get a message from
        :type queue: str or unicode
        :param bool no_ack: Tell the broker to not expect a reply
        :rtype: (None, None, None)|(spec.Basic.Get,
                                    spec.Basic.Properties,
                                    str or unicode)

        """
        self._response = None
        self._send_method(spec.Basic.Get(queue=queue,
                                         no_ack=no_ack))
        while not self._response:
            self.connection.process_data_events()
        if isinstance(self._response[0], spec.Basic.GetEmpty):
            return None, None, None
        return self._response[0], self._response[1], self._response[2]

    def basic_publish(self, exchange, routing_key, body,
                      properties=None, mandatory=False, immediate=False):
        """Publish to the channel with the given exchange, routing key and body.
        Returns a boolean value indicating the success of the operation. For 
        more information on basic_publish and what the parameters do, see:

        http://www.rabbitmq.com/amqp-0-9-1-reference.html#basic.publish

        :param exchange: The exchange to publish to
        :type exchange: str or unicode
        :param routing_key: The routing key to bind on
        :type routing_key: str or unicode
        :param body: The message body
        :type body: str or unicode
        :param pika.spec.Properties properties: Basic.properties
        :param bool mandatory: The mandatory flag
        :param bool immediate: The immediate flag

        """
        if not self.is_open:
            raise exceptions.ChannelClosed()
        if immediate:
            LOGGER.warning('The immediate flag is deprecated in RabbitMQ')
        properties = properties or spec.BasicProperties()

        if mandatory:
            self._response = None

        if isinstance(body, unicode):
            body = body.encode('utf-8')

        if self._confirmation:
            response = self._rpc(spec.Basic.Publish(exchange=exchange,
                                                    routing_key=routing_key,
                                                    mandatory=mandatory,
                                                    immediate=immediate),
                                 None,
                                 [spec.Basic.Ack,
                                  spec.Basic.Nack],
                                 (properties, body))
            if mandatory and self._response:
                response = self._response[0]
                LOGGER.warning('Message was returned (%s): %s',
                               response.reply_code,
                               response.reply_text)
                return False

            if isinstance(response.method, spec.Basic.Ack):
                return True
            elif isinstance(response.method, spec.Basic.Nack):
                return False
            else:
                raise ValueError('Unexpected frame type: %r', response)
        else:
            self._send_method(spec.Basic.Publish(exchange=exchange,
                                                 routing_key=routing_key,
                                                 mandatory=mandatory,
                                                 immediate=immediate),
                              (properties, body), False)
            if mandatory:
                if self._response:
                    response = self._response[0]
                    LOGGER.warning('Message was returned (%s): %s',
                                   response.reply_code,
                                   response.reply_text)
                    return False
                return True

    def basic_qos(self, prefetch_size=0, prefetch_count=0, all_channels=False):
        """Specify quality of service. This method requests a specific quality
        of service. The QoS can be specified for the current channel or for all
        channels on the connection. The client can request that messages be sent
        in advance so that when the client finishes processing a message, the
        following message is already held locally, rather than needing to be
        sent down the channel. Prefetching gives a performance improvement.

        :param int prefetch_size:  This field specifies the prefetch window
                                   size. The server will send a message in
                                   advance if it is equal to or smaller in size
                                   than the available prefetch size (and also
                                   falls into other prefetch limits). May be set
                                   to zero, meaning "no specific limit",
                                   although other prefetch limits may still
                                   apply. The prefetch-size is ignored if the
                                   no-ack option is set.
        :param int prefetch_count: Specifies a prefetch window in terms of whole
                                   messages. This field may be used in
                                   combination with the prefetch-size field; a
                                   message will only be sent in advance if both
                                   prefetch windows (and those at the channel
                                   and connection level) allow it. The
                                   prefetch-count is ignored if the no-ack
                                   option is set.
        :param bool all_channels: Should the QoS apply to all channels

        """
        self._rpc(spec.Basic.Qos(prefetch_size, prefetch_count, all_channels),
                  None, [spec.Basic.QosOk])

    def basic_recover(self, requeue=False):
        """This method asks the server to redeliver all unacknowledged messages
        on a specified channel. Zero or more messages may be redelivered. This
        method replaces the asynchronous Recover.

        :param bool requeue: If False, the message will be redelivered to the
                             original recipient. If True, the server will
                             attempt to requeue the message, potentially then
                             delivering it to an alternative subscriber.

        """
        self._rpc(spec.Basic.Recover(requeue), None, [spec.Basic.RecoverOk])

    def confirm_delivery(self, nowait=False):
        """Turn on Confirm mode in the channel.

        For more information see:
            http://www.rabbitmq.com/extensions.html#confirms

        :param bool nowait: Do not send a reply frame (Confirm.SelectOk)

        """
        if (not self.connection.publisher_confirms or
            not self.connection.basic_nack):
            raise exceptions.MethodNotImplemented('Not Supported on Server')
        self._confirmation = True
        replies = [spec.Confirm.SelectOk] if nowait is False else []
        self._rpc(spec.Confirm.Select(nowait), None, replies)
        self.connection.process_data_events()

    def cancel(self):
        """Cancel the consumption of a queue, rejecting all pending messages.
        This should only work with the generator based BlockingChannel.consume
        method. If you're looking to cancel a consumer issues with
        BlockingChannel.basic_consume then you should call
        BlockingChannel.basic_cancel.

        :return int: The number of messages requeued by Basic.Nack

        """
        messages = 0
        self.basic_cancel(self._generator)
        if self._generator_messages:
            # Get the last item
            (method, properties, body) = self._generator_messages.pop()
            messages = len(self._generator_messages)
            LOGGER.info('Requeueing %i messages with delivery tag %s',
                        messages, method.delivery_tag)
            self.basic_nack(method.delivery_tag, multiple=True, requeue=True)
            self.connection.process_data_events()
        self._generator = None
        self._generator_messages = list()
        return messages

    def close(self, reply_code=0, reply_text="Normal Shutdown"):
        """Will invoke a clean shutdown of the channel with the AMQP Broker.

        :param int reply_code: The reply code to close the channel with
        :param str reply_text: The reply text to close the channel with

        """

        LOGGER.info('Channel.close(%s, %s)', reply_code, reply_text)
        if not self.is_open:
            raise exceptions.ChannelClosed()

        # Cancel the generator if it's running
        if self._generator:
            self.cancel()

        # If there are any consumers, cancel them as well
        if self._consumers:
            LOGGER.debug('Cancelling %i consumers', len(self._consumers))
            for consumer_tag in self._consumers.keys():
                self.basic_cancel(consumer_tag=consumer_tag)
        self._set_state(self.CLOSING)
        self._rpc(spec.Channel.Close(reply_code, reply_text, 0, 0),
                  None,
                  [spec.Channel.CloseOk])
        self._set_state(self.CLOSED)
        self._cleanup()

    def consume(self, queue, no_ack=False, exclusive=False):
        """Blocking consumption of a queue instead of via a callback. This
        method is a generator that returns messages a tuple of method,
        properties, and body.

        Example:

            for method, properties, body in channel.consume('queue'):
                print body
                channel.basic_ack(method.delivery_tag)

        You should call BlockingChannel.cancel() when you escape out of the
        generator loop. Also note this turns on forced data events to make
        sure that any acked messages actually get acked.

        :param queue: The queue name to consume
        :type queue: str or unicode
        :param no_ack: Tell the broker to not expect a response
        :type no_ack: bool
        :param exclusive: Don't allow other consumers on the queue
        :type exclusive: bool
        :rtype: tuple(spec.Basic.Deliver, spec.BasicProperties, str or unicode)

        """
        LOGGER.debug('Forcing data events on')
        if not self._generator:
            LOGGER.debug('Issuing Basic.Consume')
            self._generator = self.basic_consume(self._generator_callback,
                                                 queue,
                                                 no_ack,
                                                 exclusive)
        while True:
            if self._generator_messages:
                yield self._generator_messages.pop(0)
            self.connection.process_data_events()

    def force_data_events(self, enable):
        """Turn on and off forcing the blocking adapter to stop and look to see
        if there are any frames from RabbitMQ in the read buffer. By default
        the BlockingChannel will check for a read after every RPC command which
        can cause performance to degrade in scenarios where you do not care if
        RabbitMQ is trying to send RPC commands to your client connection.

        Examples of RPC commands of this sort are:

        - Heartbeats
        - Connection.Close
        - Channel.Close
        - Basic.Return
        - Basic.Ack and Basic.Nack when using delivery confirmations

        Turning off forced data events can be a bad thing and prevents your
        client from properly communicating with RabbitMQ. Forced data events
        were added in 0.9.6 to enforce proper channel behavior when
        communicating with RabbitMQ.

        Note that the BlockingConnection also has the constant
        WRITE_TO_READ_RATIO which forces the connection to stop and try and
        read after writing the number of frames specified in the constant.
        This is a way to force the client to received these types of frames
        in a very publish/write IO heavy workload.

        :param bool enable: Set to False to disable

        """
        self._force_data_events_override = enable

    def exchange_bind(self, destination=None, source=None, routing_key='',
                      nowait=False, arguments=None):
        """Bind an exchange to another exchange.

        :param destination: The destination exchange to bind
        :type destination: str or unicode
        :param source: The source exchange to bind to
        :type source: str or unicode
        :param routing_key: The routing key to bind on
        :type routing_key: str or unicode
        :param bool nowait: Do not wait for an Exchange.BindOk
        :param dict arguments: Custom key/value pair arguments for the binding

        """
        replies = [spec.Exchange.BindOk] if nowait is False else []
        return self._rpc(spec.Exchange.Bind(0, destination, source,
                                            routing_key, nowait,
                                            arguments or dict()), None, replies)

    def exchange_declare(self, exchange=None,
                         exchange_type='direct', passive=False, durable=False,
                         auto_delete=False, internal=False, nowait=False,
                         arguments=None, type=None):
        """This method creates an exchange if it does not already exist, and if
        the exchange exists, verifies that it is of the correct and expected
        class.

        If passive set, the server will reply with Declare-Ok if the exchange
        already exists with the same name, and raise an error if not and if the
        exchange does not already exist, the server MUST raise a channel
        exception with reply code 404 (not found).

        :param exchange: The exchange name consists of a non-empty sequence of
                          these characters: letters, digits, hyphen, underscore,
                          period, or colon.
        :type exchange: str or unicode
        :param str exchange_type: The exchange type to use
        :param bool passive: Perform a declare or just check to see if it exists
        :param bool durable: Survive a reboot of RabbitMQ
        :param bool auto_delete: Remove when no more queues are bound to it
        :param bool internal: Can only be published to by other exchanges
        :param bool nowait: Do not expect an Exchange.DeclareOk response
        :param dict arguments: Custom key/value pair arguments for the exchange
        :param str type: The deprecated exchange type parameter

        """
        if type is not None:
            warnings.warn('type is deprecated, use exchange_type instead',
                          DeprecationWarning)
            if exchange_type == 'direct' and type != exchange_type:
                exchange_type = type
        replies = [spec.Exchange.DeclareOk] if nowait is False else []
        return self._rpc(spec.Exchange.Declare(0, exchange, exchange_type,
                                               passive, durable, auto_delete,
                                               internal, nowait,
                                               arguments or dict()),
                         None, replies)

    def exchange_delete(self, exchange=None, if_unused=False, nowait=False):
        """Delete the exchange.

        :param exchange: The exchange name
        :type exchange: str or unicode
        :param bool if_unused: only delete if the exchange is unused
        :param bool nowait: Do not wait for an Exchange.DeleteOk

        """
        replies = [spec.Exchange.DeleteOk] if nowait is False else []
        return self._rpc(spec.Exchange.Delete(0, exchange, if_unused, nowait),
                         None, replies)

    def exchange_unbind(self, destination=None, source=None, routing_key='',
                        nowait=False, arguments=None):
        """Unbind an exchange from another exchange.

        :param destination: The destination exchange to unbind
        :type destination: str or unicode
        :param source: The source exchange to unbind from
        :type source: str or unicode
        :param routing_key: The routing key to unbind
        :type routing_key: str or unicode
        :param bool nowait: Do not wait for an Exchange.UnbindOk
        :param dict arguments: Custom key/value pair arguments for the binding

        """
        replies = [spec.Exchange.UnbindOk] if nowait is False else []
        return self._rpc(spec.Exchange.Unbind(0, destination, source,
                                              routing_key, nowait, arguments),
                         None, replies)

    def open(self):
        """Open the channel"""
        self._set_state(self.OPENING)
        self._add_callbacks()
        self._rpc(spec.Channel.Open(), self._on_openok, [spec.Channel.OpenOk])

    def queue_bind(self, queue, exchange, routing_key=None, nowait=False,
                   arguments=None):
        """Bind the queue to the specified exchange

        :param queue: The queue to bind to the exchange
        :type queue: str or unicode
        :param exchange: The source exchange to bind to
        :type exchange: str or unicode
        :param routing_key: The routing key to bind on
        :type routing_key: str or unicode
        :param bool nowait: Do not wait for a Queue.BindOk
        :param dict arguments: Custom key/value pair arguments for the binding

        """
        replies = [spec.Queue.BindOk] if nowait is False else []
        if routing_key is None:
            routing_key = queue
        return self._rpc(spec.Queue.Bind(0, queue, exchange, routing_key,
                                         nowait, arguments or dict()),
                         None, replies)

    def queue_declare(self, queue='', passive=False, durable=False,
                      exclusive=False, auto_delete=False, nowait=False,
                      arguments=None):
        """Declare queue, create if needed. This method creates or checks a
        queue. When creating a new queue the client can specify various
        properties that control the durability of the queue and its contents,
        and the level of sharing for the queue.

        Leave the queue name empty for a auto-named queue in RabbitMQ

        :param queue: The queue name
        :type queue: str or unicode
        :param bool passive: Only check to see if the queue exists
        :param bool durable: Survive reboots of the broker
        :param bool exclusive: Only allow access by the current connection
        :param bool auto_delete: Delete after consumer cancels or disconnects
        :param bool nowait: Do not wait for a Queue.DeclareOk
        :param dict arguments: Custom key/value arguments for the queue

        """
        condition = (spec.Queue.DeclareOk,
                     {'queue': queue}) if queue else spec.Queue.DeclareOk
        replies = [condition] if nowait is False else []
        return self._rpc(spec.Queue.Declare(0, queue, passive, durable,
                                            exclusive, auto_delete, nowait,
                                            arguments or dict()),
                         None, replies)

    def queue_delete(self, queue='', if_unused=False, if_empty=False,
                     nowait=False):
        """Delete a queue from the broker.

        :param queue: The queue to delete
        :type queue: str or unicode
        :param bool if_unused: only delete if it's unused
        :param bool if_empty: only delete if the queue is empty
        :param bool nowait: Do not wait for a Queue.DeleteOk

        """
        replies = [spec.Queue.DeleteOk] if nowait is False else []
        return self._rpc(spec.Queue.Delete(0, queue, if_unused, if_empty,
                                           nowait), None, replies)

    def queue_purge(self, queue='', nowait=False):
        """Purge all of the messages from the specified queue

        :param queue: The queue to purge
        :type  queue: str or unicode
        :param bool nowait: Do not expect a Queue.PurgeOk response

        """
        replies = [spec.Queue.PurgeOk] if nowait is False else []
        return self._rpc(spec.Queue.Purge(0, queue, nowait), None, replies)

    def queue_unbind(self, queue='', exchange=None, routing_key=None,
                     arguments=None):
        """Unbind a queue from an exchange.

        :param queue: The queue to unbind from the exchange
        :type queue: str or unicode
        :param exchange: The source exchange to bind from
        :type exchange: str or unicode
        :param routing_key: The routing key to unbind
        :type routing_key: str or unicode
        :param dict arguments: Custom key/value pair arguments for the binding

        """
        if routing_key is None:
            routing_key = queue
        return self._rpc(spec.Queue.Unbind(0, queue, exchange, routing_key,
                                           arguments or dict()), None,
                         [spec.Queue.UnbindOk])

    def start_consuming(self):
        """Starts consuming from registered callbacks."""
        while len(self._consumers):
            self.connection.process_data_events()

    def stop_consuming(self, consumer_tag=None):
        """Sends off the Basic.Cancel to let RabbitMQ know to stop consuming and
        sets our internal state to exit out of the basic_consume.

        """
        if consumer_tag:
            self.basic_cancel(consumer_tag)
        else:
            for consumer_tag in self._consumers.keys():
                self.basic_cancel(consumer_tag)
        self.wait = True

    def tx_commit(self):
        """Commit a transaction."""
        return self._rpc(spec.Tx.Commit(), None, [spec.Tx.CommitOk])

    def tx_rollback(self):
        """Rollback a transaction."""
        return self._rpc(spec.Tx.Rollback(), None, [spec.Tx.RollbackOk])

    def tx_select(self):
        """Select standard transaction mode. This method sets the channel to use
        standard transactions. The client must use this method at least once on
        a channel before using the Commit or Rollback methods.

        """
        return self._rpc(spec.Tx.Select(), None, [spec.Tx.SelectOk])

    # Internal methods

    def _add_reply(self, reply):
        reply = callback._name_or_value(reply)
        self._replies.append(reply)

    def _add_callbacks(self):
        """Add callbacks for when the channel opens and closes."""
        self.connection.callbacks.add(self.channel_number,
                                      spec.Channel.Close,
                                      self._on_close)
        self.callbacks.add(self.channel_number,
                           spec.Basic.GetEmpty,
                           self._on_getempty,
                           False)
        self.callbacks.add(self.channel_number,
                           spec.Basic.Cancel,
                           self._on_cancel,
                           False)
        self.connection.callbacks.add(self.channel_number,
                                      spec.Channel.CloseOk,
                                      self._on_rpc_complete)

    def _generator_callback(self, unused, method, properties, body):
        """Called when a message is received from RabbitMQ and appended to the
        list of messages to be returned when a message is received by RabbitMQ.

        :param pika.spec.Basic.Deliver: The method frame received
        :param pika.spec.BasicProperties: The  message properties
        :param body: The body received
        :type body: str or unicode

        """
        self._generator_messages.append((method, properties, body))
        LOGGER.debug('%i pending messages', len(self._generator_messages))

    def _on_cancel(self, method_frame):
        """Raises a ConsumerCanceled exception after processing the frame


        :param pika.frame.Method method_frame: The method frame received

        """
        super(BlockingChannel, self)._on_cancel(method_frame)
        raise exceptions.ConsumerCancelled(method_frame.method)

    def _on_getok(self, method_frame, header_frame, body):
        """Called in reply to a Basic.Get when there is a message.

        :param pika.frame.Method method_frame: The method frame received
        :param pika.frame.Header header_frame: The header frame received
        :param body: The body received
        :type body: str or unicode

        """
        self._received_response = True
        self._response = method_frame.method, header_frame.properties, body

    def _on_getempty(self, frame):
        self._received_response = True
        self._response = frame.method, None, None

    def _on_close(self, method_frame):
        LOGGER.warning('Received Channel.Close, closing: %r', method_frame)
        if not self.connection.is_closed:
            self._send_method(spec.Channel.CloseOk(), None, False)
        self._set_state(self.CLOSED)
        self._cleanup()
        self._generator_messages = list()
        self._generator = None
        if method_frame is None:
            raise exceptions.ChannelClosed(0, 'Not specified')
        else:
            raise exceptions.ChannelClosed(method_frame.method.reply_code,
                                           method_frame.method.reply_text)

    def _on_openok(self, method_frame):
        """Open the channel by sending the RPC command and remove the reply
        from the stack of replies.

        """
        super(BlockingChannel, self)._on_openok(method_frame)
        self._remove_reply(method_frame)

    def _on_return(self, method_frame, header_frame, body):
        """Called when a Basic.Return is received from publishing

        :param pika.frame.Method method_frame: The method frame received
        :param pika.frame.Header header_frame: The header frame received
        :param body: The body received
        :type body: str or unicode

        """
        self._received_response = True
        self._response = method_frame.method, header_frame.properties, body

    def _on_rpc_complete(self, frame):
        key = callback._name_or_value(frame)
        self._replies.append(key)
        self._frames[key] = frame
        self._received_response = True

    def _process_replies(self, replies, callback):
        """Process replies from RabbitMQ, looking in the stack of callback
        replies for a match. Will optionally call callback prior to
        returning the frame_value.

        :param list replies: The reply handles to iterate
        :param method callback: The method to optionally call
        :rtype: pika.frame.Frame

        """
        for reply in self._replies:
            if reply in replies:
                frame_value = self._frames[reply]
                self._received_response = True
                if callback:
                    callback(frame_value)
                del(self._frames[reply])
                return frame_value

    def _remove_reply(self, frame):
        key = callback._name_or_value(frame)
        if key in self._replies:
            self._replies.remove(key)

    def _rpc(self, method_frame, callback=None, acceptable_replies=None,
             content=None, force_data_events=True):
        """Make an RPC call for the given callback, channel number and method.
        acceptable_replies lists out what responses we'll process from the
        server with the specified callback.

        :param pika.amqp_object.Method method_frame: The method frame to call
        :param method callback: The callback for the RPC response
        :param list acceptable_replies: The replies this RPC call expects
        :param tuple content: Properties and Body for content frames
        :param bool force_data_events: Call process data events before reply
        :rtype: pika.frame.Method

        """
        if self.is_closed:
            raise exceptions.ChannelClosed
        self._validate_acceptable_replies(acceptable_replies)
        self._validate_callback(callback)
        replies = list()
        for reply in acceptable_replies or list():
            if isinstance(reply, tuple):
                reply, arguments = reply
            else:
                arguments = None
            prefix, key = self.callbacks.add(self.channel_number,
                                             reply,
                                             self._on_rpc_complete,
                                             arguments=arguments)
            replies.append(key)
        self._send_method(method_frame, content,
                          self._wait_on_response(method_frame))
        if force_data_events and self._force_data_events_override is not False:
            self.connection.process_data_events()
        return self._process_replies(replies, callback)

    def _send_method(self, method_frame, content=None, wait=False):
        """Shortcut wrapper to send a method through our connection, passing in
        our channel number.

        :param pika.amqp_object.Method method_frame: The method frame to send
        :param content: The content to send
        :type content: tuple
        :param bool wait: Wait for a response

        """
        self.wait = wait
        prev_received_response = self._received_response
        self._received_response = False
        self.connection.send_method(self.channel_number, method_frame, content)
        while wait and not self._received_response:
            try:
                self.connection.process_data_events()
            except exceptions.AMQPConnectionError:
                break
        self._received_response = prev_received_response

    def _validate_acceptable_replies(self, acceptable_replies):
        """Validate the list of acceptable replies

        :param acceptable_replies:
        :raises: TypeError

        """
        if acceptable_replies and not isinstance(acceptable_replies, list):
            raise TypeError("acceptable_replies should be list or None, is %s",
                            type(acceptable_replies))

    def _validate_callback(self, callback):
        """Validate the value passed in is a method or function.

        :param method callback callback: The method to validate
        :raises: TypeError

        """
        if (callback is not None and
            not utils.is_callable(callback)):
            raise TypeError("Callback should be a function or method, is %s",
                            type(callback))

    def _wait_on_response(self, method_frame):
        """Returns True if the rpc call should wait on a response.

        :param pika.frame.Method method_frame: The frame to check

        """
        return method_frame.NAME not in self.NO_RESPONSE_FRAMES

########NEW FILE########
__FILENAME__ = libev_connection
"""Use pika with the libev IOLoop via pyev"""
import pyev
import signal
import array
import logging
import warnings
from collections import deque

from pika.adapters.base_connection import BaseConnection

LOGGER = logging.getLogger(__name__)

global_sigint_watcher, global_sigterm_watcher = None, None


class LibevConnection(BaseConnection):
    """The LibevConnection runs on the libev IOLoop. If you're running the
    connection in a web app, make sure you set stop_ioloop_on_close to False,
    which is the default behavior for this adapter, otherwise the web app
    will stop taking requests.

    You should be familiar with pyev and libev to use this adapter, esp.
    with regard to the use of libev ioloops.

    If an on_signal_callback method is provided, the adapter creates signal
    watchers the first time; subsequent instantiations with a provided method
    reuse the same watchers but will call the new method upon receiving a
    signal. See pyev/libev signal handling to understand why this is done.

    :param pika.connection.Parameters parameters: Connection parameters
    :param on_open_callback: The method to call when the connection is open
    :type on_open_callback: method
    :param on_open_error_callback: Method to call if the connection can't
                                   be opened
    :type on_open_error_callback: method
    :param bool stop_ioloop_on_close: Call ioloop.stop() if disconnected
    :param custom_ioloop: Override using the default_loop in libev
    :param on_signal_callback: Method to call if SIGINT or SIGTERM occur
    :type on_signal_callback: method

    """
    WARN_ABOUT_IOLOOP = True

    # use static arrays to translate masks between pika and libev
    _PIKA_TO_LIBEV_ARRAY = array.array('i',
                                       [0] * ((BaseConnection.READ |
                                               BaseConnection.WRITE |
                                               BaseConnection.ERROR) + 1))

    _PIKA_TO_LIBEV_ARRAY[BaseConnection.READ] = pyev.EV_READ
    _PIKA_TO_LIBEV_ARRAY[BaseConnection.WRITE] = pyev.EV_WRITE

    _PIKA_TO_LIBEV_ARRAY[BaseConnection.READ |
                         BaseConnection.WRITE] = pyev.EV_READ | pyev.EV_WRITE

    _PIKA_TO_LIBEV_ARRAY[BaseConnection.READ |
                         BaseConnection.ERROR] = pyev.EV_READ

    _PIKA_TO_LIBEV_ARRAY[BaseConnection.WRITE |
                         BaseConnection.ERROR] = pyev.EV_WRITE

    _PIKA_TO_LIBEV_ARRAY[BaseConnection.READ |
                         BaseConnection.WRITE |
                         BaseConnection.ERROR] = pyev.EV_READ | pyev.EV_WRITE

    _LIBEV_TO_PIKA_ARRAY = array.array('i',
                                       [0] * ((pyev.EV_READ |
                                               pyev.EV_WRITE) + 1))

    _LIBEV_TO_PIKA_ARRAY[pyev.EV_READ] = BaseConnection.READ
    _LIBEV_TO_PIKA_ARRAY[pyev.EV_WRITE] = BaseConnection.WRITE

    _LIBEV_TO_PIKA_ARRAY[pyev.EV_READ | pyev.EV_WRITE] = \
        BaseConnection.READ | BaseConnection.WRITE

    def __init__(self,
                 parameters=None,
                 on_open_callback=None,
                 on_open_error_callback=None,
                 on_close_callback=None,
                 stop_ioloop_on_close=False,
                 custom_ioloop=None,
                 on_signal_callback=None):
        """Create a new instance of the LibevConnection class, connecting
        to RabbitMQ automatically

        :param pika.connection.Parameters parameters: Connection parameters
        :param on_open_callback: The method to call when the connection is open
        :type on_open_callback: method
        :param on_open_error_callback: Method to call if the connection cannot
                                       be opened
        :type on_open_error_callback: method
        :param bool stop_ioloop_on_close: Call ioloop.stop() if disconnected
        :param custom_ioloop: Override using the default IOLoop in libev
        :param on_signal_callback: Method to call if SIGINT or SIGTERM occur
        :type on_signal_callback: method

        """
        if custom_ioloop:
            self.ioloop = custom_ioloop
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                self.ioloop = pyev.default_loop()

        self.async = None
        self._on_signal_callback = on_signal_callback
        self._io_watcher = None
        self._active_timers = {}
        self._stopped_timers = deque()

        super(LibevConnection, self).__init__(parameters,
                                              on_open_callback,
                                              on_open_error_callback,
                                              on_close_callback,
                                              self.ioloop,
                                              stop_ioloop_on_close)

    def _adapter_connect(self):
        """Connect to the remote socket, adding the socket to the IOLoop if
        connected

        :rtype: bool

        """
        LOGGER.debug('init io and signal watchers if any')
        # reuse existing signal watchers, can only be declared for 1 ioloop
        global global_sigint_watcher, global_sigterm_watcher
        error = super(LibevConnection, self)._adapter_connect()

        if not error:
            if self._on_signal_callback and not global_sigterm_watcher:
                global_sigterm_watcher = \
                    self.ioloop.signal(signal.SIGTERM,
                                       self._handle_sigterm)

            if self._on_signal_callback and not global_sigint_watcher:
                global_sigint_watcher = self.ioloop.signal(signal.SIGINT,
                                                           self._handle_sigint)

            if not self._io_watcher:
                self._io_watcher = \
                    self.ioloop.io(self.socket.fileno(),
                                   self._PIKA_TO_LIBEV_ARRAY[self.event_state],
                                   self._handle_events)

            self.async = pyev.Async(self.ioloop, self._handle_events)
            if self._on_signal_callback:
                global_sigterm_watcher.start()
            if self._on_signal_callback:
                global_sigint_watcher.start()
            self._io_watcher.start()

        return error

    def _init_connection_state(self):
        """Initialize or reset all of our internal state variables for a given
        connection. If we disconnect and reconnect, all of our state needs to
        be wiped.

        """
        for timer in self._active_timers:
            self.remove_timeout(timer)
        if global_sigint_watcher:
            global_sigint_watcher.stop()
        if global_sigterm_watcher:
            global_sigterm_watcher.stop()
        if self._io_watcher:
            self._io_watcher.stop()
        super(LibevConnection, self)._init_connection_state()

    def _handle_sigint(self, signal_watcher, libev_events):
        """If an on_signal_callback has been defined, call it returning the
        string 'SIGINT'.

        """
        LOGGER.debug('SIGINT')
        self._on_signal_callback('SIGINT')

    def _handle_sigterm(self, signal_watcher, libev_events):
        """If an on_signal_callback has been defined, call it returning the
        string 'SIGTERM'.

        """
        LOGGER.debug('SIGTERM')
        self._on_signal_callback('SIGTERM')

    def _handle_events(self, io_watcher, libev_events, **kwargs):
        """Handle IO events by efficiently translating to BaseConnection
        events and calling super.

        """
        super(LibevConnection,
              self)._handle_events(io_watcher.fd,
                                   self._LIBEV_TO_PIKA_ARRAY[libev_events],
                                   **kwargs)

    def _reset_io_watcher(self):
        """Reset the IO watcher; retry as necessary
        
        """
        self._io_watcher.stop()
        
        retries = 0
        while True:
            try:
                self._io_watcher.set(
                    self._io_watcher.fd,
                    self._PIKA_TO_LIBEV_ARRAY[self.event_state]
                )
                
                break
            except: # sometimes the stop() doesn't complete in time
                if retries > 5: raise
                self._io_watcher.stop() # so try it again
                retries += 1
                
        self._io_watcher.start()

    def _manage_event_state(self):
        """Manage the bitmask for reading/writing/error which is used by the
        io/event handler to specify when there is an event such as a read or
        write.

        """
        if self.outbound_buffer:
            if not self.event_state & self.WRITE:
                self.event_state |= self.WRITE
                self._reset_io_watcher()
        elif self.event_state & self.WRITE:
            self.event_state = self.base_events
            self._reset_io_watcher()

    def _timer_callback(self, timer, libev_events):
        """Manage timer callbacks indirectly."""
        if timer in self._active_timers:
            (callback_method,
             callback_timeout,
             kwargs) = self._active_timers[timer]

            if callback_timeout:
                callback_method(timeout=timer, **kwargs)
            else:
                callback_method(**kwargs)

            self.remove_timeout(timer)
        else:
            LOGGER.warning('Timer callback_method not found')

    def _get_timer(self, deadline):
        """Get a timer from the pool or allocate a new one."""
        if self._stopped_timers:
            timer = self._stopped_timers.pop()
            timer.set(deadline, 0.0)
        else:
            timer = self.ioloop.timer(deadline, 0.0, self._timer_callback)

        return timer

    def add_timeout(self, deadline, callback_method,
                    callback_timeout=False, **callback_kwargs):
        """Add the callback_method indirectly to the IOLoop timer to fire
         after deadline seconds. Returns the timer handle.

        :param int deadline: The number of seconds to wait to call callback
        :param method callback_method: The callback method
        :param callback_timeout: Whether timeout kwarg is passed on callback
        :type callback_timeout: boolean
        :param kwargs callback_kwargs: additional kwargs to pass on callback
        :rtype: timer instance handle.

        """
        LOGGER.debug('deadline: {0}'.format(deadline))
        timer = self._get_timer(deadline)
        self._active_timers[timer] = (callback_method,
                                      callback_timeout,
                                      callback_kwargs)
        timer.start()
        return timer

    def remove_timeout(self, timer):
        """Remove the timer from the IOLoop using the handle returned from
        add_timeout.

        param: timer instance handle

        """
        LOGGER.debug('stop')
        self._active_timers.pop(timer, None)
        timer.stop()
        self._stopped_timers.append(timer)

    def _create_and_connect_to_socket(self, sock_addr_tuple):
        """Call super and then set the socket to nonblocking."""
        result = super(LibevConnection,
                       self)._create_and_connect_to_socket(sock_addr_tuple)
        if result:
            self.socket.setblocking(0)
        return result

########NEW FILE########
__FILENAME__ = select_connection
"""A connection adapter that tries to use the best polling method for the
platform pika is running on.

"""
import logging
import select
import time

from pika.adapters.base_connection import BaseConnection

LOGGER = logging.getLogger(__name__)

# One of select, epoll, kqueue or poll
SELECT_TYPE = None

# Use epoll's constants to keep life easy
READ = 0x0001
WRITE = 0x0004
ERROR = 0x0008


class SelectConnection(BaseConnection):
    """An asynchronous connection adapter that attempts to use the fastest
    event loop adapter for the given platform.

    """

    def __init__(self,
                 parameters=None,
                 on_open_callback=None,
                 on_open_error_callback=None,
                 on_close_callback=None,
                 stop_ioloop_on_close=True):
        """Create a new instance of the Connection object.

        :param pika.connection.Parameters parameters: Connection parameters
        :param method on_open_callback: Method to call on connection open
        :param on_open_error_callback: Method to call if the connection cant
                                       be opened
        :type on_open_error_callback: method
        :param method on_close_callback: Method to call on connection close
        :param bool stop_ioloop_on_close: Call ioloop.stop() if disconnected
        :raises: RuntimeError

        """
        ioloop = IOLoop(self._manage_event_state)
        super(SelectConnection, self).__init__(parameters,
                                               on_open_callback,
                                               on_open_error_callback,
                                               on_close_callback,
                                               ioloop,
                                               stop_ioloop_on_close)

    def _adapter_connect(self):
        """Connect to the RabbitMQ broker, returning True on success, False
        on failure.

        :rtype: bool

        """
        error = super(SelectConnection, self)._adapter_connect()
        if not error:
            self.ioloop.start_poller(self._handle_events,
                                     self.event_state,
                                     self.socket.fileno())
        return error

    def _flush_outbound(self):
        """Call the state manager who will figure out that we need to write then
        call the poller's poll function to force it to process events.

        """
        self.ioloop.poller._manage_event_state()
        # Force our poller to come up for air, but in write only mode
        # write only mode prevents messages from coming in and kicking off
        # events through the consumer
        self.ioloop.poller.poll(write_only=True)


class IOLoop(object):
    """Singlton wrapper that decides which type of poller to use, creates an
    instance of it in start_poller and keeps the invoking application in a
    blocking state by calling the pollers start method. Poller should keep
    looping until IOLoop.instance().stop() is called or there is a socket
    error.

    Also provides a convenient pass-through for add_timeout and set_events

    """
    def __init__(self, state_manager):
        """Create an instance of the IOLoop object.

        :param method state_manager: The method to manage state

        """
        self.poller = None
        self._manage_event_state = state_manager

    def add_timeout(self, deadline, callback_method):
        """Add the callback_method to the IOLoop timer to fire after deadline
        seconds. Returns a handle to the timeout. Do not confuse with
        Tornado's timeout where you pass in the time you want to have your
        callback called. Only pass in the seconds until it's to be called.

        :param int deadline: The number of seconds to wait to call callback
        :param method callback_method: The callback method
        :rtype: str

        """
        if not self.poller:
            time.sleep(deadline)
            return callback_method()
        return self.poller.add_timeout(deadline, callback_method)

    @property
    def poller_type(self):
        """Return the type of poller.

        :rtype: str

        """
        return self.poller.__class__.__name__

    def remove_timeout(self, timeout_id):
        """Remove a timeout if it's still in the timeout stack of the poller

        :param str timeout_id: The timeout id to remove

        """
        self.poller.remove_timeout(timeout_id)

    def start(self):
        """Start the IOLoop, waiting for a Poller to take over."""
        LOGGER.debug('Starting IOLoop')
        self.poller.open = True
        while not self.poller:
            time.sleep(SelectPoller.TIMEOUT)
        self.poller.start()
        self.poller.flush_pending_timeouts()

    def start_poller(self, handler, events, fileno):
        """Start the Poller, once started will take over for IOLoop.start()

        :param method handler: The method to call to handle events
        :param int events: The events to handle
        :param int fileno: The file descriptor to poll for

        """
        LOGGER.debug('Starting the Poller')
        self.poller = None
        if hasattr(select, 'epoll'):
            if not SELECT_TYPE or SELECT_TYPE == 'epoll':
                LOGGER.debug('Using EPollPoller')
                self.poller = EPollPoller(fileno, handler, events,
                                          self._manage_event_state)
        if not self.poller and hasattr(select, 'kqueue'):
            if not SELECT_TYPE or SELECT_TYPE == 'kqueue':
                LOGGER.debug('Using KQueuePoller')
                self.poller = KQueuePoller(fileno, handler, events,
                                           self._manage_event_state)
        if not self.poller and hasattr(select, 'poll') and hasattr(select.poll(), 'modify'):
            if not SELECT_TYPE or SELECT_TYPE == 'poll':
                LOGGER.debug('Using PollPoller')
                self.poller = PollPoller(fileno, handler, events,
                                         self._manage_event_state)
        if not self.poller:
            LOGGER.debug('Using SelectPoller')
            self.poller = SelectPoller(fileno, handler, events,
                                       self._manage_event_state)

    def stop(self):
        """Stop the poller's event loop"""
        LOGGER.debug('Stopping the poller event loop')
        self.poller.open = False

    def update_handler(self, fileno, events):
        """Pass in the events to process for the given file descriptor.

        :param int fileno: The file descriptor to poll for
        :param int events: The events to handle

        """
        self.poller.update_handler(fileno, events)


class SelectPoller(object):
    """Default behavior is to use Select since it's the widest supported and has
    all of the methods we need for child classes as well. One should only need
    to override the update_handler and start methods for additional types.

    """
    TIMEOUT = 1

    def __init__(self, fileno, handler, events, state_manager):
        """Create an instance of the SelectPoller

        :param int fileno: The file descriptor to check events for
        :param method handler: What is called when an event happens
        :param int events: The events to look for
        :param method state_manager: The method to manage state

        """
        self.fileno = fileno
        self.events = events
        self.open = True
        self._handler = handler
        self._timeouts = []
        self._manage_event_state = state_manager

    def add_timeout(self, deadline, callback_method):
        """Add the callback_method to the IOLoop timer to fire after deadline
        seconds. Returns a handle to the timeout. Do not confuse with
        Tornado's timeout where you pass in the time you want to have your
        callback called. Only pass in the seconds until it's to be called.

        :param int deadline: The number of seconds to wait to call callback
        :param method callback_method: The callback method
        :rtype: str

        """
        value = {'deadline': time.time() + deadline,
                 'callback': callback_method}
        timeout_id = hash(frozenset(value.items()))
        self._timeouts.append((timeout_id, value))
        return timeout_id

    def flush_pending_timeouts(self):
        """
        """
        if len(self._timeouts) > 0:
            time.sleep(SelectPoller.TIMEOUT)
        self.process_timeouts()

    def poll(self, write_only=False):
        """Check to see if the events that are cared about have fired.

        :param bool write_only: Don't look at self.events, just look to see if
            the adapter can write.

        """
        # Build our values to pass into select
        input_fileno, output_fileno, error_fileno = [], [], []

        if self.events & READ:
            input_fileno = [self.fileno]
        if self.events & WRITE:
            output_fileno = [self.fileno]
        if self.events & ERROR:
            error_fileno = [self.fileno]

        # Wait on select to let us know what's up
        try:
            read, write, error = select.select(input_fileno,
                                               output_fileno,
                                               error_fileno,
                                               SelectPoller.TIMEOUT)
        except select.error as error:
            return self._handler(self.fileno, ERROR, error)

        # Build our events bit mask
        events = 0
        if read:
            events |= READ
        if write:
            events |= WRITE
        if error:
            events |= ERROR

        if events:
            self._handler(self.fileno, events, write_only=write_only)

    def process_timeouts(self):
        """Process the self._timeouts event stack"""
        start_time = time.time()
        # while loop instead of a more straightforward for loop so we can
        # delete items from the list while iterating
        i = 0
        while i < len(self._timeouts):
            t_id, timeout = self._timeouts[i]
            if timeout['deadline'] <= start_time:
                callback = timeout['callback']
                del self._timeouts[i]
                callback()
            else:
                i += 1

    def remove_timeout(self, timeout_id):
        """Remove a timeout if it's still in the timeout stack

        :param str timeout_id: The timeout id to remove

        """
        for i in xrange(len(self._timeouts)):
            t_id, timeout = self._timeouts[i]
            if t_id == timeout_id:
                del self._timeouts[i]
                break

    def start(self):
        """Start the main poller loop. It will loop here until self.closed"""
        while self.open:
            self.poll()
            self.process_timeouts()
            self._manage_event_state()

    def update_handler(self, fileno, events):
        """Set the events to the current events

        :param int fileno: The file descriptor
        :param int events: The event mask

        """
        self.events = events


class KQueuePoller(SelectPoller):
    """KQueuePoller works on BSD based systems and is faster than select"""
    def __init__(self, fileno, handler, events, state_manager):
        """Create an instance of the KQueuePoller

        :param int fileno: The file descriptor to check events for
        :param method handler: What is called when an event happens
        :param int events: The events to look for
        :param method state_manager: The method to manage state

        """
        super(KQueuePoller, self).__init__(fileno, handler, events,
                                           state_manager)
        self.events = 0
        self._kqueue = select.kqueue()
        self.update_handler(fileno, events)
        self._manage_event_state = state_manager

    def update_handler(self, fileno, events):
        """Set the events to the current events

        :param int fileno: The file descriptor
        :param int events: The event mask

        """
        # No need to update if our events are the same
        if self.events == events:
            return

        kevents = list()
        if not events & READ:
            if self.events & READ:
                kevents.append(select.kevent(fileno,
                                             filter=select.KQ_FILTER_READ,
                                             flags=select.KQ_EV_DELETE))
        else:
            if not self.events & READ:
                kevents.append(select.kevent(fileno,
                                             filter=select.KQ_FILTER_READ,
                                             flags=select.KQ_EV_ADD))
        if not events & WRITE:
            if self.events & WRITE:
                kevents.append(select.kevent(fileno,
                                             filter=select.KQ_FILTER_WRITE,
                                             flags=select.KQ_EV_DELETE))
        else:
            if not self.events & WRITE:
                kevents.append(select.kevent(fileno,
                                             filter=select.KQ_FILTER_WRITE,
                                             flags=select.KQ_EV_ADD))
        for event in kevents:
            self._kqueue.control([event], 0)
        self.events = events

    def start(self):
        """Start the main poller loop. It will loop here until self.closed"""
        while self.open:
            self.poll()
            self.process_timeouts()
            self._manage_event_state()

    def poll(self, write_only=False):
        """Check to see if the events that are cared about have fired.

        :param bool write_only: Don't look at self.events, just look to see if
            the adapter can write.

        """
        events = 0
        try:
            kevents = self._kqueue.control(None, 1000, SelectPoller.TIMEOUT)
        except OSError as error:
            return self._handler(self.fileno, ERROR, error)
        for event in kevents:
            if event.filter == select.KQ_FILTER_READ and READ & self.events:
                events |= READ
            if event.filter == select.KQ_FILTER_WRITE and WRITE & self.events:
                events |= WRITE
            if event.flags & select.KQ_EV_ERROR and ERROR & self.events:
                events |= ERROR
        if events:
            LOGGER.debug("Calling %s(%i)", self._handler, events)
            self._handler(self.fileno, events, write_only=write_only)


class PollPoller(SelectPoller):
    """Poll works on Linux and can have better performance than EPoll in
    certain scenarios.  Both are faster than select.

    """
    def __init__(self, fileno, handler, events, state_manager):
        """Create an instance of the KQueuePoller

        :param int fileno: The file descriptor to check events for
        :param method handler: What is called when an event happens
        :param int events: The events to look for
        :param method state_manager: The method to manage state

        """
        super(PollPoller, self).__init__(fileno, handler, events, state_manager)
        self._poll = select.poll()
        self._poll.register(fileno, self.events)

    def update_handler(self, fileno, events):
        """Set the events to the current events

        :param int fileno: The file descriptor
        :param int events: The event mask

        """
        self.events = events
        self._poll.modify(fileno, self.events)

    def start(self):
        """Start the main poller loop. It will loop here until self.closed"""
        was_open = self.open
        while self.open:
            self.poll()
            self.process_timeouts()
            self._manage_event_state()
        if not was_open:
            return
        try:
            LOGGER.info("Unregistering poller on fd %d" % self.fileno)
            self.update_handler(self.fileno, 0)
            self._poll.unregister(self.fileno)
        except IOError as err:
            LOGGER.debug("Got IOError while shutting down poller: %s", err)

    def poll(self, write_only=False):
        """Poll until TIMEOUT waiting for an event

        :param bool write_only: Only process write events

        """
        try:
            events = self._poll.poll(int(SelectPoller.TIMEOUT * 1000))
        except select.error as error:
            return self._handler(self.fileno, ERROR, error)
        if events:
            LOGGER.debug("Calling %s with %d events",
                         self._handler, len(events))
            for fileno, event in events:
                self._handler(fileno, event, write_only=write_only)


class EPollPoller(PollPoller):
    """EPoll works on Linux and can have better performance than Poll in
    certain scenarios. Both are faster than select.

    """
    def __init__(self, fileno, handler, events, state_manager):
        """Create an instance of the EPollPoller

        :param int fileno: The file descriptor to check events for
        :param method handler: What is called when an event happens
        :param int events: The events to look for
        :param method state_manager: The method to manage state

        """
        super(EPollPoller, self).__init__(fileno, handler, events,
                                          state_manager)
        self._poll = select.epoll()
        self._poll.register(fileno, self.events)

    def poll(self, write_only=False):
        """Poll until TIMEOUT waiting for an event

        :param bool write_only: Only process write events

        """
        try:
            events = self._poll.poll(SelectPoller.TIMEOUT)
        except IOError as error:
            return self._handler(self.fileno, ERROR, error)
        if events:
            LOGGER.debug("Calling %s", self._handler)
            for fileno, event in events:
                self._handler(fileno, event, write_only=write_only)

########NEW FILE########
__FILENAME__ = tornado_connection
"""Use pika with the Tornado IOLoop"""
from tornado import ioloop
import logging
import time

from pika.adapters import base_connection

LOGGER = logging.getLogger(__name__)


class TornadoConnection(base_connection.BaseConnection):
    """The TornadoConnection runs on the Tornado IOLoop. If you're running the
    connection in a web app, make sure you set stop_ioloop_on_close to False,
    which is the default behavior for this adapter, otherwise the web app
    will stop taking requests.

    :param pika.connection.Parameters parameters: Connection parameters
    :param on_open_callback: The method to call when the connection is open
    :type on_open_callback: method
    :param on_open_error_callback: Method to call if the connection cant
                                   be opened
    :type on_open_error_callback: method
    :param bool stop_ioloop_on_close: Call ioloop.stop() if disconnected
    :param custom_ioloop: Override using the global IOLoop in Tornado

    """
    WARN_ABOUT_IOLOOP = True

    def __init__(self, parameters=None,
                 on_open_callback=None,
                 on_open_error_callback=None,
                 on_close_callback=None,
                 stop_ioloop_on_close=False,
                 custom_ioloop=None):
        """Create a new instance of the TornadoConnection class, connecting
        to RabbitMQ automatically

        :param pika.connection.Parameters parameters: Connection parameters
        :param on_open_callback: The method to call when the connection is open
        :type on_open_callback: method
        :param on_open_error_callback: Method to call if the connection cant
                                       be opened
        :type on_open_error_callback: method
        :param bool stop_ioloop_on_close: Call ioloop.stop() if disconnected
        :param custom_ioloop: Override using the global IOLoop in Tornado

        """
        self.sleep_counter = 0
        self.ioloop = custom_ioloop or ioloop.IOLoop.instance()
        super(TornadoConnection, self).__init__(parameters,
                                                on_open_callback,
                                                on_open_error_callback,
                                                on_close_callback,
                                                self.ioloop,
                                                stop_ioloop_on_close)

    def _adapter_connect(self):
        """Connect to the remote socket, adding the socket to the IOLoop if
        connected

        :rtype: bool

        """
        error = super(TornadoConnection, self)._adapter_connect()
        if not error:
            self.ioloop.add_handler(self.socket.fileno(),
                                    self._handle_events,
                                    self.event_state)
        return error

    def _adapter_disconnect(self):
        """Disconnect from the RabbitMQ broker"""
        if self.socket:
            self.ioloop.remove_handler(self.socket.fileno())
        super(TornadoConnection, self)._adapter_disconnect()

    def add_timeout(self, deadline, callback_method):
        """Add the callback_method to the IOLoop timer to fire after deadline
        seconds. Returns a handle to the timeout. Do not confuse with
        Tornado's timeout where you pass in the time you want to have your
        callback called. Only pass in the seconds until it's to be called.

        :param int deadline: The number of seconds to wait to call callback
        :param method callback_method: The callback method
        :rtype: str

        """
        return self.ioloop.add_timeout(time.time() + deadline, callback_method)

    def remove_timeout(self, timeout_id):
        """Remove the timeout from the IOLoop by the ID returned from
        add_timeout.

        :rtype: str

        """
        return self.ioloop.remove_timeout(timeout_id)

########NEW FILE########
__FILENAME__ = twisted_connection
"""Using Pika with a Twisted reactor.

Supports two methods of establishing the connection, using TwistedConnection
or TwistedProtocolConnection. For details about each method, see the docstrings
of the corresponding classes.

The interfaces in this module are Deferred-based when possible. This means that
the connection.channel() method and most of the channel methods return
Deferreds instead of taking a callback argument and that basic_consume()
returns a Twisted DeferredQueue where messages from the server will be
stored. Refer to the docstrings for TwistedConnection.channel() and the
TwistedChannel class for details.

"""
import functools
from twisted.internet import defer, error, reactor
from twisted.python import log

from pika import exceptions
from pika.adapters import base_connection


class ClosableDeferredQueue(defer.DeferredQueue):
    """
    Like the normal Twisted DeferredQueue, but after close() is called with an
    Exception instance all pending Deferreds are errbacked and further attempts
    to call get() or put() return a Failure wrapping that exception.
    """
    def __init__(self, size=None, backlog=None):
        self.closed = None
        super(ClosableDeferredQueue, self).__init__(size, backlog)

    def put(self, obj):
        if self.closed:
            return defer.fail(self.closed)
        return defer.DeferredQueue.put(self, obj)

    def get(self):
        if self.closed:
            return defer.fail(self.closed)
        return defer.DeferredQueue.get(self)

    def close(self, reason):
        self.closed = reason
        while self.waiting:
            self.waiting.pop().errback(reason)
        self.pending = []


class TwistedChannel(object):
    """A wrapper wround Pika's Channel.

    Channel methods that normally take a callback argument are wrapped to
    return a Deferred that fires with whatever would be passed to the callback.
    If the channel gets closed, all pending Deferreds are errbacked with a
    ChannelClosed exception. The returned Deferreds fire with whatever
    arguments the callback to the original method would receive.

    The basic_consume method is wrapped in a special way, see its docstring for
    details.
    """

    WRAPPED_METHODS = ('exchange_declare', 'exchange_delete',
                       'queue_declare', 'queue_bind', 'queue_purge',
                       'queue_unbind', 'basic_qos', 'basic_get',
                       'basic_recover', 'tx_select', 'tx_commit',
                       'tx_rollback', 'flow', 'basic_cancel')

    def __init__(self, channel):
        self.__channel = channel
        self.__closed = None
        self.__calls = set()
        self.__consumers = {}

        channel.add_on_close_callback(self.channel_closed)

    def channel_closed(self, channel, reply_code, reply_text):
        # enter the closed state
        self.__closed = exceptions.ChannelClosed(reply_code, reply_text)
        # errback all pending calls
        for d in self.__calls:
            d.errback(self.__closed)
        # close all open queues
        for consumers in self.__consumers.values():
            for c in consumers:
                c.close(self.__closed)
        # release references to stored objects
        self.__calls = set()
        self.__consumers = {}

    def basic_consume(self, *args, **kwargs):
        """Consume from a server queue. Returns a Deferred that fires with a
        tuple: (queue_object, consumer_tag). The queue object is an instance of
        ClosableDeferredQueue, where data received from the queue will be
        stored. Clients should use its get() method to fetch individual
        message.
        """
        if self.__closed:
            return defer.fail(self.__closed)

        queue = ClosableDeferredQueue()
        queue_name = kwargs['queue']
        kwargs['consumer_callback'] = lambda *args: queue.put(args)
        self.__consumers.setdefault(queue_name, set()).add(queue)

        try:
            consumer_tag = self.__channel.basic_consume(*args, **kwargs)
        except:
            return defer.fail()

        return defer.succeed((queue, consumer_tag))

    def queue_delete(self, *args, **kwargs):
        """Wraps the method the same way all the others are wrapped, but removes
        the reference to the queue object after it gets deleted on the server.

        """
        wrapped = self.__wrap_channel_method('queue_delete')
        queue_name = kwargs['queue']

        d = wrapped(*args, **kwargs)
        return d.addCallback(self.__clear_consumer, queue_name)

    def basic_publish(self, *args, **kwargs):
        """Make sure the channel is not closed and then publish. Return a
        Deferred that fires with the result of the channel's basic_publish.

        """
        if self.__closed:
            return defer.fail(self.__closed)
        return defer.succeed(self.__channel.basic_publish(*args, **kwargs))

    def __wrap_channel_method(self, name):
        """Wrap Pika's Channel method to make it return a Deferred that fires
        when the method completes and errbacks if the channel gets closed. If
        the original method's callback would receive more than one argument, the
        Deferred fires with a tuple of argument values.

        """
        method = getattr(self.__channel, name)

        @functools.wraps(method)
        def wrapped(*args, **kwargs):
            if self.__closed:
                return defer.fail(self.__closed)

            d = defer.Deferred()
            self.__calls.add(d)
            d.addCallback(self.__clear_call, d)

            def single_argument(*args):
                """
                Make sure that the deferred is called with a single argument.
                In case the original callback fires with more than one, convert
                to a tuple.
                """
                if len(args) > 1:
                    d.callback(tuple(args))
                else:
                    d.callback(*args)

            kwargs['callback'] = single_argument

            try:
                method(*args, **kwargs)
            except:
                return defer.fail()
            return d

        return wrapped

    def __clear_consumer(self, ret, queue_name):
        self.__consumers.pop(queue_name, None)
        return ret

    def __clear_call(self, ret, d):
        self.__calls.discard(d)
        return ret

    def __getattr__(self, name):
        # Wrap methods defined in WRAPPED_METHODS, forward the rest of accesses
        # to the channel.
        if name in self.WRAPPED_METHODS:
            return self.__wrap_channel_method(name)
        return getattr(self.__channel, name)


class IOLoopReactorAdapter(object):
    """An adapter providing Pika's IOLoop interface using a Twisted reactor.

    Accepts a TwistedConnection object and a Twisted reactor object.

    """
    def __init__(self, connection, reactor):
        self.connection = connection
        self.reactor = reactor
        self.started = False

    def add_timeout(self, deadline, callback_method):
        """Add the callback_method to the IOLoop timer to fire after deadline
        seconds. Returns a handle to the timeout. Do not confuse with
        Tornado's timeout where you pass in the time you want to have your
        callback called. Only pass in the seconds until it's to be called.

        :param int deadline: The number of seconds to wait to call callback
        :param method callback_method: The callback method
        :rtype: twisted.internet.interfaces.IDelayedCall

        """
        return self.reactor.callLater(deadline, callback_method)

    def remove_timeout(self, call):
        """Remove a call

        :param twisted.internet.interfaces.IDelayedCall call: The call to cancel

        """
        call.cancel()

    def stop(self):
        # Guard against stopping the reactor multiple times
        if not self.started:
            return
        self.started = False
        self.reactor.stop()

    def start(self):
        # Guard against starting the reactor multiple times
        if self.started:
            return
        self.started = True
        self.reactor.run()

    def remove_handler(self, _):
        # The fileno is irrelevant, as it's the connection's job to provide it
        # to the reactor when asked to do so. Removing the handler from the
        # ioloop is removing it from the reactor in Twisted's parlance.
        self.reactor.removeReader(self.connection)
        self.reactor.removeWriter(self.connection)

    def update_handler(self, _, event_state):
        # Same as in remove_handler, the fileno is irrelevant. First remove the
        # connection entirely from the reactor, then add it back depending on
        # the event state.
        self.reactor.removeReader(self.connection)
        self.reactor.removeWriter(self.connection)

        if event_state & self.connection.READ:
            self.reactor.addReader(self.connection)

        if event_state & self.connection.WRITE:
            self.reactor.addWriter(self.connection)


class TwistedConnection(base_connection.BaseConnection):
    """A standard Pika connection adapter. You instantiate the class passing the
    connection parameters and the connected callback and when it gets called
    you can start using it.

    The problem is that connection establishing is done using the blocking
    socket module. For instance, if the host you are connecting to is behind a
    misconfigured firewall that just drops packets, the whole process will
    freeze until the connection timeout passes. To work around that problem,
    use TwistedProtocolConnection, but read its docstring first.

    Objects of this class get put in the Twisted reactor which will notify them
    when the socket connection becomes readable or writable, so apart from
    implementing the BaseConnection interface, they also provide Twisted's
    IReadWriteDescriptor interface.

    """
    def __init__(self, parameters=None,
                 on_open_callback=None,
                 on_open_error_callback=None,
                 on_close_callback=None,
                 stop_ioloop_on_close=False):
        super(TwistedConnection, self).__init__(
            parameters=parameters,
            on_open_callback=on_open_callback,
            on_open_error_callback=on_open_error_callback,
            on_close_callback=on_close_callback,
            ioloop=IOLoopReactorAdapter(self, reactor),
            stop_ioloop_on_close=stop_ioloop_on_close)

    def _adapter_connect(self):
        """Connect to the RabbitMQ broker"""
        # Connect (blockignly!) to the server
        error = super(TwistedConnection, self)._adapter_connect()
        if not error:
            # Set the I/O events we're waiting for (see IOLoopReactorAdapter
            # docstrings for why it's OK to pass None as the file descriptor)
            self.ioloop.update_handler(None, self.event_state)
        return error

    def _adapter_disconnect(self):
        """Called when the adapter should disconnect"""
        self.ioloop.remove_handler(None)
        self.socket.close()

    def _handle_disconnect(self):
        """Do not stop the reactor, this would cause the entire process to exit,
        just fire the disconnect callbacks

        """
        self._on_connection_closed(None, True)

    def _on_connected(self):
        """Call superclass and then update the event state to flush the outgoing
        frame out. Commit 50d842526d9f12d32ad9f3c4910ef60b8c301f59 removed a
        self._flush_outbound call that was in _send_frame which previously
        made this step unnecessary.

        """
        super(TwistedConnection, self)._on_connected()
        self._manage_event_state()

    def channel(self, channel_number=None):
        """Return a Deferred that fires with an instance of a wrapper around the
        Pika Channel class.

        """
        d = defer.Deferred()
        base_connection.BaseConnection.channel(self, d.callback, channel_number)
        return d.addCallback(TwistedChannel)

    # IReadWriteDescriptor methods

    def fileno(self):
        return self.socket.fileno()

    def logPrefix(self):
        return "twisted-pika"

    def connectionLost(self, reason):
        # If the connection was not closed cleanly, log the error
        if not reason.check(error.ConnectionDone):
            log.err(reason)

        self._handle_disconnect()

    def doRead(self):
        self._handle_read()

    def doWrite(self):
        self._handle_write()
        self._manage_event_state()


class TwistedProtocolConnection(base_connection.BaseConnection):
    """A hybrid between a Pika Connection and a Twisted Protocol. Allows using
    Twisted's non-blocking connectTCP/connectSSL methods for connecting to the
    server.

    It has one caveat: TwistedProtocolConnection objects have a ready
    instance variable that's a Deferred which fires when the connection is
    ready to be used (the initial AMQP handshaking has been done). You *have*
    to wait for this Deferred to fire before requesting a channel.

    Since it's Twisted handling connection establishing it does not accept
    connect callbacks, you have to implement that within Twisted. Also remember
    that the host, port and ssl values of the connection parameters are ignored
    because, yet again, it's Twisted who manages the connection.

    """
    def __init__(self, parameters):
        self.ready = defer.Deferred()
        super(TwistedProtocolConnection, self).__init__(
            parameters=parameters,
            on_open_callback=self.connectionReady,
            on_open_error_callback=self.connectionFailed,
            on_close_callback=None,
            ioloop=IOLoopReactorAdapter(self, reactor),
            stop_ioloop_on_close=False)

    def connect(self):
        # The connection is open asynchronously by Twisted, so skip the whole
        # connect() part, except for setting the connection state
        self._set_connection_state(self.CONNECTION_INIT)

    def _adapter_connect(self):
        # Should never be called, as we override connect() and leave the
        # building of a TCP connection to Twisted, but implement anyway to keep
        # the interface
        return False

    def _adapter_disconnect(self):
        # Disconnect from the server
        self.transport.loseConnection()

    def _send_frame(self, frame_value):
        """Send data the Twisted way, by writing to the transport. No need for
        buffering, Twisted handles that by itself.

        :param frame_value: The frame to write
        :type frame_value:  pika.frame.Frame|pika.frame.ProtocolHeader

        """
        if self.is_closed:
            raise exceptions.ConnectionClosed
        marshaled_frame = frame_value.marshal()
        self.bytes_sent += len(marshaled_frame)
        self.frames_sent += 1
        self.transport.write(marshaled_frame)

    def channel(self, channel_number=None):
        """Create a new channel with the next available channel number or pass
        in a channel number to use. Must be non-zero if you would like to
        specify but it is recommended that you let Pika manage the channel
        numbers.

        Return a Deferred that fires with an instance of a wrapper around the
        Pika Channel class.

        :param int channel_number: The channel number to use, defaults to the
                                   next available.

        """
        d = defer.Deferred()
        base_connection.BaseConnection.channel(self, d.callback, channel_number)
        return d.addCallback(TwistedChannel)

    # IProtocol methods

    def dataReceived(self, data):
        # Pass the bytes to Pika for parsing
        self._on_data_available(data)

    def connectionLost(self, reason):
        # Let the caller know there's been an error
        d, self.ready = self.ready, None
        if d:
            d.errback(reason)

    def makeConnection(self, transport):
        self.transport = transport
        self.connectionMade()

    def connectionMade(self):
        # Tell everyone we're connected
        self._on_connected()

    # Our own methods

    def connectionReady(self, res):
        d, self.ready = self.ready, None
        if d:
            d.callback(res)

    def connectionFailed(self, connection_unused, error_message=None):
        d, self.ready = self.ready, None
        if d:
            attempts = self.params.connection_attempts
            exc = exceptions.AMQPConnectionError(attempts)
            d.errback(exc)

########NEW FILE########
__FILENAME__ = amqp_object
"""Base classes that are extended by low level AMQP frames and higher level
AMQP classes and methods.

"""


class AMQPObject(object):
    """Base object that is extended by AMQP low level frames and AMQP classes
    and methods.

    """
    NAME = 'AMQPObject'
    INDEX = None

    def __repr__(self):
        items = list()
        for key, value in self.__dict__.items():
            if getattr(self.__class__, key, None) != value:
                items.append('%s=%s' % (key, value))
        if not items:
            return "<%s>" % self.NAME
        return "<%s(%s)>" % (self.NAME, sorted(items))


class Class(AMQPObject):
    """Is extended by AMQP classes"""
    NAME = 'Unextended Class'


class Method(AMQPObject):
    """Is extended by AMQP methods"""
    NAME = 'Unextended Method'
    synchronous = False

    def _set_content(self, properties, body):
        """If the method is a content frame, set the properties and body to
        be carried as attributes of the class.

        :param pika.frame.Properties properties: AMQP Basic Properties
        :param body: The message body
        :type body: str or unicode

        """
        self._properties = properties
        self._body = body

    def get_properties(self):
        """Return the properties if they are set.

        :rtype: pika.frame.Properties

        """
        return self._properties

    def get_body(self):
        """Return the message body if it is set.

        :rtype: str|unicode

        """
        return self._body


class Properties(AMQPObject):
    """Class to encompass message properties (AMQP Basic.Properties)"""
    NAME = 'Unextended Properties'

########NEW FILE########
__FILENAME__ = callback
"""Callback management class, common area for keeping track of all callbacks in
the Pika stack.

"""
import functools
import logging

from pika import frame
from pika import amqp_object

LOGGER = logging.getLogger(__name__)


def _name_or_value(value):
    """Will take Frame objects, classes, etc and attempt to return a valid
    string identifier for them.

    :param value: The value to sanitize
    :type value:  pika.amqp_object.AMQPObject|pika.frame.Frame|int|unicode|str
    :rtype: str

    """
    # Is it subclass of AMQPObject
    try:
        if issubclass(value, amqp_object.AMQPObject):
            return value.NAME
    except TypeError:
        pass

    # Is it a Pika frame object?
    if isinstance(value, frame.Method):
        return value.method.NAME

    # Is it a Pika frame object (go after Method since Method extends this)
    if isinstance(value, amqp_object.AMQPObject):
        return value.NAME

    # Cast the value to a string, encoding it if it's unicode
    try:
        return str(value)
    except UnicodeEncodeError:
        return str(value.encode('utf-8'))


def sanitize_prefix(function):
    """Automatically call _name_or_value on the prefix passed in."""
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        args = list(args)
        offset = 1
        if 'prefix' in kwargs:
            kwargs['prefix'] = _name_or_value(kwargs['prefix'])
        elif len(args) - 1  >= offset:
            args[offset] = _name_or_value(args[offset])
            offset += 1
        if 'key' in kwargs:
            kwargs['key'] = _name_or_value(kwargs['key'])
        elif len(args) - 1 >= offset:
            args[offset] = _name_or_value(args[offset])

        return function(*tuple(args), **kwargs)
    return wrapper


def check_for_prefix_and_key(function):
    """Automatically return false if the key or prefix is not in the callbacks
    for the instance.

    """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        offset = 1
        # Sanitize the prefix
        if 'prefix' in kwargs:
            prefix = _name_or_value(kwargs['prefix'])
        else:
            prefix = _name_or_value(args[offset])
            offset += 1

        # Make sure to sanitize the key as well
        if 'key' in kwargs:
            key = _name_or_value(kwargs['key'])
        else:
            key = _name_or_value(args[offset])

        # Make sure prefix and key are in the stack
        if (prefix not in args[0]._stack or
            key not in args[0]._stack[prefix]):
            return False

        # Execute the method
        return function(*args, **kwargs)
    return wrapper


class CallbackManager(object):
    """CallbackManager is a global callback system designed to be a single place
    where Pika can manage callbacks and process them. It should be referenced
    by the CallbackManager.instance() method instead of constructing new
    instances of it.

    """
    CALLS = 'calls'
    ARGUMENTS = 'arguments'
    DUPLICATE_WARNING = 'Duplicate callback found for "%s:%s"'
    CALLBACK = 'callback'
    ONE_SHOT = 'one_shot'
    ONLY_CALLER = 'only'

    def __init__(self):
        """Create an instance of the CallbackManager"""
        self._stack = dict()

    @sanitize_prefix
    def add(self, prefix, key, callback, one_shot=True, only_caller=None,
            arguments=None):
        """Add a callback to the stack for the specified key. If the call is
        specified as one_shot, it will be removed after being fired

        The prefix is usually the channel number but the class is generic
        and prefix and key may be any value. If you pass in only_caller
        CallbackManager will restrict processing of the callback to only
        the calling function/object that you specify.

        :param prefix: Categorize the callback
        :type prefix: str or int
        :param key: The key for the callback
        :type key: object or str or dict
        :param method callback: The callback to call
        :param bool one_shot: Remove this callback after it is called
        :param object only_caller: Only allow one_caller value to call the
                                   event that fires the callback.
        :param dict arguments: Arguments to validate when processing
        :rtype: tuple(prefix, key)

        """
        # Prep the stack
        if prefix not in self._stack:
            self._stack[prefix] = dict()

        if key not in self._stack[prefix]:
            self._stack[prefix][key] = list()

        # Check for a duplicate
        for callback_dict in self._stack[prefix][key]:
            if (callback_dict[self.CALLBACK] == callback and
                callback_dict[self.ARGUMENTS] == arguments and
                callback_dict[self.ONLY_CALLER] == only_caller):
                if callback_dict[self.ONE_SHOT] is True:
                    callback_dict[self.CALLS] += 1
                    LOGGER.debug('Incremented callback reference counter: %r',
                                 callback_dict)
                else:
                    LOGGER.warning(self.DUPLICATE_WARNING, prefix, key)
                return prefix, key

        # Create the callback dictionary
        callback_dict = self._callback_dict(callback, one_shot, only_caller,
                                            arguments)
        self._stack[prefix][key].append(callback_dict)
        LOGGER.debug('Added: %r', callback_dict)
        return prefix, key

    def clear(self):
        """Clear all the callbacks if there are any defined."""
        self._stack = dict()
        LOGGER.debug('Callbacks cleared')

    @sanitize_prefix
    def cleanup(self, prefix):
        """Remove all callbacks from the stack by a prefix. Returns True
        if keys were there to be removed

        :param str or int prefix: The prefix for keeping track of callbacks with
        :rtype: bool

        """
        LOGGER.debug('Clearing out %r from the stack', prefix)
        if prefix not in self._stack or not self._stack[prefix]:
            return False
        del self._stack[prefix]
        return True

    @sanitize_prefix
    def pending(self, prefix, key):
        """Return count of callbacks for a given prefix or key or None

        :param prefix: Categorize the callback
        :type prefix: str or int
        :param key: The key for the callback
        :type key: object or str or dict
        :rtype: None or int

        """
        if not prefix in self._stack or not key in self._stack[prefix]:
            return None
        return len(self._stack[prefix][key])

    @sanitize_prefix
    @check_for_prefix_and_key
    def process(self, prefix, key, caller, *args, **keywords):
        """Run through and process all the callbacks for the specified keys.
        Caller should be specified at all times so that callbacks which
        require a specific function to call CallbackManager.process will
        not be processed.

        :param prefix: Categorize the callback
        :type prefix: str or int
        :param key: The key for the callback
        :type key: object or str or dict
        :param object caller: Who is firing the event
        :param list args: Any optional arguments
        :param dict keywords: Optional keyword arguments
        :rtype: bool

        """
        LOGGER.debug('Processing %s:%s', prefix, key)
        if prefix not in self._stack or key not in self._stack[prefix]:
            return False

        callbacks = list()
        # Check each callback, append it to the list if it should be called
        for callback_dict in list(self._stack[prefix][key]):
            if self._should_process_callback(callback_dict, caller, list(args)):
                callbacks.append(callback_dict[self.CALLBACK])
                if callback_dict[self.ONE_SHOT]:
                    self._use_one_shot_callback(prefix, key, callback_dict)

        # Call each callback
        for callback in callbacks:
            LOGGER.debug('Calling %s for "%s:%s"', callback, prefix, key)
            callback(*args, **keywords)
        return True

    @sanitize_prefix
    @check_for_prefix_and_key
    def remove(self, prefix, key, callback_value=None, arguments=None):
        """Remove a callback from the stack by prefix, key and optionally
        the callback itself. If you only pass in prefix and key, all
        callbacks for that prefix and key will be removed.

        :param str or int prefix: The prefix for keeping track of callbacks with
        :param str key: The callback key
        :param method callback_value: The method defined to call on callback
        :param dict arguments: Optional arguments to check
        :rtype: bool

        """
        if callback_value:
            offsets_to_remove = list()
            for offset in xrange(len(self._stack[prefix][key]), 0, -1):
                callback_dict = self._stack[prefix][key][offset - 1]

                if (callback_dict[self.CALLBACK] == callback_value and
                    self._arguments_match(callback_dict, [arguments])):
                    offsets_to_remove.append(offset - 1)

            for offset in offsets_to_remove:
                try:
                    LOGGER.debug('Removing callback #%i: %r', offset,
                                 self._stack[prefix][key][offset])
                    del self._stack[prefix][key][offset]
                except KeyError:
                    pass

        self._cleanup_callback_dict(prefix, key)
        return True

    @sanitize_prefix
    @check_for_prefix_and_key
    def remove_all(self, prefix, key):
        """Remove all callbacks for the specified prefix and key.

        :param str prefix: The prefix for keeping track of callbacks with
        :param str key: The callback key

        """
        del self._stack[prefix][key]
        self._cleanup_callback_dict(prefix, key)

    def _arguments_match(self, callback_dict, args):
        """Validate if the arguments passed in match the expected arguments in
        the callback_dict. We expect this to be a frame passed in to *args for
        process or passed in as a list from remove.

        :param dict callback_dict: The callback dictionary to evaluate against
        :param list args: The arguments passed in as a list

        """
        if callback_dict[self.ARGUMENTS] is None:
            return True
        if not args:
            return False
        if isinstance(args[0], dict):
            return self._dict_arguments_match(args[0],
                                              callback_dict[self.ARGUMENTS])
        return self._obj_arguments_match(args[0].method if hasattr(args[0],
                                                                   'method')
                                         else args[0],
                                         callback_dict[self.ARGUMENTS])

    def _callback_dict(self, callback, one_shot, only_caller, arguments):
        """Return the callback dictionary.

        :param method callback: The callback to call
        :param bool one_shot: Remove this callback after it is called
        :param object only_caller: Only allow one_caller value to call the
                                   event that fires the callback.
        :rtype: dict

        """
        value = {self.CALLBACK: callback,
                 self.ONE_SHOT: one_shot,
                 self.ONLY_CALLER: only_caller,
                 self.ARGUMENTS: arguments}
        if one_shot:
            value[self.CALLS] = 1
        return value

    def _cleanup_callback_dict(self, prefix, key=None):
        """Remove empty dict nodes in the callback stack.

        :param str or int prefix: The prefix for keeping track of callbacks with
        :param str key: The callback key

        """
        if key and key in self._stack[prefix] and not self._stack[prefix][key]:
            del self._stack[prefix][key]
        if prefix in self._stack and not self._stack[prefix]:
            del self._stack[prefix]

    def _dict_arguments_match(self, value, expectation):
        """Checks an dict to see if it has attributes that meet the expectation.

        :param dict value: The dict to evaluate
        :param dict expectation: The values to check against
        :rtype: bool

        """
        LOGGER.debug('Comparing %r to %r', value, expectation)
        for key in expectation:
            if value.get(key) != expectation[key]:
                LOGGER.debug('Values in dict do not match for %s', key)
                return False
        return True

    def _obj_arguments_match(self, value, expectation):
        """Checks an object to see if it has attributes that meet the
        expectation.

        :param object value: The object to evaluate
        :param dict expectation: The values to check against
        :rtype: bool

        """
        for key in expectation:
            if not hasattr(value, key):
                LOGGER.debug('%r does not have required attribute: %s',
                             type(value), key)
                return False
            if getattr(value, key) != expectation[key]:
                LOGGER.debug('Values in %s do not match for %s',
                             type(value), key)
                return False
        return True

    def _should_process_callback(self, callback_dict, caller, args):
        """Returns True if the callback should be processed.

        :param dict callback_dict: The callback configuration
        :param object caller: Who is firing the event
        :param list args: Any optional arguments
        :rtype: bool

        """
        if not self._arguments_match(callback_dict, args):
            LOGGER.debug('Arguments do not match for %r, %r',
                         callback_dict, args)
            return False
        return (callback_dict[self.ONLY_CALLER] is None or
                (callback_dict[self.ONLY_CALLER] and
                 callback_dict[self.ONLY_CALLER] == caller))

    def _use_one_shot_callback(self, prefix, key, callback_dict):
        """Process the one-shot callback, decrementing the use counter and
        removing it from the stack if it's now been fully used.

        :param str or int prefix: The prefix for keeping track of callbacks with
        :param str key: The callback key
        :param dict callback_dict: The callback dict to process

        """
        LOGGER.debug('Processing use of oneshot callback')
        callback_dict[self.CALLS] -= 1
        LOGGER.debug('%i registered uses left', callback_dict[self.CALLS])

        if callback_dict[self.CALLS] <= 0:
            self.remove(prefix, key,
                        callback_dict[self.CALLBACK],
                        callback_dict[self.ARGUMENTS])

########NEW FILE########
__FILENAME__ = channel
"""The Channel class provides a wrapper for interacting with RabbitMQ
implementing the methods and behaviors for an AMQP Channel.

"""
import collections
import logging
import warnings
import uuid

import pika.frame as frame
import pika.exceptions as exceptions
import pika.spec as spec
from pika.utils import is_callable

LOGGER = logging.getLogger(__name__)
MAX_CHANNELS = 32768


class Channel(object):
    """A Channel is the primary communication method for interacting with
    RabbitMQ. It is recommended that you do not directly invoke
    the creation of a channel object in your application code but rather
    construct the a channel by calling the active connection's channel()
    method.

    """
    CLOSED = 0
    OPENING = 1
    OPEN = 2
    CLOSING = 3

    def __init__(self, connection, channel_number, on_open_callback=None):
        """Create a new instance of the Channel

        :param pika.connection.Connection connection: The connection
        :param int channel_number: The channel number for this instance
        :param method on_open_callback: The method to call on channel open

        """
        if not isinstance(channel_number, int):
            raise exceptions.InvalidChannelNumber
        self.channel_number = channel_number
        self.callbacks = connection.callbacks
        self.connection = connection

        # The frame-handler changes depending on the type of frame processed
        self.frame_dispatcher = ContentFrameDispatcher()

        self._blocked = collections.deque(list())
        self._blocking = None
        self._has_on_flow_callback = False
        self._cancelled = collections.deque(list())
        self._consumers = dict()
        self._on_flowok_callback = None
        self._on_getok_callback = None
        self._on_openok_callback = on_open_callback
        self._pending = dict()
        self._state = self.CLOSED

    def __int__(self):
        """Return the channel object as its channel number

        :rtype: int

        """
        return self.channel_number

    def add_callback(self, callback, replies, one_shot=True):
        """Pass in a callback handler and a list replies from the
        RabbitMQ broker which you'd like the callback notified of. Callbacks
        should allow for the frame parameter to be passed in.

        :param method callback: The method to call
        :param list replies: The replies to get a callback for
        :param bool one_shot: Only handle the first type callback

        """
        for reply in replies:
            self.callbacks.add(self.channel_number, reply, callback, one_shot)

    def add_on_cancel_callback(self, callback):
        """Pass a callback function that will be called when the basic_cancel
        is sent by the server. The callback function should receive a frame
        parameter.

        :param method callback: The method to call on callback

        """
        self.callbacks.add(self.channel_number, spec.Basic.Cancel, callback,
                           False)

    def add_on_close_callback(self, callback):
        """Pass a callback function that will be called when the channel is
        closed. The callback function will receive the channel, the
        reply_code (int) and the reply_text (int) sent by the server describing
        why the channel was closed.

        :param method callback: The method to call on callback

        """
        self.callbacks.add(self.channel_number, '_on_channel_close', callback,
                           False, self)

    def add_on_flow_callback(self, callback):
        """Pass a callback function that will be called when Channel.Flow is
        called by the remote server. Note that newer versions of RabbitMQ
        will not issue this but instead use TCP backpressure

        :param method callback: The method to call on callback

        """
        self._has_on_flow_callback = True
        self.callbacks.add(self.channel_number, spec.Channel.Flow, callback,
                           False)

    def add_on_return_callback(self, callback):
        """Pass a callback function that will be called when basic_publish as
        sent a message that has been rejected and returned by the server. The
        callback handler should receive a method, header and body frame. The
        base signature for the callback should be the same as the method
        signature one creates for a basic_consume callback.

        :param method callback: The method to call on callback

        """
        self.callbacks.add(self.channel_number, '_on_return', callback, False)

    def basic_ack(self, delivery_tag=0, multiple=False):
        """Acknowledge one or more messages. When sent by the client, this
        method acknowledges one or more messages delivered via the Deliver or
        Get-Ok methods. When sent by server, this method acknowledges one or
        more messages published with the Publish method on a channel in
        confirm mode. The acknowledgement can be for a single message or a
        set of messages up to and including a specific message.

        :param int delivery-tag: The server-assigned delivery tag
        :param bool multiple: If set to True, the delivery tag is treated as
                              "up to and including", so that multiple messages
                              can be acknowledged with a single method. If set
                              to False, the delivery tag refers to a single
                              message. If the multiple field is 1, and the
                              delivery tag is zero, this indicates
                              acknowledgement of all outstanding messages.
        """
        if not self.is_open:
            raise exceptions.ChannelClosed()
        return self._send_method(spec.Basic.Ack(delivery_tag, multiple))

    def basic_cancel(self, callback=None, consumer_tag='', nowait=False):
        """This method cancels a consumer. This does not affect already
        delivered messages, but it does mean the server will not send any more
        messages for that consumer. The client may receive an arbitrary number
        of messages in between sending the cancel method and receiving the
        cancel-ok reply. It may also be sent from the server to the client in
        the event of the consumer being unexpectedly cancelled (i.e. cancelled
        for any reason other than the server receiving the corresponding
        basic.cancel from the client). This allows clients to be notified of
        the loss of consumers due to events such as queue deletion.

        :param method callback: Method to call for a Basic.CancelOk response
        :param str consumer_tag: Identifier for the consumer
        :param bool nowait: Do not expect a Basic.CancelOk response
        :raises: ValueError

        """
        self._validate_channel_and_callback(callback)
        if consumer_tag not in self.consumer_tags:
            return
        if callback:
            if nowait is True:
                raise ValueError('Can not pass a callback if nowait is True')
            self.callbacks.add(self.channel_number,
                               spec.Basic.CancelOk,
                               callback)
        self._cancelled.append(consumer_tag)
        self._rpc(spec.Basic.Cancel(consumer_tag=consumer_tag,
                                    nowait=nowait),
                  self._on_cancelok,
                  [(spec.Basic.CancelOk,
                    {'consumer_tag': consumer_tag})] if nowait is False else [])

    def basic_consume(self, consumer_callback, queue='', no_ack=False,
                      exclusive=False, consumer_tag=None, arguments=None):
        """Sends the AMQP command Basic.Consume to the broker and binds messages
        for the consumer_tag to the consumer callback. If you do not pass in
        a consumer_tag, one will be automatically generated for you. Returns
        the consumer tag.

        For more information on basic_consume, see:
        http://www.rabbitmq.com/amqp-0-9-1-reference.html#basic.consume

        :param method consumer_callback: The method to callback when consuming
        :param queue: The queue to consume from
        :type queue: str or unicode
        :param bool no_ack: Tell the broker to not expect a response
        :param bool exclusive: Don't allow other consumers on the queue
        :param consumer_tag: Specify your own consumer tag
        :type consumer_tag: str or unicode
        :param dict arguments: Custom key/value pair arguments for the consume
        :rtype: str

        """
        self._validate_channel_and_callback(consumer_callback)

        # If a consumer tag was not passed, create one
        consumer_tag = consumer_tag or 'ctag%i.%s' % (self.channel_number,
                                                      uuid.uuid4().get_hex())

        if consumer_tag in self._consumers or consumer_tag in self._cancelled:
            raise exceptions.DuplicateConsumerTag(consumer_tag)

        self._consumers[consumer_tag] = consumer_callback
        self._pending[consumer_tag] = list()
        self._rpc(spec.Basic.Consume(queue=queue,
                                     consumer_tag=consumer_tag,
                                     no_ack=no_ack,
                                     exclusive=exclusive,
                                     arguments=arguments or dict()),
                           self._on_eventok,
                           [(spec.Basic.ConsumeOk,
                             {'consumer_tag': consumer_tag})])

        return consumer_tag

    def basic_get(self, callback=None, queue='', no_ack=False):
        """Get a single message from the AMQP broker. The callback method
        signature should have 3 parameters: The method frame, header frame and
        the body, like the consumer callback for Basic.Consume. If you want to
        be notified of Basic.GetEmpty, use the Channel.add_callback method
        adding your Basic.GetEmpty callback which should expect only one
        parameter, frame. For more information on basic_get and its
        parameters, see:

        http://www.rabbitmq.com/amqp-0-9-1-reference.html#basic.get

        :param method callback: The method to callback with a message
        :param queue: The queue to get a message from
        :type queue: str or unicode
        :param bool no_ack: Tell the broker to not expect a reply

        """
        self._validate_channel_and_callback(callback)
        self._on_getok_callback = callback
        self._send_method(spec.Basic.Get(queue=queue,
                                         no_ack=no_ack))

    def basic_nack(self, delivery_tag=None, multiple=False, requeue=True):
        """This method allows a client to reject one or more incoming messages.
        It can be used to interrupt and cancel large incoming messages, or
        return untreatable messages to their original queue.

        :param int delivery-tag: The server-assigned delivery tag
        :param bool multiple: If set to True, the delivery tag is treated as
                              "up to and including", so that multiple messages
                              can be acknowledged with a single method. If set
                              to False, the delivery tag refers to a single
                              message. If the multiple field is 1, and the
                              delivery tag is zero, this indicates
                              acknowledgement of all outstanding messages.
        :param bool requeue: If requeue is true, the server will attempt to
                             requeue the message. If requeue is false or the
                             requeue attempt fails the messages are discarded or
                             dead-lettered.

        """
        if not self.is_open:
            raise exceptions.ChannelClosed()
        return self._send_method(spec.Basic.Nack(delivery_tag, multiple,
                                                 requeue))

    def basic_publish(self, exchange, routing_key, body,
                      properties=None, mandatory=False, immediate=False):
        """Publish to the channel with the given exchange, routing key and body.
        For more information on basic_publish and what the parameters do, see:

        http://www.rabbitmq.com/amqp-0-9-1-reference.html#basic.publish

        :param exchange: The exchange to publish to
        :type exchange: str or unicode
        :param routing_key: The routing key to bind on
        :type routing_key: str or unicode
        :param body: The message body
        :type body: str or unicode
        :param pika.spec.Properties properties: Basic.properties
        :param bool mandatory: The mandatory flag
        :param bool immediate: The immediate flag

        """
        if not self.is_open:
            raise exceptions.ChannelClosed()
        if immediate:
            LOGGER.warning('The immediate flag is deprecated in RabbitMQ')
        if isinstance(body, unicode):
            body = body.encode('utf-8')
        properties = properties or spec.BasicProperties()
        self._send_method(spec.Basic.Publish(exchange=exchange,
                                             routing_key=routing_key,
                                             mandatory=mandatory,
                                             immediate=immediate),
                          (properties, body))

    def basic_qos(self, callback=None, prefetch_size=0, prefetch_count=0,
                  all_channels=False):
        """Specify quality of service. This method requests a specific quality
        of service. The QoS can be specified for the current channel or for all
        channels on the connection. The client can request that messages be sent
        in advance so that when the client finishes processing a message, the
        following message is already held locally, rather than needing to be
        sent down the channel. Prefetching gives a performance improvement.

        :param method callback: The method to callback for Basic.QosOk response
        :param int prefetch_size:  This field specifies the prefetch window
                                   size. The server will send a message in
                                   advance if it is equal to or smaller in size
                                   than the available prefetch size (and also
                                   falls into other prefetch limits). May be set
                                   to zero, meaning "no specific limit",
                                   although other prefetch limits may still
                                   apply. The prefetch-size is ignored if the
                                   no-ack option is set.
        :param int prefetch_count: Specifies a prefetch window in terms of whole
                                   messages. This field may be used in
                                   combination with the prefetch-size field; a
                                   message will only be sent in advance if both
                                   prefetch windows (and those at the channel
                                   and connection level) allow it. The
                                   prefetch-count is ignored if the no-ack
                                   option is set.
        :param bool all_channels: Should the QoS apply to all channels

        """
        self._validate_channel_and_callback(callback)
        return self._rpc(spec.Basic.Qos(prefetch_size, prefetch_count,
                                        all_channels),
                         callback,
                         [spec.Basic.QosOk])

    def basic_reject(self, delivery_tag=None, requeue=True):
        """Reject an incoming message. This method allows a client to reject a
        message. It can be used to interrupt and cancel large incoming messages,
        or return untreatable messages to their original queue.

        :param int delivery-tag: The server-assigned delivery tag
        :param bool requeue: If requeue is true, the server will attempt to
                             requeue the message. If requeue is false or the
                             requeue attempt fails the messages are discarded or
                             dead-lettered.

        """
        if not self.is_open:
            raise exceptions.ChannelClosed()
        return self._send_method(spec.Basic.Reject(delivery_tag, requeue))

    def basic_recover(self, callback=None, requeue=False):
        """This method asks the server to redeliver all unacknowledged messages
        on a specified channel. Zero or more messages may be redelivered. This
        method replaces the asynchronous Recover.

        :param method callback: Method to call when receiving Basic.RecoverOk
        :param bool requeue: If False, the message will be redelivered to the
                             original recipient. If True, the server will
                             attempt to requeue the message, potentially then
                             delivering it to an alternative subscriber.

        """
        self._validate_channel_and_callback(callback)
        return self._rpc(spec.Basic.Recover(requeue), callback,
                         [spec.Basic.RecoverOk])

    def close(self, reply_code=0, reply_text="Normal Shutdown"):
        """Will invoke a clean shutdown of the channel with the AMQP Broker.

        :param int reply_code: The reply code to close the channel with
        :param str reply_text: The reply text to close the channel with

        """
        if not self.is_open:
            raise exceptions.ChannelClosed()
        LOGGER.info('Channel.close(%s, %s)', reply_code, reply_text)
        if self._consumers:
            LOGGER.debug('Cancelling %i consumers', len(self._consumers))
            for consumer_tag in self._consumers.keys():
                self.basic_cancel(consumer_tag=consumer_tag)
        self._set_state(self.CLOSING)
        self._rpc(spec.Channel.Close(reply_code, reply_text, 0, 0),
                  self._on_closeok, [spec.Channel.CloseOk])

    def confirm_delivery(self, callback=None, nowait=False):
        """Turn on Confirm mode in the channel. Pass in a callback to be
        notified by the Broker when a message has been confirmed as received or
        rejected (Basic.Ack, Basic.Nack) from the broker to the publisher.

        For more information see:
            http://www.rabbitmq.com/extensions.html#confirms

        :param method callback: The callback for delivery confirmations
        :param bool nowait: Do not send a reply frame (Confirm.SelectOk)

        """
        self._validate_channel_and_callback(callback)
        if (self.connection.publisher_confirms is False or
            self.connection.basic_nack is False):
            raise exceptions.MethodNotImplemented('Not Supported on Server')

        # Add the ack and nack callbacks
        if callback is not None:
            self.callbacks.add(self.channel_number,
                               spec.Basic.Ack,
                               callback,
                               False)
            self.callbacks.add(self.channel_number,
                               spec.Basic.Nack,
                               callback,
                               False)

        # Send the RPC command
        self._rpc(spec.Confirm.Select(nowait),
                  self._on_selectok,
                  [spec.Confirm.SelectOk] if nowait is False else [])

    @property
    def consumer_tags(self):
        """Property method that returns a list of currently active consumers

        :rtype: list

        """
        return list(self._consumers.keys())

    def exchange_bind(self, callback=None, destination=None, source=None,
                      routing_key='', nowait=False, arguments=None):
        """Bind an exchange to another exchange.

        :param method callback: The method to call on Exchange.BindOk
        :param destination: The destination exchange to bind
        :type destination: str or unicode
        :param source: The source exchange to bind to
        :type source: str or unicode
        :param routing_key: The routing key to bind on
        :type routing_key: str or unicode
        :param bool nowait: Do not wait for an Exchange.BindOk
        :param dict arguments: Custom key/value pair arguments for the binding

        """
        self._validate_channel_and_callback(callback)
        return self._rpc(spec.Exchange.Bind(0, destination, source,
                                            routing_key, nowait,
                                            arguments or dict()), callback,
                         [spec.Exchange.BindOk] if nowait is False else [])

    def exchange_declare(self, callback=None, exchange=None,
                         exchange_type='direct', passive=False, durable=False,
                         auto_delete=False, internal=False, nowait=False,
                         arguments=None, type=None):
        """This method creates an exchange if it does not already exist, and if
        the exchange exists, verifies that it is of the correct and expected
        class.

        If passive set, the server will reply with Declare-Ok if the exchange
        already exists with the same name, and raise an error if not and if the
        exchange does not already exist, the server MUST raise a channel
        exception with reply code 404 (not found).

        :param method callback: Call this method on Exchange.DeclareOk
        :param exchange: The exchange name consists of a non-empty
        :type exchange: str or unicode
                                     sequence of these characters: letters,
                                     digits, hyphen, underscore, period, or
                                     colon.
        :param str exchange_type: The exchange type to use
        :param bool passive: Perform a declare or just check to see if it exists
        :param bool durable: Survive a reboot of RabbitMQ
        :param bool auto_delete: Remove when no more queues are bound to it
        :param bool internal: Can only be published to by other exchanges
        :param bool nowait: Do not expect an Exchange.DeclareOk response
        :param dict arguments: Custom key/value pair arguments for the exchange
        :param str type: The deprecated exchange type parameter

        """
        self._validate_channel_and_callback(callback)
        if type is not None:
            warnings.warn('type is deprecated, use exchange_type instead',
                          DeprecationWarning)
            if exchange_type == 'direct' and type != exchange_type:
                exchange_type = type
        return self._rpc(spec.Exchange.Declare(0, exchange, exchange_type,
                                               passive, durable, auto_delete,
                                               internal, nowait,
                                               arguments or dict()),
                         callback,
                         [spec.Exchange.DeclareOk] if nowait is False else [])

    def exchange_delete(self, callback=None, exchange=None, if_unused=False,
                        nowait=False):
        """Delete the exchange.

        :param method callback: The method to call on Exchange.DeleteOk
        :param exchange: The exchange name
        :type exchange: str or unicode
        :param bool if_unused: only delete if the exchange is unused
        :param bool nowait: Do not wait for an Exchange.DeleteOk

        """
        self._validate_channel_and_callback(callback)
        return self._rpc(spec.Exchange.Delete(0, exchange, if_unused, nowait),
                         callback,
                         [spec.Exchange.DeleteOk] if nowait is False else [])

    def exchange_unbind(self, callback=None, destination=None, source=None,
                        routing_key='', nowait=False, arguments=None):
        """Unbind an exchange from another exchange.

        :param method callback: The method to call on Exchange.UnbindOk
        :param destination: The destination exchange to unbind
        :type destination: str or unicode
        :param source: The source exchange to unbind from
        :type source: str or unicode
        :param routing_key: The routing key to unbind
        :type routing_key: str or unicode
        :param bool nowait: Do not wait for an Exchange.UnbindOk
        :param dict arguments: Custom key/value pair arguments for the binding

        """
        self._validate_channel_and_callback(callback)
        return self._rpc(spec.Exchange.Unbind(0, destination, source,
                                              routing_key, nowait, arguments),
                         callback,
                         [spec.Exchange.UnbindOk] if nowait is False else [])

    def flow(self, callback, active):
        """Turn Channel flow control off and on. Pass a callback to be notified
        of the response from the server. active is a bool. Callback should
        expect a bool in response indicating channel flow state. For more
        information, please reference:

        http://www.rabbitmq.com/amqp-0-9-1-reference.html#channel.flow

        :param method callback: The callback method
        :param bool active: Turn flow on or off

        """
        self._validate_channel_and_callback(callback)
        self._on_flowok_callback = callback
        self._rpc(spec.Channel.Flow(active),
                  self._on_flowok,
                  [spec.Channel.FlowOk])

    @property
    def is_closed(self):
        """Returns True if the channel is closed.

        :rtype: bool

        """
        return self._state == self.CLOSED

    @property
    def is_closing(self):
        """Returns True if the channel is closing.

        :rtype: bool

        """
        return self._state == self.CLOSING

    @property
    def is_open(self):
        """Returns True if the channel is open.

        :rtype: bool

        """
        return self._state == self.OPEN

    def open(self):
        """Open the channel"""
        self._set_state(self.OPENING)
        self._add_callbacks()
        self._rpc(spec.Channel.Open(), self._on_openok, [spec.Channel.OpenOk])

    def queue_bind(self, callback, queue, exchange, routing_key=None,
                   nowait=False, arguments=None):
        """Bind the queue to the specified exchange

        :param method callback: The method to call on Queue.BindOk
        :param queue: The queue to bind to the exchange
        :type queue: str or unicode
        :param exchange: The source exchange to bind to
        :type exchange: str or unicode
        :param routing_key: The routing key to bind on
        :type routing_key: str or unicode
        :param bool nowait: Do not wait for a Queue.BindOk
        :param dict arguments: Custom key/value pair arguments for the binding

        """
        self._validate_channel_and_callback(callback)
        replies = [spec.Queue.BindOk] if nowait is False else []
        if routing_key is None:
            routing_key = queue
        return self._rpc(spec.Queue.Bind(0, queue, exchange, routing_key,
                                         nowait, arguments or dict()), callback,
                         replies)

    def queue_declare(self, callback, queue='', passive=False, durable=False,
                      exclusive=False, auto_delete=False, nowait=False,
                      arguments=None):
        """Declare queue, create if needed. This method creates or checks a
        queue. When creating a new queue the client can specify various
        properties that control the durability of the queue and its contents,
        and the level of sharing for the queue.

        Leave the queue name empty for a auto-named queue in RabbitMQ

        :param method callback: The method to call on Queue.DeclareOk
        :param queue: The queue name
        :type queue: str or unicode
        :param bool passive: Only check to see if the queue exists
        :param bool durable: Survive reboots of the broker
        :param bool exclusive: Only allow access by the current connection
        :param bool auto_delete: Delete after consumer cancels or disconnects
        :param bool nowait: Do not wait for a Queue.DeclareOk
        :param dict arguments: Custom key/value arguments for the queue

        """
        condition = (spec.Queue.DeclareOk,
                     {'queue': queue}) if queue else spec.Queue.DeclareOk
        replies = [condition] if nowait is False else []
        self._validate_channel_and_callback(callback)
        return self._rpc(spec.Queue.Declare(0, queue, passive, durable,
                                            exclusive, auto_delete, nowait,
                                            arguments or dict()), callback,
                         replies)

    def queue_delete(self, callback=None, queue='', if_unused=False,
                     if_empty=False, nowait=False):
        """Delete a queue from the broker.

        :param method callback: The method to call on Queue.DeleteOk
        :param queue: The queue to delete
        :type queue: str or unicode
        :param bool if_unused: only delete if it's unused
        :param bool if_empty: only delete if the queue is empty
        :param bool nowait: Do not wait for a Queue.DeleteOk

        """
        replies = [spec.Queue.DeleteOk] if nowait is False else []
        self._validate_channel_and_callback(callback)
        return self._rpc(spec.Queue.Delete(0, queue, if_unused, if_empty,
                                           nowait), callback,
                         replies)

    def queue_purge(self, callback=None, queue='', nowait=False):
        """Purge all of the messages from the specified queue

        :param method callback: The method to call on Queue.PurgeOk
        :param queue: The queue to purge
        :type queue: str or unicode
        :param bool nowait: Do not expect a Queue.PurgeOk response

        """
        replies = [spec.Queue.PurgeOk] if nowait is False else []
        self._validate_channel_and_callback(callback)
        return self._rpc(spec.Queue.Purge(0, queue, nowait), callback,
                         replies)

    def queue_unbind(self, callback=None, queue='', exchange=None,
                     routing_key=None, arguments=None):
        """Unbind a queue from an exchange.

        :param method callback: The method to call on Queue.UnbindOk
        :param queue: The queue to unbind from the exchange
        :type queue: str or unicode
        :param exchange: The source exchange to bind from
        :type exchange: str or unicode
        :param routing_key: The routing key to unbind
        :type routing_key: str or unicode
        :param dict arguments: Custom key/value pair arguments for the binding

        """
        self._validate_channel_and_callback(callback)
        if routing_key is None:
            routing_key = queue
        return self._rpc(spec.Queue.Unbind(0, queue, exchange, routing_key,
                                           arguments or dict()), callback,
                         [spec.Queue.UnbindOk])

    def tx_commit(self, callback=None):
        """Commit a transaction

        :param method callback: The callback for delivery confirmations

        """
        self._validate_channel_and_callback(callback)
        return self._rpc(spec.Tx.Commit(), callback, [spec.Tx.CommitOk])

    def tx_rollback(self, callback=None):
        """Rollback a transaction.

        :param method callback: The callback for delivery confirmations

        """
        self._validate_channel_and_callback(callback)
        return self._rpc(spec.Tx.Rollback(), callback, [spec.Tx.RollbackOk])

    def tx_select(self, callback=None):
        """Select standard transaction mode. This method sets the channel to use
        standard transactions. The client must use this method at least once on
        a channel before using the Commit or Rollback methods.

        :param method callback: The callback for delivery confirmations

        """
        self._validate_channel_and_callback(callback)
        return self._rpc(spec.Tx.Select(), callback, [spec.Tx.SelectOk])

    # Internal methods

    def _add_callbacks(self):
        """Callbacks that add the required behavior for a channel when
        connecting and connected to a server.

        """
        # Add a callback for Basic.GetEmpty
        self.callbacks.add(self.channel_number,
                           spec.Basic.GetEmpty,
                           self._on_getempty,
                           False)

        # Add a callback for Basic.Cancel
        self.callbacks.add(self.channel_number,
                           spec.Basic.Cancel,
                           self._on_cancel,
                           False)

        # Deprecated in newer versions of RabbitMQ but still register for it
        self.callbacks.add(self.channel_number,
                           spec.Channel.Flow,
                           self._on_flow,
                           False)

        # Add a callback for when the server closes our channel
        self.callbacks.add(self.channel_number,
                           spec.Channel.Close,
                           self._on_close,
                           True)

    def _add_pending_msg(self, consumer_tag, method_frame,  header_frame, body):
        """Add the received message to the pending message stack.

        :param str consumer_tag: The consumer tag for the message
        :param pika.frame.Method method_frame: The received method frame
        :param pika.frame.Header header_frame: The received header frame
        :param body: The message body
        :type body: str or unicode

        """
        self._pending[consumer_tag].append((self, method_frame.method,
                                            header_frame.properties, body))

    def _cleanup(self):
        """Remove all consumers and any callbacks for the channel."""
        self._consumers = dict()
        self.callbacks.cleanup(str(self.channel_number))

    def _get_pending_msg(self, consumer_tag):
        """Get a pending message for the consumer tag from the stack.

        :param str consumer_tag: The consumer tag to get a message from
        :rtype: tuple(pika.frame.Header, pika.frame.Method, str|unicode)

        """
        return self._pending[consumer_tag].pop(0)

    def _handle_content_frame(self, frame_value):
        """This is invoked by the connection when frames that are not registered
        with the CallbackManager have been found. This should only be the case
        when the frames are related to content delivery.

        The frame_dispatcher will be invoked which will return the fully formed
        message in three parts when all of the body frames have been received.

        :param pika.amqp_object.Frame frame_value: The frame to deliver

        """
        try:
            response = self.frame_dispatcher.process(frame_value)
        except exceptions.UnexpectedFrameError:
            return self._unexpected_frame(frame_value)

        if response:
            if isinstance(response[0].method, spec.Basic.Deliver):
                self._on_deliver(*response)
            elif isinstance(response[0].method, spec.Basic.GetOk):
                self._on_getok(*response)
            elif isinstance(response[0].method, spec.Basic.Return):
                self._on_return(*response)

    def _has_content(self, method_frame):
        """Return a bool if it's a content method as defined by the spec

        :param pika.amqp_object.Method method_frame: The method frame received

        """
        return spec.has_content(method_frame.INDEX)

    def _on_cancel(self, method_frame):
        """When the broker cancels a consumer, delete it from our internal
        dictionary.

        :param pika.frame.Method method_frame: The method frame received

        """
        self._cancelled.append(method_frame.method.consumer_tag)
        if method_frame.method.consumer_tag in self._consumers:
            del self._consumers[method_frame.method.consumer_tag]

    def _on_cancelok(self, method_frame):
        """Called in response to a frame from the Broker when the
         client sends Basic.Cancel

        :param pika.frame.Method method_frame: The method frame received

        """
        if method_frame.method.consumer_tag in self._consumers:
            del self._consumers[method_frame.method.consumer_tag]
        if method_frame.method.consumer_tag in self._pending:
            del self._pending[method_frame.method.consumer_tag]

    def _on_close(self, method_frame):
        """Handle the case where our channel has been closed for us

        :param pika.frame.Method method_frame: The close frame

        """
        LOGGER.info('%s', method_frame)
        LOGGER.warning('Received remote Channel.Close (%s): %s',
                       method_frame.method.reply_code,
                       method_frame.method.reply_text)
        if self.connection.is_open:
            self._send_method(spec.Channel.CloseOk())
        self._set_state(self.CLOSED)
        self.callbacks.process(self.channel_number,
                               '_on_channel_close',
                               self, self,
                               method_frame.method.reply_code,
                               method_frame.method.reply_text)
        self._cleanup()

    def _on_closeok(self, method_frame):
        """Invoked when RabbitMQ replies to a Channel.Close method

        :param pika.frame.Method method_frame: The CloseOk frame

        """
        self._set_state(self.CLOSED)
        self.callbacks.process(self.channel_number,
                               '_on_channel_close',
                               self, self,
                               0, '')
        self._cleanup()

    def _on_deliver(self, method_frame, header_frame, body):
        """Cope with reentrancy. If a particular consumer is still active when
        another delivery appears for it, queue the deliveries up until it
        finally exits.

        :param pika.frame.Method method_frame: The method frame received
        :param pika.frame.Header header_frame: The header frame received
        :param body: The body received
        :type body: str or unicode

        """
        consumer_tag = method_frame.method.consumer_tag
        if consumer_tag in self._cancelled:
            if self.is_open:
                self.basic_reject(method_frame.method.delivery_tag)
            return
        if consumer_tag not in self._consumers:
            return self._add_pending_msg(consumer_tag, method_frame,
                                         header_frame, body)
        while self._pending[consumer_tag]:
            self._consumers[consumer_tag](*self._get_pending_msg(consumer_tag))
        self._consumers[consumer_tag](self,
                                      method_frame.method,
                                      header_frame.properties,
                                      body)

    def _on_eventok(self, method_frame):
        """Generic events that returned ok that may have internal callbacks.
        We keep a list of what we've yet to implement so that we don't silently
        drain events that we don't support.

        :param pika.frame.Method method_frame: The method frame received

        """
        LOGGER.debug('Discarding frame %r', method_frame)

    def _on_flow(self, method_frame_unused):
        """Called if the server sends a Channel.Flow frame.

        :param pika.frame.Method method_frame_unused: The Channel.Flow frame

        """
        if self._has_on_flow_callback is False:
            LOGGER.warning('Channel.Flow received from server')

    def _on_flowok(self, method_frame):
        """Called in response to us asking the server to toggle on Channel.Flow

        :param pika.frame.Method method_frame: The method frame received

        """
        self.flow_active = method_frame.method.active
        if self._on_flowok_callback:
            self._on_flowok_callback(method_frame.method.active)
            self._on_flowok_callback = None
        else:
            LOGGER.warning('Channel.FlowOk received with no active callbacks')

    def _on_getempty(self, method_frame):
        """When we receive an empty reply do nothing but log it

        :param pika.frame.Method method_frame: The method frame received

        """
        LOGGER.debug('Received Basic.GetEmpty: %r', method_frame)

    def _on_getok(self, method_frame, header_frame, body):
        """Called in reply to a Basic.Get when there is a message.

        :param pika.frame.Method method_frame: The method frame received
        :param pika.frame.Header header_frame: The header frame received
        :param body: The body received
        :type body: str or unicode

        """
        if self._on_getok_callback is not None:
            callback = self._on_getok_callback
            self._on_getok_callback = None
            callback(self,
                     method_frame.method,
                     header_frame.properties,
                     body)
        else:
            LOGGER.error('Basic.GetOk received with no active callback')

    def _on_openok(self, frame_unused):
        """Called by our callback handler when we receive a Channel.OpenOk and
        subsequently calls our _on_openok_callback which was passed into the
        Channel constructor. The reason we do this is because we want to make
        sure that the on_open_callback parameter passed into the Channel
        constructor is not the first callback we make.

        :param pika.frame.Method frame_unused: Unused Channel.OpenOk frame

        """
        self._set_state(self.OPEN)
        if self._on_openok_callback is not None:
            self._on_openok_callback(self)

    def _on_return(self, method_frame, header_frame, body):
        """Called if the server sends a Basic.Return frame.

        :param pika.frame.Method method_frame: The Basic.Return frame
        :param pika.frame.Header header_frame: The content header frame
        :param body: The message body
        :type body: str or unicode

        """
        if not self.callbacks.process(self.channel_number, '_on_return', self,
                                      (self,
                                       method_frame.method,
                                       header_frame.properties,
                                       body)):
            LOGGER.warning('Basic.Return received from server (%r, %r)',
                           method_frame.method, header_frame.properties)

    def _on_selectok(self, method_frame):
        """Called when the broker sends a Confirm.SelectOk frame

        :param pika.frame.Method method_frame: The method frame received

        """
        LOGGER.debug("Confirm.SelectOk Received: %r", method_frame)

    def _on_synchronous_complete(self, method_frame_unused):
        """This is called when a synchronous command is completed. It will undo
        the blocking state and send all the frames that stacked up while we
        were in the blocking state.

        :param pika.frame.Method method_frame_unused: The method frame received

        """
        LOGGER.debug('%i blocked frames', len(self._blocked))
        self._blocking = None
        while len(self._blocked) > 0 and self._blocking is None:
            self._rpc(*self._blocked.popleft())

    def _rpc(self, method_frame, callback=None, acceptable_replies=None):
        """Shortcut wrapper to the Connection's rpc command using its callback
        stack, passing in our channel number.

        :param pika.amqp_object.Method method_frame: The method frame to call
        :param method callback: The callback for the RPC response
        :param list acceptable_replies: The replies this RPC call expects

        """
        # Make sure the channel is open
        if self.is_closed:
            raise exceptions.ChannelClosed

        # If the channel is blocking, add subsequent commands to our stack
        if self._blocking:
            return self._blocked.append([method_frame,
                                         callback,
                                         acceptable_replies])

        # Validate we got None or a list of acceptable_replies
        if acceptable_replies and not isinstance(acceptable_replies, list):
            raise TypeError("acceptable_replies should be list or None")

        # Validate the callback is callable
        if callback and not is_callable(callback):
            raise TypeError("callback should be None, a function or method.")

        # Block until a response frame is received for synchronous frames
        if method_frame.synchronous:
            self.blocking = method_frame.NAME

        # If acceptable replies are set, add callbacks
        if acceptable_replies:
            for reply in acceptable_replies or list():
                if isinstance(reply, tuple):
                    reply, arguments = reply
                else:
                    arguments = None
                LOGGER.debug('Adding in on_synchronous_complete callback')
                self.callbacks.add(self.channel_number, reply,
                                   self._on_synchronous_complete,
                                   arguments=arguments)
                if callback:
                    LOGGER.debug('Adding passed in callback')
                    self.callbacks.add(self.channel_number, reply, callback,
                                       arguments=arguments)

        self._send_method(method_frame)

    def _send_method(self, method_frame, content=None):
        """Shortcut wrapper to send a method through our connection, passing in
        the channel number

        :param pika.object.Method method_frame: The method frame to send
        :param tuple content: If set, is a content frame, is tuple of
                              properties and body.

        """
        self.connection._send_method(self.channel_number, method_frame, content)

    def _set_state(self, connection_state):
        """Set the channel connection state to the specified state value.

        :param int connection_state: The connection_state value

        """
        self._state = connection_state

    def _unexpected_frame(self, frame_value):
        """Invoked when a frame is received that is not setup to be processed.

        :param pika.frame.Frame frame_value: The frame received

        """
        LOGGER.warning('Unexpected frame: %r', frame_value)

    def _validate_channel_and_callback(self, callback):
        if not self.is_open:
            raise exceptions.ChannelClosed()
        if callback is not None and not is_callable(callback):
            raise ValueError('callback must be a function or method')



class ContentFrameDispatcher(object):
    """Handle content related frames, building a message and return the message
    back in three parts upon receipt.

    """
    def __init__(self):
        """Create a new instance of the Dispatcher passing in the callback
        manager.

        """
        self._method_frame = None
        self._header_frame = None
        self._seen_so_far = 0
        self._body_fragments = list()

    def process(self, frame_value):
        """Invoked by the Channel object when passed frames that are not
        setup in the rpc process and that don't have explicit reply types
        defined. This includes Basic.Publish, Basic.GetOk and Basic.Return

        :param Method|Header|Body frame_value: The frame to process

        """
        if (isinstance(frame_value, frame.Method) and
            spec.has_content(frame_value.method.INDEX)):
            self._method_frame = frame_value
        elif isinstance(frame_value, frame.Header):
            self._header_frame = frame_value
            if frame_value.body_size == 0:
                return self._finish()
        elif isinstance(frame_value, frame.Body):
            return self._handle_body_frame(frame_value)
        else:
            raise exceptions.UnexpectedFrameError(frame_value)

    def _finish(self):
        """Invoked when all of the message has been received

        :rtype: tuple(pika.frame.Method, pika.frame.Header, str)

        """
        content = (self._method_frame,
                   self._header_frame,
                   ''.join(self._body_fragments))
        self._reset()
        return content

    def _handle_body_frame(self, body_frame):
        """Receive body frames and append them to the stack. When the body size
        matches, call the finish method.

        :param Body body_frame: The body frame
        :raises: pika.exceptions.BodyTooLongError
        :rtype: tuple(pika.frame.Method, pika.frame.Header, str)|None

        """
        self._seen_so_far += len(body_frame.fragment)
        self._body_fragments.append(body_frame.fragment)
        if self._seen_so_far == self._header_frame.body_size:
            return self._finish()
        elif self._seen_so_far > self._header_frame.body_size:
            raise exceptions.BodyTooLongError(self._seen_so_far,
                                              self._header_frame.body_size)
        return None

    def _reset(self):
        """Reset the values for processing frames"""
        self._method_frame = None
        self._header_frame = None
        self._seen_so_far = 0
        self._body_fragments = list()

########NEW FILE########
__FILENAME__ = connection
"""Core connection objects"""
import ast
import sys
import collections
import logging
import math
import platform
import urllib
import warnings

if sys.version_info > (3,):
    import urllib.parse as urlparse
else:
    import urlparse

from pika import __version__
from pika import callback
from pika import channel
from pika import credentials as pika_credentials
from pika import exceptions
from pika import frame
from pika import heartbeat
from pika import utils

from pika import spec

BACKPRESSURE_WARNING = ("Pika: Write buffer exceeded warning threshold at "
                        "%i bytes and an estimated %i frames behind")
PRODUCT = "Pika Python Client Library"

LOGGER = logging.getLogger(__name__)


class Parameters(object):
    """Base connection parameters class definition

    :param str DEFAULT_HOST: 'localhost'
    :param int DEFAULT_PORT: 5672
    :param str DEFAULT_VIRTUAL_HOST: '/'
    :param str DEFAULT_USERNAME: 'guest'
    :param str DEFAULT_PASSWORD: 'guest'
    :param int DEFAULT_HEARTBEAT_INTERVAL: 0
    :param int DEFAULT_CHANNEL_MAX: 0
    :param int DEFAULT_FRAME_MAX: pika.spec.FRAME_MAX_SIZE
    :param str DEFAULT_LOCALE: 'en_US'
    :param int DEFAULT_CONNECTION_ATTEMPTS: 1
    :param int|float DEFAULT_RETRY_DELAY: 2.0
    :param int|float DEFAULT_SOCKET_TIMEOUT: 0.25
    :param bool DEFAULT_SSL: False
    :param dict DEFAULT_SSL_OPTIONS: {}
    :param int DEFAULT_SSL_PORT: 5671
    :param bool DEFAULT_BACKPRESSURE_DETECTION: False

    """
    DEFAULT_BACKPRESSURE_DETECTION = False
    DEFAULT_CONNECTION_ATTEMPTS = 1
    DEFAULT_CHANNEL_MAX = 0
    DEFAULT_FRAME_MAX = spec.FRAME_MAX_SIZE
    DEFAULT_HEARTBEAT_INTERVAL = 0
    DEFAULT_HOST = 'localhost'
    DEFAULT_LOCALE = 'en_US'
    DEFAULT_PASSWORD = 'guest'
    DEFAULT_PORT = 5672
    DEFAULT_RETRY_DELAY = 2.0
    DEFAULT_SOCKET_TIMEOUT = 0.25
    DEFAULT_SSL = False
    DEFAULT_SSL_OPTIONS = {}
    DEFAULT_SSL_PORT = 5671
    DEFAULT_USERNAME = 'guest'
    DEFAULT_VIRTUAL_HOST = '/'

    def __init__(self):
        self.virtual_host = self.DEFAULT_VIRTUAL_HOST
        self.backpressure_detection = self.DEFAULT_BACKPRESSURE_DETECTION
        self.channel_max = self.DEFAULT_CHANNEL_MAX
        self.connection_attempts = self.DEFAULT_CONNECTION_ATTEMPTS
        self.credentials = self._credentials(self.DEFAULT_USERNAME,
                                             self.DEFAULT_PASSWORD)
        self.frame_max = self.DEFAULT_FRAME_MAX
        self.heartbeat = self.DEFAULT_HEARTBEAT_INTERVAL
        self.host = self.DEFAULT_HOST
        self.locale = self.DEFAULT_LOCALE
        self.port = self.DEFAULT_PORT
        self.retry_delay = self.DEFAULT_RETRY_DELAY
        self.ssl = self.DEFAULT_SSL
        self.ssl_options = self.DEFAULT_SSL_OPTIONS
        self.socket_timeout = self.DEFAULT_SOCKET_TIMEOUT

    def __repr__(self):
        """Represent the info about the instance.

        :rtype: str

        """
        return ('<%s host=%s port=%s virtual_host=%s ssl=%s>' %
                (self.__class__.__name__, self.host, self.port,
                 self.virtual_host, self.ssl))

    def _credentials(self, username, password):
        """Return a plain credentials object for the specified username and
        password.

        :param str username: The username to use
        :param str password: The password to use
        :rtype: pika_credentials.PlainCredentials

        """
        return pika_credentials.PlainCredentials(username, password)

    def _validate_backpressure(self, backpressure_detection):
        """Validate that the backpressure detection option is a bool.

        :param bool backpressure_detection: The backpressure detection value
        :rtype: bool
        :raises: TypeError

        """
        if not isinstance(backpressure_detection, bool):
            raise TypeError('backpressure detection must be a bool')
        return True

    def _validate_channel_max(self, channel_max):
        """Validate that the channel_max value is an int

        :param int channel_max: The value to validate
        :rtype: bool
        :raises: TypeError
        :raises: ValueError

        """
        if not isinstance(channel_max, int):
            raise TypeError('channel_max must be an int')
        if channel_max < 1 or channel_max > 65535:
            raise ValueError('channel_max must be <= 65535 and > 0')
        return True

    def _validate_connection_attempts(self, connection_attempts):
        """Validate that the channel_max value is an int

        :param int connection_attempts: The value to validate
        :rtype: bool
        :raises: TypeError
        :raises: ValueError

        """
        if not isinstance(connection_attempts, int):
            raise TypeError('connection_attempts must be an int')
        if connection_attempts < 1:
            raise ValueError('connection_attempts must be None or > 0')
        return True

    def _validate_credentials(self, credentials):
        """Validate the credentials passed in are using a valid object type.

        :param pika.credentials.Credentials credentials: Credentials to validate
        :rtype: bool
        :raises: TypeError

        """
        for credential_type in pika_credentials.VALID_TYPES:
            if isinstance(credentials, credential_type):
                return True
        raise TypeError('Credentials must be an object of type: %r' %
                        pika_credentials.VALID_TYPES)

    def _validate_frame_max(self, frame_max):
        """Validate that the frame_max value is an int and does not exceed
         the maximum frame size and is not less than the frame min size.

        :param int frame_max: The value to validate
        :rtype: bool
        :raises: TypeError
        :raises: InvalidMinimumFrameSize

        """
        if not isinstance(frame_max, int):
            raise TypeError('frame_max must be an int')
        if frame_max < spec.FRAME_MIN_SIZE:
            raise exceptions.InvalidMinimumFrameSize
        elif frame_max > spec.FRAME_MAX_SIZE:
            raise exceptions.InvalidMaximumFrameSize
        return True

    def _validate_heartbeat_interval(self, heartbeat_interval):
        """Validate that the heartbeat_interval value is an int

        :param int heartbeat_interval: The value to validate
        :rtype: bool
        :raises: TypeError
        :raises: ValueError

        """
        if not isinstance(heartbeat_interval, int):
            raise TypeError('heartbeat must be an int')
        if heartbeat_interval < 0:
            raise ValueError('heartbeat_interval must >= 0')
        return True

    def _validate_host(self, host):
        """Validate that the host value is an str

        :param str|unicode host: The value to validate
        :rtype: bool
        :raises: TypeError

        """
        if not isinstance(host, basestring):
            raise TypeError('host must be a str or unicode str')
        return True

    def _validate_locale(self, locale):
        """Validate that the locale value is an str

        :param str locale: The value to validate
        :rtype: bool
        :raises: TypeError

        """
        if not isinstance(locale, basestring):
            raise TypeError('locale must be a str')
        return True

    def _validate_port(self, port):
        """Validate that the port value is an int

        :param int port: The value to validate
        :rtype: bool
        :raises: TypeError

        """
        if not isinstance(port, int):
            raise TypeError('port must be an int')
        return True

    def _validate_retry_delay(self, retry_delay):
        """Validate that the retry_delay value is an int or float

        :param int|float retry_delay: The value to validate
        :rtype: bool
        :raises: TypeError

        """
        if not any([isinstance(retry_delay, int),
                    isinstance(retry_delay, float)]):
            raise TypeError('retry_delay must be a float or int')
        return True

    def _validate_socket_timeout(self, socket_timeout):
        """Validate that the socket_timeout value is an int or float

        :param int|float socket_timeout: The value to validate
        :rtype: bool
        :raises: TypeError

        """
        if not any([isinstance(socket_timeout, int),
                    isinstance(socket_timeout, float)]):
            raise TypeError('socket_timeout must be a float or int')
        if not socket_timeout > 0:
            raise ValueError('socket_timeout must be > 0')
        return True

    def _validate_ssl(self, ssl):
        """Validate the SSL toggle is a bool

        :param bool ssl: The SSL enabled/disabled value
        :rtype: bool
        :raises: TypeError

        """
        if not isinstance(ssl, bool):
            raise TypeError('ssl must be a bool')
        return True

    def _validate_ssl_options(self, ssl_options):
        """Validate the SSL options value is a dictionary.

        :param dict|None ssl_options: SSL Options to validate
        :rtype: bool
        :raises: TypeError

        """
        if not isinstance(ssl_options, dict) and ssl_options is not None:
            raise TypeError('ssl_options must be either None or dict')
        return True

    def _validate_virtual_host(self, virtual_host):
        """Validate that the virtual_host value is an str

        :param str virtual_host: The value to validate
        :rtype: bool
        :raises: TypeError

        """
        if not isinstance(virtual_host, basestring):
            raise TypeError('virtual_host must be a str')
        return True


class ConnectionParameters(Parameters):
    """Connection parameters object that is passed into the connection adapter
    upon construction.

    :param str host: Hostname or IP Address to connect to
    :param int port: TCP port to connect to
    :param str virtual_host: RabbitMQ virtual host to use
    :param pika.credentials.Credentials credentials: auth credentials
    :param int channel_max: Maximum number of channels to allow
    :param int frame_max: The maximum byte size for an AMQP frame
    :param int heartbeat_interval: How often to send heartbeats
    :param bool ssl: Enable SSL
    :param dict ssl_options: Arguments passed to ssl.wrap_socket as
    :param int connection_attempts: Maximum number of retry attempts
    :param int|float retry_delay: Time to wait in seconds, before the next
    :param int|float socket_timeout: Use for high latency networks
    :param str locale: Set the locale value
    :param bool backpressure_detection: Toggle backpressure detection

    """
    def __init__(self,
                 host=None,
                 port=None,
                 virtual_host=None,
                 credentials=None,
                 channel_max=None,
                 frame_max=None,
                 heartbeat_interval=None,
                 ssl=None,
                 ssl_options=None,
                 connection_attempts=None,
                 retry_delay=None,
                 socket_timeout=None,
                 locale=None,
                 backpressure_detection=None):
        """Create a new ConnectionParameters instance.

        :param str host: Hostname or IP Address to connect to
        :param int port: TCP port to connect to
        :param str virtual_host: RabbitMQ virtual host to use
        :param pika.credentials.Credentials credentials: auth credentials
        :param int channel_max: Maximum number of channels to allow
        :param int frame_max: The maximum byte size for an AMQP frame
        :param int heartbeat_interval: How often to send heartbeats
        :param bool ssl: Enable SSL
        :param dict ssl_options: Arguments passed to ssl.wrap_socket
        :param int connection_attempts: Maximum number of retry attempts
        :param int|float retry_delay: Time to wait in seconds, before the next
        :param int|float socket_timeout: Use for high latency networks
        :param str locale: Set the locale value
        :param bool backpressure_detection: Toggle backpressure detection

        """
        super(ConnectionParameters, self).__init__()

        # Create the default credentials object
        if not credentials:
            credentials = self._credentials(self.DEFAULT_USERNAME,
                                            self.DEFAULT_PASSWORD)

        # Assign the values
        if host and self._validate_host(host):
            self.host = host
        if port is not None and self._validate_port(port):
            self.port = port
        if virtual_host and self._validate_virtual_host(virtual_host):
            self.virtual_host = virtual_host
        if credentials and self._validate_credentials(credentials):
            self.credentials = credentials
        if channel_max is not None and self._validate_channel_max(channel_max):
            self.channel_max = channel_max
        if frame_max is not None and self._validate_frame_max(frame_max):
            self.frame_max = frame_max
        if locale and self._validate_locale(locale):
            self.locale = locale
        if (heartbeat_interval is not None and
            self._validate_heartbeat_interval(heartbeat_interval)):
            self.heartbeat = heartbeat_interval
        if ssl is not None and self._validate_ssl(ssl):
            self.ssl = ssl
        if ssl_options and self._validate_ssl_options(ssl_options):
            self.ssl_options = ssl_options or dict()
        if (connection_attempts is not None and
            self._validate_connection_attempts(connection_attempts)):
            self.connection_attempts = connection_attempts
        if retry_delay is not None and self._validate_retry_delay(retry_delay):
            self.retry_delay = retry_delay
        if (socket_timeout is not None and
            self._validate_socket_timeout(socket_timeout)):
            self.socket_timeout = socket_timeout
        if (backpressure_detection is not None and
            self._validate_backpressure(backpressure_detection)):
            self.backpressure_detection = backpressure_detection


class URLParameters(Parameters):
    """Connect to RabbitMQ via an AMQP URL in the format::

         amqp://username:password@host:port/<virtual_host>[?query-string]

    Ensure that the virtual host is URI encoded when specified. For example if
    you are using the default "/" virtual host, the value should be `%2f`.

    Valid query string values are:

        - backpressure_detection:
            Toggle backpressure detection, possible values are `t` or `f`
        - channel_max:
            Override the default maximum channel count value
        - connection_attempts:
            Specify how many times pika should try and reconnect before it gives up
        - frame_max:
            Override the default maximum frame size for communication
        - heartbeat_interval:
            Specify the number of seconds between heartbeat frames to ensure that
            the link between RabbitMQ and your application is up
        - locale:
            Override the default `en_US` locale value
        - ssl:
            Toggle SSL, possible values are `t`, `f`
        - ssl_options:
            Arguments passed to :meth:`ssl.wrap_socket`
        - retry_delay:
            The number of seconds to sleep before attempting to connect on
            connection failure.
        - socket_timeout:
            Override low level socket timeout value

    :param str url: The AMQP URL to connect to

    """
    def __init__(self, url):

        """Create a new URLParameters instance.

        :param str url: The URL value

        """
        super(URLParameters, self).__init__()
        self._process_url(url)

    def _process_url(self, url):
        """Take an AMQP URL and break it up into the various parameters.

        :param str url: The URL to parse

        """
        if url[0:4] == 'amqp':
            url = 'http' + url[4:]

        parts = urlparse.urlparse(url)

        # Handle the Protocol scheme, changing to HTTPS so urlparse doesnt barf
        if parts.scheme == 'https':
            self.ssl = True

        if self._validate_host(parts.hostname):
            self.host = parts.hostname
        if not parts.port:
            if self.ssl:
                self.port = self.DEFAULT_SSL_PORT if \
                    self.ssl else self.DEFAULT_PORT
        elif self._validate_port(parts.port):
            self.port = parts.port
        self.credentials = pika_credentials.PlainCredentials(parts.username,
                                                             parts.password)

        # Get the Virtual Host
        if len(parts.path) <= 1:
            self.virtual_host = self.DEFAULT_VIRTUAL_HOST
        else:
            path_parts = parts.path.split('/')
            virtual_host = urllib.unquote(path_parts[1])
            if self._validate_virtual_host(virtual_host):
                self.virtual_host = virtual_host

        # Handle query string values, validating and assigning them
        values = urlparse.parse_qs(parts.query)

        # Cast the various numeric values to the appropriate values
        for key in values.keys():
            # Always reassign the first list item in query values
            values[key] = values[key].pop(0)
            if values[key].isdigit():
                values[key] = int(values[key])
            else:
                try:
                    values[key] = float(values[key])
                except ValueError:
                    pass

        if 'backpressure_detection' in values:
            if values['backpressure_detection'] == 't':
                self.backpressure_detection = True
            elif values['backpressure_detection'] == 'f':
                self.backpressure_detection = False
            else:
                raise ValueError('Invalid backpressure_detection value: %s' %
                                 values['backpressure_detection'])

        if ('channel_max' in values and
            self._validate_channel_max(values['channel_max'])):
            self.channel_max = values['channel_max']

        if ('connection_attempts' in values and
            self._validate_connection_attempts(values['connection_attempts'])):
            self.connection_attempts = values['connection_attempts']

        if ('frame_max' in values and
            self._validate_frame_max(values['frame_max'])):
            self.frame_max = values['frame_max']

        if ('heartbeat_interval' in values and
            self._validate_heartbeat_interval(values['heartbeat_interval'])):
            self.heartbeat = values['heartbeat_interval']

        if ('locale' in values and
            self._validate_locale(values['locale'])):
            self.locale = values['locale']

        if ('retry_delay' in values and
            self._validate_retry_delay(values['retry_delay'])):
            self.retry_delay = values['retry_delay']

        if ('socket_timeout' in values and
            self._validate_socket_timeout(values['socket_timeout'])):
            self.socket_timeout = values['socket_timeout']

        if 'ssl_options' in values:
            options = ast.literal_eval(values['ssl_options'])
            if self._validate_ssl_options(options):
                self.ssl_options = options


class Connection(object):
    """This is the core class that implements communication with RabbitMQ. This
    class should not be invoked directly but rather through the use of an
    adapter such as SelectConnection or BlockingConnection.

    :param pika.connection.Parameters parameters: Connection parameters
    :param method on_open_callback: Called when the connection is opened
    :param method on_open_error_callback: Called if the connection cant
                                   be opened
    :param method on_close_callback: Called when the connection is closed

    """
    ON_CONNECTION_BACKPRESSURE = '_on_connection_backpressure'
    ON_CONNECTION_CLOSED = '_on_connection_closed'
    ON_CONNECTION_ERROR = '_on_connection_error'
    ON_CONNECTION_OPEN = '_on_connection_open'
    CONNECTION_CLOSED = 0
    CONNECTION_INIT = 1
    CONNECTION_PROTOCOL = 2
    CONNECTION_START = 3
    CONNECTION_TUNE = 4
    CONNECTION_OPEN = 5
    CONNECTION_CLOSING = 6

    def __init__(self,
                 parameters=None,
                 on_open_callback=None,
                 on_open_error_callback=None,
                 on_close_callback=None):
        """Connection initialization expects an object that has implemented the
         Parameters class and a callback function to notify when we have
         successfully connected to the AMQP Broker.

        Available Parameters classes are the ConnectionParameters class and
        URLParameters class.

        :param pika.connection.Parameters parameters: Connection parameters
        :param method on_open_callback: Called when the connection is opened
        :param method on_open_error_callback: Called if the connection cant
                                       be opened
        :param method on_close_callback: Called when the connection is closed

        """
        # Define our callback dictionary
        self.callbacks = callback.CallbackManager()

        # Add the on connection error callback
        self.callbacks.add(0, self.ON_CONNECTION_ERROR,
                           on_open_error_callback or self._on_connection_error,
                           False)

        # On connection callback
        if on_open_callback:
            self.add_on_open_callback(on_open_callback)

        # On connection callback
        if on_close_callback:
            self.add_on_close_callback(on_close_callback)

        # Set our configuration options
        self.params = parameters or ConnectionParameters()

        # Initialize the connection state and connect
        self._init_connection_state()
        self.connect()

    def add_backpressure_callback(self, callback_method):
        """Call method "callback" when pika believes backpressure is being
        applied.

        :param method callback_method: The method to call

        """
        self.callbacks.add(0, self.ON_CONNECTION_BACKPRESSURE,
                           callback_method, False)

    def add_on_close_callback(self, callback_method):
        """Add a callback notification when the connection has closed. The
        callback will be passed the connection, the reply_code (int) and the
        reply_text (str), if sent by the remote server.

        :param method callback_method: Callback to call on close

        """
        self.callbacks.add(0, self.ON_CONNECTION_CLOSED, callback_method, False)

    def add_on_open_callback(self, callback_method):
        """Add a callback notification when the connection has opened.

        :param method callback_method: Callback to call when open

        """
        self.callbacks.add(0, self.ON_CONNECTION_OPEN, callback_method, False)

    def add_on_open_error_callback(self, callback_method, remove_default=True):
        """Add a callback notification when the connection can not be opened.

        The callback method should accept the connection object that could not
        connect, and an optional error message.

        :param method callback_method: Callback to call when can't connect
        :param bool remove_default: Remove default exception raising callback

        """
        if remove_default:
            self.callbacks.remove(0, self.ON_CONNECTION_ERROR,
                                  self._on_connection_error)
        self.callbacks.add(0, self.ON_CONNECTION_ERROR, callback_method, False)

    def add_timeout(self, deadline, callback_method):
        """Adapters should override to call the callback after the
        specified number of seconds have elapsed, using a timer, or a
        thread, or similar.

        :param int deadline: The number of seconds to wait to call callback
        :param method callback_method: The callback method

        """
        raise NotImplementedError

    def channel(self, on_open_callback, channel_number=None):
        """Create a new channel with the next available channel number or pass
        in a channel number to use. Must be non-zero if you would like to
        specify but it is recommended that you let Pika manage the channel
        numbers.

        :param method on_open_callback: The callback when the channel is opened
        :param int channel_number: The channel number to use, defaults to the
                                   next available.
        :rtype: pika.channel.Channel

        """
        if not channel_number:
            channel_number = self._next_channel_number()
        self._channels[channel_number] = self._create_channel(channel_number,
                                                              on_open_callback)
        self._add_channel_callbacks(channel_number)
        self._channels[channel_number].open()
        return self._channels[channel_number]

    def close(self, reply_code=200, reply_text='Normal shutdown'):
        """Disconnect from RabbitMQ. If there are any open channels, it will
        attempt to close them prior to fully disconnecting. Channels which
        have active consumers will attempt to send a Basic.Cancel to RabbitMQ
        to cleanly stop the delivery of messages prior to closing the channel.

        :param int reply_code: The code number for the close
        :param str reply_text: The text reason for the close

        """
        if self.is_closing or self.is_closed:
            return

        if self._has_open_channels:
            self._close_channels(reply_code, reply_text)

        # Set our connection state
        self._set_connection_state(self.CONNECTION_CLOSING)
        LOGGER.info("Closing connection (%s): %s", reply_code, reply_text)
        self.closing = reply_code, reply_text

        if not self._has_open_channels:
            # if there are open channels then _on_close_ready will finally be
            # called in _on_channel_closeok once all channels have been closed
            self._on_close_ready()

    def connect(self):
        """Invoke if trying to reconnect to a RabbitMQ server. Constructing the
        Connection object should connect on its own.

        """
        self._set_connection_state(self.CONNECTION_INIT)
        error = self._adapter_connect()
        if not error:
            return self._on_connected()
        self.remaining_connection_attempts -= 1
        LOGGER.warning('Could not connect, %i attempts left',
                       self.remaining_connection_attempts)
        if self.remaining_connection_attempts:
            LOGGER.info('Retrying in %i seconds', self.params.retry_delay)
            self.add_timeout(self.params.retry_delay, self.connect)
        else:
            self.callbacks.process(0, self.ON_CONNECTION_ERROR, self, self, error)
            self.remaining_connection_attempts = self.params.connection_attempts
            self._set_connection_state(self.CONNECTION_CLOSED)

    def remove_timeout(self, callback_method):
        """Adapters should override to call the callback after the
        specified number of seconds have elapsed, using a timer, or a
        thread, or similar.

        :param method callback_method: The callback to remove a timeout for

        """
        raise NotImplementedError

    def set_backpressure_multiplier(self, value=10):
        """Alter the backpressure multiplier value. We set this to 10 by default.
        This value is used to raise warnings and trigger the backpressure
        callback.

        :param int value: The multiplier value to set

        """
        self._backpressure = value

    #
    # Connections state properties
    #

    @property
    def is_closed(self):
        """
        Returns a boolean reporting the current connection state.
        """
        return self.connection_state == self.CONNECTION_CLOSED

    @property
    def is_closing(self):
        """
        Returns a boolean reporting the current connection state.
        """
        return self.connection_state == self.CONNECTION_CLOSING

    @property
    def is_open(self):
        """
        Returns a boolean reporting the current connection state.
        """
        return self.connection_state == self.CONNECTION_OPEN

    #
    # Properties that reflect server capabilities for the current connection
    #

    @property
    def basic_nack(self):
        """Specifies if the server supports basic.nack on the active connection.

        :rtype: bool

        """
        return self.server_capabilities.get('basic.nack', False)

    @property
    def consumer_cancel_notify(self):
        """Specifies if the server supports consumer cancel notification on the
        active connection.

        :rtype: bool

        """
        return self.server_capabilities.get('consumer_cancel_notify', False)

    @property
    def exchange_exchange_bindings(self):
        """Specifies if the active connection supports exchange to exchange
        bindings.

        :rtype: bool

        """
        return self.server_capabilities.get('exchange_exchange_bindings',
                                            False)

    @property
    def publisher_confirms(self):
        """Specifies if the active connection can use publisher confirmations.

        :rtype: bool

        """
        return self.server_capabilities.get('publisher_confirms', False)

    #
    # Internal methods for managing the communication process
    #

    def _adapter_connect(self):
        """Subclasses should override to set up the outbound socket connection.

        :raises: NotImplementedError

        """
        raise NotImplementedError

    def _adapter_disconnect(self):
        """Subclasses should override this to cause the underlying transport
        (socket) to close.

        :raises: NotImplementedError

        """
        raise NotImplementedError

    def _add_channel_callbacks(self, channel_number):
        """Add the appropriate callbacks for the specified channel number.

        :param int channel_number: The channel number for the callbacks

        """
        self.callbacks.add(channel_number,
                           spec.Channel.CloseOk,
                           self._on_channel_closeok)

    def _add_connection_start_callback(self):
        """Add a callback for when a Connection.Start frame is received from
        the broker.

        """
        self.callbacks.add(0, spec.Connection.Start, self._on_connection_start)

    def _add_connection_tune_callback(self):
        """Add a callback for when a Connection.Tune frame is received."""
        self.callbacks.add(0, spec.Connection.Tune, self._on_connection_tune)

    def _append_frame_buffer(self, value):
        """Append the bytes to the frame buffer.

        :param str value: The bytes to append to the frame buffer

        """
        self._frame_buffer += value

    @property
    def _buffer_size(self):
        """Return the suggested buffer size from the connection state/tune or
        the default if that is None.

        :rtype: int

        """
        return self.params.frame_max or spec.FRAME_MAX_SIZE

    def _check_for_protocol_mismatch(self, value):
        """Invoked when starting a connection to make sure it's a supported
        protocol.

        :param pika.frame.Method value: The frame to check
        :raises: ProtocolVersionMismatch

        """
        if (value.method.version_major,
            value.method.version_minor) != spec.PROTOCOL_VERSION[0:2]:
            raise exceptions.ProtocolVersionMismatch(frame.ProtocolHeader(),
                                                     value)

    @property
    def _client_properties(self):
        """Return the client properties dictionary.

        :rtype: dict

        """
        return {'product': PRODUCT,
                'platform': 'Python %s' % platform.python_version(),
                'capabilities': {'authentication_failure_close': True,
                                 'basic.nack': True,
                                 'connection.blocked': True,
                                 'consumer_cancel_notify': True,
                                 'publisher_confirms': True},
                'information': 'See http://pika.rtfd.org',
                'version': __version__}

    def _close_channels(self, reply_code, reply_text):
        """Close the open channels with the specified reply_code and reply_text.

        :param int reply_code: The code for why the channels are being closed
        :param str reply_text: The text reason for why the channels are closing

        """
        if self.is_open:
            for channel_number in self._channels.keys():
                if self._channels[channel_number].is_open:
                    self._channels[channel_number].close(reply_code, reply_text)
                else:
                    del self._channels[channel_number]
                    # Force any lingering callbacks to be removed
                    # moved inside else block since _on_channel_closeok removes
                    # callbacks
                    self.callbacks.cleanup(channel_number)
        else:
            self._channels = dict()

    def _combine(self, a, b):
        """Pass in two values, if a is 0, return b otherwise if b is 0,
        return a. If neither case matches return the smallest value.

        :param int a: The first value
        :param int b: The second value
        :rtype: int

        """
        return min(a, b) or (a or b)

    def _connect(self):
        """Attempt to connect to RabbitMQ

        :rtype: bool

        """
        warnings.warn('This method is deprecated, use Connection.connect',
                      DeprecationWarning)

    def _create_channel(self, channel_number, on_open_callback):
        """Create a new channel using the specified channel number and calling
        back the method specified by on_open_callback

        :param int channel_number: The channel number to use
        :param method on_open_callback: The callback when the channel is opened

        """
        return channel.Channel(self, channel_number, on_open_callback)

    def _create_heartbeat_checker(self):
        """Create a heartbeat checker instance if there is a heartbeat interval
        set.

        :rtype: pika.heartbeat.Heartbeat

        """
        if self.params.heartbeat is not None and self.params.heartbeat > 0:
            LOGGER.debug('Creating a HeartbeatChecker: %r',
                         self.params.heartbeat)
            return heartbeat.HeartbeatChecker(self, self.params.heartbeat)

    def _deliver_frame_to_channel(self, value):
        """Deliver the frame to the channel specified in the frame.

        :param pika.frame.Method value: The frame to deliver

        """
        if not value.channel_number in self._channels:
            if self._is_basic_deliver_frame(value):
                self._reject_out_of_band_delivery(value.channel_number,
                                                  value.method.delivery_tag)
            else:
                LOGGER.warning("Received %r for non-existing channel %i",
                               value, value.channel_number)
            return
        return self._channels[value.channel_number]._handle_content_frame(value)

    def _detect_backpressure(self):
        """Attempt to calculate if TCP backpressure is being applied due to
        our outbound buffer being larger than the average frame size over
        a window of frames.

        """
        avg_frame_size = self.bytes_sent / self.frames_sent
        buffer_size = sum([len(frame) for frame in self.outbound_buffer])
        if buffer_size > (avg_frame_size * self._backpressure):
            LOGGER.warning(BACKPRESSURE_WARNING, buffer_size,
                           int(buffer_size / avg_frame_size))
            self.callbacks.process(0, self.ON_CONNECTION_BACKPRESSURE, self)

    def _ensure_closed(self):
        """If the connection is not closed, close it."""
        if self.is_open:
            self.close()

    def _flush_outbound(self):
        """Adapters should override to flush the contents of outbound_buffer
        out along the socket.

        :raises: NotImplementedError

        """
        raise NotImplementedError

    def _get_body_frame_max_length(self):
        """Calculate the maximum amount of bytes that can be in a body frame.

        :rtype: int

        """
        return (self.params.frame_max -
                spec.FRAME_HEADER_SIZE -
                spec.FRAME_END_SIZE)

    def _get_credentials(self, method_frame):
        """Get credentials for authentication.

        :param pika.frame.MethodFrame method_frame: The Connection.Start frame
        :rtype: tuple(str, str)

        """
        (auth_type,
         response) = self.params.credentials.response_for(method_frame.method)
        if not auth_type:
            raise exceptions.AuthenticationError(self.params.credentials.TYPE)
        self.params.credentials.erase_credentials()
        return auth_type, response

    @property
    def _has_open_channels(self):
        """Returns true if channels are open.

        :rtype: bool

        """
        return any([self._channels[num].is_open for num in
                    self._channels.keys()])

    def _has_pending_callbacks(self, value):
        """Return true if there are any callbacks pending for the specified
        frame.

        :param pika.frame.Method value: The frame to check
        :rtype: bool

        """
        return self.callbacks.pending(value.channel_number, value.method)

    def _init_connection_state(self):
        """Initialize or reset all of the internal state variables for a given
        connection. On disconnect or reconnect all of the state needs to
        be wiped.

        """
        # Connection state
        self._set_connection_state(self.CONNECTION_CLOSED)

        # Negotiated server properties
        self.server_properties = None

        # Outbound buffer for buffering writes until we're able to send them
        self.outbound_buffer = collections.deque([])

        # Inbound buffer for decoding frames
        self._frame_buffer = bytes()

        # Dict of open channels
        self._channels = dict()

        # Remaining connection attempts
        self.remaining_connection_attempts = self.params.connection_attempts

        # Data used for Heartbeat checking and back-pressure detection
        self.bytes_sent = 0
        self.bytes_received = 0
        self.frames_sent = 0
        self.frames_received = 0
        self.heartbeat = None

        # Default back-pressure multiplier value
        self._backpressure = 10

        # When closing, hold reason why
        self.closing = 0, 'Not specified'

        # Our starting point once connected, first frame received
        self._add_connection_start_callback()

    def _is_basic_deliver_frame(self, frame_value):
        """Returns true if the frame is a Basic.Deliver

        :param pika.frame.Method frame_value: The frame to check
        :rtype: bool

        """
        return isinstance(frame_value, spec.Basic.Deliver)

    def _is_connection_close_frame(self, value):
        """Returns true if the frame is a Connection.Close frame.

        :param pika.frame.Method value: The frame to check
        :rtype: bool

        """
        if not value:
            return False
        return isinstance(value.method, spec.Connection.Close)

    def _is_method_frame(self, value):
        """Returns true if the frame is a method frame.

        :param pika.frame.Frame value: The frame to evaluate
        :rtype: bool

        """
        return isinstance(value, frame.Method)

    def _is_protocol_header_frame(self, value):
        """Returns True if it's a protocol header frame.

        :rtype: bool

        """
        return  isinstance(value, frame.ProtocolHeader)

    def _next_channel_number(self):
        """Return the next available channel number or raise on exception.

        :rtype: int

        """
        limit = self.params.channel_max or channel.MAX_CHANNELS
        if len(self._channels) == limit:
            raise exceptions.NoFreeChannels()
        return [x + 1 for x in sorted(self._channels.keys() or [0])
                if x + 1 not in self._channels.keys()][0]

    def _on_channel_closeok(self, method_frame):
        """Remove the channel from the dict of channels when Channel.CloseOk is
        sent.

        :param pika.frame.Method method_frame: The response

        """
        try:
            del self._channels[method_frame.channel_number]
        except KeyError:
            LOGGER.error('Channel %r not in channels',
                         method_frame.channel_number)
        if self.is_closing and not self._has_open_channels:
            self._on_close_ready()

    def _on_close_ready(self):
        """Called when the Connection is in a state that it can close after
        a close has been requested. This happens, for example, when all of the
        channels are closed that were open when the close request was made.

        """
        if self.is_closed:
            LOGGER.warning('Invoked while already closed')
            return
        self._send_connection_close(self.closing[0], self.closing[1])

    def _on_connected(self):
        """Invoked when the socket is connected and it's time to start speaking
        AMQP with the broker.

        """
        self._set_connection_state(self.CONNECTION_PROTOCOL)

        # Start the communication with the RabbitMQ Broker
        self._send_frame(frame.ProtocolHeader())

    def _on_connection_closed(self, method_frame, from_adapter=False):
        """Called when the connection is closed remotely. The from_adapter value
        will be true if the connection adapter has been disconnected from
        the broker and the method was invoked directly instead of by receiving
        a Connection.Close frame.

        :param pika.frame.Method: The Connection.Close frame
        :param bool from_adapter: Called by the connection adapter

        """
        if method_frame and self._is_connection_close_frame(method_frame):
            self.closing = (method_frame.method.reply_code,
                            method_frame.method.reply_text)

        # Stop the heartbeat checker if it exists
        if self.heartbeat:
            self.heartbeat.stop()

        # If this did not come from the connection adapter, close the socket
        if not from_adapter:
            self._adapter_disconnect()

        # Invoke a method frame neutral close
        self._on_disconnect(self.closing[0], self.closing[1])

    def _on_connection_error(self, connection_unused, error_message=None):
        """Default behavior when the connecting connection can not connect.

        :raises: exceptions.AMQPConnectionError

        """
        raise exceptions.AMQPConnectionError(error_message or
                                             self.params.connection_attempts)

    def _on_connection_open(self, method_frame):
        """
        This is called once we have tuned the connection with the server and
        called the Connection.Open on the server and it has replied with
        Connection.Ok.
        """
        self.known_hosts = method_frame.method.known_hosts

        # Add a callback handler for the Broker telling us to disconnect
        self.callbacks.add(0, spec.Connection.Close, self._on_connection_closed)

        # We're now connected at the AMQP level
        self._set_connection_state(self.CONNECTION_OPEN)

        # Call our initial callback that we're open
        self.callbacks.process(0, self.ON_CONNECTION_OPEN, self, self)

    def _on_connection_start(self, method_frame):
        """This is called as a callback once we have received a Connection.Start
        from the server.

        :param pika.frame.Method method_frame: The frame received
        :raises: UnexpectedFrameError

        """
        self._set_connection_state(self.CONNECTION_START)
        if self._is_protocol_header_frame(method_frame):
            raise exceptions.UnexpectedFrameError
        self._check_for_protocol_mismatch(method_frame)
        self._set_server_information(method_frame)
        self._add_connection_tune_callback()
        self._send_connection_start_ok(*self._get_credentials(method_frame))

    def _on_connection_tune(self, method_frame):
        """Once the Broker sends back a Connection.Tune, we will set our tuning
        variables that have been returned to us and kick off the Heartbeat
        monitor if required, send our TuneOk and then the Connection. Open rpc
        call on channel 0.

        :param pika.frame.Method method_frame: The frame received

        """
        self._set_connection_state(self.CONNECTION_TUNE)

        # Get our max channels, frames and heartbeat interval
        self.params.channel_max = self._combine(self.params.channel_max,
                                                method_frame.method.channel_max)
        self.params.frame_max = self._combine(self.params.frame_max,
                                              method_frame.method.frame_max)
        self.params.heartbeat = self._combine(self.params.heartbeat,
                                              method_frame.method.heartbeat)

        # Calculate the maximum pieces for body frames
        self._body_max_length = self._get_body_frame_max_length()

        # Create a new heartbeat checker if needed
        self.heartbeat = self._create_heartbeat_checker()

        # Send the TuneOk response with what we've agreed upon
        self._send_connection_tune_ok()

        # Send the Connection.Open RPC call for the vhost
        self._send_connection_open()

    def _on_data_available(self, data_in):
        """This is called by our Adapter, passing in the data from the socket.
        As long as we have buffer try and map out frame data.

        :param str data_in: The data that is available to read

        """
        self._append_frame_buffer(data_in)
        while self._frame_buffer:
            consumed_count, frame_value = self._read_frame()
            if not frame_value:
                return
            self._trim_frame_buffer(consumed_count)
            self._process_frame(frame_value)

    def _on_disconnect(self, reply_code, reply_text):
        """Invoke passing in the reply_code and reply_text from internal
        methods to the adapter. Called from on_connection_closed and Heartbeat
        timeouts.

        :param str reply_code: The numeric close code
        :param str reply_text: The text close reason

        """
        LOGGER.warning('Disconnected from RabbitMQ at %s:%i (%s): %s',
                       self.params.host, self.params.port,
                       reply_code, reply_text)
        self._set_connection_state(self.CONNECTION_CLOSED)
        for channel in self._channels.keys():
            if channel not in self._channels:
                continue
            method_frame = frame.Method(channel, spec.Channel.Close(reply_code,
                                                                    reply_text))
            self._channels[channel]._on_close(method_frame)
        self._process_connection_closed_callbacks(reply_code, reply_text)
        self._remove_connection_callbacks()

    def _process_callbacks(self, frame_value):
        """Process the callbacks for the frame if the frame is a method frame
        and if it has any callbacks pending.

        :param pika.frame.Method frame_value: The frame to process
        :rtype: bool

        """
        if (self._is_method_frame(frame_value) and
            self._has_pending_callbacks(frame_value)):
            self.callbacks.process(frame_value.channel_number,  # Prefix
                                   frame_value.method,          # Key
                                   self,                        # Caller
                                   frame_value)                 # Args
            return True
        return False

    def _process_connection_closed_callbacks(self, reason_code, reason_text):
        """Process any callbacks that should be called when the connection is
        closed.

        :param str reason_code: The numeric code from RabbitMQ for the close
        :param str reason_text: The text reason fro closing

        """
        self.callbacks.process(0, self.ON_CONNECTION_CLOSED, self, self,
                               reason_code, reason_text)

    def _process_frame(self, frame_value):
        """Process an inbound frame from the socket.

        :param frame_value: The frame to process
        :type frame_value: pika.frame.Frame | pika.frame.Method

        """
        # Will receive a frame type of -1 if protocol version mismatch
        if frame_value.frame_type < 0:
            return

        # Keep track of how many frames have been read
        self.frames_received += 1

        # Process any callbacks, if True, exit method
        if self._process_callbacks(frame_value):
            return

        # If a heartbeat is received, update the checker
        if isinstance(frame_value, frame.Heartbeat):
            if self.heartbeat:
                self.heartbeat.received()
            else:
                LOGGER.warning('Received heartbeat frame without a heartbeat '
                               'checker')

        # If the frame has a channel number beyond the base channel, deliver it
        elif frame_value.channel_number > 0:
            self._deliver_frame_to_channel(frame_value)

    def _read_frame(self):
        """Try and read from the frame buffer and decode a frame.

        :rtype tuple: (int, pika.frame.Frame)

        """
        return frame.decode_frame(self._frame_buffer)

    def _reject_out_of_band_delivery(self, channel_number, delivery_tag):
        """Reject a delivery on the specified channel number and delivery tag
        because said channel no longer exists.

        :param int channel_number: The channel number
        :param int delivery_tag: The delivery tag

        """
        LOGGER.warning('Rejected out-of-band delivery on channel %i (%s)',
                       channel_number, delivery_tag)
        self._send_method(channel_number, spec.Basic.Reject(delivery_tag))

    def _remove_callback(self, channel_number, method_frame):
        """Remove the specified method_frame callback if it is set for the
        specified channel number.

        :param int channel_number: The channel number to remove the callback on
        :param pika.object.Method: The method frame for the callback

        """
        self.callbacks.remove(str(channel_number), method_frame)

    def _remove_callbacks(self, channel_number, method_frames):
        """Remove the callbacks for the specified channel number and list of
        method frames.

        :param int channel_number: The channel number to remove the callback on
        :param list method_frames: The method frames for the callback

        """
        for method_frame in method_frames:
            self._remove_callback(channel_number, method_frame)

    def _remove_connection_callbacks(self):
        """Remove all callbacks for the connection"""
        self._remove_callbacks(0, [spec.Connection.Close,
                                   spec.Connection.Start,
                                   spec.Connection.Open])

    def _rpc(self, channel_number, method_frame,
             callback_method=None, acceptable_replies=None):
        """Make an RPC call for the given callback, channel number and method.
        acceptable_replies lists out what responses we'll process from the
        server with the specified callback.

        :param int channel_number: The channel number for the RPC call
        :param pika.object.Method method_frame: The method frame to call
        :param method callback_method: The callback for the RPC response
        :param list acceptable_replies: The replies this RPC call expects

        """
        # Validate that acceptable_replies is a list or None
        if acceptable_replies and not isinstance(acceptable_replies, list):
            raise TypeError('acceptable_replies should be list or None')

        # Validate the callback is callable
        if callback_method:
            if not utils.is_callable(callback_method):
                raise TypeError('callback should be None, function or method.')

            for reply in acceptable_replies:
                self.callbacks.add(channel_number, reply, callback_method)

        # Send the rpc call to RabbitMQ
        self._send_method(channel_number, method_frame)

    def _send_connection_close(self, reply_code, reply_text):
        """Send a Connection.Close method frame.

        :param int reply_code: The reason for the close
        :param str reply_text: The text reason for the close

        """
        self._rpc(0, spec.Connection.Close(reply_code, reply_text, 0, 0),
                  self._on_connection_closed, [spec.Connection.CloseOk])

    def _send_connection_open(self):
        """Send a Connection.Open frame"""
        self._rpc(0, spec.Connection.Open(self.params.virtual_host,
                                          insist=True),
                  self._on_connection_open, [spec.Connection.OpenOk])

    def _send_connection_start_ok(self, authentication_type, response):
        """Send a Connection.StartOk frame

        :param str authentication_type: The auth type value
        :param str response: The encoded value to send

        """
        self._send_method(0, spec.Connection.StartOk(self._client_properties,
                                                     authentication_type,
                                                     response,
                                                     self.params.locale))

    def _send_connection_tune_ok(self):
        """Send a Connection.TuneOk frame"""
        self._send_method(0, spec.Connection.TuneOk(self.params.channel_max,
                                                    self.params.frame_max,
                                                    self.params.heartbeat))

    def _send_frame(self, frame_value):
        """This appends the fully generated frame to send to the broker to the
        output buffer which will be then sent via the connection adapter.

        :param frame_value: The frame to write
        :type frame_value:  pika.frame.Frame|pika.frame.ProtocolHeader

        """
        if self.is_closed:
            LOGGER.critical('Attempted to send frame when closed')
            return
        marshaled_frame = frame_value.marshal()
        self.bytes_sent += len(marshaled_frame)
        self.frames_sent += 1
        self.outbound_buffer.append(marshaled_frame)
        self._flush_outbound()
        if self.params.backpressure_detection:
            self._detect_backpressure()

    def _send_method(self, channel_number, method_frame, content=None):
        """Constructs a RPC method frame and then sends it to the broker.

        :param int channel_number: The channel number for the frame
        :param pika.object.Method method_frame: The method frame to send
        :param tuple content: If set, is a content frame, is tuple of
                              properties and body.

        """
        self._send_frame(frame.Method(channel_number, method_frame))

        # If it's not a tuple of Header, str|unicode then return
        if not isinstance(content, tuple):
            return

        length = len(content[1])
        self._send_frame(frame.Header(channel_number, length, content[0]))
        if content[1]:
            chunks = int(math.ceil(float(length) / self._body_max_length))
            for chunk in range(0, chunks):
                start = chunk * self._body_max_length
                end = start + self._body_max_length
                if end > length:
                    end = length
                self._send_frame(frame.Body(channel_number,
                                            content[1][start:end]))

    def _set_connection_state(self, connection_state):
        """Set the connection state.

        :param int connection_state: The connection state to set

        """
        self.connection_state = connection_state

    def _set_server_information(self, method_frame):
        """Set the server properties and capabilities

        :param spec.connection.Start method_frame: The Connection.Start frame

        """
        self.server_properties = method_frame.method.server_properties
        self.server_capabilities = self.server_properties.get('capabilities',
                                                              dict())
        if hasattr(self.server_properties, 'capabilities'):
            del self.server_properties['capabilities']

    def _trim_frame_buffer(self, byte_count):
        """Trim the leading N bytes off the frame buffer and increment the
        counter that keeps track of how many bytes have been read/used from the
        socket.

        :param int byte_count: The number of bytes consumed

        """
        self._frame_buffer = self._frame_buffer[byte_count:]
        self.bytes_received += byte_count

########NEW FILE########
__FILENAME__ = credentials
"""The credentials classes are used to encapsulate all authentication
information for the :class:`~pika.connection.ConnectionParameters` class.

The :class:`~pika.credentials.PlainCredentials` class returns the properly
formatted username and password to the :class:`~pika.connection.Connection`.

To authenticate with Pika, create a :class:`~pika.credentials.PlainCredentials`
object passing in the username and password and pass it as the credentials
argument value to the :class:`~pika.connection.ConnectionParameters` object.

If you are using :class:`~pika.connection.URLParameters` you do not need a
credentials object, one will automatically be created for you.

If you are looking to implement SSL certificate style authentication, you would
extend the :class:`~pika.credentials.ExternalCredentials` class implementing
the required behavior.

"""
import logging

LOGGER = logging.getLogger(__name__)


class PlainCredentials(object):
    """A credentials object for the default authentication methodology with
    RabbitMQ.

    If you do not pass in credentials to the ConnectionParameters object, it
    will create credentials for 'guest' with the password of 'guest'.

    If you pass True to erase_on_connect the credentials will not be stored
    in memory after the Connection attempt has been made.

    :param str username: The username to authenticate with
    :param str password: The password to authenticate with
    :param bool erase_on_connect: erase credentials on connect.

    """
    TYPE = 'PLAIN'

    def __init__(self, username, password, erase_on_connect=False):
        """Create a new instance of PlainCredentials

        :param str username: The username to authenticate with
        :param str password: The password to authenticate with
        :param bool erase_on_connect: erase credentials on connect.

        """
        self.username = username
        self.password = password
        self.erase_on_connect = erase_on_connect

    def response_for(self, start):
        """Validate that this type of authentication is supported

        :param spec.Connection.Start start: Connection.Start method
        :rtype: tuple(str|None, str|None)

        """
        if PlainCredentials.TYPE not in start.mechanisms.split():
            return None, None
        return (PlainCredentials.TYPE,
                '\0%s\0%s' % (self.username, self.password))

    def erase_credentials(self):
        """Called by Connection when it no longer needs the credentials"""
        if self.erase_on_connect:
            LOGGER.info("Erasing stored credential values")
            self.username = None
            self.password = None


class ExternalCredentials(object):
    """The ExternalCredentials class allows the connection to use EXTERNAL
    authentication, generally with a client SSL certificate.

    """
    TYPE = 'EXTERNAL'

    def __init__(self):
        """Create a new instance of ExternalCredentials"""
        self.erase_on_connect = False

    def response_for(self, start):
        """Validate that this type of authentication is supported

        :param spec.Connection.Start start: Connection.Start method
        :rtype: tuple(str or None, str or None)

        """
        if ExternalCredentials.TYPE not in start.mechanisms.split():
            return None, None
        return ExternalCredentials.TYPE, ''

    def erase_credentials(self):
        """Called by Connection when it no longer needs the credentials"""
        LOGGER.debug('Not supported by this Credentials type')


# Append custom credential types to this list for validation support
VALID_TYPES = [PlainCredentials, ExternalCredentials]

########NEW FILE########
__FILENAME__ = data
"""AMQP Table Encoding/Decoding"""
import struct
import decimal
import calendar
from datetime import datetime

from pika import exceptions


def encode_table(pieces, table):
    """Encode a dict as an AMQP table appending the encded table to the
    pieces list passed in.

    :param list pieces: Already encoded frame pieces
    :param dict table: The dict to encode
    :rtype: int

    """
    table = table or dict()
    length_index = len(pieces)
    pieces.append(None)  # placeholder
    tablesize = 0
    for (key, value) in table.items():
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        pieces.append(struct.pack('B', len(key)))
        pieces.append(key)
        tablesize = tablesize + 1 + len(key)
        tablesize += encode_value(pieces, value)

    pieces[length_index] = struct.pack('>I', tablesize)
    return tablesize + 4


def encode_value(pieces, value):
    """Encode the value passed in and append it to the pieces list returning
    the the size of the encoded value.

    :param list pieces: Already encoded values
    :param any value: The value to encode
    :rtype: int

    """
    if isinstance(value, basestring):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        pieces.append(struct.pack('>cI', 'S', len(value)))
        pieces.append(value)
        return 5 + len(value)
    elif isinstance(value, bool):
        pieces.append(struct.pack('>cB', 't', int(value)))
        return 2
    elif isinstance(value, int):
        pieces.append(struct.pack('>ci', 'I', value))
        return 5
    elif isinstance(value, long):
        pieces.append(struct.pack('>cq', 'l', value))
        return 9
    elif isinstance(value, decimal.Decimal):
        value = value.normalize()
        if value._exp < 0:
            decimals = -value._exp
            raw = int(value * (decimal.Decimal(10) ** decimals))
            pieces.append(struct.pack('>cBi', 'D', decimals, raw))
        else:
            # per spec, the "decimals" octet is unsigned (!)
            pieces.append(struct.pack('>cBi', 'D', 0, int(value)))
        return 6
    elif isinstance(value, datetime):
        pieces.append(struct.pack('>cQ', 'T',
                                  calendar.timegm(value.utctimetuple())))
        return 9
    elif isinstance(value, dict):
        pieces.append(struct.pack('>c', 'F'))
        return 1 + encode_table(pieces, value)
    elif isinstance(value, list):
        p = []
        for v in value:
            encode_value(p, v)
        piece = ''.join(p)
        pieces.append(struct.pack('>cI', 'A', len(piece)))
        pieces.append(piece)
        return 5 + len(piece)
    elif value is None:
        pieces.append(struct.pack('>c', 'V'))
        return 1
    else:
        raise exceptions.UnsupportedAMQPFieldException(pieces, value)


def decode_table(encoded, offset):
    """Decode the AMQP table passed in from the encoded value returning the
    decoded result and the number of bytes read plus the offset.

    :param str encoded: The binary encoded data to decode
    :param int offset: The starting byte offset
    :rtype: tuple

    """
    result = {}
    tablesize = struct.unpack_from('>I', encoded, offset)[0]
    offset += 4
    limit = offset + tablesize
    while offset < limit:
        keylen = struct.unpack_from('B', encoded, offset)[0]
        offset += 1
        key = encoded[offset: offset + keylen]
        offset += keylen
        value, offset = decode_value(encoded, offset)
        result[key] = value
    return result, offset


def decode_value(encoded, offset):
    """Decode the value passed in returning the decoded value and the number
    of bytes read in addition to the starting offset.

    :param str encoded: The binary encoded data to decode
    :param int offset: The starting byte offset
    :rtype: tuple
    :raises: pika.exceptions.InvalidFieldTypeException

    """
    kind = encoded[offset]
    offset += 1

    # Bool
    if kind == 't':
        value = struct.unpack_from('>B', encoded, offset)[0]
        value = bool(value)
        offset += 1

    # Short-Short Int
    elif kind == 'b':
        value = struct.unpack_from('>B', encoded, offset)[0]
        offset += 1

    # Short-Short Unsigned Int
    elif kind == 'B':
        value = struct.unpack_from('>b', encoded, offset)[0]
        offset += 1

    # Short Int
    elif kind == 'U':
        value = struct.unpack_from('>h', encoded, offset)[0]
        offset += 2

    # Short Unsigned Int
    elif kind == 'u':
        value = struct.unpack_from('>H', encoded, offset)[0]
        offset += 2

    # Long Int
    elif kind == 'I':
        value = struct.unpack_from('>i', encoded, offset)[0]
        offset += 4

    # Long Unsigned Int
    elif kind == 'i':
        value = struct.unpack_from('>I', encoded, offset)[0]
        offset += 4

    # Long-Long Int
    elif kind == 'L':
        value = long(struct.unpack_from('>q', encoded, offset)[0])
        offset += 8

    # Long-Long Unsigned Int
    elif kind == 'l':
        value = long(struct.unpack_from('>Q', encoded, offset)[0])
        offset += 8

    # Float
    elif kind == 'f':
        value = long(struct.unpack_from('>f', encoded, offset)[0])
        offset += 4

    # Double
    elif kind == 'd':
        value = long(struct.unpack_from('>d', encoded, offset)[0])
        offset += 8

    # Decimal
    elif kind == 'D':
        decimals = struct.unpack_from('B', encoded, offset)[0]
        offset += 1
        raw = struct.unpack_from('>i', encoded, offset)[0]
        offset += 4
        value = decimal.Decimal(raw) * (decimal.Decimal(10) ** -decimals)

    # Short String
    elif kind == 's':
        length = struct.unpack_from('B', encoded, offset)[0]
        offset += 1
        value = encoded[offset: offset + length].decode('utf8')
        offset += length

    # Long String
    elif kind == 'S':
        length = struct.unpack_from('>I', encoded, offset)[0]
        offset += 4
        value = encoded[offset: offset + length].decode('utf8')
        offset += length

    # Field Array
    elif kind == 'A':
        length = struct.unpack_from('>I', encoded, offset)[0]
        offset += 4
        offset_end = offset + length
        value = []
        while offset < offset_end:
            v, offset = decode_value(encoded, offset)
            value.append(v)

    # Timestamp
    elif kind == 'T':
        value = datetime.utcfromtimestamp(struct.unpack_from('>Q', encoded,
                                                             offset)[0])
        offset += 8

    # Field Table
    elif kind == 'F':
        (value, offset) = decode_table(encoded, offset)

    # Null / Void
    elif kind == 'V':
        value = None
    else:
        raise exceptions.InvalidFieldTypeException(kind)

    return value, offset

########NEW FILE########
__FILENAME__ = exceptions
"""Pika specific exceptions"""


class AMQPError(Exception):
    def __repr__(self):
        return 'An unspecified AMQP error has occurred'


class AMQPConnectionError(AMQPError):
    def __repr__(self):
        if len(self.args) == 1:
            if self.args[0] == 1:
                return ('No connection could be opened after 1 '
                        'connection attempt')
            elif isinstance(self.args[0], int):
                return ('No connection could be opened after %s '
                        'connection attempts' %
                        self.args[0])
            else:
                return ('No connection could be opened: %s' %
                        self.args[0])
        elif len(self.args) == 2:
            return '%s: %s' % (self.args[0], self.args[1])


class IncompatibleProtocolError(AMQPConnectionError):
    def __repr__(self):
        return 'The protocol returned by the server is not supported'


class AuthenticationError(AMQPConnectionError):
    def __repr__(self):
        return ('Server and client could not negotiate use of the %s '
                'authentication mechanism' % self.args[0])


class ProbableAuthenticationError(AMQPConnectionError):
    def __repr__(self):
        return ('Client was disconnected at a connection stage indicating a '
                'probable authentication error')


class ProbableAccessDeniedError(AMQPConnectionError):
    def __repr__(self):
        return ('Client was disconnected at a connection stage indicating a '
                'probable denial of access to the specified virtual host')


class NoFreeChannels(AMQPConnectionError):
    def __repr__(self):
        return 'The connection has run out of free channels'


class ConnectionClosed(AMQPConnectionError):
    def __repr__(self):
        if len(self.args) == 2:
            return 'The AMQP connection was closed (%s) %s' % (self.args[0],
                                                               self.args[1])
        else:
            return 'The AMQP connection was closed'


class AMQPChannelError(AMQPError):
    def __repr__(self):
        return 'An unspecified AMQP channel error has occurred'


class ChannelClosed(AMQPChannelError):
    def __repr__(self):
        if len(self.args) == 2:
            return 'The channel was remotely closed (%s) %s' % (self.args[0],
                                                                self.args[1])
        else:
            return 'The channel was remotely closed'


class DuplicateConsumerTag(AMQPChannelError):
    def __repr__(self):
        return ('The consumer tag specified already exists for this '
                'channel: %s' % self.args[0])


class ConsumerCancelled(AMQPChannelError):
    def __repr__(self):
        return 'Server cancelled consumer'


class InvalidChannelNumber(AMQPError):
    def __repr__(self):
        return 'An invalid channel number has been specified: %s' % self.args[0]


class ProtocolSyntaxError(AMQPError):
    def __repr__(self):
        return 'An unspecified protocol syntax error occurred'


class UnexpectedFrameError(ProtocolSyntaxError):
    def __repr__(self):
        return 'Received a frame out of sequence: %r' % self.args[0]


class ProtocolVersionMismatch(ProtocolSyntaxError):
    def __repr__(self):
        return 'Protocol versions did not match: %r vs %r' % (self.args[0],
                                                              self.args[1])


class BodyTooLongError(ProtocolSyntaxError):
    def __repr__(self):
        return ('Received too many bytes for a message delivery: '
                'Received %i, expected %i' % (self.args[0], self.args[1]))


class InvalidFrameError(ProtocolSyntaxError):
    def __repr__(self):
        return 'Invalid frame received: %r' % self.args[0]


class InvalidFieldTypeException(ProtocolSyntaxError):
    def __repr__(self):
        return 'Unsupported field kind %s' % self.args[0]


class UnsupportedAMQPFieldException(ProtocolSyntaxError):
    def __repr__(self):
        return 'Unsupported field kind %s' % type(self.args[1])


class UnspportedAMQPFieldException(UnsupportedAMQPFieldException):
    """Deprecated version of UnsupportedAMQPFieldException"""


class MethodNotImplemented(AMQPError):
    pass


class ChannelError(Exception):
    def __repr__(self):
        return 'An unspecified error occurred with the Channel'


class InvalidMinimumFrameSize(ProtocolSyntaxError):
    def __repr__(self):
        return 'AMQP Minimum Frame Size is 4096 Bytes'


class InvalidMaximumFrameSize(ProtocolSyntaxError):
    def __repr__(self):
        return 'AMQP Maximum Frame Size is 131072 Bytes'

########NEW FILE########
__FILENAME__ = frame
"""Frame objects that do the frame demarshaling and marshaling."""
import logging
import struct

from pika import amqp_object
from pika import exceptions
from pika import spec

LOGGER = logging.getLogger(__name__)


class Frame(amqp_object.AMQPObject):
    """Base Frame object mapping. Defines a behavior for all child classes for
    assignment of core attributes and implementation of the a core _marshal
    method which child classes use to create the binary AMQP frame.

    """
    NAME = 'Frame'

    def __init__(self, frame_type, channel_number):
        """Create a new instance of a frame

        :param int frame_type: The frame type
        :param int channel_number: The channel number for the frame

        """
        self.frame_type = frame_type
        self.channel_number = channel_number

    def _marshal(self, pieces):
        """Create the full AMQP wire protocol frame data representation

        :rtype: str

        """
        payload = ''.join(pieces)
        return struct.pack('>BHI',
                           self.frame_type,
                           self.channel_number,
                           len(payload)) + payload + chr(spec.FRAME_END)

    def marshal(self):
        """To be ended by child classes

        :raises NotImplementedError

        """
        raise NotImplementedError


class Method(Frame):
    """Base Method frame object mapping. AMQP method frames are mapped on top
    of this class for creating or accessing their data and attributes.

    """
    NAME = 'METHOD'

    def __init__(self, channel_number, method):
        """Create a new instance of a frame

        :param int channel_number: The frame type
        :param pika.Spec.Class.Method method: The AMQP Class.Method

        """
        Frame.__init__(self, spec.FRAME_METHOD, channel_number)
        self.method = method

    def marshal(self):
        """Return the AMQP binary encoded value of the frame

        :rtype: str

        """
        pieces = self.method.encode()
        pieces.insert(0, struct.pack('>I', self.method.INDEX))
        return self._marshal(pieces)


class Header(Frame):
    """Header frame object mapping. AMQP content header frames are mapped
    on top of this class for creating or accessing their data and attributes.

    """
    NAME = 'Header'

    def __init__(self, channel_number, body_size, props):
        """Create a new instance of a AMQP ContentHeader object

        :param int channel_number: The channel number for the frame
        :param int body_size: The number of bytes for the body
        :param pika.spec.BasicProperties props: Basic.Properties object

        """
        Frame.__init__(self, spec.FRAME_HEADER, channel_number)
        self.body_size = body_size
        self.properties = props

    def marshal(self):
        """Return the AMQP binary encoded value of the frame

        :rtype: str

        """
        pieces = self.properties.encode()
        pieces.insert(0, struct.pack('>HxxQ',
                                     self.properties.INDEX,
                                     self.body_size))
        return self._marshal(pieces)


class Body(Frame):
    """Body frame object mapping class. AMQP content body frames are mapped on
    to this base class for getting/setting of attributes/data.

    """
    NAME = 'Body'

    def __init__(self, channel_number, fragment):
        """
        Parameters:

        - channel_number: int
        - fragment: unicode or str
        """
        Frame.__init__(self, spec.FRAME_BODY, channel_number)
        self.fragment = fragment

    def marshal(self):
        """Return the AMQP binary encoded value of the frame

        :rtype: str

        """
        return self._marshal([self.fragment])


class Heartbeat(Frame):
    """Heartbeat frame object mapping class. AMQP Heartbeat frames are mapped
    on to this class for a common access structure to the attributes/data
    values.

    """
    NAME = 'Heartbeat'

    def __init__(self):
        """Create a new instance of the Heartbeat frame"""
        Frame.__init__(self, spec.FRAME_HEARTBEAT, 0)

    def marshal(self):
        """Return the AMQP binary encoded value of the frame

        :rtype: str

        """
        return self._marshal(list())


class ProtocolHeader(amqp_object.AMQPObject):
    """AMQP Protocol header frame class which provides a pythonic interface
    for creating AMQP Protocol headers

    """
    NAME = 'ProtocolHeader'

    def __init__(self, major=None, minor=None, revision=None):
        """Construct a Protocol Header frame object for the specified AMQP
        version

        :param int major: Major version number
        :param int minor: Minor version number
        :param int revision: Revision

        """
        self.frame_type = -1
        self.major = major or spec.PROTOCOL_VERSION[0]
        self.minor = minor or spec.PROTOCOL_VERSION[1]
        self.revision = revision or spec.PROTOCOL_VERSION[2]

    def marshal(self):
        """Return the full AMQP wire protocol frame data representation of the
        ProtocolHeader frame

        :rtype: str

        """
        return 'AMQP' + struct.pack('BBBB', 0,
                                    self.major,
                                    self.minor,
                                    self.revision)


def decode_frame(data_in):
    """Receives raw socket data and attempts to turn it into a frame.
    Returns bytes used to make the frame and the frame

    :param str data_in: The raw data stream
    :rtype: tuple(bytes consumed, frame)
    :raises: pika.exceptions.InvalidFrameError

    """
    # Look to see if it's a protocol header frame
    try:
        if data_in[0:4] == 'AMQP':
            major, minor, revision = struct.unpack_from('BBB', data_in, 5)
            return 8, ProtocolHeader(major, minor, revision)
    except (IndexError, struct.error):
        return 0, None

    # Get the Frame Type, Channel Number and Frame Size
    try:
        (frame_type,
         channel_number,
         frame_size) = struct.unpack('>BHL', data_in[0:7])
    except struct.error:
        return 0, None

    # Get the frame data
    frame_end = spec.FRAME_HEADER_SIZE + frame_size + spec.FRAME_END_SIZE

    # We don't have all of the frame yet
    if frame_end > len(data_in):
        return 0, None

    # The Frame termination chr is wrong
    if data_in[frame_end - 1] != chr(spec.FRAME_END):
        raise exceptions.InvalidFrameError("Invalid FRAME_END marker")

    # Get the raw frame data
    frame_data = data_in[spec.FRAME_HEADER_SIZE:frame_end - 1]

    if frame_type == spec.FRAME_METHOD:

        # Get the Method ID from the frame data
        method_id = struct.unpack_from('>I', frame_data)[0]

        # Get a Method object for this method_id
        method = spec.methods[method_id]()

        # Decode the content
        method.decode(frame_data, 4)

        # Return the amount of data consumed and the Method object
        return frame_end, Method(channel_number, method)

    elif frame_type == spec.FRAME_HEADER:

        # Return the header class and body size
        class_id, weight, body_size = struct.unpack_from('>HHQ', frame_data)

        # Get the Properties type
        properties = spec.props[class_id]()

        # Decode the properties
        out = properties.decode(frame_data[12:])

        # Return a Header frame
        return frame_end, Header(channel_number, body_size, properties)

    elif frame_type == spec.FRAME_BODY:

        # Return the amount of data consumed and the Body frame w/ data
        return frame_end, Body(channel_number, frame_data)

    elif frame_type == spec.FRAME_HEARTBEAT:

        # Return the amount of data and a Heartbeat frame
        return frame_end, Heartbeat()

    raise exceptions.InvalidFrameError("Unknown frame type: %i" % frame_type)

########NEW FILE########
__FILENAME__ = heartbeat
"""Handle AMQP Heartbeats"""
import logging

from pika import frame

LOGGER = logging.getLogger(__name__)


class HeartbeatChecker(object):
    """Checks to make sure that our heartbeat is received at the expected
    intervals.

    """
    MAX_IDLE_COUNT = 2
    _CONNECTION_FORCED = 320
    _STALE_CONNECTION = "Too Many Missed Heartbeats, No reply in %i seconds"

    def __init__(self, connection, interval, idle_count=MAX_IDLE_COUNT):
        """Create a heartbeat on connection sending a heartbeat frame every
        interval seconds.

        :param pika.connection.Connection: Connection object
        :param int interval: Heartbeat check interval
        :param int idle_count: Number of heartbeat intervals missed until the
                               connection is considered idle and disconnects

        """
        self._connection = connection
        self._interval = interval
        self._max_idle_count = idle_count

        # Initialize counters
        self._bytes_received = 0
        self._bytes_sent = 0
        self._heartbeat_frames_received = 0
        self._heartbeat_frames_sent = 0
        self._idle_byte_intervals = 0

        # The handle for the last timer
        self._timer = None

        # Setup the timer to fire in _interval seconds
        self._setup_timer()

    @property
    def active(self):
        """Return True if the connection's heartbeat attribute is set to this
        instance.

        :rtype True

        """
        return self._connection.heartbeat is self

    @property
    def bytes_received_on_connection(self):
        """Return the number of bytes received by the connection bytes object.

        :rtype int

        """
        return self._connection.bytes_received

    @property
    def connection_is_idle(self):
        """Returns true if the byte count hasn't changed in enough intervals
        to trip the max idle threshold.

        """
        return self._idle_byte_intervals >= self._max_idle_count

    def received(self):
        """Called when a heartbeat is received"""
        LOGGER.debug('Received heartbeat frame')
        self._heartbeat_frames_received += 1

    def send_and_check(self):
        """Invoked by a timer to send a heartbeat when we need to, check to see
        if we've missed any heartbeats and disconnect our connection if it's
        been idle too long.

        """
        LOGGER.debug('Received %i heartbeat frames, sent %i',
                     self._heartbeat_frames_received,
                     self._heartbeat_frames_sent)

        if self.connection_is_idle:
            return self._close_connection()

        # Connection has not received any data, increment the counter
        if not self._has_received_data:
            self._idle_byte_intervals += 1
        else:
            self._idle_byte_intervals = 0

        # Update the counters of bytes sent/received and the frames received
        self._update_counters()

        # Send a heartbeat frame
        self._send_heartbeat_frame()

        # Update the timer to fire again
        self._start_timer()

    def stop(self):
        """Stop the heartbeat checker"""
        if self._timer:
            LOGGER.debug('Removing timeout for next heartbeat interval')
            self._connection.remove_timeout(self._timer)
            self._timer = None

    def _close_connection(self):
        """Close the connection with the AMQP Connection-Forced value."""
        LOGGER.info('Connection is idle, %i stale byte intervals',
                    self._idle_byte_intervals)
        duration = self._max_idle_count * self._interval
        text = HeartbeatChecker._STALE_CONNECTION % duration
        self._connection.close(HeartbeatChecker._CONNECTION_FORCED, text)
        self._connection._on_disconnect(HeartbeatChecker._CONNECTION_FORCED,
                                        text)

    @property
    def _has_received_data(self):
        """Returns True if the connection has received data on the connection.

        :rtype: bool

        """
        return not self._bytes_received == self.bytes_received_on_connection

    def _new_heartbeat_frame(self):
        """Return a new heartbeat frame.

        :rtype pika.frame.Heartbeat

        """
        return frame.Heartbeat()

    def _send_heartbeat_frame(self):
        """Send a heartbeat frame on the connection.

        """
        LOGGER.debug('Sending heartbeat frame')
        self._connection._send_frame(self._new_heartbeat_frame())
        self._heartbeat_frames_sent += 1

    def _setup_timer(self):
        """Use the connection objects delayed_call function which is
        implemented by the Adapter for calling the check_heartbeats function
        every interval seconds.

        """
        self._timer = self._connection.add_timeout(self._interval,
                                                   self.send_and_check)

    def _start_timer(self):
        """If the connection still has this object set for heartbeats, add a
        new timer.

        """
        if self.active:
            self._setup_timer()

    def _update_counters(self):
        """Update the internal counters for bytes sent and received and the
        number of frames received

        """
        self._bytes_sent = self._connection.bytes_sent
        self._bytes_received = self._connection.bytes_received

########NEW FILE########
__FILENAME__ = spec
# ***** BEGIN LICENSE BLOCK *****
#
# For copyright and licensing please refer to COPYING.
#
# ***** END LICENSE BLOCK *****

# NOTE: Autogenerated code by codegen.py, do not edit

import struct
from pika import amqp_object
from pika import data


PROTOCOL_VERSION = (0, 9, 1)
PORT = 5672

ACCESS_REFUSED = 403
CHANNEL_ERROR = 504
COMMAND_INVALID = 503
CONNECTION_FORCED = 320
CONTENT_TOO_LARGE = 311
FRAME_BODY = 3
FRAME_END = 206
FRAME_END_SIZE = 1
FRAME_ERROR = 501
FRAME_HEADER = 2
FRAME_HEADER_SIZE = 7
FRAME_HEARTBEAT = 8
FRAME_MAX_SIZE = 131072
FRAME_METHOD = 1
FRAME_MIN_SIZE = 4096
INTERNAL_ERROR = 541
INVALID_PATH = 402
NOT_ALLOWED = 530
NOT_FOUND = 404
NOT_IMPLEMENTED = 540
NO_CONSUMERS = 313
NO_ROUTE = 312
PRECONDITION_FAILED = 406
REPLY_SUCCESS = 200
RESOURCE_ERROR = 506
RESOURCE_LOCKED = 405
SYNTAX_ERROR = 502
UNEXPECTED_FRAME = 505


class Connection(amqp_object.Class):

    INDEX = 0x000A  # 10
    NAME = 'Connection'

    class Start(amqp_object.Method):

        INDEX = 0x000A000A  # 10, 10; 655370
        NAME = 'Connection.Start'

        def __init__(self, version_major=0, version_minor=9, server_properties=None, mechanisms='PLAIN', locales='en_US'):
            self.version_major = version_major
            self.version_minor = version_minor
            self.server_properties = server_properties
            self.mechanisms = mechanisms
            self.locales = locales

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            self.version_major = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.version_minor = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            (self.server_properties, offset) = data.decode_table(encoded, offset)
            length = struct.unpack_from('>I', encoded, offset)[0]
            offset += 4
            self.mechanisms = encoded[offset:offset + length]
            try:
                self.mechanisms = str(self.mechanisms)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('>I', encoded, offset)[0]
            offset += 4
            self.locales = encoded[offset:offset + length]
            try:
                self.locales = str(self.locales)
            except UnicodeEncodeError:
                pass
            offset += length
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('B', self.version_major))
            pieces.append(struct.pack('B', self.version_minor))
            data.encode_table(pieces, self.server_properties)
            assert isinstance(self.mechanisms, basestring),\
                   'A non-bytestring value was supplied for self.mechanisms'
            value = self.mechanisms.encode('utf-8') if isinstance(self.mechanisms, unicode) else self.mechanisms
            pieces.append(struct.pack('>I', len(value)))
            pieces.append(value)
            assert isinstance(self.locales, basestring),\
                   'A non-bytestring value was supplied for self.locales'
            value = self.locales.encode('utf-8') if isinstance(self.locales, unicode) else self.locales
            pieces.append(struct.pack('>I', len(value)))
            pieces.append(value)
            return pieces

    class StartOk(amqp_object.Method):

        INDEX = 0x000A000B  # 10, 11; 655371
        NAME = 'Connection.StartOk'

        def __init__(self, client_properties=None, mechanism='PLAIN', response=None, locale='en_US'):
            self.client_properties = client_properties
            self.mechanism = mechanism
            self.response = response
            self.locale = locale

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            (self.client_properties, offset) = data.decode_table(encoded, offset)
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.mechanism = encoded[offset:offset + length]
            try:
                self.mechanism = str(self.mechanism)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('>I', encoded, offset)[0]
            offset += 4
            self.response = encoded[offset:offset + length]
            try:
                self.response = str(self.response)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.locale = encoded[offset:offset + length]
            try:
                self.locale = str(self.locale)
            except UnicodeEncodeError:
                pass
            offset += length
            return self

        def encode(self):
            pieces = list()
            data.encode_table(pieces, self.client_properties)
            assert isinstance(self.mechanism, basestring),\
                   'A non-bytestring value was supplied for self.mechanism'
            value = self.mechanism.encode('utf-8') if isinstance(self.mechanism, unicode) else self.mechanism
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            assert isinstance(self.response, basestring),\
                   'A non-bytestring value was supplied for self.response'
            value = self.response.encode('utf-8') if isinstance(self.response, unicode) else self.response
            pieces.append(struct.pack('>I', len(value)))
            pieces.append(value)
            assert isinstance(self.locale, basestring),\
                   'A non-bytestring value was supplied for self.locale'
            value = self.locale.encode('utf-8') if isinstance(self.locale, unicode) else self.locale
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            return pieces

    class Secure(amqp_object.Method):

        INDEX = 0x000A0014  # 10, 20; 655380
        NAME = 'Connection.Secure'

        def __init__(self, challenge=None):
            self.challenge = challenge

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            length = struct.unpack_from('>I', encoded, offset)[0]
            offset += 4
            self.challenge = encoded[offset:offset + length]
            try:
                self.challenge = str(self.challenge)
            except UnicodeEncodeError:
                pass
            offset += length
            return self

        def encode(self):
            pieces = list()
            assert isinstance(self.challenge, basestring),\
                   'A non-bytestring value was supplied for self.challenge'
            value = self.challenge.encode('utf-8') if isinstance(self.challenge, unicode) else self.challenge
            pieces.append(struct.pack('>I', len(value)))
            pieces.append(value)
            return pieces

    class SecureOk(amqp_object.Method):

        INDEX = 0x000A0015  # 10, 21; 655381
        NAME = 'Connection.SecureOk'

        def __init__(self, response=None):
            self.response = response

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            length = struct.unpack_from('>I', encoded, offset)[0]
            offset += 4
            self.response = encoded[offset:offset + length]
            try:
                self.response = str(self.response)
            except UnicodeEncodeError:
                pass
            offset += length
            return self

        def encode(self):
            pieces = list()
            assert isinstance(self.response, basestring),\
                   'A non-bytestring value was supplied for self.response'
            value = self.response.encode('utf-8') if isinstance(self.response, unicode) else self.response
            pieces.append(struct.pack('>I', len(value)))
            pieces.append(value)
            return pieces

    class Tune(amqp_object.Method):

        INDEX = 0x000A001E  # 10, 30; 655390
        NAME = 'Connection.Tune'

        def __init__(self, channel_max=0, frame_max=0, heartbeat=0):
            self.channel_max = channel_max
            self.frame_max = frame_max
            self.heartbeat = heartbeat

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            self.channel_max = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            self.frame_max = struct.unpack_from('>I', encoded, offset)[0]
            offset += 4
            self.heartbeat = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.channel_max))
            pieces.append(struct.pack('>I', self.frame_max))
            pieces.append(struct.pack('>H', self.heartbeat))
            return pieces

    class TuneOk(amqp_object.Method):

        INDEX = 0x000A001F  # 10, 31; 655391
        NAME = 'Connection.TuneOk'

        def __init__(self, channel_max=0, frame_max=0, heartbeat=0):
            self.channel_max = channel_max
            self.frame_max = frame_max
            self.heartbeat = heartbeat

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            self.channel_max = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            self.frame_max = struct.unpack_from('>I', encoded, offset)[0]
            offset += 4
            self.heartbeat = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.channel_max))
            pieces.append(struct.pack('>I', self.frame_max))
            pieces.append(struct.pack('>H', self.heartbeat))
            return pieces

    class Open(amqp_object.Method):

        INDEX = 0x000A0028  # 10, 40; 655400
        NAME = 'Connection.Open'

        def __init__(self, virtual_host='/', capabilities='', insist=False):
            self.virtual_host = virtual_host
            self.capabilities = capabilities
            self.insist = insist

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.virtual_host = encoded[offset:offset + length]
            try:
                self.virtual_host = str(self.virtual_host)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.capabilities = encoded[offset:offset + length]
            try:
                self.capabilities = str(self.capabilities)
            except UnicodeEncodeError:
                pass
            offset += length
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.insist = (bit_buffer & (1 << 0)) != 0
            return self

        def encode(self):
            pieces = list()
            assert isinstance(self.virtual_host, basestring),\
                   'A non-bytestring value was supplied for self.virtual_host'
            value = self.virtual_host.encode('utf-8') if isinstance(self.virtual_host, unicode) else self.virtual_host
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            assert isinstance(self.capabilities, basestring),\
                   'A non-bytestring value was supplied for self.capabilities'
            value = self.capabilities.encode('utf-8') if isinstance(self.capabilities, unicode) else self.capabilities
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            bit_buffer = 0
            if self.insist:
                bit_buffer = bit_buffer | (1 << 0)
            pieces.append(struct.pack('B', bit_buffer))
            return pieces

    class OpenOk(amqp_object.Method):

        INDEX = 0x000A0029  # 10, 41; 655401
        NAME = 'Connection.OpenOk'

        def __init__(self, known_hosts=''):
            self.known_hosts = known_hosts

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.known_hosts = encoded[offset:offset + length]
            try:
                self.known_hosts = str(self.known_hosts)
            except UnicodeEncodeError:
                pass
            offset += length
            return self

        def encode(self):
            pieces = list()
            assert isinstance(self.known_hosts, basestring),\
                   'A non-bytestring value was supplied for self.known_hosts'
            value = self.known_hosts.encode('utf-8') if isinstance(self.known_hosts, unicode) else self.known_hosts
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            return pieces

    class Close(amqp_object.Method):

        INDEX = 0x000A0032  # 10, 50; 655410
        NAME = 'Connection.Close'

        def __init__(self, reply_code=None, reply_text='', class_id=None, method_id=None):
            self.reply_code = reply_code
            self.reply_text = reply_text
            self.class_id = class_id
            self.method_id = method_id

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            self.reply_code = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.reply_text = encoded[offset:offset + length]
            try:
                self.reply_text = str(self.reply_text)
            except UnicodeEncodeError:
                pass
            offset += length
            self.class_id = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            self.method_id = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.reply_code))
            assert isinstance(self.reply_text, basestring),\
                   'A non-bytestring value was supplied for self.reply_text'
            value = self.reply_text.encode('utf-8') if isinstance(self.reply_text, unicode) else self.reply_text
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            pieces.append(struct.pack('>H', self.class_id))
            pieces.append(struct.pack('>H', self.method_id))
            return pieces

    class CloseOk(amqp_object.Method):

        INDEX = 0x000A0033  # 10, 51; 655411
        NAME = 'Connection.CloseOk'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces

    class Blocked(amqp_object.Method):

        INDEX = 0x000A003C  # 10, 60; 655420
        NAME = 'Connection.Blocked'

        def __init__(self, reason=''):
            self.reason = reason

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.reason = encoded[offset:offset + length]
            try:
                self.reason = str(self.reason)
            except UnicodeEncodeError:
                pass
            offset += length
            return self

        def encode(self):
            pieces = list()
            assert isinstance(self.reason, basestring),\
                   'A non-bytestring value was supplied for self.reason'
            value = self.reason.encode('utf-8') if isinstance(self.reason, unicode) else self.reason
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            return pieces

    class Unblocked(amqp_object.Method):

        INDEX = 0x000A003D  # 10, 61; 655421
        NAME = 'Connection.Unblocked'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces


class Channel(amqp_object.Class):

    INDEX = 0x0014  # 20
    NAME = 'Channel'

    class Open(amqp_object.Method):

        INDEX = 0x0014000A  # 20, 10; 1310730
        NAME = 'Channel.Open'

        def __init__(self, out_of_band=''):
            self.out_of_band = out_of_band

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.out_of_band = encoded[offset:offset + length]
            try:
                self.out_of_band = str(self.out_of_band)
            except UnicodeEncodeError:
                pass
            offset += length
            return self

        def encode(self):
            pieces = list()
            assert isinstance(self.out_of_band, basestring),\
                   'A non-bytestring value was supplied for self.out_of_band'
            value = self.out_of_band.encode('utf-8') if isinstance(self.out_of_band, unicode) else self.out_of_band
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            return pieces

    class OpenOk(amqp_object.Method):

        INDEX = 0x0014000B  # 20, 11; 1310731
        NAME = 'Channel.OpenOk'

        def __init__(self, channel_id=''):
            self.channel_id = channel_id

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            length = struct.unpack_from('>I', encoded, offset)[0]
            offset += 4
            self.channel_id = encoded[offset:offset + length]
            try:
                self.channel_id = str(self.channel_id)
            except UnicodeEncodeError:
                pass
            offset += length
            return self

        def encode(self):
            pieces = list()
            assert isinstance(self.channel_id, basestring),\
                   'A non-bytestring value was supplied for self.channel_id'
            value = self.channel_id.encode('utf-8') if isinstance(self.channel_id, unicode) else self.channel_id
            pieces.append(struct.pack('>I', len(value)))
            pieces.append(value)
            return pieces

    class Flow(amqp_object.Method):

        INDEX = 0x00140014  # 20, 20; 1310740
        NAME = 'Channel.Flow'

        def __init__(self, active=None):
            self.active = active

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.active = (bit_buffer & (1 << 0)) != 0
            return self

        def encode(self):
            pieces = list()
            bit_buffer = 0
            if self.active:
                bit_buffer = bit_buffer | (1 << 0)
            pieces.append(struct.pack('B', bit_buffer))
            return pieces

    class FlowOk(amqp_object.Method):

        INDEX = 0x00140015  # 20, 21; 1310741
        NAME = 'Channel.FlowOk'

        def __init__(self, active=None):
            self.active = active

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.active = (bit_buffer & (1 << 0)) != 0
            return self

        def encode(self):
            pieces = list()
            bit_buffer = 0
            if self.active:
                bit_buffer = bit_buffer | (1 << 0)
            pieces.append(struct.pack('B', bit_buffer))
            return pieces

    class Close(amqp_object.Method):

        INDEX = 0x00140028  # 20, 40; 1310760
        NAME = 'Channel.Close'

        def __init__(self, reply_code=None, reply_text='', class_id=None, method_id=None):
            self.reply_code = reply_code
            self.reply_text = reply_text
            self.class_id = class_id
            self.method_id = method_id

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            self.reply_code = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.reply_text = encoded[offset:offset + length]
            try:
                self.reply_text = str(self.reply_text)
            except UnicodeEncodeError:
                pass
            offset += length
            self.class_id = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            self.method_id = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.reply_code))
            assert isinstance(self.reply_text, basestring),\
                   'A non-bytestring value was supplied for self.reply_text'
            value = self.reply_text.encode('utf-8') if isinstance(self.reply_text, unicode) else self.reply_text
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            pieces.append(struct.pack('>H', self.class_id))
            pieces.append(struct.pack('>H', self.method_id))
            return pieces

    class CloseOk(amqp_object.Method):

        INDEX = 0x00140029  # 20, 41; 1310761
        NAME = 'Channel.CloseOk'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces


class Access(amqp_object.Class):

    INDEX = 0x001E  # 30
    NAME = 'Access'

    class Request(amqp_object.Method):

        INDEX = 0x001E000A  # 30, 10; 1966090
        NAME = 'Access.Request'

        def __init__(self, realm='/data', exclusive=False, passive=True, active=True, write=True, read=True):
            self.realm = realm
            self.exclusive = exclusive
            self.passive = passive
            self.active = active
            self.write = write
            self.read = read

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.realm = encoded[offset:offset + length]
            try:
                self.realm = str(self.realm)
            except UnicodeEncodeError:
                pass
            offset += length
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.exclusive = (bit_buffer & (1 << 0)) != 0
            self.passive = (bit_buffer & (1 << 1)) != 0
            self.active = (bit_buffer & (1 << 2)) != 0
            self.write = (bit_buffer & (1 << 3)) != 0
            self.read = (bit_buffer & (1 << 4)) != 0
            return self

        def encode(self):
            pieces = list()
            assert isinstance(self.realm, basestring),\
                   'A non-bytestring value was supplied for self.realm'
            value = self.realm.encode('utf-8') if isinstance(self.realm, unicode) else self.realm
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            bit_buffer = 0
            if self.exclusive:
                bit_buffer = bit_buffer | (1 << 0)
            if self.passive:
                bit_buffer = bit_buffer | (1 << 1)
            if self.active:
                bit_buffer = bit_buffer | (1 << 2)
            if self.write:
                bit_buffer = bit_buffer | (1 << 3)
            if self.read:
                bit_buffer = bit_buffer | (1 << 4)
            pieces.append(struct.pack('B', bit_buffer))
            return pieces

    class RequestOk(amqp_object.Method):

        INDEX = 0x001E000B  # 30, 11; 1966091
        NAME = 'Access.RequestOk'

        def __init__(self, ticket=1):
            self.ticket = ticket

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            self.ticket = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.ticket))
            return pieces


class Exchange(amqp_object.Class):

    INDEX = 0x0028  # 40
    NAME = 'Exchange'

    class Declare(amqp_object.Method):

        INDEX = 0x0028000A  # 40, 10; 2621450
        NAME = 'Exchange.Declare'

        def __init__(self, ticket=0, exchange=None, type='direct', passive=False, durable=False, auto_delete=False, internal=False, nowait=False, arguments={}):
            self.ticket = ticket
            self.exchange = exchange
            self.type = type
            self.passive = passive
            self.durable = durable
            self.auto_delete = auto_delete
            self.internal = internal
            self.nowait = nowait
            self.arguments = arguments

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            self.ticket = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.exchange = encoded[offset:offset + length]
            try:
                self.exchange = str(self.exchange)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.type = encoded[offset:offset + length]
            try:
                self.type = str(self.type)
            except UnicodeEncodeError:
                pass
            offset += length
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.passive = (bit_buffer & (1 << 0)) != 0
            self.durable = (bit_buffer & (1 << 1)) != 0
            self.auto_delete = (bit_buffer & (1 << 2)) != 0
            self.internal = (bit_buffer & (1 << 3)) != 0
            self.nowait = (bit_buffer & (1 << 4)) != 0
            (self.arguments, offset) = data.decode_table(encoded, offset)
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.ticket))
            assert isinstance(self.exchange, basestring),\
                   'A non-bytestring value was supplied for self.exchange'
            value = self.exchange.encode('utf-8') if isinstance(self.exchange, unicode) else self.exchange
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            assert isinstance(self.type, basestring),\
                   'A non-bytestring value was supplied for self.type'
            value = self.type.encode('utf-8') if isinstance(self.type, unicode) else self.type
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            bit_buffer = 0
            if self.passive:
                bit_buffer = bit_buffer | (1 << 0)
            if self.durable:
                bit_buffer = bit_buffer | (1 << 1)
            if self.auto_delete:
                bit_buffer = bit_buffer | (1 << 2)
            if self.internal:
                bit_buffer = bit_buffer | (1 << 3)
            if self.nowait:
                bit_buffer = bit_buffer | (1 << 4)
            pieces.append(struct.pack('B', bit_buffer))
            data.encode_table(pieces, self.arguments)
            return pieces

    class DeclareOk(amqp_object.Method):

        INDEX = 0x0028000B  # 40, 11; 2621451
        NAME = 'Exchange.DeclareOk'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces

    class Delete(amqp_object.Method):

        INDEX = 0x00280014  # 40, 20; 2621460
        NAME = 'Exchange.Delete'

        def __init__(self, ticket=0, exchange=None, if_unused=False, nowait=False):
            self.ticket = ticket
            self.exchange = exchange
            self.if_unused = if_unused
            self.nowait = nowait

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            self.ticket = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.exchange = encoded[offset:offset + length]
            try:
                self.exchange = str(self.exchange)
            except UnicodeEncodeError:
                pass
            offset += length
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.if_unused = (bit_buffer & (1 << 0)) != 0
            self.nowait = (bit_buffer & (1 << 1)) != 0
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.ticket))
            assert isinstance(self.exchange, basestring),\
                   'A non-bytestring value was supplied for self.exchange'
            value = self.exchange.encode('utf-8') if isinstance(self.exchange, unicode) else self.exchange
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            bit_buffer = 0
            if self.if_unused:
                bit_buffer = bit_buffer | (1 << 0)
            if self.nowait:
                bit_buffer = bit_buffer | (1 << 1)
            pieces.append(struct.pack('B', bit_buffer))
            return pieces

    class DeleteOk(amqp_object.Method):

        INDEX = 0x00280015  # 40, 21; 2621461
        NAME = 'Exchange.DeleteOk'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces

    class Bind(amqp_object.Method):

        INDEX = 0x0028001E  # 40, 30; 2621470
        NAME = 'Exchange.Bind'

        def __init__(self, ticket=0, destination=None, source=None, routing_key='', nowait=False, arguments={}):
            self.ticket = ticket
            self.destination = destination
            self.source = source
            self.routing_key = routing_key
            self.nowait = nowait
            self.arguments = arguments

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            self.ticket = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.destination = encoded[offset:offset + length]
            try:
                self.destination = str(self.destination)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.source = encoded[offset:offset + length]
            try:
                self.source = str(self.source)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.routing_key = encoded[offset:offset + length]
            try:
                self.routing_key = str(self.routing_key)
            except UnicodeEncodeError:
                pass
            offset += length
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.nowait = (bit_buffer & (1 << 0)) != 0
            (self.arguments, offset) = data.decode_table(encoded, offset)
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.ticket))
            assert isinstance(self.destination, basestring),\
                   'A non-bytestring value was supplied for self.destination'
            value = self.destination.encode('utf-8') if isinstance(self.destination, unicode) else self.destination
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            assert isinstance(self.source, basestring),\
                   'A non-bytestring value was supplied for self.source'
            value = self.source.encode('utf-8') if isinstance(self.source, unicode) else self.source
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            assert isinstance(self.routing_key, basestring),\
                   'A non-bytestring value was supplied for self.routing_key'
            value = self.routing_key.encode('utf-8') if isinstance(self.routing_key, unicode) else self.routing_key
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            bit_buffer = 0
            if self.nowait:
                bit_buffer = bit_buffer | (1 << 0)
            pieces.append(struct.pack('B', bit_buffer))
            data.encode_table(pieces, self.arguments)
            return pieces

    class BindOk(amqp_object.Method):

        INDEX = 0x0028001F  # 40, 31; 2621471
        NAME = 'Exchange.BindOk'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces

    class Unbind(amqp_object.Method):

        INDEX = 0x00280028  # 40, 40; 2621480
        NAME = 'Exchange.Unbind'

        def __init__(self, ticket=0, destination=None, source=None, routing_key='', nowait=False, arguments={}):
            self.ticket = ticket
            self.destination = destination
            self.source = source
            self.routing_key = routing_key
            self.nowait = nowait
            self.arguments = arguments

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            self.ticket = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.destination = encoded[offset:offset + length]
            try:
                self.destination = str(self.destination)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.source = encoded[offset:offset + length]
            try:
                self.source = str(self.source)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.routing_key = encoded[offset:offset + length]
            try:
                self.routing_key = str(self.routing_key)
            except UnicodeEncodeError:
                pass
            offset += length
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.nowait = (bit_buffer & (1 << 0)) != 0
            (self.arguments, offset) = data.decode_table(encoded, offset)
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.ticket))
            assert isinstance(self.destination, basestring),\
                   'A non-bytestring value was supplied for self.destination'
            value = self.destination.encode('utf-8') if isinstance(self.destination, unicode) else self.destination
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            assert isinstance(self.source, basestring),\
                   'A non-bytestring value was supplied for self.source'
            value = self.source.encode('utf-8') if isinstance(self.source, unicode) else self.source
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            assert isinstance(self.routing_key, basestring),\
                   'A non-bytestring value was supplied for self.routing_key'
            value = self.routing_key.encode('utf-8') if isinstance(self.routing_key, unicode) else self.routing_key
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            bit_buffer = 0
            if self.nowait:
                bit_buffer = bit_buffer | (1 << 0)
            pieces.append(struct.pack('B', bit_buffer))
            data.encode_table(pieces, self.arguments)
            return pieces

    class UnbindOk(amqp_object.Method):

        INDEX = 0x00280033  # 40, 51; 2621491
        NAME = 'Exchange.UnbindOk'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces


class Queue(amqp_object.Class):

    INDEX = 0x0032  # 50
    NAME = 'Queue'

    class Declare(amqp_object.Method):

        INDEX = 0x0032000A  # 50, 10; 3276810
        NAME = 'Queue.Declare'

        def __init__(self, ticket=0, queue='', passive=False, durable=False, exclusive=False, auto_delete=False, nowait=False, arguments={}):
            self.ticket = ticket
            self.queue = queue
            self.passive = passive
            self.durable = durable
            self.exclusive = exclusive
            self.auto_delete = auto_delete
            self.nowait = nowait
            self.arguments = arguments

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            self.ticket = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.queue = encoded[offset:offset + length]
            try:
                self.queue = str(self.queue)
            except UnicodeEncodeError:
                pass
            offset += length
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.passive = (bit_buffer & (1 << 0)) != 0
            self.durable = (bit_buffer & (1 << 1)) != 0
            self.exclusive = (bit_buffer & (1 << 2)) != 0
            self.auto_delete = (bit_buffer & (1 << 3)) != 0
            self.nowait = (bit_buffer & (1 << 4)) != 0
            (self.arguments, offset) = data.decode_table(encoded, offset)
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.ticket))
            assert isinstance(self.queue, basestring),\
                   'A non-bytestring value was supplied for self.queue'
            value = self.queue.encode('utf-8') if isinstance(self.queue, unicode) else self.queue
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            bit_buffer = 0
            if self.passive:
                bit_buffer = bit_buffer | (1 << 0)
            if self.durable:
                bit_buffer = bit_buffer | (1 << 1)
            if self.exclusive:
                bit_buffer = bit_buffer | (1 << 2)
            if self.auto_delete:
                bit_buffer = bit_buffer | (1 << 3)
            if self.nowait:
                bit_buffer = bit_buffer | (1 << 4)
            pieces.append(struct.pack('B', bit_buffer))
            data.encode_table(pieces, self.arguments)
            return pieces

    class DeclareOk(amqp_object.Method):

        INDEX = 0x0032000B  # 50, 11; 3276811
        NAME = 'Queue.DeclareOk'

        def __init__(self, queue=None, message_count=None, consumer_count=None):
            self.queue = queue
            self.message_count = message_count
            self.consumer_count = consumer_count

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.queue = encoded[offset:offset + length]
            try:
                self.queue = str(self.queue)
            except UnicodeEncodeError:
                pass
            offset += length
            self.message_count = struct.unpack_from('>I', encoded, offset)[0]
            offset += 4
            self.consumer_count = struct.unpack_from('>I', encoded, offset)[0]
            offset += 4
            return self

        def encode(self):
            pieces = list()
            assert isinstance(self.queue, basestring),\
                   'A non-bytestring value was supplied for self.queue'
            value = self.queue.encode('utf-8') if isinstance(self.queue, unicode) else self.queue
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            pieces.append(struct.pack('>I', self.message_count))
            pieces.append(struct.pack('>I', self.consumer_count))
            return pieces

    class Bind(amqp_object.Method):

        INDEX = 0x00320014  # 50, 20; 3276820
        NAME = 'Queue.Bind'

        def __init__(self, ticket=0, queue='', exchange=None, routing_key='', nowait=False, arguments={}):
            self.ticket = ticket
            self.queue = queue
            self.exchange = exchange
            self.routing_key = routing_key
            self.nowait = nowait
            self.arguments = arguments

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            self.ticket = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.queue = encoded[offset:offset + length]
            try:
                self.queue = str(self.queue)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.exchange = encoded[offset:offset + length]
            try:
                self.exchange = str(self.exchange)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.routing_key = encoded[offset:offset + length]
            try:
                self.routing_key = str(self.routing_key)
            except UnicodeEncodeError:
                pass
            offset += length
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.nowait = (bit_buffer & (1 << 0)) != 0
            (self.arguments, offset) = data.decode_table(encoded, offset)
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.ticket))
            assert isinstance(self.queue, basestring),\
                   'A non-bytestring value was supplied for self.queue'
            value = self.queue.encode('utf-8') if isinstance(self.queue, unicode) else self.queue
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            assert isinstance(self.exchange, basestring),\
                   'A non-bytestring value was supplied for self.exchange'
            value = self.exchange.encode('utf-8') if isinstance(self.exchange, unicode) else self.exchange
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            assert isinstance(self.routing_key, basestring),\
                   'A non-bytestring value was supplied for self.routing_key'
            value = self.routing_key.encode('utf-8') if isinstance(self.routing_key, unicode) else self.routing_key
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            bit_buffer = 0
            if self.nowait:
                bit_buffer = bit_buffer | (1 << 0)
            pieces.append(struct.pack('B', bit_buffer))
            data.encode_table(pieces, self.arguments)
            return pieces

    class BindOk(amqp_object.Method):

        INDEX = 0x00320015  # 50, 21; 3276821
        NAME = 'Queue.BindOk'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces

    class Purge(amqp_object.Method):

        INDEX = 0x0032001E  # 50, 30; 3276830
        NAME = 'Queue.Purge'

        def __init__(self, ticket=0, queue='', nowait=False):
            self.ticket = ticket
            self.queue = queue
            self.nowait = nowait

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            self.ticket = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.queue = encoded[offset:offset + length]
            try:
                self.queue = str(self.queue)
            except UnicodeEncodeError:
                pass
            offset += length
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.nowait = (bit_buffer & (1 << 0)) != 0
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.ticket))
            assert isinstance(self.queue, basestring),\
                   'A non-bytestring value was supplied for self.queue'
            value = self.queue.encode('utf-8') if isinstance(self.queue, unicode) else self.queue
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            bit_buffer = 0
            if self.nowait:
                bit_buffer = bit_buffer | (1 << 0)
            pieces.append(struct.pack('B', bit_buffer))
            return pieces

    class PurgeOk(amqp_object.Method):

        INDEX = 0x0032001F  # 50, 31; 3276831
        NAME = 'Queue.PurgeOk'

        def __init__(self, message_count=None):
            self.message_count = message_count

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            self.message_count = struct.unpack_from('>I', encoded, offset)[0]
            offset += 4
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>I', self.message_count))
            return pieces

    class Delete(amqp_object.Method):

        INDEX = 0x00320028  # 50, 40; 3276840
        NAME = 'Queue.Delete'

        def __init__(self, ticket=0, queue='', if_unused=False, if_empty=False, nowait=False):
            self.ticket = ticket
            self.queue = queue
            self.if_unused = if_unused
            self.if_empty = if_empty
            self.nowait = nowait

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            self.ticket = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.queue = encoded[offset:offset + length]
            try:
                self.queue = str(self.queue)
            except UnicodeEncodeError:
                pass
            offset += length
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.if_unused = (bit_buffer & (1 << 0)) != 0
            self.if_empty = (bit_buffer & (1 << 1)) != 0
            self.nowait = (bit_buffer & (1 << 2)) != 0
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.ticket))
            assert isinstance(self.queue, basestring),\
                   'A non-bytestring value was supplied for self.queue'
            value = self.queue.encode('utf-8') if isinstance(self.queue, unicode) else self.queue
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            bit_buffer = 0
            if self.if_unused:
                bit_buffer = bit_buffer | (1 << 0)
            if self.if_empty:
                bit_buffer = bit_buffer | (1 << 1)
            if self.nowait:
                bit_buffer = bit_buffer | (1 << 2)
            pieces.append(struct.pack('B', bit_buffer))
            return pieces

    class DeleteOk(amqp_object.Method):

        INDEX = 0x00320029  # 50, 41; 3276841
        NAME = 'Queue.DeleteOk'

        def __init__(self, message_count=None):
            self.message_count = message_count

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            self.message_count = struct.unpack_from('>I', encoded, offset)[0]
            offset += 4
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>I', self.message_count))
            return pieces

    class Unbind(amqp_object.Method):

        INDEX = 0x00320032  # 50, 50; 3276850
        NAME = 'Queue.Unbind'

        def __init__(self, ticket=0, queue='', exchange=None, routing_key='', arguments={}):
            self.ticket = ticket
            self.queue = queue
            self.exchange = exchange
            self.routing_key = routing_key
            self.arguments = arguments

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            self.ticket = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.queue = encoded[offset:offset + length]
            try:
                self.queue = str(self.queue)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.exchange = encoded[offset:offset + length]
            try:
                self.exchange = str(self.exchange)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.routing_key = encoded[offset:offset + length]
            try:
                self.routing_key = str(self.routing_key)
            except UnicodeEncodeError:
                pass
            offset += length
            (self.arguments, offset) = data.decode_table(encoded, offset)
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.ticket))
            assert isinstance(self.queue, basestring),\
                   'A non-bytestring value was supplied for self.queue'
            value = self.queue.encode('utf-8') if isinstance(self.queue, unicode) else self.queue
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            assert isinstance(self.exchange, basestring),\
                   'A non-bytestring value was supplied for self.exchange'
            value = self.exchange.encode('utf-8') if isinstance(self.exchange, unicode) else self.exchange
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            assert isinstance(self.routing_key, basestring),\
                   'A non-bytestring value was supplied for self.routing_key'
            value = self.routing_key.encode('utf-8') if isinstance(self.routing_key, unicode) else self.routing_key
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            data.encode_table(pieces, self.arguments)
            return pieces

    class UnbindOk(amqp_object.Method):

        INDEX = 0x00320033  # 50, 51; 3276851
        NAME = 'Queue.UnbindOk'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces


class Basic(amqp_object.Class):

    INDEX = 0x003C  # 60
    NAME = 'Basic'

    class Qos(amqp_object.Method):

        INDEX = 0x003C000A  # 60, 10; 3932170
        NAME = 'Basic.Qos'

        def __init__(self, prefetch_size=0, prefetch_count=0, global_=False):
            self.prefetch_size = prefetch_size
            self.prefetch_count = prefetch_count
            self.global_ = global_

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            self.prefetch_size = struct.unpack_from('>I', encoded, offset)[0]
            offset += 4
            self.prefetch_count = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.global_ = (bit_buffer & (1 << 0)) != 0
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>I', self.prefetch_size))
            pieces.append(struct.pack('>H', self.prefetch_count))
            bit_buffer = 0
            if self.global_:
                bit_buffer = bit_buffer | (1 << 0)
            pieces.append(struct.pack('B', bit_buffer))
            return pieces

    class QosOk(amqp_object.Method):

        INDEX = 0x003C000B  # 60, 11; 3932171
        NAME = 'Basic.QosOk'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces

    class Consume(amqp_object.Method):

        INDEX = 0x003C0014  # 60, 20; 3932180
        NAME = 'Basic.Consume'

        def __init__(self, ticket=0, queue='', consumer_tag='', no_local=False, no_ack=False, exclusive=False, nowait=False, arguments={}):
            self.ticket = ticket
            self.queue = queue
            self.consumer_tag = consumer_tag
            self.no_local = no_local
            self.no_ack = no_ack
            self.exclusive = exclusive
            self.nowait = nowait
            self.arguments = arguments

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            self.ticket = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.queue = encoded[offset:offset + length]
            try:
                self.queue = str(self.queue)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.consumer_tag = encoded[offset:offset + length]
            try:
                self.consumer_tag = str(self.consumer_tag)
            except UnicodeEncodeError:
                pass
            offset += length
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.no_local = (bit_buffer & (1 << 0)) != 0
            self.no_ack = (bit_buffer & (1 << 1)) != 0
            self.exclusive = (bit_buffer & (1 << 2)) != 0
            self.nowait = (bit_buffer & (1 << 3)) != 0
            (self.arguments, offset) = data.decode_table(encoded, offset)
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.ticket))
            assert isinstance(self.queue, basestring),\
                   'A non-bytestring value was supplied for self.queue'
            value = self.queue.encode('utf-8') if isinstance(self.queue, unicode) else self.queue
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            assert isinstance(self.consumer_tag, basestring),\
                   'A non-bytestring value was supplied for self.consumer_tag'
            value = self.consumer_tag.encode('utf-8') if isinstance(self.consumer_tag, unicode) else self.consumer_tag
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            bit_buffer = 0
            if self.no_local:
                bit_buffer = bit_buffer | (1 << 0)
            if self.no_ack:
                bit_buffer = bit_buffer | (1 << 1)
            if self.exclusive:
                bit_buffer = bit_buffer | (1 << 2)
            if self.nowait:
                bit_buffer = bit_buffer | (1 << 3)
            pieces.append(struct.pack('B', bit_buffer))
            data.encode_table(pieces, self.arguments)
            return pieces

    class ConsumeOk(amqp_object.Method):

        INDEX = 0x003C0015  # 60, 21; 3932181
        NAME = 'Basic.ConsumeOk'

        def __init__(self, consumer_tag=None):
            self.consumer_tag = consumer_tag

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.consumer_tag = encoded[offset:offset + length]
            try:
                self.consumer_tag = str(self.consumer_tag)
            except UnicodeEncodeError:
                pass
            offset += length
            return self

        def encode(self):
            pieces = list()
            assert isinstance(self.consumer_tag, basestring),\
                   'A non-bytestring value was supplied for self.consumer_tag'
            value = self.consumer_tag.encode('utf-8') if isinstance(self.consumer_tag, unicode) else self.consumer_tag
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            return pieces

    class Cancel(amqp_object.Method):

        INDEX = 0x003C001E  # 60, 30; 3932190
        NAME = 'Basic.Cancel'

        def __init__(self, consumer_tag=None, nowait=False):
            self.consumer_tag = consumer_tag
            self.nowait = nowait

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.consumer_tag = encoded[offset:offset + length]
            try:
                self.consumer_tag = str(self.consumer_tag)
            except UnicodeEncodeError:
                pass
            offset += length
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.nowait = (bit_buffer & (1 << 0)) != 0
            return self

        def encode(self):
            pieces = list()
            assert isinstance(self.consumer_tag, basestring),\
                   'A non-bytestring value was supplied for self.consumer_tag'
            value = self.consumer_tag.encode('utf-8') if isinstance(self.consumer_tag, unicode) else self.consumer_tag
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            bit_buffer = 0
            if self.nowait:
                bit_buffer = bit_buffer | (1 << 0)
            pieces.append(struct.pack('B', bit_buffer))
            return pieces

    class CancelOk(amqp_object.Method):

        INDEX = 0x003C001F  # 60, 31; 3932191
        NAME = 'Basic.CancelOk'

        def __init__(self, consumer_tag=None):
            self.consumer_tag = consumer_tag

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.consumer_tag = encoded[offset:offset + length]
            try:
                self.consumer_tag = str(self.consumer_tag)
            except UnicodeEncodeError:
                pass
            offset += length
            return self

        def encode(self):
            pieces = list()
            assert isinstance(self.consumer_tag, basestring),\
                   'A non-bytestring value was supplied for self.consumer_tag'
            value = self.consumer_tag.encode('utf-8') if isinstance(self.consumer_tag, unicode) else self.consumer_tag
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            return pieces

    class Publish(amqp_object.Method):

        INDEX = 0x003C0028  # 60, 40; 3932200
        NAME = 'Basic.Publish'

        def __init__(self, ticket=0, exchange='', routing_key='', mandatory=False, immediate=False):
            self.ticket = ticket
            self.exchange = exchange
            self.routing_key = routing_key
            self.mandatory = mandatory
            self.immediate = immediate

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            self.ticket = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.exchange = encoded[offset:offset + length]
            try:
                self.exchange = str(self.exchange)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.routing_key = encoded[offset:offset + length]
            try:
                self.routing_key = str(self.routing_key)
            except UnicodeEncodeError:
                pass
            offset += length
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.mandatory = (bit_buffer & (1 << 0)) != 0
            self.immediate = (bit_buffer & (1 << 1)) != 0
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.ticket))
            assert isinstance(self.exchange, basestring),\
                   'A non-bytestring value was supplied for self.exchange'
            value = self.exchange.encode('utf-8') if isinstance(self.exchange, unicode) else self.exchange
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            assert isinstance(self.routing_key, basestring),\
                   'A non-bytestring value was supplied for self.routing_key'
            value = self.routing_key.encode('utf-8') if isinstance(self.routing_key, unicode) else self.routing_key
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            bit_buffer = 0
            if self.mandatory:
                bit_buffer = bit_buffer | (1 << 0)
            if self.immediate:
                bit_buffer = bit_buffer | (1 << 1)
            pieces.append(struct.pack('B', bit_buffer))
            return pieces

    class Return(amqp_object.Method):

        INDEX = 0x003C0032  # 60, 50; 3932210
        NAME = 'Basic.Return'

        def __init__(self, reply_code=None, reply_text='', exchange=None, routing_key=None):
            self.reply_code = reply_code
            self.reply_text = reply_text
            self.exchange = exchange
            self.routing_key = routing_key

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            self.reply_code = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.reply_text = encoded[offset:offset + length]
            try:
                self.reply_text = str(self.reply_text)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.exchange = encoded[offset:offset + length]
            try:
                self.exchange = str(self.exchange)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.routing_key = encoded[offset:offset + length]
            try:
                self.routing_key = str(self.routing_key)
            except UnicodeEncodeError:
                pass
            offset += length
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.reply_code))
            assert isinstance(self.reply_text, basestring),\
                   'A non-bytestring value was supplied for self.reply_text'
            value = self.reply_text.encode('utf-8') if isinstance(self.reply_text, unicode) else self.reply_text
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            assert isinstance(self.exchange, basestring),\
                   'A non-bytestring value was supplied for self.exchange'
            value = self.exchange.encode('utf-8') if isinstance(self.exchange, unicode) else self.exchange
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            assert isinstance(self.routing_key, basestring),\
                   'A non-bytestring value was supplied for self.routing_key'
            value = self.routing_key.encode('utf-8') if isinstance(self.routing_key, unicode) else self.routing_key
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            return pieces

    class Deliver(amqp_object.Method):

        INDEX = 0x003C003C  # 60, 60; 3932220
        NAME = 'Basic.Deliver'

        def __init__(self, consumer_tag=None, delivery_tag=None, redelivered=False, exchange=None, routing_key=None):
            self.consumer_tag = consumer_tag
            self.delivery_tag = delivery_tag
            self.redelivered = redelivered
            self.exchange = exchange
            self.routing_key = routing_key

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.consumer_tag = encoded[offset:offset + length]
            try:
                self.consumer_tag = str(self.consumer_tag)
            except UnicodeEncodeError:
                pass
            offset += length
            self.delivery_tag = struct.unpack_from('>Q', encoded, offset)[0]
            offset += 8
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.redelivered = (bit_buffer & (1 << 0)) != 0
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.exchange = encoded[offset:offset + length]
            try:
                self.exchange = str(self.exchange)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.routing_key = encoded[offset:offset + length]
            try:
                self.routing_key = str(self.routing_key)
            except UnicodeEncodeError:
                pass
            offset += length
            return self

        def encode(self):
            pieces = list()
            assert isinstance(self.consumer_tag, basestring),\
                   'A non-bytestring value was supplied for self.consumer_tag'
            value = self.consumer_tag.encode('utf-8') if isinstance(self.consumer_tag, unicode) else self.consumer_tag
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            pieces.append(struct.pack('>Q', self.delivery_tag))
            bit_buffer = 0
            if self.redelivered:
                bit_buffer = bit_buffer | (1 << 0)
            pieces.append(struct.pack('B', bit_buffer))
            assert isinstance(self.exchange, basestring),\
                   'A non-bytestring value was supplied for self.exchange'
            value = self.exchange.encode('utf-8') if isinstance(self.exchange, unicode) else self.exchange
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            assert isinstance(self.routing_key, basestring),\
                   'A non-bytestring value was supplied for self.routing_key'
            value = self.routing_key.encode('utf-8') if isinstance(self.routing_key, unicode) else self.routing_key
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            return pieces

    class Get(amqp_object.Method):

        INDEX = 0x003C0046  # 60, 70; 3932230
        NAME = 'Basic.Get'

        def __init__(self, ticket=0, queue='', no_ack=False):
            self.ticket = ticket
            self.queue = queue
            self.no_ack = no_ack

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            self.ticket = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.queue = encoded[offset:offset + length]
            try:
                self.queue = str(self.queue)
            except UnicodeEncodeError:
                pass
            offset += length
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.no_ack = (bit_buffer & (1 << 0)) != 0
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>H', self.ticket))
            assert isinstance(self.queue, basestring),\
                   'A non-bytestring value was supplied for self.queue'
            value = self.queue.encode('utf-8') if isinstance(self.queue, unicode) else self.queue
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            bit_buffer = 0
            if self.no_ack:
                bit_buffer = bit_buffer | (1 << 0)
            pieces.append(struct.pack('B', bit_buffer))
            return pieces

    class GetOk(amqp_object.Method):

        INDEX = 0x003C0047  # 60, 71; 3932231
        NAME = 'Basic.GetOk'

        def __init__(self, delivery_tag=None, redelivered=False, exchange=None, routing_key=None, message_count=None):
            self.delivery_tag = delivery_tag
            self.redelivered = redelivered
            self.exchange = exchange
            self.routing_key = routing_key
            self.message_count = message_count

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            self.delivery_tag = struct.unpack_from('>Q', encoded, offset)[0]
            offset += 8
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.redelivered = (bit_buffer & (1 << 0)) != 0
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.exchange = encoded[offset:offset + length]
            try:
                self.exchange = str(self.exchange)
            except UnicodeEncodeError:
                pass
            offset += length
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.routing_key = encoded[offset:offset + length]
            try:
                self.routing_key = str(self.routing_key)
            except UnicodeEncodeError:
                pass
            offset += length
            self.message_count = struct.unpack_from('>I', encoded, offset)[0]
            offset += 4
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>Q', self.delivery_tag))
            bit_buffer = 0
            if self.redelivered:
                bit_buffer = bit_buffer | (1 << 0)
            pieces.append(struct.pack('B', bit_buffer))
            assert isinstance(self.exchange, basestring),\
                   'A non-bytestring value was supplied for self.exchange'
            value = self.exchange.encode('utf-8') if isinstance(self.exchange, unicode) else self.exchange
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            assert isinstance(self.routing_key, basestring),\
                   'A non-bytestring value was supplied for self.routing_key'
            value = self.routing_key.encode('utf-8') if isinstance(self.routing_key, unicode) else self.routing_key
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            pieces.append(struct.pack('>I', self.message_count))
            return pieces

    class GetEmpty(amqp_object.Method):

        INDEX = 0x003C0048  # 60, 72; 3932232
        NAME = 'Basic.GetEmpty'

        def __init__(self, cluster_id=''):
            self.cluster_id = cluster_id

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.cluster_id = encoded[offset:offset + length]
            try:
                self.cluster_id = str(self.cluster_id)
            except UnicodeEncodeError:
                pass
            offset += length
            return self

        def encode(self):
            pieces = list()
            assert isinstance(self.cluster_id, basestring),\
                   'A non-bytestring value was supplied for self.cluster_id'
            value = self.cluster_id.encode('utf-8') if isinstance(self.cluster_id, unicode) else self.cluster_id
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
            return pieces

    class Ack(amqp_object.Method):

        INDEX = 0x003C0050  # 60, 80; 3932240
        NAME = 'Basic.Ack'

        def __init__(self, delivery_tag=0, multiple=False):
            self.delivery_tag = delivery_tag
            self.multiple = multiple

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            self.delivery_tag = struct.unpack_from('>Q', encoded, offset)[0]
            offset += 8
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.multiple = (bit_buffer & (1 << 0)) != 0
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>Q', self.delivery_tag))
            bit_buffer = 0
            if self.multiple:
                bit_buffer = bit_buffer | (1 << 0)
            pieces.append(struct.pack('B', bit_buffer))
            return pieces

    class Reject(amqp_object.Method):

        INDEX = 0x003C005A  # 60, 90; 3932250
        NAME = 'Basic.Reject'

        def __init__(self, delivery_tag=None, requeue=True):
            self.delivery_tag = delivery_tag
            self.requeue = requeue

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            self.delivery_tag = struct.unpack_from('>Q', encoded, offset)[0]
            offset += 8
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.requeue = (bit_buffer & (1 << 0)) != 0
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>Q', self.delivery_tag))
            bit_buffer = 0
            if self.requeue:
                bit_buffer = bit_buffer | (1 << 0)
            pieces.append(struct.pack('B', bit_buffer))
            return pieces

    class RecoverAsync(amqp_object.Method):

        INDEX = 0x003C0064  # 60, 100; 3932260
        NAME = 'Basic.RecoverAsync'

        def __init__(self, requeue=False):
            self.requeue = requeue

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.requeue = (bit_buffer & (1 << 0)) != 0
            return self

        def encode(self):
            pieces = list()
            bit_buffer = 0
            if self.requeue:
                bit_buffer = bit_buffer | (1 << 0)
            pieces.append(struct.pack('B', bit_buffer))
            return pieces

    class Recover(amqp_object.Method):

        INDEX = 0x003C006E  # 60, 110; 3932270
        NAME = 'Basic.Recover'

        def __init__(self, requeue=False):
            self.requeue = requeue

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.requeue = (bit_buffer & (1 << 0)) != 0
            return self

        def encode(self):
            pieces = list()
            bit_buffer = 0
            if self.requeue:
                bit_buffer = bit_buffer | (1 << 0)
            pieces.append(struct.pack('B', bit_buffer))
            return pieces

    class RecoverOk(amqp_object.Method):

        INDEX = 0x003C006F  # 60, 111; 3932271
        NAME = 'Basic.RecoverOk'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces

    class Nack(amqp_object.Method):

        INDEX = 0x003C0078  # 60, 120; 3932280
        NAME = 'Basic.Nack'

        def __init__(self, delivery_tag=0, multiple=False, requeue=True):
            self.delivery_tag = delivery_tag
            self.multiple = multiple
            self.requeue = requeue

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            self.delivery_tag = struct.unpack_from('>Q', encoded, offset)[0]
            offset += 8
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.multiple = (bit_buffer & (1 << 0)) != 0
            self.requeue = (bit_buffer & (1 << 1)) != 0
            return self

        def encode(self):
            pieces = list()
            pieces.append(struct.pack('>Q', self.delivery_tag))
            bit_buffer = 0
            if self.multiple:
                bit_buffer = bit_buffer | (1 << 0)
            if self.requeue:
                bit_buffer = bit_buffer | (1 << 1)
            pieces.append(struct.pack('B', bit_buffer))
            return pieces


class Tx(amqp_object.Class):

    INDEX = 0x005A  # 90
    NAME = 'Tx'

    class Select(amqp_object.Method):

        INDEX = 0x005A000A  # 90, 10; 5898250
        NAME = 'Tx.Select'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces

    class SelectOk(amqp_object.Method):

        INDEX = 0x005A000B  # 90, 11; 5898251
        NAME = 'Tx.SelectOk'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces

    class Commit(amqp_object.Method):

        INDEX = 0x005A0014  # 90, 20; 5898260
        NAME = 'Tx.Commit'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces

    class CommitOk(amqp_object.Method):

        INDEX = 0x005A0015  # 90, 21; 5898261
        NAME = 'Tx.CommitOk'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces

    class Rollback(amqp_object.Method):

        INDEX = 0x005A001E  # 90, 30; 5898270
        NAME = 'Tx.Rollback'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces

    class RollbackOk(amqp_object.Method):

        INDEX = 0x005A001F  # 90, 31; 5898271
        NAME = 'Tx.RollbackOk'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces


class Confirm(amqp_object.Class):

    INDEX = 0x0055  # 85
    NAME = 'Confirm'

    class Select(amqp_object.Method):

        INDEX = 0x0055000A  # 85, 10; 5570570
        NAME = 'Confirm.Select'

        def __init__(self, nowait=False):
            self.nowait = nowait

        @property
        def synchronous(self):
            return True

        def decode(self, encoded, offset=0):
            bit_buffer = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.nowait = (bit_buffer & (1 << 0)) != 0
            return self

        def encode(self):
            pieces = list()
            bit_buffer = 0
            if self.nowait:
                bit_buffer = bit_buffer | (1 << 0)
            pieces.append(struct.pack('B', bit_buffer))
            return pieces

    class SelectOk(amqp_object.Method):

        INDEX = 0x0055000B  # 85, 11; 5570571
        NAME = 'Confirm.SelectOk'

        def __init__(self):
            pass

        @property
        def synchronous(self):
            return False

        def decode(self, encoded, offset=0):
            return self

        def encode(self):
            pieces = list()
            return pieces


class BasicProperties(amqp_object.Properties):

    CLASS = Basic
    INDEX = 0x003C  # 60
    NAME = 'BasicProperties'

    FLAG_CONTENT_TYPE = (1 << 15)
    FLAG_CONTENT_ENCODING = (1 << 14)
    FLAG_HEADERS = (1 << 13)
    FLAG_DELIVERY_MODE = (1 << 12)
    FLAG_PRIORITY = (1 << 11)
    FLAG_CORRELATION_ID = (1 << 10)
    FLAG_REPLY_TO = (1 << 9)
    FLAG_EXPIRATION = (1 << 8)
    FLAG_MESSAGE_ID = (1 << 7)
    FLAG_TIMESTAMP = (1 << 6)
    FLAG_TYPE = (1 << 5)
    FLAG_USER_ID = (1 << 4)
    FLAG_APP_ID = (1 << 3)
    FLAG_CLUSTER_ID = (1 << 2)

    def __init__(self, content_type=None, content_encoding=None, headers=None, delivery_mode=None, priority=None, correlation_id=None, reply_to=None, expiration=None, message_id=None, timestamp=None, type=None, user_id=None, app_id=None, cluster_id=None):
        self.content_type = content_type
        self.content_encoding = content_encoding
        self.headers = headers
        self.delivery_mode = delivery_mode
        self.priority = priority
        self.correlation_id = correlation_id
        self.reply_to = reply_to
        self.expiration = expiration
        self.message_id = message_id
        self.timestamp = timestamp
        self.type = type
        self.user_id = user_id
        self.app_id = app_id
        self.cluster_id = cluster_id

    def decode(self, encoded, offset=0):
        flags = 0
        flagword_index = 0
        while True:
            partial_flags = struct.unpack_from('>H', encoded, offset)[0]
            offset += 2
            flags = flags | (partial_flags << (flagword_index * 16))
            if not (partial_flags & 1):
                break
            flagword_index += 1
        if flags & BasicProperties.FLAG_CONTENT_TYPE:
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.content_type = encoded[offset:offset + length]
            try:
                self.content_type = str(self.content_type)
            except UnicodeEncodeError:
                pass
            offset += length
        else:
            self.content_type = None
        if flags & BasicProperties.FLAG_CONTENT_ENCODING:
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.content_encoding = encoded[offset:offset + length]
            try:
                self.content_encoding = str(self.content_encoding)
            except UnicodeEncodeError:
                pass
            offset += length
        else:
            self.content_encoding = None
        if flags & BasicProperties.FLAG_HEADERS:
            (self.headers, offset) = data.decode_table(encoded, offset)
        else:
            self.headers = None
        if flags & BasicProperties.FLAG_DELIVERY_MODE:
            self.delivery_mode = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
        else:
            self.delivery_mode = None
        if flags & BasicProperties.FLAG_PRIORITY:
            self.priority = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
        else:
            self.priority = None
        if flags & BasicProperties.FLAG_CORRELATION_ID:
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.correlation_id = encoded[offset:offset + length]
            try:
                self.correlation_id = str(self.correlation_id)
            except UnicodeEncodeError:
                pass
            offset += length
        else:
            self.correlation_id = None
        if flags & BasicProperties.FLAG_REPLY_TO:
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.reply_to = encoded[offset:offset + length]
            try:
                self.reply_to = str(self.reply_to)
            except UnicodeEncodeError:
                pass
            offset += length
        else:
            self.reply_to = None
        if flags & BasicProperties.FLAG_EXPIRATION:
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.expiration = encoded[offset:offset + length]
            try:
                self.expiration = str(self.expiration)
            except UnicodeEncodeError:
                pass
            offset += length
        else:
            self.expiration = None
        if flags & BasicProperties.FLAG_MESSAGE_ID:
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.message_id = encoded[offset:offset + length]
            try:
                self.message_id = str(self.message_id)
            except UnicodeEncodeError:
                pass
            offset += length
        else:
            self.message_id = None
        if flags & BasicProperties.FLAG_TIMESTAMP:
            self.timestamp = struct.unpack_from('>Q', encoded, offset)[0]
            offset += 8
        else:
            self.timestamp = None
        if flags & BasicProperties.FLAG_TYPE:
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.type = encoded[offset:offset + length]
            try:
                self.type = str(self.type)
            except UnicodeEncodeError:
                pass
            offset += length
        else:
            self.type = None
        if flags & BasicProperties.FLAG_USER_ID:
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.user_id = encoded[offset:offset + length]
            try:
                self.user_id = str(self.user_id)
            except UnicodeEncodeError:
                pass
            offset += length
        else:
            self.user_id = None
        if flags & BasicProperties.FLAG_APP_ID:
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.app_id = encoded[offset:offset + length]
            try:
                self.app_id = str(self.app_id)
            except UnicodeEncodeError:
                pass
            offset += length
        else:
            self.app_id = None
        if flags & BasicProperties.FLAG_CLUSTER_ID:
            length = struct.unpack_from('B', encoded, offset)[0]
            offset += 1
            self.cluster_id = encoded[offset:offset + length]
            try:
                self.cluster_id = str(self.cluster_id)
            except UnicodeEncodeError:
                pass
            offset += length
        else:
            self.cluster_id = None
        return self

    def encode(self):
        pieces = list()
        flags = 0
        if self.content_type is not None:
            flags = flags | BasicProperties.FLAG_CONTENT_TYPE
            assert isinstance(self.content_type, basestring),\
                   'A non-bytestring value was supplied for self.content_type'
            value = self.content_type.encode('utf-8') if isinstance(self.content_type, unicode) else self.content_type
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
        if self.content_encoding is not None:
            flags = flags | BasicProperties.FLAG_CONTENT_ENCODING
            assert isinstance(self.content_encoding, basestring),\
                   'A non-bytestring value was supplied for self.content_encoding'
            value = self.content_encoding.encode('utf-8') if isinstance(self.content_encoding, unicode) else self.content_encoding
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
        if self.headers is not None:
            flags = flags | BasicProperties.FLAG_HEADERS
            data.encode_table(pieces, self.headers)
        if self.delivery_mode is not None:
            flags = flags | BasicProperties.FLAG_DELIVERY_MODE
            pieces.append(struct.pack('B', self.delivery_mode))
        if self.priority is not None:
            flags = flags | BasicProperties.FLAG_PRIORITY
            pieces.append(struct.pack('B', self.priority))
        if self.correlation_id is not None:
            flags = flags | BasicProperties.FLAG_CORRELATION_ID
            assert isinstance(self.correlation_id, basestring),\
                   'A non-bytestring value was supplied for self.correlation_id'
            value = self.correlation_id.encode('utf-8') if isinstance(self.correlation_id, unicode) else self.correlation_id
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
        if self.reply_to is not None:
            flags = flags | BasicProperties.FLAG_REPLY_TO
            assert isinstance(self.reply_to, basestring),\
                   'A non-bytestring value was supplied for self.reply_to'
            value = self.reply_to.encode('utf-8') if isinstance(self.reply_to, unicode) else self.reply_to
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
        if self.expiration is not None:
            flags = flags | BasicProperties.FLAG_EXPIRATION
            assert isinstance(self.expiration, basestring),\
                   'A non-bytestring value was supplied for self.expiration'
            value = self.expiration.encode('utf-8') if isinstance(self.expiration, unicode) else self.expiration
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
        if self.message_id is not None:
            flags = flags | BasicProperties.FLAG_MESSAGE_ID
            assert isinstance(self.message_id, basestring),\
                   'A non-bytestring value was supplied for self.message_id'
            value = self.message_id.encode('utf-8') if isinstance(self.message_id, unicode) else self.message_id
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
        if self.timestamp is not None:
            flags = flags | BasicProperties.FLAG_TIMESTAMP
            pieces.append(struct.pack('>Q', self.timestamp))
        if self.type is not None:
            flags = flags | BasicProperties.FLAG_TYPE
            assert isinstance(self.type, basestring),\
                   'A non-bytestring value was supplied for self.type'
            value = self.type.encode('utf-8') if isinstance(self.type, unicode) else self.type
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
        if self.user_id is not None:
            flags = flags | BasicProperties.FLAG_USER_ID
            assert isinstance(self.user_id, basestring),\
                   'A non-bytestring value was supplied for self.user_id'
            value = self.user_id.encode('utf-8') if isinstance(self.user_id, unicode) else self.user_id
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
        if self.app_id is not None:
            flags = flags | BasicProperties.FLAG_APP_ID
            assert isinstance(self.app_id, basestring),\
                   'A non-bytestring value was supplied for self.app_id'
            value = self.app_id.encode('utf-8') if isinstance(self.app_id, unicode) else self.app_id
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
        if self.cluster_id is not None:
            flags = flags | BasicProperties.FLAG_CLUSTER_ID
            assert isinstance(self.cluster_id, basestring),\
                   'A non-bytestring value was supplied for self.cluster_id'
            value = self.cluster_id.encode('utf-8') if isinstance(self.cluster_id, unicode) else self.cluster_id
            pieces.append(struct.pack('B', len(value)))
            pieces.append(value)
        flag_pieces = list()
        while True:
            remainder = flags >> 16
            partial_flags = flags & 0xFFFE
            if remainder != 0:
                partial_flags |= 1
            flag_pieces.append(struct.pack('>H', partial_flags))
            flags = remainder
            if not flags:
                break
        return flag_pieces + pieces

methods = {
    0x000A000A: Connection.Start,
    0x000A000B: Connection.StartOk,
    0x000A0014: Connection.Secure,
    0x000A0015: Connection.SecureOk,
    0x000A001E: Connection.Tune,
    0x000A001F: Connection.TuneOk,
    0x000A0028: Connection.Open,
    0x000A0029: Connection.OpenOk,
    0x000A0032: Connection.Close,
    0x000A0033: Connection.CloseOk,
    0x000A003C: Connection.Blocked,
    0x000A003D: Connection.Unblocked,
    0x0014000A: Channel.Open,
    0x0014000B: Channel.OpenOk,
    0x00140014: Channel.Flow,
    0x00140015: Channel.FlowOk,
    0x00140028: Channel.Close,
    0x00140029: Channel.CloseOk,
    0x001E000A: Access.Request,
    0x001E000B: Access.RequestOk,
    0x0028000A: Exchange.Declare,
    0x0028000B: Exchange.DeclareOk,
    0x00280014: Exchange.Delete,
    0x00280015: Exchange.DeleteOk,
    0x0028001E: Exchange.Bind,
    0x0028001F: Exchange.BindOk,
    0x00280028: Exchange.Unbind,
    0x00280033: Exchange.UnbindOk,
    0x0032000A: Queue.Declare,
    0x0032000B: Queue.DeclareOk,
    0x00320014: Queue.Bind,
    0x00320015: Queue.BindOk,
    0x0032001E: Queue.Purge,
    0x0032001F: Queue.PurgeOk,
    0x00320028: Queue.Delete,
    0x00320029: Queue.DeleteOk,
    0x00320032: Queue.Unbind,
    0x00320033: Queue.UnbindOk,
    0x003C000A: Basic.Qos,
    0x003C000B: Basic.QosOk,
    0x003C0014: Basic.Consume,
    0x003C0015: Basic.ConsumeOk,
    0x003C001E: Basic.Cancel,
    0x003C001F: Basic.CancelOk,
    0x003C0028: Basic.Publish,
    0x003C0032: Basic.Return,
    0x003C003C: Basic.Deliver,
    0x003C0046: Basic.Get,
    0x003C0047: Basic.GetOk,
    0x003C0048: Basic.GetEmpty,
    0x003C0050: Basic.Ack,
    0x003C005A: Basic.Reject,
    0x003C0064: Basic.RecoverAsync,
    0x003C006E: Basic.Recover,
    0x003C006F: Basic.RecoverOk,
    0x003C0078: Basic.Nack,
    0x005A000A: Tx.Select,
    0x005A000B: Tx.SelectOk,
    0x005A0014: Tx.Commit,
    0x005A0015: Tx.CommitOk,
    0x005A001E: Tx.Rollback,
    0x005A001F: Tx.RollbackOk,
    0x0055000A: Confirm.Select,
    0x0055000B: Confirm.SelectOk
}

props = {
    0x003C: BasicProperties
}


def has_content(methodNumber):

    if methodNumber == Basic.Publish.INDEX:
        return True
    if methodNumber == Basic.Return.INDEX:
        return True
    if methodNumber == Basic.Deliver.INDEX:
        return True
    if methodNumber == Basic.GetOk.INDEX:
        return True
    return False


########NEW FILE########
__FILENAME__ = utils
"""
Non-module specific functions shared by modules in the pika package

"""
import collections


def is_callable(handle):
    """Returns a bool value if the handle passed in is a callable
    method/function

    :param any handle: The object to check
    :rtype: bool

    """
    return isinstance(handle, collections.Callable)

########NEW FILE########
__FILENAME__ = asyncore_adapter_tests
import time

import async_test_base

from pika import adapters
from pika import spec


class AsyncTestCase(async_test_base.AsyncTestCase):
    ADAPTER = adapters.AsyncoreConnection


class BoundQueueTestCase(async_test_base.BoundQueueTestCase):
    ADAPTER = adapters.AsyncoreConnection


class TestA_Connect(AsyncTestCase):

    ADAPTER = adapters.AsyncoreConnection

    def begin(self, channel):
        self.stop()

    def start_test(self):
        """AsyncoreConnection should connect, open channel and disconnect"""
        self.start()


class TestConfirmSelect(AsyncTestCase):

    def begin(self, channel):
        channel._on_selectok = self.on_complete
        channel.confirm_delivery()

    def on_complete(self, frame):
        self.assertIsInstance(frame.method, spec.Confirm.SelectOk)
        self.stop()

    def start_test(self):
        """AsyncoreConnection should receive confirmation of Confirm.Select"""
        self.start()


class TestExchangeDeclareAndDelete(AsyncTestCase):

    X_TYPE = 'direct'

    def begin(self, channel):
        self.name = self.__class__.__name__ + ':' + str(id(self))
        channel.exchange_declare(self.on_exchange_declared,
                                 self.name,
                                 exchange_type=self.X_TYPE,
                                 passive=False,
                                 durable=False,
                                 auto_delete=True)

    def on_exchange_declared(self, frame):
        self.assertIsInstance(frame.method, spec.Exchange.DeclareOk)
        self.channel.exchange_delete(self.on_exchange_delete, self.name)

    def on_exchange_delete(self, frame):
        self.assertIsInstance(frame.method, spec.Exchange.DeleteOk)
        self.stop()

    def start_test(self):
        """TornadoConnection should create and delete an exchange"""
        self.start()


class TestExchangeRedeclareWithDifferentValues(AsyncTestCase):

    X_TYPE1 = 'direct'
    X_TYPE2 = 'topic'

    def begin(self, channel):
        self.name = self.__class__.__name__ + ':' + str(id(self))
        self.channel.add_on_close_callback(self.on_channel_closed)
        channel.exchange_declare(self.on_exchange_declared,
                                 self.name,
                                 exchange_type=self.X_TYPE1,
                                 passive=False,
                                 durable=False,
                                 auto_delete=True)


    def on_cleanup_channel(self, channel):
        channel.exchange_delete(None, self.name, nowait=True)
        self.stop()

    def on_channel_closed(self, channel, reply_code, reply_text):
        self.connection.channel(self.on_cleanup_channel)

    def on_exchange_declared(self, frame):
        self.channel.exchange_declare(self.on_exchange_declared,
                                      self.name,
                                      exchange_type=self.X_TYPE2,
                                      passive=False,
                                      durable=False,
                                      auto_delete=True)

    def on_bad_result(self, frame):
        self.channel.exchange_delete(None, self.name, nowait=True)
        raise AssertionError("Should not have received a Queue.DeclareOk")

    def start_test(self):
        """TornadoConnection should close chan: re-declared exchange w/ diff params

        """
        self.start()


class TestQueueDeclareAndDelete(AsyncTestCase):

    def begin(self, channel):
        channel.queue_declare(self.on_queue_declared,
                              passive=False,
                              durable=False,
                              exclusive=True,
                              auto_delete=False,
                              nowait=False,
                              arguments={'x-expires': self.TIMEOUT})

    def on_queue_declared(self, frame):
        self.assertIsInstance(frame.method, spec.Queue.DeclareOk)
        self.channel.queue_delete(self.on_queue_delete, frame.method.queue)

    def on_queue_delete(self, frame):
        self.assertIsInstance(frame.method, spec.Queue.DeleteOk)
        self.stop()

    def start_test(self):
        """AsyncoreConnection should create and delete a queue"""
        self.start()


class TestQueueNameDeclareAndDelete(AsyncTestCase):

    def begin(self, channel):
        channel.queue_declare(self.on_queue_declared, str(id(self)),
                              passive=False,
                              durable=False,
                              exclusive=True,
                              auto_delete=True,
                              nowait=False,
                              arguments={'x-expires': self.TIMEOUT})

    def on_queue_declared(self, frame):
        self.assertIsInstance(frame.method, spec.Queue.DeclareOk)
        self.assertEqual(frame.method.queue, str(id(self)))
        self.channel.queue_delete(self.on_queue_delete, frame.method.queue)

    def on_queue_delete(self, frame):
        self.assertIsInstance(frame.method, spec.Queue.DeleteOk)
        self.stop()

    def start_test(self):
        """AsyncoreConnection should create and delete a named queue"""
        self.start()


class TestQueueRedeclareWithDifferentValues(AsyncTestCase):

    def begin(self, channel):
        self.channel.add_on_close_callback(self.on_channel_closed)
        channel.queue_declare(self.on_queue_declared,
                              str(id(self)),
                              passive=False,
                              durable=False,
                              exclusive=True,
                              auto_delete=True,
                              nowait=False,
                              arguments={'x-expires': self.TIMEOUT})

    def on_channel_closed(self, channel, reply_code, reply_text):
        self.stop()

    def on_queue_declared(self, frame):
        self.channel.queue_declare(self.on_bad_result,
                                   str(id(self)),
                                   passive=False,
                                   durable=True,
                                   exclusive=False,
                                   auto_delete=True,
                                   nowait=False,
                                   arguments={'x-expires': self.TIMEOUT})

    def on_bad_result(self, frame):
        self.channel.queue_delete(None, str(id(self)), nowait=True)
        raise AssertionError("Should not have received a Queue.DeclareOk")

    def start_test(self):
        """AsyncoreConnection should close chan: re-declared queue w/ diff params

        """
        self.start()


class TestTX1_Select(AsyncTestCase):

    def begin(self, channel):
        channel.tx_select(self.on_complete)

    def on_complete(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.SelectOk)
        self.stop()

    def test_confirm_select(self):
        """AsyncoreConnection should receive confirmation of Tx.Select"""
        self.start()


class TestTX2_Commit(AsyncTestCase):

    def begin(self, channel):
        channel.tx_select(self.on_selectok)

    def on_selectok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.SelectOk)
        self.channel.tx_commit(self.on_commitok)

    def on_commitok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.CommitOk)
        self.stop()

    def start_test(self):
        """AsyncoreConnection should start a transaction, then commit it back"""
        self.start()


class TestTX2_CommitFailure(AsyncTestCase):

    def begin(self, channel):
        self.channel.add_on_close_callback(self.on_channel_closed)
        self.channel.tx_commit(self.on_commitok)

    def on_channel_closed(self, channel, reply_code, reply_text):
        self.stop()

    def on_selectok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.SelectOk)

    def on_commitok(self, frame):
        raise AssertionError("Should not have received a Tx.CommitOk")

    def start_test(self):
        """AsyncoreConnection should close the channel: commit without a TX"""
        self.start()


class TestTX3_Rollback(AsyncTestCase):

    def begin(self, channel):
        channel.tx_select(self.on_selectok)

    def on_selectok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.SelectOk)
        self.channel.tx_rollback(self.on_rollbackok)

    def on_rollbackok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.RollbackOk)
        self.stop()

    def start_test(self):
        """AsyncoreConnection should start a transaction, then roll it back"""
        self.start()


class TestTX3_RollbackFailure(AsyncTestCase):

    def begin(self, channel):
        self.channel.add_on_close_callback(self.on_channel_closed)
        self.channel.tx_rollback(self.on_commitok)

    def on_channel_closed(self, channel, reply_code, reply_text):
        self.stop()

    def on_commitok(self, frame):
        raise AssertionError("Should not have received a Tx.RollbackOk")

    def start_test(self):
        """AsyncoreConnection should close the channel: rollback without a TX"""
        self.start()


class TestZ_PublishAndConsume(BoundQueueTestCase):

    def on_ready(self, frame):
        self.ctag = self.channel.basic_consume(self.on_message, self.queue)
        self.msg_body = "%s: %i" % (self.__class__.__name__, time.time())
        self.channel.basic_publish(self.exchange,
                                   self.routing_key,
                                   self.msg_body)

    def on_cancelled(self, frame):
        self.assertIsInstance(frame.method, spec.Basic.CancelOk)
        self.stop()

    def on_message(self, channel, method, header, body):
        self.assertIsInstance(method, spec.Basic.Deliver)
        self.assertEqual(body, self.msg_body)
        self.channel.basic_ack(method.delivery_tag)
        self.channel.basic_cancel(self.on_cancelled, self.ctag)

    def start_test(self):
        """AsyncoreConnection should publish a message and consume it"""
        self.start()


class TestZ_PublishAndConsumeBig(BoundQueueTestCase):

    def _get_msg_body(self):
        return '\n'.join(["%s" % i for i in range(0, 2097152)])

    def on_ready(self, frame):
        self.ctag = self.channel.basic_consume(self.on_message, self.queue)
        self.msg_body = self._get_msg_body()
        self.channel.basic_publish(self.exchange,
                                   self.routing_key,
                                   self.msg_body)

    def on_cancelled(self, frame):
        self.assertIsInstance(frame.method, spec.Basic.CancelOk)
        self.stop()

    def on_message(self, channel, method, header, body):
        self.assertIsInstance(method, spec.Basic.Deliver)
        self.assertEqual(body, self.msg_body)
        self.channel.basic_ack(method.delivery_tag)
        self.channel.basic_cancel(self.on_cancelled, self.ctag)

    def start_test(self):
        """AsyncoreConnection should publish a big message and consume it"""
        self.start()



class TestZ_PublishAndGet(BoundQueueTestCase):

    def on_ready(self, frame):
        self.msg_body = "%s: %i" % (self.__class__.__name__, time.time())
        self.channel.basic_publish(self.exchange,
                                   self.routing_key,
                                   self.msg_body)
        self.channel.basic_get(self.on_get, self.queue)

    def on_get(self, channel, method, header, body):
        self.assertIsInstance(method, spec.Basic.GetOk)
        self.assertEqual(body, self.msg_body)
        self.channel.basic_ack(method.delivery_tag)
        self.stop()

    def start_test(self):
        """AsyncoreConnection should publish a message and get it"""
        self.start()


########NEW FILE########
__FILENAME__ = async_test_base
import logging
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import pika

LOGGER = logging.getLogger(__name__)
PARAMETERS = pika.URLParameters('amqp://guest:guest@localhost:5672/%2f')
DEFAULT_TIMEOUT = 30


class AsyncTestCase(unittest.TestCase):

    ADAPTER = None
    TIMEOUT = DEFAULT_TIMEOUT

    def begin(self, channel):
        """Extend to start the actual tests on the channel"""
        raise AssertionError("AsyncTestCase.begin_test not extended")

    def start(self):
        self.connection = self.ADAPTER(PARAMETERS,
                                       self.on_open,
                                       self.on_open_error,
                                       self.on_closed)
        self.timeout = self.connection.add_timeout(self.TIMEOUT,
                                                   self.on_timeout)
        self.connection.ioloop.start()

    def stop(self):
        """close the connection and stop the ioloop"""
        LOGGER.info("Stopping test")
        self.connection.remove_timeout(self.timeout)
        self.timeout = None
        self.connection.close()

    def _stop(self):
        if hasattr(self, 'timeout') and self.timeout:
            self.connection.remove_timeout(self.timeout)
            self.timeout = None
        if hasattr(self, 'connection') and self.connection:
            self.connection.ioloop.stop()
            self.connection = None

    def tearDown(self):
        self._stop()

    def on_closed(self, connection, reply_code, reply_text):
        """called when the connection has finished closing"""
        LOGGER.debug("Connection Closed")
        self._stop()

    def on_open(self, connection):
        self.channel = connection.channel(self.begin)

    def on_open_error(self, connection):
        connection.ioloop.stop()
        raise AssertionError('Error connecting to RabbitMQ')

    def on_timeout(self):
        """called when stuck waiting for connection to close"""
        # force the ioloop to stop
        self.connection.ioloop.stop()
        raise AssertionError('Test timed out')


class BoundQueueTestCase(AsyncTestCase):

    def tearDown(self):
        """Cleanup auto-declared queue and exchange"""
        self._cconn = self.ADAPTER(PARAMETERS,
                                   self._on_cconn_open,
                                   self._on_cconn_error,
                                   self._on_cconn_closed)

    def start(self):
        self.exchange = 'e' + str(id(self))
        self.queue = 'q' + str(id(self))
        self.routing_key = self.__class__.__name__
        super(BoundQueueTestCase, self).start()

    def begin(self, channel):
        self.channel.exchange_declare(self.on_exchange_declared,
                                      self.exchange,
                                      exchange_type='direct',
                                      passive=False,
                                      durable=False,
                                      auto_delete=True)

    def on_exchange_declared(self, frame):
        self.channel.queue_declare(self.on_queue_declared,
                                   self.queue,
                                   passive=False,
                                   durable=False,
                                   exclusive=True,
                                   auto_delete=True,
                                   nowait=False,
                                   arguments={'x-expires': self.TIMEOUT})

    def on_queue_declared(self, frame):
        self.channel.queue_bind(self.on_ready,
                                self.queue,
                                self.exchange,
                                self.routing_key)

    def on_ready(self, frame):
        raise NotImplementedError

    def _on_cconn_closed(self, cconn, *args, **kwargs):
        cconn.ioloop.stop()
        self._cconn = None

    def _on_cconn_error(self, connection):
        connection.ioloop.stop()
        raise AssertionError('Error connecting to RabbitMQ')

    def _on_cconn_open(self, connection):
        connection.channel(self._on_cconn_channel)

    def _on_cconn_channel(self, channel):
        channel.exchange_delete(None, self.exchange, nowait=True)
        channel.queue_delete(None, self.queue, nowait=True)
        self._cconn.close()

########NEW FILE########
__FILENAME__ = libev_adapter_tests

import platform
import time
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import async_test_base

from pika import adapters
from pika import spec

target = platform.python_implementation()


class AsyncTestCase(async_test_base.AsyncTestCase):
    ADAPTER = adapters.LibevConnection


class BoundQueueTestCase(async_test_base.BoundQueueTestCase):
    ADAPTER = adapters.LibevConnection




class TestConfirmSelect(AsyncTestCase):

    def begin(self, channel):
        channel._on_selectok = self.on_complete
        channel.confirm_delivery()

    def on_complete(self, frame):
        self.assertIsInstance(frame.method, spec.Confirm.SelectOk)
        self.stop()


    @unittest.skipIf(target == 'PyPy', 'PyPy is not supported')
    @unittest.skipIf(adapters.LibevConnection is None, 'pyev is not installed')
    def start_test(self):
        """LibevConnection should receive confirmation of Confirm.Select"""
        self.start()


class TestExchangeDeclareAndDelete(AsyncTestCase):

    X_TYPE = 'direct'

    def begin(self, channel):
        self.name = self.__class__.__name__ + ':' + str(id(self))
        channel.exchange_declare(self.on_exchange_declared,
                                 self.name,
                                 exchange_type=self.X_TYPE,
                                 passive=False,
                                 durable=False,
                                 auto_delete=True)

    def on_exchange_declared(self, frame):
        self.assertIsInstance(frame.method, spec.Exchange.DeclareOk)
        self.channel.exchange_delete(self.on_exchange_delete, self.name)

    def on_exchange_delete(self, frame):
        self.assertIsInstance(frame.method, spec.Exchange.DeleteOk)
        self.stop()

    @unittest.skipIf(target == 'PyPy', 'PyPy is not supported')
    @unittest.skipIf(adapters.LibevConnection is None, 'pyev is not installed')
    def start_test(self):
        """LibevConnection should create and delete an exchange"""
        self.start()


class TestExchangeRedeclareWithDifferentValues(AsyncTestCase):

    X_TYPE1 = 'direct'
    X_TYPE2 = 'topic'

    def begin(self, channel):
        self.name = self.__class__.__name__ + ':' + str(id(self))
        self.channel.add_on_close_callback(self.on_channel_closed)
        channel.exchange_declare(self.on_exchange_declared,
                                 self.name,
                                 exchange_type=self.X_TYPE1,
                                 passive=False,
                                 durable=False,
                                 auto_delete=True)


    def on_cleanup_channel(self, channel):
        channel.exchange_delete(None, self.name, nowait=True)
        self.stop()

    def on_channel_closed(self, channel, reply_code, reply_text):
        self.connection.channel(self.on_cleanup_channel)

    def on_exchange_declared(self, frame):
        self.channel.exchange_declare(self.on_exchange_declared,
                                      self.name,
                                      exchange_type=self.X_TYPE2,
                                      passive=False,
                                      durable=False,
                                      auto_delete=True)

    def on_bad_result(self, frame):
        self.channel.exchange_delete(None, self.name, nowait=True)
        raise AssertionError("Should not have received a Queue.DeclareOk")

    @unittest.skipIf(target == 'PyPy', 'PyPy is not supported')
    @unittest.skipIf(adapters.LibevConnection is None, 'pyev is not installed')
    def start_test(self):
        """LibevConnection should close chan: re-declared exchange w/ diff params

        """
        self.start()


class TestQueueDeclareAndDelete(AsyncTestCase):

    def begin(self, channel):
        channel.queue_declare(self.on_queue_declared,
                              passive=False,
                              durable=False,
                              exclusive=True,
                              auto_delete=False,
                              nowait=False,
                              arguments={'x-expires': self.TIMEOUT})

    def on_queue_declared(self, frame):
        self.assertIsInstance(frame.method, spec.Queue.DeclareOk)
        self.channel.queue_delete(self.on_queue_delete, frame.method.queue)

    def on_queue_delete(self, frame):
        self.assertIsInstance(frame.method, spec.Queue.DeleteOk)
        self.stop()

    @unittest.skipIf(target == 'PyPy', 'PyPy is not supported')
    @unittest.skipIf(adapters.LibevConnection is None, 'pyev is not installed')
    def start_test(self):
        """LibevConnection should create and delete a queue"""
        self.start()


class TestQueueNameDeclareAndDelete(AsyncTestCase):

    def begin(self, channel):
        channel.queue_declare(self.on_queue_declared, str(id(self)),
                              passive=False,
                              durable=False,
                              exclusive=True,
                              auto_delete=True,
                              nowait=False,
                              arguments={'x-expires': self.TIMEOUT})

    def on_queue_declared(self, frame):
        self.assertIsInstance(frame.method, spec.Queue.DeclareOk)
        self.assertEqual(frame.method.queue, str(id(self)))
        self.channel.queue_delete(self.on_queue_delete, frame.method.queue)

    def on_queue_delete(self, frame):
        self.assertIsInstance(frame.method, spec.Queue.DeleteOk)
        self.stop()

    @unittest.skipIf(target == 'PyPy', 'PyPy is not supported')
    @unittest.skipIf(adapters.LibevConnection is None, 'pyev is not installed')
    def start_test(self):
        """LibevConnection should create and delete a named queue"""
        self.start()


class TestQueueRedeclareWithDifferentValues(AsyncTestCase):

    def begin(self, channel):
        self.channel.add_on_close_callback(self.on_channel_closed)
        channel.queue_declare(self.on_queue_declared,
                              str(id(self)),
                              passive=False,
                              durable=False,
                              exclusive=True,
                              auto_delete=True,
                              nowait=False,
                              arguments={'x-expires': self.TIMEOUT})

    def on_channel_closed(self, channel, reply_code, reply_text):
        self.stop()

    def on_queue_declared(self, frame):
        self.channel.queue_declare(self.on_bad_result,
                                   str(id(self)),
                                   passive=False,
                                   durable=True,
                                   exclusive=False,
                                   auto_delete=True,
                                   nowait=False,
                                   arguments={'x-expires': self.TIMEOUT})

    def on_bad_result(self, frame):
        self.channel.queue_delete(None, str(id(self)), nowait=True)
        raise AssertionError("Should not have received a Queue.DeclareOk")

    @unittest.skipIf(target == 'PyPy', 'PyPy is not supported')
    @unittest.skipIf(adapters.LibevConnection is None, 'pyev is not installed')
    def start_test(self):
        """LibevConnection should close chan: re-declared queue w/ diff params

        """
        self.start()


class TestTX1_Select(AsyncTestCase):

    def begin(self, channel):
        channel.tx_select(self.on_complete)

    def on_complete(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.SelectOk)
        self.stop()

    @unittest.skipIf(target == 'PyPy', 'PyPy is not supported')
    @unittest.skipIf(adapters.LibevConnection is None, 'pyev is not installed')
    def test_confirm_select(self):
        """LibevConnection should receive confirmation of Tx.Select"""
        self.start()


class TestTX2_Commit(AsyncTestCase):

    def begin(self, channel):
        channel.tx_select(self.on_selectok)

    def on_selectok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.SelectOk)
        self.channel.tx_commit(self.on_commitok)

    def on_commitok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.CommitOk)
        self.stop()

    @unittest.skipIf(target == 'PyPy', 'PyPy is not supported')
    @unittest.skipIf(adapters.LibevConnection is None, 'pyev is not installed')
    def start_test(self):
        """LibevConnection should start a transaction, then commit it back"""
        self.start()


class TestTX2_CommitFailure(AsyncTestCase):

    def begin(self, channel):
        self.channel.add_on_close_callback(self.on_channel_closed)
        self.channel.tx_commit(self.on_commitok)

    def on_channel_closed(self, channel, reply_code, reply_text):
        self.stop()

    def on_selectok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.SelectOk)

    def on_commitok(self, frame):
        raise AssertionError("Should not have received a Tx.CommitOk")

    @unittest.skipIf(target == 'PyPy', 'PyPy is not supported')
    @unittest.skipIf(adapters.LibevConnection is None, 'pyev is not installed')
    def start_test(self):
        """LibevConnection should close the channel: commit without a TX"""
        self.start()


class TestTX3_Rollback(AsyncTestCase):

    def begin(self, channel):
        channel.tx_select(self.on_selectok)

    def on_selectok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.SelectOk)
        self.channel.tx_rollback(self.on_rollbackok)

    def on_rollbackok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.RollbackOk)
        self.stop()

    @unittest.skipIf(target == 'PyPy', 'PyPy is not supported')
    @unittest.skipIf(adapters.LibevConnection is None, 'pyev is not installed')
    def start_test(self):
        """LibevConnection should start a transaction, then roll it back"""
        self.start()


class TestTX3_RollbackFailure(AsyncTestCase):

    def begin(self, channel):
        self.channel.add_on_close_callback(self.on_channel_closed)
        self.channel.tx_rollback(self.on_commitok)

    def on_channel_closed(self, channel, reply_code, reply_text):
        self.stop()

    def on_commitok(self, frame):
        raise AssertionError("Should not have received a Tx.RollbackOk")

    @unittest.skipIf(target == 'PyPy', 'PyPy is not supported')
    @unittest.skipIf(adapters.LibevConnection is None, 'pyev is not installed')
    def start_test(self):
        """LibevConnection should close the channel: rollback without a TX"""
        self.start()


class TestZ_PublishAndConsume(BoundQueueTestCase):

    def on_ready(self, frame):
        self.ctag = self.channel.basic_consume(self.on_message, self.queue)
        self.msg_body = "%s: %i" % (self.__class__.__name__, time.time())
        self.channel.basic_publish(self.exchange,
                                   self.routing_key,
                                   self.msg_body)

    def on_cancelled(self, frame):
        self.assertIsInstance(frame.method, spec.Basic.CancelOk)
        self.stop()

    def on_message(self, channel, method, header, body):
        self.assertIsInstance(method, spec.Basic.Deliver)
        self.assertEqual(body, self.msg_body)
        self.channel.basic_ack(method.delivery_tag)
        self.channel.basic_cancel(self.on_cancelled, self.ctag)

    @unittest.skipIf(target == 'PyPy', 'PyPy is not supported')
    @unittest.skipIf(adapters.LibevConnection is None, 'pyev is not installed')
    def start_test(self):
        """LibevConnection should publish a message and consume it"""
        self.start()


class TestZ_PublishAndConsumeBig(BoundQueueTestCase):

    def _get_msg_body(self):
        return '\n'.join(["%s" % i for i in range(0, 2097152)])

    def on_ready(self, frame):
        self.ctag = self.channel.basic_consume(self.on_message, self.queue)
        self.msg_body = self._get_msg_body()
        self.channel.basic_publish(self.exchange,
                                   self.routing_key,
                                   self.msg_body)

    def on_cancelled(self, frame):
        self.assertIsInstance(frame.method, spec.Basic.CancelOk)
        self.stop()

    def on_message(self, channel, method, header, body):
        self.assertIsInstance(method, spec.Basic.Deliver)
        self.assertEqual(body, self.msg_body)
        self.channel.basic_ack(method.delivery_tag)
        self.channel.basic_cancel(self.on_cancelled, self.ctag)

    @unittest.skipIf(target == 'PyPy', 'PyPy is not supported')
    @unittest.skipIf(adapters.LibevConnection is None, 'pyev is not installed')
    def start_test(self):
        """LibevConnection should publish a big message and consume it"""
        self.start()



class TestZ_PublishAndGet(BoundQueueTestCase):

    def on_ready(self, frame):
        self.msg_body = "%s: %i" % (self.__class__.__name__, time.time())
        self.channel.basic_publish(self.exchange,
                                   self.routing_key,
                                   self.msg_body)
        self.channel.basic_get(self.on_get, self.queue)

    def on_get(self, channel, method, header, body):
        self.assertIsInstance(method, spec.Basic.GetOk)
        self.assertEqual(body, self.msg_body)
        self.channel.basic_ack(method.delivery_tag)
        self.stop()

    @unittest.skipIf(target == 'PyPy', 'PyPy is not supported')
    @unittest.skipIf(adapters.LibevConnection is None, 'pyev is not installed')
    def start_test(self):
        """LibevConnection should publish a message and get it"""
        self.start()


########NEW FILE########
__FILENAME__ = select_adapter_tests
import time

import async_test_base

from pika import adapters
from pika import spec


class AsyncTestCase(async_test_base.AsyncTestCase):
    ADAPTER = adapters.SelectConnection


class BoundQueueTestCase(async_test_base.BoundQueueTestCase):
    ADAPTER = adapters.SelectConnection


class TestA_Connect(AsyncTestCase):

    ADAPTER = adapters.SelectConnection

    def begin(self, channel):
        self.stop()

    def start_test(self):
        """SelectConnection should connect, open channel and disconnect"""
        self.start()


class TestConfirmSelect(AsyncTestCase):

    def begin(self, channel):
        channel._on_selectok = self.on_complete
        channel.confirm_delivery()

    def on_complete(self, frame):
        self.assertIsInstance(frame.method, spec.Confirm.SelectOk)
        self.stop()

    def start_test(self):
        """SelectConnection should receive confirmation of Confirm.Select"""
        self.start()


class TestExchangeDeclareAndDelete(AsyncTestCase):

    X_TYPE = 'direct'

    def begin(self, channel):
        self.name = self.__class__.__name__ + ':' + str(id(self))
        channel.exchange_declare(self.on_exchange_declared,
                                 self.name,
                                 exchange_type=self.X_TYPE,
                                 passive=False,
                                 durable=False,
                                 auto_delete=True)

    def on_exchange_declared(self, frame):
        self.assertIsInstance(frame.method, spec.Exchange.DeclareOk)
        self.channel.exchange_delete(self.on_exchange_delete, self.name)

    def on_exchange_delete(self, frame):
        self.assertIsInstance(frame.method, spec.Exchange.DeleteOk)
        self.stop()

    def start_test(self):
        """TornadoConnection should create and delete an exchange"""
        self.start()


class TestExchangeRedeclareWithDifferentValues(AsyncTestCase):

    X_TYPE1 = 'direct'
    X_TYPE2 = 'topic'

    def begin(self, channel):
        self.name = self.__class__.__name__ + ':' + str(id(self))
        self.channel.add_on_close_callback(self.on_channel_closed)
        channel.exchange_declare(self.on_exchange_declared,
                                 self.name,
                                 exchange_type=self.X_TYPE1,
                                 passive=False,
                                 durable=False,
                                 auto_delete=True)


    def on_cleanup_channel(self, channel):
        channel.exchange_delete(None, self.name, nowait=True)
        self.stop()

    def on_channel_closed(self, channel, reply_code, reply_text):
        self.connection.channel(self.on_cleanup_channel)

    def on_exchange_declared(self, frame):
        self.channel.exchange_declare(self.on_exchange_declared,
                                      self.name,
                                      exchange_type=self.X_TYPE2,
                                      passive=False,
                                      durable=False,
                                      auto_delete=True)

    def on_bad_result(self, frame):
        self.channel.exchange_delete(None, self.name, nowait=True)
        raise AssertionError("Should not have received a Queue.DeclareOk")

    def start_test(self):
        """TornadoConnection should close chan: re-declared exchange w/ diff params

        """
        self.start()


class TestQueueDeclareAndDelete(AsyncTestCase):

    def begin(self, channel):
        channel.queue_declare(self.on_queue_declared,
                              passive=False,
                              durable=False,
                              exclusive=True,
                              auto_delete=False,
                              nowait=False,
                              arguments={'x-expires': self.TIMEOUT})

    def on_queue_declared(self, frame):
        self.assertIsInstance(frame.method, spec.Queue.DeclareOk)
        self.channel.queue_delete(self.on_queue_delete, frame.method.queue)

    def on_queue_delete(self, frame):
        self.assertIsInstance(frame.method, spec.Queue.DeleteOk)
        self.stop()

    def start_test(self):
        """SelectConnection should create and delete a queue"""
        self.start()


class TestQueueNameDeclareAndDelete(AsyncTestCase):

    def begin(self, channel):
        channel.queue_declare(self.on_queue_declared, str(id(self)),
                              passive=False,
                              durable=False,
                              exclusive=True,
                              auto_delete=True,
                              nowait=False,
                              arguments={'x-expires': self.TIMEOUT})

    def on_queue_declared(self, frame):
        self.assertIsInstance(frame.method, spec.Queue.DeclareOk)
        self.assertEqual(frame.method.queue, str(id(self)))
        self.channel.queue_delete(self.on_queue_delete, frame.method.queue)

    def on_queue_delete(self, frame):
        self.assertIsInstance(frame.method, spec.Queue.DeleteOk)
        self.stop()

    def start_test(self):
        """SelectConnection should create and delete a named queue"""
        self.start()


class TestQueueRedeclareWithDifferentValues(AsyncTestCase):

    def begin(self, channel):
        self.channel.add_on_close_callback(self.on_channel_closed)
        channel.queue_declare(self.on_queue_declared,
                              str(id(self)),
                              passive=False,
                              durable=False,
                              exclusive=True,
                              auto_delete=True,
                              nowait=False,
                              arguments={'x-expires': self.TIMEOUT})

    def on_channel_closed(self, channel, reply_code, reply_text):
        self.stop()

    def on_queue_declared(self, frame):
        self.channel.queue_declare(self.on_bad_result,
                                   str(id(self)),
                                   passive=False,
                                   durable=True,
                                   exclusive=False,
                                   auto_delete=True,
                                   nowait=False,
                                   arguments={'x-expires': self.TIMEOUT})

    def on_bad_result(self, frame):
        self.channel.queue_delete(None, str(id(self)), nowait=True)
        raise AssertionError("Should not have received a Queue.DeclareOk")

    def start_test(self):
        """SelectConnection should close chan: re-declared queue w/ diff params

        """
        self.start()


class TestTX1_Select(AsyncTestCase):

    def begin(self, channel):
        channel.tx_select(self.on_complete)

    def on_complete(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.SelectOk)
        self.stop()

    def test_confirm_select(self):
        """SelectConnection should receive confirmation of Tx.Select"""
        self.start()


class TestTX2_Commit(AsyncTestCase):

    def begin(self, channel):
        channel.tx_select(self.on_selectok)

    def on_selectok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.SelectOk)
        self.channel.tx_commit(self.on_commitok)

    def on_commitok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.CommitOk)
        self.stop()

    def start_test(self):
        """SelectConnection should start a transaction, then commit it back"""
        self.start()


class TestTX2_CommitFailure(AsyncTestCase):

    def begin(self, channel):
        self.channel.add_on_close_callback(self.on_channel_closed)
        self.channel.tx_commit(self.on_commitok)

    def on_channel_closed(self, channel, reply_code, reply_text):
        self.stop()

    def on_selectok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.SelectOk)

    def on_commitok(self, frame):
        raise AssertionError("Should not have received a Tx.CommitOk")

    def start_test(self):
        """SelectConnection should close the channel: commit without a TX"""
        self.start()


class TestTX3_Rollback(AsyncTestCase):

    def begin(self, channel):
        channel.tx_select(self.on_selectok)

    def on_selectok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.SelectOk)
        self.channel.tx_rollback(self.on_rollbackok)

    def on_rollbackok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.RollbackOk)
        self.stop()

    def start_test(self):
        """SelectConnection should start a transaction, then roll it back"""
        self.start()


class TestTX3_RollbackFailure(AsyncTestCase):

    def begin(self, channel):
        self.channel.add_on_close_callback(self.on_channel_closed)
        self.channel.tx_rollback(self.on_commitok)

    def on_channel_closed(self, channel, reply_code, reply_text):
        self.stop()

    def on_commitok(self, frame):
        raise AssertionError("Should not have received a Tx.RollbackOk")

    def start_test(self):
        """SelectConnection should close the channel: rollback without a TX"""
        self.start()


class TestZ_PublishAndConsume(BoundQueueTestCase):

    def on_ready(self, frame):
        self.ctag = self.channel.basic_consume(self.on_message, self.queue)
        self.msg_body = "%s: %i" % (self.__class__.__name__, time.time())
        self.channel.basic_publish(self.exchange,
                                   self.routing_key,
                                   self.msg_body)

    def on_cancelled(self, frame):
        self.assertIsInstance(frame.method, spec.Basic.CancelOk)
        self.stop()

    def on_message(self, channel, method, header, body):
        self.assertIsInstance(method, spec.Basic.Deliver)
        self.assertEqual(body, self.msg_body)
        self.channel.basic_ack(method.delivery_tag)
        self.channel.basic_cancel(self.on_cancelled, self.ctag)

    def start_test(self):
        """SelectConnection should publish a message and consume it"""
        self.start()


class TestZ_PublishAndConsumeBig(BoundQueueTestCase):

    def _get_msg_body(self):
        return '\n'.join(["%s" % i for i in range(0, 2097152)])

    def on_ready(self, frame):
        self.ctag = self.channel.basic_consume(self.on_message, self.queue)
        self.msg_body = self._get_msg_body()
        self.channel.basic_publish(self.exchange,
                                   self.routing_key,
                                   self.msg_body)

    def on_cancelled(self, frame):
        self.assertIsInstance(frame.method, spec.Basic.CancelOk)
        self.stop()

    def on_message(self, channel, method, header, body):
        self.assertIsInstance(method, spec.Basic.Deliver)
        self.assertEqual(body, self.msg_body)
        self.channel.basic_ack(method.delivery_tag)
        self.channel.basic_cancel(self.on_cancelled, self.ctag)

    def start_test(self):
        """SelectConnection should publish a big message and consume it"""
        self.start()



class TestZ_PublishAndGet(BoundQueueTestCase):

    def on_ready(self, frame):
        self.msg_body = "%s: %i" % (self.__class__.__name__, time.time())
        self.channel.basic_publish(self.exchange,
                                   self.routing_key,
                                   self.msg_body)
        self.channel.basic_get(self.on_get, self.queue)

    def on_get(self, channel, method, header, body):
        self.assertIsInstance(method, spec.Basic.GetOk)
        self.assertEqual(body, self.msg_body)
        self.channel.basic_ack(method.delivery_tag)
        self.stop()

    def start_test(self):
        """SelectConnection should publish a message and get it"""
        self.start()


########NEW FILE########
__FILENAME__ = tornado_adapter_tests
import time

import async_test_base

from pika import adapters
from pika import spec


class AsyncTestCase(async_test_base.AsyncTestCase):
    ADAPTER = adapters.TornadoConnection


class BoundQueueTestCase(async_test_base.BoundQueueTestCase):
    ADAPTER = adapters.TornadoConnection




class TestConfirmSelect(AsyncTestCase):

    def begin(self, channel):
        channel._on_selectok = self.on_complete
        channel.confirm_delivery()

    def on_complete(self, frame):
        self.assertIsInstance(frame.method, spec.Confirm.SelectOk)
        self.stop()

    def start_test(self):
        """TornadoConnection should receive confirmation of Confirm.Select"""
        self.start()


class TestExchangeDeclareAndDelete(AsyncTestCase):

    X_TYPE = 'direct'

    def begin(self, channel):
        self.name = self.__class__.__name__ + ':' + str(id(self))
        channel.exchange_declare(self.on_exchange_declared,
                                 self.name,
                                 exchange_type=self.X_TYPE,
                                 passive=False,
                                 durable=False,
                                 auto_delete=True)

    def on_exchange_declared(self, frame):
        self.assertIsInstance(frame.method, spec.Exchange.DeclareOk)
        self.channel.exchange_delete(self.on_exchange_delete, self.name)

    def on_exchange_delete(self, frame):
        self.assertIsInstance(frame.method, spec.Exchange.DeleteOk)
        self.stop()

    def start_test(self):
        """TornadoConnection should create and delete an exchange"""
        self.start()


class TestExchangeRedeclareWithDifferentValues(AsyncTestCase):

    X_TYPE1 = 'direct'
    X_TYPE2 = 'topic'

    def begin(self, channel):
        self.name = self.__class__.__name__ + ':' + str(id(self))
        self.channel.add_on_close_callback(self.on_channel_closed)
        channel.exchange_declare(self.on_exchange_declared,
                                 self.name,
                                 exchange_type=self.X_TYPE1,
                                 passive=False,
                                 durable=False,
                                 auto_delete=True)


    def on_cleanup_channel(self, channel):
        channel.exchange_delete(None, self.name, nowait=True)
        self.stop()

    def on_channel_closed(self, channel, reply_code, reply_text):
        self.connection.channel(self.on_cleanup_channel)

    def on_exchange_declared(self, frame):
        self.channel.exchange_declare(self.on_exchange_declared,
                                      self.name,
                                      exchange_type=self.X_TYPE2,
                                      passive=False,
                                      durable=False,
                                      auto_delete=True)

    def on_bad_result(self, frame):
        self.channel.exchange_delete(None, self.name, nowait=True)
        raise AssertionError("Should not have received a Queue.DeclareOk")

    def start_test(self):
        """TornadoConnection should close chan: re-declared exchange w/ diff params

        """
        self.start()


class TestQueueDeclareAndDelete(AsyncTestCase):

    def begin(self, channel):
        channel.queue_declare(self.on_queue_declared,
                              passive=False,
                              durable=False,
                              exclusive=True,
                              auto_delete=False,
                              nowait=False,
                              arguments={'x-expires': self.TIMEOUT})

    def on_queue_declared(self, frame):
        self.assertIsInstance(frame.method, spec.Queue.DeclareOk)
        self.channel.queue_delete(self.on_queue_delete, frame.method.queue)

    def on_queue_delete(self, frame):
        self.assertIsInstance(frame.method, spec.Queue.DeleteOk)
        self.stop()

    def start_test(self):
        """TornadoConnection should create and delete a queue"""
        self.start()


class TestQueueNameDeclareAndDelete(AsyncTestCase):

    def begin(self, channel):
        channel.queue_declare(self.on_queue_declared, str(id(self)),
                              passive=False,
                              durable=False,
                              exclusive=True,
                              auto_delete=True,
                              nowait=False,
                              arguments={'x-expires': self.TIMEOUT})

    def on_queue_declared(self, frame):
        self.assertIsInstance(frame.method, spec.Queue.DeclareOk)
        self.assertEqual(frame.method.queue, str(id(self)))
        self.channel.queue_delete(self.on_queue_delete, frame.method.queue)

    def on_queue_delete(self, frame):
        self.assertIsInstance(frame.method, spec.Queue.DeleteOk)
        self.stop()

    def start_test(self):
        """TornadoConnection should create and delete a named queue"""
        self.start()


class TestQueueRedeclareWithDifferentValues(AsyncTestCase):

    def begin(self, channel):
        self.channel.add_on_close_callback(self.on_channel_closed)
        channel.queue_declare(self.on_queue_declared,
                              str(id(self)),
                              passive=False,
                              durable=False,
                              exclusive=True,
                              auto_delete=True,
                              nowait=False,
                              arguments={'x-expires': self.TIMEOUT})

    def on_channel_closed(self, channel, reply_code, reply_text):
        self.stop()

    def on_queue_declared(self, frame):
        self.channel.queue_declare(self.on_bad_result,
                                   str(id(self)),
                                   passive=False,
                                   durable=True,
                                   exclusive=False,
                                   auto_delete=True,
                                   nowait=False,
                                   arguments={'x-expires': self.TIMEOUT})

    def on_bad_result(self, frame):
        self.channel.queue_delete(None, str(id(self)), nowait=True)
        raise AssertionError("Should not have received a Queue.DeclareOk")

    def start_test(self):
        """TornadoConnection should close chan: re-declared queue w/ diff params

        """
        self.start()


class TestTX1_Select(AsyncTestCase):

    def begin(self, channel):
        channel.tx_select(self.on_complete)

    def on_complete(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.SelectOk)
        self.stop()

    def test_confirm_select(self):
        """TornadoConnection should receive confirmation of Tx.Select"""
        self.start()


class TestTX2_Commit(AsyncTestCase):

    def begin(self, channel):
        channel.tx_select(self.on_selectok)

    def on_selectok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.SelectOk)
        self.channel.tx_commit(self.on_commitok)

    def on_commitok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.CommitOk)
        self.stop()

    def start_test(self):
        """TornadoConnection should start a transaction, then commit it back"""
        self.start()


class TestTX2_CommitFailure(AsyncTestCase):

    def begin(self, channel):
        self.channel.add_on_close_callback(self.on_channel_closed)
        self.channel.tx_commit(self.on_commitok)

    def on_channel_closed(self, channel, reply_code, reply_text):
        self.stop()

    def on_selectok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.SelectOk)

    def on_commitok(self, frame):
        raise AssertionError("Should not have received a Tx.CommitOk")

    def start_test(self):
        """TornadoConnection should close the channel: commit without a TX"""
        self.start()


class TestTX3_Rollback(AsyncTestCase):

    def begin(self, channel):
        channel.tx_select(self.on_selectok)

    def on_selectok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.SelectOk)
        self.channel.tx_rollback(self.on_rollbackok)

    def on_rollbackok(self, frame):
        self.assertIsInstance(frame.method, spec.Tx.RollbackOk)
        self.stop()

    def start_test(self):
        """TornadoConnection should start a transaction, then roll it back"""
        self.start()


class TestTX3_RollbackFailure(AsyncTestCase):

    def begin(self, channel):
        self.channel.add_on_close_callback(self.on_channel_closed)
        self.channel.tx_rollback(self.on_commitok)

    def on_channel_closed(self, channel, reply_code, reply_text):
        self.stop()

    def on_commitok(self, frame):
        raise AssertionError("Should not have received a Tx.RollbackOk")

    def start_test(self):
        """TornadoConnection should close the channel: rollback without a TX"""
        self.start()


class TestZ_PublishAndConsume(BoundQueueTestCase):

    def on_ready(self, frame):
        self.ctag = self.channel.basic_consume(self.on_message, self.queue)
        self.msg_body = "%s: %i" % (self.__class__.__name__, time.time())
        self.channel.basic_publish(self.exchange,
                                   self.routing_key,
                                   self.msg_body)

    def on_cancelled(self, frame):
        self.assertIsInstance(frame.method, spec.Basic.CancelOk)
        self.stop()

    def on_message(self, channel, method, header, body):
        self.assertIsInstance(method, spec.Basic.Deliver)
        self.assertEqual(body, self.msg_body)
        self.channel.basic_ack(method.delivery_tag)
        self.channel.basic_cancel(self.on_cancelled, self.ctag)

    def start_test(self):
        """TornadoConnection should publish a message and consume it"""
        self.start()


class TestZ_PublishAndConsumeBig(BoundQueueTestCase):

    def _get_msg_body(self):
        return '\n'.join(["%s" % i for i in range(0, 2097152)])

    def on_ready(self, frame):
        self.ctag = self.channel.basic_consume(self.on_message, self.queue)
        self.msg_body = self._get_msg_body()
        self.channel.basic_publish(self.exchange,
                                   self.routing_key,
                                   self.msg_body)

    def on_cancelled(self, frame):
        self.assertIsInstance(frame.method, spec.Basic.CancelOk)
        self.stop()

    def on_message(self, channel, method, header, body):
        self.assertIsInstance(method, spec.Basic.Deliver)
        self.assertEqual(body, self.msg_body)
        self.channel.basic_ack(method.delivery_tag)
        self.channel.basic_cancel(self.on_cancelled, self.ctag)

    def start_test(self):
        """TornadoConnection should publish a big message and consume it"""
        self.start()



class TestZ_PublishAndGet(BoundQueueTestCase):

    def on_ready(self, frame):
        self.msg_body = "%s: %i" % (self.__class__.__name__, time.time())
        self.channel.basic_publish(self.exchange,
                                   self.routing_key,
                                   self.msg_body)
        self.channel.basic_get(self.on_get, self.queue)

    def on_get(self, channel, method, header, body):
        self.assertIsInstance(method, spec.Basic.GetOk)
        self.assertEqual(body, self.msg_body)
        self.channel.basic_ack(method.delivery_tag)
        self.stop()

    def start_test(self):
        """TornadoConnection should publish a message and get it"""
        self.start()


########NEW FILE########
__FILENAME__ = amqp_object_tests
"""
Tests for pika.callback

"""
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from pika import amqp_object


class AMQPObjectTests(unittest.TestCase):

    def test_base_name(self):
        self.assertEqual(amqp_object.AMQPObject().NAME, 'AMQPObject')

    def test_repr_no_items(self):
        obj = amqp_object.AMQPObject()
        self.assertEqual(repr(obj), '<AMQPObject>')

    def test_repr_items(self):
        obj = amqp_object.AMQPObject()
        setattr(obj, 'foo', 'bar')
        setattr(obj, 'baz', 'qux')
        self.assertEqual(repr(obj), "<AMQPObject(['baz=qux', 'foo=bar'])>")


class ClassTests(unittest.TestCase):

    def test_base_name(self):
        self.assertEqual(amqp_object.Class().NAME, 'Unextended Class')

class MethodTests(unittest.TestCase):

    def test_base_name(self):
        self.assertEqual(amqp_object.Method().NAME, 'Unextended Method')

    def test_set_content_body(self):
        properties = amqp_object.Properties()
        body = 'This is a test'
        obj = amqp_object.Method()
        obj._set_content(properties, body)
        self.assertEqual(obj._body, body)

    def test_set_content_properties(self):
        properties = amqp_object.Properties()
        body = 'This is a test'
        obj = amqp_object.Method()
        obj._set_content(properties, body)
        self.assertEqual(obj._properties, properties)

    def test_get_body(self):
        properties = amqp_object.Properties()
        body = 'This is a test'
        obj = amqp_object.Method()
        obj._set_content(properties, body)
        self.assertEqual(obj.get_body(), body)

    def test_get_properties(self):
        properties = amqp_object.Properties()
        body = 'This is a test'
        obj = amqp_object.Method()
        obj._set_content(properties, body)
        self.assertEqual(obj.get_properties(), properties)

class PropertiesTests(unittest.TestCase):

    def test_base_name(self):
        self.assertEqual(amqp_object.Properties().NAME, 'Unextended Properties')

########NEW FILE########
__FILENAME__ = base_connection_tests
"""
Tests for pika.base_connection.BaseConnection

"""
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from pika.adapters import base_connection


class BaseConnectionTests(unittest.TestCase):

    def test_should_raise_value_exception_with_no_params_func_instead(self):
      def foo():
          return True
      self.assertRaises(ValueError, base_connection.BaseConnection, foo)

########NEW FILE########
__FILENAME__ = blocking_channel_tests
# -*- coding: utf8 -*-
"""
Tests for pika.adapters.blocking_connection.BlockingChannel

"""
import logging
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from pika.adapters import blocking_connection
from pika import callback
from pika import frame
from pika import spec

BLOCKING_CHANNEL = 'pika.adapters.blocking_connection.BlockingChannel'
BLOCKING_CONNECTION = 'pika.adapters.blocking_connection.BlockingConnection'


class BlockingChannelTests(unittest.TestCase):

    @mock.patch(BLOCKING_CONNECTION)
    def _create_connection(self, connection=None):
        return connection

    def setUp(self):
        self.connection = self._create_connection()
        with mock.patch(BLOCKING_CHANNEL + '.open') as _open:
            self.obj = blocking_connection.BlockingChannel(self.connection, 1)
            self._open = _open

    def tearDown(self):
        del self.connection
        del self.obj

    def test_init_initial_value_confirmation(self):
        self.assertFalse(self.obj._confirmation)

    def test_init_initial_value_force_data_events_override(self):
        self.assertFalse(self.obj._force_data_events_override)

    def test_init_initial_value_frames(self):
        self.assertDictEqual(self.obj._frames, dict())

    def test_init_initial_value_replies(self):
        self.assertListEqual(self.obj._replies, list())

    def test_init_initial_value_wait(self):
        self.assertFalse(self.obj._wait)

    def test_init_open_called(self):
        self._open.assert_called_once_with()


########NEW FILE########
__FILENAME__ = callback_tests
# -*- coding: utf8 -*-
"""
Tests for pika.callback

"""
import logging
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from pika import amqp_object
from pika import callback
from pika import frame
from pika import spec


class CallbackTests(unittest.TestCase):

    KEY = 'Test Key'
    ARGUMENTS = callback.CallbackManager.ARGUMENTS
    CALLS = callback.CallbackManager.CALLS
    CALLBACK = callback.CallbackManager.CALLBACK
    ONE_SHOT = callback.CallbackManager.ONE_SHOT
    ONLY_CALLER = callback.CallbackManager.ONLY_CALLER
    PREFIX_CLASS = spec.Basic.Consume
    PREFIX = 'Basic.Consume'
    ARGUMENTS_VALUE = {'foo': 'bar'}

    @property
    def _callback_dict(self):
        return {self.CALLBACK: self.callback_mock,
                self.ONE_SHOT: True,
                self.ONLY_CALLER: self.mock_caller,
                self.ARGUMENTS: self.ARGUMENTS_VALUE,
                self.CALLS: 1}

    def setUp(self):
        self.obj = callback.CallbackManager()
        self.callback_mock = mock.Mock()
        self.mock_caller = mock.Mock()

    def tearDown(self):
        del self.obj
        del self.callback_mock
        del self.mock_caller

    def test_initialization(self):
        obj = callback.CallbackManager()
        self.assertDictEqual(obj._stack, {})


    def test_name_or_value_method_object(self):
        value = spec.Basic.Consume()
        self.assertEqual(callback._name_or_value(value), self.PREFIX)

    def test_name_or_value_basic_consume_object(self):
        self.assertEqual(callback._name_or_value(spec.Basic.Consume()),
                         self.PREFIX)

    def test_name_or_value_amqpobject_class(self):
        self.assertEqual(callback._name_or_value(self.PREFIX_CLASS),
                         self.PREFIX)

    def test_name_or_value_protocol_header(self):
        self.assertEqual(callback._name_or_value(frame.ProtocolHeader()),
                         'ProtocolHeader')

    def test_name_or_value_method_frame(self):
        value = frame.Method(1, self.PREFIX_CLASS())
        self.assertEqual(callback._name_or_value(value), self.PREFIX)

    def test_name_or_value_str(self):
        value = 'Test String Value'
        expectation = value
        self.assertEqual(callback._name_or_value(value), expectation)

    def test_name_or_value_unicode(self):
        value = u'Это тест значения'
        expectation = ('\xd0\xad\xd1\x82\xd0\xbe \xd1\x82\xd0\xb5\xd1\x81\xd1'
                       '\x82 \xd0\xb7\xd0\xbd\xd0\xb0\xd1\x87\xd0\xb5\xd0\xbd'
                       '\xd0\xb8\xd1\x8f')
        self.assertEqual(callback._name_or_value(value), expectation)

    def test_empty_callbacks_on_init(self):
        self.assertFalse(self.obj._stack)

    def test_sanitize_decorator_with_args_only(self):
        self.obj.add(self.PREFIX_CLASS, self.KEY, None)
        self.assertIn(self.PREFIX, self.obj._stack.keys())

    def test_sanitize_decorator_with_kwargs(self):
        self.obj.add(prefix=self.PREFIX_CLASS, key=self.KEY, callback=None)
        self.assertIn(self.PREFIX, self.obj._stack.keys())

    def test_sanitize_decorator_with_mixed_args_and_kwargs(self):
        self.obj.add(self.PREFIX_CLASS, key=self.KEY, callback=None)
        self.assertIn(self.PREFIX, self.obj._stack.keys())

    def test_add_first_time_prefix_added(self):
        self.obj.add(self.PREFIX, self.KEY, None)
        self.assertIn(self.PREFIX, self.obj._stack)

    def test_add_first_time_key_added(self):
        self.obj.add(self.PREFIX, self.KEY, None)
        self.assertIn(self.KEY, self.obj._stack[self.PREFIX])

    def test_add_first_time_callback_added(self):
        self.obj.add(self.PREFIX, self.KEY, self.callback_mock)
        self.assertEqual(self.callback_mock,
                         self.obj._stack[self.PREFIX][self.KEY][0][self.CALLBACK])

    def test_add_oneshot_default_is_true(self):
        self.obj.add(self.PREFIX, self.KEY, None)
        self.assertTrue(self.obj._stack[self.PREFIX][self.KEY][0][self.ONE_SHOT])

    def test_add_oneshot_is_false(self):
        self.obj.add(self.PREFIX, self.KEY, None, False)
        self.assertFalse(self.obj._stack[self.PREFIX][self.KEY][0][self.ONE_SHOT])

    def test_add_only_caller_default_is_false(self):
        self.obj.add(self.PREFIX, self.KEY, None)
        self.assertFalse(self.obj._stack[self.PREFIX][self.KEY][0][self.ONLY_CALLER])

    def test_add_only_caller_true(self):
        self.obj.add(self.PREFIX, self.KEY, None, only_caller=True)
        self.assertTrue(self.obj._stack[self.PREFIX][self.KEY][0][self.ONLY_CALLER])

    def test_add_returns_prefix_value_and_key(self):
        self.assertEqual(self.obj.add(self.PREFIX, self.KEY, None),
                         (self.PREFIX, self.KEY))

    def test_add_duplicate_callback(self):
        mock_callback = mock.Mock()

        def add_callback():
            self.obj.add(self.PREFIX, self.KEY, mock_callback, False)


        with mock.patch('pika.callback.LOGGER', spec=logging.Logger) as logger:
            logger.warning = mock.Mock()
            add_callback()
            add_callback()
            DUPLICATE_WARNING = callback.CallbackManager.DUPLICATE_WARNING
            logger.warning.assert_called_once_with(DUPLICATE_WARNING,
                                                   self.PREFIX, self.KEY)

    def test_add_duplicate_callback_returns_prefix_value_and_key(self):
        self.obj.add(self.PREFIX, self.KEY, None)
        self.assertEqual(self.obj.add(self.PREFIX, self.KEY, None),
                         (self.PREFIX, self.KEY))

    def test_clear(self):
        self.obj.add(self.PREFIX, self.KEY, None)
        self.obj.clear()
        self.assertDictEqual(self.obj._stack, dict())

    def test_cleanup_removes_prefix(self):
        OTHER_PREFIX = 'Foo'
        self.obj.add(self.PREFIX, self.KEY, None)
        self.obj.add(OTHER_PREFIX, 'Bar', None)
        self.obj.cleanup(self.PREFIX)
        self.assertNotIn(self.PREFIX, self.obj._stack)

    def test_cleanup_keeps_other_prefix(self):
        OTHER_PREFIX = 'Foo'
        self.obj.add(self.PREFIX, self.KEY, None)
        self.obj.add(OTHER_PREFIX, 'Bar', None)
        self.obj.cleanup(self.PREFIX)
        self.assertIn(OTHER_PREFIX, self.obj._stack)

    def test_cleanup_returns_true(self):
        self.obj.add(self.PREFIX, self.KEY, None)
        self.assertTrue(self.obj.cleanup(self.PREFIX))

    def test_missing_prefix(self):
        self.assertFalse(self.obj.cleanup(self.PREFIX))

    def test_pending_none(self):
        self.assertIsNone(self.obj.pending(self.PREFIX_CLASS, self.KEY))

    def test_pending_one(self):
        self.obj.add(self.PREFIX, self.KEY, None)
        self.assertEqual(self.obj.pending(self.PREFIX_CLASS, self.KEY), 1)

    def test_pending_two(self):
        self.obj.add(self.PREFIX, self.KEY, None)
        self.obj.add(self.PREFIX, self.KEY, lambda x: True)
        self.assertEqual(self.obj.pending(self.PREFIX_CLASS, self.KEY), 2)

    def test_process_callback_false(self):
        self.obj._stack = dict()
        self.assertFalse(self.obj.process('FAIL', 'False', 'Empty',
                                          self.mock_caller, []))

    def test_process_false(self):
        self.assertFalse(self.obj.process(self.PREFIX_CLASS, self.KEY, self))

    def test_process_true(self):
        self.obj.add(self.PREFIX, self.KEY, self.callback_mock)
        self.assertTrue(self.obj.process(self.PREFIX_CLASS, self.KEY, self))

    def test_process_mock_called(self):
        args = (1, None, 'Hi')
        self.obj.add(self.PREFIX, self.KEY, self.callback_mock)
        self.obj.process(self.PREFIX, self.KEY, self, args)
        self.callback_mock.assert_called_once_with(args)

    def test_process_one_shot_removed(self):
        args = (1, None, 'Hi')
        self.obj.add(self.PREFIX, self.KEY, self.callback_mock)
        self.obj.process(self.PREFIX, self.KEY, self, args)
        self.assertNotIn(self.PREFIX, self.obj._stack)

    def test_process_non_one_shot_prefix_not_removed(self):
        self.obj.add(self.PREFIX, self.KEY, self.callback_mock, one_shot=False)
        self.obj.process(self.PREFIX, self.KEY, self)
        self.assertIn(self.PREFIX, self.obj._stack)

    def test_process_non_one_shot_key_not_removed(self):
        self.obj.add(self.PREFIX, self.KEY, self.callback_mock, one_shot=False)
        self.obj.process(self.PREFIX, self.KEY, self)
        self.assertIn(self.KEY, self.obj._stack[self.PREFIX])

    def test_process_non_one_shot_callback_not_removed(self):
        self.obj.add(self.PREFIX, self.KEY, self.callback_mock, one_shot=False)
        self.obj.process(self.PREFIX, self.KEY, self)
        self.assertEqual(self.obj._stack[self.PREFIX][self.KEY][0][self.CALLBACK],
                         self.callback_mock)

    def test_process_only_caller_fails(self):
        self.obj.add(self.PREFIX_CLASS, self.KEY, self.callback_mock,
                only_caller=self.mock_caller)
        self.obj.process(self.PREFIX_CLASS, self.KEY, self)
        self.assertFalse(self.callback_mock.called)

    def test_process_only_caller_fails_no_removal(self):
        self.obj.add(self.PREFIX_CLASS, self.KEY, self.callback_mock,
                     only_caller=self.mock_caller)
        self.obj.process(self.PREFIX_CLASS, self.KEY, self)
        self.assertEqual(self.obj._stack[self.PREFIX][self.KEY][0][self.CALLBACK],
                         self.callback_mock)

    def test_remove_with_no_callbacks_pending(self):
        self.obj = callback.CallbackManager()
        self.assertFalse(self.obj.remove(self.PREFIX, self.KEY,
                                         self.callback_mock))

    def test_remove_with_callback_true(self):
        self.obj.add(self.PREFIX_CLASS, self.KEY, self.callback_mock)
        self.assertTrue(self.obj.remove(self.PREFIX, self.KEY,
                                        self.callback_mock))

    def test_remove_with_callback_false(self):
        self.obj.add(self.PREFIX_CLASS, self.KEY, None)
        self.assertTrue(self.obj.remove(self.PREFIX, self.KEY,
                                        self.callback_mock))

    def test_remove_with_callback_true_empty_stack(self):
        self.obj.add(self.PREFIX_CLASS, self.KEY, self.callback_mock)
        self.obj.remove(prefix=self.PREFIX, key=self.KEY,
                        callback_value=self.callback_mock)
        self.assertDictEqual(self.obj._stack, dict())

    def test_remove_with_callback_true_non_empty_stack(self):
        self.obj.add(self.PREFIX_CLASS, self.KEY, self.callback_mock)
        self.obj.add(self.PREFIX_CLASS, self.KEY, self.mock_caller)
        self.obj.remove(self.PREFIX, self.KEY, self.callback_mock)
        self.assertEqual(self.mock_caller,
                         self.obj._stack[self.PREFIX][self.KEY][0][self.CALLBACK])

    def test_remove_prefix_key_with_other_key_prefix_remains(self):
        OTHER_KEY = 'Other Key'
        self.obj.add(self.PREFIX_CLASS, self.KEY, self.callback_mock)
        self.obj.add(self.PREFIX_CLASS, OTHER_KEY, self.mock_caller)
        self.obj.remove(self.PREFIX, self.KEY, self.callback_mock)
        self.assertIn(self.PREFIX, self.obj._stack)

    def test_remove_prefix_key_with_other_key_remains(self):
        OTHER_KEY = 'Other Key'
        self.obj.add(self.PREFIX_CLASS, self.KEY, self.callback_mock)
        self.obj.add(prefix=self.PREFIX_CLASS, key=OTHER_KEY,
                     callback=self.mock_caller)
        self.obj.remove(self.PREFIX, self.KEY)
        self.assertIn(OTHER_KEY, self.obj._stack[self.PREFIX])

    def test_remove_prefix_key_with_other_key_callback_remains(self):
        OTHER_KEY = 'Other Key'
        self.obj.add(self.PREFIX_CLASS, self.KEY, self.callback_mock)
        self.obj.add(self.PREFIX_CLASS, OTHER_KEY, self.mock_caller)
        self.obj.remove(self.PREFIX, self.KEY)
        self.assertEqual(self.mock_caller,
                         self.obj._stack[self.PREFIX][OTHER_KEY][0][self.CALLBACK])

    def test_remove_all(self):
        self.obj.add(self.PREFIX_CLASS, self.KEY, self.callback_mock)
        self.obj.remove_all(self.PREFIX, self.KEY)
        self.assertNotIn(self.PREFIX, self.obj._stack)

    def test_should_process_callback_true(self):
        self.obj.add(self.PREFIX_CLASS, self.KEY, self.callback_mock)
        value = self.obj._callback_dict(self.callback_mock, False, None, None)
        self.assertTrue(self.obj._should_process_callback(value,
                                                          self.mock_caller, []))

    def test_should_process_callback_false_argument_fail(self):
        self.obj.clear()
        self.obj.add(self.PREFIX_CLASS, self.KEY, self.callback_mock,
                     arguments={'foo': 'baz'})
        self.assertFalse(self.obj._should_process_callback(self._callback_dict,
                                                           self.mock_caller,
                                                           [{'foo': 'baz'}]))

    def test_should_process_callback_false_only_caller_failure(self):
        self.obj.add(self.PREFIX_CLASS, self.KEY, self.callback_mock)
        value = self.obj._callback_dict(self.callback_mock, False, self, None)
        self.assertTrue(self.obj._should_process_callback(value,
                                                          self.mock_caller, []))

    def test_should_process_callback_false_only_caller_failure(self):
        self.obj.add(self.PREFIX_CLASS, self.KEY, self.callback_mock)
        value = self.obj._callback_dict(self.callback_mock, False,
                                        self.mock_caller, None)
        self.assertTrue(self.obj._should_process_callback(value,
                                                          self.mock_caller, []))

    def test_dict(self):
        self.assertDictEqual(self.obj._callback_dict(self.callback_mock,
                                                     True, self.mock_caller,
                                                     self.ARGUMENTS_VALUE),
                             self._callback_dict)

    def test_arguments_match_no_arguments(self):
        self.assertFalse(self.obj._arguments_match(self._callback_dict, []))

    def test_arguments_match_dict_argument(self):
        self.assertTrue(self.obj._arguments_match(self._callback_dict,
                                                  [self.ARGUMENTS_VALUE]))

    def test_arguments_match_dict_argument_no_attribute(self):
        self.assertFalse(self.obj._arguments_match(self._callback_dict,
                                                   [{}]))

    def test_arguments_match_dict_argument_no_match(self):
        self.assertFalse(self.obj._arguments_match(self._callback_dict,
                                                   [{'foo': 'baz'}]))

    def test_arguments_match_obj_argument(self):
        class TestObj(object):
            foo = 'bar'
        test_instance = TestObj()
        self.assertTrue(self.obj._arguments_match(self._callback_dict,
                                                  [test_instance]))

    def test_arguments_match_obj_no_attribute(self):
        class TestObj(object):
            qux = 'bar'
        test_instance = TestObj()
        self.assertFalse(self.obj._arguments_match(self._callback_dict,
                                                  [test_instance]))

    def test_arguments_match_obj_argument_no_match(self):
        class TestObj(object):
            foo = 'baz'
        test_instance = TestObj()
        self.assertFalse(self.obj._arguments_match(self._callback_dict,
                                                   [test_instance]))

    def test_arguments_match_obj_argument_with_method(self):
        class TestFrame(object):
            method = None
        class MethodObj(object):
            foo = 'bar'
        test_instance = TestFrame()
        test_instance.method = MethodObj()
        self.assertTrue(self.obj._arguments_match(self._callback_dict,
                                                  [test_instance]))

    def test_arguments_match_obj_argument_with_method_no_match(self):
        class TestFrame(object):
            method = None
        class MethodObj(object):
            foo = 'baz'
        test_instance = TestFrame()
        test_instance.method = MethodObj()
        self.assertFalse(self.obj._arguments_match(self._callback_dict,
                                                   [test_instance]))

########NEW FILE########
__FILENAME__ = channel_tests
"""
Tests for pika.channel.ContentFrameDispatcher

"""
import collections
import logging
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import warnings

from pika import channel
from pika import exceptions
from pika import frame
from pika import spec


class ChannelTests(unittest.TestCase):

    @mock.patch('pika.connection.Connection')
    def _create_connection(self, connection=None):
        return connection

    def setUp(self):
        self.connection = self._create_connection()
        self._on_openok_callback = mock.Mock()
        self.obj = channel.Channel(self.connection, 1,
                                   self._on_openok_callback)
        warnings.resetwarnings()

    def tearDown(self):
        del self.connection
        del self._on_openok_callback
        del self.obj
        warnings.resetwarnings()

    def test_init_invalid_channel_number(self):
        self.assertRaises(exceptions.InvalidChannelNumber,
                          channel.Channel,
                          'Foo', self.connection)

    def test_init_channel_number(self):
        self.assertEqual(self.obj.channel_number, 1)

    def test_init_callbacks(self):
        self.assertEqual(self.obj.callbacks, self.connection.callbacks)

    def test_init_connection(self):
        self.assertEqual(self.obj.connection, self.connection)

    def test_init_frame_dispatcher(self):
        self.assertIsInstance(self.obj.frame_dispatcher,
                              channel.ContentFrameDispatcher)

    def test_init_blocked(self):
        self.assertIsInstance(self.obj._blocked, collections.deque)

    def test_init_blocking(self):
        self.assertEqual(self.obj._blocking, None)

    def test_init_on_flowok_callback(self):
        self.assertEqual(self.obj._on_flowok_callback, None)

    def test_init_has_on_flow_callback(self):
        self.assertEqual(self.obj._has_on_flow_callback, False)

    def test_init_on_openok_callback(self):
        self.assertEqual(self.obj._on_openok_callback, self._on_openok_callback)

    def test_init_state(self):
        self.assertEqual(self.obj._state, channel.Channel.CLOSED)

    def test_init_cancelled(self):
        self.assertIsInstance(self.obj._cancelled, collections.deque)

    def test_init_consumers(self):
        self.assertEqual(self.obj._consumers, dict())

    def test_init_pending(self):
        self.assertEqual(self.obj._pending, dict())

    def test_init_on_getok_callback(self):
        self.assertEqual(self.obj._on_getok_callback, None)

    def test_init_on_flowok_callback(self):
        self.assertEqual(self.obj._on_flowok_callback, None)

    def test_add_callback(self):
        mock_callback = mock.Mock()
        self.obj.add_callback(mock_callback, [spec.Basic.Qos])
        self.connection.callbacks.add.assert_called_once_with(self.obj.channel_number,
                                                              spec.Basic.Qos,
                                                              mock_callback,
                                                              True)

    def test_add_callback_multiple_replies(self):
        mock_callback = mock.Mock()
        self.obj.add_callback(mock_callback, [spec.Basic.Qos, spec.Basic.QosOk])
        calls = [mock.call(self.obj.channel_number, spec.Basic.Qos,
                           mock_callback, True),
                 mock.call(self.obj.channel_number, spec.Basic.QosOk,
                           mock_callback, True)]
        self.connection.callbacks.add.assert_has_calls(calls)

    def test_add_on_cancel_callback(self):
        mock_callback = mock.Mock()
        self.obj.add_on_cancel_callback(mock_callback)
        self.connection.callbacks.add.assert_called_once_with(self.obj.channel_number,
                                                              spec.Basic.Cancel,
                                                              mock_callback,
                                                              False)

    def test_add_on_close_callback(self):
        mock_callback = mock.Mock()
        self.obj.add_on_close_callback(mock_callback)
        self.connection.callbacks.add.assert_called_once_with(self.obj.channel_number,
                                                              '_on_channel_close',
                                                              mock_callback,
                                                              False,
                                                              self.obj)

    def test_add_on_flow_callback(self):
        mock_callback = mock.Mock()
        self.obj.add_on_flow_callback(mock_callback)
        self.connection.callbacks.add.assert_called_once_with(self.obj.channel_number,
                                                              spec.Channel.Flow,
                                                              mock_callback,
                                                              False)

    def test_add_on_return_callback(self):
        mock_callback = mock.Mock()
        self.obj.add_on_return_callback(mock_callback)
        self.connection.callbacks.add.assert_called_once_with(self.obj.channel_number,
                                                              '_on_return',
                                                              mock_callback,
                                                              False)

    def test_basic_ack_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed,
                          self.obj.basic_ack)

    @mock.patch('pika.channel.Channel._validate_channel_and_callback')
    def test_basic_cancel_calls_validate(self, validate):
        self.obj._set_state(self.obj.OPEN)
        consumer_tag = 'ctag0'
        callback_mock = mock.Mock()
        self.obj._consumers[consumer_tag] = callback_mock
        self.obj.basic_cancel(callback_mock, consumer_tag)
        validate.assert_called_once_with(callback_mock)

    @mock.patch('pika.spec.Basic.Ack')
    @mock.patch('pika.channel.Channel._send_method')
    def test_basic_send_method_calls_rpc(self, send_method, unused):
        self.obj._set_state(self.obj.OPEN)
        self.obj.basic_ack(1, False)
        send_method.assert_called_once_with(spec.Basic.Ack(1, False))

    @mock.patch('pika.channel.Channel._rpc')
    def test_basic_cancel_no_consumer_tag(self, rpc):
        self.obj._set_state(self.obj.OPEN)
        callback_mock = mock.Mock()
        consumer_tag = 'ctag0'
        self.obj.basic_cancel(callback_mock, consumer_tag)
        self.assertFalse(rpc.called)

    @mock.patch('pika.channel.Channel._rpc')
    def test_basic_cancel_channel_cancelled_appended(self, unused):
        self.obj._set_state(self.obj.OPEN)
        callback_mock = mock.Mock()
        consumer_tag = 'ctag0'
        self.obj._consumers[consumer_tag] = mock.Mock()
        self.obj.basic_cancel(callback_mock, consumer_tag)
        self.assertListEqual(list(self.obj._cancelled), [consumer_tag])

    def test_basic_cancel_callback_appended(self):
        self.obj._set_state(self.obj.OPEN)
        consumer_tag = 'ctag0'
        callback_mock = mock.Mock()
        self.obj._consumers[consumer_tag] = callback_mock
        self.obj.basic_cancel(callback_mock, consumer_tag)
        expectation = [self.obj.channel_number,
                       spec.Basic.CancelOk,
                       callback_mock]
        self.obj.callbacks.add.assert_any_call(*expectation)

    def test_basic_cancel_raises_value_error(self):
        self.obj._set_state(self.obj.OPEN)
        consumer_tag = 'ctag0'
        callback_mock = mock.Mock()
        self.obj._consumers[consumer_tag] = callback_mock
        self.assertRaises(ValueError, self.obj.basic_cancel, callback_mock,
                          consumer_tag, nowait=True)

    def test_basic_cancel_then_close(self):
        self.obj._set_state(self.obj.OPEN)
        callback_mock = mock.Mock()
        consumer_tag = 'ctag0'
        self.obj._consumers[consumer_tag] = mock.Mock()
        self.obj.basic_cancel(callback_mock, consumer_tag)
        try:
            self.obj.close()
        except exceptions.ChannelClosed:
            self.fail('unable to cancel consumers as channel is closing')
        self.assertTrue(self.obj.is_closing)

    def test_basic_cancel_on_cancel_appended(self):
        self.obj._set_state(self.obj.OPEN)
        self.obj._consumers['ctag0'] = logging.debug
        self.obj.basic_cancel(consumer_tag='ctag0')
        expectation = [self.obj.channel_number,
                       spec.Basic.CancelOk,
                       self.obj._on_cancelok]
        self.obj.callbacks.add.assert_any_call(*expectation,
                                               arguments={'consumer_tag': 'ctag0'})

    def test_basic_consume_channel_closed(self):
        mock_callback = mock.Mock()
        self.assertRaises(exceptions.ChannelClosed,
                          self.obj.basic_consume,
                          mock_callback, 'test-queue')

    @mock.patch('pika.channel.Channel._validate_channel_and_callback')
    def test_basic_consume_calls_validate(self, validate):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.basic_consume(mock_callback, 'test-queue')
        validate.assert_called_once_with(mock_callback)

    def test_basic_consume_consumer_tag(self):
        self.obj._set_state(self.obj.OPEN)
        expectation = 'ctag1.'
        mock_callback = mock.Mock()
        self.assertEqual(self.obj.basic_consume(mock_callback, 'test-queue')[:6],
                         expectation)

    def test_basic_consume_consumer_tag_cancelled_full(self):
        self.obj._set_state(self.obj.OPEN)
        expectation = 'ctag1.'
        mock_callback = mock.Mock()
        for ctag in ['ctag1.%i' % ii for ii in range(11)]:
            self.obj._cancelled.append(ctag)
        self.assertEqual(self.obj.basic_consume(mock_callback, 'test-queue')[:6],
                         expectation)

    def test_basic_consume_consumer_tag_in_consumers(self):
        self.obj._set_state(self.obj.OPEN)
        consumer_tag = 'ctag1.0'
        mock_callback = mock.Mock()
        self.obj.basic_consume(mock_callback, 'test-queue', consumer_tag=consumer_tag)
        self.assertIn(consumer_tag, self.obj._consumers)

    def test_basic_consume_duplicate_consumer_tag_raises(self):
        self.obj._set_state(self.obj.OPEN)
        consumer_tag = 'ctag1.0'
        mock_callback = mock.Mock()
        self.obj._consumers[consumer_tag] = logging.debug
        self.assertRaises(exceptions.DuplicateConsumerTag,
                          self.obj.basic_consume,
                          mock_callback,
                          'test-queue',
                          False, False, consumer_tag)

    def test_basic_consume_consumers_callback_value(self):
        self.obj._set_state(self.obj.OPEN)
        consumer_tag = 'ctag1.0'
        mock_callback = mock.Mock()
        self.obj.basic_consume(mock_callback, 'test-queue', consumer_tag=consumer_tag)
        self.assertEqual(self.obj._consumers[consumer_tag], mock_callback)

    def test_basic_consume_has_pending_list(self):
        self.obj._set_state(self.obj.OPEN)
        consumer_tag = 'ctag1.0'
        mock_callback = mock.Mock()
        self.obj.basic_consume(mock_callback, 'test-queue', consumer_tag=consumer_tag)
        self.assertIn(consumer_tag, self.obj._pending)

    def test_basic_consume_consumers_pending_list_is_empty(self):
        self.obj._set_state(self.obj.OPEN)
        consumer_tag = 'ctag1.0'
        mock_callback = mock.Mock()
        self.obj.basic_consume(mock_callback, 'test-queue', consumer_tag=consumer_tag)
        self.assertEqual(self.obj._pending[consumer_tag], list())

    @mock.patch('pika.spec.Basic.Consume')
    @mock.patch('pika.channel.Channel._rpc')
    def test_basic_consume_consumers_rpc_called(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        consumer_tag = 'ctag1.0'
        mock_callback = mock.Mock()
        self.obj.basic_consume(mock_callback, 'test-queue', consumer_tag=consumer_tag)
        expectation = spec.Basic.Consume(queue='test-queue',
                                         consumer_tag=consumer_tag,
                                         no_ack=False,
                                         exclusive=False)
        rpc.assert_called_once_with(expectation,
                                    self.obj._on_eventok,
                                    [(spec.Basic.ConsumeOk,
                                      {'consumer_tag': consumer_tag})])

    @mock.patch('pika.channel.Channel._validate_channel_and_callback')
    def test_basic_get_calls_validate(self, validate):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.basic_get(mock_callback, 'test-queue')
        validate.assert_called_once_with(mock_callback)

    @mock.patch('pika.channel.Channel._send_method')
    def test_basic_get_callback(self, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.basic_get(mock_callback, 'test-queue')
        self.assertEqual(self.obj._on_getok_callback, mock_callback)

    @mock.patch('pika.spec.Basic.Get')
    @mock.patch('pika.channel.Channel._send_method')
    def test_basic_get_send_mehtod_called(self, send_method, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.basic_get(mock_callback, 'test-queue', False)
        send_method.assert_called_once_with(spec.Basic.Get(queue='test-queue',
                                                           no_ack=False))

    def test_basic_nack_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed, self.obj.basic_nack,
                          0, False, True)

    @mock.patch('pika.spec.Basic.Nack')
    @mock.patch('pika.channel.Channel._send_method')
    def test_basic_nack_send_method_request(self, send_method, unused):
        self.obj._set_state(self.obj.OPEN)
        self.obj.basic_nack(1, False, True)
        send_method.assert_called_once_with(spec.Basic.Nack(1, False, True))

    def test_basic_publish_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed, self.obj.basic_publish,
                          'foo', 'bar', 'baz')

    @mock.patch('pika.channel.LOGGER')
    @mock.patch('pika.spec.Basic.Publish')
    @mock.patch('pika.channel.Channel._send_method')
    def test_immediate_called_logger_warning(self, send_method, unused, logger):
        self.obj._set_state(self.obj.OPEN)
        exchange = 'basic_publish_test'
        routing_key = 'routing-key-fun'
        body = 'This is my body'
        properties = spec.BasicProperties(content_type='text/plain')
        mandatory = False
        immediate = True
        self.obj.basic_publish(exchange, routing_key, body, properties,
                               mandatory, immediate)
        logger.warning.assert_called_once_with('The immediate flag is '
                                               'deprecated in RabbitMQ')

    @mock.patch('pika.spec.Basic.Publish')
    @mock.patch('pika.channel.Channel._send_method')
    def test_basic_publish_send_method_request(self, send_method, unused):
        self.obj._set_state(self.obj.OPEN)
        exchange = 'basic_publish_test'
        routing_key = 'routing-key-fun'
        body = 'This is my body'
        properties = spec.BasicProperties(content_type='text/plain')
        mandatory = False
        immediate = False
        self.obj.basic_publish(exchange, routing_key, body, properties,
                               mandatory, immediate)
        send_method.assert_called_once_with(spec.Basic.Publish(exchange=exchange,
                                                               routing_key=routing_key,
                                                               mandatory=mandatory,
                                                               immediate=immediate),
                                            (properties, body))

    def test_basic_qos_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed, self.obj.basic_qos,
                          0, False, True)

    @mock.patch('pika.spec.Basic.Qos')
    @mock.patch('pika.channel.Channel._rpc')
    def test_basic_qos_rpc_request(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.basic_qos(mock_callback, 10, 20, False)
        rpc.assert_called_once_with(spec.Basic.Qos(mock_callback, 10, 20,
                                                   False),
                                    mock_callback, [spec.Basic.QosOk])

    def test_basic_reject_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed, self.obj.basic_reject,
                          1, False)

    @mock.patch('pika.spec.Basic.Reject')
    @mock.patch('pika.channel.Channel._send_method')
    def test_basic_reject_send_method_request(self, send_method, unused):
        self.obj._set_state(self.obj.OPEN)
        self.obj.basic_reject(1, True)
        send_method.assert_called_once_with(spec.Basic.Reject(1, True))

    def test_basic_recover_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed, self.obj.basic_qos,
                          0, False, True)

    @mock.patch('pika.spec.Basic.Recover')
    @mock.patch('pika.channel.Channel._rpc')
    def test_basic_recover_rpc_request(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.basic_recover(mock_callback, True)
        rpc.assert_called_once_with(spec.Basic.Recover(mock_callback, True),
                                    mock_callback, [spec.Basic.RecoverOk])

    def test_close_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed, self.obj.close)

    def test_close_state(self):
        self.obj._set_state(self.obj.OPEN)
        self.obj.close()
        self.assertEqual(self.obj._state, channel.Channel.CLOSING)

    def test_close_basic_cancel_called(self):
        self.obj._set_state(self.obj.OPEN)
        self.obj._consumers['abc'] = None
        with mock.patch.object(self.obj, 'basic_cancel') as basic_cancel:
            self.obj.close()
            basic_cancel.assert_called_once_with(consumer_tag='abc')

    def test_confirm_delivery_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed, self.obj.confirm_delivery)

    def test_confirm_delivery_raises_method_not_implemented_for_confirms(self):
        self.obj._set_state(self.obj.OPEN)
        # Since connection is a mock.Mock, overwrite the method def with False
        self.obj.connection.publisher_confirms = False
        self.assertRaises(exceptions.MethodNotImplemented,
                          self.obj.confirm_delivery, logging.debug)

    def test_confirm_delivery_raises_method_not_implemented_for_nack(self):
        self.obj._set_state(self.obj.OPEN)
        # Since connection is a mock.Mock, overwrite the method def with False
        self.obj.connection.basic_nack = False
        self.assertRaises(exceptions.MethodNotImplemented,
                          self.obj.confirm_delivery, logging.debug)

    def test_confirm_delivery_callback_without_nowait_selectok(self):
        self.obj._set_state(self.obj.OPEN)
        expectation = [self.obj.channel_number,
                       spec.Confirm.SelectOk,
                       self.obj._on_selectok]
        self.obj.confirm_delivery(logging.debug)
        self.obj.callbacks.add.assert_called_with(*expectation, arguments=None)

    def test_confirm_delivery_callback_with_nowait(self):
        self.obj._set_state(self.obj.OPEN)
        expectation = [self.obj.channel_number,
                       spec.Confirm.SelectOk,
                       self.obj._on_selectok]
        self.obj.confirm_delivery(logging.debug, True)
        self.assertNotIn(mock.call(*expectation, arguments=None),
                         self.obj.callbacks.add.call_args_list)

    def test_confirm_delivery_callback_basic_ack(self):
        self.obj._set_state(self.obj.OPEN)
        expectation = (self.obj.channel_number,
                       spec.Basic.Ack,
                       logging.debug,
                       False)
        self.obj.confirm_delivery(logging.debug)
        self.obj.callbacks.add.assert_any_call(*expectation)

    def test_confirm_delivery_callback_basic_nack(self):
        self.obj._set_state(self.obj.OPEN)
        expectation = (self.obj.channel_number,
                       spec.Basic.Nack,
                       logging.debug,
                       False)
        self.obj.confirm_delivery(logging.debug)
        self.obj.callbacks.add.assert_any_call(*expectation)

    def test_confirm_delivery_no_callback_callback_call_count(self):
        self.obj._set_state(self.obj.OPEN)
        self.obj.confirm_delivery()
        expectation = [mock.call(*[self.obj.channel_number,
                                   spec.Confirm.SelectOk,
                                   self.obj._on_synchronous_complete],
                                 arguments=None),
                       mock.call(*[self.obj.channel_number,
                                   spec.Confirm.SelectOk,
                                   self.obj._on_selectok,
                                   ], arguments=None)]
        self.assertEqual(self.obj.callbacks.add.call_args_list,
                         expectation)

    def test_confirm_delivery_no_callback_no_basic_ack_callback(self):
        self.obj._set_state(self.obj.OPEN)
        expectation = [self.obj.channel_number,
                       spec.Basic.Ack,
                       None,
                       False]
        self.obj.confirm_delivery()
        self.assertNotIn(mock.call(*expectation),
                         self.obj.callbacks.add.call_args_list)

    def test_confirm_delivery_no_callback_no_basic_nack_callback(self):
        self.obj._set_state(self.obj.OPEN)
        expectation = [self.obj.channel_number,
                       spec.Basic.Nack,
                       None,
                       False]
        self.obj.confirm_delivery()
        self.assertNotIn(mock.call(*expectation),
                         self.obj.callbacks.add.call_args_list)

    def test_consumer_tags(self):
        self.assertListEqual(self.obj.consumer_tags, self.obj._consumers.keys())

    def test_exchange_bind_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed,
                          self.obj.exchange_bind,
                          None, 'foo', 'bar', 'baz')

    def test_exchange_bind_raises_value_error_on_invalid_callback(self):
        self.obj._set_state(self.obj.OPEN)
        self.assertRaises(ValueError,
                          self.obj.exchange_bind,
                          'callback', 'foo', 'bar', 'baz')

    @mock.patch('pika.spec.Exchange.Bind')
    @mock.patch('pika.channel.Channel._rpc')
    def test_exchange_bind_rpc_request(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.exchange_bind(mock_callback, 'foo', 'bar', 'baz')
        rpc.assert_called_once_with(spec.Exchange.Bind(0, 'foo', 'bar', 'baz'),
                                    mock_callback, [spec.Exchange.BindOk])

    @mock.patch('pika.spec.Exchange.Bind')
    @mock.patch('pika.channel.Channel._rpc')
    def test_exchange_bind_rpc_request_nowait(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.exchange_bind(mock_callback, 'foo', 'bar', 'baz', nowait=True)
        rpc.assert_called_once_with(spec.Exchange.Bind(0, 'foo', 'bar', 'baz'),
                                    mock_callback, [])

    def test_exchange_declare_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed,
                          self.obj.exchange_declare,
                          exchange='foo')

    @mock.patch('pika.channel.Channel._rpc')
    def test_exchange_declare_with_type_arg_raises_deprecation_warning(self,
                                                                       _rpc):
        self.obj._set_state(self.obj.OPEN)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            self.obj.exchange_declare(None, 'foo', type='direct')
            self.assertEqual(len(w), 1)
            self.assertIs(w[-1].category, DeprecationWarning)

    @mock.patch('pika.spec.Exchange.Declare')
    @mock.patch('pika.channel.Channel._rpc')
    def test_exchange_declare_with_type_arg_assigns_to_exchange_type(self, rpc,
                                                                     unused):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            self.obj._set_state(self.obj.OPEN)
            mock_callback = mock.Mock()
            self.obj.exchange_declare(mock_callback, exchange='foo',
                                      type='topic')
            rpc.assert_called_once_with(spec.Exchange.Declare(0, 'foo',
                                                              'topic'),
                                        mock_callback,
                                        [spec.Exchange.DeclareOk])

    def test_exchange_declare_raises_value_error_on_invalid_callback(self):
        self.obj._set_state(self.obj.OPEN)
        self.assertRaises(ValueError,
                          self.obj.exchange_declare,
                          'callback', 'foo')

    @mock.patch('pika.spec.Exchange.Declare')
    @mock.patch('pika.channel.Channel._rpc')
    def test_exchange_declare_rpc_request(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.exchange_declare(mock_callback, 'foo')
        rpc.assert_called_once_with(spec.Exchange.Declare(0, 'foo'),
                                    mock_callback, [spec.Exchange.DeclareOk])

    @mock.patch('pika.spec.Exchange.Declare')
    @mock.patch('pika.channel.Channel._rpc')
    def test_exchange_declare_rpc_request_nowait(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.exchange_declare(mock_callback, 'foo', nowait=True)
        rpc.assert_called_once_with(spec.Exchange.Declare(0, 'foo'),
                                    mock_callback, [])

    def test_exchange_delete_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed,
                          self.obj.exchange_delete,
                          exchange='foo')

    def test_exchange_delete_raises_value_error_on_invalid_callback(self):
        self.obj._set_state(self.obj.OPEN)
        self.assertRaises(ValueError,
                          self.obj.exchange_delete,
                          'callback', 'foo')

    @mock.patch('pika.spec.Exchange.Delete')
    @mock.patch('pika.channel.Channel._rpc')
    def test_exchange_delete_rpc_request(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.exchange_delete(mock_callback, 'foo')
        rpc.assert_called_once_with(spec.Exchange.Delete(0, 'foo'),
                                    mock_callback, [spec.Exchange.DeleteOk])

    @mock.patch('pika.spec.Exchange.Delete')
    @mock.patch('pika.channel.Channel._rpc')
    def test_exchange_delete_rpc_request_nowait(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.exchange_delete(mock_callback, 'foo', nowait=True)
        rpc.assert_called_once_with(spec.Exchange.Delete(0, 'foo'),
                                    mock_callback, [])

    def test_exchange_unbind_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed,
                          self.obj.exchange_unbind,
                          None, 'foo', 'bar', 'baz')

    def test_exchange_unbind_raises_value_error_on_invalid_callback(self):
        self.obj._set_state(self.obj.OPEN)
        self.assertRaises(ValueError,
                          self.obj.exchange_unbind,
                          'callback', 'foo', 'bar', 'baz')

    @mock.patch('pika.spec.Exchange.Unbind')
    @mock.patch('pika.channel.Channel._rpc')
    def test_exchange_unbind_rpc_request(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.exchange_unbind(mock_callback, 'foo', 'bar', 'baz')
        rpc.assert_called_once_with(spec.Exchange.Unbind(0, 'foo', 'bar', 'baz'),
                                    mock_callback, [spec.Exchange.UnbindOk])

    @mock.patch('pika.spec.Exchange.Unbind')
    @mock.patch('pika.channel.Channel._rpc')
    def test_exchange_unbind_rpc_request_nowait(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.exchange_unbind(mock_callback, 'foo', 'bar', 'baz',
                                 nowait=True)
        rpc.assert_called_once_with(spec.Exchange.Unbind(0, 'foo', 'bar', 'baz'),
                                    mock_callback, [])

    def test_flow_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed,
                          self.obj.flow, 'foo', True)

    def test_flow_raises_invalid_callback(self):
        self.obj._set_state(self.obj.OPEN)
        self.assertRaises(ValueError, self.obj.flow, 'foo', True)

    @mock.patch('pika.spec.Channel.Flow')
    @mock.patch('pika.channel.Channel._rpc')
    def test_flow_on_rpc_request(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.flow(mock_callback, True)
        rpc.assert_called_once_with(spec.Channel.Flow(True),
                                    self.obj._on_flowok,
                                    [spec.Channel.FlowOk])

    @mock.patch('pika.spec.Channel.Flow')
    @mock.patch('pika.channel.Channel._rpc')
    def test_flow_off_rpc_request(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.flow(mock_callback, False)
        rpc.assert_called_once_with(spec.Channel.Flow(False),
                                    self.obj._on_flowok,
                                    [spec.Channel.FlowOk])

    @mock.patch('pika.channel.Channel._rpc')
    def test_flow_on_flowok_callback(self, rpc):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.flow(mock_callback, True)
        self.assertEqual(self.obj._on_flowok_callback, mock_callback)

    def test_is_closed_true(self):
        self.obj._set_state(self.obj.CLOSED)
        self.assertTrue(self.obj.is_closed)

    def test_is_closed_false(self):
        self.obj._set_state(self.obj.OPEN)
        self.assertFalse(self.obj.is_closed)

    def test_is_closing_true(self):
        self.obj._set_state(self.obj.CLOSING)
        self.assertTrue(self.obj.is_closing)

    def test_is_closing_false(self):
        self.obj._set_state(self.obj.OPEN)
        self.assertFalse(self.obj.is_closing)

    @mock.patch('pika.channel.Channel._rpc')
    def test_channel_open_add_callbacks_called(self, rpc):
        with mock.patch.object(self.obj, '_add_callbacks') as _add_callbacks:
            self.obj.open()
            _add_callbacks.assert_called_once_with()

    def test_queue_bind_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed,
                          self.obj.queue_bind,
                          None, 'foo', 'bar', 'baz')

    def test_queue_bind_raises_value_error_on_invalid_callback(self):
        self.obj._set_state(self.obj.OPEN)
        self.assertRaises(ValueError,
                          self.obj.queue_bind,
                          'callback', 'foo', 'bar', 'baz')

    @mock.patch('pika.spec.Queue.Bind')
    @mock.patch('pika.channel.Channel._rpc')
    def test_queue_bind_rpc_request(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.queue_bind(mock_callback, 'foo', 'bar', 'baz')
        rpc.assert_called_once_with(spec.Queue.Bind(0, 'foo', 'bar', 'baz'),
                                    mock_callback, [spec.Queue.BindOk])

    @mock.patch('pika.spec.Queue.Bind')
    @mock.patch('pika.channel.Channel._rpc')
    def test_queue_bind_rpc_request_nowait(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.queue_bind(mock_callback, 'foo', 'bar', 'baz', nowait=True)
        rpc.assert_called_once_with(spec.Queue.Bind(0, 'foo', 'bar', 'baz'),
                                    mock_callback, [])

    def test_queue_declare_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed,
                          self.obj.queue_declare,
                          None,
                          queue='foo')

    def test_queue_declare_raises_value_error_on_invalid_callback(self):
        self.obj._set_state(self.obj.OPEN)
        self.assertRaises(ValueError,
                          self.obj.queue_declare,
                          'callback', 'foo')

    @mock.patch('pika.spec.Queue.Declare')
    @mock.patch('pika.channel.Channel._rpc')
    def test_queue_declare_rpc_request(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.queue_declare(mock_callback, 'foo')
        rpc.assert_called_once_with(spec.Queue.Declare(0, 'foo'),
                                    mock_callback, [(spec.Queue.DeclareOk,
                                                     {'queue': 'foo'})])

    @mock.patch('pika.spec.Queue.Declare')
    @mock.patch('pika.channel.Channel._rpc')
    def test_queue_declare_rpc_request_nowait(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.queue_declare(mock_callback, 'foo', nowait=True)
        rpc.assert_called_once_with(spec.Queue.Declare(0, 'foo'),
                                    mock_callback, [])

    def test_queue_delete_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed,
                          self.obj.queue_delete,
                          queue='foo')

    def test_queue_delete_raises_value_error_on_invalid_callback(self):
        self.obj._set_state(self.obj.OPEN)
        self.assertRaises(ValueError,
                          self.obj.queue_delete,
                          'callback', 'foo')

    @mock.patch('pika.spec.Queue.Delete')
    @mock.patch('pika.channel.Channel._rpc')
    def test_queue_delete_rpc_request(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.queue_delete(mock_callback, 'foo')
        rpc.assert_called_once_with(spec.Queue.Delete(0, 'foo'),
                                    mock_callback, [spec.Queue.DeleteOk])

    @mock.patch('pika.spec.Queue.Delete')
    @mock.patch('pika.channel.Channel._rpc')
    def test_queue_delete_rpc_request_nowait(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.queue_delete(mock_callback, 'foo', nowait=True)
        rpc.assert_called_once_with(spec.Queue.Delete(0, 'foo'),
                                    mock_callback, [])

    def test_queue_purge_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed,
                          self.obj.queue_purge,
                          queue='foo')

    def test_queue_purge_raises_value_error_on_invalid_callback(self):
        self.obj._set_state(self.obj.OPEN)
        self.assertRaises(ValueError,
                          self.obj.queue_purge,
                          'callback', 'foo')

    @mock.patch('pika.spec.Queue.Purge')
    @mock.patch('pika.channel.Channel._rpc')
    def test_queue_purge_rpc_request(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.queue_purge(mock_callback, 'foo')
        rpc.assert_called_once_with(spec.Queue.Purge(0, 'foo'),
                                    mock_callback, [spec.Queue.PurgeOk])

    @mock.patch('pika.spec.Queue.Purge')
    @mock.patch('pika.channel.Channel._rpc')
    def test_queue_purge_rpc_request_nowait(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.queue_purge(mock_callback, 'foo', nowait=True)
        rpc.assert_called_once_with(spec.Queue.Purge(0, 'foo'),
                                    mock_callback, [])

    def test_queue_unbind_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed,
                          self.obj.queue_unbind,
                          None, 'foo', 'bar', 'baz')

    def test_queue_unbind_raises_value_error_on_invalid_callback(self):
        self.obj._set_state(self.obj.OPEN)
        self.assertRaises(ValueError,
                          self.obj.queue_unbind,
                          'callback', 'foo', 'bar', 'baz')

    @mock.patch('pika.spec.Queue.Unbind')
    @mock.patch('pika.channel.Channel._rpc')
    def test_queue_unbind_rpc_request(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.queue_unbind(mock_callback, 'foo', 'bar', 'baz')
        rpc.assert_called_once_with(spec.Queue.Unbind(0, 'foo', 'bar', 'baz'),
                                    mock_callback, [spec.Queue.UnbindOk])

    def test_tx_commit_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed, self.obj.tx_commit, None)

    @mock.patch('pika.spec.Tx.Commit')
    @mock.patch('pika.channel.Channel._rpc')
    def test_tx_commit_rpc_request(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.tx_commit(mock_callback)
        rpc.assert_called_once_with(spec.Tx.Commit(mock_callback),
                                    mock_callback, [spec.Tx.CommitOk])

    @mock.patch('pika.spec.Tx.Rollback')
    @mock.patch('pika.channel.Channel._rpc')
    def test_tx_rollback_rpc_request(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.tx_rollback(mock_callback)
        rpc.assert_called_once_with(spec.Tx.Rollback(mock_callback),
                                    mock_callback, [spec.Tx.RollbackOk])

    @mock.patch('pika.spec.Tx.Select')
    @mock.patch('pika.channel.Channel._rpc')
    def test_tx_select_rpc_request(self, rpc, unused):
        self.obj._set_state(self.obj.OPEN)
        mock_callback = mock.Mock()
        self.obj.tx_select(mock_callback)
        rpc.assert_called_once_with(spec.Tx.Select(mock_callback),
                                    mock_callback, [spec.Tx.SelectOk])

    # Test internal methods

    def test_add_callbacks_basic_cancel_empty_added(self):
        self.obj._add_callbacks()
        self.obj.callbacks.add.assert_any_calls(self.obj.channel_number,
                                                spec.Basic.Cancel,
                                                self.obj._on_getempty,
                                                False)

    def test_add_callbacks_basic_get_empty_added(self):
        self.obj._add_callbacks()
        self.obj.callbacks.add.assert_any_calls(self.obj.channel_number,
                                                spec.Basic.GetEmpty,
                                                self.obj._on_getempty,
                                                False)

    def test_add_callbacks_channel_close_added(self):
        self.obj._add_callbacks()
        self.obj.callbacks.add.assert_any_calls(self.obj.channel_number,
                                                spec.Channel.Close,
                                                self.obj._on_getempty,
                                                False)

    def test_add_callbacks_channel_flow_added(self):
        self.obj._add_callbacks()
        self.obj.callbacks.add.assert_any_calls(self.obj.channel_number,
                                                spec.Channel.Flow,
                                                self.obj._on_getempty,
                                                False)

    def test_cleanup(self):
        self.obj._cleanup()
        self.obj.callbacks.cleanup.assert_called_once_with(str(self.obj.channel_number))

    def test_get_pending_message(self):
        key = 'foo'
        expectation = 'abc1234'
        self.obj._pending = {key: [expectation]}
        self.assertEqual(self.obj._get_pending_msg(key), expectation)

    def test_get_pending_message_item_popped(self):
        key = 'foo'
        expectation = 'abc1234'
        self.obj._pending = {key: [expectation]}
        self.obj._get_pending_msg(key)
        self.assertEqual(len(self.obj._pending[key]), 0)

    def test_handle_content_frame_method_returns_none(self):
        frame_value = frame.Method(1, spec.Basic.Deliver('ctag0', 1))
        self.assertEqual(self.obj._handle_content_frame(frame_value), None)

    def test_handle_content_frame_sets_method_frame(self):
        frame_value = frame.Method(1, spec.Basic.Deliver('ctag0', 1))
        self.obj._handle_content_frame(frame_value)
        self.assertEqual(self.obj.frame_dispatcher._method_frame, frame_value)

    def test_handle_content_frame_sets_header_frame(self):
        frame_value = frame.Header(1, 10, spec.BasicProperties())
        self.obj._handle_content_frame(frame_value)
        self.assertEqual(self.obj.frame_dispatcher._header_frame, frame_value)

    def test_handle_content_frame_basic_deliver_called(self):
        method_value = frame.Method(1, spec.Basic.Deliver('ctag0', 1))
        self.obj._handle_content_frame(method_value)
        header_value = frame.Header(1, 10, spec.BasicProperties())
        self.obj._handle_content_frame(header_value)
        body_value = frame.Body(1, '0123456789')
        with mock.patch.object(self.obj, '_on_deliver') as deliver:
            self.obj._handle_content_frame(body_value)
            deliver.assert_called_once_with(method_value, header_value,
                                            '0123456789')

    def test_handle_content_frame_basic_get_called(self):
        method_value = frame.Method(1, spec.Basic.GetOk('ctag0', 1))
        self.obj._handle_content_frame(method_value)
        header_value = frame.Header(1, 10, spec.BasicProperties())
        self.obj._handle_content_frame(header_value)
        body_value = frame.Body(1, '0123456789')
        with mock.patch.object(self.obj, '_on_getok') as getok:
            self.obj._handle_content_frame(body_value)
            getok.assert_called_once_with(method_value, header_value,
                                          '0123456789')

    def test_handle_content_frame_basic_return_called(self):
        method_value = frame.Method(1, spec.Basic.Return(999, 'Reply Text',
                                                         'exchange_value',
                                                         'routing.key'))
        self.obj._handle_content_frame(method_value)
        header_value = frame.Header(1, 10, spec.BasicProperties())
        self.obj._handle_content_frame(header_value)
        body_value = frame.Body(1, '0123456789')
        with mock.patch.object(self.obj, '_on_return') as basic_return:
            self.obj._handle_content_frame(body_value)
            basic_return.assert_called_once_with(method_value, header_value,
                                                 '0123456789')

    def test_has_content_true(self):
        self.assertTrue(self.obj._has_content(spec.Basic.GetOk))

    def test_has_content_false(self):
        self.assertFalse(self.obj._has_content(spec.Basic.Ack))

    def test_on_cancel_appended_cancelled(self):
        consumer_tag = 'ctag0'
        frame_value = frame.Method(1, spec.Basic.Cancel(consumer_tag))
        self.obj._on_cancel(frame_value)
        self.assertIn(consumer_tag, self.obj._cancelled)

    def test_on_cancel_removed_consumer(self):
        consumer_tag = 'ctag0'
        self.obj._consumers[consumer_tag] = logging.debug
        frame_value = frame.Method(1, spec.Basic.Cancel(consumer_tag))
        self.obj._on_cancel(frame_value)
        self.assertNotIn(consumer_tag, self.obj._consumers)


    def test_on_cancelok_removed_consumer(self):
        consumer_tag = 'ctag0'
        self.obj._consumers[consumer_tag] = logging.debug
        frame_value = frame.Method(1, spec.Basic.CancelOk(consumer_tag))
        self.obj._on_cancelok(frame_value)
        self.assertNotIn(consumer_tag, self.obj._consumers)

    def test_on_cancelok_removed_pending(self):
        consumer_tag = 'ctag0'
        self.obj._pending[consumer_tag] = logging.debug
        frame_value = frame.Method(1, spec.Basic.CancelOk(consumer_tag))
        self.obj._on_cancelok(frame_value)
        self.assertNotIn(consumer_tag, self.obj._pending)

    def test_on_deliver_pending_called(self):
        self.obj._set_state(self.obj.OPEN)
        consumer_tag = 'ctag0'
        mock_callback = mock.Mock()
        self.obj._pending[consumer_tag] = mock_callback
        method_value = frame.Method(1, spec.Basic.Deliver(consumer_tag, 1))
        header_value = frame.Header(1, 10, spec.BasicProperties())
        body_value = '0123456789'
        with mock.patch.object(self.obj, '_add_pending_msg') as add_pending:
            self.obj._on_deliver(method_value, header_value, body_value)
            add_pending.assert_called_with(consumer_tag, method_value,
                                           header_value, body_value)

    def test_on_deliver_callback_called(self):
        self.obj._set_state(self.obj.OPEN)
        consumer_tag = 'ctag0'
        mock_callback = mock.Mock()
        self.obj._pending[consumer_tag] = list()
        self.obj._consumers[consumer_tag] = mock_callback
        method_value = frame.Method(1, spec.Basic.Deliver(consumer_tag, 1))
        header_value = frame.Header(1, 10, spec.BasicProperties())
        body_value = '0123456789'
        self.obj._on_deliver(method_value, header_value, body_value)
        mock_callback.assert_called_with(self.obj, method_value.method,
                                         header_value.properties, body_value)

    def test_on_deliver_pending_callbacks_called(self):
        self.obj._set_state(self.obj.OPEN)
        consumer_tag = 'ctag0'
        mock_callback = mock.Mock()
        self.obj._pending[consumer_tag] = list()
        method_value = frame.Method(1, spec.Basic.Deliver(consumer_tag, 1))
        header_value = frame.Header(1, 10, spec.BasicProperties())
        body_value = '0123456789'
        expectation = [mock.call(self.obj, method_value.method,
                                 header_value.properties, body_value)]

        self.obj._on_deliver(method_value, header_value, body_value)
        self.obj._consumers[consumer_tag] = mock_callback
        method_value = frame.Method(1, spec.Basic.Deliver(consumer_tag, 2))
        header_value = frame.Header(1, 10, spec.BasicProperties())
        body_value = '0123456789'
        self.obj._on_deliver(method_value, header_value, body_value)
        expectation.append(mock.call(self.obj, method_value.method,
                                     header_value.properties, body_value))
        self.assertListEqual(mock_callback.call_args_list, expectation)


    @mock.patch('logging.Logger.debug')
    def test_on_getempty(self, debug):
        method_frame = frame.Method(self.obj.channel_number,
                                    spec.Basic.GetEmpty)
        self.obj._on_getempty(method_frame)
        debug.assert_called_with('Received Basic.GetEmpty: %r', method_frame)

    @mock.patch('logging.Logger.error')
    def test_on_getok_no_callback(self, error):
        method_value = frame.Method(1, spec.Basic.GetOk('ctag0', 1))
        header_value = frame.Header(1, 10, spec.BasicProperties())
        body_value = '0123456789'
        self.obj._on_getok(method_value, header_value, body_value)
        error.assert_called_with('Basic.GetOk received with no active callback')

    def test_on_getok_callback_called(self):
        mock_callback = mock.Mock()
        self.obj._on_getok_callback = mock_callback
        method_value = frame.Method(1, spec.Basic.GetOk('ctag0', 1))
        header_value = frame.Header(1, 10, spec.BasicProperties())
        body_value = '0123456789'
        self.obj._on_getok(method_value, header_value, body_value)
        mock_callback.assert_called_once_with(self.obj,
                                              method_value.method,
                                              header_value.properties,
                                              body_value)

    def test_on_getok_callback_reset(self):
        mock_callback = mock.Mock()
        self.obj._on_getok_callback = mock_callback
        method_value = frame.Method(1, spec.Basic.GetOk('ctag0', 1))
        header_value = frame.Header(1, 10, spec.BasicProperties())
        body_value = '0123456789'
        self.obj._on_getok(method_value, header_value, body_value)
        self.assertIsNone(self.obj._on_getok_callback)

    @mock.patch('logging.Logger.debug')
    def test_on_confirm_selectok(self, debug):
        method_frame = frame.Method(self.obj.channel_number,
                                    spec.Confirm.SelectOk())
        self.obj._on_selectok(method_frame)
        debug.assert_called_with('Confirm.SelectOk Received: %r', method_frame)

    @mock.patch('logging.Logger.debug')
    def test_on_eventok(self, debug):
        method_frame = frame.Method(self.obj.channel_number,
                                    spec.Basic.GetEmpty())
        self.obj._on_eventok(method_frame)
        debug.assert_called_with('Discarding frame %r', method_frame)

    @mock.patch('logging.Logger.warning')
    def test_on_flow(self, warning):
        self.obj._has_on_flow_callback = False
        method_frame = frame.Method(self.obj.channel_number,
                                    spec.Channel.Flow())
        self.obj._on_flow(method_frame)
        warning.assert_called_with('Channel.Flow received from server')

    @mock.patch('logging.Logger.warning')
    def test_on_flow_with_callback(self, warning):
        method_frame = frame.Method(self.obj.channel_number,
                                    spec.Channel.Flow())
        self.obj._on_flowok_callback = logging.debug
        self.obj._on_flow(method_frame)
        self.assertEqual(len(warning.call_args_list), 1)

    @mock.patch('logging.Logger.warning')
    def test_on_flowok(self, warning):
        method_frame = frame.Method(self.obj.channel_number,
                                    spec.Channel.FlowOk())
        self.obj._on_flowok(method_frame)
        warning.assert_called_with('Channel.FlowOk received with no active '
                                   'callbacks')

    def test_on_flowok_calls_callback(self):
        method_frame = frame.Method(self.obj.channel_number,
                                    spec.Channel.FlowOk())
        mock_callback = mock.Mock()
        self.obj._on_flowok_callback = mock_callback
        self.obj._on_flowok(method_frame)
        mock_callback.assert_called_once_with(method_frame.method.active)

    def test_on_flowok_callback_reset(self):
        method_frame = frame.Method(self.obj.channel_number,
                                    spec.Channel.FlowOk())
        mock_callback = mock.Mock()
        self.obj._on_flowok_callback = mock_callback
        self.obj._on_flowok(method_frame)
        self.assertIsNone(self.obj._on_flowok_callback)

    def test_on_openok_no_callback(self):
        mock_callback = mock.Mock()
        self.obj._on_openok_callback = None
        method_value = frame.Method(1, spec.Channel.OpenOk())
        self.obj._on_openok(method_value)
        self.assertEqual(self.obj._state, self.obj.OPEN)

    def test_on_openok_callback_called(self):
        mock_callback = mock.Mock()
        self.obj._on_openok_callback = mock_callback
        method_value = frame.Method(1, spec.Channel.OpenOk())
        self.obj._on_openok(method_value)
        mock_callback.assert_called_once_with(self.obj)

    def test_onreturn(self):
        method_value = frame.Method(1, spec.Basic.Return(999, 'Reply Text',
                                                         'exchange_value',
                                                         'routing.key'))
        header_value = frame.Header(1, 10, spec.BasicProperties())
        body_value = frame.Body(1, '0123456789')
        self.obj._on_return(method_value, header_value, body_value)
        self.obj.callbacks.process.assert_called_with(self.obj.channel_number,
                                                      '_on_return',
                                                      self.obj,
                                                      (self.obj,
                                                       method_value.method,
                                                       header_value.properties,
                                                       body_value))

    @mock.patch('logging.Logger.warning')
    def test_onreturn_warning(self, warning):
        method_value = frame.Method(1, spec.Basic.Return(999, 'Reply Text',
                                                         'exchange_value',
                                                         'routing.key'))
        header_value = frame.Header(1, 10, spec.BasicProperties())
        body_value = frame.Body(1, '0123456789')
        self.obj.callbacks.process.return_value = False
        self.obj._on_return(method_value, header_value, body_value)
        warning.assert_called_with('Basic.Return received from server (%r, %r)',
                                   method_value.method, header_value.properties)

    @mock.patch('pika.channel.Channel._rpc')
    def test_on_synchronous_complete(self, rpc):
        mock_callback = mock.Mock()
        expectation = [spec.Queue.Unbind(0, 'foo', 'bar', 'baz'),
                       mock_callback, [spec.Queue.UnbindOk]]
        self.obj._blocked = collections.deque([expectation])
        self.obj._on_synchronous_complete(frame.Method(self.obj.channel_number,
                                                       spec.Basic.Ack(1)))
        rpc.assert_called_once_with(*expectation)

    def test_rpc_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed,
                          self.obj._rpc,
                          frame.Method(self.obj.channel_number,
                                       spec.Basic.Ack(1)))

    def test_rpc_while_blocking_appends_blocked_collection(self):
        self.obj._set_state(self.obj.OPEN)
        self.obj._blocking = spec.Confirm.Select()
        expectation = [frame.Method(self.obj.channel_number, spec.Basic.Ack(1)),
                       'Foo', None]
        self.obj._rpc(*expectation)
        self.assertIn(expectation, self.obj._blocked)

    def test_rpc_throws_value_error_with_unacceptable_replies(self):
        self.obj._set_state(self.obj.OPEN)
        self.assertRaises(TypeError, self.obj._rpc, spec.Basic.Ack(1),
                          logging.debug, 'Foo')

    def test_rpc_throws_type_error_with_invalid_callback(self):
        self.obj._set_state(self.obj.OPEN)
        self.assertRaises(TypeError, self.obj._rpc, spec.Channel.Open(1),
                          ['foo'], [spec.Channel.OpenOk])

    def test_rpc_adds_on_synchronous_complete(self):
        self.obj._set_state(self.obj.OPEN)
        method_frame = spec.Channel.Open()
        self.obj._rpc(method_frame, None, [spec.Channel.OpenOk])
        self.obj.callbacks.add.assert_called_with(self.obj.channel_number,
                                                  spec.Channel.OpenOk,
                                                  self.obj._on_synchronous_complete,
                                                  arguments=None)

    def test_rpc_adds_callback(self):
        self.obj._set_state(self.obj.OPEN)
        method_frame = spec.Channel.Open()
        mock_callback = mock.Mock()
        self.obj._rpc(method_frame, mock_callback, [spec.Channel.OpenOk])
        self.obj.callbacks.add.assert_called_with(self.obj.channel_number,
                                                  spec.Channel.OpenOk,
                                                  mock_callback,
                                                  arguments=None)

    def test_send_method(self):
        expectation = [2, 3]
        with mock.patch.object(self.obj.connection,
                               '_send_method') as send_method:
            self.obj._send_method(*expectation)
            send_method.assert_called_once_with(*[self.obj.channel_number] +
                                                 expectation)

    def test_set_state(self):
        self.obj._state = channel.Channel.CLOSED
        self.obj._set_state(channel.Channel.OPENING)
        self.assertEqual(self.obj._state, channel.Channel.OPENING)

    def test_validate_channel_and_callback_raises_channel_closed(self):
        self.assertRaises(exceptions.ChannelClosed,
                          self.obj._validate_channel_and_callback,
                          None)

    def test_validate_channel_and_callback_raises_value_error_not_callable(self):
        self.obj._set_state(self.obj.OPEN)
        self.assertRaises(ValueError, self.obj._validate_channel_and_callback,
                          'foo')

    @mock.patch('logging.Logger.warning')
    def test_on_close_warning(self, warning):
        method_frame = frame.Method(self.obj.channel_number,
                                    spec.Channel.Close(999, 'Test_Value'))
        self.obj._on_close(method_frame)
        warning.assert_called_with('Received remote Channel.Close (%s): %s',
                                   method_frame.method.reply_code,
                                   method_frame.method.reply_text)

########NEW FILE########
__FILENAME__ = connection_tests
"""
Tests for pika.connection.Connection

"""
import mock
import random
import urllib
import copy
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from pika import connection
from pika import channel
from pika import credentials
from pika import frame
from pika import spec


def callback_method():
    """Callback method to use in tests"""
    pass


class ConnectionTests(unittest.TestCase):

    @mock.patch('pika.connection.Connection.connect')
    def setUp(self, connect):
        self.connection = connection.Connection()
        self.channel = mock.Mock(spec=channel.Channel)
        self.channel.is_open = True
        self.connection._channels[1] = self.channel
        self.connection._set_connection_state(connection.Connection.CONNECTION_OPEN)

    def tearDown(self):
        del self.connection
        del self.channel

    @mock.patch('pika.connection.Connection._send_connection_close')
    def test_close_closes_open_channels(self, send_connection_close):
        self.connection.close()
        self.channel.close.assert_called_once_with(200, 'Normal shutdown')

    @mock.patch('pika.connection.Connection._send_connection_close')
    def test_close_ignores_closed_channels(self, send_connection_close):
        for closed_state in (self.connection.CONNECTION_CLOSED,
                self.connection.CONNECTION_CLOSING):
            self.connection.connection_state = closed_state
            self.connection.close()
            self.assertFalse(self.channel.close.called)

    @mock.patch('pika.connection.Connection._on_close_ready')
    def test_on_close_ready_open_channels(self, on_close_ready):
        """if open channels _on_close_ready shouldn't be called"""
        self.connection.close()
        self.assertFalse(on_close_ready.called,
                         '_on_close_ready should not have been called')

    @mock.patch('pika.connection.Connection._on_close_ready')
    def test_on_close_ready_no_open_channels(self, on_close_ready):
        self.connection._channels = dict()
        self.connection.close()
        self.assertTrue(on_close_ready.called,
                        '_on_close_ready should have been called')

    @mock.patch('pika.connection.Connection._on_close_ready')
    def test_on_channel_closeok_no_open_channels(self, on_close_ready):
        """Should call _on_close_ready if connection is closing and there are
        no open channels

        """
        self.connection._channels = dict()
        self.connection.close()
        self.assertTrue(on_close_ready.called,
                        '_on_close_ready should been called')

    @mock.patch('pika.connection.Connection._on_close_ready')
    def test_on_channel_closeok_open_channels(self, on_close_ready):
        """if connection is closing but channels remain open do not call
        _on_close_ready

        """
        self.connection.close()
        self.assertFalse(on_close_ready.called,
                         '_on_close_ready should not have been called')

    @mock.patch('pika.connection.Connection._on_close_ready')
    def test_on_channel_closeok_non_closing_state(self, on_close_ready):
        """if connection isn't closing _on_close_ready should not be called"""
        self.connection._on_channel_closeok(mock.Mock())
        self.assertFalse(on_close_ready.called,
                         '_on_close_ready should not have been called')

    def test_on_disconnect(self):
        """if connection isn't closing _on_close_ready should not be called"""
        self.connection._on_disconnect(0, 'Undefined')
        self.assertTrue(self.channel._on_close.called,
                        'channel._on_close should have been called')
        method_frame = self.channel._on_close.call_args[0][0]
        self.assertEqual(method_frame.method.reply_code, 0)
        self.assertEqual(method_frame.method.reply_text, 'Undefined')

    @mock.patch('pika.connection.Connection.connect')
    def test_new_conn_should_use_first_channel(self, connect):
        """_next_channel_number in new conn should always be 1"""
        conn = connection.Connection()
        self.assertEqual(1, conn._next_channel_number())

    def test_next_channel_number_returns_lowest_unused(self):
        """_next_channel_number must return lowest available channel number"""
        for channel_num in xrange(1, 50):
            self.connection._channels[channel_num] = True
        expectation = random.randint(5, 50)
        del self.connection._channels[expectation]
        self.assertEqual(self.connection._next_channel_number(),
                         expectation)

    def test_add_callbacks(self):
        """make sure the callback adding works"""
        self.connection.callbacks = mock.Mock(spec=self.connection.callbacks)
        for test_method, expected_key in (
                (self.connection.add_backpressure_callback,
                 self.connection.ON_CONNECTION_BACKPRESSURE),
                (self.connection.add_on_open_callback,
                 self.connection.ON_CONNECTION_OPEN),
                (self.connection.add_on_close_callback,
                 self.connection.ON_CONNECTION_CLOSED)
                ):
            self.connection.callbacks.reset_mock()
            test_method(callback_method)
            self.connection.callbacks.add.assert_called_once_with(0,
                expected_key, callback_method, False)

    def test_add_on_close_callback(self):
        """make sure the add on close callback is added"""
        self.connection.callbacks = mock.Mock(spec=self.connection.callbacks)
        self.connection.add_on_open_callback(callback_method)
        self.connection.callbacks.add.assert_called_once_with(0,
            self.connection.ON_CONNECTION_OPEN, callback_method, False)

    def test_add_on_open_error_callback(self):
        """make sure the add on open error callback is added"""
        self.connection.callbacks = mock.Mock(spec=self.connection.callbacks)
        #Test with remove default first (also checks default is True)
        self.connection.add_on_open_error_callback(callback_method)
        self.connection.callbacks.remove.assert_called_once_with(
            0, self.connection.ON_CONNECTION_ERROR,
            self.connection._on_connection_error)
        self.connection.callbacks.add.assert_called_once_with(0,
            self.connection.ON_CONNECTION_ERROR, callback_method,
            False)

    def test_channel(self):
        """test the channel method"""
        self.connection._next_channel_number = mock.Mock(return_value=42)
        test_channel = mock.Mock(spec=channel.Channel)
        self.connection._create_channel = mock.Mock(return_value=test_channel)
        self.connection._add_channel_callbacks = mock.Mock()
        ret_channel = self.connection.channel(callback_method)
        self.assertEqual(test_channel, ret_channel)
        self.connection._create_channel.assert_called_once_with(42,
                                                                callback_method)
        self.connection._add_channel_callbacks.assert_called_once_with(42)
        test_channel.open.assert_called_once_with()

    def test_process_url(self):
        """test for the different query stings checked by process url"""
        url_params = {
            'backpressure_detection': None,
            'channel_max': 1,
            'connection_attempts': 2,
            'frame_max': 30000,
            'heartbeat_interval': 4,
            'locale': 'en',
            'retry_delay': 5,
            'socket_timeout': 6,
            'ssl_options': {'ssl': 'dict'}
        }
        for backpressure in ('t', 'f'):
            test_params = copy.deepcopy(url_params)
            test_params['backpressure_detection'] = backpressure
            query_string = urllib.urlencode(test_params)
            test_url = 'https://www.test.com?%s' % query_string
            params = connection.URLParameters(test_url)
            #check each value
            for t_param in ('channel_max', 'connection_attempts', 'frame_max',
                    'locale', 'retry_delay', 'socket_timeout', 'ssl_options'):
                self.assertEqual(test_params[t_param],
                                 getattr(params, t_param), t_param)
            self.assertEqual(params.backpressure_detection,
                             backpressure == 't')
            self.assertEqual(test_params['heartbeat_interval'],
                             params.heartbeat)

    def test_good_connection_parameters(self):
        """make sure connection kwargs get set correctly"""
        kwargs = {
            'host': 'https://www.test.com',
            'port': 5678,
            'virtual_host': u'vvhost',
            'channel_max': 3,
            'frame_max': 40000,
            'credentials': credentials.PlainCredentials('very', 'secure'),
            'heartbeat_interval': 7,
            'backpressure_detection': False,
            'retry_delay': 3,
            'ssl': True,
            'connection_attempts': 2,
            'locale': 'en',
            'ssl_options': {'ssl': 'options'}
        }
        conn = connection.ConnectionParameters(**kwargs)
        #check values
        for t_param in ('host', 'port', 'virtual_host', 'channel_max',
                'frame_max', 'backpressure_detection', 'ssl',
                'credentials', 'retry_delay', 'connection_attempts',
                'locale'):
            self.assertEqual(kwargs[t_param], getattr(conn, t_param), t_param)
        self.assertEqual(kwargs['heartbeat_interval'], conn.heartbeat)

    def test_bad_type_connection_parameters(self):
        """test connection kwargs type checks throw errors for bad input"""
        kwargs = {
            'host': 'https://www.test.com',
            'port': 5678,
            'virtual_host': 'vvhost',
            'channel_max': 3,
            'frame_max': 40000,
            'heartbeat_interval': 7,
            'backpressure_detection': False,
            'ssl': True
        }
        #Test Type Errors
        for bad_field, bad_value in (
                ('host', 15672) ,
                ('port', '5672'),
                ('virtual_host', True),
                ('channel_max', '4'),
                ('frame_max', '5'),
                ('credentials', 'bad'),
                ('locale', 1),
                ('heartbeat_interval', '6'),
                ('socket_timeout', '42'),
                ('retry_delay', 'two'),
                ('backpressure_detection', 'true'),
                ('ssl', {'ssl': 'dict'}),
                ('ssl_options', True),
                ('connection_attempts', 'hello')
                ):
            bkwargs = copy.deepcopy(kwargs)
            bkwargs[bad_field] = bad_value
            self.assertRaises(TypeError, connection.ConnectionParameters,
                              **bkwargs)

    @mock.patch('pika.frame.ProtocolHeader')
    def test_connect(self, frame_protocol_header):
        """make sure the connect method sets the state and sends a frame"""
        self.connection._adapter_connect = mock.Mock(return_value=None)
        self.connection._send_frame = mock.Mock()
        frame_protocol_header.spec = frame.ProtocolHeader
        frame_protocol_header.return_value = 'frame object'
        self.connection.connect()
        self.assertEqual(self.connection.CONNECTION_PROTOCOL,
                         self.connection.connection_state)
        self.connection._send_frame.assert_called_once_with('frame object')

    def test_connect_reconnect(self):
        """try the different reconnect logic, check state & other class vars"""
        self.connection._adapter_connect = mock.Mock(return_value='error')
        self.connection.callbacks = mock.Mock(spec=self.connection.callbacks)
        self.connection.remaining_connection_attempts = 2
        self.connection.params.retry_delay = 555
        self.connection.params.connection_attempts = 99
        self.connection.add_timeout = mock.Mock()
        #first failure
        self.connection.connect()
        self.connection.add_timeout.assert_called_once_with(555,
            self.connection.connect)
        self.assertEqual(1, self.connection.remaining_connection_attempts)
        self.assertFalse(self.connection.callbacks.process.called)
        self.assertEqual(self.connection.CONNECTION_INIT,
                         self.connection.connection_state)
        #fail with no attempts remaining
        self.connection.add_timeout.reset_mock()
        self.connection.connect()
        self.assertFalse(self.connection.add_timeout.called)
        self.assertEqual(99, self.connection.remaining_connection_attempts)
        self.connection.callbacks.process.assert_called_once_with(0,
            self.connection.ON_CONNECTION_ERROR, self.connection,
            self.connection, 'error')
        self.assertEqual(self.connection.CONNECTION_CLOSED,
                         self.connection.connection_state)

    def test_client_properties(self):
        """make sure client properties has some important keys"""
        client_props = self.connection._client_properties
        self.assertTrue(isinstance(client_props, dict))
        for required_key in ('product', 'platform', 'capabilities',
                'information', 'version'):
            self.assertTrue(required_key in client_props,
                            '%s missing' % required_key)

    def test_set_backpressure_multiplier(self):
        """test setting the backpressure multiplier"""
        self.connection._backpressure = None
        self.connection.set_backpressure_multiplier(value=5)
        self.assertEqual(5, self.connection._backpressure)

    def test_close_channels(self):
        """test closing all channels"""
        self.connection.connection_state = self.connection.CONNECTION_OPEN
        self.connection.callbacks = mock.Mock(spec=self.connection.callbacks)
        open_channel = mock.Mock(is_open=True)
        closed_channel = mock.Mock(is_open=False)
        self.connection._channels = {
            'oc': open_channel,
            'cc': closed_channel
        }
        self.connection._close_channels('reply code', 'reply text')
        open_channel.close.assert_called_once_with('reply code', 'reply text')
        self.assertTrue('oc' in self.connection._channels)
        self.assertTrue('cc' not in self.connection._channels)
        self.connection.callbacks.cleanup.assert_called_once_with('cc')
        #Test on closed channel
        self.connection.connection_state = self.connection.CONNECTION_CLOSED
        self.connection._close_channels('reply code', 'reply text')
        self.assertEqual({}, self.connection._channels)

    def test_on_connection_start(self):
        """make sure starting a connection sets the correct class vars"""
        method_frame = mock.Mock()
        method_frame.method = mock.Mock()
        method_frame.method.mechanisms = str(credentials.PlainCredentials.TYPE)
        method_frame.method.version_major = 0
        method_frame.method.version_minor = 9
        #This may be incorrectly mocked, or the code is wrong
        #TODO: Code does hasattr check, should this be a has_key/in check?
        method_frame.method.server_properties = {
            'capabilities': {
                'basic.nack': True,
                'consumer_cancel_notify': False,
                'exchange_exchange_bindings': False
            }
        }
        #This will be called, but shoudl not be implmented here, just mock it
        self.connection._flush_outbound = mock.Mock()
        self.connection._on_connection_start(method_frame)
        self.assertEqual(True, self.connection.basic_nack)
        self.assertEqual(False, self.connection.consumer_cancel_notify)
        self.assertEqual(False, self.connection.exchange_exchange_bindings)
        self.assertEqual(False, self.connection.publisher_confirms)

    @mock.patch('pika.heartbeat.HeartbeatChecker')
    @mock.patch('pika.frame.Method')
    def test_on_connection_tune(self, method, heartbeat_checker):
        """make sure on connection tune turns the connection params"""
        heartbeat_checker.return_value = 'hearbeat obj'
        self.connection._flush_outbound = mock.Mock()
        marshal = mock.Mock(return_value='ab')
        method.return_value = mock.Mock(marshal=marshal)
        #may be good to test this here, but i don't want to test too much
        self.connection._rpc = mock.Mock()
        method_frame = mock.Mock()
        method_frame.method = mock.Mock()
        method_frame.method.channel_max = 40
        method_frame.method.frame_max = 10
        method_frame.method.heartbeat = 0
        self.connection.params.channel_max = 20
        self.connection.params.frame_max = 20
        self.connection.params.heartbeat = 20
        #Test
        self.connection._on_connection_tune(method_frame)
        #verfy
        self.assertEqual(self.connection.CONNECTION_TUNE,
                         self.connection.connection_state)
        self.assertEqual(20, self.connection.params.channel_max)
        self.assertEqual(10, self.connection.params.frame_max)
        self.assertEqual(20, self.connection.params.heartbeat)
        self.assertEqual(2, self.connection._body_max_length)
        heartbeat_checker.assert_called_once_with(self.connection, 20)
        self.assertEqual(['ab'], list(self.connection.outbound_buffer))
        self.assertEqual('hearbeat obj', self.connection.heartbeat)

    def test_on_connection_closed(self):
        """make sure connection close sends correct frames"""
        method_frame = mock.Mock()
        method_frame.method = mock.Mock(spec=spec.Connection.Close)
        method_frame.method.reply_code = 1
        method_frame.method.reply_text = 'hello'
        self.connection.heartbeat = mock.Mock()
        self.connection._adapter_disconnect = mock.Mock()
        self.connection._on_connection_closed(method_frame, from_adapter=False)
        #Check
        self.assertTupleEqual((1, 'hello'), self.connection.closing)
        self.connection.heartbeat.stop.assert_called_once_with()
        self.connection._adapter_disconnect.assert_called_once_with()

    @mock.patch('pika.frame.decode_frame')
    def test_on_data_available(self, decode_frame):
        """test on data available and process frame"""
        data_in = ['data']
        self.connection._frame_buffer = ['old_data']
        for frame_type in (frame.Method, spec.Basic.Deliver, frame.Heartbeat):
            frame_value = mock.Mock(spec=frame_type)
            frame_value.frame_type = 2
            frame_value.method = 2
            frame_value.channel_number = 1
            self.connection.bytes_received = 0
            self.connection.heartbeat = mock.Mock()
            self.connection.frames_received = 0
            decode_frame.return_value = (2, frame_value)
            self.connection._on_data_available(data_in)
            #test value
            self.assertListEqual([], self.connection._frame_buffer)
            self.assertEqual(2, self.connection.bytes_received)
            self.assertEqual(1, self.connection.frames_received)
            if frame_type == frame.Heartbeat:
                self.assertTrue(self.connection.heartbeat.received.called)


########NEW FILE########
__FILENAME__ = connection_timeout_tests
# -*- coding: utf8 -*-
"""
Tests for connection parameters.

"""
import socket
from mock import patch
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import pika
from pika.adapters import asyncore_connection
from pika.adapters import base_connection
from pika.adapters import blocking_connection
from pika.adapters import select_connection
try:
    from pika.adapters import tornado_connection
except ImportError:
    tornado_connection = None
try:
    from pika.adapters import twisted_connection
except ImportError:
    twisted_connection = None
try:
    from pika.adapters import libev_connection
except ImportError:
    libev_connection = None

from pika import exceptions


def mock_timeout(*args, **kwargs):
    raise socket.timeout


class ConnectionTests(unittest.TestCase):

    def test_parameters(self):
        params = pika.ConnectionParameters(socket_timeout=0.5,
                                           retry_delay=0.1,
                                           connection_attempts=3)
        self.assertEqual(params.socket_timeout, 0.5)
        self.assertEqual(params.retry_delay, 0.1)
        self.assertEqual(params.connection_attempts, 3)

    @patch.object(socket.socket, 'settimeout')
    @patch.object(socket.socket, 'connect')
    def test_connection_timeout(self, connect, settimeout):
        connect.side_effect = mock_timeout
        with self.assertRaises(exceptions.AMQPConnectionError):
            params = pika.ConnectionParameters(socket_timeout=2.0)
            base_connection.BaseConnection(params)
        settimeout.assert_called_with(2.0)

    @patch.object(socket.socket, 'settimeout')
    @patch.object(socket.socket, 'connect')
    def test_asyncore_connection_timeout(self, connect, settimeout):
        connect.side_effect = mock_timeout
        with self.assertRaises(exceptions.AMQPConnectionError):
            params = pika.ConnectionParameters(socket_timeout=2.0)
            asyncore_connection.AsyncoreConnection(params)
        settimeout.assert_called_with(2.0)

    @patch.object(socket.socket, 'settimeout')
    @patch.object(socket.socket, 'connect')
    def test_blocking_connection_timeout(self, connect, settimeout):
        connect.side_effect = mock_timeout
        with self.assertRaises(exceptions.AMQPConnectionError):
            params = pika.ConnectionParameters(socket_timeout=2.0)
            blocking_connection.BlockingConnection(params)
        settimeout.assert_called_with(2.0)

    @patch.object(socket.socket, 'settimeout')
    @patch.object(socket.socket, 'connect')
    def test_select_connection_timeout(self, connect, settimeout):
        connect.side_effect = mock_timeout
        with self.assertRaises(exceptions.AMQPConnectionError):
            params = pika.ConnectionParameters(socket_timeout=2.0)
            select_connection.SelectConnection(params)
        settimeout.assert_called_with(2.0)

    @unittest.skipUnless(tornado_connection is not None,
                         'tornado is not installed')
    @patch.object(socket.socket, 'settimeout')
    @patch.object(socket.socket, 'connect')
    def test_tornado_connection_timeout(self, connect, settimeout):
        connect.side_effect = mock_timeout
        with self.assertRaises(exceptions.AMQPConnectionError):
            params = pika.ConnectionParameters(socket_timeout=2.0)
            tornado_connection.TornadoConnection(params)
        settimeout.assert_called_with(2.0)

    @unittest.skipUnless(twisted_connection is not None,
                         'twisted is not installed')
    @patch.object(socket.socket, 'settimeout')
    @patch.object(socket.socket, 'connect')
    def test_twisted_connection_timeout(self, connect, settimeout):
        connect.side_effect = mock_timeout
        with self.assertRaises(exceptions.AMQPConnectionError):
            params = pika.ConnectionParameters(socket_timeout=2.0)
            twisted_connection.TwistedConnection(params)
        settimeout.assert_called_with(2.0)

    @unittest.skipUnless(libev_connection is not None, 'pyev is not installed')
    @patch.object(socket.socket, 'settimeout')
    @patch.object(socket.socket, 'connect')
    def test_libev_connection_timeout(self, connect, settimeout):
        connect.side_effect = mock_timeout
        with self.assertRaises(exceptions.AMQPConnectionError):
            params = pika.ConnectionParameters(socket_timeout=2.0)
            libev_connection.LibevConnection(params)
        settimeout.assert_called_with(2.0)

########NEW FILE########
__FILENAME__ = content_frame_dispatcher_tests
# -*- encoding: utf-8 -*-
"""
Tests for pika.channel.ContentFrameDispatcher

"""
import marshal
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from pika import channel
from pika import exceptions
from pika import frame
from pika import spec


class ContentFrameDispatcherTests(unittest.TestCase):

    def setUp(self):
         self.obj = channel.ContentFrameDispatcher()

    def test_init_method_frame(self):
        self.assertEqual(self.obj._method_frame, None)

    def test_init_header_frame(self):
        self.assertEqual(self.obj._header_frame, None)

    def test_init_seen_so_far(self):
        self.assertEqual(self.obj._seen_so_far, 0)

    def test_init_body_fragments(self):
        self.assertEqual(self.obj._body_fragments, list())

    def test_process_with_basic_deliver(self):
        value = frame.Method(1, spec.Basic.Deliver())
        self.obj.process(value)
        self.assertEqual(self.obj._method_frame, value)

    def test_process_with_content_header(self):
        value = frame.Header(1, 100, spec.BasicProperties)
        self.obj.process(value)
        self.assertEqual(self.obj._header_frame, value)

    def test_process_with_body_frame_partial(self):
        value = frame.Header(1, 100, spec.BasicProperties)
        self.obj.process(value)
        value = frame.Method(1, spec.Basic.Deliver())
        self.obj.process(value)
        value = frame.Body(1, 'abc123')
        self.obj.process(value)
        self.assertEqual(self.obj._body_fragments, [value.fragment])

    def test_process_with_full_message(self):
        method_frame = frame.Method(1, spec.Basic.Deliver())
        self.obj.process(method_frame)
        header_frame = frame.Header(1, 6, spec.BasicProperties)
        self.obj.process(header_frame)
        body_frame = frame.Body(1, 'abc123')
        response = self.obj.process(body_frame)
        self.assertEqual(response, (method_frame, header_frame, 'abc123'))

    def test_process_with_body_frame_six_bytes(self):
        method_frame = frame.Method(1, spec.Basic.Deliver())
        self.obj.process(method_frame)
        header_frame = frame.Header(1, 10, spec.BasicProperties)
        self.obj.process(header_frame)
        body_frame = frame.Body(1, 'abc123')
        self.obj.process(body_frame)
        self.assertEqual(self.obj._seen_so_far, 6)

    def test_process_with_body_frame_too_big(self):
        method_frame = frame.Method(1, spec.Basic.Deliver())
        self.obj.process(method_frame)
        header_frame = frame.Header(1, 6, spec.BasicProperties)
        self.obj.process(header_frame)
        body_frame = frame.Body(1, 'abcd1234')
        self.assertRaises(exceptions.BodyTooLongError,
                          self.obj.process, body_frame)

    def test_process_with_unexpected_frame_type(self):
        value = frame.Method(1, spec.Basic.Qos())
        self.assertRaises(exceptions.UnexpectedFrameError,
                          self.obj.process, value)

    def test_reset_method_frame(self):
        method_frame = frame.Method(1, spec.Basic.Deliver())
        self.obj.process(method_frame)
        header_frame = frame.Header(1, 10, spec.BasicProperties)
        self.obj.process(header_frame)
        body_frame = frame.Body(1, 'abc123')
        self.obj.process(body_frame)
        self.obj._reset()
        self.assertEqual(self.obj._method_frame, None)

    def test_reset_header_frame(self):
        method_frame = frame.Method(1, spec.Basic.Deliver())
        self.obj.process(method_frame)
        header_frame = frame.Header(1, 10, spec.BasicProperties)
        self.obj.process(header_frame)
        body_frame = frame.Body(1, 'abc123')
        self.obj.process(body_frame)
        self.obj._reset()
        self.assertEqual(self.obj._header_frame, None)

    def test_reset_seen_so_far(self):
        method_frame = frame.Method(1, spec.Basic.Deliver())
        self.obj.process(method_frame)
        header_frame = frame.Header(1, 10, spec.BasicProperties)
        self.obj.process(header_frame)
        body_frame = frame.Body(1, 'abc123')
        self.obj.process(body_frame)
        self.obj._reset()
        self.assertEqual(self.obj._seen_so_far, 0)

    def test_reset_body_fragments(self):
        method_frame = frame.Method(1, spec.Basic.Deliver())
        self.obj.process(method_frame)
        header_frame = frame.Header(1, 10, spec.BasicProperties)
        self.obj.process(header_frame)
        body_frame = frame.Body(1, 'abc123')
        self.obj.process(body_frame)
        self.obj._reset()
        self.assertEqual(self.obj._body_fragments, list())

    def test_ascii_body_instance(self):
        method_frame = frame.Method(1, spec.Basic.Deliver())
        self.obj.process(method_frame)
        header_frame = frame.Header(1, 11, spec.BasicProperties)
        self.obj.process(header_frame)
        body_frame = frame.Body(1, 'foo-bar-baz')
        method_frame, header_frame, body_value = self.obj.process(body_frame)
        self.assertIsInstance(body_value, str)

    def test_ascii_body_value(self):
        expectation ='foo-bar-baz'
        self.obj = channel.ContentFrameDispatcher()
        method_frame = frame.Method(1, spec.Basic.Deliver())
        self.obj.process(method_frame)
        header_frame = frame.Header(1, 11, spec.BasicProperties)
        self.obj.process(header_frame)
        body_frame = frame.Body(1, 'foo-bar-baz')
        method_frame, header_frame, body_value = self.obj.process(body_frame)
        self.assertEqual(body_value, expectation)
        self.assertIsInstance(body_value, str)

    def test_binary_non_unicode_value(self):
        expectation =('a', 0.8)
        self.obj = channel.ContentFrameDispatcher()
        method_frame = frame.Method(1, spec.Basic.Deliver())
        self.obj.process(method_frame)
        header_frame = frame.Header(1, 20, spec.BasicProperties)
        self.obj.process(header_frame)
        body_frame = frame.Body(1, marshal.dumps(expectation))
        method_frame, header_frame, body_value = self.obj.process(body_frame)
        self.assertEqual(marshal.loads(body_value), expectation)

########NEW FILE########
__FILENAME__ = credentials_tests
"""
Tests for pika.credentials

"""
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from pika import credentials
from pika import spec

class PlainCredentialsTests(unittest.TestCase):

    CREDENTIALS = 'guest', 'guest'
    def test_response_for(self):
        obj = credentials.PlainCredentials(*self.CREDENTIALS)
        start = spec.Connection.Start()
        self.assertEqual(obj.response_for(start),
                         ('PLAIN', '\x00guest\x00guest'))

    def test_erase_response_for_no_mechanism_match(self):
        obj = credentials.PlainCredentials(*self.CREDENTIALS)
        start = spec.Connection.Start()
        start.mechanisms = 'FOO BAR BAZ'
        self.assertEqual(obj.response_for(start), (None, None))

    def test_erase_credentials_false(self):
        obj = credentials.PlainCredentials(*self.CREDENTIALS)
        obj.erase_credentials()
        self.assertEqual((obj.username, obj.password), self.CREDENTIALS)

    def test_erase_credentials_true(self):
        obj = credentials.PlainCredentials(self.CREDENTIALS[0],
                                           self.CREDENTIALS[1],
                                           True)
        obj.erase_credentials()
        self.assertEqual((obj.username, obj.password), (None, None))


class ExternalCredentialsTest(unittest.TestCase):

    def test_response_for(self):
        obj = credentials.ExternalCredentials()
        start = spec.Connection.Start()
        start.mechanisms = 'PLAIN EXTERNAL'
        self.assertEqual(obj.response_for(start), ('EXTERNAL', ''))

    def test_erase_response_for_no_mechanism_match(self):
        obj = credentials.ExternalCredentials()
        start = spec.Connection.Start()
        start.mechanisms = 'FOO BAR BAZ'
        self.assertEqual(obj.response_for(start), (None, None))

    def test_erase_credentials(self):
        with mock.patch('pika.credentials.LOGGER', autospec=True) as logger:
            obj = credentials.ExternalCredentials()
            obj.erase_credentials()
            logger.debug.assert_called_once_with('Not supported by this '
                                                 'Credentials type')

########NEW FILE########
__FILENAME__ = data_tests
# -*- encoding: utf-8 -*-
"""
pika.data tests

"""
import datetime
import decimal
import platform
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from pika import data
from pika import exceptions


class DataTests(unittest.TestCase):

    FIELD_TBL_ENCODED = ('\x00\x00\x00\xbb\x07longvall\x00\x00\x00\x006e&U'
                         '\x06intvalI\x00\x00\x00\x01\x07dictvalF\x00\x00'
                         '\x00\x0c\x03fooS\x00\x00\x00\x03bar\x07unicodeS'
                         '\x00\x00\x00\x08utf8=\xe2\x9c\x93\x05arrayA\x00'
                         '\x00\x00\x0fI\x00\x00\x00\x01I\x00\x00\x00\x02I'
                         '\x00\x00\x00\x03\x04nullV\x06strvalS\x00\x00\x00'
                         '\x04Test\x0ctimestampvalT\x00\x00\x00\x00Ec)\x92'
                         '\x07decimalD\x02\x00\x00\x01:\x07boolvalt\x01'
                         '\x0bdecimal_tooD\x00\x00\x00\x00d')

    FIELD_TBL_VALUE = {'array': [1, 2, 3],
                       'boolval': True,
                       'decimal': decimal.Decimal('3.14'),
                       'decimal_too': decimal.Decimal('100'),
                       'dictval': {'foo': 'bar'},
                       'intval': 1,
                       'longval': long(912598613),
                       'null': None,
                       'strval': 'Test',
                       'timestampval': datetime.datetime(2006, 11, 21, 16, 30,
                                                         10),
                       'unicode': u'utf8=✓'}

    @unittest.skipIf(platform.python_implementation() == 'PyPy',
                     'pypy sort order issue')
    def test_encode_table(self):
        result = []
        data.encode_table(result, self.FIELD_TBL_VALUE)
        self.assertEqual(''.join(result), self.FIELD_TBL_ENCODED)

    def test_encode_table_bytes(self):
        result = []
        byte_count = data.encode_table(result, self.FIELD_TBL_VALUE)
        self.assertEqual(byte_count, 191)

    def test_decode_table(self):
        value, byte_count = data.decode_table(self.FIELD_TBL_ENCODED, 0)
        self.assertDictEqual(value, self.FIELD_TBL_VALUE)

    def test_decode_table_bytes(self):
        value, byte_count = data.decode_table(self.FIELD_TBL_ENCODED, 0)
        self.assertEqual(byte_count, 191)

    def test_encode_raises(self):
        self.assertRaises(exceptions.UnsupportedAMQPFieldException,
                          data.encode_table,
                          [], {'foo': set([1, 2, 3])})

    def test_decode_raises(self):
        self.assertRaises(exceptions.InvalidFieldTypeException,
                          data.decode_table,
                          '\x00\x00\x00\t\x03fooZ\x00\x00\x04\xd2', 0)

########NEW FILE########
__FILENAME__ = exceptions_test
"""
Tests for pika.exceptions

"""
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from pika import exceptions


class ExceptionTests(unittest.TestCase):

    def test_amqp_connection_error_one_param_repr(self):
        self.assertEqual(repr(exceptions.AMQPConnectionError(10)),
                         "No connection could be opened after 10 connection attempts")

    def test_amqp_connection_error_two_params_repr(self):
        self.assertEqual(repr(exceptions.AMQPConnectionError(1, 'Test')),
                         "1: Test")

    def test_authentication_error_repr(self):
        self.assertEqual(repr(exceptions.AuthenticationError('PLAIN')),
                         'Server and client could not negotiate use of the '
                         'PLAIN authentication mechanism')

    def test_body_too_long_error_repr(self):
        self.assertEqual(repr(exceptions.BodyTooLongError(100, 50)),
                         'Received too many bytes for a message delivery: '
                         'Received 100, expected 50' )

    def test_invalid_minimum_frame_size_repr(self):
        self.assertEqual(repr(exceptions.InvalidMinimumFrameSize()),
                         'AMQP Minimum Frame Size is 4096 Bytes')

    def test_invalid_maximum_frame_size_repr(self):
        self.assertEqual(repr(exceptions.InvalidMaximumFrameSize()),
                         'AMQP Maximum Frame Size is 131072 Bytes')

########NEW FILE########
__FILENAME__ = frame_tests
"""
Tests for pika.frame

"""
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from pika import exceptions
from pika import frame
from pika import spec


class FrameTests(unittest.TestCase):

    BASIC_ACK = ('\x01\x00\x01\x00\x00\x00\r\x00<\x00P\x00\x00\x00\x00\x00\x00'
                 '\x00d\x00\xce')
    BODY_FRAME = '\x03\x00\x01\x00\x00\x00\x14I like it that sound\xce'
    BODY_FRAME_VALUE = 'I like it that sound'
    CONTENT_HEADER = ('\x02\x00\x01\x00\x00\x00\x0f\x00<\x00\x00\x00'
                      '\x00\x00\x00\x00\x00\x00d\x10\x00\x02\xce')
    HEARTBEAT = '\x08\x00\x00\x00\x00\x00\x00\xce'
    PROTOCOL_HEADER = 'AMQP\x00\x00\t\x01'

    def frame_marshal_not_implemented_test(self):
        frame_obj = frame.Frame(0x000A000B, 1)
        self.assertRaises(NotImplementedError, frame_obj.marshal)

    def frame_underscore_marshal_test(self):
        basic_ack = frame.Method(1, spec.Basic.Ack(100))
        self.assertEqual(basic_ack.marshal(), self.BASIC_ACK)

    def headers_marshal_test(self):
        header = frame.Header(1, 100,
                              spec.BasicProperties(delivery_mode=2))
        self.assertEqual(header.marshal(), self.CONTENT_HEADER)

    def body_marshal_test(self):
        body = frame.Body(1, 'I like it that sound')
        self.assertEqual(body.marshal(), self.BODY_FRAME)

    def heartbeat_marshal_test(self):
        heartbeat = frame.Heartbeat()
        self.assertEqual(heartbeat.marshal(), self.HEARTBEAT)

    def protocol_header_marshal_test(self):
        protocol_header = frame.ProtocolHeader()
        self.assertEqual(protocol_header.marshal(), self.PROTOCOL_HEADER)

    def decode_protocol_header_instance_test(self):
        self.assertIsInstance(frame.decode_frame(self.PROTOCOL_HEADER)[1],
                              frame.ProtocolHeader)

    def decode_protocol_header_bytes_test(self):
        self.assertEqual(frame.decode_frame(self.PROTOCOL_HEADER)[0], 8)

    def decode_method_frame_instance_test(self):
        self.assertIsInstance(frame.decode_frame(self.BASIC_ACK)[1],
                              frame.Method)

    def decode_protocol_header_failure_test(self):
        self.assertEqual(frame.decode_frame('AMQPa'), (0, None))

    def decode_method_frame_bytes_test(self):
        self.assertEqual(frame.decode_frame(self.BASIC_ACK)[0], 21)

    def decode_method_frame_method_test(self):
        self.assertIsInstance(frame.decode_frame(self.BASIC_ACK)[1].method,
                              spec.Basic.Ack)

    def decode_header_frame_instance_test(self):
        self.assertIsInstance(frame.decode_frame(self.CONTENT_HEADER)[1],
                              frame.Header)

    def decode_header_frame_bytes_test(self):
        self.assertEqual(frame.decode_frame(self.CONTENT_HEADER)[0], 23)

    def decode_header_frame_properties_test(self):
        frame_value = frame.decode_frame(self.CONTENT_HEADER)[1]
        self.assertIsInstance(frame_value.properties, spec.BasicProperties)

    def decode_frame_decoding_failure_test(self):
        self.assertEqual(frame.decode_frame('\x01\x00\x01\x00\x00\xce'),
                         (0, None))

    def decode_frame_decoding_no_end_byte_test(self):
        self.assertEqual(frame.decode_frame(self.BASIC_ACK[:-1]), (0, None))

    def decode_frame_decoding_wrong_end_byte_test(self):
        self.assertRaises(exceptions.InvalidFrameError,
                          frame.decode_frame,
                          self.BASIC_ACK[:-1] + 'A')

    def decode_body_frame_instance_test(self):
        self.assertIsInstance(frame.decode_frame(self.BODY_FRAME)[1],
                              frame.Body)

    def decode_body_frame_fragment_test(self):
        self.assertEqual(frame.decode_frame(self.BODY_FRAME)[1].fragment,
                         self.BODY_FRAME_VALUE)

    def decode_body_frame_fragment_consumed_bytes_test(self):
        self.assertEqual(frame.decode_frame(self.BODY_FRAME)[0], 28)

    def decode_heartbeat_frame_test(self):
        self.assertIsInstance(frame.decode_frame(self.HEARTBEAT)[1],
                              frame.Heartbeat)

    def decode_heartbeat_frame_bytes_consumed_test(self):
        self.assertEqual(frame.decode_frame(self.HEARTBEAT)[0], 8)

    def decode_frame_invalid_frame_type_test(self):
        self.assertRaises(exceptions.InvalidFrameError,
                          frame.decode_frame,
                          '\x09\x00\x00\x00\x00\x00\x00\xce')

########NEW FILE########
__FILENAME__ = heartbeat_tests
"""
Tests for pika.heartbeat

"""
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from pika import connection
from pika import frame
from pika import heartbeat

class HeartbeatTests(unittest.TestCase):

    INTERVAL = 5

    def setUp(self):
        self.mock_conn = mock.Mock(spec=connection.Connection)
        self.mock_conn.bytes_received = 100
        self.mock_conn.bytes_sent = 100
        self.mock_conn.heartbeat = mock.Mock(spec=heartbeat.HeartbeatChecker)
        self.obj = heartbeat.HeartbeatChecker(self.mock_conn, self.INTERVAL)

    def tearDown(self):
        del self.obj
        del self.mock_conn

    def test_default_initialization_max_idle_count(self):
        self.assertEqual(self.obj._max_idle_count,
                         self.obj.MAX_IDLE_COUNT)

    def test_constructor_assignment_connection(self):
        self.assertEqual(self.obj._connection, self.mock_conn)

    def test_constructor_assignment_heartbeat_interval(self):
        self.assertEqual(self.obj._interval, self.INTERVAL)

    def test_constructor_initial_bytes_received(self):
        self.assertEqual(self.obj._bytes_received, 0)

    def test_constructor_initial_bytes_sent(self):
        self.assertEqual(self.obj._bytes_received, 0)

    def test_constructor_initial_heartbeat_frames_received(self):
        self.assertEqual(self.obj._heartbeat_frames_received, 0)

    def test_constructor_initial_heartbeat_frames_sent(self):
        self.assertEqual(self.obj._heartbeat_frames_sent, 0)

    def test_constructor_initial_idle_byte_intervals(self):
        self.assertEqual(self.obj._idle_byte_intervals, 0)

    @mock.patch('pika.heartbeat.HeartbeatChecker._setup_timer')
    def test_constructor_called_setup_timer(self, timer):
        obj = heartbeat.HeartbeatChecker(self.mock_conn, self.INTERVAL)
        timer.assert_called_once_with()

    def test_active_true(self):
        self.mock_conn.heartbeat = self.obj
        self.assertTrue(self.obj.active)

    def test_active_false(self):
        self.mock_conn.heartbeat = mock.Mock()
        self.assertFalse(self.obj.active)

    def test_bytes_received_on_connection(self):
        self.mock_conn.bytes_received = 128
        self.assertEqual(self.obj.bytes_received_on_connection, 128)

    def test_connection_is_idle_false(self):
        self.assertFalse(self.obj.connection_is_idle)

    def test_connection_is_idle_true(self):
        self.obj._idle_byte_intervals = self.INTERVAL
        self.assertTrue(self.obj.connection_is_idle)

    def test_received(self):
        self.obj.received()
        self.assertTrue(self.obj._heartbeat_frames_received, 1)

    @mock.patch('pika.heartbeat.HeartbeatChecker._close_connection')
    def test_send_and_check_not_closed(self, close_connection):
        obj = heartbeat.HeartbeatChecker(self.mock_conn, self.INTERVAL)
        obj.send_and_check()
        close_connection.assert_not_called()

    @mock.patch('pika.heartbeat.HeartbeatChecker._close_connection')
    def test_send_and_check_missed_bytes(self, close_connection):
        obj = heartbeat.HeartbeatChecker(self.mock_conn, self.INTERVAL)
        obj._idle_byte_intervals = self.INTERVAL
        obj.send_and_check()
        close_connection.assert_called_once_with()

    def test_send_and_check_increment_no_bytes(self):
        self.mock_conn.bytes_received = 100
        self.obj._bytes_received = 100
        self.obj.send_and_check()
        self.assertEqual(self.obj._idle_byte_intervals, 1)

    def test_send_and_check_increment_bytes(self):
        self.mock_conn.bytes_received = 100
        self.obj._bytes_received = 128
        self.obj.send_and_check()
        self.assertEqual(self.obj._idle_byte_intervals, 0)

    @mock.patch('pika.heartbeat.HeartbeatChecker._update_counters')
    def test_send_and_check_update_counters(self, update_counters):
        obj = heartbeat.HeartbeatChecker(self.mock_conn, self.INTERVAL)
        obj.send_and_check()
        update_counters.assert_called_once_with()

    @mock.patch('pika.heartbeat.HeartbeatChecker._send_heartbeat_frame')
    def test_send_and_check_send_heartbeat_frame(self, send_heartbeat_frame):
        obj = heartbeat.HeartbeatChecker(self.mock_conn, self.INTERVAL)
        obj.send_and_check()
        send_heartbeat_frame.assert_called_once_with()

    @mock.patch('pika.heartbeat.HeartbeatChecker._start_timer')
    def test_send_and_check_start_timer(self, start_timer):
        obj = heartbeat.HeartbeatChecker(self.mock_conn, self.INTERVAL)
        obj.send_and_check()
        start_timer.assert_called_once_with()

    def test_connection_close(self):
        self.obj._idle_byte_intervals = 3
        self.obj._idle_heartbeat_intervals = 4
        self.obj._close_connection()
        self.mock_conn.close.assert_called_once_with(self.obj._CONNECTION_FORCED,
                                                     self.obj._STALE_CONNECTION %
                                                     (self.obj._max_idle_count *
                                                      self.obj._interval))

    def test_has_received_data_false(self):
        self.obj._bytes_received = 100
        self.assertFalse(self.obj._has_received_data)

    def test_has_received_data_true(self):
        self.mock_conn.bytes_received = 128
        self.obj._bytes_received = 100
        self.assertTrue(self.obj._has_received_data)

    def test_new_heartbeat_frame(self):
        self.assertIsInstance(self.obj._new_heartbeat_frame(), frame.Heartbeat)

    def test_send_heartbeat_send_frame_called(self):
        self.obj._send_heartbeat_frame()
        self.mock_conn._send_frame.assert_called_once()

    def test_send_heartbeat_counter_incremented(self):
        self.obj._send_heartbeat_frame()
        self.assertEqual(self.obj._heartbeat_frames_sent, 1)

    def test_setup_timer_called(self):
        self.obj._setup_timer()
        self.mock_conn.add_timeout.called_once_with(self.INTERVAL,
                                                    self.obj.send_and_check)

    @mock.patch('pika.heartbeat.HeartbeatChecker._setup_timer')
    def test_start_timer_not_active(self, setup_timer):
        self.obj._start_timer()
        setup_timer.assert_not_called()

    @mock.patch('pika.heartbeat.HeartbeatChecker._setup_timer')
    def test_start_timer_active(self, setup_timer):
        self.mock_conn.heartbeat = self.obj
        self.obj._start_timer()
        self.assertTrue(setup_timer.called)

    def test_update_counters_bytes_received(self):
        self.mock_conn.bytes_received = 256
        self.obj._update_counters()
        self.assertEqual(self.obj._bytes_received, 256)

    def test_update_counters_bytes_sent(self):
        self.mock_conn.bytes_sent = 256
        self.obj._update_counters()
        self.assertEqual(self.obj._bytes_sent, 256)

########NEW FILE########
__FILENAME__ = parameter_tests
import unittest
import pika


class ConnectionTests(unittest.TestCase):

    def test_parameters_accepts_plain_string_virtualhost(self):
        parameters = pika.ConnectionParameters(virtual_host="prtfqpeo")
        self.assertEqual(parameters.virtual_host, "prtfqpeo")

    def test_parameters_accepts_plain_string_virtualhost(self):
        parameters = pika.ConnectionParameters(virtual_host=u"prtfqpeo")
        self.assertEqual(parameters.virtual_host, "prtfqpeo")

    def test_parameters_accept_plain_string_locale(self):
        parameters = pika.ConnectionParameters(locale="en_US")
        self.assertEqual(parameters.locale, "en_US")

    def test_parameters_accept_unicode_locale(self):
        parameters = pika.ConnectionParameters(locale=u"en_US")
        self.assertEqual(parameters.locale, "en_US")

    def test_urlparameters_accepts_plain_string(self):
        parameters = pika.URLParameters("amqp://prtfqpeo:oihdglkhcp0@myserver.mycompany.com:5672/prtfqpeo?locale=en_US")
        self.assertEqual(parameters.port, 5672)
        self.assertEqual(parameters.virtual_host, "prtfqpeo")
        self.assertEqual(parameters.credentials.password, "oihdglkhcp0")
        self.assertEqual(parameters.credentials.username, "prtfqpeo")
        self.assertEqual(parameters.locale, "en_US")

    def test_urlparameters_accepts_unicode_string(self):
        parameters = pika.URLParameters(u"amqp://prtfqpeo:oihdglkhcp0@myserver.mycompany.com:5672/prtfqpeo?locale=en_US")
        self.assertEqual(parameters.port, 5672)
        self.assertEqual(parameters.virtual_host, "prtfqpeo")
        self.assertEqual(parameters.credentials.password, "oihdglkhcp0")
        self.assertEqual(parameters.credentials.username, "prtfqpeo")
        self.assertEqual(parameters.locale, "en_US")
########NEW FILE########
__FILENAME__ = tornado_tests
"""
Tests for pika.adapters.tornado_connection

"""
try:
    from tornado import ioloop
except ImportError:
    ioloop = None

import mock

try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    from pika.adapters import tornado_connection
except ImportError:
    tornado_connection = None


class TornadoConnectionTests(unittest.TestCase):

    @unittest.skipIf(ioloop is None, 'requires Tornado')
    @mock.patch('pika.adapters.base_connection.BaseConnection.__init__')
    def test_tornado_connection_call_parent(self, mock_init):
        obj = tornado_connection.TornadoConnection()
        mock_init.called_once_with(None, None, False)

########NEW FILE########
__FILENAME__ = utils_tests
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from pika import utils


class UtilsTests(unittest.TestCase):

    def test_is_callable_true(self):
        self.assertTrue(utils.is_callable(utils.is_callable))

    def test_is_callable_false(self):
        self.assertFalse(utils.is_callable(1))

########NEW FILE########
__FILENAME__ = codegen
# ***** BEGIN LICENSE BLOCK *****
#
# For copyright and licensing please refer to COPYING.
#
# ***** END LICENSE BLOCK *****

from __future__ import nested_scopes

import os
import sys

RABBITMQ_PUBLIC_UMBRELLA = '../../rabbitmq-public-umbrella'
RABBITMQ_CODEGEN = 'rabbitmq-codegen'
PIKA_SPEC = '../pika/spec.py'

CODEGEN_PATH = os.path.realpath('%s/%s' % (RABBITMQ_PUBLIC_UMBRELLA,
                                           RABBITMQ_CODEGEN))
print('codegen-path: %s' % CODEGEN_PATH)
sys.path.append(CODEGEN_PATH)

import amqp_codegen
import re

DRIVER_METHODS = {
    "Exchange.Bind": ["Exchange.BindOk"],
    "Exchange.Unbind": ["Exchange.UnbindOk"],
    "Exchange.Declare": ["Exchange.DeclareOk"],
    "Exchange.Delete": ["Exchange.DeleteOk"],
    "Queue.Declare": ["Queue.DeclareOk"],
    "Queue.Bind": ["Queue.BindOk"],
    "Queue.Purge": ["Queue.PurgeOk"],
    "Queue.Delete": ["Queue.DeleteOk"],
    "Queue.Unbind": ["Queue.UnbindOk"],
    "Basic.Qos": ["Basic.QosOk"],
    "Basic.Get": ["Basic.GetOk", "Basic.GetEmpty"],
    "Basic.Ack": [],
    "Basic.Reject": [],
    "Basic.Recover": ["Basic.RecoverOk"],
    "Basic.RecoverAsync": [],
    "Tx.Select": ["Tx.SelectOk"],
    "Tx.Commit": ["Tx.CommitOk"],
    "Tx.Rollback": ["Tx.RollbackOk"]
    }


def fieldvalue(v):
    if isinstance(v, unicode):
        return repr(v.encode('ascii'))
    else:
        return repr(v)


def normalize_separators(s):
    s = s.replace('-', '_')
    s = s.replace(' ', '_')
    return s


def pyize(s):
    s = normalize_separators(s)
    if s in ('global', 'class'):
        s += '_'
    return s


def camel(s):
    return normalize_separators(s).title().replace('_', '')


amqp_codegen.AmqpMethod.structName = lambda m: camel(m.klass.name) + '.' + camel(m.name)
amqp_codegen.AmqpClass.structName = lambda c: camel(c.name) + "Properties"


def constantName(s):
    return '_'.join(re.split('[- ]', s.upper()))


def flagName(c, f):
    if c:
        return c.structName() + '.' + constantName('flag_' + f.name)
    else:
        return constantName('flag_' + f.name)


def generate(specPath):
    spec = amqp_codegen.AmqpSpec(specPath)

    def genSingleDecode(prefix, cLvalue, unresolved_domain):
        type = spec.resolveDomain(unresolved_domain)
        if type == 'shortstr':
            print(prefix + "length = struct.unpack_from('B', encoded, offset)[0]")
            print(prefix + "offset += 1")
            print(prefix + "%s = encoded[offset:offset + length]" % cLvalue)
            print(prefix + "try:")
            print(prefix + "    %s = str(%s)" % (cLvalue, cLvalue))
            print(prefix + "except UnicodeEncodeError:")
            print(prefix + "    pass")
            print(prefix + "offset += length")
        elif type == 'longstr':
            print(prefix + "length = struct.unpack_from('>I', encoded, offset)[0]")
            print(prefix + "offset += 4")
            print(prefix + "%s = encoded[offset:offset + length]" % cLvalue)
            print(prefix + "try:")
            print(prefix + "    %s = str(%s)" % (cLvalue, cLvalue))
            print(prefix + "except UnicodeEncodeError:")
            print(prefix + "    pass")
            print(prefix + "offset += length")
        elif type == 'octet':
            print(prefix + "%s = struct.unpack_from('B', encoded, offset)[0]" % cLvalue)
            print(prefix + "offset += 1")
        elif type == 'short':
            print(prefix + "%s = struct.unpack_from('>H', encoded, offset)[0]" % cLvalue)
            print(prefix + "offset += 2")
        elif type == 'long':
            print(prefix + "%s = struct.unpack_from('>I', encoded, offset)[0]" % cLvalue)
            print(prefix + "offset += 4")
        elif type == 'longlong':
            print(prefix + "%s = struct.unpack_from('>Q', encoded, offset)[0]" % cLvalue)
            print(prefix + "offset += 8")
        elif type == 'timestamp':
            print(prefix + "%s = struct.unpack_from('>Q', encoded, offset)[0]" % cLvalue)
            print(prefix + "offset += 8")
        elif type == 'bit':
            raise Exception("Can't decode bit in genSingleDecode")
        elif type == 'table':
            print(Exception(prefix + "(%s, offset) = data.decode_table(encoded, offset)" % \
                  cLvalue))
        else:
            raise Exception("Illegal domain in genSingleDecode", type)

    def genSingleEncode(prefix, cValue, unresolved_domain):
        type = spec.resolveDomain(unresolved_domain)
        if type == 'shortstr':
            print(prefix + \
                "assert isinstance(%s, basestring),\\\n%s       'A non-bytestring value was supplied for %s'" \
                % (cValue, prefix, cValue))
            print(prefix + "value = %s.encode('utf-8') if isinstance(%s, unicode) else %s" % (cValue, cValue, cValue))
            print(prefix + "pieces.append(struct.pack('B', len(value)))")
            print(prefix + "pieces.append(value)")
        elif type == 'longstr':
            print(prefix + \
                "assert isinstance(%s, basestring),\\\n%s       'A non-bytestring value was supplied for %s'" \
                % (cValue, prefix ,cValue))
            print(prefix + "value = %s.encode('utf-8') if isinstance(%s, unicode) else %s" % (cValue, cValue, cValue))
            print(prefix + "pieces.append(struct.pack('>I', len(value)))")
            print(prefix + "pieces.append(value)")
        elif type == 'octet':
            print(prefix + "pieces.append(struct.pack('B', %s))" % cValue)
        elif type == 'short':
            print(prefix + "pieces.append(struct.pack('>H', %s))" % cValue)
        elif type == 'long':
            print(prefix + "pieces.append(struct.pack('>I', %s))" % cValue)
        elif type == 'longlong':
            print(prefix + "pieces.append(struct.pack('>Q', %s))" % cValue)
        elif type == 'timestamp':
            print(prefix + "pieces.append(struct.pack('>Q', %s))" % cValue)
        elif type == 'bit':
            raise Exception("Can't encode bit in genSingleEncode")
        elif type == 'table':
            print(Exception(prefix + "data.encode_table(pieces, %s)" % cValue))
        else:
            raise Exception("Illegal domain in genSingleEncode", type)

    def genDecodeMethodFields(m):
        print("        def decode(self, encoded, offset=0):")
        bitindex = None
        for f in m.arguments:
            if spec.resolveDomain(f.domain) == 'bit':
                if bitindex is None:
                    bitindex = 0
                if bitindex >= 8:
                    bitindex = 0
                if not bitindex:
                    print("            bit_buffer = struct.unpack_from('B', encoded, offset)[0]")
                    print("            offset += 1")
                print("            self.%s = (bit_buffer & (1 << %d)) != 0" % \
                      (pyize(f.name), bitindex))
                bitindex += 1
            else:
                bitindex = None
                genSingleDecode("            ", "self.%s" % (pyize(f.name),), f.domain)
        print("            return self")
        print('')

    def genDecodeProperties(c):
        print("    def decode(self, encoded, offset=0):")
        print("        flags = 0")
        print("        flagword_index = 0")
        print("        while True:")
        print("            partial_flags = struct.unpack_from('>H', encoded, offset)[0]")
        print("            offset += 2")
        print("            flags = flags | (partial_flags << (flagword_index * 16))")
        print("            if not (partial_flags & 1):")
        print("                break")
        print("            flagword_index += 1")
        for f in c.fields:
            if spec.resolveDomain(f.domain) == 'bit':
                print("        self.%s = (flags & %s) != 0" % (pyize(f.name), flagName(c, f)))
            else:
                print("        if flags & %s:" % (flagName(c, f),))
                genSingleDecode("            ", "self.%s" % (pyize(f.name),), f.domain)
                print("        else:")
                print("            self.%s = None" % (pyize(f.name),))
        print("        return self")
        print('')

    def genEncodeMethodFields(m):
        print("        def encode(self):")
        print("            pieces = list()")
        bitindex = None

        def finishBits():
            if bitindex is not None:
                print("            pieces.append(struct.pack('B', bit_buffer))")
        for f in m.arguments:
            if spec.resolveDomain(f.domain) == 'bit':
                if bitindex is None:
                    bitindex = 0
                    print("            bit_buffer = 0")
                if bitindex >= 8:
                    finishBits()
                    print("            bit_buffer = 0")
                    bitindex = 0
                print("            if self.%s:" % pyize(f.name))
                print("                bit_buffer = bit_buffer | (1 << %d)" % \
                    bitindex)
                bitindex += 1
            else:
                finishBits()
                bitindex = None
                genSingleEncode("            ", "self.%s" % (pyize(f.name),), f.domain)
        finishBits()
        print("            return pieces")
        print('')

    def genEncodeProperties(c):
        print("    def encode(self):")
        print("        pieces = list()")
        print("        flags = 0")
        for f in c.fields:
            if spec.resolveDomain(f.domain) == 'bit':
                print("        if self.%s: flags = flags | %s" % (pyize(f.name), flagName(c, f)))
            else:
                print("        if self.%s is not None:" % (pyize(f.name),))
                print("            flags = flags | %s" % (flagName(c, f),))
                genSingleEncode("            ", "self.%s" % (pyize(f.name),), f.domain)
        print("        flag_pieces = list()")
        print("        while True:")
        print("            remainder = flags >> 16")
        print("            partial_flags = flags & 0xFFFE")
        print("            if remainder != 0:")
        print("                partial_flags |= 1")
        print("            flag_pieces.append(struct.pack('>H', partial_flags))")
        print("            flags = remainder")
        print("            if not flags:")
        print("                break")
        print("        return flag_pieces + pieces")
        print('')

    def fieldDeclList(fields):
        return ''.join([", %s=%s" % (pyize(f.name), fieldvalue(f.defaultvalue)) for f in fields])

    def fieldInitList(prefix, fields):
        if fields:
            return ''.join(["%sself.%s = %s\n" % (prefix, pyize(f.name), pyize(f.name)) \
                            for f in fields])
        else:
            return '%spass\n' % (prefix,)

    print("""# ***** BEGIN LICENSE BLOCK *****
#
# For copyright and licensing please refer to COPYING.
#
# ***** END LICENSE BLOCK *****

# NOTE: Autogenerated code by codegen.py, do not edit

import struct
from pika import amqp_object
from pika import data

""")

    print("PROTOCOL_VERSION = (%d, %d, %d)" % (spec.major, spec.minor,
                                               spec.revision))
    print("PORT = %d" % spec.port)
    print('')

    # Append some constants that arent in the spec json file
    spec.constants.append(('FRAME_MAX_SIZE', 131072, ''))
    spec.constants.append(('FRAME_HEADER_SIZE', 7, ''))
    spec.constants.append(('FRAME_END_SIZE', 1, ''))

    constants = {}
    for c, v, cls in spec.constants:
        constants[constantName(c)] = v

    for key in sorted(constants.keys()):
        print("%s = %s" % (key, constants[key]))
    print('')

    for c in spec.allClasses():
        print('')
        print('class %s(amqp_object.Class):' % (camel(c.name),))
        print('')
        print("    INDEX = 0x%.04X  # %d" % (c.index, c.index))
        print("    NAME = %s" % (fieldvalue(camel(c.name)),))
        print('')

        for m in c.allMethods():
            print('    class %s(amqp_object.Method):' % (camel(m.name),))
            print('')
            methodid = m.klass.index << 16 | m.index
            print("        INDEX = 0x%.08X  # %d, %d; %d" % \
                  (methodid,
                   m.klass.index,
                   m.index,
                   methodid))
            print("        NAME = %s" % (fieldvalue(m.structName(),)))
            print('')
            print("        def __init__(self%s):" % (fieldDeclList(m.arguments),))
            print(fieldInitList('            ', m.arguments))
            print("        @property")
            print("        def synchronous(self):")
            print("            return %s" % m.isSynchronous)
            print('')
            genDecodeMethodFields(m)
            genEncodeMethodFields(m)

    for c in spec.allClasses():
        if c.fields:
            print('')
            print('class %s(amqp_object.Properties):' % (c.structName(),))
            print('')
            print("    CLASS = %s" % (camel(c.name),))
            print("    INDEX = 0x%.04X  # %d" % (c.index, c.index))
            print("    NAME = %s" % (fieldvalue(c.structName(),)))
            print('')

            index = 0
            if c.fields:
                for f in c.fields:
                    if index % 16 == 15:
                        index += 1
                    shortnum = index / 16
                    partialindex = 15 - (index % 16)
                    bitindex = shortnum * 16 + partialindex
                    print('    %s = (1 << %d)' % (flagName(None, f), bitindex))
                    index += 1
                print('')

            print("    def __init__(self%s):" % (fieldDeclList(c.fields),))
            print(fieldInitList('        ', c.fields))
            genDecodeProperties(c)
            genEncodeProperties(c)

    print("methods = {")
    print(',\n'.join(["    0x%08X: %s" % (m.klass.index << 16 | m.index, m.structName()) \
                      for m in spec.allMethods()]))
    print("}")
    print('')

    print("props = {")
    print(',\n'.join(["    0x%04X: %s" % (c.index, c.structName()) \
                      for c in spec.allClasses() \
                      if c.fields]))
    print("}")
    print('')
    print('')

    print("def has_content(methodNumber):")
    print('')
    for m in spec.allMethods():
        if m.hasContent:
            print('    if methodNumber == %s.INDEX:' % m.structName())
            print('        return True')
    print("    return False")
    print('')

if __name__ == "__main__":
    with open(PIKA_SPEC, 'w') as handle:
        sys.stdout = handle
        generate(['%s/amqp-rabbitmq-0.9.1.json' % CODEGEN_PATH])

########NEW FILE########
