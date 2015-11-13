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
# -*- coding: iso-8859-1 -*-

#   Copyright 2010 Pepijn de Vos
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""The goal of PyMouse is to have a cross-platform way to control the mouse.
PyMouse should work on Windows, Mac and any Unix that has xlib.

See http://github.com/pepijndevos/PyMouse for more information.
"""

from threading import Thread

class PyMouseMeta(object):

    def press(self, x, y, button = 1):
        """Press the mouse on a givven x, y and button.
        Button is defined as 1 = left, 2 = right, 3 = middle."""

        raise NotImplementedError

    def release(self, x, y, button = 1):
        """Release the mouse on a givven x, y and button.
        Button is defined as 1 = left, 2 = right, 3 = middle."""

        raise NotImplementedError

    def click(self, x, y, button = 1, n = 1):
        """Click a mouse button n times on a given x, y.
        Button is defined as 1 = left, 2 = right, 3 = middle.
        """

        for i in range(n):
            self.press(x, y, button)
            self.release(x, y, button)
 
    def move(self, x, y):
        """Move the mouse to a givven x and y"""

        raise NotImplementedError

    def position(self):
        """Get the current mouse position in pixels.
        Returns a tuple of 2 integers"""

        raise NotImplementedError

    def screen_size(self):
        """Get the current screen size in pixels.
        Returns a tuple of 2 integers"""

        raise NotImplementedError

class PyMouseEventMeta(Thread):
    def __init__(self, capture=False, captureMove=False):
        Thread.__init__(self)
        self.daemon = True
        self.capture = capture
        self.captureMove = captureMove
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
# -*- coding: iso-8859-1 -*-

#   Copyright 2010 Pepijn de Vos
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from java.awt import Robot, Toolkit
from java.awt.event import InputEvent
from java.awt.MouseInfo import getPointerInfo
from base import PyMouseMeta

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
# -*- coding: iso-8859-1 -*-

#   Copyright 2010 Pepijn de Vos
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from Quartz import *
from AppKit import NSEvent
from base import PyMouseMeta, PyMouseEventMeta

pressID = [None, kCGEventLeftMouseDown, kCGEventRightMouseDown, kCGEventOtherMouseDown]
releaseID = [None, kCGEventLeftMouseUp, kCGEventRightMouseUp, kCGEventOtherMouseUp]

class PyMouse(PyMouseMeta):
    def press(self, x, y, button = 1):
        event = CGEventCreateMouseEvent(None, pressID[button], (x, y), button - 1)
        CGEventPost(kCGHIDEventTap, event)

    def release(self, x, y, button = 1):
        event = CGEventCreateMouseEvent(None, releaseID[button], (x, y), button - 1)
        CGEventPost(kCGHIDEventTap, event)

    def move(self, x, y):
        move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, (x, y), 0)
        CGEventPost(kCGHIDEventTap, move)
        

    def position(self):
        loc = NSEvent.mouseLocation()
        return loc.x, CGDisplayPixelsHigh(0) - loc.y

    def screen_size(self):
        return CGDisplayPixelsWide(0), CGDisplayPixelsHigh(0)

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
__FILENAME__ = unix
# -*- coding: iso-8859-1 -*-

#   Copyright 2010 Pepijn de Vos
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from Xlib.display import Display
from Xlib import X
from Xlib.ext.xtest import fake_input
from Xlib.ext import record
from Xlib.protocol import rq

from base import PyMouseMeta, PyMouseEventMeta


class PyMouse(PyMouseMeta):
    def __init__(self, display=None):
        PyMouseMeta.__init__(self)
        self.display = Display(display)
        self.display2 = Display(display)

    def press(self, x, y, button = 1):
        self.move(x, y)
        fake_input(self.display, X.ButtonPress, [None, 1, 3, 2, 4, 5][button])
        self.display.sync()

    def release(self, x, y, button = 1):
        self.move(x, y)
        fake_input(self.display, X.ButtonRelease, [None, 1, 3, 2, 4, 5][button])
        self.display.sync()

    def move(self, x, y):
        fake_input(self.display, X.MotionNotify, x=x, y=y)
        self.display.sync()

    def position(self):
        coord = self.display.screen().root.query_pointer()._data
        return coord["root_x"], coord["root_y"]

    def screen_size(self):
        width = self.display.screen().width_in_pixels
        height = self.display.screen().height_in_pixels
        return width, height

class PyMouseEvent(PyMouseEventMeta):
    def __init__(self, display=None):
        PyMouseEventMeta.__init__(self)
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
        if self.capture:
            self.display2.screen().root.grab_pointer(True, X.ButtonPressMask | X.ButtonReleaseMask, X.GrabModeAsync, X.GrabModeAsync, 0, 0, X.CurrentTime)

        self.display2.record_enable_context(self.ctx, self.handler)
        self.display2.record_free_context(self.ctx)

    def stop(self):
        self.display.record_disable_context(self.ctx)
        self.display.ungrab_pointer(X.CurrentTime)
        self.display.flush()
        self.display2.record_disable_context(self.ctx)
        self.display2.ungrab_pointer(X.CurrentTime)
        self.display2.flush()

    def handler(self, reply):
        data = reply.data
        while len(data):
            event, data = rq.EventField(None).parse_binary_value(data, self.display.display, None, None)

            if event.type == X.ButtonPress:
                self.click(event.root_x, event.root_y, (None, 1, 3, 2, 3, 3, 3)[event.detail], True)
            elif event.type == X.ButtonRelease:
                self.click(event.root_x, event.root_y, (None, 1, 3, 2, 3, 3, 3)[event.detail], False)
            else:
                self.move(event.root_x, event.root_y)



########NEW FILE########
__FILENAME__ = windows
# -*- coding: iso-8859-1 -*-

#   Copyright 2010 Pepijn de Vos
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from ctypes import *
import win32api,win32con
from base import PyMouseMeta, PyMouseEventMeta
import pythoncom, pyHook
from time import sleep

class POINT(Structure):
    _fields_ = [("x", c_ulong),
                ("y", c_ulong)]

class PyMouse(PyMouseMeta):
    """MOUSEEVENTF_(button and action) constants 
    are defined at win32con, buttonAction is that value"""
    def press(self, x, y, button = 1):
        buttonAction = 2**((2*button)-1)
        self.move(x,y)
        win32api.mouse_event(buttonAction, x, y)
     
    def release(self, x, y, button = 1):
        buttonAction = 2**((2*button))
        self.move(x,y)
        win32api.mouse_event(buttonAction, x, y)

    def move(self, x, y):
        windll.user32.SetCursorPos(x, y)

    def position(self):
        pt = POINT()
        windll.user32.GetCursorPos(byref(pt))
        return pt.x, pt.y

    def screen_size(self):
        width = windll.user32.GetSystemMetrics(0)
        height = windll.user32.GetSystemMetrics(1)
        return width, height

class PyMouseEvent(PyMouseEventMeta):
    def __init__(self):
        PyMouseEventMeta.__init__(self)
        self.hm = pyHook.HookManager()

    def run(self):
        self.hm.MouseAllButtons = self._click
        self.hm.MouseMove = self._move
        self.hm.HookMouse()
        while self.state:
            sleep(0.01)
            pythoncom.PumpWaitingMessages()

    def stop(self):
        self.hm.UnhookMouse()
        self.state = False

    def _click(self, event):
        x,y = event.Position

        if event.Message == pyHook.HookConstants.WM_LBUTTONDOWN:
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
        return not self.capture

    def _move(self, event):
        x,y = event.Position
        self.move(x, y)
        return not self.captureMove

########NEW FILE########
__FILENAME__ = basic
# -*- coding: iso-8859-1 -*-

#   Copyright 2010 Pepijn de Vos
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

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
