__FILENAME__ = console_client
import json
import socket
import zlib


class RemoteError(Exception):
    def __init__(self, resp):
        super(RemoteError, self).__init__()
        self._resp = resp

    def __unicode__(self):
        return unicode(self._resp)

    def __str__(self):
        return str(self._resp)

UDP_IP="127.0.0.1"
RECV_UDP_PORT=8828
SEND_UDP_PORT=8829

class ConsoleClient(object):

    def __init__(self, host, port): 
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((UDP_IP, SEND_UDP_PORT))
        self.is_running = True 

    def _request(self, cmd, *args, **kwds):
        try:
            req = zlib.compress(json.dumps({"command": cmd, "args": args, "kwds": kwds}))
            self._sock.sendto(req, (UDP_IP, RECV_UDP_PORT))
            res = self._sock.recv(2**15)
            resp = json.loads(zlib.decompress(res))
            if resp["status"] != "ok":
                raise RemoteError(resp)
            return resp["result"]
        except socket.error:
            self.is_running = False
            return None

    def __getattr__(self, name):
        """Automatically return procedure used to invokek remote methods"""
        from functools import partial
        proc = partial(self._request, name)
        setattr(self, name, proc) # cache! 
        return proc


if __name__ == "__main__":
    cli = ConsoleClient("localhost", 8828)
    raw_input()
########NEW FILE########
__FILENAME__ = console_server
import win32api
import win32pipe
import win32console
import win32process
import win32con
import time
import win32event
import win32job

Coord = win32console.PyCOORDType
SmallRect = win32console.PySMALL_RECTType

MAX_BUFFER_WIDTH = 160
MAX_BUFFER_HEIGHT = 100

PYTHON_PID = win32process.GetCurrentProcessId()

# import signal
# import sys
# def signal_handler(signal, handler):
#     print("Signal")
# signal.signal(signal.SIGINT, signal_handler)
# def win32error(error):
#     print("WIn32", error)
#     return False


class ConsoleServer(object):

    def __init__(self):
        self._last_lines = {}
        self._last_colors = {}

        win32console.FreeConsole()
        win32console.AllocConsole()
        #self._job = win32job.CreateJobObject(None, str(time.time())) 
        flags = win32process.CREATE_SUSPENDED | win32process.NORMAL_PRIORITY_CLASS | win32process.CREATE_NEW_PROCESS_GROUP | win32process.CREATE_UNICODE_ENVIRONMENT 
        si = win32process.STARTUPINFO()
        si.dwFlags |= win32con.STARTF_USESHOWWINDOW
        (self._handle, self._thandle, self._pid, i2) = win32process.CreateProcess(None, "cmd.exe", None, None, 0, flags, None, '.', si)
        time.sleep(0.2)
        self._con_out = win32console.GetStdHandle(win32console.STD_OUTPUT_HANDLE)
        self._con_in = win32console.GetStdHandle(win32console.STD_INPUT_HANDLE)
        #win32job.AssignProcessToJobObject(self._job, self._handle)
        win32process.ResumeThread(self._thandle)

    def set_window_size(self, width, height):
        window_size = SmallRect()
        window_size.Right = 1
        window_size.Bottom = 1
        self._con_out.SetConsoleWindowInfo(True, window_size)
        time.sleep(0.1)

        req_width = min(MAX_BUFFER_WIDTH, width)
        req_height = min(MAX_BUFFER_HEIGHT, height)
        window_size = SmallRect()
        window_size.Right = req_width - 1
        window_size.Bottom = req_height - 1
        self.set_screen_buffer_size(req_width, req_height)
        time.sleep(0.1)

        self._con_out.SetConsoleWindowInfo(True, window_size)

    def set_screen_buffer_size(self, width, height):
        self._con_out.SetConsoleScreenBufferSize(Coord(width, height))

    def terminate_process(self):
        #return win32job.TerminateJobObject(self.job, 1) 
        return win32process.TerminateProcess(self._handle, 0)

    def write_console_input(self, codes):
        self._con_in.WriteConsoleInput(codes)

    def _input_record(self, key, **kwds):
        from win32_keymap import make_input_key
        return make_input_key(key, **kwds)

    def send_keypress(self, key, **kwds):
        self.write_console_input([self._input_record(key, **kwds)])

    def send_ctrl_c(self):
        # ctrl_break for now, it seems I am unable to control
        # ctrl_c correctly, it either does nopthing or kills 
        # controling python process as well
        #win32console.GenerateConsoleCtrlEvent(win32console.CTRL_C_EVENT, self._pid)
        win32console.GenerateConsoleCtrlEvent(win32console.CTRL_BREAK_EVENT, self._pid)

    def send_click(self, row, col, button=1, count=1):
        inputs = []

        mc = win32console.PyINPUT_RECORDType(win32console.MOUSE_EVENT)
        mc.MousePosition = Coord(col, row)
        mc.ButtonState = button #FROM_LEFT_1ST_BUTTON_PRESSED 
        inputs.append(mc)

        if count == 2:
            mc2 = win32console.PyINPUT_RECORDType(win32console.MOUSE_EVENT)
            mc2.MousePosition = Coord(col, row)
            mc2.ButtonState = button
            mc2.EventFlags = 2 #double click            
            inputs.append(mc2)

        mc3 = win32console.PyINPUT_RECORDType(win32console.MOUSE_EVENT)
        mc3.MousePosition = Coord(col, row)
        mc3.ButtonState = 0 #release
        inputs.append(mc3)

        self.write_console_input(inputs)
        

    def read(self, full=False, with_colors=False):
        lines = {}
        colors = {}
        buf_info = self._con_out.GetConsoleScreenBufferInfo()
        size = buf_info['Window']
        idx = 0
        for i in range(size.Top, size.Bottom + 1):
            lines[idx] = self._con_out.ReadConsoleOutputCharacter(size.Right+1 - size.Left, Coord(size.Left, i))
            if with_colors:
                colors[idx] = self._con_out.ReadConsoleOutputAttribute(size.Right+1 - size.Left, Coord(size.Left, i))
            idx += 1
        diff_lines = {}
        diff_colors = {}
        last_lines_keys = self._last_lines.keys()
        last_colors_keys = self._last_colors.keys()
        for k, v in lines.items():
            if k in last_colors_keys and self._last_colors[k] != colors[k]:
                diff_colors[k] = colors[k]
            if k in last_lines_keys and self._last_lines[k] == v:
                continue
            diff_lines[k] = v
            diff_colors[k] = colors[k] # if line is changed, then colors need to be reaplied 
        self._last_lines = lines
        self._last_colors = colors

        cursos_position = buf_info['CursorPosition']
        pos = (cursos_position.X, cursos_position.Y)
        if full:
            return lines, pos, colors
        return diff_lines, pos, diff_colors


import socket

UDP_IP="127.0.0.1"
RECV_UDP_PORT=8828
SEND_UDP_PORT=8829

class UdpConsole(object):
    def __init__(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((UDP_IP, RECV_UDP_PORT))
        self._console = ConsoleServer()

    def run(self):
        while True:
            import json, zlib
            msg = self._sock.recv(2**14)
            response = {"status": "error"}
            try:
                cmd = json.loads(zlib.decompress(msg))
                response["result"] = self.handle_command(cmd)
                response["status"] = "ok"
            except Exception, e:
                response["status"] = "error"
                response["description"] = unicode(e)
            self._sock.sendto(zlib.compress(json.dumps(response)), (UDP_IP, SEND_UDP_PORT))

    def handle_command(self, cmd):
        method = getattr(self._console, cmd["command"])
        return method(*cmd["args"], **cmd["kwds"])


if __name__ == "__main__":
    con = UdpConsole()
    con.run()

########NEW FILE########
__FILENAME__ = win32_keymap
import win32con
import win32console
import ctypes
import winkbd

KEYMAP = {
    "enter": win32con.VK_RETURN,
    "up": win32con.VK_UP,
    "down": win32con.VK_DOWN,
    "left": win32con.VK_LEFT,
    "right": win32con.VK_RIGHT,
    "backspace": win32con.VK_BACK,
    "delete": win32con.VK_DELETE,
    "end": win32con.VK_END,
    "home": win32con.VK_HOME,
    "tab": win32con.VK_TAB,
    "f1": win32con.VK_F1,
    "f2": win32con.VK_F2,
    "f3": win32con.VK_F3,
    "f4": win32con.VK_F4,
    "f5": win32con.VK_F5,
    "f6": win32con.VK_F6,
    "f7": win32con.VK_F7,
    "f8": win32con.VK_F8,
    "f9": win32con.VK_F9,
    "f10": win32con.VK_F10,
    "f11": win32con.VK_F11,
    "f12": win32con.VK_F11,
    "pageup": win32con.VK_PRIOR,
    "pagedown": win32con.VK_NEXT,
    "escape": win32con.VK_ESCAPE
    }

CONTROL_KEY_STATE_FLAGS = {
    "ctrl": win32con.LEFT_CTRL_PRESSED,
    "shift": win32con.SHIFT_PRESSED,
    "alt": win32con.LEFT_ALT_PRESSED,
    "super": 0
}

def flag_value(flags_dict, **kwds):
    """ compute flag value for dictionary with true/false values"""
    flag = 0
    for k,v in kwds.items():
        if v:
            flag |= flags_dict[str(k)]
    return flag

def make_input_key(key, **kwds):
    kc = win32console.PyINPUT_RECORDType(win32console.KEY_EVENT)
    kc.KeyDown = True
    kc.RepeatCount = 1
    kc.ControlKeyState = flag_value(CONTROL_KEY_STATE_FLAGS, **kwds)

    if key in KEYMAP:
        kc.Char = unicode(chr(KEYMAP[key]))
        kc.VirtualKeyCode = KEYMAP[key]
    elif len(key) == 1:
        actual_char = winkbd.kb_to_unicode(key, **kwds)
        virtual_key_code, kb_states = winkbd.unichar_to_virtual_key(unicode(actual_char))
        actual_states = flag_value(CONTROL_KEY_STATE_FLAGS, **kb_states)

        kc.Char = unicode(actual_char)
        kc.VirtualKeyCode = virtual_key_code
        kc.ControlKeyState = actual_states
    else:
        raise RuntimeError("no such key %s"% (key,))
    return kc

########NEW FILE########
__FILENAME__ = winkbd
#! coding: utf-8

import ctypes
from ctypes import windll
user32 = windll.user32

# http://msdn.microsoft.com/en-us/library/windows/desktop/dd375731(v=vs.85).aspx
# Winuser.h
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12

NULL = 0x00
KB_STATES_SIZE = 256
# high-order bit == 1 means the key is down
# See GetKeyboardState function for more information:
# http://msdn.microsoft.com/en-us/library/windows/desktop/ms646299(v=vs.85).aspx
KB_STATE_KEY_DOWN = 0xF0


def unichar_to_virtual_key(c):
    # return vk code and keyboard state
    rv = user32.VkKeyScanA(ord(c))
    virtual_key_code = rv & 0xFF
    keyboard_state = rv >> 8

    translated_states = dict(shift=False, ctrl=False, alt=False)

    if keyboard_state & 0x01 == 0x01:
        translated_states["shift"] = True
    if keyboard_state & 0x02 == 0x02:
        translated_states["ctrl"] = True
    if keyboard_state & 0x04 == 0x04:
        translated_states["alt"] = True

    return virtual_key_code, translated_states


def kb_to_unicode(unichar, shift=False, ctrl=False, alt=False, **kwd):
    # Converts key binding to unicode char on Windows
    virtual_key_code, _ = unichar_to_virtual_key(unichar)

    # See GetKeyboardState function for more information:
    # http://msdn.microsoft.com/en-us/library/windows/desktop/ms646299(v=vs.85).aspx
    states_as_bytes = (ctypes.c_byte * KB_STATES_SIZE)(*((NULL,) * KB_STATES_SIZE))
    if shift:
        states_as_bytes[VK_SHIFT] = KB_STATE_KEY_DOWN
    if ctrl:
        states_as_bytes[VK_CONTROL] = KB_STATE_KEY_DOWN
    if alt:
        states_as_bytes[VK_MENU] = KB_STATE_KEY_DOWN

    # will fail with dead keys
    rv = ctypes.create_string_buffer(1)
    user32.ToUnicode(
                virtual_key_code,
                None,
                states_as_bytes,
                rv,
                len(rv),
                0
                )

    return rv.value[0]


if __name__ == '__main__':
    # this will only make sense in one keyboard layout for Spanish
    print kb_to_unicode(u"2", ctrl=True, alt=True), "@"
    print kb_to_unicode(u"1", ctrl=True, alt=True), "|"
    print kb_to_unicode(u"1", ctrl=False, alt=False), "1"
    print kb_to_unicode(u"a", ctrl=False, alt=False), "a"

########NEW FILE########
__FILENAME__ = keymap

CTRL = 0x01
ALT = 0x02
SHIFT = 0x04
SUPER = 0x08

ANSI = {
	"enter": "\n", 
	"tab": "\t", 
	"f10": "\x1b[21~", 
    "space": " ",
    "f8": "\e[[19~",
    "escape": "\x1b\x1b",
    "down": "\x1b[B",
    "up": "\x1b[A", 
    "right": "\x1b[C",
    "left": "\x1b[D",
    "backspace": "\b",
    "c": {CTRL: chr(3)}
}


WIN32 = {
    "enter": "\r",
    "tab": "\t",
    "backspace": "\b",
    "up": chr(38),
    "down": chr(40)
}
########NEW FILE########
__FILENAME__ = process
#!coding: utf-8
from __future__ import division
from __future__ import absolute_import

import subprocess
from weakref import WeakValueDictionary
import pyte
import keymap
import os
import sys
from collections import namedtuple

Coord = namedtuple("Coord", ["x", "y"])
ColorSpec = namedtuple("ColorSpec", ["scope", "regions", "key"])
ON_WINDOWS = os.name == "nt" 

try:
    import tty
    import pty
except ImportError:
    pass

PACKAGE_DIR = os.getcwdu()
sys.path.append(PACKAGE_DIR)

class Supervisor(object):
    def __init__(self):
        self.processes = WeakValueDictionary()

    def register(self, process):
        self.processes[process.id] = process

    def process(self, process_id):
        if process_id in self.processes:
            return self.processes[process_id]
        return None

    def read_all(self):
        for process in self.processes.values():
            process.read()


class Process(object):
    DEFAULT_COLUMNS = 80
    DEFAULT_LINES   = 24
    MIN_COLUMNS     = 10
    MIN_LINES       = 2 

    def __init__(self, supervisor):
        from uuid import uuid4
        self.id = uuid4().hex
        self._supervisor = supervisor
        self._views = []
        self._columns = self.DEFAULT_COLUMNS
        self._lines = self.DEFAULT_LINES
        
        self._supervisor.register(self)

    def attach_view(self, view):
        """Connect a View(thing that displays Process output) to this Process"""
        self._views.append(view)
        view.process = self

    def detach_view(self, view):
        """Detaches a view that was previously added"""
        pass

    @property
    def columns(self):
        return self._columns

    @property
    def lines(self):
        return self._lines

    def available_columns(self):
        ac = min((v.available_columns() for v in self._views))
        return max(ac, self.MIN_COLUMNS)

    def available_lines(self):
        al = min((v.available_lines() for v in self._views))
        return max(al, self.MIN_LINES)

    def start(self):
        raise NotImplemented

    def stop(self):
        raise NotImplemented

    def is_running(self):
        raise NotImplemented

    def send_bytes(self, bytes):
        raise NotImplemented

    def send_keypress(self, key, ctrl=False, alt=False, shift=False, super=False):
        raise NotImplemented

    def send_click(self, row, col, **kwds):
        raise NotImplemented

    def read(self):
        raise NotImplemented



class PtyProcess(Process):
    
    DEFAULT_LOCALE = 'en_US.UTF8'
    KEYMAP = keymap.ANSI

    def __init__(self, supervisor, cmd=None, env=None, cwd=None, encodings=None):
        super(PtyProcess, self).__init__(supervisor)
        self._cmd = cmd or [os.environ.get("SHELL")]
        self._env = env or os.environ
        self._env["TERM"] = "linux"

        self._cwd = cwd or "."
        self._process = None
        self._master = None
        self._slave = None
        
        self._stream = pyte.ByteStream(encodings)
        self._dbg_steram = None #pyte.DebugStream()
        self._screens = {'diff': pyte.DiffScreen(self.DEFAULT_COLUMNS, self.DEFAULT_LINES)}
        for screen in self._screens.values():
            self._stream.attach(screen)


    def start(self):
        self._start()

    def _start(self):
        (self._master, self._slave) = pty.openpty()
        #ttyname = os.ttyname(self._slave)
        self._process = subprocess.Popen(self._cmd, stdin=self._slave, 
                                         stdout=self._slave, stderr=self._slave, shell=False, 
                                         env=self._env, close_fds=True, preexec_fn=os.setsid)
        
    def refresh_views(self):
        sc = self._screens['diff']
        dis = sc.display
        lines_dict = dict((lineno, dis[lineno]) for lineno in sc.dirty)
        sc.dirty.clear()
        cursor = self._screens['diff'].cursor
        for v in self._views:
            v.diff_refresh(lines_dict, cursor)

    def read(self):
        self._read()

    def _read(self):
        import select
        
        read = 0
        while True:
            (r,w,x) = select.select([self._master], [], [], 0)
            if not r:
                break # no input
            if not self.is_running(): 
                return # dont lock on exit!
            data = os.read(self._master, 1024)
            read += len(data)
            self._stream.feed(data)
            if self._dbg_steram:
                self._dbg_steram.feed(data)
        if read:
            self.refresh_views()
        return read

    def send_bytes(self, bytes):
        if self.is_running():
            os.write(self._master, bytes)

    def stop(self):
        self._process.kill()
        self._process = None 
        return 

    def is_running(self):
        return self._process is not None and self._process.poll() is None

    def send_ctrl(self, key):
        char = key.lower()
        a = ord(char)
        if a>=97 and a<=122:
            a = a - ord('a') + 1
            return self.send_bytes(chr(a))
        d = {'@':0, '`':0, '[':27, '{':27, '\\':28, '|':28, ']':29, '}': 29,
            '^':30, '~':30,'_':31, '?':127}
        if char not in d:
            return
        return self.send_bytes(chr(d[char]))

    def send_keypress(self, key, ctrl=False, alt=False, shift=False, super=False):
        if ctrl and len(key)==1:
            self.send_ctrl(key)
            self._read()
            return 
        bytes = key
        if key in self.KEYMAP:
            d = self.KEYMAP[key]
            flags = 0
            flags |= keymap.CTRL * ctrl
            if isinstance(d, dict):
                if flags in d:
                    bytes = d[flags]
                else:
                    bytes = key
            else:
                bytes = d
        self.send_bytes(bytes)
        self._read()


colors = [
    "black",
    "darkblue",  #ok
    "darkgreen", #ok
    "darkcyan",  #ok
    "darkred", 
    "darkmagenta",
    "brown",
    "white",
    "lightgrey", #ok
    "blue",  #ok
    "green", #ok
    "cyan",  #ok
    "red",   #ok
    "magenta",
    "yellow", # ok
    "white"
]

def fg_color(char_attribute):
    col = colors[char_attribute & 0x0F]
    if col == "white":
        return "default"
    return col

def bg_color(char_attribute):
    ca = (char_attribute & 0xF0) >> 4
    col = colors[ca & 0x0F]
    if col == "black":
        return "default"
    return col


class Win32Process(Process):
    KEYMAP = keymap.WIN32
    SIZE_REFRESH_EACH = 50 # reads

    def __init__(self, *args, **kwds):
        self._lines = {}
        self._reads = 1
        self._width = 0
        self._height = 0
        self._last_cursor_pos = None
        self._cc = None
        super(Win32Process, self).__init__(*args, **kwds)

    def start(self):
        from console.console_client import ConsoleClient
        self._cc = ConsoleClient("localhost", 8828)

    def stop(self):
        pass

    def is_running(self):
        return self._cc.is_running

    def send_bytes(self, bytes):
        self._cc.write_console_input(bytes)

    def send_keypress(self, key, ctrl=False, alt=False, shift=False, super=False):
        if (ctrl and not (alt or shift or super) and key=='c'):
            self._cc.send_ctrl_c()
        else:
            self._cc.send_keypress(key, ctrl=ctrl, alt=alt, shift=shift, super=super)
        self.read()

    def send_click(self, row, col, **kwds):
        self._cc.send_click(row, col, **kwds)
        self.read()

    def read(self):
        if not self._cc:
            return # dead or not started yet
        full = False
        with_colors = True
        self._reads = (self._reads + 1) % self.SIZE_REFRESH_EACH
        if not self._reads:
            self._size_refresh()
            full = True

        (_lines, _cursor_pos, _colors) = self._cc.read(full, with_colors)
        cursor_pos = Coord(*_cursor_pos) # we need .x .y access
        if not full and self._last_cursor_pos == cursor_pos:
            cursor_pos = None
        else:
            self._last_cursor_pos = cursor_pos

        translated_colors = self._translate_colors(_colors)
            
        lines = {}
        for k,v in _lines.items():
            lines[int(k)] = v
        for v in self._views:
            if full:
                v.full_refresh(lines, cursor_pos, translated_colors)
            else:
                v.diff_refresh(lines, cursor_pos, translated_colors)

    def _translate_colors(self, colors):
        translated_colors = {}
        for line_str, line in colors.items():
            start = int(line_str) * (len(line) + 1)
            for idx, colornum in enumerate(line):
                scope = fg_color(colornum) + "." + bg_color(colornum)
                reg = (start + idx, start + idx + 1)
                key = line_str + "." + str(idx)
                translated_colors[key] = ColorSpec(scope, [reg], key)    
                
        return translated_colors

    def _size_refresh(self):
        height = self.available_lines()
        width = self.available_columns()
        if self._width == width and self._height == height:
            return 
        self._width = width
        self._height = height
        self._cc.set_window_size(width, height)


class SublimeView(object):
    def __init__(self, view=None):
        v = view or self._new_view()
        self._view = v
        self._process = None
        settings = v.settings()
        settings.set("sublimepty", True)
        settings.set("line_numbers", False)
        settings.set("caret_style", "blink")
        settings.set("auto_complete", False)
        settings.set("draw_white_space", "none")
        settings.set("word_wrap", False)
        settings.set("gutter", False)
        settings.set("color_scheme", os.path.join(PACKAGE_DIR, "SublimePTY.tmTheme"))
        if ON_WINDOWS: # better defaults
            settings.set("font_face", "Consolas Bold") 
            settings.set("font_options", ["directwrite"])
            settings.set("font_size", 11)
        v.set_scratch(True)
        v.set_name("TERMINAL")

    @property
    def process(self):
        return self._process

    @property
    def view(self):
        return self._view

    @process.setter
    def process(self, new_process):
        if self._process:
            self._process.detach_view(self)
        self._process = new_process
        if new_process:
            self._view.settings().set("sublimepty_id", new_process.id)
            self._fill_stars(new_process._columns, new_process._lines)
        else:
            self._view.settings().set("sublimepty_id", None)
            
    def _fill_stars(self, columns, lines):
        self.full_refresh(["*"*columns]*lines)

    def _new_view(self):
        import sublime
        return sublime.active_window().new_file()

    def available_columns(self):
        (w, h) = self._view.viewport_extent()
        return int(w // self._view.em_width())

    def available_lines(self):
        (w, h) = self._view.viewport_extent()
        return int(h // self._view.line_height())

    def _set_cursor(self, cursor):
        import sublime
        if not cursor:
            return 
        self._view.sel().clear()
        tp = self._view.text_point(cursor.y, cursor.x)
        self._view.sel().add(sublime.Region(tp, tp))

    def _apply_colors(self, translated_colors):
        import sublime
        v = self._view
        for cs in translated_colors.values():
            v.erase_regions(cs.key)
            if cs.scope == "default.default":  # partial colors mode
                continue
            v.add_regions(str(cs.key), [sublime.Region(*x) for x in cs.regions], cs.scope, "", sublime.DRAW_EMPTY_AS_OVERWRITE)
            
        
    def full_refresh(self, lines, cursor=None, translated_colors=None):
        import sublime
        v = self._view
        ed = v.begin_edit()
        whole = sublime.Region(0, v.size())
        v.erase(ed, whole)
        for idx in range(len(lines)):
            l = lines[idx]
            p = v.text_point(idx, 0)
            v.insert(ed, p, l + "\n")
        if translated_colors:
            self._apply_colors(translated_colors)
        if cursor:
            self._set_cursor(cursor)
        v.end_edit(ed)

    def diff_refresh(self, lines_dict, cursor=None, translated_colors=None):
        import sublime
        v = self._view
        ed = v.begin_edit()
        for lineno, text in lines_dict.items():
            p = v.text_point(lineno, 0)
            line_region = v.line(p)
            v.replace(ed, line_region, text)
        if translated_colors:
            self._apply_colors(translated_colors)
        if cursor:
            self._set_cursor(cursor)
        v.end_edit(ed)


########NEW FILE########
__FILENAME__ = charsets
# -*- coding: utf-8 -*-
"""
    pyte.charsets
    ~~~~~~~~~~~~~~

    This module defines ``G0`` and ``G1`` charset mappings the same way
    they are defined for linux terminal, see
    ``linux/drivers/tty/consolemap.c`` @ http://git.kernel.org

    .. note:: ``VT100_MAP`` and ``IBMPC_MAP`` were taken unchanged
              from linux kernel source and therefore are licensed
              under **GPL**.

    :copyright: (c) 2011 by Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import unicode_literals


#: Latin1.
LAT1_MAP = map(unichr, xrange(256))

#: VT100 graphic character set.
VT100_MAP = "".join(unichr(c) for c in [
    0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0007,
    0x0008, 0x0009, 0x000a, 0x000b, 0x000c, 0x000d, 0x000e, 0x000f,
    0x0010, 0x0011, 0x0012, 0x0013, 0x0014, 0x0015, 0x0016, 0x0017,
    0x0018, 0x0019, 0x001a, 0x001b, 0x001c, 0x001d, 0x001e, 0x001f,
    0x0020, 0x0021, 0x0022, 0x0023, 0x0024, 0x0025, 0x0026, 0x0027,
    0x0028, 0x0029, 0x002a, 0x2192, 0x2190, 0x2191, 0x2193, 0x002f,
    0x2588, 0x0031, 0x0032, 0x0033, 0x0034, 0x0035, 0x0036, 0x0037,
    0x0038, 0x0039, 0x003a, 0x003b, 0x003c, 0x003d, 0x003e, 0x003f,
    0x0040, 0x0041, 0x0042, 0x0043, 0x0044, 0x0045, 0x0046, 0x0047,
    0x0048, 0x0049, 0x004a, 0x004b, 0x004c, 0x004d, 0x004e, 0x004f,
    0x0050, 0x0051, 0x0052, 0x0053, 0x0054, 0x0055, 0x0056, 0x0057,
    0x0058, 0x0059, 0x005a, 0x005b, 0x005c, 0x005d, 0x005e, 0x00a0,
    0x25c6, 0x2592, 0x2409, 0x240c, 0x240d, 0x240a, 0x00b0, 0x00b1,
    0x2591, 0x240b, 0x2518, 0x2510, 0x250c, 0x2514, 0x253c, 0x23ba,
    0x23bb, 0x2500, 0x23bc, 0x23bd, 0x251c, 0x2524, 0x2534, 0x252c,
    0x2502, 0x2264, 0x2265, 0x03c0, 0x2260, 0x00a3, 0x00b7, 0x007f,
    0x0080, 0x0081, 0x0082, 0x0083, 0x0084, 0x0085, 0x0086, 0x0087,
    0x0088, 0x0089, 0x008a, 0x008b, 0x008c, 0x008d, 0x008e, 0x008f,
    0x0090, 0x0091, 0x0092, 0x0093, 0x0094, 0x0095, 0x0096, 0x0097,
    0x0098, 0x0099, 0x009a, 0x009b, 0x009c, 0x009d, 0x009e, 0x009f,
    0x00a0, 0x00a1, 0x00a2, 0x00a3, 0x00a4, 0x00a5, 0x00a6, 0x00a7,
    0x00a8, 0x00a9, 0x00aa, 0x00ab, 0x00ac, 0x00ad, 0x00ae, 0x00af,
    0x00b0, 0x00b1, 0x00b2, 0x00b3, 0x00b4, 0x00b5, 0x00b6, 0x00b7,
    0x00b8, 0x00b9, 0x00ba, 0x00bb, 0x00bc, 0x00bd, 0x00be, 0x00bf,
    0x00c0, 0x00c1, 0x00c2, 0x00c3, 0x00c4, 0x00c5, 0x00c6, 0x00c7,
    0x00c8, 0x00c9, 0x00ca, 0x00cb, 0x00cc, 0x00cd, 0x00ce, 0x00cf,
    0x00d0, 0x00d1, 0x00d2, 0x00d3, 0x00d4, 0x00d5, 0x00d6, 0x00d7,
    0x00d8, 0x00d9, 0x00da, 0x00db, 0x00dc, 0x00dd, 0x00de, 0x00df,
    0x00e0, 0x00e1, 0x00e2, 0x00e3, 0x00e4, 0x00e5, 0x00e6, 0x00e7,
    0x00e8, 0x00e9, 0x00ea, 0x00eb, 0x00ec, 0x00ed, 0x00ee, 0x00ef,
    0x00f0, 0x00f1, 0x00f2, 0x00f3, 0x00f4, 0x00f5, 0x00f6, 0x00f7,
    0x00f8, 0x00f9, 0x00fa, 0x00fb, 0x00fc, 0x00fd, 0x00fe, 0x00ff
])

#: IBM Codepage 437.
IBMPC_MAP = "".join(unichr(c) for c in [
    0x0000, 0x263a, 0x263b, 0x2665, 0x2666, 0x2663, 0x2660, 0x2022,
    0x25d8, 0x25cb, 0x25d9, 0x2642, 0x2640, 0x266a, 0x266b, 0x263c,
    0x25b6, 0x25c0, 0x2195, 0x203c, 0x00b6, 0x00a7, 0x25ac, 0x21a8,
    0x2191, 0x2193, 0x2192, 0x2190, 0x221f, 0x2194, 0x25b2, 0x25bc,
    0x0020, 0x0021, 0x0022, 0x0023, 0x0024, 0x0025, 0x0026, 0x0027,
    0x0028, 0x0029, 0x002a, 0x002b, 0x002c, 0x002d, 0x002e, 0x002f,
    0x0030, 0x0031, 0x0032, 0x0033, 0x0034, 0x0035, 0x0036, 0x0037,
    0x0038, 0x0039, 0x003a, 0x003b, 0x003c, 0x003d, 0x003e, 0x003f,
    0x0040, 0x0041, 0x0042, 0x0043, 0x0044, 0x0045, 0x0046, 0x0047,
    0x0048, 0x0049, 0x004a, 0x004b, 0x004c, 0x004d, 0x004e, 0x004f,
    0x0050, 0x0051, 0x0052, 0x0053, 0x0054, 0x0055, 0x0056, 0x0057,
    0x0058, 0x0059, 0x005a, 0x005b, 0x005c, 0x005d, 0x005e, 0x005f,
    0x0060, 0x0061, 0x0062, 0x0063, 0x0064, 0x0065, 0x0066, 0x0067,
    0x0068, 0x0069, 0x006a, 0x006b, 0x006c, 0x006d, 0x006e, 0x006f,
    0x0070, 0x0071, 0x0072, 0x0073, 0x0074, 0x0075, 0x0076, 0x0077,
    0x0078, 0x0079, 0x007a, 0x007b, 0x007c, 0x007d, 0x007e, 0x2302,
    0x00c7, 0x00fc, 0x00e9, 0x00e2, 0x00e4, 0x00e0, 0x00e5, 0x00e7,
    0x00ea, 0x00eb, 0x00e8, 0x00ef, 0x00ee, 0x00ec, 0x00c4, 0x00c5,
    0x00c9, 0x00e6, 0x00c6, 0x00f4, 0x00f6, 0x00f2, 0x00fb, 0x00f9,
    0x00ff, 0x00d6, 0x00dc, 0x00a2, 0x00a3, 0x00a5, 0x20a7, 0x0192,
    0x00e1, 0x00ed, 0x00f3, 0x00fa, 0x00f1, 0x00d1, 0x00aa, 0x00ba,
    0x00bf, 0x2310, 0x00ac, 0x00bd, 0x00bc, 0x00a1, 0x00ab, 0x00bb,
    0x2591, 0x2592, 0x2593, 0x2502, 0x2524, 0x2561, 0x2562, 0x2556,
    0x2555, 0x2563, 0x2551, 0x2557, 0x255d, 0x255c, 0x255b, 0x2510,
    0x2514, 0x2534, 0x252c, 0x251c, 0x2500, 0x253c, 0x255e, 0x255f,
    0x255a, 0x2554, 0x2569, 0x2566, 0x2560, 0x2550, 0x256c, 0x2567,
    0x2568, 0x2564, 0x2565, 0x2559, 0x2558, 0x2552, 0x2553, 0x256b,
    0x256a, 0x2518, 0x250c, 0x2588, 0x2584, 0x258c, 0x2590, 0x2580,
    0x03b1, 0x00df, 0x0393, 0x03c0, 0x03a3, 0x03c3, 0x00b5, 0x03c4,
    0x03a6, 0x0398, 0x03a9, 0x03b4, 0x221e, 0x03c6, 0x03b5, 0x2229,
    0x2261, 0x00b1, 0x2265, 0x2264, 0x2320, 0x2321, 0x00f7, 0x2248,
    0x00b0, 0x2219, 0x00b7, 0x221a, 0x207f, 0x00b2, 0x25a0, 0x00a0
])


#: VAX42 character set.
VAX42_MAP = "".join(unichr(c) for c in [
    0x0000, 0x263a, 0x263b, 0x2665, 0x2666, 0x2663, 0x2660, 0x2022,
    0x25d8, 0x25cb, 0x25d9, 0x2642, 0x2640, 0x266a, 0x266b, 0x263c,
    0x25b6, 0x25c0, 0x2195, 0x203c, 0x00b6, 0x00a7, 0x25ac, 0x21a8,
    0x2191, 0x2193, 0x2192, 0x2190, 0x221f, 0x2194, 0x25b2, 0x25bc,
    0x0020, 0x043b, 0x0022, 0x0023, 0x0024, 0x0025, 0x0026, 0x0027,
    0x0028, 0x0029, 0x002a, 0x002b, 0x002c, 0x002d, 0x002e, 0x002f,
    0x0030, 0x0031, 0x0032, 0x0033, 0x0034, 0x0035, 0x0036, 0x0037,
    0x0038, 0x0039, 0x003a, 0x003b, 0x003c, 0x003d, 0x003e, 0x0435,
    0x0040, 0x0041, 0x0042, 0x0043, 0x0044, 0x0045, 0x0046, 0x0047,
    0x0048, 0x0049, 0x004a, 0x004b, 0x004c, 0x004d, 0x004e, 0x004f,
    0x0050, 0x0051, 0x0052, 0x0053, 0x0054, 0x0055, 0x0056, 0x0057,
    0x0058, 0x0059, 0x005a, 0x005b, 0x005c, 0x005d, 0x005e, 0x005f,
    0x0060, 0x0441, 0x0062, 0x0063, 0x0064, 0x0065, 0x0066, 0x0067,
    0x0435, 0x0069, 0x006a, 0x006b, 0x006c, 0x006d, 0x006e, 0x043a,
    0x0070, 0x0071, 0x0442, 0x0073, 0x043b, 0x0435, 0x0076, 0x0077,
    0x0078, 0x0079, 0x007a, 0x007b, 0x007c, 0x007d, 0x007e, 0x2302,
    0x00c7, 0x00fc, 0x00e9, 0x00e2, 0x00e4, 0x00e0, 0x00e5, 0x00e7,
    0x00ea, 0x00eb, 0x00e8, 0x00ef, 0x00ee, 0x00ec, 0x00c4, 0x00c5,
    0x00c9, 0x00e6, 0x00c6, 0x00f4, 0x00f6, 0x00f2, 0x00fb, 0x00f9,
    0x00ff, 0x00d6, 0x00dc, 0x00a2, 0x00a3, 0x00a5, 0x20a7, 0x0192,
    0x00e1, 0x00ed, 0x00f3, 0x00fa, 0x00f1, 0x00d1, 0x00aa, 0x00ba,
    0x00bf, 0x2310, 0x00ac, 0x00bd, 0x00bc, 0x00a1, 0x00ab, 0x00bb,
    0x2591, 0x2592, 0x2593, 0x2502, 0x2524, 0x2561, 0x2562, 0x2556,
    0x2555, 0x2563, 0x2551, 0x2557, 0x255d, 0x255c, 0x255b, 0x2510,
    0x2514, 0x2534, 0x252c, 0x251c, 0x2500, 0x253c, 0x255e, 0x255f,
    0x255a, 0x2554, 0x2569, 0x2566, 0x2560, 0x2550, 0x256c, 0x2567,
    0x2568, 0x2564, 0x2565, 0x2559, 0x2558, 0x2552, 0x2553, 0x256b,
    0x256a, 0x2518, 0x250c, 0x2588, 0x2584, 0x258c, 0x2590, 0x2580,
    0x03b1, 0x00df, 0x0393, 0x03c0, 0x03a3, 0x03c3, 0x00b5, 0x03c4,
    0x03a6, 0x0398, 0x03a9, 0x03b4, 0x221e, 0x03c6, 0x03b5, 0x2229,
    0x2261, 0x00b1, 0x2265, 0x2264, 0x2320, 0x2321, 0x00f7, 0x2248,
    0x00b0, 0x2219, 0x00b7, 0x221a, 0x207f, 0x00b2, 0x25a0, 0x00a0
])


MAPS = {
    "B": LAT1_MAP,
    "0": VT100_MAP,
    "U": IBMPC_MAP,
    "V": VAX42_MAP
}

########NEW FILE########
__FILENAME__ = control
# -*- coding: utf-8 -*-
"""
    pyte.control
    ~~~~~~~~~~~~

    This module defines simple control sequences, recognized by
    :class:`~pyte.streams.Stream`, the set of codes here is for
    ``TERM=linux`` which is a superset of VT102.

    :copyright: (c) 2011 by Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import unicode_literals

#: *Space*: Not suprisingly -- ``" "``.
SP = " "

#: *Null*: Does nothing.
NUL = "\u0000"

#: *Bell*: Beeps.
BEL = "\u0007"

#: *Backspace*: Backspace one column, but not past the begining of the
#: line.
BS = "\u0008"

#: *Horizontal tab*: Move cursor to the next tab stop, or to the end
#: of the line if there is no earlier tab stop.
HT = "\u0009"

#: *Linefeed*: Give a line feed, and, if :data:`pyte.modes.LNM` (new
#: line mode) is set also a carriage return.
LF = "\n"
#: *Vertical tab*: Same as :data:`LF`.
VT = "\u000b"
#: *Form feed*: Same as :data:`LF`.
FF = "\u000c"

#: *Carriage return*: Move cursor to left margin on current line.
CR = "\r"

#: *Shift out*: Activate G1 character set.
SO = "\u000e"

#: *Shift in*: Activate G0 character set.
SI = "\u000f"

#: *Cancel*: Interrupt escape sequence. If received during an escape or
#: control sequence, cancels the sequence and displays substitution
#: character.
CAN = "\u0018"
#: *Substitute*: Same as :data:`CAN`.
SUB = "\u001a"

#: *Escape*: Starts an escape sequence.
ESC = "\u001b"

#: *Delete*: Is ingored.
DEL = "\u007f"

#: *Control sequence introducer*: An equavalent for ``ESC [``.
CSI = "\u009b"

########NEW FILE########
__FILENAME__ = escape
# -*- coding: utf-8 -*-
"""
    pyte.escape
    ~~~~~~~~~~~

    This module defines bot CSI and non-CSI escape sequences, recognized
    by :class:`~pyte.streams.Stream` and subclasses.

    :copyright: (c) 2011 by Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import unicode_literals


#: *Reset*.
RIS = "c"

#: *Index*: Move cursor down one line in same column. If the cursor is
#: at the bottom margin, the screen performs a scroll-up.
IND = "D"

#: *Next line*: Same as :data:`pyte.control.LF`.
NEL = "E"

#: Tabulation set: Set a horizontal tab stop at cursor position.
HTS = "H"

#: *Reverse index*: Move cursor up one line in same column. If the
#: cursor is at the top margin, the screen performs a scroll-down.
RI = "M"

#: Save cursor: Save cursor position, character attribute (graphic
#: rendition), character set, and origin mode selection (see
#: :data:`DECRC`).
DECSC = "7"

#: *Restore cursor*: Restore previously saved cursor position, character
#: attribute (graphic rendition), character set, and origin mode
#: selection. If none were saved, move cursor to home position.
DECRC = "8"


# "Sharp" escape sequences.
# -------------------------

#: *Alignment display*: Fill screen with uppercase E's for testing
#: screen focus and alignment.
DECALN = "8"


# ECMA-48 CSI sequences.
# ---------------------

#: *Insert character*: Insert the indicated # of blank characters.
ICH = "@"

#: *Cursor up*: Move cursor up the indicated # of lines in same column.
#: Cursor stops at top margin.
CUU = "A"

#: *Cursor down*: Move cursor down the indicated # of lines in same
#: column. Cursor stops at bottom margin.
CUD = "B"

#: *Cursor forward*: Move cursor right the indicated # of columns.
#: Cursor stops at right margin.
CUF = "C"

#: *Cursor back*: Move cursor left the indicated # of columns. Cursor
#: stops at left margin.
CUB = "D"

#: *Cursor next line*: Move cursor down the indicated # of lines to
#: column 1.
CNL = "E"

#: *Cursor previous line*: Move cursor up the indicated # of lines to
#: column 1.
CPL = "F"

#: *Cursor horizontal align*: Move cursor to the indicated column in
#: current line.
CHA = "G"

#: *Cursor position*: Move cursor to the indicated line, column (origin
#: at ``1, 1``).
CUP = "H"

#: *Erase data* (default: from cursor to end of line).
ED = "J"

#: *Erase in line* (default: from cursor to end of line).
EL = "K"

#: *Insert line*: Insert the indicated # of blank lines, starting from
#: the current line. Lines displayed below cursor move down. Lines moved
#: past the bottom margin are lost.
IL = "L"

#: *Delete line*: Delete the indicated # of lines, starting from the
#: current line. As lines are deleted, lines displayed below cursor
#: move up. Lines added to bottom of screen have spaces with same
#: character attributes as last line move up.
DL = "M"

#: *Delete character*: Delete the indicated # of characters on the
#: current line. When character is deleted, all characters to the right
#: of cursor move left.
DCH = "P"

#: *Erase character*: Erase the indicated # of characters on the
#: current line.
ECH = "X"

#: *Horizontal position relative*: Same as :data:`CUF`.
HPR = "a"

#: *Vertical position adjust*: Move cursor to the indicated line,
#: current column.
VPA = "d"

#: *Vertical position relative*: Same as :data:`CUD`.
VPR = "e"

#: *Horizontal / Vertical position*: Same as :data:`CUP`.
HVP = "f"

#: *Tabulation clear*: Clears a horizontal tab stop at cursor position.
TBC = "g"

#: *Set mode*.
SM = "h"

#: *Reset mode*.
RM = "l"

#: *Select graphics rendition*: The terminal can display the following
#: character attributes that change the character display without
#: changing the character (see :mod:`pyte.graphics`).
SGR = "m"

#: *Select top and bottom margins*: Selects margins, defining the
#: scrolling region; parameters are top and bottom line. If called
#: without any arguments, whole screen is used.
DECSTBM = "r"

#: *Horizontal position adjust*: Same as :data:`CHA`.
HPA = "'"

########NEW FILE########
__FILENAME__ = graphics
# -*- coding: utf-8 -*-
"""
    pyte.graphics
    ~~~~~~~~~~~~~

    This module defines graphic-related constants, mostly taken from
    :manpage:`console_codes(4)` and
    http://pueblo.sourceforge.net/doc/manual/ansi_color_codes.html.

    :copyright: (c) 2011 by Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
"""

#: A mapping of ANSI text style codes to style names, "+" means the:
#: attribute is set, "-" -- reset; example:
#:
#: >>> text[1]
#: '+bold'
#: >>> text[9]
#: '+strikethrough'
TEXT = {
    1: "+bold" ,
    3: "+italics",
    4: "+underscore",
    7: "+reverse",
    9: "+strikethrough",
    22: "-bold",
    23: "-italics",
    24: "-underscore",
    27: "-reverse",
    29: "-strikethrough"
}


#: A mapping of ANSI foreground color codes to color names, example:
#:
#: >>> FG[30]
#: 'black'
#: >>> FG[38]
#: 'default'
FG = {
    30: "black",
    31: "red",
    32: "green",
    33: "brown",
    34: "blue",
    35: "magenta",
    36: "cyan",
    37: "white",
    39: "default"  # white.
}

#: A mapping of ANSI background color codes to color names, example:
#:
#: >>> BG[40]
#: 'black'
#: >>> BG[48]
#: 'default'
BG = {
    40: "black",
    41: "red",
    42: "green",
    43: "brown",
    44: "blue",
    45: "magenta",
    46: "cyan",
    47: "white",
    49: "default"  # black.
}

# Reverse mapping of all available attributes -- keep this private!
_SGR = dict((v, k) for k, v in BG.items() + FG.items() + TEXT.items())

########NEW FILE########
__FILENAME__ = modes
# -*- coding: utf-8 -*-
"""
    pyte.modes
    ~~~~~~~~~~

    This module defines terminal mode switches, used by
    :class:`~pyte.screens.Screen`. There're two types of terminal modes:

    * `non-private` which should be set with ``ESC [ N h``, where ``N``
      is an integer, representing mode being set; and
    * `private` which should be set with ``ESC [ ? N h``.

    The latter are shifted 5 times to the right, to be easily
    distinguishable from the former ones; for example `Origin Mode`
    -- :data:`DECOM` is ``192`` not ``6``.

    >>> DECOM
    192

    :copyright: (c) 2011 by Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
"""

#: *Line Feed/New Line Mode*: When enabled, causes a received
#: :data:`~pyte.control.LF`, :data:`pyte.control.FF`, or
#: :data:`~pyte.control.VT` to move the cursor to the first column of
#: the next line.
LNM = 20

#: *Insert/Replace Mode*: When enabled, new display characters move
#: old display characters to the right. Characters moved past the
#: right margin are lost. Otherwise, new display characters replace
#: old display characters at the cursor position.
IRM = 4


# Private modes.
# ..............

#: *Text Cursor Enable Mode*: determines if the text cursor is
#: visible.
DECTCEM = 25 << 5

#: *Screen Mode*: toggles screen-wide reverse-video mode.
DECSCNM = 5 << 5

#: *Origin Mode*: allows cursor addressing relative to a user-defined
#: origin. This mode resets when the terminal is powered up or reset.
#: It does not affect the erase in display (ED) function.
DECOM = 6 << 5

#: *Auto Wrap Mode*: selects where received graphic characters appear
#: when the cursor is at the right margin.
DECAWM = 7 << 5

#: *Column Mode*: selects the number of columns per line (80 or 132)
#: on the screen.
DECCOLM = 3 << 5

########NEW FILE########
__FILENAME__ = screens
# -*- coding: utf-8 -*-
"""
    pyte.screens
    ~~~~~~~~~~~~

    This module provides classes for terminal screens, currently
    it contains three screens with different features:

    * :class:`~pyte.screens.Screen` -- base screen implementation,
      which handles all the core escape sequences, recognized by
      :class:`~pyte.streams.Stream`.
    * If you need a screen to keep track of the changed lines
      (which you probably do need) -- use
      :class:`~pyte.screens.DiffScreen`.
    * If you also want a screen to collect history and allow
      pagination -- :class:`pyte.screen.HistoryScreen` is here
      for ya ;)

    .. note:: It would be nice to split those features into mixin
              classes, rather than subclasses, but it's not obvious
              how to do -- feel free to submit a pull request.

    :copyright: (c) 2011 Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import (
    absolute_import, print_function, unicode_literals, division
)

import copy
import math
import operator
from collections import namedtuple, deque
from itertools import islice, repeat

from . import modes as mo, graphics as g, charsets as cs


try:
    xrange
except NameError:
    pass
else:
    range = xrange


def take(n, iterable):
    """Returns first n items of the iterable as a list."""
    return list(islice(iterable, n))


#: A container for screen's scroll margins.
Margins = namedtuple("Margins", "top bottom")

#: A container for savepoint, created on :data:`~pyte.escape.DECSC`.
Savepoint = namedtuple("Savepoint", [
    "cursor",
    "g0_charset",
    "g1_charset",
    "charset",
    "origin",
    "wrap"
])

#: A container for a single character, field names are *hopefully*
#: self-explanatory.
_Char = namedtuple("_Char", [
    "data",
    "fg",
    "bg",
    "bold",
    "italics",
    "underscore",
    "strikethrough",
    "reverse",
])


class Char(_Char):
    """A wrapper around :class:`_Char`, providing some useful defaults
    for most of the attributes.
    """
    def __new__(cls, data, fg="default", bg="default", bold=False,
                italics=False, underscore=False, reverse=False,
                strikethrough=False):
        return _Char.__new__(cls, data, fg, bg, bold, italics, underscore,
                             reverse, strikethrough)


class Cursor(object):
    """Screen cursor.

    :param int x: horizontal cursor position.
    :param int y: vertical cursor position.
    :param pyte.screens.Char attrs: cursor attributes (see
        :meth:`~pyte.screens.Screen.selectel_graphic_rendition`
        for details).
    """
    def __init__(self, x, y, attrs=Char(" ")):
        self.x, self.y, self.attrs, self.hidden = x, y, attrs, False


class Screen(list):
    """
    A screen is an in-memory matrix of characters that represents the
    screen display of the terminal. It can be instantiated on it's own
    and given explicit commands, or it can be attached to a stream and
    will respond to events.

    .. attribute:: cursor

       Reference to the :class:`~pyte.screens.Cursor` object, holding
       cursor position and attributes.

    .. attribute:: margins

       Top and bottom screen margins, defining the scrolling region;
       the actual values are top and bottom line.

    .. attribute:: charset

       Current charset number; can be either ``0`` or ``1`` for `G0`
       and `G1` respectively, note that `G0` is activated by default.

    .. note::

       According to ``ECMA-48`` standard, **lines and columnns are
       1-indexed**, so, for instance ``ESC [ 10;10 f`` really means
       -- move cursor to position (9, 9) in the display matrix.

    .. seealso::

       `Standard ECMA-48, Section 6.1.1 \
       <http://www.ecma-international.org/publications
       /standards/Ecma-048.htm>`_
         For a description of the presentational component, implemented
         by ``Screen``.
    """
    #: A plain empty character with default foreground and background
    #: colors.
    default_char = Char(data=" ", fg="default", bg="default")

    #: An inifinite sequence of default characters, used for populating
    #: new lines and columns.
    default_line = repeat(default_char)

    def __init__(self, columns, lines):
        self.savepoints = []
        self.lines, self.columns = lines, columns
        self.reset()

    def __repr__(self):
        return ("{0}({1}, {2})".format(self.__class__.__name__,
                                       self.columns, self.lines))

    def __before__(self, command):
        """Hook, called **before** a command is dispatched to the
        :class:`Screen` instance.

        :param unicode command: command name, for example ``"LINEFEED"``.
        """

    def __after__(self, command):
        """Hook, called **after** a command is dispatched to the
        :class:`Screen` instance.

        :param unicode command: command name, for example ``"LINEFEED"``.
        """

    @property
    def size(self):
        """Returns screen size -- ``(lines, columns)``"""
        return self.lines, self.columns

    @property
    def display(self):
        """Returns a :func:`list` of screen lines as unicode strings."""
        return ["".join(map(operator.attrgetter("data"), line))
                for line in self]

    def reset(self):
        """Resets the terminal to its initial state.

        * Scroll margins are reset to screen boundaries.
        * Cursor is moved to home location -- ``(0, 0)`` and its
          attributes are set to defaults (see :attr:`default_char`).
        * Screen is cleared -- each character is reset to
          :attr:`default_char`.
        * Tabstops are reset to "every eight columns".

        .. note::

           Neither VT220 nor VT102 manuals mentioned that terminal modes
           and tabstops should be reset as well, thanks to
           :manpage:`xterm` -- we now know that.
        """
        self[:] = (take(self.columns, self.default_line)
                   for _ in range(self.lines))
        self.mode = set([mo.DECAWM, mo.DECTCEM, mo.LNM, mo.DECTCEM])
        self.margins = Margins(0, self.lines - 1)

        # According to VT220 manual and ``linux/drivers/tty/vt.c``
        # the default G0 charset is latin-1, but for reasons unknown
        # latin-1 breaks ascii-graphics; so G0 defaults to cp437.
        self.charset = 0
        self.g0_charset = cs.IBMPC_MAP
        self.g1_charset = cs.VT100_MAP

        # From ``man terminfo`` -- "... hardware tabs are initially
        # set every `n` spaces when the terminal is powered up. Since
        # we aim to support VT102 / VT220 and linux -- we use n = 8.
        self.tabstops = set(range(7, self.columns, 8))

        self.cursor = Cursor(0, 0)
        self.cursor_position()

    def resize(self, lines=None, columns=None):
        """Resize the screen to the given dimensions.

        If the requested screen size has more lines than the existing
        screen, lines will be added at the bottom. If the requested
        size has less lines than the existing screen lines will be
        clipped at the top of the screen. Similarly, if the existing
        screen has less columns than the requested screen, columns will
        be added at the right, and if it has more -- columns will be
        clipped at the right.

        .. note:: According to `xterm`, we should also reset origin
                  mode and screen margins, see ``xterm/screen.c:1761``.

        :param int lines: number of lines in the new screen.
        :param int columns: number of columns in the new screen.
        """
        lines = lines or self.lines
        columns = columns or self.columns

        # First resize the lines:
        diff = self.lines - lines

        # a) if the current display size is less than the requested
        #    size, add lines to the bottom.
        if diff < 0:
            self.extend(take(self.columns, self.default_line)
                        for _ in range(diff, 0))
        # b) if the current display size is greater than requested
        #    size, take lines off the top.
        elif diff > 0:
            self[:diff] = ()

        # Then resize the columns:
        diff = self.columns - columns

        # a) if the current display size is less than the requested
        #    size, expand each line to the new size.
        if diff < 0:
            for y in range(lines):
                self[y].extend(take(abs(diff), self.default_line))
        # b) if the current display size is greater than requested
        #    size, trim each line from the right to the new size.
        elif diff > 0:
            self[:] = (line[:columns] for line in self)

        self.lines, self.columns = lines, columns
        self.margins = Margins(0, self.lines - 1)
        self.reset_mode(mo.DECOM)

    def set_margins(self, top=None, bottom=None):
        """Selects top and bottom margins for the scrolling region.

        Margins determine which screen lines move during scrolling
        (see :meth:`index` and :meth:`reverse_index`). Characters added
        outside the scrolling region do not cause the screen to scroll.

        :param int top: the smallest line number that is scrolled.
        :param int bottom: the biggest line number that is scrolled.
        """
        if top is None or bottom is None:
            return

        # Arguments are 1-based, while :attr:`margins` are zero based --
        # so we have to decrement them by one. We also make sure that
        # both of them is bounded by [0, lines - 1].
        top = max(0, min(top - 1, self.lines - 1))
        bottom = max(0, min(bottom - 1, self.lines - 1))

        # Even though VT102 and VT220 require DECSTBM to ignore regions
        # of width less than 2, some programs (like aptitude for example)
        # rely on it. Practicality beats purity.
        if bottom - top >= 1:
            self.margins = Margins(top, bottom)

            # The cursor moves to the home position when the top and
            # bottom margins of the scrolling region (DECSTBM) changes.
            self.cursor_position()

    def set_charset(self, code, mode):
        """Set active ``G0`` or ``G1`` charset.

        :param unicode code: character set code, should be a character
                             from ``"B0UK"`` -- otherwise ignored.
        :param unicode mode: if ``"("`` ``G0`` charset is set, if
                             ``")"`` -- we operate on ``G1``.

        .. warning:: User-defined charsets are currently not supported.
        """
        print(code, code in cs.MAPS, cs.MAPS.keys())
        if code in cs.MAPS:
            setattr(self, {"(": "g0_charset", ")": "g1_charset"}[mode],
                    cs.MAPS[code])

    def set_mode(self, *modes, **kwargs):
        """Sets (enables) a given list of modes.

        :param list modes: modes to set, where each mode is a constant
                           from :mod:`pyte.modes`.
        """
        # Private mode codes are shifted, to be distingiushed from non
        # private ones.
        if kwargs.get("private"):
            modes = [mode << 5 for mode in modes]

        self.mode.update(modes)

        # When DECOLM mode is set, the screen is erased and the cursor
        # moves to the home position.
        if mo.DECCOLM in modes:
            self.resize(columns=132)
            self.erase_in_display(2)
            self.cursor_position()

        # According to `vttest`, DECOM should also home the cursor, see
        # vttest/main.c:303.
        if mo.DECOM in modes:
            self.cursor_position()

        # Mark all displayed characters as reverse.
        if mo.DECSCNM in modes:
            self[:] = ([char._replace(reverse=True) for char in line]
                       for line in self)
            self.select_graphic_rendition(g._SGR["+reverse"])

        # Make the cursor visible.
        if mo.DECTCEM in modes:
            self.cursor.hidden = False

    def reset_mode(self, *modes, **kwargs):
        """Resets (disables) a given list of modes.

        :param list modes: modes to reset -- hopefully, each mode is a
                           constant from :mod:`pyte.modes`.
        """
        # Private mode codes are shifted, to be distingiushed from non
        # private ones.
        if kwargs.get("private"):
            modes = [mode << 5 for mode in modes]

        self.mode.difference_update(modes)

        # Lines below follow the logic in :meth:`set_mode`.
        if mo.DECCOLM in modes:
            self.resize(columns=80)
            self.erase_in_display(2)
            self.cursor_position()

        if mo.DECOM in modes:
            self.cursor_position()

        if mo.DECSCNM in modes:
            self[:] = ([char._replace(reverse=False) for char in line]
                       for line in self)
            self.select_graphic_rendition(g._SGR["-reverse"])

        # Hide the cursor.
        if mo.DECTCEM in modes:
            self.cursor.hidden = True

    def shift_in(self):
        """Activates ``G0`` character set."""
        self.charset = 0

    def shift_out(self):
        """Activates ``G1`` character set."""
        self.charset = 1

    def draw(self, char):
        """Display a character at the current cursor position and advance
        the cursor if :data:`~pyte.modes.DECAWM` is set.

        :param unicode char: a character to display.
        """
        # Translating a given character.
        char = char.translate([self.g0_charset,
                               self.g1_charset][self.charset])

        # If this was the last column in a line and auto wrap mode is
        # enabled, move the cursor to the next line. Otherwise replace
        # characters already displayed with newly entered.
        if self.cursor.x == self.columns:
            if mo.DECAWM in self.mode:
                self.linefeed()
            else:
                self.cursor.x -= 1

        # If Insert mode is set, new characters move old characters to
        # the right, otherwise terminal is in Replace mode and new
        # characters replace old characters at cursor position.
        if mo.IRM in self.mode:
            self.insert_characters(1)

        self[self.cursor.y][self.cursor.x] = self.cursor.attrs \
            ._replace(data=char)

        # .. note:: We can't use :meth:`cursor_forward()`, because that
        #           way, we'll never know when to linefeed.
        self.cursor.x += 1

    def carriage_return(self):
        """Move the cursor to the beginning of the current line."""
        self.cursor.x = 0

    def index(self):
        """Move the cursor down one line in the same column. If the
        cursor is at the last line, create a new line at the bottom.
        """
        top, bottom = self.margins

        if self.cursor.y == bottom:
            self.pop(top)
            self.insert(bottom, take(self.columns, self.default_line))
        else:
            self.cursor_down()

    def reverse_index(self):
        """Move the cursor up one line in the same column. If the cursor
        is at the first line, create a new line at the top.
        """
        top, bottom = self.margins

        if self.cursor.y == top:
            self.pop(bottom)
            self.insert(top, take(self.columns, self.default_line))
        else:
            self.cursor_up()

    def linefeed(self):
        """Performs an index and, if :data:`~pyte.modes.LNM` is set, a
        carriage return.
        """
        self.index()

        if mo.LNM in self.mode:
            self.carriage_return()

    def tab(self):
        """Move to the next tab space, or the end of the screen if there
        aren't anymore left.
        """
        for stop in sorted(self.tabstops):
            if self.cursor.x < stop:
                column = stop
                break
        else:
            column = self.columns - 1

        self.cursor.x = column

    def backspace(self):
        """Move cursor to the left one or keep it in it's position if
        it's at the beginning of the line already.
        """
        self.cursor_back()

    def save_cursor(self):
        """Push the current cursor position onto the stack."""
        self.savepoints.append(Savepoint(copy.copy(self.cursor),
                                         self.g0_charset,
                                         self.g1_charset,
                                         self.charset,
                                         mo.DECOM in self.mode,
                                         mo.DECAWM in self.mode))

    def restore_cursor(self):
        """Set the current cursor position to whatever cursor is on top
        of the stack.
        """
        if self.savepoints:
            savepoint = self.savepoints.pop()

            self.g0_charset = savepoint.g0_charset
            self.g1_charset = savepoint.g1_charset
            self.charset = savepoint.charset

            if savepoint.origin:
                self.set_mode(mo.DECOM)
            if savepoint.wrap:
                self.set_mode(mo.DECAWM)

            self.cursor = savepoint.cursor
            self.ensure_bounds(use_margins=True)
        else:
            # If nothing was saved, the cursor moves to home position;
            # origin mode is reset. :todo: DECAWM?
            self.reset_mode(mo.DECOM)
            self.cursor_position()

    def insert_lines(self, count=None):
        """Inserts the indicated # of lines at line with cursor. Lines
        displayed **at** and below the cursor move down. Lines moved
        past the bottom margin are lost.

        :param count: number of lines to delete.
        """
        count = count or 1
        top, bottom = self.margins

        # If cursor is outside scrolling margins it -- do nothin'.
        if top <= self.cursor.y <= bottom:
            #                           v +1, because range() is exclusive.
            for line in range(self.cursor.y,
                              min(bottom + 1, self.cursor.y + count)):
                self.pop(bottom)
                self.insert(line, take(self.columns, self.default_line))

            self.carriage_return()

    def delete_lines(self, count=None):
        """Deletes the indicated # of lines, starting at line with
        cursor. As lines are deleted, lines displayed below cursor
        move up. Lines added to bottom of screen have spaces with same
        character attributes as last line moved up.

        :param int count: number of lines to delete.
        """
        count = count or 1
        top, bottom = self.margins

        # If cursor is outside scrolling margins it -- do nothin'.
        if top <= self.cursor.y <= bottom:
            #                v -- +1 to include the bottom margin.
            for _ in range(min(bottom - self.cursor.y + 1, count)):
                self.pop(self.cursor.y)
                self.insert(bottom, list(
                    repeat(self.cursor.attrs, self.columns)))

            self.carriage_return()

    def insert_characters(self, count=None):
        """Inserts the indicated # of blank characters at the cursor
        position. The cursor does not move and remains at the beginning
        of the inserted blank characters. Data on the line is shifted
        forward.

        :param int count: number of characters to insert.
        """
        count = count or 1

        for _ in range(min(self.columns - self.cursor.y, count)):
            self[self.cursor.y].insert(self.cursor.x, self.cursor.attrs)
            self[self.cursor.y].pop()

    def delete_characters(self, count=None):
        """Deletes the indicated # of characters, starting with the
        character at cursor position. When a character is deleted, all
        characters to the right of cursor move left. Character attributes
        move with the characters.

        :param int count: number of characters to delete.
        """
        count = count or 1

        for _ in range(min(self.columns - self.cursor.x, count)):
            self[self.cursor.y].pop(self.cursor.x)
            self[self.cursor.y].append(self.cursor.attrs)

    def erase_characters(self, count=None):
        """Erases the indicated # of characters, starting with the
        character at cursor position. Character attributes are set
        cursor attributes. The cursor remains in the same position.

        :param int count: number of characters to erase.

        .. warning::

           Even though *ALL* of the VTXXX manuals state that character
           attributes **should be reset to defaults**, ``libvte``,
           ``xterm`` and ``ROTE`` completely ignore this. Same applies
           too all ``erase_*()`` and ``delete_*()`` methods.
        """
        count = count or 1

        for column in range(self.cursor.x,
                            min(self.cursor.x + count, self.columns)):
            self[self.cursor.y][column] = self.cursor.attrs

    def erase_in_line(self, type_of=0, private=False):
        """Erases a line in a specific way.

        :param int type_of: defines the way the line should be erased in:

            * ``0`` -- Erases from cursor to end of line, including cursor
              position.
            * ``1`` -- Erases from beginning of line to cursor,
              including cursor position.
            * ``2`` -- Erases complete line.
        :param bool private: when ``True`` character attributes aren left
                             unchanged **not implemented**.
        """
        interval = (
            # a) erase from the cursor to the end of line, including
            # the cursor,
            range(self.cursor.x, self.columns),
            # b) erase from the beginning of the line to the cursor,
            # including it,
            range(0, self.cursor.x + 1),
            # c) erase the entire line.
            range(0, self.columns)
        )[type_of]

        for column in interval:
            self[self.cursor.y][column] = self.cursor.attrs

    def erase_in_display(self, type_of=0, private=False):
        """Erases display in a specific way.

        :param int type_of: defines the way the line should be erased in:

            * ``0`` -- Erases from cursor to end of screen, including
              cursor position.
            * ``1`` -- Erases from beginning of screen to cursor,
              including cursor position.
            * ``2`` -- Erases complete display. All lines are erased
              and changed to single-width. Cursor does not move.
        :param bool private: when ``True`` character attributes aren left
                             unchanged **not implemented**.
        """
        interval = (
            # a) erase from cursor to the end of the display, including
            # the cursor,
            range(self.cursor.y + 1, self.lines),
            # b) erase from the beginning of the display to the cursor,
            # including it,
            range(0, self.cursor.y),
            # c) erase the whole display.
            range(0, self.lines)
        )[type_of]

        for line in interval:
            self[line][:] = \
                (self.cursor.attrs for _ in range(self.columns))

        # In case of 0 or 1 we have to erase the line with the cursor.
        if type_of in [0, 1]:
            self.erase_in_line(type_of)

    def set_tab_stop(self):
        """Sest a horizontal tab stop at cursor position."""
        self.tabstops.add(self.cursor.x)

    def clear_tab_stop(self, type_of=None):
        """Clears a horizontal tab stop in a specific way, depending
        on the ``type_of`` value:

        * ``0`` or nothing -- Clears a horizontal tab stop at cursor
          position.
        * ``3`` -- Clears all horizontal tab stops.
        """
        if not type_of:
            # Clears a horizontal tab stop at cursor position, if it's
            # present, or silently fails if otherwise.
            self.tabstops.discard(self.cursor.x)
        elif type_of == 3:
            self.tabstops = set()  # Clears all horizontal tab stops.

    def ensure_bounds(self, use_margins=None):
        """Ensure that current cursor position is within screen bounds.

        :param bool use_margins: when ``True`` or when
                                 :data:`~pyte.modes.DECOM` is set,
                                 cursor is bounded by top and and bottom
                                 margins, instead of ``[0; lines - 1]``.
        """
        if use_margins or mo.DECOM in self.mode:
            top, bottom = self.margins
        else:
            top, bottom = 0, self.lines - 1

        self.cursor.x = min(max(0, self.cursor.x), self.columns - 1)
        self.cursor.y = min(max(top, self.cursor.y), bottom)

    def cursor_up(self, count=None):
        """Moves cursor up the indicated # of lines in same column.
        Cursor stops at top margin.

        :param int count: number of lines to skip.
        """
        self.cursor.y -= count or 1
        self.ensure_bounds(use_margins=True)

    def cursor_up1(self, count=None):
        """Moves cursor up the indicated # of lines to column 1. Cursor
        stops at bottom margin.

        :param int count: number of lines to skip.
        """
        self.cursor_up(count)
        self.carriage_return()

    def cursor_down(self, count=None):
        """Moves cursor down the indicated # of lines in same column.
        Cursor stops at bottom margin.

        :param int count: number of lines to skip.
        """
        self.cursor.y += count or 1
        self.ensure_bounds(use_margins=True)

    def cursor_down1(self, count=None):
        """Moves cursor down the indicated # of lines to column 1.
        Cursor stops at bottom margin.

        :param int count: number of lines to skip.
        """
        self.cursor_down(count)
        self.carriage_return()

    def cursor_back(self, count=None):
        """Moves cursor left the indicated # of columns. Cursor stops
        at left margin.

        :param int count: number of columns to skip.
        """
        self.cursor.x -= count or 1
        self.ensure_bounds()

    def cursor_forward(self, count=None):
        """Moves cursor right the indicated # of columns. Cursor stops
        at right margin.

        :param int count: number of columns to skip.
        """
        self.cursor.x += count or 1
        self.ensure_bounds()

    def cursor_position(self, line=None, column=None):
        """Set the cursor to a specific `line` and `column`.

        Cursor is allowed to move out of the scrolling region only when
        :data:`~pyte.modes.DECOM` is reset, otherwise -- the position
        doesn't change.

        :param int line: line number to move the cursor to.
        :param int column: column number to move the cursor to.
        """
        column = (column or 1) - 1
        line = (line or 1) - 1

        # If origin mode (DECOM) is set, line number are relative to
        # the top scrolling margin.
        if mo.DECOM in self.mode:
            line += self.margins.top

            # Cursor is not allowed to move out of the scrolling region.
            if not self.margins.top <= line <= self.margins.bottom:
                return

        self.cursor.x, self.cursor.y = column, line
        self.ensure_bounds()

    def cursor_to_column(self, column=None):
        """Moves cursor to a specific column in the current line.

        :param int column: column number to move the cursor to.
        """
        self.cursor.x = (column or 1) - 1
        self.ensure_bounds()

    def cursor_to_line(self, line=None):
        """Moves cursor to a specific line in the current column.

        :param int line: line number to move the cursor to.
        """
        self.cursor.y = (line or 1) - 1

        # If origin mode (DECOM) is set, line number are relative to
        # the top scrolling margin.
        if mo.DECOM in self.mode:
            self.cursor.y += self.margins.top

            # FIXME: should we also restrict the cursor to the scrolling
            # region?

        self.ensure_bounds()

    def bell(self, *args):
        """Bell stub -- the actual implementation should probably be
        provided by the end-user.
        """

    def alignment_display(self):
        """Fills screen with uppercase E's for screen focus and alignment."""
        for line in self:
            for column, char in enumerate(line):
                line[column] = char._replace(data="E")

    def select_graphic_rendition(self, *attrs):
        """Set display attributes.

        :param list attrs: a list of display attributes to set.
        """
        replace = {}

        for attr in attrs or [0]:
            if attr in g.FG:
                replace[b"fg"] = g.FG[attr]
            elif attr in g.BG:
                replace[b"bg"] = g.BG[attr]
            elif attr in g.TEXT:
                attr = g.TEXT[attr]
                replace[attr[1:]] = attr.startswith("+")
            elif not attr:
                replace = self.default_char._asdict()

        self.cursor.attrs = self.cursor.attrs._replace(**replace)


class DiffScreen(Screen):
    """A screen subclass, which maintains a set of dirty lines in its
    :attr:`dirty` attribute. The end user is responsible for emptying
    a set, when a diff is applied.

    .. attribute:: dirty

       A set of line numbers, which should be re-drawn.

       >>> screen = DiffScreen(80, 24)
       >>> screen.dirty.clear()
       >>> screen.draw(u"!")
       >>> screen.dirty
       set([0])
    """
    def __init__(self, *args):
        self.dirty = set()
        super(DiffScreen, self).__init__(*args)

    def set_mode(self, *modes, **kwargs):
        if mo.DECSCNM >> 5 in modes and kwargs.get("private"):
            self.dirty.update(range(self.lines))
        super(DiffScreen, self).set_mode(*modes, **kwargs)

    def reset_mode(self, *modes, **kwargs):
        if mo.DECSCNM >> 5 in modes and kwargs.get("private"):
            self.dirty.update(range(self.lines))
        super(DiffScreen, self).reset_mode(*modes, **kwargs)

    def reset(self):
        self.dirty.update(range(self.lines))
        super(DiffScreen, self).reset()

    def resize(self, *args, **kwargs):
        self.dirty.update(range(self.lines))
        super(DiffScreen, self).resize(*args, **kwargs)

    def draw(self, *args):
        self.dirty.add(self.cursor.y)
        super(DiffScreen, self).draw(*args)

    def index(self):
        if self.cursor.y == self.margins.bottom:
            self.dirty.update(range(self.lines))

        super(DiffScreen, self).index()

    def reverse_index(self):
        if self.cursor.y == self.margins.top:
            self.dirty.update(range(self.lines))

        super(DiffScreen, self).reverse_index()

    def insert_lines(self, *args):
        self.dirty.update(range(self.cursor.y, self.lines))
        super(DiffScreen, self).insert_lines(*args)

    def delete_lines(self, *args):
        self.dirty.update(range(self.cursor.y, self.lines))
        super(DiffScreen, self).delete_lines(*args)

    def insert_characters(self, *args):
        self.dirty.add(self.cursor.y)
        super(DiffScreen, self).insert_characters(*args)

    def delete_characters(self, *args):
        self.dirty.add(self.cursor.y)
        super(DiffScreen, self).delete_characters(*args)

    def erase_characters(self, *args):
        self.dirty.add(self.cursor.y)
        super(DiffScreen, self).erase_characters(*args)

    def erase_in_line(self, *args):
        self.dirty.add(self.cursor.y)
        super(DiffScreen, self).erase_in_line(*args)

    def erase_in_display(self, type_of=0):
        self.dirty.update((
            range(self.cursor.y + 1, self.lines),
            range(0, self.cursor.y),
            range(0, self.lines)
        )[type_of])
        super(DiffScreen, self).erase_in_display(type_of)

    def alignment_display(self):
        self.dirty.update(range(self.lines))
        super(DiffScreen, self).alignment_display()


History = namedtuple("History", "top bottom ratio size position")


class HistoryScreen(DiffScreen):
    """A screen subclass, which keeps track of screen history and allows
    pagination. This is not linux-specific, but still useful; see  page
    462 of VT520 User's Manual.

    :param int history: total number of history lines to keep; is split
                        between top and bottom queues.
    :param int ratio: defines how much lines to scroll on :meth:`next_page`
                      and :meth:`prev_page` calls.

    .. attribute:: history

       A pair of history queues for top and bottom margins accordingly;
       here's the overall screen structure::

            [ 1: .......]
            [ 2: .......]  <- top history
            [ 3: .......]
            ------------
            [ 4: .......]  s
            [ 5: .......]  c
            [ 6: .......]  r
            [ 7: .......]  e
            [ 8: .......]  e
            [ 9: .......]  n
            ------------
            [10: .......]
            [11: .......]  <- bottom history
            [12: .......]

    .. note::

       Don't forget to update :class:`~pyte.streams.Stream` class with
       appropriate escape sequences -- you can use any, since pagination
       protocol is not standardized, for example::

           Stream.escape["N"] = "next_page"
           Stream.escape["P"] = "prev_page"
    """

    def __init__(self, columns, lines, history=100, ratio=.5):
        self.history = History(deque(maxlen=history // 2),
                               deque(maxlen=history),
                               float(ratio),
                               history,
                               history)

        super(HistoryScreen, self).__init__(columns, lines)

    def __before__(self, command):
        """Ensures a screen is at the bottom of the history buffer."""
        if command not in ["prev_page", "next_page"]:
            while self.history.position < self.history.size:
                self.next_page()

        super(HistoryScreen, self).__before__(command)

    def __after__(self, command):
        """Ensures all lines on a screen have proper width (attr:`columns`).

        Extra characters are truncated, missing characters are filled
        with whitespace.
        """
        if command in ["prev_page", "next_page"]:
            for idx, line in enumerate(self):
                if len(line) > self.columns:
                    self[idx] = line[:self.columns]
                elif len(line) < self.columns:
                    self[idx] = line + take(self.columns - len(line),
                                            self.default_line)

        # If we're at the bottom of the history buffer and `DECTCEM`
        # mode is set -- show the cursor.
        self.cursor.hidden = not (
            abs(self.history.position - self.history.size) < self.lines and
            mo.DECTCEM in self.mode
        )

        super(HistoryScreen, self).__after__(command)

    def reset(self):
        """Overloaded to reset screen history state: history position
        is reset to bottom of both queues;  queues themselves are
        emptied.
        """
        super(HistoryScreen, self).reset()

        self.history.top.clear()
        self.history.bottom.clear()
        self.history = self.history._replace(position=self.history.size)

    def index(self):
        """Overloaded to update top history with the removed lines."""
        top, bottom = self.margins

        if self.cursor.y == bottom:
            self.history.top.append(self[top])

        super(HistoryScreen, self).index()

    def reverse_index(self):
        """Overloaded to update bottom history with the removed lines."""
        top, bottom = self.margins

        if self.cursor.y == top:
            self.history.bottom.append(self[bottom])

        super(HistoryScreen, self).reverse_index()

    def prev_page(self):
        """Moves the screen page up through the history buffer. Page
        size is defined by ``history.ratio``, so for instance
        ``ratio = .5`` means that half the screen is restored from
        history on page switch.
        """
        if self.history.position > self.lines and self.history.top:
            mid = min(len(self.history.top),
                      int(math.ceil(self.lines * self.history.ratio)))

            self.history.bottom.extendleft(reversed(self[-mid:]))
            self.history = self.history \
                ._replace(position=self.history.position - self.lines)

            self[:] = list(reversed([
                self.history.top.pop() for _ in range(mid)
            ])) + self[:-mid]

            self.dirty = set(range(self.lines))

    def next_page(self):
        """Moves the screen page down through the history buffer."""
        if self.history.position < self.history.size and self.history.bottom:
            mid = min(len(self.history.bottom),
                      int(math.ceil(self.lines * self.history.ratio)))

            self.history.top.extend(self[:mid])
            self.history = self.history \
                ._replace(position=self.history.position + self.lines)

            self[:] = self[mid:] + [
                self.history.bottom.popleft() for _ in range(mid)
            ]

            self.dirty = set(range(self.lines))

########NEW FILE########
__FILENAME__ = streams
# -*- coding: utf-8 -*-
"""
    pyte.streams
    ~~~~~~~~~~~~

    This module provides three stream implementations with different
    features; for starters, here's a quick example of how streams are
    typically used:

    >>> import pyte
    >>>
    >>> class Dummy(object):
    ...     def __init__(self):
    ...         self.y = 0
    ...
    ...     def cursor_up(self, count=None):
    ...         self.y += count or 1
    ...
    >>> dummy = Dummy()
    >>> stream = pyte.Stream()
    >>> stream.attach(dummy)
    >>> stream.feed(u"\u001B[5A")  # Move the cursor up 5 rows.
    >>> dummy.y
    5

    :copyright: (c) 2011 by Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import absolute_import, unicode_literals

import codecs
import sys

from . import control as ctrl, escape as esc


class Stream(object):
    """A stream is a state machine that parses a stream of characters
    and dispatches events based on what it sees.

    .. note::

       Stream only accepts unicode strings as input, but if, for some
       reason, you need to feed it with byte strings, consider using
       :class:`~pyte.streams.ByteStream` instead.

    .. seealso::

        `man console_codes <http://linux.die.net/man/4/console_codes>`_
            For details on console codes listed bellow in :attr:`basic`,
            :attr:`escape`, :attr:`csi` and :attr:`sharp`.
    """

    #: Control sequences, which don't require any arguments.
    basic = {
        ctrl.BEL: "bell",
        ctrl.BS: "backspace",
        ctrl.HT: "tab",
        ctrl.LF: "linefeed",
        ctrl.VT: "linefeed",
        ctrl.FF: "linefeed",
        ctrl.CR: "carriage_return",
        ctrl.SO: "shift_out",
        ctrl.SI: "shift_in",
    }

    #: non-CSI escape sequences.
    escape = {
        esc.RIS: "reset",
        esc.IND: "index",
        esc.NEL: "linefeed",
        esc.RI: "reverse_index",
        esc.HTS: "set_tab_stop",
        esc.DECSC: "save_cursor",
        esc.DECRC: "restore_cursor",
    }

    #: "sharp" escape sequences -- ``ESC # <N>``.
    sharp = {
        esc.DECALN: "alignment_display",
    }

    #: CSI escape sequences -- ``CSI P1;P2;...;Pn <fn>``.
    csi = {
        esc.ICH: "insert_characters",
        esc.CUU: "cursor_up",
        esc.CUD: "cursor_down",
        esc.CUF: "cursor_forward",
        esc.CUB: "cursor_back",
        esc.CNL: "cursor_down1",
        esc.CPL: "cursor_up1",
        esc.CHA: "cursor_to_column",
        esc.CUP: "cursor_position",
        esc.ED: "erase_in_display",
        esc.EL: "erase_in_line",
        esc.IL: "insert_lines",
        esc.DL: "delete_lines",
        esc.DCH: "delete_characters",
        esc.ECH: "erase_characters",
        esc.HPR: "cursor_forward",
        esc.VPA: "cursor_to_line",
        esc.VPR: "cursor_down",
        esc.HVP: "cursor_position",
        esc.TBC: "clear_tab_stop",
        esc.SM: "set_mode",
        esc.RM: "reset_mode",
        esc.SGR: "select_graphic_rendition",
        esc.DECSTBM: "set_margins",
        esc.HPA: "cursor_to_column",
    }

    def __init__(self):
        self.handlers = {
            "stream": self._stream,
            "escape": self._escape,
            "arguments": self._arguments,
            "sharp": self._sharp,
            "charset": self._charset
        }

        self.listeners = []
        self.reset()

    def reset(self):
        """Reset state to ``"stream"`` and empty parameter attributes."""
        self.state = "stream"
        self.flags = {}
        self.params = []
        self.current = ""

    def consume(self, char):
        """Consume a single unicode character and advance the state as
        necessary.

        :param unicode char: a unicode character to consume.
        """
        if not isinstance(char, unicode):
            raise TypeError(
                "%s requires unicode input" % self.__class__.__name__)

        try:
            self.handlers.get(self.state)(char)
        except TypeError:
            pass
        except KeyError:
            if __debug__:
                self.flags[b"state"] = self.state
                self.flags[b"unhandled"] = char
                self.dispatch("debug", *self.params)
                self.reset()
            else:
                raise

    def feed(self, chars):
        """Consume a unicode string and advance the state as necessary.

        :param unicode chars: a unicode string to feed from.
        """
        if not isinstance(chars, unicode):
            raise TypeError(
                "%s requires unicode input" % self.__class__.__name__)

        for char in chars: self.consume(char)

    def attach(self, screen, only=()):
        """Adds a given screen to the listeners queue.

        :param pyte.screens.Screen screen: a screen to attach to.
        :param list only: a list of events you want to dispatch to a
                          given screen (empty by default, which means
                          -- dispatch all events).
        """
        self.listeners.append((screen, set(only)))

    def detach(self, screen):
        """Removes a given screen from the listeners queue and failes
        silently if it's not attached.

        :param pyte.screens.Screen screen: a screen to detach.
        """
        for idx, (listener, _) in enumerate(self.listeners):
            if screen is listener:
                self.listeners.pop(idx)

    def dispatch(self, event, *args, **kwargs):
        """Dispatch an event.

        Event handlers are looked up implicitly in the listeners'
        ``__dict__``, so, if a listener only wants to handle ``DRAW``
        events it should define a ``draw()`` method or pass
        ``only=["draw"]`` argument to :meth:`attach`.

        .. warning::

           If any of the attached listeners throws an exception, the
           subsequent callbacks are be aborted.

        :param unicode event: event to dispatch.
        :param list args: arguments to pass to event handlers.
        """
        for listener, only in self.listeners:
            if only and event not in only:
                continue

            try:
                handler = getattr(listener, event)
            except AttributeError:
                continue

            if hasattr(listener, "__before__"):
                listener.__before__(event)
            try:
                handler(*args, **self.flags)
            except Exception, e:
                # wuub: unicode keys in dict caused problems on OSX 
                # when used as **kwds, all of them should be fixed now
                print("HandlerException", repr(e), handler, args, self.flags)

            if hasattr(listener, "__after__"):
                listener.__after__(event)
        else:
            if kwargs.get("reset", True): self.reset()

    # State transformers.
    # ...................

    def _stream(self, char):
        """Process a character when in the default ``"stream"`` state."""
        if char in self.basic:
            self.dispatch(self.basic[char])
        elif char == ctrl.ESC:
            self.state = "escape"
        elif char == ctrl.CSI:
            self.state = "arguments"
        elif char not in [ctrl.NUL, ctrl.DEL]:
            self.dispatch("draw", char)

    def _escape(self, char):
        """Handle characters seen when in an escape sequence.

        Most non-VT52 commands start with a left-bracket after the
        escape and then a stream of parameters and a command; with
        a single notable exception -- :data:`escape.DECOM` sequence,
        which starts with a sharp.
        """
        if char == "#":
            self.state = "sharp"
        elif char == "[":
            self.state = "arguments"
        elif char in "()":
            self.state = "charset"
            self.flags[b"mode"] = char
        else:
            self.dispatch(self.escape[char])

    def _sharp(self, char):
        """Parse arguments of a `"#"` seqence."""
        self.dispatch(self.sharp[char])

    def _charset(self, char):
        """Parse ``G0`` or ``G1`` charset code."""
        self.dispatch("set_charset", char)

    def _arguments(self, char):
        """Parse arguments of an escape sequence.

        All parameters are unsigned, positive decimal integers, with
        the most significant digit sent first. Any parameter greater
        than 9999 is set to 9999. If you do not specify a value, a 0
        value is assumed.

        .. seealso::

           `VT102 User Guide <http://vt100.net/docs/vt102-ug/>`_
               For details on the formatting of escape arguments.

           `VT220 Programmer Reference <http://http://vt100.net/docs/vt220-rm/>`_
               For details on the characters valid for use as arguments.
        """
        if char == "?":
            self.flags[b"private"] = True
        elif char in [ctrl.BEL, ctrl.BS, ctrl.HT, ctrl.LF, ctrl.VT,
                      ctrl.FF, ctrl.CR]:
            # Not sure why, but those seem to be allowed between CSI
            # sequence arguments.
            self.dispatch(self.basic[char], reset=False)
        elif char == ctrl.SP:
            pass
        elif char in [ctrl.CAN, ctrl.SUB]:
            # If CAN or SUB is received during a sequence, the current
            # sequence is aborted; terminal displays the substitute
            # character, followed by characters in the sequence received
            # after CAN or SUB.
            self.dispatch("draw", char)
            self.state = "stream"
        elif char.isdigit():
            self.current += char
        else:
            self.params.append(min(int(self.current or 0), 9999))

            if char == ";":
                self.current = ""
            else:
                self.dispatch(self.csi[char], *self.params)


class ByteStream(Stream):
    """A stream, which takes bytes strings (instead of unicode) as input
    and tries to decode them using a given list of possible encodings.
    It uses :class:`codecs.IncrementalDecoder` internally, so broken
    bytes is not an issue.

    By default, the following decoding strategy is used:

    * First, try strict ``"utf-8"``, proceed if recieved and
      :exc:`UnicodeDecodeError` ...
    * Try strict ``"cp437"``, failed? move on ...
    * Use ``"utf-8"`` with invalid bytes replaced -- this one will
      allways succeed.

    >>> stream = ByteStream()
    >>> stream.feed(b"foo".decode("utf-8"))
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "pyte/streams.py", line 323, in feed
        "%s requires input in bytes" % self.__class__.__name__)
    TypeError: ByteStream requires input in bytes
    >>> stream.feed(b"foo")

    :param list encodings: a list of ``(encoding, errors)`` pairs,
                           where the first element is encoding name,
                           ex: ``"utf-8"`` and second defines how
                           decoding errors should be handeld; see
                           :meth:`str.decode` for possible values.
    """

    def __init__(self, encodings=None):
        encodings = encodings or [
            ("utf-8", "strict"),
            ("cp437", "strict"),
            ("utf-8", "replace")
        ]

        self.buffer = b"", 0
        self.decoders = [codecs.getincrementaldecoder(encoding)(errors)
                         for encoding, errors in encodings]

        super(ByteStream, self).__init__()

    def feed(self, chars):
        if not isinstance(chars, bytes):
            raise TypeError(
                "%s requires input in bytes" % self.__class__.__name__)

        for decoder in self.decoders:
            decoder.setstate(self.buffer)

            try:
                chars = decoder.decode(chars)
            except UnicodeDecodeError:
                continue

            self.buffer = decoder.getstate()
            return super(ByteStream, self).feed(chars)
        else:
            raise


class DebugStream(ByteStream):
    """Stream, which dumps a subset of the dispatched events to a given
    file-like object (:data:`sys.stdout` by default).

    >>> stream = DebugStream()
    >>> stream.feed("\x1b[1;24r\x1b[4l\x1b[24;1H\x1b[0;10m")
    SET_MARGINS 1; 24
    RESET_MODE 4
    CURSOR_POSITION 24; 1
    SELECT_GRAPHIC_RENDITION 0; 10

    :param file to: a file-like object to write debug information to.
    :param list only: a list of events you want to debug (empty by
                      default, which means -- debug all events).
    """

    def __init__(self, to=sys.stdout, only=(), *args, **kwargs):
        super(DebugStream, self).__init__(*args, **kwargs)

        def safestr(chunk):
            if isinstance(chunk, unicode):
                chunk = chunk.encode("utf-8")
            elif not isinstance(chunk, str):
                chunk = str(chunk)

            return chunk

        def write(chunk):
            to.write(safestr(chunk))

        class Bugger(object):
            __before__ = __after__ = lambda *args: None

            def __getattr__(self, event):
                def inner(*args, **flags):
                    write(event.upper() + " ")
                    write("; ".join(safestr(args)))
                    write(" ")
                    write(", ".join("{0}: {1}".format(name, safestr(arg))
                                    for name, arg in flags.iteritems()))
                    write("\n")
                return inner

        self.attach(Bugger(), only=only)

########NEW FILE########
__FILENAME__ = __main__
# -*- coding: utf-8 -*-
"""
    pyte
    ~~~~

    Command-line tool for "disassembling" escape and CSI sequences::

        $ echo -e "\e[Jfoo" | python -m pyte
        ERASE_IN_DISPLAY 0
        DRAW f
        DRAW o
        DRAW o
        LINEFEED

        $ python -m pyte foo
        DRAW f
        DRAW o
        DRAW o

    :copyright: (c) 2011 by Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
"""

if __name__ == "__main__":
    import sys
    import pyte

    if len(sys.argv) is 1:
        pyte.dis(sys.stdin.read())
    else:
        pyte.dis("".join(sys.argv[1:]))

########NEW FILE########
__FILENAME__ = sublimepty
import sublime
import sublime_plugin
import os
from process import Supervisor, SublimeView, PtyProcess, Win32Process

SUPERVISOR = Supervisor()
ON_WINDOWS = os.name == "nt" 

def read_all():
    SUPERVISOR.read_all()
    sublime.set_timeout(read_all, 200)

read_all()

def process(id):
    return SUPERVISOR.process(id)

class OpenPty(sublime_plugin.WindowCommand):
    def run(self, shell=None, encodings=None, title="TERMINAL"):
        sv = SublimeView()
        sv.view.set_name(title);
        if ON_WINDOWS:
            proc = Win32Process(SUPERVISOR)
        else:
            proc = PtyProcess(SUPERVISOR, cmd = shell, encodings = encodings)
        proc.attach_view(sv)
        proc.start()
########NEW FILE########
__FILENAME__ = sublime_keypress
import sublime_plugin

import sublimepty

class SublimeptyKeypress(sublime_plugin.TextCommand):
    def run(self, edit, key, ctrl=False, alt=False, shift=False, super=False):
        process_id = self.view.settings().get("sublimepty_id")
        process = sublimepty.process(process_id)
        if not process:
            return
        process.send_keypress(key, ctrl, alt, shift, super)


class SublimeptyClick(sublime_plugin.TextCommand):
    def run(self, edit, **kwds):
        process_id = self.view.settings().get("sublimepty_id")
        process = sublimepty.process(process_id)
        row, col = self.view.rowcol(self.view.sel()[0].a) # Thanks quarnster
        print("sublimeclik", row, col)
        if not process:
            return
        process.send_click(row, col, **kwds)
########NEW FILE########
