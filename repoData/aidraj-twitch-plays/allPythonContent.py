__FILENAME__ = config_dist
config = {
    
    'irc': {
        'server': 'irc.twitch.tv',
        'port': 6667
    },

    'account': {
        'username': 'username',
        'password': 'oauth:' # http://twitchapps.com/tmi/
    },

    'throttled_buttons': {
        'start': 10
    },

    'misc': {
        'chat_height': 13
    }

}
########NEW FILE########
__FILENAME__ = bot
import time

from config.config import config
from lib.irc import Irc
from lib.game import Game
from lib.misc import pbutton

class Bot:

    def __init__(self):
        self.config = config
        self.irc = Irc(config)
        self.game = Game()
        self.message_buffer = [{'username': '', 'button': ''}] * self.config['misc']['chat_height']

    def set_message_buffer(self, message):
        self.message_buffer.insert(self.config['misc']['chat_height'] - 1, message)
        self.message_buffer.pop(0)

    def run(self):
        throttle_timers = {button:0 for button in config['throttled_buttons'].keys()}

        while True:
            new_messages = self.irc.recv_messages(1024)
            
            if not new_messages:
                continue

            for message in new_messages: 
                button = message['message'].lower()
                username = message['username'].lower()

                if not self.game.is_valid_button(button):
                    continue

                if button in self.config['throttled_buttons']:
                    if time.time() - throttle_timers[button] < self.config['throttled_buttons'][button]:
                        continue

                    throttle_timers[button] = time.time()
         
                self.set_message_buffer({'username': username, 'button': button})
                pbutton(self.message_buffer)
                self.game.push_button(button)
########NEW FILE########
__FILENAME__ = game
import win32api
import win32con
import time

class Game:

    keymap = {
        'up': 0x30,
        'down': 0x31,
        'left': 0x32,
        'right': 0x33,
        'a': 0x34,
        'b': 0x35,
        'start': 0x36,
        'select': 0x37
    }

    def get_valid_buttons(self):
        return [button for button in self.keymap.keys()]

    def is_valid_button(self, button):
        return button in self.keymap.keys()

    def button_to_key(self, button):
        return self.keymap[button]

    def push_button(self, button):
        win32api.keybd_event(self.button_to_key(button), 0, 0, 0)
        time.sleep(.15)
        win32api.keybd_event(self.button_to_key(button), 0, win32con.KEYEVENTF_KEYUP, 0)
########NEW FILE########
__FILENAME__ = irc
import socket
import sys
import re

from lib.misc import pp, pbot

class Irc:

    socket_retry_count = 0

    def __init__(self, config):
        self.config = config
        self.set_socket_object()

    def set_socket_object(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock = sock

        sock.settimeout(10)

        username = self.config['account']['username'].lower()
        password = self.config['account']['password']

        server = self.config['irc']['server']
        port = self.config['irc']['port']

        try:
            sock.connect((server, port))
        except:
            pp('Error connecting to IRC server. (%s:%i) (%i)' % (server, port, self.socket_retry_count + 1), 'error')

            if self.socket_retry_count < 2:
                self.socket_retry_count += 1
                return self.set_socket_object()
            else:
                sys.exit()

        sock.settimeout(None)

        sock.send('USER %s\r\n' % username)
        sock.send('PASS %s\r\n' % password)
        sock.send('NICK %s\r\n' % username)

        if not self.check_login_status(self.recv()):
            pp('Invalid login.', 'error')
            sys.exit()
        else:
            pp('Login successful!')

        sock.send('JOIN #%s\r\n' % username)
        pp('Joined #%s' % username)

    def ping(self, data):
        if data.startswith('PING'):
            self.sock.send(data.replace('PING', 'PONG'))

    def recv(self, amount=1024):
        return self.sock.recv(amount)

    def recv_messages(self, amount=1024):
        data = self.recv(amount)

        if not data:
            pbot('Lost connection, reconnecting.')
            return self.set_socket_object()

        self.ping(data)

        if self.check_has_message(data):
            return [self.parse_message(line) for line in filter(None, data.split('\r\n'))]

    def check_login_status(self, data):
        if not re.match(r'^:(testserver\.local|tmi\.twitch\.tv) NOTICE \* :Login unsuccessful\r\n$', data): return True

    def check_has_message(self, data):
        return re.match(r'^:[a-zA-Z0-9_]+\![a-zA-Z0-9_]+@[a-zA-Z0-9_]+(\.tmi\.twitch\.tv|\.testserver\.local) PRIVMSG #[a-zA-Z0-9_]+ :.+$', data)

    def parse_message(self, data): 
        return {
            'channel': re.findall(r'^:.+\![a-zA-Z0-9_]+@[a-zA-Z0-9_]+.+ PRIVMSG (.*?) :', data)[0],
            'username': re.findall(r'^:([a-zA-Z0-9_]+)\!', data)[0],
            'message': re.findall(r'PRIVMSG #[a-zA-Z0-9_]+ :(.+)', data)[0].decode('utf8')
        }
########NEW FILE########
__FILENAME__ = misc
import time
from os import system

def pp(message, mtype='INFO'):
    mtype = mtype.upper()
    print '[%s] [%s] %s' % (time.strftime('%H:%M:%S', time.gmtime()), mtype, message)

def ppi(channel, message, username):
    print '[%s %s] <%s> %s' % (time.strftime('%H:%M:%S', time.gmtime()), channel, username.lower(), message)

def pbot(message, channel=''):
    if channel: 
        msg = '[%s %s] <%s> %s' % (time.strftime('%H:%M:%S', time.gmtime()), channel, 'BOT', message)
    else: 
        msg = '[%s] <%s> %s' % (time.strftime('%H:%M:%S', time.gmtime()), 'BOT', message)

    print msg

def pbutton(message_buffer):
    system('cls')
    print '\n\n'
    print '\n'.join([' {0:<12s} {1:>6s}'.format(message['username'][:12].title(), message['button'].lower()) for message in message_buffer])
########NEW FILE########
__FILENAME__ = serve
#!/usr/bin/env python

from sys import exit
from config.config import config
import lib.bot as bot

# Twitch Plays
# Inpsired by http://twitch.tv/twitchplayspokemon
# Written by Aidan Thomson - <aidraj0 at gmail dot com>

try:
    bot.Bot().run()
except KeyboardInterrupt:
    exit()

########NEW FILE########
__FILENAME__ = timer
import sys
import time
import os

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')
    print('\n')

days = 0
hours = 0
minutes = 0
seconds = 0

clear()

while True:

    seconds += 1

    if seconds == 60:
        seconds = 0
        minutes += 1
        clear()

    if minutes == 60:
        minutes = 0
        hours += 1
        clear()

    if hours == 24:
        hours = 0
        days += 1
        clear()

    message = '\t{0:>2}d {1:>2}h {2:>2}m {3:>2}s\r'.format(days, hours, minutes, seconds)
    
    sys.stdout.write(message)
    sys.stdout.flush()

    time.sleep(1)
########NEW FILE########
