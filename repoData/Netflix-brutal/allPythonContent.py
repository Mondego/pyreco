__FILENAME__ = brutal-overlord
#!/usr/bin/env python
from brutal.core.management import exec_overlord

if __name__ == '__main__':
    exec_overlord()
########NEW FILE########
__FILENAME__ = global_config
import logging

DEBUG = False
LOG_LEVEL = logging.INFO
LOG_FILE = 'bot.log'

INSTALLED_PLUGINS = ()
########NEW FILE########
__FILENAME__ = bot
import uuid
import logging

from twisted.internet import reactor
from twisted.internet import task, defer
from brutal.core.connections import ConnectionManager

from brutal.core.plugin import PluginManager
from brutal.core.models import Event, Action

from brutal.core.constants import *


class Bot(object):
    def __init__(self, nick, connections, *args, **kwargs):
        """
        acts as a connection manager, middle man for incoming events, and processor of outgoing actions.
        """
        #TODO: maybe support a custom internal key to keep track of bots, not just by 'name'...
        #TODO: if we do it by name, make sure we don't have name dupes, even between networks :-/

        # bot id
        self.nick = nick
        self.id = str(uuid.uuid1())
        self.log = logging.getLogger('{0}.{1}.{2}'.format(self.__class__.__module__, self.__class__.__name__,
                                                          self.nick))
        self.log.info('starting bot')

        #bot manager instance
        self.bot_manager = None

        # setup this bots event queue / consumer, action queue/consumer
        self.event_queue = defer.DeferredQueue()
        self._consume_events(self.event_queue)

        self.action_queue = defer.DeferredQueue()
        self._consume_actions(self.action_queue)

        # setup plugins
        self.enabled_plugins = kwargs.get('enabled_plugins')
        self.plugin_manager = PluginManager(bot=self)
        # self.manager.config.PLUGINS:

        # build connections
        # TODO: create connection manager
        self.connection_manager = ConnectionManager(config=connections, bot=self)
        self.log.debug('connections on {0!r}: {1!r}'.format(self.nick, self.connection_manager))

        # should have a 'ready' state that we should check before starting?
        self.state = OFF
        self.party_line = None

    def __repr__(self):
        return '<{0}: {1!r} ({2!s})>'.format(self.__class__.__name__, self.nick, self.id)

    def __str__(self):
        return repr(self)

    # CORE

    def start(self):
        #TODO: catch failures?
        #TODO: pass enabled plugins
        self.plugin_manager.start(self.enabled_plugins)
        self.connection_manager.connect()
        self.state = ON

    # review
    def stop(self):
        """
        TODO: placeholder
        """
        if self.state >= ON:
            self.state = OFF

    # review
    def pause(self):
        """
        placeholder
        """
        pass

    def default_destination(self):
        """
        if no destination room is defined, and no event triggered an action, determine where to send results

        NOTE: for now send everywhere...
        """
        pass

    # EVENT QUEUE
    # default event consumer queue.
    def _consume_events(self, queue):
        def consumer(event):
            # check if Event, else try to make it one
            if not isinstance(event, Event):
                try:
                    event = self.build_event(event)
                except Exception as e:
                    self.log.exception('unable to parse data to Event, {0!r}: {1!r}'.format(event, e))
                    event = None

            if event is not None:
                self.log.debug('EVENT on {0!r} {1!r}'.format(self, event))
                responses = self.plugin_manager.process_event(event)
                # this is going to be a list of deferreds,
                # TODO: should probably do this differently
                #self.log.debug('HERE: {0!r}'.format(responses))
                for response in responses:
                    #self.log.debug('adding response router')
                    response.addCallback(self.route_response, event)

            queue.get().addCallback(consumer)
        queue.get().addCallback(consumer)

    def new_event(self, event):
        """
        this is what protocol backends call when they get an event.
        """
        self.event_queue.put(event)

    def build_event(self, event_data):
        #todo: needs to be safe
        try:
            e = Event(source_bot=self, raw_details=event_data)
        except Exception as e:
            self.log.exception('failed to build event from {0!r}: {1!r}'.format(event_data, e))
        else:
            return e

    # ACTION QUEUE
    # default action consumer
    def _consume_actions(self, queue):
        def consumer(action):
            # check if Action, else try to make it one
            if not isinstance(action, Action):
                try:
                    action = self.build_action(action)
                except Exception as e:
                    self.log.exception('unable to build Action with {0!r}: {1!r}'.format(action, e))

            if action is not None:
                res = defer.maybeDeferred(self.process_action, action)

            queue.get().addCallback(consumer)
        queue.get().addCallback(consumer)

    def build_action(self, action_data, event=None):
        if type(action_data) in (str, unicode):
            try:
                a = Action(source_bot=self, source_event=event).msg(action_data)
            except Exception as e:
                self.log.exception('failed to build action from {0!r}, for {1!r}: {2!r}'.format(action_data, event, e))
            else:
                return a

    # PLUGIN SYSTEM #################################################
    def route_response(self, response, event):
        if response is not None:
            self.log.debug('got {0!r} from {1!r}'.format(response, event))
            #TODO: update to actually route to correct bot, for now we just assume its ours
            if isinstance(response, Action):
                self.action_queue.put(response)
            else:
                self.log.error('got invalid response type')

    def process_action(self, action):
        #self.log.debug('routing response: {0}'.format(action))
        self.connection_manager.route_action(action)
        # for client_id, client in self.connection_manager..items():
        #     if conn.id is not None and conn.id in action.destination_connections:
        #         conn.queue_action(action)


class BotManager(object):
    """
    Handles herding of all bottes, responsible for spinning up and shutting down
    """
    #TODO: fill this out, needs to read config or handle config object?
    def __init__(self, config=None):
        if config is None:
            raise AttributeError("No config passed to manager.")

        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))

        self.config = config
        self.log.debug('config: {0!r}'.format(self.config))

        self.bots = {}
        # not sure about this...
        # {'bot_name': {'connections':[], ....}, }
        # bot -> {partyline:_, otherstuff?}
        # NETWORKED PARTY LINES WOULD BE HOT FIRE

        #self.tasks = Queue()
        self.event_handler = None

        # build bottes from config
        self.setup()

        self.delete_this = 0

    def __repr__(self):
        return '<{0}: {1!r}>'.format(self.__class__.__name__, self.bots)

    def __str(self):
        return repr(self)

    def setup(self):
        bots = getattr(self.config, 'BOTS', None)

        self.log.debug('bots: {0!r}'.format(bots))

        if bots is not None and isinstance(bots, list):
            for bot_config in bots:
                if isinstance(bot_config, dict):
                    self.create_bot(**bot_config)
        else:
            self.log.warning('no bots found in configuration')

    def update(self):
        self.log.debug('manager loop called')
        pass

    def create_bot(self, *args, **kwargs):
        bot = Bot(*args, **kwargs)
        bot.bot_manager = self

        #todo: check if startup worked?
        self.bots[bot.nick] = {'bot': bot}

    def start_bots(self):
        for bot_id in self.bots:
            # dont like this. change.
            self.bots[bot_id]['bot'].start()

    def start(self):
        """
        starts the manager
        """
        self.start_bots()

        loop = task.LoopingCall(self.update)
        loop.start(30.0)

        reactor.run()

########NEW FILE########
__FILENAME__ = connections
import logging
from collections import OrderedDict
from brutal.core.models import Action

from brutal.protocols.core import ProtocolBackend
# supported protocols - done for plugin access. kinda ugly
from brutal.protocols.irc import IrcBackend
from brutal.protocols.xmpp import XmppBackend
from brutal.protocols.testconsole import TestConsoleBackend


class ConnectionManager(object):
    """
    handles building and holding of connection clients
    """
    def __init__(self, config, bot):
        self.config = config
        self.bot = bot
        self.clients = OrderedDict()

        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))

        self._parse_config()

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return '<{0}: {1} clients>'.format(self.__class__.__name__, len(self.clients))

    def _parse_config(self):
        """
        setup clients based on the config
        """
        if isinstance(self.config, list):
            for conn_settings in self.config:
                conn = self._build_client(conn_settings)

                if conn is not None:
                    self.clients[conn.id] = conn
                else:
                    self.log.error('connection creation failed')
        else:
            self.log.error('invalid connection configuration, needs to be a list')

    def _build_client(self, conn_settings):
        if not isinstance(conn_settings, dict):
            self.log.error('invalid conn_settings passed to build_connection: {0!r}'.format(conn_settings))
            return

        if 'nick' not in conn_settings:
            conn_settings['nick'] = self.bot.nick

        protocol_name = conn_settings.get('protocol')
        if protocol_name is None:
            self.log.error('no protocol defined for connection: {0!r}'.format(conn_settings))
            return

        protocol_name = protocol_name.strip().lower()

        for protocol in ProtocolBackend.plugins:
            if protocol.protocol_name.lower() == protocol_name:
                #TODO: should probably try/except this
                try:
                    conn = protocol(bot=self.bot)
                    conn.configure(**conn_settings)
                except Exception as e:
                    self.log.exception('failed to build protocol: {0!r}'.format(e))
                else:
                    return conn

        self.log.error('unsupported protocol given: {0!r}'.format(protocol_name))

    def connect(self):
        """
        connect the actual connections to the reactor
        """
        for conn_id, conn in self.clients.items():
            conn.connect()

    def disconnect(self):
        """
        placeholder
        """
        pass

    def route_action(self, action):
        if isinstance(action, Action):
            self.log.debug('destination_bots: {0!r}'.format(action.destination_bots))
            self.log.debug('destination_client_ids: {0!r}'.format(action.destination_client_ids))
            self.log.debug('destination_rooms: {0!r}'.format(action.destination_rooms))

            if self.bot in action.destination_bots:
                for client_id in action.destination_client_ids:
                    if client_id in self.clients:
                        self.log.debug('queuing action {0!r} on client {1!r}'.format(action, self.clients[client_id]))
                        self.clients[client_id].queue_action(action)

    @property
    def default_connection(self):
        for client in self.clients:
            return client #.default_room
        self.log.error('unable to get default client on {0!r}'.format(self))


########NEW FILE########
__FILENAME__ = constants
OFF = 0
ON = 1
DISCONNECTED = 20
CONNECTED = 30

DEFAULT_EVENT_VERSION = 1
DEFAULT_ACTION_VERSION = 1
########NEW FILE########
__FILENAME__ = management
from importlib import import_module
import os
import re
import shutil
import argparse

import brutal


def _make_writeable(filename):
    # thx django
    import stat
    if not os.access(filename, os.W_OK):
        st = os.stat(filename)
        new_permissions = stat.S_IMODE(st.st_mode) | stat.S_IWUSR
        os.chmod(filename, new_permissions)


def spawn_command(spawn_name):
    cwd = os.getcwd()

    try:
        import_module(spawn_name)
    except ImportError:
        pass
    else:
        #conflicts with the name of an existing python module and cannot be used as a project. roll with a virtualenv.
        raise

    # check valid dir name
    if not re.search(r'^[_a-zA-Z]\w*$', spawn_name):
        raise

    base_dir = os.path.join(cwd, spawn_name)

    try:
        #print 'MKDIR {0}'.format(base_dir)
        os.mkdir(base_dir)
    except OSError as e:
        # log dat e?
        raise

    template_dir = os.path.join(brutal.__path__[0], 'spawn', 'spawn_template')

    for base, sub, files in os.walk(template_dir):
        relative = base[len(template_dir) + 1:].replace('spawn_name', spawn_name)
        if relative:
            #print 'MKDIR {0}'.format(os.path.join(base_dir, relative))
            os.mkdir(os.path.join(base_dir, relative))
        for f in files:
            if f.endswith('.pyc'):
                continue
            path_old = os.path.join(base, f)
            path_new = os.path.join(base_dir, relative, f.replace('spawn_name', spawn_name))

            #print "\nOLD: {0}".format(path_old)
            #print "NEW: {0}".format(path_new)
            fp_old = open(path_old, 'r')
            fp_new = open(path_new, 'w')
            fp_new.write(fp_old.read().replace('{{ spawn_name }}', spawn_name))
            fp_old.close()
            fp_new.close()

            try:
                shutil.copymode(path_old, path_new)
                _make_writeable(path_new)
            except OSError:
                raise


#TODO: get rid of config_name, rename func to start_bots
def run_command(config_name):
    import brutal.run
    from brutal.conf import config

    brutal.run.main(config)


# django general design pattern mimicked
class Overlord(object):
    def __init__(self):
        self.parser = self.build_parser()

    def build_parser(self):
        # global options
        config = argparse.ArgumentParser(add_help=False)
        config.add_argument('-c', '--config', help='specify the config module you would like to use')

        # primary parser
        parser = argparse.ArgumentParser(description='Go forth. Go forth, and DIE!', parents=[config])
        subparsers = parser.add_subparsers(help='commands', dest='command')

        # spawn
        spawn_cmd = subparsers.add_parser('spawn', help='create new bot')
        spawn_cmd.add_argument('name', action='store', help='new bot spawn name')

        # run
        subparsers.add_parser('run', help='run the bot in the cwd')

        return parser

    def execute(self, config_name=None):
        #add version
        parsed_args = self.parser.parse_args()

        command = parsed_args.command

        if command == 'run':
            config = parsed_args.config or config_name
            if config is None:
                raise
            run_command(config)

        elif command == 'spawn':
            project_name = parsed_args.name
            print 'spawning {0}'.format(project_name)

            spawn_command(project_name)


def exec_overlord(config_name=None):
    overlord = Overlord()
    overlord.execute(config_name)

########NEW FILE########
__FILENAME__ = models
import time
import logging

from brutal.core.constants import DEFAULT_EVENT_VERSION, DEFAULT_ACTION_VERSION


# class NetworkConfig(object):
#     __metaclass__ = PluginRoot
#     protocol_name = None
#
#     def __init__(self):
#         if self.protocol_name is None:
#             raise NotImplementedError
#


class Network(object):
    def __init__(self):
        self.protocol = None
        self.log_traffic = None
        self.server = None
        self.port = None
        self.use_ssl = None

        # network user / pass
        self.user = None
        self.password = None

        # rooms / users
        self.chats = None

    def parse_config(self, **kwargs):
        self.protocol = kwargs.get('protocol')
        self.log_traffic = kwargs.get('log_traffic', False)
        self.server = kwargs.get('server', 'localhost')
        self.port = kwargs.get('port')
        self.use_ssl = kwargs.get('use_ssl')

        self.nick = kwargs.get('nick')
        self.password = kwargs.get('password')

        if 'channels' in kwargs:
            self.rooms = kwargs.get('channels', [])
        elif 'rooms' in kwargs:
            self.rooms = kwargs.get('rooms', [])


class Chat(object):
    def __init__(self):
        # room id or user id
        self.id = None
        self.last_active = None

        self.users = None


class Room(Chat):
    pass


class User(Chat):
    pass


class Event(object):
    """
    This is the generic object which is used to handle objects received
    Gets generated for every single event the bot _receives_.
    """

    def __init__(self, source_bot, raw_details):  # channel, type, meta=None, server_info=None, version=None):
        """
        source_bot: the source bot the event was generated from

        details:
            client: if given, the source client the event was generated from
            type
            meta
            version
        """
        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))

        self.source_bot = source_bot
        self.raw_details = raw_details
        #self.raw_line =
        self.time_stamp = time.time()

        self.event_version = DEFAULT_EVENT_VERSION
        self.event_type = None
        self.cmd = None
        self.args = None

        self.source_client = None
        self.source_client_id = None
        self.source_room = None
        self.scope = None

        self.meta = None
        self.from_bot = None

        # TODO: move so that the bot actually calls this and passes in its list of accepted tokens
        self.parse_details()

        # probably needs to know which protocol...
        # self.server_info = server_info or {}
        # self.version = version or '1' #todo: figure out how to handle these...

        # this might be too heavy...
        # self.response = Queue()

    def __repr__(self):
        return "<{0} {1}:{2}>".format(self.__class__.__name__, self.source_bot.nick, self.event_type)

    def __str__(self):
        return repr(self)

    def parse_details(self):
        if not isinstance(self.raw_details, dict):
            raise TypeError

        self.source_client = self.raw_details.get('client')
        self.source_client_id = self.raw_details.get('client_id')
        self.source_room = self.raw_details.get('channel') or self.raw_details.get('room')

        self.scope = self.raw_details.get('scope')
        self.event_type = self.raw_details.get('type')
        self.meta = self.raw_details.get('meta')
        self.from_bot = self.raw_details.get('from_bot')
        if self.from_bot is not True:
            self.from_bot = False

        if self.event_type == 'message' and isinstance(self.meta, dict) and 'body' in self.meta:
            res = self.parse_event_cmd(self.meta['body'])
            # if res is False:
            #     self.log.debug('event not parsed as a command')

    def check_message_match(self, starts_with=None, regex=None):
        """
        simple message matching to check for commands or general message structures,
        could lead to a crash because of the regex...
        """
        match = False
        if 'msg' in self.meta and self.meta['msg'] is not None and type(self.meta['msg']) in (str, unicode):
            if starts_with is not None:
                if self.meta['msg'].startswith(starts_with):
                    match = True
                else:
                    return False
            if regex is not None:
                if match:
                    match = True
                else:
                    return False
            return match

    def parse_event_cmd(self, body, token=None):
        token = token or '!'  # TODO: make this configurable
        if type(body) not in (str, unicode):
            return False

        split = body.split()
        if len(split):

            if split[0].startswith(token):
                try:
                    cmd = split[0][1:]
                    args = split[1:]
                except Exception as e:
                    self.log.exception('failed parsing cmd from {0!r}: {1!r}'.format(body, e))
                else:
                    self.event_type = 'cmd'
                    self.cmd = cmd
                    self.args = args
                    return True
        return False


class Action(object):
    """
    used to define bot actions, mostly responses to incoming events
    possibly refactor due to similarities to events

    action types:
        msg
        join
        part
    """
    def __init__(self, source_bot, source_event=None, destination_bots=None, destination_client_ids=None, rooms=None,
                 action_type=None, meta=None):
        """
        represents an action that the bot should handle.
        """
        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))

        self.source_bot = source_bot
        self.source_event = source_event

        #TODO: this logic is so broken. fix
        # default to source_bot if no destinations given
        self.destination_bots = destination_bots or [self.source_bot, ]

        self.destination_client_ids = destination_client_ids
        self.destination_rooms = rooms
        #self.log.debug('source: {0!r}, destination: {1!r}'.format(self.source_bot, self.destination_bots))

        if source_event is not None:
            self.destination_client_ids = [self.source_event.source_client_id, ]
            self.destination_rooms = [source_event.source_room, ]

        # get client_id
        if self.destination_client_ids is None:
            if self.destination_bots:
                bot = self.destination_bots[0]

                conn_id = bot.connection_manager.default_connection

                if conn_id is not None:
                    self.destination_client_ids = [conn_id, ]
                else:
                    self.log.error('no default connections on {0!r}'.format(bot))
                    raise AttributeError

            else:
                self.log.error('no destination bots for action')
                raise AttributeError

        if self.destination_rooms is None:
            self.destination_rooms = []
            #TODO: fix this 'try all the things' method
            for bot in self.destination_bots:
                for conn_id in self.destination_client_ids:
                    if conn_id in bot.connection_manager.clients:
                        room = bot.connection_manager.clients[conn_id].default_room
                        if room is not None:
                            self.destination_rooms.append(room)

        self.time_stamp = time.time()
        self.action_version = DEFAULT_ACTION_VERSION

        self.scope = None
        if self.source_event is not None:
            self.scope = self.source_event.scope

        self.action_type = action_type
        self.meta = meta or {}

    def __repr__(self):
        return "<{0} {1}:{2} dest:{3}>".format(self.__class__.__name__, self.source_bot.nick, self.action_type,
                                               [bot.nick for bot in self.destination_bots])

    def _is_valid(self):
        """
        check contents of action to ensure that it has all required fields.
        """
        return True

    def _add_to_meta(self, key, value):
        if key is not None and value is not None:
            if type(self.meta) is dict:
                self.meta[key] = value
                return True

    def msg(self, msg, room=None):
        """
        send a msg to a room
        """
        if room:
            self.destination_room = room

        self.action_type = 'message'
        if msg is not None:
            self._add_to_meta('body', msg)
        return self

    def join(self, channel, key=None):
        """
        if supported, join a rooml
        """
        self.channel = channel
        self.type = 'join'
        if key is not None:
            self._add_to_meta('key', key)
        return self

    def part(self, channel, msg=None):
        """
        if supported, leave a room the bot is currently in
        """
        self.channel = channel
        self.type = 'part'
        if msg is not None:
            self._add_to_meta('msg', msg)
        return self
########NEW FILE########
__FILENAME__ = plugin
import re
import logging
import inspect
import functools
from twisted.internet import reactor, task, defer, threads
from twisted.python.threadable import isInIOThread

from brutal.core.models import Action, Event
from brutal.conf import config

SRE_MATCH_TYPE = type(re.match("", ""))


def threaded(func=None):
    """
    tells bot to run function in a thread
    """
    def decorator(func):
        func.__brutal_threaded = True

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


def cmd(func=None, command=None, thread=False):
    """
    this decorator is used to create a command the bot will respond to.
    """
    def decorator(func):
        func.__brutal_event = True
        func.__brutal_event_type = 'cmd'
        func.__brutal_trigger = None
        if command is not None and type(command) in (str, unicode):

            try:
                func.__brutal_trigger = re.compile(command)
            except Exception:
                logging.exception('failed to build regex for {0!r} from func {1!r}'.format(command, func.__name__))

        if func.__brutal_trigger is None:
            try:
                raw_name = r'^{0}$'.format(func.__name__)
                func.__brutal_trigger = re.compile(raw_name)
            except Exception:
                logging.exception('failing to build command from {0!r}'.format(func.__name__))
                func.__brutal_event = False

        if thread is True:
            func.__brutal_threaded = True

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


# def parser(func=None, thread=True):
#     """
#     this decorator makes the function look at _all_ lines and attempt to parse them
#     ex: logging
#     """
#     def decorator(func):
#         func.__brutal_parser = True
#
#         if thread is True:
#             func.__brutal_threaded = True
#
#         @functools.wraps(func)
#         def wrapper(*args, **kwargs):
#             return func(*args, **kwargs)
#         return wrapper
#
#     if func is None:
#         return decorator
#     else:
#         return decorator(func)


# make event_type required?
def event(func=None, event_type=None, thread=False):
    """
    this decorator is used to register an event parser that the bot will respond to.
    """
    def decorator(func):
        func.__brutal_event = True
        if event_type is not None and type(event_type) in (str, unicode):
            func.__brutal_event_type = event_type

        if thread is True:
            func.__brutal_threaded = True

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


#TODO: maybe swap this to functools.partial
def match(func=None, regex=None, thread=False):
    """
    this decorator is used to create a command the bot will respond to.
    """
    def decorator(func):
        func.__brutal_event = True
        func.__brutal_event_type = 'message'
        func.__brutal_trigger = None
        if regex is not None and type(regex) in (str, unicode):
            try:
                func.__brutal_trigger = re.compile(regex)
            except Exception:
                logging.exception('failed to build regex for {0!r} from func {1!r}'.format(regex, func.__name__))

        if func.__brutal_trigger is None:
            try:
                raw_name = r'^{0}$'.format(func.__name__)
                func.__brutal_trigger = re.compile(raw_name)
            except Exception:
                logging.exception('failing to build match from {0!r}'.format(func.__name__))
                func.__brutal_event = False

        if thread is True:
            func.__brutal_threaded = True

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


#TODO: possibly abstract like this?
class Parser(object):
    def __init__(self, func, source=None):
        self.healthy = False

        self.source = source
        if inspect.isclass(source) is True:
            self.source_name = '{0}.{1}'.format(self.source.__module__, self.source.__name__)
        elif inspect.ismodule(source) is True:
            self.source_name = self.source.__name__
        else:
            try:
                test = isinstance(source, BotPlugin)
            except TypeError:
                self.source_name = 'UNKNOWN: {0!r}'.format(source)
            else:
                if test is True:
                    self.source_name = "{0}".format(self.__class__.__name__)
                else:
                    self.source_name = 'UNKNOWN instance: {0!r}'.format(source)

        self.func = func
        self.func_name = self.func.__name__

        self.event_type = None
        self.regex = None
        self.threaded = getattr(self.func, '__brutal_threaded', False)
        self.parse_bot_events = False

        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))

        # future use:
        #self.stop_parsing = False  # if true, wont run any more parsers after this.
        #self.parent = None
        #elf.children = None

        #TODO: check if healthy
        self.event_type = getattr(self.func, '__brutal_event_type', None)
        if self.event_type in ['cmd', 'message']:
            self.regex = getattr(self.func, '__brutal_trigger', None)

            if self.regex is None:
                self.log.error('failed to get compiled regex from func for {0}'.format(self))
                self.healthy = False
            else:
                # should probably check that its a compiled re
                self.healthy = True
        else:
            self.healthy = True

        self.log.debug('built parser - event_type: {0!r}, source: {1!r}, func: {2!r}'.format(self.event_type,
                                                                                             self.source_name,
                                                                                             self.func_name))

    def __repr__(self):
        return '<{0} {1}:{2}>'.format(self.__class__.__name__, self.source_name, self.func_name)

    def __str__(self):
        return repr(self)

    def matches(self, event):
        if not isinstance(event, Event):
            self.log.error('invalid event passed to parser')
            return

        if event.event_type == self.event_type:
            if event.event_type == 'cmd':
                if event.cmd is not None and self.regex is not None:
                    try:
                        match = self.regex.match(event.cmd)
                    except Exception:
                        self.log.exception('invalid regex match attempt on {0!r}, {1!r}'.format(event.cmd, self))
                    else:
                        return match
                else:
                    self.log.error('invalid event passed in')
            elif event.event_type == 'message' and isinstance(event.meta, dict) and 'body' in event.meta:
                body = event.meta['body']
                #TODO: HERE, make this smarter.
                if self.regex is not None and type(body) in (str, unicode):
                    try:
                        match = self.regex.match(body)
                    except Exception:
                        self.log.exception('invalid regex match attempt on {0!r}, {1!r}'.format(body, self))
                    else:
                        return match
                else:
                    self.log.error('message contains no body to regex match against')
            else:
                return True
        else:
            self.log.debug('event_parser not meant for this event type')

    @classmethod
    def build_parser(cls, func, source):
        if getattr(func, '__brutal_event', False):
            return cls(func, source)


class PluginManager(object):
    def __init__(self, bot):
        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))
        self.bot = bot
        self.event_parsers = {None: [], }

        self.plugin_modules = {}
        self.plugin_instances = {}

        self.status = None

        # possibly track which bot this PM is assigned to?
        # should track which module it came from for easy unloading

    # def start(self):
    #     installed_plugins = getattr(config, PLUGINS)

    def start(self, enabled_plugins=None):
        if enabled_plugins is not None and not type(enabled_plugins) in (list, dict):
            self.log.error('improper plugin config, list or dictionary required')
            return

        installed_plugins = getattr(config, 'PLUGINS')

        if installed_plugins is None:
            self.log.error('error getting INSTALLED_PLUGINS')
            return

        # find enabled plugin modules and instantiate classes of every BotPlugin within modules
        for plugin_module in installed_plugins:
            if enabled_plugins is not None:
                if plugin_module.__name__ not in enabled_plugins:
                    continue

            self.plugin_modules[plugin_module] = plugin_module.__name__

            # get classes
            for class_name, class_object in inspect.getmembers(plugin_module, inspect.isclass):
                if issubclass(class_object, BotPlugin):
                    try:
                        instance = class_object(bot=self.bot)
                    except Exception:
                        self.log.exception('failed to load plugin {0!r} from {1!r}'.format(class_name,
                                                                                           plugin_module.__name__))
                    else:
                        try:
                            instance.setup()
                        except Exception:
                            self.log.exception('failed to setup plugin {0!r} from {1!r}'.format(class_name,
                                                                                                plugin_module.__name))
                        else:
                            self.plugin_instances[instance] = plugin_module.__name__

        self._register_plugins(self.plugin_modules, self.plugin_instances)

    def _register_plugins(self, plugin_modules, plugin_instances):
        """
        TODO: add default plugins

        for this bot, load all the plugins
        - find event handlers and register them
        """
        for module in plugin_modules:
            self._register_plugin_functions(module)

        for plugin_instance in plugin_instances:
            self._register_plugin_class_methods(plugin_instance)

    def remove_plugin(self, plugin_module):
        #TODO: fill out
        pass

    def _register_plugin_functions(self, plugin_module):
        module_name = plugin_module.__name__
        self.log.debug('loading plugins from module {0!r}'.format(module_name))

        # step through all functions in module
        for func_name, func in inspect.getmembers(plugin_module, inspect.isfunction):
            try:
                parser = Parser.build_parser(func=func, source=plugin_module)
            except Exception:
                self.log.exception('failed to build parser from {0} ({1})'.format(func_name, module_name))
                continue
            else:
                if parser is not None:
                    if parser.event_type in self.event_parsers:
                        self.event_parsers[parser.event_type].append(parser)
                    else:
                        self.event_parsers[parser.event_type] = [parser, ]

    def _register_plugin_class_methods(self, plugin_instance):
        #TODO: should wrap this...
        class_name = plugin_instance.__class__.__name__
        self.log.debug('loading plugins from instance of {0!r}'.format(class_name))

        for func_name, func in inspect.getmembers(plugin_instance, inspect.ismethod):
            try:
                parser = Parser.build_parser(func=func, source=plugin_instance)
            except Exception:
                self.log.exception('failed to build parser from {0} ({1})'.format(func_name, class_name))
                continue
            else:
                if parser is not None:
                    if parser.event_type in self.event_parsers:
                        self.event_parsers[parser.event_type].append(parser)
                    else:
                        self.event_parsers[parser.event_type] = [parser, ]

    # event processing
    @defer.inlineCallbacks
    def _run_event_processor(self, event_parser, event, *args):
        run = True
        response = None
        # TODO: make this check if from_bot == _this_ bot
        if event.from_bot is True:
            if event_parser.parse_bot_events is not True:
                self.log.info('ignoring event from bot: {0!r}'.format(event))
                run = False

        if run is True:
            if event_parser.threaded is True:
                self.log.debug('executing event_parser {0!r} in thread'.format(event_parser))
                response = yield threads.deferToThread(event_parser.func, event, *args)
            else:
                self.log.debug('executing event_parser {0!r}'.format(event_parser))
                #try:
                response = yield event_parser.func(event, *args)

        defer.returnValue(response)

    def process_event(self, event):
        #TODO: this needs some love

        # this will keep track of all the responses we get
        responses = []

        # TODO: wrap everything in try/except
        if not isinstance(event, Event):
            self.log.error('invalid event, ignoring: {0!r}'.format(event))
            raise

        self.log.debug('processing {0!r}'.format(event))

        # run only processors of this event_type
        if event.event_type is not None and event.event_type in self.event_parsers:
            self.log.debug('detected event_type {0!r}'.format(event.event_type))
            for event_parser in self.event_parsers[event.event_type]:
                # check if match
                match = event_parser.matches(event)
                response = None
                if match is True:
                    self.log.debug('running event_parser {0!r}'.format(event_parser))
                    response = self._run_event_processor(event_parser, event)
                elif isinstance(match, SRE_MATCH_TYPE):
                    self.log.debug('running event_parser {0!r} with regex results {1!r}'.format(event_parser,
                                                                                                match.groups()))
                    response = self._run_event_processor(event_parser, event, *match.groups())

                if response is not None:
                    responses.append(response)

        # default 'all' parsers
        for event_parser in self.event_parsers[None]:
            self.log.debug('running event_parser {0!r}'.format(event_parser))
            # response = yield self._run_event_processor(event_parser, event)
            response = self._run_event_processor(event_parser, event)

            if response is not None:
                responses.append(response)

        for response in responses:
            response.addCallback(self.process_result, event)

        return responses
        #defer.returnValue(responses)

    # def emit_action() - out of band action to the bot.

    def process_result(self, response, event):
        if response is not None:
            self.log.debug('RESPONSE: {0!r}'.format(response))
            if isinstance(response, Action):
                return response
                #self.bot.action_queue.put(response)
            else:
                # a = self.build_action(response, event)
                return self.build_action(response, event)

                # if a is not None:
                #     self.bot.action_queue.put(a)

    def build_action(self, action_data, event=None):
        if type(action_data) in (str, unicode):
            try:
                a = Action(source_bot=self.bot, source_event=event).msg(action_data)
            except Exception as e:
                self.log.exception('failed to build action from {0!r}, for {1!r}: {2!r}'.format(action_data, event, e))
            else:
                return a


#TODO: completely changed, need to rework this...
class BotPlugin(object):
    """
    base plugin class

    """
    event_version = '1'
    built_in = False  # is this a packaged plugin

    #TODO: make a 'task' decorator...
    def __init__(self, bot=None):
        """
        don't touch me. plz?

        each bot that spins up, loads its own plugin instance

        TODO: move the stuff in here to a separate func and call it after we initialize the instance.
            that way they can do whatever they want in init
        """
        self.bot = bot

        self.log = logging.getLogger('{0}.{1}'.format(self.__module__, self.__class__.__name__))

        self._active = False  # is this instance active?
        self._delayed_tasks = []  # tasks scheduled to run in the future
        self._looping_tasks = []

    # Tasks

    def _clear_called_tasks(self):
        # yes.
        self._delayed_tasks[:] = [d for d in self._delayed_tasks if d.called()]

    def _handle_task_response(self, response, *args, **kwargs):
        self.log.debug('PLUGIN TASK RESULTS: {0!r}'.format(response))
        self.log.debug('TASK ARGS: {0!r}'.format(args))
        self.log.debug('TASK KWARGS: {0!r}'.format(kwargs))
        # hacking this in for now:
        event = kwargs.get('event')
        try:
            a = self.build_action(action_data=response, event=event)
        except Exception:
            self.log.exception('failed to build action from plugin task {0!r}, {1!r}, {2!r}'.format(response, args,
                                                                                                    kwargs))
        else:
            self.log.debug('wat: {0!r}'.format(a))
            if a is not None:
                self._queue_action(a, event)

    def build_action(self, action_data, event=None):
        #TODO this is hacky - fix it.
        if type(action_data) in (str, unicode):
            try:
                a = Action(source_bot=self.bot, source_event=event).msg(action_data)
            except Exception:
                logging.exception('failed to build action from {0!r}, for {1!r}'.format(action_data, event))
            else:
                return a


    @defer.inlineCallbacks
    def _plugin_task_runner(self, func, *args, **kwargs):
        try:
            if getattr(func, '__brutal_threaded', False):
                self.log.debug('executing plugin task in thread')  # add func details
                response = yield threads.deferToThread(func, *args, **kwargs)
            else:
                self.log.debug('executing plugin task')  # add func details
                response = yield func(*args, **kwargs)

            yield self._handle_task_response(response, *args, **kwargs)
            # defer.returnValue(response)
        except Exception as e:
            self.log.error('_plugin_task_runner failed: {0!r}'.format(e))

    def delay_task(self, delay, func, *args, **kwargs):
        if inspect.isfunction(func) or inspect.ismethod(func):
            self.log.debug('scheduling task {0!r} to run in {1} seconds'.format(func.__name__, delay))
            # trying this.. but should probably just use callLater
            d = task.deferLater(reactor, delay, self._plugin_task_runner, func, *args, **kwargs)
            self._delayed_tasks.append(d)

    def loop_task(self, loop_time, func, *args, **kwargs):
        if inspect.isfunction(func) or inspect.ismethod(func):
            self.log.debug('scheduling task {0!r} to run every {1} seconds'.format(func.__name__, loop_time))
            now = kwargs.pop('now', True)
            #event = kwargs.pop('event', None)
            t = task.LoopingCall(self._plugin_task_runner, func, *args, **kwargs)
            t.start(loop_time, now)
            self._looping_tasks.append(t)

    # Actions

    def _queue_action(self, action, event=None):
        if isinstance(action, Action):
            if isInIOThread():
                self.bot.route_response(action, event)
            else:
                reactor.callFromThread(self.bot.route_response, action, event)
        else:
            self.log.error('tried to queue invalid action: {0!r}'.format(action))

    def msg(self, msg, room=None, event=None):
        a = Action(source_bot=self.bot, source_event=event).msg(msg, room=room)
        self._queue_action(a, event)

    # internal

    def enable(self):
        self.log.info('enabling plugin on {0!r}: {1!r}'.format(self.bot, self.__class__.__name__))

        # eh. would like to be able to resume... but that's :effort:
        self._delayed_tasks = []
        self._looping_tasks = []
        # set job to clear task queue
        self.loop_task(15, self._clear_called_tasks, now=False)
        self._active = True

    def disable(self):
        self.log.info('disabling plugin on {0!r}: {1!r}'.format(self.bot, self.__class__.__name__))
        self._active = False

        for func in self._delayed_tasks:
            if func.called is False:
                func.cancel()

        for func in self._looping_tasks:
            if func.running:
                func.stop()

        self._delayed_tasks = []
        self._looping_tasks = []

#     def handle_event(self, event):
#         if isinstance(event, Event):
#             if self._version_matches(event):
# #                if self._is_match(event):
#                 self._parse_event(event)
#
    #min_version
    #max_version
    def _version_matches(self, event):
        #TODO: ugh.. figure out what i want to do here...
        if event.version == self.event_version:
            return True
        return False

    def setup(self, *args, **kwargs):
        """
        use this to do any one off actions needed to initialize the bot once its active
        """
        pass
        #raise NotImplementedError

    def _is_match(self, event):
        """
        returns t/f based if the plugin should parse the event
        """
        return True
        #raise NotImplementedError

    def _parse_event(self, event):
        """
        takes in an event object and does whatever the plugins supposed to do...
        """
        raise NotImplementedError
########NEW FILE########
__FILENAME__ = utils
import functools

#TODO: not using this anymore.
def decorator(plz_decorate):
    """
    create a decorator out of a function
    uh.. i hope this works the way i want it to work
    """
    @functools.wraps(plz_decorate)
    def final(func=None, **kwargs):

        def decorated(func):
            @functools.wraps(func)
            def wrapper(*a, **kw):
                return plz_decorate(func, a, kw, **kwargs)
            return wrapper

        if func is None:
            return decorated
        else:
            return decorated(func)

    return final


class PluginRoot(type):
    """
    metaclass that all plugin base classes will use
    """
    def __init__(cls, name, bases, attrs):
        if not hasattr(cls, 'plugins'):
            # only execs when processing mount point itself
            cls.plugins = []
        else:
            # plugin implementation, register it
            cls.plugins.append(cls)
########NEW FILE########
__FILENAME__ = basic
from brutal.core.plugin import cmd

@cmd
def help(event):
    return 'no...'
########NEW FILE########
__FILENAME__ = core
import uuid
import logging
from twisted.internet.defer import DeferredQueue

from brutal.core.utils import PluginRoot
from brutal.core.models import Event, Action


def catch_error(failure):
    """ used for errbacks
    """
    return failure.getErrorMessage()


class ProtocolBackend(object):
    """
    all protocol backends will inherit from this.
    """
    __metaclass__ = PluginRoot
    protocol_name = None

    def __init__(self, bot):
        if self.protocol_name is None:
            raise NotImplementedError

        self.id = str(uuid.uuid1())
        self.bot = bot
        self.rooms = None

        self.action_queue = DeferredQueue()
        self.consume_actions(self.action_queue)

        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))

    def __repr__(self):
        return '<{0} {1!s}>'.format(self.__class__.__name__, self.id)

    def __str__(self):
        return repr(self)

    @property
    def default_room(self):
        if self.rooms is not None:
            for i in self.rooms:
                return i
        self.log.error('unable to get default room from {0!r} on {1!r}'.format(self.rooms, self))

    def handle_event(self, event):
        """
        takes events, tags them with the current backend, and places them on bot event_queue
        """
        if isinstance(event, Event):
            event.source_client = self
            event.source_client_id = self.id
            self.bot.new_event(event)
        elif isinstance(event, dict):
            event['client'] = self
            event['client_id'] = self.id
            self.bot.new_event(event)
        else:
            self.log.error('invalid Event passed to {0}')

    def queue_action(self, action):
        if isinstance(action, Action):
            self.action_queue.put(action)
        else:
            self.log.error('invalid object handed to protocol action queue: {0!r}'.format(action))

    def consume_actions(self, queue):
        """
        responsible for reading actions given to this connection
        """
        def consumer(action):
            if isinstance(action, Action):
                self.handle_action(action)
            else:
                self.log.warning('invalid action put in queue: {0!r}'.format(action))

            queue.get().addCallback(consumer)
        queue.get().addCallback(consumer)

    def handle_action(self, action):
        """
        should take an action and act on it
        """
        raise NotImplementedError

    def configure(self, *args, **kwargs):
        """
        should read in the config options and setup client
        """
        raise NotImplementedError

    def connect(self, *args, **kwargs):
        """
        should connect the client
        """
        #TODO: find a way to delay connections (have it be user definable in the config) reactor.callLater
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = irc
import logging
from twisted.internet import reactor, protocol
from twisted.python import log
from twisted.words.protocols import irc

from brutal.protocols.core import ProtocolBackend
#from brutal.protocols.core import catch_error

IRC_DEFAULT_PORT = 6667

# OLD
# def irc_event_parser(raw_event):
#     if 'meta' in raw_event:
#         if 'user' in raw_event['meta']:
#             try:
#                 username = raw_event['meta']['user'].split('!', 1)[0]
#             except KeyError:
#                 pass
#             else:
#                 raw_event['meta']['username'] = username
#
#     raw_event['event_version'] = event_version or None
#
#     # server info - protocol_name probably useles...
#     #server_info = {'protocol': self.__class__.__name__, 'hostname': self.hostname}
#     #hostname gets changed on connection RPL_WELCOMEMSG
#     try:
#         server_info['addr'] = transport.addr[0]
#     except Exception:
#         server_info['addr'] = None
#     try:
#         server_info['port'] = transport.addr[1]
#     except Exception:
#         server_info['port'] = None
#
#     raw_event['server_info'] = server_info
#
#     #this needs to return a defered... should use maybedeferred?
#     d = self.factory.new_event(raw_event)


class IrcBotProtocol(irc.IRCClient):
    """
    Handles basic bot activity on irc. generates events and fires
    """
    event_version = '1'

    def __init__(self):
        self.state_handler = None
        self.timer = None
        self.channel_users = {}
        self.hostname = 'trolololol'  # <- nothing
        self.realname = 'brutal_bot'  # <- ircname
        self.username = 'brutal'  # <- ~____@...

    @property
    def nickname(self):
        return self.factory.nickname

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.factory.conn = self

    #-- server info
    def created(self, when):
        log.msg('created: {0!r}'.format(when), logLevel=logging.DEBUG)

    def yourHost(self, info):
        log.msg('yourHost: {0!r}'.format(info), logLevel=logging.DEBUG)

    def myInfo(self, servername, version, umodes, cmodes):
        log.msg('myInfo - servername: {0!r}, version: {1!r}, umodes: {2!r}, cmodes: {3!r}'.format(servername, version,
                                                                                                  umodes, cmodes),
                logLevel=logging.DEBUG)

    def luserClient(self, info):
        log.msg('luserClient: {0!r}'.format(info), logLevel=logging.DEBUG)

    def bounce(self, info):
        log.msg('bounce: {0!r}' % info, logLevel=logging.DEBUG)

    def isupport(self, options):
        log.msg('isupport: supported._features {0!r}'.format(self.supported._features), logLevel=logging.DEBUG)

    def luserChannels(self, channels):
        log.msg('luserChannels: {0!r}'.format(channels), logLevel=logging.DEBUG)

    def luserOp(self, ops):
        log.msg('luserOp: {0!r}'.format(ops), logLevel=logging.DEBUG)

    def luserMe(self, info):
        log.msg('luserMe: {0!r}'.format(info), logLevel=logging.DEBUG)

    #-- methods involving dis bot
    def privmsg(self, user, channel, message):
        """
        handle a new msg on irc
        """
        log.msg('privmsg - user: {0!r}, channel: {1!r}, msg: {2!r}'.format(user, channel, message),
                logLevel=logging.DEBUG)

        nick, _, host = user.partition('!')
        message = message.strip()

        #command, sep, rest = message.lstrip('!').partition(' ')

        event_data = {'type': 'priv_msg',
                      'channel': channel,
                      'meta': {
                          'user': user,
                          'msg': message}}

        self._botte_event(event_data)

        #event = Event(self, self, 'msg', {'user':user, 'source':channel, 'msg':message})
        #self._botte_event(event)
#        if self.nickname in message:
#            self.msg(channel, 'no :E')
#            log.msg('whois'n %s' % user)
#            log.msg(repr(user))
#            log.msg('derp:')
#            self.whois(user)

    def joined(self, channel):
        log.msg('joined: {0!r}'.format(channel), logLevel=logging.DEBUG)
        #self.say(channel, 'hi guys!')# %s' % channel)
        #self.sendLine('NAMES %s' % channel)

    def left(self, channel):
        log.msg('left: {0!r}'.format(channel), logLevel=logging.DEBUG)

    def noticed(self, user, channel, message):
        # automatic replies MUST NEVER be sent in response to a NOTICE message
        log.msg('noticed - user: {0!r}, channel: {1!r}, msg: {2!r}'.format(user, channel, message),
                logLevel=logging.DEBUG)

    def modeChanged(self, user, channel, set, modes, args):
        log.msg('modeChanged - user: {0!r}, channel: {1!r}, set: {2!r}, modes: {3!r}, args: {4!r}'.format(user, channel,
                                                                                                          set, modes,
                                                                                                          args),
                logLevel=logging.DEBUG)

    #pong

    def signedOn(self):
        for channel in self.factory.channels:
            if isinstance(channel, tuple):
                #TODO: confirm len and
                self.join(channel[0], channel[1])
            else:
                self.join(channel)

    def kickedFrom(self, channel, kicker, message):
        log.msg('kickedFrom - channel: {0!r}, kicker: {2!r}, msg: {3!r}'.format(channel, kicker, message),
                logLevel=logging.DEBUG)

    #nickChanged
    #TODO: track dis

    #-- observed actions of others in a channel
    def userJoined(self, user, channel):
        log.msg('userJoined - user: {0!r}, channel: {1!r}'.format(user, channel), logLevel=logging.DEBUG)

    def userLeft(self, user, channel):
        log.msg('userLeft - tuser: {0!r}, channel: {1!r}'.format(user, channel), logLevel=logging.DEBUG)

    def userQuit(self, user, quitMessage):
        log.msg('userQuit - user: {0!r}, quit msg: {1!r}'.format(user, quitMessage), logLevel=logging.DEBUG)

    def userKicked(self, kickee, channel, kicker, message):
        log.msg('userKicked - user: {0!r}, channel: {1!r}, kicker: {2!r}, msg: {3!r}'.format(kickee, channel, kicker,
                                                                                             message),
                logLevel=logging.DEBUG)

    def action(self, user, channel, data):
        log.msg('action - user: {0!r}, channel: {1!r}, data: {2!r}'.format(user, channel, data), logLevel=logging.DEBUG)

    def topicUpdated(self, user, channel, newTopic):
        log.msg('topicUpdated - user: {0!r}, channel: {1!r}, topic: {2!r}'.format(user, channel, newTopic),
                logLevel=logging.DEBUG)

    def userRenamed(self, oldname, newname):
        log.msg('userRenamed - old: {0!r}, new: {1!r}'.format(oldname, newname), logLevel=logging.DEBUG)

    #-- recv server info
    def receivedMOTD(self, motd):
        log.msg('receivedMOTD: {0!r}'.format(motd), logLevel=logging.DEBUG)

    #--  custom
    def received_names(self, channel, nick_list):
        self.channel_users[channel] = nick_list
        #self.say(channel, 'current users: {0!r}'.format(nick_list)

    #-- client cmds
    # join(self, channel, key=None)
    # leave(self, channel, reason=None)
    # kick(self, channel, user, reason=None)
    # invite(self, user, channel)
    # topic(self, channel, topic=None)
    # mode(self, chan, set, modes, limit = None, user = None, mask = None)
    # say(self, channel, message, length=None) #wtf is this?
    # msg(self, user, message, length=None)
    # notice(self, user, message)
    # away(self, message='')
    # back(self)
    # whois(self, nickname, server=None)
    # register(self, nickname, hostname='foo', servername='bar')
    # setNick(self, nickname)
    # quit(self, message = '')

    #-- user input commands, client-> client
    # describe(self, channel, action)
    #ping
    #dccSend
    #dccResume
    #dccAcceptResume

    #-- custom protocol stuff
    def names(self, channel):
        channel = channel.lower()
        self.sendLine('NAMES {0}'.format(channel))

    #-- lots hidden here... server->client
    def irc_PONG(self, prefix, params):
        """
        parse a server pong message
        we don't care about responses to our keepalive PINGS
        """
        log.msg('irc_PONG - prefix: {0!r}, params: {1!r}'.format(prefix, params), logLevel=logging.DEBUG)

    def irc_RPL_NAMREPLY(self, prefix, params):
        #log.msg('irc_RPL_NAMREPLY - prefix: {0!r}, {1!r}'.format(prefix, params), logLevel=logging.DEBUG)
        channel = params[2].lower()
        nicklist = []
        for name in params[3].split(' '):
            nicklist.append(name)

        self.received_names(channel, nicklist)

    def irc_RPL_ENDOFNAMES(self, prefix, params):
        channel = params[1].lower()
        if channel not in self.channel_users:
            return

        log.msg('names output {0!r}: {1!r}'.format(channel, self.channel_users[channel]), logLevel=logging.DEBUG)
        #self.received_names(channel, nicklist)
        #should fire here

    def irc_unknown(self, prefix, command, params):
        """ useful for debug'n weird irc data """
        log.msg('irc_unknown - prefix: {0!r}, cmd: {1!r}, params: {2!r}'.format(prefix, command, params),
                logLevel=logging.DEBUG)

    #-- BOTTE SPECIFIC
    def _botte_event(self, raw_event):
        if 'meta' in raw_event:
            if 'user' in raw_event['meta']:
                try:
                    username = raw_event['meta']['user'].split('!', 1)[0]
                except KeyError:
                    pass
                else:
                    raw_event['meta']['username'] = username

        raw_event['event_version'] = self.event_version or None

        # server info - protocol_name probably useles...
        server_info = {'protocol': self.__class__.__name__, 'hostname': self.hostname}
        #hostname gets changed on connection RPL_WELCOMEMSG
        try:
            server_info['addr'] = self.transport.addr[0]
        except Exception:
            server_info['addr'] = None
        try:
            server_info['port'] = self.transport.addr[1]
        except Exception:
            server_info['port'] = None

        raw_event['server_info'] = server_info

        #this needs to return a defered... should use maybedeferred?
        d = self.factory.new_event(raw_event)
        # if isinstance(d, defer.Deferred):
        #     #d.addErrback(catch_error)
        #     d.addCallback(self._botte_response) #<- attaches protocol response
        #     #d.callback(raw_event)

    def _botte_response(self, event):
        #TODO: rather than parsing through what we know is a queue, would be better to pass queue initially, or use other datatype
        while not event.response.empty():
            # if i want to rate limit these, i should group them so that sets get executed together...
            action = event.response.get()
            self._botte_parse_action(action)

    def _botte_parse_action(self, action):
        if action.type == 'msg':
            if 'msg' in action.meta and action.meta['msg'] is not None and len(action.meta['msg']):
                self.say(action.channel, action.meta['msg'])
        elif action.type == 'join':
            if 'key' in action.meta and action.meta['key'] is not None and len(action.meta['key']):
                key = action.meta['key']
            else:
                key = None
            self.join(action.channel, key=key)
        elif action.type == 'part':
            if 'msg' in action.meta and action.meta['msg'] is not None and len(action.meta['msg']):
                msg = action.meta['msg']
            else:
                msg = None
            self.leave(action.channel, msg)


class SimpleIrcBotProtocol(irc.IRCClient):
    """
    Handles basic bot activity on irc. generates events and fires
    """
    event_version = '1'

    def __init__(self):
        self.channel_users = {}
        #TODO: accept these as init vars
        self.hostname = 'brutal_bot'
        self.realname = 'brutal_bot'
        self.username = 'brutal_bot'

    @property
    def nickname(self):
        return self.factory.nickname

    @property
    def channels(self):
        return self.factory.channels

    def privmsg(self, user, channel, message):
        """
        handle a new msg on irc
        """
        log.msg('privmsg - user: {0!r}, channel: {1!r}, msg: {2!r}'.format(user, channel, message),
                logLevel=logging.DEBUG)

        nick, _, host = user.partition('!')
        message = message.strip()

        # parse if we're the owner / message was to bot directly
        if channel == self.nickname:
            event_data = {'type': 'message', 'scope': 'private', 'meta': {'from': user, 'body': message}}
        else:
            event_data = {'type': 'message', 'scope': 'public', 'channel': channel, 'meta': {'from': user,
                                                                                             'body': message}}

        self._bot_process_event(event_data)

    def action(self, user, channel, data):
        """
        handle a new msg on irc
        """
        log.msg('action - user: {0!r}, channel: {1!r}, data: {2!r}'.format(user, channel, data), logLevel=logging.DEBUG)

        nick, _, host = user.partition('!')
        data = data.strip()

        # parse if we're the owner / message was to bot directly
        if channel == self.nickname:
            event_data = {'type': 'message', 'scope': 'private', 'meta': {'from': user, 'body': data, 'emote': True}}
        else:
            event_data = {'type': 'message', 'scope': 'public', 'channel': channel, 'meta': {'from': user, 'body': data,
                                                                                             'emote': True}}

        self._bot_process_event(event_data)

    def signedOn(self):
        for channel in self.channels:
            if isinstance(channel, tuple):
                if len(channel) > 1:
                    try:
                        channel, key = channel
                    except ValueError:
                        log.err('unable to parse channel/key combo from: {0!r}'.format(channel))
                    else:
                        self.join(channel=channel, key=key)
                else:
                    self.join(channel=channel[0])
            else:
                self.join(channel)

    def irc_unknown(self, prefix, command, params):
        """
        useful for debug'n weird irc data
        """
        log.msg('irc_unknown - prefix: {0!r}, cmd: {1!r}, params: {2!r}'.format(prefix, command, params),
                logLevel=logging.DEBUG)

    #-- BOT SPECIFIC
    def _bot_process_event(self, raw_event):
        """
        passes raw data to bot
        """
        self.factory.new_event(raw_event)

    def _bot_process_action(self, action):
        log.msg('irc acting on {0!r}'.format(action), logLevel=logging.DEBUG)
        if action.action_type == 'message':
            body = action.meta.get('body')
            if body:
                dest = action.destination_room
                if dest:
                    if dest[0] == '#':
                        self.say(dest, body)
                    else:
                        self.msg(dest, body)


class IrcBotClient(protocol.ReconnectingClientFactory):
    protocol = SimpleIrcBotProtocol

    def __init__(self, channels, nickname, backend=None):
        self.channels = channels
        self.nickname = nickname
        self.backend = backend

        # this might be bad?
        self.current_conn = None

    def buildProtocol(self, addr):
        p = self.protocol()
        p.factory = self

        # adding this
        self.current_conn = p

        return p

    def clientConnectionLost(self, connector, reason):
        self.current_conn = None
        log.msg('connection lost, reconnecting: ({0!r})'.format(reason), logLevel=logging.DEBUG)
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        self.current_conn = None
        log.msg('connection failed: {0!r}'.format(reason), logLevel=logging.DEBUG)
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def new_event(self, event):
        """
        Event! creates a deferred for the bot to append too....
        """
        if self.backend:
            self.backend.handle_event(event)

    def handle_action(self, action):
        if self.current_conn is not None:
            self.current_conn._bot_process_action(action)
        else:
            log.err('connection not active')


class IrcBackend(ProtocolBackend):
    """
    parses config options for irc protocol, responsible for handling events
    """
    protocol_name = 'irc'

    def configure(self, *args, **kwargs):
        #TODO: add log_traffic for IRC
        self.log_traffic = kwargs.get('log_traffic', False)
        self.server = kwargs.get('server', 'localhost')
        self.port = kwargs.get('port', IRC_DEFAULT_PORT)
        self.use_ssl = kwargs.get('use_ssl', False)

        self.nick = kwargs.get('nick')
        self.password = kwargs.get('password')

        self.rooms = kwargs.get('channels') or kwargs.get('rooms', [])

        self.client = IrcBotClient(self.rooms, nickname=self.nick, backend=self)

    def connect(self, *args, **kwargs):
        """
        starts connection on reactor
        """
        # if use_ssl:
        #     reactor.connectSSL
        log.msg('connecting to {0}:{1} with nick {2!r}'.format(self.server, self.port, self.nick),
                logLevel=logging.DEBUG)
        reactor.connectTCP(self.server, self.port, self.client)

    def handle_action(self, action):
        self.client.handle_action(action)
########NEW FILE########
__FILENAME__ = testconsole
import logging
from os import linesep

from twisted.internet import stdio
from twisted.protocols import basic

from brutal.protocols.core import ProtocolBackend


class TestConsoleClient(basic.LineReceiver):
    delimiter = linesep
    #delimiter = '\n'  # unix terminal style newlines

    def __init__(self, backend):
        # ugh old style classes
        #basic.LineReceiver.__init__(self)

        self.backend = backend

        self.log = logging.getLogger('brutal.protocol.{0}'.format(self.__class__.__name__))

    def connectionMade(self):
        self.log.debug('connected!')
        self.sendLine('>>> brutal bot test console connected')

        #from twisted.internet import task
        #loop = task.LoopingCall(self.print_loop)
        #loop.start(2.0)

    def lineReceived(self, line):
        # ignore blank lines
        if not line:
            return

        self.log.debug('line received: {0!r}'.format(line))
        msg = line
        if self.backend.rooms is not None:
            room = self.backend.rooms[0]
        else:
            room = 'test_console'

        event_data = {'type': 'message', 'scope': 'public', 'room': room, 'meta': {'from': 'console', 'body': msg}}
        #self.sendLine('GOT! {0!r}'.format(line))
        self._bot_process_event(event_data)

    def _bot_process_event(self, raw_event):
        self.backend.handle_event(raw_event)

    def bot_process_action(self, action):
        #self.sendLine('>>> got action! {0!r}'.format(action))
        if action.action_type == 'message':
            body = action.meta.get('body')
            if body:
                for dest in action.destination_rooms:
                    self.sendLine('>>> {0}: {1}'.format(dest, body))

    def print_loop(self):
        self.sendLine('>>> loop')


class TestConsoleBackend(ProtocolBackend):
    protocol_name = 'testconsole'

    def configure(self, *args, **kwargs):
        self.log.debug('configuring {0}'.format(self))
        self.log_traffic = kwargs.get('log_traffic', True)

        self.nick = kwargs.get('nick')
        self.rooms = ['ROOM', ]

        self.client = TestConsoleClient(backend=self)

    def connect(self, *args, **kwargs):
        self.log.debug('connecting {0}'.format(self))
        stdio.StandardIO(self.client)

    def handle_action(self, action):
        self.client.bot_process_action(action)
########NEW FILE########
__FILENAME__ = xmpp
import logging

from twisted.internet.task import LoopingCall
from twisted.words.protocols.jabber import jid

from wokkel import muc
from wokkel import xmppim
from wokkel.client import XMPPClient
from wokkel.subprotocols import XMPPHandler

from brutal.protocols.core import ProtocolBackend

XMPP_DEFAULT_PORT = 5222


class XmppBot():
    pass


class MucBot(muc.MUCClient):

    def __init__(self, rooms,  nick, backend):
        super(MucBot, self).__init__()

        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))
        self.backend = backend

        self.raw_rooms = rooms or []
        self.room_jids = []
        self.nick = nick

        for room in self.raw_rooms:
            password = None
            if type(room) is tuple:
                if len(room) > 1:
                    room, password = room
                else:
                    room = room[0]

            self.room_jids.append((jid.internJID(room), password))

    def connectionInitialized(self):
        super(MucBot, self).connectionInitialized()

        def joined_room(room):
            self.log.debug('joined room: {0!r}'.format(room.__dict__))
            if room.locked:
                self.log.error('room locked?')
                return self.configure(room.roomJID, {})

        def join_room(room_jid):
            d = self.join(room_jid, self.nick)
            d.addCallback(joined_room)
            #d.addCallback(lambda _: log.msg("joined room"))
            d.addErrback(self.log.error, 'join of {0!r} failed'.format(room_jid))

        for room in self.room_jids:
            join_room(room[0])

    def receivedGroupChat(self, room, user, message):
        self.log.debug('groupchat - user: {0}, room: {1!r}, msg: {2!r}'.format(user, room, message.body))
        if user is None:
            self.log.error('groupchat recieved from None?')
            return

        event_data = {'type': 'message', 'scope': 'public', 'room': room.roomJID.full(), 'meta': {'from': user.nick,
                                                                                                  'body': message.body}}

        if user.nick == self.nick:
            event_data['from_bot'] = True

        self.log.debug('event_data: {0!r}'.format(event_data))
        # log.msg('room: {0!r}, room.nick: {1!r}'.format(room, room.nick), logLevel=logging.DEBUG)
        # log.msg('roomJID: {0!s}, full: {1!r}, host: {2!r}, resource: {3!r}, user: {4!r}'.format(room.roomJID,
        #                                                                                         room.roomJID.full,
        #                                                                                         room.roomJID.host,
        #                                                                                         room.roomJID.resource,
        #                                                                                         room.roomJID.user),
        #         logLevel=logging.DEBUG)
        #self.groupChat(room.roomJID, 'wat')
        self._bot_process_event(event_data)

    #-- BOT STUFF
    def _bot_process_event(self, raw_event):
        self.backend.handle_event(raw_event)


class ClientKeepalive(XMPPHandler):
    DEFAULT_INTERVAL = 15.0
    lc = None

    def __init__(self, interval=None):
        super(ClientKeepalive, self).__init__()
        self.interval = interval or self.DEFAULT_INTERVAL

    def space(self):
        #self.xmlstream.send(' ')
        self.send(' ')

    def connectionInitialized(self):
        self.lc = LoopingCall(self.space)
        self.lc.start(self.interval, now=False)

    def connectionLost(self, reason):
        if self.lc:
            self.lc.stop()


class XmppBackend(ProtocolBackend):
    protocol_name = 'xmpp'

    def configure(self, *args, **kwargs):
        # user args
        self.nick = kwargs.get('nick')
        # TODO: remove, make this just the bot name...
        self.room_nick = kwargs.get('room_nick')
        if self.room_nick is None:
            self.room_nick = self.nick

        self.log_traffic = kwargs.get('log_traffic', False)
        #TODO: remove localhost default, fail.
        self.server = kwargs.get('server', 'localhost')
        self.port = kwargs.get('port', XMPP_DEFAULT_PORT)
        self.use_ssl = kwargs.get('use_ssl', True)
        self.keepalive_freq = kwargs.get('keepalive_freq')  # defaults to None
        if type(self.keepalive_freq) not in (None, float):
            try:
                self.keepalive_freq = float(self.keepalive_freq)
            except Exception as e:
                self.log.error('invalid keepalive passed in, {0!r}: {1!r}'.format(self.keepalive_freq, e))
                self.keepalive_freq = None

        #TODO: have this default to botname @ .
        self.jabber_id = kwargs.get('jabber_id', self.nick + '@' + self.server)
        #self.room_jabber_id =  # do we need this for servers that act wonky? maybe.
        self.password = kwargs.get('password')

        self.rooms = kwargs.get('rooms')

        # allow users to define custom handlers? not now.
        #self.subprotocol_handlers = kwargs.get()

        # internal
        self.bot_jid = jid.internJID(self.jabber_id)

        # probably want to override client?
        self.client = XMPPClient(self.bot_jid, self.password, host=self.server)

        if self.log_traffic is True:
            self.client.logTraffic = True

    # def connect_handlers(self):
    #     for subprotocol in self.subprotocol_handlers:
    #         instance = subprotocol()
    #         instance.setHandlerParent(self.client)

    def connect(self, *args, **kwargs):
        #TODO: try moving this below
        self.client.startService()

        # setup handlers
        self.muc_handler = MucBot(self.rooms, self.room_nick, backend=self)
        self.muc_handler.setHandlerParent(self.client)

        self.presence = xmppim.PresenceClientProtocol()
        self.presence.setHandlerParent(self.client)
        self.presence.available()

        self.keepalive = ClientKeepalive(interval=self.keepalive_freq)
        self.keepalive.setHandlerParent(self.client)

    def handle_action(self, action):
        #self.log.debug(': {0!r}'.format(action))

        if action.action_type == 'message':
            body = action.meta.get('body')
            if body:
                if action.destination_rooms:
                    for room in action.destination_rooms:
                        if action.scope == 'public':
                            # TODO: replace this with an actual room lookup of known rooms
                            room_jid = jid.internJID(room)
                            message = muc.GroupChat(recipient=room_jid, body=body)
                            self.client.send(message.toElement())
########NEW FILE########
__FILENAME__ = run
import logging

from twisted.python import log

from brutal.core.bot import BotManager


def main(config):
    """
    this is the primary run loop, should probably catch quits here?
    """
    # TODO: move logging to BotManager, make configurable
    logger = logging.basicConfig(level=logging.DEBUG,
                                 format='%(asctime)-21s %(levelname)s %(name)s (%(funcName)-s) %(process)d:%(thread)d - %(message)s',
                                 filename='lol.log')

    observer = log.PythonLoggingObserver()
    observer.start()

    bot_manager = BotManager(config)
    bot_manager.start()
########NEW FILE########
__FILENAME__ = hive
#!/usr/bin/env python
import os

from brutal.core.management import exec_overlord

if __name__ == "__main__":
    os.environ.setdefault("BRUTAL_CONFIG_MODULE", "{{ spawn_name }}.config")
    exec_overlord("{{ spawn_name }}.config")
########NEW FILE########
__FILENAME__ = config
INSTALLED_PLUGINS = (
    'brutal.plugins.basic',
    #'brutal.plugins.logging',
)

BOTS = [
    # bot 1
    {
        'nick': '{{ spawn_name }}',
        'connections': [
            # connect to multiple networks
            # {
            #     'protocol': 'xmpp',
            #     'log_traffic': True,
            #     'server': 'localhost', # server to connect to
            #     'port': 5222, # default
            #     'use_ssl': True,  # default for jabber
            #     'keepalive_freq': '15', # default
            #     'jabber_id':'bot@server', # depends on the server...
            #     'password': '', # jabber_id password
            #     'room_nick': 'bot', # nick to use in rooms, if not given, defaults to bot nick
            #     'rooms': ['room@conference.server', ('private_room@conference.server', 'pass')]
            # },
            # {
            #     'protocol': 'irc',
            #     'server': 'irc.localhost',
            #     'port': 6667,
            #     'use_ssl': False, # default or irc
            #     'password': '',
            #     'channels': ['room', ('private_room', 'pass')]
            # }
        ],
        'enabled_plugins': {
            #'plugin_one': {},
        },  # if this isn't set, load all
        'plugin_settings': {}
    },
    # bot 2
    # {
    #     'nick': 'tester',
    #     'connections': [
    #         {
    #             'protocol': 'irc',
    #             'server': 'irc.localhost',
    #             'port': 6667,
    #             'use_ssl': False, # default or irc
    #             'password': '',
    #             'channels': ['room', ('private_room', 'pass')]
    #         }
    #     ],
    #     'plugin_settings': {}
    # }
]
########NEW FILE########
__FILENAME__ = example
"""
Examples of brutal plugins. Primarily used for testing.
"""

import time
from brutal.core.plugin import BotPlugin, cmd, event, match, threaded


@cmd
def ping(event):
    return 'pong, got {0!r}'.format(event)


@cmd
def testargs(event):
    return 'you passed in args: {0!r}'.format(event.args)


#@event(thread=True)
def sleepevent(event):
    time.sleep(7)
    return 'SOOOOOO sleepy'


@cmd(thread=True)
def sleep(event):
    time.sleep(5)
    return 'im sleepy...'


#@event
def test_event_parser(event):
    return 'EVENT!!! {0!r}'.format(event)

# @match(regex=r'^hi$')
# def matcher(event):
#     return 'Hello to you!'


class TestPlugin(BotPlugin):
    def setup(self, *args, **kwargs):
        self.log.debug('SETUP CALLED')
        self.count = 0
        self.loop_task(5, self.test_loop, now=False)
        self.delay_task(10, self.future_task)

    def future_task(self):
        self.log.info('testing future task')
        return 'future!'

    @threaded
    def test_loop(self):
        self.log.info('testing looping task')
        return 'loop!'

    def say_hi(self, event=None):
        self.msg('from say_hi: {0!r}'.format(event), event=event)
        return 'hi'

    @threaded
    def say_delayed_hi(self, event=None):
        self.msg('from say_hi_threaded, sleeping for 5: {0!r}'.format(event), event=event)
        time.sleep(5)
        return 'even more delayed hi'

    @cmd
    def runlater(self, event):
        self.delay_task(5, self.say_hi, event=event)
        self.delay_task(5, self.say_delayed_hi, event=event)
        return 'will say hi in 5 seconds'

    @cmd
    def count(self, event):
        self.count += 1
        return 'count {1!r} from class! got {0!r}'.format(event, self.count)

    @cmd(thread=True)
    def inlinemsg(self, event):
        self.msg('sleeping for 5 seconds!', event=event)
        time.sleep(5)
        return 'done sleeping!'

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# brutal documentation build configuration file, created by
# sphinx-quickstart on Mon Apr 15 20:52:19 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

sys.path.insert(0, os.path.abspath('..'))
from brutal import __version__

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'brutal'
copyright = u'2013 - Corey Bertram'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = __version__
# The full version, including alpha/beta/rc tags.
release = version

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
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

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
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

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
html_show_sourcelink = False

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
htmlhelp_basename = 'brutaldoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'brutal.tex', u'brutal Documentation',
   u'Corey Bertram', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'brutal', u'brutal Documentation',
     [u'Corey Bertram'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'brutal', u'brutal Documentation',
   u'Corey Bertram', 'brutal', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
