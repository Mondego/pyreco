__FILENAME__ = default
../../../ranger/colorschemes/default.py
########NEW FILE########
__FILENAME__ = jungle
../../../ranger/colorschemes/jungle.py
########NEW FILE########
__FILENAME__ = snow
../../../ranger/colorschemes/snow.py
########NEW FILE########
__FILENAME__ = commands
../../ranger/config/commands.py
########NEW FILE########
__FILENAME__ = plugin_chmod_keybindings
# Compatible with ranger 1.6.*
#
# This plugin serves as an example for adding key bindings through a plugin.
# It could replace the ten lines in the rc.conf that create the key bindings
# for the "chmod" command.

import ranger.api
old_hook_init = ranger.api.hook_init

def hook_init(fm):
    old_hook_init(fm)

    # Generate key bindings for the chmod command
    command = "map {0}{1}{2} shell -d chmod {1}{0}{2} %s"
    for mode in list('ugoa') + ['']:
        for perm in "rwxXst":
            fm.execute_console(command.format('-', mode, perm))
            fm.execute_console(command.format('+', mode, perm))

ranger.api.hook_init = hook_init

########NEW FILE########
__FILENAME__ = plugin_file_filter
# Compatible with ranger 1.6.*
#
# This plugin hides the directories "boot", "sbin", "proc" and "sys" in the
# root directory.

# Save the original filter function
import ranger.container.directory
old_accept_file = ranger.container.directory.accept_file

# Define a new one
def custom_accept_file(fname, directory, hidden_filter, name_filter):
       if hidden_filter and directory.path == '/' and fname in ('boot', 'sbin', 'proc', 'sys'):
               return False
       else:
               return old_accept_file(fname, directory, hidden_filter, name_filter)

# Overwrite the old function
import ranger.container.directory
ranger.container.directory.accept_file = custom_accept_file

########NEW FILE########
__FILENAME__ = plugin_hello_world
# Compatible with ranger 1.6.*
#
# This is a sample plugin that displays "Hello World" in ranger's console after
# it started.

# We are going to extend the hook "ranger.api.hook_ready", so first we need
# to import ranger.api:
import ranger.api

# Save the previously existing hook, because maybe another module already
# extended that hook and we don't want to lose it:
old_hook_ready = ranger.api.hook_ready

# Create a replacement for the hook that...
def hook_ready(fm):
    # ...does the desired action...
    fm.notify("Hello World")
    # ...and calls the saved hook.  If you don't care about the return value,
    # simply return the return value of the previous hook to be safe.
    return old_hook_ready(fm)

# Finally, "monkey patch" the existing hook_ready function with our replacement:
ranger.api.hook_ready = hook_ready

########NEW FILE########
__FILENAME__ = plugin_new_macro
# Compatible with ranger 1.6.*
#
# This plugin adds the new macro %date which is substituted with the current
# date in commands that allow macros.  You can test it with the command
# ":shell echo %date; read"

# Save the original macro function
import ranger.core.actions
old_get_macros = ranger.core.actions.Actions._get_macros

# Define a new macro function
import time
def get_macros_with_date(self):
       macros = old_get_macros(self)
       macros['date'] = time.strftime('%m/%d/%Y')
       return macros

# Overwrite the old one
ranger.core.actions.Actions._get_macros = get_macros_with_date

########NEW FILE########
__FILENAME__ = plugin_new_sorting_method
# Compatible with ranger 1.6.*
#
# This plugin adds the sorting algorithm called 'random'.  To enable it, type
# ":set sort=random" or create a key binding with ":map oz set sort=random"

from ranger.container.directory import Directory
from random import random
Directory.sort_dict['random'] = lambda path: random()


########NEW FILE########
__FILENAME__ = print_colors
#!/usr/bin/env python
"""
You can use this tool to display all supported colors and their color number.
It will exit after a keypress.
"""

import curses
from curses import *

@wrapper
def main(win):
    def print_all_colors(attr):
        for c in range(-1, curses.COLORS):
            try:
                init_pair(c, c, 0)
            except:
                pass
            else:
                win.addstr(str(c) + ' ', color_pair(c) | attr)
    start_color()
    try:
        use_default_colors()
    except:
        pass
    win.addstr("available colors: %d\n\n" % curses.COLORS)
    print_all_colors(0)
    win.addstr("\n\n")
    print_all_colors(A_BOLD)
    win.refresh()
    win.getch()


########NEW FILE########
__FILENAME__ = print_keys
#!/usr/bin/env python
"""
You can use this tool to find out values of keypresses
"""

from curses import *

sep = '; '

@wrapper
def main(w):
    while True:
        w.addstr(str(w.getch()) + sep)


########NEW FILE########
__FILENAME__ = commands
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

# TODO: Add an optional "!" to all commands and set a flag if it's there

import os
import ranger
import re
from collections import deque
from ranger.api import *
from ranger.core.shared import FileManagerAware
from ranger.ext.lazy_property import lazy_property

_SETTINGS_RE = re.compile(r'^\s*([^\s]+?)=(.*)$')
DELETE_WARNING = 'delete seriously? '  # COMPAT

def alias(*_): pass # COMPAT

class CommandContainer(object):
    def __init__(self):
        self.commands = {}

    def __getitem__(self, key):
        return self.commands[key]

    def alias(self, name, full_command):
        try:
            cmd = type(name, (AliasCommand, ), dict())
            cmd._based_function = name
            cmd._function_name = name
            cmd._object_name = name
            cmd._line = full_command
            self.commands[name] = cmd

        except:
            pass

    def load_commands_from_module(self, module):
        for var in vars(module).values():
            try:
                if issubclass(var, Command) and var != Command \
                        and var != FunctionCommand:
                    self.commands[var.get_name()] = var
            except TypeError:
                pass

    def load_commands_from_object(self, obj, filtr):
        for attribute_name in dir(obj):
            if attribute_name[0] == '_' or attribute_name not in filtr:
                continue
            attribute = getattr(obj, attribute_name)
            if hasattr(attribute, '__call__'):
                cmd = type(attribute_name, (FunctionCommand, ), dict())
                cmd._based_function = attribute
                cmd._function_name = attribute.__name__
                cmd._object_name = obj.__class__.__name__
                self.commands[attribute_name] = cmd

    def get_command(self, name, abbrev=True):
        if abbrev:
            lst = [cls for cmd, cls in self.commands.items() \
                    if cls.allow_abbrev and cmd.startswith(name) \
                    or cmd == name]
            if len(lst) == 0:
                raise KeyError
            if len(lst) == 1:
                return lst[0]
            if self.commands[name] in lst:
                return self.commands[name]
            raise ValueError("Ambiguous command")
        else:
            try:
                return self.commands[name]
            except KeyError:
                return None

    def command_generator(self, start):
        return (cmd + ' ' for cmd in self.commands if cmd.startswith(start))


class Command(FileManagerAware):
    """Abstract command class"""
    name = None
    allow_abbrev = True
    resolve_macros = True
    escape_macros_for_shell = False
    quantifier = None
    _shifted = 0
    _setting_line = None

    def __init__(self, line, quantifier=None):
        self.line = line
        self.args = line.split()
        self.quantifier = quantifier
        try:
            self.firstpart = line[:line.rindex(' ') + 1]
        except ValueError:
            self.firstpart = ''

    @classmethod
    def get_name(self):
        classdict = self.__mro__[0].__dict__
        if 'name' in classdict and classdict['name']:
            return self.name
        else:
            return self.__name__

    def execute(self):
        """Override this"""

    def tab(self):
        """Override this"""

    def quick(self):
        """Override this"""

    def cancel(self):
        """Override this"""

    # Easy ways to get information
    def arg(self, n):
        """Returns the nth space separated word"""
        try:
            return self.args[n]
        except IndexError:
            return ""

    def rest(self, n):
        """Returns everything from and after arg(n)"""
        got_space = True
        word_count = 0
        for i in range(len(self.line)):
            if self.line[i] == " ":
                if not got_space:
                    got_space = True
                    word_count += 1
            elif got_space:
                got_space = False
                if word_count == n + self._shifted:
                    return self.line[i:]
        return ""

    def start(self, n):
        """Returns everything until (inclusively) arg(n)"""
        return ' '.join(self.args[:n]) + " " # XXX

    def shift(self):
        del self.args[0]
        self._setting_line = None
        self._shifted += 1

    def tabinsert(self, word):
        return ''.join([self._tabinsert_left, word, self._tabinsert_right])

    def parse_setting_line(self):
        if self._setting_line is not None:
            return self._setting_line
        match = _SETTINGS_RE.match(self.rest(1))
        if match:
            self.firstpart += match.group(1) + '='
            result = [match.group(1), match.group(2), True]
        else:
            result = [self.arg(1), self.rest(2), ' ' in self.rest(1)]
        self._setting_line = result
        return result

    def parse_flags(self):
        """Finds and returns flags in the command

        >>> Command("").parse_flags()
        ('', '')
        >>> Command("foo").parse_flags()
        ('', '')
        >>> Command("shell test").parse_flags()
        ('', 'test')
        >>> Command("shell -t ls -l").parse_flags()
        ('t', 'ls -l')
        >>> Command("shell -f -- -q test").parse_flags()
        ('f', '-q test')
        >>> Command("shell -foo -bar rest of the command").parse_flags()
        ('foobar', 'rest of the command')
        """
        flags = ""
        args = self.line.split()
        rest = ""
        if len(args) > 0:
            rest = self.line[len(args[0]):].lstrip()
            for arg in args[1:]:
                if arg == "--":
                    rest = rest[2:].lstrip()
                    break
                elif len(arg) > 1 and arg[0] == "-":
                    rest = rest[len(arg):].lstrip()
                    flags += arg[1:]
                else:
                    break
        return flags, rest

    # XXX: Lazy properties? Not so smart? self.line can change after all!
    @lazy_property
    def _tabinsert_left(self):
        try:
            return self.line[:self.line[0:self.pos].rindex(' ') + 1]
        except ValueError:
            return ''

    @lazy_property
    def _tabinsert_right(self):
        return self.line[self.pos:]

    # COMPAT: this is still used in old commands.py configs
    def _tab_only_directories(self):
        from os.path import dirname, basename, expanduser, join

        cwd = self.fm.thisdir.path

        rel_dest = self.rest(1)

        # expand the tilde into the user directory
        if rel_dest.startswith('~'):
            rel_dest = expanduser(rel_dest)

        # define some shortcuts
        abs_dest = join(cwd, rel_dest)
        abs_dirname = dirname(abs_dest)
        rel_basename = basename(rel_dest)
        rel_dirname = dirname(rel_dest)

        try:
            # are we at the end of a directory?
            if rel_dest.endswith('/') or rel_dest == '':
                _, dirnames, _ = next(os.walk(abs_dest))

            # are we in the middle of the filename?
            else:
                _, dirnames, _ = next(os.walk(abs_dirname))
                dirnames = [dn for dn in dirnames \
                        if dn.startswith(rel_basename)]
        except (OSError, StopIteration):
            # os.walk found nothing
            pass
        else:
            dirnames.sort()

            # no results, return None
            if len(dirnames) == 0:
                return

            # one result. since it must be a directory, append a slash.
            if len(dirnames) == 1:
                return self.start(1) + join(rel_dirname, dirnames[0]) + '/'

            # more than one result. append no slash, so the user can
            # manually type in the slash to advance into that directory
            return (self.start(1) + join(rel_dirname, dirname)
                    for dirname in dirnames)

    def _tab_directory_content(self):
        from os.path import dirname, basename, expanduser, join

        cwd = self.fm.thisdir.path

        rel_dest = self.rest(1)

        # expand the tilde into the user directory
        if rel_dest.startswith('~'):
            rel_dest = expanduser(rel_dest)

        # define some shortcuts
        abs_dest = join(cwd, rel_dest)
        abs_dirname = dirname(abs_dest)
        rel_basename = basename(rel_dest)
        rel_dirname = dirname(rel_dest)

        try:
            directory = self.fm.get_directory(abs_dest)

            # are we at the end of a directory?
            if rel_dest.endswith('/') or rel_dest == '':
                if directory.content_loaded:
                    # Take the order from the directory object
                    names = [f.basename for f in directory.files]
                    if self.fm.thisfile.basename in names:
                        i = names.index(self.fm.thisfile.basename)
                        names = names[i:] + names[:i]
                else:
                    # Fall back to old method with "os.walk"
                    _, dirnames, filenames = next(os.walk(abs_dest))
                    names = dirnames + filenames
                    names.sort()

            # are we in the middle of the filename?
            else:
                if directory.content_loaded:
                    # Take the order from the directory object
                    names = [f.basename for f in directory.files \
                            if f.basename.startswith(rel_basename)]
                    if self.fm.thisfile.basename in names:
                        i = names.index(self.fm.thisfile.basename)
                        names = names[i:] + names[:i]
                else:
                    # Fall back to old method with "os.walk"
                    _, dirnames, filenames = next(os.walk(abs_dirname))
                    names = [name for name in (dirnames + filenames) \
                            if name.startswith(rel_basename)]
                    names.sort()
        except (OSError, StopIteration):
            # os.walk found nothing
            pass
        else:
            # no results, return None
            if len(names) == 0:
                return

            # one result. append a slash if it's a directory
            if len(names) == 1:
                path = join(rel_dirname, names[0])
                slash = '/' if os.path.isdir(path) else ''
                return self.start(1) + path + slash

            # more than one result. append no slash, so the user can
            # manually type in the slash to advance into that directory
            return (self.start(1) + join(rel_dirname, name) for name in names)

    def _tab_through_executables(self):
        from ranger.ext.get_executables import get_executables
        programs = [program for program in get_executables() if \
                program.startswith(self.rest(1))]
        if not programs:
            return
        if len(programs) == 1:
            return self.start(1) + programs[0]
        programs.sort()
        return (self.start(1) + program for program in programs)


class FunctionCommand(Command):
    _based_function = None
    _object_name = ""
    _function_name = "unknown"
    def execute(self):
        if not self._based_function:
            return
        if len(self.args) == 1:
            try:
                return self._based_function(**{'narg':self.quantifier})
            except TypeError:
                return self._based_function()

        args, keywords = list(), dict()
        for arg in self.args[1:]:
            equal_sign = arg.find("=")
            value = arg if (equal_sign is -1) else arg[equal_sign + 1:]
            try:
                value = int(value)
            except:
                if value in ('True', 'False'):
                    value = (value == 'True')
                else:
                    try:
                        value = float(value)
                    except:
                        pass

            if equal_sign == -1:
                args.append(value)
            else:
                keywords[arg[:equal_sign]] = value

        if self.quantifier is not None:
            keywords['narg'] = self.quantifier

        try:
            if self.quantifier is None:
                return self._based_function(*args, **keywords)
            else:
                try:
                    return self._based_function(*args, **keywords)
                except TypeError:
                    del keywords['narg']
                    return self._based_function(*args, **keywords)
        except TypeError:
            if ranger.arg.debug:
                raise
            else:
                self.fm.notify("Bad arguments for %s.%s: %s, %s" %
                        (self._object_name, self._function_name,
                            repr(args), repr(keywords)), bad=True)

class AliasCommand(Command):
    _based_function = None
    _object_name = ""
    _function_name = "unknown"
    _line = ""
    def execute(self):
        return self._make_cmd().execute()

    def quick(self):
        return self._make_cmd().quick()

    def tab(self):
        return self._make_cmd().tab()

    def cancel(self):
        return self._make_cmd().cancel()

    def _make_cmd(self):
        Cmd = self.fm.commands.get_command(self._line.split()[0])
        return Cmd(self._line + ' ' + self.rest(1))


if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = options
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

# THIS WHOLE FILE IS OBSOLETE AND EXISTS FOR BACKWARDS COMPATIBILITIY
import re
from re import compile as regexp
from ranger.api import *
from ranger.gui import color

########NEW FILE########
__FILENAME__ = default
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

from ranger.gui.colorscheme import ColorScheme
from ranger.gui.color import *

class Default(ColorScheme):
    progress_bar_color = blue

    def use(self, context):
        fg, bg, attr = default_colors

        if context.reset:
            return default_colors

        elif context.in_browser:
            if context.selected:
                attr = reverse
            else:
                attr = normal
            if context.empty or context.error:
                bg = red
            if context.border:
                fg = default
            if context.media:
                if context.image:
                    fg = yellow
                else:
                    fg = magenta
            if context.container:
                fg = red
            if context.directory:
                attr |= bold
                fg = blue
            elif context.executable and not \
                    any((context.media, context.container,
                        context.fifo, context.socket)):
                attr |= bold
                fg = green
            if context.socket:
                fg = magenta
                attr |= bold
            if context.fifo or context.device:
                fg = yellow
                if context.device:
                    attr |= bold
            if context.link:
                fg = context.good and cyan or magenta
            if context.tag_marker and not context.selected:
                attr |= bold
                if fg in (red, magenta):
                    fg = white
                else:
                    fg = red
            if not context.selected and (context.cut or context.copied):
                fg = black
                attr |= bold
            if context.main_column:
                if context.selected:
                    attr |= bold
                if context.marked:
                    attr |= bold
                    fg = yellow
            if context.badinfo:
                if attr & reverse:
                    bg = magenta
                else:
                    fg = magenta

        elif context.in_titlebar:
            attr |= bold
            if context.hostname:
                fg = context.bad and red or green
            elif context.directory:
                fg = blue
            elif context.tab:
                if context.good:
                    bg = green
            elif context.link:
                fg = cyan

        elif context.in_statusbar:
            if context.permissions:
                if context.good:
                    fg = cyan
                elif context.bad:
                    fg = magenta
            if context.marked:
                attr |= bold | reverse
                fg = yellow
            if context.message:
                if context.bad:
                    attr |= bold
                    fg = red
            if context.loaded:
                bg = self.progress_bar_color
            if context.vcsinfo:
                fg = blue
                attr &= ~bold
            if context.vcscommit:
                fg = yellow
                attr &= ~bold


        if context.text:
            if context.highlight:
                attr |= reverse

        if context.in_taskview:
            if context.title:
                fg = blue

            if context.selected:
                attr |= reverse

            if context.loaded:
                if context.selected:
                    fg = self.progress_bar_color
                else:
                    bg = self.progress_bar_color


        if context.vcsfile and not context.selected:
            attr &= ~bold
            if context.vcsconflict:
                fg = magenta
            elif context.vcschanged:
                fg = red
            elif context.vcsunknown:
                fg = red
            elif context.vcsstaged:
                fg = green
            elif context.vcssync:
                fg = green
            elif context.vcsignored:
                fg = default

        elif context.vcsremote and not context.selected:
            attr &= ~bold
            if context.vcssync:
                fg = green
            elif context.vcsbehind:
                fg = red
            elif context.vcsahead:
                fg = blue
            elif context.vcsdiverged:
                fg = magenta
            elif context.vcsunknown:
                fg = red

        return fg, bg, attr

########NEW FILE########
__FILENAME__ = jungle
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

from ranger.gui.color import *
from ranger.colorschemes.default import Default

class Scheme(Default):
    progress_bar_color = green
    def use(self, context):
        fg, bg, attr = Default.use(self, context)

        if context.directory and not context.marked and not context.link:
            fg = green

        if context.in_titlebar and context.hostname:
            fg = red if context.bad else blue

        return fg, bg, attr

########NEW FILE########
__FILENAME__ = snow
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

from ranger.gui.colorscheme import ColorScheme
from ranger.gui.color import *

class Snow(ColorScheme):
    def use(self, context):
        fg, bg, attr = default_colors

        if context.reset:
            pass

        elif context.in_browser:
            if context.selected:
                attr = reverse
            if context.directory:
                attr |= bold

        elif context.highlight:
            attr |= reverse

        elif context.in_titlebar and context.tab and context.good:
            attr |= reverse

        elif context.in_statusbar:
            if context.loaded:
                attr |= reverse
            if context.marked:
                attr |= reverse

        elif context.in_taskview:
            if context.selected:
                attr |= bold
            if context.loaded:
                attr |= reverse

        return fg, bg, attr

########NEW FILE########
__FILENAME__ = commands
# -*- coding: utf-8 -*-
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This configuration file is licensed under the same terms as ranger.
# ===================================================================
# This file contains ranger's commands.
# It's all in python; lines beginning with # are comments.
#
# Note that additional commands are automatically generated from the methods
# of the class ranger.core.actions.Actions.
#
# You can customize commands in the file ~/.config/ranger/commands.py.
# It has the same syntax as this file.  In fact, you can just copy this
# file there with `ranger --copy-config=commands' and make your modifications.
# But make sure you update your configs when you update ranger.
#
# ===================================================================
# Every class defined here which is a subclass of `Command' will be used as a
# command in ranger.  Several methods are defined to interface with ranger:
#   execute(): called when the command is executed.
#   cancel():  called when closing the console.
#   tab():     called when <TAB> is pressed.
#   quick():   called after each keypress.
#
# The return values for tab() can be either:
#   None: There is no tab completion
#   A string: Change the console to this string
#   A list/tuple/generator: cycle through every item in it
#
# The return value for quick() can be:
#   False: Nothing happens
#   True: Execute the command afterwards
#
# The return value for execute() and cancel() doesn't matter.
#
# ===================================================================
# Commands have certain attributes and methods that facilitate parsing of
# the arguments:
#
# self.line: The whole line that was written in the console.
# self.args: A list of all (space-separated) arguments to the command.
# self.quantifier: If this command was mapped to the key "X" and
#      the user pressed 6X, self.quantifier will be 6.
# self.arg(n): The n-th argument, or an empty string if it doesn't exist.
# self.rest(n): The n-th argument plus everything that followed.  For example,
#      if the command was "search foo bar a b c", rest(2) will be "bar a b c"
# self.start(n): Anything before the n-th argument.  For example, if the
#      command was "search foo bar a b c", start(2) will be "search foo"
#
# ===================================================================
# And this is a little reference for common ranger functions and objects:
#
# self.fm: A reference to the "fm" object which contains most information
#      about ranger.
# self.fm.notify(string): Print the given string on the screen.
# self.fm.notify(string, bad=True): Print the given string in RED.
# self.fm.reload_cwd(): Reload the current working directory.
# self.fm.thisdir: The current working directory. (A File object.)
# self.fm.thisfile: The current file. (A File object too.)
# self.fm.thistab.get_selection(): A list of all selected files.
# self.fm.execute_console(string): Execute the string as a ranger command.
# self.fm.open_console(string): Open the console with the given string
#      already typed in for you.
# self.fm.move(direction): Moves the cursor in the given direction, which
#      can be something like down=3, up=5, right=1, left=1, to=6, ...
#
# File objects (for example self.fm.thisfile) have these useful attributes and
# methods:
#
# cf.path: The path to the file.
# cf.basename: The base name only.
# cf.load_content(): Force a loading of the directories content (which
#      obviously works with directories only)
# cf.is_directory: True/False depending on whether it's a directory.
#
# For advanced commands it is unavoidable to dive a bit into the source code
# of ranger.
# ===================================================================

from ranger.api.commands import *

class alias(Command):
    """:alias <newcommand> <oldcommand>

    Copies the oldcommand as newcommand.
    """

    context = 'browser'
    resolve_macros = False

    def execute(self):
        if not self.arg(1) or not self.arg(2):
            self.fm.notify('Syntax: alias <newcommand> <oldcommand>', bad=True)
        else:
            self.fm.commands.alias(self.arg(1), self.rest(2))

class cd(Command):
    """:cd [-r] <dirname>

    The cd command changes the directory.
    The command 'cd -' is equivalent to typing ``.
    Using the option "-r" will get you to the real path.
    """

    def execute(self):
        import os.path
        if self.arg(1) == '-r':
            self.shift()
            destination = os.path.realpath(self.rest(1))
            if os.path.isfile(destination):
                destination = os.path.dirname(destination)
        else:
            destination = self.rest(1)

        if not destination:
            destination = '~'

        if destination == '-':
            self.fm.enter_bookmark('`')
        else:
            self.fm.cd(destination)

    def tab(self):
        import os
        from os.path import dirname, basename, expanduser, join

        cwd = self.fm.thisdir.path
        rel_dest = self.rest(1)

        bookmarks = [v.path for v in self.fm.bookmarks.dct.values()
                if rel_dest in v.path ]

        # expand the tilde into the user directory
        if rel_dest.startswith('~'):
            rel_dest = expanduser(rel_dest)

        # define some shortcuts
        abs_dest = join(cwd, rel_dest)
        abs_dirname = dirname(abs_dest)
        rel_basename = basename(rel_dest)
        rel_dirname = dirname(rel_dest)

        try:
            # are we at the end of a directory?
            if rel_dest.endswith('/') or rel_dest == '':
                _, dirnames, _ = next(os.walk(abs_dest))

            # are we in the middle of the filename?
            else:
                _, dirnames, _ = next(os.walk(abs_dirname))
                dirnames = [dn for dn in dirnames \
                        if dn.startswith(rel_basename)]
        except (OSError, StopIteration):
            # os.walk found nothing
            pass
        else:
            dirnames.sort()
            if self.fm.settings.cd_bookmarks:
                dirnames = bookmarks + dirnames

            # no results, return None
            if len(dirnames) == 0:
                return

            # one result. since it must be a directory, append a slash.
            if len(dirnames) == 1:
                return self.start(1) + join(rel_dirname, dirnames[0]) + '/'

            # more than one result. append no slash, so the user can
            # manually type in the slash to advance into that directory
            return (self.start(1) + join(rel_dirname, dirname) for dirname in dirnames)


class chain(Command):
    """:chain <command1>; <command2>; ...

    Calls multiple commands at once, separated by semicolons.
    """
    def execute(self):
        for command in self.rest(1).split(";"):
            self.fm.execute_console(command)


class shell(Command):
    escape_macros_for_shell = True

    def execute(self):
        if self.arg(1) and self.arg(1)[0] == '-':
            flags = self.arg(1)[1:]
            command = self.rest(2)
        else:
            flags = ''
            command = self.rest(1)

        if not command and 'p' in flags:
            command = 'cat %f'
        if command:
            if '%' in command:
                command = self.fm.substitute_macros(command, escape=True)
            self.fm.execute_command(command, flags=flags)

    def tab(self):
        from ranger.ext.get_executables import get_executables
        if self.arg(1) and self.arg(1)[0] == '-':
            command = self.rest(2)
        else:
            command = self.rest(1)
        start = self.line[0:len(self.line) - len(command)]

        try:
            position_of_last_space = command.rindex(" ")
        except ValueError:
            return (start + program + ' ' for program \
                    in get_executables() if program.startswith(command))
        if position_of_last_space == len(command) - 1:
            selection = self.fm.thistab.get_selection()
            if len(selection) == 1:
                return self.line + selection[0].shell_escaped_basename + ' '
            else:
                return self.line + '%s '
        else:
            before_word, start_of_word = self.line.rsplit(' ', 1)
            return (before_word + ' ' + file.shell_escaped_basename \
                    for file in self.fm.thisdir.files \
                    if file.shell_escaped_basename.startswith(start_of_word))

class open_with(Command):
    def execute(self):
        app, flags, mode = self._get_app_flags_mode(self.rest(1))
        self.fm.execute_file(
                files = [f for f in self.fm.thistab.get_selection()],
                app = app,
                flags = flags,
                mode = mode)

    def tab(self):
        return self._tab_through_executables()

    def _get_app_flags_mode(self, string):
        """Extracts the application, flags and mode from a string.

        examples:
        "mplayer f 1" => ("mplayer", "f", 1)
        "aunpack 4" => ("aunpack", "", 4)
        "p" => ("", "p", 0)
        "" => None
        """

        app = ''
        flags = ''
        mode = 0
        split = string.split()

        if len(split) == 0:
            pass

        elif len(split) == 1:
            part = split[0]
            if self._is_app(part):
                app = part
            elif self._is_flags(part):
                flags = part
            elif self._is_mode(part):
                mode = part

        elif len(split) == 2:
            part0 = split[0]
            part1 = split[1]

            if self._is_app(part0):
                app = part0
                if self._is_flags(part1):
                    flags = part1
                elif self._is_mode(part1):
                    mode = part1
            elif self._is_flags(part0):
                flags = part0
                if self._is_mode(part1):
                    mode = part1
            elif self._is_mode(part0):
                mode = part0
                if self._is_flags(part1):
                    flags = part1

        elif len(split) >= 3:
            part0 = split[0]
            part1 = split[1]
            part2 = split[2]

            if self._is_app(part0):
                app = part0
                if self._is_flags(part1):
                    flags = part1
                    if self._is_mode(part2):
                        mode = part2
                elif self._is_mode(part1):
                    mode = part1
                    if self._is_flags(part2):
                        flags = part2
            elif self._is_flags(part0):
                flags = part0
                if self._is_mode(part1):
                    mode = part1
            elif self._is_mode(part0):
                mode = part0
                if self._is_flags(part1):
                    flags = part1

        return app, flags, int(mode)

    def _is_app(self, arg):
        return not self._is_flags(arg) and not arg.isdigit()

    def _is_flags(self, arg):
        from ranger.core.runner import ALLOWED_FLAGS
        return all(x in ALLOWED_FLAGS for x in arg)

    def _is_mode(self, arg):
        return all(x in '0123456789' for x in arg)


class set_(Command):
    """:set <option name>=<python expression>

    Gives an option a new value.
    """
    name = 'set'  # don't override the builtin set class
    def execute(self):
        name = self.arg(1)
        name, value, _ = self.parse_setting_line()
        self.fm.set_option_from_string(name, value)

    def tab(self):
        name, value, name_done = self.parse_setting_line()
        settings = self.fm.settings
        if not name:
            return sorted(self.firstpart + setting for setting in settings)
        if not value and not name_done:
            return (self.firstpart + setting for setting in settings \
                    if setting.startswith(name))
        if not value:
            return self.firstpart + str(settings[name])
        if bool in settings.types_of(name):
            if 'true'.startswith(value.lower()):
                return self.firstpart + 'True'
            if 'false'.startswith(value.lower()):
                return self.firstpart + 'False'


class setlocal(set_):
    """:setlocal path=<python string> <option name>=<python expression>

    Gives an option a new value.
    """
    PATH_RE = re.compile(r'^\s*path="?(.*?)"?\s*$')
    def execute(self):
        import os.path
        match = self.PATH_RE.match(self.arg(1))
        if match:
            path = os.path.normpath(os.path.expanduser(match.group(1)))
            self.shift()
        elif self.fm.thisdir:
            path = self.fm.thisdir.path
        else:
            path = None

        if path:
            name = self.arg(1)
            name, value, _ = self.parse_setting_line()
            self.fm.set_option_from_string(name, value, localpath=path)


class setintag(setlocal):
    """:setintag <tag or tags> <option name>=<option value>

    Sets an option for directories that are tagged with a specific tag.
    """
    def execute(self):
        tags = self.arg(1)
        self.shift()
        name, value, _ = self.parse_setting_line()
        self.fm.set_option_from_string(name, value, tags=tags)


class quit(Command):
    """:quit

    Closes the current tab.  If there is only one tab, quit the program.
    """

    def execute(self):
        if len(self.fm.tabs) <= 1:
            self.fm.exit()
        self.fm.tab_close()


class quitall(Command):
    """:quitall

    Quits the program immediately.
    """

    def execute(self):
        self.fm.exit()


class quit_bang(quitall):
    """:quit!

    Quits the program immediately.
    """
    name = 'quit!'
    allow_abbrev = False


class terminal(Command):
    """:terminal

    Spawns an "x-terminal-emulator" starting in the current directory.
    """
    def execute(self):
        import os
        from ranger.ext.get_executables import get_executables
        command = os.environ.get('TERMCMD', os.environ.get('TERM'))
        if command not in get_executables():
            command = 'x-terminal-emulator'
        if command not in get_executables():
            command = 'xterm'
        self.fm.run(command, flags='f')


class delete(Command):
    """:delete

    Tries to delete the selection.

    "Selection" is defined as all the "marked files" (by default, you
    can mark files with space or v). If there are no marked files,
    use the "current file" (where the cursor is)

    When attempting to delete non-empty directories or multiple
    marked files, it will require a confirmation.
    """

    allow_abbrev = False

    def execute(self):
        import os
        if self.rest(1):
            self.fm.notify("Error: delete takes no arguments! It deletes "
                    "the selected file(s).", bad=True)
            return

        cwd = self.fm.thisdir
        cf = self.fm.thisfile
        if not cwd or not cf:
            self.fm.notify("Error: no file selected for deletion!", bad=True)
            return

        confirm = self.fm.settings.confirm_on_delete
        many_files = (cwd.marked_items or (cf.is_directory and not cf.is_link \
                and len(os.listdir(cf.path)) > 0))

        if confirm != 'never' and (confirm != 'multiple' or many_files):
            self.fm.ui.console.ask("Confirm deletion of: %s (y/N)" %
                ', '.join(f.basename for f in self.fm.thistab.get_selection()),
                self._question_callback, ('n', 'N', 'y', 'Y'))
        else:
            # no need for a confirmation, just delete
            self.fm.delete()

    def _question_callback(self, answer):
        if answer == 'y' or answer == 'Y':
            self.fm.delete()


class mark_tag(Command):
    """:mark_tag [<tags>]

    Mark all tags that are tagged with either of the given tags.
    When leaving out the tag argument, all tagged files are marked.
    """
    do_mark = True

    def execute(self):
        cwd = self.fm.thisdir
        tags = self.rest(1).replace(" ","")
        if not self.fm.tags:
            return
        for fileobj in cwd.files:
            try:
                tag = self.fm.tags.tags[fileobj.realpath]
            except KeyError:
                continue
            if not tags or tag in tags:
                cwd.mark_item(fileobj, val=self.do_mark)
        self.fm.ui.status.need_redraw = True
        self.fm.ui.need_redraw = True


class console(Command):
    """:console <command>

    Open the console with the given command.
    """
    def execute(self):
        position = None
        if self.arg(1)[0:2] == '-p':
            try:
                position = int(self.arg(1)[2:])
                self.shift()
            except:
                pass
        self.fm.open_console(self.rest(1), position=position)


class load_copy_buffer(Command):
    """:load_copy_buffer

    Load the copy buffer from confdir/copy_buffer
    """
    copy_buffer_filename = 'copy_buffer'
    def execute(self):
        from ranger.container.file import File
        from os.path import exists
        try:
            fname = self.fm.confpath(self.copy_buffer_filename)
            f = open(fname, 'r')
        except:
            return self.fm.notify("Cannot open %s" % \
                    (fname or self.copy_buffer_filename), bad=True)
        self.fm.copy_buffer = set(File(g) \
            for g in f.read().split("\n") if exists(g))
        f.close()
        self.fm.ui.redraw_main_column()


class save_copy_buffer(Command):
    """:save_copy_buffer

    Save the copy buffer to confdir/copy_buffer
    """
    copy_buffer_filename = 'copy_buffer'
    def execute(self):
        fname = None
        try:
            fname = self.fm.confpath(self.copy_buffer_filename)
            f = open(fname, 'w')
        except:
            return self.fm.notify("Cannot open %s" % \
                    (fname or self.copy_buffer_filename), bad=True)
        f.write("\n".join(f.path for f in self.fm.copy_buffer))
        f.close()


class unmark_tag(mark_tag):
    """:unmark_tag [<tags>]

    Unmark all tags that are tagged with either of the given tags.
    When leaving out the tag argument, all tagged files are unmarked.
    """
    do_mark = False


class mkdir(Command):
    """:mkdir <dirname>

    Creates a directory with the name <dirname>.
    """

    def execute(self):
        from os.path import join, expanduser, lexists
        from os import mkdir

        dirname = join(self.fm.thisdir.path, expanduser(self.rest(1)))
        if not lexists(dirname):
            mkdir(dirname)
        else:
            self.fm.notify("file/directory exists!", bad=True)

    def tab(self):
        return self._tab_directory_content()


class touch(Command):
    """:touch <fname>

    Creates a file with the name <fname>.
    """

    def execute(self):
        from os.path import join, expanduser, lexists

        fname = join(self.fm.thisdir.path, expanduser(self.rest(1)))
        if not lexists(fname):
            open(fname, 'a').close()
        else:
            self.fm.notify("file/directory exists!", bad=True)

    def tab(self):
        return self._tab_directory_content()


class edit(Command):
    """:edit <filename>

    Opens the specified file in vim
    """

    def execute(self):
        if not self.arg(1):
            self.fm.edit_file(self.fm.thisfile.path)
        else:
            self.fm.edit_file(self.rest(1))

    def tab(self):
        return self._tab_directory_content()


class eval_(Command):
    """:eval [-q] <python code>

    Evaluates the python code.
    `fm' is a reference to the FM instance.
    To display text, use the function `p'.

    Examples:
    :eval fm
    :eval len(fm.directories)
    :eval p("Hello World!")
    """
    name = 'eval'
    resolve_macros = False

    def execute(self):
        if self.arg(1) == '-q':
            code = self.rest(2)
            quiet = True
        else:
            code = self.rest(1)
            quiet = False
        import ranger
        global cmd, fm, p, quantifier
        fm = self.fm
        cmd = self.fm.execute_console
        p = fm.notify
        quantifier = self.quantifier
        try:
            try:
                result = eval(code)
            except SyntaxError:
                exec(code)
            else:
                if result and not quiet:
                    p(result)
        except Exception as err:
            p(err)


class rename(Command):
    """:rename <newname>

    Changes the name of the currently highlighted file to <newname>
    """

    def execute(self):
        from ranger.container.file import File
        from os import access

        new_name = self.rest(1)

        if not new_name:
            return self.fm.notify('Syntax: rename <newname>', bad=True)

        if new_name == self.fm.thisfile.basename:
            return

        if access(new_name, os.F_OK):
            return self.fm.notify("Can't rename: file already exists!", bad=True)

        self.fm.rename(self.fm.thisfile, new_name)
        f = File(new_name)
        self.fm.thisdir.pointed_obj = f
        self.fm.thisfile = f

    def tab(self):
        return self._tab_directory_content()


class chmod(Command):
    """:chmod <octal number>

    Sets the permissions of the selection to the octal number.

    The octal number is between 0 and 777. The digits specify the
    permissions for the user, the group and others.

    A 1 permits execution, a 2 permits writing, a 4 permits reading.
    Add those numbers to combine them. So a 7 permits everything.
    """

    def execute(self):
        mode = self.rest(1)
        if not mode:
            mode = str(self.quantifier)

        try:
            mode = int(mode, 8)
            if mode < 0 or mode > 0o777:
                raise ValueError
        except ValueError:
            self.fm.notify("Need an octal number between 0 and 777!", bad=True)
            return

        for file in self.fm.thistab.get_selection():
            try:
                os.chmod(file.path, mode)
            except Exception as ex:
                self.fm.notify(ex)

        try:
            # reloading directory.  maybe its better to reload the selected
            # files only.
            self.fm.thisdir.load_content()
        except:
            pass


class bulkrename(Command):
    """:bulkrename

    This command opens a list of selected files in an external editor.
    After you edit and save the file, it will generate a shell script
    which does bulk renaming according to the changes you did in the file.

    This shell script is opened in an editor for you to review.
    After you close it, it will be executed.
    """
    def execute(self):
        import sys
        import tempfile
        from ranger.container.file import File
        from ranger.ext.shell_escape import shell_escape as esc
        py3 = sys.version > "3"

        # Create and edit the file list
        filenames = [f.basename for f in self.fm.thistab.get_selection()]
        listfile = tempfile.NamedTemporaryFile()

        if py3:
            listfile.write("\n".join(filenames).encode("utf-8"))
        else:
            listfile.write("\n".join(filenames))
        listfile.flush()
        self.fm.execute_file([File(listfile.name)], app='editor')
        listfile.seek(0)
        if py3:
            new_filenames = listfile.read().decode("utf-8").split("\n")
        else:
            new_filenames = listfile.read().split("\n")
        listfile.close()
        if all(a == b for a, b in zip(filenames, new_filenames)):
            self.fm.notify("No renaming to be done!")
            return

        # Generate and execute script
        cmdfile = tempfile.NamedTemporaryFile()
        cmdfile.write(b"# This file will be executed when you close the editor.\n")
        cmdfile.write(b"# Please double-check everything, clear the file to abort.\n")
        if py3:
            cmdfile.write("\n".join("mv -vi -- " + esc(old) + " " + esc(new) \
                for old, new in zip(filenames, new_filenames) \
                if old != new).encode("utf-8"))
        else:
            cmdfile.write("\n".join("mv -vi -- " + esc(old) + " " + esc(new) \
                for old, new in zip(filenames, new_filenames) if old != new))
        cmdfile.flush()
        self.fm.execute_file([File(cmdfile.name)], app='editor')
        self.fm.run(['/bin/sh', cmdfile.name], flags='w')
        cmdfile.close()


class relink(Command):
    """:relink <newpath>

    Changes the linked path of the currently highlighted symlink to <newpath>
    """

    def execute(self):
        from ranger.container.file import File

        new_path = self.rest(1)
        cf = self.fm.thisfile

        if not new_path:
            return self.fm.notify('Syntax: relink <newpath>', bad=True)

        if not cf.is_link:
            return self.fm.notify('%s is not a symlink!' % cf.basename, bad=True)

        if new_path == os.readlink(cf.path):
            return

        try:
            os.remove(cf.path)
            os.symlink(new_path, cf.path)
        except OSError as err:
            self.fm.notify(err)

        self.fm.reset()
        self.fm.thisdir.pointed_obj = cf
        self.fm.thisfile = cf

    def tab(self):
        if not self.rest(1):
            return self.line+os.readlink(self.fm.thisfile.path)
        else:
            return self._tab_directory_content()


class help_(Command):
    """:help

    Display ranger's manual page.
    """
    name = 'help'
    def execute(self):
        if self.quantifier == 1:
            self.fm.dump_keybindings()
        elif self.quantifier == 2:
            self.fm.dump_commands()
        elif self.quantifier == 3:
            self.fm.dump_settings()
        else:
            self.fm.display_help()


class copymap(Command):
    """:copymap <keys> <newkeys1> [<newkeys2>...]

    Copies a "browser" keybinding from <keys> to <newkeys>
    """
    context = 'browser'

    def execute(self):
        if not self.arg(1) or not self.arg(2):
            return self.fm.notify("Not enough arguments", bad=True)

        for arg in self.args[2:]:
            self.fm.ui.keymaps.copy(self.context, self.arg(1), arg)


class copypmap(copymap):
    """:copypmap <keys> <newkeys1> [<newkeys2>...]

    Copies a "pager" keybinding from <keys> to <newkeys>
    """
    context = 'pager'


class copycmap(copymap):
    """:copycmap <keys> <newkeys1> [<newkeys2>...]

    Copies a "console" keybinding from <keys> to <newkeys>
    """
    context = 'console'


class copytmap(copymap):
    """:copycmap <keys> <newkeys1> [<newkeys2>...]

    Copies a "taskview" keybinding from <keys> to <newkeys>
    """
    context = 'taskview'


class unmap(Command):
    """:unmap <keys> [<keys2>, ...]

    Remove the given "browser" mappings
    """
    context = 'browser'

    def execute(self):
        for arg in self.args[1:]:
            self.fm.ui.keymaps.unbind(self.context, arg)


class cunmap(unmap):
    """:cunmap <keys> [<keys2>, ...]

    Remove the given "console" mappings
    """
    context = 'browser'


class punmap(unmap):
    """:punmap <keys> [<keys2>, ...]

    Remove the given "pager" mappings
    """
    context = 'pager'


class tunmap(unmap):
    """:tunmap <keys> [<keys2>, ...]

    Remove the given "taskview" mappings
    """
    context = 'taskview'


class map_(Command):
    """:map <keysequence> <command>

    Maps a command to a keysequence in the "browser" context.

    Example:
    map j move down
    map J move down 10
    """
    name = 'map'
    context = 'browser'
    resolve_macros = False

    def execute(self):
        self.fm.ui.keymaps.bind(self.context, self.arg(1), self.rest(2))


class cmap(map_):
    """:cmap <keysequence> <command>

    Maps a command to a keysequence in the "console" context.

    Example:
    cmap <ESC> console_close
    cmap <C-x> console_type test
    """
    context = 'console'


class tmap(map_):
    """:tmap <keysequence> <command>

    Maps a command to a keysequence in the "taskview" context.
    """
    context = 'taskview'


class pmap(map_):
    """:pmap <keysequence> <command>

    Maps a command to a keysequence in the "pager" context.
    """
    context = 'pager'


class scout(Command):
    """:scout [-FLAGS] <pattern>

    Swiss army knife command for searching, traveling and filtering files.
    The command takes various flags as arguments which can be used to
    influence its behaviour:

    -a = automatically open a file on unambiguous match
    -e = open the selected file when pressing enter
    -f = filter files that match the current search pattern
    -g = interpret pattern as a glob pattern
    -i = ignore the letter case of the files
    -k = keep the console open when changing a directory with the command
    -l = letter skipping; e.g. allow "rdme" to match the file "readme"
    -m = mark the matching files after pressing enter
    -M = unmark the matching files after pressing enter
    -p = permanent filter: hide non-matching files after pressing enter
    -s = smart case; like -i unless pattern contains upper case letters
    -t = apply filter and search pattern as you type
    -v = inverts the match

    Multiple flags can be combined.  For example, ":scout -gpt" would create
    a :filter-like command using globbing.
    """
    AUTO_OPEN       = 'a'
    OPEN_ON_ENTER   = 'e'
    FILTER          = 'f'
    SM_GLOB         = 'g'
    IGNORE_CASE     = 'i'
    KEEP_OPEN       = 'k'
    SM_LETTERSKIP   = 'l'
    MARK            = 'm'
    UNMARK          = 'M'
    PERM_FILTER     = 'p'
    SM_REGEX        = 'r'
    SMART_CASE      = 's'
    AS_YOU_TYPE     = 't'
    INVERT          = 'v'

    def __init__(self, *args, **kws):
        Command.__init__(self, *args, **kws)
        self._regex = None
        self.flags, self.pattern = self.parse_flags()

    def execute(self):
        thisdir = self.fm.thisdir
        flags   = self.flags
        pattern = self.pattern
        regex   = self._build_regex()
        count   = self._count(move=True)

        self.fm.thistab.last_search = regex
        self.fm.set_search_method(order="search")

        if self.MARK in flags or self.UNMARK in flags:
            value = flags.find(self.MARK) > flags.find(self.UNMARK)
            if self.FILTER in flags:
                for f in thisdir.files:
                    thisdir.mark_item(f, value)
            else:
                for f in thisdir.files:
                    if regex.search(f.basename):
                        thisdir.mark_item(f, value)

        if self.PERM_FILTER in flags:
            thisdir.filter = regex if pattern else None

        # clean up:
        self.cancel()

        if self.OPEN_ON_ENTER in flags or \
                self.AUTO_OPEN in flags and count == 1:
            if os.path.exists(pattern):
                self.fm.cd(pattern)
            else:
                self.fm.move(right=1)

        if self.KEEP_OPEN in flags and thisdir != self.fm.thisdir:
            # reopen the console:
            self.fm.open_console(self.line[0:-len(pattern)])

        if thisdir != self.fm.thisdir and pattern != "..":
            self.fm.block_input(0.5)

    def cancel(self):
        self.fm.thisdir.temporary_filter = None
        self.fm.thisdir.refilter()

    def quick(self):
        asyoutype = self.AS_YOU_TYPE in self.flags
        if self.FILTER in self.flags:
            self.fm.thisdir.temporary_filter = self._build_regex()
        if self.PERM_FILTER in self.flags and asyoutype:
            self.fm.thisdir.filter = self._build_regex()
        if self.FILTER in self.flags or self.PERM_FILTER in self.flags:
            self.fm.thisdir.refilter()
        if self._count(move=asyoutype) == 1 and self.AUTO_OPEN in self.flags:
            return True
        return False

    def tab(self):
        self._count(move=True, offset=1)

    def _build_regex(self):
        if self._regex is not None:
            return self._regex

        frmat   = "%s"
        flags   = self.flags
        pattern = self.pattern

        if pattern == ".":
            return re.compile("")

        # Handle carets at start and dollar signs at end separately
        if pattern.startswith('^'):
            pattern = pattern[1:]
            frmat = "^" + frmat
        if pattern.endswith('$'):
            pattern = pattern[:-1]
            frmat += "$"

        # Apply one of the search methods
        if self.SM_REGEX in flags:
            regex = pattern
        elif self.SM_GLOB in flags:
            regex = re.escape(pattern).replace("\\*", ".*").replace("\\?", ".")
        elif self.SM_LETTERSKIP in flags:
            regex = ".*".join(re.escape(c) for c in pattern)
        else:
            regex = re.escape(pattern)

        regex = frmat % regex

        # Invert regular expression if necessary
        if self.INVERT in flags:
            regex = "^(?:(?!%s).)*$" % regex

        # Compile Regular Expression
        options = re.LOCALE | re.UNICODE
        if self.IGNORE_CASE in flags or self.SMART_CASE in flags and \
                pattern.islower():
            options |= re.IGNORECASE
        try:
            self._regex = re.compile(regex, options)
        except:
            self._regex = re.compile("")
        return self._regex

    def _count(self, move=False, offset=0):
        count   = 0
        cwd     = self.fm.thisdir
        pattern = self.pattern

        if not pattern:
            return 0
        if pattern == '.':
            return 0
        if pattern == '..':
            return 1

        deq = deque(cwd.files)
        deq.rotate(-cwd.pointer - offset)
        i = offset
        regex = self._build_regex()
        for fsobj in deq:
            if regex.search(fsobj.basename):
                count += 1
                if move and count == 1:
                    cwd.move(to=(cwd.pointer + i) % len(cwd.files))
                    self.fm.thisfile = cwd.pointed_obj
            if count > 1:
                return count
            i += 1

        return count == 1


class grep(Command):
    """:grep <string>

    Looks for a string in all marked files or directories
    """

    def execute(self):
        if self.rest(1):
            action = ['grep', '--line-number']
            action.extend(['-e', self.rest(1), '-r'])
            action.extend(f.path for f in self.fm.thistab.get_selection())
            self.fm.execute_command(action, flags='p')


# Version control commands
# --------------------------------
class stage(Command):
    """
    :stage

    Stage selected files for the corresponding version control system
    """
    def execute(self):
        from ranger.ext.vcs import VcsError

        filelist = [f.path for f in self.fm.thistab.get_selection()]
        self.fm.thisdir.vcs_outdated = True
#        for f in self.fm.thistab.get_selection():
#            f.vcs_outdated = True

        try:
            self.fm.thisdir.vcs.add(filelist)
        except VcsError:
            self.fm.notify("Could not stage files.")

        self.fm.reload_cwd()


class unstage(Command):
    """
    :unstage

    Unstage selected files for the corresponding version control system
    """
    def execute(self):
        from ranger.ext.vcs import VcsError

        filelist = [f.path for f in self.fm.thistab.get_selection()]
        self.fm.thisdir.vcs_outdated = True
#        for f in self.fm.thistab.get_selection():
#            f.vcs_outdated = True

        try:
            self.fm.thisdir.vcs.reset(filelist)
        except VcsError:
            self.fm.notify("Could not unstage files.")

        self.fm.reload_cwd()


class diff(Command):
    """
    :diff

    Displays a diff of selected files against the last committed version
    """
    def execute(self):
        from ranger.ext.vcs import VcsError
        import tempfile

        L = self.fm.thistab.get_selection()
        if len(L) == 0: return

        filelist = [f.path for f in L]
        vcs = L[0].vcs

        diff = vcs.get_raw_diff(filelist=filelist)
        if len(diff.strip()) > 0:
            tmp = tempfile.NamedTemporaryFile()
            tmp.write(diff.encode('utf-8'))
            tmp.flush()

            pager = os.environ.get('PAGER', ranger.DEFAULT_PAGER)
            self.fm.run([pager, tmp.name])
        else:
            raise Exception("diff is empty")


class log(Command):
    """
    :log

    Displays the log of the current repo or files
    """
    def execute(self):
        from ranger.ext.vcs import VcsError
        import tempfile

        L = self.fm.thistab.get_selection()
        if len(L) == 0: return

        filelist = [f.path for f in L]
        vcs = L[0].vcs

        log = vcs.get_raw_log(filelist=filelist)
        tmp = tempfile.NamedTemporaryFile()
        tmp.write(log.encode('utf-8'))
        tmp.flush()

        pager = os.environ.get('PAGER', ranger.DEFAULT_PAGER)
        self.fm.run([pager, tmp.name])

########NEW FILE########
__FILENAME__ = bookmarks
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

import string
import re
import os
ALLOWED_KEYS = string.ascii_letters + string.digits + "`'"

class Bookmarks(object):
    """Bookmarks is a container which associates keys with bookmarks.

    A key is a string with: len(key) == 1 and key in ALLOWED_KEYS.

    A bookmark is an object with: bookmark == bookmarktype(str(instance))
    Which is true for str or FileSystemObject. This condition is required
    so bookmark-objects can be saved to and loaded from a file.

    Optionally, a bookmark.go() method is used for entering a bookmark.
    """

    last_mtime = None
    autosave = True
    load_pattern = re.compile(r"^[\d\w']:.")

    def __init__(self, bookmarkfile, bookmarktype=str, autosave=False):
        """Initializes Bookmarks.

        <bookmarkfile> specifies the path to the file where
        bookmarks are saved in.
        """
        self.autosave = autosave
        self.dct = {}
        self.path = bookmarkfile
        self.bookmarktype = bookmarktype

    def load(self):
        """Load the bookmarks from path/bookmarks"""
        try:
            new_dict = self._load_dict()
        except OSError:
            return

        self._set_dict(new_dict, original=new_dict)

    def delete(self, key):
        """Delete the bookmark with the given key"""
        if key == '`':
            key = "'"
        if key in self.dct:
            del self.dct[key]
            if self.autosave: self.save()

    def enter(self, key):
        """Enter the bookmark with the given key.

        Requires the bookmark instance to have a go() method.
        """

        try:
            return self[key].go()
        except (IndexError, KeyError, AttributeError):
            return False

    def update_if_outdated(self):
        if self.last_mtime != self._get_mtime():
            self.update()

    def remember(self, value):
        """Bookmarks <value> to the key '"""
        self["'"] = value
        if self.autosave: self.save()

    def __iter__(self):
        return iter(self.dct.items())

    def __getitem__(self, key):
        """Get the bookmark associated with the key"""
        if key == '`':
            key = "'"
        if key in self.dct:
            return self.dct[key]
        else:
            raise KeyError("Nonexistant Bookmark: `%s'!" % key)

    def __setitem__(self, key, value):
        """Bookmark <value> to the key <key>.

        key is expected to be a 1-character string and element of ALLOWED_KEYS.
        value is expected to be a filesystemobject.
        """
        if key == '`':
            key = "'"
        if key in ALLOWED_KEYS:
            self.dct[key] = value
            if self.autosave: self.save()

    def __contains__(self, key):
        """Test whether a bookmark-key is defined"""
        return key in self.dct

    def update(self):
        """Update the bookmarks from the bookmark file.

        Useful if two instances are running which define different bookmarks.
        """

        try:
            real_dict = self._load_dict()
            real_dict_copy = real_dict.copy()
        except OSError:
            return

        for key in set(self.dct.keys()) | set(real_dict.keys()):
            # set some variables
            if key in self.dct:
                current = self.dct[key]
            else:
                current = None

            if key in self.original_dict:
                original = self.original_dict[key]
            else:
                original = None

            if key in real_dict:
                real = real_dict[key]
            else:
                real = None

            # determine if there have been changes
            if current == original and current != real:
                continue   # another ranger instance has changed the bookmark

            if key not in self.dct:
                del real_dict[key]   # the user has deleted it
            else:
                real_dict[key] = current   # the user has changed it

        self._set_dict(real_dict, original=real_dict_copy)

    def save(self):
        """Save the bookmarks to the bookmarkfile.

        This is done automatically after every modification if autosave is True."""
        self.update()
        if self.path is None:
            return
        if os.access(self.path, os.W_OK):
            f = open(self.path+".new", 'w')
            for key, value in self.dct.items():
                if type(key) == str\
                        and key in ALLOWED_KEYS:
                    try:
                        f.write("{0}:{1}\n".format(str(key), str(value)))
                    except:
                        pass

            f.close()
            os.rename(self.path+".new", self.path)
        self._update_mtime()

    def _load_dict(self):
        dct = {}

        if self.path is None:
            return dct

        if not os.path.exists(self.path):
            try:
                f = open(self.path, 'w')
            except:
                raise OSError('Cannot read the given path')
            f.close()

        if os.access(self.path, os.R_OK):
            f = open(self.path, 'r')
            for line in f:
                if self.load_pattern.match(line):
                    key, value = line[0], line[2:-1]
                    if key in ALLOWED_KEYS:
                        dct[key] = self.bookmarktype(value)
            f.close()
            return dct
        else:
            raise OSError('Cannot read the given path')

    def _set_dict(self, dct, original):
        if original is None:
            original = {}

        self.dct.clear()
        self.dct.update(dct)
        self.original_dict = original
        self._update_mtime()

    def _get_mtime(self):
        if self.path is None:
            return None
        try:
            return os.stat(self.path).st_mtime
        except OSError:
            return None

    def _update_mtime(self):
        self.last_mtime = self._get_mtime()

########NEW FILE########
__FILENAME__ = directory
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

import os.path
import re

from os import stat as os_stat, lstat as os_lstat
from collections import deque
from time import time

from ranger.container.fsobject import BAD_INFO, FileSystemObject
from ranger.core.loader import Loadable
from ranger.ext.mount_path import mount_path
from ranger.container.file import File
from ranger.ext.accumulator import Accumulator
from ranger.ext.lazy_property import lazy_property
from ranger.ext.human_readable import human_readable
from ranger.container.settings import LocalSettings

def sort_by_basename(path):
    """returns path.basename (for sorting)"""
    return path.basename

def sort_by_basename_icase(path):
    """returns case-insensitive path.basename (for sorting)"""
    return path.basename_lower

def sort_by_directory(path):
    """returns 0 if path is a directory, otherwise 1 (for sorting)"""
    return 1 - path.is_directory

def sort_naturally(path):
    return path.basename_natural

def sort_naturally_icase(path):
    return path.basename_natural_lower

def accept_file(fname, directory, hidden_filter, name_filter):
    if hidden_filter and hidden_filter.search(fname):
        return False
    if name_filter and not name_filter.search(fname):
        return False
    if directory.temporary_filter and not directory.temporary_filter.search(fname):
        return False
    return True

class Directory(FileSystemObject, Accumulator, Loadable):
    is_directory = True
    enterable = False
    load_generator = None
    cycle_list = None
    loading = False
    progressbar_supported = True

    filenames = None
    files = None
    files_all = None
    filter = None
    temporary_filter = None
    marked_items = None
    scroll_begin = 0

    mount_path = '/'
    disk_usage = 0

    last_update_time = -1
    load_content_mtime = -1

    order_outdated = False
    content_outdated = False
    content_loaded = False

    has_vcschild = False

    _cumulative_size_calculated = False

    sort_dict = {
        'basename': sort_by_basename,
        'natural': sort_naturally,
        'size': lambda path: -path.size,
        'mtime': lambda path: -(path.stat and path.stat.st_mtime or 1),
        'ctime': lambda path: -(path.stat and path.stat.st_ctime or 1),
        'atime': lambda path: -(path.stat and path.stat.st_atime or 1),
        'type': lambda path: path.mimetype or '',
    }

    def __init__(self, path, **kw):
        assert not os.path.isfile(path), "No directory given!"

        Loadable.__init__(self, None, None)
        Accumulator.__init__(self)
        FileSystemObject.__init__(self, path, **kw)

        self.marked_items = list()

        for opt in ('sort_directories_first', 'sort', 'sort_reverse',
                'sort_case_insensitive'):
            self.settings.signal_bind('setopt.' + opt,
                    self.request_resort, weak=True, autosort=False)

        for opt in ('hidden_filter', 'show_hidden'):
            self.settings.signal_bind('setopt.' + opt,
                self.refilter, weak=True, autosort=False)

        self.settings = LocalSettings(path, self.settings)

        self.use()

    def request_resort(self):
        self.order_outdated = True

    def request_reload(self):
        self.content_outdated = True

    def get_list(self):
        return self.files

    def mark_item(self, item, val):
        item._mark(val)
        if val:
            if item in self.files and not item in self.marked_items:
                self.marked_items.append(item)
        else:
            while True:
                try:
                    self.marked_items.remove(item)
                except ValueError:
                    break

    def toggle_mark(self, item):
        self.mark_item(item, not item.marked)

    def toggle_all_marks(self):
        for item in self.files:
            self.toggle_mark(item)

    def mark_all(self, val):
        for item in self.files:
            self.mark_item(item, val)

        if not val:
            del self.marked_items[:]
            self._clear_marked_items()

    # XXX: Is it really necessary to have the marked items in a list?
    # Can't we just recalculate them with [f for f in self.files if f.marked]?
    def _gc_marked_items(self):
        for item in list(self.marked_items):
            if item.path not in self.filenames:
                self.marked_items.remove(item)

    def _clear_marked_items(self):
        for item in self.marked_items:
            item._mark(False)
        del self.marked_items[:]

    def get_selection(self):
        """READ ONLY"""
        self._gc_marked_items()
        if self.marked_items:
            return [item for item in self.files if item.marked]
        elif self.pointed_obj:
            return [self.pointed_obj]
        else:
            return []

    def refilter(self):
        if self.files_all is None:
            return # propably not loaded yet

        self.last_update_time = time()

        if not self.settings.show_hidden and self.settings.hidden_filter:
            hidden_filter = re.compile(self.settings.hidden_filter)
        else:
            hidden_filter = None

        self.files = [f for f in self.files_all if accept_file(
            f.basename, self, hidden_filter, self.filter)]
        self.move_to_obj(self.pointed_obj)

    # XXX: Check for possible race conditions
    def load_bit_by_bit(self):
        """An iterator that loads a part on every next() call

        Returns a generator which load a part of the directory
        in each iteration.
        """

        self.loading = True
        self.percent = 0
        self.load_if_outdated()

        try:
            if self.runnable:
                yield
                mypath = self.path

                self.mount_path = mount_path(mypath)

                filelist = os.listdir(mypath)

                if self._cumulative_size_calculated:
                    # If self.content_loaded is true, this is not the first
                    # time loading.  So I can't really be sure if the
                    # size has changed and I'll add a "?".
                    if self.content_loaded:
                        if self.fm.settings.autoupdate_cumulative_size:
                            self.look_up_cumulative_size()
                        else:
                            self.infostring = ' %s' % human_readable(
                                self.size, separator='? ')
                    else:
                        self.infostring = ' %s' % human_readable(self.size)
                else:
                    self.size = len(filelist)
                    self.infostring = ' %d' % self.size
                if self.is_link:
                    self.infostring = '->' + self.infostring

                filenames = [mypath + (mypath == '/' and fname or '/' + fname)
                        for fname in filelist]
                yield

                self.load_content_mtime = os.stat(mypath).st_mtime

                marked_paths = [obj.path for obj in self.marked_items]

                files = []
                disk_usage = 0

                if self.settings.vcs_aware:
                    self.has_vcschild = False
                    self.load_vcs(None)

                for name in filenames:
                    try:
                        file_lstat = os_lstat(name)
                        if file_lstat.st_mode & 0o170000 == 0o120000:
                            file_stat = os_stat(name)
                        else:
                            file_stat = file_lstat
                        stats = (file_stat, file_lstat)
                        is_a_dir = file_stat.st_mode & 0o170000 == 0o040000
                    except:
                        stats = None
                        is_a_dir = False
                    if is_a_dir:
                        try:
                            item = self.fm.get_directory(name)
                            item.load_if_outdated()
                        except:
                            item = Directory(name, preload=stats,
                                    path_is_abs=True)
                            item.load()
                    else:
                        item = File(name, preload=stats, path_is_abs=True)
                        item.load()
                        disk_usage += item.size

                    # Load vcs data
                    if self.settings.vcs_aware:
                        item.load_vcs(self)
                        if item.vcs_enabled:
                            self.has_vcschild = True

                    files.append(item)
                    self.percent = 100 * len(files) // len(filenames)
                    yield
                self.disk_usage = disk_usage
                self.vcs_outdated = False

                self.filenames = filenames
                self.files_all = files

                self._clear_marked_items()
                for item in self.files_all:
                    if item.path in marked_paths:
                        item._mark(True)
                        self.marked_items.append(item)
                    else:
                        item._mark(False)

                self.sort()

                if files:
                    if self.pointed_obj is not None:
                        self.sync_index()
                    else:
                        self.move(to=0)
            else:
                self.filenames = None
                self.files_all = None
                self.files = None

            self.cycle_list = None
            self.content_loaded = True
            self.last_update_time = time()
            self.correct_pointer()

        finally:
            self.loading = False
            self.fm.signal_emit("finished_loading_dir", directory=self)

    def unload(self):
        self.loading = False
        self.load_generator = None

    def load_content(self, schedule=None):
        """Loads the contents of the directory.

        Use this sparingly since it takes rather long.
        """
        self.content_outdated = False

        if not self.loading:
            if not self.loaded:
                self.load()

            if not self.accessible:
                self.content_loaded = True
                return

            if schedule is None:
                schedule = True   # was: self.size > 30

            if self.load_generator is None:
                self.load_generator = self.load_bit_by_bit()

                if schedule and self.fm:
                    self.fm.loader.add(self)
                else:
                    for _ in self.load_generator:
                        pass
                    self.load_generator = None

            elif not schedule or not self.fm:
                for _ in self.load_generator:
                    pass
                self.load_generator = None


    def sort(self):
        """Sort the contained files"""
        if self.files_all is None:
            return

        try:
            sort_func = self.sort_dict[self.settings.sort]
        except:
            sort_func = sort_by_basename

        if self.settings.sort_case_insensitive and \
                sort_func == sort_by_basename:
            sort_func = sort_by_basename_icase

        if self.settings.sort_case_insensitive and \
                sort_func == sort_naturally:
            sort_func = sort_naturally_icase

        self.files_all.sort(key = sort_func)

        if self.settings.sort_reverse:
            self.files_all.reverse()

        if self.settings.sort_directories_first:
            self.files_all.sort(key = sort_by_directory)

        self.refilter()

    def _get_cumulative_size(self):
        if self.size == 0:
            return 0
        cum = 0
        realpath = os.path.realpath
        for dirpath, dirnames, filenames in os.walk(self.path,
                onerror=lambda _: None):
            for file in filenames:
                try:
                    if dirpath == self.path:
                        stat = os_stat(realpath(dirpath + "/" + file))
                    else:
                        stat = os_stat(dirpath + "/" + file)
                    cum += stat.st_size
                except:
                    pass
        return cum

    def look_up_cumulative_size(self):
        self._cumulative_size_calculated = True
        self.size = self._get_cumulative_size()
        self.infostring = ('-> ' if self.is_link else ' ') + \
                human_readable(self.size)

    @lazy_property
    def size(self):
        try:
            if self.fm.settings.automatically_count_files:
                size = len(os.listdir(self.path))
            else:
                size = None
        except OSError:
            self.infostring = BAD_INFO
            self.accessible = False
            self.runnable = False
            return 0
        else:
            if size is None:
                self.infostring = ''
            else:
                self.infostring = ' %d' % size
            self.accessible = True
            self.runnable = True
            return size

    @lazy_property
    def infostring(self):
        self.size  # trigger the lazy property initializer
        if self.is_link:
            return '->' + self.infostring
        return self.infostring

    @lazy_property
    def runnable(self):
        self.size  # trigger the lazy property initializer
        return self.runnable

    def sort_if_outdated(self):
        """Sort the containing files if they are outdated"""
        if self.order_outdated:
            self.order_outdated = False
            self.sort()
            return True
        return False

    def move_to_obj(self, arg):
        try:
            arg = arg.path
        except:
            pass
        self.load_content_once(schedule=False)
        if self.empty():
            return

        Accumulator.move_to_obj(self, arg, attr='path')

    def search_fnc(self, fnc, offset=1, forward=True):
        if not hasattr(fnc, '__call__'):
            return False

        length = len(self)

        if forward:
            generator = ((self.pointer + (x + offset)) % length \
                    for x in range(length - 1))
        else:
            generator = ((self.pointer - (x + offset)) % length \
                    for x in range(length - 1))

        for i in generator:
            _file = self.files[i]
            if fnc(_file):
                self.pointer = i
                self.pointed_obj = _file
                self.correct_pointer()
                return True
        return False

    def set_cycle_list(self, lst):
        self.cycle_list = deque(lst)

    def cycle(self, forward=True):
        if self.cycle_list:
            if forward is True:
                self.cycle_list.rotate(-1)
            elif forward is False:
                self.cycle_list.rotate(1)

            self.move_to_obj(self.cycle_list[0])

    def correct_pointer(self):
        """Make sure the pointer is in the valid range"""
        Accumulator.correct_pointer(self)

        try:
            if self == self.fm.thisdir:
                self.fm.thisfile = self.pointed_obj
        except:
            pass

    def load_content_once(self, *a, **k):
        """Load the contents of the directory if not done yet"""
        if not self.content_loaded:
            self.load_content(*a, **k)
            return True
        return False

    def load_content_if_outdated(self, *a, **k):
        """Load the contents of the directory if outdated"""

        if self.load_content_once(*a, **k): return True

        if self.files_all is None or self.content_outdated:
            self.load_content(*a, **k)
            return True

        try:
            real_mtime = os.stat(self.path).st_mtime
        except OSError:
            real_mtime = None
            return False
        if self.stat:
            cached_mtime = self.load_content_mtime
        else:
            cached_mtime = 0

        if real_mtime != cached_mtime:
            self.load_content(*a, **k)
            return True
        return False

    def get_description(self):
        return "Loading " + str(self)

    def use(self):
        """mark the filesystem-object as used at the current time"""
        self.last_used = time()

    def is_older_than(self, seconds):
        """returns whether this object wasn't use()d in the last n seconds"""
        if seconds < 0:
            return True
        return self.last_used + seconds < time()

    def go(self, history=True):
        """enter the directory if the filemanager is running"""
        if self.fm:
            return self.fm.enter_dir(self.path, history=history)
        return False

    def empty(self):
        """Is the directory empty?"""
        return self.files is None or len(self.files) == 0

    def __nonzero__(self):
        """Always True"""
        return True
    __bool__ = __nonzero__

    def __len__(self):
        """The number of containing files"""
        assert self.accessible
        assert self.content_loaded
        assert self.files is not None
        return len(self.files)

    def __eq__(self, other):
        """Check for equality of the directories paths"""
        return isinstance(other, Directory) and self.path == other.path

    def __neq__(self, other):
        """Check for inequality of the directories paths"""
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.path)

########NEW FILE########
__FILENAME__ = file
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

import re
from ranger.container.fsobject import FileSystemObject

N_FIRST_BYTES = 256
control_characters = set(chr(n) for n in
        set(range(0, 9)) | set(range(14, 32)))

# Don't even try to preview files which match this regular expression:
PREVIEW_BLACKLIST = re.compile(r"""
        # look at the extension:
        \.(
            # one character extensions:
                [oa]
            # media formats:
                | avi | mpe?g | mp\d | og[gmv] | wm[av] | mkv | flv
                | vob | wav | mpc | flac | divx? | xcf | pdf
            # binary files:
                | torrent | class | so | img | py[co] | dmg
        )
        # ignore filetype-independent suffixes:
            (\.part|\.bak|~)?
        # ignore fully numerical file extensions:
            (\.\d+)*?
        $
""", re.VERBOSE | re.IGNORECASE)

# Preview these files (almost) always:
PREVIEW_WHITELIST = re.compile(r"""
        \.(
            txt | py | c
        )
        # ignore filetype-independent suffixes:
            (\.part|\.bak|~)?
        $
""", re.VERBOSE | re.IGNORECASE)

class File(FileSystemObject):
    is_file = True
    preview_data = None
    preview_known = False
    preview_loading = False

    @property
    def firstbytes(self):
        try:
            return self._firstbytes
        except:
            try:
                f = open(self.path, 'r')
                self._firstbytes = f.read(N_FIRST_BYTES)
                f.close()
                return self._firstbytes
            except:
                pass

    def is_binary(self):
        if self.firstbytes and control_characters & set(self.firstbytes):
            return True
        return False

    def has_preview(self):
        if not self.fm.settings.preview_files:
            return False
        if self.is_socket or self.is_fifo or self.is_device:
            return False
        if not self.accessible:
            return False
        if self.fm.settings.preview_max_size and \
                self.size > self.fm.settings.preview_max_size:
            return False
        if self.fm.settings.preview_script and \
                self.fm.settings.use_preview_script:
            return True
        if self.image and self.fm.settings.preview_images:
            return True
        if self.container:
            return False
        if PREVIEW_WHITELIST.search(self.basename):
            return True
        if PREVIEW_BLACKLIST.search(self.basename):
            return False
        if self.path == '/dev/core' or self.path == '/proc/kcore':
            return False
        if self.is_binary():
            return False
        return True

    def get_preview_source(self, width, height):
        return self.fm.get_preview(self, width, height)

    def is_image_preview(self):
        try:
            return self.fm.previews[self.realpath]['imagepreview']
        except KeyError:
            return False

########NEW FILE########
__FILENAME__ = fsobject
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

CONTAINER_EXTENSIONS = ('7z', 'ace', 'ar', 'arc', 'bz', 'bz2', 'cab', 'cpio',
    'cpt', 'deb', 'dgc', 'dmg', 'gz', 'iso', 'jar', 'msi', 'pkg', 'rar',
    'shar', 'tar', 'tbz', 'tgz', 'xar', 'xpi', 'xz', 'zip')
DOCUMENT_EXTENSIONS = ('cfg', 'css', 'cvs', 'djvu', 'doc', 'docx', 'gnm',
    'gnumeric', 'htm', 'html', 'md', 'odf', 'odg', 'odp', 'ods', 'odt', 'pdf',
    'pod', 'ps', 'rtf', 'sxc', 'txt', 'xls', 'xlw', 'xml', 'xslx')
DOCUMENT_BASENAMES = ('bugs', 'bugs', 'changelog', 'copying', 'credits',
    'hacking', 'help', 'install', 'license', 'readme', 'todo')

BAD_INFO = '?'

import re
from os import lstat, stat
from os.path import abspath, basename, dirname, realpath, splitext, extsep
from ranger.core.shared import FileManagerAware, SettingsAware
from ranger.ext.shell_escape import shell_escape
from ranger.ext.spawn import spawn
from ranger.ext.lazy_property import lazy_property
from ranger.ext.human_readable import human_readable

if hasattr(str, 'maketrans'):
    maketrans = str.maketrans
else:
    from string import maketrans
_unsafe_chars = '\n' + ''.join(map(chr, range(32))) + ''.join(map(chr, range(128, 256)))
_safe_string_table = maketrans(_unsafe_chars, '?' * len(_unsafe_chars))
_extract_number_re = re.compile(r'([^0-9]?)(\d*)')

def safe_path(path):
    return path.translate(_safe_string_table)

class FileSystemObject(FileManagerAware, SettingsAware):
    (basename,
    basename_lower,
    dirname,
    extension,
    infostring,
    path,
    permissions,
    stat) = (None,) * 8

    (content_loaded,
    force_load,

    is_device,
    is_directory,
    is_file,
    is_fifo,
    is_link,
    is_socket,

    accessible,
    exists,       # "exists" currently means "link_target_exists"
    loaded,
    marked,
    runnable,
    stopped,
    tagged,

    audio,
    container,
    document,
    image,
    media,
    video) = (False,) * 21

    size = 0

    (vcs,
     vcsfilestatus,
     vcsremotestatus,
     vcsbranch,
     vcshead) = (None,) * 5

    vcs_outdated = False
    vcs_enabled = False

    def __init__(self, path, preload=None, path_is_abs=False):
        if not path_is_abs:
            path = abspath(path)
        self.path = path
        self.basename = basename(path)
        self.basename_lower = self.basename.lower()
        self.extension = splitext(self.basename)[1].lstrip(extsep) or None
        self.dirname = dirname(path)
        self.preload = preload
        self.display_data = {}

        try:
            lastdot = self.basename.rindex('.') + 1
            self.extension = self.basename[lastdot:].lower()
        except ValueError:
            self.extension = None

    def __repr__(self):
        return "<{0} {1}>".format(self.__class__.__name__, self.path)

    @lazy_property
    def shell_escaped_basename(self):
        return shell_escape(self.basename)

    @lazy_property
    def filetype(self):
        try:
            return spawn(["file", '-Lb', '--mime-type', self.path])
        except OSError:
            return ""

    @lazy_property
    def basename_natural(self):
        return [c if i % 3 == 1 else (int(c) if c else 0) for i, c in \
            enumerate(_extract_number_re.split(self.basename))]

    @lazy_property
    def basename_natural_lower(self):
        return [c if i % 3 == 1 else (int(c) if c else 0) for i, c in \
            enumerate(_extract_number_re.split(self.basename_lower))]

    @lazy_property
    def safe_basename(self):
        return self.basename.translate(_safe_string_table)


    for attr in ('video', 'audio', 'image', 'media', 'document', 'container'):
        exec("%s = lazy_property("
            "lambda self: self.set_mimetype() or self.%s)" % (attr, attr))

    def __str__(self):
        """returns a string containing the absolute path"""
        return str(self.path)

    def use(self):
        """Used in garbage-collecting.  Override in Directory"""

    def look_up_cumulative_size(self):
        pass # normal files have no cumulative size

    def set_mimetype(self):
        """assign attributes such as self.video according to the mimetype"""
        basename = self.basename
        if self.extension == 'part':
            basename = basename[0:-5]
        self._mimetype = self.fm.mimetypes.guess_type(basename, False)[0]
        if self._mimetype is None:
            self._mimetype = ''

        self.video = self._mimetype.startswith('video')
        self.image = self._mimetype.startswith('image')
        self.audio = self._mimetype.startswith('audio')
        self.media = self.video or self.image or self.audio
        self.document = self._mimetype.startswith('text') \
                or self.extension in DOCUMENT_EXTENSIONS \
                or self.basename.lower() in DOCUMENT_BASENAMES
        self.container = self.extension in CONTAINER_EXTENSIONS

        keys = ('video', 'audio', 'image', 'media', 'document', 'container')
        self._mimetype_tuple = tuple(key for key in keys if getattr(self, key))

        if self._mimetype == '':
            self._mimetype = None

    @property
    def mimetype(self):
        try:
            return self._mimetype
        except:
            self.set_mimetype()
            return self._mimetype

    @property
    def mimetype_tuple(self):
        try:
            return self._mimetype_tuple
        except:
            self.set_mimetype()
            return self._mimetype_tuple

    def mark(self, boolean):
        directory = self.fm.get_directory(self.dirname)
        directory.mark_item(self)

    def _mark(self, boolean):
        """Called by directory.mark_item() and similar functions"""
        self.marked = bool(boolean)

    @lazy_property
    def realpath(self):
        if self.is_link:
            try:
                return realpath(self.path)
            except:
                return None  # it is impossible to get the link destination
        return self.path

    def load_vcs(self, parent):
        """
        Reads data regarding the version control system the object is on.
        Does not load content specific data.
        """
        from ranger.ext.vcs import Vcs, VcsError

        vcs = Vcs(self.path)

        # Not under vcs
        if vcs.root == None:
            return

        # Already know about the right vcs
        elif self.vcs and abspath(vcs.root) == abspath(self.vcs.root):
            self.vcs.update()

        # Need new Vcs object and self.path is the root
        elif self.vcs == None and abspath(vcs.root) == abspath(self.path):
            self.vcs = vcs
            self.vcs_outdated = True

        # Otherwise, find the root, and try to get the Vcs object from there
        else:
            rootdir = self.fm.get_directory(vcs.root)
            rootdir.load_if_outdated()

            # Get the Vcs object from rootdir
            rootdir.load_vcs(None)
            self.vcs = rootdir.vcs
            if rootdir.vcs_outdated:
                self.vcs_outdated = True

        if self.vcs:
            if self.vcs.vcsname == 'git':
                backend_state = self.settings.vcs_backend_git
            elif self.vcs.vcsname == 'hg':
                backend_state = self.settings.vcs_backend_hg
            elif self.vcs.vcsname == 'bzr':
                backend_state = self.settings.vcs_backend_bzr
            else:
                backend_state = 'disabled'

            self.vcs_enabled = backend_state in set(['enabled', 'local'])
            if self.vcs_enabled:
                try:
                    if self.vcs_outdated or (parent and parent.vcs_outdated):
                        self.vcs_outdated = False
                        # this caches the file status for get_file_status():
                        self.vcs.get_status()
                        self.vcsbranch = self.vcs.get_branch()
                        self.vcshead = self.vcs.get_info(self.vcs.HEAD)
                        if self.path == self.vcs.root and \
                                backend_state == 'enabled':
                            self.vcsremotestatus = \
                                    self.vcs.get_remote_status()
                    elif parent:
                        self.vcsbranch = parent.vcsbranch
                        self.vcshead = parent.vcshead
                    self.vcsfilestatus = self.vcs.get_file_status(self.path)
                except VcsError as err:
                    self.vcsbranch = None
                    self.vcshead = None
                    self.vcsremotestatus = 'unknown'
                    self.vcsfilestatus = 'unknown'
                    self.fm.notify("Can not load vcs data on %s: %s" %
                            (self.path, err), bad=True)
        else:
            self.vcs_enabled = False

    def load(self):
        """Loads information about the directory itself.

        reads useful information about the filesystem-object from the
        filesystem and caches it for later use
        """

        self.display_data = {}
        self.fm.update_preview(self.path)
        self.loaded = True

        # Get the stat object, either from preload or from [l]stat
        self.permissions = None
        new_stat = None
        path = self.path
        is_link = False
        if self.preload:
            new_stat = self.preload[1]
            self.is_link = new_stat.st_mode & 0o170000 == 0o120000
            if self.is_link:
                new_stat = self.preload[0]
            self.preload = None
            self.exists = True if new_stat else False
        else:
            try:
                new_stat = lstat(path)
                self.is_link = new_stat.st_mode & 0o170000 == 0o120000
                if self.is_link:
                    new_stat = stat(path)
                self.exists = True
            except:
                self.exists = False

        # Set some attributes

        self.accessible = True if new_stat else False
        mode = new_stat.st_mode if new_stat else 0

        format = mode & 0o170000
        if format == 0o020000 or format == 0o060000:  # stat.S_IFCHR/BLK
            self.is_device = True
            self.size = 0
            self.infostring = 'dev'
        elif format == 0o010000:  # stat.S_IFIFO
            self.is_fifo = True
            self.size = 0
            self.infostring = 'fifo'
        elif format == 0o140000:  # stat.S_IFSOCK
            self.is_socket = True
            self.size = 0
            self.infostring = 'sock'
        elif self.is_file:
            if new_stat:
                self.size = new_stat.st_size
                self.infostring = ' ' + human_readable(self.size)
            else:
                self.size = 0
                self.infostring = '?'
        if self.is_link and not self.is_directory:
            self.infostring = '->' + self.infostring

        self.stat = new_stat

    def get_permission_string(self):
        if self.permissions is not None:
            return self.permissions

        if self.is_directory:
            perms = ['d']
        elif self.is_link:
            perms = ['l']
        else:
            perms = ['-']

        mode = self.stat.st_mode
        test = 0o0400
        while test:  # will run 3 times because 0o400 >> 9 = 0
            for what in "rwx":
                if mode & test:
                    perms.append(what)
                else:
                    perms.append('-')
                test >>= 1

        self.permissions = ''.join(perms)
        return self.permissions

    def load_if_outdated(self):
        """Calls load() if the currently cached information is outdated"""
        if not self.loaded:
            self.load()
            return True
        try:
            real_ctime = lstat(self.path).st_ctime
        except OSError:
            real_ctime = None
        if not self.stat or self.stat.st_ctime != real_ctime:
            self.load()
            return True
        return False

########NEW FILE########
__FILENAME__ = history
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

# TODO: rewrite to use deque instead of list

class HistoryEmptyException(Exception):
    pass

class History(object):
    def __init__(self, maxlen=None, unique=True):
        if isinstance(maxlen, History):
            self._history = list(maxlen._history)
            self._index = maxlen._index
            self.maxlen = maxlen.maxlen
            self.unique = maxlen.unique
        else:
            self._history = []
            self._index = 0
            self.maxlen = maxlen
            self.unique = unique

    def add(self, item):
        # Remove everything after index
        if self._index < len(self._history) - 2:
            del self._history[:self._index+1]
        # Remove Duplicates
        if self.unique:
            try:
                self._history.remove(item)
            except:
                pass
        else:
            if self._history and self._history[-1] == item:
                del self._history[-1]
        # Remove first if list is too long
        if len(self._history) > max(self.maxlen - 1, 0):
            del self._history[0]
        # Append the item and fast forward
        self._history.append(item)
        self._index = len(self._history) - 1

    def modify(self, item, unique=False):
        if self._history and unique:
            try:
                self._history.remove(item)
                self._index -= 1
            except:
                pass
        try:
            self._history[self._index] = item
        except IndexError:
            self.add(item)

    def rebase(self, other_history):
        assert isinstance(other_history, History)
        index_offset = len(self._history) - self._index
        self._history[:self._index] = list(other_history._history)
        if len(self._history) > self.maxlen:
            self._history = self._history[-self.maxlen:]
        self._index = len(self._history) - index_offset

    def __len__(self):
        return len(self._history)

    def current(self):
        if self._history:
            return self._history[self._index]
        else:
            raise HistoryEmptyException

    def top(self):
        try:
            return self._history[-1]
        except IndexError:
            raise HistoryEmptyException()

    def bottom(self):
        try:
            return self._history[0]
        except IndexError:
            raise HistoryEmptyException()

    def back(self):
        self._index -= 1
        if self._index < 0:
            self._index = 0
        return self.current()

    def move(self, n):
        self._index += n
        if self._index > len(self._history) - 1:
            self._index = len(self._history) - 1
        if self._index < 0:
            self._index = 0
        return self.current()

    def search(self, string, n):
        if n != 0 and string:
            step = n > 0 and 1 or -1
            i = self._index
            steps_left = steps_left_at_start = int(abs(n))
            while steps_left:
                i += step
                if i >= len(self._history) or i < 0:
                    break
                if self._history[i].startswith(string):
                    steps_left -= 1
            if steps_left != steps_left_at_start:
                self._index = i
        return self.current()

    def __iter__(self):
        return self._history.__iter__()

    def next(self):
        return self._history.next()

    def forward(self):
        if self._history:
            self._index += 1
            if self._index > len(self._history) - 1:
                self._index = len(self._history) - 1
        else:
            self._index = 0
        return self.current()

    def fast_forward(self):
        if self._history:
            self._index = len(self._history) - 1
        else:
            self._index = 0

    def _left(self):  # used for unit test
        return self._history[0:self._index+1]

########NEW FILE########
__FILENAME__ = settings
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

from inspect import isfunction
from ranger.ext.signals import SignalDispatcher, Signal
from ranger.core.shared import FileManagerAware
from ranger.gui.colorscheme import _colorscheme_name_to_class
import re
import os.path

ALLOWED_SETTINGS = {
    'automatically_count_files': bool,
    'autosave_bookmarks': bool,
    'autoupdate_cumulative_size': bool,
    'cd_bookmarks': bool,
    'collapse_preview': bool,
    'colorscheme': str,
    'column_ratios': (tuple, list),
    'confirm_on_delete': str,
    'dirname_in_tabs': bool,
    'display_size_in_main_column': bool,
    'display_size_in_status_bar': bool,
    'display_tags_in_all_columns': bool,
    'draw_borders': bool,
    'draw_progress_bar_in_status_bar': bool,
    'flushinput': bool,
    'hidden_filter': str,
    'max_console_history_size': (int, type(None)),
    'max_history_size': (int, type(None)),
    'mouse_enabled': bool,
    'open_all_images': bool,
    'padding_right': bool,
    'preview_directories': bool,
    'preview_files': bool,
    'preview_images': bool,
    'preview_max_size': int,
    'preview_script': (str, type(None)),
    'save_console_history': bool,
    'scroll_offset': int,
    'shorten_title': int,
    'show_cursor': bool,  # TODO: not working?
    'show_hidden_bookmarks': bool,
    'show_hidden': bool,
    'sort_case_insensitive': bool,
    'sort_directories_first': bool,
    'sort_reverse': bool,
    'sort': str,
    'status_bar_on_top': bool,
    'tilde_in_titlebar': bool,
    'unicode_ellipsis': bool,
    'update_title': bool,
    'update_tmux_title': bool,
    'use_preview_script': bool,
    'vcs_aware': bool,
    'vcs_backend_bzr': str,
    'vcs_backend_git': str,
    'vcs_backend_hg': str,
    'xterm_alt_key': bool,
}

DEFAULT_VALUES = {
    bool: False,
    type(None): None,
    str: "",
    int: 0,
    list: [],
    tuple: tuple([]),
}

class Settings(SignalDispatcher, FileManagerAware):
    def __init__(self):
        SignalDispatcher.__init__(self)
        self.__dict__['_localsettings'] = dict()
        self.__dict__['_localregexes'] = dict()
        self.__dict__['_tagsettings'] = dict()
        self.__dict__['_settings'] = dict()
        for name in ALLOWED_SETTINGS:
            self.signal_bind('setopt.'+name,
                    self._sanitize, priority=1.0)
            self.signal_bind('setopt.'+name,
                    self._raw_set_with_signal, priority=0.2)

    def _sanitize(self, signal):
        name, value = signal.setting, signal.value
        if name == 'column_ratios':
            # TODO: cover more cases here
            if isinstance(value, tuple):
                signal.value = list(value)
            if not isinstance(value, list) or len(value) < 2:
                signal.value = [1, 1]
            else:
                signal.value = [int(i) if str(i).isdigit() else 1 \
                        for i in value]

        elif name == 'colorscheme':
            _colorscheme_name_to_class(signal)

        elif name == 'preview_script':
            if isinstance(value, str):
                result = os.path.expanduser(value)
                if os.path.exists(result):
                    signal.value = result
                else:
                    signal.value = None

        elif name == 'use_preview_script':
            if self._settings['preview_script'] is None and value \
                    and self.fm.ui.is_on:
                self.fm.notify("Preview script undefined or not found!",
                        bad=True)

    def set(self, name, value, path=None, tags=None):
        assert name in ALLOWED_SETTINGS, "No such setting: {0}!".format(name)
        if name not in self._settings:
            previous = None
        else:
            previous=self._settings[name]
        assert self._check_type(name, value)
        assert not (tags and path), "Can't set a setting for path and tag " \
            "at the same time!"
        kws = dict(setting=name, value=value, previous=previous,
                path=path, tags=tags, fm=self.fm)
        self.signal_emit('setopt', **kws)
        self.signal_emit('setopt.'+name, **kws)

    def get(self, name, path=None):
        assert name in ALLOWED_SETTINGS, "No such setting: {0}!".format(name)
        if path:
            localpath = path
        else:
            try:
                localpath = self.fm.thisdir.path
            except:
                localpath = path

        if localpath:
            for pattern, regex in self._localregexes.items():
                if name in self._localsettings[pattern] and\
                        regex.search(localpath):
                    return self._localsettings[pattern][name]
        if self._tagsettings and path:
            realpath = os.path.realpath(path)
            if realpath in self.fm.tags:
                tag = self.fm.tags.marker(realpath)
                if tag in self._tagsettings and name in self._tagsettings[tag]:
                    return self._tagsettings[tag][name]
        if name in self._settings:
            return self._settings[name]
        else:
            type_ = self.types_of(name)[0]
            value = DEFAULT_VALUES[type_]
            self._raw_set(name, value)
            self.__setattr__(name, value)
            return self._settings[name]

    def __setattr__(self, name, value):
        if name.startswith('_'):
            self.__dict__[name] = value
        else:
            self.set(name, value, None)

    def __getattr__(self, name):
        if name.startswith('_'):
            return self.__dict__[name]
        else:
            return self.get(name, None)

    def __iter__(self):
        for x in self._settings:
            yield x

    def types_of(self, name):
        try:
            typ = ALLOWED_SETTINGS[name]
        except KeyError:
            return tuple()
        else:
            if isinstance(typ, tuple):
                return typ
            else:
                return (typ, )


    def _check_type(self, name, value):
        typ = ALLOWED_SETTINGS[name]
        if isfunction(typ):
            assert typ(value), \
                "Warning: The option `" + name + "' has an incorrect type!"
        else:
            assert isinstance(value, typ), \
                "Warning: The option `" + name + "' has an incorrect type!"\
                " Got " + str(type(value)) + ", expected " + str(typ) + "!" +\
                " Please check if your commands.py is up to date." if not \
                self.fm.ui.is_set_up else ""
        return True

    __getitem__ = __getattr__
    __setitem__ = __setattr__

    def _raw_set(self, name, value, path=None, tags=None):
        if path:
            if not path in self._localsettings:
                try:
                    regex = re.compile(path)
                except:
                    # Bad regular expression
                    return
                self._localregexes[path] = regex
                self._localsettings[path] = dict()
            self._localsettings[path][name] = value

            # make sure name is in _settings, so __iter__ runs through
            # local settings too.
            if not name in self._settings:
                type_ = self.types_of(name)[0]
                value = DEFAULT_VALUES[type_]
                self._settings[name] = value
        elif tags:
            for tag in tags:
                if tag not in self._tagsettings:
                    self._tagsettings[tag] = dict()
                self._tagsettings[tag][name] = value
        else:
            self._settings[name] = value

    def _raw_set_with_signal(self, signal):
        self._raw_set(signal.setting, signal.value, signal.path, signal.tags)


class LocalSettings():
    def __init__(self, path, parent):
        self.__dict__['_parent'] = parent
        self.__dict__['_path'] = path

    def __setattr__(self, name, value):
        if name.startswith('_'):
            self.__dict__[name] = value
        else:
            self._parent.set(name, value, self._path)

    def __getattr__(self, name):
        if name.startswith('_'):
            return self.__dict__[name]
        else:
            return self._parent.get(name, self._path)

    def __iter__(self):
        for x in self._parent._settings:
            yield x

    __getitem__ = __getattr__
    __setitem__ = __setattr__

########NEW FILE########
__FILENAME__ = tags
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

# TODO: add a __getitem__ method to get the tag of a file

from os.path import isdir, exists, dirname, abspath, realpath, expanduser
import string

ALLOWED_KEYS = string.ascii_letters + string.digits + string.punctuation

class Tags(object):
    default_tag = '*'

    def __init__(self, filename):

        self._filename = realpath(abspath(expanduser(filename)))

        if isdir(dirname(self._filename)) and not exists(self._filename):
            open(self._filename, 'w')

        self.sync()

    def __contains__(self, item):
        return item in self.tags

    def add(self, *items, **others):
        if 'tag' in others:
            tag = others['tag']
        else:
            tag = self.default_tag
        self.sync()
        for item in items:
            self.tags[item] = tag
        self.dump()

    def remove(self, *items):
        self.sync()
        for item in items:
            try:
                del(self.tags[item])
            except KeyError:
                pass
        self.dump()

    def toggle(self, *items, **others):
        if 'tag' in others:
            tag = others['tag']
        else:
            tag = self.default_tag
        tag = str(tag)
        if tag not in ALLOWED_KEYS:
            return
        self.sync()
        for item in items:
            try:
                if item in self and tag in (self.tags[item], self.default_tag):
                    del(self.tags[item])
                else:
                    self.tags[item] = tag
            except KeyError:
                pass
        self.dump()

    def marker(self, item):
        if item in self.tags:
            return self.tags[item]
        else:
            return self.default_tag

    def sync(self):
        try:
            f = open(self._filename, 'r')
        except OSError:
            pass
        else:
            self.tags = self._parse(f)
            f.close()

    def dump(self):
        try:
            f = open(self._filename, 'w')
        except OSError:
            pass
        else:
            self._compile(f)
            f.close()

    def _compile(self, f):
        for path, tag in self.tags.items():
            if tag == self.default_tag:
                # COMPAT: keep the old format if the default tag is used
                f.write(path + '\n')
            elif tag in ALLOWED_KEYS:
                f.write('{0}:{1}\n'.format(tag, path))

    def _parse(self, f):
        result = dict()
        for line in f:
            line = line.strip()
            if len(line) > 2 and line[1] == ':':
                tag, path = line[0], line[2:]
                if tag in ALLOWED_KEYS:
                    result[path] = tag
            else:
                result[line] = self.default_tag

        return result

    def __nonzero__(self):
        return True
    __bool__ = __nonzero__

########NEW FILE########
__FILENAME__ = actions
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

import codecs
import os
import re
import shutil
import string
import tempfile
from os.path import join, isdir, realpath, exists
from os import link, symlink, getcwd, listdir, stat
from inspect import cleandoc
from stat import S_IEXEC
from hashlib import sha1
from sys import version_info

import ranger
from ranger.ext.direction import Direction
from ranger.ext.relative_symlink import relative_symlink
from ranger.ext.keybinding_parser import key_to_string, construct_keybinding
from ranger.ext.shell_escape import shell_quote
from ranger.ext.next_available_filename import next_available_filename
from ranger.ext.rifle import squash_flags, ASK_COMMAND
from ranger.core.shared import FileManagerAware, EnvironmentAware, \
        SettingsAware
from ranger.core.tab import Tab
from ranger.container.file import File
from ranger.core.loader import CommandLoader, CopyLoader
from ranger.container.settings import ALLOWED_SETTINGS

MACRO_FAIL = "<\x01\x01MACRO_HAS_NO_VALUE\x01\01>"

class _MacroTemplate(string.Template):
    """A template for substituting macros in commands"""
    delimiter = ranger.MACRO_DELIMITER

class Actions(FileManagerAware, EnvironmentAware, SettingsAware):
    # --------------------------
    # -- Basic Commands
    # --------------------------

    def exit(self):
        """Exit the program"""
        raise SystemExit()

    def reset(self):
        """Reset the filemanager, clearing the directory buffer"""
        old_path = self.thisdir.path
        self.previews = {}
        self.garbage_collect(-1)
        self.enter_dir(old_path)
        self.change_mode('normal')

    def change_mode(self, mode):
        if mode == self.mode:
            return
        if mode == 'visual':
            self._visual_start       = self.thisdir.pointed_obj
            self._visual_start_pos   = self.thisdir.pointer
            self._previous_selection = set(self.thisdir.marked_items)
            self.mark_files(val=not self._visual_reverse, movedown=False)
        elif mode == 'normal':
            if self.mode == 'visual':
                self._visual_start       = None
                self._visual_start_pos   = None
                self._previous_selection = None
        else:
            return
        self.mode = mode
        self.ui.status.request_redraw()

    def set_option_from_string(self, option_name, value, localpath=None, tags=None):
        if option_name not in ALLOWED_SETTINGS:
            raise ValueError("The option named `%s' does not exist" %
                    option_name)
        if not isinstance(value, str):
            raise ValueError("The value for an option needs to be a string.")

        self.settings.set(option_name, self._parse_option_value(option_name, value), localpath, tags)


    def _parse_option_value(self, name, value):
        types = self.fm.settings.types_of(name)
        if bool in types:
            if value.lower() in ('false', 'off', '0'):
                return False
            elif value.lower() in ('true', 'on', '1'):
                return True
        if type(None) in types and value.lower() == 'none':
            return None
        if int in types:
            try:
                return int(value)
            except ValueError:
                pass
        if str in types:
            return value
        if list in types:
            return value.split(',')
        raise ValueError("Invalid value `%s' for option `%s'!" % (name, value))

    def toggle_visual_mode(self, reverse=False, narg=None):
        if self.mode == 'normal':
            self._visual_reverse = reverse
            if narg != None:
                self.mark_files(val=not reverse, narg=narg)
            self.change_mode('visual')
        else:
            self.change_mode('normal')

    def reload_cwd(self):
        try:
            cwd = self.thisdir
        except:
            pass
        cwd.unload()
        cwd.load_content()

    def notify(self, text, duration=4, bad=False):
        if isinstance(text, Exception):
            if ranger.arg.debug:
                raise
            bad = True
        elif bad == True and ranger.arg.debug:
            raise Exception(str(text))
        text = str(text)
        self.log.appendleft(text)
        if self.ui and self.ui.is_on:
            self.ui.status.notify("  ".join(text.split("\n")),
                    duration=duration, bad=bad)
        else:
            print(text)

    def abort(self):
        try:
            item = self.loader.queue[0]
        except:
            self.notify("Type Q or :quit<Enter> to exit ranger")
        else:
            self.notify("Aborting: " + item.get_description())
            self.loader.remove(index=0)

    def get_cumulative_size(self):
        for f in self.thistab.get_selection() or ():
            f.look_up_cumulative_size()
        self.ui.status.request_redraw()
        self.ui.redraw_main_column()

    def redraw_window(self):
        """Redraw the window"""
        self.ui.redraw_window()

    def open_console(self, string='', prompt=None, position=None):
        """Open the console"""
        self.change_mode('normal')
        self.ui.open_console(string, prompt=prompt, position=position)

    def execute_console(self, string='', wildcards=[], quantifier=None):
        """Execute a command for the console"""
        command_name = string.split()[0]
        cmd_class = self.commands.get_command(command_name, abbrev=False)
        if cmd_class is None:
            self.notify("Command not found: `%s'" % command_name, bad=True)
            return
        cmd = cmd_class(string)
        if cmd.resolve_macros and _MacroTemplate.delimiter in string:
            macros = dict(('any%d'%i, key_to_string(char)) \
                    for i, char in enumerate(wildcards))
            if 'any0' in macros:
                macros['any'] = macros['any0']
            try:
                string = self.substitute_macros(string, additional=macros,
                        escape=cmd.escape_macros_for_shell)
            except ValueError as e:
                if ranger.arg.debug:
                    raise
                else:
                    return self.notify(e)
        try:
            cmd_class(string, quantifier=quantifier).execute()
        except Exception as e:
            if ranger.arg.debug:
                raise
            else:
                self.notify(e)

    def substitute_macros(self, string, additional=dict(), escape=False):
        macros = self._get_macros()
        macros.update(additional)
        if escape:
            for key, value in macros.items():
                if isinstance(value, list):
                    macros[key] = " ".join(shell_quote(s) for s in value)
                elif value != MACRO_FAIL:
                    macros[key] = shell_quote(value)
        else:
            for key, value in macros.items():
                if isinstance(value, list):
                    macros[key] = " ".join(value)
        result = _MacroTemplate(string).safe_substitute(macros)
        if MACRO_FAIL in result:
            raise ValueError("Could not apply macros to `%s'" % string)
        return result

    def _get_macros(self):
        macros = {}

        macros['rangerdir'] = ranger.RANGERDIR

        if self.fm.thisfile:
            macros['f'] = self.fm.thisfile.basename
        else:
            macros['f'] = MACRO_FAIL

        if self.fm.thistab.get_selection:
            macros['s'] = [fl.basename for fl in self.fm.thistab.get_selection()]
        else:
            macros['s'] = MACRO_FAIL

        if self.fm.copy_buffer:
            macros['c'] = [fl.path for fl in self.fm.copy_buffer]
        else:
            macros['c'] = MACRO_FAIL

        if self.fm.thisdir.files:
            macros['t'] = [fl.basename for fl in self.fm.thisdir.files
                    if fl.realpath in (self.fm.tags or [])]
        else:
            macros['t'] = MACRO_FAIL

        if self.fm.thisdir:
            macros['d'] = self.fm.thisdir.path
        else:
            macros['d'] = '.'

        # define d/f/s macros for each tab
        for i in range(1,10):
            try:
                tab = self.fm.tabs[i]
            except:
                continue
            tabdir = tab.thisdir
            if not tabdir:
                continue
            i = str(i)
            macros[i + 'd'] = tabdir.path
            if tabdir.get_selection():
                macros[i + 's'] = [fl.path for fl in tabdir.get_selection()]
            else:
                macros[i + 's'] = MACRO_FAIL
            if tabdir.pointed_obj:
                macros[i + 'f'] = tabdir.pointed_obj.path
            else:
                macros[i + 'f'] = MACRO_FAIL

        # define D/F/S for the next tab
        found_current_tab = False
        next_tab = None
        first_tab = None
        for tabname in self.fm.tabs:
            if not first_tab:
                first_tab = tabname
            if found_current_tab:
                next_tab = self.fm.tabs[tabname]
                break
            if self.fm.current_tab == tabname:
                found_current_tab = True
        if found_current_tab and next_tab is None:
            next_tab = self.fm.tabs[first_tab]
        next_tab_dir = next_tab.thisdir

        if next_tab_dir:
            macros['D'] = str(next_tab_dir.path)
            if next_tab.thisfile:
                macros['F'] = next_tab.thisfile.path
            else:
                macros['F'] = MACRO_FAIL
            if next_tab_dir.get_selection():
                macros['S'] = [fl.path for fl in next_tab.get_selection()]
            else:
                macros['S'] = MACRO_FAIL
        else:
            macros['D'] = MACRO_FAIL
            macros['F'] = MACRO_FAIL
            macros['S'] = MACRO_FAIL

        return macros

    def source(self, filename):
        filename = os.path.expanduser(filename)
        for line in open(filename, 'r'):
            line = line.lstrip().rstrip("\r\n")
            if line.startswith("#") or not line.strip():
                continue
            try:
                self.execute_console(line)
            except Exception as e:
                if ranger.arg.debug:
                    raise
                else:
                    self.notify('Error in line `%s\':\n  %s' %
                            (line, str(e)), bad=True)

    def execute_file(self, files, **kw):
        """Execute a file.

        app is the name of a method in Applications, without the "app_"
        flags is a string consisting of runner.ALLOWED_FLAGS
        mode is a positive integer.
        Both flags and mode specify how the program is run."""

        mode = kw['mode'] if 'mode' in kw else 0

        # ranger can act as a file chooser when running with --choosefile=...
        if mode == 0 and 'label' not in kw:
            if ranger.arg.choosefile:
                open(ranger.arg.choosefile, 'w').write(self.fm.thisfile.path)

            if ranger.arg.choosefiles:
                open(ranger.arg.choosefiles, 'w').write("".join(
                    f.path + "\n" for f in self.fm.thistab.get_selection()))

            if ranger.arg.choosefile or ranger.arg.choosefiles:
                raise SystemExit()

        if isinstance(files, set):
            files = list(files)
        elif type(files) not in (list, tuple):
            files = [files]

        flags = kw.get('flags', '')
        if 'c' in squash_flags(flags):
            files = [self.fm.thisfile]

        self.signal_emit('execute.before', keywords=kw)
        filenames = [f.path for f in files]
        label = kw.get('label', kw.get('app', None))
        try:
            return self.rifle.execute(filenames, mode, label, flags, None)
        finally:
            self.signal_emit('execute.after')

    # --------------------------
    # -- Moving Around
    # --------------------------

    def move(self, narg=None, **kw):
        """A universal movement method.

        Accepts these parameters:
        (int) down, (int) up, (int) left, (int) right, (int) to,
        (bool) absolute, (bool) relative, (bool) pages,
        (bool) percentage

        to=X is translated to down=X, absolute=True

        Example:
        self.move(down=4, pages=True)  # moves down by 4 pages.
        self.move(to=2, pages=True)  # moves to page 2.
        self.move(to=1, percentage=True)  # moves to 80%
        """
        cwd = self.thisdir
        direction = Direction(kw)
        if 'left' in direction or direction.left() > 0:
            steps = direction.left()
            if narg is not None:
                steps *= narg
            try:
                directory = os.path.join(*(['..'] * steps))
            except:
                return
            self.thistab.enter_dir(directory)
            self.change_mode('normal')
        if cwd and cwd.accessible and cwd.content_loaded:
            if 'right' in direction:
                mode = 0
                if narg is not None:
                    mode = narg
                cf = self.thisfile
                selection = self.thistab.get_selection()
                if not self.thistab.enter_dir(cf) and selection:
                    result = self.execute_file(selection, mode=mode)
                    if result in (False, ASK_COMMAND):
                        self.open_console('open_with ')
            elif direction.vertical() and cwd.files:
                newpos = direction.move(
                        direction=direction.down(),
                        override=narg,
                        maximum=len(cwd),
                        current=cwd.pointer,
                        pagesize=self.ui.browser.hei)
                cwd.move(to=newpos)
                if self.mode == 'visual':
                    try:
                        startpos = cwd.index(self._visual_start)
                    except:
                        self._visual_start = None
                        startpos = min(self._visual_start_pos, len(cwd))
                    # The files between here and _visual_start_pos
                    targets = set(cwd.files[min(startpos, newpos):\
                            max(startpos, newpos) + 1])
                    # The selection before activating visual mode
                    old = self._previous_selection
                    # The current selection
                    current = set(cwd.marked_items)

                    # Set theory anyone?
                    if not self._visual_reverse:
                        for f in targets - current:
                            cwd.mark_item(f, True)
                        for f in current - old - targets:
                            cwd.mark_item(f, False)
                    else:
                        for f in targets & current:
                            cwd.mark_item(f, False)
                        for f in old - current - targets:
                            cwd.mark_item(f, True)
                if self.ui.pager.visible:
                    self.display_file()


    def move_parent(self, n, narg=None):
        self.change_mode('normal')
        if narg is not None:
            n *= narg
        parent = self.thistab.at_level(-1)
        if parent is not None:
            if parent.pointer + n < 0:
                n = 0 - parent.pointer
            try:
                self.thistab.enter_dir(parent.files[parent.pointer+n])
            except IndexError:
                pass

    def select_file(self, path):
        path = path.strip()
        if self.enter_dir(os.path.dirname(path)):
            self.thisdir.move_to_obj(path)

    def history_go(self, relative):
        """Move back and forth in the history"""
        self.thistab.history_go(int(relative))

    # TODO: remove this method since it is not used?
    def scroll(self, relative):
        """Scroll down by <relative> lines"""
        if self.ui.browser and self.ui.browser.main_column:
            self.ui.browser.main_column.scroll(relative)
            self.thisfile = self.thisdir.pointed_obj

    def enter_dir(self, path, remember=False, history=True):
        """Enter the directory at the given path"""
        cwd = self.thisdir
        # csh variable is lowercase
        cdpath = os.environ.get('CDPATH', None) or os.environ.get('cdpath', None)
        result = self.thistab.enter_dir(path, history=history)
        if result == 0 and cdpath:
            for p in cdpath.split(':'):
                curpath = os.path.join(p, path)
                if os.path.isdir(curpath):
                    result = self.thistab.enter_dir(curpath, history=history)
                    break
        if cwd != self.thisdir:
            if remember:
                self.bookmarks.remember(cwd)
            self.change_mode('normal')
        return result

    def cd(self, path, remember=True):
        """enter the directory at the given path, remember=True"""
        self.enter_dir(path, remember=remember)

    def traverse(self):
        self.change_mode('normal')
        cf = self.thisfile
        cwd = self.thisdir
        if cf is not None and cf.is_directory:
            self.enter_dir(cf.path)
        elif cwd.pointer >= len(cwd) - 1:
            while True:
                self.move(left=1)
                cwd = self.thisdir
                if cwd.pointer < len(cwd) - 1:
                    break
                if cwd.path == '/':
                    break
            self.move(down=1)
            self.traverse()
        else:
            self.move(down=1)
            self.traverse()

    # --------------------------
    # -- Shortcuts / Wrappers
    # --------------------------

    def pager_move(self, narg=None, **kw):
        self.ui.get_pager().move(narg=narg, **kw)

    def taskview_move(self, narg=None, **kw):
        self.ui.taskview.move(narg=narg, **kw)

    def pause_tasks(self):
        self.loader.pause(-1)

    def pager_close(self):
        if self.ui.pager.visible:
            self.ui.close_pager()
        if self.ui.browser.pager.visible:
            self.ui.close_embedded_pager()

    def taskview_open(self):
        self.ui.open_taskview()

    def taskview_close(self):
        self.ui.close_taskview()

    def execute_command(self, cmd, **kw):
        return self.run(cmd, **kw)

    def edit_file(self, file=None):
        """Calls execute_file with the current file and label='editor'"""
        if file is None:
            file = self.thisfile
        elif isinstance(file, str):
            file = File(os.path.expanduser(file))
        if file is None:
            return
        self.execute_file(file, label='editor')

    def toggle_option(self, string):
        """Toggle a boolean option named <string>"""
        if isinstance(self.settings[string], bool):
            self.settings[string] ^= True

    def set_option(self, optname, value):
        """Set the value of an option named <optname>"""
        self.settings[optname] = value

    def sort(self, func=None, reverse=None):
        if reverse is not None:
            self.settings['sort_reverse'] = bool(reverse)

        if func is not None:
            self.settings['sort'] = str(func)

    def set_filter(self, fltr):
        try:
            self.thisdir.filter = fltr
        except:
            pass

    def mark_files(self, all=False, toggle=False, val=None, movedown=None, narg=None):
        """A wrapper for the directory.mark_xyz functions.

        Arguments:
        all - change all files of the current directory at once?
        toggle - toggle the marked-status?
        val - mark or unmark?
        """

        if self.thisdir is None:
            return

        cwd = self.thisdir

        if not cwd.accessible:
            return

        if movedown is None:
            movedown = not all

        if val is None and toggle is False:
            return

        if narg == None:
            narg = 1
        else:
            all = False

        if all:
            if toggle:
                cwd.toggle_all_marks()
            else:
                cwd.mark_all(val)
            if self.mode == 'visual':
                self.change_mode('normal')
        else:
            for i in range(cwd.pointer, min(cwd.pointer + narg, len(cwd))):
                item = cwd.files[i]
                if item is not None:
                    if toggle:
                        cwd.toggle_mark(item)
                    else:
                        cwd.mark_item(item, val)

        if movedown:
            self.move(down=narg)

        self.ui.redraw_main_column()
        self.ui.status.need_redraw = True

    def mark_in_direction(self, val=True, dirarg=None):
        cwd = self.thisdir
        direction = Direction(dirarg)
        pos, selected = direction.select(lst=cwd.files, current=cwd.pointer,
                pagesize=self.ui.termsize[0])
        cwd.pointer = pos
        cwd.correct_pointer()
        for item in selected:
            cwd.mark_item(item, val)

    # --------------------------
    # -- Searching
    # --------------------------

    def search_file(self, text, offset=1, regexp=True):
        if isinstance(text, str) and regexp:
            try:
                text = re.compile(text, re.L | re.U | re.I)
            except:
                return False
        self.thistab.last_search = text
        self.search_next(order='search', offset=offset)

    def search_next(self, order=None, offset=1, forward=True):
        original_order = order

        if order is None:
            order = self.search_method
        else:
            self.set_search_method(order=order)

        if order in ('search', 'tag'):
            if order == 'search':
                arg = self.thistab.last_search
                if arg is None:
                    return False
                if hasattr(arg, 'search'):
                    fnc = lambda x: arg.search(x.basename)
                else:
                    fnc = lambda x: arg in x.basename
            elif order == 'tag':
                fnc = lambda x: x.realpath in self.tags

            return self.thisdir.search_fnc(fnc=fnc, offset=offset, forward=forward)

        elif order in ('size', 'mimetype', 'ctime', 'mtime', 'atime'):
            cwd = self.thisdir
            if original_order is not None or not cwd.cycle_list:
                lst = list(cwd.files)
                if order == 'size':
                    fnc = lambda item: -item.size
                elif order == 'mimetype':
                    fnc = lambda item: item.mimetype or ''
                elif order == 'ctime':
                    fnc = lambda item: -int(item.stat and item.stat.st_ctime)
                elif order == 'atime':
                    fnc = lambda item: -int(item.stat and item.stat.st_atime)
                elif order == 'mtime':
                    fnc = lambda item: -int(item.stat and item.stat.st_mtime)
                lst.sort(key=fnc)
                cwd.set_cycle_list(lst)
                return cwd.cycle(forward=None)

            return cwd.cycle(forward=forward)

    def set_search_method(self, order, forward=True):
        if order in ('search', 'tag', 'size', 'mimetype', 'ctime',
                'mtime', 'atime'):
            self.search_method = order

    # --------------------------
    # -- Tags
    # --------------------------
    # Tags are saved in ~/.config/ranger/tagged and simply mark if a
    # file is important to you in any context.

    def tag_toggle(self, paths=None, value=None, movedown=None, tag=None):
        if not self.tags:
            return
        if paths is None:
            tags = tuple(x.realpath for x in self.thistab.get_selection())
        else:
            tags = [realpath(path) for path in paths]
        if value is True:
            self.tags.add(*tags, tag=tag or self.tags.default_tag)
        elif value is False:
            self.tags.remove(*tags)
        else:
            self.tags.toggle(*tags, tag=tag or self.tags.default_tag)

        if movedown is None:
            movedown = len(tags) == 1 and paths is None
        if movedown:
            self.move(down=1)

        self.ui.redraw_main_column()

    def tag_remove(self, paths=None, movedown=None):
        self.tag_toggle(paths=paths, value=False, movedown=movedown)

    def tag_add(self, paths=None, movedown=None):
        self.tag_toggle(paths=paths, value=True, movedown=movedown)

    # --------------------------
    # -- Bookmarks
    # --------------------------
    # Using ranger.container.bookmarks.

    def enter_bookmark(self, key):
        """Enter the bookmark with the name <key>"""
        try:
            self.bookmarks.update_if_outdated()
            destination = self.bookmarks[str(key)]
            cwd = self.thisdir
            if destination.path != cwd.path:
                self.bookmarks.enter(str(key))
                self.bookmarks.remember(cwd)
        except KeyError:
            pass

    def set_bookmark(self, key):
        """Set the bookmark with the name <key> to the current directory"""
        self.bookmarks.update_if_outdated()
        self.bookmarks[str(key)] = self.thisdir

    def unset_bookmark(self, key):
        """Delete the bookmark with the name <key>"""
        self.bookmarks.update_if_outdated()
        self.bookmarks.delete(str(key))

    def draw_bookmarks(self):
        self.ui.browser.draw_bookmarks = True

    def hide_bookmarks(self):
        self.ui.browser.draw_bookmarks = False

    def draw_possible_programs(self):
        try:
            target = self.thistab.get_selection()[0]
        except:
            self.ui.browser.draw_info = []
            return
        programs = self.rifle.list_commands([target.path], None)
        programs = ['%s | %s' % program[0:2] for program in programs]
        self.ui.browser.draw_info = programs

    def hide_console_info(self):
        self.ui.browser.draw_info = False

    # --------------------------
    # -- Pager
    # --------------------------
    # These commands open the built-in pager and set specific sources.

    def display_command_help(self, console_widget):
        try:
            command = console_widget._get_cmd_class()
        except:
            self.notify("Feature not available!", bad=True)
            return

        if not command:
            self.notify("Command not found!", bad=True)
            return

        if not command.__doc__:
            self.notify("Command has no docstring. Try using python without -OO",
                    bad=True)
            return

        pager = self.ui.open_pager()
        lines = cleandoc(command.__doc__).split('\n')
        pager.set_source(lines)

    def display_help(self):
        manualpath = self.relpath('../doc/ranger.1')
        if os.path.exists(manualpath):
            process = self.run(['man', manualpath])
            if process.poll() != 16:
                return
        process = self.run(['man', 'ranger'])
        if process.poll() == 16:
            self.notify("Could not find manpage.", bad=True)

    def display_log(self):
        pager = self.ui.open_pager()
        if self.log:
            pager.set_source(["Message Log:"] + list(self.log))
        else:
            pager.set_source(["Message Log:", "No messages!"])

    def display_file(self):
        if not self.thisfile or not self.thisfile.is_file:
            return

        pager = self.ui.open_pager()
        if self.settings.preview_images and self.thisfile.image:
            pager.set_image(self.thisfile.realpath)
        else:
            f = self.thisfile.get_preview_source(pager.wid, pager.hei)
            if self.thisfile.is_image_preview():
                pager.set_image(f)
            else:
                pager.set_source(f)

    # --------------------------
    # -- Previews
    # --------------------------
    def update_preview(self, path):
        try:
            del self.previews[path]
            self.ui.need_redraw = True
        except:
            return False

    if version_info[0] == 3:
        def sha1_encode(self, path):
            return os.path.join(ranger.CACHEDIR,
                    sha1(path.encode('utf-8')).hexdigest()) + '.jpg'
    else:
        def sha1_encode(self, path):
            return os.path.join(ranger.CACHEDIR,
                    sha1(path).hexdigest()) + '.jpg'

    def get_preview(self, file, width, height):
        pager = self.ui.get_pager()
        path = file.realpath

        if self.settings.preview_images and file.image:
            pager.set_image(path)
            return None

        if self.settings.preview_script and self.settings.use_preview_script:
            # self.previews is a 2 dimensional dict:
            # self.previews['/tmp/foo.jpg'][(80, 24)] = "the content..."
            # self.previews['/tmp/foo.jpg']['loading'] = False
            # A -1 in tuples means "any"; (80, -1) = wid. of 80 and any hei.
            # The key 'foundpreview' is added later. Values in (True, False)
            # XXX: Previews can break when collapse_preview is on and the
            # preview column is popping out as you move the cursor on e.g. a
            # PDF file.
            try:
                data = self.previews[path]
            except:
                data = self.previews[path] = {'loading': False}
            else:
                if data['loading']:
                    return None


            found = data.get((-1, -1), data.get((width, -1),
                data.get((-1, height), data.get((width, height), False))))
            if found == False:
                try:
                    stat_ = os.stat(self.settings.preview_script)
                except:
                    self.fm.notify("Preview Script `%s' doesn't exist!" %
                            self.settings.preview_script, bad=True)
                    return None

                if not stat_.st_mode & S_IEXEC:
                    self.fm.notify("Preview Script `%s' is not executable!" %
                            self.settings.preview_script, bad=True)
                    return None

                data['loading'] = True

                cacheimg = os.path.join(ranger.CACHEDIR, self.sha1_encode(path))
                if (os.path.isfile(cacheimg) and os.path.getmtime(cacheimg) > os.path.getmtime(path)):
                    data['foundpreview'] = True
                    data['imagepreview'] = True
                    pager.set_image(cacheimg)
                    data['loading'] = False
                    return cacheimg

                loadable = CommandLoader(args=[self.settings.preview_script,
                    path, str(width), str(height), cacheimg], read=True,
                    silent=True, descr="Getting preview of %s" % path)
                def on_after(signal):
                    exit = signal.process.poll()
                    content = signal.loader.stdout_buffer
                    data['foundpreview'] = True
                    if exit == 0:
                        data[(width, height)] = content
                    elif exit == 3:
                        data[(-1, height)] = content
                    elif exit == 4:
                        data[(width, -1)] = content
                    elif exit == 5:
                        data[(-1, -1)] = content
                    elif exit == 6:
                        data['imagepreview'] = True
                    elif exit == 1:
                        data[(-1, -1)] = None
                        data['foundpreview'] = False
                    elif exit == 2:
                        f = codecs.open(path, 'r', errors='ignore')
                        try:
                            data[(-1, -1)] = f.read(1024 * 32)
                        except UnicodeDecodeError:
                            f.close()
                            f = codecs.open(path, 'r', encoding='latin-1',
                                    errors='ignore')
                            data[(-1, -1)] = f.read(1024 * 32)
                        f.close()
                    else:
                        data[(-1, -1)] = None
                    if self.thisfile and self.thisfile.realpath == path:
                        self.ui.browser.need_redraw = True
                    data['loading'] = False
                    pager = self.ui.get_pager()
                    if self.thisfile and self.thisfile.is_file:
                        if 'imagepreview' in data:
                            pager.set_image(cacheimg)
                            return cacheimg
                        else:
                            pager.set_source(self.thisfile.get_preview_source(
                                pager.wid, pager.hei))
                def on_destroy(signal):
                    try:
                        del self.previews[path]
                    except:
                        pass
                loadable.signal_bind('after', on_after)
                loadable.signal_bind('destroy', on_destroy)
                self.loader.add(loadable)
                return None
            else:
                return found
        else:
            try:
                return codecs.open(path, 'r', errors='ignore')
            except:
                return None

    # --------------------------
    # -- Tabs
    # --------------------------
    def tab_open(self, name, path=None):
        tab_has_changed = (name != self.current_tab)
        self.current_tab = name
        previous_tab = self.thistab
        try:
            tab = self.tabs[name]
        except KeyError:
            # create a new tab
            tab = Tab(self.thistab.path)
            self.tabs[name] = tab
            self.thistab = tab
            tab.enter_dir(tab.path, history=False)
            if path:
                tab.enter_dir(path, history=True)
            if previous_tab:
                tab.inherit_history(previous_tab.history)
        else:
            self.thistab = tab
            if path:
                tab.enter_dir(path, history=True)
            else:
                tab.enter_dir(tab.path, history=False)

        if tab_has_changed:
            self.change_mode('normal')
            self.signal_emit('tab.change', old=previous_tab, new=self.thistab)

    def tab_close(self, name=None):
        if name is None:
            name = self.current_tab
        tab = self.tabs[name]
        if name == self.current_tab:
            direction = -1 if name == self._get_tab_list()[-1] else 1
            previous = self.current_tab
            self.tab_move(direction)
            if previous == self.current_tab:
                return  # can't close last tab
        if name in self.tabs:
            del self.tabs[name]
        self.restorable_tabs.append(tab)

    def tab_restore(self):
        # NOTE: The name of the tab is not restored.
        previous_tab = self.thistab
        if self.restorable_tabs:
            tab = self.restorable_tabs.pop()
            for name in range(1, len(self.tabs) + 2):
                if not name in self.tabs:
                    self.current_tab = name
                    self.tabs[name] = tab
                    tab.enter_dir(tab.path, history=False)
                    self.thistab = tab
                    self.change_mode('normal')
                    self.signal_emit('tab.change', old=previous_tab,
                            new=self.thistab)
                    break

    def tab_move(self, offset, narg=None):
        if narg:
            return self.tab_open(narg)
        assert isinstance(offset, int)
        tablist = self._get_tab_list()
        current_index = tablist.index(self.current_tab)
        newtab = tablist[(current_index + offset) % len(tablist)]
        if newtab != self.current_tab:
            self.tab_open(newtab)

    def tab_new(self, path=None, narg=None):
        if narg:
            return self.tab_open(narg, path)
        for i in range(1, 10):
            if not i in self.tabs:
                return self.tab_open(i, path)

    def _get_tab_list(self):
        assert len(self.tabs) > 0, "There must be >=1 tabs at all times"
        return sorted(self.tabs)

    # --------------------------
    # -- Overview of internals
    # --------------------------

    def dump_keybindings(self, *contexts):
        if not contexts:
            contexts = 'browser', 'console', 'pager', 'taskview'

        temporary_file = tempfile.NamedTemporaryFile()
        def write(string):
            temporary_file.write(string.encode('utf-8'))

        def recurse(before, pointer):
            for key, value in pointer.items():
                keys = before + [key]
                if isinstance(value, dict):
                    recurse(keys, value)
                else:
                    write("%12s %s\n" % (construct_keybinding(keys), value))

        for context in contexts:
            write("Keybindings in `%s'\n" % context)
            if context in self.fm.ui.keymaps:
                recurse([], self.fm.ui.keymaps[context])
            else:
                write("  None\n")
            write("\n")

        temporary_file.flush()
        pager = os.environ.get('PAGER', ranger.DEFAULT_PAGER)
        self.run([pager, temporary_file.name])

    def dump_commands(self):
        temporary_file = tempfile.NamedTemporaryFile()
        def write(string):
            temporary_file.write(string.encode('utf-8'))

        undocumented = []
        for cmd_name in sorted(self.commands.commands):
            cmd = self.commands.commands[cmd_name]
            if hasattr(cmd, '__doc__') and cmd.__doc__:
                write(cleandoc(cmd.__doc__))
                write("\n\n" + "-" * 60 + "\n")
            else:
                undocumented.append(cmd)

        if undocumented:
            write("Undocumented commands:\n\n")
            for cmd in undocumented:
                write("    :%s\n" % cmd.get_name())

        temporary_file.flush()
        pager = os.environ.get('PAGER', ranger.DEFAULT_PAGER)
        self.run([pager, temporary_file.name])

    def dump_settings(self):
        temporary_file = tempfile.NamedTemporaryFile()
        def write(string):
            temporary_file.write(string.encode('utf-8'))

        for setting in sorted(ALLOWED_SETTINGS):
            write("%30s = %s\n" % (setting, getattr(self.settings, setting)))

        temporary_file.flush()
        pager = os.environ.get('PAGER', ranger.DEFAULT_PAGER)
        self.run([pager, temporary_file.name])

    # --------------------------
    # -- File System Operations
    # --------------------------

    def uncut(self):
        self.copy_buffer = set()
        self.do_cut = False
        self.ui.browser.main_column.request_redraw()

    def copy(self, mode='set', narg=None, dirarg=None):
        """Copy the selected items.  Modes are: 'set', 'add', 'remove'."""
        assert mode in ('set', 'add', 'remove')
        cwd = self.thisdir
        if not narg and not dirarg:
            selected = (f for f in self.thistab.get_selection() if f in cwd.files)
        else:
            if not dirarg and narg:
                direction = Direction(down=1)
                offset = 0
            else:
                direction = Direction(dirarg)
                offset = 1
            pos, selected = direction.select(
                    override=narg, lst=cwd.files, current=cwd.pointer,
                    pagesize=self.ui.termsize[0], offset=offset)
            cwd.pointer = pos
            cwd.correct_pointer()
        if mode == 'set':
            self.copy_buffer = set(selected)
        elif mode == 'add':
            self.copy_buffer.update(set(selected))
        elif mode == 'remove':
            self.copy_buffer.difference_update(set(selected))
        self.do_cut = False
        self.ui.browser.main_column.request_redraw()

    def cut(self, mode='set', narg=None, dirarg=None):
        self.copy(mode=mode, narg=narg, dirarg=dirarg)
        self.do_cut = True
        self.ui.browser.main_column.request_redraw()

    def paste_symlink(self, relative=False):
        copied_files = self.copy_buffer
        for f in copied_files:
            self.notify(next_available_filename(f.basename))
            try:
                new_name = next_available_filename(f.basename)
                if relative:
                    relative_symlink(f.path, join(getcwd(), new_name))
                else:
                    symlink(f.path, join(getcwd(), new_name))
            except Exception as x:
                self.notify(x)

    def paste_hardlink(self):
        for f in self.copy_buffer:
            try:
                new_name = next_available_filename(f.basename)
                link(f.path, join(getcwd(), new_name))
            except Exception as x:
                self.notify(x)

    def paste_hardlinked_subtree(self):
        for f in self.copy_buffer:
            try:
                target_path = join(getcwd(), f.basename)
                self._recurse_hardlinked_tree(f.path, target_path)
            except Exception as x:
                self.notify(x)

    def _recurse_hardlinked_tree(self, source_path, target_path):
        if isdir(source_path):
            if not exists(target_path):
                os.mkdir(target_path, stat(source_path).st_mode)
            for item in listdir(source_path):
                self._recurse_hardlinked_tree(
                    join(source_path, item),
                    join(target_path, item))
        else:
            if not exists(target_path) \
            or stat(source_path).st_ino != stat(target_path).st_ino:
                link(source_path,
                    next_available_filename(target_path))

    def paste(self, overwrite=False):
        """Paste the selected items into the current directory"""
        self.loader.add(CopyLoader(self.copy_buffer, self.do_cut, overwrite))
        self.do_cut = False

    def delete(self):
        # XXX: warn when deleting mount points/unseen marked files?
        self.notify("Deleting!")
        selected = self.thistab.get_selection()
        self.copy_buffer -= set(selected)
        if selected:
            for f in selected:
                if isdir(f.path) and not os.path.islink(f.path):
                    try:
                        shutil.rmtree(f.path)
                    except OSError as err:
                        self.notify(err)
                else:
                    try:
                        os.remove(f.path)
                    except OSError as err:
                        self.notify(err)
        self.thistab.ensure_correct_pointer()

    def mkdir(self, name):
        try:
            os.mkdir(os.path.join(self.thisdir.path, name))
        except OSError as err:
            self.notify(err)

    def rename(self, src, dest):
        if hasattr(src, 'path'):
            src = src.path

        try:
            os.renames(src, dest)
        except OSError as err:
            self.notify(err)

########NEW FILE########
__FILENAME__ = environment
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

# THIS WHOLE FILE IS OBSOLETE AND EXISTS FOR BACKWARDS COMPATIBILITIY

import os
from ranger.ext.signals import SignalDispatcher
from ranger.core.shared import SettingsAware, FileManagerAware

# COMPAT
class Environment(SettingsAware, FileManagerAware, SignalDispatcher):
    def __init__(self, path):
        SignalDispatcher.__init__(self)

    def _get_copy(self): return self.fm.copy_buffer
    def _set_copy(self, obj): self.fm.copy_buffer = obj
    copy = property(_get_copy, _set_copy)

    def _get_cut(self): return self.fm.do_cut
    def _set_cut(self, obj): self.fm.do_cut = obj
    cut = property(_get_cut, _set_cut)

    def _get_keymaps(self): return self.fm.ui.keymaps
    def _set_keymaps(self, obj): self.fm.ui.keymaps = obj
    keymaps = property(_get_keymaps, _set_keymaps)

    def _get_keybuffer(self): return self.fm.ui.keybuffer
    def _set_keybuffer(self, obj): self.fm.ui.keybuffer = obj
    keybuffer = property(_get_keybuffer, _set_keybuffer)

    def _get_username(self): return self.fm.username
    def _set_username(self, obj): self.fm.username = obj
    username = property(_get_username, _set_username)

    def _get_hostname(self): return self.fm.hostname
    def _set_hostname(self, obj): self.fm.hostname = obj
    hostname = property(_get_hostname, _set_hostname)

    def _get_home_path(self): return self.fm.home_path
    def _set_home_path(self, obj): self.fm.home_path = obj
    home_path = property(_get_home_path, _set_home_path)

    def _get_get_directory(self): return self.fm.get_directory
    def _set_get_directory(self, obj): self.fm.get_directory = obj
    get_directory = property(_get_get_directory, _set_get_directory)

    def _get_garbage_collect(self): return self.fm.garbage_collect
    def _set_garbage_collect(self, obj): self.fm.garbage_collect = obj
    garbage_collect = property(_get_garbage_collect, _set_garbage_collect)

    def _get_cwd(self): return self.fm.thisdir
    def _set_cwd(self, obj): self.fm.thisdir = obj
    cwd = property(_get_cwd, _set_cwd)

    def _get_cf(self): return self.fm.thisfile
    def _set_cf(self, obj): self.fm.thisfile = obj
    cf = property(_get_cf, _set_cf)

    def _get_history(self): return self.fm.thistab.history
    def _set_history(self, obj): self.fm.thistab.history = obj
    history = property(_get_history, _set_history)

    def _get_last_search(self): return self.fm.thistab.last_search
    def _set_last_search(self, obj): self.fm.thistab.last_search = obj
    last_search = property(_get_last_search, _set_last_search)

    def _get_path(self): return self.fm.thistab.path
    def _set_path(self, obj): self.fm.thistab.path = obj
    path = property(_get_path, _set_path)

    def _get_pathway(self): return self.fm.thistab.pathway
    def _set_pathway(self, obj): self.fm.thistab.pathway = obj
    pathway = property(_get_pathway, _set_pathway)

    def _get_enter_dir(self): return self.fm.thistab.enter_dir
    def _set_enter_dir(self, obj): self.fm.thistab.enter_dir = obj
    enter_dir = property(_get_enter_dir, _set_enter_dir)

    def _get_at_level(self): return self.fm.thistab.at_level
    def _set_at_level(self, obj): self.fm.thistab.at_level = obj
    at_level = property(_get_at_level, _set_at_level)

    def _get_get_selection(self): return self.fm.thistab.get_selection
    def _set_get_selection(self, obj): self.fm.thistab.get_selection = obj
    get_selection = property(_get_get_selection, _set_get_selection)

    def _get_assign_cursor_positions_for_subdirs(self):
        return self.fm.thistab.assign_cursor_positions_for_subdirs
    def _set_assign_cursor_positions_for_subdirs(self, obj):
        self.fm.thistab.assign_cursor_positions_for_subdirs = obj
    assign_cursor_positions_for_subdirs = property(
            _get_assign_cursor_positions_for_subdirs,
            _set_assign_cursor_positions_for_subdirs)

    def _get_ensure_correct_pointer(self):
        return self.fm.thistab.ensure_correct_pointer
    def _set_ensure_correct_pointer(self, obj):
        self.fm.thistab.ensure_correct_pointer = obj
    ensure_correct_pointer = property(_get_ensure_correct_pointer,
            _set_ensure_correct_pointer)

    def _get_history_go(self): return self.fm.thistab.history_go
    def _set_history_go(self, obj): self.fm.thistab.history_go = obj
    history_go = property(_get_history_go, _set_history_go)

    def _set_cf_from_signal(self, signal):
        self.fm._cf = signal.new

    def get_free_space(self, path):
        stat = os.statvfs(path)
        return stat.f_bavail * stat.f_frsize

########NEW FILE########
__FILENAME__ = fm
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""The File Manager, putting the pieces together"""

from time import time
from collections import deque
import mimetypes
import os.path
import pwd
import socket
import stat
import sys

import ranger.api
from ranger.core.actions import Actions
from ranger.core.tab import Tab
from ranger.container.tags import Tags
from ranger.gui.ui import UI
from ranger.container.bookmarks import Bookmarks
from ranger.core.runner import Runner
from ranger.ext.img_display import ImageDisplayer
from ranger.ext.rifle import Rifle
from ranger.container.directory import Directory
from ranger.ext.signals import SignalDispatcher
from ranger import __version__
from ranger.core.loader import Loader

class FM(Actions, SignalDispatcher):
    input_blocked = False
    input_blocked_until = 0
    mode = 'normal'  # either 'normal' or 'visual'.
    search_method = 'ctime'

    _previous_selection = None
    _visual_reverse = False
    _visual_start = None
    _visual_start_pos = None

    def __init__(self, ui=None, bookmarks=None, tags=None, paths=['.']):
        """Initialize FM."""
        Actions.__init__(self)
        SignalDispatcher.__init__(self)
        if ui is None:
            self.ui = UI()
        else:
            self.ui = ui
        self.start_paths = paths
        self.directories = dict()
        self.log = deque(maxlen=20)
        self.image_displayer = ImageDisplayer()
        self.bookmarks = bookmarks
        self.current_tab = 1
        self.tabs = {}
        self.tags = tags
        self.restorable_tabs = deque([], ranger.MAX_RESTORABLE_TABS)
        self.py3 = sys.version_info >= (3, )
        self.previews = {}
        self.loader = Loader()
        self.copy_buffer = set()
        self.do_cut = False

        try:
            self.username = pwd.getpwuid(os.geteuid()).pw_name
        except:
            self.username = 'uid:' + str(os.geteuid())
        self.hostname = socket.gethostname()
        self.home_path = os.path.expanduser('~')

        self.log.append('ranger {0} started! Process ID is {1}.' \
                .format(__version__, os.getpid()))
        self.log.append('Running on Python ' + sys.version.replace('\n',''))

        mimetypes.knownfiles.append(os.path.expanduser('~/.mime.types'))
        mimetypes.knownfiles.append(self.relpath('data/mime.types'))
        self.mimetypes = mimetypes.MimeTypes()

    def initialize(self):
        """If ui/bookmarks are None, they will be initialized here."""

        self.tabs = dict((n+1, Tab(path)) for n, path in
                enumerate(self.start_paths))
        tab_list = self._get_tab_list()
        if tab_list:
            self.current_tab = tab_list[0]
            self.thistab = self.tabs[self.current_tab]
        else:
            self.current_tab = 1
            self.tabs[self.current_tab] = self.thistab = Tab('.')

        if not ranger.arg.clean and os.path.isfile(self.confpath('rifle.conf')):
            rifleconf = self.confpath('rifle.conf')
        else:
            rifleconf = self.relpath('config/rifle.conf')
        self.rifle = Rifle(rifleconf)
        self.rifle.reload_config()

        if self.bookmarks is None:
            if ranger.arg.clean:
                bookmarkfile = None
            else:
                bookmarkfile = self.confpath('bookmarks')
            self.bookmarks = Bookmarks(
                    bookmarkfile=bookmarkfile,
                    bookmarktype=Directory,
                    autosave=self.settings.autosave_bookmarks)
            self.bookmarks.load()

        if not ranger.arg.clean and self.tags is None:
            self.tags = Tags(self.confpath('tagged'))

        self.ui.setup_curses()
        self.ui.initialize()

        self.rifle.hook_before_executing = lambda a, b, flags: \
            self.ui.suspend() if 'f' not in flags else None
        self.rifle.hook_after_executing = lambda a, b, flags: \
            self.ui.initialize() if 'f' not in flags else None
        self.rifle.hook_logger = self.notify

        # This hook allows image viewers to open all images in the current
        # directory, keeping the order of files the same as in ranger.
        # The requirements to use it are:
        # 1. set open_all_images to true
        # 2. ensure no files are marked
        # 3. call rifle with a command that starts with "sxiv " or "feh "
        def sxiv_workaround_hook(command):
            import re
            from ranger.ext.shell_escape import shell_quote

            if self.settings.open_all_images and \
                    len(self.thisdir.marked_items) == 0 and \
                    re.match(r'^(feh|sxiv) ', command):

                images = [f.basename for f in self.thisdir.files if f.image]
                escaped_filenames = " ".join(shell_quote(f) \
                        for f in images if "\x00" not in f)

                if images and self.thisfile.basename in images and \
                        "$@" in command:
                    new_command = None

                    if command[0:5] == 'sxiv ':
                        number = images.index(self.thisfile.basename) + 1
                        new_command = command.replace("sxiv ",
                                "sxiv -n %d " % number, 1)

                    if command[0:4] == 'feh ':
                        new_command = command.replace("feh ",
                            "feh --start-at %s " % \
                            shell_quote(self.thisfile.basename), 1)

                    if new_command:
                        command = "set -- %s; %s" % (escaped_filenames,
                                new_command)
            return command

        self.rifle.hook_command_preprocessing = sxiv_workaround_hook

        def mylogfunc(text):
            self.notify(text, bad=True)
        self.run = Runner(ui=self.ui, logfunc=mylogfunc, fm=self)

    def destroy(self):
        debug = ranger.arg.debug
        if self.ui:
            try:
                self.ui.destroy()
            except:
                if debug:
                    raise
        if self.loader:
            try:
                self.loader.destroy()
            except:
                if debug:
                    raise

    def _get_thisfile(self):
        return self.thistab.thisfile

    def _set_thisfile(self, obj):
        self.thistab.thisfile = obj

    def _get_thisdir(self):
        return self.thistab.thisdir

    def _set_thisdir(self, obj):
        self.thistab.thisdir = obj

    thisfile = property(_get_thisfile, _set_thisfile)
    thisdir  = property(_get_thisdir,  _set_thisdir)

    def block_input(self, sec=0):
        self.input_blocked = sec != 0
        self.input_blocked_until = time() + sec

    def input_is_blocked(self):
        if self.input_blocked and time() > self.input_blocked_until:
            self.input_blocked = False
        return self.input_blocked

    def copy_config_files(self, which):
        if ranger.arg.clean:
            sys.stderr.write("refusing to copy config files in clean mode\n")
            return
        import shutil
        from errno import EEXIST
        def copy(_from, to):
            if os.path.exists(self.confpath(to)):
                sys.stderr.write("already exists: %s\n" % self.confpath(to))
            else:
                sys.stderr.write("creating: %s\n" % self.confpath(to))
                try:
                    os.makedirs(ranger.arg.confdir)
                except OSError as err:
                    if err.errno != EEXIST:  # EEXIST means it already exists
                        print("This configuration directory could not be created:")
                        print(ranger.arg.confdir)
                        print("To run ranger without the need for configuration")
                        print("files, use the --clean option.")
                        raise SystemExit()
                try:
                    shutil.copy(self.relpath(_from), self.confpath(to))
                except Exception as e:
                    sys.stderr.write("  ERROR: %s\n" % str(e))
        if which == 'rifle' or which == 'all':
            copy('config/rifle.conf', 'rifle.conf')
        if which == 'commands' or which == 'all':
            copy('config/commands.py', 'commands.py')
        if which == 'rc' or which == 'all':
            copy('config/rc.conf', 'rc.conf')
        if which == 'scope' or which == 'all':
            copy('data/scope.sh', 'scope.sh')
            os.chmod(self.confpath('scope.sh'),
                os.stat(self.confpath('scope.sh')).st_mode | stat.S_IXUSR)
        if which in ('all', 'rifle', 'scope', 'commands', 'rc'):
            sys.stderr.write("\nPlease note that configuration files may "
                "change as ranger evolves.\nIt's completely up to you to keep "
                "them up to date.\n")
        else:
            sys.stderr.write("Unknown config file `%s'\n" % which)

    def confpath(self, *paths):
        """returns the path relative to rangers configuration directory"""
        if ranger.arg.clean:
            assert 0, "Should not access relpath_conf in clean mode!"
        else:
            return os.path.join(ranger.arg.confdir, *paths)

    def relpath(self, *paths):
        """returns the path relative to rangers library directory"""
        return os.path.join(ranger.RANGERDIR, *paths)

    def get_directory(self, path):
        """Get the directory object at the given path"""
        path = os.path.abspath(path)
        try:
            return self.directories[path]
        except KeyError:
            obj = Directory(path)
            self.directories[path] = obj
            return obj

    def garbage_collect(self, age, tabs=None):  # tabs=None is for COMPATibility
        """Delete unused directory objects"""
        for key in tuple(self.directories):
            value = self.directories[key]
            if age != -1:
                if not value.is_older_than(age) \
                        or any(value in tab.pathway for tab in self.tabs.values()):
                    continue
            del self.directories[key]
            if value.is_directory:
                value.files = None
        self.settings.signal_garbage_collect()
        self.signal_garbage_collect()

    def loop(self):
        """The main loop of ranger.

        It consists of:
        1. reloading bookmarks if outdated
        2. letting the loader work
        3. drawing and finalizing ui
        4. reading and handling user input
        5. after X loops: collecting unused directory objects
        """

        self.enter_dir(self.thistab.path)

        gc_tick = 0

        # for faster lookup:
        ui = self.ui
        throbber = ui.throbber
        loader = self.loader
        has_throbber = hasattr(ui, 'throbber')
        zombies = self.run.zombies

        ranger.api.hook_ready(self)

        try:
            while True:
                loader.work()
                if has_throbber:
                    if loader.has_work():
                        throbber(loader.status)
                    else:
                        throbber(remove=True)

                ui.redraw()

                ui.set_load_mode(not loader.paused and loader.has_work())

                ui.draw_images()

                ui.handle_input()

                if zombies:
                    for zombie in tuple(zombies):
                        if zombie.poll() is not None:
                            zombies.remove(zombie)

                #gc_tick += 1
                #if gc_tick > ranger.TICKS_BEFORE_COLLECTING_GARBAGE:
                    #gc_tick = 0
                    #self.garbage_collect(ranger.TIME_BEFORE_FILE_BECOMES_GARBAGE)

        except KeyboardInterrupt:
            # this only happens in --debug mode. By default, interrupts
            # are caught in curses_interrupt_handler
            raise SystemExit

        finally:
            self.image_displayer.quit()
            if ranger.arg.choosedir and self.thisdir and self.thisdir.path:
                # XXX: UnicodeEncodeError: 'utf-8' codec can't encode character
                # '\udcf6' in position 42: surrogates not allowed
                open(ranger.arg.choosedir, 'w').write(self.thisdir.path)
            self.bookmarks.remember(self.thisdir)
            self.bookmarks.save()

########NEW FILE########
__FILENAME__ = loader
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

from collections import deque
from time import time, sleep
from subprocess import Popen, PIPE
from ranger.core.shared import FileManagerAware
from ranger.ext.signals import SignalDispatcher
import math
import os.path
import sys
import select
try:
    import chardet
    HAVE_CHARDET = True
except:
    HAVE_CHARDET = False

class Loadable(object):
    paused = False
    progressbar_supported = False
    def __init__(self, gen, descr):
        self.load_generator = gen
        self.description = descr
        self.percent = 0

    def get_description(self):
        return self.description

    def pause(self):
        self.paused = True

    def unpause(self):
        try:
            del self.paused
        except:
            pass

    def destroy(self):
        pass


class CopyLoader(Loadable, FileManagerAware):
    progressbar_supported = True
    def __init__(self, copy_buffer, do_cut=False, overwrite=False):
        self.copy_buffer = tuple(copy_buffer)
        self.do_cut = do_cut
        self.original_copy_buffer = copy_buffer
        self.original_path = self.fm.thistab.path
        self.overwrite = overwrite
        self.percent = 0
        if self.copy_buffer:
            self.one_file = self.copy_buffer[0]
        Loadable.__init__(self, self.generate(), 'Calculating size...')

    def _calculate_size(self, step):
        from os.path import join
        size = 0
        stack = [f.path for f in self.copy_buffer]
        while stack:
            fname = stack.pop()
            if os.path.isdir(fname):
                stack.extend([join(fname, item) for item in os.listdir(fname)])
            else:
                try:
                    fstat = os.stat(fname)
                except:
                    continue
                size += max(step, math.ceil(fstat.st_size / step) * step)
        return size

    def generate(self):
        from ranger.ext import shutil_generatorized as shutil_g
        if self.copy_buffer:
            # TODO: Don't calculate size when renaming (needs detection)
            bytes_per_tick = shutil_g.BLOCK_SIZE
            size = max(1, self._calculate_size(bytes_per_tick))
            bar_tick = 100.0 / (float(size) / bytes_per_tick)
            if self.do_cut:
                self.original_copy_buffer.clear()
                if len(self.copy_buffer) == 1:
                    self.description = "moving: " + self.one_file.path
                else:
                    self.description = "moving files from: " + self.one_file.dirname
                for f in self.copy_buffer:
                    for _ in shutil_g.move(src=f.path,
                            dst=self.original_path,
                            overwrite=self.overwrite):
                        self.percent += bar_tick
                        yield
            else:
                if len(self.copy_buffer) == 1:
                    self.description = "copying: " + self.one_file.path
                else:
                    self.description = "copying files from: " + self.one_file.dirname
                for f in self.copy_buffer:
                    if os.path.isdir(f.path):
                        for _ in shutil_g.copytree(src=f.path,
                                dst=os.path.join(self.original_path, f.basename),
                                symlinks=True,
                                overwrite=self.overwrite):
                            self.percent += bar_tick
                            yield
                    else:
                        for _ in shutil_g.copy2(f.path, self.original_path,
                                symlinks=True,
                                overwrite=self.overwrite):
                            self.percent += bar_tick
                            yield
            cwd = self.fm.get_directory(self.original_path)
            cwd.load_content()


class CommandLoader(Loadable, SignalDispatcher, FileManagerAware):
    """Run an external command with the loader.

    Output from stderr will be reported.  Ensure that the process doesn't
    ever ask for input, otherwise the loader will be blocked until this
    object is removed from the queue (type ^C in ranger)
    """
    finished = False
    process = None
    def __init__(self, args, descr, silent=False, read=False, input=None,
            kill_on_pause=False):
        SignalDispatcher.__init__(self)
        Loadable.__init__(self, self.generate(), descr)
        self.args = args
        self.silent = silent
        self.read = read
        self.stdout_buffer = ""
        self.input = input
        self.kill_on_pause = kill_on_pause

    def generate(self):
        py3 = sys.version >= '3'
        if self.input:
            stdin = PIPE
        else:
            stdin = open(os.devnull, 'r')
        self.process = process = Popen(self.args,
                stdout=PIPE, stderr=PIPE, stdin=stdin)
        self.signal_emit('before', process=process, loader=self)
        if self.input:
            if py3:
                import io
                stdin = io.TextIOWrapper(process.stdin)
            else:
                stdin = process.stdin
            try:
                stdin.write(self.input)
            except IOError as e:
                if e.errno != errno.EPIPE and e.errno != errno.EINVAL:
                    raise
            stdin.close()
        if self.silent and not self.read:
            while process.poll() is None:
                yield
                if self.finished:
                    break
                sleep(0.03)
        else:
            selectlist = []
            if self.read:
                selectlist.append(process.stdout)
            if not self.silent:
                selectlist.append(process.stderr)
            while process.poll() is None:
                yield
                if self.finished:
                    break
                try:
                    rd, _, __ = select.select(selectlist, [], [], 0.03)
                    if rd:
                        rd = rd[0]
                        if rd == process.stderr:
                            read = rd.readline()
                            if py3:
                                read = safeDecode(read)
                            if read:
                                self.fm.notify(read, bad=True)
                        elif rd == process.stdout:
                            read = rd.read(512)
                            if py3:
                                read = safeDecode(read)
                            if read:
                                self.stdout_buffer += read
                except select.error:
                    sleep(0.03)
            if not self.silent:
                for l in process.stderr.readlines():
                    if py3:
                        l = safeDecode(l)
                    self.fm.notify(l, bad=True)
            if self.read:
                read = process.stdout.read()
                if py3:
                    read = safeDecode(read)
                self.stdout_buffer += read
        self.finished = True
        self.signal_emit('after', process=process, loader=self)

    def pause(self):
        if not self.finished and not self.paused:
            if self.kill_on_pause:
                self.finished = True
                try:
                    self.process.kill()
                except OSError:
                    # probably a race condition where the process finished
                    # between the last poll()ing and this point.
                    pass
                return
            try:
                self.process.send_signal(20)
            except:
                pass
            Loadable.pause(self)
            self.signal_emit('pause', process=self.process, loader=self)

    def unpause(self):
        if not self.finished and self.paused:
            try:
                self.process.send_signal(18)
            except:
                pass
            Loadable.unpause(self)
            self.signal_emit('unpause', process=self.process, loader=self)

    def destroy(self):
        self.signal_emit('destroy', process=self.process, loader=self)
        if self.process:
            try:
                self.process.kill()
            except OSError:
                pass


def safeDecode(string):
    try:
        return string.decode("utf-8")
    except (UnicodeDecodeError):
        if HAVE_CHARDET:
            return string.decode(chardet.detect(string)["encoding"])
        else:
            return ""


class Loader(FileManagerAware):
    seconds_of_work_time = 0.03
    throbber_chars = r'/-\|'
    throbber_paused = '#'
    paused = False

    def __init__(self):
        self.queue = deque()
        self.item = None
        self.load_generator = None
        self.throbber_status = 0
        self.rotate()
        self.old_item = None

    def rotate(self):
        """Rotate the throbber"""
        # TODO: move all throbber logic to UI
        self.throbber_status = \
            (self.throbber_status + 1) % len(self.throbber_chars)
        self.status = self.throbber_chars[self.throbber_status]

    def add(self, obj):
        """Add an object to the queue.

        It should have a load_generator method.
        """
        while obj in self.queue:
            self.queue.remove(obj)
        self.queue.appendleft(obj)
        if self.paused:
            obj.pause()
        else:
            obj.unpause()

    def move(self, _from, to):
        try:
            item = self.queue[_from]
        except IndexError:
            return

        del self.queue[_from]

        if to == 0:
            self.queue.appendleft(item)
            if _from != 0:
                self.queue[1].pause()
        elif to == -1:
            self.queue.append(item)
        else:
            raise NotImplementedError

    def remove(self, item=None, index=None):
        if item is not None and index is None:
            for i, test in enumerate(self.queue):
                if test == item:
                    index = i
                    break
            else:
                return

        if index is not None:
            if item is None:
                item = self.queue[index]
            if hasattr(item, 'unload'):
                item.unload()
            item.destroy()
            del self.queue[index]
            if item.progressbar_supported:
                self.fm.ui.status.request_redraw()

    def pause(self, state):
        """Change the pause-state to 1 (pause), 0 (no pause) or -1 (toggle)"""
        if state == -1:
            state = not self.paused
        elif state == self.paused:
            return

        self.paused = state

        if not self.queue:
            return

        if state:
            self.queue[0].pause()
        else:
            self.queue[0].unpause()

    def work(self):
        """Load items from the queue if there are any.

        Stop after approximately self.seconds_of_work_time.
        """
        if self.paused:
            self.status = self.throbber_paused
            return

        while True:
            # get the first item with a proper load_generator
            try:
                item = self.queue[0]
                if item.load_generator is None:
                    self.queue.popleft()
                else:
                    break
            except IndexError:
                return

        item.unpause()

        self.rotate()
        if item != self.old_item:
            if self.old_item:
                self.old_item.pause()
            self.old_item = item
        item.unpause()

        end_time = time() + self.seconds_of_work_time

        try:
            while time() < end_time:
                next(item.load_generator)
            if item.progressbar_supported:
                self.fm.ui.status.request_redraw()
        except StopIteration:
            self._remove_current_process(item)
        except Exception as err:
            self.fm.notify(err)
            self._remove_current_process(item)

    def _remove_current_process(self, item):
        item.load_generator = None
        self.queue.remove(item)
        if item.progressbar_supported:
            self.fm.ui.status.request_redraw()

    def has_work(self):
        """Is there anything to load?"""
        return bool(self.queue)

    def destroy(self):
        while self.queue:
            self.queue.pop().destroy()

########NEW FILE########
__FILENAME__ = main
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""The main function responsible to initialize the FM object and stuff."""

import os.path
import sys

def main():
    """initialize objects and run the filemanager"""
    import locale
    import ranger.api
    from ranger.container.settings import Settings
    from ranger.core.shared import FileManagerAware, SettingsAware
    from ranger.core.fm import FM

    if not sys.stdin.isatty():
        sys.stderr.write("Error: Must run ranger from terminal\n")
        raise SystemExit(1)

    try:
        locale.setlocale(locale.LC_ALL, '')
    except:
        print("Warning: Unable to set locale.  Expect encoding problems.")

    # so that programs can know that ranger spawned them:
    level = 'RANGER_LEVEL'
    if level in os.environ and os.environ[level].isdigit():
        os.environ[level] = str(int(os.environ[level]) + 1)
    else:
        os.environ[level] = '1'

    if not 'SHELL' in os.environ:
        os.environ['SHELL'] = 'sh'

    ranger.arg = arg = parse_arguments()
    if arg.copy_config is not None:
        fm = FM()
        fm.copy_config_files(arg.copy_config)
        return 1 if arg.fail_unless_cd else 0 # COMPAT
    if arg.list_tagged_files:
        fm = FM()
        try:
            f = open(fm.confpath('tagged'), 'r')
        except:
            pass
        else:
            for line in f.readlines():
                if len(line) > 2 and line[1] == ':':
                    if line[0] in arg.list_tagged_files:
                        sys.stdout.write(line[2:])
                elif len(line) > 0 and '*' in arg.list_tagged_files:
                    sys.stdout.write(line)
        return 1 if arg.fail_unless_cd else 0 # COMPAT

    SettingsAware._setup(Settings())

    if arg.selectfile:
        arg.selectfile = os.path.abspath(arg.selectfile)
        arg.targets.insert(0, os.path.dirname(arg.selectfile))

    targets = arg.targets or ['.']
    target = targets[0]
    if arg.targets:  # COMPAT
        if target.startswith('file://'):
            target = target[7:]
        if not os.access(target, os.F_OK):
            print("File or directory doesn't exist: %s" % target)
            return 1
        elif os.path.isfile(target):
            sys.stderr.write("Warning: Using ranger as a file launcher is "
                   "deprecated.\nPlease use the standalone file launcher "
                   "'rifle' instead.\n")
            def print_function(string):
                print(string)
            from ranger.ext.rifle import Rifle
            fm = FM()
            if not arg.clean and os.path.isfile(fm.confpath('rifle.conf')):
                rifleconf = fm.confpath('rifle.conf')
            else:
                rifleconf = fm.relpath('config/rifle.conf')
            rifle = Rifle(rifleconf)
            rifle.reload_config()
            rifle.execute(targets, number=ranger.arg.mode, flags=ranger.arg.flags)
            return 1 if arg.fail_unless_cd else 0 # COMPAT

    crash_traceback = None
    try:
        # Initialize objects
        fm = FM(paths=targets)
        FileManagerAware._setup(fm)
        load_settings(fm, arg.clean)

        if arg.list_unused_keys:
            from ranger.ext.keybinding_parser import (special_keys,
                    reversed_special_keys)
            maps = fm.ui.keymaps['browser']
            for key in sorted(special_keys.values(), key=lambda x: str(x)):
                if key not in maps:
                    print("<%s>" % reversed_special_keys[key])
            for key in range(33, 127):
                if key not in maps:
                    print(chr(key))
            return 1 if arg.fail_unless_cd else 0 # COMPAT

        if fm.username == 'root':
            fm.settings.preview_files = False
            fm.settings.use_preview_script = False
        if not arg.debug:
            from ranger.ext import curses_interrupt_handler
            curses_interrupt_handler.install_interrupt_handler()

        # Create cache directory
        if fm.settings.preview_images and fm.settings.use_preview_script:
            from ranger import CACHEDIR
            if not os.path.exists(CACHEDIR):
                os.makedirs(CACHEDIR)

        # Run the file manager
        fm.initialize()
        ranger.api.hook_init(fm)
        fm.ui.initialize()

        if arg.selectfile:
            fm.select_file(arg.selectfile)

        if arg.cmd:
            for command in arg.cmd:
                fm.execute_console(command)

        if ranger.arg.profile:
            import cProfile
            import pstats
            profile = None
            ranger.__fm = fm
            cProfile.run('ranger.__fm.loop()', '/tmp/ranger_profile')
            profile = pstats.Stats('/tmp/ranger_profile', stream=sys.stderr)
        else:
            fm.loop()
    except Exception:
        import traceback
        crash_traceback = traceback.format_exc()
    except SystemExit as error:
        return error.args[0]
    finally:
        if crash_traceback:
            try:
                filepath = fm.thisfile.path if fm.thisfile else "None"
            except:
                filepath = "None"
        try:
            fm.ui.destroy()
        except (AttributeError, NameError):
            pass
        if ranger.arg.profile and profile:
            profile.strip_dirs().sort_stats('cumulative').print_callees()
        if crash_traceback:
            print("ranger version: %s, executed with python %s" %
                    (ranger.__version__, sys.version.split()[0]))
            print("Locale: %s" % '.'.join(str(s) for s in locale.getlocale()))
            try:
                print("Current file: %s" % filepath)
            except:
                pass
            print(crash_traceback)
            print("ranger crashed.  " \
                "Please report this traceback at:")
            print("http://savannah.nongnu.org/bugs/?group=ranger&func=additem")
            return 1
        return 0


def parse_arguments():
    """Parse the program arguments"""
    from optparse import OptionParser, SUPPRESS_HELP
    from os.path import expanduser
    from ranger import CONFDIR, USAGE, VERSION
    from ranger.ext.openstruct import OpenStruct

    if 'XDG_CONFIG_HOME' in os.environ and os.environ['XDG_CONFIG_HOME']:
        default_confdir = os.environ['XDG_CONFIG_HOME'] + '/ranger'
    else:
        default_confdir = CONFDIR

    parser = OptionParser(usage=USAGE, version=VERSION)

    parser.add_option('-d', '--debug', action='store_true',
            help="activate debug mode")
    parser.add_option('-c', '--clean', action='store_true',
            help="don't touch/require any config files. ")
    parser.add_option('-r', '--confdir', type='string',
            metavar='dir', default=default_confdir,
            help="change the configuration directory. (%default)")
    parser.add_option('--copy-config', type='string', metavar='which',
            help="copy the default configs to the local config directory. "
            "Possible values: all, rc, rifle, commands, scope")
    parser.add_option('--fail-unless-cd', action='store_true',
            help=SUPPRESS_HELP)  # COMPAT
    parser.add_option('-m', '--mode', type='int', default=0, metavar='n',
            help=SUPPRESS_HELP)  # COMPAT
    parser.add_option('-f', '--flags', type='string', default='',
            metavar='string', help=SUPPRESS_HELP)  # COMPAT
    parser.add_option('--choosefile', type='string', metavar='TARGET',
            help="Makes ranger act like a file chooser. When opening "
            "a file, it will quit and write the name of the selected "
            "file to TARGET.")
    parser.add_option('--choosefiles', type='string', metavar='TARGET',
            help="Makes ranger act like a file chooser for multiple files "
            "at once. When opening a file, it will quit and write the name "
            "of all selected files to TARGET.")
    parser.add_option('--choosedir', type='string', metavar='TARGET',
            help="Makes ranger act like a directory chooser. When ranger quits"
            ", it will write the name of the last visited directory to TARGET")
    parser.add_option('--selectfile', type='string', metavar='filepath',
            help="Open ranger with supplied file selected.")
    parser.add_option('--list-unused-keys', action='store_true',
            help="List common keys which are not bound to any action.")
    parser.add_option('--list-tagged-files', type='string', default=None,
            metavar='tag',
            help="List all files which are tagged with the given tag, default: *")
    parser.add_option('--profile', action='store_true',
            help="Print statistics of CPU usage on exit.")
    parser.add_option('--cmd', action='append', type='string', metavar='COMMAND',
            help="Execute COMMAND after the configuration has been read. "
            "Use this option multiple times to run multiple commands.")

    options, positional = parser.parse_args()
    arg = OpenStruct(options.__dict__, targets=positional)
    arg.confdir = expanduser(arg.confdir)

    if arg.fail_unless_cd: # COMPAT
        sys.stderr.write("Warning: The option --fail-unless-cd is deprecated.\n"
            "It was used to faciliate using ranger as a file launcher.\n"
            "Now, please use the standalone file launcher 'rifle' instead.\n")

    return arg


def load_settings(fm, clean):
    from ranger.core.actions import Actions
    import ranger.core.shared
    import ranger.api.commands
    from ranger.config import commands

    # Load default commands
    fm.commands = ranger.api.commands.CommandContainer()
    exclude = ['settings']
    include = [name for name in dir(Actions) if name not in exclude]
    fm.commands.load_commands_from_object(fm, include)
    fm.commands.load_commands_from_module(commands)

    if not clean:
        allow_access_to_confdir(ranger.arg.confdir, True)

        # Load custom commands
        if os.path.exists(fm.confpath('commands.py')):
            try:
                import commands
                fm.commands.load_commands_from_module(commands)
            except ImportError:
                pass

        allow_access_to_confdir(ranger.arg.confdir, False)

        # Load rc.conf
        custom_conf = fm.confpath('rc.conf')
        default_conf = fm.relpath('config', 'rc.conf')

        if os.environ.get('RANGER_LOAD_DEFAULT_RC', 0) != 'FALSE':
            fm.source(default_conf)
        if os.access(custom_conf, os.R_OK):
            fm.source(custom_conf)

        allow_access_to_confdir(ranger.arg.confdir, True)

        # XXX Load plugins (experimental)
        try:
            plugindir = fm.confpath('plugins')
            plugins = [p[:-3] for p in os.listdir(plugindir) \
                    if p.endswith('.py') and not p.startswith('_')]
        except:
            pass
        else:
            if not os.path.exists(fm.confpath('plugins', '__init__.py')):
                f = open(fm.confpath('plugins', '__init__.py'), 'w')
                f.close()

            ranger.fm = fm
            for plugin in sorted(plugins):
                try:
                    module = __import__('plugins', fromlist=[plugin])
                    fm.log.append("Loaded plugin '%s'." % plugin)
                except Exception as e:
                    fm.log.append("Error in plugin '%s'" % plugin)
                    import traceback
                    for line in traceback.format_exception_only(type(e), e):
                        fm.log.append(line)
            ranger.fm = None

        # COMPAT: Load the outdated options.py
        # options.py[oc] are deliberately ignored
        if os.path.exists(fm.confpath("options.py")):
            module = __import__('options')
            from ranger.container.settings import ALLOWED_SETTINGS
            for setting in ALLOWED_SETTINGS:
                if hasattr(module, setting):
                    fm.settings[setting] = getattr(module, setting)

            sys.stderr.write(
"""******************************
Warning: The configuration file 'options.py' is deprecated.
Please move all settings to the file 'rc.conf', converting lines like
    "preview_files = False"
to
    "set preview_files false"
If you had python code in the options.py that you'd like to keep, simply
copy & paste it to a .py file in ~/.config/ranger/plugins/.
Remove the options.py or discard stderr to get rid of this warning.
******************************\n""")

        allow_access_to_confdir(ranger.arg.confdir, False)
    else:
        fm.source(fm.relpath('config', 'rc.conf'))


def allow_access_to_confdir(confdir, allow):
    import sys
    from errno import EEXIST

    if allow:
        try:
            os.makedirs(confdir)
        except OSError as err:
            if err.errno != EEXIST:  # EEXIST means it already exists
                print("This configuration directory could not be created:")
                print(confdir)
                print("To run ranger without the need for configuration")
                print("files, use the --clean option.")
                raise SystemExit()
        if not confdir in sys.path:
            sys.path[0:0] = [confdir]
    else:
        if sys.path[0] == confdir:
            del sys.path[0]

########NEW FILE########
__FILENAME__ = runner
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""This module is an abstract layer over subprocess.Popen

It gives you highlevel control about how processes are run.

Example:
run = Runner(logfunc=print)
run('sleep 2', wait=True)         # waits until the process exists
run(['ls', '--help'], flags='p')  # pipes output to pager
run()                             # prints an error message

List of allowed flags:
s: silent mode. output will be discarded.
f: fork the process.
p: redirect output to the pager
c: run only the current file (not handled here)
w: wait for enter-press afterwards
r: run application with root privilege (requires sudo)
t: run application in a new terminal window
(An uppercase key negates the respective lower case flag)
"""

import os
import sys
from subprocess import Popen, PIPE
from ranger.ext.get_executables import get_executables
from ranger.ext.popen_forked import Popen_forked


# TODO: Remove unused parts of runner.py
#ALLOWED_FLAGS = 'sdpwcrtSDPWCRT'
ALLOWED_FLAGS = 'cfrtCFRT'


def press_enter():
    """Wait for an ENTER-press"""
    sys.stdout.write("Press ENTER to continue")
    try:
        waitfnc = raw_input
    except NameError:
        # "raw_input" not available in python3
        waitfnc = input
    waitfnc()


class Context(object):
    """A context object contains data on how to run a process.

    The attributes are:
    action -- a string with a command or a list of arguments for
        the Popen call.
    app -- the name of the app function. ("vim" for app_vim.)
        app is used to get an action if the user didn't specify one.
    mode -- a number, mainly used in determining the action in app_xyz()
    flags -- a string with flags which change the way programs are run
    files -- a list containing files, mainly used in app_xyz
    file -- an arbitrary file from that list (or None)
    fm -- the filemanager instance
    wait -- boolean, wait for the end or execute programs in parallel?
    popen_kws -- keyword arguments which are directly passed to Popen
    """

    def __init__(self, **keywords):
        self.__dict__ = keywords

    @property
    def filepaths(self):
        try:
            return [f.path for f in self.files]
        except:
            return []

    def __iter__(self):
        """Iterate over file paths"""
        for item in self.filepaths:
            yield item

    def squash_flags(self):
        """Remove duplicates and lowercase counterparts of uppercase flags"""
        for flag in self.flags:
            if ord(flag) <= 90:
                bad = flag + flag.lower()
                self.flags = ''.join(c for c in self.flags if c not in bad)


class Runner(object):
    def __init__(self, ui=None, logfunc=None, fm=None):
        self.ui = ui
        self.fm = fm
        self.logfunc = logfunc
        self.zombies = set()

    def _log(self, text):
        try:
            self.logfunc(text)
        except TypeError:
            pass
        return False

    def _activate_ui(self, boolean):
        if self.ui is not None:
            if boolean:
                try: self.ui.initialize()
                except: self._log("Failed to initialize UI")
            else:
                try: self.ui.suspend()
                except: self._log("Failed to suspend UI")

    def __call__(self, action=None, try_app_first=False,
            app='default', files=None, mode=0,
            flags='', wait=True, **popen_kws):
        """Run the application in the way specified by the options.

        Returns False if nothing can be done, None if there was an error,
        otherwise the process object returned by Popen().

        This function tries to find an action if none is defined.
        """

        # Find an action if none was supplied by
        # creating a Context object and passing it to
        # an Application object.

        context = Context(app=app, files=files, mode=mode, fm=self.fm,
                flags=flags, wait=wait, popen_kws=popen_kws,
                file=files and files[0] or None)

        if action is None:
            return self._log("No way of determining the action!")

        # Preconditions

        context.squash_flags()
        popen_kws = context.popen_kws  # shortcut

        toggle_ui = True
        pipe_output = False
        wait_for_enter = False
        devnull = None

        if 'shell' not in popen_kws:
            popen_kws['shell'] = isinstance(action, str)
        if 'stdout' not in popen_kws:
            popen_kws['stdout'] = sys.stdout
        if 'stderr' not in popen_kws:
            popen_kws['stderr'] = sys.stderr

        # Evaluate the flags to determine keywords
        # for Popen() and other variables

        if 'p' in context.flags:
            popen_kws['stdout'] = PIPE
            popen_kws['stderr'] = PIPE
            toggle_ui = False
            pipe_output = True
            context.wait = False
        if 's' in context.flags:
            devnull_writable = open(os.devnull, 'w')
            devnull_readable = open(os.devnull, 'r')
            for key in ('stdout', 'stderr'):
                popen_kws[key] = devnull_writable
            toggle_ui = False
            popen_kws['stdin'] = devnull_readable
        if 'f' in context.flags:
            toggle_ui = False
            context.wait = False
        if 'w' in context.flags:
            if not pipe_output and context.wait: # <-- sanity check
                wait_for_enter = True
        if 'r' in context.flags:
            # TODO: make 'r' flag work with pipes
            if 'sudo' not in get_executables():
                return self._log("Can not run with 'r' flag, sudo is not installed!")
            f_flag = ('f' in context.flags)
            if isinstance(action, str):
                action = 'sudo ' + (f_flag and '-b ' or '') + action
            else:
                action = ['sudo'] + (f_flag and ['-b'] or []) + action
            toggle_ui = True
            context.wait = True
        if 't' in context.flags:
            if 'DISPLAY' not in os.environ:
                return self._log("Can not run with 't' flag, no display found!")
            term = os.environ.get('TERMCMD', os.environ.get('TERM'))
            if term not in get_executables():
                term = 'x-terminal-emulator'
            if term not in get_executables():
                term = 'xterm'
            if isinstance(action, str):
                action = term + ' -e ' + action
            else:
                action = [term, '-e'] + action
            toggle_ui = False
            context.wait = False

        popen_kws['args'] = action
        # Finally, run it

        if toggle_ui:
            self._activate_ui(False)
        try:
            error = None
            process = None
            self.fm.signal_emit('runner.execute.before',
                    popen_kws=popen_kws, context=context)
            try:
                if 'f' in context.flags:
                    # This can fail and return False if os.fork() is not
                    # supported, but we assume it is, since curses is used.
                    Popen_forked(**popen_kws)
                else:
                    process = Popen(**popen_kws)
            except Exception as e:
                error = e
                self._log("Failed to run: %s\n%s" % (str(action), str(e)))
            else:
                if context.wait:
                    process.wait()
                elif process:
                    self.zombies.add(process)
                if wait_for_enter:
                    press_enter()
        finally:
            self.fm.signal_emit('runner.execute.after',
                    popen_kws=popen_kws, context=context, error=error)
            if devnull:
                devnull.close()
            if toggle_ui:
                self._activate_ui(True)
            if pipe_output and process:
                return self(action='less', app='pager', try_app_first=True,
                        stdin=process.stdout)
            return process

########NEW FILE########
__FILENAME__ = shared
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""Shared objects contain singletons for shared use."""

from ranger.ext.lazy_property import lazy_property

class FileManagerAware(object):
    """Subclass this to gain access to the global "FM" object."""
    @staticmethod
    def _setup(fm):
        FileManagerAware.fm = fm

class SettingsAware(object):
    """Subclass this to gain access to the global "SettingObject" object."""
    @staticmethod
    def _setup(settings):
        SettingsAware.settings = settings

class EnvironmentAware(object):  # COMPAT
    """DO NOT USE.  This is for backward compatibility only."""
    @lazy_property
    def env(self):
        from ranger.core.environment import Environment
        return Environment(".")

########NEW FILE########
__FILENAME__ = tab
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

import os
import sys
from os.path import abspath, normpath, join, expanduser, isdir

from ranger.container.history import History
from ranger.core.shared import FileManagerAware, SettingsAware
from ranger.ext.signals import SignalDispatcher

class Tab(FileManagerAware, SettingsAware):
    def __init__(self, path):
        self.thisdir = None  # Current Working Directory
        self._thisfile = None  # Current File
        self.history = History(self.settings.max_history_size, unique=False)
        self.last_search = None
        self.pointer = 0
        self.path = abspath(expanduser(path))
        self.pathway = ()
        # NOTE: in the line below, weak=True works only in python3.  In python2,
        # weak references are not equal to the original object when tested with
        # "==", and this breaks _set_thisfile_from_signal and _on_tab_change.
        self.fm.signal_bind('move', self._set_thisfile_from_signal, priority=0.1,
                weak=(sys.version > '3'))
        self.fm.signal_bind('tab.change', self._on_tab_change,
                weak=(sys.version > '3'))

    def _set_thisfile_from_signal(self, signal):
        if self == signal.tab:
            self._thisfile = signal.new
            if self == self.fm.thistab:
                self.pointer = self.thisdir.pointer

    def _on_tab_change(self, signal):
        if self == signal.new and self.thisdir:
            # restore the pointer whenever this tab is reopened
            self.thisdir.pointer = self.pointer
            self.thisdir.correct_pointer()

    def _set_thisfile(self, value):
        if value is not self._thisfile:
            previous = self._thisfile
            self.fm.signal_emit('move', previous=previous, new=value, tab=self)

    def _get_thisfile(self):
        return self._thisfile

    thisfile = property(_get_thisfile, _set_thisfile)

    def at_level(self, level):
        """Returns the FileSystemObject at the given level.

        level >0 => previews
        level 0 => current file/directory
        level <0 => parent directories
        """
        if level <= 0:
            try:
                return self.pathway[level - 1]
            except IndexError:
                return None
        else:
            directory = self.thisdir
            for i in range(level):
                if directory is None:
                    return None
                if directory.is_directory:
                    directory = directory.pointed_obj
                else:
                    return None
            return directory

    def get_selection(self):
        if self.thisdir:
            if self.thisdir.marked_items:
                return self.thisdir.get_selection()
            elif self._thisfile:
                return [self._thisfile]
        return []

    def assign_cursor_positions_for_subdirs(self):
        """Assign correct cursor positions for subdirectories"""
        last_path = None
        for path in reversed(self.pathway):
            if last_path is None:
                last_path = path
                continue

            path.move_to_obj(last_path)
            last_path = path

    def ensure_correct_pointer(self):
        if self.thisdir:
            self.thisdir.correct_pointer()

    def history_go(self, relative):
        """Move relative in history"""
        if self.history:
            self.history.move(relative).go(history=False)

    def inherit_history(self, other_history):
        self.history.rebase(other_history)

    def enter_dir(self, path, history = True):
        """Enter given path"""
        # TODO: Ensure that there is always a self.thisdir
        if path is None: return
        path = str(path)

        previous = self.thisdir

        # get the absolute path
        path = normpath(join(self.path, expanduser(path)))

        if not isdir(path):
            return False
        new_thisdir = self.fm.get_directory(path)

        try:
            os.chdir(path)
        except:
            return True
        self.path = path
        self.thisdir = new_thisdir

        self.thisdir.load_content_if_outdated()

        # build the pathway, a tuple of directory objects which lie
        # on the path to the current directory.
        if path == '/':
            self.pathway = (self.fm.get_directory('/'), )
        else:
            pathway = []
            currentpath = '/'
            for dir in path.split('/'):
                currentpath = join(currentpath, dir)
                pathway.append(self.fm.get_directory(currentpath))
            self.pathway = tuple(pathway)

        self.assign_cursor_positions_for_subdirs()

        # set the current file.
        self.thisdir.sort_directories_first = self.fm.settings.sort_directories_first
        self.thisdir.sort_reverse = self.fm.settings.sort_reverse
        self.thisdir.sort_if_outdated()
        if previous and previous.path != path:
            self.thisfile = self.thisdir.pointed_obj
        else:
            # This avoids setting self.pointer (through the 'move' signal) and
            # is required so that you can use enter_dir when switching tabs
            # without messing up the pointer.
            self._thisfile = self.thisdir.pointed_obj

        if history:
            self.history.add(new_thisdir)

        self.fm.signal_emit('cd', previous=previous, new=self.thisdir)

        return True

    def __repr__(self):
        return "<Tab '%s'>" % self.thisdir

########NEW FILE########
__FILENAME__ = accumulator
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

from ranger.ext.direction import Direction

class Accumulator(object):
    def __init__(self):
        self.pointer = 0
        self.pointed_obj = None

    def move(self, narg=None, **keywords):
        direction = Direction(keywords)
        lst = self.get_list()
        if not lst:
            return self.pointer
        pointer = direction.move(
                direction=direction.down(),
                maximum=len(lst),
                override=narg,
                pagesize=self.get_height(),
                current=self.pointer)
        self.pointer = pointer
        self.correct_pointer()
        return pointer

    def move_to_obj(self, arg, attr=None):
        if not arg:
            return

        lst = self.get_list()

        if not lst:
            return

        do_get_attr = isinstance(attr, str)

        good = arg
        if do_get_attr:
            try:
                good = getattr(arg, attr)
            except (TypeError, AttributeError):
                pass

        for obj, i in zip(lst, range(len(lst))):
            if do_get_attr:
                try:
                    test = getattr(obj, attr)
                except AttributeError:
                    continue
            else:
                test = obj

            if test == good:
                self.move(to=i)
                return True

        return self.move(to=self.pointer)

    # XXX Is this still necessary?  move() ensures correct pointer position
    def correct_pointer(self):
        lst = self.get_list()

        if not lst:
            self.pointer = 0
            self.pointed_obj = None

        else:
            i = self.pointer

            if i is None:
                i = 0
            if i >= len(lst):
                i = len(lst) - 1
            if i < 0:
                i = 0

            self.pointer = i
            self.pointed_obj = lst[i]

    def pointer_is_synced(self):
        lst = self.get_list()
        try:
            return lst[self.pointer] == self.pointed_obj
        except (IndexError, KeyError):
            return False

    def sync_index(self, **kw):
        self.move_to_obj(self.pointed_obj, **kw)

    def get_list(self):
        """OVERRIDE THIS"""
        return []

    def get_height(self):
        """OVERRIDE THIS"""
        return 25

########NEW FILE########
__FILENAME__ = cached_function
# Copyright (C) 2012-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

def cached_function(fnc):
    cache = {}
    def inner_cached_function(*args):
        try:
            return cache[args]
        except:
            value = fnc(*args)
            cache[args] = value
            return value
    inner_cached_function._cache = cache
    return inner_cached_function


########NEW FILE########
__FILENAME__ = curses_interrupt_handler
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""Interrupt Signal handler for curses

This module can catch interrupt signals which would otherwise
rise a KeyboardInterrupt exception and handle it by pushing
a Ctrl+C (ASCII value 3) to the curses getch stack.
"""

import curses
import signal

_do_catch_interrupt = True

def catch_interrupt(boolean=True):
    """Should interrupts be caught and simulate a ^C press in curses?"""
    global _do_catch_interrupt
    old_value = _do_catch_interrupt
    _do_catch_interrupt = bool(boolean)
    return old_value

# The handler which will be used in signal.signal()
def _interrupt_handler(a1, a2):
    global _do_catch_interrupt
    # if a keyboard-interrupt occurs...
    if _do_catch_interrupt:
        # push a Ctrl+C (ascii value 3) to the curses getch stack
        curses.ungetch(3)
    else:
        # use the default handler
        signal.default_int_handler(a1, a2)

def install_interrupt_handler():
    """Install the custom interrupt_handler"""
    signal.signal(signal.SIGINT, _interrupt_handler)

def restore_interrupt_handler():
    """Restore the default_int_handler"""
    signal.signal(signal.SIGINT, signal.default_int_handler)

########NEW FILE########
__FILENAME__ = direction
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""This class provides convenient methods for movement operations.

Direction objects are handled just like dicts but provide
methods like up() and down() which give you the correct value
for the vertical direction, even if only the "up" or "down" key
has been defined.


>>> d = Direction(down=5)
>>> d.down()
5
>>> d.up()
-5
>>> bool(d.horizontal())
False
"""

class Direction(dict):
    def __init__(self, dictionary=None, **keywords):
        if dictionary is not None:
            dict.__init__(self, dictionary)
        else:
            dict.__init__(self, keywords)
        if 'to' in self:
            self['down'] = self['to']
            self['absolute'] = True

    def copy(self):
        return Direction(**self)

    def _get_bool(self, first, second, fallback=None):
        try: return self[first]
        except:
            try: return not self[second]
            except: return fallback

    def _get_direction(self, first, second, fallback=0):
        try: return self[first]
        except:
            try: return -self[second]
            except: return fallback

    def up(self):
        return -Direction.down(self)

    def down(self):
        return Direction._get_direction(self, 'down', 'up')

    def right(self):
        return Direction._get_direction(self, 'right', 'left')

    def absolute(self):
        return Direction._get_bool(self, 'absolute', 'relative')

    def left(self):
        return -Direction.right(self)

    def relative(self):
        return not Direction.absolute(self)

    def vertical_direction(self):
        down = Direction.down(self)
        return (down > 0) - (down < 0)

    def horizontal_direction(self):
        right = Direction.right(self)
        return (right > 0) - (right < 0)

    def vertical(self):
        return set(self) & set(['up', 'down'])

    def horizontal(self):
        return set(self) & set(['left', 'right'])

    def pages(self):
        return 'pages' in self and self['pages']

    def percentage(self):
        return 'percentage' in self and self['percentage']

    def multiply(self, n):
        for key in ('up', 'right', 'down', 'left'):
            try:
                self[key] *= n
            except:
                pass

    def set(self, n):
        for key in ('up', 'right', 'down', 'left'):
            if key in self:
                self[key] = n

    def move(self, direction, override=None, minimum=0, maximum=9999,
            current=0, pagesize=1, offset=0):
        """Calculates the new position in a given boundary.

        Example:
        >>> d = Direction(pages=True)
        >>> d.move(direction=3)
        3
        >>> d.move(direction=3, current=2)
        5
        >>> d.move(direction=3, pagesize=5)
        15
        >>> # Note: we start to count at zero.
        >>> d.move(direction=3, pagesize=5, maximum=10)
        9
        >>> d.move(direction=9, override=2)
        18
        """
        pos = direction
        if override is not None:
            if self.absolute():
                pos = override
            else:
                pos *= override
        if self.pages():
            pos *= pagesize
        elif self.percentage():
            pos *= maximum / 100.0
        if self.absolute():
            if pos < minimum:
                pos += maximum
        else:
            pos += current
        return int(max(min(pos, maximum + offset - 1), minimum))

    def select(self, lst, current, pagesize, override=None, offset=1):
        dest = self.move(direction=self.down(), override=override,
            current=current, pagesize=pagesize, minimum=0, maximum=len(lst)+1)
        selection = lst[min(current, dest):max(current, dest) + offset]
        return dest + offset - 1, selection

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = get_executables
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

from stat import S_IXOTH, S_IFREG
from ranger.ext.iter_tools import unique
from os import listdir, environ, stat


_cached_executables = None


def get_executables():
    """Return all executable files in $PATH. Cached version."""
    global _cached_executables
    if _cached_executables is None:
        _cached_executables = get_executables_uncached()
    return _cached_executables


def get_executables_uncached(*paths):
    """Return all executable files in each of the given directories.

    Looks in $PATH by default.
    """
    if not paths:
        try:
            pathstring = environ['PATH']
        except KeyError:
            return ()
        paths = unique(pathstring.split(':'))

    executables = set()
    for path in paths:
        try:
            content = listdir(path)
        except:
            continue
        for item in content:
            abspath = path + '/' + item
            try:
                filestat = stat(abspath)
            except:
                continue
            if filestat.st_mode & (S_IXOTH | S_IFREG):
                executables.add(item)
    return executables


########NEW FILE########
__FILENAME__ = human_readable
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

def human_readable(byte, separator=' '):
    """Convert a large number of bytes to an easily readable format.

    >>> human_readable(54)
    '54 B'
    >>> human_readable(1500)
    '1.46 K'
    >>> human_readable(2 ** 20 * 1023)
    '1023 M'
    """

    # I know this can be written much shorter, but this long version
    # performs much better than what I had before.  If you attempt to
    # shorten this code, take performance into consideration.
    if byte <= 0:
        return '0'
    if byte < 2**10:
        return '%d%sB'   % (byte, separator)
    if byte < 2**10 * 999:
        return '%.3g%sK' % (byte / 2**10.0, separator)
    if byte < 2**20:
        return '%.4g%sK' % (byte / 2**10.0, separator)
    if byte < 2**20 * 999:
        return '%.3g%sM' % (byte / 2**20.0, separator)
    if byte < 2**30:
        return '%.4g%sM' % (byte / 2**20.0, separator)
    if byte < 2**30 * 999:
        return '%.3g%sG' % (byte / 2**30.0, separator)
    if byte < 2**40:
        return '%.4g%sG' % (byte / 2**30.0, separator)
    if byte < 2**40 * 999:
        return '%.3g%sT' % (byte / 2**40.0, separator)
    if byte < 2**50:
        return '%.4g%sT' % (byte / 2**40.0, separator)
    if byte < 2**50 * 999:
        return '%.3g%sP' % (byte / 2**50.0, separator)
    if byte < 2**60:
        return '%.4g%sP' % (byte / 2**50.0, separator)
    return '>9000'

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = img_display
# This software is distributed under the terms of the GNU GPL version 3.

"""Interface for w3mimgdisplay to draw images into the console

This module provides functions to draw images in the terminal using
w3mimgdisplay, an utilitary program from w3m (a text-based web browser).
w3mimgdisplay can display images either in virtual tty (using linux
framebuffer) or in a Xorg session.

w3m need to be installed for this to work.
"""

import fcntl
import os
import select
import struct
import sys
import termios
from subprocess import Popen, PIPE

W3MIMGDISPLAY_PATH = '/usr/lib/w3m/w3mimgdisplay'
W3MIMGDISPLAY_OPTIONS = []

class ImgDisplayUnsupportedException(Exception):
    pass


class ImageDisplayer(object):
    is_initialized = False

    def initialize(self):
        """start w3mimgdisplay"""
        self.binary_path = os.environ.get("W3MIMGDISPLAY_PATH", None)
        if not self.binary_path:
            self.binary_path = W3MIMGDISPLAY_PATH
        self.process = Popen([self.binary_path] + W3MIMGDISPLAY_OPTIONS,
                stdin=PIPE, stdout=PIPE, universal_newlines=True)
        self.is_initialized = True

    def draw(self, path, start_x, start_y, width, height):
        """Draw an image at the given coordinates."""
        if not self.is_initialized or self.process.poll() is not None:
            self.initialize()
        self.process.stdin.write(self._generate_w3m_input(path, start_x,
            start_y, width, height))
        self.process.stdin.flush()
        self.process.stdout.readline()

    def clear(self, start_x, start_y, width, height):
        """Clear a part of terminal display."""
        if not self.is_initialized or self.process.poll() is not None:
            self.initialize()

        fontw, fonth = _get_font_dimensions()

        cmd = "6;{x};{y};{w};{h}\n4;\n3;\n".format(
                x = start_x * fontw,
                y = start_y * fonth,
                w = (width + 1) * fontw,
                h = height * fonth)

        self.process.stdin.write(cmd)
        self.process.stdin.flush()
        self.process.stdout.readline()

    def _generate_w3m_input(self, path, start_x, start_y, max_width, max_height):
        """Prepare the input string for w3mimgpreview

        start_x, start_y, max_height and max_width specify the drawing area.
        They are expressed in number of characters.
        """
        fontw, fonth = _get_font_dimensions()
        if fontw == 0 or fonth == 0:
            raise ImgDisplayUnsupportedException()

        max_width_pixels = max_width * fontw
        max_height_pixels = max_height * fonth

        # get image size
        cmd = "5;{}\n".format(path)

        self.process.stdin.write(cmd)
        self.process.stdin.flush()
        output = self.process.stdout.readline().split()

        if len(output) != 2:
            raise Exception('Failed to execute w3mimgdisplay', output)

        width = int(output[0])
        height = int(output[1])

        # get the maximum image size preserving ratio
        if width > max_width_pixels:
            height = (height * max_width_pixels) // width
            width = max_width_pixels
        if height > max_height_pixels:
            width = (width * max_height_pixels) // height
            height = max_height_pixels

        return "0;1;{x};{y};{w};{h};;;;;{filename}\n4;\n3;\n".format(
                x = start_x * fontw,
                y = start_y * fonth,
                w = width,
                h = height,
                filename = path)

    def quit(self):
        if self.is_initialized:
            self.process.kill()


def _get_font_dimensions():
    # Get the height and width of a character displayed in the terminal in
    # pixels.
    s = struct.pack("HHHH", 0, 0, 0, 0)
    fd_stdout = sys.stdout.fileno()
    x = fcntl.ioctl(fd_stdout, termios.TIOCGWINSZ, s)
    rows, cols, xpixels, ypixels = struct.unpack("HHHH", x)
    if xpixels == 0 and ypixels == 0:
        binary_path = os.environ.get("W3MIMGDISPLAY_PATH", None)
        if not binary_path:
            binary_path = W3MIMGDISPLAY_PATH
        process = Popen([binary_path, "-test"],
            stdout=PIPE, universal_newlines=True)
        output, _ = process.communicate()
        output = output.split()
        xpixels, ypixels = int(output[0]), int(output[1])
        # adjust for misplacement
        xpixels += 2
        ypixels += 2

    return (xpixels // cols), (ypixels // rows)

########NEW FILE########
__FILENAME__ = iter_tools
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

from collections import deque

def flatten(lst):
    """Flatten an iterable.

    All contained tuples, lists, deques and sets are replaced by their
    elements and flattened as well.

    >>> l = [1, 2, [3, [4], [5, 6]], 7]
    >>> list(flatten(l))
    [1, 2, 3, 4, 5, 6, 7]
    >>> list(flatten(()))
    []
    """
    for elem in lst:
        if isinstance(elem, (tuple, list, set, deque)):
            for subelem in flatten(elem):
                yield subelem
        else:
            yield elem

def unique(iterable):
    """Return an iterable of the same type which contains unique items.

    This function assumes that:
    type(iterable)(list(iterable)) == iterable
    which is true for tuples, lists and deques (but not for strings)

    >>> unique([1, 2, 3, 1, 2, 3, 4, 2, 3, 4, 1, 1, 2])
    [1, 2, 3, 4]
    >>> unique(('w', 't', 't', 'f', 't', 'w'))
    ('w', 't', 'f')
    """
    already_seen = []
    for item in iterable:
        if item not in already_seen:
            already_seen.append(item)
    return type(iterable)(already_seen)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = keybinding_parser
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

import sys
import copy
import curses.ascii

PY3 = sys.version > '3'
digits = set(range(ord('0'), ord('9')+1))

# Arbitrary numbers which are not used with curses.KEY_XYZ
ANYKEY, PASSIVE_ACTION, ALT_KEY, QUANT_KEY = range(9001, 9005)

special_keys = {
    'bs': curses.KEY_BACKSPACE,
    'backspace': curses.KEY_BACKSPACE,
    'backspace2': curses.ascii.DEL,
    'delete': curses.KEY_DC,
    's-delete': curses.KEY_SDC,
    'insert': curses.KEY_IC,
    'cr': ord("\n"),
    'enter': ord("\n"),
    'return': ord("\n"),
    'space': ord(" "),
    'esc': curses.ascii.ESC,
    'escape': curses.ascii.ESC,
    'down': curses.KEY_DOWN,
    'up': curses.KEY_UP,
    'left': curses.KEY_LEFT,
    'right': curses.KEY_RIGHT,
    'pagedown': curses.KEY_NPAGE,
    'pageup': curses.KEY_PPAGE,
    'home': curses.KEY_HOME,
    'end': curses.KEY_END,
    'tab': ord('\t'),
    's-tab': curses.KEY_BTAB,
}

very_special_keys = {
    'any': ANYKEY,
    'alt': ALT_KEY,
    'bg': PASSIVE_ACTION,
    'allow_quantifiers': QUANT_KEY,
}

for key, val in tuple(special_keys.items()):
    special_keys['a-' + key] = (ALT_KEY, val)

for char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789':
    special_keys['a-' + char] = (ALT_KEY, ord(char))

for char in 'abcdefghijklmnopqrstuvwxyz':
    special_keys['c-' + char] = ord(char) - 96

for n in range(64):
    special_keys['f' + str(n)] = curses.KEY_F0 + n

special_keys.update(very_special_keys)
del very_special_keys
reversed_special_keys = dict((v, k) for k, v in special_keys.items())


def parse_keybinding(obj):
    """Translate a keybinding to a sequence of integers

    >>> tuple(parse_keybinding("lol<CR>"))
    (108, 111, 108, 10)

    >>> out = tuple(parse_keybinding("x<A-Left>"))
    >>> out  # it's kind of dumb that you cant test for constants...
    (120, 9003, 260)
    >>> out[0] == ord('x')
    True
    >>> out[1] == ALT_KEY
    True
    >>> out[2] == curses.KEY_LEFT
    True
    """
    assert isinstance(obj, (tuple, int, str))
    if isinstance(obj, tuple):
        for char in obj:
            yield char
    elif isinstance(obj, int):
        yield obj
    elif isinstance(obj, str):
        in_brackets = False
        bracket_content = None
        for char in obj:
            if in_brackets:
                if char == '>':
                    in_brackets = False
                    string = ''.join(bracket_content).lower()
                    try:
                        keys = special_keys[string]
                        for key in keys:
                            yield key
                    except KeyError:
                        if string.isdigit():
                            yield int(string)
                        else:
                            yield ord('<')
                            for c in bracket_content:
                                yield ord(c)
                            yield ord('>')
                    except TypeError:
                        yield keys  # it was no tuple, just an int
                else:
                    bracket_content.append(char)
            else:
                if char == '<':
                    in_brackets = True
                    bracket_content = []
                else:
                    yield ord(char)
        if in_brackets:
            yield ord('<')
            for c in bracket_content:
                yield ord(c)


def construct_keybinding(iterable):
    """Does the reverse of parse_keybinding"""
    return ''.join(key_to_string(c) for c in iterable)


def key_to_string(key):
    if key in range(33, 127):
        return chr(key)
    if key in reversed_special_keys:
        return "<%s>" % reversed_special_keys[key]
    return "<%s>" % str(key)


def _unbind_traverse(pointer, keys, pos=0):
    if keys[pos] not in pointer:
        return
    if len(keys) > pos+1 and isinstance(pointer, dict):
        _unbind_traverse(pointer[keys[pos]], keys, pos=pos+1)
        if not pointer[keys[pos]]:
            del pointer[keys[pos]]
    elif len(keys) == pos+1:
        try:
            del pointer[keys[pos]]
            keys.pop()
        except:
            pass

class KeyMaps(dict):
    def __init__(self, keybuffer=None):
        dict.__init__(self)
        self.keybuffer = keybuffer
        self.used_keymap = None

    def use_keymap(self, keymap_name):
        self.keybuffer.keymap = self.get(keymap_name, dict())
        if self.used_keymap != keymap_name:
            self.used_keymap = keymap_name
            self.keybuffer.clear()

    def _clean_input(self, context, keys):
        try:
            pointer = self[context]
        except:
            self[context] = pointer = dict()
        if PY3:
            keys = keys.encode('utf-8').decode('latin-1')
        return list(parse_keybinding(keys)), pointer

    def bind(self, context, keys, leaf):
        keys, pointer = self._clean_input(context, keys)
        if not keys:
            return
        last_key = keys[-1]
        for key in keys[:-1]:
            try:
                if isinstance(pointer[key], dict):
                    pointer = pointer[key]
                else:
                    pointer[key] = pointer = dict()
            except:
                pointer[key] = pointer = dict()
        pointer[last_key] = leaf

    def copy(self, context, source, target):
        clean_source, pointer = self._clean_input(context, source)
        if not source:
            return
        for key in clean_source:
            try:
                pointer = pointer[key]
            except:
                raise KeyError("Tried to copy the keybinding `%s',"
                        " but it was not found." % source)
        self.bind(context, target, copy.deepcopy(pointer))

    def unbind(self, context, keys):
        keys, pointer = self._clean_input(context, keys)
        if not keys:
            return
        _unbind_traverse(pointer, keys)


class KeyBuffer(object):
    any_key             = ANYKEY
    passive_key         = PASSIVE_ACTION
    quantifier_key      = QUANT_KEY
    exclude_from_anykey = [27]

    def __init__(self, keymap=None):
        self.keymap = keymap
        self.clear()

    def clear(self):
        self.keys = []
        self.wildcards = []
        self.pointer = self.keymap
        self.result = None
        self.quantifier = None
        self.finished_parsing_quantifier = False
        self.finished_parsing = False
        self.parse_error = False

        if self.keymap and self.quantifier_key in self.keymap:
            if self.keymap[self.quantifier_key] == 'false':
                self.finished_parsing_quantifier = True

    def add(self, key):
        self.keys.append(key)
        self.result = None
        if not self.finished_parsing_quantifier and key in digits:
            if self.quantifier is None:
                self.quantifier = 0
            self.quantifier = self.quantifier * 10 + key - 48 # (48 = ord(0))
        else:
            self.finished_parsing_quantifier = True

            moved = True
            if key in self.pointer:
                self.pointer = self.pointer[key]
            elif self.any_key in self.pointer and \
                    key not in self.exclude_from_anykey:
                self.wildcards.append(key)
                self.pointer = self.pointer[self.any_key]
            else:
                moved = False

            if moved:
                if isinstance(self.pointer, dict):
                    if self.passive_key in self.pointer:
                        self.result = self.pointer[self.passive_key]
                else:
                    self.result = self.pointer
                    self.finished_parsing = True
            else:
                self.finished_parsing = True
                self.parse_error = True

    def __str__(self):
        return "".join(key_to_string(c) for c in self.keys)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = lazy_property
# From http://blog.pythonisito.com/2008/08/lazy-descriptors.html

class lazy_property(object):
    """A @property-like decorator with lazy evaluation

    >>> class Foo:
    ...     @lazy_property
    ...     def answer(self):
    ...         print("calculating answer...")
    ...         return 2*3*7
    >>> foo = Foo()
    >>> foo.answer
    calculating answer...
    42
    >>> foo.answer
    42
    """

    def __init__(self, method):
        self._method = method
        self.__name__ = method.__name__
        self.__doc__ = method.__doc__

    def __get__(self, obj, cls=None):
        if obj is None:  # to fix issues with pydoc
            return None
        result = self._method(obj)
        obj.__dict__[self.__name__] = result
        return result

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = mount_path
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

from os.path import realpath, abspath, dirname, ismount

def mount_path(path):
    """Get the mount root of a directory"""
    path = abspath(realpath(path))
    while path != '/':
        if ismount(path):
            return path
        path = dirname(path)
    return '/'

########NEW FILE########
__FILENAME__ = next_available_filename
# Copyright (C) 2011-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

import os.path

def next_available_filename(fname, directory="."):
    existing_files = os.listdir(directory)

    if fname not in existing_files:
        return fname
    if not fname.endswith("_"):
        fname += "_"
        if fname not in existing_files:
            return fname

    for i in range(1, len(existing_files) + 1):
        if fname + str(i) not in existing_files:
            return fname + str(i)

########NEW FILE########
__FILENAME__ = openstruct
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

# prepend __ to arguments because one might use "args"
# or "keywords" as a keyword argument.

class OpenStruct(dict):
    """The fusion of dict and struct"""
    def __init__(self, *__args, **__keywords):
        dict.__init__(self, *__args, **__keywords)
        self.__dict__ = self

########NEW FILE########
__FILENAME__ = popen_forked
# Copyright (C) 2012-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

import os
import subprocess

def Popen_forked(*args, **kwargs):
    """Forks process and runs Popen with the given args and kwargs.

    Returns True if forking succeeded, otherwise False.
    """
    try:
        pid = os.fork()
    except OSError:
        return False
    if pid == 0:
        os.setsid()
        kwargs['stdin'] = open(os.devnull, 'r')
        kwargs['stdout'] = kwargs['stderr'] = open(os.devnull, 'w')
        subprocess.Popen(*args, **kwargs)
        os._exit(0)
    else:
        os.wait()
    return True

########NEW FILE########
__FILENAME__ = relative_symlink
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

from os import symlink, sep

def relative_symlink(src, dst):
    common_base = get_common_base(src, dst)
    symlink(get_relative_source_file(src, dst, common_base), dst)

def get_relative_source_file(src, dst, common_base=None):
    if common_base is None:
        common_base = get_common_base(src, dst)
    return '../' * dst.count('/', len(common_base)) + src[len(common_base):]

def get_common_base(src, dst):
    if not src or not dst:
        return '/'
    i = 0
    while True:
        new_i = src.find(sep, i + 1)
        if new_i == -1:
            break
        if not dst.startswith(src[:new_i + 1]):
            break
        i = new_i
    return src[:i + 1]

########NEW FILE########
__FILENAME__ = rifle
#!/usr/bin/python
# Copyright (C) 2012-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""rifle, the file executor/opener of ranger

This can be used as a standalone program or can be embedded in python code.
When used together with ranger, it doesn't have to be installed to $PATH.

Example usage:

    rifle = Rifle("rilfe.conf")
    rifle.reload_config()
    rifle.execute(["file1", "file2"])
"""

import os.path
import re
from subprocess import Popen, PIPE
import sys

__version__ = 'rifle 1.6.1'

# Options and constants that a user might want to change:
DEFAULT_PAGER = 'less'
DEFAULT_EDITOR = 'nano'
ASK_COMMAND = 'ask'
ENCODING = 'utf-8'

# Imports from ranger library, plus reimplementations in case ranger is not
# installed so rifle can be run as a standalone program.
try:
    from ranger.ext.get_executables import get_executables
except ImportError:
    _cached_executables = None

    def get_executables():
        """Return all executable files in $PATH + Cache them."""
        global _cached_executables
        if _cached_executables is not None:
            return _cached_executables

        if 'PATH' in os.environ:
            paths = os.environ['PATH'].split(':')
        else:
            paths = ['/usr/bin', '/bin']

        from stat import S_IXOTH, S_IFREG
        paths_seen = set()
        _cached_executables = set()
        for path in paths:
            if path in paths_seen:
                continue
            paths_seen.add(path)
            try:
                content = os.listdir(path)
            except OSError:
                continue
            for item in content:
                abspath = path + '/' + item
                try:
                    filestat = os.stat(abspath)
                except OSError:
                    continue
                if filestat.st_mode & (S_IXOTH | S_IFREG):
                    _cached_executables.add(item)
        return _cached_executables


try:
    from ranger.ext.popen_forked import Popen_forked
except ImportError:
    def Popen_forked(*args, **kwargs):
        """Forks process and runs Popen with the given args and kwargs."""
        try:
            pid = os.fork()
        except OSError:
            return False
        if pid == 0:
            os.setsid()
            kwargs['stdin'] = open(os.devnull, 'r')
            kwargs['stdout'] = kwargs['stderr'] = open(os.devnull, 'w')
            Popen(*args, **kwargs)
            os._exit(0)
        return True


def _is_terminal():
    # Check if stdin (file descriptor 0), stdout (fd 1) and
    # stderr (fd 2) are connected to a terminal
    try:
        os.ttyname(0)
        os.ttyname(1)
        os.ttyname(2)
    except:
        return False
    return True


def squash_flags(flags):
    """Remove lowercase flags if the respective uppercase flag exists

    >>> squash_flags('abc')
    'abc'
    >>> squash_flags('abcC')
    'ab'
    >>> squash_flags('CabcAd')
    'bd'
    """
    exclude = ''.join(f.upper() + f.lower() for f in flags if f == f.upper())
    return ''.join(f for f in flags if f not in exclude)


class Rifle(object):
    delimiter1 = '='
    delimiter2 = ','

    # TODO: Test all of the hooks properly
    def hook_before_executing(self, command, mimetype, flags):
        pass

    def hook_after_executing(self, command, mimetype, flags):
        pass

    def hook_command_preprocessing(self, command):
        return command

    def hook_command_postprocessing(self, command):
        return command

    def hook_environment(self, env):
        return env

    def hook_logger(self, string):
        sys.stderr.write(string + "\n")

    def __init__(self, config_file):
        self.config_file = config_file
        self._app_flags = ''
        self._app_label = None
        self._initialized_mimetypes = False

        # get paths for mimetype files
        self._mimetype_known_files = [
                os.path.expanduser("~/.mime.types")]
        if __file__.endswith("ranger/ext/rifle.py"):
            # Add ranger's default mimetypes when run from ranger directory
            self._mimetype_known_files.append(
                    __file__.replace("ext/rifle.py", "data/mime.types"))

    def reload_config(self, config_file=None):
        """Replace the current configuration with the one in config_file"""
        if config_file is None:
            config_file = self.config_file
        f = open(config_file, 'r')
        self.rules = []
        lineno = 1
        for line in f:
            if line.startswith('#') or line == '\n':
                continue
            line = line.strip()
            try:
                if self.delimiter1 not in line:
                    raise Exception("Line without delimiter")
                tests, command = line.split(self.delimiter1, 1)
                tests = tests.split(self.delimiter2)
                tests = tuple(tuple(f.strip().split(None, 1)) for f in tests)
                command = command.strip()
                self.rules.append((command, tests))
            except Exception as e:
                self.hook_logger("Syntax error in %s line %d (%s)" % \
                    (config_file, lineno, str(e)))
            lineno += 1
        f.close()

    def _eval_condition(self, condition, files, label):
        # Handle the negation of conditions starting with an exclamation mark,
        # then pass on the arguments to _eval_condition2().

        if not condition:
            return True
        if condition[0].startswith('!'):
            new_condition = tuple([condition[0][1:]]) + tuple(condition[1:])
            return not self._eval_condition2(new_condition, files, label)
        return self._eval_condition2(condition, files, label)

    def _eval_condition2(self, rule, files, label):
        # This function evaluates the condition, after _eval_condition() handled
        # negation of conditions starting with a "!".

        if not files:
            return False

        function = rule[0]
        argument = rule[1] if len(rule) > 1 else ''

        if function == 'ext':
            extension = os.path.basename(files[0]).rsplit('.', 1)[-1].lower()
            return bool(re.search('^(' + argument + ')$', extension))
        elif function == 'name':
            return bool(re.search(argument, os.path.basename(files[0])))
        elif function == 'match':
            return bool(re.search(argument, files[0]))
        elif function == 'file':
            return os.path.isfile(files[0])
        elif function == 'directory':
            return os.path.isdir(files[0])
        elif function == 'path':
            return bool(re.search(argument, os.path.abspath(files[0])))
        elif function == 'mime':
            return bool(re.search(argument, self._get_mimetype(files[0])))
        elif function == 'has':
            return argument in get_executables()
        elif function == 'terminal':
            return _is_terminal()
        elif function == 'number':
            if argument.isdigit():
                self._skip = int(argument)
            return True
        elif function == 'label':
            self._app_label = argument
            if label:
                return argument == label
            return True
        elif function == 'flag':
            self._app_flags = argument
            return True
        elif function == 'X':
            return 'DISPLAY' in os.environ
        elif function == 'else':
            return True

    def _get_mimetype(self, fname):
        # Spawn "file" to determine the mime-type of the given file.
        if self._mimetype:
            return self._mimetype

        import mimetypes
        for path in self._mimetype_known_files:
            if path not in mimetypes.knownfiles:
                mimetypes.knownfiles.append(path)
        self._mimetype, encoding = mimetypes.guess_type(fname)

        if not self._mimetype:
            process = Popen(["file", "--mime-type", "-Lb", fname],
                    stdout=PIPE, stderr=PIPE)
            mimetype, _ = process.communicate()
            self._mimetype = mimetype.decode(ENCODING).strip()
        return self._mimetype

    def _build_command(self, files, action, flags):
        # Get the flags
        if isinstance(flags, str):
            self._app_flags += flags
        self._app_flags = squash_flags(self._app_flags)
        filenames = "' '".join(f.replace("'", "'\\\''") for f in files
                if "\x00" not in f)
        return "set -- '%s'; %s" % (filenames, action)

    def list_commands(self, files, mimetype=None):
        """List all commands that are applicable for the given files

        Returns one 4-tuple for all currently applicable commands
        The 4-tuple contains (count, command, label, flags).
        count is the index, counted from 0 upwards,
        command is the command that will be executed.
        label and flags are the label and flags specified in the rule.
        """
        self._mimetype = mimetype
        count = -1
        for cmd, tests in self.rules:
            self._skip = None
            self._app_flags = ''
            self._app_label = None
            for test in tests:
                if not self._eval_condition(test, files, None):
                    break
            else:
                if self._skip is None:
                    count += 1
                else:
                    count = self._skip
                yield (count, cmd, self._app_label, self._app_flags)

    def execute(self, files, number=0, label=None, flags="", mimetype=None):
        """Executes the given list of files.

        By default, this executes the first command where all conditions apply,
        but by specifying number=N you can run the 1+Nth command.

        If a label is specified, only rules with this label will be considered.

        If you specify the mimetype, rifle will not try to determine it itself.

        By specifying a flag, you extend the flag that is defined in the rule.
        Uppercase flags negate the respective lowercase flags.
        For example: if the flag in the rule is "pw" and you specify "Pf", then
        the "p" flag is negated and the "f" flag is added, resulting in "wf".
        """
        command = None
        found_at_least_one = None

        # Determine command
        for count, cmd, lbl, flgs in self.list_commands(files, mimetype):
            if label and label == lbl or not label and count == number:
                cmd = self.hook_command_preprocessing(cmd)
                if cmd == ASK_COMMAND:
                    return ASK_COMMAND
                command = self._build_command(files, cmd, flags + flgs)
                flags = self._app_flags
                break
            else:
                found_at_least_one = True
        else:
            if label and label in get_executables():
                cmd = '%s "$@"' % label
                command = self._build_command(files, cmd, flags)

        # Execute command
        if command is None:
            if found_at_least_one:
                if label:
                    self.hook_logger("Label '%s' is undefined" % label)
                else:
                    self.hook_logger("Method number %d is undefined." % number)
            else:
                self.hook_logger("No action found.")
        else:
            if 'PAGER' not in os.environ:
                os.environ['PAGER'] = DEFAULT_PAGER
            if 'EDITOR' not in os.environ:
                os.environ['EDITOR'] = DEFAULT_EDITOR
            command = self.hook_command_postprocessing(command)
            self.hook_before_executing(command, self._mimetype, self._app_flags)
            try:
                if 'r' in flags:
                    prefix = ['sudo', '-E', 'su', '-mc']
                else:
                    prefix = ['/bin/sh', '-c']

                cmd = prefix + [command]
                if 't' in flags:
                    if 'TERMCMD' not in os.environ:
                        term = os.environ['TERM']
                        if term.startswith('rxvt-unicode'):
                            term = 'urxvt'
                        if term not in get_executables():
                            self.hook_logger("Can not determine terminal command.  "
                                "Please set $TERMCMD manually.")
                            # A fallback terminal that is likely installed:
                            term = 'xterm'
                        os.environ['TERMCMD'] = term
                    cmd = [os.environ['TERMCMD'], '-e'] + cmd
                if 'f' in flags or 't' in flags:
                    Popen_forked(cmd, env=self.hook_environment(os.environ))
                else:
                    p = Popen(cmd, env=self.hook_environment(os.environ))
                    p.wait()
            finally:
                self.hook_after_executing(command, self._mimetype, self._app_flags)


def main():
    """The main function which is run when you start this program direectly."""
    import sys

    # Find configuration file path
    if 'XDG_CONFIG_HOME' in os.environ and os.environ['XDG_CONFIG_HOME']:
        conf_path = os.environ['XDG_CONFIG_HOME'] + '/ranger/rifle.conf'
    else:
        conf_path = os.path.expanduser('~/.config/ranger/rifle.conf')
    default_conf_path = conf_path
    if not os.path.isfile(conf_path):
        conf_path = os.path.normpath(os.path.join(os.path.dirname(__file__),
            '../config/rifle.conf'))
    if not os.path.isfile(conf_path):
        try:
            # if ranger is installed, get the configuration from ranger
            import ranger
        except ImportError:
            pass
        else:
            conf_path = os.path.join(ranger.__path__[0], "config", "rifle.conf")


    # Evaluate arguments
    from optparse import OptionParser
    parser = OptionParser(usage="%prog [-fhlpw] [files]", version=__version__)
    parser.add_option('-f', type="string", default="", metavar="FLAGS",
            help="use additional flags: f=fork, r=root, t=terminal. "
            "Uppercase flag negates respective lowercase flags.")
    parser.add_option('-l', action="store_true",
            help="list possible ways to open the files (id:label:flags:command)")
    parser.add_option('-p', type='string', default='0', metavar="KEYWORD",
            help="pick a method to open the files.  KEYWORD is either the "
            "number listed by 'rifle -l' or a string that matches a label in "
            "the configuration file")
    parser.add_option('-w', type='string', default=None, metavar="PROGRAM",
            help="open the files with PROGRAM")
    options, positional = parser.parse_args()
    if not positional:
        parser.print_help()
        raise SystemExit(1)

    if not os.path.isfile(conf_path):
        sys.stderr.write("Could not find a configuration file.\n"
                "Please create one at %s.\n" % default_conf_path)
        raise SystemExit(1)

    if options.p.isdigit():
        number = int(options.p)
        label = None
    else:
        number = 0
        label = options.p

    if options.w is not None and not options.l:
        p = Popen([options.w] + list(positional))
        p.wait()
    else:
        # Start up rifle
        rifle = Rifle(conf_path)
        rifle.reload_config()
        #print(rifle.list_commands(sys.argv[1:]))
        if options.l:
            for count, cmd, label, flags in rifle.list_commands(positional):
                print("%d:%s:%s:%s" % (count, label or '', flags, cmd))
        else:
            result = rifle.execute(positional, number=number, label=label,
                    flags=options.f)
            if result == ASK_COMMAND:
                # TODO: implement interactive asking for file type?
                print("Unknown file type: %s" % rifle._get_mimetype(positional[0]))



if __name__ == '__main__':
    if 'RANGER_DOCTEST' in os.environ:
        import doctest
        doctest.testmod()
    else:
        main()

########NEW FILE########
__FILENAME__ = shell_escape
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""Functions to escape metacharacters of arguments for shell commands."""

META_CHARS = (' ', "'", '"', '`', '&', '|', ';',
        '$', '!', '(', ')', '[', ']', '<', '>', '\t')
UNESCAPABLE = set(map(chr, list(range(9)) + list(range(10, 32)) \
        + list(range(127, 256))))
META_DICT = dict([(mc, '\\' + mc) for mc in META_CHARS])

def shell_quote(string):
    """Escapes by quoting"""
    return "'" + str(string).replace("'", "'\\''") + "'"

def shell_escape(arg):
    """Escapes by adding backslashes"""
    arg = str(arg)
    if UNESCAPABLE & set(arg):
        return shell_quote(arg)
    arg = arg.replace('\\', '\\\\') # make sure this comes at the start
    for k, v in META_DICT.items():
        arg = arg.replace(k, v)
    return arg

########NEW FILE########
__FILENAME__ = shutil_generatorized
# This file was taken from the python standard library and has been
# slightly modified to do a "yield" after every 16KB of copying
"""Utility functions for copying files and directory trees.

XXX The functions here don't copy the resource fork or other metadata on Mac.
"""

import os
import sys
import stat
from os.path import abspath

__all__ = ["copyfileobj","copyfile","copystat","copy2","BLOCK_SIZE",
           "copytree","move","rmtree","Error", "SpecialFileError"]

APPENDIX = '_'
BLOCK_SIZE = 16 * 1024

class Error(EnvironmentError):
    pass

class SpecialFileError(EnvironmentError):
    """Raised when trying to do a kind of operation (e.g. copying) which is
    not supported on a special file (e.g. a named pipe)"""

try:
    WindowsError
except NameError:
    WindowsError = None

def copyfileobj(fsrc, fdst, length=BLOCK_SIZE):
    """copy data from file-like object fsrc to file-like object fdst"""
    while 1:
        buf = fsrc.read(length)
        if not buf:
            break
        fdst.write(buf)
        yield

def _samefile(src, dst):
    # Macintosh, Unix.
    if hasattr(os.path,'samefile'):
        try:
            return os.path.samefile(src, dst)
        except OSError:
            return False

    # All other platforms: check for same pathname.
    return (os.path.normcase(abspath(src)) ==
            os.path.normcase(abspath(dst)))

def copyfile(src, dst):
    """Copy data from src to dst"""
    if _samefile(src, dst):
        raise Error("`%s` and `%s` are the same file" % (src, dst))

    fsrc = None
    fdst = None
    for fn in [src, dst]:
        try:
            st = os.stat(fn)
        except OSError:
            # File most likely does not exist
            pass
        else:
            # XXX What about other special files? (sockets, devices...)
            if stat.S_ISFIFO(st.st_mode):
                raise SpecialFileError("`%s` is a named pipe" % fn)
    try:
        fsrc = open(src, 'rb')
        fdst = open(dst, 'wb')
        for _ in copyfileobj(fsrc, fdst):
            yield
    finally:
        if fdst:
            fdst.close()
        if fsrc:
            fsrc.close()

def copystat(src, dst):
    """Copy all stat info (mode bits, atime, mtime, flags) from src to dst"""
    st = os.stat(src)
    mode = stat.S_IMODE(st.st_mode)
    if hasattr(os, 'utime'):
        try: os.utime(dst, (st.st_atime, st.st_mtime))
        except: pass
    if hasattr(os, 'chmod'):
        try: os.chmod(dst, mode)
        except: pass
    if hasattr(os, 'chflags') and hasattr(st, 'st_flags'):
        try: os.chflags(dst, st.st_flags)
        except: pass

def copy2(src, dst, overwrite=False, symlinks=False):
    """Copy data and all stat info ("cp -p src dst").

    The destination may be a directory.

    """
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))
    if not overwrite:
        dst = get_safe_path(dst)
    if symlinks and os.path.islink(src):
        linkto = os.readlink(src)
        os.symlink(linkto, dst)
    else:
        for _ in copyfile(src, dst):
            yield
        copystat(src, dst)

def get_safe_path(dst):
    if not os.path.exists(dst):
        return dst
    if not dst.endswith(APPENDIX):
        dst += APPENDIX
        if not os.path.exists(dst):
            return dst
    n = 0
    test_dst = dst + str(n)
    while os.path.exists(test_dst):
        n += 1
        test_dst = dst + str(n)

    return test_dst

def copytree(src, dst, symlinks=False, ignore=None, overwrite=False):
    """Recursively copy a directory tree using copy2().

    The destination directory must not already exist.
    If exception(s) occur, an Error is raised with a list of reasons.

    If the optional symlinks flag is true, symbolic links in the
    source tree result in symbolic links in the destination tree; if
    it is false, the contents of the files pointed to by symbolic
    links are copied.

    The optional ignore argument is a callable. If given, it
    is called with the `src` parameter, which is the directory
    being visited by copytree(), and `names` which is the list of
    `src` contents, as returned by os.listdir():

        callable(src, names) -> ignored_names

    Since copytree() is called recursively, the callable will be
    called once for each directory that is copied. It returns a
    list of names relative to the `src` directory that should
    not be copied.

    XXX Consider this example code rather than the ultimate tool.

    """
    names = os.listdir(src)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()

    errors = []
    try:
        os.makedirs(dst)
    except Exception as err:
        if not overwrite:
            dst = get_safe_path(dst)
            os.makedirs(dst)
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                if os.path.lexists(dstname):
                    if not os.path.islink(dstname) \
                    or os.readlink(dstname) != linkto:
                        os.unlink(dstname)
                        os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                for _ in copytree(srcname, dstname, symlinks,
                        ignore, overwrite):
                    yield
            else:
                # Will raise a SpecialFileError for unsupported file types
                for _ in copy2(srcname, dstname,
                        overwrite=overwrite, symlinks=symlinks):
                    yield
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except Error as err:
            errors.extend(err.args[0])
        except EnvironmentError as why:
            errors.append((srcname, dstname, str(why)))
    try:
        copystat(src, dst)
    except OSError as why:
        if WindowsError is not None and isinstance(why, WindowsError):
            # Copying file access times may fail on Windows
            pass
        else:
            errors.extend((src, dst, str(why)))
    if errors:
        raise Error(errors)

def rmtree(path, ignore_errors=False, onerror=None):
    """Recursively delete a directory tree.

    If ignore_errors is set, errors are ignored; otherwise, if onerror
    is set, it is called to handle the error with arguments (func,
    path, exc_info) where func is os.listdir, os.remove, or os.rmdir;
    path is the argument to that function that caused it to fail; and
    exc_info is a tuple returned by sys.exc_info().  If ignore_errors
    is false and onerror is None, an exception is raised.

    """
    if ignore_errors:
        def onerror(*args):
            pass
    elif onerror is None:
        def onerror(*args):
            raise
    try:
        if os.path.islink(path):
            # symlinks to directories are forbidden, see bug #1669
            raise OSError("Cannot call rmtree on a symbolic link")
    except OSError:
        onerror(os.path.islink, path, sys.exc_info())
        # can't continue even if onerror hook returns
        return
    names = []
    try:
        names = os.listdir(path)
    except os.error as err:
        onerror(os.listdir, path, sys.exc_info())
    for name in names:
        fullname = os.path.join(path, name)
        try:
            mode = os.lstat(fullname).st_mode
        except os.error:
            mode = 0
        if stat.S_ISDIR(mode):
            rmtree(fullname, ignore_errors, onerror)
        else:
            try:
                os.remove(fullname)
            except os.error as err:
                onerror(os.remove, fullname, sys.exc_info())
    try:
        os.rmdir(path)
    except os.error:
        onerror(os.rmdir, path, sys.exc_info())


def _basename(path):
    # A basename() variant which first strips the trailing slash, if present.
    # Thus we always get the last component of the path, even for directories.
    return os.path.basename(path.rstrip(os.path.sep))

def move(src, dst, overwrite=False):
    """Recursively move a file or directory to another location. This is
    similar to the Unix "mv" command.

    If the destination is a directory or a symlink to a directory, the source
    is moved inside the directory. The destination path must not already
    exist.

    If the destination already exists but is not a directory, it may be
    overwritten depending on os.rename() semantics.

    If the destination is on our current filesystem, then rename() is used.
    Otherwise, src is copied to the destination and then removed.
    A lot more could be done here...  A look at a mv.c shows a lot of
    the issues this implementation glosses over.

    """
    real_dst = os.path.join(dst, _basename(src))
    if not overwrite:
        real_dst = get_safe_path(real_dst)
    try:
        os.rename(src, real_dst)
    except OSError:
        if os.path.isdir(src):
            if _destinsrc(src, dst):
                raise Error("Cannot move a directory '%s' into itself '%s'." % (src, dst))
            for _ in copytree(src, real_dst, symlinks=True, overwrite=overwrite):
                yield
            rmtree(src)
        else:
            for _ in copy2(src, real_dst, symlinks=True, overwrite=overwrite):
                yield
            os.unlink(src)

def _destinsrc(src, dst):
    src = abspath(src)
    dst = abspath(dst)
    if not src.endswith(os.path.sep):
        src += os.path.sep
    if not dst.endswith(os.path.sep):
        dst += os.path.sep
    return dst.startswith(src)

# vi: expandtab sts=4 ts=4 sw=4

########NEW FILE########
__FILENAME__ = signals
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""An efficient and minimalistic signaling/hook module.

To use this in a class, subclass SignalDispatcher and call
SignalDispatcher.__init__(self) in the __init__ function.  Now you can bind
functions to a signal name (string) by using signal_bind or remove it with
signal_unbind.  Now whenever signal_emit is called with that signal name,
the bound functions are executed in order of priority.

This module supports weak referencing.  This means that if you bind a function
which is later deleted everywhere except in this binding, Python's garbage
collector will remove it from memory.  Activate it with
signal_bind(..., weak=True).  The handlers for such functions are automatically
deleted when trying to call them (in signal_emit), but if they are never
called, they accumulate and should be manually deleted with
signal_garbage_collect().

>>> def test_function(signal):
...     if 'display' in signal:
...         print(signal.display)
...     else:
...         signal.stop()
>>> def temporary_function():
...     print("A temporary function")

>>> sig = SignalDispatcher()

>>> # Test binding and unbinding
>>> handler1 = sig.signal_bind('test', test_function, priority=2)
>>> handler2 = sig.signal_bind('test', temporary_function, priority=1)
>>> sig.signal_emit('test', display="It works!")
It works!
A temporary function
True
>>> # Note that test_function stops the signal when there's no display keyword
>>> sig.signal_emit('test')
False
>>> sig.signal_unbind(handler1)
>>> sig.signal_emit('test')
A temporary function
True
>>> sig.signal_clear()
>>> sig.signal_emit('test')
True

>>> # Bind temporary_function with a weak reference
>>> handler = sig.signal_bind('test', temporary_function, weak=True)
>>> sig.signal_emit('test')
A temporary function
True
>>> # Delete temporary_function.  Its handler is removed too, since it
>>> # was weakly referenced.
>>> del temporary_function
>>> sig.signal_emit('test')
True
"""

import weakref
from types import MethodType

class Signal(dict):
    """Signals are passed to the bound functions as an argument.

    They contain the attributes "origin", which is a reference to the
    signal dispatcher, and "name", the name of the signal that was emitted.
    You can call signal_emit with any keyword arguments, which will be
    turned into attributes of this object as well.

    To delete a signal handler from inside a signal, raise a ReferenceError.
    """
    stopped = False
    def __init__(self, **keywords):
        dict.__init__(self, keywords)
        self.__dict__ = self

    def stop(self):
        """ Stop the propagation of the signal to the next handlers.  """
        self.stopped = True


class SignalHandler:
    """Signal Handlers contain information about a signal binding.

    They are returned by signal_bind() and have to be passed to signal_unbind()
    in order to remove the handler again.

    You can disable a handler without removing it by setting the attribute
    "active" to False.
    """
    active = True
    def __init__(self, signal_name, function, priority, pass_signal):
        self._priority = max(0, min(1, priority))
        self._signal_name = signal_name
        self._function = function
        self._pass_signal = pass_signal


class SignalDispatcher(object):
    """This abstract class handles the binding and emitting of signals."""
    def __init__(self):
        self._signals = dict()

    def signal_clear(self):
        """Remove all signals."""
        for handler_list in self._signals.values():
            for handler in handler_list:
                handler._function = None
        self._signals = dict()

    def signal_bind(self, signal_name, function, priority=0.5, weak=False, autosort=True):
        """Bind a function to the signal.

        signal_name:  Any string to name the signal
        function:  Any function with either one or zero arguments which will be
            called when the signal is emitted.  If it takes one argument, a
            Signal object will be passed to it.
        priority:  Optional, any number.  When signals are emitted, handlers will
            be called in order of priority.  (highest priority first)
        weak:  Use a weak reference of "function" so it can be garbage collected
            properly when it's deleted.

        Returns a SignalHandler which can be used to remove this binding by
        passing it to signal_unbind().
        """
        assert isinstance(signal_name, str)
        assert hasattr(function, '__call__')
        assert hasattr(function, '__code__')
        assert isinstance(priority, (int, float))
        assert isinstance(weak, bool)
        try:
            handlers = self._signals[signal_name]
        except:
            handlers = self._signals[signal_name] = []
        nargs = function.__code__.co_argcount

        if getattr(function, '__self__', None):
            nargs -= 1
            if weak:
                function = (function.__func__, weakref.proxy(function.__self__))
        elif weak:
            function = weakref.proxy(function)

        handler = SignalHandler(signal_name, function, priority, nargs > 0)
        handlers.append(handler)
        if autosort:
            handlers.sort(key=lambda handler: -handler._priority)
        return handler

    def signal_force_sort(self, signal_name=None):
        """Forces a sorting of signal handlers by priority.

        This is only necessary if you used signal_bind with autosort=False
        after finishing to bind many signals at once.
        """
        if signal_name is None:
            for handlers in self._signals.values():
                handlers.sort(key=lambda handler: -handler._priority)
        elif signal_name in self._signals:
            self._signals[signal_name].sort(key=lambda handler: -handler._priority)
        else:
            return False

    def signal_unbind(self, signal_handler):
        """Removes a signal binding.

        This requires the SignalHandler that has been originally returned by
        signal_bind().
        """
        try:
            handlers = self._signals[signal_handler._signal_name]
        except:
            pass
        else:
            try:
                signal_handler._function = None
                handlers.remove(signal_handler)
            except:
                pass

    def signal_garbage_collect(self):
        """Remove all handlers with deleted weak references.

        Usually this is not needed; every time you emit a signal, its handlers
        are automatically checked in this way.  However, if you can't be sure
        that a signal is ever emitted AND you keep binding weakly referenced
        functions to the signal, this method should be regularly called to
        avoid memory leaks in self._signals.

        >>> sig = SignalDispatcher()

        >>> # lambda:None is an anonymous function which has no references
        >>> # so it should get deleted immediately
        >>> handler = sig.signal_bind('test', lambda: None, weak=True)
        >>> len(sig._signals['test'])
        1
        >>> # need to call garbage collect so that it's removed from the list.
        >>> sig.signal_garbage_collect()
        >>> len(sig._signals['test'])
        0
        >>> # This demonstrates that garbage collecting is not necessary
        >>> # when using signal_emit().
        >>> handler = sig.signal_bind('test', lambda: None, weak=True)
        >>> sig.signal_emit('another_signal')
        True
        >>> len(sig._signals['test'])
        1
        >>> sig.signal_emit('test')
        True
        >>> len(sig._signals['test'])
        0
        """
        for handler_list in self._signals.values():
            i = len(handler_list)
            while i:
                i -= 1
                handler = handler_list[i]
                try:
                    if isinstance(handler._function, tuple):
                        handler._function[1].__class__
                    else:
                        handler._function.__class__
                except ReferenceError:
                    handler._function = None
                    del handler_list[i]

    def signal_emit(self, signal_name, **kw):
        """Emits a signal and call every function that was bound to that signal.

        You can call this method with any key words.  They will be turned into
        attributes of the Signal object that is passed to the functions.
        If a function calls signal.stop(), no further functions will be called.
        If a function raises a ReferenceError, the handler will be deleted.

        Returns False if signal.stop() was called and True otherwise.
        """
        assert isinstance(signal_name, str)
        if signal_name not in self._signals:
            return True
        handlers = self._signals[signal_name]
        if not handlers:
            return True

        signal = Signal(origin=self, name=signal_name, **kw)

        # propagate
        for handler in tuple(handlers):
            if handler.active:
                try:
                    if isinstance(handler._function, tuple):
                        fnc = MethodType(*handler._function)
                    else:
                        fnc = handler._function
                    if handler._pass_signal:
                        fnc(signal)
                    else:
                        fnc()
                except ReferenceError:
                    handler._function = None
                    handlers.remove(handler)
                if signal.stopped:
                    return False
        return True


if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = spawn
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

from subprocess import Popen, PIPE
ENCODING = 'utf-8'

def spawn(*args):
    """Runs a program, waits for its termination and returns its stdout"""
    if len(args) == 1:
        popen_arguments = args[0]
        shell = isinstance(popen_arguments, str)
    else:
        popen_arguments = args
        shell = False
    process = Popen(popen_arguments, stdout=PIPE, shell=shell)
    stdout, stderr = process.communicate()
    return stdout.decode(ENCODING)

########NEW FILE########
__FILENAME__ = bzr
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# vcs - a python module to handle various version control systems
# Copyright 2012 Abdó Roig-Maranges <abdo.roig@gmail.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import shutil
from datetime import datetime

from .vcs import Vcs, VcsError


class Bzr(Vcs):
    vcsname  = 'bzr'
    HEAD="last:1"

    # Auxiliar stuff
    #---------------------------

    def _bzr(self, path, args, silent=True, catchout=False, bytes=False):
        return self._vcs(path, 'bzr', args, silent=silent, catchout=catchout, bytes=bytes)


    def _has_head(self):
        """Checks whether repo has head"""
        rnum = self._bzr(self.path, ['revno'], catchout=True)
        return rnum != '0'


    def _sanitize_rev(self, rev):
        if rev == None: return None
        rev = rev.strip()
        if len(rev) == 0: return None

        return rev


    def _log(self, refspec=None, filelist=None):
        """Gets a list of dicts containing revision info, for the revisions matching refspec"""
        args = ['log', '-n0', '--show-ids']
        if refspec: args = args + ["-r", refspec]

        if filelist: args = args + filelist

        raw = self._bzr(self.path, args, catchout=True, silent=True)
        L = re.findall('-+$(.*?)^-', raw + '\n---', re.MULTILINE | re.DOTALL)

        log = []
        for t in L:
            t = t.strip()
            if len(t) == 0: continue

            dt = {}
            m = re.search('^revno:\s*([0-9]+)\s*$', t, re.MULTILINE)
            if m: dt['short'] = m.group(1).strip()
            m = re.search('^revision-id:\s*(.+)\s*$', t, re.MULTILINE)
            if m: dt['revid'] = m.group(1).strip()
            m = re.search('^committer:\s*(.+)\s*$', t, re.MULTILINE)
            if m: dt['author'] = m.group(1).strip()
            m = re.search('^timestamp:\s*(.+)\s*$', t, re.MULTILINE)
            if m: dt['date'] = datetime.strptime(m.group(1).strip(), '%a %Y-%m-%d %H:%M:%S %z')
            m = re.search('^message:\s*^(.+)$', t, re.MULTILINE)
            if m: dt['summary'] = m.group(1).strip()
            log.append(dt)
        return log


    def _bzr_file_status(self, st):
        st = st.strip()
        if   st in "AM":     return 'staged'
        elif st in "D":      return 'deleted'
        elif st in "?":      return 'untracked'
        else:                return 'unknown'



    # Repo creation
    #---------------------------

    def init(self):
        """Initializes a repo in current path"""
        self._bzr(self.path, ['init'])
        self.update()


    def clone(self, src):
        """Clones a repo from src"""
        path = os.path.dirname(self.path)
        name = os.path.basename(self.path)
        try:
            os.rmdir(self.path)
        except OSError:
            raise VcsError("Can't clone to %s. It is not an empty directory" % self.path)

        self._bzr(path, ['branch', src, name])
        self.update()



    # Action Interface
    #---------------------------

    def commit(self, message):
        """Commits with a given message"""
        self._bzr(self.path, ['commit', '-m', message])


    def add(self, filelist=None):
        """Adds files to the index, preparing for commit"""
        if filelist != None: self._bzr(self.path, ['add'] + filelist)
        else:                self._bzr(self.path, ['add'])


    def reset(self, filelist=None):
        """Removes files from the index"""
        if filelist != None: self._bzr(self.path, ['remove', '--keep', '--new'] + filelist)
        else:                self._bzr(self.path, ['remove', '--keep', '--new'])


    def pull(self):
        """Pulls a git repo"""
        self._bzr(self.path, ['pull'])


    def push(self):
        """Pushes a git repo"""
        self._bzr(self.path, ['push'])


    def checkout(self, rev):
        """Checks out a branch or revision"""
        self._bzr(self.path, ['update', '-r', rev])


    def extract_file(self, rev, name, dest):
        """Extracts a file from a given revision and stores it in dest dir"""
        if rev == self.INDEX:
            shutil.copyfile(os.path.join(self.path, name), dest)
        else:
            out = self._bzr(self.path, ['cat', '--r', rev, name], catchout=True, bytes=True)
            with open(dest, 'wb') as fd: fd.write(out)



    # Data Interface
    #---------------------------

    def get_status_allfiles(self):
        """Returns a dict indexed by files not in sync their status as values.
           Paths are given relative to the root. Strips trailing '/' from dirs."""
        raw = self._bzr(self.path, ['status', '--short', '--no-classify'], catchout=True, bytes=True)
        L = re.findall('^(..)\s*(.*?)\s*$', raw.decode('utf-8'), re.MULTILINE)
        ret = {}
        for st, p in L:
            sta = self._bzr_file_status(st)
            ret[os.path.normpath(p.strip())] = sta
        return ret


    def get_ignore_allfiles(self):
        """Returns a set of all the ignored files in the repo. Strips trailing '/' from dirs."""
        raw = self._bzr(self.path, ['ls', '--ignored'], catchout=True)
        return set(os.path.normpath(p) for p in raw.split('\n'))


    # TODO: slow due to net access
    def get_remote_status(self):
        """Checks the status of the repo regarding sync state with remote branch"""
        if self.get_remote() == None:
            return "none"

        ahead = behind = True
        try:
            self._bzr(self.path, ['missing', '--mine-only'], silent=True)
        except:
            ahead = False

        try:
            self._bzr(self.path, ['missing', '--theirs-only'], silent=True)
        except:
            behind = False

        if       ahead and     behind: return "diverged"
        elif     ahead and not behind: return "ahead"
        elif not ahead and     behind: return "behind"
        elif not ahead and not behind: return "sync"


    def get_branch(self):
        """Returns the current named branch, if this makes sense for the backend. None otherwise"""
        branch = self._bzr(self.path, ['nick'], catchout=True)
        return branch or None


    def get_log(self, filelist=None, maxres=None):
        """Get the entire log for the current HEAD"""
        if not self._has_head(): return []
        return self._log(refspec=None, filelist=filelist)


    def get_raw_log(self, filelist=None):
        """Gets the raw log as a string"""
        if not self._has_head(): return []
        args = ['log']
        if filelist: args = args + filelist
        return self._bzr(self.path, args, catchout=True)


    def get_raw_diff(self, refspec=None, filelist=None):
        """Gets the raw diff as a string"""
        args = ['diff', '--git']
        if refspec:  args = args + [refspec]
        if filelist: args = args + filelist
        return self._bzr(self.path, args, catchout=True)


    def get_remote(self):
        """Returns the url for the remote repo attached to head"""
        try:
            remote = self._bzr(self.path, ['config', 'parent_location'], catchout=True)
        except VcsError:
            remote = ""

        return remote.strip() or None


    def get_revision_id(self, rev=None):
        """Get a canonical key for the revision rev"""
        if rev == None: rev = self.HEAD
        elif rev == self.INDEX: return None
        rev = self._sanitize_rev(rev)
        try:
            L = self._log(refspec=rev)
        except VcsError:
            L = []
        if len(L) == 0: return None
        else:           return L[0]['revid']


    def get_info(self, rev=None):
        """Gets info about the given revision rev"""
        if rev == None: rev = self.HEAD
        rev = self._sanitize_rev(rev)
        if rev == self.HEAD and not self._has_head(): return []

        L = self._log(refspec=rev)
        if len(L) == 0:
            raise VcsError("Revision %s does not exist" % rev)
        elif len(L) > 1:
            raise VcsError("More than one instance of revision %s ?!?" % rev)
        else:
            return L[0]


    def get_files(self, rev=None):
        """Gets a list of files in revision rev"""
        if rev == None: rev = self.HEAD
        rev = self._sanitize_rev(rev)

        if rev:
            if rev == self.INDEX:  raw = self._bzr(self.path, ["ls"], catchout=True)
            else:                  raw = self._bzr(self.path, ['ls', '--R', '-V', '-r', rev], catchout=True)
            return raw.split('\n')
        else:
            return []

# vim: expandtab:shiftwidth=4:tabstop=4:softtabstop=4:textwidth=80

########NEW FILE########
__FILENAME__ = git
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# vcs - a python module to handle various version control systems
# Copyright 2011, 2012 Abdó Roig-Maranges <abdo.roig@gmail.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import shutil
from datetime import datetime

from .vcs import Vcs, VcsError


class Git(Vcs):
    vcsname  = 'git'

    # Auxiliar stuff
    #---------------------------

    def _git(self, path, args, silent=True, catchout=False, bytes=False):
        return self._vcs(path, 'git', args, silent=silent, catchout=catchout, bytes=bytes)


    def _has_head(self):
        """Checks whether repo has head"""
        try:
            self._git(self.path, ['rev-parse', 'HEAD'], silent=True)
        except VcsError:
            return False
        return True


    def _head_ref(self):
        """Gets HEAD's ref"""
        ref = self._git(self.path, ['symbolic-ref', self.HEAD], catchout=True, silent=True)
        return ref.strip() or None


    def _remote_ref(self, ref):
        """Gets remote ref associated to given ref"""
        if ref == None: return None
        remote = self._git(self.path, ['for-each-ref', '--format=%(upstream)', ref], catchout=True, silent=True)
        return remote.strip() or None


    def _sanitize_rev(self, rev):
        if rev == None: return None
        return rev.strip()


    def _log(self, refspec=None, maxres=None, filelist=None):
        """Gets a list of dicts containing revision info, for the revisions matching refspec"""
        fmt = '--pretty=%h %H%nAuthor: %an <%ae>%nDate: %ct%nSubject: %s%n'

        args = ['--no-pager', 'log', fmt]
        if refspec:  args = args + ['-1', refspec]
        elif maxres: args = args + ['-%d' % maxres]

        if filelist: args = args + ['--'] + filelist

        raw = self._git(self.path, args, catchout=True)
        L = re.findall('^\s*(\w*)\s*(\w*)\s*^Author:\s*(.*)\s*^Date:\s*(.*)\s*^Subject:\s*(.*)\s*', raw, re.MULTILINE)

        log = []
        for t in L:
            dt = {}
            dt['short'] = t[0].strip()
            dt['revid'] = t[1].strip()
            dt['author'] = t[2].strip()
            m = re.match('\d+(\.\d+)?', t[3].strip())
            dt['date'] = datetime.fromtimestamp(float(m.group(0)))
            dt['summary'] = t[4].strip()
            log.append(dt)
        return log


    def _git_file_status(self, st):
        if len(st) != 2: raise VcsError("Wrong git file status string: %s" % st)
        X, Y = (st[0], st[1])
        if   X in " "      and Y in " " : return 'sync'
        elif X in "MADRC"  and Y in " " : return 'staged'
        elif X in "MADRC " and Y in "M":  return 'changed'
        elif X in "MARC "  and Y in "D":  return 'deleted'
        elif X in "U" or Y in "U":        return 'conflict'
        elif X in "A" and Y in "A":       return 'conflict'
        elif X in "D" and Y in "D":       return 'conflict'
        elif X in "?" and Y in "?":       return 'untracked'
        elif X in "!" and Y in "!":       return 'ignored'
        else:                             return 'unknown'



    # Repo creation
    #---------------------------

    def init(self):
        """Initializes a repo in current path"""
        self._git(self.path, ['init'])
        self.update()


    def clone(self, src):
        """Clones a repo from src"""
        name = os.path.basename(self.path)
        path = os.path.dirname(self.path)
        try:
            os.rmdir(self.path)
        except OSError:
            raise VcsError("Can't clone to %s. It is not an empty directory" % self.path)

        self._git(path, ['clone', src, name])
        self.update()



    # Action interface
    #---------------------------

    def commit(self, message):
        """Commits with a given message"""
        self._git(self.path, ['commit', '-m', message])


    def add(self, filelist=None):
        """Adds files to the index, preparing for commit"""
        if filelist != None: self._git(self.path, ['add', '-A'] + filelist)
        else:                self._git(self.path, ['add', '-A'])


    def reset(self, filelist=None):
        """Removes files from the index"""
        if filelist != None: self._git(self.path, ['reset'] + filelist)
        else:                self._git(self.path, ['reset'])


    def pull(self, br=None):
        """Pulls from remote"""
        if br: self._git(self.path, ['pull', br])
        else:  self._git(self.path, ['pull'])


    def push(self, br=None):
        """Pushes to remote"""
        if br: self._git(self.path, ['push', br])
        else:  self._git(self.path, ['push'])


    def checkout(self, rev):
        """Checks out a branch or revision"""
        self._git(self.path, ['checkout', self._sanitize_rev(rev)])


    def extract_file(self, rev, name, dest):
        """Extracts a file from a given revision and stores it in dest dir"""
        if rev == self.INDEX:
            shutil.copyfile(os.path.join(self.path, name), dest)
        else:
            out = self._git(self.path, ['--no-pager', 'show', '%s:%s' % (self._sanitize_rev(rev), name)],
                            catchout=True, bytes=True)
            with open(dest, 'wb') as fd: fd.write(out)



    # Data Interface
    #---------------------------

    def get_status_allfiles(self):
        """Returns a dict indexed by files not in sync their status as values.
           Paths are given relative to the root. Strips trailing '/' from dirs."""
        raw = self._git(self.path, ['status', '--porcelain'], catchout=True, bytes=True)
        L = re.findall('^(..)\s*(.*?)\s*$', raw.decode('utf-8'), re.MULTILINE)
        ret = {}
        for st, p in L:
            sta = self._git_file_status(st)
            if 'R' in st:
                m = re.match('^(.*)\->(.*)$', p)
                if m: p = m.group(2).strip()
            ret[os.path.normpath(p.strip())] = sta
        return ret


    def get_ignore_allfiles(self):
        """Returns a set of all the ignored files in the repo. Strips trailing '/' from dirs."""
        raw = self._git(self.path, ['ls-files', '--others', '--directory', '-i', '--exclude-standard'],
                        catchout=True)
        return set(os.path.normpath(p) for p in raw.split('\n'))


    def get_remote_status(self):
        """Checks the status of the repo regarding sync state with remote branch"""
        try:
            head = self._head_ref()
            remote = self._remote_ref(head)
        except VcsError:
            head = remote = None

        if head and remote:
            raw = self._git(self.path, ['rev-list', '--left-right', '%s...%s' % (remote, head)], catchout=True)
            ahead  = re.search("^>", raw, flags=re.MULTILINE)
            behind = re.search("^<", raw, flags=re.MULTILINE)

            if       ahead and     behind: return "diverged"
            elif     ahead and not behind: return "ahead"
            elif not ahead and     behind: return "behind"
            elif not ahead and not behind: return "sync"
        else:                            return "none"


    def get_branch(self):
        """Returns the current named branch, if this makes sense for the backend. None otherwise"""
        try:
            head = self._head_ref()
        except VcsError:
            head = None

        if head:
            m = re.match('refs/heads/([^/]*)', head)
            if m: return m.group(1).strip()
        else:
            return "detached"

        return None


    def get_log(self, filelist=None, maxres=None):
        """Get the entire log for the current HEAD"""
        if not self._has_head(): return []
        return self._log(refspec=None, maxres=maxres, filelist=filelist)


    def get_raw_log(self, filelist=None):
        """Gets the raw log as a string"""
        if not self._has_head(): return []
        args = ['log']
        if filelist: args = args + ['--'] + filelist
        return self._git(self.path, args, catchout=True)


    def get_raw_diff(self, refspec=None, filelist=None):
        """Gets the raw diff as a string"""
        args = ['diff']
        if refspec:  args = args + [refspec]
        if filelist: args = args + ['--'] + filelist
        return self._git(self.path, args, catchout=True)


    def get_remote(self):
        """Returns the url for the remote repo attached to head"""
        if self.is_repo():
            try:
                ref = self._head_ref()
                remote = self._remote_ref(ref)
            except VcsError:
                ref = remote = None

            if remote:
                m = re.match('refs/remotes/([^/]*)/', remote)
                if m:
                    url = self._git(self.path, ['config', '--get', 'remote.%s.url' % m.group(1)], catchout=True)
                    return url.strip() or None
        return None


    def get_revision_id(self, rev=None):
        """Get a canonical key for the revision rev"""
        if rev == None: rev = self.HEAD
        elif rev == self.INDEX: return None
        rev = self._sanitize_rev(rev)

        return self._sanitize_rev(self._git(self.path, ['rev-parse', rev], catchout=True))


    def get_info(self, rev=None):
        """Gets info about the given revision rev"""
        if rev == None: rev = self.HEAD
        rev = self._sanitize_rev(rev)
        if rev == self.HEAD and not self._has_head(): return None

        L = self._log(refspec=rev)
        if len(L) == 0:
            raise VcsError("Revision %s does not exist" % rev)
        elif len(L) > 1:
            raise VcsError("More than one instance of revision %s ?!?" % rev)
        else:
            return L[0]


    def get_files(self, rev=None):
        """Gets a list of files in revision rev"""
        if rev == None: rev = self.HEAD
        rev = self._sanitize_rev(rev)

        if rev:
            if rev == self.INDEX:  raw = self._git(self.path, ["ls-files"], catchout=True)
            else:                  raw = self._git(self.path, ['ls-tree', '--name-only', '-r', rev], catchout=True)
            return raw.split('\n')
        else:
            return []

# vim: expandtab:shiftwidth=4:tabstop=4:softtabstop=4:textwidth=80

########NEW FILE########
__FILENAME__ = hg
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# vcs - a python module to handle various version control systems
# Copyright 2011, 2012 Abdó Roig-Maranges <abdo.roig@gmail.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import shutil
from datetime import datetime
try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser

from .vcs import Vcs, VcsError


class Hg(Vcs):
    vcsname  = 'hg'
    HEAD = 'tip'
    # Auxiliar stuff
    #---------------------------

    def _hg(self, path, args, silent=True, catchout=False, bytes=False):
        return self._vcs(path, 'hg', args, silent=silent, catchout=catchout, bytes=bytes)


    def _has_head(self):
        """Checks whether repo has head"""
        rnum = self._hg(self.path, ['-q', 'identify', '--num', '-r', self.HEAD], catchout=True)
        return rnum != '-1'


    def _sanitize_rev(self, rev):
        if rev == None: return None
        rev = rev.strip()
        if len(rev) == 0: return None
        if rev[-1] == '+': rev = rev[:-1]

        try:
            if int(rev) == 0: return None
        except:
            pass

        return rev


    def _log(self, refspec=None, maxres=None, filelist=None):

        fmt = "changeset: {rev}:{node}\ntag: {tags}\nuser: {author}\ndate: {date}\nsummary: {desc}\n"
        args = ['log', '--template', fmt]

        if refspec:  args = args + ['--limit', '1', '-r', refspec]
        elif maxres: args = args + ['--limit', str(maxres)]

        if filelist: args = args + filelist

        raw = self._hg(self.path, args, catchout=True)
        L = re.findall('^changeset:\s*([0-9]*):([0-9a-zA-Z]*)\s*$\s*^tag:\s*(.*)\s*$\s*^user:\s*(.*)\s*$\s*^date:\s*(.*)$\s*^summary:\s*(.*)\s*$', raw, re.MULTILINE)

        log = []
        for t in L:
            dt = {}
            dt['short'] = t[0].strip()
            dt['revid'] = self._sanitize_rev(t[1].strip())
            dt['author'] = t[3].strip()
            m = re.match('\d+(\.\d+)?', t[4].strip())
            dt['date'] = datetime.fromtimestamp(float(m.group(0)))
            dt['summary'] = t[5].strip()
            log.append(dt)
        return log


    def _hg_file_status(self, st):
        if len(st) != 1: raise VcsError("Wrong hg file status string: %s" % st)
        if   st in "ARM":    return 'staged'
        elif st in "!":      return 'deleted'
        elif st in "I":      return 'ignored'
        elif st in "?":      return 'untracked'
        elif st in "X":      return 'conflict'
        elif st in "C":      return 'sync'
        else:                return 'unknown'



    # Repo creation
    #---------------------------

    def init(self):
        """Initializes a repo in current path"""
        self._hg(self.path, ['init'])
        self.update()


    def clone(self, src):
        """Clones a repo from src"""
        name = os.path.basename(self.path)
        path = os.path.dirname(self.path)
        try:
            os.rmdir(self.path)
        except OSError:
            raise VcsError("Can't clone to %s. It is not an empty directory" % self.path)

        self._hg(path, ['clone', src, name])
        self.update()



    # Action Interface
    #---------------------------

    def commit(self, message):
        """Commits with a given message"""
        self._hg(self.path, ['commit', '-m', message])


    def add(self, filelist=None):
        """Adds files to the index, preparing for commit"""
        if filelist != None: self._hg(self.path, ['addremove'] + filelist)
        else:                self._hg(self.path, ['addremove'])


    def reset(self, filelist=None):
        """Removes files from the index"""
        if filelist == None: filelist = self.get_status_allfiles().keys()
        self._hg(self.path, ['forget'] + filelist)


    def pull(self):
        """Pulls a hg repo"""
        self._hg(self.path, ['pull', '-u'])


    def push(self):
        """Pushes a hg repo"""
        self._hg(self.path, ['push'])


    def checkout(self, rev):
        """Checks out a branch or revision"""
        self._hg(self.path, ['update', rev])


    def extract_file(self, rev, name, dest):
        """Extracts a file from a given revision and stores it in dest dir"""
        if rev == self.INDEX:
            shutil.copyfile(os.path.join(self.path, name), dest)
        else:
            self._hg(self.path, ['cat', '--rev', rev, '--output', dest, name])


    # Data Interface
    #---------------------------

    def get_status_allfiles(self):
        """Returns a dict indexed by files not in sync their status as values.
           Paths are given relative to the root. Strips trailing '/' from dirs."""
        raw = self._hg(self.path, ['status'], catchout=True, bytes=True)
        L = re.findall('^(.)\s*(.*?)\s*$', raw.decode('utf-8'), re.MULTILINE)
        ret = {}
        for st, p in L:
            # Detect conflict by the existence of .orig files
            if st == '?' and re.match('^.*\.orig\s*$', p):  st = 'X'
            sta = self._hg_file_status(st)
            ret[os.path.normpath(p.strip())] = sta
        return ret


    def get_ignore_allfiles(self):
        """Returns a set of all the ignored files in the repo"""
        raw = self._hg(self.path, ['status', '-i'], catchout=True, bytes=True)
        L = re.findall('^I\s*(.*?)\s*$', raw.decode('utf-8'), re.MULTILINE)
        return set(L)


    def get_remote_status(self):
        """Checks the status of the repo regarding sync state with remote branch"""
        if self.get_remote() == None:
            return "none"

        ahead = behind = True
        try:
            self._hg(self.path, ['outgoing'], silent=True)
        except:
            ahead = False

        try:
            self._hg(self.path, ['incoming'], silent=True)
        except:
            behind = False

        if       ahead and     behind: return "diverged"
        elif     ahead and not behind: return "ahead"
        elif not ahead and     behind: return "behind"
        elif not ahead and not behind: return "sync"


    def get_branch(self):
        """Returns the current named branch, if this makes sense for the backend. None otherwise"""
        branch = self._hg(self.path, ['branch'], catchout=True)
        return branch or None


    def get_log(self, filelist=None, maxres=None):
        """Get the entire log for the current HEAD"""
        if not self._has_head(): return []
        return self._log(refspec=None, maxres=maxres, filelist=filelist)


    def get_raw_log(self, filelist=None):
        """Gets the raw log as a string"""
        if not self._has_head(): return []
        args = ['log']
        if filelist: args = args + filelist
        return self._hg(self.path, args, catchout=True)


    def get_raw_diff(self, refspec=None, filelist=None):
        """Gets the raw diff as a string"""
        args = ['diff', '--git']
        if refspec:  args = args + [refspec]
        if filelist: args = args + filelist
        return self._hg(self.path, args, catchout=True)


    def get_remote(self, rev=None):
        """Returns the url for the remote repo attached to head"""
        remote = self._hg(self.path, ['showconfig', 'paths.default'], catchout=True)
        return remote or None


    def get_revision_id(self, rev=None):
        """Get a canonical key for the revision rev"""
        if rev == None: rev = self.HEAD
        elif rev == self.INDEX: return None
        rev = self._sanitize_rev(rev)

        return self._sanitize_rev(self._hg(self.path, ['-q', 'identify', '--id', '-r', rev], catchout=True))


    def get_info(self, rev=None):
        """Gets info about the given revision rev"""
        if rev == None: rev = self.HEAD
        rev = self._sanitize_rev(rev)
        if rev == self.HEAD and not self._has_head(): return None

        L = self._log(refspec=rev)
        if len(L) == 0:
            raise VcsError("Revision %s does not exist" % rev)
        elif len(L) > 1:
            raise VcsError("More than one instance of revision %s ?!?" % rev)
        else:
            return L[0]


    def get_files(self, rev=None):
        """Gets a list of files in revision rev"""
        if rev == None: rev = self.HEAD
        rev = self._sanitize_rev(rev)

        if rev:
            if rev == self.INDEX: raw = self._hg(self.path, ['locate', "*"], catchout=True)
            else:                 raw = self._hg(self.path, ['locate', '--rev', rev, "*"], catchout=True)
            return raw.split('\n')
        else:
            return []


# vim: expandtab:shiftwidth=4:tabstop=4:softtabstop=4:textwidth=80

########NEW FILE########
__FILENAME__ = vcs
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# vcs - a python module to handle various version control systems
# Copyright 2011, 2012 Abdó Roig-Maranges <abdo.roig@gmail.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import subprocess
from datetime import datetime


class VcsError(Exception):
    pass


class Vcs(object):
    """ This class represents a version controlled path, abstracting the usual
        operations from the different supported backends.

        The backends are declared in te variable self.repo_types, and are derived
        classes from Vcs with the following restrictions:

         * do NOT implement __init__. Vcs takes care of this.

         * do not create change internal state. All internal state should be
           handled in Vcs

        Objects from backend classes should never be created directly. Instead
        create objects of Vcs class. The initialization calls update, which takes
        care of detecting the right Vcs backend to use and dynamically changes the
        object type accordingly.
        """

    # These are abstracted revs, representing the current index (staged files),
    # the current head and nothing. Every backend should redefine them if the
    # version control has a similar concept, or implement _sanitize_rev method to
    # clean the rev before using them
    INDEX    = "INDEX"
    HEAD     = "HEAD"
    NONE     = "NONE"
    vcsname  = None

    # Possible status responses
    FILE_STATUS   = ['conflict', 'untracked', 'deleted', 'changed', 'staged', 'ignored', 'sync', 'none', 'unknown']
    REMOTE_STATUS = ['none', 'sync', 'behind', 'ahead', 'diverged', 'unknown']


    def __init__(self, path, vcstype=None):
        # This is a bit hackish, but I need to import here to avoid circular imports
        from .git import Git
        from .hg  import Hg
        from .bzr import Bzr
        self.repo_types  = {'git': Git, 'hg': Hg, 'bzr': Bzr}

        self.path = os.path.expanduser(path)
        self.status = {}
        self.ignored = set()
        self.root = None

        self.update(vcstype=vcstype)


    # Auxiliar
    #---------------------------

    def _vcs(self, path, cmd, args, silent=False, catchout=False, bytes=False):
        """Executes a vcs command"""
        with open('/dev/null', 'w') as devnull:
            if silent: out=devnull
            else:      out=None
            try:
                if catchout:
                    raw = subprocess.check_output([cmd] + args, stderr=out, cwd=path)
                    if bytes: return raw
                    else:     return raw.decode('utf-8', errors="ignore").strip()
                else:
                    subprocess.check_call([cmd] + args, stderr=out, stdout=out, cwd=path)
            except subprocess.CalledProcessError:
                raise VcsError("%s error on %s. Command: %s" % (cmd, path, ' '.join([cmd] + args)))


    def _path_contains(self, parent, path):
        """Checks wether path is an object belonging to the subtree in parent"""
        if parent == path: return True
        parent = os.path.normpath(parent + '/')
        path = os.path.normpath(path)
        return os.path.commonprefix([parent, path]) == parent


    # Object manipulation
    #---------------------------
    # This may be a little hacky, but very useful. An instance of Vcs class changes its own class
    # when calling update(), to match the right repo type. I can have the same object adapt to
    # the path repo type, if this ever changes!

    def get_repo_type(self, path):
        """Returns the right repo type for path. None if no repo present in path"""
        for rn, rt in self.repo_types.items():
            if path and os.path.exists(os.path.join(path, '.%s' % rn)): return rt
        return None


    def get_root(self, path):
        """Finds the repository root path. Otherwise returns none"""
        curpath = os.path.abspath(path)
        while curpath != '/':
            if self.get_repo_type(curpath): return curpath
            else:                           curpath = os.path.dirname(curpath)
        return None


    def update(self, vcstype=None):
        """Updates the repo instance. Re-checks the repo and changes object class if repo type changes
           If vcstype is given, uses that repo type, without autodetection"""
        if os.path.exists(self.path):
            self.root = self.get_root(self.path)
            if vcstype:
                if vcstype in self.repo_types:
                    ty = self.repo_types[vcstype]
                else:
                    raise VcsError("Unrecognized repo type %s" % vcstype)
            else:
                ty = self.get_repo_type(self.root)
            if ty:
                self.__class__ = ty
                return

        self.__class__ = Vcs


    # Repo creation
    #---------------------------

    def init(self, repotype):
        """Initializes a repo in current path"""
        if not repotype in self.repo_types:
            raise VcsError("Unrecognized repo type %s" % repotype)

        if not os.path.exists(self.path): os.makedirs(self.path)
        rt = self.repo_types[repotype]
        try:
            self.__class__ = rt
            self.init()
        except:
            self.__class__ = Vcs
            raise


    def clone(self, repotype, src):
        """Clones a repo from src"""
        if not repotype in self.repo_types:
            raise VcsError("Unrecognized repo type %s" % repotype)

        if not os.path.exists(self.path): os.makedirs(self.path)
        rt = self.repo_types[repotype]
        try:
            self.__class__ = rt
            self.clone(src)
        except:
            self.__class__ = Vcs
            raise


    # Action interface
    #---------------------------

    def commit(self, message):
        """Commits with a given message"""
        raise NotImplementedError


    def add(self, filelist):
        """Adds files to the index, preparing for commit"""
        raise NotImplementedError


    def reset(self, filelist):
        """Removes files from the index"""
        raise NotImplementedError


    def pull(self):
        """Pulls from remote"""
        raise NotImplementedError


    def push(self):
        """Pushes to remote"""
        raise NotImplementedError


    def checkout(self, rev):
        """Checks out a branch or revision"""
        raise NotImplementedError


    def extract_file(self, rev, name, dest):
        """Extracts a file from a given revision and stores it in dest dir"""
        raise NotImplementedError


    # Data
    #---------------------------

    def is_repo(self):
        """Checks wether there is an initialized repo in self.path"""
        return self.path and os.path.exists(self.path) and self.root != None


    def is_tracking(self):
        """Checks whether HEAD is tracking a remote repo"""
        return self.get_remote(self.HEAD) != None


    def get_file_status(self, path):
        """Returns the status for a given path regarding the repo"""

        # if path is relative, join it with root. otherwise do nothing
        path = os.path.join(self.root, path)

        # path is not in the repo
        if not self._path_contains(self.root, path):
            return "none"

        # check if prel or some parent of prel is ignored
        prel = os.path.relpath(path, self.root)
        while len(prel) > 0 and prel != '/' and prel != '.':
            if prel in self.ignored: return "ignored"
            prel, tail = os.path.split(prel)

        # check if prel or some parent of prel is listed in status
        prel = os.path.relpath(path, self.root)
        while len(prel) > 0 and prel != '/' and prel != '.':
            if prel in self.status: return self.status[prel]
            prel, tail = os.path.split(prel)

        # check if prel is a directory that contains some file in status
        prel = os.path.relpath(path, self.root)
        if os.path.isdir(path):
            sts = set(st for p, st in self.status.items()
                      if self._path_contains(path, os.path.join(self.root, p)))
            for st in self.FILE_STATUS:
                if st in sts: return st

        # it seems prel is in sync
        return "sync"


    def get_status(self, path=None):
        """Returns a dict with changed files under path and their status.
           If path is None, returns all changed files"""

        self.status = self.get_status_allfiles()
        self.ignored = self.get_ignore_allfiles()
        if path:
            path = os.path.join(self.root, path)
            if os.path.commonprefix([self.root, path]) == self.root:
                return dict((p, st) for p, st in self.status.items() if self._path_contains(path, os.path.join(self.root, p)))
            else:
                return {}
        else:
            return self.status


    def get_status_allfiles(self):
        """Returns a dict indexed by files not in sync their status as values.
           Paths are given relative to the root.  Strips trailing '/' from dirs."""
        raise NotImplementedError


    def get_ignore_allfiles(self):
        """Returns a set of all the ignored files in the repo. Strips trailing '/' from dirs."""
        raise NotImplementedError


    def get_remote_status(self):
        """Checks the status of the entire repo"""
        raise NotImplementedError


    def get_branch(self):
        """Returns the current named branch, if this makes sense for the backend. None otherwise"""
        raise NotImplementedError


    def get_log(self):
        """Get the entire log for the current HEAD"""
        raise NotImplementedError


    def get_raw_log(self, filelist=None):
        """Gets the raw log as a string"""
        raise NotImplementedError


    def get_raw_diff(self, refspec=None, filelist=None):
        """Gets the raw diff as a string"""
        raise NotImplementedError


    def get_remote(self):
        """Returns the url for the remote repo attached to head"""
        raise NotImplementedError


    def get_revision_id(self, rev=None):
        """Get a canonical key for the revision rev"""
        raise NotImplementedError


    def get_info(self, rev=None):
        """Gets info about the given revision rev"""
        raise NotImplementedError


    def get_files(self, rev=None):
        """Gets a list of files in revision rev"""
        raise NotImplementedError



    # I / O
    #---------------------------

    def print_log(self, fmt):
        log = self.log()
        if fmt == "compact":
            for dt in log:
                print(self.format_revision_compact(dt))
        else:
            raise Exception("Unknown format %s" % fmt)


    def format_revision_compact(self, dt):
        return "{0:<10}{1:<20}{2}".format(dt['revshort'],
                                          dt['date'].strftime('%a %b %d, %Y'),
                                          dt['summary'])


    def format_revision_text(self, dt):
        L = ["revision:         %s:%s" % (dt['revshort'], dt['revhash']),
             "date:             %s" % dt['date'].strftime('%a %b %d, %Y'),
             "time:             %s" % dt['date'].strftime('%H:%M'),
             "user:             %s" % dt['author'],
             "description:      %s" % dt['summary']]
        return '\n'.join(L)

########NEW FILE########
__FILENAME__ = widestring
# -*- encoding: utf8 -*-
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

import sys
from unicodedata import east_asian_width

PY3 = sys.version > '3'
ASCIIONLY = set(chr(c) for c in range(1, 128))
NARROW = 1
WIDE = 2
WIDE_SYMBOLS = set('WF')

def uwid(string):
    """Return the width of a string"""
    if not PY3:
        string = string.decode('utf-8', 'ignore')
    return sum(utf_char_width(c) for c in string)


def utf_char_width(string):
    """Return the width of a single character"""
    if east_asian_width(string) in WIDE_SYMBOLS:
        return WIDE
    return NARROW


def string_to_charlist(string):
    """Return a list of characters with extra empty strings after wide chars"""
    if not set(string) - ASCIIONLY:
        return list(string)
    result = []
    if PY3:
        for c in string:
            result.append(c)
            if east_asian_width(c) in WIDE_SYMBOLS:
                result.append('')
    else:
        try:
            # This raised a "UnicodeEncodeError: 'ascii' codec can't encode
            # character u'\xe4' in position 10: ordinal not in range(128)"
            # for me once.  I thought errors='ignore' means IGNORE THE DAMN
            # ERRORS but apparently it doesn't.
            string = string.decode('utf-8', 'ignore')
        except UnicodeEncodeError:
            return []
        for c in string:
            result.append(c.encode('utf-8'))
            if east_asian_width(c) in WIDE_SYMBOLS:
                result.append('')
    return result


class WideString(object):
    def __init__(self, string, chars=None):
        try:
            self.string = str(string)
        except UnicodeEncodeError:
            # Here I assume that string is a "unicode" object, because why else
            # would str(string) raise a UnicodeEncodeError?
            try:
                self.string = string.encode('latin-1', 'ignore')
            except:
                self.string = ""
        if chars is None:
            self.chars = string_to_charlist(string)
        else:
            self.chars = chars

    def __add__(self, string):
        """
        >>> (WideString("a") + WideString("b")).string
        'ab'
        >>> (WideString("a") + WideString("b")).chars
        ['a', 'b']
        >>> (WideString("afd") + "bc").chars
        ['a', 'f', 'd', 'b', 'c']
        """
        if isinstance(string, str):
            return WideString(self.string + string)
        elif isinstance(string, WideString):
            return WideString(self.string + string.string,
                    self.chars + string.chars)

    def __radd__(self, string):
        """
        >>> ("bc" + WideString("afd")).chars
        ['b', 'c', 'a', 'f', 'd']
        """
        if isinstance(string, str):
            return WideString(string + self.string)
        elif isinstance(string, WideString):
            return WideString(string.string + self.string,
                    string.chars + self.chars)

    def __str__(self):
        return self.string

    def __repr__(self):
        return '<' + self.__class__.__name__ + " '" + self.string + "'>"

    def __getslice__(self, a, z):
        """
        >>> WideString("asdf")[1:3]
        <WideString 'sd'>
        >>> WideString("asdf")[1:-100]
        <WideString ''>
        >>> WideString("モヒカン")[2:4]
        <WideString 'ヒ'>
        >>> WideString("モヒカン")[2:5]
        <WideString 'ヒ '>
        >>> WideString("モabカン")[2:5]
        <WideString 'ab '>
        >>> WideString("モヒカン")[1:5]
        <WideString ' ヒ '>
        >>> WideString("モヒカン")[:]
        <WideString 'モヒカン'>
        >>> WideString("aモ")[0:3]
        <WideString 'aモ'>
        >>> WideString("aモ")[0:2]
        <WideString 'a '>
        >>> WideString("aモ")[0:1]
        <WideString 'a'>
        """
        if z is None or z > len(self.chars):
            z = len(self.chars)
        if z < 0:
            z = len(self.chars) + z
        if z < 0:
            return WideString("")
        if a is None or a < 0:
            a = 0
        if z < len(self.chars) and self.chars[z] == '':
            if self.chars[a] == '':
                return WideString(' ' + ''.join(self.chars[a:z - 1]) + ' ')
            return WideString(''.join(self.chars[a:z - 1]) + ' ')
        if self.chars[a] == '':
            return WideString(' ' + ''.join(self.chars[a:z - 1]))
        return WideString(''.join(self.chars[a:z]))

    def __getitem__(self, i):
        """
        >>> WideString("asdf")[2]
        <WideString 'd'>
        >>> WideString("……")[0]
        <WideString '…'>
        >>> WideString("……")[1]
        <WideString '…'>
        """
        if isinstance(i, slice):
            return self.__getslice__(i.start, i.stop)
        return self.__getslice__(i, i+1)

    def __len__(self):
        """
        >>> len(WideString("poo"))
        3
        >>> len(WideString("モヒカン"))
        8
        """
        return len(self.chars)


if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = fsobject
# THIS WHOLE FILE IS OBSOLETE AND EXISTS FOR BACKWARDS COMPATIBILITIY

from ranger.container.fsobject import FileSystemObject, BAD_INFO
from ranger.container.file import File
from ranger.container.directory import Directory

########NEW FILE########
__FILENAME__ = ansi
# Copyright (C) 2010 David Barnett <davidbarnett2@gmail.com>
# Copyright (C) 2010-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""A library to help to convert ANSI codes to curses instructions."""

from ranger.gui import color
import re

ansi_re = re.compile('(\x1b' + r'\[\d*(?:;\d+)*?[a-zA-Z])')
codesplit_re = re.compile('38;5;(\d+);|48;5;(\d+);|(\d*);')
reset = '\x1b[0m'

def split_ansi_from_text(ansi_text):
    return ansi_re.split(ansi_text)

# For information on the ANSI codes see
# githttp://en.wikipedia.org/wiki/ANSI_escape_code
def text_with_fg_bg_attr(ansi_text):
    fg, bg, attr = -1, -1, 0
    for chunk in split_ansi_from_text(ansi_text):
        if chunk and chunk[0] == '\x1b':
            if chunk[-1] != 'm':
                continue
            match = re.match(r'^.\[(.*).$', chunk)
            if not match:
                # XXX I have no test case to determine what should happen here
                continue
            attr_args = match.group(1)

            # Convert arguments to attributes/colors
            for x256fg, x256bg, arg in codesplit_re.findall(attr_args + ';'):
                # first handle xterm256 codes
                try:
                    if len(x256fg) > 0:           # xterm256 foreground
                        fg = int(x256fg)
                        continue
                    elif len(x256bg) > 0:         # xterm256 background
                        bg = int(x256bg)
                        continue
                    elif len(arg) > 0:            # usual ansi code
                        n = int(arg)
                    else:                         # empty code means reset
                        n = 0
                except:
                    continue

                if n == 0:                        # reset colors and attributes
                    fg, bg, attr = -1, -1, 0

                elif n == 1:                      # enable attribute
                    attr |= color.bold
                elif n == 4:
                    attr |= color.underline
                elif n == 5:
                    attr |= color.blink
                elif n == 7:
                    attr |= color.reverse
                elif n == 8:
                    attr |= color.invisible

                elif n == 22:                     # disable attribute
                    attr &= not color.bold
                elif n == 24:
                    attr &= not color.underline
                elif n == 25:
                    attr &= not color.blink
                elif n == 27:
                    attr &= not color.reverse
                elif n == 28:
                    attr &= not color.invisible

                elif n >= 30 and n <= 37:         # 8 ansi foreground and background colors
                    fg = n - 30
                elif n == 39:
                    fg = -1
                elif n >= 40 and n <= 47:
                    bg = n - 40
                elif n == 49:
                    bg = -1

                elif n >= 90 and n <= 97:         # 8 aixterm high intensity colors (light but not bold)
                    fg = n - 90 + 8
                elif n == 99:
                    fg = -1
                elif n >= 100 and n <= 107:
                    bg = n - 100 + 8
                elif n == 109:
                    bg = -1

            yield (fg, bg, attr)

        else:
            yield chunk

def char_len(ansi_text):
    """Count the number of visible characters.

    >>> char_len("\x1b[0;30;40mX\x1b[0m")
    1
    >>> char_len("\x1b[0;30;40mXY\x1b[0m")
    2
    >>> char_len("\x1b[0;30;40mX\x1b[0mY")
    2
    >>> char_len("hello")
    5
    >>> char_len("")
    0
    """
    return len(ansi_re.sub('', ansi_text))

def char_slice(ansi_text, start, length):
    """Slices a string with respect to ansi code sequences

    Acts as if the ansi codes aren't there, slices the text from the
    given start point to the given length and adds the codes back in.

    >>> test_string = "abcde\x1b[30mfoo\x1b[31mbar\x1b[0mnormal"
    >>> split_ansi_from_text(test_string)
    ['abcde', '\\x1b[30m', 'foo', '\\x1b[31m', 'bar', '\\x1b[0m', 'normal']
    >>> char_slice(test_string, 1, 3)
    'bcd'
    >>> char_slice(test_string, 5, 6)
    '\\x1b[30mfoo\\x1b[31mbar'
    >>> char_slice(test_string, 0, 8)
    'abcde\\x1b[30mfoo'
    >>> char_slice(test_string, 4, 4)
    'e\\x1b[30mfoo'
    >>> char_slice(test_string, 11, 100)
    '\\x1b[0mnormal'
    >>> char_slice(test_string, 9, 100)
    '\\x1b[31mar\\x1b[0mnormal'
    >>> char_slice(test_string, 9, 4)
    '\\x1b[31mar\\x1b[0mno'
    """
    chunks = []
    last_color = ""
    pos = old_pos = 0
    for i, chunk in enumerate(split_ansi_from_text(ansi_text)):
        if i % 2 == 1:
            last_color = chunk
            continue

        old_pos = pos
        pos += len(chunk)
        if pos <= start:
            pass # seek
        elif old_pos < start and pos >= start:
            chunks.append(last_color)
            chunks.append(chunk[start-old_pos:start-old_pos+length])
        elif pos > length + start:
            chunks.append(last_color)
            chunks.append(chunk[:start-old_pos+length])
        else:
            chunks.append(last_color)
            chunks.append(chunk)
        if pos - start >= length:
            break
    return ''.join(chunks)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = bar
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

from ranger.ext.widestring import WideString, utf_char_width
import sys
PY3 = sys.version > '3'

class Bar(object):
    left = None
    right = None
    gap = None

    def __init__(self, base_color_tag):
        self.left = BarSide(base_color_tag)
        self.right = BarSide(base_color_tag)
        self.gap = BarSide(base_color_tag)

    def add(self, *a, **kw):
        self.left.add(*a, **kw)

    def addright(self, *a, **kw):
        self.right.add(*a, **kw)

    def sumsize(self):
        return self.left.sumsize() + self.right.sumsize()

    def fixedsize(self):
        return self.left.fixedsize() + self.right.fixedsize()

    def shrink_by_removing(self, wid):
        leftsize = self.left.sumsize()
        rightsize = self.right.sumsize()
        sumsize = leftsize + rightsize

        # remove elemets from the left until it fits
        if sumsize > wid:
            while len(self.left) > 0:
                leftsize -= len(self.left.pop(-1))
                if leftsize + rightsize <= wid:
                    break
            sumsize = leftsize + rightsize

            # remove elemets from the right until it fits
            if sumsize > wid:
                while len(self.right) > 0:
                    rightsize -= len(self.right.pop(0))
                    if leftsize + rightsize <= wid:
                        break
                sumsize = leftsize + rightsize

        if sumsize < wid:
            self.fill_gap(' ', (wid - sumsize), gapwidth=True)

    def shrink_from_the_left(self, wid):
        fixedsize = self.fixedsize()
        if wid < fixedsize:
            raise ValueError("Cannot shrink down to that size by cutting")
        leftsize = self.left.sumsize()
        rightsize = self.right.sumsize()
        oversize = leftsize + rightsize - wid
        if oversize <= 0:
            return self.fill_gap(' ', wid, gapwidth=False)

        # Shrink items to a minimum size until there is enough room.
        for item in self.left:
            if not item.fixed:
                itemlen = len(item)
                if oversize > itemlen - item.min_size:
                    item.cut_off_to(item.min_size)
                    oversize -= (itemlen - item.min_size)
                else:
                    item.cut_off(oversize)
                    break

    def fill_gap(self, char, wid, gapwidth=False):
        del self.gap[:]

        if not gapwidth:
            wid = wid - self.sumsize()

        if wid > 0:
            self.gap.add(char * wid, 'space')

    def combine(self):
        return self.left + self.gap + self.right


class BarSide(list):
    def __init__(self, base_color_tag):
        self.base_color_tag = base_color_tag

    def add(self, string, *lst, **kw):
        cs = ColoredString(string, self.base_color_tag, *lst)
        cs.__dict__.update(kw)
        self.append(cs)

    def add_space(self, n=1):
        self.add(' ' * n, 'space')

    def sumsize(self):
        return sum(len(item) for item in self)

    def fixedsize(self):
        n = 0
        for item in self:
            if item.fixed:
                n += len(item)
            else:
                n += item.min_size
        return n


class ColoredString(object):
    def __init__(self, string, *lst):
        self.string = WideString(string)
        self.lst = lst
        self.fixed = False
        if not len(string) or not len(self.string.chars):
            self.min_size = 0
        elif PY3:
            self.min_size = utf_char_width(string[0])
        else:
            self.min_size = utf_char_width(self.string.chars[0].decode('utf-8'))

    def cut_off(self, n):
        if n >= 1:
            self.string = self.string[:-n]

    def cut_off_to(self, n):
        if n < self.min_size:
            self.string = self.string[:self.min_size]
        elif n < len(self.string):
            self.string = self.string[:n]

    def __len__(self):
        return len(self.string)

    def __str__(self):
        return str(self.string)

########NEW FILE########
__FILENAME__ = color
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""Contains abbreviations to curses color/attribute constants.

Multiple attributes can be combined with the | (or) operator, toggled
with ^ (xor) and checked for with & (and). Examples:

attr = bold | underline
attr |= reverse
bool(attr & reverse) # => True
attr ^= reverse
bool(attr & reverse) # => False
"""

import curses

DEFAULT_FOREGROUND = curses.COLOR_WHITE
DEFAULT_BACKGROUND = curses.COLOR_BLACK
COLOR_PAIRS = {10: 0}

def get_color(fg, bg):
    """Returns the curses color pair for the given fg/bg combination."""

    key = (fg, bg)
    if key not in COLOR_PAIRS:
        size = len(COLOR_PAIRS)
        try:
            curses.init_pair(size, fg, bg)
        except:
            # If curses.use_default_colors() failed during the initialization
            # of curses, then using -1 as fg or bg will fail as well, which
            # we need to handle with fallback-defaults:
            if fg == -1:  # -1 is the "default" color
                fg = DEFAULT_FOREGROUND
            if bg == -1:  # -1 is the "default" color
                bg = DEFAULT_BACKGROUND
            curses.init_pair(size, fg, bg)
        COLOR_PAIRS[key] = size

    return COLOR_PAIRS[key]

black   = curses.COLOR_BLACK
blue    = curses.COLOR_BLUE
cyan    = curses.COLOR_CYAN
green   = curses.COLOR_GREEN
magenta = curses.COLOR_MAGENTA
red     = curses.COLOR_RED
white   = curses.COLOR_WHITE
yellow  = curses.COLOR_YELLOW
default = -1

normal     = curses.A_NORMAL
bold       = curses.A_BOLD
blink      = curses.A_BLINK
reverse    = curses.A_REVERSE
underline  = curses.A_UNDERLINE
invisible  = curses.A_INVIS

default_colors = (default, default, normal)

########NEW FILE########
__FILENAME__ = colorscheme
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""Colorschemes define colors for specific contexts.

Generally, this works by passing a set of keywords (strings) to
the colorscheme.get() method to receive the tuple (fg, bg, attr).
fg, bg are the foreground and background colors and attr is the attribute.
The values are specified in ranger.gui.color.

A colorscheme must...

1. be inside either of these directories:
~/.config/ranger/colorschemes/
path/to/ranger/colorschemes/

2. be a subclass of ranger.gui.colorscheme.ColorScheme

3. implement a use(self, context) method which returns (fg, bg, attr).
context is a struct which contains all entries of CONTEXT_KEYS,
associated with either True or False.

define which colorscheme to use by having this to your options.py:
from ranger import colorschemes
colorscheme = "name"
"""

import os
from curses import color_pair

import ranger
from ranger.gui.color import get_color
from ranger.gui.context import Context
from ranger.core.main import allow_access_to_confdir
from ranger.ext.cached_function import cached_function
from ranger.ext.iter_tools import flatten

class ColorScheme(object):
    """This is the class that colorschemes must inherit from.

    it defines the get() method, which returns the color tuple
    which fits to the given keys.
    """

    @cached_function
    def get(self, *keys):
        """Returns the (fg, bg, attr) for the given keys.

        Using this function rather than use() will cache all
        colors for faster access.
        """
        context = Context(keys)
        color = self.use(context)
        if len(color) != 3 or not all(isinstance(value, int) \
                for value in color):
            raise ValueError("Bad Value from colorscheme.  Need "
                "a tuple of (foreground_color, background_color, attribute).")
        return color

    @cached_function
    def get_attr(self, *keys):
        """Returns the curses attribute for the specified keys

        Ready to use for curses.setattr()
        """
        fg, bg, attr = self.get(*flatten(keys))
        return attr | color_pair(get_color(fg, bg))

    def use(self, context):
        """Use the colorscheme to determine the (fg, bg, attr) tuple.

        Override this method in your own colorscheme.
        """
        return (-1, -1, 0)

def _colorscheme_name_to_class(signal):
    # Find the colorscheme.  First look in ~/.config/ranger/colorschemes,
    # then at RANGERDIR/colorschemes.  If the file contains a class
    # named Scheme, it is used.  Otherwise, an arbitrary other class
    # is picked.
    if isinstance(signal.value, ColorScheme): return

    if not signal.value:
        signal.value = 'default'

    scheme_name = signal.value
    usecustom = not ranger.arg.clean

    def exists(colorscheme):
        return os.path.exists(colorscheme + '.py')

    def is_scheme(x):
        try:
            return issubclass(x, ColorScheme)
        except:
            return False

    # create ~/.config/ranger/colorschemes/__init__.py if it doesn't exist
    if usecustom:
        if os.path.exists(signal.fm.confpath('colorschemes')):
            initpy = signal.fm.confpath('colorschemes', '__init__.py')
            if not os.path.exists(initpy):
                open(initpy, 'a').close()

    if usecustom and \
            exists(signal.fm.confpath('colorschemes', scheme_name)):
        scheme_supermodule = 'colorschemes'
    elif exists(signal.fm.relpath('colorschemes', scheme_name)):
        scheme_supermodule = 'ranger.colorschemes'
        usecustom = False
    else:
        scheme_supermodule = None  # found no matching file.

    if scheme_supermodule is None:
        if signal.previous and isinstance(signal.previous, ColorScheme):
            signal.value = signal.previous
        else:
            signal.value = ColorScheme()
        raise Exception("Cannot locate colorscheme `%s'" % scheme_name)
    else:
        if usecustom: allow_access_to_confdir(ranger.arg.confdir, True)
        scheme_module = getattr(__import__(scheme_supermodule,
                globals(), locals(), [scheme_name], 0), scheme_name)
        if usecustom: allow_access_to_confdir(ranger.arg.confdir, False)
        if hasattr(scheme_module, 'Scheme') \
                and is_scheme(scheme_module.Scheme):
            signal.value = scheme_module.Scheme()
        else:
            for var in scheme_module.__dict__.values():
                if var != ColorScheme and is_scheme(var):
                    signal.value = var()
                    break
            else:
                raise Exception("The module contains no valid colorscheme!")

########NEW FILE########
__FILENAME__ = context
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

CONTEXT_KEYS = ['reset', 'error', 'badinfo',
        'in_browser', 'in_statusbar', 'in_titlebar', 'in_console',
        'in_pager', 'in_taskview',
        'directory', 'file', 'hostname',
        'executable', 'media', 'link', 'fifo', 'socket', 'device',
        'video', 'audio', 'image', 'media', 'document', 'container',
        'selected', 'empty', 'main_column', 'message', 'background',
        'good', 'bad',
        'space', 'permissions', 'owner', 'group', 'mtime', 'nlink',
        'scroll', 'all', 'bot', 'top', 'percentage', 'filter',
        'marked', 'tagged', 'tag_marker', 'cut', 'copied',
        'help_markup', # COMPAT
        'seperator', 'key', 'special', 'border', # COMPAT
        'title', 'text', 'highlight', 'bars', 'quotes', 'tab', 'loaded',
        'keybuffer',
        'infostring',
        'vcsfile', 'vcsremote', 'vcsinfo', 'vcscommit',
        'vcsconflict', 'vcschanged', 'vcsunknown', 'vcsignored',
        'vcsstaged', 'vcssync', 'vcsbehind', 'vcsahead', 'vcsdiverged']

class Context(object):
    def __init__(self, keys):
        # set all given keys to True
        d = self.__dict__
        for key in keys:
            d[key] = True

# set all keys to False
for key in CONTEXT_KEYS:
    setattr(Context, key, False)

########NEW FILE########
__FILENAME__ = curses_shortcuts
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# Copyright (C) 2010 David Barnett <davidbarnett2@gmail.com>
# This software is distributed under the terms of the GNU GPL version 3.

import curses
import _curses
import sys

from ranger.gui.color import get_color
from ranger.core.shared import SettingsAware

REVERSE_ADDCH_ARGS = sys.version[0:5] == '3.4.0'

def _fix_surrogates(args):
    return [isinstance(arg, str) and arg.encode('utf-8', 'surrogateescape')
            .decode('utf-8', 'replace') or arg for arg in args]

class CursesShortcuts(SettingsAware):
    """This class defines shortcuts to faciliate operations with curses.

    color(*keys) -- sets the color associated with the keys from
        the current colorscheme.
    color_at(y, x, wid, *keys) -- sets the color at the given position
    color_reset() -- resets the color to the default
    addstr(*args) -- failsafe version of self.win.addstr(*args)
    """

    def addstr(self, *args):
        try:
            self.win.addstr(*args)
        except:
            if len(args) > 1:
                try:
                    self.win.addstr(*_fix_surrogates(args))
                except:
                    pass

    def addnstr(self, *args):
        try:
            self.win.addnstr(*args)
        except:
            if len(args) > 2:
                try:
                    self.win.addnstr(*_fix_surrogates(args))
                except:
                    pass

    def addch(self, *args):
        if REVERSE_ADDCH_ARGS and len(args) >= 3:
            args = [args[1], args[0]] + list(args[2:])
        try:
            self.win.addch(*args)
        except:
            pass

    def color(self, *keys):
        """Change the colors from now on."""
        attr = self.settings.colorscheme.get_attr(*keys)
        try:
            self.win.attrset(attr)
        except _curses.error:
            pass

    def color_at(self, y, x, wid, *keys):
        """Change the colors at the specified position"""
        attr = self.settings.colorscheme.get_attr(*keys)
        try:
            self.win.chgat(y, x, wid, attr)
        except _curses.error:
            pass

    def set_fg_bg_attr(self, fg, bg, attr):
        try:
            self.win.attrset(curses.color_pair(get_color(fg, bg)) | attr)
        except _curses.error:
            pass

    def color_reset(self):
        """Change the colors to the default colors"""
        CursesShortcuts.color(self, 'reset')

########NEW FILE########
__FILENAME__ = displayable
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

from ranger.core.shared import FileManagerAware, EnvironmentAware
from ranger.gui.curses_shortcuts import CursesShortcuts

class Displayable(EnvironmentAware, FileManagerAware, CursesShortcuts):
    """Displayables are objects which are displayed on the screen.

    This is just the abstract class, defining basic operations
    such as resizing, printing, changing colors.
    Subclasses of displayable can extend these methods:

    draw() -- draw the object. Is only called if visible.
    poke() -- is called just before draw(), even if not visible.
    finalize() -- called after all objects finished drawing.
    click(event) -- called with a MouseEvent. This is called on all
        visible objects under the mouse, until one returns True.
    press(key) -- called after a key press on focused objects.
    destroy() -- called before destroying the displayable object

    Additionally, there are these methods:

    __contains__(item) -- is the item (y, x) inside the widget?

    These attributes are set:

    Modifiable:
        focused -- Focused objects receive press() calls.
        visible -- Visible objects receive draw() and finalize() calls
        need_redraw -- Should the widget be redrawn? This variable may
            be set at various places in the script and should eventually be
            handled (and unset) in the draw() method.

    Read-Only: (i.e. reccomended not to change manually)
        win -- the own curses window object
        parent -- the parent (DisplayableContainer) object or None
        x, y, wid, hei -- absolute coordinates and boundaries
        settings, fm -- inherited shared variables
    """

    def __init__(self, win, env=None, fm=None, settings=None):
        from ranger.gui.ui import UI
        if env is not None:
            self.env = env
        if fm is not None:
            self.fm = fm
        if settings is not None:
            self.settings = settings

        self.need_redraw = True
        self.focused = False
        self.visible = True
        self.x = 0
        self.y = 0
        self.wid = 0
        self.hei = 0
        self.paryx = (0, 0)
        self.parent = None

        self._old_visible = self.visible

        if win is not None:
            if isinstance(self, UI):
                self.win = win
            else:
                self.win = win.derwin(1, 1, 0, 0)

    def __nonzero__(self):
        """Always True"""
        return True
    __bool__ = __nonzero__

    def __contains__(self, item):
        """Checks if item is inside the boundaries.

        item can be an iterable like [y, x] or an object with x and y methods.
        """
        try:
            y, x = item.y, item.x
        except AttributeError:
            try:
                y, x = item
            except (ValueError, TypeError):
                return False

        return self.contains_point(y, x)

    def draw(self):
        """Draw the oject.

        Called on every main iteration if visible.  Containers should call
        draw() on their contained objects here.  Override this!
        """

    def destroy(self):
        """Called when the object is destroyed.

        Override this!
        """

    def contains_point(self, y, x):
        """Test whether the point lies inside this object.

        x and y should be absolute coordinates.
        """
        return (x >= self.x and x < self.x + self.wid) and \
                (y >= self.y and y < self.y + self.hei)

    def click(self, event):
        """Called when a mouse key is pressed and self.focused is True.

        Override this!
        """
        pass

    def press(self, key):
        """Called when a key is pressed and self.focused is True.

        Override this!
        """
        pass

    def poke(self):
        """Called before drawing, even if invisible"""
        if self._old_visible != self.visible:
            self._old_visible = self.visible
            self.need_redraw = True

            if not self.visible:
                self.win.erase()

    def finalize(self):
        """Called after every displayable is done drawing.

        Override this!
        """
        pass

    def resize(self, y, x, hei=None, wid=None):
        """Resize the widget"""
        do_move = True
        try:
            maxy, maxx = self.fm.ui.termsize
        except TypeError:
            pass
        else:
            if hei is None:
                hei = maxy - y

            if wid is None:
                wid = maxx - x

            if x < 0 or y < 0:
                self.fm.notify("Warning: Subwindow origin below zero for <%s> "
                    "(x = %d, y = %d)" % (self, x, y), bad=True)

            if x + wid > maxx or y + hei > maxy:
                self.fm.notify("Warning: Subwindow size out of bounds for <%s> "
                    "(x = %d, y = %d, hei = %d, wid = %d)" % (self,
                    x, y, hei, wid), bad=True)

        window_is_cleared = False

        if hei != self.hei or wid != self.wid:
            #log("resizing " + str(self))
            self.win.erase()
            self.need_redraw = True
            window_is_cleared = True
            try:
                self.win.resize(hei, wid)
            except:
                # Not enough space for resizing...
                try:
                    self.win.mvderwin(0, 0)
                    do_move = True
                    self.win.resize(hei, wid)
                except:
                    pass
                    #raise ValueError("Resizing Failed!")

            self.hei, self.wid = self.win.getmaxyx()

        if do_move or y != self.paryx[0] or x != self.paryx[1]:
            if not window_is_cleared:
                self.win.erase()
                self.need_redraw = True
            #log("moving " + str(self))
            try:
                self.win.mvderwin(y, x)
            except:
                pass

            self.paryx = self.win.getparyx()
            self.y, self.x = self.paryx
            if self.parent:
                self.y += self.parent.y
                self.x += self.parent.x

    def __str__(self):
        return self.__class__.__name__

class DisplayableContainer(Displayable):
    """DisplayableContainers are Displayables which contain other Displayables.

    This is also an abstract class. The methods draw, poke, finalize,
    click, press and destroy are extended here and will recursively
    call the function on all contained objects.

    New methods:

    add_child(object) -- add the object to the container.
    remove_child(object) -- remove the object from the container.

    New attributes:

    container -- a list with all contained objects (rw)
    """

    def __init__(self, win, env=None, fm=None, settings=None):
        if env is not None:
            self.env = env
        if fm is not None:
            self.fm = fm
        if settings is not None:
            self.settings = settings

        self.container = []

        Displayable.__init__(self, win)

    # ------------------------------------ extended or overidden methods

    def poke(self):
        """Recursively called on objects in container"""
        Displayable.poke(self)
        for displayable in self.container:
            displayable.poke()

    def draw(self):
        """Recursively called on visible objects in container"""
        for displayable in self.container:
            if self.need_redraw:
                displayable.need_redraw = True
            if displayable.visible:
                displayable.draw()

        self.need_redraw = False

    def finalize(self):
        """Recursively called on visible objects in container"""
        for displayable in self.container:
            if displayable.visible:
                displayable.finalize()

    def press(self, key):
        """Recursively called on objects in container"""
        focused_obj = self._get_focused_obj()

        if focused_obj:
            focused_obj.press(key)
            return True
        return False

    def click(self, event):
        """Recursively called on objects in container"""
        focused_obj = self._get_focused_obj()
        if focused_obj and focused_obj.click(event):
            return True

        for displayable in self.container:
            if displayable.visible and event in displayable:
                if displayable.click(event):
                    return True

        return False

    def destroy(self):
        """Recursively called on objects in container"""
        for displayable in self.container:
            displayable.destroy()

    # ----------------------------------------------- new methods

    def add_child(self, obj):
        """Add the objects to the container."""
        if obj.parent:
            obj.parent.remove_child(obj)
        self.container.append(obj)
        obj.parent = self

    def remove_child(self, obj):
        """Remove the object from the container."""
        try:
            self.container.remove(obj)
        except ValueError:
            pass
        else:
            obj.parent = None

    def _get_focused_obj(self):
        # Finds a focused displayable object in the container.
        for displayable in self.container:
            if displayable.focused:
                return displayable
            try:
                obj = displayable._get_focused_obj()
            except AttributeError:
                pass
            else:
                if obj is not None:
                    return obj
        return None

########NEW FILE########
__FILENAME__ = mouse_event
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

import curses

class MouseEvent(object):
    PRESSED = [ 0,
            curses.BUTTON1_PRESSED,
            curses.BUTTON2_PRESSED,
            curses.BUTTON3_PRESSED,
            curses.BUTTON4_PRESSED ]
    CTRL_SCROLLWHEEL_MULTIPLIER = 5

    def __init__(self, getmouse):
        """Creates a MouseEvent object from the result of win.getmouse()"""
        _, self.x, self.y, _, self.bstate = getmouse

        # x-values above ~220 suddenly became negative, apparently
        # it's sufficient to add 0xFF to fix that error.
        if self.x < 0:
            self.x += 0xFF

        if self.y < 0:
            self.y += 0xFF

    def pressed(self, n):
        """Returns whether the mouse key n is pressed"""
        try:
            return (self.bstate & MouseEvent.PRESSED[n]) != 0
        except:
            return False

    def mouse_wheel_direction(self):
        """Returns the direction of the scroll action, 0 if there was none"""
        # If the bstate > ALL_MOUSE_EVENTS, it's an invalid mouse button.
        # I interpret invalid buttons as "scroll down" because all tested
        # systems have a broken curses implementation and this is a workaround.
        if self.bstate & curses.BUTTON4_PRESSED:
            return self.ctrl() and -self.CTRL_SCROLLWHEEL_MULTIPLIER or -1
        elif self.bstate & curses.BUTTON2_PRESSED \
                or self.bstate > curses.ALL_MOUSE_EVENTS:
            return self.ctrl() and self.CTRL_SCROLLWHEEL_MULTIPLIER or 1
        else:
            return 0

    def ctrl(self):
        return self.bstate & curses.BUTTON_CTRL

    def alt(self):
        return self.bstate & curses.BUTTON_ALT

    def shift(self):
        return self.bstate & curses.BUTTON_SHIFT

    def key_invalid(self):
        return self.bstate > curses.ALL_MOUSE_EVENTS

########NEW FILE########
__FILENAME__ = ui
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

import os
import sys
import curses
import _curses

from .displayable import DisplayableContainer
from .mouse_event import MouseEvent
from ranger.ext.keybinding_parser import KeyBuffer, KeyMaps, ALT_KEY

MOUSEMASK = curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION

_ASCII = ''.join(chr(c) for c in range(32, 127))
def ascii_only(string):
    return ''.join(c if c in _ASCII else '?' for c in string)

def _setup_mouse(signal):
    if signal['value']:
        curses.mousemask(MOUSEMASK)
        curses.mouseinterval(0)

        ## this line solves this problem:
        ## If an action, following a mouse click, includes the
        ## suspension and re-initializion of the ui (e.g. running a
        ## file by clicking on its preview) and the next key is another
        ## mouse click, the bstate of this mouse event will be invalid.
        ## (atm, invalid bstates are recognized as scroll-down)
        curses.ungetmouse(0,0,0,0,0)
    else:
        curses.mousemask(0)

# TODO: progress bar
# TODO: branch view
class UI(DisplayableContainer):
    is_set_up = False
    load_mode = False
    is_on = False
    termsize = None

    def __init__(self, env=None, fm=None):
        self.keybuffer = KeyBuffer()
        self.keymaps = KeyMaps(self.keybuffer)

        if fm is not None:
            self.fm = fm

    def setup_curses(self):
        os.environ['ESCDELAY'] = '25'   # don't know a cleaner way
        try:
            self.win = curses.initscr()
        except _curses.error as e:
            if e.args[0] == "setupterm: could not find terminal":
                os.environ['TERM'] = 'linux'
                self.win = curses.initscr()
        self.keymaps.use_keymap('browser')
        DisplayableContainer.__init__(self, None)

    def initialize(self):
        """initialize curses, then call setup (at the first time) and resize."""
        self.win.leaveok(0)
        self.win.keypad(1)
        self.load_mode = False

        curses.cbreak()
        curses.noecho()
        curses.halfdelay(20)
        try:
            curses.curs_set(int(bool(self.settings.show_cursor)))
        except:
            pass
        curses.start_color()
        try:
            curses.use_default_colors()
        except:
            pass

        self.settings.signal_bind('setopt.mouse_enabled', _setup_mouse)
        _setup_mouse(dict(value=self.settings.mouse_enabled))

        if not self.is_set_up:
            self.is_set_up = True
            self.setup()
            self.win.addstr("loading...")
            self.win.refresh()
            self._draw_title = curses.tigetflag('hs') # has_status_line
        self.update_size()
        self.is_on = True

        if self.settings.update_tmux_title:
            sys.stdout.write("\033kranger\033\\")
            sys.stdout.flush()

    def suspend(self):
        """Turn off curses"""
        self.win.keypad(0)
        curses.nocbreak()
        curses.echo()
        try:
            curses.curs_set(1)
        except:
            pass
        if self.settings.mouse_enabled:
            _setup_mouse(dict(value=False))
        curses.endwin()
        self.is_on = False

    def set_load_mode(self, boolean):
        boolean = bool(boolean)
        if boolean != self.load_mode:
            self.load_mode = boolean

            if boolean:
                # don't wait for key presses in the load mode
                curses.cbreak()
                self.win.nodelay(1)
            else:
                self.win.nodelay(0)
                curses.halfdelay(20)

    def destroy(self):
        """Destroy all widgets and turn off curses"""
        DisplayableContainer.destroy(self)
        self.suspend()

    def handle_mouse(self):
        """Handles mouse input"""
        try:
            event = MouseEvent(curses.getmouse())
        except _curses.error:
            return
        if not self.console.visible:
            DisplayableContainer.click(self, event)

    def handle_key(self, key):
        """Handles key input"""

        if hasattr(self, 'hint'):
            self.hint()

        if key < 0:
            self.keybuffer.clear()

        elif not DisplayableContainer.press(self, key):
            self.keymaps.use_keymap('browser')
            self.press(key)

    def press(self, key):
        keybuffer = self.keybuffer
        self.status.clear_message()

        keybuffer.add(key)
        self.fm.hide_bookmarks()
        self.browser.draw_hints = not keybuffer.finished_parsing \
                and keybuffer.finished_parsing_quantifier

        if keybuffer.result is not None:
            try:
                self.fm.execute_console(keybuffer.result,
                        wildcards=keybuffer.wildcards,
                        quantifier=keybuffer.quantifier)
            finally:
                if keybuffer.finished_parsing:
                    keybuffer.clear()
        elif keybuffer.finished_parsing:
            keybuffer.clear()
            return False
        return True

    def handle_keys(self, *keys):
        for key in keys:
            self.handle_key(key)

    def handle_input(self):
        key = self.win.getch()
        if key is 27 or key >= 128 and key < 256:
            # Handle special keys like ALT+X or unicode here:
            keys = [key]
            previous_load_mode = self.load_mode
            self.set_load_mode(True)
            for n in range(4):
                getkey = self.win.getch()
                if getkey is not -1:
                    keys.append(getkey)
            if len(keys) == 1:
                keys.append(-1)
            elif keys[0] == 27:
                keys[0] = ALT_KEY
            if self.settings.xterm_alt_key:
                if len(keys) == 2 and keys[1] in range(127, 256):
                    if keys[0] == 195:
                        keys = [ALT_KEY, keys[1] - 64]
                    elif keys[0] == 194:
                        keys = [ALT_KEY, keys[1] - 128]
            self.handle_keys(*keys)
            self.set_load_mode(previous_load_mode)
            if self.settings.flushinput and not self.console.visible:
                curses.flushinp()
        else:
            # Handle simple key presses, CTRL+X, etc here:
            if key > 0:
                if self.settings.flushinput and not self.console.visible:
                    curses.flushinp()
                if key == curses.KEY_MOUSE:
                    self.handle_mouse()
                elif key == curses.KEY_RESIZE:
                    self.update_size()
                else:
                    if not self.fm.input_is_blocked():
                        self.handle_key(key)

    def setup(self):
        """Build up the UI by initializing widgets."""
        from ranger.gui.widgets.browserview import BrowserView
        from ranger.gui.widgets.titlebar import TitleBar
        from ranger.gui.widgets.console import Console
        from ranger.gui.widgets.statusbar import StatusBar
        from ranger.gui.widgets.taskview import TaskView
        from ranger.gui.widgets.pager import Pager

        # Create a title bar
        self.titlebar = TitleBar(self.win)
        self.add_child(self.titlebar)

        # Create the browser view
        self.browser = BrowserView(self.win, self.settings.column_ratios)
        self.settings.signal_bind('setopt.column_ratios',
                self.browser.change_ratios)
        self.add_child(self.browser)

        # Create the process manager
        self.taskview = TaskView(self.win)
        self.taskview.visible = False
        self.add_child(self.taskview)

        # Create the status bar
        self.status = StatusBar(self.win, self.browser.main_column)
        self.add_child(self.status)

        # Create the console
        self.console = Console(self.win)
        self.add_child(self.console)
        self.console.visible = False

        # Create the pager
        self.pager = Pager(self.win)
        self.pager.visible = False
        self.add_child(self.pager)

    def redraw(self):
        """Redraw all widgets"""
        self.poke()

        # determine which widgets are shown
        if self.console.wait_for_command_input or self.console.question_queue:
            self.console.focused = True
            self.console.visible = True
            self.status.visible = False
        else:
            self.console.focused = False
            self.console.visible = False
            self.status.visible = True

        self.draw()
        self.finalize()

    def redraw_window(self):
        """Redraw the window. This only calls self.win.redrawwin()."""
        self.win.erase()
        self.win.redrawwin()
        self.win.refresh()
        self.win.redrawwin()
        self.need_redraw = True

    def update_size(self):
        """resize all widgets"""
        self.termsize = self.win.getmaxyx()
        y, x = self.termsize

        self.browser.resize(self.settings.status_bar_on_top and 2 or 1, 0, y - 2, x)
        self.taskview.resize(1, 0, y - 2, x)
        self.pager.resize(1, 0, y - 2, x)
        self.titlebar.resize(0, 0, 1, x)
        self.status.resize(self.settings.status_bar_on_top and 1 or y-1, 0, 1, x)
        self.console.resize(y - 1, 0, 1, x)

    def draw(self):
        """Draw all objects in the container"""
        self.win.touchwin()
        DisplayableContainer.draw(self)
        if self._draw_title and self.settings.update_title:
            cwd = self.fm.thisdir.path
            if cwd.startswith(self.fm.home_path):
                cwd = '~' + cwd[len(self.fm.home_path):]
            if self.settings.shorten_title:
                split = cwd.rsplit(os.sep, self.settings.shorten_title)
                if os.sep in split[0]:
                    cwd = os.sep.join(split[1:])
            try:
                fixed_cwd = cwd.encode('utf-8', 'surrogateescape'). \
                        decode('utf-8', 'replace')
                sys.stdout.write("%sranger:%s%s" %
                        (curses.tigetstr('tsl').decode('latin-1'), fixed_cwd,
                         curses.tigetstr('fsl').decode('latin-1')))
                sys.stdout.flush()
            except:
                pass

        self.win.refresh()

    def finalize(self):
        """Finalize every object in container and refresh the window"""
        DisplayableContainer.finalize(self)
        self.win.refresh()

    def draw_images(self):
        if self.pager.visible:
            self.pager.draw_image()
        elif self.browser.pager.visible:
            self.browser.pager.draw_image()
        else:
            self.browser.columns[-1].draw_image()

    def close_pager(self):
        if self.console.visible:
            self.console.focused = True
        self.pager.close()
        self.pager.visible = False
        self.pager.focused = False
        self.browser.visible = True

    def open_pager(self):
        self.browser.columns[-1].clear_image(force=True)
        if self.console.focused:
            self.console.focused = False
        self.pager.open()
        self.pager.visible = True
        self.pager.focused = True
        self.browser.visible = False
        return self.pager

    def open_embedded_pager(self):
        self.browser.open_pager()
        for column in self.browser.columns:
            if column == self.browser.main_column:
                break
            column.level_shift(amount=1)
        return self.browser.pager

    def close_embedded_pager(self):
        self.browser.close_pager()
        for column in self.browser.columns:
            column.level_restore()

    def open_console(self, string='', prompt=None, position=None):
        if self.console.open(string, prompt=prompt, position=position):
            self.status.msg = None

    def close_console(self):
        self.console.close()
        self.close_pager()

    def open_taskview(self):
        self.browser.columns[-1].clear_image(force=True)
        self.pager.close()
        self.pager.visible = False
        self.pager.focused = False
        self.console.visible = False
        self.browser.visible = False
        self.taskview.visible = True
        self.taskview.focused = True

    def redraw_main_column(self):
        self.browser.main_column.need_redraw = True

    def close_taskview(self):
        self.taskview.visible = False
        self.browser.visible = True
        self.taskview.focused = False

    def throbber(self, string='.', remove=False):
        if remove:
            self.titlebar.throbber = type(self.titlebar).throbber
        else:
            self.titlebar.throbber = string

    def hint(self, text=None):
        self.status.hint = text

    def get_pager(self):
        if self.browser.pager.visible:
            return self.browser.pager
        else:
            return self.pager

########NEW FILE########
__FILENAME__ = browsercolumn
# -*- coding: utf-8 -*-
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""The BrowserColumn widget displays the contents of a directory or file."""

import curses
import stat
from time import time

from . import Widget
from .pager import Pager
from ranger.ext.widestring import WideString

from ranger.gui.color import *

class BrowserColumn(Pager):
    main_column = False
    display_infostring = False
    display_vcsstate   = True
    scroll_begin = 0
    target = None
    last_redraw_time = -1
    ellipsis = { False: '~', True: '…' }

    old_dir = None
    old_thisfile = None

    def __init__(self, win, level):
        """Initializes a Browser Column Widget

        win = the curses window object of the BrowserView
        level = what to display?

        level >0 => previews
        level 0 => current file/directory
        level <0 => parent directories
        """
        Pager.__init__(self, win)
        Widget.__init__(self, win)
        self.level = level
        self.original_level = level

        self.settings.signal_bind('setopt.display_size_in_main_column',
                self.request_redraw, weak=True)

    def request_redraw(self):
        self.need_redraw = True

    def resize(self, y, x, hei, wid):
        Widget.resize(self, y, x, hei, wid)

    def click(self, event):
        """Handle a MouseEvent"""
        direction = event.mouse_wheel_direction()
        if not (event.pressed(1) or event.pressed(3) or direction):
            return False

        if self.target is None:
            pass

        elif self.target.is_directory:
            if self.target.accessible and self.target.content_loaded:
                index = self.scroll_begin + event.y - self.y

                if direction:
                    if self.level == -1:
                        self.fm.move_parent(direction)
                    else:
                        return False
                elif event.pressed(1):
                    if not self.main_column:
                        self.fm.enter_dir(self.target.path)

                    if index < len(self.target):
                        self.fm.move(to=index)
                elif event.pressed(3):
                    try:
                        clicked_file = self.target.files[index]
                        if clicked_file.is_directory:
                            self.fm.enter_dir(clicked_file.path)
                        elif self.level == 0:
                            self.fm.thisdir.move_to_obj(clicked_file)
                            self.fm.execute_file(clicked_file)
                    except:
                        pass

        else:
            if self.level > 0 and not direction:
                self.fm.move(right=0)

        return True

    def execute_curses_batch(self, line, commands):
        """Executes a list of "commands" which can be easily cached.

        "commands" is a list of lists.    Each element contains
        a text and an attribute.  First, the attribute will be
        set with attrset, then the text is printed.

        Example:
        execute_curses_batch(0, [["hello ", 0], ["world", curses.A_BOLD]])
        """
        try:
            self.win.move(line, 0)
        except:
            return
        for entry in commands:
            text, attr = entry
            self.addstr(text, attr)

    def has_preview(self):
        if self.target is None:
            return False

        if self.target.is_file:
            if not self.target.has_preview():
                return False

        if self.target.is_directory:
            if self.level > 0 and not self.settings.preview_directories:
                return False

        return True

    def level_shift(self, amount):
        self.level = self.original_level + amount

    def level_restore(self):
        self.level = self.original_level

    def poke(self):
        Widget.poke(self)
        self.target = self.fm.thistab.at_level(self.level)

    def draw(self):
        """Call either _draw_file() or _draw_directory()"""
        if self.target != self.old_dir:
            self.need_redraw = True
            self.old_dir = self.target

        if self.target:     # don't garbage collect this directory please
            self.target.use()

        if self.target and self.target.is_directory \
                and (self.level <= 0 or self.settings.preview_directories):
            if self.target.pointed_obj != self.old_thisfile:
                self.need_redraw = True
                self.old_thisfile = self.target.pointed_obj

            if self.target.load_content_if_outdated() \
            or self.target.sort_if_outdated() \
            or self.last_redraw_time < self.target.last_update_time:
                self.need_redraw = True

        if self.need_redraw:
            self.win.erase()
            if self.target is None:
                pass
            elif self.target.is_file:
                Pager.open(self)
                self._draw_file()
            elif self.target.is_directory:
                self._draw_directory()
                Widget.draw(self)
            self.need_redraw = False
            self.last_redraw_time = time()

    def _draw_file(self):
        """Draw a preview of the file, if the settings allow it"""
        self.win.move(0, 0)
        if not self.target.accessible:
            self.addnstr("not accessible", self.wid)
            Pager.close(self)
            return

        if self.target is None or not self.target.has_preview():
            Pager.close(self)
            return

        if self.fm.settings.preview_images and self.target.image:
            self.set_image(self.target.realpath)
            Pager.draw(self)
        else:
            f = self.target.get_preview_source(self.wid, self.hei)
            if f is None:
                Pager.close(self)
            else:
                if self.target.is_image_preview():
                    self.set_image(f)
                else:
                    self.set_source(f)
                Pager.draw(self)

    def _draw_directory(self):
        """Draw the contents of a directory"""
        if self.image:
            self.image = None
            self.need_clear_image = True
            Pager.clear_image(self)

        if self.level > 0 and not self.settings.preview_directories:
            return

        base_color = ['in_browser']

        self.win.move(0, 0)

        if not self.target.content_loaded:
            self.color(tuple(base_color))
            self.addnstr("...", self.wid)
            self.color_reset()
            return

        if self.main_column:
            base_color.append('main_column')

        if not self.target.accessible:
            self.color(tuple(base_color + ['error']))
            self.addnstr("not accessible", self.wid)
            self.color_reset()
            return

        if self.target.empty():
            self.color(tuple(base_color + ['empty']))
            self.addnstr("empty", self.wid)
            self.color_reset()
            return

        self._set_scroll_begin()

        copied = [f.path for f in self.fm.copy_buffer]

        selected_i = self.target.pointer
        for line in range(self.hei):
            i = line + self.scroll_begin
            if line > self.hei:
                break

            try:
                drawn = self.target.files[i]
            except IndexError:
                break

            tagged = self.fm.tags and drawn.realpath in self.fm.tags
            if tagged:
                tagged_marker = self.fm.tags.marker(drawn.realpath)
            else:
                tagged_marker = " "

            key = (self.wid, selected_i == i, drawn.marked, self.main_column,
                    drawn.path in copied, tagged_marker, drawn.infostring,
                    drawn.vcsfilestatus, drawn.vcsremotestatus, self.fm.do_cut)

            if key in drawn.display_data:
                self.execute_curses_batch(line, drawn.display_data[key])
                self.color_reset()
                continue

            text = drawn.basename
            if drawn.marked and (self.main_column or \
                    self.settings.display_tags_in_all_columns):
                text = " " + text

            # Computing predisplay data. predisplay contains a list of lists
            # [string, colorlst] where string is a piece of string to display,
            # and colorlst a list of contexts that we later pass to the
            # colorscheme, to compute the curses attribute.
            predisplay_left = []
            predisplay_right = []
            space = self.wid

            # selection mark
            tagmark = self._draw_tagged_display(tagged, tagged_marker)
            tagmarklen = self._total_len(tagmark)
            if space - tagmarklen > 2:
                predisplay_left += tagmark
                space -= tagmarklen

            # vcs data
            vcsstring = self._draw_vcsstring_display(drawn)
            vcsstringlen = self._total_len(vcsstring)
            if space - vcsstringlen > 2:
                predisplay_right += vcsstring
                space -= vcsstringlen

            # info string
            infostring = self._draw_infostring_display(drawn, space)
            infostringlen = self._total_len(infostring)
            if space - infostringlen > 2:
                predisplay_right = infostring + predisplay_right
                space -= infostringlen

            textstring = self._draw_text_display(text, space)
            textstringlen = self._total_len(textstring)
            predisplay_left += textstring
            space -= textstringlen

            if space > 0:
                predisplay_left.append([' ' * space, []])
            elif space < 0:
                raise Exception("Error: there is not enough space to write "
                        "the text. I have computed spaces wrong.")

            # Computing display data. Now we compute the display_data list
            # ready to display in curses. It is a list of lists [string, attr]

            this_color = base_color + list(drawn.mimetype_tuple) + \
                    self._draw_directory_color(i, drawn, copied)
            display_data = []
            drawn.display_data[key] = display_data

            predisplay = predisplay_left + predisplay_right
            for txt, color in predisplay:
                attr = self.settings.colorscheme.get_attr(*(this_color + color))
                display_data.append([txt, attr])

            self.execute_curses_batch(line, display_data)
            self.color_reset()

    def _total_len(self, predisplay):
        return sum([len(WideString(s)) for s, L in predisplay])

    def _draw_text_display(self, text, space):
        wtext = WideString(text)
        wellip = WideString(self.ellipsis[self.settings.unicode_ellipsis])
        if len(wtext) > space:
            wtext = wtext[:max(0, space - len(wellip))] + wellip

        return [[str(wtext), []]]

    def _draw_tagged_display(self, tagged, tagged_marker):
        tagged_display = []
        if (self.main_column or self.settings.display_tags_in_all_columns) \
                and self.wid > 2:
            if tagged:
                tagged_display.append([tagged_marker, ['tag_marker']])
            else:
                tagged_display.append([" ", ['tag_marker']])
        return tagged_display

    def _draw_infostring_display(self, drawn, space):
        infostring_display = []
        if self.display_infostring and drawn.infostring \
                and self.settings.display_size_in_main_column:
            infostring = str(drawn.infostring) + " "
            if len(infostring) <= space:
                infostring_display.append([infostring, ['infostring']])
        return infostring_display

    def _draw_vcsstring_display(self, drawn):
        vcsstring_display = []
        if self.settings.vcs_aware and (drawn.vcsfilestatus or \
                drawn.vcsremotestatus):
            if drawn.vcsfilestatus:
                vcsstr, vcscol = self.vcsfilestatus_symb[drawn.vcsfilestatus]
            else:
                vcsstr = " "
                vcscol = []
            vcsstring_display.append([vcsstr, ['vcsfile'] + vcscol])

            if drawn.vcsremotestatus:
                vcsstr, vcscol = self.vcsremotestatus_symb[
                        drawn.vcsremotestatus]
            else:

                vcsstr = " "
                vcscol = []
            vcsstring_display.append([vcsstr, ['vcsremote'] + vcscol])
        elif self.target.has_vcschild:
            vcsstring_display.append(["  ", []])
        return vcsstring_display

    def _draw_directory_color(self, i, drawn, copied):
        this_color = []
        if i == self.target.pointer:
            this_color.append('selected')

        if drawn.marked:
            this_color.append('marked')

        if self.fm.tags and drawn.realpath in self.fm.tags:
            this_color.append('tagged')

        if drawn.is_directory:
            this_color.append('directory')
        else:
            this_color.append('file')

        if drawn.stat:
            mode = drawn.stat.st_mode
            if mode & stat.S_IXUSR:
                this_color.append('executable')
            if stat.S_ISFIFO(mode):
                this_color.append('fifo')
            if stat.S_ISSOCK(mode):
                this_color.append('socket')
            if drawn.is_device:
                this_color.append('device')

        if drawn.path in copied:
            this_color.append('cut' if self.fm.do_cut else 'copied')

        if drawn.is_link:
            this_color.append('link')
            this_color.append(drawn.exists and 'good' or 'bad')

        return this_color

    def _get_scroll_begin(self):
        """Determines scroll_begin (the position of the first displayed file)"""
        offset = self.settings.scroll_offset
        dirsize = len(self.target)
        winsize = self.hei
        halfwinsize = winsize // 2
        index = self.target.pointer or 0
        original = self.target.scroll_begin
        projected = index - original

        upper_limit = winsize - 1 - offset
        lower_limit = offset

        if original < 0:
            return 0

        if dirsize < winsize:
            return 0

        if halfwinsize < offset:
            return min( dirsize - winsize, max( 0, index - halfwinsize ))

        if original > dirsize - winsize:
            self.target.scroll_begin = dirsize - winsize
            return self._get_scroll_begin()

        if projected < upper_limit and projected > lower_limit:
            return original

        if projected > upper_limit:
            return min( dirsize - winsize,
                    original + (projected - upper_limit))

        if projected < upper_limit:
            return max( 0,
                    original - (lower_limit - projected))

        return original

    def _set_scroll_begin(self):
        """Updates the scroll_begin value"""
        self.scroll_begin = self._get_scroll_begin()
        self.target.scroll_begin = self.scroll_begin

    def scroll(self, n):
        """scroll down by n lines"""
        self.need_redraw = True
        self.target.move(down=n)
        self.target.scroll_begin += 3 * n

    def __str__(self):
        return self.__class__.__name__ + ' at level ' + str(self.level)

########NEW FILE########
__FILENAME__ = browserview
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""The BrowserView manages a set of BrowserColumns."""

import curses, _curses
from ranger.ext.signals import Signal
from ranger.ext.keybinding_parser import key_to_string
from . import Widget
from .browsercolumn import BrowserColumn
from .pager import Pager
from ..displayable import DisplayableContainer

class BrowserView(Widget, DisplayableContainer):
    ratios = None
    preview = True
    is_collapsed = False
    draw_bookmarks = False
    stretch_ratios = None
    need_clear = False
    old_collapse = False
    draw_hints = False
    draw_info = False

    def __init__(self, win, ratios, preview = True):
        DisplayableContainer.__init__(self, win)
        self.preview = preview
        self.columns = []

        self.pager = Pager(self.win, embedded=True)
        self.pager.visible = False
        self.add_child(self.pager)

        self.change_ratios(ratios)

        for option in ('preview_directories', 'preview_files'):
            self.settings.signal_bind('setopt.' + option,
                    self._request_clear_if_has_borders, weak=True)

        self.fm.signal_bind('move', self.request_clear)
        self.settings.signal_bind('setopt.column_ratios', self.request_clear)

        self.old_draw_borders = self.settings.draw_borders

    def change_ratios(self, ratios):
        if isinstance(ratios, Signal):
            ratios = ratios.value

        for column in self.columns:
            column.destroy()
            self.remove_child(column)
        self.columns = []

        ratio_sum = float(sum(ratios))
        self.ratios = tuple(x / ratio_sum for x in ratios)

        last = 0.1 if self.settings.padding_right else 0
        if len(self.ratios) >= 2:
            self.stretch_ratios = self.ratios[:-2] + \
                    ((self.ratios[-2] + self.ratios[-1] * 1.0 - last),
                    (self.ratios[-1] * last))

        offset = 1 - len(ratios)
        if self.preview: offset += 1

        for level in range(len(ratios)):
            fl = BrowserColumn(self.win, level + offset)
            self.add_child(fl)
            self.columns.append(fl)

        try:
            self.main_column = self.columns[self.preview and -2 or -1]
        except IndexError:
            self.main_column = None
        else:
            self.main_column.display_infostring = True
            self.main_column.main_column = True

        self.resize(self.y, self.x, self.hei, self.wid)

    def _request_clear_if_has_borders(self):
        if self.settings.draw_borders:
            self.request_clear()

    def request_clear(self):
        self.need_clear = True

    def draw(self):
        if self.need_clear:
            self.win.erase()
            self.need_redraw = True
            self.need_clear = False
        for tab in self.fm.tabs.values():
            directory = tab.thisdir
            if directory:
                directory.load_content_if_outdated()
                directory.use()
        DisplayableContainer.draw(self)
        if self.settings.draw_borders:
            self._draw_borders()
        if self.draw_bookmarks:
            self._draw_bookmarks()
        elif self.draw_hints:
            self._draw_hints()
        elif self.draw_info:
            self._draw_info(self.draw_info)

    def finalize(self):
        if self.pager.visible:
            try:
                self.fm.ui.win.move(self.main_column.y, self.main_column.x)
            except:
                pass
        else:
            try:
                x = self.main_column.x
                y = self.main_column.y + self.main_column.target.pointer\
                        - self.main_column.scroll_begin
                self.fm.ui.win.move(y, x)
            except:
                pass

    def _draw_borders(self):
        win = self.win
        self.color('in_browser', 'border')

        left_start = 0
        right_end = self.wid - 1

        for child in self.columns:
            if not child.has_preview():
                left_start = child.x + child.wid
            else:
                break

        # Shift the rightmost vertical line to the left to create a padding,
        # but only when padding_right is on, the preview column is collapsed
        # and we did not open the pager to "zoom" in to the file.
        if self.settings.padding_right and not self.pager.visible and \
                self.is_collapsed:
            right_end = self.columns[-1].x - 1
            if right_end < left_start:
                right_end = self.wid - 1

        # Draw horizontal lines and the leftmost vertical line
        try:
            win.hline(0, left_start, curses.ACS_HLINE, right_end - left_start)
            win.hline(self.hei - 1, left_start, curses.ACS_HLINE,
                    right_end - left_start)
            win.vline(1, left_start, curses.ACS_VLINE, self.hei - 2)
        except _curses.error:
            pass

        # Draw the vertical lines in the middle
        for child in self.columns[:-1]:
            if not child.has_preview():
                continue
            if child.main_column and self.pager.visible:
                # If we "zoom in" with the pager, we have to
                # skip the between main_column and pager.
                break
            x = child.x + child.wid
            y = self.hei - 1
            try:
                win.vline(1, x, curses.ACS_VLINE, y - 1)
                self.addch(0, x, curses.ACS_TTEE, 0)
                self.addch(y, x, curses.ACS_BTEE, 0)
            except:
                # in case it's off the boundaries
                pass

        # Draw the last vertical line
        try:
            win.vline(1, right_end, curses.ACS_VLINE, self.hei - 2)
        except _curses.error:
            pass

        self.addch(0, left_start, curses.ACS_ULCORNER)
        self.addch(self.hei - 1, left_start, curses.ACS_LLCORNER)
        self.addch(0, right_end, curses.ACS_URCORNER)
        self.addch(self.hei - 1, right_end, curses.ACS_LRCORNER)

    def _draw_bookmarks(self):
        self.columns[-1].clear_image(force=True)
        self.fm.bookmarks.update_if_outdated()
        self.color_reset()
        self.need_clear = True

        sorted_bookmarks = sorted((item for item in self.fm.bookmarks \
            if self.fm.settings.show_hidden_bookmarks or \
            '/.' not in item[1].path), key=lambda t: t[0].lower())

        hei = min(self.hei - 1, len(sorted_bookmarks))
        ystart = self.hei - hei

        maxlen = self.wid
        self.addnstr(ystart - 1, 0, "mark  path".ljust(self.wid), self.wid)

        whitespace = " " * maxlen
        for line, items in zip(range(self.hei-1), sorted_bookmarks):
            key, mark = items
            string = " " + key + "   " + mark.path
            self.addstr(ystart + line, 0, whitespace)
            self.addnstr(ystart + line, 0, string, self.wid)

        self.win.chgat(ystart - 1, 0, curses.A_UNDERLINE)

    def _draw_info(self, lines):
        self.columns[-1].clear_image(force=True)
        self.need_clear = True
        hei = min(self.hei - 1, len(lines))
        ystart = self.hei - hei
        i = ystart
        whitespace = " " * self.wid
        for line in lines:
            if i >= self.hei:
                break
            self.addstr(i, 0, whitespace)
            self.addnstr(i, 0, line, self.wid)
            i += 1

    def _draw_hints(self):
        self.columns[-1].clear_image(force=True)
        self.need_clear = True
        hints = []
        for k, v in self.fm.ui.keybuffer.pointer.items():
            k = key_to_string(k)
            if isinstance(v, dict):
                text = '...'
            else:
                text = v
            if text.startswith('hint') or text.startswith('chain hint'):
                continue
            hints.append((k, text))
        hints.sort(key=lambda t: t[1])

        hei = min(self.hei - 1, len(hints))
        ystart = self.hei - hei
        self.addnstr(ystart - 1, 0, "key          command".ljust(self.wid),
                self.wid)
        try:
            self.win.chgat(ystart - 1, 0, curses.A_UNDERLINE)
        except:
            pass
        whitespace = " " * self.wid
        i = ystart
        for key, cmd in hints:
            string = " " + key.ljust(11) + " " + cmd
            self.addstr(i, 0, whitespace)
            self.addnstr(i, 0, string, self.wid)
            i += 1

    def _collapse(self):
        # Should the last column be cut off? (Because there is no preview)
        if not self.settings.collapse_preview or not self.preview \
                or not self.stretch_ratios:
            return False
        result = not self.columns[-1].has_preview()
        target = self.columns[-1].target
        if not result and target and target.is_file:
            if target.image and self.fm.settings.preview_images:
                result = False  # don't collapse when drawing images
            elif self.fm.settings.preview_script and \
                    self.fm.settings.use_preview_script:
                try:
                    result = not self.fm.previews[target.realpath]['foundpreview']
                except:
                    return self.old_collapse

        self.old_collapse = result
        return result

    def resize(self, y, x, hei, wid):
        """Resize all the columns according to the given ratio"""
        DisplayableContainer.resize(self, y, x, hei, wid)
        borders = self.settings.draw_borders
        pad = 1 if borders else 0
        left = pad

        self.is_collapsed = self._collapse()
        if self.is_collapsed:
            generator = enumerate(self.stretch_ratios)
        else:
            generator = enumerate(self.ratios)

        last_i = len(self.ratios) - 1

        for i, ratio in generator:
            wid = int(ratio * self.wid)

            cut_off = self.is_collapsed and not self.settings.padding_right
            if i == last_i:
                if not cut_off:
                    wid = int(self.wid - left + 1 - pad)
                else:
                    self.columns[i].resize(pad, left - 1, hei - pad * 2, 1)
                    self.columns[i].visible = False
                    continue

            if i == last_i - 1:
                self.pager.resize(pad, left, hei - pad * 2, \
                        max(1, self.wid - left - pad))

                if cut_off:
                    self.columns[i].resize(pad, left, hei - pad * 2, \
                            max(1, self.wid - left - pad))
                    continue

            try:
                self.columns[i].resize(pad, left, hei - pad * 2, \
                        max(1, wid - 1))
            except KeyError:
                pass

            left += wid

    def click(self, event):
        if DisplayableContainer.click(self, event):
            return True
        direction = event.mouse_wheel_direction()
        if direction:
            self.main_column.scroll(direction)
        return False

    def open_pager(self):
        self.pager.visible = True
        self.pager.focused = True
        self.need_clear = True
        self.pager.open()
        try:
            self.columns[-1].visible = False
            self.columns[-2].visible = False
        except IndexError:
            pass

    def close_pager(self):
        self.pager.visible = False
        self.pager.focused = False
        self.need_clear = True
        self.pager.close()
        try:
            self.columns[-1].visible = True
            self.columns[-2].visible = True
        except IndexError:
            pass

    def poke(self):
        DisplayableContainer.poke(self)

        # Show the preview column when it has a preview but has
        # been hidden (e.g. because of padding_right = False)
        if not self.pager.visible and not self.columns[-1].visible and \
        self.columns[-1].target and self.columns[-1].target.is_directory \
        or self.columns[-1].has_preview() and not self.pager.visible:
            self.columns[-1].visible = True

        if self.preview and self.is_collapsed != self._collapse():
            if (self.fm.settings.preview_images and
                self.fm.settings.preview_files):
                # force clearing the image when resizing preview column
                self.columns[-1].clear_image(force=True)
            self.resize(self.y, self.x, self.hei, self.wid)

        if self.old_draw_borders != self.settings.draw_borders:
            self.resize(self.y, self.x, self.hei, self.wid)
            self.old_draw_borders = self.settings.draw_borders

########NEW FILE########
__FILENAME__ = console
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""The Console widget implements a vim-like console"""

import curses
import re
from collections import deque

from . import Widget
from ranger.ext.direction import Direction
from ranger.ext.widestring import uwid, WideString
from ranger.container.history import History, HistoryEmptyException
import ranger

class Console(Widget):
    visible = False
    last_cursor_mode = None
    history_search_pattern = None
    prompt = ':'
    copy = ''
    tab_deque = None
    original_line = None
    history = None
    history_backup = None
    override = None
    allow_close = False
    historypath = None
    wait_for_command_input = False
    unicode_buffer = ""

    def __init__(self, win):
        Widget.__init__(self, win)
        self.clear()
        self.history = History(self.settings.max_console_history_size)
        # load history from files
        if not ranger.arg.clean:
            self.historypath = self.fm.confpath('history')
            try:
                f = open(self.historypath, 'r')
            except:
                pass
            else:
                for line in f:
                    self.history.add(line[:-1])
                f.close()
        self.line = ""
        self.history_backup = History(self.history)

        # NOTE: the console is considered in the "question mode" when the
        # question_queue is non-empty.  In that case, the console will draw the
        # question instead of the regular console, and the input you give is
        # used to answer the question instead of typing in commands.
        #
        # A question is a tuple of (question_string, callback_func,
        # tuple_of_choices).  callback_func is a function that is called when
        # the question is answered which gets the answer as an argument.
        # tuple_of_choices looks like ('y', 'n').  Only one-letter-answers are
        # currently supported.  Pressing enter uses the first choice whereas
        # pressing ESC uses the second choice.
        self.question_queue = []

    def destroy(self):
        # save history to files
        if ranger.arg.clean or not self.settings.save_console_history:
            return
        if self.historypath:
            try:
                f = open(self.historypath, 'w')
            except:
                pass
            else:
                for entry in self.history_backup:
                    try:
                        f.write(entry + '\n')
                    except UnicodeEncodeError:
                        pass
                f.close()

    def draw(self):
        self.win.erase()
        if self.question_queue:
            assert isinstance(self.question_queue[0], tuple)
            assert len(self.question_queue[0]) == 3
            self.addstr(0, 0, self.question_queue[0][0])
            return

        self.addstr(0, 0, self.prompt)
        line = WideString(self.line)
        overflow = -self.wid + len(self.prompt) + len(line) + 1
        if overflow > 0:
            self.addstr(0, len(self.prompt), str(line[overflow:]))
        else:
            self.addstr(0, len(self.prompt), self.line)

    def finalize(self):
        move = self.fm.ui.win.move
        if self.question_queue:
            try:
                move(self.y, len(self.question_queue[0][0]))
            except:
                pass
        else:
            try:
                pos = uwid(self.line[0:self.pos]) + len(self.prompt)
                move(self.y, self.x + min(self.wid-1, pos))
            except:
                pass

    def open(self, string='', prompt=None, position=None):
        if prompt is not None:
            assert isinstance(prompt, str)
            self.prompt = prompt
        elif 'prompt' in self.__dict__:
            del self.prompt

        if self.last_cursor_mode is None:
            try:
                self.last_cursor_mode = curses.curs_set(1)
            except:
                pass
        self.allow_close = False
        self.tab_deque = None
        self.unicode_buffer = ""
        self.line = string
        self.history_search_pattern = self.line
        self.pos = len(string)
        if position is not None:
            self.pos = min(self.pos, position)
        self.history_backup.fast_forward()
        self.history = History(self.history_backup)
        self.history.add('')
        self.wait_for_command_input = True
        return True

    def close(self, trigger_cancel_function=True):
        if self.question_queue:
            question = self.question_queue[0]
            answers = question[2]
            if len(answers) >= 2:
                self._answer_question(answers[1])
        else:
            self._close_command_prompt(trigger_cancel_function)

    def _close_command_prompt(self, trigger_cancel_function=True):
        if trigger_cancel_function:
            cmd = self._get_cmd(quiet=True)
            if cmd:
                try:
                    cmd.cancel()
                except Exception as error:
                    self.fm.notify(error)
        if self.last_cursor_mode is not None:
            try:
                curses.curs_set(self.last_cursor_mode)
            except:
                pass
            self.last_cursor_mode = None
        self.fm.hide_console_info()
        self.add_to_history()
        self.tab_deque = None
        self.clear()
        self.__class__ = Console
        self.wait_for_command_input = False

    def clear(self):
        self.pos = 0
        self.line = ''

    def press(self, key):
        self.fm.ui.keymaps.use_keymap('console')
        if not self.fm.ui.press(key):
            self.type_key(key)

    def _answer_question(self, answer):
        if not self.question_queue:
            return False
        question = self.question_queue[0]
        text, callback, answers = question
        if answer in answers:
            self.question_queue.pop(0)
            callback(answer)
            return True
        return False

    def type_key(self, key):
        self.tab_deque = None

        line = "" if self.question_queue else self.line
        result = self._add_character(key, self.unicode_buffer, line, self.pos)
        if result[1] == line:
            # line didn't change, so we don't need to do anything, just update
            # the unicode _buffer.
            self.unicode_buffer = result[0]
            return

        if self.question_queue:
            self.unicode_buffer, answer, self.pos = result
            self._answer_question(answer)
        else:
            self.unicode_buffer, self.line, self.pos = result
            self.on_line_change()

    def _add_character(self, key, unicode_buffer, line, pos):
        # Takes the pressed key, a string "unicode_buffer" containing a
        # potentially incomplete unicode character, the current line and the
        # position of the cursor inside the line.
        # This function returns the new unicode buffer, the modified line and
        # position.
        if isinstance(key, int):
            try:
                key = chr(key)
            except ValueError:
                return unicode_buffer, line, pos

        if self.fm.py3:
            unicode_buffer += key
            try:
                decoded = unicode_buffer.encode("latin-1").decode("utf-8")
            except UnicodeDecodeError:
                return unicode_buffer, line, pos
            except UnicodeEncodeError:
                return unicode_buffer, line, pos
            else:
                unicode_buffer = ""
                if pos == len(line):
                    line += decoded
                else:
                    line = line[:pos] + decoded + line[pos:]
                pos += len(decoded)
        else:
            if pos == len(line):
                line += key
            else:
                line = line[:pos] + key + line[pos:]
            pos += len(key)
        return unicode_buffer, line, pos

    def history_move(self, n):
        try:
            current = self.history.current()
        except HistoryEmptyException:
            pass
        else:
            if self.line != current and self.line != self.history.top():
                self.history.modify(self.line)
            if self.history_search_pattern:
                self.history.search(self.history_search_pattern, n)
            else:
                self.history.move(n)
            current = self.history.current()
            if self.line != current:
                self.line = self.history.current()
                self.pos = len(self.line)

    def add_to_history(self):
        self.history_backup.fast_forward()
        self.history_backup.add(self.line)
        self.history = History(self.history_backup)

    def move(self, **keywords):
        direction = Direction(keywords)
        if direction.horizontal():
            # Ensure that the pointer is moved utf-char-wise
            if self.fm.py3:
                self.pos = direction.move(
                        direction=direction.right(),
                        minimum=0,
                        maximum=len(self.line) + 1,
                        current=self.pos)
            else:
                if self.fm.py3:
                    uc = list(self.line)
                    upos = len(self.line[:self.pos])
                else:
                    uc = list(self.line.decode('utf-8', 'ignore'))
                    upos = len(self.line[:self.pos].decode('utf-8', 'ignore'))
                newupos = direction.move(
                        direction=direction.right(),
                        minimum=0,
                        maximum=len(uc) + 1,
                        current=upos)
                self.pos = len(''.join(uc[:newupos]).encode('utf-8', 'ignore'))

    def delete_rest(self, direction):
        self.tab_deque = None
        if direction > 0:
            self.copy = self.line[self.pos:]
            self.line = self.line[:self.pos]
        else:
            self.copy = self.line[:self.pos]
            self.line = self.line[self.pos:]
            self.pos = 0
        self.on_line_change()

    def paste(self):
        if self.pos == len(self.line):
            self.line += self.copy
        else:
            self.line = self.line[:self.pos] + self.copy + self.line[self.pos:]
        self.pos += len(self.copy)
        self.on_line_change()

    def delete_word(self, backward=True):
        if self.line:
            self.tab_deque = None
            if backward:
                right_part = self.line[self.pos:]
                i = self.pos - 2
                while i >= 0 and re.match(r'[\w\d]', self.line[i], re.U):
                    i -= 1
                self.copy = self.line[i + 1:self.pos]
                self.line = self.line[:i + 1] + right_part
                self.pos = i + 1
            else:
                left_part = self.line[:self.pos]
                i = self.pos + 1
                while i < len(self.line) and re.match(r'[\w\d]', self.line[i], re.U):
                    i += 1
                self.copy = self.line[self.pos:i]
                if i >= len(self.line):
                    self.line = left_part
                    self.pos = len(self.line)
                else:
                    self.line = left_part + self.line[i:]
                    self.pos = len(left_part)
            self.on_line_change()

    def delete(self, mod):
        self.tab_deque = None
        if mod == -1 and self.pos == 0:
            if not self.line:
                self.close(trigger_cancel_function=False)
            return
        # Delete utf-char-wise
        if self.fm.py3:
            left_part = self.line[:self.pos + mod]
            self.pos = len(left_part)
            self.line = left_part + self.line[self.pos + 1:]
        else:
            uc = list(self.line.decode('utf-8', 'ignore'))
            upos = len(self.line[:self.pos].decode('utf-8', 'ignore')) + mod
            left_part = ''.join(uc[:upos]).encode('utf-8', 'ignore')
            self.pos = len(left_part)
            self.line = left_part + ''.join(uc[upos+1:]).encode('utf-8', 'ignore')
        self.on_line_change()

    def execute(self, cmd=None):
        if self.question_queue and cmd is None:
            question = self.question_queue[0]
            answers = question[2]
            if len(answers) >= 1:
                self._answer_question(answers[0])
            else:
                self.question_queue.pop(0)
            return

        self.allow_close = True
        self.fm.execute_console(self.line)
        if self.allow_close:
            self._close_command_prompt(trigger_cancel_function=False)

    def _get_cmd(self, quiet=False):
        try:
            command_class = self._get_cmd_class()
        except KeyError:
            if not quiet:
                error = "Command not found: `%s'" % self.line.split()[0]
                self.fm.notify(error, bad=True)
        except:
            return None
        else:
            return command_class(self.line)

    def _get_cmd_class(self):
        return self.fm.commands.get_command(self.line.split()[0])

    def _get_tab(self):
        if ' ' in self.line:
            cmd = self._get_cmd()
            if cmd:
                return cmd.tab()
            else:
                return None

        return self.fm.commands.command_generator(self.line)

    def tab(self, n=1):
        if self.tab_deque is None:
            tab_result = self._get_tab()

            if isinstance(tab_result, str):
                self.line = tab_result
                self.pos = len(tab_result)
                self.on_line_change()

            elif tab_result == None:
                pass

            elif hasattr(tab_result, '__iter__'):
                self.tab_deque = deque(tab_result)
                self.tab_deque.appendleft(self.line)

        if self.tab_deque is not None:
            self.tab_deque.rotate(-n)
            self.line = self.tab_deque[0]
            self.pos = len(self.line)
            self.on_line_change()

    def on_line_change(self):
        self.history_search_pattern = self.line
        try:
            cls = self._get_cmd_class()
        except (KeyError, ValueError, IndexError):
            pass
        else:
            cmd = cls(self.line)
            if cmd and cmd.quick():
                self.execute(cmd)

    def ask(self, text, callback, choices=['y', 'n']):
        """Open a question prompt with predefined choices

        The "text" is displayed as the question text and should include a list
        of possible keys that the user can type.  The "callback" is a function
        that is called when the question is answered.  It only gets the answer
        as an argument.  "choices" is a tuple of one-letter strings that can be
        typed in by the user.  Every other input gets ignored, except <Enter>
        and <ESC>.

        The first choice is used when the user presses <Enter>, the second
        choice is used when the user presses <ESC>.
        """
        self.question_queue.append((text, callback, choices))

########NEW FILE########
__FILENAME__ = pager
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# Copyright (C) 2010 David Barnett <davidbarnett2@gmail.com>
# This software is distributed under the terms of the GNU GPL version 3.

"""The pager displays text and allows you to scroll inside it."""

from . import Widget
from ranger.core.loader import CommandLoader
from ranger.gui import ansi
from ranger.ext.direction import Direction
from ranger.ext.img_display import ImgDisplayUnsupportedException

# TODO: Scrolling in embedded pager
class Pager(Widget):
    source = None
    source_is_stream = False

    old_source = None
    old_scroll_begin = 0
    old_startx = 0
    need_clear_image = False
    need_redraw_image = False
    max_width = None
    def __init__(self, win, embedded=False):
        Widget.__init__(self, win)
        self.embedded = embedded
        self.scroll_begin = 0
        self.startx = 0
        self.markup = None
        self.lines = []
        self.image = None
        self.image_drawn = False

    def open(self):
        self.scroll_begin = 0
        self.markup = None
        self.max_width = 0
        self.startx = 0
        self.need_redraw = True

    def clear_image(self, force=False):
        if (force or self.need_clear_image) and self.image_drawn:
            self.fm.image_displayer.clear(self.x, self.y, self.wid, self.hei)
            self.need_clear_image = False
            self.image_drawn = False

    def close(self):
        if self.image:
            self.need_clear_image = True
            self.clear_image()
        if self.source and self.source_is_stream:
            self.source.close()

    def destroy(self):
        self.clear_image(force=True)

    def finalize(self):
        self.fm.ui.win.move(self.y, self.x)

    def draw(self):
        if self.need_clear_image:
            self.need_redraw = True

        if self.old_source != self.source:
            self.old_source = self.source
            self.need_redraw = True

        if self.old_scroll_begin != self.scroll_begin or \
                self.old_startx != self.startx:
            self.old_startx = self.startx
            self.old_scroll_begin = self.scroll_begin
            self.need_redraw = True

        if self.need_redraw:
            self.win.erase()
            self.need_redraw_image = True
            self.clear_image()

            if not self.image:
                line_gen = self._generate_lines(
                        starty=self.scroll_begin, startx=self.startx)

                for line, i in zip(line_gen, range(self.hei)):
                    self._draw_line(i, line)

            self.need_redraw = False

    def draw_image(self):
        if self.image and self.need_redraw_image:
            self.source = None
            self.need_redraw_image = False
            try:
                self.fm.image_displayer.draw(self.image, self.x, self.y,
                        self.wid, self.hei)
            except ImgDisplayUnsupportedException:
                self.fm.settings.preview_images = False
            except Exception as e:
                self.fm.notify(e, bad=True)
            else:
                self.image_drawn = True

    def _draw_line(self, i, line):
        if self.markup is None:
            self.addstr(i, 0, line)
        elif self.markup == 'ansi':
            try:
                self.win.move(i, 0)
            except:
                pass
            else:
                for chunk in ansi.text_with_fg_bg_attr(line):
                    if isinstance(chunk, tuple):
                        self.set_fg_bg_attr(*chunk)
                    else:
                        self.addstr(chunk)

    def move(self, narg=None, **kw):
        direction = Direction(kw)
        if direction.horizontal():
            self.startx = direction.move(
                    direction=direction.right(),
                    override=narg,
                    maximum=self.max_width,
                    current=self.startx,
                    pagesize=self.wid,
                    offset=-self.wid + 1)
        if direction.vertical():
            if self.source_is_stream:
                self._get_line(self.scroll_begin + self.hei * 2)
            self.scroll_begin = direction.move(
                    direction=direction.down(),
                    override=narg,
                    maximum=len(self.lines),
                    current=self.scroll_begin,
                    pagesize=self.hei,
                    offset=-self.hei + 1)

    def press(self, key):
        self.fm.ui.keymaps.use_keymap('pager')
        self.fm.ui.press(key)

    def set_image(self, image):
        if self.image:
            self.need_clear_image = True
        self.image = image

        if self.source and self.source_is_stream:
            self.source.close()
        self.source = None
        self.source_is_stream = False

    def set_source(self, source, strip=False):
        if self.image:
            self.image = None
            self.need_clear_image = True

        if self.source and self.source_is_stream:
            self.source.close()

        self.max_width = 0
        if isinstance(source, str):
            self.source_is_stream = False
            self.lines = source.splitlines()
            if self.lines:
                self.max_width = max(len(line) for line in self.lines)
        elif hasattr(source, '__getitem__'):
            self.source_is_stream = False
            self.lines = source
            if self.lines:
                self.max_width = max(len(line) for line in source)
        elif hasattr(source, 'readline'):
            self.source_is_stream = True
            self.lines = []
        else:
            self.source = None
            self.source_is_stream = False
            return False
        self.markup = 'ansi'

        if not self.source_is_stream and strip:
            self.lines = map(lambda x: x.strip(), self.lines)

        self.source = source
        return True

    def click(self, event):
        n = event.ctrl() and 1 or 3
        direction = event.mouse_wheel_direction()
        if direction:
            self.move(down=direction * n)
        return True

    def _get_line(self, n, attempt_to_read=True):
        assert isinstance(n, int), n
        try:
            return self.lines[n]
        except (KeyError, IndexError):
            if attempt_to_read and self.source_is_stream:
                try:
                    for l in self.source:
                        if len(l) > self.max_width:
                            self.max_width = len(l)
                        self.lines.append(l)
                        if len(self.lines) > n:
                            break
                except (UnicodeError, IOError):
                    pass
                return self._get_line(n, attempt_to_read=False)
            return ""

    def _generate_lines(self, starty, startx):
        i = starty
        if not self.source:
            raise StopIteration
        while True:
            try:
                line = self._get_line(i).expandtabs(4)
                if self.markup is 'ansi':
                    line = ansi.char_slice(line, startx, self.wid) + ansi.reset
                else:
                    line = line[startx:self.wid + startx]
                yield line.rstrip()
            except IndexError:
                raise StopIteration
            i += 1

########NEW FILE########
__FILENAME__ = statusbar
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""The statusbar displays information about the current file and directory.

On the left side, there is a display similar to what "ls -l" would
print for the current file.  The right side shows directory information
such as the space used by all the files in this directory.
"""

import os
from pwd import getpwuid
from grp import getgrgid
from os import getuid, readlink
from time import time, strftime, localtime

from ranger.ext.human_readable import human_readable
from . import Widget
from ranger.gui.bar import Bar

class StatusBar(Widget):
    __doc__ = __doc__
    owners = {}
    groups = {}
    timeformat = '%Y-%m-%d %H:%M'
    hint = None
    msg = None

    old_thisfile = None
    old_ctime = None
    old_du = None
    old_hint = None
    result = None

    def __init__(self, win, column=None):
        Widget.__init__(self, win)
        self.column = column
        self.settings.signal_bind('setopt.display_size_in_status_bar',
                self.request_redraw, weak=True)

    def request_redraw(self):
        self.need_redraw = True

    def notify(self, text, duration=0, bad=False):
        self.msg = Message(text, duration, bad)

    def clear_message(self):
        self.msg = None

    def draw(self):
        """Draw the statusbar"""

        if self.hint and isinstance(self.hint, str):
            if self.old_hint != self.hint:
                self.need_redraw = True
            if self.need_redraw:
                self._draw_hint()
            return

        if self.old_hint and not self.hint:
            self.old_hint = None
            self.need_redraw = True

        if self.msg:
            if self.msg.is_alive():
                self._draw_message()
                return
            else:
                self.msg = None
                self.need_redraw = True

        if self.fm.thisfile:
            self.fm.thisfile.load_if_outdated()
            try:
                ctime = self.fm.thisfile.stat.st_ctime
            except:
                ctime = -1
        else:
            ctime = -1

        if not self.result:
            self.need_redraw = True

        if self.old_du and not self.fm.thisdir.disk_usage:
            self.old_du = self.fm.thisdir.disk_usage
            self.need_redraw = True

        if self.old_thisfile != self.fm.thisfile:
            self.old_thisfile = self.fm.thisfile
            self.need_redraw = True

        if self.old_ctime != ctime:
            self.old_ctime = ctime
            self.need_redraw = True

        if self.need_redraw:
            self.need_redraw = False

            self._calc_bar()
            self._print_result(self.result)

    def _calc_bar(self):
        bar = Bar('in_statusbar')
        self._get_left_part(bar)
        self._get_right_part(bar)
        bar.shrink_by_removing(self.wid)

        self.result = bar.combine()

    def _draw_message(self):
        self.win.erase()
        self.color('in_statusbar', 'message',
                self.msg.bad and 'bad' or 'good')
        self.addnstr(0, 0, self.msg.text, self.wid)

    def _draw_hint(self):
        self.win.erase()
        highlight = True
        space_left = self.wid
        starting_point = self.x
        for string in self.hint.split('*'):
            highlight = not highlight
            if highlight:
                self.color('in_statusbar', 'text', 'highlight')
            else:
                self.color('in_statusbar', 'text')

            try:
                self.addnstr(0, starting_point, string, space_left)
            except:
                break
            space_left -= len(string)
            starting_point += len(string)

    def _get_left_part(self, bar):
        left = bar.left

        if self.column is not None and self.column.target is not None\
                and self.column.target.is_directory:
            target = self.column.target.pointed_obj
        else:
            directory = self.fm.thistab.at_level(0)
            if directory:
                target = directory.pointed_obj
            else:
                return
        try:
            stat = target.stat
        except:
            return
        if stat is None:
            return

        if self.fm.mode != 'normal':
            perms = '--%s--' % self.fm.mode.upper()
        else:
            perms = target.get_permission_string()
        how = getuid() == stat.st_uid and 'good' or 'bad'
        left.add(perms, 'permissions', how)
        left.add_space()
        left.add(str(stat.st_nlink), 'nlink')
        left.add_space()
        left.add(self._get_owner(target), 'owner')
        left.add_space()
        left.add(self._get_group(target), 'group')

        if target.is_link:
            how = target.exists and 'good' or 'bad'
            try:
                dest = readlink(target.path)
            except:
                dest = '?'
            left.add(' -> ' + dest, 'link', how)
        else:
            left.add_space()

            if self.settings.display_size_in_status_bar and target.infostring:
                left.add(target.infostring.replace(" ", ""))
                left.add_space()

            left.add(strftime(self.timeformat,
                    localtime(stat.st_mtime)), 'mtime')

        if target.vcs:
            if target.vcsbranch:
                vcsinfo = '(%s: %s)' % (target.vcs.vcsname, target.vcsbranch)
            else:
                vcsinfo = '(%s)' % (target.vcs.vcsname)

            left.add_space()
            left.add(vcsinfo, 'vcsinfo')

            if target.vcsfilestatus:
                left.add_space()
                vcsstr, vcscol = self.vcsfilestatus_symb[target.vcsfilestatus]
                left.add(vcsstr.strip(), 'vcsfile', *vcscol)
            if target.vcsremotestatus:
                vcsstr, vcscol = self.vcsremotestatus_symb[target.vcsremotestatus]
                left.add(vcsstr.strip(), 'vcsremote', *vcscol)
            if target.vcshead:
                left.add_space()
                left.add('%s' % target.vcshead['summary'], 'vcscommit')

    def _get_owner(self, target):
        uid = target.stat.st_uid

        try:
            return self.owners[uid]
        except KeyError:
            try:
                self.owners[uid] = getpwuid(uid)[0]
                return self.owners[uid]
            except KeyError:
                return str(uid)

    def _get_group(self, target):
        gid = target.stat.st_gid

        try:
            return self.groups[gid]
        except KeyError:
            try:
                self.groups[gid] = getgrgid(gid)[0]
                return self.groups[gid]
            except KeyError:
                return str(gid)



    def _get_right_part(self, bar):
        right = bar.right
        if self.column is None:
            return

        target = self.column.target
        if target is None \
                or not target.accessible \
                or (target.is_directory and target.files is None):
            return

        pos = target.scroll_begin
        max_pos = len(target) - self.column.hei
        base = 'scroll'

        if self.fm.thisdir.filter:
            right.add(" f=`", base, 'filter')
            right.add(self.fm.thisdir.filter.pattern, base, 'filter')
            right.add("', ", "space")

        if target.marked_items:
            if len(target.marked_items) == len(target.files):
                right.add(human_readable(target.disk_usage, separator=''))
            else:
                sumsize = sum(f.size for f in target.marked_items if not
                        f.is_directory or f._cumulative_size_calculated)
                right.add(human_readable(sumsize, separator=''))
            right.add("/" + str(len(target.marked_items)))
        else:
            right.add(human_readable(target.disk_usage, separator='') + " sum")
            try:
                free = get_free_space(target.mount_path)
            except OSError:
                pass
            else:
                right.add(", ", "space")
                right.add(human_readable(free, separator='') + " free")
        right.add("  ", "space")

        if target.marked_items:
            # Indicate that there are marked files. Useful if you scroll
            # away and don't see them anymore.
            right.add('Mrk', base, 'marked')
        elif len(target.files):
            right.add(str(target.pointer + 1) + '/'
                    + str(len(target.files)) + '  ', base)
            if max_pos <= 0:
                right.add('All', base, 'all')
            elif pos == 0:
                right.add('Top', base, 'top')
            elif pos >= max_pos:
                right.add('Bot', base, 'bot')
            else:
                right.add('{0:0>.0f}%'.format(100.0 * pos / max_pos),
                        base, 'percentage')
        else:
            right.add('0/0  All', base, 'all')

    def _print_result(self, result):
        self.win.move(0, 0)
        for part in result:
            self.color(*part.lst)
            self.addstr(str(part))

        if self.settings.draw_progress_bar_in_status_bar:
            queue = self.fm.loader.queue
            states = []
            for item in queue:
                if item.progressbar_supported:
                    states.append(item.percent)
            if states:
                state = sum(states) / len(states)
                barwidth = state / 100.0 * self.wid
                self.color_at(0, 0, int(barwidth), ("in_statusbar", "loaded"))
                self.color_reset()

def get_free_space(path):
    stat = os.statvfs(path)
    return stat.f_bavail * stat.f_bsize

class Message(object):
    elapse = None
    text = None
    bad = False

    def __init__(self, text, duration, bad):
        self.text = text
        self.bad = bad
        self.elapse = time() + duration

    def is_alive(self):
        return time() <= self.elapse

########NEW FILE########
__FILENAME__ = taskview
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""The TaskView allows you to modify what the loader is doing."""

from . import Widget
from ranger.ext.accumulator import Accumulator

class TaskView(Widget, Accumulator):
    old_lst = None

    def __init__(self, win):
        Widget.__init__(self, win)
        Accumulator.__init__(self)
        self.scroll_begin = 0

    def draw(self):
        base_clr = []
        base_clr.append('in_taskview')
        lst = self.get_list()

        if self.old_lst != lst:
            self.old_lst = lst
            self.need_redraw = True

        if self.need_redraw:
            self.win.erase()
            if not self.pointer_is_synced():
                self.sync_index()

            if self.hei <= 0:
                return

            self.addstr(0, 0, "Task View")
            self.color_at(0, 0, self.wid, tuple(base_clr), 'title')

            if lst:
                for i in range(self.hei - 1):
                    i += self.scroll_begin
                    try:
                        obj = lst[i]
                    except IndexError:
                        break

                    y = i + 1
                    clr = list(base_clr)

                    if self.pointer == i:
                        clr.append('selected')

                    descr = obj.get_description()
                    if obj.progressbar_supported and obj.percent >= 0 \
                            and obj.percent <= 100:
                        self.addstr(y, 0, "%3.2f%% - %s" % \
                                (obj.percent, descr), self.wid)
                        wid = int(self.wid / 100.0 * obj.percent)
                        self.color_at(y, 0, self.wid, tuple(clr))
                        self.color_at(y, 0, wid, tuple(clr), 'loaded')
                    else:
                        self.addstr(y, 0, descr, self.wid)
                        self.color_at(y, 0, self.wid, tuple(clr))

            else:
                if self.hei > 1:
                    self.addstr(1, 0, "No task in the queue.")
                    self.color_at(1, 0, self.wid, tuple(base_clr), 'error')

            self.color_reset()

    def finalize(self):
        y = self.y + 1 + self.pointer - self.scroll_begin
        self.fm.ui.win.move(y, self.x)


    def task_remove(self, i=None):
        if i is None:
            i = self.pointer

        if self.fm.loader.queue:
            self.fm.loader.remove(index=i)

    def task_move(self, to, i=None):
        if i is None:
            i = self.pointer

        self.fm.loader.move(_from=i, to=to)

    def press(self, key):
        self.fm.ui.keymaps.use_keymap('taskview')
        self.fm.ui.press(key)

    def get_list(self):
        return self.fm.loader.queue

########NEW FILE########
__FILENAME__ = titlebar
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

"""The titlebar is the widget at the top, giving you broad overview.

It displays the current path among other things.
"""

from os.path import basename

from . import Widget
from ranger.gui.bar import Bar

class TitleBar(Widget):
    old_thisfile = None
    old_keybuffer = None
    old_wid = None
    result = None
    throbber = ' '
    need_redraw = False
    tab_width = 0

    def __init__(self, *args, **keywords):
        Widget.__init__(self, *args, **keywords)
        self.fm.signal_bind('tab.change', self.request_redraw, weak=True)

    def request_redraw(self):
        self.need_redraw = True

    def draw(self):
        if self.need_redraw or \
                self.fm.thisfile != self.old_thisfile or\
                str(self.fm.ui.keybuffer) != str(self.old_keybuffer) or\
                self.wid != self.old_wid:
            self.need_redraw = False
            self.old_wid = self.wid
            self.old_thisfile = self.fm.thisfile
            self._calc_bar()
        self._print_result(self.result)
        if self.wid > 2:
            self.color('in_titlebar', 'throbber')
            self.addnstr(self.y, self.wid - 2 - self.tab_width,
                    self.throbber, 1)

    def click(self, event):
        """Handle a MouseEvent"""
        direction = event.mouse_wheel_direction()
        if direction:
            self.fm.tab_move(direction)
            self.need_redraw = True
            return True

        if not event.pressed(1) or not self.result:
            return False

        pos = self.wid - 1
        for tabname in reversed(self.fm._get_tab_list()):
            tabtext = self._get_tab_text(tabname)
            pos -= len(tabtext)
            if event.x > pos:
                self.fm.tab_open(tabname)
                self.need_redraw = True
                return True

        pos = 0
        for i, part in enumerate(self.result):
            pos += len(part)
            if event.x < pos:
                if i < 2:
                    self.fm.enter_dir("~")
                elif i == 2:
                    self.fm.enter_dir("/")
                else:
                    try:
                        self.fm.enter_dir(part.directory)
                    except:
                        pass
                return True
        return False

    def _calc_bar(self):
        bar = Bar('in_titlebar')
        self._get_left_part(bar)
        self._get_right_part(bar)
        try:
            bar.shrink_from_the_left(self.wid)
        except ValueError:
            bar.shrink_by_removing(self.wid)
        self.result = bar.combine()

    def _get_left_part(self, bar):
        # TODO: Properly escape non-printable chars without breaking unicode
        if self.fm.username == 'root':
            clr = 'bad'
        else:
            clr = 'good'

        bar.add(self.fm.username, 'hostname', clr, fixed=True)
        bar.add('@', 'hostname', clr, fixed=True)
        bar.add(self.fm.hostname, 'hostname', clr, fixed=True)
        bar.add(':', 'hostname', clr, fixed=True)

        pathway = self.fm.thistab.pathway
        if self.settings.tilde_in_titlebar and \
                self.fm.thisdir.path.startswith(self.fm.home_path):
            pathway = pathway[self.fm.home_path.count('/')+1:]
            bar.add('~/', 'directory', fixed=True)

        for path in pathway:
            if path.is_link:
                clr = 'link'
            else:
                clr = 'directory'

            bar.add(path.basename, clr, directory=path)
            bar.add('/', clr, fixed=True, directory=path)

        if self.fm.thisfile is not None:
            bar.add(self.fm.thisfile.basename, 'file')

    def _get_right_part(self, bar):
        # TODO: fix that pressed keys are cut off when chaining CTRL keys
        kb = str(self.fm.ui.keybuffer)
        self.old_keybuffer = kb
        bar.addright(kb, 'keybuffer', fixed=True)
        bar.addright('  ', 'space', fixed=True)
        self.tab_width = 0
        if len(self.fm.tabs) > 1:
            for tabname in self.fm._get_tab_list():
                tabtext = self._get_tab_text(tabname)
                self.tab_width += len(tabtext)
                clr = 'good' if tabname == self.fm.current_tab else 'bad'
                bar.addright(tabtext, 'tab', clr, fixed=True)

    def _get_tab_text(self, tabname):
        result = ' ' + str(tabname)
        if self.settings.dirname_in_tabs:
            dirname = basename(self.fm.tabs[tabname].path)
            if not dirname:
                result += ":/"
            elif len(dirname) > 15:
                result += ":" + dirname[:14] + "~"
            else:
                result += ":" + dirname
        return result

    def _print_result(self, result):
        self.win.move(0, 0)
        for part in result:
            self.color(*part.lst)
            y, x = self.win.getyx()
            self.addstr(y, x, str(part))
        self.color_reset()

########NEW FILE########
__FILENAME__ = ranger
#!/usr/bin/python -O
# ranger - a vim-inspired file manager for the console  (coding: utf-8)
# Copyright (C) 2009-2013  Roman Zimbelmann <hut@lepus.uberspace.de>
# This software is distributed under the terms of the GNU GPL version 3.

# =====================
# This embedded bash script can be executed by sourcing this file.
# It will cd to ranger's last location after you exit it.
# The first argument specifies the command to run ranger, the
# default is simply "ranger". (Not this file itself!)
# The other arguments are passed to ranger.
"""":
tempfile='/tmp/chosendir'
ranger="${1:-ranger}"
test -z "$1" || shift
"$ranger" --choosedir="$tempfile" "${@:-$(pwd)}"
returnvalue=$?
test -f "$tempfile" &&
if [ "$(cat -- "$tempfile")" != "$(echo -n `pwd`)" ]; then
    cd "$(cat "$tempfile")"
    rm -f -- "$tempfile"
fi
return $returnvalue
""" and None

import sys
from os.path import exists, abspath

# Need to find out whether or not the flag --clean was used ASAP,
# because --clean is supposed to disable bytecode compilation
argv = sys.argv[1:sys.argv.index('--')] if '--' in sys.argv else sys.argv[1:]
sys.dont_write_bytecode = '-c' in argv or '--clean' in argv

# Don't import ./ranger when running an installed binary at /usr/.../ranger
if __file__[:4] == '/usr' and exists('ranger') and abspath('.') in sys.path:
    sys.path.remove(abspath('.'))

# Start ranger
import ranger
sys.exit(ranger.main())

########NEW FILE########
