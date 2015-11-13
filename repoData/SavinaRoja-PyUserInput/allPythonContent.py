__FILENAME__ = clickonacci
from pymouse import PyMouseEvent

def fibo():
    a = 0
    yield a
    b = 1
    yield b
    while True:
        a, b = b, a+b
        yield b

class Clickonacci(PyMouseEvent):
    def __init__(self):
        PyMouseEvent.__init__(self)
        self.fibo = fibo()

    def click(self, x, y, button, press):
        '''Print Fibonacci numbers when the left click is pressed.'''
        if button == 1:
            if press:
                print(self.fibo.next())
        else:  # Exit if any other mouse button used
            self.stop()

C = Clickonacci()
C.run()
########NEW FILE########
__FILENAME__ = filetranscriber
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FileTranscriber

A small utility that simulates user typing to aid plaintext file transcription
in limited environments

Usage:
  transcribe <file> [--interval=<time>] [--pause=<time>]
  transcribe (--help | --version)

Options:
  -v --version          show program's version number and exit
  -h --help             show this help message and exit
  -i --interval=<time>  Interval between keystrokes (in seconds). Typing too
                        quickly may break applications processing the
                        keystrokes. [default: 0.1]
  -p --pause=<time>     How long the script should wait before starting (in
                        seconds). Increase this if you need more time to enter
                        the typing field. [default: 5]
"""

#This script copied from https://github.com/SavinaRoja/FileTranscriber
#Check there for updates

from docopt import docopt
from pykeyboard import PyKeyboard
from pymouse import PyMouseEvent
import time
import sys


#Hack to make input work for both Python 2 and Python 3
try:
    input = raw_input
except NameError:
    pass


class AbortMouse(PyMouseEvent):
    def click(self, x, y, button, press):
        if press:
            self.stop()


def main():
    #Get an instance of PyKeyboard, and our custom PyMouseEvent
    keyboard = PyKeyboard()
    mouse = AbortMouse()

    input('Press Enter when ready.')
    print('Typing will begin in {0} seconds...'.format(opts['--pause']))
    time.sleep(opts['--pause'])

    mouse.start()
    with open(opts['<file>'], 'r') as readfile:
        for line in readfile:
            if not mouse.state:
                print('Typing aborted!')
                break
            keyboard.type_string(line, opts['--interval'])

if __name__ == '__main__':
    opts = docopt(__doc__, version='0.2.1')
    try:
        opts['--interval'] = float(opts['--interval'])
    except ValueError:
        print('The value of --interval must be a number')
        sys.exit(1)
    try:
        opts['--pause'] = float(opts['--pause'])
    except ValueError:
        print('The value of --pause must be a number')
        sys.exit(1)
    main()
########NEW FILE########
__FILENAME__ = mouse
#!/usr/bin/python

import logging
import daemon
from socket import gethostname;
from pymouse import PyMouse
import random, time
from signal import signal, SIGINT

with daemon.DaemonContext():

    def stop(signum, frame):
	cleanup_stop_thread();
	sys.exit()
    signal(SIGINT, stop)

    try:
	from pymouse import PyMouseEvent

	class event(PyMouseEvent):
	    def __init__(self):
		super(event, self).__init__()
		FORMAT = '%(asctime)-15s ' + gethostname() + ' touchlogger %(levelname)s %(message)s'
		logging.basicConfig(filename='/var/log/mouse.log', level=logging.DEBUG, format=FORMAT)

	    def move(self, x, y):
		pass

	    def click(self, x, y, button, press):
		if press:
		    logging.info('{ "event": "click", "type": "press", "x": "' + str(x) + '", "y": "' + str(y) + '"}') 
		else:
		    logging.info('{ "event": "click", "type": "release", "x": "' + str(x) + '", "y": "' + str(y) + '"}') 

	e = event()
	e.capture = False
	e.daemon = False
	e.start()

    except ImportError:
	logging.info('{ "event": "exception", "type": "ImportError", "value": "Mouse events unsupported"}') 
	sys.exit()

    m = PyMouse()
    try:
	    size = m.screen_size()
	    logging.info('{ "event": "start", "type": "size", "value": "' + str(size) + '"}') 
    except:
	    logging.info('{ "event": "exception", "type": "size", "value": "undetermined problem"}') 
	    sys.exit()

    try:
	    e.join()
    except KeyboardInterrupt:
	    e.stop()
	    sys.exit()


########NEW FILE########
__FILENAME__ = base
#Copyright 2013 Paul Barton
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
As the base file, this provides a rough operational model along with the
framework to be extended by each platform.
"""

import time
from threading import Thread


class PyKeyboardMeta(object):
    """
    The base class for PyKeyboard. Represents basic operational model.
    """

    def press_key(self, character=''):
        """Press a given character key."""
        raise NotImplementedError

    def release_key(self, character=''):
        """Release a given character key."""
        raise NotImplementedError

    def tap_key(self, character='', n=1, interval=0):
        """Press and release a given character key n times."""
        for i in range(n):
            self.press_key(character)
            self.release_key(character)
            time.sleep(interval)

    def type_string(self, char_string, interval=0):
        """
        A convenience method for typing longer strings of characters. Generates
        as few Shift events as possible."""
        shift = False
        for char in char_string:
            if self.is_char_shifted(char):
                if not shift:  # Only press Shift as needed
                    time.sleep(interval)
                    self.press_key(self.shift_key)
                    shift = True
                #In order to avoid tap_key pressing Shift, we need to pass the
                #unshifted form of the character
                if char in '<>?:"{}|~!@#$%^&*()_+':
                    ch_index = '<>?:"{}|~!@#$%^&*()_+'.index(char)
                    unshifted_char = ",./;'[]\\`1234567890-="[ch_index]
                else:
                    unshifted_char = char.lower()
                time.sleep(interval)
                self.tap_key(unshifted_char)
            else:  # Unshifted already
                if shift and char != ' ':  # Only release Shift as needed
                    self.release_key(self.shift_key)
                    shift = False
                time.sleep(interval)
                self.tap_key(char)

        if shift:  # Turn off Shift if it's still ON
            self.release_key(self.shift_key)

    def special_key_assignment(self):
        """Makes special keys more accessible."""
        raise NotImplementedError

    def lookup_character_value(self, character):
        """
        If necessary, lookup a valid API value for the key press from the
        character.
        """
        raise NotImplementedError

    def is_char_shifted(self, character):
        """Returns True if the key character is uppercase or shifted."""
        if character.isupper():
            return True
        if character in '<>?:"{}|~!@#$%^&*()_+':
            return True
        return False


class PyKeyboardEventMeta(Thread):
    """
    The base class for PyKeyboard. Represents basic operational model.
    """

    #One of the most variable components of keyboards throughout history and
    #across manufacturers is the Modifier Key...
    #I am attempting to cover a lot of bases to make using PyKeyboardEvent
    #simpler, without digging a bunch of traps for incompatibilities between
    #platforms.

    #Keeping track of the keyboard's state is not only necessary at times to
    #correctly interpret character identities in keyboard events, but should
    #also enable a user to easily query modifier states without worrying about
    #chaining event triggers for mod-combinations

    #The keyboard's state will be represented by an integer, the individual
    #mod keys by a bit mask of that integer
    state = 0

    #Each platform should assign, where applicable/possible, the bit masks for
    #modifier keys initially set to 0 here. Not all modifiers are recommended
    #for cross-platform use
    modifier_bits = {'Shift': 1,
                     'Lock': 2,
                     'Control': 4,
                     'Mod1': 8,  # X11 dynamic assignment
                     'Mod2': 16,  # X11 dynamic assignment
                     'Mod3': 32,  # X11 dynamic assignment
                     'Mod4': 64,  # X11 dynamic assignment
                     'Mod5': 128,  # X11 dynamic assignment
                     'Alt': 0,
                     'AltGr': 0,  # Uncommon
                     'Caps_Lock': 0,
                     'Command': 0,  # Mac key without generic equivalent
                     'Function': 0,  # Not advised; typically undetectable
                     'Hyper': 0,  # Uncommon?
                     'Meta': 0,  # Uncommon?
                     'Num_Lock': 0,
                     'Mode_switch': 0,  # Uncommon
                     'Shift_Lock': 0,  # Uncommon
                     'Super': 0,  # X11 key, sometimes equivalent to Windows
                     'Windows': 0}  # Windows key, sometimes equivalent to Super

    #Make the modifiers dictionary for individual states, setting all to off
    modifiers = {}
    for key in modifier_bits.keys():
        modifiers[key] = False

    def __init__(self, capture=False):
        Thread.__init__(self)
        self.daemon = True
        self.capture = capture
        self.state = True
        self.configure_keys()

    def run(self):
        self.state = True

    def stop(self):
        self.state = False

    def handler(self):
        raise NotImplementedError

    def tap(self, keycode, character, press):
        """
        Subclass this method with your key event handler. It will receive
        the keycode associated with the key event, as well as string name for
        the key if one can be assigned (keyboard mask states will apply). The
        argument 'press' will be True if the key was depressed and False if the
        key was released.
        """
        pass

    def escape(self, event):
        """
        A function that defines when to stop listening; subclass this with your
        escape behavior. If the program is meant to stop, this method should
        return True. Every key event will go through this method before going to
        tap(), allowing this method to check for exit conditions.

        The default behavior is to stop when the 'Esc' key is pressed.

        If one wishes to use key combinations, or key series, one might be
        interested in reading about Finite State Machines.
        http://en.wikipedia.org/wiki/Deterministic_finite_automaton
        """
        condition = None
        return event == condition

    def configure_keys(self):
        """
        Does per-platform work of configuring the modifier keys as well as data
        structures for simplified key access. Does nothing in this base
        implementation.
        """
        pass
########NEW FILE########
__FILENAME__ = java_
#Copyright 2013 Paul Barton
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = mac
#Copyright 2013 Paul Barton
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import time
from Quartz import *
from AppKit import NSEvent
from .base import PyKeyboardMeta, PyKeyboardEventMeta

# Taken from events.h
# /System/Library/Frameworks/Carbon.framework/Versions/A/Frameworks/HIToolbox.framework/Versions/A/Headers/Events.h
character_translate_table = {
    'a': 0x00,
    's': 0x01,
    'd': 0x02,
    'f': 0x03,
    'h': 0x04,
    'g': 0x05,
    'z': 0x06,
    'x': 0x07,
    'c': 0x08,
    'v': 0x09,
    'b': 0x0b,
    'q': 0x0c,
    'w': 0x0d,
    'e': 0x0e,
    'r': 0x0f,
    'y': 0x10,
    't': 0x11,
    '1': 0x12,
    '2': 0x13,
    '3': 0x14,
    '4': 0x15,
    '6': 0x16,
    '5': 0x17,
    '=': 0x18,
    '9': 0x19,
    '7': 0x1a,
    '-': 0x1b,
    '8': 0x1c,
    '0': 0x1d,
    ']': 0x1e,
    'o': 0x1f,
    'u': 0x20,
    '[': 0x21,
    'i': 0x22,
    'p': 0x23,
    'l': 0x25,
    'j': 0x26,
    '\'': 0x27,
    'k': 0x28,
    ';': 0x29,
    '\\': 0x2a,
    ',': 0x2b,
    '/': 0x2c,
    'n': 0x2d,
    'm': 0x2e,
    '.': 0x2f,
    '`': 0x32,
    ' ': 0x31,
    '\r': 0x24,
    '\t': 0x30,
    '\n': 0x24,
    'return' : 0x24,
    'tab' : 0x30,
    'space' : 0x31,
    'delete' : 0x33,
    'escape' : 0x35,
    'command' : 0x37,
    'shift' : 0x38,
    'capslock' : 0x39,
    'option' : 0x3A,
    'control' : 0x3B,
    'rightshift' : 0x3C,
    'rightoption' : 0x3D,
    'rightcontrol' : 0x3E,
    'function' : 0x3F,
}

# Taken from ev_keymap.h
# http://www.opensource.apple.com/source/IOHIDFamily/IOHIDFamily-86.1/IOHIDSystem/IOKit/hidsystem/ev_keymap.h
special_key_translate_table = {
    'KEYTYPE_SOUND_UP': 0,
    'KEYTYPE_SOUND_DOWN': 1,
    'KEYTYPE_BRIGHTNESS_UP': 2,
    'KEYTYPE_BRIGHTNESS_DOWN': 3,
    'KEYTYPE_CAPS_LOCK': 4,
    'KEYTYPE_HELP': 5,
    'POWER_KEY': 6,
    'KEYTYPE_MUTE': 7,
    'UP_ARROW_KEY': 8,
    'DOWN_ARROW_KEY': 9,
    'KEYTYPE_NUM_LOCK': 10,
    'KEYTYPE_CONTRAST_UP': 11,
    'KEYTYPE_CONTRAST_DOWN': 12,
    'KEYTYPE_LAUNCH_PANEL': 13,
    'KEYTYPE_EJECT': 14,
    'KEYTYPE_VIDMIRROR': 15,
    'KEYTYPE_PLAY': 16,
    'KEYTYPE_NEXT': 17,
    'KEYTYPE_PREVIOUS': 18,
    'KEYTYPE_FAST': 19,
    'KEYTYPE_REWIND': 20,
    'KEYTYPE_ILLUMINATION_UP': 21,
    'KEYTYPE_ILLUMINATION_DOWN': 22,
    'KEYTYPE_ILLUMINATION_TOGGLE': 23
}

class PyKeyboard(PyKeyboardMeta):

    def __init__(self):
      self.shift_key = 'shift'
      
    def press_key(self, key):
        if key in special_key_translate_table:
            self._press_special_key(key, True)
        else:
            self._press_normal_key(key, True)

    def release_key(self, key):
        if key in special_key_translate_table:
            self._press_special_key(key, False)
        else:
            self._press_normal_key(key, False)

    def special_key_assignment(self):
        self.volume_mute_key = 'KEYTYPE_MUTE'
        self.volume_down_key = 'KEYTYPE_SOUND_DOWN'
        self.volume_up_key = 'KEYTYPE_SOUND_UP'
        self.media_play_pause_key = 'KEYTYPE_PLAY'

        # Doesn't work :(
        # self.media_next_track_key = 'KEYTYPE_NEXT'
        # self.media_prev_track_key = 'KEYTYPE_PREVIOUS'

    def _press_normal_key(self, key, down):
        try:
            key_code = character_translate_table[key.lower()]

            event = CGEventCreateKeyboardEvent(None, key_code, down)
            CGEventPost(kCGHIDEventTap, event)
            if key.lower() == "shift":
              time.sleep(.1)

        except KeyError:
            raise RuntimeError("Key {} not implemented.".format(key))

    def _press_special_key(self, key, down):
        """ Helper method for special keys. 

        Source: http://stackoverflow.com/questions/11045814/emulate-media-key-press-on-mac
        """
        key_code = special_key_translate_table[key]

        ev = NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
                NSSystemDefined, # type
                (0,0), # location
                0xa00 if down else 0xb00, # flags
                0, # timestamp
                0, # window
                0, # ctx
                8, # subtype
                (key_code << 16) | ((0xa if down else 0xb) << 8), # data1
                -1 # data2
            )

        CGEventPost(0, ev.CGEvent())

class PyKeyboardEvent(PyKeyboardEventMeta):
    def run(self):
        tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionDefault,
            CGEventMaskBit(kCGEventKeyDown) |
            CGEventMaskBit(kCGEventKeyUp),
            self.handler,
            None)

        loopsource = CFMachPortCreateRunLoopSource(None, tap, 0)
        loop = CFRunLoopGetCurrent()
        CFRunLoopAddSource(loop, loopsource, kCFRunLoopDefaultMode)
        CGEventTapEnable(tap, True)

        while self.state:
            CFRunLoopRunInMode(kCFRunLoopDefaultMode, 5, False)

    def handler(self, proxy, type, event, refcon):
        key = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
        if type == kCGEventKeyDown:
            self.key_press(key)
        elif type == kCGEventKeyUp:
            self.key_release(key)

        if self.capture:
            CGEventSetType(event, kCGEventNull)

        return event

########NEW FILE########
__FILENAME__ = mir
#Copyright 2013 Paul Barton
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = wayland
#Copyright 2013 Paul Barton
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = windows
#Copyright 2013 Paul Barton
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from ctypes import *
import win32api
from win32con import *
import pythoncom

from .base import PyKeyboardMeta, PyKeyboardEventMeta

import time


class SupportError(Exception):
    """For keys not supported on this system"""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return('The {0} key is not supported in Windows'.format(self.value))


class PyKeyboard(PyKeyboardMeta):
    """
    The PyKeyboard implementation for Windows systems. This allows one to
    simulate keyboard input.
    """
    def __init__(self):
        PyKeyboardMeta.__init__(self)
        self.special_key_assignment()

    def press_key(self, character=''):
        """
        Press a given character key.
        """
        try:
            shifted = self.is_char_shifted(character)
        except AttributeError:
            win32api.keybd_event(character, 0, 0, 0)
        else:
            if shifted:
                win32api.keybd_event(self.shift_key, 0, 0, 0)
            char_vk = win32api.VkKeyScan(character)
            win32api.keybd_event(char_vk, 0, 0, 0)

    def release_key(self, character=''):
        """
        Release a given character key.
        """
        try:
            shifted = self.is_char_shifted(character)
        except AttributeError:
            win32api.keybd_event(character, 0, KEYEVENTF_KEYUP, 0)
        else:
            if shifted:
                win32api.keybd_event(self.shift_key, 0, KEYEVENTF_KEYUP, 0)
            char_vk = win32api.VkKeyScan(character)
            win32api.keybd_event(char_vk, 0, KEYEVENTF_KEYUP, 0)

    def special_key_assignment(self):
        """
        Special Key assignment for windows
        """
        #As defined by Microsoft, refer to:
        #http://msdn.microsoft.com/en-us/library/windows/desktop/dd375731(v=vs.85).aspx
        self.backspace_key = VK_BACK
        self.tab_key = VK_TAB
        self.clear_key = VK_CLEAR
        self.return_key = VK_RETURN
        self.enter_key = self.return_key  # Because many keyboards call it "Enter"
        self.shift_key = VK_SHIFT
        self.shift_l_key = VK_LSHIFT
        self.shift_r_key = VK_RSHIFT
        self.control_key = VK_CONTROL
        self.control_l_key = VK_LCONTROL
        self.control_r_key = VK_RCONTROL
        #Windows uses "menu" to refer to Alt...
        self.menu_key = VK_MENU
        self.alt_l_key = VK_LMENU
        self.alt_r_key = VK_RMENU
        self.alt_key = self.alt_l_key
        self.pause_key = VK_PAUSE
        self.caps_lock_key = VK_CAPITAL
        self.capital_key = self.caps_lock_key
        self.num_lock_key = VK_NUMLOCK
        self.scroll_lock_key = VK_SCROLL
        #Windows Language Keys,
        self.kana_key = VK_KANA
        self.hangeul_key = VK_HANGEUL # old name - should be here for compatibility
        self.hangul_key = VK_HANGUL
        self.junjua_key = VK_JUNJA
        self.final_key = VK_FINAL
        self.hanja_key = VK_HANJA
        self.kanji_key = VK_KANJI
        self.convert_key = VK_CONVERT
        self.nonconvert_key = VK_NONCONVERT
        self.accept_key = VK_ACCEPT
        self.modechange_key = VK_MODECHANGE
        #More Keys
        self.escape_key = VK_ESCAPE
        self.space_key = VK_SPACE
        self.prior_key = VK_PRIOR
        self.next_key = VK_NEXT
        self.page_up_key = self.prior_key
        self.page_down_key = self.next_key
        self.home_key = VK_HOME
        self.up_key = VK_UP
        self.down_key = VK_DOWN
        self.left_key = VK_LEFT
        self.right_key = VK_RIGHT
        self.end_key = VK_END
        self.select_key = VK_SELECT
        self.print_key = VK_PRINT
        self.snapshot_key = VK_SNAPSHOT
        self.print_screen_key = self.snapshot_key
        self.execute_key = VK_EXECUTE
        self.insert_key = VK_INSERT
        self.delete_key = VK_DELETE
        self.help_key = VK_HELP
        self.windows_l_key = VK_LWIN
        self.super_l_key = self.windows_l_key
        self.windows_r_key = VK_RWIN
        self.super_r_key = self.windows_r_key
        self.apps_key = VK_APPS
        #Numpad
        self.keypad_keys = {'Space': None,
                            'Tab': None,
                            'Enter': None,  # Needs Fixing
                            'F1': None,
                            'F2': None,
                            'F3': None,
                            'F4': None,
                            'Home': VK_NUMPAD7,
                            'Left': VK_NUMPAD4,
                            'Up': VK_NUMPAD8,
                            'Right': VK_NUMPAD6,
                            'Down': VK_NUMPAD2,
                            'Prior': None,
                            'Page_Up': VK_NUMPAD9,
                            'Next': None,
                            'Page_Down': VK_NUMPAD3,
                            'End': VK_NUMPAD1,
                            'Begin': None,
                            'Insert': VK_NUMPAD0,
                            'Delete': VK_DECIMAL,
                            'Equal': None,  # Needs Fixing
                            'Multiply': VK_MULTIPLY,
                            'Add': VK_ADD,
                            'Separator': VK_SEPARATOR,
                            'Subtract': VK_SUBTRACT,
                            'Decimal': VK_DECIMAL,
                            'Divide': VK_DIVIDE,
                            0: VK_NUMPAD0,
                            1: VK_NUMPAD1,
                            2: VK_NUMPAD2,
                            3: VK_NUMPAD3,
                            4: VK_NUMPAD4,
                            5: VK_NUMPAD5,
                            6: VK_NUMPAD6,
                            7: VK_NUMPAD7,
                            8: VK_NUMPAD8,
                            9: VK_NUMPAD9}
        self.numpad_keys = self.keypad_keys
        #FKeys
        self.function_keys = [None, VK_F1, VK_F2, VK_F3, VK_F4, VK_F5, VK_F6,
                              VK_F7, VK_F8, VK_F9, VK_F10, VK_F11, VK_F12,
                              VK_F13, VK_F14, VK_F15, VK_F16, VK_F17, VK_F18,
                              VK_F19, VK_F20, VK_F21, VK_F22, VK_F23, VK_F24,
                              None, None, None, None, None, None, None, None,
                              None, None, None]  # Up to 36 as in x11
        #Miscellaneous
        self.cancel_key = VK_CANCEL
        self.break_key = self.cancel_key
        self.mode_switch_key = VK_MODECHANGE
        self.browser_back_key = VK_BROWSER_BACK
        self.browser_forward_key = VK_BROWSER_FORWARD
        self.processkey_key = VK_PROCESSKEY
        self.attn_key = VK_ATTN
        self.crsel_key = VK_CRSEL
        self.exsel_key = VK_EXSEL
        self.ereof_key = VK_EREOF
        self.play_key = VK_PLAY
        self.zoom_key = VK_ZOOM
        self.noname_key = VK_NONAME
        self.pa1_key = VK_PA1
        self.oem_clear_key = VK_OEM_CLEAR
        self.volume_mute_key = VK_VOLUME_MUTE
        self.volume_down_key = VK_VOLUME_DOWN
        self.volume_up_key = VK_VOLUME_UP
        self.media_next_track_key = VK_MEDIA_NEXT_TRACK
        self.media_prev_track_key = VK_MEDIA_PREV_TRACK
        self.media_play_pause_key = VK_MEDIA_PLAY_PAUSE
        self.begin_key = self.home_key
        #LKeys - Unsupported
        self.l_keys = [None] * 11
        #RKeys - Unsupported
        self.r_keys = [None] * 16

        #Other unsupported Keys from X11
        self.linefeed_key = None
        self.find_key = None
        self.meta_l_key = None
        self.meta_r_key = None
        self.sys_req_key = None
        self.hyper_l_key = None
        self.hyper_r_key = None
        self.undo_key = None
        self.redo_key = None
        self.script_switch_key = None

class PyKeyboardEvent(PyKeyboardEventMeta):
    """
    The PyKeyboardEvent implementation for Windows Systems. This allows one
    to listen for keyboard input.
    """
    def __init__(self, diagnostic=False):
        self.diagnostic = diagnostic

        import pyHook

        PyKeyboardEventMeta.__init__(self)
        self.hm = pyHook.HookManager()
        self.hc = pyHook.HookConstants()

        self.lock_meaning = None

    def run(self):
        """Begin listening for keyboard input events."""
        self.state = True
        self.hm.KeyAll = self.handler
        self.hm.HookKeyboard()
        while self.state:
            time.sleep(0.01)
            pythoncom.PumpWaitingMessages()

    def stop(self):
        """Stop listening for keyboard input events."""
        self.hm.UnhookKeyboard()
        self.state = False

    def handler(self, event):
        """Upper level handler of keyboard events."""

        if self.escape(event):  # A chance to escape
            self.stop()
        elif self.diagnostic:
            self._diagnostic(event)
        else:
            self._tap(event)
        #This is needed according to the pyHook tutorials 'http://sourceforge.net/apps/mediawiki/pyhook/index.php?title=PyHook_Tutorial'
        return True

    def _tap(self, event):
        keycode = event.KeyID
        press_bool = (event.Message in [self.hc.WM_KEYDOWN, self.hc.WM_SYSKEYDOWN])

        #Not using event.GeyKey() because we want to differentiate between
        #KeyID and Ascii attributes of the event
        if event.Ascii != 0:
            character = chr(event.Ascii)
        else:
            character = self.hc.id_to_vk[keycode][3:]

        #TODO: Need to universalize keys between platforms. ie. 'Menu' -> 'Alt'

        self.tap(keycode, character, press_bool)

    def _diagnostic(self, event):
        """
        This method is employed instead of _tap() if the PyKeyboardEvent is
        initialized with diagnostic=True. This makes some basic testing quickly
        and easily available. It will print out information regarding the event
        instead of passing information along to self.tap()
        """
        print('\n---Keyboard Event Diagnostic---')
        print('MessageName:', event.MessageName)
        print('Message:', event.Message)
        print('Time:', event.Time)
        print('Window:', event.Window)
        print('WindowName:', event.WindowName)
        print('Ascii:', event.Ascii, ',', chr(event.Ascii))
        print('Key:', event.Key)
        print('KeyID:', event.KeyID)
        print('ScanCode:', event.ScanCode)
        print('Extended:', event.Extended)
        print('Injected:', event.Injected)
        print('Alt', event.Alt)
        print('Transition', event.Transition)
        print('---')

    def escape(self, event):
        return event.KeyID == VK_ESCAPE

    def toggle_shift_state(self):  # This will be removed later
        '''Does toggling for the shift state.'''
        states = [1, 0]
        self.shift_state = states[self.shift_state]

    def toggle_alt_state(self):  # This will be removed later
        '''Does toggling for the alt state.'''
        states = [2, None, 0]
        self.alt_state = states[self.alt_state]

    def configure_keys(self):
        """
        This does initial configuration for keyboard modifier state tracking
        including alias setting and keycode list construction.
        """
        pass

########NEW FILE########
__FILENAME__ = x11
#Copyright 2013 Paul Barton
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from Xlib.display import Display
from Xlib import X
from Xlib.ext.xtest import fake_input
from Xlib.ext import record
from Xlib.protocol import rq
import Xlib.XK

from .base import PyKeyboardMeta, PyKeyboardEventMeta

import time
import string

special_X_keysyms = {
    ' ': "space",
    '\t': "Tab",
    '\n': "Return",  # for some reason this needs to be cr, not lf
    '\r': "Return",
    '\e': "Escape",
    '!': "exclam",
    '#': "numbersign",
    '%': "percent",
    '$': "dollar",
    '&': "ampersand",
    '"': "quotedbl",
    '\'': "apostrophe",
    '(': "parenleft",
    ')': "parenright",
    '*': "asterisk",
    '=': "equal",
    '+': "plus",
    ',': "comma",
    '-': "minus",
    '.': "period",
    '/': "slash",
    ':': "colon",
    ';': "semicolon",
    '<': "less",
    '>': "greater",
    '?': "question",
    '@': "at",
    '[': "bracketleft",
    ']': "bracketright",
    '\\': "backslash",
    '^': "asciicircum",
    '_': "underscore",
    '`': "grave",
    '{': "braceleft",
    '|': "bar",
    '}': "braceright",
    '~': "asciitilde"
    }

class PyKeyboard(PyKeyboardMeta):
    """
    The PyKeyboard implementation for X11 systems (mostly linux). This
    allows one to simulate keyboard input.
    """
    def __init__(self, display=None):
        PyKeyboardMeta.__init__(self)
        self.display = Display(display)
        self.display2 = Display(display)
        self.special_key_assignment()

    def press_key(self, character=''):
        """
        Press a given character key. Also works with character keycodes as
        integers, but not keysyms.
        """
        try:  # Detect uppercase or shifted character
            shifted = self.is_char_shifted(character)
        except AttributeError:  # Handle the case of integer keycode argument
            fake_input(self.display, X.KeyPress, character)
            self.display.sync()
        else:
            if shifted:
                fake_input(self.display, X.KeyPress, self.shift_key)
            keycode = self.lookup_character_keycode(character)
            fake_input(self.display, X.KeyPress, keycode)
            self.display.sync()

    def release_key(self, character=''):
        """
        Release a given character key. Also works with character keycodes as
        integers, but not keysyms.
        """
        try:  # Detect uppercase or shifted character
            shifted = self.is_char_shifted(character)
        except AttributeError:  # Handle the case of integer keycode argument
            fake_input(self.display, X.KeyRelease, character)
            self.display.sync()
        else:
            if shifted:
                fake_input(self.display, X.KeyRelease, self.shift_key)
            keycode = self.lookup_character_keycode(character)
            fake_input(self.display, X.KeyRelease, keycode)
            self.display.sync()

    def special_key_assignment(self):
        """
        Determines the keycodes for common special keys on the keyboard. These
        are integer values and can be passed to the other key methods.
        Generally speaking, these are non-printable codes.
        """
        #This set of keys compiled using the X11 keysymdef.h file as reference
        #They comprise a relatively universal set of keys, though there may be
        #exceptions which may come up for other OSes and vendors. Countless
        #special cases exist which are not handled here, but may be extended.
        #TTY Function Keys
        self.backspace_key = self.lookup_character_keycode('BackSpace')
        self.tab_key = self.lookup_character_keycode('Tab')
        self.linefeed_key = self.lookup_character_keycode('Linefeed')
        self.clear_key = self.lookup_character_keycode('Clear')
        self.return_key = self.lookup_character_keycode('Return')
        self.enter_key = self.return_key  # Because many keyboards call it "Enter"
        self.pause_key = self.lookup_character_keycode('Pause')
        self.scroll_lock_key = self.lookup_character_keycode('Scroll_Lock')
        self.sys_req_key = self.lookup_character_keycode('Sys_Req')
        self.escape_key = self.lookup_character_keycode('Escape')
        self.delete_key = self.lookup_character_keycode('Delete')
        #Modifier Keys
        self.shift_l_key = self.lookup_character_keycode('Shift_L')
        self.shift_r_key = self.lookup_character_keycode('Shift_R')
        self.shift_key = self.shift_l_key  # Default Shift is left Shift
        self.alt_l_key = self.lookup_character_keycode('Alt_L')
        self.alt_r_key = self.lookup_character_keycode('Alt_R')
        self.alt_key = self.alt_l_key  # Default Alt is left Alt
        self.control_l_key = self.lookup_character_keycode('Control_L')
        self.control_r_key = self.lookup_character_keycode('Control_R')
        self.control_key = self.control_l_key  # Default Ctrl is left Ctrl
        self.caps_lock_key = self.lookup_character_keycode('Caps_Lock')
        self.capital_key = self.caps_lock_key  # Some may know it as Capital
        self.shift_lock_key = self.lookup_character_keycode('Shift_Lock')
        self.meta_l_key = self.lookup_character_keycode('Meta_L')
        self.meta_r_key = self.lookup_character_keycode('Meta_R')
        self.super_l_key = self.lookup_character_keycode('Super_L')
        self.windows_l_key = self.super_l_key  # Cross-support; also it's printed there
        self.super_r_key = self.lookup_character_keycode('Super_R')
        self.windows_r_key = self.super_r_key  # Cross-support; also it's printed there
        self.hyper_l_key = self.lookup_character_keycode('Hyper_L')
        self.hyper_r_key = self.lookup_character_keycode('Hyper_R')
        #Cursor Control and Motion
        self.home_key = self.lookup_character_keycode('Home')
        self.up_key = self.lookup_character_keycode('Up')
        self.down_key = self.lookup_character_keycode('Down')
        self.left_key = self.lookup_character_keycode('Left')
        self.right_key = self.lookup_character_keycode('Right')
        self.end_key = self.lookup_character_keycode('End')
        self.begin_key = self.lookup_character_keycode('Begin')
        self.page_up_key = self.lookup_character_keycode('Page_Up')
        self.page_down_key = self.lookup_character_keycode('Page_Down')
        self.prior_key = self.lookup_character_keycode('Prior')
        self.next_key = self.lookup_character_keycode('Next')
        #Misc Functions
        self.select_key = self.lookup_character_keycode('Select')
        self.print_key = self.lookup_character_keycode('Print')
        self.print_screen_key = self.print_key  # Seems to be the same thing
        self.snapshot_key = self.print_key  # Another name for printscreen
        self.execute_key = self.lookup_character_keycode('Execute')
        self.insert_key = self.lookup_character_keycode('Insert')
        self.undo_key = self.lookup_character_keycode('Undo')
        self.redo_key = self.lookup_character_keycode('Redo')
        self.menu_key = self.lookup_character_keycode('Menu')
        self.apps_key = self.menu_key  # Windows...
        self.find_key = self.lookup_character_keycode('Find')
        self.cancel_key = self.lookup_character_keycode('Cancel')
        self.help_key = self.lookup_character_keycode('Help')
        self.break_key = self.lookup_character_keycode('Break')
        self.mode_switch_key = self.lookup_character_keycode('Mode_switch')
        self.script_switch_key = self.lookup_character_keycode('script_switch')
        self.num_lock_key = self.lookup_character_keycode('Num_Lock')
        #Keypad Keys: Dictionary structure
        keypad = ['Space', 'Tab', 'Enter', 'F1', 'F2', 'F3', 'F4', 'Home',
                  'Left', 'Up', 'Right', 'Down', 'Prior', 'Page_Up', 'Next',
                  'Page_Down', 'End', 'Begin', 'Insert', 'Delete', 'Equal',
                  'Multiply', 'Add', 'Separator', 'Subtract', 'Decimal',
                  'Divide', 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        self.keypad_keys = {k: self.lookup_character_keycode('KP_'+str(k)) for k in keypad}
        self.numpad_keys = self.keypad_keys
        #Function Keys/ Auxilliary Keys
        #FKeys
        self.function_keys = [None] + [self.lookup_character_keycode('F'+str(i)) for i in range(1,36)]
        #LKeys
        self.l_keys = [None] + [self.lookup_character_keycode('L'+str(i)) for i in range(1,11)]
        #RKeys
        self.r_keys = [None] + [self.lookup_character_keycode('R'+str(i)) for i in range(1,16)]

        #Unsupported keys from windows
        self.kana_key = None
        self.hangeul_key = None # old name - should be here for compatibility
        self.hangul_key = None
        self.junjua_key = None
        self.final_key = None
        self.hanja_key = None
        self.kanji_key = None
        self.convert_key = None
        self.nonconvert_key = None
        self.accept_key = None
        self.modechange_key = None
        self.sleep_key = None

    def lookup_character_keycode(self, character):
        """
        Looks up the keysym for the character then returns the keycode mapping
        for that keysym.
        """
        keysym = Xlib.XK.string_to_keysym(character)
        if keysym == 0:
            keysym = Xlib.XK.string_to_keysym(special_X_keysyms[character])
        return self.display.keysym_to_keycode(keysym)


class PyKeyboardEvent(PyKeyboardEventMeta):
    """
    The PyKeyboardEvent implementation for X11 systems (mostly linux). This
    allows one to listen for keyboard input.
    """
    def __init__(self, display=None):
        self.display = Display(display)
        self.display2 = Display(display)
        self.ctx = self.display2.record_create_context(
            0,
            [record.AllClients],
            [{
                    'core_requests': (0, 0),
                    'core_replies': (0, 0),
                    'ext_requests': (0, 0, 0, 0),
                    'ext_replies': (0, 0, 0, 0),
                    'delivered_events': (0, 0),
                    'device_events': (X.KeyPress, X.KeyRelease),
                    'errors': (0, 0),
                    'client_started': False,
                    'client_died': False,
            }])

        self.lock_meaning = None

        #Get these dictionaries for converting keysyms and strings
        self.keysym_to_string, self.string_to_keysym = self.get_translation_dicts()

        #Identify and register special groups of keys
        self.modifier_keycodes = {}
        self.all_mod_keycodes = []
        self.keypad_keycodes = []
        #self.configure_keys()

        #Direct access to the display's keycode-to-keysym array
        #print('Keycode to Keysym map')
        #for i in range(len(self.display._keymap_codes)):
        #    print('{0}: {1}'.format(i, self.display._keymap_codes[i]))

        PyKeyboardEventMeta.__init__(self)

    def run(self):
        """Begin listening for keyboard input events."""
        self.state = True
        if self.capture:
            self.display2.screen().root.grab_keyboard(True, X.KeyPressMask | X.KeyReleaseMask, X.GrabModeAsync, X.GrabModeAsync, 0, 0, X.CurrentTime)

        self.display2.record_enable_context(self.ctx, self.handler)
        self.display2.record_free_context(self.ctx)

    def stop(self):
        """Stop listening for keyboard input events."""
        self.state = False
        self.display.record_disable_context(self.ctx)
        self.display.ungrab_keyboard(X.CurrentTime)
        self.display.flush()
        self.display2.record_disable_context(self.ctx)
        self.display2.ungrab_keyboard(X.CurrentTime)
        self.display2.flush()

    def handler(self, reply):
        """Upper level handler of keyboard events."""
        data = reply.data
        while len(data):
            event, data = rq.EventField(None).parse_binary_value(data, self.display.display, None, None)
            if self.escape(event):  # Quit if this returns True
                self.stop()
            else:
                self._tap(event)

    def _tap(self, event):
        keycode = event.detail
        press_bool = (event.type == X.KeyPress)

        #Detect modifier states from event.state
        for mod, bit in self.modifier_bits.items():
            self.modifiers[mod] = event.state & bit

        if keycode in self.all_mod_keycodes:
            keysym = self.display.keycode_to_keysym(keycode, 0)
            character = self.keysym_to_string[keysym]
        else:
            character = self.lookup_char_from_keycode(keycode)

        #All key events get passed to self.tap()
        self.tap(keycode,
                 character,
                 press=press_bool)

    def lookup_char_from_keycode(self, keycode):
        """
        This will conduct a lookup of the character or string associated with a
        given keycode.
        """

        #TODO: Logic should be strictly adapted from X11's src/KeyBind.c
        #Right now the logic is based off of
        #http://tronche.com/gui/x/xlib/input/keyboard-encoding.html
        #Which I suspect is not the whole story and may likely cause bugs

        keysym_index = 0
        #TODO: Display's Keysyms per keycode count? Do I need this?
        #If the Num_Lock is on, and the keycode corresponds to the keypad
        if self.modifiers['Num_Lock'] and keycode in self.keypad_keycodes:
            if self.modifiers['Shift'] or self.modifiers['Shift_Lock']:
                keysym_index = 0
            else:
                keysym_index = 1

        elif not self.modifiers['Shift'] and self.modifiers['Caps_Lock']:
            #Use the first keysym if uppercase or uncased
            #Use the uppercase keysym if the first is lowercase (second)
            keysym_index = 0
            keysym = self.display.keycode_to_keysym(keycode, keysym_index)
            #TODO: Support Unicode, Greek, and special latin characters
            if keysym & 0x7f == keysym and chr(keysym) in 'abcdefghijklmnopqrstuvwxyz':
                keysym_index = 1

        elif self.modifiers['Shift'] and self.modifiers['Caps_Lock']:
            keysym_index = 1
            keysym = self.display.keycode_to_keysym(keycode, keysym_index)
            #TODO: Support Unicode, Greek, and special latin characters
            if keysym & 0x7f == keysym and chr(keysym) in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                keysym_index = 0

        elif self.modifiers['Shift'] or self.modifiers['Shift_Lock']:
            keysym_index = 1

        if self.modifiers['Mode_switch']:
            keysym_index += 2

        #Finally! Get the keysym
        keysym = self.display.keycode_to_keysym(keycode, keysym_index)

        #If the character is ascii printable, return that character
        if keysym & 0x7f == keysym and self.ascii_printable(keysym):
            return chr(keysym)

        #If the character was not printable, look for its name
        try:
            char = self.keysym_to_string[keysym]
        except KeyError:
            print('Unable to determine character.')
            print('Keycode: {0} KeySym {1}'.format(keycode, keysym))
            return None
        else:
            return char

    def escape(self, event):
        if event.detail == self.lookup_character_keycode('Escape'):
            return True
        return False

    def configure_keys(self):
        """
        This function locates the keycodes corresponding to special groups of
        keys and creates data structures of them for use by the PyKeyboardEvent
        instance; including the keypad keys and the modifiers.

        The keycodes pertaining to the keyboard modifiers are assigned by the
        modifier name in a dictionary. This dictionary can be accessed in the
        following manner:
            self.modifier_keycodes['Shift']  # All keycodes for Shift Masking

        It also assigns certain named modifiers (Alt, Num_Lock, Super), which
        may be dynamically assigned to Mod1 - Mod5 on different platforms. This
        should generally allow the user to do the following lookups on any
        system:
            self.modifier_keycodes['Alt']  # All keycodes for Alt Masking
            self.modifiers['Alt']  # State of Alt mask, non-zero if "ON"
        """
        modifier_mapping = self.display.get_modifier_mapping()
        all_mod_keycodes = []
        mod_keycodes = {}
        mod_index = [('Shift', X.ShiftMapIndex), ('Lock', X.LockMapIndex),
                     ('Control', X.ControlMapIndex), ('Mod1', X.Mod1MapIndex),
                     ('Mod2', X.Mod2MapIndex), ('Mod3', X.Mod3MapIndex),
                     ('Mod4', X.Mod4MapIndex), ('Mod5', X.Mod5MapIndex)]
        #This gets the list of all keycodes per Modifier, assigns to name
        for name, index in mod_index:
            codes = [v for v in list(modifier_mapping[index]) if v]
            mod_keycodes[name] = codes
            all_mod_keycodes += codes

        def lookup_keycode(string):
            keysym = self.string_to_keysym[string]
            return self.display.keysym_to_keycode(keysym)

        #Dynamically assign Lock to Caps_Lock, Shift_Lock, Alt, Num_Lock, Super,
        #and mode switch. Set in both mod_keycodes and self.modifier_bits

        #Try to assign Lock to Caps_Lock or Shift_Lock
        shift_lock_keycode = lookup_keycode('Shift_Lock')
        caps_lock_keycode = lookup_keycode('Caps_Lock')

        if shift_lock_keycode in mod_keycodes['Lock']:
            mod_keycodes['Shift_Lock'] = [shift_lock_keycode]
            self.modifier_bits['Shift_Lock'] = self.modifier_bits['Lock']
            self.lock_meaning = 'Shift_Lock'
        elif caps_lock_keycode in mod_keycodes['Lock']:
            mod_keycodes['Caps_Lock'] = [caps_lock_keycode]
            self.modifier_bits['Caps_Lock'] = self.modifier_bits['Lock']
            self.lock_meaning = 'Caps_Lock'
        else:
            self.lock_meaning = None
        #print('Lock is bound to {0}'.format(self.lock_meaning))

        #Need to find out which Mod# to use for Alt, Num_Lock, Super, and
        #Mode_switch
        num_lock_keycodes = [lookup_keycode('Num_Lock')]
        alt_keycodes = [lookup_keycode(i) for i in ['Alt_L', 'Alt_R']]
        super_keycodes = [lookup_keycode(i) for i in ['Super_L', 'Super_R']]
        mode_switch_keycodes = [lookup_keycode('Mode_switch')]

        #Detect Mod number for Alt, Num_Lock, and Super
        for name, keycodes in list(mod_keycodes.items()):
            for alt_key in alt_keycodes:
                if alt_key in keycodes:
                    mod_keycodes['Alt'] = keycodes
                    self.modifier_bits['Alt'] = self.modifier_bits[name]
            for num_lock_key in num_lock_keycodes:
                if num_lock_key in keycodes:
                    mod_keycodes['Num_Lock'] = keycodes
                    self.modifier_bits['Num_Lock'] = self.modifier_bits[name]
            for super_key in super_keycodes:
                if super_key in keycodes:
                    mod_keycodes['Super'] = keycodes
                    self.modifier_bits['Super'] = self.modifier_bits[name]
            for mode_switch_key in mode_switch_keycodes:
                if mode_switch_key in keycodes:
                    mod_keycodes['Mode_switch'] = keycodes
                    self.modifier_bits['Mode_switch'] = self.modifier_bits[name]

        #Assign the mod_keycodes to a local variable for access
        self.modifier_keycodes = mod_keycodes
        self.all_mod_keycodes = all_mod_keycodes

        #TODO: Determine if this might fail, perhaps iterate through the mapping
        #and identify all keycodes with registered keypad keysyms?

        #Acquire the full list of keypad keycodes
        self.keypad_keycodes = []
        keypad = ['Space', 'Tab', 'Enter', 'F1', 'F2', 'F3', 'F4', 'Home',
                  'Left', 'Up', 'Right', 'Down', 'Prior', 'Page_Up', 'Next',
                  'Page_Down', 'End', 'Begin', 'Insert', 'Delete', 'Equal',
                  'Multiply', 'Add', 'Separator', 'Subtract', 'Decimal',
                  'Divide', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
        for keyname in keypad:
            keypad_keycode = self.lookup_character_keycode('KP_' + keyname)
            self.keypad_keycodes.append(keypad_keycode)

    def lookup_character_keycode(self, character):
        """
        Looks up the keysym for the character then returns the keycode mapping
        for that keysym.
        """
        keysym = self.string_to_keysym.get(character, 0)
        if keysym == 0:
            keysym = self.string_to_keysym.get(special_X_keysyms[character], 0)
        return self.display.keysym_to_keycode(keysym)

    def get_translation_dicts(self):
        """
        Returns dictionaries for the translation of keysyms to strings and from
        strings to keysyms.
        """
        keysym_to_string_dict = {}
        string_to_keysym_dict = {}
        #XK loads latin1 and miscellany on its own; load latin2-4 and greek
        Xlib.XK.load_keysym_group('latin2')
        Xlib.XK.load_keysym_group('latin3')
        Xlib.XK.load_keysym_group('latin4')
        Xlib.XK.load_keysym_group('greek')

        #Make a standard dict and the inverted dict
        for string, keysym in Xlib.XK.__dict__.items():
            if string.startswith('XK_'):
                string_to_keysym_dict[string[3:]] = keysym
                keysym_to_string_dict[keysym] = string[3:]
        return keysym_to_string_dict, string_to_keysym_dict

    def ascii_printable(self, keysym):
        """
        If the keysym corresponds to a non-printable ascii character this will
        return False. If it is printable, then True will be returned.

        ascii 11 (vertical tab) and ascii 12 are printable, chr(11) and chr(12)
        will return '\x0b' and '\x0c' respectively.
        """
        if 0 <= keysym < 9:
            return False
        elif 13 < keysym < 32:
            return False
        elif keysym > 126:
            return False
        else:
            return True

########NEW FILE########
__FILENAME__ = base
#Copyright 2013 Paul Barton
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
The goal of PyMouse is to have a cross-platform way to control the mouse.
PyMouse should work on Windows, Mac and any Unix that has xlib.

As the base file, this provides a rough operational model along with the
framework to be extended by each platform.
"""

from threading import Thread


class ScrollSupportError(Exception):
    pass


class PyMouseMeta(object):

    def press(self, x, y, button=1):
        """
        Press the mouse on a given x, y and button.
        Button is defined as 1 = left, 2 = right, 3 = middle.
        """

        raise NotImplementedError

    def release(self, x, y, button=1):
        """
        Release the mouse on a given x, y and button.
        Button is defined as 1 = left, 2 = right, 3 = middle.
        """

        raise NotImplementedError

    def click(self, x, y, button=1, n=1):
        """
        Click a mouse button n times on a given x, y.
        Button is defined as 1 = left, 2 = right, 3 = middle.
        """

        for i in range(n):
            self.press(x, y, button)
            self.release(x, y, button)

    def scroll(self, vertical=None, horizontal=None, depth=None):
        """
        Generates mouse scrolling events in up to three dimensions: vertical,
        horizontal, and depth (Mac-only). Values for these arguments may be
        positive or negative numbers (float or int). Refer to the following:
            Vertical: + Up, - Down
            Horizontal: + Right, - Left
            Depth: + Rise (out of display), - Dive (towards display)

        Dynamic scrolling, which is used Windows and Mac platforms, is not
        implemented at this time due to an inability to test Mac code. The
        events generated by this code will thus be discrete units of scrolling
        "lines". The user is advised to take care at all times with scrolling
        automation as scrolling event consumption is relatively un-standardized.

        Float values will be coerced to integers.
        """

        raise NotImplementedError

    def move(self, x, y):
        """Move the mouse to a given x and y"""

        raise NotImplementedError

    def drag(self, x, y):
        """Drag the mouse to a given x and y.
        A Drag is a Move where the mouse key is held down."""

        raise NotImplementedError

    def position(self):
        """
        Get the current mouse position in pixels.
        Returns a tuple of 2 integers
        """

        raise NotImplementedError

    def screen_size(self):
        """
        Get the current screen size in pixels.
        Returns a tuple of 2 integers
        """

        raise NotImplementedError


class PyMouseEventMeta(Thread):
    def __init__(self, capture=False, capture_move=False):
        Thread.__init__(self)
        self.daemon = True
        self.capture = capture
        self.capture_move = capture_move
        self.state = True

    def stop(self):
        self.state = False

    def click(self, x, y, button, press):
        """Subclass this method with your click event handler"""
        pass

    def move(self, x, y):
        """Subclass this method with your move event handler"""
        pass

########NEW FILE########
__FILENAME__ = java_
#Copyright 2013 Paul Barton
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from java.awt import Robot, Toolkit
from java.awt.event import InputEvent
from java.awt.MouseInfo import getPointerInfo
from .base import PyMouseMeta

r = Robot()

class PyMouse(PyMouseMeta):
    def press(self, x, y, button = 1):
        button_list = [None, InputEvent.BUTTON1_MASK, InputEvent.BUTTON3_MASK, InputEvent.BUTTON2_MASK]
        self.move(x, y)
        r.mousePress(button_list[button])

    def release(self, x, y, button = 1):
        button_list = [None, InputEvent.BUTTON1_MASK, InputEvent.BUTTON3_MASK, InputEvent.BUTTON2_MASK]
        self.move(x, y)
        r.mouseRelease(button_list[button])
    
    def move(self, x, y):
        r.mouseMove(x, y)

    def position(self):
        loc = getPointerInfo().getLocation()
        return loc.getX, loc.getY

    def screen_size(self):
        dim = Toolkit.getDefaultToolkit().getScreenSize()
        return dim.getWidth(), dim.getHeight()

########NEW FILE########
__FILENAME__ = mac
#Copyright 2013 Paul Barton
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from Quartz import *
from AppKit import NSEvent
from .base import PyMouseMeta, PyMouseEventMeta

pressID = [None, kCGEventLeftMouseDown,
           kCGEventRightMouseDown, kCGEventOtherMouseDown]
releaseID = [None, kCGEventLeftMouseUp,
             kCGEventRightMouseUp, kCGEventOtherMouseUp]


class PyMouse(PyMouseMeta):

    def press(self, x, y, button=1):
        event = CGEventCreateMouseEvent(None,
                                        pressID[button],
                                        (x, y),
                                        button - 1)
        CGEventPost(kCGHIDEventTap, event)

    def release(self, x, y, button=1):
        event = CGEventCreateMouseEvent(None,
                                        releaseID[button],
                                        (x, y),
                                        button - 1)
        CGEventPost(kCGHIDEventTap, event)

    def move(self, x, y):
        move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, (x, y), 0)
        CGEventPost(kCGHIDEventTap, move)

    def drag(self, x, y):
        drag = CGEventCreateMouseEvent(None, kCGEventLeftMouseDragged, (x, y), 0)
        CGEventPost(kCGHIDEventTap, drag)

    def position(self):
        loc = NSEvent.mouseLocation()
        return loc.x, CGDisplayPixelsHigh(0) - loc.y

    def screen_size(self):
        return CGDisplayPixelsWide(0), CGDisplayPixelsHigh(0)

    def scroll(self, vertical=None, horizontal=None, depth=None):
        #Local submethod for generating Mac scroll events in one axis at a time
        def scroll_event(y_move=None, x_move=None, z_move=None, n=1):
            for _ in range(abs(n)):
                scrollWheelEvent = CGEventCreateScrollWheelEvent(
                    None,  # No source
                    kCGScrollEventUnitLine,  # Unit of measurement is lines
                    3,  # Number of wheels(dimensions)
                    y_move,
                    x_move,
                    z_move)
                CGEventPost(kCGHIDEventTap, scrollWheelEvent)

        #Execute vertical then horizontal then depth scrolling events
        if vertical is not None:
            vertical = int(vertical)
            if vertical == 0:   # Do nothing with 0 distance
                pass
            elif vertical > 0:  # Scroll up if positive
                scroll_event(y_movement=1, n=vertical)
            else:  # Scroll down if negative
                scroll_event(y_movement=-1, n=abs(vertical))
        if horizontal is not None:
            horizontal = int(horizontal)
            if horizontal == 0:  # Do nothing with 0 distance
                pass
            elif horizontal > 0:  # Scroll right if positive
                scroll_event(x_movement=1, n=horizontal)
            else:  # Scroll left if negative
                scroll_event(x_movement=-1, n=abs(horizontal))
        if depth is not None:
            depth = int(depth)
            if depth == 0:  # Do nothing with 0 distance
                pass
            elif vertical > 0:  # Scroll "out" if positive
                scroll_event(z_movement=1, n=depth)
            else:  # Scroll "in" if negative
                scroll_event(z_movement=-1, n=abs(depth))


class PyMouseEvent(PyMouseEventMeta):
    def run(self):
        tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionDefault,
            CGEventMaskBit(kCGEventMouseMoved) |
            CGEventMaskBit(kCGEventLeftMouseDown) |
            CGEventMaskBit(kCGEventLeftMouseUp) |
            CGEventMaskBit(kCGEventRightMouseDown) |
            CGEventMaskBit(kCGEventRightMouseUp) |
            CGEventMaskBit(kCGEventOtherMouseDown) |
            CGEventMaskBit(kCGEventOtherMouseUp),
            self.handler,
            None)

        loopsource = CFMachPortCreateRunLoopSource(None, tap, 0)
        loop = CFRunLoopGetCurrent()
        CFRunLoopAddSource(loop, loopsource, kCFRunLoopDefaultMode)
        CGEventTapEnable(tap, True)

        while self.state:
            CFRunLoopRunInMode(kCFRunLoopDefaultMode, 5, False)

    def handler(self, proxy, type, event, refcon):
        (x, y) = CGEventGetLocation(event)
        if type in pressID:
            self.click(x, y, pressID.index(type), True)
        elif type in releaseID:
            self.click(x, y, releaseID.index(type), False)
        else:
            self.move(x, y)

        if self.capture:
            CGEventSetType(event, kCGEventNull)

        return event

########NEW FILE########
__FILENAME__ = mir
#Copyright 2013 Paul Barton
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = wayland
#Copyright 2013 Paul Barton
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = windows
#Copyright 2013 Paul Barton
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from ctypes import *
import win32api, win32con
from .base import PyMouseMeta, PyMouseEventMeta, ScrollSupportError
import pythoncom
from time import sleep

class POINT(Structure):
    _fields_ = [("x", c_ulong),
                ("y", c_ulong)]

class PyMouse(PyMouseMeta):
    """MOUSEEVENTF_(button and action) constants
    are defined at win32con, buttonAction is that value"""

    def press(self, x, y, button=1):
        buttonAction = 2 ** ((2 * button) - 1)
        self.move(x, y)
        win32api.mouse_event(buttonAction, x, y)

    def release(self, x, y, button=1):
        buttonAction = 2 ** ((2 * button))
        self.move(x, y)
        win32api.mouse_event(buttonAction, x, y)

    def scroll(self, vertical=None, horizontal=None, depth=None):

        #Windows supports only vertical and horizontal scrolling
        if depth is not None:
            raise ScrollSupportError('PyMouse cannot support depth-scrolling \
in Windows. This feature is only available on Mac.')

        #Execute vertical then horizontal scrolling events
        if vertical is not None:
            vertical = int(vertical)
            if vertical == 0:  # Do nothing with 0 distance
                pass
            elif vertical > 0:  # Scroll up if positive
                for _ in range(vertical):
                    win32api.mouse_event(0x0800, 0, 0, 120, 0)
            else:  # Scroll down if negative
                for _ in range(abs(vertical)):
                    win32api.mouse_event(0x0800, 0, 0, -120, 0)
        if horizontal is not None:
            horizontal = int(horizontal)
            if horizontal == 0:  # Do nothing with 0 distance
                pass
            elif horizontal > 0:  # Scroll right if positive
                for _ in range(horizontal):
                    win32api.mouse_event(0x01000, 0, 0, 120, 0)
            else:  # Scroll left if negative
                for _ in range(abs(horizontal)):
                    win32api.mouse_event(0x01000, 0, 0, -120, 0)

    def move(self, x, y):
        windll.user32.SetCursorPos(x, y)

    def drag(self, x, y):
        self.press(*m.position())
        #self.move(x, y)
        self.release(x, y)

    def position(self):
        pt = POINT()
        windll.user32.GetCursorPos(byref(pt))
        return pt.x, pt.y

    def screen_size(self):
        if windll.user32.GetSystemMetrics(80) == 1:
            width = windll.user32.GetSystemMetrics(0)
            height = windll.user32.GetSystemMetrics(1)
        else:
            width = windll.user32.GetSystemMetrics(78)
            height = windll.user32.GetSystemMetrics(79)
        return width, height

class PyMouseEvent(PyMouseEventMeta):
    def __init__(self, capture=False, capture_move=False):
        import pyHook

        PyMouseEventMeta.__init__(self, capture=capture, capture_move=capture_move)
        self.hm = pyHook.HookManager()

    def run(self):
        self.hm.MouseAll = self._action
        self.hm.HookMouse()
        while self.state:
            sleep(0.01)
            pythoncom.PumpWaitingMessages()

    def stop(self):
        self.hm.UnhookMouse()
        self.state = False

    def _action(self, event):
        import pyHook
        x, y = event.Position

        if event.Message == pyHook.HookConstants.WM_MOUSEMOVE:
            self.move(x,y)

        elif event.Message == pyHook.HookConstants.WM_LBUTTONDOWN:
            self.click(x, y, 1, True)
        elif event.Message == pyHook.HookConstants.WM_LBUTTONUP:
            self.click(x, y, 1, False)
        elif event.Message == pyHook.HookConstants.WM_RBUTTONDOWN:
            self.click(x, y, 2, True)
        elif event.Message == pyHook.HookConstants.WM_RBUTTONUP:
            self.click(x, y, 2, False)
        elif event.Message == pyHook.HookConstants.WM_MBUTTONDOWN:
            self.click(x, y, 3, True)
        elif event.Message == pyHook.HookConstants.WM_MBUTTONUP:
            self.click(x, y, 3, False)
            
        elif event.Message == pyHook.HookConstants.WM_MOUSEWHEEL:
            # event.Wheel is -1 when scrolling down, 1 when scrolling up
            self.scroll(x,y,event.Wheel)
        
        return not self.capture

########NEW FILE########
__FILENAME__ = x11
#Copyright 2013 Paul Barton
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from Xlib.display import Display
from Xlib import X
from Xlib.ext.xtest import fake_input
from Xlib.ext import record
from Xlib.protocol import rq

from .base import PyMouseMeta, PyMouseEventMeta, ScrollSupportError

button_ids = [None, 1, 3, 2, 4, 5, 6, 7]


class PyMouse(PyMouseMeta):
    def __init__(self, display=None):
        PyMouseMeta.__init__(self)
        self.display = Display(display)
        self.display2 = Display(display)

    def press(self, x, y, button=1):
        self.move(x, y)
        fake_input(self.display, X.ButtonPress, button_ids[button])
        self.display.sync()

    def release(self, x, y, button=1):
        self.move(x, y)
        fake_input(self.display, X.ButtonRelease, button_ids[button])
        self.display.sync()

    def scroll(self, vertical=None, horizontal=None, depth=None):
        #Xlib supports only vertical and horizontal scrolling
        if depth is not None:
            raise ScrollSupportError('PyMouse cannot support depth-scrolling \
in X11. This feature is only available on Mac.')

        #Execute vertical then horizontal scrolling events
        if vertical is not None:
            vertical = int(vertical)
            if vertical == 0:  # Do nothing with 0 distance
                pass
            elif vertical > 0:  # Scroll up if positive
                self.click(*self.position(), button=4, n=vertical)
            else:  # Scroll down if negative
                self.click(*self.position(), button=5, n=abs(vertical))
        if horizontal is not None:
            horizontal = int(horizontal)
            if horizontal == 0:  # Do nothing with 0 distance
                pass
            elif horizontal > 0:  # Scroll right if positive
                self.click(*self.position(), button=7, n=horizontal)
            else:  # Scroll left if negative
                self.click(*self.position(), button=6, n=abs(horizontal))

    def move(self, x, y):
        if (x, y) != self.position():
            fake_input(self.display, X.MotionNotify, x=x, y=y)
            self.display.sync()

    def drag(self, x, y):
        fake_input(self.display, X.ButtonPress, button_ids[1])
        fake_input(self.display, X.MotionNotify, x=x, y=y)
        fake_input(self.display, X.ButtonRelease, button_ids[1])
        self.display.sync()

    def position(self):
        coord = self.display.screen().root.query_pointer()._data
        return coord["root_x"], coord["root_y"]

    def screen_size(self):
        width = self.display.screen().width_in_pixels
        height = self.display.screen().height_in_pixels
        return width, height


class PyMouseEvent(PyMouseEventMeta):
    def __init__(self, capture=False, capture_move=False, display=None):
        PyMouseEventMeta.__init__(self,
                                  capture=capture,
                                  capture_move=capture_move)
        self.display = Display(display)
        self.display2 = Display(display)
        self.ctx = self.display2.record_create_context(
            0,
            [record.AllClients],
            [{
                    'core_requests': (0, 0),
                    'core_replies': (0, 0),
                    'ext_requests': (0, 0, 0, 0),
                    'ext_replies': (0, 0, 0, 0),
                    'delivered_events': (0, 0),
                    'device_events': (X.ButtonPressMask, X.ButtonReleaseMask),
                    'errors': (0, 0),
                    'client_started': False,
                    'client_died': False,
            }])

    def run(self):
        try:
            if self.capture and self.capture_move:
                capturing = X.ButtonPressMask | X.ButtonReleaseMask | X.PointerMotionMask
            elif self.capture:
                capturing = X.ButtonPressMask | X.ButtonReleaseMask
            elif self.capture_move:
                capturing = X.PointerMotionMask
            else:
                capturing = False

            if capturing:
                self.display2.screen().root.grab_pointer(True,
                                                         capturing,
                                                         X.GrabModeAsync,
                                                         X.GrabModeAsync,
                                                         0, 0, X.CurrentTime)
                self.display.screen().root.grab_pointer(True,
                                                         capturing,
                                                         X.GrabModeAsync,
                                                         X.GrabModeAsync,
                                                         0, 0, X.CurrentTime)

            self.display2.record_enable_context(self.ctx, self.handler)
            self.display2.record_free_context(self.ctx)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.state = False
        self.display.flush()
        self.display.record_disable_context(self.ctx)
        self.display.ungrab_pointer(X.CurrentTime)
        self.display2.flush()
        self.display2.record_disable_context(self.ctx)
        self.display2.ungrab_pointer(X.CurrentTime)

    def handler(self, reply):
        data = reply.data
        while len(data):
            event, data = rq.EventField(None).parse_binary_value(data, self.display.display, None, None)

            #In X11, the button numbers are: leftclick=1, middleclick=2,
            #  rightclick=3, scrollup=4, scrolldown=5, scrollleft=6,
            #  scrollright=7
            #  For the purposes of the cross-platform interface of PyMouse, we
            #  invert the button number values of the right and middle buttons
            if event.type == X.ButtonPress:
                self.click(event.root_x, event.root_y, (None, 1, 3, 2, 4, 5, 6, 7)[event.detail], True)
            elif event.type == X.ButtonRelease:
                self.click(event.root_x, event.root_y, (None, 1, 3, 2, 4, 5, 6, 7)[event.detail], False)
            else:
                self.move(event.root_x, event.root_y)

########NEW FILE########
__FILENAME__ = virtual_keystroke_example
#Giant dictionary to hold key name and VK value
VK_CODE = {'backspace':0x08,
           'tab':0x09,
           'clear':0x0C,
           'enter':0x0D,
           'shift':0x10,
           'ctrl':0x11,
           'alt':0x12,
           'pause':0x13,
           'caps_lock':0x14,
           'esc':0x1B,
           'spacebar':0x20,
           'page_up':0x21,
           'page_down':0x22,
           'end':0x23,
           'home':0x24,
           'left_arrow':0x25,
           'up_arrow':0x26,
           'right_arrow':0x27,
           'down_arrow':0x28,
           'select':0x29,
           'print':0x2A,
           'execute':0x2B,
           'print_screen':0x2C,
           'ins':0x2D,
           'del':0x2E,
           'help':0x2F,
           '0':0x30,
           '1':0x31,
           '2':0x32,
           '3':0x33,
           '4':0x34,
           '5':0x35,
           '6':0x36,
           '7':0x37,
           '8':0x38,
           '9':0x39,
           'a':0x41,
           'b':0x42,
           'c':0x43,
           'd':0x44,
           'e':0x45,
           'f':0x46,
           'g':0x47,
           'h':0x48,
           'i':0x49,
           'j':0x4A,
           'k':0x4B,
           'l':0x4C,
           'm':0x4D,
           'n':0x4E,
           'o':0x4F,
           'p':0x50,
           'q':0x51,
           'r':0x52,
           's':0x53,
           't':0x54,
           'u':0x55,
           'v':0x56,
           'w':0x57,
           'x':0x58,
           'y':0x59,
           'z':0x5A,
           'numpad_0':0x60,
           'numpad_1':0x61,
           'numpad_2':0x62,
           'numpad_3':0x63,
           'numpad_4':0x64,
           'numpad_5':0x65,
           'numpad_6':0x66,
           'numpad_7':0x67,
           'numpad_8':0x68,
           'numpad_9':0x69,
           'multiply_key':0x6A,
           'add_key':0x6B,
           'separator_key':0x6C,
           'subtract_key':0x6D,
           'decimal_key':0x6E,
           'divide_key':0x6F,
           'F1':0x70,
           'F2':0x71,
           'F3':0x72,
           'F4':0x73,
           'F5':0x74,
           'F6':0x75,
           'F7':0x76,
           'F8':0x77,
           'F9':0x78,
           'F10':0x79,
           'F11':0x7A,
           'F12':0x7B,
           'F13':0x7C,
           'F14':0x7D,
           'F15':0x7E,
           'F16':0x7F,
           'F17':0x80,
           'F18':0x81,
           'F19':0x82,
           'F20':0x83,
           'F21':0x84,
           'F22':0x85,
           'F23':0x86,
           'F24':0x87,
           'num_lock':0x90,
           'scroll_lock':0x91,
           'left_shift':0xA0,
           'right_shift ':0xA1,
           'left_control':0xA2,
           'right_control':0xA3,
           'left_menu':0xA4,
           'right_menu':0xA5,
           'browser_back':0xA6,
           'browser_forward':0xA7,
           'browser_refresh':0xA8,
           'browser_stop':0xA9,
           'browser_search':0xAA,
           'browser_favorites':0xAB,
           'browser_start_and_home':0xAC,
           'volume_mute':0xAD,
           'volume_Down':0xAE,
           'volume_up':0xAF,
           'next_track':0xB0,
           'previous_track':0xB1,
           'stop_media':0xB2,
           'play/pause_media':0xB3,
           'start_mail':0xB4,
           'select_media':0xB5,
           'start_application_1':0xB6,
           'start_application_2':0xB7,
           'attn_key':0xF6,
           'crsel_key':0xF7,
           'exsel_key':0xF8,
           'play_key':0xFA,
           'zoom_key':0xFB,
           'clear_key':0xFE,
           '+':0xBB,
           ',':0xBC,
           '-':0xBD,
           '.':0xBE,
           '/':0xBF,
           '`':0xC0,
           ';':0xBA,
           '[':0xDB,
           '\\':0xDC,
           ']':0xDD,
           "'":0xDE,
           '`':0xC0}

def press(*args):
    '''
    one press, one release.
    accepts as many arguments as you want. e.g. press('left_arrow', 'a','b').
    '''
    for i in args:
        win32api.keybd_event(VK_CODE[i], 0,0,0)
        time.sleep(.05)
        win32api.keybd_event(VK_CODE[i],0 ,win32con.KEYEVENTF_KEYUP ,0)

def pressAndHold(*args):
    '''
    press and hold. Do NOT release.
    accepts as many arguments as you want.
    e.g. pressAndHold('left_arrow', 'a','b').
    '''
    for i in args:
        win32api.keybd_event(VK_CODE[i], 0,0,0)
        time.sleep(.05)
           
def pressHoldRelease(*args):
    '''
    press and hold passed in strings. Once held, release
    accepts as many arguments as you want.
    e.g. pressAndHold('left_arrow', 'a','b').

    this is useful for issuing shortcut command or shift commands.
    e.g. pressHoldRelease('ctrl', 'alt', 'del'), pressHoldRelease('shift','a')
    '''
    for i in args:
        win32api.keybd_event(VK_CODE[i], 0,0,0)
        time.sleep(.05)
            
    for i in args:
            win32api.keybd_event(VK_CODE[i],0 ,win32con.KEYEVENTF_KEYUP ,0)
            time.sleep(.1)
            
        

def release(*args):
    '''
    release depressed keys
    accepts as many arguments as you want.
    e.g. release('left_arrow', 'a','b').
    '''
    for i in args:
           win32api.keybd_event(VK_CODE[i],0 ,win32con.KEYEVENTF_KEYUP ,0)


def typer(string=None,*args):
##    time.sleep(4)
    for i in string:
        if i == ' ':
            win32api.keybd_event(VK_CODE['spacebar'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['spacebar'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == '!':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['1'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['1'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == '@':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['2'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['2'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == '{':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['['], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['['],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == '?':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['/'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['/'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == ':':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE[';'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE[';'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == '"':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['\''], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['\''],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == '}':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE[']'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE[']'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == '#':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['3'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['3'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == '$':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['4'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['4'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == '%':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['5'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['5'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == '^':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['6'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['6'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == '&':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['7'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['7'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == '*':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['8'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['8'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == '(':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['9'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['9'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == ')':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['0'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['0'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == '_':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['-'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['-'],0 ,win32con.KEYEVENTF_KEYUP ,0)


        elif i == '=':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['+'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['+'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == '~':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['`'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['`'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == '<':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE[','], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE[','],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == '>':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['.'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['.'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'A':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['a'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['a'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'B':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['b'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['b'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'C':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['c'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['c'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'D':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['d'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['d'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'E':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['e'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['e'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'F':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['f'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['f'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'G':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['g'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['g'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'H':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['h'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['h'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'I':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['i'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['i'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'J':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['j'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['j'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'K':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['k'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['k'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'L':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['l'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['l'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'M':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['m'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['m'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'N':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['n'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['n'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'O':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['o'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['o'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'P':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['p'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['p'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'Q':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['q'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['q'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'R':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['r'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['r'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'S':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['s'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['s'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'T':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['t'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['t'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'U':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['u'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['u'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'V':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['v'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['v'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'W':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['w'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['w'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'X':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['x'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['x'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'Y':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['y'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['y'],0 ,win32con.KEYEVENTF_KEYUP ,0)

        elif i == 'Z':
            win32api.keybd_event(VK_CODE['left_shift'], 0,0,0)
            win32api.keybd_event(VK_CODE['z'], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE['left_shift'],0 ,win32con.KEYEVENTF_KEYUP ,0)
            win32api.keybd_event(VK_CODE['z'],0 ,win32con.KEYEVENTF_KEYUP ,0)

    
        else:    
            win32api.keybd_event(VK_CODE[i], 0,0,0)
            time.sleep(.05)
            win32api.keybd_event(VK_CODE[i],0 ,win32con.KEYEVENTF_KEYUP ,0)





########NEW FILE########
__FILENAME__ = winex
import ctypes

LONG = ctypes.c_long
DWORD = ctypes.c_ulong
ULONG_PTR = ctypes.POINTER(DWORD)
WORD = ctypes.c_ushort

class MOUSEINPUT(ctypes.Structure):
    _fields_ = (('dx', LONG),
                ('dy', LONG),
                ('mouseData', DWORD),
                ('dwFlags', DWORD),
                ('time', DWORD),
                ('dwExtraInfo', ULONG_PTR))

class KEYBDINPUT(ctypes.Structure):
    _fields_ = (('wVk', WORD),
                ('wScan', WORD),
                ('dwFlags', DWORD),
                ('time', DWORD),
                ('dwExtraInfo', ULONG_PTR))

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (('uMsg', DWORD),
                ('wParamL', WORD),
                ('wParamH', WORD))

class _INPUTunion(ctypes.Union):
    _fields_ = (('mi', MOUSEINPUT),
                ('ki', KEYBDINPUT),
                ('hi', HARDWAREINPUT))

class INPUT(ctypes.Structure):
    _fields_ = (('type', DWORD),
                ('union', _INPUTunion))

def SendInput(*inputs):
    nInputs = len(inputs)
    LPINPUT = INPUT * nInputs
    pInputs = LPINPUT(*inputs)
    cbSize = ctypes.c_int(ctypes.sizeof(INPUT))
    return ctypes.windll.user32.SendInput(nInputs, pInputs, cbSize)

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARD = 2

def Input(structure):
    if isinstance(structure, MOUSEINPUT):
        return INPUT(INPUT_MOUSE, _INPUTunion(mi=structure))
    if isinstance(structure, KEYBDINPUT):
        return INPUT(INPUT_KEYBOARD, _INPUTunion(ki=structure))
    if isinstance(structure, HARDWAREINPUT):
        return INPUT(INPUT_HARDWARE, _INPUTunion(hi=structure))
    raise TypeError('Cannot create INPUT structure!')

WHEEL_DELTA = 120
XBUTTON1 = 0x0001
XBUTTON2 = 0x0002
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_HWHEEL = 0x01000
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_MOVE_NOCOALESCE = 0x2000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100

def MouseInput(flags, x, y, data):
    return MOUSEINPUT(x, y, data, flags, 0, None)

VK_LBUTTON = 0x01               # Left mouse button
VK_RBUTTON = 0x02               # Right mouse button
VK_CANCEL = 0x03                # Control-break processing
VK_MBUTTON = 0x04               # Middle mouse button (three-button mouse)
VK_XBUTTON1 = 0x05              # X1 mouse button
VK_XBUTTON2 = 0x06              # X2 mouse button
VK_BACK = 0x08                  # BACKSPACE key
VK_TAB = 0x09                   # TAB key
VK_CLEAR = 0x0C                 # CLEAR key
VK_RETURN = 0x0D                # ENTER key
VK_SHIFT = 0x10                 # SHIFT key
VK_CONTROL = 0x11               # CTRL key
VK_MENU = 0x12                  # ALT key
VK_PAUSE = 0x13                 # PAUSE key
VK_CAPITAL = 0x14               # CAPS LOCK key
VK_KANA = 0x15                  # IME Kana mode
VK_HANGUL = 0x15                # IME Hangul mode
VK_JUNJA = 0x17                 # IME Junja mode
VK_FINAL = 0x18                 # IME final mode
VK_HANJA = 0x19                 # IME Hanja mode
VK_KANJI = 0x19                 # IME Kanji mode
VK_ESCAPE = 0x1B                # ESC key
VK_CONVERT = 0x1C               # IME convert
VK_NONCONVERT = 0x1D            # IME nonconvert
VK_ACCEPT = 0x1E                # IME accept
VK_MODECHANGE = 0x1F            # IME mode change request
VK_SPACE = 0x20                 # SPACEBAR
VK_PRIOR = 0x21                 # PAGE UP key
VK_NEXT = 0x22                  # PAGE DOWN key
VK_END = 0x23                   # END key
VK_HOME = 0x24                  # HOME key
VK_LEFT = 0x25                  # LEFT ARROW key
VK_UP = 0x26                    # UP ARROW key
VK_RIGHT = 0x27                 # RIGHT ARROW key
VK_DOWN = 0x28                  # DOWN ARROW key
VK_SELECT = 0x29                # SELECT key
VK_PRINT = 0x2A                 # PRINT key
VK_EXECUTE = 0x2B               # EXECUTE key
VK_SNAPSHOT = 0x2C              # PRINT SCREEN key
VK_INSERT = 0x2D                # INS key
VK_DELETE = 0x2E                # DEL key
VK_HELP = 0x2F                  # HELP key
VK_LWIN = 0x5B                  # Left Windows key (Natural keyboard)
VK_RWIN = 0x5C                  # Right Windows key (Natural keyboard)
VK_APPS = 0x5D                  # Applications key (Natural keyboard)
VK_SLEEP = 0x5F                 # Computer Sleep key
VK_NUMPAD0 = 0x60               # Numeric keypad 0 key
VK_NUMPAD1 = 0x61               # Numeric keypad 1 key
VK_NUMPAD2 = 0x62               # Numeric keypad 2 key
VK_NUMPAD3 = 0x63               # Numeric keypad 3 key
VK_NUMPAD4 = 0x64               # Numeric keypad 4 key
VK_NUMPAD5 = 0x65               # Numeric keypad 5 key
VK_NUMPAD6 = 0x66               # Numeric keypad 6 key
VK_NUMPAD7 = 0x67               # Numeric keypad 7 key
VK_NUMPAD8 = 0x68               # Numeric keypad 8 key
VK_NUMPAD9 = 0x69               # Numeric keypad 9 key
VK_MULTIPLY = 0x6A              # Multiply key
VK_ADD = 0x6B                   # Add key
VK_SEPARATOR = 0x6C             # Separator key
VK_SUBTRACT = 0x6D              # Subtract key
VK_DECIMAL = 0x6E               # Decimal key
VK_DIVIDE = 0x6F                # Divide key
VK_F1 = 0x70                    # F1 key
VK_F2 = 0x71                    # F2 key
VK_F3 = 0x72                    # F3 key
VK_F4 = 0x73                    # F4 key
VK_F5 = 0x74                    # F5 key
VK_F6 = 0x75                    # F6 key
VK_F7 = 0x76                    # F7 key
VK_F8 = 0x77                    # F8 key
VK_F9 = 0x78                    # F9 key
VK_F10 = 0x79                   # F10 key
VK_F11 = 0x7A                   # F11 key
VK_F12 = 0x7B                   # F12 key
VK_F13 = 0x7C                   # F13 key
VK_F14 = 0x7D                   # F14 key
VK_F15 = 0x7E                   # F15 key
VK_F16 = 0x7F                   # F16 key
VK_F17 = 0x80                   # F17 key
VK_F18 = 0x81                   # F18 key
VK_F19 = 0x82                   # F19 key
VK_F20 = 0x83                   # F20 key
VK_F21 = 0x84                   # F21 key
VK_F22 = 0x85                   # F22 key
VK_F23 = 0x86                   # F23 key
VK_F24 = 0x87                   # F24 key
VK_NUMLOCK = 0x90               # NUM LOCK key
VK_SCROLL = 0x91                # SCROLL LOCK key
VK_LSHIFT = 0xA0                # Left SHIFT key
VK_RSHIFT = 0xA1                # Right SHIFT key
VK_LCONTROL = 0xA2              # Left CONTROL key
VK_RCONTROL = 0xA3              # Right CONTROL key
VK_LMENU = 0xA4                 # Left MENU key
VK_RMENU = 0xA5                 # Right MENU key
VK_BROWSER_BACK = 0xA6          # Browser Back key
VK_BROWSER_FORWARD = 0xA7       # Browser Forward key
VK_BROWSER_REFRESH = 0xA8       # Browser Refresh key
VK_BROWSER_STOP = 0xA9          # Browser Stop key
VK_BROWSER_SEARCH = 0xAA        # Browser Search key
VK_BROWSER_FAVORITES = 0xAB     # Browser Favorites key
VK_BROWSER_HOME = 0xAC          # Browser Start and Home key
VK_VOLUME_MUTE = 0xAD           # Volume Mute key
VK_VOLUME_DOWN = 0xAE           # Volume Down key
VK_VOLUME_UP = 0xAF             # Volume Up key
VK_MEDIA_NEXT_TRACK = 0xB0      # Next Track key
VK_MEDIA_PREV_TRACK = 0xB1      # Previous Track key
VK_MEDIA_STOP = 0xB2            # Stop Media key
VK_MEDIA_PLAY_PAUSE = 0xB3      # Play/Pause Media key
VK_LAUNCH_MAIL = 0xB4           # Start Mail key
VK_LAUNCH_MEDIA_SELECT = 0xB5   # Select Media key
VK_LAUNCH_APP1 = 0xB6           # Start Application 1 key
VK_LAUNCH_APP2 = 0xB7           # Start Application 2 key
VK_OEM_1 = 0xBA                 # Used for miscellaneous characters; it can vary by keyboard.
                                # For the US standard keyboard, the ';:' key
VK_OEM_PLUS = 0xBB              # For any country/region, the '+' key
VK_OEM_COMMA = 0xBC             # For any country/region, the ',' key
VK_OEM_MINUS = 0xBD             # For any country/region, the '-' key
VK_OEM_PERIOD = 0xBE            # For any country/region, the '.' key
VK_OEM_2 = 0xBF                 # Used for miscellaneous characters; it can vary by keyboard.
                                # For the US standard keyboard, the '/?' key
VK_OEM_3 = 0xC0                 # Used for miscellaneous characters; it can vary by keyboard.
                                # For the US standard keyboard, the '`~' key
VK_OEM_4 = 0xDB                 # Used for miscellaneous characters; it can vary by keyboard.
                                # For the US standard keyboard, the '[{' key
VK_OEM_5 = 0xDC                 # Used for miscellaneous characters; it can vary by keyboard.
                                # For the US standard keyboard, the '\|' key
VK_OEM_6 = 0xDD                 # Used for miscellaneous characters; it can vary by keyboard.
                                # For the US standard keyboard, the ']}' key
VK_OEM_7 = 0xDE                 # Used for miscellaneous characters; it can vary by keyboard.
                                # For the US standard keyboard, the 'single-quote/double-quote' key
VK_OEM_8 = 0xDF                 # Used for miscellaneous characters; it can vary by keyboard.
VK_OEM_102 = 0xE2               # Either the angle bracket key or the backslash key on the RT 102-key keyboard
VK_PROCESSKEY = 0xE5            # IME PROCESS key
VK_PACKET = 0xE7                # Used to pass Unicode characters as if they were keystrokes. The VK_PACKET key is the low word of a 32-bit Virtual Key value used for non-keyboard input methods. For more information, see Remark in KEYBDINPUT, SendInput, WM_KEYDOWN, and WM_KEYUP
VK_ATTN = 0xF6                  # Attn key
VK_CRSEL = 0xF7                 # CrSel key
VK_EXSEL = 0xF8                 # ExSel key
VK_EREOF = 0xF9                 # Erase EOF key
VK_PLAY = 0xFA                  # Play key
VK_ZOOM = 0xFB                  # Zoom key
VK_PA1 = 0xFD                   # PA1 key
VK_OEM_CLEAR = 0xFE             # Clear key

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_UNICODE = 0x0004

KEY_0 = 0x30
KEY_1 = 0x31
KEY_2 = 0x32
KEY_3 = 0x33
KEY_4 = 0x34
KEY_5 = 0x35
KEY_6 = 0x36
KEY_7 = 0x37
KEY_8 = 0x38
KEY_9 = 0x39
KEY_A = 0x41
KEY_B = 0x42
KEY_C = 0x43
KEY_D = 0x44
KEY_E = 0x45
KEY_F = 0x46
KEY_G = 0x47
KEY_H = 0x48
KEY_I = 0x49
KEY_J = 0x4A
KEY_K = 0x4B
KEY_L = 0x4C
KEY_M = 0x4D
KEY_N = 0x4E
KEY_O = 0x4F
KEY_P = 0x50
KEY_Q = 0x51
KEY_R = 0x52
KEY_S = 0x53
KEY_T = 0x54
KEY_U = 0x55
KEY_V = 0x56
KEY_W = 0x57
KEY_X = 0x58
KEY_Y = 0x59
KEY_Z = 0x5A

def KeybdInput(code, flags):
    return KEYBDINPUT(code, code, flags, 0, None)

def HardwareInput(message, parameter):
    return HARDWAREINPUT(message & 0xFFFFFFFF,
                         parameter & 0xFFFF,
                         parameter >> 16 & 0xFFFF)

def Mouse(flags, x=0, y=0, data=0):
    return Input(MouseInput(flags, x, y, data))

def Keyboard(code, flags=0):
    return Input(KeybdInput(code, flags))

def Hardware(message, parameter=0):
    return Input(HardwareInput(message, parameter))

################################################################################

import string

UPPER = frozenset('~!@#$%^&*()_+QWERTYUIOP{}|ASDFGHJKL:"ZXCVBNM<>?')
LOWER = frozenset("`1234567890-=qwertyuiop[]\\asdfghjkl;'zxcvbnm,./")
ORDER = string.ascii_letters + string.digits + ' \b\r\t'
ALTER = dict(zip('!@#$%^&*()', '1234567890'))
OTHER = {'`': VK_OEM_3,
         '~': VK_OEM_3,
         '-': VK_OEM_MINUS,
         '_': VK_OEM_MINUS,
         '=': VK_OEM_PLUS,
         '+': VK_OEM_PLUS,
         '[': VK_OEM_4,
         '{': VK_OEM_4,
         ']': VK_OEM_6,
         '}': VK_OEM_6,
         '\\': VK_OEM_5,
         '|': VK_OEM_5,
         ';': VK_OEM_1,
         ':': VK_OEM_1,
         "'": VK_OEM_7,
         '"': VK_OEM_7,
         ',': VK_OEM_COMMA,
         '<': VK_OEM_COMMA,
         '.': VK_OEM_PERIOD,
         '>': VK_OEM_PERIOD,
         '/': VK_OEM_2,
         '?': VK_OEM_2}

def keyboard_stream(string):
    mode = False
    for character in string.replace('\r\n', '\r').replace('\n', '\r'):
        if mode and character in LOWER or not mode and character in UPPER:
            yield Keyboard(VK_SHIFT, mode and KEYEVENTF_KEYUP)
            mode = not mode
        character = ALTER.get(character, character)
        if character in ORDER:
            code = ord(character.upper())
        elif character in OTHER:
            code = OTHER[character]
        else:
            continue
            raise ValueError('String is not understood!')
        yield Keyboard(code)
        yield Keyboard(code, KEYEVENTF_KEYUP)
    if mode:
        yield Keyboard(VK_SHIFT, KEYEVENTF_KEYUP)

################################################################################

import time, sys

def main():
    time.sleep(5)
    for event in keyboard_stream('o2E^uXh#:SHn&HQ+t]YF'):
        SendInput(event)
        time.sleep(0.1)

##if __name__ == '__main__':
##    main()

def switch_program():
    SendInput(Keyboard(VK_MENU), Keyboard(VK_TAB))
    time.sleep(0.2)
    SendInput(Keyboard(VK_TAB, KEYEVENTF_KEYUP),
              Keyboard(VK_MENU, KEYEVENTF_KEYUP))
    time.sleep(0.2)

def select_line():
    SendInput(Keyboard(VK_SHIFT, KEYEVENTF_EXTENDEDKEY),
              Keyboard(VK_END, KEYEVENTF_EXTENDEDKEY))
    time.sleep(0.2)
    SendInput(Keyboard(VK_SHIFT, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP),
              Keyboard(VK_END, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP))
    time.sleep(0.2)

def copy_line():
    SendInput(Keyboard(VK_CONTROL), Keyboard(KEY_C))
    time.sleep(0.2)
    SendInput(Keyboard(VK_CONTROL, KEYEVENTF_KEYUP),
              Keyboard(KEY_C, KEYEVENTF_KEYUP))
    time.sleep(0.2)

def next_line():
    SendInput(Keyboard(VK_HOME), Keyboard(VK_DOWN))
    time.sleep(0.2)
    SendInput(Keyboard(VK_HOME, KEYEVENTF_KEYUP),
              Keyboard(VK_DOWN, KEYEVENTF_KEYUP))
    time.sleep(0.2)

def prepare_text():
    # Open Text
    SendInput(Keyboard(KEY_M))
    time.sleep(0.2)
    SendInput(Keyboard(KEY_M, KEYEVENTF_KEYUP))
    time.sleep(0.2)
    # Goto Area
    SendInput(Keyboard(VK_TAB))
    time.sleep(0.2)
    SendInput(Keyboard(VK_TAB, KEYEVENTF_KEYUP))
    time.sleep(0.2)
    # Paste Message
    SendInput(Keyboard(VK_CONTROL), Keyboard(KEY_V))
    time.sleep(0.2)
    SendInput(Keyboard(VK_CONTROL, KEYEVENTF_KEYUP),
              Keyboard(KEY_V, KEYEVENTF_KEYUP))
    time.sleep(0.2)
    # Goto Button
    SendInput(Keyboard(VK_TAB))
    time.sleep(0.2)
    SendInput(Keyboard(VK_TAB, KEYEVENTF_KEYUP))
    time.sleep(0.2)

def send_one_message():
    select_line()
    copy_line()
    next_line()
    switch_program()
    prepare_text()
    # Send Message
    SendInput(Keyboard(VK_RETURN))
    time.sleep(0.2)
    SendInput(Keyboard(VK_RETURN, KEYEVENTF_KEYUP))
    time.sleep(10)
    switch_program()

def send_messages(total):
    time.sleep(10)
    for _ in range(total):
        send_one_message()
########NEW FILE########
__FILENAME__ = basic
#Copyright 2013 Paul Barton
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pymouse import PyMouse
import random, time
try:
    from pymouse import PyMouseEvent

    class event(PyMouseEvent):
        def move(self, x, y):
            print "Mouse moved to", x, y

        def click(self, x, y, button, press):
            if press:
                print "Mouse pressed at", x, y, "with button", button
            else:
                print "Mouse released at", x, y, "with button", button

    e = event()
    #e.capture = True
    e.start()

except ImportError:
    print "Mouse events are not yet supported on your platform"

m = PyMouse()
try:
	size = m.screen_size()
	print "size: %s" % (str(size))

	pos = (random.randint(0, size[0]), random.randint(0, size[1]))
except:
	pos = (random.randint(0, 250), random.randint(0, 250))

print "Position: %s" % (str(pos))

m.move(pos[0], pos[1])

time.sleep(2)

m.click(pos[0], pos[1], 1)

time.sleep(2)

m.click(pos[0], pos[1], 2)

time.sleep(2)

m.click(pos[0], pos[1], 3)

try:
    e.stop()
except:
    pass

########NEW FILE########
__FILENAME__ = test_unix
'''
Tested on linux.

install:  Xvfb, Xephyr, PyVirtualDisplay, nose

on Ubuntu:

    sudo apt-get install python-nose
    sudo apt-get install xvfb 
    sudo apt-get install xserver-xephyr
    sudo apt-get install python-setuptools
    sudo easy_install PyVirtualDisplay

to start:

    nosetests -v
'''

from nose.tools import eq_
from pymouse import PyMouse, PyMouseEvent
from pyvirtualdisplay import Display
from unittest import TestCase
import time

# 0 -> Xvfb
# 1 -> Xephyr
VISIBLE = 0

screen_sizes = [
              (10, 20),
              (100, 200),
              (765, 666),
              ]
positions = [
              (0, 5),
              (0, 0),
              (10, 20),
              (-10, -20),
              (5, 0),
              (2222, 2222),
              (9, 19),
              ]


class Event(PyMouseEvent):
    def move(self, x, y):
        print "Mouse moved to", x, y
        self.pos = (x, y)

    def click(self, x, y, button, press):
        if press:
            print "Mouse pressed at", x, y, "with button", button
        else:
            print "Mouse released at", x, y, "with button", button

def expect_pos(pos, size):
    def expect(x, m):
        x = max(0, x)
        x = min(m - 1, x)
        return x
    expected_pos = (expect(pos[0], size[0]), expect(pos[1], size[1]))
    return expected_pos

class Test(TestCase):
    def test_size(self):
        for size in screen_sizes:
            with Display(visible=VISIBLE, size=size):
                mouse = PyMouse()
                eq_(size, mouse.screen_size())

    def test_move(self):
        for size in screen_sizes:
            with Display(visible=VISIBLE, size=size):
                mouse = PyMouse()
                for p in positions:
                    mouse.move(*p)
                    eq_(expect_pos(p, size), mouse.position())

    def test_event(self):
        for size in screen_sizes:
            with Display(visible=VISIBLE, size=size):
                time.sleep(3)  # TODO: how long should we wait?
                mouse = PyMouse()
                event = Event()
                event.start()
                for p in positions:
                    event.pos = None
                    mouse.move(*p)
                    time.sleep(0.1)  # TODO: how long should we wait?
                    print 'check ', expect_pos(p, size), '=', event.pos
                    eq_(expect_pos(p, size), event.pos)
                event.stop()                

########NEW FILE########
