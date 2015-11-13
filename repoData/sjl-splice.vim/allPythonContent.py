__FILENAME__ = splice
import vim, os, sys


# Add the library to the Python path.
for p in vim.eval("&runtimepath").split(','):
    plugin_dir = os.path.join(p, "autoload")
    if os.path.exists(os.path.join(plugin_dir, "splicelib")):
       if plugin_dir not in sys.path:
          sys.path.append(plugin_dir)
       break


import splicelib.init as splice


# Wrapper functions ----------------------------------------------------------------

def SpliceInit():
    splice.init()


def SpliceOriginal():
    splice.modes.current_mode.key_original()

def SpliceOne():
    splice.modes.current_mode.key_one()

def SpliceTwo():
    splice.modes.current_mode.key_two()

def SpliceResult():
    splice.modes.current_mode.key_result()


def SpliceGrid():
    splice.modes.key_grid()

def SpliceLoupe():
    splice.modes.key_loupe()

def SpliceCompare():
    splice.modes.key_compare()

def SplicePath():
    splice.modes.key_path()


def SpliceDiff():
    splice.modes.current_mode.key_diff()

def SpliceDiffoff():
    splice.modes.current_mode.key_diffoff()

def SpliceScroll():
    splice.modes.current_mode.key_scrollbind()

def SpliceLayout():
    splice.modes.current_mode.key_layout()

def SpliceNext():
    splice.modes.current_mode.key_next()

def SplicePrev():
    splice.modes.current_mode.key_prev()

def SpliceUse():
    splice.modes.current_mode.key_use()

def SpliceUse1():
    splice.modes.current_mode.key_use1()

def SpliceUse2():
    splice.modes.current_mode.key_use2()


########NEW FILE########
__FILENAME__ = init
import vim
import modes
from settings import setting
from util import buffers, keys, windows


CONFLICT_MARKER_START = '<<<<<<<'
CONFLICT_MARKER_MARK = '======='
CONFLICT_MARKER_END = '>>>>>>>'

def process_result():
    windows.close_all()
    buffers.result.open()

    lines = []
    in_conflict = False
    for line in buffers.result.lines:
        if in_conflict:
            if CONFLICT_MARKER_MARK in line:
                lines.append(line)
            if CONFLICT_MARKER_END in line:
                in_conflict = False
            continue

        if CONFLICT_MARKER_START in line:
            in_conflict = True
            continue

        lines.append(line)

    buffers.result.set_lines(lines)

def bind_global_keys():
    keys.bind('g', ':SpliceGrid<cr>')
    keys.bind('l', ':SpliceLoupe<cr>')
    keys.bind('c', ':SpliceCompare<cr>')
    keys.bind('p', ':SplicePath<cr>')

    keys.bind('o', ':SpliceOriginal<cr>')
    keys.bind('1', ':SpliceOne<cr>')
    keys.bind('2', ':SpliceTwo<cr>')
    keys.bind('r', ':SpliceResult<cr>')

    keys.bind('d', ':SpliceDiff<cr>')
    keys.bind('D', ':SpliceDiffoff<cr>')
    keys.bind('s', ':SpliceScroll<cr>')
    keys.bind('n', ':SpliceNext<cr>')
    keys.bind('N', ':SplicePrev<cr>')
    keys.bind('<space>', ':SpliceLayout<cr>')
    keys.bind('u', ':SpliceUse<cr>')

    keys.bind('q', ':wa<cr>:qa<cr>')
    keys.bind('CC', ':cq<cr>')

def setlocal_buffers():
    buffers.result.open()
    filetype = vim.eval('&filetype')

    buffers.original.open()
    vim.command('setlocal noswapfile')
    vim.command('setlocal nomodifiable')
    vim.command('set filetype=%s' % filetype)
    if setting('wrap'):
        vim.command('setlocal ' + setting('wrap'))

    buffers.one.open()
    vim.command('setlocal noswapfile')
    vim.command('setlocal nomodifiable')
    vim.command('set filetype=%s' % filetype)
    if setting('wrap'):
        vim.command('setlocal ' + setting('wrap'))

    buffers.two.open()
    vim.command('setlocal noswapfile')
    vim.command('setlocal nomodifiable')
    vim.command('set filetype=%s' % filetype)
    if setting('wrap'):
        vim.command('setlocal ' + setting('wrap'))

    buffers.result.open()
    vim.command('set filetype=%s' % filetype)
    if setting('wrap'):
        vim.command('setlocal ' + setting('wrap'))

    buffers.hud.open()
    vim.command('setlocal noswapfile')
    vim.command('setlocal nomodifiable')
    vim.command('setlocal nobuflisted')
    vim.command('setlocal buftype=nofile')
    vim.command('setlocal noundofile')
    vim.command('setlocal nolist')
    vim.command('setlocal ft=splice')
    vim.command('setlocal nowrap')
    vim.command('resize ' + setting('hud_size', '3'))

def create_hud():
    vim.command('new __Splice_HUD__')


def init():
    process_result()
    create_hud()
    setlocal_buffers()
    bind_global_keys()

    vim.command('set hidden')

    initial_mode = setting('initial_mode', 'grid').lower()
    if initial_mode not in ['grid', 'loupe', 'compare', 'path']:
        initial_mode = 'grid'

    modes.current_mode = getattr(modes, initial_mode)
    modes.current_mode.activate()



########NEW FILE########
__FILENAME__ = modes
from __future__ import with_statement

import vim
from util import buffers, keys, windows
from settings import boolsetting, setting


current_mode = None

class Mode(object):
    def __init__(self):
        return super(Mode, self).__init__()


    def diff(self, diffmode):
        with buffers.remain():
            with windows.remain():
                getattr(self, '_diff_%d' % diffmode)()

        # Reset the scrollbind to whatever it was before we diffed.
        if not diffmode:
            self.scrollbind(self._current_scrollbind)

    def key_diff(self, diffmode=None):
        next_diff_mode = self._current_diff_mode + 1
        if next_diff_mode >= self._number_of_diff_modes:
            next_diff_mode = 0
        self.diff(next_diff_mode)


    def diffoff(self):
        with windows.remain():
            for winnr in range(2, 2 + self._number_of_windows):
                windows.focus(winnr)
                curbuffer = buffers.current

                for buffer in buffers.all:
                    buffer.open()
                    vim.command('diffoff')
                    if setting('wrap'):
                        vim.command('setlocal ' + setting('wrap'))

                curbuffer.open()


    def key_diffoff(self):
        self.diff(0)


    def scrollbind(self, enabled):
        if self._current_diff_mode:
            return

        with windows.remain():
            self._current_scrollbind = enabled

            for winnr in range(2, 2 + self._number_of_windows):
                windows.focus(winnr)

                if enabled:
                    vim.command('set scrollbind')
                else:
                    vim.command('set noscrollbind')

            if enabled:
                vim.command('syncbind')

    def key_scrollbind(self):
        self.scrollbind(not self._current_scrollbind)


    def layout(self, layoutnr):
        getattr(self, '_layout_%d' % layoutnr)()
        self.diff(self._current_diff_mode)
        self.redraw_hud()

    def key_layout(self, diffmode=None):
        next_layout = self._current_layout + 1
        if next_layout >= self._number_of_layouts:
            next_layout = 0
        self.layout(next_layout)


    def key_original(self):
        pass

    def key_one(self):
        pass

    def key_two(self):
        pass

    def key_result(self):
        pass


    def key_use(self):
        pass


    def activate(self):
        self.layout(self._current_layout)
        self.diff(self._current_diff_mode)
        self.scrollbind(self._current_scrollbind)

    def deactivate(self):
        pass


    def key_next(self):
        self.goto_result()
        vim.command(r'exe "silent! normal! /\\v^\\=\\=\\=\\=\\=\\=\\=*$\<cr>"')

    def key_prev(self):
        self.goto_result()
        vim.command(r'exe "silent! normal! ?\\v^\\=\\=\\=\\=\\=\\=\\=*$\<cr>"')


    def open_hud(self, winnr):
        windows.split()
        windows.focus(winnr)
        buffers.hud.open()
        vim.command('wincmd K')
        self.redraw_hud()

    def hud_lines(self):
        def pad(lines):
            l = max([len(line) for line in lines])
            return [line.ljust(l) for line in lines]

        sep = '    |    '

        modes = pad([
            r'Splice Modes',
            r'x[g]rid   y[c]ompare'.replace('x', self._id == 'grid' and '*' or ' ')
                                   .replace('y', self._id == 'comp' and '*' or ' '),
            r'x[l]oupe  y[p]ath'.replace('x', self._id == 'loup' and '*' or ' ')
                                .replace('y', self._id == 'path' and '*' or ' '),
        ])
        diagram = pad(self.hud_diagram())
        commands = pad([
            r'Splice Commands',
            r'd: cycle diffs   n: next conflict   space: cycle layouts   u: use hunk   o: original   1: one   q: save and quit',
            r'D: diffs off     N: prev conflict   s: toggle scrollbind                 r: result     2: two   CC: exit with error',
        ])

        lines = []
        for line in modes:
            lines.append(line + sep)
        for i, line in enumerate(diagram):
            lines[i] += line + sep
        for i, line in enumerate(commands):
            lines[i] += line + sep

        for i, line in enumerate(lines):
            lines[i] = line.rstrip()

        return lines

    def redraw_hud(self):
        with windows.remain():
            windows.focus(1)

            vim.command('setlocal modifiable')
            buffers.hud.set_lines(self.hud_lines())
            vim.command('setlocal nomodifiable')

            vim.command('set winfixheight')
            vim.command('resize ' + setting('hud_size', '3'))
            vim.command('wincmd =')


class GridMode(Mode):
    """
    Layout 0                 Layout 1                        Layout 2
    +-------------------+    +--------------------------+    +---------------+
    |     Original      |    | One    | Result | Two    |    |      One      |
    |2                  |    |        |        |        |    |2              |
    +-------------------+    |        |        |        |    +---------------+
    |  One    |    Two  |    |        |        |        |    |     Result    |
    |3        |4        |    |        |        |        |    |3              |
    +-------------------+    |        |        |        |    +---------------+
    |      Result       |    |        |        |        |    |      Two      |
    |5                  |    |2       |3       |4       |    |4              |
    +-------------------+    +--------------------------+    +---------------+
    """

    def __init__(self):
        self._id = 'grid'
        self._current_layout = int(setting('initial_layout_grid', 0))
        self._current_diff_mode = int(setting('initial_diff_grid', 0))
        self._current_scrollbind = boolsetting('initial_scrollbind_grid')

        self._number_of_diff_modes = 2
        self._number_of_layouts = 3

        return super(GridMode, self).__init__()


    def _layout_0(self):
        self._number_of_windows = 4
        self._current_layout = 0

        # Open the layout
        windows.close_all()
        windows.split()
        windows.split()
        windows.focus(2)
        windows.vsplit()

        # Put the buffers in the appropriate windows
        windows.focus(1)
        buffers.original.open()

        windows.focus(2)
        buffers.one.open()

        windows.focus(3)
        buffers.two.open()

        windows.focus(4)
        buffers.result.open()

        self.open_hud(5)

        windows.focus(5)

    def _layout_1(self):
        self._number_of_windows = 3
        self._current_layout = 1

        # Open the layout
        windows.close_all()
        windows.vsplit()
        windows.vsplit()

        # Put the buffers in the appropriate windows
        windows.focus(1)
        buffers.one.open()

        windows.focus(2)
        buffers.result.open()

        windows.focus(3)
        buffers.two.open()

        self.open_hud(4)

        windows.focus(3)

    def _layout_2(self):
        self._number_of_windows = 4
        self._current_layout = 2

        # Open the layout
        windows.close_all()
        windows.split()
        windows.split()

        # Put the buffers in the appropriate windows
        windows.focus(1)
        buffers.one.open()

        windows.focus(2)
        buffers.result.open()

        windows.focus(3)
        buffers.two.open()

        self.open_hud(4)

        windows.focus(3)


    def _diff_0(self):
        self.diffoff()
        self._current_diff_mode = 0

    def _diff_1(self):
        self.diffoff()
        self._current_diff_mode = 1

        for i in range(2, self._number_of_windows + 2):
            windows.focus(i)
            vim.command('diffthis')


    def key_original(self):
        if self._current_layout == 0:
            windows.focus(2)
        elif self._current_layout == 1:
            return
        elif self._current_layout == 2:
            return

    def key_one(self):
        if self._current_layout == 0:
            windows.focus(3)
        elif self._current_layout == 1:
            windows.focus(2)
        elif self._current_layout == 2:
            windows.focus(2)

    def key_two(self):
        if self._current_layout == 0:
            windows.focus(4)
        elif self._current_layout == 1:
            windows.focus(4)
        elif self._current_layout == 2:
            windows.focus(4)

    def key_result(self):
        if self._current_layout == 0:
            windows.focus(5)
        elif self._current_layout == 1:
            windows.focus(3)
        elif self._current_layout == 2:
            windows.focus(3)


    def _key_use_0(self, target):
        targetwin = 3 if target == 1 else 4

        with windows.remain():
            self.diffoff()

            windows.focus(5)
            vim.command('diffthis')

            windows.focus(targetwin)
            vim.command('diffthis')

    def _key_use_12(self, target):
        targetwin = 2 if target == 1 else 4

        with windows.remain():
            self.diffoff()

            windows.focus(3)
            vim.command('diffthis')

            windows.focus(targetwin)
            vim.command('diffthis')


    def key_use1(self):
        current_diff = self._current_diff_mode

        if self._current_layout == 0:
            self._key_use_0(1)
        elif self._current_layout == 1:
            self._key_use_12(1)
        elif self._current_layout == 2:
            self._key_use_12(1)

        if buffers.current == buffers.result:
            vim.command('diffget')
        elif buffers.current in (buffers.one, buffers.two):
            vim.command('diffput')

        self.diff(current_diff)

    def key_use2(self):
        current_diff = self._current_diff_mode

        if self._current_layout == 0:
            self._key_use_0(2)
        elif self._current_layout == 1:
            self._key_use_12(2)
        elif self._current_layout == 2:
            self._key_use_12(2)

        if buffers.current == buffers.result:
            vim.command('diffget')
        elif buffers.current in (buffers.one, buffers.two):
            vim.command('diffput')

        self.diff(current_diff)


    def goto_result(self):
        if self._current_layout == 0:
            windows.focus(5)
        elif self._current_layout == 1:
            windows.focus(3)
        elif self._current_layout == 2:
            windows.focus(3)


    def activate(self):
        keys.unbind('u')
        keys.bind('u1', ':SpliceUse1<cr>')
        keys.bind('u2', ':SpliceUse2<cr>')
        return super(GridMode, self).activate()

    def deactivate(self):
        keys.unbind('u1')
        keys.unbind('u2')
        keys.bind('u', ':SpliceUse<cr>')
        return super(GridMode, self).deactivate()


    def hud_diagram(self):
        if self._current_layout == 0:
            return [
                r'           Original',
                r'Layout ->  One  Two',
                r'            Result',
            ]
        elif self._current_layout == 1:
            return [
                r'',
                r'Layout ->  One  Result  Two',
                r'',
            ]
        elif self._current_layout == 2:
            return [
                r'           One',
                r'Layout ->  Result',
                r'           Two',
            ]

class LoupeMode(Mode):
    def __init__(self):
        self._id = 'loup'
        self._current_layout = int(setting('initial_layout_loupe', 0))
        self._current_diff_mode = int(setting('initial_diff_loupe', 0))
        self._current_scrollbind = boolsetting('initial_scrollbind_loupe')

        self._number_of_diff_modes = 1
        self._number_of_layouts = 1

        self._current_buffer = buffers.result

        return super(LoupeMode, self).__init__()


    def _diff_0(self):
        self.diffoff()
        self._current_diff_mode = 0


    def _layout_0(self):
        self._number_of_windows = 1
        self._current_layout = 0

        # Open the layout
        windows.close_all()

        # Put the buffers in the appropriate windows
        windows.focus(1)
        self._current_buffer.open()

        self.open_hud(2)

        windows.focus(2)


    def key_original(self):
        windows.focus(2)
        buffers.original.open()
        self._current_buffer = buffers.original
        self.redraw_hud()

    def key_one(self):
        windows.focus(2)
        buffers.one.open()
        self._current_buffer = buffers.one
        self.redraw_hud()

    def key_two(self):
        windows.focus(2)
        buffers.two.open()
        self._current_buffer = buffers.two
        self.redraw_hud()

    def key_result(self):
        windows.focus(2)
        buffers.result.open()
        self._current_buffer = buffers.result
        self.redraw_hud()


    def key_use(self):
        pass


    def goto_result(self):
        self.key_result()


    def hud_diagram(self):
        buf = buffers.labels[self._current_buffer.name]

        if self._current_layout == 0:
            return [
                r'',
                r'Layout ->  %s ' % (buf,),
                r'',
            ]

class CompareMode(Mode):
    def __init__(self):
        self._id = 'comp'
        self._current_layout = int(setting('initial_layout_compare', 0))
        self._current_diff_mode = int(setting('initial_diff_compare', 0))
        self._current_scrollbind = boolsetting('initial_scrollbind_compare')

        self._number_of_diff_modes = 2
        self._number_of_layouts = 2

        self._current_buffer_first = buffers.original
        self._current_buffer_second = buffers.result

        return super(CompareMode, self).__init__()


    def _diff_0(self):
        self.diffoff()
        self._current_diff_mode = 0

    def _diff_1(self):
        self.diffoff()
        self._current_diff_mode = 1

        windows.focus(2)
        vim.command('diffthis')

        windows.focus(3)
        vim.command('diffthis')


    def _layout_0(self):
        self._number_of_windows = 2
        self._current_layout = 0

        # Open the layout
        windows.close_all()
        windows.vsplit()

        # Put the buffers in the appropriate windows
        windows.focus(1)
        self._current_buffer_first.open()

        windows.focus(2)
        self._current_buffer_second.open()

        self.open_hud(3)

        windows.focus(3)

    def _layout_1(self):
        self._number_of_windows = 2
        self._current_layout = 1

        # Open the layout
        windows.close_all()
        windows.split()

        # Put the buffers in the appropriate windows
        windows.focus(1)
        self._current_buffer_first.open()

        windows.focus(2)
        self._current_buffer_second.open()

        self.open_hud(3)

        windows.focus(3)


    def key_original(self):
        windows.focus(2)
        buffers.original.open()
        self._current_buffer_first = buffers.original
        self.diff(self._current_diff_mode)

        self.redraw_hud()

    def key_one(self):
        def open_one(winnr):
            buffers.one.open(winnr)
            if winnr == 2:
                self._current_buffer_first = buffers.one
            else:
                self._current_buffer_second = buffers.one
            self.diff(self._current_diff_mode)
            self.redraw_hud()

        curwindow = windows.currentnr()
        if curwindow == 1:
            curwindow = 2

        # If file one is showing, go to it.
        windows.focus(2)
        if buffers.current == buffers.one:
            return

        windows.focus(3)
        if buffers.current == buffers.one:
            return

        # If both the original and result are showing, open file one in the
        # current window.
        windows.focus(2)
        if buffers.current == buffers.original:
            windows.focus(3)
            if buffers.current == buffers.result:
                open_one(curwindow)
                return

        # If file two is in window 1, then we open file one in window 1.
        windows.focus(2)
        if buffers.current == buffers.two:
            open_one(2)
            return

        # Otherwise, open file one in the current window.
        open_one(curwindow)

    def key_two(self):
        def open_two(winnr):
            buffers.two.open(winnr)
            if winnr == 2:
                self._current_buffer_first = buffers.two
            else:
                self._current_buffer_second = buffers.two
            self.diff(self._current_diff_mode)
            self.redraw_hud()

        curwindow = windows.currentnr()
        if curwindow == 1:
            curwindow = 2

        # If file two is showing, go to it.
        windows.focus(2)
        if buffers.current == buffers.two:
            return

        windows.focus(3)
        if buffers.current == buffers.two:
            return

        # If both the original and result are showing, open file two in the
        # current window.
        windows.focus(2)
        if buffers.current == buffers.original:
            windows.focus(3)
            if buffers.current == buffers.result:
                open_two(curwindow)
                return

        # If file one and the result are showing, then we open file two in the
        # current window.
        windows.focus(2)
        if buffers.current == buffers.one:
            windows.focus(3)
            if buffers.current == buffers.result:
                open_two(curwindow)
                return

        # If file one is in window 2, then we open file two in window 2.
        windows.focus(3)
        if buffers.current == buffers.two:
            open_two(3)
            return

        # Otherwise, open file two in window 2.
        open_two(3)

    def key_result(self):
        windows.focus(3)
        buffers.result.open()
        self._current_buffer_second = buffers.result
        self.diff(self._current_diff_mode)

        self.redraw_hud()


    def key_use(self):
        active = (self._current_buffer_first, self._current_buffer_second)

        if buffers.result not in active:
            return

        if buffers.one not in active and buffers.two not in active:
            return

        current_diff = self._current_diff_mode
        with windows.remain():
            self._diff_1()  # diff the windows

        if buffers.current == buffers.result:
            vim.command('diffget')
        elif buffers.current in (buffers.one, buffers.two):
            vim.command('diffput')

        self.diff(current_diff)


    def goto_result(self):
        self.key_result()


    def hud_diagram(self):
        first = buffers.labels[self._current_buffer_first.name]
        second = buffers.labels[self._current_buffer_second.name]

        if self._current_layout == 0:
            return [
                r'',
                r'Layout ->  %s %s' % (first, second),
                r'',
            ]
        elif self._current_layout == 1:
            return [
                r'',
                r'Layout ->  %s' % first,
                r'           %s' % second,
            ]

class PathMode(Mode):
    def __init__(self):
        self._id = 'path'
        self._current_layout = int(setting('initial_layout_path', 0))
        self._current_diff_mode = int(setting('initial_diff_path', 0))
        self._current_scrollbind = boolsetting('initial_scrollbind_path')

        self._number_of_diff_modes = 5
        self._number_of_layouts = 2

        self._current_mid_buffer = buffers.one

        return super(PathMode, self).__init__()


    def _diff_0(self):
        self.diffoff()
        self._current_diff_mode = 0

    def _diff_1(self):
        self.diffoff()
        self._current_diff_mode = 1

        windows.focus(2)
        vim.command('diffthis')

        windows.focus(4)
        vim.command('diffthis')

    def _diff_2(self):
        self.diffoff()
        self._current_diff_mode = 2

        windows.focus(2)
        vim.command('diffthis')

        windows.focus(3)
        vim.command('diffthis')

    def _diff_3(self):
        self.diffoff()
        self._current_diff_mode = 3

        windows.focus(3)
        vim.command('diffthis')

        windows.focus(4)
        vim.command('diffthis')

    def _diff_4(self):
        self.diffoff()
        self._current_diff_mode = 4

        windows.focus(2)
        vim.command('diffthis')

        windows.focus(3)
        vim.command('diffthis')

        windows.focus(4)
        vim.command('diffthis')


    def _layout_0(self):
        self._number_of_windows = 3
        self._current_layout = 0

        # Open the layout
        windows.close_all()
        windows.vsplit()
        windows.vsplit()

        # Put the buffers in the appropriate windows
        windows.focus(1)
        buffers.original.open()

        windows.focus(2)
        self._current_mid_buffer.open()

        windows.focus(3)
        buffers.result.open()

        self.open_hud(4)

        windows.focus(4)

    def _layout_1(self):
        self._number_of_windows = 3
        self._current_layout = 1

        # Open the layout
        windows.close_all()
        windows.split()
        windows.split()

        # Put the buffers in the appropriate windows
        windows.focus(1)
        buffers.original.open()

        windows.focus(2)
        self._current_mid_buffer.open()

        windows.focus(3)
        buffers.result.open()

        self.open_hud(4)

        windows.focus(4)


    def key_original(self):
        windows.focus(2)

    def key_one(self):
        windows.focus(3)
        buffers.one.open()
        self._current_mid_buffer = buffers.one
        self.diff(self._current_diff_mode)
        windows.focus(3)
        self.redraw_hud()

    def key_two(self):
        windows.focus(3)
        buffers.two.open()
        self._current_mid_buffer = buffers.two
        self.diff(self._current_diff_mode)
        windows.focus(3)
        self.redraw_hud()

    def key_result(self):
        windows.focus(4)


    def key_use(self):
        current_diff = self._current_diff_mode
        with windows.remain():
            self._diff_3()  # diff the middle and result windows

        if buffers.current == buffers.result:
            vim.command('diffget')
        elif buffers.current in (buffers.one, buffers.two):
            vim.command('diffput')

        self.diff(current_diff)


    def goto_result(self):
        windows.focus(4)


    def hud_diagram(self):
        if self._current_mid_buffer == buffers.one:
            buf = 'One'
        else:
            buf = 'Two'

        if self._current_layout == 0:
            return [
                r'',
                r'Layout ->  Original  %s  Result' % buf,
                r'',
            ]
        elif self._current_layout == 1:
            return [
                r'           Original',
                r'Layout ->  %s' % buf,
                r'           Result',
            ]


grid = GridMode()
loupe = LoupeMode()
compare = CompareMode()
path = PathMode()


def key_grid():
    global current_mode
    current_mode.deactivate()
    current_mode = grid
    grid.activate()

def key_loupe():
    global current_mode
    current_mode.deactivate()
    current_mode = loupe
    loupe.activate()

def key_compare():
    global current_mode
    current_mode.deactivate()
    current_mode = compare
    compare.activate()

def key_path():
    global current_mode
    current_mode.deactivate()
    current_mode = path
    path.activate()

########NEW FILE########
__FILENAME__ = settings
import vim


def setting(name, default=None):
    full_name = 'g:splice_' + name

    if not int(vim.eval('exists("%s")' % full_name)):
        return default
    else:
        return vim.eval(full_name)

def boolsetting(name):
    if int(setting(name, 0)):
        return True
    else:
        False

########NEW FILE########
__FILENAME__ = bufferlib
import os
import vim
import windows

ap = os.path.abspath

class Buffer(object):
    def __init__(self, i):
        self.number = i
        for b in vim.buffers:
            if b.number == self.number:
                self._buffer = b
                break
        self.name = self._buffer.name

    def open(self, winnr=None):
        if winnr is not None:
            windows.focus(winnr)
        vim.command('%dbuffer' % self.number)

    def set_lines(self, lines):
        self._buffer[:] = lines

    @property
    def lines(self):
        for line in self._buffer:
            yield line


    def __eq__(self, other):
        return self.name == other.name

    def __ne__(self, other):
        return self.name != other.name


class _BufferList(object):
    @property
    def original(self):
        return Buffer(1)

    @property
    def one(self):
        return Buffer(2)

    @property
    def two(self):
        return Buffer(3)

    @property
    def result(self):
        return Buffer(4)

    @property
    def hud(self):
        return Buffer(int(vim.eval("bufnr('__Splice_HUD__')")))


    @property
    def current(self):
        bufname = ap(vim.eval('bufname("%")'))

        if bufname == ap(self.original.name):
            return self.original
        elif bufname == ap(self.one.name):
            return self.one
        elif bufname == ap(self.two.name):
            return self.two
        elif bufname == ap(self.result.name):
            return self.result

    @property
    def all(self):
        return [self.original, self.one, self.two, self.result]


    @property
    def labels(self):
        return { buffers.original.name: 'Original',
                 buffers.one.name: 'One',
                 buffers.two.name: 'Two',
                 buffers.result.name: 'Result' }

    class remain:
        def __enter__(self):
            self.curbuf = int(vim.eval('bufnr(bufname("%"))'))
            self.pos = windows.pos()

        def __exit__(self, type, value, traceback):
            vim.command('%dbuffer' % self.curbuf)
            vim.current.window.cursor = self.pos

buffers = _BufferList()


########NEW FILE########
__FILENAME__ = io
import sys
import vim


def error(m):
    sys.stderr.write(str(m) + '\n')

def echomsg(m):
    vim.command('echomsg "%s"' % m)

########NEW FILE########
__FILENAME__ = keys
from __future__ import with_statement
import vim
from bufferlib import buffers
from ..settings import setting


def bind(key, to, options='', mode=None, leader=None):
    if not leader:
        leader = setting('prefix', '-')

    vim.command('nnoremap %s %s%s %s' % (options, leader, key, to))

def unbind(key, options='', leader=None):
    if not leader:
        leader = setting('prefix', '-')

    vim.command('unmap %s %s%s' % (options, leader, key))

def bind_for_all(key, to, options='', mode=None, leader=None):
    if not leader:
        leader = setting('prefix', '-')

    with buffers.remain():
        for b in buffers.all:
            b.open()
            bind(key, to, options, mode, leader)

def unbind_for_all(key, options='', leader=None):
    if not leader:
        leader = setting('prefix', '-')

    with buffers.remain():
        for b in buffers.all:
            b.open()
            unbind(key, options, leader)

########NEW FILE########
__FILENAME__ = windows
import vim


def focus(winnr):
    vim.command('%dwincmd w' % winnr)

def close_all():
    focus(1)
    vim.command('wincmd o')

def split():
    vim.command('wincmd s')

def vsplit():
    vim.command('wincmd v')

def currentnr():
    return int(vim.eval('winnr()'))

def pos():
    return vim.current.window.cursor


class remain:
    def __enter__(self):
        self.curwindow = currentnr()
        self.pos = pos()

    def __exit__(self, type, value, traceback):
        focus(self.curwindow)
        vim.current.window.cursor = self.pos


########NEW FILE########
__FILENAME__ = render
#!/usr/bin/env python

import os
import markdown

extensions = ['toc']
fns = [f for f in os.listdir('.') if f.endswith('.markdown')
                                  or f.endswith('.mdown')
                                  or f.endswith('.md')]

with open('layout.html') as layoutfile:
    layoutlines = layoutfile.readlines()

for fn in fns:
    name = fn.rsplit('.')[0]
    newfn = name + '.html'

    with open(fn) as mdfile:
        title = mdfile.readline().strip()
        content = markdown.markdown(mdfile.read(), extensions)

    with open(newfn, 'w') as newfile:
        for line in layoutlines:
            line = line.replace('{{ title }}', title)
            line = line.replace('{{ content }}', content)
            newfile.write(line)


########NEW FILE########
