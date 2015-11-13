__FILENAME__ = agent
'''
Copyright (C) 2012-2013 Karsten-Kai König <kkoenig@posteo.de>

This file is part of keepassc.

keepassc is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or at your
option) any later version.

keepassc is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with keepassc.  If not, see <http://www.gnu.org/licenses/>.
'''

"""This module implements an agent for KeePassC

    Classes:
        Agent(Client, Daemon)
"""

import logging
import signal
import socket
import ssl
import sys
from hashlib import sha256
from os import chdir
from os.path import expanduser, realpath, isfile, join

from keepassc.conn import *
from keepassc.client import Client
from keepassc.daemon import Daemon


class Agent(Daemon):
    """The KeePassC agent daemon"""

    def __init__(self, pidfile, loglevel, logfile,
                 server_address = 'localhost', server_port = 50000,
                 agent_port = 50001, password = None, keyfile = None,
                 tls = False, tls_dir = None):
        Daemon.__init__(self, pidfile)

        try:
            logdir = realpath(expanduser(getenv('XDG_DATA_HOME')))
        except:
            logdir = realpath(expanduser('~/.local/share'))
        finally:
            logfile = join(logdir, 'keepassc', logfile)

        logging.basicConfig(format='[%(levelname)s] in %(filename)s:'
                                   '%(funcName)s at %(asctime)s\n%(message)s',
                            level=loglevel, filename=logfile,
                            filemode='a')

        self.lookup = {
            b'FIND': self.find,
            b'GET': self.get_db,
            b'GETC': self.get_credentials}

        self.server_address = (server_address, server_port)
        try:
            # Listen for commands
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind(("localhost", agent_port))
            self.sock.listen(1)
        except OSError as err:
            print(err)
            logging.error(err.__str__())
            sys.exit(1)
        else:
            logging.info('Agent socket created on localhost:'+
                         str(agent_port))

        if tls_dir is not None:
            self.tls_dir = realpath(expanduser(tls_dir)).encode()
        else:
            self.tls_dir = b''

        chdir("/var/empty")

        self.password = password
        # Agent is a daemon and cannot find the keyfile after run
        if keyfile is not None:
            with open(keyfile, "rb") as handler:
                self.keyfile = handler.read()
                handler.close()
        else:
            self.keyfile = b''

        if tls is True:
            self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            self.context.verify_mode = ssl.CERT_REQUIRED
            self.context.load_verify_locations(tls_dir + "/cacert.pem")
        else:
            self.context = None

        #Handle SIGTERM
        signal.signal(signal.SIGTERM, self.handle_sigterm)

    def send_cmd(self, *cmd):
        """Overrides Client.connect_server"""

        if self.password is None:
            password = b''
        else:
            password = self.password.encode()

        tmp = [password, self.keyfile]
        tmp.extend(cmd)
        cmd_chain = build_message(tmp)

        try:
            tmp_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.context is not None:
                conn = self.context.wrap_socket(tmp_conn)
            else:
                conn = tmp_conn
            conn.connect(self.server_address)
        except:
            raise
        else:
            logging.info('Connected to '+self.server_address[0]+':'+
                         str(self.server_address[1]))

        try:
            conn.settimeout(60)
            if self.context is not None:
                if not isfile(self.tls_dir.decode() + '/pin'):
                    sha = sha256()
                    sha.update(conn.getpeercert(True))
                    with open(self.tls_dir.decode() + '/pin', 'wb') as pin:
                        pin.write(sha.digest())
                else:
                    with open(self.tls_dir.decode() + '/pin', 'rb') as pin:
                        pinned_key = pin.read()
                    sha = sha256()
                    sha.update(conn.getpeercert(True))
                    if pinned_key != sha.digest():
                        return (b'FAIL: Server certificate differs from '
                                b'pinned certificate')
                cert = conn.getpeercert()
                try:
                    ssl.match_hostname(cert, "KeePassC Server")
                except:
                    return b'FAIL: TLS - Hostname does not match'
            sendmsg(conn, cmd_chain)
            answer = receive(conn)
        except:
            raise
        finally:
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()

        return answer

    def run(self):
        """Overide Daemon.run() and provide sockets"""

        while True:
            try:
                conn, client = self.sock.accept()
            except OSError:
                break

            logging.info('Connected to '+client[0]+':'+str(client[1]))
            conn.settimeout(60)

            try:
                parts = receive(conn).split(b'\xB2\xEA\xC0')
                cmd = parts.pop(0)
                if cmd in self.lookup:
                    self.lookup[cmd](conn, parts)
                else:
                    logging.error('Received a wrong command')
                    sendmsg(conn, b'FAIL: Command isn\'t available')
            except OSError as err:
                logging.error(err.__str__())
            finally:
                conn.shutdown(socket.SHUT_RDWR)
                conn.close()

    def find(self, conn, cmd_misc):
        """Find Entries"""

        try:
            answer = self.send_cmd(b'FIND', cmd_misc[0])
            sendmsg(conn, answer)
            if answer[:4] == b'FAIL':
                raise OSError(answer.decode())
        except (OSError, TypeError) as err:
            logging.error(err.__str__())

    def get_db(self, conn, cmd_misc):
        """Get the whole encrypted database from server"""

        try:
            answer = self.send_cmd(b'GET')
            sendmsg(conn, answer)
            if answer[:4] == b'FAIL':
                raise OSError(answer.decode())
        except (OSError, TypeError) as err:
            logging.error(err.__str__())

    def get_credentials(self, conn, cmd_misc):
        """Send password credentials to client"""

        if self.password is None:
            password = b''
        else:
            password = self.password.encode()
        if self.context:
            tls = b'True'
        else:
            tls = b'False'

        tmp = [password, self.keyfile, self.server_address[0].encode(),
               str(self.server_address[1]).encode(), tls,
               self.tls_dir]
        chain = build_message(tmp)
        try:
            sendmsg(conn, chain)
        except (OSError, TypeError) as err:
            logging.error(err.__str__())

    def handle_sigterm(self, signum, frame):
        """Handle SIGTERM"""

        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
        del self.keyfile


########NEW FILE########
__FILENAME__ = client
'''
Copyright (C) 2012-2013 Karsten-Kai König <kkoenig@posteo.de>

This file is part of keepassc.

keepassc is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or at your
option) any later version.

keepassc is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with keepassc.  If not, see <http://www.gnu.org/licenses/>.
'''

"""This module implements the Client class for KeePassC.

Classes:
    Client(Connection)
"""

import logging
import socket
import ssl
from os.path import join, expanduser, realpath, isfile
from hashlib import sha256

from keepassc.conn import *

class Client(object):
    """The KeePassC client"""

    def __init__(self, loglevel, logfile, server_address = 'localhost',
                 server_port = 50000, password = None, keyfile = None,
                 tls = False, tls_dir = None):
        try:
            logdir = realpath(expanduser(getenv('XDG_DATA_HOME')))
        except:
            logdir = realpath(expanduser('~/.local/share'))
        finally:
            logfile = join(logdir, 'keepassc', logfile)

        logging.basicConfig(format='[%(levelname)s] in %(filename)s:'
                                   '%(funcName)s at %(asctime)s\n%(message)s',
                            level=loglevel, filename=logfile,
                            filemode='a')

        self.password = password
        self.keyfile = keyfile
        self.server_address = (server_address, server_port)

        self.tls_dir = tls_dir

        if tls is True:
            self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            self.context.verify_mode = ssl.CERT_REQUIRED
            logging.error(tls_dir)
            self.context.load_verify_locations(tls_dir + "/cacert.pem")
        else:
            self.context = None

    def send_cmd(self, *cmd):
        """Send a command to server

        *cmd are arbitary byte strings

        """
        if self.keyfile is not None:
            with open(self.keyfile, 'rb') as keyfile:
                key = keyfile.read()
        else:
            key = b''
        if self.password is None:
            password = b''
        else:
            password = self.password.encode()

        tmp = [password, key]
        tmp.extend(cmd)
        cmd_chain = build_message(tmp)

        try:
            tmp_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.context is not None:
                conn = self.context.wrap_socket(tmp_conn)
            else:
                conn = tmp_conn
            conn.connect(self.server_address)
        except:
            raise
        else:
            logging.info('Connected to '+self.server_address[0]+':'+
                         str(self.server_address[1]))
        try:
            conn.settimeout(60)
            if self.context is not None:
                if not isfile(self.tls_dir + '/pin'):
                    sha = sha256()
                    sha.update(conn.getpeercert(True))
                    with open(self.tls_dir + '/pin', 'wb') as pin:
                        pin.write(sha.digest())
                else:
                    with open(self.tls_dir + '/pin', 'rb') as pin:
                        pinned_key = pin.read()
                    sha = sha256()
                    sha.update(conn.getpeercert(True))
                    if pinned_key != sha.digest():
                        return (b'FAIL: Server certificate differs from '
                                b'pinned certificate')
                cert = conn.getpeercert()
                try:
                    ssl.match_hostname(cert, "KeePassC Server")
                except:
                    return b'FAIL: TLS - Hostname does not match'
            sendmsg(conn, cmd_chain)
            answer = receive(conn)
        except:
            raise
        finally:
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()

        return answer

    def get_bytes(self, cmd, *misc):
        """Send a command and get the answer as bytes

        cmd is a bytestring with the command
        *misc are arbitary bytestring needed for the command

        """

        try:
            db_buf = self.send_cmd(cmd, *misc)
            if db_buf[:4] == b'FAIL':
                raise OSError(db_buf.decode())
            return db_buf
        except (OSError, TypeError) as err:
            logging.error(err.__str__())
            return err.__str__()

    def get_string(self, cmd, *misc):
        """Send a command and get the answer decoded"""

        try:
            answer = self.send_cmd(cmd, *misc).decode()
            if answer[:4] == b'FAIL':
                raise OSError(answer)
            return answer
        except (OSError, TypeError) as err:
            logging.error(err.__str__())
            return err.__str__()

    def find(self, title):
        """Find entries by title"""

        return self.get_string(b'FIND', title)

    def get_db(self):
        """Just get the whole encrypted database from server"""

        return self.get_bytes(b'GET')

    def change_password(self, password, keyfile):
        """Change the password of the remote database

        This is only allowed from localhost (127.0.0.1

        """

        return self.get_string(b'CHANGESECRET', password, keyfile)

    def create_group(self, title, root):
        """Create a group

        
        title is the group title, root is the id of the parent group

        """

        return self.get_bytes(b'NEWG', title, root)

    def create_entry(self, title, url, username, password, comment, y, mon, d,
                     group_id):
        """Create an entry

        Watch the kppy documentation for an explanation of the arguments

        """

        return self.get_bytes(b'NEWE', title, url, username, password, comment,
                              y, mon, d, group_id)

    def delete_group(self, group_id, last_mod):
        """Delete a group by the id

        last_mod is needed to check if the group was updated since the
        last refresh

        """

        return self.get_bytes(b'DELG', group_id, str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def delete_entry(self, uuid, last_mod):
        """Delete an entry by uuid"""

        return self.get_bytes(b'DELE', uuid, str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def move_group(self, group_id, root):
        """Move a group to a new parent

        If root is 0 the group with id group_id is moved to the root

        """

        return self.get_bytes(b'MOVG', group_id, root)

    def move_entry(self, uuid, root):
        """Move an entry with uuid to the group with id root"""

        return self.get_bytes(b'MOVE', uuid, root)

    def set_g_title(self, title, group_id, last_mod):
        """Set the title of a group"""

        return self.get_bytes(b'TITG', title, group_id,
                         str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_title(self, title, uuid, last_mod):
        """Set the title of an entry"""

        return self.get_bytes(b'TITE', title, uuid, str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_user(self, username, uuid, last_mod):
        """Set the username of an entry"""

        return self.get_bytes(b'USER', username, uuid,
                         str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_url(self, url, uuid, last_mod):
        """Set the URL of an entry"""

        return self.get_bytes(b'URL', url, uuid, str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_comment(self, comment, uuid, last_mod):
        """Set the comment of an entry"""

        return self.get_bytes(b'COMM', comment, uuid,
                         str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_pass(self, password, uuid, last_mod):
        """Set the password of an entry"""

        return self.get_bytes(b'PASS', password, uuid,
                         str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_exp(self, y, mon, d, uuid, last_mod):
        """Set the expiration date of an entry"""

        return self.get_bytes(b'DATE', y, mon, d, uuid,
                         str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())


########NEW FILE########
__FILENAME__ = conn
'''
Copyright (C) 2012-2013 Karsten-Kai König <kkoenig@posteo.de>

This file is part of keepassc.

keepassc is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or at your
option) any later version.

keepassc is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with keepassc.  If not, see <http://www.gnu.org/licenses/>.
'''

"""This module implements some functions for a connection.

Functions:
    build_message(parts)
    receive(conn)
    sendmsg(sock, msg)
"""

import logging


def build_message(parts):
    """Join many parts to one message with a seperator

    A message will look like

    b'foo\xB2\xEA\xC0bar\xB2\xEA\xC0foobar'

    so that it could easily splitted by .split

    parts has to be a tuple of bytestrings

    """

    msg = b''
    for i in parts[:-1]:
        msg += i
        msg += b'\xB2\xEA\xC0' # \xB2\xEA\xC0 = BREAK
    msg += parts[-1]

    return msg

def receive(conn):
    """Receive a message

    conn has to be the socket which receive the message

    A message has to end with the bytestring  b'\xDE\xAD\xE1\x1D'
    
    """

    ip, port = conn.getpeername()
    logging.info('Receiving a message from '+ip+':'+str(port))
    data = b''
    while True:
        try:
            received = conn.recv(16)
        except:
            raise
        if b'\xDE\xAD\xE1\x1D' in received:
            data += received[:received.find(b'\xDE\xAD\xE1\x1D')]
            break
        else:
            data += received
            if data[-4:] == b'\xDE\xAD\xE1\x1D':
                data = data[:-4]
                break
    return data

def sendmsg(sock, msg):
    """Send message

    sock is the socket which sends the message

    msg hast to be a bytestring

    """

    ip, port = sock.getpeername()
    try:
        logging.info('Send a message to '+ip+':'+str(port))
        # \xDE\xAD\xE1\x1D = DEAD END
        sock.sendall(msg + b'\xDE\xAD\xE1\x1D')
    except:
        raise


########NEW FILE########
__FILENAME__ = control
# -*- coding: utf-8 -*-
'''
Copyright (C) 2012-2013 Karsten-Kai König <kkoenig@posteo.de>

This file is part of keepassc.

keepassc is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or at your
option) any later version.

keepassc is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with keepassc.  If not, see <http://www.gnu.org/licenses/>.
'''

import curses as cur
import logging
from curses.ascii import NL, DEL, SP
from datetime import date
from os import chdir, getcwd, getenv, geteuid, makedirs, remove
from os.path import expanduser, isfile, isdir, realpath, join
from pwd import getpwuid
from random import sample
from socket import gethostname, socket, AF_INET, SOCK_STREAM, SHUT_RDWR
from sys import exit

from kppy.database import KPDBv1
from kppy.exceptions import KPError

from keepassc.conn import *
from keepassc.client import Client
from keepassc.editor import Editor
from keepassc.helper import parse_config, write_config
from keepassc.filebrowser import FileBrowser
from keepassc.dbbrowser import DBBrowser


class Control(object):
    '''This class represents the whole application.'''
    def __init__(self):
        '''The __init__-method.

        It just initializes some variables and settings and changes
        the working directory to /var/empty to prevent coredumps as
        normal user.

        '''

        try:
            self.config_home = realpath(expanduser(getenv('XDG_CONFIG_HOME')))
        except:
            self.config_home = realpath(expanduser('~/.config'))
        finally:
            self.config_home = join(self.config_home, 'keepassc', 'config')

        try:
            self.data_home = realpath(expanduser(getenv('XDG_DATA_HOME')))
        except:
            self.data_home = realpath(expanduser('~/.local/share/'))
        finally:
            self.data_home = join(self.data_home, 'keepassc')
        self.last_home = join(self.data_home, 'last')
        self.remote_home = join(self.data_home, 'remote')
        self.key_home = join(self.data_home, 'key')

        self.config = parse_config(self)

        if self.config['rem_key'] is False and isfile(self.key_home):
            remove(self.key_home)

        self.initialize_cur()
        self.last_file = None
        self.last_key = None
        self.loginname = getpwuid(geteuid())[0]
        self.hostname = gethostname()
        self.cur_dir = getcwd()
        chdir('/var/empty')
        self.db = None

    def initialize_cur(self):
        '''Method to initialize curses functionality'''

        self.stdscr = cur.initscr()
        try:
            cur.curs_set(0)
        except:
            print('Invisible cursor not supported')
        cur.cbreak()
        cur.noecho()
        self.stdscr.keypad(1)
        cur.start_color()
        cur.use_default_colors()
        cur.init_pair(1, -1, -1)
        cur.init_pair(2, 2, -1)
        cur.init_pair(3, -1, 1)
        cur.init_pair(4, 6, -1)
        cur.init_pair(5, 0, 6)
        cur.init_pair(6, 0, 7)
        cur.init_pair(7, 1, -1)
        self.stdscr.bkgd(1)
        self.ysize, self.xsize = self.stdscr.getmaxyx()

        self.group_win = cur.newwin(self.ysize - 1, int(self.xsize / 3),
                                    1, 0)
        # 11 is the y size of info_win
        self.entry_win = cur.newwin((self.ysize - 1) - 11,
                                    int(2 * self.xsize / 3),
                                    1, int(self.xsize / 3))
        self.info_win = cur.newwin(11,
                                   int(2 * self.xsize / 3),
                                   (self.ysize - 1) - 11,
                                   int(self.xsize / 3))
        self.group_win.keypad(1)
        self.entry_win.keypad(1)
        self.group_win.bkgd(1)
        self.entry_win.bkgd(1)
        self.info_win.bkgd(1)

    def resize_all(self):
        '''Method to resize windows'''

        self.ysize, self.xsize = self.stdscr.getmaxyx()
        self.group_win.resize(self.ysize - 1, int(self.xsize / 3))
        self.entry_win.resize(
            self.ysize - 1 - 11, int(2 * self.xsize / 3))
        self.info_win.resize(11, int(2 * self.xsize / 3))
        self.group_win.mvwin(1, 0)
        self.entry_win.mvwin(1, int(self.xsize / 3))
        self.info_win.mvwin((self.ysize - 1) - 11, int(self.xsize / 3))

    def any_key(self):
        '''If any key is needed.'''

        while True:
            try:
                e = self.stdscr.getch()
            except KeyboardInterrupt:
                e = 4
            if e == 4:
                return -1
            elif e == cur.KEY_RESIZE:
                self.resize_all()
            else:
                return e

    def draw_text(self, changed, *misc):
        '''This method is a wrapper to display some text on stdscr.

        misc is a list that should consist of 3-tuples which holds
        text to display.
        (1st element: y-coordinate, 2nd: x-coordinate, 3rd: text)

        '''

        if changed is True:
            cur_dir = self.cur_dir + '*'
        else:
            cur_dir = self.cur_dir
        try:
            self.stdscr.clear()
            self.stdscr.addstr(
                0, 0, self.loginname + '@' + self.hostname + ':',
                cur.color_pair(2))
            self.stdscr.addstr(
                0, len(self.loginname + '@' + self.hostname + ':'),
                cur_dir)
            for i, j, k in misc:
                self.stdscr.addstr(i, j, k)
        except:  # to prevent a crash if screen is small
            pass
        finally:
            self.stdscr.refresh()

    def draw_help(self, *text):
        """Draw a help

        *text are arbitary string

        """

        if len(text) > self.ysize -1:
            length = self.ysize - 1
            offset = 0
            spill = len(text) - self.ysize + 2
        else:
            length = len(text)
            offset = 0
            spill = 0

        while True:
            try:
                self.draw_text(False)
                for i in range(length):
                    self.stdscr.addstr(
                    i + 1, 0, text[(i + offset)])
            except:
                pass
            finally:
                self.stdscr.refresh()
            try:
                e = self.stdscr.getch()
            except KeyboardInterrupt:
                e = 4

            if e == cur.KEY_DOWN:
                if offset < spill:
                    offset += 1
            elif e == cur.KEY_UP:
                if offset > 0:
                    offset -= 1
            elif e == NL:
                return
            elif e == cur.KEY_RESIZE:
                self.resize_all()
                if len(text) > self.ysize -1:
                    length = self.ysize - 1
                    offset = 0
                    spill = len(text) - self.ysize + 2
                else:
                    length = len(text)
                    offset = 0
                    spill = 0
            elif e == 4:
                if self.db is not None:
                    self.db.close()
                self.close()

    def get_password(self, std, needed=True):
        '''This method is used to get a password.

        The pasword will not be displayed during typing.

        std is a string that should be displayed. If needed is True it
        is not possible to return an emptry string.

        '''
        password = Editor(self.stdscr, max_text_size=1, win_location=(0, 1),
                          win_size=(1, self.xsize), title=std, pw_mode=True)()
        if needed is True and not password:
            return False
        else:
            return password

    def get_authentication(self):
        """Get authentication credentials"""

        while True:
            if (self.config['skip_menu'] is False or
                (self.config['rem_db'] is False and
                 self.config['rem_key'] is False)):
                auth = self.gen_menu(1, (
                                     (1, 0, 'Use a password (1)'),
                                     (2, 0, 'Use a keyfile (2)'),
                                     (3, 0, 'Use both (3)')),
                                    (5, 0, 'Press \'F5\' to go back to main '
                                           'menu'))
            else:
                self.draw_text(False)
                auth = 3
            if auth is False:
                return False
            elif auth == -1:
                self.close()
            if auth == 1 or auth == 3:
                if self.config['skip_menu'] is True:
                    needed = False
                else:
                    needed = True
                password = self.get_password('Password: ', needed = needed)
                if password is False:
                    self.config['skip_menu'] = False
                    continue
                elif password == -1:
                    self.close()
                # happens only if self.config['skip_menu'] is True
                elif password == "":
                    password = None
                if auth != 3:
                    keyfile = None
            if auth == 2 or auth == 3:
                # Ugly construct but works
                # "if keyfile is False" stuff is needed to implement the
                # return to previous screen stuff
                # Use similar constructs elsewhere
                while True:
                    self.get_last_key()
                    if (self.last_key is None or
                            self.config['rem_key'] is False):
                        ask_for_lf = False
                    else:
                        ask_for_lf = True

                    keyfile = FileBrowser(self, ask_for_lf, True, 
                                          self.last_key)()
                    if keyfile is False:
                        break
                    elif keyfile == -1:
                        self.close()
                    elif not isfile(keyfile):
                        self.draw_text(False,
                                       (1, 0, 'That\'s not a file'),
                                       (3, 0, 'Press any key.'))
                        if self.any_key() == -1:
                            self.close()
                        continue
                    break
                if keyfile is False:
                    continue
                if auth != 3:
                    password = None
                if self.config['rem_key'] is True:
                    if not isdir(self.key_home[:-4]):
                        if isfile(self.key_home[:-4]):
                            remove(self.key_home[:-4])
                        makedirs(self.key_home[:-4])
                    handler = open(self.key_home, 'w')
                    handler.write(keyfile)
                    handler.close()
            break
        return (password, keyfile)

    def get_last_db(self):
        if isfile(self.last_home) and self.config['rem_db'] is False:
            remove(self.last_home)
            self.last_file = None
        elif isfile(self.last_home):
            try:
                handler = open(self.last_home, 'r')
            except Exception as err:
                self.last_file = None
                print(err.__str__())
            else:
                self.last_file = handler.readline()
                handler.close()
        else:
            self.last_file = None

    def get_last_key(self):
        if isfile(self.key_home) and self.config['rem_key'] is False:
            remove(self.key_home)
            self.last_key = None
        elif isfile(self.key_home):
            try:
                handler = open(self.key_home, 'r')
            except Exception as err:
                self.last_key = None
                print(err.__str__())
            else:
                self.last_key = handler.readline()
                handler.close()
        else:
            self.last_key = None

    def gen_pass(self):
        '''Method to generate a password'''

        while True:
            items = self.gen_check_menu(((1, 0, 'Include numbers'),
                                         (2, 0,
                                          'Include capitalized letters'),
                                         (3, 0, 'Include special symbols')),
                                        (5, 0, 'Press space to un-/check'),
                                        (6, 0,
                                         'Press return to enter options'))
            if items is False or items == -1:
                return items
            length = self.get_num('Password length: ')
            if length is False:
                continue
            elif length == -1:
                return -1
            char_set = 'abcdefghijklmnopqrstuvwxyz'
            if items[0] == 1:
                char_set += '1234567890'
            if items[1] == 1:
                char_set += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            if items[2] == 1:
                char_set += '!"#$%& \'()*+,-./:;<=>?@[\\]^_`{|}~$§'

            password = ''
            for _ in range(length):
                password += sample(char_set, 1)[0]
            return password

    def get_exp_date(self, *exp):
        '''This method is used to get an expiration date for entries.

        exp is used to display an actual expiration date.

        '''

        pass_y = False
        pass_mon = False
        goto_last = False
        while True:
            if pass_y is False:
                edit = ''
                e = cur.KEY_BACKSPACE
                while e != NL:
                    if (e == cur.KEY_BACKSPACE or e == DEL) and len(edit) != 0:
                        edit = edit[:-1]
                    elif e == cur.KEY_BACKSPACE or e == DEL:
                        pass
                    elif e == 4:
                        return -1
                    elif e == cur.KEY_RESIZE:
                        self.resize_all()
                    elif e == cur.KEY_F5:
                        return False
                    elif len(edit) < 4 and e >= 48 and e <= 57:
                        edit += chr(e)
                    self.draw_text(False,
                                   (1, 0, 'Special date 2999-12-28 means that '
                                    'the expires never.'),
                                   (3, 0, 'Year: ' + edit))
                    if exp:
                        try:
                            self.stdscr.addstr(2, 0,
                                               'Actual expiration date: ' +
                                               str(exp[0]) + '-' +
                                               str(exp[1]) + '-' +
                                               str(exp[2]))
                        except:
                            pass
                        finally:
                            self.stdscr.refresh()
                    try:
                        e = self.stdscr.getch()
                    except KeyboardInterrupt:
                        e = 4
                    if e == NL and edit == '':
                        e = cur.KEY_BACKSPACE
                        continue
                y = int(edit)
                pass_y = True

            if pass_mon is False:
                edit = ''
                e = cur.KEY_BACKSPACE
                while e != NL:
                    if (e == cur.KEY_BACKSPACE or e == DEL) and len(edit) != 0:
                        edit = edit[:-1]
                    elif e == cur.KEY_BACKSPACE or e == DEL:
                        pass
                    elif e == 4:
                        return -1
                    elif e == cur.KEY_RESIZE:
                        self.resize_all()
                    elif e == cur.KEY_F5:
                        pass_y = False
                        goto_last = True
                        break
                    elif len(edit) < 2 and e >= 48 and e <= 57:
                        edit += chr(e)
                    self.draw_text(False,
                                   (1, 0, 'Special date 2999-12-28 means that '
                                    'the expires never.'),
                                   (3, 0, 'Year: ' + str(y)),
                                   (4, 0, 'Month: ' + edit))
                    if exp:
                        try:
                            self.stdscr.addstr(2, 0,
                                               'Actual expiration date: ' +
                                               str(exp[0]) + '-' +
                                               str(exp[1]) + '-' +
                                               str(exp[2]))
                        except:
                            pass
                        finally:
                            self.stdscr.refresh()
                    try:
                        e = self.stdscr.getch()
                    except KeyboardInterrupt:
                        e = 4

                    if e == NL and edit == '':
                        e = cur.KEY_BACKSPACE
                        continue
                    elif e == NL and (int(edit) > 12 or int(edit) < 1):
                        self.draw_text(False,
                                       (1, 0,
                                        'Month must be between 1 and 12. '
                                        'Press any key.'))
                        if self.any_key() == -1:
                            return -1
                        e = ''
                if goto_last is True:
                    goto_last = False
                    continue
                mon = int(edit)
                pass_mon = True

            edit = ''
            e = cur.KEY_BACKSPACE
            while e != NL:
                if (e == cur.KEY_BACKSPACE or e == DEL) and len(edit) != 0:
                    edit = edit[:-1]
                elif e == cur.KEY_BACKSPACE or e == DEL:
                    pass
                elif e == 4:
                    return -1
                elif e == cur.KEY_RESIZE:
                    self.resize_all()
                elif e == cur.KEY_F5:
                    pass_mon = False
                    goto_last = True
                    break
                elif len(edit) < 2 and e >= 48 and e <= 57:
                    edit += chr(e)
                self.draw_text(False,
                               (1, 0, 'Special date 2999-12-28 means that the '
                                'expires never.'),
                               (3, 0, 'Year: ' + str(y)),
                               (4, 0, 'Month: ' + str(mon)),
                               (5, 0, 'Day: ' + edit))
                if exp:
                    try:
                        self.stdscr.addstr(2, 0, 'Actual expiration date: ' +
                                           str(exp[0]) + '-' +
                                           str(exp[1]) + '-' +
                                           str(exp[2]))
                    except:
                        pass
                    finally:
                        self.stdscr.refresh()
                try:
                    e = self.stdscr.getch()
                except KeyboardInterrupt:
                    e = 4

                if e == NL and edit == '':
                    e = cur.KEY_BACKSPACE
                    continue
                elif (e == NL and (mon == 1 or mon == 3 or mon == 5 or
                                   mon == 7 or mon == 8 or mon == 10 or
                                   mon == 12) and
                      (int(edit) > 31 or int(edit) < 0)):
                    self.draw_text(False,
                                   (1, 0,
                                    'Day must be between 1 and 31. Press '
                                    'any key.'))
                    if self.any_key() == -1:
                        return -1
                    e = ''
                elif (e == NL and mon == 2 and (int(edit) > 28 or
                                                int(edit) < 0)):
                    self.draw_text(False,
                                   (1, 0,
                                    'Day must be between 1 and 28. Press '
                                    'any key.'))
                    if self.any_key() == -1:
                        return -1
                    e = ''
                elif (e == NL and (mon == 4 or mon == 6 or mon == 9 or
                      mon == 11) and (int(edit) > 30 or int(edit) < 0)):
                    self.draw_text(False,
                                   (1, 0,
                                    'Day must be between 1 and 30. Press '
                                    'any key.'))
                    if self.any_key() == -1:
                        return -1
                    e = ''
            if goto_last is True:
                goto_last = False
                pass_mon = False
                continue
            d = int(edit)
            break
        return (y, mon, d)

    def get_num(self, std='', edit='', length=4):
        '''Method to get a number'''

        edit = edit
        e = 60 # just an unrecognized letter
        while e != NL:
            if (e == cur.KEY_BACKSPACE or e == DEL) and len(edit) != 0:
                edit = edit[:-1]
            elif e == cur.KEY_BACKSPACE or e == DEL:
                pass
            elif e == 4:
                return -1
            elif e == cur.KEY_RESIZE:
                self.resize_all()
            elif e == cur.KEY_F5:
                return False
            elif len(edit) < length and e >= 48 and e <= 57:
                edit += chr(e)
            self.draw_text(False,
                           (1, 0, std + edit))
            try:
                e = self.stdscr.getch()
            except KeyboardInterrupt:
                e = 4
            if e == NL and edit == '':
                e = cur.KEY_BACKSPACE
                continue
        return int(edit)

    def gen_menu(self, highlight, misc, *add):
        '''A universal method to generate a menu.

        misc is a tupel of triples (y, x, 'text')

        add are more tuples but the content should not be accessable

        '''

        if len(misc) == 0:
            return False
        h_color = 6
        n_color = 1
        e = ''
        while e != NL:
            try:
                self.stdscr.clear()
                self.stdscr.addstr(
                    0, 0, self.loginname + '@' + self.hostname + ':',
                    cur.color_pair(2))
                self.stdscr.addstr(0,
                                   len(self.loginname +
                                       '@' + self.hostname + ':'),
                                   self.cur_dir)
                for i, j, k in misc:
                    if i == highlight:
                        self.stdscr.addstr(i, j, k, cur.color_pair(h_color))
                    else:
                        self.stdscr.addstr(i, j, k, cur.color_pair(n_color))
                for i, j, k in add:
                    self.stdscr.addstr(i, j, k)
            except:
                pass
            finally:
                self.stdscr.refresh()
            try:
                e = self.stdscr.getch()
            except KeyboardInterrupt:
                e = 4
            if e == 4:
                return -1
            elif e == cur.KEY_RESIZE:
                self.resize_all()
            elif e == cur.KEY_F5:
                return False
            elif e == NL:
                return highlight
            elif (e == cur.KEY_DOWN or e == ord('j')) and highlight < len(misc):
                highlight += 1
            elif (e == cur.KEY_UP or e == ord('k')) and highlight > 1:
                highlight -= 1
            elif 49 <= e <= 48 + len(misc):  # ASCII(49) = 1 ...
                return e - 48

    def gen_check_menu(self, misc, *add):
        '''Print a menu with checkable entries'''

        if len(misc) == 0:
            return False
        items = []
        for i in range(len(misc)):
            items.append(0)
        highlight = 1
        h_color = 6
        n_color = 1
        e = ''
        while e != NL:
            try:
                self.stdscr.clear()
                self.stdscr.addstr(
                    0, 0, self.loginname + '@' + self.hostname + ':',
                    cur.color_pair(2))
                self.stdscr.addstr(0,
                                   len(self.loginname +
                                       '@' + self.hostname + ':'),
                                   self.cur_dir)
                for i, j, k in misc:
                    if items[i - 1] == 0:
                        check = '[ ]'
                    else:
                        check = '[X]'
                    if i == highlight:
                        self.stdscr.addstr(
                            i, j, check + k, cur.color_pair(h_color))
                    else:
                        self.stdscr.addstr(
                            i, j, check + k, cur.color_pair(n_color))
                for i, j, k in add:
                    self.stdscr.addstr(i, j, k)
            except:
                pass
            finally:
                self.stdscr.refresh()
            try:
                e = self.stdscr.getch()
            except KeyboardInterrupt:
                e = 4
            if e == 4:
                return -1
            elif e == cur.KEY_RESIZE:
                self.resize_all()
            elif e == cur.KEY_F5:
                return False
            elif e == SP:
                if items[highlight - 1] == 0:
                    items[highlight - 1] = 1
                else:
                    items[highlight - 1] = 0
            elif (e == cur.KEY_DOWN or e == ord('j')) and highlight < len(misc):
                highlight += 1
            elif (e == cur.KEY_UP or e == ord('k')) and highlight > 1:
                highlight -= 1
            elif e == NL:
                return items

    def gen_config_menu(self):
        '''The configuration menu'''

        self.config = parse_config(self)
        menu = 1
        while True:
            menu = self.gen_menu(menu,
                ((1, 0, 'Delete clipboard automatically: ' +
                  str(self.config['del_clip'])),
                 (2, 0, 'Waiting time (seconds): ' +
                  str(self.config['clip_delay'])),
                 (3, 0, 'Lock database automatically: ' +
                  str(self.config['lock_db'])),
                 (4, 0, 'Waiting time (seconds): ' +
                  str(self.config['lock_delay'])),
                 (5, 0, 'Remember last database: ' +
                  str(self.config['rem_db'])),
                 (6, 0, 'Remember last keyfile: ' +
                  str(self.config['rem_key'])),
                 (7, 0, 'Use directly password and key if one of the two '
                        'above is True: ' +
                  str(self.config['skip_menu'])),
                 (8, 0, 'Pin server certificate: ' + str(self.config['pin'])),
                 (9, 0, 'Generate default configuration'),
                 (10, 0, 'Write config')),
                (12, 0, 'Automatic locking works only for saved databases!'))
            if menu == 1:
                if self.config['del_clip'] is True:
                    self.config['del_clip'] = False
                elif self.config['del_clip'] is False:
                    self.config['del_clip'] = True
            elif menu == 2:
                delay = self.get_num('Waiting time: ',
                                     str(self.config['clip_delay']))
                if delay is False:
                    continue
                elif delay == -1:
                    self.close()
                else:
                    self.config['clip_delay'] = delay
            elif menu == 3:
                if self.config['lock_db'] is True:
                    self.config['lock_db'] = False
                elif self.config['lock_db'] is False:
                    self.config['lock_db'] = True
            elif menu == 4:
                delay = self.get_num('Waiting time: ',
                                     str(self.config['lock_delay']))
                if delay is False:
                    continue
                elif delay == -1:
                    self.close()
                else:
                    self.config['lock_delay'] = delay
            elif menu == 5:
                if self.config['rem_db'] is True:
                    self.config['rem_db'] = False
                elif self.config['rem_db'] is False:
                    self.config['rem_db'] = True
            elif menu == 6:
                if self.config['rem_key'] is True:
                    self.config['rem_key'] = False
                elif self.config['rem_key'] is False:
                    self.config['rem_key'] = True
            elif menu == 7:
                if self.config['skip_menu'] is True:
                    self.config['skip_menu'] = False
                elif self.config['skip_menu'] is False:
                    self.config['skip_menu'] = True
            elif menu == 8:
                if self.config['pin'] is True:
                    self.config['pin'] = False
                elif self.config['pin'] is False:
                    self.config['pin'] = True
            elif menu == 9:
                self.config = {'del_clip': True,  # standard config
                               'clip_delay': 20,
                               'lock_db': True,
                               'lock_delay': 60,
                               'rem_db': True,
                               'rem_key': False,
                               'skip_menu': False,
                               'pin': True}
            elif menu == 10:
                write_config(self, self.config)
                return True
            elif menu is False:
                return False
            elif menu == -1:
                self.close()

    def draw_lock_menu(self, changed, highlight, *misc):
        '''Draw menu for locked database'''

        h_color = 6
        n_color = 1
        if changed is True:
            cur_dir = self.cur_dir + '*'
        else:
            cur_dir = self.cur_dir
        try:
            self.stdscr.clear()
            self.stdscr.addstr(
                0, 0, self.loginname + '@' + self.hostname + ':',
                cur.color_pair(2))
            self.stdscr.addstr(
                0, len(self.loginname + '@' + self.hostname + ':'),
                cur_dir)
            for i, j, k in misc:
                if i == highlight:
                    self.stdscr.addstr(i, j, k, cur.color_pair(h_color))
                else:
                    self.stdscr.addstr(i, j, k, cur.color_pair(n_color))
        #except: # to prevent a crash if screen is small
        #    pass
        finally:
            self.stdscr.refresh()

    def main_loop(self, kdb_file=None, remote = False):
        '''The main loop. The program alway return to this method.'''

        if remote is True:
            self.remote_interface()
        else:
            # This is needed to remember last database and open it directly
            self.get_last_db()

            if kdb_file is not None:
                self.cur_dir = kdb_file
                if self.open_db(True) is True:
                    db = DBBrowser(self)
                    del db
                    last = self.cur_dir.split('/')[-1]
                    self.cur_dir = self.cur_dir[:-len(last) - 1]
            elif self.last_file is not None and self.config['rem_db'] is True:
                self.cur_dir = self.last_file
                if self.open_db(True) is True:
                    db = DBBrowser(self)
                    del db
                    last = self.cur_dir.split('/')[-1]
                    self.cur_dir = self.cur_dir[:-len(last) - 1]

        while True:
            self.get_last_db()
            menu = self.gen_menu(1, ((1, 0, 'Open existing database (1)'),
                                  (2, 0, 'Create new database (2)'),
                                  (3, 0, 'Connect to a remote database(3)'),
                                  (4, 0, 'Configuration (4)'),
                                  (5, 0, 'Quit (5)')),
                                 (7, 0, 'Type \'F1\' for help inside the file '
                                        'or database browser.'),
                                 (8, 0, 'Type \'F5\' to return to the previous'
                                        ' dialog at any time.'))
            if menu == 1:
                if self.open_db() is False:
                    continue
                db = DBBrowser(self)
                del db
                last = self.cur_dir.split('/')[-1]
                self.cur_dir = self.cur_dir[:-len(last) - 1]
            elif menu == 2:
                while True:
                    auth = self.gen_menu(1, (
                                         (1, 0, 'Use a password (1)'),
                                         (2, 0, 'Use a keyfile (2)'),
                                         (3, 0, 'Use both (3)')))
                    password = None
                    confirm = None
                    filepath = None
                    self.db = KPDBv1(new=True)
                    if auth is False:
                        break
                    elif auth == -1:
                        self.db = None
                        self.close()
                    if auth == 1 or auth == 3:
                        while True:
                            password = self.get_password('Password: ')
                            if password is False:
                                break
                            elif password == -1:
                                self.db = None
                                self.close()
                            confirm = self.get_password('Confirm: ')
                            if confirm is False:
                                break
                            elif confirm == -1:
                                self.db = None
                                self.close()
                            if password == confirm:
                                self.db.password = password
                                break
                            else:
                                self.draw_text(False,
                                               (1, 0,
                                                'Passwords didn\' match!'),
                                               (3, 0, 'Press any key'))
                                if self.any_key() == -1:
                                    self.db = None
                                    self.close()
                        if auth != 3:
                            self.db.keyfile = None
                    if password is False or confirm is False:
                        continue
                    if auth == 2 or auth == 3:
                        while True:
                            filepath = FileBrowser(self, False, True, None)()
                            if filepath is False:
                                break
                            elif filepath == -1:
                                self.close()
                            elif not isfile(filepath):
                                self.draw_text(False,
                                               (1, 0, 'That\' not a file!'),
                                               (3, 0, 'Press any key'))
                                if self.any_key() == -1:
                                    self.db = None
                                    self.close()
                                continue
                            break
                        if filepath is False:
                            continue
                        self.db.keyfile = filepath
                        if auth != 3:
                            self.db.password = None

                    if auth is not False:
                        db = DBBrowser(self)
                        del db
                        last = self.cur_dir.split('/')[-1]
                        self.cur_dir = self.cur_dir[:-len(last) - 1]
                    else:
                        self.db = None
                    break
            elif menu == 3:
                self.remote_interface()
            elif menu == 4:
                self.gen_config_menu()
            elif menu == 5 or menu is False or menu == -1:
                self.close()

    def open_db(self, skip_fb=False):
        ''' This method opens a database.'''

        if skip_fb is False:
            filepath = FileBrowser(self, True, False, self.last_file)()
            if filepath is False:
                return False
            elif filepath == -1:
                self.close()
            else:
                self.cur_dir = filepath

        ret = self.get_authentication()
        if ret is False:
            return False
        password, keyfile = ret

        try:
            if isfile(self.cur_dir + '.lock'):
                self.draw_text(False,
                               (1, 0, 'Database seems to be opened.'
                                ' Open file in read-only mode?'
                                ' [(y)/n]'))
                while True:
                    try:
                        e = self.stdscr.getch()
                    except KeyboardInterrupt:
                        e = 4

                    if e == ord('n'):
                        read_only = False
                        break
                    elif e == 4:
                        self.close()
                    elif e == cur.KEY_RESIZE:
                        self.resize_all()
                    elif e == cur.KEY_F5:
                        return False
                    else:
                        read_only = True
                        break
            else:
                read_only = False
            self.db = KPDBv1(self.cur_dir, password, keyfile, read_only)
            self.db.load()
            return True
        except KPError as err:
            self.draw_text(False,
                           (1, 0, err.__str__()),
                           (4, 0, 'Press any key.'))
            if self.any_key() == -1:
                self.close()
            last = self.cur_dir.split('/')[-1]
            self.cur_dir = self.cur_dir[:-len(last) - 1]
            return False

    def remote_interface(self, ask_for_agent = True, agent = False):
        if ask_for_agent is True and agent is False:
            use_agent = self.gen_menu(1, ((1, 0, 'Use agent (1)'),
                                          (2, 0, 'Use no agent (2)')))
        elif agent is True:
            use_agent = 1
        else:
            use_agent = 2

        if use_agent == 1:
            port = self.get_num("Agent port: ", "50001", 5)
            if port is False:
                return False
            elif port == -1:
                self.close()

            sock = socket(AF_INET, SOCK_STREAM)
            sock.settimeout(60)
            try:
                sock.connect(('localhost', port))
                sendmsg(sock, build_message((b'GET',)))
            except OSError as err:
                self.draw_text(False, (1, 0, err.__str__()),
                                      (3, 0, "Press any key."))
                if self.any_key() == -1:
                    self.close()
                return False

            db_buf = receive(sock)
            if db_buf[:4] == b'FAIL' or db_buf[:4] == b'[Err':
                self.draw_text(False,
                               (1, 0, db_buf),
                               (3, 0, 'Press any key.'))
                if self.any_key() == -1:
                    self.close()
                return False
            sock.shutdown(SHUT_RDWR)
            sock.close()

            sock = socket(AF_INET, SOCK_STREAM)
            sock.settimeout(60)
            try:
                sock.connect(('localhost', port))
                sendmsg(sock, build_message((b'GETC',)))
            except OSError as err:
                self.draw_text(False, (1, 0, err.__str__()),
                                      (3, 0, "Press any key."))
                if self.any_key() == -1:
                    self.close()
                return False

            answer = receive(sock)
            parts = answer.split(b'\xB2\xEA\xC0')
            password = parts.pop(0).decode()
            keyfile_cont = parts.pop(0).decode()
            if keyfile_cont == '':
                keyfile = None
            else:
                if not isdir('/tmp/keepassc'):
                    makedirs('/tmp/keepassc')
                with open('/tmp/keepassc/tmp_keyfile', 'w') as handler:
                    handler.write(parts.pop(0).decode())
                    keyfile = '/tmp/keepassc/tmp_keyfile'

            server = parts.pop(0).decode()
            port = int(parts.pop(0))
            if parts.pop(0) == b'True':
                ssl = True
            else:
                ssl = False
            tls_dir = parts.pop(0).decode()
        elif use_agent is False:
            return False
        elif use_agent == -1:
            self.close()
        else:
            if isfile(self.remote_home):
                with open(self.remote_home, 'r') as handler:
                    last_address = handler.readline()
                    last_port = handler.readline()
            else:
                last_address = '127.0.0.1'
                last_port = None

            pass_auth = False
            pass_ssl = False
            while True:
                if pass_auth is False:
                    ret = self.get_authentication()
                    if ret is False:
                        return False
                    elif ret == -1:
                        self.close()
                    password, keyfile = ret
                pass_auth = True
                if pass_ssl is False:
                    ssl = self.gen_menu(1, ((1, 0, 'Use SSL/TLS (1)'),
                                            (2, 0, 'Plain text (2)')))
                    if ssl is False:
                        pass_auth = False
                        continue
                    elif ssl == -1:
                        self.close()
                pass_ssl = True
                server = Editor(self.stdscr, max_text_size=1,
                                inittext=last_address,
                                win_location=(0, 1),
                                win_size=(1, self.xsize),
                                title="Server address")()
                if server is False:
                    pass_ssl = False
                    continue
                elif server == -1:
                    self.close()
                if last_port is None:
                    if ssl == 1:
                        ssl = True # for later use
                        std_port = "50003"
                    else:
                        ssl = False
                        std_port = "50000"
                else:
                    if ssl == 1:
                        ssl = True # for later use
                    else:
                        ssl = False
                    std_port = last_port

                port = self.get_num("Server port: ", std_port, 5)
                if port is False:
                    path_auth = True
                    path_ssl = True
                    continue
                elif port == -1:
                    self.close()
                break

            if ssl is True:
                try:
                    datapath = realpath(expanduser(getenv('XDG_DATA_HOME')))
                except:
                    datapath = realpath(expanduser('~/.local/share'))
                finally:
                    tls_dir = join(datapath, 'keepassc')
            else:
                tls_dir = None

            client = Client(logging.INFO, 'client.log', server, port,
                            password, keyfile, ssl, tls_dir)
            db_buf = client.get_db()
            if db_buf[:4] == 'FAIL' or db_buf[:4] == "[Err":
                self.draw_text(False,
                               (1, 0, db_buf),
                               (3, 0, 'Press any key.'))
                if self.any_key() == -1:
                    self.close()
                return False
        self.db = KPDBv1(None, password, keyfile)
        self.db.load(db_buf)
        db = DBBrowser(self, True, server, port, ssl, tls_dir)
        del db
        return True

    def browser_help(self, mode_new):
        '''Print help for filebrowser'''

        if mode_new:
            self.draw_help(
            'Navigate with arrow keys.',
            '\'o\' - choose directory',
            '\'e\' - abort',
            '\'H\' - show/hide hidden files',
            '\'ngg\' - move to line n',
            '\'G\' - move to last line',
            '/text - go to \'text\' (like in vim/ranger)',
            '\n',
            'Press return.')
        else:
            self.draw_help(
            'Navigate with arrow keys.',
            '\'q\' - close program',
            '\'e\' - abort',
            '\'H\' - show/hide hidden files',
            '\'ngg\' - move to line n',
            '\'G\' - move to last line',
            '/text - go to \'text\' (like in vim/ranger)',
            '\n',
            'Press return.')

    def dbbrowser_help(self):
        self.draw_help(
        '\'e\' - go to main menu',
        '\'q\' - close program',
        '\'CTRL+D\' or \'CTRL+C\' - close program at any time',
        '\'x\' - save db and close program',
        '\'s\' - save db',
        '\'S\' - save db with alternative filepath',
        '\'c\' - copy password of current entry',
        '\'b\' - copy username of current entry',
        '\'H\' - show password of current entry',
        '\'o\' - open URL of entry in standard webbrowser',
        '\'P\' - edit db password',
        '\'g\' - create group',
        '\'G\' - create subgroup',
        '\'y\' - create entry',
        '\'d\' - delete group or entry (depends on what is marked)',
        '\'t\' - edit title of selected group or entry',
        '\'u\' - edit username',
        '\'p\' - edit password',
        '\'U\' - edit URL',
        '\'C\' - edit comment',
        '\'E\' - edit expiration date',
        '\'f\' or \'/\' - find entry by title',
        '\'L\' - lock db',
        '\'m\' - enter move mode for marked group or entry',
        '\'r\' - reload remote database (no function if not remote)',
        'Navigate with arrow keys or h/j/k/l like in vim',
        'Type \'return\' to enter subgroups',
        'Type \'backspace\' to go back to parent',
        'Type \'F5\' in a dialog to return to the previous one',
        '\n',
        'Press return.')

    def move_help(self):
        self.draw_help(
        '\'e\' - go to main menu',
        '\'q\' - close program',
        '\'CTRL+D\' or \'CTRL+C\' - close program at any time',
        'Navigate up or down with arrow keys or k and j',
        'Navigate to subgroup with right arrow key or h',
        'Navigate to parent with left arrow key or l',
        'Type \'return\' to move the group to marked parent or the entry',
        '\tto the marked group',
        'Type \'backspace\' to move a group to the root',
        'Type \'ESC\' to abort moving',
        '\n',
        'Press return.')

    def show_dir(self, highlight, dir_cont):
        '''List a directory with highlighting.'''

        self.draw_text(changed=False)
        for i in range(len(dir_cont)):
            if i == highlight:
                if isdir(self.cur_dir + '/' + dir_cont[i]):
                    try:
                        self.stdscr.addstr(
                            i + 1, 0, dir_cont[i], cur.color_pair(5))
                    except:
                        pass
                else:
                    try:
                        self.stdscr.addstr(
                            i + 1, 0, dir_cont[i], cur.color_pair(3))
                    except:
                        pass
            else:
                if isdir(self.cur_dir + '/' + dir_cont[i]):
                    try:
                        self.stdscr.addstr(
                            i + 1, 0, dir_cont[i], cur.color_pair(4))
                    except:
                        pass
                else:
                    try:
                        self.stdscr.addstr(i + 1, 0, dir_cont[i])
                    except:
                        pass
        self.stdscr.refresh()

    def close(self):
        '''Close the program correctly.'''

        if self.config['rem_key'] is False and isfile(self.key_home):
            remove(self.key_home)
        cur.nocbreak()
        self.stdscr.keypad(0)
        cur.endwin()
        exit()

    def show_groups(self, highlight, groups, cur_win, offset, changed, parent):
        '''Just print all groups in a column'''

        self.draw_text(changed)
        self.group_win.clear()
            
        if parent is self.db.root_group:
            root_title = 'Parent: _ROOT_'
        else:
            root_title = 'Parent: ' + parent.title
        if cur_win == 0:
            h_color = 5
            n_color = 4
        else:
            h_color = 6
            n_color = 1

        try:
            ysize = self.group_win.getmaxyx()[0]
            self.group_win.addstr(0, 0, root_title,
                                  cur.color_pair(n_color))
            if groups:
                if len(groups) <= ysize - 3:
                    num = len(groups)
                else:
                    num = ysize - 3

                for i in range(num):
                    if highlight == i + offset:
                        if groups[i + offset].children:
                            title = '+' + groups[i + offset].title
                        else:
                            title = ' ' + groups[i + offset].title
                        self.group_win.addstr(i + 1, 0, title,
                                              cur.color_pair(h_color))
                    else:
                        if groups[i + offset].children:
                            title = '+' + groups[i + offset].title
                        else:
                            title = ' ' + groups[i + offset].title
                        self.group_win.addstr(i + 1, 0, title,
                                              cur.color_pair(n_color))
                x_of_n = str(highlight + 1) + ' of ' + str(len(groups))
                self.group_win.addstr(ysize - 2, 0, x_of_n)
        except:
            pass
        finally:
            self.group_win.refresh()

    def show_entries(self, e_highlight, entries, cur_win, offset):
        '''Just print all entries in a column'''

        self.info_win.clear()
        try:
            self.entry_win.clear()
            if entries:
                if cur_win == 1:
                    h_color = 5
                    n_color = 4
                else:
                    h_color = 6
                    n_color = 1

                ysize = self.entry_win.getmaxyx()[0]
                if len(entries) <= ysize - 3:
                    num = len(entries)
                else:
                    num = ysize - 3

                for i in range(num):
                    title = entries[i + offset].title
                    if date.today() > entries[i + offset].expire.date():
                        expired = True
                    else:
                        expired = False
                    if e_highlight == i + offset:
                        if expired is True:
                            self.entry_win.addstr(i, 2, title,
                                                  cur.color_pair(3))
                        else:
                            self.entry_win.addstr(i, 2, title,
                                                  cur.color_pair(h_color))
                    else:
                        if expired is True:
                            self.entry_win.addstr(i, 2, title,
                                                  cur.color_pair(7))
                        else:
                            self.entry_win.addstr(i, 2, title,
                                                  cur.color_pair(n_color))
                self.entry_win.addstr(ysize - 2, 2, (str(e_highlight + 1) +
                                                     ' of ' +
                                                     str(len(entries))))
        except:
            pass
        finally:
            self.entry_win.noutrefresh()

        try:
            if entries:
                xsize = self.entry_win.getmaxyx()[1]
                entry = entries[e_highlight]
                if entry.title is None:
                    title = ""
                elif len(entry.title) > xsize:
                    title = entry.title[:xsize - 2] + '\\'
                else:
                    title = entry.title
                if entry.group.title is None:
                    group_title = ""
                elif len(entry.group.title) > xsize:
                    group_title = entry.group.title[:xsize - 9] + '\\'
                else:
                    group_title = entry.group.title
                if entry.username is None:
                    username = ""
                elif len(entry.username) > xsize:
                    username = entry.username[:xsize - 12] + '\\'
                else:
                    username = entry.username
                if entry.url is None:
                    url = ""
                elif len(entry.url) > xsize:
                    url = entry.title[:xsize - 7] + '\\'
                else:
                    url = entry.url
                if entry.creation is None:
                    creation = ""
                else:
                    creation = entry.creation.__str__()[:10]
                if entry.last_access is None:
                    last_access = ""
                else:
                    last_access = entry.last_access.__str__()[:10]
                if entry.last_mod is None:
                    last_mod = ""
                else:
                    last_mod = entry.last_mod.__str__()[:10]
                if entry.expire is None:
                    expire = ""
                else:
                    if entry.expire.__str__()[:19] == '2999-12-28 23:59:59':
                        expire = "Expires: Never"
                    else:
                        expire = "Expires: " + entry.expire.__str__()[:10]
                if entry.comment is None:
                    comment = ""
                else:
                    comment = entry.comment

                self.info_win.addstr(2, 0, title, cur.A_BOLD)
                self.info_win.addstr(3, 0, "Group: " + group_title)
                self.info_win.addstr(4, 0, "Username: " + username)
                self.info_win.addstr(5, 0, "URL: " + url)
                self.info_win.addstr(6, 0, "Creation: " + creation)
                self.info_win.addstr(7, 0, "Access: " + last_access)
                self.info_win.addstr(8, 0, "Modification: " + last_mod)
                self.info_win.addstr(9, 0, expire)
                if date.today() > entry.expire.date():
                    self.info_win.addstr(9, 22, ' (expired)')
                if '\n' in comment:
                    comment = comment.split('\n')[0]
                    dots = ' ...'
                else:
                    dots = ''
                self.info_win.addstr(10, 0, "Comment: " + comment + dots)
        except:
            pass
        finally:
            self.info_win.noutrefresh()
        cur.doupdate()

########NEW FILE########
__FILENAME__ = daemon
'''
Copyright (C) 2012-2013 Karsten-Kai König <kkoenig@posteo.de>

This file is part of keepassc.

keepassc is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or at your
option) any later version.

keepassc is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with keepassc.  If not, see <http://www.gnu.org/licenses/>.
'''

import sys
import os
import time
import atexit
import signal

class Daemon(object):
    """A generic daemon class.

    Usage: subclass the daemon class and override the run() method."""

    def __init__(self, pidfile): self.pidfile = pidfile

    def daemonize(self):
        """Deamonize class. UNIX double fork mechanism."""

        try: 
            pid = os.fork() 
            if pid > 0:
                # exit first parent
                sys.exit(0) 
        except OSError as err: 
            sys.stderr.write('fork #1 failed: {0}\n'.format(err))
            sys.exit(1)
    
        # decouple from parent environment
        os.chdir('/') 
        os.setsid() 
        os.umask(0) 
    
        # do second fork
        try: 
            pid = os.fork() 
            if pid > 0:

                # exit from second parent
                sys.exit(0) 
        except OSError as err: 
            sys.stderr.write('fork #2 failed: {0}\n'.format(err))
            sys.exit(1) 
    
        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(os.devnull, 'r')
        so = open(os.devnull, 'a+')
        se = open(os.devnull, 'a+')

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
        # write pidfile
        atexit.register(self.delpid)

        pid = str(os.getpid())
        with open(self.pidfile,'w+') as f:
            f.write(pid + '\n')
        
    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        """Start the daemon."""

        # Check for a pidfile to see if the daemon already runs
        try:
            with open(self.pidfile,'r') as pf:

                pid = int(pf.read().strip())
        except IOError:
            pid = None
    
        if pid:
            message = "pidfile {0} already exist. " + \
                    "Daemon already running?\n"
            sys.stderr.write(message.format(self.pidfile))
            sys.exit(1)
        
        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """Stop the daemon."""

        # Get the pid from the pidfile
        try:
            with open(self.pidfile,'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None
    
        if not pid:
            message = "pidfile {0} does not exist. " + \
                    "Daemon not running?\n"
            sys.stderr.write(message.format(self.pidfile))
            return # not an error in a restart

        # Try killing the daemon process    
        try:
            while 1:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            e = str(err.args)
            if e.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print (str(err.args))
                sys.exit(1)

    def restart(self):
        """Restart the daemon."""
        self.stop()
        self.start()

    def run(self):
        """You should override this method when you subclass Daemon.
        
        It will be called after the process has been daemonized by 
        start() or restart()."""


########NEW FILE########
__FILENAME__ = dbbrowser
# -*- coding: utf-8 -*-
'''
Copyright (C) 2012-2013 Karsten-Kai König <kkoenig@posteo.de>

This file is part of keepassc.

keepassc is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or at your
option) any later version.

keepassc is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with keepassc.  If not, see <http://www.gnu.org/licenses/>.
'''

import curses as cur
import logging
import os
import threading
import webbrowser
from curses.ascii import NL, DEL, ESC
from os.path import isfile, isdir
from subprocess import Popen, PIPE

from kppy.database import KPDBv1
from kppy.exceptions import KPError

from keepassc.client import Client
from keepassc.editor import Editor
from keepassc.filebrowser import FileBrowser


class DBBrowser(object):
    '''This class represents the database browser'''

    def __init__(self, control, remote = False, address = None, port = None,
                 ssl = False, tls_dir = None):
        self.control = control
        if (self.control.cur_dir[-4:] == '.kdb' and 
            self.control.config['rem_db'] is True and
            remote is False):
            if not isdir(self.control.data_home):
                if isfile(self.control.data_home):
                    os.remove(self.control.data_home)
                os.makedirs(self.control.data_home)
            with open(self.control.last_home, 'w') as handler:
                handler.write(self.control.cur_dir)

        if remote is True and self.control.config['rem_db'] is True:
            if not isdir(self.control.data_home):
                if isfile(self.control.data_home):
                    os.remove(self.control.data_home)
                os.makedirs(self.control.data_home)
            with open(self.control.remote_home, 'w') as handler:
                handler.write(address+'\n')
                handler.write(str(port))
            
        self.db = self.control.db
        self.cur_root = self.db.root_group
        self.lock_timer = None
        self.lock_highlight = 1
        self.clip_timer = None
        self.cb = None
        self.changed = False
        self.g_highlight = 0
        self.e_highlight = 0
        self.g_offset = 0
        self.e_offset = 0
        self.sort_tables(True, False)
        self.changed = False
        self.cur_win = 0
        # 0 = unlocked, 1 = locked, 2 = pre_lock,
        # 3 = move group, 4 = move entry
        self.state = 0
        self.move_object = None

        self.remote = remote
        self.address = address
        self.port = port
        self.ssl = ssl
        self.tls_dir = tls_dir

        self.control.show_groups(self.g_highlight, self.groups,
                                 self.cur_win, self.g_offset,
                                 self.changed, self.cur_root)
        self.control.show_entries(self.e_highlight, self.entries,
                                  self.cur_win, self.e_offset)
        self.db_browser()

    def sort_tables(self, groups, results, go2results=False):
        if groups is True:  # To prevent senseless sorting
            self.groups = sorted(self.cur_root.children,
                                 key=lambda group: group.title.lower())
        if results is True:  # To prevent senseless sorting
            for i in self.groups:  # 'Results' should be the last group
                if i.id_ == 0:
                    self.groups.remove(i)
                    self.groups.append(i)
        if go2results is True:
            self.g_highlight = len(self.groups) - 1
        self.entries = []
        if self.groups:
            if self.groups[self.g_highlight].entries:
                self.entries = sorted(self.groups[self.g_highlight].entries,
                                      key=lambda entry: entry.title.lower())

    def pre_save(self):
        '''Prepare saving'''

        if self.remote is True:
            return True

        if self.db.filepath is None:
            filepath = FileBrowser(self.control, False, False, None, True)()
            if filepath == -1:
                self.close()
            elif filepath is not False:
                self.control.cur_dir = filepath
            else:
                return False
        while True:
            if self.save(self.control.cur_dir) is not False:
                self.changed = False
                break
            elif self.state != 2:
                return False
            else:
                continue

    def pre_save_as(self):
        '''Prepare "Save as"'''

        if self.remote is True:
            return True

        filepath = FileBrowser(self.control, False, False, None, True)()
        if filepath == -1:
            self.close()
        elif filepath is not False:
            if self.db.filepath is None:
                self.control.cur_dir = filepath
            if isfile(filepath):
                self.overwrite_file(filepath)
            else:
                if self.save(filepath) is not False:
                    self.changed = False
                else:
                    return False
        else:
            return False

    def save(self, cur_dir):
        '''Save the database. cur_dir is the current directory.'''

        self.remove_results()
        self.sort_tables(True, False)
        self.control.draw_text(False,
                               (1, 0, 'Do not interrupt or '
                                'your file will break!'))
        try:
            self.db.save(cur_dir)
        except KPError as err:
            self.control.draw_text(False,
                                   (1, 0, err.__str__()),
                                   (4, 0, 'Press any key.'))
            if self.control.any_key() == -1:
                self.close()
            return False

    def save_n_quit(self):
        '''Save database and close KeePassC'''

        if self.db.filepath is None:
            filepath = FileBrowser(self.control, False, False, None, True)()
            if filepath == -1:
                self.close()
            elif filepath is not False:
                self.control.cur_dir = filepath
                if self.save(self.control.cur_dir) is not False:
                    self.close()
        elif self.save(self.control.cur_dir) is not False:
            self.close()

    def ask_for_saving(self):
        '''Ask to save the database (e.g. before quitting)'''

        while True:
            self.control.draw_text(self.changed,
                                   (1, 0, 'File has changed. Save? [(y)/n]'))
            try:
                e = self.control.stdscr.getch()
            except KeyboardInterrupt:
                e = 4
            if e == 4:
                self.close()
            elif e == cur.KEY_RESIZE:
                self.control.resize_all()
            elif e == cur.KEY_F5:
                return False
            elif e == ord('n'):
                break
            else:
                if self.db.filepath is None:
                    filepath = FileBrowser(self.control, False, False, None, 
                                           True)()
                    if filepath == -1:
                        self.close()
                    elif filepath is not False:
                        self.control.cur_dir = filepath
                        self.save(self.control.cur_dir)
                    else:
                        continue
                else:
                    self.save(self.control.cur_dir)
            break

    def overwrite_file(self, filepath):
        '''Overwrite an existing file'''

        self.control.draw_text(self.changed,
                               (1, 0, 'File exists. Overwrite? [y/(n)]'))
        while True:
            try:
                c = self.control.stdscr.getch()
            except KeyboardInterrupt:
                c = 4
            if c == ord('y'):
                if self.save(filepath) is not False:
                    return True
                else:
                    return False
            elif c == 4:
                self.close()
            elif c == cur.KEY_RESIZE:
                self.control.resize_all()
            else:
                return False

    def close(self):
        '''Close KeePassC'''

        self.db_close()
        if type(self.clip_timer) is threading.Timer:
            self.clip_timer.cancel()
            self.del_clipboard()
        self.control.close()

    def db_close(self):
        '''Close the database correctly.'''

        if self.db.filepath is not None:
            try:
                self.db.close()
            except KPError as err:
                self.control.draw_text(False,
                                       (1, 0, err.__str__()),
                                       (4, 0, 'Press any key.'))
                self.control.any_key()
        self.db = None
        self.control.db = None

    def exit2main(self):
        '''Exit to main menu'''

        if self.changed is True:
            if self.ask_for_saving() is False:
                return
        if type(self.clip_timer) is threading.Timer:
            self.clip_timer.cancel()
            self.del_clipboard()
        self.db_close()

    def quit_kpc(self):
        '''Prepare closing of KeePassC'''

        if self.changed is True:
            if self.ask_for_saving() is False:
                return
        self.close()

    def pre_lock(self):
        '''Method is necessary to prevent weird effects due to theading'''

        if self.db.filepath is None and self.remote is False:
            self.control.draw_text(self.changed,
                                   (1, 0, 'Can only lock an existing db!'),
                                   (4, 0, 'Press any key.'))
            if self.control.any_key() == -1:
                self.close()
            return False
        if ((self.changed is True and self.db.read_only is False) and
            self.remote is False):
            self.state = 2
            self.control.draw_text(self.changed,
                                   (1, 0, 'File has changed. Save? [(y)/n]'))
        else:
            self.lock_db()

    def lock_db(self):
        '''Lock the database'''

        self.remove_results()
        self.del_clipboard()
        self.db.lock()
        self.state = 1
        self.control.draw_lock_menu(self.changed, self.lock_highlight,
                                    (1, 0, 'Use a password (1)'),
                                    (2, 0, 'Use a keyfile (2)'),
                                    (3, 0, 'Use both (3)'))

    def reload_remote_db(self, db_buf = None):
        if self.remote is True:
            old_root = self.cur_root
            if self.groups:
                old_group_id = self.groups[self.g_highlight].id_
            else:
                old_group_id = None
            if self.entries:
                old_entry_uuid = self.entries[self.e_highlight].uuid
            else:
                old_entry_uuid = None

            if db_buf == None:
                db_buf = self.client().get_db()
                if self.check_answer(db_buf) is False:
                    return False
            self.db = KPDBv1(None, self.db.password, self.db.keyfile)
            self.db.load(db_buf)
            self.control.db = self.db

            # This loop has to be executed _before_ sort_tables is called
            for i in self.db.groups:
                if i.id_ == old_root.id_:
                    self.cur_root = i
                    break
                else:
                    self.cur_root = self.db.root_group

            self.sort_tables(True, True)

            if self.groups and old_group_id:
                for i in self.groups:
                    if i.id_ == old_group_id:
                        self.g_highlight = self.groups.index(i)
                        break
                    else:
                        self.g_highlight = 0
            else:
                self.g_highlight = 0

            if self.entries and old_entry_uuid:
                for i in self.entries:
                    if i.uuid == old_entry_uuid:
                        self.e_highlight = self.entries.index(i)
                        break
                    else:
                        self.e_highlight = 0
            else:
                self.e_highlight = 0

    def unlock_with_password(self):
        '''Unlock the database with a password'''

        self.lock_highlight = 1
        self.unlock_db()

    def unlock_with_keyfile(self):
        '''Unlock the database with a keyfile'''

        self.lock_highlight = 2
        self.unlock_db()

    def unlock_with_both(self):
        '''Unlock the database with both'''

        self.lock_highlight = 3
        self.unlock_db()

    def unlock_db(self):
        '''Unlock the database'''

        if self.lock_highlight == 1 or self.lock_highlight == 3:
            password = self.control.get_password('Password: ')
            if password is False:
                return False
            elif password == -1:
                self.close()
            if self.lock_highlight != 3:  # Only password needed
                keyfile = None
        if self.lock_highlight == 2 or self.lock_highlight == 3:
            while True:
                if self.control.config['rem_key'] is True:
                    self.control.get_last_key()
                if (self.control.last_key is None or
                        self.control.config['rem_key'] is False):
                    ask_for_lf = False
                else:
                    ask_for_lf = True

                keyfile = FileBrowser(self.control, ask_for_lf, True, 
                                      self.control.last_key)()
                if keyfile is False:
                    return False
                elif keyfile == -1:
                    self.close()
                elif not isfile(keyfile):
                    self.control.draw_text(self.changed,
                                           (1, 0, 'That\'s not a file'),
                                           (3, 0, 'Press any key.'))
                    if self.control.any_key() == -1:
                        self.close()
                    continue
                break
            if self.lock_highlight != 3:  # Only keyfile needed
                password = None

        if self.remote is True:
            db_buf = self.client().get_db()
            if self.check_answer(db_buf) is False:
                return False
        else:
            db_buf = None

        try:
            self.db.unlock(password, keyfile, db_buf)
        except KPError as err:
            self.control.draw_text(self.changed,
                                   (1, 0, err.__str__()),
                                   (4, 0, 'Press any key.'))
            if self.control.any_key() == -1:
                self.close()
        else:
            self.cur_root = self.db.root_group
            # If last shown group was Results
            if self.g_highlight >= len(self.groups):
                self.g_highlight = len(self.groups) - 1 
            self.sort_tables(True, False)
            self.state = 0
            self.control.show_groups(self.g_highlight, self.groups,
                                     self.cur_win, self.g_offset,
                                     self.changed, self.cur_root)
            self.control.show_entries(self.e_highlight, self.entries,
                                      self.cur_win, self.e_offset)

    def nav_down_lock(self):
        '''Navigate down in lock menu'''

        if self.lock_highlight < 3:
            self.lock_highlight += 1

    def nav_up_lock(self):
        '''Navigate up in lock menu'''

        if self.lock_highlight > 1:
            self.lock_highlight -= 1

    def change_db_password(self):
        '''Change the master key of the database'''

        if (self.address != "127.0.0.1" and self.address != "localhost" and
            self.remote is True):
            self.control.draw_text(False,
                           (1, 0, "Password change from remote is not "
                                  "allowed"),
                           (3, 0, "Press any key."))
            if self.control.any_key() == -1:
                self.close()

        while True:
            auth = self.control.gen_menu(1, (
                                         (1, 0, 'Use a password (1)'),
                                         (2, 0, 'Use a keyfile (2)'),
                                         (3, 0, 'Use both (3)')))
            if auth == 2 or auth == 3:
                while True:
                    filepath = FileBrowser(self.control, False, True, None)()
                    if filepath == -1:
                        self.close()
                    elif not isfile(filepath):
                        self.control.draw_text(self.changed,
                                               (1, 0, "That's not a file!"),
                                               (3, 0, 'Press any key.'))
                        if self.control.any_key() == -1:
                            self.close()
                        continue
                    break
                if filepath is False:
                    continue
                if self.remote is False:
                    self.db.keyfile = filepath
                else:
                    tmp_keyfile = filepath
                if auth != 3:
                    password = None
                    tmp_password = None

            if auth == 1 or auth == 3:
                password = self.control.get_password('New Password: ')
                if password is False:
                    continue
                elif password == -1:
                    self.close()
                confirm = self.control.get_password('Confirm: ')
                if confirm is False:
                    continue
                elif confirm == -1:
                    self.close()
                if password == confirm:
                    if self.remote is False:
                        self.db.password = password
                    else:
                        tmp_password = password
                else:
                    self.control.draw_text(self.changed,
                                           (1, 0, 'Passwords didn\'t match. '
                                               'Press any key.'))
                    if self.control.any_key() == -1:
                        self.close()
                    continue
                if auth != 3:
                    filepath = None
                    tmp_keyfile = None

            if auth is False:
                return False
            elif auth == -1:
                self.close()
            elif self.remote is True:
                if tmp_password is None:
                    tmp_password = b''
                else:
                    tmp_password = tmp_password.encode()
                if tmp_keyfile is None:
                    tmp_keyfile = b''
                else:
                    tmp_keyfile = tmp_keyfile.encode()

                answer = self.client().change_password(tmp_password, 
                                                       tmp_keyfile)
                if self.check_answer(answer) is False:
                    return False
                else:
                    self.db.password = password
                    self.db.keyfile = filepath
                return True
            else:
                self.changed = True
                return True

    def create_group(self):
        '''Create a group in the current root'''

        edit = Editor(self.control.stdscr, max_text_size=1, win_location=(0, 1),
                      win_size=(1, 80), title="Group Name: ")()
        if edit == -1:
            self.close()
        elif edit is not False:
            if self.groups:
                old_group = self.groups[self.g_highlight]
            else:
                old_group = None

            if self.remote is True:
                if self.cur_root is self.db.root_group:
                    root = 0
                else:
                    root = self.cur_root.id_
                db_buf = self.client().create_group(edit.encode(), 
                                                    str(root).encode())
                if self.check_answer(db_buf) is not False:
                    self.reload_remote_db(db_buf)
            else:
                try:
                    if self.cur_root is self.db.root_group:
                        self.db.create_group(edit)
                    else:
                        self.db.create_group(edit, self.cur_root)
                except KPError as err:
                    self.control.draw_text(self.changed,
                                           (1, 0, err.__str__()),
                                           (4, 0, 'Press any key.'))
                    if self.control.any_key() == -1:
                        self.close()
                else:
                    self.changed = True

                self.sort_tables(True, True)
                if (self.groups and
                    self.groups[self.g_highlight] is not old_group and
                        old_group is not None):
                    self.g_highlight = self.groups.index(old_group)

    def create_sub_group(self):
        '''Create a sub group with marked group as parent'''

        if self.groups:
            edit = Editor(self.control.stdscr, max_text_size=1,
                          win_location=(0, 1),
                          win_size=(1, 80), title="Group Name: ")()
            if edit == -1:
                self.close()
            elif edit is not False:
                if self.remote is True:
                    root = self.groups[self.g_highlight].id_
                    db_buf = self.client().create_group(edit.encode(),
                                                        (str(root)
                                                         .encode()))
                    if self.check_answer(db_buf) is not False:
                        self.reload_remote_db(db_buf)
                else:
                    try:
                        self.db.create_group(edit, 
                                             self.groups[self.g_highlight])
                    except KPError as err:
                        self.control.draw_text(self.changed,
                                               (1, 0, err.__str__()),
                                               (4, 0, 'Press any key.'))
                        if self.control.any_key() == -1:
                            self.close()
                    else:
                        self.changed = True

    def create_entry(self):
        '''Create an entry for the marked group'''

        if self.groups:
            if self.entries:
                old_entry = self.entries[self.e_highlight]
            else:
                old_entry = None
            self.control.draw_text(self.changed,
                                   (1, 0, 'At least one of the following '
                                    'attributes must be given. Press any key'))
            if self.control.any_key() == -1:
                self.close()

            pass_title = False
            pass_url = False
            pass_username = False
            pass_password = False
            pass_comment = False
            goto_last = False
            while True:
                if pass_title is False:
                    title = Editor(self.control.stdscr, max_text_size=1,
                                   win_location=(0, 1),
                                   win_size=(1, 80), title="Title: ")()
                if title is False:
                    break
                elif title == -1:
                    self.close()
                pass_title = True

                if pass_url is False:
                    url = Editor(self.control.stdscr, max_text_size=1,
                                 win_location=(0, 1),
                                 win_size=(1, 80), title="URL: ")()
                if url is False:
                    pass_title = False
                    continue
                elif url == -1:
                    self.close()
                pass_url = True

                if pass_username is False:
                    username = Editor(self.control.stdscr, max_text_size=1,
                                      win_location=(0, 1),
                                      win_size=(1, 80), title="Username: ")()
                if username is False:
                    pass_url = False
                    continue
                elif username == -1:
                    self.close()
                pass_username = True

                if pass_password is False:
                    nav = self.control.gen_menu(1,
                        ((1, 0, 'Use password generator (1)'),
                         (2, 0, 'Type password by hand (2)'),
                         (3, 0, 'No password (3)')))
                    if nav == 1:
                        password = self.control.gen_pass()
                        if password is False:
                            continue
                        elif password == -1:
                            self.close()
                    elif nav == 2:
                        while True:
                            password = self.control.get_password('Password: ',
                                                                 False)
                            if password is False:
                                break
                            elif password == -1:
                                self.close()
                            confirm = self.control.get_password('Confirm: ',
                                                                False)
                            if confirm is False:
                                continue
                            elif confirm == -1:
                                self.close()

                            if password != confirm:
                                self.control.draw_text(self.changed,
                                                    (3, 0,
                                                    "Passwords didn't match"),
                                                    (5, 0, 'Press any key.'))
                                if self.control.any_key() == -1:
                                    self.close()
                            else:
                                break
                        if password is False:
                            continue
                    elif nav == -1:
                        self.close()
                    else:
                        password = ''
                if nav is False:
                    pass_username = False
                    continue
                pass_password = True

                if pass_comment is False:
                    comment = Editor(self.control.stdscr, win_location=(0, 1),
                                     title="Comment: ")()
                if comment is False:
                    pass_password = False
                    continue
                elif comment == -1:
                    self.close()
                pass_comment = True

                self.control.draw_text(self.changed,
                                       (1, 0, 'Set expiration date? [y/(n)]'))
                while True:
                    try:
                        e = self.control.stdscr.getch()
                    except KeyboardInterrupt:
                        e = 4

                    if e == ord('y'):
                        exp_date = self.control.get_exp_date()
                        break
                    elif e == 4:
                        self.close()
                    elif e == cur.KEY_RESIZE:
                        self.control.resize_all()
                    elif e == cur.KEY_F5:
                        pass_comment = False
                        goto_last = True
                        break
                    else:
                        exp_date = (2999, 12, 28)
                        break
                if goto_last is True:
                    goto_last = False
                    continue
                if exp_date is False:
                    pass_comment = False
                    continue
                elif exp_date == -1:
                    self.close()

                if self.remote is True:
                    root = self.groups[self.g_highlight].id_

                    db_buf = self.client().create_entry(title.encode(),
                                                 url.encode(),
                                                 username.encode(),
                                                 password.encode(),
                                                 comment.encode(),
                                                 str(exp_date[0]).encode(),
                                                 str(exp_date[1]).encode(),
                                                 str(exp_date[2]).encode(),
                                                 str(root).encode())
                    if self.check_answer(db_buf) is not False:
                        self.reload_remote_db(db_buf)
                    break
                else:
                    try:
                        self.groups[self.g_highlight].create_entry(title, 1, 
                                                                   url,
                                                                   username,
                                                                   password,
                                                                   comment,
                                                                   exp_date[0],
                                                                   exp_date[1],
                                                                   exp_date[2])
                    except KPError as err:
                        self.control.draw_text(self.changed,
                                               (1, 0, err.__str__()),
                                               (4, 0, 'Press any key.'))
                        if self.control.any_key() == -1:
                            self.close()
                    else:
                        self.changed = True

                    self.sort_tables(True, True)
                    if (self.entries and
                        self.entries[self.e_highlight] is not old_entry and
                            old_entry is not None):
                        self.e_highlight = self.entries.index(old_entry)
                    break

    def pre_delete(self):
        '''Prepare deletion of group or entry'''

        if self.cur_win == 0 and self.groups:
            self.delete_group()
        elif self.cur_win == 1:
            self.delete_entry()

    def delete_group(self):
        '''Delete the marked group'''

        if len(self.db.groups) > 1:
            title = self.groups[self.g_highlight].title
            self.control.draw_text(self.changed,
                                   (1, 0, 'Really delete group ' + title + '? '
                                    '[y/(n)]'))
        else:
            self.control.draw_text(self.changed,
                                   (1, 0, 'At least one group is needed!'),
                                   (3, 0, 'Press any key'))
            if self.control.any_key() == -1:
                self.close()
        while True:
            try:
                e = self.control.stdscr.getch()
            except KeyboardInterrupt:
                e = 4
            if e == ord('y'):
                if self.remote is True:
                    root = self.groups[self.g_highlight].id_
                    last_mod = (self.groups[self.g_highlight]
                                    .last_mod.timetuple())
                    db_buf = self.client().delete_group(str(root).encode(),
                                                        last_mod)
                    if self.check_answer(db_buf) is not False:
                        self.reload_remote_db(db_buf)
                else:
                    try:
                        self.groups[self.g_highlight].remove_group()
                    except KPError as err:
                        self.control.draw_text(self.changed,
                                               (1, 0, err.__str__()),
                                               (4, 0, 'Press any key.'))
                        if self.control.any_key() == -1:
                            self.close()
                    else:
                        if (not self.cur_root.children and
                                self.cur_root is not self.db.root_group):
                            self.cur_root = self.cur_root.parent
                        self.changed = True

                        if (self.g_highlight >= len(self.groups) - 1 and
                                self.g_highlight != 0):
                            self.g_highlight -= 1
                        self.e_highlight = 0
                        self.sort_tables(True, True)
                break
            elif e == 4:
                self.close()
            elif e == cur.KEY_RESIZE:
                self.control.resize_all()
            else:
                break

    def delete_entry(self):
        '''Delete marked entry'''

        title = self.entries[self.e_highlight].title
        self.control.draw_text(self.changed,
                               (1, 0,
                                'Really delete entry ' + title + '? [y/(n)]'))
        while True:
            try:
                e = self.control.stdscr.getch()
            except KeyboardInterrupt:
                e = 4
            if e == ord('y'):
                if self.remote is True:
                    entry_uuid = self.entries[self.e_highlight].uuid
                    last_mod = (self.entries[self.e_highlight]
                                    .last_mod.timetuple())

                    db_buf = self.client().delete_entry(entry_uuid, last_mod)
                    if self.check_answer(db_buf) is not False:
                        self.reload_remote_db(db_buf)

                        if not self.entries:
                            self.cur_win = 0
                        if (self.e_highlight >= len(self.entries) and
                                self.e_highlight != 0):
                            self.e_highlight -= 1
                else:
                    try:
                        self.entries[self.e_highlight].remove_entry()
                    except KPError as err:
                        self.control.draw_text(self.changed,
                                               (1, 0, err.__str__()),
                                               (4, 0, 'Press any key.'))
                        if self.control.any_key() == -1:
                            self.close()
                    else:
                        if self.groups[self.g_highlight].id_ == 0:
                            del (self.groups[self.g_highlight]
                                     .entries[self.e_highlight]) 
                        self.sort_tables(True, True)
                        self.changed = True
                        if not self.entries:
                            self.cur_win = 0
                        if (self.e_highlight >= len(self.entries) and
                                self.e_highlight != 0):
                            self.e_highlight -= 1
                break
            elif e == 4:
                self.close()
            elif e == cur.KEY_RESIZE:
                self.control.resize_all()
            else:
                break

    def move(self):
        '''Enable move state'''

        if self.cur_win == 0:
            self.state = 3
            self.move_object = self.groups[self.g_highlight]
        elif self.cur_win == 1:
            self.state = 4
            self.cur_win = 0
            self.move_object = self.entries[self.e_highlight]

    def move_group_or_entry(self):
        '''Move group to subgroup or entry to new group'''
        
        if (self.state == 3 and 
            self.groups[self.g_highlight] is not self.move_object and
            self.groups):  # e.g. there is actually a group
            if self.remote is True:
                group_id = self.move_object.id_
                root = self.groups[self.g_highlight].id_

                db_buf = self.client().move_group(str(group_id).encode(), 
                                                  str(root).encode())
                if self.check_answer(db_buf) is not False:
                    self.reload_remote_db(db_buf)
            else:
                self.move_object.move_group(self.groups[self.g_highlight])
        elif (self.state == 4 and 
              self.groups[self.g_highlight] is not self.move_object.group and
              self.groups):
            if self.remote is True:
                uuid = self.move_object.uuid
                root = self.groups[self.g_highlight].id_

                db_buf = self.client().move_entry(uuid, 
                                                  str(root).encode())
                if self.check_answer(db_buf) is not False:
                    self.reload_remote_db(db_buf)
            else:
                self.move_object.move_entry(self.groups[self.g_highlight])
        self.changed = True
        self.move_object = None
        self.state = 0
        self.sort_tables(True, True)
            
    def move2root(self):
        if self.state == 3:
            if self.remote is True:
                group_id = self.move_object.id_
                root = 0

                db_buf = self.client().move_group(str(group_id).encode(), 
                                                  str(root).encode())
                if self.check_answer(db_buf) is not False:
                    self.reload_remote_db(db_buf)
            else:
                self.move_object.move_group(self.db.root_group)
            self.move_object = None
            self.state = 0
            self.sort_tables(True, True)

    def move_abort(self):
        self.move_object = None
        self.state = 0
        self.sort_tables(True, True)

    def find_entries(self):
        '''Find entries by title'''

        if self.db.entries:
            title = Editor(self.control.stdscr, max_text_size=1,
                           win_location=(0, 1),
                           win_size=(1, 80), title="Title Search: ")()
            if title == -1:
                self.close()
            elif title is not False and title != '':
                self.remove_results()
                self.db.create_group('Results')
                result_group = self.db.groups[-1]
                result_group.id_ = 0

                for i in self.db.entries:
                    if title.lower() in i.title.lower():
                        result_group.entries.append(i)
                        self.cur_win = 1
                self.cur_root = self.db.root_group
                self.sort_tables(True, True, True)
                self.e_highlight = 0

    def remove_results(self):
        '''Remove possible search result group'''

        for i in self.db.groups:
            if i.id_ == 0:
                try:
                    i.entries.clear()
                    i.remove_group()
                except KPError as err:
                    self.control.draw_text(self.changed,
                                           (1, 0, err.__str__()),
                                           (4, 0, 'Press any key.'))
                    if self.control.any_key() == -1:
                        self.close()
                    return False
                else:
                    if (self.g_highlight >= len(self.cur_root.children) and
                            self.g_highlight != 0):
                        self.g_highlight -= 1
                    self.e_highlight = 0
                break

    def edit_title(self):
        '''Edit title of group or entry'''

        if self.groups:
            std = 'Title: '
            if self.cur_win == 0:
                edit = Editor(self.control.stdscr, max_text_size=1,
                              inittext=self.groups[self.g_highlight].title,
                              win_location=(0, 1),
                              win_size=(1, self.control.xsize), title=std)()
                if edit == -1:
                    self.close()
                elif edit is not False:
                    if self.remote is True:
                        group_id = self.groups[self.g_highlight].id_
                        last_mod = (self.groups[self.g_highlight]
                                        .last_mod.timetuple())
                        db_buf = self.client().set_g_title(edit.encode(),
                                                           (str(group_id)
                                                            .encode()),
                                                           last_mod)
                        if self.check_answer(db_buf) is not False:
                            self.reload_remote_db(db_buf)
                    else:
                        self.groups[self.g_highlight].set_title(edit)
                        self.changed = True
            elif self.cur_win == 1:
                edit = Editor(self.control.stdscr, max_text_size=1,
                              inittext=self.entries[self.e_highlight].title,
                              win_location=(0, 1),
                              win_size=(1, self.control.xsize), title=std)()
                if edit == -1:
                    self.close()
                elif edit is not False:
                    if self.remote is True:
                        uuid = self.entries[self.e_highlight].uuid
                        last_mod = (self.entries[self.e_highlight]
                                        .last_mod.timetuple())
                        db_buf = self.client().set_e_title(edit.encode(),
                                                           uuid, last_mod)
                        if self.check_answer(db_buf) is not False:
                            self.reload_remote_db(db_buf)
                    else:
                        self.entries[self.e_highlight].set_title(edit)
                        self.changed = True

    def edit_username(self):
        '''Edit username of marked entry'''

        if self.entries:
            std = 'Username: '
            edit = Editor(self.control.stdscr, max_text_size=1,
                          inittext=self.entries[self.e_highlight].username,
                          win_location=(0, 1), win_size=(1, self.control.xsize),
                          title=std)()
            if edit == -1:
                self.close()
            elif edit is not False:
                if self.remote is True:
                    uuid = self.entries[self.e_highlight].uuid
                    last_mod = (self.entries[self.e_highlight]
                                    .last_mod.timetuple())
                    db_buf = self.client().set_e_user(edit.encode(),
                                                       uuid, last_mod)
                    if self.check_answer(db_buf) is not False:
                        self.reload_remote_db(db_buf)
                else:
                    self.changed = True
                    self.entries[self.e_highlight].set_username(edit)

    def edit_url(self):
        '''Edit URL of marked entry'''

        if self.entries:
            std = 'URL: '
            edit = Editor(self.control.stdscr, max_text_size=1,
                          inittext=self.entries[self.e_highlight].url,
                          win_location=(0, 1), win_size=(1, 
                          self.control.xsize), 
                          title=std)()
            if edit == -1:
                self.close()
            elif edit is not False:
                if self.remote is True:
                    uuid = self.entries[self.e_highlight].uuid
                    last_mod = (self.entries[self.e_highlight]
                                    .last_mod.timetuple())
                    db_buf = self.client().set_e_url(edit.encode(),
                                                     uuid, last_mod)
                    if self.check_answer(db_buf) is not False:
                        self.reload_remote_db(db_buf)
                else:
                    self.changed = True
                    self.entries[self.e_highlight].set_url(edit)

    def edit_comment(self):
        '''Edit comment of marked entry'''

        if self.entries:
            std = 'Comment: '
            edit = Editor(self.control.stdscr, title=std, win_location=(0, 1),
                          inittext=self.entries[self.e_highlight].comment)()
            if edit == -1:
                self.close()
            elif edit is not False:
                if self.remote is True:
                    uuid = self.entries[self.e_highlight].uuid
                    last_mod = (self.entries[self.e_highlight]
                                    .last_mod.timetuple())
                    db_buf = self.client().set_e_comment(edit.encode(),
                                                         uuid, last_mod)
                    if self.check_answer(db_buf) is not False:
                        self.reload_remote_db(db_buf)
                else:
                    self.changed = True
                    self.entries[self.e_highlight].set_comment(edit)

    def edit_password(self):
        '''Edit password of marked entry'''

        nav = self.control.gen_menu(1, ((1, 0, 'Use password generator (1)'),
                                     (2, 0, 'Type password by hand (2)'),
                                     (3, 0, 'No password (3)')))
        if nav == 1:
            password = self.control.gen_pass()
            if password == -1:
                self.close()
            elif password is False:
                return False
            if self.remote is True:
                uuid = self.entries[self.e_highlight].uuid
                last_mod = (self.entries[self.e_highlight]
                                .last_mod.timetuple())
                db_buf = self.client().set_e_pass(password.encode(),
                                                  uuid, last_mod)
                if self.check_answer(db_buf) is not False:
                    self.reload_remote_db(db_buf)
            else:
                self.entries[self.e_highlight].set_password(password)
                self.changed = True
        elif nav == 2:
            while True:
                password = self.control.get_password('Password: ', False)
                if password is False:
                    break
                elif password == -1:
                    self.close()
                confirm = self.control.get_password('Confirm: ', False)
                if confirm is False:
                    continue
                elif confirm == -1:
                    self.close()

                if password == confirm:
                    if self.remote is True:
                        uuid = self.entries[self.e_highlight].uuid
                        last_mod = (self.entries[self.e_highlight]
                                        .last_mod.timetuple())
                        db_buf = self.client().set_e_pass(password.encode(),
                                                          uuid, last_mod)
                        if self.check_answer(db_buf) is not False:
                            self.reload_remote_db(db_buf)
                    else:
                        self.entries[self.e_highlight].set_password(password)
                        self.changed = True
                    break
                else:
                    self.control.draw_text(self.changed,
                                           (3, 0, 'Passwords didn\'t match. '
                                               'Press any key.'))
                    if self.control.any_key() == -1:
                        self.close()
                    break
        elif nav == -1:
            self.close()

    def edit_date(self):
        '''Edit expiration date of marked entry'''

        exp = self.entries[self.e_highlight].expire.timetuple()
        exp_date = self.control.get_exp_date(exp[0], exp[1], exp[2])

        if exp_date == -1:
            self.close()
        elif exp_date is not False:
            if self.remote is True:
                uuid = self.entries[self.e_highlight].uuid
                last_mod = (self.entries[self.e_highlight]
                                .last_mod.timetuple())
                db_buf = self.client().set_e_exp(
                    str(exp_date[0]).encode(), str(exp_date[1]).encode(), 
                    str(exp_date[2]).encode(), uuid, last_mod)
                if self.check_answer(db_buf) is not False:
                    self.reload_remote_db(db_buf)
            else:
                self.entries[self.e_highlight].set_expire(
                    exp_date[0], exp_date[1], exp_date[2],
                    exp[3], exp[4], exp[5])
                self.changed = True

    def client(self):
        return Client(logging.ERROR, 'client.log', 
                      self.address, 
                      self.port, self.db.password, 
                      self.db.keyfile, self.ssl, 
                      self.tls_dir)

    def check_answer(self, answer):
        if answer[:4] == 'FAIL' or answer[:4] == "[Err":
            self.control.draw_text(False,
                                   (1, 0, answer),
                                   (3, 0, 'Press any key.'))
            if self.control.any_key() == -1:
                self.close()
            return False

    def show_password(self):
        '''Show password of marked entry (e.g. copy it without xsel)'''

        if self.entries:
            self.control.draw_text(self.changed,
                                   (1, 0,
                                    self.entries[self.e_highlight].password))
            if self.control.any_key() == -1:
                self.close()

    def copy_password(self):
        '''Copy password to clipboard (calls cp2cb)'''

        if self.entries:
            self.cp2cb(self.entries[self.e_highlight].password)

    def copy_username(self):
        '''Copy username to clipboard (calls cp2cb)'''

        if self.entries:
            self.cp2cb(self.entries[self.e_highlight].username)

    def cp2cb(self, stuff):
        '''Copy stuff to clipboard'''

        if stuff is not None:
            try:
                Popen(
                    ['xsel', '-pc'], stderr=PIPE, stdout=PIPE)
                Popen(
                    ['xsel', '-bc'], stderr=PIPE, stdout=PIPE)
                Popen(['xsel', '-pi'], stdin=PIPE, stderr=PIPE,
                      stdout=PIPE).communicate(stuff.encode())
                Popen(['xsel', '-bi'], stdin=PIPE, stderr=PIPE,
                      stdout=PIPE).communicate(stuff.encode())
                if self.control.config['del_clip'] is True:
                    if type(self.clip_timer) is threading.Timer:
                        self.clip_timer.cancel()
                    self.clip_timer = threading.Timer(
                        self.control.config['clip_delay'],
                        self.del_clipboard)
                    self.clip_timer.start()
            except FileNotFoundError as err:
                self.control.draw_text(False,
                                       (1, 0, err.__str__()),
                                       (4, 0, 'Press any key.'))
                if self.control.any_key() == -1:
                    self.close()
            else:
                self.cb = stuff

    def del_clipboard(self):
        '''Delete the X clipboard'''

        try:
            cb_p = Popen('xsel', stdout=PIPE)
            cb = cb_p.stdout.read().decode()
            if cb == self.cb:
                Popen(['xsel', '-pc'])
                Popen(['xsel', '-bc'])
                self.cb = None
        except FileNotFoundError:  # xsel not installed
            pass

    def open_url(self):
        '''Open URL in standard webbrowser'''

        if self.entries:
            entry = self.entries[self.e_highlight]
            url = entry.url
            if url != '':
                if url[:7] != 'http://' and url[:8] != 'https://':
                    url = 'http://' + url
                savout = os.dup(1)
                saverr = os.dup(2)
                os.close(1)
                os.close(2)
                os.open(os.devnull, os.O_RDWR)
                try:
                    webbrowser.open(url)
                finally:
                    os.dup2(saverr, 2)
                    os.dup2(savout, 1)

    def nav_down(self):
        '''Navigate down'''

        if self.cur_win == 0 and self.g_highlight < len(self.groups) - 1:
            ysize = self.control.group_win.getmaxyx()[0]
            if (self.g_highlight >= ysize - 4 + self.g_offset and
                not self.g_offset >= len(self.groups) - ysize + 4):
                self.g_offset += 1
            self.g_highlight += 1
            self.e_offset = 0
            self.e_highlight = 0
            self.sort_tables(False, True)
        elif self.cur_win == 1 and self.e_highlight < len(self.entries) - 1:
            ysize = self.control.entry_win.getmaxyx()[0]
            if (self.e_highlight >= ysize - 4 + self.e_offset and
                not self.e_offset >= len(self.entries) - ysize + 3):
                self.e_offset += 1
            self.e_highlight += 1

    def nav_up(self):
        '''Navigate up'''

        if self.cur_win == 0 and self.g_highlight > 0:
            if self.g_offset > 0 and self.g_highlight == self.g_offset:
                self.g_offset -= 1
            self.g_highlight -= 1
            self.e_offset = 0
            self.e_highlight = 0
            self.sort_tables(False, True)
        elif self.cur_win == 1 and self.e_highlight > 0:
            if self.e_offset > 0 and self.e_highlight == self.e_offset:
                self.e_offset -= 1
            self.e_highlight -= 1

    def nav_left(self):
        '''Go to groups'''

        self.cur_win = 0

    def nav_right(self):
        '''Go to entries'''

        if self.entries:
            self.cur_win = 1

    def go2sub(self):
        '''Change to subgroups of current root'''

        # To prevent that a parent group is moved to a subgroup
        if (self.state == 3 and 
            self.move_object is self.groups[self.g_highlight]):
            return 

        if self.groups and self.groups[self.g_highlight].children:
            self.cur_root = self.groups[self.g_highlight]
            self.g_highlight = 0
            self.e_highlight = 0
            self.cur_win = 0
            self.sort_tables(True, False)

    def go2parent(self):
        '''Change to parent of current subgroups'''

        if not self.cur_root is self.db.root_group:
            self.g_highlight = 0
            self.e_highlight = 0
            self.cur_win = 0
            self.cur_root = self.cur_root.parent
            self.sort_tables(True, True)

    def db_browser(self):
        '''The database browser.'''

        unlocked_state = {
            cur.KEY_F1: self.control.dbbrowser_help,
            ord('e'): self.exit2main,
            ord('q'): self.quit_kpc,
            4: self.quit_kpc,
            ord('c'): self.copy_password,
            ord('b'): self.copy_username,
            ord('o'): self.open_url,
            ord('s'): self.pre_save,
            ord('S'): self.pre_save_as,
            ord('x'): self.save_n_quit,
            ord('L'): self.pre_lock,
            ord('P'): self.change_db_password,
            ord('g'): self.create_group,
            ord('G'): self.create_sub_group,
            ord('y'): self.create_entry,
            ord('d'): self.pre_delete,
            ord('f'): self.find_entries,
            ord('/'): self.find_entries,
            ord('t'): self.edit_title,
            ord('u'): self.edit_username,
            ord('U'): self.edit_url,
            ord('C'): self.edit_comment,
            ord('p'): self.edit_password,
            ord('E'): self.edit_date,
            ord('H'): self.show_password,
            ord('m'): self.move,
            cur.KEY_RESIZE: self.control.resize_all,
            NL: self.go2sub,
            cur.KEY_BACKSPACE: self.go2parent,
            DEL: self.go2parent,
            cur.KEY_DOWN: self.nav_down,
            ord('j'): self.nav_down,
            cur.KEY_UP: self.nav_up,
            ord('k'): self.nav_up,
            cur.KEY_LEFT: self.nav_left,
            ord('h'): self.nav_left,
            cur.KEY_RIGHT: self.nav_right,
            ord('l'): self.nav_right,
            ord('r'): self.reload_remote_db}

        locked_state = {
            ord('q'): self.quit_kpc,
            4: self.quit_kpc,
            cur.KEY_DOWN: self.nav_down_lock,
            ord('j'): self.nav_down_lock,
            cur.KEY_UP: self.nav_up_lock,
            ord('k'): self.nav_up_lock,
            NL: self.unlock_db,
            ord('1'): self.unlock_with_password,
            ord('2'): self.unlock_with_keyfile,
            ord('3'): self.unlock_with_both}

        move_states = {
            ord('e'): self.exit2main,
            ord('q'): self.quit_kpc,
            4: self.quit_kpc,
            cur.KEY_DOWN: self.nav_down,
            ord('j'): self.nav_down,
            cur.KEY_UP: self.nav_up,
            ord('k'): self.nav_up,
            cur.KEY_LEFT: self.go2parent,
            ord('h'): self.go2parent,
            cur.KEY_RIGHT: self.go2sub,
            ord('l'): self.go2sub,
            NL: self.move_group_or_entry,
            cur.KEY_BACKSPACE: self.move2root,
            DEL: self.move2root,
            ESC: self.move_abort,
            cur.KEY_F1: self.control.move_help}

        exceptions = (ord('s'), ord('S'), ord('P'), ord('t'), ord('p'), 
                      ord('u'), ord('U'), ord('C'), ord('E'), ord('H'), 
                      ord('g'), ord('d'), ord('y'), ord('f'), ord('/'),
                      cur.KEY_F1, cur.KEY_RESIZE)

        while True:
            old_g_highlight = self.g_highlight
            old_e_highlight = self.e_highlight
            old_window = self.cur_win
            old_root = self.cur_root
    
            if (self.control.config['lock_db'] and self.state == 0 and
                    self.db.filepath is not None):
                self.lock_timer = threading.Timer(
                    self.control.config['lock_delay'],
                    self.pre_lock)
                self.lock_timer.start()
            try:
                c = self.control.stdscr.getch()
            except KeyboardInterrupt:
                c = 4
            if type(self.lock_timer) is threading.Timer:
                self.lock_timer.cancel()
            if self.state == 0:
                if c == ord('\t'):  # Switch group/entry view with tab.
                    if self.cur_win == 0:
                        c = cur.KEY_RIGHT
                    else:
                        c = cur.KEY_LEFT
                if c in unlocked_state:
                    unlocked_state[c]()
                if c == ord('e'):
                    return False
                # 'cause 'L' changes state
                if self.state == 0 or self.state == 4:  
                    if ((self.cur_win == 0 and
                         old_g_highlight != self.g_highlight) or
                        c in exceptions or
                        old_window != self.cur_win or
                        old_root is not self.cur_root):
                        self.control.show_groups(self.g_highlight, self.groups,
                                                 self.cur_win, self.g_offset,
                                                 self.changed, self.cur_root)
                    if ((self.cur_win == 1 and
                         old_e_highlight != self.e_highlight) or
                        c in exceptions or
                        old_window != self.cur_win or
                        old_g_highlight != self.g_highlight or
                        old_root is not self.cur_root):
                        self.control.show_entries(self.e_highlight, 
                                                  self.entries,
                                                  self.cur_win, self.e_offset)
            elif self.state == 1 and c in locked_state:
                locked_state[c]()
                if self.state == 1:  # 'cause 'L' changes state
                    self.control.draw_lock_menu(self.changed,
                                                self.lock_highlight,
                                                (1, 0, 'Use a password (1)'),
                                                (2, 0, 'Use a keyfile (2)'),
                                                (3, 0, 'Use both (3)'))
            elif self.state == 2:
                if c == ord('n'):
                    self.lock_db()
                else:
                    self.pre_save()
                    self.lock_db()
            elif self.state > 2 and c in move_states:
                move_states[c]()
                if ((self.cur_win == 0 and
                     old_g_highlight != self.g_highlight) or
                    old_window != self.cur_win or
                    c == NL):
                    self.control.show_groups(self.g_highlight, self.groups,
                                             self.cur_win, self.g_offset,
                                             self.changed, self.cur_root)
                self.control.show_entries(self.e_highlight, self.entries,
                                          self.cur_win, self.e_offset)

########NEW FILE########
__FILENAME__ = editor
"""Scott Hansen <firecat four one five three at gmail dot com>

Copyright (c) 2013, Scott Hansen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""

import curses
import curses.ascii
import locale
from textwrap import wrap


class Editor(object):
    """ Basic python curses text editor class.

    Can be used for multi-line editing.

    Text will be wrapped to the width of the editing window, so there will be
    no scrolling in the horizontal direction. For now, there's no line
    wrapping, so lines will have to be wrapped manually.

    Args:
        stdscr:         the curses window object
        title:          title text
        inittext:       inital text content string
        win_location:   tuple (y,x) for location of upper left corner
        win_size:       tuple (rows,cols) size of the editor window
        box:            True/False whether to outline editor with a box
        max_text_size:  maximum rows allowed size for text.
                            Default=0 (unlimited)
        pw_mode:        True/False. Whether or not to show text entry
                            (e.g. for passwords)

    Returns:
        text:   text string  or -1 on a KeyboardInterrupt

    Usage:
        import keepassc
        keepassc.editor(box=False, inittext="Hi", win_location=(5, 5))

    TODO: fix pageup/pagedown for single line text entry

    """

    def __init__(self, scr, title="", inittext="", win_location=(0, 0),
                 win_size=(20, 80), box=True, max_text_size=0, pw_mode=False):
        self.scr = scr
        self.title = title
        self.box = box
        self.max_text_size = max_text_size
        self.pw_mode = pw_mode
        if self.pw_mode is True:
            try:
                curses.curs_set(0)
            except:
                print('Invisible cursor not supported.')
        else:
            try:
                curses.curs_set(1)
            except:
                pass
            curses.echo()
        locale.setlocale(locale.LC_ALL, '')
        curses.use_default_colors()
        #encoding = locale.getpreferredencoding()
        self.resize_flag = False
        self.win_location_x, self.win_location_y = win_location
        self.win_size_orig_y, self.win_size_orig_x = win_size
        self.win_size_y = self.win_size_orig_y
        self.win_size_x = self.win_size_orig_x
        self.win_init()
        self.box_init()
        self.text_init(inittext)
        self.keys_init()
        self.display()

    def __call__(self):
        return self.run()

    def box_init(self):
        """Clear the main screen and redraw the box and/or title

        """
        # Touchwin seems to save the underlying screen and refreshes it (for
        # example when the help popup is drawn and cleared again)
        self.scr.touchwin()
        self.scr.refresh()
        self.stdscr.clear()
        self.stdscr.refresh()
        quick_help = "   (F2 or Enter: Save, F5: Cancel)"
        if self.box is True:
            self.boxscr.clear()
            self.boxscr.box()
            if self.title:
                self.boxscr.addstr(1, 1, self.title, curses.A_BOLD)
                self.boxscr.addstr(quick_help, curses.A_STANDOUT)
                self.boxscr.addstr
            self.boxscr.refresh()
        elif self.title:
            self.boxscr.clear()
            self.boxscr.addstr(0, 0, self.title, curses.A_BOLD)
            self.boxscr.addstr(quick_help, curses.A_STANDOUT)
            self.boxscr.refresh()

    def text_init(self, text):
        """Transform text string into a list of strings, wrapped to fit the
        window size. Sets the dimensions of the text buffer.

        """
        t = str(text).split('\n')
        t = [wrap(i, self.win_size_x - 1) for i in t]
        self.text = []
        for line in t:
            # This retains any empty lines
            if line:
                self.text.extend(line)
            else:
                self.text.append("")
        if self.text:
            # Sets size for text buffer...may be larger than win_size!
            self.buffer_cols = max(self.win_size_x,
                                   max([len(i) for i in self.text]))
            self.buffer_rows = max(self.win_size_y, len(self.text))
        self.text_orig = self.text[:]
        if self.max_text_size:
            # Truncates initial text if max_text_size < len(self.text)
            self.text = self.text[:self.max_text_size]
        self.buf_length = len(self.text[self.buffer_idx_y])

    def keys_init(self):
        """Define methods for each key.

        """
        self.keys = {
            curses.KEY_BACKSPACE:                self.backspace,
            curses.KEY_DOWN:                     self.down,
            curses.KEY_END:                      self.end,
            curses.KEY_ENTER:                    self.insert_line_or_quit,
            curses.KEY_HOME:                     self.home,
            curses.KEY_DC:                       self.del_char,
            curses.KEY_LEFT:                     self.left,
            curses.KEY_NPAGE:                    self.page_down,
            curses.KEY_PPAGE:                    self.page_up,
            curses.KEY_RIGHT:                    self.right,
            curses.KEY_UP:                       self.up,
            curses.KEY_F1:                       self.help,
            curses.KEY_F2:                       self.quit,
            curses.KEY_F5:                       self.quit_nosave,
            curses.KEY_RESIZE:                   self.resize,
            chr(curses.ascii.ctrl(ord('x'))):    self.quit,
            chr(curses.ascii.ctrl(ord('u'))):    self.del_to_bol,
            chr(curses.ascii.ctrl(ord('k'))):    self.del_to_eol,
            chr(curses.ascii.ctrl(ord('d'))):    self.close,
            chr(curses.ascii.DEL):               self.backspace,
            chr(curses.ascii.NL):                self.insert_line_or_quit,
            chr(curses.ascii.LF):                self.insert_line_or_quit,
            chr(curses.ascii.BS):                self.backspace,
            chr(curses.ascii.ESC):               self.quit_nosave,
            chr(curses.ascii.ETX):               self.close,
            "\n":                                self.insert_line_or_quit,
            -1:                                  self.resize,
        }

    def win_init(self):
        """Set initial editor window size parameters, and reset them if window
        is resized.

        """
        # self.cur_pos is the current y,x position of the cursor
        self.cur_pos_y = 0
        self.cur_pos_x = 0
        # y_offset controls the up-down scrolling feature
        self.y_offset = 0
        self.buffer_idx_y = 0
        self.buffer_idx_x = 0
        # Adjust win_size if resizing
        if self.resize_flag is True:
            self.win_size_x += 1
            self.win_size_y += 1
            self.resize_flag = False
        # Make sure requested window size is < available window size
        self.max_win_size_y, self.max_win_size_x = self.scr.getmaxyx()
        # Adjust max_win_size for maximum possible offsets
        # (e.g. if there is a title and a box)
        self.max_win_size_y = max(0, self.max_win_size_y - 4)
        self.max_win_size_x = max(0, self.max_win_size_x - 3)
        # Keep the input box inside the physical window
        if (self.win_size_y > self.max_win_size_y or
                self.win_size_y < self.win_size_orig_y):
            self.win_size_y = self.max_win_size_y
        if (self.win_size_x > self.max_win_size_x or
                self.win_size_x < self.win_size_orig_x):
            self.win_size_x = self.max_win_size_x
        # Reduce win_size by 1 to account for position starting at 0 instead of
        # 1. E.g. if size=80, then the max size should be 79 (0-79).
        self.win_size_y -= 1
        self.win_size_x -= 1
        # Validate win_location settings
        if self.win_size_x + self.win_location_x >= self.max_win_size_x:
            self.win_location_x = max(0, self.max_win_size_x -
                                      self.win_size_x)
        if self.win_size_y + self.win_location_y >= self.max_win_size_y:
            self.win_location_y = max(0, self.max_win_size_y -
                                      self.win_size_y)
        # Create an extra window for the box outline and/or title, if required
        x_off = y_off = loc_off_y = loc_off_x = 0
        if self.box:
            y_off += 3
            x_off += 2
            loc_off_y += 1
            loc_off_x += 1
        if self.title:
            y_off += 1
            loc_off_y += 1
        if self.box is True or self.title:
            # Make box/title screen bigger than actual text area (stdscr)
            self.boxscr = self.scr.subwin(self.win_size_y + y_off,
                                          self.win_size_x + x_off,
                                          self.win_location_y,
                                          self.win_location_x)
            self.stdscr = self.boxscr.subwin(self.win_size_y,
                                             self.win_size_x,
                                             self.win_location_y + loc_off_y,
                                             self.win_location_x + loc_off_x)
        else:
            self.stdscr = self.scr.subwin(self.win_size_y,
                                          self.win_size_x,
                                          self.win_location_y,
                                          self.win_location_x)
        self.stdscr.keypad(1)

    def left(self):
        if self.cur_pos_x > 0:
            self.cur_pos_x = self.cur_pos_x - 1

    def right(self):
        if self.cur_pos_x < self.win_size_x:
            self.cur_pos_x = self.cur_pos_x + 1

    def up(self):
        if self.cur_pos_y > 0:
            self.cur_pos_y = self.cur_pos_y - 1
        else:
            self.y_offset = max(0, self.y_offset - 1)

    def down(self):
        if (self.cur_pos_y < self.win_size_y - 1 and
                self.buffer_idx_y < len(self.text) - 1):
            self.cur_pos_y = self.cur_pos_y + 1
        elif self.buffer_idx_y == len(self.text) - 1:
            pass
        else:
            self.y_offset = min(self.buffer_rows - self.win_size_y,
                                self.y_offset + 1)

    def end(self):
        self.cur_pos_x = self.buf_length

    def home(self):
        self.cur_pos_x = 0

    def page_up(self):
        self.y_offset = max(0, self.y_offset - self.win_size_y)

    def page_down(self):
        self.y_offset = min(self.buffer_rows - self.win_size_y - 1,
                            self.y_offset + self.win_size_y)
        # Corrects negative offsets
        self.y_offset = max(0, self.y_offset)

    def insert_char(self, c):
        """Given a curses wide character, insert that character in the current
        line. Stop when the maximum line length is reached.

        """
        # Skip non-handled special characters (get_wch returns int value for
        # certain special characters)
        if isinstance(c, int):
            return
        line = list(self.text[self.buffer_idx_y])
        line.insert(self.buffer_idx_x, c)
        if len(line) < self.win_size_x:
            self.text[self.buffer_idx_y] = "".join(line)
            self.cur_pos_x += 1

    def insert_line_or_quit(self):
        """Insert a new line at the cursor. Wrap text from the cursor to the
        end of the line to the next line. If the line is a single line, saves
        and exits.

        """
        if self.max_text_size == 1:
            # Save and quit for single-line entries
            return False
        if len(self.text) == self.max_text_size:
            return
        line = list(self.text[self.buffer_idx_y])
        newline = line[self.cur_pos_x:]
        line = line[:self.cur_pos_x]
        self.text[self.buffer_idx_y] = "".join(line)
        self.text.insert(self.buffer_idx_y + 1, "".join(newline))
        self.buffer_rows = max(self.win_size_y, len(self.text))
        self.cur_pos_x = 0
        self.down()

    def backspace(self):
        """Delete character under cursor and move one space left.

        """
        line = list(self.text[self.buffer_idx_y])
        if self.cur_pos_x > 0:
            if self.cur_pos_x <= len(line):
                # Just backspace if beyond the end of the actual string
                del line[self.buffer_idx_x - 1]
            self.text[self.buffer_idx_y] = "".join(line)
            self.cur_pos_x -= 1
        elif self.cur_pos_x == 0:
            # If at BOL, move cursor to end of previous line
            # (unless already at top of file)
            # If current or previous line is empty, delete it
            if self.y_offset > 0 or self.cur_pos_y > 0:
                self.cur_pos_x = len(self.text[self.buffer_idx_y - 1])
            if not self.text[self.buffer_idx_y]:
                if len(self.text) > 1:
                    del self.text[self.buffer_idx_y]
            elif not self.text[self.buffer_idx_y - 1]:
                del self.text[self.buffer_idx_y - 1]
            self.up()
        self.buffer_rows = max(self.win_size_y, len(self.text))
        # Makes sure leftover rows are visually cleared if deleting rows from
        # the bottom of the text.
        self.stdscr.clear()

    def del_char(self):
        """Delete character under the cursor.

        """
        line = list(self.text[self.buffer_idx_y])
        if line and self.cur_pos_x < len(line):
            del line[self.buffer_idx_x]
        self.text[self.buffer_idx_y] = "".join(line)

    def del_to_eol(self):
        """Delete from cursor to end of current line. (C-k)

        """
        line = list(self.text[self.buffer_idx_y])
        line = line[:self.cur_pos_x]
        self.text[self.buffer_idx_y] = "".join(line)

    def del_to_bol(self):
        """Delete from cursor to beginning of current line. (C-u)

        """
        line = list(self.text[self.buffer_idx_y])
        line = line[self.cur_pos_x:]
        self.text[self.buffer_idx_y] = "".join(line)
        self.cur_pos_x = 0

    def quit(self):
        return False

    def quit_nosave(self):
        self.text = False
        return False

    def help(self):
        """Display help text popup window.

        """
        help_txt = """
        Save and exit                               : F2 or Ctrl-x
                                       (Enter if single-line entry)
        Exit without saving                         : F5 or ESC
        Cursor movement                             : Arrow keys
        Move to beginning of line                   : Home
        Move to end of line                         : End
        Page Up/Page Down                           : PgUp/PgDn
        Backspace/Delete one char left of cursor    : Backspace
        Delete 1 char under cursor                  : Del
        Insert line at cursor                       : Enter
        Delete to end of line                       : Ctrl-k
        Delete to beginning of line                 : Ctrl-u
        Help                                        : F1
        """
        try:
            curses.curs_set(0)
        except:
            pass
        txt = help_txt.split('\n')
        lines = min(self.max_win_size_y, len(txt) + 2)
        cols = min(self.max_win_size_x, max([len(i) for i in txt]) + 2)
        # Only print help text if the window is big enough
        try:
            popup = curses.newwin(lines, cols, 0, 0)
            popup.addstr(1, 1, help_txt)
            popup.box()
        except:
            pass
        else:
            while not popup.getch():
                pass
        finally:
            # Turn back on the cursor
            if self.pw_mode is False:
                curses.curs_set(1)
            # flushinp Needed to prevent spurious F1 characters being written to line
            curses.flushinp()
            self.box_init()

    def resize(self):
        self.resize_flag = True
        self.win_init()
        self.box_init()
        self.text_init("\n".join(self.text))

    def run(self):
        """Main program loop.

        """
        try:
            while True:
                self.stdscr.move(self.cur_pos_y, self.cur_pos_x)
                loop = self.get_key()
                if loop is False or loop == -1:
                    break
                self.buffer_idx_y = self.cur_pos_y + self.y_offset
                self.buf_length = len(self.text[self.buffer_idx_y])
                if self.cur_pos_x > self.buf_length:
                    self.cur_pos_x = self.buf_length
                self.buffer_idx_x = self.cur_pos_x
                self.display()
        except KeyboardInterrupt:
            self.close()
        return self.exit()

    def display(self):
        """Display the editor window and the current contents.

        """
        s = self.text[self.y_offset:(self.y_offset + self.win_size_y) or 1]
        for y, line in enumerate(s):
            try:
                self.stdscr.move(y, 0)
                self.stdscr.clrtoeol()
                if not self.pw_mode:
                    self.stdscr.addstr(y, 0, line)
            except:
                self.close()
        self.stdscr.refresh()
        if self.box:
            self.boxscr.refresh()
        self.scr.refresh()

    def exit(self):
        """Normal exit procedure.

        """
        curses.flushinp()
        try:
            curses.curs_set(0)
        except:  # If invisible cursor not supported
            pass
        curses.noecho()
        if self.text == -1:
            return -1
        elif self.text is False:
            return False
        else:
            return "\n".join(self.text)

    def close(self):
        """Exiting on keyboard interrupt or other curses display errors.

        """
        curses.endwin()
        self.text = -1
        return self.exit()

    def get_key(self):
        try:
            c = self.stdscr.get_wch()
        except KeyboardInterrupt:
            self.close()
        try:
            loop = self.keys[c]()
        except KeyError:
            self.insert_char(c)
            loop = True
        return loop


def main(stdscr, **kwargs):
    return Editor(stdscr, **kwargs)()


def editor(**kwargs):
    return curses.wrapper(main, **kwargs)

########NEW FILE########
__FILENAME__ = filebrowser
# -*- coding: utf-8 -*-
'''
Copyright (C) 2012-2013 Karsten-Kai König <kkoenig@posteo.de>

This file is part of keepassc.

keepassc is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or at your
option) any later version.

keepassc is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with keepassc.  If not, see <http://www.gnu.org/licenses/>.
'''

import curses as cur
from curses.ascii import NL, DEL
from os import listdir
from os.path import expanduser, isdir

from keepassc.editor import Editor

class FileBrowser(object):
    '''This class represents the file browser'''

    def __init__(self, control, ask_for_lf, keyfile, last_file, mode_new = False):

        self.control = control
        self.ask_for_lf = ask_for_lf
        self.keyfile = keyfile
        self.last_file = last_file
        self.mode_new = mode_new
        self.highlight = 0
        self.kdb_file = None
        if self.control.cur_dir[-4:] == '.kdb':
            self.kdb_file = self.control.cur_dir.split('/')[-1]
            self.control.cur_dir = self.control.cur_dir[:-len(self.kdb_file) - 1]
            self.kdb_file = self.control.cur_dir + '/' + self.kdb_file
        self.hidden = True
        self.dir_cont = []
        self.return_flag = False
        self.lookup = {
            cur.KEY_DOWN:   self.nav_down,
            ord('j'):       self.nav_down,
            cur.KEY_UP:     self.nav_up,
            ord('k'):       self.nav_up,
            cur.KEY_LEFT:   self.nav_left,
            ord('h'):       self.nav_left,
            cur.KEY_RIGHT:  self.nav_right,
            ord('l'):       self.nav_right,
            NL:             self.nav_right,
            cur.KEY_RESIZE: self.control.resize_all,
            cur.KEY_F1:     self.browser_help,
            ord('H'):       self.show_hidden,
            ord('o'):       self.open_file,
            cur.KEY_F5:     self.cancel,
            ord('e'):       self.cancel,
            4:              self.close,
            ord('q'):       self.close,
            ord('G'):       self.G_typed,
            ord('/'):       self.find}
        self.find_rem = []
        self.find_pos = 0

    def __call__(self):
        ret = self.get_filepath()
        if self.kdb_file is not None:
            self.control.cur_dir = self.kdb_file
        return ret

    def get_filepath(self):
        '''This method is used to get a filepath, e.g. for 'Save as' '''

        if (self.ask_for_lf is False or self.last_file is None or 
            self.control.config['rem_db'] is False):
            nav = self.control.gen_menu(1, (
                    (1, 0, 'Use the file browser (1)'),
                    (2, 0, 'Type direct path (2)')))
        else:
            nav = self.control.gen_menu(1, (
                    (1, 0, 'Use ' + self.last_file + ' (1)'),
                    (2, 0, 'Use the file browser (2)'),
                    (3, 0, 'Type direct path (3)')))
        if ((self.ask_for_lf is True and self.last_file is not None and 
             nav == 2) or
            ((self.last_file is None or self.ask_for_lf is False) and 
             nav == 1)):
            if self.keyfile is True:
                filepath = self.browser()
            else:
                filepath = self.browser()
                if type(filepath) is str:
                    if filepath[-4:] != '.kdb' and filepath is not False:
                        filename = Editor(self.control.stdscr, max_text_size=1,
                                          win_location=(0, 1), win_size=(1, 80),
                                          title="Filename: ")()
                        if filename == "":
                            return False
                        filepath += '/' + filename + '.kdb'
            return filepath
        if ((self.ask_for_lf is True and self.last_file is not None and 
             nav == 3) or
            ((self.last_file is None or self.ask_for_lf is False) and 
             nav == 2)):
            while True:
                if self.last_file:
                    init = self.last_file
                else:
                    init = ''
                filepath = self.get_direct_filepath()
                if filepath is False:
                    return False
                elif filepath == -1:
                    return -1
                elif ((filepath[-4:] != '.kdb' or isdir(filepath)) and
                      self.keyfile is False):
                    self.control.draw_text(False,
                                           (1, 0, 'Need path to a kdb-file!'),
                                           (3, 0, 'Press any key'))
                    if self.control.any_key() == -1:
                        return -1
                    continue
                else:
                    return filepath
        elif nav == 1:  # it was asked for last file
            return self.last_file
        elif nav == -1:
            return -1
        else:
            return False

    def get_direct_filepath(self):
        '''Get a direct filepath.'''

        e = ''
        show = 0
        rem = []
        cur_dir = ''
        if self.last_file is not None:
            edit = self.last_file
        else:
            edit = ''
        while e != '\n':
            if e == cur.KEY_BACKSPACE or e == chr(DEL) and len(edit) != 0:
                edit = edit[:-1]
                show = 0
                rem = []
                cur_dir = ''
            elif e == cur.KEY_BACKSPACE or e == chr(DEL):
                pass
            elif e == '\x04':
                return -1
            elif e == '':
                pass
            elif e == cur.KEY_F5:
                return False
            elif e == cur.KEY_RESIZE:
                self.control.resize_all()
            elif e == '~':
                edit += expanduser('~/')
                show = 0
                rem = []
                cur_dir = ''
            elif e == '\t':
                if cur_dir == '':
                    last = edit.split('/')[-1]
                    cur_dir = edit[:-len(last)]
                try:
                    dir_cont = listdir(cur_dir)
                except OSError:
                    pass
                else:
                    if len(rem) == 0:
                        for i in dir_cont:
                            if i[:len(last)] == last:
                                rem.append(i)
                    if len(rem) > 0:
                        edit = cur_dir + rem[show]
                    else:
                        edit = cur_dir + last
                    if show + 1 >= len(rem):
                        show = 0
                    else:
                        show += 1
                    if isdir(edit):
                        edit += '/'
            elif type(e) is not int:
                show = 0
                rem = []
                cur_dir = ''
                edit += e

            self.control.draw_text(False, (1, 0, 'Filepath: ' + edit))
            try:
                e = self.control.stdscr.get_wch()
            except KeyboardInterrupt:
                e = '\x04'
        return edit

    def nav_down(self):
        '''Navigate down'''

        if self.highlight < len(self.dir_cont) - 1:
            self.highlight += 1

    def nav_up(self):
        '''Navigate up'''

        if self.highlight > 0:
            self.highlight -= 1

    def nav_left(self):
        '''Navigate left'''

        last = self.control.cur_dir.split('/')[-1]
        self.control.cur_dir = self.control.cur_dir[:-len(last) - 1]
        if self.control.cur_dir == '':
            self.control.cur_dir = '/'
        self.highlight = 0
        self.get_dir_cont()
        self.find_rem = []
        self.find_pos = 0

    def nav_right(self):
        '''Navigate right'''

        self.find_rem = []
        self.find_pos = 0
        if self.dir_cont[self.highlight] == '..':
            last = self.control.cur_dir.split('/')[-1]
            self.control.cur_dir = self.control.cur_dir[:-len(last) - 1]
            if self.control.cur_dir == '':
                self.control.cur_dir = '/'
            self.highlight = 0
            self.get_dir_cont()
        elif isdir(self.control.cur_dir + '/' + self.dir_cont[self.highlight]):
            self.control.cur_dir = (self.control.cur_dir + '/' +
                                    self.dir_cont[self.highlight])
            if self.control.cur_dir[:2] == '//':
                self.control.cur_dir = self.control.cur_dir[1:]
            self.highlight = 0
            self.get_dir_cont()
        else:
            ret = self.control.cur_dir + '/' + self.dir_cont[self.highlight]
            if self.kdb_file is not None:
                self.control.cur_dir = self.kdb_file
            self.return_flag = True
            return ret

    def show_hidden(self):
        '''Show hidden files'''

        if self.hidden is True:
            self.hidden = False
        else:
            self.hidden = True
        self.get_dir_cont()

    def browser_help(self):
        '''Show help'''

        self.control.browser_help(self.mode_new)

    def open_file(self):
        '''Return dir or file for "save as..."'''

        if self.mode_new is True:
            if self.kdb_file is not None:
                ret = self.control.cur_dir
                self.control.cur_dir = self.kdb_file
                self.return_flag = True
                return ret
            else:
                self.return_flag = True
                return self.control.cur_dir

    def cancel(self):
        '''Cancel browser'''

        self.return_flag = True
        return False

    def close(self):
        '''Close KeePassC'''

        self.return_flag = True
        return -1

    def start_gg(self, c):
        '''Enable gg like in vim'''

        gg = chr(c)
        while True:
            try:
                c = self.control.stdscr.getch()
            except KeyboardInterrupt:
                c = 4

            if gg[-1] == 'g' and c == ord('g') and gg[:-1] != '':
                if int(gg[:-1]) > len(self.dir_cont):
                    self.highlight = len(self.dir_cont) -1
                else:
                    self.highlight = int(gg[:-1]) -1
                return True
            elif gg[-1] == 'g' and c == ord('g') and gg[:-1] == '':
                self.highlight = 0
                return True
            elif gg[-1] != 'g' and c == ord('g'):
                gg += 'g'
            elif 48 <= c <= 57 and gg[-1] != 'g':
                gg += chr(c)
            elif c in self.lookup:
                return c

    def G_typed(self):
        '''G typed => last entry (like in vim)'''

        self.highlight = len(self.dir_cont) - 1

    def find(self):
        '''Find a directory or file like in ranger'''

        filename = Editor(self.control.stdscr, max_text_size=1,
                          win_location=(0, 1), win_size=(1, 80),
                          title="Filename to find: ")()
        if filename == '' and self.find_pos < len(self.find_rem) - 1:
            self.find_pos += 1
        elif filename == '':
            self.find_pos = 0
        else:
            self.find_rem = []
            self.find_pos = 0
            for i in self.dir_cont:
                if filename.lower() in i.lower():
                    self.find_rem.append(i)
        if self.find_rem:
            self.highlight = self.dir_cont.index(self.find_rem[self.find_pos])

    def browser(self):
        '''A simple file browser.'''

        self.get_dir_cont()
        if self.dir_cont == -1 or self.dir_cont is False:
            return self.dir_cont

        old_highlight = None
        while True:
            if old_highlight != self.highlight:
                self.control.show_dir(self.highlight, self.dir_cont)
            try:
                c = self.control.stdscr.getch()
            except KeyboardInterrupt:
                c = 4

            if 49 <= c <= 57 or c == ord('g'):
                c = self.start_gg(c)

            old_highlight = self.highlight
            if c in self.lookup:
                ret = self.lookup[c]()
                if self.return_flag is True:
                    return ret

    def get_dir_cont(self):
        '''Get the content of the current dir'''

        try:
            dir_cont = listdir(self.control.cur_dir)
        except OSError:
            self.control.draw_text(False,
                                   (1, 0, 'Was not able to read directory'),
                                   (2, 0, 'Press any key.'))
            if self.control.any_key() == -1:
                return -1
            last = self.control.cur_dir.split('/')[-1]
            self.control.cur_dir = self.control.cur_dir[:-len(last) - 1]
            if self.control.cur_dir == '':
                self.control.cur_dir = '/'
            return False

        rem = []
        for i in dir_cont:
            if ((not isdir(self.control.cur_dir + '/' + i) and not
                    i[-4:] == '.kdb' and self.keyfile is False) or
                    (i[0] == '.' and self.hidden is True)):
                rem.append(i)
        for i in rem:
            dir_cont.remove(i)

        dirs = []
        files = []
        for i in dir_cont:
            if isdir(self.control.cur_dir + '/' + i):
                dirs.append(i)
            else:
                files.append(i)
        dirs.sort()
        files.sort()

        self.dir_cont = []
        self.dir_cont.extend(dirs)
        self.dir_cont.extend(files)
        if not self.control.cur_dir == '/':
            self.dir_cont.insert(0, '..')

########NEW FILE########
__FILENAME__ = helper
# -*- coding: utf-8 -*-
'''
Copyright (C) 2012-2013 Karsten-Kai König <kkoenig@posteo.de>

This file is part of keepassc.

keepassc is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or at your
option) any later version.

keepassc is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with keepassc.  If not, see <http://www.gnu.org/licenses/>.
'''

import struct
from os import makedirs, remove
from os.path import isdir, isfile

from Crypto.Hash import SHA256
from Crypto.Cipher import AES

def parse_config(control):
    '''Parse the config file.

    It's important that a line in the file is written without spaces,
    that means

     - 'foo=bar' is a valid line
     - 'foo = bar' is not a valid one

    '''
    config = {'del_clip': True,  # standard config
              'clip_delay': 20,
              'lock_db': True,
              'lock_delay': 60,
              'rem_db': True,
              'rem_key': False,
              'skip_menu': False,
              'pin': True}

    if isfile(control.config_home):
        try:
            handler = open(control.config_home, 'r')
        except Exception as err:  # don't know if this is good style
            print(err.__str__())
        else:
            for line in handler:
                key, val = line.split('=')
                if val == 'True\n':
                    val = True
                elif val == 'False\n':
                    val = False
                else:
                    val = int(val)
                if key in config:
                    config[key] = val
            handler.close()
    else:  # write standard config
        write_config(control, config)
    return config


def write_config(control, config):
    '''Function to write the config file'''

    config_dir = control.config_home[:-7]
    if not isdir(config_dir):
        if isfile(config_dir):
            remove(config_dir)
        makedirs(config_dir)
    try:
        handler = open(control.config_home, 'w')
    except Exception as err:
        print(err.__str__())
        return False
    else:
        for key, val in config.items():
            handler.write(key + '=' + str(val) + '\n')
        handler.close()
    return True

def transform_key(masterkey, seed1, seed2, rounds):
    """This method creates the key to decrypt the database"""

    if masterkey is None or seed1 is None or seed2 is None or rounds is None:
        raise TypeError('None type not allowed')
    aes = AES.new(seed1, AES.MODE_ECB)

    # Encrypt the created hash
    for i in range(rounds):
        masterkey = aes.encrypt(masterkey)

    # Finally, hash it again...
    sha_obj = SHA256.new()
    sha_obj.update(masterkey)
    masterkey = sha_obj.digest()
    # ...and hash the result together with the randomseed
    sha_obj = SHA256.new()
    sha_obj.update(seed2 + masterkey)
    return sha_obj.digest()

def get_passwordkey(key):
    """This method hashes key"""

    if key is None:
        raise TypeError('None type not allowed')
    sha = SHA256.new()
    sha.update(key.encode('utf-8'))
    return sha.digest()

def get_filekey(keyfile):
    """This method creates a key from a keyfile."""

    try:
        handler = open(keyfile, 'rb')
        buf = handler.read()
    except:
        raise OSError('Could not open or read file.')
    else:
        handler.close()
    sha = SHA256.new()
    if len(buf) == 33:
        sha.update(buf)
        return sha.digest()
    elif len(buf) == 65:
        sha.update(struct.unpack('<65s', buf)[0].decode())
        return sha.digest()
    else:
        while buf:
            if len(buf) <= 2049:
                sha.update(buf)
                buf = []
            else:
                sha.update(buf[:2048])
                buf = buf[2048:]
        return sha.digest()

def get_remote_filekey(buf):
    """This method creates a key from a keyfile."""

    sha = SHA256.new()
    if len(buf) == 33:
        sha.update(buf)
        return sha.digest()
    elif len(buf) == 65:
        sha.update(struct.unpack('<65s', buf)[0].decode())
        return sha.digest()
    else:
        while buf:
            if len(buf) <= 2049:
                sha.update(buf)
                buf = []
            else:
                sha.update(buf[:2048])
                buf = buf[2048:]
        return sha.digest()

def get_key(password, keyfile, remote = False):
    """Get a key generated from KeePass-password and -keyfile"""

    if password is None and keyfile is None:
        raise TypeError('None type not allowed')
    elif password is None:
        if remote is True:
            masterkey = get_remote_filekey(keyfile)
        else:
            masterkey = get_filekey(keyfile)
    elif password is not None and keyfile is not None:
        passwordkey = get_passwordkey(password)
        if remote is True:
            filekey = get_remote_filekey(keyfile)
        else:
            filekey = get_filekey(keyfile)
        sha = SHA256.new()
        sha.update(passwordkey+filekey)
        masterkey = sha.digest()
    else:
        masterkey = get_passwordkey(password)

    return masterkey


########NEW FILE########
__FILENAME__ = server
'''
Copyright (C) 2012-2013 Karsten-Kai König <kkoenig@posteo.de>

This file is part of keepassc.

keepassc is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or at your
option) any later version.

keepassc is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with keepassc.  If not, see <http://www.gnu.org/licenses/>.
'''

"""This file implements the server daemon.

Decorator:
    class waitDecorator(object)

Classes:
    class Server(Connection, Daemon)
"""

import logging
import signal
import socket
import ssl
import sys
import time
import threading
from datetime import datetime
from os import chdir
from os.path import join, expanduser, realpath

from kppy.database import KPDBv1
from kppy.exceptions import KPError

from keepassc.conn import *
from keepassc.daemon import Daemon
from keepassc.helper import get_key, transform_key

class waitDecorator(object):
    def __init__(self, func):
        self.func = func
        self.lock = False

    def __get__(self, obj, type=None):
        return self.__class__(self.func.__get__(obj, type))

    def __call__(self, *args):
        while True:
            if self.lock == True:
                time.sleep(1)
                continue
            else:
                self.lock = True
                self.func(args[0], args[1])
                self.lock = False
                break
        
class Server(Daemon):
    """The KeePassC server daemon"""

    def __init__(self, pidfile, loglevel, logfile, address = None,
                 port = 50002, db = None, password = None, keyfile = None,
                 tls = False, tls_dir = None, tls_port = 50003, 
                 tls_req = False):
        Daemon.__init__(self, pidfile)

        try:
            logdir = realpath(expanduser(getenv('XDG_DATA_HOME')))
        except:
            logdir = realpath(expanduser('~/.local/share'))
        finally:
            logfile = join(logdir, 'keepassc', logfile)

        logging.basicConfig(format='[%(levelname)s] in %(filename)s:'
                                   '%(funcName)s at %(asctime)s\n%(message)s',
                            level=loglevel, filename=logfile,
                            filemode='a')

        if db is None:
            print('Need a database path')
            sys.exit(1)
            
        self.db_path = realpath(expanduser(db))

        # To use this idiom only once, I store the keyfile path
        # as a class attribute
        if keyfile is not None:
            keyfile = realpath(expanduser(keyfile))
        else:
            keyfile = None

        chdir("/var/empty")

        try:
            self.db = KPDBv1(self.db_path, password, keyfile)
            self.db.load()
        except KPError as err:
            print(err)
            logging.error(err.__str__())
            sys.exit(1)

        self.lookup = {
            b'FIND': self.find,
            b'GET': self.send_db,
            b'CHANGESECRET': self.change_password,
            b'NEWG': self.create_group,
            b'NEWE': self.create_entry,
            b'DELG': self.delete_group,
            b'DELE': self.delete_entry,
            b'MOVG': self.move_group,
            b'MOVE': self.move_entry,
            b'TITG': self.set_g_title,
            b'TITE': self.set_e_title,
            b'USER': self.set_e_user,
            b'URL': self.set_e_url,
            b'COMM': self.set_e_comment,
            b'PASS': self.set_e_pass,
            b'DATE': self.set_e_exp}

        self.sock = None
        self.net_sock = None
        self.tls_sock = None
        self.tls_req = tls_req
        
        if tls is True or tls_req is True:
            self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            cert = join(tls_dir, "servercert.pem")
            key = join(tls_dir, "serverkey.pem")
            self.context.load_cert_chain(certfile=cert, keyfile=key)
        else:
            self.context = None

        try:
            # Listen for commands
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind(("localhost", 50000))
            self.sock.listen(5)
        except OSError as err:
            print(err)
            logging.error(err.__str__())
            sys.exit(1)
        else:
            logging.info('Server socket created on localhost:50000')

        if self.tls_req is False and address is not None:
            try:
                # Listen for commands
                self.net_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.net_sock.bind((address, port))
                self.net_sock.listen(5)
            except OSError as err:
                print(err)
                logging.error(err.__str__())
                sys.exit(1)
            else:
                logging.info('Server socket created on '+address+':'+
                             str(port))

        if self.context is not None and address is not None:
            try:
                # Listen for commands
                self.tls_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.tls_sock.bind((address, tls_port))
                self.tls_sock.listen(5)
            except OSError as err:
                print(err)
                logging.error(err.__str__())
                sys.exit(1)
            else:
                logging.info('TLS-Server socket created on '+address+':'+
                             str(tls_port))


        #Handle SIGTERM
        signal.signal(signal.SIGTERM, self.handle_sigterm)

    def check_password(self, password, keyfile):
        """Check received password"""
        
        master = get_key(password, keyfile, True)
        remote_final =  transform_key(master, self.db._transf_randomseed,
                                      self.db._final_randomseed, 
                                      self.db._key_transf_rounds)
        master = get_key(self.db.password, self.db.keyfile)
        final =  transform_key(master, self.db._transf_randomseed,
                               self.db._final_randomseed, 
                               self.db._key_transf_rounds)
        return (remote_final == final)

    def run(self):
        """Overide Daemon.run() and provide socets"""
        
        try:
            local_thread = threading.Thread(target=self.handle_non_tls,
                                            args=(self.sock,))
            local_thread.start()
            if self.tls_req is False:
                non_tls_thread = threading.Thread(target=self.handle_non_tls,
                                                  args=(self.net_sock,))
                non_tls_thread.start()
            if self.context is not None:
                tls_thread = threading.Thread(target=self.handle_tls)
                tls_thread.start()
        except OSError as err:
            logging.error(err.__str__())
            self.stop()

    def handle_non_tls(self, sock):
        while True:
            try:
                conn, client = sock.accept()
            except OSError as err:
                # For correct closing
                if "Bad file descriptor" in err.__str__():
                    break
                logging.error(err.__str__())
            else:
                logging.info('Connection from '+client[0]+':'+str(client[1]))
                client_thread = threading.Thread(target=self.handle_client, 
                                                 args=(conn,client,))
                client_thread.daemon = True
                client_thread.start()

    def handle_tls(self):
        while True:
            try:
                conn_tmp, client = self.tls_sock.accept()
                conn = self.context.wrap_socket(conn_tmp, server_side = True)
            except (ssl.SSLError, OSError) as err:
                # For correct closing
                if "Bad file descriptor" in err.__str__():
                    break
                logging.error(err.__str__())
            else:
                logging.info('Connection from '+client[0]+':'+str(client[1]))
                client_thread = threading.Thread(target=self.handle_client, 
                                                 args=(conn, client,))
                client_thread.daemon = True
                client_thread.start()

    def handle_client(self, conn, client):
        conn.settimeout(60)

        try:
            msg = receive(conn)
            parts = msg.split(b'\xB2\xEA\xC0')
            parts.append(client)
            password = parts.pop(0)
            keyfile = parts.pop(0)
            cmd = parts.pop(0)

            if password == b'':
                password = None
            else:
                password = password.decode()
            if keyfile == b'':
                keyfile = None
            if self.check_password(password, keyfile) is False:
                sendmsg(conn, b'FAIL: Wrong password')
                raise OSError("Received wrong password")
        except OSError as err:
            logging.error(err.__str__())
        else:
            try:
                if cmd in self.lookup:
                    self.lookup[cmd](conn, parts)
                else:
                    logging.error('Received a wrong command')
                    sendmsg(conn, b'FAIL: Command isn\'t available')
            except (OSError, ValueError) as err:
                logging.error(err.__str__())
        finally:
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()

    def find(self, conn, parts):
        """Find entries and send them to connection"""

        title = parts.pop(0)
        msg = ''
        for i in self.db.entries:
            if title.decode().lower() in i.title.lower():
                msg += 'Title: '+i.title+'\n'
                if i.url is not None:
                    msg += 'URL: '+i.url+'\n'
                if i.username is not None:
                    msg += 'Username: '+i.username+'\n'
                if i.password is not None:
                    msg += 'Password: '+i.password+'\n'
                if i.creation is not None:
                    msg += 'Creation: '+i.creation.__str__()+'\n'
                if i.last_access is not None:
                    msg += 'Access: '+i.last_access.__str__()+'\n'
                if i.last_mod is not None:
                    msg += 'Modification: '+i.last_mod.__str__()+'\n'
                if i.expire is not None:
                    msg += 'Expiration: '+i.expire.__str__()+'\n'
                if i.comment is not None:
                    msg += 'Comment: '+i.comment+'\n'
                msg += '\n'
        sendmsg(conn, msg.encode())

    def send_db(self, conn, parts):
        with open(self.db_path, 'rb') as handler:
            buf = handler.read()
        sendmsg(conn, buf)

    @waitDecorator
    def create_group(self, conn, parts):
        title = parts.pop(0).decode()
        root = int(parts.pop(0))
        if root == 0:
            self.db.create_group(title)
        else:
            for i in self.db.groups:
                if i.id_ == root:
                    self.db.create_group(title, i)
                    break
                elif i is self.db.groups[-1]:
                    sendmsg(conn, b"FAIL: Parent doesn't exist anymore. "
                                       b"You should refresh")
                    return
        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def change_password(self, conn, parts):
        client_add = parts[-1][0]
        if client_add != "localhost" and client_add != "127.0.0.1":
            sendmsg(conn, b'Password change from remote is not allowed')

        new_password = parts.pop(0).decode()
        new_keyfile = parts.pop(0).decode()
        if new_password == '':
            self.db.password = None
        else:
            self.db.password = new_password

        if new_keyfile == '':
            self.db.keyfile = None
        else:
            self.db.keyfile = realpath(expanduser(new_keyfile))

        self.db.save()
        sendmsg(conn, b"Password changed")

    @waitDecorator
    def create_entry(self, conn, parts):
        title = parts.pop(0).decode()
        url = parts.pop(0).decode()
        username = parts.pop(0).decode()
        password = parts.pop(0).decode()
        comment = parts.pop(0).decode()
        y = int(parts.pop(0))
        mon = int(parts.pop(0))
        d = int(parts.pop(0))
        root = int(parts.pop(0))

        for i in self.db.groups:
            if i.id_ == root:
                self.db.create_entry(i, title, 1, url, username, password,
                                     comment, y, mon, d)
                break
            elif i is self.db.groups[-1]:
                sendmsg(conn, b"FAIL: Group for entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])
    
    @waitDecorator
    def delete_group(self, conn, parts):
        group_id = int(parts.pop(0))
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()

        for i in self.db.groups:
            if i.id_ == group_id:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Group was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to delete this group try it again.")
                    return
                i.remove_group()
                break
            elif i is self.db.groups[-1]:
                sendmsg(conn, b"FAIL: Group doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def delete_entry(self, conn, parts):
        uuid = parts.pop(0)
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()
       
        for i in self.db.entries:
            if i.uuid == uuid:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Entry was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to delete this entry try it again.")
                    return
                i.remove_entry()
                break
            elif i is self.db.entries[-1]:
                sendmsg(conn, b"FAIL: Entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def move_group(self, conn, parts):
        group_id = int(parts.pop(0))
        root = int(parts.pop(0))

        for i in self.db.groups:
            if i.id_ == group_id:
                if root == 0:
                    i.move_group(self.db.root_group)
                else:
                    for j in self.db.groups:
                        if j.id_ == root:
                            i.move_group(j)
                            break
                        elif j is self.db.groups[-1]:
                            sendmsg(conn, b"FAIL: New parent doesn't "
                                               b"exist anymore. You should "
                                               b"refresh")
                            return
                break
            elif i is self.db.groups[-1]:
                sendmsg(conn, b"FAIL: Group doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def move_entry(self, conn, parts):
        uuid = parts.pop(0)
        root = int(parts.pop(0))

        for i in self.db.entries:
            if i.uuid == uuid:
                for j in self.db.groups:
                    if j.id_ == root:
                        i.move_entry(j)
                        break
                    elif j is self.db.groups[-1]:
                        sendmsg(conn, b"FAIL: New parent doesn't exist "
                                           b"anymore. You should refresh")
                        return
                break
            elif i is self.db.entries[-1]:
                sendmsg(conn, b"FAIL: Entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])
        
    @waitDecorator
    def set_g_title(self, conn, parts):
        title = parts.pop(0).decode()
        group_id = int(parts.pop(0))
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()

        for i in self.db.groups:
            if i.id_ == group_id:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Group was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to edit this group try it again.")
                    return
                i.set_title(title)
                break
            elif i is self.db.groups[-1]:
                sendmsg(conn, b"FAIL: Group doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def set_e_title(self, conn, parts):
        title = parts.pop(0).decode()
        uuid = parts.pop(0)
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()

        for i in self.db.entries:
            if i.uuid == uuid:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Entry was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to edit this entry try it again.")
                    return
                i.set_title(title)
                break
            elif i is self.db.entries[-1]:
                sendmsg(conn, b"FAIL: Entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def set_e_user(self, conn, parts):
        username = parts.pop(0).decode()
        uuid = parts.pop(0)
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()

        for i in self.db.entries:
            if i.uuid == uuid:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Entry was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to edit this entry try it again.")
                    return
                i.set_username(username)
                break
            elif i is self.db.entries[-1]:
                sendmsg(conn, b"FAIL: Entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def set_e_url(self, conn, parts):
        url = parts.pop(0).decode()
        uuid = parts.pop(0)
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()

        for i in self.db.entries:
            if i.uuid == uuid:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Entry was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to edit this entry try it again.")
                    return
                i.set_url(url)
                break
            elif i is self.db.entries[-1]:
                sendmsg(conn, b"FAIL: Entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def set_e_comment(self, conn, parts):
        comment = parts.pop(0).decode()
        uuid = parts.pop(0)
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()

        for i in self.db.entries:
            if i.uuid == uuid:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Entry was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to edit this entry try it again.")
                    return
                i.set_comment(comment)
                break
            elif i is self.db.entries[-1]:
                sendmsg(conn, b"FAIL: Entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def set_e_pass(self, conn, parts):
        password = parts.pop(0).decode()
        uuid = parts.pop(0)
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()

        for i in self.db.entries:
            if i.uuid == uuid:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Entry was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to edit this entry try it again.")
                    return
                i.set_password(password)
                break
            elif i is self.db.entries[-1]:
                sendmsg(conn, b"FAIL: Entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def set_e_exp(self, conn, parts):
        y = int(parts.pop(0))
        mon = int(parts.pop(0))
        d = int(parts.pop(0))
        uuid = parts.pop(0)
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()

        for i in self.db.entries:
            if i.uuid == uuid:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Entry was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to edit this entry try it again.")
                    return
                i.set_expire(y, mon, d)
                break
            elif i is self.db.entries[-1]:
                sendmsg(conn, b"FAIL: Entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    def check_last_mod(self, obj, time):
       return obj.last_mod.timetuple() > time 

    def handle_sigterm(self, signum, frame):
        self.db.lock()
        if self.sock is not None:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        if self.net_sock is not None:
            self.net_sock.shutdown(socket.SHUT_RDWR)
            self.net_sock.close()
        if self.tls_sock is not None:
            self.tls_sock.shutdown(socket.SHUT_RDWR)
            self.tls_sock.close()

########NEW FILE########
