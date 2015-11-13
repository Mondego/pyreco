__FILENAME__ = cycle
import i3
import time

def cycle():
    # get currently focused windows
    current = i3.filter(nodes=[], focused=True)
    # get unfocused windows
    other = i3.filter(nodes=[], focused=False)
    # focus each previously unfocused window for 0.5 seconds
    for window in other:
        i3.focus(con_id=window['id'])
        time.sleep(0.5)
    # focus the original windows
    for window in current:
        i3.focus(con_id=window['id'])

if __name__ == '__main__':
    cycle()

########NEW FILE########
__FILENAME__ = fibonacci
import i3
import os
import time

term = os.environ.get('TERM', 'xterm')
if 'rxvt-unicode' in term: 
    term = 'urxvt'

def fibonacci(num):
    i3.exec(term)
    time.sleep(0.5)
    if num % 2 == 0:
        if num % 4 == 0:
            i3.focus('up')
        i3.split('h')
    else:
        if num % 4 == 1:
            i3.focus('left')
        i3.split('v')
    if num > 1:
        fibonacci(num - 1)

def run(num):
    # current workspace
    current = [ws for ws in i3.get_workspaces() if ws['focused']][0]
    # switch to workspace named 'fibonacci'
    i3.workspace('fibonacci')
    i3.layout('default')
    fibonacci(num)
    time.sleep(3)
    # close all opened terminals
    for n in range(num):
        i3.kill()
        time.sleep(0.5)
    i3.workspace(current['name'])

if __name__ == '__main__':
    run(8)

########NEW FILE########
__FILENAME__ = ipc
#!/usr/bin/env python
#======================================================================
# i3 (Python module for communicating with i3 window manager)
# Copyright (C) 2012  Jure Ziberna
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#======================================================================


import os
import argparse

import i3


# Generate description based on current version and its date
DESCRIPTION = 'i3-ipc %s (%s).' % (i3.__version__, i3.__date__)
DESCRIPTION += ' Implemented in Python.'

# Dictionary of command-line help messages
HELP = {
    'socket': "custom path to an i3 socket file",
    'type': "message type in text form (e.g. \"get_tree\")",
    'timeout': "seconds before socket times out, floating point values allowed",
    'message': "message or \"payload\" to send, can be multiple strings",
}


def parse():
    """
    Creates argument parser for parsing command-line arguments. Returns parsed
    arguments in a form of a namespace.
    """
    # Setting up argument parses
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('-s', metavar='<socket>', dest='socket', type=str, default=None, help=HELP['socket'])
    parser.add_argument('-t', metavar='<type>', dest='type', type=str, default='command', help=HELP['type'])
    parser.add_argument('-T', metavar='<timeout>', dest='timeout', type=float, default=None, help=HELP['timeout'])
    parser.add_argument('<message>', type=str, nargs='*', help=HELP['message'])
    # Parsing and hacks
    args = parser.parse_args()
    message = args.__dict__['<message>']
    args.message = ' '.join(message)
    return args


def main(socket, type, timeout, message):
    """
    Excepts arguments and evaluates them.
    """
    if not socket:
        socket = i3.get_socket_path()
        if not socket:
            print("Couldn't get socket path. Are you sure i3 is running?")
            return False
    # Initializes default socket with given path and timeout
    try:
        i3.default_socket(i3.Socket(path=socket, timeout=timeout))
    except i3.ConnectionError:
        print("Couldn't connect to socket at '%s'." % socket)
        return False
    # Format input
    if type in i3.EVENT_TYPES:
        event_type = type
        event = message
        type = 'subscribe'
    elif type == 'subscribe':
        message = message.split(' ')
        message_len = len(message)
        if message_len >= 1:
            event_type = message[0]
            if message_len >= 2:
                event = ' '.join(message[1:])
            else:
                event = ''
        else:
            # Let if fail
            event_type = ''
    try:
        if type == 'subscribe':
            i3.subscribe(event_type, event)
        else:
            output = i3.msg(type, message)
            print(output)
    except i3.i3Exception as i3error:
        print(i3error)


if __name__ == '__main__':
    args = parse()
    main(args.socket, args.type, args.timeout, args.message)


########NEW FILE########
__FILENAME__ = scratcher
#!/usr/bin/env python
"""
Cycling through scratchpad windows...

Add this to your i3 config file:
    bindsym <key-combo> exec python /path/to/this/script.py
"""

import i3

def scratchpad_windows():
    # get containers with appropriate scratchpad state
    containers = i3.filter(scratchpad_state='changed')
    # filter out windows (leaf nodes of the above containers)
    return i3.filter(containers, nodes=[])

def main():
    windows = scratchpad_windows()
    # search for focused window among scratchpad windows
    if i3.filter(windows, focused=True):
        # move that window back to scratchpad
        i3.move('scratchpad')
    # show the next scratchpad window
    i3.scratchpad('show')

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = winmenu
#!/usr/bin/env python
# dmenu script to jump to windows in i3.
#
# using ziberna's i3-py library: https://github.com/ziberna/i3-py
# depends: dmenu (vertical patch), i3.
# released by joepd under WTFPLv2-license:
# http://sam.zoy.org/wtfpl/COPYING
#
# edited by Jure Ziberna for i3-py's examples section

import i3
import subprocess

def i3clients():
    """
    Returns a dictionary of key-value pairs of a window text and window id.
    Each window text is of format "[workspace] window title (instance number)"
    """
    clients = {}
    for ws_num in range(1,11):
        workspace = i3.filter(num=ws_num)
        if not workspace:
            continue
        workspace = workspace[0]
        windows = i3.filter(workspace, nodes=[])
        instances = {}
        # Adds windows and their ids to the clients dictionary
        for window in windows:
            win_str = '[%s] %s' % (workspace['name'], window['name'])
            # Appends an instance number if other instances are present
            if win_str in instances:
                instances[win_str] += 1
                win_str = '%s (%d)' % (win_str, instances[win_str])
            else:
                instances[win_str] = 1
            clients[win_str] = window['id']
    return clients

def win_menu(clients, l=10):
    """
    Displays a window menu using dmenu. Returns window id.
    """
    dmenu = subprocess.Popen(['/usr/bin/dmenu','-i','-l', str(l)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE)
    menu_str = '\n'.join(sorted(clients.keys()))
    # Popen.communicate returns a tuple stdout, stderr
    win_str = dmenu.communicate(menu_str.encode('utf-8'))[0].decode('utf-8').rstrip()
    return clients.get(win_str, None)

if __name__ == '__main__':
    clients = i3clients()
    win_id = win_menu(clients)
    if win_id:
        i3.focus(con_id=win_id)


########NEW FILE########
__FILENAME__ = wsbar
#!/usr/bin/env python
#======================================================================
# i3 (Python module for communicating with i3 window manager)
# Copyright (C) 2012  Jure Ziberna
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#======================================================================


import sys
import time
import subprocess

import i3


class Colors(object):
    """
    A class for easier managing of bar's colors.
    Attributes (hexadecimal color values):
    - background
    - statusline (foreground)
    (below are (foreground, background) tuples for workspace buttons)
    - focused
    - active (when a workspace is opened on unfocused output)
    - inactive (unfocused workspace)
    - urgent
    The naming comes from i3-wm itself.
    Default values are also i3-wm's defaults.
    """
    # bar colors
    background = '#000000'
    statusline = '#ffffff'
    # workspace button colors
    focused = ('#ffffff', '#285577')
    active = ('#ffffff', '#333333')
    inactive = ('#888888', '#222222')
    urgent = ('#ffffff', '#900000')
    
    def get_color(self, workspace, output):
        """
        Returns a (foreground, background) tuple based on given workspace
        state.
        """
        if workspace['focused']:
            if output['current_workspace'] == workspace['name']:
                return self.focused
            else:
                return self.active
        if workspace['urgent']:
            return self.urgent
        else:
            return self.inactive


class i3wsbar(object):
    """
    A workspace bar; display a list of workspaces using a given bar
    application. Defaults to dzen2.
    Changeable settings (attributes):
    - button_format
    - bar_format
    - colors (see i3wsbar.Colors docs)
    - font
    - bar_command (the bar application)
    - bar_arguments (command-line arguments for the bar application)
    """
    # bar formatting (set for dzen)
    button_format = '^bg(%s)^ca(1,i3-ipc workspace %s)^fg(%s)%s^ca()^bg() '
    bar_format = '^p(_LEFT) %s^p(_RIGHT) '
    # default bar style
    colors = Colors()
    font = '-misc-fixed-medium-r-normal--13-120-75-75-C-70-iso10646-1'
    # default bar settings
    bar_command = 'dzen2'
    bar_arguments = ['-dock', '-fn', font, '-bg', colors.background, '-fg', colors.statusline]
    
    def __init__(self, colors=None, font=None, bar_cmd=None, bar_args=None):
        if colors:
            self.colors = colors
        if font:
            self.font = font
        if bar_cmd:
            self.dzen_command = bar_cmd
        if bar_args:
            self.bar_arguments = bar_args
        # Initialize bar application...
        args = [self.bar_command] + self.bar_arguments
        self.bar = subprocess.Popen(args, stdin=subprocess.PIPE)
        # ...and socket
        self.socket = i3.Socket()
        # Output to the bar right away
        workspaces = self.socket.get('get_workspaces')
        outputs = self.socket.get('get_outputs')
        self.display(self.format(workspaces, outputs))
        # Subscribe to an event
        callback = lambda data, event, _: self.change(data, event)
        self.subscription = i3.Subscription(callback, 'workspace')
    
    def change(self, event, workspaces):
        """
        Receives event and workspace data, changes the bar if change is
        present in event.
        """
        if 'change' in event:
            outputs = self.socket.get('get_outputs')
            bar_text = self.format(workspaces, outputs)
            self.display(bar_text)
    
    def format(self, workspaces, outputs):
        """
        Formats the bar text according to the workspace data given.
        """
        bar = ''
        for workspace in workspaces:
            output = None
            for output_ in outputs:
                if output_['name'] == workspace['output']:
                    output = output_
                    break
            if not output:
                continue
            foreground, background = self.colors.get_color(workspace, output)
            if not foreground:
                continue
            name = workspace['name']
            button = self.button_format % (background, "'"+name+"'", foreground, name)
            bar += button
        return self.bar_format % bar
    
    def display(self, bar_text):
        """
        Displays a text on the bar by piping it to the bar application.
        """
        bar_text += '\n'
        try:
            bar_text = bar_text.encode()
        except AttributeError:
            pass  # already a byte string
        self.bar.stdin.write(bar_text)
    
    def quit(self):
        """
        Quits the i3wsbar; closes the subscription and terminates the bar
        application.
        """
        self.subscription.close()
        self.bar.terminate()


if __name__ == '__main__':
    args = sys.argv[1:]
    bar = i3wsbar(bar_args=args)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('')  # force new line
    finally:
        bar.quit()


########NEW FILE########
__FILENAME__ = i3
#======================================================================
# i3 (Python module for communicating with i3 window manager)
# Copyright (C) 2012  Jure Ziberna
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#======================================================================


import sys
import subprocess
import json
import socket
import struct
import threading
import time

ModuleType = type(sys)


__author__ = 'Jure Ziberna'
__version__ = '0.6.5'
__date__ = '2012-06-20'
__license__ = 'GNU GPL 3'


MSG_TYPES = [
    'command',
    'get_workspaces',
    'subscribe',
    'get_outputs',
    'get_tree',
    'get_marks',
    'get_bar_config',
]

EVENT_TYPES = [
    'workspace',
    'output',
]


class i3Exception(Exception):
    pass

class MessageTypeError(i3Exception):
    """
    Raised when message type isn't available. See i3.MSG_TYPES.
    """
    def __init__(self, type):
        msg = "Message type '%s' isn't available" % type
        super(MessageTypeError, self).__init__(msg)

class EventTypeError(i3Exception):
    """
    Raised when even type isn't available. See i3.EVENT_TYPES.
    """
    def __init__(self, type):
        msg = "Event type '%s' isn't available" % type
        super(EventTypeError, self).__init__(msg)

class MessageError(i3Exception):
    """
    Raised when a message to i3 is unsuccessful.
    That is, when it contains 'success': false in its JSON formatted response.
    """
    pass

class ConnectionError(i3Exception):
    """
    Raised when a socket couldn't connect to the window manager.
    """
    def __init__(self, socket_path):
        msg = "Could not connect to socket at '%s'" % socket_path
        super(ConnectionError, self).__init__(msg)


def parse_msg_type(msg_type):
    """
    Returns an i3-ipc code of the message type. Raises an exception if
    the given message type isn't available.
    """
    try:
        index = int(msg_type)
    except ValueError:
        index = -1
    if index >= 0 and index < len(MSG_TYPES):
        return index
    msg_type = str(msg_type).lower()
    if msg_type in MSG_TYPES:
        return MSG_TYPES.index(msg_type)
    else:
        raise MessageTypeError(msg_type)

def parse_event_type(event_type):
    """
    Returns an i3-ipc string of the event_type. Raises an exception if
    the given event type isn't available.
    """
    try:
        index = int(event_type)
    except ValueError:
        index = -1
    if index >= 0 and index < len(EVENT_TYPES):
        return EVENT_TYPES[index]
    event_type = str(event_type).lower()
    if event_type in EVENT_TYPES:
        return event_type
    else:
        raise EventTypeError(event_type)


class Socket(object):
    """
    Socket for communicating with the i3 window manager.
    Optional arguments:
    - path of the i3 socket. Path is retrieved from i3-wm itself via
      "i3.get_socket_path()" if not provided.
    - timeout in seconds
    - chunk_size in bytes
    - magic_string as a safety string for i3-ipc. Set to 'i3-ipc' by default.
    """
    magic_string = 'i3-ipc'  # safety string for i3-ipc
    chunk_size = 1024  # in bytes
    timeout = 0.5  # in seconds
    buffer = b''  # byte string
    
    def __init__(self, path=None, timeout=None, chunk_size=None,
                 magic_string=None):
        if not path:
            path = get_socket_path()
        self.path = path
        if timeout:
            self.timeout = timeout
        if chunk_size:
            self.chunk_size = chunk_size
        if magic_string:
            self.magic_string = magic_string
        # Socket initialization and connection
        self.initialize()
        self.connect()
        # Struct format initialization, length of magic string is in bytes
        self.struct_header = '<%dsII' % len(self.magic_string.encode('utf-8'))
        self.struct_header_size = struct.calcsize(self.struct_header)
    
    def initialize(self):
        """
        Initializes the socket.
        """
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)
    
    def connect(self, path=None):
        """
        Connects the socket to socket path if not already connected.
        """
        if not self.connected:
            self.initialize()
            if not path:
                path = self.path
            try:
                self.socket.connect(path)
            except socket.error:
                raise ConnectionError(path)
    
    def get(self, msg_type, payload=''):
        """
        Convenience method, calls "socket.send(msg_type, payload)" and
        returns data from "socket.receive()".
        """
        self.send(msg_type, payload)
        return self.receive()
    
    def subscribe(self, event_type, event=None):
        """
        Subscribes to an event. Returns data on first occurrence.
        """
        event_type = parse_event_type(event_type)
        # Create JSON payload from given event type and event
        payload = [event_type]
        if event:
            payload.append(event)
        payload = json.dumps(payload)
        return self.get('subscribe', payload)
    
    def send(self, msg_type, payload=''):
        """
        Sends the given message type with given message by packing them
        and continuously sending bytes from the packed message.
        """
        message = self.pack(msg_type, payload)
        # Continuously send the bytes from the message
        self.socket.sendall(message)
    
    def receive(self):
        """
        Tries to receive a data. Unpacks the received byte string if
        successful. Returns None on failure.
        """
        try:
            data = self.socket.recv(self.chunk_size)
            msg_magic, msg_length, msg_type = self.unpack_header(data)
            msg_size = self.struct_header_size + msg_length
            # Keep receiving data until the whole message gets through
            while len(data) < msg_size:
                data += self.socket.recv(msg_length)
            data = self.buffer + data
            return self.unpack(data)
        except socket.timeout:
            return None
    
    def pack(self, msg_type, payload):
        """
        Packs the given message type and payload. Turns the resulting
        message into a byte string.
        """
        msg_magic = self.magic_string
        # Get the byte count instead of number of characters
        msg_length = len(payload.encode('utf-8'))
        msg_type = parse_msg_type(msg_type)
        # "struct.pack" returns byte string, decoding it for concatenation
        msg_length = struct.pack('I', msg_length).decode('utf-8')
        msg_type = struct.pack('I', msg_type).decode('utf-8')
        message = '%s%s%s%s' % (msg_magic, msg_length, msg_type, payload)
        # Encoding the message back to byte string
        return message.encode('utf-8')
    
    def unpack(self, data):
        """
        Unpacks the given byte string and parses the result from JSON.
        Returns None on failure and saves data into "self.buffer".
        """
        data_size = len(data)
        msg_magic, msg_length, msg_type = self.unpack_header(data)
        msg_size = self.struct_header_size + msg_length
        # Message shouldn't be any longer than the data
        if data_size >= msg_size:
            payload = data[self.struct_header_size:msg_size].decode('utf-8')
            payload = json.loads(payload)
            self.buffer = data[msg_size:]
            return payload
        else:
            self.buffer = data
            return None
    
    def unpack_header(self, data):
        """
        Unpacks the header of given byte string.
        """
        return struct.unpack(self.struct_header, data[:self.struct_header_size])
    
    @property
    def connected(self):
        """
        Returns True if connected and False if not.
        """
        try:
            self.get('command')
            return True
        except socket.error:
            return False
    
    def close(self):
        """
        Closes the socket connection.
        """
        self.socket.close()


class Subscription(threading.Thread):
    """
    Creates a new subscription and runs a listener loop. Calls the
    callback on event.
    Example parameters:
    callback = lambda event, data, subscription: print(data)
    event_type = 'workspace'
    event = 'focus'
    event_socket = <i3.Socket object>
    data_socket = <i3.Socket object>
    """
    subscribed = False
    type_translation = {
        'workspace': 'get_workspaces',
        'output': 'get_outputs'
    }
    
    def __init__(self, callback, event_type, event=None, event_socket=None,
                 data_socket=None):
        # Variable initialization
        if not callable(callback):
            raise TypeError('Callback must be callable')
        event_type = parse_event_type(event_type)
        self.callback = callback
        self.event_type = event_type
        self.event = event
        # Socket initialization
        if not event_socket:
            event_socket = Socket()
        self.event_socket = event_socket
        self.event_socket.subscribe(event_type, event)
        if not data_socket:
            data_socket = Socket()
        self.data_socket = data_socket
        # Thread initialization
        threading.Thread.__init__(self)
        self.start()
    
    def run(self):
        """
        Wrapper method for the listen method -- handles exceptions.
        The method is run by the underlying "threading.Thread" object.
        """
        try:
            self.listen()
        except socket.error:
            self.close()
    
    def listen(self):
        """
        Runs a listener loop until self.subscribed is set to False.
        Calls the given callback method with data and the object itself.
        If event matches the given one, then matching data is retrieved.
        Otherwise, the event itself is sent to the callback.
        In that case 'change' key contains the thing that was changed.
        """
        self.subscribed = True
        while self.subscribed:
            event = self.event_socket.receive()
            if not event:  # skip an iteration if event is None
                continue
            if not self.event or ('change' in event and event['change'] == self.event):
                msg_type = self.type_translation[self.event_type]
                data = self.data_socket.get(msg_type)
            else:
                data = None
            self.callback(event, data, self)
        self.close()
    
    def close(self):
        """
        Ends subscription loop by setting self.subscribed to False and
        closing both sockets.
        """
        self.subscribed = False
        self.event_socket.close()
        if self.data_socket is not default_socket():
            self.data_socket.close()


def __call_cmd__(cmd):
    """
    Returns output (stdout or stderr) of the given command args.
    """
    try:
        output = subprocess.check_output(cmd)
    except subprocess.CalledProcessError as error:
        output = error.output
    output = output.decode('utf-8')  # byte string decoding
    return output.strip()


__socket__ = None
def default_socket(socket=None):
    """
    Returns i3.Socket object, which was initiliazed once with default values
    if no argument is given.
    Otherwise sets the default socket to the given socket.
    """
    global __socket__
    if socket and isinstance(socket, Socket):
        __socket__ = socket
    elif not __socket__:
        __socket__ = Socket()
    return __socket__


def msg(type, message=''):
    """
    Takes a message type and a message itself.
    Talks to the i3 via socket and returns the response from the socket.
    """
    response = default_socket().get(type, message)
    return response


def __function__(type, message='', *args, **crit):
    """
    Accepts a message type, a message. Takes optional args and keyword
    args which are present in all future calls of the resulting function.
    Returns a function, which takes arguments and container criteria.
    If message type was 'command', the function returns success value.
    """
    def function(*args2, **crit2):
        msg_full = ' '.join([message] + list(args)  + list(args2))
        criteria = dict(crit)
        criteria.update(crit2)
        if criteria:
            msg_full = '%s %s' % (container(**criteria), msg_full)
        response = msg(type, msg_full)
        response = success(response)
        if isinstance(response, i3Exception):
            raise response
        return response
    function.__name__ = type
    function.__doc__ = 'Message sender (type: %s, message: %s)' % (type, message)
    return function


def subscribe(event_type, event=None, callback=None):
    """
    Accepts an event_type and event itself.
    Creates a new subscription, prints data on every event until
    KeyboardInterrupt is raised.
    """
    if not callback:
        def callback(event, data, subscription):
            print('changed:', event['change'])
            if data:
                print('data:\n', data)
    
    socket = default_socket()
    subscription = Subscription(callback, event_type, event, data_socket=socket)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('')  # force newline
    finally:
        subscription.close()


def get_socket_path():
    """
    Gets the socket path via i3 command.
    """
    cmd = ['i3', '--get-socketpath']
    output = __call_cmd__(cmd)
    return output


def success(response):
    """
    Convenience method for filtering success values of a response.
    Each success dictionary is replaces with boolean value.
    i3.MessageError is returned if error key is found in any of the
    success dictionaries.
    """
    if isinstance(response, dict) and 'success' in response:
        if 'error' in response:
            return MessageError(response['error'])
        return response['success']
    elif isinstance(response, list):
        for index, item in enumerate(response):
            item = success(item)
            if isinstance(item, i3Exception):
                return item
            response[index] = item
    return response


def container(**criteria):
    """
    Turns keyword arguments into a formatted container criteria.
    """
    criteria = ['%s="%s"' % (key, val) for key, val in criteria.items()]
    return '[%s]' % ' '.join(criteria)


def parent(con_id, tree=None):
    """
    Searches for a parent of a node/container, given the container id.
    Returns None if no container with given id exists (or if the
    container is already a root node).
    """
    def has_child(node):
        for child in node['nodes']:
            if child['id'] == con_id:
                return True
        return False
    parents = filter(tree, has_child)
    if not parents or len(parents) > 1:
        return None
    return parents[0]

 
def filter(tree=None, function=None, **conditions):
    """
    Filters a tree based on given conditions. For example, to get a list of
    unfocused windows (leaf nodes) in the current tree:
      i3.filter(nodes=[], focused=False)
    The return value is always a list of matched items, even if there's
    only one item that matches.
    The user function should take a single node. The function doesn't have
    to do any dict key or index checking (this is handled by i3.filter
    internally).
    """
    if tree is None:
        tree = msg('get_tree')
    elif isinstance(tree, list):
        tree = {'list': tree}
    if function:
        try:
            if function(tree):
                return [tree]
        except (KeyError, IndexError):
            pass
    else:
        for key, value in conditions.items():
            if key not in tree or tree[key] != value:
                break
        else:
            return [tree]
    matches = []
    for nodes in ['nodes', 'floating_nodes', 'list']:
        if nodes in tree:
            for node in tree[nodes]:
                matches += filter(node, function, **conditions)
    return matches


class i3(ModuleType):
    """
    i3.py is a Python module for communicating with the i3 window manager.
    """
    def __init__(self, module):
        self.__module__ = module
        self.__name__ = module.__name__
    
    def __getattr__(self, name):
        """
        Turns a nonexistent attribute into a function.
        Returns the resulting function.
        """
        try:
            return getattr(self.__module__, name)
        except AttributeError:
            pass
        if name.lower() in self.__module__.MSG_TYPES:
            return self.__module__.__function__(type=name)
        else:
            return self.__module__.__function__(type='command', message=name)


# Turn the module into an i3 object
sys.modules[__name__] = i3(sys.modules[__name__])

########NEW FILE########
__FILENAME__ = test
import i3
import unittest
import platform
py3 = platform.python_version_tuple() > ('3',)

class ParseTest(unittest.TestCase):
    def setUp(self):
        self.msg_types = ['get_tree', 4, '4']
        self.event_types = ['output', 1, '1']
    
    def test_msg_parse(self):
        msg_types = []
        for msg_type in self.msg_types:
            msg_types.append(i3.parse_msg_type(msg_type))
        for index in range(-1, len(msg_types) - 1):
            self.assertEqual(msg_types[index], msg_types[index+1])
            self.assertIsInstance(msg_types[index], int)
    
    def test_event_parse(self):
        event_types = []
        for event_type in self.event_types:
            event_types.append(i3.parse_event_type(event_type))
        for index in range(-1, len(event_types) - 1):
            self.assertEqual(event_types[index], event_types[index+1])
            self.assertIsInstance(event_types[index], str)
    
    def test_msg_type_error(self):
        border_lower = -1
        border_higher = len(i3.MSG_TYPES)
        values = ['joke', border_lower, border_higher, -100, 100]
        for val in values:
            self.assertRaises(i3.MessageTypeError, i3.parse_msg_type, val)
            self.assertRaises(i3.MessageTypeError, i3.parse_msg_type, str(val))
    
    def test_event_type_error(self):
        border_lower = -1
        border_higher = len(i3.EVENT_TYPES)
        values = ['joke', border_lower, border_higher, -100, 100]
        for val in values:
            self.assertRaises(i3.EventTypeError, i3.parse_event_type, val)
            self.assertRaises(i3.EventTypeError, i3.parse_event_type, str(val))
    
    def test_msg_error(self):
        """If i3.yada doesn't pass, see http://bugs.i3wm.org/report/ticket/693"""
        self.assertRaises(i3.MessageError, i3.focus)  # missing argument
        self.assertRaises(i3.MessageError, i3.yada)  # doesn't exist
        self.assertRaises(i3.MessageError, i3.meh, 'some', 'args')
    

class SocketTest(unittest.TestCase):
    def setUp(self):
        pass
    
    def test_connection(self):
        def connect():
            return i3.Socket('/nil/2971.socket')
        self.assertRaises(i3.ConnectionError, connect)
    
    def test_response(self, socket=i3.default_socket()):
        workspaces = socket.get('get_workspaces')
        self.assertIsNotNone(workspaces)
        for workspace in workspaces:
            self.assertTrue('name' in workspace)
    
    def test_multiple_sockets(self):
        socket1 = i3.Socket()
        socket2 = i3.Socket()
        socket3 = i3.Socket()
        for socket in [socket1, socket2, socket3]:
            self.test_response(socket)
        for socket in [socket1, socket2, socket3]:
            socket.close()
    
    def test_pack(self):
        packed = i3.default_socket().pack(0, "haha")
        if py3:
            self.assertIsInstance(packed, bytes)


class GeneralTest(unittest.TestCase):
    def setUp(self):
        pass
    
    def test_getattr(self):
        func = i3.some_attribute
        self.assertTrue(callable(func))
        socket = i3.default_socket()
        self.assertIsInstance(socket, i3.Socket)
    
    def test_success(self):
        data = {'success': True}
        self.assertEqual(i3.success(data), True)
        self.assertEqual(i3.success([data, {'success': False}]), [True, False])
        data = {'success': False, 'error': 'Error message'}
        self.assertIsInstance(i3.success(data), i3.MessageError)
    
    def test_container(self):
        container = i3.container(title='abc', con_id=123)
        output = ['[title="abc" con_id="123"]',
                '[con_id="123" title="abc"]']
        self.assertTrue(container in output)

    def test_criteria(self):
        self.assertTrue(i3.focus(clasS='xterm'))
    
    def test_filter1(self):
        windows = i3.filter(nodes=[])
        for window in windows:
            self.assertEqual(window['nodes'], [])
    
    def test_filter2(self):
        unfocused_windows = i3.filter(focused=False)
        parent_count = 0
        for window in unfocused_windows:
            self.assertEqual(window['focused'], False)
            if window['nodes'] != []:
                parent_count += 1
        self.assertGreater(parent_count, 0)
    
    def test_filter_function_wikipedia(self):
        """You have to have a Wikipedia tab opened in a browser."""
        func = lambda node: 'Wikipedia' in node['name']
        nodes = i3.filter(function=func)
        self.assertTrue(nodes != [])
        for node in nodes:
            self.assertTrue('free encyclopedia' in node['name'])

if __name__ == '__main__':
    test_suits = []
    for Test in [ParseTest, SocketTest, GeneralTest]:
        test_suits.append(unittest.TestLoader().loadTestsFromTestCase(Test))
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(test_suits))


########NEW FILE########
