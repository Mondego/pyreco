__FILENAME__ = debug_me

def simple_func(x):
    x += 1

    s = range(20)
    z = None
    w = ()

    y = dict((i, i**2) for i in s)

    k = set(range(5, 99))

    try:
        x.invalid
    except AttributeError:
        pass

    #import sys
    #sys.exit(1)

    return 2*x

def fermat(n):
    """Returns triplets of the form x^n + y^n = z^n.
    Warning! Untested with n > 2.
    """

    # source: "Fermat's last Python script"
    # https://earthboundkid.jottit.com/fermat.py
    # :)

    for x in range(100):
        for y in range(1, x+1):
            for z in range(1, x**n+y**n + 1):
                if x**n + y**n == z**n:
                    yield x, y, z

print("SF %s" % simple_func(10))

for i in fermat(2):
    print(i)

print("FINISHED")

########NEW FILE########
__FILENAME__ = example-stringifier
#!/usr/bin/env python
"""
This file shows how you can define a custom stringifier for PuDB.

A stringifier is a function that is called on the variables in the namespace
for display in the variables list.  The default is type()*, as this is fast and
cannot fail.  PuDB also includes built-in options for using str() and repr().

Note that str() and repr() will be slower than type(), which is especially
noticable when you have many varialbes, or some of your variables have very
large string/repr representations.

Also note that if you just want to change the type for one or two variables,
you can do that by selecting the variable in the variables list and pressing
Enter, or by pressing t, s, or r.

To define a custom stringifier, create a file like this one with a function
called pudb_stringifier() at the module level.  pudb_stringifier(obj) should
return a string value for an object (note that str() will always be called on
the result). Note that the file will be execfile'd.

Then, go to the PuDB preferences window (type Ctrl-p inside of
PuDB), and add the path to the file in the "Custom" field under the "Variable
Stringifier" heading.

The example in this file returns the string value, unless it take more than 500
ms (1 second in Python 2.5-) to compute, in which case it falls back to the
type.

TIP: Run "python -m pudb.run example-stringifier.py and set this file to be
your stringifier in the settings to see how it works.

You can use custom stringifiers to do all sorts of things: callbacks, custom
views on variables of interest without having to use a watch variable or the
expanded view, etc.

* - Actually, the default is a mix between type() and str().  str() is used for
    a handful of "safe" types for which it is guaranteed to be fast and not to
    fail.
"""
import time
import signal
import sys
import math

class TimeOutError(Exception):
    pass

def timeout(signum, frame, time):
    raise TimeOutError("Timed out after %d seconds" % time)

def run_with_timeout(code, time, globals=None):
    """
    Evaluate ``code``, timing out after ``time`` seconds.

    In Python 2.5 and lower, ``time`` is rounded up to the nearest integer.
    The return value is whatever ``code`` returns.
    """
    # Set the signal handler and a ``time``-second alarm
    signal.signal(signal.SIGALRM, lambda s, f: timeout(s, f, time))
    if sys.version_info > (2, 5):
        signal.setitimer(signal.ITIMER_REAL, time)
    else:
        # The above only exists in Python 2.6+
        # Otherwise, we have to use this, which only supports integer arguments
        # Use math.ceil to round a float up.
        time = int(math.ceil(time))
        signal.alarm(time)
    r = eval(code, globals)
    signal.alarm(0)          # Disable the alarm
    return r

def pudb_stringifier(obj):
    """
    This is the custom stringifier.

    It returns str(obj), unless it take more than a second to compute,
    in which case it falls back to type(obj).
    """
    try:
        return run_with_timeout("str(obj)", 0.5, {'obj':obj})
    except TimeOutError:
        return (type(obj), "(str too slow to compute)")

# Example usage

class FastString(object):
    def __str__(self):
        return "This was fast to compute."

class SlowString(object):
    def __str__(self):
        time.sleep(10) # Return the string value after ten seconds
        return "This was slow to compute."

fast = FastString()
slow = SlowString()

# If you are running this in PuDB, set this file as your custom stringifier in
# the prefs (Ctrl-p) and run to here. Notice how fast shows the string value,
# but slow shows the type, as the string value takes too long to compute.

########NEW FILE########
__FILENAME__ = example-theme
# Supported 16 color values:
#   'h0' (color number 0) through 'h15' (color number 15)
#    or
#   'default' (use the terminal's default foreground),
#   'black', 'dark red', 'dark green', 'brown', 'dark blue',
#   'dark magenta', 'dark cyan', 'light gray', 'dark gray',
#   'light red', 'light green', 'yellow', 'light blue',
#   'light magenta', 'light cyan', 'white'
#
# Supported 256 color values:
#   'h0' (color number 0) through 'h255' (color number 255)
#
# 256 color chart: http://en.wikipedia.org/wiki/File:Xterm_color_chart.png
#
# "setting_name": (foreground_color, background_color),

# See pudb/theme.py
# (https://github.com/inducer/pudb/blob/master/pudb/theme.py) to see what keys
# there are.

# Note, be sure to test your theme in both curses and raw mode (see the bottom
# of the preferences window). Curses mode will be used with screen or tmux.

palette.update({
    "source": (add_setting("black", "underline"), "dark green"),
    "comment": ("h250", "default")
    })

########NEW FILE########
__FILENAME__ = b
import sys

from pudb import _get_debugger, set_interrupt_handler

def __myimport__(name, *args, **kwargs):
    if name == 'pudb.b':
        set_trace()
    return __origimport__(name, *args, **kwargs)

# Will only be run on first import
__builtins__['__origimport__'] = __import__
__builtins__['__import__'] = __myimport__

def set_trace():
    dbg = _get_debugger()
    set_interrupt_handler()
    dbg.set_trace(sys._getframe().f_back.f_back)

set_trace()

########NEW FILE########
__FILENAME__ = debugger
#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
import urwid
import bdb
import sys
import os

from pudb.settings import load_config, save_config
CONFIG = load_config()
save_config(CONFIG)

from pudb.py3compat import PY3, raw_input
if PY3:
    _next = "__next__"
else:
    _next = "next"

try:
    from functools import partial
except ImportError:
    def partial(func, *args, **keywords):
        def newfunc(*fargs, **fkeywords):
            newkeywords = keywords.copy()
            newkeywords.update(fkeywords)
            return func(*(args + fargs), **newkeywords)
        newfunc.func = func
        newfunc.args = args
        newfunc.keywords = keywords
        return newfunc

HELP_TEXT = """\
Welcome to PuDB, the Python Urwid debugger.
-------------------------------------------

(This help screen is scrollable. Hit Page Down to see more.)

Keys:
    Ctrl-p - edit preferences

    n - step over ("next")
    s - step into
    c - continue
    r/f - finish current function
    t - run to cursor
    e - show traceback [post-mortem or in exception state]

    H - move to current line (bottom of stack)
    u - move up one stack frame
    d - move down one stack frame

    o - show console/output screen

    b - toggle breakpoint
    m - open module

    j/k - up/down
    Ctrl-u/d - page up/down
    h/l - scroll left/right
    g/G - start/end
    L - show (file/line) location / go to line
    / - search
    ,/. - search next/previous

    V - focus variables
    S - focus stack
    B - focus breakpoint list
    C - focus code

    f1/?/H - show this help screen
    q - quit

    Ctrl-c - when in continue mode, break back to PuDB

    Ctrl-l - redraw screen

Command line-related:
    ! - invoke configured python command line in current environment
    Ctrl-x - toggle inline command line focus

    +/- - grow/shrink inline command line (active in command line history)
    _/= - minimize/maximize inline command line (active in command line history)

    Ctrl-v - insert newline
    Ctrl-n/p - browse command line history
    Tab - yes, there is (simple) tab completion

Sidebar-related (active in sidebar):
    +/- - grow/shrink sidebar
    _/= - minimize/maximize sidebar
    [/] - grow/shrink relative size of active sidebar box

Keys in variables list:
    \ - expand/collapse
    t/r/s/c - show type/repr/str/custom for this variable
    h - toggle highlighting
    @ - toggle repetition at top
    * - toggle private members
    w - toggle line wrapping
    n/insert - add new watch expression
    enter - edit options (also to delete)

Keys in stack list:

    enter - jump to frame

Keys in breakpoints view:

    enter - edit breakpoint
    d - delete breakpoint
    e - enable/disable breakpoint

License:
--------

PuDB is licensed to you under the MIT/X Consortium license:

Copyright (c) 2009-13 Andreas Kloeckner and contributors

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""


# {{{ debugger interface

class Debugger(bdb.Bdb):
    def __init__(self, steal_output=False):
        bdb.Bdb.__init__(self)
        self.ui = DebuggerUI(self)
        self.steal_output = steal_output

        self.setup_state()

        if steal_output:
            raise NotImplementedError("output stealing")
            if PY3:
                from io import StringIO
            else:
                from cStringIO import StringIO
            self.stolen_output = sys.stderr = sys.stdout = StringIO()
            sys.stdin = StringIO("")  # avoid spurious hangs

        from pudb.settings import load_breakpoints
        for bpoint_descr in load_breakpoints():
            self.set_break(*bpoint_descr)

    def set_trace(self, frame=None):
        """Start debugging from `frame`.

        If frame is not specified, debugging starts from caller's frame.

        This is exactly the same as Bdb.set_trace(), sans the self.reset() call.
        """
        if frame is None:
            frame = sys._getframe().f_back
        # See pudb issue #52. If this works well enough we should upstream to
        # stdlib bdb.py.
        #self.reset()
        while frame:
            frame.f_trace = self.trace_dispatch
            self.botframe = frame
            frame = frame.f_back
        self.set_step()
        sys.settrace(self.trace_dispatch)

    def save_breakpoints(self):
        from pudb.settings import save_breakpoints
        save_breakpoints([
            bp
            for fn, bp_lst in self.get_all_breaks().items()
            for lineno in bp_lst
            for bp in self.get_breaks(fn, lineno)
            if not bp.temporary])

    def enter_post_mortem(self, exc_tuple):
        self.post_mortem = True

    def setup_state(self):
        self.bottom_frame = None
        self.mainpyfile = ''
        self._wait_for_mainpyfile = False
        self.current_bp = None
        self.post_mortem = False

    def restart(self):
        from linecache import checkcache
        checkcache()
        self.ui.set_source_code_provider(NullSourceCodeProvider())
        self.setup_state()

    def do_clear(self, arg):
        self.clear_bpbynumber(int(arg))

    def set_frame_index(self, index):
        self.curindex = index
        if index < 0 or index >= len(self.stack):
            return

        self.curframe, lineno = self.stack[index]

        filename = self.curframe.f_code.co_filename

        import linecache
        if not linecache.getlines(filename):
            code = self.curframe.f_globals.get("_MODULE_SOURCE_CODE")
            if code is not None:
                self.ui.set_current_line(lineno,
                        DirectSourceCodeProvider(
                            self.curframe.f_code.co_name, code))
            else:
                self.ui.set_current_line(lineno,
                        NullSourceCodeProvider())

        else:
            self.ui.set_current_line(lineno,
                FileSourceCodeProvider(self, filename))

        self.ui.update_var_view()
        self.ui.update_stack()

        self.ui.stack_list._w.set_focus(self.ui.translate_ui_stack_index(index))

    def move_up_frame(self):
        if self.curindex > 0:
            self.set_frame_index(self.curindex-1)

    def move_down_frame(self):
        if self.curindex < len(self.stack)-1:
            self.set_frame_index(self.curindex+1)

    def get_shortened_stack(self, frame, tb):
        stack, index = self.get_stack(frame, tb)

        for i, (s_frame, lineno) in enumerate(stack):
            if s_frame is self.bottom_frame and index >= i:
                stack = stack[i:]
                index -= i

        return stack, index

    def interaction(self, frame, exc_tuple=None, show_exc_dialog=True):
        if exc_tuple is None:
            tb = None
        else:
            tb = exc_tuple[2]

        if frame is None and tb is not None:
            frame = tb.tb_frame

        found_bottom_frame = False
        walk_frame = frame
        while True:
            if walk_frame is self.bottom_frame:
                found_bottom_frame = True
                break
            if walk_frame is None:
                break
            walk_frame = walk_frame.f_back

        if not found_bottom_frame and not self.post_mortem:
            return

        self.stack, index = self.get_shortened_stack(frame, tb)

        if self.post_mortem:
            index = len(self.stack)-1

        self.set_frame_index(index)

        self.ui.call_with_ui(self.ui.interaction, exc_tuple,
                show_exc_dialog=show_exc_dialog)

    def get_stack_situation_id(self):
        return str(id(self.stack[self.curindex][0].f_code))

    def user_call(self, frame, argument_list):
        """This method is called when there is the remote possibility
        that we ever need to stop in this function."""
        if self._wait_for_mainpyfile:
            return
        if self.stop_here(frame):
            self.interaction(frame)

    def user_line(self, frame):
        """This function is called when we stop or break at this line."""
        if "__exc_tuple__" in frame.f_locals:
            del frame.f_locals['__exc_tuple__']

        if self._wait_for_mainpyfile:
            if (self.mainpyfile != self.canonic(frame.f_code.co_filename)
                    or frame.f_lineno <= 0):
                return
            self._wait_for_mainpyfile = False
            self.bottom_frame = frame

        if self.get_break(self.canonic(frame.f_code.co_filename), frame.f_lineno):
            self.current_bp = (
                    self.canonic(frame.f_code.co_filename), frame.f_lineno)
        else:
            self.current_bp = None
        self.ui.update_breakpoints()

        self.interaction(frame)

    def user_return(self, frame, return_value):
        """This function is called when a return trap is set here."""
        frame.f_locals['__return__'] = return_value

        if self._wait_for_mainpyfile:
            if (self.mainpyfile != self.canonic(frame.f_code.co_filename)
                    or frame.f_lineno <= 0):
                return
            self._wait_for_mainpyfile = False
            self.bottom_frame = frame

        if "__exc_tuple__" not in frame.f_locals:
            self.interaction(frame)

    def user_exception(self, frame, exc_tuple):
        """This function is called if an exception occurs,
        but only if we are to stop at or just below this level."""
        frame.f_locals['__exc_tuple__'] = exc_tuple

        if not self._wait_for_mainpyfile:
            self.interaction(frame, exc_tuple)

    def _runscript(self, filename):
        # Start with fresh empty copy of globals and locals and tell the script
        # that it's being run as __main__ to avoid scripts being able to access
        # the debugger's namespace.
        globals_ = {"__name__": "__main__", "__file__": filename}
        locals_ = globals_

        # When bdb sets tracing, a number of call and line events happens
        # BEFORE debugger even reaches user's code (and the exact sequence of
        # events depends on python version). So we take special measures to
        # avoid stopping before we reach the main script (see user_line and
        # user_call for details).
        self._wait_for_mainpyfile = 1
        self.mainpyfile = self.canonic(filename)
        if PY3:
            statement = 'exec(compile(open("%s").read(), "%s", "exec"))' % (
                    filename, filename)
        else:
            statement = 'execfile( "%s")' % filename

        # Set up an interrupt handler
        from pudb import set_interrupt_handler
        set_interrupt_handler()

        self.run(statement, globals=globals_, locals=locals_)

# }}}


# UI stuff --------------------------------------------------------------------

from pudb.ui_tools import make_hotkey_markup, labelled_value, \
        SelectableText, SignalWrap, StackFrame, BreakpointFrame

from pudb.var_view import FrameVarInfoKeeper


# {{{ display setup

try:
    import curses
except ImportError:
    curses = None


want_curses_display = (
        CONFIG["display"] == "curses"
        or (
            CONFIG["display"] == "auto"
            and
            not os.environ.get("TERM", "").startswith("xterm")))

from urwid.raw_display import Screen as RawScreen
if want_curses_display:
    try:
        from urwid.curses_display import Screen
    except ImportError:
        Screen = RawScreen
else:
    Screen = RawScreen

del want_curses_display


class ThreadsafeScreen(Screen):
    "A Screen subclass that doesn't crash when running from a non-main thread."

    def signal_init(self):
        "Initialize signal handler, ignoring errors silently."
        try:
            super(ThreadsafeScreen, self).signal_init()
        except ValueError:
            pass

    def signal_restore(self):
        "Restore default signal handler, ignoring errors silently."
        try:
            super(ThreadsafeScreen, self).signal_restore()
        except ValueError:
            pass

# }}}


# {{{ source code providers

class SourceCodeProvider(object):
    def __ne__(self, other):
        return not (self == other)


class NullSourceCodeProvider(SourceCodeProvider):
    def __eq__(self, other):
        return type(self) == type(other)

    def identifier(self):
        return "<no source code>"

    def get_breakpoint_source_identifier(self):
        return None

    def clear_cache(self):
        pass

    def get_lines(self, debugger_ui):
        from pudb.source_view import SourceLine
        return [
                SourceLine(debugger_ui, "<no source code available>"),
                SourceLine(debugger_ui, ""),
                SourceLine(debugger_ui, "If this is generated code and you would "
                    "like the source code to show up here,"),
                SourceLine(debugger_ui, "simply set the attribute "
                    "_MODULE_SOURCE_CODE in the module in which this function"),
                SourceLine(debugger_ui, "was compiled to a string containing "
                    "the code."),
                ]


class FileSourceCodeProvider(SourceCodeProvider):
    def __init__(self, debugger, file_name):
        self.file_name = debugger.canonic(file_name)

    def __eq__(self, other):
        return (
                type(self) == type(other)
                and
                self.file_name == other.file_name)

    def identifier(self):
        return self.file_name

    def get_breakpoint_source_identifier(self):
        return self.file_name

    def clear_cache(self):
        from linecache import clearcache
        clearcache()

    def get_lines(self, debugger_ui):
        from pudb.source_view import SourceLine, format_source

        if self.file_name == "<string>":
            return [SourceLine(self, self.file_name)]

        breakpoints = debugger_ui.debugger.get_file_breaks(self.file_name)
        try:
            from linecache import getlines
            lines = getlines(self.file_name)

            from pudb.lowlevel import detect_encoding
            source_enc, _ = detect_encoding(getattr(iter(lines), _next))

            decoded_lines = []
            for l in lines:
                if hasattr(l, "decode"):
                    decoded_lines.append(l.decode(source_enc))
                else:
                    decoded_lines.append(l)

            return format_source(debugger_ui, decoded_lines, set(breakpoints))
        except:
            from pudb.lowlevel import format_exception
            debugger_ui.message("Could not load source file '%s':\n\n%s" % (
                self.file_name, "".join(format_exception(sys.exc_info()))),
                title="Source Code Load Error")
            return [SourceLine(self,
                "Error while loading '%s'." % self.file_name)]


class DirectSourceCodeProvider(SourceCodeProvider):
    def __init__(self, func_name, code):
        self.function_name = func_name
        self.code = code

    def __eq__(self, other):
        return (
                type(self) == type(other)
                and
                self.function_name == other.function_name
                and
                self.code is other.code)

    def identifier(self):
        return "<source code of function %s>" % self.function_name

    def get_breakpoint_source_identifier(self):
        return None

    def clear_cache(self):
        pass

    def get_lines(self, debugger_ui):
        from pudb.source_view import format_source

        lines = self.code.split("\n")

        from pudb.lowlevel import detect_encoding
        source_enc, _ = detect_encoding(getattr(iter(lines), _next))

        decoded_lines = []
        for i, l in enumerate(lines):
            if hasattr(l, "decode"):
                l = l.decode(source_enc)
            else:
                l = l.decode(source_enc)

            if i+1 < len(lines):
                l += "\n"

            decoded_lines.append(l)

        return format_source(debugger_ui, decoded_lines, set())

# }}}


class DebuggerUI(FrameVarInfoKeeper):
    # {{{ constructor

    def __init__(self, dbg):
        FrameVarInfoKeeper.__init__(self)

        self.debugger = dbg

        from urwid import AttrMap

        from pudb.ui_tools import SearchController
        self.search_controller = SearchController(self)

        self.last_module_filter = ""

        # {{{ build ui

        # {{{ left/source column

        self.source = urwid.SimpleListWalker([])
        self.source_list = urwid.ListBox(self.source)
        self.source_sigwrap = SignalWrap(self.source_list)
        self.source_attr = urwid.AttrMap(self.source_sigwrap, "source")
        self.source_hscroll_start = 0

        self.cmdline_history = []
        self.cmdline_history_position = -1

        self.cmdline_contents = urwid.SimpleFocusListWalker([])
        self.cmdline_list = urwid.ListBox(self.cmdline_contents)
        self.cmdline_edit = urwid.Edit([
            ("command line prompt", ">>> ")
            ])
        cmdline_edit_attr = urwid.AttrMap(self.cmdline_edit, "command line edit")
        self.cmdline_edit_sigwrap = SignalWrap(
                cmdline_edit_attr, is_preemptive=True)

        def clear_cmdline_history(btn):
            del self.cmdline_contents[:]

        self.cmdline_edit_bar = urwid.Columns([
                self.cmdline_edit_sigwrap,
                ("fixed", 10, AttrMap(
                    urwid.Button("Clear", clear_cmdline_history),
                    "command line clear button", "command line focused button"))
                ])

        self.cmdline_pile = urwid.Pile([
            ("flow", urwid.Text("Command line: [Ctrl-X]")),
            ("weight", 1, urwid.AttrMap(self.cmdline_list, "command line output")),
            ("flow", self.cmdline_edit_bar),
            ])
        self.cmdline_sigwrap = SignalWrap(
                urwid.AttrMap(self.cmdline_pile, None, "focused sidebar")
                )

        self.lhs_col = urwid.Pile([
            ("weight", 5, self.source_attr),
            ("weight", 1, self.cmdline_sigwrap),
            ])

        # }}}

        # {{{ right column

        self.locals = urwid.SimpleListWalker([])
        self.var_list = SignalWrap(
                urwid.ListBox(self.locals))

        self.stack_walker = urwid.SimpleListWalker([])
        self.stack_list = SignalWrap(
                urwid.ListBox(self.stack_walker))

        self.bp_walker = urwid.SimpleListWalker([])
        self.bp_list = SignalWrap(
                urwid.ListBox(self.bp_walker))

        self.rhs_col = urwid.Pile([
            ("weight", float(CONFIG["variables_weight"]), AttrMap(urwid.Pile([
                ("flow", urwid.Text(make_hotkey_markup("_Variables:"))),
                AttrMap(self.var_list, "variables"),
                ]), None, "focused sidebar"),),
            ("weight", float(CONFIG["stack_weight"]), AttrMap(urwid.Pile([
                ("flow", urwid.Text(make_hotkey_markup("_Stack:"))),
                AttrMap(self.stack_list, "stack"),
                ]), None, "focused sidebar"),),
            ("weight", float(CONFIG["breakpoints_weight"]), AttrMap(urwid.Pile([
                ("flow", urwid.Text(make_hotkey_markup("_Breakpoints:"))),
                AttrMap(self.bp_list, "breakpoint"),
                ]), None, "focused sidebar"),),
            ])
        self.rhs_col_sigwrap = SignalWrap(self.rhs_col)

        # }}}

        self.columns = urwid.Columns(
                    [
                        ("weight", 1, self.lhs_col),
                        ("weight", float(CONFIG["sidebar_width"]),
                            self.rhs_col_sigwrap),
                        ],
                    dividechars=1)

        self.caption = urwid.Text("")
        header = urwid.AttrMap(self.caption, "header")
        self.top = SignalWrap(urwid.Frame(
            urwid.AttrMap(self.columns, "background"),
            header))

        # }}}

        def change_rhs_box(name, index, direction, w, size, key):
            from pudb.settings import save_config

            _, weight = self.rhs_col.item_types[index]

            if direction < 0:
                if weight > 1/5:
                    weight /= 1.25
            else:
                if weight < 5:
                    weight *= 1.25

            CONFIG[name+"_weight"] = weight
            save_config(CONFIG)
            self.rhs_col.item_types[index] = "weight", weight
            self.rhs_col._invalidate()

        # {{{ variables listeners

        def change_var_state(w, size, key):
            var, pos = self.var_list._w.get_focus()

            iinfo = self.get_frame_var_info(read_only=False) \
                    .get_inspect_info(var.id_path, read_only=False)

            if key == "\\":
                iinfo.show_detail = not iinfo.show_detail
            elif key == "t":
                iinfo.display_type = "type"
            elif key == "r":
                iinfo.display_type = "repr"
            elif key == "s":
                iinfo.display_type = "str"
            elif key == "c":
                iinfo.display_type = CONFIG["custom_stringifier"]
            elif key == "h":
                iinfo.highlighted = not iinfo.highlighted
            elif key == "@":
                iinfo.repeated_at_top = not iinfo.repeated_at_top
            elif key == "*":
                iinfo.show_private_members = not iinfo.show_private_members
            elif key == "w":
                iinfo.wrap = not iinfo.wrap

            self.update_var_view()

        def edit_inspector_detail(w, size, key):
            var, pos = self.var_list._w.get_focus()

            if var is None:
                return

            fvi = self.get_frame_var_info(read_only=False)
            iinfo = fvi.get_inspect_info(var.id_path, read_only=False)

            buttons = [
                ("OK", True),
                ("Cancel", False),
                ]

            if var.watch_expr is not None:
                watch_edit = urwid.Edit([
                    ("label", "Watch expression: ")
                    ], var.watch_expr.expression)
                id_segment = [urwid.AttrMap(watch_edit, "value"), urwid.Text("")]

                buttons.extend([None, ("Delete", "del")])

                title = "Watch Expression Options"
            else:
                id_segment = [
                        labelled_value("Identifier Path: ", var.id_path),
                        urwid.Text(""),
                        ]

                title = "Variable Inspection Options"

            rb_grp = []
            rb_show_type = urwid.RadioButton(rb_grp, "Show Type",
                    iinfo.display_type == "type")
            rb_show_repr = urwid.RadioButton(rb_grp, "Show repr()",
                    iinfo.display_type == "repr")
            rb_show_str = urwid.RadioButton(rb_grp, "Show str()",
                    iinfo.display_type == "str")
            rb_show_custom = urwid.RadioButton(rb_grp, "Show custom (set in prefs)",
                    iinfo.display_type == CONFIG["custom_stringifier"])

            wrap_checkbox = urwid.CheckBox("Line Wrap", iinfo.wrap)
            expanded_checkbox = urwid.CheckBox("Expanded", iinfo.show_detail)
            highlighted_checkbox = urwid.CheckBox("Highlighted", iinfo.highlighted)
            repeated_at_top_checkbox = urwid.CheckBox(
                    "Repeated at top", iinfo.repeated_at_top)
            show_private_checkbox = urwid.CheckBox(
                    "Show private members", iinfo.show_private_members)

            lb = urwid.ListBox(urwid.SimpleListWalker(
                id_segment+rb_grp+[
                    urwid.Text(""),
                    wrap_checkbox,
                    expanded_checkbox,
                    highlighted_checkbox,
                    repeated_at_top_checkbox,
                    show_private_checkbox,
                ]))

            result = self.dialog(lb, buttons, title=title)

            if result is True:
                iinfo.show_detail = expanded_checkbox.get_state()
                iinfo.wrap = wrap_checkbox.get_state()
                iinfo.highlighted = highlighted_checkbox.get_state()
                iinfo.repeated_at_top = repeated_at_top_checkbox.get_state()
                iinfo.show_private_members = show_private_checkbox.get_state()

                if rb_show_type.get_state():
                    iinfo.display_type = "type"
                elif rb_show_repr.get_state():
                    iinfo.display_type = "repr"
                elif rb_show_str.get_state():
                    iinfo.display_type = "str"
                elif rb_show_custom.get_state():
                    iinfo.display_type = CONFIG["custom_stringifier"]

                if var.watch_expr is not None:
                    var.watch_expr.expression = watch_edit.get_edit_text()

            elif result == "del":
                for i, watch_expr in enumerate(fvi.watches):
                    if watch_expr is var.watch_expr:
                        del fvi.watches[i]

            self.update_var_view()

        def insert_watch(w, size, key):
            watch_edit = urwid.Edit([
                ("label", "Watch expression: ")
                ])

            if self.dialog(
                    urwid.ListBox(urwid.SimpleListWalker([
                        urwid.AttrMap(watch_edit, "value")
                        ])),
                    [
                        ("OK", True),
                        ("Cancel", False),
                        ], title="Add Watch Expression"):

                from pudb.var_view import WatchExpression
                we = WatchExpression(watch_edit.get_edit_text())
                fvi = self.get_frame_var_info(read_only=False)
                fvi.watches.append(we)
                self.update_var_view()

        self.var_list.listen("\\", change_var_state)
        self.var_list.listen("t", change_var_state)
        self.var_list.listen("r", change_var_state)
        self.var_list.listen("s", change_var_state)
        self.var_list.listen("c", change_var_state)
        self.var_list.listen("h", change_var_state)
        self.var_list.listen("@", change_var_state)
        self.var_list.listen("*", change_var_state)
        self.var_list.listen("w", change_var_state)
        self.var_list.listen("enter", edit_inspector_detail)
        self.var_list.listen("n", insert_watch)
        self.var_list.listen("insert", insert_watch)

        self.var_list.listen("[", partial(change_rhs_box, 'variables', 0, -1))
        self.var_list.listen("]", partial(change_rhs_box, 'variables', 0, 1))

        # }}}

        # {{{ stack listeners
        def examine_frame(w, size, key):
            _, pos = self.stack_list._w.get_focus()
            self.debugger.set_frame_index(self.translate_ui_stack_index(pos))

        self.stack_list.listen("enter", examine_frame)

        def move_stack_top(w, size, key):
            self.debugger.set_frame_index(len(self.debugger.stack)-1)

        def move_stack_up(w, size, key):
            self.debugger.move_up_frame()

        def move_stack_down(w, size, key):
            self.debugger.move_down_frame()

        self.stack_list.listen("H", move_stack_top)
        self.stack_list.listen("u", move_stack_up)
        self.stack_list.listen("d", move_stack_down)

        self.stack_list.listen("[", partial(change_rhs_box, 'stack', 1, -1))
        self.stack_list.listen("]", partial(change_rhs_box, 'stack', 1, 1))

        # }}}

        # {{{ breakpoint listeners
        def save_breakpoints(w, size, key):
            self.debugger.save_breakpoints()

        def delete_breakpoint(w, size, key):
            bp_source_identifier = \
                    self.source_code_provider.get_breakpoint_source_identifier()

            if bp_source_identifier is None:
                self.message(
                    "Cannot currently delete a breakpoint here--"
                    "source code does not correspond to a file location. "
                    "(perhaps this is generated code)")

            bp_list = self._get_bp_list()
            if bp_list:
                _, pos = self.bp_list._w.get_focus()
                bp = bp_list[pos]
                if bp_source_identifier == bp.file and bp.line-1 < len(self.source):
                    self.source[bp.line-1].set_breakpoint(False)

                err = self.debugger.clear_break(bp.file, bp.line)
                if err:
                    self.message("Error clearing breakpoint:\n" + err)
                else:
                    self.update_breakpoints()

        def enable_disable_breakpoint(w, size, key):
            bp_entry, pos = self.bp_list._w.get_focus()

            if bp_entry is None:
                return

            bp = self._get_bp_list()[pos]
            bp.enabled = not bp.enabled

            self.update_breakpoints()

        def examine_breakpoint(w, size, key):
            bp_entry, pos = self.bp_list._w.get_focus()

            if bp_entry is None:
                return

            bp = self._get_bp_list()[pos]

            if bp.cond is None:
                cond = ""
            else:
                cond = str(bp.cond)

            enabled_checkbox = urwid.CheckBox(
                    "Enabled", bp.enabled)
            cond_edit = urwid.Edit([
                ("label", "Condition:               ")
                ], cond)
            ign_count_edit = urwid.IntEdit([
                ("label", "Ignore the next N times: ")
                ], bp.ignore)

            lb = urwid.ListBox(urwid.SimpleListWalker([
                labelled_value("File: ", bp.file),
                labelled_value("Line: ", bp.line),
                labelled_value("Hits: ", bp.hits),
                urwid.Text(""),
                enabled_checkbox,
                urwid.AttrMap(cond_edit, "value", "value"),
                urwid.AttrMap(ign_count_edit, "value", "value"),
                ]))

            result = self.dialog(lb, [
                ("OK", True),
                ("Cancel", False),
                None,
                ("Delete", "del"),
                ("Location", "loc"),
                ], title="Edit Breakpoint")

            if result is True:
                bp.enabled = enabled_checkbox.get_state()
                bp.ignore = int(ign_count_edit.value())
                cond = cond_edit.get_edit_text()
                if cond:
                    bp.cond = cond
                else:
                    bp.cond = None
            elif result == "loc":
                self.show_line(bp.line,
                        FileSourceCodeProvider(self.debugger, bp.file))
                self.columns.set_focus(0)
            elif result == "del":
                bp_source_identifier = \
                        self.source_code_provider.get_breakpoint_source_identifier()

                if bp_source_identifier is None:
                    self.message(
                        "Cannot currently delete a breakpoint here--"
                        "source code does not correspond to a file location. "
                        "(perhaps this is generated code)")

                if bp_source_identifier == bp.file:
                    self.source[bp.line-1].set_breakpoint(False)

                err = self.debugger.clear_break(bp.file, bp.line)
                if err:
                    self.message("Error clearing breakpoint:\n" + err)
                else:
                    self.update_breakpoints()

        self.bp_list.listen("enter", examine_breakpoint)
        self.bp_list.listen("d", delete_breakpoint)
        self.bp_list.listen("s", save_breakpoints)
        self.bp_list.listen("e", enable_disable_breakpoint)

        self.bp_list.listen("[", partial(change_rhs_box, 'breakpoints', 2, -1))
        self.bp_list.listen("]", partial(change_rhs_box, 'breakpoints', 2, 1))

        # }}}

        # {{{ source listeners

        def end():
            self.debugger.save_breakpoints()
            self.quit_event_loop = True

        def next(w, size, key):
            if self.debugger.post_mortem:
                self.message("Post-mortem mode: Can't modify state.")
            else:
                self.debugger.set_next(self.debugger.curframe)
                end()

        def step(w, size, key):
            if self.debugger.post_mortem:
                self.message("Post-mortem mode: Can't modify state.")
            else:
                self.debugger.set_step()
                end()

        def finish(w, size, key):
            if self.debugger.post_mortem:
                self.message("Post-mortem mode: Can't modify state.")
            else:
                self.debugger.set_return(self.debugger.curframe)
                end()

        def cont(w, size, key):
            if self.debugger.post_mortem:
                self.message("Post-mortem mode: Can't modify state.")
            else:
                self.debugger.set_continue()
                end()

        def run_to_cursor(w, size, key):
            if self.debugger.post_mortem:
                self.message("Post-mortem mode: Can't modify state.")
            else:
                sline, pos = self.source.get_focus()
                lineno = pos+1

                bp_source_identifier = \
                        self.source_code_provider.get_breakpoint_source_identifier()

                if bp_source_identifier is None:
                    self.message(
                        "Cannot currently set a breakpoint here--"
                        "source code does not correspond to a file location. "
                        "(perhaps this is generated code)")

                from pudb.lowlevel import get_breakpoint_invalid_reason
                invalid_reason = get_breakpoint_invalid_reason(
                        bp_source_identifier, lineno)

                if invalid_reason is not None:
                    self.message(
                        "Cannot run to the line you indicated, "
                        "for the following reason:\n\n"
                        + invalid_reason)
                else:
                    err = self.debugger.set_break(
                            bp_source_identifier, pos+1, temporary=True)
                    if err:
                        self.message("Error dealing with breakpoint:\n" + err)

                    self.debugger.set_continue()
                    end()

        def move_home(w, size, key):
            self.source.set_focus(0)

        def move_end(w, size, key):
            self.source.set_focus(len(self.source)-1)

        def go_to_line(w, size, key):
            _, line = self.source.get_focus()

            lineno_edit = urwid.IntEdit([
                ("label", "Line number: ")
                ], line+1)

            if self.dialog(
                    urwid.ListBox(urwid.SimpleListWalker([
                        labelled_value("File :",
                            self.source_code_provider.identifier()),
                        urwid.AttrMap(lineno_edit, "value")
                        ])),
                    [
                        ("OK", True),
                        ("Cancel", False),
                        ], title="Go to Line Number"):
                lineno = min(max(0, int(lineno_edit.value())-1), len(self.source)-1)
                self.source.set_focus(lineno)

        def move_down(w, size, key):
            w.keypress(size, "down")

        def move_up(w, size, key):
            w.keypress(size, "up")

        def page_down(w, size, key):
            w.keypress(size, "page down")

        def page_up(w, size, key):
            w.keypress(size, "page up")

        def scroll_left(w, size, key):
            self.source_hscroll_start = max(
                    0,
                    self.source_hscroll_start - 4)
            for sl in self.source:
                sl._invalidate()

        def scroll_right(w, size, key):
            self.source_hscroll_start += 4
            for sl in self.source:
                sl._invalidate()

        def search(w, size, key):
            self.search_controller.open_search_ui()

        def search_next(w, size, key):
            self.search_controller.perform_search(dir=1, update_search_start=True)

        def search_previous(w, size, key):
            self.search_controller.perform_search(dir=-1, update_search_start=True)

        def toggle_breakpoint(w, size, key):
            bp_source_identifier = \
                    self.source_code_provider.get_breakpoint_source_identifier()

            if bp_source_identifier:
                sline, pos = self.source.get_focus()
                lineno = pos+1

                existing_breaks = self.debugger.get_breaks(
                        bp_source_identifier, lineno)
                if existing_breaks:
                    err = self.debugger.clear_break(bp_source_identifier, lineno)
                    sline.set_breakpoint(False)
                else:
                    from pudb.lowlevel import get_breakpoint_invalid_reason
                    invalid_reason = get_breakpoint_invalid_reason(
                            bp_source_identifier, pos+1)

                    if invalid_reason is not None:
                        do_set = not self.dialog(
                                urwid.ListBox(urwid.SimpleListWalker([
                                    urwid.Text("The breakpoint you just set may be "
                                        "invalid, for the following reason:\n\n"
                                        + invalid_reason),
                                    ])), [
                                        ("Cancel", True),
                                        ("Set Anyway", False),
                                        ], title="Possibly Invalid Breakpoint",
                                    focus_buttons=True)
                    else:
                        do_set = True

                    if do_set:
                        err = self.debugger.set_break(bp_source_identifier, pos+1)
                        sline.set_breakpoint(True)
                    else:
                        err = None

                if err:
                    self.message("Error dealing with breakpoint:\n" + err)

                self.update_breakpoints()
            else:
                self.message(
                    "Cannot currently set a breakpoint here--"
                    "source code does not correspond to a file location. "
                    "(perhaps this is generated code)")

        def pick_module(w, size, key):
            from os.path import splitext

            import sys

            def mod_exists(mod):
                if not hasattr(mod, "__file__"):
                    return False
                filename = mod.__file__

                base, ext = splitext(filename)
                ext = ext.lower()

                from os.path import exists

                if ext == ".pyc":
                    return exists(base+".py")
                else:
                    return ext == ".py"

            new_mod_text = SelectableText("-- update me --")
            new_mod_entry = urwid.AttrMap(new_mod_text,
                    None, "focused selectable")

            def build_filtered_mod_list(filt_string=""):
                modules = sorted(name
                        for name, mod in sys.modules.items()
                        if mod_exists(mod))

                result = [urwid.AttrMap(SelectableText(mod),
                        None, "focused selectable")
                        for mod in modules if filt_string in mod]
                new_mod_text.set_text("<<< IMPORT MODULE '%s' >>>" % filt_string)
                result.append(new_mod_entry)
                return result

            def show_mod(mod):
                filename = self.debugger.canonic(mod.__file__)

                base, ext = splitext(filename)
                if ext == ".pyc":
                    ext = ".py"
                    filename = base+".py"

                self.set_source_code_provider(
                        FileSourceCodeProvider(self.debugger, filename))
                self.source_list.set_focus(0)

            class FilterEdit(urwid.Edit):
                def keypress(self, size, key):
                    result = urwid.Edit.keypress(self, size, key)

                    if result is None:
                        mod_list[:] = build_filtered_mod_list(
                                self.get_edit_text())

                    return result

            filt_edit = FilterEdit([("label", "Filter: ")],
                    self.last_module_filter)

            mod_list = urwid.SimpleListWalker(
                    build_filtered_mod_list(filt_edit.get_edit_text()))
            lb = urwid.ListBox(mod_list)

            w = urwid.Pile([
                ("flow", urwid.AttrMap(filt_edit, "value")),
                ("fixed", 1, urwid.SolidFill()),
                urwid.AttrMap(lb, "selectable")])

            while True:
                result = self.dialog(w, [
                    ("OK", True),
                    ("Cancel", False),
                    ("Reload", "reload"),

                    ], title="Pick Module")
                self.last_module_filter = filt_edit.get_edit_text()

                if result is True:
                    widget, pos = lb.get_focus()
                    if widget is new_mod_entry:
                        new_mod_name = filt_edit.get_edit_text()
                        try:
                            __import__(str(new_mod_name))
                        except:
                            from pudb.lowlevel import format_exception

                            self.message("Could not import module '%s':\n\n%s" % (
                                new_mod_name, "".join(
                                    format_exception(sys.exc_info()))),
                                title="Import Error")
                        else:
                            show_mod(sys.modules[str(new_mod_name)])
                            break
                    else:
                        show_mod(sys.modules[widget.base_widget.get_text()[0]])
                        break
                elif result is False:
                    break
                elif result == "reload":
                    widget, pos = lb.get_focus()
                    if widget is not new_mod_entry:
                        mod_name = widget.base_widget.get_text()[0]
                        mod = sys.modules[mod_name]
                        reload(mod)
                        self.message("'%s' was successfully reloaded." % mod_name)

                        if self.source_code_provider is not None:
                            self.source_code_provider.clear_cache()

                        self.set_source_code_provider(self.source_code_provider,
                                force_update=True)

                        _, pos = self.stack_list._w.get_focus()
                        self.debugger.set_frame_index(
                                self.translate_ui_stack_index(pos))

        self.source_sigwrap.listen("n", next)
        self.source_sigwrap.listen("s", step)
        self.source_sigwrap.listen("f", finish)
        self.source_sigwrap.listen("r", finish)
        self.source_sigwrap.listen("c", cont)
        self.source_sigwrap.listen("t", run_to_cursor)

        self.source_sigwrap.listen("j", move_down)
        self.source_sigwrap.listen("k", move_up)
        self.source_sigwrap.listen("ctrl d", page_down)
        self.source_sigwrap.listen("ctrl u", page_up)
        self.source_sigwrap.listen("ctrl f", page_down)
        self.source_sigwrap.listen("ctrl b", page_up)
        self.source_sigwrap.listen("h", scroll_left)
        self.source_sigwrap.listen("l", scroll_right)

        self.source_sigwrap.listen("/", search)
        self.source_sigwrap.listen(",", search_previous)
        self.source_sigwrap.listen(".", search_next)

        self.source_sigwrap.listen("home", move_home)
        self.source_sigwrap.listen("end", move_end)
        self.source_sigwrap.listen("g", move_home)
        self.source_sigwrap.listen("G", move_end)
        self.source_sigwrap.listen("L", go_to_line)

        self.source_sigwrap.listen("b", toggle_breakpoint)
        self.source_sigwrap.listen("m", pick_module)

        self.source_sigwrap.listen("H", move_stack_top)
        self.source_sigwrap.listen("u", move_stack_up)
        self.source_sigwrap.listen("d", move_stack_down)

        # }}}

        # {{{ command line listeners

        def cmdline_get_namespace():
            curframe = self.debugger.curframe

            from pudb.shell import SetPropagatingDict
            return SetPropagatingDict(
                    [curframe.f_locals, curframe.f_globals],
                    curframe.f_locals)

        def add_cmdline_content(s, attr):
            s = s.rstrip("\n")

            from pudb.ui_tools import SelectableText
            self.cmdline_contents.append(
                    urwid.AttrMap(SelectableText(s),
                        attr, "focused "+attr))

            # scroll to end of last entry
            self.cmdline_list.set_focus_valign("bottom")
            self.cmdline_list.set_focus(len(self.cmdline_contents) - 1,
                    coming_from="above")

        def cmdline_tab_complete(w, size, key):
            from rlcompleter import Completer

            text = self.cmdline_edit.edit_text
            pos = self.cmdline_edit.edit_pos

            chopped_text = text[:pos]
            suffix = text[pos:]

            # stolen from readline in the Python interactive shell
            delimiters = " \t\n`~!@#$%^&*()-=+[{]}\\|;:\'\",<>/?"

            complete_start_index = max(
                    chopped_text.rfind(delim_i)
                    for delim_i in delimiters)

            if complete_start_index == -1:
                prefix = ""
            else:
                prefix = chopped_text[:complete_start_index+1]
                chopped_text = chopped_text[complete_start_index+1:]

            state = 0
            chopped_completions = []
            completer = Completer(cmdline_get_namespace())
            while True:
                completion = completer.complete(chopped_text, state)

                if not isinstance(completion, str):
                    break

                chopped_completions.append(completion)
                state += 1

            def common_prefix(a, b):
                for i, (a_i, b_i) in enumerate(zip(a, b)):
                    if a_i != b_i:
                        return a[:i]

                return a[:max(len(a), len(b))]

            common_compl_prefix = None
            for completion in chopped_completions:
                if common_compl_prefix is None:
                    common_compl_prefix = completion
                else:
                    common_compl_prefix = common_prefix(
                            common_compl_prefix, completion)

            completed_chopped_text = common_compl_prefix

            if completed_chopped_text is None:
                return

            if (
                    len(completed_chopped_text) == len(chopped_text)
                    and len(chopped_completions) > 1):
                add_cmdline_content(
                        "   ".join(chopped_completions),
                        "command line output")
                return

            self.cmdline_edit.edit_text = \
                    prefix+completed_chopped_text+suffix
            self.cmdline_edit.edit_pos = len(prefix) + len(completed_chopped_text)

        def cmdline_append_newline(w, size, key):
            self.cmdline_edit.insert_text("\n")

        def cmdline_exec(w, size, key):
            cmd = self.cmdline_edit.get_edit_text()
            if not cmd:
                # blank command -> refuse service
                return

            add_cmdline_content(">>> " + cmd, "command line input")

            if not self.cmdline_history or cmd != self.cmdline_history[-1]:
                self.cmdline_history.append(cmd)

            self.cmdline_history_position = -1

            prev_sys_stdin = sys.stdin
            prev_sys_stdout = sys.stdout
            prev_sys_stderr = sys.stderr

            if PY3:
                from io import StringIO
            else:
                from cStringIO import StringIO

            sys.stdin = None
            sys.stderr = sys.stdout = StringIO()
            try:
                eval(compile(cmd, "<pudb command line>", 'single'),
                        cmdline_get_namespace())
            except:
                tp, val, tb = sys.exc_info()

                import traceback

                tblist = traceback.extract_tb(tb)
                del tblist[:1]
                tb_lines = traceback.format_list(tblist)
                if tb_lines:
                    tb_lines.insert(0, "Traceback (most recent call last):\n")
                tb_lines[len(tb_lines):] = traceback.format_exception_only(tp, val)

                add_cmdline_content("".join(tb_lines), "command line error")
            else:
                self.cmdline_edit.set_edit_text("")
            finally:
                if sys.stdout.getvalue():
                    add_cmdline_content(sys.stdout.getvalue(), "command line output")

                sys.stdin = prev_sys_stdin
                sys.stdout = prev_sys_stdout
                sys.stderr = prev_sys_stderr

        def cmdline_history_browse(direction):
            if self.cmdline_history_position == -1:
                self.cmdline_history_position = len(self.cmdline_history)

            self.cmdline_history_position += direction

            if 0 <= self.cmdline_history_position < len(self.cmdline_history):
                self.cmdline_edit.edit_text = \
                        self.cmdline_history[self.cmdline_history_position]
            else:
                self.cmdline_history_position = -1
                self.cmdline_edit.edit_text = ""
            self.cmdline_edit.edit_pos = len(self.cmdline_edit.edit_text)

        def cmdline_history_prev(w, size, key):
            cmdline_history_browse(-1)

        def cmdline_history_next(w, size, key):
            cmdline_history_browse(1)

        def toggle_cmdline_focus(w, size, key):
            self.columns.set_focus(self.lhs_col)
            if self.lhs_col.get_focus() is self.cmdline_sigwrap:
                self.lhs_col.set_focus(self.source_attr)
            else:
                self.cmdline_pile.set_focus(self.cmdline_edit_bar)
                self.lhs_col.set_focus(self.cmdline_sigwrap)

        self.cmdline_edit_sigwrap.listen("tab", cmdline_tab_complete)
        self.cmdline_edit_sigwrap.listen("ctrl v", cmdline_append_newline)
        self.cmdline_edit_sigwrap.listen("enter", cmdline_exec)
        self.cmdline_edit_sigwrap.listen("ctrl n", cmdline_history_next)
        self.cmdline_edit_sigwrap.listen("ctrl p", cmdline_history_prev)
        self.cmdline_edit_sigwrap.listen("esc", toggle_cmdline_focus)
        self.cmdline_edit_sigwrap.listen("ctrl d", toggle_cmdline_focus)

        self.top.listen("ctrl x", toggle_cmdline_focus)

        # {{{ command line sizing

        def max_cmdline(w, size, key):
            self.lhs_col.item_types[-1] = "weight", 5
            self.lhs_col._invalidate()

        def min_cmdline(w, size, key):
            self.lhs_col.item_types[-1] = "weight", 1/2
            self.lhs_col._invalidate()

        def grow_cmdline(w, size, key):
            _, weight = self.lhs_col.item_types[-1]

            if weight < 5:
                weight *= 1.25
                self.lhs_col.item_types[-1] = "weight", weight
                self.lhs_col._invalidate()

        def shrink_cmdline(w, size, key):
            _, weight = self.lhs_col.item_types[-1]

            if weight > 1/2:
                weight /= 1.25
                self.lhs_col.item_types[-1] = "weight", weight
                self.lhs_col._invalidate()

        self.cmdline_sigwrap.listen("=", max_cmdline)
        self.cmdline_sigwrap.listen("+", grow_cmdline)
        self.cmdline_sigwrap.listen("_", min_cmdline)
        self.cmdline_sigwrap.listen("-", shrink_cmdline)

        # }}}

        # }}}

        # {{{ sidebar sizing

        def max_sidebar(w, size, key):
            from pudb.settings import save_config

            weight = 5
            CONFIG["sidebar_width"] = weight
            save_config(CONFIG)

            self.columns.column_types[1] = "weight", weight
            self.columns._invalidate()

        def min_sidebar(w, size, key):
            from pudb.settings import save_config

            weight = 1/5
            CONFIG["sidebar_width"] = weight
            save_config(CONFIG)

            self.columns.column_types[1] = "weight", weight
            self.columns._invalidate()

        def grow_sidebar(w, size, key):
            from pudb.settings import save_config

            _, weight = self.columns.column_types[1]

            if weight < 5:
                weight *= 1.25
                CONFIG["sidebar_width"] = weight
                save_config(CONFIG)
                self.columns.column_types[1] = "weight", weight
                self.columns._invalidate()

        def shrink_sidebar(w, size, key):
            from pudb.settings import save_config

            _, weight = self.columns.column_types[1]

            if weight > 1/5:
                weight /= 1.25
                CONFIG["sidebar_width"] = weight
                save_config(CONFIG)
                self.columns.column_types[1] = "weight", weight
                self.columns._invalidate()

        self.rhs_col_sigwrap.listen("=", max_sidebar)
        self.rhs_col_sigwrap.listen("+", grow_sidebar)
        self.rhs_col_sigwrap.listen("_", min_sidebar)
        self.rhs_col_sigwrap.listen("-", shrink_sidebar)

        # }}}

        # {{{ top-level listeners

        def show_output(w, size, key):
            self.screen.stop()
            raw_input("Hit Enter to return:")
            self.screen.start()

        def reload_breakpoints(w, size, key):
            self.debugger.clear_all_breaks()
            from pudb.settings import load_breakpoints
            for bpoint_descr in load_breakpoints():
                dbg.set_break(*bpoint_descr)
            self.update_breakpoints()

        def show_traceback(w, size, key):
            if self.current_exc_tuple is not None:
                from pudb.lowlevel import format_exception

                result = self.dialog(
                        urwid.ListBox(urwid.SimpleListWalker([urwid.Text(
                            "".join(format_exception(self.current_exc_tuple)))])),
                        [
                            ("Close", "close"),
                            ("Location", "location")
                            ],
                        title="Exception Viewer",
                        focus_buttons=True,
                        bind_enter_esc=False)

                if result == "location":
                    self.debugger.set_frame_index(len(self.debugger.stack)-1)

            else:
                self.message("No exception available.")

        def run_external_cmdline(w, size, key):
            self.screen.stop()

            if not hasattr(self, "have_been_to_cmdline"):
                self.have_been_to_cmdline = True
                first_cmdline_run = True
            else:
                first_cmdline_run = False

            curframe = self.debugger.curframe

            import pudb.shell as shell
            if shell.HAVE_IPYTHON and CONFIG["shell"] == "ipython":
                runner = shell.run_ipython_shell
            elif shell.HAVE_BPYTHON and CONFIG["shell"] == "bpython":
                runner = shell.run_bpython_shell
            else:
                runner = shell.run_classic_shell

            runner(curframe.f_locals, curframe.f_globals,
                    first_cmdline_run)

            self.screen.start()

            self.update_var_view()

        def run_cmdline(w, size, key):
            if CONFIG["shell"] == "internal":
                return toggle_cmdline_focus(w, size, key)
            else:
                return run_external_cmdline(w, size, key)

        def focus_code(w, size, key):
            self.columns.set_focus(self.lhs_col)
            self.lhs_col.set_focus(self.source_attr)

        class RHColumnFocuser:
            def __init__(self, idx):
                self.idx = idx

            def __call__(subself, w, size, key):
                self.columns.set_focus(self.rhs_col_sigwrap)
                self.rhs_col.set_focus(self.rhs_col.widget_list[subself.idx])

        def quit(w, size, key):
            self.debugger.set_quit()
            end()

        def do_edit_config(w, size, key):
            self.run_edit_config()

        def redraw_screen(w, size, key):
            self.screen.clear()

        def help(w, size, key):
            self.message(HELP_TEXT, title="PuDB Help")

        self.top.listen("o", show_output)
        self.top.listen("ctrl r", reload_breakpoints)
        self.top.listen("!", run_cmdline)
        self.top.listen("e", show_traceback)

        self.top.listen("C", focus_code)
        self.top.listen("V", RHColumnFocuser(0))
        self.top.listen("S", RHColumnFocuser(1))
        self.top.listen("B", RHColumnFocuser(2))

        self.top.listen("q", quit)
        self.top.listen("ctrl p", do_edit_config)
        self.top.listen("ctrl l", redraw_screen)
        self.top.listen("f1", help)
        self.top.listen("?", help)

        # }}}

        # {{{ setup

        self.screen = ThreadsafeScreen()

        if curses:
            try:
                curses.setupterm()
            except:
                # Something went wrong--oh well. Nobody will die if their
                # 256 color support breaks. Just carry on without it.
                # https://github.com/inducer/pudb/issues/78
                pass
            else:
                color_support = curses.tigetnum('colors')

                if color_support == 256 and isinstance(self.screen, RawScreen):
                    self.screen.set_terminal_properties(256)

        self.setup_palette(self.screen)

        self.show_count = 0
        self.source_code_provider = None

        self.current_line = None

        self.quit_event_loop = False

        # }}}

    # }}}

    # {{{ UI helpers

    def translate_ui_stack_index(self, index):
        # note: self-inverse

        if CONFIG["current_stack_frame"] == "top":
            return len(self.debugger.stack)-1-index
        elif CONFIG["current_stack_frame"] == "bottom":
            return index
        else:
            raise ValueError("invalid value for 'current_stack_frame' pref")

    def message(self, msg, title="Message", **kwargs):
        self.call_with_ui(self.dialog,
                urwid.ListBox(urwid.SimpleListWalker([urwid.Text(msg)])),
                [("OK", True)], title=title, **kwargs)

    def run_edit_config(self):
        from pudb.settings import edit_config, save_config
        edit_config(self, CONFIG)
        save_config(CONFIG)

    def dialog(self, content, buttons_and_results,
            title=None, bind_enter_esc=True, focus_buttons=False,
            extra_bindings=[]):
        class ResultSetter:
            def __init__(subself, res):
                subself.res = res

            def __call__(subself, btn):
                self.quit_event_loop = [subself.res]

        Attr = urwid.AttrMap

        if bind_enter_esc:
            content = SignalWrap(content)

            def enter(w, size, key):
                self.quit_event_loop = [True]

            def esc(w, size, key):
                self.quit_event_loop = [False]

            content.listen("enter", enter)
            content.listen("esc", esc)

        button_widgets = []
        for btn_descr in buttons_and_results:
            if btn_descr is None:
                button_widgets.append(urwid.Text(""))
            else:
                btn_text, btn_result = btn_descr
                button_widgets.append(
                        Attr(urwid.Button(btn_text, ResultSetter(btn_result)),
                            "button", "focused button"))

        w = urwid.Columns([
            content,
            ("fixed", 15, urwid.ListBox(urwid.SimpleListWalker(button_widgets))),
            ], dividechars=1)

        if focus_buttons:
            w.set_focus_column(1)

        if title is not None:
            w = urwid.Pile([
                ("flow", urwid.AttrMap(
                    urwid.Text(title, align="center"),
                    "dialog title")),
                ("fixed", 1, urwid.SolidFill()),
                w])

        class ResultSetter:
            def __init__(subself, res):
                subself.res = res

            def __call__(subself, w, size, key):
                self.quit_event_loop = [subself.res]

        w = SignalWrap(w)
        for key, binding in extra_bindings:
            if isinstance(binding, str):
                w.listen(key, ResultSetter(binding))
            else:
                w.listen(key, binding)

        w = urwid.LineBox(w)

        w = urwid.Overlay(w, self.top,
                align="center",
                valign="middle",
                width=('relative', 75),
                height=('relative', 75),
                )
        w = Attr(w, "background")

        return self.event_loop(w)[0]

    @staticmethod
    def setup_palette(screen):
        may_use_fancy_formats = not hasattr(urwid.escape, "_fg_attr_xterm")

        from pudb.theme import get_palette
        screen.register_palette(
                get_palette(may_use_fancy_formats, CONFIG["theme"]))

    def show_exception_dialog(self, exc_tuple):
        from pudb.lowlevel import format_exception

        tb_txt = "".join(format_exception(exc_tuple))
        while True:
            res = self.dialog(
                    urwid.ListBox(urwid.SimpleListWalker([urwid.Text(
                        "The program has terminated abnormally because of "
                        "an exception.\n\n"
                        "A full traceback is below. You may recall this "
                        "traceback at any time using the 'e' key. "
                        "The debugger has entered post-mortem mode and will "
                        "prevent further state changes.\n\n"
                        + tb_txt)])),
                    title="Program Terminated for Uncaught Exception",
                    buttons_and_results=[
                        ("OK", True),
                        ("Save traceback", "save"),
                        ])

            if res in [True, False]:
                break

            if res == "save":
                try:
                    n = 0
                    from os.path import exists
                    while True:
                        if n:
                            fn = "traceback-%d.txt" % n
                        else:
                            fn = "traceback.txt"

                        if not exists(fn):
                            outf = open(fn, "w")
                            try:
                                outf.write(tb_txt)
                            finally:
                                outf.close()

                            self.message("Traceback saved as %s." % fn,
                                    title="Success")

                            break

                        n += 1

                except Exception:
                    io_tb_txt = "".join(format_exception(sys.exc_info()))
                    self.message(
                            "An error occurred while trying to write "
                            "the traceback:\n\n" + io_tb_txt,
                            title="I/O error")

    # }}}

    # {{{ UI enter/exit

    def show(self):
        if self.show_count == 0:
            self.screen.start()
        self.show_count += 1

    def hide(self):
        self.show_count -= 1
        if self.show_count == 0:
            self.screen.stop()

    def call_with_ui(self, f, *args, **kwargs):
        self.show()
        try:
            return f(*args, **kwargs)
        finally:
            self.hide()

    # }}}

    # {{{ interaction

    def event_loop(self, toplevel=None):
        prev_quit_loop = self.quit_event_loop

        try:
            import pygments  # noqa
        except ImportError:
            if not hasattr(self, "pygments_message_shown"):
                self.pygments_message_shown = True
                self.message("Package 'pygments' not found. "
                        "Syntax highlighting disabled.")

        WELCOME_LEVEL = "e022"
        if CONFIG["seen_welcome"] < WELCOME_LEVEL:
            CONFIG["seen_welcome"] = WELCOME_LEVEL
            from pudb import VERSION
            self.message("Welcome to PudB %s!\n\n"
                    "PuDB is a full-screen, console-based visual debugger for "
                    "Python.  Its goal is to provide all the niceties of modern "
                    "GUI-based debuggers in a more lightweight and "
                    "keyboard-friendly package. "
                    "PuDB allows you to debug code right where you write and test "
                    "it--in a terminal. If you've worked with the excellent "
                    "(but nowadays ancient) DOS-based Turbo Pascal or C tools, "
                    "PuDB's UI might look familiar.\n\n"
                    "If you're new here, welcome! The help screen "
                    "(invoked by hitting '?' after this message) should get you "
                    "on your way.\n"

                    "\nChanges in version 2014.1:\n\n"
                    "- Make prompt-on-quit optional (Mike Burr)\n"
                    "- Make tab completion in the built-in shell saner\n"
                    "- Fix handling of unicode source\n  (reported by Morten Nielsen and Buck Golemon)\n"

                    "\nChanges in version 2013.5.1:\n\n"
                    "- Fix loading of saved breakpoint conditions "
                    "(Antoine Dechaume)\n"
                    "- Fixes for built-in command line\n"
                    "- Theme updates\n"

                    "\nChanges in version 2013.5:\n\n"
                    "- Add command line window\n"
                    "- Uses curses display driver when appropriate\n"

                    "\nChanges in version 2013.4:\n\n"
                    "- Support for debugging generated code\n"

                    "\nChanges in version 2013.3.5:\n\n"
                    "- IPython fixes (Aaron Meurer)\n"
                    "- Py2/3 configuration fixes (Somchai Smythe)\n"
                    "- PyPy fixes (Julian Berman)\n"

                    "\nChanges in version 2013.3.4:\n\n"
                    "- Don't die if curses doesn't like what stdin/out are\n"
                    "  connected to.\n"

                    "\nChanges in version 2013.3.3:\n\n"
                    "- As soon as pudb is loaded, you can break to the debugger by\n"
                    "  evaluating the expression 'pu.db', where 'pu' is a new \n"
                    "  'builtin' that pudb has rudely shoved into the interpreter.\n"

                    "\nChanges in version 2013.3.2:\n\n"
                    "- Don't attempt to do signal handling if a signal handler\n"
                    "  is already set (Fix by Buck Golemon).\n"

                    "\nChanges in version 2013.3.1:\n\n"
                    "- Don't ship {ez,distribute}_setup at all.\n"
                    "  It breaks more than it helps.\n"

                    "\nChanges in version 2013.3:\n\n"
                    "- Switch to setuptools as a setup helper.\n"

                    "\nChanges in version 2013.2:\n\n"
                    "- Even more bug fixes.\n"

                    "\nChanges in version 2013.1:\n\n"
                    "- Ctrl-C will now break to the debugger in a way that does\n"
                    "  not terminate the program\n"
                    "- Lots of bugs fixed\n"

                    "\nChanges in version 2012.3:\n\n"
                    "- Python 3 support (contributed by Brad Froehle)\n"
                    "- Better search box behavior (suggested by Ram Rachum)\n"
                    "- Made it possible to go back and examine state from "
                    "'finished' window. (suggested by Aaron Meurer)\n"

                    "\nChanges in version 2012.2.1:\n\n"
                    "- Don't touch config files during install.\n"

                    "\nChanges in version 2012.2:\n\n"
                    "- Add support for BPython as a shell.\n"
                    "- You can now run 'python -m pudb script.py' on Py 2.6+.\n"
                    "  '-m pudb.run' still works--but it's four "
                    "keystrokes longer! :)\n"

                    "\nChanges in version 2012.1:\n\n"
                    "- Work around an API change in IPython 0.12.\n"

                    "\nChanges in version 2011.3.1:\n\n"
                    "- Work-around for bug in urwid >= 1.0.\n"

                    "\nChanges in version 2011.3:\n\n"
                    "- Finer-grained string highlighting "
                    "(contributed by Aaron Meurer)\n"
                    "- Prefs tweaks, instant-apply, top-down stack "
                    "(contributed by Aaron Meurer)\n"
                    "- Size changes in sidebar boxes (contributed by Aaron Meurer)\n"
                    "- New theme 'midnight' (contributed by Aaron Meurer)\n"
                    "- Support for IPython 0.11 (contributed by Chris Farrow)\n"
                    "- Suport for custom stringifiers "
                    "(contributed by Aaron Meurer)\n"
                    "- Line wrapping in variables view "
                    "(contributed by Aaron Meurer)\n"

                    "\nChanges in version 2011.2:\n\n"
                    "- Fix for post-mortem debugging (contributed by 'Sundance')\n"

                    "\nChanges in version 2011.1:\n\n"
                    "- Breakpoints saved between sessions\n"
                    "- A new 'dark vim' theme\n"
                    "(both contributed by Naveen Michaud-Agrawal)\n"

                    "\nChanges in version 0.93:\n\n"
                    "- Stored preferences (no more pesky IPython prompt!)\n"
                    "- Themes\n"
                    "- Line numbers (optional)\n"
                    % VERSION)
            from pudb.settings import save_config
            save_config(CONFIG)
            self.run_edit_config()

        try:
            if toplevel is None:
                toplevel = self.top

            self.size = self.screen.get_cols_rows()

            self.quit_event_loop = False

            while not self.quit_event_loop:
                canvas = toplevel.render(self.size, focus=True)
                self.screen.draw_screen(self.size, canvas)
                keys = self.screen.get_input()

                for k in keys:
                    if k == "window resize":
                        self.size = self.screen.get_cols_rows()
                    else:
                        toplevel.keypress(self.size, k)

            return self.quit_event_loop
        finally:
            self.quit_event_loop = prev_quit_loop

    # }}}

    # {{{ debugger-facing interface

    def interaction(self, exc_tuple, show_exc_dialog=True):
        self.current_exc_tuple = exc_tuple

        from pudb import VERSION
        caption = [(None,
            "PuDB %s - ?:help  n:next  s:step into  b:breakpoint  "
            "!:python command line"
            % VERSION)]

        if self.debugger.post_mortem:
            if show_exc_dialog and exc_tuple is not None:
                self.show_exception_dialog(exc_tuple)

            caption.extend([
                (None, " "),
                ("warning", "[POST-MORTEM MODE]")
                ])
        elif exc_tuple is not None:
            caption.extend([
                (None, " "),
                ("warning", "[PROCESSING EXCEPTION - hit 'e' to examine]")
                ])

        self.caption.set_text(caption)
        self.event_loop()

    def set_source_code_provider(self, source_code_provider, force_update=False):
        if self.source_code_provider != source_code_provider or force_update:
            self.source[:] = source_code_provider.get_lines(self)
            self.source_code_provider = source_code_provider
            self.current_line = None

    def show_line(self, line, source_code_provider=None):
        """Updates the UI so that a certain line is currently in view."""

        changed_file = False
        if source_code_provider is not None:
            changed_file = self.source_code_provider != source_code_provider
            self.set_source_code_provider(source_code_provider)

        line -= 1
        if line >= 0 and line < len(self.source):
            self.source_list.set_focus(line)
            if changed_file:
                self.source_list.set_focus_valign("middle")

    def set_current_line(self, line, source_code_provider):
        """Updates the UI to show the line currently being executed."""

        if self.current_line is not None:
            self.current_line.set_current(False)

        self.show_line(line, source_code_provider)

        line -= 1
        if line >= 0 and line < len(self.source):
            self.current_line = self.source[line]
            self.current_line.set_current(True)

    def update_var_view(self, locals=None, globals=None):
        if locals is None:
            locals = self.debugger.curframe.f_locals
        if globals is None:
            globals = self.debugger.curframe.f_globals

        from pudb.var_view import make_var_view
        self.locals[:] = make_var_view(
                self.get_frame_var_info(read_only=True),
                locals, globals)

    def _get_bp_list(self):
        return [bp
                for fn, bp_lst in self.debugger.get_all_breaks().items()
                for lineno in bp_lst
                for bp in self.debugger.get_breaks(fn, lineno)
                if not bp.temporary]

    def _format_fname(self, fname):
        from os.path import dirname, basename
        name = basename(fname)

        if name == "__init__.py":
            name = "..."+dirname(fname)[-10:]+"/"+name
        return name

    def update_breakpoints(self):
        self.bp_walker[:] = [
                BreakpointFrame(self.debugger.current_bp == (bp.file, bp.line),
                    self._format_fname(bp.file), bp.line)
                for bp in self._get_bp_list()]

    def update_stack(self):
        def make_frame_ui(frame_lineno):
            frame, lineno = frame_lineno

            code = frame.f_code

            class_name = None
            if code.co_argcount and code.co_varnames[0] == "self":
                try:
                    class_name = frame.f_locals["self"].__class__.__name__
                except:
                    pass

            return StackFrame(frame is self.debugger.curframe,
                    code.co_name, class_name,
                    self._format_fname(code.co_filename), lineno)

        frame_uis = [make_frame_ui(fl) for fl in self.debugger.stack]
        if CONFIG["current_stack_frame"] == "top":
            frame_uis = frame_uis[::-1]
        elif CONFIG["current_stack_frame"] == "bottom":
            pass
        else:
            raise ValueError("invalid value for 'current_stack_frame' pref")

        self.stack_walker[:] = frame_uis

    # }}}

# vim: foldmethod=marker:expandtab:softtabstop=4

########NEW FILE########
__FILENAME__ = ipython
from __future__ import with_statement

import sys
import os

try:
    from IPython import ipapi
    ip = ipapi.get()
    _ipython_version = (0, 10)
except ImportError:
    try:
        from IPython.core.magic import register_line_magic
        from IPython import get_ipython
        _ipython_version = (1, 0)
    except ImportError:
        # Note, keep this run last, or else it will raise a deprecation
        # warning.
        from IPython.frontend.terminal.interactiveshell import \
            TerminalInteractiveShell
        ip = TerminalInteractiveShell.instance()
        _ipython_version = (0, 11)


# This conforms to IPython version 0.10
def pudb_f_v10(self, arg):
    """ Debug a script (like %run -d) in the IPython process, using PuDB.

    Usage:

    %pudb test.py [args]
        Run script test.py under PuDB.
    """

    if not arg.strip():
        print(__doc__)
        return

    from IPython.genutils import arg_split
    args = arg_split(arg)

    path = os.path.abspath(args[0])
    args = args[1:]
    if not os.path.isfile(path):
        raise ipapi.UsageError("%%pudb: file %s does not exist" % path)

    from pudb import runscript
    ip.IP.history_saving_wrapper(lambda: runscript(path, args))()


# This conforms to IPython version 0.11
def pudb_f_v11(self, arg):
    """ Debug a script (like %run -d) in the IPython process, using PuDB.

    Usage:

    %pudb test.py [args]
        Run script test.py under PuDB.
    """

    # Get the running instance

    if not arg.strip():
        print(pudb_f_v11.__doc__)
        return

    from IPython.utils.process import arg_split
    args = arg_split(arg)

    path = os.path.abspath(args[0])
    args = args[1:]
    if not os.path.isfile(path):
        from IPython.core.error import UsageError
        raise UsageError("%%pudb: file %s does not exist" % path)

    from pudb import runscript
    runscript(path, args)


if _ipython_version == (1, 0):
    # For IPython 1.0.0
    def pudb(line):
        """
        Debug a script (like %run -d) in the IPython process, using PuDB.

        Usage:

        %pudb test.py [args]
            Run script test.py under PuDB.

        """

        # Get the running instance

        if not line.strip():
            print(pudb.__doc__)
            return

        from IPython.utils.process import arg_split
        args = arg_split(line)

        path = os.path.abspath(args[0])
        args = args[1:]
        if not os.path.isfile(path):
            from IPython.core.error import UsageError
            raise UsageError("%%pudb: file %s does not exist" % path)

        from pudb import runscript
        runscript(path, args)
    register_line_magic(pudb)

    def debugger(self, force=False):
        """
        Call the PuDB debugger
        """
        from IPython.utils.warn import error
        if not (force or self.call_pdb):
            return

        if not hasattr(sys, 'last_traceback'):
            error('No traceback has been produced, nothing to debug.')
            return

        from pudb import pm

        with self.readline_no_record:
            pm()

    ip = get_ipython()
    ip.__class__.debugger = debugger

elif _ipython_version == (0, 10):
    ip.expose_magic('pudb', pudb_f_v10)
else:
    ip.define_magic('pudb', pudb_f_v11)

########NEW FILE########
__FILENAME__ = lowlevel
from pudb.py3compat import PY3


# {{{ breakpoint validity

def generate_executable_lines_for_code(code):
    l = code.co_firstlineno
    yield l
    if PY3:
        for c in code.co_lnotab[1::2]:
            l += c
            yield l
    else:
        for c in code.co_lnotab[1::2]:
            l += ord(c)
            yield l


def get_executable_lines_for_file(filename):
    # inspired by rpdb2

    from linecache import getlines
    codes = [compile("".join(getlines(filename)), filename, "exec")]

    from types import CodeType

    execable_lines = set()

    while codes:
        code = codes.pop()
        execable_lines |= set(generate_executable_lines_for_code(code))
        codes.extend(const
                for const in code.co_consts
                if isinstance(const, CodeType))

    return execable_lines


def get_breakpoint_invalid_reason(filename, lineno):
    # simple logic stolen from pdb
    import linecache
    line = linecache.getline(filename, lineno)
    if not line:
        return "Line is beyond end of file."

    if lineno not in get_executable_lines_for_file(filename):
        return "No executable statement found in line."


def lookup_module(filename):
    """Helper function for break/clear parsing -- may be overridden.

    lookupmodule() translates (possibly incomplete) file or module name
    into an absolute file name.
    """

    # stolen from pdb
    import os
    import sys

    if os.path.isabs(filename) and os.path.exists(filename):
        return filename
    f = os.path.join(sys.path[0], filename)
    if os.path.exists(f):  # and self.canonic(f) == self.mainpyfile:
        return f
    root, ext = os.path.splitext(filename)
    if ext == '':
        filename = filename + '.py'
    if os.path.isabs(filename):
        return filename
    for dirname in sys.path:
        while os.path.islink(dirname):
            dirname = os.readlink(dirname)
        fullname = os.path.join(dirname, filename)
        if os.path.exists(fullname):
            return fullname
    return None

# }}}

# {{{ file encoding detection
# stolen from Python 3.1's tokenize.py, by Ka-Ping Yee

import re
cookie_re = re.compile("^\s*#.*coding[:=]\s*([-\w.]+)")
from codecs import lookup, BOM_UTF8
if PY3:
    BOM_UTF8 = BOM_UTF8.decode()


def detect_encoding(readline):
    """
    The detect_encoding() function is used to detect the encoding that should
    be used to decode a Python source file. It requires one argment, readline,
    in the same way as the tokenize() generator.

    It will call readline a maximum of twice, and return the encoding used
    (as a string) and a list of any lines (left as bytes) it has read
    in.

    It detects the encoding from the presence of a utf-8 bom or an encoding
    cookie as specified in pep-0263. If both a bom and a cookie are present,
    but disagree, a SyntaxError will be raised. If the encoding cookie is an
    invalid charset, raise a SyntaxError.

    If no encoding is specified, then the default of 'utf-8' will be returned.
    """
    bom_found = False
    encoding = None

    def read_or_stop():
        try:
            return readline()
        except StopIteration:
            return ''

    def find_cookie(line):
        try:
            if PY3:
                line_string = line
            else:
                line_string = line.decode('ascii')
        except UnicodeDecodeError:
            return None

        matches = cookie_re.findall(line_string)
        if not matches:
            return None
        encoding = matches[0]
        try:
            codec = lookup(encoding)
        except LookupError:
            # This behaviour mimics the Python interpreter
            raise SyntaxError("unknown encoding: " + encoding)

        if bom_found and codec.name != 'utf-8':
            # This behaviour mimics the Python interpreter
            raise SyntaxError('encoding problem: utf-8')
        return encoding

    first = read_or_stop()
    if first.startswith(BOM_UTF8):
        bom_found = True
        first = first[3:]
    if not first:
        return 'utf-8', []

    encoding = find_cookie(first)
    if encoding:
        return encoding, [first]

    second = read_or_stop()
    if not second:
        return 'utf-8', [first]

    encoding = find_cookie(second)
    if encoding:
        return encoding, [first, second]

    return 'utf-8', [first, second]

# }}}


# {{{ traceback formatting

class StringExceptionValueWrapper:
    def __init__(self, string_val):
        self.string_val = string_val

    def __str__(self):
        return self.string_val

    __context__ = None
    __cause__ = None


def format_exception(exc_tuple):
    # Work around http://bugs.python.org/issue17413
    # See also https://github.com/inducer/pudb/issues/61

    from traceback import format_exception
    if PY3:
        exc_type, exc_value, exc_tb = exc_tuple

        if isinstance(exc_value, str):
            exc_value = StringExceptionValueWrapper(exc_value)
            exc_tuple = exc_type, exc_value, exc_tb

        return format_exception(
                *exc_tuple,
                **dict(chain=hasattr(exc_value, "__context__")))
    else:
        return format_exception(*exc_tuple)

# }}}

# vim: foldmethod=marker

########NEW FILE########
__FILENAME__ = py3compat
import sys

PY3 = sys.version_info[0] >= 3
if PY3:
    raw_input = input
    xrange = range
    integer_types = (int,)
    string_types = (str,)
    def execfile(fname, globs, locs=None):
        exec(compile(open(fname).read(), fname, 'exec'), globs, locs or globs)
else:
    raw_input = raw_input
    xrange = xrange
    integer_types = (int, long)
    string_types = (basestring,)
    execfile = execfile

########NEW FILE########
__FILENAME__ = run
def main():
    import sys

    from optparse import OptionParser
    parser = OptionParser(
            usage="usage: %prog [options] SCRIPT-TO-RUN [SCRIPT-ARGUMENTS]")

    parser.add_option("-s", "--steal-output", action="store_true"),
    parser.add_option("--pre-run", metavar="COMMAND",
            help="Run command before each program run",
            default="")
    parser.disable_interspersed_args()
    options, args = parser.parse_args()

    if len(args) < 1:
        parser.print_help()
        sys.exit(2)

    mainpyfile =  args[0]
    from os.path import exists
    if not exists(mainpyfile):
        print('Error: %s does not exist' % mainpyfile)
        sys.exit(1)

    sys.argv = args

    from pudb import runscript
    runscript(mainpyfile,
            pre_run=options.pre_run,
            steal_output=options.steal_output)




if __name__=='__main__':
    main()

########NEW FILE########
__FILENAME__ = settings
import os
import sys

from pudb.py3compat import PY3
if PY3:
    from configparser import ConfigParser
else:
    from ConfigParser import ConfigParser

# minor LGPL violation: stolen from python-xdg

_home = os.environ.get('HOME', '/')
xdg_data_home = os.environ.get('XDG_DATA_HOME',
            os.path.join(_home, '.local', 'share'))

xdg_config_home = os.environ.get('XDG_CONFIG_HOME',
            os.path.join(_home, '.config'))

xdg_config_dirs = [xdg_config_home] + \
    os.environ.get('XDG_CONFIG_DIRS', '/etc/xdg').split(':')


def get_save_config_path(*resource):
    if not resource:
        resource = [XDG_CONF_RESOURCE]
    resource = os.path.join(*resource)
    assert not resource.startswith('/')
    path = os.path.join(xdg_config_home, resource)
    if not os.path.isdir(path):
        os.makedirs(path, 448)  # 0o700
    return path

# end LGPL violation

CONF_SECTION = "pudb"
XDG_CONF_RESOURCE = "pudb"
CONF_FILE_NAME = "pudb.cfg"

SAVED_BREAKPOINTS_FILE_NAME = "saved-breakpoints-%d.%d" % sys.version_info[:2]
BREAKPOINTS_FILE_NAME = "breakpoints-%d.%d" % sys.version_info[:2]


def load_config():
    from os.path import join, isdir

    cparser = ConfigParser()

    conf_dict = {}
    try:
        cparser.read([
            join(cdir, XDG_CONF_RESOURCE, CONF_FILE_NAME)
            for cdir in xdg_config_dirs if isdir(cdir)])

        if cparser.has_section(CONF_SECTION):
            conf_dict.update(dict(cparser.items(CONF_SECTION)))
    except:
        pass

    conf_dict.setdefault("shell", "internal")
    conf_dict.setdefault("theme", "classic")
    conf_dict.setdefault("line_numbers", False)
    conf_dict.setdefault("seen_welcome", "a")

    conf_dict.setdefault("sidebar_width", 0.5)
    conf_dict.setdefault("variables_weight", 1)
    conf_dict.setdefault("stack_weight", 1)
    conf_dict.setdefault("breakpoints_weight", 1)

    conf_dict.setdefault("current_stack_frame", "top")

    conf_dict.setdefault("stringifier", "type")

    conf_dict.setdefault("custom_theme", "")
    conf_dict.setdefault("custom_stringifier", "")

    conf_dict.setdefault("wrap_variables", True)

    conf_dict.setdefault("display", "auto")

    conf_dict.setdefault("prompt_on_quit", True)

    def normalize_bool_inplace(name):
        try:
            if conf_dict[name].lower() in ["0", "false", "off"]:
                conf_dict[name] = False
            else:
                conf_dict[name] = True
        except:
            pass

    normalize_bool_inplace("line_numbers")
    normalize_bool_inplace("wrap_variables")
    normalize_bool_inplace("prompt_on_quit")

    return conf_dict


def save_config(conf_dict):
    from os.path import join

    cparser = ConfigParser()
    cparser.add_section(CONF_SECTION)

    for key in sorted(conf_dict):
        cparser.set(CONF_SECTION, key, str(conf_dict[key]))

    try:
        outf = open(join(get_save_config_path(),
            CONF_FILE_NAME), "w")
        cparser.write(outf)
        outf.close()
    except:
        pass


def edit_config(ui, conf_dict):
    import urwid

    old_conf_dict = conf_dict.copy()

    def _update_theme():
        ui.setup_palette(ui.screen)

        for sl in ui.source:
            sl._invalidate()

    def _update_line_numbers():
        for sl in ui.source:
                sl._invalidate()

    def _update_prompt_on_quit():
        pass

    def _update_current_stack_frame():
        ui.update_stack()

    def _update_stringifier():
        import pudb.var_view
        pudb.var_view.custom_stringifier_dict = {}
        ui.update_var_view()

    def _update_wrap_variables():
        ui.update_var_view()

    def _update_config(check_box, new_state, option_newvalue):
        option, newvalue = option_newvalue
        new_conf_dict = {option: newvalue}
        if option == "theme":
            # only activate if the new state of the radio button is 'on'
            if new_state:
                if newvalue is None:
                    # Select the custom theme entry dialog
                    lb.set_focus(lb_contents.index(theme_edit_list_item))
                    return

                conf_dict.update(theme=newvalue)
                _update_theme()

        elif option == "line_numbers":
            new_conf_dict["line_numbers"] = not check_box.get_state()
            conf_dict.update(new_conf_dict)
            _update_line_numbers()

        elif option == "prompt_on_quit":
            new_conf_dict["prompt_on_quit"] = not check_box.get_state()
            conf_dict.update(new_conf_dict)
            _update_prompt_on_quit()

        elif option == "current_stack_frame":
            # only activate if the new state of the radio button is 'on'
            if new_state:
                conf_dict.update(new_conf_dict)
                _update_current_stack_frame()

        elif option == "stringifier":
            # only activate if the new state of the radio button is 'on'
            if new_state:
                if newvalue is None:
                    lb.set_focus(lb_contents.index(stringifier_edit_list_item))
                    return

                conf_dict.update(stringifier=newvalue)
                _update_stringifier()
        elif option == "wrap_variables":
            new_conf_dict["wrap_variables"] = not check_box.get_state()
            conf_dict.update(new_conf_dict)
            _update_wrap_variables()

    heading = urwid.Text("This is the preferences screen for PuDB. "
        "Hit Ctrl-P at any time to get back to it.\n\n"
        "Configuration settings are saved in "
        "%s.\n" % get_save_config_path())

    cb_line_numbers = urwid.CheckBox("Show Line Numbers",
            bool(conf_dict["line_numbers"]), on_state_change=_update_config,
                user_data=("line_numbers", None))

    cb_prompt_on_quit = urwid.CheckBox("Prompt before quitting",
            bool(conf_dict["prompt_on_quit"]), on_state_change=_update_config,
                user_data=("prompt_on_quit", None))

    # {{{ shells

    shell_info = urwid.Text("This is the shell that will be "
            "used when you hit '!'.\n")
    shells = ["internal", "classic", "ipython", "bpython"]

    shell_rb_group = []
    shell_rbs = [
            urwid.RadioButton(shell_rb_group, name,
                conf_dict["shell"] == name)
            for name in shells]

    # }}}

    # {{{ themes

    from pudb.theme import THEMES

    known_theme = conf_dict["theme"] in THEMES

    theme_rb_group = []
    theme_edit = urwid.Edit(edit_text=conf_dict["custom_theme"])
    theme_edit_list_item = urwid.AttrMap(theme_edit, "value")
    theme_rbs = [
            urwid.RadioButton(theme_rb_group, name,
                conf_dict["theme"] == name, on_state_change=_update_config,
                user_data=("theme", name))
            for name in THEMES]+[
                urwid.RadioButton(theme_rb_group, "Custom:",
                    not known_theme, on_state_change=_update_config,
                    user_data=("theme", None)),
                theme_edit_list_item,
                urwid.Text("\nTo use a custom theme, see example-theme.py in the "
                    "pudb distribution. Enter the full path to a file like it in "
                    "the box above. '~' will be expanded to your home directory. "
                    "Note that a custom theme will not be applied until you close "
                    "this dialog."),
            ]

    # }}}

    # {{{ stack

    stack_rb_group = []
    stack_opts = ["top", "bottom"]
    stack_info = urwid.Text("Show the current stack frame at the\n")
    stack_rbs = [
            urwid.RadioButton(stack_rb_group, name,
                conf_dict["current_stack_frame"] == name,
                on_state_change=_update_config,
                user_data=("current_stack_frame", name))
            for name in stack_opts
            ]

    # }}}

    # {{{ stringifier

    stringifier_opts = ["type", "str", "repr"]
    known_stringifier = conf_dict["stringifier"] in stringifier_opts
    stringifier_rb_group = []
    stringifier_edit = urwid.Edit(edit_text=conf_dict["custom_stringifier"])
    stringifier_info = urwid.Text("This is the default function that will be "
        "called on variables in the variables list.  Note that you can change "
        "this on a per-variable basis by selecting a variable and hitting Enter "
        "or by typing t/s/r.  Note that str and repr will be slower than type "
        "and have the potential to crash PuDB.\n")
    stringifier_edit_list_item = urwid.AttrMap(stringifier_edit, "value")
    stringifier_rbs = [
            urwid.RadioButton(stringifier_rb_group, name,
                conf_dict["stringifier"] == name,
                on_state_change=_update_config,
                user_data=("stringifier", name))
            for name in stringifier_opts
            ]+[
                urwid.RadioButton(stringifier_rb_group, "Custom:",
                    not known_stringifier, on_state_change=_update_config,
                    user_data=("stringifier", None)),
                stringifier_edit_list_item,
                urwid.Text("\nTo use a custom stringifier, see "
                    "example-stringifier.py in the pudb distribution. Enter the "
                    "full path to a file like it in the box above. "
                    "'~' will be expanded to your home directory. "
                    "The file should contain a function called pudb_stringifier() "
                    "at the module level, which should take a single argument and "
                    "return the desired string form of the object passed to it. "
                    "Note that if you choose a custom stringifier, the variables "
                    "view will not be updated until you close this dialog."),
            ]

    # }}}

    # {{{ wrap variables

    cb_wrap_variables = urwid.CheckBox("Wrap variables",
            bool(conf_dict["wrap_variables"]), on_state_change=_update_config,
                user_data=("wrap_variables", None))

    wrap_variables_info = urwid.Text("\nNote that you can change this option on "
                                     "a per-variable basis by selecting the "
                                     "variable and pressing 'w'.")

    # }}}

    # {{{ display

    display_info = urwid.Text("What driver is used to talk to your terminal. "
            "'raw' has the most features (colors and highlighting), "
            "but is only correct for "
            "XTerm and terminals like it. 'curses' "
            "has fewer "
            "features, but it will work with just about any terminal. 'auto' "
            "will attempt to pick between the two based on availability and "
            "the $TERM environment variable.\n\n"
            "Changing this setting requires a restart of PuDB.")

    displays = ["auto", "raw", "curses"]

    display_rb_group = []
    display_rbs = [
            urwid.RadioButton(display_rb_group, name,
                conf_dict["display"] == name)
            for name in displays]

    # }}}

    lb_contents = (
            [heading]
            + [urwid.AttrMap(urwid.Text("Line Numbers:\n"), "group head")]
            + [cb_line_numbers]

            + [urwid.AttrMap(urwid.Text("\nPrompt on quit:\n"), "group head")]
            + [cb_prompt_on_quit]

            + [urwid.AttrMap(urwid.Text("\nShell:\n"), "group head")]
            + [shell_info]
            + shell_rbs

            + [urwid.AttrMap(urwid.Text("\nTheme:\n"), "group head")]
            + theme_rbs

            + [urwid.AttrMap(urwid.Text("\nStack Order:\n"), "group head")]
            + [stack_info]
            + stack_rbs

            + [urwid.AttrMap(urwid.Text("\nVariable Stringifier:\n"), "group head")]
            + [stringifier_info]
            + stringifier_rbs

            + [urwid.AttrMap(urwid.Text("\nWrap Variables:\n"), "group head")]
            + [cb_wrap_variables]
            + [wrap_variables_info]

            + [urwid.AttrMap(urwid.Text("\nDisplay driver:\n"), "group head")]
            + [display_info]
            + display_rbs
            )

    lb = urwid.ListBox(urwid.SimpleListWalker(lb_contents))

    if ui.dialog(lb,         [
            ("OK", True),
            ("Cancel", False),
            ],
            title="Edit Preferences"):
        # Only update the settings here that instant-apply (above) doesn't take
        # care of.

        # if we had a custom theme, it wasn't updated live
        if theme_rb_group[-1].state:
            newvalue = theme_edit.get_edit_text()
            conf_dict.update(theme=newvalue, custom_theme=newvalue)
            _update_theme()

        # Ditto for custom stringifiers
        if stringifier_rb_group[-1].state:
            newvalue = stringifier_edit.get_edit_text()
            conf_dict.update(stringifier=newvalue, custom_stringifier=newvalue)
            _update_stringifier()

        for shell, shell_rb in zip(shells, shell_rbs):
            if shell_rb.get_state():
                conf_dict["shell"] = shell

        for display, display_rb in zip(displays, display_rbs):
            if display_rb.get_state():
                conf_dict["display"] = display

    else:  # The user chose cancel, revert changes
        conf_dict.update(old_conf_dict)
        _update_theme()
        # _update_line_numbers() is equivalent to _update_theme()
        _update_current_stack_frame()
        _update_stringifier()


# {{{ breakpoint saving

def parse_breakpoints(lines):
    # b [ (filename:lineno | function) [, "condition"] ]

    breakpoints = []
    for arg in lines:
        if not arg:
            continue
        arg = arg[1:]

        filename = None
        lineno = None
        cond = None
        comma = arg.find(',')

        if comma > 0:
            # parse stuff after comma: "condition"
            cond = arg[comma+1:].lstrip()
            arg = arg[:comma].rstrip()

        colon = arg.rfind(':')
        funcname = None

        if colon > 0:
            filename = arg[:colon].strip()

            from pudb.lowlevel import lookup_module
            f = lookup_module(filename)

            if not f:
                continue
            else:
                filename = f

            arg = arg[colon+1:].lstrip()
            try:
                lineno = int(arg)
            except ValueError:
                continue
        else:
            continue

        from pudb.lowlevel import get_breakpoint_invalid_reason
        if get_breakpoint_invalid_reason(filename, lineno) is None:
            breakpoints.append((filename, lineno, False, cond, funcname))

    return breakpoints


def get_breakpoints_file_name():
    from os.path import join
    return join(get_save_config_path(), SAVED_BREAKPOINTS_FILE_NAME)


def load_breakpoints():
    from os.path import join, isdir

    file_names = [
            join(cdir, XDG_CONF_RESOURCE, name)
            for cdir in xdg_config_dirs if isdir(cdir)
            for name in [SAVED_BREAKPOINTS_FILE_NAME, BREAKPOINTS_FILE_NAME]
            ]

    lines = []
    for fname in file_names:
        try:
            rcFile = open(fname)
        except IOError:
            pass
        else:
            lines.extend([l.strip() for l in rcFile.readlines()])
            rcFile.close()

    return parse_breakpoints(lines)


def save_breakpoints(bp_list):
    """
    :arg bp_list: a list of tuples `(file_name, line)`
    """

    histfile = open(get_breakpoints_file_name(), 'w')
    bp_list = set([(bp.file, bp.line, bp.cond) for bp in bp_list])
    for bp in bp_list:
        line = "b %s:%d" % (bp[0], bp[1])
        if bp[2]:
            line += ", %s" % bp[2]
        line += "\n"
        histfile.write(line)
    histfile.close()

# }}}

# vim:foldmethod=marker

########NEW FILE########
__FILENAME__ = shell
try:
    import IPython
except ImportError:
    HAVE_IPYTHON = False
else:
    HAVE_IPYTHON = True

try:
    import bpython  # noqa
except ImportError:
    HAVE_BPYTHON = False
else:
    HAVE_BPYTHON = True


# {{{ readline wrangling

def setup_readline():
    import os
    import atexit

    from pudb.settings import get_save_config_path
    histfile = os.path.join(
            get_save_config_path(),
            "shell-history")

    try:
        readline.read_history_file(histfile)
        atexit.register(readline.write_history_file, histfile)
    except Exception:
        pass

    readline.parse_and_bind("tab: complete")


try:
    import readline
    import rlcompleter
    HAVE_READLINE = True
except ImportError:
    HAVE_READLINE = False
else:
    setup_readline()

# }}}


# {{{ combined locals/globals dict

class SetPropagatingDict(dict):
    def __init__(self, source_dicts, target_dict):
        dict.__init__(self)
        for s in source_dicts[::-1]:
            self.update(s)

        self.target_dict = target_dict

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self.target_dict[key] = value

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        del self.target_dict[key]

# }}}


def run_classic_shell(locals, globals, first_time):
    if first_time:
        banner = "Hit Ctrl-D to return to PuDB."
    else:
        banner = ""

    ns = SetPropagatingDict([locals, globals], locals)

    if HAVE_READLINE:
        readline.set_completer(
                rlcompleter.Completer(ns).complete)

    from code import InteractiveConsole
    cons = InteractiveConsole(ns)

    cons.interact(banner)


def run_bpython_shell(locals, globals, first_time):
    ns = SetPropagatingDict([locals, globals], locals)

    import bpython.cli
    bpython.cli.main(locals_=ns)


def run_ipython_shell_v10(locals, globals, first_time):
    '''IPython shell from IPython version 0.10'''
    if first_time:
        banner = "Hit Ctrl-D to return to PuDB."
    else:
        banner = ""

    # avoid IPython's namespace litter
    ns = locals.copy()

    from IPython.Shell import IPShell
    IPShell(argv=[], user_ns=ns, user_global_ns=globals) \
            .mainloop(banner=banner)


def run_ipython_shell_v11(locals, globals, first_time):
    '''IPython shell from IPython version 0.11'''
    if first_time:
        banner = "Hit Ctrl-D to return to PuDB."
    else:
        banner = ""

    try:
        # IPython 1.0 got rid of the frontend intermediary, and complains with
        # a deprecated warning when you use it.
        from IPython.terminal.interactiveshell import TerminalInteractiveShell
        from IPython.terminal.ipapp import load_default_config
    except ImportError:
        from IPython.frontend.terminal.interactiveshell import \
                TerminalInteractiveShell
        from IPython.frontend.terminal.ipapp import load_default_config
    # XXX: in the future it could be useful to load a 'pudb' config for the
    # user (if it exists) that could contain the user's macros and other
    # niceities.
    config = load_default_config()
    shell = TerminalInteractiveShell.instance(config=config,
            banner2=banner)
    # XXX This avoids a warning about not having unique session/line numbers.
    # See the HistoryManager.writeout_cache method in IPython.core.history.
    shell.history_manager.new_session()
    # Save the originating namespace
    old_locals = shell.user_ns
    old_globals = shell.user_global_ns
    # Update shell with current namespace
    _update_ns(shell, locals, globals)
    shell.mainloop(banner)
    # Restore originating namespace
    _update_ns(shell, old_locals, old_globals)


def _update_ns(shell, locals, globals):
    '''Update the IPython 0.11 namespace at every visit'''

    shell.user_ns = locals.copy()

    try:
        shell.user_global_ns = globals
    except AttributeError:
        class DummyMod(object):
            "A dummy module used for IPython's interactive namespace."
            pass

        user_module = DummyMod()
        user_module.__dict__ = globals
        shell.user_module = user_module

    shell.init_user_ns()
    shell.init_completer()


# Set the proper ipython shell
if HAVE_IPYTHON and hasattr(IPython, 'Shell'):
    run_ipython_shell = run_ipython_shell_v10
else:
    run_ipython_shell = run_ipython_shell_v11

########NEW FILE########
__FILENAME__ = source_view
import urwid


TABSTOP = 8


class SourceLine(urwid.FlowWidget):
    def __init__(self, dbg_ui, text, line_nr='', attr=None, has_breakpoint=False):
        self.dbg_ui = dbg_ui
        self.text = text
        self.attr = attr
        self.line_nr = line_nr
        self.has_breakpoint = has_breakpoint
        self.is_current = False
        self.highlight = False

    def selectable(self):
        return True

    def set_current(self, is_current):
        self.is_current = is_current
        self._invalidate()

    def set_highlight(self, highlight):
        self.highlight = highlight
        self._invalidate()

    def set_breakpoint(self, has_breakpoint):
        self.has_breakpoint = has_breakpoint
        self._invalidate()

    def rows(self, size, focus=False):
        return 1

    def render(self, size, focus=False):
        from pudb.debugger import CONFIG
        render_line_nr = CONFIG["line_numbers"]

        maxcol = size[0]
        hscroll = self.dbg_ui.source_hscroll_start

        # attrs is a list of words like 'focused' and 'breakpoint'
        attrs = []

        if self.is_current:
            crnt = ">"
            attrs.append("current")
        else:
            crnt = " "

        if self.has_breakpoint:
            bp = "*"
            attrs.append("breakpoint")
        else:
            bp = " "

        if focus:
            attrs.append("focused")
        elif self.highlight:
            if not self.has_breakpoint:
                attrs.append("highlighted")

        text = self.text
        if not attrs and self.attr is not None:
            attr = self.attr + [("source", None)]
        else:
            attr = [(" ".join(attrs+["source"]), None)]

        from urwid.util import apply_target_encoding, trim_text_attr_cs

        # build line prefix ---------------------------------------------------
        line_prefix = ""
        line_prefix_attr = []

        if render_line_nr:
            line_prefix_attr = [("line number", len(self.line_nr))]
            line_prefix = self.line_nr

        line_prefix = crnt+bp+line_prefix
        line_prefix_attr = [("source", 1), ("breakpoint marker", 1)] \
                + line_prefix_attr

        # assume rendered width is same as len
        line_prefix_len = len(line_prefix)

        encoded_line_prefix, line_prefix_cs = apply_target_encoding(line_prefix)

        assert len(encoded_line_prefix) == len(line_prefix)
        # otherwise we'd have to adjust line_prefix_attr... :/

        # shipout, encoding ---------------------------------------------------
        cs = []
        encoded_text_segs = []
        encoded_attr = []

        i = 0
        for seg_attr, seg_len in attr:
            if seg_len is None:
                # means: gobble up remainder of text and rest of line
                # and fill with attribute

                l = hscroll+maxcol
                remaining_text = text[i:]
                encoded_seg_text, seg_cs = apply_target_encoding(
                        remaining_text + l*" ")
                encoded_attr.append((seg_attr, len(remaining_text)+l))
            else:
                unencoded_seg_text = text[i:i+seg_len]
                encoded_seg_text, seg_cs = apply_target_encoding(unencoded_seg_text)

                adjustment = len(encoded_seg_text) - len(unencoded_seg_text)

                encoded_attr.append((seg_attr, seg_len + adjustment))

                i += seg_len

            encoded_text_segs.append(encoded_seg_text)
            cs.extend(seg_cs)

        encoded_text = b"".join(encoded_text_segs)
        encoded_text, encoded_attr, cs = trim_text_attr_cs(
                encoded_text, encoded_attr, cs,
                hscroll, hscroll+maxcol-line_prefix_len)

        encoded_text = encoded_line_prefix + encoded_text
        encoded_attr = line_prefix_attr + encoded_attr
        cs = line_prefix_cs + cs

        return urwid.TextCanvas([encoded_text], [encoded_attr], [cs], maxcol=maxcol)

    def keypress(self, size, key):
        return key


def format_source(debugger_ui, lines, breakpoints):
    lineno_format = "%%%dd " % (len(str(len(lines))))
    try:
        import pygments  # noqa
    except ImportError:
        return [SourceLine(debugger_ui,
            line.rstrip("\n\r").expandtabs(TABSTOP),
            lineno_format % (i+1), None,
            has_breakpoint=i+1 in breakpoints)
            for i, line in enumerate(lines)]
    else:
        from pygments import highlight
        from pygments.lexers import PythonLexer
        from pygments.formatter import Formatter
        import pygments.token as t

        result = []

        ATTR_MAP = {
                t.Token: "source",
                t.Keyword: "keyword",
                t.Literal: "literal",
                t.Name.Function: "name",
                t.Name.Class: "name",
                t.Punctuation: "punctuation",
                t.String: "string",
                # XXX: Single and Double don't actually work yet.
                # See https://bitbucket.org/birkenfeld/pygments-main/issue/685
                t.String.Double: "doublestring",
                t.String.Single: "singlestring",
                t.String.Backtick: "backtick",
                t.String.Doc: "docstring",
                t.Comment: "comment",
                }

        class UrwidFormatter(Formatter):
            def __init__(subself, **options):
                Formatter.__init__(subself, **options)
                subself.current_line = ""
                subself.current_attr = []
                subself.lineno = 1

            def format(subself, tokensource, outfile):
                def add_snippet(ttype, s):
                    if not s:
                        return

                    while not ttype in ATTR_MAP:
                        if ttype.parent is not None:
                            ttype = ttype.parent
                        else:
                            raise RuntimeError(
                                    "untreated token type: %s" % str(ttype))

                    attr = ATTR_MAP[ttype]

                    subself.current_line += s
                    subself.current_attr.append((attr, len(s)))

                def shipout_line():
                    result.append(
                            SourceLine(debugger_ui,
                                subself.current_line,
                                lineno_format % subself.lineno,
                                subself.current_attr,
                                has_breakpoint=subself.lineno in breakpoints))
                    subself.current_line = ""
                    subself.current_attr = []
                    subself.lineno += 1

                for ttype, value in tokensource:
                    while True:
                        newline_pos = value.find("\n")
                        if newline_pos == -1:
                            add_snippet(ttype, value)
                            break
                        else:
                            add_snippet(ttype, value[:newline_pos])
                            shipout_line()
                            value = value[newline_pos+1:]

                if subself.current_line:
                    shipout_line()

        highlight("".join(l.expandtabs(TABSTOP) for l in lines),
                PythonLexer(stripnl=False), UrwidFormatter())

        return result

########NEW FILE########
__FILENAME__ = theme
THEMES = ["classic", "vim", "dark vim", "midnight"]

from pudb.py3compat import execfile, raw_input
import urwid


def get_palette(may_use_fancy_formats, theme="classic"):
    if may_use_fancy_formats:
        def add_setting(color, setting):
            return color+","+setting
    else:
        def add_setting(color, setting):
            return color

    palette_dict = { # {{{ ui

        "header": ("black", "light gray", "standout"),

        "selectable": ("black", "dark cyan"),
        "focused selectable": ("black", "dark green"),

        "button": (add_setting("white", "bold"), "dark blue"),
        "focused button": ("light cyan", "black"),

        "dialog title": (add_setting("white", "bold"), "dark cyan"),

        "background": ("black", "light gray"),
        "hotkey": (add_setting("black", "underline"), "light gray", "underline"),
        "focused sidebar": (add_setting("yellow", "bold"), "light gray", "standout"),

        "warning": (add_setting("white", "bold"), "dark red", "standout"),

        "label": ("black", "light gray"),
        "value": (add_setting("yellow", "bold"), "dark blue"),
        "fixed value": ("light gray", "dark blue"),
        "group head": (add_setting("dark blue", "bold"), "light gray"),

        "search box": ("black", "dark cyan"),
        "search not found": ("white", "dark red"),

        # }}}

        # {{{ shell

        "command line edit": (add_setting("yellow", "bold"), "dark blue"),
        "command line prompt": (add_setting("white", "bold"), "dark blue"),

        "command line output": ("light cyan", "dark blue"),
        "command line input": (add_setting("light cyan", "bold"), "dark blue"),
        "command line error": (add_setting("light red", "bold"), "dark blue"),

        "focused command line output": ("black", "dark green"),
        "focused command line input": (add_setting("light cyan", "bold"), "dark green"),
        "focused command line error": ("black", "dark green"),

        "command line clear button": (add_setting("white", "bold"), "dark blue"),
        "command line focused button": ("light cyan", "black"),

        # }}}

        # {{{ source

        "breakpoint": ("black", "dark cyan"),
        "focused breakpoint": ("black", "dark green"),
        "current breakpoint": (add_setting("white", "bold"), "dark cyan"),
        "focused current breakpoint": (add_setting("white", "bold"), "dark green", "bold"),

        "source": (add_setting("yellow", "bold"), "dark blue"),
        "focused source": ("black", "dark green"),
        "highlighted source": ("black", "dark magenta"),
        "current source": ("black", "dark cyan"),
        "current focused source": (add_setting("white", "bold"), "dark cyan"),
        "current highlighted source": ("white", "dark cyan"),

        # {{{ highlighting

        "line number": ("light gray", "dark blue"),
        "keyword": (add_setting("white", "bold"), "dark blue"),
        "name": ("light cyan", "dark blue"),
        "literal": ("light magenta, bold", "dark blue"),

        "string": (add_setting("light magenta", "bold"), "dark blue"),
        "doublestring": (add_setting("light magenta", "bold"), "dark blue"),
        "singlestring": (add_setting("light magenta", "bold"), "dark blue"),
        "docstring": (add_setting("light magenta", "bold"), "dark blue"),

        "punctuation": ("light gray", "dark blue"),
        "comment": ("light gray", "dark blue"),

        # }}}

        # }}}

        # {{{ breakpoints

        "breakpoint marker": ("dark red", "dark blue"),

        "breakpoint source": (add_setting("yellow", "bold"), "dark red"),
        "breakpoint focused source": ("black", "dark red"),
        "current breakpoint source": ("black", "dark red"),
        "current breakpoint focused source": ("white", "dark red"),

        # }}}

        # {{{ variables view

        "variables": ("black", "dark cyan"),
        "variable separator": ("dark cyan", "light gray"),

        "var label": ("dark blue", "dark cyan"),
        "var value": ("black", "dark cyan"),
        "focused var label": ("dark blue", "dark green"),
        "focused var value": ("black", "dark green"),

        "highlighted var label": ("white", "dark cyan"),
        "highlighted var value": ("black", "dark cyan"),
        "focused highlighted var label": ("white", "dark green"),
        "focused highlighted var value": ("black", "dark green"),

        "return label": ("white", "dark blue"),
        "return value": ("black", "dark cyan"),
        "focused return label": ("light gray", "dark blue"),
        "focused return value": ("black", "dark green"),

        # }}}

        # {{{ stack

        "stack": ("black", "dark cyan"),

        "frame name": ("black", "dark cyan"),
        "focused frame name": ("black", "dark green"),
        "frame class": ("dark blue", "dark cyan"),
        "focused frame class": ("dark blue", "dark green"),
        "frame location": ("light cyan", "dark cyan"),
        "focused frame location": ("light cyan", "dark green"),

        "current frame name": (add_setting("white", "bold"),
            "dark cyan"),
        "focused current frame name": (add_setting("white", "bold"),
            "dark green", "bold"),
        "current frame class": ("dark blue", "dark cyan"),
        "focused current frame class": ("dark blue", "dark green"),
        "current frame location": ("light cyan", "dark cyan"),
        "focused current frame location": ("light cyan", "dark green"),

        # }}}

    }

    if theme == "classic":
        pass
    elif theme == "vim":
        # {{{ vim theme

        palette_dict.update({
            "source": ("black", "default"),
            "keyword": ("brown", "default"),
            "kw_namespace": ("dark magenta", "default"),

            "literal": ("black", "default"),
            "string": ("dark red", "default"),
            "doublestring": ("dark red", "default"),
            "singlestring": ("dark red", "default"),
            "docstring": ("dark red", "default"),

            "punctuation": ("black", "default"),
            "comment": ("dark blue", "default"),
            "classname": ("dark cyan", "default"),
            "name": ("dark cyan", "default"),
            "line number": ("dark gray", "default"),
            "breakpoint marker": ("dark red", "default"),

            # {{{ shell

            "command line edit":
            ("black", "default"),
            "command line prompt":
            (add_setting("black", "bold"), "default"),

            "command line output":
            (add_setting("black", "bold"), "default"),
            "command line input":
            ("black", "default"),
            "command line error":
            (add_setting("light red", "bold"), "default"),

            "focused command line output":
            ("black", "dark green"),
            "focused command line input":
            (add_setting("light cyan", "bold"), "dark green"),
            "focused command line error":
            ("black", "dark green"),

            # }}}
            })
        # }}}
    elif theme == "dark vim":
        # {{{ dark vim

        palette_dict.update({
            "header": ("black", "light gray", "standout"),

            # {{{ variables view
            "variables": ("black", "dark gray"),
            "variable separator": ("dark cyan", "light gray"),

            "var label": ("light gray", "dark gray"),
            "var value": ("white", "dark gray"),
            "focused var label": ("light gray", "light blue"),
            "focused var value": ("white", "light blue"),

            "highlighted var label": ("light gray", "dark green"),
            "highlighted var value": ("white", "dark green"),
            "focused highlighted var label": ("light gray", "light blue"),
            "focused highlighted var value": ("white", "light blue"),

            "return label": ("light gray", "dark gray"),
            "return value": ("light cyan", "dark gray"),
            "focused return label": ("yellow", "light blue"),
            "focused return value": ("white", "light blue"),

            # }}}

            # {{{ stack view

            "stack": ("black", "dark gray"),

            "frame name": ("light gray", "dark gray"),
            "focused frame name": ("light gray", "light blue"),
            "frame class": ("dark blue", "dark gray"),
            "focused frame class": ("dark blue", "light blue"),
            "frame location": ("white", "dark gray"),
            "focused frame location": ("white", "light blue"),

            "current frame name": (add_setting("white", "bold"),
                "dark gray"),
            "focused current frame name": (add_setting("white", "bold"),
                "light blue", "bold"),
            "current frame class": ("dark blue", "dark gray"),
            "focused current frame class": ("dark blue", "dark green"),
            "current frame location": ("light cyan", "dark gray"),
            "focused current frame location": ("light cyan", "light blue"),

            # }}}

            # {{{ breakpoint view

            "breakpoint": ("light gray", "dark gray"),
            "focused breakpoint": ("light gray", "light blue"),
            "current breakpoint": (add_setting("white", "bold"), "dark gray"),
            "focused current breakpoint":
                (add_setting("white", "bold"), "light blue"),

            # }}}

            # {{{ ui widgets

            "selectable": ("light gray", "dark gray"),
            "focused selectable": ("white", "light blue"),

            "button": ("light gray", "dark gray"),
            "focused button": ("white", "light blue"),

            "background": ("black", "light gray"),
            "hotkey": (add_setting("black", "underline"), "light gray", "underline"),
            "focused sidebar": ("light blue", "light gray", "standout"),

            "warning": (add_setting("white", "bold"), "dark red", "standout"),

            "label": ("black", "light gray"),
            "value": ("white", "dark gray"),
            "fixed value": ("light gray", "dark gray"),

            "search box": ("white", "dark gray"),
            "search not found": ("white", "dark red"),

            "dialog title": (add_setting("white", "bold"), "dark gray"),

            # }}}

            # {{{ source view

            "breakpoint marker": ("dark red", "black"),

            "breakpoint source": ("light gray", "dark red"),
            "breakpoint focused source": ("black", "dark red"),
            "current breakpoint source": ("black", "dark red"),
            "current breakpoint focused source": ("white", "dark red"),

            # }}}

            # {{{ highlighting

            "source": ("white", "black"),
            "focused source": ("white", "light blue"),
            "highlighted source": ("black", "dark magenta"),
            "current source": ("black", "light gray"),
            "current focused source": ("white", "dark cyan"),
            "current highlighted source": ("white", "dark cyan"),

            "line number": ("dark gray", "black"),
            "keyword": ("yellow", "black"),

            "literal": ("dark magenta", "black"),
            "string": ("dark magenta", "black"),
            "doublestring": ("dark magenta", "black"),
            "singlestring": ("dark magenta", "black"),
            "docstring": ("dark magenta", "black"),

            "name": ("light cyan", "black"),
            "punctuation": ("yellow", "black"),
            "comment": ("light blue", "black"),

            # }}}

            # {{{ shell

            "command line edit":
            ("white", "black"),
            "command line prompt":
            (add_setting("yellow", "bold"), "black"),

            "command line output":
            (add_setting("yellow", "bold"), "black"),
            "command line input":
            ("white", "black"),
            "command line error":
            (add_setting("light red", "bold"), "black"),

            "focused command line output":
            ("black", "light blue"),
            "focused command line input":
            (add_setting("light cyan", "bold"), "light blue"),
            "focused command line error":
            ("black", "light blue"),

            # }}}
            })

        # }}}
    elif theme == "midnight":
        # {{{ midnight

        # Based on XCode's midnight theme
        # Looks best in a console with green text against black background
        palette_dict.update({
            "variables": ("white", "default"),

            "var label": ("light blue", "default"),
            "var value": ("white", "default"),

            "stack": ("white", "default"),

            "frame name": ("white", "default"),
            "frame class": ("dark blue", "default"),
            "frame location": ("light cyan", "default"),

            "current frame name": (add_setting("white", "bold"), "default"),
            "current frame class": ("dark blue", "default"),
            "current frame location": ("light cyan", "default"),

            "focused frame name": ("black", "dark green"),
            "focused frame class": (add_setting("white", "bold"), "dark green"),
            "focused frame location": ("dark blue", "dark green"),

            "focused current frame name": ("black", "dark green"),
            "focused current frame class": (add_setting("white", "bold"), "dark green"),
            "focused current frame location": ("dark blue", "dark green"),

            "breakpoint": ("default", "default"),

            "search box": ("default", "default"),

            "source": ("white", "default"),
            "highlighted source": ("white", "light cyan"),
            "current source": ("white", "light gray"),
            "current focused source": ("white", "brown"),

            "line number": ("light gray", "default"),
            "keyword": ("dark magenta", "default"),
            "name": ("white", "default"),
            "literal": ("dark cyan", "default"),
            "string": ("dark red", "default"),
            "doublestring": ("dark red", "default"),
            "singlestring": ("light blue", "default"),
            "docstring": ("light red", "default"),
            "backtick": ("light green", "default"),
            "punctuation": ("white", "default"),
            "comment": ("dark green", "default"),
            "classname": ("dark cyan", "default"),
            "funcname": ("white", "default"),

            "breakpoint marker": ("dark red", "default"),

            # {{{ shell

            "command line edit": ("white", "default"),
            "command line prompt": (add_setting("white", "bold"), "default"),

            "command line output": (add_setting("white", "bold"), "default"),
            "command line input": (add_setting("white", "bold"), "default"),
            "command line error": (add_setting("light red", "bold"), "default"),

            "focused command line output": ("black", "dark green"),
            "focused command line input": (add_setting("white", "bold"), "dark green"),
            "focused command line error": ("black", "dark green"),

            "command line clear button": (add_setting("white", "bold"), "default"),
            "command line focused button": ("black", "light gray"), # White
            # doesn't work in curses mode

            # }}}

        })

        # }}}

    else:
        try:
            symbols = {
                    "palette": palette_dict,
                    "add_setting": add_setting,
                    }

            from os.path import expanduser
            execfile(expanduser(theme), symbols)
        except:
            print("Error when importing theme:")
            from traceback import print_exc
            print_exc()
            raw_input("Hit enter:")

    palette_list = []
    for setting_name, color_values in palette_dict.items():
        fg_color = color_values[0].lower().strip()
        bg_color = color_values[1].lower().strip()

        # Convert hNNN syntax to equivalent #RGB value
        # (https://github.com/wardi/urwid/issues/24)
        if fg_color.startswith('h') or bg_color.startswith('h'):
            attr = urwid.AttrSpec(fg_color, bg_color, colors=256)
            palette_list.append((setting_name, 'default', 'default', 'default',
                attr.foreground,
                attr.background))
        else:
            palette_list.append((setting_name,) + color_values)

    return palette_list

# vim: foldmethod=marker

########NEW FILE########
__FILENAME__ = ui_tools
import urwid


# generic urwid helpers -------------------------------------------------------

def make_canvas(txt, attr, maxcol, fill_attr=None):
    processed_txt = []
    processed_attr = []
    processed_cs = []

    for line, line_attr in zip(txt, attr):
        # filter out zero-length attrs
        line_attr = [(aname, l) for aname, l in line_attr if l > 0]

        diff = maxcol - len(line)
        if diff > 0:
            line += " "*diff
            line_attr.append((fill_attr, diff))
        else:
            from urwid.util import rle_subseg
            line = line[:maxcol]
            line_attr = rle_subseg(line_attr, 0, maxcol)

        from urwid.util import apply_target_encoding
        line, line_cs = apply_target_encoding(line)

        processed_txt.append(line)
        processed_attr.append(line_attr)
        processed_cs.append(line_cs)

    return urwid.TextCanvas(
            processed_txt,
            processed_attr,
            processed_cs,
            maxcol=maxcol)


def make_hotkey_markup(s):
    import re
    match = re.match(r"^([^_]*)_(.)(.*)$", s)
    assert match is not None

    return [
            (None, match.group(1)),
            ("hotkey", match.group(2)),
            (None, match.group(3)),
            ]


def labelled_value(label, value):
    return urwid.AttrMap(urwid.Text([
        ("label", label), str(value)]),
        "fixed value", "fixed value")


class SelectableText(urwid.Text):
    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class SignalWrap(urwid.WidgetWrap):
    def __init__(self, w, is_preemptive=False):
        urwid.WidgetWrap.__init__(self, w)
        self.event_listeners = []
        self.is_preemptive = is_preemptive

    def listen(self, mask, handler):
        self.event_listeners.append((mask, handler))

    def keypress(self, size, key):
        result = key

        if self.is_preemptive:
            for mask, handler in self.event_listeners:
                if mask is None or mask == key:
                    result = handler(self, size, key)
                    break

        if result is not None:
            result = self._w.keypress(size, key)

        if result is not None and not self.is_preemptive:
            for mask, handler in self.event_listeners:
                if mask is None or mask == key:
                    return handler(self, size, key)

        return result


# {{{ debugger-specific stuff

class StackFrame(urwid.FlowWidget):
    def __init__(self, is_current, name, class_name, filename, line):
        self.is_current = is_current
        self.name = name
        self.class_name = class_name
        self.filename = filename
        self.line = line

    def selectable(self):
        return True

    def rows(self, size, focus=False):
        return 1

    def render(self, size, focus=False):
        maxcol = size[0]
        if focus:
            apfx = "focused "
        else:
            apfx = ""

        if self.is_current:
            apfx += "current "
            crnt_pfx = ">> "
        else:
            crnt_pfx = "   "

        text = crnt_pfx+self.name
        attr = [(apfx+"frame name", 3+len(self.name))]

        if self.class_name is not None:
            text += " [%s]" % self.class_name
            attr.append((apfx+"frame class", len(self.class_name)+3))

        loc = " %s:%d" % (self.filename, self.line)
        text += loc
        attr.append((apfx+"frame location", len(loc)))

        return make_canvas([text], [attr], maxcol, apfx+"frame location")

    def keypress(self, size, key):
        return key


class BreakpointFrame(urwid.FlowWidget):
    def __init__(self, is_current, filename, line):
        self.is_current = is_current
        self.filename = filename
        self.line = line

    def selectable(self):
        return True

    def rows(self, size, focus=False):
        return 1

    def render(self, size, focus=False):
        maxcol = size[0]
        if focus:
            apfx = "focused "
        else:
            apfx = ""

        if self.is_current:
            apfx += "current "
            crnt_pfx = ">> "
        else:
            crnt_pfx = "   "

        loc = " %s:%d" % (self.filename, self.line)
        text = crnt_pfx+loc
        attr = [(apfx+"breakpoint", len(loc))]

        return make_canvas([text], [attr], maxcol, apfx+"breakpoint")

    def keypress(self, size, key):
        return key


class SearchController(object):
    def __init__(self, ui):
        self.ui = ui
        self.highlight_line = None

        self.search_box = None
        self.last_search_string = None

    def cancel_highlight(self):
        if self.highlight_line is not None:
            self.highlight_line.set_highlight(False)
            self.highlight_line = None

    def cancel_search(self):
        self.cancel_highlight()
        self.hide_search_ui()

    def hide_search_ui(self):
        self.search_box = None
        del self.ui.lhs_col.contents[0]
        self.ui.lhs_col.set_focus(self.ui.lhs_col.widget_list[0])

    def open_search_ui(self):
        lhs_col = self.ui.lhs_col

        if self.search_box is None:
            _, self.search_start = self.ui.source.get_focus()

            self.search_box = SearchBox(self)
            self.search_AttrMap = urwid.AttrMap(
                    self.search_box, "search box")

            lhs_col.item_types.insert(
                    0, ("flow", None))
            lhs_col.widget_list.insert(0, self.search_AttrMap)

            self.ui.columns.set_focus(lhs_col)
            lhs_col.set_focus(self.search_AttrMap)
        else:
            self.ui.columns.set_focus(lhs_col)
            lhs_col.set_focus(self.search_AttrMap)
            #self.search_box.restart_search()

    def perform_search(self, dir, s=None, start=None, update_search_start=False):
        self.cancel_highlight()

        # self.ui.lhs_col.set_focus(self.ui.lhs_col.widget_list[1])

        if s is None:
            s = self.last_search_string

            if s is None:
                self.ui.message("No previous search term.")
                return False
        else:
            self.last_search_string = s

        if start is None:
            start = self.search_start

        case_insensitive = s.lower() == s

        if start > len(self.ui.source):
            start = 0

        i = (start+dir) % len(self.ui.source)

        if i >= len(self.ui.source):
            i = 0

        while i != start:
            sline = self.ui.source[i].text
            if case_insensitive:
                sline = sline.lower()

            if s in sline:
                sl = self.ui.source[i]
                sl.set_highlight(True)
                self.highlight_line = sl
                self.ui.source.set_focus(i)

                if update_search_start:
                    self.search_start = i

                return True

            i = (i+dir) % len(self.ui.source)

        return False


class SearchBox(urwid.Edit):
    def __init__(self, controller):
        urwid.Edit.__init__(self, [("label", "Search: ")], "")
        self.controller = controller

    def restart_search(self):
        from time import time
        now = time()

        if self.search_start_time > 5:
            self.set_edit_text("")

        self.search_time = now

    def keypress(self, size, key):
        result = urwid.Edit.keypress(self, size, key)
        txt = self.get_edit_text()

        if result is not None:
            if key == "esc":
                self.controller.cancel_search()
                return None
            elif key == "enter":
                if txt:
                    self.controller.hide_search_ui()
                    self.controller.perform_search(dir=1, s=txt,
                            update_search_start=True)
                else:
                    self.controller.cancel_search()
                return None
        else:
            if self.controller.perform_search(dir=1, s=txt):
                self.controller.search_AttrMap.set_attr_map({None: "search box"})
            else:
                self.controller.search_AttrMap.set_attr_map(
                        {None: "search not found"})

        return result

# }}}

########NEW FILE########
__FILENAME__ = var_view
# -*- coding: utf-8 -*-

# {{{ constants and imports

import urwid

try:
    import numpy
    HAVE_NUMPY = 1
except ImportError:
    HAVE_NUMPY = 0

from pudb.py3compat import PY3, execfile, raw_input, xrange, \
        integer_types, string_types
if PY3:
    ELLIPSIS = '…'
else:
    ELLIPSIS = unicode('…', 'utf-8')

from pudb.debugger import CONFIG

# }}}


# {{{ data

class FrameVarInfo(object):
    def __init__(self):
        self.id_path_to_iinfo = {}
        self.watches = []

    def get_inspect_info(self, id_path, read_only):
        if read_only:
            return self.id_path_to_iinfo.get(
                    id_path, InspectInfo())
        else:
            return self.id_path_to_iinfo.setdefault(
                    id_path, InspectInfo())


class InspectInfo(object):
    def __init__(self):
        self.show_detail = False
        self.display_type = CONFIG["stringifier"]
        self.highlighted = False
        self.repeated_at_top = False
        self.show_private_members = False
        self.wrap = CONFIG["wrap_variables"]


class WatchExpression(object):
    def __init__(self, expression):
        self.expression = expression


class WatchEvalError(object):
    def __str__(self):
        return "<error>"

# }}}


# {{{ safe types

def get_str_safe_types():
    import types

    return tuple(getattr(types, s) for s in
        "BuiltinFunctionType BuiltinMethodType  ClassType "
        "CodeType FileType FrameType FunctionType GetSetDescriptorType "
        "LambdaType MemberDescriptorType MethodType ModuleType "
        "SliceType TypeType TracebackType UnboundMethodType XRangeType".split()
        if hasattr(types, s)) + (WatchEvalError,)

STR_SAFE_TYPES = get_str_safe_types()

# }}}


# {{{ widget

class VariableWidget(urwid.FlowWidget):
    def __init__(self, prefix, var_label, value_str, id_path=None, attr_prefix=None,
            watch_expr=None, iinfo=None):
        self.prefix = prefix
        self.var_label = var_label
        self.value_str = value_str
        self.id_path = id_path
        self.attr_prefix = attr_prefix or "var"
        self.watch_expr = watch_expr
        if iinfo is None:
            self.wrap = CONFIG["wrap_variables"]
        else:
            self.wrap = iinfo.wrap

    def selectable(self):
        return True

    SIZE_LIMIT = 20

    def _get_text(self, size):
        maxcol = size[0] - len(self.prefix)  # self.prefix is a padding
        var_label = self.var_label or ''
        value_str = self.value_str or ''
        alltext = var_label + ": " + value_str
        # The first line is not indented
        firstline = self.prefix + alltext[:maxcol]
        if not alltext[maxcol:]:
            return [firstline]
        fulllines, rest = divmod(len(alltext) - maxcol, maxcol - 2)
        restlines = [alltext[(maxcol - 2)*i + maxcol:(maxcol - 2)*i + 2*maxcol - 2]
            for i in xrange(fulllines + bool(rest))]
        return [firstline] + ["  " + self.prefix + i for i in restlines]

    def rows(self, size, focus=False):
        if self.wrap:
            return len(self._get_text(size))

        if (self.value_str is not None
                and self.var_label is not None
                and len(self.prefix) + len(self.var_label) > self.SIZE_LIMIT):
            return 2
        else:
            return 1

    def render(self, size, focus=False):
        from pudb.ui_tools import make_canvas

        maxcol = size[0]
        if focus:
            apfx = "focused "+self.attr_prefix+" "
        else:
            apfx = self.attr_prefix+" "

        var_label = self.var_label or ''

        if self.wrap:
            text = self._get_text(size)

            extralabel_full, extralabel_rem = divmod(len(var_label[maxcol:]), maxcol)
            totallen = sum([len(i) for i in text])
            labellen = (
                    len(self.prefix)  # Padding of first line

                    + (len(self.prefix) + 2)  # Padding of subsequent lines
                    * (extralabel_full + bool(extralabel_rem))

                    + len(var_label)

                    + 2  # for ": "
                    )

            _attr = [(apfx+"label", labellen), (apfx+"value", totallen - labellen)]
            from urwid.util import rle_subseg

            fullcols, rem = divmod(totallen, maxcol)

            attr = [rle_subseg(_attr, i*maxcol, (i + 1)*maxcol)
                for i in xrange(fullcols + bool(rem))]

            return make_canvas(text, attr, maxcol, apfx+"value")

        if self.value_str is not None:
            if self.var_label is not None:
                if len(self.prefix) + len(self.var_label) > self.SIZE_LIMIT:
                    # label too long? generate separate value line
                    text = [self.prefix + self.var_label,
                            self.prefix+"  " + self.value_str]

                    attr = [[(apfx+"label", len(self.prefix)+len(self.var_label))],
                            [(apfx+"value", len(self.prefix)+2+len(self.value_str))]]
                else:
                    text = [self.prefix + self.var_label + ": " + self.value_str]

                    attr = [[
                            (apfx+"label", len(self.prefix)+len(self.var_label)+2),
                            (apfx+"value", len(self.value_str)),
                            ]]
            else:
                text = [self.prefix + self.value_str]

                attr = [[
                        (apfx+"label", len(self.prefix)),
                        (apfx+"value", len(self.value_str)),
                        ]]
        else:
            text = [self.prefix + self.var_label]

            attr = [[(apfx+"label", len(self.prefix) + len(self.var_label)), ]]

        # Ellipses to show text was cut off
        #encoding = urwid.util.detected_encoding

        if False:  # encoding[:3] == "UTF":
            # Unicode is supported, use single character ellipsis
            for i in xrange(len(text)):
                if len(text[i]) > maxcol:
                    text[i] = (unicode(text[i][:maxcol-1])
                    + ELLIPSIS + unicode(text[i][maxcol:]))
                    # XXX: This doesn't work.  It just gives a ?
                    # Strangely, the following does work (it gives the …
                    # three characters from the right):
                    #
                    # text[i] = (unicode(text[i][:maxcol-3])
                    # + unicode(u'…')) + unicode(text[i][maxcol-2:])
        else:
            for i in xrange(len(text)):
                if len(text[i]) > maxcol:
                    text[i] = text[i][:maxcol-3] + "..."

        return make_canvas(text, attr, maxcol, apfx+"value")

    def keypress(self, size, key):
        return key


custom_stringifier_dict = {}


def type_stringifier(value):
    if HAVE_NUMPY and isinstance(value, numpy.ndarray):
        return "ndarray %s %s" % (value.dtype, value.shape)
    elif isinstance(value, STR_SAFE_TYPES):
        try:
            return str(value)
        except Exception:
            pass

    return type(value).__name__


def get_stringifier(iinfo):
    if iinfo.display_type == "type":
        return type_stringifier
    elif iinfo.display_type == "repr":
        return repr
    elif iinfo.display_type == "str":
        return str
    else:
        try:
            if not custom_stringifier_dict:  # Only execfile once
                from os.path import expanduser
                execfile(expanduser(iinfo.display_type), custom_stringifier_dict)
        except:
            print("Error when importing custom stringifier:")
            from traceback import print_exc
            print_exc()
            raw_input("Hit enter:")
            return lambda value: "ERROR: Invalid custom stringifier file."
        else:
            if "pudb_stringifier" not in custom_stringifier_dict:
                print("%s does not contain a function named pudb_stringifier at"
                      "the module level." % iinfo.display_type)
                raw_input("Hit enter:")
                return lambda value: ("ERROR: Invalid custom stringifier file: "
                "pudb_stringifer not defined.")
            else:
                return (lambda value:
                    str(custom_stringifier_dict["pudb_stringifier"](value)))


# tree walking ----------------------------------------------------------------
class ValueWalker:

    PREFIX = "| "

    def __init__(self, frame_var_info):
        self.frame_var_info = frame_var_info

    def walk_value(self, prefix, label, value, id_path=None, attr_prefix=None):
        if id_path is None:
            id_path = label

        iinfo = self.frame_var_info.get_inspect_info(id_path, read_only=True)

        if isinstance(value, integer_types + (float, complex)):
            self.add_item(prefix, label, repr(value), id_path, attr_prefix)
        elif isinstance(value, string_types):
            self.add_item(prefix, label, repr(value), id_path, attr_prefix)
        else:
            try:
                displayed_value = get_stringifier(iinfo)(value)
            except Exception:
                ## Unfortunately, anything can happen when calling str() or
                ## repr() on a random object.
                displayed_value = type_stringifier(value) \
                                + " (!! %s error !!)" % iinfo.display_type

            self.add_item(prefix, label,
                displayed_value, id_path, attr_prefix)

            if not iinfo.show_detail:
                return

            # set ---------------------------------------------------------
            if isinstance(value, (set, frozenset)):
                for i, entry in enumerate(value):
                    if i % 10 == 0 and i:
                        cont_id_path = "%s.cont-%d" % (id_path, i)
                        if not self.frame_var_info.get_inspect_info(
                                cont_id_path, read_only=True).show_detail:
                            self.add_item(prefix+self.PREFIX, "...",
                                    None, cont_id_path)
                            break

                    self.walk_value(prefix+self.PREFIX, None, entry,
                        "%s[%d]" % (id_path, i))
                if not value:
                    self.add_item(prefix+self.PREFIX, "<empty>", None)
                return

            # containers --------------------------------------------------
            key_it = None
            try:
                l = len(value)
            except:
                pass
            else:
                try:
                    value[0]
                except IndexError:
                    key_it = []
                except:
                    pass
                else:
                    key_it = xrange(l)

            try:
                key_it = value.iterkeys()
            except:
                pass

            if key_it is not None:
                cnt = 0
                for key in key_it:
                    if cnt % 10 == 0 and cnt:
                        cont_id_path = "%s.cont-%d" % (id_path, cnt)
                        if not self.frame_var_info.get_inspect_info(
                                cont_id_path, read_only=True).show_detail:
                            self.add_item(
                                prefix+self.PREFIX, "...", None, cont_id_path)
                            break

                    self.walk_value(prefix+self.PREFIX, repr(key), value[key],
                        "%s[%r]" % (id_path, key))
                    cnt += 1
                if not cnt:
                    self.add_item(prefix+self.PREFIX, "<empty>", None)
                return

            # class types -------------------------------------------------
            key_its = []

            try:
                key_its.append(dir(value))
            except:
                pass

            keys = [key
                    for ki in key_its
                    for key in ki]
            keys.sort()

            cnt_omitted = 0

            for key in keys:
                if key[0] == "_" and not iinfo.show_private_members:
                    cnt_omitted += 1
                    continue

                try:
                    attr_value = getattr(value, key)
                except:
                    attr_value = WatchEvalError()

                self.walk_value(prefix+self.PREFIX,
                        ".%s" % key, attr_value,
                        "%s.%s" % (id_path, key))

            if not keys:
                if cnt_omitted:
                    self.add_item(prefix+self.PREFIX,
                            "<omitted private attributes>", None)
                else:
                    self.add_item(prefix+self.PREFIX, "<empty>", None)

            if not key_its:
                self.add_item(prefix+self.PREFIX, "<?>", None)


class BasicValueWalker(ValueWalker):
    def __init__(self, frame_var_info):
        ValueWalker.__init__(self, frame_var_info)

        self.widget_list = []

    def add_item(self, prefix, var_label, value_str, id_path=None, attr_prefix=None):
        iinfo = self.frame_var_info.get_inspect_info(id_path, read_only=True)
        if iinfo.highlighted:
            attr_prefix = "highlighted var"

        self.widget_list.append(VariableWidget(prefix, var_label, value_str,
            id_path, attr_prefix, iinfo=iinfo))


class WatchValueWalker(ValueWalker):
    def __init__(self, frame_var_info, widget_list, watch_expr):
        ValueWalker.__init__(self, frame_var_info)
        self.widget_list = widget_list
        self.watch_expr = watch_expr

    def add_item(self, prefix, var_label, value_str, id_path=None, attr_prefix=None):
        iinfo = self.frame_var_info.get_inspect_info(id_path, read_only=True)
        if iinfo.highlighted:
            attr_prefix = "highlighted var"

        self.widget_list.append(
                VariableWidget(prefix, var_label, value_str, id_path, attr_prefix,
                    watch_expr=self.watch_expr, iinfo=iinfo))


class TopAndMainVariableWalker(ValueWalker):
    def __init__(self, frame_var_info):
        ValueWalker.__init__(self, frame_var_info)

        self.main_widget_list = []
        self.top_widget_list = []

        self.top_id_path_prefixes = []

    def add_item(self, prefix, var_label, value_str, id_path=None, attr_prefix=None):
        iinfo = self.frame_var_info.get_inspect_info(id_path, read_only=True)
        if iinfo.highlighted:
            attr_prefix = "highlighted var"

        repeated_at_top = iinfo.repeated_at_top
        if repeated_at_top and id_path is not None:
            self.top_id_path_prefixes.append(id_path)

        for tipp in self.top_id_path_prefixes:
            if id_path is not None and id_path.startswith(tipp):
                repeated_at_top = True

        if repeated_at_top:
            self.top_widget_list.append(VariableWidget(prefix, var_label,
                value_str, id_path, attr_prefix, iinfo=iinfo))

        self.main_widget_list.append(VariableWidget(prefix, var_label,
            value_str, id_path, attr_prefix, iinfo=iinfo))

# }}}


# {{{ top level

SEPARATOR = urwid.AttrMap(urwid.Text(""), "variable separator")


def make_var_view(frame_var_info, locals, globals):
    vars = list(locals.keys())
    vars.sort(key=lambda n: n.lower())

    tmv_walker = TopAndMainVariableWalker(frame_var_info)
    ret_walker = BasicValueWalker(frame_var_info)
    watch_widget_list = []

    for watch_expr in frame_var_info.watches:
        try:
            value = eval(watch_expr.expression, globals, locals)
        except:
            value = WatchEvalError()

        WatchValueWalker(frame_var_info, watch_widget_list, watch_expr) \
                .walk_value("", watch_expr.expression, value)

    if "__return__" in vars:
        ret_walker.walk_value("", "Return", locals["__return__"],
                attr_prefix="return")

    for var in vars:
        if not var[0] in "_.":
            tmv_walker.walk_value("", var, locals[var])

    result = tmv_walker.main_widget_list

    if watch_widget_list:
        result = (watch_widget_list + [SEPARATOR] + result)

    if tmv_walker.top_widget_list:
        result = (tmv_walker.top_widget_list + [SEPARATOR] + result)

    if ret_walker.widget_list:
        result = (ret_walker.widget_list + result)

    return result


class FrameVarInfoKeeper(object):
    def __init__(self):
        self.frame_var_info = {}

    def get_frame_var_info(self, read_only, ssid=None):
        if ssid is None:
            ssid = self.debugger.get_stack_situation_id()
        if read_only:
            return self.frame_var_info.get(ssid, FrameVarInfo())
        else:
            return self.frame_var_info.setdefault(ssid, FrameVarInfo())

# }}}

# vim: foldmethod=marker

########NEW FILE########
__FILENAME__ = __main__
if __name__ == "__main__":
    from pudb.run import main
    main()

########NEW FILE########
__FILENAME__ = test-api
def f():
    fail

from pudb import runcall
runcall(f)

########NEW FILE########
__FILENAME__ = test-encoding
def f(encoding=None):
	print 'ENCODING:', encoding

from pudb import runcall
runcall(f)

########NEW FILE########
__FILENAME__ = test-postmortem
def f():
    fail

try:
    f()
except:
    from pudb import post_mortem
    post_mortem()

########NEW FILE########
