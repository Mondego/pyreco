__FILENAME__ = action
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 mooz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

# ============================================================ #
# Action
# ============================================================ #

class Action(object):
    def __init__(self, desc, act, args):
        self.act  = act
        self.desc = desc
        self.args = args

def action(**args):
    def act_handler(act):
        return Action(act.__doc__, act, args)
    return act_handler

########NEW FILE########
__FILENAME__ = actions
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 mooz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import sys

from percol.action import action

def double_quote_string(string):
    return '"' + string.replace('"', r'\"') + '"'

@action()
def output_to_stdout(lines, percol):
    "output marked (selected) items to stdout"
    for line in lines:
        sys.stdout.write(percol.display.get_raw_string(line))
        sys.stdout.write("\n")

@action()
def output_to_stdout_double_quote(lines, percol):
    "output marked (selected) items to stdout with double quotes"
    for line in lines:
        sys.stdout.write(percol.display.get_raw_string(double_quote_string(line)))
        sys.stdout.write("\n")

########NEW FILE########
__FILENAME__ = ansi
# -*- coding: utf-8 -*-
# Copyright (C) 2011 mooz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

from percol.markup import MarkupParser

import sys

# http://graphcomp.com/info/specs/ansi_col.html

DISPLAY_ATTRIBUTES = {
    "reset"      : 0,
    "bold"       : 1,
    "bright"     : 1,
    "dim"        : 2,
    "underline"  : 4,
    "underscore" : 4,
    "blink"      : 5,
    "reverse"    : 7,
    "hidden"     : 8,
    # Colors
    "black"      : 30,
    "red"        : 31,
    "green"      : 32,
    "yellow"     : 33,
    "blue"       : 34,
    "magenta"    : 35,
    "cyan"       : 36,
    "white"      : 37,
    "on_black"   : 40,
    "on_red"     : 41,
    "on_green"   : 42,
    "on_yellow"  : 43,
    "on_blue"    : 44,
    "on_magenta" : 45,
    "on_cyan"    : 46,
    "on_white"   : 47,
}

markup_parser = MarkupParser()

def markup(string):
    return decorate_parse_result(markup_parser.parse(string))

def decorate_parse_result(parse_result):
    decorated_string = ""
    for (fragment_string, attributes) in parse_result:
        decorated_string += decorate_string_with_attributes(fragment_string, attributes)
    return decorated_string

def decorate_string_with_attributes(string, attributes):
    attribute_numbers = attribute_names_to_numbers(attributes)
    attribute_format = ";".join(attribute_numbers)
    return "\033[{0}m{1}\033[0m".format(attribute_format, string)

def attribute_names_to_numbers(attribute_names):
    return [str(DISPLAY_ATTRIBUTES[name])
            for name in attribute_names
            if name in DISPLAY_ATTRIBUTES]

if __name__ == "__main__":
    tests = (
        "hello",
        "hello <red>red</red> normal",
        "hello <on_green>with background green <underline>this is underline <red>and red</red></underline></on_green> then, normal",
        "baaaaa<green>a<blue>aa</green>a</blue>aaaaaaa", # unmatch
        "baaaaa<green>a<blue>aa</blue>a</green>aaaaaaa",
        "<underline>hello \\<red>red\\</red> normal</underline>",  # escape
        u"マルチ<magenta>バイト<blue>文字</blue>の</magenta>テスト", # multibyte
    )

    for test in tests:
        try:
            print("----------------------------------------------------------")
            print(markup(test))
        except Exception as e:
            print("fail: " + str(e))

########NEW FILE########
__FILENAME__ = cli
# -*- coding: utf-8 -*-
#
# Copyright (C) 2013 mooz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import sys
import os
import locale

from optparse import OptionParser

import percol
from percol import Percol
from percol import tty
from percol import debug
from percol import ansi

INSTRUCTION_TEXT = ansi.markup("""<bold><blue>{logo}</blue></bold>
                                <on_blue><underline> {version} </underline></on_blue>

You did not give any inputs to <underline>percol</underline>. Check following typical usages and try again.

<underline>(1) Giving a filename,</underline>

 $ <underline>percol</underline> /var/log/syslog

<underline>(2) or specifying a redirection.</underline>

 $ ps aux | <underline>percol</underline>

""").format(logo = percol.__logo__,
            version = percol.__version__)

def load_rc(percol, path = None, encoding = 'utf-8'):
    if path is None:
        path = os.path.expanduser("~/.percol.d/rc.py")
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rc.py')
    try:
        with open(path, 'r') as rc:
            exec(rc.read().decode(encoding), locals())
    except Exception as e:
        debug.log("Exception in rc file {0}".format(path), e)

def eval_string(percol, string_to_eval, encoding = 'utf-8'):
    try:
        import types
        if string_to_eval.__class__ != types.UnicodeType:
            string_to_eval = string_to_eval.decode(encoding)
        exec(string_to_eval, locals())
    except Exception as e:
        debug.log("Exception in eval_string", e)

def setup_options(parser):
    parser.add_option("--tty", dest = "tty",
                      help = "path to the TTY (usually, the value of $TTY)")
    parser.add_option("--rcfile", dest = "rcfile",
                      help = "path to the settings file")
    parser.add_option("--output-encoding", dest = "output_encoding",
                      help = "encoding for output")
    parser.add_option("--input-encoding", dest = "input_encoding", default = "utf8",
                      help = "encoding for input and output (default 'utf8')")
    parser.add_option("--query", dest = "query",
                      help = "pre-input query")
    parser.add_option("--eager", action = "store_true", dest = "eager", default = False,
                      help = "suppress lazy matching (slower, but display correct candidates count)")
    parser.add_option("--eval", dest = "string_to_eval",
                      help = "eval given string after loading the rc file")
    parser.add_option("--prompt", dest = "prompt", default = None,
                      help = "specify prompt (percol.view.PROMPT)")
    parser.add_option("--right-prompt", dest = "right_prompt", default = None,
                      help = "specify right prompt (percol.view.RPROMPT)")
    parser.add_option("--match-method", dest = "match_method", default = "",
                      help = "specify matching method for query. `string` (default) and `regex` are currently supported")
    parser.add_option("--caret-position", dest = "caret",
                      help = "position of the caret (default length of the `query`)")
    parser.add_option("--initial-index", dest = "index",
                      help = "position of the initial index of the selection (numeric, \"first\" or \"last\")")
    parser.add_option("--case-sensitive", dest = "case_sensitive", default = False, action="store_true",
                      help = "whether distinguish the case of query or not")
    parser.add_option("--reverse", dest = "reverse", default = False, action="store_true",
                      help = "whether reverse the order of candidates or not")
    parser.add_option("--auto-fail", dest = "auto_fail", default = False, action="store_true",
                      help = "auto fail if no candidates")
    parser.add_option("--auto-match", dest = "auto_match", default = False, action="store_true",
                      help = "auto matching if only one candidate")

    parser.add_option("--prompt-top", dest = "prompt_on_top", default = None, action="store_true",
                      help = "display prompt top of the screen (default)")
    parser.add_option("--prompt-bottom", dest = "prompt_on_top", default = None, action="store_false",
                      help = "display prompt bottom of the screen")
    parser.add_option("--result-top-down", dest = "results_top_down", default = None, action="store_true",
                      help = "display results top down (default)")
    parser.add_option("--result-bottom-up", dest = "results_top_down", default = None, action="store_false",
                      help = "display results bottom up instead of top down")

    parser.add_option("--quote", dest = "quote", default = False, action="store_true",
                      help = "whether quote the output line")
    parser.add_option("--peep", action = "store_true", dest = "peep", default = False,
                      help = "exit immediately with doing nothing to cache module files and speed up start-up time")

def set_proper_locale(options):
    locale.setlocale(locale.LC_ALL, '')
    output_encoding = locale.getpreferredencoding()
    if options.output_encoding:
        output_encoding = options.output_encoding
    return output_encoding

def read_input(filename, encoding, reverse=False):
    if filename:
        stream = open(filename, "r")
    else:
        stream = sys.stdin
    if reverse:
        lines = reversed(stream.readlines())
    else:
        lines = stream
    for line in lines:
        yield unicode(line.rstrip("\r\n"), encoding, "replace")
    stream.close()

def decide_match_method(options):
    if options.match_method == "regex":
        from percol.finder import FinderMultiQueryRegex
        return FinderMultiQueryRegex
    if options.match_method == "migemo":
        from percol.finder import FinderMultiQueryMigemo
        return FinderMultiQueryMigemo
    else:
        from percol.finder import FinderMultiQueryString
        return FinderMultiQueryString

def main():
    parser = OptionParser(usage = "Usage: %prog [options] [FILE]")
    setup_options(parser)
    options, args = parser.parse_args()

    if options.peep:
        exit(1)

    def exit_program(msg = None, show_help = True):
        if not msg is None:
            print("\n" + msg + "\n")
        if show_help:
            parser.print_help()
        exit(1)

    # get ttyname
    ttyname = options.tty or tty.get_ttyname()
    if not ttyname:
        exit_program("""Error: No tty name is given and failed to guess it from descriptors.
Maybe all descriptors are redirecred.""")

    # decide which encoding to use
    output_encoding = set_proper_locale(options)
    input_encoding = options.input_encoding

    with open(ttyname, "r+w") as tty_f:
        if not tty_f.isatty():
            exit_program("Error: {0} is not a tty file".format(ttyname), show_help = False)

        filename = args[0] if len(args) > 0 else None

        if filename is None and sys.stdin.isatty():
            tty_f.write(INSTRUCTION_TEXT)
            exit_program(show_help = False)

        # read input
        try:
            candidates = read_input(filename, input_encoding, reverse=options.reverse)
        except KeyboardInterrupt:
            exit_program("Canceled", show_help = False)

        # setup actions
        import percol.actions as actions
        if (options.quote):
            acts = (actions.output_to_stdout_double_quote, )
        else:
            acts = (actions.output_to_stdout, actions.output_to_stdout_double_quote)

        # arrange finder class
        candidate_finder_class = action_finder_class = decide_match_method(options)

        def set_finder_attribute_from_option(finder_instance):
            finder_instance.lazy_finding = not options.eager
            finder_instance.case_insensitive = not options.case_sensitive

        def set_if_not_none(src, dest, name):
            value = getattr(src, name)
            if value is not None:
                setattr(dest, name, value)

        with Percol(descriptors = tty.reconnect_descriptors(tty_f),
                    candidates = candidates,
                    actions = acts,
                    finder = candidate_finder_class,
                    action_finder = action_finder_class,
                    query = options.query,
                    caret = options.caret,
                    index = options.index,
                    encoding = output_encoding) as percol:
            # load run-command file
            load_rc(percol, options.rcfile, input_encoding)
            # override prompts
            if options.prompt is not None:
                percol.view.__class__.PROMPT = property(lambda self: options.prompt)
            if options.right_prompt is not None:
                percol.view.__class__.RPROMPT = property(lambda self: options.right_prompt)
            # evalutate strings specified by the option argument
            if options.string_to_eval is not None:
                eval_string(percol, options.string_to_eval, locale.getpreferredencoding())
            # finder settings from option values
            set_finder_attribute_from_option(percol.model_candidate.finder)
            set_finder_attribute_from_option(percol.model_action.finder)
            # view settings from option values
            set_if_not_none(options, percol.view, 'prompt_on_top')
            set_if_not_none(options, percol.view, 'results_top_down')
            # enter main loop
            if options.auto_fail and percol.has_no_candidate():
                exit_code = percol.cancel_with_exit_code()
            elif options.auto_match and percol.has_only_one_candidate():
                exit_code = percol.finish_with_exit_code()
            else:
                exit_code = percol.loop()

        exit(exit_code)

########NEW FILE########
__FILENAME__ = command
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 mooz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

class SelectorCommand(object):
    """
    Wraps up SelectorModel and provides advanced commands
    """
    def __init__(self, model, view):
        self.model = model
        self.view = view

    # ------------------------------------------------------------ #
    # Selection
    # ------------------------------------------------------------ #

    # Line

    def select_successor(self):
        self.model.select_index(self.model.index + 1)

    def select_predecessor(self):
        self.model.select_index(self.model.index - 1)

    def select_next(self):
        if self.view.results_top_down:
            self.select_successor()
        else:
            self.select_predecessor()

    def select_previous(self):
        if self.view.results_top_down:
            self.select_predecessor()
        else:
            self.select_successor()

    # Top / Bottom

    def select_top(self):
        if self.view.results_top_down:
            self.model.select_top()
        else:
            self.model.select_bottom()

    def select_bottom(self):
        if self.view.results_top_down:
            self.model.select_bottom()
        else:
            self.model.select_top()

    # Page

    def select_successor_page(self):
        self.model.select_index(self.model.index + self.view.RESULTS_DISPLAY_MAX)

    def select_predecessor_page(self):
        self.model.select_index(self.model.index - self.view.RESULTS_DISPLAY_MAX)

    def select_next_page(self):
        if self.view.results_top_down:
            self.select_successor_page()
        else:
            self.select_predecessor_page()

    def select_previous_page(self):
        if self.view.results_top_down:
            self.select_predecessor_page()
        else:
            self.select_successor_page()

    # ------------------------------------------------------------ #
    # Mark
    # ------------------------------------------------------------ #

    def toggle_mark(self):
        self.model.set_is_marked(not self.model.get_is_marked())

    def toggle_mark_and_next(self):
        self.toggle_mark()
        self.select_successor()

    def __get_all_mark_indices(self):
        return xrange(self.model.results_count)

    def mark_all(self):
        for mark_index in self.__get_all_mark_indices():
            self.model.set_is_marked(True, mark_index)

    def unmark_all(self):
        for mark_index in self.__get_all_mark_indices():
            self.model.set_is_marked(False, mark_index)

    def toggle_mark_all(self):
        for mark_index in self.__get_all_mark_indices():
            self.model.set_is_marked(not self.model.get_is_marked(mark_index), mark_index)

    # ------------------------------------------------------------ #
    # Caret
    # ------------------------------------------------------------ #

    def beginning_of_line(self):
        self.model.set_caret(0)

    def end_of_line(self):
        self.model.set_caret(len(self.model.query))

    def backward_char(self):
        self.model.set_caret(self.model.caret - 1)

    def forward_char(self):
        self.model.set_caret(self.model.caret + 1)

    # ------------------------------------------------------------ #
    # Text
    # ------------------------------------------------------------ #

    def delete_backward_char(self):
        if self.model.caret > 0:
            self.backward_char()
            self.delete_forward_char()

    def delete_backward_word(self):
        from re import search
        caret = self.model.caret
        if caret > 0:
            q = self.model.query
            qc = q[:caret]
            m = search(r'\S+', qc[::-1])
            self.model.query = qc[:-m.end()] + q[caret:]
            self.model.set_caret(caret - m.end())

    def delete_forward_char(self):
        caret = self.model.caret
        self.model.query = self.model.query[:caret] + self.model.query[caret + 1:]

    def delete_end_of_line(self):
        self.model.query = self.model.query[:self.model.caret]

    def clear_query(self):
        self.model.query = u""
        self.model.set_caret(0)

    def transpose_chars(self):
        caret = self.model.caret
        qlen = len(self.model.query)
        if qlen <= 1:
            self.end_of_line()
        elif caret == 0:
            self.forward_char()
            self.transpose_chars()
        elif caret == qlen:
            self.backward_char()
            self.transpose_chars()
        else:
            self.model.query = self.model.query[:caret - 1] + \
                               self.model.query[caret] + \
                               self.model.query[caret - 1] + \
                               self.model.query[caret + 1:]
            self.forward_char()

    # ------------------------------------------------------------ #
    # Text > kill
    # ------------------------------------------------------------ #

    def kill_end_of_line(self):
        self.model.killed = self.model.query[self.model.caret:]
        self.model.query  = self.model.query[:self.model.caret]

    killed = None                  # default
    def yank(self):
        if self.model.killed:
            self.model.insert_string(self.model.killed)

    # ------------------------------------------------------------ #
    # Finder
    # ------------------------------------------------------------ #

    def specify_case_sensitive(self, case_sensitive):
        self.model.finder.case_insensitive = not case_sensitive
        self.model.force_search()

    def toggle_case_sensitive(self):
        self.model.finder.case_insensitive = not self.model.finder.case_insensitive
        self.model.force_search()

    def specify_finder(self, preferred_finder_class):
        self.model.remake_finder(preferred_finder_class)
        self.model.force_search()

    def toggle_finder(self, preferred_finder_class):
        if self.model.finder.__class__ == preferred_finder_class:
            self.model.remake_finder(self.model.original_finder_class)
        else:
            self.model.remake_finder(preferred_finder_class)
        self.model.force_search()

########NEW FILE########
__FILENAME__ = debug
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 mooz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import pprint

pp = pprint.PrettyPrinter(indent=2)

def log(name, s = ""):
    with open("/tmp/percol-log", "a") as f:
        f.write(str(name) + " : " + str(s) + "\n")

def dump(obj):
    with open("/tmp/percol-log", "a") as f:
        f.write(pp.pformat(obj) + "\n")
    return obj

########NEW FILE########
__FILENAME__ = display
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 mooz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import unicodedata
import types
import curses
import re

from percol import markup, debug

FG_COLORS = {
    "black"   : curses.COLOR_BLACK,
    "red"     : curses.COLOR_RED,
    "green"   : curses.COLOR_GREEN,
    "yellow"  : curses.COLOR_YELLOW,
    "blue"    : curses.COLOR_BLUE,
    "magenta" : curses.COLOR_MAGENTA,
    "cyan"    : curses.COLOR_CYAN,
    "white"   : curses.COLOR_WHITE,
}

BG_COLORS = dict(("on_" + name, value) for name, value in FG_COLORS.iteritems())

ATTRS = {
    "altcharset" : curses.A_ALTCHARSET,
    "blink"      : curses.A_BLINK,
    "bold"       : curses.A_BOLD,
    "dim"        : curses.A_DIM,
    "normal"     : curses.A_NORMAL,
    "standout"   : curses.A_STANDOUT,
    "underline"  : curses.A_UNDERLINE,
}

COLOR_COUNT = len(FG_COLORS)

# ============================================================ #
# Markup
# ============================================================ #

def get_fg_color(attrs):
    for attr in attrs:
        if attr in FG_COLORS:
            return FG_COLORS[attr]
    return FG_COLORS["default"]

def get_bg_color(attrs):
    for attr in attrs:
        if attr in BG_COLORS:
            return BG_COLORS[attr]
    return BG_COLORS["on_default"]

def get_attributes(attrs):
    for attr in attrs:
        if attr in ATTRS:
            yield ATTRS[attr]

# ============================================================ #
# Unicode
# ============================================================ #

def screen_len(s, beg = None, end = None):
    if beg is None:
        beg = 0
    if end is None:
        end = len(s)

    if "\t" in s:
        # consider tabstop (very naive approach)
        beg = len(s[0:beg].expandtabs())
        end = len(s[beg:end].expandtabs())
        s = s.expandtabs()

    if s.__class__ != types.UnicodeType:
        return end - beg

    dis_len = end - beg
    for i in xrange(beg, end):
        if unicodedata.east_asian_width(s[i]) in ("W", "F"):
            dis_len += 1

    return dis_len

def screen_length_to_bytes_count(string, screen_length_limit, encoding):
    bytes_count = 0
    screen_length = 0
    for unicode_char in string:
        screen_length += screen_len(unicode_char)
        char_bytes_count = len(unicode_char.encode(encoding))
        bytes_count += char_bytes_count
        if screen_length > screen_length_limit:
            bytes_count -= char_bytes_count
            break
    return bytes_count

# ============================================================ #
# Display
# ============================================================ #

class Display(object):
    def __init__(self, screen, encoding):
        self.screen   = screen
        self.encoding = encoding
        self.markup_parser   = markup.MarkupParser()

        curses.start_color()

        self.has_default_colors = curses.COLORS > COLOR_COUNT

        if self.has_default_colors:
            # xterm-256color
            curses.use_default_colors()
            FG_COLORS["default"]    = -1
            BG_COLORS["on_default"] = -1
            self.init_color_pairs()
        elif curses.COLORS != 0:
            # ansi linux rxvt ...etc.
            self.init_color_pairs()
            FG_COLORS["default"]    = curses.COLOR_WHITE
            BG_COLORS["on_default"] = curses.COLOR_BLACK
        else: # monochrome, curses.COLORS == 0
            # vt100 x10term wy520 ...etc.
            FG_COLORS["default"]    = curses.COLOR_WHITE
            BG_COLORS["on_default"] = curses.COLOR_BLACK

        self.update_screen_size()

    def update_screen_size(self):
        self.HEIGHT, self.WIDTH = self.screen.getmaxyx()

    @property
    def Y_BEGIN(self):
        return 0

    @property
    def Y_END(self):
        return self.HEIGHT - 1

    @property
    def X_BEGIN(self):
        return 0

    @property
    def X_END(self):
        return self.WIDTH - 1

    # ============================================================ #
    # Color Pairs
    # ============================================================ #

    def init_color_pairs(self):
        for fg_s, fg in FG_COLORS.iteritems():
            for bg_s, bg in BG_COLORS.iteritems():
                if not (fg == bg == 0):
                    curses.init_pair(self.get_pair_number(fg, bg), fg, bg)

    def get_normalized_number(self, number):
        return COLOR_COUNT if number < 0 else number

    def get_pair_number(self, fg, bg):
        if self.has_default_colors:
            # Assume the number of colors is up to 16 (2^4 = 16)
            return self.get_normalized_number(fg) | (self.get_normalized_number(bg) << 4)
        else:
            return self.get_normalized_number(fg) + self.get_normalized_number(bg) * COLOR_COUNT

    def get_color_pair(self, fg, bg):
        return curses.color_pair(self.get_pair_number(fg, bg))

    # ============================================================ #
    # Aligned string
    # ============================================================ #

    def get_pos_x(self, x_align, x_offset, whole_len):
        position = 0

        if x_align == "left":
            position = x_offset
        elif x_align == "right":
            position = self.WIDTH - whole_len - x_offset
        elif x_align == "center":
            position = x_offset + (int(self.WIDTH - whole_len) / 2)

        return position

    def get_pos_y(self, y_align, y_offset):
        position = 0

        if y_align == "top":
            position = y_offset
        elif y_align == "bottom":
            position = self.HEIGHT - y_offset
        elif y_align == "center":
            position = y_offset + int(self.HEIGHT / 2)

        return position

    def get_flag_from_attrs(self, attrs):
        flag = self.get_color_pair(get_fg_color(attrs), get_bg_color(attrs))

        for attr in get_attributes(attrs):
            flag |= attr

        return flag

    def add_aligned_string_markup(self, markup, **keywords):
        return self.add_aligned_string_tokens(self.markup_parser.parse(markup), **keywords)

    def add_aligned_string_tokens(self, tokens,
                                  y_align = "top", x_align = "left",
                                  y_offset = 0, x_offset = 0,
                                  fill = False, fill_char = " ", fill_style = None):
        dis_lens  = [screen_len(s) for (s, attrs) in tokens]
        whole_len = sum(dis_lens)

        pos_x = self.get_pos_x(x_align, x_offset, whole_len)
        pos_y = self.get_pos_y(y_align, y_offset)

        org_pos_x = pos_x

        for i, (s, attrs) in enumerate(tokens):
            self.add_string(s, pos_y, pos_x, self.attrs_to_style(attrs))
            pos_x += dis_lens[i]

        if fill:
            self.add_filling(fill_char, pos_y, 0, org_pos_x, fill_style)
            self.add_filling(fill_char, pos_y, pos_x, self.WIDTH, fill_style)

        return pos_y, org_pos_x

    def add_aligned_string(self, s,
                           y_align = "top", x_align = "left",
                           y_offset = 0, x_offset = 0,
                           style = None,
                           fill = False, fill_char = " ", fill_style = None):
        dis_len = screen_len(s)

        pos_x = self.get_pos_x(x_align, x_offset, dis_len)
        pos_y = self.get_pos_y(y_align, y_offset)

        self.add_string(s, pos_y, pos_x, style)

        if fill:
            if fill_style is None:
                fill_style = style
            self.add_filling(fill_char, pos_y, 0, pos_x, fill_style)
            self.add_filling(fill_char, pos_y, pos_x + dis_len, self.WIDTH, fill_style)

        return pos_y, pos_x

    def add_filling(self, fill_char, pos_y, pos_x_beg, pos_x_end, style):
        filling_len = pos_x_end - pos_x_beg
        if filling_len > 0:
            self.add_string(fill_char * filling_len, pos_y, pos_x_beg, style)

    def attrs_to_style(self, attrs):
        if attrs is None:
            return 0

        style = self.get_color_pair(get_fg_color(attrs), get_bg_color(attrs))
        for attr in get_attributes(attrs):
            style |= attr

        return style

    def add_string(self, s, pos_y = 0, pos_x = 0, style = None, n = -1):
        self.addnstr(pos_y, pos_x, s, n if n >= 0 else self.WIDTH - pos_x, style)

    # ============================================================ #
    # Fundamental
    # ============================================================ #

    def erase(self):
        self.screen.erase()

    def clear(self):
        self.screen.clear()

    def refresh(self):
        self.screen.refresh()

    def get_raw_string(self, s):
        return s.encode(self.encoding) if s.__class__ == types.UnicodeType else s

    def addnstr(self, y, x, s, n, style):
        if style.__class__ != types.IntType:
            style = self.attrs_to_style(style)

        # Compute bytes count of the substring that fits in the screen
        bytes_count_to_display = screen_length_to_bytes_count(s, n, self.encoding)

        try:
            sanitized_str = re.sub(r'[\x00-\x08\x0a-\x1f]', '?', s)
            raw_str = self.get_raw_string(sanitized_str)
            self.screen.addnstr(y, x, raw_str, bytes_count_to_display, style)
            return True
        except curses.error:
            return False

if __name__ == "__main__":
    import locale

    locale.setlocale(locale.LC_ALL, '')

    screen = curses.initscr()

    display = Display(screen, locale.getpreferredencoding())

    display.add_string("-" * display.WIDTH, pos_y = 2)

    display.add_aligned_string_markup("<underline><bold><red>foo</red> <blue>bar</blue> <green>baz<green/> <cyan>qux</cyan></bold></underline>",
                                      x_align = "center", y_offset = 3)

    display.add_aligned_string_markup(u"ああ，<on_green>なんて<red>赤くて<bold>太くて</on_green>太い，</bold>そして赤い</red>リンゴ",
                                      y_offset = 4,
                                      x_offset = -20,
                                      x_align = "center",
                                      fill = True, fill_char = "*")

    display.add_aligned_string(u"こんにちは",
                               y_offset = 5,
                               x_offset = 0,
                               x_align = "right",
                               fill = True, fill_char = '*', fill_style = display.attrs_to_style(("bold", "white", "on_green")))

    display.add_aligned_string(u" foo bar baz qux ",
                               x_align = "center", y_align = "center",
                               style = display.attrs_to_style(("bold", "white", "on_default")),
                               fill = True, fill_char = '-')

    screen.getch()

########NEW FILE########
__FILENAME__ = finder
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 mooz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

from abc import ABCMeta, abstractmethod
from percol.lazyarray import LazyArray

# ============================================================ #
# Finder
# ============================================================ #

class Finder(object):
    __metaclass__ = ABCMeta

    def __init__(self, **args):
        pass

    def clone_as(self, new_finder_class):
        new_finder = new_finder_class(collection = self.collection)
        new_finder.lazy_finding = self.lazy_finding
        return new_finder

    @abstractmethod
    def get_name(self):
        pass

    @abstractmethod
    def find(self, query, collection = None):
        pass

    lazy_finding = True
    def get_results(self, query, collection = None):
        if self.lazy_finding:
            return LazyArray((result for result in self.find(query, collection)))
        else:
            return [result for result in self.find(query, collection)]

# ============================================================ #
# Cached Finder
# ============================================================ #

class CachedFinder(Finder):
    def __init__(self, **args):
        self.results_cache = {}

    def get_collection_from_trie(self, query):
        """
        If any prefix of the query matches a past query, use its
        result as a collection to improve performance (prefix of the
        query constructs a trie)
        """
        for i in xrange(len(query) - 1, 0, -1):
            query_prefix = query[0:i]
            if query_prefix in self.results_cache:
                return (line for (line, res, idx) in self.results_cache[query_prefix])
        return None

    def get_results(self, query):
        if query in self.results_cache:
            return self.results_cache[query]
        collection = self.get_collection_from_trie(query) or self.collection
        return Finder.get_results(self, query, collection)

# ============================================================ #
# Finder > multiquery
# ============================================================ #

class FinderMultiQuery(CachedFinder):
    def __init__(self, collection, split_str = " "):
        CachedFinder.__init__(self)

        self.collection = collection
        self.split_str  = split_str

    def clone_as(self, new_finder_class):
        new_finder = Finder.clone_as(self, new_finder_class)
        new_finder.case_insensitive = self.case_insensitive
        new_finder.and_search = self.and_search
        return new_finder

    case_insensitive = True

    dummy_res = [["", [(0, 0)]]]

    def find(self, query, collection = None):
        query_is_empty = query == ""

        # Arrange queries
        if self.case_insensitive:
            query = query.lower()
        queries = [self.transform_query(sub_query)
                   for sub_query in query.split(self.split_str)]

        if collection is None:
            collection = self.collection

        for idx, line in enumerate(collection):
            if query_is_empty:
                res = self.dummy_res
            else:
                if self.case_insensitive:
                    line_to_match = line.lower()
                else:
                    line_to_match = line
                res = self.find_queries(queries, line_to_match)

            if res:
                yield line, res, idx

    and_search = True

    def find_queries(self, sub_queries, line):
        res = []

        and_search = self.and_search

        for subq in sub_queries:
            if subq:
                find_info = self.find_query(subq, line)
                if find_info:
                    res.append((subq, find_info))
                elif and_search:
                    return None
        return res

    @abstractmethod
    def find_query(self, needle, haystack):
        # return [(pos1, pos1_len), (pos2, pos2_len), ...]
        #
        # where `pos1', `pos2', ... are begining positions of all occurence of needle in `haystack'
        # and `pos1_len', `pos2_len', ... are its length.
        pass

    # override this method if needed
    def transform_query(self, query):
        return query

# ============================================================ #
# Finder > AND search
# ============================================================ #

class FinderMultiQueryString(FinderMultiQuery):
    def get_name(self):
        return "string"

    trie_style_matching = True

    def find_query(self, needle, haystack):
        stride = len(needle)
        start  = 0
        res    = []

        while True:
            found = haystack.find(needle, start)
            if found < 0:
                break
            res.append((found, stride))
            start = found + stride

        return res

# ============================================================ #
# Finder > AND search > Regular Expression
# ============================================================ #

class FinderMultiQueryRegex(FinderMultiQuery):
    def get_name(self):
        return "regex"

    def transform_query(self, needle):
        try:
            import re
            return re.compile(needle)
        except:
            return None

    def find_query(self, needle, haystack):
        try:
            matched = needle.search(haystack)
            return [(matched.start(), matched.end() - matched.start())]
        except:
            return None

# ============================================================ #
# Finder > AND search > Migemo
# ============================================================ #

class FinderMultiQueryMigemo(FinderMultiQuery):
    def get_name(self):
        return "migemo"

    dictionary_path = "/usr/local/share/migemo/utf-8/migemo-dict"
    minimum_query_length = 2

    migemo_instance = None
    @property
    def migemo(self):
        import migemo, os
        if self.migemo_instance is None:
            self.migemo_instance = migemo.Migemo(os.path.expanduser(self.dictionary_path))
        return self.migemo_instance

    def transform_query(self, needle):
        try:
            if len(needle) >= self.minimum_query_length:
                regexp_string = self.migemo.query(needle)
            else:
                regexp_string = needle
            import re
            return re.compile(regexp_string)
        except:
            return None

    def find_query(self, needle, haystack):
        try:
            matched = needle.search(haystack)
            return [(matched.start(), matched.end() - matched.start())]
        except:
            return None

########NEW FILE########
__FILENAME__ = key
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 mooz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import curses, array

SPECIAL_KEYS = {
    curses.KEY_A1        : "<a1>",
    curses.KEY_A3        : "<a3>",
    curses.KEY_B2        : "<b2>",
    curses.KEY_BACKSPACE : "<backspace>",
    curses.KEY_BEG       : "<beg>",
    curses.KEY_BREAK     : "<break>",
    curses.KEY_BTAB      : "<btab>",
    curses.KEY_C1        : "<c1>",
    curses.KEY_C3        : "<c3>",
    curses.KEY_CANCEL    : "<cancel>",
    curses.KEY_CATAB     : "<catab>",
    curses.KEY_CLEAR     : "<clear>",
    curses.KEY_CLOSE     : "<close>",
    curses.KEY_COMMAND   : "<command>",
    curses.KEY_COPY      : "<copy>",
    curses.KEY_CREATE    : "<create>",
    curses.KEY_CTAB      : "<ctab>",
    curses.KEY_DC        : "<dc>",
    curses.KEY_DL        : "<dl>",
    curses.KEY_DOWN      : "<down>",
    curses.KEY_EIC       : "<eic>",
    curses.KEY_END       : "<end>",
    curses.KEY_ENTER     : "<enter>",
    curses.KEY_EOL       : "<eol>",
    curses.KEY_EOS       : "<eos>",
    curses.KEY_EXIT      : "<exit>",
    curses.KEY_F0        : "<f0>",
    curses.KEY_F1        : "<f1>",
    curses.KEY_F10       : "<f10>",
    curses.KEY_F11       : "<f11>",
    curses.KEY_F12       : "<f12>",
    curses.KEY_F13       : "<f13>",
    curses.KEY_F14       : "<f14>",
    curses.KEY_F15       : "<f15>",
    curses.KEY_F16       : "<f16>",
    curses.KEY_F17       : "<f17>",
    curses.KEY_F18       : "<f18>",
    curses.KEY_F19       : "<f19>",
    curses.KEY_F2        : "<f2>",
    curses.KEY_F20       : "<f20>",
    curses.KEY_F21       : "<f21>",
    curses.KEY_F22       : "<f22>",
    curses.KEY_F23       : "<f23>",
    curses.KEY_F24       : "<f24>",
    curses.KEY_F25       : "<f25>",
    curses.KEY_F26       : "<f26>",
    curses.KEY_F27       : "<f27>",
    curses.KEY_F28       : "<f28>",
    curses.KEY_F29       : "<f29>",
    curses.KEY_F3        : "<f3>",
    curses.KEY_F30       : "<f30>",
    curses.KEY_F31       : "<f31>",
    curses.KEY_F32       : "<f32>",
    curses.KEY_F33       : "<f33>",
    curses.KEY_F34       : "<f34>",
    curses.KEY_F35       : "<f35>",
    curses.KEY_F36       : "<f36>",
    curses.KEY_F37       : "<f37>",
    curses.KEY_F38       : "<f38>",
    curses.KEY_F39       : "<f39>",
    curses.KEY_F4        : "<f4>",
    curses.KEY_F40       : "<f40>",
    curses.KEY_F41       : "<f41>",
    curses.KEY_F42       : "<f42>",
    curses.KEY_F43       : "<f43>",
    curses.KEY_F44       : "<f44>",
    curses.KEY_F45       : "<f45>",
    curses.KEY_F46       : "<f46>",
    curses.KEY_F47       : "<f47>",
    curses.KEY_F48       : "<f48>",
    curses.KEY_F49       : "<f49>",
    curses.KEY_F5        : "<f5>",
    curses.KEY_F50       : "<f50>",
    curses.KEY_F51       : "<f51>",
    curses.KEY_F52       : "<f52>",
    curses.KEY_F53       : "<f53>",
    curses.KEY_F54       : "<f54>",
    curses.KEY_F55       : "<f55>",
    curses.KEY_F56       : "<f56>",
    curses.KEY_F57       : "<f57>",
    curses.KEY_F58       : "<f58>",
    curses.KEY_F59       : "<f59>",
    curses.KEY_F6        : "<f6>",
    curses.KEY_F60       : "<f60>",
    curses.KEY_F61       : "<f61>",
    curses.KEY_F62       : "<f62>",
    curses.KEY_F63       : "<f63>",
    curses.KEY_F7        : "<f7>",
    curses.KEY_F8        : "<f8>",
    curses.KEY_F9        : "<f9>",
    curses.KEY_FIND      : "<find>",
    curses.KEY_HELP      : "<help>",
    curses.KEY_HOME      : "<home>",
    curses.KEY_IC        : "<ic>",
    curses.KEY_IL        : "<il>",
    curses.KEY_LEFT      : "<left>",
    curses.KEY_LL        : "<ll>",
    curses.KEY_MARK      : "<mark>",
    curses.KEY_MAX       : "<max>",
    curses.KEY_MESSAGE   : "<message>",
    curses.KEY_MIN       : "<min>",
    curses.KEY_MOUSE     : "<mouse>",
    curses.KEY_MOVE      : "<move>",
    curses.KEY_NEXT      : "<next>",
    curses.KEY_NPAGE     : "<npage>",
    curses.KEY_OPEN      : "<open>",
    curses.KEY_OPTIONS   : "<options>",
    curses.KEY_PPAGE     : "<ppage>",
    curses.KEY_PREVIOUS  : "<previous>",
    curses.KEY_PRINT     : "<print>",
    curses.KEY_REDO      : "<redo>",
    curses.KEY_REFERENCE : "<reference>",
    curses.KEY_REFRESH   : "<refresh>",
    curses.KEY_REPLACE   : "<replace>",
    curses.KEY_RESET     : "<reset>",
    curses.KEY_RESIZE    : "<resize>",
    curses.KEY_RESTART   : "<restart>",
    curses.KEY_RESUME    : "<resume>",
    curses.KEY_RIGHT     : "<right>",
    curses.KEY_SAVE      : "<save>",
    curses.KEY_SBEG      : "<sbeg>",
    curses.KEY_SCANCEL   : "<scancel>",
    curses.KEY_SCOMMAND  : "<scommand>",
    curses.KEY_SCOPY     : "<scopy>",
    curses.KEY_SCREATE   : "<screate>",
    curses.KEY_SDC       : "<sdc>",
    curses.KEY_SDL       : "<sdl>",
    curses.KEY_SELECT    : "<select>",
    curses.KEY_SEND      : "<send>",
    curses.KEY_SEOL      : "<seol>",
    curses.KEY_SEXIT     : "<sexit>",
    curses.KEY_SF        : "<sf>",
    curses.KEY_SFIND     : "<sfind>",
    curses.KEY_SHELP     : "<shelp>",
    curses.KEY_SHOME     : "<shome>",
    curses.KEY_SIC       : "<sic>",
    curses.KEY_SLEFT     : "<sleft>",
    curses.KEY_SMESSAGE  : "<smessage>",
    curses.KEY_SMOVE     : "<smove>",
    curses.KEY_SNEXT     : "<snext>",
    curses.KEY_SOPTIONS  : "<soptions>",
    curses.KEY_SPREVIOUS : "<sprevious>",
    curses.KEY_SPRINT    : "<sprint>",
    curses.KEY_SR        : "<sr>",
    curses.KEY_SREDO     : "<sredo>",
    curses.KEY_SREPLACE  : "<sreplace>",
    curses.KEY_SRESET    : "<sreset>",
    curses.KEY_SRIGHT    : "<sright>",
    curses.KEY_SRSUME    : "<srsume>",
    curses.KEY_SSAVE     : "<ssave>",
    curses.KEY_SSUSPEND  : "<ssuspend>",
    curses.KEY_STAB      : "<stab>",
    curses.KEY_SUNDO     : "<sundo>",
    curses.KEY_SUSPEND   : "<suspend>",
    curses.KEY_UNDO      : "<undo>",
    curses.KEY_UP        : "<up>",
}

# TODO: Better to use ord(curses.erasechar()) instead of 127
SPECIAL_KEYS[8] = SPECIAL_KEYS[127] = "<backspace>"

# Other
KEY_ESCAPE = 27

class KeyHandler(object):
    def __init__(self, screen):
        self.screen = screen

    def get_key_for(self, ch, escaped = False):
        k = None

        if self.is_displayable_key(ch):
            k = self.displayable_key_to_str(ch)
        elif ch in SPECIAL_KEYS:
            k = SPECIAL_KEYS[ch]
        elif self.is_ctrl_masked_key(ch):
            k = self.ctrl_masked_key_to_str(ch)
        elif ch == KEY_ESCAPE:
            if escaped:
                k = "ESC"
            else:
                k = "M-" + self.get_key_for(self.screen.getch(), escaped = True)
        elif ch == -1:
            k = "C-c"
        return k

    def get_utf8_key_for(self, ch):
        buf = array.array("B", [ch])
        buf.extend(self.screen.getch() for i in xrange(1, self.get_utf8_count(ch)))
        return buf.tostring().decode("utf-8")

    def is_utf8_multibyte_key(self, ch):
        return (ch & 0b11000000) == 0b11000000

    utf8_skip_data = [
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 1, 1
    ]

    def get_utf8_count(self, ch):
        return self.utf8_skip_data[ch]

    def displayable_key_to_str(self, ch):
        return chr(ch)

    def is_displayable_key(self, ch):
        return 32 <= ch <= 126

    def is_ctrl_masked_key(self, ch):
        return 0 <= ch <= 31 and ch != KEY_ESCAPE

    def ctrl_masked_key_to_str(self, ch):
        s = "C-"

        if ch == 0:
            s += "SPC"
        elif 0 < ch <= 27:
            s += chr(ch + 96)  # ord('a') => 97, CTRL_A => 1
        else:
            s += "UNKNOWN ({0:d} :: 0x{0:x})".format(ch)

        return s

########NEW FILE########
__FILENAME__ = lazyarray
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 mooz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

# ============================================================ #
# Lazy Array
# ============================================================ #

class LazyArray(object):
    """
    Wraps an iterable object and provides lazy array functionality,
    namely, lazy index access and iteration. Lazily got iteration
    results are cached and reused to provide consistent view
    for users.
    """

    def __init__(self, iterable_source):
        self.source = iterable_source
        self.got_elements = []
        self.read_count = 0

    def __len__(self):
        return len(self.got_elements)

    def __iter__(self):
        # yield cached result
        for elem in self.got_elements:
            yield elem
        # get results from iterable object
        for elem in self.source:
            self.read_count = self.read_count + 1
            self.got_elements.append(elem)
            yield elem

    def __getitem__(self, idx):
        # if the element corresponds to the specified index is not
        # available, pull results from iterable object
        if idx < 0:
            self.pull_all()
        else:
            from itertools import islice
            for elem in islice(self, 0, idx + 1):
                pass

        return self.got_elements[idx]

    def pull_all(self):
        for elem in self:
            pass

    def has_nth_value(self, nth):
        try:
            self[nth]
            return True
        except IndexError:
            return False

if __name__ == "__main__":
    def getnumbers(n):
        for x in xrange(1, n):
            print("yield " + str(x))
            yield x
    larray = LazyArray(getnumbers(20))
    print("larray[7]: %d" % larray[7])
    for idx, x in enumerate(larray):
        print("larray[%d]: %d" % (idx, x))
    print("larray[10]: %d" % larray[10])

    larray2 = LazyArray(getnumbers(20))
    print("larray2[-1]: %d" % larray2[-1])

########NEW FILE########
__FILENAME__ = markup
# -*- coding: utf-8 -*-
# Copyright (C) 2011 mooz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

class MarkupParser(object):
    def __init__(self):
        pass

    def parse(self, s):
        self.init_status(s)
        self.parse_string()
        self.consume_token()

        return self.tokens

    def init_status(self, s):
        self.s = s
        self.pos = 0
        self.tokens = []
        self.tags = []
        self.buffer = []

    def consume_token(self):
        if self.buffer:
            self.tokens.append(("".join(self.buffer), list(self.tags)))
            self.buffer[:] = []

    def get_next_char(self):
        try:
            p = self.pos
            self.pos += 1
            return self.s[p]
        except IndexError:
            return None

    def get_next_chars(self):
        s_len = len(self.s)
        while self.pos < s_len:
            yield self.get_next_char()

    def peek_next_char(self):
        try:
            return self.s[self.pos]
        except IndexError:
            return None

    def parse_string(self):
        escaped = False

        for c in self.get_next_chars():
            if escaped:
                escaped = False
                self.buffer.append(c)
            elif c == '\\':
                    escaped = True
            elif c == '<':
                self.consume_token()

                if self.peek_next_char() == '/':
                    # end certain tag
                    self.get_next_char()
                    tag = self.parse_tag()

                    try:
                        self.tags.remove(tag)
                    except:
                        raise Exception("corresponding beginning tag for </{0}> is not found".format(tag))
                else:
                    # begin new tag
                    tag = self.parse_tag()
                    self.tags.insert(0, tag) # front
            else:
                self.buffer.append(c)

    def parse_tag(self):
        buf = []
        escaped = False

        for c in self.get_next_chars():
            if escaped:
                buf.append(c)
            elif c == '\\':
                escaped = True
            elif c == '>':
                return "".join(buf)
            else:
                buf.append(c)

        raise Exception("Unclosed tag " + "".join(buf))

if __name__ == "__main__":
    import pprint, sys, types

    parser = MarkupParser()

    def color(str, color = 31):
        colors = {
            "black"      : 30,
            "red"        : 31,
            "green"      : 32,
            "yellow"     : 33,
            "blue"       : 34,
            "magenta"    : 35,
            "cyan"       : 36,
            "white"      : 37,
            "on_black"   : 40,
            "on_red"     : 41,
            "on_green"   : 42,
            "on_yellow"  : 43,
            "on_blue"    : 44,
            "on_magenta" : 45,
            "on_cyan"    : 46,
            "on_white"   : 47,
        }

        if color.__class__ == types.StringType:
            try:
                color = colors[color]
            except:
                color = colors["white"]

        if sys.stdout.isatty():
            return "\033[1;{0}m{1}\033[0m".format(color, str)
        else:
            return str

    tests = (
        "hello",
        "hello <red>red</red> normal",
        "hello <on_green>with background green <bold>this is bold <red>and red</red></bold></on_green> then, normal",
        "baaaaa<green>a<blue>aa</green>a</blue>aaaaaaa", # unmatch
        "baaaaa<green>a<blue>aa</blue>a</green>aaaaaaa",
        "hello \\<red>red\\</red> normal",  # escape
        u"マルチ<magenta>バイト<blue>文字</blue>の</magenta>テスト", # multibyte
    )

    for test in tests:
        try:
            print("----------------------------------------------------------")
            print("Testing [%s]" % color(test, "cyan"))
            print(color("pass: " + pprint.pformat(parser.parse(test)), "green"))
        except Exception as e:
            print(color("fail: " + str(e), "red"))

########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 mooz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import types
from percol import display, debug

class SelectorModel(object):
    def __init__(self,
                 percol, collection, finder,
                 query = None, caret = None, index = None):
        self.original_finder_class = finder
        self.percol = percol
        self.finder = finder(collection)
        self.setup_results(query)
        self.setup_caret(caret)
        self.setup_index(index)

    # ============================================================ #
    # Pager attributes
    # ============================================================ #

    @property
    def absolute_index(self):
        return self.index

    @property
    def results_count(self):
        return len(self.results)

    # ============================================================ #
    # Initializer
    # ============================================================ #

    def setup_results(self, query):
        self.query   = self.old_query = query or u""
        self.results = self.finder.get_results(self.query)
        self.marks   = {}

    def setup_caret(self, caret):
        if isinstance(caret, types.StringType) or isinstance(caret, types.UnicodeType):
            try:
                caret = int(caret)
            except ValueError:
                caret = None
        if caret is None or caret < 0 or caret > display.screen_len(self.query):
            caret = display.screen_len(self.query)
        self.caret = caret

    def setup_index(self, index):
        self.index = 0
        if index is None or index == "first":
            self.select_top()
        elif index == "last":
            self.select_bottom()
        else:
            self.select_index(int(index))

    # ============================================================ #
    # Result handling
    # ============================================================ #

    search_forced = False
    def force_search(self):
        self.search_forced = True

    def should_search_again(self):
        return self.query != self.old_query or self.search_forced

    old_query = u""
    def do_search(self, query):
        with self.percol.global_lock:
            self.index = 0
            self.results = self.finder.get_results(query)
            self.marks   = {}
            # search finished
            self.search_forced = False
            self.old_query = query

    def get_result(self, index):
        try:
            return self.results[index][0]
        except IndexError:
            return None

    def get_selected_result(self):
        return self.get_result(self.index)

    def get_selected_results_with_index(self):
        results = self.get_marked_results_with_index()
        if not results:
            try:
                index = self.index
                result = self.results[index] # EAFP (results may be a zero-length list)
                results.append((result[0], index, result[2]))
            except Exception as e:
                debug.log("get_selected_results_with_index", e)
        return results

    # ------------------------------------------------------------ #
    #  Selections
    # ------------------------------------------------------------ #

    def select_index(self, idx):
        try:
            # For lazy results, correct "results_count" by getting
            # items (if available)
            self.results[idx]
            self.index = idx
        except:
            pass
        if self.results_count > 0:
            self.index = idx % self.results_count

    def select_top(self):
        self.select_index(0)

    def select_bottom(self):
        self.select_index(-1)

    # ------------------------------------------------------------ #
    # Mark
    # ------------------------------------------------------------ #

    def get_marked_results_with_index(self):
        if self.marks:
            return [(self.results[index][0], index, self.results[index][2])
                    for index in self.marks if self.get_is_marked(index)]
        else:
            return []

    def set_is_marked(self, marked, index = None):
        if index is None:
            index = self.index          # use current index
        self.marks[index] = marked

    def get_is_marked(self, index = None):
        if index is None:
            index = self.index          # use current index
        return self.marks.get(index, False)

    # ------------------------------------------------------------ #
    # Caret position
    # ------------------------------------------------------------ #

    def set_caret(self, caret):
        q_len = len(self.query)
        self.caret = max(min(caret, q_len), 0)

    # ------------------------------------------------------------ #
    # Text
    # ------------------------------------------------------------ #

    def append_char_to_query(self, ch):
        self.query += chr(ch).decode(self.percol.encoding)
        self.forward_char()

    def insert_char(self, ch):
        q = self.query
        c = self.caret
        self.query = q[:c] + chr(ch).decode(self.percol.encoding) + q[c:]
        self.set_caret(c + 1)

    def insert_string(self, string):
        caret_pos  = self.caret + len(string)
        self.query = self.query[:self.caret] + string + self.query[self.caret:]
        self.caret = caret_pos

    # ------------------------------------------------------------ #
    # Finder
    # ------------------------------------------------------------ #

    def remake_finder(self, new_finder_class):
        self.finder = self.finder.clone_as(new_finder_class)

########NEW FILE########
__FILENAME__ = tty
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 mooz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import sys
import os

def get_ttyname():
    for f in sys.stdin, sys.stdout, sys.stderr:
        if f.isatty():
            return os.ttyname(f.fileno())
    return None

def reconnect_descriptors(tty):
    target = {}

    stdios = (("stdin", "r"), ("stdout", "w"), ("stderr", "w"))

    tty_desc = tty.fileno()

    for name, mode in stdios:
        f = getattr(sys, name)

        if f.isatty():
            # f is TTY
            target[name] = f
        else:
            # f is other process's output / input or a file

            # save descriptor connected with other process
            std_desc = f.fileno()
            other_desc = os.dup(std_desc)

            # set std descriptor. std_desc become invalid.
            os.dup2(tty_desc, std_desc)

            # set file object connected to other_desc to corresponding one of sys.{stdin, stdout, stderr}
            try:
                target[name] = os.fdopen(other_desc, mode)
                setattr(sys, name, target[name])
            except OSError:
                # maybe mode specification is invalid or /dev/null is specified (?)
                target[name] = None
                print("Failed to open {0}".format(other_desc))

    return target

########NEW FILE########
__FILENAME__ = view
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 mooz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import re
import curses
import types
import math

from itertools import islice

from percol import display, debug

class SelectorView(object):
    def __init__(self, percol = None):
        self.percol  = percol
        self.screen  = percol.screen
        self.display = percol.display

    CANDIDATES_LINE_BASIC    = ("on_default", "default")
    CANDIDATES_LINE_SELECTED = ("underline", "on_magenta", "white")
    CANDIDATES_LINE_MARKED   = ("bold", "on_cyan", "black")
    CANDIDATES_LINE_QUERY    = ("yellow", "bold")

    @property
    def RESULTS_DISPLAY_MAX(self):
        return self.display.Y_END - self.display.Y_BEGIN

    @property
    def model(self):
        return self.percol.model

    @property
    def page_number(self):
        return int(self.model.index / self.RESULTS_DISPLAY_MAX) + 1

    @property
    def total_page_number(self):
        return max(int(math.ceil(1.0 * self.model.results_count / self.RESULTS_DISPLAY_MAX)), 1)

    @property
    def absolute_page_head(self):
        return self.RESULTS_DISPLAY_MAX * int(self.model.index / self.RESULTS_DISPLAY_MAX)

    @property
    def absolute_page_tail(self):
        return self.absolute_page_head + self.RESULTS_DISPLAY_MAX

    def refresh_display(self):
        with self.percol.global_lock:
            self.display.erase()
            self.display_results()
            self.display_prompt()
            self.display.refresh()

    def display_line(self, y, x, s, style = None):
        if style is None:
            style = self.CANDIDATES_LINE_BASIC
        self.display.add_aligned_string(s, y_offset = y, x_offset = x, style = style, fill = True)

    def display_result(self, y, result, is_current = False, is_marked = False):
        line, find_info, abs_idx = result

        if is_current:
            line_style = self.CANDIDATES_LINE_SELECTED
        elif is_marked:
            line_style = self.CANDIDATES_LINE_MARKED
        else:
            line_style = self.CANDIDATES_LINE_BASIC

        keyword_style = self.CANDIDATES_LINE_QUERY + line_style

        self.display_line(y, 0, line, style = line_style)

        if find_info is None:
            return
        for (subq, match_info) in find_info:
            for x_offset, subq_len in match_info:
                try:
                    x_offset_real = display.screen_len(line, beg = 0, end = x_offset)
                    self.display.add_string(line[x_offset:x_offset + subq_len],
                                            pos_y = y,
                                            pos_x = x_offset_real,
                                            style = keyword_style)
                except curses.error as e:
                    debug.log("addnstr", str(e) + " ({0})".format(y))

    def display_results(self):
        result_vertical_pos = self.RESULTS_OFFSET_V
        result_pos_direction = 1 if self.results_top_down else -1

        results_in_page = islice(enumerate(self.model.results), self.absolute_page_head, self.absolute_page_tail)

        for cand_nth, result in results_in_page:
            try:
                self.display_result(result_vertical_pos, result,
                                    is_current = cand_nth == self.model.index,
                                    is_marked = self.model.get_is_marked(cand_nth))
            except curses.error as e:
                debug.log("display_results", str(e))
            result_vertical_pos += result_pos_direction

    results_top_down = True

    @property
    def RESULTS_OFFSET_V(self):
        if self.results_top_down:
            # top -> bottom
            if self.prompt_on_top:
                return self.display.Y_BEGIN + 1
            else:
                return self.display.Y_BEGIN
        else:
            # bottom -> top
            if self.prompt_on_top:
                return self.display.Y_END
            else:
                return self.display.Y_END - 1

    # ============================================================ #
    # Prompt
    # ============================================================ #

    prompt_on_top = True

    @property
    def PROMPT_OFFSET_V(self):
        if self.prompt_on_top:
            return self.display.Y_BEGIN
        else:
            return self.display.Y_END

    PROMPT  = u"QUERY> %q"
    RPROMPT = u"(%i/%I) [%n/%N]"

    def do_display_prompt(self, format,
                          y_offset = 0, x_offset = 0,
                          y_align = "top", x_align = "left"):
        parsed = self.display.markup_parser.parse(format)
        offset = 0
        tokens = []

        self.last_query_position = -1

        for s, attrs in parsed:
            formatted_string = self.format_prompt_string(s, offset)
            tokens.append((formatted_string, attrs))
            offset += display.screen_len(formatted_string)

        y, x = self.display.add_aligned_string_tokens(tokens,
                                                      y_offset = y_offset,
                                                      x_offset = x_offset,
                                                      y_align = y_align,
                                                      x_align = x_align)

        # when %q is specified, record its position
        if self.last_query_position >= 0:
            self.caret_x = self.last_query_position + x
            self.caret_y = self.PROMPT_OFFSET_V

    def display_prompt(self):
        self.caret_x = -1
        self.caret_y = -1

        self.do_display_prompt(self.RPROMPT,
                               y_offset = self.PROMPT_OFFSET_V,
                               x_align = "right")

        self.do_display_prompt(self.PROMPT,
                               y_offset = self.PROMPT_OFFSET_V)

        try:
            # move caret
            if self.caret_x >= 0 and self.caret_y >= 0:
                self.screen.move(self.caret_y,
                                 self.caret_x + display.screen_len(self.model.query, 0, self.model.caret))
        except curses.error:
            pass

    def handle_format_prompt_query(self, matchobj, offset):
        # -1 is from first '%' of %([a-zA-Z%])
        self.last_query_position = matchobj.start(1) - 1 + offset
        return self.model.query

    prompt_replacees = {
        "%" : lambda self, **args: "%",
        # display query and caret
        "q" : lambda self, **args: self.handle_format_prompt_query(args["matchobj"], args["offset"]),
        # display query but does not display caret
        "Q" : lambda self, **args: self.model.query,
        "n" : lambda self, **args: self.page_number,
        "N" : lambda self, **args: self.total_page_number,
        "i" : lambda self, **args: self.model.index + (1 if self.model.results_count > 0 else 0),
        "I" : lambda self, **args: self.model.results_count,
        "c" : lambda self, **args: self.model.caret,
        "k" : lambda self, **args: self.percol.last_key
    }

    format_pattern = re.compile(ur'%([a-zA-Z%])')
    def format_prompt_string(self, s, offset = 0):
        def formatter(matchobj):
            al = matchobj.group(1)
            if self.prompt_replacees.has_key(al):
                res = self.prompt_replacees[al](self, matchobj = matchobj, offset = offset)
                return (res if res.__class__ == types.UnicodeType
                        else unicode(str(res), self.percol.encoding, 'replace'))
            else:
                return u""

        return re.sub(self.format_pattern, formatter, s)

########NEW FILE########
__FILENAME__ = check_colors
#!/usr/bin/env python

#
# Copyright (C) 2011 mooz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import curses

if __name__ == "__main__":
    screen = curses.initscr()

    try:
        curses.start_color()

        def get_fg_bg():
            for bg in xrange(0, curses.COLORS):
                for fg in xrange(0, curses.COLORS):
                    yield bg, fg

        def pair_number(fg, bg):
            return fg + bg * curses.COLORS

        def init_pairs():
            for bg, fg in get_fg_bg():
                if not (fg == bg == 0):
                    curses.init_pair(pair_number(fg, bg), fg, bg)

        def print_pairs(attrs = None, offset_y = 0):
            fmt = " ({0}:{1}) "
            fmt_len = len(fmt)

            for bg, fg in get_fg_bg():
                try:
                    color = curses.color_pair(pair_number(fg, bg))
                    if not attrs is None:
                        for attr in attrs:
                            color |= attr
                    screen.addstr(offset_y + bg, fg * fmt_len, fmt.format(fg, bg), color)
                    pass
                except curses.error:
                    pass

        def wait_input():
            screen.getch()

        init_pairs()
        print_pairs()
        print_pairs([curses.A_BOLD], offset_y = curses.COLORS + 1)
        screen.refresh()
        wait_input()
    finally:
        curses.endwin()

########NEW FILE########
