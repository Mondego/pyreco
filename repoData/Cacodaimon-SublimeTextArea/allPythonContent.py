__FILENAME__ = SublimeTextarea
__author__ = 'Guido Krömer'
__license__ = 'MIT'
__version__ = '0.1'
__email__ = 'mail 64 cacodaemon 46 de'

import sublime
from sublime_plugin import TextCommand
from threading import Thread
import json
from .WebSocket.Server import Server
from .WebSocket.AbstractOnClose import AbstractOnClose
from .WebSocket.AbstractOnMessage import AbstractOnMessage
from .SublimeTextareaTools.OnSelectionModifiedListener import OnSelectionModifiedListener
from .SublimeTextareaTools.WindowHelper import WindowHelper


class ReplaceContentCommand(TextCommand):
    """
    Replaces the views complete text content.
    """
    def run(self, edit, **args):
        self.view.replace(edit, sublime.Region(0, self.view.size()), args['txt'])


class OnConnect(AbstractOnMessage):
    def on_message(self, text):
        try:
            request = json.loads(text)
            window_helper = WindowHelper()
            current_view = window_helper.add_file(request['title'], request['text'])
            OnSelectionModifiedListener.set_view_name(request['title'])

            self._web_socket_server.on_message(OnMessage(current_view))
        except ValueError:
            print('Invalid JSON!')


class OnMessage(AbstractOnMessage):
    def __init__(self, current_view):
        self._current_view = current_view

    def on_message(self, text):
        try:
            request = json.loads(text)
            self._current_view.run_command('replace_content', {'txt': request['text']})
        except ValueError:
            print('Invalid JSON!')


class OnClose(AbstractOnClose):
    def on_close(self):
        self._web_socket_server.on_message(OnConnect())
        Thread(target=web_socket_server_thread).start()

web_socket_server = Server('localhost', 1337)
OnSelectionModifiedListener.set_web_socket_server(web_socket_server)

web_socket_server.on_message(OnConnect())
web_socket_server.on_close(OnClose())


def web_socket_server_thread():
    global web_socket_server
    web_socket_server.start()

Thread(target = web_socket_server_thread).start()
########NEW FILE########
__FILENAME__ = OnSelectionModifiedListener
import sublime
from sublime_plugin import EventListener
import json
import sys


class OnSelectionModifiedListener(EventListener):
    """
    Handles content changes, each changes gets send with the given web socket server to the client.
    """
    _web_socket_server = None
    _view_name = None

    def on_selection_modified(self, view):
        if not OnSelectionModifiedListener._web_socket_server:
            return

        if not OnSelectionModifiedListener._view_name or OnSelectionModifiedListener._view_name != view.name():
            return

        sel_min, sel_max = OnSelectionModifiedListener._get_max_selection(view)

        changed_text = view.substr(sublime.Region(0, view.size()))
        response = json.dumps({
            'title': view.name(),
            'text':  changed_text,
            'cursor': {'min': sel_min, 'max': sel_max}
        })
        OnSelectionModifiedListener._web_socket_server.send_message(response)

    @staticmethod
    def set_web_socket_server(web_socket_server):
        OnSelectionModifiedListener._web_socket_server = web_socket_server

    @staticmethod
    def set_view_name(name):
        OnSelectionModifiedListener._view_name = name

    @staticmethod
    def _get_max_selection(view):
        """
        Returns the min and max values of all selections from the given view.
        """
        _max = 0
        _min = sys.maxsize

        for pos in view.sel():
            _min = min(pos.begin(), _min)
            _max = max(pos.end(), _max)

        return _min, _max
########NEW FILE########
__FILENAME__ = ReplaceContentCommand
import sublime
from sublime_plugin import TextCommand


class ReplaceContentCommand(TextCommand):
    """
    Replaces the views complete text content.
    """
    def run(self, edit, **args):
        self.view.replace(edit, sublime.Region(0, self.view.size()), args['txt'])
########NEW FILE########
__FILENAME__ = WindowHelper
import sublime


class WindowHelper(sublime.Window):
    """
    Helper class for opening new files in the active sublime text window.
    """
    def __init__(self):
        self.window_id = sublime.active_window().id()

    def add_file(self, title, text):
        """
        Creates a new file and adds the given text content to it.
        """
        view = self.new_file()
        view.set_name(title)
        view.set_status('title', title)
        view.run_command('replace_content', {'txt': text})

        return view
########NEW FILE########
__FILENAME__ = AbstractHandler
class AbstractHandler():
    """
    Abstract on whatever handler.
    """
    def __init__(self):
        self._web_socket_server = None

    def set_web_socket_server(self, web_socket_server):
        self._web_socket_server = web_socket_server
########NEW FILE########
__FILENAME__ = AbstractOnClose
from .AbstractHandler import AbstractHandler


class AbstractOnClose(AbstractHandler):
    """
    Abstract on connection close handler.
    """
    def on_close(self):
        raise NotImplementedError("error message")
########NEW FILE########
__FILENAME__ = AbstractOnMessage
from .AbstractHandler import AbstractHandler


class AbstractOnMessage(AbstractHandler):
    """
    Abstract on message handler.
    """
    def on_message(self, text):
        raise NotImplementedError("error message")
########NEW FILE########
__FILENAME__ = Frame

class Frame:
    """
    Parses and creates a WebSocket frame.
    """
    def __init__(self):
        self._payload_len = 0
        self._payload_start = 2
        self._mask_start = 2
        self._mask_data = []

        self.fin = False
        self.continues = False
        self.utf8 = False
        self.binary = False
        self.terminate = False
        self.ping = False
        self.pong = False
        self.mask = False

    def create(self, text):
        """
        Creates a from the given text.
        """
        length = len(text)

        if length <= 125:
            ret = bytearray([129, length])
        elif length > 65536:  # 64 bit length
            ret = bytearray([129,
                             127,
                             (length >> 56) & 0xff,
                             (length >> 48) & 0xff,
                             (length >> 40) & 0xff,
                             (length >> 32) & 0xff,
                             (length >> 24) & 0xff,
                             (length >> 16) & 0xff,
                             (length >> 8) & 0xff,
                             length & 0xff])
        else:  # 16bit length
            ret = bytearray([129, 126, (length >> 8) & 0xff, length & 0xff])

        for byte in text.encode("utf-8"):
            ret.append(byte)

        return ret

    def parse(self, data):
        """
        Parses a frame.
        """
        self._parse_first_byte(data[0])
        self._parse_second_byte(data[1])

        if self._payload_len == 126:  # 16 bit int length
            self._payload_len = (data[2] << 8) + data[3]
            self._mask_start += 2
            self._payload_start += 2

        if self._payload_len == 127:  # 64 bit int length
            self._payload_len = (data[2] << 56) + \
                               (data[3] << 48) + \
                               (data[4] << 40) + \
                               (data[5] << 32) + \
                               (data[6] << 24) + \
                               (data[7] << 16) + \
                               (data[8] << 8) + data[9]
            self._mask_start += 8
            self._payload_start += 8

        if self.mask:
            self._mask_data = [
                data[self._mask_start],
                data[self._mask_start + 1],
                data[self._mask_start + 2],
                data[self._mask_start + 3]
            ]

    def close(self):
        """
        Creates a closing frame.

        """
        return bytearray([136, 0])

    def get_payload(self, data):
        """
        Gets the payload from the given raw data, parse has to be called first!
        """
        if self.mask:
            res = bytearray(self._payload_len)
            i = 0
            for char in data[self._payload_start:]:
                res.append(char ^ self._mask_data[i % 4])
                i += 1

            return res

        return data[self._payload_start:]

    def get_payload_offset(self):
        """
        Retuns the payload offset length.

        """
        return self._payload_len - self._payload_start

    def _parse_first_byte(self, byte):
        self.fin = byte >= 128
        opcode = byte
        if self.fin:
            opcode -= 128

        self.continues = opcode == 0
        self.utf8 = opcode == 1
        self.binary = opcode == 2
        self.terminate = opcode == 8
        self.ping = opcode == 9
        self.pong = opcode == 10

    def _parse_second_byte(self, byte):
        self.mask = byte >= 128
        self._payload_len = byte

        if self.mask:
            self._payload_start += 4
            self._payload_len -= 128

    def __str__(self):
        lengths_frm = " maskStart: {}\n payloadStart: {}\n payloadLen: {}\n"
        lengths = lengths_frm.format(self._mask_start, self._payload_start, self._payload_len)

        flags_frm = " fin: {}\n continues: {}\n utf8: {}\n binary: {}\n terminate: {}\n ping: {}\n pong: {}\n mask: {}\n"
        flags = flags_frm.format(self.fin, self.continues, self.utf8, self.binary, self.terminate, self.ping, self.pong, self.mask)

        return "Frame:\n" + lengths + flags
########NEW FILE########
__FILENAME__ = Handshake
import hashlib
import base64


class Handshake:
    """
    Handles the WebSocket handshake.
    """
    def perform(self, data):
        """
        Parses the given request data and returns a matching response header.
        """
        key = self._build_web_socket_accept_from_request_header(data.decode("utf-8"))

        return self._build_response_header(key)

    def _build_web_socket_accept_from_request_header(self, header):
        """
        Parses the response header and builds a sec web socket accept.
        """
        search_term = "Sec-WebSocket-Key: "
        start = header.find(search_term) + len(search_term)
        end = header.find("\r\n", start)
        key = header[start:end]

        guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        key = (key + guid).encode('utf-8')
        sha1 = hashlib.sha1(key).digest()

        return base64.b64encode(sha1)

    def _build_response_header(self, key):
        """
        Builds the response header containing the given key.
        """
        return str("HTTP/1.1 101 Switching Protocols\r\n" +
                       "Upgrade: websocket\r\n" + 
                       "Connection: Upgrade\r\n" + 
                       "Sec-WebSocket-Accept: " + 
                       key.decode('utf-8') + 
                       "\r\n\r\n")
########NEW FILE########
__FILENAME__ = Server
import socket
from .Frame import Frame
from .Handshake import Handshake


class Server:
    """
    A simple, single threaded, web socket server.
    """
    def __init__(self, host='localhost', port=1337):
        self._handshake = Handshake()
        self._frame = Frame()

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((host, port))

        self._on_message_handler = None
        self._on_close_handler = None
        self._running = False
        self._conn = None
        self._address = None

        self._received_payload = ''

    def start(self):
        """
        Starts the server,
        """
        print('Start')
        self._socket.listen(1)
        self._conn, self._address = self._socket.accept()
        self._running = True

        data = self._conn.recv(1024)
        self._conn.sendall(self._handshake.perform(data).encode("utf-8"))

        while self._running:
            header = self._conn.recv(24)  # Max web socket header length

            if len(data) > 0:
                self._frame = Frame()

                try:
                    self._frame.parse(header)
                except IndexError:
                    self._running = False
                    continue

                if self._frame.terminate:
                    self._running = False
                    continue

                data = bytearray()
                data.extend(header)
                offset = self._frame.get_payload_offset()
                data.extend(self._conn.recv(offset))

                if self._frame.utf8:
                    request = self._frame.get_payload(data).decode("utf-8")
                    self._received_payload += request.lstrip('\x00')

                if self._frame.utf8 and self._frame.fin:
                    self._on_message_handler.on_message(self._received_payload)
                    self._received_payload = ''

        print('Stop')
        self.stop()

    def send_message(self, txt):
        """
        Sends a message if the server is in running state.
        """
        if not self._running:
            return

        self._frame = Frame()
        raw_data = self._frame.create(txt)
        self._conn.send(raw_data)

    def stop(self):
        """
        Stops the server by sending the fin package to the client and closing the socket.
        """
        self._running = False
        try:
            self._conn.send(self._frame.close())
        except BrokenPipeError:
            print('Ignored BrokenPipeError')

        self._conn.close()
        if self._on_close_handler:
            print('Triggering on_close')
            self._on_close_handler.on_close()

    def on_message(self, handler):
        """
        Sets the on message handler.
        """
        print('Setting on message handler')
        self._on_message_handler = handler
        self._on_message_handler.set_web_socket_server(self)

    def on_close(self, handler):
        """
        Sets the on connection closed handler.
        """
        print('Setting on close handler')
        self._on_close_handler = handler
        self._on_close_handler.set_web_socket_server(self)
########NEW FILE########
