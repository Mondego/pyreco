__FILENAME__ = actual
import sublime
import sublime_plugin

from .edit import Edit
from .view import ViewMeta
from .vim import Vim, VISUAL_MODES


class ActualVim(ViewMeta):
    def __init__(self, view):
        super().__init__(view)
        if view.settings().get('actual_proxy'):
            return

        view.settings().set('actual_intercept', True)
        view.settings().set('actual_mode', True)
        self.vim = vim = Vim(view, update=self.update, modify=self.modify)
        vim.set_path(view.file_name())
        vim.insert(0, view.substr(sublime.Region(0, view.size())))
        vim.init_done()
        # view.set_read_only(False)

        self.output = None

    @property
    def actual(self):
        return self.view and self.view.settings().get('actual_mode')

    def monitor(self):
        if self.output:
            return

        window = sublime.active_window()
        self.output = output = window.new_file()
        ActualVim.views[output.id()] = self

        output.settings().set('actual_proxy', True)
        output.set_read_only(True)
        output.set_scratch(True)
        output.set_name('(tty)')
        output.settings().set('actual_intercept', True)
        output.settings().set('actual_mode', True)

        with Edit(output) as edit:
            edit.insert(0, self.vim.tty.dump())
        self.vim.monitor = output

        # move the monitor view to a different group
        if window.num_groups() > 1:
            target = int(not window.active_group())
            window.set_view_index(output, target, 0)

    def update(self, vim, dirty, moved):
        mode = vim.mode
        view = vim.view
        tty = vim.tty

        if vim.cmdline:
            view.set_status('actual', vim.cmdline)
        else:
            view.erase_status('actual')

        if tty.row == tty.rows and tty.col > 0:
            char = tty.buf[tty.row - 1][0]
            if char in ':/':
                if vim.panel:
                    # we already have a panel
                    panel = vim.panel.panel
                    with Edit(panel) as edit:
                        edit.replace(sublime.Region(0, panel.size()), vim.cmdline)
                else:
                    # vim is prompting for input
                    row, col = (tty.row - 1, tty.col - 1)
                    vim.panel = ActualPanel(self)
                    vim.panel.show(char)
                return
        elif vim.panel:
            vim.panel.close()
            vim.panel = None

        if mode in VISUAL_MODES:
            def select():
                v = ActualVim.get(view)
                start = vim.visual
                end = (vim.row, vim.col)
                regions = v.visual(vim.mode, start, end)
                view.sel().clear()
                for r in regions:
                    view.sel().add(sublime.Region(*r))

            Edit.defer(view, select)
            return
        else:
            vim.update_cursor()

    def modify(self, vim):
        pass

    def close(self, view):
        if self.output:
            self.output.close()
            self.output = None

        if view == self.view:
            self.view.close()
            self.vim.close()

    def set_path(self, path):
        self.vim.set_path(path)

class ActualKeypress(sublime_plugin.TextCommand):
    def run(self, edit, key):
        v = ActualVim.get(self.view, exact=False)
        if v and v.actual:
            v.vim.press(key)


class ActualListener(sublime_plugin.EventListener):
    def on_new_async(self, view):
        ActualVim.get(view)

    def on_load(self, view):
        ActualVim.get(view)

    def on_selection_modified_async(self, view):
        v = ActualVim.get(view, create=False)
        if v and v.actual:
            if not v.sel_changed():
                return

            sel = view.sel()
            if not sel:
                return

            vim = v.vim
            sel = sel[0]
            def cursor(args):
                buf, lnum, col, off = [int(a) for a in args.split(' ')]
                # see if we changed selection on Sublime's side
                if vim.mode in VISUAL_MODES:
                    start = vim.visual
                    end = lnum, col + 1
                    region = v.visual(vim.mode, start, end)[0]
                    if (sel.a, sel.b) == region:
                        return

                if off == sel.b or off > view.size():
                    return

                # selection didn't match Vim's, so let's change Vim's.
                if sel.b == sel.a:
                    if vim.mode in VISUAL_MODES:
                        # vim.type('{}go'.format(sel.b))
                        vim.press('escape')

                    vim.set_cursor(sel.b, callback=vim.update_cursor)
                else:
                    # this is currently broken
                    return
                    if vim.mode != 'n':
                        vim.press('escape')
                    a, b = sel.a, sel.b
                    if b > a:
                        a += 1
                    else:
                        b += 1
                    vim.type('{}gov{}go'.format(a, b))

            vim.get_cursor(cursor)

    def on_modified(self, view):
        v = ActualVim.get(view, create=False)
        if v:
            v.sel_changed()

    def on_close(self, view):
        v = ActualVim.get(view, create=False)
        if v:
            v.close(view)

    def on_post_save_async(self, view):
        v = ActualVim.get(view, create=False)
        if v:
            v.set_path(view.file_name())

class ActualPanel:
    def __init__(self, actual):
        self.actual = actual
        self.vim = actual.vim
        self.view = actual.view
        self.panel = None

    def close(self):
        if self.panel:
            self.panel.close()

    def show(self, char):
        window = self.view.window()
        self.panel = window.show_input_panel('Vim', char, self.on_done, None, self.on_cancel)
        settings = self.panel.settings()
        settings.set('actual_intercept', True)
        settings.set('actual_proxy', self.view.id())
        ActualVim.views[self.panel.id()] = self.actual

    def on_done(self, text):
        self.vim.press('enter')
        self.vim.panel = None

    def on_cancel(self):
        self.vim.press('escape')
        self.vim.panel = None

########NEW FILE########
__FILENAME__ = commands
from .actual import ActualVim
import sublime_plugin


class actual_monitor(sublime_plugin.WindowCommand):
    @property
    def view(self):
        return self.window.active_view()

    def run(self):
        v = ActualVim.get(self.view)
        if v and v.actual:
            v.monitor()

    def is_enabled(self):
        return bool(self.view.settings().get('actual_mode'))

########NEW FILE########
__FILENAME__ = edit
# edit.py
# buffer editing for both ST2 and ST3 that "just works"

import inspect
import sublime
import sublime_plugin

try:
    sublime.edit_storage
except AttributeError:
    sublime.edit_storage = {}

def run_callback(func, *args, **kwargs):
    spec = inspect.getfullargspec(func)
    if spec.args or spec.varargs:
        return func(*args, **kwargs)
    else:
        return func()


class EditFuture:
    def __init__(self, func):
        self.func = func

    def resolve(self, view, edit):
        return self.func(view, edit)


class EditStep:
    def __init__(self, cmd, *args):
        self.cmd = cmd
        self.args = args

    def run(self, view, edit):
        if self.cmd == 'callback':
            return run_callback(self.args[0], view, edit)

        def insert(edit, pos, text):
            pos = min(view.size(), pos)
            view.insert(edit, pos, text)

        funcs = {
            'insert': insert,
            'erase': view.erase,
            'replace': view.replace,
        }
        func = funcs.get(self.cmd)
        if func:
            args = self.resolve_args(view, edit)
            func(edit, *args)

    def resolve_args(self, view, edit):
        args = []
        for arg in self.args:
            if isinstance(arg, EditFuture):
                arg = arg.resolve(view, edit)
            args.append(arg)
        return args


class Edit:
    def __init__(self, view):
        self.view = view
        self.steps = []

    def __nonzero__(self):
        return bool(self.steps)

    @classmethod
    def future(cls, func):
        return EditFuture(func)

    @classmethod
    def defer(cls, view, func):
        with Edit(view) as edit:
            edit.callback(func)

    def step(self, cmd, *args):
        step = EditStep(cmd, *args)
        self.steps.append(step)

    def insert(self, point, string):
        self.step('insert', point, string)

    def erase(self, region):
        self.step('erase', region)

    def replace(self, region, string):
        self.step('replace', region, string)

    def callback(self, func):
        self.step('callback', func)

    def reselect(self, pos):
        def select(view, edit):
            region = pos
            if hasattr(pos, '__call__'):
                region = run_callback(pos, view)

            if isinstance(region, int):
                region = sublime.Region(region, region)
            elif isinstance(region, (tuple, list)):
                region = sublime.Region(*region)

            view.sel().clear()
            view.sel().add(region)
            view.show(region, False)

        self.callback(select)

    def append(self, text):
        self.insert(self.view.size(), text)

    def run(self, view, edit):
        read_only = False
        if view.is_read_only():
            read_only = True
            view.set_read_only(False)

        for step in self.steps:
            step.run(view, edit)

        if read_only:
            view.set_read_only(True)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        view = self.view
        if sublime.version().startswith('2'):
            edit = view.begin_edit()
            self.run(edit)
            view.end_edit(edit)
        else:
            key = str(hash(tuple(self.steps)))
            sublime.edit_storage[key] = self.run
            view.run_command('apply_edit', {'key': key})


class apply_edit(sublime_plugin.TextCommand):
    def run(self, edit, key):
        sublime.edit_storage.pop(key)(self.view, edit)

########NEW FILE########
__FILENAME__ = term
#!/usr/bin/env python2
# term.py
# terminal buffer emulator

import re
import sys
import threading
import time
import weakref
from queue import Queue, Empty


def intgroups(m):
    return [int(d) for d in m.groups() if d and d.isdigit()]


class Row(object):
    def __init__(self, buf, data=None):
        if not isinstance(buf, weakref.ProxyType):
            buf = weakref.proxy(buf)
        self.buf = buf
        self.cols = buf.cols
        if data:
            self.data = data[:]
        else:
            self.reset()

    def copy(self):
        return Row(self.buf, data=self.data)

    def reset(self):
        self.data = [' ' for i in range(self.cols)]

    def __add__(self, o):
        if isinstance(o, list):
            return self.data + o
        elif isinstance(o, Row):
            return self.data + o.data
        else:
            raise TypeError('expected int or Row, found {}'.format(type(o)))

    def __mul__(self, n):
        if isinstance(n, int):
            return [self.copy() for i in range(n)]
        else:
            raise TypeError('expected int, found {}'.format(type(n)))

    def __iter__(self):
        return iter(self.data)

    def __str__(self):
        return ''.join(self)

    def __getitem__(self, col):
        return self.data[col]

    def __setitem__(self, col, value):
        dirty = False
        if self.data[col] != value:
            dirty = True
        self.data[col] = value
        if dirty:
            self.buf.dirty = True


class Buffer(object):
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.reset()
        self.dirty = False

    def reset(self):
        self.data = Row(self) * self.rows
        self.dirty = True

    def __getitem__(self, row):
        return self.data[row]

    def __setitem__(self, row, value):
        if isinstance(value, list):
            self.data[row] = Row(self, data=value)
        else:
            raise TypeError('expected list, found {}'.format(type(value)))

    def __iter__(self):
        return iter(self.data)

    def insert(self, pos):
        self.data.insert(pos, Row(self))

    def __delitem__(self, row):
        del self.data[row]


class Terminal(object):
    ESCAPE = '\033'

    def __init__(self, cols, rows, debug=False, callback=None, fps=60):
        self.debug = debug
        self.cols = cols
        self.rows = rows
        self.pending = ''
        # chars are stored at self.buf[row][col]
        self.callback = callback
        self.fps = fps
        self.frame = 1.0 / fps
        self.buf = Buffer(self.rows, self.cols)
        self.row = 1
        self.col = 1
        self.reset()

        self.smooth_lock = threading.RLock()
        self.smooth_queue = Queue()
        self.moved = False

    def reset(self):
        self.cursor = True
        self.scroll = (1, self.rows)
        self.clear()
        self.move(1, 1)

    def clear(self):
        self.buf.reset()

    def hide_cursor(self):
        self.cursor = False

    def show_cursor(self):
        self.cursor = True

    @property
    def dirty(self):
        return self.buf.dirty

    @dirty.setter
    def dirty(self, value):
        self.buf.dirty = value

    def move(self, row=None, col=None, rel=False):
        if rel:
            row = self.row + (row or 0)
            col = self.col + (col or 0)
        else:
            if row is None:
                row = self.row
            if col is None:
                col = self.col

        if col > self.cols:
            row += 1
            col = 1
        if col < 1:
            col = self.cols
            row -= 1

        start, end = self.scroll
        if row > end:
            self.del_lines(num=row - end, row=start)
            row = end

        if self.row != row or self.col != col:
            self.moved = True
            self.row = max(1, min(row, self.rows))
            self.col = max(1, min(col, self.cols))

    def rel(self, row=None, col=None):
        self.move(row, col, rel=True)

    def erase(self, start, end):
        save = self.row, self.col
        for row in range(start[0], end[0] + 1):
            if row == start[0]:
                left = start[1]
                right = end[1]
            elif row == end[0]:
                left = 0
                right = end[1]
            else:
                left = 0
                right = self.cols

            for col in range(left, right + 1):
                self.move(row, col)
                self.puts(' ', move=False)
        self.row, self.col = save

    def insert_lines(self, num=1, row=None):
        if row is None:
            row = self.row

        for i in range(num):
            del self.buf[self.scroll[1] - 1]
            self.buf.insert(row - 1)

    def del_lines(self, num=1, row=None):
        if row is None:
            row = self.row

        for i in range(num):
            del self.buf[row - 1]
            self.buf.insert(self.scroll[1] - 1)

    def puts(self, s, move=True):
        if isinstance(s, int):
            s = chr(s)
        for c in s:
            self.buf[self.row-1][self.col-1] = c
            if move:
                self.rel(col=1)

    def sequence(self, data, i):
        if self.debug:
            print('control character!', repr(data[i:i+8]))
        return 1

    def pre(self, data, i):
        b = data[i]
        # print(repr(data[i:i+8]))
        if b == self.ESCAPE:
            return self.sequence(data, i)
        elif b == '\b':
            self.rel(col=-1)
            self.puts(' ', move=False)
            return 1
        elif b == '\r':
            self.move(col=1)
            return 1
        elif b == '\n':
            self.move(self.row + 1, 1)
            return 1
        elif b == '\x07':
            # beep
            return 1
        else:
            if self.debug:
                sys.stdout.write(b)
            return None

    def append(self, data):
        if isinstance(data, bytes):
            data = data.decode('utf8', 'replace')
        data = self.pending + data
        self.pending = ''
        i = 0
        while i < len(data):
            pre = self.pre(data, i)
            if pre == 0:
                if i > len(data) - 15 and data[i] == self.ESCAPE:
                    # we might need more data to complete the sequence
                    self.pending = data[i:]
                    return
                else:
                    # looks like we don't know how to read this sequence
                    if self.debug:
                        print('Unknown VT100 sequence:', repr(data[i:i+8]))
                    i += 1
                    continue
            elif pre is not None:
                i += pre
                self.notify()
                continue
            else:
                self.puts(data[i])
                self.notify()
                i += 1

    def notify(self, thread=False):
        if not self.callback:
            return

        if not thread:
            threading.Thread(target=self.notify, kwargs={'thread': True}).start()
            return

        self.smooth_queue.put(1)

        if not self.smooth_lock.acquire(False):
            return

        try:
            while True:
                while True:
                    try:
                        self.smooth_queue.get(False)
                    except Empty:
                        break

                # make a best effort to BOTH not block the caller
                # and not call the callback twice at the same time
                if self.dirty or self.moved:
                    dirty, moved = self.dirty, self.moved
                    self.dirty = False
                    self.moved = False
                    time.sleep(self.frame)
                    self.callback(self, dirty, moved)

                try:
                    self.smooth_queue.get(False)
                except Empty:
                    break
        finally:
            self.smooth_lock.release()

    def dump(self):
        return ''.join(col for row in self.buf for col in row + ['\n'])

    def __str__(self):
        return '<{} ({},{})+{}x{}>'.format(
            self.__class__,
            self.row, self.col, self.cols, self.rows)


class VT100(Terminal):
    control = None
    KEYMAP = {
        'backspace': '\b',
        'enter': '\n',
        'escape': '\033',
        'space': ' ',
        'tab': '\t',
        'up': '\033[A',
        'down': '\033[B',
        'right': '\033[C',
        'left': '\033[D',
    }

    @classmethod
    def map(cls, key):
        if '+' in key and key != '+':
            mods, key = key.rsplit('+', 1)
            mods = mods.split('+')
            if mods == ['ctrl']:
                b = ord(key)
                if b >= 63 and b < 96:
                    return chr((b - 64) % 128)

        return cls.KEYMAP.get(key, key)

    def __init__(self, *args, **kwargs):
        if not self.control:
            self.control = []

        # control character handlers
        REGEX = (
            # cursor display
            (r'\[\?(12;)?(25|50)l', lambda g: self.hide_cursor()),
            (r'\[\?(12;)?(25|50)h', lambda g: self.show_cursor()),
            # cursor motion
            (r'\[(\d+)A', lambda g: self.rel(-g[0], 0)),
            (r'\[(\d+)B', lambda g: self.rel(g[0], 0)),
            (r'\[(\d+)C', lambda g: self.rel(0, g[0])),
            (r'\[(\d+)D', lambda g: self.rel(0, -g[0])),
            (r'\[(\d+);(\d+)[Hf]', lambda g: self.move(g[0], g[1])),
            (r'\[(\d+)G', lambda g: self.move(self.row, g[0])),
            (r'\[(\d*)d', lambda g: self.move(row=g[0] or 1)),
            (r'\[(\d*)e', lambda g: self.rel(row=g[0] or 1)),
            # set scrolling region
            (r'\[(\d+);(\d+)r', lambda g: self.set_scroll(g[0], g[1])),
            # insert lines under cursor
            (r'\[(\d+)L', lambda g: self.insert_lines(g[0])),
            # remove lines from cursor
            (r'\[(\d+)M', lambda g: self.del_lines(g[0])),
            # erase from cursor to end of screen
            (r'\[0?J', lambda g: self.erase(
                (self.row, self.col), (self.rows, self.cols))),
            # noop
            (r'\[\?(\d+)h', None),
            ## set cursor attributes
            (r'\[(\d+|;)*m', None),
            (r'\[\??(\d+)l', None),
            # change character set
            (r'\([AB012]', None),

        )
        SIMPLE = (
            ('[A', lambda: self.rel(row=-1)),
            ('[B', lambda: self.rel(row=1)),
            ('[C', lambda: self.rel(col=1)),
            ('[D', lambda: self.rel(col=1)),
            ('[H', lambda: self.move(1, 1)),
            ('[2J', lambda: self.clear()),
            ('[K', lambda: self.erase(
                (self.row, self.col), (self.row, self.cols))),
            ('[L', lambda: self.insert_lines(1)),
            ('[M', lambda: self.del_lines(1)),
            # noop
            ('>', None),
            ('<', None),
            ('=', None),
        )

        for r, func in REGEX:
            r = re.compile(r)
            self.control.append((r, func))

        for s, func in SIMPLE:
            r = re.compile(re.escape(s))
            if func:
                def wrap(func):
                    return lambda g: func()

                func = wrap(func)
            self.control.append((r, func))

        super(self.__class__, self).__init__(*args, **kwargs)

    def sequence(self, data, i):
        def call(func, s, groups):
            if func:
                if self.debug:
                    print('<ESC "{}">'.format(s))
                func(groups)
            else:
                if self.debug:
                    print('<NOOP "{}">'.format(s))
            return len(s)

        context = data[i+1:i+20].split('\033')[0]
        if not context:
            return 0
        for r, func in self.control:
            m = r.match(context)
            if m:
                return 1 + call(func, m.group(), intgroups(m))

        return 0

    def set_scroll(self, start, end):
        self.scroll = (start, end)

if __name__ == '__main__':
    def debug():
        v = VT100(142, 32, debug=True)
        data = sys.stdin.read()
        print('-= begin input =-')
        print(repr(data))
        print('-= begin parsing =-')
        for b in data:
            v.append(b)
        print('-= begin dump =-')
        print(repr(v.dump()))
        print('-= begin output =-')
        sys.stdout.write(v.dump())

    def static():
        v = VT100(142, 32)
        data = sys.stdin.read()
        v.append(data)
        sys.stdout.write(v.dump())

    def stream():
        v = VT100(80, 24)
        while True:
            b = sys.stdin.read(1)
            if not b:
                break
            v.append(b)
            print('\r\n'.join(v.dump().rsplit('\n')[-3:-1]) + '\r')
            print(v.row, v.col, '\r')
            # sys.stdout.write(v.dump() + '\r')
            # sys.stdout.flush()

    stream()

########NEW FILE########
__FILENAME__ = view
import sublime
import traceback


def copy_sel(sel):
    if isinstance(sel, sublime.View):
        sel = sel.sel()
    return [(r.a, r.b) for r in sel]


class ViewMeta:
    views = {}

    @classmethod
    def get(cls, view, create=True, exact=True):
        vid = view.id()
        m = cls.views.get(vid)
        if not m and create:
            try:
                m = cls(view)
            except Exception:
                traceback.print_exc()
                return
            cls.views[vid] = m
        elif m and exact and m.view != view:
            return None

        return m

    def __init__(self, view):
        self.view = view
        self.last_sel = copy_sel(view)
        self.buf = ''

    def sel_changed(self):
        new_sel = copy_sel(self.view)
        changed = new_sel != self.last_sel
        self.last_sel = new_sel
        return changed

    def visual(self, mode, a, b):
        view = self.view
        regions = []
        sr, sc = a[0] - 1, a[1] - 1
        er, ec = b[0] - 1, b[1] - 1

        a = view.text_point(sr, sc)
        b = view.text_point(er, ec)

        if mode == 'V':
            # visual line mode
            if a > b:
                start = view.line(a).b
                end = view.line(b).a
            else:
                start = view.line(a).a
                end = view.line(b).b

            regions.append((start, end))
        elif mode == 'v':
            # visual mode
            if a > b:
                a += 1
            else:
                b += 1
            regions.append((a, b))
        elif mode in ('^V', '\x16'):
            # visual block mode
            left = min(sc, ec)
            right = max(sc, ec) + 1
            top = min(sr, er)
            bot = max(sr, er)
            end = view.text_point(top, right)

            for i in range(top, bot + 1):
                line = view.line(view.text_point(i, 0))
                _, end = view.rowcol(line.b)
                if left <= end:
                    a = view.text_point(i, left)
                    b = view.text_point(i, min(right, end))
                    regions.append((a, b))

        return regions

    def size(self):
        return len(self.buf)

########NEW FILE########
__FILENAME__ = vim
#!/usr/bin/env python2
# vim.py
# launches and manages a headless vim instance

import itertools
import os
import pty
import select
import socket
import sublime
import subprocess
import threading

from .edit import Edit
from .term import VT100


VISUAL_MODES = ('V', 'v', '^V', '\x16')
replace = [
    ('\\', '\\\\'),
    ('"', '\\"'),
    ('\n', '\\n'),
    ('\r', '\\r'),
    ('\t', '\\t'),
]


def encode(s, t=None):
    types = [
        (str, 'string'),
        ((int, float), 'number'),
        (bool, 'boolean'),
    ]
    if t is None:
        for typ, b in types:
            if isinstance(s, typ):
                t = b
                break
        else:
            return ''

    if t == 'string':
        for a, b in replace:
            s = s.replace(a, b)
        return '"' + s + '"'
    elif t == 'number':
        return str(s)
    elif t == 'boolean':
        return 'T' if s else 'F'
    elif t == 'color':
        if isinstance(s, (int, float)) or s:
            return str(s)
        else:
            return encode('none')


def decode(s, t=None):
    if t is None:
        if s.startswith('"'):
            t = 'string'
        elif s.replace('.', '', 1).isdigit():
            t = 'number'
        elif s in 'TF':
            t = 'boolean'
        else:
            return s

    if t == 'string':
        s = s[1:-1]
        lookup = {r[1]: r[0] for r in replace}
        i = 0
        while i < len(s) - 1:
            cur = s[i:i+2]
            if cur in lookup:
                rep = lookup[cur]
                s = s[:i] + rep + s[i+2:]
                i += len(rep)
                continue

            i += 1

        return s
    elif t == 'number':
        return float(s)
    elif t == 'boolean':
        return True if s == 'T' else False
    else:
        return s


class VimSocket:
    def __init__(self, vim, view, callback=None):
        self.vim = vim
        self.view = view
        self.server = socket.socket()
        self.server.bind(('localhost', 0))
        self.server.listen(1)
        self.client = None
        self.extra = ''
        self.port = self.server.getsockname()[1]
        self.serial = itertools.count(start=2)
        self.callbacks = {}
        self.callback = callback
        self.preload = []

    def spawn(self):
        threading.Thread(target=self.loop).start()

    def active(self):
        return self.view.buffer_id() != 0 and self.server.fileno() >= 0

    def handle(self, data):
        view = self.view
        data = self.extra + data
        commands = data.split('\n')
        self.extra = commands.pop()
        edits = []
        for cmd in commands:
            if ':' in cmd:
                buf, cmd = cmd.split(':', 1)
                cmd, args = cmd.split('=', 1)
                if ' ' in args:
                    seq, args = args.split(' ', 1)
                else:
                    seq, args = args, None
                seq = int(seq)

                if cmd == 'insert':
                    pos, text = args.split(' ', 1)
                    text = decode(text, 'string')
                    pos = decode(pos)
                    edits.append(('insert', pos, text))
                elif cmd == 'remove':
                    pos, length = args.split(' ', 1)
                    pos, length = int(pos), int(length)
                    if length > 0:
                        edits.append(('erase', sublime.Region(pos, pos+length)))
                elif cmd == 'disconnect':
                    view.set_scratch(True)
                    raise socket.error
            else:
                if ' ' in cmd:
                    seq, cmd = cmd.split(' ', 1)
                else:
                    seq, cmd = cmd, ''
                if seq.isdigit():
                    seq = int(seq)
                    callback = self.callbacks.pop(seq, None)
                    if callback:
                        callback(cmd)

        if edits:
            def cursor(args):
                buf, lnum, col, off = [int(a) for a in args.split(' ')]
                with Edit(view) as edit:
                    for args in edits:
                        edit.step(*args)
                    edit.reselect(off)

                self.callback(self.vim)
            self.get_cursor(cursor)

    def send(self, data):
        if not self.client:
            self.preload.append(data)
            return

        try:
            data = (data + '\r\n').encode('utf8')
            self.client.send(data)
        except socket.error:
            self.close()

    def close(self, disconnect=False):
        self.view.close()
        if self.client:
            if disconnect:
                self.send('1:disconnect!1')
            self.client.close()

    def loop(self):
        sockets = [self.server]
        try:
            while self.active():
                try:
                    ready, _, _ = select.select(sockets, [], [], 0.1)
                except ValueError:
                    raise socket.error
                if not self.client:
                    if self.server in ready:
                        print('client connection')
                        self.client, addr = self.server.accept()
                        sockets = [self.client]
                        self.cmd('1', 'create')
                        for line in self.preload:
                            self.send(line)
                    else:
                        continue
                elif self.client in ready:
                    # we're willing to wait up to 1/120 of a second
                    # for a delete following an erase
                    # this and a big buffer prevent flickering.
                    data = self.client.recv(102400).decode('utf8')
                    if 'remove' in data and not 'insert' in data:
                        more, _, _ = select.select([self.client], [], [], 1.0 / 120)
                        if more:
                            data += self.client.recv(102400).decode('utf8')

                    # print('data:', data)
                    if data:
                        self.handle(data)
                    else:
                        break
        except socket.error:
            pass
        finally:
            self.close(disconnect=True)

    def cmd(self, buf, name, *args, **kwargs):
        seq = kwargs.get('seq', 1)
        sep = kwargs.get('sep', '!')
        cmd = '{}:{}{}{}'.format(buf, name, sep, seq)
        if args is not None:
            cmd += ' ' + ' '.join(encode(a) for a in args)
        self.send(cmd)

    def func(self, *args, **kwargs):
        return self.cmd(*args, sep='/', **kwargs)

    def add_callback(self, callback):
        if not callback:
            return None
        serial = next(self.serial)
        self.callbacks[serial] = callback
        return serial

    def get_cursor(self, callback):
        serial = self.add_callback(callback)
        self.func('1', 'getCursor', seq=serial)

    def set_cursor(self, offset, callback=None):
        serial = self.add_callback(callback)
        self.cmd('1', 'setDot', offset, seq=serial)

    def insert(self, offset, text):
        self.func('1', 'insert', offset, str(text or ''))

    def init_done(self):
        self.cmd('1', 'initDone')

    def set_path(self, path):
        self.cmd('1', 'setFullName', path)


class Vim:
    DEFAULT_CMD = ('vim',)

    @property
    def vimrc(self):
        return (
            '--cmd', 'set fileformat=unix',
            '--cmd', 'set lines={} columns={}'.format(self.rows, self.cols),
            '--cmd', '''set statusline=%{printf(\\"%d+%d,%s,%d+%d\\",line(\\".\\"),col(\\".\\"),mode(),line(\\"v\\"),col(\\"v\\"))},%M''',
            '--cmd', 'set laststatus=2',
            '--cmd', 'set shortmess=aoOtTWAI',
            '--cmd', 'set noswapfile',
        )

    def __init__(self, view, rows=24, cols=80, monitor=None, cmd=None, update=None, modify=None):
        self.view = view
        self.monitor = monitor
        self.rows = rows
        self.cols = cols
        self.cmd = cmd or self.DEFAULT_CMD
        self.update_callback = update
        self.modify_callback = modify

        self.proc = None
        self.input = None
        self.output = None
        self.row = self.col = 0
        self.mode = 'n'
        self.modified = False
        self.visual = (0, 0)
        self.visual_selected = False

        self.panel = None
        self.tty = None
        self.__serve()
        self.__spawn()

    def __spawn(self):
        master, slave = pty.openpty()
        devnul = open(os.devnull, 'r')
        cmd = self.cmd + ('-nb::{}'.format(self.port),) + self.vimrc
        self.proc = subprocess.Popen(
            cmd, stdin=slave, stdout=slave,
            stderr=devnul, close_fds=True)
        self.output = os.fdopen(master, 'rb')
        self.input = os.fdopen(master, 'wb')

        def pump():
            self.tty = v = VT100(self.cols, self.rows, callback=self._update)
            while True:
                b = self.output.read(1)
                if not b:
                    # TODO: subprocess closed tty. recover somehow?
                    break
                v.append(b)
        threading.Thread(target=pump).start()

    def __serve(self):
        self.socket = VimSocket(self, self.view, callback=self.modify_callback)
        self.port = self.socket.port
        self.socket.spawn()

    def _update(self, v, dirty, moved):
        data = v.dump()
        self.status, self.cmdline = [
            s.strip() for s in data.rsplit('\n')[-3:-1]
        ]
        try:
            if self.status.count('+') >= 2:
                pos, rest = self.status.split(',', 1)
                row, col = pos.split('+', 1)
                self.row, self.col = int(row), int(col)

                self.mode, vs, rest = rest.split(',', 2)

                a, b = vs.split('+', 1)
                self.modified = (rest == '+')
                self.visual = (int(a), int(b))
            # print(self.status)
        except ValueError:
            pass

        if self.monitor:
            with Edit(self.monitor) as edit:
                if dirty:
                    edit.erase(sublime.Region(0, self.monitor.size()))
                    edit.insert(0, data)
                    edit.reselect(
                        lambda view: view.text_point(v.row - 1, v.col - 1))

                def update_cursor(view, edit):
                    row, col = (self.row - 1, self.col + 1)
                    # see if it's prompting for input
                    if v.row == self.rows and v.col > 0:
                        char = v.buf[v.row - 1][0]
                        if char in ':/':
                            row, col = (v.row - 1, v.col - 1)
                    pos = view.text_point(row, col)
                    sel = sublime.Region(pos, pos)
                    view.add_regions(
                        'cursor', [sel], 'comment',
                        '', sublime.DRAW_EMPTY,
                    )
                if moved:
                    edit.callback(update_cursor)

        if self.update_callback:
            self.update_callback(self, dirty, moved)

    def send(self, b):
        # send input
        if self.input:
            self.input.write(b.encode('utf8'))
            self.input.flush()

    def press(self, *keys):
        for key in keys:
            b = VT100.map(key)
            self.send(b)

    def type(self, text):
        self.press(*list(text))

    def close(self):
        print('ending Vim')
        self.view.close()
        if self.panel:
            self.panel.close()
        if self.monitor:
            self.monitor.close()
        self.proc.kill()
        self.socket.close()

    def update_cursor(self, *args, **kwargs):
        def callback(args):
            buf, lnum, col, off = [int(a) for a in args.split(' ')]
            with Edit(self.view) as edit:
                edit.reselect(off)
        self.socket.get_cursor(callback)

    def get_cursor(self, callback):
        self.socket.get_cursor(callback)

    def set_cursor(self, offset, callback=None):
        self.socket.set_cursor(offset, callback=callback)

    def insert(self, offset, text):
        self.socket.insert(offset, text)

    def init_done(self):
        self.socket.init_done()

    def set_path(self, path):
        self.socket.set_path(path)

if __name__ == '__main__':
    import time

    v = Vim()
    time.sleep(3)
    v.send('i')
    while True:
        v.send('asdfjkl ')
        time.sleep(1)

########NEW FILE########
