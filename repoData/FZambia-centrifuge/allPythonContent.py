__FILENAME__ = client
import sys
import hmac
import six
import json
import time
from twisted.internet import reactor
from autobahn.websocket import WebSocketClientFactory
from autobahn.websocket import WebSocketClientProtocol
from autobahn.websocket import connectWS


URL = sys.argv[1]
PROJECT_ID = sys.argv[2]
SECRET_KEY = sys.argv[3]
USER_ID = "test"

try:
    NUM_CLIENTS = int(sys.argv[4])
except IndexError:
    NUM_CLIENTS = 1


COUNT = 0
LIMIT = 1*NUM_CLIENTS
NUM_CLIENTS_SUBSCRIBED = 0


class ClientProtocol(WebSocketClientProtocol):
    """
    Simple client that connects to a WebSocket server, send a HELLO
    message every 2 seconds and print everything it receives.
    """

    _connected = False

    _subscribed = False

    def centrifuge_connect(self):
        message = {
            "method": "connect",
            "params": {
                "token": generate_token(SECRET_KEY, PROJECT_ID, USER_ID, str(int(time.time()))),
                "user": USER_ID,
                "project": PROJECT_ID
            }
        }

        self.sendMessage(json.dumps(message))

    def centrifuge_subscribe(self):
        message = {
            "method": "subscribe",
            "params": {
                "namespace": "test",
                "channel": "test"
            }
        }

        self.sendMessage(json.dumps(message))

    def centrifuge_publish(self):

        message = {
            "method": "publish",
            "params": {
                "namespace": "test",
                "channel": "test",
                "data": {"input": "test"}
            }
        }

        self.sendMessage(json.dumps(message))

    def on_centrifuge_message(self, msg):
        pass

    def on_centrifuge_subscribed(self):
        pass

    def onOpen(self):
        self.centrifuge_connect()

    def onMessage(self, msg, binary):
        msg = json.loads(msg)
        if msg['error']:
            print msg['error']
            raise

        method = msg['method']

        if method == 'connect':
            self._connected = True
            self.centrifuge_subscribe()
        elif method == 'subscribe':
            self._subscribed = True
            self.on_centrifuge_subscribed()
        elif method == 'message':
            self.on_centrifuge_message(msg)


class WebsocketFactory(WebSocketClientFactory):

    clients = []

    def start_publishing(self):
        for client in self.clients:
            client.centrifuge_publish()


class ThroughputClientProtocol(ClientProtocol):

    def on_centrifuge_subscribed(self):
        global NUM_CLIENTS_SUBSCRIBED
        NUM_CLIENTS_SUBSCRIBED += 1
        self.factory.clients.append(self)
        if NUM_CLIENTS_SUBSCRIBED == NUM_CLIENTS:
            print 'all clients subscribed'
            self.factory.start = time.time()
            self.factory.start_publishing()

    def on_centrifuge_message(self, msg):
        global COUNT
        COUNT += 1
        if COUNT == NUM_CLIENTS*NUM_CLIENTS:
            stop = time.time()
            print stop - self.factory.start
            reactor.stop()


class ReceiveClientProtocol(ClientProtocol):

    def on_centrifuge_subscribed(self):
        global NUM_CLIENTS_SUBSCRIBED
        NUM_CLIENTS_SUBSCRIBED += 1
        self.factory.clients.append(self)
        if NUM_CLIENTS_SUBSCRIBED == NUM_CLIENTS:
            print 'all clients subscribed'
            self.factory.start = time.time()

    def on_centrifuge_message(self, msg):
        global COUNT
        COUNT += 1
        if COUNT == 1:
            self.factory.start = time.time()

        if COUNT == NUM_CLIENTS:
            stop = time.time()
            print stop - self.factory.start
            COUNT = 0


def generate_token(secret_key, project_id, user_id, timestamp):
    sign = hmac.new(six.b(str(secret_key)))
    sign.update(six.b(str(project_id)))
    sign.update(six.b(user_id))
    sign.update(six.b(timestamp))
    token = sign.hexdigest()
    return token


if __name__ == '__main__':

    if len(sys.argv) < 2:
        print "Need the WebSocket server address, i.e. ws://localhost:9000"
        sys.exit(1)

    for _ in range(NUM_CLIENTS):
        factory = WebsocketFactory(URL)
        factory.protocol = ThroughputClientProtocol
        connectWS(factory)

    reactor.run()

########NEW FILE########
__FILENAME__ = auth
# coding: utf-8
# Copyright (c) Alexandr Emelin. MIT license.

from tornado.escape import json_decode
import hmac
import six

from centrifuge.log import logger


def check_sign(secret_key, project_id, encoded_data, auth_sign):
    """
    Check that data from client was properly signed.
    To do it create an HMAC with md5 hashing algorithm (python's default)
    based on secret key, project ID and encoded data and compare result
    with sign provided.
    """
    sign = hmac.new(six.b(str(secret_key)))
    sign.update(six.b(project_id))
    sign.update(six.b(encoded_data))
    return sign.hexdigest() == auth_sign


def decode_data(data):
    """
    Decode request body received from API client.
    """
    try:
        return json_decode(data)
    except Exception as err:
        logger.debug(err)
        return None


def get_client_token(secret_key, project_id, user, expired, user_info=None):
    """
    When client from browser connects to Centrifuge he must send his
    user ID, ID of project and optionally user_info JSON string.
    To validate that data we use md5 HMAC to build token.
    """
    sign = hmac.new(six.b(str(secret_key)))
    sign.update(six.b(project_id))
    sign.update(six.b(user))
    sign.update(six.b(expired))
    if user_info is not None:
        sign.update(six.b(user_info))
    token = sign.hexdigest()
    return token

########NEW FILE########
__FILENAME__ = client
# coding: utf-8
# Copyright (c) Alexandr Emelin. MIT license.

import six
import uuid
import time
import random

try:
    from urllib import urlencode
except ImportError:
    # python 3
    # noinspection PyUnresolvedReferences
    from urllib.parse import urlencode

from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.escape import json_decode
from tornado.gen import coroutine, Return, Task

from jsonschema import validate, ValidationError

from centrifuge import auth
from centrifuge.response import Response, MultiResponse
from centrifuge.log import logger
from centrifuge.schema import req_schema, client_api_schema

import toro


@coroutine
def sleep(seconds):
    """
    Non-blocking sleep.
    """
    awake_at = time.time() + seconds
    yield Task(IOLoop.instance().add_timeout, awake_at)
    raise Return((True, None))


class Client(object):
    """
    This class describes a single connection of client.
    """
    application = None

    def __init__(self, sock, info):
        self.sock = sock
        self.info = info
        self.uid = uuid.uuid4().hex
        self.is_authenticated = False
        self.user = None
        self.token = None
        self.examined_at = None
        self.channel_user_info = {}
        self.default_user_info = {}
        self.project_id = None
        self.channels = None
        self.presence_ping_task = None
        self.connect_queue = None
        logger.debug("new client created (uid: {0}, ip: {1})".format(
            self.uid, getattr(self.info, 'ip', '-')
        ))

    @coroutine
    def close(self):
        yield self.clean()
        logger.debug('client destroyed (uid: %s)' % self.uid)
        raise Return((True, None))

    @coroutine
    def clean(self):
        """
        Must be called when client connection closes. Here we are
        making different clean ups.
        """
        if self.presence_ping_task:
            self.presence_ping_task.stop()

        project_id = self.project_id

        if project_id:
            self.application.remove_connection(
                project_id, self.user, self.uid
            )

        if project_id and self.channels is not None:
            channels = self.channels.copy()
            for channel_name, channel_info in six.iteritems(channels):
                yield self.application.engine.remove_presence(
                    project_id, channel_name, self.uid
                )
                self.application.engine.remove_subscription(
                    project_id, channel_name, self
                )
                project, error = yield self.application.get_project(project_id)
                if not error and project:
                    namespace, error = yield self.application.get_namespace(
                        project, channel_name
                    )
                    if namespace and namespace.get("join_leave", False):
                        self.send_leave_message(channel_name)

        self.channels = None
        self.channel_user_info = None
        self.default_user_info = None
        self.project_id = None
        self.is_authenticated = False
        self.sock = None
        self.user = None
        self.token = None
        self.examined_at = None
        raise Return((True, None))

    @coroutine
    def close_sock(self, pause=True, pause_value=1):
        """
        Force closing connection.
        """
        if pause:
            # sleep for a while before closing connection to prevent mass invalid reconnects
            yield sleep(pause_value)

        try:
            if self.sock:
                self.sock.close()
            else:
                yield self.close()
        except Exception as err:
            logger.error(err)
        raise Return((True, None))

    @coroutine
    def send(self, response):
        """
        Send message directly to client.
        """
        if not self.sock:
            raise Return((False, None))

        try:
            self.sock.send(response)
        except Exception as err:
            logger.exception(err)
            yield self.close_sock(pause=False)
            raise Return((False, None))

        raise Return((True, None))

    @coroutine
    def process_obj(self, obj):

        response = Response()

        try:
            validate(obj, req_schema)
        except ValidationError as e:
            response.error = str(e)
            raise Return((response, response.error))

        uid = obj.get('uid', None)
        method = obj.get('method')
        params = obj.get('params')

        response.uid = uid
        response.method = method

        if method != 'connect' and not self.is_authenticated:
            response.error = self.application.UNAUTHORIZED
            raise Return((response, response.error))

        func = getattr(self, 'handle_%s' % method, None)

        if not func or not method in client_api_schema:
            response.error = "unknown method %s" % method
            raise Return((response, response.error))

        try:
            validate(params, client_api_schema[method])
        except ValidationError as e:
            response.error = str(e)
            raise Return((response, response.error))

        response.body, response.error = yield func(params)

        raise Return((response, None))

    @coroutine
    def message_received(self, message):
        """
        Called when message from client received.
        """
        multi_response = MultiResponse()
        try:
            data = json_decode(message)
        except ValueError:
            logger.error('malformed JSON data')
            yield self.close_sock()
            raise Return((True, None))

        if isinstance(data, dict):
            # single object request
            response, err = yield self.process_obj(data)
            multi_response.add(response)
            if err:
                # error occurred, connection must be closed
                logger.error(err)
                yield self.sock.send(multi_response.as_message())
                yield self.close_sock()
                raise Return((True, None))

        elif isinstance(data, list):
            # multiple object request
            if len(data) > self.application.CLIENT_API_MESSAGE_LIMIT:
                logger.debug("client API message limit exceeded")
                yield self.close_sock()
                raise Return((True, None))

            for obj in data:
                response, err = yield self.process_obj(obj)
                multi_response.add(response)
                if err:
                    # close connection in case of any error
                    logger.error(err)
                    yield self.sock.send(multi_response.as_message())
                    yield self.send_disconnect_message()
                    yield self.close_sock()
                    raise Return((True, None))

        else:
            logger.error('data not list and not dictionary')
            yield self.close_sock()
            raise Return((True, None))

        yield self.send(multi_response.as_message())

        raise Return((True, None))

    @coroutine
    def send_presence_ping(self):
        """
        Update presence information for all channels this client
        subscribed to.
        """
        for channel, channel_info in six.iteritems(self.channels):
            user_info = self.get_user_info(channel)
            if channel not in self.channels:
                continue
            yield self.application.engine.add_presence(
                self.project_id, channel, self.uid, user_info
            )
        raise Return((True, None))

    def get_user_info(self, channel):
        """
        Return channel specific user info.
        """
        try:
            channel_user_info = self.channel_user_info[channel]
        except KeyError:
            channel_user_info = None
        default_info = self.default_user_info.copy()
        default_info.update({
            'channel_info': channel_user_info
        })
        return default_info

    def update_channel_user_info(self, body, channel):
        """
        Try to extract channel specific user info from response body
        and keep it for channel.
        """
        try:
            info = json_decode(body)
        except Exception as e:
            logger.error(str(e))
            info = {}

        self.channel_user_info[channel] = info

    @coroutine
    def authorize(self, auth_address, project, channel):
        """
        Send POST request to web application to ask it if current client
        has a permission to subscribe on channel.
        """
        project_id = self.project_id

        http_client = AsyncHTTPClient()
        request = HTTPRequest(
            auth_address,
            method="POST",
            body=urlencode({
                'user': self.user,
                'channel': channel
            }),
            request_timeout=1
        )

        max_auth_attempts = project.get('max_auth_attempts')
        back_off_interval = project.get('back_off_interval')
        back_off_max_timeout = project.get('back_off_max_timeout')

        attempts = 0

        while attempts < max_auth_attempts:

            # get current timeout for project
            current_attempts = self.application.back_off.setdefault(project_id, 0)

            factor = random.randint(0, 2**current_attempts-1)
            timeout = factor*back_off_interval

            if timeout > back_off_max_timeout:
                timeout = back_off_max_timeout

            # wait before next authorization request attempt
            yield sleep(float(timeout)/1000)

            try:
                response = yield http_client.fetch(request)
            except Exception as err:
                # let it fail and try again after some timeout
                # until we have auth attempts
                logger.debug(err)
            else:
                # reset back-off attempts
                self.application.back_off[project_id] = 0

                if response.code == 200:
                    # auth successful
                    self.update_channel_user_info(response.body, channel)
                    raise Return((True, None))

                else:
                    # access denied for this client
                    raise Return((False, None))
            attempts += 1
            self.application.back_off[project_id] += 1

        raise Return((False, None))

    @coroutine
    def handle_ping(self, params):
        """
        Some hosting platforms (for example Heroku) disconnect websocket
        connection after a while if no payload transfer over network. To
        prevent such disconnects clients can periodically send ping messages
        to Centrifuge.
        """
        raise Return(('pong', None))

    @coroutine
    def handle_connect(self, params):
        """
        Authenticate client's connection, initialize required
        variables in case of successful authentication.
        """
        if self.application.collector:
            self.application.collector.incr('connect')

        if self.is_authenticated:
            raise Return((self.uid, None))

        token = params["token"]
        user = params["user"]
        project_id = params["project"]
        timestamp = params["timestamp"]
        user_info = params.get("info")

        project, error = yield self.application.get_project(project_id)
        if error:
            raise Return((None, error))

        secret_key = project['secret_key']

        try:
            client_token = auth.get_client_token(secret_key, project_id, user, timestamp, user_info=user_info)
        except Exception as err:
            logger.error(err)
            raise Return((None, "invalid connection parameters"))

        if token != client_token:
            raise Return((None, "invalid token"))

        if user_info is not None:
            try:
                user_info = json_decode(user_info)
            except Exception as err:
                logger.debug("malformed JSON data in user_info")
                logger.debug(err)
                user_info = None

        try:
            timestamp = int(timestamp)
        except ValueError:
            raise Return((None, "invalid timestamp"))

        now = time.time()

        self.user = user
        self.examined_at = timestamp

        connection_check = project.get('connection_check', False)

        if connection_check and self.examined_at + project.get("connection_lifetime", 24*365*3600) < now:
            # connection expired - this is a rare case when Centrifuge went offline
            # for a while or client turned on his computer from sleeping mode.

            # put this client into the queue of connections waiting for
            # permission to reconnect with expired credentials. To avoid waiting
            # client must reconnect with actual credentials i.e. reload browser
            # window.

            if project_id not in self.application.expired_reconnections:
                self.application.expired_reconnections[project_id] = []
            self.application.expired_reconnections[project_id].append(self)

            if project_id not in self.application.expired_connections:
                self.application.expired_connections[project_id] = {
                    "users": set(),
                    "checked_at": None
                }
            self.application.expired_connections[project_id]["users"].add(user)

            self.connect_queue = toro.Queue(maxsize=1)
            value = yield self.connect_queue.get()
            if not value:
                yield self.close_sock()
                raise Return((None, self.application.UNAUTHORIZED))
            else:
                self.connect_queue = None

        # Welcome to Centrifuge dear Connection!
        self.is_authenticated = True
        self.project_id = project_id
        self.token = token
        self.default_user_info = {
            'user_id': self.user,
            'client_id': self.uid,
            'default_info': user_info,
            'channel_info': None
        }
        self.channels = {}

        self.presence_ping_task = PeriodicCallback(
            self.send_presence_ping, self.application.engine.presence_ping_interval
        )
        self.presence_ping_task.start()

        self.application.add_connection(project_id, self.user, self.uid, self)

        raise Return((self.uid, None))

    @coroutine
    def handle_subscribe(self, params):
        """
        Subscribe client on channel.
        """
        project, error = yield self.application.get_project(self.project_id)
        if error:
            raise Return((None, error))

        channel = params.get('channel')
        if not channel:
            raise Return((None, 'channel required'))

        if len(channel) > self.application.MAX_CHANNEL_LENGTH:
            raise Return((None, 'maximum channel length exceeded'))

        body = {
            "channel": channel,
        }

        if self.application.USER_SEPARATOR in channel:
            users_allowed = channel.rsplit('#', 1)[1].split(',')
            if self.user not in users_allowed:
                raise Return((body, self.application.PERMISSION_DENIED))

        namespace, error = yield self.application.get_namespace(project, channel)
        if error:
            raise Return((body, error))

        project_id = self.project_id

        anonymous = namespace.get('anonymous', False)
        if not anonymous and not self.user:
            raise Return((body, self.application.PERMISSION_DENIED))

        is_private = namespace.get('is_private', False)

        if is_private:
            auth_address = namespace.get('auth_address', None)
            if not auth_address:
                auth_address = project.get('auth_address', None)
            if not auth_address:
                raise Return((body, 'no auth address found'))
            is_authorized, error = yield self.authorize(
                auth_address, project, channel
            )
            if error:
                raise Return((body, self.application.INTERNAL_SERVER_ERROR))
            if not is_authorized:
                raise Return((body, self.application.PERMISSION_DENIED))

        yield self.application.engine.add_subscription(
            project_id, channel, self
        )

        self.channels[channel] = True

        user_info = self.get_user_info(channel)

        yield self.application.engine.add_presence(
            project_id, channel, self.uid, user_info
        )

        if namespace.get('join_leave', False):
            self.send_join_message(channel)

        raise Return((body, None))

    @coroutine
    def handle_unsubscribe(self, params):
        """
        Unsubscribe client from channel.
        """
        project, error = yield self.application.get_project(self.project_id)
        if error:
            raise Return((None, error))

        channel = params.get('channel')

        if not channel:
            raise Return((None, "channel required"))

        body = {
            "channel": channel,
        }

        namespace, error = yield self.application.get_namespace(project, channel)
        if error:
            raise Return((body, error))

        project_id = self.project_id

        yield self.application.engine.remove_subscription(
            project_id, channel, self
        )

        try:
            del self.channels[channel]
        except KeyError:
            pass

        yield self.application.engine.remove_presence(
            project_id, channel, self.uid
        )

        if namespace.get('join_leave', False):
            self.send_leave_message(channel)

        raise Return((body, None))

    def check_channel_permission(self, channel):
        """
        Check that user subscribed on channel.
        """
        if channel in self.channels:
            return

        raise Return((None, self.application.PERMISSION_DENIED))

    @coroutine
    def handle_publish(self, params):
        """
        Publish message into channel.
        """
        project, error = yield self.application.get_project(self.project_id)
        if error:
            raise Return((None, error))

        channel = params.get('channel')

        body = {
            "channel": channel,
            "status": False
        }

        self.check_channel_permission(channel)

        namespace, error = yield self.application.get_namespace(project, channel)
        if error:
            raise Return((body, error))

        if not namespace.get('publish', False):
            raise Return((body, self.application.PERMISSION_DENIED))

        user_info = self.get_user_info(channel)

        result, error = yield self.application.process_publish(
            project,
            params,
            client=user_info
        )
        body["status"] = result
        raise Return((body, error))

    @coroutine
    def handle_presence(self, params):
        """
        Get presence information for channel.
        """
        project, error = yield self.application.get_project(self.project_id)
        if error:
            raise Return((None, error))

        channel = params.get('channel')

        body = {
            "channel": channel,
        }

        self.check_channel_permission(channel)

        namespace, error = yield self.application.get_namespace(project, channel)
        if error:
            raise Return((body, error))

        if not namespace.get('presence', False):
            raise Return((body, self.application.NOT_AVAILABLE))

        data, error = yield self.application.process_presence(
            project,
            params
        )
        body["data"] = data
        raise Return((body, error))

    @coroutine
    def handle_history(self, params):
        """
        Get message history for channel.
        """
        project, error = yield self.application.get_project(self.project_id)
        if error:
            raise Return((None, error))

        channel = params.get('channel')

        body = {
            "channel": channel,
        }

        self.check_channel_permission(channel)

        namespace, error = yield self.application.get_namespace(project, channel)
        if error:
            raise Return((body, error))

        if not namespace.get('history', False):
            raise Return((body, self.application.NOT_AVAILABLE))

        data, error = yield self.application.process_history(
            project,
            params
        )
        body["data"] = data
        raise Return((body, error))

    def send_join_leave_message(self, channel, message_method):
        """
        Generate and send message about join or leave event.
        """
        subscription_key = self.application.engine.get_subscription_key(
            self.project_id, channel
        )
        user_info = self.get_user_info(channel)
        message = {
            "channel": channel,
            "data": user_info
        }
        self.application.engine.publish_message(
            subscription_key, message, method=message_method
        )

    def send_join_message(self, channel):
        """
        Send join message to all channel subscribers when client
        subscribed on channel.
        """
        self.send_join_leave_message(channel, 'join')

    def send_leave_message(self, channel):
        """
        Send leave message to all channel subscribers when client
        unsubscribed from channel.
        """
        self.send_join_leave_message(channel, 'leave')

    @coroutine
    def send_disconnect_message(self, reason=None):
        """
        Send disconnect message - after receiving it proper client
        must close connection and do not reconnect.
        """
        reason = reason or "go away!"
        message_body = {
            "reason": reason
        }
        response = Response(method="disconnect", body=message_body)
        result, error = yield self.send(response.as_message())
        raise Return((result, error))

########NEW FILE########
__FILENAME__ = core
# coding: utf-8
# Copyright (c) Alexandr Emelin. MIT license.

import six
import uuid
import time
import socket
import json
from functools import partial

import tornado.web
import tornado.ioloop
from tornado.gen import coroutine, Return
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

try:
    from urllib import urlencode
except ImportError:
    # python 3
    # noinspection PyUnresolvedReferences
    from urllib.parse import urlencode

from centrifuge import utils
from centrifuge.structure import Structure
from centrifuge.log import logger
from centrifuge.forms import NamespaceForm, ProjectForm
from centrifuge.metrics import Collector, Exporter


def get_address():
    try:
        address = socket.gethostbyname(socket.gethostname())
    except Exception as err:
        logger.warning(err)
        address = "?"
    return address


class Application(tornado.web.Application):

    USER_SEPARATOR = '#'

    NAMESPACE_SEPARATOR = ":"

    # magic fake project ID for owner API purposes.
    OWNER_API_PROJECT_ID = '_'

    # magic project param name to allow owner make API operations within project
    OWNER_API_PROJECT_PARAM = '_project'

    # in milliseconds, how often this application will send ping message
    PING_INTERVAL = 5000

    # in seconds
    PING_MAX_DELAY = 10

    # in milliseconds, how often node will send its info into admin channel
    NODE_INFO_PUBLISH_INTERVAL = 10000

    # in milliseconds, how often application will remove stale ping information
    PING_REVIEW_INTERVAL = 10000

    # maximum length of channel name
    MAX_CHANNEL_LENGTH = 255

    # maximum number of messages in single admin API request
    ADMIN_API_MESSAGE_LIMIT = 100

    # maximum number of messages in single client API request
    CLIENT_API_MESSAGE_LIMIT = 100

    # does application check expiring connections?
    CONNECTION_EXPIRE_CHECK = True

    # how often in seconds this node should check expiring connections
    CONNECTION_EXPIRE_COLLECT_INTERVAL = 3

    # how often in seconds this node should check expiring connections
    CONNECTION_EXPIRE_CHECK_INTERVAL = 6

    # default metrics export interval in seconds
    METRICS_EXPORT_INTERVAL = 10

    LIMIT_EXCEEDED = 'limit exceeded'

    UNAUTHORIZED = 'unauthorized'

    PERMISSION_DENIED = 'permission denied'

    NOT_AVAILABLE = 'not available'

    INTERNAL_SERVER_ERROR = 'internal server error'

    METHOD_NOT_FOUND = 'method not found'

    PROJECT_NOT_FOUND = 'project not found'

    NAMESPACE_NOT_FOUND = 'namespace not found'

    DUPLICATE_NAME = 'duplicate name'

    def __init__(self, *args, **kwargs):

        # create unique uid for this application
        self.uid = uuid.uuid4().hex

        # initialize dict to keep administrator's connections
        self.admin_connections = {}

        # dictionary to keep client's connections
        self.connections = {}

        # dictionary to keep ping from nodes
        self.nodes = {}

        # storage to use
        self.storage = None

        # application structure manager (projects, namespaces etc)
        self.structure = None

        # application engine
        self.engine = None

        # initialize dict to keep back-off information for projects
        self.back_off = {}

        # list of coroutines that must be done before message publishing
        self.pre_publish_callbacks = []

        # list of coroutines that must be done after message publishing
        self.post_publish_callbacks = []

        # time of last node info revision
        self.node_info_revision_time = time.time()

        # periodic task to collect expired connections
        self.periodic_connection_expire_collect = None

        # periodic task to check expired connections
        self.periodic_connection_expire_check = None

        # dictionary to keep expired connections
        self.expired_connections = {}

        # dictionary to keep new connections with expired credentials until next connection check
        self.expired_reconnections = {}

        self.address = get_address()

        # count of messages published since last node info revision
        self.messages_published = 0

        # metrics collector class instance
        self.collector = None

        # metric exporter class instance
        self.exporter = None

        # periodic task to export collected metrics
        self.periodic_metrics_export = None

        # log collected metrics
        self.log_metrics = False

        # send collected metrics into admin channel
        self.admin_metrics = True

        # export collected metrics into Graphite
        self.graphite_metrics = False

        # initialize tornado's application
        super(Application, self).__init__(*args, **kwargs)

    def initialize(self):
        self.init_callbacks()
        self.init_structure()
        self.init_engine()
        self.init_ping()
        self.init_connection_expire_check()
        self.init_metrics()

    def init_structure(self):
        """
        Initialize structure manager using settings provided
        in configuration file.
        """
        custom_settings = self.settings['config']
        self.structure = Structure(self)
        self.structure.set_storage(self.storage)

        def run_periodic_structure_update():
            # update structure periodically from database. This is necessary to be sure
            # that application has actual and correct structure information. Structure
            # updates also triggered in real-time by message passing through control channel,
            # but in rare cases those update messages can be lost because of some kind of
            # network errors
            logger.info("Structure initialized")
            self.structure.update()
            structure_update_interval = custom_settings.get('structure_update_interval', 60)
            logger.info(
                "Periodic structure update interval: {0} seconds".format(
                    structure_update_interval
                )
            )
            periodic_structure_update = tornado.ioloop.PeriodicCallback(
                self.structure.update, structure_update_interval*1000
            )
            periodic_structure_update.start()

        tornado.ioloop.IOLoop.instance().add_callback(
            partial(
                self.storage.connect,
                run_periodic_structure_update
            )
        )

    def init_engine(self):
        """
        Initialize engine.
        """
        tornado.ioloop.IOLoop.instance().add_callback(self.engine.initialize)

    def init_callbacks(self):
        """
        Fill custom callbacks with callable objects provided in config.
        """
        config = self.settings['config']

        pre_publish_callbacks = config.get('pre_publish_callbacks', [])
        for callable_path in pre_publish_callbacks:
            callback = utils.namedAny(callable_path)
            self.pre_publish_callbacks.append(callback)

        post_publish_callbacks = config.get('post_publish_callbacks', [])
        for callable_path in post_publish_callbacks:
            callback = utils.namedAny(callable_path)
            self.post_publish_callbacks.append(callback)

    def init_connection_expire_check(self):
        """
        Initialize periodic connection expiration check task if enabled.
        We periodically check the time of client connection expiration time
        and ask web application about these clients - are they still active in
        web application?
        """

        if not self.CONNECTION_EXPIRE_CHECK:
            return

        self.periodic_connection_expire_collect = tornado.ioloop.PeriodicCallback(
            self.collect_expired_connections,
            self.CONNECTION_EXPIRE_COLLECT_INTERVAL*1000
        )
        self.periodic_connection_expire_collect.start()

        tornado.ioloop.IOLoop.instance().add_timeout(
            time.time()+self.CONNECTION_EXPIRE_CHECK_INTERVAL,
            self.check_expired_connections
        )

    def init_metrics(self):
        """
        Initialize metrics collector - different counters, timers in
        Centrifuge which then will be exported into web interface, log or
        Graphite.
        """
        config = self.settings['config']
        metrics_config = config.get('metrics', {})

        self.admin_metrics = metrics_config.get('admin', True)
        self.log_metrics = metrics_config.get('log', False)
        self.graphite_metrics = metrics_config.get('graphite', False)

        if not self.log_metrics and not self.admin_metrics and not self.graphite_metrics:
            return

        self.collector = Collector()

        if self.graphite_metrics:

            prefix = metrics_config.get("graphite_prefix", "")
            if prefix and not prefix.endswith(Exporter.SEP):
                prefix = prefix + Exporter.SEP

            prefix += self.name

            self.exporter = Exporter(
                metrics_config["graphite_host"],
                metrics_config["graphite_port"],
                prefix=prefix
            )

        self.periodic_metrics_export = tornado.ioloop.PeriodicCallback(
            self.flush_metrics,
            metrics_config.get("interval", self.METRICS_EXPORT_INTERVAL)*1000
        )
        self.periodic_metrics_export.start()

    def flush_metrics(self):

        if not self.collector:
            return

        for key, value in six.iteritems(self.get_node_gauges()):
            self.collector.gauge(key, value)

        metrics = self.collector.get()

        if self.admin_metrics:
            self.publish_node_info(metrics)

        if self.log_metrics:
            logger.info(metrics)

        if self.graphite_metrics:
            self.exporter.export(metrics)

    @property
    def name(self):
        if self.settings['options'].name:
            return self.settings['options'].name
        return self.address.replace(".", "_") + '_' + str(self.settings['options'].port)

    def send_ping(self, ping_message):
        self.engine.publish_control_message(ping_message)

    def review_ping(self):
        """
        Remove outdated information about other nodes.
        """
        now = time.time()
        outdated = []
        for node, params in self.nodes.items():
            updated_at = params["updated_at"]
            if now - updated_at > self.PING_MAX_DELAY:
                outdated.append(node)
        for node in outdated:
            try:
                del self.nodes[node]
            except KeyError:
                pass

    def init_ping(self):
        """
        Start periodic tasks for sending ping and reviewing ping.
        """
        message = {
            'app_id': self.uid,
            'method': 'ping',
            'params': {
                'uid': self.uid,
                'name': self.name
            }
        }
        send_ping = partial(self.engine.publish_control_message, message)
        ping = tornado.ioloop.PeriodicCallback(send_ping, self.PING_INTERVAL)
        tornado.ioloop.IOLoop.instance().add_timeout(
            self.PING_INTERVAL, ping.start
        )

        review_ping = tornado.ioloop.PeriodicCallback(self.review_ping, self.PING_REVIEW_INTERVAL)
        tornado.ioloop.IOLoop.instance().add_timeout(
            self.PING_INTERVAL, review_ping.start
        )

    def get_node_gauges(self):
        gauges = {
            'channels': len(self.engine.subscriptions),
            'clients': sum(len(v) for v in six.itervalues(self.engine.subscriptions)),
            'unique_clients': sum(len(v) for v in six.itervalues(self.connections)),
        }
        return gauges

    def publish_node_info(self, metrics):
        """
        Publish information about current node into admin channel
        """
        self.engine.publish_admin_message({
            "admin": True,
            "type": "node",
            "data": {
                "uid": self.uid,
                "nodes": len(self.nodes) + 1,
                "name": self.name,
                "metrics": metrics
            }
        })

    @coroutine
    def collect_expired_connections(self):
        """
        Find all expired connections in projects to check them later.
        """
        projects, error = yield self.structure.project_list()
        if error:
            logger.error(error)
            raise Return((None, error))

        for project in projects:

            project_id = project['_id']
            expired_connections, error = yield self.collect_project_expired_connections(project)
            if error:
                logger.error(error)
                continue

            if project_id not in self.expired_connections:
                self.expired_connections[project_id] = {
                    "users": set(),
                    "checked_at": None
                }

            current_expired_connections = self.expired_connections[project_id]["users"]
            self.expired_connections[project_id]["users"] = current_expired_connections | expired_connections

        raise Return((True, None))

    @coroutine
    def collect_project_expired_connections(self, project):
        """
        Find users in project whose connections expired.
        """
        project_id = project.get("_id")
        to_return = set()
        now = time.time()
        if not project.get('connection_check') or project_id not in self.connections:
            raise Return((to_return, None))

        for user, user_connections in six.iteritems(self.connections[project_id]):

            if user == '':
                # do not collect anonymous connections
                continue

            for uid, client in six.iteritems(user_connections):
                if client.examined_at and client.examined_at + project.get("connection_lifetime", 24*365*3600) < now:
                    to_return.add(user)

        raise Return((to_return, None))

    @coroutine
    def check_expired_connections(self):
        """
        For each project ask web application about users whose connections expired.
        Close connections of deactivated users and keep valid users' connections.
        """
        projects, error = yield self.structure.project_list()
        if error:
            raise Return((None, error))

        checks = []
        for project in projects:
            if project.get('connection_check', False):
                checks.append(self.check_project_expired_connections(project))

        try:
            # run all checks in parallel
            yield checks
        except Exception as err:
            logger.error(err)

        tornado.ioloop.IOLoop.instance().add_timeout(
            time.time()+self.CONNECTION_EXPIRE_CHECK_INTERVAL,
            self.check_expired_connections
        )

        raise Return((True, None))

    @coroutine
    def check_project_expired_connections(self, project):

        now = time.time()
        project_id = project['_id']

        checked_at = self.expired_connections.get(project_id, {}).get("checked_at")
        if checked_at and (now - checked_at < project.get("connection_check_interval", 60)):
            raise Return((True, None))

        users = self.expired_connections.get(project_id, {}).get("users", {}).copy()
        if not users:
            raise Return((True, None))

        self.expired_connections[project_id]["users"] = set()

        expired_reconnect_clients = self.expired_reconnections.get(project_id, [])[:]
        self.expired_reconnections[project_id] = []

        inactive_users, error = yield self.check_users(project, users)
        if error:
            raise Return((False, error))

        self.expired_connections[project_id]["checked_at"] = now
        now = time.time()

        clients_to_disconnect = []

        if isinstance(inactive_users, list):
            # a list of inactive users received, iterate trough connections
            # destroy inactive, update active.
            if project_id in self.connections:
                for user, user_connections in six.iteritems(self.connections[project_id]):
                    for uid, client in six.iteritems(user_connections):
                        if client.user in inactive_users:
                            clients_to_disconnect.append(client)
                        elif client.user in users:
                            client.examined_at = now

        for client in clients_to_disconnect:
            yield client.send_disconnect_message("deactivated")
            yield client.close_sock()

        if isinstance(inactive_users, list):
            # now deal with users waiting for reconnect with expired credentials
            for client in expired_reconnect_clients:
                is_valid = client.user not in inactive_users
                if is_valid:
                    client.examined_at = now
                if client.connect_queue:
                    yield client.connect_queue.put(is_valid)
                else:
                    yield client.close_sock()

        raise Return((True, None))

    @staticmethod
    @coroutine
    def check_users(project, users, timeout=5):

        address = project.get("connection_check_address")
        if not address:
            logger.debug("no connection check address for project {0}".format(project['name']))
            raise Return(())

        http_client = AsyncHTTPClient()
        request = HTTPRequest(
            address,
            method="POST",
            body=urlencode({
                'users': json.dumps(list(users))
            }),
            request_timeout=timeout
        )

        try:
            response = yield http_client.fetch(request)
        except Exception as err:
            logger.error(err)
            raise Return((None, None))
        else:
            if response.code != 200:
                raise Return((None, None))

            try:
                content = [str(x) for x in json.loads(response.body)]
            except Exception as err:
                logger.error(err)
                raise Return((None, err))

            raise Return((content, None))

    def add_connection(self, project_id, user, uid, client):
        """
        Register new client's connection.
        """
        if project_id not in self.connections:
            self.connections[project_id] = {}
        if user not in self.connections[project_id]:
            self.connections[project_id][user] = {}

        self.connections[project_id][user][uid] = client

    def remove_connection(self, project_id, user, uid):
        """
        Remove client's connection
        """
        try:
            del self.connections[project_id][user][uid]
        except KeyError:
            pass

        if project_id in self.connections and user in self.connections[project_id]:
            # clean connections
            if self.connections[project_id][user]:
                return
            try:
                del self.connections[project_id][user]
            except KeyError:
                pass
            if self.connections[project_id]:
                return
            try:
                del self.connections[project_id]
            except KeyError:
                pass

    def add_admin_connection(self, uid, client):
        """
        Register administrator's connection (from web-interface).
        """
        self.admin_connections[uid] = client

    def remove_admin_connection(self, uid):
        """
        Remove administrator's connection.
        """
        try:
            del self.admin_connections[uid]
        except KeyError:
            pass

    @coroutine
    def get_project(self, project_id):
        """
        Project settings can change during client's connection.
        Every time we need project - we must extract actual
        project data from structure.
        """
        project, error = yield self.structure.get_project_by_id(project_id)
        if error:
            raise Return((None, self.INTERNAL_SERVER_ERROR))
        if not project:
            raise Return((None, self.PROJECT_NOT_FOUND))
        raise Return((project, None))

    def extract_namespace_name(self, channel):
        """
        Get namespace name from channel name
        """
        if self.NAMESPACE_SEPARATOR in channel:
            # namespace:rest_of_channel
            namespace_name = channel.split(self.NAMESPACE_SEPARATOR, 1)[0]
        else:
            namespace_name = None

        return namespace_name

    @coroutine
    def get_namespace(self, project, channel):

        namespace_name = self.extract_namespace_name(channel)

        if not namespace_name:
            raise Return((project, None))

        namespace, error = yield self.structure.get_namespace_by_name(
            project, namespace_name
        )
        if error:
            raise Return((None, self.INTERNAL_SERVER_ERROR))
        if not namespace:
            raise Return((None, self.NAMESPACE_NOT_FOUND))
        raise Return((namespace, None))

    @coroutine
    def handle_ping(self, params):
        """
        Ping message received.
        """
        params['updated_at'] = time.time()
        self.nodes[params.get('uid')] = params

    @coroutine
    def handle_unsubscribe(self, params):
        """
        Unsubscribe message received - unsubscribe client from certain channels.
        """
        project = params.get("project")
        user = params.get("user")
        channel = params.get("channel", None)

        project_id = project['_id']

        # try to find user's connection
        user_connections = self.connections.get(project_id, {}).get(user, {})
        if not user_connections:
            raise Return((True, None))

        for uid, connection in six.iteritems(user_connections):

            if not channel:
                # unsubscribe from all channels
                for chan, channel_info in six.iteritems(connection.channels):
                    yield connection.handle_unsubscribe({
                        "channel": chan
                    })
            else:
                # unsubscribe from certain channel
                yield connection.handle_unsubscribe({
                    "channel": channel
                })

        raise Return((True, None))

    @coroutine
    def handle_disconnect(self, params):
        """
        Handle disconnect message - when user deactivated in web application
        and its connections must be closed by Centrifuge by force
        """
        project = params.get("project")
        user = params.get("user")
        reason = params.get("reason", None)

        project_id = project['_id']

        # try to find user's connection
        user_connections = self.connections.get(project_id, {}).get(user, {})
        if not user_connections:
            raise Return((True, None))

        clients_to_disconnect = []

        for uid, client in six.iteritems(user_connections):
            clients_to_disconnect.append(client)

        for client in clients_to_disconnect:
            yield client.send_disconnect_message(reason=reason)
            yield client.close_sock(pause=False)

        raise Return((True, None))

    @coroutine
    def handle_update_structure(self, params):
        """
        Update structure message received - structure changed and other
        node sent us a signal about update.
        """
        result, error = yield self.structure.update()
        raise Return((result, error))

    # noinspection PyCallingNonCallable
    @coroutine
    def process_call(self, project, method, params):
        """
        Call appropriate method from this class according to specified method.
        Note, that all permission checking must be done before calling this method.
        """
        handle_func = getattr(self, "process_%s" % method, None)

        if handle_func:
            result, error = yield handle_func(project, params)
            raise Return((result, error))
        else:
            raise Return((None, self.METHOD_NOT_FOUND))

    @coroutine
    def publish_message(self, project, message):
        """
        Publish event into PUB socket stream
        """
        project_id = message['project_id']
        channel = message['channel']

        namespace, error = yield self.get_namespace(project, channel)
        if error:
            raise Return((False, error))

        if namespace.get('is_watching', False):
            # send to admin channel
            self.engine.publish_admin_message(message)

        # send to event channel
        subscription_key = self.engine.get_subscription_key(
            project_id, channel
        )

        # no need in project id when sending message to clients
        del message['project_id']

        self.engine.publish_message(subscription_key, message)

        if namespace.get('history', False):
            yield self.engine.add_history_message(
                project_id, channel, message,
                history_size=namespace.get('history_size'),
                history_expire=namespace.get('history_expire', 0)
            )

        if self.collector:
            self.collector.incr('messages')

        raise Return((True, None))

    @coroutine
    def prepare_message(self, project, params, client):
        """
        Prepare message before actual publishing.
        """
        data = params.get('data', None)

        message = {
            'project_id': project['_id'],
            'uid': uuid.uuid4().hex,
            'timestamp': int(time.time()),
            'client': client,
            'channel': params.get('channel'),
            'data': data
        }

        for callback in self.pre_publish_callbacks:
            try:
                message = yield callback(message)
            except Exception as err:
                logger.exception(err)
            else:
                if message is None:
                    raise Return((None, None))

        raise Return((message, None))

    @coroutine
    def process_publish(self, project, params, client=None):
        """
        Publish message into appropriate channel.
        """
        message, error = yield self.prepare_message(
            project, params, client
        )
        if error:
            raise Return((False, self.INTERNAL_SERVER_ERROR))

        if not message:
            # message was discarded
            raise Return((False, None))

        # publish prepared message
        result, error = yield self.publish_message(
            project, message
        )
        if error:
            raise Return((False, error))

        for callback in self.post_publish_callbacks:
            try:
                yield callback(message)
            except Exception as err:
                logger.exception(err)

        raise Return((True, None))

    @coroutine
    def process_history(self, project, params):
        """
        Return a list of last messages sent into channel.
        """
        project_id = project['_id']
        channel = params.get("channel")
        data, error = yield self.engine.get_history(project_id, channel)
        if error:
            raise Return((data, self.INTERNAL_SERVER_ERROR))
        raise Return((data, None))

    @coroutine
    def process_presence(self, project, params):
        """
        Return current presence information for channel.
        """
        project_id = project['_id']
        channel = params.get("channel")
        data, error = yield self.engine.get_presence(project_id, channel)
        if error:
            raise Return((data, self.INTERNAL_SERVER_ERROR))
        raise Return((data, None))

    @coroutine
    def process_unsubscribe(self, project, params):
        """
        Unsubscribe user from channels.
        """
        params["project"] = project
        message = {
            'app_id': self.uid,
            'method': 'unsubscribe',
            'params': params
        }

        # handle on this node
        result, error = yield self.handle_unsubscribe(params)

        # send to other nodes
        self.engine.publish_control_message(message)

        if error:
            raise Return((result, self.INTERNAL_SERVER_ERROR))
        raise Return((result, None))

    @coroutine
    def process_disconnect(self, project, params):
        """
        Unsubscribe user from channels.
        """
        params["project"] = project
        message = {
            'app_id': self.uid,
            'method': 'disconnect',
            'params': params
        }

        # handle on this node
        result, error = yield self.handle_disconnect(params)

        # send to other nodes
        self.engine.publish_control_message(message)

        if error:
            raise Return((result, self.INTERNAL_SERVER_ERROR))
        raise Return((result, None))

    @coroutine
    def process_dump_structure(self, project, params):

        projects, error = yield self.structure.project_list()
        if error:
            raise Return((None, self.INTERNAL_SERVER_ERROR))

        namespaces, error = yield self.structure.namespace_list()
        if error:
            raise Return((None, self.INTERNAL_SERVER_ERROR))

        data = {
            "projects": projects,
            "namespaces": namespaces
        }
        raise Return((data, None))

    @coroutine
    def process_project_list(self, project, params):
        projects, error = yield self.structure.project_list()
        if error:
            raise Return((None, self.INTERNAL_SERVER_ERROR))
        raise Return((projects, None))

    @coroutine
    def process_project_get(self, project, params):
        if not project:
            raise Return((None, self.PROJECT_NOT_FOUND))
        raise Return((project, None))

    @coroutine
    def process_project_by_name(self, project, params):
        project, error = yield self.structure.get_project_by_name(
            params.get("name")
        )
        if error:
            raise Return((None, self.INTERNAL_SERVER_ERROR))
        if not project:
            raise Return((None, self.PROJECT_NOT_FOUND))
        raise Return((project, None))

    @coroutine
    def process_project_create(self, project, params, error_form=False):

        form = ProjectForm(params)

        if form.validate():
            existing_project, error = yield self.structure.get_project_by_name(
                form.name.data
            )
            if error:
                raise Return((None, self.INTERNAL_SERVER_ERROR))

            if existing_project:
                form.name.errors.append(self.DUPLICATE_NAME)
                if error_form:
                    raise Return((None, form))
                raise Return((None, form.errors))
            else:
                project, error = yield self.structure.project_create(
                    **form.data
                )
                if error:
                    raise Return((None, self.INTERNAL_SERVER_ERROR))
                raise Return((project, None))
        else:
            if error_form:
                raise Return((None, form))
            raise Return((None, form.errors))

    @coroutine
    def process_project_edit(self, project, params, error_form=False, patch=True):
        """
        Edit project namespace.
        """
        if not project:
            raise Return((None, self.PROJECT_NOT_FOUND))

        if "name" not in params:
            params["name"] = project["name"]

        boolean_patch_data = {}
        if patch:
            boolean_patch_data = utils.get_boolean_patch_data(ProjectForm.BOOLEAN_FIELDS, params)

        form = ProjectForm(params)

        if form.validate():

            if "name" in params and params["name"] != project["name"]:

                existing_project, error = yield self.structure.get_project_by_name(
                    params["name"]
                )
                if error:
                    raise Return((None, self.INTERNAL_SERVER_ERROR))
                if existing_project:
                    form.name.errors.append(self.DUPLICATE_NAME)
                    if error_form:
                        raise Return((None, form))
                    raise Return((None, form.errors))

            updated_project = project.copy()

            if patch:
                data = utils.make_patch_data(form, params)
            else:
                data = form.data.copy()

            updated_project.update(data)
            if patch:
                updated_project.update(boolean_patch_data)
            project, error = yield self.structure.project_edit(
                project, **updated_project
            )
            if error:
                raise Return((None, self.INTERNAL_SERVER_ERROR))
            raise Return((project, None))
        else:
            if error_form:
                raise Return((None, form))
            raise Return((None, form.errors))

    @coroutine
    def process_project_delete(self, project, params):
        if not project:
            raise Return((None, self.PROJECT_NOT_FOUND))
        result, error = yield self.structure.project_delete(project)
        if error:
            raise Return((None, self.INTERNAL_SERVER_ERROR))
        raise Return((True, None))

    @coroutine
    def process_regenerate_secret_key(self, project, params):
        if not project:
            raise Return((None, self.PROJECT_NOT_FOUND))
        result, error = yield self.structure.regenerate_project_secret_key(project)
        if error:
            raise Return((None, self.INTERNAL_SERVER_ERROR))
        raise Return((result, None))

    @coroutine
    def process_namespace_list(self, project, params):
        """
        Return a list of all namespaces for project.
        """
        if not project:
            raise Return((None, self.PROJECT_NOT_FOUND))
        namespaces, error = yield self.structure.get_project_namespaces(project)
        if error:
            raise Return((None, self.INTERNAL_SERVER_ERROR))
        raise Return((namespaces, None))

    @coroutine
    def process_namespace_get(self, project, params):
        """
        Return a list of all namespaces for project.
        """
        namespace_id = params.get('_id')
        namespace, error = yield self.structure.get_namespace_by_id(namespace_id)
        if error:
            raise Return((None, self.INTERNAL_SERVER_ERROR))
        if not namespace:
            raise Return((None, self.NAMESPACE_NOT_FOUND))
        raise Return((namespace, None))

    @coroutine
    def process_namespace_by_name(self, project, params):
        if not project:
            raise Return((None, self.PROJECT_NOT_FOUND))

        namespace, error = yield self.structure.get_namespace_by_name(
            project, params.get("name")
        )
        if error:
            raise Return((None, self.INTERNAL_SERVER_ERROR))
        if not namespace:
            raise Return((None, self.NAMESPACE_NOT_FOUND))
        raise Return((namespace, None))

    @coroutine
    def process_namespace_create(self, project, params, error_form=False):
        """
        Create new namespace in project or update if already exists.
        """
        if not project:
            raise Return((None, self.PROJECT_NOT_FOUND))

        form = NamespaceForm(params)

        if form.validate():
            existing_namespace, error = yield self.structure.get_namespace_by_name(
                project, form.name.data
            )
            if error:
                raise Return((None, self.INTERNAL_SERVER_ERROR))

            if existing_namespace:
                form.name.errors.append(self.DUPLICATE_NAME)
                if error_form:
                    raise Return((None, form))
                raise Return((None, form.errors))
            else:
                namespace, error = yield self.structure.namespace_create(
                    project, **form.data
                )
                if error:
                    raise Return((None, self.INTERNAL_SERVER_ERROR))
                raise Return((namespace, None))
        else:
            if error_form:
                raise Return((None, form))
            raise Return((None, form.errors))

    @coroutine
    def process_namespace_edit(self, project, params, error_form=False, patch=True):
        """
        Edit project namespace.
        """
        namespace, error = yield self.structure.get_namespace_by_id(
            params.pop('_id')
        )
        if error:
            raise Return((None, self.INTERNAL_SERVER_ERROR))

        if not namespace:
            raise Return((None, self.NAMESPACE_NOT_FOUND))

        if not project:
            project, error = yield self.get_project(
                namespace['project_id']
            )
            if error:
                raise Return((None, error))

        if "name" not in params:
            params["name"] = namespace["name"]

        boolean_patch_data = {}
        if patch:
            boolean_patch_data = utils.get_boolean_patch_data(NamespaceForm.BOOLEAN_FIELDS, params)

        form = NamespaceForm(params)

        if form.validate():

            if "name" in params and params["name"] != namespace["name"]:

                existing_namespace, error = yield self.structure.get_namespace_by_name(
                    project, params["name"]
                )
                if error:
                    raise Return((None, self.INTERNAL_SERVER_ERROR))
                if existing_namespace:
                    form.name.errors.append(self.DUPLICATE_NAME)
                    if error_form:
                        raise Return((None, form))
                    raise Return((None, form.errors))

            updated_namespace = namespace.copy()
            if patch:
                data = utils.make_patch_data(form, params)
            else:
                data = form.data.copy()
            updated_namespace.update(data)
            if patch:
                updated_namespace.update(boolean_patch_data)
            namespace, error = yield self.structure.namespace_edit(
                namespace, **updated_namespace
            )
            if error:
                raise Return((None, self.INTERNAL_SERVER_ERROR))
            raise Return((namespace, None))
        else:
            if error_form:
                raise Return((None, form))
            raise Return((None, form.errors))

    @coroutine
    def process_namespace_delete(self, project, params):
        """
        Delete project namespace.
        """
        namespace_id = params["_id"]

        existing_namespace, error = yield self.structure.get_namespace_by_id(namespace_id)
        if error:
            raise Return((None, self.INTERNAL_SERVER_ERROR))
        if not existing_namespace:
            raise Return((None, self.NAMESPACE_NOT_FOUND))

        result, error = yield self.structure.namespace_delete(existing_namespace)
        if error:
            raise Return((None, self.INTERNAL_SERVER_ERROR))
        raise Return((True, None))

########NEW FILE########
__FILENAME__ = memory
# coding: utf-8
# Copyright (c) Alexandr Emelin. MIT license.

import time
import six
import heapq

from tornado.gen import coroutine, Return
from tornado.escape import json_encode
from tornado.ioloop import PeriodicCallback

from centrifuge.response import Response
from centrifuge.log import logger
from centrifuge.engine import BaseEngine


class Engine(BaseEngine):

    NAME = 'In memory - single node only'

    HISTORY_EXPIRE_TASK_INTERVAL = 60000  # once in a minute

    def __init__(self, *args, **kwargs):
        super(Engine, self).__init__(*args, **kwargs)
        self.subscriptions = {}
        self.history = {}
        self.history_expire_at = {}
        self.history_expire_heap = []
        self.presence = {}
        self.deactivated = {}
        self.history_expire_task = PeriodicCallback(
            self.check_history_expire,
            self.HISTORY_EXPIRE_TASK_INTERVAL
        )

    def initialize(self):
        self.history_expire_task.start()
        logger.info("Memory engine initialized")

    @coroutine
    def publish_message(self, channel, body, method=BaseEngine.DEFAULT_PUBLISH_METHOD):
        yield self.handle_message(channel, method, body)
        raise Return((True, None))

    @coroutine
    def publish_control_message(self, message):
        yield self.handle_control_message(message)
        raise Return((True, None))

    @coroutine
    def publish_admin_message(self, message):
        yield self.handle_admin_message(message)
        raise Return((True, None))

    @coroutine
    def handle_admin_message(self, message):
        message = json_encode(message)
        for uid, connection in six.iteritems(self.application.admin_connections):
            if uid not in self.application.admin_connections:
                continue
            connection.send(message)

        raise Return((True, None))

    @coroutine
    def handle_control_message(self, message):
        """
        Handle control message.
        """
        app_id = message.get("app_id")
        method = message.get("method")
        params = message.get("params")

        if app_id and app_id == self.application.uid:
            # application id must be set when we don't want to do
            # make things twice for the same application. Setting
            # app_id means that we don't want to process control
            # message when it is appear in application instance if
            # application uid matches app_id
            raise Return((True, None))

        func = getattr(self.application, 'handle_%s' % method, None)
        if not func:
            raise Return((None, self.application.METHOD_NOT_FOUND))

        result, error = yield func(params)
        raise Return((result, error))

    @coroutine
    def handle_message(self, channel, method, body):

        if channel not in self.subscriptions:
            raise Return((True, None))

        timer = None
        if self.application.collector:
            timer = self.application.collector.get_timer('broadcast')

        response = Response(method=method, body=body)
        prepared_response = response.as_message()
        for uid, client in six.iteritems(self.subscriptions[channel]):
            if channel in self.subscriptions and uid in self.subscriptions[channel]:
                yield client.send(prepared_response)

        if timer:
            timer.stop()

        raise Return((True, None))

    @coroutine
    def add_subscription(self, project_id, channel, client):
        """
        Subscribe application on channel if necessary and register client
        to receive messages from that channel.
        """
        subscription_key = self.get_subscription_key(project_id, channel)

        if subscription_key not in self.subscriptions:
            self.subscriptions[subscription_key] = {}

        self.subscriptions[subscription_key][client.uid] = client

        raise Return((True, None))

    @coroutine
    def remove_subscription(self, project_id, channel, client):
        """
        Unsubscribe application from channel if necessary and prevent client
        from receiving messages from that channel.
        """
        subscription_key = self.get_subscription_key(project_id, channel)

        try:
            del self.subscriptions[subscription_key][client.uid]
        except KeyError:
            pass

        try:
            if not self.subscriptions[subscription_key]:
                del self.subscriptions[subscription_key]
        except KeyError:
            pass

        raise Return((True, None))

    def get_presence_key(self, project_id, channel):
        return "%s:presence:%s:%s" % (self.prefix, project_id, channel)

    @coroutine
    def add_presence(self, project_id, channel, uid, user_info, presence_timeout=None):
        now = int(time.time())
        expire_at = now + (presence_timeout or self.presence_timeout)

        hash_key = self.get_presence_key(project_id, channel)

        if hash_key not in self.presence:
            self.presence[hash_key] = {}

        self.presence[hash_key][uid] = {
            'expire_at': expire_at,
            'user_info': user_info
        }

        raise Return((True, None))

    @coroutine
    def remove_presence(self, project_id, channel, uid):
        hash_key = self.get_presence_key(project_id, channel)
        try:
            del self.presence[hash_key][uid]
        except KeyError:
            pass

        raise Return((True, None))

    @coroutine
    def get_presence(self, project_id, channel):
        now = int(time.time())
        hash_key = self.get_presence_key(project_id, channel)
        to_return = {}
        if hash_key in self.presence:
            keys_to_delete = []
            for uid, data in six.iteritems(self.presence[hash_key]):
                expire_at = data['expire_at']
                if expire_at > now:
                    to_return[uid] = data['user_info']
                else:
                    keys_to_delete.append(uid)

            for uid in keys_to_delete:
                try:
                    del self.presence[hash_key][uid]
                except KeyError:
                    pass

            if not self.presence[hash_key]:
                try:
                    del self.presence[hash_key]
                except KeyError:
                    pass

        raise Return((to_return, None))

    def get_history_key(self, project_id, channel):
        return "%s:history:%s:%s" % (self.prefix, project_id, channel)

    @coroutine
    def add_history_message(self, project_id, channel, message, history_size=None, history_expire=0):

        history_key = self.get_history_key(project_id, channel)

        if history_expire:
            expire_at = int(time.time()) + history_expire
            self.history_expire_at[history_key] = expire_at
            heapq.heappush(self.history_expire_heap, (expire_at, history_key))
        elif history_key in self.history_expire_at:
            del self.history_expire_at[history_key]

        if history_key not in self.history:
            self.history[history_key] = []

        history_size = history_size or self.history_size

        self.history[history_key].insert(0, message)
        self.history[history_key] = self.history[history_key][:history_size]

        raise Return((True, None))

    @coroutine
    def get_history(self, project_id, channel):
        history_key = self.get_history_key(project_id, channel)

        now = int(time.time())

        if history_key in self.history_expire_at:
            expire_at = self.history_expire_at[history_key]
            if expire_at <= now:
                self.remove_history(history_key)
                raise Return(([], None))

        try:
            data = self.history[history_key]
        except KeyError:
            data = []

        raise Return((data, None))

    def remove_history(self, history_key):
        try:
            del self.history[history_key]
        except KeyError:
            pass
        try:
            del self.history_expire_at[history_key]
        except KeyError:
            pass

    def check_history_expire(self):
        now = int(time.time())
        while True:
            try:
                expire, history_key = heapq.heappop(self.history_expire_heap)
            except IndexError:
                return

            if expire <= now:
                if history_key in self.history_expire_at and self.history_expire_at[history_key] <= now:
                    self.remove_history(history_key)
            else:
                break
########NEW FILE########
__FILENAME__ = redis
# coding: utf-8
# Copyright (c) Alexandr Emelin. MIT license.

import time
import six

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from tornado.ioloop import PeriodicCallback
from tornado.gen import coroutine, Return, Task
from tornado.iostream import StreamClosedError
from tornado.escape import json_encode, json_decode

import toredis

from centrifuge.response import Response
from centrifuge.log import logger
from centrifuge.engine import BaseEngine

from tornado.options import define

define(
    "redis_host", default="localhost", help="Redis host", type=str
)

define(
    "redis_port", default=6379, help="Redis port", type=int
)

define(
    "redis_db", default=0, help="Redis database number", type=int
)

define(
    "redis_password", default="", help="Redis auth password", type=str
)

define(
    "redis_url", default="", help="Redis URL", type=str
)


range_func = six.moves.xrange


def prepare_key_value(pair):
    if not pair:
        return
    key = pair[0].decode()
    try:
        value = json_decode(pair[1].decode())
    except ValueError:
        value = {}
    return key, value


def dict_from_list(key_value_list):
    # noinspection PyTypeChecker
    return dict(
        prepare_key_value(key_value_list[i:i+2]) for i in range_func(0, len(key_value_list), 2)
    )


class Engine(BaseEngine):

    NAME = 'Redis'

    OK_RESPONSE = b'OK'

    def __init__(self, *args, **kwargs):
        super(Engine, self).__init__(*args, **kwargs)

        if not self.options.redis_url:
            self.host = self.options.redis_host
            self.port = self.options.redis_port
            self.password = self.options.redis_password
            self.db = self.options.redis_db
        else:
            # according to https://devcenter.heroku.com/articles/redistogo
            parsed_url = urlparse.urlparse(self.options.redis_url)
            self.host = parsed_url.hostname
            self.port = int(parsed_url.port)
            self.db = 0
            self.password = parsed_url.password

        self.connection_check = PeriodicCallback(self.check_connection, 1000)
        self._need_reconnect = False

        self.subscriber = toredis.Client(io_loop=self.io_loop)
        self.publisher = toredis.Client(io_loop=self.io_loop)
        self.worker = toredis.Client(io_loop=self.io_loop)

        self.subscriptions = {}

    def initialize(self):
        self.connect()
        logger.info("Redis engine at {0}:{1} (db {2})".format(self.host, self.port, self.db))

    def on_auth(self, res):
        if res != self.OK_RESPONSE:
            logger.error("auth failed: {0}".format(res))

    def on_subscriber_select(self, res):
        """
        After selecting subscriber database subscribe on channels
        """
        if res != self.OK_RESPONSE:
            # error returned
            logger.error("select database failed: {0}".format(res))
            self._need_reconnect = True
            return

        self.subscriber.subscribe(self.admin_channel_name, callback=self.on_redis_message)
        self.subscriber.subscribe(self.control_channel_name, callback=self.on_redis_message)

        for subscription in self.subscriptions.copy():
            if subscription not in self.subscriptions:
                continue
            self.subscriber.subscribe(subscription, callback=self.on_redis_message)

    def on_select(self, res):
        if res != self.OK_RESPONSE:
            logger.error("select database failed: {0}".format(res))
            self._need_reconnect = True

    def connect(self):
        """
        Connect from scratch
        """
        try:
            self.subscriber.connect(host=self.host, port=self.port)
            self.publisher.connect(host=self.host, port=self.port)
            self.worker.connect(host=self.host, port=self.port)
        except Exception as e:
            logger.error("error connecting to Redis server: %s" % (str(e)))
        else:
            if self.password:
                self.subscriber.auth(self.password, callback=self.on_auth)
                self.publisher.auth(self.password, callback=self.on_auth)
                self.worker.auth(self.password, callback=self.on_auth)

            self.subscriber.select(self.db, callback=self.on_subscriber_select)
            self.publisher.select(self.db, callback=self.on_select)
            self.worker.select(self.db, callback=self.on_select)

        self.connection_check.stop()
        self.connection_check.start()

    def check_connection(self):
        conn_statuses = [
            self.subscriber.is_connected(),
            self.publisher.is_connected(),
            self.worker.is_connected()
        ]
        connection_dropped = not all(conn_statuses)
        if connection_dropped or self._need_reconnect:
            logger.info('reconnecting to Redis')
            self._need_reconnect = False
            self.connect()

    def _publish(self, channel, message):
        try:
            self.publisher.publish(channel, message)
        except StreamClosedError as e:
            self._need_reconnect = True
            logger.error(e)
            return False
        else:
            return True

    @coroutine
    def publish_message(self, channel, body, method=BaseEngine.DEFAULT_PUBLISH_METHOD):
        """
        Publish message into channel of stream.
        """
        response = Response()
        method = method or self.DEFAULT_PUBLISH_METHOD
        response.method = method
        response.body = body
        to_publish = response.as_message()
        result = self._publish(channel, to_publish)
        raise Return((result, None))

    @coroutine
    def publish_control_message(self, message):
        result = self._publish(self.control_channel_name, json_encode(message))
        raise Return((result, None))

    @coroutine
    def publish_admin_message(self, message):
        result = self._publish(self.admin_channel_name, json_encode(message))
        raise Return((result, None))

    @coroutine
    def on_redis_message(self, redis_message):
        """
        Got message from Redis, dispatch it into right message handler.
        """
        msg_type = redis_message[0]
        if six.PY3:
            msg_type = msg_type.decode()

        if msg_type != 'message':
            return

        channel = redis_message[1]
        if six.PY3:
            channel = channel.decode()

        if channel == self.control_channel_name:
            yield self.handle_control_message(json_decode(redis_message[2]))
        elif channel == self.admin_channel_name:
            yield self.handle_admin_message(json_decode(redis_message[2]))
        else:
            yield self.handle_message(channel, redis_message[2])

    @coroutine
    def handle_admin_message(self, message):
        message = json_encode(message)
        for uid, connection in six.iteritems(self.application.admin_connections):
            if uid not in self.application.admin_connections:
                continue
            connection.send(message)

        raise Return((True, None))

    @coroutine
    def handle_control_message(self, message):
        """
        Handle control message.
        """
        app_id = message.get("app_id")
        method = message.get("method")
        params = message.get("params")

        if app_id and app_id == self.application.uid:
            # application id must be set when we don't want to do
            # make things twice for the same application. Setting
            # app_id means that we don't want to process control
            # message when it is appear in application instance if
            # application uid matches app_id
            raise Return((True, None))

        func = getattr(self.application, 'handle_%s' % method, None)
        if not func:
            raise Return((None, self.application.METHOD_NOT_FOUND))

        result, error = yield func(params)
        raise Return((result, error))

    @coroutine
    def handle_message(self, channel, message_data):
        if channel not in self.subscriptions:
            raise Return((True, None))
        for uid, client in six.iteritems(self.subscriptions[channel]):
            if channel in self.subscriptions and uid in self.subscriptions[channel]:
                yield client.send(message_data)

    def subscribe_key(self, subscription_key):
        self.subscriber.subscribe(
            subscription_key, callback=self.on_redis_message
        )

    def unsubscribe_key(self, subscription_key):
        self.subscriber.unsubscribe(subscription_key)

    @coroutine
    def add_subscription(self, project_id, channel, client):
        """
        Subscribe application on channel if necessary and register client
        to receive messages from that channel.
        """
        subscription_key = self.get_subscription_key(project_id, channel)

        self.subscribe_key(subscription_key)

        if subscription_key not in self.subscriptions:
            self.subscriptions[subscription_key] = {}

        self.subscriptions[subscription_key][client.uid] = client

        raise Return((True, None))

    @coroutine
    def remove_subscription(self, project_id, channel, client):
        """
        Unsubscribe application from channel if necessary and prevent client
        from receiving messages from that channel.
        """
        subscription_key = self.get_subscription_key(project_id, channel)

        try:
            del self.subscriptions[subscription_key][client.uid]
        except KeyError:
            pass

        try:
            if not self.subscriptions[subscription_key]:
                self.unsubscribe_key(subscription_key)
                del self.subscriptions[subscription_key]
        except KeyError:
            pass

        raise Return((True, None))

    def get_presence_hash_key(self, project_id, channel):
        return "%s:presence:hash:%s:%s" % (self.prefix, project_id, channel)

    def get_presence_set_key(self, project_id, channel):
        return "%s:presence:set:%s:%s" % (self.prefix, project_id, channel)

    def get_history_list_key(self, project_id, channel):
        return "%s:history:list:%s:%s" % (self.prefix, project_id, channel)

    @coroutine
    def add_presence(self, project_id, channel, uid, user_info, presence_timeout=None):
        now = int(time.time())
        expire_at = now + (presence_timeout or self.presence_timeout)
        hash_key = self.get_presence_hash_key(project_id, channel)
        set_key = self.get_presence_set_key(project_id, channel)
        try:
            pipeline = self.worker.pipeline()
            pipeline.multi()
            pipeline.zadd(set_key, {uid: expire_at})
            pipeline.hset(hash_key, uid, json_encode(user_info))
            pipeline.execute()
            yield Task(pipeline.send)
        except StreamClosedError as e:
            raise Return((None, e))
        else:
            raise Return((True, None))

    @coroutine
    def remove_presence(self, project_id, channel, uid):
        hash_key = self.get_presence_hash_key(project_id, channel)
        set_key = self.get_presence_set_key(project_id, channel)
        try:
            pipeline = self.worker.pipeline()
            pipeline.hdel(hash_key, uid)
            pipeline.zrem(set_key, uid)
            yield Task(pipeline.send)
        except StreamClosedError as e:
            raise Return((None, e))
        else:
            raise Return((True, None))

    @coroutine
    def get_presence(self, project_id, channel):
        now = int(time.time())
        hash_key = self.get_presence_hash_key(project_id, channel)
        set_key = self.get_presence_set_key(project_id, channel)
        try:
            expired_keys = yield Task(self.worker.zrangebyscore, set_key, 0, now)
            if expired_keys:
                pipeline = self.worker.pipeline()
                pipeline.zremrangebyscore(set_key, 0, now)
                pipeline.hdel(hash_key, [x.decode() for x in expired_keys])
                yield Task(pipeline.send)
            data = yield Task(self.worker.hgetall, hash_key)
        except StreamClosedError as e:
            raise Return((None, e))
        else:
            raise Return((dict_from_list(data), None))

    @coroutine
    def add_history_message(self, project_id, channel, message, history_size=None, history_expire=0):
        history_size = history_size or self.history_size
        history_list_key = self.get_history_list_key(project_id, channel)
        try:
            pipeline = self.worker.pipeline()
            pipeline.lpush(history_list_key, json_encode(message))
            pipeline.ltrim(history_list_key, 0, history_size - 1)
            if history_expire:
                pipeline.expire(history_list_key, history_expire)
            else:
                pipeline.persist(history_list_key)
            yield Task(pipeline.send)
        except StreamClosedError as e:
            raise Return((None, e))
        else:
            raise Return((True, None))

    @coroutine
    def get_history(self, project_id, channel):
        history_list_key = self.get_history_list_key(project_id, channel)
        try:
            data = yield Task(self.worker.lrange, history_list_key, 0, -1)
        except StreamClosedError as e:
            raise Return((None, e))
        else:
            raise Return(([json_decode(x.decode()) for x in data], None))

########NEW FILE########
__FILENAME__ = forms
# coding: utf-8
# Copyright (c) Alexandr Emelin. MIT license.

import re
from wtforms import TextField, IntegerField, BooleanField, validators
from centrifuge.utils import Form


# regex pattern to match project and namespace names
NAME_PATTERN = r'^[-a-zA-Z0-9_]{2,}$'

NAME_PATTERN_DESCRIPTION = 'must consist of letters, numbers, underscores or hyphens'

NAME_RE = re.compile(NAME_PATTERN)

# how many times we are trying to authorize subscription by default
DEFAULT_MAX_AUTH_ATTEMPTS = 5

# milliseconds, increment for back-off
DEFAULT_BACK_OFF_INTERVAL = 100

# milliseconds, max timeout between auth attempts
DEFAULT_BACK_OFF_MAX_TIMEOUT = 5000

# how many messages keep in channel history by default
DEFAULT_HISTORY_SIZE = 50

# how long in seconds we keep history in inactive channels (0 - forever until size is not exceeded)
DEFAULT_HISTORY_EXPIRE = 3600*24  # 24 hours by default


class ProjectMixin(object):

    BOOLEAN_FIELDS = ['connection_check']

    name = TextField(
        label='project name',
        validators=[
            validators.Regexp(regex=NAME_RE, message="invalid name")
        ],
        description="project name: {0}".format(NAME_PATTERN_DESCRIPTION)
    )

    display_name = TextField(
        label='display name',
        validators=[
            validators.Length(min=3, max=50),
            validators.Optional()
        ],
        description="human readable project name, will be used in web interface"
    )

    connection_check = BooleanField(
        label='connection check',
        validators=[],
        default=False,
        description="check expired connections sending POST request to web application"
    )

    connection_lifetime = IntegerField(
        label='connection lifetime in seconds',
        validators=[
            validators.NumberRange(min=1)
        ],
        default=3600,
        description="time interval in seconds for connection to expire. Keep it as large "
                    "as possible in your case."
    )

    connection_check_address = TextField(
        label='connection check url address',
        validators=[
            validators.URL(require_tld=False),
            validators.Optional()
        ],
        description="url address to check connections by periodically sending POST request "
                    "to it with list of users with expired connections. "
    )

    connection_check_interval = IntegerField(
        label='minimum connection check interval in seconds',
        validators=[
            validators.NumberRange(min=1)
        ],
        default=10,
        description="minimum time interval in seconds between periodic connection "
                    "check POST requests to your web application."
    )

    max_auth_attempts = IntegerField(
        label='maximum auth attempts',
        validators=[
            validators.NumberRange(min=1, max=100)
        ],
        default=DEFAULT_MAX_AUTH_ATTEMPTS,
        description="maximum amount of POST requests from Centrifuge to your application "
                    "during client's authorization"
    )

    back_off_interval = IntegerField(
        label='back-off interval',
        validators=[
            validators.NumberRange(min=50, max=10000)
        ],
        default=DEFAULT_BACK_OFF_INTERVAL,
        description="interval increment in milliseconds in authorization back-off mechanism. "
                    "Please, keep it default until you know what you do"
    )

    back_off_max_timeout = IntegerField(
        label='back-off max timeout',
        validators=[
            validators.NumberRange(min=50, max=120000)
        ],
        default=DEFAULT_BACK_OFF_MAX_TIMEOUT,
        description="maximum interval in milliseconds between authorization requests. "
                    "Please, keep it default until you know what you do"
    )


class NamespaceMixin(object):

    BOOLEAN_FIELDS = [
        'is_watching', 'is_private', 'publish',
        'presence', 'history', 'join_leave', 'anonymous'
    ]

    is_watching = BooleanField(
        label='is watching',
        validators=[],
        default=True,
        description="publish messages into admin channel "
                    "(messages will be visible in web interface). Turn it off "
                    "if you expect high load in channels."
    )

    is_private = BooleanField(
        label='is private',
        validators=[],
        default=False,
        description="authorize every subscription on channel using "
                    "POST request to provided auth address (see below)"
    )

    auth_address = TextField(
        label='auth url address',
        validators=[
            validators.URL(require_tld=False),
            validators.Optional()
        ],
        description="url address to authorize clients sending POST request to it"
    )

    publish = BooleanField(
        label='publish',
        validators=[],
        default=False,
        description="allow clients to publish messages in channels "
                    "(your web application never receive those messages)"
    )

    anonymous = BooleanField(
        label='anonymous access',
        validators=[],
        default=False,
        description="allow anonymous (with empty USER ID) clients to subscribe on channels"
    )

    presence = BooleanField(
        label='presence',
        validators=[],
        default=True,
        description="enable presence information for channels "
                    "(state must be configured)"
    )

    history = BooleanField(
        label='history',
        validators=[],
        default=True,
        description="enable history information for channels "
                    "(state must be configured)"
    )

    history_size = IntegerField(
        label="history size",
        validators=[
            validators.NumberRange(min=1)
        ],
        default=DEFAULT_HISTORY_SIZE,
        description="maximum amount of messages in history for single channel"
    )

    history_expire = IntegerField(
        label="history expire",
        validators=[
            validators.NumberRange(min=0)
        ],
        default=DEFAULT_HISTORY_EXPIRE,
        description="time in seconds to keep history for inactive channels. 0 - "
                    "do not expire at all - not recommended though as this can lead to"
                    "memory leaks (as Centrifuge keeps all history in memory), default "
                    "is 86400 seconds (24 hours)"
    )

    join_leave = BooleanField(
        label="join/leave messages",
        validators=[],
        default=True,
        description="send join(leave) messages when client subscribes on channel "
                    "(unsubscribes from channel)"
    )


class ProjectForm(ProjectMixin, NamespaceMixin, Form):

    BOOLEAN_FIELDS = ProjectMixin.BOOLEAN_FIELDS + NamespaceMixin.BOOLEAN_FIELDS


class NamespaceNameMixin(object):

    name = TextField(
        label='namespace name',
        validators=[
            validators.Regexp(regex=NAME_RE, message="invalid name")
        ],
        description="unique namespace name: {0}".format(NAME_PATTERN_DESCRIPTION)
    )


class NamespaceForm(NamespaceNameMixin, NamespaceMixin, Form):

    field_order = ('name', '*')

########NEW FILE########
__FILENAME__ = handlers
# coding: utf-8
# Copyright (c) Alexandr Emelin. MIT license.

import tornado.web
from tornado.gen import coroutine, Return
from sockjs.tornado import SockJSConnection

from jsonschema import validate, ValidationError

from centrifuge import auth
from centrifuge.log import logger
from centrifuge.response import Response, MultiResponse
from centrifuge.client import Client
from centrifuge.schema import req_schema, server_api_schema, owner_api_methods


class BaseHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        user = self.get_secure_cookie("user")
        if not user:
            return None
        return user

    def json_response(self, to_return):
        """
        Finish asynchronous request and return JSON response.
        """
        self.set_header('Content-Type', 'application/json; charset=utf-8')
        self.finish(to_return)

    @property
    def opts(self):
        return self.settings.get('config', {})


class ApiHandler(BaseHandler):
    """
    Listen for incoming POST request, authorize it and in case off
    successful authorization process requested action for project.
    """
    def check_xsrf_cookie(self):
        """
        No need in CSRF protection here.
        """
        pass

    @coroutine
    def process_object(self, obj, project, is_owner_request):

        response = Response()

        try:
            validate(obj, req_schema)
        except ValidationError as e:
            response.error = str(e)
            raise Return(response)

        req_id = obj.get("uid", None)
        method = obj.get("method")
        params = obj.get("params")

        response.uid = req_id
        response.method = method

        schema = server_api_schema

        if is_owner_request and self.application.OWNER_API_PROJECT_PARAM in params:

            project_id = params[self.application.OWNER_API_PROJECT_PARAM]

            project, error = yield self.application.structure.get_project_by_id(
                project_id
            )
            if error:
                logger.error(error)
                response.error = self.application.INTERNAL_SERVER_ERROR
            if not project:
                response.error = self.application.PROJECT_NOT_FOUND

        try:
            params.pop(self.application.OWNER_API_PROJECT_PARAM)
        except KeyError:
            pass

        if not is_owner_request and method in owner_api_methods:
            response.error = self.application.PERMISSION_DENIED

        if not response.error:
            if method not in schema:
                response.error = self.application.METHOD_NOT_FOUND
            else:
                try:
                    validate(params, schema[method])
                except ValidationError as e:
                    response.error = str(e)
                else:
                    result, error = yield self.application.process_call(
                        project, method, params
                    )
                    response.body = result
                    response.error = error

        raise Return(response)

    @coroutine
    def post(self, project_id):
        """
        Handle API HTTP requests.
        """
        if not self.request.body:
            raise tornado.web.HTTPError(400, log_message="empty request")

        sign = self.get_argument('sign', None)

        if not sign:
            raise tornado.web.HTTPError(400, log_message="no data sign")

        encoded_data = self.get_argument('data', None)
        if not encoded_data:
            raise tornado.web.HTTPError(400, log_message="no data")

        is_owner_request = False

        if project_id == self.application.OWNER_API_PROJECT_ID:
            # API request aims to be from superuser
            is_owner_request = True

        if is_owner_request:
            # use api secret key from configuration to check sign
            secret = self.application.settings["config"].get("api_secret")
            if not secret:
                raise tornado.web.HTTPError(501, log_message="no api_secret in configuration file")
            project = None

        else:
            project, error = yield self.application.structure.get_project_by_id(project_id)
            if error:
                raise tornado.web.HTTPError(500, log_message=str(error))
            if not project:
                raise tornado.web.HTTPError(404, log_message="project not found")

            # use project secret key to validate sign
            secret = project['secret_key']

        is_valid = auth.check_sign(
            secret, project_id, encoded_data, sign
        )

        if not is_valid:
            raise tornado.web.HTTPError(401, log_message="unauthorized")

        data = auth.decode_data(encoded_data)
        if not data:
            raise tornado.web.HTTPError(400, log_message="malformed data")

        multi_response = MultiResponse()

        if isinstance(data, dict):
            # single object request
            response = yield self.process_object(data, project, is_owner_request)
            multi_response.add(response)
        elif isinstance(data, list):
            # multiple object request
            if len(data) > self.application.ADMIN_API_MESSAGE_LIMIT:
                raise tornado.web.HTTPError(
                    400,
                    log_message="admin API message limit exceeded (received {0} messages)".format(
                        len(data)
                    )
                )

            for obj in data:
                response = yield self.process_object(obj, project, is_owner_request)
                multi_response.add(response)
        else:
            raise tornado.web.HTTPError(400, log_message="data not a list or dictionary")

        if self.application.collector:
            self.application.collector.incr('api')

        self.json_response(multi_response.as_message())


class SockjsConnection(SockJSConnection):

    def on_open(self, info):
        if self.session:
            self.client = Client(self, info)
            if self.session.transport_name != 'rawwebsocket':
                self.session.start_heartbeat()
        else:
            self.close()

    @coroutine
    def on_message(self, message):
        yield self.client.message_received(message)
        raise Return((True, None))

    @coroutine
    def on_close(self):
        if hasattr(self, 'client'):
            yield self.client.close()
            del self.client
        raise Return((True, None))

########NEW FILE########
__FILENAME__ = log
# coding: utf-8
# Copyright (c) Alexandr Emelin. MIT license.

import logging

logger = logging.getLogger('centrifuge')
logger.setLevel(logging.DEBUG)


########NEW FILE########
__FILENAME__ = metrics
# coding: utf-8
# Copyright (c) Alexandr Emelin. MIT license.

import six
import time
import socket
import logging
from functools import wraps
from collections import defaultdict


logger = logging.getLogger('metrics')


class MetricError(Exception):
    pass


class Timer(object):
    """
    Measure time interval between events
    """

    def __init__(self, collector, metric):
        self.collector = collector
        self.metric = metric
        self.interval = None
        self._sent = False
        self._start_time = None

    def __call__(self, f):
        @wraps(f)
        def wrapper(*args, **kw):
            with self:
                return f(*args, **kw)
        return wrapper

    def __enter__(self):
        return self.start()

    def __exit__(self, t, val, tb):
        self.stop()

    def start(self):
        self.interval = None
        self._sent = False
        self._start_time = time.time()
        return self

    def stop(self, send=True):
        if self._start_time is None:
            raise MetricError("Can not stop - timer not started")
        delta = time.time() - self._start_time
        self.interval = int(round(1000 * delta))  # to milliseconds.
        if send:
            self.send()
        return self.interval

    def send(self):
        if self.interval is None:
            raise MetricError('No time interval recorded')
        if self._sent:
            raise MetricError('Already sent')
        self._sent = True
        self.collector.timing(self.metric, self.interval)


class Collector(object):
    """
    Class to collect and aggregate statistical metrics.
    Lots of ideas and some code borrowed from Statsd server/client
    implementations and adapted to use with Centrifuge.
    """
    SEP = '.'

    def __init__(self, sep=None):
        self.sep = sep or self.SEP
        self._counters = None
        self._times = None
        self._gauges = None
        self._last_reset = None
        self.reset()

    def get(self):
        prepared_data = self.prepare_data()
        self.reset()
        return prepared_data

    def prepare_data(self):
        timestamp = time.time()
        to_return = {}

        for metric, value in six.iteritems(self._counters):
            to_return[metric + self.sep + 'count'] = value
            to_return[metric + self.sep + 'rate'] = round(value / (timestamp - self._last_reset), 2)

        for metric, value in six.iteritems(self._gauges):
            to_return[metric] = value

        for metric, intervals in six.iteritems(self._times):
            prepared_timing_data = self.prepare_timing_data(intervals)
            for key, value in six.iteritems(prepared_timing_data):
                to_return[metric + self.sep + key] = value

        return to_return

    @classmethod
    def prepare_timing_data(cls, intervals):
        min_interval = intervals[0]
        max_interval = 0
        avg_interval = 0
        total = 0
        count = 0
        for interval in intervals:
            interval = float(interval)
            count += 1
            total += interval
            if interval > max_interval:
                max_interval = interval
            if interval < min_interval:
                min_interval = interval
        if count:
            avg_interval = round(total / count, 2)

        return {
            "min": min_interval,
            "max": max_interval,
            "avg": avg_interval,
            "count": count
        }

    def reset(self):
        self._counters = defaultdict(int)
        self._times = defaultdict(list)
        self._gauges = defaultdict(int)
        self._last_reset = time.time()

    def timing(self, metric, interval):
        if metric not in self._times:
            self._times[metric] = []
        self._times[metric].append(interval)

    def increment(self, metric, incr_by=1):
        if metric not in self._counters:
            self._counters[metric] = 0
        self._counters[metric] += incr_by

    incr = increment

    def decrement(self, metric, decr_by=1):
        self.incr(metric, -decr_by)

    decr = decrement

    def gauge(self, metric, value):
        self._gauges[metric] = value

    def get_timer(self, time_name, start=True):
        timer = Timer(self, time_name)
        if start:
            return timer.start()
        return timer


class Exporter(object):
    """
    Export collected metrics into Graphite
    """

    SEP = "."

    def __init__(self, host, port, prefix=None, sep=None, max_udp_size=512):
        self.host = host
        self.port = port
        self.prefix = prefix or ""
        self.sep = sep or self.SEP
        self._address = (socket.gethostbyname(host), port)
        self.max_udp_size = max_udp_size
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(0)

    def get_key(self, metric):
        if not self.prefix:
            return metric
        if self.prefix.endswith(self.sep):
            return self.prefix + metric
        else:
            return self.prefix + self.sep + metric

    def prepare_metrics(self, metrics):
        to_return = []
        timestamp = int(time.time())
        for metric, value in six.iteritems(metrics):
            to_return.append('{0} {1} {2}'.format(self.get_key(metric), int(value), timestamp))
        return to_return

    def export(self, metrics):
        if not metrics:
            return

        prepared_metrics = self.prepare_metrics(metrics)

        data = prepared_metrics.pop(0)
        while prepared_metrics:
            stat = prepared_metrics.pop(0)
            if len(stat) + len(data) + 1 >= self.max_udp_size:
                self.send(data)
                data = stat
            else:
                data += '\n' + stat

        self.send(data)

    def send(self, data):
        try:
            self.socket.sendto(data.encode('ascii'), self._address)
        except Exception as err:
            logger.exception(err)

########NEW FILE########
__FILENAME__ = node
# coding: utf-8
# Copyright (c) Alexandr Emelin. MIT license.

import os
import sys
import json
import tornado
import tornado.web
import tornado.ioloop
import tornado.options
import tornado.httpserver
from tornado.options import define, options

from centrifuge.utils import namedAny


define(
    "debug", default=False, help="tornado debug mode", type=bool
)

define(
    "port", default=8000, help="app port", type=int
)

define(
    "config", default='config.json', help="JSON config file", type=str
)

define(
    "name", default='', help="unique node name", type=str
)


engine = os.environ.get('CENTRIFUGE_ENGINE')
if not engine or engine == 'memory':
    engine_class_path = 'centrifuge.engine.memory.Engine'
elif engine == "redis":
    engine_class_path = 'centrifuge.engine.redis.Engine'
else:
    engine_class_path = engine

engine_class = namedAny(engine_class_path)


storage = os.environ.get('CENTRIFUGE_STORAGE')
if not storage or storage == 'sqlite':
    storage_class_path = 'centrifuge.structure.sqlite.Storage'
elif storage == "file":
    storage_class_path = 'centrifuge.structure.file.Storage'
else:
    storage_class_path = storage

storage_class = namedAny(storage_class_path)


tornado.options.parse_command_line()


from centrifuge.log import logger
from centrifuge.core import Application

from sockjs.tornado import SockJSRouter

from centrifuge.handlers import ApiHandler
from centrifuge.handlers import SockjsConnection
from centrifuge.handlers import Client

from centrifuge.web.handlers import MainHandler
from centrifuge.web.handlers import AuthHandler
from centrifuge.web.handlers import LogoutHandler
from centrifuge.web.handlers import AdminSocketHandler
from centrifuge.web.handlers import Http404Handler
from centrifuge.web.handlers import ProjectCreateHandler
from centrifuge.web.handlers import NamespaceFormHandler
from centrifuge.web.handlers import ProjectDetailHandler
from centrifuge.web.handlers import StructureDumpHandler
from centrifuge.web.handlers import StructureLoadHandler


def stop_running(msg):
    """
    Called only during initialization when critical error occurred.
    """
    logger.error(msg)
    sys.exit(1)


def create_application_handlers(sockjs_settings):

    handlers = [
        tornado.web.url(
            r'/', MainHandler, name="main"
        ),
        tornado.web.url(
            r'/project/create$',
            ProjectCreateHandler,
            name="project_create"
        ),
        tornado.web.url(
            r'/project/([^/]+)/([^/]+)$',
            ProjectDetailHandler,
            name="project_detail"
        ),
        tornado.web.url(
            r'/project/([^/]+)/namespace/create$',
            NamespaceFormHandler,
            name="namespace_create"
        ),
        tornado.web.url(
            r'/project/([^/]+)/namespace/edit/([^/]+)/',
            NamespaceFormHandler,
            name="namespace_edit"
        ),
        tornado.web.url(
            r'/api/([^/]+)$', ApiHandler, name="api"
        ),
        tornado.web.url(
            r'/auth$', AuthHandler, name="auth"
        ),
        tornado.web.url(
            r'/logout$', LogoutHandler, name="logout"
        ),
        tornado.web.url(
            r'/dumps$', StructureDumpHandler, name="dump_structure"
        ),
        tornado.web.url(
            r'/loads$', StructureLoadHandler, name="load_structure"
        )
    ]

    # create SockJS route for admin connections
    admin_sock_router = SockJSRouter(
        AdminSocketHandler, '/socket', user_settings=sockjs_settings
    )
    handlers = admin_sock_router.urls + handlers

    # create SockJS route for client connections
    client_sock_router = SockJSRouter(
        SockjsConnection, '/connection', user_settings=sockjs_settings
    )
    handlers = client_sock_router.urls + handlers

    # match everything else to 404 handler
    handlers.append(
        tornado.web.url(
            r'.*', Http404Handler, name='http404'
        )
    )

    return handlers


def main():

    try:
        custom_settings = json.load(open(options.config, 'r'))
    except IOError:
        logger.warning(
            "Application started without configuration file.\n"
            "This is normal only during development"
        )
        custom_settings = {}

    ioloop_instance = tornado.ioloop.IOLoop.instance()

    settings = dict(
        cookie_secret=custom_settings.get("cookie_secret", "bad secret"),
        login_url="/auth",
        template_path=os.path.join(
            os.path.dirname(__file__),
            os.path.join("web/frontend", "templates")
        ),
        static_path=os.path.join(
            os.path.dirname(__file__),
            os.path.join("web/frontend", "static")
        ),
        xsrf_cookies=True,
        autoescape="xhtml_escape",
        debug=options.debug,
        options=options,
        config=custom_settings
    )

    sockjs_settings = custom_settings.get("sockjs_settings", {})

    handlers = create_application_handlers(sockjs_settings)

    try:
        app = Application(handlers=handlers, **settings)
        server = tornado.httpserver.HTTPServer(app)
        server.listen(options.port)
    except Exception as e:
        return stop_running(str(e))

    logger.info("Engine class: {0}".format(engine_class_path))
    app.engine = engine_class(app)

    logger.info("Storage class: {0}".format(storage_class_path))
    app.storage = storage_class(options)

    # create references to application from SockJS handlers
    AdminSocketHandler.application = app
    Client.application = app

    app.initialize()

    max_channel_length = custom_settings.get('max_channel_length')
    if max_channel_length:
        app.MAX_CHANNEL_LENGTH = max_channel_length

    admin_api_message_limit = custom_settings.get('admin_api_message_limit')
    if admin_api_message_limit:
        app.ADMIN_API_MESSAGE_LIMIT = admin_api_message_limit

    client_api_message_limit = custom_settings.get('client_api_message_limit')
    if client_api_message_limit:
        app.CLIENT_API_MESSAGE_LIMIT = client_api_message_limit

    owner_api_project_id = custom_settings.get('owner_api_project_id')
    if owner_api_project_id:
        app.OWNER_API_PROJECT_ID = owner_api_project_id

    owner_api_project_param = custom_settings.get('owner_api_project_param')
    if owner_api_project_param:
        app.OWNER_API_PROJECT_PARAM = owner_api_project_param

    connection_expire_check = custom_settings.get('connection_expire_check', True)
    if connection_expire_check:
        app.CONNECTION_EXPIRE_CHECK = connection_expire_check

    connection_expire_collect_interval = custom_settings.get('connection_expire_collect_interval')
    if connection_expire_collect_interval:
        app.CONNECTION_EXPIRE_COLLECT_INTERVAL = connection_expire_collect_interval

    connection_expire_check_interval = custom_settings.get('connection_expire_check_interval')
    if connection_expire_check_interval:
        app.CONNECTION_EXPIRE_CHECK_INTERVAL = connection_expire_check_interval

    logger.info("Tornado port: {0}".format(options.port))

    # finally, let's go
    try:
        ioloop_instance.start()
    except KeyboardInterrupt:
        logger.info('interrupted')
    finally:
        # cleaning
        if hasattr(app.engine, 'clean'):
            app.engine.clean()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = response
# coding: utf-8
# Copyright (c) Alexandr Emelin. MIT license.

from tornado.escape import json_encode


class Response(object):

    def __init__(self, uid=None, method=None, error=None, body=None):
        self.uid = uid
        self.method = method
        self.error = error
        self.body = body

    def as_message(self):
        return json_encode(self.as_dict())

    def as_dict(self):
        return {
            'uid': self.uid,
            'method': self.method,
            'error': self.error,
            'body': self.body
        }


class MultiResponse(object):

    def __init__(self):
        self.responses = []

    def add(self, response):
        self.responses.append(response)

    def add_many(self, responses):
        for response in responses:
            self.add(response)

    def as_message(self):
        return json_encode(self.as_list_of_dicts())

    def as_list_of_dicts(self):
        return [x.as_dict() for x in self.responses]

########NEW FILE########
__FILENAME__ = schema
# coding: utf-8
# Copyright (c) Alexandr Emelin. MIT license.

req_schema = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string"
        },
        "method": {
            "type": "string"
        },
        "params": {
            "type": "object"
        }
    },
    "required": ["method", "params"]
}

owner_api_methods = [
    "project_list", "project_create", "dump_structure"
]

server_api_schema = {
    "publish": {
        "type": "object",
        "properties": {
            "channel": {
                "type": "string"
            }
        },
        "required": ["channel"]
    },
    "presence": {
        "type": "object",
        "properties": {
            "channel": {
                "type": "string"
            }
        },
        "required": ["channel"]
    },
    "history": {
        "type": "object",
        "properties": {
            "channel": {
                "type": "string"
            }
        },
        "required": ["channel"]
    },
    "unsubscribe": {
        "type": "object",
        "properties": {
            "user": {
                "type": "string"
            },
            "channel": {
                "type": "string"
            }
        },
        "required": ["user"]
    },
    "disconnect": {
        "type": "object",
        "properties": {
            "user": {
                "type": "string"
            },
            "reason": {
                "type": "string"
            }
        },
        "required": ["user"]
    },
    "namespace_list": {
        "type": "object",
        "properties": {}
    },
    "namespace_by_name": {
        "type": "object",
        "properties": {
            "_id": {
                "type": "string"
            },
            "name": {
                "type": "string"
            }
        },
        "required": ["name"]
    },
    "namespace_get": {
        "type": "object",
        "properties": {
            "_id": {
                "type": "string"
            }
        },
        "required": ["_id"]
    },
    "namespace_create": {
        "type": "object",
        "properties": {}
    },
    "namespace_edit": {
        "type": "object",
        "properties": {
            "_id": {
                "type": "string"
            }
        },
        "required": ["_id"]
    },
    "namespace_delete": {
        "type": "object",
        "properties": {
            "_id": {
                "type": "string"
            }
        },
        "required": ["_id"]
    },
    "project_list": {
        "type": "object",
        "properties": {}
    },
    "project_get": {
        "type": "object",
        "properties": {
            "_id": {
                "type": "string"
            }
        }
    },
    "project_by_name": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string"
            }
        },
        "required": ["name"]
    },
    "project_create": {
        "type": "object",
        "properties": {}
    },
    "project_edit": {
        "type": "object",
        "properties": {
            "_id": {
                "type": "string"
            }
        }
    },
    "project_delete": {
        "type": "object",
        "properties": {
            "_id": {
                "type": "string"
            }
        }
    },
    "regenerate_secret_key": {
        "type": "object",
        "properties": {}
    },
    "dump_structure": {
        "type": "object",
        "properties": {}
    }
}

client_api_schema = {
    "publish": server_api_schema["publish"],
    "presence": server_api_schema["presence"],
    "history": server_api_schema["history"],
    "ping": {
        "type": "object"
    },
    "subscribe": {
        "type": "object",
        "properties": {
            "channel": {
                "type": "string"
            }
        },
        "required": ["channel"]
    },
    "unsubscribe": {
        "type": "object",
        "properties": {
            "channel": {
                "type": "string"
            }
        },
        "required": ["channel"]
    },
    "connect": {
        "type": "object",
        "properties": {
            "token": {
                "type": "string",
            },
            "user": {
                "type": "string"
            },
            "project": {
                "type": "string"
            },
            "timestamp": {
                "type": "string"
            },
            "info": {
                "type": "string"
            }
        },
        "required": ["token", "user", "project", "timestamp"]
    }
}

########NEW FILE########
__FILENAME__ = file
# coding: utf-8
# Copyright (c) Alexandr Emelin. MIT license.

import json
from tornado.gen import coroutine, Return
from centrifuge.structure import BaseStorage


from tornado.options import define

define(
    "path", default='structure.json', help="Path to JSON file with structure configuration", type=str
)


class Storage(BaseStorage):

    NAME = "JSON file"

    def __init__(self, *args, **kwargs):
        super(Storage, self).__init__(*args, **kwargs)
        self.data = json.load(open(self.options.path, 'r'))

    def connect(self, callback=None):
        callback()

    @coroutine
    def project_list(self):
        projects = self.data.get('projects', [])
        raise Return((projects, None))

    @coroutine
    def namespace_list(self):
        namespaces = self.data.get('namespaces', [])
        raise Return((namespaces, None))

########NEW FILE########
__FILENAME__ = sqlite
# coding: utf-8
# Copyright (c) Alexandr Emelin. MIT license.

import sqlite3
from tornado.gen import coroutine, Return
import uuid
import json

from centrifuge.structure import BaseStorage


from tornado.options import define

define(
    "path", default='centrifuge.db', help="path to SQLite database file", type=str
)


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def extract_obj_id(obj):
    return obj['_id']


def on_error(error):
    raise Return((None, error))


class Storage(BaseStorage):

    NAME = "SQLite"

    def __init__(self, *args, **kwargs):
        super(Storage, self).__init__(*args, **kwargs)
        self._cursor = None

    def create_connection_cursor(self):
        conn = sqlite3.connect(self.options.path)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        self._cursor = cursor

    def connect(self, callback=None):

        self.create_connection_cursor()

        project = 'CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, ' \
                  '_id varchar(32) UNIQUE, secret_key varchar(32) NOT NULL, options text)'

        namespace = 'CREATE TABLE IF NOT EXISTS namespaces (id INTEGER PRIMARY KEY AUTOINCREMENT, ' \
                    '_id varchar(32) UNIQUE, project_id varchar(32), name varchar(100) NOT NULL, ' \
                    'options text, UNIQUE (project_id, name) ON CONFLICT ABORT)'

        self._cursor.execute(project, ())
        self._cursor.connection.commit()
        self._cursor.execute(namespace, ())
        self._cursor.connection.commit()

        if callback:
            callback()

    @coroutine
    def clear_structure(self):
        project = "DELETE FROM projects"
        namespace = "DELETE FROM namespaces"
        try:
            self._cursor.execute(project, ())
            self._cursor.connection.commit()
            self._cursor.execute(namespace, ())
            self._cursor.connection.commit()
        except Exception as err:
            raise Return((None, err))
        raise Return((True, None))

    @coroutine
    def project_list(self):

        query = "SELECT * FROM projects"
        try:
            self._cursor.execute(query, {},)
        except Exception as e:
            on_error(e)
        else:
            projects = self._cursor.fetchall()
            raise Return((projects, None))

    @coroutine
    def project_create(self, secret_key, options, project_id=None):

        to_insert = (
            project_id or uuid.uuid4().hex,
            secret_key,
            json.dumps(options)
        )

        to_return = {
            '_id': to_insert[0],
            'secret_key': to_insert[1],
            'options': to_insert[2]
        }

        query = "INSERT INTO projects (_id, secret_key, options) VALUES (?, ?, ?)"

        try:
            self._cursor.execute(query, to_insert)
        except Exception as e:
            on_error(e)
        else:
            self._cursor.connection.commit()
            raise Return((to_return, None))

    @coroutine
    def project_edit(self, project, options):

        to_return = {
            '_id': extract_obj_id(project),
            'options': options
        }

        to_update = (json.dumps(options), extract_obj_id(project))

        query = "UPDATE projects SET options=? WHERE _id=?"

        try:
            self._cursor.execute(query, to_update)
        except Exception as e:
            on_error(e)
        else:
            self._cursor.connection.commit()
            raise Return((to_return, None))

    @coroutine
    def regenerate_project_secret_key(self, project, secret_key):

        project_id = extract_obj_id(project)
        haystack = (secret_key, project_id)

        query = "UPDATE projects SET secret_key=? WHERE _id=?"

        try:
            self._cursor.execute(query, haystack)
        except Exception as e:
            on_error(e)
        else:
            self._cursor.connection.commit()
            raise Return((secret_key, None))

    @coroutine
    def project_delete(self, project):
        """
        Delete project. Also delete all related namespaces.
        """
        haystack = (extract_obj_id(project), )

        query = "DELETE FROM projects WHERE _id=?"
        try:
            self._cursor.execute(query, haystack)
        except Exception as e:
            on_error(e)

        query = "DELETE FROM namespaces WHERE project_id=?"
        try:
            self._cursor.execute(query, haystack)
        except Exception as e:
            on_error(e)
        else:
            self._cursor.connection.commit()
            raise Return((True, None))

    @coroutine
    def namespace_list(self):

        query = "SELECT * FROM namespaces"
        try:
            self._cursor.execute(query, ())
        except Exception as e:
            on_error(e)
        else:
            namespaces = self._cursor.fetchall()
            raise Return((namespaces, None))

    @coroutine
    def namespace_create(self, project, name, options, namespace_id=None):

        to_return = {
            '_id': namespace_id or uuid.uuid4().hex,
            'project_id': extract_obj_id(project),
            'name': name,
            'options': options
        }

        to_insert = (
            to_return['_id'], to_return['project_id'], name, json.dumps(options)
        )

        query = "INSERT INTO namespaces (_id, project_id, name, options) VALUES (?, ?, ?, ?)"

        try:
            self._cursor.execute(query, to_insert)
        except Exception as e:
            on_error(e)
        else:
            self._cursor.connection.commit()
            raise Return((to_return, None))

    @coroutine
    def namespace_edit(self, namespace, name, options):

        to_return = {
            '_id': extract_obj_id(namespace),
            'name': name,
            'options': options
        }

        to_update = (name, json.dumps(options), extract_obj_id(namespace))

        query = "UPDATE namespaces SET name=?, options=? WHERE _id=?"

        try:
            self._cursor.execute(query, to_update)
        except Exception as e:
            on_error(e)
        else:
            self._cursor.connection.commit()
            raise Return((to_return, None))

    @coroutine
    def namespace_delete(self, namespace):
        haystack = (extract_obj_id(namespace),)
        query = "DELETE FROM namespaces WHERE _id=?"
        try:
            self._cursor.execute(query, haystack)
        except Exception as e:
            on_error(e)
        else:
            self._cursor.connection.commit()
            raise Return((True, None))

########NEW FILE########
__FILENAME__ = utils
# coding: utf-8
# Copyright (c) Alexandr Emelin. MIT license.

from __future__ import with_statement
import sys
import six
import weakref
from wtforms import Form as WTForm


class Form(WTForm):
    """
    WTForms wrapper for Tornado.
    """

    def __init__(self, formdata=None, obj=None, prefix='', **kwargs):
        super(Form, self).__init__(
            MultiDictWrapper(formdata), obj=obj, prefix=prefix, **kwargs
        )

    def __iter__(self):
        field_order = getattr(self, 'field_order', None)
        if field_order:
            temp_fields = []
            for name in field_order:
                if name == '*':
                    temp_fields.extend([f for f in self._unbound_fields if f[0] not in field_order])
                else:
                    temp_fields.append([f for f in self._unbound_fields if f[0] == name][0])
            self._unbound_fields = temp_fields
        return super(Form, self).__iter__()


class MultiDictWrapper(object):
    """
    Wrapper class to provide form values to wtforms.Form

    This class is tightly coupled to a request handler, and more importantly
    one of our BaseHandlers which has a 'context'. At least if you want to use
    the save/load functionality.

    Some of this more difficult that it otherwise seems like it should be because of nature
    of how tornado handles it's form input.
    """
    def __init__(self, handler):
        # We keep a weakref to prevent circular references
        # This object is tightly coupled to the handler...
        # which certainly isn't nice, but it's the
        # way it's gonna have to be for now.
        if handler and isinstance(handler, dict):
            self.handler = handler
        elif handler:
            self.handler = weakref.ref(handler)
        else:
            self.handler = None

    @property
    def _arguments(self):
        if not self.handler:
            return {}
        if isinstance(self.handler, dict):
            to_return = {}
            for key, value in six.iteritems(self.handler):
                to_return.setdefault(key, []).append(value)
            return to_return
        return self.handler().request.arguments

    def __iter__(self):
        return iter(self._arguments)

    def __len__(self):
        return len(self._arguments)

    def __contains__(self, name):
        # We use request.arguments because get_arguments always returns a
        # value regardless of the existence of the key.
        return name in self._arguments

    def getlist(self, name):
        # get_arguments by default strips whitespace from the input data,
        # so we pass strip=False to stop that in case we need to validate
        # on whitespace.
        if isinstance(self.handler, dict):
            return self._arguments.get(name, [])
        return self.handler().get_arguments(name, strip=False)

    def __getitem__(self, name):
        if isinstance(self.handler, dict):
            return self.handler.get(name)
        return self.handler().get_argument(name)


if six.PY3:
    def reraise(exception, traceback):
        raise exception.with_traceback(traceback)
else:
    exec("""def reraise(exception, traceback):
    raise exception.__class__, exception, traceback""")


class _NoModuleFound(Exception):
    """
    No module was found because none exists.
    """


class InvalidName(ValueError):
    """
    The given name is not a dot-separated list of Python objects.
    """


class ModuleNotFound(InvalidName):
    """
    The module associated with the given name doesn't exist and it can't be
    imported.
    """


class ObjectNotFound(InvalidName):
    """
    The object associated with the given name doesn't exist and it can't be
    imported.
    """


def _importAndCheckStack(importName):
    """
    Import the given name as a module, then walk the stack to determine whether
    the failure was the module not existing, or some code in the module (for
    example a dependent import) failing. This can be helpful to determine
    whether any actual application code was run. For example, to distiguish
    administrative error (entering the wrong module name), from programmer
    error (writing buggy code in a module that fails to import).

    @raise Exception: if something bad happens. This can be any type of
    exception, since nobody knows what loading some arbitrary code might do.

    @raise _NoModuleFound: if no module was found.
    """
    try:
        try:
            return __import__(importName)
        except ImportError:
            excType, excValue, excTraceback = sys.exc_info()
            while excTraceback:
                execName = excTraceback.tb_frame.f_globals["__name__"]
                if execName is None or execName == importName:
                    reraise(excValue, excTraceback)
                excTraceback = excTraceback.tb_next
            raise _NoModuleFound()
    except:
        # Necessary for cleaning up modules in 2.3.
        sys.modules.pop(importName, None)
        raise


def namedAny(name):
    """
    From Twisted source code.

    Retrieve a Python object by its fully qualified name from the global Python
    module namespace. The first part of the name, that describes a module,
    will be discovered and imported. Each subsequent part of the name is
    treated as the name of an attribute of the object specified by all of the
    name which came before it. For example, the fully-qualified name of this
    object is 'twisted.python.reflect.namedAny'.

    @type name: L{str}
    @param name: The name of the object to return.

    @raise InvalidName: If the name is an empty string, starts or ends with
    a '.', or is otherwise syntactically incorrect.

    @raise ModuleNotFound: If the name is syntactically correct but the
    module it specifies cannot be imported because it does not appear to
    exist.

    @raise ObjectNotFound: If the name is syntactically correct, includes at
    least one '.', but the module it specifies cannot be imported because
    it does not appear to exist.

    @raise AttributeError: If an attribute of an object along the way cannot be
    accessed, or a module along the way is not found.

    @return: the Python object identified by 'name'.
    """
    if not name:
        raise InvalidName('Empty module name')

    names = name.split('.')

    # if the name starts or ends with a '.' or contains '..', the __import__
    # will raise an 'Empty module name' error. This will provide a better error
    # message.
    if '' in names:
        raise InvalidName(
            "name must be a string giving a '.'-separated list of Python "
            "identifiers, not %r" % (name,))

    topLevelPackage = None
    moduleNames = names[:]
    while not topLevelPackage:
        if moduleNames:
            trial_name = '.'.join(moduleNames)
            try:
                topLevelPackage = _importAndCheckStack(trial_name)
            except _NoModuleFound:
                moduleNames.pop()
        else:
            if len(names) == 1:
                raise ModuleNotFound("No module named %r" % (name,))
            else:
                raise ObjectNotFound('%r does not name an object' % (name,))

    obj = topLevelPackage
    for n in names[1:]:
        obj = getattr(obj, n)

    return obj


try:
    from importlib import import_module
except ImportError:
    def _resolve_name(name, package, level):
        """Return the absolute name of the module to be imported."""
        if not hasattr(package, 'rindex'):
            raise ValueError("'package' not set to a string")
        dot = len(package)
        for x in range(level, 1, -1):
            try:
                dot = package.rindex('.', 0, dot)
            except ValueError:
                raise ValueError("attempted relative import beyond top-level "
                                 "package")
        return "%s.%s" % (package[:dot], name)

    def import_module(name, package=None):
        """
        From Gunicorn source code.

        Import a module.
        The 'package' argument is required when performing a relative import. It
        specifies the package to use as the anchor point from which to resolve the
        relative import to an absolute import.
        """
        if name.startswith('.'):
            if not package:
                raise TypeError("relative imports require the 'package' argument")
            level = 0
            for character in name:
                if character != '.':
                    break
                level += 1
            name = _resolve_name(name[level:], package, level)
        __import__(name)
        return sys.modules[name]


def make_patch_data(form, params):
    """
    Return a dictionary with keys which present in request params and in form data
    """
    data = form.data.copy()
    keys_to_delete = list(set(data.keys()) - set(params.keys()))
    for key in keys_to_delete:
        del data[key]
    return data


def get_boolean_patch_data(boolean_fields, params):
    """
    Used as work around HTML form behaviour for checkbox (boolean) fields - when
    boolean field must be set as False then it must not be in request params.
    Here we construct dictionary with keys which present in request params and must
    be interpreted as False. This is necessary as Centrifuge uses partial updates in API.
    """
    boolean_patch_data = {}
    for field in boolean_fields:
        if field in params and not bool(params[field]):
            boolean_patch_data[field] = False
    return boolean_patch_data

########NEW FILE########
__FILENAME__ = handlers
# coding: utf-8
# Copyright (c) Alexandr Emelin. MIT license.

import six
import uuid
import tornado.web
import tornado.escape
import tornado.auth
import tornado.httpclient
import tornado.gen
from tornado.gen import coroutine, Return
from tornado.web import decode_signed_value
from tornado.escape import json_encode, json_decode
from sockjs.tornado import SockJSConnection

from centrifuge.log import logger
from centrifuge.handlers import BaseHandler
from centrifuge.forms import ProjectForm, NamespaceForm


class LogoutHandler(BaseHandler):

    def get(self):
        self.clear_cookie("user")
        self.redirect(self.reverse_url("main"))


class AuthHandler(BaseHandler):

    def authorize(self):
        self.set_secure_cookie("user", "authorized")
        next_url = self.get_argument("next", None)
        if next_url:
            self.redirect(next_url)
        else:
            self.redirect(self.reverse_url("main"))

    def get(self):
        if not self.opts.get("password"):
            self.authorize()
        else:
            self.render('index.html')

    def post(self):
        password = self.get_argument("password", None)
        if password and password == self.opts.get("password"):
            self.authorize()
        else:
            self.render('index.html')


class MainHandler(BaseHandler):

    @tornado.web.authenticated
    @coroutine
    def get(self):
        """
        Render main template with additional data.
        """
        user = self.current_user.decode()

        projects, error = yield self.application.structure.project_list()
        if error:
            raise tornado.web.HTTPError(500, log_message=str(error))

        config = self.application.settings.get('config', {})
        metrics_interval = config.get('metrics', {}).get('interval', self.application.METRICS_EXPORT_INTERVAL)*1000

        context = {
            'js_data': tornado.escape.json_encode({
                'current_user': user,
                'socket_url': '/socket',
                'projects': projects,
                'metrics_interval': metrics_interval
            }),
            'node_count': len(self.application.nodes) + 1,
            'engine': getattr(self.application.engine, 'NAME', 'unknown'),
            'structure': getattr(self.application.structure.storage, 'NAME', 'unknown')
        }
        self.render("main.html", **context)


def render_control(field):
    if field.type == 'BooleanField':
        return field()
    return field(class_="form-control")


def render_label(label):
    return label(class_="col-lg-2 control-label")


def params_from_request(request):
    return dict((k, ''.join([x.decode('utf-8') for x in v])) for k, v in six.iteritems(request.arguments))


class ProjectCreateHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self):

        self.render(
            'project/create.html', form=ProjectForm(self),
            render_control=render_control, render_label=render_label
        )

    @tornado.web.authenticated
    @coroutine
    def post(self):

        params = params_from_request(self.request)
        result, error = yield self.application.process_project_create(None, params, error_form=True)

        if error and isinstance(error, six.string_types):
            # server error
            raise tornado.web.HTTPError(500)
        elif error:
            # error is form with errors in this case
            self.render(
                'project/create.html', form=error,
                render_control=render_control, render_label=render_label
            )
        else:
            self.redirect(self.reverse_url('main'))


class ProjectDetailHandler(BaseHandler):

    @coroutine
    def get_project(self, project_id):
        project, error = yield self.application.structure.get_project_by_id(project_id)
        if not project:
            raise tornado.web.HTTPError(404)
        raise Return((project, None))

    @coroutine
    def get_credentials(self):
        data = {
            'user': self.current_user,
            'project': self.project,
        }
        raise Return((data, None))

    @coroutine
    def get_namespaces(self):
        namespaces, error = yield self.application.structure.get_project_namespaces(self.project)
        if error:
            raise tornado.web.HTTPError(500, log_message=str(error))
        data = {
            'user': self.current_user,
            'project': self.project,
            'namespaces': namespaces
        }
        raise Return((data, None))

    @coroutine
    def post_credentials(self, submit):

        if submit != 'regenerate_secret':
            raise tornado.web.HTTPError(400)

        confirm = self.get_argument('confirm', None)
        if confirm == self.project['name']:
            # regenerate project secret key
            res, error = yield self.application.structure.regenerate_project_secret_key(self.project)
            if error:
                raise tornado.web.HTTPError(500, log_message=str(error))

        self.redirect(self.reverse_url("project_detail", self.project['_id'], 'credentials'))

    @coroutine
    def get_settings(self):
        data = {
            'user': self.current_user,
            'project': self.project,
            'form': ProjectForm(self, **self.project),
            'render_control': render_control,
            'render_label': render_label
        }
        raise Return((data, None))

    @coroutine
    def post_settings(self, submit):

        if submit == 'project_del':
            # completely remove project
            confirm = self.get_argument('confirm', None)
            if confirm == self.project['name']:
                res, error = yield self.application.structure.project_delete(self.project)
                if error:
                    raise tornado.web.HTTPError(500, log_message=str(error))
                self.redirect(self.reverse_url("main"))
            else:
                self.redirect(self.reverse_url("project_detail", self.project['_id'], "settings"))

        else:
            # edit project
            params = params_from_request(self.request)
            result, error = yield self.application.process_project_edit(
                self.project, params, error_form=True, patch=False
            )
            if error and isinstance(error, six.string_types):
                # server error
                raise tornado.web.HTTPError(500)
            elif error:
                # error is form with errors in this case
                self.render(
                    'project/detail_settings.html', project=self.project,
                    form=error, render_control=render_control, render_label=render_label
                )
            else:
                self.redirect(self.reverse_url("project_detail", self.project['_id'], "settings"))

    @coroutine
    def get_actions(self):
        data, error = yield self.get_credentials()
        raise Return((data, None))

    @coroutine
    def post_actions(self):
        params = params_from_request(self.request)
        method = params.pop('method')
        params.pop('_xsrf')
        data = params.get('data', None)
        if data is not None:
            try:
                data = json_decode(data)
            except Exception as e:
                logger.error(e)
            else:
                params["data"] = data

        result, error = yield self.application.process_call(self.project, method, params)

        self.set_header("Content-Type", "application/json")
        self.finish(json_encode({
            "body": result,
            "error": error
        }))

    @tornado.web.authenticated
    @coroutine
    def get(self, project_name, section):

        self.project, error = yield self.get_project(project_name)

        if section == 'credentials':
            template_name = 'project/detail_credentials.html'
            func = self.get_credentials

        elif section == 'settings':
            template_name = 'project/detail_settings.html'
            func = self.get_settings

        elif section == 'namespaces':
            template_name = 'project/detail_namespaces.html'
            func = self.get_namespaces

        elif section == 'actions':
            template_name = 'project/detail_actions.html'
            func = self.get_actions

        else:
            raise tornado.web.HTTPError(404)

        data, error = yield func()

        self.render(template_name, **data)

    @tornado.web.authenticated
    @coroutine
    def post(self, project_name, section):

        self.project, error = yield self.get_project(
            project_name
        )

        submit = self.get_argument('submit', None)

        if section == 'credentials':
            yield self.post_credentials(submit)

        elif section == 'settings':
            yield self.post_settings(submit)

        elif section == 'actions':
            yield self.post_actions()

        else:
            raise tornado.web.HTTPError(404)


class NamespaceFormHandler(BaseHandler):

    @coroutine
    def get_project(self, project_id):
        project, error = yield self.application.structure.get_project_by_id(project_id)
        if error:
            raise tornado.web.HTTPError(500, log_message=str(error))
        if not project:
            raise tornado.web.HTTPError(404)
        raise Return((project, None))

    @coroutine
    def get_namespace(self, namespace_id):
        namespace, error = yield self.application.structure.get_namespace_by_id(
            namespace_id
        )
        if error:
            raise tornado.web.HTTPError(500, log_message=str(error))
        if not namespace:
            raise tornado.web.HTTPError(404)
        raise Return((namespace, error))

    @tornado.web.authenticated
    @coroutine
    def get(self, project_id, namespace_id=None):

        self.project, error = yield self.get_project(project_id)

        if namespace_id:
            template_name = 'namespace/edit.html'
            self.namespace, error = yield self.get_namespace(namespace_id)
            form = NamespaceForm(self, **self.namespace)
        else:
            template_name = 'namespace/create.html'
            form = NamespaceForm(self)

        self.render(
            template_name, form=form, project=self.project,
            render_control=render_control, render_label=render_label
        )

    @tornado.web.authenticated
    @coroutine
    def post(self, project_id, namespace_id=None):

        self.project, error = yield self.get_project(project_id)

        if namespace_id:
            self.namespace, error = yield self.get_namespace(namespace_id)

        submit = self.get_argument('submit', None)

        if submit == 'namespace_delete':
            if self.get_argument('confirm', None) == self.namespace["name"]:
                res, error = yield self.application.structure.namespace_delete(
                    self.namespace
                )
                if error:
                    raise tornado.web.HTTPError(500, log_message=str(error))
                self.redirect(
                    self.reverse_url("project_detail", self.project['_id'], 'namespaces')
                )
            else:
                self.redirect(
                    self.reverse_url("namespace_edit", self.project['_id'], namespace_id)
                )
        else:
            params = params_from_request(self.request)

            if namespace_id:
                template_name = 'namespace/edit.html'
                params['_id'] = namespace_id
                result, error = yield self.application.process_namespace_edit(
                    self.project, params, error_form=True, patch=False
                )
            else:
                template_name = 'namespace/create.html'
                result, error = yield self.application.process_namespace_create(
                    self.project, params, error_form=True
                )

            if error and isinstance(error, six.string_types):
                # server error
                raise tornado.web.HTTPError(500)
            elif error:
                # error is form with errors in this case
                self.render(
                    template_name, form=error, project=self.project,
                    render_control=render_control, render_label=render_label
                )
            else:
                self.redirect(self.reverse_url("project_detail", self.project['_id'], 'namespaces'))


class AdminSocketHandler(SockJSConnection):

    @coroutine
    def subscribe(self):
        self.uid = uuid.uuid4().hex
        self.application.add_admin_connection(self.uid, self)
        logger.debug('admin connected')

    def unsubscribe(self):
        if not hasattr(self, 'uid'):
            return
        self.application.remove_admin_connection(self.uid)
        logger.debug('admin disconnected')

    def on_open(self, info):
        try:
            value = info.cookies['user'].value
        except (KeyError, AttributeError):
            self.close()
        else:
            user = decode_signed_value(
                self.application.settings['cookie_secret'], 'user', value
            )
            if user:
                self.subscribe()
            else:
                self.close()

    def on_close(self):
        self.unsubscribe()


class Http404Handler(BaseHandler):

    def get(self):
        self.render("http404.html")


class StructureDumpHandler(BaseHandler):

    @tornado.web.authenticated
    @coroutine
    def get(self):
        projects, error = yield self.application.structure.project_list()
        if error:
            raise tornado.web.HTTPError(500, log_message=str(error))
        namespaces, error = yield self.application.structure.namespace_list()
        if error:
            raise tornado.web.HTTPError(500, log_message=str(error))
        data = {
            "projects": projects,
            "namespaces": namespaces
        }
        self.set_header("Content-Type", "application/json")
        self.finish(json_encode(data))


class StructureLoadHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self):
        self.render("loads.html")

    @tornado.web.authenticated
    @coroutine
    def post(self):
        json_data = self.get_argument("data")
        data = json_decode(json_data)
        res, err = yield self.application.structure.clear_structure()
        if err:
            raise tornado.web.HTTPError(500, log_message=str(err))

        for project in data.get("projects", []):
            res, err = yield self.application.structure.project_create(**project)
            if err:
                raise tornado.web.HTTPError(500, log_message=str(err))
            for namespace in data.get("namespaces", []):
                if namespace["project_id"] != project["_id"]:
                    continue
                res, err = yield self.application.structure.namespace_create(project, **namespace)
                if err:
                    raise tornado.web.HTTPError(500, log_message=str(err))

        self.redirect(self.reverse_url("main"))

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.append(os.path.abspath('_themes'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.ifconfig',
    'sphinx.ext.todo',
    'sphinx.ext.intersphinx',
    'sphinx.ext.doctest',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'centrifuge'
copyright = u'2014, <a href="https://www.facebook.com/emelin.alexander">Alexandr Emelin</a>'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.5.0'
# The full version, including alpha/beta/rc tags.
release = '0.5.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'flask_theme_support.FlaskyStyle'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'kr'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = 'Centrifuge'

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
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
html_sidebars = {
    'index':    ['sidebarintro.html', 'sourcelink.html', 'searchbox.html'],
    '**':       ['sidebarlogo.html', 'localtoc.html', 'relations.html',
                 'sourcelink.html', 'searchbox.html']
}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'pythonguidedoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'pythonguide.tex', u'Python Guide Documentation',
   u'Kenneth Reitz', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'pythonguide', u'Python Guide Documentation',
     [u'Kenneth Reitz'], 1)
]


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'pythonguide'
epub_author = u'Kenneth Reitz'
epub_publisher = u'Kenneth Reitz'
epub_copyright = u'2010, Kenneth Reitz'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True

todo_include_todos = True

intersphinx_mapping = {
    'python': ('http://docs.python.org/', None),
}

########NEW FILE########
__FILENAME__ = flask_theme_support
# flasky extensions.  flasky pygments style based on tango style
from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Whitespace, Punctuation, Other, Literal


class FlaskyStyle(Style):
    background_color = "#f8f8f8"
    default_style = ""

    styles = {
        # No corresponding class for the following:
        #Text:                     "", # class:  ''
        Whitespace:                "underline #f8f8f8",      # class: 'w'
        Error:                     "#a40000 border:#ef2929", # class: 'err'
        Other:                     "#000000",                # class 'x'

        Comment:                   "italic #8f5902", # class: 'c'
        Comment.Preproc:           "noitalic",       # class: 'cp'

        Keyword:                   "bold #004461",   # class: 'k'
        Keyword.Constant:          "bold #004461",   # class: 'kc'
        Keyword.Declaration:       "bold #004461",   # class: 'kd'
        Keyword.Namespace:         "bold #004461",   # class: 'kn'
        Keyword.Pseudo:            "bold #004461",   # class: 'kp'
        Keyword.Reserved:          "bold #004461",   # class: 'kr'
        Keyword.Type:              "bold #004461",   # class: 'kt'

        Operator:                  "#582800",   # class: 'o'
        Operator.Word:             "bold #004461",   # class: 'ow' - like keywords

        Punctuation:               "bold #000000",   # class: 'p'

        # because special names such as Name.Class, Name.Function, etc.
        # are not recognized as such later in the parsing, we choose them
        # to look the same as ordinary variables.
        Name:                      "#000000",        # class: 'n'
        Name.Attribute:            "#c4a000",        # class: 'na' - to be revised
        Name.Builtin:              "#004461",        # class: 'nb'
        Name.Builtin.Pseudo:       "#3465a4",        # class: 'bp'
        Name.Class:                "#000000",        # class: 'nc' - to be revised
        Name.Constant:             "#000000",        # class: 'no' - to be revised
        Name.Decorator:            "#888",           # class: 'nd' - to be revised
        Name.Entity:               "#ce5c00",        # class: 'ni'
        Name.Exception:            "bold #cc0000",   # class: 'ne'
        Name.Function:             "#000000",        # class: 'nf'
        Name.Property:             "#000000",        # class: 'py'
        Name.Label:                "#f57900",        # class: 'nl'
        Name.Namespace:            "#000000",        # class: 'nn' - to be revised
        Name.Other:                "#000000",        # class: 'nx'
        Name.Tag:                  "bold #004461",   # class: 'nt' - like a keyword
        Name.Variable:             "#000000",        # class: 'nv' - to be revised
        Name.Variable.Class:       "#000000",        # class: 'vc' - to be revised
        Name.Variable.Global:      "#000000",        # class: 'vg' - to be revised
        Name.Variable.Instance:    "#000000",        # class: 'vi' - to be revised

        Number:                    "#990000",        # class: 'm'

        Literal:                   "#000000",        # class: 'l'
        Literal.Date:              "#000000",        # class: 'ld'

        String:                    "#4e9a06",        # class: 's'
        String.Backtick:           "#4e9a06",        # class: 'sb'
        String.Char:               "#4e9a06",        # class: 'sc'
        String.Doc:                "italic #8f5902", # class: 'sd' - like a comment
        String.Double:             "#4e9a06",        # class: 's2'
        String.Escape:             "#4e9a06",        # class: 'se'
        String.Heredoc:            "#4e9a06",        # class: 'sh'
        String.Interpol:           "#4e9a06",        # class: 'si'
        String.Other:              "#4e9a06",        # class: 'sx'
        String.Regex:              "#4e9a06",        # class: 'sr'
        String.Single:             "#4e9a06",        # class: 's1'
        String.Symbol:             "#4e9a06",        # class: 'ss'

        Generic:                   "#000000",        # class: 'g'
        Generic.Deleted:           "#a40000",        # class: 'gd'
        Generic.Emph:              "italic #000000", # class: 'ge'
        Generic.Error:             "#ef2929",        # class: 'gr'
        Generic.Heading:           "bold #000080",   # class: 'gh'
        Generic.Inserted:          "#00A000",        # class: 'gi'
        Generic.Output:            "#888",           # class: 'go'
        Generic.Prompt:            "#745334",        # class: 'gp'
        Generic.Strong:            "bold #000000",   # class: 'gs'
        Generic.Subheading:        "bold #800080",   # class: 'gu'
        Generic.Traceback:         "bold #a40000",   # class: 'gt'
    }

########NEW FILE########
__FILENAME__ = settings

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'o)&d(qy!8lx^p0bc6o&_oo0%&jvqu#))bxcrvg)(v*^(yfa1ke'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'application.urls'

WSGI_APPLICATION = 'application.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
    "adjacent.context_processors.main"
)

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = '/static/'

CENTRIFUGE_ADDRESS = 'http://localhost:8000'
CENTRIFUGE_PROJECT_ID = '1d88332ec09e4ed3805fc1999379bcfd'
CENTRIFUGE_PROJECT_SECRET = '1ee93d4ac83e4ccf87d2bbd0e447275b'
CENTRIFUGE_TIMEOUT = 5

try:
    from local_settings import *
except ImportError:
    pass
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^admin/', include(admin.site.urls)),
    url(r'', include('core.urls')),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for weather project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "weather.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

# Register your models here.

########NEW FILE########
__FILENAME__ = publish
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from adjacent import Client


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--lat', default=0, dest='lat', type='float', help='Latitude'),
        make_option('--long', default=0, dest='long', type='float', help='Longitude'),
        make_option('--content', default='', dest='content', help='Content'),
    )

    help = 'Publish new event on map'

    def handle(self, *args, **options):
        client = Client()
        client.publish('map', {
            "lat": options.get("lat"),
            "long": options.get("long"),
            "content": options.get("content")
        })
        client.send()

########NEW FILE########
__FILENAME__ = models
from django.db import models

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase

# Create your tests here.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import url
from django.conf.urls import patterns
from django.views.generic import TemplateView

urlpatterns = patterns(
    '',
    url('^$', TemplateView.as_view(template_name='core/index.html'), name="core_index"),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render

# Create your views here.

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "application.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
from __future__ import print_function
import hmac
import time
import json
import logging

import six
import tornado.ioloop
import tornado.web
from tornado.options import options, define


logging.getLogger().setLevel(logging.DEBUG)


define(
    "port", default=3000, help="app port", type=int
)
define(
    "centrifuge", default='localhost:8000',
    help="centrifuge address without url scheme", type=str
)
define(
    "project_id", default='', help="project id", type=str
)
define(
    "secret_key", default='', help="project secret key", type=str
)


# let it be your application's user ID
USER_ID = '2694'

INFO = json.dumps(None)

# uncomment this to send some additional default info
#INFO = json.dumps({
#    'first_name': 'Alexandr',
#    'last_name': 'Emelin'
#})


def get_client_token(secret_key, project_id, user, timestamp, info=None):
    """
    Create token to validate information provided by new connection.
    """
    sign = hmac.new(six.b(str(secret_key)))
    sign.update(six.b(project_id))
    sign.update(six.b(user))
    sign.update(six.b(timestamp))
    if info is not None:
        sign.update(six.b(info))
    token = sign.hexdigest()
    return token


class IndexHandler(tornado.web.RequestHandler):

    def get(self):
        self.render('index.html')


def get_auth_data():

    user = USER_ID
    now = str(int(time.time()))
    token = get_client_token(
        options.secret_key, options.project_id, user, now, info=INFO
    )

    auth_data = {
        'token': token,
        'user': user,
        'project': options.project_id,
        'timestamp': now,
        'info': INFO
    }

    return auth_data


class SockjsHandler(tornado.web.RequestHandler):

    def get(self):
        """
        Render template with data required to connect to Centrifuge using SockJS.
        """
        self.render(
            "index_sockjs.html",
            auth_data=get_auth_data(),
            centrifuge_address=options.centrifuge
        )


class WebsocketHandler(tornado.web.RequestHandler):

    def get(self):
        """
        Render template with data required to connect to Centrifuge using Websockets.
        """
        self.render(
            "index_websocket.html",
            auth_data=get_auth_data(),
            centrifuge_address=options.centrifuge
        )


class CheckHandler(tornado.web.RequestHandler):
    """
    Allow all users to subscribe on channels they want.
    """
    def check_xsrf_cookie(self):
        pass

    def post(self):

        # the list of users connected to Centrifuge with expired connection
        # web application must find deactivated users in this list
        users_to_check = json.loads(self.get_argument("users"))
        logging.info(users_to_check)

        # list of deactivated users
        deactivated_users = []

        # send list of deactivated users as json
        self.write(json.dumps(deactivated_users))


class AuthorizeHandler(tornado.web.RequestHandler):
    """
    Allow all users to subscribe on channels they want.
    """
    def check_xsrf_cookie(self):
        pass

    def post(self):

        user = self.get_argument("user")
        channel = self.get_argument("channel")

        logging.info("{0} wants to subscribe on {1} channel".format(user, channel))

        # web application now has user and channel and must decide that
        # user has permissions to subscribe on that channel
        # if permission denied - then you can return non 200 HTTP response

        # but here we allow to join any private channel and return additional
        # JSON info specific for channel
        self.write(json.dumps({
            'channel_data_example': 'you can add additional JSON data when authorizing'
        }))


def run():
    options.parse_command_line()
    app = tornado.web.Application(
        [
            (r'/', IndexHandler),
            (r'/sockjs', SockjsHandler),
            (r'/ws', WebsocketHandler),
            (r'/check', CheckHandler),
            (r'/authorize', AuthorizeHandler),
        ],
        debug=True
    )
    app.listen(options.port)
    logging.info("app started, visit http://localhost:%s" % options.port)
    tornado.ioloop.IOLoop.instance().start()


def main():
    try:
        run()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_auth
# coding: utf-8
import json
import time
from unittest import TestCase, main

from centrifuge.auth import decode_data, get_client_token


class FakeRequest(object):
    pass


class AuthTest(TestCase):

    def setUp(self):
        self.correct_request = FakeRequest()
        self.wrong_request = FakeRequest()
        self.wrong_request.headers = {}
        self.data = 'test'
        self.encoded_data = json.dumps(self.data)
        self.secret_key = "test"
        self.project_id = "test"
        self.user_id = "test"
        self.user_info = '{"data": "test"}'

    def test_decode_data(self):
        self.assertEqual(decode_data(self.encoded_data), self.data)

    def test_client_token(self):
        now = int(time.time())
        token_no_info = get_client_token(
            self.secret_key, self.project_id, self.user_id, str(now)
        )
        token_with_info = get_client_token(
            self.secret_key, self.project_id, self.user_id, str(now), user_info=self.user_info
        )
        self.assertTrue(token_no_info != token_with_info)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_client
# coding: utf-8
from __future__ import print_function
from tornado.gen import coroutine, Return
from tornado.testing import AsyncTestCase, gen_test
import json

from centrifuge.client import Client
from centrifuge.schema import client_api_schema
from centrifuge.core import Application
from centrifuge.engine.memory import Engine


class FakeSock(object):

    @coroutine
    def send(self, message):
        return True


class FakeEngine(Engine):

    @coroutine
    def add_presence(self, *args, **kwargs):
        raise Return((True, None))

    @coroutine
    def remove_presence(self, *args, **kwargs):
        raise Return((True, None))


class FakeApplication(Application):

    @coroutine
    def get_project(self, project_id):
        raise Return(({'_id': 'test', 'name': 'test'}, None))

    @coroutine
    def get_namespace(self, project, params):
        raise Return(({'_id': 'test', 'name': 'test'}, None))


class FakePeriodic(object):

    def stop(self):
        return True


class TestClient(Client):

    @coroutine
    def handle_test(self, params):
        raise Return((True, None))


class ClientTest(AsyncTestCase):
    """ Test the client """

    def setUp(self):
        super(ClientTest, self).setUp()
        self.client = TestClient(FakeSock(), {})
        self.client.is_authenticated = True
        self.client.project_id = "test_project"
        self.client.uid = "test_uid"
        self.client.user = "test_user"
        self.client.channels = {}
        self.client.presence_ping = FakePeriodic()
        self.client.application = FakeApplication()
        self.client.application.engine = FakeEngine(self.client.application)

    @gen_test
    def test_method_resolve(self):
        message = json.dumps({
            "method": "test",
            "params": {}
        })
        client_api_schema["test"] = {
            "type": "object"
        }
        result, error = yield self.client.message_received(message)
        self.assertEqual(result, True)
        self.assertEqual(error, None)

    @gen_test
    def test_client(self):

        params = {
            "channel": "test"
        }
        result, error = yield self.client.handle_subscribe(params)
        self.assertEqual(result, {"channel": "test"})
        self.assertEqual(error, None)

        subs = self.client.application.engine.subscriptions
        subscription = self.client.application.engine.get_subscription_key(
            self.client.project_id, params["channel"]
        )
        self.assertTrue(subscription in subs)

        self.assertTrue(params["channel"] in self.client.channels)

        result, error = yield self.client.handle_unsubscribe(params)
        self.assertEqual(result, {"channel": "test"})
        self.assertEqual(error, None)
        self.assertTrue(subscription not in subs)

        self.assertTrue(params["channel"] not in self.client.channels)

        result, error = yield self.client.clean()
        self.assertEqual(result, True)
        self.assertEqual(error, None)

########NEW FILE########
__FILENAME__ = test_core
# coding: utf-8
from unittest import TestCase, main


from centrifuge.core import *


class TestApp(Application):
    pass


class CoreTest(TestCase):

    def setUp(self):
        self.app = TestApp()

    def test_extracting_namespace(self):

        channel = 'channel'
        self.assertEqual(self.app.extract_namespace_name(channel), None)

        channel = 'namespace:channel'
        self.assertEqual(self.app.extract_namespace_name(channel), 'namespace')

        channel = 'namespace:channel#user1.user2'
        self.assertEqual(self.app.extract_namespace_name(channel), 'namespace')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_engine
# coding: utf-8
from unittest import main
import sys
import os
import json
import time
from tornado.gen import Task
from tornado.testing import AsyncTestCase, gen_test


from centrifuge.engine import BaseEngine
from centrifuge.engine.memory import Engine as MemoryEngine
from centrifuge.engine.redis import Engine as RedisEngine
from centrifuge.core import Application


class FakeClient(object):

    uid = 'test_uid'


class Options(object):

    redis_host = "localhost"
    redis_port = 6379
    redis_password = ""
    redis_db = 0
    redis_url = ""


class BaseEngineTest(AsyncTestCase):

    def setUp(self):
        super(BaseEngineTest, self).setUp()
        self.application = Application(**{'options': Options})
        self.engine = BaseEngine(self.application)

    def test_get_subscription_key(self):
        key = self.engine.get_subscription_key('project', 'channel')
        self.assertEqual(key, "centrifuge|project|channel")


class MemoryEngineTest(AsyncTestCase):

    def setUp(self):
        super(MemoryEngineTest, self).setUp()
        self.application = Application(**{'options': Options})
        self.engine = MemoryEngine(self.application)
        self.engine.initialize()
        self.engine.history_size = 2
        self.engine.presence_timeout = 1
        self.project_id = "project_id"
        self.channel = "channel"
        self.uid_1 = 'uid-1'
        self.uid_2 = 'uid-2'
        self.user_id = 'user_id'
        self.user_id_extra = 'user_id_extra'
        self.user_info = "{}"
        self.message_1 = json.dumps('test message 1')
        self.message_2 = json.dumps('test message 2')
        self.message_3 = json.dumps('test message 3')

    @gen_test
    def test_add_subscription(self):
        yield self.engine.add_subscription(self.project_id, self.channel, FakeClient())

        self.assertTrue(
            self.engine.get_subscription_key(
                self.project_id, self.channel
            ) in self.engine.subscriptions
        )

    @gen_test
    def test_remove_subscription(self):
        yield self.engine.remove_subscription(self.project_id, self.channel, FakeClient())

        self.assertTrue(
            self.engine.get_subscription_key(
                self.project_id, self.channel
            ) not in self.engine.subscriptions
        )

    @gen_test
    def test_presence(self):
        result, error = yield self.engine.get_presence(
            self.project_id, self.channel
        )
        self.assertEqual(result, {})

        result, error = yield self.engine.add_presence(
            self.project_id, self.channel, self.uid_1, self.user_info
        )
        self.assertEqual(result, True)

        result, error = yield self.engine.get_presence(
            self.project_id, self.channel
        )
        self.assertTrue(self.uid_1 in result)

        result, error = yield self.engine.add_presence(
            self.project_id, self.channel,
            self.uid_1, self.user_info
        )
        self.assertEqual(result, True)

        result, error = yield self.engine.get_presence(
            self.project_id, self.channel
        )
        self.assertTrue(self.uid_1 in result)
        self.assertEqual(len(result), 1)

        result, error = yield self.engine.add_presence(
            self.project_id, self.channel,
            self.uid_2, self.user_info
        )
        self.assertEqual(result, True)

        result, error = yield self.engine.get_presence(
            self.project_id, self.channel
        )
        self.assertTrue(self.uid_1 in result)
        self.assertTrue(self.uid_2 in result)
        self.assertEqual(len(result), 2)

        result, error = yield self.engine.remove_presence(
            self.project_id, self.channel, self.uid_2
        )
        self.assertEqual(result, True)

        result, error = yield self.engine.get_presence(
            self.project_id, self.channel
        )
        self.assertTrue(self.uid_1 in result)
        self.assertTrue(self.uid_2 not in result)
        self.assertEqual(len(result), 1)

        time.sleep(2)
        result, error = yield self.engine.get_presence(
            self.project_id, self.channel
        )
        self.assertEqual(result, {})

    @gen_test
    def test_history(self):
        result, error = yield self.engine.add_history_message(
            self.project_id, self.channel, self.message_1
        )
        self.assertEqual(error, None)
        self.assertEqual(result, True)

        result, error = yield self.engine.get_history(
            self.project_id, self.channel
        )
        self.assertEqual(error, None)
        self.assertEqual(len(result), 1)

        result, error = yield self.engine.add_history_message(
            self.project_id, self.channel, self.message_2
        )
        self.assertEqual(error, None)
        self.assertEqual(result, True)

        result, error = yield self.engine.get_history(
            self.project_id, self.channel
        )
        self.assertEqual(error, None)
        self.assertEqual(len(result), 2)

        result, error = yield self.engine.add_history_message(
            self.project_id, self.channel, self.message_3
        )
        self.assertEqual(error, None)
        self.assertEqual(result, True)

        result, error = yield self.engine.get_history(
            self.project_id, self.channel
        )
        self.assertEqual(error, None)
        self.assertEqual(len(result), 2)

    @gen_test
    def test_history_expire(self):
        result, error = yield self.engine.add_history_message(
            self.project_id, self.channel, self.message_1, history_expire=1
        )
        self.assertEqual(error, None)
        self.assertEqual(result, True)

        result, error = yield self.engine.get_history(
            self.project_id, self.channel
        )
        self.assertEqual(error, None)
        self.assertEqual(len(result), 1)

        time.sleep(2)

        result, error = yield self.engine.get_history(
            self.project_id, self.channel
        )
        self.assertEqual(error, None)
        self.assertEqual(len(result), 0)


class RedisEngineTest(AsyncTestCase):
    """ Test the client """

    def setUp(self):
        super(RedisEngineTest, self).setUp()
        self.application = Application(**{'options': Options})
        self.engine = RedisEngine(self.application, io_loop=self.io_loop)
        self.engine.initialize()
        self.engine.history_size = 2
        self.engine.presence_timeout = 1
        self.project_id = "project_id"
        self.channel = "channel"
        self.uid_1 = 'uid-1'
        self.uid_2 = 'uid-2'
        self.user_id = 'user_id'
        self.user_id_extra = 'user_id_extra'
        self.user_info = "{}"
        self.message_1 = json.dumps('test message 1')
        self.message_2 = json.dumps('test message 2')
        self.message_3 = json.dumps('test message 3')

    @gen_test
    def test_presence(self):

        result = yield Task(self.engine.worker.flushdb)
        self.assertEqual(result, b"OK")

        result, error = yield self.engine.get_presence(
            self.project_id, self.channel
        )
        self.assertEqual(result, {})

        result, error = yield self.engine.add_presence(
            self.project_id, self.channel,
            self.uid_1, self.user_info
        )
        self.assertEqual(result, True)

        result, error = yield self.engine.get_presence(
            self.project_id, self.channel
        )
        self.assertTrue(self.uid_1 in result)

        result, error = yield self.engine.add_presence(
            self.project_id, self.channel,
            self.uid_1, self.user_info
        )
        self.assertEqual(result, True)

        result, error = yield self.engine.get_presence(
            self.project_id, self.channel
        )
        self.assertTrue(self.uid_1 in result)
        self.assertEqual(len(result), 1)

        result, error = yield self.engine.add_presence(
            self.project_id, self.channel,
            self.uid_2, self.user_info
        )
        self.assertEqual(result, True)

        result, error = yield self.engine.get_presence(
            self.project_id, self.channel
        )
        self.assertTrue(self.uid_1 in result)
        self.assertTrue(self.uid_2 in result)
        self.assertEqual(len(result), 2)

        result, error = yield self.engine.remove_presence(
            self.project_id, self.channel, self.uid_2
        )
        self.assertEqual(result, True)

        result, error = yield self.engine.get_presence(
            self.project_id, self.channel
        )
        self.assertTrue(self.uid_1 in result)
        self.assertTrue(self.uid_2 not in result)
        self.assertEqual(len(result), 1)

        time.sleep(2)
        result, error = yield self.engine.get_presence(
            self.project_id, self.channel
        )
        self.assertEqual(result, {})

    @gen_test
    def test_history(self):
        result = yield Task(self.engine.worker.flushdb)
        self.assertEqual(result, b"OK")

        result, error = yield self.engine.add_history_message(
            self.project_id, self.channel, self.message_1
        )
        self.assertEqual(error, None)
        self.assertEqual(result, True)

        result, error = yield self.engine.get_history(
            self.project_id, self.channel
        )
        self.assertEqual(error, None)
        self.assertEqual(len(result), 1)

        result, error = yield self.engine.add_history_message(
            self.project_id, self.channel, self.message_2
        )
        self.assertEqual(error, None)
        self.assertEqual(result, True)

        result, error = yield self.engine.get_history(
            self.project_id, self.channel
        )
        self.assertEqual(error, None)
        self.assertEqual(len(result), 2)

        result, error = yield self.engine.add_history_message(
            self.project_id, self.channel, self.message_3
        )
        self.assertEqual(error, None)
        self.assertEqual(result, True)

        result, error = yield self.engine.get_history(
            self.project_id, self.channel
        )
        self.assertEqual(error, None)
        self.assertEqual(len(result), 2)

    @gen_test
    def test_history_expire(self):
        result = yield Task(self.engine.worker.flushdb)
        self.assertEqual(result, b"OK")

        result, error = yield self.engine.add_history_message(
            self.project_id, self.channel, self.message_1, history_expire=1
        )
        self.assertEqual(error, None)
        self.assertEqual(result, True)

        result, error = yield self.engine.get_history(
            self.project_id, self.channel
        )
        self.assertEqual(error, None)
        self.assertEqual(len(result), 1)

        time.sleep(2)

        result, error = yield self.engine.get_history(
            self.project_id, self.channel
        )
        self.assertEqual(error, None)
        self.assertEqual(len(result), 0)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_metrics
# coding: utf-8
from unittest import TestCase, main
import time


from centrifuge.metrics import *


class CollectorTest(TestCase):

    def setUp(self):
        self.collector = Collector()

    def test_timer(self):
        timer = self.collector.get_timer('test')
        time.sleep(0.1)
        interval = timer.stop()
        self.assertTrue(interval >= 0.1)
        metrics = self.collector.get()
        self.assertTrue('test.avg') in metrics
        self.assertTrue('test.min') in metrics
        self.assertTrue('test.max') in metrics
        self.assertTrue('test.count') in metrics

    def test_counter(self):
        self.collector.incr('counter')
        self.collector.incr('counter', 5)
        self.collector.decr('counter', 2)
        metrics = self.collector.get()
        self.assertEqual(metrics['counter.count'], 4)
        self.assertTrue('counter.rate' in metrics)

    def test_gauge(self):
        self.collector.gauge('gauge', 101)
        metrics = self.collector.get()
        self.assertEqual(metrics['gauge'], 101)


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = test_schema
# coding: utf-8
from unittest import TestCase, main


from centrifuge.schema import req_schema, server_api_schema, client_api_schema
from jsonschema import validate, ValidationError


class SchemaTest(TestCase):

    def setUp(self):

        pass

    def test_req_schema(self):
        schema = {
            'id': '123',
            'method': 'test',
            'params': {"test": "test"}
        }

        self.assertEqual(validate(schema, req_schema), None)

        schema["method"] = 1
        try:
            validate(schema, req_schema)
        except ValidationError:
            pass
        else:
            self.assertTrue(False)

    def test_server_api_schema_publish(self):
        schema = {
            "namespace": "test",
            "channel": "test",
            "data": {"input": "test"}
        }

        self.assertEqual(
            validate(schema, server_api_schema["publish"]),
            None
        )

        del schema["namespace"]

        self.assertEqual(
            validate(schema, server_api_schema["publish"]),
            None
        )

    def test_server_api_schema_unsubscribe(self):
        schema = {
            "user": "test",
            "namespace": "channel",
            "channel": "test"
        }

        self.assertEqual(
            validate(schema, server_api_schema["unsubscribe"]),
            None
        )

    def test_client_api_schema_subscribe(self):
        schema = {
            "namespace": "channel",
            "channel": "test"
        }

        self.assertEqual(
            validate(schema, client_api_schema["subscribe"]),
            None
        )

    def test_client_api_schema_unsubscribe(self):
        schema = {
            "namespace": "channel",
            "channel": "test"
        }

        self.assertEqual(
            validate(schema, client_api_schema["unsubscribe"]),
            None
        )

    def test_client_api_schema_connect(self):
        schema = {
            "token": "test",
            "user": "test",
            "project": "test",
            "timestamp": "123"
        }

        self.assertEqual(
            validate(schema, client_api_schema["connect"]),
            None
        )

        schema = {
            "token": "test",
            "user": "test",
            "project": "test",
            "timestamp": "123",
            "info": 1
        }
        try:
            validate(schema, client_api_schema["connect"])
        except ValidationError:
            pass
        else:
            raise AssertionError("Exception must be raised here")

        schema = {
            "token": "test",
            "user": "test",
            "project": "test",
            "timestamp": "123",
            "info": "{}"
        }

        self.assertEqual(
            validate(schema, client_api_schema["connect"]),
            None
        )


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_structure
# coding: utf-8
from __future__ import print_function
from tornado.testing import AsyncTestCase, main

from centrifuge.structure import flatten


class FlattenTest(AsyncTestCase):

    def test_non_dict(self):
        structure = "test"
        self.assertEqual(flatten(structure), "test")

    def test_dict_with_no_options(self):
        structure = {"name": 1}
        self.assertEqual(flatten(structure), structure)

    def test_json_options(self):
        structure = {
            "name": 1,
            "options": '{"test": 1}'
        }
        res = flatten(structure)
        self.assertTrue("name" in res)
        self.assertTrue("test" in res)
        self.assertTrue("options" not in res)

    def test_dict_options(self):
        structure = {
            "name": 1,
            "options": {
                "test": 1
            }
        }
        res = flatten(structure)
        self.assertTrue("name" in res)
        self.assertTrue("test" in res)
        self.assertTrue("options" not in res)


if __name__ == '__main__':
    main()

########NEW FILE########
