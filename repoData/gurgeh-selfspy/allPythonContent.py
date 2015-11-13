__FILENAME__ = activity_store
# Copyright 2012 David Fendrich

# This file is part of Selfspy

# Selfspy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Selfspy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Selfspy.  If not, see <http://www.gnu.org/licenses/>.

import time
from datetime import datetime
NOW = datetime.now

import sqlalchemy

import platform
if platform.system() == 'Darwin':
    from selfspy import sniff_cocoa as sniffer
elif platform.system() == 'Windows':
    from selfspy import sniff_win as sniffer
else:
    from selfspy import sniff_x as sniffer

from selfspy import models
from selfspy.models import Process, Window, Geometry, Click, Keys


SKIP_MODIFIERS = {"", "Shift_L", "Control_L", "Super_L", "Alt_L", "Super_R", "Control_R", "Shift_R", "[65027]"}  # [65027] is AltGr in X for some ungodly reason.

SCROLL_BUTTONS = {4, 5, 6, 7}
SCROLL_COOLOFF = 10  # seconds


class Display:
    def __init__(self):
        self.proc_id = None
        self.win_id = None
        self.geo_id = None


class KeyPress:
    def __init__(self, key, time, is_repeat):
        self.key = key
        self.time = time
        self.is_repeat = is_repeat


class ActivityStore:
    def __init__(self, db_name, encrypter=None, store_text=True, repeat_char=True):
        self.session_maker = models.initialize(db_name)

        models.ENCRYPTER = encrypter

        self.store_text = store_text
        self.repeat_char = repeat_char
        self.curtext = u""

        self.key_presses = []
        self.mouse_path = []

        self.current_window = Display()

        self.last_scroll = {button: 0 for button in SCROLL_BUTTONS}

        self.last_key_time = time.time()
        self.last_commit = time.time()

        self.started = NOW()

    def trycommit(self):
        self.last_commit = time.time()
        for _ in xrange(1000):
            try:
                self.session.commit()
                break
            except sqlalchemy.exc.OperationalError:
                time.sleep(1)
            except:
               self.session.rollback()

    def run(self):
        self.session = self.session_maker()

        self.sniffer = sniffer.Sniffer()
        self.sniffer.screen_hook = self.got_screen_change
        self.sniffer.key_hook = self.got_key
        self.sniffer.mouse_button_hook = self.got_mouse_click
        self.sniffer.mouse_move_hook = self.got_mouse_move

        self.sniffer.run()

    def got_screen_change(self, process_name, window_name, win_x, win_y, win_width, win_height):
        """ Receives a screen change and stores any changes. If the process or window has
            changed it will also store any queued pressed keys.
            process_name is the name of the process running the current window
            window_name is the name of the window
            win_x is the x position of the window
            win_y is the y position of the window
            win_width is the width of the window
            win_height is the height of the window """
        cur_process = self.session.query(Process).filter_by(name=process_name).scalar()
        if not cur_process:
            cur_process = Process(process_name)
            self.session.add(cur_process)

        cur_geometry = self.session.query(Geometry).filter_by(xpos=win_x,
                                                              ypos=win_y,
                                                              width=win_width,
                                                              height=win_height).scalar()
        if not cur_geometry:
            cur_geometry = Geometry(win_x, win_y, win_width, win_height)
            self.session.add(cur_geometry)

        cur_window = self.session.query(Window).filter_by(title=window_name,
                                                          process_id=cur_process.id).scalar()
        if not cur_window:
            cur_window = Window(window_name, cur_process.id)
            self.session.add(cur_window)

        if not (self.current_window.proc_id == cur_process.id
                and self.current_window.win_id == cur_window.id):
            self.trycommit()
            self.store_keys()  # happens before as these keypresses belong to the previous window
            self.current_window.proc_id = cur_process.id
            self.current_window.win_id = cur_window.id
            self.current_window.geo_id = cur_geometry.id

    def filter_many(self):
        specials_in_row = 0
        lastpress = None
        newpresses = []
        for press in self.key_presses:
            key = press.key
            if specials_in_row and key != lastpress.key:
                if specials_in_row > 1:
                    lastpress.key = '%s]x%d>' % (lastpress.key[:-2], specials_in_row)

                newpresses.append(lastpress)
                specials_in_row = 0

            if len(key) > 1:
                specials_in_row += 1
                lastpress = press
            else:
                newpresses.append(press)

        if specials_in_row:
            if specials_in_row > 1:
                lastpress.key = '%s]x%d>' % (lastpress.key[:-2], specials_in_row)
            newpresses.append(lastpress)

        self.key_presses = newpresses

    def store_keys(self):
        """ Stores the current queued key-presses """
        if self.repeat_char:
            self.filter_many()

        if self.key_presses:
            keys = [press.key for press in self.key_presses]
            timings = [press.time for press in self.key_presses]
            add = lambda count, press: count + (0 if press.is_repeat else 1)
            nrkeys = reduce(add, self.key_presses, 0)

            curtext = u""
            if not self.store_text:
                keys = []
            else:
                curtext = ''.join(keys)

            self.session.add(Keys(curtext.encode('utf8'),
                                  keys,
                                  timings,
                                  nrkeys,
                                  self.started,
                                  self.current_window.proc_id,
                                  self.current_window.win_id,
                                  self.current_window.geo_id))

            self.trycommit()

            self.started = NOW()
            self.key_presses = []
            self.last_key_time = time.time()

    def got_key(self, keycode, state, string, is_repeat):
        """ Receives key-presses and queues them for storage.
            keycode is the code sent by the keyboard to represent the pressed key
            state is the list of modifier keys pressed, each modifier key should be represented
                  with capital letters and optionally followed by an underscore and location
                  specifier, i.e: SHIFT or SHIFT_L/SHIFT_R, ALT, CTRL
            string is the string representation of the key press
            repeat is True if the current key is a repeat sent by the keyboard """
        now = time.time()

        if string in SKIP_MODIFIERS:
            return

        if len(state) > 1 or (len(state) == 1 and state[0] != "Shift"):
            string = '<[%s: %s]>' % (' '.join(state), string)
        elif len(string) > 1:
            string = '<[%s]>' % string

        self.key_presses.append(KeyPress(string, now - self.last_key_time, is_repeat))
        self.last_key_time = now

    def store_click(self, button, x, y):
        """ Stores incoming mouse-clicks """
        self.session.add(Click(button,
                               True,
                               x, y,
                               len(self.mouse_path),
                               self.current_window.proc_id,
                               self.current_window.win_id,
                               self.current_window.geo_id))
        self.mouse_path = []
        self.trycommit()

    def got_mouse_click(self, button, x, y):
        """ Receives mouse clicks and sends them for storage.
            Mouse buttons: left: 1, middle: 2, right: 3, scroll up: 4, down:5, left:6, right:7
            x,y are the coordinates of the keypress
            press is True if it pressed down, False if released"""
        if button in [4, 5, 6, 7]:
            if time.time() - self.last_scroll[button] < SCROLL_COOLOFF:
                return
            self.last_scroll[button] = time.time()

        self.store_click(button, x, y)

    def got_mouse_move(self, x, y):
        """ Queues mouse movements.
            x,y are the new coorinates on moving the mouse"""
        self.mouse_path.append([x, y])

    def close(self):
        """ stops the sniffer and stores the latest keys. To be used on shutdown of program"""
        self.sniffer.cancel()
        self.store_keys()

    def change_password(self, new_encrypter):
        self.session = self.session_maker()
        keys = self.session.query(Keys).all()
        for k in keys:
            dtext = k.decrypt_text()
            dkeys = k.decrypt_keys()
            k.encrypt_text(dtext, new_encrypter)
            k.encrypt_keys(dkeys, new_encrypter)
        self.session.commit()

########NEW FILE########
__FILENAME__ = check_password
# Copyright 2012 David Fendrich

# This file is part of Selfspy

# Selfspy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Selfspy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Selfspy.  If not, see <http://www.gnu.org/licenses/>.

import os

DIGEST_NAME = 'password.digest'
MAGIC_STRING = '\xc5\x7fdh\x05\xf6\xc5=\xcfh\xafv\xc0\xf4\x13i*.O\xf6\xc2\x8d\x0f\x87\xdb\x9f\xc2\x88\xac\x95\xf8\xf0\xf4\x96\xe9\x82\xd1\xca[\xe5\xa32\xa0\x03\nD\x12\n\x1dr\xbc\x03\x9bE\xd3q6\x89Cwi\x10\x92\xdf(#\x8c\x87\x1b3\xd6\xd4\x8f\xde)\xbe\x17\xbf\xe4\xae\xb73\\\xcb\x7f\xd3\xc4\x89\xd0\x88\x07\x90\xd8N,\xbd\xbd\x93j\xc7\xa3\xec\xf3P\xff\x11\xde\xc9\xd6 \x98\xe8\xbc\xa0|\x83\xe90Nw\xe4=\xb53\x08\xf0\x14\xaa\xf9\x819,X~\x8e\xf7mB\x13\xe9;\xde\x9e\x10\xba\x19\x95\xd4p\xa7\xd2\xa9o\xbdF\xcd\x83\xec\xc5R\x17":K\xceAiX\xc1\xe8\xbe\xb8\x04m\xbefA8\x99\xee\x00\x93\xb4\x00\xb3\xd4\x8f\x00@Q\xe9\xd5\xdd\xff\x8d\x93\xe3w6\x8ctRQK\xa9\x97a\xc1UE\xdfv\xda\x15\xf5\xccA)\xec^]AW\x17/h)\x12\x89\x15\x0e#8"\x7f\x16\xd6e\x91\xa6\xd8\xea \xb9\xdb\x93W\xce9\xf2a\xe7\xa7T=q'


def check(data_dir, decrypter, read_only=False):
    fname = os.path.join(data_dir, DIGEST_NAME)
    if os.path.exists(fname):
        if decrypter is None:
            return False
        f = open(fname, 'rb')
        s = f.read()
        f.close()
        return decrypter.decrypt(s) == MAGIC_STRING
    else:
        if decrypter is not None:
            if read_only:
                return False
            else:
                s = decrypter.encrypt(MAGIC_STRING)
                f = open(fname, 'wb')
                f.write(s)
                f.close()
        return True

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python

# Copyright 2012 Bjarte Johansen

# This file is part of Selfspy

# Selfspy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Selfspy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Selfspy.  If not, see <http://www.gnu.org/licenses/>.

DATA_DIR = '~/.selfspy'
DBNAME = 'selfspy.sqlite'
LOCK_FILE = 'selfspy.pid'
LOCK = None

########NEW FILE########
__FILENAME__ = models
# Copyright 2012 David Fendrich

# This file is part of Selfspy

# Selfspy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Selfspy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Selfspy.  If not, see <http://www.gnu.org/licenses/>.

import zlib
import json
import re

import datetime

from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Index, Column, Boolean, Integer, Unicode, DateTime, Binary, ForeignKey, create_engine
from sqlalchemy.orm import sessionmaker, relationship, backref


def initialize(fname):
    engine = create_engine('sqlite:///%s' % fname)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

ENCRYPTER = None

Base = declarative_base()


class SpookMixin(object):

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.now, index=True)


class Process(SpookMixin, Base):
    name = Column(Unicode, index=True, unique=True)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<Process '%s'>" % self.name


class Window(SpookMixin, Base):
    title = Column(Unicode, index=True)

    process_id = Column(Integer, ForeignKey('process.id'), nullable=False, index=True)
    process = relationship("Process", backref=backref('windows'))

    def __init__(self, title, process_id):
        self.title = title
        self.process_id = process_id

    def __repr__(self):
        return "<Window '%s'>" % (self.title)

    
class Geometry(SpookMixin, Base):
    xpos = Column(Integer, nullable=False)
    ypos = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)

    Index('idx_geo', 'xpos', 'ypos', 'width', 'height')

    def __init__(self, x, y, width, height):
        self.xpos = x
        self.ypos = y
        self.width = width
        self.height = height

    def __repr__(self):
        return "<Geometry (%d, %d), (%d, %d)>" % (self.xpos, self.ypos, self.width, self.height)

    
class Click(SpookMixin, Base):
    button = Column(Integer, nullable=False)
    press = Column(Boolean, nullable=False)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    nrmoves = Column(Integer, nullable=False)

    process_id = Column(Integer, ForeignKey('process.id'), nullable=False, index=True)
    process = relationship("Process", backref=backref('clicks'))

    window_id = Column(Integer, ForeignKey('window.id'), nullable=False)
    window = relationship("Window", backref=backref('clicks'))
    
    geometry_id = Column(Integer, ForeignKey('geometry.id'), nullable=False)
    geometry = relationship("Geometry", backref=backref('clicks'))

    def __init__(self, button, press, x, y, nrmoves, process_id, window_id, geometry_id):
        self.button = button
        self.press = press
        self.x = x
        self.y = y
        self.nrmoves = nrmoves

        self.process_id = process_id
        self.window_id = window_id
        self.geometry_id = geometry_id

    def __repr__(self):
        return "<Click (%d, %d), (%d, %d, %d)>" % (self.x, self.y, self.button, self.press, self.nrmoves)

    
def pad(s, padnum):
    ls = len(s)
    if ls % padnum == 0:
        return s
    return s + '\0' * (padnum - (ls % padnum))


def maybe_encrypt(s, other_encrypter=None):
    if other_encrypter is not None:
        s = pad(s, 8)
        s = other_encrypter.encrypt(s)
    elif ENCRYPTER:
        s = pad(s, 8)
        s = ENCRYPTER.encrypt(s)
    return s


def maybe_decrypt(s, other_encrypter=None):
    if other_encrypter is not None:
        s = other_encrypter.decrypt(s)
    elif ENCRYPTER:
        s = ENCRYPTER.decrypt(s)
    return s


class Keys(SpookMixin, Base):
    text = Column(Binary, nullable=False)
    started = Column(DateTime, nullable=False)

    process_id = Column(Integer, ForeignKey('process.id'), nullable=False, index=True)
    process = relationship("Process", backref=backref('keys'))

    window_id = Column(Integer, ForeignKey('window.id'), nullable=False)
    window = relationship("Window", backref=backref('keys'))

    geometry_id = Column(Integer, ForeignKey('geometry.id'), nullable=False)
    geometry = relationship("Geometry", backref=backref('keys'))

    nrkeys = Column(Integer, index=True)

    keys = Column(Binary)
    timings = Column(Binary)

    def __init__(self, text, keys, timings, nrkeys, started, process_id, window_id, geometry_id):
        ztimings = zlib.compress(json.dumps(timings))

        self.encrypt_text(text)
        self.encrypt_keys(keys)

        self.nrkeys = nrkeys
        self.timings = ztimings
        self.started = started

        self.process_id = process_id
        self.window_id = window_id
        self.geometry_id = geometry_id

    def encrypt_text(self, text, other_encrypter=None):
        ztext = maybe_encrypt(text, other_encrypter=other_encrypter)
        self.text = ztext

    def encrypt_keys(self, keys, other_encrypter=None):
        zkeys = maybe_encrypt(zlib.compress(json.dumps(keys)),
                              other_encrypter=other_encrypter)
        self.keys = zkeys

    def decrypt_text(self):
        return maybe_decrypt(self.text)

    def decrypt_humanreadable(self):
        return self.to_humanreadable(self.decrypt_text())

    def decrypt_keys(self):
        keys = maybe_decrypt(self.keys)
        return json.loads(zlib.decompress(keys))

    def to_humanreadable(self, text):
        backrex = re.compile("\<\[Backspace\]x?(\d+)?\>",re.IGNORECASE)
        matches = backrex.search(text)
        while matches is not None:
            backspaces = matches.group(1)
            try:
                deletechars = int(backspaces)
            except TypeError:
                deletechars = 1

            newstart = matches.start() - deletechars
            if newstart < 0:
                newstart = 0

            text = (text[:newstart] + text[matches.end():])
            matches = backrex.search(text)
        return text

    def load_timings(self):
        return json.loads(zlib.decompress(self.timings))

    def __repr__(self):
        return "<Keys %s>" % self.nrkeys

########NEW FILE########
__FILENAME__ = password_dialog
# Copyright 2012 David Fendrich

# This file is part of Selfspy

# Selfspy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Selfspy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Selfspy.  If not, see <http://www.gnu.org/licenses/>.

import sys
import getpass

from Tkinter import Tk
from tkSimpleDialog import Dialog


def get_password(verify=None, message=None):
    if (not verify):
        pw = get_user_password(verify, message)
    else:
        pw = get_keyring_password(verify)

    if pw == None:
        pw = get_user_password(verify, message)

    return pw


def get_user_password(verify, message=None, force_save=False):
    if sys.stdin.isatty():
        pw = get_tty_password(verify, message, force_save)
    else:
        pw = get_tk_password(verify, message, force_save)

    return pw


def get_keyring_password(verify, message=None):
    pw = None
    try:
        import keyring

        usr = getpass.getuser()
        pw = keyring.get_password('Selfspy', usr)

        if pw is not None:
            if (not verify) or not verify(pw):
                print 'The keyring password is not valid. Please, input the correct one.'
                pw = get_user_password(verify, message, force_save=True)
    except ImportError:
        print 'keyring library not found'

    return pw


def set_keyring_password(password):
    try:
        import keyring
        usr = getpass.getuser()
        keyring.set_password('Selfspy', usr, password)
    except ImportError:
        print 'Unable to save password to keyring (library not found)'
    except NameError:
        pass
    except:
        print 'Unable to save password to keyring'


def get_tty_password(verify, message=None, force_save=False):
    verified = False
    for i in xrange(3):
        if message:
            pw = getpass.getpass(message)
        else:
            pw = getpass.getpass()
        if (not verify) or verify(pw):
            verified = True
            break

    if not verified:
        print 'Password failed'
        sys.exit(1)

    if not force_save:
        while True:
            store = raw_input("Do you want to store the password in the keychain [Y/N]: ")
            if store.lower() in ['n', 'y']:
                break
        save_to_keychain = store.lower() == 'y'
    else:
        save_to_keychain = True

    if save_to_keychain:
        set_keyring_password(pw)

    return pw


def get_tk_password(verify, message=None, force_save=False):
    root = Tk()
    root.withdraw()
    if message is None:
        message = 'Password'

    while True:
        pw, save_to_keychain = PasswordDialog(title='Selfspy encryption password',
                            prompt=message,
                            parent=root)
        if pw is None:
            return ""

        if (not verify) or verify(pw):
            break

    if save_to_keychain or force_save:
        set_keyring_password(pw)

    return pw


class PasswordDialog(Dialog):

    def __init__(self, title, prompt, parent):
        self.prompt = prompt
        Dialog.__init__(self, parent, title)

    def body(self, master):
        from Tkinter import Label
        from Tkinter import Entry
        from Tkinter import Checkbutton
        from Tkinter import IntVar
        from Tkinter import W

        self.checkVar = IntVar()

        Label(master, text=self.prompt).grid(row=0, sticky=W)

        self.e1 = Entry(master)

        self.e1.grid(row=0, column=1)

        self.cb = Checkbutton(master, text="Save to keychain", variable=self.checkVar)
        self.cb.pack()
        self.cb.grid(row=1, columnspan=2, sticky=W)
        self.configure(show='*')

    def apply(self):
        self.result = (self.e1.get(), self.checkVar.get() == 1)


if __name__ == '__main__':
    print get_password()

########NEW FILE########
__FILENAME__ = period
# Copyright 2012 David Fendrich

# This file is part of Selfspy

# Selfspy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Selfspy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Selfspy.  If not, see <http://www.gnu.org/licenses/>.

import bisect


class Period:
    def __init__(self, cutoff, maxtime):
        self.times = []
        self.cutoff = cutoff
        self.maxtime = maxtime

    def append(self, time):
        ltimes = len(self.times)
        end = min(time + self.cutoff, self.maxtime)
        
        def check_in(i):
            if self.times[i][0] <= time <= self.times[i][1]:
                self.times[i] = (self.times[i][0], max(end, self.times[i][1]))
                return True
            return False

        def maybe_merge(i):
            if ltimes > i + 1:
                if self.times[i][1] >= self.times[i + 1][0]:
                    self.times[i] = (self.times[i][0], self.times[i + 1][1])
                    self.times.pop(i + 1)

        if ltimes == 0:
            self.times.append((time, end))
            return

        i = bisect.bisect(self.times, (time,))
        if i >= 1 and check_in(i - 1):
            maybe_merge(i - 1)
        elif i < ltimes and check_in(i):
            maybe_merge(i)
        else:
            self.times.insert(i, (time, end))
            maybe_merge(i)
            
    def extend(self, times):
        for time in times:
            self.append(time)

    def calc_total(self):
        return sum(t2 - t1 for t1, t2 in self.times)

########NEW FILE########
__FILENAME__ = sniff_cocoa
# Copyright 2012 Bjarte Johansen

# This file is part of Selfspy

# Selfspy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Selfspy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Selfspy.  If not, see <http://www.gnu.org/licenses/>.

from Foundation import NSObject
from AppKit import NSApplication, NSApp, NSWorkspace
from Cocoa import (NSEvent,
                   NSKeyDown, NSKeyDownMask, NSKeyUp, NSKeyUpMask,
                   NSLeftMouseUp, NSLeftMouseDown, NSLeftMouseUpMask, NSLeftMouseDownMask,
                   NSRightMouseUp, NSRightMouseDown, NSRightMouseUpMask, NSRightMouseDownMask,
                   NSMouseMoved, NSMouseMovedMask,
                   NSScrollWheel, NSScrollWheelMask,
                   NSFlagsChanged, NSFlagsChangedMask,
                   NSAlternateKeyMask, NSCommandKeyMask, NSControlKeyMask,
                   NSShiftKeyMask, NSAlphaShiftKeyMask,
                   NSApplicationActivationPolicyProhibited)
from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
from PyObjCTools import AppHelper
import config as cfg

class Sniffer:
    def __init__(self):
        self.key_hook = lambda x: True
        self.mouse_button_hook = lambda x: True
        self.mouse_move_hook = lambda x: True
        self.screen_hook = lambda x: True

    def createAppDelegate(self):
        sc = self

        class AppDelegate(NSObject):

            def applicationDidFinishLaunching_(self, notification):
                mask = (NSKeyDownMask
                        | NSKeyUpMask
                        | NSLeftMouseDownMask
                        | NSLeftMouseUpMask
                        | NSRightMouseDownMask
                        | NSRightMouseUpMask
                        | NSMouseMovedMask
                        | NSScrollWheelMask
                        | NSFlagsChangedMask)
                NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(mask, sc.handler)

            def applicationWillTerminate_(self, application):
                # need to release the lock here as when the
                # application terminates it does not run the rest the
                # original main, only the code that has crossed the
                # pyobc bridge.
                if cfg.LOCK.is_locked():
                    cfg.LOCK.release()
                print "Exiting ..."

        return AppDelegate

    def run(self):
        NSApplication.sharedApplication()
        delegate = self.createAppDelegate().alloc().init()
        NSApp().setDelegate_(delegate)
        NSApp().setActivationPolicy_(NSApplicationActivationPolicyProhibited)
        self.workspace = NSWorkspace.sharedWorkspace()
        AppHelper.runEventLoop()

    def cancel(self):
        AppHelper.stopEventLoop()

    def handler(self, event):
        try:
            activeApps = self.workspace.runningApplications()
            #Have to look into this if it is too slow on move and scoll,
            #right now the check is done for everything.
            for app in activeApps:
                if app.isActive():
                    options = kCGWindowListOptionOnScreenOnly
                    windowList = CGWindowListCopyWindowInfo(options,
                                                            kCGNullWindowID)
                    for window in windowList:
                        if (window['kCGWindowNumber'] == event.windowNumber()
                            or (not event.windowNumber()
                                and window['kCGWindowOwnerName'] == app.localizedName())):
                            geometry = window['kCGWindowBounds']
                            self.screen_hook(window['kCGWindowOwnerName'],
                                             window.get('kCGWindowName', u''),
                                             geometry['X'],
                                             geometry['Y'],
                                             geometry['Width'],
                                             geometry['Height'])
                            break
                    break

            loc = NSEvent.mouseLocation()
            if event.type() == NSLeftMouseDown:
                self.mouse_button_hook(1, loc.x, loc.y)
#           elif event.type() == NSLeftMouseUp:
#               self.mouse_button_hook(1, loc.x, loc.y)
            elif event.type() == NSRightMouseDown:
                self.mouse_button_hook(3, loc.x, loc.y)
#           elif event.type() == NSRightMouseUp:
#               self.mouse_button_hook(2, loc.x, loc.y)
            elif event.type() == NSScrollWheel:
                if event.deltaY() > 0:
                    self.mouse_button_hook(4, loc.x, loc.y)
                elif event.deltaY() < 0:
                    self.mouse_button_hook(5, loc.x, loc.y)
                if event.deltaX() > 0:
                    self.mouse_button_hook(6, loc.x, loc.y)
                elif event.deltaX() < 0:
                    self.mouse_button_hook(7, loc.x, loc.y)
#               if event.deltaZ() > 0:
#                   self.mouse_button_hook(8, loc.x, loc.y)
#               elif event.deltaZ() < 0:
#                   self.mouse_button_hook(9, loc.x, loc.y)
            elif event.type() == NSKeyDown:
                flags = event.modifierFlags()
                modifiers = []  # OS X api doesn't care it if is left or right
                if flags & NSControlKeyMask:
                    modifiers.append('Ctrl')
                if flags & NSAlternateKeyMask:
                    modifiers.append('Alt')
                if flags & NSCommandKeyMask:
                    modifiers.append('Cmd')
                if flags & (NSShiftKeyMask | NSAlphaShiftKeyMask):
                    modifiers.append('Shift')
                character = event.charactersIgnoringModifiers()
                # these two get a special case because I am unsure of
                # their unicode value
                if event.keyCode() is 36:
                    character = "Enter"
                elif event.keyCode() is 51:
                    character = "Backspace"
                self.key_hook(event.keyCode(),
                              modifiers,
                              keycodes.get(character,
                                           character),
                              event.isARepeat())
            elif event.type() == NSMouseMoved:
                self.mouse_move_hook(loc.x, loc.y)
        except (SystemExit, KeyboardInterrupt):
            AppHelper.stopEventLoop()
            return
        except:
            AppHelper.stopEventLoop()
            raise

# Cocoa does not provide a good api to get the keycodes, therefore we
# have to provide our own.
keycodes = {
   u"\u0009": "Tab",
   u"\u001b": "Escape",
   u"\uf700": "Up",
   u"\uF701": "Down",
   u"\uF702": "Left",
   u"\uF703": "Right",
   u"\uF704": "F1",
   u"\uF705": "F2",
   u"\uF706": "F3",
   u"\uF707": "F4",
   u"\uF708": "F5",
   u"\uF709": "F6",
   u"\uF70A": "F7",
   u"\uF70B": "F8",
   u"\uF70C": "F9",
   u"\uF70D": "F10",
   u"\uF70E": "F11",
   u"\uF70F": "F12",
   u"\uF710": "F13",
   u"\uF711": "F14",
   u"\uF712": "F15",
   u"\uF713": "F16",
   u"\uF714": "F17",
   u"\uF715": "F18",
   u"\uF716": "F19",
   u"\uF717": "F20",
   u"\uF718": "F21",
   u"\uF719": "F22",
   u"\uF71A": "F23",
   u"\uF71B": "F24",
   u"\uF71C": "F25",
   u"\uF71D": "F26",
   u"\uF71E": "F27",
   u"\uF71F": "F28",
   u"\uF720": "F29",
   u"\uF721": "F30",
   u"\uF722": "F31",
   u"\uF723": "F32",
   u"\uF724": "F33",
   u"\uF725": "F34",
   u"\uF726": "F35",
   u"\uF727": "Insert",
   u"\uF728": "Delete",
   u"\uF729": "Home",
   u"\uF72A": "Begin",
   u"\uF72B": "End",
   u"\uF72C": "PageUp",
   u"\uF72D": "PageDown",
   u"\uF72E": "PrintScreen",
   u"\uF72F": "ScrollLock",
   u"\uF730": "Pause",
   u"\uF731": "SysReq",
   u"\uF732": "Break",
   u"\uF733": "Reset",
   u"\uF734": "Stop",
   u"\uF735": "Menu",
   u"\uF736": "User",
   u"\uF737": "System",
   u"\uF738": "Print",
   u"\uF739": "ClearLine",
   u"\uF73A": "ClearDisplay",
   u"\uF73B": "InsertLine",
   u"\uF73C": "DeleteLine",
   u"\uF73D": "InsertChar",
   u"\uF73E": "DeleteChar",
   u"\uF73F": "Prev",
   u"\uF740": "Next",
   u"\uF741": "Select",
   u"\uF742": "Execute",
   u"\uF743": "Undo",
   u"\uF744": "Redo",
   u"\uF745": "Find",
   u"\uF746": "Help",
   u"\uF747": "ModeSwitch"}

########NEW FILE########
__FILENAME__ = sniff_win
# -*- coding: utf-8 -*-
# Copyright 2012 Morten Linderud

# This file is part of Selfspy

# Selfspy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Selfspy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Selfspy.  If not, see <http://www.gnu.org/licenses/>.

import pyHook
import pythoncom
import sys
import threading
import ctypes


class SnifferThread(threading.Thread):
    def __init__(self, hook):
        threading.Thread.__init__(self)
        self.daemon = True
        self.encoding = sys.stdin.encoding
        self.key_hook = lambda x: True
        self.mouse_button_hook = lambda x: True
        self.mouse_move_hook = lambda x: True
        self.screen_hook = lambda x: True
        self.remap = {
                248: u"\xf8",
                216: u"\xd8",
                230: u"\xe6",
                198: u"\xc6",
                229: u"\xe5",
                197: u"\xc5"
                }
        self.hm = hook

    def run(self):
        self.hm.KeyDown = self.KeyboardEvent
        self.hm.MouseAllButtonsDown = self.MouseButtons
        self.hm.MouseMove = self.MouseMove
        self.hm.HookKeyboard()
        self.hm.HookMouse()
        pythoncom.PumpMessages()


    def MouseButtons(self, event):
        loc = event.Position
        if event.MessageName == "mouse right down":
            self.mouse_button_hook(3, loc[0], loc[1],)
        if event.MessageName == "mouse left down":
            self.mouse_button_hook(1, loc[0], loc[1])
        if event.MessageName == "mouse middle down":
            self.mouse_button_hook(2, loc[0], loc[1])
        try:
            string_event = event.WindowName.decode(self.encoding)
        except AttributeError:
            string_event = ""
        self.screen_hook(str(event.Window), string_event, loc[0], loc[1], 0, 0)
        return True

    def MouseMove(self, event):
        loc = event.Position
        if event.MessageName == "mouse move":
            self.mouse_move_hook(loc[0], loc[1])
        if event.MessageName == "mouse wheel":
            if event.Wheel == -1:
                self.mouse_button_hook(5, loc[0], loc[1],)
            elif event.Wheel == 1:
                self.mouse_button_hook(4, loc[0], loc[1],)
        return True

    def KeyboardEvent(self, event):
        modifiers = []
        if event.Key in ["Lshift", "Rshift"]:
            modifiers.append('Shift')
        elif event.Key in ["Lmenu", "Rmenu"]:
            modifiers.append('Alt')
        elif event.Key in ["Rcontrol", "Lcontrol"]:
            modifiers.append('Ctrl')
        elif event.Key in ["Rwin", "Lwin"]:
            modifiers.append('Super')
        if event.Ascii in self.remap.keys():
            string = self.remap[event.Ascii]
        else:
            string = unicode(chr(event.Ascii))
        self.key_hook(str(event.Ascii), modifiers, string, False)
        self.screen_hook(str(event.Window), event.WindowName.decode(self.encoding), 0, 0, 0, 0)
        return True


class Sniffer:
    """Winning!"""
    def __init__(self):
        self.encoding = sys.stdin.encoding
        self.key_hook = lambda x: True
        self.mouse_button_hook = lambda x: True
        self.mouse_move_hook = lambda x: True
        self.screen_hook = lambda x: True 
        self.remap = {
                248: u"\xf8",
                216: u"\xd8",
                230: u"\xe6",
                198: u"\xc6",
                229: u"\xe5",
                197: u"\xc5"
                }

    def run(self):
        try:
            self.hm = pyHook.HookManager()
            self.thread = SnifferThread(self.hm)
            # pythoncom.PumpMessages needs to be in the same thread as the events
            self.thread.mouse_button_hook = self.mouse_button_hook
            self.thread.mouse_move_hook = self.mouse_move_hook
            self.thread.screen_hook = self.screen_hook
            self.thread.key_hook = self.key_hook
            self.thread.start()
            while True:
                self.thread.join(100)
        except:
            self.cancel()

    def cancel(self):
        ctypes.windll.user32.PostQuitMessage(0)
        self.hm.UnhookKeyboard()
        self.hm.UnhookMouse()
        del self.thread
        del self.hm

########NEW FILE########
__FILENAME__ = sniff_x
# Copyright 2012 David Fendrich

# This file is part of Selfspy

# Selfspy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Selfspy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Selfspy.  If not, see <http://www.gnu.org/licenses/>.


# This file is loosely based on examples/record_demo.py in python-xlib

import sys

from Xlib import X, XK, display
from Xlib.ext import record
from Xlib.error import XError
from Xlib.protocol import rq


def state_to_idx(state):  # this could be a dict, but I might want to extend it.
    if state == 1:
        return 1
    if state == 128:
        return 4
    if state == 129:
        return 5
    return 0


class Sniffer:
    def __init__(self):
        self.keysymdict = {}
        for name in dir(XK):
            if name.startswith("XK_"):
                self.keysymdict[getattr(XK, name)] = name[3:]

        self.key_hook = lambda x: True
        self.mouse_button_hook = lambda x: True
        self.mouse_move_hook = lambda x: True
        self.screen_hook = lambda x: True

        self.contextEventMask = [X.KeyPress, X.MotionNotify]

        self.the_display = display.Display()
        self.record_display = display.Display()
        self.keymap = self.the_display._keymap_codes

    def run(self):
        # Check if the extension is present
        if not self.record_display.has_extension("RECORD"):
            print "RECORD extension not found"
            sys.exit(1)
        else:
            print "RECORD extension present"

        # Create a recording context; we only want key and mouse events
        self.ctx = self.record_display.record_create_context(
                0,
                [record.AllClients],
                [{
                        'core_requests': (0, 0),
                        'core_replies': (0, 0),
                        'ext_requests': (0, 0, 0, 0),
                        'ext_replies': (0, 0, 0, 0),
                        'delivered_events': (0, 0),
                        'device_events': tuple(self.contextEventMask),
                        'errors': (0, 0),
                        'client_started': False,
                        'client_died': False,
                }])

        # Enable the context; this only returns after a call to record_disable_context,
        # while calling the callback function in the meantime
        self.record_display.record_enable_context(self.ctx, self.processevents)
        # Finally free the context
        self.record_display.record_free_context(self.ctx)

    def cancel(self):
        self.the_display.record_disable_context(self.ctx)
        self.the_display.flush()

    def processevents(self, reply):
        if reply.category != record.FromServer:
            return
        if reply.client_swapped:
            print "* received swapped protocol data, cowardly ignored"
            return
        if not len(reply.data) or ord(reply.data[0]) < 2:
            # not an event
            return

        cur_class, cur_window, cur_name = self.get_cur_window()
        if cur_class:
            cur_geo = self.get_geometry(cur_window)
            if cur_geo:
                self.screen_hook(cur_class,
                                 cur_name,
                                 cur_geo.x,
                                 cur_geo.y,
                                 cur_geo.width,
                                 cur_geo.height)

        data = reply.data
        while len(data):
            ef = rq.EventField(None)
            event, data = ef.parse_binary_value(data, self.record_display.display, None, None)
            if event.type in [X.KeyPress]:
                # X.KeyRelease, we don't log this anyway
                self.key_hook(*self.key_event(event))
            elif event.type in [X.ButtonPress]:
                # X.ButtonRelease we don't log this anyway.
                self.mouse_button_hook(*self.button_event(event))
            elif event.type == X.MotionNotify:
                self.mouse_move_hook(event.root_x, event.root_y)
            elif event.type == X.MappingNotify:
                self.the_display.refresh_keyboard_mapping()
                newkeymap = self.the_display._keymap_codes
                print 'Change keymap!', newkeymap == self.keymap
                self.keymap = newkeymap

    def get_key_name(self, keycode, state):
        state_idx = state_to_idx(state)
        cn = self.keymap[keycode][state_idx]
        if cn < 256:
            return chr(cn).decode('latin1')
        else:
            return self.lookup_keysym(cn)

    def key_event(self, event):
        flags = event.state
        modifiers = []
        if flags & X.ControlMask:
            modifiers.append('Ctrl')
        if flags & X.Mod1Mask:  # Mod1 is the alt key
            modifiers.append('Alt')
        if flags & X.Mod4Mask:  # Mod4 should be super/windows key
            modifiers.append('Super')
        if flags & X.ShiftMask:
            modifiers.append('Shift')
        return (event.detail,
                modifiers,
                self.get_key_name(event.detail, event.state),
                event.sequence_number == 1)

    def button_event(self, event):
        return event.detail, event.root_x, event.root_y

    def lookup_keysym(self, keysym):
        if keysym in self.keysymdict:
            return self.keysymdict[keysym]
        return "[%d]" % keysym

    def get_cur_window(self):
        i = 0
        cur_class = None
        cur_window = None
        cur_name = None
        while i < 10:
            try:
                cur_window = self.the_display.get_input_focus().focus
                cur_class = None
                cur_name = None
                while cur_class is None:
                    if type(cur_window) is int:
                        return None, None, None

                    cur_name = cur_window.get_wm_name()
                    cur_class = cur_window.get_wm_class()

                    if cur_class:
                        cur_class = cur_class[1]
                    if not cur_class:
                        cur_window = cur_window.query_tree().parent
            except XError:
                i += 1
                continue
            break
        cur_class = cur_class or ''
        cur_name = cur_name or ''
        return cur_class.decode('latin1'), cur_window, cur_name.decode('latin1')

    def get_geometry(self, cur_window):
        i = 0
        geo = None
        while i < 10:
            try:
                geo = cur_window.get_geometry()
                break
            except XError:
                i += 1
        return geo

########NEW FILE########
__FILENAME__ = stats
#!/usr/bin/env python

# Copyright 2012 David Fendrich

# This file is part of Selfspy

# Selfspy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Selfspy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Selfspy.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import re
import datetime
import time

import argparse
import ConfigParser

from collections import Counter

from Crypto.Cipher import Blowfish
import hashlib

import config as cfg

from selfspy import check_password
from selfspy.password_dialog import get_password
from selfspy.period import Period

from selfspy import models

import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)

ACTIVE_SECONDS = 180
PERIOD_LOOKUP = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days', 'w': 'weeks'}
ACTIVITY_ACTIONS = {'active', 'periods', 'pactive', 'tactive', 'ratios'}
SUMMARY_ACTIONS = ACTIVITY_ACTIONS.union({'pkeys', 'tkeys', 'key_freqs', 'clicks', 'ratios'})

PROCESS_ACTIONS = {'pkeys', 'pactive'}
WINDOW_ACTIONS = {'tkeys', 'tactive'}

BUTTON_MAP = [('button1', 'left'),
              ('button2', 'middle'),
              ('button3', 'right'),
              ('button4', 'up'),
              ('button5', 'down')]


def pretty_seconds(secs):
    secs = int(secs)
    active = False
    outs = ''
    days = secs / (3600 * 24)
    if days:
        active = True
        outs += '%d days, ' % days
    secs -= days * (3600 * 24)

    hours = secs / 3600
    if hours:
        active = True
    if active:
        outs += '%dh ' % hours
    secs -= hours * 3600

    minutes = secs / 60
    if minutes:
        active = True
    if active:
        outs += '%dm ' % minutes
    secs -= minutes * 60

    outs += '%ds' % secs

    return outs


def make_time_string(dates, clock):
    now = datetime.datetime.now()
    now2 = datetime.datetime.now()

    if dates is None:
        dates = []

    if len(dates) > 3:
        print 'Max three arguments to date', dates
        sys.exit(1)

    try:
        dates = [int(d) for d in dates]
        if len(dates) == 3:
            now = now.replace(year=dates[0])
        if len(dates) >= 2:
            now = now.replace(month=dates[-2])
        if len(dates) >= 1:
            now = now.replace(day=dates[-1])

        if len(dates) == 2:
            if now > now2:
                now = now.replace(year=now.year - 1)

        if len(dates) == 1:
            if now > now2:
                m = now.month - 1
                if m:
                    now = now.replace(month=m)
                else:
                    now = now.replace(year=now.year - 1, month=12)
    except ValueError:
        print 'Malformed date', dates
        sys.exit(1)

    if clock:
        try:
            hour, minute = [int(v) for v in clock.split(':')]
        except ValueError:
            print 'Malformed clock', clock
            sys.exit(1)

        now = now.replace(hour=hour, minute=minute, second=0)

        if now > now2:
            now -= datetime.timedelta(days=1)

    return now.strftime('%Y-%m-%d %H:%M'), now


def make_period(q, period, who, start, prop):
    if len(period) < 1 or len(period) > 2:
        print '%s needs one or two arguments, not %d.' % (who, len(period)), period
        sys.exit(1)

    d = {}
    val = int(period[0])
    if len(period) == 1:
        d['hours'] = val
    else:
        if period[1] not in PERIOD_LOOKUP:
            print '--limit unit "%s" not one of %s' % (period[1], PERIOD_LOOKUP.keys())
            sys.exit(1)
        d[PERIOD_LOOKUP[period[1]]] = val

    if start:
        return q.filter(prop <= start + datetime.timedelta(**d))
    else:
        start = datetime.datetime.now() - datetime.timedelta(**d)
        return q.filter(prop >= start), start


def create_times(row):
    current_time = time.mktime(row.created_at.timetuple())
    abs_times = [current_time]
    for t in row.load_timings():
        current_time -= t
        abs_times.append(current_time)
    abs_times.reverse()
    return abs_times


class Selfstats:
    def __init__(self, db_name, args):
        self.args = args
        self.session_maker = models.initialize(db_name)
        self.inmouse = False

        self.check_needs()

    def do(self):
        if self.need_summary:
            self.calc_summary()
            self.show_summary()
        else:
            self.show_rows()

    def check_needs(self):
        self.need_text = False
        self.need_activity = False
        self.need_timings = False
        self.need_keys = False
        self.need_humanreadable = False
        self.need_summary = False
        self.need_process = any(self.args[k] for k in PROCESS_ACTIONS)
        self.need_window = any(self.args[k] for k in WINDOW_ACTIONS)

        if self.args['body'] is not None:
            self.need_text = True
        if self.args['showtext']:
            self.need_text = True
        cutoff = [self.args[k] for k in ACTIVITY_ACTIONS if self.args[k]]
        if cutoff:
            if any(c != cutoff[0] for c in cutoff):
                print 'You must give the same time argument to the different parameters in the --active family, when you use several in the same query.'
                sys.exit(1)
            self.need_activity = cutoff[0]
            self.need_timings = True
        if self.args['key_freqs']:
            self.need_keys = True
        if self.args['human_readable']:
            self.need_humanreadable = True

        if any(self.args[k] for k in SUMMARY_ACTIONS):
            self.need_summary = True

    def maybe_reg_filter(self, q, name, names, table, source_prop, target_prop):
        if self.args[name] is not None:
            ids = []
            try:
                reg = re.compile(self.args[name], re.I)
            except re.error, e:
                print 'Error in regular expression', str(e)
                sys.exit(1)

            for x in self.session.query(table).all():
                if reg.search(x.__getattribute__(source_prop)):
                    ids.append(x.id)
            if not self.inmouse:
                print '%d %s matched' % (len(ids), names)
            if ids:
                q = q.filter(target_prop.in_(ids))
            else:
                return q, False
        return q, True

    def filter_prop(self, prop, startprop):
        self.session = self.session_maker()

        q = self.session.query(prop).order_by(prop.id)

        if self.args['date'] or self.args['clock']:
            s, start = make_time_string(self.args['date'], self.args['clock'])
            q = q.filter(prop.created_at >= s)
            if self.args['limit'] is not None:
                q = make_period(q, self.args['limit'], '--limit', start, startprop)
        elif self.args['id'] is not None:
            q = q.filter(prop.id >= self.args['id'])
            if self.args['limit'] is not None:
                q = q.filter(prop.id < self.args['id'] + int(self.args['limit'][0]))
        elif self.args['back'] is not None:
            q, start = make_period(q, self.args['back'], '--back', None, startprop)
            if self.args['limit'] is not None:
                q = make_period(q, self.args['limit'], '--limit', start, startprop)

        q, found = self.maybe_reg_filter(q, 'process', 'process(es)', models.Process, 'name', prop.process_id)
        if not found:
            return None

        q, found = self.maybe_reg_filter(q, 'title', 'title(s)', models.Window, 'title', prop.window_id)
        if not found:
            return None

        return q

    def filter_keys(self):
        q = self.filter_prop(models.Keys, models.Keys.started)
        if q is None:
            return

        if self.args['min_keys'] is not None:
            q = q.filter(Keys.nrkeys >= self.args['min_keys'])

        if self.args['body']:
            try:
                bodrex = re.compile(self.args['body'], re.I)
            except re.error, e:
                print 'Error in regular expression', str(e)
                sys.exit(1)
            for x in q.all():
                if(self.need_humanreadable):
                    body = x.decrypt_humanreadable()
                else:
                    body = x.decrypt_text()
                if bodrex.search(body):
                    yield x
        else:
            for x in q:
                yield x

    def filter_clicks(self):
        self.inmouse = True
        q = self.filter_prop(models.Click, models.Click.created_at)
        if q is None:
            return

        for x in q:
            yield x

    def show_rows(self):
        fkeys = self.filter_keys()
        rows = 0
        print '<RowID> <Starting date and time> <Duration> <Process> <Window title> <Number of keys pressed>',
        if self.args['showtext'] and self.need_humanreadable:
            print '<Decrypted Human Readable text>'
        elif self.args['showtext']:
            print '<Decrypted text>'
        else:
            print

        for row in fkeys:
            rows += 1
            print row.id, row.started, pretty_seconds((row.created_at - row.started).total_seconds()), row.process.name, '"%s"' % row.window.title, row.nrkeys,
            if self.args['showtext']:
                if self.need_humanreadable:
                    print row.decrypt_humanreadable().decode('utf8')
                else:
                    print row.decrypt_text().decode('utf8')
            else:
                print
        print rows, 'rows'

    def calc_summary(self):
        def updict(d1, d2, activity_times, sub=None):
            if sub is not None:
                if sub not in d1:
                    d1[sub] = {}
                d1 = d1[sub]

            for key, val in d2.items():
                if key not in d1:
                    d1[key] = 0
                d1[key] += val

            if self.need_activity:
                if 'activity' not in d1:
                    d1['activity'] = Period(self.need_activity, time.time())
                d1['activity'].extend(activity_times)

        sumd = {}
        processes = {}
        windows = {}
        timings = []
        keys = Counter()
        for row in self.filter_keys():
            d = {'nr': 1,
                 'keystrokes': len(row.load_timings())}

            if self.need_activity:
                timings = create_times(row)
            if self.need_process:
                updict(processes, d, timings, sub=row.process.name)
            if self.need_window:
                updict(windows, d, timings, sub=row.window.title)
            updict(sumd, d, timings)

            if self.args['key_freqs']:
                keys.update(row.decrypt_keys())

        for click in self.filter_clicks():
            d = {'noscroll_clicks': click.button not in [4, 5],
                 'clicks': 1,
                 'button%d' % click.button: 1,
                 'mousings': click.nrmoves}
            if self.need_activity:
                timings = [time.mktime(click.created_at.timetuple())]
            if self.need_process:
                updict(processes, d, timings, sub=click.process.name)
            if self.need_window:
                updict(windows, d, timings, sub=click.window.title)
            updict(sumd, d, timings)

        self.processes = processes
        self.windows = windows
        self.summary = sumd
        if self.args['key_freqs']:
            self.summary['key_freqs'] = keys

    def show_summary(self):
        print '%d keystrokes in %d key sequences,' % (self.summary.get('keystrokes', 0), self.summary.get('nr', 0)),
        print '%d clicks (%d excluding scroll),' % (self.summary.get('clicks', 0), self.summary.get('noscroll_clicks', 0)),
        print '%d mouse movements' % (self.summary.get('mousings', 0))
        print

        if self.need_activity:
            act = self.summary.get('activity')

            if act:
                act = act.calc_total()
            else:
                act = 0
            print 'Total time active:',
            print pretty_seconds(act)
            print

        if self.args['clicks']:
            print 'Mouse clicks:'
            for key, name in BUTTON_MAP:
                print self.summary.get(key, 0), name
            print

        if self.args['key_freqs']:
            print 'Key frequencies:'
            for key, val in self.summary['key_freqs'].most_common():
                print key, val
            print

        if self.args['pkeys']:
            print 'Processes sorted by keystrokes:'
            pdata = self.processes.items()
            pdata.sort(key=lambda x: x[1].get('keystrokes', 0), reverse=True)
            for name, data in pdata:
                print name, data.get('keystrokes', 0)
            print

        if self.args['tkeys']:
            print 'Window titles sorted by keystrokes:'
            wdata = self.windows.items()
            wdata.sort(key=lambda x: x[1].get('keystrokes', 0), reverse=True)
            for name, data in wdata:
                print name, data.get('keystrokes', 0)
            print

        if self.args['pactive']:
            print 'Processes sorted by activity:'
            for p in self.processes.values():
                p['active_time'] = int(p['activity'].calc_total())
            pdata = self.processes.items()
            pdata.sort(key=lambda x: x[1]['active_time'], reverse=True)
            for name, data in pdata:
                print '%s, %s' % (name, pretty_seconds(data['active_time']))
            print

        if self.args['tactive']:
            print 'Window titles sorted by activity:'
            for w in self.windows.values():
                w['active_time'] = int(w['activity'].calc_total())
            wdata = self.windows.items()
            wdata.sort(key=lambda x: x[1]['active_time'], reverse=True)
            for name, data in wdata:
                print '%s, %s' % (name, pretty_seconds(data['active_time']))
            print

        if self.args['periods']:
            if 'activity' in self.summary:
                print 'Active periods:'
                for t1, t2 in self.summary['activity'].times:
                    d1 = datetime.datetime.fromtimestamp(t1).replace(microsecond=0)
                    d2 = datetime.datetime.fromtimestamp(t2).replace(microsecond=0)
                    print '%s - %s' % (d1.isoformat(' '), str(d2.time()).split('.')[0])
            else:
                print 'No active periods.'
            print

        if self.args['ratios']:
            def tryget(prop):
                return float(max(1, self.summary.get(prop, 1)))

            mousings = tryget('mousings')
            clicks = tryget('clicks')
            keys = tryget('keystrokes')
            print 'Keys / Clicks: %.1f' % (keys / clicks)
            print 'Active seconds / Keys: %.1f' % (act / keys)
            print
            print 'Mouse movements / Keys: %.1f' % (mousings / keys)
            print 'Mouse movements / Clicks: %.1f' % (mousings / clicks)
            print


def parse_config():
    conf_parser = argparse.ArgumentParser(description=__doc__, add_help=False,
                                          formatter_class=argparse.RawDescriptionHelpFormatter)

    conf_parser.add_argument("-c", "--config",
                             help="""Config file with defaults. Command line parameters will override those given in the config file. Options to selfspy goes in the "[Defaults]" section, followed by [argument]=[value] on each line. Options specific to selfstats should be in the "[Selfstats]" section, though "password" and "data-dir" are still read from "[Defaults]".""", metavar="FILE")
    args, remaining_argv = conf_parser.parse_known_args()

    defaults = {}
    if args.config:
        config = ConfigParser.SafeConfigParser()
        config.read([args.config])
        defaults = dict(config.items('Defaults') + config.items("Selfstats"))

    parser = argparse.ArgumentParser(description="""Calculate statistics on selfspy data. Per default it will show non-text information that matches the filter. Adding '-s' means also show text. Adding any of the summary options will show those summaries over the given filter instead of the listing. Multiple summary options can be given to print several summaries over the same filter. If you give arguments that need to access text / keystrokes, you will be asked for the decryption password.""", epilog="""See the README file or http://gurgeh.github.com/selfspy for examples.""", parents=[conf_parser])
    parser.set_defaults(**defaults)
    parser.add_argument('-p', '--password', help='Decryption password. Only needed if selfstats needs to access text / keystrokes data. If your database in not encrypted, specify -p="" here. If you don\'t specify a password in the command line arguments or in a config file, and the statistics you ask for require a password, a dialog will pop up asking for the password. If you give your password on the command line, remember that it will most likely be stored in plain text in your shell history.')
    parser.add_argument('-d', '--data-dir', help='Data directory for selfspy, where the database is stored. Remember that Selfspy must have read/write access. Default is %s' % cfg.DATA_DIR, default=cfg.DATA_DIR)

    parser.add_argument('-s', '--showtext', action='store_true', help='Also show the text column. This switch is ignored if at least one of the summary options are used. Requires password.')

    parser.add_argument('-D', '--date', nargs='+', help='Which date to start the listing or summarizing from. If only one argument is given (--date 13) it is interpreted as the closest date in the past on that day. If two arguments are given (--date 03 13) it is interpreted as the closest date in the past on that month and that day, in that order. If three arguments are given (--date 2012 03 13) it is interpreted as YYYY MM DD')
    parser.add_argument('-C', '--clock', type=str, help='Time to start the listing or summarizing from. Given in 24 hour format as --clock 13:25. If no --date is given, interpret the time as today if that results in sometimes in the past, otherwise as yesterday.')

    parser.add_argument('-i', '--id', type=int, help='Which row ID to start the listing or summarizing from. If --date and/or --clock is given, this option is ignored.')

    parser.add_argument('-b', '--back', nargs='+', type=str, help='--back <period> [<unit>] Start the listing or summary this much back in time. Use this as an alternative to --date, --clock and --id. If any of those are given, this option is ignored. <unit> is either "s" (seconds), "m" (minutes), "h" (hours), "d" (days) or "w" (weeks). If no unit is given, it is assumed to be hours.')

    parser.add_argument('-l', '--limit', help='--limit <period> [<unit>]. If the start is given in --date/--clock, the limit is a time period given by <unit>. <unit> is either "s" (seconds), "m" (minutes), "h" (hours), "d" (days) or "w" (weeks). If no unit is given, it is assumed to be hours. If the start is given with --id, limit has no unit and means that the maximum row ID is --id + --limit.', nargs='+', type=str)

    parser.add_argument('-m', '--min-keys', type=int, metavar='nr', help='Only allow entries with at least <nr> keystrokes')

    parser.add_argument('-T', '--title', type=str, metavar='regexp', help='Only allow entries where a search for this <regexp> in the window title matches something. All regular expressions are case insensitive.')
    parser.add_argument('-P', '--process', type=str, metavar='regexp', help='Only allow entries where a search for this <regexp> in the process matches something.')
    parser.add_argument('-B', '--body', type=str, metavar='regexp', help='Only allow entries where a search for this <regexp> in the body matches something. Do not use this filter when summarizing ratios or activity, as it has no effect on mouse clicks. Requires password.')

    parser.add_argument('--clicks', action='store_true', help='Summarize number of mouse button clicks for all buttons.')

    parser.add_argument('--key-freqs', action='store_true', help='Summarize a table of absolute and relative number of keystrokes for each used key during the time period. Requires password.')

    parser.add_argument('--human-readable', action='store_true', help='This modifies the --body entry and honors backspace.')
    parser.add_argument('--active', type=int, metavar='seconds', nargs='?', const=ACTIVE_SECONDS, help='Summarize total time spent active during the period. The optional argument gives how many seconds after each mouse click (including scroll up or down) or keystroke that you are considered active. Default is %d.' % ACTIVE_SECONDS)

    parser.add_argument('--ratios', type=int, metavar='seconds', nargs='?', const=ACTIVE_SECONDS, help='Summarize the ratio between different metrics in the given period. "Clicks" will not include up or down scrolling. The optional argument is the "seconds" cutoff for calculating active use, like --active.')

    parser.add_argument('--periods', type=int, metavar='seconds', nargs='?', const=ACTIVE_SECONDS, help='List active time periods. Optional argument works same as for --active.')

    parser.add_argument('--pactive', type=int, metavar='seconds', nargs='?', const=ACTIVE_SECONDS, help='List processes, sorted by time spent active in them. Optional argument works same as for --active.')
    parser.add_argument('--tactive', type=int, metavar='seconds', nargs='?', const=ACTIVE_SECONDS, help='List window titles, sorted by time spent active in them. Optional argument works same as for --active.')

    parser.add_argument('--pkeys', action='store_true', help='List processes sorted by number of keystrokes.')
    parser.add_argument('--tkeys', action='store_true', help='List window titles sorted by number of keystrokes.')

    return parser.parse_args()


def make_encrypter(password):
    if password == "":
        encrypter = None
    else:
        encrypter = Blowfish.new(hashlib.md5(password).digest())
    return encrypter


def main():
    args = vars(parse_config())

    args['data_dir'] = os.path.expanduser(args['data_dir'])

    def check_with_encrypter(password):
        encrypter = make_encrypter(password)
        return check_password.check(args['data_dir'], encrypter, read_only=True)

    ss = Selfstats(os.path.join(args['data_dir'], cfg.DBNAME), args)

    if args['limit']:
        try:
            int(args['limit'][0])
        except ValueError:
            print 'First argument to --limit must be an integer'
            sys.exit(1)

    if ss.need_text or ss.need_keys:
        if args['password'] is None:
            args['password'] = get_password(verify=check_with_encrypter)

        models.ENCRYPTER = make_encrypter(args['password'])

        if not check_password.check(args['data_dir'], models.ENCRYPTER, read_only=True):
            print 'Password failed'
            sys.exit(1)

    ss.do()


if __name__ == '__main__':
    main()

########NEW FILE########
