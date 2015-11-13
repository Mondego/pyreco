__FILENAME__ = core
# -*- coding: utf-8 -*-
"""
breeze.core
~~~~~~~~~~~

This module defines Breeze class.
"""

import os
import vim

from breeze import parser
from breeze import jumper
from breeze.utils import v
from breeze.utils import misc
from breeze.utils import settings


class Breeze:

    def __init__(self):
        self.parser = parser.Parser()
        self.jumper = jumper.Jumper(self)
        self.setup_colors()
        # caching stuff
        self.refresh_cache = True
        self.cache = None

    def parse_current_buffer(f):
        """To provide some naive form of caching.

        This decorator ensures that the wrapped method will have access to
        a fully parsed DOM tree structure for the current buffer.
        """
        def wrapper(self, *args, **kwargs):
            if self.refresh_cache or vim.eval("&mod") == '1':
                self.parser.feed(v.buf())
                if self.parser.success:
                    self.cache = self.parser.tree
                    self.refresh_cache = False
                else:
                    v.clear_hl('BreezeJumpMark', 'BreezeShade')
                    self.refresh_cache = True
                    return
            else:
                self.parser.tree = self.cache
            return f(self, *args, **kwargs)
        return wrapper

    def remember_curr_pos(f):
        """To add the current cursor position to the jump list so that the user
        can come back with CTRL+O.
        """
        def wrapper(self, *args, **kwargs):
            vim.command("normal! m'")
            return f(self, *args, **kwargs)
        return wrapper

    def setup_colors(self):
        """To setup Breeze highlight groups."""
        postfix = "" if vim.eval("&bg") == "light" else "_darkbg"
        colors = {
            "BreezeShade": settings.get("shade_color{0}".format(postfix)),
            "BreezeJumpMark": settings.get("jumpmark_color{0}".format(postfix)),
            "BreezeHl": settings.get("hl_color{0}".format(postfix))
        }
        for group, color in colors.items():
            link = "" if "=" in color else "link"
            vim.command("hi {0} {1} {2}".format(link, group, color))

    @remember_curr_pos
    @parse_current_buffer
    def jump_forward(self):
        """Jump forward! Displays jump marks, asks for the destination and
        jumps to the selected tag."""
        self.jumper.jump(backward=False)

    @remember_curr_pos
    @parse_current_buffer
    def jump_backward(self):
        """Jump backward! Displays jump marks, asks for the destination and
        jumps to the selected tag."""
        self.jumper.jump(backward=True)

    @parse_current_buffer
    def highlight_curr_element(self):
        """Highlights opening and closing tags of the current element."""
        v.clear_hl('BreezeHl')

        node = self.parser.get_current_node()
        if not node:
            return

        line, scol = node.start[0], node.start[1]+1
        ecol = scol + len(node.tag) + 1
        patt = "\\%{0}l\\%>{1}c\%<{2}c".format(line, scol, ecol)
        v.highlight("BreezeHl", patt)

        if node.tag not in misc.empty_tags:
            line, scol = node.end[0], node.end[1]+1
            ecol = scol + len(node.tag) + 2
            patt = "\\%{0}l\\%>{1}c\%<{2}c".format(line, scol, ecol)
            v.highlight("BreezeHl", patt)

    @remember_curr_pos
    @parse_current_buffer
    def match_tag(self):
        """Matches the current tag.

        If the cursor is on the first line of the tag the cursor is positioned
        at the closing tag, and vice-versa.  If the cursor isn't on the start
        line of the tag, the cursor is positioned at the opening tag.
        """
        node = self.parser.get_current_node()
        if node:
            row, col = v.cursor()
            if row != node.start[0]:
                target = node.start
            else:
                endcol = node.start[1] + len(node.starttag_text)
                if col < endcol:
                    target = node.end
                else:
                    target = node.start

            row, col = target
            if not settings.get("jump_to_angle_bracket", bool):
                col += 1
            v.cursor((row, col))

    @remember_curr_pos
    @parse_current_buffer
    def goto_next_sibling(self):
        """To move the cursor to the next sibling node."""
        node = self.parser.get_current_node()
        if node and node.parent:
            ch = node.parent.children
            for i, c in enumerate(ch):
                if c.start == node.start and c.end == node.end and i + 1 < len(ch):
                    row, col = ch[i+1].start
                    if not settings.get("jump_to_angle_bracket", bool):
                        col += 1
                    v.cursor((row, col))

    @remember_curr_pos
    @parse_current_buffer
    def goto_prev_sibling(self):
        """To move the cursor to the previous sibling node."""
        node = self.parser.get_current_node()
        if node and node.parent:
            ch = node.parent.children
            for i, c in enumerate(ch):
                if c.start == node.start and c.end == node.end and i - 1 >= 0:
                    row, col = ch[i-1].start
                    if not settings.get("jump_to_angle_bracket", bool):
                        col += 1
                    v.cursor((row, col))

    @remember_curr_pos
    @parse_current_buffer
    def goto_first_sibling(self):
        """To move the cursor to the first sibling node."""
        node = self.parser.get_current_node()
        if node and node.parent:
            row, col = node.parent.children[0].start
            if not settings.get("jump_to_angle_bracket", bool):
                col += 1
            v.cursor((row, col))

    @remember_curr_pos
    @parse_current_buffer
    def goto_last_sibling(self):
        """To move the cursor to the last sibling node."""
        node = self.parser.get_current_node()
        if node and node.parent:
            row, col = node.parent.children[-1].start
            if not settings.get("jump_to_angle_bracket", bool):
                col += 1
            v.cursor((row, col))

    @remember_curr_pos
    @parse_current_buffer
    def goto_first_child(self):
        """To move the cursor to the first child of the current node."""
        node = self.parser.get_current_node()
        if node and node.children:
            row, col = node.children[0].start
            if not settings.get("jump_to_angle_bracket", bool):
                col += 1
            v.cursor((row, col))

    @remember_curr_pos
    @parse_current_buffer
    def goto_last_child(self):
        """To move the cursor to the last child of the current node."""
        node = self.parser.get_current_node()
        if node and node.children:
            row, col = node.children[-1].start
            if not settings.get("jump_to_angle_bracket", bool):
                col += 1
            v.cursor((row, col))

    @remember_curr_pos
    @parse_current_buffer
    def goto_parent(self):
        """To move the cursor to the parent of the current node."""
        node = self.parser.get_current_node()
        if node:
            if node.parent.tag != "root":
                row, col = node.parent.start
                if not settings.get("jump_to_angle_bracket", bool):
                    col += 1
                v.cursor((row, col))
            else:
                v.echom("no parent found")

    @parse_current_buffer
    def print_dom(self):
        """To print the DOM tree."""
        self.parser.print_dom_tree()

    def whats_wrong(self):
        """To tell the user about the last encountered problem."""
        v.echom(self.parser.get_error())

########NEW FILE########
__FILENAME__ = jumper
# -*- coding: utf-8 -*-
"""
breeze.jumper
~~~~~~~~~~~~~

This module defines the Jumper class. The Jumper is responsible for the jumping
functionality:

    1. display jump marks on the current buffer
    2. ask the user for the destination mark
    3. jump to the selected mark

The only method that should be called from the outside and that provide
the above functionality is the "jump" method.
"""

import vim
import string

from breeze.utils import v
from breeze.utils import input
from breeze.utils import settings


class Jumper(object):

    def __init__(self, plug):
        self.plug = plug

    def jump(self, backward=False):
        """To display jump marks and move to the selected jump mark."""
        table = self._show_jump_marks(v.cursor(), backward)
        choice = None
        while choice not in table:
            choice = self._ask_target_key()
            if choice is None:
                break

        v.clear_hl('BreezeJumpMark', 'BreezeShade')
        self._clear_jump_marks(table)

        if choice:
            row, col = table[choice][0]
            if not settings.get("jump_to_angle_bracket", bool):
                col += 1
            v.cursor((row, col))

    def _show_jump_marks(self, curr_pos, backward=False):
        """To display jump marks."""
        top, bot = v.window_bundaries()
        v.highlight("BreezeShade", "\\%>{0}l\\%<{1}l".format(top-1, bot+1))

        table = {}
        jump_marks = list(string.letters)
        vim.command("setl modifiable noreadonly")
        vim.command("try|undojoin|catch|endtry")

        nodes = filter(lambda n: top <= n.start[0] <= bot, self.plug.parser.all_nodes())
        nodes = reversed(nodes) if backward else nodes

        for node in nodes:

            if not jump_marks:
                break

            # both trow and tcol are 1-indexed
            trow, tcol = node.start[0], node.start[1]
            crow, ccol = curr_pos[0], curr_pos[1]-1

            if backward:
                if not (trow < crow or (trow == crow and tcol < ccol)):
                    continue
            else:
                if not (trow > crow or (trow == crow and tcol > ccol)):
                    continue

            old = v.subst_char(v.buf(), jump_marks[0], trow-1, tcol+1)
            self._highlight_jump_mark((trow, tcol+2))
            table[jump_marks.pop(0)] = (node.start, old)

        vim.command("setl nomodified")
        v.redraw()

        return table

    def _highlight_jump_mark(self, pos, special=False):
        """To highligt the jump mark at the given position."""
        v.highlight("BreezeJumpMark", "\\%{0}l\\%{1}c".format(*pos))

    def _ask_target_key(self):
        """To ask the user where to jump."""
        key = input.Input()
        while True:
            v.redraw()
            vim.command('echohl Question|echo " target: "|echohl None')
            key.get()
            if key.ESC or key.INTERRUPT:
                return
            elif key.CHAR:
                return key.CHAR

    def _clear_jump_marks(self, table):
        """To clear jump marks."""
        vim.command("try|undojoin|catch|endtry")
        # restore characters
        for mark, tpl in table.items():
            pos, old = tpl
            row, col = pos[0]-1, pos[1]+1
            v.subst_char(v.buf(), old, row, col)

        vim.command("setl nomodified")
        v.redraw()

########NEW FILE########
__FILENAME__ = parser
# -*- coding: utf-8 -*-
"""
breeze.parser
~~~~~~~~~~~~~

This module defines the Parser and Node classes. The Parser is responsible for
parsing the current buffer and generating a DOM tree, whereas the Node class is
needed to represent a single HTML node.
"""

import vim
import itertools

from breeze.utils import v
from breeze.utils import misc

try:
    # python 3
    import html.parser as HTMLParser
except ImportError:
    import HTMLParser as HTMLParser


class Node:

    def __init__(self, tag="", starttag_text="", parent=None, start=None, end=None):
        self.tag = tag  # tag name
        self.starttag_text = starttag_text  # raw starttag text
        self.start = start  # a tuple (row, col)
        self.end = end  # a tuple (row, col)
        self.parent = parent  # a Node or None (if root)
        self.children = []  # a list of Nodes

    def __str__(self):
        return "<{0} start={1} end={2}>".format(self.tag, self.start, self.end)

    def __repr__(self):
        return "<{0} start={1} end={2}>".format(self.tag, self.start, self.end)


class Parser(HTMLParser.HTMLParser):

    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.last_known_error = None
        self.success = False
        self.tree = Node(tag="root")
        self.stack = [self.tree]

    def feed(self, buffer):
        """To generate a brand new tree at each call."""
        self.tree = Node(tag="root")
        self.stack = [self.tree]
        try:
            HTMLParser.HTMLParser.feed(self, "\n".join(buffer))
            self.success = True
            self.last_known_error = None
        except HTMLParser.HTMLParseError as e:
            self.last_known_error = dict(msg=e.msg, pos=(e.lineno, e.offset))
            self.tree = Node(tag="root")
            self.success = False
        finally:
            self.reset()

    def handle_startendtag(self, tag, attrs):
        """To handle empty tags."""
        self.handle_starttag(tag, attrs, skip_emptytag_check=True)
        self.handle_endtag(tag)

    def handle_starttag(self, tag, attrs, skip_emptytag_check=False):
        """To handle the start of a tag.

        Note how this method handles empty tags. The HTMLParser does not
        recognize self-closing tags if they aren't closed with '../>',
        although this is totally acceptable in non-XHTML documents. So we call
        the handle_startendtag tags by ourselves and we make sure we don't run
        infinite recursive calls with the skip_emptytag_check parameter.
        """
        if not skip_emptytag_check and tag in misc.empty_tags:
            self.handle_startendtag(tag, attrs)
            return

        if self.stack:
            # Note: getpos() return 1-indexed line numbers and 0-indexed
            # column numbers
            node = Node(tag, self.get_starttag_text(), self.stack[-1], self.getpos())
            self.stack[-1].children.append(node)
            self.stack.append(node)

    def handle_endtag(self, tag):
        """To handle the end of a tag.

        If a script tag is opened, ignore all the junk in there until
        the tag is closed.
        """
        if self.stack:
            if self.stack[-1].tag == "script" and tag != "script":
                # ignore everything inside script tag
                return

            if tag != self.stack[-1].tag:
                # tag mismatch
                if any(n.tag == tag for n in self.stack):
                    msg = "no closing tag for '<{0}>'".format(
                        self.stack[-1].tag)
                    pos = self.stack[-1].start
                else:
                    msg = "no opening tag for '</{0}>'".format(tag)
                    pos = self.getpos()
                raise HTMLParser.HTMLParseError(msg, pos)

            self.stack[-1].end = self.getpos()
            self.stack.pop(-1)

    def get_current_node(self):
        """To return the current element (the one that enclose our cursor position)."""
        for c in self.tree.children:
            node, depth = self._closest_node(c, 0, None, -1, v.cursor())
            if node:
                return node

    def _closest_node(self, tree, depth, closest_node, closest_depth, pos):
        """To find the closest element that encloses our current cursor position."""
        if not tree.start or not tree.end:
            if not tree.start:
                self.last_known_error = dict(msg="malformed tag found", pos=tree.end)
            if not tree.end:
                self.last_known_error = dict(msg="malformed tag found", pos=tree.start)
            return (None, -1)

        row, col = pos
        startrow, startcol = tree.start[0], tree.start[1]
        endrow = tree.end[0]

        if tree.tag in misc.empty_tags:
            endcol = tree.start[1] + len(tree.starttag_text)
        else:
            endcol = tree.end[1] + len(tree.tag) + 2

        # check if the current position is inside the element boundaries
        if startrow < row < endrow:
            cond = True
        elif startrow == row and endrow != row and startcol <= col:
            cond = True
        elif endrow == row and startrow != row and col <= endcol:
            cond = True
        elif startrow == row and endrow == row and startcol <= col < endcol:
            cond = True
        else:
            cond = False

        # if cond is True the current element (tree) eclose our position. Now
        # we assume this is the closest node that enclose our position.
        if cond:

            closest_node = tree
            closest_depth = depth

            if not tree.children:
                return closest_node, closest_depth

            # if the current position is closest to the end of the current
            # enclosing tag, start iterating its children from the last element,
            # and vice-versa. This little piece of code just aims to improve
            # performances, nothing else.
            if row - tree.start[0] > tree.end[0] - row:
                rev = True
            else:
                rev = False

            for child in (reversed(tree.children) if rev else tree.children):
                n, d = self._closest_node(child, depth + 1, closest_node, closest_depth, pos)

                if d > closest_depth:
                    # a child of tree node is closest to the current position.
                    closest_node = n
                    closest_depth = d

                if depth < closest_depth:
                    # we have already found the closest node and we are going up
                    # the tree structure (depth < closest_depth). There is no
                    # need to continue the search
                    return closest_node, closest_depth

            return closest_node, closest_depth

        else:
            # untouched
            return closest_node, closest_depth

    def print_dom_tree(self, indent=2):
        """To print the parsed DOM tree."""

        def _print_tree(tree, depth, indent):
            """Internal function for printing the HTML tree."""
            print(" " * depth + tree.tag)
            for c in tree.children:
                _print_tree(c, depth + indent, indent)

        for c in self.tree.children:
            _print_tree(c, 0, indent)

    def all_nodes(self):
        """To return all DOM nodes as a generator."""

        def _flatten(tree):
            nodes = [tree]
            for c in tree.children:
                nodes += _flatten(c)
            return nodes

        nodes = []
        for c in self.tree.children:
            nodes += _flatten(c)
        return nodes

    def get_error(self):
        """To return the last known error."""
        if self.last_known_error is not None:
            return "Error found at {pos}, type: {msg}".format(**self.last_known_error)
        return "All should be fine!"

########NEW FILE########
__FILENAME__ = input
# -*- coding: utf-8 -*-
"""
breeze.utils.input
~~~~~~~~~~~~~~~~~~

This module defines the Input class that is responsible for handling
the input coming from the user via the command line.
"""

import vim


class Input:

    def __init__(self):
        self._reset()

    def _reset(self):
        """To reset the input state."""
        self.LEFT = self.RIGHT = self.UP = self.DOWN = None
        self.RETURN = self.ESC = self.TAB = self.CTRL = self.BS = None
        self.INTERRUPT = self.MOUSE = self.MAC_CMD = None
        self.CHAR = ""
        self.F1 = self.F2 = self.F3 = self.F4 = self.F5 = self.F6 = None
        self.F7 = self.F8 = self.F9 = self.F10 = self.F11 = self.F12 = None
        vim.command("let g:_breeze_char = ''")
        vim.command("let g:_breeze_interrupt = 0")

    def get(self):
        """To read a key pressed by the user."""
        self._reset()

        vim.command("""
            try |
             let g:_breeze_char = strtrans(getchar()) |
            catch |
             let g:_breeze_interrupt = 1 |
            endtry
        """)

        if vim.eval('g:_breeze_interrupt') == '1':  # Ctrl + c
            self.CTRL = True
            self.CHAR = unicode("c", "utf-8")
            self.INTERRUPT = True
            return

        raw_char = vim.eval('g:_breeze_char')

        # only with mac os
        # 'cmd' key has been pressed
        if raw_char.startswith("<80><fc><80>"):
            self.MAC_CMD = True
            char = raw_char.replace("<80><fc><80>", "")
            nr = vim.eval("char2nr('{0}')".format(char))
        else:
            # we use str2nr in order to get a negative number as a result if
            # the user press a special key such as backspace
            nr = int(vim.eval("str2nr('{0}')".format(raw_char)))

        if nr != 0:

            if nr == 13:
                self.RETURN = True
            elif nr == 27:
                self.ESC = True
            elif nr == 9:  # same as Ctrl+i.. miss something?
                self.TAB = True
            elif 1 <= nr <= 26:
                self.CTRL = True
                self.CHAR = vim.eval("nr2char({0})".format(nr + 96)).decode('utf-8')
            else:
                self.CHAR = vim.eval("nr2char({0})".format(nr)).decode('utf-8')

        else:

            c = raw_char.replace("<80>", "")
            if c == 'kl':
                self.LEFT = True
            elif c == 'kr':
                self.RIGHT = True
            elif c == 'ku':
                self.UP = True
            elif c == 'kd':
                self.DOWN = True
            elif c == 'kb':  # backspace
                self.BS = True
            elif c == 'k1':
                self.F1 = True
            elif c == 'k2':
                self.F2 = True
            elif c == 'k3':
                self.F3 = True
            elif c == 'k4':
                self.F4 = True
            elif c == 'k5':
                self.F5 = True
            elif c == 'k6':
                self.F6 = True
            elif c == 'k7':
                self.F7 = True
            elif c == 'k8':
                self.F8 = True
            elif c == 'k9':
                self.F9 = True
            elif c == 'k10':
                self.F10 = True
            elif c == 'k11':
                self.F11 = True
            elif c == 'k12':
                self.F12 = True
            else:
                # mouse clicks or scrolls
                self.MOUSE = True

########NEW FILE########
__FILENAME__ = misc
# -*- coding: utf-8 -*-
"""
breeze.utils.misc
~~~~~~~~~~~~~~~~~

This module defines various utilities.
"""


# Empty HTML tags
empty_tags = set([
    "br", "base", "hr", "meta", "link", "base", "source",
    "img", "embed", "param", "area", "col", "input", "command",
    "keygen", "track", "wbr"])

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
"""
breeze.utils.settings
~~~~~~~~~~~~~~~~~~~~~

This module defines various utility functions for dealing with vim variables.
"""

import vim


prefix = 'g:breeze_'


def set(name, value):
    """To set a vim variable to a given value."""
    if isinstance(value, basestring):
        val = "'{0}'".format(value)
    elif isinstance(value, bool):
        val = 1 if value else 0
    else:
        val = value

    vim.command("let {0} = {0}".format(prefix + name, val))


def get(name, type=None):
    """To get the value of a vim variable."""
    rawval = vim.eval(prefix + name)
    if type is bool:
        return False if rawval == '0' else True
    elif type is int:
        return int(rawval)
    elif type is float:
        return float(rawval)
    else:
        return rawval

########NEW FILE########
__FILENAME__ = v
# -*- coding: utf-8 -*-
"""
breeze.utils.v
~~~~~~~~~~~~~~

This module defines thin wrappers around vim commands and functions.
"""

import vim

from breeze.utils import settings


def echom(msg):
    """To display a message to the user via the command line."""
    vim.command('echom "[breeze] {0}"'.format(msg.replace('"', '\"')))


def echohl(msg, hlgroup):
    """To display a colored message to the user via the command line."""
    vim.command("echohl {0}".format(hlgroup))
    echom(msg)
    vim.command("echohl None")


def redraw():
    """Little wrapper around the redraw command."""
    vim.command('redraw')


def buf():
    """To return the curent vim buffer."""
    return vim.current.buffer


def cursor(target=None):
    """To move the cursor or return the current cursor position."""
    if not target:
        return vim.current.window.cursor
    else:
        vim.current.window.cursor = target


def window_bundaries():
    """To return the top and bottom lines number for the current window."""
    curr_pos = cursor()

    scrolloff = vim.eval("&scrolloff")
    vim.command("setlocal scrolloff=0")

    # :help keepjumps -> Moving around in {command} does not change the '',
    # '. and '^ marks, the jumplist or the changelist.
    vim.command("keepjumps normal! H")
    top = cursor()[0]
    vim.command("keepjumps normal! L")
    bot = cursor()[0]

    # restore position and changed options
    cursor(curr_pos)
    vim.command("setlocal scrolloff={0}".format(scrolloff))

    return top, bot


def highlight(group, patt, priority=10):
    """Wrapper of the matchadd() vim function."""
    return vim.eval("matchadd('{0}', '{1}', {2})".format(group, patt, priority))


def clear_hl(*groups):
    """To clear Breeze highlightings."""
    for match in vim.eval("getmatches()"):
        if match['group'] in groups:
            vim.command("call matchdelete({0})".format(match['id']))


def subst_char(buffer, v, row, col):
    """To substitute a character in the buffer with the given character at the
    given position. Return the substituted character."""
    if row >= len(buffer):
        raise ValueError("row index out of bound")

    new_line = list(buffer[row])
    if col >= len(new_line):
        raise ValueError("column index out of bound")

    old = buffer[row][col]
    new_line[col] = v
    buffer[row] = "".join(new_line)

    return old

########NEW FILE########
