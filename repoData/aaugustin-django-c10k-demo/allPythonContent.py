__FILENAME__ = settings
# Django settings for c10kdemo project.

import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

DEBUG = True

INSTALLED_APPS = (
    'c10ktools',
    'gameoflife',
    'django.contrib.staticfiles',
)

LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
        },
    },
}

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
)

ROOT_URLCONF = 'c10kdemo.urls'

SECRET_KEY = os.environ.get('SECRET_KEY', 'whatever')

STATIC_URL = '/static/'

TIME_ZONE = 'Europe/Paris'

WSGI_APPLICATION = 'c10kdemo.wsgi.application'

del os

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import include, patterns, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


urlpatterns = patterns('',
    url(r'^test/', include('c10ktools.urls')),
    url(r'', include('gameoflife.urls')),

)

########NEW FILE########
__FILENAME__ = wsgi
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "c10kdemo.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

########NEW FILE########
__FILENAME__ = websockets
import asyncio
import functools

import aiohttp.parsers
import websockets
from websockets import handshake

from django.http import HttpResponse, HttpResponseServerError


def websocket(handler):
    """Decorator for WebSocket handlers."""

    @functools.wraps(handler)
    def wrapper(request, *args, **kwargs):
        environ = request.META
        try:
            assert environ['wsgi.async']
            stream = environ['async.reader']
            transport = environ['async.writer']
            assert isinstance(stream, aiohttp.parsers.StreamParser)
            assert isinstance(transport, asyncio.Transport)
            # All asyncio transports appear to have a _protocol attribute...
            http_proto = transport._protocol
            # ... I still feel guilty about this.
            assert http_proto.stream is stream
            assert http_proto.transport is transport
        except (AssertionError, KeyError) as e:             # pragma: no cover
            return HttpResponseServerError("Unsupported WSGI server: %s." % e)

        @asyncio.coroutine
        def run_ws_handler(ws):
            yield from handler(ws, *args, **kwargs)
            yield from ws.close()

        def switch_protocols():
            ws_proto = websockets.WebSocketCommonProtocol()
            # Disconnect transport from http_proto and connect it to ws_proto.
            http_proto.transport = DummyTransport()
            transport._protocol = ws_proto
            ws_proto.connection_made(transport)
            # Run the WebSocket handler in an asyncio Task.
            asyncio.Task(run_ws_handler(ws_proto))

        return WebSocketResponse(environ, switch_protocols)

    return wrapper


class WebSocketResponse(HttpResponse):
    """Upgrade from a WSGI connection with the WebSocket handshake."""

    status_code = 101

    def __init__(self, environ, switch_protocols):
        super().__init__()

        http_1_1 = environ['SERVER_PROTOCOL'] == 'HTTP/1.1'
        get_header = lambda k: environ['HTTP_' + k.upper().replace('-', '_')]
        key = handshake.check_request(get_header)

        if not http_1_1 or key is None:
            self.status_code = 400
            self.content = "Invalid WebSocket handshake.\n"
        else:
            self._headers = {}                  # Reset headers (private API!)
            set_header = self.__setitem__
            handshake.build_response(set_header, key)
            self.close = switch_protocols


class DummyTransport(asyncio.Transport):
    """Transport that doesn't do anything, but can be closed silently."""

    def can_write_eof(self):
        return False

    def close(self):
        pass

########NEW FILE########
__FILENAME__ = testecho
import random

import asyncio
import websockets

from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):

    CLIENTS = 10000
    DELAY = 60
    ECHO_URL = 'ws://localhost:8000/test/ws/'

    def handle_noargs(self, **options):
        self.count = 0
        connections = [self.test_echo() for _ in range(self.CLIENTS)]
        asyncio.get_event_loop().run_until_complete(asyncio.wait(connections))
        assert self.count == 0

    @asyncio.coroutine
    def test_echo(self):

        # Distribute the connections a bit
        yield from asyncio.sleep(2 * self.DELAY * random.random())
        ws = yield from websockets.connect(self.ECHO_URL)

        self.count += 1
        if self.count % (self.CLIENTS * 3 // self.DELAY) == 0:
            self.stdout.write("> {:5} connections\n".format(self.count))
        if self.count == self.CLIENTS:
            self.stdout.write("\n{} clients are connected!\n\n".format(self.count))

        messages = []
        messages.append((yield from ws.recv()))
        yield from asyncio.sleep(self.DELAY)
        yield from ws.send('Spam?')
        messages.append((yield from ws.recv()))
        yield from asyncio.sleep(self.DELAY)
        yield from ws.send('Eggs!')
        messages.append((yield from ws.recv()))
        yield from asyncio.sleep(self.DELAY)
        yield from ws.send('Python.')
        messages.append((yield from ws.recv()))
        messages.append((yield from ws.recv()))
        assert messages == [
            "Hello!",
            "1. Spam?",
            "2. Eggs!",
            "3. Python.",
            "Goodbye!",
        ]

        yield from ws.close()

        self.count -= 1
        if self.count % (self.CLIENTS * 3 // self.DELAY) == 0:
            self.stdout.write("< {:5} connections\n".format(self.count))

########NEW FILE########
__FILENAME__ = models
from . import monkey

monkey.patch()

########NEW FILE########
__FILENAME__ = monkey
import asyncio

from aiohttp.wsgi import WSGIServerHttpProtocol


def run(addr, port, wsgi_handler, loop=None, stop=None, **options):
    """
    Alternate version of django.core.servers.basehttp.run running on asyncio.
    """
    if loop is None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    # The code that reads environ['wsgi.input'] is deep inside Django and hard
    # to make asynchronous. Pre-loading the payload is the simplest option.
    protocol_factory = lambda: WSGIServerHttpProtocol(
            wsgi_handler, readpayload=True)
    server = loop.run_until_complete(
            loop.create_server(protocol_factory, addr, port))
    try:
        if stop is None:
            loop.run_forever()
        else:
            loop.run_until_complete(stop)
    finally:
        server.close()
        loop.run_until_complete(server.wait_closed())


def patch():
    from django.core.management.commands import runserver
    runserver.run = run

########NEW FILE########
__FILENAME__ = test
import threading

import asyncio

from selenium.webdriver import Firefox

from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.servers.basehttp import get_internal_wsgi_application
from django.test import TestCase

from .monkey import run


# Since it's hard to subclass LiveServerTestCase to run on top of asyncio, and
# since we don't need to share a database connection between the live server
# and the tests, we use a simple ServerTestCase instead of LiveServerTestCase.

class ServerTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        super(ServerTestCase, cls).setUpClass()
        cls.start_server('localhost', 8999)

    @classmethod
    def tearDownClass(cls):
        cls.stop_server()
        super(ServerTestCase, cls).tearDownClass()

    @classmethod
    def start_server(cls, host, port):
        cls.live_server_url = 'http://{}:{}'.format(host, port)
        cls.server_thread = threading.Thread(target=cls.run_server,
                                             args=(host, port))
        cls.server_thread.start()

    @classmethod
    def run_server(cls, host, port):
        handler = StaticFilesHandler(get_internal_wsgi_application())
        # Save the event loop for the thread in a class variable
        # so we can unblock it when the tests are finished.
        cls.server_thread_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.server_thread_loop)
        cls.server_stop = asyncio.Future()
        run(host, port, handler, cls.server_thread_loop, cls.server_stop)
        cls.server_thread_loop.close()

    @classmethod
    def stop_server(cls):
        cls.server_thread_loop.call_soon_threadsafe(cls.server_stop.set_result, None)
        cls.server_thread.join()


class SeleniumTestCase(ServerTestCase):

    @classmethod
    def setUpClass(cls):
        super(SeleniumTestCase, cls).setUpClass()
        cls.selenium = Firefox()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(SeleniumTestCase, cls).tearDownClass()

########NEW FILE########
__FILENAME__ = test_commands
from io import StringIO

from django.core.management import call_command
from django.core.urlresolvers import reverse

from .management.commands.testecho import Command as TestEchoCommand
from .test import ServerTestCase


class CommandsTests(ServerTestCase):

    def test_testecho(self):
        # Tweak a few parameters to make the test run faster.
        TestEchoCommand.CLIENTS = 12
        TestEchoCommand.DELAY = 0.1
        TestEchoCommand.ECHO_URL = (self.live_server_url.replace('http', 'ws')
                                    + reverse('c10ktools.views.echo_ws'))

        call_command('testecho', stdout=StringIO())

########NEW FILE########
__FILENAME__ = test_views
from django.core.urlresolvers import reverse

from .test import SeleniumTestCase


class ViewsTests(SeleniumTestCase):

    def test_basic(self):
        self.selenium.get(self.live_server_url + reverse('c10ktools.views.basic'))

        field = self.selenium.find_element_by_xpath('//form[@method="GET"]/input[@type="text"]')
        field.send_keys('spam')
        field.submit()

        result = self.selenium.find_element_by_xpath('//pre[1]')
        self.assertEqual(result.text, "<QueryDict: {'text': ['spam']}>")

        field = self.selenium.find_element_by_xpath('//form[@method="POST"]/input[@type="text"]')
        field.send_keys('eggs')
        field.submit()

        result = self.selenium.find_element_by_xpath('//pre[2]')
        self.assertEqual(result.text, "<QueryDict: {'text': ['eggs']}>")

    def test_echo(self):
        self.selenium.get(self.live_server_url + reverse('c10ktools.views.echo'))

        def get_messages():
            messages = self.selenium.find_elements_by_xpath('//ul[@id="messages"]/li')
            return [msg.text for msg in messages]

        expected_messages = [
            'Connection open.', 'Hello!',
            '1. Spam', '2. Eggs', '3. Café',
            'Goodbye!', 'Connection closed.',
        ]

        def expect_messages(count):
            self.assertEqual(get_messages(), expected_messages[:count])

        field = self.selenium.find_element_by_id('text')
        expect_messages(2)

        field.send_keys("Spam")
        field.submit()
        expect_messages(3)

        field.send_keys("Eggs")
        field.submit()
        expect_messages(4)

        field.send_keys("Café")
        field.submit()
        expect_messages(7)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url


urlpatterns = patterns('c10ktools.views',
    url(r'^$', 'echo'),
    url(r'^ws/$', 'echo_ws'),
    url(r'^wsgi/$', 'basic'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render

from c10ktools.http import websocket


def basic(request):
    return render(request, 'c10ktools/basic.html', {'request': request})


def echo(request):
    return render(request, 'c10ktools/echo.html')


@websocket
def echo_ws(ws):
    yield from ws.send('Hello!')
    for i in range(3):
        message = yield from ws.recv()
        yield from ws.send('{}. {}'.format(i + 1, message))
    yield from ws.send('Goodbye!')

########NEW FILE########
__FILENAME__ = client
import random

import asyncio
import websockets

BASE_URL = 'ws://localhost:8000'

@asyncio.coroutine
def reset(size):
    ws = yield from websockets.connect(BASE_URL + '/reset/')
    yield from ws.send(str(size))
    yield from ws.worker


@asyncio.coroutine
def run(row, col, size, wrap, speed, steps=None, state=None):

    if state is None:
        state = random.choice((True, False, False, False))

    neighbors = get_neighbors(row, col, size, wrap)
    neighbors = {n: i for i, n in enumerate(neighbors)}
    n = len(neighbors)

    # Throttle at 100 connections / second on average
    yield from asyncio.sleep(size * size / 100 * random.random())
    ws = yield from websockets.connect(BASE_URL + '/worker/')

    # Wait until all clients are connected.
    msg = yield from ws.recv()
    if msg != 'sub':
        raise Exception("Unexpected message: {}".format(msg))

    # Subscribe to updates sent by neighbors.
    for neighbor in neighbors:
        yield from ws.send('{} {}'.format(*neighbor))
    yield from ws.send('sub')

    # Wait until all clients are subscribed.
    msg = yield from ws.recv()
    if msg != 'run':
        raise Exception("Unexpected message: {}".format(msg))

    yield from ws.send('{} {} {} {}'.format(0, row, col, int(state)))

    # This is the step for which we last sent our state, and for which we're
    # collecting the states of our neighbors.
    step = 0
    # Once we know all our neighbors' states at step N - 1, we compute and
    # send our state at step N. At this point, our neighbors can send their
    # states at steps N and N + 1, but not N + 2, since that requires our
    # state at step N + 1. We only need to keep track of two sets of states.
    states = [[None] * n, [None] * n]

    # Gather state updates from neighbors and send our own state updates.
    while (steps is None or step < steps):
        msg = yield from ws.recv()
        if msg is None:
            break
        _step, _row, _col, _state = (int(x) for x in msg.split())
        target = _step % 2
        states[target][neighbors[(_row, _col)]] = bool(_state)
        # Compute next state
        if None not in states[target]:
            assert _step == step
            step += 1
            alive = states[target].count(True)
            state = alive == 3 or (state and alive == 2)
            states[target] = [None] * n
            yield from ws.send('{} {} {} {}'.format(step, row, col, int(state)))
            # Throttle, speed is a number of steps per second
            yield from asyncio.sleep(1 / speed)

    yield from ws.close()


def get_neighbors(row, col, size, wrap):
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            if i == j == 0:
                continue
            if 0 <= row + i < size and 0 <= col + j < size:
                yield row + i, col + j
            elif wrap:
                yield (row + i) % size, (col + j) % size

########NEW FILE########
__FILENAME__ = gameoflife
from optparse import make_option

import asyncio

from django.core.management.base import CommandError, NoArgsCommand

from ...client import reset, run


class Command(NoArgsCommand):

    option_list = NoArgsCommand.option_list + (
        make_option('-C', '--no-center', default=True,
                    action='store_false', dest='center',
                    help='Do not center the pattern in the grid.'),
        make_option('-p', '--pattern',
                    help='The initial state of the grid.'),
        make_option('-s', '--size', type='int', default=32,
                    help='The size of the grid.'),
        make_option('-l', '--speed', type='float', default=1.0,
                    help='The maximum number of steps per second.'),
        make_option('-n', '--steps', type='int', default=None,
                    help='The number of steps.'),
        make_option('-W', '--no-wrap', default=True,
                    action='store_false', dest='wrap',
                    help='Do not wrap around the grid.'),
    )
    help = 'Runs one worker for each cell of the Game of Life grid.'

    def handle_noargs(self, **options):
        center = options['center']
        pattern = options['pattern']
        size = options['size']
        speed = options['speed']
        steps = options['steps']
        wrap = options['wrap']

        if pattern is None:
            states = [[None] * size] * size
        else:
            states = self.parse_pattern(pattern, size, center)

        clients = [run(row, col, size, wrap, speed, steps, states[row][col])
                   for row in range(size) for col in range(size)]

        try:
            asyncio.get_event_loop().run_until_complete(reset(size))
            asyncio.get_event_loop().run_until_complete(asyncio.wait(clients))
        except KeyboardInterrupt:
            pass

    def parse_pattern(self, pattern, size, center):
        with open(pattern) as handle:
            rows = [row.rstrip() for row in handle]

        # Check that the pattern fits in the grid
        height = len(rows)
        width = max(len(row) for row in rows)
        if height > size:
            raise CommandError("Too many rows in pattern. Increase size?")
        if width > size:
            raise CommandError("Too many columns in pattern. Increase size?")

        # Center pattern vertically and horizontally
        if center:
            top = (size - height) // 2
            rows = [''] * top + rows
            left = (size - width) // 2
            prefix = ' ' * left
            rows = [prefix + row for row in rows]

        # Add padding to match the grid size
        rows += [''] * (size - len(rows))
        rows = [row.ljust(size) for row in rows]

        # Convert to booleans
        return [[x not in '. ' for x in row] for row in rows]

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = test_integration
import asyncio

from django.core.management import call_command
from django.core.urlresolvers import reverse

from c10ktools.test import SeleniumTestCase

from . import client


class IntegrationTests(SeleniumTestCase):

    @classmethod
    def setUpClass(cls):
        super(IntegrationTests, cls).setUpClass()
        client.BASE_URL = cls.live_server_url.replace('http', 'ws')

    def test_gameoflife(self):
        # Reduce size before opening the browser so it gets the right size.
        asyncio.get_event_loop().run_until_complete(client.reset(5))

        # This is just for the eye candy.
        self.selenium.get(self.live_server_url + reverse('gameoflife.views.watch'))

        # Run the game, with and without a pattern.
        call_command('gameoflife', size=5, speed=100, steps=5)

        call_command('gameoflife', size=5, speed=100, steps=5,
                                   pattern='gameoflife/patterns/blinker')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url


urlpatterns = patterns('gameoflife.views',
    url(r'^$', 'watch'),
    url(r'^watcher/$', 'watcher'),
    url(r'^reset/$', 'reset'),
    url(r'^worker/$', 'worker'),
)

########NEW FILE########
__FILENAME__ = views
import itertools

import asyncio

from django.conf import settings
from django.shortcuts import render

from c10ktools.http import websocket

# Server-wide state used by the watchers
global_subscribers = set()
size = 32

def watch(request):
    context = {
        'size': size,
        'sizelist': list(range(size)),
    }
    return render(request, 'gameoflife/watch.html', context)


@websocket
def watcher(ws):
    debug("Watcher connected")
    global_subscribers.add(ws)
    # Block until the client goes away
    yield from ws.recv()
    global_subscribers.remove(ws)
    debug("Watcher disconnected")


@websocket
# Server-wide state
def reset(ws):
    global size, expected, connected, subscribed, sub_latch, run_latch, subscribers
    size = int((yield from ws.recv()))
    expected = size * size
    connected = 0
    subscribed = 0
    sub_latch = asyncio.Future()
    run_latch = asyncio.Future()
    subscribers = [[set() for col in range(size)] for row in range(size)]


@websocket
def worker(ws):
    global connected, subscribed

    # Wait until all clients are connected.
    connected += 1
    if connected == expected:
        debug("{:5} workers connected".format(connected))
        debug("Telling workers to subscribe")
        sub_latch.set_result(None)
    elif connected % 100 == 0:
        debug("{:5} workers connected".format(connected))
    yield from sub_latch
    yield from ws.send('sub')

    # Subscribe to updates sent by neighbors.
    subscriptions = set()
    while True:
        msg = yield from ws.recv()
        if msg == 'sub':
            break
        row, col = msg.split()
        row, col = int(row), int(col)
        subscriptions.add((row, col))
        subscribers[row][col].add(ws)

    # Wait until all clients are subscribed.
    subscribed += 1
    if subscribed == expected:
        debug("{:5} workers subscribed".format(subscribed))
        debug("Telling workers to run")
        run_latch.set_result(None)
    elif subscribed % 100 == 0:
        debug("{:5} workers subscribed".format(subscribed))
    yield from run_latch
    yield from ws.send('run')

    # Relay state updates to subscribers.
    while True:
        msg = yield from ws.recv()
        if msg is None:
            break
        step, row, col, state = msg.split()
        for subscriber in itertools.chain(
                subscribers[int(row)][int(col)], global_subscribers):
            if subscriber.open:
                yield from subscriber.send(msg)

    # Unsubscribe from updates.
    for row, col in subscriptions:
        subscribers[row][col].remove(ws)


def debug(message):
    if settings.DEBUG:
        print(message)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "c10kdemo.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
