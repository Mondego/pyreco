__FILENAME__ = decorators
from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import decorator_from_middleware
from django_websocket.middleware import WebSocketMiddleware

__all__ = ('accept_websocket', 'require_websocket')


WEBSOCKET_MIDDLEWARE_INSTALLED = 'django_websocket.middleware.WebSocketMiddleware' in settings.MIDDLEWARE_CLASSES


def _setup_websocket(func):
    from functools import wraps
    @wraps(func)
    def new_func(request, *args, **kwargs):
        response = func(request, *args, **kwargs)
        if response is None and request.is_websocket():
            return HttpResponse()
        return response
    if not WEBSOCKET_MIDDLEWARE_INSTALLED:
        decorator = decorator_from_middleware(WebSocketMiddleware)
        new_func = decorator(new_func)
    return new_func


def accept_websocket(func):
    func.accept_websocket = True
    func.require_websocket = getattr(func, 'require_websocket', False)
    func = _setup_websocket(func)
    return func


def require_websocket(func):
    func.accept_websocket = True
    func.require_websocket = True
    func = _setup_websocket(func)
    return func

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings
from django.http import HttpResponseBadRequest
from django_websocket.websocket import setup_websocket, MalformedWebSocket


WEBSOCKET_ACCEPT_ALL = getattr(settings, 'WEBSOCKET_ACCEPT_ALL', False)


class WebSocketMiddleware(object):
    def process_request(self, request):
        try:
            request.websocket = setup_websocket(request)
        except MalformedWebSocket, e:
            request.websocket = None
            request.is_websocket = lambda: False
            return HttpResponseBadRequest()
        if request.websocket is None:
            request.is_websocket = lambda: False
        else:
            request.is_websocket = lambda: True

    def process_view(self, request, view_func, view_args, view_kwargs):
        # open websocket if its an accepted request
        if request.is_websocket():
            # deny websocket request if view can't handle websocket
            if not WEBSOCKET_ACCEPT_ALL and \
                not getattr(view_func, 'accept_websocket', False):
                return HttpResponseBadRequest()
            # everything is fine .. so prepare connection by sending handshake
            request.websocket.send_handshake()
        elif getattr(view_func, 'require_websocket', False):
            # websocket was required but not provided
            return HttpResponseBadRequest()

    def process_response(self, request, response):
        if request.is_websocket() and request.websocket._handshake_sent:
            request.websocket._send_closing_frame(True)
        return response

########NEW FILE########
__FILENAME__ = websocket
import collections
import select
import string
import struct
try:
    from hashlib import md5
except ImportError: #pragma NO COVER
    from md5 import md5
from errno import EINTR
from socket import error as SocketError


class MalformedWebSocket(ValueError):
    pass


def _extract_number(value):
    """
    Utility function which, given a string like 'g98sd  5[]221@1', will
    return 4926105. Used to parse the Sec-WebSocket-Key headers.

    In other words, it extracts digits from a string and returns the number
    due to the number of spaces.
    """
    out = ""
    spaces = 0
    for char in value:
        if char in string.digits:
            out += char
        elif char == " ":
            spaces += 1
    return int(out) / spaces


def setup_websocket(request):
    if request.META.get('HTTP_CONNECTION', None) == 'Upgrade' and \
        request.META.get('HTTP_UPGRADE', None) == 'WebSocket':

        # See if they sent the new-format headers
        if 'HTTP_SEC_WEBSOCKET_KEY1' in request.META:
            protocol_version = 76
            if 'HTTP_SEC_WEBSOCKET_KEY2' not in request.META:
                raise MalformedWebSocket()
        else:
            protocol_version = 75

        # If it's new-version, we need to work out our challenge response
        if protocol_version == 76:
            key1 = _extract_number(request.META['HTTP_SEC_WEBSOCKET_KEY1'])
            key2 = _extract_number(request.META['HTTP_SEC_WEBSOCKET_KEY2'])
            # There's no content-length header in the request, but it has 8
            # bytes of data.
            key3 = request.META['wsgi.input'].read(8)
            key = struct.pack(">II", key1, key2) + key3
            handshake_response = md5(key).digest()

        location = 'ws://%s%s' % (request.get_host(), request.path)
        qs = request.META.get('QUERY_STRING')
        if qs:
            location += '?' + qs
        if protocol_version == 75:
            handshake_reply = (
                "HTTP/1.1 101 Web Socket Protocol Handshake\r\n"
                "Upgrade: WebSocket\r\n"
                "Connection: Upgrade\r\n"
                "WebSocket-Origin: %s\r\n"
                "WebSocket-Location: %s\r\n\r\n" % (
                    request.META.get('HTTP_ORIGIN'),
                    location))
        elif protocol_version == 76:
            handshake_reply = (
                "HTTP/1.1 101 Web Socket Protocol Handshake\r\n"
                "Upgrade: WebSocket\r\n"
                "Connection: Upgrade\r\n"
                "Sec-WebSocket-Origin: %s\r\n"
                "Sec-WebSocket-Protocol: %s\r\n"
                "Sec-WebSocket-Location: %s\r\n" % (
                    request.META.get('HTTP_ORIGIN'),
                    request.META.get('HTTP_SEC_WEBSOCKET_PROTOCOL', 'default'),
                    location))
            handshake_reply = str(handshake_reply)
            handshake_reply = '%s\r\n%s' % (handshake_reply, handshake_response)

        else:
            raise MalformedWebSocket("Unknown WebSocket protocol version.")
        socket = request.META['wsgi.input']._sock.dup()
        return WebSocket(
            socket,
            protocol=request.META.get('HTTP_WEBSOCKET_PROTOCOL'),
            version=protocol_version,
            handshake_reply=handshake_reply,
        )
    return None


class WebSocket(object):
    """
    A websocket object that handles the details of
    serialization/deserialization to the socket.

    The primary way to interact with a :class:`WebSocket` object is to
    call :meth:`send` and :meth:`wait` in order to pass messages back
    and forth with the browser.
    """
    _socket_recv_bytes = 4096


    def __init__(self, socket, protocol, version=76,
        handshake_reply=None, handshake_sent=None):
        '''
        Arguments:

        - ``socket``: An open socket that should be used for WebSocket
          communciation.
        - ``protocol``: not used yet.
        - ``version``: The WebSocket spec version to follow (default is 76)
        - ``handshake_reply``: Handshake message that should be sent to the
          client when ``send_handshake()`` is called.
        - ``handshake_sent``: Whether the handshake is already sent or not.
          Set to ``False`` to prevent ``send_handshake()`` to do anything.
        '''
        self.socket = socket
        self.protocol = protocol
        self.version = version
        self.closed = False
        self.handshake_reply = handshake_reply
        if handshake_sent is None:
            self._handshake_sent = not bool(handshake_reply)
        else:
            self._handshake_sent = handshake_sent
        self._buffer = ""
        self._message_queue = collections.deque()

    def send_handshake(self):
        self.socket.sendall(self.handshake_reply)
        self._handshake_sent = True

    @classmethod
    def _pack_message(cls, message):
        """Pack the message inside ``00`` and ``FF``

        As per the dataframing section (5.3) for the websocket spec
        """
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        elif not isinstance(message, str):
            message = str(message)
        packed = "\x00%s\xFF" % message
        return packed

    def _parse_message_queue(self):
        """ Parses for messages in the buffer *buf*.  It is assumed that
        the buffer contains the start character for a message, but that it
        may contain only part of the rest of the message.

        Returns an array of messages, and the buffer remainder that
        didn't contain any full messages."""
        msgs = []
        end_idx = 0
        buf = self._buffer
        while buf:
            frame_type = ord(buf[0])
            if frame_type == 0:
                # Normal message.
                end_idx = buf.find("\xFF")
                if end_idx == -1: #pragma NO COVER
                    break
                msgs.append(buf[1:end_idx].decode('utf-8', 'replace'))
                buf = buf[end_idx+1:]
            elif frame_type == 255:
                # Closing handshake.
                assert ord(buf[1]) == 0, "Unexpected closing handshake: %r" % buf
                self.closed = True
                break
            else:
                raise ValueError("Don't understand how to parse this type of message: %r" % buf)
        self._buffer = buf
        return msgs

    def send(self, message):
        '''
        Send a message to the client. *message* should be convertable to a
        string; unicode objects should be encodable as utf-8.
        '''
        packed = self._pack_message(message)
        self.socket.sendall(packed)

    def _socket_recv(self):
        '''
        Gets new data from the socket and try to parse new messages.
        '''
        delta = self.socket.recv(self._socket_recv_bytes)
        if delta == '':
            return False
        self._buffer += delta
        msgs = self._parse_message_queue()
        self._message_queue.extend(msgs)
        return True

    def _socket_can_recv(self, timeout=0.0):
        '''
        Return ``True`` if new data can be read from the socket.
        '''
        r, w, e = [self.socket], [], []
        try:
            r, w, e = select.select(r, w, e, timeout)
        except select.error, err:
            if err.args[0] == EINTR:
                return False
            raise
        return self.socket in r

    def _get_new_messages(self):
        # read as long from socket as we need to get a new message.
        while self._socket_can_recv():
            self._socket_recv()
            if self._message_queue:
                return

    def count_messages(self):
        '''
        Returns the number of queued messages.
        '''
        self._get_new_messages()
        return len(self._message_queue)

    def has_messages(self):
        '''
        Returns ``True`` if new messages from the socket are available, else
        ``False``.
        '''
        if self._message_queue:
            return True
        self._get_new_messages()
        if self._message_queue:
            return True
        return False

    def read(self, fallback=None):
        '''
        Return new message or ``fallback`` if no message is available.
        '''
        if self.has_messages():
            return self._message_queue.popleft()
        return fallback

    def wait(self):
        '''
        Waits for and deserializes messages. Returns a single message; the
        oldest not yet processed.
        '''
        while not self._message_queue:
            # Websocket might be closed already.
            if self.closed:
                return None
            # no parsed messages, must mean buf needs more data
            new_data = self._socket_recv()
            if not new_data:
                return None
        return self._message_queue.popleft()

    def __iter__(self):
        '''
        Use ``WebSocket`` as iterator. Iteration only stops when the websocket
        gets closed by the client.
        '''
        while True:
            message = self.wait()
            if message is None:
                return
            yield message

    def _send_closing_frame(self, ignore_send_errors=False):
        '''
        Sends the closing frame to the client, if required.
        '''
        if self.version == 76 and not self.closed:
            try:
                self.socket.sendall("\xff\x00")
            except SocketError:
                # Sometimes, like when the remote side cuts off the connection,
                # we don't care about this.
                if not ignore_send_errors:
                    raise
            self.closed = True

    def close(self):
        '''
        Forcibly close the websocket.
        '''
        self._send_closing_frame()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

sys.path.insert(0,
os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = runtests
#This file mainly exists to allow python setup.py test to work.
import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'django_websocket_tests.settings'
test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, test_dir)

import django
from django.test.utils import get_runner
from django.conf import settings

def runtests():
    TestRunner = get_runner(settings)
    if django.VERSION[:2] > (1,1):
        test_runner = TestRunner(verbosity=1, interactive=True)
        failures = test_runner.run_tests(settings.TEST_APPS)
    else:
        # test runner is not class based, this means we use django 1.1.x or
        # earlier.
        failures = TestRunner(settings.TEST_APPS, verbosity=1, interactive=True)
    sys.exit(bool(failures))

if __name__ == '__main__':
    runtests()

########NEW FILE########
__FILENAME__ = settings
DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'db.sqlite',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

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
)

ROOT_URLCONF = 'django_websocket_tests.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django_websocket_tests',
    'django_websocket',

    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
)

TEST_APPS = (
    'django_websocket_tests',
)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from mock import Mock
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory
from django_websocket.decorators import accept_websocket, require_websocket
from django_websocket.websocket import WebSocket


class WebSocketTests(TestCase):
    def setUp(self):
        self.socket = Mock()
        self.protocol = '1'

    def test_send_handshake(self):
        handshake = 'Hi!'
        ws = WebSocket(self.socket, self.protocol, handshake_reply=handshake)
        self.assertEquals(ws._handshake_sent, False)
        ws.send_handshake()
        self.assertEquals(self.socket.sendall.call_count, 1)
        self.assertEquals(self.socket.sendall.call_args, ((handshake,), {}))

    def test_message_sending(self):
        ws = WebSocket(self.socket, self.protocol)
        ws.send('foobar')
        self.assertEquals(self.socket.sendall.call_count, 1)
        self.assertEquals(self.socket.sendall.call_args, (('\x00foobar\xFF',), {}))
        message = self.socket.sendall.call_args[0][0]
        self.assertEquals(type(message), str)

        ws.send(u'Küss die Hand schöne Frau')
        self.assertEquals(self.socket.sendall.call_count, 2)
        self.assertEquals(self.socket.sendall.call_args, (('\x00K\xc3\xbcss die Hand sch\xc3\xb6ne Frau\xFF',), {}))
        message = self.socket.sendall.call_args[0][0]
        self.assertEquals(type(message), str)

    def test_message_receiving(self):
        ws = WebSocket(self.socket, self.protocol)
        self.assertFalse(ws.closed)

        results = [
            '\x00spam & eggs\xFF',
            '\x00K\xc3\xbcss die Hand sch\xc3\xb6ne Frau\xFF',
            '\xFF\x00'][::-1]
        def return_results(*args, **kwargs):
            return results.pop()
        self.socket.recv.side_effect = return_results
        self.assertEquals(ws.wait(), u'spam & eggs')
        self.assertEquals(ws.wait(), u'Küss die Hand schöne Frau')

    def test_closing_socket_by_client(self):
        self.socket.recv.return_value = '\xFF\x00'

        ws = WebSocket(self.socket, self.protocol)
        self.assertFalse(ws.closed)
        self.assertEquals(ws.wait(), None)
        self.assertTrue(ws.closed)

        self.assertEquals(self.socket.shutdown.call_count, 0)
        self.assertEquals(self.socket.close.call_count, 0)

    def test_closing_socket_by_server(self):
        ws = WebSocket(self.socket, self.protocol)
        self.assertFalse(ws.closed)
        ws.close()
        self.assertEquals(self.socket.sendall.call_count, 1)
        self.assertEquals(self.socket.sendall.call_args, (('\xFF\x00',), {}))
        # don't close system socket! django still needs it.
        self.assertEquals(self.socket.shutdown.call_count, 0)
        self.assertEquals(self.socket.close.call_count, 0)
        self.assertTrue(ws.closed)

        # closing again will not send another close message
        ws.close()
        self.assertTrue(ws.closed)
        self.assertEquals(self.socket.sendall.call_count, 1)
        self.assertEquals(self.socket.shutdown.call_count, 0)
        self.assertEquals(self.socket.close.call_count, 0)

    def test_iterator_behaviour(self):
        results = [
            '\x00spam & eggs\xFF',
            '\x00K\xc3\xbcss die Hand sch\xc3\xb6ne Frau\xFF',
            '\xFF\x00'][::-1]
        expected_results = [
            u'spam & eggs',
            u'Küss die Hand schöne Frau']
        def return_results(*args, **kwargs):
            return results.pop()
        self.socket.recv.side_effect = return_results

        ws = WebSocket(self.socket, self.protocol)
        for i, message in enumerate(ws):
            self.assertEquals(message, expected_results[i])


@accept_websocket
def add_one(request):
    if request.is_websocket():
        for message in request.websocket:
            request.websocket.send(int(message) + 1)
    else:
        value = int(request.GET['value'])
        value += 1
        return HttpResponse(unicode(value))


@require_websocket
def echo_once(request):
    request.websocket.send(request.websocket.wait())


class DecoratorTests(TestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_require_websocket_decorator(self):
        # view requires websocket -> bad request
        request = self.rf.get('/echo/')
        response = echo_once(request)
        self.assertEquals(response.status_code, 400)

    def test_accept_websocket_decorator(self):
        request = self.rf.get('/add/', {'value': '23'})
        response = add_one(request)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.content, '24')

# TODO: test views with actual websocket connection - not really possible yet
# with django's test client/request factory. Heavy use of mock objects
# necessary.

########NEW FILE########
__FILENAME__ = utils
from django.test import Client
from django.core.handlers.wsgi import WSGIRequest


class RequestFactory(Client):
    """
    Class that lets you create mock Request objects for use in testing.

    Usage:

    rf = RequestFactory()
    get_request = rf.get('/hello/')
    post_request = rf.post('/submit/', {'foo': 'bar'})

    This class re-uses the django.test.client.Client interface, docs here:
    http://www.djangoproject.com/documentation/testing/#the-test-client

    Once you have a request object you can pass it to any view function,
    just as if that view had been hooked up using a URLconf.

    """
    def request(self, **request):
        """
        Similar to parent class, but returns the request object as soon as it
        has created it.
        """
        environ = {
            'HTTP_COOKIE': self.cookies,
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }
        environ.update(self.defaults)
        environ.update(request)
        return WSGIRequest(environ)


class WebsocketFactory(RequestFactory):
    def __init__(self, *args, **kwargs):
        self.protocol_version = kwargs.pop('websocket_version', 75)
        super(WebsocketFactory, self).__init__(*args, **kwargs)

    def request(self, **request):
        """
        Returns a request simliar to one from a browser which wants to upgrade
        to a websocket connection.
        """
        environ = {
            'HTTP_COOKIE': self.cookies,
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
            'SERVER_PROTOCOL': 'HTTP/1.1',
            # WebSocket specific headers
            'HTTP_CONNECTION': 'Upgrade',
            'HTTP_UPGRADE': 'WebSocket',
        }
        if self.protocol_version == 76:
            raise NotImplementedError(u'This version is not yet supported.')
        environ.update(self.defaults)
        environ.update(request)
        return WSGIRequest(environ)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for examples project.
import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(PROJECT_ROOT))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'db.sqlite',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'a#(pgz7yyyld!7mgs3(yve=t0^!psep_-&w=e@0&p)a##s(&r-'

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
)

ROOT_URLCONF = 'examples.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django_websocket',

    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.shortcuts import render_to_response
from django.template import RequestContext
from django_websocket import require_websocket

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

def base_view(request):
    return render_to_response('index.html', {

    }, context_instance=RequestContext(request))


@require_websocket
def echo(request):
    for message in request.websocket:
        request.websocket.send(message)


urlpatterns = patterns('',
    # Example:
    url(r'^$', base_view),
    url(r'^echo$', echo),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
