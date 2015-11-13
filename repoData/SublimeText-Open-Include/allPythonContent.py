__FILENAME__ = dialog
#!/usr/bin/env python

"""
Simple desktop dialogue box support for Python.

Copyright (C) 2007, 2009 Paul Boddie <paul@boddie.org.uk>

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU Lesser General Public License as published by the Free
Software Foundation; either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
details.

You should have received a copy of the GNU Lesser General Public License along
with this program.  If not, see <http://www.gnu.org/licenses/>.

--------

Opening Dialogue Boxes (Dialogs)
--------------------------------

To open a dialogue box (dialog) in the current desktop environment, relying on
the automatic detection of that environment, use the appropriate dialogue box
class:

question = desktop.dialog.Question("Are you sure?")
result = question.open()

To override the detected desktop, specify the desktop parameter to the open
function as follows:

question.open("KDE") # Insists on KDE
question.open("GNOME") # Insists on GNOME
question.open("MATE") # Insists on MATE

The dialogue box options are documented in each class's docstring.

Available dialogue box classes are listed in the desktop.dialog.available
attribute.

Supported desktop environments are listed in the desktop.dialog.supported
attribute.
"""

from desktop import use_desktop, _run, _readfrom, _status

class _wrapper:
    def __init__(self, handler):
        self.handler = handler

class _readvalue(_wrapper):
    def __call__(self, cmd, shell):
        return self.handler(cmd, shell).strip()

class _readinput(_wrapper):
    def __call__(self, cmd, shell):
        return self.handler(cmd, shell)[:-1]

class _readvalues_kdialog(_wrapper):
    def __call__(self, cmd, shell):
        result = self.handler(cmd, shell).strip().strip('"')
        if result:
            return result.split('" "')
        else:
            return []

class _readvalues_zenity(_wrapper):
    def __call__(self, cmd, shell):
        result = self.handler(cmd, shell).strip()
        if result:
            return result.split("|")
        else:
            return []

class _readvalues_Xdialog(_wrapper):
    def __call__(self, cmd, shell):
        result = self.handler(cmd, shell).strip()
        if result:
            return result.split("/")
        else:
            return []

# Dialogue parameter classes.

class String:

    "A generic parameter."

    def __init__(self, name):
        self.name = name

    def convert(self, value, program):
        return [value or ""]

class Strings(String):

    "Multiple string parameters."

    def convert(self, value, program):
        return value or []

class StringPairs(String):

    "Multiple string parameters duplicated to make identifiers."

    def convert(self, value, program):
        l = []
        for v in value:
            l.append(v)
            l.append(v)
        return l

class StringKeyword:

    "A keyword parameter."

    def __init__(self, keyword, name):
        self.keyword = keyword
        self.name = name

    def convert(self, value, program):
        return [self.keyword + "=" + (value or "")]

class StringKeywords:

    "Multiple keyword parameters."

    def __init__(self, keyword, name):
        self.keyword = keyword
        self.name = name

    def convert(self, value, program):
        l = []
        for v in value or []:
            l.append(self.keyword + "=" + v)
        return l

class Integer(String):

    "An integer parameter."

    defaults = {
        "width" : 40,
        "height" : 15,
        "list_height" : 10
        }
    scale = 8

    def __init__(self, name, pixels=0):
        String.__init__(self, name)
        if pixels:
            self.factor = self.scale
        else:
            self.factor = 1

    def convert(self, value, program):
        if value is None:
            value = self.defaults[self.name]
        return [str(int(value) * self.factor)]

class IntegerKeyword(Integer):

    "An integer keyword parameter."

    def __init__(self, keyword, name, pixels=0):
        Integer.__init__(self, name, pixels)
        self.keyword = keyword

    def convert(self, value, program):
        if value is None:
            value = self.defaults[self.name]
        return [self.keyword + "=" + str(int(value) * self.factor)]

class Boolean(String):

    "A boolean parameter."

    values = {
        "kdialog" : ["off", "on"],
        "zenity" : ["FALSE", "TRUE"],
        "Xdialog" : ["off", "on"]
        }

    def convert(self, value, program):
        values = self.values[program]
        if value:
            return [values[1]]
        else:
            return [values[0]]

class MenuItemList(String):

    "A menu item list parameter."

    def convert(self, value, program):
        l = []
        for v in value:
            l.append(v.value)
            l.append(v.text)
        return l

class ListItemList(String):

    "A radiolist/checklist item list parameter."

    def __init__(self, name, status_first=0):
        String.__init__(self, name)
        self.status_first = status_first

    def convert(self, value, program):
        l = []
        for v in value:
            boolean = Boolean(None)
            status = boolean.convert(v.status, program)
            if self.status_first:
                l += status
            l.append(v.value)
            l.append(v.text)
            if not self.status_first:
                l += status
        return l

# Dialogue argument values.

class MenuItem:

    "A menu item which can also be used with radiolists and checklists."

    def __init__(self, value, text, status=0):
        self.value = value
        self.text = text
        self.status = status

# Dialogue classes.

class Dialogue:

    commands = {
        "KDE" : "kdialog",
        "GNOME" : "zenity",
        "MATE" : "zenity",
        "XFCE" : "zenity", # NOTE: Based on observations with Xubuntu.
        "X11" : "Xdialog"
        }

    def open(self, desktop=None):

        """
        Open a dialogue box (dialog) using a program appropriate to the desktop
        environment in use.

        If the optional 'desktop' parameter is specified then attempt to use
        that particular desktop environment's mechanisms to open the dialog
        instead of guessing or detecting which environment is being used.

        Suggested values for 'desktop' are "standard", "KDE", "GNOME",
        "MATE", "Mac OS X", "Windows".

        The result of the dialogue interaction may be a string indicating user
        input (for Input, Password, Menu, Pulldown), a list of strings
        indicating selections of one or more items (for RadioList, CheckList),
        or a value indicating true or false (for Question, Warning, Message,
        Error).

        Where a string value may be expected but no choice is made, an empty
        string may be returned. Similarly, where a list of values is expected
        but no choice is made, an empty list may be returned.
        """

        # Decide on the desktop environment in use.

        desktop_in_use = use_desktop(desktop)

        # Get the program.

        try:
            program = self.commands[desktop_in_use]
        except KeyError:
            raise OSError("Desktop '%s' not supported (no known dialogue box command could be suggested)" % desktop_in_use)

        # The handler is one of the functions communicating with the subprocess.
        # Some handlers return boolean values, others strings.

        handler, options = self.info[program]

        cmd = [program]
        for option in options:
            if isinstance(option, str):
                cmd.append(option)
            else:
                value = getattr(self, option.name, None)
                cmd += option.convert(value, program)

        return handler(cmd, 0)

class Simple(Dialogue):
    def __init__(self, text, width=None, height=None):
        self.text = text
        self.width = width
        self.height = height

class Question(Simple):

    """
    A dialogue asking a question and showing response buttons.
    Options: text, width (in characters), height (in characters)
    Response: a boolean value indicating an affirmative response (true) or a
              negative response
    """

    name = "question"
    info = {
        "kdialog" : (_status, ["--yesno", String("text")]),
        "zenity" : (_status, ["--question", StringKeyword("--text", "text")]),
        "Xdialog" : (_status, ["--stdout", "--yesno", String("text"), Integer("height"), Integer("width")]),
        }

class Warning(Simple):

    """
    A dialogue asking a question and showing response buttons.
    Options: text, width (in characters), height (in characters)
    Response: a boolean value indicating an affirmative response (true) or a
              negative response
    """

    name = "warning"
    info = {
        "kdialog" : (_status, ["--warningyesno", String("text")]),
        "zenity" : (_status, ["--warning", StringKeyword("--text", "text")]),
        "Xdialog" : (_status, ["--stdout", "--yesno", String("text"), Integer("height"), Integer("width")]),
        }

class Message(Simple):

    """
    A message dialogue.
    Options: text, width (in characters), height (in characters)
    Response: a boolean value indicating an affirmative response (true) or a
              negative response
    """

    name = "message"
    info = {
        "kdialog" : (_status, ["--msgbox", String("text")]),
        "zenity" : (_status, ["--info", StringKeyword("--text", "text")]),
        "Xdialog" : (_status, ["--stdout", "--msgbox", String("text"), Integer("height"), Integer("width")]),
        }

class Error(Simple):

    """
    An error dialogue.
    Options: text, width (in characters), height (in characters)
    Response: a boolean value indicating an affirmative response (true) or a
              negative response
    """

    name = "error"
    info = {
        "kdialog" : (_status, ["--error", String("text")]),
        "zenity" : (_status, ["--error", StringKeyword("--text", "text")]),
        "Xdialog" : (_status, ["--stdout", "--msgbox", String("text"), Integer("height"), Integer("width")]),
        }

class Menu(Simple):

    """
    A menu of options, one of which being selectable.
    Options: text, width (in characters), height (in characters),
             list_height (in items), items (MenuItem objects)
    Response: a value corresponding to the chosen item
    """

    name = "menu"
    info = {
        "kdialog" : (_readvalue(_readfrom), ["--menu", String("text"), MenuItemList("items")]),
        "zenity" : (_readvalue(_readfrom), ["--list", StringKeyword("--text", "text"), StringKeywords("--column", "titles"),
            MenuItemList("items")]
            ),
        "Xdialog" : (_readvalue(_readfrom), ["--stdout", "--menubox",
            String("text"), Integer("height"), Integer("width"), Integer("list_height"), MenuItemList("items")]
            ),
        }
    item = MenuItem
    number_of_titles = 2

    def __init__(self, text, titles, items=None, width=None, height=None, list_height=None):

        """
        Initialise a menu with the given heading 'text', column 'titles', and
        optional 'items' (which may be added later), 'width' (in characters),
        'height' (in characters) and 'list_height' (in items).
        """

        Simple.__init__(self, text, width, height)
        self.titles = ([""] * self.number_of_titles + titles)[-self.number_of_titles:]
        self.items = items or []
        self.list_height = list_height

    def add(self, *args, **kw):

        """
        Add an item, passing the given arguments to the appropriate item class.
        """

        self.items.append(self.item(*args, **kw))

class RadioList(Menu):

    """
    A list of radio buttons, one of which being selectable.
    Options: text, width (in characters), height (in characters),
             list_height (in items), items (MenuItem objects), titles
    Response: a list of values corresponding to chosen items (since some
              programs, eg. zenity, appear to support multiple default
              selections)
    """

    name = "radiolist"
    info = {
        "kdialog" : (_readvalues_kdialog(_readfrom), ["--radiolist", String("text"), ListItemList("items")]),
        "zenity" : (_readvalues_zenity(_readfrom),
            ["--list", "--radiolist", StringKeyword("--text", "text"), StringKeywords("--column", "titles"),
            ListItemList("items", 1)]
            ),
        "Xdialog" : (_readvalues_Xdialog(_readfrom), ["--stdout", "--radiolist",
            String("text"), Integer("height"), Integer("width"), Integer("list_height"), ListItemList("items")]
            ),
        }
    number_of_titles = 3

class CheckList(Menu):

    """
    A list of checkboxes, many being selectable.
    Options: text, width (in characters), height (in characters),
             list_height (in items), items (MenuItem objects), titles
    Response: a list of values corresponding to chosen items
    """

    name = "checklist"
    info = {
        "kdialog" : (_readvalues_kdialog(_readfrom), ["--checklist", String("text"), ListItemList("items")]),
        "zenity" : (_readvalues_zenity(_readfrom),
            ["--list", "--checklist", StringKeyword("--text", "text"), StringKeywords("--column", "titles"),
            ListItemList("items", 1)]
            ),
        "Xdialog" : (_readvalues_Xdialog(_readfrom), ["--stdout", "--checklist",
            String("text"), Integer("height"), Integer("width"), Integer("list_height"), ListItemList("items")]
            ),
        }
    number_of_titles = 3

class Pulldown(Menu):

    """
    A pull-down menu of options, one of which being selectable.
    Options: text, width (in characters), height (in characters),
             items (list of values)
    Response: a value corresponding to the chosen item
    """

    name = "pulldown"
    info = {
        "kdialog" : (_readvalue(_readfrom), ["--combobox", String("text"), Strings("items")]),
        "zenity" : (_readvalue(_readfrom),
            ["--list", "--radiolist", StringKeyword("--text", "text"), StringKeywords("--column", "titles"),
            StringPairs("items")]
            ),
        "Xdialog" : (_readvalue(_readfrom),
            ["--stdout", "--combobox", String("text"), Integer("height"), Integer("width"), Strings("items")]),
        }
    item = str
    number_of_titles = 2

class Input(Simple):

    """
    An input dialogue, consisting of an input field.
    Options: text, input, width (in characters), height (in characters)
    Response: the text entered into the dialogue by the user
    """

    name = "input"
    info = {
        "kdialog" : (_readinput(_readfrom),
            ["--inputbox", String("text"), String("data")]),
        "zenity" : (_readinput(_readfrom),
            ["--entry", StringKeyword("--text", "text"), StringKeyword("--entry-text", "data")]),
        "Xdialog" : (_readinput(_readfrom),
            ["--stdout", "--inputbox", String("text"), Integer("height"), Integer("width"), String("data")]),
        }

    def __init__(self, text, data="", width=None, height=None):
        Simple.__init__(self, text, width, height)
        self.data = data

class Password(Input):

    """
    A password dialogue, consisting of a password entry field.
    Options: text, width (in characters), height (in characters)
    Response: the text entered into the dialogue by the user
    """

    name = "password"
    info = {
        "kdialog" : (_readinput(_readfrom),
            ["--password", String("text")]),
        "zenity" : (_readinput(_readfrom),
            ["--entry", StringKeyword("--text", "text"), "--hide-text"]),
        "Xdialog" : (_readinput(_readfrom),
            ["--stdout", "--password", "--inputbox", String("text"), Integer("height"), Integer("width")]),
        }

class TextFile(Simple):

    """
    A text file input box.
    Options: filename, text, width (in characters), height (in characters)
    Response: any text returned by the dialogue program (typically an empty
              string)
    """

    name = "textfile"
    info = {
        "kdialog" : (_readfrom, ["--textbox", String("filename"), Integer("width", pixels=1), Integer("height", pixels=1)]),
        "zenity" : (_readfrom, ["--text-info", StringKeyword("--filename", "filename"), IntegerKeyword("--width", "width", pixels=1),
            IntegerKeyword("--height", "height", pixels=1)]
            ),
        "Xdialog" : (_readfrom, ["--stdout", "--textbox", String("filename"), Integer("height"), Integer("width")]),
        }

    def __init__(self, filename, text="", width=None, height=None):
        Simple.__init__(self, text, width, height)
        self.filename = filename

# Available dialogues.

available = [Question, Warning, Message, Error, Menu, CheckList, RadioList, Input, Password, Pulldown, TextFile]

# Supported desktop environments.

supported = list(Dialogue.commands.keys())

# vim: tabstop=4 expandtab shiftwidth=4

########NEW FILE########
__FILENAME__ = windows
#!/usr/bin/env python

"""
Simple desktop window enumeration for Python.

Copyright (C) 2007, 2008, 2009 Paul Boddie <paul@boddie.org.uk>

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU Lesser General Public License as published by the Free
Software Foundation; either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
details.

You should have received a copy of the GNU Lesser General Public License along
with this program.  If not, see <http://www.gnu.org/licenses/>.

--------

Finding Open Windows on the Desktop
-----------------------------------

To obtain a list of windows, use the desktop.windows.list function as follows:

windows = desktop.windows.list()

To obtain the root window, typically the desktop background, use the
desktop.windows.root function as follows:

root = desktop.windows.root()

Each window object can be inspected through a number of methods. For example:

name = window.name()
width, height = window.size()
x, y = window.position()
child_windows = window.children()

See the desktop.windows.Window class for more information.
"""

from desktop import _is_x11, _get_x11_vars, _readfrom, use_desktop
import re

# System functions.

def _xwininfo(identifier, action):
    if identifier is None:
        args = "-root"
    else:
        args = "-id " + identifier

    s = _readfrom(_get_x11_vars() + "xwininfo %s -%s" % (args, action), shell=1)

    # Return a mapping of keys to values for the "stats" action.

    if action == "stats":
        d = {}
        for line in s.split("\n"):
            fields = line.split(":")
            if len(fields) < 2:
                continue
            key, value = fields[0].strip(), ":".join(fields[1:]).strip()
            d[key] = value

        return d

    # Otherwise, return the raw output.

    else:
        return s

def _get_int_properties(d, properties):
    results = []
    for property in properties:
        results.append(int(d[property]))
    return results

# Finder functions.

def find_all(name):
    return 1

def find_named(name):
    return name is not None

def find_by_name(name):
    return lambda n, t=name: n == t

# Window classes.
# NOTE: X11 is the only supported desktop so far.

class Window:

    "A window on the desktop."

    _name_pattern = re.compile(r':\s+\(.*?\)\s+[-0-9x+]+\s+[-0-9+]+$')
    _absent_names = "(has no name)", "(the root window) (has no name)"

    def __init__(self, identifier):

        "Initialise the window with the given 'identifier'."

        self.identifier = identifier

        # Finder methods (from above).

        self.find_all = find_all
        self.find_named = find_named
        self.find_by_name = find_by_name

    def __repr__(self):
        return "Window(%r)" % self.identifier

    # Methods which deal with the underlying commands.

    def _get_handle_and_name(self, text):
        fields = text.strip().split(" ")
        handle = fields[0]

        # Get the "<name>" part, stripping off the quotes.

        name = " ".join(fields[1:])
        if len(name) > 1 and name[0] == '"' and name[-1] == '"':
            name = name[1:-1]

        if name in self._absent_names:
            return handle, None
        else:
            return handle, name

    def _get_this_handle_and_name(self, line):
        fields = line.split(":")
        return self._get_handle_and_name(":".join(fields[1:]))

    def _get_descendant_handle_and_name(self, line):
        match = self._name_pattern.search(line)
        if match:
            return self._get_handle_and_name(line[:match.start()].strip())
        else:
            raise OSError("Window information from %r did not contain window details." % line)

    def _descendants(self, s, fn):
        handles = []
        adding = 0
        for line in s.split("\n"):
            if line.endswith("child:") or line.endswith("children:"):
                if not adding:
                    adding = 1
            elif adding and line:
                handle, name = self._get_descendant_handle_and_name(line)
                if fn(name):
                    handles.append(handle)
        return [Window(handle) for handle in handles]

    # Public methods.

    def children(self, all=0):

        """
        Return a list of windows which are children of this window. If the
        optional 'all' parameter is set to a true value, all such windows will
        be returned regardless of whether they have any name information.
        """

        s = _xwininfo(self.identifier, "children")
        return self._descendants(s, all and self.find_all or self.find_named)

    def descendants(self, all=0):

        """
        Return a list of windows which are descendants of this window. If the
        optional 'all' parameter is set to a true value, all such windows will
        be returned regardless of whether they have any name information.
        """

        s = _xwininfo(self.identifier, "tree")
        return self._descendants(s, all and self.find_all or self.find_named)

    def find(self, callable):

        """
        Return windows using the given 'callable' (returning a true or a false
        value when invoked with a window name) for descendants of this window.
        """

        s = _xwininfo(self.identifier, "tree")
        return self._descendants(s, callable)

    def name(self):

        "Return the name of the window."

        d = _xwininfo(self.identifier, "stats")

        # Format is 'xwininfo: Window id: <handle> "<name>"

        return self._get_this_handle_and_name(d["xwininfo"])[1]

    def size(self):

        "Return a tuple containing the width and height of this window."

        d = _xwininfo(self.identifier, "stats")
        return _get_int_properties(d, ["Width", "Height"])

    def position(self):

        "Return a tuple containing the upper left co-ordinates of this window."

        d = _xwininfo(self.identifier, "stats")
        return _get_int_properties(d, ["Absolute upper-left X", "Absolute upper-left Y"])

    def displayed(self):

        """
        Return whether the window is displayed in some way (but not necessarily
        visible on the current screen).
        """

        d = _xwininfo(self.identifier, "stats")
        return d["Map State"] != "IsUnviewable"

    def visible(self):

        "Return whether the window is displayed and visible."

        d = _xwininfo(self.identifier, "stats")
        return d["Map State"] == "IsViewable"

def list(desktop=None):

    """
    Return a list of windows for the current desktop. If the optional 'desktop'
    parameter is specified then attempt to use that particular desktop
    environment's mechanisms to look for windows.
    """

    root_window = root(desktop)
    window_list = [window for window in root_window.descendants() if window.displayed()]
    window_list.insert(0, root_window)
    return window_list

def root(desktop=None):

    """
    Return the root window for the current desktop. If the optional 'desktop'
    parameter is specified then attempt to use that particular desktop
    environment's mechanisms to look for windows.
    """

    # NOTE: The desktop parameter is currently ignored and X11 is tested for
    # NOTE: directly.

    if _is_x11():
        return Window(None)
    else:
        raise OSError("Desktop '%s' not supported" % use_desktop(desktop))

def find(callable, desktop=None):

    """
    Find and return windows using the given 'callable' for the current desktop.
    If the optional 'desktop' parameter is specified then attempt to use that
    particular desktop environment's mechanisms to look for windows.
    """

    return root(desktop).find(callable)

# vim: tabstop=4 expandtab shiftwidth=4

########NEW FILE########
__FILENAME__ = Edit
# edit.py
# buffer editing for both ST2 and ST3 that "just works"

import sublime
import sublime_plugin
from collections import defaultdict

try:
    sublime.edit_storage
except AttributeError:
    sublime.edit_storage = {}

class EditStep:
    def __init__(self, cmd, *args):
        self.cmd = cmd
        self.args = args

    def run(self, view, edit):
        if self.cmd == 'callback':
            return self.args[0](view, edit)

        funcs = {
            'insert': view.insert,
            'erase': view.erase,
            'replace': view.replace,
        }
        func = funcs.get(self.cmd)
        if func:
            func(edit, *self.args)


class Edit:
    defer = defaultdict(dict)

    def __init__(self, view):
        self.view = view
        self.steps = []

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

    def run(self, view, edit):
        for step in self.steps:
            step.run(view, edit)

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
__FILENAME__ = open_env
import sublime, sublime_plugin
import os

# Note: This plugin uses 'Verbose' plugin available in 'Package Control' to log some messages for debug purpose but it works fine without.


PluginName = 'Open-Include'


def verbose(**kwargs):
    kwargs.update({'plugin_name': PluginName})
    sublime.run_command("verbose", kwargs)


class Prefs:
    @staticmethod
    def load():
        settings = sublime.load_settings(PluginName + '.sublime-settings')
        Prefs.environment = settings.get('environment', [])
        Prefs.expand_alias = settings.get('expand_alias', True)

    @staticmethod
    def show():
        verbose(log="############################################################")
        for env in Prefs.environment:
            for key, values in env.items():
                verbose(log=key + ": " + ';'.join(values))
        verbose(log="############################################################")


if int(sublime.version()) < 3000:
    Prefs.load()


### OpenFileFromEnv ###

# Find root directory
# Get base directory with name
# foreach env test if file exit
class OpenFileFromEnvCommand(sublime_plugin.TextCommand):

    # Set by is_enabled()
    initial_env_name = ''
    base_name = ''

    # List of existing files in other environments
    env_files = []

    def run(self, edit):
        verbose(log="run()")

        verbose(log="initial_env_name: " + self.initial_env_name)
        verbose(log="base_name: " + self.base_name)

        if len(self.base_name) > 0:
            # Create a list of files which exist in other environment
            self.env_files = []
            for env in Prefs.environment:
                for env_name, root_alias in env.items():

                    # Bypass initial environment
                    if env_name == self.initial_env_name:
                        continue

                    # Loop in path alias of the current environment
                    available_file_names = []
                    for root in root_alias:
                        env_file_name = os.path.join(root, self.base_name)
                        state = ' '
                        if os.path.exists(env_file_name):
                            state = 'X'
                            if Prefs.expand_alias:
                                self.env_files.append([env_name, env_file_name])
                            else:
                                available_file_names.append(env_file_name)
                        verbose(log='[%s] %15s %s' % (state, env_name, env_file_name))

                    if len(available_file_names) > 0:
                        # available_file_names used only with expand_alias = False
                        current_id = self.view.id()
                        is_file_opened = False
                        # Find the first file of the environment which is already opened in st
                        for v in self.view.window().views():
                            if v.id() == current_id or v.file_name() is None:
                                continue
                            for file_name in available_file_names:
                                if file_name.lower() == v.file_name().lower():
                                    self.env_files.append([env_name, file_name])
                                    is_file_opened = True
                                    break
                            if is_file_opened:
                                break
                        # Or choose the file of the environment of the main path
                        if not is_file_opened:
                            self.env_files.append([env_name, available_file_names[0]])

            if len(self.env_files) > 0:
                self.view.window().show_quick_panel(self.env_files, self.quick_panel_done)
            else:
                sublime.status_message("No file found in other environments")


    def quick_panel_done(self, index):
        if index > -1:
            # Open selected file in an another environment
            self.view.window().open_file(self.env_files[index][1])


    def is_filename_part_of_env(self, file_name, root_alias):
        for root in root_alias:
            # Remove trailing os.sep
            root = os.path.normpath(root).lower()
            if file_name.startswith(root):
                base_name = file_name.replace(root.lower(), "")
                if base_name[0] == os.sep:
                    # Get back the original case
                    file_name = self.view.file_name()
                    # Remove first os.sep character and get base name
                    self.base_name = file_name[len(file_name)-len(base_name)+1:]
                    return True
        return False

    # Return True if the file is part of an environment
    def is_enabled(self):
        Prefs.show()
        verbose(log="is_enabled()")

        file_name = self.view.file_name()
        self.initial_env_name = ''
        base_name = ''
        if file_name is not None and len(file_name) > 0:
            file_name = file_name.lower()
            verbose(log="file_name: " + file_name)

            # Loop into registered environment
            for env in Prefs.environment:
                for env_name, root_alias in env.items():
                    # Test if file_name is part of an environment
                    if self.is_filename_part_of_env(file_name, root_alias):
                        self.initial_env_name = env_name
                        return True

        sublime.status_message("The current file is not part of an environment")
        return False

########NEW FILE########
__FILENAME__ = open_include
import os.path
import re
import threading
import urllib

import sublime
import sublime_plugin

try:
    from .Edit import Edit as Edit
except:
    from Edit import Edit as Edit

BINARY = re.compile('\.(psd|ai|cdr|ico|cache|sublime-package|eot|svgz|ttf|woff|zip|tar|gz|rar|bz2|jar|xpi|mov|mpeg|avi|mpg|flv|wmv|mp3|wav|aif|aiff|snd|wma|asf|asx|pcm|pdf|doc|docx|xls|xlsx|ppt|pptx|rtf|sqlite|sqlitedb|fla|swf|exe)$', re.I)
IMAGE = re.compile('\.(apng|png|jpg|gif|jpeg|bmp)$', re.I)

# global settings container
s = None


def plugin_loaded():
    global s
    s = sublime.load_settings('Open-Include.sublime-settings')


class OpenInclude(sublime_plugin.TextCommand):

    # run and look for different sources of paths
    def run(self, edit):
        window = sublime.active_window()
        view = self.view
        something_opened = False

        for region in view.sel():
            opened = False

            # find in files panel
            if not opened and 'Find Results.hidden-tmLanguage' in view.settings().get('syntax'):
            	opened = OpenIncludeFindInFileGoto().run(view);

            # between quotes
            if not opened and view.score_selector(region.begin(), "parameter.url, string.quoted"):
                file_to_open = view.substr(view.extract_scope(region.begin()))
                opened = self.resolve_path(window, view, file_to_open)

                if opened:
                    break

                if not opened and s.get('create_if_not_exists') and view.file_name():
                    file_name = view.substr(view.extract_scope(region.begin())).replace("'", '').replace('"', '')
                    path = self.resolve_relative(os.path.dirname(view.file_name()), file_name)
                    branch, leaf = os.path.split(path)
                    try:
                        os.makedirs(branch)
                    except:
                        pass
                    window.open_file(path)
                    opened = True

            # between curly brackets
            if not opened:
                file_to_open = view.substr(view.extract_scope(region.begin())).replace('{','').replace('}','')
                opened = self.resolve_path(window, view, file_to_open)

                if opened:
                    break

            # word
            if not opened:
                file_to_open = view.substr(view.word(region)).strip()
                opened = self.resolve_path(window, view, file_to_open)

            # selected text
            if not opened:
                opened = self.resolve_path(window, view, view.substr(region))

            # current line quotes and parenthesis
            if not opened:
                line = view.substr(view.line(region.begin()))
                for line in re.split(r"[()'\"]", line):
                    line = line.strip()
                    if line:
                        opened = self.resolve_path(window, view, line)
                        if opened:
                            break

            # selection expanded to full lines
            if not opened:
                expanded_lines = view.substr(sublime.Region(view.line(region.begin()).begin(), view.line(region.end()).end()))
                opened = self.resolve_path(window, view, expanded_lines)

                # split by spaces and tabs
                if not opened:
                    words = re.sub(r"\s+", "\n", expanded_lines)  # expanded_lines.replace('\t', '\n').replace(' ', '\n'))
                    opened = self.resolve_path(window, view, words)

            if opened:
                something_opened = True

        # Nothing in a selected region could be opened
        if not something_opened:
            opened = self.resolve_path(window, view, view.substr(sublime.Region(0, view.size())).replace('\t', '\n'))
            if not opened:
            	sublime.status_message("Unable to find a file in the current selection")

    def expand_paths_with_extensions(self, window, view, paths):

        # Special file naming conventions, e.g. '_'+name+'.scss' + current extension
        extensions = s.get('auto_extension', [])
        if view.file_name():
            file_ext = os.path.splitext(view.file_name())[1]
            extensions.append(dict(extension=file_ext))

        path_add = []
        for path in paths:
            if os.path.splitext(path)[1]:
                continue
            for extension in extensions:
                subs = path.replace('\\', '/').split('/')
                subs[-1] = re.sub('("|\')', '', subs[-1]);
                subs[-1] = extension.get('prefix', '') + subs[-1] + extension.get('extension', '')
                path_add.append(os.path.join(*subs))
        return paths + path_add

    # resolve the path of these sources and send to try_open
    def resolve_path(self, window, view, paths):
        try:
            paths_decoded = urllib.unquote(paths.encode('utf8'))
            paths_decoded = unicode(paths_decoded.decode('utf8'))
            paths += '\n' + paths_decoded
        except:
            pass

        paths = paths.split('\n')

        if s.get('use_strict'):
            return self.try_open(window, self.resolve_relative(os.path.dirname(view.file_name()), paths[0]))

        paths = self.expand_paths_with_extensions(window, view, paths)

        something_opened = False

        for path in paths:
            path = path.strip()
            if path == '':
                continue

            # remove quotes
            path = path.strip('"\'<>')  # re.sub(r'^("|\'|<)|("|\'|>)$', '', path)

            # remove :row:col
            path = re.sub('(\:[0-9]*)+$', '', path).strip()

            folder_structure = ["../" * i for i in range(s.get('maximum_folder_up', 5))]

            # relative to view & view dir name
            opened = False
            if view.file_name():
                for new_path_prefix in folder_structure:
                    maybe_path = os.path.dirname(view.file_name())
                    opened = self.create_path_relative_to_folder(window, view, maybe_path, new_path_prefix + path)
                    if not opened:
                        maybe_path = os.path.dirname(maybe_path)
                        opened = self.create_path_relative_to_folder(window, view, maybe_path, new_path_prefix + path)

                    if opened:
                        break

            # relative to project folders
            if not opened:
                for maybe_path in sublime.active_window().folders():
                    for new_path_prefix in folder_structure:
                        if self.create_path_relative_to_folder(window, view, maybe_path, new_path_prefix + path):
                            opened = True
                            break
                    if opened:
                        break

            # absolute
            if not opened:
                opened = self.try_open(window, path)
                if opened:
                    opened = True

            if opened:
                something_opened = True

        return something_opened

    def create_path_relative_to_folder(self, window, view, maybe_path, path):
        maybe_path_tpm = self.resolve_relative(maybe_path, path)
        return self.try_open(window, maybe_path_tpm)

    # try opening the resouce
    def try_open(self, window, maybe_path):
        # TODO: Add this somewhere WAY earlier since we are doing so much data
        # processing regarding paths prior to this
        if re.match(r'https?://', maybe_path):
            # HTTP URL
            if BINARY.search(maybe_path) or s.get("open_http_in_browser", False):
                sublime.status_message("Opening in browser " + maybe_path)

                import webbrowser
                webbrowser.open_new_tab(maybe_path)
            else:
                sublime.status_message("Opening URL " + maybe_path)
                # Create thread to download url in background
                threading.Thread(target=self.read_url, args=(maybe_path,)).start()

        elif os.path.isfile(maybe_path):
            if IMAGE.search(maybe_path):
                window.open_file(maybe_path)
            elif BINARY.search(maybe_path):
                try:
                    import desktop
                except:
                    from . import desktop
                desktop.open(maybe_path)
            else:
                # Open within ST
                window.open_file(maybe_path)
            sublime.status_message("Opening file " + maybe_path)
        else:
            return False

        return True

    # util
    def resolve_relative(self, absolute, path):
        subs = path.replace('\\', '/').split('/')
        for sub in subs:
            if sub != '':
                absolute = os.path.join(absolute, sub)
        return absolute

    def read_url(self, url):
        try:
            if url.startswith('https'):
                url = 'http' + url[5:]

            import urllib.request
            req = urllib.request.urlopen(url)
            content = req.read()
            encoding = req.headers['content-type'].split('charset=')[-1]
            try:
                content = str(content, encoding)
            except:
                try:
                    content = str(content, 'utf-8')
                except:
                    content = str(content, 'utf8', errors="replace")

            content_type = req.headers['content-type'].split(';')[0]
            # ST3 is thread-safe, but ST2 is not so we use set_timeout to get to the main thread again
            sublime.set_timeout(lambda: self.read_url_on_done(content, content_type), 0)
        except:
            pass

    def read_url_on_done(self, content, content_type):
        if content:
            window = sublime.active_window()
            view = window.new_file()
            with Edit(view) as edit:
                edit.insert(0, content)

            # TODO: convert to a dict and include in settings
            if content_type == 'text/html':
                view.settings().set('syntax', 'Packages/HTML/HTML.tmLanguage')
            elif content_type == 'text/css':
                view.settings().set('syntax', 'Packages/CSS/CSS.tmLanguage')
            elif content_type == 'text/javascript' or content_type == 'application/javascript' or content_type == 'application/x-javascript':
                view.settings().set('syntax', 'Packages/JavaScript/JavaScript.tmLanguage')
            elif content_type == 'application/json' or content_type == 'text/json':
                view.settings().set('syntax', 'Packages/JavaScript/JSON.tmLanguage')
            elif content_type == 'text/xml' or content_type == 'application/xml':
                view.settings().set('syntax', 'Packages/XML/XML.tmLanguage')

class OpenIncludeFindInFileGoto():
    def run(self, view):
        line_no = self.get_line_no(view)
        file_name = self.get_file(view)
        if line_no is not None and file_name is not None:
            file_loc = "%s:%s" % (file_name, line_no)
            view.window().open_file(file_loc, sublime.ENCODED_POSITION)
            return True
        elif file_name is not None:
            view.window().open_file(file_name)
            return True
        return False

    def get_line_no(self, view):
        if len(view.sel()) == 1:
            line_text = view.substr(view.line(view.sel()[0]))
            match = re.match(r"\s*(\d+).+", line_text)
            if match:
                return match.group(1)
        return None

    def get_file(self, view):
        if len(view.sel()) == 1:
            line = view.line(view.sel()[0])
            while line.begin() > 0:
                line_text = view.substr(line)
                match = re.match(r"^(.+)\:$", line_text)
                if match:
                    if os.path.exists(match.group(1)):
                        return match.group(1)
                line = view.line(line.begin() - 1)
        return None

if int(sublime.version()) < 3000:
    plugin_loaded()
########NEW FILE########
